---
layout: post
title: "Python 타입 힌트 실전: Protocol, TypedDict, Generic으로 대규모 코드베이스 안전하게 다루기"
date: 2026-03-22 11:40:00 +0900
categories: [python]
tags: [study, python, typing, protocol, typeddict, generics, mypy, pyright, architecture]
---

## 왜 이 주제가 실무에서 중요할까?

Python은 빠르게 만들기 좋은 언어다. 문제는 프로젝트가 커질수록 "빨리 만든 코드"가 "나중에 읽기 어려운 코드"로 바뀌기 쉽다는 점이다. 특히 아래 상황이 겹치면 유지보수 비용이 급격히 올라간다.

- 외부 API 응답 구조가 자주 바뀜
- 딕셔너리 payload가 서비스 전역을 떠다님
- 함수는 많아졌는데 입력/출력 계약이 문서로만 존재함
- 팀원이 늘어나면서 "이 값이 여기서 string인지 int인지"를 매번 추적해야 함
- 리팩터링 때 런타임 테스트를 돌리기 전까지 깨진 지점을 알기 어려움

이때 타입 힌트는 단순한 문법 장식이 아니라 **변경 비용을 낮추는 설계 도구**가 된다. 다만 `list[str]`, `dict[str, Any]` 수준에 멈추면 효과가 제한적이다. 실무 난이도가 올라갈수록 진짜 체감이 큰 건 다음 세 가지다.

- **`TypedDict`**: 느슨한 dict payload를 구조화된 계약으로 바꾸기
- **`Protocol`**: 상속 없이도 인터페이스를 명시해 결합도 낮추기
- **`Generic`**: 공통 컴포넌트를 재사용하면서도 타입 안정성 유지하기

이 세 가지를 제대로 쓰면 Python 코드베이스도 Java나 TypeScript 못지않게 의도를 명확하게 표현할 수 있다.

---

## 먼저 큰 그림: 타입 힌트는 검증 도구가 아니라 의도 표현 도구다

많은 팀이 타입 힌트를 도입할 때 처음부터 삐끗한다. 이유는 타입을 "에러 잡는 장치"로만 보기 때문이다. 물론 맞는 말이지만, 실무에서는 그보다 더 큰 가치가 있다.

1. **함수 계약이 코드에 남는다**
2. **IDE 자동완성과 리뷰 품질이 올라간다**
3. **리팩터링 중 깨지는 지점을 정적으로 확인할 수 있다**
4. **모듈 간 책임 경계가 선명해진다**

즉, 타입 힌트의 핵심은 "엄격함" 자체보다 **변경 가능성을 통제 가능한 형태로 만드는 것**이다.

예를 들어 아래 코드는 동작은 하지만 유지보수성은 낮다.

```python
from typing import Any


def build_order_summary(order: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": order["id"],
        "customer_name": order["customer"]["name"],
        "paid": order["payment"]["status"] == "PAID",
    }
```

문제는 단순하다.

- `order`에 어떤 키가 있는지 함수 시그니처만 보고는 알 수 없다.
- `customer`가 빠지면 어디서 깨질지 정적 분석이 어렵다.
- `status`가 문자열인지 enum 비슷한 값인지 드러나지 않는다.
- 이 함수를 사용하는 쪽도 출력 구조를 문서나 구현을 읽어야만 안다.

이 구조를 `TypedDict`로 바꾸면 "payload 기반 코드"가 "계약 기반 코드"로 바뀐다.

---

## 핵심 개념 1: `TypedDict`로 dict 중심 코드를 구조화하기

실무 Python은 생각보다 dict가 많다.

- JSON API 요청/응답
- 이벤트 payload
- 설정 객체
- 배치 파이프라인 중간 결과
- ORM 밖의 경량 데이터 구조

문제는 dict가 편한 만큼 쉽게 오염된다는 점이다. 키 이름이 조금씩 달라지고, optional 필드 규칙이 암묵적으로 퍼지고, `Any`가 늘어나면서 타입 체크가 무력화된다.

### `TypedDict`가 적합한 상황

- 런타임 객체를 굳이 class로 만들고 싶진 않다
- JSON과 1:1로 가까운 구조를 다룬다
- 키 기반 접근이 자연스럽다
- 응답 스키마를 정적 분석에서 잡고 싶다

```python
from typing import Literal, NotRequired, TypedDict


class CustomerPayload(TypedDict):
    id: int
    name: str
    grade: Literal["BASIC", "VIP"]


class PaymentPayload(TypedDict):
    status: Literal["READY", "PAID", "FAILED"]
    approved_at: NotRequired[str]


class OrderPayload(TypedDict):
    id: int
    customer: CustomerPayload
    payment: PaymentPayload
    coupon_code: NotRequired[str]
```

이제 함수는 훨씬 읽기 쉬워진다.

```python
def build_order_summary(order: OrderPayload) -> dict[str, str | int | bool]:
    return {
        "id": order["id"],
        "customer_name": order["customer"]["name"],
        "paid": order["payment"]["status"] == "PAID",
    }
```

### `TypedDict`의 실무 장점

#### 1) 필수/선택 필드를 구분할 수 있다

`NotRequired`를 쓰면 "있을 수도 있고 없을 수도 있는 값"이 명시된다. 이게 중요한 이유는 optional 규칙을 사람 기억이 아니라 코드 계약으로 옮기기 때문이다.

#### 2) API 스키마 변경 영향 범위를 빨리 찾는다

예를 들어 `payment.status`가 `payment.state`로 바뀌면, 런타임 오류를 기다리지 않고 타입 검사 단계에서 영향 지점을 발견할 수 있다.

#### 3) dataclass보다 JSON 경계에서 덜 무겁다

입출력 경계에서 굳이 객체 생성 비용과 변환 로직을 두기 싫을 때 `TypedDict`는 매우 현실적인 선택이다.

### `TypedDict`를 남용하면 안 되는 경우

반대로 아래 상황이면 dataclass나 Pydantic 모델이 더 낫다.

- 메서드가 필요한 도메인 객체
- 생성 시점 검증이 반드시 필요한 입력 모델
- 기본값, 변환, serializer 규칙이 복잡함
- 객체 identity와 행동이 함께 중요함

즉, `TypedDict`는 **행동 없는 구조적 데이터 계약**에 강하다.

---

## 핵심 개념 2: `Protocol`로 느슨한 결합 만들기

Python에서 인터페이스 흉내를 내려고 추상 베이스 클래스(ABC)만 고집하면 오히려 결합도가 올라가는 경우가 많다. 특정 베이스 클래스를 상속해야만 계약을 만족한다고 생각하게 되기 때문이다.

`Protocol`은 이 지점을 바꾼다. 핵심은 **"무엇을 상속했는가"보다 "어떤 형태를 제공하는가"** 에 있다. 즉 구조적 타이핑(structural typing)이다.

### 왜 실무에서 유용한가?

서비스 계층이 인프라 구현체를 직접 알 필요는 없다. 필요한 건 몇 개 메서드 계약뿐이다.

```python
from typing import Protocol


class UserRepository(Protocol):
    def get_by_id(self, user_id: int) -> dict | None: ...
    def save_login_state(self, user_id: int, success: bool) -> None: ...


class LoginAuditPublisher(Protocol):
    def publish(self, event_name: str, payload: dict) -> None: ...
```

이제 서비스는 구체 구현체가 아니라 계약에 의존한다.

```python
class LoginService:
    def __init__(
        self,
        user_repo: UserRepository,
        audit_publisher: LoginAuditPublisher,
    ) -> None:
        self.user_repo = user_repo
        self.audit_publisher = audit_publisher

    def login(self, user_id: int) -> bool:
        user = self.user_repo.get_by_id(user_id)
        success = user is not None
        self.user_repo.save_login_state(user_id, success)
        self.audit_publisher.publish(
            "user.login",
            {"user_id": user_id, "success": success},
        )
        return success
```

여기서 포인트는 구현체가 꼭 `UserRepository`를 상속할 필요가 없다는 것이다.

```python
class SqlAlchemyUserRepository:
    def get_by_id(self, user_id: int) -> dict | None:
        ...

    def save_login_state(self, user_id: int, success: bool) -> None:
        ...


class FakeAuditPublisher:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    def publish(self, event_name: str, payload: dict) -> None:
        self.events.append((event_name, payload))
```

이 구현체들은 상속 선언이 없어도 `Protocol` 계약을 만족한다.

### `Protocol`이 특히 좋은 장면

#### 1) 테스트 대체 구현을 쉽게 만들 때

mock 프레임워크로 모든 걸 덮기보다, 작은 fake 객체를 만들면 테스트가 더 읽기 쉬워진다. `Protocol`은 그 fake가 만족해야 할 계약을 문서화해준다.

#### 2) 라이브러리나 인프라 교체 가능성을 열어둘 때

예를 들어 캐시 구현을 Redis에서 in-memory로 바꾸거나, 메시지 발행기를 Kafka에서 SQS로 바꾸더라도 서비스 계층 변경을 최소화할 수 있다.

#### 3) 프레임워크 의존성을 서비스 레이어에서 밀어낼 때

특정 ORM 모델, 특정 HTTP 클라이언트, 특정 SDK 타입을 서비스 함수 시그니처에 직접 노출하면 나중에 경계가 무너진다. `Protocol`은 이 경계를 지키는 데 유용하다.

### `Protocol`과 ABC의 선택 기준

- **ABC가 유리한 경우**: 공통 기본 구현이 필요함, 런타임 `isinstance` 판단이 중요함, 상속 계층 자체가 설계의 일부임
- **Protocol이 유리한 경우**: 계약만 필요함, 구현 다양성이 큼, 테스트 대체 객체를 쉽게 만들고 싶음

실무에서는 서비스 경계에는 `Protocol`, 프레임워크 내부 공통 구현에는 ABC가 더 잘 맞는 경우가 많다.

---

## 핵심 개념 3: `Generic`으로 재사용성과 안정성을 동시에 챙기기

제네릭 없이 공통 유틸을 만들면 보통 두 가지 문제가 생긴다.

1. 재사용을 위해 `Any`를 쓰게 된다
2. 재사용은 됐지만 호출부 타입 정보가 사라진다

`Generic`은 이 둘 사이의 균형점이다. 대표적으로 아래 같은 구조에서 효과가 크다.

- 페이지네이션 응답 래퍼
- API 공통 응답 객체
- 캐시 래퍼
- Repository/BaseService 공통화
- Result/Success/Error 모델

### 예제 1) 페이지 응답 래퍼

```python
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(slots=True)
class Page(Generic[T]):
    items: list[T]
    total_count: int
    page: int
    size: int
```

이제 `Page[UserSummary]`, `Page[OrderPayload]`, `Page[str]`처럼 타입 손실 없이 재사용할 수 있다.

```python
class UserSummary(TypedDict):
    id: int
    name: str


def fetch_users() -> Page[UserSummary]:
    return Page(
        items=[{"id": 1, "name": "kim"}],
        total_count=1,
        page=1,
        size=20,
    )
```

### 예제 2) Result 패턴

예외를 무조건 던지는 대신, 일부 경계에서는 성공/실패를 명시적으로 다루는 편이 더 나을 때가 있다.

```python
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")
E = TypeVar("E")


@dataclass(slots=True)
class Result(Generic[T, E]):
    data: T | None
    error: E | None

    @property
    def is_ok(self) -> bool:
        return self.error is None
```

```python
class PaymentError(TypedDict):
    code: str
    message: str


def approve_payment() -> Result[str, PaymentError]:
    return Result(data="approved", error=None)
```

이 구조의 장점은 단순히 재사용이 아니라, **호출부가 처리해야 할 데이터 형태를 타입 수준에서 강제**할 수 있다는 점이다.

### `Generic`이 주는 실무 이점

- 공통 모듈이 `Any` 오염원이 되는 것을 막음
- 반환 타입 추론이 좋아져 IDE 경험이 개선됨
- 중복 코드를 줄이면서도 안전성은 유지됨

단, 제네릭도 지나치게 추상화하면 오히려 코드를 읽기 어려워진다. 타입 매개변수가 3개 이상으로 늘어나고, 함수 시그니처만 봐도 해석이 어렵다면 대개 추상화 수준이 과한 신호다.

---

## 실무 예시: 외부 결제 이벤트 소비 파이프라인을 타입 중심으로 다시 설계해보기

이제 `TypedDict`, `Protocol`, `Generic`을 따로 보지 말고 한 흐름 안에서 묶어보자.

상황은 이렇다.

- 결제사 webhook 이벤트를 수신한다
- 이벤트 payload를 검증/정규화한다
- 주문 상태를 업데이트한다
- 후속 이벤트를 발행한다
- 실패를 재처리 큐로 보낸다

초기 코드가 보통 이렇게 생긴다.

```python
def handle_event(payload: dict) -> dict:
    event_type = payload.get("type")
    order_id = payload.get("data", {}).get("order_id")
    ...
```

짧을 때는 괜찮아 보이지만, 이벤트 종류가 늘어나면 바로 지옥이 시작된다.

### 1) 이벤트 스키마를 `TypedDict`로 정의

```python
from typing import Literal, NotRequired, TypedDict


class PaymentEventData(TypedDict):
    order_id: str
    payment_id: str
    amount: int
    currency: Literal["KRW", "USD"]


class PaymentWebhookEvent(TypedDict):
    event_id: str
    type: Literal["payment.approved", "payment.failed"]
    occurred_at: str
    data: PaymentEventData
    trace_id: NotRequired[str]
```

### 2) 저장소/발행기 계약은 `Protocol`로 분리

```python
class OrderRepository(Protocol):
    def mark_paid(self, order_id: str, payment_id: str) -> None: ...
    def mark_payment_failed(self, order_id: str, reason: str) -> None: ...


class EventPublisher(Protocol):
    def publish(self, topic: str, payload: dict) -> None: ...


class DeadLetterQueue(Protocol):
    def enqueue(self, event: PaymentWebhookEvent, reason: str) -> None: ...
```

### 3) 공통 처리 결과는 `Generic`으로 표현

```python
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(slots=True)
class HandlerResult(Generic[T]):
    ok: bool
    data: T | None = None
    reason: str | None = None
```

### 4) 핸들러는 계약 중심으로 구현

```python
class PaymentWebhookHandler:
    def __init__(
        self,
        order_repo: OrderRepository,
        publisher: EventPublisher,
        dlq: DeadLetterQueue,
    ) -> None:
        self.order_repo = order_repo
        self.publisher = publisher
        self.dlq = dlq

    def handle(
        self,
        event: PaymentWebhookEvent,
    ) -> HandlerResult[str]:
        try:
            event_type = event["type"]
            order_id = event["data"]["order_id"]
            payment_id = event["data"]["payment_id"]

            if event_type == "payment.approved":
                self.order_repo.mark_paid(order_id, payment_id)
                self.publisher.publish(
                    "order.payment.completed",
                    {"order_id": order_id, "payment_id": payment_id},
                )
                return HandlerResult(ok=True, data=order_id)

            self.order_repo.mark_payment_failed(order_id, "provider failure")
            return HandlerResult(ok=False, reason="payment failed")

        except Exception as exc:
            self.dlq.enqueue(event, str(exc))
            return HandlerResult(ok=False, reason="unexpected exception")
```

이 구조가 좋은 이유는 단순히 타입이 예뻐서가 아니다.

- payload 계약이 명확하다
- 서비스가 구체 인프라 구현을 모른다
- 테스트에서 fake 구현을 쉽게 넣을 수 있다
- 결과 모델이 일관된다
- 리팩터링 시 영향 범위를 타입 검사로 먼저 확인할 수 있다

실무에서 이런 구조는 코드 리뷰 속도와 장애 예방에 직접 연결된다.

---

## 타입 힌트를 도입할 때 가장 많이 부딪히는 트레이드오프

좋은 도구라도 비용은 있다. 타입 힌트 역시 마찬가지다.

### 1) 초기 속도 vs 장기 유지보수성

초기에는 귀찮다. 타입 정의를 더 써야 하고, 검사 도구 설정도 필요하다. 하지만 팀 개발로 넘어가면 이 비용은 금방 회수된다. 특히 API 경계, 배치 파이프라인, 공용 라이브러리에서 회수 속도가 빠르다.

### 2) 엄격함 vs 개발 유연성

`mypy --strict`나 pyright strict 모드는 품질을 끌어올리지만, 레거시 프로젝트에 한 번에 적용하면 반발이 크다. 보통은 아래 순서가 현실적이다.

- 신규 모듈부터 타입 강제
- 핵심 경계(입출력, 서비스 인터페이스, 공용 util) 우선 적용
- `Any` 허용 범위를 점진적으로 줄이기

### 3) 정적 안전성 vs 런타임 검증

타입 힌트는 런타임 입력 검증을 대체하지 않는다. 외부 요청, 환경변수, 메시지 큐 payload처럼 신뢰할 수 없는 데이터는 Pydantic, validator, schema 검증이 여전히 필요하다.

정리하면,

- **정적 타입**: 코드 내부 계약 관리
- **런타임 검증**: 외부 입력 신뢰성 확보

둘은 경쟁 관계가 아니라 보완 관계다.

### 4) 추상화 재사용 vs 가독성

제네릭과 프로토콜은 멋있게 보이기 쉬워서 과하게 일반화하기 쉽다. 추상화 한 단계가 실제 중복 제거보다 더 큰 이해 비용을 만든다면 실패다. 실무에서는 "재사용 가능성"보다 **현재 팀이 이해 가능한 수준**이 더 중요하다.

---

## 흔한 실수

### 실수 1) `dict[str, Any]`를 사실상 기본 타입처럼 쓰기

이건 타입을 쓴 게 아니라 포기한 것에 가깝다. 경계가 넓은 payload부터 `TypedDict`로 좁혀야 한다.

### 실수 2) `Protocol` 없이 구현체를 직접 타입으로 박아 넣기

서비스 함수 시그니처에 `RedisCache`, `SqlAlchemySession`, `Boto3Client` 같은 구체 타입이 들어가기 시작하면 교체 가능성과 테스트성이 빠르게 떨어진다.

### 실수 3) 제네릭을 너무 복잡하게 만들기

`TypeVar`가 여러 개 등장하고 bound, variance까지 겹치면 팀 전체가 타입 시스템 공부를 하게 된다. 라이브러리 레벨이 아니라면 대개 과하다.

### 실수 4) 타입 힌트만 달고 검사기를 돌리지 않기

타입 힌트는 검사기와 함께 써야 가치가 커진다. 최소한 CI에서 mypy 또는 pyright 한 종류는 돌리는 편이 좋다.

### 실수 5) 레거시 전체를 한 번에 고치려 하기

대부분 실패한다. 실제로는 아래 순서가 훨씬 낫다.

1. 신규 파일은 타입 필수
2. 자주 수정되는 모듈 우선
3. 장애 잦은 경계 우선
4. 공용 유틸의 `Any`부터 제거

---

## 도입 체크리스트

### 1) 우선순위를 이렇게 잡으면 실패 확률이 낮다

- [ ] 외부 API 요청/응답 dict를 `TypedDict` 또는 Pydantic으로 정의했다
- [ ] 서비스 레이어 생성자/함수 인자에 구체 구현체 대신 `Protocol` 사용을 검토했다
- [ ] 공통 응답/페이지네이션/결과 래퍼에 `Generic` 적용 가능성을 점검했다
- [ ] `dict[str, Any]`, `list[dict]` 같은 넓은 타입을 검색해 축소 후보를 찾았다
- [ ] CI에 mypy 또는 pyright를 넣었다
- [ ] 신규 코드부터 점진 적용하는 원칙을 정했다

### 2) 팀 규칙도 함께 정해야 한다

- [ ] `Any` 사용 허용 기준이 있다
- [ ] optional 필드는 `NotRequired` 또는 `X | None` 중 어떤 방식으로 표현할지 정했다
- [ ] 도메인 객체는 dataclass/Pydantic, 단순 payload는 `TypedDict`로 분리하는 기준이 있다
- [ ] 서비스 인터페이스 추상화는 `Protocol` 우선인지 합의했다

타입 시스템은 문법보다 팀 규칙이 더 중요하다. 규칙이 없으면 같은 코드베이스 안에서 타입 스타일이 제각각이 된다.

---

## 언제 어떤 도구를 고르면 좋을까?

짧게 기준을 정리하면 다음과 같다.

### `TypedDict`

- JSON payload
- 이벤트 메시지
- key 기반 경량 데이터
- 구조만 중요하고 행동은 중요하지 않음

### `dataclass`

- 내부 도메인 모델
- 생성 이후 다루기 쉬운 객체가 필요함
- 필드 기반 비교/표현이 유용함

### Pydantic 같은 런타임 모델

- 입력 검증이 중요함
- 파싱/변환/기본값 처리 규칙이 많음
- 외부 입력을 신뢰할 수 없음

### `Protocol`

- 서비스와 인프라 경계를 분리하고 싶음
- 테스트 대체 객체를 쉽게 만들고 싶음
- 상속보다 계약이 중요함

### `Generic`

- 공통 래퍼를 여러 타입에 재사용해야 함
- 재사용하면서 호출부 타입 정보도 보존해야 함

도구를 섞는 감각이 중요하다. 예를 들어 "외부 입력은 Pydantic으로 검증 → 내부 경량 전달은 `TypedDict` 또는 dataclass → 서비스 경계는 `Protocol` → 공통 래퍼는 `Generic`" 같은 조합은 꽤 실전적이다.

---

## 한 줄 정리

Python 타입 힌트의 진짜 가치는 문법 예쁘게 쓰는 데 있지 않다. **`TypedDict`로 데이터 계약을 명확히 하고, `Protocol`로 결합도를 낮추고, `Generic`으로 재사용성을 확보하면 대규모 코드베이스의 변경 비용을 눈에 띄게 줄일 수 있다.**
