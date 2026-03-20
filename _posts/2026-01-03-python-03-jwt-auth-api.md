---
layout: post
title: "[Python 3/6] 인증 API 구현: JWT 로그인/내 정보 조회"
date: 2026-01-03 21:00:00 +0900
categories: [python]
tags: [python, fastapi, jwt, login, auth]
---

# [Python 3/6] 인증 API 구현: JWT 로그인/내 정보 조회

## 1) 패키지 설치

```bash
pip install python-jose
```

## 2) JWT 유틸 확장

`app/security.py` 아래 추가
```py
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError

SECRET_KEY = 'CHANGE_ME_FOR_REAL_PROJECT'
ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 60

def create_access_token(subject: str) -> str:
  expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
  payload = {'sub': subject, 'exp': expire}
  return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
  return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
```

## 3) 스키마 추가

`app/schemas.py` 아래 추가
```py
class LoginRequest(BaseModel):
  email: EmailStr
  password: str

class TokenResponse(BaseModel):
  access_token: str
  token_type: str = 'bearer'
```

## 4) 인증 라우터 확장

`app/routers/auth.py` 전체 교체
```py
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from jose import JWTError

from app.db import get_db
from app.models import User
from app.schemas import UserCreate, UserOut, LoginRequest, TokenResponse
from app.security import hash_password, verify_password, create_access_token, decode_token

router = APIRouter(prefix='/auth', tags=['auth'])

@router.post('/register', response_model=UserOut)
def register(payload: UserCreate, db: Session = Depends(get_db)):
  if db.query(User).filter(User.email == payload.email).first():
    raise HTTPException(status_code=400, detail='이미 사용 중인 이메일입니다.')
  user = User(email=payload.email, name=payload.name, password_hash=hash_password(payload.password))
  db.add(user)
  db.commit()
  db.refresh(user)
  return user

@router.post('/login', response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
  user = db.query(User).filter(User.email == payload.email).first()
  if not user or not verify_password(payload.password, user.password_hash):
    raise HTTPException(status_code=401, detail='이메일 또는 비밀번호가 올바르지 않습니다.')
  token = create_access_token(str(user.id))
  return TokenResponse(access_token=token)

@router.get('/me', response_model=UserOut)
def me(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
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
