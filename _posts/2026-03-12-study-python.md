---
layout: post
title: "Python 제너레이터와 이터레이터 실전: 메모리 효율적인 데이터 처리"
date: 2026-03-12 09:59:31 +0900
categories: [python]
tags: [study, python, generator, iterator, performance, backend]
---

## 왜 제너레이터가 중요한가?

실무에서 로그 파일, 대용량 CSV, 배치 데이터처럼 한 번에 메모리에 올리기 부담스러운 데이터를 다룰 일이 많습니다. 이때 리스트로 전부 읽어오면 메모리 사용량이 급격히 증가합니다.

제너레이터는 **필요한 시점에 한 건씩 값을 생성**하기 때문에, 메모리 효율이 중요한 백엔드 작업에서 매우 유리합니다.

## 핵심 개념

- **Iterator**: `__next__()`로 다음 값을 하나씩 꺼낼 수 있는 객체
- **Generator**: `yield`를 사용해 간단하게 iterator를 만드는 문법
- **Lazy Evaluation**: 미리 전부 계산하지 않고 필요할 때 계산

## 리스트 vs 제너레이터

```python
numbers = [i * 2 for i in range(1_000_000)]  # 메모리 사용량 큼
numbers_gen = (i * 2 for i in range(1_000_000))  # lazy evaluation
```

## yield 예제

```python
def read_lines(path):
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            yield line.strip()


for line in read_lines('app.log'):
    if 'ERROR' in line:
        print(line)
```

## 배치 처리 예제

```python
def chunked(iterable, size):
    batch = []
    for item in iterable:
        batch.append(item)
        if len(batch) == size:
            yield batch
            batch = []
    if batch:
        yield batch


for batch in chunked(range(1, 21), 5):
    print(batch)
```

## 언제 쓰면 좋은가?

- 대용량 파일 처리
- DB 조회 결과 스트리밍
- API 페이지네이션 처리
- 배치 파이프라인 구성

## 흔한 실수

- 제너레이터는 한 번 소비하면 끝난다는 점을 놓침
- 디버깅 편하다고 중간에 `list()`로 바꿔 메모리 이점 상실
- 제너레이터와 비동기 스트림을 혼동

## 한 줄 정리

제너레이터는 Python에서 대용량 데이터를 다룰 때 가장 먼저 떠올려야 하는 **메모리 절약 패턴**입니다.
