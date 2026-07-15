---
layout: post
title: "Python 관측 가능성 설계: Logging, ContextVar, Exception Chain, OpenTelemetry로 운영 로그를 증거로 만드는 법"
date: 2026-07-15 11:50:00 +0900
categories: [python]
tags: [study, python, logging, observability, contextvars, opentelemetry, exception, tracing, structured-logging, backend, operations]
permalink: /python/2026/07/15/study-python-logging-contextvars-opentelemetry-exception-observability.html
---

## 배경: 로그는 많이 남기는 것이 아니라 나중에 판단할 수 있게 남기는 것이다

Python 백엔드 서비스를 운영하다 보면 로그는 거의 항상 있다. `logging.info()`도 있고, 예외가 나면 traceback도 찍히고, 웹 서버 access log도 남는다. 그런데 장애가 났을 때 실제로 도움이 되는 로그는 생각보다 적다.

장애 상황에서 필요한 질문은 대개 이런 형태다.

1. 이 요청은 어느 사용자, 어느 tenant, 어느 request id에서 시작됐는가
2. 같은 요청 안에서 호출한 DB, 외부 API, 메시지 발행은 각각 성공했는가
3. 실패한 함수는 원인이 되는 예외를 보존했는가, 아니면 새 예외로 덮어썼는가
4. timeout, retry, cancellation, validation failure, authorization failure를 서로 구분할 수 있는가
5. 같은 에러가 최근 배포 이후 늘었는가, 특정 endpoint나 worker queue에 집중되는가
6. 로그, metric, trace를 서로 연결할 수 있는 공통 키가 있는가
7. 개인정보나 토큰 같은 민감 정보가 로그에 섞이지 않는가

초기 서비스에서는 아래처럼 로그를 남겨도 어느 정도 충분해 보인다.

```python
logger.info("start")
logger.info("user created")
logger.error("failed")
```

하지만 운영 트래픽이 붙으면 이런 로그는 금방 한계에 부딪힌다.

- `failed`만 있고 어떤 요청인지 모른다
- 에러 메시지는 있는데 입력 조건과 외부 의존성 상태를 알 수 없다
- 여러 서비스의 로그를 모아도 같은 사용자 흐름으로 묶이지 않는다
- 재시도가 성공했는지 실패했는지, 몇 번째 시도였는지 알 수 없다
- 예외를 `raise RuntimeError("failed")`로 바꾸면서 원래 예외 stack이 사라진다
- 모든 로그가 문자열이라 검색과 집계가 어렵다
- debug 로그를 켰더니 비용과 노이즈가 폭발한다

이 문제는 로그 라인을 더 많이 추가한다고 해결되지 않는다. 오히려 의미 없는 로그가 많아지면 중요한 신호가 묻힌다. 중급 이상 Python 개발자에게 필요한 것은 "어디에 로그를 찍을까"가 아니라 **운영자가 판단할 수 있는 증거 모델을 어떻게 설계할까**다.

오늘 글은 Python 서비스에서 logging, `contextvars`, 예외 체인, 구조화 로그, OpenTelemetry를 함께 설계하는 방법을 정리한다. FastAPI, worker, batch, CLI 모두에 적용할 수 있는 기준을 목표로 한다.

이번 글에서 다룰 질문은 아래와 같다.

1. Python 표준 `logging`을 운영 기준으로 어떻게 구성해야 하는가
2. request id, user id, tenant id 같은 context를 함수 인자로 계속 넘기지 않고 어떻게 보존할 수 있는가
3. `raise ... from ...`으로 예외 원인을 어떻게 보존해야 하는가
4. 구조화 로그는 어떤 필드를 가져야 하며 어떤 필드는 남기면 안 되는가
5. metric, log, trace는 서로 어떤 책임을 가져야 하는가
6. OpenTelemetry를 도입할 때 처음부터 과하게 설계하지 않으려면 어디서 시작해야 하는가
7. 운영 비용, 보안, 디버깅 편의성 사이의 트레이드오프는 무엇인가

핵심 결론부터 말하면 이렇다.

**Python 관측 가능성의 핵심은 로그를 문자열 기록으로 보는 것이 아니라, 요청 생명주기와 실패 원인을 재구성할 수 있는 구조화된 사건으로 다루는 것이다.**

로그는 "무슨 일이 있었다"를 남긴다. Metric은 "얼마나 자주, 얼마나 오래, 얼마나 많이"를 보여 준다. Trace는 "하나의 흐름이 어디를 지나갔는지"를 보여 준다. 세 가지를 섞어 쓰면 안 된다. 대신 공통 식별자와 일관된 event model로 연결해야 한다.

---

## 먼저 큰 그림: 운영 관측은 세 가지 질문으로 나뉜다

관측 가능성을 설계할 때 가장 먼저 나눠야 할 질문은 아래 세 가지다.

1. 무엇이 일어났는가: log
2. 얼마나 자주 또는 오래 일어났는가: metric
3. 한 요청이 어떤 경로를 지나갔는가: trace

세 질문은 비슷해 보이지만 답하는 방식이 다르다.

### Log: 개별 사건의 설명

로그는 사건의 기록이다.

```json
{
  "level": "INFO",
  "event": "payment.authorized",
  "request_id": "req_01J...",
  "tenant_id": "acme",
  "payment_id": "pay_123",
  "amount": 39000,
  "currency": "KRW",
  "duration_ms": 183
}
```

이 로그는 "결제가 승인됐다"는 사건을 설명한다. 운영자는 payment id나 request id로 관련 로그를 찾을 수 있다. 장애 분석에서는 개별 사건의 입력 조건, 상태 전이, 외부 호출 결과를 확인하는 데 유용하다.

다만 로그는 모든 것을 집계하는 도구가 아니다. `payment.authorized`가 1분에 몇 번 발생했는지, p95 latency가 얼마인지는 metric으로 보는 것이 더 적합하다. 로그를 쿼리해서 집계할 수는 있지만 비용이 크고 지연도 커지기 쉽다.

### Metric: 수치와 추세

Metric은 수치화된 신호다.

- 요청 수
- 에러 수
- latency histogram
- queue depth
- retry count
- DB pool 사용량
- external API timeout 비율

Metric은 알림과 대시보드에 강하다. "최근 5분 동안 5xx 비율이 3%를 넘었다" 같은 조건은 metric으로 잡아야 한다.

하지만 metric만으로는 개별 실패의 원인을 알기 어렵다. `payment_error_total{reason="timeout"}`이 증가했다는 사실은 알려 주지만, 어떤 request id가 실패했는지는 로그나 trace로 들어가야 한다.

### Trace: 흐름과 의존성

Trace는 하나의 요청이 여러 함수, 서비스, DB, 외부 API를 지나가는 경로를 span으로 표현한다.

```text
HTTP POST /payments
  validate_request
  load_user
  authorize_payment_gateway
  insert_payment
  publish_payment_event
```

Trace는 분산 시스템에서 특히 강하다. API 서버, worker, message broker, DB, 외부 API가 섞인 흐름에서 병목과 실패 위치를 보여 준다.

하지만 trace가 있다고 로그가 필요 없어지는 것은 아니다. Span에는 흐름과 시간 정보가 있고, 로그에는 사건의 의미와 business context가 있다. 좋은 설계는 둘을 연결한다.

---

## 핵심 개념 1: Python logging은 루트 로거에 대충 붙이면 나중에 꼬인다

Python 표준 `logging`은 오래됐지만 여전히 운영 코드의 기본이다. 문제는 기능이 약한 것이 아니라, 기본값을 그대로 쓰면 애플리케이션 규모가 커질수록 제어가 어려워진다는 점이다.

실무에서 먼저 정해야 할 것은 네 가지다.

1. logger namespace
2. handler
3. formatter
4. propagation

### logger namespace는 모듈 경로를 기본으로 한다

각 파일에서는 보통 아래처럼 logger를 만든다.

```python
import logging

logger = logging.getLogger(__name__)
```

`__name__`을 쓰면 logger 이름이 `app.services.payment`처럼 모듈 경로가 된다. 이 방식의 장점은 로그 레벨을 모듈 단위로 조절할 수 있다는 것이다.

예를 들어 결제 모듈만 debug로 올리고 싶다면 설정에서 `app.services.payment` 레벨만 바꿀 수 있다. 반대로 모든 코드가 `logging.getLogger("app")` 하나를 공유하면 어느 모듈에서 나온 로그인지 필드로 따로 넣어야 하고, 레벨 제어도 거칠어진다.

### handler는 출력 위치를 결정한다

컨테이너 환경에서는 보통 stdout/stderr로 내보내고, 수집기는 sidecar나 node agent가 담당한다. 애플리케이션이 직접 파일 rotation, 압축, 전송까지 맡으면 장애 지점이 늘어난다.

기본 정책은 단순하다.

- application log: stdout
- error log도 가능하면 stdout에 구조화해서 통합
- local 개발만 보기 좋은 console formatter 허용
- production은 JSON formatter 사용
- 애플리케이션 내부에서 장기 파일 보관을 책임지지 않음

### formatter는 사람이 보기 좋은 형식보다 기계가 읽기 좋은 형식을 우선한다

운영 환경에서는 문자열 로그보다 JSON 로그가 유리하다.

문자열 로그:

```text
payment failed user=123 amount=39000 reason=timeout
```

JSON 로그:

```json
{
  "event": "payment.failed",
  "user_id": "123",
  "amount": 39000,
  "reason": "timeout"
}
```

둘은 비슷해 보이지만 검색, 집계, masking, alert rule 작성에서는 차이가 크다. JSON 로그는 `event="payment.failed"`와 `reason="timeout"`을 필드로 다룰 수 있다. 문자열 로그는 파싱 규칙이 필요하고, 메시지 문구가 조금만 바뀌어도 깨질 수 있다.

### propagation은 중복 로그의 주범이다

Python logging에서 child logger는 기본적으로 parent logger로 로그를 전파한다. 라이브러리와 애플리케이션 설정이 섞이면 같은 로그가 두 번 찍히는 일이 흔하다.

예를 들어 `app` logger와 root logger에 모두 handler가 붙어 있고 propagation이 켜져 있으면 로그가 중복 출력될 수 있다.

운영에서는 보통 아래 원칙을 둔다.

- root logger에는 최소 handler 하나만 둔다
- 애플리케이션 logger에 별도 handler를 붙인다면 propagation을 명확히 제어한다
- 라이브러리 logger 레벨은 설정으로 낮추거나 올린다
- `basicConfig()`를 여러 곳에서 호출하지 않는다

`basicConfig()`는 작은 스크립트에는 편하지만 애플리케이션에서는 중앙 설정 한 곳으로 모으는 편이 낫다.

---

## 핵심 개념 2: 구조화 로그의 event 이름은 문장이 아니라 안정적인 식별자여야 한다

로그 메시지를 이렇게 남기는 코드를 자주 본다.

```python
logger.info("Payment authorized successfully")
logger.warning("Payment authorization failed")
```

사람이 보기에는 괜찮지만, 시간이 지나면 문제가 생긴다.

- 문구가 바뀌면 검색 조건이 깨진다
- 한글/영문 혼용으로 집계가 어렵다
- 같은 사건을 여러 표현으로 남긴다
- alert rule이 메시지 문자열에 의존한다

운영 로그에서는 `event` 필드를 안정적인 식별자로 두는 것이 좋다.

```python
logger.info(
    "payment.authorized",
    extra={
        "event": "payment.authorized",
        "payment_id": payment.id,
        "user_id": user.id,
        "amount": payment.amount,
        "duration_ms": duration_ms,
    },
)
```

메시지와 event를 둘 다 넣을 수도 있지만, 검색과 집계의 기준은 event여야 한다. event 이름은 가능하면 아래 규칙을 따른다.

- `domain.action` 또는 `domain.resource.action` 형태
- 과거형과 현재형을 섞지 않음
- 성공과 실패를 구분해야 하면 별도 event로 둠
- 너무 세부적인 함수명보다 운영 사건 기준으로 이름 붙임

예시:

- `auth.login.succeeded`
- `auth.login.failed`
- `payment.authorization.requested`
- `payment.authorization.failed`
- `order.status_changed`
- `webhook.delivery.retried`
- `worker.job.started`
- `worker.job.failed`

반대로 이런 event는 좋지 않다.

- `success`
- `failed`
- `process`
- `do_payment`
- `error_occurred`

event는 로그의 API다. 한번 대시보드, 알림, 검색 쿼리에 쓰이기 시작하면 쉽게 바꾸기 어렵다.

---

## 핵심 개념 3: ContextVar는 요청 context를 전역 변수처럼 쓰기 위한 도구가 아니다

요청 단위 context를 로그에 넣으려면 모든 함수에 `request_id`, `user_id`, `tenant_id`를 인자로 넘기는 방식이 가장 명시적이다.

```python
def create_order(command: CreateOrder, request_id: str, user_id: str) -> Order:
    ...
```

하지만 실제 서비스에서는 깊은 호출 구조 전체에 관측용 인자를 계속 넘기는 것이 부담스럽다. 이때 Python의 `contextvars.ContextVar`가 유용하다.

`ContextVar`는 thread-local과 비슷해 보이지만 `asyncio` task context를 이해한다. FastAPI 같은 async 환경에서 request별 값을 보존하기에 적합하다.

기본 예시는 아래와 같다.

```python
from contextvars import ContextVar

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
tenant_id_var: ContextVar[str | None] = ContextVar("tenant_id", default=None)
user_id_var: ContextVar[str | None] = ContextVar("user_id", default=None)


def get_log_context() -> dict[str, str]:
    context: dict[str, str] = {}
    if request_id := request_id_var.get():
        context["request_id"] = request_id
    if tenant_id := tenant_id_var.get():
        context["tenant_id"] = tenant_id
    if user_id := user_id_var.get():
        context["user_id"] = user_id
    return context
```

Middleware에서 값을 세팅한다.

```python
from uuid import uuid4
from fastapi import Request


@app.middleware("http")
async def bind_request_context(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or f"req_{uuid4().hex}"
    request_token = request_id_var.set(request_id)

    tenant_id = request.headers.get("x-tenant-id")
    tenant_token = tenant_id_var.set(tenant_id)

    try:
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response
    finally:
        tenant_id_var.reset(tenant_token)
        request_id_var.reset(request_token)
```

중요한 점은 `set()`이 token을 반환하고, `finally`에서 `reset()`해야 한다는 것이다. reset하지 않으면 long-lived worker나 test 환경에서 context가 새 작업으로 새어 나갈 수 있다.

### ContextVar를 logger adapter와 연결하기

표준 logging에서 context를 자동으로 붙이려면 `logging.Filter`를 사용할 수 있다.

```python
import logging


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        for key, value in get_log_context().items():
            setattr(record, key, value)
        return True
```

JSON formatter를 쓰면 record의 custom attribute를 필드로 출력할 수 있다. 직접 formatter를 만들 수도 있고, `python-json-logger`, `structlog`, `loguru` 같은 도구를 선택할 수도 있다.

중요한 것은 도구가 아니라 정책이다.

- 모든 로그에 `request_id`를 붙인다
- 인증 이후에는 가능한 범위에서 `user_id` 또는 `subject_id`를 붙인다
- multi-tenant 서비스라면 `tenant_id`를 붙인다
- background job에서는 `job_id`, `queue`, `attempt`를 붙인다
- message consumer에서는 `message_id`, `correlation_id`를 붙인다

### ContextVar의 함정

`ContextVar`는 편하지만 남용하면 안 된다.

첫째, 비즈니스 로직에 필요한 값은 명시적 인자로 전달해야 한다. `tenant_id`가 권한 판단이나 DB schema 선택에 필요하다면 context에서 몰래 꺼내기보다 command나 dependency에 명확히 담는 편이 안전하다. 관측용 context와 비즈니스 결정용 context를 섞으면 테스트와 재사용이 어려워진다.

둘째, 새 thread나 process로 넘어가면 context가 자동 전파되지 않을 수 있다. `asyncio` task 안에서는 잘 유지되지만, thread pool executor, Celery worker, multiprocessing, subprocess에서는 별도 전달이 필요하다.

셋째, context가 너무 많아지면 모든 로그가 비대해진다. request id, tenant id, user id, trace id 정도는 유용하지만, request body 전체나 permission 목록 같은 큰 객체를 context에 넣으면 비용과 보안 위험이 커진다.

---

## 핵심 개념 4: 예외 체인을 보존하지 않는 로그는 원인을 지운다

Python에서 예외를 변환할 때 흔히 이런 코드를 쓴다.

```python
try:
    user = gateway.fetch_user(user_id)
except TimeoutError:
    raise UserLookupFailed("사용자 조회 실패")
```

이 코드는 `UserLookupFailed`라는 도메인 예외로 바꾸는 점은 좋지만, 원인이 되는 `TimeoutError`를 명시적으로 연결하지 않았다. Python은 일부 context를 보여 주기도 하지만, 의도를 분명히 하려면 `raise ... from ...`을 써야 한다.

```python
try:
    user = gateway.fetch_user(user_id)
except TimeoutError as exc:
    raise UserLookupFailed("사용자 조회 실패") from exc
```

이렇게 하면 traceback에 직접 원인(`__cause__`)이 보존된다. 운영에서 매우 중요하다. 도메인 계층에서는 "사용자 조회 실패"가 맞지만, 장애 대응에서는 원인이 timeout인지, DNS 실패인지, 인증 실패인지, 응답 파싱 실패인지 알아야 한다.

### 예외 변환 기준

예외를 변환해야 하는 경우는 분명히 있다.

- 외부 라이브러리 예외를 애플리케이션 경계 밖으로 그대로 노출하고 싶지 않을 때
- infrastructure error를 domain 또는 application error로 분류하고 싶을 때
- API 응답 status code와 error code를 안정화하고 싶을 때
- retry 가능 여부를 명확히 표현하고 싶을 때

하지만 변환할 때 원인을 지우면 안 된다.

```python
class ExternalServiceError(RuntimeError):
    def __init__(self, service: str, operation: str, retryable: bool):
        self.service = service
        self.operation = operation
        self.retryable = retryable
        super().__init__(f"{service}.{operation} failed")


try:
    response = await client.post("/authorize", json=payload)
    response.raise_for_status()
except httpx.TimeoutException as exc:
    raise ExternalServiceError(
        service="payment_gateway",
        operation="authorize",
        retryable=True,
    ) from exc
except httpx.HTTPStatusError as exc:
    retryable = exc.response.status_code >= 500
    raise ExternalServiceError(
        service="payment_gateway",
        operation="authorize",
        retryable=retryable,
    ) from exc
```

이렇게 하면 상위 계층은 `ExternalServiceError.retryable`을 보고 재시도 정책을 결정할 수 있고, 로그에는 원래 httpx 예외와 status code를 함께 남길 수 있다.

### logger.exception은 except 블록 안에서만 의미가 있다

`logger.exception()`은 현재 exception 정보를 자동으로 포함한다. 따라서 except 블록 안에서 써야 한다.

```python
try:
    await service.create_order(command)
except OrderCreationFailed:
    logger.exception("order.creation.failed", extra={"event": "order.creation.failed"})
    raise
```

except 블록 밖에서 `logger.exception()`을 호출하면 현재 예외 정보가 없어 기대한 traceback이 남지 않는다.

예외를 로그로 남길 때도 기준이 필요하다. 모든 계층에서 같은 예외를 `logger.exception()`하면 같은 장애 하나가 여러 에러 로그로 중복된다. 보통은 "처리하지 못하고 경계를 넘어가는 지점"에서 한 번 error로 남긴다.

예를 들어 service 내부에서는 예외를 변환하고, API middleware에서 최종적으로 error log와 response 변환을 담당할 수 있다.

```python
@app.exception_handler(AppError)
async def handle_app_error(request: Request, exc: AppError):
    logger.warning(
        "app.error",
        extra={
            "event": "app.error",
            "error_code": exc.code,
            "retryable": exc.retryable,
        },
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.public_message},
    )
```

예상 가능한 사용자 오류는 warning이나 info일 수 있다. 모든 4xx를 error로 찍으면 error 알림의 신뢰도가 떨어진다. 반대로 예상하지 못한 5xx는 error로 남기고 traceback을 포함해야 한다.

---

## 핵심 개념 5: 로그 레벨은 감정 표현이 아니라 운영 계약이다

로그 레벨은 "이게 중요해 보인다" 정도로 정하면 안 된다. 레벨은 운영자가 어떻게 반응해야 하는지에 대한 계약이다.

실무 기준은 아래처럼 잡을 수 있다.

### DEBUG

개발 또는 임시 진단용 상세 정보다. 운영에서 항상 켜두면 비용이 커질 수 있다.

예시:

- SQL bind parameter 일부
- feature flag 평가 과정
- cache key 계산 세부
- retry backoff 계산값

주의할 점은 debug 로그에도 민감 정보가 들어가면 안 된다는 것이다. "운영에서는 debug를 안 켜니까 괜찮다"는 위험한 가정이다. 장애 때 debug를 켜는 순간 정보가 새어 나갈 수 있다.

### INFO

정상적인 상태 전이나 의미 있는 운영 사건이다.

예시:

- `order.created`
- `payment.authorized`
- `worker.job.completed`
- `webhook.delivery.succeeded`
- `model.loaded`

info는 너무 많아지기 쉽다. 모든 함수 시작/종료를 info로 찍으면 비용과 노이즈가 커진다. 사용자가 한 행동, 외부 side effect, 상태 전이, 작업 완료처럼 나중에 추적할 가치가 있는 사건을 기준으로 남기는 편이 좋다.

### WARNING

작업은 계속될 수 있지만 주의가 필요한 상태다.

예시:

- retry 후 성공
- fallback 사용
- validation 실패가 비정상적으로 많음
- 외부 API 429로 backoff
- idempotency key 중복 감지
- cache corrupt로 재생성

warning은 나중에 error로 커질 가능성이 있는 신호다. 운영자는 warning이 증가하는 추세를 볼 수 있어야 한다.

### ERROR

요청이나 작업이 실패했고 개입 또는 조사가 필요할 수 있는 상태다.

예시:

- 5xx response
- worker job 최종 실패
- 외부 API 호출 실패로 핵심 기능 실패
- DB transaction rollback
- message 처리 실패 후 DLQ 이동

error는 알림의 후보가 된다. 따라서 너무 많은 예상 가능한 사용자 오류를 error로 남기면 알림이 무너진다.

### CRITICAL

프로세스나 핵심 기능이 지속 불가능한 상태다.

예시:

- 애플리케이션 시작 실패
- 필수 설정 누락
- DB migration 불일치로 서비스 시작 중단
- 암호화 키 로드 실패

critical은 자주 쓰지 않는 편이 좋다. 자주 발생하는 critical은 이미 critical의 의미를 잃은 것이다.

---

## 실무 예시 1: FastAPI 요청 로그를 access log와 application log로 나누기

API 서버에서는 보통 두 종류의 로그가 필요하다.

1. access log: 요청 단위 요약
2. application log: 비즈니스 사건과 내부 처리

access log는 middleware에서 한 요청당 한 줄로 남긴다.

```python
import time
from uuid import uuid4
from fastapi import Request


@app.middleware("http")
async def access_log_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or f"req_{uuid4().hex}"
    token = request_id_var.set(request_id)
    started = time.perf_counter()

    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers["x-request-id"] = request_id
        return response
    finally:
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        logger.info(
            "http.request.completed",
            extra={
                "event": "http.request.completed",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "duration_ms": duration_ms,
                "client_host": request.client.host if request.client else None,
            },
        )
        request_id_var.reset(token)
```

여기서 중요한 점은 query string을 그대로 남기지 않는 것이다. query string에는 token, email, search keyword 같은 민감하거나 고카디널리티 정보가 들어갈 수 있다. 필요하다면 whitelist 방식으로 일부만 남긴다.

application log는 use case 안에서 의미 있는 사건을 남긴다.

```python
async def create_order(command: CreateOrderCommand) -> Order:
    order = Order.create(command)
    await order_repository.save(order)

    logger.info(
        "order.created",
        extra={
            "event": "order.created",
            "order_id": order.id,
            "user_id": order.user_id,
            "item_count": len(order.items),
            "total_amount": order.total_amount,
        },
    )

    return order
```

access log만 있으면 HTTP 요청이 성공했다는 사실은 알 수 있지만, 주문 id나 비즈니스 상태 전이를 찾기 어렵다. application log만 있으면 요청 전체 latency와 status code를 보기 어렵다. 둘은 역할이 다르다.

---

## 실무 예시 2: Worker 로그는 job id, attempt, idempotency key가 핵심이다

Background worker에서는 request id보다 job id와 message id가 중요하다.

예를 들어 결제 완료 이벤트를 받아 영수증을 발송하는 worker가 있다고 하자.

```python
async def handle_receipt_job(message: ReceiptMessage) -> None:
    job_token = job_id_var.set(message.job_id)
    attempt_token = attempt_var.set(str(message.attempt))

    try:
        logger.info(
            "receipt.job.started",
            extra={
                "event": "receipt.job.started",
                "job_id": message.job_id,
                "payment_id": message.payment_id,
                "attempt": message.attempt,
            },
        )

        await receipt_service.send_receipt(
            payment_id=message.payment_id,
            idempotency_key=message.idempotency_key,
        )

        logger.info(
            "receipt.job.completed",
            extra={
                "event": "receipt.job.completed",
                "job_id": message.job_id,
                "payment_id": message.payment_id,
                "attempt": message.attempt,
            },
        )
    except RetryableReceiptError:
        logger.warning(
            "receipt.job.retryable_failed",
            extra={
                "event": "receipt.job.retryable_failed",
                "job_id": message.job_id,
                "payment_id": message.payment_id,
                "attempt": message.attempt,
            },
            exc_info=True,
        )
        raise
    except Exception:
        logger.exception(
            "receipt.job.failed",
            extra={
                "event": "receipt.job.failed",
                "job_id": message.job_id,
                "payment_id": message.payment_id,
                "attempt": message.attempt,
            },
        )
        raise
    finally:
        attempt_var.reset(attempt_token)
        job_id_var.reset(job_token)
```

worker에서 특히 중요한 필드는 아래와 같다.

- `job_id`: 작업 단위 식별자
- `message_id`: broker message 식별자
- `correlation_id`: 원래 요청이나 upstream event와 연결하는 식별자
- `attempt`: 몇 번째 시도인지
- `idempotency_key`: 중복 처리 방지 기준
- `queue`: 어느 queue에서 왔는지
- `lease_ms` 또는 `visibility_timeout_ms`: broker의 재전달 조건과 관련된 값

worker 장애에서 가장 중요한 질문은 "이 작업이 다시 실행돼도 안전한가"다. 따라서 로그도 재시도와 멱등성 판단에 필요한 필드를 담아야 한다.

---

## 실무 예시 3: 외부 API 호출 로그는 요청 본문보다 결과 분류가 중요하다

외부 API 호출에서 흔한 실수는 request와 response를 통째로 로그에 남기는 것이다.

```python
logger.info("gateway request %s", payload)
logger.info("gateway response %s", response.text)
```

이 방식은 디버깅에는 편해 보이지만 운영에서는 위험하다.

- 개인정보가 섞일 수 있다
- 응답이 커지면 로그 비용이 급증한다
- 카드, 토큰, 주소 같은 민감 정보가 노출될 수 있다
- 로그 검색이 본문 문자열에 의존한다
- timeout이나 status code 분류가 어렵다

대신 호출 결과를 구조화한다.

```python
started = time.perf_counter()
try:
    response = await client.post("/payments/authorize", json=payload)
    response.raise_for_status()
except httpx.TimeoutException as exc:
    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    logger.warning(
        "external_api.timeout",
        extra={
            "event": "external_api.timeout",
            "service": "payment_gateway",
            "operation": "authorize",
            "duration_ms": duration_ms,
            "timeout_ms": 3000,
            "retryable": True,
        },
        exc_info=True,
    )
    raise PaymentGatewayTimeout(retryable=True) from exc
except httpx.HTTPStatusError as exc:
    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    status_code = exc.response.status_code
    logger.warning(
        "external_api.http_error",
        extra={
            "event": "external_api.http_error",
            "service": "payment_gateway",
            "operation": "authorize",
            "status_code": status_code,
            "duration_ms": duration_ms,
            "retryable": status_code >= 500,
        },
        exc_info=True,
    )
    raise PaymentGatewayError(retryable=status_code >= 500) from exc
```

본문이 꼭 필요하다면 원문 전체가 아니라 제한된 safe field만 남긴다. 예를 들어 gateway error code, request amount, currency, masked external id 정도다.

```python
logger.warning(
    "payment_gateway.declined",
    extra={
        "event": "payment_gateway.declined",
        "gateway_error_code": error.code,
        "gateway_error_group": classify_gateway_error(error.code),
        "amount": command.amount,
        "currency": command.currency,
        "payment_id": payment.id,
    },
)
```

운영 로그는 원문 재현보다 의사결정에 필요한 분류를 우선한다.

---

## OpenTelemetry는 무엇을 해결하고 무엇을 해결하지 않는가

OpenTelemetry는 로그, metric, trace를 위한 표준 instrumentation 체계다. Python에서는 `opentelemetry-api`, `opentelemetry-sdk`, 각종 instrumentation 패키지를 통해 FastAPI, requests/httpx, SQLAlchemy, Redis 등을 자동 계측할 수 있다.

OpenTelemetry가 해결하는 것은 주로 아래다.

- trace id, span id 생성과 전파
- HTTP, DB, messaging 같은 공통 라이브러리 자동 span 생성
- 서비스 간 context propagation
- vendor 독립적인 export
- metric과 trace의 공통 semantic convention

하지만 OpenTelemetry가 모든 관측 설계를 대신해주지는 않는다.

- 어떤 비즈니스 event를 로그로 남길지는 애플리케이션이 결정해야 한다
- 어떤 field가 민감 정보인지 도구가 자동으로 알 수 없다
- 예외를 어떤 도메인 error로 분류할지 정해주지 않는다
- 너무 많은 span과 attribute로 인한 비용 문제를 자동으로 해결하지 않는다
- 잘못된 로그 레벨 정책을 고쳐주지 않는다

즉 OpenTelemetry는 배관과 표준화에 강하고, 의미 설계는 여전히 애플리케이션 책임이다.

### 처음 도입할 때의 현실적인 순서

처음부터 모든 것을 계측하려고 하면 대부분 실패한다. 현실적인 순서는 아래가 좋다.

1. 모든 요청에 `request_id`를 부여하고 로그에 포함한다
2. JSON 구조화 로그를 도입한다
3. error handling middleware에서 5xx와 예상 가능한 app error를 분리한다
4. 외부 API, DB, worker job의 핵심 event를 표준화한다
5. OpenTelemetry trace를 HTTP server와 HTTP client부터 붙인다
6. trace id와 log field를 연결한다
7. 주요 metric을 SLI 기준으로 추가한다

trace를 먼저 붙여도 된다. 하지만 로그가 문자열이고 error 분류가 엉켜 있으면 trace만으로 장애 대응이 충분하지 않다. 반대로 구조화 로그가 먼저 정리되어 있으면 trace 도입 효과가 훨씬 커진다.

### trace id를 로그에 넣기

OpenTelemetry를 쓰면 현재 span context에서 trace id를 가져와 로그 필드에 넣을 수 있다.

```python
from opentelemetry import trace


def get_trace_context() -> dict[str, str]:
    span = trace.get_current_span()
    span_context = span.get_span_context()
    if not span_context.is_valid:
        return {}

    return {
        "trace_id": format(span_context.trace_id, "032x"),
        "span_id": format(span_context.span_id, "016x"),
    }
```

이 값을 logging filter에서 context field로 추가하면 로그에서 trace 화면으로 이동할 수 있다.

```python
class ObservabilityFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        for key, value in get_log_context().items():
            setattr(record, key, value)
        for key, value in get_trace_context().items():
            setattr(record, key, value)
        return True
```

이 연결이 있으면 운영자는 error log 한 줄에서 trace id를 복사해 전체 요청 경로를 볼 수 있다. 분산 시스템에서는 이 차이가 매우 크다.

---

## 트레이드오프 1: 구조화 로그는 검색이 쉬워지지만 스키마 관리가 필요하다

구조화 로그를 도입하면 필드 기반 검색과 집계가 쉬워진다. 하지만 자유도가 높아져서 팀마다 필드 이름이 달라질 수 있다.

예를 들어 같은 의미를 아래처럼 제각각 남기면 곤란하다.

- `request_id`
- `req_id`
- `x_request_id`
- `correlationId`
- `correlation_id`

처음부터 완벽한 스키마가 필요하지는 않지만 최소 공통 필드는 정해야 한다.

권장 공통 필드:

- `timestamp`
- `level`
- `logger`
- `event`
- `message`
- `request_id`
- `trace_id`
- `span_id`
- `tenant_id`
- `user_id`
- `job_id`
- `duration_ms`
- `error_type`
- `error_code`
- `retryable`

필드 이름은 snake_case로 통일하는 편이 Python 코드와 잘 맞는다. 다만 사용하는 로그 플랫폼의 convention이 있다면 맞춰도 된다. 핵심은 일관성이다.

### 고카디널리티 필드 주의

로그에는 고카디널리티 필드를 넣어도 metric보다는 부담이 덜하지만, 그래도 비용과 인덱싱 문제가 생길 수 있다.

특히 metric label에는 user id, email, request id 같은 값을 넣으면 안 된다. label cardinality가 폭발한다.

로그에는 request id가 필요하지만 metric label에는 보통 넣지 않는다.

좋은 metric label:

- endpoint pattern: `/orders/{order_id}`
- method: `POST`
- status_class: `5xx`
- error_code: `PAYMENT_TIMEOUT`
- service: `payment_gateway`

위험한 metric label:

- user_id
- email
- raw path
- request_id
- full exception message
- idempotency_key

로그, metric, trace는 서로 필드 기준이 다르다. 같은 값을 모든 곳에 넣는 것이 좋은 설계는 아니다.

---

## 트레이드오프 2: 로그를 자세히 남길수록 보안과 비용 위험이 커진다

운영 장애를 겪고 나면 "앞으로 더 자세히 남기자"는 결론이 나오기 쉽다. 하지만 로그는 비용과 보안의 덩어리이기도 하다.

로그에 남기면 위험한 값은 아래와 같다.

- 비밀번호
- access token, refresh token
- API key
- session cookie
- 주민등록번호, 여권번호 같은 강한 식별자
- 카드번호, CVC
- 이메일, 전화번호, 주소 등 개인정보
- 인증 header 전체
- 외부 API request/response 원문

필요한 경우 masking 또는 hashing을 쓴다.

```python
import hashlib


def hash_identifier(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def mask_email(email: str) -> str:
    name, _, domain = email.partition("@")
    if not domain:
        return "***"
    return f"{name[:2]}***@{domain}"
```

하지만 masking도 만능은 아니다. 가장 좋은 보안 로그 정책은 민감 정보를 애초에 로그 경계에 넣지 않는 것이다.

### 비용을 줄이는 방법

로그 비용은 대체로 volume, retention, index field 수에 의해 커진다.

실무적으로는 아래 정책이 도움이 된다.

- 정상 요청 access log는 한 요청당 한 줄로 제한한다
- health check, metrics scrape 같은 noise endpoint는 별도 sampling 또는 제외한다
- debug 로그는 동적 레벨 조정이 가능하게 하되 기본 off로 둔다
- 대량 batch에서는 item마다 info를 남기지 말고 chunk 요약을 남긴다
- 실패한 item은 sample 없이 남기되, 성공 item은 summary metric으로 대체한다
- 큰 payload는 size, hash, schema version 정도만 남긴다
- 로그 retention을 레벨과 인덱스 필요성에 따라 나눈다

예를 들어 매일 100만 개 item을 처리하는 batch에서 item 성공 로그를 모두 남기면 비용은 빠르게 커진다. 이때는 chunk 단위 요약이 더 낫다.

```python
logger.info(
    "batch.chunk.completed",
    extra={
        "event": "batch.chunk.completed",
        "batch_id": batch_id,
        "chunk_index": chunk_index,
        "item_count": len(items),
        "success_count": success_count,
        "failure_count": failure_count,
        "duration_ms": duration_ms,
    },
)
```

개별 실패는 별도 warning/error로 남기되, 성공은 집계한다.

---

## 트레이드오프 3: 라이브러리 선택보다 팀 운영 규칙이 더 중요하다

Python logging 생태계에는 여러 선택지가 있다.

- 표준 `logging`
- `structlog`
- `loguru`
- `python-json-logger`
- OpenTelemetry logging integration

개인적으로 운영 서비스에서는 표준 logging을 중심에 두고, JSON formatter나 structlog를 붙이는 방식을 선호한다. 이유는 라이브러리 호환성 때문이다. 대부분의 Python 라이브러리는 표준 logging을 사용한다. 표준 logging 경로를 유지하면 uvicorn, SQLAlchemy, httpx, boto3 같은 로그도 같은 수집 파이프라인에 태우기 쉽다.

`structlog`는 구조화 로그를 팀 표준으로 강제하기 좋다. context binding, processor chain, JSON rendering이 명확하다. 다만 팀이 logging 기본 동작을 이해하지 못한 상태에서 도입하면 표준 logging과 structlog가 이중으로 얽혀 중복 로그나 누락이 생길 수 있다.

`loguru`는 작은 앱이나 CLI에서 개발 경험이 좋다. 하지만 큰 서비스에서는 표준 logging과의 bridge, 라이브러리 로그 통합, 운영 설정 제어를 신중히 봐야 한다.

결론은 단순하다.

- 작은 스크립트: 표준 logging 또는 loguru로 충분
- FastAPI 운영 서비스: 표준 logging + JSON formatter + context filter부터 시작
- 구조화 로그 규칙을 강하게 밀고 싶음: structlog 고려
- 분산 trace가 필요함: OpenTelemetry를 logging과 연결

도구를 바꾼다고 관측 가능성이 자동으로 생기지는 않는다. event 이름, 필드 정책, 예외 분류, 로그 레벨 계약이 먼저다.

---

## 흔한 실수 1: 예외를 잡고 로그만 남긴 뒤 계속 진행한다

가장 위험한 패턴 중 하나는 이것이다.

```python
try:
    charge_payment(order)
except Exception:
    logger.exception("payment failed")

ship_order(order)
```

결제 실패를 로그로 남겼지만 처리는 계속 진행된다. 로그는 제어 흐름이 아니다. 실패를 복구할 수 없다면 다시 raise해야 한다.

```python
try:
    charge_payment(order)
except PaymentError:
    logger.exception("payment.failed", extra={"event": "payment.failed"})
    raise
```

예외를 삼켜도 되는 경우는 매우 제한적이다.

- best-effort 알림 발송
- metric 전송 실패
- cleanup 중 일부 부가 작업
- fallback이 명확히 정의된 경우

그런 경우에도 로그에는 fallback 여부와 영향도를 남겨야 한다.

---

## 흔한 실수 2: request body 전체를 에러 로그에 남긴다

디버깅을 위해 request body를 남기고 싶은 마음은 이해된다. 하지만 운영에서는 위험하다.

```python
logger.error("invalid request: %s", await request.body())
```

이 코드는 개인정보, 토큰, 파일 내용, 대용량 payload를 그대로 남길 수 있다. 대신 validation error의 구조와 safe field만 남긴다.

```python
logger.info(
    "request.validation_failed",
    extra={
        "event": "request.validation_failed",
        "path": request.url.path,
        "method": request.method,
        "error_count": len(errors),
        "error_fields": [err["loc"] for err in errors[:10]],
    },
)
```

원문 payload가 정말 필요하다면 운영 로그가 아니라 보안 통제된 별도 저장소에 짧은 retention으로 저장하고, 접근 권한과 masking을 적용해야 한다.

---

## 흔한 실수 3: logger를 함수 인자로 계속 넘긴다

테스트하기 쉽게 하려는 의도로 logger를 함수 인자로 넘기는 경우가 있다.

```python
def create_order(command: CreateOrder, logger: logging.Logger) -> Order:
    logger.info("...")
```

대부분의 애플리케이션 코드에서는 필요 없다. 모듈 logger를 쓰면 된다.

```python
logger = logging.getLogger(__name__)


def create_order(command: CreateOrder) -> Order:
    logger.info("order.create.requested", extra={"event": "order.create.requested"})
```

logger를 인자로 넘기면 비즈니스 함수 signature가 관측 도구에 오염된다. 테스트에서는 logging capture 기능을 쓰거나, 더 중요한 비즈니스 결과를 검증하는 편이 낫다.

단, 라이브러리 코드나 SDK처럼 호출자가 logging 정책을 제어해야 하는 경우에는 logger injection이 의미 있을 수 있다. 애플리케이션 내부 코드와 배포 가능한 라이브러리는 기준이 다르다.

---

## 흔한 실수 4: 문자열 포맷팅으로 로그 비용을 미리 써버린다

Python logging은 lazy formatting을 지원한다.

좋은 예:

```python
logger.debug("cache candidate keys=%s", candidate_keys)
```

나쁜 예:

```python
logger.debug(f"cache candidate keys={candidate_keys}")
```

f-string은 debug 레벨이 꺼져 있어도 문자열 생성 비용을 먼저 낸다. 작은 값은 큰 문제가 아니지만, 큰 객체를 직렬화하거나 비싼 함수를 호출하면 문제가 된다.

구조화 로그에서도 마찬가지다. 로그 레벨이 꺼져 있을 때 비싼 extra 계산을 피해야 한다.

```python
if logger.isEnabledFor(logging.DEBUG):
    logger.debug(
        "ranking.debug_features",
        extra={
            "event": "ranking.debug_features",
            "features": build_expensive_debug_features(item),
        },
    )
```

---

## 흔한 실수 5: 에러 로그와 metric 알림의 기준이 다르다

로그에서는 `payment.failed`를 error로 남기지만 metric은 `gateway_timeout`으로 세고, trace span status는 OK로 남기는 경우가 있다. 그러면 대시보드, 로그, trace가 서로 다른 이야기를 한다.

에러 분류는 공통 모델을 가져야 한다.

예를 들어 아래처럼 error code를 정한다.

- `PAYMENT_GATEWAY_TIMEOUT`
- `PAYMENT_GATEWAY_DECLINED`
- `ORDER_CONFLICT`
- `AUTH_TOKEN_EXPIRED`
- `RATE_LIMITED`

이 error code를 response, log, metric label, trace attribute에 일관되게 쓴다.

```python
logger.warning(
    "payment.failed",
    extra={
        "event": "payment.failed",
        "error_code": "PAYMENT_GATEWAY_TIMEOUT",
        "retryable": True,
    },
)
payment_failed_total.labels(error_code="PAYMENT_GATEWAY_TIMEOUT").inc()
span.set_attribute("app.error_code", "PAYMENT_GATEWAY_TIMEOUT")
```

모든 필드를 똑같이 넣으라는 뜻이 아니다. 핵심 분류값은 공유해야 한다는 뜻이다.

---

## 체크리스트: Python 서비스 관측 가능성 점검

아래 항목은 새 서비스나 운영 전 점검에서 그대로 사용할 수 있다.

- [ ] 모든 HTTP 요청에 `request_id`가 있고 response header로도 돌려준다
- [ ] background job에는 `job_id`, `message_id`, `attempt`가 있다
- [ ] 로그는 production에서 JSON으로 출력된다
- [ ] `event` 필드는 안정적인 식별자로 관리된다
- [ ] 공통 필드 이름이 문서화되어 있다
- [ ] request body, response body, token, cookie를 기본 로그에 남기지 않는다
- [ ] 민감 정보 masking 또는 제외 정책이 있다
- [ ] 4xx, expected app error, unexpected 5xx의 로그 레벨이 구분된다
- [ ] 예외 변환 시 `raise ... from ...`으로 원인을 보존한다
- [ ] `logger.exception()`은 처리 경계에서 중복 없이 사용한다
- [ ] 외부 API 호출은 service, operation, status_code, duration_ms, retryable을 남긴다
- [ ] DB나 cache 장애는 operation과 duration을 남긴다
- [ ] timeout과 cancellation은 일반 error와 구분된다
- [ ] retry 로그에는 attempt, max_attempts, backoff_ms가 있다
- [ ] worker 실패 로그에는 ack/nack/DLQ 결과가 드러난다
- [ ] metric label에 user id, request id, email 같은 고카디널리티 값을 넣지 않는다
- [ ] trace id와 span id를 로그에서 찾을 수 있다
- [ ] health check와 noise endpoint 로그를 별도 처리한다
- [ ] debug 로그에도 민감 정보가 들어가지 않는다
- [ ] 로그 retention과 sampling 정책이 비용 기준에 맞게 정해져 있다

---

## 실무 설계 예시: 최소 관측 패키지 구성

작은 팀에서 바로 시작할 수 있는 구성은 아래 정도면 충분하다.

```text
app/
  observability/
    __init__.py
    context.py
    logging.py
    errors.py
  main.py
  services/
    order_service.py
```

`context.py`

```python
from contextvars import ContextVar

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
tenant_id_var: ContextVar[str | None] = ContextVar("tenant_id", default=None)
user_id_var: ContextVar[str | None] = ContextVar("user_id", default=None)
job_id_var: ContextVar[str | None] = ContextVar("job_id", default=None)


def collect_context() -> dict[str, str]:
    result: dict[str, str] = {}
    for key, var in {
        "request_id": request_id_var,
        "tenant_id": tenant_id_var,
        "user_id": user_id_var,
        "job_id": job_id_var,
    }.items():
        value = var.get()
        if value:
            result[key] = value
    return result
```

`logging.py`

```python
import json
import logging
from datetime import datetime, timezone

from app.observability.context import collect_context


class JsonFormatter(logging.Formatter):
    RESERVED = {
        "args", "asctime", "created", "exc_info", "exc_text", "filename",
        "funcName", "levelname", "levelno", "lineno", "module", "msecs",
        "message", "msg", "name", "pathname", "process", "processName",
        "relativeCreated", "stack_info", "thread", "threadName",
    }

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        payload.update(collect_context())

        for key, value in record.__dict__.items():
            if key not in self.RESERVED and not key.startswith("_"):
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
```

이 정도만 있어도 production 로그의 품질은 크게 올라간다. 이후 OpenTelemetry trace context를 `JsonFormatter`에 추가하거나, structlog로 교체할 수 있다.

중요한 점은 이 코드 자체가 완성형이 아니라 시작점이라는 것이다. 운영 환경에서는 로그 플랫폼, 보안 정책, 성능 요구에 맞춰 formatter와 masking을 보강해야 한다.

---

## 한 단계 더: 에러 분류를 코드로 고정하기

관측 가능성은 에러 분류와 함께 설계할 때 강해진다.

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class ErrorSpec:
    code: str
    status_code: int
    retryable: bool
    log_level: int


PAYMENT_GATEWAY_TIMEOUT = ErrorSpec(
    code="PAYMENT_GATEWAY_TIMEOUT",
    status_code=502,
    retryable=True,
    log_level=logging.WARNING,
)

ORDER_CONFLICT = ErrorSpec(
    code="ORDER_CONFLICT",
    status_code=409,
    retryable=False,
    log_level=logging.INFO,
)
```

애플리케이션 예외가 이 spec을 들고 있으면 response, log, metric이 같은 기준을 공유할 수 있다.

```python
class AppError(Exception):
    def __init__(self, spec: ErrorSpec, public_message: str):
        self.spec = spec
        self.public_message = public_message
        super().__init__(public_message)
```

Exception handler에서 일관되게 처리한다.

```python
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    logger.log(
        exc.spec.log_level,
        "app.error",
        extra={
            "event": "app.error",
            "error_code": exc.spec.code,
            "retryable": exc.spec.retryable,
            "status_code": exc.spec.status_code,
        },
        exc_info=exc.spec.status_code >= 500,
    )
    return JSONResponse(
        status_code=exc.spec.status_code,
        content={
            "code": exc.spec.code,
            "message": exc.public_message,
            "request_id": request_id_var.get(),
        },
    )
```

이 방식의 장점은 에러 정책이 흩어지지 않는다는 것이다. 단점은 초기에는 다소 무겁게 느껴질 수 있다는 점이다. 작은 프로젝트에서는 enum과 간단한 exception class로 시작해도 된다. 핵심은 error code와 retryable 여부, log level이 매번 즉흥적으로 정해지지 않게 하는 것이다.

---

## 운영에서 바로 쓰는 로그 이벤트 예시

아래는 실무에서 자주 필요한 event 예시다.

HTTP:

- `http.request.completed`
- `http.request.validation_failed`
- `http.request.rate_limited`
- `http.request.unauthorized`
- `http.request.unhandled_exception`

인증:

- `auth.login.succeeded`
- `auth.login.failed`
- `auth.token.expired`
- `auth.permission.denied`

DB:

- `db.transaction.committed`
- `db.transaction.rolled_back`
- `db.query.slow`
- `db.pool.exhausted`

외부 API:

- `external_api.request.completed`
- `external_api.timeout`
- `external_api.http_error`
- `external_api.response_invalid`

Worker:

- `worker.job.started`
- `worker.job.completed`
- `worker.job.retryable_failed`
- `worker.job.failed`
- `worker.job.sent_to_dlq`

도메인:

- `order.created`
- `order.status_changed`
- `payment.authorized`
- `payment.failed`
- `webhook.delivery.succeeded`
- `webhook.delivery.failed`

이 목록을 그대로 쓰라는 뜻은 아니다. 중요한 것은 팀이 event namespace를 관리한다는 점이다. event 이름이 쌓이면 그것이 곧 운영 언어가 된다.

---

## 마무리: 좋은 로그는 장애가 난 뒤에 읽는 문서다

Python에서 관측 가능성을 설계한다는 것은 로깅 라이브러리를 하나 고르는 일이 아니다. 요청, 작업, 예외, 외부 의존성, 상태 전이를 어떤 증거로 남길지 정하는 일이다.

좋은 로그는 평소에는 조용히 쌓이다가 장애가 났을 때 아래 질문에 답해준다.

- 어떤 요청에서 시작됐는가
- 어느 사용자나 tenant에 영향이 있었는가
- 어떤 외부 의존성이 실패했는가
- 재시도 가능한 실패인가, 즉시 수정해야 하는 데이터 문제인가
- 같은 흐름의 trace는 어디에 있는가
- 이전 배포 전후로 증가했는가
- 민감 정보를 노출하지 않으면서도 원인을 좁힐 수 있는가

이 질문에 답하지 못하는 로그는 많아도 부족하다. 반대로 이 질문에 답할 수 있는 로그는 적어도 강하다.

한 줄 정리:

**Python 운영 로그는 `print()`의 확장이 아니라, request context, exception chain, structured event, trace id를 연결해 장애 원인을 재구성하는 증거 시스템으로 설계해야 한다.**
