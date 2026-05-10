---
layout: post
title: "PostgreSQL Index Only Scan 실전: Covering Index, INCLUDE, Visibility Map, Heap Fetch를 함께 설계하는 법"
date: 2026-05-10 11:40:00 +0900
categories: [sql]
tags: [study, sql, postgresql, index-only-scan, covering-index, include, visibility-map, heap-fetch, performance]
permalink: /sql/2026/05/10/study-postgresql-index-only-scan-covering-index-visibility-map-include.html
---

## 배경: 인덱스도 있는데 왜 PostgreSQL은 아직도 힙(Heap)을 보러 가는가

PostgreSQL 튜닝을 하다 보면 꽤 자주 이런 상황을 만난다.

- `WHERE tenant_id = ? AND status = ?` 인덱스를 만들었는데 조회가 기대만큼 빠르지 않다.
- `LIMIT 50` 조회인데도 I/O가 꽤 크다.
- 실행 계획에는 `Index Scan`이 찍히지만 `Buffers`를 보면 heap 접근이 여전히 많다.
- 같은 쿼리인데 어느 날은 빠르고 어느 날은 느리다.
- 분명 읽기 위주 API인데 autovacuum 상태에 따라 체감 성능이 달라진다.

이 지점에서 많은 팀이 "인덱스가 있으니 충분하다"고 생각한다. 하지만 PostgreSQL에서는 **인덱스가 있다는 사실과, 인덱스만 보고 쿼리를 끝낼 수 있다는 사실이 완전히 다르다.**

핵심은 두 가지다.

1. 인덱스가 `조건 탐색`에는 도움을 줄 수 있어도, **반환할 컬럼** 때문에 결국 heap tuple을 다시 읽어야 할 수 있다.
2. 필요한 컬럼이 모두 인덱스 안에 있어도, PostgreSQL은 **MVCC 가시성 확인** 때문에 heap을 다시 볼 수 있다.

즉 실무에서 우리가 원하는 것은 단순한 `Index Scan`이 아니라, 가능한 한 **Index Only Scan**에 가깝게 만드는 것이다.

그런데 여기서 흔한 오해가 바로 나온다.

- INCLUDE 컬럼만 넣으면 자동으로 index only scan이 된다.
- covering index는 읽기 성능만 좋아지고 부작용은 작다.
- index only scan은 MySQL의 covering index와 비슷하게 생각하면 된다.
- 인덱스만 잘 설계하면 vacuum 상태는 크게 중요하지 않다.
- `EXPLAIN`에 index only scan이 한 번 찍혔으면 그 쿼리는 끝난 것이다.

실무에서는 이 다섯 가지가 전부 위험한 단순화다.

PostgreSQL의 index only scan은 단순히 컬럼을 더 얹는 기술이 아니다. **인덱스 구조, 반환 컬럼, heap page 가시성, autovacuum, 업데이트 패턴, 쓰기 비용**이 한 번에 엮인 운영 주제다.

오늘 글은 그 연결을 실무 기준으로 정리한다. 목표는 아래 질문에 답하는 것이다.

- PostgreSQL에서 index only scan은 정확히 어떤 조건에서 가능한가?
- 왜 INCLUDE를 넣었는데도 heap fetch가 계속 발생하는가?
- visibility map은 성능과 어떻게 연결되는가?
- covering index가 읽기를 빠르게 만들면서도 쓰기를 망칠 수 있는 이유는 무엇인가?
- composite key, INCLUDE, partial index는 어떤 기준으로 조합해야 하는가?
- API 조회, 목록 페이지, 배치 스캔에서 실무적으로 어떻게 적용해야 하는가?
- 흔한 실수와 점검 체크리스트는 무엇인가?

이 글의 핵심 메시지는 한 줄로 요약할 수 있다.

> **PostgreSQL에서 covering index 최적화는 “컬럼을 더 넣는 일”이 아니라, heap fetch를 얼마나 구조적으로 줄일 수 있는지 설계하는 일이다.**

---

## 먼저 큰 그림: `Index Scan`과 `Index Only Scan`은 비슷해 보여도 비용 구조가 다르다

실행 계획을 보다 보면 둘 다 얼핏 비슷해 보인다.

- `Index Scan using ...`
- `Index Only Scan using ...`

둘 다 인덱스를 사용하니 같은 부류처럼 느껴진다. 하지만 비용 구조는 꽤 다르다.

### `Index Scan`

`Index Scan`은 보통 다음 순서로 움직인다.

1. 인덱스에서 조건에 맞는 TID(tuple 위치)를 찾는다.
2. 그 TID를 따라 heap page로 간다.
3. heap tuple을 읽는다.
4. 반환 컬럼을 모으고 MVCC 가시성을 확인한다.

즉 인덱스는 "어디 있는지"를 알려주고, 실제 row 확인은 heap이 담당한다.

### `Index Only Scan`

`Index Only Scan`은 이상적으로는 이렇게 끝난다.

1. 인덱스에서 조건에 맞는 항목을 찾는다.
2. 필요한 반환 컬럼도 인덱스에서 읽는다.
3. heap page를 다시 열지 않거나, 아주 제한적으로만 연다.

중요한 차이는 이것이다.

- `Index Scan`은 **매칭된 row 수만큼 heap 접근 비용**이 따라붙기 쉽다.
- `Index Only Scan`은 **heap 접근을 크게 줄일 수 있을 때** 진가가 나온다.

특히 랜덤 I/O가 비싸거나, 캐시 적중률이 애매하거나, 페이지네이션 API가 자주 호출되는 환경에서는 이 차이가 체감 성능을 크게 바꾼다.

### 그런데 PostgreSQL에서는 이름이 `Index Only Scan`이어도 heap을 완전히 안 볼 수는 없다

여기서 PostgreSQL 특유의 포인트가 나온다.

MySQL 경험이 강한 개발자는 often "covering index면 테이블 안 본다"고 단순화한다. PostgreSQL은 조금 다르다. PostgreSQL은 MVCC 때문에 row visibility를 판단해야 하고, 그 판단이 **visibility map**으로 충분히 보장되지 않으면 heap을 다시 볼 수 있다.

즉 이름은 `Index Only Scan`이어도 실제 성능은 아래에 따라 달라진다.

- 필요한 컬럼이 인덱스에 모두 있는가
- heap page가 all-visible 상태인가
- 업데이트가 자주 일어나 visibility map이 자주 깨지는가
- autovacuum이 적절히 돌아가고 있는가

그래서 실무에서는 실행 계획의 node 이름보다 **Heap Fetches 숫자**를 같이 봐야 한다.

---

## 핵심 개념 1: Index Only Scan의 첫 번째 조건은 “필요한 컬럼이 인덱스 안에 있어야 한다”이다

가장 기본 조건부터 보자.

예를 들어 주문 목록 API가 아래처럼 생겼다고 하자.

```sql
SELECT id, created_at, total_amount
FROM orders
WHERE tenant_id = 42
  AND status = 'PAID'
ORDER BY created_at DESC
LIMIT 50;
```

이 쿼리를 빠르게 만들기 위해 보통 먼저 이런 인덱스를 만든다.

```sql
CREATE INDEX idx_orders_tenant_status_created_at
ON orders (tenant_id, status, created_at DESC);
```

이 인덱스는 분명 도움이 된다.

- `tenant_id`, `status` 필터에 맞는 범위를 좁히고
- `created_at DESC` 정렬까지 지원할 수 있다.

하지만 이 인덱스만으로는 `SELECT id, created_at, total_amount`를 모두 반환할 수 없다. `id`, `total_amount`가 인덱스 키에 없기 때문이다. 그러면 PostgreSQL은 결국 heap에 가서 row를 다시 읽어야 한다.

이때 선택지는 세 가지다.

### 선택지 1: 그냥 heap을 읽는다

가장 단순하다. 인덱스는 탐색용으로만 쓰고 반환 컬럼은 heap에서 읽는다.

장점:

- 인덱스 크기가 작다.
- 쓰기 비용 증가가 제한적이다.

단점:

- 매칭 row 수가 많을수록 heap 접근이 부담된다.
- 목록 API나 핫한 조회 API에서 랜덤 heap fetch 비용이 누적된다.

### 선택지 2: 반환 컬럼을 key part에 포함한다

```sql
CREATE INDEX idx_orders_tenant_status_created_at_id_amount
ON orders (tenant_id, status, created_at DESC, id, total_amount);
```

가능하긴 하지만 주의해야 한다.

- key part가 길어지면 인덱스 정렬 구조가 더 무거워진다.
- 실제 탐색/정렬에 필요하지 않은 컬럼까지 key ordering에 들어간다.
- 불필요하게 인덱스 팬아웃과 크기를 키울 수 있다.

### 선택지 3: `INCLUDE`를 사용한다

```sql
CREATE INDEX idx_orders_tenant_status_created_at_cover
ON orders (tenant_id, status, created_at DESC)
INCLUDE (id, total_amount);
```

이 방식이 PostgreSQL에서 흔히 말하는 covering index 설계의 핵심이다.

- 탐색과 정렬 기준은 key part에 둔다.
- 단순 반환용 컬럼은 INCLUDE에 둔다.

즉 key는 "찾기 위한 정보", INCLUDE는 "돌려주기 위한 정보"로 역할을 분리한다.

이 구분이 중요하다. **탐색 조건이 아닌 컬럼을 무작정 key 뒤에 붙이는 것보다, INCLUDE로 분리하는 편이 의도를 더 정확히 표현**하기 때문이다.

---

## 핵심 개념 2: INCLUDE는 만능이 아니다 — “반환 컬럼 충족”만 해결하고 “가시성 확인”은 해결하지 않는다

INCLUDE를 넣으면 많은 개발자가 이제 끝났다고 생각한다. 하지만 PostgreSQL에서는 절반만 끝난 것이다.

예를 들어 아래처럼 인덱스를 만들었다고 하자.

```sql
CREATE INDEX idx_orders_tenant_status_created_at_cover
ON orders (tenant_id, status, created_at DESC)
INCLUDE (id, total_amount, currency);
```

그리고 조회는 이렇다.

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, created_at, total_amount, currency
FROM orders
WHERE tenant_id = 42
  AND status = 'PAID'
ORDER BY created_at DESC
LIMIT 50;
```

실행 계획에 `Index Only Scan`이 찍힐 수 있다. 그런데 실제 성능이 기대보다 덜 좋은 경우가 있다. 왜냐하면 PostgreSQL은 아직도 다음 질문을 해결해야 하기 때문이다.

> 이 인덱스 항목이 가리키는 heap tuple이 지금 이 트랜잭션에서 정말 보이는 row가 맞는가?

이 가시성 확인을 매번 heap에서 다시 하면 index only의 장점이 사라진다. 그래서 PostgreSQL은 heap page 단위의 보조 정보인 **visibility map**을 활용한다.

즉 INCLUDE는 **컬럼 부족 문제**를 해결하지만, visibility map은 **heap 재방문 최소화 문제**를 해결한다. 둘은 별개다.

실무에서 이걸 놓치면 이런 오판이 생긴다.

- INCLUDE를 넣었는데 왜 빨라지지 않았지?
- `Index Only Scan`인데 왜 버퍼 읽기가 아직 많지?
- 같은 인덱스인데 운영은 느리고 스테이징은 빠르지?

대부분 답은 visibility map과 업데이트 패턴 쪽에 있다.

---

## 핵심 개념 3: Visibility Map을 이해해야 Heap Fetch가 왜 생기는지 보인다

PostgreSQL은 heap page마다 “이 페이지의 row들이 모든 트랜잭션에 대해 보이는가?”를 빠르게 판단하기 위해 visibility map을 유지한다.

여기서 중요한 플래그는 대표적으로 `all-visible`이다.

- 어떤 heap page가 all-visible이면
- 그 페이지에 있는 tuple들은 현재 visibility 체크를 위해 heap을 다시 열 필요가 적다.
- 그 결과 index only scan이 더 순수하게 작동할 수 있다.

반대로 어떤 page가 all-visible이 아니면 PostgreSQL은 안전하게 heap을 다시 확인해야 한다.

### 왜 all-visible이 깨질까?

아주 단순하다. 해당 페이지의 row에 변경이 생기면 된다.

- INSERT
- UPDATE
- DELETE
- HOT update 여부와 관계없는 가시성 변화

즉 **쓰기 많은 테이블은 visibility map이 자주 흔들린다.**

### 누가 all-visible을 다시 세워주나?

주로 vacuum, 특히 autovacuum이 큰 역할을 한다.

즉 읽기 최적화 주제처럼 보이는 index only scan은 결국 autovacuum 건강 상태와 연결된다.

이 지점이 실무에서 정말 중요하다.

- 조회 API가 느려졌는데 원인이 인덱스 설계가 아니라 vacuum 지연일 수 있다.
- INCLUDE를 잘 설계해도 업데이트가 잦으면 heap fetch가 다시 늘어난다.
- 읽기 성능 개선을 위해 만든 covering index가 실제로는 "변경이 드문 조회 표면"에 더 잘 맞는다.

### 실행 계획에서 뭘 봐야 하나

가장 중요한 지표 중 하나는 `Heap Fetches`다.

예를 들어 아래처럼 나온다면:

```text
Index Only Scan using idx_orders_tenant_status_created_at_cover on orders
  Index Cond: ((tenant_id = 42) AND (status = 'PAID'))
  Heap Fetches: 0
```

이건 꽤 이상적인 상태다.

반대로:

```text
Index Only Scan using idx_orders_tenant_status_created_at_cover on orders
  Index Cond: ((tenant_id = 42) AND (status = 'PAID'))
  Heap Fetches: 18743
```

이건 이름은 index only scan이어도 실제로는 heap을 상당히 다시 보고 있다는 뜻이다.

실무적으로는 이렇게 읽으면 된다.

- `Heap Fetches`가 매우 낮다 → covering index + visibility 상태가 잘 맞는다.
- `Heap Fetches`가 높다 → 인덱스 자체보다 **가시성/업데이트 패턴/vacuum 주기**를 의심한다.

---

## 핵심 개념 4: Covering Index 설계의 본질은 “탐색 컬럼”과 “반환 컬럼”을 분리하는 것이다

실무에서 인덱스 설계를 망치는 가장 흔한 습관은 "필요한 컬럼 전부 key 뒤에 붙이기"다.

하지만 index only scan 최적화에서는 다음 분리가 중요하다.

### 1) 탐색 컬럼(search keys)

이 컬럼들은 아래 역할을 한다.

- `WHERE` 필터 선택도 줄이기
- `ORDER BY` 지원
- 조인/범위 탐색 구조 결정

예:

- `tenant_id`
- `status`
- `created_at`

### 2) 반환 컬럼(payload / projection columns)

이 컬럼들은 결과를 반환하기 위해 필요하지만, 인덱스 탐색 순서에는 영향을 줄 필요가 없다.

예:

- `id`
- `total_amount`
- `currency`
- `title`
- `author_name`

### 좋은 기본 원칙

- 필터/정렬에 필요한 최소 컬럼만 key part에 둔다.
- 결과 반환용이지만 탐색에는 불필요한 컬럼은 `INCLUDE`로 뺀다.
- 큰 텍스트, 자주 바뀌는 컬럼은 신중하게 다룬다.

예를 들어 게시글 목록 API라면:

```sql
SELECT id, slug, title, published_at, author_id
FROM posts
WHERE site_id = 7
  AND status = 'PUBLISHED'
ORDER BY published_at DESC
LIMIT 20;
```

이런 인덱스가 후보가 된다.

```sql
CREATE INDEX idx_posts_site_status_published_at
ON posts (site_id, status, published_at DESC)
INCLUDE (id, slug, title, author_id);
```

이 설계의 장점은 명확하다.

- 필터와 정렬은 key가 담당한다.
- 목록 화면에 필요한 컬럼은 heap 재방문 없이 가져올 기회를 만든다.

다만 여기서 `title`이 매우 길고 자주 수정되는 컬럼이라면 얘기가 달라질 수 있다. covering index는 읽기만 보지 말고 **인덱스 크기와 업데이트 비용**을 같이 봐야 한다.

---

## 핵심 개념 5: 모든 조회를 Covering Index로 만들려는 욕심이 오히려 시스템을 무겁게 만든다

읽기 병목을 발견하면 많은 팀이 빠지기 쉬운 함정이 있다.

> 자주 쓰는 SELECT마다 필요한 컬럼을 전부 INCLUDE 해버리자.

이 접근은 초기에는 꽤 매력적으로 보인다. 몇 개 API가 눈에 띄게 빨라질 수 있다. 하지만 시간이 지나면 대개 아래 문제가 생긴다.

### 문제 1: 인덱스 크기 급증

INCLUDE 컬럼도 인덱스 저장공간을 차지한다. 반환 컬럼을 많이 넣을수록:

- 인덱스 파일이 커지고
- 메모리 캐시 적중률이 떨어지고
- 스캔해야 하는 인덱스 페이지 수가 늘 수 있다.

즉 heap 접근을 줄이려다 인덱스 자체가 둔해질 수 있다.

### 문제 2: 쓰기 비용 증가

INSERT/UPDATE 시 인덱스도 같이 관리해야 한다. 특히 INCLUDE 컬럼이 업데이트되면:

- 인덱스 유지 비용이 늘고
- WAL 양이 증가하고
- vacuum 부담도 간접적으로 커진다.

### 문제 3: HOT 기회 감소

PostgreSQL의 HOT update는 인덱스를 건드리지 않고 heap 내부에서만 업데이트를 처리할 기회를 준다. 그런데 자주 바뀌는 컬럼이 인덱스 key나 INCLUDE에 들어가면 이 기회가 줄어든다.

즉 covering index는 읽기만의 문제가 아니라, **쓰기 경로와 HOT 효율을 희생할 가치가 있는지**를 같이 따져야 한다.

### 문제 4: 인덱스 스프롤(index sprawl)

API별로 각자 covering index를 만들다 보면 비슷한 인덱스가 여러 개 생긴다.

- `(tenant_id, status, created_at)` + `INCLUDE (id, total_amount)`
- `(tenant_id, status, created_at)` + `INCLUDE (id, total_amount, currency)`
- `(tenant_id, status, created_at)` + `INCLUDE (id, customer_id, channel)`

이렇게 되면 읽기 최적화보다 관리 비용이 더 커진다. 운영자는 어느 인덱스가 실제로 쓰이는지 추적해야 하고, 개발자는 새 API마다 또 인덱스를 추가하는 습관이 생긴다.

실무에서 더 나은 질문은 이것이다.

> 정말 모든 조회를 완전한 covering으로 만들 필요가 있는가, 아니면 상위 1~2개의 핫한 read path만 집중적으로 최적화하면 되는가?

대부분 후자가 맞다.

---

## 실무 예시 1: SaaS 주문 목록 API를 Index Only Scan 친화적으로 바꾸기

가정:

- 멀티테넌트 SaaS
- 운영자가 주문 목록을 자주 조회
- 최신 주문 50개 조회가 매우 빈번
- 상태값과 시간순 정렬이 핵심

기존 쿼리:

```sql
SELECT id, order_no, customer_id, total_amount, currency, created_at
FROM orders
WHERE tenant_id = $1
  AND status = 'PAID'
ORDER BY created_at DESC
LIMIT 50;
```

기존 인덱스:

```sql
CREATE INDEX idx_orders_tenant_status_created_at
ON orders (tenant_id, status, created_at DESC);
```

이 상태의 문제:

- 필터와 정렬은 빠를 수 있다.
- 하지만 결과 반환에 필요한 `id`, `order_no`, `customer_id`, `total_amount`, `currency`를 heap에서 읽는다.
- 최신 50건이라 row 수는 작아 보여도, 호출 빈도가 높으면 heap fetch가 누적된다.

개선 후보:

```sql
CREATE INDEX CONCURRENTLY idx_orders_tenant_status_created_at_cover
ON orders (tenant_id, status, created_at DESC)
INCLUDE (id, order_no, customer_id, total_amount, currency);
```

### 적용 전 확인할 것

1. `currency`는 자주 바뀌는가? 거의 안 바뀐다면 괜찮다.
2. `order_no` 길이가 과도하게 큰가? 너무 크면 INCLUDE 이득이 줄 수 있다.
3. 이 API가 충분히 자주 호출되는가? 드문 관리자 화면이면 비용 대비 효과가 작다.
4. `orders`가 초고빈도 업데이트 테이블인가? 그렇다면 heap fetch 감소 효과가 생각보다 약할 수 있다.

### 기대 효과

- 동일한 필터/정렬 유지
- 반환 컬럼을 인덱스에서 바로 공급할 기회 확보
- all-visible page 비율이 높은 구간에서는 heap 접근 크게 감소

### 기대를 낮춰야 하는 경우

- 실시간으로 상태 전이가 많다.
- 결제 후 후속 업데이트가 여러 번 발생한다.
- 최근 주문이 있는 page들이 자주 수정된다.

이 경우 최신 50건 조회는 의외로 all-visible 비율이 낮을 수 있다. 즉 “최신 데이터 조회”는 business-wise 중요하지만, storage-wise로는 index only scan 친화적이지 않을 수 있다.

이럴 때는 오히려 다음을 함께 고려해야 한다.

- 상태 이력 테이블 분리
- 자주 바뀌는 컬럼과 읽기 전용 컬럼 분리
- 운영 대시보드용 read model/materialized summary

즉 covering index만으로 모든 문제를 해결하려고 하면 안 된다.

---

## 실무 예시 2: 이벤트 로그 탐색에서는 왜 Index Only Scan보다 BRIN/파티셔닝/요약 테이블이 더 나을 수도 있는가

이벤트 로그 테이블을 생각해 보자.

```sql
SELECT id, event_type, user_id, created_at
FROM user_events
WHERE tenant_id = 42
  AND created_at >= now() - interval '1 day'
ORDER BY created_at DESC
LIMIT 100;
```

겉으로 보면 covering index 후보처럼 보인다.

```sql
CREATE INDEX idx_user_events_tenant_created_at
ON user_events (tenant_id, created_at DESC)
INCLUDE (id, event_type, user_id);
```

하지만 이벤트 로그는 보통 다음 특징이 있다.

- INSERT가 매우 많다.
- 최신 구간 조회가 많다.
- 최근 page는 all-visible 상태가 되기 전까지 계속 흔들린다.
- retention, 파티셔닝, cold storage 전략이 더 중요하다.

즉 이 테이블은 index only scan의 교과서적 대상처럼 보여도, 실제로는 **최신 구간 hot write 패턴** 때문에 heap fetch 절감 폭이 제한될 수 있다.

이런 경우 더 실용적인 질문은 다음일 수 있다.

- 이 조회는 정말 row-level 원문이 필요한가?
- 최근 1일 요약이 목적이면 summary table이 더 낫지 않은가?
- 시간순 append-only라면 BRIN이 더 경제적이지 않은가?
- 파티셔닝 후 최근 파티션만 집중적으로 보는 편이 낫지 않은가?

즉 index only scan은 강력하지만, **append-heavy observability/workload의 만능 답은 아니다.**

---

## 실무 예시 3: 상품 목록 페이지에서 Partial Index + INCLUDE가 좋은 이유

다음 같은 전자상거래 쿼리를 보자.

```sql
SELECT id, slug, name, price, thumbnail_url, published_at
FROM products
WHERE tenant_id = 9
  AND status = 'PUBLISHED'
  AND deleted_at IS NULL
ORDER BY published_at DESC
LIMIT 24;
```

전체 상품 중 실제로 목록에 노출되는 것은 `PUBLISHED` + `deleted_at IS NULL` 뿐이라고 하자. 그렇다면 전체 row를 다 포괄하는 인덱스보다 partial index가 더 맞을 수 있다.

```sql
CREATE INDEX idx_products_listing_cover
ON products (tenant_id, published_at DESC)
INCLUDE (id, slug, name, price, thumbnail_url)
WHERE status = 'PUBLISHED' AND deleted_at IS NULL;
```

이 설계의 장점:

- 인덱스 대상 row 수 자체를 줄인다.
- 자주 쓰는 목록 API에 매우 정확히 맞는다.
- 불필요한 상태값까지 인덱싱하지 않아 크기와 유지 비용을 줄일 수 있다.

이건 covering index 설계에서 자주 놓치는 포인트다.

> **모든 row를 더 넓게 커버하는 것보다, 필요한 row만 더 날카롭게 커버하는 편이 낫다.**

즉 partial index는 covering index의 경쟁자가 아니라, 오히려 **인덱스를 작게 유지하면서 heap fetch 감소 효과를 확보하는 좋은 파트너**다.

다만 주의점도 있다.

- 쿼리가 partial predicate와 정확히 맞아야 planner가 잘 활용한다.
- 애플리케이션 쿼리 스타일이 흔들리면 활용률이 떨어진다.
- `status` 전이가 매우 잦다면 인덱스 유지 비용이 다시 커질 수 있다.

---

## 핵심 개념 6: 최신 데이터 조회는 비즈니스적으로 중요하지만, Storage 관점에서는 Index Only Scan에 불리할 수 있다

이 부분은 중급 개발자 이상에게 특히 중요하다.

많은 팀이 가장 핫한 API를 최적화하려고 한다. 당연히 맞는 방향이다. 그런데 핫한 API의 대상이 항상 index only scan에 잘 맞는 건 아니다.

예를 들어:

- 최근 10분 주문
- 방금 생성된 알림
- 현재 처리 중인 작업 큐
- 최신 에러 로그 100건

이런 쿼리는 비즈니스적으로 매우 중요하지만, storage 관점에서는 다음 특징이 있다.

- 최근 heap page에 집중된다.
- 해당 page들이 아직 all-visible이 아닐 가능성이 높다.
- 계속 새로운 쓰기/수정이 들어온다.

즉 covering index를 만들어도 heap fetch가 줄어드는 폭이 기대보다 작을 수 있다.

반대로 index only scan이 특히 잘 맞는 표면은 이런 경우다.

- 하루 이상 지난 정산 완료 데이터 조회
- 상태 전이가 끝난 이력성 데이터
- 게시 후 거의 수정되지 않는 콘텐츠 목록
- append 후 거의 immutable한 아카이브 테이블

실무에서 이 구분이 중요하다. 어떤 팀은 최신 활동 피드를 index only scan으로 밀어붙이다가 실망하고, 어떤 팀은 변경이 거의 없는 목록 화면을 커버링해서 큰 이득을 얻는다.

즉 **query frequency만 보지 말고, row mutability까지 같이 봐야 한다.**

---

## 핵심 개념 7: `EXPLAIN (ANALYZE, BUFFERS)`에서 꼭 같이 봐야 할 것들

covering index 검토에서 `EXPLAIN`을 대충 보면 쉽게 착시가 생긴다. 아래 항목들을 같이 봐야 한다.

### 1) Node type

- `Index Scan`
- `Index Only Scan`
- `Bitmap Heap Scan`

이건 시작점일 뿐이다.

### 2) `Heap Fetches`

index only scan의 실질적인 품질을 보여준다.

- 낮을수록 좋다.
- 높으면 visibility map, update pattern, vacuum 상태를 봐야 한다.

### 3) `Buffers`

```sql
EXPLAIN (ANALYZE, BUFFERS)
...
```

여기서 shared hit/read가 어떻게 분포되는지 보면:

- 인덱스 쪽 부담인지
- heap 재방문이 많은지
- 캐시 효과 덕분에 가려져 있는지

를 더 정확히 볼 수 있다.

### 4) actual rows vs LIMIT

`LIMIT 20`이어도 planner가 조건을 좁히기 위해 생각보다 많은 index entry를 훑을 수 있다. 특히 정렬/필터 조합이 깔끔하지 않으면 index only scan이더라도 기대보다 많은 인덱스 페이지를 읽을 수 있다.

### 5) 실행 시점 분산

한 번 빠르게 나왔다고 끝내면 안 된다. 같은 쿼리를 여러 시점에 봐야 한다.

- 배치 직후
- autovacuum 직후
- 쓰기 피크 시간대
- 트래픽이 비교적 잔잔한 시간대

같은 쿼리인데 heap fetch가 시간대별로 다르면, 인덱스 문법보다 운영 패턴 영향이 크다는 뜻이다.

---

## 핵심 개념 8: PostgreSQL B-Tree에서 key 컬럼과 INCLUDE 컬럼은 역할이 다르다

`INCLUDE`를 이해할 때 자주 생기는 오해가 있다.

> INCLUDE도 인덱스에 들어가니까, key에 붙이는 것과 거의 같지 않나?

비슷해 보이지만 역할은 다르다.

### key 컬럼이 하는 일

- 탐색 범위를 정한다.
- 정렬 순서를 만든다.
- 범위 조건과 equality 조건의 효율을 좌우한다.
- unique index라면 유일성 판단의 기준이 된다.

### INCLUDE 컬럼이 하는 일

- 결과 반환용 payload를 제공한다.
- 탐색 순서와 범위 결정에는 직접 관여하지 않는다.
- 유일성 판단의 기준이 아니다.

예를 들어 아래 두 인덱스는 완전히 다른 의미를 가진다.

```sql
CREATE UNIQUE INDEX uq_users_email
ON users (tenant_id, email);
```

```sql
CREATE UNIQUE INDEX uq_users_email_cover
ON users (tenant_id, email)
INCLUDE (name, status);
```

두 번째 인덱스에서 `name`, `status`는 반환에는 도움이 될 수 있어도 **unique 의미를 바꾸지 않는다.**

이 차이를 모르고 설계하면 다음 같은 실수를 한다.

- 정렬에 필요한 컬럼을 INCLUDE에 넣고 끝냈다고 착각
- 범위 조건에 필요한 컬럼을 INCLUDE에 넣고 planner가 알아서 활용할 거라 기대
- unique key의 의미를 넓히려다가 실제로는 그대로인 상태를 놓침

즉 INCLUDE는 "인덱스에 저장은 하지만 탐색 규칙을 정의하지는 않는 컬럼"이라고 이해하는 편이 안전하다.

### 그래서 composite key 설계는 여전히 별도 사고가 필요하다

아래 쿼리를 보자.

```sql
SELECT id, amount, created_at
FROM payments
WHERE tenant_id = 10
  AND status = 'SETTLED'
  AND created_at >= date_trunc('month', now())
ORDER BY created_at DESC
LIMIT 100;
```

이 쿼리에서는 보통 아래처럼 생각해야 한다.

1. `tenant_id`, `status`는 equality filter
2. `created_at`은 range + order 역할
3. `id`, `amount`는 projection 역할

즉 자연스러운 구조는 이런 식이다.

```sql
CREATE INDEX idx_payments_listing
ON payments (tenant_id, status, created_at DESC)
INCLUDE (id, amount);
```

이 논리를 건너뛰고 `created_at`을 INCLUDE에 두면 정렬/범위 효율이 무너진다. 반대로 `amount`를 key에 올리면 탐색에는 별 이득이 없는데 인덱스만 더 무거워진다.

---

## 핵심 개념 9: “Heap Fetches가 왜 높은가”를 볼 때는 쿼리 문제와 데이터 문제를 분리해야 한다

실행 계획을 읽을 때 많은 팀이 자꾸 SQL 문법 쪽만 본다. 하지만 heap fetch가 높을 때는 원인을 두 부류로 나눠서 생각해야 한다.

### 부류 1: 쿼리/인덱스 설계 문제

- 반환 컬럼이 인덱스에 없다.
- 정렬 컬럼이 key에 없다.
- partial predicate와 실제 쿼리가 잘 안 맞는다.
- leading column 순서가 잘못됐다.

이 경우에는 DDL을 바꾸는 것이 직접적인 해결이다.

### 부류 2: 데이터/운영 패턴 문제

- 최근 row가 계속 수정된다.
- autovacuum이 늦게 돈다.
- 긴 트랜잭션 때문에 all-visible 전환이 늦다.
- 쿼리가 읽는 구간이 늘 hot page에 집중된다.

이 경우에는 인덱스를 하나 더 만드는 것으로 해결되지 않는다.

### 분리 진단 질문

1. projection을 최소화했는가?
2. 필요한 컬럼이 인덱스 안에 있는가?
3. 그럼에도 heap fetch가 높은가?
4. 그렇다면 최근 page 수정 패턴과 vacuum 상태는 어떤가?

이 순서가 중요하다. 1~2를 건너뛰고 운영 문제를 논하면 산만해지고, 3~4를 건너뛰고 인덱스만 늘리면 과잉 DDL이 된다.

---

## 실무 예시 5: Keyset Pagination과 Covering Index는 궁합이 아주 좋다

목록 API 최적화에서 OFFSET 기반 페이지네이션은 흔히 문제를 만든다.

```sql
SELECT id, title, published_at
FROM posts
WHERE site_id = 1
  AND status = 'PUBLISHED'
ORDER BY published_at DESC, id DESC
LIMIT 20 OFFSET 10000;
```

이 쿼리는 covering index가 있어도 뒤 페이지로 갈수록 비용이 커질 수 있다. 왜냐하면 planner는 여전히 앞선 많은 row를 건너뛰어야 하기 때문이다.

이럴 때 더 좋은 방식은 keyset pagination이다.

```sql
SELECT id, title, published_at
FROM posts
WHERE site_id = 1
  AND status = 'PUBLISHED'
  AND (published_at, id) < ($last_published_at, $last_id)
ORDER BY published_at DESC, id DESC
LIMIT 20;
```

이 쿼리에 맞는 인덱스:

```sql
CREATE INDEX idx_posts_published_seek
ON posts (site_id, status, published_at DESC, id DESC)
INCLUDE (title);
```

이 조합의 장점은 크다.

- 정렬 순서와 탐색 시작점이 인덱스와 정확히 맞는다.
- OFFSET으로 앞쪽 row를 버리지 않아도 된다.
- 필요한 컬럼이 적으면 heap fetch까지 줄일 기회가 생긴다.

즉 covering index는 단독으로 보는 것보다 **페이지네이션 전략과 함께** 볼 때 효과가 더 커진다.

실무 감각으로는 이렇다.

- OFFSET이 큰 목록 API → index only보다 pagination 구조부터 의심
- keyset 기반 목록 API → covering index 투자 가치가 훨씬 커짐

---

## 실무 예시 6: 관리자 검색 화면은 Covering Index보다 “조회 모드 분리”가 더 낫다

관리자 화면은 욕심이 많다.

- 조건이 많다
- 정렬 기준이 자주 바뀐다
- 내보내기(export)까지 요구된다
- 목록 화면과 상세 팝업이 한 쿼리로 엮인다

이런 화면에 대해 covering index 하나로 모든 요구를 해결하려고 하면 거의 항상 실패한다.

예를 들어 고객 검색 화면에서:

```sql
SELECT id, email, name, status, country, last_login_at, created_at, note
FROM customers
WHERE tenant_id = $1
  AND status = ANY($2)
  AND country = COALESCE($3, country)
ORDER BY last_login_at DESC
LIMIT 50;
```

이 화면은 운영 중 곧 이런 요구로 번진다.

- 이번에는 `created_at` 정렬도 필요
- 국가 필터 대신 세그먼트 필터 추가
- `note`도 목록에서 미리 보여달라
- CSV 다운로드는 LIMIT 없이 필요

이걸 covering index 한두 개로 버티려 하면 인덱스만 비대해진다. 이런 화면은 보통 다음처럼 분리하는 편이 낫다.

1. 기본 목록용 빠른 경로: 핵심 정렬/필터 + 작은 projection
2. 상세 보기 경로: PK lookup 허용
3. 대량 export 경로: 배치/비동기/파일 생성

즉 covering index는 **정해진 read path**에는 강하지만, 검색 표면이 계속 변하는 도구형 UI에는 한계가 있다.

---

## 진단 SQL: 어떤 쿼리/테이블이 Covering Index 후보인지 찾는 법

막연히 인덱스를 추가하지 말고 후보를 찾는 습관이 중요하다.

### 1) 자주 읽히는 테이블 확인

```sql
SELECT
  relname,
  seq_scan,
  idx_scan,
  n_tup_ins,
  n_tup_upd,
  n_tup_del,
  n_live_tup
FROM pg_stat_user_tables
ORDER BY idx_scan DESC
LIMIT 20;
```

여기서 볼 포인트:

- `idx_scan`이 높다 → 이미 인덱스 기반 조회가 많다.
- `n_tup_upd`가 낮다 → immutable 성향이면 index only scan 친화적일 수 있다.
- `n_tup_upd`가 매우 높다 → covering index 이득이 제한될 수 있다.

### 2) 인덱스 사용량과 크기 확인

```sql
SELECT
  s.relname AS table_name,
  s.indexrelname AS index_name,
  s.idx_scan,
  pg_size_pretty(pg_relation_size(s.indexrelid)) AS index_size
FROM pg_stat_user_indexes s
ORDER BY s.idx_scan DESC
LIMIT 30;
```

이 결과로 다음을 같이 본다.

- 정말 자주 쓰이는 인덱스인가
- 너무 큰데 효익이 애매한 인덱스는 없는가
- 비슷한 역할을 하는 인덱스가 여러 개인가

### 3) vacuum 상태 확인

```sql
SELECT
  relname,
  last_vacuum,
  last_autovacuum,
  last_analyze,
  last_autoanalyze,
  n_dead_tup
FROM pg_stat_user_tables
WHERE relname IN ('orders', 'posts', 'products');
```

covering index 후보인데도 효과가 약하면 이 정보를 같이 본다. 읽기 성능 문제인데 vacuum 타이밍이 같이 나온다는 점이 PostgreSQL 특유의 현실이다.

---

## 패턴별 추천: 어떤 워크로드에 Covering Index가 특히 잘 맞는가

### 잘 맞는 패턴

#### 1) 콘텐츠/카탈로그 목록

- 게시글 목록
- 상품 목록
- 문서 목록
- 거의 수정되지 않는 공개 콘텐츠

이런 표면은 projection이 비교적 안정적이고, status 종료 후 row가 잘 안 바뀌는 경우가 많아 좋은 후보다.

#### 2) 정산/이력/리포트 조회

- settled payments
- closed invoices
- immutable audit history

최신 실시간 데이터보다 과거 안정 구간이 많아 all-visible 효과를 얻기 쉽다.

#### 3) 멀티테넌트 운영자 목록 화면

- `tenant_id + status + created_at DESC`
- 소수 컬럼만 보여주는 목록
- LIMIT가 명확한 탐색형 UI

이런 쿼리는 composite key + INCLUDE가 깔끔하게 먹힌다.

### 신중해야 하는 패턴

#### 1) 상태 전이가 매우 잦은 큐/잡 테이블

읽기 패턴이 뚜렷해 보여도 write churn이 커서 이득이 줄 수 있다.

#### 2) 긴 text/JSON payload를 자주 포함하는 화면

projection 자체를 줄이는 것이 우선이다.

#### 3) ad-hoc 검색

운영자 검색 도구처럼 필터/정렬이 계속 바뀌면 covering보다 별도 검색 인프라나 조회 모드 분리가 나을 수 있다.

---

## 트레이드오프를 숫자로 보는 사고법

인덱스 추가 여부를 감으로만 결정하면 팀마다 의견 싸움이 된다. 다음처럼 숫자 기준으로 생각하면 훨씬 선명해진다.

### 질문 1: 이 쿼리는 하루에 몇 번 호출되는가?

- 하루 수십 번이면 큰 인덱스를 추가할 이유가 약하다.
- 하루 수십만 번이면 작은 heap fetch 절감도 누적 가치가 크다.

### 질문 2: 한 번의 호출에서 몇 row를 읽는가?

- 항상 LIMIT 20~100 수준이면 covering index 효익 계산이 쉽다.
- 수천~수만 row를 읽는다면 index only scan보다 다른 접근법이 나을 수 있다.

### 질문 3: row는 얼마나 자주 변하는가?

- 생성 후 거의 불변 → 후보 강함
- 몇 분/몇 시간 동안 계속 업데이트 → 후보 약함

### 질문 4: 반환 컬럼이 얼마나 큰가?

- 짧은 scalar 값 → INCLUDE 적합
- 긴 text/json → projection 축소 우선

### 질문 5: 기존 인덱스를 대체할 수 있는가?

새 covering index가 기존 일반 인덱스를 대체할 수 있다면 비용이 생각보다 크지 않을 수 있다. 반대로 중복 인덱스를 계속 쌓는다면 유지비가 눈덩이처럼 불어난다.

---

## 자주 묻는 판단 포인트

### Q1. PK 조회에도 covering index가 필요한가?

대부분 아니다. PK 단건 조회는 heap 한 번 읽는 비용이 크지 않은 경우가 많다. covering index는 보통 **목록형 반복 조회**에서 가치가 크다.

### Q2. INCLUDE에 컬럼을 많이 넣으면 planner가 더 잘 쓰나?

아니다. planner는 "반환 컬럼 충족"에는 도움을 받지만, 인덱스가 지나치게 커지면 오히려 비용이 올라갈 수 있다.

### Q3. 최근 데이터가 느린데 vacuum을 세게 돌리면 되나?

항상 그렇지는 않다. 최근 데이터가 본질적으로 계속 변한다면 all-visible이 안정적으로 유지되기 어렵다. vacuum 튜닝은 중요하지만, **테이블 성격 자체**를 바꾸지는 못한다.

### Q4. covering index와 materialized view 중 무엇이 낫나?

실시간 정합성과 간단한 목록 최적화가 중요하면 covering index가 단순하다. 반대로 쿼리 조합이 복잡하고 원본 테이블 churn이 크면 materialized view나 projection table이 더 낫다.

---

## 운영 롤아웃 체크: “생성”보다 “정리”가 더 중요할 때가 많다

새 인덱스를 만드는 일은 쉽다. 어려운 건 인덱스 생태계를 건강하게 유지하는 일이다.

### 권장 순서

1. 슬로우 쿼리/핫패스 확인
2. projection 축소
3. covering index 후보 설계
4. `CREATE INDEX CONCURRENTLY`
5. 쿼리 플랜과 지연시간 검증
6. write 부작용 확인
7. **기존 중복 인덱스 제거 검토**

여기서 7단계를 빼먹는 팀이 많다. 그 결과:

- 새 인덱스도 있고
- 예전 인덱스도 남고
- 쓰기 비용은 둘 다 내고
- 어느 쿼리가 뭘 쓰는지 점점 불명확해진다.

즉 covering index 최적화의 마지막 단계는 종종 “하나 더 만들기”가 아니라 **덜어내기**다.

---

## PostgreSQL의 Covering Index를 MySQL 감각으로 보면 자주 틀리는 이유

실무에서 이 주제가 헷갈리는 가장 큰 이유 중 하나는 MySQL 경험 때문이다. 둘 다 인덱스만으로 결과를 돌려줄 수 있다는 점은 비슷하지만, 운영 감각은 꽤 다르다.

### 공통점

- 필요한 컬럼이 인덱스에 있으면 heap/table 재방문을 줄일 수 있다.
- 목록 조회, 정렬 + LIMIT, projection이 작은 API에서 효과가 크다.

### PostgreSQL에서 더 주의할 점

1. **MVCC visibility 확인이 별도 관심사**다.
2. autovacuum 상태가 read path 체감 성능에 영향을 준다.
3. 최근 hot page는 index only scan 품질이 떨어질 수 있다.
4. heap fetch가 0이 아닐 수 있다는 점을 항상 염두에 둬야 한다.

즉 MySQL에서의 "covering index = 거의 끝" 감각을 PostgreSQL에 그대로 가져오면 실망하기 쉽다. PostgreSQL에서는 **DDL + vacuum + update pattern**을 같이 봐야 한다.

이 비교는 중요한 실무 판단으로 이어진다.

- MySQL 경험상 유효했던 인덱스가 PostgreSQL에서는 기대보다 덜 먹힐 수 있다.
- PostgreSQL에서는 오히려 row mutability를 줄이는 스키마/도메인 설계가 더 큰 최적화가 될 수 있다.

---

## 조인 쿼리에서는 Covering Index를 어떻게 봐야 하나

많은 실제 API는 단일 테이블 조회가 아니다. 예를 들어 주문 목록 화면에서 주문 테이블만 읽는 것이 아니라 고객명, 결제 상태, 배송 상태를 함께 보여주고 싶어 한다.

```sql
SELECT
  o.id,
  o.order_no,
  o.total_amount,
  o.created_at,
  c.name AS customer_name
FROM orders o
JOIN customers c ON c.id = o.customer_id
WHERE o.tenant_id = $1
  AND o.status = 'PAID'
ORDER BY o.created_at DESC
LIMIT 50;
```

이때 흔한 오해는 `orders`에 covering index를 만들면 쿼리 전체가 거의 끝난다고 생각하는 것이다. 실제로는 절반만 맞다.

### 어떤 부분은 좋아질 수 있다

- `orders` 후보 row를 빠르게 좁힌다.
- `orders` 측 projection 일부를 heap 없이 공급할 수 있다.
- `LIMIT 50`까지 도달하는 비용이 줄 수 있다.

### 하지만 조인 상대는 여전히 별도 문제다

- `customers` 접근 방식이 비싸면 전체 지연시간은 여전히 높다.
- `customer_name` 때문에 매 row join lookup이 발생할 수 있다.
- 조인 순서와 row estimate 오차가 크면 covering index 이득이 희석될 수 있다.

즉 조인 쿼리에서는 다음처럼 생각해야 한다.

1. 가장 바깥쪽 후보 집합을 얼마나 빨리 작게 만들 수 있는가
2. 그 뒤 join lookup 수를 얼마나 줄일 수 있는가
3. 목록 화면이라면 customer_name을 denormalize/projection table로 빼는 게 낫지 않은가

### 실무적으로 자주 맞는 패턴

목록 API는 원본 join을 그대로 유지하기보다 아래처럼 분리할 때가 많다.

- `order_list_items` read model 생성
- 주문 목록에 필요한 고객명, 채널, 통화 정도만 미리 동기화
- 이 read model에 covering index 적용

이 구조는 write 복잡도는 조금 늘어나지만, 자주 호출되는 목록 API에는 매우 강하다.

즉 조인 쿼리에서 covering index를 쓸 때는 “원본 join 전체를 인덱스로 끝낼 수 있나”보다, **핫한 read path를 더 단순한 구조로 바꿀 수 있나**를 먼저 보는 편이 낫다.

---

## 실무 예시 7: 멀티테넌트 공지사항 목록 — 읽기 경로가 안정적일수록 covering index가 잘 먹힌다

공지사항 목록을 예로 들어 보자.

```sql
SELECT id, slug, title, author_id, published_at
FROM notices
WHERE tenant_id = $1
  AND status = 'PUBLISHED'
  AND published_at <= now()
ORDER BY published_at DESC, id DESC
LIMIT 30;
```

이 쿼리는 covering index에 매우 좋은 후보일 수 있다.

이유:

- projection이 작다.
- status가 게시 후 크게 안 바뀐다.
- row가 발행 후 자주 수정되지 않는다.
- 정렬 기준이 안정적이다.
- 목록 호출 빈도가 높다.

가능한 인덱스:

```sql
CREATE INDEX idx_notices_public_listing
ON notices (tenant_id, status, published_at DESC, id DESC)
INCLUDE (slug, title, author_id);
```

여기서 중요한 실무 판단은 `published_at <= now()` 같은 조건이 있어도, 실제 row 대부분이 발행 완료 상태로 안정적이면 visibility 측면에서 꽤 유리하다는 점이다. 즉 **비즈니스 워크플로가 immutable에 가까운 도메인**은 covering index 효율이 좋다.

---

## 실무 예시 8: 결제 이력 화면 — 최신 1시간과 지난 7일은 다른 쿼리처럼 봐야 한다

많은 팀이 하나의 화면에 하나의 인덱스만 생각한다. 하지만 같은 화면이라도 시간 범위에 따라 workload가 다를 수 있다.

예를 들어 결제 이력 화면에서:

- 최근 1시간 조회
- 지난 7일 조회

가 모두 중요하다고 하자.

```sql
SELECT id, order_no, amount, status, created_at
FROM payment_events
WHERE tenant_id = $1
  AND created_at >= $from
ORDER BY created_at DESC
LIMIT 100;
```

겉보기엔 같은 쿼리지만, 실제 데이터 성격은 다르다.

### 최근 1시간

- page가 계속 뜨겁다
- status/후처리 업데이트가 아직 남아 있을 수 있다
- all-visible 비율 낮을 수 있다

### 지난 7일 중 과거 구간

- 이미 안정화된 row 비중이 높다
- heap fetch 감소 효과를 더 잘 볼 수 있다

이 차이를 이해하면 팀의 기대치가 훨씬 현실적이 된다. covering index는 두 구간 모두에 도움이 될 수 있지만, **효과 크기는 동일하지 않다.**

이런 workload에서는 지표를 한 숫자로만 보지 말고 아래처럼 나눠 보는 것이 좋다.

- 최근 15분 latency
- 최근 24시간 latency
- 시간 구간별 heap fetch 패턴

즉 동일한 인덱스라도 어느 시간 구간을 읽느냐에 따라 체감 성능이 달라질 수 있다.

---

## 실무 예시 9: “좋은 covering index”보다 “나쁜 projection 제거”가 먼저였던 사례

어떤 상품 목록 API가 느리다고 하자.

```sql
SELECT id, sku, name, short_desc, long_desc, specs_json,
       price, discount_price, stock_status, thumbnail_url,
       category_name, brand_name, updated_at
FROM product_search_view
WHERE tenant_id = $1
  AND is_active = true
ORDER BY updated_at DESC
LIMIT 48;
```

많은 팀은 여기서 곧바로 인덱스 후보를 고민한다. 하지만 이 쿼리는 이미 경고 신호가 많다.

- `long_desc`가 목록 카드에 정말 필요한가?
- `specs_json`을 목록에서 즉시 써야 하는가?
- `category_name`, `brand_name`은 별도 lookup/cache로 충분하지 않은가?

이런 경우 실제 개선 순서는 대개 이렇다.

1. 응답 계약을 줄인다.
2. view 대신 base projection table로 단순화한다.
3. 그 뒤에 covering index를 붙인다.

결국 covering index가 성능을 만든 것처럼 보여도, 진짜 승부는 **projection discipline**에서 난다.

---

## 구현 전 사고 실험: 이 컬럼을 INCLUDE할 때 무엇을 사는가

팀 리뷰에서 아주 유용한 질문이 있다.

> 이 컬럼을 INCLUDE하면 정확히 무엇을 얻고, 무엇을 잃는가?

컬럼별로 따져 보면 판단이 쉬워진다.

### `id`

- 거의 항상 작고 안정적
- INCLUDE 후보로 무난

### `title`, `name`

- 목록 표시용으로 자주 필요
- 길이가 적당하고 수정 빈도가 낮다면 괜찮음

### `status`

- WHERE 조건이면 key로 갈 가능성이 큼
- 자주 바뀌면 쓰기 영향도 고려 필요

### `updated_at`

- 정렬/범위에 쓰이면 key로 고려
- 단순 표시용이면 INCLUDE 가능하지만 update churn 주의

### `jsonb`, `text body`, `memo`

- 대부분 INCLUDE 부적합
- projection 축소가 먼저

이렇게 컬럼별 사고를 하면 "일단 다 넣어보자"를 막을 수 있다.

---

## 인덱스 설계 리뷰 때 팀이 꼭 물어야 할 질문 10개

1. 이 쿼리는 정말 핫패스인가?
2. LIMIT와 ORDER BY가 안정적인가?
3. 반환 컬럼은 몇 개이고 얼마나 큰가?
4. row는 생성 후 얼마나 자주 바뀌는가?
5. partial index로 대상 row를 줄일 수 있는가?
6. 기존 인덱스 중 재활용하거나 대체할 것이 있는가?
7. write latency/WAL 증가를 감당할 수 있는가?
8. autovacuum 상태가 나쁜데 DDL로만 해결하려는 건 아닌가?
9. keyset pagination 같은 상위 구조 개선이 가능한가?
10. 이 인덱스를 6개월 뒤에도 설명할 수 있는가?

마지막 질문이 의외로 중요하다. 설명하기 어려운 인덱스는 대개 과도하거나 임시 처방일 가능성이 높다.

---

## 검증 루틴: 적용 후 무엇을 확인해야 “성공”이라고 볼 수 있나

인덱스를 만들고 실행 계획에 `Index Only Scan`이 한 번 찍혔다고 성공이 아니다. 최소한 아래를 확인해야 한다.

### 1) 쿼리 지연시간

- p50만 아니라 p95/p99도 본다.
- 쓰기 피크 시간대에도 좋아졌는지 본다.

### 2) heap fetch 추세

- 배포 직후 한 번만 보지 말고 시간대별로 본다.
- autovacuum 이후 좋아지는지, 쓰기 피크에 다시 나빠지는지 본다.

### 3) 인덱스 크기 증가

- 새 인덱스가 메모리/디스크에 주는 부담 확인
- 캐시 압박이 생기지 않는지 본다.

### 4) write 영향

- INSERT/UPDATE latency 상승 여부
- WAL/replication lag 변화

### 5) 불필요해진 기존 인덱스 여부

- 새 인덱스 도입 후 사용량이 0에 가까운 구형 인덱스가 생기지 않았는가

즉 검증은 쿼리 하나가 아니라 **시스템 전체 읽기/쓰기 균형**을 보는 일이다.

---

## 어떤 순서로 최적화할까: 추천 우선순위

covering index는 강력하지만, 무조건 첫 카드로 꺼낼 필요는 없다. 실무적으로는 아래 순서가 효율적이다.

### 1단계: projection 정리

- `SELECT *` 제거
- 목록/상세 응답 분리
- 큰 컬럼 제거

### 2단계: 정렬/필터에 맞는 기본 composite index 설계

- leading column 순서 정리
- keyset pagination 가능성 점검

### 3단계: partial index 검토

- 상태/삭제 여부/공개 여부 등으로 대상 row 축소

### 4단계: 그 다음에 INCLUDE

- 정말 필요한 반환 컬럼만 포함

### 5단계: 운영 상태 검증

- heap fetch
- vacuum
- write 부작용

이 순서를 지키면 인덱스가 더 작고 오래 살아남는다.

---

## 트레이드오프: Covering Index는 읽기 최적화지만, 쓰기/저장공간/운영 복잡도를 산다

실무에서 좋은 판단은 항상 trade-off를 숫자로 보는 데서 나온다.

### 장점

- heap fetch 감소 가능
- 목록 API/대시보드/읽기 핫패스 지연시간 개선
- 랜덤 I/O 절감 가능
- 인덱스 정렬과 projection을 한 번에 처리할 기회 확보

### 비용

- 인덱스 크기 증가
- INSERT/UPDATE WAL 증가
- vacuum/maintenance 부담 증가
- HOT 기회 감소 가능
- 유사 인덱스 난립 위험

### 특히 신중해야 하는 경우

- 자주 수정되는 컬럼을 INCLUDE하려는 경우
- 긴 텍스트/JSONB 조각을 넣으려는 경우
- 비슷한 목록 API가 너무 많은 경우
- 실제 트래픽은 낮은데 "언젠가 필요할 것 같아서" 미리 추가하는 경우

### 추천 판단 기준

다음 질문에 `예`가 많을수록 covering index 가치가 높다.

1. 이 조회는 충분히 자주 호출되는가?
2. 반환 컬럼이 비교적 작고 안정적인가?
3. row가 생성 후 크게 변하지 않는가?
4. 정렬/필터 패턴이 안정적인가?
5. partial index로 대상 row를 더 줄일 수 있는가?
6. 비슷한 인덱스가 이미 있지 않은가?

---

## 흔한 실수 1: `SELECT *` API에 covering index를 기대한다

가장 흔하고 가장 비효율적이다.

`SELECT *`는 대개 이런 문제를 만든다.

- 반환 컬럼이 계속 변한다.
- 큰 텍스트/메모/메타데이터까지 끌려온다.
- covering index 설계가 사실상 불가능하거나 너무 비싸진다.

covering index는 **projection이 명확한 API**와 궁합이 좋다. 즉 목록/탐색/대시보드처럼 필요한 컬럼이 안정적인 쿼리에 맞다.

실무 원칙은 단순하다.

> index only scan을 원하면 먼저 `SELECT *`를 버려라.

---

## 흔한 실수 2: ORDER BY 지원 없이 INCLUDE만 늘린다

다음 쿼리를 보자.

```sql
SELECT id, title, price
FROM products
WHERE tenant_id = 7
  AND status = 'PUBLISHED'
ORDER BY published_at DESC
LIMIT 20;
```

그런데 인덱스를 이렇게 만들면:

```sql
CREATE INDEX idx_products_tenant_status
ON products (tenant_id, status)
INCLUDE (id, title, price, published_at);
```

반환 컬럼은 인덱스에 있지만, 정렬 기준 `published_at DESC`가 key order에 없어서 planner가 추가 정렬이나 더 비싼 경로를 택할 수 있다.

즉 INCLUDE는 정렬 대체 수단이 아니다. 정렬이 중요하면 **정렬 컬럼은 key part**에 있어야 한다.

---

## 흔한 실수 3: 자주 바뀌는 상태 컬럼을 무분별하게 INCLUDE한다

예를 들어 작업 큐 테이블에서 아래 조회를 최적화한다고 하자.

```sql
SELECT id, payload, retry_count, updated_at
FROM jobs
WHERE queue_name = 'email'
  AND status = 'READY'
ORDER BY scheduled_at ASC
LIMIT 100;
```

여기서 `retry_count`, `updated_at`, 심지어 `status` 전이와 함께 자주 바뀌는 컬럼을 넓게 커버하려고 하면 읽기는 조금 나아질 수 있어도 쓰기 비용이 크게 오른다.

작업 큐처럼 상태 전이가 빈번한 도메인에서는 다음을 먼저 생각해야 한다.

- partial index로 READY만 잡을 수 있는가
- payload 원문 대신 요약 컬럼만 필요한가
- dequeue 경로와 관리 화면 경로를 분리해야 하는가

즉 변경이 심한 hot table에는 covering index보다 **도메인 분리**가 더 큰 해법일 수 있다.

---

## 흔한 실수 4: visibility map 문제를 인덱스 문제로 오해한다

아래 상황은 꽤 자주 발생한다.

- 실행 계획에 `Index Only Scan`이 찍힌다.
- 그런데 `Heap Fetches`가 계속 높다.
- 팀은 INCLUDE 컬럼을 더 추가하거나 인덱스를 다시 만든다.

하지만 원인은 인덱스 부족이 아니라 다음일 수 있다.

- autovacuum이 늦다.
- 장기 트랜잭션 때문에 page가 all-visible로 정리되지 못한다.
- 최근 데이터가 계속 수정 중이다.
- 테이블 성격상 index only scan 친화적이지 않다.

이럴 때 인덱스를 바꾸는 건 증상에 비해 처방이 어긋난다. 먼저 확인해야 할 것은:

- `pg_stat_user_tables`의 vacuum/analyze 상태
- 장기 트랜잭션 존재 여부
- 업데이트 빈도와 대상 구간
- 쿼리가 읽는 데이터가 최근 hot range인지 여부

즉 index only scan의 실패를 언제나 DDL 문제로 보지 말아야 한다.

---

## 흔한 실수 5: Covering Index 하나로 상세 조회와 목록 조회를 동시에 해결하려 한다

목록 조회와 상세 조회는 보통 성격이 다르다.

### 목록 조회

- row 수 적당히 많음
- 특정 정렬 + LIMIT 중요
- 필요한 컬럼은 제한적
- covering index 효과 큼

### 상세 조회

- 보통 PK 하나 조회
- 컬럼이 훨씬 많음
- 큰 text/json/blob성 컬럼까지 필요할 수 있음

상세 조회까지 covering으로 만들려고 하면 인덱스가 비대해진다. 대부분은:

- 목록 API는 covering/partial/composite index로 최적화
- 상세 페이지는 PK lookup + heap access 허용

이 분리가 더 건강하다.

---

## 실무 체크리스트: Covering Index 추가 전 반드시 확인할 것

### 1. 쿼리 표면 확인

- [ ] `SELECT *`가 아닌가
- [ ] 반환 컬럼이 안정적인가
- [ ] 정렬 기준이 명확한가
- [ ] LIMIT 기반 목록 조회인가

### 2. workload 확인

- [ ] 호출 빈도가 충분히 높은가
- [ ] 읽기 이득이 쓰기 비용을 상쇄할 만큼 큰가
- [ ] 대상 row가 생성 후 비교적 안정적인가
- [ ] 최신 hot range만 읽는 패턴은 아닌가

### 3. 인덱스 설계 확인

- [ ] 필터/정렬 컬럼만 key part에 두었는가
- [ ] 반환 전용 컬럼은 INCLUDE로 분리했는가
- [ ] partial index로 더 작게 만들 수 있는가
- [ ] 기존 인덱스와 중복되지 않는가

### 4. 운영 확인

- [ ] `EXPLAIN (ANALYZE, BUFFERS)`로 검증했는가
- [ ] `Heap Fetches`를 확인했는가
- [ ] autovacuum 상태를 같이 봤는가
- [ ] 장기 트랜잭션/idle in transaction을 점검했는가

### 5. 쓰기 영향 확인

- [ ] INCLUDE 컬럼이 자주 바뀌지 않는가
- [ ] 인덱스 크기 증가를 감당할 수 있는가
- [ ] HOT 기회 감소가 치명적이지 않은가
- [ ] WAL 및 복제 지연 영향이 없는가

---

## 운영 팁: “index only scan이 잘 나오는 테이블”을 일부러 만들 수도 있다

실무에서 더 적극적으로 접근하면, 쿼리만 고치는 게 아니라 **데이터 수명주기 자체를 index only scan 친화적으로** 설계할 수 있다.

예를 들어:

### 패턴 1: active / history 분리

- `orders_active`: 아직 상태 전이 중인 주문
- `orders_history`: 정산 완료 후 거의 immutable한 주문

이렇게 나누면 history 쪽은 all-visible 비율이 높아져 covering index 효율이 좋아진다.

### 패턴 2: 목록용 projection table

복잡한 join과 자주 바뀌는 원본 테이블 대신, 목록 페이지에 필요한 최소 컬럼만 가진 projection/read model을 둔다.

- 쓰기는 조금 복잡해진다.
- 대신 read path는 훨씬 단순해진다.
- index only scan 친화적인 구조를 만들기 쉽다.

### 패턴 3: 상태 종료 후 immutable zone 만들기

예를 들어 `published_posts`나 `settled_payouts`처럼 "끝난 후 거의 안 바뀌는" 구간을 명확히 만들면, index only scan 효과가 커진다.

즉 PostgreSQL 성능은 쿼리 튜닝만이 아니라 **데이터 변이 패턴 설계**와도 연결된다.

---

## 실무 예시 4: 커버링보다 컬럼 축소가 먼저인 경우

어떤 팀은 목록 API가 느리다고 하면 바로 인덱스를 고민한다. 그런데 종종 더 큰 문제는 쿼리가 너무 많은 컬럼을 가져오는 것이다.

예를 들어:

```sql
SELECT id, slug, title, summary, body_html, hero_image_url, tags_json,
       author_name, author_bio, created_at, published_at
FROM posts
WHERE site_id = 1
  AND status = 'PUBLISHED'
ORDER BY published_at DESC
LIMIT 20;
```

이건 covering index 이전에 **화면 계약이 과하다**는 신호일 수 있다.

목록 카드에 정말 필요한 것은 대개 이 정도다.

```sql
SELECT id, slug, title, summary, hero_image_url, published_at
FROM posts
WHERE site_id = 1
  AND status = 'PUBLISHED'
ORDER BY published_at DESC
LIMIT 20;
```

이렇게 projection을 줄이면:

- heap read 자체가 줄고
- covering index 설계 가능성이 생기고
- 네트워크 payload도 줄고
- 캐시 효율도 좋아진다.

즉 covering index는 종종 "마지막 20% 최적화"가 아니라, **API 응답 계약 정리와 함께 가야 하는 구조 개선**이다.

---

## 한 단계 더: Composite Index 컬럼 순서는 여전히 중요하다

INCLUDE가 있다고 해서 key order 중요성이 사라지는 건 아니다. 오히려 더 중요해진다.

예를 들어:

```sql
WHERE tenant_id = ?
  AND status = 'PUBLISHED'
ORDER BY published_at DESC
LIMIT 20
```

이라면 보통 다음이 자연스럽다.

```sql
(tenant_id, status, published_at DESC)
```

반대로 이렇게 두면:

```sql
(status, published_at DESC, tenant_id)
```

멀티테넌트 workload에서는 `tenant_id` 선택도가 좋아도 앞부분을 못 타면서 비효율적일 수 있다.

즉 covering index의 성공 조건은 단순히 INCLUDE가 아니라:

1. key 순서가 실제 탐색 패턴과 맞고
2. 반환 컬럼이 인덱스에 있고
3. visibility 상태가 따라오고
4. 쓰기 비용이 감당 가능해야 한다.

이 네 가지가 같이 맞아야 한다.

---

## 마이그레이션 전략: 운영 중 기존 인덱스를 어떻게 바꿀까

실서비스에서는 보통 이미 인덱스가 있다. 이때 대개 아래 순서가 안전하다.

### 1) 후보 쿼리 선정

- 느린 쿼리 로그
- APM 상 호출 빈도
- p95/p99 높은 읽기 API

여기서 실제 가치가 큰 쿼리만 고른다.

### 2) projection 축소

먼저 정말 필요한 컬럼만 남긴다.

### 3) 새 covering index를 `CONCURRENTLY`로 추가

```sql
CREATE INDEX CONCURRENTLY ...
```

운영 쓰기를 막지 않도록 한다.

### 4) `EXPLAIN (ANALYZE, BUFFERS)`와 실제 트래픽 검증

- node type
- heap fetches
- latency
- write 부작용

### 5) 중복/구형 인덱스 정리

새 인덱스가 안정적으로 사용되면, 기존 유사 인덱스를 제거할지 검토한다. 중복 인덱스를 방치하면 읽기 이득보다 쓰기 비용이 더 커질 수 있다.

---

## 언제 만들지 말아야 하나

다음 상황이라면 covering index를 서두르지 않는 편이 낫다.

### 1) 테이블이 매우 작다

작은 테이블은 heap 접근 비용이 크지 않다. 오히려 인덱스 추가로 복잡도만 늘 수 있다.

### 2) 조회 빈도가 낮다

월 몇 번 보는 관리자 화면이면 과최적화일 수 있다.

### 3) row가 계속 바뀐다

최신 작업 큐, 실시간 상태 테이블, 세션 스토어 등은 index only scan 이점이 약할 수 있다.

### 4) 반환 컬럼이 크고 불안정하다

긴 text, 대형 JSON, 자주 수정되는 메모성 컬럼은 INCLUDE 후보가 아니다.

### 5) 더 상위 구조 문제가 있다

- 쿼리가 너무 많은 join을 한다
- projection이 과도하다
- read model 분리가 필요하다
- retention/partitioning이 먼저다

이때 covering index는 증상 완화는 될 수 있어도 본질 해결은 아닐 수 있다.

---

## 한 줄 정리 전에 꼭 남기고 싶은 실무 감각

PostgreSQL에서 index only scan을 잘 쓰는 팀은 보통 인덱스 문법만 잘 아는 팀이 아니다. 그 팀들은 대개 다음을 같이 본다.

- 어떤 조회가 정말 비싼가
- 그 조회는 어떤 컬럼만 필요로 하는가
- 그 row는 시간이 지나도 잘 안 바뀌는가
- autovacuum과 장기 트랜잭션이 read latency에 어떤 영향을 주는가
- 이 문제를 인덱스로 풀지, projection table이나 데이터 수명주기로 풀지

즉 covering index는 단순 SQL 테크닉이 아니라, **읽기 경로를 스토리지 현실에 맞게 좁혀 가는 설계 감각**에 가깝다.

---

## 체크리스트 요약

- [ ] `SELECT *`를 먼저 없앴는가
- [ ] 필터/정렬 컬럼과 반환 컬럼을 분리했는가
- [ ] 반환 전용 컬럼은 `INCLUDE` 후보로 검토했는가
- [ ] partial index로 인덱스 대상을 줄일 수 있는가
- [ ] 자주 바뀌는 컬럼을 무심코 넣지 않았는가
- [ ] `EXPLAIN (ANALYZE, BUFFERS)`에서 `Heap Fetches`를 확인했는가
- [ ] autovacuum/visibility map 상태를 같이 봤는가
- [ ] 유사 인덱스 난립을 막고 있는가
- [ ] 최신 hot range에는 기대를 과하게 걸지 않았는가
- [ ] 읽기 이득이 쓰기 비용보다 큰지 숫자로 확인했는가

---

## 한 줄 정리

**PostgreSQL covering index의 성패는 INCLUDE 문법이 아니라, “필요한 컬럼을 인덱스에 담되 heap fetch를 줄일 수 있는 데이터 구간인가”를 판단하는 데 달려 있다.**
