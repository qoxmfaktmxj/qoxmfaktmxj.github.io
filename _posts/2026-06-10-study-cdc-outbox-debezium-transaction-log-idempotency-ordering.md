---
layout: post
title: "CDC Outbox 실전: Debezium, Transaction Log, Idempotency, Ordering으로 데이터 변경 이벤트를 안전하게 발행하는 법"
date: 2026-06-10 11:50:00 +0900
categories: [data-infra]
tags: [study, data-infra, cdc, outbox, debezium, kafka, transaction-log, idempotency, ordering, schema, operations]
permalink: /data-infra/2026/06/10/study-cdc-outbox-debezium-transaction-log-idempotency-ordering.html
---

## 배경: "DB 저장 후 Kafka 발행"은 가장 쉬운 코드이지만 가장 위험한 경계다

주문 서비스에서 결제가 완료되면 보통 두 가지 일이 필요하다.

- `orders` 테이블의 상태를 `PAID`로 바꾼다
- 다른 서비스가 알 수 있도록 `OrderPaid` 이벤트를 발행한다

처음에는 아래처럼 코드를 짠다.

```java
@Transactional
public void pay(String orderId) {
    Order order = orderRepository.findById(orderId);
    order.markPaid();
    orderRepository.save(order);

    kafkaTemplate.send("order-events", new OrderPaid(orderId));
}
```

겉보기에는 자연스럽다. 데이터베이스도 바뀌고 Kafka 이벤트도 나간다. 하지만 운영 환경에서 이 코드는 생각보다 쉽게 깨진다.

- DB 커밋은 성공했는데 Kafka 발행 직전에 프로세스가 죽는다
- Kafka 발행은 성공했는데 DB 트랜잭션이 롤백된다
- 네트워크 타임아웃 때문에 발행 성공 여부를 모른다
- 재시도 로직 때문에 같은 이벤트가 두 번 발행된다
- 소비자는 이벤트를 받았는데 원본 DB에는 아직 커밋이 보이지 않는다
- 여러 aggregate 변경 이벤트의 순서가 뒤집힌다
- 배포 중 producer 설정이 바뀌며 일부 이벤트만 다른 스키마로 나간다
- 장애 복구 후 누락된 이벤트를 사람이 SQL로 찾아 재발행한다

이 문제는 단순한 Kafka 사용법 문제가 아니다. 더 본질적으로는 **데이터베이스 트랜잭션과 메시지 브로커 발행 사이에 원자성이 없다는 문제**다.

분산 트랜잭션이나 2PC로 풀 수 있다고 생각할 수도 있다. 하지만 대부분의 현대 서비스 환경에서는 Kafka, RDB, 마이크로서비스, 클라우드 운영 조건을 모두 만족하는 실용적인 2PC를 도입하기 어렵다. 설령 가능하더라도 장애 모드, 성능, 운영 복잡도, 팀 이해 비용이 커진다.

그래서 실무에서는 다른 접근을 쓴다.

> **비즈니스 데이터 변경과 이벤트 발행 의도를 같은 DB 트랜잭션에 기록한 뒤, 별도 프로세스가 트랜잭션 로그를 읽어 메시지 브로커로 내보낸다.**

이 패턴이 바로 Outbox와 CDC(Change Data Capture)의 결합이다.

오늘 글은 "Debezium을 설치하는 법"이나 "Kafka Connect 설정 예제"에서 멈추지 않는다. 중급 이상 개발자가 운영 설계 단계에서 실제로 답해야 하는 질문을 기준으로 정리한다.

1. Outbox 패턴은 어떤 장애 경계를 없애고 어떤 새 책임을 만드는가
2. CDC는 왜 polling publisher보다 운영적으로 유리한가
3. Debezium은 트랜잭션 로그, snapshot, offset, connector task를 어떤 방식으로 다루는가
4. 이벤트 순서, 중복, idempotency는 어디까지 보장되고 어디서 애플리케이션 책임이 되는가
5. outbox 테이블 스키마는 어떤 필드를 가져야 운영이 편해지는가
6. Kafka 토픽, key, partition, schema registry, DLQ를 어떻게 연결해야 하는가
7. 흔한 실수는 무엇이고, 배포 전에 어떤 체크리스트를 봐야 하는가

결론부터 말하면 이렇다.

**CDC Outbox의 목표는 "이벤트를 한 번만 발행한다"가 아니라, 비즈니스 상태 변경과 이벤트 발행 의도를 같은 커밋 단위에 묶고, 이후 단계의 중복과 지연을 관측 가능한 운영 문제로 바꾸는 것이다.**

이 관점이 중요하다. Outbox를 도입했다고 exactly-once 비즈니스 처리가 자동으로 완성되는 것은 아니다. 대신 가장 위험한 구멍, 즉 "DB는 바뀌었는데 이벤트 의도 자체가 사라지는 문제"를 제거한다. 그 다음부터는 중복 허용, 멱등 처리, 순서 기준, 재처리 전략을 명시적으로 설계해야 한다.

---

## 먼저 큰 그림: Outbox는 메시지를 보내는 코드가 아니라 트랜잭션 경계 설계다

Outbox의 기본 구조는 단순하다.

```text
Application Transaction
  1. business table 변경
  2. outbox table에 event row INSERT
  3. COMMIT

Publisher or CDC
  4. outbox 변경을 감지
  5. Kafka topic으로 publish
  6. consumer가 처리
```

핵심은 1번과 2번이 같은 데이터베이스 트랜잭션 안에 있다는 점이다.

```sql
BEGIN;

UPDATE orders
   SET status = 'PAID',
       paid_at = now()
 WHERE order_id = 'order-100';

INSERT INTO outbox_events (
    event_id,
    aggregate_type,
    aggregate_id,
    event_type,
    event_version,
    payload,
    occurred_at
) VALUES (
    'evt-900',
    'Order',
    'order-100',
    'OrderPaid',
    1,
    '{"orderId":"order-100","paidAt":"2026-06-10T11:49:59+09:00"}',
    now()
);

COMMIT;
```

이렇게 하면 DB 커밋 관점에서 두 가지는 함께 성공하거나 함께 실패한다.

- 주문 상태가 `PAID`로 바뀌었다
- `OrderPaid` 이벤트를 발행해야 한다는 사실이 저장되었다

여기서 중요한 표현은 "이벤트가 발행되었다"가 아니라 **"발행해야 한다는 사실이 저장되었다"**다. Outbox 테이블은 브로커가 아니다. Outbox는 발행 의도를 잃지 않기 위한 내구성 있는 기록이다.

### 직접 발행 방식의 근본 문제

애플리케이션이 DB와 Kafka를 동시에 다루면 다음 경계가 생긴다.

```text
DB transaction commit  <---- 위험한 간극 ----> Kafka publish ack
```

이 간극에서는 어떤 순서를 택해도 문제가 남는다.

DB를 먼저 커밋하고 Kafka를 나중에 발행하면:

- Kafka 발행 실패 시 DB 변경만 남는다
- 재시도 큐가 별도로 필요하다
- 누락 이벤트를 찾기 어렵다

Kafka를 먼저 발행하고 DB를 나중에 커밋하면:

- consumer가 아직 커밋되지 않은 상태를 참조할 수 있다
- DB 롤백 시 존재하지 않는 비즈니스 이벤트가 외부로 나간다
- 보상 이벤트나 취소 이벤트가 필요해진다

두 시스템을 하나의 원자적 커밋으로 묶지 않는 이상 이 문제는 사라지지 않는다. Outbox는 이 간극을 없애는 것이 아니라, 가장 중요한 원자성을 DB 내부로 끌어들인다.

```text
business change + publish intent  --same DB commit-->
CDC publisher                    --eventual delivery-->
Kafka
```

즉 Outbox는 "Kafka 발행 성공까지 같은 트랜잭션으로 보장"하는 패턴이 아니다. **비즈니스 변경과 발행 의도 저장을 같은 트랜잭션으로 보장**하는 패턴이다.

---

## 핵심 개념 1: CDC는 outbox row를 조회하는 배치가 아니라 트랜잭션 로그를 따라가는 방식이다

Outbox row를 Kafka로 보내는 방법은 크게 두 가지다.

1. 애플리케이션 또는 별도 worker가 outbox 테이블을 polling한다
2. Debezium 같은 CDC 도구가 DB transaction log를 읽는다

둘 다 가능하다. 하지만 운영 요구가 커질수록 CDC 방식이 더 자주 선택된다.

### Polling publisher 방식

Polling 방식은 단순하다.

```sql
SELECT *
  FROM outbox_events
 WHERE published_at IS NULL
 ORDER BY occurred_at
 LIMIT 100;
```

worker가 이 row들을 읽어 Kafka에 발행하고, 성공하면 `published_at`을 찍거나 상태를 변경한다.

장점:

- 이해하기 쉽다
- 별도 Kafka Connect나 Debezium 운영이 필요 없다
- 작은 서비스에서는 빠르게 시작할 수 있다
- 발행 성공 표시, retry count, error message를 테이블에서 직접 관리하기 쉽다

하지만 단점도 뚜렷하다.

- 테이블 polling 부하가 생긴다
- 잠금과 동시 worker 제어가 필요하다
- `published_at` 업데이트 때문에 outbox 테이블 write가 한 번 더 생긴다
- 발행 성공 후 상태 업데이트 실패 같은 새 경계가 생긴다
- row 정리, index bloat, long transaction 영향까지 DB 운영 이슈가 커진다
- 높은 처리량에서는 batch size, skip locked, retry backoff, vacuum까지 설계해야 한다

Polling이 나쁘다는 뜻은 아니다. 다만 polling은 단순해 보이는 대신, outbox 테이블 자체를 작업 큐처럼 운영해야 한다. 이때 RDB는 메시지 브로커가 아니므로 큐 처리량, 재시도, lease, visibility timeout 같은 기능을 직접 조립하게 된다.

### CDC 방식

CDC 방식은 outbox 테이블을 직접 계속 조회하는 대신, DB의 변경 로그를 읽는다.

- PostgreSQL: WAL
- MySQL: binlog
- SQL Server: transaction log 기반 CDC
- Oracle: redo log 계열

Debezium은 이 로그를 읽어 row-level change event를 만들고 Kafka로 보낸다. Outbox 패턴과 결합하면 outbox 테이블에 insert된 row가 곧 Kafka 이벤트의 원천이 된다.

```text
Application
  -> INSERT outbox_events
  -> COMMIT

DB transaction log
  -> committed INSERT record

Debezium connector
  -> read log position
  -> produce Kafka event
  -> store connector offset
```

CDC의 운영상 장점은 다음이다.

- 커밋된 변경만 읽는다
- DB 테이블 polling 부하가 줄어든다
- 발행 여부를 표시하기 위해 outbox row를 다시 update하지 않아도 된다
- transaction log의 순서 정보를 활용할 수 있다
- 여러 서비스의 CDC 파이프라인을 표준화하기 쉽다
- 장애 후 connector offset부터 이어 읽는 모델을 만들 수 있다

하지만 CDC도 공짜는 아니다.

- Debezium과 Kafka Connect 운영이 필요하다
- connector offset, snapshot, schema change 이벤트를 이해해야 한다
- DB log retention 설정이 맞지 않으면 connector가 따라잡지 못한다
- outbox 테이블 정리 정책이 필요하다
- 메시지 중복 가능성을 여전히 다뤄야 한다
- DB별 transaction log semantics 차이를 알아야 한다

정리하면, Polling은 애플리케이션 안에 큐 운영 책임을 가져오는 방식이고, CDC는 DB 변경 로그와 Kafka Connect 운영 책임을 가져오는 방식이다. 중대형 시스템에서는 CDC가 더 표준화되기 쉽지만, "도구가 더 고급이니 자동으로 안전하다"는 식으로 접근하면 오히려 장애가 커진다.

---

## 핵심 개념 2: Debezium은 커밋된 변경을 읽지만 비즈니스 exactly-once를 보장하지 않는다

Debezium을 도입할 때 가장 위험한 오해가 있다.

> "CDC니까 DB 변경이 Kafka에 exactly-once로 들어가겠지."

운영 관점에서는 이 표현이 너무 거칠다. Debezium은 DB 로그 위치와 Kafka Connect offset을 관리하며 변경 이벤트를 발행한다. 하지만 장애 시점, producer ack, offset flush, connector restart, Kafka broker 장애가 얽히면 consumer 입장에서는 중복을 볼 수 있다.

더 정확히 말하면 다음에 가깝다.

- Debezium은 커밋된 DB 변경을 순서대로 읽으려 한다
- connector는 읽은 log position을 offset으로 저장한다
- Kafka 발행과 offset 저장 사이에는 장애 경계가 있다
- 따라서 중복 이벤트는 가능하다고 보고 설계해야 한다
- 누락은 connector와 log retention, offset 관리가 정상이라면 피할 수 있지만, 운영 실수로는 충분히 발생할 수 있다

즉 CDC Outbox의 안정성은 "중복이 절대 없다"가 아니라 **누락 가능성을 줄이고, 중복을 명시적으로 처리 가능한 형태로 만든다**에 있다.

### Debezium 이벤트의 핵심 요소

Debezium이 만드는 이벤트에는 보통 다음 계층의 정보가 들어간다.

- 변경 전/후 row 값
- operation type: create/update/delete/read
- source metadata: database, table, log position, transaction id 등
- timestamp
- schema 정보

Outbox Event Router 같은 Debezium SMT를 쓰면 이 row change event를 애플리케이션 이벤트 형태로 변환할 수 있다.

예를 들어 outbox row가 아래처럼 저장되어 있다고 하자.

```json
{
  "event_id": "evt-900",
  "aggregate_type": "Order",
  "aggregate_id": "order-100",
  "event_type": "OrderPaid",
  "payload": {
    "orderId": "order-100",
    "paidAt": "2026-06-10T11:49:59+09:00"
  }
}
```

SMT를 적용하면 Kafka message는 대략 아래처럼 설계할 수 있다.

```text
topic: order.events
key: order-100
headers:
  event_id: evt-900
  event_type: OrderPaid
  aggregate_type: Order
  event_version: 1
value:
  {"orderId":"order-100","paidAt":"2026-06-10T11:49:59+09:00"}
```

이렇게 하면 consumer는 Debezium 내부 envelope에 강하게 결합되지 않고 비즈니스 이벤트를 받을 수 있다. 반대로 envelope를 그대로 노출하면 downstream consumer들이 CDC 도구의 내부 형식에 묶인다.

### Snapshot을 무시하면 첫 부팅부터 사고가 난다

Debezium connector를 처음 붙이면 snapshot 문제가 생긴다.

이미 outbox 테이블에 과거 row가 있는데 connector가 처음 시작하면 어떻게 할 것인가?

- 기존 outbox row를 전부 이벤트로 내보낼 것인가
- 지금 이후 insert만 볼 것인가
- 특정 시점 이후 row만 볼 것인가
- snapshot 중 애플리케이션이 새 row를 insert하면 순서는 어떻게 되는가

Outbox 테이블은 일반 CDC 대상 테이블과 성격이 다르다. 오래된 outbox row는 이미 발행되었거나 더 이상 발행하면 안 되는 과거 이벤트일 수 있다. 그런데 connector snapshot을 잘못 잡으면 과거 이벤트가 대량 재발행될 수 있다.

실무 기준은 보통 다음 중 하나다.

1. **새 outbox 테이블로 시작한다.** connector를 붙이기 전 테이블을 비워두고 이후 이벤트만 흘린다.
2. **snapshot mode를 명확히 제한한다.** 기존 데이터는 읽지 않고 이후 변경만 읽도록 한다.
3. **과거 row 재발행을 의도한다면 event_id 기반 멱등성을 먼저 보장한다.**
4. **마이그레이션 기간에는 dual-write 결과를 검증하고 cutover 시점을 기록한다.**

여기서 "일단 켜보고 중복 나오면 consumer가 알아서 처리하겠지"는 위험하다. 재고 차감, 포인트 적립, 알림 발송처럼 외부 부작용이 있는 consumer는 중복 이벤트 한 번으로도 사용자 피해를 만들 수 있다.

---

## 핵심 개념 3: Outbox 테이블은 로그가 아니라 운영 계약이다

Outbox 테이블을 단순히 `id`, `payload`, `created_at` 정도로 만들면 처음에는 돌아간다. 하지만 장애 분석, 재처리, 스키마 진화, 라우팅, 멱등 처리가 시작되면 필드 부족이 바로 드러난다.

실무에서 자주 쓰는 기본 형태는 아래와 같다.

```sql
CREATE TABLE outbox_events (
    event_id        uuid PRIMARY KEY,
    aggregate_type  varchar(100) NOT NULL,
    aggregate_id    varchar(200) NOT NULL,
    event_type      varchar(100) NOT NULL,
    event_version   integer NOT NULL,
    occurred_at     timestamptz NOT NULL,
    payload         jsonb NOT NULL,
    trace_id        varchar(100),
    causation_id    uuid,
    correlation_id  uuid,
    producer        varchar(100) NOT NULL,
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_outbox_aggregate
    ON outbox_events (aggregate_type, aggregate_id, occurred_at);

CREATE INDEX idx_outbox_created_at
    ON outbox_events (created_at);
```

필드별 의미를 운영 관점에서 보면 더 선명하다.

### `event_id`

전역적으로 유일한 이벤트 식별자다. consumer idempotency의 핵심 키가 된다.

```sql
CREATE TABLE processed_events (
    consumer_name varchar(100) NOT NULL,
    event_id uuid NOT NULL,
    processed_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (consumer_name, event_id)
);
```

consumer는 처리 전에 이 테이블에 insert하거나, 처리 결과 테이블에 event_id unique constraint를 걸 수 있다. 이러면 중복 이벤트가 와도 같은 부작용을 한 번만 수행할 수 있다.

`event_id`를 Kafka offset으로 대체하면 안 된다. offset은 topic/partition 안의 위치일 뿐이고, 재발행, 토픽 변경, mirror, replay 시 안정적인 비즈니스 id가 아니다.

### `aggregate_type`, `aggregate_id`

이벤트가 어떤 도메인 객체 흐름에 속하는지 나타낸다. Kafka key와 partitioning 기준으로 자주 사용된다.

예를 들어 주문 이벤트는 key를 `orderId`로 잡아 같은 주문 이벤트를 같은 partition에 넣을 수 있다.

```text
Order order-100 -> partition 3
Order order-100 -> partition 3
Order order-101 -> partition 7
```

이렇게 해야 같은 aggregate 안의 이벤트 순서가 유지될 가능성이 높아진다. 물론 Kafka는 같은 partition 안의 순서를 보장하지, 전체 도메인 순서를 보장하지 않는다.

### `event_type`, `event_version`

consumer가 어떤 이벤트로 해석해야 하는지 나타낸다.

주의할 점은 `event_type`만으로 충분하지 않다는 것이다. 이벤트 payload는 시간이 지나며 바뀐다. 필드가 추가되고, 의미가 분리되고, enum 값이 늘어난다. version 없이 payload만 던지면 consumer가 암묵적으로 JSON 구조를 추론하게 된다.

운영 기준:

- breaking change는 새 event type 또는 새 major version으로 분리한다
- optional field 추가는 backward compatible하게 처리한다
- 의미가 바뀌는 필드 재사용은 금지한다
- event version과 schema registry subject naming 전략을 연결한다

### `occurred_at`과 `created_at`

`occurred_at`은 도메인 사건 발생 시간이고, `created_at`은 outbox row 생성 시간이다. 대부분 같아 보이지만, 재처리나 보상 이벤트에서는 다를 수 있다.

운영에서 이 둘을 분리하면 분석이 쉬워진다.

- 사용자가 결제한 시각
- 서비스가 이벤트를 기록한 시각
- Debezium이 Kafka로 발행한 시각
- consumer가 처리한 시각

이 네 가지는 모두 다를 수 있다. 지연을 추적하려면 시간 개념을 섞지 말아야 한다.

### `trace_id`, `correlation_id`, `causation_id`

이 필드들은 처음에는 과해 보이지만 장애 분석에서 큰 차이를 만든다.

- `trace_id`: 요청 흐름 추적
- `correlation_id`: 같은 업무 흐름에 속한 여러 이벤트 묶기
- `causation_id`: 이 이벤트를 유발한 직전 이벤트 또는 command 표시

예를 들어 `PaymentApproved`가 `OrderPaid`를 만들고, `OrderPaid`가 `ShipmentRequested`를 만들었다면 causation chain을 남길 수 있다. 나중에 "왜 이 배송 요청이 생성됐나"를 추적할 때 단순 로그 검색보다 훨씬 강하다.

---

## 핵심 개념 4: 순서 보장은 "전체 순서"가 아니라 "무엇의 순서가 필요한가"를 먼저 정해야 한다

Outbox를 설계할 때 "이벤트 순서가 보장되나요?"라는 질문이 자주 나온다. 이 질문은 그대로는 답하기 어렵다. 먼저 순서의 범위를 나눠야 한다.

### 1) 같은 DB 트랜잭션 안의 순서

하나의 트랜잭션에서 여러 outbox row가 insert될 수 있다.

```text
TX-1:
  order-100 OrderPaid
  order-100 LoyaltyPointReserved
```

이 둘의 상대 순서를 Kafka consumer가 반드시 알아야 하는가? 그렇다면 outbox row에 sequence를 명시하는 편이 안전하다.

```sql
transaction_id varchar(100),
transaction_sequence integer
```

DB log의 물리 순서에 기대는 것은 도구와 DB 구현 세부에 강하게 묶인다. 도메인적으로 필요한 순서라면 도메인 필드로 표현해야 한다.

### 2) 같은 aggregate 안의 순서

대부분의 실무 이벤트에서 정말 중요한 것은 같은 aggregate의 순서다.

```text
OrderCreated -> OrderPaid -> OrderCancelled
```

이 순서를 지키려면 최소한 다음이 필요하다.

- Kafka key를 `aggregate_id`로 설정한다
- 같은 aggregate 이벤트는 같은 topic 또는 ordering이 유지되는 topic 설계로 보낸다
- consumer가 partition 안에서 순차 처리 또는 순서 보존 처리를 한다
- aggregate version을 이벤트에 포함해 역전 감지를 가능하게 한다

예를 들어 payload에 `aggregateVersion`을 넣는다.

```json
{
  "orderId": "order-100",
  "aggregateVersion": 12,
  "status": "PAID"
}
```

consumer는 이미 version 12를 처리했는데 version 11이 늦게 도착하면 무시하거나 보류할 수 있다. 반대로 version 14가 먼저 오고 version 13이 빠졌다면 gap을 감지할 수 있다.

### 3) 여러 aggregate 사이의 전역 순서

전역 순서는 대부분 요구하면 안 된다. 주문 A와 주문 B의 상대 순서가 비즈니스적으로 중요하지 않은데도 전체 순서를 요구하면 partitioning, 확장성, 장애 복구가 모두 어려워진다.

정말 전역 순서가 필요하다면 그 요구는 Kafka 설정 하나로 해결할 문제가 아니다.

- 단일 partition으로 처리량을 포기할 것인가
- 별도 sequencer 서비스를 둘 것인가
- DB transaction sequence를 기준으로 projection할 것인가
- 지연과 병목을 감수할 것인가

전역 순서는 강력한 제약이다. "정렬이 편하니까" 수준으로 요구하면 시스템 전체가 불필요하게 느려진다.

---

## 핵심 개념 5: 멱등성은 consumer 테이블 하나가 아니라 부작용 경계 전체의 설계다

CDC Outbox를 도입해도 중복 이벤트는 가능하다. 따라서 consumer는 멱등해야 한다. 하지만 "processed_events 테이블 하나 만들면 끝"이라고 생각하면 부족하다.

멱등성은 부작용 종류마다 다르게 설계해야 한다.

### DB 상태 갱신

가장 다루기 쉽다. 이벤트가 특정 상태를 "설정"하는 형태라면 upsert로 멱등 처리할 수 있다.

```sql
INSERT INTO order_projection (
    order_id,
    status,
    last_event_id,
    aggregate_version,
    updated_at
) VALUES (
    'order-100',
    'PAID',
    'evt-900',
    12,
    now()
)
ON CONFLICT (order_id) DO UPDATE
   SET status = EXCLUDED.status,
       last_event_id = EXCLUDED.last_event_id,
       aggregate_version = EXCLUDED.aggregate_version,
       updated_at = EXCLUDED.updated_at
 WHERE order_projection.aggregate_version < EXCLUDED.aggregate_version;
```

여기서는 `aggregate_version`이 중요하다. 같은 이벤트 중복뿐 아니라 오래된 이벤트 역전까지 막을 수 있다.

### 금액, 포인트, 재고처럼 누적되는 변경

`balance = balance + 100` 같은 증감 연산은 중복에 취약하다. 이 경우 event_id unique constraint를 처리 결과와 같은 트랜잭션에 묶어야 한다.

```sql
BEGIN;

INSERT INTO processed_events (consumer_name, event_id)
VALUES ('point-service', 'evt-900');

UPDATE user_points
   SET points = points + 100
 WHERE user_id = 'user-1';

COMMIT;
```

이미 처리된 event_id면 insert에서 unique violation이 나고, 포인트 증가는 수행하지 않는다. 핵심은 "중복 체크"와 "부작용"이 같은 트랜잭션에 있어야 한다는 것이다.

체크만 먼저 하고 나중에 update하면 그 사이에 race condition이 생긴다.

### 외부 API 호출

외부 결제사, 문자 발송, 이메일 발송은 더 어렵다. DB 트랜잭션 안에 외부 API를 묶을 수 없기 때문이다.

이때는 외부 API의 idempotency key를 적극적으로 써야 한다.

```text
POST /send-sms
Idempotency-Key: evt-900
```

외부 시스템이 idempotency key를 지원하지 않는다면, 내부에서 발송 요청 테이블을 두고 상태 머신으로 관리하는 편이 낫다.

```text
PENDING -> SENDING -> SENT
                -> FAILED_RETRYABLE
                -> FAILED_FINAL
```

이렇게 하면 consumer가 중복 실행되어도 같은 `event_id`에 대한 발송 요청은 하나만 만들어진다. 실제 외부 호출 worker는 별도의 retry/backoff 정책으로 처리한다.

### 파일, 검색 인덱스, 캐시 갱신

검색 인덱스나 캐시는 대부분 eventual consistency를 받아들일 수 있다. 이 경우 "마지막 상태가 이기게" 만드는 것이 중요하다.

- event_id만 보지 말고 aggregate version을 본다
- 늦게 온 오래된 이벤트가 최신 projection을 덮어쓰지 못하게 한다
- 재색인 job이 이벤트 처리와 충돌해도 최종 상태가 수렴하게 한다

정리하면, consumer 멱등성은 한 가지 기술이 아니라 **부작용을 어떤 저장소와 어떤 원자성 경계 안에서 제어할 수 있는가**의 문제다.

---

## 실무 예시: 주문 결제 이벤트를 CDC Outbox로 발행하기

이제 주문 서비스를 예로 전체 흐름을 설계해 보자.

요구사항:

- 주문 결제 완료 시 `OrderPaid` 이벤트를 발행한다
- 배송 서비스, 포인트 서비스, 알림 서비스가 소비한다
- 같은 주문의 이벤트 순서는 유지하고 싶다
- 이벤트 중복은 가능하다고 보고 consumer가 멱등 처리한다
- 장애 시 누락 여부를 추적할 수 있어야 한다

### 1단계: 애플리케이션 트랜잭션

Spring 서비스라면 핵심은 outbox insert를 비즈니스 변경과 같은 트랜잭션에 넣는 것이다.

```java
@Transactional
public void markPaid(String orderId, PaymentResult payment) {
    Order order = orderRepository.getForUpdate(orderId);
    order.markPaid(payment.approvedAt());

    orderRepository.save(order);

    OutboxEvent event = OutboxEvent.builder()
        .eventId(UUID.randomUUID())
        .aggregateType("Order")
        .aggregateId(order.id())
        .eventType("OrderPaid")
        .eventVersion(1)
        .aggregateVersion(order.version())
        .occurredAt(payment.approvedAt())
        .payload(OrderPaidPayload.from(order, payment))
        .traceId(Trace.currentId())
        .producer("order-service")
        .build();

    outboxRepository.save(event);
}
```

주의할 점:

- KafkaTemplate을 여기서 호출하지 않는다
- outbox insert 실패 시 주문 상태 변경도 롤백되어야 한다
- event_id는 애플리케이션에서 생성해 consumer까지 유지한다
- aggregateVersion은 가능하면 도메인 모델의 version과 연결한다

### 2단계: Outbox Event Router

Debezium connector는 outbox 테이블의 insert를 읽고 Kafka로 보낸다. SMT를 적용해 다음 매핑을 한다.

```text
outbox.aggregate_type + outbox.event_type -> topic
outbox.aggregate_id                       -> message key
outbox.payload                            -> message value
outbox.event_id                           -> header
outbox.event_version                      -> header or value
```

토픽은 여러 방식이 가능하다.

```text
order.events
order.paid.v1
domain.order.events
```

일반적으로 같은 aggregate의 순서가 중요하면 한 aggregate 계열 이벤트를 같은 topic에 두고 key를 aggregate_id로 잡는 편이 단순하다. 이벤트 타입별로 토픽을 너무 잘게 나누면 consumer 선택은 편해지지만, 같은 aggregate의 여러 이벤트 순서를 topic 간에 보장하기 어려워진다.

### 3단계: 배송 서비스 consumer

배송 서비스는 `OrderPaid`를 받으면 배송 요청을 만든다.

```sql
BEGIN;

INSERT INTO processed_events (consumer_name, event_id)
VALUES ('shipping-service', :event_id);

INSERT INTO shipment_requests (
    order_id,
    status,
    requested_by_event_id,
    created_at
) VALUES (
    :order_id,
    'REQUESTED',
    :event_id,
    now()
)
ON CONFLICT (order_id) DO NOTHING;

COMMIT;
```

이 구조는 같은 이벤트가 두 번 와도 배송 요청을 하나만 만든다. `processed_events`와 `shipment_requests` 중 어느 쪽 unique constraint를 중심으로 둘지는 도메인에 따라 다르지만, 핵심은 중복 이벤트가 부작용을 두 번 만들지 못하게 하는 것이다.

### 4단계: 포인트 서비스 consumer

포인트는 누적 변경이므로 더 조심해야 한다.

```sql
BEGIN;

INSERT INTO processed_events (consumer_name, event_id)
VALUES ('point-service', :event_id);

UPDATE user_points
   SET balance = balance + :earned_points
 WHERE user_id = :user_id;

INSERT INTO point_ledger (
    ledger_id,
    user_id,
    event_id,
    amount,
    reason,
    created_at
) VALUES (
    gen_random_uuid(),
    :user_id,
    :event_id,
    :earned_points,
    'ORDER_PAID',
    now()
);

COMMIT;
```

여기서는 ledger의 `event_id`에도 unique constraint를 걸어두는 편이 좋다. processed_events와 ledger가 같은 DB에 있다면 중복 방어가 강해진다.

### 5단계: 알림 서비스 consumer

알림은 외부 부작용이다. 직접 문자 API를 호출하기보다 내부 발송 요청을 먼저 만든다.

```sql
INSERT INTO notification_requests (
    request_id,
    idempotency_key,
    channel,
    recipient,
    template,
    payload,
    status,
    created_at
) VALUES (
    gen_random_uuid(),
    :event_id,
    'KAKAO',
    :phone,
    'ORDER_PAID',
    :payload,
    'PENDING',
    now()
)
ON CONFLICT (idempotency_key) DO NOTHING;
```

그 다음 별도 sender가 `PENDING` 요청을 보내고 상태를 갱신한다. 외부 API가 idempotency key를 지원하면 `event_id`를 그대로 넘긴다. 지원하지 않으면 내부 요청 테이블이 최소한의 방어막이 된다.

---

## 트레이드오프: CDC Outbox가 해결하는 것과 새로 만드는 것

CDC Outbox는 강력하지만 은탄환은 아니다. 도입 전에 장단점을 명확히 봐야 한다.

### 해결하는 것

첫째, DB 변경과 이벤트 발행 의도의 원자성을 확보한다.

DB 커밋이 성공했다면 outbox row도 남는다. 따라서 "상태는 바뀌었는데 이벤트를 발행해야 한다는 사실 자체가 사라지는" 문제를 줄인다.

둘째, 이벤트 발행을 애플리케이션 요청 지연에서 분리한다.

사용자 요청은 DB 커밋까지만 책임지고, Kafka 발행은 CDC 파이프라인이 처리한다. Kafka 일시 장애가 곧바로 모든 주문 요청 실패로 이어지는 구조를 피할 수 있다.

셋째, 변경 이벤트의 원천을 DB commit log에 가깝게 둔다.

Polling보다 DB 변경 순서와 커밋 여부를 더 자연스럽게 따라갈 수 있다. 특히 여러 서비스에서 CDC를 표준 운영하면 데이터 파이프라인의 관측과 장애 대응 방식도 통일된다.

넷째, 누락 조사와 재처리가 쉬워진다.

outbox row가 남아 있으면 특정 event_id가 생성되었는지, Debezium이 읽었는지, Kafka에 들어갔는지, consumer가 처리했는지 단계별로 추적할 수 있다.

### 새로 만드는 책임

첫째, Debezium과 Kafka Connect 운영 책임이 생긴다.

connector 상태, task 재시작, offset storage, schema history topic, log retention, snapshot mode, connector config 배포를 운영해야 한다.

둘째, outbox 테이블 lifecycle을 관리해야 한다.

outbox row를 영원히 쌓아둘 수는 없다. 보존 기간, archive, purge, partitioning, vacuum, index bloat를 관리해야 한다.

셋째, consumer 멱등성이 필수가 된다.

중복은 가능하다고 봐야 한다. consumer가 중복에 취약하면 CDC Outbox를 도입해도 장애 양상이 "누락"에서 "중복 부작용"으로 바뀔 뿐이다.

넷째, 이벤트 계약과 스키마 진화를 관리해야 한다.

payload를 JSON으로 아무렇게나 넣으면 초기에는 빠르지만, consumer가 늘어날수록 계약 변경이 무섭게 어려워진다.

다섯째, 지연을 받아들이는 설계가 필요하다.

CDC는 비동기다. DB commit 직후 Kafka consumer가 즉시 처리한다고 보장할 수 없다. 사용자 화면이나 downstream API가 강한 일관성을 요구한다면 별도 조회 경로나 상태 확인 API가 필요하다.

---

## 운영 설계 1: Outbox 테이블 정리는 "나중에"가 아니라 처음부터 설계해야 한다

Outbox 테이블은 insert-only 성격이 강하다. 트래픽이 늘면 빠르게 커진다.

예를 들어 초당 500개 이벤트가 발생하면 하루 row 수는 다음과 같다.

```text
500 events/sec * 86,400 sec = 43,200,000 rows/day
```

이 규모에서는 "한 달 뒤에 지우자"가 단순하지 않다. 인덱스 크기, autovacuum, backup time, replication lag, connector scan 영향이 모두 커진다.

### 보존 기간 기준

보존 기간은 다음 질문으로 정한다.

- Kafka 발행이 성공했는지 확인할 수 있는 별도 지표가 있는가
- consumer 장애 조사에 outbox 원본 row가 며칠 필요할까
- 법적/감사 요구가 있는가
- object storage로 archive할 것인가
- connector가 장애로 며칠 멈췄을 때 DB log와 outbox row가 남아 있어야 하는가

보통은 Kafka에 정상 발행된 뒤 일정 기간만 DB에 보관하고, 장기 감사는 object storage나 data lake로 넘긴다. 하지만 "정상 발행"을 DB row에 표시하지 않는 CDC 방식에서는 발행 여부를 테이블 자체로 알기 어렵다. 이 경우 Kafka side의 topic retention, audit consumer, event ledger 등을 조합해야 한다.

### Partitioning

대용량 outbox는 날짜 기준 partitioning을 고려할 만하다.

```sql
CREATE TABLE outbox_events (
    ...
    created_at timestamptz NOT NULL
) PARTITION BY RANGE (created_at);
```

장점:

- 오래된 partition drop으로 빠른 정리가 가능하다
- vacuum 부담을 줄일 수 있다
- 인덱스 크기를 partition 단위로 관리할 수 있다

주의점:

- Debezium이 partitioned table 변경을 어떻게 캡처하는지 DB별로 확인해야 한다
- primary key와 partition key 제약을 이해해야 한다
- 너무 작은 partition은 관리 오버헤드를 만든다
- retention job이 connector lag보다 앞서 삭제하지 않게 해야 한다

### Purge job

정리 job은 단순 delete보다 partition drop이 낫지만, 작은 규모에서는 batch delete도 가능하다.

```sql
DELETE FROM outbox_events
 WHERE created_at < now() - interval '7 days'
 LIMIT 10000;
```

PostgreSQL에서는 `DELETE ... LIMIT` 문법이 직접 지원되지 않으므로 CTE를 사용해야 한다.

```sql
WITH old_rows AS (
    SELECT event_id
      FROM outbox_events
     WHERE created_at < now() - interval '7 days'
     ORDER BY created_at
     LIMIT 10000
)
DELETE FROM outbox_events o
 USING old_rows r
 WHERE o.event_id = r.event_id;
```

삭제 job은 낮은 우선순위로 천천히 돌아야 한다. 이벤트 발행 경로와 같은 DB를 쓰므로 purge가 본 업무 write를 방해하면 안 된다.

---

## 운영 설계 2: Lag는 Kafka lag만 보면 늦다

CDC Outbox 파이프라인의 지연은 여러 구간으로 나뉜다.

```text
T1: domain event occurred
T2: outbox row committed
T3: Debezium read from DB log
T4: Kafka message produced
T5: consumer polled message
T6: business side effect completed
```

Kafka consumer lag는 T4 이후의 지연만 보여준다. 하지만 실제 사용자가 보는 지연은 T1부터 T6까지다.

따라서 관측 지표는 구간별로 나누는 것이 좋다.

### DB to Debezium lag

- connector가 DB log를 얼마나 늦게 읽는가
- DB replication slot 또는 binlog position이 얼마나 밀렸는가
- connector task가 재시작을 반복하고 있지는 않은가
- snapshot이 오래 걸려 streaming으로 넘어가지 못하고 있지는 않은가

PostgreSQL이라면 replication slot lag를 봐야 한다. 이 lag가 커지면 WAL 보관량이 늘고 디스크 압박이 생길 수 있다.

### Debezium to Kafka lag

- Kafka produce latency
- broker ack 지연
- connector producer error
- schema registry 등록 실패
- transform error

이 구간에서 실패하면 connector는 멈추거나 retry할 수 있다. 단순히 consumer lag가 0이라고 안심하면 안 된다. 애초에 Kafka로 들어오지 못하고 있을 수 있다.

### Kafka to Consumer lag

- topic/partition lag
- consumer group rebalance
- 처리 시간 증가
- DLQ 증가
- downstream DB/API 지연

이 구간은 일반 Kafka consumer 운영 지표와 같다. 단, CDC Outbox에서는 event_id, aggregate_id, occurred_at을 로그에 남겨야 추적이 쉬워진다.

### End-to-end latency

가장 유용한 지표는 event payload 또는 header의 `occurred_at`과 consumer 처리 완료 시각의 차이다.

```text
event_end_to_end_latency =
  consumer_processed_at - event_occurred_at
```

이 값이 p50은 낮고 p99만 높다면 특정 partition skew, 특정 downstream API, 특정 event type 문제가 있을 수 있다. 평균만 보면 장애를 놓친다.

---

## 운영 설계 3: Schema Registry와 Outbox payload를 느슨하게 두면 결국 consumer가 깨진다

Outbox payload를 `jsonb`로 두면 편하다. 하지만 편하다는 말은 아무 계약이 없다는 뜻일 수도 있다.

초기에는 이런 payload가 들어간다.

```json
{
  "orderId": "order-100",
  "paidAt": "2026-06-10T11:49:59+09:00",
  "amount": 39000
}
```

나중에 팀이 필드를 바꾼다.

```json
{
  "orderId": "order-100",
  "payment": {
    "approvedAt": "2026-06-10T11:49:59+09:00",
    "amount": {
      "currency": "KRW",
      "value": 39000
    }
  }
}
```

producer는 더 좋아졌다고 생각하지만, 기존 consumer는 `amount` 숫자를 기대하다가 깨진다.

### 계약 관리 방식

선택지는 세 가지다.

1. outbox payload 자체를 Avro/Protobuf로 직렬화해 저장한다
2. DB에는 JSON을 저장하되 Kafka 발행 시 Schema Registry subject를 적용한다
3. JSON Schema를 사용하고 CI에서 payload schema compatibility를 검사한다

어떤 방식이든 핵심은 같다.

- 이벤트 타입별 스키마를 명시한다
- optional field 추가와 breaking change를 구분한다
- consumer가 unknown field를 견딜 수 있게 한다
- enum 확장은 특히 조심한다
- 날짜, 금액, decimal, timezone 규칙을 고정한다
- schema version과 event_version의 관계를 문서화한다

### 이벤트 타입별 subject

Outbox에서 여러 event_type이 한 테이블에 들어가면 Schema Registry subject naming이 중요해진다.

가능한 전략:

```text
order.events-OrderPaid-value
order.events-OrderCancelled-value
com.example.order.OrderPaid
```

같은 topic에 여러 event type을 넣는다면 TopicNameStrategy만으로는 부족할 수 있다. 모든 event type이 같은 subject lineage로 묶이면 호환성 검사가 엉뚱해진다. RecordNameStrategy 또는 TopicRecordNameStrategy를 검토해야 한다.

이 부분은 앞서 다룬 Kafka Schema Registry 글의 주제와도 연결된다. Outbox는 이벤트 생성 경계이고, Schema Registry는 그 이벤트가 여러 팀 사이에서 오래 살아남을 수 있도록 통제하는 계약 경계다.

---

## 운영 설계 4: DLQ는 실패를 버리는 곳이 아니라 재처리 계약이다

CDC Outbox 파이프라인에는 실패 지점이 많다.

- Debezium이 outbox row를 변환하지 못한다
- payload schema가 맞지 않는다
- Kafka produce가 실패한다
- consumer 역직렬화가 실패한다
- 비즈니스 validation이 실패한다
- downstream DB/API가 일시적으로 실패한다
- 특정 이벤트가 poison message가 되어 계속 재시도된다

DLQ를 둘 때 중요한 것은 "어디서 실패했는가"를 분리하는 것이다.

### Connector-level DLQ

Debezium/Kafka Connect transform이나 serialization에서 실패하는 경우다.

여기에는 원본 row, error message, connector name, topic, partition, offset, timestamp를 남겨야 한다. 이 DLQ는 애플리케이션 consumer가 처리할 수 없는 형식일 수 있다. 운영자가 원인을 보고 connector 설정이나 데이터 오류를 고쳐야 한다.

### Consumer-level DLQ

Kafka topic에는 정상 발행되었지만 특정 consumer가 처리하지 못한 경우다.

이 DLQ에는 최소한 다음이 있어야 한다.

- original topic/partition/offset
- event_id
- aggregate_id
- event_type
- payload
- error code
- retry count
- failed_at
- consumer version

중요한 점은 DLQ가 최종 쓰레기통이 아니라는 것이다. 재처리 도구가 있어야 한다.

```text
DLQ inspect -> classify -> fix data/code/config -> replay selected events
```

선택 재처리가 불가능한 DLQ는 장애를 미루는 저장소일 뿐이다.

### Retry와 DLQ의 경계

모든 실패를 즉시 DLQ로 보내면 일시 장애에 약하다. 반대로 모든 실패를 무한 재시도하면 poison message 하나가 partition 전체를 막는다.

실무 기준:

- 네트워크 timeout, 5xx, lock timeout은 retry
- schema mismatch, required field missing, unknown event type은 DLQ
- 비즈니스적으로 이미 취소된 주문 등은 idempotent no-op 또는 DLQ 중 정책 결정
- retry는 exponential backoff와 max attempt를 둔다
- retry topic을 쓰는 경우 원래 ordering 요구와 충돌하지 않는지 확인한다

같은 aggregate 순서가 중요한 이벤트를 retry topic으로 빼면 뒤 이벤트가 먼저 처리될 수 있다. 이게 허용되는 도메인인지 반드시 확인해야 한다.

---

## 흔한 실수 1: Outbox row를 저장했으니 consumer는 중복을 신경 쓰지 않아도 된다고 믿는다

Outbox는 발행 의도 누락을 줄이는 패턴이다. 중복을 제거하는 패턴이 아니다.

중복은 여러 곳에서 생긴다.

- Debezium restart 후 offset 재처리
- Kafka producer retry
- consumer offset commit 전 장애
- DLQ replay
- 운영자가 수동 재발행
- disaster recovery 후 topic 복구

따라서 consumer는 기본적으로 at-least-once를 받아들여야 한다. 특히 결제, 포인트, 쿠폰, 재고처럼 돈과 가까운 도메인은 event_id 기반 unique constraint 없이는 운영에 내보내면 안 된다.

---

## 흔한 실수 2: Kafka key를 event_id로 잡는다

event_id는 멱등성에는 좋지만 ordering key로는 보통 좋지 않다. 모든 이벤트마다 event_id가 다르면 같은 주문의 이벤트가 서로 다른 partition으로 흩어진다.

```text
key = event_id
OrderCreated(order-100) -> partition 1
OrderPaid(order-100)    -> partition 6
OrderCancelled(order-100) -> partition 2
```

이러면 같은 주문의 순서를 Kafka가 보장할 수 없다.

대부분의 도메인 이벤트에서는 key를 aggregate_id로 잡는 편이 낫다.

```text
key = order-100
OrderCreated(order-100) -> partition 3
OrderPaid(order-100)    -> partition 3
OrderCancelled(order-100) -> partition 3
```

event_id는 header나 payload에 넣어 멱등성 키로 쓴다.

---

## 흔한 실수 3: Snapshot mode를 모른 채 운영 테이블에 connector를 붙인다

운영 중인 outbox 테이블에 Debezium을 붙였는데 connector가 기존 row를 snapshot으로 읽어 과거 이벤트를 대량 발행하는 사고가 생길 수 있다.

특히 마이그레이션에서 위험하다.

- 기존에는 polling publisher가 이미 이벤트를 발행하고 있었다
- 새로 Debezium을 붙였다
- outbox 테이블에는 과거 row가 남아 있었다
- Debezium이 snapshot으로 과거 row를 읽었다
- consumer가 중복 이벤트를 대량 처리했다

해결 기준:

- connector 도입 전 snapshot 정책을 문서화한다
- cutover 전 outbox 테이블을 비우거나 기준 시점을 정한다
- 모든 consumer의 event_id 멱등성을 먼저 검증한다
- 마이그레이션 기간에는 이벤트 수, event_id 중복률, consumer side effect를 대조한다

---

## 흔한 실수 4: Outbox 테이블을 업무 조회에 재사용한다

Outbox 테이블은 발행 계약이다. 사용자 화면, 관리자 화면, 통계 조회의 원천 테이블로 쓰기 시작하면 lifecycle 관리가 꼬인다.

예를 들어 운영자가 "최근 주문 이벤트를 보고 싶다"며 outbox를 직접 조회하는 기능을 만들면, 나중에 outbox retention을 7일로 줄이기 어려워진다. 감사 목적이 필요하면 별도 audit log나 data lake로 복제하는 편이 낫다.

Outbox는 다음 책임에 집중해야 한다.

- 발행할 이벤트 의도 저장
- CDC source
- 장애 추적을 위한 최소한의 원본 보존

그 외 장기 분석, 감사, 사용자 조회는 별도 projection으로 분리하는 것이 깔끔하다.

---

## 흔한 실수 5: 이벤트 payload에 현재 DB row 전체를 넣는다

처음에는 편하다.

```json
{
  "orderId": "order-100",
  "status": "PAID",
  "buyerName": "Kim",
  "buyerPhone": "010-0000-0000",
  "shippingAddress": "...",
  "internalMemo": "...",
  "updatedBy": "admin-1"
}
```

하지만 이 방식은 위험하다.

- consumer가 필요 없는 개인정보까지 받는다
- DB 컬럼 변경이 이벤트 계약 변경으로 새어 나간다
- 내부 필드가 외부 팀에 의존된다
- payload가 커지고 schema evolution이 어려워진다
- 보안/마스킹/삭제 요구가 복잡해진다

이벤트 payload는 "그 사건을 이해하는 데 필요한 계약"이어야 한다. DB row 복사본이 아니다.

좋은 기준:

- 이벤트 이름이 표현하는 사실에 필요한 필드만 담는다
- 개인정보는 최소화한다
- 내부 운영 필드는 빼거나 별도 내부 이벤트로 분리한다
- consumer가 조회 가능한 데이터는 ID만 주고 query API를 쓰게 할지 검토한다
- 장기적으로 공개할 수 없는 필드는 이벤트에 넣지 않는다

---

## 흔한 실수 6: Connector 장애를 애플리케이션 장애보다 덜 중요하게 본다

Outbox를 도입하면 애플리케이션 요청은 정상인데 이벤트가 downstream으로 안 가는 상태가 가능해진다. 이때 주문 서비스 API는 200을 반환하지만 배송, 포인트, 알림은 멈춘다.

따라서 connector는 부가 컴포넌트가 아니라 비즈니스 처리 경로의 일부다.

필수 알림:

- connector task failed
- connector paused
- source DB log lag 증가
- Kafka produce error 증가
- schema registry error
- DLQ 증가
- event end-to-end latency p95/p99 임계치 초과
- outbox row 증가율 급증
- replication slot WAL 보관량 증가

운영 대시보드에서는 애플리케이션, DB, Debezium, Kafka, consumer를 한 흐름으로 봐야 한다.

```text
order-service commit rate
outbox insert rate
Debezium source lag
Kafka topic input rate
consumer lag
consumer success/failure rate
business side effect completion rate
```

이 흐름 중 하나라도 끊기면 사용자 관점의 업무 처리는 미완성일 수 있다.

---

## 체크리스트: CDC Outbox를 운영 투입하기 전에 확인할 것

### 트랜잭션 경계

- 비즈니스 상태 변경과 outbox insert가 같은 DB 트랜잭션에 있는가
- Kafka 직접 발행 코드가 트랜잭션 안에 남아 있지 않은가
- outbox insert 실패 시 비즈니스 변경도 롤백되는가
- event_id가 커밋 전에 결정되고 payload/header에 유지되는가
- aggregate version 또는 event sequence가 필요한 도메인에 포함되어 있는가

### Outbox 스키마

- event_id가 전역 unique인가
- aggregate_type, aggregate_id가 명확한가
- event_type, event_version이 있는가
- occurred_at과 created_at을 분리했는가
- trace_id/correlation_id/causation_id가 필요한 흐름에 포함되는가
- payload에 개인정보와 내부 필드가 과도하게 들어가지 않는가
- retention, archive, purge 기준이 정해졌는가

### Debezium/CDC

- snapshot mode를 명확히 정했는가
- connector offset storage와 schema history topic을 백업/운영 대상으로 보고 있는가
- source DB log retention이 connector 장애 시간을 버틸 만큼 충분한가
- connector lag와 task failure alert가 있는가
- SMT 변환 실패 시 DLQ 또는 장애 정책이 있는가
- connector config 변경이 리뷰와 배포 절차를 거치는가

### Kafka 설계

- topic 이름과 event_type 라우팅 규칙이 문서화되어 있는가
- Kafka key가 event_id가 아니라 aggregate_id 등 ordering 기준에 맞는가
- partition 수가 처리량과 ordering 요구를 동시에 만족하는가
- retention 정책이 replay 요구와 맞는가
- schema registry subject naming 전략이 여러 event_type을 감당하는가
- producer acks, retries, compression, message size 제한을 확인했는가

### Consumer 설계

- 모든 consumer가 event_id 기반 멱등성을 갖는가
- 중복 체크와 부작용이 같은 트랜잭션에 있는가
- 외부 API 호출에는 idempotency key 또는 내부 요청 테이블이 있는가
- aggregate_version으로 오래된 이벤트를 막을 수 있는가
- retry와 DLQ 기준이 실패 유형별로 나뉘어 있는가
- DLQ replay 도구가 있는가
- consumer offset commit이 처리 완료 이후에 일어나는가

### 관측과 운영

- end-to-end latency를 측정하는가
- outbox insert rate와 Kafka input rate를 비교할 수 있는가
- event_id로 DB row, Kafka message, consumer log를 연결할 수 있는가
- connector 장애 시 누가 어떤 순서로 복구할지 runbook이 있는가
- 수동 재발행 절차가 멱등성을 전제로 설계되어 있는가
- purge job이 connector lag보다 앞서 원본 row를 지우지 않는가

---

## 설계 판단 기준: 언제 CDC Outbox를 쓰고, 언제 단순 발행으로 충분한가

모든 이벤트에 CDC Outbox가 필요한 것은 아니다.

### CDC Outbox가 잘 맞는 경우

- DB 상태 변경과 이벤트 발행이 모두 비즈니스적으로 중요하다
- 이벤트 누락이 정산, 배송, 권한, 포인트 등 실제 피해를 만든다
- 여러 서비스가 같은 도메인 이벤트를 소비한다
- replay, audit, 장애 추적 요구가 있다
- Kafka 발행 실패가 사용자 요청 전체 실패로 번지면 안 된다
- 마이크로서비스 간 eventual consistency를 표준 패턴으로 운영하려 한다

### 과할 수 있는 경우

- 이벤트가 단순 캐시 무효화 정도이고 누락 시 다음 요청에서 회복된다
- 트래픽이 매우 작고 운영 복잡도를 감당할 팀이 없다
- Kafka Connect/Debezium 운영 역량이 아직 없다
- consumer가 하나뿐이고 동기 API 호출이 더 명확하다
- 강한 일관성이 필요해 비동기 이벤트로 풀면 안 되는 요구다

이때는 polling outbox, transactional event listener, 단순 retry publisher, 동기 API 호출이 더 나을 수 있다. 중요한 것은 패턴 이름이 아니라 장애 비용과 운영 역량의 균형이다.

---

## 마이그레이션 전략: 이미 직접 Kafka 발행 중인 서비스를 바꾸는 법

운영 중인 서비스를 CDC Outbox로 바꿀 때는 한 번에 갈아엎지 않는 편이 안전하다.

### 1단계: event_id를 먼저 도입한다

기존 직접 발행 이벤트에도 event_id를 넣는다. consumer는 이 event_id로 멱등성을 갖추기 시작한다.

이 단계의 목표는 발행 방식을 바꾸기 전, 중복에 견디는 downstream을 만드는 것이다.

### 2단계: outbox 테이블에 shadow write한다

기존 Kafka 발행은 유지하되, 같은 트랜잭션에 outbox row도 저장한다. 아직 Debezium은 발행하지 않거나 별도 검증 topic으로만 보낸다.

확인할 것:

- 기존 발행 이벤트와 outbox payload가 의미적으로 같은가
- event count가 맞는가
- aggregate_id, event_type, occurred_at이 정상인가
- payload schema가 consumer 요구를 만족하는가

### 3단계: Debezium을 검증 topic에 연결한다

실제 consumer가 보지 않는 topic으로 CDC 이벤트를 흘린다. 기존 Kafka 이벤트와 비교한다.

```text
direct topic: order.events
cdc topic:    order.events.shadow
```

대조 기준:

- event_id set 차이
- payload hash 차이
- 발생 시각 차이
- 순서 차이
- 누락/중복률

### 4단계: consumer 일부를 CDC topic으로 전환한다

부작용이 작은 consumer부터 전환한다. 알림처럼 외부 발송이 있는 서비스보다 projection, 검색 인덱스, 내부 캐시가 먼저 적합하다.

### 5단계: 직접 Kafka 발행을 제거한다

모든 consumer가 CDC topic으로 전환되고 일정 기간 안정화되면 애플리케이션의 직접 Kafka 발행 코드를 제거한다. 이때도 feature flag나 빠른 rollback 경로를 준비한다.

마이그레이션의 핵심은 "발행 경로를 바꾸기 전 consumer 멱등성을 먼저 만든다"는 것이다. 발행 안정성을 높이려다 consumer 중복 부작용을 터뜨리면 순서가 잘못된 것이다.

---

## DB별로 달라지는 실무 포인트

CDC Outbox의 큰 원리는 같지만, 실제 운영에서는 DB별 차이가 꽤 크다. Debezium이라는 공통 도구를 쓰더라도 source database가 무엇인지에 따라 장애 모드, 권한, 로그 보존, schema change 처리, snapshot 방식이 달라진다.

여기서는 PostgreSQL과 MySQL을 중심으로 정리한다. 두 DB는 가장 흔한 조합이고, 차이를 이해하면 다른 DB를 볼 때도 어떤 질문을 해야 하는지 감이 잡힌다.

### PostgreSQL: WAL, logical replication slot, publication

PostgreSQL에서 Debezium은 logical decoding을 통해 WAL 변경을 읽는다. 운영자가 반드시 이해해야 하는 단어는 replication slot이다.

Replication slot은 "이 consumer가 여기까지 WAL을 읽었다"는 위치를 PostgreSQL이 기억하게 만드는 장치다. 장점은 connector가 잠시 멈춰도 필요한 WAL이 바로 지워지지 않는다는 점이다. 단점은 connector가 오래 멈추면 WAL이 계속 쌓여 디스크를 압박한다는 점이다.

즉 PostgreSQL CDC에서는 다음 지표가 매우 중요하다.

- replication slot restart_lsn
- confirmed_flush_lsn
- retained WAL size
- connector streaming lag
- disk usage

connector가 죽어 있는데 replication slot이 유지되면 PostgreSQL은 Debezium이 아직 읽지 못한 WAL을 계속 보관하려고 한다. 이 상태가 오래 지속되면 DB 디스크가 가득 차는 장애로 이어질 수 있다. 그래서 "이벤트 발행이 멈췄다"가 "원본 DB 쓰기 장애"로 확대될 수 있다.

운영 기준:

- connector 장애 알림은 애플리케이션 장애만큼 빠르게 울려야 한다
- WAL 보관량 임계치를 별도로 둔다
- slot lag가 커질 때 purge job이나 대량 write job을 멈출 수 있어야 한다
- disaster recovery 시 slot 재생성 절차를 문서화한다
- publication 대상 테이블을 좁혀 불필요한 변경 캡처를 줄인다

PostgreSQL에서는 outbox 테이블만 publication에 포함하는 방식이 깔끔하다.

```sql
CREATE PUBLICATION app_outbox_publication
    FOR TABLE outbox_events;
```

이렇게 하면 Debezium이 모든 업무 테이블 변경을 볼 필요가 없다. Outbox 패턴의 장점 중 하나가 바로 이것이다. 원본 업무 테이블 구조를 downstream에 노출하지 않고, 이벤트로 공개할 것만 outbox에 기록해 캡처한다.

### PostgreSQL partitioned outbox 주의점

대용량 outbox에서는 partitioning을 고려한다고 했다. 하지만 logical replication과 partitioned table의 동작은 PostgreSQL 버전과 publication 설정에 영향을 받는다.

확인할 질문:

- Debezium 버전이 현재 PostgreSQL partitioned table 변경을 원하는 방식으로 읽는가
- publication이 parent table 기준인지 child partition 기준인지
- 새 partition 생성 시 publication에 자동 포함되는가
- partition drop이 connector에 어떤 schema/change event로 보이는가
- primary key가 Debezium message key로 안정적으로 잡히는가

운영에서는 partition 생성 job과 Debezium 캡처 설정을 따로 생각하면 안 된다. 월초에 새 partition이 생겼는데 publication에 포함되지 않아 이벤트가 누락되는 사고가 충분히 가능하다.

안전한 방식은 다음이다.

1. partition 생성 자동화에 publication 검증을 포함한다
2. 새 partition에 test row를 넣고 Kafka 도착 여부를 확인한다
3. outbox insert count와 Kafka input count를 일 단위로 대조한다
4. partition drop 전에 connector lag가 0에 가까운지 확인한다

### MySQL: binlog, server id, row format

MySQL에서는 binlog가 핵심이다. Debezium은 MySQL replication protocol을 사용해 binlog를 읽는다. 이때 binlog 설정이 맞지 않으면 CDC 자체가 불안정해진다.

운영 질문:

- `binlog_format`이 ROW인가
- binlog retention이 connector 장애 시간을 버틸 만큼 충분한가
- Debezium connector의 server id가 기존 replica와 충돌하지 않는가
- GTID를 사용하는가
- schema history topic을 잃었을 때 복구 절차가 있는가

statement-based binlog는 row-level change capture에 적합하지 않다. CDC를 안정적으로 쓰려면 보통 ROW format이 필요하다.

MySQL에서 자주 터지는 문제는 binlog가 이미 삭제된 뒤 connector가 재시작되는 경우다.

```text
1. Debezium connector가 2일 동안 중단
2. MySQL binlog retention은 24시간
3. connector 재시작
4. 이전 offset의 binlog file을 찾을 수 없음
5. connector가 이어 읽지 못함
```

이 상황에서는 단순 restart로 해결되지 않는다. snapshot 재수행, offset 초기화, 누락 구간 보정, 이벤트 재발행 판단이 필요하다. Outbox row가 아직 남아 있다면 복구 옵션이 있지만, outbox purge까지 끝났다면 누락 복구가 매우 어려워진다.

따라서 binlog retention, outbox retention, connector 복구 목표 시간은 함께 정해야 한다.

```text
connector 최대 허용 중단 시간 <= binlog retention <= outbox retention
```

현실적으로는 outbox retention을 더 길게 두고, binlog retention은 DB 디스크와 복구 목표 사이에서 조정한다.

### Timezone과 timestamp

DB별 timestamp 처리는 사소해 보이지만 이벤트 시스템에서는 자주 문제를 만든다.

원칙:

- 이벤트 payload의 시간은 가능하면 timezone을 포함한 ISO-8601 문자열 또는 epoch millis로 표준화한다
- DB `created_at`은 서버 timezone에 기대지 말고 UTC 또는 명시적 timezone 정책을 둔다
- 사용자 지역 시간과 시스템 발생 시간을 구분한다
- consumer가 local timezone으로 파싱하지 않도록 테스트한다

예를 들어 `2026-06-10T11:50:00+09:00`과 `2026-06-10T02:50:00Z`는 같은 시각이다. 이 둘을 같은 의미로 다루려면 payload 계약에서 명확히 해야 한다.

---

## Debezium Connector 설정을 읽는 법

설정 예시는 환경마다 다르지만, 어떤 항목을 어떤 관점으로 봐야 하는지는 공통적이다. 아래는 PostgreSQL outbox connector의 개념 예시다.

```json
{
  "name": "order-outbox-connector",
  "config": {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "database.hostname": "postgres",
    "database.port": "5432",
    "database.user": "debezium",
    "database.dbname": "orders",
    "topic.prefix": "orders_cdc",
    "plugin.name": "pgoutput",
    "slot.name": "orders_outbox_slot",
    "publication.name": "app_outbox_publication",
    "table.include.list": "public.outbox_events",
    "snapshot.mode": "never",
    "transforms": "outbox",
    "transforms.outbox.type": "io.debezium.transforms.outbox.EventRouter",
    "transforms.outbox.table.field.event.id": "event_id",
    "transforms.outbox.table.field.event.key": "aggregate_id",
    "transforms.outbox.table.field.event.type": "event_type",
    "transforms.outbox.table.field.event.payload": "payload",
    "transforms.outbox.route.by.field": "aggregate_type",
    "transforms.outbox.route.topic.replacement": "${routedByValue}.events"
  }
}
```

이 설정을 그대로 복사하라는 뜻이 아니다. 핵심은 각 항목이 어떤 장애 경계와 연결되는지 이해하는 것이다.

### `snapshot.mode`

Outbox에서는 가장 먼저 봐야 한다. 기존 row를 읽을지 말지를 결정한다.

가능한 판단:

- 신규 서비스이고 outbox가 비어 있다면 snapshot을 허용해도 위험이 작다
- 기존 운영 테이블이면 `never` 또는 schema-only 계열을 검토한다
- 과거 row 재발행이 목적이면 consumer 멱등성을 먼저 검증한다

snapshot mode는 "처음 시작 설정"처럼 보이지만, 운영에서는 마이그레이션 안전장치다.

### `table.include.list`

Outbox 테이블만 캡처하는지 확인한다. 업무 테이블 전체를 CDC로 흘리면 downstream이 DB 내부 구조에 결합된다.

Outbox 패턴의 철학은 "DB 변경을 모두 이벤트로 공개"가 아니다. **공개할 도메인 이벤트를 outbox에 명시적으로 쓰고 그것만 흘린다**에 가깝다.

### `slot.name` 또는 binlog client identity

connector의 정체성이다. 운영 환경별로 충돌하지 않게 이름을 정해야 한다.

나쁜 예:

```text
slot.name=debezium
```

여러 connector나 환경에서 이름이 겹치기 쉽다.

좋은 예:

```text
slot.name=prod_orders_outbox_v1
```

이름에는 환경, 서비스, 목적이 드러나는 편이 좋다.

### `topic.prefix`와 route 설정

Debezium 원본 topic과 Outbox routed topic이 어떻게 만들어지는지 이해해야 한다. 잘못 설정하면 consumer가 예상하지 못한 topic으로 이벤트가 흘러가거나, 여러 aggregate 이벤트가 하나의 topic에 섞인다.

운영에서는 topic naming을 코드 리뷰와 같은 수준으로 관리하는 것이 좋다. topic 이름은 API endpoint 못지않은 계약이다.

### Secret 관리

connector 설정에는 DB 계정 정보가 들어간다. Git에 평문으로 두면 안 된다. Kafka Connect 배포 방식에 따라 secret provider, Kubernetes Secret, Vault, 환경 변수 등을 써야 한다.

CDC 계정 권한도 최소화한다.

- outbox table read 권한
- replication 권한
- 필요한 schema 조회 권한

업무 테이블 update/delete 권한은 보통 필요 없다.

---

## 테스트 전략: 단위 테스트보다 장애 시나리오 테스트가 중요하다

CDC Outbox는 코드 몇 줄보다 경계 조건이 중요하다. 그래서 테스트도 단순 repository test에서 끝나면 부족하다.

### 테스트 1: 비즈니스 변경과 outbox insert 원자성

목표: outbox 저장 실패 시 비즈니스 변경이 같이 롤백되는지 확인한다.

시나리오:

1. 주문 결제 트랜잭션 시작
2. 주문 상태 변경
3. outbox insert에서 unique violation 또는 payload serialization error 유도
4. 트랜잭션 롤백 확인
5. 주문 상태가 변경되지 않았는지 확인

이 테스트는 단순하지만 중요하다. outbox insert가 별도 트랜잭션으로 분리되어 있으면 패턴이 깨진다.

### 테스트 2: Kafka 발행 중단 시 API 동작

목표: Kafka 또는 Debezium이 멈춰도 애플리케이션 요청이 어떤 정책으로 동작하는지 확인한다.

CDC Outbox에서는 Kafka가 잠시 장애여도 DB commit은 성공할 수 있다. 이게 장점이지만, downstream 지연을 사용자에게 어떻게 보여줄지 정책이 필요하다.

예:

- 주문 결제 API는 성공한다
- 배송 요청은 지연될 수 있다
- 사용자 화면에는 "결제 완료, 배송 준비 중" 상태를 보여준다
- 일정 시간 이상 배송 이벤트가 처리되지 않으면 운영 알림을 울린다

테스트는 단순히 200 응답만 보는 것이 아니라 end-to-end 상태 전이를 봐야 한다.

### 테스트 3: Debezium restart 중복

목표: connector 재시작 후 같은 event_id가 두 번 들어와도 consumer가 안전한지 확인한다.

방법:

1. 이벤트를 하나 생성한다
2. Kafka topic에서 같은 메시지를 수동으로 한 번 더 produce하거나 replay한다
3. consumer 처리 결과가 한 번만 반영되는지 확인한다

이 테스트는 Debezium 자체를 죽이지 않아도 된다. 중요한 것은 consumer가 중복에 견디는지다.

### 테스트 4: 순서 역전

목표: 오래된 aggregate version 이벤트가 늦게 도착해도 projection을 되돌리지 않는지 확인한다.

시나리오:

```text
OrderPaid version 12 처리
OrderCreated version 11이 늦게 도착
```

기대 결과:

- projection status가 `CREATED`로 되돌아가지 않는다
- stale event metric이 증가한다
- 필요하면 DLQ 또는 no-op 로그가 남는다

### 테스트 5: Snapshot 오발행

목표: 운영 전환 중 과거 outbox row가 재발행되지 않는지 확인한다.

방법:

1. 테스트 DB에 과거 outbox row를 넣는다
2. connector를 실제 운영 설정과 같은 snapshot mode로 시작한다
3. Kafka topic에 과거 row가 흘러가는지 확인한다
4. 의도와 다르면 설정을 수정한다

이 테스트는 마이그레이션 전에 꼭 필요하다.

### 테스트 6: Schema breaking change

목표: 호환되지 않는 payload 변경이 CI나 registry에서 막히는지 확인한다.

예:

- required field 삭제
- number를 object로 변경
- enum 의미 변경
- timestamp format 변경

좋은 파이프라인은 이런 변경을 코드 리뷰에서 감지하고, registry 등록 단계에서도 거부한다.

### 테스트 7: Purge와 connector lag 충돌

목표: outbox row 정리와 connector 지연이 충돌하지 않는지 확인한다.

시나리오:

1. connector를 중단한다
2. outbox row를 계속 쌓는다
3. purge job을 실행한다
4. connector를 재시작한다
5. 누락 여부를 확인한다

CDC는 transaction log를 읽으므로 row가 삭제되어도 이미 WAL/binlog에 남아 있으면 읽을 수 있다. 하지만 connector 중단 기간, log retention, snapshot 재시작 여부에 따라 복구 가능성이 달라진다. 이 경계는 문서가 아니라 실제 환경에서 검증해야 한다.

---

## 장애 시나리오별 대응 runbook

운영에서는 "정상 구조"보다 "깨졌을 때 무엇을 할지"가 더 중요하다. CDC Outbox 장애는 원인을 잘못 짚으면 복구가 더 위험해진다.

### 시나리오 1: Connector task failed

증상:

- Kafka topic input rate가 0에 가까워진다
- outbox insert rate는 정상이다
- Debezium connector status가 failed다
- source lag가 증가한다

확인 순서:

1. connector error message 확인
2. 최근 connector config 변경 여부 확인
3. DB 권한/네트워크/schema 변경 확인
4. schema registry 오류 확인
5. DLQ에 transform error가 쌓이는지 확인
6. replication slot/binlog lag 확인

대응:

- 일시 오류면 connector restart
- 특정 row transform 오류면 DLQ 정책에 따라 격리 또는 데이터 보정
- schema 변경 오류면 connector schema history와 DB DDL 변경 이력을 확인
- lag가 크면 consumer 영향도를 공지하고 복구 후 backlog 처리량을 감시

주의:

connector restart는 중복 발행을 만들 수 있다. 따라서 복구 후 consumer 중복 처리 metric을 같이 본다.

### 시나리오 2: DB log retention을 넘어 connector가 따라잡지 못함

증상:

- connector가 이전 WAL/binlog 위치를 찾지 못한다
- restart해도 같은 오류로 실패한다
- outbox 테이블에는 일부 row가 남아 있을 수 있다

이건 심각한 상황이다. 자동 복구가 안 될 수 있다.

대응 옵션:

1. outbox row가 남아 있고 기준 시점이 명확하면 별도 재발행 job을 만든다
2. connector offset을 새 위치로 초기화하고 이후 이벤트만 흘린다
3. 누락 구간 이벤트를 audit log나 업무 테이블에서 재구성한다
4. consumer 멱등성을 전제로 전체 snapshot/replay를 수행한다

어떤 선택이든 "누락을 숨기고 그냥 offset을 앞으로 민다"는 위험하다. 반드시 누락 구간을 기록하고, 비즈니스 영향도를 평가해야 한다.

### 시나리오 3: Consumer lag 폭증

증상:

- Debezium과 Kafka input은 정상
- 특정 consumer group lag가 증가
- downstream DB/API latency 증가
- retry topic 또는 DLQ 증가 가능

확인 순서:

1. lag가 모든 partition인지 특정 partition인지 확인
2. 특정 event_type에서 실패가 많은지 확인
3. downstream dependency 상태 확인
4. consumer rebalance 빈도 확인
5. 최근 배포나 schema 변경 확인

대응:

- 모든 partition lag면 consumer 처리량 또는 downstream 병목을 본다
- 특정 partition lag면 hot aggregate/key skew를 본다
- poison message면 DLQ 격리 후 partition 진행을 회복한다
- retry 폭증이면 backoff와 max attempt를 조정한다

주의:

consumer 수를 늘리는 것이 항상 답은 아니다. partition 수보다 consumer가 많으면 효과가 없고, downstream DB가 병목이면 오히려 더 큰 부하를 만들 수 있다.

### 시나리오 4: 중복 부작용 발생

증상:

- 같은 주문에 배송 요청이 2개 생성됨
- 포인트가 두 번 적립됨
- 알림이 중복 발송됨

확인 순서:

1. 같은 event_id가 중복 처리되었는지 확인
2. event_id는 다른데 같은 aggregate/event_type이 중복 발생했는지 확인
3. producer가 같은 비즈니스 사건에 대해 outbox row를 두 번 만들었는지 확인
4. consumer idempotency key가 잘못 잡혔는지 확인
5. 수동 replay나 DLQ replay가 있었는지 확인

대응:

- 같은 event_id 중복이면 consumer 멱등성 결함이다
- event_id가 다르면 producer command 중복, 사용자 재시도, 도메인 invariant 문제를 본다
- 외부 발송 중복이면 idempotency key 전달 여부를 확인한다

중요한 구분:

```text
same event_id duplicated    -> delivery duplicate
different event_id same fact -> domain duplicate or command duplicate
```

이 둘을 섞으면 잘못된 곳을 고치게 된다.

### 시나리오 5: 이벤트 순서 역전

증상:

- projection이 이전 상태로 돌아감
- 취소된 주문이 다시 결제 완료로 보임
- consumer 로그에 version gap이 보임

확인 순서:

1. Kafka key가 aggregate_id인지 확인
2. 같은 aggregate 이벤트가 같은 topic/partition에 들어갔는지 확인
3. retry topic 처리로 순서가 깨졌는지 확인
4. consumer 내부 병렬 처리로 순서가 깨졌는지 확인
5. aggregate_version이 단조 증가하는지 확인

대응:

- key 오류면 topic 재설계 또는 producer mapping 수정
- retry topic으로 인한 역전이면 retry 정책 변경
- consumer 내부 thread pool 문제면 partition별 순서 보존 queue 도입
- projection에는 aggregate_version guard를 추가

---

## Consumer 구현 패턴: poll loop에서 무엇을 조심해야 하나

Kafka consumer 구현은 프레임워크가 감춰주는 부분이 많지만, CDC Outbox 이벤트에서는 몇 가지 원칙을 코드에 명확히 반영해야 한다.

### 원칙 1: offset commit은 부작용 이후

메시지를 poll한 직후 offset을 commit하면 처리 실패 시 이벤트를 잃은 것처럼 된다. 적어도 해당 consumer의 관점에서는 다시 읽을 기회가 사라진다.

```text
poll -> process business side effect -> commit offset
```

물론 이 순서에서는 process 성공 후 commit 전에 죽으면 중복이 생긴다. 그래서 멱등성이 필요하다. 즉 offset commit 순서와 멱등성은 한 묶음이다.

### 원칙 2: 긴 외부 호출로 poll loop를 막지 않는다

외부 API가 30초씩 걸리면 `max.poll.interval.ms`를 넘겨 consumer group에서 쫓겨날 수 있다. 처리 시간이 긴 작업은 내부 queue, worker pool, pause/resume, batch 크기 조정으로 제어해야 한다.

하지만 worker pool을 쓰면 순서 보존이 깨질 수 있다. 따라서 partition별 순서가 필요한지 먼저 정해야 한다.

가능한 구조:

```text
poll thread
  -> partition별 work queue
  -> partition worker는 순차 처리
  -> 처리 완료 offset 추적
  -> 안전한 offset만 commit
```

이 구조는 단순 consumer보다 복잡하지만, 같은 partition 순서를 유지하면서 처리와 poll을 분리할 수 있다.

### 원칙 3: poison message가 partition 전체를 영원히 막지 않게 한다

항상 실패하는 메시지가 하나 있으면 그 partition은 진행하지 못한다. 순서를 엄격히 지키려면 이게 맞을 수도 있지만, 운영에서는 격리 기준이 필요하다.

정책 예:

- 재시도 가능한 오류는 최대 5회 backoff
- validation 오류는 DLQ 후 offset commit
- 비즈니스 선행 상태가 없는 경우 짧은 retry 후 parking lot topic
- 운영자가 수정 후 replay

DLQ 후 offset commit은 "그 이벤트를 정상 처리한 것으로 간주"하는 결정이다. 그래서 DLQ 운영과 replay 절차가 반드시 있어야 한다.

### 원칙 4: Consumer 로그에는 event_id가 반드시 있어야 한다

장애 분석에서 `offset=12345`만 있으면 부족하다. offset은 topic/partition에 종속적이고, 사용자 문의나 업무 테이블과 연결하기 어렵다.

로그 필드:

```text
event_id
event_type
aggregate_type
aggregate_id
aggregate_version
topic
partition
offset
consumer_group
trace_id
```

이 정도가 있어야 한 이벤트의 전체 흐름을 추적할 수 있다.

---

## 보안과 개인정보: 이벤트는 한번 퍼지면 회수하기 어렵다

Outbox 이벤트는 여러 consumer, Kafka topic retention, backup, data lake, log, DLQ에 복제될 수 있다. 그래서 개인정보를 payload에 넣는 결정은 DB 컬럼 하나 추가보다 훨씬 무겁다.

### 최소 공개 원칙

이벤트에는 consumer가 그 사건을 처리하는 데 필요한 최소 정보만 넣는다.

나쁜 예:

```json
{
  "orderId": "order-100",
  "userId": "user-1",
  "userName": "Kim",
  "phone": "010-0000-0000",
  "address": "Seoul ...",
  "paymentCardLast4": "1234",
  "internalMemo": "VIP complaint"
}
```

좋은 예:

```json
{
  "orderId": "order-100",
  "userId": "user-1",
  "paymentId": "pay-100",
  "paidAt": "2026-06-10T11:50:00+09:00",
  "amount": {
    "currency": "KRW",
    "value": 39000
  }
}
```

알림 서비스가 전화번호가 필요하다면 이벤트에 전화번호를 넣을지, 알림 서비스가 user profile API를 조회할지 판단해야 한다. 이벤트에 넣으면 결합은 낮아지지만 개인정보 복제 범위가 넓어진다. API 조회로 바꾸면 개인정보 확산은 줄지만 조회 의존성과 장애 경계가 생긴다.

정답은 도메인과 규제에 따라 다르다. 중요한 것은 이 선택을 보안 리뷰 없이 개발 편의로 결정하지 않는 것이다.

### DLQ와 로그 마스킹

payload가 DLQ로 들어가면 운영자가 조회할 수 있다. 로그에도 payload를 찍을 수 있다. 이 경로는 DB 권한 모델보다 느슨한 경우가 많다.

기준:

- full payload logging 금지
- event_id와 aggregate_id 중심으로 로그 작성
- DLQ 조회 권한 제한
- 개인정보 포함 이벤트는 retention 짧게 설정
- data lake 복제 시 마스킹 또는 별도 보안 zone 사용

### 삭제 요청과 이벤트 retention

개인정보 삭제 요청이 들어왔을 때 Kafka 과거 이벤트까지 지울 수 있는가? 대부분 쉽지 않다. compacted topic이라도 tombstone과 retention이 복잡하고, 이미 consumer 저장소로 퍼진 데이터는 별도 삭제가 필요하다.

따라서 이벤트에 개인정보를 넣기 전에 "나중에 삭제할 수 있는가"를 물어야 한다.

---

## 성능 설계: 처리량은 outbox insert, DB log, Kafka partition이 함께 결정한다

CDC Outbox의 처리량은 한 지점으로만 결정되지 않는다.

```text
application write TPS
outbox insert overhead
DB WAL/binlog write volume
Debezium read/transform throughput
Kafka producer throughput
topic partition count
consumer processing throughput
```

어느 하나가 병목이 되면 전체 지연이 늘어난다.

### Outbox insert overhead

outbox row는 업무 트랜잭션 안에 추가 write를 만든다. payload가 크고 index가 많으면 commit latency가 늘어난다.

최적화 기준:

- payload는 필요한 만큼만 저장한다
- outbox table index를 최소화한다
- 조회용 index와 CDC source 목적을 혼동하지 않는다
- 대용량 payload는 object storage 참조로 분리할지 검토한다
- 같은 트랜잭션에 너무 많은 이벤트를 넣지 않는다

index는 특히 조심해야 한다. 운영자가 나중에 조회 편의를 위해 index를 계속 추가하면 outbox insert 경로가 느려진다. Outbox는 write-heavy 테이블이다.

### Kafka partition 수

partition 수는 병렬성과 순서 보장의 균형이다.

- partition이 너무 적으면 consumer 병렬성이 부족하다
- partition이 너무 많으면 broker metadata, file handle, rebalance 비용이 커진다
- aggregate_id key를 쓰면 hot aggregate가 특정 partition을 압박할 수 있다
- partition 수를 늘리면 key-to-partition mapping이 바뀔 수 있다

처음부터 완벽한 수를 맞추기는 어렵다. 대신 트래픽 추정과 growth plan을 둔다.

예:

```text
목표 peak: 5,000 events/sec
consumer 1개 안정 처리량: 250 events/sec
필요 active consumers: 20
여유 포함 partition: 48 또는 64
```

하지만 이벤트 순서가 중요한 aggregate에서 partition 수 변경이 어떤 영향을 주는지 확인해야 한다. 같은 key의 미래 이벤트가 다른 partition으로 갈 수 있는 producer partitioner 변경도 주의한다.

### Batch 크기와 latency

Debezium, Kafka producer, consumer 모두 batch 처리 설정이 있다. batch를 키우면 처리량은 좋아질 수 있지만 지연이 늘고 장애 시 재처리 단위가 커진다.

운영 기준:

- 결제/배송 이벤트는 낮은 지연이 중요하므로 batch를 과도하게 키우지 않는다
- 분석/집계 이벤트는 처리량 중심으로 batch를 키울 수 있다
- p99 latency와 throughput을 같이 본다
- "평균 100ms"보다 "최대 2분 지연"이 더 문제일 수 있다

### Backpressure

downstream이 느려졌을 때 어디서 압력을 흡수할지 정해야 한다.

가능한 위치:

- Kafka topic backlog
- consumer retry topic
- 내부 작업 queue
- DB outbox row 누적
- 사용자 요청 제한

가장 위험한 구조는 backpressure가 원본 DB 디스크로 돌아오는 것이다. connector가 멈춰 WAL/binlog가 쌓이고, 결국 원본 DB가 쓰기 불능이 되는 상황이다. CDC 파이프라인은 비동기라서 안전해 보이지만, source log retention 때문에 원본 DB와 연결되어 있다.

---

## 도메인 이벤트와 CDC row event를 구분하라

CDC를 쓰면 DB row 변경을 그대로 이벤트로 보내고 싶은 유혹이 생긴다. 하지만 Outbox 패턴에서는 도메인 이벤트와 row event를 구분하는 것이 중요하다.

### Row event

Row event는 "테이블의 row가 insert/update/delete되었다"는 사실이다.

예:

```text
orders.status changed from PENDING to PAID
```

이 정보는 DB 구조에 강하게 묶여 있다.

### Domain event

Domain event는 "비즈니스적으로 어떤 일이 발생했다"는 사실이다.

예:

```text
OrderPaid
PaymentCaptured
ShipmentRequested
CouponExpired
```

Domain event는 consumer가 이해해야 하는 계약이다. DB 컬럼명이 바뀌어도 이벤트 의미는 유지될 수 있다.

Outbox 테이블은 이 domain event를 담기 위한 장치다. Debezium은 transport 역할을 할 뿐이다.

나쁜 구조:

```text
orders table update CDC -> downstream consumer가 status 변경 해석
```

이 구조에서는 consumer가 `orders` 테이블 내부 컬럼과 상태 전이 규칙을 알아야 한다.

좋은 구조:

```text
order service domain logic -> outbox OrderPaid -> downstream consumer
```

이 구조에서는 이벤트 의미가 producer 도메인 안에서 결정된다.

### 언제 row-level CDC가 적합한가

물론 row-level CDC가 항상 나쁜 것은 아니다.

잘 맞는 경우:

- 데이터 웨어하우스 적재
- 검색 인덱스 동기화
- read replica 성격의 projection
- legacy DB 변경 추적
- audit log 수집

하지만 서비스 간 비즈니스 이벤트 통신에서는 row event보다 domain event가 더 안정적인 계약이다. Outbox는 그 경계를 만들기 위한 패턴이다.

---

## 이벤트 이름 짓기: 과거형 사실을 표현하라

Outbox 이벤트 이름은 consumer 모델을 결정한다. 이름이 애매하면 payload와 처리 정책도 흔들린다.

좋은 이벤트 이름은 이미 발생한 사실을 과거형으로 표현한다.

좋은 예:

- `OrderCreated`
- `OrderPaid`
- `PaymentCaptured`
- `ShipmentRequested`
- `CouponIssued`
- `UserEmailChanged`

나쁜 예:

- `CreateOrder`
- `PayOrder`
- `SendShipment`
- `UpdateStatus`
- `OrderEvent`
- `DataChanged`

명령과 이벤트를 섞으면 consumer가 의도를 잘못 해석한다. `PayOrder`는 누군가 결제를 하라는 명령처럼 보인다. `OrderPaid`는 결제가 완료되었다는 사실이다.

또한 `DataChanged` 같은 이름은 너무 넓다. consumer가 payload를 열어봐야 의미를 알 수 있다. 이벤트 타입이 라우팅과 처리 정책의 기준이라면 이름은 구체적이어야 한다.

### 이벤트 granularity

너무 작은 이벤트:

```text
OrderStatusUpdated
OrderPaidAtUpdated
OrderPaymentIdUpdated
```

너무 큰 이벤트:

```text
OrderChanged
```

적절한 이벤트:

```text
OrderPaid
OrderCancelled
OrderRefunded
```

기준은 "consumer가 독립적인 비즈니스 반응을 해야 하는 사건인가"다. 단순 필드 변경 하나하나를 이벤트로 만들면 noisy하고, 모든 것을 `Changed`로 뭉치면 의미가 사라진다.

---

## Idempotency 설계를 더 깊게 보기

멱등성은 이벤트 시스템의 보험이다. 하지만 보험도 약관을 알아야 작동한다.

### 자연 멱등과 인공 멱등

자연 멱등은 같은 요청을 여러 번 수행해도 결과가 원래 같은 경우다.

```sql
UPDATE orders
   SET status = 'PAID'
 WHERE order_id = 'order-100';
```

이미 `PAID`여도 다시 `PAID`로 설정하면 결과가 같다. 물론 updated_at이 매번 바뀐다면 완전한 멱등은 아니다.

인공 멱등은 event_id나 idempotency key를 저장해 중복 실행을 막는 방식이다.

```sql
INSERT INTO processed_events (consumer_name, event_id)
VALUES ('consumer-a', 'evt-900');
```

실무에서는 둘을 같이 쓴다.

- 상태 설정은 aggregate_version guard로 자연 멱등에 가깝게 만든다
- 누적 변경과 외부 부작용은 event_id로 인공 멱등을 만든다

### 멱등 키 선택

멱등 키는 무엇을 한 번만 해야 하는지에 따라 달라진다.

같은 이벤트 처리 한 번:

```text
key = event_id
```

같은 주문에 배송 요청 한 번:

```text
key = order_id + request_type
```

같은 결제 승인에 포인트 적립 한 번:

```text
key = payment_id + reward_policy_id
```

같은 사용자에게 같은 알림 템플릿 하루 한 번:

```text
key = user_id + template_id + business_date
```

무조건 event_id만 쓰면 부족할 수 있다. producer 버그로 같은 사건에 대해 다른 event_id가 두 개 만들어지면 event_id 멱등성은 막지 못한다. 도메인 invariant가 필요한 경우 domain key unique constraint를 추가해야 한다.

### Processed events 테이블의 보존 기간

processed_events도 무한히 커진다. 언제까지 보존해야 할까?

기준:

- Kafka topic retention 기간
- replay 가능 기간
- DLQ 재처리 가능 기간
- 외부 부작용 취소/보정 가능 기간
- 감사 요구

Kafka 이벤트를 14일 동안 replay할 수 있는데 processed_events를 3일만 보관하면, 10일 전 이벤트 replay 시 중복 방어가 사라진다. 멱등 키 보존 기간은 replay window보다 길어야 한다.

대안:

- 처리 결과 테이블 자체에 event_id를 남긴다
- ledger table을 장기 보관한다
- processed_events를 월별 partitioning한다
- 오래된 event_id는 compacted topic이나 object storage로 archive한다

### 멱등성과 트랜잭션 격리

동시에 같은 event_id가 처리될 수 있다. 예를 들어 consumer instance 두 개가 rebalance 과정에서 같은 메시지를 처리하거나, replay job과 실시간 consumer가 겹칠 수 있다.

따라서 "먼저 select로 확인하고 없으면 insert"는 race condition이 있다.

나쁜 예:

```sql
SELECT 1 FROM processed_events WHERE event_id = :event_id;
-- 없네?
UPDATE points SET balance = balance + 100;
INSERT INTO processed_events ...
```

좋은 예:

```sql
INSERT INTO processed_events (consumer_name, event_id)
VALUES (:consumer, :event_id);
-- unique violation이면 이미 처리된 것으로 보고 종료
```

unique constraint를 DB에 맡기는 것이 안전하다.

---

## Read model과 Projection 설계

CDC Outbox 이벤트는 read model을 만드는 데 자주 쓰인다. 예를 들어 주문 서비스의 이벤트를 검색 서비스, 관리자 대시보드, 정산 projection이 소비한다.

Projection 설계에서 중요한 것은 "이벤트를 순서대로 모두 처리하면 항상 정확하다"는 순진한 가정을 버리는 것이다.

### Projection은 재생 가능해야 한다

좋은 projection은 다음을 지원한다.

- 특정 시점부터 rebuild
- 특정 aggregate만 rebuild
- DLQ 수정 후 replay
- schema version 변경 후 backfill
- projection table truncate 후 전체 재처리

이를 위해 이벤트에는 충분한 정보가 있어야 한다.

- aggregate_id
- aggregate_version
- event_type
- event_id
- occurred_at
- 필요한 상태 값

너무 delta 중심 이벤트만 있으면 재생이 어렵다.

예:

```json
{
  "eventType": "OrderAmountIncreased",
  "delta": 1000
}
```

이 이벤트만으로는 중간 누락이나 중복에 취약하다. 반대로 아래처럼 변경 후 상태와 version을 포함하면 projection이 더 안전하다.

```json
{
  "eventType": "OrderAmountChanged",
  "orderId": "order-100",
  "aggregateVersion": 7,
  "amount": {
    "currency": "KRW",
    "value": 39000
  }
}
```

모든 이벤트가 full state를 가져야 한다는 뜻은 아니다. 하지만 projection 복구가 중요한 이벤트는 변경 후 기준 값을 포함하는 편이 운영이 쉽다.

### Projection 테이블의 last_event_id와 version

Projection table에는 마지막 처리 정보를 남기는 것이 좋다.

```sql
CREATE TABLE order_search_projection (
    order_id varchar(100) PRIMARY KEY,
    status varchar(30) NOT NULL,
    amount numeric(18, 2) NOT NULL,
    aggregate_version bigint NOT NULL,
    last_event_id uuid NOT NULL,
    last_event_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL
);
```

이 필드들은 장애 분석에 유용하다.

- 왜 화면 상태가 오래됐는가
- 어떤 이벤트까지 반영됐는가
- 특정 event_id가 projection에 반영됐는가
- 역전 이벤트가 무시됐는가

### Rebuild와 실시간 소비의 충돌

Projection rebuild를 할 때 실시간 consumer와 충돌할 수 있다.

방법:

1. 별도 projection table을 새로 만든 뒤 swap한다
2. rebuild consumer group을 별도로 사용한다
3. 실시간 이벤트를 잠시 멈추고 replay한다
4. snapshot + tailing 방식을 사용한다

대용량 시스템에서는 1번이 자주 안전하다.

```text
order_projection_v2_building
  -> replay complete
  -> validation
  -> switch read alias
  -> drop old table later
```

이런 운영을 하려면 이벤트 retention과 schema compatibility가 충분해야 한다.

---

## Outbox와 SAGA: 이벤트 발행은 분산 트랜잭션의 시작일 뿐이다

Outbox는 분산 트랜잭션을 마법처럼 해결하지 않는다. 여러 서비스가 함께 하나의 업무를 완성해야 한다면 SAGA나 process manager가 필요할 수 있다.

예를 들어 주문 결제 후 배송 예약과 포인트 적립이 필요하다고 하자.

```text
OrderPaid
  -> ShippingRequested
  -> PointAccrued
```

배송 예약은 성공했는데 포인트 적립이 실패하면 어떻게 할까?

선택지:

- 포인트 적립을 retry한다
- 포인트 적립 실패를 사용자에게 별도 보정한다
- 배송도 취소하는 보상 트랜잭션을 실행한다
- 주문 상태를 `PAID_BUT_REWARD_PENDING`으로 둔다

Outbox는 `OrderPaid`가 누락되지 않도록 돕는다. 하지만 이후 서비스들의 성공/실패 조합을 어떻게 업무 상태로 표현할지는 별도 설계다.

### Process manager

복잡한 흐름에서는 process manager가 이벤트를 소비하며 장기 상태를 관리한다.

```text
order_process
  order_id
  payment_status
  shipping_status
  reward_status
  current_step
  last_event_id
  updated_at
```

Process manager도 이벤트 consumer이므로 멱등해야 한다. 그리고 자신이 새 command나 event를 만들 때도 outbox를 쓸 수 있다.

### 보상 이벤트

분산 시스템에서는 실패를 롤백보다 보상으로 다루는 경우가 많다.

예:

- `ShipmentReservationCancelled`
- `PointAccrualReversed`
- `PaymentRefundRequested`

보상 이벤트도 일반 이벤트와 똑같이 event_id, causation_id, correlation_id를 가져야 한다. 그래야 "왜 이 보상이 실행됐나"를 추적할 수 있다.

---

## 팀 운영 규칙: 패턴보다 합의가 중요하다

CDC Outbox는 여러 팀이 함께 쓰는 순간 운영 규칙이 필요하다. 규칙 없이 각 팀이 payload, topic, key, retry를 다르게 만들면 플랫폼은 금방 복잡해진다.

### 이벤트 리뷰 체크 항목

새 이벤트를 추가할 때 리뷰해야 할 질문:

- 이벤트 이름은 과거형 사실인가
- 이 이벤트를 소비할 팀은 누구인가
- payload 필드는 최소인가
- 개인정보가 포함되는가
- key는 무엇이며 ordering 요구와 맞는가
- event_version은 어떻게 올릴 것인가
- breaking change 시 새 이벤트 타입으로 분리할 것인가
- replay 가능한가
- consumer 멱등 키는 무엇인가
- DLQ로 갔을 때 운영자가 이해할 수 있는가

### 공통 라이브러리의 범위

Outbox event 생성 코드는 공통 라이브러리로 어느 정도 표준화할 수 있다.

공통화하기 좋은 것:

- event_id 생성
- metadata 필드
- trace/correlation 전파
- JSON serialization 규칙
- outbox repository 기본 구현
- test fixture

공통화하면 위험한 것:

- 모든 도메인 payload base class 강제
- event_type enum 중앙 집중
- 모든 서비스의 topic route를 하나의 거대한 설정으로 관리
- 도메인별 version 정책까지 라이브러리에 숨기기

공통화는 반복 실수를 줄이는 데 써야지 도메인 표현력을 빼앗으면 안 된다.

### 문서화

각 이벤트는 최소한 아래 문서를 가져야 한다.

```text
event_type: OrderPaid
version: 1
producer: order-service
topic: Order.events
key: orderId
meaning: 주문 결제가 승인되어 주문 상태가 PAID가 되었음
when emitted: payment approval transaction commit
idempotency key: event_id
ordering key: order_id
schema: link
consumers:
  - shipping-service
  - point-service
  - notification-service
retention: 14 days
pii: none
replay policy: allowed
```

이 정도 문서가 없으면 나중에 consumer가 늘어날수록 이벤트 의미가 흐려진다.

---

## 예제로 보는 전체 장애 흐름 추적

실제 문의가 들어왔다고 가정해 보자.

> "고객은 결제를 완료했는데 배송 요청이 생성되지 않았습니다."

CDC Outbox 구조에서는 다음 순서로 추적한다.

### 1단계: 주문 서비스 DB 확인

```sql
SELECT order_id, status, paid_at, version
  FROM orders
 WHERE order_id = 'order-100';
```

상태가 `PAID`라면 비즈니스 변경은 성공했다.

### 2단계: Outbox row 확인

```sql
SELECT event_id, event_type, aggregate_id, aggregate_version, occurred_at, created_at
  FROM outbox_events
 WHERE aggregate_type = 'Order'
   AND aggregate_id = 'order-100'
 ORDER BY created_at;
```

`OrderPaid` row가 없다면 애플리케이션 트랜잭션 안에서 outbox insert가 누락된 것이다. 이 경우 Debezium이나 Kafka를 볼 필요가 없다. producer 코드 문제다.

### 3단계: Kafka topic 확인

event_id로 Kafka topic을 검색한다. 찾을 수 없다면 Debezium 또는 Kafka Connect 경계에서 막힌 것이다.

확인:

- connector status
- connector lag
- DLQ
- schema registry error
- topic input rate

### 4단계: Consumer 처리 확인

Kafka에는 있는데 배송 요청이 없다면 shipping-service consumer 문제다.

확인:

```sql
SELECT *
  FROM processed_events
 WHERE consumer_name = 'shipping-service'
   AND event_id = 'evt-900';
```

없다면 consumer가 아직 처리하지 않았거나 DLQ로 보냈을 수 있다. 있다면 처리했다고 표시했지만 부작용이 빠진 것이다. 이 경우 processed_events와 shipment insert가 같은 트랜잭션인지 의심해야 한다.

### 5단계: DLQ와 retry 확인

```text
event_id=evt-900
error=Missing shipping address
failed_at=...
```

비즈니스 validation 실패라면 배송 요청이 생성되지 않은 것이 정상일 수 있다. 이 경우 사용자 상태와 운영 알림이 그 사실을 반영해야 한다.

이 추적 흐름의 핵심은 event_id다. event_id가 없다면 각 시스템의 로그를 시간대와 order_id로 뒤져야 한다. event_id는 분산 이벤트 시스템의 사건 번호다.

---

## 설계 결론: "한 번만"보다 "다시 해도 안전하게"가 현실적이다

분산 시스템에서 exactly-once라는 표현은 매력적이지만, 비즈니스 부작용까지 포함하면 현실적으로 매우 까다롭다. Kafka의 transactional producer나 exactly-once semantics가 도움이 되는 영역은 있지만, DB, 외부 API, 이메일, 결제사, 검색 인덱스까지 포함한 전체 업무 처리의 exactly-once를 자동으로 보장하지는 않는다.

CDC Outbox에서 더 현실적인 목표는 다음이다.

- 이벤트 발행 의도는 DB 커밋과 함께 절대 잃지 않는다
- 메시지는 중복될 수 있다고 가정한다
- 모든 consumer는 중복 처리에 안전하다
- 순서가 필요한 범위는 aggregate 단위로 제한한다
- 늦게 온 이벤트와 누락된 gap을 감지한다
- 장애 구간은 event_id로 추적하고 재처리할 수 있다
- 이벤트 계약은 장기간 replay를 견딘다

이렇게 설계하면 "절대 실패하지 않는 시스템"은 아니지만, 실패했을 때 어디서 멈췄는지 알고 다시 처리할 수 있는 시스템이 된다. 실무에서 더 중요한 것은 대개 그쪽이다.

---

## 참조 아키텍처: 주문 서비스 기준으로 구성 요소를 배치하면

글 전체를 하나의 운영 아키텍처로 묶어보면 다음과 같다.

```text
┌────────────────────┐
│ Client / API        │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│ order-service       │
│ - domain logic      │
│ - transaction       │
│ - outbox insert     │
└─────────┬──────────┘
          │ same DB commit
          ▼
┌────────────────────┐
│ PostgreSQL / MySQL  │
│ - orders            │
│ - outbox_events     │
│ - WAL / binlog      │
└─────────┬──────────┘
          │ transaction log
          ▼
┌────────────────────┐
│ Debezium Connector  │
│ - offset            │
│ - snapshot policy   │
│ - outbox routing    │
└─────────┬──────────┘
          │ produce
          ▼
┌────────────────────┐
│ Kafka               │
│ - order.events      │
│ - DLQ / retry       │
└─────────┬──────────┘
          │ consume
          ▼
┌────────────────────┐
│ consumers           │
│ - shipping          │
│ - point             │
│ - notification      │
│ - projection        │
└────────────────────┘
```

이 구조에서 각 계층의 책임은 분명해야 한다.

### order-service의 책임

- 도메인 invariant를 검증한다
- 업무 상태를 변경한다
- 같은 트랜잭션에 outbox row를 넣는다
- 이벤트 payload를 도메인 계약으로 만든다
- event_id, aggregate_id, version을 부여한다
- Kafka 발행 성공 여부를 요청 처리 경로에서 직접 책임지지 않는다

order-service가 하면 안 되는 일:

- consumer별 payload를 따로 만든다
- downstream 처리 성공까지 같은 요청에서 기다린다
- Kafka 장애를 이유로 DB commit 이후 수동 보정 로직을 숨긴다
- outbox row 없이 Kafka에만 발행한다

### DB의 책임

- 비즈니스 변경과 outbox insert를 원자적으로 커밋한다
- transaction log를 CDC가 읽을 수 있게 보존한다
- outbox row를 일정 기간 보관한다
- index와 partition을 통해 write 경로를 안정적으로 유지한다

DB가 하면 안 되는 일:

- outbox를 장기 분석 테이블로 겸용한다
- 과도한 index로 insert 경로를 느리게 만든다
- connector lag와 무관하게 row를 성급히 purge한다
- CDC 계정에 불필요한 쓰기 권한을 준다

### Debezium의 책임

- source log를 읽는다
- 커밋된 outbox insert를 Kafka 이벤트로 변환한다
- offset을 관리한다
- 장애 후 재시작 가능한 위치를 유지한다
- transform 오류를 관측 가능한 실패로 드러낸다

Debezium이 하지 않는 일:

- 비즈니스 멱등성을 보장하지 않는다
- consumer 부작용 성공을 알지 못한다
- 이벤트 payload의 도메인 의미를 검증하지 않는다
- 부적절한 snapshot 정책의 결과를 자동으로 막지 않는다

### Kafka의 책임

- 이벤트를 partition 단위로 저장한다
- 같은 key가 같은 partition에 있을 때 순서를 유지한다
- consumer group별 offset을 관리할 수 있게 한다
- replay window를 제공한다

Kafka가 하지 않는 일:

- 전체 도메인 전역 순서를 보장하지 않는다
- external API 부작용을 exactly-once로 만들지 않는다
- 잘못 잡은 key를 고쳐주지 않는다
- consumer가 처리한 비즈니스 상태를 알지 못한다

### Consumer의 책임

- event_id로 중복을 견딘다
- aggregate_version으로 역전 이벤트를 막는다
- retry와 DLQ를 구분한다
- offset commit을 처리 완료 기준에 맞춘다
- 외부 부작용에는 idempotency key를 쓴다
- 처리 결과를 관측 가능하게 남긴다

이 책임 분리가 흐려지는 순간 장애 분석이 어려워진다. CDC Outbox는 여러 컴포넌트가 관여하는 패턴이므로 "누가 무엇을 보장하는가"를 팀 전체가 같은 언어로 이해해야 한다.

---

## 코드 구조 예시: 애플리케이션 내부에서는 어떻게 나누는가

Spring Boot를 예로 들면, outbox 코드는 도메인 서비스에 너무 깊게 섞지 않는 편이 좋다. 하지만 완전히 외부 인프라로 숨겨서도 안 된다. 이벤트가 도메인 계약이기 때문이다.

### 도메인 이벤트 객체

```java
public record OrderPaidEvent(
    UUID eventId,
    String orderId,
    long aggregateVersion,
    Instant paidAt,
    Money amount,
    UUID correlationId,
    UUID causationId
) {
    public String eventType() {
        return "OrderPaid";
    }

    public int eventVersion() {
        return 1;
    }
}
```

이 객체는 Kafka 메시지 클래스라기보다 도메인 사건 표현이다. Kafka header나 Debezium envelope를 모르도록 유지하는 것이 좋다.

### Outbox mapper

```java
public final class OutboxEventMapper {
    private final ObjectMapper objectMapper;

    public OutboxEvent toOutbox(OrderPaidEvent event) {
        return new OutboxEvent(
            event.eventId(),
            "Order",
            event.orderId(),
            event.eventType(),
            event.eventVersion(),
            event.aggregateVersion(),
            event.paidAt(),
            toJson(event),
            TraceContext.currentTraceId(),
            event.correlationId(),
            event.causationId(),
            "order-service"
        );
    }

    private JsonNode toJson(OrderPaidEvent event) {
        return objectMapper.valueToTree(Map.of(
            "orderId", event.orderId(),
            "aggregateVersion", event.aggregateVersion(),
            "paidAt", event.paidAt().toString(),
            "amount", event.amount()
        ));
    }
}
```

mapper를 두면 도메인 이벤트와 저장 형식을 분리할 수 있다. 나중에 outbox 테이블 필드가 바뀌거나 payload schema가 바뀌어도 도메인 로직 전체를 흔들지 않는다.

### Transactional service

```java
@Service
public class OrderPaymentService {
    private final OrderRepository orderRepository;
    private final OutboxRepository outboxRepository;
    private final OutboxEventMapper outboxEventMapper;

    @Transactional
    public void markPaid(MarkPaidCommand command) {
        Order order = orderRepository.getForUpdate(command.orderId());
        OrderPaidEvent event = order.markPaid(command.payment());

        orderRepository.save(order);
        outboxRepository.save(outboxEventMapper.toOutbox(event));
    }
}
```

여기서 `order.markPaid()`가 event를 반환하는 방식은 취향에 따라 다르다. 중요한 것은 outbox 저장이 같은 transaction 안에 있다는 점이다.

### 테스트 포인트

이 서비스의 핵심 테스트는 다음이다.

```java
@Test
void paymentAndOutboxAreCommittedTogether() {
    paymentService.markPaid(command);

    Order order = orderRepository.find(command.orderId());
    List<OutboxEvent> events = outboxRepository.findByAggregateId(command.orderId());

    assertThat(order.status()).isEqualTo(PAID);
    assertThat(events).hasSize(1);
    assertThat(events.get(0).eventType()).isEqualTo("OrderPaid");
}
```

그리고 outbox 저장 실패 시 주문 상태가 롤백되는 테스트도 필요하다.

```java
@Test
void rollbackOrderWhenOutboxInsertFails() {
    outboxRepository.forceFailure();

    assertThatThrownBy(() -> paymentService.markPaid(command))
        .isInstanceOf(RuntimeException.class);

    Order order = orderRepository.find(command.orderId());
    assertThat(order.status()).isEqualTo(PENDING);
}
```

이 테스트는 단순해 보이지만 outbox 패턴의 핵심을 검증한다.

---

## Outbox payload 설계 예시: 좋은 이벤트와 나쁜 이벤트

같은 `OrderPaid`라도 payload 설계에 따라 운영성이 크게 달라진다.

### 너무 빈약한 이벤트

```json
{
  "orderId": "order-100"
}
```

장점:

- payload가 작다
- 개인정보 노출 위험이 낮다

단점:

- 모든 consumer가 order-service API를 다시 조회해야 한다
- order-service 장애가 downstream 전체 장애로 번진다
- replay 시점에 조회한 주문 상태가 이벤트 발생 당시 상태와 다를 수 있다
- consumer가 어떤 금액/시각 기준으로 처리해야 하는지 모른다

이벤트가 너무 빈약하면 사실상 "알림 신호"일 뿐이다. 이 방식이 맞는 경우도 있지만, 모든 consumer가 원본 API를 조회해야 하면 이벤트 기반 구조의 장점이 줄어든다.

### DB row 복사 이벤트

```json
{
  "id": "order-100",
  "status": "PAID",
  "created_at": "2026-06-10 10:00:00",
  "updated_at": "2026-06-10 11:50:00",
  "buyer_name": "Kim",
  "buyer_phone": "010-0000-0000",
  "shipping_zipcode": "12345",
  "shipping_address1": "Seoul ...",
  "shipping_address2": "...",
  "payment_provider": "card",
  "payment_raw_response": "{...}",
  "admin_memo": null
}
```

장점:

- consumer가 많은 정보를 즉시 쓸 수 있다
- 추가 조회가 줄어든다

단점:

- DB 컬럼이 이벤트 계약으로 새어 나간다
- 개인정보가 과도하게 퍼진다
- payload가 커진다
- schema 변경 영향이 커진다
- 내부 필드와 외부 계약이 섞인다

이 방식은 CDC row event에 가깝다. 도메인 이벤트라기보다는 테이블 복제다.

### 균형 잡힌 도메인 이벤트

```json
{
  "eventId": "evt-900",
  "eventType": "OrderPaid",
  "eventVersion": 1,
  "orderId": "order-100",
  "aggregateVersion": 12,
  "userId": "user-1",
  "paymentId": "pay-900",
  "paidAt": "2026-06-10T11:50:00+09:00",
  "amount": {
    "currency": "KRW",
    "value": 39000
  },
  "orderLines": [
    {
      "orderLineId": "line-1",
      "productId": "product-1",
      "quantity": 1,
      "paidAmount": {
        "currency": "KRW",
        "value": 39000
      }
    }
  ]
}
```

이 이벤트는 `OrderPaid`라는 사건을 처리하는 데 필요한 핵심 정보를 담는다. 하지만 배송 주소, 전화번호, 관리자 메모, 결제사 원문 응답 같은 민감하거나 내부적인 정보는 제외한다.

여기서도 정답은 도메인마다 다르다. 배송 서비스가 주소를 반드시 이벤트에서 받아야 한다면 주소를 포함할 수 있다. 다만 그 결정은 개인정보 확산과 삭제 요구까지 고려해 내려야 한다.

---

## Topic 설계 패턴 비교

Outbox Event Router를 쓸 때 이벤트를 어떤 topic으로 보낼지 결정해야 한다. topic 구조는 consumer 확장성과 ordering, 권한, retention에 영향을 준다.

### 패턴 1: Aggregate별 topic

```text
order.events
payment.events
shipment.events
```

장점:

- 같은 aggregate 계열 이벤트를 한 흐름으로 볼 수 있다
- aggregate_id key로 순서 보장이 쉽다
- consumer가 도메인 단위로 구독하기 쉽다
- retention과 권한을 도메인 단위로 관리할 수 있다

단점:

- consumer가 관심 없는 event_type도 받아 필터링해야 할 수 있다
- topic 안에 여러 schema가 섞이므로 subject naming 전략이 필요하다
- 특정 event_type만 retention을 다르게 주기 어렵다

주문 도메인에서는 이 방식이 자주 무난하다.

### 패턴 2: Event type별 topic

```text
order.paid
order.cancelled
order.refunded
```

장점:

- consumer가 필요한 이벤트만 구독하기 쉽다
- topic별 schema가 단순하다
- event type별 retention과 권한을 다르게 주기 쉽다

단점:

- 같은 aggregate의 여러 event_type 간 순서 보장이 어려워진다
- topic 수가 빠르게 늘어난다
- consumer가 여러 topic을 조합해야 한다

이 방식은 이벤트 타입별 처리 주체가 뚜렷하고 순서 요구가 약할 때 잘 맞는다.

### 패턴 3: 서비스별 outbox raw topic

```text
orders_cdc.public.outbox_events
```

Debezium 기본 topic을 그대로 쓰는 방식이다.

장점:

- 설정이 단순하다
- 원본 CDC envelope를 모두 볼 수 있다
- 디버깅에는 정보가 많다

단점:

- consumer가 Debezium envelope에 결합된다
- topic 이름이 기술 구조를 노출한다
- event routing과 schema 관리가 애플리케이션 이벤트 관점과 어긋난다

운영 내부 검증 topic으로는 쓸 수 있지만, 여러 서비스가 장기간 소비하는 공개 이벤트 계약으로는 조심해야 한다.

### 선택 기준

질문:

- consumer는 도메인 단위로 구독하는가, event type 단위로 구독하는가
- 같은 aggregate의 순서가 중요한가
- topic별 권한/retention을 다르게 줘야 하는가
- schema registry subject naming을 어떻게 가져갈 것인가
- topic 수 증가를 운영할 수 있는가

대부분의 중간 규모 시스템에서는 aggregate별 topic으로 시작하고, 특정 이벤트가 독립적인 retention/권한/처리량 요구를 가질 때 event type별 topic을 분리하는 방식이 실용적이다.

---

## Retry topic 설계와 순서 보장의 충돌

Consumer 실패를 처리할 때 retry topic을 자주 쓴다.

```text
order.events
  -> order.events.retry.1m
  -> order.events.retry.10m
  -> order.events.dlq
```

이 구조는 일시 장애를 흡수하는 데 좋다. 하지만 순서 보장과 충돌한다.

예를 들어 같은 주문의 이벤트가 순서대로 들어왔다.

```text
1. OrderPaid(order-100, version=12)
2. OrderCancelled(order-100, version=13)
```

`OrderPaid` 처리 중 downstream 장애가 발생해 retry topic으로 빠졌다. 원래 topic에서는 offset이 commit되어 다음 이벤트가 진행된다. 그러면 `OrderCancelled`가 먼저 처리될 수 있다.

이게 문제인지 아닌지는 도메인에 따라 다르다.

문제가 아닌 경우:

- consumer가 최종 상태 projection이고 aggregate_version guard가 있다
- `OrderCancelled`가 더 최신 상태이므로 먼저 처리되어도 괜찮다
- 늦게 온 `OrderPaid` version 12는 무시된다

문제가 되는 경우:

- 배송 요청은 결제 이벤트를 반드시 먼저 처리해야 한다
- 취소 처리는 기존 배송 요청을 찾아 취소하는 방식이다
- 선행 이벤트가 없으면 후행 이벤트 처리 자체가 실패한다

이 경우 retry topic은 순서 문제를 만들 수 있다.

대안:

- partition을 막더라도 같은 aggregate 순서를 유지한다
- aggregate별 상태 머신에서 gap을 감지하고 보류한다
- retry topic에도 aggregate_id key를 유지하고 consumer에서 version guard를 둔다
- 선행 이벤트 없이도 후행 이벤트를 처리할 수 있게 consumer를 설계한다
- projection은 최신 상태 기준, side effect는 process manager 기준으로 분리한다

Retry topic은 무조건 좋은 패턴이 아니다. 실패 격리와 순서 보장 중 무엇이 더 중요한지 도메인별로 결정해야 한다.

---

## 모니터링 대시보드 구성 예시

CDC Outbox를 운영한다면 대시보드는 단순히 Kafka lag만 보여주면 부족하다. 한 화면에서 전체 흐름을 봐야 한다.

### Producer / Application 패널

- order-service request rate
- payment success count
- outbox insert count
- outbox insert failure count
- transaction rollback count
- outbox insert latency

핵심 비교:

```text
payment success count == OrderPaid outbox insert count
```

물론 모든 결제가 이벤트를 만드는 정책인지 확인해야 한다. 이 비율이 갑자기 깨지면 producer 경계 문제다.

### DB / CDC 패널

- WAL/binlog retained size
- replication slot lag
- connector source lag
- connector task status
- connector restart count
- snapshot running 여부
- outbox table row count
- outbox table size

핵심 알림:

```text
connector failed > 0
replication slot lag > threshold
WAL retained size growth rate > threshold
```

### Kafka 패널

- topic input rate
- produce error rate
- topic partition skew
- under replicated partitions
- broker request latency
- message size p95/p99

핵심 비교:

```text
outbox insert rate ~= order.events input rate
```

약간의 지연은 정상이다. 하지만 장시간 차이가 벌어지면 CDC 경계에 문제가 있다.

### Consumer 패널

- consumer group lag by partition
- processing success/failure rate
- processing latency p50/p95/p99
- DLQ count by error code
- retry count by attempt
- duplicate event count
- stale aggregate version count
- external API latency/error

핵심 지표:

```text
end_to_end_latency_p99
duplicate_event_rate
dlq_rate
stale_event_rate
```

중복 이벤트가 0이어야 한다고 가정하지 말고, 중복이 발생했을 때 consumer가 정상적으로 no-op 처리하는지도 metric으로 봐야 한다.

### Business completion 패널

기술 지표만으로는 사용자가 겪는 문제를 놓칠 수 있다.

예:

- paid orders without shipment request > 10 minutes
- paid orders without point accrual > 10 minutes
- notification pending > 30 minutes
- refund requested but payment reversal missing

이 지표는 이벤트 파이프라인이 정상이어도 비즈니스 처리 누락을 잡아준다. 최종적으로 중요한 것은 topic lag가 아니라 업무 완료다.

---

## 운영 데이터 보정: 수동 재발행은 어떻게 안전하게 할까

어떤 시스템이든 수동 재발행이 필요해지는 날이 온다. 이때 절차가 없으면 운영자가 SQL과 Kafka CLI로 임기응변을 하게 되고, 그 과정에서 중복 부작용이 발생한다.

### 재발행 원칙

1. 원본 event_id를 유지할지 새 event_id를 만들지 결정한다
2. 같은 비즈니스 사건의 재처리라면 원본 event_id를 유지하는 편이 안전하다
3. 보상이나 정정 이벤트라면 새 event_id와 causation_id를 둔다
4. 재발행 대상 event_id 목록을 파일이나 테이블로 남긴다
5. dry-run으로 consumer 멱등 상태를 확인한다
6. 재발행 후 처리 결과를 대조한다

### 원본 이벤트 재발행

Kafka topic retention 안에 이벤트가 남아 있다면 offset 기반 replay가 가능하다. 하지만 특정 event_id만 골라 재발행하려면 별도 도구가 필요하다.

재발행 도구는 다음 기능을 가져야 한다.

- event_id 목록 입력
- 원본 topic에서 이벤트 조회
- target topic 선택
- headers 유지
- dry-run 출력
- replay reason 기록
- 실행자 기록

### Outbox row 기반 재발행

outbox row가 남아 있다면 그 row로 Kafka 이벤트를 다시 만들 수 있다. 하지만 Debezium route와 동일한 변환을 재현해야 한다.

위험:

- 원래 Kafka header와 다르게 발행
- key를 다르게 잡아 partition이 바뀜
- schema version이 달라짐
- event_id를 새로 만들어 consumer 멱등성을 우회

따라서 수동 재발행 도구도 Debezium SMT와 같은 mapping 규칙을 공유하거나, 가능한 한 원본 Kafka 메시지를 replay하는 편이 낫다.

### 정정 이벤트

이미 잘못된 이벤트가 나갔다면 삭제보다 정정 이벤트가 더 명확할 때가 많다.

예:

```text
OrderPaid(event_id=evt-900, amount=39000)  -- 잘못된 금액
OrderPaymentCorrected(event_id=evt-901, correctedAmount=29000, causation_id=evt-900)
```

consumer는 정정 이벤트를 이해해야 한다. 모든 오류를 원본 이벤트 삭제로 해결하려고 하면 이미 퍼진 상태를 회수하기 어렵다.

---

## 비용 관점: CDC Outbox는 어디에 비용을 만든다

아키텍처 결정에는 비용도 포함된다.

### DB 비용

- outbox insert write amplification
- WAL/binlog 증가
- outbox table storage
- index storage
- backup size 증가
- purge/vacuum 비용

특히 payload가 크면 DB와 Kafka 양쪽에 비용이 생긴다. 이벤트 payload는 계약이면서 비용 단위다.

### Kafka 비용

- topic storage
- replication factor에 따른 저장 배수
- network egress
- consumer replay 비용
- DLQ/retry topic 추가 저장

retention을 길게 잡으면 replay는 쉬워지지만 storage 비용이 커진다. compacted topic을 쓰는 경우에도 key 설계와 tombstone 정책을 이해해야 한다.

### 운영 비용

- Debezium/Kafka Connect 운영
- connector 배포와 설정 관리
- schema registry 운영
- 모니터링/알림
- 장애 대응 훈련
- 재처리 도구 개발

작은 팀에서 이 비용을 감당하기 어렵다면 polling outbox가 더 나을 수 있다. 반대로 이벤트가 핵심 업무 경로라면 이 비용은 안정성을 위한 투자다.

---

## 최종 설계 샘플: 운영 기준표

마지막으로 실제 설계 리뷰에서 쓸 수 있는 기준표 형태로 정리해 보자.

```text
Pattern: CDC Outbox
Service: order-service
Database: PostgreSQL
CDC: Debezium PostgreSQL connector
Broker: Kafka

Outbox table:
  name: public.outbox_events
  primary key: event_id
  partitioning: monthly by created_at
  retention: 14 days in DB, 90 days archived

Event metadata:
  event_id: UUID v7
  aggregate_type: Order
  aggregate_id: orderId
  aggregate_version: order.version
  event_type: past-tense domain event
  event_version: integer
  occurred_at: domain event time
  trace_id/correlation_id/causation_id: propagated

Kafka:
  topic: order.events
  key: aggregate_id
  partitions: 64
  retention: 14 days
  schema: TopicRecordNameStrategy

Debezium:
  snapshot.mode: never after cutover
  publication: outbox only
  slot alert: retained WAL > threshold
  connector DLQ: enabled

Consumer:
  delivery assumption: at-least-once
  idempotency: event_id unique per consumer
  ordering: aggregate_version guard
  retry: bounded backoff
  DLQ: replayable with reason code

Operations:
  dashboard: app -> DB -> connector -> Kafka -> consumer -> business completion
  runbook: connector failure, log retention gap, DLQ replay, duplicate side effect
  replay: event_id based, audited
```

이 정도가 문서화되어 있으면 팀이 바뀌어도 시스템의 의도를 복원할 수 있다. 반대로 이런 기준 없이 "Debezium으로 outbox 흘립니다"만 남아 있으면 장애 때마다 같은 질문을 반복하게 된다.

---

## 마지막 검산: 이 패턴을 도입하기 전 스스로 물어볼 질문

CDC Outbox는 도입 결정을 내리는 순간보다 운영 6개월 뒤에 진짜 가치가 드러난다. 그래서 설계 리뷰 마지막에는 아래 질문을 꼭 던지는 편이 좋다.

- 이 이벤트가 누락되면 실제로 어떤 비즈니스 피해가 생기는가
- 중복되면 어떤 부작용이 생기며, 지금 consumer가 그것을 막는가
- 같은 aggregate의 순서가 깨졌을 때 감지할 수 있는가
- connector가 12시간 멈추면 DB, Kafka, consumer는 각각 어떤 상태가 되는가
- snapshot을 다시 수행하면 과거 이벤트가 재발행되는가
- event_id 하나로 전체 경로를 추적할 수 있는가
- DLQ에 들어간 이벤트를 누가 어떤 도구로 재처리하는가
- payload에 1년 뒤 삭제하기 어려운 개인정보가 들어 있지는 않은가
- topic retention보다 processed_events 보존 기간이 짧지는 않은가
- schema breaking change가 코드 리뷰나 CI에서 막히는가
- outbox purge가 connector lag와 충돌하지 않는가
- 운영자가 토요일 새벽에도 runbook만 보고 복구할 수 있는가

이 질문에 답하지 못한 상태에서 패턴만 도입하면 복잡도만 늘어난다. 반대로 답을 문서와 테스트, 알림, 재처리 도구로 고정해두면 CDC Outbox는 서비스 간 이벤트 전달의 아주 강한 기본기가 된다.

개인적으로 이 패턴의 핵심은 Debezium이 아니다. Debezium은 좋은 운반 장치다. 진짜 핵심은 "비즈니스 사건을 잃지 않는 기록으로 만들고, 그 기록이 여러 시스템을 지나며 중복·지연·실패를 만나도 다시 설명 가능하게 만드는 것"이다.

그래서 CDC Outbox를 잘 설계한 팀은 장애가 없어서 강한 것이 아니라, 장애가 났을 때 다음 질문에 빠르게 답할 수 있어서 강하다.

```text
그 사건은 생성됐는가?
어느 event_id인가?
Kafka까지 갔는가?
어떤 consumer가 처리했는가?
어디서 실패했는가?
다시 처리해도 안전한가?
```

이 여섯 질문에 답할 수 있으면 이벤트 기반 시스템은 운영 가능한 시스템이 된다. 답할 수 없다면 아직 패턴이 아니라 연결만 만든 것이다.

마지막으로, CDC Outbox를 처음 도입하는 팀이라면 모든 이벤트를 한 번에 옮기지 않는 것이 좋다. 결제, 배송, 포인트처럼 실패 비용이 큰 이벤트는 오히려 가장 나중에 옮기는 편이 안전할 수 있다. 먼저 검색 projection, 내부 통계, 캐시 갱신처럼 중복과 지연을 상대적으로 쉽게 흡수할 수 있는 consumer로 운영 감각을 만든다. 그 과정에서 connector 배포, lag 알림, DLQ replay, schema 변경, purge job을 실제로 한 번씩 겪어보면 결제성 이벤트를 옮길 때 훨씬 덜 위험하다.

반대로 처음부터 가장 중요한 업무를 옮겨도 되는 조건도 있다. 이미 Kafka consumer 멱등성이 검증되어 있고, Debezium 운영 경험이 있으며, outbox retention과 replay 도구가 준비되어 있고, 장애 대응 훈련까지 끝난 팀이라면 핵심 이벤트부터 표준화하는 것이 장기적으로 낫다. 결국 순서는 조직의 준비도 문제다. 패턴 자체보다 중요한 것은 팀이 그 패턴의 실패 모드를 알고 있는지다.

CDC Outbox는 "이벤트 기반 아키텍처를 멋지게 보이게 하는 장식"이 아니다. 업무 상태 변경이 여러 서비스로 퍼지는 순간 생기는 가장 위험한 간극을 정면으로 다루는 운영 패턴이다. 그래서 이 패턴을 설계할 때는 라이브러리 선택보다 장애 질문, 재처리 질문, 삭제 질문, 비용 질문을 먼저 해야 한다. 그 질문들이 답을 얻으면 구현은 비교적 단순해진다. 답이 없으면 구현이 아무리 깔끔해도 운영에서 흔들린다.

좋은 기준은 단순하다. 새 이벤트를 만들 때마다 "이 이벤트를 6개월 뒤 새 consumer가 처음부터 재생해도 안전한가"를 묻는다. 안전하지 않다면 무엇이 부족한지 드러난다. 스키마일 수도 있고, version일 수도 있고, idempotency key일 수도 있고, 개인정보 최소화일 수도 있다. 이 질문 하나가 설계를 꽤 많이 바로잡아 준다.

또 하나의 질문도 유용하다. "이 이벤트가 두 번 오면 돈, 재고, 알림, 권한 중 무엇이 두 번 바뀌는가?" 이 질문에 바로 답하지 못하면 아직 consumer 설계가 끝난 것이 아니다.

그리고 그 답은 문서가 아니라 unique constraint, 상태 머신, replay 테스트, 알림 지표로 남아 있어야 한다.

그래야 다음 장애 때 사람이 기억에 의존하지 않는다.

시스템이 스스로 증거를 남겨야 한다.

그것이 운영 가능한 설계다.

핵심이다. 정말로. 그래서 반복해서 확인해야 한다.

---

## 한줄 정리

CDC Outbox는 DB 변경과 이벤트 발행 의도를 같은 커밋에 묶어 누락을 줄이는 패턴이고, 성공적인 운영의 핵심은 Debezium 자체보다 event_id 기반 멱등성, aggregate_id 기반 순서 설계, snapshot/lag/retention 관측, 그리고 오래 버틸 수 있는 이벤트 계약에 있다.
