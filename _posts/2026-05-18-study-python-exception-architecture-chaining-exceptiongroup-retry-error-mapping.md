---
layout: post
title: "Python 예외 처리 아키텍처 실전: Exception Chaining, ExceptionGroup, Retry 경계, Error Mapping으로 장애를 숨기지 않는 법"
date: 2026-05-18 11:40:00 +0900
categories: [python]
tags: [study, python, exception-handling, exception-chaining, exceptiongroup, retry, fastapi, architecture, error-mapping, observability]
permalink: /python/2026/05/18/study-python-exception-architecture-chaining-exceptiongroup-retry-error-mapping.html
---

## 배경: Python 예외 처리는 문법 문제가 아니라 장애를 어디서 설명할지에 대한 아키텍처 문제다

Python 팀이 커질수록 비슷한 문제가 반복된다.

- 외부 API timeout이 났는데 서비스에서는 그냥 `RuntimeError` 하나로 뭉개진다
- 데이터 검증 실패와 DB 연결 실패가 같은 500으로 나간다
- retry를 붙였더니 오히려 중복 결제와 중복 적재가 늘어난다
- 로그는 많은데 "왜 실패했는지"보다 "어디서 또 잡아먹혔는지" 찾는 데 시간이 더 든다
- 배치에서는 1000건 중 7건만 실패했는데 전체 예외 메시지 하나만 남아 재처리 기준을 세우기 어렵다
- FastAPI, worker, CLI가 각자 다른 예외 스타일을 써서 같은 장애가 표면마다 다르게 보인다

초기에는 `try/except`를 몇 줄 더 넣으면 해결되는 것처럼 보인다.
하지만 서비스가 커지면 예외 처리는 더 이상 로컬 코드 습관이 아니다.

> 예외는 실패를 표현하는 문법이 아니라, **경계마다 어떤 실패를 어떤 의미로 번역할지 정하는 계약**이다.

실무에서 중요한 질문은 아래에 가깝다.

1. 어떤 실패를 도메인 규칙 위반으로 볼 것인가
2. 어떤 실패를 일시 장애로 보고 retry할 것인가
3. 어떤 실패를 사용자에게 그대로 보여 주면 안 되는가
4. 병렬 작업의 여러 실패를 하나로 어떻게 묶을 것인가
5. 로그에는 원인을 얼마나 남기고, API 응답에는 얼마나 숨길 것인가
6. FastAPI, worker, CLI, batch가 같은 실패를 각자 어떻게 매핑할 것인가

오늘 글은 Python 3.11+ 기준으로 아래를 실무 관점에서 정리한다.

- 예외를 계층별 계약으로 분류하는 법
- `raise ... from ...` 로 원인 체인을 보존하는 법
- retry를 붙여도 되는 예외와 붙이면 안 되는 예외를 나누는 기준
- `ExceptionGroup`과 `except*`를 병렬 처리에서 언제 써야 하는지
- FastAPI, 배치, consumer에서 error mapping을 어디에 둬야 하는지
- 흔한 실수와 운영 체크리스트

핵심 결론만 먼저 말하면 이렇다.

- 예외 계층이 없으면 retry, 로그, API 응답이 전부 흔들린다
- 원인 체인을 잃어버리면 장애는 해결보다 추측의 영역이 된다
- retry는 예외 처리 옵션이 아니라 **정합성 정책**이다
- 병렬 처리 시대에는 단일 예외만 가정한 설계가 금방 한계에 부딪힌다
- 좋은 예외 처리는 에러를 많이 잡는 코드가 아니라 **실패를 의미 있게 번역하는 구조**다

---

## 먼저 큰 그림: 예외는 "잡는 기술"보다 "올려보내는 구조"가 더 중요하다

많은 코드베이스가 예외 처리를 아래처럼 이해한다.

- 터지면 `except`로 잡는다
- 로그 남긴다
- 필요하면 새 예외로 바꾼다

이 접근이 위험한 이유는 실패가 이동하는 경로를 설계하지 않기 때문이다.

실무 시스템에서 실패는 보통 이런 경로를 탄다.

- 인프라 계층: socket timeout, DNS 실패, DB deadlock, unique violation
- 애플리케이션 계층: 주문이 이미 확정됨, 재시도 예산 초과, 요청 상태 불일치
- 어댑터 계층: HTTP 409, HTTP 503, CLI exit code 2, queue nack
- 관측 계층: 로그, 메트릭, trace tag, error group

즉 예외는 던지는 순간 끝나는 게 아니라 **경계를 통과하면서 의미가 바뀐다**.

그래서 내가 추천하는 기본 원칙은 단순하다.

1. **가장 안쪽에서는 구체 원인을 잃지 않는다**
2. **중간 계층에서는 도메인 의미로 번역한다**
3. **가장 바깥에서는 채널별 응답 형식으로 매핑한다**
4. **같은 예외를 여러 계층에서 중복 로깅하지 않는다**

이 네 줄이 예외 처리 품질의 대부분을 결정한다.

---

## 핵심 개념 1: 예외를 기술 스택이 아니라 책임 경계 기준으로 분류해야 한다

실무에서 제일 먼저 무너지는 부분은 예외 이름이 아니라 **분류 기준**이다.

예외 분류를 라이브러리 이름 기준으로 두면 금방 흔들린다.

- `httpx.ReadTimeout`
- `psycopg.errors.UniqueViolation`
- `botocore.exceptions.ClientError`

이런 예외는 원인 파악에는 좋지만, 애플리케이션 정책을 직접 담기에는 너무 구체적이다.

그래서 서비스 코어에서는 보통 아래 정도의 계층이 더 오래 산다.

```python
class AppError(Exception):
    """애플리케이션 전반의 베이스 예외"""


class DomainError(AppError):
    """비즈니스 규칙 위반"""


class ValidationError(AppError):
    """입력 자체가 잘못됨"""


class TransientInfraError(AppError):
    """재시도 가능성이 있는 일시 장애"""


class PermanentInfraError(AppError):
    """재시도해도 의미 없는 외부/인프라 실패"""


class ConcurrencyConflict(AppError):
    """낙관적 락, 중복 처리, 상태 충돌"""
```

이렇게 두면 장점이 크다.

- FastAPI에서는 `DomainError`를 409/422로 매핑하기 쉽다
- worker에서는 `TransientInfraError`만 retry 대상으로 제한할 수 있다
- CLI에서는 `ValidationError`와 `PermanentInfraError`를 다른 exit code로 분리할 수 있다
- 로깅/메트릭에서도 에러 그룹을 라이브러리명이 아니라 운영 의미로 볼 수 있다

### 왜 "예외 클래스가 많아지지 않을까"를 먼저 걱정하면 안 되나

예외 클래스 수 자체는 본질이 아니다.
문제는 **팀이 실패를 같은 언어로 설명할 수 있느냐**다.

예를 들어 아래 두 실패는 둘 다 결제 API 호출 중 발생할 수 있다.

- 연결 timeout
- 카드 한도 초과

겉으로는 둘 다 외부 API 에러처럼 보이지만 운영 의미는 완전히 다르다.

- timeout: 재시도 후보일 수 있음
- 카드 한도 초과: 재시도하면 안 됨, 사용자 수정 필요

이 둘을 `PaymentError` 하나로만 뭉개면 retry 정책도, API 응답도, 알림 기준도 흐려진다.

### 실무 추천 분류 기준

보통 아래 네 축이면 충분하다.

1. **사용자/호출자가 수정 가능한가**
2. **재시도 가치가 있는가**
3. **이미 일부 부수효과가 발생했을 가능성이 있는가**
4. **도메인 규칙 위반인가, 시스템 장애인가**

즉 예외 설계의 목적은 세련된 계층도가 아니라 **행동 기준을 안정적으로 붙이는 것**이다.

---

## 핵심 개념 2: `raise ... from ...` 를 쓰지 않으면 장애 원인을 스스로 지운다

Python 코드베이스에서 정말 자주 보는 안티패턴이 있다.

```python
try:
    await payment_client.charge(...)
except httpx.TimeoutException:
    raise TransientInfraError("payment timeout")
```

겉으로는 괜찮아 보인다.
하지만 이 순간 원인 예외 체인이 끊긴다.
나중에 traceback을 보면 실제 socket timeout, DNS 문제, TLS handshake 실패 같은 하위 맥락이 희미해질 수 있다.

원인을 유지하려면 이렇게 써야 한다.

```python
try:
    await payment_client.charge(...)
except httpx.TimeoutException as exc:
    raise TransientInfraError("payment timeout") from exc
```

### 왜 이게 중요한가

예외 체인은 단순 디버깅 편의가 아니다.
운영에서는 아래 판단에 직접 영향을 준다.

- timeout이 진짜 upstream latency 문제였는가
- connection reset이 특정 AZ/network 구간에서만 발생했는가
- DB unique violation이 어떤 SQL/constraint와 연결되었는가
- 애플리케이션이 번역한 예외가 원인을 제대로 보존했는가

즉 바깥 계층에서 의미를 더해도, 안쪽 계층의 사실은 잃지 않는 편이 좋다.

### 언제 `from None` 이 필요한가

반대로 내부 구현을 노출하지 말아야 할 때도 있다.

예를 들어 CLI 사용자나 API 소비자에게는 내부 traceback 연결고리를 그대로 보여 줄 필요가 없을 수 있다.
그럴 때는 표현을 단순화할 수 있다.

```python
try:
    settings = load_settings()
except FileNotFoundError:
    raise ValidationError("설정 파일이 없습니다") from None
```

다만 여기서 중요한 점이 있다.

> `from None` 은 **표면 표현을 단순화하는 도구**이지, 내부 관측성까지 지워야 한다는 뜻이 아니다.

즉 외부 응답은 단순화하되,
내부 로그나 에러 추적 시스템에는 원인 정보가 남도록 설계하는 편이 안전하다.

### 실무 규칙 하나

- 내부 번역 계층: `raise NewError(...) from exc`
- 외부 사용자 메시지 노출 계층: 필요 시 `from None`
- 단, 로그/추적에는 원인 체인을 남긴다

이 규칙만 지켜도 장애 분석 시간이 꽤 줄어든다.

---

## 핵심 개념 3: retry는 예외 처리의 부록이 아니라 정합성과 중복 제어의 일부다

retry가 어려운 이유는 실패 자체보다 **실패 이후 시스템 상태를 확신하기 어렵기 때문**이다.

예를 들어 결제 승인 요청에서 timeout이 났다고 하자.
이때 가능한 상태는 적어도 세 가지다.

1. 외부 시스템에 요청이 도달하지 않았다
2. 외부 시스템이 이미 승인했지만 응답만 잃었다
3. 외부 시스템이 실패했고 그 실패 응답도 잃었다

즉 timeout 하나만으로는 상태를 단정하기 어렵다.
이런 예외에 무조건 retry를 붙이면 중복 부수효과가 생길 수 있다.

### retry 분류는 최소한 이렇게 나눠야 한다

#### 1) 절대 retry하면 안 되는 예외

- 입력 검증 실패
- 비즈니스 규칙 위반
- 인증/인가 거부
- 존재하지 않는 리소스
- 멱등하지 않은 요청의 명확한 중복 금지 위반

#### 2) 조건부 retry 예외

- network timeout
- connection reset
- 429 / 503 / 일시적 upstream overload
- deadlock detected
- lock timeout

#### 3) 재조회 후 판단해야 하는 예외

- 외부 시스템 호출 timeout 이후 상태 미확정
- commit 직전/직후 경계에서 응답 유실
- 비동기 발행 성공 여부가 불분명한 경우

### retry 경계에서 꼭 같이 붙어야 할 것

- idempotency key
- retry budget
- backoff + jitter
- 최대 시도 횟수
- 재시도 전 상태 재확인 로직

예를 들어 단순한 retry wrapper도 분류 기준 없이는 위험하다.

```python
async def retry_transient(fn, *, attempts: int = 3):
    last_exc = None
    for attempt in range(1, attempts + 1):
        try:
            return await fn()
        except TransientInfraError as exc:
            last_exc = exc
            if attempt == attempts:
                break
            await asyncio.sleep(0.2 * attempt)
    raise RetryExhaustedError("retry budget exhausted") from last_exc
```

이 wrapper가 안전하려면 전제가 있다.

- `TransientInfraError` 분류가 정확해야 한다
- 호출이 멱등하거나 멱등 키가 있어야 한다
- 시도 초과 후 상위 계층이 후속 복구 경로를 알아야 한다

### 실무 감각 하나

retry를 기술적으로만 보면 "성공률을 높이는 장치"처럼 보인다.
하지만 실제로는 **불확실한 상태를 얼마나 통제할지 결정하는 정책**이다.

성공률은 올라갈 수 있다.
대신 중복 처리, 지연 증가, 동시성 증폭, 큐 적체 비용이 따라온다.
그래서 retry는 `except` 블록 안에 몰래 숨길 기능이 아니다.

---

## 핵심 개념 4: Error Mapping은 도메인 안이 아니라 어댑터 경계에서 일어나야 한다

같은 예외라도 표면에 따라 표현 방식이 달라야 한다.

- HTTP API: status code + JSON body
- CLI: exit code + stderr
- consumer: ack / nack / retry / DLQ
- batch: 요약 리포트 + 실패 건 목록

문제는 많은 코드가 이 매핑을 서비스 레이어 내부에 박아 넣는다는 점이다.

```python
class OrderService:
    async def confirm(self, ...):
        try:
            ...
        except OutOfStockError:
            raise HTTPException(status_code=409, detail="out of stock")
```

이 구조의 문제는 간단하다.

- 서비스가 FastAPI에 묶인다
- worker와 CLI에서 같은 코어를 재사용하기 어렵다
- 같은 도메인 실패가 채널마다 다른 의미를 가져야 할 때 대응이 힘들다

더 건강한 방향은 도메인/애플리케이션 예외는 그대로 유지하고,
가장 바깥 어댑터에서 매핑하는 것이다.

```python
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()


@app.exception_handler(ValidationError)
async def handle_validation_error(_, exc: ValidationError):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(ConcurrencyConflict)
async def handle_conflict(_, exc: ConcurrencyConflict):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(TransientInfraError)
async def handle_transient(_, exc: TransientInfraError):
    return JSONResponse(
        status_code=503,
        content={"detail": "temporary upstream failure"},
    )
```

### 이 구조가 좋은 이유

- 코어는 프레임워크를 모른다
- 같은 `ConcurrencyConflict` 를 HTTP에서는 409로, consumer에서는 retry stop으로 다르게 다룰 수 있다
- 에러 번역 위치가 한곳에 모여 운영 정책을 읽기 쉬워진다

### worker에서는 어떻게 다를까

예를 들어 메시지 consumer라면 보통 이렇게 나뉜다.

- `DomainError`, `ValidationError`: DLQ 또는 skip
- `TransientInfraError`: retry
- `ConcurrencyConflict`: 짧은 지연 후 재시도 또는 중복 처리로 간주 후 ack
- 알 수 없는 예외: 제한된 retry 후 alert

즉 Error Mapping은 예외를 "예쁘게 바꾸는" 일이 아니라,
**실패를 채널별 행동으로 변환하는 작업**이다.

---

## 핵심 개념 5: Python 3.11의 `ExceptionGroup` 은 병렬 실패를 1차원으로 뭉개지 않게 해 준다

병렬 처리 코드가 늘어나면 단일 예외만 가정한 설계가 무너진다.

예를 들어 20개 테넌트에 같은 설정 변경을 병렬 적용하는 배치를 생각해 보자.
실패가 동시에 여러 개 날 수 있다.

- 3개는 권한 오류
- 2개는 timeout
- 1개는 데이터 불일치

이걸 `Exception("batch failed")` 하나로 뭉개면 재처리 기준이 사라진다.
Python 3.11의 `ExceptionGroup` 은 이 문제를 풀기 위한 중요한 도구다.

```python
errors = []
for tenant_id in tenant_ids:
    try:
        await sync_tenant(tenant_id)
    except Exception as exc:
        errors.append(exc)

if errors:
    raise ExceptionGroup("tenant sync failed", errors)
```

이제 상위 계층에서 `except*` 로 타입별 분리가 가능하다.

```python
try:
    await sync_all_tenants(tenant_ids)
except* ValidationError as exc_group:
    record_skip_group(exc_group)
except* TransientInfraError as exc_group:
    schedule_retry_group(exc_group)
```

### `ExceptionGroup` 이 실무에서 좋은 이유

1. **부분 실패를 구조적으로 표현할 수 있다**
2. **재시도 대상과 비재시도 대상을 분리하기 쉽다**
3. **배치 리포트와 운영 메트릭을 더 정확히 만들 수 있다**
4. **병렬 처리의 실제 실패 모양을 숨기지 않는다**

### 언제 쓰면 안 되나

모든 예외를 무조건 그룹으로 감쌀 필요는 없다.

- 하나라도 실패하면 전체를 즉시 중단하는 fail-fast use case
- 첫 실패만 알면 충분한 단일 트랜잭션 경계
- 병렬 작업 수가 작고 후속 분류 가치가 낮은 경우

즉 `ExceptionGroup` 의 목적은 복잡해 보이는 예외 구조를 만드는 게 아니라,
**이미 존재하는 다중 실패 현실을 잃지 않는 것**이다.

---

## 핵심 개념 6: 병렬 처리에서는 `TaskGroup` 과 `ExceptionGroup` 의 역할을 구분해서 봐야 한다

둘 다 Python 3.11+에서 자주 같이 등장하지만 역할은 다르다.

- `TaskGroup`: 같은 생명주기의 동시 작업을 관리하는 구조
- `ExceptionGroup`: 여러 실패를 함께 표현하는 결과 구조

예를 들어 `TaskGroup` 안에서 병렬 실행한 작업들이 여러 예외를 던지면,
상위로 `ExceptionGroup` 이 올라올 수 있다.

```python
async def run_batch(items: list[str]) -> None:
    async with asyncio.TaskGroup() as tg:
        for item in items:
            tg.create_task(process_item(item))
```

이때 중요한 질문은 이것이다.

- 하나 실패하면 나머지도 취소해야 하는가
- 아니면 개별 실패를 모아 후처리해야 하는가

만약 "같이 성공하거나 같이 멈춰야 하는 작업"이면 `TaskGroup` 의 fail-fast 성향이 맞다.
반대로 "실패를 모아 요약해야 하는 작업"이면 내부에서 예외를 분류·수집한 뒤 `ExceptionGroup` 으로 올리는 쪽이 더 낫다.

### 실무 감각 하나

동시성 구조와 예외 결과 구조를 분리해서 생각하면 설계가 선명해진다.

- 실행 제어는 `TaskGroup`
- 실패 표현은 `ExceptionGroup`

이 둘을 구분하지 않으면 "병렬 돌리기"와 "실패 리포트"가 한 덩어리로 섞여 코드가 빨리 지저분해진다.

---

## 핵심 개념 7: 로그는 모든 곳에서 남기지 말고, 의미가 확정되는 경계에서 한 번 남겨야 한다

예외 처리 구조가 나쁜 팀의 특징 중 하나는 로그가 너무 많다는 점이다.

- repository에서 한 번
- service에서 또 한 번
- router에서 또 한 번
- worker wrapper에서 또 한 번

이렇게 되면 같은 실패가 네 번 쌓이고,
정작 어디서 정책이 결정됐는지는 흐려진다.

내가 추천하는 기본 원칙은 아래다.

### 1) 원인만 추가하는 계층에서는 로그보다 체인 보존을 우선한다

예외를 번역만 하는 계층이라면 굳이 로그를 찍지 않아도 된다.
`raise ... from exc` 가 더 중요하다.

### 2) 채널별 응답/행동이 확정되는 가장 바깥 경계에서 로그를 남긴다

예를 들면:

- HTTP handler / middleware
- worker loop wrapper
- CLI main entrypoint
- batch orchestrator

### 3) 로그에는 예외 클래스뿐 아니라 운영 키를 같이 남긴다

- request_id
- job_id
- tenant_id
- idempotency_key
- retry_attempt
- error_class
- root_cause_class

### 4) 사용자 메시지와 내부 로그 메시지를 분리한다

사용자에게는

- "temporary upstream failure"
- "order already confirmed"

정도로 충분할 수 있다.

내부 로그에는

- 어떤 upstream
- 몇 번째 시도
- 어떤 상태 전이 중
- 어떤 원인 체인

이 남아야 한다.

즉 좋은 예외 처리는 traceback을 숨기는 기술이 아니라,
**누가 어떤 수준의 정보를 봐야 하는지 분리하는 기술**이다.

---

## 실무 예시 1: 외부 결제 연동에서 예외 계층과 원인 체인을 어떻게 설계할까

결제 승인 흐름을 예로 들어 보자.

요구사항은 아래와 같다.

- 카드 한도 초과는 사용자 수정 대상이다
- gateway timeout은 재시도 후보다
- 승인 성공 여부가 불분명한 timeout은 별도 reconciliation 대상이다
- FastAPI API, consumer, admin CLI가 같은 코어를 공유한다

### 1) 도메인/애플리케이션 예외 정의

```python
class PaymentError(AppError):
    pass


class PaymentDeclined(PaymentError, DomainError):
    pass


class PaymentTemporaryFailure(PaymentError, TransientInfraError):
    pass


class PaymentStateUnknown(PaymentError):
    pass
```

여기서 `PaymentStateUnknown` 이 중요한 이유는 timeout보다 더 구체적이기 때문이다.

- timeout 자체는 기술 원인
- 상태 미확정은 비즈니스 후속조치 필요 신호

### 2) 인프라 예외를 코어 의미로 번역

```python
async def authorize_payment(client: PaymentClient, command: AuthorizeCommand) -> str:
    try:
        response = await client.authorize(
            order_id=command.order_id,
            amount=command.amount,
            idempotency_key=command.idempotency_key,
        )
    except httpx.TimeoutException as exc:
        raise PaymentStateUnknown(
            f"payment authorization state unknown: order_id={command.order_id}"
        ) from exc
    except httpx.NetworkError as exc:
        raise PaymentTemporaryFailure("payment network failure") from exc

    if response.status == "DECLINED":
        raise PaymentDeclined(response.reason)

    return response.transaction_id
```

이제 상위 계층은 기술 라이브러리를 몰라도 된다.
대신 행동 가능한 의미를 받는다.

### 3) 상위 서비스에서 후속 정책 결정

```python
async def confirm_order(service_input: ConfirmOrderInput) -> None:
    try:
        tx_id = await authorize_payment(...)
    except PaymentDeclined:
        raise
    except PaymentStateUnknown as exc:
        await mark_order_pending_reconciliation(service_input.order_id)
        raise ConcurrencyConflict("payment state is pending reconciliation") from exc
```

물론 실제 서비스에서는 더 세밀한 예외명을 쓸 수 있다.
핵심은 번역 책임이 선명해야 한다는 점이다.

- infra adapter: 라이브러리 예외 → 도메인 의미
- application service: 도메인 의미 → 상태 전이/후속 프로세스
- outer adapter: 도메인 예외 → HTTP/queue/CLI 응답

---

## 실무 예시 2: FastAPI에서는 전역 handler에서 error mapping을 고정하는 편이 오래 간다

FastAPI 코드베이스가 커질수록 route마다 `try/except HTTPException` 를 반복하는 건 금방 한계에 닿는다.

아래처럼 전역 exception handler를 두는 편이 일관성에 좋다.

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()


@app.exception_handler(DomainError)
async def handle_domain_error(request: Request, exc: DomainError):
    request.app.logger.info(
        "domain_error",
        extra={"path": request.url.path, "error_class": exc.__class__.__name__},
        exc_info=exc,
    )
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(ValidationError)
async def handle_validation_error(request: Request, exc: ValidationError):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(TransientInfraError)
async def handle_transient_error(request: Request, exc: TransientInfraError):
    request.app.logger.warning(
        "transient_infra_error",
        extra={"path": request.url.path, "error_class": exc.__class__.__name__},
        exc_info=exc,
    )
    return JSONResponse(status_code=503, content={"detail": "temporary failure"})
```

### 여기서 중요한 포인트

#### 1) 에러 응답 포맷이 고정된다

프론트엔드와 다른 서비스가 예측 가능한 방식으로 실패를 다룰 수 있다.

#### 2) route 함수가 단순해진다

route는 파싱, 인증, use case 호출에 집중하고,
예외 정책은 바깥 경계로 밀어낼 수 있다.

#### 3) 로깅 정책도 함께 모인다

도메인 에러는 info 또는 warning,
인프라 일시 장애는 warning,
알 수 없는 에러는 error처럼 분리할 수 있다.

### 주의할 점

`DomainError` 전체를 무조건 409로 보내는 식의 단순화는 오래 못 간다.
예를 들어:

- 잘못된 입력: 422
- 상태 충돌: 409
- 존재하지 않음: 404
- 권한 문제: 403

처럼 한 단계 더 세분화할 필요가 있다.
중요한 건 세분화 위치가 **route 내부가 아니라 예외 분류 체계 쪽**이어야 한다는 점이다.

---

## 실무 예시 3: batch/병렬 처리에서는 개별 실패를 모아 재처리 가능한 형태로 남겨야 한다

배치가 어려운 이유는 "전체 성공/실패"보다 **부분 실패 후속 처리** 때문이다.

예를 들어 CSV로 5000건의 사용자 초대 메일을 보내는 작업을 생각해 보자.

가능한 실패는 섞여 있다.

- 이메일 형식 오류
- 이미 초대된 사용자
- SMTP provider timeout
- 외부 rate limit

이때 전체 예외 하나만 남기면 운영팀은 할 수 있는 게 없다.
그래서 개별 실패를 구조적으로 모아야 한다.

```python
class InviteFailure(AppError):
    def __init__(self, row_no: int, email: str, reason: str):
        self.row_no = row_no
        self.email = email
        self.reason = reason
        super().__init__(f"row={row_no}, email={email}, reason={reason}")
```

```python
async def invite_many(rows: list[InviteRow]) -> None:
    errors: list[Exception] = []

    for row_no, row in enumerate(rows, start=1):
        try:
            await invite_one(row)
        except ValidationError as exc:
            errors.append(InviteFailure(row_no, row.email, str(exc)))
        except TransientInfraError as exc:
            errors.append(InviteFailure(row_no, row.email, "temporary_provider_failure"))
        except Exception as exc:
            errors.append(InviteFailure(row_no, row.email, "unknown_failure"))

    if errors:
        raise ExceptionGroup("bulk invite failed", errors)
```

상위에서는 이렇게 처리할 수 있다.

```python
try:
    await invite_many(rows)
except* InviteFailure as exc_group:
    write_failure_report(exc_group.exceptions)
    raise
```

### 이 방식의 장점

- 실패 행 번호와 재처리 대상을 바로 뽑을 수 있다
- validation 실패와 transient 실패를 후속 정책상 구분하기 쉽다
- 사용자에게는 요약 리포트를, 운영팀에는 상세 실패 목록을 줄 수 있다

즉 `ExceptionGroup` 은 추상 이론보다 **배치 재처리 UX**에서 특히 빛난다.

---

## 트레이드오프: 예외 아키텍처는 명확성을 얻는 대신 초기 설계 비용을 낸다

예외 구조를 정리하면 장점만 있는 것처럼 보일 수 있다.
하지만 비용도 분명하다.

### 장점

- retry 대상과 비대상을 구분하기 쉬워진다
- API/worker/CLI가 같은 실패를 일관되게 다룰 수 있다
- 로그 노이즈가 줄고 원인 체인이 보존된다
- 병렬 실패와 부분 실패 리포트가 쉬워진다
- 팀이 "이 예외는 어떤 행동을 뜻하는가"를 공통 언어로 합의하기 쉬워진다

### 비용

- 초기에 예외 분류를 설계해야 한다
- 클래스 수가 조금 늘어난다
- 계층 간 번역 코드를 써야 한다
- 팀이 `raise ... from ...`, `ExceptionGroup`, retry 의미를 함께 이해해야 한다

### 실무 추천 균형점

내 경험상 Python 서비스에서는 아래 정도가 가장 효율적이다.

- 최상위 `AppError`
- `DomainError`, `ValidationError`, `TransientInfraError`, `ConcurrencyConflict` 정도의 핵심 축
- 기능별로 정말 행동이 달라질 때만 세부 예외 추가
- Error Mapping은 채널 경계로 모으기
- retry는 예외 이름보다 멱등성/상태 미확정 여부와 함께 판단

즉 모든 실패마다 전용 클래스를 만드는 게 목표가 아니다.
**행동 기준이 달라지는 실패만 구조화**하면 된다.

---

## 흔한 실수 1: `except Exception` 으로 다 잡고 문자열만 바꿔 던진다

이 패턴은 처음엔 단순해 보인다.
하지만 결국 아래를 잃는다.

- 원인 타입
- 재시도 가능성
- 사용자 수정 가능성
- 운영 후속조치 기준

문자열은 분류 체계가 아니다.
실패 정책이 달라지면 예외 구조도 달라져야 한다.

---

## 흔한 실수 2: retry를 decorator 하나로 전역 통일한다

retry 라이브러리나 decorator 자체가 문제는 아니다.
문제는 예외 의미를 무시한 채 일괄 적용하는 것이다.

- 검증 실패까지 retry
- 상태 충돌까지 retry
- 멱등하지 않은 외부 호출까지 retry
- 요청 전체 deadline 밖까지 retry

이렇게 되면 성공률보다 데이터 정합성이 먼저 깨진다.
retry는 공통 유틸이 아니라 **경계별 정책**이어야 한다.

---

## 흔한 실수 3: 같은 예외를 모든 계층에서 중복 로깅한다

중복 로그는 안전망처럼 보이지만 실제로는 장애 분석을 더 어렵게 만든다.

- 로그 건수만 늘어난다
- 같은 실패가 여러 severity로 섞인다
- 어느 계층이 최종 정책을 결정했는지 흐려진다

로그는 의미가 확정되는 경계에서 한 번 남기고,
중간 계층은 체인 보존에 집중하는 편이 좋다.

---

## 흔한 실수 4: 외부 라이브러리 예외를 서비스 전역 공개 API처럼 사용한다

예를 들어 서비스 시그니처와 상위 handler가 `httpx.TimeoutException`, `psycopg.Error` 같은 타입에 직접 의존하면,
인프라 교체와 테스트 대역 구성이 모두 어려워진다.

외부 라이브러리 예외는 adapter 안에서 소화하고,
코어에는 더 안정적인 애플리케이션 의미를 올려보내는 편이 낫다.

---

## 흔한 실수 5: `ExceptionGroup` 을 쓴다고 해서 부분 실패 전략이 자동으로 생기지는 않는다

`ExceptionGroup` 은 표현 도구일 뿐 정책 도구는 아니다.

질문은 여전히 남는다.

- 어떤 실패를 skip할 것인가
- 어떤 실패를 retry할 것인가
- 어떤 실패를 전체 중단 사유로 볼 것인가
- 요약 리포트에는 무엇을 남길 것인가

즉 그룹 예외를 도입하기 전에 **분류와 후속 행동 기준**이 먼저 있어야 한다.

---

## 흔한 실수 6: 내부 정보를 숨기려다 원인 자체를 완전히 잃어버린다

사용자에게 상세 traceback을 보여 주지 않는 것은 맞다.
하지만 그렇다고 내부 로그에서도 원인 체인을 지워 버리면 장애는 금방 미궁으로 간다.

- 외부 응답: 단순화
- 내부 관측성: 풍부하게 유지

이 분리를 꼭 기억할 필요가 있다.

---

## 체크리스트: Python 서비스의 예외 처리 구조를 점검할 때 보는 항목

### 분류

- [ ] 예외가 라이브러리 이름이 아니라 행동 기준으로 분류되어 있는가
- [ ] 사용자 수정 가능 실패와 시스템 장애가 구분되는가
- [ ] retry 가능 실패와 비재시도 실패가 구분되는가
- [ ] 상태 미확정 실패를 별도로 다루는가

### 체인 보존

- [ ] 예외 번역 시 `raise ... from exc` 를 사용하는가
- [ ] 외부 응답 단순화와 내부 원인 보존을 분리했는가
- [ ] traceback 없이 문자열만 새로 만드는 패턴이 남아 있지 않은가

### Error Mapping

- [ ] FastAPI/CLI/worker에서 채널별 매핑 지점이 명확한가
- [ ] 코어 서비스가 `HTTPException` 같은 어댑터 예외를 직접 모르도록 되어 있는가
- [ ] 같은 도메인 실패가 채널마다 일관된 행동으로 연결되는가

### Retry

- [ ] retry가 멱등성과 함께 설계되어 있는가
- [ ] retry budget, backoff, jitter가 있는가
- [ ] timeout 이후 상태 재확인 경로가 필요한 호출을 구분했는가
- [ ] domain error를 무의미하게 retry하지 않는가

### 병렬/배치

- [ ] 부분 실패를 구조적으로 모을 수 있는가
- [ ] `ExceptionGroup` 이 필요한 배치/병렬 경계가 있는가
- [ ] 실패 건별 재처리 정보(row id, tenant id, key)가 남는가

### 관측성

- [ ] 중복 로그 대신 최종 경계 로깅 원칙이 있는가
- [ ] request_id, job_id, tenant_id, retry_attempt 같은 키를 같이 남기는가
- [ ] error class와 root cause class를 구분해 집계할 수 있는가

---

## 바로 적용 가능한 정리 순서

이미 운영 중인 Python 서비스라면 아래 순서가 현실적이다.

1. 상위 `AppError` 와 핵심 분류 3~5개를 먼저 만든다
2. 외부 라이브러리 예외를 adapter 안에서 번역한다
3. `raise ... from ...` 가 빠진 곳부터 채운다
4. FastAPI/CLI/worker 바깥 경계에 Error Mapping을 모은다
5. retry decorator를 걷어내기보다, retry 대상 예외부터 축소한다
6. 배치/병렬 경계에서 개별 실패 식별자와 `ExceptionGroup` 도입 여부를 검토한다

핵심은 완벽한 계층도를 그리는 게 아니라,
**지금 운영 판단을 흐리게 만드는 실패들을 먼저 구조화하는 것**이다.

---

## 한 줄 정리

> Python 예외 처리의 본질은 `try/except` 를 많이 쓰는 데 있지 않고, **실패를 계층별 계약으로 분류하고, 원인 체인을 보존하고, retry와 채널별 Error Mapping을 일관되게 설계해 장애를 추측이 아니라 행동 가능한 정보로 바꾸는 데** 있다.
