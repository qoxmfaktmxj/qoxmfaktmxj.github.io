---
layout: post
title: "[Python 1/6] FastAPI 백엔드 프로젝트 시작: REST 기본 구조"
date: 2026-01-01 21:00:00 +0900
categories: [python]
tags: [python, fastapi, rest, education, backend]
---

# [Python 1/6] FastAPI 백엔드 프로젝트 시작: REST 기본 구조

## 목표

- FastAPI 프로젝트를 실행 가능한 형태로 초기화
- DB 연결(SessionLocal) 및 Health API 준비
- 다음 편에서 auth/todo를 붙일 베이스 완성

## 1) 프로젝트 생성

```bash
mkdir backend && cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn sqlalchemy pydantic[email]
```

`requirements.txt`
```txt
fastapi==0.115.0
uvicorn==0.30.6
sqlalchemy==2.0.35
pydantic==2.9.2
email-validator==2.2.0
```

## 2) 폴더 구조

```txt
app/
  main.py
  db.py
  routers/
    health.py
```

## 3) DB 연결

`app/db.py`
```py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = 'sqlite:///./app.db'

engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
  db = SessionLocal()
  try:
    yield db
  finally:
    db.close()
```

## 4) Health Router

`app/routers/health.py`
```py
from fastapi import APIRouter

router = APIRouter(prefix='/health', tags=['health'])

@router.get('')
def health_check():
  return {'status': 'ok'}
```

## 5) FastAPI 엔트리포인트

`app/main.py`
```py
from fastapi import FastAPI
from app.routers.health import router as health_router

app = FastAPI(title='Todo Backend')
app.include_router(health_router)
```

## 6) 실행

```bash
uvicorn app.main:app --reload --port 8000
```

- `http://localhost:8000/health`
- `http://localhost:8000/docs`

## 과제

- 필수: `/health/db` endpoint를 만들어 DB 연결 테스트 반환
- 도전: `settings.py`로 환경변수 분리
