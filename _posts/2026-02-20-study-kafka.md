---
layout: post
title: "Kafka Consumer Group과 Offset 관리: 중복 처리와 유실을 막는 핵심"
date: 2026-02-20 10:04:44 +0900
categories: [data-infra]
tags: [study, kafka, consumer-group, offset, streaming, infra]
---

## 왜 이 주제가 중요한가?

Kafka를 실제로 운영하면 성능보다 먼저 부딪히는 문제가 **중복 처리, 메시지 유실처럼 보이는 현상, 컨슈머 재시작 이후 위치 꼬임**입니다. 이 문제의 핵심은 대부분 Consumer Group과 Offset을 어떻게 이해하고 커밋하느냐에 달려 있습니다.

## 핵심 개념

- **Consumer Group**
  같은 그룹의 컨슈머들은 파티션을 나눠 읽습니다.
- **Offset**
  컨슈머가 어디까지 읽었는지를 나타내는 위치 정보입니다.
- **Auto Commit**
  편하지만 처리 완료 전에 커밋되면 유실처럼 보일 수 있습니다.
- **Manual Commit**
  더 안전하지만 애플리케이션 책임이 늘어납니다.

## Python 예시

```python
from kafka import KafkaConsumer
import json

consumer = KafkaConsumer(
    'orders',
    bootstrap_servers='localhost:9092',
    group_id='order-service',
    enable_auto_commit=False,
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)

for message in consumer:
    data = message.value
    print('processing', data)

    # 실제 비즈니스 처리 성공 이후에만 커밋
    consumer.commit()
```

## 왜 수동 커밋을 고려해야 하나?

주문 생성, 결제, 포인트 적립처럼 재처리와 유실에 민감한 업무에서는 "읽었다"와 "처리 완료했다"를 같은 것으로 보면 안 됩니다. 처리 성공 이후에만 커밋해야 장애 시 재처리 전략을 세울 수 있습니다.

## 흔한 실수

- auto commit 기본값을 그대로 쓰고 정합성 문제를 나중에 발견함
- 동일 그룹과 다른 그룹의 차이를 이해하지 못함
- offset은 Kafka가 알아서 해결해준다고 오해함

## 한 줄 정리

Kafka 운영 안정성의 핵심은 브로커보다도 **컨슈머가 offset을 언제 커밋하느냐**에 있습니다.
