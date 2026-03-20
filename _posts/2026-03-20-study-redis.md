---
layout: post
title: "Redis와 SQL: 캐싱 전략으로 데이터베이스 성능 극대화하기"
date: 2026-03-20 10:06:37 +0900
categories: [sql]
tags: [study, redis, caching, database, automation]
---

## 왜 이 주제가 중요한가?

SQL 데이터베이스만으로는 고트래픽 서비스를 감당하기 어렵습니다. Redis를 캐시 레이어로 추가하면 데이터베이스 부하를 크게 줄이고 응답 속도를 10배 이상 개선할 수 있습니다.

실제 프로젝트에서 Redis 없이는 초당 수천 건의 요청을 처리하기 거의 불가능합니다. 특히 사용자 세션, 상품 정보, 순위 데이터 같은 자주 조회되는 데이터에 효과적입니다.

## 핵심 개념

- **캐시 워밍 (Cache Warming)**
  애플리케이션 시작 시 자주 사용되는 데이터를 미리 Redis에 로드하는 전략입니다.

- **TTL (Time To Live) 설정**
  캐시된 데이터의 유효 기간을 정해서 자동으로 만료되도록 합니다. 데이터 신선도와 메모리 효율의 균형을 맞춥니다.

- **캐시 무효화 (Cache Invalidation)**
  데이터베이스 업데이트 시 해당 캐시를 삭제하거나 갱신하는 과정입니다. 가장 어려운 부분이기도 합니다.

- **Look-Aside 패턴**
  애플리케이션이 먼저 Redis에서 데이터를 찾고, 없으면 SQL에서 조회한 후 Redis에 저장하는 방식입니다.

- **Write-Through 패턴**
  데이터 쓰기 시 Redis와 SQL 데이터베이스에 동시에 저장하는 방식입니다. 데이터 일관성이 높지만 속도가 느립니다.

## 실전 예제

### 기본 캐싱 구조

```python
import redis
import json
from datetime import timedelta

redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

def get_user_by_id(user_id):
    # 1단계: Redis에서 확인
    cache_key = f"user:{user_id}"
    cached_user = redis_client.get(cache_key)
    
    if cached_user:
        return json.loads(cached_user)
    
    # 2단계: 캐시 미스 시 SQL에서 조회
    user = fetch_from_database(user_id)
    
    # 3단계: Redis에 저장 (TTL: 1시간)
    redis_client.setex(
        cache_key,
        timedelta(hours=1),
        json.dumps(user)
    )
    
    return user
```

### 캐시 무효화 처리

```python
def update_user(user_id, new_data):
    # 1단계: 데이터베이스 업데이트
    update_database(user_id, new_data)
    
    # 2단계: 캐시 삭제
    cache_key = f"user:{user_id}"
    redis_client.delete(cache_key)
    
    return new_data
```

### 배치 캐싱 (자주 사용되는 데이터)

```python
def warm_up_cache():
    # 상위 100개 상품을 캐시에 미리 로드
    top_products = fetch_top_products_from_db(limit=100)
    
    for product in top_products:
        cache_key = f"product:{product['id']}"
        redis_client.setex(
            cache_key,
            timedelta(hours=6),
            json.dumps(product)
        )
    
    print(f"캐시 워밍 완료: {len(top_products)}개 상품")
```

## 자주 하는 실수

- **TTL을 너무 길게 설정**
  데이터가 오래되어 사용자에게 잘못된 정보를 제공할 수 있습니다. 데이터 특성에 맞춰 적절한 TTL을 설정하세요.

- **캐시 무효화 로직 누락**
  데이터 업데이트 후 캐시를 삭제하지 않으면 계속 구 데이터를 제공합니다. 모든 쓰기 작업에서 캐시 삭제를 필수로 포함하세요.

- **메모리 모니터링 부재**
  Redis 메모리가 가득 차면 성능이 급격히 떨어집니다. 정기적으로 메모리 사용량을 확인하고 정책을 조정하세요.

- **직렬화 형식 불일치**
  JSON으로 저장했는데 pickle로 읽으려고 하면 에러가 발생합니다. 팀 전체가 동일한 직렬화 방식을 사용하도록 통일하세요.

- **캐시 스탬피드 (Cache Stampede) 미처리**
  인기 있는 데이터의 캐시가 동시에 만료되면 모든 요청이 데이터베이스로 몰립니다. 캐시 갱신 시간을 분산시키거나 Lock을 사용하세요.

## 오늘의 실습 체크리스트

- [ ] 로컬 환경에 Redis 설치 및 실행 확인
- [ ] redis-py 라이브러리 설치
- [ ] Look-Aside 패턴으로 간단한 캐싱 함수 작성
- [ ] TTL을 다양하게 설정해서 동작 확인
- [ ] 데이터 업데이트 시 캐시 무효화 로직 추가
- [ ] redis-cli를 사용해 실제 캐시 데이터 확인
- [ ] 캐시 히트율을 계산하는 간단한 모니터링 코드 작성
