---
layout: post
title: "Kafka 리밸런싱과 운영 장애 대응: 컨슈머가 흔들릴 때 보는 체크포인트"
date: 2026-03-11 10:03:03 +0900
categories: [data-infra]
tags: [study, kafka, rebalancing, operations, troubleshooting, infra]
---

## 왜 리밸런싱을 이해해야 하나?

Kafka는 컨슈머 수가 바뀌거나 장애가 발생하면 Consumer Group 내부에서 파티션 재할당을 수행합니다. 이 리밸런싱 과정이 길어지면 처리 지연, 중복 소비, lag 급증 문제가 동시에 발생할 수 있습니다.

## 리밸런싱이 일어나는 대표 상황

- 컨슈머 인스턴스가 추가/삭제될 때
- 컨슈머가 세션 타임아웃으로 죽었다고 판단될 때
- 토픽 파티션 구성이 바뀔 때

## 체크해야 할 주요 지표

- **consumer lag**
- **rebalance 횟수**
- **poll interval 초과 여부**
- **session timeout / heartbeat 설정**

## 운영 팁

### 1) 처리 시간이 긴 작업은 poll loop와 분리
컨슈머가 한 번에 너무 오래 처리하면 heartbeat가 끊겨 죽은 것으로 오해받을 수 있습니다.

### 2) timeout 값을 실제 처리 시간에 맞춰 조정
짧게 잡으면 불필요한 리밸런싱이 늘고, 너무 길면 장애 감지가 늦어집니다.

### 3) lag만 보지 말고 원인을 분리
lag 증가는 단순히 처리량 부족 때문일 수도 있고, 리밸런싱 폭주 때문일 수도 있습니다.

## 예시 설정

```python
from kafka import KafkaConsumer

consumer = KafkaConsumer(
    'orders',
    bootstrap_servers='localhost:9092',
    group_id='order-service',
    session_timeout_ms=15000,
    heartbeat_interval_ms=5000,
    max_poll_interval_ms=300000
)
```

## 흔한 실수

- lag만 보고 파티션을 무조건 늘림
- heartbeat/session timeout 의미를 분리해서 이해하지 못함
- 비즈니스 처리 시간이 긴데 max_poll_interval을 기본값으로 둠

## 한 줄 정리

Kafka 장애 대응의 핵심은 "브로커가 죽었나?"보다 먼저, **컨슈머 그룹이 안정적으로 파티션을 유지하고 있는가**를 보는 것입니다.
