---
layout: post
title: "Python 데이터 모델링 실전: dataclass, frozen, slots, Pydantic, DTO와 도메인 객체를 운영 코드에서 나누는 법"
date: 2026-06-06 11:50:00 +0900
categories: [python]
tags: [study, python, dataclass, pydantic, dto, domain-model, value-object, slots, frozen, validation, architecture]
permalink: /python/2026/06/06/study-python-dataclass-slots-frozen-pydantic-domain-dto.html
---

## 배경: Python 데이터 모델링은 "클래스를 예쁘게 쓰는 법"이 아니라 변경 가능성과 신뢰 경계를 설계하는 일이다

Python 백엔드 코드가 어느 정도 커지면 거의 같은 논쟁이 반복된다.

- 요청/응답 스키마는 Pydantic으로 만들었는데 내부 서비스 객체도 그대로 써도 되는가
- `dict`가 편한데 굳이 `dataclass`를 써야 하는가
- `frozen=True`를 쓰면 불변 객체가 되는가, 아니면 불편하기만 한가
- `slots=True`는 성능 최적화인가, 운영 코드 기본값인가
- DB ORM 모델, API DTO, 도메인 객체, 이벤트 payload를 하나로 합치면 왜 나중에 깨지는가
- 검증은 Pydantic에서 끝났는데 도메인 객체에서도 또 검증해야 하는가
- 타입 힌트가 있는데 런타임 검증이 왜 필요한가

작은 프로젝트에서는 `dict` 하나로도 충분해 보인다.
FastAPI 요청 모델을 그대로 서비스에 넘기고,
SQLAlchemy 모델을 그대로 응답으로 직렬화하고,
필요하면 중간중간 `payload["status"] = "done"`처럼 값을 고치면 빠르다.

문제는 서비스가 커진 뒤에 나타난다.

- 같은 필드가 API에서는 optional인데 내부에서는 required다
- DB에는 `NULL`이 가능하지만 도메인 규칙상 실제 처리 시점에는 값이 반드시 있어야 한다
- 외부 API에서 받은 문자열 상태값이 내부 상태 전이에 그대로 섞인다
- 테스트가 객체를 쉽게 만들려고 규칙을 우회한다
- 캐시 키나 이벤트 payload에 mutable 객체가 들어가서 나중에 값이 바뀐다
- `dict` 기반 코드가 많아져 리팩터링 도구와 타입 체커가 도와주기 어렵다
- Pydantic 모델이 도메인 로직을 먹어 들어가면서 웹 프레임워크와 비즈니스 규칙이 한 덩어리가 된다

이런 문제는 문법을 몰라서 생기지 않는다.
대부분 **데이터가 어느 경계에서 신뢰 가능한 형태로 바뀌는지**를 정하지 않았기 때문에 생긴다.

오늘 글은 중급 이상 Python 개발자를 기준으로 데이터 모델링을 운영 코드 관점에서 정리한다.

- `dict`, `NamedTuple`, `dataclass`, Pydantic 모델을 어디에 써야 하는가
- `frozen`, `slots`, `kw_only`, `InitVar`, `__post_init__`가 실제로 해결하는 문제는 무엇인가
- DTO와 도메인 객체를 왜 분리해야 하는가
- 값 객체(Value Object)를 언제 만들고, 언제 과한 추상화가 되는가
- API, DB, worker, event payload 사이에서 검증과 변환을 어떻게 배치해야 하는가
- 흔한 실수와 체크리스트는 무엇인가

핵심 결론부터 말하면 이렇다.

- Pydantic은 **경계 입력 검증과 직렬화**에 강하고, `dataclass`는 **내부 불변 데이터 구조와 도메인 표현**에 강하다
- DTO는 이동을 위한 모양이고, 도메인 객체는 규칙을 지키는 상태다
- `frozen=True`는 만능 불변성이 아니라 "재할당을 막는 신호"에 가깝다
- `slots=True`는 성능보다도 "객체 모양을 닫는 효과" 때문에 운영 코드에서 가치가 있다
- 좋은 데이터 모델링은 클래스를 많이 만드는 것이 아니라 **경계별로 허용되는 변경과 책임을 좁히는 것**이다

---

## 먼저 큰 그림: Python 객체는 네 가지 층으로 나눠야 덜 흔들린다

실무 애플리케이션에서 데이터는 보통 아래 경로를 지난다.

1. 외부 입력: HTTP request, message queue, CSV, webhook, CLI argument
2. 애플리케이션 명령: use case가 처리할 수 있는 내부 입력
3. 도메인 객체: 규칙과 상태 전이를 가진 핵심 모델
4. 외부 출력: HTTP response, event payload, DB row, cache value

초기 코드에서는 이 네 층이 하나의 객체로 합쳐지기 쉽다.

```python
class Order(BaseModel):
    id: int | None = None
    user_id: int
    status: str = "PENDING"
    total_amount: int
    coupon_code: str | None = None
```

이 모델 하나를 API request에도 쓰고,
service 인자로도 쓰고,
DB 저장 전 임시 객체로도 쓰고,
응답에도 쓰면 처음에는 편하다.
하지만 시간이 지나면 필드 의미가 충돌한다.

- 생성 요청에는 `id`가 없어야 한다
- 응답에는 `id`가 있어야 한다
- 내부 결제 처리에는 `total_amount`가 이미 계산된 값이어야 한다
- DB row에는 마이그레이션 때문에 오래된 `status` 값이 있을 수 있다
- 이벤트 payload에는 개인정보가 빠져야 한다

한 객체가 너무 많은 경계를 대표하면 필드는 점점 느슨해진다.
`Optional`이 늘고,
기본값이 늘고,
서비스 코드에는 `if order.id is None` 같은 방어 로직이 쌓인다.

그래서 큰 그림은 단순하게 잡는 편이 좋다.

- 외부 입력 모델: 받아도 되는 형태를 넓게 열고, 오류 메시지를 친절하게 만든다
- 애플리케이션 명령 객체: use case 실행에 필요한 값만 담는다
- 도메인 객체: 유효한 상태만 만들 수 있게 한다
- 출력 모델: 소비자에게 공개할 형태만 담는다

이렇게 나누면 클래스 수는 조금 늘지만, 각 클래스의 고민은 줄어든다.
서비스가 커질수록 이 편이 읽기 쉽고 테스트하기 쉽다.

---

## 핵심 개념 1: `dict`는 경계 초반에는 좋지만 코어로 들어오면 비용이 급격히 커진다

Python에서 `dict`는 가장 강력하고 편한 데이터 구조다.
JSON과 잘 맞고, 동적으로 필드를 추가하기 쉽고, 테스트 데이터 만들기도 쉽다.
문제는 편한 만큼 계약이 약하다는 점이다.

```python
def approve_order(payload: dict) -> None:
    if payload["status"] != "PENDING":
        raise ValueError("cannot approve")

    payload["status"] = "APPROVED"
```

이 코드는 짧지만 숨은 질문이 많다.

- `payload`에는 어떤 키가 반드시 있어야 하는가
- `status`는 문자열인가 enum인가
- 함수가 입력 객체를 수정해도 되는가
- `payload["status"]`가 외부 API 원문인지 내부 표준값인지 알 수 있는가
- 호출자는 이 함수 이후 payload가 바뀐다는 사실을 기대하는가

작은 스크립트에서는 괜찮다.
하지만 서비스 코어에서는 `dict`가 늘수록 리팩터링이 어려워진다.
키 이름은 문자열이라 변경 추적이 약하고,
타입 체커는 깊은 구조를 충분히 보호하지 못하고,
실수는 런타임 특정 분기에서야 터진다.

`dict`를 금지하자는 뜻은 아니다.
좋은 사용 위치가 있다.

- 원본 JSON을 잠깐 담는 adapter 계층
- 관측 로그의 extra 필드
- unknown field를 보존해야 하는 integration layer
- 스키마가 자주 바뀌는 외부 payload의 임시 표현
- 작은 테스트 fixture의 중간 재료

반대로 아래 위치에서는 구조화된 객체가 낫다.

- 도메인 규칙이 붙는 값
- 여러 함수가 공유하는 내부 명령
- 캐시 키, 이벤트, 상태 전이처럼 안정성이 필요한 값
- 리팩터링과 타입 체커 지원을 받아야 하는 핵심 경로

실무 기준은 이렇게 잡으면 된다.

> 경계 바깥쪽에서는 `dict`를 받아도 되지만, 코어로 들어오기 전에는 이름 있는 타입으로 바꿔라.

---

## 핵심 개념 2: Pydantic은 입구와 출구에 강하고, 도메인 중심부의 기본 도구는 아닐 때가 많다

FastAPI를 쓰면 Pydantic 모델은 거의 자동으로 도입된다.
요청 검증,
응답 직렬화,
OpenAPI 문서화,
타입 변환,
오류 메시지까지 한 번에 해결해 준다.

```python
from pydantic import BaseModel, Field


class CreateOrderRequest(BaseModel):
    user_id: int
    product_id: int
    quantity: int = Field(gt=0, le=100)
    coupon_code: str | None = None
```

이 모델은 HTTP 입구에서 아주 좋다.
하지만 이걸 그대로 도메인 객체로 쓰기 시작하면 책임이 섞인다.

Pydantic 모델의 주 관심사는 대체로 아래다.

- 외부 입력을 Python 값으로 파싱한다
- 필드별 검증 오류를 구조화한다
- JSON 직렬화와 역직렬화를 제공한다
- alias, default, extra field, schema 문서화를 다룬다

반면 도메인 객체의 주 관심사는 다르다.

- 유효한 상태만 표현한다
- 상태 전이 규칙을 지킨다
- 외부 표현 방식과 독립적으로 비즈니스 언어를 유지한다
- 테스트에서 프레임워크 없이 만들고 사용할 수 있다

그래서 아래처럼 한 번 변환해 주는 경계를 두는 편이 안정적이다.

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CreateOrderCommand:
    user_id: int
    product_id: int
    quantity: int
    coupon_code: str | None


def to_command(request: CreateOrderRequest) -> CreateOrderCommand:
    return CreateOrderCommand(
        user_id=request.user_id,
        product_id=request.product_id,
        quantity=request.quantity,
        coupon_code=request.coupon_code,
    )
```

겉보기에는 중복처럼 보인다.
하지만 두 객체가 담당하는 실패가 다르다.

- `CreateOrderRequest`: 클라이언트가 보낸 JSON이 문법적으로 맞는가
- `CreateOrderCommand`: use case가 실행되기 위해 필요한 값이 준비되었는가

이 차이가 중요하다.
API가 GraphQL로 바뀌거나,
worker message에서 같은 use case를 호출하거나,
CLI에서 주문 생성 배치를 돌릴 때,
도메인 코어는 HTTP request 모델에 묶이지 않는다.

### Pydantic을 내부에서도 써도 되는 경우

물론 Pydantic을 내부에서 절대 쓰지 말라는 말은 아니다.
아래 상황에서는 내부 모델로도 충분히 유용하다.

- 외부 설정 파일을 읽어 strongly typed config로 만들 때
- 여러 외부 시스템 payload를 표준화할 때
- 런타임 검증이 중요한 data pipeline 중간 단계
- JSON schema 생성이 내부 계약에도 필요한 경우
- 데이터 과학, ML feature payload처럼 구조가 크고 검증 규칙이 많은 경우

다만 이때도 질문은 남는다.

> 이 모델이 도메인 규칙을 담는가, 아니면 경계 payload를 검증하는가?

답이 후자라면 Pydantic이 잘 맞는다.
답이 전자라면 `dataclass`나 일반 class가 더 단단한 선택일 수 있다.

---

## 핵심 개념 3: `dataclass`는 boilerplate 제거 도구가 아니라 값의 형태를 닫는 도구다

`dataclass`를 처음 보면 생성자와 `repr`을 자동 생성하는 문법 설탕처럼 느껴진다.
그 정도로만 써도 도움이 되지만, 실무 가치는 더 크다.

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class Money:
    amount: int
    currency: str

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError("amount must be non-negative")
        if self.currency not in {"KRW", "USD", "JPY"}:
            raise ValueError("unsupported currency")
```

이 코드는 단순히 `__init__`을 줄인 것이 아니다.
아래 계약을 만든다.

- `Money`는 `amount`와 `currency`만 가진다
- 생성 이후 필드 재할당은 막는다
- 인자는 keyword로만 받는다
- 음수 금액은 만들 수 없다
- 지원하지 않는 통화도 만들 수 없다

도메인 코드에서는 이런 작은 계약이 중요하다.
`int`와 `str`만 전달하면 빠르지만, 의미가 사라진다.

```python
def refund(amount: int, currency: str) -> None:
    ...
```

이 함수는 편하지만 실수에 약하다.

- `amount`가 원 단위인지 센트 단위인지 모른다
- `currency`에 어떤 값이 가능한지 모른다
- 음수 금액을 호출자가 넘겨도 함수 내부까지 들어온다

값 객체로 감싸면 호출부가 조금 길어지지만 의미가 분명해진다.

```python
refund(Money(amount=10_000, currency="KRW"))
```

실무에서 중요한 데이터는 대부분 primitive가 아니다.
`email`, `user_id`, `order_id`, `money`, `date_range`, `percentage`, `page_size` 같은 값은 규칙을 가진다.
그 규칙이 여러 곳에 흩어지기 시작하면 값 객체로 올릴 시점이다.

---

## 핵심 개념 4: `frozen=True`는 "완전한 불변"이 아니라 "재할당 금지와 의도 표현"이다

`dataclass(frozen=True)`를 쓰면 필드 재할당이 막힌다.

```python
@dataclass(frozen=True)
class UserSnapshot:
    id: int
    email: str


user = UserSnapshot(id=1, email="a@example.com")
user.email = "b@example.com"  # FrozenInstanceError
```

이것만으로도 큰 효과가 있다.
함수 하나가 전달받은 객체를 몰래 바꾸는 일을 막을 수 있고,
객체가 값처럼 다뤄진다는 신호를 줄 수 있다.

하지만 `frozen=True`를 과신하면 안 된다.
필드 안에 mutable 객체가 있으면 내부 값은 여전히 바뀔 수 있다.

```python
@dataclass(frozen=True)
class Cart:
    item_ids: list[int]


cart = Cart(item_ids=[1, 2])
cart.item_ids.append(3)  # 가능하다
```

이 코드는 `cart.item_ids` 재할당을 막을 뿐, 리스트 내부 변경은 막지 않는다.
진짜 값 객체에 가깝게 만들려면 immutable collection을 써야 한다.

```python
@dataclass(frozen=True, slots=True)
class CartSnapshot:
    item_ids: tuple[int, ...]

    def __post_init__(self) -> None:
        if not self.item_ids:
            raise ValueError("cart must not be empty")
```

`frozen=True`는 아래 상황에서 특히 유용하다.

- 명령 객체처럼 생성 후 바뀌면 안 되는 값
- 이벤트 payload처럼 발행 후 내용이 고정되어야 하는 값
- 캐시 키나 해시 가능한 값 객체
- 상태 전이 함수의 입력과 출력이 분명해야 하는 도메인 모델
- 테스트 fixture가 중간에 오염되면 안 되는 경우

반대로 아래 상황에서는 조심해야 한다.

- ORM entity처럼 lifecycle 동안 상태가 변해야 하는 객체
- 대형 데이터 구조를 조금씩 갱신하는 hot path
- 내부에 list, dict, set이 많아 사실상 불변이 아닌 객체
- 값을 바꿀 때마다 새 객체를 만들어야 해서 비용이 큰 모델

실무에서는 "모든 객체를 frozen으로 만들자"보다,
"경계를 넘는 값과 도메인 값 객체는 기본적으로 frozen을 검토하자"가 더 균형 잡힌 규칙이다.

---

## 핵심 개념 5: `slots=True`는 메모리 최적화보다 객체 모양을 닫는 효과가 더 중요하다

Python 객체는 기본적으로 인스턴스마다 `__dict__`를 가진다.
그래서 선언하지 않은 속성도 나중에 붙일 수 있다.

```python
@dataclass
class User:
    id: int
    email: str


user = User(id=1, email="a@example.com")
user.emali = "typo@example.com"  # 오타인데 새 속성으로 붙을 수 있다
```

이런 실수는 생각보다 무섭다.
특히 테스트가 느슨하거나 특정 분기에서만 해당 속성을 읽으면 늦게 발견된다.

`slots=True`를 쓰면 선언된 필드 외 속성 추가가 막힌다.

```python
@dataclass(slots=True)
class User:
    id: int
    email: str
```

장점은 세 가지다.

1. 오타 속성이 조용히 생기는 일을 막는다
2. 많은 객체를 만들 때 메모리 사용량이 줄 수 있다
3. 객체가 어떤 필드를 갖는지 더 닫힌 계약이 된다

물론 주의점도 있다.

- dynamic attribute를 의도적으로 붙이는 라이브러리와 충돌할 수 있다
- 일부 serialization, mocking, ORM 도구가 `__dict__`를 기대할 수 있다
- 상속 구조에서 slots를 섞으면 이해 비용이 올라간다

그래도 순수 값 객체나 내부 DTO에서는 `slots=True`를 기본 후보로 두는 편이 좋다.
특히 이벤트를 많이 만들거나,
배치에서 수십만 개 객체를 생성하거나,
타이포 속성을 막고 싶다면 효과가 분명하다.

다만 `slots=True`를 성능 미신처럼 쓰면 안 된다.
성능은 측정해야 한다.
이 글에서 더 중요한 포인트는 성능보다 **객체의 모양을 닫아서 코드 계약을 좁히는 것**이다.

---

## 핵심 개념 6: `kw_only=True`는 필드 순서 변경과 인자 뒤섞임을 막는 작은 안전장치다

도메인 값 객체는 필드가 많아질수록 positional argument가 위험해진다.

```python
@dataclass(frozen=True)
class ShippingAddress:
    zipcode: str
    city: str
    line1: str
    line2: str | None


address = ShippingAddress("Seoul", "06236", "Gangnam-daero", None)
```

타입이 모두 `str`에 가까우면 순서가 바뀌어도 타입 체커가 잘 잡지 못한다.
`kw_only=True`를 쓰면 호출부가 길어지는 대신 실수를 줄인다.

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class ShippingAddress:
    zipcode: str
    city: str
    line1: str
    line2: str | None = None


address = ShippingAddress(
    zipcode="06236",
    city="Seoul",
    line1="Gangnam-daero",
)
```

운영 코드에서는 이런 사소한 안전장치가 리팩터링 비용을 줄인다.
필드 순서를 바꾸거나 새 필드를 추가해도 호출부 의미가 덜 흔들린다.

내 기준에서 아래 객체에는 `kw_only=True`를 거의 기본으로 둔다.

- 필드가 3개 이상인 값 객체
- 같은 타입 필드가 여러 개인 DTO
- 금액, 주소, 기간, 정책 옵션처럼 순서 실수가 치명적인 객체
- 장기적으로 필드가 늘 가능성이 높은 내부 명령 객체

---

## 실무 예시 1: API 요청 모델과 use case 명령 객체를 분리하기

주문 생성 API를 예로 보자.
HTTP 요청에서는 클라이언트 친화적인 검증과 오류 메시지가 중요하다.

```python
from pydantic import BaseModel, Field, field_validator


class CreateOrderRequest(BaseModel):
    user_id: int = Field(gt=0)
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0, le=100)
    coupon_code: str | None = Field(default=None, max_length=50)

    @field_validator("coupon_code")
    @classmethod
    def normalize_coupon_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip().upper()
        return value or None
```

이 모델은 HTTP 계층에 잘 맞는다.
하지만 service 계층은 Pydantic을 몰라도 되어야 한다.
그래서 내부 명령 객체로 변환한다.

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class CreateOrderCommand:
    user_id: int
    product_id: int
    quantity: int
    coupon_code: str | None = None

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")
```

여기서 "Pydantic에서 이미 quantity를 검증했는데 왜 또 검증하나"라는 질문이 나온다.
답은 호출 경로가 하나가 아니기 때문이다.

오늘은 HTTP API만 있을 수 있다.
내일은 아래 경로가 생긴다.

- 관리자 CLI에서 주문 보정
- message queue에서 주문 재처리
- 테스트에서 use case 직접 호출
- 배치에서 CSV를 읽어 주문 생성
- 내부 API gateway가 다른 포맷으로 호출

도메인 코어가 HTTP 검증에만 의존하면 다른 경로에서 쉽게 깨진다.
내부 명령 객체의 검증은 외부 오류 메시지를 예쁘게 만들기 위한 검증이 아니다.
**use case 실행 전제 조건을 지키기 위한 마지막 문**이다.

변환 코드는 adapter에 둔다.

```python
def create_order_command_from_request(
    request: CreateOrderRequest,
) -> CreateOrderCommand:
    return CreateOrderCommand(
        user_id=request.user_id,
        product_id=request.product_id,
        quantity=request.quantity,
        coupon_code=request.coupon_code,
    )
```

이 함수가 단순해 보여도 가치가 있다.
외부 표현과 내부 표현이 달라지는 시점을 한곳에 모은다.
나중에 `couponCode` alias, legacy 필드, feature flag, 기본값 보정이 들어와도 도메인 서비스가 흔들리지 않는다.

---

## 실무 예시 2: 도메인 객체는 상태 전이를 메서드로 감싸야 한다

DTO는 데이터를 옮긴다.
도메인 객체는 규칙을 지킨다.
이 차이를 놓치면 아래 같은 코드가 생긴다.

```python
@dataclass
class Order:
    id: int
    status: str
    paid_amount: int


def cancel_order(order: Order) -> None:
    if order.status == "SHIPPED":
        raise ValueError("cannot cancel shipped order")
    order.status = "CANCELED"
```

처음엔 충분해 보인다.
하지만 상태 전이 규칙이 늘면 서비스 함수마다 같은 조건이 흩어진다.

- 결제 완료 전에는 배송할 수 없다
- 배송 후에는 취소할 수 없다
- 환불 완료 후에는 결제 금액을 바꿀 수 없다
- 특정 프로모션 주문은 부분 취소가 제한된다

이럴 때는 도메인 객체가 상태 전이를 직접 제공하는 편이 낫다.

```python
from dataclasses import dataclass, replace
from enum import StrEnum


class OrderStatus(StrEnum):
    PENDING = "PENDING"
    PAID = "PAID"
    SHIPPED = "SHIPPED"
    CANCELED = "CANCELED"


@dataclass(frozen=True, slots=True, kw_only=True)
class Order:
    id: int
    user_id: int
    status: OrderStatus
    paid_amount: int

    def mark_paid(self, amount: int) -> "Order":
        if self.status != OrderStatus.PENDING:
            raise ValueError("only pending order can be paid")
        if amount <= 0:
            raise ValueError("paid amount must be positive")
        return replace(self, status=OrderStatus.PAID, paid_amount=amount)

    def cancel(self) -> "Order":
        if self.status == OrderStatus.SHIPPED:
            raise ValueError("shipped order cannot be canceled")
        if self.status == OrderStatus.CANCELED:
            return self
        return replace(self, status=OrderStatus.CANCELED)
```

여기서는 frozen 객체를 쓰고 상태 변경 시 새 객체를 반환했다.
이 방식은 상태 전이가 명확하고 테스트하기 쉽다.

```python
paid_order = order.mark_paid(amount=20_000)
canceled_order = paid_order.cancel()
```

물론 모든 도메인 entity를 immutable하게 만들 필요는 없다.
ORM과 강하게 연결된 엔티티는 mutable 방식이 더 자연스러울 수 있다.
하지만 상태 전이를 메서드로 감싼다는 원칙은 유지하는 편이 좋다.

중요한 점은 이거다.

> 외부 코드가 `order.status = "CANCELED"`를 마음대로 할 수 있다면 도메인 규칙은 객체 밖으로 새고 있는 것이다.

---

## 실무 예시 3: DB ORM 모델을 도메인 모델로 착각하지 않기

SQLAlchemy 같은 ORM 모델은 DB row와 객체를 연결해 준다.
아주 강력하지만, ORM 모델이 곧 도메인 모델이라고 단정하면 문제가 생긴다.

```python
class OrderRow(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int]
    status: Mapped[str]
    paid_amount: Mapped[int]
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
```

이 모델의 관심사는 DB 저장과 로딩이다.

- 컬럼 타입
- primary key
- nullable 여부
- index
- relationship
- lazy loading
- migration 호환성

도메인 모델의 관심사는 다르다.

- 상태 전이
- 규칙
- 불변 조건
- 비즈니스 언어
- 테스트 가능성

둘을 항상 분리해야 한다는 뜻은 아니다.
단순 CRUD 서비스에서는 ORM 모델 하나로 충분할 수 있다.
하지만 아래 신호가 보이면 분리를 고려해야 한다.

- ORM relationship 로딩 여부가 비즈니스 로직 결과를 바꾼다
- 테스트에서 DB 세션 없이는 도메인 규칙을 검증하기 어렵다
- API 응답 때문에 ORM 모델에 직렬화 속성이 계속 붙는다
- migration 때문에 nullable인 필드가 도메인에서는 required인데 코드가 계속 방어한다
- 상태 전이 메서드가 DB flush, lazy loading, transaction과 얽힌다

분리하면 mapper가 필요하다.

```python
def order_from_row(row: OrderRow) -> Order:
    return Order(
        id=row.id,
        user_id=row.user_id,
        status=OrderStatus(row.status),
        paid_amount=row.paid_amount,
    )


def apply_order_to_row(order: Order, row: OrderRow) -> None:
    row.status = order.status.value
    row.paid_amount = order.paid_amount
```

이 mapper는 귀찮아 보인다.
하지만 이 작은 비용으로 DB 구조와 도메인 규칙이 독립적으로 변할 여지를 얻는다.

실무에서는 완전한 순수 도메인 모델과 ORM 일체형 모델 사이에서 선택하면 된다.

- CRUD 중심, 규칙 적음: ORM 모델에 얇은 메서드 추가
- 규칙 많음, 상태 전이 복잡: 도메인 모델 분리
- 성능상 대량 조회 중심: read model은 별도 DTO로 단순화
- 이벤트 소싱 또는 audit 중요: 도메인 이벤트 모델을 분리

정답은 하나가 아니다.
중요한 것은 ORM 모델을 쓰더라도 그 책임이 DB 영속성에 강하게 묶여 있다는 사실을 잊지 않는 것이다.

---

## 실무 예시 4: 이벤트 payload는 도메인 객체를 그대로 던지지 않는다

주문 결제가 완료되면 이벤트를 발행한다고 해 보자.
가장 쉬운 코드는 도메인 객체를 그대로 serialize하는 것이다.

```python
event_bus.publish("order.paid", order)
```

이 방식은 빠르지만 위험하다.

- 도메인 객체에 새 필드가 추가되면 이벤트 계약도 조용히 바뀐다
- 내부 필드가 외부 consumer에게 노출될 수 있다
- consumer가 필요한 값과 도메인 객체가 가진 값이 다를 수 있다
- 이벤트는 과거 계약을 오래 유지해야 하는데 도메인 모델은 더 자주 변한다

이벤트는 별도 payload로 만드는 편이 안전하다.

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class OrderPaidEvent:
    event_id: str
    order_id: int
    user_id: int
    paid_amount: int
    occurred_at: datetime
    schema_version: int = 1
```

그리고 명시적으로 변환한다.

```python
def order_paid_event_from_order(
    order: Order,
    *,
    event_id: str,
    occurred_at: datetime,
) -> OrderPaidEvent:
    if order.status != OrderStatus.PAID:
        raise ValueError("order must be paid")

    return OrderPaidEvent(
        event_id=event_id,
        order_id=order.id,
        user_id=order.user_id,
        paid_amount=order.paid_amount,
        occurred_at=occurred_at,
    )
```

여기서 event payload는 도메인 객체보다 더 보수적인 계약이다.
한 번 발행된 이벤트는 consumer, archive, replay, monitoring에 남는다.
따라서 내부 객체 변경과 이벤트 스키마 변경은 분리해야 한다.

Pydantic을 이벤트 payload에 쓰는 것도 괜찮다.
특히 JSON 직렬화와 schema 문서화가 중요하면 장점이 크다.
다만 그 경우에도 이벤트 모델은 도메인 객체와 별도 타입으로 두는 편이 낫다.

---

## 트레이드오프 1: 클래스가 늘어나는 비용과 경계가 흐려지는 비용

DTO와 도메인 객체를 나누자는 이야기를 하면 가장 먼저 나오는 반론은 "클래스가 너무 많아진다"다.
맞는 지적이다.
분리는 공짜가 아니다.

분리 비용은 아래처럼 나타난다.

- 파일과 클래스가 늘어난다
- mapper 코드가 생긴다
- 비슷한 필드가 반복된다
- 작은 변경에도 여러 타입을 고쳐야 할 수 있다
- 초보 팀원에게 구조 설명이 필요하다

반대로 합쳤을 때의 비용도 있다.

- `Optional`이 늘어 의미가 느슨해진다
- 한 필드의 변경 이유가 여러 계층에 걸친다
- API 호환성 때문에 도메인 객체가 낡은 필드를 계속 품는다
- DB 제약과 도메인 제약이 뒤섞인다
- 테스트에서 불필요한 프레임워크나 DB 객체가 따라온다
- 상태 전이 규칙이 서비스 함수 곳곳으로 퍼진다

그래서 무조건 분리도, 무조건 통합도 좋지 않다.
판단 기준은 변경 속도와 책임 차이다.

아래 질문에 "예"가 많으면 분리가 이긴다.

- 외부 API 스펙과 내부 규칙의 변경 속도가 다른가
- DB schema와 도메인 언어가 다르게 진화하는가
- 같은 use case를 HTTP, worker, CLI에서 함께 호출하는가
- 이벤트 계약을 장기간 유지해야 하는가
- 상태 전이나 검증 규칙이 단순 CRUD를 넘어서는가
- 테스트에서 외부 프레임워크 없이 코어를 실행하고 싶은가

반대로 아래 조건이면 통합이 더 낫다.

- 작은 관리자 CRUD 화면이다
- 도메인 규칙보다 DB 저장이 핵심이다
- 모델 변경이 드물고 팀이 작다
- mapper가 실제 버그보다 더 많은 복잡도를 만든다
- 읽기 전용 projection이라 단순 직렬화만 필요하다

좋은 아키텍처는 항상 비용을 숨기지 않는다.
분리의 비용과 결합의 비용을 비교해서 더 싼 쪽을 고르는 것이다.

---

## 트레이드오프 2: 런타임 검증과 정적 타입 검사의 역할을 혼동하지 않기

Python 타입 힌트는 강력해졌지만 런타임 검증을 대체하지 않는다.

```python
@dataclass(frozen=True)
class Page:
    size: int
```

이 코드는 `size`가 int라고 말하지만, 런타임에 자동으로 막지는 않는다.

```python
page = Page(size="100")  # 실행 자체는 가능하다
```

Mypy나 Pyright를 잘 쓰면 정적 분석 단계에서 잡을 수 있다.
하지만 외부 입력은 런타임에 들어온다.
JSON, DB row, queue message, environment variable은 타입 체커가 보장하지 않는다.

그래서 역할을 나눠야 한다.

- 타입 힌트: 개발 중 설계 계약과 리팩터링 안전망
- Pydantic: 외부 입력 파싱과 런타임 검증
- `dataclass.__post_init__`: 도메인 불변 조건 검증
- DB constraint: 최종 영속성 무결성
- 테스트: 실제 시나리오에서 규칙 유지 확인

이 중 하나가 나머지를 완전히 대체하지 않는다.

예를 들어 수량은 아래 여러 층에서 보호될 수 있다.

```python
class CreateOrderRequest(BaseModel):
    quantity: int = Field(gt=0, le=100)
```

```python
@dataclass(frozen=True, slots=True)
class Quantity:
    value: int

    def __post_init__(self) -> None:
        if not 1 <= self.value <= 100:
            raise ValueError("quantity must be between 1 and 100")
```

```sql
CHECK (quantity > 0)
```

중복처럼 보이지만 서로 다른 실패를 막는다.

- API 요청 모델은 사용자 오류를 빠르고 친절하게 돌려준다
- 값 객체는 내부 호출 경로가 늘어도 규칙을 지킨다
- DB constraint는 버그나 우회 경로가 있어도 저장소 무결성을 지킨다

실무에서는 "검증을 한 번만 하자"보다 "각 경계가 책임지는 검증을 하자"가 더 안전하다.

---

## 트레이드오프 3: 불변 객체와 성능, 그리고 ergonomics

불변 데이터 구조는 버그를 줄인다.
하지만 모든 곳에 쓰면 코드가 장황해질 수 있다.

```python
order = replace(order, status=OrderStatus.PAID)
order = replace(order, paid_amount=20_000)
order = replace(order, updated_at=now)
```

상태 갱신이 잦은 객체에서는 불편하고 비효율적일 수 있다.
반대로 상태 전이가 드문 핵심 객체에서는 명확성이 더 중요할 수 있다.

판단 기준은 아래와 같다.

- 객체가 값처럼 전달되는가: frozen이 유리
- lifecycle 동안 점진적으로 변경되는가: mutable이 유리
- 변경 이력이 중요한가: immutable + 새 객체 반환이 유리
- ORM이 추적해야 하는가: mutable entity가 유리
- hot path에서 수백만 번 갱신되는가: 측정 후 결정
- 동시성 경계나 캐시 키로 쓰이는가: immutable이 유리

Python에서 immutable 설계는 함수형 순수성을 과시하기 위한 것이 아니다.
의도하지 않은 공유 변경을 줄이고, 상태 변화 지점을 드러내기 위한 실용적 선택이다.

---

## 흔한 실수 1: 모든 모델 이름을 `User`, `Order`, `Item`으로만 짓는다

이름이 모호하면 책임도 모호해진다.

```python
class User(BaseModel):
    ...
```

이 이름만 보면 무엇인지 알기 어렵다.

- API 요청인가
- API 응답인가
- DB row인가
- 도메인 entity인가
- 인증 principal인가
- 외부 SaaS에서 온 user payload인가

실무에서는 이름에 역할을 넣는 편이 낫다.

- `CreateUserRequest`
- `UserResponse`
- `UserRow`
- `UserProfile`
- `AuthenticatedUser`
- `UserSnapshot`
- `RegisterUserCommand`
- `ExternalUserPayload`

이름이 조금 길어져도 읽는 사람은 훨씬 빨리 이해한다.
특히 Python은 패키지와 타입이 느슨하게 연결되기 쉬워서 이름이 설계 문서 역할을 한다.

---

## 흔한 실수 2: `Optional`로 lifecycle 차이를 덮는다

가장 위험한 냄새 중 하나는 하나의 모델에 `None`이 과도하게 늘어나는 것이다.

```python
@dataclass
class Order:
    id: int | None
    paid_at: datetime | None
    shipped_at: datetime | None
    canceled_at: datetime | None
```

물론 nullable 필드는 현실적으로 필요하다.
하지만 `Optional`이 lifecycle 상태를 대충 덮고 있다면 문제가 된다.

예를 들어 주문 생성 전에는 `id`가 없고,
저장 후에는 `id`가 있고,
결제 전에는 `paid_at`이 없고,
결제 후에는 있어야 한다.

이 차이를 하나의 모델로 표현하면 모든 함수가 방어해야 한다.

```python
def publish_paid_event(order: Order) -> None:
    if order.id is None:
        raise ValueError("order id is required")
    if order.paid_at is None:
        raise ValueError("paid_at is required")
```

상태별 타입을 나누면 일부 방어 로직이 타입 구조로 올라간다.

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class NewOrder:
    user_id: int
    items: tuple[int, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class PaidOrder:
    id: int
    user_id: int
    paid_at: datetime
    paid_amount: int
```

모든 상태를 타입으로 쪼개라는 뜻은 아니다.
하지만 `None` 체크가 여러 곳에서 반복되면 타입이 lifecycle을 제대로 표현하지 못한다는 신호다.

---

## 흔한 실수 3: Pydantic 모델에 도메인 메서드를 계속 추가한다

처음에는 이런 코드가 자연스러워 보인다.

```python
class OrderModel(BaseModel):
    status: str
    paid_amount: int

    def cancel(self) -> None:
        if self.status == "SHIPPED":
            raise ValueError("cannot cancel")
        self.status = "CANCELED"
```

문제는 이 모델이 시간이 지나면서 너무 많은 책임을 갖는다는 점이다.

- API validation
- OpenAPI schema
- JSON serialization
- 도메인 상태 전이
- 외부 응답 alias
- 내부 계산 메서드

Pydantic v2는 훌륭한 도구지만,
`BaseModel`이 있다고 해서 그 위에 모든 것을 올려야 하는 것은 아니다.
도메인 메서드가 많아지고,
프레임워크 없는 테스트가 어려워지고,
response alias 때문에 내부 이름까지 영향을 받기 시작하면 분리할 시점이다.

경계 모델은 경계 모델답게,
도메인 모델은 도메인 모델답게 두는 편이 오래 간다.

---

## 흔한 실수 4: `asdict()`를 무심코 깊은 복사와 직렬화 도구로 쓴다

`dataclasses.asdict()`는 편하지만 생각보다 무겁고 위험할 수 있다.
중첩 dataclass를 재귀적으로 dict로 바꾸고, 내부 객체를 copy한다.
작은 객체에서는 문제 없지만 대형 그래프에서는 비용이 커질 수 있다.

또한 `asdict()` 결과를 외부 응답으로 그대로 내보내면 공개하면 안 되는 필드가 섞일 수 있다.

```python
from dataclasses import asdict

return JSONResponse(asdict(user))
```

이 코드는 빠르지만 계약이 약하다.
응답 DTO를 따로 두거나, 명시적 serializer를 두는 편이 안전하다.

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class UserResponse:
    id: int
    email: str
    display_name: str


def user_response_from_domain(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
    )
```

직렬화는 단순 변환이 아니라 공개 계약이다.
내부 객체를 그대로 dict로 풀어내는 순간 그 내부 구조가 외부 API가 된다.

---

## 흔한 실수 5: 값 객체를 만들고도 primitive를 계속 흘려보낸다

값 객체를 만들었는데 실제 함수 시그니처는 여전히 primitive만 받는 경우가 많다.

```python
@dataclass(frozen=True)
class Email:
    value: str


def send_welcome_email(email: str) -> None:
    ...
```

이러면 `Email` 타입의 장점이 약해진다.
검증된 값이라는 신뢰가 함수 경계에서 사라지기 때문이다.

도메인 내부에서는 가능한 한 값 객체를 유지하는 편이 좋다.

```python
def send_welcome_email(email: Email) -> None:
    ...
```

primitive로 내려가는 시점은 보통 adapter 경계다.

- SMTP client에 문자열 주소 전달
- DB column에 문자열 저장
- JSON response에 문자열 직렬화
- 로그 필드에 문자열 기록

즉 내부에서는 의미 있는 타입을 유지하고,
외부 시스템과 만나는 가장자리에서 primitive로 바꾸는 것이 좋다.

---

## 설계 패턴: 얇은 DTO, 두꺼운 도메인, 명시적 mapper

내가 실무에서 가장 자주 쓰는 기본 형태는 아래다.

```python
# adapters/http/schemas.py
class CreateOrderRequest(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0, le=100)


class OrderResponse(BaseModel):
    id: int
    status: str
    paid_amount: int
```

```python
# application/commands.py
@dataclass(frozen=True, slots=True, kw_only=True)
class CreateOrderCommand:
    user_id: int
    product_id: int
    quantity: int
```

```python
# domain/order.py
@dataclass(frozen=True, slots=True, kw_only=True)
class Order:
    id: int
    user_id: int
    status: OrderStatus
    paid_amount: Money

    def mark_paid(self, amount: Money) -> "Order":
        ...
```

```python
# adapters/http/mappers.py
def command_from_request(
    request: CreateOrderRequest,
    *,
    user_id: int,
) -> CreateOrderCommand:
    return CreateOrderCommand(
        user_id=user_id,
        product_id=request.product_id,
        quantity=request.quantity,
    )


def response_from_order(order: Order) -> OrderResponse:
    return OrderResponse(
        id=order.id,
        status=order.status.value,
        paid_amount=order.paid_amount.amount,
    )
```

이 구조의 핵심은 mapper가 있다는 사실이 아니다.
**변환 위치가 명시적**이라는 점이다.

어떤 팀은 mapper 함수를 싫어한다.
필드 복사가 반복되기 때문이다.
나도 무조건 좋아하지는 않는다.
하지만 서비스가 커지면 암묵 변환보다 명시 변환이 대체로 더 안전하다.

특히 아래 경우에는 mapper를 두는 편이 좋다.

- 외부 필드명과 내부 필드명이 다르다
- 응답에서 일부 필드를 숨겨야 한다
- 도메인 값 객체를 primitive로 풀어야 한다
- schema versioning이 필요하다
- 이벤트 payload가 오래 유지된다
- legacy 필드와 신규 필드가 공존한다

---

## 실전 구조: 패키지 배치를 어떻게 할 것인가

예시 구조는 아래처럼 잡을 수 있다.

```text
app/
  adapters/
    http/
      routes.py
      schemas.py
      mappers.py
    persistence/
      rows.py
      repositories.py
      mappers.py
    messaging/
      events.py
      publishers.py
  application/
    commands.py
    services.py
  domain/
    order.py
    money.py
    errors.py
```

의존 방향은 대략 이렇게 둔다.

- `domain`은 Pydantic, FastAPI, SQLAlchemy를 모른다
- `application`은 domain을 사용하고 use case를 조립한다
- `adapters`는 외부 프레임워크와 domain/application 사이를 변환한다
- mapper는 adapter 쪽에 두는 경우가 많다

이 구조는 작은 프로젝트에는 과할 수 있다.
하지만 HTTP, worker, batch가 함께 커지는 서비스에서는 장점이 크다.
프레임워크 교체가 쉬워져서가 아니다.
실제로 프레임워크 교체는 자주 일어나지 않는다.
더 큰 장점은 **핵심 규칙을 프레임워크 밖에서 테스트하고 이해할 수 있다**는 점이다.

---

## 테스트 전략: 모델 테스트는 getter/setter가 아니라 불변 조건과 변환 경계를 봐야 한다

데이터 모델링 테스트는 단순히 생성자가 동작하는지 확인하는 것이 아니다.
중요한 것은 불변 조건과 변환 경계다.

값 객체 테스트 예시:

```python
def test_money_rejects_negative_amount() -> None:
    with pytest.raises(ValueError):
        Money(amount=-1, currency="KRW")


def test_money_rejects_unknown_currency() -> None:
    with pytest.raises(ValueError):
        Money(amount=1000, currency="ABC")
```

상태 전이 테스트 예시:

```python
def test_shipped_order_cannot_be_canceled() -> None:
    order = Order(
        id=1,
        user_id=10,
        status=OrderStatus.SHIPPED,
        paid_amount=20_000,
    )

    with pytest.raises(ValueError):
        order.cancel()
```

mapper 테스트 예시:

```python
def test_order_response_does_not_expose_internal_fields() -> None:
    order = make_order(internal_note="fraud review")

    response = response_from_order(order)

    assert not hasattr(response, "internal_note")
```

여기서 중요한 것은 테스트 범위다.
Pydantic 자체가 `Field(gt=0)`을 잘 검증하는지는 우리가 테스트할 필요가 적다.
대신 우리 서비스의 중요한 규칙을 테스트해야 한다.

- 어떤 상태 전이가 금지되는가
- 외부 입력이 내부 명령으로 어떻게 정규화되는가
- 응답/이벤트에 어떤 필드를 공개하지 않는가
- legacy payload를 어떻게 보정하는가
- 도메인 객체가 프레임워크 없이 생성되고 동작하는가

---

## 운영 관점: 데이터 모델은 로그, 메트릭, 장애 분석에도 영향을 준다

데이터 모델링은 코드 예쁨의 문제가 아니다.
운영에서도 직접 영향을 준다.

예를 들어 이벤트 payload와 도메인 객체가 분리되어 있으면 장애 분석이 쉬워진다.

- 특정 schema version의 이벤트만 재처리할 수 있다
- 도메인 객체 내부 필드 변경과 consumer 오류를 분리해서 볼 수 있다
- 로그에 남길 안전한 필드와 숨길 필드를 모델 레벨에서 구분할 수 있다
- trace attribute에 올릴 값 객체를 일관되게 직렬화할 수 있다

반대로 모든 것이 `dict`면 장애 분석이 어려워진다.
같은 값이 어떤 경로에서 만들어졌는지 알기 어렵고,
필드명이 조금씩 달라지고,
로그에는 비슷하지만 다른 payload가 쌓인다.

운영에서 좋은 모델은 아래 특징을 가진다.

- 오류 메시지가 어느 경계에서 발생했는지 드러난다
- 모델 이름만 봐도 request, command, domain, event를 구분할 수 있다
- 이벤트 payload는 version을 가진다
- 공개 응답 모델과 내부 모델이 분리되어 민감 필드 노출 가능성이 낮다
- 값 객체가 로그와 메트릭에서 일관된 표현으로 변환된다

즉 데이터 모델링은 관측성과 보안의 일부이기도 하다.

---

## 의사결정 가이드: 어떤 도구를 어디에 쓸 것인가

아래 기준으로 시작하면 대부분의 팀에서 무난하다.

### `dict`

적합한 곳:

- 외부 JSON 원문
- 빠른 one-off script
- unknown field를 보존해야 하는 adapter
- 로그 extra
- 테스트 fixture의 임시 데이터

주의할 곳:

- 도메인 코어
- 여러 함수가 공유하는 상태
- 이벤트 계약
- 캐시 키

### `TypedDict`

적합한 곳:

- dict 형태를 유지해야 하지만 타입 힌트가 필요한 경우
- JSON과 거의 같은 구조를 내부에서 잠깐 다루는 경우
- 런타임 객체 비용 없이 정적 타입 도움만 받고 싶은 경우

주의할 곳:

- 런타임 검증이 필요한 외부 입력
- 메서드와 불변 조건이 필요한 도메인 값

### `dataclass`

적합한 곳:

- 내부 명령 객체
- 값 객체
- 도메인 snapshot
- 이벤트 payload
- 테스트하기 쉬운 순수 데이터 모델

주의할 곳:

- JSON schema와 alias가 중요한 API 경계
- 복잡한 runtime parsing이 필요한 입력
- ORM lifecycle과 강하게 묶인 entity

### Pydantic `BaseModel`

적합한 곳:

- HTTP request/response
- 설정 파일
- 외부 API payload 검증
- JSON schema가 필요한 계약
- 런타임 파싱과 오류 메시지가 중요한 경계

주의할 곳:

- 순수 도메인 로직
- 프레임워크와 무관해야 하는 코어 모델
- 상태 전이 메서드가 많은 entity

### 일반 class

적합한 곳:

- 복잡한 invariant를 생성자에서 강하게 통제해야 하는 경우
- lazy property, cache, 캡슐화가 중요한 entity
- dataclass 자동 생성 메서드보다 직접 구현이 명확한 경우

주의할 곳:

- 단순 데이터 묶음인데 boilerplate만 늘어나는 경우

---

## 코드 리뷰에서 보는 신호

PR에서 데이터 모델링을 볼 때는 아래 질문을 던진다.

- 이 타입의 이름만 보고 어느 경계의 객체인지 알 수 있는가
- 생성된 뒤 값이 바뀌어도 되는가
- 바뀌면 누가 바꿀 수 있는가
- `None`이 실제로 가능한 상태인가, lifecycle 차이를 덮는가
- 외부 입력 검증과 도메인 불변 조건이 구분되어 있는가
- Pydantic 모델이 도메인 규칙까지 너무 많이 품고 있지 않은가
- ORM 모델이 API 응답 요구사항 때문에 오염되고 있지 않은가
- 이벤트 payload가 내부 객체 변경에 따라 조용히 바뀌지 않는가
- `asdict()`, `model_dump()` 결과를 그대로 외부로 노출하지 않는가
- mapper가 단순 반복인지, 실제 경계 변환을 명확히 하는지 판단했는가

이 질문에 답하기 어렵다면 모델 책임이 섞였을 가능성이 높다.

---

## 단계적 리팩터링: 이미 섞인 모델을 한 번에 갈아엎지 않는 법

이미 큰 코드베이스에서 request, ORM, domain이 뒤섞여 있다면 한 번에 정리하려고 하면 위험하다.
단계적으로 가는 편이 좋다.

1. 새 기능부터 request/command/domain/response 이름을 분리한다
2. 기존 모델에 바로 손대기보다 adapter mapper를 먼저 만든다
3. 가장 많은 버그가 나는 값부터 값 객체로 올린다
4. 이벤트 payload는 내부 객체와 먼저 분리한다
5. `Optional` 방어 로직이 반복되는 타입부터 lifecycle을 나눈다
6. 도메인 규칙 테스트를 프레임워크 없이 실행할 수 있게 만든다
7. 마지막에 중복 필드와 낡은 타입을 제거한다

예를 들어 `OrderModel` 하나가 모든 역할을 하고 있다면 바로 다 쪼개지 않는다.
먼저 API 응답만 `OrderResponse`로 분리한다.
그다음 주문 생성 입력을 `CreateOrderCommand`로 분리한다.
그다음 상태 전이가 복잡한 부분만 순수 `Order` 도메인 모델로 옮긴다.

이런 식으로 하면 리팩터링이 기능 개발을 멈추게 하지 않는다.
중요한 것은 완벽한 모델 계층도를 만드는 것이 아니라, 가장 위험한 결합부터 줄이는 것이다.

---

## 심화 1: 값 객체는 검증보다 "연산의 닫힘"을 먼저 생각해야 한다

값 객체를 만들 때 초보적으로는 검증만 생각하기 쉽다.

```python
@dataclass(frozen=True, slots=True)
class Money:
    amount: int
    currency: str

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError("amount must be non-negative")
```

이 정도도 primitive보다 낫다.
하지만 실무에서 값 객체의 진짜 힘은 검증보다 연산에 있다.

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class Money:
    amount: int
    currency: str

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError("amount must be non-negative")
        if self.currency not in {"KRW", "USD"}:
            raise ValueError("unsupported currency")

    def add(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError("currency mismatch")
        return Money(amount=self.amount + other.amount, currency=self.currency)

    def multiply(self, quantity: int) -> "Money":
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        return Money(amount=self.amount * quantity, currency=self.currency)
```

이렇게 하면 금액 계산 규칙이 서비스 코드에 흩어지지 않는다.
특히 통화가 다를 때 더하기를 막는 규칙은 `Money` 안에 있는 것이 자연스럽다.

나쁜 형태는 이런 식이다.

```python
total_amount = item.price_amount * quantity
if item.currency != coupon.currency:
    raise ValueError("currency mismatch")
discounted_amount = total_amount - coupon.amount
```

이 코드는 지금은 짧지만, 여러 서비스 함수에 퍼지면 규칙을 찾기 어려워진다.
반면 `Money`가 연산을 제공하면 호출부가 의도를 드러낸다.

```python
total_price = item.price.multiply(quantity)
final_price = total_price.add(discount.negate())
```

값 객체를 만들지 말지 판단할 때는 아래 질문이 유용하다.

- 이 값에 전용 검증 규칙이 있는가
- 이 값끼리만 가능한 연산이 있는가
- 같은 primitive 타입끼리 섞이면 위험한가
- 단위, 통화, timezone, precision 같은 맥락이 중요한가
- 로그, DB, API에서 표현은 다르지만 내부 의미는 하나인가

이 질문에 "예"가 많으면 값 객체가 유리하다.

반대로 값 객체가 과한 경우도 있다.

- 단순 CRUD 필드라서 규칙이 거의 없다
- 한두 곳에서만 쓰이고 재사용 가능성이 낮다
- 값 객체를 만들었지만 메서드 없이 `.value`만 계속 꺼낸다
- 팀이 아직 도메인 언어를 합의하지 못해 이름이 계속 바뀐다

값 객체는 "모든 primitive를 감싸는 규칙"이 아니다.
반복되는 실수와 흩어진 규칙을 한곳으로 모으는 도구다.

---

## 심화 2: 시간 모델링은 `datetime` 하나로 끝나지 않는다

Python 서비스에서 시간은 데이터 모델링 버그의 단골 원인이다.
`datetime` 타입 하나를 쓴다고 문제가 해결되지 않는다.

자주 보는 문제는 아래와 같다.

- naive datetime과 aware datetime이 섞인다
- DB에는 UTC로 저장하지만 API에는 로컬 시간처럼 보낸다
- 이벤트 발생 시각과 DB 저장 시각을 같은 의미로 쓴다
- 기간의 시작과 끝이 inclusive인지 exclusive인지 불분명하다
- 만료 시간을 `created_at + seconds`로 매번 계산해 오차가 생긴다

시간 값도 도메인 의미가 있으면 별도 타입이 낫다.

```python
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True, slots=True, kw_only=True)
class UtcInstant:
    value: datetime

    def __post_init__(self) -> None:
        if self.value.tzinfo is None:
            raise ValueError("datetime must be timezone-aware")
        if self.value.utcoffset() != timezone.utc.utcoffset(self.value):
            raise ValueError("datetime must be UTC")
```

이 값 객체는 모든 시간 문제를 해결하지 않는다.
하지만 적어도 내부 코어에서 naive datetime이 조용히 퍼지는 일을 막는다.

기간도 마찬가지다.

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class TimeWindow:
    start: UtcInstant
    end: UtcInstant

    def __post_init__(self) -> None:
        if self.start.value >= self.end.value:
            raise ValueError("start must be before end")

    def contains(self, instant: UtcInstant) -> bool:
        return self.start.value <= instant.value < self.end.value
```

여기서 `contains`가 half-open interval을 명시한다.
이 규칙이 없으면 서비스마다 `<=`, `<` 조합이 달라지고 경계 시각 버그가 생긴다.

시간 모델링에서 중요한 원칙은 아래다.

- 내부 저장과 비교는 UTC aware datetime으로 통일한다
- 사용자 표시 timezone은 adapter에서 처리한다
- "발생 시각", "수신 시각", "저장 시각", "처리 시각"을 이름으로 구분한다
- 기간은 inclusive/exclusive 정책을 타입 메서드로 드러낸다
- 테스트에서는 `datetime.now()`를 직접 호출하지 않고 clock을 주입한다

데이터 모델링은 결국 의미를 이름 붙이는 일이다.
시간처럼 당연해 보이는 값일수록 이름을 붙이지 않으면 운영에서 비싸게 돌아온다.

---

## 심화 3: Pydantic v2의 `model_validate`와 `model_dump`는 경계에서만 강하게 쓰는 편이 좋다

Pydantic v2에서는 `model_validate`, `model_dump`, `model_dump_json` 같은 API가 중심이다.
이 API들은 경계 처리에서 매우 유용하다.

```python
request = CreateOrderRequest.model_validate(raw_payload)
payload = response.model_dump(mode="json")
```

문제는 이 편리함이 내부 모델 전체로 퍼질 때다.
예를 들어 도메인 서비스 안에서 여기저기 `model_dump()`가 나오기 시작하면 직렬화 형식과 비즈니스 로직이 섞인다.

```python
def calculate(order: OrderModel) -> dict:
    data = order.model_dump()
    ...
```

이런 코드는 처음에는 편하지만 나중에 아래 질문을 어렵게 만든다.

- 이 dict는 API 응답용인가
- DB 저장용인가
- 이벤트 발행용인가
- 로그용인가
- alias가 적용되어야 하는가
- `None` 필드는 포함해야 하는가
- datetime은 문자열이어야 하는가, 객체여야 하는가

Pydantic dump 옵션은 생각보다 많다.
`mode`, `by_alias`, `exclude_none`, `exclude_unset`, `exclude_defaults` 같은 옵션 하나가 외부 계약을 바꿀 수 있다.
그래서 이 선택은 도메인 내부가 아니라 adapter serializer에 모으는 편이 안전하다.

```python
def order_response_payload(response: OrderResponse) -> dict:
    return response.model_dump(
        mode="json",
        by_alias=True,
        exclude_none=True,
    )
```

이렇게 하면 API 출력 정책이 한곳에 남는다.

### Pydantic dataclass는 언제 쓸까

Pydantic은 dataclass 통합도 제공한다.
이 기능은 "dataclass 문법을 유지하면서 런타임 검증을 받고 싶다"는 상황에 유용하다.
하지만 도메인 코어의 기본값으로 쓰기 전에는 신중해야 한다.

장점:

- dataclass 스타일과 Pydantic 검증을 같이 쓸 수 있다
- 외부 payload를 내부 타입으로 빠르게 파싱할 수 있다
- 설정이나 integration 모델에 편하다

주의점:

- 순수 dataclass보다 Pydantic runtime semantics가 들어온다
- import 비용과 검증 비용이 생긴다
- 도메인 코어가 Pydantic에 의존한다
- 일반 dataclass라고 생각한 팀원이 동작 차이를 놓칠 수 있다

내 기준에서는 Pydantic dataclass를 도메인 핵심보다는 integration layer나 config layer에서 더 자주 쓴다.
도메인 중심부는 가능하면 표준 라이브러리 기반으로 유지하고,
경계에서 Pydantic의 강력한 파싱 능력을 쓰는 식이다.

---

## 심화 4: schema versioning은 모델 이름보다 payload 계약에 붙여야 한다

이벤트나 외부 API 응답은 시간이 지나면 바뀐다.
필드가 추가되고,
의미가 바뀌고,
nullable 정책이 달라지고,
consumer가 구버전 payload를 계속 읽어야 한다.

이때 내부 도메인 모델 버전을 올리는 것만으로는 부족하다.
버전은 payload 계약에 붙어야 한다.

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class OrderPaidEventV1:
    schema_version: int
    event_id: str
    order_id: int
    paid_amount: int
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class OrderPaidEventV2:
    schema_version: int
    event_id: str
    order_id: int
    paid_amount: int
    currency: str
    occurred_at: datetime
```

버전이 올라가는 이유는 내부 객체가 바뀌어서가 아니다.
consumer가 해석해야 하는 계약이 바뀌었기 때문이다.

실무에서는 아래 정책을 미리 정해야 한다.

- 새 필드 추가는 backward compatible로 볼 것인가
- 필드 제거는 언제 허용할 것인가
- 의미 변경은 새 필드로 낼 것인가, 버전을 올릴 것인가
- consumer가 모르는 schema version을 받으면 실패할 것인가, dead letter로 보낼 것인가
- 이벤트 재처리 시 구버전 payload를 최신 도메인 명령으로 변환할 것인가

이 정책이 없으면 이벤트 모델은 금방 내부 객체 dump가 된다.
그리고 한번 외부로 나간 payload는 오래 산다.
지금 편하자고 내부 모델을 그대로 발행하면, 몇 달 뒤에 consumer 호환성 때문에 내부 리팩터링이 막힌다.

---

## 심화 5: 대량 처리에서는 객체 모델링도 비용이다

좋은 모델링이 항상 성능에 유리한 것은 아니다.
대량 배치, ETL, log processing, feature extraction처럼 수백만 건을 다루는 코드에서는 객체 생성 비용이 눈에 띌 수 있다.

예를 들어 각 row마다 Pydantic 모델을 만들고,
다시 dataclass 명령으로 바꾸고,
다시 도메인 값 객체 여러 개로 감싸면,
정확성은 좋아지지만 처리량은 떨어질 수 있다.

이때는 경계를 다르게 잡아야 한다.

- 외부 입력 초반에 샘플링 또는 chunk 단위 검증을 한다
- hot path에서는 `tuple`, `TypedDict`, columnar structure를 유지한다
- 도메인 규칙이 필요한 지점에서만 값 객체로 올린다
- Pydantic 검증은 신뢰할 수 없는 입력 경계에 집중한다
- 성능이 중요한 mapper는 benchmark를 둔다

예를 들어 광고 로그 집계처럼 단순 변환이 많은 작업에서는 모든 row를 도메인 객체로 만들 필요가 없을 수 있다.
반대로 결제, 정산, 권한 변경처럼 한 건의 오류 비용이 큰 작업에서는 객체 생성 비용보다 규칙 안전성이 더 중요하다.

판단 기준은 "객체가 많냐 적냐"가 아니다.
오류 비용과 처리량 요구의 균형이다.

```text
높은 오류 비용 + 낮은 처리량: 강한 모델링
높은 오류 비용 + 높은 처리량: 경계 검증 + 핵심 규칙 모델링 + 측정
낮은 오류 비용 + 높은 처리량: 단순 구조 + 샘플링 검증
낮은 오류 비용 + 낮은 처리량: 팀이 읽기 쉬운 쪽
```

운영 코드는 아름다운 모델만으로 충분하지 않다.
처리량과 지연 시간도 계약이다.
다만 성능을 이유로 모든 모델링을 포기하기 전에, 어느 경계의 어떤 객체 생성이 실제 병목인지 먼저 측정해야 한다.

---

## 심화 6: 모델 변환은 Anti-Corruption Layer가 될 수 있다

외부 SaaS나 legacy system과 연동할 때는 외부 모델을 내부로 그대로 들여오지 않는 것이 중요하다.
외부 시스템의 필드명과 상태값은 그 시스템의 역사와 사정을 담고 있다.
그것을 내부 도메인 언어로 착각하면 코드 전체가 오염된다.

예를 들어 외부 결제사가 아래 상태를 준다고 해 보자.

```json
{
  "payment_status": "S",
  "approval_yn": "Y",
  "cancel_code": ""
}
```

이 값을 내부 도메인에 그대로 퍼뜨리면 `S`, `Y`, 빈 문자열의 의미를 모든 개발자가 알아야 한다.
대신 adapter에서 내부 값으로 번역한다.

```python
class PaymentStatus(StrEnum):
    APPROVED = "APPROVED"
    DECLINED = "DECLINED"
    CANCELED = "CANCELED"
    UNKNOWN = "UNKNOWN"


def payment_status_from_gateway(payload: GatewayPaymentPayload) -> PaymentStatus:
    if payload.payment_status == "S" and payload.approval_yn == "Y":
        return PaymentStatus.APPROVED
    if payload.cancel_code:
        return PaymentStatus.CANCELED
    return PaymentStatus.UNKNOWN
```

이 mapper는 단순 변환이 아니다.
외부 시스템의 언어를 내부 언어로 바꾸는 Anti-Corruption Layer다.

이 계층이 있으면 외부 시스템 변경이 내부 전체로 퍼지는 것을 줄일 수 있다.
또한 외부 payload의 모순을 어디서 처리할지도 분명해진다.

- 모순된 외부 값은 adapter에서 reject할 것인가
- `UNKNOWN`으로 받아 내부 보정 flow에 태울 것인가
- 원본 payload를 audit log에 저장할 것인가
- 도메인 이벤트에는 표준화된 상태만 발행할 것인가

데이터 모델링은 외부 세계의 혼란을 내부 규칙으로 번역하는 일이다.
이 번역을 생략하면 내부 코드가 외부 시스템의 예외 규칙을 계속 떠안게 된다.

---

## 체크리스트

새 데이터 모델을 만들 때 아래를 확인하자.

- 이 객체는 request, command, domain, row, event, response 중 무엇인가
- 객체 이름에 그 역할이 드러나는가
- 생성 이후 변경되어도 되는가
- 변경되면 어떤 메서드를 통해서만 변경되어야 하는가
- `frozen=True`와 `slots=True`를 쓸 수 있는가
- 필드가 3개 이상이거나 같은 타입이 반복되면 `kw_only=True`를 쓸 수 있는가
- `list`, `dict`, `set`을 frozen 객체 안에 넣고 불변이라고 착각하지 않았는가
- 외부 입력 검증은 Pydantic이나 명시적 parser에서 처리되는가
- 도메인 불변 조건은 도메인 타입 안에서도 유지되는가
- DB nullable과 도메인 optional을 구분했는가
- 이벤트 payload와 응답 DTO가 내부 모델을 그대로 노출하지 않는가
- `asdict()`나 `model_dump()` 결과를 공개 계약으로 바로 쓰지 않는가
- mapper가 필요한 경계와 불필요한 경계를 구분했는가
- 타입 체커, 런타임 검증, DB constraint의 역할을 혼동하지 않았는가
- 테스트가 프레임워크 없이 핵심 도메인 규칙을 검증할 수 있는가

---

## 한줄 정리

Python 데이터 모델링의 핵심은 `dataclass`와 Pydantic 중 하나를 고르는 것이 아니라, **데이터가 경계를 지날 때 어떤 책임을 얻고 어떤 변경을 허용할지 명시하는 것**이다.
