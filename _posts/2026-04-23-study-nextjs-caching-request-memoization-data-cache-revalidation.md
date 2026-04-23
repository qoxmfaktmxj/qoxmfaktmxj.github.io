---
layout: post
title: "Next.js 캐싱 실전: Request Memoization, Data Cache, revalidateTag, unstable_cache를 운영 기준으로 설계하는 법"
date: 2026-04-23 11:40:00 +0900
categories: [nextjs]
tags: [study, nextjs, caching, request-memoization, data-cache, full-route-cache, router-cache, revalidateTag, revalidatePath, unstable_cache, app-router]
permalink: /nextjs/2026/04/23/study-nextjs-caching-request-memoization-data-cache-revalidation.html
---

## 배경: Next.js에서 캐시는 성능 옵션이 아니라 데이터 신뢰도와 장애 반경을 결정하는 운영 설계다

App Router로 서비스를 만들다 보면 캐시는 처음에는 꽤 단순해 보인다.

- 조회 API에는 `fetch`를 쓴다
- 자주 바뀌지 않으면 `revalidate: 60` 정도를 붙인다
- 수정 후에는 `revalidatePath()`를 한 번 호출한다
- 정말 최신이어야 하는 화면은 `cache: "no-store"`로 돌린다

초기 데모에서는 이 정도만으로도 잘 굴러간다. 그런데 서비스가 커지고 페이지 수, 테넌트 수, 쓰기 트래픽이 늘어나면 곧 이상한 현상이 생긴다.

- 상세 화면은 수정됐는데 목록은 예전 값이 계속 보인다
- 어떤 경로는 즉시 반영되는데 어떤 경로는 몇 분씩 늦다
- 동일한 데이터를 한 요청 안에서 여러 번 읽어 DB 비용이 늘어난다
- `revalidatePath("/")` 같은 넓은 무효화가 붙어 배포 후 캐시가 자주 날아간다
- 사용자별 대시보드를 무심코 캐시해 다른 사용자 정보가 섞일 위험이 생긴다
- 태그 설계가 없어 특정 엔티티 하나 수정해도 관련 없는 페이지까지 광범위하게 재생성된다
- 반대로 태그를 너무 세분화해 운영자가 무엇을 무효화해야 하는지 알 수 없게 된다
- 외부 API와 DB 조회, 서버 액션, 라우트 캐시가 각자 다른 기준으로 움직여서 디버깅이 어려워진다

이 문제의 핵심은 문법이 아니다. **Next.js에는 캐시가 하나만 있는 것이 아니라 서로 다른 수명과 책임을 가진 캐시 계층이 여러 개 존재한다는 점**이다.

실무에서 꼭 구분해야 하는 축은 최소한 네 가지다.

1. 같은 렌더 안에서 중복 호출을 줄이는 요청 단위 중복 제거
2. 요청을 넘어 데이터를 재사용하는 서버 측 데이터 캐시
3. 렌더 결과 자체를 재사용하는 라우트 캐시
4. 브라우저 이동 경험을 빠르게 만드는 클라이언트 라우터 캐시

즉 Next.js 캐싱은 "캐시를 쓸까 말까"의 문제가 아니라 아래 질문에 답하는 설계 문제다.

- **무엇을 캐시할 것인가**: 원시 데이터, 가공된 데이터, 최종 렌더 결과 중 무엇인가
- **어디까지 공유할 것인가**: 요청 내부, 사용자 간, 테넌트 내부, 전역 중 어디까지인가
- **언제 버릴 것인가**: 시간 기반인가, 이벤트 기반인가, 수동 운영인가
- **어떻게 복구할 것인가**: 캐시 미스나 스탬피드 시 DB와 외부 API를 보호할 장치가 있는가

이 글의 목표는 하나다.

> **Next.js 캐싱을 `fetch` 옵션 몇 개 외우는 수준이 아니라, 데이터 일관성, 비용, 장애 반경을 함께 통제하는 운영 설계로 이해하는 것**

중급 이상 개발자를 기준으로, 배경, 핵심 개념, 실무 예시, 트레이드오프, 흔한 실수, 체크리스트, 한 줄 정리까지 한 번에 정리한다.

---

## 먼저 큰 그림: Next.js 캐시는 "한 덩어리 기능"이 아니라 서로 다른 계층의 조합이다

캐시가 꼬이는 팀은 대개 모든 현상을 하나의 캐시로 설명하려고 한다. 하지만 App Router 기준으로는 보통 아래 네 층을 분리해서 생각해야 한다.

### 1) Request Memoization

같은 서버 렌더 흐름 안에서 동일한 `fetch(GET/HEAD)` 호출을 중복 실행하지 않도록 줄이는 계층이다.

- 범위: **한 번의 렌더 요청 내부**
- 목적: 같은 데이터에 대한 중복 네트워크 호출 제거
- 특징: 요청이 끝나면 사라진다

### 2) Data Cache

`fetch` 결과나 캐시 가능한 데이터 소스를 요청 간에도 재사용하는 서버 측 캐시다.

- 범위: **여러 요청 간 공유 가능**
- 목적: 원본 데이터 조회 비용 절감
- 특징: `revalidate`, `tags` 같은 정책이 중요하다

### 3) Full Route Cache

정적 렌더 결과, 즉 RSC payload와 HTML 같은 **페이지 결과물**을 재사용하는 계층이다.

- 범위: 경로 단위
- 목적: 페이지 생성 비용 절감, 빠른 응답
- 특징: 데이터 캐시 정책과 연결돼 있다

### 4) Router Cache

브라우저가 세그먼트 단위로 RSC payload를 재사용해 클라이언트 내비게이션을 빠르게 만드는 계층이다.

- 범위: 브라우저 세션 내부
- 목적: 뒤로 가기, 탭 이동, 인앱 내비게이션 최적화
- 특징: 서버에서 캐시를 무효화해도 클라이언트 체감이 즉시 같지 않을 수 있다

실무에서 중요한 포인트는 이 네 계층이 **서로 독립적이면서도 연결돼 있다**는 점이다.

예를 들어 상세 페이지가 수정 후에도 옛값을 보여주는 원인은 하나가 아닐 수 있다.

- 서버의 Data Cache가 안 지워졌을 수도 있고
- Full Route Cache가 남아 있을 수도 있고
- 사용자의 브라우저 Router Cache가 이전 RSC payload를 재사용하고 있을 수도 있다

그래서 디버깅 질문도 바뀌어야 한다.

- "왜 안 바뀌지?"가 아니라
- **"어느 계층의 캐시가 아직 살아 있지?"** 를 먼저 물어야 한다.

---

## 핵심 개념 1: Request Memoization은 성능 최적화이지만, 데이터 일관성 도구로 오해하면 안 된다

App Router에서 서버 컴포넌트를 쓰다 보면 같은 렌더 안에서 동일 데이터를 여러 번 필요로 할 때가 많다.

- 상단 헤더에서 현재 사용자 조회
- 본문에서 같은 사용자 조직 정보 조회
- 사이드바에서 권한 정보 조회
- 메타데이터 생성과 본문 렌더에서 같은 리소스 조회

이때 동일한 `fetch`를 여러 번 써도 한 요청 안에서는 중복 실행이 줄어들 수 있다. 이것이 Request Memoization이다.

```tsx
async function getProject(projectId: string) {
  const res = await fetch(`https://api.example.com/projects/${projectId}`);
  if (!res.ok) throw new Error("failed to fetch project");
  return res.json();
}

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const project = await getProject(id);
  return { title: project.name };
}

export default async function ProjectPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const project = await getProject(id);
  return <h1>{project.name}</h1>;
}
```

이 구조는 중복 호출 비용을 줄이는 데 유리하다. 하지만 여기서 많은 팀이 바로 첫 번째 착각을 한다.

> **Memoization은 요청 내부 dedupe일 뿐, 요청 간 최신성 보장을 해주지 않는다.**

즉 아래 문제는 해결하지 못한다.

- 수정 직후 다음 요청에서 최신 데이터가 안 보이는 문제
- 여러 페이지가 같은 엔티티를 다르게 갱신하는 문제
- 운영자가 특정 상품 하나만 선택적으로 무효화하고 싶은 문제

### 언제 특히 유용한가

- `generateMetadata`와 페이지 본문이 같은 데이터를 읽을 때
- 레이아웃, 페이지, 중첩 서버 컴포넌트가 동일 API를 바라볼 때
- 하나의 렌더 트리에서 중복 호출이 생기기 쉬운 BFF 구조일 때

### 언제 한계를 보이나

- DB 직접 조회 함수처럼 `fetch`가 아닌 데이터 소스일 때
- 요청 간 재사용이 필요할 때
- 외부 API 비용이 커서 서버 수준 캐시가 필요한데 memoization만 기대할 때

실무 기준은 단순하다.

- Request Memoization은 **기본적인 중복 제거**로 이해한다
- 운영 캐시 전략은 Data Cache, `unstable_cache`, 태그 설계에서 해결한다

---

## 핵심 개념 2: Data Cache는 "얼마나 자주 바뀌는가"보다 "누구에게 공유해도 안전한가"부터 따져야 한다

많은 팀이 캐시 판단을 TTL부터 시작한다.

- 재고는 30초
- 가격은 5분
- 공지사항은 1시간

이 접근이 완전히 틀린 것은 아니지만, 실무에서 더 먼저 봐야 하는 질문은 이것이다.

> **이 데이터를 여러 요청과 여러 사용자 사이에서 공유해도 안전한가?**

예를 들어 아래 데이터는 성격이 다르다.

### 전역 공유에 적합한 데이터

- 공개 상품 목록
- 기술 문서 본문
- 카테고리 메타데이터
- 공개 블로그 포스트

### 조건부 공유 데이터

- 조직 단위 대시보드 집계
- 프로젝트 설정값
- 테넌트별 피처 플래그
- 지역/언어별 콘텐츠 목록

### 공유하면 위험한 데이터

- 현재 로그인 사용자 프로필
- 장바구니, 알림, 개인 추천
- 권한에 따라 필드가 달라지는 응답
- 쿠키, 헤더, 세션 상태에 따라 결과가 달라지는 데이터

캐시 사고의 상당수는 TTL 값이 아니라 **공유 범위를 잘못 잡아서** 생긴다.

### 안전한 기준

1. 결과가 사용자/세션에 따라 달라지는가
2. 접근 권한에 따라 일부 필드가 숨겨지는가
3. 쿠키, Authorization 헤더, 실험군 배정에 영향을 받는가
4. 특정 테넌트 바깥에 노출되면 사고가 되는가

이 질문 중 하나라도 강하게 걸리면 우선 `no-store` 또는 더 좁은 범위 캐시를 먼저 검토하는 편이 안전하다.

```tsx
async function getViewer() {
  const res = await fetch("https://api.example.com/me", {
    cache: "no-store",
    headers: {
      Authorization: `Bearer ${process.env.INTERNAL_TOKEN!}`,
    },
  });

  if (!res.ok) throw new Error("failed to fetch viewer");
  return res.json();
}
```

반대로 공개 데이터라면 명시적으로 캐시 정책을 주는 편이 훨씬 안정적이다.

```tsx
async function getPublicDocs() {
  const res = await fetch("https://api.example.com/docs", {
    next: {
      revalidate: 3600,
      tags: ["docs"],
    },
  });

  if (!res.ok) throw new Error("failed to fetch docs");
  return res.json();
}
```

핵심은 "캐시해도 되나"를 최신성보다 먼저 판단하는 것이다. 최신성은 무효화 전략으로 줄일 수 있지만, **잘못 공유된 데이터 노출은 한 번 터지면 신뢰를 크게 잃는다.**

---

## 핵심 개념 3: 태그 설계가 없으면 `revalidateTag`는 편한 API가 아니라 운영 리스크가 된다

App Router에서 on-demand revalidation을 제대로 쓰려면 `revalidatePath`만으로는 곧 한계가 온다. 이유는 페이지가 데이터를 여러 경로에서 공유하기 때문이다.

예를 들어 상품 하나가 아래 화면에 동시에 나타날 수 있다.

- 상품 상세 `/products/[id]`
- 카테고리 목록 `/categories/[slug]`
- 메인 추천 섹션 `/`
- 관리자 검수 목록 `/admin/products`
- 검색 결과 `/search?q=...`

이때 상세 화면만 재검증하면 나머지 화면에는 구 데이터가 남는다. 그래서 태그 기반 무효화가 중요해진다. 다만 태그는 막 붙이면 안 된다.

### 나쁜 태그 설계

- 모든 데이터를 `"all"` 같은 태그 하나로 묶기
- 반대로 태그를 지나치게 세분화해 호출 규칙을 아무도 모르게 만들기
- 엔티티, 목록, 집계, 파생 데이터를 구분하지 않기
- 테넌트 경계가 필요한데 전역 태그만 사용하기

### 운영 가능한 태그 설계 예시

상품 도메인이라면 보통 아래 정도의 계층이 실용적이다.

- `products`
- `product:{id}`
- `product-list`
- `product-list:category:{slug}`
- `tenant:{tenantId}:products`
- `tenant:{tenantId}:product:{id}`

중요한 점은 태그가 곧 운영 언어가 된다는 것이다. 운영자나 개발자가 "이 변경은 어느 데이터를 더럽히는가"를 말로 설명할 수 있어야 한다.

### 실무 예시: 상품 조회와 수정

```tsx
// lib/products.ts
export async function getProduct(productId: string) {
  const res = await fetch(`https://api.example.com/products/${productId}`, {
    next: {
      revalidate: 900,
      tags: ["products", `product:${productId}`],
    },
  });

  if (!res.ok) throw new Error("failed to fetch product");
  return res.json();
}

export async function getCategoryProducts(categorySlug: string) {
  const res = await fetch(`https://api.example.com/categories/${categorySlug}/products`, {
    next: {
      revalidate: 300,
      tags: ["products", "product-list", `product-list:category:${categorySlug}`],
    },
  });

  if (!res.ok) throw new Error("failed to fetch category products");
  return res.json();
}
```

수정 액션에서는 이렇게 간다.

```tsx
// app/admin/products/[id]/actions.ts
"use server";

import { revalidatePath, revalidateTag } from "next/cache";

export async function updateProduct(input: {
  id: string;
  categorySlug: string;
  name: string;
  price: number;
}) {
  const res = await fetch(`https://api.example.com/admin/products/${input.id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });

  if (!res.ok) {
    throw new Error("failed to update product");
  }

  revalidateTag(`product:${input.id}`);
  revalidateTag(`product-list:category:${input.categorySlug}`);
  revalidateTag("product-list");
  revalidatePath(`/products/${input.id}`);
}
```

여기서 핵심은 역할 분리다.

- **태그**는 같은 데이터를 여러 경로에서 공유하는 문제를 푼다
- **경로 무효화**는 특정 라우트 결과물을 빠르게 재생성하게 돕는다

둘 중 하나만 쓰는 팀보다, 데이터 축과 라우트 축을 분리해 쓰는 팀이 훨씬 디버깅이 쉽다.

---

## 핵심 개념 4: `revalidatePath`와 `revalidateTag`는 대체재가 아니라 적용 축이 다르다

실무에서 자주 나오는 질문이 있다.

> 수정 후엔 `revalidatePath`만 쓰면 되나요, 아니면 `revalidateTag`가 더 좋은가요?

정답은 보통 "둘 다 필요할 수 있다"다.

### `revalidatePath`

- 라우트 단위 무효화에 적합하다
- 어떤 URL이 다시 렌더돼야 하는지 분명할 때 좋다
- 경로가 명확한 상세, 대시보드, 특정 목록 페이지에 유리하다

### `revalidateTag`

- 같은 데이터가 여러 경로에서 재사용될 때 좋다
- 경로를 일일이 나열하기 어려운 공유 데이터 모델에 유리하다
- API, 페이지, 레이아웃, 서로 다른 경로가 동일 데이터에 기대는 구조에서 특히 중요하다

### 둘을 같이 쓰는 기준

#### 상세 수정

- `revalidateTag("product:123")`
- `revalidatePath("/products/123")`

#### 카테고리 이름 변경

- `revalidateTag("category:backend")`
- `revalidateTag("product-list:category:backend")`
- 카테고리 랜딩 페이지 경로도 필요하면 `revalidatePath("/categories/backend")`

#### 공지 배너 토글

- 여러 페이지 상단 레이아웃에서 공통 사용한다면 태그 중심 접근이 더 낫다
- 특정 경로만 다시 렌더해야 한다면 경로 무효화를 추가한다

실무에서 흔한 실패는 아래 둘 중 하나다.

1. 모든 변경에 `revalidatePath("/")` 같은 넓은 경로 무효화만 쓴다  
2. 태그만 무수히 늘려놓고 어느 액션이 어떤 태그를 지워야 하는지 문서화하지 않는다

좋은 기준은 이렇다.

- 경로가 명확하면 path를 쓴다
- 공유 데이터면 tag를 쓴다
- 둘이 겹치면 둘 다 쓰되, **왜 둘 다 필요한지 설명 가능한 수준으로만** 쓴다

---

## 핵심 개념 5: `unstable_cache`는 DB 조회와 계산 결과를 Next.js 캐시 모델에 편입시키는 도구다

Request Memoization과 `fetch` 캐시만으로는 부족한 경우가 많다. 특히 다음 같은 상황이다.

- 외부 HTTP가 아니라 DB 직접 조회를 한다
- 여러 쿼리를 합쳐 집계 결과를 만든다
- 동일 계산이 비싸서 요청 간 재사용이 필요하다
- 태그 기반 무효화와 같은 운영 모델을 맞추고 싶다

이럴 때 `unstable_cache`가 유용하다.

```tsx
// lib/dashboard.ts
import { unstable_cache } from "next/cache";
import { db } from "@/lib/db";

async function readTenantDashboard(tenantId: string) {
  const [openIncidents, activeDeployments, errorRate] = await Promise.all([
    db.incident.count({ where: { tenantId, status: "OPEN" } }),
    db.deployment.count({ where: { tenantId, status: "RUNNING" } }),
    db.metric.aggregate({
      _avg: { value: true },
      where: {
        tenantId,
        key: "error_rate_5m",
      },
    }),
  ]);

  return {
    openIncidents,
    activeDeployments,
    errorRate: errorRate._avg.value ?? 0,
  };
}

export const getTenantDashboard = (tenantId: string) =>
  unstable_cache(
    () => readTenantDashboard(tenantId),
    ["tenant-dashboard", tenantId],
    {
      revalidate: 60,
      tags: [`tenant:${tenantId}:dashboard`],
    }
  )();
```

이 패턴의 장점은 분명하다.

- DB 집계 비용을 요청 간 줄일 수 있다
- 태그 기반 무효화 규칙을 HTTP `fetch` 캐시와 비슷하게 맞출 수 있다
- 도메인 서비스 레이어 안에서 캐시 책임을 명시할 수 있다

하지만 여기서도 범위 설계가 중요하다.

### 특히 주의할 점

- 함수 인자가 결과에 영향을 주는데 키 설계에 반영하지 않으면 잘못된 공유가 생긴다
- 사용자 권한에 따라 다른 결과가 나오는데 테넌트 단위로만 캐시하면 정보가 섞일 수 있다
- 태그는 잘 붙였지만 실제 쓰기 경로에서 무효화를 호출하지 않으면 오래된 집계가 남는다

즉 `unstable_cache`는 "DB에도 캐시를 쉽게 붙이는 마법"이 아니라, **키 설계와 무효화 계약을 직접 책임져야 하는 저수준 도구**에 가깝다.

---

## 핵심 개념 6: Full Route Cache와 Data Cache를 분리해서 보지 않으면 "왜 저 페이지만 안 바뀌지?"가 반복된다

페이지 결과가 캐시된다는 사실을 잊으면, 데이터는 무효화했는데 여전히 예전 HTML이 보이는 상황을 이해하기 어렵다. 반대로 라우트 캐시만 보고 있으면 데이터 캐시 공유 문제를 놓친다.

### 생각해야 할 순서

1. 이 페이지가 정적으로 렌더될 수 있는가
2. 내부에서 사용하는 데이터가 캐시 가능한가
3. 수정 후 재생성 트리거가 무엇인가
4. 레이아웃, 페이지, 중첩 컴포넌트 중 어디가 공통 데이터에 기대는가

예를 들어 문서 사이트 홈은 정적 캐시에 잘 맞는다.

- 공개 데이터
- 변경 빈도 낮음
- 렌더 비용 큼
- SEO 중요

반면 운영자 대시보드는 이런 특성이 있을 수 있다.

- 테넌트별 데이터
- 1분 이내 최신성 필요
- 권한 차등 존재
- 쓰기 직후 즉시 반영 요구

이 둘을 같은 캐시 기준으로 다루면 문제가 생긴다.

### 안전한 실무 기준

- 공개 페이지는 Full Route Cache와 Data Cache를 적극 활용한다
- 사용자별/권한별 화면은 공유 캐시보다 최신성과 안전성을 우선한다
- 하나의 페이지 안에서도 공개 데이터와 개인 데이터를 분리할 수 있으면 분리한다

예를 들어 제품 랜딩은 캐시하되, 우상단의 개인 알림 수는 별도 동적 섬으로 분리하는 식이다. 모든 것을 한 페이지 정책으로 뭉치면 둘 다 어정쩡해진다.

---

## 실무 예시 1: CMS 기반 기술 블로그에서 공개 콘텐츠를 안정적으로 캐시하는 법

블로그나 문서 사이트는 Next.js 캐싱이 가장 잘 듣는 대표 사례다. 하지만 여기서도 운영 문제는 있다.

- 목록과 상세가 같은 글 데이터를 다르게 가져온다
- 태그 페이지, 카테고리 페이지, 홈 피드가 같은 글 집합을 공유한다
- 발행, 수정, 비공개 전환 시 여러 경로가 함께 갱신돼야 한다

### 추천 구조

#### 글 목록

```tsx
export async function getPosts() {
  const res = await fetch("https://cms.example.com/posts", {
    next: {
      revalidate: 600,
      tags: ["posts", "post-list"],
    },
  });

  if (!res.ok) throw new Error("failed to fetch posts");
  return res.json();
}
```

#### 글 상세

```tsx
export async function getPost(slug: string) {
  const res = await fetch(`https://cms.example.com/posts/${slug}`, {
    next: {
      revalidate: 600,
      tags: ["posts", `post:${slug}`],
    },
  });

  if (!res.ok) throw new Error("failed to fetch post");
  return res.json();
}
```

#### 발행 후 무효화

```tsx
"use server";

import { revalidatePath, revalidateTag } from "next/cache";

export async function publishPost(slug: string) {
  await fetch(`https://cms.example.com/admin/posts/${slug}/publish`, {
    method: "POST",
  });

  revalidateTag("post-list");
  revalidateTag(`post:${slug}`);
  revalidatePath("/");
  revalidatePath("/blog");
  revalidatePath(`/blog/${slug}`);
}
```

### 여기서 얻는 효과

- 홈 피드와 목록은 공유 태그로 함께 갱신 가능
- 상세는 개별 태그로 정밀 무효화 가능
- 경로 재생성도 같이 수행해 즉시 체감 반영 가능

### 여기서 많이 하는 실수

- 상세만 무효화하고 목록 태그를 잊는다
- slug 변경 시 옛 경로 무효화를 놓친다
- 비공개 전환인데 공개 목록 캐시를 안 지워 검색엔진에 한동안 남는다

블로그처럼 단순해 보이는 서비스도 결국은 데이터 축과 라우트 축을 같이 봐야 안정적이다.

---

## 실무 예시 2: SaaS 대시보드에서 테넌트별 집계와 사용자별 정보를 섞어 쓸 때

실무에서 더 어려운 쪽은 이 케이스다. 같은 화면 안에 아래 데이터가 섞여 있기 때문이다.

- 테넌트 전체 배포 수, 장애 수, 사용량 집계
- 현재 로그인 사용자의 알림, 즐겨찾기, 최근 본 항목
- 권한별로 다른 액션 버튼과 민감 정보

이때 전체 페이지를 `no-store`로 돌리면 안전하지만 비용이 커지고, 전체를 캐시하면 위험해진다.

### 추천 접근

#### 1) 공유 가능한 집계는 테넌트 단위 캐시

```tsx
const getUsageSummary = (tenantId: string) =>
  unstable_cache(
    async () => {
      return db.usageSummary.findFirstOrThrow({ where: { tenantId } });
    },
    ["usage-summary", tenantId],
    {
      revalidate: 120,
      tags: [`tenant:${tenantId}:usage-summary`],
    }
  )();
```

#### 2) 사용자별 정보는 캐시를 매우 신중히, 필요 시 no-store

```tsx
async function getMyNotifications() {
  const res = await fetch("https://api.example.com/me/notifications", {
    cache: "no-store",
  });

  if (!res.ok) throw new Error("failed to fetch notifications");
  return res.json();
}
```

#### 3) 쓰기 후에는 공유 데이터와 사용자 체감 경로를 같이 갱신

```tsx
"use server";

import { revalidatePath, revalidateTag } from "next/cache";

export async function acknowledgeIncident(input: {
  tenantId: string;
  incidentId: string;
}) {
  await db.incident.update({
    where: { id: input.incidentId },
    data: { acknowledgedAt: new Date() },
  });

  revalidateTag(`tenant:${input.tenantId}:dashboard`);
  revalidateTag(`tenant:${input.tenantId}:usage-summary`);
  revalidatePath(`/app/${input.tenantId}`);
}
```

### 왜 이 구조가 낫나

- 공유 가능한 데이터만 캐시해 비용을 줄인다
- 개인 데이터는 과도하게 공유되지 않는다
- 수정 직후 대시보드 체감 반영이 좋아진다

### 운영 포인트

테넌트 캐시와 사용자 캐시를 섞는 순간 사고 확률이 올라간다. 그래서 코드 리뷰 질문도 명확해야 한다.

- 이 함수 결과는 테넌트 내부 공유가 안전한가
- 사용자 권한에 따라 값이 달라지지 않는가
- 태그 이름에 테넌트 경계가 들어갔는가

---

## 실무 예시 3: 쓰기 폭주 구간에서 캐시 스탬피드와 무효화 폭발을 줄이는 법

많은 팀이 캐시를 도입한 뒤 오히려 쓰기 피크 시간에 장애를 겪는다. 이유는 두 가지다.

1. 같은 키가 한꺼번에 만료되며 원본 저장소로 요청이 몰린다
2. 하나의 쓰기 이벤트가 너무 많은 태그와 경로를 동시에 무효화한다

### 시나리오

이커머스 운영툴에서 가격 일괄 변경 배치를 돌린다고 해보자.

- 수천 개 상품이 5분 내 변경된다
- 각 상품은 상세, 카테고리, 추천 목록, 메인 피드에 반영된다
- 모든 변경마다 `revalidatePath`를 여러 번 때리면 재생성 폭발이 생긴다

### 실무 기준

#### 1) 태그 granularity를 도메인 단위로 조절한다

상품 1개 변경마다 홈 전체를 무효화할 필요가 없는지 먼저 본다. 반대로 메인 피드가 실제로 상품 집합에 강하게 묶여 있다면, 변경 이벤트를 모아 주기적으로 재검증하는 편이 낫다.

#### 2) 쓰기 경로에서 무효화를 직렬화 또는 배치화한다

동일 요청 내에서 중복 `revalidateTag("product-list")`를 수십 번 날리는 구조는 피한다. 이벤트 큐나 배치 워커에서 도메인별로 합치는 편이 낫다.

#### 3) 매우 비싼 집계는 짧은 TTL + 이벤트 무효화 혼합 전략을 쓴다

100% 즉시 일관성이 필요하지 않은 운영 지표라면 아래 구조가 현실적이다.

- 평소에는 `revalidate: 30` 또는 `60`
- 중요한 상태 변경 시에만 태그 무효화
- 읽기 부하가 큰 피크 시간에는 과도한 광역 path 무효화 금지

### 중요한 현실 인식

캐시는 읽기 비용을 줄여주지만, 무효화는 쓰기 비용을 올린다. 데이터 모델이 커질수록 이 균형이 더 중요해진다.

---

## 핵심 개념 7: Router Cache까지 고려해야 "서버에서는 갱신됐는데 브라우저에서는 왜 그대로지?"를 설명할 수 있다

서버 쪽 캐시만 이해하고 있으면 운영 중 자주 듣는 질문에 답하기 어렵다.

- "방금 수정했는데 새로고침하면 바뀌고, 링크 이동만 하면 안 바뀌어요"
- "관리자 화면에서 저장 후 돌아왔는데 목록이 그대로예요"
- "다른 사람은 최신인데 내 브라우저만 예전 상태예요"

이런 현상은 브라우저의 Router Cache가 얽혀 있을 가능성이 크다. App Router는 사용자 내비게이션 경험을 빠르게 만들기 위해 RSC payload를 세그먼트 단위로 재사용한다. 이건 UX에는 좋지만, 캐시 디버깅을 어렵게 만든다.

### 왜 중요하나

서버에서 `revalidateTag`나 `revalidatePath`를 호출했다고 해서, 이미 브라우저가 들고 있던 화면 조각이 즉시 사라지는 체감과 항상 일치하지는 않는다. 특히 아래 흐름에서 차이가 커진다.

- 목록 진입
- 상세 이동
- 수정 저장
- 브라우저 뒤로 가기 또는 클라이언트 라우팅으로 목록 복귀

이때 서버의 데이터는 이미 최신이어도, 사용자가 체감하는 목록은 이전 RSC payload를 잠시 재사용할 수 있다.

### 실무 대응 기준

#### 1) 쓰기 직후 돌아가는 핵심 경로는 서버 무효화만 믿지 않는다

예를 들어 관리자 수정 폼 저장 후 상세나 목록으로 돌아간다면 아래 중 하나를 고려한다.

- 저장 완료 후 대상 경로로 서버 리다이렉트
- 명시적 refresh 흐름 설계
- 낙관적 UI와 서버 재검증 결과를 함께 맞추기

#### 2) "새로고침하면 최신"이면 서버 캐시 문제인지 클라이언트 캐시 문제인지 분리해서 본다

- 새로고침 후에도 stale이면 서버 측 Data Cache 또는 Full Route Cache 문제일 가능성이 높다
- 새로고침하면 최신이면 Router Cache나 클라이언트 상태 동기화 문제일 수 있다

#### 3) 저장 후 UX를 설계할 때 목록/상세 체감 반영 시점을 요구사항으로 본다

많은 팀이 저장 API 성공 여부만 본다. 하지만 사용자는 저장 성공보다 "방금 바꾼 값이 내가 보는 화면에 언제 보이느냐"를 더 민감하게 느낀다. 따라서 캐시 설계는 백엔드 효율 문제가 아니라 **UX 일관성 계약**이기도 하다.

---

## 핵심 개념 8: 세그먼트 설정은 전역 스위치가 아니라, 데이터 정책을 보완하는 마지막 안전장치로 써야 한다

App Router에서는 페이지나 레이아웃 레벨에서 캐시 성격에 영향을 주는 설정들이 있다. 예를 들면 이런 축이다.

- 이 경로를 정적으로 다룰 것인가, 동적으로 다룰 것인가
- 기본 revalidate를 둘 것인가
- 하위 `fetch` 기본 정책을 어떻게 가져갈 것인가

이런 설정은 강력하다. 하지만 실무에서 자주 벌어지는 실수는 **세그먼트 설정으로 데이터 문제를 덮으려는 것**이다.

### 나쁜 접근

- 특정 데이터만 동적인데 페이지 전체를 강제로 동적으로 돌린다
- 원인 분석 없이 상위 레이아웃에 짧은 revalidate를 걸어 전체 트래픽에 비용을 퍼뜨린다
- 하위 읽기 함수가 제각각인데 상위에서 한 번에 해결하려 한다

### 더 나은 접근

1. 먼저 데이터 단위에서 공유 가능성과 무효화 규칙을 정한다  
2. 그래도 페이지 전체 성격이 분명하면 세그먼트 설정으로 보완한다  
3. 레이아웃처럼 영향 범위가 큰 곳에서는 특히 보수적으로 적용한다

예를 들어 운영자 화면 전체가 사용자별/권한별로 달라지고 즉시성이 중요하다면 해당 구간은 동적 성격을 강하게 가져갈 수 있다. 반면 공개 문서 레이아웃에 짧은 revalidate를 넣어 전체 문서 사이트를 불필요하게 자주 다시 만들 필요는 없다.

즉 세그먼트 설정은 첫 번째 도구가 아니라, **데이터 정책을 페이지 단위 현실에 맞게 고정하는 마지막 레버**에 가깝다.

---

## 실무 예시 4: 상품 상세 페이지에서 "자주 안 바뀌는 본문"과 "자주 바뀌는 가격/재고"를 분리하는 법

캐시 설계가 어려운 가장 대표적인 이유는 한 화면 안에 업데이트 속도가 다른 데이터가 섞여 있기 때문이다.

상품 상세를 생각해 보자.

- 상품명, 설명, 이미지, 스펙은 자주 안 바뀐다
- 가격은 프로모션 때 자주 바뀔 수 있다
- 재고는 더 자주 바뀔 수 있다
- 개인화 쿠폰, 최근 본 상품, 장바구니 상태는 사용자별이다

이 모든 것을 한 번에 `no-store`로 읽으면 안전하지만 비효율적이다. 반대로 전부 캐시하면 stale과 노출 위험이 커진다.

### 추천 분리 방식

#### 1) 공개 본문 데이터는 비교적 긴 캐시

```tsx
async function getProductContent(productId: string) {
  const res = await fetch(`https://api.example.com/products/${productId}/content`, {
    next: {
      revalidate: 3600,
      tags: [`product:${productId}:content`],
    },
  });

  if (!res.ok) throw new Error("failed to fetch product content");
  return res.json();
}
```

#### 2) 가격은 더 짧은 주기 또는 이벤트 무효화 병행

```tsx
async function getProductPrice(productId: string) {
  const res = await fetch(`https://api.example.com/products/${productId}/price`, {
    next: {
      revalidate: 30,
      tags: [`product:${productId}:price`],
    },
  });

  if (!res.ok) throw new Error("failed to fetch product price");
  return res.json();
}
```

#### 3) 재고나 개인화 데이터는 더 엄격히 관리

- 재고가 실제 주문 가능 여부와 직결된다면 더 짧은 캐시나 no-store 검토
- 쿠폰, 장바구니 상태는 사용자별이라면 공유 캐시 금지

### 이 구조가 주는 이점

- 비싼 상세 본문을 매번 다시 읽지 않아도 된다
- 가격 변경 시 본문 전체를 광범위하게 무효화하지 않아도 된다
- 사용자별 데이터 노출 위험을 낮출 수 있다

### 이 구조가 요구하는 팀 습관

- UI 컴포넌트도 데이터 신선도 단위에 맞춰 분리해야 한다
- "상세 페이지" 하나로 뭉뚱그리지 말고, 본문/가격/재고/개인화 모듈로 나눠 생각해야 한다
- PR 리뷰에서 "이 값은 어느 freshness domain에 속하나"를 물어야 한다

이 질문을 잘하는 팀은 캐시가 빨리 안정된다.

---

## 실무 예시 5: 관리자 백오피스에서 저장 직후 리스트와 집계를 모두 맞추는 법

백오피스는 캐시가 가장 헷갈리는 구간 중 하나다. 사용자는 저장 직후 아래 세 가지를 동시에 기대한다.

1. 방금 저장한 상세 값이 최신이어야 한다  
2. 목록으로 돌아가도 변경분이 보여야 한다  
3. 상단 통계 카드나 필터 집계도 맞아야 한다

문제는 이 세 가지가 보통 서로 다른 데이터 소스를 쓴다는 점이다.

- 상세: 엔티티 단건 조회
- 목록: 검색 조건이 포함된 리스트 조회
- 통계 카드: 집계 쿼리 또는 materialized summary

### 잘못된 구현 패턴

저장 후 상세 경로만 `revalidatePath` 한다. 그러면 상세는 맞아도 목록과 통계가 틀린다.

### 더 나은 구현 패턴

```tsx
"use server";

import { revalidatePath, revalidateTag } from "next/cache";

export async function updateMember(input: {
  tenantId: string;
  memberId: string;
  departmentId: string;
}) {
  await db.member.update({
    where: { id: input.memberId },
    data: { departmentId: input.departmentId },
  });

  revalidateTag(`tenant:${input.tenantId}:member:${input.memberId}`);
  revalidateTag(`tenant:${input.tenantId}:member-list`);
  revalidateTag(`tenant:${input.tenantId}:member-stats`);

  revalidatePath(`/admin/${input.tenantId}/members`);
  revalidatePath(`/admin/${input.tenantId}/members/${input.memberId}`);
}
```

### 핵심 교훈

저장 액션은 단건 데이터만 오염시키지 않는다. 실제로는 다음을 함께 오염시킨다.

- 엔티티 상세
- 엔티티를 포함하는 목록
- 필터/카운트/상태 집계
- 상위 대시보드 카드

따라서 백오피스에서 캐시 설계는 CRUD 구현이 아니라 **도메인 영향 반경 분석**에 가깝다.

---

## 디버깅 플레이북: stale data 이슈가 났을 때 확인 순서를 고정하자

캐시 문제는 감으로 접근하면 오래 끈다. 팀 공용 플레이북을 만들어 순서를 고정하는 편이 좋다.

### 1단계: 문제 데이터가 공유 가능한 데이터인지 먼저 분류한다

- 공개 데이터인가
- 테넌트 공유 데이터인가
- 사용자 전용 데이터인가

여기서 분류가 틀리면 나머지 분석도 틀린다.

### 2단계: stale이 서버 전체인지, 특정 브라우저 체감인지 본다

- 다른 브라우저, 시크릿 창, 새로고침에서도 stale인가
- 특정 탐색 흐름에서만 stale인가

이 단계에서 서버 캐시 문제와 Router Cache 문제를 빨리 나눌 수 있다.

### 3단계: 읽기 함수의 캐시 계약을 확인한다

- `fetch`에 `revalidate`, `tags`, `cache`가 무엇으로 설정돼 있는가
- `unstable_cache` 키와 태그는 무엇인가
- 메타데이터, 레이아웃, 페이지가 같은 함수를 공유하는가

### 4단계: 쓰기 후 무효화가 실제로 연결돼 있는지 본다

- 저장 액션에서 어떤 태그를 지우는가
- 어떤 경로를 재검증하는가
- 새로 추가된 목록/탭/집계가 무효화 범위에서 빠지지 않았는가

### 5단계: 태그 설계 자체가 과도하게 넓거나 좁지 않은지 본다

- 너무 넓어서 광역 stale와 재생성 폭발이 생기지 않는가
- 너무 좁아서 운영자가 빠뜨리기 쉬운 구조는 아닌가

### 6단계: 문제를 재현 가능한 사용자 행동 단위로 적는다

예를 들어 이렇게 적어야 한다.

1. 목록 진입  
2. 상세 이동  
3. 상태값 변경 후 저장  
4. 뒤로 가기  
5. 목록 카드의 상태가 30초간 예전 값 유지

이 정도로 적어야 Router Cache, 낙관적 업데이트, 서버 재검증 사이를 나눠서 볼 수 있다.

---

## 의사결정 매트릭스: 어떤 도구를 먼저 검토해야 하나

### 경우 1) 같은 렌더 안에서 API 중복 호출을 줄이고 싶다

- 먼저 볼 것: Request Memoization
- 기대 효과: 서버 렌더 내부 중복 제거
- 주의점: 요청 간 최신성 문제는 못 푼다

### 경우 2) 공개 데이터 조회 비용이 크고 여러 요청에서 재사용하고 싶다

- 먼저 볼 것: `fetch` 기반 Data Cache
- 기대 효과: 비용 절감, 정적 페이지 최적화
- 주의점: 태그와 revalidate 정책이 필요하다

### 경우 3) DB 직접 조회나 집계 결과를 재사용하고 싶다

- 먼저 볼 것: `unstable_cache`
- 기대 효과: 비HTTP 데이터도 Next.js 캐시 모델에 편입 가능
- 주의점: 키/태그/권한 경계를 직접 책임져야 한다

### 경우 4) 수정 직후 특정 URL을 즉시 최신으로 만들고 싶다

- 먼저 볼 것: `revalidatePath`
- 기대 효과: 사용자 체감 반영이 쉬움
- 주의점: 공유 데이터 전파까지는 부족할 수 있다

### 경우 5) 같은 데이터가 여러 경로에 퍼져 있다

- 먼저 볼 것: `revalidateTag`
- 기대 효과: 데이터 중심 전파가 쉬움
- 주의점: 태그 설계와 문서화가 필수다

### 경우 6) 사용자별 데이터가 섞여 있어 공유가 위험하다

- 먼저 볼 것: `no-store` 또는 더 좁은 범위 분리
- 기대 효과: 노출 사고 방지
- 주의점: 비용 상승을 감수하거나 구조 분리가 필요하다

이 매트릭스를 팀 위키에 붙여두면, 캐시 관련 코드 리뷰 속도가 꽤 빨라진다.

---

## 실무 예시 6: 외부 CMS 웹훅, 관리자 수정, 공개 사이트 반영이 동시에 얽힐 때

실제 운영에서는 데이터 변경이 하나의 경로에서만 일어나지 않는다. 예를 들어 마케팅 팀은 CMS에서 글을 수정하고, 개발팀은 관리자 백오피스에서 추천 배너를 바꾸고, 공개 사이트는 Next.js로 서빙할 수 있다. 이때 캐시 문제는 더 복잡해진다.

- 변경 이벤트가 외부 시스템에서 들어온다
- 내부 서버 액션이 아닌 웹훅으로 무효화해야 한다
- 공개 홈, 카테고리, 상세, 추천 위젯이 같은 콘텐츠를 다르게 소비한다

### 추천 방식

#### 1) 외부 변경 이벤트를 도메인 이벤트로 번역한다

웹훅 payload를 그대로 path 무효화에 연결하지 말고, 먼저 도메인 언어로 바꾸는 편이 낫다.

- 글 수정됨 → `post:{slug}` 오염
- 카테고리 변경됨 → `post-list`, `category:{slug}` 오염
- 배너 교체됨 → `homepage-hero`, `campaign:{id}` 오염

이 단계가 있어야 외부 시스템이 바뀌어도 Next.js 쪽 운영 언어는 유지된다.

#### 2) 웹훅 처리기는 path보다 tag를 중심으로 설계한다

외부 시스템은 어느 페이지에서 그 데이터를 쓰는지 항상 알기 어렵다. 반면 데이터 태그는 상대적으로 안정적이다.

```tsx
// app/api/webhooks/cms/route.ts
import { revalidatePath, revalidateTag } from "next/cache";

export async function POST(request: Request) {
  const payload = await request.json();

  if (payload.type === "post.updated") {
    revalidateTag(`post:${payload.slug}`);
    revalidateTag("post-list");
    revalidatePath(`/blog/${payload.slug}`);
    revalidatePath("/blog");
  }

  return Response.json({ ok: true });
}
```

#### 3) 웹훅이 중복 호출돼도 안전해야 한다

외부 시스템은 재시도, 중복 전달, 순서 뒤섞임이 흔하다. 따라서 캐시 무효화는 가능한 한 멱등적으로 설계하는 편이 좋다. 무효화 자체는 대개 멱등적이지만, 웹훅 처리 중 추가 DB 업데이트나 상태 기록을 한다면 별도 보호가 필요하다.

### 여기서 많이 놓치는 것

- 글 slug 변경 시 새 경로만 재검증하고 옛 경로를 놓침
- 배너처럼 레이아웃 공통 데이터인데 특정 상세 path만 재검증함
- 외부 CMS의 발행 상태와 공개 사이트의 캐시 정책이 달라 비공개가 늦게 반영됨

외부 웹훅이 끼는 순간, 캐시 설계는 앱 내부 최적화가 아니라 **시스템 간 계약 관리**가 된다.

---

## 운영 표준안: 팀에서 최소한 이 정도는 문서로 고정해두자

캐시 문제는 개별 개발자가 똑똑해서 해결하는 것보다, 팀 규칙이 있어서 덜 발생하게 만드는 편이 낫다. 작은 팀 기준으로도 아래 네 가지는 문서화할 가치가 있다.

### 1) 읽기 함수 표

예시:

- `getPost(slug)` → 공개 공유 가능, `tags: [post:{slug}, post-list]`, `revalidate: 600`
- `getTenantDashboard(tenantId)` → 테넌트 공유 가능, `tags: [tenant:{id}:dashboard]`, `revalidate: 60`
- `getViewer()` → 사용자 전용, `no-store`

이 표가 있으면 새 화면을 만들 때 매번 감으로 정하지 않아도 된다.

### 2) 쓰기 액션 표

예시:

- `publishPost(slug)` → `post:{slug}`, `post-list`, `/blog`, `/blog/{slug}`
- `updateProduct(id)` → `product:{id}`, `product-list`, `/products/{id}`
- `ackIncident(id)` → `tenant:{id}:dashboard`, `/app/{tenantId}`

이 표가 있으면 백오피스 기능 추가 시 어떤 무효화를 붙여야 하는지 훨씬 빨라진다.

### 3) 위험 데이터 분류 표

특히 아래는 전역 공유 캐시 금지 대상으로 명확히 적어두는 편이 좋다.

- 현재 사용자 정보
- 권한별 응답
- 개인화 추천
- 장바구니, 알림, 최근 본 항목
- 실험군에 따라 결과가 달라지는 응답

이 표가 없으면 언젠가 "이것도 그냥 60초 캐시해도 되지 않나요" 같은 위험한 리뷰가 나온다.

### 4) 디버깅 템플릿

stale 이슈가 생기면 아래 항목을 반드시 남기게 하면 좋다.

- 문제 데이터 종류: 공개/테넌트/개인
- 재현 경로: 새로고침 포함 여부, 뒤로 가기 포함 여부
- 관련 읽기 함수와 캐시 정책
- 관련 쓰기 액션과 무효화 대상
- 기대 최신성: 즉시/수초/수분 허용

이 정도만 있어도 캐시 이슈는 절반 이상 빨리 좁혀진다.

---

## 언제 캐시하지 않는 편이 더 나은가

좋은 캐시 설계는 캐시를 많이 쓰는 설계가 아니다. **캐시하지 않아야 할 곳을 정확히 아는 설계**다.

아래 조건이 강하면 우선 캐시보다 단순한 최신성 경로를 선택하는 편이 낫다.

### 1) 데이터 오노출 비용이 매우 크다

- 급여, 결제, 의료, 보안 권한 화면
- 사용자 간 데이터 혼입이 치명적인 경우

이런 화면은 약간 느려도 안전한 편이 낫다.

### 2) 조회 비용보다 stale 비용이 더 크다

예를 들어 주문 직후 결제 상태, 즉시 승인 여부, 운영 장애 현재 상태처럼 stale이 사용자 행동을 크게 왜곡하면 캐시 이득보다 손해가 더 클 수 있다.

### 3) 데이터 모델이 아직 자주 바뀐다

도메인 모델과 화면 구조가 빠르게 변하는 초기 단계에서는 정교한 태그 설계가 오히려 발목을 잡을 수 있다. 이때는 단순한 no-store나 짧은 TTL로 시작하고, 패턴이 안정된 뒤 태그 체계를 도입하는 편이 낫다.

### 4) 팀이 아직 무효화 계약을 운영할 준비가 안 됐다

캐시 자체보다 중요한 건 캐시를 이해하고 유지할 팀 습관이다. 읽기 함수 표도 없고, 쓰기 액션 표도 없고, stale 이슈 플레이북도 없다면 공격적인 캐시 도입은 나중에 더 비싸게 돌아올 수 있다.

즉 캐시는 성능 기능이 아니라 운영 기능이다. 운영할 준비가 덜 됐다면, 단순한 구조가 더 좋은 선택일 때가 많다.

---

## 트레이드오프 1: 최신성, 비용, 단순성은 동시에 최대화하기 어렵다

캐시 설계는 결국 세 가지 축 사이 균형이다.

### 1) 최신성 우선

- 장점: 수정 직후 사용자가 바로 최신 상태를 본다
- 단점: 원본 저장소 비용 증가, TTFB 증가, 스탬피드 위험 증가

### 2) 비용 우선

- 장점: DB, 외부 API, 렌더 비용 감소
- 단점: stale data 허용 폭을 설계해야 한다

### 3) 단순성 우선

- 장점: 개발자 온보딩과 운영 이해도가 높다
- 단점: 세밀한 최적화와 정밀 무효화가 어렵다

작은 팀에서 특히 중요한 건 **조금 덜 최적이어도 설명 가능한 구조**다. 예를 들어 아래 두 선택이 있다.

- 태그 40종류를 정교하게 설계한 초미세 무효화
- 태그 8종류와 몇 개의 핵심 path 무효화만 유지하는 구조

후자가 운영 이해도와 사고 방지 측면에서 더 나을 때가 많다.

---

## 트레이드오프 2: 경로 중심 설계는 직관적이지만, 공유 데이터가 많은 서비스에서는 금방 한계가 온다

`revalidatePath`만 쓰면 처음엔 쉽다.

- 어느 URL이 갱신돼야 하는지 눈에 보인다
- 코드 리뷰가 단순하다
- 디버깅도 직관적이다

하지만 데이터 재사용이 많아질수록 문제가 생긴다.

- 같은 엔티티를 소비하는 경로를 전부 찾기 어렵다
- 나중에 새 페이지가 추가되면 쓰기 로직도 계속 수정해야 한다
- 레이아웃, 병렬 라우트, 추천 섹션 같은 간접 소비 경로를 놓치기 쉽다

반대로 태그 중심 설계는 공유 데이터 문제에 강하지만, 설계 문서와 네이밍 규칙이 없으면 금방 블랙박스가 된다.

좋은 팀은 보통 이렇게 정리한다.

- **경로는 체감 반영용**
- **태그는 데이터 전파용**

이렇게 역할을 나누면 코드 읽기도 좋아지고, 무효화 원인 추적도 쉬워진다.

---

## 트레이드오프 3: 과감한 캐시는 빠르지만, 디버깅 가능성을 같이 설계하지 않으면 운영이 어려워진다

캐시 문제는 재현이 어렵다. 로컬에서는 최신인데 운영에서는 stale, 어떤 사용자만 오래된 값을 보고, 몇 분 뒤엔 자연히 사라진다. 그래서 성능보다 먼저 **관측성**을 붙여야 한다.

### 추천 관측 항목

- 캐시 키 또는 태그 네이밍 규칙 문서
- 주요 읽기 함수의 캐시 정책 표
- 쓰기 액션별 무효화 대상 표
- 수정 후 반영 지연 시간 측정
- 캐시 미스 급증 시 원본 저장소 부하 메트릭

### 실무 팁

- PR 템플릿에 "이 변경은 어떤 태그/path를 무효화해야 하나" 항목을 넣는다
- 운영자 도구에서 주요 엔티티 기준 재검증 액션을 제공한다
- 장애 대응 문서에 "이 화면 stale 시 어느 태그와 path를 먼저 확인할지"를 적는다

캐시를 많이 쓸수록, 코드만 잘 짜는 팀보다 **운영 언어를 잘 정리한 팀**이 훨씬 덜 아프다.

---

## 흔한 실수 1: `cache: "no-store"`를 만능 해결책으로 남발한다

stale data를 몇 번 겪고 나면 많은 팀이 그냥 전부 no-store로 돌린다. 단기적으로는 마음이 편하다. 하지만 장기적으로는 아래 문제가 생긴다.

- DB와 외부 API 비용 증가
- 트래픽 피크에서 응답 지연 증가
- 원래 캐시해도 안전한 공개 데이터까지 매번 재조회
- 페이지 전체가 동적 성격을 띠며 Full Route Cache 이점을 잃음

더 좋은 접근은 문제 화면 전체를 no-store로 바꾸기 전에, **정말 최신이어야 하는 데이터 조각이 무엇인지**를 좁히는 것이다.

---

## 흔한 실수 2: 사용자별 데이터를 태그 캐시에 섞어 공유한다

가장 위험한 실수다.

예를 들어 아래 코드는 보기엔 편하지만 위험하다.

```tsx
async function getDashboardData() {
  return fetch("https://api.example.com/dashboard", {
    next: { revalidate: 300, tags: ["dashboard"] },
  }).then((r) => r.json());
}
```

이 응답이 실제로는 사용자 권한, 조직, 실험군, 개인 알림 수에 따라 달라진다면, 전역 태그 캐시는 맞지 않는다. 이 문제는 "가끔 옛값이 보인다" 수준이 아니라 **데이터 노출 사고**로 이어질 수 있다.

---

## 흔한 실수 3: 쓰기 로직에서 무효화를 빼먹고 TTL에만 의존한다

`revalidate: 300`을 줬으니 5분 안에는 알아서 최신이 되겠지, 라고 생각하기 쉽다. 하지만 실무에서는 수정 직후 사용자의 기대가 더 중요하다.

- 관리자에서 상품 수정 후 바로 상세를 다시 본다
- 문서 발행 직후 링크를 공유한다
- 장애 상태를 ack한 뒤 대시보드를 즉시 확인한다

이때 5분 stale은 사용자 입장에서 버그다. 그래서 **사용자 액션 직후 경로/태그 무효화**는 별도로 설계해야 한다.

---

## 흔한 실수 4: 태그를 너무 넓거나 너무 좁게 잡는다

둘 다 문제다.

### 너무 넓은 경우

- `posts`
- `products`
- `dashboard`

장점은 단순하지만, 하나 수정할 때 전체가 흔들린다.

### 너무 좁은 경우

- `tenant:42:category:backend:page:7:sort:latest:card:compact`

이 정도로 가면 운영자가 무엇을 지워야 하는지 아무도 모른다.

좋은 기준은 **도메인 엔티티, 대표 목록, 테넌트 경계** 정도에서 멈추는 것이다. 그보다 미세한 뷰 상태까지 태그에 태우면 설계가 과도하게 복잡해진다.

---

## 흔한 실수 5: 메타데이터, 레이아웃, 페이지가 서로 다른 캐시 정책을 가져 데이터 정합성이 깨진다

이 문제는 조용히 오래 간다.

- 본문은 최신인데 `<title>`은 예전 제목이다
- 상세는 바뀌었는데 상단 breadcrumb는 예전 카테고리다
- 레이아웃의 조직 이름은 예전 값인데 본문 표는 최신이다

원인은 대부분 동일 엔티티를 서로 다른 소스 또는 다른 캐시 정책으로 읽기 때문이다. 특히 `generateMetadata`, 레이아웃 서버 컴포넌트, 페이지 본문이 같은 리소스를 바라볼 때 이 문제가 자주 생긴다.

해법은 단순하다.

- 같은 엔티티는 가능한 한 같은 읽기 함수에 모은다
- 태그와 revalidate 정책을 한 곳에서 관리한다
- 제목, breadcrumb, 본문이 동일 도메인 데이터 계약을 따르도록 만든다

---

## 체크리스트: Next.js 캐시 설계를 PR 전에 점검하는 질문

### 데이터 성격

- [ ] 이 데이터는 사용자 간 공유가 안전한가?
- [ ] 권한, 쿠키, 헤더, 실험군에 따라 결과가 달라지지 않는가?
- [ ] 테넌트 경계가 있다면 키나 태그에 반영됐는가?

### 캐시 계층

- [ ] 이 문제는 Request Memoization으로 충분한가, Data Cache가 필요한가?
- [ ] 라우트 결과 캐시와 데이터 캐시를 구분해서 설계했는가?
- [ ] 브라우저 Router Cache 때문에 체감 반영이 늦을 수 있음을 이해하고 있는가?

### 무효화 정책

- [ ] 쓰기 액션 직후 어떤 태그를 무효화해야 하는가?
- [ ] 어떤 경로를 재렌더해야 사용자가 즉시 최신 상태를 보는가?
- [ ] 새 페이지가 추가돼도 태그 중심 전파가 가능한 구조인가?

### 운영성

- [ ] 태그 네이밍 규칙이 문서화돼 있는가?
- [ ] stale 이슈가 났을 때 먼저 확인할 태그/path가 명확한가?
- [ ] 캐시 미스 급증 시 원본 저장소 보호 전략이 있는가?

### 안전성

- [ ] 사용자별/권한별 데이터에 전역 캐시를 붙이지 않았는가?
- [ ] `no-store`를 무심코 남발하지 않았는가?
- [ ] `unstable_cache` 키와 태그가 함수 결과 입력을 충분히 반영하는가?

---

## 팀 규칙으로 정리하면 더 강해진다

작은 팀이라도 아래 세 규칙만 잡아두면 캐시 사고가 크게 줄어든다.

### 규칙 1: 읽기 함수는 캐시 정책까지 함께 가진다

`getPost`, `getProduct`, `getTenantDashboard` 같은 함수는 단순 조회 래퍼가 아니라 캐시 계약의 소유자여야 한다. 호출하는 페이지마다 `revalidate`와 태그를 제각각 붙이기 시작하면 곧 정합성이 깨진다.

### 규칙 2: 쓰기 함수는 무효화까지 완료해야 성공이다

상품 수정, 문서 발행, 설정 변경은 DB 업데이트만 끝났다고 성공이 아니다. 어떤 태그와 경로가 오염됐는지 정리하고 같이 무효화해야 비로소 완료다.

### 규칙 3: 태그는 도메인 언어여야 한다

`data1`, `list2`, `cache-x` 같은 이름은 피한다. `product:123`, `tenant:42:dashboard`, `post-list`처럼 누가 봐도 의미가 드러나는 이름이 운영을 살린다.

---

## 한 줄 정리

**Next.js 캐싱의 핵심은 `fetch` 옵션을 외우는 것이 아니라, 어떤 데이터를 누구와 공유할 수 있는지 먼저 구분하고, 태그와 경로 무효화를 도메인 언어로 설계해 최신성, 비용, 장애 반경을 함께 통제하는 데 있다.**
