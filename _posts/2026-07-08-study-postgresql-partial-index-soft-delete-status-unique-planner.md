---
layout: post
title: "PostgreSQL Partial Index 실전: Soft Delete, Status Predicate, Unique Constraint, Planner 조건 매칭으로 작은 인덱스를 크게 쓰는 법"
date: 2026-07-08 11:50:00 +0900
categories: [sql]
tags: [study, sql, postgresql, partial-index, soft-delete, unique-index, predicate, planner, indexing, performance, operations]
permalink: /sql/2026/07/08/study-postgresql-partial-index-soft-delete-status-unique-planner.html
---

## 배경: 모든 row를 인덱싱하는 것이 항상 좋은 설계는 아니다

PostgreSQL에서 인덱스 튜닝을 시작하면 보통 첫 번째 질문은 "어떤 컬럼 조합으로 B-tree 인덱스를 만들 것인가"가 된다.

```sql
CREATE INDEX idx_orders_tenant_status_created
ON orders (tenant_id, status, created_at DESC);
```

이 방식은 많은 상황에서 정답에 가깝다. 조건절의 선행 컬럼, 정렬 방향, 선택도, covering 여부를 맞추면 검색 API와 목록 화면의 응답 시간을 크게 줄일 수 있다. 하지만 운영 서비스가 커지면 조금 다른 문제가 생긴다.

- 테이블에는 1억 row가 있지만 실제 API가 자주 보는 row는 최근 3개월의 활성 row뿐이다.
- `deleted_at IS NULL` 조건이 모든 조회에 붙지만, 삭제된 row도 같은 인덱스 안에 계속 남아 있다.
- 주문 테이블의 대부분은 `COMPLETED`인데 운영 화면은 `PENDING`, `FAILED`만 자주 본다.
- 유저별 "활성 구독은 하나만" 보장하고 싶지만 과거 구독 이력은 여러 개 보관해야 한다.
- 멀티테넌트 SaaS에서 특정 tenant의 active row만 빠르게 찾고 싶다.
- 인덱스가 너무 커져서 cache hit ratio가 떨어지고, 쓰기 비용과 vacuum 부담이 커진다.
- 복합 인덱스를 계속 추가했더니 읽기보다 쓰기 경로가 더 먼저 병목이 된다.

이때 단순히 컬럼을 하나 더 붙이는 방식은 한계가 있다. 문제의 핵심은 "어떤 순서로 정렬할 것인가"가 아니라 **인덱스에 애초에 어떤 row를 넣을 것인가**이기 때문이다.

PostgreSQL의 Partial Index는 이 지점에서 강력하다. Partial Index는 테이블 전체가 아니라 특정 조건을 만족하는 row만 인덱싱한다.

```sql
CREATE INDEX idx_orders_active_tenant_created
ON orders (tenant_id, created_at DESC)
WHERE deleted_at IS NULL;
```

이 인덱스에는 `deleted_at IS NULL`인 row만 들어간다. 삭제된 row는 테이블에는 남아 있지만 인덱스에는 들어가지 않는다. 따라서 active row 조회는 훨씬 작은 인덱스를 타고, 삭제된 row 때문에 cache와 쓰기 비용을 낭비하지 않는다.

Partial Index를 처음 보면 "조건이 붙은 인덱스" 정도로 간단하게 느껴진다. 하지만 운영에서는 생각보다 섬세하다. Partial Index가 실제로 선택되려면 쿼리의 `WHERE` 조건이 인덱스 predicate를 논리적으로 포함해야 한다. prepared statement, ORM query builder, nullable column, enum 상태값, timezone 조건, parameterized predicate가 섞이면 "분명히 같은 조건 같은데 인덱스를 안 타는" 일이 생긴다.

또 Partial Index는 성능 도구이면서 무결성 도구이기도 하다.

```sql
CREATE UNIQUE INDEX uq_subscriptions_one_active
ON subscriptions (tenant_id, user_id)
WHERE canceled_at IS NULL;
```

이 제약은 "유저별 활성 구독은 하나만 허용하되, 취소된 과거 구독은 여러 개 보관한다"는 업무 규칙을 DB 레벨에서 표현한다. 일반 unique constraint로는 과거 이력까지 막아버리고, 애플리케이션 검증만으로는 동시성 경합에서 뚫릴 수 있다.

이번 글은 Partial Index의 문법 설명이 아니다. 중급 이상 개발자가 운영 PostgreSQL에서 Partial Index를 도입할 때 실제로 판단해야 하는 기준을 정리한다.

이번 글에서 답하려는 질문은 아래와 같다.

1. Partial Index는 composite index, expression index, covering index와 무엇이 다른가?
2. `WHERE deleted_at IS NULL`, `status IN (...)`, `processed_at IS NULL` 같은 predicate는 언제 효과적인가?
3. PostgreSQL planner는 어떤 경우에 partial index를 선택하고, 어떤 경우에는 선택하지 못하는가?
4. Partial Unique Index로 soft delete, active-only uniqueness, idempotency key를 어떻게 안전하게 보장할 수 있는가?
5. prepared statement와 ORM이 partial index 선택을 방해하는 대표 패턴은 무엇인가?
6. 작은 인덱스가 주는 이득과 predicate drift, 운영 복잡도라는 비용을 어떻게 비교할 것인가?
7. 도입 전후에 어떤 쿼리, 통계, 체크리스트로 검증해야 하는가?

핵심 결론부터 말하면 이렇다.

1. Partial Index는 "더 좋은 컬럼 순서"가 아니라 **인덱싱 대상 row 집합을 줄이는 설계**다.
2. predicate는 자주 조회되고, 충분히 선택적이며, 업무적으로 안정적인 조건이어야 한다.
3. 쿼리가 predicate를 명확히 포함하지 않으면 PostgreSQL은 partial index를 쓰지 못한다.
4. soft delete와 active-only uniqueness는 Partial Unique Index가 애플리케이션 검증보다 훨씬 안전하다.
5. prepared statement, generic plan, ORM의 조건 조립 방식은 partial index와 충돌할 수 있다.
6. Partial Index는 읽기 성능뿐 아니라 index bloat, WAL, vacuum, cache 효율까지 줄일 수 있지만, predicate가 늘어나면 운영자가 이해해야 할 인덱스 계약도 늘어난다.
7. 좋은 Partial Index는 "특정 쿼리를 빠르게 하는 장치"가 아니라 **데이터 생명주기에서 뜨거운 row와 차가운 row를 분리하는 계약**이다.

---

## 핵심 개념: Partial Index는 테이블 전체가 아니라 predicate를 만족하는 row만 가진다

일반 B-tree 인덱스는 테이블의 모든 row에 대해 인덱스 엔트리를 만든다. 컬럼 값이 `NULL`이어도 인덱싱된다.

```sql
CREATE INDEX idx_users_email
ON users (email);
```

이 인덱스는 `users` 테이블의 모든 row를 대상으로 한다. `email`이 없는 row, 탈퇴한 row, 비활성 row도 인덱스 구조 안에 들어간다.

Partial Index는 여기에 predicate를 붙인다.

```sql
CREATE INDEX idx_users_active_email
ON users (email)
WHERE deleted_at IS NULL;
```

이제 인덱스에는 `deleted_at IS NULL`인 row만 들어간다. 삭제된 row는 heap table에는 남지만 인덱스에서는 빠진다.

이 차이는 단순한 크기 차이가 아니다. 인덱스가 작아지면 여러 운영 비용이 함께 줄어든다.

- B-tree 높이가 낮아질 수 있다.
- shared buffer에 더 잘 머문다.
- index scan이 읽어야 할 page가 줄어든다.
- insert/update/delete 시 유지해야 할 index entry가 줄어든다.
- WAL 발생량이 줄 수 있다.
- autovacuum과 index cleanup 부담이 줄 수 있다.
- hot path 쿼리의 plan 안정성이 좋아질 수 있다.

하지만 Partial Index는 항상 좋은 것이 아니다. predicate 밖의 row를 찾는 쿼리에는 사용할 수 없다.

```sql
-- partial index 사용 가능성이 높다
SELECT id, email
FROM users
WHERE deleted_at IS NULL
  AND email = 'dev@example.com';

-- partial index를 사용할 수 없다
SELECT id, email
FROM users
WHERE email = 'dev@example.com';

-- partial index를 사용할 수 없다
SELECT id, email
FROM users
WHERE deleted_at IS NOT NULL
  AND email = 'dev@example.com';
```

첫 번째 쿼리는 `deleted_at IS NULL` 조건을 명시하므로 partial index의 row 집합 안에서 찾을 수 있다. 두 번째 쿼리는 삭제된 row까지 포함해야 할 수 있으므로 partial index만으로는 정답을 보장할 수 없다. 세 번째 쿼리는 아예 predicate 반대편을 찾는다.

이 점 때문에 Partial Index는 설계 단계에서 두 가지 질문을 먼저 해야 한다.

1. 이 조건은 대부분의 hot path 쿼리에 항상 들어가는가?
2. 이 조건 밖의 row를 조회하는 경로는 느려도 되는가, 아니면 별도 인덱스가 필요한가?

soft delete 테이블에서 일반 사용자 API는 거의 항상 `deleted_at IS NULL`만 본다. 반면 관리자 감사 화면은 삭제된 row도 조회할 수 있다. 이 경우 active row용 partial index를 만들고, 감사 화면은 느린 조회를 허용하거나 별도 admin 전용 인덱스를 두는 식으로 경로를 분리할 수 있다.

---

## Composite Index와 Partial Index는 해결하는 문제가 다르다

Partial Index를 복합 인덱스의 대체재로 오해하면 설계가 흔들린다. 둘은 서로 다른 축의 선택이다.

복합 인덱스는 "인덱스 안에서 어떤 순서로 찾을 것인가"를 다룬다.

```sql
CREATE INDEX idx_orders_tenant_status_created
ON orders (tenant_id, status, created_at DESC);
```

Partial Index는 "어떤 row만 인덱스에 넣을 것인가"를 다룬다.

```sql
CREATE INDEX idx_orders_pending_tenant_created
ON orders (tenant_id, created_at DESC)
WHERE status = 'PENDING';
```

둘은 함께 쓸 수 있다.

```sql
CREATE INDEX idx_orders_active_pending_tenant_created
ON orders (tenant_id, created_at DESC)
WHERE deleted_at IS NULL
  AND status = 'PENDING';
```

이 인덱스는 active이면서 pending인 주문만 대상으로, tenant별 최신순 조회에 최적화되어 있다.

여기서 중요한 판단은 `status`를 인덱스 key에 넣을지 predicate에 넣을지다.

### status를 key에 넣는 경우

```sql
CREATE INDEX idx_orders_tenant_status_created
ON orders (tenant_id, status, created_at DESC);
```

이 방식은 여러 status를 골고루 조회할 때 좋다.

```sql
SELECT *
FROM orders
WHERE tenant_id = $1
  AND status = $2
ORDER BY created_at DESC
LIMIT 50;
```

`status`가 동적으로 바뀌고, `PENDING`, `PAID`, `FAILED`, `CANCELED`를 모두 비슷하게 조회한다면 key 컬럼으로 두는 편이 자연스럽다.

### status를 predicate에 넣는 경우

```sql
CREATE INDEX idx_orders_pending_tenant_created
ON orders (tenant_id, created_at DESC)
WHERE status = 'PENDING';
```

이 방식은 특정 status만 압도적으로 뜨거울 때 좋다.

```sql
SELECT *
FROM orders
WHERE tenant_id = $1
  AND status = 'PENDING'
ORDER BY created_at DESC
LIMIT 50;
```

예를 들어 전체 주문의 98%는 `COMPLETED`이고, 운영자가 반복해서 보는 것은 `PENDING`과 `FAILED`라면 전체 status를 모두 담은 큰 인덱스보다 hot status용 partial index가 훨씬 작고 빠를 수 있다.

### 둘을 혼합하는 경우

가끔은 predicate와 key를 함께 쓴다.

```sql
CREATE INDEX idx_orders_open_tenant_status_created
ON orders (tenant_id, status, created_at DESC)
WHERE status IN ('PENDING', 'FAILED', 'RETRYING');
```

이 인덱스는 "열린 상태"만 담되, 그 안에서 status별 조회도 지원한다. 운영 화면이 open 상태 집합만 다루고 완료된 주문은 거의 보지 않는다면 유효하다.

다만 이 방식은 predicate와 key에 같은 컬럼이 동시에 등장하므로 팀이 의도를 명확히 이해해야 한다. `status IN (...)` predicate는 인덱스 row 집합을 제한하고, key의 `status`는 그 제한된 집합 안에서 탐색과 정렬을 돕는다.

---

## 실무 예시 1: Soft Delete 테이블의 active row 조회

가장 흔한 Partial Index 사용처는 soft delete다.

```sql
CREATE TABLE customers (
  id BIGSERIAL PRIMARY KEY,
  tenant_id BIGINT NOT NULL,
  email TEXT NOT NULL,
  name TEXT NOT NULL,
  deleted_at TIMESTAMPTZ NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

애플리케이션은 고객을 물리 삭제하지 않고 `deleted_at`을 채운다.

```sql
UPDATE customers
SET deleted_at = now(),
    updated_at = now()
WHERE id = $1
  AND tenant_id = $2;
```

일반 사용자 화면은 active 고객만 본다.

```sql
SELECT id, email, name, created_at
FROM customers
WHERE tenant_id = $1
  AND deleted_at IS NULL
ORDER BY created_at DESC
LIMIT 50;
```

이 쿼리에 전체 인덱스를 만들면 삭제된 고객도 함께 들어간다.

```sql
CREATE INDEX idx_customers_tenant_created
ON customers (tenant_id, created_at DESC);
```

삭제 비율이 낮다면 괜찮다. 하지만 오래 운영된 SaaS에서 고객, 프로젝트, 문서, 알림 같은 테이블은 삭제되거나 보관 상태가 된 row가 상당히 많아질 수 있다. 특히 free trial, 임시 데이터, import 실패 데이터가 쌓이면 active row보다 inactive row가 더 많아질 수 있다.

이때 active row만 인덱싱한다.

```sql
CREATE INDEX idx_customers_active_tenant_created
ON customers (tenant_id, created_at DESC)
WHERE deleted_at IS NULL;
```

이 인덱스는 사용자 화면에 맞다.

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, email, name, created_at
FROM customers
WHERE tenant_id = 42
  AND deleted_at IS NULL
ORDER BY created_at DESC
LIMIT 50;
```

기대하는 계획은 대략 이런 형태다.

```text
Limit
  ->  Index Scan using idx_customers_active_tenant_created on customers
        Index Cond: (tenant_id = 42)
```

여기서 `deleted_at IS NULL`은 `Index Cond`에 반드시 보이지 않을 수 있다. 이미 partial index predicate로 보장되므로 plan에는 `Filter` 또는 별도 조건으로 표시되지 않을 수 있다. 중요한 것은 사용한 인덱스 이름과 buffer 접근량이다.

### soft delete에서 partial index가 특히 좋은 이유

soft delete는 데이터 생명주기가 명확하다.

- active row: 온라인 API가 자주 읽고 쓴다.
- deleted row: 감사, 복구, 법적 보관, 운영 조사에서 가끔 읽는다.

이 두 집합은 접근 빈도와 요구 성능이 다르다. 그런데 일반 인덱스는 둘을 같은 구조에 섞는다. Partial Index는 hot path만 분리한다.

또 soft delete는 update 비용과도 연결된다. row가 active에서 deleted로 바뀌면 해당 row는 partial index에서 제거된다. 이후 삭제된 row의 일부 컬럼이 보정되더라도 active partial index는 더 이상 업데이트되지 않는다. 쓰기가 많은 테이블에서 이 차이는 작지 않다.

### 주의: 모든 쿼리에 active 조건이 실제로 들어가야 한다

아래 ORM 코드는 위험할 수 있다.

```sql
SELECT id, email, name
FROM customers
WHERE tenant_id = $1
ORDER BY created_at DESC
LIMIT 50;
```

애플리케이션 레이어에서 나중에 삭제 row를 걸러낸다면 DB는 partial index를 사용할 수 없다. 더 나쁘게는 삭제된 row를 먼저 많이 읽고 애플리케이션에서 버리는 구조가 된다.

Partial Index는 "인덱스가 알아서 삭제 row를 제외해주겠지"가 아니다. 쿼리가 predicate를 포함해야 한다.

따라서 soft delete를 쓰는 팀은 repository 또는 query builder 레벨에서 `deleted_at IS NULL` 조건을 기본 scope로 강제해야 한다. 단, 관리자 화면처럼 삭제 row를 의도적으로 보는 경로는 별도 메서드로 분리하는 편이 좋다.

---

## 실무 예시 2: Active-only Unique 제약

Partial Index의 진짜 강점은 unique와 만날 때 더 잘 드러난다.

요구사항을 보자.

> 한 tenant 안에서 active 사용자의 email은 유일해야 한다. 하지만 탈퇴한 사용자의 email은 재가입에 쓸 수 있어야 하고, 탈퇴 이력은 보관해야 한다.

일반 unique constraint는 요구사항을 그대로 표현하지 못한다.

```sql
ALTER TABLE users
ADD CONSTRAINT uq_users_tenant_email
UNIQUE (tenant_id, email);
```

이 제약은 삭제된 사용자까지 포함해 email 중복을 막는다. 탈퇴 후 재가입이 불가능해진다.

애플리케이션에서만 검사하면 동시성에 취약하다.

```sql
-- 요청 A
SELECT count(*)
FROM users
WHERE tenant_id = 42
  AND email = 'dev@example.com'
  AND deleted_at IS NULL;

-- 요청 B도 동시에 0을 본다
-- 둘 다 INSERT하면 active email 중복이 생길 수 있다
```

정답에 가까운 것은 Partial Unique Index다.

```sql
CREATE UNIQUE INDEX uq_users_active_tenant_email
ON users (tenant_id, lower(email))
WHERE deleted_at IS NULL;
```

이 제약은 active row에 대해서만 `(tenant_id, lower(email))` 중복을 막는다. 삭제된 row는 여러 개 있어도 된다.

```sql
INSERT INTO users (tenant_id, email, name, deleted_at)
VALUES (42, 'dev@example.com', 'Dev A', NULL);

-- 실패: active email 중복
INSERT INTO users (tenant_id, email, name, deleted_at)
VALUES (42, 'DEV@example.com', 'Dev B', NULL);

-- 성공: 과거 삭제 이력
INSERT INTO users (tenant_id, email, name, deleted_at)
VALUES (42, 'dev@example.com', 'Old Dev', now());
```

이 방식은 애플리케이션 검증보다 안전하다. 두 요청이 동시에 들어와도 PostgreSQL unique index가 충돌을 최종적으로 막는다. 애플리케이션은 unique violation을 잡아서 사용자 친화적인 오류로 바꾸면 된다.

### 구독 도메인: "활성 구독은 하나만" 보장하기

구독 테이블에서도 자주 쓰인다.

```sql
CREATE TABLE subscriptions (
  id BIGSERIAL PRIMARY KEY,
  tenant_id BIGINT NOT NULL,
  user_id BIGINT NOT NULL,
  plan_id BIGINT NOT NULL,
  started_at TIMESTAMPTZ NOT NULL,
  canceled_at TIMESTAMPTZ NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

요구사항은 "사용자당 활성 구독은 하나"다. 과거 구독 이력은 여러 개 있을 수 있다.

```sql
CREATE UNIQUE INDEX uq_subscriptions_one_active_per_user
ON subscriptions (tenant_id, user_id)
WHERE canceled_at IS NULL;
```

이제 동시에 두 결제 콜백이 들어와도 활성 구독 중복은 DB가 막는다.

```sql
INSERT INTO subscriptions (tenant_id, user_id, plan_id, started_at, canceled_at)
VALUES ($1, $2, $3, now(), NULL);
```

실무에서는 여기에 idempotency key도 함께 설계하는 편이 좋다.

```sql
CREATE UNIQUE INDEX uq_payment_events_idempotency_key
ON payment_events (provider, idempotency_key)
WHERE idempotency_key IS NOT NULL;
```

이 인덱스는 idempotency key가 있는 이벤트만 중복을 막는다. provider가 idempotency key를 제공하지 않는 과거 이벤트나 수동 보정 이벤트는 별도 경로로 다룰 수 있다.

### NULL과 unique의 차이를 이해해야 한다

PostgreSQL unique index에서 `NULL`은 서로 같지 않은 값처럼 취급된다. 즉 일반 unique index에서도 nullable 컬럼은 여러 `NULL`을 허용한다.

```sql
CREATE UNIQUE INDEX uq_users_optional_external_id
ON users (tenant_id, external_id);
```

이 경우 `external_id IS NULL`인 row는 여러 개 들어갈 수 있다. 그래서 "NULL이 아닌 값만 유일"이면 partial unique index를 명시하는 편이 의도를 더 잘 드러낸다.

```sql
CREATE UNIQUE INDEX uq_users_external_id_present
ON users (tenant_id, external_id)
WHERE external_id IS NOT NULL;
```

성능만 놓고 보면 일반 unique index와 큰 차이가 없을 수도 있다. 하지만 운영자가 인덱스 목록을 볼 때 "이 제약은 external_id가 있을 때만 의미 있다"는 계약이 명확해진다.

---

## 실무 예시 3: 작업 큐와 미처리 row 인덱스

작업 큐 테이블은 Partial Index와 잘 맞는다.

```sql
CREATE TABLE jobs (
  id BIGSERIAL PRIMARY KEY,
  queue_name TEXT NOT NULL,
  status TEXT NOT NULL,
  run_at TIMESTAMPTZ NOT NULL,
  locked_at TIMESTAMPTZ NULL,
  locked_by TEXT NULL,
  attempts INT NOT NULL DEFAULT 0,
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

워커는 실행 가능한 job을 가져간다.

```sql
SELECT id
FROM jobs
WHERE queue_name = $1
  AND status = 'READY'
  AND run_at <= now()
ORDER BY run_at, id
LIMIT 100
FOR UPDATE SKIP LOCKED;
```

전체 jobs 테이블에는 완료된 job이 훨씬 많다. `DONE`, `FAILED_FINAL`, `CANCELED`가 99%이고 `READY`는 1%라면 전체 인덱스는 낭비가 크다.

```sql
CREATE INDEX idx_jobs_ready_queue_run_at
ON jobs (queue_name, run_at, id)
WHERE status = 'READY';
```

이 인덱스는 워커가 매번 보는 작은 집합만 담는다.

job이 완료되면 status가 바뀐다.

```sql
UPDATE jobs
SET status = 'DONE',
    updated_at = now()
WHERE id = $1;
```

이때 해당 row는 partial index에서 제거된다. 완료된 job이 인덱스에 남아 워커의 탐색 공간을 더럽히지 않는다.

### retry 상태를 어떻게 다룰 것인가

실무 큐는 단순히 `READY`만 있지 않다.

- `READY`: 실행 가능
- `RUNNING`: 워커가 잡음
- `RETRY_WAIT`: 실패 후 대기
- `DONE`: 완료
- `FAILED_FINAL`: 최종 실패

여기서 predicate를 어떻게 잡을지는 워커 쿼리와 상태 전이 모델에 따라 다르다.

방식 1: 실행 가능한 상태만 predicate로 둔다.

```sql
CREATE INDEX idx_jobs_executable_queue_run_at
ON jobs (queue_name, run_at, id)
WHERE status IN ('READY', 'RETRY_WAIT');
```

쿼리는 이렇게 맞춘다.

```sql
SELECT id
FROM jobs
WHERE queue_name = $1
  AND status IN ('READY', 'RETRY_WAIT')
  AND run_at <= now()
ORDER BY run_at, id
LIMIT 100
FOR UPDATE SKIP LOCKED;
```

방식 2: 상태를 key에 넣고 predicate는 terminal 상태 제외로 둔다.

```sql
CREATE INDEX idx_jobs_open_queue_status_run_at
ON jobs (queue_name, status, run_at, id)
WHERE status IN ('READY', 'RETRY_WAIT', 'RUNNING');
```

이 방식은 운영 화면에서 열린 job을 상태별로 보는 데 유리하다. 대신 워커의 hot path만 놓고 보면 첫 번째 방식보다 인덱스가 클 수 있다.

중요한 것은 상태 모델이 바뀔 때 index predicate도 함께 점검해야 한다는 점이다. `PAUSED`, `DEFERRED`, `THROTTLED` 같은 상태가 추가되었는데 partial index predicate와 워커 쿼리를 같이 수정하지 않으면 성능과 동작이 갈라진다.

---

## Planner 조건 매칭: 쿼리가 predicate를 포함한다는 사실을 DB가 알아야 한다

Partial Index에서 가장 자주 만나는 함정은 이것이다.

> 사람이 보기에는 같은 조건인데 PostgreSQL planner는 partial index를 쓸 수 없다고 판단한다.

PostgreSQL은 partial index가 정답을 놓치지 않는다고 증명할 수 있을 때만 해당 인덱스를 고려한다. 쿼리 조건이 index predicate를 논리적으로 함의해야 한다.

간단한 경우는 잘 된다.

```sql
CREATE INDEX idx_invoices_unpaid_tenant_due
ON invoices (tenant_id, due_at)
WHERE paid_at IS NULL;

SELECT id
FROM invoices
WHERE tenant_id = 42
  AND paid_at IS NULL
  AND due_at < now();
```

쿼리에 `paid_at IS NULL`이 그대로 있으므로 planner가 partial index를 사용할 수 있다.

하지만 아래는 다르다.

```sql
SELECT id
FROM invoices
WHERE tenant_id = 42
  AND coalesce(paid_at, 'infinity'::timestamptz) = 'infinity'::timestamptz
  AND due_at < now();
```

사람은 이 조건이 `paid_at IS NULL`과 비슷한 의도라는 것을 알 수 있다. 하지만 planner가 partial index predicate와 안전하게 매칭하지 못할 수 있다. 쿼리는 인덱스를 안 탈 수 있다.

### predicate는 단순하고 직접적인 형태가 좋다

Partial Index predicate는 가능하면 단순해야 한다.

좋은 예:

```sql
WHERE deleted_at IS NULL
WHERE processed_at IS NULL
WHERE status = 'PENDING'
WHERE status IN ('READY', 'RETRY_WAIT')
WHERE archived_at IS NULL AND tenant_id IS NOT NULL
```

주의가 필요한 예:

```sql
WHERE coalesce(deleted_at, 'infinity') = 'infinity'
WHERE lower(status) = 'pending'
WHERE now() - created_at < interval '30 days'
WHERE metadata->>'state' = 'active'
WHERE is_active(status, deleted_at)
```

물론 expression과 function을 절대 쓰지 말라는 뜻은 아니다. 다만 predicate가 복잡할수록 쿼리 조건도 같은 표현을 안정적으로 반복해야 하고, planner가 implication을 증명하기 어려워질 수 있다. 운영 팀이 `\d+`로 인덱스를 봤을 때 즉시 의미를 이해하기도 어렵다.

### prepared statement와 parameter가 만드는 문제

Partial Index는 parameterized query와도 충돌할 수 있다.

```sql
CREATE INDEX idx_orders_pending_tenant_created
ON orders (tenant_id, created_at DESC)
WHERE status = 'PENDING';
```

이 쿼리는 partial index를 쓰기 쉽다.

```sql
SELECT id
FROM orders
WHERE tenant_id = $1
  AND status = 'PENDING'
ORDER BY created_at DESC
LIMIT 50;
```

하지만 ORM이 모든 값을 parameter로 만들면 이렇게 된다.

```sql
SELECT id
FROM orders
WHERE tenant_id = $1
  AND status = $2
ORDER BY created_at DESC
LIMIT 50;
```

실행 시 `$2 = 'PENDING'`이면 사람이 보기에는 같은 쿼리다. 하지만 prepared statement가 generic plan을 쓰는 경우, planner는 `$2`가 항상 `'PENDING'`인지 모른다. `$2`가 `'COMPLETED'`일 수도 있으므로 `WHERE status = 'PENDING'` partial index를 안전하게 사용할 수 없다.

PostgreSQL은 custom plan을 만들 때 실제 parameter 값을 고려할 수 있지만, generic plan으로 전환되면 partial index 선택이 사라질 수 있다. 이 문제는 "개발 환경에서는 인덱스를 타는데 운영에서 갑자기 안 탄다"는 형태로 나타난다. 개발 환경은 데이터가 작고 prepared statement 재사용이 적어서 custom plan이 유지되지만, 운영에서는 plan cache와 parameter 분포가 다르게 작동하기 때문이다.

대응 방법은 몇 가지다.

1. hot path 쿼리는 literal predicate를 유지한다.
2. status별로 repository 메서드를 분리한다.
3. prepared statement generic plan 이슈를 `EXPLAIN (ANALYZE, BUFFERS)`와 `pg_stat_statements`로 확인한다.
4. 특정 경로에서 `plan_cache_mode`를 실험적으로 조정하되, 전역 설정 변경은 신중하게 한다.
5. partial index predicate를 동적 값이 아니라 업무적으로 고정된 조건에만 둔다.

예를 들어 아래처럼 메서드를 분리하는 것이 단순하지만 강력할 수 있다.

```sql
-- findPendingOrders
SELECT id, created_at
FROM orders
WHERE tenant_id = $1
  AND status = 'PENDING'
ORDER BY created_at DESC
LIMIT $2;

-- findOrdersByStatus
SELECT id, created_at
FROM orders
WHERE tenant_id = $1
  AND status = $2
ORDER BY created_at DESC
LIMIT $3;
```

첫 번째는 hot path 최적화를 위한 고정 predicate 쿼리다. 두 번째는 일반 조회다. 둘을 하나의 범용 메서드로 합치면 코드 중복은 줄어들지만 plan 안정성이 떨어질 수 있다.

---

## 실무 예시 4: multi-tenant에서 tenant_id를 predicate에 넣지 말아야 하는 경우

멀티테넌트 테이블에서 거의 모든 쿼리는 `tenant_id = ?` 조건을 가진다.

```sql
SELECT id, title
FROM projects
WHERE tenant_id = $1
  AND deleted_at IS NULL
ORDER BY updated_at DESC
LIMIT 50;
```

그렇다고 아래처럼 tenant별 partial index를 만드는 것은 보통 나쁜 생각이다.

```sql
CREATE INDEX idx_projects_tenant_42_active_updated
ON projects (updated_at DESC)
WHERE tenant_id = 42
  AND deleted_at IS NULL;
```

특정 초대형 tenant 하나만 별도로 최적화해야 하는 예외 상황에서는 쓸 수 있다. 하지만 일반적으로 tenant별 partial index는 운영 복잡도를 크게 키운다.

- tenant가 늘어날 때마다 인덱스가 늘어난다.
- schema migration 시간이 증가한다.
- planner 선택지가 불필요하게 많아진다.
- 작은 tenant 인덱스는 거의 쓰이지 않는다.
- `pg_class`, `pg_index`, autovacuum 관리 대상이 늘어난다.
- 장애 시 어떤 tenant 인덱스가 필요한지 판단하기 어렵다.

대부분의 SaaS에서는 tenant_id를 key의 선두에 둔다.

```sql
CREATE INDEX idx_projects_active_tenant_updated
ON projects (tenant_id, updated_at DESC)
WHERE deleted_at IS NULL;
```

이 설계는 active row만 인덱싱하면서도 모든 tenant를 하나의 구조로 지원한다.

단, 초대형 tenant가 전체 데이터의 대부분을 차지하고 다른 tenant와 접근 패턴이 완전히 다르다면 선택지가 생긴다.

1. 해당 tenant만 별도 partial index를 둔다.
2. 테이블 partitioning으로 tenant 또는 tenant group을 분리한다.
3. 초대형 tenant를 별도 shard나 database로 분리한다.
4. 쿼리 요구사항을 바꿔 검색 인덱스나 집계 테이블로 뺀다.

Partial Index는 이 중 가장 작은 변화지만, 장기적인 데이터 배치 문제를 가리는 임시 처방이 될 수도 있다. tenant skew가 심하면 인덱스 하나보다 partitioning, retention, product-level limit까지 함께 봐야 한다.

---

## 실무 예시 5: 최근 데이터만 인덱싱하고 싶을 때의 함정

운영자가 자주 하는 생각이 있다.

> 최근 30일 데이터만 자주 보니까 최근 30일만 partial index로 만들면 되지 않을까?

예를 들면 이런 인덱스를 상상한다.

```sql
CREATE INDEX idx_events_recent_tenant_created
ON events (tenant_id, created_at DESC)
WHERE created_at >= now() - interval '30 days';
```

이 인덱스는 문제가 있다. PostgreSQL partial index predicate는 immutable한 조건이어야 한다. `now()`처럼 시간에 따라 값이 바뀌는 함수는 predicate에 적합하지 않다. 인덱스가 만들어진 뒤 시간이 지나면 어떤 row가 "최근 30일"인지 계속 바뀌어야 하는데, 인덱스는 자동으로 그런 의미 변화를 재평가하지 않는다.

최근 데이터 최적화에는 다른 접근이 필요하다.

### 방법 1: 명시적 상태 컬럼 사용

업무적으로 hot/cold 상태를 명시한다.

```sql
ALTER TABLE events
ADD COLUMN is_hot BOOLEAN NOT NULL DEFAULT true;

CREATE INDEX idx_events_hot_tenant_created
ON events (tenant_id, created_at DESC)
WHERE is_hot = true;
```

배치가 오래된 row를 cold로 전환한다.

```sql
UPDATE events
SET is_hot = false
WHERE is_hot = true
  AND created_at < now() - interval '30 days';
```

이 방식은 predicate가 안정적이다. 대신 상태 전환 배치가 필요하고, hot/cold 전환 시 인덱스 업데이트 비용이 발생한다.

### 방법 2: 파티셔닝 사용

시간 기준 데이터 생명주기가 강하다면 range partitioning이 더 자연스럽다.

```sql
CREATE TABLE events (
  id BIGINT NOT NULL,
  tenant_id BIGINT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL,
  payload JSONB NOT NULL
) PARTITION BY RANGE (created_at);
```

최근 partition에만 더 촘촘한 인덱스를 두고, 오래된 partition은 조회 패턴에 맞게 적은 인덱스만 둔다. retention, archive, detach/drop까지 같이 해결할 수 있다.

### 방법 3: 일반 인덱스와 쿼리 제한으로 충분한지 확인

아래 인덱스만으로도 최근 조회는 충분히 빠를 수 있다.

```sql
CREATE INDEX idx_events_tenant_created
ON events (tenant_id, created_at DESC);
```

`tenant_id`와 `created_at DESC`가 맞으면 `LIMIT 100` 조회는 최근 데이터부터 짧게 읽고 멈춘다. 굳이 최근 30일 partial index를 만들 필요가 없을 수 있다.

Partial Index는 시간 이동 window를 표현하는 도구가 아니다. 데이터 생명주기가 시간 기준이라면 partitioning, retention, materialized summary, hot flag 중 무엇이 맞는지 먼저 판단해야 한다.

---

## Trade-off: 작은 인덱스는 빠르지만 계약이 하나 더 생긴다

Partial Index의 장점은 분명하다.

- 인덱스 크기가 작다.
- hot path query가 읽는 page가 줄어든다.
- cache 효율이 좋아진다.
- 쓰기 시 유지 비용이 줄어든다.
- partial unique로 업무 제약을 정확히 표현할 수 있다.
- 완료/삭제/보관 row가 온라인 조회 경로를 방해하지 않는다.

하지만 비용도 있다.

### 1) 쿼리와 인덱스 predicate가 강하게 결합된다

일반 인덱스는 조건 일부가 빠져도 어느 정도 쓸 수 있다. 하지만 Partial Index는 predicate가 빠지면 후보에서 제외된다.

```sql
CREATE INDEX idx_tasks_open_assignee_due
ON tasks (assignee_id, due_at)
WHERE closed_at IS NULL;
```

이 인덱스를 기대하는 쿼리는 반드시 `closed_at IS NULL`을 포함해야 한다.

```sql
SELECT id
FROM tasks
WHERE assignee_id = $1
  AND closed_at IS NULL
ORDER BY due_at
LIMIT 20;
```

팀원이 나중에 범용 task 검색을 만들면서 `closed_at` 조건을 optional filter로 빼면 plan이 달라진다. 즉 Partial Index는 코드 컨벤션과 함께 관리해야 한다.

### 2) predicate drift가 생긴다

처음에는 `status = 'PENDING'`만 hot path였다.

```sql
WHERE status = 'PENDING'
```

몇 달 뒤 `RETRYING`과 `ESCALATED`가 추가된다.

```sql
WHERE status IN ('PENDING', 'RETRYING', 'ESCALATED')
```

쿼리는 바뀌었는데 인덱스 predicate는 그대로라면 `RETRYING`과 `ESCALATED` 조회는 인덱스를 못 타거나 다른 plan을 탄다. 반대로 인덱스 predicate만 넓히면 인덱스 크기가 커져 기존 이득이 줄어든다.

상태값 기반 Partial Index는 상태 모델 변경 때마다 반드시 같이 리뷰해야 한다.

### 3) 인덱스 개수가 늘어날 수 있다

`PENDING`, `FAILED`, `RETRYING` 각각에 partial index를 만들고 싶어질 수 있다.

```sql
CREATE INDEX idx_orders_pending_tenant_created
ON orders (tenant_id, created_at DESC)
WHERE status = 'PENDING';

CREATE INDEX idx_orders_failed_tenant_created
ON orders (tenant_id, created_at DESC)
WHERE status = 'FAILED';

CREATE INDEX idx_orders_retrying_tenant_created
ON orders (tenant_id, created_at DESC)
WHERE status = 'RETRYING';
```

정말 각 상태별 쿼리가 모두 뜨겁고 데이터 분포가 다르면 유효할 수 있다. 하지만 대개는 아래처럼 하나로 묶는 편이 낫다.

```sql
CREATE INDEX idx_orders_open_tenant_status_created
ON orders (tenant_id, status, created_at DESC)
WHERE status IN ('PENDING', 'FAILED', 'RETRYING');
```

인덱스가 많아지면 쓰기 비용과 운영 복잡도가 증가한다. partial이라 작더라도 insert/update/delete마다 어떤 인덱스에 들어가고 빠져야 하는지 평가해야 한다.

### 4) 통계와 추정이 여전히 중요하다

Partial Index가 작다고 항상 선택되는 것은 아니다. planner는 table statistics, index statistics, correlation, cost parameter를 바탕으로 plan을 고른다. predicate에 해당하는 row가 너무 많거나, 쿼리 조건이 넓거나, 정렬과 LIMIT 이점이 작으면 sequential scan이나 다른 인덱스를 선택할 수 있다.

도입 후에는 반드시 실제 쿼리로 확인해야 한다.

```sql
EXPLAIN (ANALYZE, BUFFERS, SETTINGS)
SELECT ...
```

`idx_scan` 증가만 볼 것이 아니라 buffer read, execution time, rows estimate, heap fetch, sort 여부를 함께 봐야 한다.

---

## 흔한 실수 1: "작은 테이블이니까 괜찮다"며 predicate를 복잡하게 만든다

작은 테이블에서 Partial Index는 별 이득이 없을 수 있다. 그런데 작은 테이블일수록 설계자가 과감하게 복잡한 predicate를 붙이기도 한다.

```sql
CREATE INDEX idx_notifications_dashboard
ON notifications (user_id, created_at DESC)
WHERE deleted_at IS NULL
  AND read_at IS NULL
  AND type IN ('MENTION', 'APPROVAL', 'COMMENT')
  AND priority >= 3;
```

처음에는 대시보드 쿼리에 딱 맞는다. 하지만 알림 정책이 바뀌면 이 인덱스는 금방 낡는다.

- `FOLLOW_UP` 타입이 추가된다.
- priority 의미가 바뀐다.
- 읽은 알림도 최근 7일은 보여준다.
- 삭제 대신 archive 개념이 생긴다.
- 모바일과 웹 대시보드 조건이 달라진다.

Partial Index predicate는 업무 규칙의 일부가 된다. 자주 바뀌는 product rule을 그대로 predicate에 넣으면 DB schema가 product 실험 속도를 따라가지 못한다.

실무 기준은 이렇다.

- 생명주기 조건은 좋다: `deleted_at IS NULL`, `archived_at IS NULL`, `processed_at IS NULL`
- 상태 집합은 조심한다: `status IN (...)`
- 점수, 우선순위, 시간 window는 더 조심한다.
- 사용자 설정, AB test, 권한 조건은 보통 predicate에 넣지 않는다.

---

## 흔한 실수 2: Partial Unique Index를 만들고 애플리케이션 오류 처리를 안 한다

Partial Unique Index를 만들면 동시성 중복은 DB가 막는다. 하지만 애플리케이션이 unique violation을 정상적인 업무 오류로 다루지 않으면 사용자 경험은 나빠진다.

예를 들어 active email unique를 만들었다.

```sql
CREATE UNIQUE INDEX uq_users_active_tenant_email
ON users (tenant_id, lower(email))
WHERE deleted_at IS NULL;
```

회원 생성 API는 unique violation을 잡아야 한다.

```text
SQLSTATE 23505 unique_violation
constraint/index name: uq_users_active_tenant_email
```

좋은 처리 흐름은 다음과 같다.

1. 애플리케이션에서 먼저 형식 검증과 빠른 중복 조회를 한다.
2. insert를 시도한다.
3. unique violation이 발생하면 index name을 확인한다.
4. 해당 업무 오류로 변환한다.
5. 클라이언트에는 "이미 사용 중인 이메일"처럼 안정적인 메시지를 반환한다.

애플리케이션 사전 검증은 UX용이고, DB unique index는 정합성의 최종 방어선이다. 둘 중 하나만으로 충분하다고 보면 안 된다.

---

## 흔한 실수 3: 기존 전체 인덱스를 제거하지 못해 쓰기 비용만 늘린다

Partial Index를 추가한 뒤 기존 전체 인덱스를 그대로 두는 경우가 많다.

```sql
CREATE INDEX idx_customers_tenant_created
ON customers (tenant_id, created_at DESC);

CREATE INDEX idx_customers_active_tenant_created
ON customers (tenant_id, created_at DESC)
WHERE deleted_at IS NULL;
```

이 두 인덱스는 역할이 겹칠 수 있다. active 조회는 partial index를 타고, admin 전체 조회는 full index를 탈 수 있다. 둘 다 필요하다면 유지해도 된다. 하지만 전체 조회가 거의 없고 테이블 쓰기가 많다면 full index는 비용만 만든다.

인덱스를 제거하기 전에는 반드시 사용량을 확인한다.

```sql
SELECT
  schemaname,
  relname,
  indexrelname,
  idx_scan,
  idx_tup_read,
  idx_tup_fetch
FROM pg_stat_user_indexes
WHERE relname = 'customers'
ORDER BY idx_scan DESC;
```

크기도 함께 본다.

```sql
SELECT
  indexrelid::regclass AS index_name,
  pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_index
WHERE indrelid = 'customers'::regclass
ORDER BY pg_relation_size(indexrelid) DESC;
```

중복 가능성은 `pg_indexes`와 실제 query workload를 함께 봐야 한다. 단순히 컬럼 목록이 비슷하다고 제거하면 드문 admin query나 foreign key 검증 경로가 느려질 수 있다.

운영에서는 보통 아래 순서를 따른다.

1. partial index를 `CREATE INDEX CONCURRENTLY`로 추가한다.
2. 배포 후 실제 plan과 `pg_stat_user_indexes`를 관찰한다.
3. 기존 full index의 사용량이 사라졌는지 확인한다.
4. 느린 admin query가 없는지 확인한다.
5. 충분한 기간 후 `DROP INDEX CONCURRENTLY`를 검토한다.

---

## 흔한 실수 4: write-heavy 테이블에서 partial index 평가 비용을 무시한다

Partial Index는 인덱스 크기를 줄이지만, 쓰기 시 predicate 평가가 공짜는 아니다.

```sql
CREATE INDEX idx_events_failed_recent
ON events (tenant_id, created_at DESC)
WHERE status = 'FAILED'
  AND retryable = true
  AND error_code IS NOT NULL;
```

row가 insert/update될 때 PostgreSQL은 이 row가 predicate를 만족하는지 판단해야 한다. predicate가 단순하면 비용은 작다. 하지만 expression, function, JSONB extraction이 들어가면 쓰기 경로에서 반복 평가된다.

```sql
CREATE INDEX idx_events_payload_state
ON events (tenant_id, created_at DESC)
WHERE payload->>'state' = 'FAILED';
```

이런 인덱스가 필요한 경우도 있지만, 초당 수천 건 insert되는 event table에서는 JSONB predicate 평가와 index maintenance가 부담이 될 수 있다. 차라리 `state`를 별도 컬럼으로 정규화하고 단순 predicate를 쓰는 편이 낫다.

```sql
ALTER TABLE events
ADD COLUMN state TEXT NOT NULL;

CREATE INDEX idx_events_failed_tenant_created
ON events (tenant_id, created_at DESC)
WHERE state = 'FAILED';
```

쓰기 많은 테이블의 Partial Index는 읽기 개선만 보지 말고 다음을 함께 측정해야 한다.

- insert TPS 변화
- update latency 변화
- WAL bytes 증가/감소
- autovacuum 빈도
- index bloat
- checkpoint 압력
- replica replay lag

Partial Index가 full index보다 작아도, 새 인덱스를 하나 더 추가하는 순간 쓰기 비용은 늘 수 있다. 기존 full index를 대체해 제거할 수 있을 때 이득이 가장 크다.

---

## 무중단 도입: CREATE INDEX CONCURRENTLY와 실패 복구

운영 테이블에 인덱스를 추가할 때는 잠금도 중요하다. 일반 `CREATE INDEX`는 쓰기 차단 위험이 크다. 운영에서는 대개 `CONCURRENTLY`를 쓴다.

```sql
CREATE INDEX CONCURRENTLY idx_customers_active_tenant_created
ON customers (tenant_id, created_at DESC)
WHERE deleted_at IS NULL;
```

`CREATE INDEX CONCURRENTLY`는 일반 생성보다 오래 걸리고, 트랜잭션 블록 안에서 실행할 수 없다.

```sql
BEGIN;
CREATE INDEX CONCURRENTLY ...;
COMMIT;
```

위 방식은 실패한다. migration tool이 모든 migration을 자동 트랜잭션으로 감싼다면 해당 migration만 transaction을 끄는 옵션이 필요하다.

생성 중 실패하면 invalid index가 남을 수 있다.

```sql
SELECT
  c.relname AS index_name,
  i.indisvalid,
  i.indisready
FROM pg_index i
JOIN pg_class c ON c.oid = i.indexrelid
WHERE c.relname = 'idx_customers_active_tenant_created';
```

invalid index는 planner가 사용하지 않지만 유지 비용이나 catalog 혼란을 만들 수 있다. 실패 시에는 상태를 확인하고 제거 후 재시도한다.

```sql
DROP INDEX CONCURRENTLY IF EXISTS idx_customers_active_tenant_created;
```

Partial Unique Index도 concurrently로 만들 수 있다.

```sql
CREATE UNIQUE INDEX CONCURRENTLY uq_users_active_tenant_email
ON users (tenant_id, lower(email))
WHERE deleted_at IS NULL;
```

다만 기존 데이터에 중복이 있으면 생성이 실패한다. 그러므로 unique partial index를 만들기 전에는 반드시 중복을 찾는다.

```sql
SELECT tenant_id, lower(email), count(*)
FROM users
WHERE deleted_at IS NULL
GROUP BY tenant_id, lower(email)
HAVING count(*) > 1;
```

중복이 있으면 어떤 row를 살리고 어떤 row를 정리할지 업무적으로 결정해야 한다. 인덱스 생성은 데이터 정합성 문제를 대신 해결하지 않는다. 숨어 있던 문제를 드러낼 뿐이다.

---

## 관측: Partial Index가 실제로 일을 하고 있는지 확인하는 법

인덱스를 만들었다고 끝이 아니다. 실제 query workload에서 쓰이는지 봐야 한다.

### 1) EXPLAIN으로 plan 확인

가장 먼저 실제 hot path 쿼리를 본다.

```sql
EXPLAIN (ANALYZE, BUFFERS, SETTINGS)
SELECT id, email, name
FROM customers
WHERE tenant_id = 42
  AND deleted_at IS NULL
ORDER BY created_at DESC
LIMIT 50;
```

확인할 것은 다음이다.

- partial index 이름이 plan에 등장하는가?
- `actual time`이 줄었는가?
- `Buffers: shared read`와 `shared hit`가 어떻게 변했는가?
- `Rows Removed by Filter`가 줄었는가?
- sort가 사라졌는가?
- estimate rows와 actual rows가 크게 어긋나지 않는가?
- custom/generic plan 차이가 있는가?

### 2) pg_stat_user_indexes로 사용량 확인

배포 후 일정 기간이 지나면 index scan count를 본다.

```sql
SELECT
  relname,
  indexrelname,
  idx_scan,
  idx_tup_read,
  idx_tup_fetch,
  pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes
WHERE relname IN ('customers', 'orders', 'jobs')
ORDER BY idx_scan DESC;
```

`idx_scan`이 0이라고 바로 제거하면 안 된다. 통계가 reset되었을 수 있고, 드문 운영 쿼리용 인덱스일 수 있다. 하지만 hot path용으로 만든 partial index가 며칠 동안 0이라면 쿼리가 predicate를 포함하지 않거나 planner가 선택하지 않는 것이다.

### 3) pg_stat_statements로 쿼리 fingerprint 확인

쿼리 텍스트가 예상과 다르게 parameterized되어 있을 수 있다.

```sql
SELECT
  query,
  calls,
  mean_exec_time,
  rows
FROM pg_stat_statements
WHERE query ILIKE '%customers%'
ORDER BY total_exec_time DESC
LIMIT 20;
```

여기서 `deleted_at IS NULL`이 빠져 있거나, `status = $2`처럼 generic plan을 유도하는 형태인지 확인한다. ORM이 생성한 SQL은 코드에서 기대한 SQL과 다를 때가 많다.

### 4) 인덱스 크기와 bloat 확인

Partial Index의 핵심 이득 중 하나는 크기다.

```sql
SELECT
  c.relname AS index_name,
  pg_size_pretty(pg_relation_size(c.oid)) AS size
FROM pg_class c
JOIN pg_index i ON i.indexrelid = c.oid
WHERE i.indrelid = 'customers'::regclass
ORDER BY pg_relation_size(c.oid) DESC;
```

크기가 기대만큼 줄지 않았다면 predicate 선택도가 낮은 것이다. 예를 들어 active row가 전체의 95%라면 `deleted_at IS NULL` partial index는 full index보다 크게 작지 않다. 이 경우 이득은 unique semantics나 특정 정렬 최적화에 있을 수 있지만, 단순 크기 절감은 제한적이다.

---

## 의사결정 기준: 언제 Partial Index를 선택할 것인가

Partial Index를 만들기 전 아래 질문에 답해보면 과도한 인덱스를 줄일 수 있다.

### 1) predicate 선택도가 충분한가?

좋은 후보:

- active row가 전체의 10~30% 이하
- 미처리 job이 전체의 1% 이하
- 실패/대기 상태가 전체의 작은 일부
- idempotency key가 있는 row만 중복 확인 필요
- tenant별 active subset이 hot path 대부분

애매한 후보:

- active row가 전체의 90% 이상
- status 값이 균등 분포
- predicate가 자주 바뀜
- 조회마다 조건이 optional
- 쿼리가 predicate 밖의 row도 자주 봄

선택도가 낮아도 partial unique처럼 제약 표현이 목적이면 만들 수 있다. 하지만 성능 개선을 기대한다면 row 비율을 먼저 확인해야 한다.

```sql
SELECT
  count(*) AS total,
  count(*) FILTER (WHERE deleted_at IS NULL) AS active,
  round(
    100.0 * count(*) FILTER (WHERE deleted_at IS NULL) / nullif(count(*), 0),
    2
  ) AS active_pct
FROM customers;
```

### 2) predicate가 업무적으로 안정적인가?

`deleted_at IS NULL`, `canceled_at IS NULL`, `processed_at IS NULL`은 비교적 안정적이다. 데이터 생명주기의 핵심이기 때문이다.

반면 `priority >= 7`, `score > 0.85`, `type IN (...)`는 product rule 변화에 취약할 수 있다. 이런 조건은 먼저 쿼리 빈도와 변경 가능성을 따져야 한다.

### 3) 쿼리에서 predicate를 항상 명시할 수 있는가?

Partial Index는 query contract와 붙어 있다. repository, ORM scope, API path가 predicate를 안정적으로 포함해야 한다.

좋은 구조:

```sql
-- active 고객 전용 repository 메서드
WHERE tenant_id = $1
  AND deleted_at IS NULL
```

애매한 구조:

```sql
-- includeDeleted 파라미터에 따라 조건이 optional
WHERE tenant_id = $1
  AND ($2::boolean OR deleted_at IS NULL)
```

두 번째 쿼리는 `$2` 값에 따라 active만 볼 수도 있고 전체를 볼 수도 있다. 이런 범용 쿼리는 partial index와 잘 맞지 않는다. hot path는 별도 쿼리로 분리하는 편이 낫다.

### 4) 기존 인덱스를 대체할 수 있는가?

Partial Index를 추가만 하면 쓰기 비용이 늘 수 있다. 가장 좋은 경우는 기존 full index를 partial index로 대체하는 것이다.

예를 들어 기존 인덱스가 있다.

```sql
CREATE INDEX idx_tasks_assignee_due
ON tasks (assignee_id, due_at);
```

실제 쿼리 대부분은 열린 task만 본다.

```sql
WHERE assignee_id = $1
  AND closed_at IS NULL
ORDER BY due_at
```

이 경우 아래로 대체할 수 있다.

```sql
CREATE INDEX idx_tasks_open_assignee_due
ON tasks (assignee_id, due_at)
WHERE closed_at IS NULL;
```

단, 닫힌 task 조회가 필요한 화면이 있는지 확인해야 한다. 있으면 느려져도 되는지, 별도 archive 인덱스가 필요한지 결정한다.

---

## 체크리스트: 운영에 넣기 전 확인할 것

Partial Index 도입 전 체크리스트는 아래처럼 잡을 수 있다.

1. 대상 쿼리의 실제 SQL을 `pg_stat_statements` 또는 로그에서 확인했다.
2. 쿼리에 partial index predicate가 명시적으로 포함되어 있다.
3. predicate 컬럼의 분포를 측정했다.
4. active/hot subset이 충분히 작거나, partial unique 같은 명확한 제약 목적이 있다.
5. prepared statement와 generic plan에서 인덱스 선택이 유지되는지 확인했다.
6. ORM이 조건을 optional parameter로 바꾸지 않는지 확인했다.
7. 기존 full index와 역할이 겹치는지 비교했다.
8. `CREATE INDEX CONCURRENTLY`로 만들 migration 방식을 준비했다.
9. unique index라면 기존 중복 데이터를 먼저 찾았다.
10. 실패 시 invalid index를 확인하고 제거하는 절차를 준비했다.
11. 배포 후 `EXPLAIN (ANALYZE, BUFFERS)`로 실제 plan을 검증했다.
12. 배포 후 `pg_stat_user_indexes`로 사용량을 관찰했다.
13. 상태값이나 생명주기 정책이 바뀔 때 index predicate를 리뷰하는 규칙을 만들었다.

---

## 실무 판단 요약

Partial Index는 "인덱스를 작게 만드는 기능"이라고만 이해하면 반쪽이다. 더 정확히는 **업무적으로 뜨거운 row 집합을 DB 구조로 분리하는 기능**이다.

soft delete에서 active row만 인덱싱하면 사용자 API가 과거 이력 때문에 느려지지 않는다. 작업 큐에서 `READY` row만 인덱싱하면 완료된 job이 워커의 탐색 공간을 더럽히지 않는다. Partial Unique Index를 쓰면 "활성 상태에서만 유일" 같은 업무 규칙을 애플리케이션 race condition 없이 표현할 수 있다.

반대로 predicate가 불안정하거나, 쿼리가 predicate를 명시하지 않거나, ORM이 모든 조건을 parameter로 추상화하거나, 기존 full index를 제거하지 못하면 Partial Index는 또 하나의 관리 대상이 된다. 작은 인덱스가 항상 단순한 운영을 의미하지는 않는다.

좋은 Partial Index 설계는 아래 문장으로 설명할 수 있어야 한다.

> 이 테이블에서 온라인 경로가 반복해서 보는 row 집합은 이것이고, 그 집합 밖의 row는 느리게 보거나 다른 경로로 본다.

이 문장을 팀원이 이해하고, 쿼리와 migration과 관측 지표가 같은 방향을 가리키면 Partial Index는 매우 강력하다.

## 한줄정리

PostgreSQL Partial Index는 조건이 붙은 작은 인덱스가 아니라, hot row 집합과 업무 제약을 명시적으로 분리해 읽기 성능·쓰기 비용·데이터 무결성을 함께 조정하는 운영 설계 도구다.
