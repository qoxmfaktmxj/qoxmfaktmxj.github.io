---
layout: post
title: "Python 데코레이터 실전: 로깅, 권한체크, 재시도 로직 공통화하기"
date: 2026-03-03 10:07:40 +0900
categories: [python]
tags: [study, python, decorator, retry, logging, automation]
---

## 왜 데코레이터를 따로 배워야 할까?

Python에서 데코레이터는 문법 트릭처럼 보이지만, 실무에서는 **반복되는 부가기능을 비즈니스 로직 밖으로 분리**하는 핵심 도구입니다. 로깅, 권한 검사, 실행 시간 측정, 재시도 정책을 함수마다 직접 넣기 시작하면 코드가 빠르게 지저분해집니다.

## 핵심 개념

- **함수는 객체다**
  Python에서는 함수를 변수처럼 전달할 수 있습니다.
- **데코레이터는 함수를 감싸는 함수**
  원래 함수를 수정하지 않고 앞뒤 동작을 끼워 넣습니다.
- **`functools.wraps`는 거의 필수**
  원본 함수 이름, docstring, metadata를 유지합니다.

## 실행 시간 측정 데코레이터

```python
import time
from functools import wraps


def log_execution_time(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start
        print(f"[TIME] {func.__name__}: {duration:.4f}s")
        return result
    return wrapper


@log_execution_time
def generate_report():
    time.sleep(1)
    return "done"


print(generate_report())
```

## 재시도 데코레이터

```python
import time
from functools import wraps


def retry(max_attempts=3, delay=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    print(f"attempt={attempt} failed: {e}")
                    if attempt < max_attempts:
                        time.sleep(delay)
            raise last_error
        return wrapper
    return decorator


@retry(max_attempts=3, delay=2)
def fetch_external_api():
    raise RuntimeError("temporary network error")
```

## 실무에서 유용한 패턴

- API 호출 재시도
- 관리자 권한 체크
- 함수 실행 로그 남기기
- 캐시 공통 처리
- 트랜잭션 시작/종료 래핑

## 흔한 실수

- 데코레이터 안에서 예외를 삼켜버림
- `wraps`를 쓰지 않아 디버깅이 어려워짐
- 부가기능이 너무 많아 데코레이터 중첩이 과해짐

## 한 줄 정리

데코레이터는 "멋있는 문법"이 아니라, **반복되는 운영 로직을 공통화하는 실무 도구**입니다.
