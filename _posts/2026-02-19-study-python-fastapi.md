---
layout: post
title: "FastAPI 실전 가이드: CRUD API 빠르게 만들기"
date: 2026-02-19 15:00:00 +0900
categories: [python]
tags: [study, python, fastapi, backend, automation]
---

# FastAPI 실전 가이드: CRUD API 빠르게 만들기

## 왜 중요한가?

FastAPI는 Python 웹 프레임워크 중 가장 빠른 성능을 자랑합니다.
Pydantic 기반 자동 검증과 Swagger 문서 자동 생성 덕분에 API 개발 속도가 크게 향상됩니다.

스타트업부터 대기업까지 실무에서 빠르게 채택되고 있는 프레임워크입니다.

## 핵심 개념

- **비동기 지원**
  `async/await` 기반으로 높은 동시 처리 성능을 제공합니다.

- **Pydantic 통합**
  요청/응답 모델을 Pydantic으로 정의하면 자동 검증 + 문서화가 됩니다.

- **의존성 주입 (Depends)**
  DB 세션, 인증 등 공통 로직을 깔끔하게 분리할 수 있습니다.

- **자동 API 문서**
  `/docs` (Swagger UI)와 `/redoc`이 자동 생성됩니다.

## 실전 예제: Todo CRUD API

### 1. 모델 정의

```python
from pydantic import BaseModel, Field
from typing import Optional

class TodoCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None

class TodoResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    completed: bool
```

### 2. FastAPI 앱 & CRUD 엔드포인트

```python
from fastapi import FastAPI, HTTPException

app = FastAPI(title="Todo API")

# 임시 저장소 (실무에서는 DB 사용)
todos: dict[int, dict] = {}
counter = 0
```

생성과 조회 엔드포인트입니다.

```python
@app.post("/todos", response_model=TodoResponse)
async def create_todo(todo: TodoCreate):
    global counter
    counter += 1
    item = {"id": counter, **todo.dict(), "completed": False}
    todos[counter] = item
    return item

@app.get("/todos/{todo_id}", response_model=TodoResponse)
async def get_todo(todo_id: int):
    if todo_id not in todos:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todos[todo_id]
```

수정과 삭제 엔드포인트입니다.

```python
@app.put("/todos/{todo_id}", response_model=TodoResponse)
async def update_todo(todo_id: int, todo: TodoCreate):
    if todo_id not in todos:
        raise HTTPException(status_code=404, detail="Todo not found")
    todos[todo_id].update(todo.dict())
    return todos[todo_id]

@app.delete("/todos/{todo_id}")
async def delete_todo(todo_id: int):
    if todo_id not in todos:
        raise HTTPException(status_code=404, detail="Todo not found")
    del todos[todo_id]
    return {"message": "삭제 완료"}
```

### 3. 실행

```bash
pip install fastapi uvicorn
uvicorn main:app --reload
```

브라우저에서 `http://localhost:8000/docs` 접속하면 Swagger UI에서 바로 테스트 가능합니다.

## 흔한 실수

- **async 함수에서 동기 I/O 호출**
  `await` 없이 `requests.get()` 같은 동기 호출을 쓰면 전체 이벤트 루프가 블로킹됩니다.
  `httpx.AsyncClient`를 사용하세요.

- **response_model 생략**
  응답 모델을 지정하지 않으면 내부 데이터가 그대로 노출될 수 있습니다.
  민감한 필드 필터링을 위해 반드시 설정하세요.

- **HTTPException 대신 return으로 에러 처리**
  `return {"error": "not found"}` 방식은 상태 코드가 200으로 나갑니다.
  반드시 `HTTPException`을 raise 하세요.

- **CORS 설정 누락**
  프론트엔드에서 호출 시 CORS 에러가 발생합니다.
  `CORSMiddleware`를 추가해야 합니다.

## 오늘의 실습 체크리스트

- [ ] FastAPI + uvicorn 설치
- [ ] Todo CRUD 4개 엔드포인트 구현
- [ ] `/docs`에서 Swagger UI 확인
- [ ] HTTPException으로 에러 처리 테스트
- [ ] Pydantic 모델로 요청 검증 확인
