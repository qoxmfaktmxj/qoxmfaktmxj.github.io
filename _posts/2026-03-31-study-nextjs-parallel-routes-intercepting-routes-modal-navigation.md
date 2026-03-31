---
layout: post
title: "Next.js Parallel Routes·Intercepting Routes 실전: 모달 UX와 URL 정합성을 함께 설계하는 법"
date: 2026-03-31 11:40:00 +0900
categories: [nextjs]
tags: [study, nextjs, parallel-routes, intercepting-routes, modal, app-router, navigation]
---

## 배경: 모달은 쉬워 보여도, URL까지 맞추려는 순간 설계 난도가 급상승한다

대부분의 팀은 상세 보기 모달을 처음엔 아주 단순하게 시작한다.

- 목록에서 카드 클릭
- 로컬 상태로 `isOpen = true`
- 선택한 아이템을 state에 담아 모달 렌더링
- 닫기 버튼 누르면 state 초기화

데모에서는 잘 된다. 문제는 서비스가 커질수록 **모달이 더 이상 단순한 시각 효과가 아니게 된다**는 점이다.

실무에서는 곧 이런 요구가 붙는다.

- 상세 화면 링크를 복사해 동료에게 공유하고 싶다
- 새로고침해도 지금 보고 있던 상세 상태를 복구하고 싶다
- 모바일에서는 전체 페이지, 데스크톱에서는 오버레이처럼 보이고 싶다
- 뒤로 가기 한 번으로 모달만 닫히고, 목록 스크롤 위치는 유지되길 원한다
- 직접 URL로 진입했을 때는 모달이 아니라 **정상적인 상세 페이지**로 열려야 한다
- 검색엔진이나 분석 시스템에서는 상세 페이지가 독립 경로로 잡혀야 한다

이 시점부터 단순한 클라이언트 상태 모달은 자주 무너진다.

- 공유 가능한 URL이 없다
- 새로고침 시 상태가 사라진다
- 히스토리 스택과 UI 상태가 어긋난다
- 목록/상세 두 화면의 책임 경계가 흐려진다
- 모달용 데이터 로딩과 정식 상세 페이지 로딩이 중복된다

Next.js App Router의 **Parallel Routes** 와 **Intercepting Routes** 는 바로 이런 문제를 해결하기 위해 존재한다. 하지만 실무에서는 이 둘을 “모달 라우팅 기능” 정도로만 이해하고 들어갔다가 오히려 디렉터리 구조와 렌더링 규칙에서 더 큰 혼란을 겪는 경우가 많다.

이 글의 목표는 문법 암기가 아니다. 핵심은 다음 질문에 답하는 것이다.

> **어떻게 하면 하나의 상세 리소스를 유지하면서도, 목록 문맥에서는 모달처럼 보이고 직접 진입 시에는 정식 페이지처럼 보이게 설계할 수 있을까?**

그리고 그 답은 단순히 폴더 이름 몇 개를 외우는 것이 아니라, **URL 정합성, 레이아웃 문맥, soft navigation/hard navigation 차이, slot 기본값 복구 전략**까지 이해하는 데 있다.

---

## 먼저 큰 그림: Parallel Routes와 Intercepting Routes는 역할이 완전히 다르다

둘을 같이 쓰는 경우가 많아서 한 덩어리 기능처럼 느껴지지만, 본질은 다르다.

### 1) Parallel Routes: 한 레이아웃 안에서 여러 UI 슬롯을 독립적으로 렌더링하는 구조

Parallel Routes는 `@slot` 폴더를 통해 **동일한 레이아웃 아래 여러 렌더링 영역**을 만든다.

예를 들어 `@modal`, `@analytics`, `@team` 같은 슬롯을 두고 레이아웃에서 props로 받아 함께 렌더링할 수 있다.

중요한 점은 이것이다.

- `@modal` 은 **URL 세그먼트가 아니다**
- 슬롯은 경로가 아니라 **레이아웃의 렌더링 자리**다
- 각 슬롯은 `loading.tsx`, `error.tsx`, `default.tsx`를 독립적으로 가질 수 있다
- soft navigation 중에는 슬롯별 활성 서브페이지 상태가 유지될 수 있다

즉 Parallel Routes의 핵심은 “모달”이 아니라 **동시에 여러 라우트 하위 상태를 공존시키는 레이아웃 설계**다.

### 2) Intercepting Routes: 다른 경로를 현재 레이아웃 문맥에서 가로채 렌더링하는 방식

Intercepting Routes는 원래라면 다른 경로에서 렌더될 페이지를, **현재 보고 있는 문맥 안으로 끌어와서** 보여준다.

대표적인 요구가 이거다.

- `/products` 목록에서 `/products/42`로 이동할 때는 모달처럼 열고 싶다
- 하지만 `/products/42`를 주소창에 직접 입력하면 전체 상세 페이지로 보여야 한다

즉 Intercepting Routes는 “해당 리소스의 canonical URL은 유지하되, **어디서 어떻게 진입했는지에 따라 다른 프레젠테이션 문맥**을 제공하는 기능”에 가깝다.

### 둘을 같이 쓰는 이유

실무에서 많이 쓰는 패턴은 아래다.

- **Parallel Routes** 로 `@modal` 슬롯을 준비한다
- **Intercepting Routes** 로 상세 페이지 경로를 현재 문맥에서 가로채 `@modal` 슬롯에 렌더한다
- 결과적으로 soft navigation 시엔 모달, direct visit 시엔 full page가 된다

정리하면:

- Parallel Routes = **어디에 렌더할지**
- Intercepting Routes = **무엇을 현재 문맥에서 가로채 렌더할지**

이 구분이 서지 않으면 폴더 구조를 따라 쳐도 왜 동작하는지 이해가 안 된다.

---

## 핵심 개념 1: Parallel Routes의 본질은 “다중 페이지”가 아니라 “다중 슬롯 상태”다

많은 개발자가 `@modal` 을 보면 “아, 이건 URL에 추가되는 특수 라우트구나”라고 오해한다. 하지만 `@slot`은 URL 경로가 아니라 레이아웃 prop이다.

예를 들어 이런 구조를 보자.

```txt
app/
  products/
    layout.tsx
    page.tsx
    [id]/page.tsx
    @modal/
      default.tsx
```

`layout.tsx`는 이렇게 받을 수 있다.

```tsx
// app/products/layout.tsx
import type { ReactNode } from "react";

export default function ProductsLayout({
  children,
  modal,
}: {
  children: ReactNode;
  modal: ReactNode;
}) {
  return (
    <>
      <main>{children}</main>
      {modal}
    </>
  );
}
```

여기서 중요한 포인트는 다음과 같다.

- `children` 은 기본 슬롯이다
- `@modal` 폴더는 `modal` prop으로 들어온다
- 즉 레이아웃은 “본문 + 모달 슬롯”을 항상 받을 준비를 하는 셈이다

이 구조 자체만으로는 아직 아무 것도 가로채지 않는다. 다만 **모달을 끼워 넣을 수 있는 레이아웃 자리**를 만든 것이다.

### 왜 이게 실무적으로 중요한가

단순 상태 기반 모달은 보통 현재 페이지 내부에서만 의미가 있다. 반면 Parallel Routes를 쓰면 모달이 페이지 내부 로컬 상태가 아니라, **라우팅 시스템이 관리하는 렌더링 상태**가 된다.

그 결과 얻는 이점은 크다.

- 뒤로 가기/앞으로 가기와 모달 상태가 더 자연스럽게 연결된다
- 슬롯 단위 로딩/에러 분리가 가능하다
- 동일 레이아웃 아래 여러 보조 화면(모달, 사이드패널, 보조 탭)을 구조적으로 넣을 수 있다
- 클라이언트 상태에만 의존하지 않아 URL/히스토리와의 정합성이 좋아진다

### 슬롯은 독립 상태를 가진다

Parallel Routes를 깊게 이해하려면 **soft navigation 시 각 슬롯의 활성 서브페이지가 유지될 수 있다**는 점을 알아야 한다.

예를 들어 대시보드에서 `@analytics`, `@team` 슬롯을 운영하면, 본문이 다른 경로로 이동해도 특정 슬롯은 직전 상태를 기억해 보이는 것처럼 느껴질 수 있다. 이 특성은 강력하지만 동시에 함정도 있다.

- 장점: 복합 레이아웃을 자연스럽게 유지 가능
- 단점: 의도하지 않은 이전 슬롯 상태가 남아 “왜 이게 아직 떠 있지?” 같은 버그를 만든다

그래서 실무에서는 `default.tsx` 설계가 생각보다 중요하다.

---

## 핵심 개념 2: `default.tsx`를 가볍게 보면 새로고침과 직접 진입에서 바로 깨진다

Parallel Routes를 처음 쓸 때 가장 많이 놓치는 파일이 `default.tsx` 다.

예를 들어 모달 슬롯에 이 파일이 없다고 해보자.

```txt
app/
  products/
    @modal/
      (.)[id]/page.tsx
```

soft navigation으로 목록에서 상세를 눌렀을 때는 잘 뜰 수 있다. 하지만 이런 상황에서 문제가 생긴다.

- 상세 모달이 열린 상태에서 새로고침
- `/products` 로 직접 방문
- 다른 경로에서 hard navigation 발생

Next.js는 hard navigation 시 **현재 URL과 정확히 매칭되지 않는 슬롯의 활성 상태를 복원할 수 없다**. 이때 `default.tsx` 가 없으면 예상치 못한 404나 빈 상태를 보게 될 수 있다.

그래서 모달 슬롯에는 보통 아래처럼 둔다.

```tsx
// app/products/@modal/default.tsx
export default function Default() {
  return null;
}
```

의미는 단순하다.

- 지금 URL에서 `@modal` 슬롯이 활성화될 이유가 없으면 아무 것도 렌더하지 마라

하지만 효과는 크다. 이것이 있어야 hard navigation 시 모달 슬롯이 안전하게 비워진다.

### 실무 포인트

`default.tsx`는 선택사항처럼 보여도, Parallel Routes를 운영 가능한 수준으로 만들기 위한 **복구 전략**이다.

특히 아래 경우에는 거의 필수다.

- 모달 슬롯
- 조건부 사이드패널 슬롯
- 인증 상태/권한에 따라 비어 있을 수 있는 슬롯
- direct visit에서는 보이지 않아야 하는 보조 슬롯

---

## 핵심 개념 3: Intercepting Routes의 핵심은 “URL을 바꾸지 않는 것”이 아니라 “같은 URL을 다른 문맥에서 렌더링하는 것”이다

Intercepting Routes를 오해하면 “모달을 띄우되 주소는 그대로 유지하는 기능”으로 생각하기 쉽다. 실제로는 반대다.

**주소는 바뀐다.** 대신 그 주소가 가리키는 리소스를, 현재 레이아웃 문맥 안에서 다르게 표현한다.

예를 들어 사용자가 `/products` 목록에서 상품 42를 클릭하면 URL은 `/products/42` 로 이동할 수 있다. 그런데 사용자는 전체 상세 페이지 전환이 아니라, 목록 위에 뜬 모달을 본다.

즉 사용자가 얻게 되는 경험은 이렇다.

- URL은 canonical detail URL로 이동한다
- 히스토리도 detail URL 기준으로 쌓인다
- 하지만 UI는 현재 목록 문맥을 유지한 채 detail을 오버레이로 렌더한다

이게 중요한 이유는 다음과 같다.

- 링크 공유 시 실제 상세 URL을 그대로 줄 수 있다
- 분석/SEO/딥링크가 일관된다
- soft navigation과 direct visit이 서로 다른 UX를 가질 수 있다

### Intercepting Routes 문법

Next.js는 상대적 세그먼트 표기로 interception 대상을 지정한다.

- `(.)` : 같은 수준 세그먼트
- `(..)` : 한 단계 위
- `(..)(..)` : 두 단계 위
- `(...)` : 루트 기준

모달 예시로 많이 쓰는 구조는 이런 형태다.

```txt
app/
  products/
    page.tsx
    [id]/page.tsx
    layout.tsx
    @modal/
      default.tsx
      (.)[id]/page.tsx
```

여기서 `@modal/(.)[id]/page.tsx` 는 원래 `products/[id]/page.tsx` 로 가야 할 상세 페이지를, **현재 `products` 문맥 안의 modal 슬롯에서 가로채 렌더링**하는 역할을 한다.

### direct visit과 soft navigation의 차이

이 기능이 실무에서 강력한 이유는 진입 방식에 따라 경험이 갈리기 때문이다.

#### soft navigation

사용자가 `/products` 에서 `<Link href="/products/42">` 를 눌렀다.

- 현재 레이아웃 문맥이 살아 있다
- 인터셉트 규칙이 적용된다
- 결과적으로 `/products/42` 가 `@modal` 슬롯에 렌더된다

#### hard navigation / direct visit

사용자가 주소창에 `/products/42` 를 직접 입력하거나 새 탭으로 열었다.

- 현재 목록 문맥이 없다
- 인터셉트 문맥도 없다
- 따라서 원래 정식 상세 라우트인 `products/[id]/page.tsx` 가 렌더된다

이 차이를 이해하지 못하면 “왜 같은 URL인데 어떤 때는 모달이고 어떤 때는 전체 페이지지?”가 이상하게 느껴진다. 하지만 사실 이것이 의도된 동작이다.

> 같은 URL이지만, **현재 사용자가 어느 레이아웃 문맥에서 이동했는지**에 따라 표현 방식이 달라지는 것이다.

---

## 실무 예시 1: 상품 목록에서는 모달, 직접 진입 시에는 정식 상세 페이지

가장 대표적인 패턴을 실제 구조로 정리해보자.

```txt
app/
  products/
    layout.tsx
    page.tsx
    [id]/
      page.tsx
      loading.tsx
      error.tsx
    @modal/
      default.tsx
      (.)[id]/
        page.tsx
```

### 1) 목록 레이아웃에서 모달 슬롯을 받는다

```tsx
// app/products/layout.tsx
import type { ReactNode } from "react";

export default function ProductsLayout({
  children,
  modal,
}: {
  children: ReactNode;
  modal: ReactNode;
}) {
  return (
    <div className="products-layout">
      {children}
      {modal}
    </div>
  );
}
```

### 2) 목록 페이지는 일반 링크로 상세 경로를 건다

```tsx
// app/products/page.tsx
import Link from "next/link";

export default async function ProductsPage() {
  const products = await getProducts();

  return (
    <section>
      <h1>상품 목록</h1>
      <ul>
        {products.map((product) => (
          <li key={product.id}>
            <Link href={`/products/${product.id}`} scroll={false}>
              {product.name}
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
```

여기서 `scroll={false}` 는 필수는 아니지만, 목록 스크롤 위치를 최대한 보존하고 싶을 때 자주 쓴다.

### 3) 정식 상세 페이지는 canonical 화면을 담당한다

```tsx
// app/products/[id]/page.tsx
export default async function ProductDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const product = await getProductOrThrow(id);

  return (
    <article>
      <h1>{product.name}</h1>
      <p>{product.description}</p>
      <ProductSpecTable product={product} />
      <RelatedProducts productId={product.id} />
    </article>
  );
}
```

이 페이지는 SEO, 공유, direct visit, 새 탭 열기 기준의 **정식 진실 소스**다.

### 4) 인터셉트된 모달 페이지는 같은 리소스를 모달 프레젠테이션으로 감싼다

```tsx
// app/products/@modal/(.)[id]/page.tsx
import { Modal } from "@/components/modal";
import { ProductDetailView } from "@/components/product-detail-view";

export default async function ProductModalPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const product = await getProductOrThrow(id);

  return (
    <Modal>
      <ProductDetailView product={product} />
    </Modal>
  );
}
```

여기서 중요한 실무 원칙은 **상세 데이터와 핵심 뷰는 공유하고, 컨테이너만 다르게 둔다**는 점이다.

즉 아래처럼 분리하는 편이 좋다.

- `products/[id]/page.tsx` → full page container
- `@modal/(.)[id]/page.tsx` → modal container
- `ProductDetailView` → 공통 상세 본문
- `getProductOrThrow` → 공통 서버 데이터 접근

이렇게 해야 모달 버전과 정식 상세 버전이 시간이 지나며 따로 진화하는 사고를 막을 수 있다.

### 5) 모달 슬롯 기본값은 반드시 비워둔다

```tsx
// app/products/@modal/default.tsx
export default function Default() {
  return null;
}
```

이 파일이 있어야 `/products` 에 직접 들어왔을 때 모달 슬롯이 안전하게 비워진다.

---

## 실무 예시 2: 대시보드의 보조 패널은 모달보다 Parallel Routes에 더 잘 맞을 때가 많다

많은 팀이 Parallel Routes를 모달 전용 기능으로 기억하지만, 오히려 더 강한 장면은 **복합 업무 화면**이다.

예를 들어 운영 대시보드에서 이런 요구가 있다고 해보자.

- 왼쪽: 고객 목록
- 가운데: 고객 상세
- 오른쪽: 최근 티켓/결제 이슈 패널
- 일부 패널은 URL에 따라 독립 갱신되어야 함
- 특정 슬롯만 loading/error를 별도 처리하고 싶음

이런 구조를 전부 클라이언트 상태로 만들면 금방 상태 지옥이 된다.

- 선택된 고객 ID
- 열린 티켓 패널 ID
- 필터 상태
- 리스트 스크롤 위치
- 우측 패널 로딩/오류

반면 Parallel Routes를 쓰면 레이아웃 차원에서 “이 화면은 본문 외에 보조 슬롯들을 가진다”는 구조를 명시할 수 있다.

```txt
app/
  dashboard/
    layout.tsx
    page.tsx
    @detail/
      [customerId]/page.tsx
      default.tsx
    @activity/
      [customerId]/page.tsx
      default.tsx
```

이 패턴의 장점은 명확하다.

- 각 슬롯이 자체 loading/error 경계를 가질 수 있다
- 보조 패널을 독립 컴포넌트 상태가 아니라 라우트 상태로 관리할 수 있다
- 대시보드 정보 구조를 폴더 구조로 드러낼 수 있다

다만 이런 설계는 복잡도도 같이 올라간다. 그래서 단순 탭 전환이나 일회성 팝오버에까지 Parallel Routes를 남용하면 오히려 과설계가 된다.

---

## 핵심 개념 4: 모달 UX의 진짜 포인트는 “닫기”가 아니라 “뒤로 가기 복원”이다

모달 라우팅을 도입하는 가장 큰 이유 중 하나는 사용자가 목록 맥락을 잃지 않게 하는 것이다. 여기서 중요한 건 닫기 버튼 렌더링이 아니라, **히스토리와 스크롤이 복원되는 경험**이다.

예를 들어 사용자가 다음 순서로 행동한다고 하자.

1. `/products` 진입
2. 200번째 상품 근처까지 스크롤
3. 상품 클릭 → `/products/42` 모달 오픈
4. 뒤로 가기

좋은 경험은 이렇다.

- 모달만 닫힌다
- 목록 페이지가 다시 마운트되며 처음부터 로딩되지 않는다
- 스크롤 위치가 크게 흔들리지 않는다

이 경험을 위해 실무에서 같이 봐야 할 포인트는 다음과 같다.

### 1) 목록 페이지를 불필요하게 클라이언트 재마운트시키지 말 것

모달 라우팅을 했는데도 뒤로 가기 시 목록이 처음부터 다시 그려지면 사용자는 “그냥 페이지 전환이네?”라고 느낀다. 목록의 정렬/필터/스크롤 상태를 어디서 관리하는지 먼저 점검해야 한다.

- URL search params로 올릴 수 있는 상태는 올린다
- 클라이언트 전역 상태로만 가진 값은 최소화한다
- 서버 컴포넌트 + 클라이언트 리스트 조합이면 hydration 경계가 과도하게 흔들리지 않게 한다

### 2) 모달 닫기를 `router.back()` 중심으로 설계할지, 명시적 링크로 설계할지 구분할 것

간단한 경우엔 뒤로 가기가 자연스럽다.

```tsx
"use client";

import { useRouter } from "next/navigation";

export function ModalCloseButton() {
  const router = useRouter();
  return <button onClick={() => router.back()}>닫기</button>;
}
```

하지만 항상 `router.back()` 만 쓰면 안 되는 경우도 있다.

- 사용자가 상세 URL을 직접 진입한 경우
- 히스토리에 이전 페이지가 외부 사이트인 경우
- 닫기 시 안전하게 `/products` 로 보내야 하는 경우

이런 경우는 fallback 전략이 필요하다.

```tsx
"use client";

import { useRouter } from "next/navigation";

export function ModalCloseButton() {
  const router = useRouter();

  function handleClose() {
    if (window.history.length > 1) {
      router.back();
      return;
    }

    router.push("/products");
  }

  return <button onClick={handleClose}>닫기</button>;
}
```

실무에서는 “닫기 버튼”보다 **히스토리 안전성**을 설계하는 것이 더 중요하다.

---

## 핵심 개념 5: 상세 페이지를 두 벌 만드는 것이 아니라, 프레젠테이션 컨테이너만 두 벌 만들어야 한다

Intercepting Routes를 처음 적용하면 흔히 이렇게 구현한다.

- full page용 상세 구현 1개
- modal용 상세 구현 1개
- 데이터 호출도 각자 따로 작성
- 에러 처리도 각각 다름

처음엔 빨라 보이지만 시간이 지나면 반드시 벌어진다.

- 어떤 필드는 full page에만 있고 modal엔 없음
- 가격 표시 포맷이 다름
- 서버 액션 연결 방식이 다름
- 메타데이터와 접근성 라벨이 불일치

이건 모달 라우팅의 문제가 아니라 **리소스 표현의 진실 소스가 분리된 문제**다.

권장 구조는 아래와 같다.

```txt
app/products/[id]/page.tsx              # 정식 페이지 컨테이너
app/products/@modal/(.)[id]/page.tsx    # 모달 컨테이너
components/product-detail-view.tsx      # 공통 상세 본문
lib/products/get-product.ts             # 공통 데이터 조회
```

즉 “상세 리소스”는 하나고, 표현 컨테이너만 두 개다.

### 왜 이 원칙이 중요한가

1. **기능 일관성**이 유지된다  
   상세 정보/액션 버튼/권한 체크가 어디서 열리든 동일하다.

2. **SEO와 UX 역할이 분리된다**  
   canonical page는 메타데이터와 full document semantics를 책임지고, modal page는 프레젠테이션 오버레이만 책임진다.

3. **테스트 범위가 명확해진다**  
   공통 상세 뷰 테스트 + 컨테이너 차이 테스트로 나눌 수 있다.

---

## 트레이드오프: URL 정합성을 얻는 대신 파일 구조와 사고 비용이 올라간다

이 패턴은 강력하지만 공짜가 아니다.

### 얻는 것

- 공유 가능한 상세 URL
- 목록 문맥을 유지한 모달 UX
- direct visit과 soft navigation을 모두 만족하는 구조
- 히스토리/뒤로 가기와 더 자연스러운 결합
- 슬롯 단위 로딩/오류/기본값 제어

### 치르는 비용

- 폴더 구조가 즉시 복잡해진다
- 팀원이 `@slot`, `(.)`, `default.tsx` 의미를 이해해야 한다
- hard navigation/soft navigation 차이를 테스트해야 한다
- modal/full page 사이의 중복 구현을 계속 경계해야 한다
- 디자이너/기획자와 “언제 모달이고 언제 full page인가”를 명확히 합의해야 한다

### 언제 가치가 큰가

- 콘텐츠 카드 → 상세 보기 전환이 매우 잦은 서비스
- 검색/목록 맥락 유지가 중요한 커머스, 미디어, 갤러리
- 공유 링크와 deep link가 중요함
- 데스크톱과 모바일에서 다른 프레젠테이션 전략이 필요함

### 언제 과한가

- 단순 확인 팝업
- URL로 공유할 필요가 전혀 없는 설정 다이얼로그
- 한 번 열고 끝나는 로컬 편집 UI
- 뒤로 가기/직접 진입 정합성이 핵심이 아닌 경우

즉 모든 모달을 라우트로 만들 필요는 없다. **리소스 탐색의 일부인 상세 보기**일 때 특히 강하다.

---

## 흔한 실수

### 1) `@modal` 이 URL 세그먼트라고 착각한다

슬롯은 경로가 아니다. 그래서 `@modal` 폴더 깊이를 보고 interception 상대 경로를 계산하면 종종 헷갈린다. **slot은 세그먼트 카운트에 포함되지 않는다**는 점을 꼭 기억해야 한다.

### 2) `default.tsx` 없이도 잘 동작하는 것처럼 보여서 생략한다

초기 데모에서는 문제 없어 보일 수 있다. 하지만 새로고침, 직접 진입, hard navigation에서 슬롯 복구가 틀어지기 시작한다.

### 3) 상세 페이지를 modal 버전과 full page 버전으로 따로 복붙한다

단기 속도는 나지만 장기적으로 100% 어긋난다. 상세 본문과 서버 데이터 접근은 공유해야 한다.

### 4) 모달 닫기를 무조건 `router.back()` 에만 의존한다

직접 진입/새 탭/외부 referrer 유입까지 고려하면 fallback 없는 `back()` 은 UX를 망칠 수 있다.

### 5) direct visit 시에도 억지로 모달로 보이게 만든다

이렇게 되면 canonical page 의미가 약해지고, 새로고침/공유/SEO/접근성에서 손해가 커진다. **직접 진입은 full page**가 기본값인 경우가 많다.

### 6) 목록 상태를 URL에 올릴 수 있는데 전부 클라이언트 메모리로만 들고 간다

모달을 잘 닫아도 필터/정렬/페이지네이션 상태가 사라지면 사용자 입장에서는 문맥이 복원되지 않는다.

### 7) 슬롯별 loading/error 경계를 안 만든다

보조 슬롯이 실패했다고 전체 페이지가 흔들릴 필요는 없다. Parallel Routes의 장점은 슬롯 단위 독립성인데, 이를 활용하지 않으면 복잡도만 늘고 이점은 못 얻는다.

### 8) 모달 오픈 경로와 정식 상세 경로의 메타데이터 책임을 섞는다

SEO 메타, Open Graph, canonical, 구조화 데이터는 보통 정식 상세 페이지가 책임지는 편이 명확하다. 인터셉트된 모달은 브라우징 UX 레이어에 가깝다.

### 9) soft navigation만 테스트하고 direct visit을 빼먹는다

이 패턴은 “어떻게 들어왔는가”에 따라 UI가 달라지므로 둘 다 꼭 확인해야 한다.

- 목록에서 클릭
- 주소창 직접 입력
- 새로고침
- 새 탭 열기
- 뒤로 가기/앞으로 가기

### 10) 단순 탭 UI까지 Parallel Routes로 해결하려 든다

슬롯 기반 라우팅은 강력하지만 비용이 있다. 탭 몇 개 전환이면 search params나 로컬 상태로 충분한 경우가 많다.

---

## 실무 체크리스트

### 1) 문제 정의

- [ ] 이 UI는 단순 팝업이 아니라 **공유 가능한 상세 리소스**인가?
- [ ] direct visit 시 full page로 보여주는 것이 자연스러운가?
- [ ] 뒤로 가기 시 목록 문맥 복원이 핵심 UX인가?

### 2) 구조 설계

- [ ] `@modal` 같은 슬롯이 정말 필요한가?
- [ ] 슬롯 이름이 UI 책임을 명확히 드러내는가?
- [ ] `default.tsx` 로 비활성 슬롯 기본값을 정의했는가?
- [ ] 정식 상세 페이지와 인터셉트 모달의 역할이 분리되어 있는가?

### 3) 데이터/뷰 재사용

- [ ] 상세 데이터 조회 로직이 공통 함수로 분리되어 있는가?
- [ ] full page와 modal이 공통 상세 뷰를 공유하는가?
- [ ] 권한 체크/에러 처리 기준이 두 경로에서 동일한가?

### 4) UX 동작

- [ ] 목록에서 클릭 시 soft navigation으로 모달이 뜨는가?
- [ ] 주소창 직접 입력 시 full page로 열리는가?
- [ ] 뒤로 가기 시 모달만 닫히는가?
- [ ] 목록 스크롤/필터/정렬 문맥이 충분히 유지되는가?
- [ ] 닫기 버튼에 `back()` fallback 전략이 있는가?

### 5) 운영 품질

- [ ] 슬롯별 `loading.tsx`, `error.tsx` 필요 여부를 검토했는가?
- [ ] 모바일/데스크톱 프레젠테이션 차이를 합의했는가?
- [ ] E2E 테스트에 soft navigation/hard navigation 모두 포함했는가?
- [ ] canonical, OG, analytics 경로 집계 기준이 일관적인가?

---

## 한 줄 정리

Next.js Parallel Routes와 Intercepting Routes의 핵심은 “모달을 예쁘게 띄우는 법”이 아니다. **같은 상세 URL을 유지하면서도, 사용자가 어디서 어떻게 들어왔는지에 따라 목록 문맥의 모달 UX와 정식 상세 페이지 UX를 모두 성립시키는 정보 구조를 설계하는 법**이다.
