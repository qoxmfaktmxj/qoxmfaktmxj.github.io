---
layout: post
title: "[Next.js 4/6] To-do 화면 만들기: 목록/추가/수정/완료 UI 컴포넌트"
date: 2026-01-04 09:00:00 +0900
categories: [nextjs]
tags: [nextjs, todo, components, ui, education]
---

# [Next.js 4/6] To-do 화면 만들기: 목록/추가/수정/완료 UI 컴포넌트

이번 편은 투두 앱의 화면을 실전처럼 분리합니다.

## 폴더 구조

```txt
src/
  components/todo/
    TodoForm.tsx
    TodoItem.tsx
    TodoList.tsx
  types/todo.ts
  app/(dashboard)/todos/page.tsx
```

## 1) 타입 정의

`src/types/todo.ts`
```ts
export type Todo = {
  id: number;
  title: string;
  done: boolean;
  created_at: string;
};
```

## 2) 입력 폼

`src/components/todo/TodoForm.tsx`
```tsx
'use client';

import { useState } from 'react';

export function TodoForm({ onCreate }: { onCreate: (title: string) => Promise<void> }) {
  const [title, setTitle] = useState('');

  return (
    <form
      onSubmit={async (e) => {
        e.preventDefault();
        if (!title.trim()) return;
        await onCreate(title.trim());
        setTitle('');
      }}
      style={{ display: 'flex', gap: 8 }}
    >
      <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="할 일을 입력하세요" />
      <button type="submit">추가</button>
    </form>
  );
}
```

## 3) 아이템 컴포넌트

`src/components/todo/TodoItem.tsx`
```tsx
'use client';

import type { Todo } from '@/types/todo';

export function TodoItem({
  todo,
  onToggle,
  onDelete
}: {
  todo: Todo;
  onToggle: (id: number, done: boolean) => Promise<void>;
  onDelete: (id: number) => Promise<void>;
}) {
  return (
    <li style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <input
        type="checkbox"
        checked={todo.done}
        onChange={() => onToggle(todo.id, !todo.done)}
      />
      <span style={{ textDecoration: todo.done ? 'line-through' : 'none' }}>{todo.title}</span>
      <button onClick={() => onDelete(todo.id)}>삭제</button>
    </li>
  );
}
```

## 4) 리스트 컴포넌트

`src/components/todo/TodoList.tsx`
```tsx
import type { Todo } from '@/types/todo';
import { TodoItem } from './TodoItem';

export function TodoList({
  todos,
  onToggle,
  onDelete
}: {
  todos: Todo[];
  onToggle: (id: number, done: boolean) => Promise<void>;
  onDelete: (id: number) => Promise<void>;
}) {
  return (
    <ul style={{ display: 'grid', gap: 8, paddingLeft: 20 }}>
      {todos.map((todo) => (
        <TodoItem key={todo.id} todo={todo} onToggle={onToggle} onDelete={onDelete} />
      ))}
    </ul>
  );
}
```

## 5) 페이지 연결(임시 더미 데이터)

`src/app/(dashboard)/todos/page.tsx`
```tsx
'use client';

import { useState } from 'react';
import { TodoForm } from '@/components/todo/TodoForm';
import { TodoList } from '@/components/todo/TodoList';
import type { Todo } from '@/types/todo';

export default function TodosPage() {
  const [todos, setTodos] = useState<Todo[]>([]);

  const onCreate = async (title: string) => {
    setTodos((prev) => [...prev, {
      id: Date.now(),
      title,
      done: false,
      created_at: new Date().toISOString()
    }]);
  };

  const onToggle = async (id: number, done: boolean) => {
    setTodos((prev) => prev.map((t) => (t.id === id ? { ...t, done } : t)));
  };

  const onDelete = async (id: number) => {
    setTodos((prev) => prev.filter((t) => t.id !== id));
  };

  return (
    <main style={{ padding: 24, maxWidth: 640 }}>
      <h1>To-do</h1>
      <TodoForm onCreate={onCreate} />
      <TodoList todos={todos} onToggle={onToggle} onDelete={onDelete} />
    </main>
  );
}
```

다음 편(5/6)에서 이 더미 상태를 SWR + 실제 백엔드 API로 치환합니다.
