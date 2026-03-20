---
layout: post
title: "[Next.js 5/6] SWR + Optimistic Update로 To-do CRUD 연동"
date: 2026-01-05 09:00:00 +0900
categories: [nextjs]
tags: [nextjs, swr, optimistic-update, todo, api]
---

# [Next.js 5/6] SWR + Optimistic Update로 To-do CRUD 연동

이번 편에서는 화면 상태를 실제 API와 연결합니다.

## 1) 패키지 설치

```bash
npm i swr
```

## 2) SWR 훅 생성

`src/hooks/useTodos.ts`
```ts
'use client';

import useSWR from 'swr';
import type { Todo } from '@/types/todo';

const fetcher = async (url: string): Promise<Todo[]> => {
  const res = await fetch(url, { cache: 'no-store' });
  if (!res.ok) throw new Error('failed to fetch');
  return res.json();
};

export function useTodos() {
  const { data, error, mutate, isLoading } = useSWR<Todo[]>('/api/todos', fetcher);

  return {
    todos: data ?? [],
    error,
    isLoading,
    mutate
  };
}
```

## 3) 투두 API 프록시

`src/app/api/todos/route.ts`
```ts
import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';
const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

export async function GET() {
  const token = (await cookies()).get('access_token')?.value;
  const res = await fetch(`${API}/todos`, { headers: { Authorization: `Bearer ${token}` }, cache: 'no-store' });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}

export async function POST(req: Request) {
  const token = (await cookies()).get('access_token')?.value;
  const body = await req.json();
  const res = await fetch(`${API}/todos`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify(body)
  });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
```

`src/app/api/todos/[id]/route.ts`
```ts
import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';
const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

export async function PATCH(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const token = (await cookies()).get('access_token')?.value;
  const body = await req.json();
  const res = await fetch(`${API}/todos/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify(body)
  });
  return NextResponse.json(await res.json(), { status: res.status });
}

export async function DELETE(_: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const token = (await cookies()).get('access_token')?.value;
  const res = await fetch(`${API}/todos/${id}`, { method: 'DELETE', headers: { Authorization: `Bearer ${token}` } });
  return NextResponse.json({}, { status: res.status });
}
```

## 4) 페이지에서 낙관적 업데이트

`src/app/(dashboard)/todos/page.tsx`
```tsx
'use client';

import { TodoForm } from '@/components/todo/TodoForm';
import { TodoList } from '@/components/todo/TodoList';
import { useTodos } from '@/hooks/useTodos';

export default function TodosPage() {
  const { todos, mutate, isLoading } = useTodos();

  const onCreate = async (title: string) => {
    await mutate(async (prev = []) => {
      const optimistic = [...prev, { id: Date.now(), title, done: false, created_at: new Date().toISOString() }];
      const res = await fetch('/api/todos', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ title }) });
      if (!res.ok) throw new Error('create failed');
      const created = await res.json();
      return [...prev, created];
    }, { optimisticData: [...todos, { id: Date.now(), title, done: false, created_at: new Date().toISOString() }], rollbackOnError: true, revalidate: false });
  };

  const onToggle = async (id: number, done: boolean) => {
    await mutate(async (prev = []) => {
      const res = await fetch(`/api/todos/${id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ done }) });
      if (!res.ok) throw new Error('toggle failed');
      return prev.map((t) => (t.id === id ? { ...t, done } : t));
    }, { optimisticData: todos.map((t) => (t.id === id ? { ...t, done } : t)), rollbackOnError: true, revalidate: false });
  };

  const onDelete = async (id: number) => {
    await mutate(async (prev = []) => {
      const res = await fetch(`/api/todos/${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('delete failed');
      return prev.filter((t) => t.id !== id);
    }, { optimisticData: todos.filter((t) => t.id !== id), rollbackOnError: true, revalidate: false });
  };

  if (isLoading) return <main style={{ padding: 24 }}>로딩 중...</main>;

  return (
    <main style={{ padding: 24, maxWidth: 640 }}>
      <h1>To-do</h1>
      <TodoForm onCreate={onCreate} />
      <TodoList todos={todos} onToggle={onToggle} onDelete={onDelete} />
    </main>
  );
}
```
