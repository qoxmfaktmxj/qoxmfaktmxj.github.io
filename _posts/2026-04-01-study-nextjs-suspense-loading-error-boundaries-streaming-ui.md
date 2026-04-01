---
layout: post
title: "Next.js Suspense·loading.tsx·error.tsx 실전: 스트리밍 UI와 장애 격리 설계 기준"
date: 2026-04-01 11:40:00 +0900
categories: [nextjs]
tags: [study, nextjs, suspense, loading, error-boundary, streaming-ui, app-router]
---

## 배경: 페이지는 하나인데, 사용자는 절대 하나의 로딩 상태로 느끼지 않는다

App Router로 넘어온 팀이 초기에 가장 자주 만드는 안티패턴 중 하나는 화면 전체를 하나의 `isLoading` 으로 다루는 것이다.

- 서버 컴포넌트에서 데이터 3개를 읽는다
- 하나라도 늦으면 페이지 전체를 스피너로 가린다
- 일부 위젯만 실패해도 전체 페이지를 에러 화면으로 보낸다
- 사용자는 “조금 늦지만 안정적인 화면”이 아니라 “아무 것도 안 보이다가 한 번에 뜨는 화면”을 보게 된다

문제는 Next.js App Router가 이미 이런 문제를 해결할 수 있는 도구를 제공하는데도, 많은 팀이 이를 **문법 단위**로만 알고 있다는 점이다.

- `Suspense` → 그냥 fallback 보여주는 컴포넌트
- `loading.tsx` → 페이지 로딩 파일
- `error.tsx` → 에러 나면 보여주는 파일
- 스트리밍 → 뭔가 AI 응답에만 쓰는 기능

실무에서는 전부 다르게 봐야 한다.

> `Suspense`, `loading.tsx`, `error.tsx` 의 핵심은 “로딩 UI 예쁘게 만들기”가 아니라, **느린 부분과 실패하는 부분을 화면에서 어디까지 격리할지 설계하는 것**이다.

특히 중급 이상 개발자가 App Router를 운영 단계까지 가져가면 아래 문제가 반복된다.

- 대시보드 상단 KPI만 늦어도 전체 페이지가 늦게 뜬다
- 추천 영역 API가 실패했는데 상품 상세 전체가 500처럼 보인다
- 초기 진입은 빠른데 클라이언트 hydration 이후 레이아웃 점프가 심하다
- `loading.tsx` 를 과하게 써서 skeleton이 계속 깜빡인다
- `error.tsx` 가 잡는 범위를 몰라서 일부 위젯 오류와 페이지 치명 오류를 구분하지 못한다
- Suspense 경계를 너무 잘게 쪼개 waterfall을 만들거나, 반대로 너무 크게 묶어 병목을 만든다

이 글은 `Suspense` 문법 소개가 아니다. 목표는 다음 질문에 답하는 것이다.

> **Next.js에서 느린 데이터, 부분 실패, 초기 체감 속도, 재시도 UX를 어떤 경계 단위로 설계해야 하는가?**

이를 위해 아래 순서로 정리한다.

1. `Suspense`, `loading.tsx`, `error.tsx` 가 각각 무슨 문제를 푸는지
2. 경계를 어디에 두어야 스트리밍 UI가 실제로 빨라지는지
3. 대시보드/상세/검색 화면에서 어떻게 쪼개야 하는지
4. 흔한 실수와 운영 체크리스트

핵심은 하나다. **페이지를 렌더링하는 것이 아니라, 사용자가 기다림과 실패를 어떻게 체감할지 설계하는 것**이다.

---

## 먼저 큰 그림: Suspense, loading.tsx, error.tsx 는 서로 대체재가 아니라 다른 층의 도구다

세 도구를 한 문장으로 정리하면 이렇다.

- `Suspense` 는 **느린 하위 트리를 어떤 fallback으로 감쌀지** 정한다
- `loading.tsx` 는 **라우트 세그먼트 진입 시 기본 Suspense 대기 화면**을 제공한다
- `error.tsx` 는 **해당 세그먼트 하위에서 발생한 렌더링 오류를 복구 가능한 UI로 감싼다**

즉 셋은 같은 종류가 아니다.

### 1) Suspense: “이 부분은 늦을 수 있으니 일단 다른 UI를 먼저 보여주자”

가장 중요한 도구다. Suspense 경계 안의 하위 트리가 아직 준비되지 않았을 때 fallback을 먼저 내보내고, 준비되면 실제 UI로 교체한다.

```tsx
import { Suspense } from "react";

export default function DashboardPage() {
  return (
    <main>
      <Header />
      <Suspense fallback={<KpiSkeleton />}>
        <KpiSection />
      </Suspense>
      <Suspense fallback={<ActivitySkeleton />}>
        <RecentActivitySection />
      </Suspense>
    </main>
  );
}
```

여기서 본질은 단순한 로딩 표시가 아니다.

- 헤더는 바로 보여준다
- KPI가 늦어도 최근 활동은 먼저 뜰 수 있다
- 최근 활동이 늦어도 페이지 전체가 막히지 않는다

즉 Suspense는 **부분 준비(partial readiness)** 를 화면에 반영하는 장치다.

### 2) loading.tsx: “이 세그먼트가 열릴 때 기본적으로 무엇을 먼저 보여줄까?”

`app/dashboard/loading.tsx` 는 해당 라우트 세그먼트가 처음 열릴 때 보여줄 기본 로딩 UI를 정의한다.

```tsx
// app/dashboard/loading.tsx
export default function Loading() {
  return <DashboardPageSkeleton />;
}
```

이 파일은 특히 **route transition** 과 잘 맞는다.

- 사용자가 다른 경로에서 `/dashboard` 로 이동했다
- 해당 세그먼트 데이터가 아직 준비되지 않았다
- 그러면 Next.js가 이 로딩 UI를 먼저 스트리밍할 수 있다

즉 `loading.tsx` 는 페이지 내부 위젯 단위가 아니라 **라우트 세그먼트 단위의 초기 대기 UX** 에 가깝다.

### 3) error.tsx: “실패를 500 한 장으로 끝내지 말고, 이 범위에서 복구 가능하게 만들자”

`error.tsx` 는 해당 세그먼트 하위 렌더링 오류를 잡아 복구 UI를 제공한다.

```tsx
"use client";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div>
      <h2>대시보드를 불러오는 중 문제가 발생했습니다.</h2>
      <button onClick={() => reset()}>다시 시도</button>
    </div>
  );
}
```

실무적으로 중요한 점은 두 가지다.

- 모든 실패를 글로벌 에러 페이지로 보내지 않아도 된다
- 사용자가 같은 문맥 안에서 재시도할 수 있다

즉 `error.tsx` 의 본질은 **실패를 국소화(localize)하고 복구 UX를 제공하는 것**이다.

---

## 핵심 개념 1: 스트리밍 UI의 출발점은 “빨리 렌더링”이 아니라 “먼저 보여도 되는 것과 기다려야 하는 것을 분리”하는 것이다

팀이 Suspense를 도입하고도 체감 속도가 좋아지지 않는 가장 큰 이유는, 실제로는 아무 것도 분리하지 않았기 때문이다.

예를 들어 아래 코드는 얼핏 비동기처럼 보이지만 사용자 체감상 거의 개선이 없다.

```tsx
export default async function DashboardPage() {
  const [profile, kpis, activities, recommendations] = await Promise.all([
    getProfile(),
    getKpis(),
    getActivities(),
    getRecommendations(),
  ]);

  return (
    <main>
      <ProfileCard profile={profile} />
      <KpiSection data={kpis} />
      <ActivitySection data={activities} />
      <RecommendationSection data={recommendations} />
    </main>
  );
}
```

`Promise.all` 자체는 병렬화에 유리하지만, 결국 **모든 데이터가 준비될 때까지 페이지 루트가 기다린다**. 즉 느린 추천 영역 하나가 전체 화면의 첫 페인트를 늦출 수 있다.

스트리밍 UI로 바꾸려면 먼저 질문이 바뀌어야 한다.

- 프로필은 가장 먼저 보여야 하는가?
- KPI와 최근 활동은 서로 독립적으로 먼저 떠도 되는가?
- 추천 위젯은 늦어도 되는가?
- 일부 영역이 실패해도 페이지 본문은 살아 있어야 하는가?

이 기준으로 쪼개면 구조가 달라진다.

```tsx
import { Suspense } from "react";

export default async function DashboardPage() {
  const profile = await getProfile();

  return (
    <main>
      <ProfileCard profile={profile} />

      <section className="grid gap-6 lg:grid-cols-2">
        <Suspense fallback={<KpiSkeleton />}>
          <KpiSection />
        </Suspense>

        <Suspense fallback={<ActivitySkeleton />}>
          <ActivitySection />
        </Suspense>
      </section>

      <Suspense fallback={<RecommendationSkeleton />}>
        <RecommendationSection />
      </Suspense>
    </main>
  );
}
```

이 구조가 실무적으로 강한 이유는 다음과 같다.

1. **사용자가 가장 먼저 봐야 할 정보**를 먼저 보여줄 수 있다  
2. 느린 영역을 후순위로 밀 수 있다  
3. 실패나 지연이 전체 페이지에 전염되지 않는다  
4. skeleton을 실제 정보 구조에 맞게 설계할 수 있다  

즉 Suspense는 성능 최적화 이전에 **우선순위 설계 도구**다.

---

## 핵심 개념 2: loading.tsx 는 “페이지 전체 스피너” 파일이 아니라 라우트 전환 시점의 첫인상 설계다

많은 프로젝트에서 `loading.tsx` 는 거대한 전체 페이지 skeleton 한 장으로 끝난다. 문제는 이렇게 만들면 route transition 때는 그럴듯해 보여도, 내부 Suspense 경계와 합쳐졌을 때 오히려 깜빡임과 중복 로딩이 생기기 쉽다는 점이다.

### 언제 loading.tsx 가 특히 유효한가

`loading.tsx` 가 가장 잘 맞는 경우는 아래다.

- 사용자가 **새로운 세그먼트로 이동**하는 순간
- 그 세그먼트의 핵심 구조를 먼저 보여주는 것이 중요할 때
- 아직 상세 데이터는 없어도 레이아웃의 윤곽은 먼저 보여줄 수 있을 때

예를 들어 상품 상세 페이지라면 사용자는 보통 아래 정도를 먼저 봐도 괜찮다.

- 상단 헤더
- 좌측 이미지 영역 자리
- 우측 제목/가격/CTA 자리
- 하단 리뷰 탭 자리

```tsx
// app/products/[id]/loading.tsx
export default function Loading() {
  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <div className="grid gap-8 lg:grid-cols-[1.2fr_1fr]">
        <div className="aspect-square animate-pulse rounded-2xl bg-neutral-200" />
        <div className="space-y-4">
          <div className="h-6 w-24 animate-pulse rounded bg-neutral-200" />
          <div className="h-10 w-3/4 animate-pulse rounded bg-neutral-200" />
          <div className="h-8 w-1/3 animate-pulse rounded bg-neutral-200" />
          <div className="h-12 w-full animate-pulse rounded-xl bg-neutral-200" />
        </div>
      </div>
    </main>
  );
}
```

이렇게 하면 사용자는 “아직 불러오는 중”이 아니라 **화면이 어떤 구조로 올지 이미 파악한 상태**에서 기다리게 된다.

### 언제 loading.tsx 가 과해지는가

반대로 아래 경우에는 `loading.tsx` 가 과하다.

- 세그먼트 전체를 막을 정도가 아니라 일부 위젯만 늦을 때
- 내부 Suspense가 이미 충분히 잘게 설계되어 있을 때
- 로딩 skeleton이 실제 콘텐츠보다 더 무겁거나 복잡할 때
- 이동할 때마다 전체 골격이 깜빡이며 재등장할 때

실무 기준으로 `loading.tsx` 는 **세그먼트 첫 진입의 기본 골격** 정도로 생각하는 편이 좋다. 세부 위젯 로딩까지 다 여기서 해결하려고 하면, 경계 책임이 흐려진다.

### 좋은 loading.tsx 의 기준

- 실제 레이아웃과 비슷한 구조를 가진다
- 텍스트 길이, 카드 밀도, 주요 CTA 위치가 크게 다르지 않다
- 너무 정교해서 관리 비용이 높아지지 않는다
- 내부 Suspense fallback 과 역할이 겹치지 않는다
- CLS를 줄이는 방향으로 크기가 안정적이다

즉 `loading.tsx` 는 “없으면 허전하니 하나 넣는 파일”이 아니라 **라우트 전환 시 사용자 시선을 붙잡는 구조적 placeholder** 다.

---

## 핵심 개념 3: Suspense 경계는 데이터 fetch 단위가 아니라 사용자 인지 단위로 나눠야 한다

초보적인 Suspense 분리는 보통 이렇게 간다.

- API 하나당 Suspense 하나
- 컴포넌트 하나당 Suspense 하나
- 느려 보이는 곳마다 일단 fallback 추가

이 방식은 쉽게 waterfall과 깜빡임을 만든다. 왜냐하면 사용자는 API 경계를 인지하지 않기 때문이다. 사용자는 **영역, 목적, 중요도**를 인지한다.

### 나쁜 기준: 기술 단위 분해

```tsx
<Suspense fallback={<div>users...</div>}>
  <UsersCount />
</Suspense>
<Suspense fallback={<div>orders...</div>}>
  <OrdersCount />
</Suspense>
<Suspense fallback={<div>sales...</div>}>
  <SalesAmount />
</Suspense>
```

KPI 카드 3개가 사실상 한 묶음으로 보이는 UI라면, 이런 분리는 오히려 카드가 하나씩 뒤늦게 들어오며 불안정해 보일 수 있다.

### 더 나은 기준: 인지적으로 함께 보이는 덩어리 단위

```tsx
<Suspense fallback={<KpiGroupSkeleton />}>
  <KpiGroup />
</Suspense>
```

그리고 `KpiGroup` 내부에서는 필요한 데이터를 병렬로 읽게 한다.

```tsx
export async function KpiGroup() {
  const [users, orders, sales] = await Promise.all([
    getUsersCount(),
    getOrdersCount(),
    getSalesAmount(),
  ]);

  return (
    <div className="grid gap-4 md:grid-cols-3">
      <KpiCard label="사용자" value={users} />
      <KpiCard label="주문" value={orders} />
      <KpiCard label="매출" value={sales} />
    </div>
  );
}
```

이게 나은 이유는 명확하다.

- 사용자는 세 카드가 하나의 정보 블록으로 보인다
- skeleton도 그 구조에 맞춰 안정적으로 설계할 수 있다
- 일부 카드만 늦게 튀어나오는 어색함이 줄어든다

### 경계 분리 질문 5가지

실무에서 Suspense 경계를 나눌 때는 아래 질문이 유용하다.

1. 사용자가 이 영역들을 **한 묶음**으로 인식하는가?  
2. 하나가 늦어도 다른 영역을 **먼저 보여주는 것이 자연스러운가**?  
3. fallback이 실제 UI의 레이아웃을 얼마나 안정적으로 대체하는가?  
4. 실패했을 때 이 범위만 따로 재시도하는 UX가 자연스러운가?  
5. 너무 잘게 쪼개서 화면이 조각조각 들어오는 인상을 만들지 않는가?  

즉 Suspense는 코드 구조가 아니라 **화면 의미 구조**에 맞춰야 한다.

---

## 핵심 개념 4: error.tsx 의 본질은 “치명적 실패”와 “국소 실패”를 구분하는 것이다

대부분의 서비스 화면은 모든 하위 영역이 동시에 필수는 아니다.

예를 들어 상품 상세에서 아래를 생각해보자.

- 상품 기본 정보
- 재고/가격
- 추천 상품
- 최근 본 상품
- 리뷰 요약
- Q&A 위젯

이 중 추천 상품 API 하나 실패했다고 상세 전체를 깨뜨리는 것은 대개 과하다. 반대로 상품 기본 정보나 권한 검증 실패는 페이지 수준에서 막는 것이 맞다.

즉 에러 설계의 핵심은 이것이다.

- **없으면 안 되는 것** → 상위 세그먼트/상위 경계에서 처리
- **없어도 본 기능은 살아 있는 것** → 하위 경계에서 처리

### 세그먼트 에러와 위젯 에러를 구분하자

예를 들어 `app/products/[id]/error.tsx` 는 상세 세그먼트 전체 실패에 가깝다.

- 잘못된 상품 ID
- 권한 없음
- 필수 데이터 소스 장애
- 치명적인 서버 렌더링 오류

반면 추천 영역처럼 부가 정보는 컴포넌트 레벨에서 자체 처리하는 편이 더 낫다.

```tsx
import { Suspense } from "react";

export default async function ProductDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const product = await getProductOrThrow(id);

  return (
    <main>
      <ProductHero product={product} />

      <Suspense fallback={<ReviewSummarySkeleton />}>
        <ReviewSummary productId={id} />
      </Suspense>

      <Suspense fallback={<RecommendationSkeleton />}>
        <RecommendationPanel productId={id} />
      </Suspense>
    </main>
  );
}
```

여기서 `RecommendationPanel` 안쪽에서 에러를 삼켜 빈 상태/안내 문구로 낮출 수도 있다.

```tsx
export async function RecommendationPanel({ productId }: { productId: string }) {
  try {
    const items = await getRecommendations(productId);

    if (items.length === 0) {
      return <EmptyRecommendationState />;
    }

    return <RecommendationCarousel items={items} />;
  } catch {
    return <RecommendationFallbackNotice />;
  }
}
```

이렇게 하면 핵심 상세 경험은 살아 있고, 부가 기능만 낮은 수준으로 degrade 된다.

### 좋은 error.tsx 는 무엇을 제공해야 하는가

`error.tsx` 에는 보통 네 가지가 필요하다.

1. 사용자가 이해할 수 있는 실패 맥락  
2. 현재 문맥을 잃지 않는 재시도 버튼  
3. 너무 기술적인 정보는 숨기되, 운영 추적용 식별자는 남길 수 있는 구조  
4. 복구 불가능한 경우의 대체 이동 경로  

```tsx
"use client";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="rounded-2xl border p-6">
      <h2 className="text-xl font-semibold">상세 정보를 불러오지 못했습니다.</h2>
      <p className="mt-2 text-sm text-neutral-600">
        잠시 후 다시 시도해 주세요. 문제가 반복되면 목록으로 돌아가 다른 상품을 확인해 보세요.
      </p>
      <div className="mt-4 flex gap-3">
        <button onClick={() => reset()}>다시 시도</button>
        <a href="/products">목록으로 이동</a>
      </div>
      {error.digest ? (
        <p className="mt-3 text-xs text-neutral-400">오류 추적 ID: {error.digest}</p>
      ) : null}
    </div>
  );
}
```

중요한 것은 `error.tsx` 를 단순한 실패 알림이 아니라 **복구 화면** 으로 보는 관점이다.

---

## 핵심 개념 5: 스트리밍 UI가 실제로 빨라지려면 fetch 병렬화와 Suspense 배치를 함께 설계해야 한다

Suspense를 붙였는데도 체감 속도가 개선되지 않는 또 다른 이유는, 내부 데이터 읽기 구조가 여전히 waterfall이기 때문이다.

예를 들어 아래는 좋지 않다.

```tsx
export async function DashboardInsights() {
  const summary = await getSummary();
  const anomalies = await getAnomalies(summary.id);
  const trends = await getTrends(summary.id);

  return <Insights summary={summary} anomalies={anomalies} trends={trends} />;
}
```

이 경우 `summary` 가 끝나야 anomalies/trends 가 시작된다. 정말 의존성이 있어서 어쩔 수 없다면 괜찮지만, 아닌데도 습관적으로 이런 구조를 만들면 Suspense 경계는 있어도 실제 시간은 줄지 않는다.

### 병렬화 가능한 것은 먼저 시작하라

```tsx
export async function DashboardInsights() {
  const summaryPromise = getSummary();
  const trendPromise = getGlobalTrends();
  const anomalyPromise = getRecentAnomalies();

  const [summary, trends, anomalies] = await Promise.all([
    summaryPromise,
    trendPromise,
    anomalyPromise,
  ]);

  return <Insights summary={summary} trends={trends} anomalies={anomalies} />;
}
```

그리고 이 블록 자체를 Suspense로 감싼다.

```tsx
<Suspense fallback={<InsightsSkeleton />}>
  <DashboardInsights />
</Suspense>
```

### 상위에서 await 하지 말고, 하위에서 기다리게 하라

App Router에서 흔한 병목은 페이지 루트가 너무 많은 것을 먼저 `await` 해버리는 것이다.

```tsx
// 나쁜 예: 루트가 모든 준비를 기다린다
export default async function Page() {
  const user = await getUser();
  const analytics = await getAnalytics();
  const feed = await getFeed();

  return <Dashboard user={user} analytics={analytics} feed={feed} />;
}
```

이 구조는 Suspense를 써도 대부분 소용이 없다. 차라리 이렇게 나누는 편이 낫다.

```tsx
import { Suspense } from "react";

export default async function Page() {
  const user = await getUser();

  return (
    <main>
      <UserHeader user={user} />

      <Suspense fallback={<AnalyticsSkeleton />}>
        <AnalyticsSection />
      </Suspense>

      <Suspense fallback={<FeedSkeleton />}>
        <FeedSection />
      </Suspense>
    </main>
  );
}
```

즉 스트리밍 UI의 성패는 Suspense 컴포넌트 추가 여부보다, **무엇을 어디서 기다리게 할지** 에 달려 있다.

---

## 실무 예시 1: 관리자 대시보드 — “모든 카드를 동시에 빨리 보여주는 것”보다 “핵심 블록을 우선 노출”하는 편이 낫다

관리자 대시보드는 Suspense 설계 연습에 가장 좋은 사례다. 보통 다음처럼 구성된다.

- 상단 헤더/필터
- KPI 카드 묶음
- 최근 승인/이슈 테이블
- 알림/작업 큐
- 비즈니스 인사이트 그래프

초기 안티패턴은 이렇다.

- 페이지 루트에서 모든 데이터를 한 번에 읽음
- 하나라도 늦으면 전체가 로딩
- 알림 위젯이 실패해도 전체 페이지가 깨짐

더 나은 구조는 보통 아래와 같다.

```tsx
import { Suspense } from "react";

export default async function AdminDashboardPage() {
  const viewer = await getViewer();

  return (
    <main className="space-y-8">
      <DashboardHeader viewer={viewer} />

      <Suspense fallback={<KpiGroupSkeleton />}>
        <KpiGroup />
      </Suspense>

      <div className="grid gap-8 xl:grid-cols-[1.4fr_1fr]">
        <Suspense fallback={<ApprovalQueueSkeleton />}>
          <ApprovalQueue />
        </Suspense>

        <Suspense fallback={<AlertPanelSkeleton />}>
          <AlertPanel />
        </Suspense>
      </div>

      <Suspense fallback={<InsightChartSkeleton />}>
        <InsightChartSection />
      </Suspense>
    </main>
  );
}
```

### 왜 이 구조가 실무적으로 낫나

- 헤더는 항상 빠르게 보여준다  
- KPI 묶음은 하나의 블록으로 안정적으로 뜬다  
- 승인 큐와 알림 패널은 서로의 지연을 기다리지 않는다  
- 인사이트 그래프가 느려도 핵심 운영 작업은 이미 가능하다  

### 실패 설계도 같이 들어가야 한다

- KPI 실패 → 대시보드 핵심 성격상 상위 error로 보내거나, 최소한 카드 묶음 단위 재시도 제공
- 알림 실패 → 패널 내부 안내 문구와 재시도 버튼으로 낮춤
- 그래프 실패 → 텍스트 요약만 대체 표시 가능

즉 화면 블록마다 **지연 허용도와 실패 허용도** 를 다르게 설계해야 한다.

---

## 실무 예시 2: 상품 상세 — 필수 정보와 부가 정보를 같은 운명으로 묶지 말아야 한다

커머스/콘텐츠 상세 페이지에서 가장 중요한 것은 보통 아래다.

- 제목, 가격, 상태, CTA
- 핵심 미디어
- 권한/가용성

반면 아래는 중요하지만 보통 필수는 아니다.

- 추천 상품
- 리뷰 요약
- 연관 콘텐츠
- 최근 본 항목

이 차이를 무시하고 전부 한 덩어리로 await 하면 상세 페이지가 무거워진다.

```tsx
import { Suspense } from "react";

export default async function ProductPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const product = await getProductOrThrow(id);

  return (
    <main className="space-y-10">
      <ProductHero product={product} />

      <section className="grid gap-10 lg:grid-cols-[2fr_1fr]">
        <ProductDetailTabs productId={id} />

        <aside className="space-y-6">
          <Suspense fallback={<ReviewSummarySkeleton />}>
            <ReviewSummary productId={id} />
          </Suspense>

          <Suspense fallback={<RecommendationSkeleton />}>
            <RecommendationPanel productId={id} />
          </Suspense>
        </aside>
      </section>
    </main>
  );
}
```

이 구조는 세 가지를 동시에 만족한다.

1. 필수 상세 정보는 먼저 뜬다  
2. 부가 정보는 늦게 와도 된다  
3. 리뷰/추천 실패가 상세 전체를 망치지 않는다  

### 실무 포인트: skeleton은 실제 공간을 보존해야 한다

상세 페이지에서는 fallback이 나중에 진짜 UI로 교체될 때 레이아웃 점프가 크면 체감 품질이 크게 떨어진다. 그래서 리뷰 summary와 recommendation panel은 fallback 단계에서도 **비슷한 박스 크기와 헤더 구조** 를 갖게 하는 편이 낫다.

나쁜 예:

```tsx
<Suspense fallback={<div>loading...</div>}>
  <RecommendationPanel productId={id} />
</Suspense>
```

좋은 예:

```tsx
function RecommendationSkeleton() {
  return (
    <section className="rounded-2xl border p-5">
      <div className="mb-4 h-5 w-32 animate-pulse rounded bg-neutral-200" />
      <div className="space-y-3">
        <div className="h-20 animate-pulse rounded-xl bg-neutral-200" />
        <div className="h-20 animate-pulse rounded-xl bg-neutral-200" />
        <div className="h-20 animate-pulse rounded-xl bg-neutral-200" />
      </div>
    </section>
  );
}
```

스트리밍 UI에서 중요한 것은 “빨리 뭔가 보이게”가 아니라 **빨리 안정적인 구조를 보이게** 다.

---

## 실무 예시 3: 검색 결과 화면 — Suspense를 잘못 쓰면 빠른 화면이 아니라 “계속 흔들리는 화면”이 된다

검색 페이지는 App Router에서 가장 쉽게 복잡해지는 화면 중 하나다.

- 상단 검색 조건
- 결과 목록
- facet/filter 집계
- 추천 검색어
- 정렬/페이지네이션
- 광고/프로모션 블록

이때 흔한 유혹은 각 블록마다 Suspense를 넣는 것이다. 하지만 검색 결과는 사용자가 보통 **결과 목록 전체의 정합성** 을 중요하게 본다. facet만 먼저 뜨고 목록이 늦거나, 목록이 먼저 뜨고 총 개수가 나중에 바뀌면 혼란이 생길 수 있다.

### 검색 화면에서 경계 기준

보통은 이렇게 나누는 편이 낫다.

- 검색 조건 헤더 → 즉시 표시
- 결과 목록 + total count + facet 주요 영역 → 한 묶음
- 추천 검색어/광고/부가 패널 → 별도 후순위 Suspense

```tsx
import { Suspense } from "react";

export default function SearchPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; sort?: string }>;
}) {
  return (
    <main className="space-y-8">
      <SearchToolbar />

      <Suspense fallback={<SearchResultSkeleton />}>
        <SearchResultsArea searchParams={searchParams} />
      </Suspense>

      <Suspense fallback={null}>
        <RelatedKeywordSection searchParams={searchParams} />
      </Suspense>
    </main>
  );
}
```

### 왜 결과 목록을 한 묶음으로 보는가

검색은 “부분적으로 먼저 보이기”보다 “한 번에 정합성 있게 보이기”가 더 중요한 경우가 많다.

- 총 결과 수
- 현재 정렬 기준
- facet 집계
- 결과 카드 리스트

이 네 가지가 서로 어긋나면 사용자는 빠르다고 느끼기보다 **불안정하고 믿기 어렵다** 고 느낀다. 따라서 모든 화면이 잘게 쪼개질수록 좋은 것이 아니다.

즉 Suspense는 항상 더 많이 넣는 것이 답이 아니라, **정합성이 중요한 블록은 의도적으로 같이 기다리게 하는 것** 도 전략이다.

---

## 핵심 개념 6: nested boundary와 재시도 흐름은 “로딩-성공”보다 “실패 후 회복”에서 진가가 드러난다

대부분의 데모는 Suspense를 성공 케이스만으로 설명한다. 하지만 실무에서 더 중요한 장면은 다음이다.

- 일부 블록이 실패했다가 재시도에 성공하는가
- 부모 경계는 유지한 채 자식 경계만 다시 그릴 수 있는가
- 사용자가 필터를 바꿨을 때 어떤 범위가 다시 fallback으로 들어가는가
- 재요청 시 기존 UI를 유지할지, skeleton으로 전환할지 의도적으로 선택했는가

즉 진짜 어려운 문제는 “처음 로딩”보다 **경계가 다시 pending / error 상태로 들어갈 때의 사용자 경험** 이다.

### nested boundary를 잘 쓰면 회복 범위를 줄일 수 있다

예를 들어 분석 대시보드에서 아래 구조를 보자.

```tsx
import { Suspense } from "react";

export default function AnalyticsPage() {
  return (
    <main className="space-y-8">
      <PageHeader />

      <Suspense fallback={<AnalyticsOverviewSkeleton />}>
        <AnalyticsOverview />
      </Suspense>

      <Suspense fallback={<ReportSectionSkeleton />}>
        <ReportSection />
      </Suspense>
    </main>
  );
}
```

그리고 `ReportSection` 안쪽에서 다시 세부 블록을 쪼갤 수 있다.

```tsx
import { Suspense } from "react";

export async function ReportSection() {
  return (
    <section className="space-y-6">
      <SectionHeader title="리포트" />

      <Suspense fallback={<ChartSkeleton />}>
        <RevenueChart />
      </Suspense>

      <Suspense fallback={<TableSkeleton />}>
        <RevenueTable />
      </Suspense>
    </section>
  );
}
```

이렇게 nested boundary를 두면 다음과 같은 설계가 가능하다.

- overview는 즉시 복구되어야 하는 핵심 블록
- report section은 조금 늦어도 되는 보조 블록
- report 안에서도 chart와 table은 서로의 실패/지연을 기다리지 않음

즉 경계를 한 번만 자르는 것이 아니라, **큰 의미 덩어리 → 내부 독립 덩어리** 순으로 계층화할 수 있다.

### 다만 nested boundary는 깊을수록 좋은 것이 아니다

잘못 쓰면 이런 일이 생긴다.

- 표 헤더, 차트 범례, 카드 숫자 하나마다 skeleton이 따로 뜬다
- 경계가 너무 많아 어느 실패가 어디까지 영향을 주는지 팀이 이해하지 못한다
- 재요청 시 여러 fallback이 동시에 깜빡이며 화면이 불안정해진다

실무 기준으로 nested boundary는 보통 **2단계 정도면 충분한 경우가 많다**.

1. 페이지/세그먼트의 큰 블록
2. 큰 블록 내부의 독립 위젯

그 이상은 정말 독립 가치가 큰 경우에만 쓰는 편이 낫다.

### reset은 기술 버튼이 아니라 회복 전략이다

`error.tsx` 의 `reset()` 은 단순히 “다시 눌러보는 버튼”이 아니다. 사용자 관점에서는 **지금 문맥을 유지한 채 다시 시도하는 가장 낮은 비용의 회복 수단** 이다.

그래서 다음 기준이 중요하다.

- 실패 원인이 일시적인 네트워크/업스트림 지연인가?
- 사용자가 같은 입력으로 다시 시도하는 것이 자연스러운가?
- 재시도 전 로컬 수정 상태나 필터 상태를 잃지 않는가?
- 재시도 후 실패 범위만 다시 렌더되는가, 아니면 전체 화면이 다시 흔들리는가?

예를 들어 보고서 영역만 실패했다면 reset도 그 영역 수준에서 끝나는 편이 좋다. 반대로 인증이나 필수 상품 데이터가 실패했다면 페이지 수준 재시도 또는 목록 복귀가 더 자연스럽다.

즉 `reset()` 은 “일단 넣어두는 UX” 가 아니라, **어디까지를 같은 문맥으로 보고 회복할 것인지 결정하는 설계 포인트** 다.

---

## 핵심 개념 7: searchParams, key, template remount를 이해하지 못하면 Suspense가 의도와 다르게 재실행된다

App Router에서 필터, 정렬, 탭, 검색어가 바뀌는 화면은 Suspense를 가장 섬세하게 다뤄야 한다. 이때 많은 팀이 겪는 혼란은 다음과 같다.

- 검색어만 바꿨는데 페이지 전체 fallback이 다시 뜬다
- 탭 전환마다 내부 상태가 예상보다 자주 초기화된다
- 같은 세그먼트 안에서 일부만 갱신하고 싶었는데 통째로 다시 렌더된다

이 문제는 보통 **경계의 identity** 를 명확히 생각하지 않았기 때문에 생긴다.

### key를 바꾸면 “같은 경계의 새 로딩”으로 취급된다

예를 들어 검색 결과를 `q` 와 `sort` 조합으로 새로 그리려면, 결과 영역 Suspense에 key를 줄 수 있다.

```tsx
import { Suspense } from "react";

export default async function SearchPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; sort?: string }>;
}) {
  const params = await searchParams;
  const queryKey = `${params.q ?? ""}:${params.sort ?? "relevance"}`;

  return (
    <main>
      <SearchToolbar initialQuery={params.q ?? ""} />
      <Suspense key={queryKey} fallback={<SearchResultSkeleton />}>
        <SearchResultsArea searchParams={params} />
      </Suspense>
    </main>
  );
}
```

이 패턴은 다음처럼 해석할 수 있다.

- 검색 조건이 같으면 같은 경계로 본다
- 검색 조건이 바뀌면 결과 영역만 새 pending 상태로 본다
- 툴바와 페이지 외곽은 유지하고, 결과 블록만 다시 skeleton 처리한다

즉 `key` 는 단순 리렌더링 트릭이 아니라 **어떤 상태 변화를 새 로딩 문맥으로 볼 것인지 정의하는 도구** 다.

### 모든 searchParams 변경이 전체 fallback을 유발할 필요는 없다

예를 들어 아래는 과한 설계일 수 있다.

- 전체 페이지를 하나의 Suspense로 감쌈
- 정렬 옵션 하나 바뀔 때도 페이지 전체 skeleton 표시
- 사용자는 결과만 바뀌면 되는데 헤더, 필터, 보조 패널까지 함께 흔들림

더 나은 방식은 대개 이렇다.

- 검색 툴바는 유지
- facet/결과 영역만 새로 로딩
- 추천 검색어나 광고는 이전 값을 유지하거나 별도 경계에서 천천히 갱신

즉 필터/정렬/검색어 변화는 종종 **페이지 진입** 과 다른 종류의 대기 경험이다. 이를 같은 fallback으로 다루면 UX가 거칠어진다.

### template.tsx 와 remount semantics도 알아둘 가치가 있다

`template.tsx` 는 같은 세그먼트 전환에서도 새 인스턴스로 다시 마운트되게 하는 데 쓰인다. 모든 글에서 꼭 다뤄야 하는 주제는 아니지만, Suspense/로딩 UX를 정교하게 다루는 팀이라면 이 차이를 알고 있어야 한다.

- `layout.tsx` → 전환 사이에 상태를 더 오래 유지하는 구조
- `template.tsx` → 전환 시 새 인스턴스로 재생성되는 구조

예를 들어 탭 전환마다 analytics panel을 항상 새로 측정하거나, 특정 전환에서 진입 애니메이션/로깅/상태 초기화를 의도적으로 발생시키고 싶다면 template의 재마운트 특성이 유용할 수 있다. 반대로 이 차이를 모르고 쓰면 **왜 어떤 경계는 fallback이 유지되고, 어떤 경계는 매번 새로 뜨는지** 설명하기 어려워진다.

실무에서는 모든 화면에 template를 도입할 필요는 없다. 다만 다음 질문엔 답할 수 있어야 한다.

- 이 전환에서 이전 상태를 유지하는 것이 맞는가?
- 아니면 새 진입처럼 다시 보여주는 것이 맞는가?
- skeleton, 애니메이션, 내부 client state 중 무엇을 유지/초기화할 것인가?

이 판단이 서야 searchParams 기반 결과 갱신과 세그먼트 전환 UX가 일관된다.

---

## 실무 예시 4: 필터 가능한 리스트 화면 — “전체 로딩”과 “부분 갱신”을 분리하면 체감 품질이 크게 달라진다

채용 공고 목록, 이슈 리스트, 주문 내역처럼 필터와 정렬이 자주 바뀌는 화면을 생각해보자.

이런 화면에서 사용자는 보통 다음을 기대한다.

- 상단 필터 바는 계속 손댈 수 있어야 한다
- 결과 리스트만 바뀌면 된다
- 정렬을 바꿀 때 페이지 전체가 사라지면 답답하다
- 일부 보조 통계는 조금 늦어도 괜찮다

이 기준으로 구조를 나누면 아래와 비슷해진다.

```tsx
import { Suspense } from "react";

export default async function JobsPage({
  searchParams,
}: {
  searchParams: Promise<{
    keyword?: string;
    status?: string;
    sort?: string;
  }>;
}) {
  const params = await searchParams;
  const listKey = JSON.stringify({
    keyword: params.keyword ?? "",
    status: params.status ?? "all",
    sort: params.sort ?? "recent",
  });

  return (
    <main className="space-y-8">
      <JobFilterBar initialParams={params} />

      <div className="grid gap-8 xl:grid-cols-[1.6fr_0.8fr]">
        <Suspense key={listKey} fallback={<JobListSkeleton />}>
          <JobListSection searchParams={params} />
        </Suspense>

        <Suspense fallback={<JobStatsSkeleton />}>
          <JobStatsPanel searchParams={params} />
        </Suspense>
      </div>
    </main>
  );
}
```

### 이 설계가 좋은 이유

- 필터 바는 항상 유지된다  
- 리스트는 새 조건 기준으로만 재로딩된다  
- 통계 패널은 별도 경계라 느려도 리스트와 분리된다  
- 사용자는 “조건을 바꾸자 화면 전체가 날아간다”는 느낌을 덜 받는다  

### 여기서 흔한 실수

- 리스트와 stats를 한 경계에 넣어 느린 통계가 리스트까지 막는다
- 반대로 리스트 내부 카드마다 Suspense를 넣어 카드들이 하나씩 튀어나온다
- 필터 바까지 경계 안에 넣어 사용자가 입력 직후 UI를 잃는다

즉 필터형 화면의 핵심은 **조작 영역은 유지하고, 결과 영역만 명시적으로 다시 pending 시키는 것** 이다.

---

## 트레이드오프: 경계를 잘게 나눌수록 빨라질 수도 있지만, 조각난 경험과 관리 비용도 커진다

좋은 경계 설계는 언제나 trade-off 문제다.

### 경계를 잘게 나눴을 때 얻는 것

- 일부 영역을 더 빨리 노출할 수 있다
- 부분 실패가 전체를 무너뜨리지 않는다
- 느린 외부 API를 격리하기 쉽다
- 위젯 단위 재시도 UX를 설계할 수 있다

### 경계를 잘게 나눴을 때 잃는 것

- 화면이 조각조각 늦게 들어오며 산만해질 수 있다
- skeleton 설계와 테스트 포인트가 늘어난다
- fallback 간 레이아웃 정합성 관리가 어려워진다
- 경계가 많아질수록 의존 관계를 이해하기 어려워진다

### 경계를 크게 묶었을 때 얻는 것

- 화면 정합성이 좋다
- skeleton 설계가 단순하다
- 로딩/에러 상태 추적이 쉬워진다

### 경계를 크게 묶었을 때 잃는 것

- 느린 하위 영역 하나가 전체를 막는다
- 부가 기능 실패가 핵심 화면까지 전염될 수 있다
- 체감 속도 개선 폭이 작아진다

결국 핵심은 아래 균형이다.

> **정합성이 중요한 덩어리는 같이 기다리고, 늦어도 되는 덩어리는 독립적으로 스트리밍하라.**

이 기준 없이 Suspense를 늘리면 “최신 패턴을 적용한 것 같은데 UX는 더 산만한 화면”이 나오기 쉽다.

---

## 흔한 실수

### 1) 페이지 루트에서 모든 데이터를 먼저 await 한다

가장 흔한 실수다. 이러면 Suspense를 붙여도 대부분 의미가 없다. 먼저 보여도 되는 정보는 하위 컴포넌트로 내려서 그쪽에서 기다리게 해야 한다.

### 2) API 하나당 Suspense 하나로 쪼갠다

기술적으로는 맞아 보여도, 사용자 눈에는 카드와 카드가 따로 늦게 들어오며 산만하게 보일 수 있다. 경계는 API가 아니라 UI 의미 단위로 잡는 편이 낫다.

### 3) loading.tsx 와 내부 fallback 이 서로 같은 일을 한다

페이지 이동 시 전체 skeleton이 보였다가, 곧 내부 카드별 skeleton이 또 보이면 이중 로딩처럼 느껴진다. 세그먼트 골격과 내부 위젯 fallback 역할을 분리해야 한다.

### 4) fallback 을 너무 가볍게 만들어 CLS를 유발한다

`loading...` 같은 텍스트 한 줄은 개발은 빠르지만, 실제 UI가 들어왔을 때 공간이 크게 변한다. 특히 카드, 표, 상세 레이아웃은 실제 크기를 보존하는 fallback이 중요하다.

### 5) error.tsx 를 “문제가 생겼다” 문구로만 끝낸다

실무에서는 재시도, 뒤로 가기, 다른 경로 이동, 운영 추적용 오류 식별자까지 고려해야 한다. error UI는 알림이 아니라 복구 UX다.

### 6) 부가 기능 오류를 페이지 치명 오류와 같은 레벨로 다룬다

추천/광고/연관 콘텐츠 실패는 상세 전체 실패와 다르다. 모든 것을 상위 세그먼트 에러로 몰면 사용자 경험이 지나치게 거칠어진다.

### 7) 스트리밍 UI를 만들면서 fetch 구조는 여전히 waterfall이다

Suspense는 경계일 뿐이다. 실제 네트워크/DB 호출이 병렬화되지 않으면 효과가 제한적이다.

### 8) 검색 같은 정합성 민감 화면을 너무 잘게 쪼갠다

빠르게 뜨는 것보다 같이 맞게 뜨는 것이 중요한 화면이 있다. 검색 결과, 장바구니 금액, 결제 요약 등이 대표적이다.

### 9) skeleton이 실제 디자인과 너무 다르다

로딩 상태가 완성 화면과 구조적으로 다르면, 사용자는 두 번 화면을 읽어야 한다. skeleton은 placeholder가 아니라 **예고편** 에 가까워야 한다.

### 10) 재시도 UX를 테스트하지 않는다

에러 발생 자체보다 더 중요한 것은 reset 이후 정말 회복되는가, 실패가 반복될 때 사용자가 다음 행동을 알 수 있는가다.

---

## 실무 체크리스트

### 1) 경계 설계

- [ ] 이 화면에서 사용자가 가장 먼저 봐야 할 블록이 무엇인지 명확한가?
- [ ] 정합성이 중요한 블록과 늦어도 되는 블록이 구분되어 있는가?
- [ ] Suspense 경계를 API 단위가 아니라 UI 의미 단위로 잡았는가?
- [ ] 일부 실패가 전체 실패로 전염되지 않도록 범위를 나눴는가?

### 2) loading.tsx

- [ ] 세그먼트 첫 진입 시 필요한 기본 골격을 제공하는가?
- [ ] 내부 Suspense fallback 과 역할이 중복되지 않는가?
- [ ] 실제 레이아웃 크기와 큰 차이가 없어 CLS를 줄이는가?
- [ ] skeleton 유지 비용이 과도하지 않은가?

### 3) Suspense fallback

- [ ] fallback 이 실제 정보 구조를 충분히 예고하는가?
- [ ] 너무 잘게 쪼개져 화면이 조각나 보이지 않는가?
- [ ] 데이터 fetch가 실제로 병렬화되어 있는가?
- [ ] 상위에서 미리 await 하느라 스트리밍 이점을 죽이지 않았는가?

### 4) error.tsx 및 실패 UX

- [ ] 어떤 오류가 세그먼트 수준 치명 오류인지 정의했는가?
- [ ] 부가 위젯 오류는 낮은 수준으로 degrade 가능한가?
- [ ] reset 기반 재시도 UX가 자연스러운가?
- [ ] 사용자가 다른 경로로 복귀할 수 있는 fallback 행동이 있는가?
- [ ] 운영 추적용 로그/오류 ID 연결을 고려했는가?

### 5) 테스트

- [ ] 느린 API 하나만 인위적으로 지연시켜도 핵심 화면이 먼저 뜨는가?
- [ ] 부가 위젯 하나가 실패해도 핵심 기능이 유지되는가?
- [ ] route transition 시 loading.tsx 가 과도하게 깜빡이지 않는가?
- [ ] skeleton → 실제 UI 전환 시 레이아웃 점프가 크지 않은가?
- [ ] reset 재시도 이후 성공/실패 루프가 의도대로 동작하는가?

---

## 한 줄 정리

Next.js의 `Suspense`, `loading.tsx`, `error.tsx` 는 단순한 로딩/에러 문법이 아니다. **느린 부분은 늦게 보여도 되고, 실패한 부분은 거기서 멈추게 하며, 핵심 정보는 먼저 안정적으로 노출되도록 화면의 기다림과 실패를 설계하는 도구** 다.
