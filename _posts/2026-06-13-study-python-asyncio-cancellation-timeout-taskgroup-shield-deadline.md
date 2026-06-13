---
layout: post
title: "Python asyncio 취소와 타임아웃 실전: TaskGroup, CancelledError, Shield, Deadline으로 비동기 작업을 끝까지 통제하는 법"
date: 2026-06-13 11:50:00 +0900
categories: [python]
tags: [study, python, asyncio, cancellation, timeout, taskgroup, cancellederror, shield, deadline, structured-concurrency, backend, reliability]
permalink: /python/2026/06/13/study-python-asyncio-cancellation-timeout-taskgroup-shield-deadline.html
---

## 배경: asyncio 장애는 느린 작업보다 "끝나야 할 작업이 끝나지 않는 것"에서 더 자주 커진다

Python에서 `asyncio`를 쓰기 시작하면 처음에는 동시성 개수가 가장 눈에 띈다.

- `asyncio.gather()`로 외부 API를 병렬 호출한다.
- `asyncio.Queue`와 worker pool로 메시지를 처리한다.
- FastAPI endpoint 안에서 여러 I/O를 동시에 기다린다.
- WebSocket, long polling, streaming response처럼 오래 살아 있는 연결을 다룬다.

이 단계에서는 "동시에 많이 처리한다"가 핵심처럼 보인다. 하지만 운영 트래픽이 붙으면 더 중요한 질문이 나온다.

> **이 작업은 언제 포기해야 하며, 포기한다고 결정했을 때 실제로 무엇이 멈춰야 하는가?**

실무 장애는 대개 아래처럼 시작한다.

- HTTP 요청은 timeout으로 끊겼는데 내부 task는 계속 외부 API를 호출한다.
- `wait_for()`를 걸었는데 DB transaction cleanup이 끝나기 전에 `CancelledError`가 삼켜진다.
- 여러 child task 중 하나가 실패했는데 나머지는 계속 돌면서 중복 side effect를 만든다.
- 배치 종료 시 signal을 받았지만 queue item의 ack/nack 기준이 불명확하다.
- `gather(return_exceptions=True)`가 실패를 값처럼 모아 버려 운영 알림이 늦어진다.
- cleanup을 보호하려고 `shield()`를 남발하다가 프로세스 종료가 지연된다.
- timeout을 각 함수마다 따로 걸어 전체 요청 deadline보다 긴 작업 조합이 만들어진다.

이 문제는 `async`와 `await` 문법을 안다고 해결되지 않는다. 오히려 문법이 익숙해진 뒤에 더 많이 터진다. 이유는 간단하다. 비동기 코드에서 실패와 취소는 일반 예외보다 더 전염성이 강하고, 호출자가 더 이상 결과를 원하지 않는 순간에도 callee가 자원을 들고 있을 수 있기 때문이다.

동기 코드에서는 함수가 실행 중이면 호출자도 보통 그 함수가 끝나기를 기다린다. 하지만 비동기 코드에서는 task가 따로 생기고, 취소가 전파되고, timeout이 외부에서 걸리고, event loop가 여러 coroutine을 번갈아 실행한다. 그래서 "함수가 실패했다"보다 "작업 그래프 전체가 어떤 상태로 정리되는가"가 중요하다.

오늘 글은 중급 이상 Python 개발자를 기준으로 `asyncio`의 취소와 타임아웃을 운영 코드 관점에서 정리한다.

이번 글에서 답하려는 질문은 아래와 같다.

1. `CancelledError`는 왜 일반 예외처럼 잡으면 안 되는가?
2. `asyncio.wait_for()`와 `asyncio.timeout()`은 무엇이 다르고 어디에 써야 하는가?
3. `TaskGroup`은 `gather()`보다 어떤 실패 전파 모델을 제공하는가?
4. deadline을 함수마다 흩어진 timeout이 아니라 요청 전체 시간 예산으로 설계하려면 어떻게 해야 하는가?
5. cleanup, commit, ack, unlock 같은 마지막 작업은 언제 `shield()`로 보호하고 언제 보호하면 안 되는가?
6. FastAPI, worker, batch shutdown에서 취소를 어떻게 다뤄야 데이터 유실과 중복 처리를 줄일 수 있는가?
7. 취소 가능한 코드를 테스트하고 관측하려면 어떤 지표와 시나리오가 필요한가?

핵심 결론부터 말하면 이렇다.

1. `CancelledError`는 실패라기보다 **호출자가 더 이상 이 작업을 원하지 않는다는 제어 신호**에 가깝다.
2. 취소를 잡았다면 cleanup 후 반드시 다시 전파하는 것이 기본이다.
3. `TaskGroup`은 child task 실패 시 나머지 sibling을 취소하는 구조화된 동시성 모델을 제공한다.
4. timeout은 함수별 숫자보다 **상위 요청 deadline을 하위 작업에 나눠 주는 방식**이 운영에 강하다.
5. `shield()`는 cleanup 보호용으로 좁게 써야 하며, 비즈니스 작업 전체를 취소 불가능하게 만들면 장애 반경이 커진다.
6. queue worker에서는 취소 시 ack, nack, retry, DLQ 기준을 명시해야 한다.
7. 좋은 asyncio 코드는 빠른 코드가 아니라 **취소되어도 자원과 상태가 예측 가능하게 정리되는 코드**다.

---

## 먼저 큰 그림: 취소는 예외 처리 문제가 아니라 생명주기 설계 문제다

`asyncio`에서 task는 독립적인 실행 단위다. `create_task()`를 호출하면 현재 coroutine과 별도로 실행될 수 있는 작업이 event loop에 등록된다.

```python
task = asyncio.create_task(send_webhook(event))
```

이 한 줄은 생각보다 큰 결정을 포함한다.

- 누가 이 task의 완료를 기다리는가?
- 실패하면 누가 관측하는가?
- 호출자가 취소되면 이 task도 취소되어야 하는가?
- 프로세스 종료 시 이 task는 얼마나 기다릴 수 있는가?
- 이미 외부 side effect를 냈다면 재시도 기준은 어디에 있는가?

동시성 코드를 불안정하게 만드는 원인은 보통 `await` 누락 하나가 아니다. 더 근본적으로는 task의 owner가 불명확한 것이다.

비동기 작업을 만들 때는 반드시 owner가 있어야 한다. owner란 아래 책임을 가진 코드다.

- task를 시작한다.
- task의 성공과 실패를 관측한다.
- task가 더 이상 필요 없을 때 취소한다.
- 취소 후 cleanup이 끝났는지 확인한다.
- 실패를 로그, 메트릭, 재시도 정책으로 번역한다.

`TaskGroup`이 중요한 이유도 여기에 있다. `TaskGroup`은 여러 child task를 만든 뒤, 그 task들이 group scope를 벗어나지 못하게 한다. 즉 동시성의 생명주기를 코드 블록으로 닫는다.

반대로 fire-and-forget task는 owner가 사라지기 쉽다.

```python
asyncio.create_task(send_webhook(event))
return {"ok": True}
```

이 코드는 짧지만 질문이 남는다.

- `send_webhook()`이 실패하면 어디에 남는가?
- 서버 shutdown 중이면 어떻게 되는가?
- 요청 trace id가 task 안까지 이어지는가?
- 같은 event를 다시 보내도 되는가?

fire-and-forget이 항상 나쁜 것은 아니다. 하지만 운영 코드에서는 "잊어버린다"가 아니라 **별도의 owner로 넘긴다**가 되어야 한다. 예를 들어 durable queue, background supervisor, outbox worker가 그 owner가 될 수 있다.

취소 설계의 첫 번째 원칙은 이것이다.

> task를 만들었다면 그 task를 누가 끝까지 책임지는지 코드 구조 안에 보여야 한다.

---

## 핵심 개념 1: `CancelledError`는 대부분 다시 던져야 한다

`asyncio`에서 task를 취소하면 task 내부 coroutine에는 `CancelledError`가 주입된다.

```python
task.cancel()
```

그러면 해당 task가 다음 cancellation point에 도달할 때 `CancelledError`가 발생한다. 대표 cancellation point는 `await`다.

```python
async def sync_profile(user_id: int) -> None:
    profile = await fetch_profile(user_id)
    await save_profile(profile)
```

이 task가 `fetch_profile()`을 기다리는 중 취소되면 `await fetch_profile(...)` 지점에서 `CancelledError`가 발생할 수 있다.

문제는 많은 코드가 아래처럼 예외를 너무 넓게 잡는다는 점이다.

```python
async def sync_profile(user_id: int) -> None:
    try:
        profile = await fetch_profile(user_id)
        await save_profile(profile)
    except Exception:
        logger.exception("profile sync failed")
```

Python 버전에 따라 `CancelledError`의 상속 관계를 정확히 확인해야 하지만, 실무 원칙은 버전과 무관하게 같다.

> 취소 신호를 일반 실패처럼 삼키지 말고, cleanup 후 호출자에게 다시 돌려보내라.

좋은 패턴은 아래에 가깝다.

```python
async def sync_profile(user_id: int) -> None:
    try:
        profile = await fetch_profile(user_id)
        await save_profile(profile)
    except asyncio.CancelledError:
        logger.info("profile sync cancelled", extra={"user_id": user_id})
        raise
    except Exception:
        logger.exception("profile sync failed", extra={"user_id": user_id})
        raise
```

여기서 중요한 점은 `CancelledError`를 로깅할 수는 있지만, 기본적으로 다시 `raise`한다는 것이다.

### 왜 취소를 삼키면 위험한가

취소는 호출자가 "이 작업의 결과는 더 이상 필요 없고, 가능하면 멈춰 달라"고 보낸 신호다. 이 신호를 함수 내부에서 삼키면 상위 레이어는 task가 정상 종료된 것으로 오해할 수 있다.

```python
async def worker_loop() -> None:
    while True:
        try:
            item = await queue.get()
            await process(item)
        except Exception:
            logger.exception("worker error")
```

이런 구조에서 취소가 삼켜지면 shutdown이 깨진다. 프로세스는 종료하라고 signal을 받았는데 worker는 loop를 계속 돈다. Kubernetes가 grace period를 다 쓰고 강제 종료할 때까지 기다릴 수도 있다.

더 위험한 것은 transaction과 lock이다.

```python
async def update_order(conn, order_id: int) -> None:
    async with conn.transaction():
        await conn.execute("select pg_advisory_lock($1)", order_id)
        await conn.execute("update orders set status = 'PROCESSING' where id = $1", order_id)
        await call_partner_api(order_id)
        await conn.execute("select pg_advisory_unlock($1)", order_id)
```

이 코드는 여러 면에서 좋지 않지만, 취소 관점에서 특히 위험하다. `call_partner_api()`를 기다리는 중 취소되면 unlock이 실행되지 않을 수 있다. 물론 transaction scope와 connection close가 일부 자원을 정리할 수 있지만, advisory lock 종류와 scope, driver 동작에 따라 기대가 달라진다.

이런 코드는 `try/finally`로 자원 해제를 명시해야 한다.

```python
async def update_order(conn, order_id: int) -> None:
    locked = False
    async with conn.transaction():
        try:
            await conn.execute("select pg_advisory_lock($1)", order_id)
            locked = True
            await conn.execute(
                "update orders set status = 'PROCESSING' where id = $1",
                order_id,
            )
            await call_partner_api(order_id)
        finally:
            if locked:
                await conn.execute("select pg_advisory_unlock($1)", order_id)
```

그리고 이 `finally`도 취소될 수 있다는 점을 기억해야 한다. cleanup이 반드시 완료되어야 한다면 별도의 timeout과 `shield()`를 검토해야 한다. 이 부분은 뒤에서 다시 본다.

### 넓은 `except`는 항상 취소 경로를 먼저 생각해야 한다

운영 코드에서 넓은 예외 처리가 필요한 경우는 있다. worker loop, request middleware, batch item processor처럼 boundary 역할을 하는 코드가 그렇다.

하지만 이때도 취소는 별도로 다룬다.

```python
async def run_consumer() -> None:
    while True:
        try:
            message = await receive_message()
            await handle_message(message)
        except asyncio.CancelledError:
            logger.info("consumer cancelled")
            raise
        except TransientError as exc:
            logger.warning("transient message failure", exc_info=exc)
        except Exception:
            logger.exception("unexpected message failure")
```

팀 규칙으로는 아래 한 줄을 두는 것이 좋다.

> `except Exception`을 비동기 코드에 넣을 때는 바로 위에 `except asyncio.CancelledError: raise`가 필요한지 검토한다.

---

## 핵심 개념 2: `wait_for()`는 대상 awaitable을 취소하고 기다린다

`asyncio.wait_for()`는 오래된 코드에서 많이 쓰는 timeout 도구다.

```python
result = await asyncio.wait_for(fetch_user(user_id), timeout=1.0)
```

지정한 시간 안에 `fetch_user()`가 끝나지 않으면 `wait_for()`는 대상 task를 취소하고 timeout 예외를 발생시킨다. 여기서 자주 빠지는 포인트가 있다.

> timeout이 발생했다는 것은 "즉시 모든 작업이 멈췄다"가 아니라 "취소를 요청했고, 취소 처리가 진행됐다"에 가깝다.

대상 coroutine이 취소 신호를 받고 cleanup을 수행하면 `wait_for()`는 그 cleanup을 기다릴 수 있다. 그래서 관측상 `timeout=1.0`인데 실제 `await wait_for(...)`가 1초보다 오래 걸릴 수 있다.

예를 들어 아래 코드를 보자.

```python
async def slow_cleanup() -> None:
    try:
        await asyncio.sleep(10)
    finally:
        await asyncio.sleep(2)


await asyncio.wait_for(slow_cleanup(), timeout=1)
```

1초 뒤 취소가 발생하지만 `finally` 안의 2초 cleanup 때문에 호출자는 더 기다릴 수 있다. 이것은 버그라기보다 정상적인 취소 협력 모델이다.

### `wait_for()`가 적합한 곳

`wait_for()`는 특정 awaitable 하나에 상한을 줄 때 유용하다.

- 외부 API 호출 하나의 최대 대기 시간
- queue `get()`의 polling 상한
- lock 획득 시도 상한
- 테스트에서 특정 coroutine이 일정 시간 안에 끝나는지 검증

예:

```python
async def fetch_with_timeout(client: httpx.AsyncClient, url: str) -> dict:
    response = await asyncio.wait_for(client.get(url), timeout=1.5)
    response.raise_for_status()
    return response.json()
```

하지만 이 패턴에도 함정이 있다. HTTP client 자체에도 connect/read/write/pool timeout이 있는데, 바깥에서 또 `wait_for()`를 걸면 두 timeout의 의미가 겹친다. 운영에서는 가능하면 라이브러리의 세부 timeout을 먼저 쓰고, 전체 작업 deadline은 상위 레이어에서 관리하는 편이 낫다.

### `wait_for()` 남발의 문제

아래 코드는 겉으로는 안전해 보인다.

```python
async def build_dashboard(user_id: int) -> Dashboard:
    profile = await asyncio.wait_for(fetch_profile(user_id), timeout=1.0)
    orders = await asyncio.wait_for(fetch_orders(user_id), timeout=1.0)
    coupons = await asyncio.wait_for(fetch_coupons(user_id), timeout=1.0)
    return Dashboard(profile=profile, orders=orders, coupons=coupons)
```

각 호출에 1초 timeout이 있으니 안전할까? 실제로는 전체 요청이 3초 이상 걸릴 수 있다. 상위 API SLA가 1.5초라면 이미 틀렸다.

더 좋은 방식은 전체 deadline을 먼저 잡고, 하위 호출은 남은 시간 안에서 실행하는 것이다.

```python
import time


class Deadline:
    def __init__(self, seconds: float) -> None:
        self._expires_at = time.monotonic() + seconds

    def remaining(self) -> float:
        return max(0.0, self._expires_at - time.monotonic())

    def expired(self) -> bool:
        return self.remaining() <= 0


async def build_dashboard(user_id: int, deadline: Deadline) -> Dashboard:
    profile = await asyncio.wait_for(fetch_profile(user_id), timeout=deadline.remaining())
    orders = await asyncio.wait_for(fetch_orders(user_id), timeout=deadline.remaining())
    coupons = await asyncio.wait_for(fetch_coupons(user_id), timeout=deadline.remaining())
    return Dashboard(profile=profile, orders=orders, coupons=coupons)
```

이제 하위 작업이 상위 요청 예산을 넘어서지 않는다. 다만 `remaining()`이 0에 가까울 때 어떤 예외를 낼지, timeout을 어느 계층에서 사용자 응답으로 바꿀지 정해야 한다.

---

## 핵심 개념 3: `asyncio.timeout()`은 scope 단위 deadline을 코드에 더 잘 드러낸다

Python 3.11 이후에는 `asyncio.timeout()`을 사용할 수 있다.

```python
async with asyncio.timeout(1.5):
    profile = await fetch_profile(user_id)
    orders = await fetch_orders(user_id)
```

이 방식은 timeout을 특정 awaitable 하나가 아니라 **코드 블록 전체 scope**에 적용한다. 그래서 여러 await가 하나의 시간 예산을 공유한다는 의도가 더 잘 드러난다.

예를 들어 API 요청 처리에서는 아래처럼 쓸 수 있다.

```python
async def handle_request(user_id: int) -> Response:
    try:
        async with asyncio.timeout(1.2):
            profile = await fetch_profile(user_id)
            permissions = await fetch_permissions(user_id)
            summary = await build_summary(user_id, profile, permissions)
            return Response(summary=summary)
    except TimeoutError as exc:
        raise ServiceUnavailable("request deadline exceeded") from exc
```

이 코드는 `fetch_profile`, `fetch_permissions`, `build_summary` 각각에 독립 timeout을 둔 것이 아니다. 전체 요청 처리 블록이 1.2초 안에 끝나야 한다는 계약을 만든다.

### timeout scope를 어디에 둬야 하는가

timeout scope는 너무 안쪽에만 두면 전체 예산이 흩어진다. 너무 바깥에만 두면 어떤 하위 의존성이 느린지 분리하기 어렵다.

실무에서는 보통 두 층으로 나눈다.

1. **상위 deadline:** 요청, job, message 하나가 허용받은 전체 시간
2. **하위 세부 timeout:** 외부 API connect/read, DB statement, lock 획득, queue get처럼 리소스별 보호 시간

예:

```python
async def create_invoice(command: CreateInvoiceCommand) -> InvoiceResult:
    async with asyncio.timeout(2.0):
        customer = await customer_repo.get(command.customer_id)

        payment_result = await payment_gateway.authorize(
            command.payment_method_id,
            amount=command.amount,
            timeout=0.8,
        )

        invoice = await invoice_repo.create(command, payment_result)
        await outbox.append(invoice.created_event())
        return InvoiceResult(invoice_id=invoice.id)
```

여기서 `2.0`은 use case 전체 deadline이고, `0.8`은 결제 승인 외부 호출의 세부 예산이다. DB driver나 HTTP client에도 별도 timeout이 필요할 수 있다. 중요한 것은 숫자가 중첩될 때 어떤 숫자가 상위 계약이고 어떤 숫자가 리소스 보호인지 문서화하는 것이다.

### `asyncio.timeout()`도 취소를 사용한다

`asyncio.timeout()`은 내부적으로 현재 task를 취소하는 방식으로 timeout을 구현한다. 그래서 block 내부 coroutine들은 취소 신호를 받는다. block 바깥에서는 일반적으로 `TimeoutError`로 보이지만, 내부 cleanup과 취소 전파는 여전히 `CancelledError` 모델을 따른다.

따라서 아래 원칙은 그대로 적용된다.

- block 내부에서 `CancelledError`를 삼키지 않는다.
- cleanup이 필요한 자원은 `try/finally` 또는 async context manager로 닫는다.
- timeout이 발생한 뒤에도 외부 side effect가 이미 발생했을 가능성을 고려한다.

예를 들어 결제 승인 요청이 timeout되었다고 해서 결제가 절대 승인되지 않았다고 단정하면 안 된다. timeout은 "응답을 못 받았다"이지 "상대 시스템이 아무 일도 하지 않았다"가 아니다. 이때는 idempotency key, 조회 API, outbox, 보상 트랜잭션 같은 설계가 같이 필요하다.

---

## 핵심 개념 4: `TaskGroup`은 실패하면 sibling을 취소한다

`asyncio.gather()`는 오래전부터 병렬 await에 많이 쓰였다.

```python
profile, orders, coupons = await asyncio.gather(
    fetch_profile(user_id),
    fetch_orders(user_id),
    fetch_coupons(user_id),
)
```

단순 병렬 호출에는 여전히 쓸 수 있다. 하지만 운영 코드에서 중요한 것은 실패 모델이다.

`TaskGroup`은 구조화된 동시성을 제공한다. group 안에서 만든 task는 group scope 안에서 완료되어야 한다. child task 중 하나가 실패하면 나머지 sibling task는 취소되고, group은 예외를 모아 바깥으로 전달한다.

```python
async def load_home(user_id: int) -> HomeData:
    async with asyncio.TaskGroup() as tg:
        profile_task = tg.create_task(fetch_profile(user_id))
        orders_task = tg.create_task(fetch_orders(user_id))
        coupons_task = tg.create_task(fetch_coupons(user_id))

    return HomeData(
        profile=profile_task.result(),
        orders=orders_task.result(),
        coupons=coupons_task.result(),
    )
```

이 코드의 장점은 명확하다.

- 세 task의 생명주기가 `async with` block 안에 묶인다.
- 하나가 실패하면 나머지를 계속 돌릴지 고민하지 않고 취소한다.
- block을 벗어나면 모든 task가 완료되었거나 예외가 전파된다.
- fire-and-forget task가 숨어 남을 가능성이 줄어든다.

### 언제 `TaskGroup`이 특히 좋은가

`TaskGroup`은 child task들이 같은 상위 목적을 공유할 때 좋다.

- 한 HTTP 응답을 만들기 위해 여러 의존성을 병렬 조회한다.
- 한 메시지를 처리하기 위해 여러 독립 검증을 동시에 수행한다.
- 한 배치 step 안에서 shard별 작업을 병렬 실행한다.
- 여러 upstream 중 하나라도 실패하면 전체 결과를 실패로 처리해야 한다.

예를 들어 주문 생성 전에 재고, 고객, 쿠폰을 동시에 검증한다고 하자.

```python
async def validate_order(command: CreateOrderCommand) -> ValidationResult:
    async with asyncio.TaskGroup() as tg:
        stock_task = tg.create_task(check_stock(command.items))
        customer_task = tg.create_task(check_customer(command.customer_id))
        coupon_task = tg.create_task(check_coupon(command.coupon_code))

    return ValidationResult(
        stock=stock_task.result(),
        customer=customer_task.result(),
        coupon=coupon_task.result(),
    )
```

`check_stock()`이 실패하면 고객과 쿠폰 검증은 더 이상 의미 없을 수 있다. 이때 sibling cancellation은 자원 낭비를 줄이고, 실패를 빠르게 상위로 전달한다.

### 언제 `gather(return_exceptions=True)`가 더 위험한가

아래 패턴은 매우 조심해야 한다.

```python
results = await asyncio.gather(
    send_email(user),
    send_sms(user),
    send_push(user),
    return_exceptions=True,
)
```

`return_exceptions=True`는 예외를 던지지 않고 결과 리스트에 담는다. partial success를 처리해야 할 때 유용할 수 있지만, 실패를 값처럼 다루게 만들어 놓치기 쉽다.

나쁜 예:

```python
results = await asyncio.gather(*tasks, return_exceptions=True)
logger.info("notifications sent", extra={"count": len(results)})
```

이 코드는 실제로는 일부 알림이 실패했는데 성공처럼 기록할 수 있다. `return_exceptions=True`를 쓸 때는 반드시 결과를 분류해야 한다.

```python
results = await asyncio.gather(*tasks, return_exceptions=True)

failures = [item for item in results if isinstance(item, Exception)]
if failures:
    for failure in failures:
        logger.warning("notification failed", exc_info=failure)
    raise PartialNotificationFailure(failures)
```

실무 기준은 단순하다.

> partial failure를 명시적으로 모델링하지 않을 거라면 `return_exceptions=True`를 쉽게 쓰지 않는다.

### `TaskGroup`과 `ExceptionGroup`

`TaskGroup`에서 여러 task가 실패하면 Python은 `ExceptionGroup`을 사용할 수 있다. 병렬 실패를 하나의 예외로 묶는 모델이다.

```python
try:
    async with asyncio.TaskGroup() as tg:
        for item in items:
            tg.create_task(process_item(item))
except* ValidationError as group:
    for exc in group.exceptions:
        logger.info("validation failed", exc_info=exc)
except* TransientInfraError as group:
    for exc in group.exceptions:
        logger.warning("transient failure", exc_info=exc)
```

`except*`는 일반 `except`와 다르다. group 안에서 해당 타입에 맞는 예외들을 분리해 처리한다. 이 기능은 batch나 fan-out 작업에서 특히 유용하다.

하지만 모든 코드에 `ExceptionGroup`을 노출할 필요는 없다. 보통은 boundary에서 운영 의미로 번역한다.

```python
try:
    await process_batch(items)
except* TransientInfraError as group:
    raise BatchRetryableFailure(len(group.exceptions)) from group
except* DomainError as group:
    raise BatchRejectedFailure(len(group.exceptions)) from group
```

---

## 실무 예시 1: FastAPI 요청이 끊겼을 때 내부 작업도 멈춰야 하는가

FastAPI 같은 ASGI 애플리케이션에서는 요청 처리 coroutine이 취소될 수 있다. 클라이언트 연결이 끊기거나 서버 shutdown이 시작되거나 상위 middleware timeout이 발생하면 request scope 작업은 더 이상 정상 응답을 만들 수 없다.

예를 들어 아래 endpoint를 보자.

```python
@router.post("/reports")
async def create_report(request: CreateReportRequest) -> ReportResponse:
    report = await report_service.create_report(request.user_id, request.range)
    return ReportResponse.from_domain(report)
```

`create_report()`가 긴 작업이라면 클라이언트가 연결을 끊었을 때 어떻게 해야 할까?

정답은 업무 성격에 따라 다르다.

### 응답 생성용 조회라면 취소되어야 한다

대시보드 조회, 검색, 추천 계산처럼 응답을 만들기 위한 작업은 보통 요청이 취소되면 같이 취소되는 것이 맞다.

```python
async def get_dashboard(user_id: int) -> Dashboard:
    async with asyncio.timeout(1.5):
        async with asyncio.TaskGroup() as tg:
            profile = tg.create_task(load_profile(user_id))
            stats = tg.create_task(load_stats(user_id))
            alerts = tg.create_task(load_alerts(user_id))

    return Dashboard(
        profile=profile.result(),
        stats=stats.result(),
        alerts=alerts.result(),
    )
```

요청이 끝났는데 dashboard 계산이 계속 돌아 봐야 가치가 없다. 오히려 DB와 외부 API를 붙잡아 다음 요청을 방해한다.

### 반드시 완료되어야 하는 작업이라면 요청 task에서 분리해야 한다

반대로 결제 승인, 송장 발행, 이메일 발송, 대용량 리포트 생성처럼 요청 이후에도 완료되어야 하는 작업이 있다. 이때 단순히 `create_task()`로 분리하면 안 된다.

나쁜 예:

```python
@router.post("/reports")
async def create_report(request: CreateReportRequest) -> dict:
    asyncio.create_task(report_service.generate_report(request.user_id, request.range))
    return {"accepted": True}
```

이 코드는 서버 프로세스가 살아 있는 동안만 기대할 수 있고, 실패 관측과 재시도도 불명확하다.

더 좋은 방향은 durable queue나 outbox를 쓰는 것이다.

```python
@router.post("/reports", status_code=202)
async def create_report(request: CreateReportRequest) -> AcceptedResponse:
    job_id = await report_jobs.enqueue(
        user_id=request.user_id,
        date_range=request.range,
        idempotency_key=request.idempotency_key,
    )
    return AcceptedResponse(job_id=job_id)
```

이제 요청 task는 "작업을 등록했다"까지만 책임진다. 실제 생성 작업의 owner는 worker다. worker는 재시도, DLQ, 취소, shutdown, 관측을 별도로 가진다.

핵심은 이것이다.

> 요청 취소 후에도 계속되어야 하는 작업은 request task에서 `shield()`로 버티게 하지 말고, 별도 durable owner에게 넘겨라.

---

## 실무 예시 2: queue worker에서 취소는 ack 정책과 함께 설계해야 한다

비동기 worker는 취소 설계가 더 중요하다. worker는 대개 메시지를 하나 가져와 처리하고, 성공하면 ack, 실패하면 retry나 DLQ로 보낸다.

```python
async def worker() -> None:
    while True:
        message = await queue.receive()
        await handle(message)
        await queue.ack(message)
```

이 코드는 happy path만 있다. 취소가 중간에 들어오면 어떻게 될까?

- `handle(message)` 시작 전 취소
- `handle(message)` 중간 취소
- side effect 후 ack 전 취소
- ack 호출 중 취소

각 상태의 의미가 다르다. 특히 side effect 후 ack 전 취소는 중복 처리로 이어질 수 있다. 그래서 worker는 "처리 함수"만이 아니라 **메시지 상태 전이**를 함께 설계해야 한다.

예:

```python
async def run_worker() -> None:
    while True:
        message = await queue.receive()
        try:
            async with asyncio.timeout(30):
                await handle_message(message)
        except asyncio.CancelledError:
            logger.info("worker cancelled", extra={"message_id": message.id})
            raise
        except TransientInfraError as exc:
            await queue.retry(message, reason=str(exc))
        except DomainError as exc:
            await queue.dead_letter(message, reason=str(exc))
        except Exception as exc:
            await queue.retry(message, reason="unexpected")
            logger.exception("unexpected message failure", exc_info=exc)
        else:
            await queue.ack(message)
```

이 구조는 여전히 완벽하지 않다. `queue.retry()`, `dead_letter()`, `ack()` 자체도 취소될 수 있기 때문이다. 메시지 시스템에 따라 visibility timeout이 있으면 ack를 못 한 메시지는 나중에 다시 보일 수 있다. 이때 idempotency가 없으면 중복 side effect가 난다.

### idempotency가 취소 설계의 일부인 이유

취소는 언제든 들어올 수 있다. timeout도 언제든 발생할 수 있다. 네트워크 응답이 끊겼다고 외부 시스템이 일을 안 했다고 보장할 수도 없다.

따라서 worker의 핵심 side effect는 idempotent해야 한다.

예를 들어 결제 캡처 메시지를 처리한다면:

- 메시지마다 `operation_id`를 둔다.
- DB에 operation 처리 상태를 먼저 기록한다.
- 외부 결제 API에는 idempotency key를 전달한다.
- timeout 후 재시도 시 같은 key로 결과를 조회하거나 재요청한다.
- 최종 상태 전이는 compare-and-set 또는 unique constraint로 보호한다.

```python
async def capture_payment(message: PaymentCaptureMessage) -> None:
    operation = await operations.start_once(message.operation_id)
    if operation.already_completed:
        return

    result = await payment_gateway.capture(
        payment_id=message.payment_id,
        amount=message.amount,
        idempotency_key=message.operation_id,
    )

    await operations.mark_completed(message.operation_id, result.transaction_id)
```

이 구조에서는 취소 후 같은 메시지가 재전달되어도 중복 결제 가능성을 줄일 수 있다.

---

## 핵심 개념 5: `shield()`는 cleanup 보호용이지 취소 회피용이 아니다

`asyncio.shield()`는 바깥 task가 취소되어도 안쪽 awaitable이 바로 취소되지 않도록 보호한다.

```python
await asyncio.shield(commit_offsets())
```

이름 때문에 강력해 보이지만, 운영 코드에서 가장 남용하기 쉬운 도구 중 하나다.

### `shield()`가 유용한 경우

`shield()`는 보통 짧고 중요한 cleanup에 제한적으로 쓴다.

- DB rollback 또는 connection 반환
- 메시지 ack/nack 기록
- 분산 락 해제
- 임시 파일 삭제
- outbox flush처럼 이미 시작한 상태 전이를 마무리해야 하는 작업

예:

```python
async def process_with_lock(lock: AsyncLock, item: Item) -> None:
    await lock.acquire(item.key)
    try:
        await process(item)
    finally:
        try:
            async with asyncio.timeout(2):
                await asyncio.shield(lock.release(item.key))
        except Exception:
            logger.exception("failed to release lock", extra={"key": item.key})
```

여기서 `shield()`는 전체 `process(item)`을 보호하지 않는다. lock release만 좁게 보호한다. 그리고 release도 무한정 기다리지 않고 별도 timeout을 둔다.

### `shield()`가 위험한 경우

나쁜 예:

```python
async def handle_request(command: Command) -> Result:
    return await asyncio.shield(do_everything(command))
```

이 코드는 요청이 취소되어도 내부 작업을 계속 진행시키려 한다. 그러면 상위 레이어의 timeout과 shutdown 정책이 무력화된다. 외부에서는 취소되었다고 생각하지만 내부에서는 DB, HTTP client, worker slot을 계속 붙잡는다.

`shield()`로 비즈니스 작업 전체를 감싸고 싶어지는 순간에는 보통 설계를 다시 봐야 한다.

- 정말 요청이 끊겨도 완료되어야 하는가?
- 그렇다면 durable queue로 넘겨야 하는가?
- 이미 시작한 side effect를 보상할 수 있는가?
- cleanup만 보호하면 충분하지 않은가?

실무 규칙은 이렇게 잡을 수 있다.

> `shield()`는 "이 작업은 취소되면 안 된다"가 아니라 "이미 시작한 정리 작업만 짧게 끝내겠다"에 가깝게 써라.

---

## 실무 예시 3: graceful shutdown은 취소 폭풍을 순서 있는 종료로 바꾸는 일이다

서버나 worker 프로세스는 언젠가 종료된다. 배포, scale down, 노드 재시작, 장애 복구, 수동 종료가 모두 shutdown 경로다.

비동기 애플리케이션에서 shutdown은 보통 다음 순서로 설계한다.

1. 새 작업 수신을 멈춘다.
2. 이미 받은 작업을 일정 시간 기다린다.
3. deadline이 지나면 남은 task를 취소한다.
4. cleanup을 제한된 시간 안에 수행한다.
5. 완료되지 않은 작업은 재처리 가능한 상태로 남긴다.

예:

```python
class WorkerRuntime:
    def __init__(self, queue: MessageQueue, concurrency: int) -> None:
        self._queue = queue
        self._concurrency = concurrency
        self._stopping = asyncio.Event()
        self._tasks: set[asyncio.Task[None]] = set()

    async def start(self) -> None:
        for index in range(self._concurrency):
            task = asyncio.create_task(self._worker(index))
            self._tasks.add(task)

    async def stop(self, timeout: float = 20.0) -> None:
        self._stopping.set()

        try:
            async with asyncio.timeout(timeout):
                await asyncio.gather(*self._tasks)
        except TimeoutError:
            for task in self._tasks:
                task.cancel()
            await asyncio.gather(*self._tasks, return_exceptions=True)

    async def _worker(self, index: int) -> None:
        while not self._stopping.is_set():
            try:
                message = await asyncio.wait_for(self._queue.receive(), timeout=1.0)
            except TimeoutError:
                continue

            await self._handle_one(index, message)
```

이 예시는 단순화되어 있지만 핵심 흐름을 보여 준다. shutdown은 무조건 `task.cancel()`부터 하는 것이 아니다. 새 메시지를 더 받지 않게 하고, 진행 중 작업에 grace period를 준 뒤, 그래도 안 끝나면 취소한다.

### shutdown에서 피해야 할 패턴

가장 흔한 실수는 아래다.

```python
for task in tasks:
    task.cancel()
```

그리고 끝이다. 이러면 취소가 실제로 처리되었는지 모른다. `cancel()`은 요청일 뿐이다. 반드시 task들을 await해서 취소 처리가 완료되도록 해야 한다.

```python
for task in tasks:
    task.cancel()

await asyncio.gather(*tasks, return_exceptions=True)
```

또 다른 실수는 shutdown cleanup에 무한 대기를 허용하는 것이다.

```python
await queue.flush()
await metrics.flush()
await db.close()
```

각 cleanup은 제한된 시간 안에 끝나야 한다. 종료 과정에서 네트워크가 이미 불안정할 수 있기 때문이다.

```python
async with asyncio.timeout(5):
    await queue.flush()

async with asyncio.timeout(2):
    await metrics.flush()

async with asyncio.timeout(5):
    await db.close()
```

실무에서는 종료 예산 전체도 필요하다. Kubernetes `terminationGracePeriodSeconds`가 30초인데 내부 cleanup 합계가 60초라면 설계가 맞지 않는다.

---

## 핵심 개념 6: cancellation point가 없는 CPU 작업은 취소되지 않는다

`asyncio` 취소는 협력적이다. task가 취소 요청을 받아도 Python 코드가 계속 CPU를 붙잡고 `await` 지점으로 돌아오지 않으면 취소가 처리되지 않는다.

나쁜 예:

```python
async def render_large_report(rows: list[Row]) -> bytes:
    buffer = io.BytesIO()
    for row in rows:
        render_row(buffer, row)
    return buffer.getvalue()
```

이 함수는 `async`로 선언되어 있지만 내부에 `await`가 없다. 실제로는 event loop를 오래 점유할 수 있다. 취소도 중간에 처리되지 않는다.

큰 CPU 작업은 별도 executor나 worker process로 분리하는 편이 낫다.

```python
async def render_large_report(rows: list[Row]) -> bytes:
    return await asyncio.to_thread(render_report_sync, rows)
```

다만 `to_thread()`도 완전한 강제 취소가 아니다. await하는 coroutine은 취소될 수 있지만, 이미 시작한 thread 작업은 Python 레벨에서 즉시 중단되지 않을 수 있다. 따라서 CPU 작업은 chunking, 별도 프로세스, job 상태 체크, 중단 플래그 같은 전략이 필요하다.

chunking을 할 수 있다면 cancellation point를 의도적으로 둔다.

```python
async def transform_rows(rows: list[Row]) -> list[OutputRow]:
    output: list[OutputRow] = []
    for index, row in enumerate(rows):
        output.append(transform(row))
        if index % 1000 == 0:
            await asyncio.sleep(0)
    return output
```

`await asyncio.sleep(0)`은 event loop에 제어권을 돌려준다. 남발할 필요는 없지만, 긴 loop에서는 취소와 다른 task 실행 기회를 준다.

---

## 실무 예시 4: 외부 API timeout은 client timeout과 요청 deadline을 같이 봐야 한다

HTTP client를 예로 들어 보자. `httpx.AsyncClient`는 connect, read, write, pool timeout을 따로 둘 수 있다.

```python
timeout = httpx.Timeout(
    connect=0.3,
    read=1.0,
    write=0.5,
    pool=0.2,
)
client = httpx.AsyncClient(timeout=timeout)
```

이 설정은 리소스별 보호에 좋다. 하지만 상위 요청 deadline과 별개로 움직이면 문제가 생긴다.

예를 들어 API 전체 deadline이 1.2초인데 외부 API read timeout이 3초라면, 상위 deadline이 먼저 터질 것이다. 이때 HTTP client 내부 요청은 취소되어야 하고 connection은 pool에 안전하게 반환되어야 한다. 대부분의 잘 만들어진 async client는 이를 처리하지만, retry wrapper나 custom transport를 쓰면 검증이 필요하다.

더 나은 구조는 전체 deadline을 인자로 전달하고 하위 client가 남은 예산을 반영하도록 하는 것이다.

```python
async def call_partner(
    client: httpx.AsyncClient,
    payload: dict,
    deadline: Deadline,
) -> PartnerResponse:
    remaining = deadline.remaining()
    if remaining <= 0.05:
        raise TimeoutError("no budget left for partner call")

    timeout = httpx.Timeout(
        connect=min(0.2, remaining),
        read=min(0.8, remaining),
        write=min(0.3, remaining),
        pool=min(0.1, remaining),
    )

    response = await client.post("/partner/orders", json=payload, timeout=timeout)
    response.raise_for_status()
    return PartnerResponse.model_validate(response.json())
```

여기서 중요한 것은 모든 숫자를 동적으로 만들라는 뜻이 아니다. 핵심은 상위 deadline보다 긴 하위 timeout이 숨어 있지 않게 하는 것이다.

### retry와 timeout의 곱셈을 조심하라

timeout 1초에 retry 3회를 붙이면 최악의 경우 3초 이상 걸린다. backoff까지 있으면 더 길다.

```python
async def fetch_with_retry() -> dict:
    for attempt in range(3):
        try:
            return await asyncio.wait_for(fetch(), timeout=1.0)
        except TimeoutError:
            if attempt == 2:
                raise
            await asyncio.sleep(0.2 * (attempt + 1))
```

이 코드는 호출자가 기대한 전체 deadline을 쉽게 넘긴다. retry loop도 deadline을 알아야 한다.

```python
async def fetch_with_retry(deadline: Deadline) -> dict:
    for attempt in range(3):
        if deadline.remaining() <= 0.1:
            raise TimeoutError("retry budget exhausted")

        try:
            return await asyncio.wait_for(fetch(), timeout=min(1.0, deadline.remaining()))
        except TimeoutError:
            if attempt == 2:
                raise
            sleep_for = min(0.2 * (attempt + 1), deadline.remaining())
            await asyncio.sleep(sleep_for)

    raise AssertionError("unreachable")
```

retry는 성공률을 올리기도 하지만, 장애 시 부하를 증폭시키기도 한다. 그래서 timeout, retry, idempotency, rate limit, circuit breaker는 함께 설계해야 한다.

---

## 흔한 실수 1: `create_task()`를 쓰고 task reference를 버린다

가장 위험한 패턴이다.

```python
asyncio.create_task(refresh_cache())
```

이 task가 실패하면 누가 알까? 서버 종료 시 누가 기다릴까? contextvars는 기대한 대로 이어질까? 같은 작업이 여러 번 겹치면 누가 제한할까?

필요하면 supervisor를 둔다.

```python
class TaskSupervisor:
    def __init__(self) -> None:
        self._tasks: set[asyncio.Task[None]] = set()

    def start(self, coro: Awaitable[None]) -> None:
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._on_done)

    def _on_done(self, task: asyncio.Task[None]) -> None:
        self._tasks.discard(task)
        try:
            task.result()
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("background task failed")

    async def stop(self, timeout: float = 10.0) -> None:
        for task in self._tasks:
            task.cancel()

        async with asyncio.timeout(timeout):
            await asyncio.gather(*self._tasks, return_exceptions=True)
```

이 supervisor도 완전한 durable worker는 아니다. 프로세스가 죽으면 task는 사라진다. 하지만 최소한 프로세스 안에서 owner가 명확해진다.

---

## 흔한 실수 2: 취소를 에러 로그로 과도하게 남긴다

취소는 정상적인 제어 흐름일 수 있다. 클라이언트가 브라우저 탭을 닫거나, 배포 때문에 shutdown이 시작되거나, 상위 deadline이 끝난 상황은 모두 정상적으로 발생한다.

따라서 모든 `CancelledError`를 error level로 남기면 로그가 오염된다.

추천 기준은 아래와 같다.

- 사용자 요청 취소: 보통 debug 또는 info, 필요 시 샘플링
- shutdown 취소: info
- 내부 timeout으로 인한 취소: warning 가능, 운영 지표와 연결
- cleanup 실패: warning 또는 error
- 취소를 삼켜서 shutdown 실패: error

즉 취소 자체보다 **취소 후 정리가 실패했는가**가 더 중요한 알림 기준이다.

---

## 흔한 실수 3: timeout 예외를 모두 같은 500으로 매핑한다

timeout은 종류별로 의미가 다르다.

- 사용자 요청 deadline 초과
- 외부 API connect timeout
- 외부 API read timeout
- DB statement timeout
- lock 획득 timeout
- queue ack timeout
- shutdown cleanup timeout

모두 `TimeoutError` 하나로 뭉개면 운영자가 원인을 볼 수 없다.

서비스 예외로 번역할 때는 운영 의미를 붙인다.

```python
class RequestDeadlineExceeded(AppError):
    pass


class PartnerTimeout(TransientInfraError):
    pass


class LockAcquireTimeout(ConcurrencyConflict):
    pass
```

그리고 metric label도 구분한다.

```python
metrics.increment(
    "operation_timeout_total",
    tags={
        "operation": "create_invoice",
        "timeout_type": "partner_read",
        "retryable": "true",
    },
)
```

중요한 것은 예외 클래스가 많아지는 게 아니다. timeout이 발생했을 때 어떤 행동을 해야 하는지 구분하는 것이다.

---

## 흔한 실수 4: cleanup에 `await`가 있다는 사실을 잊는다

`finally`는 반드시 실행된다고 배운다. 하지만 비동기 코드에서는 `finally` 안의 `await`도 취소될 수 있다.

```python
try:
    await process()
finally:
    await cleanup()
```

`cleanup()`이 오래 걸리거나 또 다른 cancellation point를 포함하면 cleanup이 중간에 멈출 수 있다. 그래서 중요한 cleanup은 아래처럼 별도 정책을 둔다.

```python
try:
    await process()
finally:
    try:
        async with asyncio.timeout(3):
            await asyncio.shield(cleanup())
    except Exception:
        logger.exception("cleanup failed")
```

이 패턴도 무조건 쓰라는 뜻은 아니다. cleanup마다 비용과 필요성이 다르다.

- memory object 정리: 그냥 동기적으로 정리
- DB connection 반환: context manager와 pool 동작 신뢰, 필요 시 짧은 timeout
- distributed lock 해제: shield + timeout + 실패 알림
- 메시지 ack: broker visibility timeout과 idempotency로 보완
- metrics flush: 짧게 시도하고 실패해도 종료

cleanup을 설계할 때 질문은 하나다.

> 이 cleanup이 실패하면 어떤 상태가 남고, 그 상태는 자동 회복되는가?

---

## 흔한 실수 5: timeout만 있고 backpressure가 없다

timeout은 작업을 끝내는 장치고, backpressure는 작업이 너무 많이 들어오지 않게 하는 장치다. 둘은 대체재가 아니다.

아래 코드는 timeout이 있어도 위험하다.

```python
tasks = [
    asyncio.create_task(asyncio.wait_for(process(item), timeout=2))
    for item in items
]
await asyncio.gather(*tasks)
```

`items`가 10만 개면 task 10만 개가 한 번에 만들어진다. timeout이 있어도 memory와 connection pool이 먼저 무너질 수 있다.

동시성 제한이 필요하다.

```python
async def process_many(items: list[Item], concurrency: int) -> None:
    semaphore = asyncio.Semaphore(concurrency)

    async def run_one(item: Item) -> None:
        async with semaphore:
            async with asyncio.timeout(2):
                await process(item)

    async with asyncio.TaskGroup() as tg:
        for item in items:
            tg.create_task(run_one(item))
```

이 방식도 `items`가 너무 크면 task 생성 수가 많아질 수 있다. 더 큰 배치에서는 bounded queue와 worker pool이 낫다.

```python
async def process_stream(items: AsyncIterator[Item], concurrency: int) -> None:
    queue: asyncio.Queue[Item | None] = asyncio.Queue(maxsize=concurrency * 2)

    async def producer() -> None:
        async for item in items:
            await queue.put(item)
        for _ in range(concurrency):
            await queue.put(None)

    async def worker() -> None:
        while True:
            item = await queue.get()
            try:
                if item is None:
                    return
                async with asyncio.timeout(2):
                    await process(item)
            finally:
                queue.task_done()

    async with asyncio.TaskGroup() as tg:
        tg.create_task(producer())
        for _ in range(concurrency):
            tg.create_task(worker())
```

---

## 테스트 전략: 취소는 happy path 테스트로 절대 잡히지 않는다

취소와 timeout은 의도적으로 테스트해야 한다. 그렇지 않으면 운영 shutdown이나 느린 외부 의존성에서 처음 발견된다.

### 1) timeout 발생 시 자원이 정리되는지 테스트

```python
async def test_lock_released_on_timeout(fake_lock: FakeLock) -> None:
    async def slow_process() -> None:
        await fake_lock.acquire("order-1")
        try:
            await asyncio.sleep(10)
        finally:
            await fake_lock.release("order-1")

    with pytest.raises(TimeoutError):
        async with asyncio.timeout(0.01):
            await slow_process()

    assert fake_lock.is_released("order-1")
```

### 2) worker 취소 시 task가 실제로 끝나는지 테스트

```python
async def test_worker_stops_on_cancel(queue: FakeQueue) -> None:
    task = asyncio.create_task(run_worker(queue))
    await asyncio.sleep(0)

    task.cancel()
    result = await asyncio.gather(task, return_exceptions=True)

    assert isinstance(result[0], asyncio.CancelledError)
```

### 3) `CancelledError`를 삼키지 않는지 테스트

```python
async def test_handler_propagates_cancellation() -> None:
    async def handler() -> None:
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            raise

    task = asyncio.create_task(handler())
    await asyncio.sleep(0)
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task
```

### 4) partial failure를 명시적으로 검증

`TaskGroup`이나 `gather(return_exceptions=True)`를 쓰는 코드에서는 일부 task 실패 시 기대 동작을 테스트해야 한다.

- 나머지 task가 취소되는가?
- 이미 성공한 결과는 버리는가, partial result로 반환하는가?
- 실패 종류별로 retry 여부가 달라지는가?
- `ExceptionGroup`이 boundary에서 서비스 예외로 번역되는가?

이 테스트가 없으면 병렬 작업은 happy path에서만 좋아 보인다.

---

## 운영 관측성: 취소와 timeout은 지표로 분리해야 한다

비동기 시스템에서 필요한 지표는 단순 latency와 error count보다 조금 더 구체적이어야 한다.

추천 지표는 아래와 같다.

| 지표 | 의미 | 예시 label |
| --- | --- | --- |
| task_created_total | task 생성 수 | owner, operation |
| task_cancelled_total | 취소된 task 수 | reason, operation |
| task_timeout_total | timeout으로 실패한 task 수 | timeout_type, operation |
| task_cleanup_failed_total | cleanup 실패 수 | resource, operation |
| task_inflight | 현재 실행 중 task 수 | owner, operation |
| queue_depth | 대기 중 메시지 수 | queue_name |
| queue_ack_failed_total | ack/nack 실패 수 | queue_name, reason |
| deadline_remaining_ms | 하위 호출 시작 시 남은 예산 | operation, dependency |

로그에는 적어도 다음 문맥이 있어야 한다.

- request id / trace id
- task owner
- operation name
- deadline 또는 timeout 값
- 남은 시간
- 취소 이유
- cleanup 성공 여부
- idempotency key 또는 message id

특히 "취소 이유"는 중요하다.

- client disconnected
- request deadline exceeded
- server shutdown
- parent task failed
- sibling task failed
- manual cancel

모두 같은 cancellation이지만 운영 대응은 다르다.

---

## 트레이드오프: 취소를 빠르게 할수록 정리는 어려워지고, 정리를 오래 보장할수록 종료는 느려진다

취소와 timeout 설계에는 정답 숫자가 없다. 항상 trade-off가 있다.

### 짧은 timeout의 장점

- 장애 전파가 빠르게 끊긴다.
- 자원 점유 시간이 줄어든다.
- 사용자는 실패를 빨리 받는다.
- retry나 fallback으로 전환하기 쉽다.

### 짧은 timeout의 단점

- 정상적인 tail latency도 실패로 분류될 수 있다.
- cleanup과 보상 작업이 자주 필요해진다.
- retry가 붙으면 오히려 부하를 키울 수 있다.
- 외부 시스템에는 성공했는데 내부는 timeout으로 보는 애매한 상태가 늘 수 있다.

### 긴 timeout의 장점

- 느린 의존성이 일시적으로 흔들려도 성공 가능성이 있다.
- 큰 작업이나 cold start, cache miss를 견딜 수 있다.
- false timeout이 줄어든다.

### 긴 timeout의 단점

- connection, worker, memory를 오래 붙잡는다.
- shutdown이 늦어진다.
- 상위 호출자는 이미 포기했는데 하위 작업이 계속될 수 있다.
- 장애 감지가 늦고 retry 폭주가 뒤늦게 겹친다.

그래서 실무에서는 하나의 timeout 값보다 workload class가 중요하다.

| workload | timeout 방향 | 취소 정책 |
| --- | --- | --- |
| 사용자 조회 API | 짧고 명확한 deadline | 요청 취소 시 하위 작업도 취소 |
| 결제/주문 mutation | 짧은 외부 timeout + idempotency | 결과 불명확 상태를 조회/보정 |
| 백그라운드 worker | 메시지별 처리 상한 | 취소 시 재전달/재시도 가능하게 |
| 배치 | chunk별 상한 | 중간 상태 저장 후 resume |
| shutdown cleanup | 매우 짧은 상한 | 실패 알림과 자동 회복 경로 |

---

## 실전 설계 패턴: deadline context를 명시적으로 전달하라

작은 코드에서는 `asyncio.timeout()` block만으로 충분하다. 하지만 서비스가 커지면 하위 함수들이 남은 시간 예산을 알아야 한다.

이때 간단한 `Deadline` 객체를 명시적으로 전달하는 방식이 의외로 오래 간다.

```python
from dataclasses import dataclass
import time


@dataclass(frozen=True)
class Deadline:
    expires_at: float

    @classmethod
    def after(cls, seconds: float) -> "Deadline":
        return cls(expires_at=time.monotonic() + seconds)

    def remaining(self) -> float:
        return max(0.0, self.expires_at - time.monotonic())

    def ensure_budget(self, minimum: float = 0.05) -> None:
        if self.remaining() < minimum:
            raise TimeoutError("deadline budget exhausted")
```

사용:

```python
async def handle_checkout(command: CheckoutCommand) -> CheckoutResult:
    deadline = Deadline.after(2.0)
    async with asyncio.timeout(deadline.remaining()):
        return await checkout_service.checkout(command, deadline)


async def checkout(command: CheckoutCommand, deadline: Deadline) -> CheckoutResult:
    deadline.ensure_budget()
    cart = await cart_repo.get(command.cart_id, timeout=min(0.3, deadline.remaining()))

    deadline.ensure_budget()
    payment = await payment_gateway.authorize(
        cart.total_amount,
        idempotency_key=command.idempotency_key,
        timeout=min(0.8, deadline.remaining()),
    )

    deadline.ensure_budget()
    order = await order_repo.create(cart, payment, timeout=min(0.4, deadline.remaining()))
    return CheckoutResult(order_id=order.id)
```

이 패턴의 장점은 숫자가 숨어 있지 않다는 것이다. 상위 요청의 전체 예산과 하위 dependency의 예산이 같은 코드 경로에서 보인다.

단점도 있다.

- 함수 시그니처가 길어진다.
- 모든 하위 라이브러리가 deadline을 직접 이해하지는 않는다.
- 너무 엄격히 적용하면 테스트가 번거로워진다.

그래도 중대 경로에서는 가치가 크다. 특히 결제, 주문, 메시지 처리, 외부 API fan-out처럼 timeout이 정합성과 연결되는 경로에서는 명시적인 deadline이 운영 사고를 줄인다.

---

## 실전 체크리스트

비동기 코드 리뷰에서 아래 항목을 점검하면 취소 관련 장애를 많이 줄일 수 있다.

### task ownership

- [ ] `create_task()`를 호출한 코드가 task reference를 보관하거나 supervisor에 등록하는가
- [ ] task 실패가 로그와 메트릭으로 관측되는가
- [ ] shutdown 시 task를 취소하고 await하는가
- [ ] fire-and-forget이 durable queue로 대체되어야 하는 작업은 아닌가

### cancellation propagation

- [ ] `except Exception` 주변에서 `CancelledError`를 삼키지 않는가
- [ ] 취소를 잡은 뒤 cleanup 후 다시 `raise`하는가
- [ ] `finally` 안의 `await`가 취소될 수 있다는 점을 고려했는가
- [ ] CPU loop에 cancellation point가 있는가, 아니면 executor/worker로 분리했는가

### timeout and deadline

- [ ] 함수별 timeout이 전체 요청 deadline을 넘지 않는가
- [ ] retry 횟수와 backoff까지 포함해 전체 예산을 계산했는가
- [ ] HTTP client, DB driver, queue client의 내부 timeout과 상위 deadline이 충돌하지 않는가
- [ ] timeout 종류별로 예외와 metric label이 분리되어 있는가

### structured concurrency

- [ ] 같은 목적의 병렬 작업은 `TaskGroup`으로 scope가 닫혀 있는가
- [ ] child task 하나가 실패했을 때 sibling을 계속 실행할지 취소할지 정책이 명확한가
- [ ] `gather(return_exceptions=True)`를 쓴다면 partial failure 처리가 명시되어 있는가
- [ ] `ExceptionGroup`이 boundary에서 운영 의미로 번역되는가

### cleanup and shield

- [ ] `shield()`가 비즈니스 작업 전체가 아니라 짧은 cleanup에만 쓰이는가
- [ ] shielded cleanup에도 별도 timeout이 있는가
- [ ] cleanup 실패 시 남는 상태와 회복 경로가 정의되어 있는가
- [ ] lock, transaction, ack, temp file, connection 반환 경로가 테스트되어 있는가

### worker and side effects

- [ ] message 처리 중 취소 시 ack/nack/retry/DLQ 정책이 명확한가
- [ ] side effect는 idempotency key나 unique constraint로 보호되는가
- [ ] timeout 후 결과 불명확 상태를 조회하거나 보정하는 경로가 있는가
- [ ] shutdown grace period와 message visibility timeout이 맞는가

---

## 한줄정리

`asyncio` 취소와 타임아웃의 핵심은 작업을 빨리 포기하는 기술이 아니라, **포기하는 순간에도 task owner, 자원 cleanup, side effect, 재시도 기준이 예측 가능하게 남도록 작업 생명주기를 설계하는 것**이다.
