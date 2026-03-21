---
layout: post
title: "Next.js 이미지 최적화 실전: LCP 개선과 next/image 제대로 쓰기"
date: 2026-03-13 10:04:59 +0900
categories: [nextjs]
tags: [study, nextjs, image, lcp, performance, frontend]
---

## 왜 이미지 최적화가 중요한가?

실제 서비스에서 느린 첫 화면의 가장 큰 원인 중 하나는 이미지입니다. 특히 랜딩 페이지나 쇼핑몰처럼 히어로 이미지가 큰 서비스에서는 이미지 전략이 곧 사용자 체감 속도입니다.

Next.js는 `next/image`를 통해 이미지 최적화를 기본 제공하지만, 설정을 잘못하면 오히려 레이아웃 깨짐이나 과도한 다운로드가 발생할 수 있습니다.

## 기본 사용법

```tsx
import Image from 'next/image';

export default function Hero() {
  return (
    <section>
      <Image
        src="/hero.jpg"
        alt="서비스 소개 이미지"
        width={1200}
        height={630}
        priority
      />
    </section>
  );
}
```

## 중요한 옵션

- **priority**
  첫 화면(LCP) 이미지라면 사용
- **sizes**
  반응형 이미지 다운로드 최적화에 중요
- **fill**
  부모 컨테이너를 채우는 레이아웃에 사용

## 반응형 예시

```tsx
<Image
  src="/product.jpg"
  alt="상품 이미지"
  fill
  sizes="(max-width: 768px) 100vw, 50vw"
  style={{ objectFit: 'cover' }}
/>
```

## 외부 이미지 허용

`next.config.ts`
```ts
import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'images.example.com'
      }
    ]
  }
};

export default nextConfig;
```

## 흔한 실수

- 첫 화면 이미지인데 `priority` 누락
- `sizes` 없이 반응형 이미지를 사용
- 그냥 `<img>`로 대체해서 최적화 이점 포기
- 외부 도메인 설정 없이 원격 이미지 로드 시도

## 한 줄 정리

Next.js 이미지 최적화의 핵심은 "보여주기"가 아니라, **첫 화면 체감 속도와 다운로드 비용을 동시에 관리하는 것**입니다.
