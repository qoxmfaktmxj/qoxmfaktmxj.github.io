---
layout: post
title: "[Python 4/6] To-do 도메인 설계: 모델/스키마/관계 정의"
date: 2026-01-04 21:00:00 +0900
categories: [python]
tags: [python, fastapi, todo, sqlalchemy, schema]
---

# [Python 4/6] To-do 도메인 설계: 모델/스키마/관계 정의

## 1) Todo 모델 추가

`app/models.py` 아래 추가
```py
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

class Todo(Base):
  __tablename__ = 'todos'

  id = Column(Integer, primary_key=True, index=True)
  title = Column(String, nullable=False)
  done = Column(Boolean, default=False)
  owner_id = Column(Integer, ForeignKey('users.id'), nullable=False)
  created_at = Column(DateTime(timezone=True), server_default=func.now())

  owner = relationship('User')
```

## 2) Todo 스키마 추가

`app/schemas.py` 아래 추가
```py
class TodoCreate(BaseModel):
  title: str

class TodoUpdate(BaseModel):
  title: str | None = None
  done: bool | None = None

class TodoOut(BaseModel):
  id: int
  title: str
  done: bool
  owner_id: int
  created_at: str

  class Config:
    from_attributes = True
```

## 3) 인증 사용자 추출 의존성

`app/deps.py`
```py
from fastapi import Depends, Header, HTTPException
from jose import JWTError
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.security import decode_token

def get_current_user(
  authorization: str | None = Header(default=None),
  db: Session = Depends(get_db)
) -> User:
  if not authorization or not authorization.startswith('Bearer '):
    raise HTTPException(status_code=401, detail='인증이 필요합니다.')

  token = authorization.replace('Bearer ', '')
  try:
    payload = decode_token(token)
    user_id = int(payload['sub'])
  except (JWTError, ValueError, KeyError):
    raise HTTPException(status_code=401, detail='유효하지 않은 토큰입니다.')

  user = db.query(User).filter(User.id == user_id).first()
  if not user:
    raise HTTPException(status_code=401, detail='사용자를 찾을 수 없습니다.')
  return user
```

다음 편에서 이 의존성을 그대로 써서 소유권 기반 CRUD를 구현합니다.
