---
layout: post
title: "Apache Kafka 기초: 실시간 데이터 스트리밍의 핵심 이해하기"
date: 2026-02-17 11:00:00 +0900
categories: [data-infra]
tags: [study, kafka, streaming, infra, automation]
---

## 왜 Kafka를 알아야 할까?

현대 서비스는 실시간 데이터 처리가 필수입니다.
주문 이벤트, 로그 수집, 알림 발송, 서비스 간 비동기 통신 등 다양한 곳에서 메시지 브로커가 필요합니다.

Kafka는 높은 처리량과 내구성을 동시에 제공하며, LinkedIn, Netflix, Uber 등 대규모 트래픽을 처리하는 기업에서 핵심 인프라로 사용됩니다.

## 핵심 개념

- **Topic & Partition**
  Topic은 메시지의 논리적 채널, Partition은 Topic을 물리적으로 분할한 단위입니다.
  Partition 수가 많을수록 병렬 처리 능력이 올라가며, 같은 키의 메시지는 항상 같은 파티션에 들어가 순서가 보장됩니다.
- **Producer & Consumer**
  Producer는 메시지를 Topic에 발행하고, Consumer는 Topic에서 메시지를 읽습니다.
  Consumer는 읽은 위치(offset)를 관리하며, 장애 시 해당 지점부터 재처리가 가능합니다.
- **Consumer Group**
  같은 그룹의 Consumer들은 파티션을 나눠 읽습니다.
  그룹 내 Consumer 수 > 파티션 수이면 남는 Consumer는 유휴 상태가 됩니다.
  서로 다른 그룹은 동일한 메시지를 독립적으로 소비합니다.
- **Broker & Cluster**
  Broker는 Kafka 서버 인스턴스이고, 여러 Broker가 모여 Cluster를 구성합니다.
  파티션은 Broker들에 분산 저장되어 확장성과 가용성을 확보합니다.
- **Offset & Commit**
  Consumer가 읽은 위치를 offset이라 하며, 이를 커밋해야 재시작 시 중복 없이 이어서 읽을 수 있습니다.
  자동 커밋과 수동 커밋 방식이 있으며, 데이터 정합성이 중요하면 수동 커밋을 사용합니다.

## 실습 예제

### Docker Compose로 Kafka 실행

```yaml
# docker-compose.yml
version: '3.8'
services:
  zookeeper:
    image: confluentinc/cp-zookeeper:7.5.0
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181

  kafka:
    image: confluentinc/cp-kafka:7.5.0
    depends_on:
      - zookeeper
    ports:
      - "9092:9092"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
```

### CLI로 토픽 생성 및 메시지 송수신

```bash
# 토픽 생성 (파티션 3개)
kafka-topics --create \
  --bootstrap-server localhost:9092 \
  --topic order-events \
  --partitions 3 \
  --replication-factor 1

# Producer: 메시지 전송
kafka-console-producer \
  --bootstrap-server localhost:9092 \
  --topic order-events

# Consumer: 메시지 수신
kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic order-events \
  --from-beginning \
  --group order-processor
```

### Python Producer & Consumer

```python
from kafka import KafkaProducer, KafkaConsumer
import json

# Producer
producer = KafkaProducer(
    bootstrap_servers=["localhost:9092"],
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    key_serializer=lambda k: k.encode("utf-8") if k else None,
)

order = {"order_id": "ORD-001", "item": "노트북", "amount": 1250000}
producer.send("order-events", key="ORD-001", value=order)
producer.flush()
print("메시지 전송 완료")

# Consumer
consumer = KafkaConsumer(
    "order-events",
    bootstrap_servers=["localhost:9092"],
    group_id="order-processor",
    value_deserializer=lambda m: json.loads(m.decode("utf-8")),
    auto_offset_reset="earliest",
    enable_auto_commit=False,
)

for message in consumer:
    print(f"파티션: {message.partition}, 오프셋: {message.offset}")
    print(f"주문 데이터: {message.value}")
    consumer.commit()  # 수동 커밋
```

## 흔한 실수

- **파티션 수 변경의 함정**
  파티션 수는 늘릴 수 있지만 줄일 수 없습니다.
  키 기반 파티셔닝 사용 시 파티션 수를 변경하면 같은 키가 다른 파티션으로 갈 수 있어 순서 보장이 깨집니다.
- **auto.offset.reset 미설정**
  Consumer Group 시작 시 `earliest`와 `latest` 중 선택해야 합니다.
  미설정 시 기본값 `latest`로 기존 메시지를 놓칠 수 있습니다.
- **Consumer 수 > Partition 수**
  Consumer가 파티션 수보다 많으면 남는 Consumer는 메시지를 받지 못합니다.
  병렬 처리를 늘리려면 파티션 수를 먼저 늘려야 합니다.
- **메시지 크기 제한 무시**
  기본 메시지 최대 크기는 1MB입니다.
  큰 파일은 스토리지에 저장한 뒤 경로만 메시지로 전달하세요.

## 하루 실습 체크리스트

- [ ] Docker Compose로 Kafka + Zookeeper 클러스터 실행하기
- [ ] CLI로 토픽 생성 후 Producer/Consumer 테스트하기
- [ ] Python `kafka-python`으로 JSON 메시지 전송 및 수신 코드 작성하기
- [ ] 같은 Consumer Group의 Consumer 2개를 띄우고 파티션 분배 확인하기
- [ ] 수동 커밋과 자동 커밋의 차이를 실험해보기
