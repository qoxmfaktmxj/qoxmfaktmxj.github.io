---
layout: post
title: "Next.js 데이터 페칭 패턴 비교: fetch, React Query, SWR 언제 뭘 쓸까"
date: 2026-03-19 10:00:00 +0900
categories: [nextjs]
tags: [study, nextjs, data-fetching, react-query, swr, server-component, cache]
---

## 선택지 정리

Next.js App Router에서 데이터 페칭 방법은 크게 세 가지로 나뉜다.

| 방법 | 실행 위치 | 캐시 | 실시간성 |
|---|---|---|---|
| `fetch` (Server Component) | 서버 | Next.js 내장 | 낮음 |
| SWR | 클라이언트 | 메모리 | 높음 |
| React Query (TanStack Query) | 클라이언트 | 메모리/영속 | 높음 |

정답은 없다. **"얼마나 자주 바뀌는 데이터인가"** 와 **"누가 소비하는가"** 에 따라 달라진다.

## 1. 서버 컴포넌트 fetch — 정적·반정적 데이터

서버에서 직접 데이터를 가져와 렌더링한다. 초기 로딩이 빠르고 SEO에 유리하다.

```tsx
// app/products/page.tsx (Server Component)
export default async function ProductsPage() {
  const products = await fetch("https://api.example.com/products", {
    next: { revalidate: 60 }, // 60초 ISR
  }).then((r) => r.json());

  return (
    <ul>
      {products.map((p) => (
        <li key={p.id}>{p.name}</li>
      ))}
    </ul>
  );
}
```

**언제 쓰나:**
- 상품 목록, 블로그 포스트처럼 자주 바뀌지 않는 데이터
- SEO가 중요한 페이지
- 사용자별로 다르지 않은 공용 데이터

**주의:**
- 사용자 인터랙션 후 즉시 갱신이 필요하면 `revalidateTag`/`revalidatePath` 조합 필요
- 사용자별 데이터는 `cookies()`나 `headers()`로 요청 컨텍스트를 읽어야 함

## 2. SWR — 가볍고 빠른 클라이언트 페칭

Vercel이 만든 가벼운 훅. 설정이 적고 직관적이다.

```tsx
"use client";

import useSWR from "swr";

const fetcher = (url: string) => fetch(url).then((r) => r.json());

export function StockPrice({ ticker }: { ticker: string }) {
  const { data, error, isLoading } = useSWR(
    `/api/stock/${ticker}`,
    fetcher,
    { refreshInterval: 5000 } // 5초마다 폴링
  );

  if (isLoading) return <span>로딩 중...</span>;
  if (error) return <span>오류 발생</span>;

  return <span>{data.price.toLocaleString()}원</span>;
}
```

**언제 쓰나:**
- 실시간성이 중요한 소규모 데이터 (주가, 알림 수 등)
- 페이지 전환 없이 최신 상태 유지
- 의존성 최소화가 우선일 때

**SWR 핵심 옵션:**
- `refreshInterval` — 폴링 주기
- `revalidateOnFocus` — 탭 복귀 시 재검증 (기본값 true)
- `dedupingInterval` — 중복 요청 방지 시간

## 3. TanStack Query — 복잡한 서버 상태 관리

뮤테이션, 낙관적 업데이트, 무한 스크롤, 의존 쿼리 등 복잡한 케이스를 체계적으로 다룬다.

```tsx
// 설정: app/providers.tsx
"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient());
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
```

```tsx
// 사용: components/CommentList.tsx
"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

export function CommentList({ postId }: { postId: string }) {
  const queryClient = useQueryClient();

  const { data: comments } = useQuery({
    queryKey: ["comments", postId],
    queryFn: () => fetch(`/api/posts/${postId}/comments`).then((r) => r.json()),
  });

  const addComment = useMutation({
    mutationFn: (body: string) =>
      fetch(`/api/posts/${postId}/comments`, {
        method: "POST",
        body: JSON.stringify({ body }),
      }),
    onSuccess: () => {
      // 댓글 추가 후 목록 자동 갱신
      queryClient.invalidateQueries({ queryKey: ["comments", postId] });
    },
  });

  return (
    <div>
      {comments?.map((c) => <p key={c.id}>{c.body}</p>)}
      <button onClick={() => addComment.mutate("새 댓글")}>댓글 달기</button>
    </div>
  );
}
```

**언제 쓰나:**
- 뮤테이션 후 관련 쿼리를 일괄 무효화해야 할 때
- 무한 스크롤 (`useInfiniteQuery`)
- 쿼리 간 의존 관계가 복잡할 때
- 캐시를 여러 컴포넌트가 공유해야 할 때

## 패턴 선택 기준

```
데이터가 자주 바뀌나?
├── 아니오 → 서버 컴포넌트 fetch (ISR)
└── 예
    ├── 뮤테이션/복잡한 캐시 동기화 필요?
    │   ├── 예 → TanStack Query
    │   └── 아니오 → SWR
```

## 혼용 패턴 (권장)

실무에서는 둘 다 쓰는 경우가 많다.

```tsx
// Server Component에서 초기 데이터 페치
export default async function PostPage({ params }: { params: { id: string } }) {
  const initialComments = await fetch(`/api/posts/${params.id}/comments`).then(r => r.json());

  // Client Component에 초기값 전달 → hydration
  return <CommentSection postId={params.id} initialData={initialComments} />;
}
```

초기 렌더링은 서버에서, 이후 갱신은 클라이언트 훅으로 처리한다.

## 오늘의 적용 체크리스트

- [ ] 페이지별 데이터 페칭 방법 현황 파악
- [ ] 정적 데이터는 서버 컴포넌트 + ISR로 전환
- [ ] 실시간 데이터는 SWR 폴링 주기 적절하게 설정
- [ ] 복잡한 뮤테이션 흐름은 TanStack Query `invalidateQueries` 패턴으로 정리
- [ ] 서버 fetch 초기값 → 클라이언트 훅 hydration 패턴 적용 검토
