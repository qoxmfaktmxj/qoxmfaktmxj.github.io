---
layout: post
title: "[Next.js 6/6] 보호 페이지, 미들웨어, 로그아웃까지 완성"
date: 2026-01-06 09:00:00 +0900
categories: [nextjs]
tags: [nextjs, middleware, auth-guard, logout, education]
---

# [Next.js 6/6] 보호 페이지, 미들웨어, 로그아웃까지 완성

프론트엔드 시리즈 마지막입니다. 인증이 필요한 페이지를 막고, 로그아웃까지 닫습니다.

## 1) 미들웨어 추가

`src/middleware.ts`
```ts
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(req: NextRequest) {
  const token = req.cookies.get('access_token')?.value;
  const { pathname } = req.nextUrl;

  const isAuthPage = pathname.startsWith('/login') || pathname.startsWith('/signup');
  const isTodoPage = pathname.startsWith('/todos');

  if (isTodoPage && !token) {
    return NextResponse.redirect(new URL('/login', req.url));
  }

  if (isAuthPage && token) {
    return NextResponse.redirect(new URL('/todos', req.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/login', '/signup', '/todos/:path*']
};
```

## 2) 로그아웃 버튼 컴포넌트

`src/components/auth/LogoutButton.tsx`
```tsx
'use client';

import { useRouter } from 'next/navigation';

export function LogoutButton() {
  const router = useRouter();

  return (
    <button
      onClick={async () => {
        await fetch('/api/auth/logout', { method: 'POST' });
        router.push('/login');
        router.refresh();
      }}
    >
      로그아웃
    </button>
  );
}
```

## 3) 투두 페이지에 사용자 정보 + 로그아웃

`src/app/(dashboard)/todos/page.tsx` 상단에 추가:

```tsx
import { LogoutButton } from '@/components/auth/LogoutButton';
```

렌더링 영역에 추가:

```tsx
<header style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
  <h1>To-do</h1>
  <LogoutButton />
</header>
```

## 4) 체크리스트

- [ ] 로그인 안 된 상태로 `/todos` 접근 시 `/login` 이동
- [ ] 로그인 상태에서 `/login` 접근 시 `/todos` 이동
- [ ] 로그아웃 버튼 클릭 시 쿠키 삭제 + `/login` 이동

## 마무리

이제 Next.js 6편이 완료되었습니다.
다음 Python 6편과 연결하면 **실무형 로그인+투두 풀스택 교육 과정**이 완성됩니다.
