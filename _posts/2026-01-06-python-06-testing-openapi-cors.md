---
layout: post
title: "[Python 6/6] 테스트/문서화/운영 기초: pytest + OpenAPI + CORS"
date: 2026-01-06 21:00:00 +0900
categories: [python]
tags: [python, fastapi, pytest, openapi, cors, education]
---

# [Python 6/6] 테스트/문서화/운영 기초: pytest + OpenAPI + CORS

백엔드 시리즈 마지막입니다. 이제 "돌아간다" 수준에서 "운영 가능한 최소 품질"로 올립니다.

## 1) 패키지 설치

```bash
pip install pytest httpx
```

## 2) CORS 설정

`app/main.py`
```py
from fastapi.middleware.cors import CORSMiddleware

# app = FastAPI(...) 아래
app.add_middleware(
  CORSMiddleware,
  allow_origins=['http://localhost:3000'],
  allow_credentials=True,
  allow_methods=['*'],
  allow_headers=['*']
)
```

## 3) 기본 테스트

`tests/test_health.py`
```py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
  res = client.get('/health')
  assert res.status_code == 200
  assert res.json()['status'] == 'ok'
```

`tests/test_auth_flow.py`
```py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_register_and_login():
  register = client.post('/auth/register', json={
    'email': 'edu@example.com',
    'name': '교육생',
    'password': 'password1234'
  })
  assert register.status_code in (200, 400)

  login = client.post('/auth/login', json={
    'email': 'edu@example.com',
    'password': 'password1234'
  })
  assert login.status_code == 200
  assert 'access_token' in login.json()
```

## 4) 테스트 실행

```bash
pytest -q
```

## 5) 문서화 포인트

- FastAPI는 `/docs`(Swagger), `/redoc` 자동 제공
- 교육 시에는 각 endpoint에 `summary`, `description`을 붙여 문서 품질을 높인다.

예시:

```py
@router.get('', summary='내 할 일 목록 조회', description='현재 로그인한 사용자 소유의 Todo만 반환합니다.')
def list_todos(...):
  ...
```

## 최종 체크리스트

- [ ] 프론트(`localhost:3000`)와 CORS 통신 정상
- [ ] 인증 없이 `/todos` 접근 시 401
- [ ] 본인 소유 Todo만 조회/수정/삭제 가능
- [ ] 최소 2개 테스트 케이스 통과

이제 Next.js 6편 + Python 6편 + 통합 실습으로 교육 과정을 완성할 수 있습니다.
