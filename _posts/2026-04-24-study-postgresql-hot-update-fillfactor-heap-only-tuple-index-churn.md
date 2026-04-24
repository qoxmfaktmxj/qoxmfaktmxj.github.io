---
layout: post
title: "PostgreSQL HOT Update 실전: Fillfactor, Heap-Only Tuple, Index Churn으로 UPDATE 비용을 구조적으로 줄이는 법"
date: 2026-04-24 11:40:00 +0900
categories: [sql]
tags: [study, sql, postgresql, hot-update, fillfactor, heap-only-tuple, index, bloat, wal, performance, operations]
permalink: /sql/2026/04/24/study-postgresql-hot-update-fillfactor-heap-only-tuple-index-churn.html
---

## 배경: 왜 PostgreSQL에서는 "UPDATE 한 줄"이 생각보다 훨씬 비싼가

운영 중인 PostgreSQL에서 쓰기 부하를 다루다 보면 이런 장면을 자주 본다.

- 초당 요청 수는 크게 늘지 않았는데 API 지연 시간이 조금씩 오른다.
- CPU보다 먼저 WAL 증가, checkpoint pressure, autovacuum 작업량이 눈에 띄게 커진다.
- 대량 배치가 없는데도 특정 테이블만 유독 bloat가 빨리 누적된다.
- 조회 성능 문제를 의심해 인덱스를 더 만들었더니 오히려 UPDATE가 더 비싸진다.
- 상태값 변경, retry count 증가, `updated_at` 갱신 같은 사소한 수정이 쌓이면서 디스크와 replica lag가 흔들린다.
- 쿼리 한 건은 단순한데 트래픽이 누적될수록 인덱스 크기와 vacuum 비용이 예상보다 빨리 커진다.

이때 많은 팀이 먼저 보는 것은 SQL 문장 자체다. 물론 쿼리 튜닝은 중요하다. 하지만 PostgreSQL에서는 같은 `UPDATE`라도 **어떤 컬럼을 바꾸는지, 그 컬럼이 인덱스와 연결되는지, 페이지 안에 여유 공간이 남아 있는지**에 따라 비용 구조가 크게 달라진다.

핵심은 PostgreSQL의 `UPDATE`가 In-place overwrite가 아니라는 점이다. PostgreSQL은 MVCC 기반이라 기존 행을 그냥 덮어쓰지 않는다. 보통은 새 row version을 만들고, 예전 버전은 나중에 vacuum이 정리한다. 그래서 UPDATE가 많아지면 단순히 "값만 바뀐다"가 아니라 아래 문제가 같이 생긴다.

- heap row version 증가
- dead tuple 누적
- 인덱스 엔트리 재기록
- WAL 증가
- page split, bloat, vacuum 부담 증가
- replica replay 비용 증가

그런데 PostgreSQL에는 이 비용을 구조적으로 줄이는 매우 중요한 최적화가 있다. 바로 **HOT(Heap-Only Tuple) Update**다.

HOT Update를 잘 활용하면 다음이 가능해진다.

- UPDATE 시 불필요한 인덱스 재기록을 줄일 수 있다.
- 자주 바뀌는 컬럼이 있는 테이블의 write amplification을 낮출 수 있다.
- bloat와 autovacuum 부담을 완화할 수 있다.
- WAL과 replica lag를 완전히 없애지는 못해도 꽤 의미 있게 줄일 수 있다.
- 같은 하드웨어에서 더 많은 write churn을 버틸 수 있다.

하지만 실무에서는 HOT가 자동으로 잘 되지 않는다. 이유는 단순하다.

1. 자주 바뀌는 컬럼에 인덱스를 걸어둔다.
2. 테이블 fillfactor를 기본값 100처럼 운영해 페이지 여유 공간을 거의 남기지 않는다.
3. `updated_at` 같은 습관적 컬럼 갱신이 HOT 기회를 깨뜨린다.
4. bloat는 보지만 HOT ratio는 보지 않는다.
5. 조회 최적화 때문에 만든 인덱스가 쓰기 병목의 원인이 되는지 추적하지 않는다.

오늘 글은 PostgreSQL HOT Update를 단순 개념 소개가 아니라, **운영 중 UPDATE가 많은 테이블에서 write cost를 어떻게 설계적으로 낮출 것인가**라는 관점으로 정리한다.

이번 글에서 다룰 핵심 질문은 아래와 같다.

- HOT Update는 정확히 언제 가능하고, 언제 불가능한가
- Heap-Only Tuple과 page-local update는 내부적으로 어떤 의미인가
- fillfactor는 왜 단순 저장 효율 옵션이 아니라 write path 설계 변수인가
- 인덱스가 많을수록 왜 UPDATE 비용이 기하급수적으로 나빠질 수 있는가
- 어떤 컬럼은 본 테이블에 두고, 어떤 컬럼은 분리하거나 인덱싱을 피해야 하는가
- HOT ratio를 어떻게 측정하고, 어떤 수치 변화가 운영 신호가 되는가
- 실무에서 자주 하는 실수와, HOT 친화적으로 바꾸는 체크리스트는 무엇인가

핵심만 먼저 요약하면 이렇다.

1. PostgreSQL의 일반 `UPDATE`는 대개 새 tuple version과 인덱스 수정까지 동반하므로 생각보다 비싸다.
2. HOT Update는 **같은 page 안에 새 tuple을 둘 수 있고, 인덱스가 영향을 받지 않을 때**만 가능하다.
3. 자주 변경되는 컬럼에 인덱스가 붙어 있으면 HOT 기회가 크게 줄어든다.
4. fillfactor는 디스크 낭비 옵션이 아니라 **미래 UPDATE를 위한 page 여유 공간 예약 정책**에 가깝다.
5. HOT ratio가 높은 테이블은 같은 UPDATE 트래픽에서도 WAL, index churn, vacuum 부담이 더 낮을 가능성이 크다.
6. 조회 최적화만 보고 인덱스를 늘리면 write-heavy 테이블에서는 오히려 전체 시스템 안정성이 악화될 수 있다.
7. 실무의 핵심은 HOT를 무조건 높이는 것이 아니라, **정말 자주 바뀌는 경로에 한해 HOT-friendly schema와 indexing을 설계하는 것**이다.

---

## 먼저 큰 그림: PostgreSQL에서 UPDATE는 "값 수정"이 아니라 "새 버전 생성"에 가깝다

다음 UPDATE를 보자.

```sql
UPDATE orders
SET status = 'PAID', updated_at = now()
WHERE id = 1001;
```

애플리케이션에서는 그저 한 row의 컬럼 두 개가 바뀐 것으로 보인다. 하지만 PostgreSQL 스토리지 관점에서는 보통 아래 흐름으로 이해하는 편이 맞다.

1. 기존 tuple은 즉시 물리 덮어쓰기 되지 않는다.
2. 새 tuple version이 만들어진다.
3. 기존 tuple은 더 이상 최신 버전이 아니지만, 어떤 트랜잭션에는 여전히 보여야 할 수 있다.
4. 필요하면 관련 인덱스 엔트리도 새 tuple을 가리키도록 추가 작업이 발생한다.
5. 예전 tuple은 나중에 vacuum과 pruning 대상이 된다.

즉 UPDATE가 많아질수록 단순 변경 횟수만 늘어나는 것이 아니라 다음 비용이 누적된다.

- heap 페이지 내 버전 체인 증가
- dead tuple 증가
- 인덱스 재기록
- 디스크 쓰기 증가
- WAL 증가
- autovacuum/pruning 부담 증가

여기서 HOT가 중요한 이유는 이 흐름 중 **인덱스 재기록 비용을 피할 수 있는 경우가 존재하기 때문**이다. PostgreSQL이 이 조건을 만족하면 일반 update 대신 더 저렴한 HOT update 경로를 선택한다.

즉 HOT는 “업데이트를 빠르게 하는 마법”이 아니라, 더 정확히 말하면 **업데이트가 인덱스를 다시 건드리지 않아도 되도록 만드는 스토리지 레벨 최적화**다.

---

## 핵심 개념 1: HOT Update는 무엇이고, 왜 인덱스 churn을 줄이는 데 결정적일까

HOT는 Heap-Only Tuple Update의 약자다. 이름 그대로 핵심은 새 tuple version을 heap 내부에서 처리하고, 가능하면 인덱스는 그대로 두는 것이다.

일반 update에서는 새 row version이 만들어질 때 인덱스도 새 row 위치를 알아야 하므로 관련 인덱스 엔트리가 추가되거나 갱신된다. 반면 HOT update가 가능하면 기존 인덱스 엔트리는 그대로 유지한 채, heap 내부에서 tuple chain을 따라 최신 버전을 찾게 만들 수 있다.

실무적으로 중요한 차이는 아래다.

### 일반 UPDATE

- heap에 새 row version 생성
- 인덱스 엔트리도 새 tuple을 향하도록 변경 필요
- 인덱스 페이지 쓰기, split 가능성, WAL 증가
- dead index tuple 관리 비용 증가

### HOT UPDATE

- heap에 새 row version 생성
- 인덱스는 대체로 그대로 유지
- heap 내부 체인으로 최신 버전 추적
- 인덱스 write amplification 감소
- vacuum 및 pruning 부담은 남지만 index churn은 크게 줄어듦

이 차이는 write-heavy 테이블에서 매우 크게 나타난다. 예를 들어 초당 수천 번 `status`, `retry_count`, `heartbeat_at`, `processed_at`, `last_seen_at` 같은 컬럼이 갱신되는 테이블에서는, HOT 여부가 몇 달 운영 뒤 다음 차이로 번질 수 있다.

- 인덱스 크기 증가 속도
- WAL 생성량
- checkpoint 이후 write burst 체감
- autovacuum이 따라오는 정도
- replica replay lag
- update latency p95, p99

즉 HOT는 단순 미시 최적화가 아니라, **자주 바뀌는 테이블의 장기 운영 비용을 낮추는 구조적 메커니즘**이다.

---

## 핵심 개념 2: HOT가 성립하려면 두 가지 조건이 동시에 맞아야 한다

HOT는 아무 UPDATE에나 자동으로 적용되지 않는다. 실무에서는 아래 두 조건을 동시에 기억하면 대부분 맞다.

1. **업데이트된 컬럼이 인덱스에 영향을 주지 않아야 한다**
2. **새 tuple version이 같은 heap page 안에 들어갈 여유 공간이 있어야 한다**

둘 중 하나라도 깨지면 일반 update가 된다.

### 조건 1, 인덱스를 건드리지 않는 변경이어야 한다

예를 들어 다음 테이블을 보자.

```sql
CREATE TABLE jobs (
  id bigint primary key,
  status text not null,
  retry_count integer not null default 0,
  updated_at timestamptz not null default now(),
  worker_id text,
  payload jsonb not null
);

CREATE INDEX idx_jobs_status ON jobs (status);
CREATE INDEX idx_jobs_updated_at ON jobs (updated_at);
```

이 상태에서 다음 update는 어떨까.

```sql
UPDATE jobs
SET retry_count = retry_count + 1,
    updated_at = now()
WHERE id = 42;
```

겉으로 보면 `status`는 안 바꿨으니 HOT가 가능해 보일 수 있다. 하지만 `updated_at`에 인덱스가 있다면, 새 tuple version은 그 인덱스 관점에서 다른 값을 가지므로 인덱스 엔트리를 다시 써야 한다. 이 경우 HOT는 깨진다.

실무에서 HOT를 망치는 가장 흔한 패턴이 바로 이것이다.

- 자주 바뀌는 컬럼에 습관적으로 인덱스를 만든다.
- 특히 `updated_at`, `last_seen_at`, `heartbeat_at`, `retry_count`, `status`가 문제다.
- 조회 최적화 한 건 때문에 쓰기 경로 전체를 비싸게 만든다.

여기서 중요한 것은 “현재 UPDATE 문이 인덱스 컬럼을 직접 SET 하는가”보다 넓다. **그 컬럼이 어떤 인덱스의 키 구성에 포함되어 있거나, 인덱스 표현식/partial predicate에 영향을 주면 HOT 기회가 사라질 수 있다.**

예를 들어 아래도 주의 대상이다.

```sql
CREATE INDEX idx_jobs_active ON jobs (id) WHERE status IN ('READY', 'RUNNING');
```

이 인덱스는 키가 `id`뿐이지만 predicate에 `status`가 들어가므로, `status` 변경은 인덱스 membership에 영향을 준다. 따라서 HOT-friendly하지 않다.

### 조건 2, 같은 page 안에 새 버전을 넣을 공간이 있어야 한다

인덱스를 안 건드리는 update라도 같은 page에 새 tuple을 놓지 못하면 HOT가 되지 않는다. 결국 page 안의 free space가 중요하다.

여기서 fillfactor가 등장한다. 테이블 fillfactor를 낮추면 초기 insert 시 페이지를 100% 꽉 채우지 않고 일부 공간을 남겨둔다. 그 남은 공간이 나중에 같은 page 안에서 HOT update를 수용하는 여지로 쓰인다.

즉 HOT는 단순히 쿼리 문장의 문제가 아니라 **스키마와 저장 밀도의 합성 결과**다.

---

## 핵심 개념 3: Heap-Only Tuple, redirect, pruning을 이해하면 HOT의 성격이 선명해진다

중급 이상 개발자라면 HOT를 단순히 “인덱스 안 건드리는 update” 정도로만 알기보다, 왜 가능한지를 내부 모델 수준에서 이해하는 편이 좋다.

PostgreSQL heap page 안에는 line pointer와 tuple들이 있다. HOT update가 발생하면 기존 tuple과 새 tuple이 같은 page 안에서 체인 형태로 연결된다. 인덱스는 대개 원래 root tuple을 가리키고, heap 쪽에서 최신 visible version을 찾는 방식으로 동작한다.

이 모델이 중요한 이유는 세 가지다.

### 1) HOT는 heap 내부 지역성(locality)에 크게 의존한다

새 version이 반드시 같은 page에 있어야 한다는 점 때문에, HOT는 CPU 최적화보다 먼저 **page-level free space management** 문제다.

### 2) 시간이 지나면 pruning이 같이 중요해진다

UPDATE가 여러 번 일어나면 같은 row에 대해 HOT chain이 길어질 수 있다. PostgreSQL은 page pruning을 통해 더 이상 필요 없는 구버전들을 정리하고 체인을 압축하려고 한다. 즉 HOT가 많다고 해서 vacuum이 필요 없어지는 것은 아니다. 오히려 **HOT를 잘 쓰는 시스템일수록 pruning과 vacuum이 건강하게 따라줘야 장점이 유지된다.**

### 3) HOT는 bloat를 없애는 기능이 아니라, 인덱스 bloat와 write amplification을 줄이는 기능에 가깝다

이 차이를 오해하면 설계가 꼬인다. HOT는 다음을 줄여줄 수 있다.

- 인덱스 엔트리 재생성 빈도
- 인덱스 bloat 누적 속도
- 인덱스 관련 WAL

하지만 다음을 완전히 없애지는 못한다.

- heap row version 증가
- dead tuple 청소 필요성
- autovacuum 필요성
- 장기 트랜잭션이 유발하는 cleanup 지연

즉 HOT를 도입한 뒤에도 autovacuum 문제, long transaction, checkpoint pressure는 여전히 관리해야 한다.

---

## 핵심 개념 4: Fillfactor는 저장 효율 옵션이 아니라 미래 UPDATE를 위한 공간 예약 정책이다

많은 팀이 fillfactor를 거의 건드리지 않는다. 기본값으로 두거나, 디스크 아끼겠다는 생각으로 페이지를 가능한 한 빽빽하게 채우는 쪽을 선호한다. 읽기 중심 테이블이라면 그럴 수 있다. 하지만 update-heavy 테이블에서는 그 판단이 비쌀 수 있다.

### fillfactor가 의미하는 것

테이블 fillfactor는 insert 시 각 page를 어느 정도까지 채울지 결정하는 힌트다.

- fillfactor 100에 가까울수록 저장 밀도는 높다.
- fillfactor가 낮을수록 같은 데이터에 더 많은 page가 필요하다.
- 대신 낮은 fillfactor는 나중에 page 내부 update를 흡수할 공간을 남긴다.

예를 들어 아래처럼 설정할 수 있다.

```sql
ALTER TABLE jobs SET (fillfactor = 80);
```

이 의미는 대략 “새 row를 넣을 때 페이지를 끝까지 채우지 말고, 이후 update를 위해 약 20% 정도 여유 공간을 남겨라”에 가깝다.

### 왜 update-heavy 테이블에서 fillfactor가 중요할까

자주 수정되는 row는 같은 page에 새 version이 들어갈 여지가 많을수록 HOT 성공 가능성이 높다. 반대로 fillfactor 100에 가깝고 row size가 크면, 작은 update라도 곧바로 page 밖으로 튀어나가면서 HOT가 무너진다.

대표적으로 fillfactor 조정 효과가 큰 테이블은 이런 종류다.

- 큐, 잡 스케줄러, 워크플로 상태 테이블
- 세션, presence, heartbeat, device status 테이블
- 주문/결제/배송 상태처럼 상태 전이가 빈번한 도메인 테이블
- retry metadata, retry count, processing timestamp가 자주 바뀌는 테이블
- soft delete 대신 상태 전이를 많이 쓰는 운영 테이블

### 하지만 fillfactor를 무작정 낮추면 안 되는 이유

fillfactor는 공짜가 아니다.

- 같은 row 수를 저장하는 데 더 많은 heap page가 필요하다.
- 순차 스캔, buffer cache 효율, 디스크 footprint에서 손해가 생길 수 있다.
- read-heavy 테이블에서는 오히려 성능이 나빠질 수 있다.
- 너무 낮추면 insert throughput과 저장 효율이 불필요하게 떨어진다.

즉 fillfactor는 “낮을수록 좋다”가 아니라 **이 테이블이 얼마나 자주 update되고, 같은 row가 얼마나 자주 다시 바뀌며, read와 write 중 어디가 더 중요한지**를 기준으로 잡아야 한다.

실무적으로는 대개 아래처럼 접근한다.

- 매우 write-heavy, same-row churn이 높은 테이블: 70~85 검토
- 중간 정도 update churn: 85~95 검토
- 거의 append-only: 기본값 유지 또는 매우 보수적으로 조정

정답은 고정 숫자가 아니라, **HOT ratio와 bloat 추이로 피드백 받는 운영 실험**에 가깝다.

---

## 핵심 개념 5: 인덱스 하나가 UPDATE 비용을 얼마나 키우는지 체감해야 한다

실무에서 가장 위험한 착각 중 하나는 이것이다.

> 조회가 느리면 인덱스를 추가하면 된다. 어차피 UPDATE는 한 row만 바꾸니까 부담이 작다.

PostgreSQL write-heavy 환경에서는 이 생각이 자주 틀린다. 이유는 인덱스가 단순 조회 가속 구조물이 아니라, **업데이트 시에도 유지비를 요구하는 데이터 구조**이기 때문이다.

자주 변경되는 row에 대해 일반 update가 발생하면 인덱스마다 다음 비용이 생길 수 있다.

- 새 index tuple 생성
- 기존 tuple 정리 대기
- index page write
- page split 가능성
- WAL 증가
- vacuum 시 dead index tuple 정리 부담

즉 테이블 하나에 인덱스가 6개 있고, 그중 3개가 자주 바뀌는 컬럼과 연관되어 있다면, UPDATE 한 번이 사실상 **heap 쓰기 + 다수 index 유지 작업**으로 증폭된다.

특히 아래 패턴이 위험하다.

### 1) `updated_at` 인덱스 남용

운영에서 정말 자주 보는 안티패턴이다.

```sql
CREATE INDEX idx_orders_updated_at ON orders (updated_at);
```

문제는 거의 모든 update가 `updated_at = now()`를 같이 수행한다는 점이다. 그러면 아주 사소한 상태 변경조차 HOT 기회를 잃는다. 만약 이 인덱스가 일부 백오피스 목록 정렬 한두 군데 때문에 존재한다면, 전체 write path를 희생하는 셈이다.

대안은 이런 식으로 나눠 생각해야 한다.

- 정말 그 인덱스가 운영 핵심 path에 필요한가
- 최근 변경분 조회는 다른 보조 테이블이나 이벤트 로그로 처리할 수 없는가
- 범위가 제한적이면 partial index나 materialized view로 우회할 수 없는가
- 정렬 용도라면 읽기 전용 replica나 분석 경로로 보내는 편이 낫지 않은가

### 2) 상태값 인덱스 과다

`status`는 조회 필터에서 자주 쓰이기 때문에 인덱싱 유혹이 크다. 하지만 동시에 가장 자주 바뀌는 컬럼이기도 하다.

예를 들어 작업 큐에서 `READY -> RUNNING -> DONE` 전이가 빈번하면, `status` 인덱스는 조회에는 유용하지만 쓰기 비용을 크게 키울 수 있다.

이때는 아래를 따져봐야 한다.

- 전체 상태값 인덱스가 필요한가
- `WHERE status = 'READY'`만 중요하다면 partial index가 더 나은가
- 큐 테이블과 이력 테이블을 분리하는 편이 나은가
- polling 대신 event/lease 구조로 바꿀 수 없는가

### 3) 자주 갱신되는 지표 컬럼 인덱스

`retry_count`, `last_accessed_at`, `view_count`, `score`, `rank` 같은 컬럼은 변경 빈도가 매우 높을 수 있다. 이런 컬럼 인덱싱은 단기적으로는 조회가 빨라 보여도, 장기 운영에서는 write amplification과 bloat 비용이 더 클 수 있다.

---

## PostgreSQL 16+에서 알아둘 미묘한 변화: BRIN과 HOT의 관계

고급 운영 관점에서 흥미로운 포인트 하나는, PostgreSQL 버전에 따라 HOT 가능성이 조금 달라질 수 있다는 점이다. 특히 PostgreSQL 16에서는 **BRIN-indexed column update에 대해 HOT 적용 여지가 넓어진 변화**가 있다.

이것이 중요한 이유는 BRIN이 B-Tree처럼 tuple TID 단위로 직접 row를 가리키는 구조가 아니라, page range 요약에 가깝기 때문이다. 따라서 특정 경우에는 BRIN 인덱스가 HOT를 완전히 막지 않을 수 있다.

다만 실무 기준으로는 아래처럼 이해하는 편이 안전하다.

- 기본 원칙은 여전히 **업데이트가 인덱스 유지 작업을 유발하면 HOT 기회가 줄어든다**.
- B-Tree 중심 OLTP 환경에서는 자주 바뀌는 컬럼 인덱싱에 매우 보수적이어야 한다.
- BRIN을 쓰는 대형 append-heavy 테이블은 예외가 있을 수 있지만, 버전과 실제 workload를 기준으로 검증해야 한다.

즉 이 변화는 “이제 자주 바뀌는 컬럼에도 인덱스를 마음껏 걸어도 된다”는 뜻이 아니다. 운영 설계의 기본 원칙은 바뀌지 않는다.

---

## 실무 예시 1: 주문 상태 테이블에서 HOT를 망치는 전형적인 설계

아래 같은 `orders` 테이블을 생각해보자.

```sql
CREATE TABLE orders (
  id bigint primary key,
  user_id bigint not null,
  status text not null,
  payment_status text not null,
  shipment_status text,
  updated_at timestamptz not null default now(),
  last_event_at timestamptz,
  retry_count integer not null default 0,
  amount numeric(12,2) not null,
  metadata jsonb not null default '{}'::jsonb
);

CREATE INDEX idx_orders_user_id ON orders (user_id);
CREATE INDEX idx_orders_status ON orders (status);
CREATE INDEX idx_orders_payment_status ON orders (payment_status);
CREATE INDEX idx_orders_updated_at ON orders (updated_at);
CREATE INDEX idx_orders_last_event_at ON orders (last_event_at);
```

처음 보면 꽤 자연스럽다. 목록 조회, 상태 필터, 최근 변경분 조회를 모두 빠르게 하고 싶기 때문이다. 하지만 운영에서 아래 update가 반복되면 문제가 커진다.

```sql
UPDATE orders
SET payment_status = 'CAPTURED',
    updated_at = now(),
    last_event_at = now()
WHERE id = $1;
```

이 update는 다음 이유로 HOT가 어렵다.

- `payment_status` 인덱스 영향
- `updated_at` 인덱스 영향
- `last_event_at` 인덱스 영향
- 같은 row가 여러 번 바뀌면서 새 version이 같은 page에 남기 어려움

결과적으로 주문 하나가 상태 전이할 때마다 여러 인덱스를 다시 만지게 된다. 주문량이 늘면 아래 현상이 나타난다.

- 인덱스가 생각보다 빨리 커진다.
- vacuum이 따라오기 더 힘들어진다.
- replica apply lag가 상태 폭주 시간대에 튄다.
- 최근 변경분 정렬 하나 때문에 전체 write path가 비싸진다.

이 테이블은 보통 이렇게 재검토할 수 있다.

### 개선 방향 1, `updated_at` 인덱스의 실효성 재검토

정말 실시간 핵심 질의가 `updated_at` 기반인가? 아니면 운영용 백오피스, 관리자 화면, 배치 스캔 정도인가?

- 관리자 화면이라면 replica, 검색 엔진, 요약 테이블로 빼는 편이 나을 수 있다.
- 범위 제한이 뚜렷하다면 partial index가 더 나을 수 있다.
- 변경 이력이 중요하다면 본 테이블 대신 event log를 두는 편이 더 자연스럽다.

### 개선 방향 2, 상태 테이블과 이벤트 이력 분리

현재 상태를 담는 row와 상태 변경 이력을 한 테이블이 동시에 책임지면, 조회 요구 때문에 인덱스가 늘고 HOT가 무너진다.

예를 들어 다음 분리가 가능하다.

- `orders_current`: 현재 상태와 핵심 조회용 컬럼만 유지
- `order_events`: 상태 전이 이력, 외부 연동 결과, 상세 로그

그럼 `orders_current`는 자주 바뀌는 컬럼 인덱스를 최소화해 HOT 친화적으로 유지하고, 상세 분석이나 시간순 조회는 이벤트 테이블이 담당할 수 있다.

### 개선 방향 3, fillfactor 조정

상태 전이가 잦다면 `orders_current`에 한해 fillfactor를 80~90 수준으로 실험할 가치가 있다. 모든 테이블에 적용할 필요는 없고, **같은 row가 짧은 시간 안에 여러 번 갱신되는 테이블**에만 적용하는 편이 좋다.

---

## 실무 예시 2: 잡 큐 테이블에서 HOT와 partial index를 같이 설계하는 법

잡 큐 테이블은 HOT 최적화 효과를 체감하기 좋은 대표 사례다.

```sql
CREATE TABLE jobs (
  id bigint primary key,
  queue_name text not null,
  status text not null,
  run_at timestamptz not null,
  locked_by text,
  locked_at timestamptz,
  attempts integer not null default 0,
  last_error text,
  payload jsonb not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
```

초기 설계를 단순하게 하면 이런 인덱스를 만들기 쉽다.

```sql
CREATE INDEX idx_jobs_status ON jobs (status);
CREATE INDEX idx_jobs_updated_at ON jobs (updated_at);
CREATE INDEX idx_jobs_locked_at ON jobs (locked_at);
CREATE INDEX idx_jobs_run_at ON jobs (run_at);
```

하지만 큐 소비자는 보통 모든 상태를 조회하지 않는다. 대부분 진짜 중요한 질의는 이것에 가깝다.

```sql
SELECT id
FROM jobs
WHERE status = 'READY'
  AND run_at <= now()
ORDER BY run_at
LIMIT 100
FOR UPDATE SKIP LOCKED;
```

그렇다면 전체 `status` 인덱스보다 아래 같은 partial index가 더 실용적일 수 있다.

```sql
CREATE INDEX idx_jobs_ready_run_at
ON jobs (run_at, id)
WHERE status = 'READY';
```

이 설계의 장점은 다음과 같다.

- `READY` 잡 탐색에는 매우 효율적이다.
- `DONE`, `FAILED`, `RUNNING` 상태 row 대부분은 이 인덱스 관리 대상이 아니다.
- status 전이가 있더라도 전체 상태 인덱스를 유지하는 비용보다 좁은 범위만 관리하면 된다.

다만 여기서도 기억할 점이 있다. partial index predicate에 `status`가 들어가므로, `READY` 입장/이탈은 여전히 인덱스 영향이 있다. 즉 HOT가 완전히 자유롭지는 않다. 그래서 큐 테이블에서는 보통 설계를 더 나눠 본다.

- 준비 상태 탐색에 필요한 최소 인덱스만 유지
- 자주 갱신되는 `attempts`, `locked_at`, `updated_at` 인덱싱은 보수적으로 검토
- 완료된 row는 빠르게 archive하거나 다른 테이블로 이동
- fillfactor를 낮춰 단기간 churn을 흡수

핵심은 **모든 조회 요구를 큐 본 테이블에 억지로 태우지 않는 것**이다.

---

## 실무 예시 3: 세션, 디바이스, presence 테이블은 HOT 친화적으로 설계할수록 오래 버틴다

다음 종류의 테이블은 HOT 최적화와 궁합이 매우 좋다.

- 사용자 세션 상태
- 모바일 디바이스 last_seen
- IoT device heartbeat
- websocket presence
- worker liveness

이 테이블의 공통점은 하나다. **같은 row가 매우 자주 갱신되고, 최신 상태만 중요하며, 과거 이력은 다른 저장소로 보내도 된다.**

예를 들어 presence 테이블에서 핵심 쓰기는 이런 형태다.

```sql
UPDATE user_presence
SET last_seen_at = now(),
    last_ping_at = now(),
    server_id = $2,
    updated_at = now()
WHERE user_id = $1;
```

여기에 `last_seen_at`, `updated_at` 인덱스까지 걸어버리면 HOT는 거의 기대하기 어렵다. 반면 이런 전략은 더 낫다.

- 기본 키와 꼭 필요한 lookup key만 인덱싱
- 시간순 분석은 별도 이벤트 스트림이나 로그에서 해결
- 상태 snapshot 테이블은 HOT-friendly하게 유지
- fillfactor를 낮춰 same-row churn 흡수

이런 설계는 실시간 운영 시스템에서 특히 중요하다. presence나 heartbeat는 본질적으로 “최신 값 덮어쓰기” 성격이 강하므로, **분석성 질의와 운영성 질의를 같은 스토리지 구조에서 동시에 만족시키려 하면 write path가 무너진다.**

---

## HOT와 WAL, Autovacuum, Bloat는 어떻게 연결될까

HOT를 이야기할 때 인덱스 비용만 보지 말고, write system 전체에서 어떤 연쇄를 끊어주는지 같이 봐야 한다.

### 1) WAL 감소 효과

HOT update도 WAL을 만든다. 즉 WAL이 0이 되지는 않는다. 하지만 인덱스 수정이 줄어들면 그만큼 인덱스 관련 WAL 양이 줄어든다. write-heavy 환경에서는 이것만으로도 꽤 큰 차이가 난다.

특히 아래 상황에서 체감이 크다.

- 인덱스가 여러 개인 테이블
- 같은 row가 짧은 시간 안에 반복 갱신되는 워크로드
- replica replay가 write burst에 민감한 환경

### 2) 인덱스 bloat 완화

일반 update는 dead index tuple도 늘린다. HOT 비율이 높아지면 같은 update 횟수에서도 인덱스 쪽 bloat 누적 속도가 느려질 가능성이 크다. 이는 장기 운영에서 큰 차이를 만든다.

### 3) Vacuum 부담의 성격 변화

HOT가 많아도 heap 쪽 cleanup은 여전히 필요하다. 다만 index cleanup 부담이 줄어들 수 있다. 즉 vacuum이 완전히 사라지는 것이 아니라, **문제의 초점이 인덱스 유지에서 heap pruning 중심으로 조금 이동**한다고 보는 편이 맞다.

### 4) Checkpoint 이후 쓰기 피크 완화 가능성

인덱스 write가 줄어들면 디스크와 WAL flush 패턴이 조금 더 덜 거칠어질 수 있다. 물론 전체 시스템 효과는 workload에 따라 다르지만, update-heavy OLTP에서는 체감 차이가 날 수 있다.

즉 HOT는 단순히 micro-optimization이 아니라, **write amplification 체인을 여러 군데에서 동시에 낮춰주는 메커니즘**이다.

---

## HOT ratio를 어떻게 측정할까: 먼저 보아야 할 통계들

HOT는 감으로 판단하면 안 된다. PostgreSQL은 꽤 유용한 통계를 제공한다.

가장 먼저 볼 것은 `pg_stat_user_tables`의 `n_tup_upd`, `n_tup_hot_upd`다.

```sql
SELECT
  schemaname,
  relname,
  n_tup_upd,
  n_tup_hot_upd,
  ROUND(100.0 * n_tup_hot_upd / NULLIF(n_tup_upd, 0), 2) AS hot_ratio_pct,
  n_dead_tup,
  n_live_tup,
  vacuum_count,
  autovacuum_count,
  analyze_count,
  autoanalyze_count
FROM pg_stat_user_tables
WHERE n_tup_upd > 0
ORDER BY hot_ratio_pct ASC NULLS LAST, n_tup_upd DESC
LIMIT 30;
```

이 쿼리로 볼 수 있는 것은 아래다.

- 업데이트가 많은데 HOT ratio가 유난히 낮은 테이블은 어디인가
- dead tuple이 같이 빠르게 늘고 있는가
- autovacuum 빈도와 update churn이 균형을 이루는가

### 수치를 어떻게 해석할까

정답 같은 임계값은 없다. 하지만 실무적으로는 아래처럼 해석하면 도움이 된다.

- update가 거의 없는 테이블의 hot ratio는 큰 의미가 없다.
- update가 많은데 hot ratio가 한 자릿수이거나 거의 0이면, 인덱스 또는 fillfactor 문제를 의심할 가치가 크다.
- hot ratio가 높아도 dead tuple이 계속 과도하면 long transaction, vacuum 지연, row size growth 문제를 같이 봐야 한다.

즉 HOT는 단독 KPI가 아니라 다음과 함께 봐야 한다.

- `n_dead_tup`
- autovacuum 주기
- table/index size 추이
- `pg_stat_wal`의 WAL bytes
- replica lag
- update latency 분포

### index churn도 같이 봐야 한다

인덱스 유지비는 테이블 통계만으로 다 보이지 않는다. 아래도 함께 확인할 만하다.

```sql
SELECT
  s.schemaname,
  s.relname AS table_name,
  s.indexrelname AS index_name,
  s.idx_scan,
  pg_size_pretty(pg_relation_size(s.indexrelid)) AS index_size
FROM pg_stat_user_indexes s
ORDER BY pg_relation_size(s.indexrelid) DESC
LIMIT 30;
```

여기서 중요한 질문은 단순히 큰 인덱스가 무엇인가가 아니다.

- 이 인덱스는 정말 자주 읽히는가
- 읽기 가치 대비 update 비용이 과도하지 않은가
- 테이블의 write churn 특성과 맞는 인덱스인가

읽히지 않는 큰 인덱스, 혹은 가끔만 읽히는데 자주 바뀌는 컬럼에 걸린 인덱스는 HOT를 망치는 대표 후보군이다.

---

## HOT를 높이기 위한 실무 설계 원칙

아래 원칙들은 write-heavy PostgreSQL 시스템에서 꽤 자주 통한다.

### 원칙 1, 자주 바뀌는 컬럼과 자주 조회되는 컬럼을 구분하라

모든 컬럼을 한 row 안에 두고, 필요할 때마다 인덱스까지 추가하는 방식은 단기 개발 속도는 빠르지만 장기 운영 비용이 크다.

특히 아래 질문이 중요하다.

- 이 컬럼은 자주 바뀌는가
- 이 컬럼으로 직접 찾는 질의가 정말 핵심인가
- 이 조회는 OLTP primary가 꼭 처리해야 하는가
- 최신 상태 조회와 이력 분석을 같은 테이블에서 해야 하는가

### 원칙 2, `updated_at`는 습관적으로 인덱싱하지 마라

`updated_at` 인덱스는 생각보다 큰 대가를 부른다. 정말 핵심 운영 질의가 아니라면 제거 후보로 먼저 검토하는 편이 좋다.

### 원칙 3, 상태 테이블과 이벤트/이력 테이블을 분리하라

현재 상태 snapshot과 시간순 이벤트 이력을 분리하면, snapshot 테이블을 HOT-friendly하게 유지하기 훨씬 쉽다.

### 원칙 4, fillfactor는 테이블별로 다르게 가져가라

전역 정답은 없다. append-only fact table, read-heavy dimension table, churn-heavy queue table은 서로 다른 fillfactor를 가져야 한다.

### 원칙 5, 인덱스는 조회 건수만이 아니라 update 피해도 함께 계산하라

특정 인덱스가 하루 20번 백오피스 조회를 빠르게 만드는 대신, 초당 수천 update의 HOT를 무너뜨린다면 손익이 맞지 않을 가능성이 크다.

### 원칙 6, 큰 row와 자주 바뀌는 row를 분리하라

row가 크면 같은 page 안에서 HOT를 유지하기 더 어렵다. 예를 들어 큰 `jsonb` payload와 자주 바뀌는 상태 메타데이터가 같은 row에 섞여 있으면 page free space를 빨리 소모한다.

이 경우 아래 분리가 유효할 수 있다.

- `jobs_core`: 상태, attempts, lock metadata
- `jobs_payload`: 큰 payload, rarely updated columns

이렇게 나누면 자주 바뀌는 작은 row는 HOT-friendly하게 운영하기 쉬워진다.

---

## 흔한 실수 1: 조회 성능만 보고 인덱스를 추가한 뒤 write 병목을 DB 튜닝으로만 해결하려는 것

이 패턴은 정말 흔하다.

1. 어떤 목록 조회가 느리다.
2. `status`, `updated_at`, `last_seen_at`에 인덱스를 추가한다.
3. 초기에는 조회가 빨라진다.
4. 시간이 지나면 update-heavy 트래픽에서 WAL, vacuum, bloat, replica lag가 커진다.
5. 그제야 autovacuum 설정, IOPS, 인스턴스 스펙으로 버티려 한다.

문제는 원인이 인프라가 아니라 **데이터 모델과 인덱스 비용 구조**일 수 있다는 점이다. write-heavy 병목은 뒤늦게 파라미터 튜닝만으로 해결되지 않는 경우가 많다.

---

## 흔한 실수 2: HOT를 fillfactor 한 번 바꾸면 끝나는 기능으로 생각하는 것

fillfactor는 중요하지만, 그것만으로 충분하지 않다. HOT는 결국 다음이 모두 맞아야 성과가 난다.

- 자주 바뀌는 컬럼의 인덱스 억제
- row 크기 관리
- long transaction 억제
- vacuum/pruning 건강성 유지
- workload 특성에 맞는 테이블 분리

즉 fillfactor만 낮춰놓고 `updated_at` 인덱스를 그대로 두면 기대만큼 개선되지 않을 수 있다.

---

## 흔한 실수 3: 모든 상태값에 범용 인덱스를 두는 것

상태값 필터는 유혹적이다. 하지만 상태 전이가 잦은 도메인에서는 범용 `status` 인덱스보다 **partial index + 큐 분리 + 이력 분리**가 더 낫다.

예를 들어 대부분의 조회가 `READY` 작업 찾기뿐이라면, `status` 전체 인덱스보다 `WHERE status = 'READY'` partial index가 맞을 수 있다. 반대로 운영 대시보드용 다목적 검색 하나 때문에 전체 상태값 인덱스를 유지하는 것은 비싼 선택일 수 있다.

---

## 흔한 실수 4: 큰 JSONB와 자주 바뀌는 메타데이터를 같은 row에서 반복 갱신하는 것

예를 들어 아래처럼 하나의 큰 row에 모든 것을 담아두는 경우가 많다.

```sql
CREATE TABLE tasks (
  id bigint primary key,
  status text not null,
  attempts integer not null,
  updated_at timestamptz not null,
  payload jsonb not null,
  result jsonb,
  audit jsonb
);
```

이 row가 크고, `status`, `attempts`, `updated_at`가 자주 바뀌면 같은 page 안에 새 version을 놓기 어렵다. 그 결과 fillfactor를 조정해도 HOT 성공률이 낮을 수 있다.

이럴 때는 다음이 더 낫다.

- 큰 payload/result는 별도 테이블 또는 object storage로 분리
- 자주 바뀌는 메타데이터 row는 작게 유지
- 분석용 audit은 append-only event table로 이동

HOT는 결국 **작고 자주 바뀌는 현재 상태 row**와 잘 맞는다.

---

## 트레이드오프: HOT 친화적 설계가 항상 좋은 것은 아니다

HOT를 높이는 방향은 write-heavy 테이블에서 매우 매력적이지만, 항상 최선은 아니다. 주요 트레이드오프를 분명히 알아야 한다.

### 트레이드오프 1, 낮은 fillfactor vs 저장 효율

낮은 fillfactor는 HOT 기회를 늘리지만, 더 많은 page를 사용한다. 읽기 비중이 높은 테이블에서는 buffer 효율이 나빠질 수 있다.

### 트레이드오프 2, 인덱스 제거 vs 조회 단순성

자주 바뀌는 컬럼 인덱스를 제거하면 write는 좋아질 수 있지만, 특정 운영 조회나 백오피스 검색은 느려질 수 있다. 이때 대안 저장소, replica, 요약 테이블, 검색 시스템을 같이 설계해야 한다.

### 트레이드오프 3, 테이블 분리 vs 개발 복잡도

현재 상태와 이력을 분리하면 HOT 친화성이 올라가지만, 애플리케이션 코드와 데이터 파이프라인 복잡도는 커질 수 있다.

### 트레이드오프 4, partial index vs 쿼리 일반성

partial index는 비용 효율이 좋지만, predicate 밖의 질의에는 도움이 제한적이다. 따라서 실제 접근 패턴이 매우 명확할 때 효과적이다.

### 트레이드오프 5, HOT ratio 최적화 vs 전체 시스템 최적화

HOT ratio가 높다고 무조건 좋은 시스템은 아니다. 정말 중요한 것은 사용자 체감 지연, replica 안정성, 운영 복잡도, 저장 비용을 포함한 전체 균형이다.

즉 HOT는 목적이 아니라, **write-heavy workload를 더 싸게 운영하기 위한 수단**이다.

---

## 변경 절차: 운영 테이블을 HOT-friendly하게 바꿀 때의 현실적인 순서

이미 운영 중인 테이블이라면 아래 순서가 비교적 안전하다.

### 1) 먼저 통계를 확인한다

- `n_tup_upd`, `n_tup_hot_upd`, hot ratio
- dead tuple 추이
- 주요 인덱스 크기와 scan 빈도
- WAL 및 replica lag 피크 시간대
- 자주 실행되는 UPDATE 문과 변경 컬럼 목록

### 2) HOT를 깨는 인덱스를 식별한다

특히 아래를 우선 검토한다.

- `updated_at`, `last_seen_at`, `heartbeat_at`
- 잦은 상태 전이 컬럼
- retry/counter 계열 컬럼
- partial index predicate에 자주 바뀌는 컬럼이 들어가는 경우

### 3) 읽기 경로 대체안을 먼저 마련한다

인덱스를 제거하기 전에 아래를 확보해야 한다.

- 백오피스 조회 대체 쿼리
- replica 또는 분석 시스템 우회
- partial index 또는 materialized view
- 현재 상태/이력 분리 전략

### 4) fillfactor 조정은 테이블 rewrite 타이밍과 함께 계획한다

fillfactor 변경은 미래에 새로 작성되는 페이지부터 효과가 누적되므로, 경우에 따라 재작성 또는 장기적 관찰이 필요하다. 즉 숫자만 바꾸고 바로 효과를 기대하면 안 된다.

### 5) 배포 후 모니터링한다

배포 후 꼭 봐야 할 것은 아래다.

- HOT ratio 변화
- update latency
- index size 증가 속도
- autovacuum 시간과 빈도
- WAL bytes
- replica lag

이 과정을 거치면 단순 파라미터 조정보다 훨씬 안정적으로 write path를 개선할 수 있다.

---

## 운영에서 바로 써먹는 점검 쿼리들

### 1) 업데이트가 많은데 HOT 비율이 낮은 테이블 찾기

```sql
SELECT
  relname,
  n_tup_upd,
  n_tup_hot_upd,
  ROUND(100.0 * n_tup_hot_upd / NULLIF(n_tup_upd, 0), 2) AS hot_ratio_pct,
  n_dead_tup,
  pg_size_pretty(pg_relation_size(relid)) AS table_size
FROM pg_stat_user_tables
WHERE n_tup_upd > 10000
ORDER BY hot_ratio_pct ASC, n_tup_upd DESC;
```

### 2) 큰데 거의 안 읽히는 인덱스 후보 보기

```sql
SELECT
  s.relname AS table_name,
  s.indexrelname AS index_name,
  s.idx_scan,
  pg_size_pretty(pg_relation_size(s.indexrelid)) AS index_size
FROM pg_stat_user_indexes s
ORDER BY s.idx_scan ASC, pg_relation_size(s.indexrelid) DESC
LIMIT 50;
```

이 결과는 바로 삭제 명단이 아니라, “읽기 가치 대비 쓰기 비용이 과한 인덱스가 무엇인가”를 보는 출발점이다.

### 3) 테이블별 저장 파라미터 확인

```sql
SELECT
  c.relname,
  c.reloptions
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind = 'r'
  AND n.nspname NOT IN ('pg_catalog', 'information_schema')
ORDER BY c.relname;
```

여기서 fillfactor가 적용된 테이블을 빠르게 확인할 수 있다.

### 4) WAL 관점의 전후 비교

```sql
SELECT * FROM pg_stat_wal;
```

세밀한 원인 분리는 별도 도구가 필요할 수 있지만, HOT-friendly 변경 전후로 WAL bytes 증가 속도와 write 피크 양상이 완화되는지 보는 것은 의미가 있다.

---

## 팀 차원에서 가져가면 좋은 설계 질문

개발팀이 새 테이블이나 인덱스를 만들 때 아래 질문을 습관화하면 HOT 관련 사고를 많이 줄일 수 있다.

1. 이 테이블은 append-heavy인가, update-heavy인가?
2. 같은 row가 짧은 시간 안에 여러 번 갱신되는가?
3. 자주 바뀌는 컬럼이 무엇인가?
4. 그 컬럼들에 인덱스가 정말 필요한가?
5. `updated_at` 인덱스는 정말 운영 핵심 path를 위한 것인가?
6. 현재 상태와 이력을 분리하는 편이 더 자연스럽지 않은가?
7. row를 작게 유지할 수 있는가?
8. fillfactor를 기본값으로 둬도 되는 테이블인가?
9. 이 인덱스는 조회 이득보다 write 피해가 더 크지 않은가?
10. HOT ratio와 dead tuple을 관측 가능한가?

이 질문은 DBA 전용이 아니라, 애플리케이션 설계 단계에서 함께 나와야 한다. HOT는 스토리지 기능이지만, 성패는 대개 **도메인 모델과 인덱싱 습관**에서 갈린다.

---

## HOT가 특히 잘 먹히는 패턴과, 반대로 기대하면 안 되는 패턴

HOT는 매우 유용하지만 모든 workload에 equally 중요하지는 않다. 어디에 힘을 써야 할지 구분하는 것이 중요하다.

### HOT 효과가 큰 패턴

#### 1) 같은 row를 반복 갱신하는 workload

예를 들어 아래 같은 패턴이다.

- 주문 한 건이 짧은 시간 안에 여러 상태를 거침
- 잡 한 건이 lock, retry, finish 과정에서 여러 번 갱신됨
- 사용자 세션이나 presence row가 몇 초 단위로 갱신됨
- worker liveness row가 heartbeat마다 갱신됨

이런 경우는 row churn이 row 수보다 훨씬 크다. 즉 전체 row 수는 많지 않아도 update 수가 매우 높아질 수 있다. HOT가 살아 있으면 이런 churn을 꽤 효율적으로 흡수할 수 있다.

#### 2) 최신 상태만 중요하고 과거 이력은 다른 경로로 저장 가능한 workload

- 현재 배송 상태
- 현재 디바이스 연결 상태
- 현재 작업 상태
- 현재 세션 정보

이런 테이블은 본질적으로 snapshot 성격이 강하다. 따라서 snapshot row를 HOT-friendly하게 유지하고, 과거 변화는 append-only event 테이블로 빼는 전략이 잘 맞는다.

#### 3) row가 상대적으로 작고, 자주 바뀌는 컬럼 수가 제한적인 workload

row가 작을수록 같은 page 안에 새 version이 들어갈 확률이 높다. 그래서 큰 payload가 분리된 메타데이터 테이블, 작은 상태 테이블, counter/cache table은 HOT 최적화 여지가 크다.

### HOT가 덜 중요하거나 기대하면 안 되는 패턴

#### 1) 거의 append-only인 테이블

append-only fact table, 로그 적재 테이블, 이벤트 테이블은 HOT보다 insert path, checkpoint, WAL, partitioning이 더 중요하다.

#### 2) row 전체가 자주 커지거나 가변 길이 컬럼이 많이 변하는 테이블

예를 들어 작은 상태 수정이 아니라 큰 `jsonb`, 긴 `text`, 압축된 payload 자체가 자주 바뀌면 같은 page에 새 version을 넣기 어렵다. 이 경우 fillfactor만으로 해결하기 어렵다.

#### 3) 자주 바뀌는 컬럼으로 직접 탐색해야 하는 서비스 핵심 질의가 많은 경우

예를 들어 시스템 본질상 `status`, `updated_at`, `score` 기반 탐색이 매우 중요하다면, 인덱스 제거만으로 HOT를 높이는 선택이 불가능할 수 있다. 이 경우는 HOT를 일부 포기하고 다른 구조적 대안을 병행해야 한다.

- 읽기 replica 분리
- 보조 테이블/검색 엔진 사용
- summary table 운영
- queue/state/history 분리

즉 HOT는 강력하지만, **비즈니스 핵심 질의와 정면 충돌하면 타협 설계가 필요하다.**

---

## 실무 예시 4: 카운터와 순위 테이블에서 HOT를 오해하면 왜 위험할까

조회 수, 좋아요 수, 점수, 랭킹, 최근 활동성 같은 값은 자주 갱신되기 때문에 HOT를 떠올리기 쉽다. 하지만 이 영역은 의외로 함정이 많다.

예를 들어 아래 테이블을 보자.

```sql
CREATE TABLE posts (
  id bigint primary key,
  title text not null,
  like_count integer not null default 0,
  comment_count integer not null default 0,
  score numeric(12,4) not null default 0,
  updated_at timestamptz not null default now()
);
```

다음 update가 매우 자주 일어난다고 하자.

```sql
UPDATE posts
SET like_count = like_count + 1,
    score = score + 0.2,
    updated_at = now()
WHERE id = $1;
```

겉으로는 HOT-friendly할 수 있어 보인다. 하지만 제품 요구사항이 아래와 같다면 상황이 달라진다.

- 홈 피드가 `ORDER BY score DESC`를 핵심으로 사용
- 최근 활동 순 정렬이 중요해 `updated_at` 인덱스 필요
- 특정 기간 인기순 필터가 자주 실행

이 경우 자주 바뀌는 컬럼이 곧 핵심 정렬 키가 된다. 즉 인덱스를 뺄 수 없고 HOT도 기대하기 어렵다.

이런 도메인에서는 보통 다른 전략이 필요하다.

### 전략 1, 카운터와 정렬 모델 분리

실시간 증가 카운터는 write-friendly store나 집계 스트림에서 관리하고, 메인 OLTP row에는 주기적으로만 반영한다.

예를 들어 아래 흐름이 가능하다.

- 사용자 이벤트는 Kafka/Redis/append-only log로 수집
- 실시간 카운터는 별도 집계기에서 관리
- 메인 `posts` row는 초당/분당 배치로 묶어 업데이트

이렇게 하면 UPDATE 횟수 자체를 줄일 수 있다.

### 전략 2, 랭킹 테이블 분리

핵심 탐색이 `score DESC`라면 메인 테이블에 score 인덱스를 강하게 걸고 매번 갱신하는 대신, 별도 `post_rankings` 테이블을 두는 편이 나을 수 있다. 이 경우 메인 본문 row와 랭킹 row의 update 패턴을 분리할 수 있다.

### 전략 3, approximate/lagged ordering 허용

모든 점수 변경을 즉시 순위에 반영해야 하는지 제품 요구사항을 다시 볼 가치가 있다. 수 초~수 분 지연 허용이 가능하면 쓰기 비용을 크게 줄일 수 있다.

이 예시가 말해주는 것은 단순하다.

> HOT는 자주 바뀌는 값을 싸게 다루는 데 유리하지만, 그 값이 동시에 핵심 정렬/탐색 키라면 아키텍처 레벨 분리가 필요해진다.

---

## row 크기와 HOT의 관계: 왜 작은 메타데이터 테이블이 유리한가

HOT 조건을 이야기할 때 인덱스만 강조하면 절반만 본 것이다. 실제 운영에서는 row 크기가 HOT 성공률에 매우 큰 영향을 준다.

같은 page 안에 새 version이 들어가야 하므로, row가 크면 아래 문제가 생긴다.

- update 전후 값이 조금만 변해도 남는 공간이 부족해질 수 있다.
- TOAST 대상 컬럼, 가변 길이 컬럼이 섞이면 예측이 더 어려워진다.
- fillfactor를 낮춰도 큰 row는 page-local update 여유를 빨리 소진한다.

예를 들어 다음 두 설계를 비교해보자.

### 설계 A, 모든 것을 한 row에 저장

```sql
CREATE TABLE workflow_jobs (
  id bigint primary key,
  status text not null,
  attempts integer not null,
  locked_by text,
  updated_at timestamptz not null,
  payload jsonb not null,
  result jsonb,
  debug_log text,
  headers jsonb,
  metadata jsonb
);
```

### 설계 B, 자주 바뀌는 메타데이터와 큰 payload 분리

```sql
CREATE TABLE workflow_job_state (
  id bigint primary key,
  status text not null,
  attempts integer not null,
  locked_by text,
  updated_at timestamptz not null
);

CREATE TABLE workflow_job_payload (
  id bigint primary key references workflow_job_state(id),
  payload jsonb not null,
  result jsonb,
  debug_log text,
  headers jsonb,
  metadata jsonb
);
```

설계 B는 join이 필요해질 수 있지만, write path 관점에서는 장점이 크다.

- 자주 바뀌는 row가 작아져 HOT 성공 가능성이 높아진다.
- heap page당 저장되는 row 수가 많아진다.
- fillfactor가 남겨둔 여유 공간을 더 효율적으로 쓸 수 있다.
- 큰 payload 재기록이 드물어지면 WAL과 I/O도 줄어든다.

물론 모든 테이블을 이렇게 쪼갤 필요는 없다. 하지만 same-row churn이 심한 테이블에서 “큰 row를 작은 상태 row와 분리”하는 것은 HOT 뿐 아니라 전체 write path에 도움이 되는 경우가 많다.

---

## HOT와 autovacuum를 함께 봐야 하는 이유: HOT가 높아도 방치하면 성능이 떨어질 수 있다

HOT가 잘 되고 있다면 vacuum 부담이 줄 것 같지만, 현실은 조금 더 미묘하다. HOT chain이 쌓이고 pruning이 지연되면 다음 문제가 생길 수 있다.

- 같은 row에 여러 버전이 page 내에 남아 탐색 비용이 증가
- dead tuple이 heap 내부에 누적
- long transaction 때문에 pruning/vacuum 효과 지연
- table bloat가 서서히 증가

즉 HOT는 vacuum의 대체재가 아니라, **vacuum이 더 감당하기 쉬운 형태로 문제를 바꾸는 것**에 가깝다.

특히 아래 상황에서는 HOT 이점이 생각보다 빨리 잠식될 수 있다.

### 1) long transaction이 cleanup을 막는 경우

오래 열린 트랜잭션은 오래된 tuple version을 계속 살려둔다. HOT chain이 짧게 정리되지 못하면 page pruning 효과가 떨어지고 dead tuple 누적이 커진다.

### 2) update churn에 비해 autovacuum가 너무 늦는 경우

테이블이 빠르게 갱신되는데 autovacuum가 한참 뒤에 따라오면, HOT로 인덱스 비용은 줄였어도 heap 쪽 정리 지연이 병목이 될 수 있다.

### 3) 테이블별 workload 차이를 무시하고 전역 설정만 믿는 경우

HOT가 중요한 테이블은 대개 update churn이 매우 높다. 이런 테이블은 전역 autovacuum 설정만으로는 부족할 수 있다. 테이블별 storage parameter 조정이 필요할 수 있다.

예를 들어 아래처럼 테이블별 autovacuum 민감도를 조정할 수 있다.

```sql
ALTER TABLE jobs SET (
  autovacuum_vacuum_scale_factor = 0.02,
  autovacuum_analyze_scale_factor = 0.01
);
```

수치는 workload마다 다르지만, 핵심은 이것이다.

- HOT-friendly 테이블은 대개 write churn이 높다.
- write churn이 높으면 cleanup도 빨라야 한다.
- HOT optimization과 autovacuum tuning은 같이 가야 한다.

---

## 관측 전략: HOT 관련 변경을 할 때 어떤 그래프를 같이 봐야 할까

운영에서는 HOT ratio 하나만 보고 성공 판단하면 안 된다. 아래 그래프들을 같이 보는 것이 좋다.

### 1) update throughput 대비 HOT ratio

특정 테이블의 update 수가 늘어도 HOT ratio가 유지되는지, 아니면 피크 시간대에 급격히 떨어지는지 본다. 피크 시간에 HOT ratio가 무너지면 page free space가 빨리 고갈되거나 특정 코드 경로가 인덱스 컬럼까지 건드리는지 의심할 수 있다.

### 2) index size growth

HOT-friendly 변경 전후로 인덱스 크기 증가 속도가 둔화되는지 본다. absolute size보다 growth slope가 중요하다.

### 3) WAL bytes / minute

정확한 원인 분리는 어렵더라도, update-heavy 테이블 변경 직후 전체 WAL 양이 완만해지는지 보는 것은 의미 있다.

### 4) autovacuum duration과 빈도

HOT가 잘 되더라도 vacuum이 더 오래 걸리기 시작하면 heap cleanup 쪽 병목이 옮겨온 것일 수 있다. 즉 vacuum 빈도와 duration을 같이 본다.

### 5) replica replay lag

인덱스 churn 감소는 replica apply 부담 완화로 이어질 수 있다. 특히 write burst 시간대 replay lag 그래프 변화는 중요한 신호다.

### 6) application latency

궁극적으로는 p95/p99 update latency, 해당 엔드포인트의 timeout 비율, lock wait 증가 여부를 같이 봐야 한다. 내부 최적화가 실제 사용자 체감 개선으로 이어지는지 확인해야 한다.

---

## 실험 방법: HOT-friendly 변경을 어떻게 안전하게 검증할까

운영 DB에서 인덱스를 바로 지우고 fillfactor를 바꾸는 것은 부담이 크다. 아래처럼 단계적으로 검증하는 편이 안전하다.

### 단계 1, 변경 후보를 좁힌다

- update 수가 높은 테이블 상위 몇 개를 고른다.
- HOT ratio가 낮은 테이블을 우선 대상으로 잡는다.
- 그중 비즈니스 리스크가 상대적으로 낮은 테이블부터 시작한다.

### 단계 2, UPDATE 패턴을 실제 코드 수준에서 분해한다

많은 팀이 SQL 문장 종류만 보고 판단하지만, 더 중요한 것은 어떤 애플리케이션 경로가 어떤 컬럼을 얼마나 자주 바꾸는가다.

- 상태 전이 API
- heartbeat 배치
- retry worker
- backfill/maintenance job
- ORM이 자동으로 넣는 `updated_at`

특히 ORM의 자동 timestamp 갱신은 HOT를 망치는 주범일 수 있다. 프레임워크 관성으로 항상 `updated_at`를 업데이트하는지 확인할 가치가 크다.

### 단계 3, 읽기 경로 대체안을 준비한다

인덱스를 제거하거나 축소할 계획이라면, 그 인덱스를 쓰는 질의를 먼저 찾는다.

- 정말 운영 핵심 path인가
- replica로 우회 가능한가
- partial index로 충분한가
- materialized view나 summary table로 대체 가능한가

### 단계 4, 작은 범위에서 변경한다

가능하면 아래 중 하나로 실험한다.

- 유사한 staging/prod-like 환경에서 재현
- 파티션 구조라면 일부 파티션만 실험
- 영향이 제한된 보조 테이블부터 적용

### 단계 5, 관측 지표를 사전에 정의한다

변경 전후 비교 없이 “조금 좋아진 것 같다”는 식으로 가면 안 된다. 최소한 아래는 수집해야 한다.

- HOT ratio
- update latency
- WAL 증가 속도
- index growth slope
- replica lag
- vacuum duration

이렇게 하면 HOT 최적화가 감에 의존하는 DB 튜닝이 아니라, 운영 가능한 실험으로 바뀐다.

---

## 애플리케이션 계층에서 HOT를 깨는 코드 냄새

DB 설계만 보지 말고 애플리케이션 코드도 같이 봐야 한다. HOT를 자주 깨는 코드 패턴은 다음과 같다.

### 1) 의미 없는 `updated_at` 갱신

실제 비즈니스 상태는 안 변했는데, ORM save 훅 때문에 항상 `updated_at`만 바뀌는 경우가 많다. 이 자체가 인덱스 영향이나 row churn을 키울 수 있다.

### 2) 같은 row를 짧은 시간 안에 여러 번 나눠 업데이트

예를 들어 아래처럼 연속 update를 날리면 비싸다.

```sql
UPDATE jobs SET status = 'RUNNING' WHERE id = $1;
UPDATE jobs SET locked_at = now() WHERE id = $1;
UPDATE jobs SET updated_at = now() WHERE id = $1;
```

가능하면 한 번으로 묶는 편이 낫다.

```sql
UPDATE jobs
SET status = 'RUNNING',
    locked_at = now(),
    updated_at = now()
WHERE id = $1;
```

HOT가 되든 안 되든, update 횟수 자체를 줄이는 것이 우선이다.

### 3) 현재 상태 row에 분석용 메타데이터까지 같이 갱신

예를 들어 운영에 당장 필요 없는 디버그 정보, 외부 응답 원문, audit blob까지 현재 상태 row에 넣고 매번 함께 바꾸면 row가 커지고 HOT 여지가 줄어든다.

### 4) 재시도 로직이 같은 row를 과도하게 흔듦

짧은 재시도 주기에서 `attempts`, `last_error`, `updated_at`, `next_retry_at`를 계속 갱신하면, 실패 폭주 상황에서 특정 테이블이 전체 DB write hotspot이 될 수 있다. 이 경우 retry metadata를 별도 테이블이나 append-only log로 분리하는 편이 낫다.

---

## 설계 패턴 비교: HOT-friendly한 구조와 그렇지 않은 구조

아래 비교는 실무에서 꽤 자주 유용하다.

### 패턴 A, 현재 상태 + 이력 분리

**권장 상황**
- 현재 상태 row가 자주 갱신됨
- 과거 이벤트는 따로 보관 가능
- 운영성 질의와 분석성 질의가 다름

**장점**
- 현재 상태 테이블을 작고 HOT-friendly하게 유지 가능
- 이력은 append-only로 적재 가능
- 인덱스 요구사항을 두 테이블로 분리 가능

**단점**
- 쓰기 로직과 조회 로직이 조금 복잡해짐

### 패턴 B, 상태 row 하나에 모든 이력까지 누적

**장점**
- 구현이 단순해 보임

**단점**
- row가 커짐
- 자주 갱신되는 컬럼과 분석용 컬럼이 섞임
- 인덱스 요구가 늘어 HOT가 무너짐
- 장기 운영 비용이 커짐

### 패턴 C, 자주 바뀌는 컬럼을 별도 보조 테이블로 분리

예를 들어 `users`와 `user_presence`를 분리하는 식이다.

**장점**
- presence row는 작은 상태 snapshot으로 유지 가능
- 메인 엔터티 row는 비교적 안정적 유지
- workload별 fillfactor/인덱싱 정책을 따로 가져갈 수 있음

**단점**
- join 또는 별도 조회가 필요함

### 패턴 D, 자주 바뀌는 정렬 키를 메인 테이블에서 직접 유지

점수, 순위, 최근 활동성을 메인 엔터티에 즉시 반영하는 방식이다.

**장점**
- 조회가 직관적

**단점**
- HOT가 어려움
- 인덱스 churn이 큼
- 스케일이 커질수록 write path 비용 급증

이 비교의 결론은 간단하다. **HOT는 스토리지 기능이지만, 결국 데이터 모델 분리 설계가 받쳐줘야 살아난다.**

---

## 자주 받는 오해 정리

### 오해 1, HOT가 되면 UPDATE는 거의 공짜다

아니다. heap row version 생성, WAL 기록, cleanup 필요성은 여전히 존재한다. HOT는 특히 인덱스 유지 비용을 크게 줄여주는 것이다.

### 오해 2, fillfactor만 낮추면 HOT는 해결된다

아니다. 자주 바뀌는 컬럼에 인덱스가 있으면 HOT는 쉽게 깨진다. fillfactor는 필요조건 중 하나일 뿐이다.

### 오해 3, HOT ratio가 높으면 vacuum은 신경 안 써도 된다

아니다. HOT chain pruning과 dead tuple cleanup은 여전히 중요하다.

### 오해 4, 읽기 성능 인덱스는 일단 추가하고 나중에 쓰기 문제 생기면 스펙을 올리면 된다

대형 OLTP에서는 이 접근이 매우 비싸다. 인덱스는 스펙으로 상쇄되지 않는 구조적 write cost를 만든다.

### 오해 5, 모든 테이블에서 HOT ratio를 높여야 한다

그럴 필요 없다. append-only 테이블, 거의 update가 없는 기준정보 테이블, read-heavy 테이블은 우선순위가 다르다. HOT는 **update-heavy hotspot**에서 집중적으로 봐야 한다.

---

## 실제 의사결정에 도움 되는 간단한 판단 프레임

새 인덱스를 만들거나 테이블 구조를 바꾸려 할 때, 아래 네 질문에 답해보면 HOT 관점의 큰 실수를 많이 줄일 수 있다.

### 질문 1, 이 컬럼은 얼마나 자주 바뀌는가

하루 한 번 바뀌는 컬럼과 초당 수백 번 바뀌는 컬럼은 같은 인덱싱 기준을 적용하면 안 된다.

### 질문 2, 이 컬럼으로 직접 찾는 질의는 얼마나 중요한가

제품 핵심 사용자 흐름인지, 아니면 운영 편의성 질의인지 구분해야 한다.

### 질문 3, 이 조회를 다른 구조로 옮길 수 있는가

replica, summary table, event log, search index, materialized view 같은 대안이 있다면 primary OLTP row를 HOT-friendly하게 유지할 수 있다.

### 질문 4, 이 row는 작게 유지할 수 있는가

자주 바뀌는 row가 작을수록 HOT 가능성이 높아진다. 큰 payload나 rarely updated blob을 분리할 수 있다면 적극 검토할 만하다.

이 네 질문만 습관화해도, “인덱스는 많을수록 좋다”는 초기 설계를 꽤 많이 교정할 수 있다.

---

## 리팩터링 사례: HOT를 염두에 둔 주문 처리 테이블 재설계

조금 더 현실적인 시나리오를 보자. 전자상거래 서비스에서 `order_processing` 테이블이 있다고 하자.

```sql
CREATE TABLE order_processing (
  order_id bigint primary key,
  status text not null,
  payment_status text not null,
  shipment_status text,
  retry_count integer not null default 0,
  last_error text,
  assigned_worker text,
  updated_at timestamptz not null default now(),
  last_event_at timestamptz,
  payload jsonb not null,
  audit jsonb
);

CREATE INDEX idx_order_processing_status ON order_processing (status);
CREATE INDEX idx_order_processing_payment_status ON order_processing (payment_status);
CREATE INDEX idx_order_processing_updated_at ON order_processing (updated_at);
CREATE INDEX idx_order_processing_last_event_at ON order_processing (last_event_at);
```

운영 지표는 아래와 같았다.

- 주문 상태 전이와 재시도 때문에 동일 row update가 매우 많음
- replica lag가 결제 피크 시간마다 증가
- `updated_at` 기반 백오피스 조회는 잦지 않음
- `payload`와 `audit`이 커서 row size가 큼
- HOT ratio는 낮고 autovacuum 빈도는 높음

이 테이블을 HOT 친화적으로 바꾸려면 단순히 인덱스 하나만 삭제해서 끝나지 않는다. 보통 아래 순서로 생각해야 한다.

### 단계 1, 역할 분리

현재 상태와 큰 payload, audit 정보를 분리한다.

```sql
CREATE TABLE order_processing_state (
  order_id bigint primary key,
  status text not null,
  payment_status text not null,
  shipment_status text,
  retry_count integer not null default 0,
  last_error text,
  assigned_worker text,
  updated_at timestamptz not null default now(),
  last_event_at timestamptz
);

CREATE TABLE order_processing_payload (
  order_id bigint primary key references order_processing_state(order_id),
  payload jsonb not null,
  audit jsonb
);
```

이렇게 하면 자주 바뀌는 상태 row가 훨씬 작아진다.

### 단계 2, 인덱스 재검토

실제 핵심 조회가 무엇인지 다시 본다.

- 운영 워커는 `status = 'READY'` 또는 `payment_status = 'PENDING_CAPTURE'` 같은 좁은 조건만 중요
- 백오피스의 `updated_at` 범위 탐색은 빈도가 낮음
- 상세 이력은 event log나 별도 테이블에서 확인 가능

그러면 전체 범용 인덱스보다 이런 쪽이 나을 수 있다.

```sql
CREATE INDEX idx_ops_ready_orders
ON order_processing_state (order_id)
WHERE status = 'READY';

CREATE INDEX idx_ops_pending_capture
ON order_processing_state (order_id)
WHERE payment_status = 'PENDING_CAPTURE';
```

partial index라고 해서 HOT가 자동으로 보장되는 것은 아니지만, 최소한 “모든 상태값 전체 인덱스”보다 관리 비용을 더 좁힐 수 있다.

### 단계 3, `updated_at` 재평가

백오피스가 정말 실시간 최신순 정렬을 primary에서 직접 해야 하는가를 다시 묻는다.

- 꼭 필요 없다면 인덱스를 제거한다.
- 필요하면 replica, 검색 인덱스, 이벤트 로그 조회로 우회한다.
- 최근 1시간 장애 분석 정도라면 운영용 별도 테이블이나 대시보드 materialization을 고려한다.

이 질문을 통과하지 못하는 `updated_at` 인덱스는 매우 자주 HOT를 망친다.

### 단계 4, fillfactor 조정

`order_processing_state`가 같은 row를 여러 번 갱신한다면 아래처럼 fillfactor를 조정해볼 수 있다.

```sql
ALTER TABLE order_processing_state SET (fillfactor = 80);
```

수치는 예시일 뿐이지만, 핵심은 이 테이블이 update churn이 큰 snapshot table이라는 점이다.

### 단계 5, 운영 검증

변경 후 다음을 비교한다.

- HOT ratio 상승 여부
- 인덱스 증가 속도 둔화 여부
- 결제 피크 시간 replica lag 완화 여부
- update latency 개선 여부

이 사례가 보여주는 것은, HOT optimization이 결국 **인덱스 몇 개를 건드리는 미세 조정이 아니라 테이블 책임을 다시 나누는 작업**이라는 점이다.

---

## 설계 리뷰 매트릭스: 어떤 컬럼을 인덱싱하고, 어떤 컬럼은 피해야 할까

아래 매트릭스는 정답표가 아니라, 인덱스를 고민할 때 팀이 함께 검토하기 좋은 판단 틀이다.

| 컬럼 성격 | 변경 빈도 | 조회 중요도 | HOT 친화성 | 일반적 판단 |
| --- | --- | --- | --- | --- |
| 기본 키, 외래 키 | 낮음 | 매우 높음 | 영향 적음 | 인덱스 유지 |
| 상태값(status) | 높음 | 상황별 상이 | 낮아지기 쉬움 | 전체 인덱스보다 partial 검토 |
| `updated_at` | 매우 높음 | 종종 과대평가 | 낮아지기 쉬움 | 습관적 인덱싱 금지 |
| `last_seen_at`, `heartbeat_at` | 매우 높음 | 운영 핵심 아님이 많음 | 매우 낮음 | snapshot/event 분리 검토 |
| counter/score/rank | 매우 높음 | 탐색 키면 충돌 큼 | 낮음 | 집계 분리 검토 |
| payload/jsonb 대형 컬럼 | 중간 | 직접 탐색 드묾 | row 크기 불리 | 분리/정규화 검토 |
| 생성 시점 `created_at` | 낮음 | 범위 조회 자주 있음 | 상대적 영향 적음 | 활용도 높으면 인덱스 가능 |

이 매트릭스에서 가장 중요한 포인트는 이것이다.

- 변경 빈도와 조회 중요도를 분리해서 봐야 한다.
- 조회 중요도가 낮거나 대체 가능하면, 자주 바뀌는 컬럼 인덱스는 매우 신중해야 한다.
- HOT를 살리려면 “변경 빈도 높은 컬럼”을 먼저 주의 깊게 봐야 한다.

---

## HOT 관점에서 ORM 사용 시 주의할 점

많은 팀이 PostgreSQL 문제를 DB 레이어에서만 찾지만, 실제로는 ORM 기본 동작이 HOT를 깨는 경우가 많다.

### 1) dirty field가 아닌 전체 row update

일부 ORM이나 구현 습관은 실제로 바뀐 컬럼만 업데이트하지 않고, 엔터티 전체를 다시 쓰는 방식으로 동작한다. 이 경우 불필요한 컬럼 갱신이 늘고, 자주 바뀌는 인덱스 컬럼까지 매번 손대게 될 수 있다.

### 2) 자동 timestamp 컬럼 갱신

프레임워크가 save 시마다 무조건 `updated_at`를 갱신하면, 비즈니스적으로 의미 없는 write churn이 발생한다. 특히 `updated_at` 인덱스가 있으면 HOT 기회가 계속 사라진다.

### 3) 불필요한 optimistic locking 컬럼 증가

버전 컬럼 자체는 유용할 수 있지만, 모든 write path에서 의미 없이 version bump를 강제하면 same-row churn을 더 키울 수 있다. 버전 관리가 필요한 경로와 그렇지 않은 경로를 구분할 필요가 있다.

### 4) JSON blob 전체 재직렬화

애플리케이션에서 일부 필드만 바뀌었는데 ORM이 큰 JSON 문서를 통째로 다시 저장하면 row 크기와 WAL 비용이 크게 증가한다. HOT는 물론 일반 write path 전체가 나빠진다.

즉 ORM을 쓴다고 해서 HOT를 포기해야 하는 것은 아니지만, 다음 질문은 꼭 해봐야 한다.

- 실제로 바뀐 컬럼만 update하는가
- `updated_at` 자동 갱신이 정말 필요한가
- 대형 payload를 통째로 다시 쓰고 있지 않은가
- 재시도 루프에서 같은 row를 짧은 간격으로 반복 저장하고 있지 않은가

---

## 장애 대응 관점: HOT를 모르면 왜 원인 분석이 늦어질까

운영 사고 중에는 증상은 분명한데 원인 해석이 틀려 대응이 늦어지는 경우가 많다. HOT를 모르면 특히 아래 상황에서 오판하기 쉽다.

### 상황 1, CPU는 여유 있는데 UPDATE 지연과 replica lag가 증가한다

이때 많은 팀은 네트워크나 스토리지 성능만 먼저 본다. 물론 맞을 수 있다. 하지만 동시에 확인해야 할 것은 아래다.

- 최근 새 인덱스가 추가되지 않았는가
- `updated_at` 인덱스가 write-heavy 테이블에 붙지 않았는가
- 특정 코드 변경으로 자주 바뀌는 컬럼이 늘지 않았는가
- HOT ratio가 급격히 낮아지지 않았는가

즉 write path 악화는 하드웨어 부족이 아니라, **인덱스와 HOT 조건 붕괴**에서 시작될 수 있다.

### 상황 2, vacuum은 열심히 도는데 테이블과 인덱스가 계속 커진다

이 경우도 단순히 vacuum aggressiveness를 올리는 것으로 끝나지 않을 수 있다. 일반 update가 계속 dead index tuple을 만들고 있다면, cleanup이 생성 속도를 따라가지 못할 수 있다.

### 상황 3, 특정 테이블만 유난히 WAL을 많이 만든다

대량 insert보다 자주 바뀌는 상태 row가 더 큰 문제일 수 있다. 특히 여러 인덱스가 붙은 churn-heavy table은 규모에 비해 WAL 기여도가 과도할 수 있다.

### 상황 4, 장애 후 백필이나 재처리 작업이 write path를 망가뜨린다

재처리 스크립트가 같은 row를 여러 번 갱신하고, 그 row가 HOT-friendly하지 않으면 장애 복구 과정 자체가 또 다른 write storm가 된다.

즉 HOT는 평상시 최적화 주제이기도 하지만, **장애 시 어떤 테이블이 시스템을 흔드는지 해석하는 기준**이기도 하다.

---

## 언제 테이블 분리보다 파이프라인 변경이 더 효과적일까

모든 문제를 테이블 분리로 해결할 수는 없다. 경우에 따라서는 UPDATE 자체를 줄이는 편이 더 강력하다.

예를 들어 아래 상황을 생각해보자.

- 좋아요 수가 초당 수만 건 증가
- 모든 증가를 메인 row에 즉시 반영
- score/랭킹도 함께 바뀜
- 조회는 실시간에 가깝게 필요

이 경우 HOT를 아무리 고민해도 근본은 "너무 많은 update"일 수 있다. 그럴 때는 다음 구조가 더 맞는다.

### 1) write coalescing

짧은 시간의 여러 증가 이벤트를 메모리/스트림/큐에서 합쳐 한 번에 반영한다.

### 2) append-only event + async materialization

이벤트는 append-only로 적재하고, 현재 상태 row는 주기적으로 materialize한다.

### 3) cache-first counter

초당 고빈도 카운터는 Redis 같은 캐시 계층에서 흡수하고, DB 반영은 배치화한다.

### 4) domain split

랭킹, 분석, 운영 현재 상태를 다른 저장 구조가 담당하게 한다.

즉 HOT는 중요하지만, update volume 자체를 줄이는 전략과 같이 봐야 한다. **HOT는 비싼 UPDATE를 덜 비싸게 만드는 기술이고, 파이프라인 변경은 UPDATE 자체를 덜 하게 만드는 기술**이다.

---

## 팀 운영 습관으로 만들면 좋은 규칙

아래 규칙은 단순하지만 효과가 크다.

### 규칙 1, 새 인덱스 PR에는 "이 컬럼은 얼마나 자주 바뀌는가"를 반드시 적는다

인덱스 리뷰에서 읽기 쿼리만 보지 말고, write cost를 같이 적게 하면 HOT를 망치는 인덱스를 초기에 많이 걸러낼 수 있다.

### 규칙 2, `updated_at` 인덱스는 기본 금지, 예외 승인 방식으로 둔다

많은 서비스에서 이 규칙 하나만으로 write path가 훨씬 건강해진다.

### 규칙 3, churn-heavy table은 설계 문서에 fillfactor와 vacuum 전략을 같이 기록한다

스키마만 적지 말고 운영 가정도 함께 적는 편이 좋다.

### 규칙 4, snapshot table과 history table을 의식적으로 분리한다

처음부터 역할을 나누면 나중에 HOT 문제로 뒤늦게 대수술할 일을 줄일 수 있다.

### 규칙 5, 성능 회고에서 HOT ratio와 dead tuple도 본다

API latency, CPU, QPS만 보지 말고 스토리지 계층의 write health를 같이 보는 문화가 중요하다.

---

## 체크리스트: PostgreSQL UPDATE가 비싸게 느껴질 때 HOT 관점에서 점검할 것

- [ ] 문제 테이블이 실제로 update-heavy한가, 아니면 insert-heavy한가
- [ ] `pg_stat_user_tables`에서 `n_tup_upd`, `n_tup_hot_upd`, `hot_ratio_pct`를 확인했는가
- [ ] 자주 바뀌는 컬럼 목록을 뽑았는가
- [ ] 그 컬럼들이 인덱스 키, partial predicate, expression index에 포함되는지 확인했는가
- [ ] `updated_at`, `last_seen_at`, `heartbeat_at` 인덱스를 습관적으로 두고 있지 않은가
- [ ] row가 지나치게 커서 같은 page에 새 version이 들어가기 어렵지 않은가
- [ ] 큰 `jsonb`나 rarely updated payload를 분리할 수 있는가
- [ ] 현재 상태와 이벤트/이력을 분리할 수 있는가
- [ ] fillfactor를 테이블 특성에 맞게 조정할 가치가 있는가
- [ ] 인덱스 제거 전 읽기 대체 경로를 준비했는가
- [ ] 변경 후 WAL, replica lag, vacuum, index growth를 비교 측정할 계획이 있는가

---

## 한 줄 정리

**PostgreSQL에서 UPDATE 비용을 진짜로 낮추고 싶다면 쿼리만 보지 말고, 자주 바뀌는 컬럼의 인덱스, row 크기, fillfactor, 상태/이력 분리를 함께 설계해 HOT Update가 살아날 공간부터 만들어야 한다.**
