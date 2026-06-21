---
layout: post
title: "Python SQLAlchemy 운영 설계: Session, Unit of Work, Transaction Boundary, Connection Pool을 한 번에 잡는 법"
date: 2026-06-21 11:50:00 +0900
categories: [python]
tags: [study, python, sqlalchemy, session, unit-of-work, transaction, connection-pool, fastapi, database, backend, operations]
permalink: /python/2026/06/21/study-python-sqlalchemy-session-unit-of-work-transaction-pool.html
---

## 배경: SQLAlchemy 장애는 쿼리 문법보다 Session 경계에서 더 자주 터진다

Python 백엔드에서 SQLAlchemy를 도입하는 순간은 대체로 단순하다.

- `create_engine()`으로 DB 연결을 만든다
- ORM model을 선언한다
- `Session`으로 조회하고 저장한다
- FastAPI dependency에서 session을 열고 닫는다
- 테스트에서는 SQLite나 test database를 붙인다

처음에는 이 정도면 충분해 보인다. CRUD API도 잘 동작하고, `select()` 문법도 익숙해지고, relationship도 적당히 연결된다. 하지만 운영으로 가면 문제의 중심이 달라진다. 대부분의 어려움은 "SQLAlchemy로 어떤 쿼리를 어떻게 쓰는가"보다 **Session이 어디서 열리고, 언제 commit되며, 실패했을 때 어떤 상태로 남는가**에서 나온다.

실제로 자주 보는 장애는 이런 식이다.

- 요청 하나가 끝났는데 DB connection이 pool로 돌아가지 않아 connection exhaustion이 난다
- 서비스 함수 안에서 `commit()`을 여러 번 호출해 중간 상태가 외부에 노출된다
- repository 함수가 session을 몰래 만들고 닫아서 같은 use case 안의 변경이 한 트랜잭션으로 묶이지 않는다
- `expire_on_commit=True` 기본값 때문에 commit 후 객체 접근 시 예상치 못한 lazy load가 발생한다
- `Session`을 전역 singleton처럼 공유하다가 요청 간 identity map이 섞인다
- 예외가 발생했는데 rollback하지 않아 이후 쿼리에서 `PendingRollbackError`가 터진다
- read-only API라고 생각했는데 autoflush 때문에 조회 직전에 쓰기 SQL이 나간다
- 테스트에서는 통과하지만 실제 PostgreSQL에서는 transaction isolation과 lock wait 때문에 교착이나 지연이 발생한다
- background task가 HTTP request session을 계속 들고 있다가 이미 닫힌 session을 사용한다

이 문제들은 SQLAlchemy를 잘 몰라서만 생기지 않는다. 더 근본적으로는 애플리케이션의 작업 단위와 DB 트랜잭션 경계를 명확히 설계하지 않았기 때문에 생긴다.

오늘 글은 SQLAlchemy 입문 문법이 아니라, 중급 이상 Python 개발자가 운영 코드에서 반드시 정해야 하는 기준을 정리한다.

1. `Engine`, `Connection`, `Session`은 각각 어떤 책임을 갖는가
2. Session은 왜 "DB 연결"이 아니라 "작업 단위와 identity map"으로 이해해야 하는가
3. Unit of Work 패턴은 repository보다 어떤 문제를 더 직접적으로 해결하는가
4. FastAPI request, worker job, CLI batch에서 transaction boundary를 어떻게 잡아야 하는가
5. connection pool 설정은 성능 튜닝이 아니라 장애 격리와 backpressure 정책으로 봐야 하는 이유는 무엇인가
6. nested transaction, savepoint, retry, idempotency는 어디까지 애플리케이션 책임인가
7. 흔한 실수와 배포 전 체크리스트는 무엇인가

핵심 결론부터 말하면 이렇다.

**SQLAlchemy 운영 설계의 핵심은 Session을 편한 전역 DB 핸들로 쓰는 것이 아니라, 하나의 비즈니스 작업을 하나의 명시적 트랜잭션 경계로 묶고 실패 시 확실히 되돌리는 것이다.**

Session은 강력하다. 하지만 강력한 만큼 애매하게 쓰면 장애를 숨긴다. 좋은 설계는 "어디서든 session을 가져다 쓰는 편의성"보다 "이 use case가 어떤 DB 변경을 하나의 원자적 작업으로 보장하는가"를 먼저 드러낸다.

---

## 먼저 큰 그림: Engine, Connection, Session은 같은 것이 아니다

SQLAlchemy를 처음 쓰면 `Engine`, `Connection`, `Session`이 모두 "DB에 연결하는 객체"처럼 보인다. 하지만 운영 설계에서는 이 셋을 분리해서 봐야 한다.

### Engine: 프로세스 단위의 DB 접근 설비

`Engine`은 데이터베이스 URL, dialect, connection pool, logging, isolation 기본값 등을 담는 프로세스 단위 객체다.

```python
from sqlalchemy import create_engine

engine = create_engine(
    settings.database_url,
    pool_size=10,
    max_overflow=20,
    pool_timeout=3,
    pool_recycle=1800,
    pool_pre_ping=True,
)
```

`Engine`은 보통 애플리케이션 시작 시 한 번 만들고 재사용한다. 요청마다 만들면 안 된다. Engine을 요청마다 만들면 connection pool도 요청마다 새로 생기고, DB 서버 입장에서는 연결 생성과 해제가 폭발한다.

Engine은 다음 질문의 답이다.

- 이 프로세스는 어느 DB에 접근하는가
- connection pool은 몇 개까지 허용하는가
- 연결이 죽었는지 어떻게 확인할 것인가
- 기본 isolation level은 무엇인가
- SQL logging과 event hook을 어떻게 붙일 것인가

즉 Engine은 "작업 단위"가 아니라 "DB 접근 인프라"다.

### Connection: 실제 DB 연결과 transaction의 낮은 레벨 경계

`Connection`은 pool에서 빌린 실제 연결에 가깝다. Core SQL을 직접 실행하거나 세밀한 transaction control이 필요할 때 다룬다.

```python
with engine.begin() as conn:
    conn.execute(text("insert into audit_log(message) values (:msg)"), {"msg": "ok"})
```

ORM 중심 애플리케이션에서는 `Connection`을 직접 만지는 일이 많지 않을 수 있다. 하지만 중요한 점은 `Session`도 내부적으로 connection을 빌려 쓴다는 것이다. Session을 닫지 않으면 connection이 pool로 돌아가지 않는다.

### Session: identity map과 unit of work를 가진 작업 공간

`Session`은 단순 DB 연결이 아니다. Session은 ORM 객체를 추적하고, 변경 내용을 모았다가 flush하고, transaction과 연결되는 작업 공간이다.

```python
from sqlalchemy.orm import Session

with Session(engine) as session:
    order = session.get(Order, order_id)
    order.status = OrderStatus.PAID
    session.commit()
```

여기서 Session은 여러 책임을 갖는다.

- 같은 row를 같은 Python 객체로 유지하는 identity map
- 변경된 객체를 추적하는 unit of work
- flush 시점에 SQL을 생성하는 변경 버퍼
- transaction begin, commit, rollback의 진입점
- relationship lazy loading의 실행 컨텍스트

그래서 Session을 "커넥션 하나"로 이해하면 위험하다. Session은 객체 상태와 DB transaction을 동시에 품고 있다. 오래 살리거나 공유하면 객체 캐시, transaction 상태, connection 점유가 함께 길어진다.

---

## 핵심 개념 1: Session의 생명주기는 비즈니스 작업 단위와 맞춰야 한다

Session을 얼마나 오래 유지할 것인가? 이 질문에 대한 실무 답은 대체로 아래다.

> Session은 하나의 독립적인 작업 단위마다 만들고, 그 작업이 끝나면 commit 또는 rollback 후 닫는다.

웹 API라면 보통 요청 하나가 작업 단위다. worker라면 job 하나 또는 message 하나가 작업 단위다. CLI batch라면 파일 전체가 아니라 record chunk 하나가 작업 단위일 수 있다.

### 요청 단위 Session

FastAPI에서는 보통 dependency로 session을 제공한다.

```python
from collections.abc import Generator
from sqlalchemy.orm import Session, sessionmaker

SessionLocal = sessionmaker(bind=engine, autoflush=True, expire_on_commit=False)

def get_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
```

이 패턴은 session close를 보장한다는 점에서 출발점으로 좋다. 하지만 여기서 끝내면 transaction boundary가 애매해질 수 있다. route handler나 service 함수 어딘가에서 각자 `commit()`을 호출하기 시작하면 요청 하나 안에서도 여러 transaction이 생긴다.

예를 들어 아래 코드는 보기에는 괜찮아 보인다.

```python
def create_order(session: Session, command: CreateOrderCommand) -> Order:
    order = Order.create(command)
    session.add(order)
    session.commit()
    return order


def publish_order_created(session: Session, order: Order) -> None:
    event = OutboxEvent.from_order(order)
    session.add(event)
    session.commit()
```

하지만 주문 생성과 outbox 기록이 서로 다른 commit으로 갈라졌다. 첫 번째 commit은 성공했는데 두 번째 commit 전에 프로세스가 죽으면 주문은 생성됐지만 이벤트 의도는 사라진다. 이건 단순 코드 스타일 문제가 아니라 원자성 문제다.

더 나은 방향은 use case 경계에서 commit을 한 번만 호출하는 것이다.

```python
def create_order_use_case(session: Session, command: CreateOrderCommand) -> Order:
    order = Order.create(command)
    session.add(order)

    event = OutboxEvent.from_order(order)
    session.add(event)

    session.commit()
    return order
```

규모가 커지면 이 commit 위치를 더 명확히 하기 위해 Unit of Work를 둔다.

### 작업 단위를 나누는 기준

작업 단위를 정할 때는 "함수 하나"가 아니라 "원자적으로 성공하거나 실패해야 하는 비즈니스 변화"를 기준으로 잡아야 한다.

좋은 경계:

- 주문 생성 + 재고 예약 + outbox 기록
- 결제 승인 반영 + 결제 이벤트 저장
- 사용자 상태 변경 + 감사 로그 기록
- CSV 1,000건 중 한 chunk의 upsert
- Kafka message 1개 처리 + 처리 결과 저장 + offset commit 준비

나쁜 경계:

- repository method마다 commit
- model method 안에서 commit
- helper 함수가 몰래 session을 만들고 commit
- request 전체를 무조건 하나의 거대한 transaction으로 묶고 외부 API 호출까지 포함
- batch 파일 전체 100만 건을 하나의 transaction으로 처리

작업 단위는 너무 작아도 문제고 너무 커도 문제다. 너무 작으면 원자성이 깨지고, 너무 크면 lock 보유 시간이 길어지고 rollback 비용이 커진다.

---

## 핵심 개념 2: Unit of Work는 repository 묶음이 아니라 commit 책임의 소유자다

Repository 패턴은 데이터 접근을 숨기는 데 도움이 된다. 하지만 repository만으로는 transaction boundary가 정리되지 않는다. 오히려 repository가 session과 commit을 직접 다루기 시작하면 구조가 흐려질 수 있다.

### Repository가 commit하면 생기는 문제

아래 코드는 흔하다.

```python
class OrderRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def save(self, order: Order) -> None:
        self.session.add(order)
        self.session.commit()
```

처음에는 편하다. `repo.save(order)`만 호출하면 DB에 저장된다. 하지만 여러 repository를 하나의 use case에서 함께 쓰면 문제가 생긴다.

```python
order_repo.save(order)        # commit 1
inventory_repo.reserve(item)  # commit 2
outbox_repo.add(event)        # commit 3
```

세 작업 중 두 번째에서 실패하면 첫 번째 commit은 이미 되돌릴 수 없다. 비즈니스 작업은 하나였는데 transaction은 셋이 됐다.

Repository는 보통 아래까지만 책임지는 편이 낫다.

- aggregate를 조회한다
- aggregate를 session에 추가한다
- 조건에 맞는 row를 찾는다
- 저장소별 query를 캡슐화한다

반대로 commit, rollback, close는 더 바깥 경계가 맡는다.

### Unit of Work 예시

Unit of Work는 여러 repository와 하나의 session, 그리고 commit/rollback 정책을 묶는다.

```python
from types import TracebackType
from sqlalchemy.orm import Session, sessionmaker


class UnitOfWork:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def __enter__(self) -> "UnitOfWork":
        self.session = self._session_factory()
        self.orders = OrderRepository(self.session)
        self.inventory = InventoryRepository(self.session)
        self.outbox = OutboxRepository(self.session)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        try:
            if exc_type is not None:
                self.session.rollback()
            else:
                self.session.commit()
        finally:
            self.session.close()
```

사용 코드는 이렇게 된다.

```python
def place_order(command: PlaceOrderCommand, uow_factory: Callable[[], UnitOfWork]) -> str:
    with uow_factory() as uow:
        order = Order.place(command)
        uow.orders.add(order)
        uow.inventory.reserve(command.product_id, command.quantity)
        uow.outbox.add(OutboxEvent.order_placed(order))
        return order.id
```

이제 비즈니스 흐름은 commit을 직접 모른다. use case가 정상 종료되면 commit, 예외가 나면 rollback된다. repository는 session을 공유하므로 같은 transaction 안에서 움직인다.

물론 모든 프로젝트가 Unit of Work 클래스를 꼭 가져야 하는 것은 아니다. 작은 서비스에서는 route handler 또는 service layer에서 `with session.begin():`을 명확히 쓰는 것만으로 충분할 수 있다. 중요한 것은 패턴 이름이 아니라 commit 책임이 흩어지지 않는 것이다.

---

## 핵심 개념 3: flush와 commit을 구분해야 중간 상태를 제어할 수 있다

SQLAlchemy에서 `flush()`와 `commit()`은 다르다.

- `flush()`: pending changes를 SQL로 DB에 보낸다. transaction은 끝나지 않는다.
- `commit()`: transaction을 확정한다. 내부적으로 필요한 flush가 먼저 일어난다.

이 차이를 모르면 "id를 얻기 위해 commit한다" 같은 코드가 나온다.

```python
order = Order(user_id=user_id)
session.add(order)
session.commit()

event = OutboxEvent(order_id=order.id)
session.add(event)
session.commit()
```

이 코드는 order id를 얻으려고 첫 commit을 호출했다. 하지만 id 생성 때문에 transaction을 둘로 쪼갤 필요는 없다. flush로 충분하다.

```python
order = Order(user_id=user_id)
session.add(order)
session.flush()

event = OutboxEvent(order_id=order.id)
session.add(event)
session.commit()
```

`flush()` 후에는 DB가 insert를 봤고, auto-increment id도 채워질 수 있다. 하지만 아직 commit은 아니다. 이후 예외가 나면 rollback으로 order와 event를 함께 되돌릴 수 있다.

### autoflush는 편하지만 놀랄 수 있다

Session은 기본적으로 query 실행 전에 autoflush를 수행할 수 있다. 즉 조회만 한다고 생각한 코드가 먼저 pending insert/update를 DB에 보낼 수 있다.

```python
order = Order(user_id=user_id)
session.add(order)

# 이 select 전에 order insert가 flush될 수 있다.
user = session.scalar(select(User).where(User.id == user_id))
```

대부분은 올바른 동작이다. query가 현재 session의 변경을 반영해야 일관성이 맞기 때문이다. 하지만 validation 중간 상태나 아직 필수 값이 채워지지 않은 객체가 있으면 예상치 못한 integrity error가 날 수 있다.

필요한 경우 좁은 범위에서 `no_autoflush`를 쓴다.

```python
with session.no_autoflush:
    user = session.scalar(select(User).where(User.id == user_id))
    order.assign_user(user)
```

다만 `no_autoflush`를 남용하면 session에 쌓인 변경과 query 결과의 관계가 더 어려워진다. 기본은 객체를 유효한 상태로 만든 뒤 session에 추가하는 것이다.

---

## 핵심 개념 4: identity map은 성능 캐시가 아니라 객체 정합성 장치다

Session은 같은 primary key의 row를 같은 Python 객체로 유지한다.

```python
order1 = session.get(Order, "ord-1")
order2 = session.get(Order, "ord-1")

assert order1 is order2
```

이 identity map 덕분에 같은 transaction 안에서 객체 상태가 일관된다. 하지만 동시에 주의점도 있다.

### 오래 사는 Session은 오래된 객체를 품는다

Session을 너무 오래 유지하면 이미 DB에서 바뀐 값을 계속 들고 있을 수 있다.

```python
# 오래 살아 있는 session
order = session.get(Order, "ord-1")

# 다른 transaction에서 order.status 변경

same_order = session.get(Order, "ord-1")
print(same_order.status)  # 예전 값일 수 있다
```

Session은 2차 캐시가 아니다. 요청 사이에 공유하는 캐시로 쓰면 안 된다. 요청이 끝나면 닫고, 다음 요청은 새 Session을 쓰는 것이 기본이다.

### expire_on_commit 선택

SQLAlchemy sessionmaker의 기본값은 `expire_on_commit=True`다. commit 후 ORM 객체의 속성이 만료되고, 이후 접근하면 DB에서 다시 로드할 수 있다.

이 기본값은 DB 최신성을 중시하는 관점에서는 합리적이다. 하지만 웹 API에서는 commit 후 response를 만들다가 lazy load가 발생해 session close 이후 오류가 나거나, 예상치 못한 추가 query가 발생할 수 있다.

그래서 API 서버에서는 종종 `expire_on_commit=False`를 선택한다.

```python
SessionLocal = sessionmaker(
    bind=engine,
    expire_on_commit=False,
)
```

트레이드오프는 명확하다.

- `True`: commit 후 DB 최신 값을 다시 읽을 수 있지만 추가 query와 detached error 가능성이 커진다
- `False`: response 생성이 단순해지지만 commit 이후 객체 값이 DB trigger나 default 반영 전 상태일 수 있다

어느 쪽이든 팀 기준을 정해야 한다. 특히 DB default, trigger, generated column에 의존한다면 `flush()`, `refresh()`, `returning` 전략까지 함께 정해야 한다.

---

## 핵심 개념 5: connection pool은 성능 옵션이 아니라 부하 제한 장치다

connection pool 설정을 단순 성능 튜닝으로 보면 운영에서 늦게 대응하게 된다. pool은 애플리케이션과 DB 사이의 backpressure 장치다.

대표 설정은 다음과 같다.

```python
engine = create_engine(
    settings.database_url,
    pool_size=10,
    max_overflow=20,
    pool_timeout=3,
    pool_recycle=1800,
    pool_pre_ping=True,
)
```

각 설정의 의미는 대략 이렇다.

- `pool_size`: 평소 유지할 connection 수
- `max_overflow`: pool_size를 초과해 임시로 더 열 수 있는 connection 수
- `pool_timeout`: connection을 빌릴 때 기다릴 최대 시간
- `pool_recycle`: 오래된 connection을 재사용하기 전에 교체하는 기준
- `pool_pre_ping`: 빌린 connection이 살아 있는지 확인

### pool을 크게 잡는다고 항상 좋아지지 않는다

API 서버 worker가 8개이고 각 프로세스가 `pool_size=20`, `max_overflow=20`이면 이론상 최대 320 connection이 DB로 갈 수 있다.

```text
8 processes * (20 pool_size + 20 max_overflow) = 320
```

PostgreSQL이 이 부하를 감당하지 못하면 API 서버는 빠른 것이 아니라 DB를 압박하는 공격자가 된다. pool은 가능한 크게 잡는 값이 아니라 DB와 애플리케이션 사이의 동시성 예산이다.

### pool_timeout은 장애를 빨리 드러내는 장치다

`pool_timeout`을 너무 길게 두면 요청이 connection을 기다리며 오래 매달린다. 사용자 입장에서는 API가 느려지고, 서버 입장에서는 worker가 점유되어 더 많은 요청이 쌓인다.

반대로 너무 짧으면 순간적인 피크에 과하게 실패할 수 있다.

실무에서는 아래처럼 생각하는 편이 좋다.

- DB가 감당 가능한 동시 query 수를 먼저 잡는다
- 애플리케이션 replica와 worker 수를 곱해 전체 connection 상한을 계산한다
- pool_timeout은 사용자가 기다릴 수 있는 시간보다 짧게 잡고 빠르게 실패시킨다
- 실패는 500 로그만 남기지 말고 pool checkout timeout metric으로 본다

### Session close 누락은 pool 장애로 드러난다

Session을 닫지 않으면 connection이 pool로 돌아가지 않을 수 있다. 특히 streaming response, background task, generator, dependency scope가 섞이면 누락이 생기기 쉽다.

기본 원칙은 단순하다.

- Session은 context manager 또는 dependency finalizer로 닫는다
- ORM 객체를 background task로 넘기지 않는다
- request session을 task나 thread 밖으로 들고 나가지 않는다
- lazy loading이 필요한 객체를 session close 이후 사용하지 않는다

---

## 실무 예시: FastAPI에서 transaction boundary를 route 밖으로 끌어내기

간단한 주문 생성 API를 생각해 보자. 흔한 구조는 이렇다.

```python
@router.post("/orders")
def create_order(
    request: CreateOrderRequest,
    session: Annotated[Session, Depends(get_session)],
) -> OrderResponse:
    order = Order(user_id=request.user_id)
    session.add(order)
    session.commit()
    session.refresh(order)
    return OrderResponse.from_orm(order)
```

작은 예제에서는 문제없다. 하지만 실제 주문 생성은 보통 재고, 쿠폰, 결제 준비, outbox, 감사 로그가 함께 들어간다. route handler에 transaction 로직이 계속 커지면 HTTP adapter와 use case가 섞인다.

조금 더 운영 친화적으로 나누면 다음과 같다.

```python
class SqlAlchemyUnitOfWork:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def __enter__(self) -> "SqlAlchemyUnitOfWork":
        self.session = self._session_factory()
        self.orders = SqlOrderRepository(self.session)
        self.products = SqlProductRepository(self.session)
        self.outbox = SqlOutboxRepository(self.session)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            if exc_type:
                self.session.rollback()
            else:
                self.session.commit()
        finally:
            self.session.close()
```

use case는 HTTP를 모른다.

```python
def create_order(command: CreateOrderCommand, uow_factory: UowFactory) -> OrderResult:
    with uow_factory() as uow:
        product = uow.products.get_for_update(command.product_id)
        product.reserve(command.quantity)

        order = Order.create(
            user_id=command.user_id,
            product_id=command.product_id,
            quantity=command.quantity,
            unit_price=product.price,
        )

        uow.orders.add(order)
        uow.outbox.add(OutboxEvent.order_created(order))

        return OrderResult(order_id=order.id, status=order.status)
```

route handler는 변환만 담당한다.

```python
@router.post("/orders")
def create_order_endpoint(request: CreateOrderRequest) -> OrderResponse:
    result = create_order(
        command=CreateOrderCommand.from_request(request),
        uow_factory=container.uow_factory,
    )
    return OrderResponse.from_result(result)
```

이 구조의 장점은 명확하다.

- transaction 경계가 use case 전체를 감싼다
- repository는 commit하지 않는다
- HTTP 밖에서도 같은 use case를 worker나 CLI에서 실행할 수 있다
- 테스트에서는 fake UoW로 DB 없이 비즈니스 흐름을 검증할 수 있다
- outbox 기록과 aggregate 변경이 같은 commit 안에 들어간다

단점도 있다.

- 클래스와 파일 수가 늘어난다
- 단순 CRUD에는 과하게 느껴질 수 있다
- 팀이 UoW 규칙을 이해하지 못하면 패턴만 복잡해진다

그래서 모든 API에 똑같이 적용할 필요는 없다. 조회 위주의 단순 endpoint는 request session만으로 충분할 수 있다. 하지만 여러 aggregate와 side effect 의도가 하나로 묶이는 write use case에는 transaction owner를 명확히 두는 편이 장기적으로 싸다.

---

## 트레이드오프 1: request 전체 transaction vs use case transaction

웹 애플리케이션에서 흔한 선택지는 두 가지다.

### 1) 요청 전체를 transaction으로 묶기

dependency에서 session을 열고, 요청이 성공하면 commit, 실패하면 rollback한다.

장점:

- 규칙이 단순하다
- handler 내부에서 commit 누락이 적다
- 여러 repository가 같은 transaction을 공유하기 쉽다

단점:

- 요청 중 외부 API 호출이 길어지면 DB transaction도 길어진다
- streaming response와 잘 맞지 않는다
- read-only 요청에도 transaction이 열릴 수 있다
- route handler가 여러 use case를 호출하면 원치 않게 하나로 묶일 수 있다

### 2) use case마다 transaction을 열기

각 write use case가 UoW 또는 `session.begin()`을 통해 transaction을 소유한다.

장점:

- transaction 경계가 비즈니스 작업과 직접 맞는다
- HTTP, worker, CLI에서 같은 규칙을 쓸 수 있다
- 외부 API 호출을 transaction 밖으로 빼기 쉽다
- read-only flow와 write flow를 다르게 설계할 수 있다

단점:

- wiring 코드가 늘어난다
- route에서 여러 use case를 조합할 때 정책을 정해야 한다
- 개발자가 use case 경계를 제대로 잡아야 한다

내 기준에서는 단순한 CRUD 서비스는 요청 단위 transaction으로 시작해도 된다. 하지만 결제, 주문, 권한, 정산, outbox처럼 원자성이 중요한 도메인은 use case transaction으로 올리는 편이 낫다.

---

## 트레이드오프 2: ORM 객체를 응답까지 들고 갈 것인가

SQLAlchemy ORM 객체를 그대로 response model로 변환하는 코드는 편하다.

```python
return OrderResponse.model_validate(order)
```

하지만 운영 코드에서는 조심해야 한다.

- response 생성 중 lazy loading이 발생할 수 있다
- session close 이후 relationship 접근이 실패할 수 있다
- 내부 DB 모델 필드가 외부 API에 노출될 수 있다
- transaction 안의 mutable ORM 객체가 계층 밖으로 퍼진다

대안은 use case 안에서 필요한 출력 값만 DTO로 고정하는 것이다.

```python
@dataclass(frozen=True, slots=True)
class OrderResult:
    order_id: str
    status: str
    total_amount: int


def create_order(command: CreateOrderCommand, uow_factory: UowFactory) -> OrderResult:
    with uow_factory() as uow:
        order = Order.create(...)
        uow.orders.add(order)
        uow.session.flush()
        return OrderResult(
            order_id=order.id,
            status=order.status.value,
            total_amount=order.total_amount,
        )
```

이렇게 하면 session이 닫힌 뒤에도 response 생성이 안전하다. 단점은 DTO 변환 코드가 늘어난다는 점이다. 하지만 외부 API가 안정적인 서비스라면 이 비용은 대체로 값어치가 있다.

---

## 트레이드오프 3: sync Session과 async Session

FastAPI를 쓰면 `AsyncSession`을 반드시 써야 할 것처럼 느껴질 수 있다. 하지만 선택 기준은 더 차분해야 한다.

### sync Session이 잘 맞는 경우

- 기존 코드와 라이브러리가 동기 기반이다
- DB 작업이 요청의 대부분이고 worker thread로 충분히 감당된다
- 팀이 동기 SQLAlchemy 운영에 익숙하다
- 트랜잭션 경계를 단순하게 유지하고 싶다

### AsyncSession이 잘 맞는 경우

- async DB driver와 async stack을 일관되게 운영한다
- 같은 요청에서 외부 async I/O가 많다
- 높은 동시성을 thread 증가 없이 다루고 싶다
- 팀이 cancellation, timeout, pool, task lifecycle을 이해하고 있다

AsyncSession은 성능 버튼이 아니다. async로 바꾸면 다음 문제도 함께 온다.

- session을 task 간 공유하면 안 된다
- cancellation 시 rollback과 close를 더 신경 써야 한다
- lazy loading은 async 문맥에서 더 조심해야 한다
- sync library와 섞이면 event loop blocking이 생길 수 있다

즉 "FastAPI니까 무조건 async DB"도 아니고, "ORM은 무조건 sync가 안전"도 아니다. 중요한 것은 애플리케이션 전체 I/O 모델과 팀의 운영 숙련도다.

---

## 흔한 실수 1: Session을 전역으로 만든다

가장 위험한 패턴이다.

```python
session = SessionLocal()

def get_user(user_id: int) -> User | None:
    return session.get(User, user_id)
```

이 코드는 요청 간 transaction 상태와 identity map을 공유한다. connection 반환도 불명확하다. 테스트에서는 우연히 동작할 수 있지만 운영에서는 거의 반드시 문제를 만든다.

전역으로 둘 수 있는 것은 Engine과 session factory다.

```python
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine)
```

Session instance는 작업 단위마다 생성한다.

---

## 흔한 실수 2: service 함수가 몰래 commit한다

아래처럼 service 내부 commit이 흩어지면 use case 원자성이 깨진다.

```python
def apply_coupon(session: Session, order: Order, coupon: Coupon) -> None:
    order.apply_coupon(coupon)
    session.commit()
```

이 함수는 이름만 보면 쿠폰 적용인데 실제로는 transaction을 끝낸다. 호출자는 이후 작업을 같은 transaction으로 묶을 수 없다.

commit하는 함수는 이름이나 계층에서 드러나야 한다. 더 좋은 방식은 commit을 use case/UoW 경계로 제한하는 것이다.

---

## 흔한 실수 3: rollback 후 Session 상태를 무시한다

DB 오류가 나면 session은 실패 상태가 될 수 있다. 이 상태에서 rollback 없이 계속 쓰면 다음 쿼리에서 다른 오류가 난다.

```python
try:
    session.flush()
except IntegrityError:
    # rollback 없이 계속 사용
    existing = session.scalar(select(User).where(User.email == email))
```

올바른 흐름은 실패한 transaction을 rollback하고, 필요하면 새 transaction에서 다시 시도하는 것이다.

```python
try:
    session.flush()
except IntegrityError:
    session.rollback()
    existing = session.scalar(select(User).where(User.email == email))
```

다만 이 예시도 실제 upsert나 unique constraint 경쟁에서는 더 신중해야 한다. 경쟁 조건이 있는 create-if-not-exists는 application check보다 DB constraint와 retry 정책을 중심으로 설계해야 한다.

---

## 흔한 실수 4: 외부 API 호출을 DB transaction 안에서 오래 수행한다

아래 코드는 결제 API 호출 동안 DB transaction을 붙잡는다.

```python
with uow_factory() as uow:
    order = uow.orders.get(order_id)
    payment_result = payment_gateway.approve(order.payment_key)
    order.mark_paid(payment_result)
```

외부 API가 3초 지연되면 transaction도 3초 동안 열린다. 그 사이 row lock이나 connection이 유지될 수 있다.

더 안전한 설계는 작업을 쪼개는 것이다.

1. DB에서 결제 시도 가능 상태인지 짧게 확인하고 payment attempt를 기록한다
2. transaction 밖에서 외부 결제 API를 호출한다
3. 결과를 새 transaction에서 반영한다
4. 중복 callback과 retry를 idempotency key로 제어한다

물론 이 방식은 더 복잡하다. 대신 긴 외부 지연이 DB transaction을 점유하지 않는다. 결제, 배송, 알림, 외부 ERP 연동처럼 느린 I/O가 섞이는 도메인은 이 설계를 고려해야 한다.

---

## 흔한 실수 5: lazy loading을 운영 API의 기본으로 둔다

relationship lazy loading은 개발 중에는 편하다.

```python
order = session.get(Order, order_id)
return {
    "order_id": order.id,
    "user_name": order.user.name,
}
```

하지만 운영에서는 N+1, session close 이후 오류, 예상치 못한 query를 만든다.

조회 API에서는 필요한 관계를 명시적으로 로드하는 편이 낫다.

```python
stmt = (
    select(Order)
    .options(selectinload(Order.items), joinedload(Order.user))
    .where(Order.id == order_id)
)
order = session.scalar(stmt)
```

더 나아가 복잡한 read model은 ORM aggregate를 그대로 쓰기보다 projection query를 별도로 두는 것도 좋다.

```python
stmt = (
    select(
        Order.id,
        User.name.label("user_name"),
        Order.total_amount,
        Order.status,
    )
    .join(User, User.id == Order.user_id)
    .where(Order.id == order_id)
)
row = session.execute(stmt).one()
```

쓰기 모델과 읽기 모델의 요구가 다르면 억지로 하나의 ORM graph에 맞추지 않는 편이 낫다.

---

## 트랜잭션 retry는 어디에 둘 것인가

운영에서는 deadlock, serialization failure, lock timeout 같은 일시적 DB 오류가 생길 수 있다. 이때 무작정 전체 요청을 재시도하면 위험하다.

재시도 가능한 조건은 제한적이어야 한다.

- transaction이 외부 side effect를 아직 수행하지 않았다
- 작업이 idempotent하거나 idempotency key가 있다
- 오류 코드가 재시도 가능한 종류로 분류된다
- backoff와 최대 횟수가 있다
- 재시도 시 새 Session 또는 깨끗한 transaction을 사용한다

예시는 다음과 같다.

```python
def run_with_transaction_retry(
    operation: Callable[[], T],
    *,
    max_attempts: int = 3,
) -> T:
    last_error: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            return operation()
        except OperationalError as exc:
            if not is_retryable_db_error(exc) or attempt == max_attempts:
                raise
            last_error = exc
            sleep(0.05 * attempt)

    raise RuntimeError("unreachable") from last_error
```

하지만 이 wrapper를 아무 곳에나 붙이면 안 된다. 예를 들어 transaction 안에서 결제 API를 호출했다면 retry가 결제 중복 승인으로 이어질 수 있다. retry는 DB transaction만 되돌리면 안전한 구간에 한정해야 한다.

---

## 테스트 전략: rollback fixture만 믿으면 부족하다

SQLAlchemy 테스트에서는 흔히 테스트마다 transaction을 열고 rollback한다.

```python
@pytest.fixture
def session():
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
```

이 방식은 빠르고 유용하다. 하지만 운영과 다른 점도 있다.

- 실제 commit 후 trigger/default/expire 동작을 놓칠 수 있다
- transaction isolation과 lock 경합을 충분히 재현하지 못한다
- background worker나 outbox publisher처럼 별도 connection을 쓰는 흐름이 가려질 수 있다
- DB 종류가 SQLite면 PostgreSQL의 constraint, lock, JSON, timezone 동작과 다를 수 있다

그래서 테스트는 층을 나누는 편이 좋다.

- 도메인 테스트: DB 없이 aggregate와 value object 규칙 검증
- repository 테스트: 실제 DB에 query와 mapping 검증
- use case 테스트: UoW fake와 real DB 케이스를 나눠 transaction 경계 검증
- migration 테스트: schema 변경과 기존 데이터 호환성 검증
- concurrency 테스트: unique constraint, lock, retry, idempotency 경합 검증

특히 운영 장애가 transaction 경계에서 났다면 단순 unit test보다 "동시에 두 요청이 같은 자원을 변경할 때"를 재현하는 테스트가 더 가치 있다.

---

## 운영 관측: SQLAlchemy도 지표가 있어야 한다

DB 장애를 query log만으로 보는 것은 늦다. 애플리케이션 쪽에서도 최소한 아래를 봐야 한다.

- pool checkout 대기 시간
- pool timeout 횟수
- checked-out connection 수
- transaction duration
- query duration histogram
- rollback count
- deadlock 또는 serialization failure count
- session 생성 대비 close 비율
- endpoint별 query count
- N+1 의심 endpoint

SQLAlchemy event hook을 이용하면 일부 지표를 붙일 수 있다.

```python
from sqlalchemy import event


@event.listens_for(engine, "checkout")
def on_checkout(dbapi_connection, connection_record, connection_proxy) -> None:
    metrics.increment("db.pool.checkout")


@event.listens_for(engine, "checkin")
def on_checkin(dbapi_connection, connection_record) -> None:
    metrics.increment("db.pool.checkin")
```

query duration은 `before_cursor_execute`, `after_cursor_execute` 이벤트로 측정할 수 있다. 다만 모든 SQL과 parameter를 그대로 로그에 남기면 개인정보와 비용 문제가 생긴다. 운영 로그는 sampling, redaction, slow query 중심으로 설계해야 한다.

---

## 실무 체크리스트

SQLAlchemy를 운영 코드에 붙이기 전에 아래를 확인하자.

- [ ] Engine은 프로세스 시작 시 한 번 만들고 재사용하는가
- [ ] Session instance를 전역으로 공유하지 않는가
- [ ] Session 생명주기가 request, job, use case 중 어떤 단위인지 명확한가
- [ ] commit과 rollback 책임이 route, service, UoW 중 한 곳으로 수렴되는가
- [ ] repository method가 몰래 commit하지 않는가
- [ ] id 생성을 위해 commit하지 않고 필요한 경우 flush를 쓰는가
- [ ] 예외 발생 시 rollback과 close가 항상 보장되는가
- [ ] 외부 API 호출이 긴 DB transaction 안에 들어 있지 않은가
- [ ] pool_size, max_overflow, worker 수를 곱한 전체 connection 상한을 계산했는가
- [ ] pool_timeout, pool_pre_ping, pool_recycle 기준을 운영 환경에 맞게 정했는가
- [ ] lazy loading이 API 응답 생성 중 예상치 못한 query를 만들지 않는가
- [ ] `expire_on_commit` 정책을 팀 기준으로 정했는가
- [ ] read model과 write aggregate를 억지로 하나의 ORM graph로 처리하지 않는가
- [ ] deadlock, lock timeout, unique constraint 경합의 retry/idempotency 기준이 있는가
- [ ] 테스트가 rollback fixture뿐 아니라 실제 commit, concurrency, migration 경로도 검증하는가
- [ ] pool checkout timeout, transaction duration, query count를 관측하는가

---

## 한줄정리

SQLAlchemy를 안정적으로 운영하려면 쿼리 문법보다 먼저 **Session을 작업 단위로 짧게 열고, commit 책임을 한 경계에 모으며, connection pool을 DB 동시성 예산으로 설계해야 한다.**
