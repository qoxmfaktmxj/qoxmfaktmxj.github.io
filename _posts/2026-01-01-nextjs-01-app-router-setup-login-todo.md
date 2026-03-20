---
layout: post
title: "[Next.js 1/6] App Router 기반 로그인+To-do 프론트엔드 시작하기"
date: 2026-01-01 09:00:00 +0900
categories: [nextjs]
tags: [nextjs, app-router, education, todo, auth]
---

# [Next.js 1/6] App Router 기반 로그인+To-do 프론트엔드 시작하기

이 글은 **프론트엔드 교육 시리즈 1편**입니다. 목표는 로그인/투두 앱 프론트엔드의 뼈대를 만들고, 다음 편에서 바로 기능을 붙일 수 있게 준비하는 것입니다.

## 학습 목표

- Next.js App Router 프로젝트를 실습용으로 초기화한다.
- 로그인/회원가입/투두 화면 라우트를 먼저 만든다.
- 백엔드 연동 전 공통 API 클라이언트 구조를 만든다.

## 1) 프로젝트 생성

```bash
npx create-next-app@latest frontend --ts --eslint --app --src-dir --import-alias "@/*"
cd frontend
npm i clsx
```

## 2) 폴더 구조

```txt
src/
  app/
    (auth)/
      login/page.tsx
      signup/page.tsx
    (dashboard)/
      todos/page.tsx
    layout.tsx
    page.tsx
  lib/
    api.ts
```

## 3) 공통 레이아웃

`src/app/layout.tsx`
```tsx
import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Next + FastAPI Todo',
  description: '교육용 로그인/투두 앱'
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body style={{ margin: 0, fontFamily: 'Pretendard, sans-serif' }}>{children}</body>
    </html>
  );
}
```

## 4) 홈, 로그인, 회원가입, 투두 화면 스켈레톤

`src/app/page.tsx`
```tsx
import Link from 'next/link';

export default function HomePage() {
  return (
    <main style={{ padding: 24 }}>
      <h1>교육용 Next.js + FastAPI Todo</h1>
      <ul>
        <li><Link href="/login">로그인</Link></li>
        <li><Link href="/signup">회원가입</Link></li>
        <li><Link href="/todos">투두</Link></li>
      </ul>
    </main>
  );
}
```

`src/app/(auth)/login/page.tsx`
```tsx
export default function LoginPage() {
  return (
    <main style={{ padding: 24 }}>
      <h1>로그인</h1>
      <p>2편에서 폼/검증을 붙입니다.</p>
    </main>
  );
}
```

`src/app/(auth)/signup/page.tsx`
```tsx
export default function SignupPage() {
  return (
    <main style={{ padding: 24 }}>
      <h1>회원가입</h1>
      <p>2편에서 폼/검증을 붙입니다.</p>
    </main>
  );
}
```

`src/app/(dashboard)/todos/page.tsx`
```tsx
export default function TodosPage() {
  return (
    <main style={{ padding: 24 }}>
      <h1>To-do List</h1>
      <p>4편부터 실제 UI/컴포넌트를 구성합니다.</p>
    </main>
  );
}
```

## 5) 공통 API 클라이언트 준비

`src/lib/api.ts`
```ts
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {})
    },
    cache: 'no-store'
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `API Error: ${res.status}`);
  }

  return res.json() as Promise<T>;
}
```

`.env.local`
```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

## 6) 실행

```bash
npm run dev
```

- `http://localhost:3000`
- 로그인/회원가입/투두 라우트 이동 확인

## 흔한 실수

- `(auth)` 같은 route group 폴더명에 괄호 누락
- `.env.local` 수정 후 dev 서버 재시작 안 함
- `@/*` alias를 tsconfig와 다르게 사용

## 과제

- 필수: 네비게이션 바 컴포넌트를 추가하고 모든 페이지에 공통 적용
- 도전: `not-found.tsx`와 `error.tsx` 기본 화면 작성
