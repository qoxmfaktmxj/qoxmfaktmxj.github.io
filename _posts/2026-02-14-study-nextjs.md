---
layout: post
title: "Next.js 서버 컴포넌트(Server Components) 완벽 가이드"
date: 2026-02-14 21:24:38 +0900
categories: [nextjs]
tags: [study, nextjs, react, frontend, automation]
---

# Next.js 서버 컴포넌트 마스터하기

## 왜 이것이 중요한가?

실무 프로젝트에서 성능과 보안은 필수입니다. Next.js 13+ 서버 컴포넌트는 번들 크기를 줄이고, 민감한 데이터를 안전하게 처리하며, 데이터베이스 쿼리를 직접 실행할 수 있게 해줍니다. 이를 모르면 불필요한 클라이언트 자바스크립트를 배포하게 되어 성능 저하로 이어집니다.

## 핵심 개념 5가지

- **서버 컴포넌트(Server Component)**: 기본값으로 서버에서만 렌더링되며, 클라이언트 번들에 포함되지 않음
- **클라이언트 컴포넌트('use client')**: 상호작용이 필요한 컴포넌트는 명시적으로 선언해야 함
- **데이터 페칭**: 서버 컴포넌트에서 async/await로 직접 DB 접근 가능
- **캐싱 전략**: fetch 기본값은 'force-cache', revalidatePath()로 재검증
- **컴포넌트 경계**: 서버와 클라이언트 컴포넌트의 명확한 분리가 성능의 핵심

## 실습 예제

### 1. 서버 컴포넌트에서 데이터 페칭

    // app/posts/page.tsx (서버 컴포넌트 - 'use client' 없음)
    async function PostsList() {
      const posts = await fetch('https://api.example.com/posts', {
        next: { revalidate: 3600 } // 1시간마다 재검증
      }).then(res => res.json());

      return (
        <div>
          {posts.map(post => (
            <article key={post.id}>
              <h2>{post.title}</h2>
              <p>{post.content}</p>
            </article>
          ))}
        </div>
      );
    }

    export default PostsList;

### 2. 클라이언트 컴포넌트로 상호작용 추가

    // app/components/LikeButton.tsx
    'use client';

    import { useState } from 'react';

    export function LikeButton({ postId }: { postId: string }) {
      const [likes, setLikes] = useState(0);

      const handleLike = async () => {
        setLikes(prev => prev + 1);
        // 서버 액션 호출
        await fetch(`/api/posts/${postId}/like`, { method: 'POST' });
      };

      return <button onClick={handleLike}>👍 {likes}</button>;
    }

### 3. 서버 액션으로 데이터 변경

    // app/actions.ts
    'use server';

    import { revalidatePath } from 'next/cache';

    export async function createPost(formData: FormData) {
      const title = formData.get('title');
      const content = formData.get('content');

      // DB에 저장
      await db.posts.create({ title, content });

      // 캐시 재검증
      revalidatePath('/posts');
    }

## 흔한 실수 3가지

### 1. 모든 컴포넌트에 'use client' 붙이기
**문제**: 번들 크기가 증가하고 성능이 저하됨
**해결**: 상호작용이 필요한 컴포넌트만 'use client' 사용

### 2. 서버 컴포넌트에서 useState/useEffect 사용
**문제**: 서버에서 실행되므로 런타임 에러 발생
**해결**: 상태 관리가 필요하면 클라이언트 컴포넌트로 분리

### 3. 민감한 API 키를 클라이언트에 노출
**문제**: 보안 위험
**해결**: 서버 컴포넌트나 서버 액션에서만 사용

## 오늘의 실습 체크리스트

- [ ] 기존 프로젝트에서 불필요한 'use client' 제거하기
- [ ] 서버 컴포넌트에서 데이터 페칭 구현하기
- [ ] 클라이언트 컴포넌트 하나 만들어 상호작용 추가하기
- [ ] 서버 액션으로 폼 제출 처리하기
- [ ] revalidatePath() 또는 revalidateTag()로 캐시 관리하기
- [ ] 브라우저 DevTools에서 번들 크기 확인하기
- [ ] 팀원과 서버/클라이언트 컴포넌트 분리 전략 논의하기

**팁**: Next.js 공식 문서의 'Server and Client Components' 섹션을 읽으면 더 깊이 있는 이해가 가능합니다.
