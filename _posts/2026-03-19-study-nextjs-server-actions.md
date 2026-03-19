---
layout: post
title: "Next.js Server Actions 실전 가이드: 폼 처리부터 낙관적 업데이트까지"
date: 2026-03-19 09:00:00 +0900
categories: [nextjs]
tags: [study, nextjs, server-actions, form, optimistic-update, react19]
---

## Server Actions 란

Server Actions는 클라이언트에서 직접 서버 함수를 호출할 수 있는 메커니즘이다. API Route를 별도로 만들지 않고, 컴포넌트 안에서 `"use server"` 지시어로 서버 로직을 선언한다.

```ts
// app/actions/post.ts
"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

export async function createPost(formData: FormData) {
  const title = formData.get("title") as string;
  const body  = formData.get("body")  as string;

  if (!title || !body) throw new Error("필수 필드 누락");

  await db.post.create({ data: { title, body } });
  revalidatePath("/posts");
  redirect("/posts");
}
```

## 기본 폼 연결

`<form action={serverAction}>` 패턴이 가장 간단하다. JS가 비활성화돼도 동작하는 Progressive Enhancement를 기본으로 지원한다.

```tsx
// app/posts/new/page.tsx
import { createPost } from "@/actions/post";

export default function NewPostPage() {
  return (
    <form action={createPost}>
      <input name="title" placeholder="제목" required />
      <textarea name="body" placeholder="내용" required />
      <button type="submit">등록</button>
    </form>
  );
}
```

## useFormStatus로 로딩 상태 처리

`useFormStatus`는 부모 `<form>`의 제출 상태를 감지한다. 반드시 **별도 Client Component**로 분리해야 한다.

```tsx
// components/SubmitButton.tsx
"use client";

import { useFormStatus } from "react-dom";

export function SubmitButton() {
  const { pending } = useFormStatus();
  return (
    <button type="submit" disabled={pending}>
      {pending ? "등록 중..." : "등록"}
    </button>
  );
}
```

## useActionState로 에러/성공 메시지

React 19의 `useActionState`(구 `useFormState`)를 사용하면 액션 반환값을 상태로 받을 수 있다.

```tsx
"use client";

import { useActionState } from "react";
import { createPost } from "@/actions/post";

const initialState = { error: "", success: false };

export function PostForm() {
  const [state, formAction] = useActionState(createPost, initialState);

  return (
    <form action={formAction}>
      {state.error && <p className="error">{state.error}</p>}
      {state.success && <p className="success">등록 완료!</p>}
      <input name="title" required />
      <SubmitButton />
    </form>
  );
}
```

액션도 상태를 반환하도록 수정한다.

```ts
"use server";

export async function createPost(prevState: typeof initialState, formData: FormData) {
  try {
    const title = formData.get("title") as string;
    if (!title) return { error: "제목은 필수입니다.", success: false };

    await db.post.create({ data: { title } });
    revalidatePath("/posts");
    return { error: "", success: true };
  } catch {
    return { error: "서버 오류가 발생했습니다.", success: false };
  }
}
```

## 낙관적 업데이트

`useOptimistic`을 사용하면 서버 응답 전에 UI를 먼저 업데이트해 체감 성능을 높일 수 있다.

```tsx
"use client";

import { useOptimistic, useTransition } from "react";
import { toggleLike } from "@/actions/like";

export function LikeButton({ postId, initialCount }: { postId: string; initialCount: number }) {
  const [optimisticCount, setOptimistic] = useOptimistic(
    initialCount,
    (current, _) => current + 1
  );
  const [, startTransition] = useTransition();

  function handleClick() {
    startTransition(async () => {
      setOptimistic(null);
      await toggleLike(postId);
    });
  }

  return <button onClick={handleClick}>❤️ {optimisticCount}</button>;
}
```

## 주의사항 및 패턴 정리

| 상황 | 권장 패턴 |
|---|---|
| 단순 폼 제출 | `form action={action}` |
| 에러/성공 메시지 | `useActionState` |
| 로딩 버튼 | `useFormStatus` (별도 컴포넌트) |
| 즉각 UI 반영 | `useOptimistic` |
| 조건부 리다이렉트 | 액션 내 `redirect()` |

## 오늘의 적용 체크리스트

- [ ] 기존 API Route 기반 폼을 Server Action으로 교체 검토
- [ ] `useFormStatus`로 제출 중 버튼 비활성화 처리
- [ ] `useActionState`로 에러 메시지 UI 구현
- [ ] 목록 추가/삭제에 `useOptimistic` 적용
- [ ] 민감 로직은 Server Action 내부에서만 처리 (클라이언트 노출 금지)
