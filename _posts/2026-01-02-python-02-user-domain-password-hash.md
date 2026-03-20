---
layout: post
title: "[Python 2/6] 회원 도메인 구현: User 모델 + 비밀번호 해싱"
date: 2026-01-02 21:00:00 +0900
categories: [python]
tags: [python, fastapi, auth, sqlalchemy, bcrypt]
---

# [Python 2/6] 회원 도메인 구현: User 모델 + 비밀번호 해싱

## 1) 패키지 추가

```bash
pip install passlib[bcrypt]
```

## 2) 모델 정의

`app/models.py`
```py
from sqlalchemy import Boolean, Column, DateTime, Integer, String, func
from app.db import Base

class User(Base):
  __tablename__ = 'users'

  id = Column(Integer, primary_key=True, index=True)
  email = Column(String, unique=True, index=True, nullable=False)
  name = Column(String, nullable=False)
  password_hash = Column(String, nullable=False)
  is_active = Column(Boolean, default=True)
  created_at = Column(DateTime(timezone=True), server_default=func.now())
```

## 3) 스키마

`app/schemas.py`
```py
from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
  email: EmailStr
  name: str
  password: str

class UserOut(BaseModel):
  id: int
  email: EmailStr
  name: str

  class Config:
    from_attributes = True
```

## 4) 보안 유틸

`app/security.py`
```py
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

def hash_password(password: str) -> str:
  return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
  return pwd_context.verify(plain, hashed)
```

## 5) 회원가입 라우터

`app/routers/auth.py`
```py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.schemas import UserCreate, UserOut
from app.security import hash_password

router = APIRouter(prefix='/auth', tags=['auth'])

@router.post('/register', response_model=UserOut)
def register(payload: UserCreate, db: Session = Depends(get_db)):
  if db.query(User).filter(User.email == payload.email).first():
    raise HTTPException(status_code=400, detail='이미 사용 중인 이메일입니다.')

  user = User(
    email=payload.email,
    name=payload.name,
    password_hash=hash_password(payload.password)
  )
  db.add(user)
  db.commit()
  db.refresh(user)
  return user
```

## 6) main.py 연결 + 테이블 생성

`app/main.py`
```py
from fastapi import FastAPI
from app.db import Base, engine
from app.routers.health import router as health_router
from app.routers.auth import router as auth_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title='Todo Backend')
app.include_router(health_router)
app.include_router(auth_router)
```
