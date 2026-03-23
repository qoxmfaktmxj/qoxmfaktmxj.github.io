---
layout: post
title: "Debezium CDC 실전: 운영 DB 변경 이벤트를 안전하게 스트리밍하는 기준"
date: 2026-03-23 11:40:00 +0900
categories: [data-infra]
tags: [study, data-infra, debezium, cdc, kafka, outbox, streaming, architecture]
---

## 배경: 왜 CDC를 지금 다시 봐야 할까?

서비스가 작을 때는 보통 애플리케이션 코드 안에서 모든 걸 해결하려고 한다. 주문을 저장하고, 그 직후 Kafka로 이벤트를 발행하고, 검색 인덱스를 갱신하고, 분석 적재 테이블까지 업데이트한다. 처음에는 이 방식이 가장 단순해 보인다.

문제는 트래픽과 조직 규모가 커질수록 아래 같은 장애가 반복된다는 점이다.

- DB 저장은 성공했는데 이벤트 발행이 실패한다
- 메시지는 발행됐는데 애플리케이션 트랜잭션은 롤백된다
- 같은 데이터를 여러 시스템으로 복제해야 해서 애플리케이션 코드가 점점 비대해진다
- 운영 DB를 기준으로 검색/분석/캐시 시스템을 동기화해야 하는데 배치 지연이 커진다
- 다른 팀이 "이 테이블 변경 이벤트를 실시간으로 받고 싶다"고 할 때마다 원본 서비스 수정이 필요하다

이때 CDC(Change Data Capture)는 단순한 "DB 변경 감지 기술"이 아니라, **운영 DB의 사실(fact)을 애플리케이션 코드와 분리된 방식으로 스트리밍 파이프라인에 연결하는 아키텍처 도구**가 된다.

특히 Debezium은 MySQL binlog, PostgreSQL WAL, Oracle redo log 같은 **DB의 변경 로그를 직접 읽어** Kafka로 흘려보내기 때문에, 단순 polling보다 훨씬 안정적이고 애플리케이션 침투도도 낮다.

다만 실무에서는 여기서 끝나지 않는다. Debezium을 붙인다고 바로 "이벤트 기반 아키텍처 완성"이 아니다. 실제로는 다음을 먼저 정해야 한다.

- 어떤 테이블을 CDC 대상으로 삼을 것인가
- 원본 테이블 CDC와 Outbox CDC 중 무엇을 택할 것인가
- snapshot, schema evolution, delete 이벤트를 어떻게 다룰 것인가
- 중복, 재처리, 순서 보장을 어디까지 시스템 계약으로 둘 것인가
- 장애 시 운영자가 어떤 지표를 보고 어디서 끊겼는지 파악할 수 있는가

오늘 글은 이 부분을 기준 중심으로 정리한다. 목표는 "Debezium 소개"가 아니라, **운영 환경에 넣었을 때 덜 망가지는 CDC 설계 기준**을 잡는 것이다.

---

## 먼저 큰 그림: CDC는 복제 기술이지, 비즈니스 의미를 자동으로 만들어주지 않는다

CDC를 처음 도입하는 팀이 가장 자주 하는 오해는 "테이블 변경을 읽으면 곧 도메인 이벤트를 얻는 것"이라고 생각하는 것이다. 실제로는 다르다.

예를 들어 `orders` 테이블에서 아래 변경이 발생했다고 하자.

- `status = CREATED`
- `status = PAID`
- `status = SHIPPED`

CDC가 내보내는 것은 기본적으로 **행(row)의 변경 사실**이다. 즉 "주문이 생성되었다"는 비즈니스 의미를 어느 정도 추론할 수는 있어도, DB 관점에서는 어디까지나 row image diff에 가깝다.

그래서 CDC 아키텍처는 보통 두 갈래로 나뉜다.

### 1) 원본 테이블 CDC

운영 테이블 자체의 insert/update/delete를 읽는다.

- 장점: 애플리케이션 수정이 적다
- 장점: 검색 인덱싱, 데이터 레이크 적재, 캐시 무효화처럼 **데이터 복제** 성격의 요구에 잘 맞는다
- 단점: 컬럼 변경이 곧 이벤트 계약 변경이 된다
- 단점: 비즈니스 의미가 모호할 수 있다
- 단점: update가 잦은 테이블에서는 노이즈가 많다

### 2) Outbox CDC

애플리케이션이 도메인 이벤트를 Outbox 테이블에 기록하고, Debezium이 그 Outbox를 읽는다.

- 장점: 이벤트 의미가 명확하다
- 장점: DB 트랜잭션과 이벤트 기록을 같은 경계에 둘 수 있다
- 장점: 외부 소비자에게 안정적인 이벤트 계약을 제공하기 쉽다
- 단점: 애플리케이션 쪽 Outbox 설계/운영 비용이 든다
- 단점: 테이블 정리, 재처리, 스키마 버전 관리까지 같이 고민해야 한다

정리하면,

- **검색/분석/동기화**가 목적이면 원본 테이블 CDC가 유리한 경우가 많고
- **업무 이벤트 전달**이 목적이면 Outbox CDC가 더 안전한 경우가 많다

이 구분을 흐리면 CDC가 편리한 복제 도구가 아니라, 시스템 간 결합을 더 키우는 함정이 된다.

---

## 핵심 개념 1: Debezium은 애플리케이션이 아니라 DB 로그를 읽는다

Debezium의 가장 큰 특징은 애플리케이션 레벨 hook이 아니라 **DB 복제 로그**를 읽는다는 점이다.

예를 들어 PostgreSQL에서는 WAL(Write-Ahead Log), MySQL에서는 binlog를 읽는다. 이 구조가 중요한 이유는 다음과 같다.

1. **변경 누락 가능성이 낮다**  
   polling처럼 `updated_at > last_seen` 조건으로 훑는 방식보다 훨씬 안정적이다. 초 단위 정밀도 문제나 clock skew, 페이지네이션 누락 같은 고전적 사고를 피하기 쉽다.

2. **원본 애플리케이션 부하를 덜 건드린다**  
   주기적으로 대량 스캔 쿼리를 날리지 않아도 된다. 물론 replication slot이나 binlog 보관 정책을 운영해야 하지만, 방식 자체는 polling보다 정교하다.

3. **변경 순서를 더 자연스럽게 보존한다**  
   같은 테이블/파티션/키 범위 안에서 변경 흐름을 추적하기 수월하다. 다만 이것이 곧 "전체 시스템 순서 보장"을 의미하는 것은 아니다.

여기서 중요한 현실 체크가 하나 있다.

> Debezium은 변경을 안정적으로 꺼내오는 도구이지, 소비자 정합성까지 자동 보장하는 도구는 아니다.

즉, Kafka로 이벤트가 흘러간 뒤에는 여전히 다음 문제가 남는다.

- 소비자 중복 처리(idempotency)
- 다운스트림 장애 시 재시도 정책
- 메시지 스키마 진화 전략
- 토픽 파티션 키 설계
- DLQ 여부와 복구 절차

많은 팀이 Debezium 도입만으로 문제를 끝냈다고 착각하는데, 실제 난이도는 그 다음 운영 설계에서 갈린다.

---

## 핵심 개념 2: Snapshot과 Streaming은 다른 문제다

Debezium 커넥터를 붙일 때 보통 처음 한 번 snapshot을 수행한다. 이때 초보 팀이 흔히 실수하는 부분은 snapshot과 streaming을 같은 성질의 작업으로 보는 것이다.

### Snapshot의 목적

- 기존 데이터를 한 번에 가져와 다운스트림 초기 상태를 만든다
- 검색 인덱스/분석 테이블/캐시 재구축의 출발점을 만든다

### Streaming의 목적

- snapshot 이후에 발생하는 변경분을 계속 반영한다

둘은 목적도, 장애 양상도 다르다.

### 실무에서 꼭 보는 포인트

#### 1) snapshot이 무거운 테이블에 미치는 영향

수천만 건 테이블을 낮 시간대에 snapshot하면 DB I/O, 네트워크, Kafka 적재량이 한꺼번에 치솟을 수 있다. 특히 처음 도입 시에는 "일단 전체 snapshot"보다 다음 판단이 먼저다.

- 정말 전체 백필이 필요한가?
- 최근 N개월 데이터만 먼저 적재해도 되는가?
- 오프피크 시간에 분리 수행할 수 있는가?
- 다운스트림이 snapshot burst를 감당할 수 있는가?

#### 2) snapshot 시점과 실시간 이벤트의 경계

초기 적재가 끝나기도 전에 운영 트래픽은 계속 변한다. 따라서 소비자는 "이 레코드가 snapshot에서 온 것인지, 실시간 변경분인지"를 구분할 수 있어야 할 때가 있다.

예를 들어 검색 인덱스를 만들 때는 snapshot 이벤트와 실시간 이벤트를 동일 로직으로 처리할 수 있지만, 알림 전송 같은 부수효과가 있는 소비자라면 snapshot 이벤트를 그대로 처리하면 안 된다.

#### 3) 재스냅샷 전략

스키마 변경, 다운스트림 데이터 손상, 신규 소비자 온보딩이 생기면 재스냅샷이 필요할 수 있다. 이때를 대비해 "커넥터 삭제 후 재생성"만 생각하면 운영이 거칠어진다.

- 특정 테이블만 다시 적재할 수 있는가
- 다운스트림에서 upsert 기반으로 안전하게 다시 받을 수 있는가
- snapshot 재수행 중 실시간 이벤트와 충돌하지 않는가

CDC에서 snapshot은 일회성 부팅 절차가 아니라, **복구 시나리오의 일부**로 봐야 한다.

---

## 핵심 개념 3: 원본 테이블 CDC와 Outbox CDC는 설계 철학이 다르다

이 부분이 가장 중요하다. 둘 다 Debezium으로 구현할 수 있지만, 잘 맞는 문제 자체가 다르다.

### 원본 테이블 CDC가 잘 맞는 경우

- Elasticsearch 인덱싱
- 데이터 웨어하우스 적재
- 캐시/서빙 테이블 동기화
- 운영 데이터의 near real-time 복제

이 경우 소비자는 "행이 이렇게 바뀌었다"는 사실이 중요하다. 예를 들어 상품 정보가 바뀌면 검색 인덱스를 업데이트하면 된다.

### Outbox CDC가 잘 맞는 경우

- 주문 생성, 결제 완료, 환불 접수 같은 업무 이벤트 발행
- 여러 서비스에 도메인 이벤트 계약을 안정적으로 제공해야 하는 경우
- DB 커밋과 이벤트 기록의 원자성을 최대한 맞추고 싶은 경우

이 경우 핵심은 row 복제가 아니라 **의미 있는 이벤트 계약**이다.

예를 들어 `orders.status = PAID`만 보고서는 아래를 알기 어렵다.

- 결제 성공이 최초 승인인지, 재승인인지
- 어떤 필드가 비즈니스적으로 중요 이벤트인지
- 외부 서비스가 알아야 할 최소 payload가 무엇인지
- 이후 컬럼 추가/변경이 소비자 계약에 어떤 영향을 주는지

이런 상황에서 원본 테이블 CDC를 바로 외부 계약으로 노출하면, 운영 DB 스키마가 곧 이벤트 API가 되어버린다. 이건 장기적으로 거의 항상 후회한다.

### 실무 판단 기준

아래 질문에 "예"가 많으면 Outbox CDC를 먼저 고려하는 편이 낫다.

- 이벤트의 의미를 명시적으로 설계해야 하는가?
- 다운스트림 소비자가 여러 팀/여러 시스템인가?
- 운영 DB 컬럼 구조를 외부에 드러내고 싶지 않은가?
- 한 트랜잭션에서 도메인 변경과 이벤트 기록을 함께 묶고 싶은가?
- 향후 이벤트 스키마 버전 관리가 필요할 가능성이 높은가?

반대로 아래에 가깝다면 원본 테이블 CDC도 충분히 현실적이다.

- 목적이 데이터 복제/색인/적재다
- 소비자가 내부 시스템 위주다
- update 의미를 소비자가 row state로 해석해도 무방하다
- 스키마 결합 위험을 감당할 수 있다

---

## 핵심 개념 4: 순서 보장보다 중요한 건 중복 무해화와 재처리 가능성이다

스트리밍 시스템을 설계할 때 많은 팀이 "exactly-once"라는 단어에 과도하게 집착한다. 하지만 CDC 실무에서는 대부분 **중복이 조금 생겨도 결과가 망가지지 않는 구조**가 더 현실적이다.

왜냐하면 실제 운영에서는 다음이 반복되기 때문이다.

- 커넥터 재시작
- 소비자 장애 후 재처리
- 네트워크 타임아웃 후 성공/실패 불확실성
- 스키마 변환기(SMT) 변경 후 재배포
- 다운스트림 저장소 일시 오류

이 환경에서 중요한 기준은 다음이다.

### 1) 이벤트 고유 식별자

Outbox CDC라면 `event_id`를 반드시 별도 컬럼으로 둔다. 소비자는 이 값을 기준으로 중복 무해화 전략을 세워야 한다.

### 2) upsert 가능한 다운스트림 모델

검색 인덱스, 서빙 테이블, 머티리얼라이즈드 뷰 성격의 저장소는 가능하면 insert-only보다 upsert 모델이 운영하기 쉽다. 같은 이벤트가 한 번 더 와도 최종 상태가 같아지기 때문이다.

### 3) 파티션 키 기준 정렬

전체 순서는 거의 환상에 가깝다. 대신 **어떤 엔티티 단위 순서가 중요한가**를 정하고, 그 키를 파티션 전략에 반영해야 한다. 주문 흐름이면 `order_id`, 계좌 흐름이면 `account_id` 같은 식이다.

### 4) 재처리 경로 문서화

운영자가 특정 시간대 이벤트를 다시 흘려보내야 할 때 절차가 명확해야 한다. "Kafka topic에 있으니 어떻게든 되겠지" 수준이면 장애 때 바로 막힌다.

즉, CDC 파이프라인의 품질은 "한 번만 보내는 능력"보다 **두 번 와도 덜 망가지는 능력**에 더 크게 좌우된다.

---

## 실무 예시: 주문 서비스 Outbox를 Debezium으로 Kafka에 연결하기

이제 가장 실전적인 형태로 보자. 상황은 아래와 같다.

- 주문 서비스는 PostgreSQL을 사용한다
- 주문 생성/결제 완료/취소 이벤트를 외부로 발행해야 한다
- DB 커밋과 이벤트 기록 정합성을 맞추고 싶다
- 소비자는 알림, 정산, 검색 인덱싱, 분석 적재 등 여러 시스템이다

이 경우 원본 `orders` 테이블 CDC보다 **Outbox CDC**가 더 적합하다.

### 1) Outbox 테이블 설계

```sql
create table outbox_event (
    id bigserial primary key,
    event_id uuid not null unique,
    aggregate_type varchar(100) not null,
    aggregate_id varchar(100) not null,
    event_type varchar(100) not null,
    payload jsonb not null,
    schema_version int not null default 1,
    occurred_at timestamptz not null,
    created_at timestamptz not null default now()
);

create index idx_outbox_event_created_at on outbox_event (created_at);
create index idx_outbox_event_aggregate on outbox_event (aggregate_type, aggregate_id);
```

핵심 포인트는 다음이다.

- `event_id`: 소비자 idempotency의 기준점
- `aggregate_type`, `aggregate_id`: 파티션 키나 라우팅 키 결정에 활용
- `event_type`: 다운스트림 분기 기준
- `payload`: 이벤트 계약 본문
- `schema_version`: 장기 운영 시 매우 중요

여기서 흔히 `status`, `retry_count`까지 Outbox 테이블에 넣는 경우가 있는데, Debezium이 로그 기반으로 읽어 Kafka에 내보낼 구조라면 polling publisher용 상태 컬럼이 꼭 필요하진 않다. 대신 보관/정리 정책은 별도로 준비해야 한다.

### 2) 애플리케이션 트랜잭션 안에서 도메인 변경과 Outbox insert를 같이 처리

```java
@Transactional
public Long createOrder(CreateOrderCommand cmd) {
    Order order = orderRepository.save(Order.create(cmd));

    OutboxEvent event = OutboxEvent.create(
        UUID.randomUUID(),
        "order",
        order.getId().toString(),
        "OrderCreated",
        objectMapper.writeValueAsString(Map.of(
            "orderId", order.getId(),
            "customerId", order.getCustomerId(),
            "totalAmount", order.getTotalAmount(),
            "orderedAt", Instant.now().toString()
        ))
    );

    outboxRepository.save(event);
    return order.getId();
}
```

이 구조의 본질은 간단하다.

- 주문 저장과 Outbox 기록은 **같이 커밋되거나 같이 롤백**된다
- Kafka 발행은 애플리케이션이 직접 하지 않는다
- 이후 Debezium이 DB 로그에서 Outbox insert를 읽어 토픽으로 내보낸다

즉, 서비스 코드는 "외부 브로커 전송 성공"을 책임지지 않고, **발행할 사실을 DB에 남기는 것**까지 책임진다.

### 3) Debezium Connector 설정 예시

```json
{
  "name": "order-outbox-connector",
  "config": {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "database.hostname": "postgres",
    "database.port": "5432",
    "database.user": "debezium",
    "database.password": "secret",
    "database.dbname": "app",
    "database.server.name": "appdb",
    "plugin.name": "pgoutput",
    "slot.name": "debezium_order_outbox",
    "publication.autocreate.mode": "filtered",
    "table.include.list": "public.outbox_event",
    "tombstones.on.delete": "false",
    "transforms": "outbox",
    "transforms.outbox.type": "io.debezium.transforms.outbox.EventRouter",
    "transforms.outbox.table.fields.additional.placement": "schema_version:header,schema_version",
    "transforms.outbox.route.by.field": "aggregate_type",
    "transforms.outbox.route.topic.replacement": "outbox.event.${routedByValue}",
    "transforms.outbox.table.field.event.id": "event_id",
    "transforms.outbox.table.field.event.key": "aggregate_id",
    "transforms.outbox.table.field.event.type": "event_type",
    "transforms.outbox.table.field.event.payload": "payload"
  }
}
```

여기서 중요한 건 단순 접속 정보보다 **EventRouter 같은 SMT(single message transform)를 어떻게 쓰느냐**다.

이 설정은 다음 효과를 만든다.

- Outbox 레코드를 일반 row change 이벤트가 아니라 **도메인 이벤트 형태**로 변환
- `aggregate_id`를 메시지 key로 사용 가능
- `aggregate_type` 기준으로 토픽 라우팅 가능
- `schema_version` 같은 메타데이터를 헤더로 전달 가능

즉, Debezium은 단순 복제기를 넘어 **이벤트 전달 파이프라인의 어댑터** 역할을 하게 된다.

### 4) 소비자 설계 포인트

예를 들어 정산 서비스 소비자는 이렇게 본다.

```python
from dataclasses import dataclass
import json


@dataclass(slots=True)
class ProcessedEvent:
    event_id: str
    event_type: str
    aggregate_id: str
    payload: dict


def handle_message(msg, processed_event_repo, settlement_service):
    event_id = msg.headers["id"]
    event_type = msg.headers["type"]
    aggregate_id = msg.key.decode()
    payload = json.loads(msg.value)

    if processed_event_repo.exists(event_id):
        return

    if event_type == "OrderCreated":
        settlement_service.reserve_order(
            order_id=payload["orderId"],
            amount=payload["totalAmount"],
        )

    processed_event_repo.save(event_id)
```

실무에서 더 중요한 건 문법보다 처리 규칙이다.

- `event_id` 기준 중복 방지 저장소가 있는가
- 처리 성공 이후에만 offset commit 또는 상태 기록을 하는가
- 스키마 버전이 달라졌을 때 하위 호환 규칙이 있는가
- 실패 이벤트를 어디까지 재시도하고 언제 격리하는가

### 5) 운영 관점에서 반드시 붙여야 할 지표

CDC 파이프라인은 애플리케이션 API처럼 500 에러가 직접 눈에 띄지 않는다. 그래서 지표를 안 붙이면 "조용히 망가지는" 시간이 길어진다.

최소한 아래는 봐야 한다.

- Debezium connector 상태(`RUNNING`, `FAILED`)
- source DB log lag / replication slot lag
- Kafka topic produce lag
- consumer lag
- DLQ 건수 또는 재처리 실패 건수
- Outbox 테이블 보관량/증가 속도
- 스냅샷 진행률 및 소요 시간

실제 운영에서는 "이벤트가 안 간다"는 신고가 들어오면 보통 아래 순서로 본다.

1. DB에는 Outbox row가 들어왔는가
2. Debezium connector가 그 시점 이후 오프셋을 읽고 있는가
3. Kafka topic에는 메시지가 실제 적재됐는가
4. 소비자 lag가 쌓였는가
5. 소비자에서 중복/스키마 오류로 버려지고 있지 않은가

이 추적 경로가 문서화되어 있지 않으면, 장애 때 팀 전체가 Kafka UI와 로그를 번갈아 보며 시간을 날리게 된다.

---

## 트레이드오프: Debezium CDC가 만능은 아니다

좋은 도구지만 비용도 분명하다.

### 장점

#### 1) 애플리케이션 코드 침투도 감소

모든 다운스트림 동기화를 서비스 코드에 넣지 않아도 된다. 특히 여러 소비자가 붙는 구조에서 강하다.

#### 2) DB 변경의 안정적 추출

polling보다 누락 가능성이 낮고, 운영 DB를 기준으로 사실을 흘려보내기 좋다.

#### 3) Outbox와 결합 시 높은 정합성

DB commit과 이벤트 기록을 같은 경계에 두고, 브로커 전송은 비동기로 넘길 수 있다.

#### 4) 검색/분석/서빙 계층 분리 용이

원본 서비스를 과도하게 수정하지 않고도 여러 파생 시스템을 붙이기 쉽다.

### 단점

#### 1) 운영 복잡도 증가

Kafka Connect, Debezium, replication slot/binlog 보관, connector 배포, 모니터링까지 함께 관리해야 한다. 단일 애플리케이션 안에서 끝나는 문제가 아니다.

#### 2) DB 스키마 변화의 파급력

원본 테이블 CDC는 특히 더 위험하다. 컬럼 rename/drop 하나가 다운스트림 파이프라인을 깨뜨릴 수 있다.

#### 3) delete 처리와 tombstone 이해 필요

삭제 이벤트를 소프트 삭제로 볼지, 실제 tombstone으로 볼지, 압축(compaction) 토픽에서 어떻게 다룰지 팀 합의가 필요하다.

#### 4) exactly-once 환상

Debezium + Kafka를 넣었다고 전체 체인이 정확히 한 번 처리되는 건 아니다. 소비자 idempotency와 재처리 정책이 빠지면 결국 중복/유실처럼 보이는 현상은 다시 나온다.

#### 5) 작은 시스템에는 과할 수 있음

단일 서비스, 낮은 트래픽, 단순한 동기화 요구라면 배치나 가벼운 publisher가 더 경제적일 수 있다. CDC는 분명 강력하지만, 그만큼 운영 팀의 성숙도도 요구한다.

핵심은 기술 선호가 아니라 **문제 크기에 맞는 도구 선택**이다.

---

## 흔한 실수

### 1) 원본 테이블 CDC를 곧바로 외부 이벤트 계약으로 노출하기

초기에는 빠르다. 하지만 운영 DB 컬럼이 바뀔 때마다 소비자 전체가 흔들린다. 외부 계약이 필요한 이벤트는 Outbox로 분리하는 편이 안전하다.

### 2) snapshot 부하를 과소평가하기

처음 붙일 때 한 번만 하면 된다고 생각하고 낮 시간대 전체 백필을 걸었다가 DB와 Kafka를 동시에 압박하는 경우가 많다. snapshot 전략은 배포 계획의 일부여야 한다.

### 3) `updated_at` polling과 CDC를 같은 수준으로 보기

둘은 장애 특성이 다르다. CDC는 복제 로그를 읽는 구조라 안정성이 높지만, 대신 replication 운영을 이해해야 한다. 단순 치환이 아니라 운영 모델 전환이다.

### 4) 소비자 idempotency를 뒤로 미루기

이벤트가 두 번 오면 큰일 나는 구조라면, 사실 그 시스템은 아직 스트리밍 준비가 덜 된 상태다. `event_id`와 처리 기록 전략은 처음부터 넣어야 한다.

### 5) 커넥터 상태만 보고 끝내기

connector가 `RUNNING`이어도 consumer lag가 쌓이거나, 특정 스키마 오류 때문에 다운스트림이 조용히 실패할 수 있다. 파이프라인 전체 관측이 필요하다.

### 6) delete 정책을 명확히 정하지 않기

실제 삭제인지, 소프트 삭제인지, 검색 인덱스에서는 문서를 제거할지 비활성화할지, 분석계에서는 이력을 남길지 초기에 정해야 한다. delete 처리 기준이 없으면 데이터 불일치가 오래간다.

### 7) Outbox 보관 전략 없이 무한 적재하기

Debezium이 읽어간 후에도 Outbox 레코드는 남는다. 파티셔닝, TTL, 아카이브 정책 없이 쌓아두면 결국 운영 부담으로 돌아온다.

---

## 체크리스트

### 아키텍처 선택 전

- [ ] 목적이 데이터 복제인지, 도메인 이벤트 전달인지 구분했다
- [ ] 원본 테이블 CDC와 Outbox CDC 중 무엇이 더 맞는지 문서화했다
- [ ] 어떤 엔티티 기준 순서가 중요한지 파티션 키 전략을 정했다
- [ ] 소비자별로 upsert 가능한지, idempotency가 필요한지 확인했다

### Debezium 도입 전

- [ ] source DB의 binlog/WAL/replication slot 운영 제약을 확인했다
- [ ] snapshot 수행 시간대와 대상 범위를 정했다
- [ ] 커넥터 재시작/재배포/재스냅샷 절차를 문서화했다
- [ ] delete/tombstone 처리 정책을 합의했다

### Outbox 설계 시

- [ ] `event_id`, `event_type`, `aggregate_id`, `schema_version` 컬럼을 포함했다
- [ ] 이벤트 payload를 외부 계약 관점으로 설계했다
- [ ] Outbox 정리(archive/TTL/partition) 정책을 정했다
- [ ] 스키마 버전 업 전략과 하위 호환 원칙을 정했다

### 운영 준비

- [ ] connector state, source lag, consumer lag 모니터링을 붙였다
- [ ] DLQ 또는 실패 격리 절차를 만들었다
- [ ] 특정 시간대 이벤트 재처리(runbook)를 준비했다
- [ ] 장애 시 DB → connector → Kafka → consumer 순서로 추적하는 진단 절차를 공유했다

---

## 한 줄 정리

Debezium CDC의 핵심은 "DB 변경을 Kafka로 보내는 것"이 아니라, **원본 테이블 복제와 의미 있는 이벤트 계약을 구분하고, 중복 무해화·재처리·운영 관측까지 포함한 파이프라인으로 설계하는 것**이다.
