---
layout: post
title: "Next.js 번들 최적화 실전: RSC 경계, Client Boundary, Dynamic Import로 Hydration 비용 줄이는 법"
date: 2026-04-09 11:40:00 +0900
categories: [nextjs]
tags: [study, nextjs, rsc, bundle-optimization, hydration, performance, app-router]
---

## 배경: App Router 시대의 성능 병목은 "렌더링 속도"보다 "보내는 JavaScript 양"에서 더 자주 터진다

Next.js App Router를 도입한 팀이 초기에 가장 많이 체감하는 변화는 서버 컴포넌트(Server Components)다. 처음에는 대개 이렇게 생각한다.

- 서버에서 더 많이 렌더하니 자동으로 빨라질 것이다
- `app/` 디렉터리로 옮기면 번들 최적화는 프레임워크가 알아서 해줄 것이다
- `use client` 만 줄이면 성능 문제가 대부분 해결될 것이다

실무에 들어가면 그렇게 단순하지 않다. 페이지는 서버에서 잘 그려지는데도 실제 사용자 경험은 여전히 느릴 수 있다.

- 첫 화면 HTML은 빨리 왔는데 버튼 클릭 전까지 인터랙션이 굼뜨다
- 상품 상세 상단은 보이는데 필터, 정렬, 탭 전환이 버벅인다
- 차트, 에디터, 맵, 아이콘 라이브러리 때문에 특정 경로에서 JS가 급격히 비대해진다
- 레이아웃 상단 Provider 하나 때문에 사실상 전체 앱이 클라이언트 번들로 끌려간다
- `dynamic()` 을 썼는데도 체감 개선이 거의 없다
- 공용 컴포넌트를 편하게 재사용하다 보니 서버 컴포넌트 안에서도 불필요한 클라이언트 경계가 늘어난다

이 문제의 핵심은 단순히 "페이지가 서버에서 렌더되었는가"가 아니다. 사용자가 실제로 기다리는 비용은 보통 아래 네 가지의 합이다.

1. **다운로드 비용**: 브라우저가 JS 파일을 받아야 한다  
2. **파싱/실행 비용**: 받은 JS를 해석하고 실행해야 한다  
3. **Hydration 비용**: 정적 HTML을 실제 인터랙티브 UI로 연결해야 한다  
4. **업데이트 비용**: 이후 상태 변경마다 클라이언트에서 다시 계산해야 한다  

즉 App Router 시대의 성능 최적화는 이렇게 바뀌었다.

> HTML을 빨리 보내는 것만으로는 부족하다. **어떤 UI를 서버에 남기고, 어떤 부분만 클라이언트에 내릴지 경계를 설계해서 브라우저가 떠안는 JavaScript 총량과 hydration 범위를 줄이는 것**이 핵심이다.

이 글은 `next build` 숫자만 보는 번들 최적화 입문서가 아니다. 중급 이상 개발자를 기준으로, 실제 팀 프로젝트에서 자주 부딪히는 문제를 다룬다.

- `use client` 가 정확히 어떤 비용을 만드는가
- RSC 경계를 어디에 두어야 하는가
- Dynamic Import는 언제 듣고 언제 안 듣는가
- 전역 Provider, 차트, 에디터, 모달, 검색 필터처럼 자주 비대해지는 UI를 어떻게 쪼개는가
- 번들 크기와 개발 생산성, 재사용성, UX 사이 트레이드오프는 무엇인가
- 실제 코드 리뷰에서 어떤 안티패턴을 잡아야 하는가

목표는 하나다.

> **Next.js에서 성능 최적화를 “빌드 결과 확인”이 아니라 “컴포넌트 경계 설계” 문제로 이해하는 것**

---

## 먼저 큰 그림: Next.js 번들 최적화는 결국 "클라이언트로 내려가는 코드의 면적"을 줄이는 일이다

App Router를 쓴다고 해서 모든 코드가 자동으로 서버 컴포넌트가 되는 것은 맞지만, 실제 프로젝트에서는 아주 작은 실수 하나가 클라이언트 번들을 예상보다 크게 만든다.

대표적인 오해부터 정리하자.

### 오해 1) 서버 컴포넌트 안에 있으니 그 자식도 자동으로 서버 전용이다

아니다. 어떤 컴포넌트가 `"use client"` 를 선언하면, 그 컴포넌트 자체뿐 아니라 **그 경계 아래에서 클라이언트에 필요한 의존성 그래프**가 생긴다. 즉 "서버 컴포넌트 트리 안에 위치한다"는 사실만으로 번들 비용이 사라지지 않는다.

### 오해 2) `use client` 는 컴포넌트 한 파일에만 영향이 있다

실제로는 그렇지 않다. 해당 컴포넌트가 import하는 훅, 유틸, UI 조합, 상태 라이브러리, 아이콘, 폼 라이브러리, 심지어 무심코 가져온 큰 서드파티 모듈까지 연결된다. 즉 `use client` 한 줄은 대개 **클라이언트 실행 그래프의 시작점**이다.

### 오해 3) Dynamic Import만 쓰면 무조건 가벼워진다

`dynamic()` 은 강력하지만 만능이 아니다.

- 초기 렌더에 꼭 필요한 UI라면 결국 바로 로드된다
- dynamic으로 쪼갰지만 공통 상위 Client Component가 너무 크면 근본 개선이 없다
- SSR을 꺼서 hydration을 줄인 것처럼 보여도, 실제로는 사용자에게 늦은 렌더와 레이아웃 점프만 남길 수 있다

### 오해 4) 전역 Provider는 어차피 한 번만 로드되니 괜찮다

실무에서는 이게 가장 자주 앱 전체 번들을 비대하게 만든다.

- `app/layout.tsx` 에 `ThemeProvider`, `QueryClientProvider`, `AuthProvider`, `ModalProvider`, `Toaster`, `Analytics`, `FeatureFlagProvider` 를 한 번에 올린다
- 결과적으로 상단 레이아웃이 클라이언트화된다
- 모든 하위 경로에서 필요하지 않은 상태/라이브러리도 공통 초기 비용이 된다

즉 번들 최적화의 본질은 도구 선택이 아니라 질문의 순서다.

1. 이 UI는 **정말 브라우저에서 실행되어야 하는가**  
2. 브라우저에서 실행되어야 한다면 **얼마나 작은 섬으로 격리할 수 있는가**  
3. 처음부터 필요한가, 아니면 **사용자 행동 이후 지연 로딩할 수 있는가**  
4. 공통 레이아웃이 아니라 **해당 경로/기능 안으로 범위를 줄일 수 있는가**  

이 네 질문이 서면 대부분의 번들 문제는 구조적으로 줄어든다.

---

## 핵심 개념 1: `use client` 는 문법이 아니라 "이 아래는 브라우저 런타임이 책임진다"는 선언이다

App Router에서 가장 중요한 경계는 `use client` 다. 이 지시어를 단순히 "이 컴포넌트에서 state를 쓰고 싶다" 정도로 이해하면 최적화가 어려워진다.

실제로 `use client` 는 다음 의미를 가진다.

- 이 컴포넌트는 브라우저에서 실행되어야 한다
- 따라서 클라이언트 JS 번들에 포함될 수 있다
- props는 서버에서 직렬화되어 내려와야 한다
- 이 파일이 import하는 클라이언트 의존성도 함께 고려해야 한다
- hydration 대상이 된다

### 왜 `use client` 가 비싼가

`use client` 자체가 비용인 것은 아니다. 비용은 그 이후에 따라오는 것들이다.

#### 1) 직렬화 경계가 생긴다

서버에서 브라우저로 props를 넘겨야 하므로 함수, 복잡한 클래스 인스턴스, 비직렬화 객체를 그대로 넘길 수 없다. 그래서 구조를 단순화하거나 클라이언트 쪽 재계산을 하게 된다.

#### 2) hydration 대상이 생긴다

정적 HTML이 이미 있어도, 브라우저는 이 컴포넌트 트리를 다시 연결해야 한다. 트리가 깊고 의존성이 많을수록 비용이 커진다.

#### 3) 렌더링이 서버 최적화에서 벗어난다

서버 컴포넌트는 브라우저 번들에 포함되지 않거나 최소화될 수 있지만, 클라이언트 컴포넌트는 사용자 기기 성능의 영향을 직접 받는다. 모바일 중저가 기기에서 차이가 특히 커진다.

#### 4) 캐시/데이터 페칭 전략이 달라진다

서버에서 해결할 수 있었던 읽기 로직을 클라이언트 상태로 옮기면, 네트워크 재요청, 로딩 상태, 에러 상태, 캐시 무효화까지 클라이언트 복잡도가 올라간다.

### 실무 기준: `use client` 는 leaf에 둘수록 좋다

나쁜 예부터 보자.

```tsx
// app/products/page.tsx
"use client";

import { useState } from "react";
import { ProductCard } from "@/components/product-card";

export default function ProductsPage({ products }: { products: Product[] }) {
  const [selectedCategory, setSelectedCategory] = useState("all");

  const filtered = products.filter((p) =>
    selectedCategory === "all" ? true : p.category === selectedCategory
  );

  return (
    <div>
      <CategoryFilter
        value={selectedCategory}
        onChange={setSelectedCategory}
      />
      <ProductGrid products={filtered} />
    </div>
  );
}
```

이 구조의 문제는 페이지 전체가 클라이언트 경계가 된다는 점이다. 필터 UI 하나 때문에 목록 렌더링, 카드 트리, 데이터 전달 구조가 전부 브라우저 책임이 된다.

더 나은 구조는 이런 식이다.

```tsx
// app/products/page.tsx
import { getProducts } from "@/lib/products";
import { ProductGrid } from "@/components/product-grid";
import { CategoryFilterIsland } from "@/components/category-filter-island";

export default async function ProductsPage() {
  const products = await getProducts();

  return (
    <div>
      <CategoryFilterIsland />
      <ProductGrid products={products} />
    </div>
  );
}
```

```tsx
// components/category-filter-island.tsx
"use client";

import { useRouter, useSearchParams } from "next/navigation";

export function CategoryFilterIsland() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const current = searchParams.get("category") ?? "all";

  function update(category: string) {
    const params = new URLSearchParams(searchParams.toString());
    params.set("category", category);
    router.push(`/products?${params.toString()}`);
  }

  return <CategoryTabs value={current} onChange={update} />;
}
```

핵심 차이는 분명하다.

- 페이지의 읽기와 기본 렌더는 서버에 남긴다
- 인터랙션이 필요한 작은 필터 조작만 클라이언트로 보낸다
- 상태를 URL로 올려 서버와 동기화한다
- 목록 전체 hydration을 피한다

즉 `use client` 의 최적 해석은 이렇다.

> 브라우저에서 꼭 필요한 동작만 **작은 인터랙션 섬(island)** 으로 내려라.

---

## 핵심 개념 2: RSC 경계는 "컴포넌트 책임 분리"와 "번들 분리"를 동시에 만든다

서버 컴포넌트와 클라이언트 컴포넌트의 경계를 잘 잡는 팀은 코드도 더 읽기 쉽고 성능도 더 좋다. 이유는 단순하다. 경계가 곧 책임 구분이기 때문이다.

### 서버 컴포넌트가 잘하는 일

- DB/API에서 읽기
- 인증/권한 정보 기반 분기
- SEO에 필요한 콘텐츠 렌더링
- 비밀값이 필요한 작업
- 큰 라이브러리 없이도 가능한 마크업 조합
- 브라우저 상태가 필요 없는 UI 조립

### 클라이언트 컴포넌트가 필요한 일

- 이벤트 핸들러 (`onClick`, `onChange`)
- `useState`, `useReducer`, `useEffect`
- 브라우저 API 접근 (`window`, `localStorage`, `IntersectionObserver`)
- 애니메이션 상태, 드래그 앤 드롭, 에디터, 차트 상호작용
- 실시간 입력 상태와 낙관적 상호작용

문제는 많은 코드베이스에서 이 둘이 섞여 있다는 점이다. 예를 들어 아래는 흔한 안티패턴이다.

```tsx
"use client";

import { formatPrice } from "@/lib/format";
import { useCart } from "@/store/cart";

export function ProductHero({ product }: { product: Product }) {
  const { addItem } = useCart();

  return (
    <section>
      <h1>{product.name}</h1>
      <p>{formatPrice(product.price)}</p>
      <p>{product.description}</p>
      <button onClick={() => addItem(product)}>장바구니 담기</button>
    </section>
  );
}
```

겉보기엔 문제 없어 보이지만, 사실 버튼 하나 때문에 아래가 한 덩어리로 클라이언트에 내려간다.

- 상세 상단 전체 마크업
- 가격 포맷팅 코드
- 설명 텍스트 렌더링
- cart store 의존성
- 관련 import 그래프

이럴 때는 보통 이렇게 나누는 편이 낫다.

```tsx
// components/product-hero.tsx
import { formatPrice } from "@/lib/format";
import { AddToCartButton } from "./add-to-cart-button";

export function ProductHero({ product }: { product: Product }) {
  return (
    <section>
      <h1>{product.name}</h1>
      <p>{formatPrice(product.price)}</p>
      <p>{product.description}</p>
      <AddToCartButton productId={product.id} />
    </section>
  );
}
```

```tsx
// components/add-to-cart-button.tsx
"use client";

import { useCart } from "@/store/cart";

export function AddToCartButton({ productId }: { productId: string }) {
  const { addItem } = useCart();

  return <button onClick={() => addItem({ productId, quantity: 1 })}>장바구니 담기</button>;
}
```

이 구조의 장점은 단순하다.

- 상품 정보 대부분은 서버에서 렌더된다
- hydration 대상은 버튼 하나로 줄어든다
- 상태 store 의존성은 좁은 범위에 묶인다
- 추후 버튼 교체나 A/B 테스트도 쉽게 격리된다

### 실무 포인트: 공통 UI 컴포넌트도 무조건 클라이언트화하지 말 것

디자인 시스템을 운영할수록 이런 실수가 많아진다.

- `Button` 에 ripple effect 때문에 `use client`
- `Card` 에 hover measurement 때문에 `use client`
- `Tabs` 전체가 클라이언트라서 콘텐츠도 모두 클라이언트화
- `Modal`, `Dropdown`, `Tooltip` 컴포넌트를 편하게 재사용하려고 페이지 전체를 클라이언트화

이때의 원칙은 명확하다.

> **상호작용 컨테이너와 정적 콘텐츠 영역을 분리하라.**

예를 들어 탭 UI라면 탭 헤더만 클라이언트고, 실제 각 탭의 콘텐츠는 서버에서 렌더하는 조합도 가능하다. 모달도 오픈 상태 관리만 클라이언트이고, 본문 데이터는 서버에서 가져와 넣는 패턴이 흔히 더 낫다.

---

## 핵심 개념 3: Dynamic Import는 "무거운 코드를 나중에 받아도 UX가 깨지지 않을 때" 가장 효과적이다

`next/dynamic` 은 번들 최적화에서 매우 유용하지만, 어디에 쓰느냐가 중요하다.

### Dynamic Import가 특히 잘 맞는 대상

- 차트 라이브러리 (`echarts`, `recharts`, `chart.js`)
- 리치 텍스트 에디터 (`tiptap`, `quill`, `slate`, `monaco`)
- 지도/지도 오버레이 (`mapbox`, `leaflet`, `google maps`)
- 이미지 편집기, 코드 하이라이터, PDF viewer
- rarely used admin tools
- 모달을 열었을 때만 필요한 복잡한 폼

이들의 공통점은 명확하다.

- 라이브러리 자체가 크다
- 초기 진입에서 반드시 필요하지 않을 수 있다
- 사용자 행동 이후 로딩되어도 큰 UX 문제가 없다

### 기본 패턴

```tsx
import dynamic from "next/dynamic";

const RevenueChart = dynamic(() => import("./revenue-chart"), {
  loading: () => <ChartSkeleton />,
});

export function DashboardSection() {
  return (
    <section>
      <h2>매출 추이</h2>
      <RevenueChart />
    </section>
  );
}
```

이 패턴이 좋은 이유는 초기 경로 진입 시 차트 코드가 main client bundle에 붙지 않을 가능성이 높아진다는 점이다.

### `ssr: false` 는 최후 수단에 가깝다

많은 팀이 브라우저 전용 라이브러리가 에러를 내면 이렇게 해결한다.

```tsx
const Editor = dynamic(() => import("./editor"), { ssr: false });
```

이 방식이 필요한 경우도 있지만, 무심코 남용하면 문제가 생긴다.

- 서버에서는 아무 것도 렌더하지 못한다
- SEO 대상 콘텐츠라면 손해가 크다
- 로딩 중 빈 영역이나 점프가 발생하기 쉽다
- hydration 자체를 줄인 게 아니라, 서버 렌더 기회를 포기한 것일 뿐일 수 있다

즉 `ssr: false` 는 보통 아래 조건을 만족할 때 더 적절하다.

- 브라우저 API 의존이 강해 서버 렌더 의미가 거의 없다
- 초기 화면에서 필수 콘텐츠가 아니다
- 관리자 도구나 편집기처럼 인터랙션 중심이다
- placeholder 전략이 명확하다

### Dynamic Import가 별 효과 없을 때

아래 같은 경우에는 기대만큼 이득이 작다.

#### 1) 첫 화면 핵심 CTA 자체가 dynamic 대상일 때

로그인 폼, 결제 버튼, 상품 상단 핵심 옵션처럼 초기 인터랙션의 중심이면 결국 바로 받아야 한다. 쪼개도 초기 체감 개선이 거의 없거나 오히려 늦을 수 있다.

#### 2) 상위 Client Component가 너무 클 때

예를 들어 페이지 전체가 이미 `use client` 이고 그 안에서 차트만 dynamic해도, 상위 상태/레이아웃/유틸/아이콘 그래프가 이미 크게 내려가고 있다면 구조적 개선은 제한적이다.

#### 3) 너무 잘게 쪼개서 네트워크 요청 오버헤드가 늘 때

번들은 무조건 잘게 쪼갠다고 좋은 게 아니다. 작은 chunk가 너무 많아지면 캐시, 요청 수, 실행 순서, 사용자 대기 경험이 오히려 복잡해질 수 있다.

핵심 기준은 이것이다.

> **dynamic import는 “작은 조각으로 나눈다”보다 “초기 사용자 여정에서 제외할 수 있는 비용을 뒤로 미룬다”는 관점으로 써야 한다.**

---

## 핵심 개념 4: Provider 범위는 작을수록 좋고, 전역 Provider는 정말 전역일 때만 전역이어야 한다

실무에서 번들 최적화를 망치는 가장 흔한 구조는 전역 layout provider 비대화다.

예를 들어 이런 구조를 생각해보자.

```tsx
// app/layout.tsx
import { Providers } from "@/components/providers";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
```

```tsx
// components/providers.tsx
"use client";

import { ThemeProvider } from "next-themes";
import { QueryClientProvider } from "@tanstack/react-query";
import { TooltipProvider } from "@radix-ui/react-tooltip";
import { AuthProvider } from "@/features/auth/provider";
import { ModalProvider } from "@/features/modal/provider";
import { AnalyticsProvider } from "@/features/analytics/provider";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <TooltipProvider>
          <AuthProvider>
            <ModalProvider>
              <AnalyticsProvider>{children}</AnalyticsProvider>
            </ModalProvider>
          </AuthProvider>
        </TooltipProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}
```

이 패턴이 처음엔 편하다. 문제는 다음과 같다.

- 앱의 모든 경로가 이 클라이언트 경계를 통과한다
- 실제로 필요 없는 provider까지 공통 초기 비용이 된다
- 특정 관리자 화면에서만 필요한 QueryClient나 Modal 상태가 공개 페이지에도 붙는다
- provider 내부에서 쓰는 라이브러리와 의존성 그래프가 루트로 올라온다

### 더 나은 기준

#### 1) 진짜 전역인지 먼저 묻기

- 테마 토글: 전역일 수 있다
- 인증 세션 읽기: 서버에서 처리 가능하면 굳이 전역 클라이언트 provider가 필요 없을 수 있다
- React Query: 전체 앱 필수인가, 일부 dashboard/실시간 UI에만 필요한가
- 모달 시스템: 공개 페이지에도 항상 필요한가
- Toast: 정말 루트 전체에 붙어야 하는가, 특정 shell 안이면 충분한가

#### 2) route segment 단위로 내리기

예를 들어 admin 영역에서만 React Query와 복잡한 상태가 필요하다면 이렇게 나누는 편이 좋다.

```tsx
// app/(admin)/layout.tsx
import { AdminProviders } from "./admin-providers";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return <AdminProviders>{children}</AdminProviders>;
}
```

```tsx
// app/(admin)/admin-providers.tsx
"use client";

import { QueryClientProvider } from "@tanstack/react-query";
import { CommandPaletteProvider } from "@/features/command/provider";

export function AdminProviders({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <CommandPaletteProvider>{children}</CommandPaletteProvider>
    </QueryClientProvider>
  );
}
```

이렇게 하면 공개 랜딩, 블로그, 상품 소개 페이지에는 관리자용 클라이언트 상태 비용이 안 섞인다.

#### 3) Provider 안에서도 역할을 분리하기

전역 provider 파일 하나에 모든 걸 몰지 말고, 경로/기능별로 provider composition을 분리하면 책임이 보인다. 번들도 더 예측 가능해진다.

### 실무 체크 포인트

- `app/layout.tsx` 가 `use client` 인가? 거의 항상 의심해봐야 한다
- `Providers` 라는 이름 아래 몇 개의 라이브러리가 한 번에 들어있는가?
- 그중 실제로 모든 페이지에서 필요한 것은 몇 개인가?
- root provider 때문에 `next build` 의 First Load JS가 과도하게 올라가고 있지 않은가?

이 영역은 코드 리뷰에서 아주 자주 놓친다. 기능 추가는 쉬운데, 성능 비용은 누적되기 때문이다.

---

## 핵심 개념 5: 아이콘, 유틸, 디자인 시스템 import 습관도 번들 크기에 영향을 준다

번들 최적화는 거대한 차트 라이브러리만의 문제가 아니다. 작은 습관들이 누적되면 꽤 커진다.

### 1) 아이콘 라이브러리 남용

예를 들어 화면 하나에서 아이콘 수십 개를 쓴다고 하자. 아이콘 라이브러리 자체는 tree-shaking이 되더라도 다음 문제가 자주 생긴다.

- 공용 파일에서 대량 re-export
- 필요 없는 아이콘 세트까지 한 번에 import
- 동적 icon mapping 때문에 정적 분석이 깨짐

나쁜 예:

```tsx
import * as Icons from "lucide-react";

export function MenuIcon({ name }: { name: string }) {
  const Icon = Icons[name as keyof typeof Icons];
  return Icon ? <Icon /> : null;
}
```

이 패턴은 편하지만 번들 최적화 관점에서는 불리하다. 가능한 경우 명시적 매핑으로 범위를 제한하는 편이 낫다.

```tsx
import { Search, Settings, Bell } from "lucide-react";

const iconMap = {
  search: Search,
  settings: Settings,
  bell: Bell,
};
```

### 2) barrel export가 클라이언트 경계를 흐리게 만드는 경우

`index.ts` 로 모든 컴포넌트를 re-export 하면 개발 경험은 좋아진다. 하지만 서버/클라이언트 혼합 모듈이 섞이면 트리 셰이킹과 경계 이해가 어려워질 수 있다.

특히 이런 패턴은 조심할 만하다.

- `components/index.ts` 에 서버/클라이언트 컴포넌트 혼재
- `lib/index.ts` 에 브라우저 전용/서버 전용 유틸 혼합
- 특정 util 하나만 필요했는데 큰 의존성 묶음 전체를 끌어오는 구조

### 3) date, chart, markdown, syntax highlighting 계열 라이브러리

크기가 상대적으로 큰 라이브러리는 특히 import 위치를 신중하게 봐야 한다.

- 클라이언트에서 꼭 필요한가?
- 서버에서 변환해 문자열/HTML/JSON으로 넘길 수 없는가?
- 정말 모든 경로에서 필요한가, 특정 상세/에디터/프리뷰에만 필요한가?

예를 들어 Markdown 렌더링이나 코드 하이라이팅은 서버에서 처리 가능한 경우가 많다. 굳이 클라이언트에 전체 파서를 보내는 순간 초기 비용이 급격히 올라간다.

### 4) `server-only`, `client-only` 로 경계 실수 방지

경계를 실수로 섞는 일을 줄이려면 `server-only`, `client-only` 같은 도구도 유용하다.

```ts
// lib/secret-config.ts
import "server-only";

export const internalApiKey = process.env.INTERNAL_API_KEY!;
```

이런 표시는 단순한 안전장치가 아니라, 팀 차원에서 경계 의도를 명시하는 효과가 있다. 번들 크기뿐 아니라 보안 사고도 줄일 수 있다.

---

## 핵심 개념 6: "데이터 읽기"와 "인터랙션 상태"를 분리하면 번들과 hydration이 함께 줄어든다

많은 페이지가 클라이언트화되는 근본 원인은 상태 때문이다. 그런데 잘 보면 상태의 종류가 두 가지로 나뉜다.

1. **도메인 데이터 상태**: 서버가 진실 소스인 읽기 결과  
2. **UI 인터랙션 상태**: 열림/닫힘, 탭, 필터, 정렬, hover, selection  

이 둘을 한 컴포넌트에 합치면 페이지 전체가 클라이언트로 기운다.

### 예시: FAQ 아코디언

나쁜 예:

```tsx
"use client";

export function FaqPage({ faqs }: { faqs: Faq[] }) {
  const [openId, setOpenId] = useState<string | null>(null);

  return (
    <div>
      {faqs.map((faq) => (
        <FaqItem
          key={faq.id}
          faq={faq}
          open={faq.id === openId}
          onToggle={() => setOpenId(faq.id)}
        />
      ))}
    </div>
  );
}
```

더 나은 예:

```tsx
// app/faq/page.tsx
import { getFaqs } from "@/lib/faq";
import { FaqList } from "@/components/faq-list";

export default async function FaqPage() {
  const faqs = await getFaqs();
  return <FaqList faqs={faqs} />;
}
```

```tsx
// components/faq-list.tsx
import { FaqItemToggle } from "./faq-item-toggle";

export function FaqList({ faqs }: { faqs: Faq[] }) {
  return (
    <div>
      {faqs.map((faq) => (
        <article key={faq.id}>
          <FaqItemToggle question={faq.question}>
            <div dangerouslySetInnerHTML={{ __html: faq.answerHtml }} />
          </FaqItemToggle>
        </article>
      ))}
    </div>
  );
}
```

```tsx
// components/faq-item-toggle.tsx
"use client";

import { useState } from "react";

export function FaqItemToggle({
  question,
  children,
}: {
  question: string;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);

  return (
    <div>
      <button onClick={() => setOpen((v) => !v)}>{question}</button>
      {open ? children : null}
    </div>
  );
}
```

이 구조에서도 children을 포함한 일부 subtree가 클라이언트 경계 아래 렌더되긴 하지만, 핵심은 **데이터를 읽는 책임과 인터랙션 토글 책임을 분리했다**는 점이다. 이 분리는 더 큰 화면에서 특히 중요하다.

### URL state를 활용하면 더 좋다

필터, 정렬, 페이지네이션은 `useState` 로 클라이언트에만 두지 말고 search params로 올리면 서버 컴포넌트와 자연스럽게 연결된다.

장점은 많다.

- 새로고침/공유 가능
- 서버 fetch와 정합성 유지
- 페이지 전체 클라이언트화를 피함
- 캐시와 SEO, 분석에도 유리

즉 실무에서는 이렇게 생각하면 편하다.

- **읽기 데이터**는 서버 우선
- **짧은 상호작용 상태**는 작은 client island
- **공유 가치 있는 상태**는 URL 우선

---

## 실무 예시 1: 전자상거래 상품 상세 페이지 최적화

상품 상세는 Next.js 번들 문제가 잘 드러나는 화면이다. 대개 이런 요소들이 함께 있다.

- 상품 이미지 갤러리
- 가격/재고/혜택 정보
- 옵션 선택기
- 장바구니 담기 버튼
- 리뷰 요약
- 추천 상품 캐러셀
- 최근 본 상품
- 배송 안내 accordion
- 상담 챗봇/추적 스크립트

초기 구현은 흔히 이렇게 된다.

```tsx
"use client";

export default function ProductPage() {
  const [selectedOption, setSelectedOption] = useState(null);
  const [quantity, setQuantity] = useState(1);
  const [activeImage, setActiveImage] = useState(0);
  const [openTab, setOpenTab] = useState("detail");

  // 상품 데이터 fetch, 리뷰 fetch, 추천 fetch ...
  // 차트, 캐러셀, tracking script, chat widget...
}
```

이 구조의 문제는 너무 명확하다.

- 사실상 전체 상세 페이지가 hydration 대상
- 옵션 선택기 하나 때문에 본문 설명, 정책, 리뷰 요약까지 클라이언트 트리에 묶임
- 추천/최근 본 상품 캐러셀 라이브러리 비용도 초기 번들에 들어오기 쉬움

### 더 나은 구조

#### 1) 상세 기본 정보는 서버에 둔다

```tsx
// app/products/[id]/page.tsx
import { getProductDetail } from "@/lib/products";
import { ProductHero } from "@/components/product-hero";
import { ProductTabs } from "@/components/product-tabs";
import { RecommendationSection } from "@/components/recommendation-section";

export default async function ProductPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const product = await getProductDetail(id);

  return (
    <main>
      <ProductHero product={product} />
      <ProductTabs product={product} />
      <RecommendationSection productId={id} />
    </main>
  );
}
```

#### 2) 옵션 선택기와 장바구니 버튼만 client island로 둔다

```tsx
// components/product-purchase-panel.tsx
"use client";

import { useState } from "react";

export function ProductPurchasePanel({
  productId,
  options,
}: {
  productId: string;
  options: ProductOption[];
}) {
  const [selectedOptionId, setSelectedOptionId] = useState(options[0]?.id ?? null);
  const [quantity, setQuantity] = useState(1);

  return (
    <section>
      <OptionSelector
        options={options}
        value={selectedOptionId}
        onChange={setSelectedOptionId}
      />
      <QuantitySelector value={quantity} onChange={setQuantity} />
      <AddToCartButton
        productId={productId}
        optionId={selectedOptionId}
        quantity={quantity}
      />
    </section>
  );
}
```

#### 3) 추천/리뷰 캐러셀은 늦게 로드해도 되면 dynamic 분리

```tsx
import dynamic from "next/dynamic";

const RecommendationCarousel = dynamic(
  () => import("./recommendation-carousel"),
  { loading: () => <RecommendationSkeleton /> }
);
```

#### 4) 챗봇/추적 스크립트는 사용자 행동 이후 또는 idle 시점으로 미룬다

이런 요소는 상품 구매 핵심 여정의 일부가 아닌 경우가 많다. 무조건 루트에서 즉시 붙이지 말고, 최소한 우선순위를 다시 따져봐야 한다.

### 얻는 효과

- 상품 제목, 가격, 설명은 빠르게 서버 렌더
- 상호작용이 필요한 옵션 패널만 hydration
- 무거운 추천 캐러셀, 챗봇 위젯은 초기에 제외 가능
- 상세 SEO와 체감 속도를 동시에 챙길 수 있음

이 예시는 단순하지만, 실제 서비스에서 효과가 큰 패턴이다.

---

## 실무 예시 2: 관리자 대시보드에서 차트와 필터를 다루는 법

대시보드는 공개 페이지보다 번들 관리가 느슨해지기 쉽다. "어차피 내부 사용자고 데스크톱이니까"라는 이유다. 하지만 관리자 화면은 오히려 기능이 많아서 번들이 더 빨리 무거워진다.

전형적인 구성은 이렇다.

- 상단 KPI
- 날짜 필터
- 차트 3~5개
- 테이블
- CSV 다운로드
- 드로어/모달
- 실시간 polling 또는 query cache

### 흔한 안티패턴

- 전체 dashboard page가 `use client`
- `useEffect` 안에서 모든 데이터 fetch
- 차트 라이브러리 전부 초기 번들 포함
- 날짜 필터, KPI, 테이블, 모달 상태가 한 파일에 몰림

이 구조는 개발은 빠르지만 성능과 유지보수성이 금방 나빠진다.

### 권장 구조

#### 1) 필터는 작게, 데이터 읽기는 서버 또는 segment 단위로

날짜 범위, 조직 선택 같은 값은 search params로 두고, 서버에서 해당 값 기반 데이터를 읽는 구조가 더 예측 가능하다.

```tsx
// app/(admin)/dashboard/page.tsx
export default async function DashboardPage({
  searchParams,
}: {
  searchParams: Promise<{ range?: string; org?: string }>;
}) {
  const params = await searchParams;
  const range = params.range ?? "7d";
  const org = params.org ?? "all";

  const [kpis, tableRows] = await Promise.all([
    getDashboardKpis({ range, org }),
    getTopRows({ range, org }),
  ]);

  return (
    <main>
      <DashboardFilterIsland initial={{ range, org }} />
      <KpiSection data={kpis} />
      <TopRowsTable rows={tableRows} />
      <ChartsSection range={range} org={org} />
    </main>
  );
}
```

#### 2) 차트는 별도 클라이언트 섹션 + dynamic import

```tsx
import dynamic from "next/dynamic";

const ChartsClient = dynamic(() => import("./charts-client"), {
  loading: () => <DashboardChartsSkeleton />,
});

export function ChartsSection({ range, org }: { range: string; org: string }) {
  return <ChartsClient range={range} org={org} />;
}
```

#### 3) React Query는 admin shell 범위에만 둔다

실시간 refetch나 mutation 후 query invalidation이 필요한 영역에서만 사용한다. 공개 페이지까지 루트에서 감쌀 이유는 별로 없다.

#### 4) heavy export 기능은 on-demand 로딩

CSV export, chart drill-down modal, report builder 같은 기능은 버튼 클릭 시 로드하는 편이 낫다.

### 트레이드오프

이 구조는 코드가 조금 더 쪼개진다. 대신 다음을 얻는다.

- 관리 화면 첫 진입이 가벼워진다
- 필터와 데이터 경계가 선명해진다
- 차트 라이브러리 비용을 필요한 곳으로 제한할 수 있다
- admin 전용 복잡한 상태를 public app과 분리할 수 있다

즉 dashboard는 "내부용이니 대충 클라이언트로" 가 아니라, 오히려 **클라이언트 비용이 비대해지기 쉬운 대표 사례**로 보는 게 맞다.

---

## 실무 예시 3: 블로그/콘텐츠 페이지에서 불필요한 hydration을 줄이는 법

콘텐츠 사이트는 특히 서버 컴포넌트와 잘 맞는다. 그런데도 의외로 hydration 비용이 높게 나오는 경우가 많다.

원인은 대개 아래와 같다.

- 목차 생성과 코드 하이라이팅을 클라이언트에서 처리
- 댓글, 추천 글, 공유 버튼, 광고 스크립트를 전부 즉시 로드
- 문서 본문 전체를 클라이언트 마크다운 렌더러로 처리
- theme, search, analytics, feedback 위젯이 루트에 과하게 결합

### 권장 기준

#### 1) 본문 렌더링은 최대한 서버에서

Markdown 파싱, syntax highlighting, heading slug 생성, TOC 추출은 서버에서 가능하면 서버에서 끝내는 편이 낫다. 읽기 콘텐츠에 굳이 큰 파서를 브라우저로 보낼 필요가 없다.

#### 2) 인터랙션은 섬으로 분리

- 복사 버튼
- 좋아요 버튼
- 댓글 입력창
- 피드백 위젯
- 공유 메뉴

이런 요소는 본문 전체를 클라이언트화하지 말고 작은 island로 두는 편이 낫다.

#### 3) 광고/분석/댓글은 우선순위 분리

사용자에게 가장 중요한 것은 본문 자체다. 댓글, 추천, 광고, 실험 스크립트는 핵심 읽기 경험을 방해하지 않도록 붙여야 한다.

콘텐츠 사이트는 특히 "JS가 없어도 읽을 수 있어야 한다"는 기준을 세우면 구조가 많이 정리된다.

---

## 핵심 개념 7: Hydration 비용은 번들 크기만이 아니라 "얼마나 넓은 DOM/컴포넌트 트리를 연결하느냐"의 문제이기도 하다

번들 분석만 보다 보면 KB 숫자에만 집중하게 된다. 하지만 실제 체감 성능에는 hydration 범위도 매우 중요하다.

같은 80KB라도 아래 둘은 다르다.

- 상단 헤더, 필터 바, 카드 리스트 전체가 client tree인 경우
- 작은 검색창과 버튼만 client tree인 경우

전자는 브라우저가 연결해야 할 노드와 이벤트, 상태 경계가 많다. 후자는 훨씬 좁다.

### hydration 비용을 키우는 대표 패턴

#### 1) 큰 리스트 전체 client rendering

상품 카드 100개가 있는 목록에서 카드 hover 효과나 좋아요 버튼 때문에 전체 grid를 클라이언트화하면 비용이 크게 오른다. 목록은 서버 렌더, 상호작용은 카드 내부 작은 island로 분리하는 것이 보통 더 낫다.

#### 2) 레이아웃 전체에 전역 state 구독

헤더, 사이드바, 본문, 푸터가 하나의 전역 store를 구독하면 작은 상태 변경에도 넓은 범위가 반응할 수 있다. 번들뿐 아니라 런타임 업데이트 비용도 커진다.

#### 3) 사용하지 않는 탭 패널까지 한 번에 hydration

탭 UI가 있다고 해서 모든 탭 본문을 클라이언트에서 미리 마운트할 필요는 없다. 자주 보지 않는 패널은 조건부 렌더, lazy load, 혹은 서버 기반 segment 분리도 고려할 만하다.

#### 4) 모달 루트에 무거운 폼과 라이브러리를 기본 포함

"언젠가 열릴 수 있는 모달" 이라고 해서 앱 시작 시점에 다 로드할 필요는 없다. 열릴 때 import해도 충분한 경우가 많다.

### 측정 관점에서 무엇을 볼까

단순한 bundle size 외에도 아래를 함께 보면 좋다.

- 특정 경로의 First Load JS
- hydration 전후 인터랙션 가능 시점
- CPU가 약한 기기에서 입력 지연
- route transition 시 새 chunk 로딩 대기
- 특정 store 업데이트가 넓은 subtree를 흔드는지

즉 hydration은 정적 HTML 이후의 **브라우저 연결 비용**이다. 이걸 줄이려면 파일 크기뿐 아니라 **경계 폭**을 줄여야 한다.

---

## 핵심 개념 8: 번들 분석은 숫자를 보는 일이 아니라 "왜 이 코드가 이 경로까지 따라왔는가"를 추적하는 일이다

최적화를 하려면 측정이 필요하다. 하지만 단순히 "현재 JS가 230KB니까 줄이자"는 접근은 한계가 있다. 중요한 건 경로와 원인이다.

### 무엇을 확인해야 하나

#### 1) 어떤 route가 특히 큰가

공개 홈, 블로그 상세, 상품 상세, 관리자 대시보드는 비용 구조가 다르다. 앱 전체 평균보다 **경로별 편차**를 보는 편이 훨씬 유용하다.

#### 2) 공통 chunk가 왜 커졌는가

특정 경로만 무거운 것이 아니라, root layout/provider 때문에 모든 경로의 공통 비용이 올라갔는지 확인해야 한다.

#### 3) 기대와 다르게 클라이언트로 따라온 모듈이 무엇인가

예를 들어 서버 유틸인 줄 알았는데 barrel export를 통해 client graph에 섞여 들어온 경우가 꽤 있다.

#### 4) route-local split이 실제로 되는가

차트, 에디터, 맵을 dynamic으로 쪼갰는데도 공통 layout chunk에 섞여 있다면 import 위치나 provider 구조를 다시 봐야 한다.

### 숫자만 보면 놓치는 것

- 번들 크기는 줄었는데 UX는 더 나빠질 수 있다
- dynamic import를 과하게 써서 skeleton 깜빡임이 심해질 수 있다
- SSR을 꺼서 JS는 줄었지만 콘텐츠 표시가 늦어질 수 있다
- 로컬 고성능 개발 환경에서는 체감되지 않던 CPU 비용이 실제 저사양 기기에서 크게 드러날 수 있다

즉 번들 분석의 질문은 이렇다.

> 이 JavaScript는 **정말 이 시점에, 이 경로에서, 이 사용자에게** 필요한가?

이 질문에 대답할 수 있으면 최적화 방향이 명확해진다.

---

## 핵심 개념 9: Third-party Script와 브라우저 전용 위젯은 "기능"이 아니라 "로드 시점"까지 설계해야 한다

실제 프로덕션에서 번들을 무겁게 만드는 주범은 종종 React 컴포넌트보다 서드파티 스크립트다.

- 채팅 상담 위젯
- 행동 분석/실험 스크립트
- 광고/전환 추적 태그
- 고객 지원 SDK
- 지도/캘린더 embed
- 외부 로그인/결제용 브라우저 SDK

이들은 보통 기능 단위로 도입된다. 하지만 사용자 브라우저 입장에서는 아래 비용을 만든다.

- 추가 네트워크 요청
- 메인 스레드 실행 비용
- 전역 이벤트 리스너 등록
- hydration 이후 상호작용 지연
- 페이지 전체 장기 task 증가

즉 서드파티 스크립트 최적화의 핵심은 "넣을까 말까"보다 **언제 로드할까**다.

### 우선순위 기준

#### 1) 렌더 이전에 꼭 필요한가

대부분의 분석/채팅/피드백 위젯은 그렇지 않다. 결제 플로우 직전의 결제 SDK처럼 실제 사용자 여정상 필요한 시점이 따로 있는 경우가 많다.

#### 2) route-local 기능인가

문의 페이지에서만 필요한 지도 SDK를 루트에 붙일 이유는 거의 없다. 지원 센터 전용 채팅 위젯도 전체 공개 페이지 공통 번들에 둘 필요가 없다.

#### 3) 사용자 행동 이후 로드해도 되는가

예를 들어 "상담 열기" 버튼을 누른 뒤 위젯을 로드해도 충분하다면, 초기 로드 비용을 크게 줄일 수 있다.

### 실무 패턴

#### 패턴 A. route segment 내부에서만 주입

```tsx
// app/support/layout.tsx
import { SupportChatBoot } from "./support-chat-boot";

export default function SupportLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      {children}
      <SupportChatBoot />
    </>
  );
}
```

```tsx
// app/support/support-chat-boot.tsx
"use client";

import { useEffect } from "react";

export function SupportChatBoot() {
  useEffect(() => {
    import("@/lib/support-chat").then(({ boot }) => boot());
  }, []);

  return null;
}
```

이렇게 하면 적어도 전체 앱 공통 비용으로 새는 것을 막을 수 있다.

#### 패턴 B. 사용자 행동 이후 lazy boot

```tsx
"use client";

import { useState } from "react";

export function OpenSupportButton() {
  const [loading, setLoading] = useState(false);

  async function handleOpen() {
    setLoading(true);
    const { openSupportChat } = await import("@/lib/support-chat");
    await openSupportChat();
    setLoading(false);
  }

  return (
    <button onClick={handleOpen} disabled={loading}>
      {loading ? "상담 열기 준비 중..." : "상담 시작"}
    </button>
  );
}
```

이 패턴은 초기 성능에 특히 유리하다. 사용자가 절대 누르지 않을 수도 있는 위젯을 미리 로드할 필요가 없기 때문이다.

#### 패턴 C. 본문과 무관한 스크립트는 hydration 이후 낮은 우선순위로

광고, 실험, heatmap, 행동 분석처럼 핵심 기능이 아닌 경우는 페이지 인터랙션이 가능한 상태를 먼저 확보하고 붙이는 편이 낫다. 핵심은 "측정"보다 "사용 가능성"이 우선이라는 점이다.

### 흔한 실수

- 모든 페이지에서 동일하게 실행되는 analytics bootstrap 파일에 여러 도구를 같이 묶는다
- route-local widget인데 루트 layout에서 무심코 import한다
- 사용자가 열지 않을 모달/챗봇을 앱 시작과 동시에 로드한다
- third-party script 실행 실패를 페이지 렌더 실패와 같은 수준으로 다룬다

이 영역은 번들 크기뿐 아니라 **메인 스레드 혼잡**까지 영향을 준다. Next.js 앱이 서버 렌더 덕분에 첫 화면은 빨라 보여도, 이후 인터랙션이 굼뜬다면 서드파티 스크립트를 꼭 의심해야 한다.

---

## 핵심 개념 10: 폼, 에디터, 모달은 "처음부터 다 마운트" 대신 "열릴 때 준비" 전략이 더 잘 맞는다

복잡한 B2B 서비스나 관리자 화면에서 자주 만나는 비대한 UI 묶음이 있다.

- 리치 텍스트 에디터
- 파일 업로드 드롭존
- 지도 검색/좌표 선택기
- 대형 설정 모달
- 역할/권한 편집 다이얼로그
- 필드가 수십 개인 생성 폼

이런 UI를 편의상 페이지 안에 기본 렌더로 넣으면 아주 쉽게 클라이언트 비용이 폭증한다.

### 나쁜 예: 모달은 닫혀 있지만, 코드는 이미 다 올라온 상태

```tsx
"use client";

import { Editor } from "@/components/editor";
import { UploadPanel } from "@/components/upload-panel";
import { PlacePickerMap } from "@/components/place-picker-map";

export function PostWritePage() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button onClick={() => setOpen(true)}>새 글 작성</button>
      <Modal open={open} onOpenChange={setOpen}>
        <Editor />
        <UploadPanel />
        <PlacePickerMap />
      </Modal>
    </>
  );
}
```

문제는 모달이 닫혀 있어도, 이 의존성들이 초기 client graph에 포함될 수 있다는 점이다.

### 더 나은 예: 모달 본문 자체를 lazy load

```tsx
"use client";

import dynamic from "next/dynamic";
import { useState } from "react";

const PostWriteDialog = dynamic(() => import("./post-write-dialog"), {
  loading: () => <div className="rounded-xl border p-6">에디터 준비 중...</div>,
});

export function PostWriteEntry() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button onClick={() => setOpen(true)}>새 글 작성</button>
      {open ? <PostWriteDialog open={open} onOpenChange={setOpen} /> : null}
    </>
  );
}
```

그리고 `PostWriteDialog` 내부에서 실제 editor, uploader, map을 조합한다.

이 구조의 장점은 명확하다.

- 사용자가 모달을 열기 전까지 거대한 편집기 코드를 내려보내지 않을 수 있다
- 페이지의 핵심 읽기/탐색 경험과 작성 기능 비용을 분리할 수 있다
- create flow 진입 자체를 명시적 사용자 행동으로 볼 수 있다

### 폼 라이브러리도 범위를 좁혀야 한다

폼이 크다고 해서 페이지 전체를 React Hook Form, Zod resolver, field array 상태와 함께 묶을 필요는 없다.

- 목록 페이지는 서버 렌더 유지
- 생성/수정 폼은 별도 route나 modal entry에서만 클라이언트화
- preview/markdown/editor/attachment 기능은 단계별 lazy load

즉 복잡한 폼은 보통 이렇게 나누는 편이 좋다.

1. 진입 버튼 또는 entry UI  
2. lazy-loaded form shell  
3. 더 무거운 editor/upload/map은 form 안에서도 필요 시 lazy  

실무에서는 이 세 단계 분리만 해도 체감 차이가 크다.

---

## 실무 예시 4: 검색·필터 화면에서 전체 페이지를 client화하지 않고도 좋은 UX를 만드는 방법

검색 화면은 상태가 많아서 쉽게 클라이언트 중심으로 기울어진다.

- 검색어
- 정렬
- 필터
- 페이지네이션
- 저장된 검색 조건
- 결과 카드 hover/selection
- 북마크 토글

많은 팀이 이 때문에 아예 페이지 전체를 client component로 만든다. 하지만 대부분의 검색 화면은 서버 중심으로도 충분히 좋은 UX를 만들 수 있다.

### 구조 원칙

#### 1) 검색 조건은 search params로

검색어, 정렬, 필터는 공유/복구 가치가 크다. URL에 올리면 서버 컴포넌트가 해당 상태로 결과를 바로 렌더할 수 있다.

#### 2) 결과 목록은 서버 렌더 우선

검색 결과 자체는 대개 읽기 데이터다. 카드 hover나 저장 버튼 때문에 전체 grid를 클라이언트화할 이유는 약하다.

#### 3) 카드 단위 인터랙션만 island화

예를 들어 북마크 버튼만 작은 client component로 빼면 된다.

```tsx
// components/search-result-card.tsx
import { BookmarkButton } from "./bookmark-button";

export function SearchResultCard({ item }: { item: SearchItem }) {
  return (
    <article>
      <h2>{item.title}</h2>
      <p>{item.summary}</p>
      <BookmarkButton itemId={item.id} initialBookmarked={item.bookmarked} />
    </article>
  );
}
```

```tsx
// components/bookmark-button.tsx
"use client";

import { useOptimistic, useTransition } from "react";
import { toggleBookmark } from "@/app/actions/bookmark";

export function BookmarkButton({
  itemId,
  initialBookmarked,
}: {
  itemId: string;
  initialBookmarked: boolean;
}) {
  const [optimisticValue, setOptimisticValue] = useOptimistic(initialBookmarked);
  const [pending, startTransition] = useTransition();

  return (
    <button
      disabled={pending}
      onClick={() => {
        startTransition(async () => {
          setOptimisticValue(!optimisticValue);
          await toggleBookmark(itemId);
        });
      }}
    >
      {optimisticValue ? "저장됨" : "저장"}
    </button>
  );
}
```

이 구조에서는 검색 결과 자체의 SEO/초기 렌더 이점을 유지하면서, 카드별 인터랙션만 선택적으로 hydration한다.

### 언제 React Query/SWR가 필요한가

실시간 필터 조합, 매우 잦은 refetch, 무한스크롤, optimistic cache merge가 핵심이면 클라이언트 상태 라이브러리가 더 적합할 수 있다. 다만 그 경우에도 전체 앱 공통으로 끌고 갈지, 검색 route subtree 안에만 둘지는 별도 판단해야 한다.

중요한 건 "검색 화면이니까 당연히 client"가 아니라,

> **어떤 상호작용이 실시간이어야 하고, 어떤 결과는 서버 왕복 기반이어도 충분한가**

를 구분하는 것이다.

---

## 실무 예시 5: App Router 마이그레이션에서 번들 최적화를 함께 가져가는 방법

기존 Pages Router 또는 SPA 스타일 코드베이스를 App Router로 옮길 때 흔한 실패 패턴이 있다. 경로만 `app/` 으로 옮기고 구조는 그대로 두는 것이다.

- 기존 page-level client component를 그대로 옮긴다
- `getServerSideProps` 로 하던 읽기를 이제 client `useEffect` 로 바꾼다
- 공용 layout/provider 구조도 그대로 유지한다
- 결과적으로 App Router를 쓰지만 실제로는 여전히 SPA처럼 동작한다

### 점진적 마이그레이션 전략

#### 1) 읽기 페이지부터 서버 우선으로 바꾼다

상품 상세, 블로그 상세, 마케팅 페이지, 문서 페이지처럼 읽기 중심 화면은 가장 먼저 서버 컴포넌트로 전환하기 좋다.

#### 2) 페이지 전체 client component를 바로 없애기 어렵다면, 섹션별로 경계를 만든다

예를 들어 기존 DashboardPage가 전부 client라면 다음처럼 나눌 수 있다.

- 서버 wrapper page
- client filter island
- server KPI section
- dynamic chart section
- client table controls

즉 한 번에 완전 재작성하지 않아도, 큰 경계를 잘라나가며 점진적으로 개선할 수 있다.

#### 3) provider migration을 별도 작업으로 본다

이 작업을 빼먹으면 경로를 옮겨도 공통 번들 구조는 거의 그대로 남는다. `app/layout.tsx` 와 각 route group layout을 먼저 도식화해보면 어디서 비용이 새는지 잘 보인다.

#### 4) bundle review를 코드 리뷰 항목에 넣는다

App Router 전환 초기에만 잠깐 최적화하고 끝내면 다시 무너진다. 새 기능 PR에서 아래를 같이 보면 효과가 좋다.

- 왜 `use client` 가 필요한가?
- 이 provider는 정말 루트에 있어야 하는가?
- dynamic import로 뒤로 미룰 수 있는 기능인가?
- 서버에서 읽을 수 있는 데이터를 클라이언트로 재요청하고 있지 않은가?

App Router 도입의 진짜 가치는 폴더 구조가 아니라 **이 질문을 자연스럽게 하게 만든다**는 데 있다.

---

## 코드 리뷰에서 바로 쓰는 질문 12개

번들 최적화는 한 번의 큰 리팩터링보다, 반복적인 코드 리뷰 습관으로 유지되는 경우가 많다. 아래 질문은 실제 리뷰에서 바로 쓸 수 있다.

1. 이 파일의 `use client` 는 정말 필요한가?  
2. 버튼/토글 하나 때문에 큰 본문 블록이 통째로 client tree가 된 것은 아닌가?  
3. root layout 또는 공통 provider에 이 기능이 왜 올라가 있는가?  
4. search params로 표현 가능한 상태를 local state로만 들고 있지 않은가?  
5. 이 라이브러리는 초기 진입 시점에 꼭 필요한가?  
6. editor, chart, map, pdf viewer는 dynamic import 후보가 아닌가?  
7. `ssr: false` 를 쓴 이유가 브라우저 의존 때문인지, 단순 편의 때문인지 명확한가?  
8. 서버에서 렌더 가능한 텍스트/마크업/포맷팅까지 클라이언트에 맡기고 있지 않은가?  
9. 전역 store 구독 범위가 필요 이상으로 넓지 않은가?  
10. barrel export가 경계를 흐려서 의존성을 불필요하게 끌고 오지 않는가?  
11. third-party script는 route-local 또는 interaction-triggered 로 미룰 수 없는가?  
12. 이 변경이 route별 First Load JS와 hydration 범위에 어떤 영향을 주는지 설명 가능한가?  

이 질문들의 목적은 팀을 느리게 만드는 것이 아니다. 오히려 기능 구현 당시 바로 경계 비용을 드러내서, 나중의 큰 리팩터링 비용을 줄이는 데 있다.

---

## 언제 굳이 최적화하지 않아도 되는가

성능 이야기를 하면 모든 UI를 최대한 잘게 쪼개야 할 것처럼 느껴질 수 있다. 하지만 실제로는 그렇지 않다.

### 굳이 과최적화하지 않아도 되는 경우

- 내부 전용 간단한 페이지이고 실제 사용 빈도가 낮다
- 무거운 라이브러리가 거의 없고, hydration 범위도 작다
- route-local client component지만 초기 진입 UX에 거의 영향이 없다
- 최적화 복잡도가 체감 이득보다 크다

예를 들어 관리자 설정의 작은 보조 페이지 하나를 서버/클라이언트로 지나치게 쪼개는 것은 오히려 가독성을 해칠 수 있다.

핵심은 다음과 같다.

- **공개 트래픽이 많고 첫인상이 중요한 화면**은 적극 최적화  
- **무거운 기능성 라이브러리**가 들어가는 화면은 구조 점검 필수  
- **작고 빈도 낮은 내부 화면**은 합리적 수준에서 유지  

즉 최적화는 교조적으로 적용하는 규칙이 아니라, **비용 대비 효과를 보는 설계 판단**이다.

---

## 트레이드오프: 클라이언트 경계를 작게 만들수록 성능은 좋아지기 쉽지만, 코드 구조는 더 세밀해진다

좋은 구조는 공짜가 아니다. RSC 경계를 잘게 잡으면 얻는 것도 크지만 비용도 있다.

### 얻는 것

1. **초기 번들 감소**  
   브라우저가 받아야 할 JS 양이 줄어든다.

2. **Hydration 범위 축소**  
   연결해야 할 컴포넌트 트리가 줄어든다.

3. **서버 우선 데이터 흐름**  
   읽기 로직이 단순해지고 보안/SEO에 유리하다.

4. **기능 단위 분리**  
   어떤 부분이 인터랙션이고 어떤 부분이 콘텐츠인지 구조가 선명해진다.

5. **경로별 최적화 유연성**  
   admin, marketing, blog, app shell을 다르게 설계하기 쉽다.

### 치르는 비용

1. **컴포넌트 수와 파일 수 증가**  
   같은 화면도 server wrapper + client island로 분리된다.

2. **props 설계와 직렬화 고려 필요**  
   함수 전달, 복잡 객체 공유가 자유롭지 않다.

3. **공용 컴포넌트 추상화 난도 상승**  
   "어디서든 쓸 수 있는 하나의 컴포넌트"보다, 서버용/클라이언트용 책임을 나눠야 할 수 있다.

4. **동료 학습 비용**  
   팀 전체가 RSC 경계를 이해하지 못하면 오히려 혼란이 생긴다.

5. **지나친 최적화 유혹**  
   실제 체감 이득이 작은 곳까지 지나치게 쪼개면 개발 생산성과 가독성이 나빠질 수 있다.

### 실무적으로 좋은 균형

보통 아래 기준이 현실적이다.

- 공개 페이지, 콘텐츠 페이지, 랜딩 페이지는 서버 우선으로 강하게 가져간다
- 관리자/복잡한 app shell은 route segment 단위로 provider와 client 영역을 제한한다
- 아주 작은 인터랙션은 leaf island로 둔다
- 무거운 기능성 라이브러리는 dynamic import를 적극 검토한다
- 성능 개선이 미미한 과최적화는 피한다

즉 최적화의 목표는 "클라이언트 코드를 0으로 만든다"가 아니라,

> **클라이언트 코드를 “필요한 범위와 시점”으로 밀어 넣는 것**

이다.

---

## 흔한 실수

### 1) 페이지 파일에 습관적으로 `use client` 를 붙인다

초기 개발 속도는 빠르지만, 장기적으로는 거의 항상 비싼 선택이다. 페이지 전체가 client tree가 되는 순간 서버 컴포넌트 이점을 많이 잃는다.

### 2) 버튼 하나 때문에 큰 본문 컴포넌트를 통째로 클라이언트화한다

상세 설명, 카드 본문, FAQ 내용, 문서 본문은 서버에 두고 버튼/토글/폼만 작은 island로 빼는 편이 훨씬 낫다.

### 3) root layout provider에 모든 상태 라이브러리를 몰아넣는다

테마 외에는 정말 전역인지 다시 확인해야 한다. 특히 React Query, 모달 시스템, 커맨드 팔레트, 관리자 전용 상태는 segment 아래로 내릴 수 있는 경우가 많다.

### 4) Dynamic Import를 성능 만능키처럼 쓴다

필수 above-the-fold UI까지 dynamic으로 쪼개면 오히려 늦고 흔들리는 UX가 된다. 초기 사용자 여정에서 제외 가능한 것에 집중해야 한다.

### 5) `ssr: false` 로 브라우저 전용 에러를 쉽게 덮는다

당장은 편하지만, 서버 렌더 포기와 레이아웃 점프, SEO 손실이 뒤따를 수 있다. 정말 브라우저 전용일 때만 제한적으로 써야 한다.

### 6) search/filter 상태를 전부 클라이언트 local state에 둔다

URL state로 올릴 수 있는데도 `useState` 로만 처리하면, 서버 컴포넌트와의 정합성이 끊기고 페이지 전체 client화로 이어지기 쉽다.

### 7) 리스트 전체를 클라이언트 렌더링으로 전환한다

좋아요 버튼, hover 효과, 드롭다운 메뉴 때문에 100개 카드 전체가 hydration 대상이 되는 구조는 매우 흔한 실수다.

### 8) 공용 barrel export로 서버/클라이언트 경계를 흐린다

편한 import 경험 때문에 모듈 경계가 무너지고, 생각보다 큰 의존성이 client graph에 섞이는 경우가 있다.

### 9) 번들 크기만 보고 hydration 범위를 보지 않는다

같은 KB라도 넓은 client subtree는 CPU와 인터랙션 비용이 더 크다. 숫자와 구조를 함께 봐야 한다.

### 10) 관리자 화면은 성능 최적화를 덜 해도 된다고 생각한다

대시보드는 차트, 테이블, 필터, export, modal이 많아서 오히려 번들 비대화가 가장 빠르게 일어난다.

---

## 실무 체크리스트

### 1) RSC 경계 점검

- [ ] `page.tsx`, `layout.tsx` 에 불필요한 `use client` 가 없는가?
- [ ] 인터랙션이 필요한 부분만 leaf client island로 분리했는가?
- [ ] 버튼/폼 때문에 큰 본문 블록이 통째로 클라이언트화되지 않았는가?
- [ ] 서버에서 읽을 수 있는 데이터는 서버 컴포넌트에서 해결하고 있는가?

### 2) Provider 구조 점검

- [ ] root provider에 정말 전역인 것만 남아 있는가?
- [ ] React Query, modal, command palette, admin state를 segment 아래로 내릴 수 없는가?
- [ ] provider 파일 하나에 너무 많은 라이브러리가 몰려 있지 않은가?
- [ ] root layout이 client boundary가 되어 공통 번들을 키우지 않는가?

### 3) Dynamic Import 점검

- [ ] 차트, 에디터, 맵, PDF viewer 같은 heavy feature를 on-demand 로딩하고 있는가?
- [ ] 초기 핵심 CTA까지 과하게 lazy 처리하지 않았는가?
- [ ] `ssr: false` 를 정말 필요한 곳에만 쓰고 있는가?
- [ ] loading fallback이 실제 UX를 해치지 않는가?

### 4) 상태 설계 점검

- [ ] 공유 가치 있는 필터/정렬 상태를 URL search params로 올렸는가?
- [ ] 읽기 데이터와 UI 인터랙션 상태를 분리했는가?
- [ ] 전역 store 구독 범위가 지나치게 넓지 않은가?
- [ ] 리스트 전체가 작은 인터랙션 때문에 client tree가 되지 않았는가?

### 5) import 습관 점검

- [ ] 아이콘/유틸/barrel export가 불필요한 의존성을 끌고 오지 않는가?
- [ ] 서버 전용 유틸에 `server-only` 를 붙여 경계 실수를 막고 있는가?
- [ ] markdown/highlight/date/chart 라이브러리를 정말 클라이언트에서 써야 하는가?
- [ ] route-local 기능이 공통 chunk로 새지 않는가?

### 6) 측정 점검

- [ ] 경로별 First Load JS 차이를 보고 있는가?
- [ ] bundle analyzer 숫자뿐 아니라 왜 해당 모듈이 포함됐는지 추적하는가?
- [ ] 저사양 기기에서 hydration 후 인터랙션 지연을 확인했는가?
- [ ] 최적화 후 UX가 더 좋아졌는지, 단순히 숫자만 줄었는지 구분했는가?

---

## 적용 순서 제안: 성능 이슈가 있는 페이지를 어떻게 리팩터링할까

실제 프로젝트에서 한 번에 다 뜯어고치기 어렵다면 아래 순서가 현실적이다.

### 1단계. 가장 큰 `use client` 부터 찾는다

페이지, 레이아웃, 대형 섹션 컴포넌트에 붙은 `use client` 를 먼저 본다. 버튼 하나, 필터 하나, 토글 하나 때문에 전체가 클라이언트화된 경우가 많다.

### 2단계. 읽기와 상호작용을 분리한다

서버에서 읽을 수 있는 데이터는 서버로 돌리고, 클라이언트 상태는 작은 island로 빼낸다.

### 3단계. root provider를 점검한다

루트에 있는 provider 중 실제 전역이 아닌 것을 route segment 아래로 내린다.

### 4단계. heavy library를 on-demand로 미룬다

차트, 에디터, 모달 폼, 분석 도구처럼 큰 기능성 코드를 dynamic import로 분리한다.

### 5단계. URL state로 올릴 수 있는 것은 올린다

필터, 정렬, 탭, 페이지네이션을 search params 기반으로 옮기면 서버 컴포넌트와 경계가 더 잘 맞는다.

### 6단계. 측정으로 검증한다

경로별 First Load JS, hydration 지연, route transition 체감, chunk 분리 상태를 확인한다. 숫자와 실제 UX 둘 다 봐야 한다.

이 순서는 단순하지만 효과가 좋다. 특히 1, 2, 3단계만 해도 번들 구조가 크게 개선되는 경우가 많다.

---

## 한 줄 정리

Next.js 번들 최적화의 핵심은 라이브러리 몇 개를 lazy load하는 기술이 아니다. **RSC 경계를 통해 읽기와 인터랙션을 분리하고, `use client` 의 범위를 leaf로 좁히며, 정말 늦게 받아도 되는 코드만 dynamic import로 미루어 브라우저가 책임지는 JavaScript와 hydration 면적 자체를 줄이는 것**이다.
