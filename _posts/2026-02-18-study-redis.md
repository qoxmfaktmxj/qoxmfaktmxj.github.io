---
layout: post
title: "Redis와 SQL 데이터베이스의 연동 전략"
date: 2026-02-18 01:54:14 +0900
categories: [sql]
tags: [study, redis, caching, database, automation]
---

# Redis와 SQL 데이터베이스의 연동 전략

## 왜 이 주제가 중요한가?

실제 프로젝트에서 Redis는 단순한 캐시가 아닙니다.
SQL 데이터베이스와 함께 사용할 때 진정한 가치를 발휘합니다.

데이터 조회 성능을 **10배 이상** 향상시키고, 데이터베이스 부하를 크게 줄일 수 있습니다.
특히 사용자 세션, 상품 정보, 랭킹 데이터 같은 자주 조회되는 데이터를 다룰 때 필수적입니다.

## 핵심 개념

- **캐시 패턴**
  Look-aside(Lazy Loading), Write-through, Write-behind 패턴의 차이점과 사용 시기
- **데이터 일관성**
  Redis와 SQL 간 데이터 동기화 전략 및 TTL 관리
- **캐시 무효화**
  데이터 변경 시 Redis 캐시를 효과적으로 갱신하는 방법
- **성능 최적화**
  쿼리 결과를 JSON 형태로 Redis에 저장하여 직렬화 오버헤드 감소
- **모니터링**
  캐시 히트율, 미스율 추적 및 메모리 사용량 관리

## 실전 예제

### 상황: 사용자 프로필 조회 최적화

```python
import redis
import json
import mysql.connector
from datetime import timedelta

# Redis 연결
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# MySQL 연결
db_connection = mysql.connector.connect(
    host='localhost',
    user='root',
    password='password',
    database='myapp'
)

def get_user_profile(user_id):
    """Look-aside 패턴: 캐시 먼저 확인"""
    cache_key = f"user:{user_id}:profile"
    
    # 1단계: Redis에서 조회
    cached_data = redis_client.get(cache_key)
    if cached_data:
        print(f"캐시 히트: user_id={user_id}")
        return json.loads(cached_data)
    
    # 2단계: 캐시 미스 시 SQL에서 조회
    print(f"캐시 미스: user_id={user_id}")
    cursor = db_connection.cursor(dictionary=True)
    cursor.execute("SELECT id, name, email, created_at FROM users WHERE id = %s", (user_id,))
    user_data = cursor.fetchone()
    cursor.close()
    
    if user_data:
        # 3단계: Redis에 저장 (TTL: 1시간)
        redis_client.setex(
            cache_key,
            timedelta(hours=1),
            json.dumps(user_data, default=str)
        )
    
    return user_data

def update_user_profile(user_id, name, email):
    """데이터 변경 시 캐시 무효화"""
    # 1단계: SQL 업데이트
    cursor = db_connection.cursor()
    cursor.execute(
        "UPDATE users SET name = %s, email = %s WHERE id = %s",
        (name, email, user_id)
    )
    db_connection.commit()
    cursor.close()
    
    # 2단계: 캐시 삭제 (다음 조회 시 새로운 데이터 로드)
    cache_key = f"user:{user_id}:profile"
    redis_client.delete(cache_key)
    print(f"캐시 무효화: {cache_key}")

# 사용 예
profile = get_user_profile(123)
print(profile)

update_user_profile(123, "New Name", "new@email.com")
profile = get_user_profile(123)  # 새로운 데이터 로드
```

## 자주 하는 실수

1. **캐시 만료 시간 설정 오류**
   TTL을 너무 길게 → 오래된 데이터 제공, 너무 짧게 → 캐시 효과 없음.
   데이터 특성에 맞게 설정하세요.

2. **캐시 무효화 누락**
   데이터 업데이트 후 Redis 캐시를 삭제하지 않으면 일관성 문제가 발생합니다.
   항상 쌍으로 처리하세요.

3. **메모리 관리 무시**
   Redis 메모리가 가득 차면 성능이 급격히 저하됩니다.
   `maxmemory` 정책을 설정하고 모니터링하세요.

4. **직렬화 형식 선택 실수**
   JSON은 가독성이 좋지만 크기가 크고, 바이너리는 빠르지만 디버깅이 어렵습니다.
   프로젝트 특성에 맞게 선택하세요.

5. **동시성 문제**
   여러 프로세스가 동시에 캐시를 갱신할 때 race condition이 발생할 수 있습니다.
   필요시 Redis 트랜잭션이나 락을 사용하세요.

## 오늘의 실습 체크리스트

- [ ] Redis 서버 로컬 환경에서 실행 확인 (redis-cli로 연결)
- [ ] Python redis 라이브러리 설치 및 기본 연결 테스트
- [ ] Look-aside 패턴으로 간단한 캐시 함수 작성
- [ ] SQL 쿼리 결과를 JSON으로 직렬화하여 Redis에 저장
- [ ] 데이터 업데이트 시 캐시 무효화 로직 구현
- [ ] redis-cli에서 KEYS, TTL, MEMORY USAGE 명령어로 캐시 상태 확인
- [ ] 같은 데이터를 여러 번 조회하여 캐시 히트/미스 로그 확인
