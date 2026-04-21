---
layout: post
title: "Next.js Metadata API 실전: canonical, Open Graph, robots, JSON-LD를 URL 정합성과 함께 설계하는 법"
date: 2026-04-21 11:40:00 +0900
categories: [nextjs]
tags: [study, nextjs, metadata, seo, canonical, open-graph, robots, json-ld, app-router]
permalink: /nextjs/2026/04/21/study-nextjs-metadata-canonical-open-graph-json-ld-robots.html
---

## 배경: App Router에서 메타데이터는 `<title>` 몇 줄이 아니라 URL 신뢰도와 배포 품질 문제다

Next.js App Router로 서비스를 운영하다 보면 메타데이터는 뒤로 밀리기 쉽다.

처음에는 보통 이렇게 접근한다.

- 페이지마다 `title` 정도만 넣는다
- 상세 페이지는 일단 상품명이나 게시글 제목만 노출한다
- 공유 이미지는 나중에 붙이자고 미룬다
- 검색 페이지, 필터 페이지, 내부 대시보드도 별 구분 없이 동일한 인덱싱 정책을 둔다
- canonical은 생각하지 않고 쿼리스트링이 붙은 URL을 그대로 노출한다

초기에는 크게 문제 없어 보인다. 그런데 트래픽이 늘고 경로가 많아지면 메타데이터 문제가 곧 운영 문제로 바뀐다.

- 같은 콘텐츠가 `?sort=latest`, `?page=2`, `?tab=overview` 등으로 중복 색인된다
- Open Graph가 비어 공유 카드가 들쭉날쭉하게 보인다
- 상품 상세는 잘 노출되는데 검색 결과 페이지까지 색인돼 저품질 페이지 비중이 높아진다
- 다국어 서비스인데 canonical, alternate, hreflang이 꼬여 언어별 대표 URL이 불명확해진다
- `generateMetadata`에서 데이터 조회를 무심코 중복 호출해 TTFB가 늘어난다
- JSON-LD를 여기저기 흩뿌려 구조화 데이터가 페이지 실제 내용과 어긋난다

이 문제의 핵심은 SEO 문법 자체보다 **URL 정합성과 페이지 의도 표현을 코드로 일관되게 유지하지 못하는 것**이다.

App Router에서는 메타데이터가 레이아웃과 페이지 트리에 연결된다. 즉 컴포넌트 구조를 설계하듯, 메타데이터도 다음 질문에 답할 수 있어야 한다.

1. 이 경로의 대표 URL은 무엇인가
2. 이 페이지는 색인돼야 하는가
3. 공유 카드에는 어떤 맥락과 이미지를 노출할 것인가
4. 동적 경로에서 제목, 설명, canonical을 어떤 기준으로 조립할 것인가
5. JSON-LD와 본문 내용을 어떻게 일치시킬 것인가

이 글의 목표는 단순하다.

> **Next.js Metadata API를 "검색엔진용 꾸밈"이 아니라 URL, 색인 정책, 공유 경험, 구조화 데이터를 함께 다루는 운영 레이어로 이해하는 것**

중급 이상 개발자를 기준으로, 배경, 핵심 개념, 실무 예시, 트레이드오프, 흔한 실수, 체크리스트, 한 줄 정리까지 한 번에 다룬다.

---

## 먼저 큰 그림: 메타데이터 설계는 결국 "대표 URL과 크롤링 의도"를 명시하는 일이다

메타데이터를 잘못 다루는 팀은 보통 태그 수집부터 시작한다. `title`, `description`, `og:image`, `robots`를 각각 따로 본다. 실무에서는 이 순서보다 먼저 질문이 서야 한다.

### 1) 이 페이지는 검색엔진에 어떤 리소스로 보이길 원하는가

예를 들어 상품 상세는 하나의 대표 URL로 모여야 한다. 반면 정렬, 필터, 임시 캠페인 파라미터는 대표 URL의 부수적 표현일 수 있다.

### 2) 이 페이지는 색인 가치가 있는가

- 상품 상세, 문서, 블로그 글은 보통 색인 가치가 높다
- 로그인, 결제 완료, 내부 검색, 사용자별 대시보드는 보통 낮다
- 같은 데이터라도 페이지 맥락에 따라 색인 정책이 달라질 수 있다

### 3) 사람과 봇에게 각각 어떤 문맥을 전달할 것인가

- 검색 결과에는 `title`, `description`, canonical이 중요하다
- 소셜 공유에는 Open Graph, Twitter 카드가 중요하다
- 지식 그래프나 리치 리절트에는 JSON-LD가 중요하다

즉 메타데이터는 태그 모음이 아니라 **페이지 정체성 계약서**에 가깝다.

이 관점으로 보면 좋은 설계 기준이 선다.

- 루트 레이아웃에는 사이트 전역 기본값을 둔다
- 섹션 레이아웃에는 도메인별 공통 정책을 둔다
- 페이지에서는 리소스 고유 정보만 얹는다
- canonical은 "실제 대표 URL" 기준으로 만든다
- robots는 마케팅 욕심이 아니라 페이지 가치 기준으로 결정한다
- JSON-LD는 본문 렌더 결과와 동일한 소스 데이터에서 만든다

---

## 핵심 개념 1: Metadata API는 head 태그를 흩뿌리는 도구가 아니라 라우트 트리 병합 규칙이다

App Router의 메타데이터가 유용한 이유는 단순히 타입 안전성 때문만이 아니다. 레이아웃과 페이지가 **트리 단위로 메타데이터를 합성**한다는 점이 핵심이다.

예를 들어 이런 구조를 생각해 보자.

- `app/layout.tsx`: 사이트 전역 제목 템플릿, 기본 OG 이미지, `metadataBase`
- `app/blog/layout.tsx`: 블로그 섹션 공통 설명, 작성자 기본값
- `app/blog/[slug]/page.tsx`: 글 단위 title, description, canonical, article OG

이 구조가 좋은 이유는 책임이 분리되기 때문이다.

- 전역 레이아웃은 브랜드와 사이트 레벨 정책
- 섹션 레이아웃은 도메인 컨텍스트
- 페이지는 리소스 고유 속성

### 루트에서 먼저 고정해야 할 기본값

```tsx
// app/layout.tsx
import type { Metadata } from "next";

export const metadata: Metadata = {
  metadataBase: new URL("https://example.com"),
  title: {
    default: "Example",
    template: "%s | Example",
  },
  description: "실무형 개발 아티클과 제품 업데이트를 다루는 사이트",
  openGraph: {
    type: "website",
    siteName: "Example",
    locale: "ko_KR",
    images: [
      {
        url: "/og/default.png",
        width: 1200,
        height: 630,
        alt: "Example 기본 공유 이미지",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
  },
};
```

여기서 특히 중요한 것은 `metadataBase` 다. 이 값이 없으면 canonical이나 OG 이미지에서 절대 URL 조립이 일관되지 않기 쉽다.

### 메타데이터를 병합할 때 주의할 점

레이아웃과 페이지는 자연스럽게 합쳐지지만, 모든 필드가 직관적으로 "깊게 merge" 되는 것은 아니다. 그래서 팀에서 다음 원칙을 두는 편이 안전하다.

- 전역에서 공통 기본값을 둔다
- 페이지에서는 필요한 필드만 명시적으로 덮어쓴다
- 상속을 기대하기보다, 페이지에서 중요한 필드는 완결적으로 작성한다
- Open Graph와 Twitter 이미지는 "부모가 있으니 붙겠지"라고 가정하지 않는다

실무에서는 메타데이터 버그 상당수가 "부모의 값이 남아 있을 줄 알았는데 페이지에서 일부만 덮으며 의도와 달라진 경우"에서 나온다.

---

## 핵심 개념 2: canonical은 SEO 장식이 아니라 "같은 문서의 대표 주소"를 선언하는 장치다

canonical을 흔히 검색엔진 최적화 옵션 정도로 생각하지만, 실제 운영에서는 **URL 정책 문서의 코드 표현**에 가깝다.

대표적으로 canonical이 필요한 상황은 다음과 같다.

- 정렬, 필터, 페이지네이션 쿼리스트링이 붙는 목록 페이지
- 마케팅 캠페인 파라미터가 붙는 랜딩 페이지
- 모바일/데스크톱, 미러 경로, locale 경로 등 표현 방식이 여러 개인 경우
- 상세 페이지가 모달 진입, 직접 진입, 추천 경로 진입 등 여러 UI 흐름을 가질 때

### 나쁜 canonical 패턴

- 현재 URL 전체를 그대로 canonical로 넣는다
- 추적 파라미터가 붙은 URL도 대표 URL로 본다
- 상세 리소스가 아니라 검색 결과 URL을 대표 URL로 둔다
- SSR에서 조립한 경로와 클라이언트 라우팅 경로가 다르다

### 좋은 canonical 기준

1. 사용자가 공유해도 무방한 URL인가  
2. 같은 리소스를 가장 안정적으로 대표하는가  
3. 쿼리스트링이 없어도 의미가 유지되는가  
4. 경로 구조가 바뀌더라도 도메인 정책상 오래 유지할 수 있는가

App Router에서는 `alternates.canonical`로 표현하는 것이 가장 명확하다.

```tsx
import type { Metadata } from "next";

export const metadata: Metadata = {
  alternates: {
    canonical: "/blog",
  },
};
```

`metadataBase`가 설정되어 있다면 상대 경로 기반 canonical 선언이 깔끔하다.

### 동적 상세 페이지에서 canonical 만들기

```tsx
// app/blog/[slug]/page.tsx
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getPostBySlug } from "@/lib/posts";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const post = await getPostBySlug(slug);

  if (!post) {
    return {
      title: "게시글을 찾을 수 없습니다",
      robots: {
        index: false,
        follow: false,
      },
    };
  }

  return {
    title: post.title,
    description: post.summary,
    alternates: {
      canonical: `/blog/${post.slug}`,
    },
  };
}

export default async function BlogDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const post = await getPostBySlug(slug);

  if (!post) notFound();

  return <article>{post.title}</article>;
}
```

핵심은 canonical과 본문이 **같은 리소스 조회 결과에 기대고 있어야 한다**는 점이다. 경로는 `/blog/[slug]` 인데 canonical은 오래된 별칭 필드를 참고하거나, 본문은 새 slug를 쓰는데 metadata는 구 slug를 쓰면 색인 신호가 갈라진다.

---

## 핵심 개념 3: `generateMetadata`는 공짜가 아니다, 데이터 패치 책임을 같이 설계해야 한다

`generateMetadata`가 편리해서 모든 동적 메타데이터를 여기 몰아넣기 쉽다. 하지만 이 함수도 결국 서버에서 실행된다. 즉 다음 비용이 생긴다.

- 데이터 조회 한 번 더 발생 가능
- 외부 API 실패가 head 렌더 실패로 이어질 수 있음
- 느린 metadata 조회가 TTFB를 밀어낼 수 있음
- 페이지 본문 조회와 메타데이터 조회의 캐시 정책이 어긋날 수 있음

### 실무에서 흔한 안티패턴

```tsx
export async function generateMetadata({ params }) {
  const product = await fetchProduct(params.id);
  return { title: product.name };
}

export default async function Page({ params }) {
  const product = await fetchProduct(params.id);
  return <ProductDetail product={product} />;
}
```

이 구조는 보기엔 단순하지만, `fetchProduct`가 DB 조회나 외부 API 호출이면 중복 비용이 발생할 수 있다.

### 더 안전한 접근

- 같은 fetch 함수가 Next.js fetch 캐시를 활용하도록 맞춘다
- DB 직접 조회라면 캐시 레이어를 붙이거나 비용을 인지하고 쓴다
- 메타데이터에 꼭 필요한 최소 데이터만 조회한다
- 공유 이미지, 설명문, canonical 생성에 필요한 필드만 가져온다

예를 들어 상품 상세라면 메타데이터용 최소 projection을 따로 두는 편이 낫다.

```ts
export async function getProductMetadataView(id: string) {
  return db.product.findUnique({
    where: { id },
    select: {
      id: true,
      slug: true,
      name: true,
      summary: true,
      ogImageUrl: true,
      isPublic: true,
    },
  });
}
```

이렇게 두면 본문에서 재고, 가격 이력, 추천 상품까지 무겁게 읽더라도 메타데이터 쪽은 가볍게 유지할 수 있다.

### `parent` 메타데이터를 활용할 때의 기준

App Router에서는 `generateMetadata` 두 번째 인자로 부모 메타데이터를 받아 확장할 수 있다. 이 기능은 유용하지만 남용하면 읽기 난도가 급격히 올라간다.

좋은 사용 예시는 아래와 같다.

- 부모 레이아웃의 기본 OG 이미지를 유지하되, 상세 페이지에서 첫 번째 이미지만 앞에 추가
- 섹션별 기본 title template 위에 페이지 제목만 얹기

반대로 좋지 않은 경우도 있다.

- 부모 메타데이터를 깊게 복제해 조건마다 복잡하게 분기
- 실제 최종 head 결과를 코드만 읽고 예측하기 어려운 구조

메타데이터는 렌더링 결과를 사람이 추론할 수 있어야 운영이 쉽다. 지나친 동적 조합은 코드 재사용보다 디버깅 비용이 더 커질 수 있다.

---

## 핵심 개념 4: Open Graph와 Twitter 카드는 "공유용 미리보기"가 아니라 클릭 전 컨텍스트 설계다

실무에서 OG 태그가 중요한 이유는 단순히 카드가 예뻐 보여서가 아니다. 링크를 받는 사람은 페이지 본문보다 먼저 공유 카드를 본다. 즉 제목, 설명, 이미지가 첫 번째 제품 경험이 된다.

### 최소 기준

- `title`
- `description`
- `openGraph.title`
- `openGraph.description`
- `openGraph.images`
- `twitter.card`

### 자주 놓치는 점

- 설명이 본문과 다르게 너무 마케팅 문구 중심이라 낚시처럼 보임
- OG 이미지가 절대 URL이 아니거나 배포 환경별 경로가 틀림
- 기본 이미지 하나만 써서 모든 페이지가 같은 카드로 보임
- 다국어 페이지인데 locale 맥락이 카드에 드러나지 않음

상품 상세나 블로그 글처럼 리소스 중심 페이지는 리소스별 OG를 두는 편이 낫다.

```tsx
return {
  title: post.title,
  description: post.summary,
  openGraph: {
    type: "article",
    title: post.title,
    description: post.summary,
    url: `/blog/${post.slug}`,
    images: post.ogImageUrl
      ? [
          {
            url: post.ogImageUrl,
            width: 1200,
            height: 630,
            alt: post.title,
          },
        ]
      : [
          {
            url: "/og/blog-default.png",
            width: 1200,
            height: 630,
            alt: "블로그 기본 이미지",
          },
        ],
  },
  twitter: {
    card: "summary_large_image",
    title: post.title,
    description: post.summary,
    images: post.ogImageUrl ? [post.ogImageUrl] : ["/og/blog-default.png"],
  },
};
```

### OG 이미지 운영 기준

중요한 것은 디자인보다 **일관된 생성 규칙**이다.

- 제목 길이 제한을 둔다
- 제품명, 문서 제목, 작성일 등 노출 규칙을 표준화한다
- 다국어 폰트, 줄바꿈, 긴 제목 말줄임을 처리한다
- fallback 이미지를 둔다
- 이미지가 늦게 생성되거나 실패할 때 기본 카드가 깨지지 않게 한다

공유 카드 품질은 검색 유입보다 느리게 드러나지만, 커뮤니티 확산과 링크 신뢰도에는 꽤 크게 작용한다.

---

## 핵심 개념 5: `robots`는 "일단 index"가 기본값이 아니라 페이지 가치 필터다

robots 정책은 종종 무조건 개방으로 출발한다. 하지만 실무에서는 색인될수록 좋은 페이지보다, 색인되면 오히려 품질 신호를 흐리는 페이지가 적지 않다.

대표적으로 `noindex`를 검토할 페이지는 아래와 같다.

- 내부 검색 결과 페이지
- 로그인, 회원가입, 비밀번호 재설정
- 결제 완료, 초대 수락, 1회성 토큰 진입 페이지
- 필터 조합이 과도하게 많은 faceted navigation 경로
- 사용자별 대시보드, 주문내역, 알림 페이지
- 실험용 랜딩, 미완성 캠페인 페이지

Next.js에서는 다음처럼 표현할 수 있다.

```tsx
export const metadata = {
  robots: {
    index: false,
    follow: false,
    googleBot: {
      index: false,
      follow: false,
      noimageindex: true,
    },
  },
};
```

### 언제 `nofollow`까지 갈 것인가

실무에서는 `noindex, follow` 와 `noindex, nofollow`를 구분해 쓰는 편이 좋다.

- 내부 검색, 정렬 페이지처럼 링크 탐색은 허용해도 되는 경우: `noindex, follow`
- 로그인 콜백, 토큰 소비 페이지처럼 크롤러가 따라갈 가치가 없는 경우: `noindex, nofollow`

무조건 `noindex, nofollow` 로 통일하면 사이트 구조 탐색 신호까지 과도하게 닫을 수 있다. 페이지 성격별로 나눠야 한다.

---

## 핵심 개념 6: JSON-LD는 Metadata API의 부속 옵션이 아니라 "본문과 같은 사실"을 다른 형식으로 쓰는 일이다

구조화 데이터는 종종 플러그인처럼 붙인다. 그러나 JSON-LD가 진짜 유효하려면 페이지 실제 내용과 같은 사실을 말해야 한다.

예를 들어 블로그 글이라면 다음 정보가 본문과 일치해야 한다.

- 제목
- 설명
- 발행일/수정일
- 작성자
- 대표 이미지
- canonical URL

### 실무에서 많이 깨지는 이유

- 본문은 최신 수정일인데 JSON-LD는 최초 발행일만 유지
- canonical은 새 slug인데 JSON-LD `url`은 예전 경로
- 대표 이미지 교체 후 OG만 바꾸고 JSON-LD는 그대로 둠
- 작성자, 조직명, 로고가 페이지마다 제각각

App Router에서는 JSON-LD를 대개 페이지 컴포넌트에서 스크립트로 주입한다. 핵심은 metadata와 다른 소스가 아니라, **같은 조회 결과로부터 파생**하는 것이다.

```tsx
function BlogPostingJsonLd({ post }: { post: Post }) {
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "BlogPosting",
    headline: post.title,
    description: post.summary,
    datePublished: post.publishedAt,
    dateModified: post.updatedAt,
    author: {
      "@type": "Person",
      name: post.authorName,
    },
    image: [post.ogImageUrl],
    mainEntityOfPage: `https://example.com/blog/${post.slug}`,
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
    />
  );
}
```

여기서 중요한 것은 JSON-LD 문법보다 데이터 출처다. metadata와 JSON-LD가 같은 `post` 객체를 기반으로 만들어지면 불일치 확률이 크게 줄어든다.

---

## 실무 예시 1: 블로그 상세 페이지를 메타데이터 중심으로 설계하기

블로그 상세는 메타데이터 설계의 기본 예시로 좋다. 요구사항이 명확하기 때문이다.

- 색인 대상이다
- canonical이 분명하다
- 공유 카드 품질이 중요하다
- JSON-LD를 붙이기 좋다
- 작성일, 수정일, 작성자 등 구조화 정보가 존재한다

### 권장 구조

- `app/layout.tsx`: 사이트 공통 metadataBase, 기본 title template
- `app/blog/layout.tsx`: 블로그 섹션 기본 설명
- `app/blog/[slug]/page.tsx`: 글별 metadata + JSON-LD

```tsx
// app/blog/[slug]/page.tsx
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getPostBySlug } from "@/lib/posts";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const post = await getPostBySlug(slug);

  if (!post || !post.published) {
    return {
      title: "게시글을 찾을 수 없습니다",
      robots: { index: false, follow: false },
    };
  }

  return {
    title: post.title,
    description: post.summary,
    alternates: {
      canonical: `/blog/${post.slug}`,
    },
    openGraph: {
      type: "article",
      url: `/blog/${post.slug}`,
      title: post.title,
      description: post.summary,
      publishedTime: post.publishedAt,
      modifiedTime: post.updatedAt,
      authors: [post.authorName],
      images: [{ url: post.ogImageUrl, width: 1200, height: 630, alt: post.title }],
    },
    twitter: {
      card: "summary_large_image",
      title: post.title,
      description: post.summary,
      images: [post.ogImageUrl],
    },
  };
}

export default async function BlogPostPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const post = await getPostBySlug(slug);

  if (!post || !post.published) notFound();

  return (
    <>
      <BlogPostingJsonLd post={post} />
      <article>{/* ... */}</article>
    </>
  );
}
```

이 구조의 장점은 다음과 같다.

- 색인 정책과 본문 노출 정책이 일치한다
- canonical, OG, JSON-LD가 같은 데이터 소스를 본다
- unpublished 콘텐츠의 색인 누출을 막기 쉽다
- 프리뷰, 예약 발행, 초안 상태 분기까지 확장 가능하다

---

## 실무 예시 2: 검색/필터 페이지는 색인보다 canonical과 robots 설계가 더 중요하다

커머스나 문서 검색 페이지에서는 사용자가 보는 URL 수가 폭발하기 쉽다.

예를 들어 아래 URL이 모두 열릴 수 있다.

- `/products`
- `/products?sort=price_asc`
- `/products?brand=abc`
- `/products?brand=abc&color=black&size=270`
- `/products?page=7`

이때 모든 URL을 색인하게 두면 중복 페이지가 늘고 품질 관리가 어렵다.

### 실무 선택지

#### 1) 목록 루트만 index, 필터 조합은 noindex

가장 보수적이지만 운영이 쉽다.

#### 2) 일부 핵심 카테고리 조합만 index

마케팅 팀과 협업이 필요하고 룰 관리 비용이 생긴다.

#### 3) 전부 canonical을 루트로 모음

단순하지만 실제로 독립 가치가 있는 페이지까지 과도하게 합칠 수 있다.

대부분 팀에서는 1번이나 2번이 현실적이다.

```tsx
// app/products/page.tsx
import type { Metadata } from "next";

export async function generateMetadata({
  searchParams,
}: {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}): Promise<Metadata> {
  const params = await searchParams;
  const hasFilter = Boolean(params.brand || params.color || params.size || params.sort || params.page);

  if (hasFilter) {
    return {
      title: "상품 검색 결과",
      description: "필터가 적용된 상품 검색 결과입니다.",
      alternates: {
        canonical: "/products",
      },
      robots: {
        index: false,
        follow: true,
      },
    };
  }

  return {
    title: "상품 목록",
    description: "카테고리별 상품을 탐색할 수 있습니다.",
    alternates: {
      canonical: "/products",
    },
  };
}
```

이 예시의 포인트는 검색 결과를 무조건 차단하는 것이 아니라, **어떤 조합이 대표 URL이 아닌지 명시**하는 데 있다.

---

## 실무 예시 3: 다국어 서비스에서는 `alternates.languages`가 경로 정책과 함께 움직여야 한다

다국어 사이트는 메타데이터 실수가 더 자주 치명적이다. `/ko/docs/setup`, `/en/docs/setup` 같이 같은 문서를 여러 언어로 제공할 때 다음이 꼬이기 쉽다.

- canonical이 항상 한 언어로 고정됨
- `hreflang` 대응이 빠짐
- 번역이 없는 페이지에서 잘못된 alternate를 노출함

App Router에서는 언어 경로 정책이 정해져 있다면 metadata도 같은 정책을 따라가게 해야 한다.

```tsx
return {
  alternates: {
    canonical: `/ko/docs/${doc.slug}`,
    languages: {
      "ko-KR": `/ko/docs/${doc.slug}`,
      "en-US": `/en/docs/${doc.slug}`,
    },
  },
};
```

여기서 중요한 것은 자동 생성보다 **실제 번역 존재 여부 검증**이다. 영어 문서가 아직 없는데 alternate만 먼저 노출하면 오히려 품질이 떨어진다.

---

## 트레이드오프: 중앙집중 메타데이터와 페이지별 세밀 제어 사이 균형 잡기

메타데이터 설계에서도 늘 같은 긴장이 있다. 한쪽 끝은 전역 추상화, 다른 한쪽 끝은 페이지별 완전 수동 제어다.

### 선택지 1) 루트/섹션에서 최대한 공통화

장점:

- 중복 감소
- 브랜드 일관성 확보
- 신규 페이지 추가 속도 향상

단점:

- 예외 케이스 처리 시 추상화가 급격히 복잡해질 수 있음
- 최종 결과를 추론하기 어려워질 수 있음

### 선택지 2) 페이지별 완전 명시

장점:

- 최종 head 결과가 명확함
- 디버깅이 쉬움
- 리소스 특화 제어가 쉬움

단점:

- 중복 증가
- 빠뜨릴 가능성 증가
- 브랜드/로고/기본 이미지가 제각각 될 수 있음

### 실무 추천

- 전역: `metadataBase`, title template, 기본 siteName, 공통 OG fallback
- 섹션: 섹션 설명, 작성자/도메인 공통값
- 페이지: title, description, canonical, robots, 리소스별 OG, JSON-LD

즉 공통값은 끌어올리고, **검색 품질에 직접 영향을 주는 핵심 필드**는 페이지에서 명시하는 편이 안전하다.

---

## 흔한 실수 1: canonical을 현재 URL 그대로 넣기

브라우저 주소창 값을 그대로 canonical로 쓰면 추적 파라미터, A/B 파라미터, 정렬 쿼리까지 대표 URL로 굳어질 수 있다.

### 대응

- canonical 생성은 경로 정책 함수로 관리한다
- `pathname + 허용된 핵심 세그먼트`만 사용한다
- 추적 파라미터는 canonical 계산에서 제외한다

---

## 흔한 실수 2: `generateMetadata`와 본문이 서로 다른 데이터를 본다

본문은 최신 DB 상태를 보는데 metadata는 캐시된 API를 보거나, 반대로 metadata는 새 slug를 아는데 본문은 옛 slug를 보는 식이다. 이러면 검색엔진과 사용자 경험이 분리된다.

### 대응

- canonical, title, JSON-LD를 같은 조회 결과에서 파생한다
- 메타데이터 전용 projection을 두더라도 동일한 원천 모델에 기대게 한다
- 리소스 공개 여부 판단도 같은 계층에서 한다

---

## 흔한 실수 3: noindex 페이지를 내부 링크 허브로 만들어 둔다

로그인 콜백, 토큰 페이지, 유저 개인 화면 등이 사이트 내부 링크 탐색의 핵심 경로가 되면 크롤링 흐름이 불필요하게 꼬일 수 있다.

### 대응

- 크롤러가 따라갈 가치가 있는 공개 경로를 분리한다
- 내부 전용 화면은 공개 네비게이션 허브에서 최대한 멀리 둔다
- 필요하면 sitemap 정책도 함께 조정한다

---

## 흔한 실수 4: OG 이미지와 JSON-LD 이미지를 따로 관리한다

한쪽만 교체돼도 공유 카드와 구조화 데이터가 어긋난다.

### 대응

- 대표 이미지 계산 함수를 하나 둔다
- metadata와 JSON-LD가 같은 image source를 사용하게 한다
- 이미지 생성 실패 시 fallback 규칙을 문서화한다

---

## 흔한 실수 5: preview, draft, private 콘텐츠가 색인된다

CMS 연동 프로젝트에서 자주 터지는 문제다. 초안/프리뷰 경로가 robots 정책 없이 열려 있으면 검색엔진이 예상치 못하게 접근할 수 있다.

### 대응

- preview, draft, internal 경로는 기본적으로 `noindex`
- 비공개 리소스는 metadata 이전에 접근 제어부터 막는다
- 공개 여부가 불명확하면 보수적으로 차단한다

---

## 운영 체크리스트

### URL/대표성

- [ ] canonical이 실제 대표 URL 정책과 일치하는가
- [ ] 추적 파라미터, 필터 파라미터가 canonical에 섞이지 않는가
- [ ] locale 경로가 있다면 alternate language가 실제 번역 존재와 일치하는가

### 색인 정책

- [ ] 검색 가치가 낮은 페이지에 `noindex`가 적용되는가
- [ ] `noindex, follow` 와 `noindex, nofollow`를 페이지 성격별로 구분했는가
- [ ] unpublished, private, preview 리소스가 색인되지 않는가

### 공유 품질

- [ ] 모든 핵심 상세 페이지에 OG 이미지 fallback이 있는가
- [ ] title, description, OG, Twitter가 본문과 같은 메시지를 전달하는가
- [ ] 이미지 URL이 절대 경로로 안정적으로 해석되는가

### 구조화 데이터

- [ ] JSON-LD가 본문과 동일한 데이터 소스를 사용하는가
- [ ] 발행일, 수정일, 작성자, 이미지, canonical이 일치하는가
- [ ] 리치 리절트 대상 페이지의 스키마 타입이 적절한가

### 성능/운영

- [ ] `generateMetadata`가 과도한 네트워크 호출을 만들지 않는가
- [ ] 메타데이터 조회 실패 시 안전한 fallback이 있는가
- [ ] head 결과를 실제 렌더 기준으로 점검하는 QA 루틴이 있는가

---

## 한 줄 정리

> **Next.js Metadata API의 핵심은 태그를 많이 넣는 것이 아니라, 각 경로의 대표 URL, 색인 의도, 공유 맥락, 구조화 데이터를 같은 사실 위에 일관되게 올려놓는 것**
