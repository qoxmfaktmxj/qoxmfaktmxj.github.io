---
layout: post
title: "Apache Kafka 기초: 실무에서 필요한 메시지 큐 이해하기"
date: 2026-02-20 10:04:44 +0900
categories: [data-infra]
tags: [study, kafka, streaming, infra, automation]
---

## 왜 Kafka를 배워야 할까?

Kafka는 대규모 데이터 처리 시스템에서 필수적인 메시지 브로커입니다. 실무에서는 실시간 로그 수집, 이벤트 스트리밍, 마이크로서비스 간 통신 등에 광범위하게 사용됩니다.

초당 수백만 건의 메시지를 안정적으로 처리해야 하는 프로젝트에서 Kafka 없이는 시스템 구축이 거의 불가능합니다. 데이터 인프라 엔지니어라면 반드시 이해해야 할 핵심 기술입니다.

## 핵심 개념

- **Topic (토픽)**
  메시지를 분류하는 논리적 단위입니다. 데이터베이스의 테이블처럼 생각하면 됩니다.

- **Partition (파티션)**
  Topic을 물리적으로 분산하는 단위로, 병렬 처리를 가능하게 합니다. 각 파티션은 순서가 보장됩니다.

- **Producer (프로듀서)**
  Topic에 메시지를 보내는 클라이언트입니다. 어느 파티션으로 보낼지 결정할 수 있습니다.

- **Consumer (컨슈머)**
  Topic에서 메시지를 읽는 클라이언트입니다. Consumer Group으로 묶여 파티션을 분담합니다.

- **Broker (브로커)**
  Kafka 서버 인스턴스입니다. 여러 브로커가 클러스터를 이루어 고가용성을 제공합니다.

## 실습: 간단한 Producer-Consumer 구성

먼저 Docker Compose로 Kafka 환경을 구성합니다.

```yaml
version: '3'
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
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:29092,PLAINTEXT_HOST://localhost:9092
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT
      KAFKA_INTER_BROKER_LISTENER_NAME: PLAINTEXT
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
```

`docker-compose up -d`로 실행한 후, Topic을 생성합니다.

```bash
docker exec kafka kafka-topics --create --topic user-events --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1
```

Python으로 간단한 Producer를 작성합니다.

```python
from kafka import KafkaProducer
import json
import time

producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

for i in range(10):
    event = {'user_id': i, 'action': 'login', 'timestamp': time.time()}
    producer.send('user-events', value=event)
    print(f"Sent: {event}")
    time.sleep(1)

producer.flush()
producer.close()
```

Consumer를 작성하여 메시지를 읽습니다.

```python
from kafka import KafkaConsumer
import json

consumer = KafkaConsumer(
    'user-events',
    bootstrap_servers=['localhost:9092'],
    group_id='user-event-group',
    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
    auto_offset_reset='earliest'
)

for message in consumer:
    print(f"Received: {message.value}")
```

두 스크립트를 각각 실행하면 Producer가 보낸 메시지를 Consumer가 받게 됩니다.

## 자주 하는 실수

- **Partition 개수를 무분별하게 늘리기**
  Partition이 많을수록 병렬성은 높아지지만, 관리 복잡도와 메모리 사용량도 증가합니다. 초기에는 적절한 수준(3~5개)에서 시작하세요.

- **Consumer Group 설정 없이 Consumer 실행하기**
  Consumer Group이 없으면 offset 관리가 제대로 되지 않아 메시지 손실이나 중복이 발생할 수 있습니다.

- **Replication Factor를 1로 설정하기**
  프로덕션 환경에서는 최소 2 이상으로 설정하여 브로커 장애 시에도 데이터를 보호해야 합니다.

- **Producer의 acks 설정을 무시하기**
  `acks=all`로 설정하면 안정성이 높아지지만 성능이 저하됩니다. 요구사항에 맞게 조정하세요.

- **Consumer lag을 모니터링하지 않기**
  Consumer가 처리 속도를 따라가지 못하면 lag이 증가합니다. 정기적으로 모니터링해야 합니다.

## 오늘의 실습 체크리스트

- [ ] Docker Compose로 Kafka 클러스터 구성하기
- [ ] `kafka-topics` 명령어로 Topic 생성 및 조회하기
- [ ] Python KafkaProducer로 메시지 5개 이상 전송하기
- [ ] Python KafkaConsumer로 메시지 수신 확인하기
- [ ] Consumer Group을 변경하여 offset 재설정 테스트하기
- [ ] `kafka-consumer-groups` 명령어로 Consumer lag 확인하기
- [ ] 여러 Consumer를 같은 Group으로 실행하여 파티션 분담 확인하기
