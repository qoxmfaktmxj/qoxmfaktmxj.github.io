---
layout: post
title: "Python contextvars 실전: 구조화 로그, Request Scope, Async 경계에서 컨텍스트를 잃지 않는 법"
date: 2026-04-08 11:40:00 +0900
categories: [python]
tags: [study, python, contextvars, structured-logging, observability, fastapi, asyncio, tracing, architecture]
permalink: /python/2026/04/08/study-python-contextvars-structured-logging-request-scope.html
---

## 왜 이 주제가 실무에서 중요할까?

서비스가 커질수록 장애를 고치는 시간보다, **어디서 무엇이 일어났는지 추적하는 시간**이 더 길어진다.

특히 Python 백엔드나 배치 파이프라인에서 아래 장면은 정말 자주 나온다.

- 같은 시각에 여러 요청이 섞여 로그를 보면 누가 누구 로그인지 구분이 안 된다
- `request_id`, `user_id`, `tenant_id`를 함수 인자로 계속 넘기다 보니 시그니처가 오염된다
- async 코드로 옮긴 뒤 `threading.local()` 기반 MDC 비슷한 패턴이 조용히 깨진다
- `create_task()`로 분리한 하위 작업에서는 상위 요청 컨텍스트가 사라진다
- 구조화 로그는 넣었는데 필드가 일부 로그에는 있고 일부 로그에는 없다
- trace id는 있는데 애플리케이션 로그, DB 로그, 외부 API 로그를 같은 흐름으로 묶지 못한다

이 문제는 로깅 라이브러리 선택의 문제가 아니다. 본질은 **컨텍스트를 어떤 경계 단위에서 생성하고, 어떻게 전파하며, 언제 반드시 정리할 것인가**의 문제다.

Python에서 이 문제를 가장 실용적으로 푸는 도구가 `contextvars`다. 다만 많은 팀이 이걸 "비동기에서 thread local 대신 쓰는 것" 정도로만 이해한다. 실무에서는 그보다 훨씬 넓게 봐야 한다.

> `contextvars`의 핵심 가치는 편한 전역 상태가 아니라, **동시성 환경에서도 요청 단위 맥락을 오염 없이 전달하는 것**이다.

오늘 글은 아래 질문에 답하는 데 초점을 둔다.

1. 왜 전역 변수나 `threading.local()`이 async 환경에서 무너지기 쉬운가
2. `ContextVar`는 정확히 어떤 범위에서 값을 보장하고, 어디서 끊기는가
3. 구조화 로그와 request scope를 어떻게 결합해야 운영에서 진짜 도움이 되는가
4. FastAPI 같은 ASGI 서버에서 어떤 패턴이 실전 기본값이 되어야 하는가
5. `create_task()`, `TaskGroup`, thread pool, background job 경계에서 무엇을 명시적으로 넘겨야 하는가
6. 흔한 실수와 운영 체크리스트는 무엇인가

핵심만 먼저 요약하면 이렇다.

- `contextvars`는 **동시 실행 단위별 문맥 격리**를 위한 도구다
- 편의성 때문에 무분별하게 쓰면 숨은 전역 상태가 되지만, 제대로 쓰면 **관측 가능성**이 크게 좋아진다
- 진짜 중요한 건 `ContextVar` API보다 **컨텍스트 생성 지점, reset 규칙, 경계 통과 전략**이다
- request id 하나만 넣는 수준에서 끝내지 말고, **로그/메트릭/트레이싱 키를 같은 기준으로 정렬**해야 효과가 난다

---

## 배경: 왜 로그는 남아 있는데도 디버깅은 계속 어려울까?

많은 시스템이 이미 로그를 남긴다. 그런데도 장애가 터지면 로그를 보는 시간이 여전히 길다. 이유는 단순하다. 로그가 부족해서라기보다 **연결이 안 되어 있기 때문**이다.

예를 들어 주문 생성 API가 있다고 하자.

- API 서버가 인증 정보를 읽는다
- 주문 서비스가 재고를 확인한다
- 결제 API를 호출한다
- 이벤트를 발행한다
- 비동기 후속 작업이 알림을 보낸다

여기서 장애가 나면 운영자는 최소한 아래 질문에 답해야 한다.

- 이 로그가 어떤 요청에서 시작됐는가
- 어떤 사용자, 어떤 테넌트, 어떤 주문 번호인가
- 같은 요청 안에서 어떤 하위 작업이 파생됐는가
- 실패 직전 마지막으로 성공한 외부 호출은 무엇인가
- 재시도된 로그와 최초 로그를 어떻게 구분할 것인가

문제는 이런 맥락 정보가 함수마다, 레이어마다, 로그마다 제각각이라는 점이다.

### 안티패턴 1: 함수 인자로 모든 메타데이터를 밀어 넣기

```python
async def create_order(
    request_id: str,
    user_id: str,
    tenant_id: str,
    correlation_id: str,
    payload: dict,
) -> dict:
    ...
```

처음에는 명시적이라 좋아 보인다. 하지만 계층이 깊어질수록 비즈니스 인자보다 관측용 인자가 더 많아진다.

- 실제 비즈니스 계약과 관측 메타데이터가 섞인다
- 함수가 재사용될수록 시그니처가 오염된다
- 로그가 필요 없는 하위 함수에도 같은 인자를 계속 전달해야 한다
- 중간에 하나라도 빠지면 로그 상관관계가 깨진다

### 안티패턴 2: 전역 변수 또는 모듈 상태 사용

```python
current_request_id = None
```

단일 스레드 실험 코드에서는 될 수 있어도 동시 요청이 들어오면 바로 오염된다. 요청 A가 값을 쓰는 동안 요청 B가 덮어쓰면 로그는 섞인다.

### 안티패턴 3: `threading.local()`을 async 환경에서도 그대로 사용

WSGI 중심 코드에서는 `threading.local()`이 어느 정도 먹혔다. 요청 하나가 스레드 하나에 묶이는 구조에서는 thread-local이 request-local처럼 보였기 때문이다.

하지만 asyncio 기반 ASGI 환경에서는 **한 스레드에서 여러 coroutine이 번갈아 실행**된다. 즉 스레드 경계와 요청 경계가 더 이상 같지 않다.

그래서 실무 질문은 이렇게 바뀐다.

> 요청이나 작업의 문맥을, 스레드가 아니라 **실행 컨텍스트 단위로 격리**할 수 있는가?

`contextvars`는 바로 이 문제를 푸는 표준 도구다.

---

## 먼저 큰 그림: `contextvars`는 "전역처럼 읽지만 실행 단위별로 분리되는 상태"다

가장 위험한 오해는 `ContextVar`를 "편한 숨은 파라미터" 정도로만 보는 것이다. 그렇게 쓰면 장점보다 부작용이 크다. 먼저 모델을 정확히 잡아야 한다.

### `ContextVar`가 제공하는 것

- 현재 실행 컨텍스트에서 값을 읽고 쓸 수 있다
- 다른 동시 실행 흐름과 값이 섞이지 않게 격리한다
- async task 생성 시 현재 컨텍스트를 이어받을 수 있다
- token 기반 reset으로 이전 상태 복원이 가능하다

### `ContextVar`가 제공하지 않는 것

- 프로세스 간 자동 전파
- 큐, 메시지 브로커, Celery, Kafka consumer 같은 외부 경계 전파
- thread pool/worker pool 모든 경계에서의 완전한 자동 전파
- 설계 없는 남용을 정당화하는 마법의 전역 상태

즉 `ContextVar`는 **애플리케이션 내부의 현재 실행 경로**를 다루는 도구이지, 시스템 전체 상관관계를 자동으로 해결하는 도구는 아니다.

---

## 핵심 개념 1: `ContextVar`의 생명주기, `set()` / `get()` / `reset()`을 정확히 이해해야 한다

가장 먼저 봐야 할 것은 API 자체보다 **값 복원 모델**이다.

```python
from contextvars import ContextVar

request_id_var: ContextVar[str] = ContextVar("request_id")


def handle() -> None:
    token = request_id_var.set("req-123")
    try:
        print(request_id_var.get())
    finally:
        request_id_var.reset(token)
```

여기서 중요한 포인트는 세 가지다.

### 1) `set()`은 토큰을 반환한다

이 토큰은 "이 값을 쓰기 전 상태"를 기억한다. 그래서 `finally`에서 `reset(token)`을 호출하면 이전 상태로 되돌릴 수 있다.

이게 중요한 이유는 컨텍스트가 중첩될 수 있기 때문이다.

```python
token1 = request_id_var.set("req-parent")
try:
    token2 = request_id_var.set("req-child")
    try:
        ...
    finally:
        request_id_var.reset(token2)
finally:
    request_id_var.reset(token1)
```

reset 없이 덮어쓰기만 하면 나중 로그에서 이전 요청의 값이 남아 있는 **context leak**가 생긴다.

### 2) 기본값 처리 전략을 정해야 한다

```python
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
```

기본값을 둘 수도 있고, `get()` 시 값이 없으면 예외를 내도록 할 수도 있다.

- 운영 공통 로깅 키라면 `default=None`이 편하다
- 반드시 있어야 하는 핵심 값이라면 값이 없는 상황을 오류로 빨리 드러내는 편이 낫다

보통은 다음처럼 접근한다.

- `request_id`, `trace_id`, `tenant_id`: 기본값 `None`
- 보안/권한 검증에서 반드시 필요한 현재 사용자 객체: 명시적 전달 선호

### 3) 컨텍스트 값은 영속 저장이 아니라 실행 중 메타데이터다

`ContextVar`에 도메인 엔티티나 대용량 payload를 넣는 팀이 있는데, 거의 항상 악수다.

좋은 값:

- request id
- trace id
- tenant id
- actor id
- locale
- feature flag snapshot
- log correlation key

나쁜 값:

- ORM session 객체 전체
- 대형 request body
- mutable dict를 그대로 공유한 상태
- 캐시처럼 쓰는 도메인 데이터

핵심은 간단하다. `ContextVar`는 **문맥 식별자**에 가깝게 유지해야 한다.

---

## 핵심 개념 2: 왜 `threading.local()`은 async request scope의 안전한 대체재가 아닌가

과거 Python 웹 애플리케이션은 thread-local 기반 request context를 꽤 많이 썼다.

```python
import threading

_local = threading.local()
_local.request_id = "req-123"
```

이 방식이 먹힌 이유는 요청과 스레드가 거의 1:1처럼 움직였기 때문이다. 그런데 ASGI + asyncio 환경에서는 아래가 바뀐다.

- 하나의 이벤트 루프 스레드 안에서 여러 요청 coroutine이 interleave 된다
- 어떤 `await` 이후 다시 깨어날 때 같은 스레드이긴 하지만, 그 사이 다른 요청도 이미 같은 스레드를 사용했다
- 따라서 스레드 단위 저장은 요청 단위 격리를 보장하지 않는다

즉 문제는 단순히 스레드 수가 적어서가 아니다. **동시성의 단위가 바뀌었기 때문**이다.

### `ContextVar`가 이 문제를 푸는 방식

`ContextVar`는 현재 실행 컨텍스트별 값을 관리한다. 그래서 같은 스레드 안에서 여러 coroutine이 번갈아 돌아도 값이 섞이지 않는다.

```python
import asyncio
from contextvars import ContextVar

request_id_var: ContextVar[str] = ContextVar("request_id")


async def worker(name: str, req_id: str) -> None:
    token = request_id_var.set(req_id)
    try:
        await asyncio.sleep(0.1)
        print(name, request_id_var.get())
    finally:
        request_id_var.reset(token)


async def main() -> None:
    await asyncio.gather(
        worker("A", "req-a"),
        worker("B", "req-b"),
    )
```

이때 A와 B는 같은 이벤트 루프에서 돌아도 서로의 `request_id`를 침범하지 않는다.

### 그렇다고 모든 것이 자동 해결되는 것은 아니다

많은 팀이 여기서 멈춘다. 하지만 실전에서는 더 까다로운 질문이 남는다.

- task를 새로 만들면 컨텍스트가 어떻게 복사되는가
- thread로 나가면 유지되는가
- process로 나가면 유지되는가
- 외부 큐에 넣었다가 다시 소비될 때는 어떻게 되는가

즉 `ContextVar`를 도입한 뒤부터 진짜 중요한 건 **경계(boundary) 설계**다.

---

## 핵심 개념 3: request scope는 로깅 기능이 아니라 애플리케이션 경계 설계다

실무에서는 `contextvars`를 대부분 로깅 때문에 도입한다. 맞는 접근이다. 다만 "로그에 request_id 하나 넣기" 수준으로 끝내면 효과가 제한적이다.

좋은 request scope 설계는 보통 아래 질문에 답한다.

1. **어디서 시작되는가**
   - HTTP middleware
   - consumer entrypoint
   - CLI job 시작점
2. **무슨 키를 넣는가**
   - request id
   - trace id
   - actor id
   - tenant id
   - endpoint/job name
3. **어디까지 자동 전파되는가**
   - 같은 coroutine
   - child task
   - thread helper
4. **어디서 반드시 명시적으로 끊거나 복제해야 하는가**
   - thread pool
   - background queue
   - 외부 이벤트 발행
5. **어떻게 정리되는가**
   - 응답 직후 reset
   - task 완료 후 reset
   - consumer 메시지 처리 완료 후 reset

### request scope에서 자주 쓰는 키의 역할 구분

실무에서는 아래 세 종류를 혼동하면 운영 가독성이 떨어진다.

#### 1) request id

애플리케이션 진입 한 번을 식별한다. 같은 HTTP 요청 전체에 동일하다.

#### 2) trace id / correlation id

여러 서비스, 여러 컴포넌트까지 이어질 수 있는 상위 흐름 식별자다. 이미 OpenTelemetry나 API Gateway에서 준다면 그 값을 따르는 편이 좋다.

#### 3) span 수준 세부 키

order_id, payment_id, tenant_id, user_id, batch_id 같은 업무 식별자다.

운영에서 정말 유용한 조합은 보통 이렇다.

- `trace_id`: 서비스 간 연결
- `request_id`: 현재 프로세스 진입 단위
- `tenant_id`, `user_id`, `order_id`: 업무 맥락

즉 request scope는 단일 키 하나가 아니라 **관측 기준 집합**이다.

---

## 실무 예시 1: FastAPI middleware에서 컨텍스트를 생성하고 구조화 로그에 주입하기

가장 먼저 적용하기 좋은 패턴이다.

### 1) 컨텍스트 변수 정의

```python
from contextvars import ContextVar

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
trace_id_var: ContextVar[str | None] = ContextVar("trace_id", default=None)
user_id_var: ContextVar[str | None] = ContextVar("user_id", default=None)
tenant_id_var: ContextVar[str | None] = ContextVar("tenant_id", default=None)
```

### 2) middleware에서 set/reset

```python
import uuid
from fastapi import FastAPI, Request

app = FastAPI()


@app.middleware("http")
async def bind_request_context(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    trace_id = request.headers.get("traceparent") or request_id
    user_id = request.headers.get("x-user-id")
    tenant_id = request.headers.get("x-tenant-id")

    tokens = [
        (request_id_var, request_id_var.set(request_id)),
        (trace_id_var, trace_id_var.set(trace_id)),
        (user_id_var, user_id_var.set(user_id)),
        (tenant_id_var, tenant_id_var.set(tenant_id)),
    ]

    try:
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response
    finally:
        for var, token in reversed(tokens):
            var.reset(token)
```

여기서 중요한 포인트는 두 가지다.

- 항상 `finally`에서 reset한다
- reset은 set의 역순으로 수행하는 편이 안전하다

### 3) 로거에 자동 주입

표준 logging을 써도 되고, structlog/loguru를 써도 된다. 핵심은 로깅 호출부마다 일일이 값을 넘기지 않는 것이다.

```python
import logging


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        record.trace_id = trace_id_var.get()
        record.user_id = user_id_var.get()
        record.tenant_id = tenant_id_var.get()
        return True


logger = logging.getLogger("app")
logger.addFilter(ContextFilter())
```

포맷터는 예를 들어 이렇게 둘 수 있다.

```python
LOG_FORMAT = (
    "%(asctime)s %(levelname)s %(name)s "
    "request_id=%(request_id)s trace_id=%(trace_id)s "
    "tenant_id=%(tenant_id)s user_id=%(user_id)s "
    "%(message)s"
)
```

### 이 패턴의 장점

- 비즈니스 함수 시그니처가 깔끔해진다
- 같은 요청 안의 모든 로그에 동일한 식별자가 찍힌다
- logger 호출부가 메타데이터를 몰라도 된다
- 운영자가 grep, Loki, Elasticsearch, Datadog에서 같은 키로 흐름을 재구성하기 쉬워진다

### 이 패턴의 한계

- 숨은 의존성이 생긴다. 함수가 어떤 컨텍스트 키를 암묵적으로 기대하는지 코드만 보고는 안 드러날 수 있다
- HTTP 경계를 벗어나면 자동 전파가 끊기는 지점이 있다
- 테스트에서 컨텍스트 초기화 없이 함수만 부르면 동작이 달라질 수 있다

그래서 다음 원칙이 중요하다.

> **비즈니스 판단에 필요한 값은 명시적으로 전달하고, 관측/상관관계용 메타데이터는 컨텍스트에 둔다.**

예를 들어 권한 체크에 필요한 `current_user` 전체 객체를 `ContextVar`에서 꺼내 비즈니스 로직의 입력으로 삼는 패턴은 보통 과하다.

---

## 실무 예시 2: 서비스 레이어에서 "로그만 컨텍스트 사용"하고 도메인 입력은 명시적으로 유지하기

아래 두 코드를 비교해보자.

### 나쁜 예: 비즈니스 로직이 컨텍스트 숨은 의존성에 기대는 경우

```python
async def issue_refund(order_id: str) -> None:
    user_id = user_id_var.get()
    if user_id is None:
        raise PermissionError("missing user")
    ...
```

겉보기엔 편하다. 하지만 함수 계약이 흐려진다.

- 누가 이 함수를 호출할 수 있는가?
- 시스템 작업이나 배치에서도 호출 가능한가?
- 테스트에서는 무엇을 먼저 세팅해야 하는가?

이건 로깅 편의성을 넘어 **도메인 입력을 숨겨버린 상태**다.

### 더 나은 예: 도메인 입력은 명시적, 로그 메타데이터는 자동

```python
async def issue_refund(order_id: str, actor_id: str) -> None:
    logger.info("refund requested", extra={"order_id": order_id, "actor_id": actor_id})
    ...
```

여기서 logger는 내부적으로 `request_id`, `trace_id`, `tenant_id`를 자동 주입받고, 도메인 함수는 실제 필요한 입력만 명시적으로 받는다.

이 패턴이 좋은 이유는 다음과 같다.

- 권한과 규칙에 필요한 값은 계약으로 드러난다
- 관측 메타데이터는 부가 부담 없이 남는다
- HTTP, CLI, batch, event consumer 어디서 호출해도 함수 의미가 같다

실무 감각으로 정리하면 이렇다.

- **업무 규칙에 필요한 값**: 함수 인자로 전달
- **로그 검색과 추적에 필요한 값**: `ContextVar`로 자동 주입

이 선을 흐리면 처음엔 편하고 나중엔 디버깅이 더 어려워진다.

---

## 핵심 개념 4: async 경계에서는 "어디까지 전파되고 어디서 분기되는지"를 알아야 한다

`contextvars`를 쓸 때 가장 많이 헷갈리는 부분이다.

### 1) 같은 coroutine 안에서는 자연스럽게 유지된다

이건 가장 단순하다.

```python
async def handler() -> None:
    token = request_id_var.set("req-123")
    try:
        await service_a()
        await service_b()
    finally:
        request_id_var.reset(token)
```

`await`를 오가도 현재 실행 흐름 안에서는 같은 컨텍스트를 본다.

### 2) `asyncio.create_task()`는 생성 시점의 컨텍스트를 이어받는다

```python
async def child() -> None:
    logger.info("child task")


async def parent() -> None:
    token = request_id_var.set("req-123")
    try:
        task = asyncio.create_task(child())
        await task
    finally:
        request_id_var.reset(token)
```

여기서 child는 보통 `req-123`을 본다. 중요한 것은 **생성 시점 스냅샷**에 가깝게 이해하는 것이다.

- parent가 가진 현재 컨텍스트를 child가 이어받는다
- child 안에서 값을 바꿔도 parent의 값을 되돌려 쓰는 용도로 기대하면 안 된다
- child가 별도 하위 흐름이라면 request id는 유지하되, span 성격의 세부 id는 새로 생성하는 편이 낫다

### 3) `TaskGroup`도 같은 원칙으로 생각하면 된다

```python
async with asyncio.TaskGroup() as tg:
    tg.create_task(fetch_profile())
    tg.create_task(fetch_orders())
```

같은 요청 안에서 파생된 하위 작업들이 같은 trace/request 문맥을 갖게 만드는 데 적합하다. 다만 하위 작업 각각을 완전히 다른 업무 흐름처럼 취급해야 한다면, 그 안에서 별도 보조 키를 설정하는 것이 운영 가독성에 좋다.

예를 들어:

- 상위 `request_id`는 유지
- 하위 `subtask_name`, `integration_name`, `attempt`는 각 task에서 별도 세팅

### 4) `asyncio.to_thread()`는 컨텍스트 전달에 유리하지만, 일반 thread/executor 경계는 주의해야 한다

동기 라이브러리를 임시로 thread로 감싸는 경우가 있다.

```python
result = await asyncio.to_thread(run_blocking_call)
```

이 경우 현재 컨텍스트가 같이 넘어가는 동작을 기대할 수 있다. 하지만 모든 thread 실행 경로가 항상 같은 보장을 주는 것은 아니다. 특히 직접 `ThreadPoolExecutor`를 다루거나 오래된 패턴의 `run_in_executor()`를 쓰면 컨텍스트 전달을 명시적으로 관리해야 할 수 있다.

실무에서는 다음 원칙이 안전하다.

- `to_thread()`를 우선 고려
- 커스텀 executor 경계에서는 자동 전파를 가정하지 말기
- 필요하면 `copy_context()`로 명시적으로 감싸기

```python
from contextvars import copy_context

ctx = copy_context()
future = executor.submit(ctx.run, run_blocking_call)
```

### 5) process, 큐, 외부 브로커 경계에서는 자동 전파가 없다

여기서 가장 큰 오해가 생긴다.

- Celery task
- Kafka consumer
- Redis queue worker
- separate batch process
- cron job

이런 경계는 **새 실행 환경**이다. 따라서 `ContextVar` 값이 자동으로 건너가지 않는다. 필요한 식별자는 메시지 payload나 header에 명시적으로 실어야 한다.

```python
message = {
    "order_id": order_id,
    "trace_id": trace_id_var.get(),
    "request_id": request_id_var.get(),
}
```

그리고 소비 측 entrypoint에서 다시 바인딩해야 한다.

```python
def consume(message: dict) -> None:
    token = trace_id_var.set(message.get("trace_id"))
    try:
        ...
    finally:
        trace_id_var.reset(token)
```

이걸 놓치면 서비스 내부 로그는 연결되는데, 비동기 후속 처리부터는 흐름이 끊긴다.

---

## 실무 예시 3: 구조화 로그를 "문자열 로그"가 아니라 검색 가능한 이벤트로 설계하기

`contextvars`의 진짜 효과는 구조화 로그와 붙을 때 나온다.

문자열 로그 위주로 남기면 request id가 있어도 검색 품질이 제한된다.

```python
logger.info(f"order created: order_id={order_id} tenant={tenant_id}")
```

이 방식의 문제는 다음과 같다.

- 필드명이 일관되지 않기 쉽다
- 파싱 규칙이 복잡하다
- 운영 도구에서 정렬, 집계, 필터링이 어렵다

대신 이벤트 로그처럼 남기는 편이 좋다.

```python
logger.info(
    "order_created",
    extra={
        "order_id": order_id,
        "payment_method": payment_method,
        "amount": amount,
    },
)
```

여기에 컨텍스트 필터가 `trace_id`, `request_id`, `tenant_id`, `user_id`를 자동 주입하면, 운영자는 아래처럼 질문할 수 있다.

- 특정 `trace_id`의 전체 흐름
- 특정 `tenant_id`에서 최근 결제 실패만 필터링
- 특정 `request_id` 내 warning/error 이벤트만 조회
- 특정 `order_id`를 가진 이벤트를 시간순으로 재구성

### 필드 네이밍 기준도 중요하다

팀마다 로그 필드명이 흔들리면 나중에 더 힘들다.

나쁜 예:

- `reqId`, `requestId`, `request_id` 혼용
- `uid`, `user_id`, `member_id` 혼용
- `tenant`, `tenant_id`, `workspace_id` 혼용

좋은 예:

- 상관관계 키는 snake_case로 통일
- 시스템 공통 키와 도메인 키를 구분
- 모든 서비스에서 최소 공통 집합 유지

예시:

- 공통: `trace_id`, `request_id`, `service`, `env`, `version`
- 사용자/범위: `tenant_id`, `user_id`, `actor_id`
- 업무: `order_id`, `payment_id`, `job_id`

즉 `contextvars` 도입은 사실상 **관측 스키마 표준화 작업**과 같이 가야 한다.

---

## 핵심 개념 5: `contextvars`와 OpenTelemetry는 대체재가 아니라 서로 다른 층의 도구다

실무에서 자주 나오는 오해가 하나 더 있다.

- "우리는 OpenTelemetry 쓰니까 `contextvars` 안 써도 된다"
- 또는 반대로 "`contextvars`로 trace id 넣었으니 tracing은 된 거다"

둘 다 절반만 맞다.

### 역할을 분리해서 봐야 한다

#### `contextvars`

- 애플리케이션 내부 현재 실행 흐름에 메타데이터를 바인딩한다
- 로깅, 로컬 관측, request scope 전달에 강하다
- 개발자가 원하는 커스텀 키를 쉽게 싣기 좋다

#### OpenTelemetry

- 분산 추적 표준을 제공한다
- 서비스 간 span 관계, duration, attribute, propagation 규칙을 다룬다
- exporter를 통해 Jaeger, Tempo, Datadog, Honeycomb 등으로 흘려보내기 좋다

즉 실무에서는 대개 이렇게 결합한다.

- tracing 시스템이 생성한 `trace_id`, `span_id`를 로그에 같이 남긴다
- 애플리케이션 로컬 키인 `request_id`, `tenant_id`, `user_id`, `job_id`는 `contextvars`로 관리한다
- 로그 검색과 trace drill-down이 서로 연결되도록 필드명을 맞춘다

### 왜 둘을 같이 써야 하는가

trace만 있고 애플리케이션 로그 필드가 부실하면, "어느 span이 느린가"는 보여도 "이 span이 어느 주문/어느 테넌트/어느 운영 이벤트와 연결되는가"가 약하다.

반대로 request id만 있고 분산 추적이 없으면, 서비스 A에서 B, C로 이어지는 cross-service 지연은 읽기 어렵다.

가장 운영 친화적인 조합은 다음과 같다.

- trace 시스템: 네트워크 경계와 span 구조 추적
- `contextvars`: 애플리케이션 내부 공통 메타데이터 바인딩
- 구조화 로그: 인간이 읽고 검색하는 사건 기록

### 추천 필드 설계

로깅 이벤트에는 최소한 아래 정도를 맞추는 편이 좋다.

- `trace_id`: tracing 시스템 식별자
- `span_id`: 가능하면 현재 span 식별자
- `request_id`: 애플리케이션 진입 단위 식별자
- `tenant_id`, `user_id`, `job_id`: 운영 검색용 업무 키
- `service`, `env`, `version`: 배포 맥락

이렇게 해두면 운영자는 다음 경로로 역추적할 수 있다.

1. 에러 로그에서 `trace_id` 확인
2. tracing 시스템에서 같은 trace 조회
3. 느린 span과 예외 span 확인
4. 같은 trace에 묶인 도메인 식별자와 요청 헤더 확인
5. 재시도, 후속 비동기 작업, 외부 호출 로그까지 이어서 검색

즉 `contextvars`는 tracing을 대체하는 게 아니라, **trace에 비즈니스 문맥을 실무적으로 붙이는 접착층**에 가깝다.

---

## 실무 예시 4: 이벤트 발행과 소비에서 상관관계 키를 어떻게 이어갈 것인가

HTTP 요청 안에서는 컨텍스트가 잘 보이는데, 이벤트 기반 아키텍처로 넘어가면 갑자기 로그 흐름이 끊기는 팀이 많다. 원인은 거의 항상 같다.

- producer는 컨텍스트를 로컬 메모리에만 가지고 있음
- broker로 보낸 메시지에는 trace/request 키가 없음
- consumer는 새 프로세스라서 이전 컨텍스트를 알 수 없음

따라서 이벤트 발행 시점에는 **무슨 키를 실을지**를 먼저 정해야 한다.

### 어떤 키를 메시지에 실어야 하나?

보통 아래 정도면 충분하다.

- `trace_id`: 전체 흐름 상관관계
- `request_id`: 원 요청 기준점
- `causation_id`: 이 이벤트를 직접 발생시킨 로컬 액션 id
- `correlation_id`: 같은 비즈니스 흐름을 묶는 상위 id
- `tenant_id`, `actor_id`: 운영상 필요한 경우

예를 들어 주문 생성 후 이벤트를 발행한다면:

```python
from dataclasses import asdict, dataclass


@dataclass
class EventEnvelope:
    event_name: str
    payload: dict
    trace_id: str | None
    request_id: str | None
    correlation_id: str | None
    causation_id: str | None
    tenant_id: str | None


async def publish_order_created(order_id: str, tenant_id: str) -> None:
    envelope = EventEnvelope(
        event_name="order_created",
        payload={"order_id": order_id},
        trace_id=trace_id_var.get(),
        request_id=request_id_var.get(),
        correlation_id=order_id,
        causation_id=request_id_var.get(),
        tenant_id=tenant_id,
    )
    await broker.publish(asdict(envelope))
```

여기서 핵심은 payload와 상관관계 메타데이터를 분리하는 것이다. 그래야 운영 도구에서도 envelope만 보고 흐름을 파악할 수 있다.

### 소비 측에서는 entrypoint에서 다시 바인딩한다

```python
def bind_event_context(message: dict):
    tokens = [
        (trace_id_var, trace_id_var.set(message.get("trace_id"))),
        (request_id_var, request_id_var.set(message.get("request_id"))),
        (tenant_id_var, tenant_id_var.set(message.get("tenant_id"))),
    ]
    return tokens


def reset_tokens(tokens) -> None:
    for var, token in reversed(tokens):
        var.reset(token)


async def consume_order_created(message: dict) -> None:
    tokens = bind_event_context(message)
    try:
        logger.info(
            "consume_order_created",
            extra={
                "order_id": message["payload"]["order_id"],
                "correlation_id": message.get("correlation_id"),
            },
        )
        await rebuild_projection(message["payload"]["order_id"])
    finally:
        reset_tokens(tokens)
```

이 패턴의 장점은 HTTP, consumer, batch를 **같은 관측 규칙**으로 묶을 수 있다는 점이다.

### 재시도와 DLQ에서는 id 정책을 따로 정해야 한다

여기서 운영 난이도가 올라간다. 예를 들어 같은 메시지가 세 번 재시도될 때 아래 중 무엇을 유지할지 정해야 한다.

- 원본 `trace_id` 유지
- 재시도마다 새 `span_id` 부여
- `attempt` 숫자 별도 기록
- 최종 DLQ 이동 시 `first_seen_at`, `last_error`, `attempt` 저장

실무 추천은 보통 이렇다.

- 비즈니스 흐름을 대표하는 `trace_id` 또는 `correlation_id`는 유지
- 각 재시도 실행은 별도 attempt 메타데이터로 구분
- 로그와 메트릭에서 `attempt`를 함께 남김

그렇게 해야 "같은 사건의 반복 실패"인지, "완전히 다른 사건"인지 구분하기 쉽다.

---

## 실무 예시 5: 테스트에서 context leak를 잡지 못하면 운영에서만 이상한 로그가 나온다

`contextvars`는 정상 경로에서는 잘 동작해 보여도, 테스트가 허술하면 누수가 숨어들기 쉽다. 특히 아래 상황에서 자주 놓친다.

- middleware에서 예외가 날 때 reset이 누락됨
- helper 함수가 내부적으로 `set()`만 하고 `reset()`을 안 함
- 테스트가 순차 실행일 때는 멀쩡하지만 동시 실행에서만 섞임
- pytest fixture가 값을 세팅하고 다음 테스트까지 끌고 감

### 1) 최소한의 reset 보장 테스트

```python
import pytest


@pytest.mark.asyncio
async def test_context_is_reset_after_request(client):
    response = await client.get("/health", headers={"x-request-id": "req-test-1"})
    assert response.status_code == 200
    assert request_id_var.get() is None
```

테스트 종료 시점에 현재 컨텍스트가 깨끗한지 확인하는 것만으로도 누락을 꽤 빨리 잡을 수 있다.

### 2) 동시 요청 분리 테스트

```python
import asyncio


@pytest.mark.asyncio
async def test_request_context_isolated_under_concurrency(client):
    async def call(req_id: str):
        response = await client.get("/echo-context", headers={"x-request-id": req_id})
        return response.json()["request_id"]

    results = await asyncio.gather(
        call("req-a"),
        call("req-b"),
        call("req-c"),
    )

    assert results == ["req-a", "req-b", "req-c"]
```

이 테스트가 중요한 이유는 thread-local 기반 코드나 reset 누락이 있을 때 동시성 상황에서만 깨지는 문제가 바로 드러나기 때문이다.

### 3) executor 경계 테스트

```python
@pytest.mark.asyncio
async def test_context_propagates_to_to_thread():
    token = request_id_var.set("req-thread")
    try:
        value = await asyncio.to_thread(request_id_var.get)
        assert value == "req-thread"
    finally:
        request_id_var.reset(token)
```

반대로 커스텀 executor를 쓴다면 "자동 전파되지 않아야 정상"인 테스트도 둘 수 있다. 그다음 `copy_context()`를 적용한 뒤 기대 동작으로 바꾸면 된다.

### 4) 로그 필드 존재 테스트

실무에서는 컨텍스트가 살아 있어도 formatter/filter 설정이 누락되어 실제 로그에 안 찍히는 경우도 많다.

- 로거 인스턴스만 다르고 filter 미적용
- JSON formatter가 특정 필드를 버림
- background worker는 별도 logging config를 써서 필드가 누락됨

따라서 적어도 핵심 로거에 대해서는 캡처된 로그 레코드에 필드가 들어 있는지 검증하는 테스트가 필요하다.

```python
def test_log_record_has_request_id(caplog):
    token = request_id_var.set("req-log-1")
    try:
        logger.info("hello")
    finally:
        request_id_var.reset(token)

    record = caplog.records[-1]
    assert getattr(record, "request_id") == "req-log-1"
```

테스트 관점에서 중요한 건 기능 테스트만이 아니다. **관측 가능성 자체를 회귀 테스트 대상으로 올리는 것**이 운영 비용을 크게 낮춘다.

---

## 도입 전략: 한 번에 전역 치환하지 말고, 진입점부터 좁게 넣어라

팀이 기존 코드베이스에 `contextvars`를 도입할 때 자주 하는 실수는 두 가지다.

- 모든 helper 함수에 한 번에 적용하려 든다
- 반대로 middleware만 넣고 끝내서 실제 로그에는 반영되지 않는다

현실적인 도입 순서는 보통 아래가 가장 안전하다.

### 1단계: 진입점 한 곳에서 request id만 바인딩

- HTTP middleware
- consumer entrypoint
- CLI main 함수

가장 먼저 `request_id` 하나만 넣고, 응답 헤더 및 핵심 에러 로그에 찍히는지 본다.

### 2단계: 로깅 필터/포매터를 붙여 모든 공통 로그에 자동 주입

이 단계가 빠지면 `ContextVar`는 생겼는데 아무도 안 보는 값이 된다. 로그 수집 파이프라인에서 필드가 실제 인덱싱되는지까지 확인해야 한다.

### 3단계: `trace_id`, `tenant_id`, `user_id` 등 최소 키 확장

운영에서 실제 검색에 필요한 필드만 넣는다. 처음부터 열 개 넘는 키를 넣으면 관리가 어렵다.

### 4단계: background producer/consumer 경계에 envelope 규칙 추가

이 단계부터는 코드보다 메시지 계약이 중요하다. 어떤 토픽, 어떤 큐, 어떤 워커가 같은 규칙을 따를지 문서화해야 한다.

### 5단계: tracing과 연결

OpenTelemetry를 쓴다면 trace id를 로그에 같이 남기고, APM에서 로그와 trace를 교차 이동할 수 있게 한다.

이 순서가 좋은 이유는 "먼저 관측 가치가 바로 보이는 곳"부터 효과를 낼 수 있기 때문이다. 특히 request id만 제대로 잡아도 장애 대응 시간이 꽤 줄어드는 팀이 많다.

---

## 판단 기준: 언제 `contextvars`를 쓰고, 언제 명시적 파라미터나 DI가 더 나은가

마지막으로 실무 의사결정 기준을 정리해보자.

### `contextvars`가 잘 맞는 경우

- 요청/작업 범위 메타데이터를 공통 로그에 자동 주입하고 싶다
- 함수 시그니처를 메타데이터 인자로 오염시키고 싶지 않다
- asyncio 기반 서비스에서 thread-local 대체가 필요하다
- middleware/consumer entrypoint가 명확하다
- tracing/logging 표준화 작업을 같이 진행할 수 있다

### 명시적 파라미터가 더 나은 경우

- 비즈니스 규칙 판단에 반드시 필요한 입력이다
- 함수 계약이 외부에 분명히 드러나야 한다
- 배치, CLI, 테스트, HTTP 등 여러 진입 경로에서 같은 함수가 쓰인다
- 컨텍스트 없이는 함수 의미가 성립하지 않는다

### DI/명시적 객체 전달이 더 나은 경우

- 현재 사용자, 권한 스냅샷, 트랜잭션 유닛 오브 워크 같은 구조화된 의존성이 필요하다
- 테스트 더블 교체가 자주 필요하다
- 로깅 메타데이터보다 행위와 상태가 중요하다

한 줄로 줄이면 이렇다.

> **컨텍스트는 "누가 이 작업을 둘러싸고 있었는가"를 담고, 함수 인자는 "이 작업이 무엇을 해야 하는가"를 담아야 한다.**

이 구분이 선명할수록 코드와 운영 둘 다 편해진다.

---

## 트레이드오프: `contextvars`는 강력하지만, 남용하면 디버깅 가능한 전역 상태가 된다

실무에서 가장 좋은 패턴은 "많이 쓰는 것"이 아니라 "좁고 일관되게 쓰는 것"이다.

### 장점

#### 1) 함수 시그니처 오염을 줄인다

관측 메타데이터를 모든 함수에 넘기지 않아도 된다.

#### 2) 동시성 환경에서 로그 상관관계를 안정적으로 유지한다

같은 이벤트 루프, 같은 프로세스 안에서 요청별 로그 분리가 훨씬 좋아진다.

#### 3) middleware/consumer entrypoint에서 공통 처리를 중앙화할 수 있다

request id 생성, trace id binding, 응답 헤더 주입을 한 곳에서 관리할 수 있다.

#### 4) 라이브러리 경계를 넘는 로깅 일관성이 좋아진다

하위 서비스 함수가 메타데이터를 몰라도 같은 문맥을 가진 로그를 남길 수 있다.

### 단점

#### 1) 숨은 의존성이 생긴다

코드만 보고는 어떤 컨텍스트 키가 필요한지 드러나지 않는다.

#### 2) 테스트가 부주의하면 누수가 숨어든다

테스트 케이스 하나가 set만 하고 reset 안 하면 다음 테스트가 오염될 수 있다.

#### 3) 경계 밖 자동 전파를 과신하기 쉽다

thread, process, queue 경계에서 암묵 전파를 기대하면 운영에서만 끊긴다.

#### 4) 도메인 상태까지 넣기 시작하면 아키텍처가 흐려진다

"지금 로그인 유저", "현재 세션", "현재 DB 세션" 같은 걸 전부 컨텍스트로 숨기면 추적이 더 어려워진다.

### 그래서 추천 기준은 이렇다

- **넣어도 되는 것**: 로그 상관관계, 추적, 요청 범위 메타데이터
- **신중해야 하는 것**: 권한 판단에 필요한 객체, mutable 상태, 트랜잭션 핸들
- **피해야 하는 것**: 비즈니스 규칙의 핵심 입력, 대형 객체, 수명 긴 캐시 역할

---

## 흔한 실수 1: `reset()`을 빼먹어 컨텍스트가 새 요청으로 샌다

가장 흔하고, 가장 위험하다.

```python
request_id_var.set("req-123")
await call_next(request)
```

이렇게만 쓰면 현재 실행 경로가 끝난 뒤에도 값이 남을 수 있다. 이벤트 루프 상에서 다른 요청 처리 흐름과 섞이면 로그가 이상하게 이어진다.

반드시 token을 보관하고 `finally`에서 reset해야 한다.

```python
token = request_id_var.set("req-123")
try:
    await call_next(request)
finally:
    request_id_var.reset(token)
```

---

## 흔한 실수 2: mutable dict 하나를 컨텍스트에 넣고 여기저기 수정한다

아래 패턴은 얼핏 편해 보인다.

```python
log_context_var = ContextVar("log_context", default={})
```

그리고 필요한 곳마다 dict를 꺼내 수정한다.

문제는 다음과 같다.

- default mutable 객체 공유 실수가 생기기 쉽다
- 누가 어떤 키를 언제 바꿨는지 추적이 어렵다
- 작은 오염이 전체 로그 품질 저하로 이어진다

보통은 개별 키를 독립 `ContextVar`로 두거나, 불변에 가까운 작은 구조를 새로 만들어 바인딩하는 편이 낫다.

---

## 흔한 실수 3: background job까지 자동으로 이어질 거라고 가정한다

HTTP 요청 중에는 잘 되던 request id가, 큐 소비 작업부터 갑자기 비어 있는 경우가 많다. 원인은 간단하다. 이미 다른 프로세스, 다른 실행 경계로 넘어갔기 때문이다.

이럴 때 필요한 것은 `contextvars` 추가가 아니라 **메시지 계약**이다.

- producer가 trace/request 식별자를 payload 또는 header에 실어야 한다
- consumer entrypoint가 그 값을 다시 set/reset 해야 한다
- 재시도 시에는 원본 trace를 유지할지, attempt 단위 새 id를 만들지 기준을 정해야 한다

즉 비동기 아키텍처에서는 `ContextVar`보다 **전파 프로토콜**이 더 중요할 때가 많다.

---

## 흔한 실수 4: 모든 값을 컨텍스트에서 꺼내 쓰며 함수 계약을 숨긴다

컨텍스트는 편하다. 그래서 금방 중독된다.

```python
async def charge_payment() -> None:
    tenant_id = tenant_id_var.get()
    user_id = user_id_var.get()
    order_id = order_id_var.get()
    ...
```

이 패턴이 늘어나면 함수는 입력이 없는 것처럼 보이지만 실제로는 숨은 의존성이 많아진다. 테스트도 어렵고 재사용도 나빠진다.

실무 기준으로는 아래처럼 선을 긋는 것이 좋다.

- **비즈니스 액션 함수**: 필요한 도메인 값 명시적 전달
- **공통 로깅/관측 계층**: 컨텍스트 자동 사용
- **정말 공통적인 진입점 메타데이터**만 `ContextVar`에 둠

---

## 실무 시나리오: 장애 대응에서 `contextvars` 설계가 실제로 시간을 얼마나 줄여주는가

개념이 많아 보이지만, 운영에서는 결국 "문제를 얼마나 빨리 좁힐 수 있느냐"로 가치가 드러난다. 주문 API 장애 상황을 하나 가정해보자.

### 상황

- 사용자가 결제를 완료했는데 주문 상태가 `PENDING`에 머문다
- API 서버에는 timeout 로그가 간헐적으로 있다
- 결제사 연동, 이벤트 발행, projection consumer가 모두 관련되어 있다
- 같은 시각에 다른 테넌트 트래픽도 많아 로그 양이 크다

### 컨텍스트 설계가 없는 경우

운영자는 보통 이렇게 헤맨다.

1. 사용자 신고 시각 기준으로 전체 에러 로그를 검색
2. 주문 번호 문자열이 찍힌 로그를 grep
3. API 서버, 워커, 컨슈머 로그 시간을 감으로 맞춤
4. 재시도 로그와 최초 실행 로그를 구분 못 함
5. 결국 여러 서비스 로그를 수동으로 이어 붙임

이 과정은 보통 시간이 오래 걸리고, 재현이 어려우며, 같은 장애가 다시 나도 학습 효과가 낮다.

### 컨텍스트 설계가 있는 경우

로그에 아래 필드가 일관되게 찍힌다고 하자.

- `trace_id`
- `request_id`
- `tenant_id`
- `order_id`
- `attempt`
- `event_name`

그러면 조사 순서는 훨씬 짧아진다.

1. 사용자에게 받은 `x-request-id` 또는 주문 번호로 로그 검색
2. 해당 레코드에서 `trace_id`, `tenant_id`, `order_id` 확인
3. 같은 `trace_id`로 API 서버, 결제 호출, 이벤트 발행 로그를 한 번에 조회
4. consumer 로그에서는 같은 `order_id`와 `correlation_id`로 후속 처리 확인
5. 실패가 최초 요청인지, 재시도 3회차인지 `attempt`로 즉시 판별
6. tracing 화면에서는 어느 외부 호출에서 시간이 길어졌는지 확인

이렇게 되면 장애 대응의 핵심 질문이 거의 즉시 정리된다.

- 결제 승인 자체는 성공했는가
- 이벤트는 발행됐는가
- consumer는 받았는가
- 받았다면 몇 번째 재시도에서 실패했는가
- 어느 테넌트/배포 버전/인스턴스에서 집중됐는가

즉 `contextvars`는 단순 로깅 문법이 아니라, **장애를 사람 머리로 재구성하는 비용을 줄이는 운영 설계**다.

### 이 시나리오에서 특히 중요한 교훈

- request scope는 요청 하나의 로그를 예쁘게 만드는 데서 끝나지 않는다
- 이벤트 발행과 소비까지 같은 상관관계 키가 이어져야 진짜 효과가 난다
- tracing, 구조화 로그, 컨텍스트 바인딩이 같은 규칙을 따라야 조사 속도가 빨라진다
- 결국 좋은 관측 설계는 성능 최적화 못지않게 **MTTR(mean time to recovery)** 를 줄인다

운영 단계에서는 이 차이가 크다. 처리량이 약간 느린 시스템보다, 장애 원인을 20분 안에 좁힐 수 있는 시스템이 훨씬 다루기 쉽다.

---

## 체크리스트: 운영에서 바로 적용할 수 있는 기준

### 설계 체크

- [ ] request scope의 시작점을 HTTP middleware, consumer entrypoint, CLI job entry로 명확히 정했는가
- [ ] `trace_id`, `request_id`, `tenant_id`, `user_id` 등 최소 공통 키를 정의했는가
- [ ] 도메인 입력과 관측 메타데이터의 경계를 분리했는가
- [ ] thread/process/queue 경계에서 자동 전파를 가정하지 않도록 팀 기준을 문서화했는가

### 구현 체크

- [ ] 모든 `set()`에 대응하는 `reset()`이 `finally`에 있는가
- [ ] middleware/consumer에서 token을 역순으로 reset하는가
- [ ] `create_task()`로 파생한 작업에서 필요한 추가 식별자를 명시적으로 넣는가
- [ ] executor 사용 시 `to_thread()` 또는 `copy_context()` 전략을 적용했는가
- [ ] background message에 필요한 상관관계 키를 payload/header에 실었는가

### 로깅 체크

- [ ] 문자열 로그 대신 검색 가능한 필드 중심 로그를 남기는가
- [ ] 필드명이 서비스 전반에서 일관적인가
- [ ] response header에 `x-request-id`를 돌려줘 클라이언트와 상호 추적이 가능한가
- [ ] 에러 로그에 최소한 `trace_id`, `request_id`, 핵심 도메인 식별자가 함께 남는가

### 테스트 체크

- [ ] 컨텍스트 reset 누락을 잡는 테스트가 있는가
- [ ] 동시 요청 상황에서 request id 혼선이 없는지 검증했는가
- [ ] thread/executor 경계 테스트를 별도로 두었는가
- [ ] consumer 재시도 시 trace/request 정책이 기대대로 유지되는지 확인했는가

---

## 한 줄 정리

`contextvars`는 "전역처럼 편한 상태"가 아니라, **동시성 환경에서도 요청 문맥을 오염 없이 전달해 구조화 로그와 추적 가능성을 지키기 위한 경계 설계 도구**로 써야 한다.
