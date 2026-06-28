---
layout: post
title: "PostgreSQL Advisory Lock 실전: pg_advisory_xact_lock, Try Lock, 트랜잭션 경계로 애플리케이션 분산락을 안전하게 다루는 법"
date: 2026-06-28 11:50:00 +0900
categories: [sql]
tags: [study, sql, postgresql, advisory-lock, pg-advisory-xact-lock, try-lock, transaction, concurrency, distributed-lock, operations]
permalink: /sql/2026/06/28/study-postgresql-advisory-lock-transaction-session-try-lock-deadlock.html
---

## 배경: "DB row가 아직 없는데 무엇을 잠글 것인가"라는 문제가 있다

PostgreSQL 동시성 제어를 이야기하면 보통 먼저 떠올리는 것은 row lock이다.

```sql
SELECT *
FROM orders
WHERE id = $1
FOR UPDATE;
```

이미 존재하는 주문, 계좌, 쿠폰, 재고 row를 바꿀 때는 이 방식이 직관적이다. 트랜잭션이 대상 row를 잠그고, 다른 트랜잭션은 같은 row를 동시에 수정하지 못한다. 문제는 실무에서 잠그고 싶은 대상이 항상 테이블 row로 예쁘게 존재하지 않는다는 점이다.

예를 들어 아래 상황을 보자.

- 아직 생성되지 않은 월별 정산 row를 테넌트별로 하나만 만들고 싶다.
- 같은 고객의 대량 포인트 재계산 작업이 동시에 두 번 돌면 안 된다.
- 특정 외부 API 동기화 작업은 서비스 전체에서 한 번만 실행되어야 한다.
- 캐시 재생성, 리포트 생성, 파일 변환처럼 결과물은 하나인데 요청은 여러 개 들어온다.
- 마이그레이션 전 보정 배치가 여러 워커에서 실행되지만 같은 shard를 중복 처리하면 안 된다.
- `INSERT ... ON CONFLICT`만으로는 충분하지 않은 여러 단계의 검증과 쓰기 흐름이 있다.
- row lock을 걸기 위해 "잠금용 row" 테이블을 만들었지만, 그 테이블이 다시 병목과 정리 대상이 되었다.

이때 자주 나오는 반응은 둘 중 하나다.

1. Redis 같은 외부 분산락을 붙인다.
2. PostgreSQL 안에 lock table을 직접 만든다.

둘 다 유효한 선택일 수 있다. 하지만 PostgreSQL을 이미 강한 일관성의 중심 저장소로 쓰고 있고, 잠금 범위가 DB 트랜잭션과 강하게 연결되어 있다면 먼저 검토할 만한 도구가 있다. 바로 **Advisory Lock**이다.

Advisory Lock은 PostgreSQL이 제공하는 애플리케이션 정의 잠금이다. row나 table 같은 물리 객체를 PostgreSQL이 자동으로 해석해서 잠그는 것이 아니라, 개발자가 숫자 key를 정하고 그 key에 대해 협력적으로 잠금을 건다.

```sql
SELECT pg_advisory_xact_lock(42);
```

이 쿼리는 "42라는 의미를 가진 어떤 업무 자원"에 대해 현재 트랜잭션이 끝날 때까지 advisory lock을 잡는다. PostgreSQL은 42가 고객인지, 테넌트인지, 월별 정산인지, 파일인지 모른다. 그 의미는 애플리케이션과 SQL 설계가 정한다.

그래서 advisory lock은 강력하지만 위험하다. 좋은 곳에 쓰면 불필요한 lock table 없이 깔끔한 직렬화 지점을 만들 수 있다. 나쁜 곳에 쓰면 코드만 봐서는 어떤 업무가 왜 막히는지 알 수 없는 숨은 전역 락이 된다.

이번 글은 `pg_advisory_lock` 함수 목록을 외우는 글이 아니다. 중급 이상 개발자가 운영 서비스에서 advisory lock을 도입할 때 반드시 판단해야 하는 기준을 정리한다.

이번 글에서 답하려는 질문은 아래와 같다.

1. Advisory Lock은 row lock, unique constraint, Redis lock과 무엇이 다른가?
2. session-level lock과 transaction-level lock은 왜 완전히 다른 운영 위험을 갖는가?
3. `pg_advisory_xact_lock`과 `pg_try_advisory_xact_lock`은 각각 언제 써야 하는가?
4. 업무 key를 64-bit integer 또는 2개의 32-bit integer로 어떻게 안정적으로 매핑할 것인가?
5. deadlock, connection pool, timeout, retry는 advisory lock과 어떻게 연결되는가?
6. 작업 큐, 정산, idempotency, 스케줄러에서 어떤 패턴이 실무적으로 안전한가?
7. 도입 후 어떤 관측 지표와 운영 체크리스트가 필요한가?

핵심 결론부터 말하면 이렇다.

1. Advisory Lock은 "DB가 모르는 업무 자원"을 PostgreSQL lock manager에 올리는 도구다.
2. 대부분의 웹 애플리케이션에서는 session-level보다 **transaction-level advisory lock**이 기본 선택이다.
3. advisory lock은 정합성을 보장하는 마지막 방어선이 아니라, **명시적 constraint와 idempotency를 보조하는 직렬화 장치**여야 한다.
4. lock key 설계는 코드 스타일 문제가 아니라 운영 계약이다. 충돌, 네임스페이스, 재현 가능성이 중요하다.
5. `try lock`은 실패를 정상 흐름으로 다룰 수 있을 때만 좋다. 무한 재시도는 일반 lock 대기보다 더 나쁘다.
6. connection pool을 쓰는 서비스에서 session-level lock을 부주의하게 쓰면 락이 요청 경계를 넘어 새어나갈 수 있다.
7. 좋은 advisory lock 설계는 "잠그는 법"보다 **언제 잠그지 않을지, 얼마나 기다릴지, 실패를 어떻게 복구할지**를 더 먼저 정한다.

---

## 핵심 개념: Advisory Lock은 PostgreSQL이 의미를 모르는 협력적 잠금이다

PostgreSQL의 일반 lock은 DB 객체와 연결된다.

- row lock: 특정 tuple 변경 충돌 방지
- table lock: DDL, 대량 작업, 명시적 `LOCK TABLE`
- relation lock: 쿼리 실행 중 schema 변경 충돌 방지
- predicate lock: serializable isolation에서 충돌 감지

반면 advisory lock은 PostgreSQL이 업무 의미를 해석하지 않는다.

```sql
SELECT pg_advisory_xact_lock(1001);
```

PostgreSQL 입장에서 `1001`은 그냥 숫자다. 이 값이 tenant 1001인지, account 1001인지, `billing:2026-06`인지 알 수 없다. 그렇기 때문에 advisory lock은 "강제"보다 "협력"에 가깝다.

같은 업무 자원을 건드리는 모든 코드 경로가 같은 key 규칙으로 advisory lock을 잡아야 효과가 있다. 한 코드 경로가 lock을 잡고 다른 코드 경로가 무시하면 PostgreSQL은 자동으로 막아주지 않는다.

이 점이 row lock과 가장 큰 차이다.

```sql
-- 트랜잭션 A
BEGIN;
SELECT *
FROM accounts
WHERE id = 10
FOR UPDATE;

-- 트랜잭션 B
UPDATE accounts
SET balance = balance + 100
WHERE id = 10;
```

트랜잭션 B가 `FOR UPDATE`를 몰라도 같은 row를 수정하면 PostgreSQL은 충돌을 안다. 하지만 advisory lock은 다르다.

```sql
-- 트랜잭션 A
BEGIN;
SELECT pg_advisory_xact_lock(10);

-- 트랜잭션 B
UPDATE accounts
SET balance = balance + 100
WHERE id = 10;
```

트랜잭션 B는 advisory lock key 10을 전혀 보지 않는다. 그냥 update가 실행된다. 그래서 advisory lock은 데이터 무결성의 유일한 방어선이 되면 안 된다.

실무 원칙은 간단하다.

> **DB가 자연스럽게 알 수 있는 정합성은 constraint와 row lock으로 지키고, DB가 모르는 업무 단위의 중복 실행만 advisory lock으로 좁혀라.**

예를 들어 "주문 번호는 유일해야 한다"는 unique constraint가 맞다. "이 고객의 월별 포인트 재계산 작업은 한 번만 돌자"는 advisory lock이 어울릴 수 있다.

---

## Advisory Lock 함수군: session-level과 transaction-level을 먼저 나눠야 한다

PostgreSQL advisory lock 함수는 크게 두 계열로 나뉜다.

| 계열 | 대표 함수 | 해제 시점 | 웹 서비스 기본 적합도 |
| --- | --- | --- | --- |
| Session-level | `pg_advisory_lock`, `pg_try_advisory_lock`, `pg_advisory_unlock` | 명시적 unlock 또는 세션 종료 | 낮음 |
| Transaction-level | `pg_advisory_xact_lock`, `pg_try_advisory_xact_lock` | 트랜잭션 종료 시 자동 해제 | 높음 |

둘의 차이는 문법보다 운영 위험에서 훨씬 크다.

### session-level lock

```sql
SELECT pg_advisory_lock(123);

-- 작업 수행

SELECT pg_advisory_unlock(123);
```

session-level lock은 DB connection 세션에 붙는다. 트랜잭션이 commit되거나 rollback되어도 자동으로 풀리지 않는다. 명시적으로 unlock하거나 connection이 끊겨야 풀린다.

이 특성은 장기 실행 작업이나 수동 운영 작업에는 유용할 수 있다. 하지만 일반적인 웹 애플리케이션에서는 조심해야 한다. 대부분의 서버는 connection pool을 쓰기 때문이다.

예를 들어 요청 A가 connection 7번에서 session-level advisory lock을 잡았는데, 예외 처리 경로에서 unlock을 못 했다고 하자. 요청 A의 트랜잭션은 rollback되었고 connection은 pool로 돌아간다. 이후 요청 B가 같은 connection을 빌리면 어떻게 될까?

- DB 세션은 여전히 lock을 들고 있다.
- 애플리케이션 요청 경계는 이미 끝났다.
- lock을 잡은 업무 주체가 사라졌다.
- 다른 요청이 이상한 대기 상태를 만들 수 있다.

이건 디버깅하기 어렵다. 코드에는 요청 A가 끝난 것으로 보이고, DB에는 세션이 살아 있으며, lock은 계속 유지된다.

### transaction-level lock

```sql
BEGIN;

SELECT pg_advisory_xact_lock(123);

-- 작업 수행

COMMIT;
```

transaction-level advisory lock은 현재 트랜잭션이 끝나면 자동으로 해제된다. rollback되어도 해제된다.

웹 요청, 워커 job, API mutation처럼 작업 단위가 DB 트랜잭션과 맞물리는 경우에는 이 방식이 대체로 안전하다.

실무 기본값은 아래처럼 잡는 편이 좋다.

> **특별한 이유가 없으면 `pg_advisory_xact_lock`을 쓰고, session-level lock은 운영자가 의식적으로 unlock lifecycle을 관리할 수 있을 때만 쓴다.**

이 원칙 하나만 지켜도 advisory lock 장애의 상당수를 피할 수 있다.

---

## key 설계: 숫자 하나를 정하는 일이 아니라 네임스페이스 계약을 만드는 일이다

Advisory lock은 key를 받는다. PostgreSQL에는 대표적으로 두 형태가 있다.

```sql
-- 64-bit signed integer 하나
SELECT pg_advisory_xact_lock(922337203685477580);

-- 32-bit integer 두 개
SELECT pg_advisory_xact_lock(10, 202606);
```

둘 중 무엇을 쓸지는 팀의 key 설계 방식에 달려 있다. 중요한 것은 **같은 업무 자원은 항상 같은 key로 매핑되고, 다른 업무 자원은 가능한 한 다른 key로 매핑되어야 한다**는 점이다.

### 나쁜 key 설계

아래는 위험하다.

```sql
SELECT pg_advisory_xact_lock($1);
```

처음에는 `$1`이 tenant id라고 생각했을 수 있다. 그런데 다른 팀이 같은 방식으로 account id에도 `$1`을 쓰면 어떻게 될까?

- tenant 42 작업과 account 42 작업이 서로 막는다.
- 대기 원인을 봐도 key 42만 보인다.
- 업무적으로 무관한 작업이 한 lock namespace에 섞인다.

advisory lock key는 전역 공간이다. 그래서 반드시 네임스페이스를 설계해야 한다.

### 두 개의 integer를 네임스페이스로 쓰는 방식

실무에서는 2-argument 함수를 쓰면 읽기 쉽다.

```sql
-- namespace 10: tenant monthly billing
-- key 20260642: 2026-06 + tenant 42 같은 업무 key
SELECT pg_advisory_xact_lock(10, 20260642);
```

하지만 두 번째 값에 여러 의미를 억지로 이어 붙이면 범위가 금방 애매해진다. 더 나은 방식은 업무 key를 안정적인 integer로 변환하는 별도 규칙을 둔다.

예를 들어 네임스페이스를 코드 상수로 관리한다.

```text
1 = tenant_monthly_billing
2 = customer_point_recalculation
3 = external_vendor_sync
4 = report_generation
```

그리고 두 번째 key는 해당 namespace 안에서만 의미를 갖게 한다.

```sql
SELECT pg_advisory_xact_lock(1, :tenant_id);
```

월별 단위까지 들어가야 한다면 `(namespace, hashed_business_key)` 방식이 더 단순할 수 있다.

```sql
-- 애플리케이션에서 "tenant:42:month:2026-06"을 32-bit signed int로 안정 해시
SELECT pg_advisory_xact_lock(1, :hashed_key);
```

### 해시를 쓸 때 주의할 점

문자열 업무 key를 integer로 바꾸려면 해시가 필요하다. 이때 주의할 점은 세 가지다.

1. 프로세스마다 달라지는 hash를 쓰면 안 된다.
2. 언어 버전이나 runtime seed에 따라 값이 달라지면 안 된다.
3. 충돌 가능성을 받아들일 수 있는 namespace에만 써야 한다.

예를 들어 Python의 기본 `hash()`는 프로세스마다 달라질 수 있다. 이런 값을 advisory lock key로 쓰면 배포나 재시작 후 같은 업무 자원이 다른 lock key로 매핑될 수 있다. 반드시 안정 해시를 써야 한다.

애플리케이션에서 해시를 만들기보다 PostgreSQL 안에서 `hashtextextended` 같은 함수를 쓰는 방법도 있다. 다만 내장 hash 함수의 버전 호환성과 충돌 가능성, signed integer 범위를 팀 표준으로 명확히 해야 한다.

중요한 것은 "어떻게든 숫자로 만들기"가 아니다.

> **lock key는 운영자가 로그와 DB에서 재현할 수 있어야 한다.**

장애 중에 `advisory lock key = 181920182`만 보고 아무도 어떤 고객, 어떤 리포트, 어떤 배치인지 모른다면 key 설계가 실패한 것이다.

---

## 실무 패턴 1: 월별 정산 row를 중복 생성하지 않기

가장 단순한 예시부터 보자. 테넌트별 월별 정산을 생성하는 작업이 있다.

```sql
CREATE TABLE tenant_monthly_settlements (
  tenant_id bigint NOT NULL,
  settlement_month date NOT NULL,
  status text NOT NULL,
  total_amount numeric(18, 2) NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, settlement_month)
);
```

이 테이블에는 이미 primary key가 있다. 그러면 advisory lock이 필요 없을까? 경우에 따라 다르다.

단순히 row 하나를 만들기만 한다면 아래로 충분하다.

```sql
INSERT INTO tenant_monthly_settlements (
  tenant_id,
  settlement_month,
  status
)
VALUES ($1, $2, 'CREATING')
ON CONFLICT (tenant_id, settlement_month) DO NOTHING;
```

하지만 실제 정산 생성은 대개 더 복잡하다.

1. 대상 주문 범위를 계산한다.
2. 환불, 취소, 수수료 정책을 적용한다.
3. 중간 집계 row를 만든다.
4. 정산 row를 만든다.
5. 파일을 생성하거나 외부 시스템에 전송한다.

이 전체 흐름을 동시에 두 번 돌리면 primary key 충돌만으로는 충분하지 않을 수 있다. 한쪽은 중간 테이블을 만들었고, 다른 쪽은 일부 상태를 읽어 진행할 수 있다. 이럴 때 업무 단위 lock을 먼저 잡아 흐름 자체를 직렬화할 수 있다.

```sql
BEGIN;

SELECT pg_advisory_xact_lock(
  1,
  hashtext(format('tenant:%s:month:%s', $1, to_char($2::date, 'YYYY-MM')))
);

INSERT INTO tenant_monthly_settlements (
  tenant_id,
  settlement_month,
  status
)
VALUES ($1, $2, 'CREATING')
ON CONFLICT (tenant_id, settlement_month)
DO UPDATE
SET updated_at = now()
WHERE tenant_monthly_settlements.status IN ('FAILED', 'CREATING');

-- 같은 트랜잭션 안에서 필요한 상태 전이와 중간 데이터 생성

COMMIT;
```

여기서 중요한 점은 advisory lock만 믿지 않는다는 것이다.

- primary key는 여전히 존재한다.
- status 전이 조건이 있다.
- 재시도 가능한 상태만 갱신한다.
- 트랜잭션이 끝나면 lock은 자동 해제된다.

advisory lock은 "동시에 같은 정산 흐름이 두 개 출발하는 상황"을 줄인다. 하지만 최종 무결성은 primary key와 상태 전이가 지킨다.

---

## 실무 패턴 2: 이미 실행 중이면 기다리지 않고 빠르게 포기하기

모든 lock이 기다려야 하는 것은 아니다. 예를 들어 리포트 재생성 요청이 동시에 여러 번 들어온다고 하자. 이미 같은 리포트가 생성 중이면 두 번째 요청은 "이미 진행 중"으로 응답해도 된다.

이때는 blocking lock보다 try lock이 낫다.

```sql
BEGIN;

SELECT pg_try_advisory_xact_lock(4, :report_key) AS acquired;
```

애플리케이션은 결과를 보고 분기한다.

```text
acquired = true  -> 리포트 생성 시작
acquired = false -> 202 Accepted 또는 409 Conflict로 "이미 생성 중" 응답
```

SQL만으로 표현하면 이런 구조가 된다.

```sql
WITH lock_attempt AS (
  SELECT pg_try_advisory_xact_lock(4, :report_key) AS acquired
)
INSERT INTO report_jobs (
  report_key,
  status,
  requested_by,
  created_at
)
SELECT
  :report_key,
  'RUNNING',
  :user_id,
  now()
FROM lock_attempt
WHERE acquired
RETURNING id;
```

결과 row가 없으면 lock을 얻지 못한 것이다. 이 경우 애플리케이션은 굳이 DB에서 오래 기다릴 필요가 없다.

이 패턴의 장점은 명확하다.

- 사용자 요청 thread가 오래 막히지 않는다.
- 이미 진행 중인 작업을 중복 시작하지 않는다.
- 실패가 예외가 아니라 정상 비즈니스 상태가 된다.

하지만 주의할 점도 있다.

`try lock` 실패 후 즉시 재시도 루프를 돌리면 오히려 busy-wait가 된다. 특히 여러 인스턴스가 동시에 같은 key에 대해 초당 수십 번 재시도하면 DB에는 짧은 쿼리 폭탄이 된다.

try lock을 쓸 때는 실패 정책을 같이 정해야 한다.

- 사용자에게 "이미 처리 중"을 반환한다.
- 다음 스케줄 주기까지 미룬다.
- exponential backoff를 둔다.
- 중복 요청을 별도 테이블에 합치고 첫 작업 완료 후 결과를 공유한다.

즉 try lock은 "기다리지 않는다"가 핵심이지 "계속 찔러본다"가 핵심이 아니다.

---

## 실무 패턴 3: 작업 큐에서 shard 단위 중복 실행 막기

PostgreSQL 작업 큐에서는 보통 `FOR UPDATE SKIP LOCKED`를 먼저 검토한다.

```sql
WITH picked AS (
  SELECT id
  FROM jobs
  WHERE status = 'PENDING'
  ORDER BY id
  LIMIT 100
  FOR UPDATE SKIP LOCKED
)
UPDATE jobs j
SET status = 'RUNNING',
    started_at = now()
FROM picked
WHERE j.id = picked.id
RETURNING j.id;
```

이 패턴은 job row 자체를 여러 워커가 중복 집지 않게 하는 데 좋다. 하지만 job row는 달라도 같은 외부 자원이나 같은 고객 shard를 건드리면 안 되는 경우가 있다.

예를 들어 고객별 데이터 동기화 job이 여러 개 쌓여 있고, 같은 `customer_id`에 대해서는 하나씩만 실행해야 한다고 하자.

이때 job row lock만으로는 부족하다. 서로 다른 job id가 같은 customer를 가리킬 수 있기 때문이다.

한 가지 방법은 job을 집은 뒤 customer 단위 advisory try lock을 잡는 것이다.

```sql
BEGIN;

WITH picked AS (
  SELECT id, customer_id
  FROM customer_sync_jobs
  WHERE status = 'PENDING'
    AND run_after <= now()
  ORDER BY priority DESC, id
  LIMIT 1
  FOR UPDATE SKIP LOCKED
),
locked AS (
  SELECT
    id,
    customer_id,
    pg_try_advisory_xact_lock(2, customer_id::int) AS acquired
  FROM picked
)
UPDATE customer_sync_jobs j
SET status = CASE WHEN locked.acquired THEN 'RUNNING' ELSE 'PENDING' END,
    started_at = CASE WHEN locked.acquired THEN now() ELSE started_at END,
    run_after = CASE
      WHEN locked.acquired THEN run_after
      ELSE now() + interval '10 seconds'
    END
FROM locked
WHERE j.id = locked.id
RETURNING j.id, j.customer_id, locked.acquired;

COMMIT;
```

이 예시는 일부러 단순화했다. 실제로는 `acquired=false`일 때 같은 트랜잭션에서 상태를 원복하거나 run_after를 뒤로 미룰지, 아예 다른 job을 다시 고를지 결정해야 한다.

핵심은 두 단계다.

1. `FOR UPDATE SKIP LOCKED`로 job row 중복 획득을 막는다.
2. advisory lock으로 업무 shard 중복 실행을 막는다.

둘은 대체 관계가 아니다.

- row lock은 "이 job row"를 보호한다.
- advisory lock은 "이 job이 건드리는 업무 자원"을 보호한다.

이 차이를 모르면 job queue가 정상인데 외부 API 호출이 중복되거나, 같은 고객 데이터를 두 워커가 서로 덮어쓰는 문제가 생긴다.

---

## 실무 패턴 4: idempotency key와 advisory lock을 함께 쓰기

결제, 포인트 적립, 쿠폰 발급 같은 쓰기 API에서는 idempotency key가 자주 필요하다. 같은 요청이 네트워크 문제로 재시도되어도 결과가 한 번만 반영되어야 하기 때문이다.

기본 테이블은 이렇게 만들 수 있다.

```sql
CREATE TABLE idempotency_keys (
  key text PRIMARY KEY,
  request_hash text NOT NULL,
  status text NOT NULL,
  response_body jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
```

단순한 경우에는 unique key와 `INSERT ... ON CONFLICT`로 충분하다.

```sql
INSERT INTO idempotency_keys(key, request_hash, status)
VALUES (:key, :request_hash, 'PROCESSING')
ON CONFLICT (key) DO NOTHING;
```

하지만 같은 idempotency key에 대해 한 요청은 처리 중이고 다른 요청은 결과를 기다리거나 읽어야 한다면 race가 복잡해진다. 이때 advisory lock을 key 단위로 잡아 처리 흐름을 단순화할 수 있다.

```sql
BEGIN;

SELECT pg_advisory_xact_lock(
  5,
  hashtext(:idempotency_key)
);

-- 1. 기존 key 조회
-- 2. request_hash 일치 여부 확인
-- 3. COMPLETED면 저장된 응답 반환
-- 4. PROCESSING이면 정책에 따라 대기/409/재조회
-- 5. 없으면 PROCESSING row 생성 후 실제 mutation 수행

COMMIT;
```

여기서도 advisory lock은 보조 장치다.

반드시 남아야 하는 방어선은 아래다.

- `idempotency_keys.key` primary key
- request hash 비교
- 처리 상태 상태기계
- 외부 결제/발송 시스템의 중복 방지 key
- timeout 후 재처리 정책

advisory lock은 같은 key에 대한 동시 처리 경로를 좁혀 코드 복잡도를 줄인다. 하지만 장애 후 재시작, connection loss, commit 성공 여부 불확실성까지 모두 해결해주지는 않는다.

특히 결제처럼 외부 부작용이 있는 작업에서는 아래 순서를 신중히 설계해야 한다.

1. DB 트랜잭션 안에서 외부 API를 호출하지 않을 것인가?
2. Outbox로 외부 호출을 분리할 것인가?
3. 외부 API 자체의 idempotency key는 무엇인가?
4. DB commit 후 응답 전 프로세스가 죽으면 다음 요청은 어떤 상태를 볼 것인가?
5. `PROCESSING`이 오래 남으면 누가, 언제, 어떤 기준으로 복구할 것인가?

advisory lock은 이 질문들을 없애지 않는다. 다만 같은 key에 대해 동시에 여러 트랜잭션이 상태를 꼬는 일을 줄여준다.

---

## 트레이드오프: Advisory Lock이 좋은 경우와 피해야 하는 경우

Advisory lock은 매력적이다. 별도 테이블 없이도 업무 단위 직렬화가 가능하고, 트랜잭션 lock manager에 통합되어 있으며, deadlock 감지도 PostgreSQL이 해준다. 하지만 모든 동시성 문제의 답은 아니다.

### 좋은 경우

아래 조건이면 advisory lock을 검토할 가치가 높다.

- 잠그려는 대상이 DB row 하나로 자연스럽게 존재하지 않는다.
- 업무 단위 중복 실행을 막는 것이 목적이다.
- lock 수명이 DB 트랜잭션 수명과 거의 같다.
- 같은 PostgreSQL 클러스터를 공유하는 프로세스들 사이에서만 조정하면 된다.
- 최종 무결성은 unique constraint, foreign key, status transition 등으로 별도 보호된다.
- lock 실패를 비즈니스 상태로 다룰 수 있다.
- 운영자가 key namespace와 대기 세션을 추적할 수 있다.

예시는 이렇다.

- 테넌트별 월 정산 생성
- 고객별 포인트 재계산
- 같은 리포트 중복 생성 방지
- 같은 외부 리소스 동기화 직렬화
- 스케줄러의 shard 단위 중복 실행 방지
- idempotency key 단위 요청 처리 단순화

### 피해야 하는 경우

반대로 아래 조건이면 다른 방법이 낫다.

- 이미 row lock이나 unique constraint로 자연스럽게 해결된다.
- lock을 잡아야 하는 모든 코드 경로를 통제할 수 없다.
- 여러 DB 클러스터, 여러 region, 여러 저장소를 가로지르는 진짜 분산락이 필요하다.
- lock을 오래 들고 외부 API, 파일 I/O, 대규모 계산을 수행해야 한다.
- lock key가 너무 많고, 대기와 충돌 패턴을 관측할 계획이 없다.
- session-level lock lifecycle을 connection pool에서 안전하게 보장할 수 없다.
- 정합성 실패 시 금전, 권한, 개인정보 같은 큰 피해가 나는데 constraint 없이 lock만 믿는다.

특히 "Redis lock 대신 PostgreSQL advisory lock을 쓰면 되나요?"라는 질문에는 항상 조건이 붙는다.

PostgreSQL 안의 데이터 변경을 직렬화하는 목적이라면 advisory lock이 더 단순할 수 있다. 반대로 여러 독립 시스템의 장기 작업을 조정하거나, DB 트랜잭션과 무관한 lease 기반 분산락이 필요하다면 Redis, etcd, ZooKeeper, 클라우드 coordinator가 더 적합할 수 있다.

---

## Deadlock: advisory lock도 deadlock에서 자유롭지 않다

Advisory lock은 PostgreSQL lock manager에 올라간다. 따라서 서로 다른 트랜잭션이 lock을 엇갈린 순서로 잡으면 deadlock이 날 수 있다.

예를 들어 보자.

```sql
-- 트랜잭션 A
BEGIN;
SELECT pg_advisory_xact_lock(1, 10);
SELECT pg_advisory_xact_lock(1, 20);

-- 트랜잭션 B
BEGIN;
SELECT pg_advisory_xact_lock(1, 20);
SELECT pg_advisory_xact_lock(1, 10);
```

A는 10을 잡고 20을 기다린다. B는 20을 잡고 10을 기다린다. PostgreSQL은 deadlock을 감지하고 한쪽 트랜잭션을 중단시킨다.

해결 원칙은 row lock과 같다.

### 1) 여러 lock을 잡아야 하면 항상 정렬된 순서로 잡는다

```sql
-- 애플리케이션에서 customer_id 목록을 정렬한 뒤 순서대로 lock
SELECT pg_advisory_xact_lock(2, :customer_id_1);
SELECT pg_advisory_xact_lock(2, :customer_id_2);
SELECT pg_advisory_xact_lock(2, :customer_id_3);
```

항상 작은 key부터 잡는 규칙을 두면 교착 가능성이 크게 줄어든다.

### 2) row lock과 advisory lock의 순서도 표준화한다

더 흔한 문제는 advisory lock과 row lock이 섞일 때다.

```text
코드 경로 A: advisory lock -> row lock
코드 경로 B: row lock -> advisory lock
```

이 조합은 deadlock을 만들기 쉽다. 팀 표준으로 순서를 정해야 한다. 대개는 다음 중 하나를 고른다.

- 업무 단위 advisory lock을 먼저 잡고, 그 안에서 필요한 row를 좁게 잠근다.
- 이미 row가 자연스러운 단위라면 advisory lock을 쓰지 않고 row lock으로 통일한다.

중요한 것은 "이 함수에서는 편한 순서"가 아니라 서비스 전체의 일관된 순서다.

### 3) deadlock은 재시도 가능한 실패로 분류한다

PostgreSQL deadlock은 없애야 할 버그이기도 하지만, 고동시성 시스템에서는 완전히 0으로 만들기 어렵다. 따라서 애플리케이션은 deadlock 에러를 재시도 가능한 실패로 분류해야 한다.

단, 무조건 재시도는 위험하다.

- 같은 순서 오류가 있으면 재시도해도 다시 deadlock 난다.
- 외부 부작용이 이미 발생했다면 재시도는 중복 실행을 만들 수 있다.
- 재시도 폭주가 lock 대기를 더 키울 수 있다.

따라서 재시도는 idempotency, backoff, 최대 횟수, 관측 로그와 함께 설계해야 한다.

---

## Timeout과 대기 정책: 얼마나 기다릴지 정하지 않은 lock은 장애가 된다

blocking advisory lock은 lock을 얻을 때까지 기다린다.

```sql
SELECT pg_advisory_xact_lock(3, :vendor_id);
```

이 줄은 간단해 보이지만 운영에서는 위험한 질문을 품고 있다.

> 이 요청은 같은 vendor 작업이 끝날 때까지 얼마나 기다려도 되는가?

답이 없다면 장애 때까지 기다릴 수 있다. 그래서 advisory lock은 timeout 정책과 같이 설계해야 한다.

PostgreSQL에서는 보통 `lock_timeout`과 `statement_timeout`을 함께 본다.

```sql
BEGIN;
SET LOCAL lock_timeout = '500ms';
SET LOCAL statement_timeout = '3s';

SELECT pg_advisory_xact_lock(3, :vendor_id);

-- 짧은 DB 작업

COMMIT;
```

이렇게 하면 advisory lock 획득 대기가 너무 길어질 때 빠르게 실패시킬 수 있다. `statement_timeout`은 전체 statement 시간 상한이고, `lock_timeout`은 lock 획득 대기 상한이다.

주의할 점은 `lock_timeout`이 너무 짧으면 정상적인 짧은 경합도 실패로 바꾼다는 것이다. 반대로 너무 길면 사용자 요청과 connection pool이 줄줄이 묶인다.

워크로드별 기준을 나눠야 한다.

| 워크로드 | 권장 대기 정책 |
| --- | --- |
| 사용자-facing API | 짧은 `lock_timeout`, 실패 시 409/429/재시도 안내 |
| 백그라운드 워커 | 제한된 대기 또는 try lock + backoff |
| 배치 정산 | 더 긴 timeout 가능, 대신 동시성 상한과 모니터링 필수 |
| 운영자 수동 작업 | 명시적 안내와 세션 관찰 전제 |

실무에서 가장 나쁜 조합은 사용자 요청에서 긴 blocking advisory lock을 잡고, 애플리케이션 HTTP timeout은 짧고, DB statement는 계속 살아 있는 구성이다.

이 경우 사용자는 실패를 봤는데 DB는 계속 기다리고, 재시도 요청이 다시 같은 lock에 줄을 선다. 장애가 self-amplifying 구조가 된다.

---

## Connection Pool 주의점: session-level lock은 요청 경계를 넘을 수 있다

connection pool을 쓰는 애플리케이션에서 가장 강조하고 싶은 경고는 이것이다.

> **pool 환경에서 session-level advisory lock은 기본 금지에 가깝게 다뤄라.**

예를 들어 Node.js, Java, Python 서버가 pool에서 connection을 빌린다. 요청 처리 중 아래를 실행한다.

```sql
SELECT pg_advisory_lock(9, 100);
```

그 다음 애플리케이션 예외가 발생했고, unlock이 실행되지 않았다. connection은 pool로 반환된다. DB 세션은 살아 있다. lock도 살아 있다.

다음 요청이 같은 connection을 빌리면 그 요청은 의도치 않게 이미 어떤 lock을 들고 있는 세션에서 실행될 수 있다. 이 상태는 코드 리뷰만으로 잘 보이지 않는다.

반면 transaction-level lock은 훨씬 안전하다.

```sql
BEGIN;
SELECT pg_advisory_xact_lock(9, 100);
-- 작업
ROLLBACK;
```

rollback만 제대로 보장하면 lock은 해제된다. 대부분의 pool middleware는 connection 반환 전 트랜잭션 종료를 강제하거나, 적어도 열린 트랜잭션을 감지할 수 있다.

물론 transaction-level lock도 무조건 안전한 것은 아니다.

- 트랜잭션이 오래 열려 있으면 lock도 오래 유지된다.
- `idle in transaction` 상태로 방치되면 다른 작업이 계속 대기한다.
- pool이 transaction pooling 모드일 때 세션 상태 의존 로직은 더 조심해야 한다.

그래도 일반적인 요청/워커 경계에서는 `pg_advisory_xact_lock`이 압도적으로 다루기 쉽다.

---

## 관측: advisory lock은 보이지 않으면 반드시 남용된다

Advisory lock은 데이터 모델에 명시적으로 드러나지 않는다. 테이블 스키마를 봐도 "이 업무는 advisory lock key 4를 잡는다"는 사실이 보이지 않는다. 그래서 관측을 붙이지 않으면 남용되기 쉽다.

현재 advisory lock을 확인하려면 `pg_locks`를 본다.

```sql
SELECT
  l.pid,
  a.usename,
  a.application_name,
  a.state,
  a.wait_event_type,
  a.wait_event,
  l.locktype,
  l.mode,
  l.granted,
  l.classid,
  l.objid,
  l.objsubid,
  now() - a.query_start AS query_age,
  left(a.query, 200) AS query_sample
FROM pg_locks l
JOIN pg_stat_activity a ON a.pid = l.pid
WHERE l.locktype = 'advisory'
ORDER BY l.granted, query_age DESC;
```

여기서 `classid`, `objid`가 advisory lock key를 해석하는 단서가 된다. 2-argument advisory lock을 쓰면 이 값들을 namespace와 key로 매핑해 운영자가 이해할 수 있게 만들어야 한다.

대기 중인 세션을 보고 싶다면 아래처럼 볼 수 있다.

```sql
SELECT
  blocked.pid AS blocked_pid,
  blocked_activity.application_name AS blocked_app,
  now() - blocked_activity.query_start AS blocked_age,
  blocking.pid AS blocking_pid,
  blocking_activity.application_name AS blocking_app,
  now() - blocking_activity.query_start AS blocking_age,
  left(blocked_activity.query, 200) AS blocked_query,
  left(blocking_activity.query, 200) AS blocking_query
FROM pg_locks blocked
JOIN pg_stat_activity blocked_activity
  ON blocked_activity.pid = blocked.pid
JOIN pg_locks blocking
  ON blocking.locktype = blocked.locktype
 AND blocking.database IS NOT DISTINCT FROM blocked.database
 AND blocking.classid IS NOT DISTINCT FROM blocked.classid
 AND blocking.objid IS NOT DISTINCT FROM blocked.objid
 AND blocking.objsubid IS NOT DISTINCT FROM blocked.objsubid
 AND blocking.pid <> blocked.pid
JOIN pg_stat_activity blocking_activity
  ON blocking_activity.pid = blocking.pid
WHERE blocked.locktype = 'advisory'
  AND NOT blocked.granted
  AND blocking.granted;
```

운영 대시보드에는 최소한 아래를 넣는 편이 좋다.

- advisory lock 대기 세션 수
- namespace별 lock 획득 실패율
- lock 대기 시간 p95/p99
- lock timeout 발생 횟수
- deadlock 발생 횟수
- `idle in transaction` 상태에서 advisory lock을 들고 있는 세션
- 오래 유지되는 session-level advisory lock

애플리케이션 로그에도 lock key를 남겨야 한다.

```text
lock_namespace=tenant_monthly_billing
lock_key=tenant:42:month:2026-06
lock_mode=xact
lock_acquired=true
lock_wait_ms=37
```

DB에서는 숫자만 보이더라도 애플리케이션 로그에서 업무 의미를 복원할 수 있어야 한다.

---

## 흔한 실수 1: unique constraint 대신 advisory lock을 쓴다

가장 위험한 실수는 advisory lock으로 데이터 무결성을 대신하려는 것이다.

예를 들어 사용자 이메일은 유일해야 한다.

```sql
CREATE UNIQUE INDEX uk_users_email ON users(email);
```

이걸 빼고 아래처럼 처리하면 안 된다.

```sql
BEGIN;
SELECT pg_advisory_xact_lock(hashtext(:email));

SELECT count(*)
FROM users
WHERE email = :email;

INSERT INTO users(email)
VALUES (:email);

COMMIT;
```

이 코드는 모든 가입 경로가 같은 advisory lock을 반드시 지킨다는 가정에 의존한다. 배치 import, 관리자 도구, 긴급 SQL, 다른 서비스가 이 규칙을 놓치면 중복 row가 생긴다.

정답은 unique constraint가 기본이고, advisory lock은 필요하면 보조로 붙이는 것이다.

```sql
CREATE UNIQUE INDEX uk_users_email ON users(email);
```

그리고 가입 흐름에 여러 외부 검증이나 비싼 계산이 있어 같은 이메일 요청을 조기에 직렬화하고 싶다면 advisory lock을 추가로 검토한다. 최종 방어선은 여전히 unique constraint다.

---

## 흔한 실수 2: lock 안에서 너무 많은 일을 한다

Advisory lock을 잡는 순간부터 같은 key의 작업은 직렬화된다. 따라서 lock 안에 들어가는 코드는 최소화해야 한다.

나쁜 예시는 이렇다.

```text
lock 획득
외부 API 호출
대용량 파일 다운로드
JSON 변환
DB update
메일 발송
commit
```

이 구조는 lock을 오래 들고 있을 뿐 아니라 실패 복구도 어렵다. 외부 API가 느려지면 같은 key의 모든 요청이 막힌다. 메일 발송 후 DB commit이 실패하면 부작용과 상태가 어긋난다.

더 나은 구조는 lock 안에 "상태 전이와 짧은 DB 쓰기"만 넣는 것이다.

```text
lock 획득
작업 상태를 RUNNING으로 전이
필요한 row를 좁게 갱신
commit

외부 작업 수행

완료 상태 저장은 별도 idempotent update 또는 outbox consumer에서 처리
```

물론 모든 작업을 이렇게 분리할 수 있는 것은 아니다. 그래도 기준은 분명하다.

> **advisory lock 안에는 공유 상태를 결정하는 최소 구간만 넣어라.**

긴 계산, 네트워크, 파일 I/O, 사용자 입력 대기는 lock 밖으로 빼야 한다.

---

## 흔한 실수 3: try lock 실패를 에러로만 기록하고 업무 상태를 남기지 않는다

try lock은 실패할 수 있다. 실패가 정상 흐름이라면 사용자나 워커가 다음에 무엇을 해야 하는지 알아야 한다.

나쁜 방식은 이렇다.

```text
try lock 실패
로그만 남김
요청 실패
끝
```

이러면 운영자는 실제로 작업이 진행 중인지, 누락된 것인지, 재시도해야 하는지 알기 어렵다.

더 나은 방식은 업무 상태를 남기는 것이다.

- 이미 같은 report job이 `RUNNING`이면 그 job id를 반환한다.
- 같은 customer sync가 진행 중이면 다음 `run_after`를 갱신한다.
- 같은 idempotency key가 `PROCESSING`이면 클라이언트에 재조회 endpoint를 안내한다.
- 같은 scheduler shard가 잠겨 있으면 이번 tick은 skip하고 다음 tick에서 다시 시도한다.

즉 try lock 실패는 "DB 에러"가 아니라 "동시 실행을 허용하지 않는 업무 상태"로 모델링해야 한다.

---

## 흔한 실수 4: lock key 충돌을 전혀 고려하지 않는다

해시 기반 key는 충돌 가능성이 있다. 대부분의 업무에서는 충분히 낮은 확률일 수 있지만, 충돌이 발생하면 서로 무관한 작업이 같은 lock을 공유한다.

충돌의 결과는 대개 정합성 오류보다 처리량 저하에 가깝다. 하지만 업무에 따라 의미가 커질 수 있다.

- 서로 다른 고객 작업이 불필요하게 직렬화된다.
- 특정 shard에서 원인 불명의 대기가 늘어난다.
- 리포트 생성이 간헐적으로 "이미 실행 중"으로 오판된다.

이를 줄이려면 다음 기준을 둔다.

- 가능하면 자연수 id를 그대로 쓴다.
- 문자열 key는 namespace를 분리한다.
- 충돌 영향이 큰 업무는 64-bit key를 검토한다.
- hash 알고리즘과 변환 규칙을 문서화한다.
- 로그에는 원본 business key를 함께 남긴다.

충돌 확률보다 더 큰 문제는 재현 불가능성이다. 어떤 key가 어떤 업무 자원인지 추적할 수 없으면 장애 분석이 길어진다.

---

## 구현 예시: 애플리케이션에서 transaction-level advisory lock을 감싸는 방식

아래는 의사 코드에 가깝지만, 구조는 언어와 프레임워크에 상관없이 비슷하다.

```text
function runWithTenantBillingLock(tenantId, month, fn):
    lockNamespace = 1
    businessKey = "tenant:" + tenantId + ":month:" + month
    lockKey = stableHash32(businessKey)

    begin transaction
    set local lock_timeout = '750ms'
    set local statement_timeout = '5s'

    acquired = select pg_try_advisory_xact_lock(lockNamespace, lockKey)
    if not acquired:
        rollback
        return AlreadyRunning(businessKey)

    log lock_acquired(namespace, businessKey, wait_ms)

    result = fn()

    commit
    return result
```

여기서 중요한 설계 포인트는 다음과 같다.

- lock mode를 xact로 고정한다.
- lock namespace를 상수로 관리한다.
- 원본 business key를 로그에 남긴다.
- `try lock` 실패를 업무 결과로 반환한다.
- timeout을 `SET LOCAL`로 트랜잭션에만 적용한다.
- lock 안에서 실행할 함수 `fn`은 짧은 DB 상태 변경에 가깝게 유지한다.

blocking lock을 써야 한다면 wait time을 반드시 측정한다.

```text
begin transaction
set local lock_timeout = '2s'

start = monotonic_now()
select pg_advisory_xact_lock(namespace, lockKey)
wait_ms = monotonic_now() - start

log lock_wait_ms=wait_ms
```

대기 시간이 지표로 남지 않는 lock은 시간이 지나면 반드시 "가끔 느림"이라는 흐릿한 장애로 돌아온다.

---

## Row Lock, Lock Table, Redis Lock과 비교하기

Advisory lock을 선택하기 전에 대안을 비교해야 한다.

| 방법 | 장점 | 단점 | 적합한 상황 |
| --- | --- | --- | --- |
| Row lock | DB가 자연스럽게 충돌 감지, 무결성과 연결 쉬움 | row가 없으면 잠그기 애매함 | 이미 존재하는 엔티티 수정 |
| Unique constraint | 최종 무결성 최강, 모든 코드 경로에 적용 | 업무 흐름 전체 직렬화는 아님 | 중복 생성 방지 |
| Lock table | 업무 의미가 데이터로 남음, TTL/소유자 기록 가능 | 테이블 청소, 경합, 구현 복잡도 | lock 상태를 감사/관리해야 할 때 |
| PostgreSQL advisory lock | 별도 테이블 없이 빠름, 트랜잭션과 결합 쉬움 | key 의미가 숨겨짐, 협력적 사용 필요 | DB 중심 업무 단위 중복 실행 방지 |
| Redis lock | DB 밖 작업 조정 가능, TTL/lease 설계 가능 | 네트워크와 lease 정확성, split-brain 고려 필요 | 여러 시스템/긴 작업/DB 외부 리소스 조정 |

선택 기준은 "무엇이 더 멋진가"가 아니라 "잠금 대상의 진실이 어디에 있는가"다.

- 데이터 무결성의 진실이 PostgreSQL 테이블에 있다면 constraint와 row lock을 우선한다.
- 업무 실행 중복만 줄이면 되고 트랜잭션과 붙어 있다면 advisory lock이 단순하다.
- lock 상태 자체를 사람이 보고 조작해야 한다면 lock table이 나을 수 있다.
- 여러 저장소와 서비스를 가로지르는 lease가 필요하면 PostgreSQL advisory lock만으로는 부족하다.

---

## 체크리스트: Advisory Lock 도입 전에 확인할 것

실무 도입 전에는 아래를 체크하자.

- [ ] 이 문제는 unique constraint나 row lock으로 더 자연스럽게 해결되지 않는가?
- [ ] advisory lock은 최종 무결성 방어선이 아니라 보조 직렬화 장치인가?
- [ ] session-level이 아니라 transaction-level lock을 기본으로 쓰는가?
- [ ] lock namespace와 key 매핑 규칙이 문서화되어 있는가?
- [ ] 원본 business key를 애플리케이션 로그에 남기는가?
- [ ] 여러 lock을 잡을 때 정렬 순서가 정해져 있는가?
- [ ] row lock과 advisory lock을 함께 잡는 순서가 표준화되어 있는가?
- [ ] `lock_timeout`, `statement_timeout` 또는 try lock 실패 정책이 있는가?
- [ ] try lock 실패를 업무 상태로 다루는가?
- [ ] connection pool에서 session-level lock이 새어나갈 가능성이 없는가?
- [ ] lock 안에서 외부 API, 파일 I/O, 긴 계산을 하지 않는가?
- [ ] deadlock과 lock timeout을 재시도 가능한 오류로 분류하되, idempotency와 backoff를 갖췄는가?
- [ ] `pg_locks`, `pg_stat_activity` 기반 관측 쿼리와 대시보드가 있는가?
- [ ] 오래 유지되는 advisory lock과 `idle in transaction` 세션에 대한 알림이 있는가?

---

## 한줄 정리

PostgreSQL Advisory Lock은 DB가 알지 못하는 업무 단위의 중복 실행을 트랜잭션 안에서 직렬화하는 강력한 도구지만, constraint와 idempotency를 대체해서는 안 되며, key 설계와 timeout, 관측, connection pool 규칙까지 함께 갖춰야 운영에서 안전하다.
