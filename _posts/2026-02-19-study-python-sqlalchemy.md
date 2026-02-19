---
layout: post
title: "SQLAlchemy 핵심 정리: Python ORM의 표준"
date: 2026-02-19 15:20:00 +0900
categories: [python]
tags: [study, python, sqlalchemy, database, backend, automation]
---

# SQLAlchemy 핵심 정리: Python ORM의 표준

## 왜 중요한가?

SQLAlchemy는 Python에서 가장 오래되고 널리 쓰이는 ORM입니다.
Django ORM과 달리 프레임워크에 종속되지 않아 FastAPI, Flask 등 어디서든 사용 가능합니다.

Raw SQL을 직접 쓰지 않으면서도 복잡한 쿼리를 Python 코드로 표현할 수 있습니다.

## 핵심 개념

- **Engine**
  DB 연결을 관리하는 핵심 객체입니다.
  커넥션 풀링을 자동으로 처리합니다.

- **Declarative Base**
  모든 모델의 부모 클래스입니다.
  SQLAlchemy 2.0에서는 `DeclarativeBase`를 사용합니다.

- **Session**
  DB 트랜잭션의 단위입니다.
  `add()`, `commit()`, `rollback()`, `query()` 등을 제공합니다.

- **Column & Relationship**
  테이블 컬럼과 테이블 간 관계를 정의합니다.
  `ForeignKey`로 외래키를 설정합니다.

## 실전 예제: 상품 + 주문 시스템

### 1. 엔진 & Base 설정 (2.0 스타일)

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session

DATABASE_URL = "sqlite:///shop.db"
engine = create_engine(DATABASE_URL, echo=True)

class Base(DeclarativeBase):
    pass
```

### 2. 모델 정의

```python
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, index=True)
    price = Column(Float, nullable=False)
    stock = Column(Integer, default=0)
    orders = relationship("Order", back_populates="product")
```

주문 모델은 상품과 N:1 관계입니다.

```python
class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    quantity = Column(Integer, nullable=False)
    total_price = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    product_id = Column(Integer, ForeignKey("products.id"))
    product = relationship("Product", back_populates="orders")
```

### 3. 테이블 생성 & CRUD

```python
# 테이블 생성
Base.metadata.create_all(engine)
```

데이터 추가와 조회입니다.

```python
with Session(engine) as session:
    # 상품 추가
    laptop = Product(name="맥북 프로", price=2500000, stock=10)
    session.add(laptop)
    session.commit()
    session.refresh(laptop)

    # 주문 생성
    order = Order(
        quantity=2,
        total_price=laptop.price * 2,
        product_id=laptop.id,
    )
    session.add(order)
    session.commit()
```

조건 조회와 필터링입니다.

```python
from sqlalchemy import select

with Session(engine) as session:
    # 가격 100만원 이상 상품 조회
    stmt = select(Product).where(Product.price >= 1000000)
    products = session.scalars(stmt).all()

    for p in products:
        print(f"{p.name}: {p.price:,.0f}원 (재고: {p.stock})")

    # 특정 상품의 주문 내역
    stmt = select(Order).where(Order.product_id == 1)
    orders = session.scalars(stmt).all()
```

### 4. 업데이트 & 삭제

```python
with Session(engine) as session:
    product = session.get(Product, 1)
    product.stock -= 2  # 재고 차감
    session.commit()

    # 삭제
    old_order = session.get(Order, 1)
    session.delete(old_order)
    session.commit()
```

## 흔한 실수

- **Session을 전역으로 공유**
  하나의 Session을 여러 요청에서 공유하면 데이터 충돌이 발생합니다.
  요청마다 새 Session을 생성하고 `with` 문으로 관리하세요.

- **commit() 빼먹기**
  `add()` 후 `commit()`을 하지 않으면 DB에 반영되지 않습니다.
  `with` 블록을 벗어나면 자동 rollback 됩니다.

- **N+1 쿼리 문제**
  `relationship`으로 연결된 데이터에 접근할 때마다 추가 쿼리가 발생합니다.
  `joinedload()` 또는 `selectinload()`로 Eager Loading을 적용하세요.

- **1.x 스타일과 2.0 스타일 혼용**
  `session.query(Model)` (1.x)와 `select(Model)` (2.0)을 섞으면 혼란스럽습니다.
  새 프로젝트는 2.0 스타일(`select`)로 통일하세요.

## 오늘의 실습 체크리스트

- [ ] SQLAlchemy 설치: `pip install sqlalchemy`
- [ ] Engine + DeclarativeBase 설정
- [ ] Product, Order 모델 정의 (relationship 포함)
- [ ] create_all()로 테이블 생성
- [ ] CRUD 작성: 추가, 조회, 수정, 삭제
- [ ] `select().where()` 조건 쿼리 연습
- [ ] `joinedload()`로 N+1 문제 해결 테스트
