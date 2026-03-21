---
layout: post
title: "Redis 분산 락 실전: 중복 실행과 동시성 충돌을 막는 기본 패턴"
date: 2026-03-20 10:06:37 +0900
categories: [sql]
tags: [study, redis, distributed-lock, concurrency, caching, infra]
---

## 왜 Redis 분산 락이 필요한가?

멀티 인스턴스 환경에서는 같은 작업이 동시에 두 번 이상 실행되는 문제가 자주 발생합니다. 예를 들어 배치 작업, 결제 후처리, 재고 차감, 쿠폰 발급 같은 로직은 중복 실행되면 곧바로 장애로 이어질 수 있습니다.

이때 Redis는 빠른 락 저장소 역할을 할 수 있습니다.

## 가장 단순한 패턴: SET NX EX

```python
import redis
import uuid

r = redis.Redis(host='localhost', port=6379, decode_responses=True)
lock_key = 'lock:coupon:123'
lock_value = str(uuid.uuid4())

locked = r.set(lock_key, lock_value, nx=True, ex=10)

if locked:
    try:
        print('락 획득 성공, 작업 실행')
    finally:
        if r.get(lock_key) == lock_value:
            r.delete(lock_key)
else:
    print('이미 다른 작업자가 실행 중')
```

## 왜 value 비교 후 삭제해야 하나?

락 만료/재획득 상황에서 다른 작업자가 이미 같은 key를 잡았을 수 있기 때문입니다. 아무 생각 없이 `DEL lock_key`를 호출하면 남의 락을 풀어버릴 수 있습니다.

## 적용이 적합한 경우

- 중복 배치 실행 방지
- 동일 주문 후처리 중복 방지
- 짧은 임계영역 보호

## 주의할 점

- 장시간 작업에는 락 갱신 전략이 필요함
- 락만으로 모든 정합성을 해결할 수 없음
- DB 트랜잭션과 역할이 다름

## 흔한 실수

- 락 획득 실패 시 재시도/포기 전략 없음
- 만료 시간 없이 락을 걸어 영구 점유 발생
- 소유자 확인 없이 삭제

## 한 줄 정리

Redis 분산 락의 핵심은 락을 거는 것보다, **안전하게 해제하고 중복 실행을 제어하는 규칙**에 있습니다.
