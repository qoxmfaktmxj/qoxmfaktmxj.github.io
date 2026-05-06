---
layout: post
title: "Python Dependency Injection 실전: FastAPI Depends를 넘어서 Composition Root, Protocol, Lifespan으로 테스트 가능한 서비스 설계하기"
date: 2026-05-06 11:40:00 +0900
categories: [python]
tags: [study, python, dependency-injection, composition-root, protocol, fastapi, lifespan, testing, architecture, unit-of-work]
permalink: /python/2026/05/06/study-python-dependency-injection-composition-root-protocol-lifespan-testing.html
---

## 배경: Python에서 DI가 어려운 이유는 문법이 아니라 경계와 생명주기를 한 번에 설계해야 하기 때문이다

Python에서는 흔히 이런 말이 나온다.

- Python은 동적 언어라서 굳이 DI가 필요 없지 않나
- FastAPI `Depends()`가 있으니 그걸로 끝난 것 아닌가
- 그냥 모듈 import해서 쓰면 빠르고 간단하지 않나
- Java/Spring처럼 컨테이너가 없으니 DI를 정교하게 할 이유가 없지 않나

작은 프로젝트에서는 이 말이 어느 정도 맞아 보인다.

파일이 몇 개 안 되고,
외부 리소스도 적고,
테스트도 happy path 위주면,
전역 singleton과 import side effect만으로도 앱이 잘 굴러간다.

문제는 서비스가 커질 때다.

- API 서버와 worker가 같은 도메인 로직을 공유해야 한다
- DB session, Redis client, S3 client, 외부 API client의 수명 주기가 서로 다르다
- 테스트에서 실제 결제 API 대신 fake를 꽂아야 한다
- request scope와 process scope를 구분하지 않으면 connection leak가 난다
- 설정 객체가 모듈 import 시점에 굳어버려 환경별 재현이 깨진다
- 비즈니스 서비스가 FastAPI, Celery, CLI, 배치 프레임워크에 동시에 묶인다
- 관측, 재시도, 트랜잭션, outbox 같은 횡단 관심사가 객체 생성 코드 전체에 흩어진다

이때 많은 팀이 두 극단으로 간다.

하나는 아무 규칙 없이 전역 import를 유지하는 방식이다.
다른 하나는 프레임워크 컨테이너를 들여오고 너무 많은 추상화를 만드는 방식이다.

둘 다 오래 가기 어렵다.

전자는 테스트와 운영이 무너지고,
후자는 읽기 난도와 디버깅 비용이 급격히 올라간다.

실무에서 중요한 것은 화려한 컨테이너가 아니다.

> Python DI의 핵심은 객체를 주입하는 기술이 아니라, **어디에서 조립하고, 어떤 범위에서 재사용하고, 언제 정리할지 명확히 만드는 것**이다.

오늘 글은 아래 질문에 답하는 데 집중한다.

1. Python에서 DI를 왜 프레임워크 기능이 아니라 아키텍처 규칙으로 봐야 하는가
2. `Depends()`와 진짜 DI의 차이는 무엇인가
3. Composition Root, `Protocol`, factory, lifespan을 어떻게 연결해야 하는가
4. request scope, app scope, job scope를 어떻게 나눠야 테스트와 운영이 동시에 편해지는가
5. 수동 DI와 컨테이너 기반 DI는 어떤 트레이드오프가 있는가
6. 흔한 실수와 실전 체크리스트는 무엇인가

핵심 결론만 먼저 말하면 이렇다.

- FastAPI `Depends()`는 유용하지만 **HTTP adapter 계층의 wiring 도구**에 가깝다
- 진짜 핵심은 비즈니스 서비스가 프레임워크 없이도 조립되고 실행되는 구조다
- Python에서는 과한 컨테이너보다 **Composition Root + 명시적 팩토리 + `Protocol` 계약**이 오래 살아남는 경우가 많다
- DI 설계의 성패는 인터페이스 개수보다 **생명주기와 경계 분리**가 좌우한다

---

## 먼저 큰 그림: DI는 "객체를 밖에서 넣는다"보다 "의존성 그래프를 한곳에서 조립한다"에 가깝다

많은 문서가 DI를 이렇게 설명한다.

- A가 B를 직접 만들지 않고 외부에서 받아 쓴다

맞는 말이다.
하지만 실무에서는 이 설명만으로는 부족하다.

왜냐하면 서비스는 객체 한두 개가 아니라 **그래프**이기 때문이다.

예를 들어 주문 확정 API를 생각해 보자.

- `OrderService`
- `OrderRepository`
- `UnitOfWork`
- `PaymentGateway`
- `InventoryGateway`
- `OutboxPublisher`
- `Clock`
- `IdGenerator`
- `Logger`
- `Settings`

여기서 중요한 질문은 단순히 "누가 누구를 받는가"가 아니다.

더 중요한 질문은 아래다.

1. 이 그래프를 **어디서 조립할 것인가**
2. 어떤 의존성은 **프로세스 전체에서 하나만** 써야 하는가
3. 어떤 의존성은 **요청마다 새로** 만들어야 하는가
4. 어떤 의존성은 **트랜잭션 단위로** 열고 닫아야 하는가
5. 테스트에서는 어떤 노드를 fake로 바꿀 것인가
6. HTTP, worker, CLI가 같은 코어를 재사용할 수 있는가

이 질문에 답하지 못하면 DI 문법만 있어도 구조는 금방 꼬인다.

그래서 나는 Python에서 DI를 이렇게 정의하는 편이 더 정확하다고 본다.

> DI는 의존성을 주입하는 테크닉이 아니라, **객체 생성 책임을 도메인 로직 밖으로 밀어내고 생명주기를 명시적으로 다루는 설계 방식**이다.

---

## 핵심 개념 1: IoC, DI, Service Locator를 구분하지 못하면 코드가 편해 보이면서도 점점 숨는다

DI 이야기를 할 때 가장 먼저 헷갈리는 것이 있다.
바로 IoC와 DI와 Service Locator를 한 덩어리로 보는 것이다.

### 1) Inversion of Control

제어의 역전이라는 말은 꽤 넓다.
프레임워크가 lifecycle을 관리해도 IoC고,
이벤트 루프가 콜백을 호출해도 IoC다.

즉 IoC는 큰 개념이다.

### 2) Dependency Injection

DI는 그중에서도 의존성을 외부에서 조립해 넣는 방식이다.
생성자 주입,
함수 인자 주입,
팩토리 인자 전달,
컨텍스트 주입 등이 여기에 들어간다.

### 3) Service Locator

Service Locator는 겉으로는 DI처럼 보이지만 실제로는 다르다.
객체가 필요한 곳에서 전역 레지스트리나 컨테이너를 직접 조회하는 방식이다.

```python
service = container.resolve(OrderService)
```

이 패턴은 처음엔 편하다.
하지만 시간이 갈수록 문제가 생긴다.

- 함수 시그니처만 보고 실제 의존성을 알 수 없다
- 테스트에서 무엇을 바꿔야 하는지 감이 흐려진다
- 모듈 import 시점에 컨테이너 접근이 시작되면 bootstrap 순서가 꼬인다
- 순환 의존성이 늦게 터지거나 런타임에만 드러난다

### 왜 이 구분이 실무에서 중요할까?

Python은 문법적으로 무엇이든 쉽게 숨길 수 있다.

- 모듈 전역에서 객체 생성
- 함수 내부에서 import
- 클래스 내부에서 싱글턴 조회
- decorator 뒤에 암묵 의존성 숨기기

이런 방식은 초반 생산성을 올려 준다.
하지만 프로젝트가 커지면 **의존성이 명시되지 않은 편리함이 결국 디버깅 비용으로 돌아온다**.

내 기준에서 건강한 Python DI의 첫 번째 신호는 이거다.

> 중요한 비즈니스 로직은 코드 서명만 봐도 어떤 자원을 기대하는지 대체로 읽혀야 한다.

---

## 핵심 개념 2: Composition Root는 "어디서 조립할지"에 대한 답이고, 이게 없으면 DI는 금방 종교가 된다

Composition Root는 애플리케이션의 객체 그래프를 실제로 조립하는 진입점이다.

웹 서버라면 앱 startup 경계가 될 수 있고,
CLI라면 `main()` 함수가 될 수 있고,
worker라면 `run()` 함수가 될 수 있다.

중요한 점은 조립이 **한곳에 모여 있어야 한다**는 것이다.

### 왜 Composition Root가 중요한가

DI를 흉내만 낸 코드의 전형적인 패턴은 이런 식이다.

```python
# services/order.py
from app.repositories.order import SqlOrderRepository
from app.gateways.payment import TossPaymentGateway


class OrderService:
    def __init__(self) -> None:
        self.repo = SqlOrderRepository()
        self.payment = TossPaymentGateway()
```

이 구조는 아래 문제를 만든다.

- 서비스 생성 시점에 어떤 리소스가 열리는지 숨는다
- 테스트에서 fake 교체가 어려워진다
- DB 구현체를 바꾸려면 서비스 코드를 수정해야 한다
- HTTP 서버와 worker가 같은 서비스 조립 규칙을 공유하지 못한다

반면 Composition Root가 있으면 이런 식이 된다.

```python
class OrderService:
    def __init__(
        self,
        repo: OrderRepository,
        payment: PaymentGateway,
        outbox: EventPublisher,
    ) -> None:
        self.repo = repo
        self.payment = payment
        self.outbox = outbox
```

```python
def build_order_service(session: Session, settings: Settings) -> OrderService:
    repo = SqlOrderRepository(session)
    payment = TossPaymentGateway(settings.payment_base_url, settings.payment_api_key)
    outbox = SqlOutboxPublisher(session)
    return OrderService(repo=repo, payment=payment, outbox=outbox)
```

이제 생성 책임이 서비스 바깥으로 이동한다.

### Composition Root를 둘 때 지켜야 할 원칙

1. **도메인 내부에서 인프라 구현체를 직접 new 하지 않는다**
2. **프레임워크 adapter가 코어를 조립하되 코어가 프레임워크를 모르게 한다**
3. **객체 그래프의 변형 지점이 한두 군데로 수렴되게 만든다**
4. **환경별 차이(dev/test/prod)는 root에서 흡수한다**

### Python에서 흔히 놓치는 포인트

Python 팀은 파일이 적을 때는 composition root가 없어도 버틴다.
그래서 이 개념을 과하게 느낀다.

하지만 실제로는 프로젝트가 커진 뒤 뒤늦게 root를 만들려 하면 비용이 더 크다.
초기에 작더라도 `main.py`, `factory.py`, `bootstrap.py`, `container.py` 같은 조립 파일 하나를 두는 습관이 장기적으로 훨씬 싸다.

---

## 핵심 개념 3: Python에서는 추상 클래스보다 `Protocol`이 DI 계약을 더 자연스럽게 만드는 경우가 많다

Java/Spring 경험이 강한 팀은 인터페이스를 먼저 떠올린다.
Python에서도 가능하다.
하지만 모든 계약을 추상 클래스와 상속으로 풀면 불필요하게 무거워질 수 있다.

실무에서는 `typing.Protocol`이 꽤 좋은 균형점을 준다.

### 왜 `Protocol`이 잘 맞을까?

- 구조적 타이핑이라 구현체가 상속을 강제받지 않는다
- 기존 라이브러리 wrapper를 붙이기 쉽다
- fake/stub를 만들 때 ceremony가 적다
- 테스트 대역을 가볍게 교체하기 좋다

예를 들어 결제 게이트웨이 계약을 이렇게 둘 수 있다.

```python
from typing import Protocol


class PaymentGateway(Protocol):
    async def authorize(self, order_id: str, amount: int) -> str: ...
    async def cancel(self, transaction_id: str) -> None: ...
```

구현체는 상속 없이도 만족할 수 있다.

```python
class TossPaymentGateway:
    async def authorize(self, order_id: str, amount: int) -> str:
        ...

    async def cancel(self, transaction_id: str) -> None:
        ...
```

테스트 대역도 가볍다.

```python
class FakePaymentGateway:
    def __init__(self) -> None:
        self.authorized: list[tuple[str, int]] = []

    async def authorize(self, order_id: str, amount: int) -> str:
        self.authorized.append((order_id, amount))
        return "tx-fake-001"

    async def cancel(self, transaction_id: str) -> None:
        return None
```

### `Protocol`을 쓸 때 주의할 점

장점이 있다고 모든 의존성에 계약 타입을 만들 필요는 없다.

계약을 만드는 기준은 이 정도가 적당하다.

- 외부 리소스 경계(DB, cache, queue, HTTP client)
- 도메인적으로 교체 가능성이 있는 정책 객체
- 테스트에서 fake가 자주 필요한 컴포넌트

반대로 아래는 과한 경우가 많다.

- 단순 value object
- 한 구현체만 있고 교체 이유도 없는 내부 helper
- getter/setter 수준의 지나치게 얇은 wrapper

즉 인터페이스 수를 늘리는 것이 DI의 성숙도가 아니다.
**교체 가능한 경계를 정확히 잡는 것**이 중요하다.

---

## 핵심 개념 4: 생성자 주입만으로는 부족하다. 리소스 생명주기까지 설계해야 진짜 운영 가능한 DI가 된다

DI 글이 얕아지는 가장 흔한 이유는 "생성자에 넣으면 끝"으로 끝나기 때문이다.

실무 시스템은 객체만 필요한 게 아니라,
연결을 열고,
풀을 재사용하고,
종료 시 정리해야 한다.

예를 들면 아래 자원은 수명이 다 다르다.

- `Settings`: 프로세스 전체에서 사실상 고정
- `AsyncEngine`: 프로세스 단위 재사용이 일반적
- `AsyncSession`: 요청 또는 작업 단위
- `httpx.AsyncClient`: 프로세스 단위 또는 adapter 단위 재사용
- transaction / unit of work: 요청 또는 use case 단위
- 임시 파일 핸들: 매우 짧은 scope

이 수명을 구분하지 않으면 문제가 생긴다.

- 요청마다 DB engine 생성
- 프로세스 종료 시 HTTP client 미정리
- background job에서 request-scoped session 재사용
- 테스트에서 열린 커넥션이 남아 flaky 해짐

### 그래서 DI는 lifecycle 설계까지 포함한다

Python에서는 `contextmanager`, `asynccontextmanager`, ASGI lifespan, generator dependency가 여기서 중요해진다.

예를 들어 app scope 자원은 startup/shutdown에서 관리할 수 있다.

```python
from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = load_settings()
    engine = create_async_engine(settings.db_url, pool_pre_ping=True)
    http_client = httpx.AsyncClient(base_url=settings.billing_base_url, timeout=3.0)

    app.state.container = AppContainer(
        settings=settings,
        engine=engine,
        http_client=http_client,
    )
    try:
        yield
    finally:
        await http_client.aclose()
        await engine.dispose()
```

반면 request scope 자원은 그 위에 얹어 만든다.

```python
async def get_session(container: AppContainer) -> AsyncIterator[AsyncSession]:
    async_session = async_sessionmaker(container.engine, expire_on_commit=False)
    async with async_session() as session:
        yield session
```

여기서 핵심은 생성자 주입보다 더 크다.

> 좋은 DI는 "무엇을 넣을까"만 묻지 않고, **언제 만들고 언제 닫을까**를 같은 설계 문맥에서 다룬다.

---

## 핵심 개념 5: request scope, app scope, job scope를 섞지 않는 것이 FastAPI `Depends()`를 제대로 쓰는 출발점이다

FastAPI를 쓰는 팀이 가장 자주 하는 실수는 `Depends()` 자체가 DI라고 생각하는 것이다.
물론 `Depends()`는 강력하다.
하지만 그것만으로는 scope 설계가 저절로 되지 않는다.

### 구분해야 할 세 가지 범위

#### 1) App scope

프로세스 시작부터 종료까지 살아도 되는 자원이다.

- 설정 객체
- DB engine
- 공용 HTTP client
- metrics/tracer exporter
- feature flag provider client

#### 2) Request scope

HTTP 요청 하나 동안만 살아야 하는 자원이다.

- DB session
- unit of work
- request context
- 권한 검사 결과 일부

#### 3) Job scope

배치 작업, consumer message, CLI command 한 번 실행 동안 살아야 하는 자원이다.

- 메시지 처리용 transaction
- 단건 재처리용 correlation context
- chunk 단위 버퍼

### 왜 request scope만 생각하면 안 되나

실제 서비스는 HTTP만 있지 않다.

- Kafka consumer
- Celery/RQ worker
- APScheduler job
- migration script
- admin CLI

만약 도메인 서비스가 `Depends()`를 직접 알거나,
request 객체에 기대거나,
FastAPI import를 포함하면,
이 코어를 다른 실행 경계에서 재사용하기 어려워진다.

그래서 권장 구조는 보통 이렇다.

- FastAPI layer: adapter, parsing, auth, response mapping, dependency wiring
- Application layer: use case orchestration
- Domain layer: business rules
- Infrastructure layer: DB/queue/http implementations
- Composition Root: 각 실행 경계에서 조립

즉 `Depends()`는 코어의 중심이 아니라 **가장 바깥 adapter의 wiring 문법**으로 보는 편이 건강하다.

---

## 핵심 개념 6: Unit of Work를 주입 대상으로 다루면 트랜잭션과 부작용 경계가 더 명확해진다

Python 백엔드에서 DI를 도입해도 트랜잭션이 흐릿하면 금방 다시 꼬인다.
특히 repository만 주입하고 commit 책임을 여기저기 흩뿌리면 아래 문제가 생긴다.

- 서비스 내부에서 repo가 몰래 commit한다
- 하나의 use case에서 여러 repo를 쓰는데 원자성이 깨진다
- 외부 API 호출과 DB 쓰기 순서가 일관되지 않다
- outbox 기록이 누락되거나 중복된다

이럴 때 `UnitOfWork`를 주입 대상으로 두면 경계가 또렷해진다.

```python
from typing import Protocol


class UnitOfWork(Protocol):
    orders: "OrderRepository"
    outbox: "OutboxRepository"

    async def __aenter__(self) -> "UnitOfWork": ...
    async def __aexit__(self, exc_type, exc, tb) -> None: ...
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...
```

서비스는 session 세부 구현보다 트랜잭션 경계를 다루게 된다.

```python
class ConfirmOrder:
    def __init__(self, payment: PaymentGateway, inventory: InventoryGateway) -> None:
        self.payment = payment
        self.inventory = inventory

    async def execute(self, order_id: str, uow: UnitOfWork) -> None:
        async with uow:
            order = await uow.orders.get(order_id)
            await self.inventory.reserve(order.items)
            tx_id = await self.payment.authorize(order.id, order.total_amount)
            order.confirm(tx_id)
            await uow.outbox.add(order.pull_events())
            await uow.commit()
```

이 패턴의 장점은 세 가지다.

1. 트랜잭션 책임이 use case 레벨에서 읽힌다
2. 테스트에서 fake UoW로 상태 검증이 쉽다
3. HTTP와 worker가 동일한 use case를 재사용하기 쉽다

물론 모든 서비스에 UoW를 강제할 필요는 없다.
하지만 여러 저장소와 외부 부작용이 엮이면 이 패턴이 상당히 실용적이다.

---

## 실무 예시 1: FastAPI `Depends()`에 비즈니스 로직이 잠식될 때 어떤 문제가 생기는가

다음 구조는 초기에 정말 흔하다.

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


class OrderService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def confirm(self, order_id: str) -> dict:
        ...


def get_order_service(session: AsyncSession = Depends(get_session)) -> OrderService:
    return OrderService(session)


@router.post("/orders/{order_id}/confirm")
async def confirm_order(
    order_id: str,
    service: OrderService = Depends(get_order_service),
) -> dict:
    return await service.confirm(order_id)
```

겉으로 보면 괜찮아 보인다.
하지만 조금만 커지면 문제가 나온다.

- `OrderService`가 session에 직접 묶여 repository 경계가 사라진다
- 서비스 생성 함수가 FastAPI에 잠식된다
- worker에서 같은 서비스를 쓰려면 별도 조립 함수를 또 만든다
- 결제 client, 재고 client, outbox, logger가 늘어날수록 dependency 함수가 비대해진다
- override는 쉬워 보여도 코어가 프레임워크 wiring과 너무 가깝다

### 더 건강한 방향

`Depends()`를 없애자는 뜻이 아니다.
`Depends()`가 **코어를 감싸는 adapter**가 되도록 위치를 조정하자는 뜻이다.

```python
class OrderService:
    def __init__(
        self,
        orders: OrderRepository,
        payment: PaymentGateway,
        inventory: InventoryGateway,
        outbox: EventPublisher,
    ) -> None:
        ...
```

```python
def build_order_service(container: AppContainer, session: AsyncSession) -> OrderService:
    return OrderService(
        orders=SqlOrderRepository(session),
        payment=container.payment_gateway,
        inventory=container.inventory_gateway,
        outbox=SqlOutboxPublisher(session),
    )
```

```python
async def get_order_service(
    container: AppContainer = Depends(get_container),
    session: AsyncSession = Depends(get_session),
) -> OrderService:
    return build_order_service(container, session)
```

이렇게 하면 `Depends()`는 여전히 쓰되,
핵심 조립 규칙은 별도 함수로 이동한다.
이 함수는 worker와 테스트에서도 재사용할 수 있다.

---

## 실무 예시 2: Composition Root를 수동 DI로 구성하는 기본 패턴

Python에서는 많은 경우 수동 DI만으로도 충분하다.
오히려 이 방식이 디버깅에 더 강하다.

아래처럼 앱 전역 자원을 담는 container를 둘 수 있다.

```python
from dataclasses import dataclass
import httpx
from sqlalchemy.ext.asyncio import AsyncEngine


@dataclass(frozen=True)
class AppContainer:
    settings: Settings
    engine: AsyncEngine
    payment_gateway: PaymentGateway
    inventory_gateway: InventoryGateway
    clock: Clock
```

부팅 시점에 root를 조립한다.

```python
def build_app_container(settings: Settings) -> AppContainer:
    engine = create_async_engine(settings.db_url, pool_pre_ping=True)
    billing_client = httpx.AsyncClient(
        base_url=settings.billing_base_url,
        timeout=settings.billing_timeout_seconds,
    )
    inventory_client = httpx.AsyncClient(
        base_url=settings.inventory_base_url,
        timeout=settings.inventory_timeout_seconds,
    )

    return AppContainer(
        settings=settings,
        engine=engine,
        payment_gateway=TossPaymentGateway(billing_client),
        inventory_gateway=InventoryHttpGateway(inventory_client),
        clock=SystemClock(),
    )
```

요청 단위 service는 별도 빌더로 만든다.

```python
def build_confirm_order(
    container: AppContainer,
    session: AsyncSession,
) -> ConfirmOrder:
    uow = SqlAlchemyUnitOfWork(session)
    return ConfirmOrder(
        payment=container.payment_gateway,
        inventory=container.inventory_gateway,
    ), uow
```

### 이 패턴이 좋은 이유

- root를 찾기 쉽다
- IDE 탐색이 편하다
- 런타임 reflection이 적다
- 잘못된 wiring이 정적으로 더 잘 드러난다
- 테스트에서 container 일부만 바꾸기 쉽다

### 언제 한계가 오나

- 구현체 조합이 환경별로 매우 많아질 때
- plugin 수가 많아 동적 등록이 필요할 때
- 객체 그래프가 매우 깊고 선택 규칙이 복잡할 때
- 십수 개 이상의 서비스 조립이 반복될 때

이때 컨테이너 라이브러리를 검토할 수 있다.
하지만 그 전까지는 수동 DI가 생각보다 오래 간다.

---

## 실무 예시 3: FastAPI Lifespan + Adapter Wiring으로 프레임워크 의존성을 바깥에 고정하기

실전에서 꽤 균형이 좋은 구조는 아래다.

### 1) app startup에서 전역 자원을 만든다

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = load_settings()
    container = await build_app_container(settings)
    app.state.container = container
    try:
        yield
    finally:
        await shutdown_container(container)
```

### 2) adapter는 `app.state`에서 container를 꺼낸다

```python
def get_container(request: Request) -> AppContainer:
    return request.app.state.container
```

### 3) request scope 자원을 만든다

```python
async def get_session(
    container: AppContainer = Depends(get_container),
) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(container.engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
```

### 4) service wiring은 별도 함수로 둔다

```python
def build_create_user_service(
    container: AppContainer,
    session: AsyncSession,
) -> CreateUserService:
    return CreateUserService(
        users=SqlUserRepository(session),
        email_verifier=container.email_verifier,
        password_hasher=container.password_hasher,
        clock=container.clock,
    )
```

### 5) 라우터는 조립 결과를 받아 use case만 호출한다

```python
@router.post("/users")
async def create_user(
    payload: CreateUserRequest,
    container: AppContainer = Depends(get_container),
    session: AsyncSession = Depends(get_session),
) -> UserResponse:
    service = build_create_user_service(container, session)
    result = await service.execute(payload)
    return UserResponse.from_result(result)
```

이 구조는 장황해 보일 수 있다.
하지만 장기적으로는 장점이 크다.

- 라우터는 HTTP concern에 집중한다
- service는 FastAPI를 모른다
- worker/CLI에서 동일한 `build_create_user_service()`를 재사용할 수 있다
- override 포인트가 명확하다

즉 boilerplate가 조금 늘더라도 **의존성 방향이 고정되는 가치**가 크다.

---

## 실무 예시 4: HTTP 서버, worker, CLI가 같은 코어를 공유하려면 root를 실행 경계별로 나눠야 한다

많은 팀이 웹 API에서는 DI를 해도 worker에서 다시 무너진다.
이유는 간단하다.
web request 기준으로만 조립했기 때문이다.

예를 들어 주문 확정 use case를 HTTP와 Kafka consumer 둘 다 쓴다고 하자.

### HTTP adapter

```python
@router.post("/orders/{order_id}/confirm")
async def confirm_order(...):
    service, uow = build_confirm_order(container, session)
    await service.execute(order_id, uow)
```

### Consumer adapter

```python
async def handle_message(message: ConfirmOrderMessage, container: AppContainer) -> None:
    session_factory = async_sessionmaker(container.engine, expire_on_commit=False)
    async with session_factory() as session:
        service, uow = build_confirm_order(container, session)
        await service.execute(message.order_id, uow)
```

### CLI adapter

```python
async def reprocess(order_id: str) -> None:
    settings = load_settings()
    container = await build_app_container(settings)
    try:
        session_factory = async_sessionmaker(container.engine, expire_on_commit=False)
        async with session_factory() as session:
            service, uow = build_confirm_order(container, session)
            await service.execute(order_id, uow)
    finally:
        await shutdown_container(container)
```

이 세 경계에서 공통으로 재사용되는 것은 무엇일까?

- 도메인 서비스
- infrastructure 구현체 일부
- service builder
- container

달라지는 것은 무엇일까?

- 입력 파싱
- 인증/인가
- 응답 직렬화
- ack/retry 정책
- process lifecycle

이 구분이 명확하면 프레임워크가 달라도 코어가 오래 산다.

---

## 실무 예시 5: 테스트 가능한 DI는 "mock을 많이 쓰는 구조"가 아니라 "fake를 꽂기 쉬운 구조"다

DI를 도입했는데 테스트가 오히려 복잡해지는 팀이 있다.
대개 이유는 두 가지다.

- 의존성을 너무 세밀하게 쪼개 mock 수가 폭증함
- root는 없고 군데군데 patch만 하느라 경로가 흐려짐

나는 Python 테스트에서 아래 순서를 더 추천한다.

1. 가능한 한 **수동 fake**를 먼저 고려한다
2. 그 다음 얇은 stub/mock을 쓴다
3. monkey patch는 마지막 수단으로 둔다

### 왜 fake가 중요한가

Python에서는 동적 patch가 쉽다.
그래서 유혹이 크다.
하지만 patch 기반 테스트는 import 경로와 호출 타이밍에 민감하다.
DI 구조가 있으면 patch보다 fake가 더 안정적이다.

```python
class FakeOrderRepository:
    def __init__(self) -> None:
        self.storage: dict[str, Order] = {}

    async def get(self, order_id: str) -> Order:
        return self.storage[order_id]

    async def save(self, order: Order) -> None:
        self.storage[order.id] = order
```

```python
class FakeUnitOfWork:
    def __init__(self, order: Order) -> None:
        self.orders = FakeOrderRepository()
        self.orders.storage[order.id] = order
        self.outbox = FakeOutboxRepository()
        self.committed = False

    async def __aenter__(self) -> "FakeUnitOfWork":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        return None
```

이렇게 두면 테스트가 비즈니스 규칙에 더 집중한다.

```python
async def test_confirm_order_marks_order_confirmed() -> None:
    order = Order.pending("order-1", total_amount=15000)
    uow = FakeUnitOfWork(order)
    payment = FakePaymentGateway()
    inventory = FakeInventoryGateway()
    service = ConfirmOrder(payment=payment, inventory=inventory)

    await service.execute(order.id, uow)

    assert order.status is OrderStatus.CONFIRMED
    assert uow.committed is True
    assert payment.authorized == [("order-1", 15000)]
```

### FastAPI override는 어디까지 써야 할까

`dependency_overrides`는 adapter 테스트에는 좋다.
하지만 application service 테스트까지 전부 override 기반으로만 가면 느려지고 복잡해진다.

실무에서는 보통 층을 나누는 편이 좋다.

- service/unit test: framework 없이 직접 객체 생성
- adapter/integration test: `dependency_overrides`, test app, test DB 사용
- E2E test: 실제 wiring 최대한 유지

즉 DI의 목표는 mock 기술을 화려하게 쓰는 것이 아니라,
**프레임워크 없이 코어를 테스트 가능하게 만드는 것**이다.

---

## 핵심 개념 7: 설정도 의존성이다. settings singleton을 너무 일찍 굳히면 테스트와 배포가 같이 아프다

설정은 자주 과소평가된다.
하지만 실제로는 DI에서 매우 중요한 의존성이다.

잘못된 패턴은 이런 식이다.

```python
settings = Settings()
```

모듈 import 시점에 이 코드가 실행되면 문제가 생긴다.

- 환경 변수를 테스트에서 바꿔도 이미 늦다
- 프로세스 부팅 순서에 따라 설정 오류가 애매하게 터진다
- CLI와 web app이 다른 환경 규칙을 쓰기 어려워진다
- secret loading 실패가 import error처럼 보일 수 있다

더 건강한 방식은 설정 로딩도 root에서 다루는 것이다.

```python
@lru_cache
def load_settings() -> Settings:
    return Settings()
```

또는 아예 root 함수에서 한 번 만든 뒤 명시적으로 전달한다.

```python
def main() -> None:
    settings = load_settings()
    container = build_app_container(settings)
```

### 설정을 DI 관점에서 볼 때 체크할 것

- 설정은 app scope인가
- 런타임 reload가 필요한가
- 테스트에서 대체가 쉬운가
- validation 오류가 bootstrap 단계에서 선명하게 드러나는가
- 비밀값 접근이 코어 내부에 새지 않는가

설정이 흐리면 나머지 DI도 흐려진다.

---

## 핵심 개념 8: 컨테이너 라이브러리는 늦게 도입해도 되지만, 도입 기준은 분명해야 한다

Python 생태계에는 여러 DI 라이브러리가 있다.

- `dependency-injector`
- `injector`
- `wired`
- `punq`
- 직접 만든 간단한 registry/container

이런 도구가 나쁜 것은 아니다.
하지만 "DI를 하려면 컨테이너가 필요하다"고 생각하면 오히려 설계를 건너뛰게 된다.

### 수동 DI로 충분한 경우

- 서비스 수가 아직 적다
- 구현체 선택 규칙이 단순하다
- runtime reflection 없이도 wiring이 읽힌다
- 팀이 명시적 코드를 선호한다
- 디버깅 단순성이 중요하다

### 컨테이너가 빛나는 경우

- 환경/기능 플래그에 따라 구현체 조합이 자주 바뀐다
- plugin/멀티 테넌트 등 동적 등록 요구가 있다
- provider scope 관리가 매우 많다
- 비동기 리소스의 조립이 중복된다
- 팀이 컨테이너 규칙을 일관되게 이해하고 있다

### 도입할 때 경계해야 할 것

1. **resolve를 아무 데서나 부르게 만들지 말 것**
2. **컨테이너 타입이 코어 시그니처에 침투하지 않게 할 것**
3. **magic decorator와 runtime string key를 남용하지 말 것**
4. **오류 메시지가 wiring 단계에서 충분히 읽히는지 확인할 것**

즉 컨테이너는 DI의 본질이 아니다.
컨테이너는 **이미 정리된 DI 규칙을 자동화하는 도구**에 가깝다.

설계가 흐린 상태에서 컨테이너만 들이면 복잡함이 추상화 뒤로 숨을 뿐이다.

---

## 트레이드오프: Python DI는 명시성과 보일러플레이트, 유연성과 추적 가능성 사이 균형 게임이다

DI 구조를 잡으면 항상 대가가 있다.
이걸 솔직하게 봐야 한다.

### 장점

- 테스트 대역 교체가 쉬워진다
- HTTP/worker/CLI 간 코어 재사용이 좋아진다
- 전역 singleton과 import side effect를 줄일 수 있다
- 리소스 생명주기를 계획적으로 관리할 수 있다
- 구현체 교체 비용이 줄어든다
- 트랜잭션 경계를 use case 수준에서 읽기 쉬워진다

### 비용

- builder/factory 코드가 늘어난다
- 작은 서비스에서는 과해 보일 수 있다
- 팀이 경계를 이해하지 못하면 ceremony만 남는다
- 추상화가 과해지면 오히려 탐색이 어려워진다
- 동적 언어 특성상 잘못된 wiring이 런타임까지 미뤄질 수 있다

### 실무 추천 균형점

내 경험상 Python에서는 아래 정도가 균형이 좋다.

- 코어 서비스는 프레임워크 비의존적으로 만든다
- 외부 리소스 경계에는 `Protocol` 또는 명시 계약을 둔다
- 조립은 `factory.py`나 `bootstrap.py`에 모은다
- container 라이브러리는 필요가 명확할 때만 쓴다
- 단순 helper까지 모두 인터페이스로 감싸지 않는다

즉 **모든 것을 추상화하지 말고, 바뀌거나 새는 경계를 추상화하라**가 핵심이다.

---

## 흔한 실수 1: `Depends()`를 서비스 레이어 아래로 끌고 내려가는 것

이건 정말 흔하다.

```python
class UserService:
    def __init__(self, session: AsyncSession = Depends(get_session)) -> None:
        ...
```

이 패턴은 편해 보인다.
하지만 service가 이미 FastAPI에 묶였다.
이제 이 코드는 worker나 CLI에서 자연스럽게 재사용되기 어렵다.

`Depends()`는 라우터나 adapter에서 끝내는 편이 좋다.

---

## 흔한 실수 2: Repository는 분리했는데 commit은 아무 데서나 하는 것

repository를 주입했다고 DI가 끝난 게 아니다.
트랜잭션 경계가 흐리면 결국 데이터 정합성이 무너진다.

- repo 내부 commit
- 서비스 내부 임의 commit
- 외부 API 성공 후 DB 실패
- outbox 저장 누락

이 문제는 repository 수보다 **unit of work 경계**를 어떻게 잡았는지가 더 중요하다.

---

## 흔한 실수 3: 모든 것에 인터페이스를 만드는 것

인터페이스가 많다고 유연한 것은 아니다.
Python에서는 오히려 타입 파일만 늘고 읽기성이 나빠질 수 있다.

질문은 이거다.

- 정말 교체 가능한가
- 테스트에서 대체가 필요한가
- 외부 리소스 경계인가
- 팀이 이 계약 이름을 공통 언어로 쓸 수 있는가

이 질문에 `아니오`가 많으면 굳이 계약 타입을 만들 필요가 없다.

---

## 흔한 실수 4: 생성자에서 무거운 I/O를 열어 버리는 것

```python
class PaymentGateway:
    def __init__(self) -> None:
        self.client = httpx.AsyncClient(...)
```

더 큰 문제는 생성자에서 바로 네트워크 handshake나 schema preload 같은 일을 해버리는 경우다.
이러면 객체 생성과 bootstrap 부작용이 섞인다.

생성자는 가볍게 유지하고,
무거운 초기화는 root나 별도 lifecycle 훅에서 다루는 편이 낫다.

---

## 흔한 실수 5: 테스트에서 patch로만 버티는 것

patch는 강력하지만,
DI 대체가 가능하면 fake가 더 읽기 쉽고 덜 깨진다.

- patch 경로가 import 스타일에 따라 달라진다
- side effect가 이미 실행된 뒤면 patch 타이밍이 늦다
- 호출 횟수 검증에만 매달리면 비즈니스 의미가 흐려진다

테스트에서 확인하고 싶은 것은 "이 함수가 몇 번 호출됐나"보다,
"이 use case가 어떤 상태 전이를 만들었나"인 경우가 많다.

---

## 흔한 실수 6: 관측 가능성 의존성을 숨겨서 로깅/트레이싱이 뒤늦게 흩어지는 것

서비스가 커지면 logger, tracer, metrics emitter도 의존성이다.
이를 전역 로거 하나로만 두면 컨텍스트 주입이 불명확해진다.

물론 모든 함수에 logger를 넣을 필요는 없다.
하지만 최소한 아래는 설계 의식이 필요하다.

- request/job scope 컨텍스트는 어디서 생성되는가
- structured logging 필드는 누가 채우는가
- 외부 호출 adapter는 어떤 span/tag를 다는가
- retry/circuit breaker는 어느 경계에 붙는가

DI가 잘 되면 관측도 같이 정돈된다.

---

## 체크리스트: Python 서비스에서 DI 구조를 점검할 때 보는 항목

### 구조

- 비즈니스 서비스가 FastAPI, Celery, CLI 프레임워크 import 없이도 생성 가능한가
- 객체 그래프를 조립하는 파일이 명확히 존재하는가
- 외부 리소스 경계가 코드 구조상 드러나는가
- 전역 singleton과 모듈 import side effect가 root 밖으로 새지 않는가

### 생명주기

- app scope 자원과 request/job scope 자원을 구분했는가
- DB engine, HTTP client, cache client의 생성/종료 위치가 명확한가
- session/transaction 범위가 use case 또는 adapter에서 일관되게 관리되는가

### 테스트

- service를 프레임워크 없이 직접 테스트할 수 있는가
- fake/stub를 꽂기 쉬운 계약이 있는가
- patch에 과도하게 의존하지 않는가
- 설정값과 시간/ID 생성 같은 비결정 요소를 주입 가능하게 했는가

### 운영

- bootstrap 단계에서 wiring 오류가 선명하게 드러나는가
- worker와 web app이 코어를 재사용할 때 같은 규칙을 따르는가
- shutdown 시 외부 자원이 정상 정리되는가
- 장애 시 어떤 의존성이 어느 scope에서 생성됐는지 추적 가능한가

### 설계 균형

- 교체 가능성이 낮은 내부 helper까지 인터페이스로 감싸지 않았는가
- 반대로 외부 API/DB/queue 같은 변경 가능 경계를 너무 구체 구현에 묶어 두지 않았는가
- 보일러플레이트 증가가 실제 테스트성·재사용성·운영 안정성으로 회수되는가

---

## 한 단계 더: 언제 수동 DI에서 컨테이너로 넘어갈지 판단하는 기준

마지막으로 많이 묻는 질문에 답해 보자.

> 지금 구조에서 컨테이너 라이브러리를 도입해야 할까?

내가 보는 신호는 대략 이렇다.

### 아직 수동 DI로 가도 되는 신호

- builder 함수 위치를 모두 설명할 수 있다
- 주요 서비스 10개 안팎의 wiring이 크게 중복되지 않는다
- 테스트에서 fake 교체가 불편하지 않다
- 팀원이 새 기능 추가 시 어디서 조립할지 자연스럽게 안다

### 컨테이너 도입을 검토할 신호

- provider scope 관리 코드가 반복된다
- 구현체 선택 규칙이 환경/기능별로 자주 갈린다
- 동적 plugin 로딩이 많다
- 조립 코드가 여러 파일에 흩어져 중복된다
- root를 읽는 데 시간이 많이 걸리고 실수가 잦다

그래도 추천 순서는 같다.

1. 먼저 root와 lifecycle을 명확히 한다
2. 다음에 수동 builder를 정리한다
3. 그래도 복잡하면 컨테이너를 도입한다

순서를 거꾸로 하면,
컨테이너가 구조 문제를 해결하기보다 가려 버리는 경우가 많다.

---

## 한 줄 정리

> Python DI의 본질은 `Depends()`나 컨테이너 자체가 아니라, **Composition Root에서 객체 그래프와 생명주기를 명시적으로 조립해 HTTP·worker·CLI 어디서도 같은 코어를 테스트 가능하게 만드는 것**이다.
