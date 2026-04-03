---
layout: post
title: "Apache Iceberg 실전: Snapshot, Partition Evolution, Compaction으로 데이터 레이크를 운영하는 기준"
date: 2026-04-03 11:40:00 +0900
categories: [data-infra]
tags: [study, data-infra, apache-iceberg, lakehouse, data-lake, snapshot, partition-evolution, compaction, spark, analytics]
---

## 배경: 데이터 레이크가 느려지는 이유는 파일 포맷보다 "테이블 운영 방식"에 더 가깝다

데이터 플랫폼이 어느 정도 커지면 비슷한 장면이 반복된다.

- Parquet는 잘 쓰고 있는데도 쿼리 성능이 들쭉날쭉하다
- 일 단위 파티션으로 시작했는데 데이터가 늘면서 시간 단위 분할이 필요해졌다
- CDC나 스트리밍 적재를 붙였더니 작은 파일이 폭발적으로 늘어났다
- `INSERT OVERWRITE` 한 번 잘못 날려서 파티션이 통째로 비거나 중복이 생겼다
- 테이블 스키마와 파티션 전략이 자주 바뀌는데 매번 새 테이블을 파서 마이그레이션하고 있다
- 엔진은 Spark, Trino, Flink를 같이 쓰는데 테이블 메타데이터 일관성이 점점 불안해진다

이 시점부터 문제의 본질은 "데이터를 어떤 파일 형식으로 저장하느냐"가 아니라, **테이블을 어떻게 버전 관리하고, 변경하고, 유지보수할 것인가**로 바뀐다.

Apache Iceberg가 주목받는 이유도 여기에 있다. Iceberg는 단순히 Parquet 위에 하나 더 얹는 도구가 아니라, **객체 스토리지 위에서도 데이터 레이크를 테이블 단위로 안전하게 운영하기 위한 메타데이터 계층**에 가깝다.

특히 중급 이상 개발자에게 중요한 질문은 아래다.

- Iceberg는 Hive-style 파티션 테이블과 정확히 무엇이 다른가?
- snapshot은 단순 버전 이력인가, 아니면 쓰기/롤백/리커버리의 핵심인가?
- partition evolution은 왜 "새 테이블 없이" 가능한가?
- CDC, upsert, late data, delete가 많은 테이블에서 compaction은 언제 어떻게 돌려야 하는가?
- 메타데이터 정리, snapshot 만료, orphan file 삭제를 안 하면 실제로 무엇이 망가지는가?

오늘 글은 Iceberg 소개 글이 아니라, **운영 환경에서 오래 가는 Iceberg 테이블을 어떻게 설계하고 관리할 것인가**를 기준 중심으로 정리한다.

핵심은 다섯 가지다.

1. Iceberg는 파일 포맷이 아니라 **테이블 포맷**이다
2. snapshot은 time travel 기능이 아니라 **동시성/복구/원자성의 중심축**이다
3. partition evolution과 hidden partitioning이 레이크하우스 운영 비용을 크게 줄인다
4. 소규모 스트리밍 적재 환경에서는 compaction과 metadata maintenance가 사실상 필수다
5. Iceberg를 도입해도 테이블 설계와 운영 기준이 없으면 결국 "객체 스토리지 위의 또 다른 복잡성"이 된다

---

## 먼저 큰 그림: Iceberg는 "쿼리 엔진"이 아니라 "테이블 계약"이다

Iceberg를 처음 접하면 Spark나 Trino의 기능처럼 보이기 쉽다. 하지만 그렇게 이해하면 중요한 절반을 놓친다.

Iceberg의 본질은 다음에 가깝다.

> 객체 스토리지나 분산 파일시스템 위에 저장된 데이터 파일들을, **스냅샷·스키마·파티션·삭제·정렬·메타데이터**까지 포함하는 하나의 테이블 계약으로 관리하는 포맷

즉 Iceberg는 직접 쿼리를 실행하지 않는다. 대신 Spark, Trino, Flink, Snowflake 같은 엔진이 **같은 테이블 상태를 해석할 수 있게 하는 공통 메타데이터 모델**을 제공한다.

이 관점이 중요한 이유는 아래와 같다.

### 1) Iceberg는 Parquet의 대체재가 아니다

대부분의 경우 Iceberg 테이블의 실제 데이터 파일은 여전히 Parquet, Avro, ORC 같은 형식으로 저장된다.

- Parquet/ORC/Avro: 파일 포맷
- Iceberg: 그 파일들을 테이블로 묶는 메타데이터 포맷

즉 "Parquet vs Iceberg"는 비교 대상이 아니다.
정확히는 **"Hive-style table metadata vs Iceberg table metadata"**에 가깝다.

### 2) Iceberg는 Hive-style 파티션 운영의 고질병을 줄인다

기존 Hive 스타일에서는 보통 아래와 같은 문제가 있었다.

- 쿼리가 파티션 컬럼에 직접 의존한다
- 파티션 레이아웃을 바꾸려면 새 테이블을 만들고 데이터 마이그레이션을 해야 한다
- 파일 목록과 파티션 목록을 맞추는 작업이 무겁다
- 객체 스토리지 rename 비원자성 문제가 메타데이터 정합성을 해친다

Iceberg는 이 문제를 **manifest / manifest list / metadata JSON / snapshot pointer** 구조로 완화한다.

### 3) 엔진을 바꿔도 테이블 상태를 공유할 수 있다

예를 들어 아래처럼 역할을 나눌 수 있다.

- Spark: 대량 적재, MERGE, compaction
- Flink: 스트리밍 append/upsert
- Trino: 저지연 분석 쿼리

핵심은 이 엔진들이 "각자 알아서 파일을 읽는 것"이 아니라, **동일한 Iceberg table metadata를 기준으로 같은 스냅샷을 바라본다**는 점이다.

즉 Iceberg를 도입한다는 것은 단순히 새로운 저장 형식을 쓰는 것이 아니라,
**데이터 레이크의 테이블 의미를 메타데이터 차원에서 표준화한다**는 뜻이다.

---

## 핵심 개념 1: Snapshot은 time travel 옵션이 아니라 쓰기 원자성과 복구의 핵심이다

Iceberg를 설명할 때 흔히 "snapshot이 있으니 과거 버전을 조회할 수 있다"고 말한다. 맞는 말이지만 절반만 맞다. 실무에서 snapshot이 진짜 중요한 이유는 **time travel보다 commit 모델**에 있다.

### Iceberg 쓰기는 결국 "새 snapshot 생성"이다

Iceberg에서 append, overwrite, delete, merge, compaction 같은 작업은 모두 결국 아래 흐름으로 이해하면 쉽다.

1. 새 데이터 파일 또는 삭제 파일을 준비한다
2. 어떤 파일들이 현재 테이블 상태에 포함되는지 메타데이터를 계산한다
3. 새 manifest / manifest list / metadata 파일을 만든다
4. 마지막에 테이블의 현재 snapshot 포인터를 새 metadata로 원자적으로 교체한다

즉 데이터 파일을 조금씩 건드리는 방식이 아니라, **테이블 상태 전체를 새 snapshot으로 교체하는 모델**에 가깝다.

### 왜 이 모델이 중요한가

이 모델 덕분에 다음이 가능해진다.

- 중간 실패가 나도 "이전 snapshot"은 그대로 남는다
- 소비자는 commit 전의 반쯤 완성된 상태를 보지 않는다
- 롤백과 time travel이 테이블 운영 기능으로 자연스럽게 연결된다
- 동시 쓰기 충돌을 optimistic concurrency 방식으로 다룰 수 있다

즉 snapshot은 단순 버전 히스토리가 아니라, **테이블의 일관된 읽기 기준점**이다.

### 실무적으로는 "파일 집합의 원자적 교체"라고 생각하는 편이 좋다

RDB에서 트랜잭션을 이해할 때 row lock이나 redo log를 떠올리듯, Iceberg에서는 snapshot pointer 전환을 떠올리면 된다.

- append → 새 파일을 추가한 새 snapshot
- overwrite → 일부 파일 집합을 교체한 새 snapshot
- merge → 영향받는 파일만 다시 쓴 새 snapshot
- compaction → 작은 파일 여러 개를 큰 파일로 재조합한 새 snapshot

즉 write path 전체가 snapshot 중심으로 움직인다.

### time travel은 부가 기능이 아니라 디버깅과 검증 수단이다

이 구조 덕분에 time travel이 가능해진다. 하지만 운영자 입장에서는 "과거 데이터를 조회하는 재미있는 기능"보다 아래 용도가 더 중요하다.

- 잘못된 overwrite 이후 직전 snapshot 검증
- 지표 급변 시 특정 시점 테이블 상태 비교
- compaction 전/후 데이터 동일성 검증
- 파이프라인 버그 배포 이후 어떤 snapshot부터 문제가 시작됐는지 역추적

즉 snapshot이 있다는 것은 단순히 버전이 남는다는 뜻이 아니라,
**테이블 변경을 되돌릴 수 있는 복구 단위가 생긴다**는 뜻이다.

---

## 핵심 개념 2: Hidden Partitioning이 Hive-style 파티션의 운영 복잡도를 크게 줄인다

Iceberg를 이해할 때 가장 체감 차이가 큰 지점 중 하나가 hidden partitioning이다.

기존 Hive 스타일에서는 보통 이런 식이었다.

- 디렉터리 구조: `dt=2026-04-03/hour=11/...`
- 쿼리도 그 구조를 의식해서 작성
- 파티션 키를 바꾸면 쿼리와 적재 로직, 테이블 구조를 함께 바꿔야 함

Iceberg는 접근이 다르다.

### 쿼리는 원본 컬럼을 기준으로 쓰고, 파티션 최적화는 Iceberg가 해석한다

예를 들어 아래처럼 테이블을 정의한다고 하자.

```sql
CREATE TABLE lake.analytics.user_events (
  event_id STRING,
  tenant_id BIGINT,
  user_id BIGINT,
  event_type STRING,
  event_time TIMESTAMP,
  payload STRING
)
USING iceberg
PARTITIONED BY (
  days(event_time),
  bucket(tenant_id, 32)
);
```

사용자는 보통 이렇게 조회한다.

```sql
SELECT count(*)
FROM lake.analytics.user_events
WHERE event_time >= TIMESTAMP '2026-04-01 00:00:00'
  AND event_time < TIMESTAMP '2026-04-02 00:00:00'
  AND tenant_id = 42;
```

중요한 점은 쿼리가 `days(event_time)`나 `bucket(tenant_id, 32)`를 직접 참조하지 않는다는 것이다.
Iceberg가 메타데이터를 통해 **해당 필터를 파티션 프루닝으로 해석**한다.

이게 hidden partitioning의 실질적 장점이다.

- 쿼리가 파티션 물리 구조에 덜 결합된다
- 파티션 전략을 바꿔도 애플리케이션 쿼리 수정량이 줄어든다
- 엔진마다 파티션 컬럼 이름을 따로 맞추는 부담이 줄어든다

### 파티션 컬럼을 노출하지 않는다고 파티션 설계가 덜 중요해지는 것은 아니다

여기서 자주 하는 착각이 있다.

> "Hidden partitioning이 있으니 파티션은 대충 잡아도 된다"

전혀 아니다. hidden partitioning은 **쿼리와 물리 레이아웃 결합을 줄여주는 기능**이지, 잘못된 파티션 전략을 자동으로 구해주지 않는다.

여전히 아래 질문이 중요하다.

- 시간 축 필터가 대부분인가?
- tenant 단위 격리가 중요한가?
- append-only인가, upsert/delete가 많은가?
- late data가 자주 들어오는가?
- 읽기 패턴이 시간 범위 중심인가, tenant + id lookup 중심인가?

즉 파티션은 여전히 중요하지만, **변경 가능성과 쿼리 독립성이 높아진다**는 점이 Iceberg의 차별점이다.

---

## 핵심 개념 3: Partition Evolution은 "새 테이블 생성" 대신 메타데이터 변경으로 해결한다

운영이 오래된 데이터 레이크에서 자주 마주치는 상황은 이렇다.

- 초기에 일 단위 partition이면 충분했다
- 데이터량이 늘면서 특정 날짜 파티션이 너무 커졌다
- 시간 단위나 bucket 전략을 추가해야 한다
- 하지만 기존 쿼리와 적재 로직, 다운스트림 파이프라인이 너무 많아 전면 마이그레이션이 부담스럽다

Hive 스타일에서는 보통 새 테이블을 만들고 데이터를 옮기는 방식으로 해결했다. Iceberg는 여기서 훨씬 유연하다.

### Partition Evolution의 핵심

Iceberg에서는 기존 데이터는 기존 partition spec으로 남겨두고, **새로 쓰이는 데이터만 새 partition spec으로 저장**할 수 있다.

즉 아래 같은 변화가 가능하다.

- 1단계: `days(event_time)`
- 2단계: `hours(event_time), bucket(tenant_id, 32)`

이 변경이 가능한 이유는 쿼리가 특정 디렉터리 구조를 직접 참조하지 않고, Iceberg 메타데이터가 **각 snapshot/manifest가 어떤 partition spec으로 기록됐는지** 알고 있기 때문이다.

### 실무 의미: "오늘부터 새 레이아웃"이 가능해진다

예전 방식에서는 시간 단위 분할이 필요해지면 다음이 필요했다.

- 새 테이블 생성
- 과거 데이터 재적재 또는 이중 운영
- 쿼리 수정
- 메타스토어/ETL 코드 수정
- 다운스트림 영향 점검

Iceberg에서는 더 현실적인 선택이 가능하다.

- 기존 데이터는 일 단위 그대로 둔다
- 특정 시점 이후 신규 데이터만 시간 단위로 쓴다
- 쿼리는 계속 원본 컬럼 기준으로 유지한다

이 차이는 운영 비용에서 매우 크다.

### 다만 split planning 비용과 운영 복잡도는 남는다

Partition evolution이 마법은 아니다. 이전 spec과 새로운 spec이 공존하면 planning 단계에서 각 레이아웃을 따로 고려해야 한다. 즉 장점만 있는 것은 아니다.

실무적으로는 아래를 함께 고려해야 한다.

- 너무 자주 spec을 바꾸지 말 것
- spec 변경 이유를 명확히 문서화할 것
- 변경 이후 쿼리 패턴이 실제로 개선되는지 측정할 것
- 과거 데이터 재정리(backfill/compaction)가 필요한지 따져볼 것

즉 partition evolution은 "마이그레이션 비용 절감 도구"이지, **무한 자유 변경 기능**으로 보면 안 된다.

---

## 핵심 개념 4: Iceberg의 성능 문제는 생각보다 자주 "작은 파일"과 "메타데이터 비대화"에서 시작된다

Iceberg를 도입하면 테이블 관리가 좋아지지만, 그렇다고 운영 비용이 자동으로 사라지지는 않는다. 특히 스트리밍 적재나 마이크로배치가 많으면 가장 먼저 부딪히는 문제가 small files다.

### 왜 작은 파일이 문제인가

작은 파일이 많으면 단순 저장 용량만의 문제가 아니다.

- 파일 open cost가 늘어난다
- planning 시 읽어야 할 metadata 양이 커진다
- manifest 수가 늘어난다
- 엔진이 실제 데이터보다 메타데이터 처리에 더 많은 시간을 쓴다
- 병렬성은 좋아 보이지만 실제 스캔 효율은 나빠질 수 있다

예를 들어 초당 수천 건 이벤트를 1분 간격 마이크로배치로 계속 쓰면, 하루 수천~수만 개 데이터 파일이 생길 수 있다. 이 경우 쿼리 느림의 원인이 Parquet 인코딩이 아니라 **파일 개수와 manifest 트리**가 된다.

### Iceberg는 small files를 자동으로 없애주지 않는다

많이 하는 오해가 있다.

> "Iceberg가 알아서 최적 파일 크기를 맞춰줄 것이다"

일부 엔진/설정에서 write distribution이나 target file size를 활용할 수는 있지만, 스트리밍 환경에서는 여전히 small files가 누적되기 쉽다. 결국 **rewrite_data_files 같은 compaction 작업**이 필요해진다.

### 메타데이터도 함께 커진다

데이터 파일만 늘어나는 게 아니다.

- snapshot 수 증가
- manifest 수 증가
- metadata JSON history 증가
- delete file 증가

즉 운영자는 테이블 크기만 볼 게 아니라, **파일 수 / snapshot 수 / manifest 수 / metadata file growth**를 같이 봐야 한다.

이걸 놓치면 보통 아래 순서로 체감이 온다.

1. 처음엔 잘 된다
2. 어느 순간 planning latency가 길어진다
3. 같은 쿼리인데 스캔 시작까지 시간이 오래 걸린다
4. compaction 한 번 돌렸더니 갑자기 빨라진다
5. 그제서야 원인이 데이터량이 아니라 파일 수였다는 걸 알게 된다

---

## 핵심 개념 5: Row-level Update/Delete를 쓸수록 "delete file + rewrite 전략"을 이해해야 한다

Iceberg가 실무에서 매력적인 이유 중 하나는 MERGE, UPDATE, DELETE 같은 row-level operation을 지원한다는 점이다. 하지만 여기에는 중요한 전제가 있다.

### 모든 수정은 결국 파일 단위 비용으로 돌아온다

RDB처럼 row 하나를 제자리에서 바로 바꾸는 이미지로 생각하면 곤란하다. Iceberg는 기본적으로 immutable file 중심 설계에 가깝기 때문이다.

엔진과 포맷 버전에 따라 내부 동작은 다를 수 있지만, 실무 감각으로는 아래를 기억하면 된다.

- 일부 수정은 **영향받는 데이터 파일 재작성**으로 처리된다
- 일부 삭제는 **delete file**을 추가하는 방식으로 처리된다
- 이후 읽기 시 base data file + delete file을 함께 해석해야 할 수 있다
- delete file이 많아지면 읽기 비용이 증가한다

### CDC / upsert 워크로드에서 자주 생기는 일

예를 들어 주문 상태 변경 CDC를 Iceberg에 적재한다고 하자.

- 같은 `order_id`가 하루에도 여러 번 수정된다
- MERGE INTO를 자주 수행한다
- delete/late update가 섞인다

이 경우 처음에는 "Iceberg가 update를 지원하니 편하네" 정도로 느껴진다. 하지만 시간이 지나면 아래 문제가 생긴다.

- 영향을 받은 파일이 자주 재작성된다
- equality delete / position delete 파일이 누적된다
- 쿼리 시 merge-on-read 비용이 증가한다
- compaction/rewrite 주기를 설계하지 않으면 읽기 성능이 급격히 나빠진다

즉 row-level operation은 강력하지만, **update가 잦은 테이블을 RDB처럼 생각하면 안 된다**.

### 실무 질문은 "수정 가능하냐"가 아니라 "수정 비용을 감당할 워크로드냐"다

이게 중요하다.

- append-heavy 분석 테이블 → Iceberg와 매우 잘 맞음
- 늦게 들어오는 이벤트 보정 정도 → 충분히 잘 맞음
- 초당 빈번한 row update / point lookup 중심 OLTP → 대체로 맞지 않음

즉 Iceberg는 만능 저장소가 아니라, **분석형/레이크하우스형 테이블에서 row-level 변경을 현실적으로 다룰 수 있게 해주는 포맷**으로 보는 편이 정확하다.

---

## 실무 예시 1: 이벤트 로그 테이블을 Iceberg로 설계할 때의 기준

가장 흔한 케이스부터 보자.

상황은 아래와 같다.

- 모바일/웹 이벤트 로그 적재
- 대부분 append-only
- 조회는 최근 7일/30일 범위 + tenant 필터 중심
- 일부 late data 존재
- Spark로 적재, Trino로 조회

이 경우 보통 아래 같은 설계를 고려할 수 있다.

```sql
CREATE TABLE lake.analytics.user_events (
  event_id STRING,
  tenant_id BIGINT,
  user_id BIGINT,
  event_type STRING,
  event_time TIMESTAMP,
  ingest_time TIMESTAMP,
  payload STRING
)
USING iceberg
PARTITIONED BY (
  days(event_time),
  bucket(tenant_id, 32)
);
```

### 왜 이런 partition spec이 자주 무난한가

- `days(event_time)`
  - 시간 범위 조회가 대부분일 때 기본값으로 좋다
  - 일 단위 retention / backfill / snapshot 검증이 직관적이다

- `bucket(tenant_id, 32)`
  - 대규모 멀티테넌트에서 특정 tenant 쏠림을 완화하는 데 도움이 된다
  - 단순 `tenant_id` partition보다 파티션 폭발을 줄일 수 있다

### 하지만 이것도 workload에 따라 틀릴 수 있다

아래 상황이면 다시 봐야 한다.

- 하루 데이터가 너무 커서 일 파티션이 과도하게 무거움
- 시간 단위 대시보드 조회가 많음
- tenant 수가 적고 특정 대형 tenant가 대부분의 데이터를 차지함
- event_time late arrival이 심해서 날짜별 재적재가 잦음

이때는 `hours(event_time)` 또는 sort order 조정, write distribution 조정이 더 중요할 수 있다.

### 정렬 전략도 같이 봐야 한다

Iceberg에서는 partition만 보고 끝내기 쉽지만, 실제 스캔 효율은 sort order도 영향을 준다.

예를 들어 최근 시간 범위 조회가 많다면 아래처럼 정렬을 고려할 수 있다.

- `event_time ASC`
- `tenant_id ASC, event_time ASC`

특히 compaction 시 정렬 기준을 맞추면 파일 내부 데이터 locality가 좋아져 쿼리 성능에 도움이 될 수 있다.

핵심은 이것이다.

> 파티션은 "어느 파일을 볼지"를 줄이고,
> 정렬은 "파일 안에서 얼마나 효율적으로 읽을지"에 영향을 준다.

둘을 같이 봐야 한다.

---

## 실무 예시 2: CDC 기반 주문 상태 테이블에서 MERGE와 compaction을 어떻게 볼 것인가

다음 상황을 보자.

- Debezium CDC로 주문 변경 이벤트 수집
- 최신 주문 상태를 Iceberg 테이블에 유지
- 분석팀은 주문 상태/금액/상태 전이 시점을 조회
- 하루 동안 같은 `order_id`에 여러 번 업데이트 발생

이 경우 보통 staging 테이블을 거쳐 MERGE INTO를 사용하게 된다.

```sql
MERGE INTO lake.ods.orders_current t
USING lake.staging.orders_cdc s
ON t.order_id = s.order_id
WHEN MATCHED AND s.op = 'DELETE' THEN DELETE
WHEN MATCHED THEN UPDATE SET
  t.status = s.status,
  t.total_amount = s.total_amount,
  t.updated_at = s.updated_at
WHEN NOT MATCHED THEN INSERT *;
```

### 이 구조의 장점

- 최신 상태 테이블을 SQL 수준에서 비교적 명확하게 유지할 수 있다
- downstream 분석/집계가 쉬워진다
- overwrite 범위를 전체 테이블이 아니라 영향 파일로 줄일 수 있다

### 하지만 곧 나오는 비용

- 업데이트가 잦을수록 파일 재작성 비용 증가
- delete file 누적 가능성 증가
- 작은 마이크로배치 MERGE를 자주 돌리면 small files 악화
- 동일 파티션에 대한 지속적인 수정으로 metadata churn 증가

### 실무적으로 자주 쓰는 완화 전략

#### 1) 마이크로배치 크기를 너무 작게 잡지 않는다

1분 단위 MERGE가 멋져 보일 수는 있지만, 실제론 파일 수만 빠르게 늘릴 수 있다. 비즈니스 SLA가 허용한다면 5분, 10분, 15분 단위 묶음이 더 현실적일 수 있다.

#### 2) append raw + current snapshot 테이블을 분리한다

- `orders_cdc_raw`: append-only raw history
- `orders_current`: MERGE를 통해 최신 상태 유지

이렇게 나누면 원천 이력 보존과 최신 상태 조회를 분리할 수 있다.

#### 3) rewrite_data_files / rewrite_manifests를 정기 운영 작업으로 둔다

MERGE를 많이 쓰는 테이블은 사실상 maintenance plan이 없는 순간부터 성능 저하가 시작된다고 보는 편이 맞다.

---

## 실무 예시 3: Partition Evolution이 실제로 유용해지는 시점

초기에는 아래처럼 만들었다고 하자.

```sql
PARTITIONED BY (days(event_time))
```

그런데 6개월 뒤 다음 문제가 생긴다.

- 하루 데이터가 너무 많아 특정 날짜 쿼리가 여전히 무겁다
- 최근 24시간 대시보드가 많아 시간 단위 pruning이 더 유리하다
- tenant 쏠림이 심해 일부 파일이 지나치게 크다

이때 예전 방식이면 새 테이블을 파고 마이그레이션을 고민해야 한다. Iceberg에서는 보다 점진적인 대응이 가능하다.

예를 들면 이런 방향을 검토한다.

- 기존 데이터: `days(event_time)` 유지
- 신규 데이터: `hours(event_time), bucket(tenant_id, 32)` 추가

### 이 전략이 잘 맞는 경우

- 과거 데이터는 자주 안 읽고 최근 데이터 위주로 조회함
- 신규 유입량이 크고 최근 파티션 최적화 효과가 큼
- 전면 재마이그레이션 비용이 너무 큼

### 이 전략이 오히려 애매한 경우

- 과거 1년 데이터에 대한 반복 대규모 분석이 많음
- spec이 여러 번 바뀌어 planning 복잡성이 커짐
- 팀 내에 어떤 시점에 어떤 spec을 썼는지 이해가 약함

즉 partition evolution은 강력하지만, **"앞으로 들어오는 데이터의 물리 레이아웃을 개선하는 도구"**라고 보는 편이 좋다. 과거 데이터까지 모두 최적화하려면 결국 재적재나 대규모 rewrite가 필요할 수 있다.

---

## 운영 유지보수 1: Expire Snapshots를 안 하면 time travel이 아니라 메타데이터 부채가 쌓인다

Iceberg의 snapshot은 유용하지만 무한히 쌓아두면 비용이 된다.

### snapshot이 많아질수록 생기는 일

- metadata tree가 커진다
- planning 시 참고할 이력이 늘어난다
- 사용하지 않는 데이터 파일이 더 오래 남는다
- object storage 비용이 증가한다
- 운영자가 "어느 시점까지 되돌릴 수 있어야 하는가"를 통제하지 못한다

즉 snapshot 보존은 백업처럼 막연히 많이 남길수록 좋은 게 아니다. **복구 요구와 비용의 균형**이 필요하다.

### 실무 기준 질문

- 24시간 되돌리면 충분한가?
- 7일 time travel이 필요한가?
- 월말 정산용으로 특정 장기 보존 snapshot이 필요한가?
- 법적/감사 요구가 있는가?

이 질문에 답이 있어야 expire policy가 정해진다.

### 너무 공격적으로 지우면 안 되는 이유

반대로 retention을 너무 짧게 잡아도 위험하다.

- 늦게 발견된 데이터 오류를 되돌릴 수 없음
- 장시간 배치/쓰기 작업 중인 파일과 충돌 가능성
- 다운스트림 검증 전에 snapshot이 사라질 수 있음

즉 expire snapshots는 단순 청소가 아니라, **복구 가능 시간창과 비용을 정하는 운영 정책**이다.

---

## 운영 유지보수 2: Remove Orphan Files는 드물게 돌려도 되지만, 잘못 돌리면 더 위험하다

분산 처리 환경에서는 실패한 작업이 참조되지 않는 파일을 남길 수 있다. 이런 파일이 orphan file이다.

### orphan file이 생기는 대표 상황

- Spark job 실패 후 임시 파일 잔존
- writer가 파일을 만들었지만 commit 전 중단
- metadata에는 연결되지 않았지만 storage에는 파일이 남음

이 파일들은 snapshot expiration만으로 항상 정리되지 않는다. 그래서 주기적으로 orphan file cleanup이 필요할 수 있다.

### 하지만 retention을 너무 짧게 두면 위험하다

이건 문서에서도 강하게 경고하는 부분이다. 아직 완료되지 않은 write job의 파일을 orphan로 오인해 지워버리면 실제 테이블 손상으로 이어질 수 있다.

즉 remove orphan files는 아래 원칙이 중요하다.

- 충분히 긴 retention window 사용
- 장시간 실행되는 job 최대 소요시간을 고려
- object storage path 정규화/authority 변경 이슈 점검
- 스토리지 listing 비용까지 감안

즉 "더러운 파일이니 빨리 지우자" 접근은 위험하다.

---

## 운영 유지보수 3: Rewrite Data Files는 성능 최적화가 아니라 사실상 읽기 품질 유지 작업이다

small files가 누적되면 결국 compaction이 필요하다. Iceberg에서는 보통 `rewrite_data_files` 같은 작업이 여기에 해당한다.

### compaction이 해결하는 문제

- 작은 파일 여러 개를 더 큰 파일로 병합
- 파일 open cost 감소
- metadata overhead 감소
- delete file 적용 후 base file 재구성 기회 제공
- 정렬 기준 재적용 가능

### 하지만 compaction도 비용이 있다

- 계산 리소스를 사용한다
- rewrite 대상 파일을 다시 읽고 써야 한다
- 너무 자주 돌리면 쓰기 비용만 커진다
- 오브젝트 스토리지 PUT/GET 비용이 늘어난다

즉 compaction은 무조건 자주 돌리는 게 아니라, **작업 패턴과 쿼리 패턴이 만나는 지점**에서 설계해야 한다.

### 실무적으로 자주 쓰는 기준

- 일별/시간별 파티션당 파일 수가 임계치 초과
- 평균 파일 크기가 목표 파일 크기보다 현저히 작음
- CDC/merge 이후 delete file이 많이 쌓임
- 대시보드/집계 쿼리 planning time이 증가

### 무차별 전 테이블 compaction은 대개 비효율적이다

예를 들어 최근 3일만 자주 조회되고 오래된 데이터는 거의 안 본다면, 모든 파티션을 매번 compaction할 필요는 없다.

더 현실적인 접근은 아래다.

- 최근 핫 파티션 위주 compaction
- 파일 수/크기 기준 임계치 기반 실행
- 대용량 파티션만 선택적 rewrite
- 배치 완료 직후 또는 야간 maintenance 윈도우 활용

즉 compaction은 "예쁘게 정리"가 아니라, **실제 hot partition의 읽기 비용을 통제하는 작업**이어야 한다.

---

## 운영 유지보수 4: Rewrite Manifests는 데이터보다 planning을 빠르게 만들기 위한 메타데이터 최적화다

운영하다 보면 데이터 파일 크기는 적절한데도 planning latency가 길어지는 경우가 있다. 이때 놓치기 쉬운 게 manifest 구조다.

### manifest가 중요한 이유

Iceberg는 어떤 데이터 파일들이 어떤 partition/spec/statistics를 갖는지 manifest에 기록한다. 즉 manifest는 단순 보조 파일이 아니라, **쿼리 planning 시 읽는 인덱스 계층**에 가깝다.

### write pattern과 read pattern이 어긋나면 manifest도 비효율적이 된다

예를 들어 쓰기는 tenant 혼합 마이크로배치로 들어오는데, 읽기는 항상 최근 날짜 범위 + tenant 기준으로 일어난다면 manifest grouping이 비효율적일 수 있다.

이 경우 데이터 파일 수만 줄이는 것보다, manifest rewrite가 planning 개선에 더 직접적일 수 있다.

### 언제 고려할까

- 파일 수 자체보다 planning time이 비정상적으로 긴 경우
- write pattern과 read filter가 자주 어긋나는 경우
- streaming append 후 manifest가 지나치게 파편화된 경우

즉 manifest rewrite는 자주 하는 기본 작업은 아닐 수 있지만,
**데이터 파일만 보고 설명되지 않는 planning 병목**이 있을 때 중요한 카드다.

---

## 핵심 개념 6: Schema Evolution은 "컬럼 이름 변경"이 아니라 필드 ID 기반 계약 관리다

Iceberg를 운영하다 보면 partition 못지않게 중요한 것이 schema evolution이다. 특히 데이터 플랫폼이 커질수록 아래 변화가 계속 발생한다.

- 새 분석 지표 컬럼 추가
- nested struct 내부 필드 확장
- 잘못 지은 컬럼명 rename
- 타입 widening
- nullable 정책 조정

기존 파일 기반 테이블 운영에서는 이런 변경이 생각보다 위험했다.

- 이름 기반으로 컬럼을 맞추다가 같은 이름 재사용이 사고를 만듦
- 위치 기반 포맷에서는 컬럼 추가/삭제 시 해석이 꼬일 수 있음
- 일부 엔진/테이블 형식은 rename가 사실상 drop + add처럼 동작해 하위 호환성이 약함

Iceberg가 여기서 주는 핵심 장점은 **필드 ID 기반 추적**이다. 즉 컬럼이 이름이나 위치보다 더 안정적인 식별자로 관리된다.

### 왜 이게 실무적으로 중요한가

예를 들어 `customer_id`라는 컬럼명을 `user_id`로 바꾸고 싶다고 하자. 이름만 보면 단순 rename 같지만, 분석 파이프라인과 BI, downstream job 관점에서는 꽤 민감한 변경이다.

Iceberg에서는 schema evolution 자체를 메타데이터 변경으로 상대적으로 안전하게 처리할 수 있다. 하지만 여기서 중요한 건 "기술적으로 rename이 가능하다"가 아니라, 아래 운영 질문이다.

- 과거 데이터를 읽는 엔진이 모두 rename 이후 스키마를 잘 해석하는가?
- downstream SQL/뷰/대시보드가 컬럼명 변경을 흡수할 준비가 되었는가?
- rename를 바로 할지, 새 컬럼 추가 후 점진 마이그레이션할지 결정했는가?

즉 Iceberg가 schema evolution을 쉽게 해준다고 해서, **데이터 계약 변경의 조직 비용까지 없애주지는 않는다**.

### 운영 기준: 기술적으로 가능한 변경과, 실제로 안전한 변경은 다르다

실무에서는 다음 정도로 나눠 생각하는 편이 좋다.

#### 상대적으로 안전한 변경

- nullable 신규 컬럼 추가
- nested struct 내부의 선택적 필드 추가
- 타입 widening(예: int → long 등 엔진 호환 범위 내)
- 설명용 metadata/property 추가

#### 더 신중해야 하는 변경

- 컬럼 rename
- 의미가 달라지는 rename
- 필드 삭제
- enum-like 문자열 값의 해석 변경
- 타입 narrowing 또는 의미가 달라지는 type migration

즉 Iceberg의 schema evolution은 강력하지만, **물리 파일 재작성 비용이 낮아졌다고 계약 변경 비용까지 낮아진 것은 아니다**.

---

## 핵심 개념 7: 동시성은 snapshot isolation 비슷하게 보이지만, 충돌 모델을 이해해야 운영 사고가 줄어든다

Iceberg의 commit 모델은 매우 강력하지만, 여러 writer가 동시에 같은 테이블에 쓰기 시작하면 반드시 동시성 설계를 해야 한다.

### 기본 감각: optimistic concurrency

Iceberg는 보통 "내가 읽은 현재 테이블 상태를 기준으로 새 snapshot을 만들고, commit 시점에 그 전제가 아직 유효한지 확인"하는 optimistic concurrency 모델로 이해하면 쉽다.

즉 writer A와 writer B가 동시에 작업할 때,

- 둘 다 같은 현재 snapshot을 기준으로 계획할 수 있고
- 먼저 commit한 쪽이 새 snapshot을 만든 뒤
- 나중 writer는 자신이 계산한 전제가 더 이상 맞지 않아 commit conflict를 만날 수 있다

이건 이상 동작이 아니라 정상이다.

### 충돌이 많이 나는 대표 패턴

#### 1) 같은 핫 파티션에 여러 배치가 겹침

예를 들어 최근 1시간 파티션에 대해 아래 작업이 동시에 일어나는 경우다.

- 스트리밍 append
- CDC merge
- compaction
- backfill overwrite

모두 같은 파일 집합을 만질 가능성이 높다. 이 경우 재시도만으로 해결될 수는 있어도, 비용과 지연이 커진다.

#### 2) 넓은 범위 overwrite

`INSERT OVERWRITE`나 대규모 rewrite가 너무 넓은 범위를 건드리면, 사소한 concurrent write와도 충돌 가능성이 급격히 커진다.

#### 3) maintenance job이 업무 적재 시간과 겹침

야간 compaction이 안전할 거라 생각했는데 실제 트래픽 피크가 새벽에 몰린다면, compaction과 ingestion이 계속 충돌할 수 있다.

### 실무 대응 기준

- append / merge / compaction / backfill의 시간대를 분리한다
- overwrite 범위를 가능한 좁게 잡는다
- hot partition과 cold partition maintenance를 분리한다
- retry는 두되, "왜 계속 충돌하는가"를 구조적으로 본다
- ingestion과 maintenance를 같은 풀에서 무한 경쟁시키지 않는다

즉 Iceberg 동시성에서 중요한 것은 락 튜닝보다,
**같은 파일 집합을 동시에 건드리는 작업을 운영 레벨에서 얼마나 잘 분리했는가**다.

---

## 실무 예시 4: Backfill과 운영 적재를 같은 테이블에서 동시에 돌릴 때의 기준

데이터 플랫폼 운영에서 backfill은 피할 수 없다.

- 코드 버그 수정 후 지난 14일 재계산
- 신규 컬럼 추가 후 과거 데이터 보정
- 이벤트 정정분 반영
- 삭제/비식별화 요청 재처리

문제는 backfill이 그냥 "예전 날짜 다시 쓰기"가 아니라, **현재 운영 ingestion과 같은 테이블에서 경쟁하는 또 하나의 writer**라는 점이다.

### 위험한 패턴

- 운영 append가 계속 들어오는 테이블에 대해 대규모 overwrite 실행
- 최근 핫 파티션까지 포함한 backfill을 낮 시간대에 수행
- 어떤 날짜 범위를 누가 덮는지 runbook 없이 수동 실행
- backfill 후 검증 없이 바로 downstream 공개

### 더 안전한 패턴

#### 1) cold partition부터 분리 실행

최근 1~2일처럼 핫한 파티션은 운영 적재와 충돌 가능성이 높다. 먼저 오래된 cold partition을 재작성하고, 핫 파티션은 별도 maintenance window에 다루는 편이 안전하다.

#### 2) write-audit-publish 또는 branch 기반 검증 흐름 검토

카탈로그와 엔진이 지원한다면 branch/WAP 패턴을 활용해 검증 후 publish하는 모델이 유용할 수 있다. 다만 이 기능은 엔진/카탈로그 지원 차이가 있으므로 "Iceberg니까 된다"고 단정하면 안 된다. 반드시 실제 사용 엔진에서 검증해야 한다.

#### 3) backfill도 snapshot 단위로 검증

backfill 이후 바로 수치만 보는 것이 아니라,

- row count
- distinct key 수
- 주요 metric 합계
- 특정 기간 time travel 비교

를 snapshot 기준으로 검증하면 훨씬 안전하다.

즉 backfill의 핵심은 데이터를 다시 쓰는 기술이 아니라,
**운영 적재와 충돌하지 않게 새 snapshot을 만들고 검증하는 절차**에 있다.

---

## 운영 대시보드에서 실제로 봐야 하는 지표

Iceberg 운영은 쿼리 응답 시간만 보면 늦다. 원인을 미리 잡으려면 테이블 상태 자체를 봐야 한다.

### 최소한 봐야 할 것

#### 1) 파티션별 파일 수

- 최근 1일/3일/7일 hot partition의 파일 수
- 특정 partition만 비정상적으로 파일이 많은지

이 지표는 compaction 필요성을 가장 빨리 알려준다.

#### 2) 평균/중앙 파일 크기

- target file size 대비 얼마나 작은가
- merge 이후 파일 크기가 급격히 작아지지 않았는가

#### 3) snapshot 증가 속도

- 하루 commit 수
- snapshot retention 내 총 snapshot 수
- streaming job 재시작 후 snapshot churn 급증 여부

#### 4) planning latency

실제 쿼리 엔진 관점에서 매우 중요하다. 데이터 스캔 시간이 아니라 **쿼리 시작까지 준비 시간**이 길어지고 있다면 manifest/metadata 문제가 원인일 수 있다.

#### 5) delete file 비율

row-level delete/merge를 많이 쓰는 테이블이라면 delete file 누적 정도가 읽기 성능 저하를 잘 설명한다.

#### 6) metadata file 증가량

잦은 commit 환경에서는 data file보다 metadata file growth가 먼저 운영 신호가 되기도 한다.

### 추가로 보면 좋은 것

- commit conflict/retry 횟수
- orphan cleanup 대상 파일 추정량
- compaction 전후 file count 감소율
- 쿼리 패턴별 스캔 파일 수
- hot partition skew

즉 Iceberg 운영 대시보드는 "용량"보다 먼저,
**파일 수·메타데이터 수·commit 빈도·planning 시간**을 보게 만드는 편이 좋다.

---

## 비교 관점: Iceberg vs Delta vs Hudi를 어떻게 볼 것인가

실무에서 자주 나오는 질문이 이것이다.

> 결국 Iceberg, Delta Lake, Hudi 중 뭘 써야 하나?

정답 암기는 어렵지만, 아래 기준으로 보면 판단이 좀 쉬워진다.

### Iceberg가 특히 매력적인 지점

- 엔진 중립성에 대한 기대가 큼
- hidden partitioning과 partition evolution 설계가 깔끔함
- 대규모 분석 테이블과 메타데이터 관리가 강점
- multi-engine lakehouse 표준 느낌으로 가져가기 좋음

### Delta Lake가 자주 강한 지점

- Databricks/Spark 중심 생태계 일체감
- 운영 경험과 기능 통합이 강함
- 특정 환경에서는 성숙한 UX와 성능 최적화 도구가 좋음

### Hudi가 자주 논의되는 지점

- record-level upsert/incremental processing 요구가 강한 환경
- near-real-time ingestion 패턴
- 특정 CDC/업데이트 중심 워크로드 최적화 경험

### 그래서 실무 질문은 이렇게 바뀌는 편이 낫다

- 우리는 multi-engine가 중요한가, 특정 엔진 최적화가 중요한가?
- append-heavy 분석 테이블이 중심인가, upsert-heavy 테이블이 중심인가?
- 운영팀이 어떤 생태계에 익숙한가?
- catalog, governance, security까지 포함한 표준을 어디에 둘 것인가?

즉 "누가 더 좋냐"보다,
**우리 조직의 엔진 표준, 업데이트 패턴, 운영 역량에 어떤 포맷이 더 맞는가**로 판단해야 한다.

---

## Spark 기준으로 자주 보는 운영 SQL/프로시저 예시

아래는 개념을 잡기 위한 예시다. 실제 문법은 catalog 설정과 엔진 버전에 따라 조금 다를 수 있지만, 운영 감각은 비슷하다.

### 1) 테이블 생성

```sql
CREATE TABLE prod.analytics.user_events (
  event_id STRING,
  tenant_id BIGINT,
  user_id BIGINT,
  event_type STRING,
  event_time TIMESTAMP,
  payload STRING
)
USING iceberg
PARTITIONED BY (
  days(event_time),
  bucket(tenant_id, 32)
);
```

### 2) CDC/upsert성 적재

```sql
MERGE INTO prod.analytics.orders_current t
USING prod.staging.orders_delta s
ON t.order_id = s.order_id
WHEN MATCHED AND s.op = 'DELETE' THEN DELETE
WHEN MATCHED THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *;
```

### 3) snapshot 만료

```sql
CALL prod.system.expire_snapshots(
  table => 'analytics.user_events',
  older_than => TIMESTAMP '2026-03-27 00:00:00'
);
```

### 4) 데이터 파일 재작성(compaction)

```sql
CALL prod.system.rewrite_data_files(
  table => 'analytics.user_events'
);
```

### 5) orphan file 삭제

```sql
CALL prod.system.remove_orphan_files(
  table => 'analytics.user_events'
);
```

실무에서는 이걸 그대로 주기 실행하기보다, 보통 아래 조건을 붙인다.

- 특정 파티션만 대상
- target file size 지정
- 최근 N일 데이터만 대상
- 사전/사후 metrics 검증

핵심은 SQL 문법 암기가 아니라,
**어떤 maintenance가 어떤 문제를 해결하는지 구분하는 것**이다.

---

## 트레이드오프 1: Iceberg는 Hive-style 테이블보다 유연하지만, 운영 계층이 더 중요해진다

Iceberg의 큰 장점은 분명하다.

### 장점

- snapshot 기반 원자적 테이블 상태 관리
- hidden partitioning으로 쿼리와 물리 레이아웃 결합 완화
- partition evolution 가능
- schema evolution이 비교적 안전함
- 엔진 간 메타데이터 공유 용이
- row-level delete/merge 같은 현대적 lakehouse 기능 지원

### 비용

- maintenance 작업을 설계해야 한다
- metadata 구조를 이해해야 한다
- small files / manifests / delete files를 관측해야 한다
- catalog 운영과 권한 모델이 중요해진다
- 엔진별 기능 지원 차이를 이해해야 한다

즉 Hive-style보다 "좋다"기보다는,
**테이블 운영을 더 명시적으로 해야 하는 대신 더 안전하고 유연해진다**고 보는 편이 맞다.

---

## 트레이드오프 2: Append-heavy 워크로드에는 매우 강하지만, OLTP처럼 자주 수정되는 테이블에는 한계가 있다

Iceberg를 처음 성공적으로 도입한 팀은 종종 모든 데이터 문제에 Iceberg를 적용하고 싶어 한다. 하지만 workload 적합성을 구분해야 한다.

### 잘 맞는 경우

- 이벤트 로그
- 분석용 fact 테이블
- 배치/스트리밍 적재 기반 데이터 마트
- CDC 기반 ODS/중간 적재층
- time travel / rollback / reproducibility가 중요한 분석 테이블

### 덜 맞는 경우

- 초당 고빈도 point update가 필요한 테이블
- 낮은 지연의 단건 조회/수정이 핵심인 서비스 저장소
- lock/transaction semantics가 OLTP 수준으로 중요한 업무 DB

즉 Iceberg는 "RDB 대체재"가 아니라,
**분석 지향 테이블에 업데이트와 운영 기능을 더해주는 포맷**이다.

---

## 트레이드오프 3: Partition Evolution은 유연하지만, 무분별한 spec 변경은 미래의 복잡성을 산다

Partition evolution은 강력하다. 하지만 바꿀 수 있다고 자주 바꾸면 안 된다.

### 좋은 변화

- 데이터량 증가로 기존 일 파티션이 너무 큰 경우
- 최근 조회 패턴이 명확히 시간 단위로 이동한 경우
- tenant skew 완화를 위해 bucket을 추가할 필요가 있는 경우

### 나쁜 변화

- 단기 실험성 성능 이슈에 즉흥 대응
- 문서화 없이 spec 변경 반복
- 팀원 다수가 현재 spec/history를 모르는 상태
- 과거 데이터와 신규 데이터 간 성능 차이를 검증하지 않은 상태

즉 partition evolution은 **계획된 변화**일 때 강력하고,
무계획 변화일 때는 메타데이터만 복잡하게 만들 수 있다.

---

## 흔한 실수 1: 파티션을 "날짜 컬럼 그대로"만 생각한다

Iceberg를 도입해도 여전히 기존 감각대로 `dt STRING` 파티션만 고정적으로 생각하는 팀이 많다. 물론 틀린 건 아니지만 최선은 아닐 수 있다.

예를 들어 timestamp 원본 컬럼이 있다면 아래를 먼저 생각해야 한다.

- 실제 조회는 일 단위인가, 시간 단위인가?
- late data가 많아 event_time 파티션이 자주 흔들리는가?
- ingest time과 event time 중 무엇이 운영상 더 안정적인가?

즉 Iceberg에서는 hidden partitioning과 transform 기반 partition spec을 활용해 더 정교하게 설계할 수 있다. 단순 문자열 날짜 컬럼에만 기대면 장점을 반쯤 버리는 셈이다.

---

## 흔한 실수 2: 스트리밍 적재를 붙인 뒤 compaction을 나중 문제로 미룬다

처음에는 쿼리가 잘 되니까 maintenance를 뒤로 미루기 쉽다. 하지만 Iceberg에서 small files는 대개 "언젠가 해결할 문제"가 아니라 **초기부터 설계해야 할 문제**다.

특히 아래 조합이면 거의 확정적으로 maintenance가 필요하다.

- 짧은 마이크로배치
- append 빈도 높음
- CDC/merge 혼합
- 조회 엔진이 Trino/Spark 등 여러 개
- 최근 데이터 조회 비중 높음

이 경우 compaction 주기, 대상 파티션, 목표 파일 크기, maintenance 실행 시간대를 초기에 정하는 편이 훨씬 낫다.

---

## 흔한 실수 3: snapshot을 많이 남기면 무조건 안전하다고 생각한다

snapshot은 복구에 도움 되지만, 무한 보존이 정답은 아니다.

- 비용 증가
- planning 복잡도 증가
- metadata 비대화
- 운영자가 실제 보존 정책을 모르는 상태 발생

즉 snapshot은 "많이 남길수록 좋다"가 아니라,
**어느 정도의 rollback/time travel 창이 필요한가를 정책으로 정해야 한다**.

---

## 흔한 실수 4: orphan file 삭제를 과감하게 짧은 retention으로 실행한다

스토리지 비용이 아깝다고 orphan cleanup을 공격적으로 돌리면, 아직 완료되지 않은 write 작업 파일을 잘못 지울 위험이 있다. 이건 최악의 경우 실제 데이터 손상으로 이어진다.

즉 orphan cleanup은 비용 절감 스크립트가 아니라,
**진행 중 작업과 충돌하지 않도록 충분한 안전 마진을 둔 유지보수 작업**이다.

---

## 흔한 실수 5: MERGE INTO를 RDB UPDATE처럼 생각한다

Iceberg의 MERGE는 강력하지만, 공짜가 아니다.

- 영향을 받은 파일 rewrite 비용
- delete file 누적
- metadata churn 증가
- 작은 배치에서 성능 악화

즉 "SQL 문법이 UPDATE처럼 보여서 OLTP처럼 자주 써도 되겠지"라는 감각이 위험하다.

분석 테이블 관점에서는 아래 질문이 더 중요하다.

- 얼마나 자주 merge할 것인가?
- 한 번에 얼마나 묶어서 merge할 것인가?
- raw history와 current snapshot 테이블을 분리할 것인가?
- merge 후 compaction/rewrite를 어떻게 운영할 것인가?

---

## 흔한 실수 6: 엔진 지원 차이를 무시한다

Iceberg는 공통 포맷이지만, 엔진별 지원 기능과 성숙도가 완전히 동일하지는 않다.

예를 들어 실무에서 자주 확인해야 하는 것은 아래다.

- Spark에서 MERGE/DELETE/UPDATE 지원 수준
- Trino에서 row-level delete, branching, maintenance 지원 수준
- Flink streaming write와 snapshot/commit 상호작용
- catalog 구현(Hive Catalog, REST Catalog, Nessie 등) 차이

즉 설계 문서에는 "Iceberg 지원" 한 줄이 아니라,
**어떤 엔진이 어떤 쓰기/조회/유지보수 책임을 맡는지**까지 있어야 한다.

---

## 설계 체크리스트: 새 Iceberg 테이블 만들기 전에 물어볼 것

### 1) 워크로드 적합성

- [ ] 이 테이블은 append-heavy인가, update-heavy인가?
- [ ] point lookup보다 범위 스캔/집계가 주 용도인가?
- [ ] Iceberg가 진짜 맞는 문제인가, 아니면 RDB/OLTP 저장소가 더 맞는가?

### 2) 스키마와 파티션

- [ ] 주 쿼리 필터가 시간 범위인가, tenant인가, 둘 다인가?
- [ ] `days`, `hours`, `bucket`, `truncate` 중 어떤 transform이 맞는가?
- [ ] event_time 기준이 맞는가, ingest_time 기준이 더 안정적인가?
- [ ] 미래에 partition evolution 가능성이 높은가?

### 3) 적재 패턴

- [ ] append-only인가, merge/delete가 많은가?
- [ ] 마이크로배치 주기는 몇 분이 적절한가?
- [ ] small files를 초기에 줄일 write 설정이 있는가?
- [ ] raw history와 current state 테이블을 분리할 필요가 있는가?

### 4) 유지보수

- [ ] snapshot expiration 정책이 정해져 있는가?
- [ ] compaction 기준(파일 수, 평균 크기, 핫 파티션)이 있는가?
- [ ] orphan file cleanup retention이 안전한가?
- [ ] manifest rewrite가 필요한 병목인지 측정 지표가 있는가?

### 5) 관측성

- [ ] 파티션별 파일 수를 보는가?
- [ ] 평균 파일 크기를 모니터링하는가?
- [ ] snapshot 수, metadata size, planning latency를 보는가?
- [ ] merge 이후 delete file 증가량을 보는가?

### 6) 운영 책임

- [ ] 어떤 엔진이 write를 담당하는가?
- [ ] 어떤 엔진이 maintenance를 담당하는가?
- [ ] catalog와 권한 정책은 어떻게 나누는가?
- [ ] rollback/runbook이 문서화돼 있는가?

---

## 운영 체크리스트: 이미 쓰고 있는 Iceberg 테이블에서 점검할 것

- [ ] 최근 7일 기준 파티션당 파일 수가 과도하게 늘지 않았는가?
- [ ] 쿼리 느림의 원인이 데이터량이 아니라 planning/metadata overhead는 아닌가?
- [ ] snapshot retention이 비즈니스 복구 요구와 맞는가?
- [ ] compaction이 전 테이블 일괄 실행으로 낭비되고 있지 않은가?
- [ ] MERGE 워크로드가 지나치게 잦아 small files를 만드는 구조는 아닌가?
- [ ] partition spec 변경 이력이 팀에 공유돼 있는가?
- [ ] orphan cleanup을 너무 짧은 retention으로 돌리고 있지 않은가?
- [ ] raw history, curated mart, current state 역할이 테이블별로 분리돼 있는가?

---

## 도입 판단 한 줄 가이드

상황별로 아주 거칠게 정리하면 다음에 가깝다.

### Iceberg가 특히 잘 맞는 경우

- 객체 스토리지 기반 데이터 레이크를 테이블처럼 관리하고 싶다
- Spark/Trino/Flink 등 여러 엔진이 같은 데이터를 읽고 쓴다
- schema/partition 변경이 장기적으로 불가피하다
- snapshot/time travel/rollback이 운영적으로 유용하다
- CDC·late data·upsert를 분석 테이블 수준에서 다뤄야 한다

### 조금 더 신중해야 하는 경우

- 매우 잦은 단건 업데이트가 핵심이다
- 운영팀이 maintenance와 catalog 관리까지 맡을 준비가 안 돼 있다
- 단순 append 로그 저장만 필요한데 굳이 복잡한 테이블 기능이 필요하지 않다
- 엔진별 지원 차이를 감당할 조직적 표준이 아직 없다

즉 Iceberg는 최신 유행이라서 도입하는 게 아니라,
**테이블 메타데이터와 운영 문제를 파일 시스템 레벨이 아니라 테이블 포맷 레벨에서 해결하고 싶을 때** 선택하는 것이 맞다.

---

## 한 줄 정리

Apache Iceberg의 핵심은 "Parquet를 더 잘 저장하는 법"이 아니라, **snapshot·hidden partitioning·partition evolution·maintenance를 통해 객체 스토리지 위의 데이터를 장기 운영 가능한 테이블로 바꾸는 것**이다.
