---
layout: post
title: "Kafka 파티션 키 설계와 순서 보장: 같은 이벤트를 같은 흐름으로 보내는 법"
date: 2026-03-02 10:05:59 +0900
categories: [data-infra]
tags: [study, kafka, partition, key, ordering, streaming, infra]
---

## 왜 파티션 키가 중요한가?

Kafka를 처음 배울 때는 Topic과 Producer/Consumer 개념만 보고 넘어가기 쉽지만, 실무에서 가장 많은 설계 실수는 **파티션 키를 대충 정하는 것**에서 발생합니다.

같은 사용자의 주문 이벤트가 서로 다른 파티션으로 흩어지면, 순서가 중요한 비즈니스 로직이 쉽게 깨집니다.

## 핵심 개념

- **같은 key → 같은 partition**
- **같은 partition 안에서는 순서 보장**
- **다른 partition 간에는 전체 순서 보장 안 됨**

## Python Producer 예시

```python
from kafka import KafkaProducer
import json

producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
    key_serializer=lambda k: k.encode('utf-8')
)

producer.send(
    'orders',
    key='user-123',
    value={'event': 'ORDER_CREATED', 'user_id': 'user-123', 'order_id': 1001}
)

producer.send(
    'orders',
    key='user-123',
    value={'event': 'ORDER_PAID', 'user_id': 'user-123', 'order_id': 1001}
)

producer.flush()
```

## 설계 원칙

### 어떤 값을 key로 써야 하나?
- 같은 흐름으로 묶여야 하는 엔티티 ID
- 예: `user_id`, `order_id`, `account_id`

### key를 잘못 잡으면?
- 동일 비즈니스 흐름이 분산되어 순서가 깨짐
- 특정 파티션에만 트래픽이 몰리는 hot partition 발생

## 흔한 실수

- key 없이 무작위 전송
- 너무 세밀한 key 사용으로 hot partition 유발
- 순서가 중요한 도메인인데 partition 전략을 뒤늦게 고민

## 한 줄 정리

Kafka의 순서 보장은 "서비스 전체"가 아니라 **같은 key가 같은 partition에 들어갈 때만 성립**합니다.
