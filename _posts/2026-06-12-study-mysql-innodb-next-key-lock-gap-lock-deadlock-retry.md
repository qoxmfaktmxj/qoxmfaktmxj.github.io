---
layout: post
title: "MySQL InnoDB Locking 실전: Next-Key Lock, Gap Lock, Deadlock Retry로 동시성 장애를 줄이는 법"
date: 2026-06-12 11:50:00 +0900
categories: [sql]
tags: [study, sql, mysql, innodb, locking, gap-lock, next-key-lock, deadlock, transaction, isolation, performance, operations]
permalink: /sql/2026/06/12/study-mysql-innodb-next-key-lock-gap-lock-deadlock-retry.html
---

## 배경: MySQL 장애는 "쿼리가 느리다"보다 "왜 여기서 락이 걸리지?"에서 더 자주 어려워진다

MySQL InnoDB를 운영하다 보면 처음에는 인덱스와 실행 계획이 가장 큰 문제처럼 보인다. 실제로 많은 성능 장애는 full scan, 잘못된 복합 인덱스, 낮은 선택도, 과도한 정렬, 잘못된 pagination에서 시작한다. 하지만 어느 정도 트래픽이 붙은 서비스에서는 다른 종류의 문제가 더 까다롭다.

> **쿼리 자체는 빠른데, 동시에 실행되면 갑자기 대기하고 실패하고 deadlock이 난다.**

이 문제는 단순한 SQL 튜닝과 다르다. 실행 계획만 봐서는 "왜 이 요청이 5초 동안 멈췄는지"가 잘 보이지 않는다. 개발 환경에서는 재현되지 않다가 운영 피크 시간에만 나타난다. 로그에는 `Lock wait timeout exceeded`, `Deadlock found when trying to get lock`, `try restarting transaction` 같은 메시지가 남는다. 사용자는 결제 버튼을 눌렀는데 응답이 늦고, 워커는 같은 작업을 여러 번 집어 가고, 배치는 온라인 요청을 막고, 운영자는 어떤 세션을 죽여야 할지 고민한다.

InnoDB 락을 어렵게 만드는 이유는 "행 하나를 수정하면 행 하나만 잠긴다"는 직관이 자주 깨지기 때문이다. 특히 기본 격리 수준인 `REPEATABLE READ`에서는 InnoDB가 phantom read를 막기 위해 **record lock**뿐 아니라 **gap lock**, **next-key lock**을 사용한다. 그래서 인덱스 조건, 범위 조건, 유니크 조건, 존재하지 않는 값 조회, 정렬 방향, 격리 수준에 따라 잠금 범위가 달라진다.

예를 들어 아래 두 쿼리는 둘 다 간단해 보인다.

```sql
SELECT *
FROM coupons
WHERE code = 'WELCOME2026'
FOR UPDATE;

SELECT *
FROM coupons
WHERE issued_at < '2026-06-01'
FOR UPDATE;
```

하지만 첫 번째 쿼리가 유니크 인덱스를 정확히 타는지, 두 번째 쿼리가 범위 인덱스를 타는지, 조건에 맞는 row가 실제로 존재하는지에 따라 잠금 범위는 완전히 달라진다. 더 나쁜 경우는 인덱스가 없어 full scan이 발생하면서 의도보다 훨씬 많은 row와 gap을 잠그는 상황이다. 개발자는 "한 건만 잡으려 했다"고 생각하지만 DB는 "조건을 만족할 수 있는 범위"를 보호하고 있을 수 있다.

이 글은 MySQL InnoDB 락을 문법 설명이 아니라 **운영 장애를 줄이는 설계 기준**으로 정리한다. 중급 이상 개발자가 실제 서비스에서 마주치는 주문 상태 변경, 재고 차감, 쿠폰 발급, 작업 큐, 중복 요청 방지, 배치 보정 같은 사례를 기준으로 본다.

이번 글에서 답하려는 질문은 아래와 같다.

1. InnoDB의 record lock, gap lock, next-key lock은 각각 무엇을 보호하는가?
2. `REPEATABLE READ`와 `READ COMMITTED`는 락 동작을 어떻게 바꾸는가?
3. `SELECT ... FOR UPDATE`는 언제 필요한 락이고, 언제 불필요하게 장애 반경을 키우는가?
4. 인덱스가 없거나 잘못 잡히면 왜 "row lock"이 넓은 범위 락처럼 보이는가?
5. deadlock은 왜 버그가 아니라 정상적으로 발생 가능한 동시성 결과이며, 어떻게 재시도해야 하는가?
6. 작업 큐와 배치에서는 `SKIP LOCKED`, 청크 처리, 정렬 기준을 어떻게 써야 하는가?
7. 운영에서 락 대기와 deadlock을 어떤 쿼리와 지표로 관측해야 하는가?

핵심 결론부터 말하면 이렇다.

1. InnoDB 락은 row만 잠그는 것이 아니라 **인덱스 레코드와 그 사이의 범위**를 잠근다.
2. `REPEATABLE READ`에서 범위 조건은 next-key lock 때문에 생각보다 넓은 삽입 차단을 만들 수 있다.
3. 락을 줄이는 가장 강력한 방법은 "락 힌트를 줄이는 것"이 아니라 **정확한 인덱스로 잠금 범위를 좁히는 것**이다.
4. deadlock은 완전히 없애는 대상이 아니라 **작게 만들고, 빠르게 감지하고, 안전하게 재시도하는 대상**이다.
5. 트랜잭션 안에서 외부 API, 긴 계산, 대량 루프를 수행하면 락 설계가 아무리 좋아도 운영에서 무너진다.
6. 작업 큐는 `FOR UPDATE SKIP LOCKED`를 쓰더라도 정렬 기준, 상태 전이, 재처리 기준, idempotency가 함께 있어야 안전하다.
7. 좋은 동시성 설계는 "강한 락을 많이 쓰는 것"이 아니라 **업무상 직렬화가 필요한 최소 지점을 명확히 잠그는 것**이다.

---

## 핵심 개념 1: InnoDB는 테이블 row가 아니라 인덱스 엔트리를 잠근다

InnoDB 락을 이해할 때 가장 먼저 바꿔야 하는 생각은 이것이다.

> "테이블의 row를 잠근다"보다 "검색에 사용한 인덱스의 엔트리와 범위를 잠근다"가 더 정확하다.

InnoDB는 클러스터드 인덱스 구조를 가진다. Primary Key가 클러스터드 인덱스이고, 보조 인덱스는 Primary Key 값을 함께 들고 있다. 어떤 row를 찾고 수정하든 결국 인덱스를 통해 대상 row를 찾는다. 그래서 잠금도 인덱스 접근 방식과 강하게 연결된다.

대표 락을 구분하면 다음과 같다.

| 락 종류 | 잠그는 대상 | 대표 상황 | 실무 의미 |
| --- | --- | --- | --- |
| Record Lock | 인덱스 레코드 자체 | 유니크 인덱스 정확 조회 후 수정 | 특정 row 변경 충돌 방지 |
| Gap Lock | 인덱스 레코드 사이의 빈 공간 | 범위 조건, 존재하지 않는 값 보호 | 다른 트랜잭션의 삽입 차단 |
| Next-Key Lock | Record Lock + 앞쪽 Gap Lock | `REPEATABLE READ` 범위 검색 | phantom read 방지 |
| Insert Intention Lock | gap에 삽입하려는 의도 | 동시 insert | 서로 다른 위치 insert는 병행 가능 |
| AUTO-INC Lock | auto increment 값 할당 | 대량 insert | insert 처리량과 순서에 영향 |

여기서 운영자가 가장 자주 헷갈리는 것은 gap lock과 next-key lock이다.

예를 들어 `orders` 테이블에 아래 인덱스가 있다고 하자.

```sql
CREATE TABLE orders (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  status VARCHAR(20) NOT NULL,
  created_at DATETIME NOT NULL,
  amount DECIMAL(12, 2) NOT NULL,
  KEY idx_orders_user_status_created (user_id, status, created_at)
) ENGINE=InnoDB;
```

다음 쿼리는 특정 사용자의 미결제 주문을 잠그려는 의도다.

```sql
START TRANSACTION;

SELECT id
FROM orders
WHERE user_id = 10
  AND status = 'PENDING'
ORDER BY created_at
LIMIT 1
FOR UPDATE;
```

인덱스가 `user_id, status, created_at` 순서로 잘 잡혀 있으면 InnoDB는 해당 user/status 범위 안에서 필요한 인덱스 엔트리를 찾고 잠근다. 하지만 인덱스가 `created_at`만 있거나 아예 없으면 어떻게 될까? MySQL은 조건을 만족하는 row를 찾기 위해 훨씬 넓은 범위를 훑어야 하고, `FOR UPDATE`는 그 과정에서 더 많은 row와 범위를 잠글 수 있다.

즉 "락 범위"는 SQL의 의도만으로 결정되지 않는다. **실제 실행 계획과 인덱스 접근 경로**가 잠금 범위를 결정한다.

실무에서 락 이슈가 터졌을 때 가장 먼저 확인해야 하는 것도 그래서 `EXPLAIN`이다.

```sql
EXPLAIN
SELECT id
FROM orders
WHERE user_id = 10
  AND status = 'PENDING'
ORDER BY created_at
LIMIT 1
FOR UPDATE;
```

확인할 포인트는 단순하다.

- `key`: 의도한 인덱스를 타는가?
- `type`: `const`, `ref`, `range` 수준인가, 아니면 `ALL`인가?
- `rows`: 예상 탐색 row 수가 너무 크지 않은가?
- `Extra`: `Using filesort`, `Using temporary`가 락 구간 안에서 발생하지 않는가?
- 조건과 정렬이 같은 복합 인덱스로 자연스럽게 해결되는가?

InnoDB 락 튜닝은 "락 옵션을 더 잘 외우는 일"이 아니다. 대개는 **잠그기 전에 적게 찾도록 인덱스를 설계하는 일**이다.

---

## 핵심 개념 2: Gap Lock과 Next-Key Lock은 존재하지 않는 row까지 보호한다

개발자가 가장 직관적으로 받아들이기 어려운 부분은 "존재하지 않는 row 때문에 다른 insert가 막히는 상황"이다.

예를 들어 쿠폰 코드가 유니크해야 한다고 하자.

```sql
CREATE TABLE coupons (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  code VARCHAR(64) NOT NULL,
  status VARCHAR(20) NOT NULL,
  issued_to BIGINT NULL,
  created_at DATETIME NOT NULL,
  UNIQUE KEY uk_coupons_code (code)
) ENGINE=InnoDB;
```

아래 쿼리는 유니크 인덱스를 정확히 사용한다.

```sql
START TRANSACTION;

SELECT id
FROM coupons
WHERE code = 'WELCOME2026'
FOR UPDATE;
```

`code = 'WELCOME2026'` row가 존재하고 유니크 인덱스로 정확히 찾는다면, InnoDB는 보통 해당 인덱스 레코드만 잠그면 된다. 하지만 row가 존재하지 않는 경우에는 이야기가 달라진다. InnoDB는 "이 값이 여전히 없다는 사실"을 트랜잭션 중 보장해야 할 수 있다. 이때 해당 값이 들어갈 수 있는 gap이 잠기면서 다른 트랜잭션의 insert가 막힐 수 있다.

범위 조건에서는 더 명확하다.

```sql
START TRANSACTION;

SELECT id
FROM coupons
WHERE code BETWEEN 'A' AND 'M'
FOR UPDATE;
```

이 쿼리는 실제 존재하는 row만 잠그는 것이 아니라 `A`부터 `M`까지의 인덱스 범위를 보호한다. `REPEATABLE READ`에서는 같은 트랜잭션 안에서 다시 조회했을 때 갑자기 새로운 row가 나타나는 phantom을 막아야 하기 때문이다. 그래서 다른 세션이 `code = 'HELLO'`를 insert하려 하면 대기할 수 있다.

이 동작은 정합성 측면에서는 의미가 있다. 하지만 온라인 서비스에서는 예상치 못한 insert 지연으로 보일 수 있다.

### 실무 예시: 예약 가능 시간 슬롯 조회

아래처럼 예약 슬롯 테이블이 있다고 하자.

```sql
CREATE TABLE reservations (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  room_id BIGINT NOT NULL,
  starts_at DATETIME NOT NULL,
  ends_at DATETIME NOT NULL,
  status VARCHAR(20) NOT NULL,
  KEY idx_reservations_room_starts (room_id, starts_at)
) ENGINE=InnoDB;
```

중복 예약을 막기 위해 트랜잭션에서 겹치는 예약을 조회하고 잠근다.

```sql
START TRANSACTION;

SELECT id
FROM reservations
WHERE room_id = 7
  AND starts_at < '2026-06-12 15:00:00'
  AND ends_at > '2026-06-12 14:00:00'
  AND status = 'CONFIRMED'
FOR UPDATE;

INSERT INTO reservations(room_id, starts_at, ends_at, status)
VALUES (7, '2026-06-12 14:00:00', '2026-06-12 15:00:00', 'CONFIRMED');

COMMIT;
```

의도는 "겹치는 예약이 있으면 막자"다. 하지만 이 방식은 조건과 인덱스가 애매하면 넓은 범위 락을 만들 수 있다. 특히 `starts_at`과 `ends_at` 양쪽 범위를 동시에 완벽하게 인덱스로 좁히기 어렵다. 동시간대 예약 요청이 많으면 락 대기가 늘고 deadlock 가능성도 커진다.

이럴 때는 모델링을 바꾸는 편이 더 안정적일 수 있다. 예를 들어 시간 슬롯을 10분 단위로 정규화하고 `(room_id, slot_start)` 유니크 키를 잡는다.

```sql
CREATE TABLE reservation_slots (
  reservation_id BIGINT NOT NULL,
  room_id BIGINT NOT NULL,
  slot_start DATETIME NOT NULL,
  PRIMARY KEY (room_id, slot_start),
  KEY idx_reservation_slots_reservation (reservation_id)
) ENGINE=InnoDB;
```

예약 생성 시 필요한 슬롯 row를 insert한다. 충돌은 유니크 키가 담당한다.

```sql
START TRANSACTION;

INSERT INTO reservations(room_id, starts_at, ends_at, status)
VALUES (7, '2026-06-12 14:00:00', '2026-06-12 15:00:00', 'CONFIRMED');

SET @reservation_id = LAST_INSERT_ID();

INSERT INTO reservation_slots(reservation_id, room_id, slot_start)
VALUES
  (@reservation_id, 7, '2026-06-12 14:00:00'),
  (@reservation_id, 7, '2026-06-12 14:10:00'),
  (@reservation_id, 7, '2026-06-12 14:20:00'),
  (@reservation_id, 7, '2026-06-12 14:30:00'),
  (@reservation_id, 7, '2026-06-12 14:40:00'),
  (@reservation_id, 7, '2026-06-12 14:50:00');

COMMIT;
```

이 설계는 저장 row 수가 늘고 슬롯 단위가 고정된다는 트레이드오프가 있다. 대신 "겹치는 범위를 조회해서 잠근다"는 복잡한 락 문제를 "동일 슬롯 유니크 키 충돌"로 바꾼다. 많은 실무 시스템에서는 이런 식으로 **범위 충돌을 키 충돌로 바꾸는 모델링**이 락 문제를 훨씬 단순하게 만든다.

---

## 핵심 개념 3: 격리 수준은 정합성과 락 범위의 교환이다

MySQL InnoDB의 기본 격리 수준은 `REPEATABLE READ`다. 같은 트랜잭션 안에서 같은 snapshot을 반복해서 읽는 성질을 제공하고, locking read에서는 phantom을 막기 위해 next-key lock을 사용한다.

반면 `READ COMMITTED`는 statement마다 새로 commit된 데이터를 읽는다. InnoDB에서는 일반적으로 gap lock 사용이 줄어든다. 그래서 일부 서비스는 온라인 API의 락 대기를 줄이기 위해 `READ COMMITTED`를 선택한다.

하지만 "락이 줄어드니까 무조건 READ COMMITTED가 좋다"는 결론은 위험하다. 격리 수준은 업무 정합성 모델과 함께 봐야 한다.

### `REPEATABLE READ`가 유리한 경우

- 같은 트랜잭션 안에서 반복 조회 결과가 안정적이어야 한다.
- 범위 조건 기반 정합성을 DB 락으로 강하게 막고 싶다.
- 기존 코드가 MySQL 기본 격리 수준을 전제로 작성되어 있다.
- 배치나 정산처럼 하나의 일관된 snapshot이 중요한 작업이 많다.

### `READ COMMITTED`가 유리한 경우

- 온라인 요청에서 불필요한 gap lock 대기가 문제가 된다.
- 애플리케이션이 명시적 유니크 키, 낙관적 잠금, idempotency로 정합성을 별도로 보장한다.
- PostgreSQL 등 다른 DB의 기본 동작에 맞춘 동시성 모델을 쓰고 있다.
- 오래 열린 트랜잭션을 줄이고, 최신 commit을 statement 단위로 보는 편이 자연스럽다.

### 격리 수준을 바꾸기 전에 확인할 질문

격리 수준 변경은 설정 한 줄 같지만 실제로는 시스템 동시성 계약 변경이다.

```sql
SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED;
```

또는 커넥션 풀 초기화 SQL에서 지정할 수도 있다.

하지만 바꾸기 전에 아래를 확인해야 한다.

- 같은 트랜잭션 안에서 같은 조회가 같은 결과를 반환해야 한다고 가정한 코드가 있는가?
- 범위 조회 후 insert하는 패턴이 유니크 제약 없이 동작하고 있지 않은가?
- 재고, 포인트, 쿠폰, 예약처럼 동시성 충돌이 금전·권한·고객 경험에 직접 영향을 주는가?
- deadlock 재시도와 lock wait timeout 재시도가 이미 안전하게 구현되어 있는가?
- ORM이나 프레임워크가 트랜잭션 격리 수준을 덮어쓰지 않는가?

개인적으로는 온라인 서비스에서 `READ COMMITTED`를 선호하는 경우가 많다. 하지만 그 전제는 "중요한 정합성은 유니크 제약, 조건부 update, 버전 컬럼, idempotency key로 명시한다"는 것이다. DB snapshot 동작에 정합성을 암묵적으로 기대하는 시스템이라면 격리 수준 변경은 위험하다.

---

## 실무 예시 1: 재고 차감은 `SELECT 후 UPDATE`보다 조건부 `UPDATE`가 단순하다

재고 차감은 동시성 설명에 자주 등장한다. 흔한 구현은 아래와 같다.

```sql
START TRANSACTION;

SELECT stock
FROM products
WHERE id = 100
FOR UPDATE;

-- 애플리케이션에서 stock >= 1 확인

UPDATE products
SET stock = stock - 1
WHERE id = 100;

COMMIT;
```

이 방식은 틀리지 않다. `FOR UPDATE`로 row를 잠그고 재고를 확인한 뒤 차감한다. 하지만 트랜잭션 안에서 애플리케이션 로직이 길어지면 잠금 점유 시간이 늘어난다. 또한 여러 상품을 한 주문에서 차감할 때 상품 row를 서로 다른 순서로 잠그면 deadlock이 생기기 쉽다.

가능하면 아래처럼 조건부 `UPDATE` 하나로 줄이는 편이 더 단순하다.

```sql
UPDATE products
SET stock = stock - 1
WHERE id = 100
  AND stock >= 1;
```

영향 row 수가 1이면 성공, 0이면 재고 부족이다.

```sql
SELECT ROW_COUNT();
```

이 방식의 장점은 명확하다.

- 읽기와 쓰기를 하나의 원자적 statement로 합친다.
- 애플리케이션이 확인한 값과 실제 update 시점 값이 어긋날 여지가 줄어든다.
- 잠금 점유 시간이 짧다.
- 실패 판단이 `affected rows`로 단순하다.

물론 여러 상품을 동시에 차감해야 한다면 여전히 트랜잭션이 필요하다. 이때는 **항상 같은 순서로 row를 잠그는 것**이 중요하다.

```sql
START TRANSACTION;

-- 상품 id 오름차순으로 정렬한 뒤 차감한다.
UPDATE products
SET stock = stock - 2
WHERE id = 100
  AND stock >= 2;

UPDATE products
SET stock = stock - 1
WHERE id = 205
  AND stock >= 1;

COMMIT;
```

트랜잭션 A는 100번 상품을 먼저 잠그고 205번을 기다리는데, 트랜잭션 B는 205번을 먼저 잠그고 100번을 기다리면 deadlock이 난다. 주문마다 상품 배열 순서가 다르면 이 문제가 쉽게 발생한다. 그래서 상품 id, 창고 id, 옵션 id 등 **잠금 순서를 결정하는 정렬 기준**을 반드시 고정해야 한다.

여기서 중요한 설계 원칙은 이것이다.

> 읽어서 판단한 뒤 쓰는 패턴은 가능하면 조건부 쓰기로 바꾸고, 여러 row를 잠글 때는 순서를 고정한다.

---

## 실무 예시 2: 중복 요청 방지는 락보다 idempotency key가 낫다

사용자가 결제 버튼을 두 번 누르거나, 네트워크 timeout 때문에 클라이언트가 같은 요청을 재시도하는 상황을 생각해 보자. 개발자는 종종 "같은 주문을 `FOR UPDATE`로 잠그면 되지 않을까?"라고 접근한다.

```sql
START TRANSACTION;

SELECT id, status
FROM orders
WHERE id = 500
FOR UPDATE;

-- status 확인 후 결제 생성

COMMIT;
```

이 방식은 주문 row의 상태 전이에는 도움이 된다. 하지만 외부 결제 API 호출까지 트랜잭션 안에 넣으면 최악이다.

```sql
START TRANSACTION;

SELECT id, status
FROM orders
WHERE id = 500
FOR UPDATE;

-- 절대 권장하지 않음: 트랜잭션 안에서 외부 결제 API 호출
-- POST https://payment.example.com/charge

UPDATE orders
SET status = 'PAID'
WHERE id = 500;

COMMIT;
```

외부 API가 3초 걸리면 주문 row 락도 3초 잡힌다. 결제사가 느려지면 DB 락 장애로 번진다. 이 문제는 락을 더 잘 잡아서 해결할 일이 아니다. 트랜잭션 경계를 다시 설계해야 한다.

더 나은 방식은 idempotency key를 별도 테이블이나 유니크 제약으로 관리하는 것이다.

```sql
CREATE TABLE payment_requests (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  order_id BIGINT NOT NULL,
  idempotency_key VARCHAR(128) NOT NULL,
  status VARCHAR(20) NOT NULL,
  payment_gateway_request_id VARCHAR(128) NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  UNIQUE KEY uk_payment_requests_key (idempotency_key),
  KEY idx_payment_requests_order (order_id)
) ENGINE=InnoDB;
```

요청 시작 시 idempotency key를 먼저 insert한다.

```sql
INSERT INTO payment_requests(
  order_id,
  idempotency_key,
  status,
  created_at,
  updated_at
)
VALUES (
  500,
  'client-generated-key-123',
  'STARTED',
  NOW(),
  NOW()
);
```

이미 같은 key가 있으면 새 결제를 만들지 않고 기존 결과를 조회한다.

```sql
SELECT id, status, payment_gateway_request_id
FROM payment_requests
WHERE idempotency_key = 'client-generated-key-123';
```

외부 결제 API 호출은 DB 트랜잭션 밖에서 수행하고, 결과 반영만 짧은 트랜잭션으로 묶는다.

```sql
START TRANSACTION;

SELECT id, status
FROM orders
WHERE id = 500
FOR UPDATE;

UPDATE orders
SET status = 'PAID',
    paid_at = NOW()
WHERE id = 500
  AND status = 'PAYMENT_PENDING';

UPDATE payment_requests
SET status = 'SUCCEEDED',
    payment_gateway_request_id = 'pgw_abc_123',
    updated_at = NOW()
WHERE idempotency_key = 'client-generated-key-123';

COMMIT;
```

이 설계의 핵심은 "중복 요청"과 "주문 상태 전이"를 분리하는 것이다.

- 중복 요청은 유니크 키로 막는다.
- 주문 상태 전이는 짧은 트랜잭션과 조건부 update로 막는다.
- 외부 API 호출은 DB 락을 잡은 채 기다리지 않는다.
- 재시도는 idempotency key 기준으로 같은 결과를 반환한다.

락은 정합성의 한 도구일 뿐이다. 특히 네트워크, 결제, 메일, 메시지 발송처럼 외부 시스템이 섞이면 락보다 idempotency와 상태 머신이 더 중요하다.

---

## 실무 예시 3: 작업 큐는 `SKIP LOCKED`만 붙인다고 완성되지 않는다

MySQL 8.0에서는 `SELECT ... FOR UPDATE SKIP LOCKED`를 사용할 수 있다. 여러 워커가 같은 테이블에서 작업을 가져갈 때 유용하다.

```sql
CREATE TABLE job_queue (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  type VARCHAR(50) NOT NULL,
  status VARCHAR(20) NOT NULL,
  priority INT NOT NULL DEFAULT 0,
  run_after DATETIME NOT NULL,
  attempts INT NOT NULL DEFAULT 0,
  locked_by VARCHAR(100) NULL,
  locked_at DATETIME NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  KEY idx_job_queue_pick (status, run_after, priority, id)
) ENGINE=InnoDB;
```

워커는 실행 가능한 작업을 잠그고 상태를 바꾼다.

```sql
START TRANSACTION;

SELECT id
FROM job_queue
WHERE status = 'PENDING'
  AND run_after <= NOW()
ORDER BY priority DESC, id ASC
LIMIT 50
FOR UPDATE SKIP LOCKED;

-- 애플리케이션이 받은 id 목록으로 상태 변경
UPDATE job_queue
SET status = 'RUNNING',
    locked_by = 'worker-01',
    locked_at = NOW(),
    updated_at = NOW()
WHERE id IN (101, 102, 103);

COMMIT;
```

`SKIP LOCKED`는 이미 다른 트랜잭션이 잠근 row를 기다리지 않고 건너뛴다. 덕분에 워커 여러 대가 동시에 작업을 가져갈 수 있다. 하지만 이것만으로 큐가 안전해지는 것은 아니다.

### 1) 인덱스가 pick 조건과 정렬을 지원해야 한다

위 쿼리의 핵심 조건은 `status`, `run_after`이고 정렬은 `priority DESC, id ASC`다. 인덱스가 맞지 않으면 MySQL은 많은 row를 읽고 정렬하면서 잠금 범위를 넓힐 수 있다.

인덱스는 워크로드에 맞춰 조정해야 한다.

```sql
CREATE INDEX idx_job_queue_pick
ON job_queue(status, run_after, priority, id);
```

만약 `type`별 워커가 나뉘어 있다면 `type`도 앞쪽에 들어가야 할 수 있다.

```sql
CREATE INDEX idx_job_queue_pick_by_type
ON job_queue(type, status, run_after, priority, id);
```

중요한 것은 `SKIP LOCKED`가 인덱스 부재를 해결해 주지 않는다는 점이다. 빠르게 건너뛰려면 빠르게 찾아야 한다.

### 2) 작업 실행은 트랜잭션 밖에서 해야 한다

큐에서 가장 위험한 구현은 작업을 실행하는 동안 row 락을 계속 잡는 것이다.

```sql
START TRANSACTION;

SELECT id
FROM job_queue
WHERE status = 'PENDING'
ORDER BY id
LIMIT 1
FOR UPDATE SKIP LOCKED;

-- 절대 권장하지 않음: 트랜잭션 안에서 실제 작업 실행
-- 이미지 변환, 외부 API 호출, 대량 계산

UPDATE job_queue
SET status = 'SUCCEEDED'
WHERE id = 101;

COMMIT;
```

올바른 패턴은 "짧게 claim하고, 밖에서 실행하고, 짧게 완료 처리"다.

```sql
START TRANSACTION;

UPDATE job_queue
SET status = 'RUNNING',
    locked_by = 'worker-01',
    locked_at = NOW(),
    attempts = attempts + 1,
    updated_at = NOW()
WHERE id = 101
  AND status = 'PENDING';

COMMIT;
```

작업 실행 후 결과만 반영한다.

```sql
UPDATE job_queue
SET status = 'SUCCEEDED',
    updated_at = NOW()
WHERE id = 101
  AND status = 'RUNNING'
  AND locked_by = 'worker-01';
```

### 3) 워커 죽음과 재처리 기준이 있어야 한다

워커가 작업을 `RUNNING`으로 바꾼 뒤 죽으면 어떻게 할까? 이 기준이 없으면 큐는 조용히 멈춘다.

```sql
UPDATE job_queue
SET status = 'PENDING',
    locked_by = NULL,
    locked_at = NULL,
    run_after = DATE_ADD(NOW(), INTERVAL 1 MINUTE),
    updated_at = NOW()
WHERE status = 'RUNNING'
  AND locked_at < DATE_SUB(NOW(), INTERVAL 10 MINUTE)
  AND attempts < 5;
```

최대 재시도 횟수를 넘으면 실패 상태로 보낸다.

```sql
UPDATE job_queue
SET status = 'FAILED',
    updated_at = NOW()
WHERE status = 'RUNNING'
  AND locked_at < DATE_SUB(NOW(), INTERVAL 10 MINUTE)
  AND attempts >= 5;
```

작업 큐에서 핵심은 락이 아니라 상태 전이다. `PENDING -> RUNNING -> SUCCEEDED/FAILED`의 전이가 조건부 update로 보호되어야 하고, 작업 자체는 재실행 가능해야 한다.

---

## Deadlock은 왜 생기고, 왜 애플리케이션이 재시도해야 하는가

Deadlock은 두 트랜잭션이 서로의 락을 기다리는 순환 대기다.

가장 단순한 예시는 이렇다.

```sql
-- Transaction A
START TRANSACTION;
UPDATE accounts SET balance = balance - 100 WHERE id = 1;
UPDATE accounts SET balance = balance + 100 WHERE id = 2;
COMMIT;
```

```sql
-- Transaction B
START TRANSACTION;
UPDATE accounts SET balance = balance - 50 WHERE id = 2;
UPDATE accounts SET balance = balance + 50 WHERE id = 1;
COMMIT;
```

A는 1번 계좌를 잠근 뒤 2번을 기다리고, B는 2번 계좌를 잠근 뒤 1번을 기다린다. InnoDB는 deadlock을 감지하고 둘 중 하나를 victim으로 골라 rollback한다. 애플리케이션은 오류를 받는다.

중요한 점은 deadlock이 항상 "개발자가 말도 안 되는 코드를 작성했다"는 뜻은 아니라는 것이다. 동시성 시스템에서는 정상적인 부하에서도 발생할 수 있다. 특히 다음 조건이 겹치면 확률이 올라간다.

- 여러 row를 한 트랜잭션에서 갱신한다.
- row 접근 순서가 요청마다 다르다.
- 범위 update/delete가 많다.
- 보조 인덱스와 primary key를 오가며 잠금이 발생한다.
- 외래 키 cascade나 trigger가 추가 row를 잠근다.
- 트랜잭션 안에서 긴 작업을 수행한다.
- 인덱스가 부족해 많은 row를 스캔하며 잠근다.

### Deadlock을 줄이는 설계 원칙

첫 번째 원칙은 **잠금 순서 고정**이다. 계좌 이체라면 작은 account id부터 잠근다.

```sql
START TRANSACTION;

SELECT id
FROM accounts
WHERE id IN (1, 2)
ORDER BY id
FOR UPDATE;

UPDATE accounts
SET balance = balance - 100
WHERE id = 1;

UPDATE accounts
SET balance = balance + 100
WHERE id = 2;

COMMIT;
```

두 번째 원칙은 **트랜잭션을 짧게 유지**하는 것이다. 락 점유 시간이 짧으면 순환 대기가 생길 창도 줄어든다.

세 번째 원칙은 **범위 갱신을 청크로 나누는 것**이다.

```sql
UPDATE user_events
SET archived = 1
WHERE archived = 0
  AND created_at < DATE_SUB(NOW(), INTERVAL 90 DAY)
ORDER BY id
LIMIT 1000;
```

이 쿼리를 루프로 반복하되 각 청크마다 commit한다. 하나의 거대한 transaction으로 수십만 row를 바꾸면 undo, redo, lock, replication lag까지 한 번에 커진다.

네 번째 원칙은 **정확한 인덱스로 대상 row를 빠르게 찾는 것**이다. deadlock은 "수정 대상 row 수"뿐 아니라 "대상을 찾기 위해 건드리는 row 수"에도 영향을 받는다.

### Deadlock 재시도는 필수다

InnoDB는 deadlock victim 트랜잭션을 rollback한다. 이때 애플리케이션은 전체 트랜잭션을 처음부터 다시 실행해야 한다. 단순히 마지막 SQL만 재실행하면 안 된다. 트랜잭션 안에서 읽은 값과 판단이 모두 무효가 되었기 때문이다.

재시도 정책은 대략 아래처럼 둔다.

- deadlock 오류는 짧은 backoff 후 전체 트랜잭션 재시도
- lock wait timeout은 원인에 따라 재시도하되 무한 반복 금지
- 유니크 키 충돌은 재시도보다 비즈니스 결과로 해석
- 외부 API 호출이 섞인 트랜잭션은 재시도 전에 idempotency 보장
- 최대 재시도 횟수 초과 시 사용자에게 명확한 실패 반환 또는 큐 재처리

애플리케이션 의사코드로 보면 이런 구조다.

```text
for attempt in 1..max_attempts:
    try:
        begin transaction
        execute business reads and writes
        commit
        return success
    catch deadlock:
        rollback
        sleep(jittered_backoff(attempt))
        continue
    catch lock_wait_timeout:
        rollback
        if retryable:
            sleep(jittered_backoff(attempt))
            continue
        return failure
```

재시도에는 jitter가 필요하다. 모든 요청이 같은 시간에 즉시 재시도하면 방금 발생한 충돌을 다시 만든다.

그리고 가장 중요한 조건이 있다. **재시도 가능한 트랜잭션은 부작용이 재실행되어도 안전해야 한다.** 메일 발송, 결제 승인, 외부 API 호출, 파일 생성이 트랜잭션 중간에 있다면 deadlock 재시도가 중복 부작용으로 이어진다. 그래서 외부 부작용은 outbox, idempotency key, 상태 머신으로 분리해야 한다.

---

## Lock wait timeout은 deadlock과 다르게 다뤄야 한다

Deadlock은 InnoDB가 순환 대기를 감지해서 한쪽을 중단한 것이다. 반면 lock wait timeout은 어떤 락을 기다리다 `innodb_lock_wait_timeout` 시간까지 못 얻은 것이다.

```sql
SHOW VARIABLES LIKE 'innodb_lock_wait_timeout';
```

기본값은 운영 환경에 따라 너무 길게 느껴질 수 있다. 온라인 API에서 50초 동안 DB 락을 기다리는 것은 대부분 의미가 없다. 상위 HTTP timeout은 이미 끝났을 가능성이 크다.

하지만 `innodb_lock_wait_timeout`을 전역으로 아주 짧게 줄이는 것도 조심해야 한다. 배치, 마이그레이션, 관리자 작업까지 영향을 받는다. 실무에서는 다음 레이어를 함께 쓴다.

- 애플리케이션 DB call timeout
- 트랜잭션별 업무 timeout
- MySQL `innodb_lock_wait_timeout`
- 커넥션 풀 checkout timeout
- API gateway/request timeout

중요한 것은 시간 예산의 순서다. 사용자 요청이 2초 안에 끝나야 한다면 DB 락 대기를 30초 허용할 이유가 없다. 반면 백그라운드 정산 배치는 짧은 락 대기보다 안정적인 완료가 더 중요할 수 있다.

세션 단위로 조정할 수도 있다.

```sql
SET SESSION innodb_lock_wait_timeout = 3;
```

마이그레이션에서는 락을 오래 기다리지 않도록 더 짧게 둘 수 있다.

```sql
SET SESSION innodb_lock_wait_timeout = 1;

ALTER TABLE orders
ADD COLUMN risk_score INT NULL;
```

이렇게 하면 온라인 트래픽이 잡고 있는 락 때문에 DDL이 오래 대기하며 뒤쪽 요청을 막는 상황을 줄일 수 있다. 실패하면 낮은 트래픽 시간에 다시 시도하거나 온라인 스키마 변경 도구를 검토한다.

다만 timeout은 해결책이 아니라 손상 반경 제한 장치다. lock wait timeout이 자주 발생한다면 근본 원인은 따로 봐야 한다.

- 트랜잭션이 너무 길다.
- 인덱스가 부족해 잠금 범위가 넓다.
- 배치가 온라인 row를 큰 단위로 갱신한다.
- DDL이 피크 시간에 실행된다.
- 애플리케이션이 트랜잭션을 열어 둔 채 네트워크 호출을 한다.
- 같은 hot row에 모든 요청이 몰린다.

---

## 운영 관측: 지금 누가 누구를 기다리는지 봐야 한다

락 장애를 해결하려면 "느린 쿼리"만 봐서는 부족하다. 누가 락을 잡고 있고, 누가 기다리는지 봐야 한다.

MySQL 8.0에서는 `performance_schema`를 활용할 수 있다.

```sql
SELECT
  r.trx_id AS waiting_trx_id,
  r.trx_mysql_thread_id AS waiting_thread,
  r.trx_query AS waiting_query,
  b.trx_id AS blocking_trx_id,
  b.trx_mysql_thread_id AS blocking_thread,
  b.trx_query AS blocking_query
FROM information_schema.innodb_lock_waits w
JOIN information_schema.innodb_trx b
  ON b.trx_id = w.blocking_trx_id
JOIN information_schema.innodb_trx r
  ON r.trx_id = w.requesting_trx_id;
```

환경에 따라 `sys` schema의 helper view가 더 편할 수 있다.

```sql
SELECT *
FROM sys.innodb_lock_waits
ORDER BY wait_age DESC;
```

현재 트랜잭션을 보는 기본 쿼리도 자주 쓴다.

```sql
SELECT
  trx_id,
  trx_state,
  trx_started,
  TIMESTAMPDIFF(SECOND, trx_started, NOW()) AS trx_age_seconds,
  trx_mysql_thread_id,
  trx_rows_locked,
  trx_rows_modified,
  trx_query
FROM information_schema.innodb_trx
ORDER BY trx_started;
```

오래 열린 트랜잭션은 락뿐 아니라 purge 지연, undo 증가, replication lag에도 영향을 줄 수 있다. 특히 `trx_query`가 NULL인데 트랜잭션이 오래 살아 있다면 애플리케이션이 transaction을 열고 idle 상태로 방치했을 가능성이 있다.

Deadlock 분석에는 아래 명령이 여전히 유용하다.

```sql
SHOW ENGINE INNODB STATUS\G
```

여기서 `LATEST DETECTED DEADLOCK` 섹션을 확인한다. 단, 마지막 deadlock 하나만 보여준다는 한계가 있으므로 운영에서는 MySQL error log, 모니터링 수집, 애플리케이션 로그의 transaction id/request id 연결이 필요하다.

관측에서 중요한 지표는 아래와 같다.

- lock wait 발생 횟수와 p95/p99 대기 시간
- deadlock 발생 횟수와 대상 쿼리
- 장기 트랜잭션 수와 최대 수명
- row lock time, row lock waits
- hot table/hot index별 대기 분포
- 배치 실행 시간대와 온라인 API 지연 상관관계
- 재시도 성공률과 최종 실패율

락 이슈는 보통 특정 SQL 하나가 아니라 업무 흐름으로 봐야 한다. "이 쿼리가 느리다"가 아니라 "이 결제 요청이 어떤 순서로 어떤 row를 잠그는가"를 추적해야 한다.

---

## 트레이드오프: 강한 정합성, 낮은 대기, 높은 처리량을 동시에 공짜로 얻을 수는 없다

동시성 설계에는 항상 교환이 있다.

### 1) 비관적 락 vs 낙관적 락

비관적 락은 먼저 잠그고 진행한다.

```sql
SELECT id, version, status
FROM orders
WHERE id = 500
FOR UPDATE;
```

장점은 충돌을 일찍 막고 구현이 직관적이라는 점이다. 단점은 락 대기와 deadlock 가능성이 커진다는 점이다.

낙관적 락은 version 조건으로 충돌을 감지한다.

```sql
UPDATE orders
SET status = 'PAID',
    version = version + 1
WHERE id = 500
  AND version = 7
  AND status = 'PAYMENT_PENDING';
```

장점은 락 대기가 줄고 처리량이 좋다는 점이다. 단점은 충돌 시 재조회와 사용자 경험 설계가 필요하다는 점이다.

실무 기준은 이렇다.

- 충돌이 드물고 사용자 편집이 많은 화면: 낙관적 락
- 금전, 재고, 쿠폰처럼 실패 비용이 큰 상태 전이: 조건부 update 또는 짧은 비관적 락
- 여러 row를 반드시 함께 바꿔야 하는 업무: 비관적 락 + 순서 고정 + 재시도
- 외부 API가 섞인 업무: idempotency + 상태 머신 + 짧은 DB 트랜잭션

### 2) `REPEATABLE READ` vs `READ COMMITTED`

`REPEATABLE READ`는 snapshot 안정성과 phantom 방지에 유리하지만 범위 락이 커질 수 있다. `READ COMMITTED`는 gap lock 부담이 줄 수 있지만 statement마다 보이는 데이터가 달라질 수 있다.

어느 쪽이 정답인지는 서비스 성격에 따라 다르다. 중요한 것은 격리 수준으로 정합성을 "우연히" 얻지 않는 것이다. 핵심 정합성은 유니크 제약, foreign key, 조건부 update, version, idempotency로 명시해야 한다.

### 3) 하나의 DB 큐 vs 전용 메시지 브로커

MySQL 테이블 큐는 운영이 단순하고 트랜잭션 데이터와 가까워서 작은 시스템에 좋다. 하지만 처리량이 커지고 지연 요구사항이 엄격해지면 Kafka, RabbitMQ, SQS 같은 전용 큐가 더 적합할 수 있다.

DB 큐의 장점:

- 별도 인프라가 없다.
- 업무 데이터와 같은 트랜잭션으로 claim 가능하다.
- 운영자가 SQL로 상태를 확인하고 보정하기 쉽다.

DB 큐의 단점:

- hot index와 lock contention이 생기기 쉽다.
- 대량 polling이 DB 부하로 이어진다.
- retry, delay, priority, fanout이 복잡해질수록 직접 구현이 늘어난다.
- primary DB의 온라인 트래픽과 자원을 공유한다.

처음에는 DB 큐로 충분할 수 있다. 하지만 큐 테이블이 주요 장애 원인이 되기 시작하면 전용 브로커나 outbox 패턴으로 분리하는 시점을 검토해야 한다.

---

## 흔한 실수

### 1) `FOR UPDATE`를 "안전 버튼"처럼 붙인다

`FOR UPDATE`는 읽은 row를 나중에 수정할 의도가 있을 때 쓰는 도구다. 단순 조회, 화면 표시, 검증용 조회에 습관적으로 붙이면 처리량만 낮아진다.

특히 list API에 `FOR UPDATE`가 붙어 있으면 위험하다.

```sql
SELECT *
FROM orders
WHERE status = 'PENDING'
ORDER BY created_at
LIMIT 100
FOR UPDATE;
```

이 쿼리가 사용자 화면 조회인지, 워커 claim인지에 따라 의미가 완전히 다르다. 화면 조회라면 락이 필요 없다. 워커 claim이라면 상태 전이와 `SKIP LOCKED`, 재처리 기준까지 있어야 한다.

### 2) 트랜잭션 안에서 외부 API를 호출한다

DB 락을 잡은 채 결제사, 메일 서버, 파일 스토리지, 다른 마이크로서비스를 호출하면 외부 지연이 DB 장애로 전파된다. 외부 호출은 트랜잭션 밖으로 빼고, 결과 반영만 짧게 묶어야 한다.

### 3) 인덱스 없는 조건으로 update/delete한다

```sql
UPDATE orders
SET status = 'EXPIRED'
WHERE status = 'PENDING'
  AND expires_at < NOW();
```

이 쿼리에 `(status, expires_at)` 인덱스가 없으면 많은 row를 훑고 잠글 수 있다. 배치라면 청크 처리와 인덱스가 필수다.

```sql
UPDATE orders
SET status = 'EXPIRED'
WHERE status = 'PENDING'
  AND expires_at < NOW()
ORDER BY id
LIMIT 1000;
```

하지만 이 경우에도 조건을 지원하는 인덱스가 없다면 매번 비싼 탐색을 반복한다. 청크는 인덱스를 대체하지 않는다.

### 4) Deadlock을 "없어야 하는 오류"로 취급한다

Deadlock은 줄여야 하지만 0을 보장하기 어렵다. 애플리케이션에 재시도 정책이 없으면 작은 충돌도 사용자 오류가 된다. 반대로 무조건 무한 재시도하면 장애를 증폭한다. 제한된 횟수, jittered backoff, idempotency가 필요하다.

### 5) Hot row를 만든다

전역 카운터, 단일 설정 row, 하나의 재고 row, 하나의 큐 메타 row에 모든 요청이 몰리면 어떤 DB도 힘들다.

예를 들어 조회수 카운터를 매 요청마다 같은 row에 update하면 hot row가 된다.

```sql
UPDATE article_stats
SET view_count = view_count + 1
WHERE article_id = 10;
```

트래픽이 높다면 버퍼링, 샤딩된 카운터, 비동기 집계, Redis 임시 카운터 등으로 충돌 지점을 분산해야 한다.

### 6) `LOCK TABLES`로 문제를 단순화하려 한다

테이블 락은 작은 운영 스크립트에서는 유용할 때가 있지만 온라인 서비스의 일반 동시성 제어 수단으로는 너무 크다. 대부분의 경우 row-level 설계, 유니크 제약, 조건부 update, 배치 청크가 먼저다.

### 7) 락 대기 로그와 request id를 연결하지 않는다

DB에서 blocking query를 봐도 어떤 API 요청인지 모르면 해결이 늦다. 애플리케이션 로그에 request id, transaction boundary, 주요 SQL 이름, 재시도 횟수를 남겨야 한다. SQL 전체를 모두 남기지 않더라도 "어떤 업무 흐름이 어떤 테이블을 잠갔는지"는 추적 가능해야 한다.

---

## 실무 설계 체크리스트

### 모델링

- [ ] 범위 충돌을 유니크 키 충돌로 바꿀 수 있는가?
- [ ] hot row가 생기는 구조는 아닌가?
- [ ] 상태 전이가 명확한 enum/state machine으로 표현되어 있는가?
- [ ] 중복 요청은 idempotency key로 식별되는가?
- [ ] 재시도 가능한 작업과 재시도하면 안 되는 외부 부작용이 분리되어 있는가?

### 인덱스

- [ ] `FOR UPDATE`, `UPDATE`, `DELETE` 조건이 적절한 인덱스를 타는가?
- [ ] 범위 조건과 정렬이 같은 복합 인덱스로 지원되는가?
- [ ] 배치 청크 쿼리가 매번 full scan하지 않는가?
- [ ] 큐 pick 쿼리의 `WHERE`, `ORDER BY`, `LIMIT`이 인덱스와 맞는가?
- [ ] 유니크 제약으로 막아야 할 정합성을 애플리케이션 조회로만 막고 있지 않은가?

### 트랜잭션

- [ ] 트랜잭션 안에서 외부 API, 파일 I/O, 긴 계산을 하지 않는가?
- [ ] 여러 row를 잠글 때 항상 같은 순서로 잠그는가?
- [ ] 사용자 입력 대기나 네트워크 대기가 열린 transaction 안에 들어가지 않는가?
- [ ] 읽고 판단한 뒤 쓰는 패턴을 조건부 update로 줄일 수 있는가?
- [ ] 격리 수준 변경이 업무 정합성 가정을 깨지 않는가?

### 재시도

- [ ] deadlock 발생 시 전체 트랜잭션을 재시도하는가?
- [ ] 재시도에는 최대 횟수와 jittered backoff가 있는가?
- [ ] lock wait timeout과 deadlock을 같은 방식으로 뭉뚱그리지 않는가?
- [ ] 재시도 중 외부 결제, 메일, 메시지 발송이 중복되지 않는가?
- [ ] 최종 실패 시 사용자나 큐에 어떤 상태를 남길지 정의되어 있는가?

### 운영

- [ ] `information_schema.innodb_trx`, `sys.innodb_lock_waits`를 볼 수 있는가?
- [ ] deadlock 로그를 수집하고 최근 사례를 추적하는가?
- [ ] 장기 트랜잭션과 idle transaction을 알림으로 잡는가?
- [ ] 배치 실행 시간과 온라인 API 지연을 함께 보는가?
- [ ] 마이그레이션은 짧은 lock wait timeout 또는 온라인 스키마 변경 전략을 쓰는가?

---

## 한줄 정리

MySQL InnoDB 동시성 장애를 줄이는 핵심은 `FOR UPDATE`를 많이 쓰는 것이 아니라, **정확한 인덱스로 잠금 범위를 좁히고, 트랜잭션을 짧게 유지하며, deadlock을 안전하게 재시도할 수 있는 업무 구조를 만드는 것**이다.
