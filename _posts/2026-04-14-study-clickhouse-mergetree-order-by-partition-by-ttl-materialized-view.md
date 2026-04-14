---
layout: post
title: "ClickHouse 실전: MergeTree, ORDER BY, PARTITION BY, TTL, Materialized View로 빠른 분석과 운영 비용을 함께 설계하는 법"
date: 2026-04-14 11:40:00 +0900
categories: [data-infra]
tags: [study, data-infra, clickhouse, mergetree, order-by, partitioning, ttl, materialized-view, analytics]
permalink: /data-infra/2026/04/14/study-clickhouse-mergetree-order-by-partition-by-ttl-materialized-view.html
---

## 배경: 분석 쿼리는 느린데, 데이터 플랫폼 비용은 왜 더 빨리 늘어날까?

서비스가 작을 때는 PostgreSQL 하나로도 웬만한 리포트가 나온다. 주문 수, 가입 전환율, 결제 실패율 정도는 인덱스 몇 개와 배치 테이블만으로도 버틴다. 그런데 데이터가 쌓이고 조회 패턴이 다양해지기 시작하면 문제의 종류가 바뀐다.

- 운영 DB에 분석 쿼리가 붙으면서 CPU와 I/O가 흔들린다
- 집계용 복제 DB를 따로 두었는데도 특정 대시보드가 수십 초씩 걸린다
- ELK, BigQuery, Redshift, Athena, Spark가 섞이면서 쿼리는 빨라졌지만 비용과 파이프라인 복잡도가 커진다
- 이벤트 로그는 빠르게 쌓이는데, 팀은 여전히 `GROUP BY` 몇 개 돌리는 데 시간을 쓴다
- "실시간 대시보드"를 원해서 파이프라인을 키웠는데, 정작 가장 비싼 것은 실시간이 아니라 잘못 설계된 저장 레이아웃이다

이 시점에서 많은 팀이 묻는다.

- ClickHouse를 붙이면 진짜 빨라지는가?
- 그냥 컬럼형 DB라서 빠른 것인가, 아니면 테이블 설계가 핵심인가?
- `ORDER BY`, `PARTITION BY`, TTL, Materialized View는 각각 어떤 역할인가?
- 왜 어떤 팀은 ClickHouse에서 1초 미만으로 집계를 하고, 어떤 팀은 insert 지연과 merge 지옥을 겪는가?
- ReplacingMergeTree, SummingMergeTree, AggregatingMergeTree 같은 엔진은 언제 쓰고 언제 피해야 하는가?

실무에서 ClickHouse의 핵심은 "컬럼형이라 빠르다"가 아니다. 더 정확히는 **조회 패턴에 맞게 데이터를 어떻게 쌓고, 어떤 단위로 묶고, 언제 자동 정리하고, 어디까지 미리 집계할 것인가**를 설계하는 데 있다.

오늘 글은 ClickHouse 소개가 아니라, **MergeTree 계열을 운영 가능한 수준으로 설계하기 위한 기준**을 정리한다. 특히 중급 이상 개발자가 자주 부딪히는 다섯 가지 질문에 답하는 것이 목표다.

1. `ORDER BY`는 왜 일반 RDB의 인덱스 감각으로 보면 계속 틀리게 설계되는가?
2. `PARTITION BY`는 조회 최적화용인가, 수명주기 관리용인가?
3. 작은 insert가 왜 merge 지옥과 쿼리 성능 저하로 이어지는가?
4. TTL은 삭제 설정이 아니라 어떤 운영 정책의 표현인가?
5. Materialized View는 캐시가 아니라 어떤 파이프라인 경계로 이해해야 하는가?

결론부터 말하면, ClickHouse는 쿼리 엔진만 잘 고르는 문제보다 **테이블 물리 레이아웃을 비즈니스 조회 패턴과 맞추는 문제**에 가깝다. 이 감각을 놓치면 ClickHouse는 매우 빠른 분석 엔진이 아니라, 매우 빠르게 복잡해지는 저장소가 된다.

---

## 먼저 큰 그림: ClickHouse는 "빠른 SQL 서버"가 아니라 읽기 경로를 강하게 의식한 컬럼형 저장 엔진이다

ClickHouse를 PostgreSQL이나 MySQL처럼 이해하고 들어가면 금방 어긋난다. 이유는 저장 방식과 읽기 경로가 다르기 때문이다.

관계형 OLTP DB가 보통 아래를 우선한다면,

- 개별 row 읽기/수정
- 짧은 트랜잭션
- 강한 제약조건과 동시성 제어
- 인덱스를 통한 row 탐색

ClickHouse는 보통 아래를 우선한다.

- 대량 append insert
- 큰 범위 scan과 aggregation
- 컬럼 단위 압축과 선택적 읽기
- 데이터 파트(part) 단위 관리
- 정렬 키와 파티션을 이용한 읽기 범위 축소

즉 ClickHouse는 "행 하나 빨리 찾기"보다 **많은 데이터를 읽더라도 덜 읽고, 읽은 뒤 빠르게 집계하는 데 최적화**되어 있다.

이 차이를 실제로 만들고 유지하는 핵심이 MergeTree 계열이다. MergeTree를 이해할 때 꼭 잡아야 하는 개념은 아래다.

- 데이터는 한 번에 큰 덩어리인 part로 쌓인다
- part 내부는 `ORDER BY` 기준으로 정렬된다
- 정렬된 데이터 위에 sparse primary index가 붙는다
- 파티션은 part를 묶는 관리 단위다
- background merge가 작은 part를 더 큰 part로 합친다
- TTL과 materialized view는 이 part 기반 세계 위에서 돌아간다

즉 ClickHouse 운영의 본질은 SQL 문법보다 **part가 어떤 형태로 만들어지고, 얼마나 많아지고, 어떤 기준으로 읽히고, 언제 합쳐지고, 언제 정리되는가**에 가깝다.

이 관점을 먼저 가져가면 많은 오해가 정리된다.

- `ORDER BY`는 일반 RDB의 보조 인덱스 여러 개를 대체하는 것이 아니다
- `PARTITION BY`는 자주 필터링하는 모든 컬럼을 넣는 곳이 아니다
- materialized view는 기존 쿼리 결과를 저장해두는 캐시가 아니다
- update/delete는 공짜가 아니고, mutation 비용을 반드시 생각해야 한다
- 높은 ingest throughput은 insert TPS만이 아니라 merge capacity와 같이 봐야 한다

즉 ClickHouse는 "쓰면 빠르다"보다 **어떻게 쌓였을 때 빠른지 예측 가능한 시스템**으로 보는 편이 맞다.

---

## 핵심 개념 1: `ORDER BY`는 정렬 규칙이자 읽기 경로의 중심이며, 일반 RDB 인덱스처럼 여러 개를 덕지덕지 붙일 수 없다

ClickHouse를 처음 설계할 때 가장 많이 틀리는 부분이 `ORDER BY`다. SQL 문법이 익숙하니 많은 사람이 이렇게 생각한다.

- 자주 조회하는 컬럼을 인덱스처럼 넣으면 되겠지
- 여러 조건을 만족시키게 많이 넣을수록 좋겠지
- unique key 비슷하게 잡아두면 중복도 막겠지

이 감각은 거의 항상 문제를 만든다.

### `ORDER BY`의 본질

MergeTree에서 `ORDER BY`는 part 내부 row를 정렬하는 기준이다. 그리고 이 정렬 순서를 따라 sparse primary index가 생성된다. 즉 `ORDER BY`는 단순 정렬 옵션이 아니라 아래를 동시에 결정한다.

- 어떤 범위를 빠르게 건너뛸 수 있는가
- 같은 값들이 얼마나 잘 모이는가
- 압축 효율이 얼마나 좋아지는가
- merge 시 데이터 재배치 비용이 어떻게 되는가
- 나중에 `FINAL`, dedup, range scan이 얼마나 비싸지는가

실무적으로는 이렇게 이해하는 편이 좋다.

> `ORDER BY`는 "이 테이블을 앞으로 어떤 축으로 가장 자주 잘라 읽을 것인가"에 대한 선언이다.

### 왜 일반 RDB 인덱스 감각이 안 맞는가

PostgreSQL에서는 여러 보조 인덱스를 둘 수 있고, 플래너가 상황에 따라 선택한다. 하지만 ClickHouse는 보통 테이블당 하나의 정렬 축이 매우 중요하다. 물론 data skipping index 같은 보조 수단이 있지만, 성능의 중심은 여전히 `ORDER BY`다.

그래서 아래처럼 설계하면 종종 나빠진다.

- 모든 필터 컬럼을 길게 `ORDER BY`에 넣기
- 카디널리티가 너무 높은 컬럼을 맨 앞에 두기
- 조회 패턴보다 유니크함을 만들겠다고 event_id를 맨 앞에 두기
- 시간축 조회가 핵심인데 tenant_id만 먼저 둬서 범위 scan 효율을 잃기

### 좋은 `ORDER BY`를 고르는 기준

보통 아래 네 가지를 같이 본다.

1. **가장 자주 쓰는 필터가 무엇인가**
2. **범위 조회가 시간축 중심인가**
3. **동일 값이 몰리면 압축과 집계에 유리한가**
4. **테이블의 주 목적이 raw event 보관인가, 특정 집계 질의 최적화인가**

예를 들어 SaaS 이벤트 로그 테이블이라면 흔히 이런 조회가 많다.

- 특정 기간의 특정 서비스 이벤트 조회
- 특정 테넌트, 특정 이벤트 타입 집계
- 최근 1일/7일 기준 funnel 분석
- 시간순 최신 이벤트 확인

이때 `ORDER BY (tenant_id, event_date, event_time)`처럼 잡을 수도 있지만, 실제 패턴이 시간범위 + 테넌트라면 아래처럼 더 현실적인 선택이 나올 수 있다.

```sql
ORDER BY (tenant_id, toStartOfHour(event_time), event_time, event_name)
```

혹은 서비스 전체 시간 범위 스캔이 더 많다면,

```sql
ORDER BY (event_date, tenant_id, event_name, event_time)
```

정답은 문법이 아니라 **주 쿼리의 절반 이상을 설명하는 축을 앞쪽에 두는 것**이다.

### `PRIMARY KEY`와 `ORDER BY`를 분리해서 볼 필요가 있는가

ClickHouse에서는 `PRIMARY KEY`를 따로 지정하지 않으면 대체로 `ORDER BY`가 primary key 역할도 한다. 일부 경우 `PRIMARY KEY`를 `ORDER BY`의 prefix로 다르게 둘 수 있지만, 대부분의 실무에서는 둘을 복잡하게 분리하기보다 `ORDER BY` 기준을 명확히 잡는 것이 더 중요하다.

핵심은 이것이다.

- ClickHouse의 primary key는 uniqueness를 강제하지 않는다
- foreign key 같은 관계형 제약과도 다르다
- 읽기 범위를 줄이기 위한 sparse index 성격이 강하다

즉 이름 때문에 오해하면 안 된다. **PostgreSQL의 primary key와 같은 의미를 기대하면 거의 틀린다.**

### `ORDER BY`가 압축에도 영향을 준다

ClickHouse가 빠른 이유 중 하나는 컬럼형 저장과 압축이다. 그런데 압축 효율은 값의 분포와 정렬 순서 영향을 많이 받는다. 예를 들어 같은 tenant나 event_type 값이 몰리면 codec이 더 효율적으로 작동하고, 스캔 시 필요한 블록 수도 줄어든다.

즉 `ORDER BY`는 단순히 "찾기 쉽게" 만드는 것만이 아니라, **같은 성질의 데이터를 근처에 모아 읽기와 저장 효율을 동시에 높이는 장치**다.

### 자주 하는 실수

#### 1) `ORDER BY (id)`

유니크 이벤트 ID를 앞에 두면 사실상 데이터가 랜덤하게 퍼진다. 시간 범위 집계나 tenant 집계에서 거의 도움을 못 주고 압축도 나빠진다.

#### 2) 컬럼을 너무 많이 넣기

길다고 무조건 나쁘지는 않지만, merge 비용과 설계 복잡도는 올라간다. 특히 앞쪽 prefix가 거의 조회에 안 쓰이면 이득보다 손해가 크다.

#### 3) 낮은 선택도의 컬럼만 앞에 두기

예를 들어 `event_type`만 맨 앞에 두면 범위 스캔을 충분히 좁히지 못할 수 있다. 조회의 실제 조합과 prefix 활용을 같이 봐야 한다.

결국 `ORDER BY`는 성능 옵션이 아니라, **이 테이블을 어떤 방식으로 읽을지에 대한 운영 계약**이다.

---

## 핵심 개념 2: `PARTITION BY`는 주로 관리와 수명주기 단위이며, 조회 최적화는 보너스일 뿐이다

두 번째로 자주 틀리는 것이 `PARTITION BY`다. 많은 팀이 이렇게 생각한다.

- 자주 필터링하는 컬럼을 partition으로 넣자
- tenant마다 나누면 좋지 않을까
- 날짜도 있고 서비스도 있고 지역도 넣으면 pruning이 더 강하겠지

이 접근은 대개 partition 수 폭증으로 이어진다.

### 파티션의 역할을 먼저 정확히 보자

ClickHouse에서 partition은 보통 아래 같은 목적에 잘 맞는다.

- 데이터 보존 기간 관리
- 특정 기간 드롭, 아카이빙, 이동
- 큰 테이블을 시간 단위로 물리적으로 나누기
- 백업/운영 관리 단위 단순화

즉 `PARTITION BY`는 주로 **데이터 생애주기와 part 묶음 관리 기준**이다. 조회 필터링에도 도움을 줄 수 있지만, 핵심 성능은 여전히 `ORDER BY`와 part 내부 정렬에 더 크게 좌우된다.

### 왜 over-partitioning이 위험한가

예를 들어 아래처럼 설계하는 경우가 있다.

```sql
PARTITION BY (tenant_id, toDate(event_time))
```

처음에는 좋아 보인다.

- 테넌트별 분리
- 날짜별 정리
- 조회도 빨라질 것 같음

하지만 테넌트 수가 많고 ingest가 자주 일어나면 어떤 일이 생길까?

- partition 수가 급증한다
- 각 partition에 작은 part가 많이 생긴다
- background merge가 분산되어 효율이 떨어진다
- "Too many parts" 계열 문제가 빨리 나타난다
- 메타데이터 관리 비용이 커진다

즉 partition은 세밀할수록 좋은 것이 아니라, **충분히 큰 묶음으로 운영하기 쉬워야 한다.**

### 시간 기반 partition이 기본 후보인 이유

실무에서 가장 흔한 선택은 아래 둘이다.

```sql
PARTITION BY toYYYYMM(event_time)
```

또는

```sql
PARTITION BY toDate(event_time)
```

그중 월 단위 partition이 자주 기본값이 되는 이유는 아래와 같다.

- retention 관리가 단순하다
- 하루 partition보다 개수가 적다
- 대부분의 분석 데이터는 시간 기준 삭제/보존 요구가 있다
- 너무 작은 partition 남발을 줄일 수 있다

물론 일 단위 partition이 맞는 경우도 있다.

- 하루 데이터량이 매우 크다
- 자주 하루 단위 drop이 필요하다
- 백필/재적재가 일자 기준으로 자주 일어난다

하지만 여기서도 중요한 것은 **정말 운영 요구가 일 단위인가**이지, 단순히 날짜 필터를 많이 쓴다는 이유만은 아니다.

### 파티션이 조회를 도와줄 때와 아닐 때

예를 들어 월 단위 partition + 시간 범위 필터가 붙으면 partition pruning이 잘 먹는다. 하지만 같은 월 안에서 tenant 조건을 잘 처리하는 것은 partition보다 `ORDER BY` 영향이 더 크다.

즉 아래처럼 생각하는 편이 맞다.

- partition은 먼저 "어느 월/일 데이터를 아예 읽지 않을지"를 정한다
- `ORDER BY`는 읽기로 결정된 part 안에서 "어느 범위를 덜 읽을지"를 정한다

이 둘을 섞어서 이해하면 설계가 흔들린다.

### 좋은 실무 감각

- retention이 시간 중심이면 partition도 시간 중심으로 시작한다
- tenant를 partition에 넣기 전에는 partition 수 증가를 먼저 계산한다
- partition은 가능한 한 관리하기 쉬운 큰 단위로 둔다
- 자주 조회하는 조건은 partition보다 `ORDER BY`와 view/table 분리로 푼다

### 자주 하는 실수

#### 1) `PARTITION BY user_id`

거의 항상 잘못된 방향이다. partition 폭발과 merge 비효율을 부른다.

#### 2) 월 단위로 충분한데 일+서비스+리전으로 쪼개기

pruning은 조금 좋아질 수 있어도 parts, metadata, background task 비용이 훨씬 더 커진다.

#### 3) 파티션을 샤딩처럼 생각하기

partition과 distributed sharding은 다른 문제다. partition은 한 서버/테이블 내부의 물리적 그룹 기준이지, 클러스터 분산 전략 그 자체가 아니다.

결국 `PARTITION BY`는 조회 인덱스가 아니라, **데이터를 언제 어떻게 치우고 옮길지 정하는 운영 레버**에 가깝다.

---

## 핵심 개념 3: Insert 성능은 쓰기 TPS보다 merge capacity와 part 개수로 판단해야 한다

ClickHouse가 insert를 잘 받는다고 해서 아무 형태의 insert도 잘 받는 것은 아니다. 특히 작은 배치를 자주 넣는 패턴은 초기에 멀쩡해 보여도 운영에서 빠르게 병목이 된다.

### ClickHouse에서 insert가 part를 만든다는 뜻

MergeTree 계열 테이블에 insert가 들어오면 보통 새로운 part가 생긴다. 이후 background merge가 작은 part들을 더 큰 part로 합친다.

이 구조의 의미는 중요하다.

- insert가 너무 자주 발생하면 작은 part가 많이 쌓인다
- merge가 따라가지 못하면 쿼리 시 읽어야 할 part 수가 늘어난다
- metadata, file handle, merge CPU, disk I/O 부담이 올라간다
- 결국 insert도 느려지고 query도 느려지는 이중 비용이 생긴다

즉 ClickHouse에서 진짜 좋은 ingest는 단순히 초당 행 수가 아니라, **part를 감당 가능한 속도로 생성하고 background merge가 안정적으로 흡수하는 상태**다.

### 작은 insert가 왜 위험한가

예를 들어 이벤트를 100건씩 1초마다 넣는다고 하자. 애플리케이션 입장에서는 빠른 실시간 적재처럼 보일 수 있다. 하지만 장기적으로는 아래가 생긴다.

- part 수 급증
- merge queue 증가
- 특정 partition에 소형 part 밀집
- `SELECT` 시 part open/read overhead 증가
- `OPTIMIZE`를 자주 돌리고 싶은 유혹 증가

많은 팀이 이 시점에서 `OPTIMIZE TABLE ... FINAL`로 버티려 하지만, 이것은 구조적 해결이 아니라 비싼 응급처치다.

### 실무 기본값: 가능한 한 큰 batch insert

가능하면 아래 방향이 좋다.

- 애플리케이션에서 수천~수만 행 단위로 batch
- Kafka consumer나 ETL worker에서 micro-batch 구성
- 비동기 insert 기능 사용 검토
- 파이프라인 전체 지연 SLA와 batch 크기를 함께 조정

예를 들어 1초 미만 지연이 절대적으로 필요하지 않다면, 5초~30초 단위 micro-batch가 전체 비용을 크게 낮출 수 있다. ClickHouse는 대개 이 편이 더 건강하다.

### `async_insert`와 버퍼링을 어떻게 볼까

ClickHouse는 비동기 insert 관련 옵션을 제공한다. 이 기능은 작은 insert를 서버 쪽에서 더 잘 모아주도록 도와줄 수 있다. 하지만 이것도 만능은 아니다.

- 애플리케이션 단의 과도한 소형 insert 설계를 정당화하지는 못한다
- durability와 latency 요구를 같이 봐야 한다
- 장애 시 flush 전 데이터 처리 의미를 명확히 이해해야 한다

즉 `async_insert`는 구조적 ingest 설계의 보완재지, 잘못된 write pattern을 자동으로 구원하는 기능이 아니다.

### merge 압박을 볼 때 확인할 것

운영에서는 보통 아래 지표를 같이 본다.

- 현재 part 수
- partition별 part 수
- background merge queue 길이
- insert latency
- read latency와 scanned rows/bytes
- disk usage와 compaction 관련 I/O

중요한 것은 part 수가 단순 저장 메트릭이 아니라, **읽기 경로 복잡도와 유지비를 보여주는 건강 지표**라는 점이다.

### 자주 하는 실수

#### 1) 실시간이 중요하다는 이유로 row-by-row insert에 가까운 패턴 유지

ClickHouse는 OLTP row insert 시스템이 아니다. 매우 낮은 지연이 정말 필요하면 ingest layer와 rollup layer를 나눠서 봐야 한다.

#### 2) merge가 밀리는데 하드웨어만 먼저 키우기

물론 CPU와 디스크도 중요하지만, 근본 원인이 너무 잘게 쪼개진 insert이면 규모만 키워도 한계가 빨리 온다.

#### 3) `OPTIMIZE ... FINAL`을 정기 배치처럼 남발

`FINAL`은 비싸다. 설계상 필요한 예외적 유지보수인지, 아니면 insert/engine 선택이 잘못된 결과인지 구분해야 한다.

결국 ClickHouse ingest는 **write throughput 문제이면서 동시에 merge scheduling 문제**다.

---

## 핵심 개념 4: TTL은 삭제 문법이 아니라 저장 계층과 데이터 수명주기 정책을 코드로 표현하는 방법이다

데이터 플랫폼에서 retention 요구는 거의 항상 있다.

- raw event는 90일만 보관
- 집계 테이블은 1년 유지
- 특정 민감 컬럼은 30일 뒤 마스킹 또는 제거
- 최근 7일은 SSD, 그 이후는 저렴한 스토리지로 이동

ClickHouse의 TTL은 이런 정책을 테이블 수준에서 표현하게 해준다. 하지만 여기서도 자주 오해가 생긴다.

### TTL을 단순 삭제 스케줄로만 보면 놓치는 것

TTL은 단순히 "언제 지울까"만이 아니다. 실무에서는 아래를 함께 표현한다.

- row 삭제 시점
- column 값 만료 시점
- 오래된 데이터의 디스크 볼륨 이동
- raw와 rollup의 보존 기간 분리

즉 TTL은 **데이터 가치가 시간에 따라 어떻게 변하는지**를 코드로 적는 것이다.

### row TTL 예시

```sql
TTL event_time + INTERVAL 90 DAY DELETE
```

이 설정은 raw 데이터가 90일 뒤 삭제되도록 한다. 여기서 중요한 것은 이 정책이 쿼리 최적화가 아니라 **비용과 규제 대응**에 직접 연결된다는 점이다.

### column TTL 예시

특정 민감한 문자열 컬럼을 일정 시점 후 비우거나 기본값 처리하는 방식도 가능하다. 이건 GDPR류 요구나 개인정보 최소 보관 정책과 잘 맞을 수 있다.

### 스토리지 티어링과 TTL

ClickHouse는 적절한 스토리지 정책과 함께 TTL을 사용하면 오래된 데이터를 느리지만 저렴한 디스크로 이동시키는 전략도 가능하다. 이 패턴은 아래에 특히 유용하다.

- 최근 7일은 빠른 조회가 중요하다
- 8일~90일은 가끔만 조회한다
- 90일 이후는 삭제한다

즉 hot/warm/cold 계층을 애플리케이션 밖에서 비교적 단순하게 운영할 수 있다.

### TTL이 즉시 삭제를 의미하지는 않는다

여기서 중요한 실무 감각이 있다. TTL은 보통 background merge 과정에서 적용된다. 즉 설정했다고 바로 row가 사라지는 것이 아니다. 이 지점을 이해 못 하면 운영 중에 "TTL이 안 먹는다"는 오해가 자주 나온다.

그래서 TTL을 볼 때는 아래를 같이 생각해야 한다.

- merge가 잘 돌고 있는가
- 오래된 part가 적절히 재작성되고 있는가
- 삭제 시점을 초 단위로 기대하고 있지는 않은가
- 규제/법무 요구가 "즉시 삭제"에 가까운지, 아니면 일정 지연 허용인지

즉 TTL은 훌륭한 retention 도구지만, **transactional delete 대체재로 보면 안 된다.**

### 실무 설계 포인트

- raw, rollup, audit 성격마다 TTL을 다르게 둔다
- TTL은 비용, 규제, 조회 패턴을 함께 반영한다
- 최근 데이터와 오래된 데이터의 스토리지 가치를 구분한다
- TTL이 merge 의존이라는 점을 운영팀과 공유한다

### 자주 하는 실수

#### 1) 모든 테이블에 같은 90일 TTL 복붙

테이블마다 가치와 조회 패턴이 다르면 retention도 달라야 한다.

#### 2) TTL만 믿고 실제 삭제 SLA를 문서화하지 않기

법무/보안 요구가 엄격하면 merge 지연이 허용 범위인지부터 확인해야 한다.

#### 3) hot/warm tiering 없이 비싼 스토리지에 오래 쌓아두기

분석 데이터는 시간이 갈수록 조회 가치가 줄어드는 경우가 많다. TTL과 storage policy를 같이 보는 편이 낫다.

결국 TTL은 **저장 비용과 데이터 정책을 자동화하는 도구**로 봐야 한다.

---

## 핵심 개념 5: Materialized View는 "쿼리 캐시"가 아니라 ingest 시점 변환과 rollup 파이프라인이다

ClickHouse의 Materialized View를 RDB materialized view 감각으로 보면 또 틀리기 쉽다. 많은 사람이 이렇게 기대한다.

- 무거운 쿼리를 미리 저장해두는 캐시겠지
- 원본 테이블이 바뀌면 자동으로 전체 재계산되겠지
- BI용 요약 테이블을 쉽게 만드는 기능이겠지

일부는 맞지만, ClickHouse 실무에서는 더 정확히 이렇게 봐야 한다.

> Materialized View는 source 테이블에 들어오는 insert를 받아 target 테이블로 흘려보내는 **실시간 변환/집계 파이프라인**에 가깝다.

### 왜 이 관점이 중요한가

ClickHouse Materialized View는 보통 source insert 시점에 동작한다. 즉 새로운 데이터가 들어올 때 변환, 필터링, 집계를 수행해 다른 테이블에 적재한다. 이 구조의 의미는 명확하다.

- 원본 raw와 rollup을 분리하기 좋다
- 조회 비용을 write 시점으로 일부 이전할 수 있다
- 반복적으로 쓰는 집계를 미리 계산해둘 수 있다
- ingestion pipeline을 DB 안에서 비교적 단순하게 구성할 수 있다

하지만 동시에 아래 제약도 생긴다.

- 기존 데이터 전체를 자동 재계산해주는 캐시는 아니다
- backfill 시 view 대상과 순서를 신중히 다뤄야 한다
- rollup 테이블의 정합성은 source insert 흐름과 엔진 선택에 달려 있다
- update/delete 기반 원본 변경은 단순 append와 다르게 생각해야 한다

### raw + rollup 2단 구조가 자주 강한 이유

실무에서는 흔히 아래 구조가 강하다.

1. raw 이벤트는 최대한 단순한 MergeTree에 저장
2. Materialized View로 시간단위/서비스단위 집계 테이블에 반영
3. 실시간 대시보드는 rollup을 주로 읽고
4. 상세 분석이나 재집계는 raw를 읽는다

이 구조의 장점은 아래다.

- 대시보드 조회가 매우 빨라진다
- raw 보존을 유지해 재처리와 정의 변경이 가능하다
- 집계 쿼리의 부담을 write 시점으로 분산한다
- 비용이 예측 가능해진다

### 어떤 target engine을 고를 것인가

Materialized View의 결과를 어디에 넣느냐도 중요하다.

- 단순 합계성 지표면 `SummingMergeTree`
- state 함수 기반 고급 집계면 `AggregatingMergeTree`
- 그냥 변환 결과를 별도 raw-like 테이블에 저장하면 일반 `MergeTree`

여기서 중요한 것은 엔진 이름보다 **조회 시점 계산 비용과 write 시점 복잡도 사이의 교환**이다.

### backfill이 왜 자주 사고를 만드는가

Materialized View는 새 insert에 반응한다. 그래서 기존 historical data를 뒤늦게 넣을 때 아래를 꼭 의식해야 한다.

- view가 켜진 상태에서 raw를 재적재하면 rollup에 중복 반영될 수 있는가
- target 테이블을 먼저 비워야 하는가
- backfill 순서를 시간순으로 맞춰야 하는가
- dedup 전략이 있는가

즉 MV는 편하지만, **재적재와 재계산 운영 절차를 별도로 가져가야 안전하다.**

### 자주 하는 실수

#### 1) materialized view를 캐시로 생각하고 원본 쿼리 구조를 자주 바꾸기

MV는 배경 캐시가 아니다. 데이터 모델 일부다.

#### 2) target table 없이 `POPULATE`나 즉석 구성만 믿기

운영에서는 명시적 target table을 두고 lifecycle과 backfill 절차를 설계하는 편이 훨씬 낫다.

#### 3) rollup 정합성을 검증하지 않고 대시보드에 바로 연결

특히 uniq 계열, 지연 이벤트, 재적재가 있는 환경에서는 비교 검증이 필요하다.

Materialized View는 정말 강력하지만, **쿼리를 가속하는 마법이 아니라 저장 시점 계산을 구조화하는 파이프라인 도구**다.

---

## 핵심 개념 6: ClickHouse에서 update/delete/upsert는 예외 경로이며, row 단위 변경이 많다면 엔진 선택부터 다시 봐야 한다

분석 시스템이라도 현실 데이터는 종종 바뀐다.

- 주문 상태가 변경된다
- 중복 이벤트가 늦게 정정된다
- CDC로 들어온 row가 UPDATE/DELETE를 포함한다
- 개인정보 삭제 요청이 들어온다
- late-arriving fact를 반영해야 한다

이때 PostgreSQL 감각으로 "update 하면 되지"라고 접근하면 빠르게 비용 폭탄을 맞는다.

### 왜 row update가 ClickHouse에서 비싼가

ClickHouse는 append + merge 세계다. 개별 row를 자주 바꾸는 OLTP 엔진이 아니다. 따라서 mutation 기반 update/delete는 대개 내부적으로 데이터 파트를 다시 써야 하고, 큰 테이블에서는 비용이 상당할 수 있다.

즉 아래 감각이 중요하다.

- ClickHouse는 읽기와 append에 강하다
- 대량 mutation은 가능하지만 비싸다
- 자주 바뀌는 현재 상태 테이블은 별도 설계가 필요할 수 있다

### ReplacingMergeTree를 언제 보나

중복 제거 또는 최신 버전 채택이 필요하면 `ReplacingMergeTree`가 자주 언급된다. 예를 들어 `(tenant_id, entity_id, updated_at)` 기준으로 여러 버전 row가 들어오고, 나중 merge 과정에서 최신 버전을 남기고 싶을 때 쓴다.

하지만 이 엔진도 자주 오해된다.

- merge 전까지는 중복이 남아 있을 수 있다
- 쿼리에서 `FINAL`을 쓰면 비싸다
- 즉시 강한 upsert 보장을 기대하면 안 된다

즉 ReplacingMergeTree는 **느슨한 최종 정합 dedup 도구**에 가깝다. 실시간 정확한 최신값 테이블처럼 쓰려면 비용과 쿼리 패턴을 아주 신중히 봐야 한다.

### CDC 적재에서 자주 필요한 판단

CDC를 ClickHouse로 넣을 때는 아래를 먼저 정해야 한다.

- 이 테이블이 raw change log 저장소인가
- 최종 최신 상태 테이블인가
- late update와 delete를 어느 지연까지 허용하는가
- 정합성이 배치 재구성으로 보완 가능한가

많은 경우 가장 안전한 구조는 아래다.

1. raw CDC 이벤트를 append로 저장
2. 필요하면 최신 상태 projection을 별도 테이블/MV로 구축
3. BI는 용도에 따라 raw or projection을 선택

즉 "한 테이블에서 모든 의미를 해결하려고 하지 않는 것"이 중요하다.

### 자주 하는 실수

#### 1) ClickHouse를 운영 DB 대체로 생각하고 update-heavy 워크로드 넣기

짧은 트랜잭션과 row-level update가 핵심이면 다른 시스템이 더 맞을 수 있다.

#### 2) ReplacingMergeTree면 곧 upsert라고 믿기

merge와 query semantics를 이해하지 않으면 중복, 지연, `FINAL` 비용 때문에 곤란해진다.

#### 3) mutation을 백그라운드니까 공짜라고 보기

mutation은 결국 I/O와 CPU를 쓴다. 대형 테이블에서는 운영 시간대와 리소스 여유를 같이 봐야 한다.

결국 ClickHouse에서 변경 데이터는 **append-first 설계와 projection 분리**로 푸는 편이 대체로 더 건강하다.

---

## 핵심 개념 7: Data Skipping Index와 Projection은 주연이 아니라 조연이며, 잘못 쓰면 설계 문제를 숨기기만 한다

ClickHouse를 조금 만져본 팀은 어느 시점에서 아래 기능들을 보게 된다.

- minmax index
- set index
- bloom filter 계열 index
- projection
- codec 튜닝

이 기능들은 분명 유용하다. 하지만 여기서 많이 생기는 오해가 있다.

- `ORDER BY`가 애매해도 skipping index로 메우면 되겠지
- raw 하나만 두고 projection 여러 개 만들면 다 해결되겠지
- bloom filter 붙이면 단건 검색도 괜찮아지겠지

대체로 그렇지 않다.

### data skipping index는 "아예 안 읽을 블록"을 늘리는 보조 수단이다

ClickHouse의 skipping index는 일반 RDB의 B-tree 인덱스처럼 row pointer를 정밀하게 찾아가는 용도와는 다르다. 목적은 더 가깝게 말해 아래다.

- 이 granule은 안 읽어도 될 가능성이 높다
- 이 part 범위는 조건에 안 맞을 가능성이 높다

즉 성능의 주축은 여전히 정렬된 데이터 레이아웃이고, skipping index는 **그 위에서 더 많은 블록을 건너뛰게 돕는 장치**다.

예를 들어 URL path, user_id, request_id처럼 본 정렬 축에는 못 넣지만 특정 필터가 종종 중요한 컬럼이 있을 수 있다. 이때 bloom 계열 index가 유용할 수 있다. 하지만 이것은 어디까지나 보강책이다.

### 언제 도움이 되는가

- 본 쿼리 패턴은 시간/테넌트 축인데, 특정 ID 필터도 가끔 들어온다
- 문자열 포함 여부나 희소한 값 검색이 있다
- 전체 raw 테이블을 다시 쪼개기엔 아직 비용이 크다
- 완전한 row lookup이 아니라 "스캔 양을 좀 더 줄이는 것"이 목표다

### 언제 실망하는가

- `ORDER BY`가 핵심 조회와 전혀 안 맞는다
- 거의 모든 쿼리가 skipping index에 의존해야 한다
- granule 단위로도 선택도가 낮아 실제로는 많이 못 건너뛴다
- 단건 lookup을 RDB 인덱스처럼 기대한다

즉 skipping index는 중요하지만, **테이블 설계의 중심이 아니라 마지막 20~30% 최적화 지점**으로 보는 편이 맞다.

### projection은 편리하지만, 숨은 rollup이 늘어나는 것과 같다

projection은 특정 쿼리 패턴에 맞는 다른 저장 형태를 같은 테이블 내부에 유지하게 해준다. 겉으로 보면 매우 매력적이다.

- 별도 rollup 테이블 없이도 최적화 가능해 보인다
- 쿼리 rewrite를 엔진이 일부 알아서 해줄 수 있다
- 운영 객체 수가 줄어 보인다

하지만 projection을 남발하면 결국 내부적으로는 또 다른 저장 구조를 늘리는 셈이다. 즉 아래 비용이 생긴다.

- insert 시 추가 유지 비용
- storage 사용량 증가
- backfill/재정의 복잡도
- 어떤 쿼리가 어느 projection을 타는지 파악해야 하는 운영 부담

그래서 실무에서는 보통 이렇게 생각하는 편이 낫다.

- 매우 반복적인 소수 쿼리를 위해선 projection이 유용할 수 있다
- 하지만 명시적 raw + rollup 구조가 더 투명하고 운영하기 쉬운 경우가 많다
- 팀이 아직 ClickHouse 운영 감각이 약하면 projection보다 별도 aggregate table이 디버깅하기 쉽다

즉 projection은 강력하지만, **운영 가시성과 단순성을 얼마나 희생할지**도 같이 봐야 한다.

### codec 튜닝도 마지막 단계에서 보라

ZSTD, Delta, DoubleDelta, Gorilla 같은 codec은 분명 중요하다. 특히 시간 컬럼, 숫자 시계열, 반복 문자열에서 효과가 좋다. 하지만 codec도 테이블 레이아웃이 잘못된 상태를 구원해주지는 못한다.

실무 우선순위는 대개 아래가 맞다.

1. `ORDER BY`
2. `PARTITION BY`
3. ingest batch/merge 건강도
4. raw vs rollup 분리
5. 그 다음 codec, skipping index, projection

즉 고급 기능은 필요하지만, **주요 설계 축을 잡은 뒤 미세 조정하는 순서**가 안전하다.

---

## 핵심 개념 8: 분산 클러스터에서는 Distributed 테이블보다 샤딩 키와 로컬 테이블 레이아웃이 먼저다

ClickHouse를 단일 노드에서 시작한 뒤 규모가 커지면 자연스럽게 클러스터 구성을 보게 된다. 이때도 많은 팀이 먼저 보는 것은 `Distributed` 테이블 문법이다. 하지만 진짜 중요한 것은 아래다.

- 어떤 기준으로 shard를 나눌 것인가
- shard 안의 로컬 MergeTree가 어떤 레이아웃을 가질 것인가
- 쿼리의 fan-out이 얼마나 자주 발생하는가
- aggregation을 로컬에서 얼마나 줄이고 중앙으로 올릴 것인가

즉 분산 ClickHouse의 성능은 `Distributed` 객체 자체보다 **샤딩 키와 각 shard 내부 물리 설계**에 더 크게 좌우된다.

### 샤딩 키를 잘못 잡으면 생기는 일

예를 들어 tenant 기반 SaaS에서 tenant별 조회가 압도적으로 많다면 `tenant_id` 샤딩이 직관적으로 맞을 수 있다. 반대로 전체 기간 집계나 전사 통계가 훨씬 많다면 tenant 샤딩이 fan-out 쿼리를 과도하게 만들 수 있다.

즉 샤딩 키는 단순 균등 분배가 아니라 아래를 같이 봐야 한다.

- 쿼리 locality
- hot tenant/hot customer 존재 여부
- 데이터량 성장 방향
- backfill, re-shard 난이도

### 로컬 테이블 설계가 여전히 중요하다

Distributed 테이블을 올렸다고 해서 로컬 테이블의 `ORDER BY`, `PARTITION BY` 문제가 사라지지 않는다. 오히려 샤드마다 같은 문제가 복제된다. 즉 분산 전에 단일 노드 설계가 먼저 건강해야 한다.

### 실무 기본값

- 초기에는 단일 노드/소수 샤드에서 raw + rollup 구조를 먼저 안정화
- 분산은 저장량이나 fan-out 비용이 실제로 한계에 닿을 때 도입
- 샤딩 키는 가장 비싼 쿼리들의 locality를 기준으로 선정
- cluster 확장보다 쿼리 경량화와 rollup 확장으로 먼저 버틸 수 있는지 검토

많은 경우 ClickHouse는 scale-up 여지가 꽤 크다. 너무 일찍 샤딩을 도입하면 운영 복잡도만 먼저 얻는다.

### 자주 하는 실수

#### 1) 데이터가 많아질 것 같다는 이유만으로 초기에 샤딩부터 설계

운영 난이도만 높아지고, 실제 병목은 여전히 소형 part나 잘못된 rollup 부재인 경우가 많다.

#### 2) shard key는 균등하지만 쿼리 fan-out이 대부분인 구조

쓰기는 고르게 분산돼도 읽기마다 전 shard를 치면 비용이 빠르게 커진다.

#### 3) Distributed 테이블 하나로 local table 문제를 가릴 수 있다고 생각

실제로는 local table 설계의 비용이 그대로 누적된다.

즉 분산 ClickHouse의 핵심은 문법이 아니라, **데이터를 어디서 줄이고 어디서 모을지에 대한 쿼리 토폴로지 설계**다.

---

## 실무 예시 1: SaaS 이벤트 분석용 raw 테이블을 어떻게 설계할까

상황을 가정해 보자.

- 여러 고객사가 사용하는 SaaS 서비스다
- 프론트엔드/백엔드 이벤트를 수집한다
- 실시간 대시보드는 최근 1시간, 24시간, 7일 조회가 많다
- 자주 보는 축은 `tenant_id`, `event_time`, `event_name`, `country`다
- raw event는 90일 유지하고, 시간 단위 집계를 따로 만든다

이때 첫 번째 테이블은 과하게 똑똑할 필요가 없다. 오히려 raw는 재처리 가능성과 안정적 적재가 중요하다.

```sql
CREATE TABLE app_events_raw
(
    tenant_id UInt64,
    event_time DateTime64(3, 'Asia/Seoul'),
    event_date Date DEFAULT toDate(event_time),
    event_name LowCardinality(String),
    user_id String,
    session_id String,
    country FixedString(2),
    platform LowCardinality(String),
    request_id String,
    revenue Decimal(18, 2) DEFAULT 0,
    properties String
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(event_time)
ORDER BY (tenant_id, event_date, event_name, event_time, user_id)
TTL event_time + INTERVAL 90 DAY DELETE
SETTINGS index_granularity = 8192;
```

### 왜 이런 선택을 했는가

#### `PARTITION BY toYYYYMM(event_time)`

- retention이 시간 중심이다
- 월 단위 삭제와 관리가 단순하다
- 하루 단위보다 partition 수를 과도하게 늘리지 않는다

#### `ORDER BY (tenant_id, event_date, event_name, event_time, user_id)`

- 테넌트 단위 조회가 많다
- 날짜/이벤트 타입별 집계가 흔하다
- 시간 범위 스캔도 중요하다
- `user_id`는 앞쪽 핵심 축보다는 뒤쪽 보조 축으로 둔다

#### `LowCardinality(String)`

- `event_name`, `platform`처럼 값 종류가 제한적인 문자열은 저장/조회 효율에 유리할 수 있다
- 하지만 무조건 모든 String에 쓰는 것이 아니라 분포를 보고 판단한다

#### raw에 JSON 속성 전체 보관

`properties`를 통째로 두는 것은 조회엔 불리할 수 있지만, raw 보존과 스키마 변화 대응에는 유리하다. 이후 자주 쓰는 속성만 projection 또는 별도 컬럼으로 승격할 수 있다.

### 이 테이블로 잘 되는 쿼리

```sql
SELECT
  event_name,
  count() AS cnt,
  uniqExact(user_id) AS users
FROM app_events_raw
WHERE tenant_id = 42
  AND event_time >= now() - INTERVAL 1 DAY
GROUP BY event_name
ORDER BY cnt DESC;
```

이 쿼리는 테넌트와 시간 범위가 명확하고, 정렬 축과도 비교적 잘 맞는다.

### 이 테이블로 불리한 쿼리

```sql
SELECT *
FROM app_events_raw
WHERE request_id = '4f7c...';
```

`request_id` 단건 조회가 핵심인 시스템이라면 ClickHouse raw 테이블만으로 해결하려 하면 안 된다. 이건 운영 DB나 별도 lookup 저장소가 더 맞을 수 있다. 즉 **모든 조회를 하나의 테이블이 책임진다고 기대하면 안 된다.**

---

## 실무 예시 2: 시간 단위 rollup을 Materialized View로 분리하면 왜 대시보드 비용이 급감할까

raw 테이블만으로 최근 7일 대시보드를 계속 그리면, 데이터가 커질수록 집계 비용이 누적된다. 이때 흔한 해결책이 시간단위 rollup이다.

### target rollup 테이블

```sql
CREATE TABLE app_events_hourly
(
    hour DateTime,
    tenant_id UInt64,
    event_name LowCardinality(String),
    events AggregateFunction(count),
    users AggregateFunction(uniqCombined64, String),
    revenue_sum AggregateFunction(sum, Decimal(18, 2))
)
ENGINE = AggregatingMergeTree
PARTITION BY toYYYYMM(hour)
ORDER BY (tenant_id, hour, event_name);
```

여기서 `events`, `users`, `revenue_sum`은 집계 state를 저장한다. 이렇게 하면 나중에 rollup끼리 다시 합칠 수 있다.

### materialized view

```sql
CREATE MATERIALIZED VIEW mv_app_events_hourly
TO app_events_hourly
AS
SELECT
    toStartOfHour(event_time) AS hour,
    tenant_id,
    event_name,
    countState() AS events,
    uniqCombined64State(user_id) AS users,
    sumState(revenue) AS revenue_sum
FROM app_events_raw
GROUP BY hour, tenant_id, event_name;
```

실제 조회는 이렇게 간다.

```sql
SELECT
  hour,
  event_name,
  countMerge(events) AS events,
  uniqCombined64Merge(users) AS users,
  sumMerge(revenue_sum) AS revenue
FROM app_events_hourly
WHERE tenant_id = 42
  AND hour >= now() - INTERVAL 7 DAY
GROUP BY hour, event_name
ORDER BY hour, event_name;
```

### 이 구조의 장점

- raw 전체 스캔 빈도가 크게 줄어든다
- 대시보드 응답시간이 예측 가능해진다
- 테이블 목적이 분리된다. raw는 상세/재처리, rollup은 빠른 조회
- retention도 raw 90일, rollup 365일처럼 다르게 가져갈 수 있다

### 이 구조의 트레이드오프

- write 시점 계산 비용이 늘어난다
- rollup 정의 변경 시 backfill 절차가 필요하다
- 지연 이벤트가 들어오면 rollup 정합성 정책을 정해야 한다
- distinct 계열 집계는 정확도/성능 트레이드오프를 신중히 봐야 한다

즉 MV는 조회 캐시가 아니라, **raw 읽기 비용을 미리 나눠서 지불하는 설계**다.

---

## 실무 예시 3: Retention과 비용을 같이 풀 때 TTL과 storage tier를 어떻게 조합할까

상황:

- 보안 이벤트는 최근 7일은 자주 조회
- 8일~30일은 감사 대응 때문에 가끔 조회
- 31일 이후는 법적 보존 불필요
- SSD는 비싸고, 느린 디스크는 충분히 있다

이때 raw 이벤트 테이블을 하나로 계속 SSD에 두면 조회는 좋지만 비용이 커진다. 반대로 너무 빨리 느린 스토리지로 보내면 조사 속도가 나빠질 수 있다.

ClickHouse TTL과 storage policy를 함께 쓰면 이런 계층화를 비교적 단순하게 표현할 수 있다.

개념적으로는 아래와 같다.

- 최근 7일: hot volume
- 8일~30일: warm/cold volume 이동
- 31일 이후: delete

실무 포인트는 TTL이 곧 비용 절감 스위치가 아니라는 점이다. 아래를 같이 봐야 한다.

- 감사 조회는 보통 최근 며칠에 집중되는가
- 오래된 데이터의 접근 빈도가 정말 낮은가
- merge와 move 작업이 운영 시간대에 미치는 영향은 어떤가
- delete와 move 타이밍이 충돌하지 않는가

즉 TTL은 데이터 가치 곡선을 반영해야 한다. 많이 보는 데이터와 거의 안 보는 데이터를 같은 디스크 비용으로 유지하는 것은 대개 낭비다.

---

## 실무 예시 4: CDC 기반 최신 상태 조회를 ClickHouse 하나로 끝내려 하면 왜 흔들릴까

많은 팀이 Debezium 같은 CDC를 넣으며 이런 요구를 만든다.

- 최신 주문 상태를 바로 보고 싶다
- 대시보드 집계도 하고 싶다
- 이력도 남기고 싶다
- 삭제 반영도 필요하다

이 요구를 하나의 ReplacingMergeTree 테이블로 모두 처리하려 하면 아래 문제가 생기기 쉽다.

- 최신 상태 조회엔 `FINAL`이 자주 필요해진다
- merge 타이밍에 따라 중복 row가 보일 수 있다
- 과거 이력과 현재 상태 의미가 뒤섞인다
- BI 쿼리와 상태 조회 쿼리가 서로 요구를 망친다

더 안정적인 구조는 보통 이렇게 간다.

1. raw CDC event log를 append 저장
2. 필요한 최신 상태 projection을 별도 테이블로 구성
3. 집계용 테이블은 상태 projection 또는 raw에서 다시 분리
4. 즉시 일관성이 정말 필요하면 ClickHouse 밖의 서빙 저장소도 고려

핵심은 이것이다.

> ClickHouse는 분석 시스템으로 매우 강력하지만, 최신 상태 서빙과 change log 보관과 대규모 집계를 한 테이블로 동시에 해결하려 들면 semantics가 빠르게 꼬인다.

---

## 트레이드오프 1: 넓은 `ORDER BY`는 더 많은 질의 패턴을 커버할 수 있지만 merge와 설계 복잡도를 키운다

### 장점

- 다양한 prefix 조건을 어느 정도 수용할 수 있다
- 압축과 scan locality를 세밀하게 조절할 수 있다
- 여러 분석 축이 섞인 테이블에서 유연성이 생긴다

### 비용

- 정렬 키가 복잡해질수록 merge 재정렬 비용이 올라간다
- 어떤 prefix가 실제로 중요한지 흐려진다
- 데이터 모델 변경 시 영향 범위가 커진다

실무에서는 "많이 넣을수록 안전"보다 **앞쪽 prefix 몇 개가 진짜 중요한가**를 더 엄격하게 보는 편이 낫다.

---

## 트레이드오프 2: 세밀한 partition은 pruning을 돕는 것처럼 보이지만 parts 폭발과 운영 복잡도를 부른다

### 장점

- 특정 기간/범위 드롭이 더 세밀해진다
- 일부 쿼리에서 pruning 이점이 있다
- 백필 단위가 잘 맞으면 운영이 편할 수 있다

### 비용

- partition 수 증가
- merge 분산과 소형 part 증가
- 메타데이터와 오버헤드 확대
- 클러스터 운영시 문제 지점이 더 많아짐

즉 partition은 세밀함보다 **충분히 큰 물리 단위로 안정적 운영이 가능한가**가 먼저다.

---

## 트레이드오프 3: raw만 읽으면 모델은 단순하지만 조회 비용이 커지고, rollup을 늘리면 빠르지만 재계산 운영이 생긴다

### raw 중심 구조

- 장점: 단순하다
- 장점: 정의 변경과 재분석이 쉽다
- 단점: 대시보드와 반복 집계 비용이 커진다
- 단점: 데이터가 커질수록 응답시간이 흔들린다

### rollup/MV 구조

- 장점: 조회가 빠르고 예측 가능하다
- 장점: CPU 비용을 write 시점으로 분산할 수 있다
- 단점: backfill, 정합성 검증, 중복 반영 관리가 필요하다
- 단점: 데이터 모델이 두세 겹으로 늘어난다

대개 현실적인 구조는 둘 중 하나가 아니라 **raw + 몇 개의 핵심 rollup**이다.

---

## 트레이드오프 4: ReplacingMergeTree와 mutation은 유연성을 주지만 즉시성, 비용, 쿼리 단순성을 잃게 만든다

### 장점

- 느슨한 upsert/dedup 패턴을 수용할 수 있다
- CDC나 정정 데이터에 대응 가능하다
- append-only가 아닌 현실 데이터를 어느 정도 흡수한다

### 비용

- merge 전 중복 가시성
- `FINAL` 비용
- mutation과 재작성 비용
- 쿼리 semantics 이해 난도 상승

즉 변경이 많은 데이터는 엔진 기능만으로 버티기보다, **projection 분리와 업무적 지연 허용 범위**를 함께 설계해야 한다.

---

## 흔한 실수 1: `ORDER BY`를 일반 RDB 복합 인덱스처럼 생각한다

ClickHouse에서 `ORDER BY`는 테이블 레이아웃 중심이다. 보조 인덱스 몇 개 더 붙이는 감각으로 설계하면 거의 반드시 재작업하게 된다.

---

## 흔한 실수 2: 자주 필터링하는 모든 컬럼을 partition에 넣는다

이건 조회 최적화보다 partition 폭발을 먼저 부른다. partition은 관리 단위라는 감각을 먼저 가져야 한다.

---

## 흔한 실수 3: 소형 insert를 파이프라인 편의로 방치한다

초반엔 괜찮아 보이지만, part 수와 merge 지연으로 결국 insert와 query 둘 다 흔들린다.

---

## 흔한 실수 4: Materialized View를 캐시처럼 생각하고 backfill 계획 없이 도입한다

MV는 파이프라인이다. 정의 변경, 재적재, 중복 반영 방지 절차가 없으면 운영 중 언젠가 사고가 난다.

---

## 흔한 실수 5: raw, latest state, rollup을 하나의 테이블 의미로 해결하려 한다

데이터 의미가 다르면 테이블도 분리하는 편이 낫다. 하나의 테이블이 모든 의미를 동시에 만족시키려 하면 쿼리도 비싸지고 정합성도 흐려진다.

---

## 흔한 실수 6: TTL을 즉시 삭제 기능처럼 기대한다

TTL은 보통 merge 기반으로 반영된다. 규제 요구가 강한 경우 실제 삭제 SLA와 차이를 반드시 이해해야 한다.

---

## 흔한 실수 7: `FINAL`을 정답처럼 남발한다

`FINAL`은 필요할 때만 써야 한다. 일상 조회에서 `FINAL`이 자주 필요하다면 엔진 선택이나 모델링을 다시 봐야 할 가능성이 크다.

---

## 흔한 실수 8: ClickHouse로 단건 조회, 강한 트랜잭션, 잦은 row update까지 모두 해결하려 한다

ClickHouse는 분석에 매우 강하지만 만능 OLTP 대체재는 아니다. 서빙 저장소와 분석 저장소의 경계를 분명히 해야 한다.

---

## 설계 체크리스트: 새 ClickHouse 테이블을 만들기 전에 반드시 확인할 것

### 1) 조회 패턴

- [ ] 가장 비싼 쿼리 3개는 무엇인가?
- [ ] 시간 범위 조회가 핵심인가, tenant/서비스별 조회가 핵심인가?
- [ ] 단건 lookup이 중요한가, 대량 scan/aggregation이 중요한가?
- [ ] raw 상세 조회와 대시보드 집계를 같은 테이블에서 처리하려는가?

### 2) `ORDER BY`

- [ ] 정렬 키 앞쪽 prefix가 핵심 쿼리와 실제로 맞는가?
- [ ] 유니크 ID를 습관적으로 맨 앞에 두지는 않았는가?
- [ ] 압축과 scan locality에 도움이 되는 순서인가?
- [ ] 너무 많은 컬럼을 넣어 merge 비용만 키우고 있지는 않은가?

### 3) `PARTITION BY`

- [ ] retention/drop 요구는 어떤 시간 단위인가?
- [ ] partition 수가 6개월, 1년 뒤에도 감당 가능한가?
- [ ] tenant/user 기반 분할로 과도하게 잘게 쪼개지지 않는가?
- [ ] partition이 조회 인덱스가 아니라 관리 단위라는 점을 반영했는가?

### 4) ingest와 merge

- [ ] insert batch 크기는 충분한가?
- [ ] 작은 insert가 초당 얼마나 발생하는가?
- [ ] merge backlog와 part 수를 모니터링하는가?
- [ ] `OPTIMIZE FINAL` 없이도 건강하게 유지될 구조인가?

### 5) TTL과 lifecycle

- [ ] raw, rollup, audit 데이터의 보존 기간이 각각 정의되어 있는가?
- [ ] hot/warm/cold storage 전략이 필요한가?
- [ ] TTL이 merge 기반 반영이라는 점을 운영팀이 이해하는가?
- [ ] 개인정보/규제 데이터는 별도 삭제 요구를 만족하는가?

### 6) Materialized View와 rollup

- [ ] 반복적으로 느린 집계가 명확한가?
- [ ] rollup 테이블이 raw 대비 실제 비용 절감을 만드는가?
- [ ] backfill 절차와 중복 방지 전략이 있는가?
- [ ] 집계 정확도와 write 비용의 trade-off를 수용할 수 있는가?

### 7) 변경 데이터 처리

- [ ] row update/delete가 자주 발생하는가?
- [ ] ReplacingMergeTree가 정말 맞는가, 아니면 raw + projection 분리가 더 나은가?
- [ ] `FINAL` 의존 조회가 많아지지 않는가?
- [ ] mutation 비용과 SLA를 계산했는가?

---

## 운영 체크리스트: 이미 돌고 있는 ClickHouse가 느려질 때 우선 보는 순서

1. **part 수가 비정상적으로 늘었는가?**
   - partition별 소형 part 밀집 여부
   - 최근 ingest batch 크기 변화

2. **merge backlog가 쌓였는가?**
   - background merge가 실제 ingest 속도를 따라가고 있는가
   - mutation/TTL/move 작업이 merge 자원을 잠식하고 있지 않은가

3. **핵심 쿼리가 `ORDER BY` prefix를 제대로 활용하는가?**
   - WHERE 절이 설계 의도와 맞는가
   - 실제로 너무 넓은 스캔을 하고 있지 않은가

4. **rollup 없이 raw 전체를 과도하게 읽고 있지는 않은가?**
   - 대시보드 쿼리가 반복적으로 동일한 heavy scan을 수행하는가
   - MV/aggregated table로 옮길 후보가 명확한가

5. **`FINAL`, mutation, backfill이 평시 트래픽을 해치고 있지는 않은가?**
   - 운영 시간대에 비싼 재작성 작업이 겹치지 않는가
   - CDC/정정 작업이 query latency를 밀어올리고 있지 않은가

이 순서를 먼저 보면, 무조건 스펙 업이나 샤딩부터 들어가는 실수를 꽤 줄일 수 있다.

---

## 실무 권장 기본 원칙

### 1) raw 테이블은 단순하게, 조회 패턴은 rollup으로 분리한다

처음부터 모든 요구를 하나의 MergeTree에 넣기보다, raw는 append와 재처리에 집중하고 조회 최적화는 별도 테이블로 나누는 편이 장기적으로 훨씬 안정적이다.

### 2) `ORDER BY`는 가장 자주 읽는 질문을 기준으로 결정한다

데이터 모델이 아니라 질문 모델로 정렬 키를 잡아야 한다. "이 테이블에서 가장 자주 무엇을 묻는가"가 핵심이다.

### 3) partition은 시간 중심으로 보수적으로 시작한다

대부분의 분석 데이터는 시간 축으로 수명주기 관리가 가능하다. 과도한 세분화는 나중에 거의 항상 비용으로 돌아온다.

### 4) ingest는 row 수보다 part 건강도로 본다

초당 몇 행 넣었는지보다, 그 결과로 part와 merge가 건강한지가 더 중요하다.

### 5) TTL은 비용 절감 장치이면서 정책 문서다

삭제 기간, tier 이동, 민감 정보 만료는 테이블 정의 속 운영 정책이다. 데이터 팀과 보안/법무 요구를 함께 반영해야 한다.

### 6) MV는 편한 기능이 아니라 파이프라인이라는 마음가짐으로 다룬다

backfill, 재정의, 정합성 검증, 중복 방지까지 운영 절차가 있어야 한다.

### 7) update-heavy 요구는 ClickHouse에 억지로 맞추지 않는다

현재 상태 서빙, 강한 트랜잭션, 잦은 수정이 핵심이면 별도 저장소를 조합하는 것이 보통 더 낫다.

---

## 한 줄 정리

ClickHouse를 실무에서 잘 쓰는 핵심은 단순히 컬럼형 DB를 도입하는 것이 아니라, **MergeTree의 `ORDER BY`로 읽기 경로를 설계하고, `PARTITION BY`와 TTL로 데이터 수명주기를 통제하며, Materialized View로 반복 집계를 파이프라인화해서 raw 보관과 빠른 조회를 분리하는 것**이다.
