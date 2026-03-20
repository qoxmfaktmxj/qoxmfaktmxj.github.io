---
layout: post
title: "[Next.js 2/6] 로그인/회원가입 폼 만들기 (react-hook-form + zod)"
date: 2026-01-02 09:00:00 +0900
categories: [nextjs]
tags: [nextjs, react-hook-form, zod, auth, education]
---

# [Next.js 2/6] 로그인/회원가입 폼 만들기 (react-hook-form + zod)

이번 편에서는 실제 교육 현장에서 가장 많이 쓰는 조합인 **react-hook-form + zod**로 인증 폼을 완성합니다.

## 학습 목표

- 폼 상태 관리와 스키마 검증을 분리해서 이해한다.
- 로그인/회원가입 폼을 복붙 가능한 수준으로 만든다.
- 백엔드 에러를 사용자 메시지로 표현한다.

## 1) 패키지 설치

```bash
npm i react-hook-form zod @hookform/resolvers
```

## 2) 스키마 정의

`src/lib/validators/auth.ts`
```ts
import { z } from 'zod';

export const loginSchema = z.object({
  email: z.string().email('올바른 이메일 형식이 아닙니다.'),
  password: z.string().min(8, '비밀번호는 8자 이상이어야 합니다.')
});

export const signupSchema = loginSchema.extend({
  name: z.string().min(2, '이름은 2자 이상이어야 합니다.')
});

export type LoginForm = z.infer<typeof loginSchema>;
export type SignupForm = z.infer<typeof signupSchema>;
```

## 3) 로그인 페이지

`src/app/(auth)/login/page.tsx`
```tsx
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { loginSchema, type LoginForm } from '@/lib/validators/auth';

export default function LoginPage() {
  const router = useRouter();
  const [serverError, setServerError] = useState('');

  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema)
  });

  const onSubmit = async (values: LoginForm) => {
    setServerError('');
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(values)
    });

    if (!res.ok) {
      setServerError('이메일 또는 비밀번호를 확인해 주세요.');
      return;
    }

    router.push('/todos');
  };

  return (
    <main style={{ padding: 24, maxWidth: 420 }}>
      <h1>로그인</h1>
      <form onSubmit={handleSubmit(onSubmit)} style={{ display: 'grid', gap: 12 }}>
        <input placeholder="email" {...register('email')} />
        {errors.email && <p>{errors.email.message}</p>}

        <input type="password" placeholder="password" {...register('password')} />
        {errors.password && <p>{errors.password.message}</p>}

        {serverError && <p style={{ color: 'crimson' }}>{serverError}</p>}

        <button disabled={isSubmitting}>로그인</button>
      </form>
    </main>
  );
}
```

## 4) 회원가입 페이지

`src/app/(auth)/signup/page.tsx`
```tsx
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { signupSchema, type SignupForm } from '@/lib/validators/auth';

export default function SignupPage() {
  const router = useRouter();
  const [serverError, setServerError] = useState('');

  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<SignupForm>({
    resolver: zodResolver(signupSchema)
  });

  const onSubmit = async (values: SignupForm) => {
    setServerError('');
    const res = await fetch('/api/auth/signup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(values)
    });

    if (!res.ok) {
      setServerError('회원가입에 실패했습니다. 이미 사용 중인 이메일일 수 있습니다.');
      return;
    }

    router.push('/login');
  };

  return (
    <main style={{ padding: 24, maxWidth: 420 }}>
      <h1>회원가입</h1>
      <form onSubmit={handleSubmit(onSubmit)} style={{ display: 'grid', gap: 12 }}>
        <input placeholder="name" {...register('name')} />
        {errors.name && <p>{errors.name.message}</p>}

        <input placeholder="email" {...register('email')} />
        {errors.email && <p>{errors.email.message}</p>}

        <input type="password" placeholder="password" {...register('password')} />
        {errors.password && <p>{errors.password.message}</p>}

        {serverError && <p style={{ color: 'crimson' }}>{serverError}</p>}

        <button disabled={isSubmitting}>가입하기</button>
      </form>
    </main>
  );
}
```

## 과제

- 필수: 비밀번호 확인(confirm password) 필드 추가
- 도전: 폼 에러 메시지 컴포넌트 공통화
