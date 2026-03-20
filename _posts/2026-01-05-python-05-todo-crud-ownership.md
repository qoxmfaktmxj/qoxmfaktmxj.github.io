---
layout: post
title: "[Python 5/6] To-do CRUD API 구현: 본인 데이터 권한 체크"
date: 2026-01-05 21:00:00 +0900
categories: [python]
tags: [python, fastapi, todo-crud, authorization, backend]
---

# [Python 5/6] To-do CRUD API 구현: 본인 데이터 권한 체크

## 1) 라우터 작성

`app/routers/todos.py`
```py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import Todo, User
from app.schemas import TodoCreate, TodoOut, TodoUpdate

router = APIRouter(prefix='/todos', tags=['todos'])

@router.get('', response_model=list[TodoOut])
def list_todos(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
  return db.query(Todo).filter(Todo.owner_id == current_user.id).order_by(Todo.id.desc()).all()

@router.post('', response_model=TodoOut)
def create_todo(payload: TodoCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
  todo = Todo(title=payload.title, owner_id=current_user.id)
  db.add(todo)
  db.commit()
  db.refresh(todo)
  return todo

@router.patch('/{todo_id}', response_model=TodoOut)
def update_todo(todo_id: int, payload: TodoUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
  todo = db.query(Todo).filter(Todo.id == todo_id, Todo.owner_id == current_user.id).first()
  if not todo:
    raise HTTPException(status_code=404, detail='할 일을 찾을 수 없습니다.')

  if payload.title is not None:
    todo.title = payload.title
  if payload.done is not None:
    todo.done = payload.done

  db.commit()
  db.refresh(todo)
  return todo

@router.delete('/{todo_id}', status_code=204)
def delete_todo(todo_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
  todo = db.query(Todo).filter(Todo.id == todo_id, Todo.owner_id == current_user.id).first()
  if not todo:
    raise HTTPException(status_code=404, detail='할 일을 찾을 수 없습니다.')
  db.delete(todo)
  db.commit()
```

## 2) main.py 등록

`app/main.py`
```py
from fastapi import FastAPI
from app.db import Base, engine
from app.routers.health import router as health_router
from app.routers.auth import router as auth_router
from app.routers.todos import router as todos_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title='Todo Backend')
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(todos_router)
```

## 3) 수동 테스트 순서

1. `/auth/register`
2. `/auth/login` → access_token 확보
3. `/todos` POST/GET/PATCH/DELETE 호출 (Authorization: Bearer ...)

## 핵심 포인트

- SQL 쿼리에서 `owner_id == current_user.id`를 항상 조건으로 넣는다.
- 이 한 줄이 빠지면 다중 사용자 데이터 누출 사고가 발생한다.
