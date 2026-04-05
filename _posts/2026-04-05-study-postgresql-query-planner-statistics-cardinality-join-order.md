---
layout: post
title: "PostgreSQL 실행 계획 실전: 통계, 카디널리티, Join Order로 플래너 오판 줄이기"
date: 2026-04-05 11:40:00 +0900
categories: [sql]
tags: [study, sql, postgresql, query-planner, explain, cardinality-estimation, join-order, statistics, performance]
permalink: /sql/2026/04/05/study-postgresql-query-planner-statistics-cardinality-join-order.html
---

## 배경: 인덱스도 있는데 왜 PostgreSQL은 자꾸 이상한 실행 계획을 고를까?

PostgreSQL 튜닝을 하다 보면 꼭 한 번은 이런 장면을 본다.

- 개발 환경에서는 빠르던 쿼리가 운영에서는 갑자기 느려진다
- 분명 적절한 인덱스가 있는데도 `Seq Scan`을 탄다
- 어제까지 `Hash Join`이던 쿼리가 오늘은 `Nested Loop`로 바뀌며 수십 배 느려진다
- 특정 테넌트나 특정 상태값에서만 유독 실행 시간이 튄다
- `EXPLAIN`의 estimated rows는 수십 건인데 실제는 수십만 건이다

이때 많은 팀이 바로 인덱스를 하나 더 만들거나, `enable_seqscan=off` 같은 위험한 우회를 고민한다. 하지만 실무에서 진짜 중요한 질문은 그 전 단계에 있다.

> **왜 PostgreSQL 플래너가 이 쿼리를 그렇게 싸다고 착각했는가?**

PostgreSQL은 마법사가 아니다. 플래너는 테이블의 실제 값을 전부 들여다본 뒤 최적 경로를 계산하지 않는다. 대신 **통계(statistics)** 와 **비용 모델(cost model)** 을 바탕으로, 지금 가능한 후보 계획 중 가장 싸 보이는 계획을 고른다. 그래서 통계가 현실과 어긋나거나, 데이터 분포가 한쪽으로 치우치거나, 컬럼 간 상관관계를 모른 채 독립이라고 가정하면 플래너는 아주 그럴듯하게 틀린 판단을 한다.

특히 중급 이상 개발자에게 중요한 건 아래다.

- `EXPLAIN ANALYZE`에서 진짜 먼저 봐야 하는 숫자는 무엇인가?
- estimated rows와 actual rows 차이가 왜 그렇게 중요한가?
- PostgreSQL은 어떤 통계를 가지고 selectivity를 추정하는가?
- 다중 조건 필터에서 왜 플래너가 자주 오판하는가?
- Join order와 join algorithm은 어떤 식으로 연결되는가?
- `ANALYZE`, `default_statistics_target`, `CREATE STATISTICS`는 언제 써야 하는가?
- 힌트 없이도 플래너를 더 똑똑하게 만드는 방법은 무엇인가?

오늘 글은 `EXPLAIN` 보는 법 입문이 아니다. 목표는 **PostgreSQL 플래너가 쿼리를 어떻게 오해하는지 구조적으로 이해하고, 통계·카디널리티·Join Order를 통해 실행 계획 오판을 줄이는 실무 기준**을 정리하는 것이다.

핵심은 여섯 가지다.

1. PostgreSQL 튜닝의 시작점은 인덱스 추가가 아니라 **카디널리티 추정 오차 확인**이다
2. 플래너는 컬럼 분포를 샘플 기반 통계로 이해하므로, **데이터 편향과 컬럼 상관관계**를 자주 놓친다
3. 잘못된 row estimate는 단순 숫자 오차가 아니라 **Join Order와 Join Algorithm 전체를 왜곡**한다
4. `ANALYZE`만으로 해결되는 문제와, `CREATE STATISTICS`나 쿼리 구조 변경이 필요한 문제는 다르다
5. `EXPLAIN ANALYZE`는 실행 시간이 아니라 **estimate와 actual의 차이**를 읽는 도구다
6. 플래너 튜닝의 목표는 힌트로 강제하는 것이 아니라 **플래너가 현실을 더 잘 보게 만드는 것**이다

---

## 먼저 큰 그림: PostgreSQL 플래너는 “정답”이 아니라 “가장 싸 보이는 계획”을 고른다

실행 계획을 이해할 때 가장 먼저 버려야 할 오해는 이것이다.

- 플래너는 항상 최적 계획을 찾는다
- 인덱스가 있으면 인덱스를 타는 게 맞다
- `Seq Scan`이면 무조건 나쁜 계획이다

실제 PostgreSQL은 다음 순서로 움직인다.

1. SQL을 파싱해 논리 구조를 만든다
2. 가능한 여러 실행 경로를 탐색한다
3. 각 경로의 비용을 추정한다
4. 가장 비용이 낮아 보이는 계획을 선택한다

여기서 핵심은 두 단어다.

- **추정(estimate)**
- **비용(cost)**

즉 플래너는 실제 실행 전에는 정확한 row 수를 모른다. 대신 통계 정보로 “이 조건이면 대략 몇 행쯤 나오겠지”, “이 정도 row 수면 hash join이 낫겠지”, “이 조건은 인덱스보다 sequential scan이 더 싸겠지”를 계산한다.

문제는 이 계산이 틀리면, 뒤에 이어지는 판단도 연쇄적으로 틀린다는 점이다.

예를 들어 실제로는 10만 행이 나오는 조건을 플래너가 100행으로 오판했다고 하자. 그러면 다음과 같은 왜곡이 생긴다.

- 작은 결과셋이라고 착각해 `Nested Loop`를 고른다
- join 입력이 작다고 착각해 join 순서를 잘못 정한다
- 정렬 비용이 낮다고 착각한다
- 인덱스 랜덤 접근이 싸다고 착각한다
- `work_mem` 안에 충분히 들어갈 거라 생각하지만 실제론 spill이 난다

결국 느린 쿼리의 본질은 의외로 단순하다.

> **플래너가 실제 row 수를 얼마나 틀리게 추정했는가**

이걸 보는 순간, “인덱스를 더 만들까?”보다 먼저 “왜 이렇게 틀렸지?”로 사고가 바뀐다.

---

## 핵심 개념 1: 실행 계획에서 가장 먼저 봐야 하는 건 비용이 아니라 rows 오차다

많은 사람이 `EXPLAIN ANALYZE`를 볼 때 맨 먼저 실행 시간과 node 이름을 본다.

예를 들어 이런 계획을 보자.

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT o.id, o.user_id, o.total_amount
FROM orders o
WHERE o.status = 'PAID'
  AND o.created_at >= now() - interval '7 days';
```

대충 이런 출력이 나온다고 하자.

```text
Bitmap Heap Scan on orders  (cost=120.00..1450.00 rows=1200 width=24)
                            (actual time=3.200..210.500 rows=187532 loops=1)
```

여기서 초보자는 보통 이렇게 본다.

- Bitmap Heap Scan이네
- cost가 1450 정도네
- 실제 시간은 210ms네

하지만 실무에서 먼저 봐야 할 건 이것이다.

- **estimated rows = 1,200**
- **actual rows = 187,532**

즉 플래너가 결과 row 수를 **156배 이상 과소추정**했다.

이 차이는 그냥 오차가 아니다. 이 오차 하나로 아래 판단이 다 흔들린다.

- 인덱스 접근이 유리한지
- 정렬이 비싼지
- 해시 테이블이 메모리에 들어갈지
- 어떤 테이블을 바깥 루프로 둘지
- join 순서를 어떻게 잡을지

### 왜 rows 오차가 이렇게 중요할까?

PostgreSQL의 대부분 비용 계산은 결국 “얼마나 많은 row를 읽고, 얼마나 많은 page를 건드리고, 얼마나 많은 비교를 할 것인가”에 매달려 있다.

즉 row estimate가 틀리면 cost estimate도 틀린다.

그래서 느린 쿼리를 디버깅할 때는 아래 순서가 더 좋다.

1. 가장 느린 node를 찾는다
2. 그 node와 상위 node들에서 `rows` vs `actual rows` 차이를 본다
3. **오차가 처음 폭발하는 지점**을 찾는다
4. 그 지점의 필터/조인 조건/통계를 의심한다

대개 진짜 원인은 마지막 느린 node가 아니라, **그보다 앞에서 잘못 추정된 작은 숫자**에 있다.

---

## 핵심 개념 2: PostgreSQL은 어떤 통계로 selectivity를 추정하는가

플래너를 이해하려면 PostgreSQL이 컬럼을 어떻게 바라보는지 알아야 한다. 기본적으로 PostgreSQL은 `ANALYZE`를 통해 테이블을 샘플링하고, 컬럼별 통계를 저장한다.

대표적으로 아래 정보가 중요하다.

- `n_distinct`: 서로 다른 값 개수 추정
- `null_frac`: NULL 비율
- `most_common_vals` / `most_common_freqs`: 자주 등장하는 값과 빈도
- `histogram_bounds`: 값 분포 경계
- `correlation`: 컬럼 값과 물리적 저장 순서의 상관도

실제로는 `pg_stats`에서 이런 정보를 볼 수 있다.

```sql
SELECT
  schemaname,
  tablename,
  attname,
  n_distinct,
  null_frac,
  most_common_vals,
  most_common_freqs,
  histogram_bounds,
  correlation
FROM pg_stats
WHERE tablename = 'orders'
  AND attname IN ('status', 'created_at', 'tenant_id');
```

### 플래너가 이 통계로 하는 일

#### 1) 단일 조건 필터 추정

예를 들어 `status = 'PAID'` 조건이 있으면, 플래너는 `most_common_vals`와 `most_common_freqs`를 이용해 대략 몇 %가 `PAID`인지 계산한다.

#### 2) 범위 조건 추정

`created_at >= '2026-04-01'` 같은 범위 조건은 histogram을 바탕으로 값 분포를 대략 추정한다.

#### 3) 인덱스 접근 비용 추정

`correlation`은 테이블 물리 순서와 인덱스 값 순서가 얼마나 비슷한지를 나타낸다. 상관도가 높으면 인덱스 스캔 후 heap 접근이 비교적 연속적으로 일어나 비용이 낮아질 수 있다.

즉 PostgreSQL은 꽤 많은 정보를 갖고 있다. 문제는 이 정보가 **컬럼 단위 통계**라는 데 있다.

여기서부터 실무 문제의 절반이 시작된다.

---

## 핵심 개념 3: 플래너는 다중 조건에서 컬럼 독립성을 가정하기 쉽다

실제 서비스 데이터는 컬럼이 서로 독립적이지 않은 경우가 많다.

예를 들어 주문 테이블을 생각해보자.

- `status = 'PAID'` 인 주문은 대부분 `paid_at IS NOT NULL`
- `country = 'KR'` 인 사용자는 `currency = 'KRW'` 비율이 압도적
- `tenant_id = 42` 인 데이터는 최근 7일에 특히 많이 몰림
- `deleted_at IS NULL` 인 row만 사실상 대부분 조회 대상

하지만 플래너는 기본적으로 **컬럼 간 상관관계를 충분히 모르면 독립이라고 가정**하는 경우가 많다.

예를 들어 다음 조건을 보자.

```sql
WHERE status = 'PAID'
  AND paid_at IS NOT NULL
```

사람에게는 거의 같은 정보를 두 번 말하는 것처럼 보일 수 있다. 하지만 플래너가 두 조건을 독립이라고 보면 selectivity를 곱해버릴 수 있다.

- `status='PAID'` 비율 20%
- `paid_at IS NOT NULL` 비율 20%
- 독립이라 가정 → 결과 4%

하지만 실제 데이터에서는 거의 완전히 같은 집합일 수 있다. 그러면 진짜 결과는 20%에 가까운데 플래너는 4%로 오판한다.

이게 왜 위험할까?

- 결과 row 수를 과소추정한다
- 작은 결과셋이라고 믿고 Nested Loop를 선택한다
- 인덱스 랜덤 접근 비용을 낮게 본다
- join order를 잘못 잡는다

### 특히 자주 깨지는 패턴

#### 1) soft delete + 상태 컬럼

```sql
WHERE deleted_at IS NULL
  AND status = 'ACTIVE'
```

#### 2) 멀티테넌트 + 최근 시간 범위

```sql
WHERE tenant_id = 42
  AND created_at >= now() - interval '1 day'
```

특정 대형 테넌트만 최근 데이터가 몰려 있으면, 전체 평균 통계로는 절대 정확히 보기 어렵다.

#### 3) 국가/언어/통화 같은 종속 컬럼

```sql
WHERE country = 'KR'
  AND currency = 'KRW'
```

#### 4) 결제/주문 상태 전이 컬럼

```sql
WHERE payment_status = 'CAPTURED'
  AND captured_at IS NOT NULL
```

즉 “조건이 둘 이상인데 왜 estimate가 이상하지?” 싶으면, 인덱스보다 먼저 **컬럼 상관관계**를 의심하는 편이 맞다.

---

## 핵심 개념 4: 잘못된 카디널리티 추정은 Join Order와 Join Algorithm 전체를 틀리게 만든다

플래너가 row 수를 잘못 추정하면 가장 크게 흔들리는 것은 join이다.

PostgreSQL은 join을 고를 때 대략 아래를 함께 본다.

- 어느 테이블을 먼저 읽을지
- 어떤 순서로 테이블을 붙일지
- `Nested Loop`, `Hash Join`, `Merge Join` 중 무엇을 쓸지
- 각 단계 중간 결과가 얼마나 커질지

여기서 핵심은 **중간 결과 크기**다.

### Join Order가 중요한 이유

세 테이블 조인을 생각해보자.

```sql
SELECT ...
FROM orders o
JOIN order_items oi ON oi.order_id = o.id
JOIN products p ON p.id = oi.product_id
WHERE o.tenant_id = 42
  AND o.created_at >= now() - interval '1 day'
  AND p.category_id = 10;
```

사람은 이렇게 생각할 수 있다.

- 먼저 `orders`를 tenant와 날짜로 강하게 줄인다
- 그 뒤 `order_items`를 붙인다
- 마지막에 `products` category 필터를 적용한다

하지만 플래너가 `tenant_id=42 AND 최근 1일` 조건 결과를 너무 작게 혹은 너무 크게 오해하면, 아예 다른 join 순서를 선택할 수 있다.

예를 들어:

- `products`에서 category 10이 아주 적다고 착각 → `products -> order_items -> orders`
- `orders`가 매우 작다고 착각 → `orders`를 outer로 둔 nested loop
- 실제론 `orders`가 수십만 건 → nested loop 폭발

### Join Algorithm이 바뀌는 기준

#### 1) Nested Loop

대개 바깥 입력이 아주 작고, 안쪽에 인덱스 접근이 가능할 때 좋다.

문제는 바깥 입력이 실제로 작지 않으면, 인덱스 접근을 수십만 번 반복하며 재앙이 된다는 점이다.

#### 2) Hash Join

한쪽 입력을 hash table로 만들고 다른 쪽을 probe한다. 중대형 조인에서 자주 유리하다.

하지만 플래너가 입력이 아주 작다고 착각하면 굳이 hash join을 안 고를 수 있다.

#### 3) Merge Join

양쪽이 정렬돼 있거나 정렬 비용 대비 이득이 있을 때 선택된다. 범위 조인이나 대형 정렬 결과 재사용이 있을 때 의미가 있다.

결국 join 튜닝의 핵심도 인덱스 이름보다 아래 질문이다.

> **플래너는 이 중간 결과를 몇 row로 보고 있는가?**

이 숫자가 틀리면 join은 거의 항상 틀어진다.

---

## 핵심 개념 5: `ANALYZE`는 중요하지만, 모든 통계 문제를 해결해주지는 않는다

실행 계획이 이상하면 가장 먼저 듣는 조언이 “ANALYZE 해보세요”다. 맞는 말이다. 하지만 절반만 맞다.

### `ANALYZE`가 잘 해결하는 문제

- 대량 INSERT/UPDATE/DELETE 뒤 통계가 오래된 경우
- 값 분포가 최근에 크게 바뀐 경우
- autovacuum/autoanalyze 주기가 충분하지 않은 경우
- 샘플 기반 통계만 다시 뽑아도 오차가 줄어드는 경우

```sql
ANALYZE orders;
```

혹은 특정 컬럼 통계 정밀도를 높일 수도 있다.

```sql
ALTER TABLE orders
ALTER COLUMN tenant_id SET STATISTICS 1000;

ANALYZE orders;
```

`default_statistics_target` 또는 컬럼별 statistics target을 높이면 더 큰 샘플과 더 정교한 MCV/histogram을 기대할 수 있다.

### 그런데 `ANALYZE`만으로 해결 안 되는 문제

#### 1) 컬럼 간 종속성

단일 컬럼 통계를 아무리 정교하게 모아도, `tenant_id`와 `created_at`의 결합 분포는 별개 문제다.

#### 2) 극단적인 편향 데이터

일부 테넌트나 일부 상태값만 유난히 큰 경우, 전체 평균 기반 통계로는 특정 값의 실제 분포를 정확히 반영하기 어렵다.

#### 3) 표현식/함수 기반 조건

```sql
WHERE date(created_at) = current_date
```

이런 조건은 통계 활용과 인덱스 활용 모두 불리해질 수 있다. 쿼리 자체를 바꾸는 편이 낫다.

#### 4) 파라미터별 분포 차이가 큰 prepared statement

어떤 `tenant_id`는 매우 작고 어떤 `tenant_id`는 매우 큰데 generic plan으로 굳어지면, 특정 값에서만 유독 나쁜 계획이 나올 수 있다.

즉 `ANALYZE`는 기본 처방이지만, 진짜 원인이 **종속성, 편향, 쿼리 형태, 파라미터 스니핑 유사 문제**라면 그 다음 수단이 필요하다.

---

## 핵심 개념 6: 다중 컬럼 분포 문제는 `CREATE STATISTICS`가 중요한 무기다

PostgreSQL에서 상대적으로 덜 알려졌지만 실무에서 매우 강력한 기능이 `CREATE STATISTICS`다.

이 기능은 다중 컬럼에 대해 다음 종류의 확장 통계를 만들 수 있다.

- `dependencies`: 컬럼 간 함수적 종속성
- `ndistinct`: 컬럼 조합의 distinct 추정
- `mcv`: 자주 함께 등장하는 값 조합

예를 들어 아래 상황을 보자.

- `status='PAID'` 이면 `paid_at IS NOT NULL`인 경우가 거의 100%
- `country='KR'` 이면 `currency='KRW'` 비율이 압도적

이럴 때 확장 통계를 줄 수 있다.

```sql
CREATE STATISTICS orders_paid_stats (dependencies, mcv)
ON status, paid_at
FROM orders;

ANALYZE orders;
```

또는 멀티테넌트 시간 편향이 강한 경우:

```sql
CREATE STATISTICS orders_tenant_created_stats (dependencies, ndistinct, mcv)
ON tenant_id, created_at
FROM orders;

ANALYZE orders;
```

### 언제 효과가 큰가?

- 두세 개 조건이 항상 같이 등장한다
- estimate 오차가 단일 컬럼보다 다중 컬럼 조합에서 폭발한다
- 특정 조합의 분포가 전체 평균과 크게 다르다
- join 전 필터 row 수가 자주 과소/과대추정된다

### 한계도 있다

- 모든 문제를 해결하는 건 아니다
- 너무 많은 통계를 무분별하게 만들면 관리 복잡도가 늘어난다
- 쿼리 패턴과 데이터 분포를 모른 채 생성하면 체감이 작을 수 있다

즉 `CREATE STATISTICS`는 “느리면 일단 만들기”가 아니라, **독립성 가정이 명백히 틀린 컬럼 조합에만 정확히 쓰는 도구**다.

---

## `pg_stats`와 `EXPLAIN ANALYZE`를 같이 보는 습관이 중요하다

느린 쿼리 앞에서 가장 생산적인 루프는 아래다.

1. `EXPLAIN (ANALYZE, BUFFERS)`로 estimate 오차 지점 확인
2. 해당 조건 컬럼의 `pg_stats` 확인
3. 데이터 분포/상관관계/편향 여부 점검
4. `ANALYZE`, statistics target, `CREATE STATISTICS`, 쿼리 구조 개선 중 적절한 수단 선택
5. 다시 plan 비교

예를 들어 아래처럼 본다.

```sql
SELECT
  attname,
  n_distinct,
  most_common_vals,
  most_common_freqs,
  correlation
FROM pg_stats
WHERE tablename = 'orders'
  AND attname IN ('tenant_id', 'status', 'created_at');
```

그리고 특정 조합 분포도 직접 확인할 수 있다.

```sql
SELECT tenant_id, count(*)
FROM orders
WHERE created_at >= now() - interval '1 day'
GROUP BY tenant_id
ORDER BY count(*) DESC
LIMIT 20;
```

이런 쿼리를 직접 보면 플래너가 왜 오판하는지 감이 훨씬 빨리 온다.

- 최근 1일 데이터가 몇 개 테넌트에 편중됨
- 특정 status가 최근 구간에서 급증함
- 대부분 값은 균등하지만 일부 MCV가 지배적임

실무에서는 결국 **통계 뷰 + 실행 계획 + 실제 분포 쿼리**를 같이 보는 사람이 문제를 제일 빨리 푼다.

---

## 실무 예시 1: soft delete + 상태 컬럼 때문에 row estimate가 붕괴하는 경우

상황을 보자.

- `users` 테이블에 `deleted_at` 소프트 삭제 컬럼이 있음
- 활성 사용자만 자주 조회함
- `status='ACTIVE'` 와 `deleted_at IS NULL` 이 거의 같은 집합을 의미함

쿼리:

```sql
SELECT id, email
FROM users
WHERE deleted_at IS NULL
  AND status = 'ACTIVE';
```

플래너가 컬럼 독립성을 가정하면,

- `deleted_at IS NULL` 70%
- `status='ACTIVE'` 60%
- 결과 42% 정도로 추정

하지만 실제로는 활성 사용자의 대부분이 미삭제 사용자라서 60%에 훨씬 가까울 수 있다. 반대로 상태 분포에 따라 더 작을 수도 있다. 핵심은 **두 조건이 독립이 아니라는 것**이다.

이 상황에서 자주 나타나는 문제는 다음과 같다.

- 부분 인덱스가 있는데도 활용이 들쭉날쭉함
- join 전에 `users`를 충분히 줄이지 못했다고 잘못 판단
- 상위 조인에서 nested loop 선택이 흔들림

대응은 보통 세 단계로 간다.

### 1) 실제 분포 확인

```sql
SELECT status,
       (deleted_at IS NULL) AS is_alive,
       count(*)
FROM users
GROUP BY status, (deleted_at IS NULL)
ORDER BY count(*) DESC;
```

### 2) 확장 통계 생성 검토

```sql
CREATE STATISTICS users_status_deleted_stats (dependencies, mcv)
ON status, deleted_at
FROM users;

ANALYZE users;
```

### 3) 자주 쓰는 조건이면 부분 인덱스와 쿼리 형태를 함께 점검

```sql
CREATE INDEX idx_users_active_live
ON users (id)
WHERE deleted_at IS NULL AND status = 'ACTIVE';
```

중요한 건 인덱스 자체보다, **왜 플래너가 이 조건을 몇 row로 보는지**를 먼저 바로잡는 것이다.

---

## 실무 예시 2: 멀티테넌트 테이블에서 특정 대형 테넌트만 유독 느린 이유

멀티테넌트 SaaS에서 정말 흔한 문제다.

전체적으로는 괜찮은 쿼리인데, 특정 대형 고객사만 유독 느리다.

```sql
SELECT *
FROM events
WHERE tenant_id = $1
  AND created_at >= now() - interval '1 day'
ORDER BY created_at DESC
LIMIT 100;
```

왜 이런 일이 생길까?

- 대부분 테넌트는 최근 1일 데이터가 적다
- 몇몇 대형 테넌트는 최근 1일 데이터가 폭증한다
- 플래너는 전체 평균 통계로 `tenant_id + 최근 시간 조건`을 추정한다
- 어떤 값에서는 아주 잘 맞지만, 대형 테넌트에서는 심하게 빗나간다

이 경우 흔한 증상은 아래다.

- 소형 테넌트에는 좋은 plan이 대형 테넌트엔 나쁜 plan이 됨
- generic prepared plan이 특정 tenant에서만 병목을 만듦
- `ORDER BY ... LIMIT` 때문에 잘못된 인덱스 선택이 발생함

### 먼저 확인할 것

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM events
WHERE tenant_id = 42
  AND created_at >= now() - interval '1 day'
ORDER BY created_at DESC
LIMIT 100;
```

여기서 특히 아래를 본다.

- index condition이 무엇인지
- filter로 얼마나 많이 버리는지
- estimate rows와 actual rows 차이
- `Rows Removed by Filter`가 과도한지

### 대응 포인트

#### 1) 쿼리 패턴에 맞는 인덱스 재검토

예를 들어 `(tenant_id, created_at DESC)` 인덱스는 자주 매우 중요하다.

```sql
CREATE INDEX idx_events_tenant_created_at_desc
ON events (tenant_id, created_at DESC);
```

#### 2) 다중 컬럼 통계 고려

```sql
CREATE STATISTICS events_tenant_created_stats (dependencies, mcv, ndistinct)
ON tenant_id, created_at
FROM events;

ANALYZE events;
```

#### 3) generic plan 문제 의심

prepared statement를 오래 쓰는 애플리케이션에서는 일부 파라미터 분포 차이가 크면 generic plan이 평균적으로만 맞고 특정 대형 고객사에는 매우 틀릴 수 있다. 이 경우 단순 인덱스 추가보다 **애플리케이션의 prepared statement 사용 방식**이나 plan cache 전략까지 봐야 한다.

핵심은 이것이다.

> 특정 tenant에서만 느리다면, 인덱스 부재보다 **분포 편향과 평균 통계의 한계**가 원인일 가능성이 높다.

---

## 실무 예시 3: Join Order 오판 때문에 Nested Loop가 폭발하는 경우

다음 쿼리를 보자.

```sql
SELECT o.id, p.name, oi.quantity
FROM orders o
JOIN order_items oi ON oi.order_id = o.id
JOIN products p ON p.id = oi.product_id
WHERE o.tenant_id = 42
  AND o.created_at >= DATE '2026-04-01'
  AND p.category_id = 7;
```

운영에서 이 쿼리가 갑자기 느려졌다고 하자. `EXPLAIN ANALYZE`를 보면 이런 패턴이 나온다.

- `orders` 결과를 200 rows로 추정
- 실제로는 85,000 rows
- 플래너는 `orders`를 바깥 루프로 두고 `order_items` 인덱스 lookup을 반복
- 실제로 인덱스 lookup이 수만 번 발생
- 전체 시간이 급증

이 경우 많은 팀이 `order_items(order_id)` 인덱스를 더 손본다. 하지만 핵심은 이미 있다. 문제는 **밖에서 들어오는 row 수를 너무 작게 본 것**이다.

### 실제 디버깅 순서

#### 1) 오차가 시작된 지점 찾기

`orders` scan 혹은 filter 단계에서 estimate와 actual 차이가 어디서 커지는지 확인한다.

#### 2) 원인 분해

- `tenant_id = 42` 분포 편향인가?
- 날짜 조건과 tenant가 강하게 연관되어 있는가?
- 최근 배치 적재 이후 `ANALYZE`가 늦었는가?

#### 3) 해결 수단 선택

- 통계 갱신
- 확장 통계 생성
- `(tenant_id, created_at)` 인덱스 점검
- 필요 시 쿼리를 더 분명한 단계로 나누기

예를 들어 먼저 orders를 줄이는 CTE 또는 서브쿼리 구조가 플래너에 더 명확할 때도 있다. 다만 PostgreSQL 버전과 최적화 상황에 따라 다르므로, “CTE면 무조건 빠르다” 같은 일반화는 위험하다. 중요한 건 **중간 결과를 플래너가 제대로 추정하도록 돕는 것**이다.

---

## 실무 예시 4: `ORDER BY ... LIMIT` 쿼리에서 잘못된 인덱스 선택이 일어나는 이유

이 패턴도 생각보다 자주 나온다.

```sql
SELECT id, created_at, status
FROM orders
WHERE tenant_id = 42
  AND status = 'PAID'
ORDER BY created_at DESC
LIMIT 50;
```

플래너 입장에서는 두 가지 유혹이 있다.

1. `created_at DESC` 인덱스를 타면 정렬 없이 바로 LIMIT 50을 가져올 수 있을 것 같다
2. 하지만 실제론 `tenant_id=42 AND status='PAID'` 조건에 맞는 row를 찾기 위해 엄청나게 많이 스캔해야 할 수도 있다

즉 planner가 “앞에서 조금만 읽으면 50개 금방 나오겠지”라고 오해하면, 정렬 회피를 위해 잘못된 인덱스를 고를 수 있다.

이건 결국 다음 문제로 돌아온다.

- `tenant_id`, `status`, `created_at`의 결합 분포를 얼마나 정확히 아는가
- 어떤 인덱스가 실제로 조건 축소와 정렬 요구를 함께 만족하는가

이런 쿼리에서는 아래 인덱스가 자주 유효하다.

```sql
CREATE INDEX idx_orders_tenant_status_created_desc
ON orders (tenant_id, status, created_at DESC);
```

하지만 여기서도 기억할 점이 있다.

- 인덱스를 만들었는데도 plan이 이상하면 통계 문제일 수 있다
- 특정 tenant에서만 느리면 데이터 편향 문제일 수 있다
- `Rows Removed by Filter`가 많으면 planner가 LIMIT 효과를 과신했을 수 있다

즉 `ORDER BY LIMIT` 문제도 본질은 **정렬 최적화**보다 **카디널리티 오판**인 경우가 많다.

---

## 트레이드오프 1: statistics target을 높이면 더 정확해질 수 있지만 공짜는 아니다

통계가 너무 거칠다고 느껴질 때 흔히 하는 조치가 statistics target을 올리는 것이다.

```sql
ALTER TABLE orders
ALTER COLUMN tenant_id SET STATISTICS 1000;
```

### 장점

- MCV와 histogram이 더 정교해질 수 있다
- 편향 데이터에서 추정 개선 여지가 있다
- 복잡한 조건 selectivity 추정이 나아질 수 있다

### 비용

- `ANALYZE` 시간이 늘어난다
- 통계 저장량이 늘어난다
- 모든 컬럼에 무작정 올리면 효과 대비 비용이 커질 수 있다

즉 statistics target은 전역으로 마구 높일 값이 아니라, **오차가 큰 핵심 컬럼만 선별적으로 올리는 것**이 보통 맞다.

---

## 트레이드오프 2: 확장 통계는 강력하지만, 쿼리 패턴을 모르면 효과가 제한적이다

`CREATE STATISTICS`는 분명 강력하다. 하지만 무조건 많이 만드는 것이 답은 아니다.

### 장점

- 컬럼 독립성 가정 문제를 완화한다
- join 전 필터 row 추정이 개선될 수 있다
- 특정 조합 쿼리에서 플래너 오판을 크게 줄일 수 있다

### 비용

- 어떤 컬럼 조합이 중요한지 이해가 필요하다
- 테이블 스키마/쿼리 변경 시 관리 포인트가 늘어난다
- 모든 조합에 만들면 복잡도만 커진다

즉 확장 통계는 “속도 안 나오네 하나 만들자”가 아니라, **estimate 오차가 반복적으로 발생하는 조건 조합에만 정확히 꽂는 도구**다.

---

## 트레이드오프 3: 쿼리 구조를 바꾸면 플래너가 더 잘 볼 수 있지만, 가독성과 재사용성은 달라질 수 있다

어떤 경우엔 통계보다 쿼리 구조가 문제다.

예를 들어 아래는 planner가 추정하기 불리한 형태일 수 있다.

```sql
WHERE date(created_at) = current_date
```

다음처럼 바꾸면 보통 더 낫다.

```sql
WHERE created_at >= current_date
  AND created_at < current_date + interval '1 day'
```

또는 거대한 OR 조건, 함수 wrapping, 지나치게 복잡한 서브쿼리, 선택도가 다른 조건을 뒤섞은 쿼리는 통계가 좋아도 planner가 불리해질 수 있다.

다만 쿼리 구조 변경은 항상 공짜가 아니다.

- 코드 가독성이 떨어질 수 있다
- ORM 추상화와 충돌할 수 있다
- 여러 데이터베이스 벤더 호환성이 깨질 수 있다

그래서 실무적으로는 보통 아래 순서가 좋다.

1. 통계 문제인지 확인
2. 인덱스/확장 통계로 해결 가능한지 확인
3. 그래도 안 되면 쿼리 구조를 더 planner-friendly 하게 조정

---

## 흔한 실수 1: `Seq Scan`만 보면 무조건 나쁜 계획이라고 생각한다

테이블 대부분을 읽는 조건이라면 `Seq Scan`이 맞을 때가 많다. 인덱스는 “있다”보다 “읽을 row 비율이 작다”에서 힘을 발휘한다.

문제는 `Seq Scan` 자체가 아니라, **플래너가 얼마나 읽을지 잘못 본 상태에서 `Seq Scan` 또는 인덱스를 선택하는 것**이다.

---

## 흔한 실수 2: estimated cost 숫자만 보고 실제 원인을 놓친다

cost는 내부 비교용 상대값이다. 절대적인 시간 단위가 아니다. 느린 이유를 보려면 먼저 `rows`와 `actual rows` 차이를 봐야 한다.

---

## 흔한 실수 3: `ANALYZE` 한 번으로 모든 planner 문제를 해결하려 한다

오래된 통계 문제라면 맞다. 하지만 컬럼 상관관계, 편향 분포, prepared statement generic plan 문제는 `ANALYZE`만으로 충분하지 않을 수 있다.

---

## 흔한 실수 4: 힌트나 GUC 강제로 특정 join을 고정하려 한다

`enable_nestloop=off` 같은 방법은 디버깅에는 유용할 수 있지만, 상시 해법으로 쓰면 다른 쿼리를 망칠 수 있다. 핵심은 플래너를 이기려는 게 아니라 **플래너가 현실을 더 잘 보게 하는 것**이다.

---

## 흔한 실수 5: 단일 컬럼 인덱스만 계속 추가한다

실제 쿼리가 `tenant_id + created_at + status` 조합으로 움직이는데 단일 인덱스만 잔뜩 늘리면 planner가 원하는 경로를 못 만들 수 있다. 동시에 쓰기 비용만 늘어난다.

---

## 흔한 실수 6: `EXPLAIN`만 보고 `EXPLAIN ANALYZE`를 안 본다

실행 전 추정만 보면 planner가 실제로 얼마나 틀렸는지 모른다. 운영 DB에서 조심해야 하지만, 검증 가능한 환경에서는 `EXPLAIN ANALYZE`가 거의 필수다.

---

## 흔한 실수 7: 문제 쿼리만 보고 데이터 분포는 안 본다

SQL 한 줄만 읽어서는 편향 테넌트, 상태 쏠림, soft delete 편향 같은 현실 데이터를 알 수 없다. planner 문제는 결국 데이터 문제다.

---

## 진단 체크리스트: 느린 PostgreSQL 조회 쿼리를 볼 때 순서대로 확인할 것

### 1) 실행 계획 자체

- [ ] `EXPLAIN (ANALYZE, BUFFERS)`로 봤는가?
- [ ] 가장 큰 시간/버퍼를 쓰는 node는 어디인가?
- [ ] `rows`와 `actual rows` 차이가 처음 커지는 지점은 어디인가?
- [ ] `Rows Removed by Filter`가 과도한가?

### 2) 통계와 분포

- [ ] 관련 컬럼 `pg_stats`를 확인했는가?
- [ ] 값 편향이나 특정 MCV 쏠림이 있는가?
- [ ] 여러 조건 컬럼이 사실상 종속적인가?
- [ ] 최근 대량 적재/삭제 후 `ANALYZE`가 충분히 반영됐는가?

### 3) 인덱스와 접근 경로

- [ ] 실제 WHERE + JOIN + ORDER BY 패턴에 맞는 인덱스인가?
- [ ] 단일 인덱스를 여러 개 두는 대신 복합 인덱스가 더 맞지 않는가?
- [ ] 부분 인덱스가 자주 쓰는 조건과 맞는가?
- [ ] 인덱스를 탔는데도 filter discard가 과도하지 않은가?

### 4) 조인

- [ ] 잘못된 row estimate 때문에 Nested Loop가 폭발하는가?
- [ ] Hash Join이 더 맞아 보이는데 입력이 작다고 착각하고 있지 않은가?
- [ ] Join order가 데이터 축소 순서와 어긋나지 않는가?
- [ ] 중간 결과 크기를 실제보다 작게 또는 크게 보고 있지 않은가?

### 5) 해결 수단 선택

- [ ] 단순 `ANALYZE`로 해결되는 문제인가?
- [ ] statistics target 조정이 필요한가?
- [ ] `CREATE STATISTICS`가 필요한 다중 컬럼 문제인가?
- [ ] 쿼리 구조 자체를 planner-friendly 하게 바꿔야 하는가?
- [ ] prepared statement/generic plan 문제 가능성이 있는가?

---

## 설계 체크리스트: 새 기능 쿼리를 만들 때 미리 점검할 것

- [ ] 필터 조건이 여러 컬럼 조합이라면, 그 컬럼들이 실제로 독립적인가?
- [ ] 멀티테넌트/최근시간/상태값처럼 편향이 심한 컬럼이 있는가?
- [ ] 자주 쓰는 정렬과 LIMIT 패턴에 맞는 복합 인덱스가 있는가?
- [ ] soft delete, 상태 컬럼, nullable 시점 컬럼처럼 사실상 종속적인 조건을 반복 사용하는가?
- [ ] 배포 후 row estimate 오차를 관측할 수 있게 slow query + plan 수집 체계를 갖췄는가?

새 쿼리 설계에서 이걸 먼저 보면, 나중에 “운영에서만 느린데요?”를 크게 줄일 수 있다.

---

## 운영 원칙: PostgreSQL 플래너는 이겨먹는 대상이 아니라 학습시킬 대상에 가깝다

실무에서 가장 안정적인 접근은 늘 비슷하다.

### 1) 먼저 plan을 읽고, 그다음 인덱스를 고민한다

인덱스는 결과이지 출발점이 아니다.

### 2) row estimate 오차가 큰 지점부터 고친다

느린 마지막 node보다, 그 앞에서 잘못된 추정이 시작된 지점을 고치는 편이 효과가 크다.

### 3) 통계 문제와 접근 경로 문제를 구분한다

- 통계 문제: `ANALYZE`, statistics target, `CREATE STATISTICS`
- 접근 경로 문제: 복합 인덱스, 부분 인덱스, 쿼리 구조

이 둘을 섞으면 삽질이 길어진다.

### 4) 편향 데이터는 평균 통계가 못 본다는 사실을 늘 기억한다

멀티테넌트, 지역, 상태, 최근시간, soft delete는 거의 항상 평균을 깨뜨린다.

### 5) 디버깅용 강제 설정은 임시로만 쓴다

`enable_hashjoin=off`, `enable_nestloop=off` 같은 옵션은 원인 확인에는 좋지만, 상시 해법으로 쓰면 전체 시스템 관점에서 위험하다.

---

## 한 줄 정리

PostgreSQL 실행 계획 튜닝의 핵심은 인덱스를 더 만드는 것이 아니라, **플래너가 통계와 카디널리티를 통해 실제 데이터 분포를 얼마나 정확히 보게 만들 수 있는지, 그리고 그 결과 Join Order와 Join Algorithm을 덜 틀리게 고르게 만드는지**에 있다.
