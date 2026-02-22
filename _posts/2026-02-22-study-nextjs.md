---
layout: post
title: "Next.js 서버 컴포넌트(Server Components) 마스터하기"
date: 2026-02-22 10:07:32 +0900
categories: [nextjs]
tags: [study, nextjs, react, frontend, automation]
---

## 왜 이 주제가 중요한가?

Next.js 13+ 버전에서 도입된 서버 컴포넌트는 현대적인 웹 개발의 핵심입니다.

실제 프로젝트에서 서버 컴포넌트를 제대로 이해하면 번들 크기를 줄이고, 데이터베이스에 직접 접근하며, 보안을 강화할 수 있습니다.

클라이언트 컴포넌트와의 경계를 명확히 하지 못하면 성능 저하와 예상치 못한 버그가 발생합니다.

## 핵심 개념

- **서버 컴포넌트의 기본 원리**
  기본적으로 모든 컴포넌트는 서버에서 렌더링됩니다. 클라이언트 상호작용이 필요할 때만 'use client' 지시어를 사용합니다.

- **클라이언트 컴포넌트와의 차이**
  서버 컴포넌트는 상태(state)와 이벤트 리스너를 사용할 수 없습니다. 클라이언트 컴포넌트는 반대로 데이터베이스 접근이 불가능합니다.

- **데이터 페칭 패턴**
  서버 컴포넌트에서 직접 데이터베이스나 API를 호출할 수 있습니다. 이는 N+1 쿼리 문제를 줄이고 성능을 향상시킵니다.

- **Props 전달과 직렬화**
  서버 컴포넌트에서 클라이언트 컴포넌트로 전달하는 props는 JSON 직렬화 가능해야 합니다. 함수나 Date 객체는 직접 전달할 수 없습니다.

- **레이아웃과 중첩 구조**
  서버 컴포넌트 내에 클라이언트 컴포넌트를 중첩할 수 있습니다. 이를 통해 필요한 부분만 클라이언트에서 렌더링합니다.

## 실습 예제

### 예제 1: 기본 서버 컴포넌트

```typescript
// app/posts/page.tsx (자동으로 서버 컴포넌트)
export default async function PostsPage() {
  const posts = await fetch('https://api.example.com/posts')
    .then(res => res.json());

  return (
    <div>
      <h1>블로그 포스트</h1>
      <ul>
        {posts.map(post => (
          <li key={post.id}>{post.title}</li>
        ))}
      </ul>
    </div>
  );
}
```

이 컴포넌트는 서버에서만 실행되므로 API 키를 노출할 걱정이 없습니다.

### 예제 2: 클라이언트 컴포넌트 분리

```typescript
// app/components/LikeButton.tsx
'use client';

import { useState } from 'react';

export function LikeButton({ postId }: { postId: string }) {
  const [likes, setLikes] = useState(0);

  const handleLike = async () => {
    setLikes(likes + 1);
    await fetch(`/api/posts/${postId}/like`, { method: 'POST' });
  };

  return <button onClick={handleLike}>좋아요 {likes}</button>;
}
```

이 컴포넌트는 상호작용이 필요하므로 'use client'로 표시합니다.

### 예제 3: 서버와 클라이언트 조합

```typescript
// app/posts/[id]/page.tsx
import { LikeButton } from '@/app/components/LikeButton';

export default async function PostDetail({ params }: { params: { id: string } }) {
  const post = await fetch(`https://api.example.com/posts/${params.id}`)
    .then(res => res.json());

  return (
    <article>
      <h1>{post.title}</h1>
      <p>{post.content}</p>
      <LikeButton postId={params.id} />
    </article>
  );
}
```

서버 컴포넌트에서 데이터를 가져온 후 클라이언트 컴포넌트에 props로 전달합니다.

## 흔한 실수

- **'use client'를 최상위에 추가하기**
  전체 페이지를 클라이언트 컴포넌트로 만들면 서버 컴포넌트의 이점을 잃습니다. 상호작용이 필요한 작은 컴포넌트만 'use client'로 표시하세요.

- **서버 컴포넌트에서 상태 사용하기**
  useState나 useEffect는 클라이언트 컴포넌트에서만 사용 가능합니다. 서버 컴포넌트에서 사용하면 런타임 에러가 발생합니다.

- **직렬화 불가능한 객체를 props로 전달하기**
  Date, Map, Set, 함수 등은 JSON으로 변환할 수 없습니다. 필요하면 문자열로 변환하거나 클라이언트에서 생성하세요.

- **과도한 데이터 페칭**
  서버 컴포넌트에서 여러 번 데이터를 가져오면 요청이 중복될 수 있습니다. React의 자동 요청 중복 제거를 활용하되, 필요하면 캐싱을 고려하세요.

- **클라이언트 전용 라이브러리를 서버 컴포넌트에서 사용하기**
  브라우저 API(localStorage, window 등)는 서버에서 실행되지 않습니다. 이런 라이브러리는 클라이언트 컴포넌트에만 사용하세요.

## 오늘의 실습 체크리스트

- [ ] 기존 프로젝트에서 'use client'가 없는 컴포넌트 3개 찾기
- [ ] 그 컴포넌트들이 정말 클라이언트 기능이 필요한지 검토하기
- [ ] 서버 컴포넌트에서 직접 데이터베이스 쿼리 작성해보기
- [ ] 클라이언트 컴포넌트로 분리할 부분 식별하고 리팩토링하기
- [ ] 'use client' 경계를 최소화하도록 컴포넌트 구조 개선하기
- [ ] 번들 크기 변화를 next/bundle-analyzer로 측정해보기
