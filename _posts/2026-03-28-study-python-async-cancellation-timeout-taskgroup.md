---
layout: post
title: "Python asyncio 취소·타임아웃·TaskGroup 실전: 안전한 종료와 부분 실패 제어"
date: 2026-03-28 11:40:00 +0900
categories: [python]
tags: [study, python, asyncio, cancellation, timeout, taskgroup, concurrency, reliability, automation]
---

## 왜 이 주제가 실무에서 중요할까?

비동기 코드를 처음 도입할 때 팀이 가장 먼저 체감하는 건 "병렬로 빨라졌다"는 장점이다.

그다음 운영 단계에서 바로 맞닥뜨리는 건 대개 속도보다 **종료와 실패의 복잡성**이다.

- 클라이언트가 연결을 끊었는데 하위 작업은 계속 돈다
- 전체 요청은 timeout 되었는데 외부 API 호출은 뒤늦게 성공해 중복 반영을 만든다
- shutdown 시 worker가 절반만 정리되고 이벤트 루프에 미완료 task가 남는다
- 일부 하위 작업만 실패했을 때 무엇을 취소하고 무엇을 살려야 하는지 기준이 없다

이 문제는 문법이 아니라 **생명주기 설계** 문제다.

특히 Python 3.11+ 이후 `TaskGroup`, `asyncio.timeout()` 같은 도구가 들어오면서, 예전처럼 `create_task()`와 `gather()`를 여기저기 흩뿌리는 방식은 점점 더 위험해졌다. 지금 실무에서 중요한 건 "비동기를 많이 돌리는 법"이 아니라 **언제, 무엇을, 어떤 경계에서 취소할지 명확히 설계하는 법**이다.

---

## 배경: 왜 비동기 장애는 대개 취소 처리에서 시작될까?

운영 장애를 보면 CPU가 부족해서만 망하지 않는다.

오히려 아래처럼 **끝나야 할 작업이 안 끝나는 상황**이 더 자주 문제를 만든다.

### 1) 요청은 끝났는데 하위 task는 살아 있는 경우

예를 들어 API 한 번에 3개의 외부 서비스를 병렬 호출한다고 하자.

브라우저는 이미 timeout 되었는데 서버 내부 task는 계속 돌고 있으면, 사용자는 실패를 봤는데 백엔드에서는 결제 승인, 포인트 적립, 알림 발송 같은 부수효과가 늦게 발생할 수 있다.

이 상태가 누적되면 다음 문제가 이어진다.

- 불필요한 외부 API 비용 증가
- connection pool 점유 증가
- retry와 중복 실행의 경계 붕괴
- 로그 상으로는 성공인데 사용자 경험은 실패인 상태 발생

### 2) timeout을 "에러 한 종류" 정도로만 취급하는 경우

많은 코드베이스에서 timeout은 그냥 `except Exception` 안의 한 갈래처럼 처리된다.

하지만 timeout은 단순 예외가 아니라 **시간 예산(deadline)을 다 썼다는 시스템 신호**다. 이 신호를 받았는데도 하위 task를 정리하지 않으면, 시스템은 이미 실패한 요청에 계속 자원을 쓴다.

### 3) 취소를 예외 삼켜도 되는 것으로 오해하는 경우

`CancelledError`를 일반 예외처럼 로깅만 하고 삼키면 상위 호출자는 "취소가 반영됐다"고 믿지만 실제로는 task가 계속 실행될 수 있다.

이건 메모리 누수보다 더 까다롭다. 겉으로는 조용한데 내부 상태 일관성이 무너진다.

결국 비동기 안정성의 핵심은 처리량이 아니라 **취소 전파, cleanup, deadline 관리**다.

---

## 핵심 개념 1: 취소는 강제 종료가 아니라 협력적 종료다

Python `asyncio`의 취소는 스레드를 강제로 죽이는 모델이 아니다.

`task.cancel()`을 호출하면 다음 await 지점에서 `CancelledError`가 발생하도록 **신호를 보내는 방식**이다. 즉, 취소는 cooperative cancellation이다.

```python
import asyncio


async def worker() -> None:
    try:
        while True:
            await asyncio.sleep(1)
            print("working...")
    except asyncio.CancelledError:
        print("cleanup before exit")
        raise
```

여기서 중요한 포인트는 두 가지다.

- 취소는 `await` 지점에서 반영된다
- cleanup 후에는 보통 `raise`로 취소를 다시 올려보내야 한다

### 왜 `CancelledError`를 다시 던져야 할까?

실무에서 가장 흔한 안티패턴이 이것이다.

```python
async def bad_worker() -> None:
    try:
        await asyncio.sleep(10)
    except Exception:
        print("ignore all errors")
```

버전에 따라 `CancelledError`는 일반 `Exception`과 별개 취급이 다를 수 있고, 팀 코드 스타일에 따라 광범위 예외 처리에서 쉽게 섞여 들어간다.

핵심은 단순하다. **취소는 실패가 아니라 제어 흐름의 일부**로 다뤄야 한다.

따라서 cleanup이 필요하면 아래처럼 쓰는 편이 안전하다.

```python
async def safe_worker() -> None:
    try:
        await asyncio.sleep(10)
    except asyncio.CancelledError:
        # 리소스 반납, 상태 기록
        raise
    except Exception as exc:
        # 진짜 오류 처리
        print(f"unexpected error: {exc}")
        raise
```

### 이 개념이 중요한 이유

취소를 제대로 재전파하지 않으면 상위 orchestration은 작업이 멈췄다고 믿는데, 실제 하위 작업은 계속 돈다.

그러면 다음 배치가 같은 리소스를 잡고 들어오거나, 이미 실패한 요청의 후속 처리만 뒤늦게 실행되는 이상한 상태가 생긴다.

---

## 핵심 개념 2: timeout은 개별 함수 옵션이 아니라 전체 deadline 설계다

실무 코드에서 timeout은 대개 두 층위로 나뉜다.

1. **개별 I/O timeout**
   - DB, HTTP, Redis 같은 외부 의존성 호출별 제한
2. **상위 업무 deadline**
   - 이 요청 전체가 몇 ms 안에 끝나야 하는가

이 둘을 섞어 쓰면 의도와 실제 동작이 어긋난다.

예를 들어 외부 API 3개를 순차 호출하는데 각 호출 timeout을 3초로만 두면, 전체 요청은 9초까지 늘어날 수 있다. 사용자는 이미 2초 안에 응답이 오길 기대하는데 말이다.

### `asyncio.wait_for()`와 `asyncio.timeout()` 차이

둘 다 시간 제한에 쓸 수 있지만 쓰임새가 다르다.

#### `asyncio.wait_for()`

- 특정 awaitable 하나에 timeout을 건다
- 함수 단위 wrapping에 적합하다

```python
result = await asyncio.wait_for(fetch_user(), timeout=0.3)
```

#### `asyncio.timeout()`

- 컨텍스트 블록 전체에 deadline을 건다
- 여러 await가 묶인 업무 흐름에 적합하다

```python
async with asyncio.timeout(0.8):
    profile = await fetch_profile()
    orders = await fetch_orders()
```

실무에서는 보통 **업무 흐름에는 `asyncio.timeout()`**, **개별 외부 호출에는 client timeout**을 두는 구성이 더 읽기 쉽다.

### timeout을 설계할 때 중요한 질문

- 이 제한은 한 API 호출에 대한 것인가?
- 아니면 사용자 요청 전체 예산인가?
- timeout 이후 하위 task는 반드시 취소되어야 하는가?
- 재시도 대상인가, 즉시 실패 대상인가?
- 늦게 성공한 응답을 버릴 수 있는가?

이 질문 없이 숫자만 정하면, timeout은 운영 안정성 장치가 아니라 랜덤 장애 스위치가 된다.

---

## 핵심 개념 3: `TaskGroup`은 단순 병렬 실행 도구가 아니라 구조적 동시성의 기준점이다

예전 `asyncio` 코드에서는 아래 패턴이 흔했다.

```python
results = await asyncio.gather(a(), b(), c())
```

짧은 예제에서는 편하지만, 실무에서는 다음 문제를 쉽게 만든다.

- 어떤 task가 실패했을 때 나머지를 어떻게 취소할지 모호함
- 생성된 task의 소유권이 분명하지 않음
- 중간에 `create_task()`를 남발하면 orphan task가 생김

`TaskGroup`의 장점은 **같은 생명주기를 공유하는 task 묶음**을 명시한다는 점이다.

```python
import asyncio


async def main() -> None:
    async with asyncio.TaskGroup() as tg:
        user_task = tg.create_task(fetch_user())
        order_task = tg.create_task(fetch_orders())

    user = user_task.result()
    orders = order_task.result()
```

### `TaskGroup`이 실무에서 좋은 이유

#### 1) 실패 전파 기준이 명확하다

한 task가 예외로 실패하면 같은 그룹의 다른 task를 취소하고, 그룹 전체를 실패로 본다.

즉 "같이 성공하거나 같이 정리되는 일의 단위"를 코드 구조로 드러낼 수 있다.

#### 2) task 생명주기 소유권이 분명하다

어느 블록 안에서 생성됐고, 언제 정리되는지 명확하다.

나중에 디버깅할 때 "이 task 누가 만들었지? 왜 아직 살아 있지?" 같은 추적 비용이 줄어든다.

#### 3) 구조적 동시성 덕분에 shutdown이 쉬워진다

상위 요청이 취소되면 하위 병렬 작업도 같은 구조 안에서 함께 정리된다.

이게 실제 운영에서는 엄청 큰 차이다. 병렬성이 많아질수록 기능보다 **정리 가능성**이 더 중요해진다.

### `gather()`를 버려야 한다는 뜻일까?

그건 아니다.

- 실패를 모아서 결과로 받고 싶다
- 일부 실패를 허용하고 계속 진행하고 싶다
- 서로 생명주기가 강하게 묶이지 않은 독립 작업이다

이런 경우 `gather(return_exceptions=True)`가 더 적합할 수 있다.

중요한 건 문법 취향이 아니라 **실패 전파 정책이 코드에 드러나는가**다.

---

## 핵심 개념 4: cleanup 코드는 성공 경로보다 더 구체적으로 써야 한다

비동기 코드에서 성공 경로는 테스트가 잘 된다.

반면 취소 경로는 부하 테스트, 네트워크 지연, shutdown, client disconnect가 겹칠 때만 터져서 뒤늦게 발견되는 경우가 많다.

그래서 cleanup은 추상적으로 쓰면 안 된다.

### 좋은 cleanup의 조건

- 어떤 리소스를 반납하는지 명확하다
- 부분 완료 상태를 어떻게 기록하는지 정해져 있다
- 재실행 시 안전한지 확인할 수 있다
- cleanup 자체가 오래 걸리면 어떤 상한으로 끊을지 결정돼 있다

예를 들어 아래처럼 쓰면 의도가 분명해진다.

```python
async def consume_message(message: Message, redis: RedisClient) -> None:
    lock_key = f"order:{message.order_id}"
    try:
        await redis.acquire(lock_key)
        await handle(message)
    except asyncio.CancelledError:
        await redis.release(lock_key)
        raise
    except Exception:
        await redis.release(lock_key)
        raise
    else:
        await redis.release(lock_key)
```

물론 중복이 보이면 `finally`로 합칠 수 있다.

하지만 중요한 건 "취소 시에도 release가 보장되는가"다. cleanup 생략으로 생기는 장애는 대개 다음 요청에서 폭발한다.

### cleanup에서 흔히 놓치는 것

- DB transaction rollback
- distributed lock release
- queue ack/nack 처리
- open stream/socket close
- 임시 파일 삭제
- in-memory 상태 플래그 복구

취소를 처리한다는 건 예외 메시지 하나 남기는 게 아니라 **중간 상태를 안전하게 되돌리는 것**이다.

---

## 핵심 개념 5: 일부는 취소하고 일부는 살리는 기준이 있어야 한다

현실의 서비스는 모든 하위 작업이 동등하지 않다.

예를 들어 주문 조회 API에서 아래 작업을 병렬 실행한다고 하자.

- 주문 본문 조회
- 결제 상태 조회
- 추천 상품 조회
- 행동 로그 전송

여기서 주문 본문과 결제 상태는 핵심일 수 있지만, 추천 상품과 로그 전송은 선택적일 수 있다.

이때 모든 task를 한 묶음으로 강하게 실패 전파시키면 가용성이 떨어진다.

반대로 전부 느슨하게 두면 핵심 데이터 일관성이 깨질 수 있다.

즉, 실무에서는 보통 아래처럼 나눈다.

### 강하게 묶을 것

- 같은 비즈니스 결과를 만들기 위한 핵심 데이터
- 하나라도 실패하면 전체 응답 의미가 사라지는 작업
- commit 이전 검증/조회/락 획득 단계

### 느슨하게 분리할 것

- 메트릭 전송
- 추천/부가 정보 조회
- 사후 알림 발송
- 감사 로그 적재

이 기준이 없으면 코드가 우연히 성공할 때만 맞고, 장애 상황에서는 매번 다른 동작을 한다.

---

## 실무 예시: API Aggregator에서 deadline과 부분 실패를 함께 다루기

상황을 하나 가정해보자.

대시보드 API가 아래 세 데이터를 병렬로 만든다.

- 사용자 프로필: 핵심
- 최근 주문: 핵심
- 추천 상품: 선택

요구사항은 다음과 같다.

- 전체 응답 예산은 800ms
- 추천 상품이 늦으면 기본값으로 대체 가능
- 상위 요청이 취소되면 하위 작업도 모두 정리돼야 함
- cleanup이 필요한 task는 취소를 삼키지 말아야 함

### 1) 개별 외부 호출은 명시적으로 감싸기

```python
import asyncio
from collections.abc import Awaitable
from typing import TypeVar

T = TypeVar("T")


async def with_timeout(awaitable: Awaitable[T], seconds: float) -> T:
    return await asyncio.wait_for(awaitable, timeout=seconds)
```

이 함수 자체는 단순하다.

중요한 건 모든 외부 호출이 **자기 timeout을 가진다**는 사실을 코드에 드러내는 것이다.

### 2) 선택적 작업은 fallback과 함께 분리하기

```python
async def fetch_profile(user_id: str) -> dict:
    ...


async def fetch_orders(user_id: str) -> list[dict]:
    ...


async def fetch_recommendations(user_id: str) -> list[dict]:
    ...


async def load_optional_recommendations(user_id: str) -> list[dict]:
    try:
        return await with_timeout(fetch_recommendations(user_id), 0.2)
    except TimeoutError:
        return []
```

여기서 포인트는 "추천 조회 timeout"을 전체 요청 실패로 승격하지 않는다는 점이다.

### 3) 핵심 데이터는 `TaskGroup`으로 함께 묶기

```python
async def load_dashboard(user_id: str) -> dict:
    async with asyncio.timeout(0.8):
        recommendations_task = asyncio.create_task(
            load_optional_recommendations(user_id)
        )

        async with asyncio.TaskGroup() as tg:
            profile_task = tg.create_task(
                with_timeout(fetch_profile(user_id), 0.3)
            )
            orders_task = tg.create_task(
                with_timeout(fetch_orders(user_id), 0.5)
            )

        recommendations = await recommendations_task

        return {
            "profile": profile_task.result(),
            "orders": orders_task.result(),
            "recommendations": recommendations,
        }
```

이 코드는 의도가 비교적 분명하다.

- 전체 deadline은 800ms
- 프로필/주문은 핵심이므로 강한 묶음
- 추천은 선택이므로 독립 fallback 허용

다만 여기서 한 가지 더 보완할 부분이 있다.

`recommendations_task`는 `create_task()`로 만들었기 때문에, 상위 흐름에서 예외가 날 때 취소/정리를 명시해주는 편이 더 안전하다.

### 4) orphan task를 남기지 않도록 정리까지 포함하기

```python
async def load_dashboard(user_id: str) -> dict:
    recommendations_task = asyncio.create_task(
        load_optional_recommendations(user_id)
    )

    try:
        async with asyncio.timeout(0.8):
            async with asyncio.TaskGroup() as tg:
                profile_task = tg.create_task(
                    with_timeout(fetch_profile(user_id), 0.3)
                )
                orders_task = tg.create_task(
                    with_timeout(fetch_orders(user_id), 0.5)
                )

            recommendations = await recommendations_task

            return {
                "profile": profile_task.result(),
                "orders": orders_task.result(),
                "recommendations": recommendations,
            }
    except asyncio.CancelledError:
        recommendations_task.cancel()
        raise
    except TimeoutError:
        recommendations_task.cancel()
        raise
    finally:
        if not recommendations_task.done():
            recommendations_task.cancel()
            await asyncio.gather(recommendations_task, return_exceptions=True)
```

이제 상위 취소나 timeout이 발생해도 선택 task가 고아처럼 남을 가능성이 훨씬 줄어든다.

실무에서는 이런 "남는 task가 없는가"가 중요하다. 테스트에서는 안 보이는데 운영에서는 connection, file descriptor, semaphore 슬롯이 조금씩 새기 때문이다.

---

## 한 단계 더: graceful shutdown과 worker 취소 설계

API 요청보다 더 어려운 건 장시간 도는 consumer/worker다.

여기서는 "지금 처리 중이던 메시지를 어디까지 마무리할 것인가"를 정해야 한다.

아래는 shutdown 친화적인 worker 스케치다.

```python
async def process_job(job: dict) -> None:
    ...


async def worker(queue: asyncio.Queue[dict]) -> None:
    while True:
        job = await queue.get()
        try:
            async with asyncio.timeout(10):
                await process_job(job)
        except asyncio.CancelledError:
            queue.task_done()
            raise
        except Exception:
            # 실패 저장 또는 재시도 큐 전송
            queue.task_done()
            raise
        else:
            queue.task_done()
```

이 코드는 단순하지만 운영 기준에서 세 가지를 생각하게 만든다.

- 취소되면 `task_done()`을 어떻게 처리할 것인가
- 실패 작업은 nack/requeue할 것인가
- 종료 시 `queue.join()`까지 기다릴 것인가, 지금 작업만 마치고 끊을 것인가

즉 shutdown 정책도 결국 비즈니스 결정이다.

### 종료 정책은 보통 세 가지로 나뉜다

#### 1) 즉시 중단

- 장점: 종료 속도가 빠름
- 단점: 중간 상태 정리가 어려움

#### 2) 현재 작업만 완료 후 중단

- 장점: 일관성 유지가 쉬움
- 단점: 종료 지연이 커질 수 있음

#### 3) 짧은 grace period 후 강제 중단

- 장점: 운영 현실과 안정성의 균형
- 단점: 각 작업이 grace budget 안에 정리 가능해야 함

실무에서는 3번이 가장 많다. Kubernetes, systemd, ECS 같은 환경도 결국 이 패턴에 가깝다.

---

## 트레이드오프: 취소를 엄격히 처리할수록 코드가 복잡해진다

좋은 취소 처리는 공짜가 아니다.

### 1) 단순한 코드 vs 예측 가능한 종료

`await gather(...)` 한 줄이면 끝날 코드를 `TaskGroup`, deadline, cleanup, fallback으로 나누면 확실히 길어진다.

하지만 운영 코드에서 중요한 건 짧은 코드보다 **틀렸을 때 예측 가능한 코드**다.

### 2) 빠른 실패 vs 부분 성공

하나라도 실패하면 전체를 취소하는 전략은 일관성 측면에서 좋다.

반면 사용자 경험 측면에서는 너무 보수적일 수 있다. 추천, 통계, 알림 같은 부가 기능은 부분 성공을 허용하는 편이 낫다.

결국 핵심은 "어떤 작업을 같은 운명으로 묶을 것인가"다.

### 3) 짧은 timeout vs 안정적 성공률

timeout을 짧게 잡으면 tail latency는 줄어든다.

대신 일시적 네트워크 흔들림에도 실패율이 높아질 수 있다. 특히 외부 API 호출이 많은 서비스는 p95, p99 latency 기반으로 timeout을 정해야지, 감으로 200ms 같은 숫자를 박으면 안 된다.

### 4) cleanup 보장 vs 종료 속도

취소 시 lock release, rollback, flush를 모두 보장하면 안전하다.

하지만 그 cleanup 자체가 오래 걸리면 shutdown이 늦어진다. 그래서 cleanup에도 budget과 우선순위가 필요하다.

---

## 흔한 실수

### 1) `create_task()`만 해두고 회수하지 않는다

이건 비동기 코드의 대표적인 누수 포인트다.

생성한 task를 어디서 await할지, 실패 시 누가 취소할지, 종료 시 누가 join할지 없다면 결국 orphan task가 된다.

### 2) `CancelledError`를 로깅만 하고 삼킨다

취소는 "오류를 처리했다"가 아니라 "종료 요청을 받았다"에 가깝다.

cleanup 후 재전파하지 않으면 상위 제어 흐름이 깨진다.

### 3) timeout을 중첩만 하고 전체 deadline은 없다

HTTP 클라이언트 timeout, DB timeout, 함수 timeout은 있는데 사용자 요청 전체 budget이 없으면 요청 하나가 시스템 안에서 너무 오래 떠다닌다.

개별 timeout과 상위 deadline은 분리해서 설계해야 한다.

### 4) `return_exceptions=True`를 의미 없이 남발한다

이 옵션은 유용하지만, 실패를 값처럼 다뤄도 되는 경우에만 맞다.

핵심 작업의 실패까지 리스트 안의 값으로 눌러버리면 장애가 조용히 숨어든다.

### 5) shutdown 테스트를 로컬 happy path로만 확인한다

실제 문제는 SIGTERM, client disconnect, upstream timeout, queue drain이 겹칠 때 발생한다.

취소 경로는 반드시 별도 테스트 케이스가 있어야 한다.

### 6) cleanup이 멱등적이지 않다

취소와 재시도는 같이 온다.

따라서 lock release, 상태 복구, 임시 파일 삭제 같은 cleanup은 두 번 실행돼도 안전해야 한다. 그렇지 않으면 장애 복구 과정에서 2차 장애가 난다.

---

## 운영 체크리스트

### 취소/타임아웃 설계

- [ ] 요청 전체 deadline과 개별 I/O timeout이 구분돼 있는가?
- [ ] timeout 이후 하위 task를 반드시 취소하는가?
- [ ] 늦게 도착한 성공 응답을 버려도 되는지 결정했는가?
- [ ] 핵심 작업과 선택 작업을 구분했는가?

### 구조적 동시성

- [ ] 함께 성공/실패해야 하는 task를 `TaskGroup`으로 묶었는가?
- [ ] `create_task()`를 쓴 곳마다 소유권과 정리 책임이 명확한가?
- [ ] orphan task 탐지를 위한 로그/메트릭이 있는가?

### cleanup과 종료

- [ ] `CancelledError`에서 필요한 cleanup 후 재전파하는가?
- [ ] 락, 트랜잭션, 소켓, 파일, 큐 ack 상태를 정리하는가?
- [ ] cleanup 자체에도 시간 상한이나 우선순위가 있는가?
- [ ] shutdown 시 현재 작업 완료/즉시 중단/grace period 중 정책이 정해져 있는가?

### 테스트와 관측성

- [ ] client disconnect 시나리오를 재현해봤는가?
- [ ] 상위 deadline 초과 시 하위 외부 호출이 남지 않는지 검증했는가?
- [ ] 취소 횟수, timeout 비율, cleanup 실패율을 메트릭으로 보고 있는가?
- [ ] `Task was destroyed but it is pending!` 류 경고를 CI/운영 로그에서 잡고 있는가?

---

## 한 줄 정리

Python 비동기 안정성의 핵심은 더 많은 task를 돌리는 능력이 아니라, **취소를 협력적으로 전파하고, timeout을 deadline으로 설계하고, `TaskGroup`으로 같은 생명주기를 묶어 orphan task 없이 정리하는 능력**에 있다.
