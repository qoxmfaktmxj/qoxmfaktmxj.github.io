---
layout: post
title: "Next.js 이미지 최적화 실전: next/image, remotePatterns, sizes, CDN Cache, LCP를 운영 기준으로 설계하는 법"
date: 2026-06-29 11:50:00 +0900
categories: [nextjs]
tags: [study, nextjs, image-optimization, next-image, remote-patterns, sizes, cdn, lcp, cache, performance, security]
permalink: /nextjs/2026/06/29/study-nextjs-image-optimization-remote-patterns-sizes-cdn-lcp.html
---

## 배경: 이미지는 프론트엔드 성능 문제이면서 동시에 보안, 비용, 운영 문제다

Next.js 프로젝트에서 이미지 최적화는 처음에는 단순한 컴포넌트 사용법처럼 보인다.

```tsx
import Image from "next/image";

export function ProductCard() {
  return (
    <Image
      src="/products/chair.jpg"
      alt="원목 의자"
      width={640}
      height={480}
    />
  );
}
```

이 정도 예제만 보면 `img` 대신 `Image`를 쓰면 끝이라고 느끼기 쉽다. 실제로 작은 서비스에서는 이 판단이 어느 정도 맞아 보인다. 로컬 이미지는 자동으로 크기가 잡히고, 브라우저에 맞는 포맷이 내려가며, lazy loading도 기본으로 적용된다. 문제는 운영 트래픽을 받기 시작한 뒤다.

- 모바일에서 카드 이미지는 선명한데 LCP가 4초를 넘는다.
- `fill`을 썼더니 레이아웃은 맞지만 실제로는 3840px 이미지가 내려간다.
- CMS 이미지 도메인을 열어 두었더니 외부 사용자가 의도하지 않은 원격 이미지를 최적화 API에 태운다.
- CDN 앞단에서 `Accept` 헤더를 전달하지 않아 WebP/AVIF 협상이 깨진다.
- 이미지 원본이 바뀌었는데 최적화 캐시가 남아 사용자는 오래된 썸네일을 본다.
- 상세 페이지의 첫 화면 이미지는 lazy loading되어 LCP가 늦고, 목록의 수십 장 이미지는 동시에 요청되어 비용이 튄다.
- SVG를 허용했다가 CSP 없이 직접 렌더링되어 보안 검토에서 막힌다.
- `sizes`를 빼먹어 작은 카드 이미지에도 viewport 폭 기준 srcset이 생성된다.

즉 이미지 최적화의 본질은 "용량을 줄인다"가 아니다.

> **Next.js 이미지 최적화의 핵심은 이미지가 어떤 레이아웃 슬롯에 표시되는지, 어떤 출처에서 오며, 어떤 캐시 수명과 CDN 경계를 거치고, 어떤 이미지를 LCP 후보로 다룰지를 명시적으로 설계하는 것이다.**

이 글은 `next/image` 속성 목록을 나열하는 글이 아니다. 중급 이상 개발자를 기준으로 운영 서비스에서 이미지 최적화를 설계할 때 고정해야 할 기준을 정리한다.

1. `width/height`, `fill`, `sizes`는 각각 어떤 책임을 갖는가
2. remote image를 열 때 `remotePatterns`를 왜 좁게 잡아야 하는가
3. LCP 이미지는 lazy image와 어떻게 다르게 다뤄야 하는가
4. CDN, `Accept` 헤더, 포맷 협상, cache TTL은 어디서 깨지는가
5. SVG, redirect, local IP, 큰 원본 이미지는 어떤 보안·비용 리스크를 만드는가
6. 실무 컴포넌트와 설정을 어떻게 나눠야 재사용과 운영 통제가 쉬운가
7. 흔한 실수와 배포 전 체크리스트는 무엇인가

---

## 핵심개념 1: 이미지 최적화는 "컴포넌트"가 아니라 "요청 파이프라인"이다

`next/image`를 쓰면 브라우저에는 결국 `<img>`가 렌더링된다. 하지만 그 앞뒤에는 생각보다 많은 단계가 붙는다.

1. React 컴포넌트가 `src`, `width`, `height`, `sizes`, `quality`를 받는다.
2. Next.js가 적절한 `srcset` 후보를 만든다.
3. 브라우저가 viewport, DPR, `sizes`를 기준으로 실제 다운로드할 후보를 고른다.
4. 원격 이미지라면 Next.js Image Optimization API가 원본을 가져온다.
5. 서버가 포맷, 품질, 크기를 변환한다.
6. 변환 결과가 Next.js 캐시 또는 CDN에 저장된다.
7. 이후 같은 조건의 요청은 캐시에서 재사용된다.

여기서 중요한 점은 **이미지 성능은 서버만 결정하지도 않고, 브라우저만 결정하지도 않는다**는 것이다. 서버는 후보를 만들고, 브라우저는 그중 하나를 고른다. 개발자가 `sizes`를 잘못 주면 서버가 아무리 최적화해도 브라우저는 큰 후보를 고를 수 있다. CDN이 `Accept` 헤더를 전달하지 않으면 서버가 브라우저별 포맷을 제대로 판단하지 못한다. 원본 캐시 수명이 길면 바뀐 이미지를 즉시 반영하기 어렵다.

그래서 이미지 최적화 설계는 아래 네 질문으로 시작하는 편이 좋다.

- 이 이미지는 레이아웃에서 몇 px 슬롯을 차지하는가?
- 이 이미지는 LCP 후보인가, 아니면 스크롤 아래의 보조 이미지인가?
- 이 이미지는 로컬 빌드 산출물인가, CMS·S3·외부 CDN의 원격 이미지인가?
- 이 이미지는 자주 바뀌는가, 아니면 파일명 또는 해시로 불변 캐시가 가능한가?

이 네 가지를 모르면 `Image` 컴포넌트 속성을 고르는 것이 감으로 바뀐다.

---

## 핵심개념 2: `width/height`는 표시 크기가 아니라 비율과 후보 생성의 기준이다

초기 개발자가 가장 자주 오해하는 부분이 `width`와 `height`다.

```tsx
<Image
  src="/avatar.png"
  alt="사용자 프로필"
  width={96}
  height={96}
/>
```

이 값은 단순히 CSS 표시 크기를 고정하기 위한 값이 아니다. Next.js와 브라우저가 이미지의 비율을 알고 layout shift를 피하게 만드는 기준이며, 어떤 크기의 최적화 후보를 만들지 결정하는 데도 관여한다.

정적 import를 쓰면 Next.js가 원본 이미지의 크기를 빌드 시점에 파악할 수 있다.

```tsx
import hero from "@/public/images/hr-dashboard-hero.png";
import Image from "next/image";

export function HeroImage() {
  return (
    <Image
      src={hero}
      alt="인사 대시보드 요약 화면"
      placeholder="blur"
    />
  );
}
```

이 방식은 운영상 장점이 크다.

- 원본 파일이 빌드 산출물에 포함되어 출처가 명확하다.
- 파일 내용 기반 해시를 활용할 수 있어 장기 캐시에 유리하다.
- width/height를 직접 틀리게 적을 가능성이 줄어든다.
- blur placeholder를 자동으로 쓰기 쉬운 편이다.

반대로 CMS 이미지처럼 런타임 URL을 받아야 하는 경우에는 개발자가 직접 비율 정보를 확보해야 한다.

```tsx
type CmsImage = {
  url: string;
  alt: string;
  width: number;
  height: number;
};

export function ArticleCover({ image }: { image: CmsImage }) {
  return (
    <Image
      src={image.url}
      alt={image.alt}
      width={image.width}
      height={image.height}
      sizes="(max-width: 768px) 100vw, 768px"
    />
  );
}
```

CMS에서 URL만 저장하고 width/height를 저장하지 않으면 프론트엔드가 매번 원본을 열어 크기를 추론하거나, 임의 비율을 가정하게 된다. 운영 기준으로는 CMS 이미지 모델에 원본 크기와 대체 텍스트를 함께 저장하는 편이 낫다.

---

## 핵심개념 3: `fill`을 쓰면 `sizes`는 사실상 필수다

`fill`은 카드, 배너, 그리드처럼 부모 컨테이너를 이미지가 꽉 채워야 할 때 편하다.

```tsx
<div className="relative aspect-[4/3] overflow-hidden rounded-md">
  <Image
    src={product.thumbnailUrl}
    alt={product.name}
    fill
    className="object-cover"
  />
</div>
```

하지만 여기에는 중요한 함정이 있다. `fill`은 이미지가 부모 요소를 채운다는 뜻이지, 브라우저가 그 부모 요소의 실제 표시 폭을 자동으로 정확히 안다는 뜻이 아니다. `sizes`를 주지 않으면 브라우저는 보수적으로 큰 이미지를 선택할 수 있다. 특히 카드 그리드에서 이 문제가 자주 터진다.

예를 들어 데스크톱에서는 4열 카드라서 실제 이미지 슬롯이 280px 정도인데, `sizes`가 없으면 훨씬 큰 후보가 내려갈 수 있다.

```tsx
<Image
  src={product.thumbnailUrl}
  alt={product.name}
  fill
  sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 25vw"
  className="object-cover"
/>
```

이 `sizes`는 브라우저에게 다음 의도를 알려 준다.

- 모바일에서는 카드가 한 줄 전체라서 viewport 폭 전체에 가깝다.
- 태블릿에서는 2열이라 대략 viewport 절반이다.
- 데스크톱에서는 4열이라 대략 viewport 1/4이다.

정확히 CSS grid와 1px까지 맞아야 하는 것은 아니다. 중요한 것은 브라우저가 "이 이미지는 대충 어느 슬롯 크기인가"를 알 수 있어야 한다는 점이다. 이미지가 화면의 25%만 차지하는데 100vw로 판단되면 데이터 낭비, 디코딩 비용, LCP 경쟁이 모두 생긴다.

---

## 핵심개념 4: LCP 이미지는 lazy image가 아니다

Next.js Image는 기본적으로 lazy loading을 활용한다. 이는 목록 하단이나 본문 중간 이미지에는 좋은 기본값이다. 하지만 첫 화면의 핵심 이미지, 특히 LCP 후보 이미지는 다르게 다뤄야 한다.

LCP 후보는 보통 아래 중 하나다.

- 메인 랜딩의 hero 이미지
- 상품 상세의 대표 이미지
- 블로그 글 상단 커버 이미지
- 카드형 홈 화면에서 가장 큰 첫 번째 콘텐츠 이미지

이 이미지는 브라우저가 늦게 발견하면 페이지 체감 속도가 크게 흔들린다. 따라서 LCP 후보라면 lazy loading 기본값에 맡기지 말고 명시적으로 우선순위를 줘야 한다.

```tsx
<Image
  src={heroImage}
  alt="근태 승인 현황을 보여주는 인사 시스템 대시보드"
  width={1440}
  height={900}
  sizes="100vw"
  preload
/>
```

운영 기준은 간단하다.

- 한 페이지에서 진짜 LCP 후보는 보통 하나만 고른다.
- 첫 화면에 보일 수도 있고 아닐 수도 있는 이미지 여러 개에 모두 preload를 주지 않는다.
- `loading`, `fetchPriority`, `preload`를 섞어 충돌하는 의도를 만들지 않는다.
- 모바일과 데스크톱에서 LCP 후보가 다르면 실제 측정 데이터를 보고 결정한다.

특히 carousel 첫 화면에 여러 이미지를 넣고 모두 preload하는 패턴은 피해야 한다. 사용자는 한 장만 보는데 네트워크는 여러 장을 동시에 당겨 온다. 그 결과 CSS, JS, font, API 요청과 경쟁해 오히려 LCP가 악화될 수 있다.

---

## 핵심개념 5: `remotePatterns`는 성능 설정이 아니라 보안 경계다

원격 이미지를 쓰려면 `next.config.js`에서 허용 출처를 설정해야 한다. 과거에는 `domains`를 많이 썼지만, 운영 기준으로는 프로토콜, 호스트, 경로, 필요하면 쿼리까지 제한할 수 있는 `remotePatterns`를 사용하는 편이 안전하다.

```js
/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "cdn.example.com",
        pathname: "/hr-assets/**",
      },
      {
        protocol: "https",
        hostname: "images.example-cms.com",
        pathname: "/uploads/**",
      },
    ],
  },
};

module.exports = nextConfig;
```

이 설정은 단순히 "이미지가 보이게 하는 옵션"이 아니다. Next.js Image Optimization API가 서버에서 원격 이미지를 가져와 변환한다는 점을 생각해야 한다. 허용 범위를 너무 넓게 잡으면 다음 문제가 생긴다.

- 공격자가 큰 원본 이미지를 반복 요청해 최적화 비용을 유발할 수 있다.
- 의도하지 않은 외부 이미지가 서비스 도메인의 최적화 API를 통해 제공될 수 있다.
- 공유 CDN 호스트에서 다른 테넌트 파일까지 최적화 대상이 될 수 있다.
- redirect를 따라가며 예상하지 못한 위치의 이미지를 가져올 수 있다.
- private network 접근 허용 같은 설정과 결합되면 SSRF 성격의 리스크가 생길 수 있다.

그래서 `remotePatterns`는 아래처럼 좁게 잡는 것이 좋다.

- 가능하면 `https`만 허용한다.
- 공용 이미지 호스트 전체보다 서비스 전용 CDN host를 쓴다.
- pathname prefix를 서비스 전용 경로로 제한한다.
- 쿼리 문자열을 서명 URL 정책과 함께 검토한다.
- redirect 허용 횟수를 줄일 수 있으면 줄인다.
- SVG는 기본적으로 `unoptimized` 또는 별도 정책으로 다룬다.

운영에서 "CMS가 나중에 바뀔 수도 있으니 일단 `**`로 열어 두자"는 선택은 나중에 비용과 보안 검토로 돌아온다. 이미지 출처는 초기에 좁혀 두는 편이 훨씬 싸다.

---

## 실무예시: HR SaaS의 아바타, 조직도, 게시글 커버 이미지를 나눠 설계하기

인사 시스템을 만든다고 가정해 보자. 이미지 유형은 대략 세 가지다.

- 직원 아바타: 작고 반복적으로 많이 보인다.
- 조직도 또는 대시보드 썸네일: 카드 그리드에 표시된다.
- 공지사항 또는 블로그 커버: 첫 화면 LCP 후보가 될 수 있다.

세 이미지를 하나의 공통 `AppImage`로 뭉개면 API는 편해 보이지만 운영 의도가 흐려진다. 오히려 이미지 유형별 컴포넌트를 나누는 편이 좋다.

```tsx
import Image from "next/image";

type AvatarImageProps = {
  src: string;
  name: string;
  size?: 32 | 40 | 64 | 96;
};

export function AvatarImage({ src, name, size = 40 }: AvatarImageProps) {
  return (
    <Image
      src={src}
      alt={`${name} 프로필 사진`}
      width={size}
      height={size}
      sizes={`${size}px`}
      className="rounded-full object-cover"
    />
  );
}
```

아바타는 보통 정사각형이고 표시 크기가 작다. `sizes`도 고정 px로 줄 수 있다. 수백 명이 나오는 조직원 목록에서 아바타 하나하나가 큰 후보를 고르면 낭비가 크므로 작은 슬롯임을 명확히 표현한다.

```tsx
type CardImageProps = {
  src: string;
  alt: string;
};

export function CardImage({ src, alt }: CardImageProps) {
  return (
    <div className="relative aspect-[16/10] overflow-hidden rounded-md bg-slate-100">
      <Image
        src={src}
        alt={alt}
        fill
        sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
        className="object-cover"
      />
    </div>
  );
}
```

카드 이미지는 `fill`을 쓰되 부모에 `position: relative`와 안정적인 `aspect-ratio`를 준다. 이렇게 해야 이미지 로딩 전후로 카드 높이가 흔들리지 않는다. `sizes`는 실제 grid 열 수와 맞춘다.

```tsx
type CoverImageProps = {
  src: string;
  alt: string;
  width: number;
  height: number;
  aboveTheFold?: boolean;
};

export function CoverImage({
  src,
  alt,
  width,
  height,
  aboveTheFold = false,
}: CoverImageProps) {
  return (
    <Image
      src={src}
      alt={alt}
      width={width}
      height={height}
      sizes="(max-width: 768px) 100vw, 768px"
      preload={aboveTheFold}
      className="h-auto w-full rounded-md object-cover"
    />
  );
}
```

커버 이미지는 본문 폭이 보통 제한되어 있다. 따라서 데스크톱에서 `100vw`가 아니라 실제 콘텐츠 폭에 맞춘다. 글 상세 상단처럼 첫 화면 LCP 후보라면 `aboveTheFold`를 통해 preload 의도를 명시하고, 본문 중간 삽입 이미지라면 preload하지 않는다.

설정도 이미지 유형에 맞춰 정리한다.

```js
const nextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "assets.vibe-hr.example",
        pathname: "/public/**",
      },
      {
        protocol: "https",
        hostname: "cms.vibe-hr.example",
        pathname: "/uploads/**",
      },
    ],
    formats: ["image/webp"],
    qualities: [50, 75],
    minimumCacheTTL: 60 * 60 * 24,
    maximumRedirects: 0,
    maximumResponseBody: 10_000_000,
  },
};

module.exports = nextConfig;
```

위 설정은 예시일 뿐이다. 핵심은 "어떤 이미지를 어디서 가져올 수 있는가", "어떤 품질 값만 허용할 것인가", "원본 크기는 어디까지 허용할 것인가", "redirect를 따라갈 것인가"를 코드로 남기는 데 있다.

---

## CDN과 캐시: 이미지가 빠른지보다 "언제 바뀌는지"를 먼저 결정해야 한다

이미지 캐시에서 가장 위험한 질문은 "TTL을 길게 할까 짧게 할까"가 아니다. 먼저 물어야 할 것은 이거다.

> 이 이미지 URL은 내용이 바뀌면 같이 바뀌는가?

파일명 또는 경로에 해시가 들어가고 내용이 바뀔 때 URL도 바뀐다면 장기 캐시가 유리하다.

```txt
/uploads/posts/cover.8f3a21c9.webp
```

반대로 같은 URL의 내용이 덮어쓰기 되는 구조라면 긴 TTL은 사고를 만든다.

```txt
/uploads/posts/latest-cover.webp
```

Next.js 최적화 캐시는 원본 응답의 캐시 헤더와 `minimumCacheTTL`의 영향을 받는다. 하지만 "지금 당장 이 최적화 결과만 무효화"하는 간단한 버튼이 있다고 기대하면 안 된다. 원본이 바뀌었는데 URL이 그대로라면 캐시된 최적화 결과가 남을 수 있다.

따라서 운영 기준은 아래처럼 잡는 편이 좋다.

- 사용자가 업로드한 이미지는 가능하면 content hash 또는 version query를 붙인다.
- CMS에서 이미지를 교체하면 URL도 바뀌게 만든다.
- 자주 바뀌는 이미지에는 매우 긴 `minimumCacheTTL`을 주지 않는다.
- 로컬 정적 import 이미지는 불변 캐시 전략에 태운다.
- CDN 앞단은 `Accept` 헤더를 origin으로 전달해 포맷 협상이 유지되게 한다.
- 캐시 키에 width, quality, format, URL이 어떻게 반영되는지 관측한다.

CDN을 붙였는데도 이미지가 느리다면 두 가지를 먼저 확인해야 한다.

1. CDN이 `/_next/image` 응답을 캐시하고 있는가
2. CDN이 브라우저의 `Accept` 헤더를 origin으로 전달하는가

두 번째가 빠지면 AVIF/WebP 같은 포맷 협상이 엉킬 수 있다. 브라우저별로 다른 최적화 결과를 제공하려면 CDN cache key와 vary 정책도 그에 맞아야 한다.

---

## 트레이드오프 1: AVIF는 항상 정답이 아니다

AVIF는 WebP보다 더 작아질 수 있지만 인코딩 비용과 최초 요청 지연이 더 클 수 있다. 이미지가 한 번 최적화된 뒤 오래 캐시되는 서비스라면 AVIF의 이점이 크다. 반대로 원본이 계속 바뀌고, 요청마다 새로운 이미지가 최적화되는 서비스라면 최초 변환 비용이 사용자 지연으로 나타날 수 있다.

운영 판단은 이렇게 나눈다.

- 마케팅 랜딩, 문서 사이트, 상품 이미지처럼 반복 조회가 많고 오래 캐시되는 이미지는 AVIF 후보가 될 수 있다.
- 관리자 화면의 임시 첨부 이미지, 미리보기 이미지처럼 조회가 적고 변경이 잦은 이미지는 WebP 중심이 단순하다.
- self-host 환경에서 CPU가 빠듯하다면 포맷 수를 늘리기 전에 변환 비용을 측정해야 한다.
- AVIF와 WebP를 모두 켜면 포맷별 캐시 저장량도 늘어난다.

가벼운 결론은 "대부분의 일반 운영에서는 WebP부터 안정화하고, 반복 조회가 많은 이미지군에만 AVIF를 실험한다" 정도가 현실적이다.

---

## 트레이드오프 2: quality를 높이면 선명해지지만 캐시 조합도 늘어난다

`quality={100}`을 습관적으로 넣는 팀이 있다. 하지만 웹 이미지에서 100은 대개 비용 대비 이득이 낮다. 특히 카드 썸네일, 아바타, 목록 이미지는 75 전후로도 충분한 경우가 많다.

품질 값은 자유롭게 열어 두기보다 허용 목록으로 제한하는 편이 좋다.

```js
const nextConfig = {
  images: {
    qualities: [50, 75],
  },
};
```

이렇게 하면 컴포넌트에서는 의도가 분명해진다.

```tsx
<Image
  src={employee.avatarUrl}
  alt={`${employee.name} 프로필`}
  width={64}
  height={64}
  sizes="64px"
  quality={50}
/>
```

- 아바타와 작은 썸네일: 50 또는 60대도 검토 가능
- 본문 이미지와 카드 커버: 75 근처가 보통 무난
- 제품 확대 이미지, 포트폴리오 이미지: 별도 컴포넌트와 측정 기준 필요

품질은 감성값처럼 보이지만 실제로는 캐시 key와 스토리지, 변환 비용, 네트워크 비용에 영향을 준다.

---

## 트레이드오프 3: 커스텀 loader는 자유도를 주지만 Next.js의 기본 운영 모델을 우회한다

이미 Cloudinary, Imgix, Akamai Image Manager 같은 전용 이미지 CDN을 쓰고 있다면 커스텀 loader가 맞을 수 있다. 이 경우 Next.js 서버가 직접 이미지를 최적화하지 않고 외부 이미지 서비스 URL을 생성한다.

```tsx
const cdnLoader = ({
  src,
  width,
  quality,
}: {
  src: string;
  width: number;
  quality?: number;
}) => {
  return `https://img.example.com/${src}?w=${width}&q=${quality ?? 75}&fm=webp`;
};

<Image
  loader={cdnLoader}
  src="uploads/cover.jpg"
  alt="서비스 소개 커버"
  width={1200}
  height={675}
  sizes="(max-width: 768px) 100vw, 960px"
/>;
```

하지만 커스텀 loader는 만능이 아니다.

- 외부 이미지 서비스의 URL 서명 정책을 직접 관리해야 한다.
- 변환 파라미터가 공격자에게 열리지 않도록 제한해야 한다.
- Next.js 설정의 일부 보안 경계와 캐시 정책이 달라질 수 있다.
- 로컬 개발, preview, production에서 이미지 URL 생성 규칙이 갈라질 수 있다.

전용 이미지 CDN이 없다면 기본 loader로 시작하고, 병목이 명확해진 뒤 커스텀 loader를 검토해도 늦지 않다. 반대로 이미 이미지 CDN을 표준으로 쓰는 조직이라면 Next.js 기본 최적화와 이중 최적화되지 않게 한쪽 책임을 분명히 해야 한다.

---

## 흔한 실수 1: `fill`만 쓰고 부모 크기를 안정화하지 않는다

`fill` 이미지는 부모 요소를 기준으로 배치된다. 부모가 `position: relative`가 아니거나, 높이가 콘텐츠 로딩 뒤에야 정해지면 이미지가 보이지 않거나 layout shift가 생긴다.

나쁜 예:

```tsx
<div className="overflow-hidden">
  <Image src={src} alt={alt} fill />
</div>
```

좋은 예:

```tsx
<div className="relative aspect-[16/9] overflow-hidden">
  <Image
    src={src}
    alt={alt}
    fill
    sizes="(max-width: 768px) 100vw, 50vw"
    className="object-cover"
  />
</div>
```

이미지 로딩 전에도 레이아웃 슬롯이 확보되어야 CLS가 줄어든다.

---

## 흔한 실수 2: `alt`를 파일명처럼 쓴다

`alt="image"`나 `alt="thumbnail"`은 접근성에도, 검색에도, 유지보수에도 거의 도움이 되지 않는다. alt는 이미지가 전달하는 정보를 텍스트로 대체해야 한다.

```tsx
<Image
  src={dashboardScreenshot}
  alt="부서별 근태 이상 징후를 카드와 차트로 보여주는 대시보드"
/>
```

단순 장식 이미지라면 빈 alt가 맞을 수 있다.

```tsx
<Image src={pattern} alt="" aria-hidden="true" />
```

다만 중요한 정보를 담은 화면 캡처, 상품 이미지, 사용자 프로필에는 의미 있는 alt를 넣어야 한다.

---

## 흔한 실수 3: 원격 이미지 URL을 사용자 입력 그대로 통과시킨다

사용자가 프로필 이미지 URL을 직접 입력할 수 있는 기능이 있다고 하자. 이 값을 그대로 `src`에 넣고 remotePatterns를 넓게 열면 서버가 외부 URL을 가져오는 구조가 된다. 운영 기준으로는 아래 중 하나가 낫다.

- 사용자가 이미지를 업로드하면 우리 스토리지로 복사한다.
- 외부 URL 입력을 허용하더라도 백엔드에서 도메인 allowlist와 파일 크기를 검증한다.
- 이미지 프록시 또는 백엔드 수집 작업에서 MIME, 크기, 확장자, redirect를 검증한다.
- 프론트엔드는 검증된 asset ID 또는 검증된 CDN URL만 받는다.

이미지는 단순 정적 파일처럼 보이지만, 원격 최적화 경로에서는 서버 측 fetch가 발생한다. 이 사실을 잊으면 보안 경계가 흐려진다.

---

## 흔한 실수 4: SVG를 일반 래스터 이미지처럼 다룬다

SVG는 벡터라서 최적화 관점에서도 다르고, 보안 관점에서도 다르다. 신뢰할 수 없는 SVG를 그대로 inline 또는 image optimization 경로에 태우는 것은 검토가 필요하다. SVG에는 스크립트, 외부 참조, 이벤트 속성 등 보안상 민감한 요소가 얽힐 수 있다.

운영 기준은 아래처럼 잡는다.

- 아이콘은 가능하면 코드로 관리하는 검증된 아이콘 라이브러리나 정적 asset을 쓴다.
- 사용자가 업로드한 SVG는 기본적으로 허용하지 않는다.
- 반드시 허용해야 한다면 sanitize, CSP, content disposition 정책을 별도로 둔다.
- `dangerouslyAllowSVG`는 이름 그대로 위험을 이해한 뒤 제한적으로 사용한다.
- SVG는 크기 변환 이득이 작으므로 `unoptimized`가 더 자연스러운 경우가 많다.

---

## 흔한 실수 5: 측정 없이 "이미지를 최적화했다"고 말한다

이미지 최적화는 Lighthouse 점수 하나로 끝내기 어렵다. 최소한 아래 지표를 같이 봐야 한다.

- LCP element가 어떤 이미지인지
- LCP 이미지의 request start와 response end
- 실제 내려간 이미지 width, encoded size, decoded size
- CDN cache hit ratio
- `/_next/image` 요청 수와 p95 latency
- 이미지 최적화 서버의 CPU, 메모리, disk cache 사용량
- 모바일 네트워크에서 hero 이미지와 JS chunk의 경쟁 여부

특히 `sizes` 문제는 네트워크 패널을 보면 바로 드러난다. 카드 슬롯은 300px인데 1200px 후보가 내려가고 있다면 CSS보다 `sizes`를 먼저 의심해야 한다.

---

## 운영 체크리스트

이미지 기능을 배포하기 전에는 아래 항목을 확인한다.

- 로컬 정적 이미지는 가능한 경우 static import를 사용한다.
- 원격 CMS 이미지는 width, height, alt를 데이터 모델에 포함한다.
- `fill` 이미지에는 안정적인 부모 크기와 `sizes`를 함께 둔다.
- 카드, 아바타, 커버처럼 이미지 유형별 컴포넌트를 나눈다.
- LCP 후보 이미지는 페이지당 하나를 정하고 preload 여부를 명시한다.
- 스크롤 아래 이미지는 불필요하게 preload하지 않는다.
- `remotePatterns`는 protocol, hostname, pathname까지 좁게 제한한다.
- 공유 CDN 전체나 사용자 입력 URL 전체를 열지 않는다.
- redirect 허용, local IP 접근, SVG 허용 정책을 보안 검토한다.
- CDN이 `Accept` 헤더를 origin으로 전달하는지 확인한다.
- 이미지 URL이 내용 변경 시 함께 바뀌는지 확인한다.
- 자주 바뀌는 이미지는 긴 `minimumCacheTTL`을 피한다.
- quality 값은 허용 목록으로 제한하고 이미지 유형별 기본값을 둔다.
- `/_next/image` 요청 수, 캐시 적중률, p95 latency를 모니터링한다.
- 모바일 실제 기기에서 LCP element와 다운로드 크기를 확인한다.

---

## 마무리: 좋은 이미지 최적화는 "작게 만들기"보다 "의도를 정확히 전달하기"에 가깝다

Next.js의 `Image` 컴포넌트는 많은 일을 대신 해준다. 하지만 운영 서비스에서 중요한 결정까지 자동으로 대신해 주지는 않는다. 어떤 이미지가 첫 화면 핵심인지, 어떤 이미지는 작은 슬롯인지, 어떤 원격 출처를 신뢰할지, 캐시를 얼마나 오래 가져갈지, SVG와 redirect를 어떻게 제한할지는 서비스 설계의 영역이다.

좋은 기준은 단순하다.

- 레이아웃 슬롯은 `width/height`, `fill`, `sizes`로 명확히 표현한다.
- 출처는 `remotePatterns`로 좁게 제한한다.
- LCP 이미지는 lazy image와 다르게 취급한다.
- 캐시는 URL 변경 정책과 함께 설계한다.
- 최적화 결과는 네트워크 패널과 운영 지표로 검증한다.

한 줄로 정리하면 이렇다.

> **Next.js 이미지 최적화는 `Image`를 쓰는 순간 끝나는 기능이 아니라, 레이아웃·출처·LCP·캐시·보안 경계를 코드로 고정하고 측정으로 검증하는 운영 설계다.**
