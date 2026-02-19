---
layout: post
title: "SQLModel 입문: FastAPI + SQLAlchemy의 완벽 조합"
date: 2026-02-19 15:10:00 +0900
categories: [python]
tags: [study, python, sqlmodel, fastapi, database, automation]
---

# SQLModel 입문: FastAPI + SQLAlchemy의 완벽 조합

## 왜 중요한가?

SQLModel은 FastAPI 창시자(Sebastián Ramírez)가 만든 라이브러리입니다.
Pydantic + SQLAlchemy를 하나로 합쳐서, 모델을 한 번만 정의하면 API 검증과 DB 매핑이 동시에 됩니다.

기존에는 Pydantic 스키마와 SQLAlchemy 모델을 따로 만들어야 했는데, SQLModel이 이 중복을 제거해줍니다.

## 핵심 개념

- **SQLModel 클래스**
  `SQLModel`을 상속하면 Pydantic 모델이자 SQLAlchemy 테이블이 됩니다.
  `table=True` 옵션으로 DB 테이블 매핑을 활성화합니다.

- **Field 정의**
  Pydantic의 `Field`와 동일한 방식으로 제약조건을 설정합니다.
  `primary_key`, `index`, `nullable` 등 DB 옵션도 지원합니다.

- **Session 관리**
  SQLAlchemy의 `Session`을 그대로 사용합니다.
  FastAPI의 `Depends`와 조합하면 요청마다 자동으로 세션을 관리할 수 있습니다.

- **관계 정의 (Relationship)**
  `Relationship()`으로 1:N, N:M 관계를 선언적으로 정의합니다.

## 실전 예제: 유저 + 게시글 API

### 1. 모델 정의

```python
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional
from datetime import datetime

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, min_length=2)
    email: str = Field(unique=True)
    posts: list["Post"] = Relationship(back_populates="author")
```

게시글 모델은 유저와 1:N 관계입니다.

```python
class Post(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(min_length=1, max_length=200)
    content: str
    created_at: datetime = Field(default_factory=datetime.now)
    author_id: int = Field(foreign_key="user.id")
    author: Optional[User] = Relationship(back_populates="posts")
```

### 2. DB 엔진 & 세션 설정

```python
from sqlmodel import Session, create_engine

DATABASE_URL = "sqlite:///database.db"
engine = create_engine(DATABASE_URL, echo=True)

def create_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
```

### 3. FastAPI CRUD

```python
from fastapi import FastAPI, Depends, HTTPException

app = FastAPI()

@app.on_event("startup")
def on_startup():
    create_tables()

@app.post("/users")
def create_user(user: User, session: Session = Depends(get_session)):
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
```

게시글 생성과 조회입니다.

```python
@app.post("/posts")
def create_post(post: Post, session: Session = Depends(get_session)):
    session.add(post)
    session.commit()
    session.refresh(post)
    return post

@app.get("/users/{user_id}")
def get_user(user_id: int, session: Session = Depends(get_session)):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
```

## 흔한 실수

- **table=True 빠뜨리기**
  `table=True`가 없으면 순수 Pydantic 모델로만 동작합니다.
  DB에 테이블이 생성되지 않아 에러가 발생합니다.

- **id 필드에 Optional 누락**
  `id: int`로 정의하면 생성 시 id를 필수로 넣어야 합니다.
  `id: Optional[int] = Field(default=None, primary_key=True)`로 해야 auto-increment가 동작합니다.

- **Session을 commit 없이 닫기**
  `session.add()` 후 `session.commit()`을 빠뜨리면 데이터가 저장되지 않습니다.
  `session.refresh()`도 같이 호출해야 생성된 id를 받을 수 있습니다.

- **Relationship import 누락**
  `Relationship`은 `sqlmodel`에서 직접 import 해야 합니다.
  SQLAlchemy의 `relationship`과 혼동하지 마세요.

## 오늘의 실습 체크리스트

- [ ] SQLModel 설치: `pip install sqlmodel`
- [ ] User, Post 모델 정의 (table=True)
- [ ] SQLite 엔진 + 세션 설정
- [ ] create_all()로 테이블 자동 생성 확인
- [ ] CRUD 엔드포인트 작성 후 `/docs`에서 테스트
- [ ] Relationship으로 유저의 게시글 목록 조회
