---
layout: post
title: "Python CPU 병렬 처리 실전: GIL, multiprocessing, spawn/fork, shared memory, pickle 비용까지 운영 기준으로 이해하기"
date: 2026-04-22 11:40:00 +0900
categories: [python]
tags: [study, python, gil, multiprocessing, processpool, shared-memory, pickle, performance, concurrency]
permalink: /python/2026/04/22/study-python-gil-multiprocessing-shared-memory-pickle.html
---

## 왜 이 주제가 실무에서 중요할까?

Python 서비스가 운영 단계로 들어가면, 어느 순간 팀은 비슷한 장면을 반복해서 본다.

- FastAPI API 자체는 가벼운데 특정 요청만 유독 느리다
- 배치 작업에 워커 수를 늘렸는데 오히려 전체 시간이 늘어난다
- ThreadPoolExecutor를 붙였는데 CPU 사용률은 높아져도 처리량은 거의 안 오른다
- pandas, 이미지 처리, 벡터 계산 작업을 프로세스로 나눴더니 pickle 비용 때문에 병렬화 이득이 사라진다
- Linux에서는 잘 돌던 코드가 macOS 개발 환경이나 Windows 배포 환경에서 `spawn` 이슈로 깨진다
- `fork`는 빠른데 라이브러리 상태를 복제해 이상한 deadlock, connection 문제, 메모리 급증을 만든다

많은 팀이 여기서 "Python은 느리다"라는 결론으로 성급하게 간다. 하지만 실무에서 문제의 핵심은 언어 그 자체보다, 아래 세 가지를 섞어 오해하는 데 있다.

1. **GIL 때문에 안 되는 것**
2. **프로세스를 늘리면 되지만 데이터 이동 비용이 더 큰 것**
3. **애초에 프로세스보다 벡터화, C extension, 쿼리 푸시다운이 먼저인 것**

즉 CPU 병렬 처리는 "프로세스를 여러 개 띄우면 끝"이 아니라, **작업 특성 분류, 프로세스 시작 방식, 데이터 직렬화, 메모리 공유, 운영 상한**을 함께 설계하는 문제다.

오늘 글은 아래 질문에 답하는 데 집중한다.

- GIL은 정확히 무엇을 막고, 무엇은 막지 않을까?
- `thread`, `asyncio`, `process`, 외부 워커 중 무엇을 어떤 기준으로 선택해야 할까?
- `fork`, `spawn`, `forkserver`는 왜 다르고, 운영 기본값은 무엇이 좋을까?
- 병렬화가 느려지는 진짜 원인인 `pickle` 비용과 데이터 복제를 어떻게 줄일까?
- `shared_memory`와 chunking을 어디까지 믿어야 하고, 언제 오히려 복잡도만 키울까?
- API 서버, 배치, 데이터 처리에서 실전 기본 패턴은 무엇일까?

핵심만 먼저 요약하면 이렇다.

- GIL은 **한 프로세스 안에서 Python 바이트코드를 동시에 여러 스레드가 실행하는 것**을 제한한다
- CPU 바운드 순수 Python 작업은 대개 스레드보다 **프로세스 분리**가 유리하다
- 하지만 프로세스를 늘리면 바로 빠른 게 아니라, **직렬화 비용과 메모리 이동 비용**이 병목으로 튀어나온다
- `fork`는 빠른 시작이 장점이지만 상태 복제가 위험하고, `spawn`은 느리지만 더 예측 가능하다
- 병렬화 전 첫 질문은 "워커 수 몇 개?"가 아니라 **"작업 한 건당 계산량이 데이터 이동량보다 충분히 큰가?"** 여야 한다
- 실전 최적화는 프로세스 개수보다 **작업 단위(chunk), 입력 표현, 메모리 공유 전략, 관측 지표**가 더 큰 차이를 만든다

---

## 배경: 왜 Python CPU 병렬화는 자주 오해될까?

Python에서 동시성 이야기가 나오면 대화가 너무 빨리 단순화된다.

- I/O 바운드면 async
- CPU 바운드면 multiprocessing

방향은 맞지만, 운영에서는 이 두 줄짜리 정리가 거의 항상 부족하다.

예를 들어 주문 추천 API에서 상품 50만 건의 feature를 읽어 점수를 계산한다고 하자.

팀은 처음에 이렇게 생각하기 쉽다.

- 요청마다 점수 계산은 CPU 바운드다
- 스레드는 GIL 때문에 병렬이 안 된다
- 프로세스를 8개 띄우면 8배 빨라질 것이다

하지만 실제 결과는 이렇게 나온다.

- 워커 시작 비용이 크다
- 요청마다 큰 딕셔너리나 DataFrame을 프로세스에 넘기느라 pickle 시간이 길다
- 각 프로세스가 메모리를 별도로 잡아 RSS가 튄다
- OpenBLAS, MKL, NumPy 내부 스레드까지 겹쳐 오히려 oversubscription이 생긴다
- 결국 CPU는 바쁜데 tail latency는 더 나빠진다

이 상황을 피하려면 먼저 아래 순서로 봐야 한다.

1. **정말 순수 Python CPU 작업인가?**
2. **작업 단위가 프로세스 경계를 넘길 만큼 충분히 무거운가?**
3. **큰 데이터를 매번 복사하지 않고 참조하거나 재사용할 수 있는가?**
4. **프로세스가 안전하게 시작되고 종료되는가?**
5. **워커 수와 내부 라이브러리 스레드 수가 서로 충돌하지 않는가?**

병렬화는 계산을 나누는 기술이기도 하지만, 동시에 **복제 비용을 통제하는 기술**이기도 하다.

---

## 핵심 개념 1: GIL은 "Python 전체가 싱글 스레드"라는 뜻이 아니다

GIL, Global Interpreter Lock, 은 CPython에서 한 시점에 하나의 스레드만 Python 바이트코드를 실행하도록 만드는 락이다.

여기서 가장 흔한 오해는 두 가지다.

### 오해 1: GIL이 있으면 스레드는 아무 의미가 없다

그렇지 않다. I/O 대기 시간이 큰 작업에서는 스레드가 여전히 유용하다.

- HTTP 호출
- DB 네트워크 대기
- 파일 읽기/쓰기
- 외부 시스템 응답 대기

이 경우 스레드는 CPU를 점유하지 않은 채 대기하므로, 다른 스레드가 진행할 수 있다.

### 오해 2: CPU 작업은 무조건 스레드가 전혀 소용없다

이것도 절반만 맞다. 순수 Python 루프는 GIL 영향을 크게 받지만, C extension이 내부에서 GIL을 해제하는 경우는 다르다.

대표적인 예시는 아래와 같다.

- NumPy 일부 벡터 연산
- Pandas 내부의 특정 연산
- Polars
- 압축, 해시, 직렬화 라이브러리의 일부 구현
- 이미지/수치 계산 라이브러리

즉 실무 질문은 "CPU인가 I/O인가"보다 조금 더 정교해야 한다.

> 이 작업은 **Python 인터프리터가 오래 잡고 있는가**, 아니면 **C 레벨 구현이 대부분의 시간을 쓰는가**?

### 실무 분류 기준

#### 1) 순수 Python CPU 바운드

```python
def score(records: list[dict]) -> int:
    total = 0
    for record in records:
        for value in record["values"]:
            total += (value * value) % 97
    return total
```

이런 류는 GIL 영향이 크다. 스레드 여러 개를 돌려도 같은 프로세스 안에서는 확장성이 낮다.

#### 2) C extension 중심 CPU 작업

```python
import numpy as np

arr = np.random.rand(10_000_000)
result = np.sqrt(arr).sum()
```

이런 류는 라이브러리 구현과 내부 스레드 모델에 따라 다르다. 무조건 프로세스로 나누기보다, 먼저 라이브러리 자체의 병렬화 특성을 확인해야 한다.

#### 3) 혼합형 작업

- 전처리는 Python 루프
- 핵심 계산은 NumPy/Pandas
- 후처리는 JSON 직렬화와 API 응답 생성

이런 경우 전체 요청 시간을 구간별로 분해하지 않으면 잘못된 병렬화 결정을 내리기 쉽다.

### 먼저 해야 할 것: wall time이 아니라 CPU time과 프로파일을 같이 본다

병렬화 전에 최소한 아래는 확인하는 편이 좋다.

- 함수별 wall time
- 프로세스 CPU 사용률
- 입력 크기 대비 처리 시간 증가 추세
- 직렬화/역직렬화 비율
- 라이브러리 내부 스레드 사용 여부

가장 위험한 패턴은 **프로파일링 없이 바로 ProcessPoolExecutor를 붙이는 것**이다. 이러면 진짜 병목이 계산이 아니라 데이터 준비나 직렬화였다는 사실을 한참 뒤에 알게 된다.

---

## 핵심 개념 2: thread, asyncio, process, 외부 워커는 역할이 다르다

CPU 병렬화를 설계할 때는 도구 선택이 먼저다. 이름이 비슷해 보여도 책임이 전혀 다르다.

| 선택지 | 잘 맞는 문제 | 장점 | 주의점 |
| --- | --- | --- | --- |
| `asyncio` | I/O 대기가 많은 고동시성 처리 | 연결 수를 효율적으로 다룸 | CPU 작업이 들어오면 이벤트 루프 응답성 붕괴 |
| ThreadPoolExecutor | 짧은 blocking I/O, 일부 C extension 작업 | API 서버에 붙이기 쉬움 | 순수 Python CPU 작업은 GIL 영향 큼 |
| ProcessPoolExecutor / multiprocessing | 순수 Python CPU 바운드, 독립 계산 | 멀티코어 활용 가능 | pickle, 시작 비용, 메모리 복제 |
| 외부 워커 시스템(Celery, Arq, Ray, Spark 등) | 긴 작업, 재시도, 스케줄링, 분산 | 장애 격리와 운영성 좋음 | 인프라 복잡도 증가 |

핵심은 "무엇이 더 강력한가"가 아니라 **요청 경계와 실패 경계를 어디에 둘 것인가**다.

### API 서버 안에서 바로 처리해도 되는 경우

- 계산 시간이 짧다, 예를 들어 수십 ms에서 수백 ms 수준
- 입력과 출력이 작다
- 워커 풀 상한을 명확히 둘 수 있다
- timeout 시 요청 단위로 취소해도 된다

### 외부 워커로 빼야 하는 경우

- 계산 시간이 수 초 이상 길다
- 재시도 정책이 필요하다
- 작업이 대용량 입력을 다룬다
- 요청/응답 경계보다 비동기 job 경계가 더 자연스럽다
- API 서버 메모리와 CPU를 격리하고 싶다

실무에서 자주 보는 실수는, **CPU 무거운 작업을 일단 API 서버 프로세스 안에 우겨 넣는 것**이다. 이 경우 순간 부하에서 사용자 요청과 백그라운드 계산이 같은 자원을 먹으면서 장애가 함께 전염된다.

---

## 핵심 개념 3: `fork`, `spawn`, `forkserver`는 성능 옵션이 아니라 안전성 옵션이다

Python 멀티프로세싱에서 프로세스 시작 방식은 생각보다 중요하다.

### 1) `fork`

부모 프로세스를 복제해서 자식 프로세스를 만든다.

장점:

- 시작이 빠르다
- 부모 메모리 페이지를 copy-on-write로 공유해 초기 비용이 낮아 보일 수 있다

주의점:

- 부모가 들고 있던 thread, lock, DB connection, event loop 상태를 복제해 예측하기 어렵다
- 라이브러리에 따라 deadlock, 소켓 문제, 내부 상태 꼬임이 생길 수 있다
- "처음엔 잘 되는데 운영에서 가끔 멈춤" 같은 장애의 원인이 되기 쉽다

### 2) `spawn`

새 인터프리터를 깨끗하게 띄우고 필요한 코드를 다시 import 한다.

장점:

- 상태가 더 깨끗하다
- 플랫폼 간 동작이 비교적 일관적이다
- thread, connection, runtime state를 덜 위험하게 다룬다

주의점:

- 시작 비용이 더 크다
- import 비용이 누적된다
- top-level import 부작용, `if __name__ == "__main__"` 누락 문제가 쉽게 드러난다

### 3) `forkserver`

초기 서버 프로세스를 하나 만들고, 이후 자식은 그 서버를 통해 fork 한다.

장점:

- 일부 `fork` 장점과 안정성 절충

주의점:

- 팀에서 익숙하지 않은 경우 운영 복잡도가 늘 수 있다
- 라이브러리 조합별 검증이 필요하다

### 운영 기본값은 무엇이 좋을까?

웹 서버, 비동기 런타임, DB 연결, 백그라운드 스레드가 섞인 현대 Python 서비스에서는 보수적으로 `spawn` 쪽이 더 안전한 경우가 많다.

특히 아래 환경에서는 `spawn`을 우선 검토하는 편이 낫다.

- FastAPI, Uvicorn, Gunicorn 조합
- 이미 여러 thread가 떠 있는 프로세스
- DB pool, Redis client, OpenTelemetry, 로거 핸들러가 초기화된 상태
- macOS, Windows 개발 환경과 Linux 운영 환경을 함께 맞춰야 하는 팀

예시는 이런 형태가 안전하다.

```python
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor

ctx = mp.get_context("spawn")
pool = ProcessPoolExecutor(max_workers=4, mp_context=ctx)
```

### `fork`를 쓸 때 특히 조심할 것

- 부모에서 이미 맺은 DB connection을 자식이 그대로 재사용한다고 가정하지 말 것
- 로깅 핸들러, 파일 디스크립터, 네트워크 소켓 상태를 믿지 말 것
- 이벤트 루프나 thread pool이 초기화된 뒤 `fork` 하지 말 것

실무 기준으로 보면, `fork`는 "빠를 수 있는 옵션"이지 "기본 안전 옵션"은 아니다.

---

## 핵심 개념 4: 프로세스 병렬화의 진짜 병목은 계산보다 `pickle` 인 경우가 많다

프로세스를 쓰면 주소 공간이 분리된다. 즉 데이터를 넘길 때는 결국 **직렬화하거나 복사**해야 한다.

이 지점에서 많은 병렬화 시도가 망가진다.

### 안티패턴: 큰 객체를 매 요청마다 워커에 통째로 넘기기

```python
from concurrent.futures import ProcessPoolExecutor


def compute(df):
    return heavy_score(df)

with ProcessPoolExecutor(max_workers=4) as pool:
    result = list(pool.map(compute, huge_dataframes))
```

겉보기에는 병렬이다. 실제로는 아래 비용이 숨어 있다.

- 부모 프로세스가 `df`를 pickle 한다
- OS pipe 또는 queue를 통해 자식에게 보낸다
- 자식 프로세스가 다시 unpickle 한다
- 결과도 같은 과정을 거꾸로 거친다

작업 한 건이 20ms 계산인데 직렬화가 35ms면, 병렬화는 시작 전부터 손해다.

### 판단 기준: 계산 대 직렬화 비율

아주 거친 기준이지만 실무에서는 아래 질문이 유용하다.

- 입력 직렬화 + 전달 + 역직렬화 시간보다 계산 시간이 충분히 큰가?
- 작업 한 건이 너무 작아서 스케줄링 오버헤드만 늘어나지 않는가?
- 결과를 전체 객체가 아니라 요약값으로 줄일 수 있는가?

보통은 **작업 한 건을 더 크게 묶는 것**, 즉 chunking 이 가장 먼저 먹힌다.

### 작은 작업을 묶어 chunk로 보내기

```python
from collections.abc import Iterable


def chunked(seq: list[int], size: int) -> Iterable[list[int]]:
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


def score_chunk(items: list[int]) -> int:
    total = 0
    for item in items:
        total += item * item
    return total
```

이 방식은 세 가지를 동시에 줄인다.

- 프로세스 간 메시지 수
- 함수 호출 횟수
- 직렬화 헤더 오버헤드

### 입력을 "데이터 자체"가 아니라 "위치"로 넘기기

대용량 CSV, Parquet, 이미지 파일, 세그먼트 데이터라면 객체를 보내지 말고 **파일 경로, 파티션 키, 오프셋 범위**를 보내는 편이 낫다.

예를 들어 배치라면 이런 접근이 좋다.

- 나쁜 방식: DataFrame 전체를 워커에 전달
- 더 나은 방식: `date=2026-04-21`, `partition=17` 같은 식별자 전달 후 워커가 직접 읽기

이렇게 하면 부모 프로세스가 메모리 복사 허브가 되는 문제를 피할 수 있다.

### 결과도 최소화해야 한다

입력만 큰 게 문제가 아니다. 결과도 큰 객체면 병목이 똑같이 반복된다.

좋은 패턴은 이렇다.

- 워커는 집계값, 파일 경로, 임시 결과 위치만 반환
- 큰 산출물은 공유 스토리지나 디스크에 쓰고 메타데이터만 부모에 전달

프로세스 병렬화에서 성능은 CPU보다 **경계 통과 데이터량**에 더 민감할 때가 많다.

---

## 핵심 개념 5: `shared_memory` 는 강력하지만, 만능 해결책은 아니다

`multiprocessing.shared_memory` 는 프로세스 간 메모리 블록을 공유하게 해 준다. 큰 배열이나 바이너리 버퍼를 복사 없이 재사용하고 싶을 때 특히 유용하다.

### 잘 맞는 경우

- 수치 배열처럼 메모리 레이아웃이 단순하다
- 읽기 전용 또는 제한된 쓰기 규칙을 둘 수 있다
- 워커들이 같은 대형 데이터를 반복 참조한다
- NumPy 배열처럼 버퍼 인터페이스를 잘 활용할 수 있다

### 잘 안 맞는 경우

- 파이썬 객체 그래프, 예를 들어 중첩 dict/list/object 를 그대로 공유하려 한다
- 동시 쓰기 충돌 제어가 필요하다
- 데이터 생명주기 관리가 복잡하다
- 개발자들이 shared memory cleanup 규칙에 익숙하지 않다

### 간단한 예시

```python
from multiprocessing import shared_memory
import numpy as np

arr = np.arange(1_000_000, dtype=np.int64)
shm = shared_memory.SharedMemory(create=True, size=arr.nbytes)
shared_arr = np.ndarray(arr.shape, dtype=arr.dtype, buffer=shm.buf)
shared_arr[:] = arr[:]

# 자식 프로세스는 shm.name, shape, dtype 만 전달받아 같은 버퍼를 연다
```

이 방식의 장점은 큰 배열 자체를 pickle 하지 않아도 된다는 점이다. 대신 운영에서는 새로운 책임이 생긴다.

- 누가 shared memory를 만들고 닫을 것인가
- 예외가 나면 unlink cleanup 은 어떻게 보장할 것인가
- 읽기 전용 규칙을 코드로 강제할 것인가
- 다중 쓰기 시 lock 이 필요한가

즉 `shared_memory` 는 성능 도구이자 동시에 **리소스 생명주기 설계 문제**다.

### 더 단순한 대안이 더 좋은 경우도 많다

아래 경우에는 굳이 shared memory 까지 가지 않는 편이 낫다.

- 파일 기반 mmap 으로 충분하다
- 파티션 파일을 워커가 직접 읽는 구조면 된다
- Arrow, Parquet, DuckDB 같은 컬럼형 처리로 Python 객체 생성을 줄일 수 있다
- 애초에 데이터 전처리를 SQL 쿼리 단계로 밀어 넣을 수 있다

실무에서는 종종 `shared_memory` 가 아니라 **입력 표현을 바꾸는 것**이 더 큰 이득을 준다.

---

## 핵심 개념 6: 작업 단위 설계가 워커 수보다 더 중요하다

병렬화 성능은 워커 수를 늘리면 선형으로 오를 것 같지만, 대부분 그렇지 않다. 이유는 간단하다.

- 작업 분배 비용이 있다
- 직렬화 비용이 있다
- 컨텍스트 전환 비용이 있다
- 결과 병합 비용이 있다
- 캐시 locality 가 나빠질 수 있다

그래서 실전에서는 워커 수보다 **작업 단위의 모양**이 먼저다.

### 좋은 작업 단위의 특징

- 한 건당 계산량이 충분히 크다
- 입력 표현이 작거나 재사용 가능하다
- 실패 시 재시도가 가능하다
- 결과가 합치기 쉽다
- 순서 의존성이 약하다

### 나쁜 작업 단위의 특징

- 너무 작아서 스케줄링 오버헤드가 계산보다 크다
- 입력 객체가 크고 깊어 pickle 비용이 높다
- 서로 같은 전역 상태를 공유해야 한다
- 부분 실패 시 전체를 다시 해야 한다

예를 들어 텍스트 100만 건을 정규화한다고 하자.

- 나쁜 방식: 문장 1개씩 프로세스에 보냄
- 더 나은 방식: 문장 5천 개 묶음을 chunk 로 보냄
- 더 좋은 방식: 파일 샤드 경로를 보내고 워커가 샤드 단위로 읽고 씀

작업 단위가 커질수록 보통 throughput 은 좋아진다. 다만 너무 크면 또 tail latency 와 불균형 문제가 생긴다. 결국 팀은 **chunk size 를 실험 가능한 설정값**으로 노출해야 한다.

---

## 실무 예시 1: FastAPI 에서 CPU 점수 계산을 안전하게 프로세스 풀로 분리하기

API 서버에서 가장 흔한 요구는 이것이다. 응답은 동기적으로 줘야 하지만, 계산이 순수 Python CPU 바운드라 스레드로는 부족한 경우다.

핵심 원칙은 네 가지다.

1. 요청마다 새 프로세스 풀을 만들지 않는다
2. 풀 크기를 CPU 수와 서비스 특성 기준으로 제한한다
3. 입력은 가능한 한 작게 전달한다
4. timeout 과 admission control 을 같이 둔다

```python
import asyncio
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor
from fastapi import FastAPI, HTTPException

app = FastAPI()
pool: ProcessPoolExecutor | None = None


def score_payload(payload: dict) -> dict:
    values = payload["values"]
    score = 0
    for value in values:
        score += (value * value) % 97
    return {"score": score, "count": len(values)}


@app.on_event("startup")
async def startup() -> None:
    global pool
    ctx = mp.get_context("spawn")
    pool = ProcessPoolExecutor(max_workers=4, mp_context=ctx)


@app.on_event("shutdown")
async def shutdown() -> None:
    global pool
    if pool is not None:
        pool.shutdown(wait=True, cancel_futures=True)
        pool = None


@app.post("/score")
async def score(body: dict) -> dict:
    if pool is None:
        raise HTTPException(status_code=503, detail="worker pool unavailable")

    loop = asyncio.get_running_loop()

    try:
        return await asyncio.wait_for(
            loop.run_in_executor(pool, score_payload, body),
            timeout=1.5,
        )
    except TimeoutError:
        raise HTTPException(status_code=504, detail="score timeout")
```

### 여기서 실전 포인트

- `spawn` 기반으로 풀을 고정 생성해, 요청마다 초기화 비용을 내지 않는다
- 프로세스 수는 서버 CPU 수와 웹 워커 수를 같이 고려한다
- timeout 을 요청 예산 안에 둔다
- 결과는 작은 dict 로 제한한다

### 여기서 추가로 필요한 운영 장치

- 동시 제출 수 상한, 예를 들어 세마포어 또는 큐 길이 제한
- 큐 대기 시간, 실행 시간, timeout 비율 메트릭
- 프로세스 풀 포화 시 degrade 전략, 예를 들어 429 또는 fallback

많은 팀이 timeout 만 두고 admission control 을 안 둔다. 그러면 부하가 몰릴 때 큐에서 오래 기다리다 timeout 나는 요청이 쌓여 **이미 실패할 요청에 자원을 계속 배분하는 상태**가 된다.

---

## 실무 예시 2: 배치에서 큰 DataFrame 을 직접 보내지 않고 파티션 단위로 처리하기

일 배치나 ETL 에서는 pandas DataFrame 을 부모 프로세스에서 읽고 워커에 나눠주는 구조를 쉽게 떠올린다. 하지만 이 구조는 메모리와 pickle 비용 때문에 빨리 한계가 온다.

### 피해야 할 구조

1. 부모가 거대한 DataFrame 생성
2. `np.array_split` 같은 방식으로 나눔
3. 각 조각을 프로세스에 전달

겉보기에는 자연스럽지만, 실제로는 부모가 모든 데이터를 메모리에 올린 뒤 다시 복사하는 허브가 된다.

### 더 나은 구조

1. 부모는 처리 대상 파티션 목록만 만든다
2. 워커는 파티션 식별자만 받아 직접 읽는다
3. 워커는 집계 결과나 출력 파일 경로만 반환한다

```python
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp


def process_partition(partition_key: str) -> dict:
    # 예: s3://bucket/events/dt=2026-04-21/hour=13
    rows = load_partition(partition_key)
    result = transform_and_aggregate(rows)
    output_path = write_result(partition_key, result)
    return {"partition": partition_key, "output_path": output_path}


def main(partitions: list[str]) -> list[dict]:
    ctx = mp.get_context("spawn")
    with ProcessPoolExecutor(max_workers=6, mp_context=ctx) as pool:
        return list(pool.map(process_partition, partitions, chunksize=4))
```

### 이 구조가 좋은 이유

- 부모 프로세스 메모리 압박이 줄어든다
- 워커가 데이터 locality 를 더 잘 활용한다
- 재시도 단위가 파티션으로 명확해진다
- 실패한 파티션만 다시 처리하기 쉽다

배치에서 병렬화는 CPU 확장성 문제이기도 하지만 동시에 **재실행 단위 설계** 문제다.

---

## 실무 예시 3: 큰 읽기 전용 참조 데이터를 공유하고 싶을 때의 기준

추천, 룰 엔진, 피처 스코어링처럼 모든 작업이 같은 대형 참조 데이터를 읽는 경우가 있다. 예를 들면 아래와 같다.

- 2GB 짜리 임베딩 매트릭스
- 대형 룩업 테이블
- 정규화 사전
- 바이너리 모델 파라미터 일부

이때 선택지는 보통 세 가지다.

### 선택지 1: 각 프로세스가 독립 로드

장점:

- 구현이 단순하다
- 프로세스 격리가 명확하다

단점:

- 메모리 사용량이 크다
- 시작 시간이 길다

### 선택지 2: `fork` 의 copy-on-write 에 기대기

장점:

- 초기 메모리 공유처럼 보일 수 있다

단점:

- 쓰기가 조금만 섞여도 페이지 복제가 일어난다
- `fork` 자체의 안정성 문제가 남는다
- 라이브러리 상태 복제를 믿기 어렵다

### 선택지 3: `shared_memory`, mmap, 외부 저장소 활용

장점:

- 큰 읽기 전용 버퍼를 재사용할 수 있다
- 플랫폼과 구조에 따라 더 예측 가능하다

단점:

- lifecycle 관리가 어렵다
- 구현 복잡도가 올라간다

이 선택에서 중요한 질문은 이것이다.

- 데이터가 정말 읽기 전용인가?
- 프로세스 재기동 시 재초기화 비용을 감당 가능한가?
- 메모리 절감 효과가 구현 복잡도를 이길 만큼 큰가?

작은 팀에서는 shared memory 보다 **워커 시작 시 로컬 디스크 캐시에서 로드** 같은 단순 전략이 더 운영 친화적일 때도 많다.

---

## 트레이드오프: 빠른 `fork`, 안전한 `spawn`, 단순한 스레드, 무거운 외부 워커

현실적인 선택은 늘 절충이다.

### 스레드 중심 접근

좋은 점:

- 구현이 간단하다
- 메모리 공유가 자연스럽다
- 짧은 blocking I/O 와 일부 C extension 작업에는 효과적이다

아쉬운 점:

- 순수 Python CPU 작업 확장성이 낮다
- GIL 때문에 멀티코어 활용이 제한된다

### 프로세스 중심 접근

좋은 점:

- 순수 Python CPU 작업에서 멀티코어 활용 가능
- 장애가 어느 정도 격리된다

아쉬운 점:

- 직렬화 비용이 크다
- 메모리 사용량이 커지기 쉽다
- 시작 방식에 따른 운영 이슈가 많다

### 외부 워커 시스템

좋은 점:

- 재시도, 큐잉, 스케줄링, 관측성이 좋아진다
- API 서버와 자원을 격리하기 쉽다

아쉬운 점:

- 인프라와 운영 복잡도가 커진다
- 로컬 개발 경험이 나빠질 수 있다

### 언제 무엇을 추천할까?

- **짧은 I/O 작업**: `asyncio` 또는 thread pool
- **짧지만 무거운 CPU 계산**: 고정 `ProcessPoolExecutor`
- **긴 CPU/배치 작업**: 외부 워커 또는 파티션 기반 배치 엔진
- **대형 컬럼 데이터 처리**: Python 프로세스 분할 전에 SQL, DuckDB, Polars, Arrow 계열로 표현 전환 검토

중요한 건 Python 프로세스를 늘리는 것이 아니라, **어디까지를 Python 런타임이 담당하고 어디서 다른 계층에 일을 넘길지**를 정하는 것이다.

---

## 흔한 실수 1: 워커 수를 CPU 코어 수와 단순히 일치시키기

"8코어니까 프로세스도 8개"는 출발점일 뿐 정답이 아니다.

다음 요소를 같이 봐야 한다.

- 이미 웹 서버 worker 가 몇 개인가
- NumPy, BLAS, OpenMP 내부 스레드가 몇 개인가
- 같은 머신에서 DB, 캐시, 에이전트, 사이드카가 돌고 있는가
- 메모리 상한이 얼마나 되는가

특히 수치 라이브러리는 내부적으로 스레드를 또 쓰는 경우가 많다. 이 상태에서 프로세스까지 많이 늘리면 oversubscription 으로 오히려 느려진다.

### 운영 팁

- 프로세스 수를 늘리기 전에 라이브러리 내부 스레드 수를 고정한다
- CPU 사용률만 보지 말고 throughput, p95, p99 를 같이 본다
- RSS 증가와 page fault 도 같이 본다

---

## 흔한 실수 2: `fork` 이후 부모 상태를 자식이 안전하게 공유할 거라고 믿기

아래 객체는 `fork` 이후 특히 위험하다.

- DB connection pool
- Redis connection
- gRPC channel
- 이벤트 루프 관련 상태
- background thread 가 관리하는 객체
- 로깅 핸들러와 파일 디스크립터

겉으로는 "잘 되는 것처럼" 보일 수 있다. 하지만 운영에서는 드물게 멈추거나, 특정 부하에서만 깨지는 문제가 생긴다. 이런 류는 가장 디버깅 비용이 비싸다.

안전한 기본값은 간단하다.

- 자식 프로세스는 필요한 외부 리소스를 **자기 안에서 다시 초기화**한다
- 부모의 열린 connection 을 그대로 믿지 않는다

---

## 흔한 실수 3: 큰 Python 객체를 프로세스 간 전달하는 비용을 과소평가하기

특히 문제가 되는 입력은 아래와 같다.

- 깊은 중첩 dict/list
- 커다란 pandas DataFrame
- 커스텀 클래스 인스턴스 목록
- 문자열이 많은 JSON 유사 구조

이런 입력은 단순 바이트 배열보다 pickle 비용이 훨씬 커진다. 그래서 병렬화 전에 아래를 먼저 검토해야 한다.

- dict 대신 배열/튜플/버퍼 표현으로 바꿀 수 있는가
- 문자열 정규화를 미리 해 중복을 줄일 수 있는가
- 워커가 직접 읽도록 입력 표현을 바꿀 수 있는가

성능 문제는 종종 알고리즘보다 **자료구조 표현**에서 먼저 해결된다.

---

## 흔한 실수 4: 너무 작은 단위로 `submit()` 을 남발하기

작업이 지나치게 잘게 쪼개지면 아래 비용이 커진다.

- 스케줄링 비용
- 큐 경쟁
- 직렬화 헤더 비용
- 결과 결합 비용

예를 들어 1ms 짜리 계산 10만 건을 개별 `submit()` 하는 구조는 거의 항상 비효율적이다. 이럴 때는 보통 아래가 더 낫다.

- `map(..., chunksize=n)` 사용
- 상위에서 미리 chunk 생성
- 입력 샤드 단위 처리

실전에서는 작은 최적화보다 **chunk size 튜닝**이 훨씬 큰 효과를 주는 경우가 많다.

---

## 흔한 실수 5: `if __name__ == "__main__"` 와 import 부작용을 가볍게 보기

`spawn` 환경에서는 자식 프로세스가 모듈을 다시 import 한다. 이때 top-level 코드가 부작용을 일으키면 아래 문제가 생긴다.

- 워커가 뜰 때마다 초기화 코드가 반복 실행된다
- DB migration, 파일 생성, 네트워크 연결 같은 코드가 중복 실행된다
- 로컬에서는 되는데 특정 배포 환경에서만 이상 동작한다

그래서 멀티프로세싱 코드에서는 더더욱 아래 원칙이 중요하다.

- import 시점에는 선언만, 실행은 명시적 엔트리포인트에서
- 초기화 코드는 함수로 감싼다
- 스크립트 진입점은 `__main__` 가드 아래 둔다

---

## 흔한 실수 6: 실패와 종료를 설계하지 않고 throughput 만 본다

프로세스 병렬화는 빨라지는 순간보다, 실패 순간에 더 많은 문제가 생긴다.

- 일부 워커만 hung 상태가 되면 어떻게 감지할 것인가
- timeout 된 작업을 어떻게 정리할 것인가
- 부모가 종료될 때 자식은 어떻게 닫을 것인가
- 부분 성공 결과를 재실행 시 어떻게 다룰 것인가

특히 API 서버 안에서 프로세스 풀을 쓴다면 아래는 거의 필수다.

- 제출 큐 길이 메트릭
- 실행 시간 분포
- timeout 비율
- worker crash 횟수
- graceful shutdown 경로 테스트

병렬화는 성능 기능이면서 동시에 **신뢰성 기능**이다.

---

## 운영 체크리스트

### 병렬화 전에

- [ ] 프로파일링으로 진짜 병목이 CPU 계산인지 확인했다
- [ ] 순수 Python CPU 작업인지, C extension 중심 작업인지 분류했다
- [ ] 입력과 출력의 직렬화 비용을 샘플링했다
- [ ] 프로세스 경계를 넘길 데이터 표현을 최소화했다

### 설계 단계에서

- [ ] `thread`, `process`, 외부 워커 중 실패 경계에 맞는 모델을 골랐다
- [ ] `fork` 대신 `spawn` 이 더 안전한 환경인지 검토했다
- [ ] chunk size 와 max_workers 를 설정값으로 뒀다
- [ ] 큰 읽기 전용 데이터는 직접 전달 대신 참조 전략을 검토했다

### 운영 단계에서

- [ ] queue depth, task latency, timeout ratio, worker restart 수를 수집한다
- [ ] 프로세스 수와 라이브러리 내부 스레드 수를 함께 조정한다
- [ ] 메모리 사용량과 page fault, RSS 증가를 모니터링한다
- [ ] shutdown, timeout, partial failure 시나리오를 부하 테스트로 검증했다

---

## 한 줄 정리

Python CPU 병렬 처리의 핵심은 "프로세스를 몇 개 띄울까"가 아니라, **GIL의 한계를 이해한 뒤 데이터 이동 비용, 시작 방식, 작업 단위를 함께 설계해 계산보다 복제가 더 비싸지지 않게 만드는 것**이다.
