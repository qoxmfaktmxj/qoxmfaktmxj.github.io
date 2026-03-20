---
layout: post
title: "[Next.js 3/6] 인증 흐름 구현: Next API Route + HttpOnly 쿠키"
date: 2026-01-03 09:00:00 +0900
categories: [nextjs]
tags: [nextjs, auth, cookie, jwt, route-handler]
---

# [Next.js 3/6] 인증 흐름 구현: Next API Route + HttpOnly 쿠키

이번 편은 보안상 중요한 파트입니다. 토큰을 localStorage에 넣지 않고 **HttpOnly 쿠키**로 다루는 기준 예제를 만듭니다.

## 학습 목표

- Next Route Handler로 백엔드를 프록시한다.
- access token을 HttpOnly 쿠키로 저장한다.
- 로그인 상태 확인용 `me` API를 만든다.

## 1) 로그인 API 프록시

`src/app/api/auth/login/route.ts`
```ts
import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

export async function POST(req: Request) {
  const body = await req.json();
  const res = await fetch(`${API}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });

  if (!res.ok) {
    return NextResponse.json({ message: 'login failed' }, { status: 401 });
  }

  const data = await res.json() as { access_token: string };
  (await cookies()).set('access_token', data.access_token, {
    httpOnly: true,
    secure: false,
    sameSite: 'lax',
    path: '/'
  });

  return NextResponse.json({ ok: true });
}
```

## 2) 회원가입 API 프록시

`src/app/api/auth/signup/route.ts`
```ts
import { NextResponse } from 'next/server';
const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

export async function POST(req: Request) {
  const body = await req.json();
  const res = await fetch(`${API}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });

  if (!res.ok) {
    return NextResponse.json({ message: 'signup failed' }, { status: 400 });
  }

  return NextResponse.json({ ok: true });
}
```

## 3) 로그인 사용자 조회 API

`src/app/api/auth/me/route.ts`
```ts
import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

export async function GET() {
  const token = (await cookies()).get('access_token')?.value;
  if (!token) {
    return NextResponse.json({ message: 'unauthorized' }, { status: 401 });
  }

  const res = await fetch(`${API}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: 'no-store'
  });

  if (!res.ok) {
    return NextResponse.json({ message: 'unauthorized' }, { status: 401 });
  }

  const user = await res.json();
  return NextResponse.json(user);
}
```

## 4) 로그아웃 API

`src/app/api/auth/logout/route.ts`
```ts
import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';

export async function POST() {
  (await cookies()).delete('access_token');
  return NextResponse.json({ ok: true });
}
```

## 체크

- 로그인 성공 후 개발자도구 Application 탭에서 쿠키 생성 확인
- `/api/auth/me` 호출 시 사용자 정보가 나오면 정상

## 과제

- 필수: 로그인 실패 메시지를 백엔드 에러 메시지와 매핑
- 도전: refresh token 쿠키까지 확장
