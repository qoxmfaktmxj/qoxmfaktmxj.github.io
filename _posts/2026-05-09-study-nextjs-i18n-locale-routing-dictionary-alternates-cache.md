---
layout: post
title: "Next.js 국제화 실전: Locale Routing, Dictionary Loading, alternates, Cache Partitioning으로 다국어 서비스를 운영하는 법"
date: 2026-05-09 11:40:00 +0900
categories: [nextjs]
tags: [study, nextjs, i18n, internationalization, locale-routing, proxy, dictionary-loading, metadata, caching, server-actions]
permalink: /nextjs/2026/05/09/study-nextjs-i18n-locale-routing-dictionary-alternates-cache.html
---

## 배경: Next.js에서 국제화는 번역 파일 몇 개의 문제가 아니라 URL·캐시·SEO·운영 정책을 함께 묶는 설계다

다국어 요구사항은 초반에는 단순해 보인다.

- `/ko`, `/en`, `/ja` 정도의 locale prefix를 붙인다
- 화면 문구는 JSON dictionary로 바꾼다
- 헤더에서 언어 전환 버튼만 하나 만든다
- 브라우저 `Accept-Language`를 보고 첫 진입 언어를 정한다

여기까지는 대부분 금방 된다. 문제는 서비스가 조금만 커져도 그다음부터다.

- 같은 상품이 locale마다 다른 slug를 가져 URL 전략이 꼬인다
- `Accept-Language`와 사용자가 직접 선택한 언어 쿠키 우선순위가 충돌한다
- `generateMetadata`는 한 언어 기준인데 실제 본문은 다른 언어가 나가 canonical과 `hreflang`이 어긋난다
- `/en/products`는 최신인데 `/ko/products`는 오래된 캐시가 남는다
- Server Action에서 locale을 잃어버려 저장 후 엉뚱한 경로로 redirect된다
- 문서 본문은 번역됐는데 에러 메시지, form validation, 이메일 템플릿은 기본 언어로 섞인다
- 정적 생성으로 시작했는데 locale 수가 늘면서 빌드 시간이 급격히 커진다
- locale별 사전 파일을 클라이언트에 무심코 실어 번들 크기가 커진다

즉 국제화는 단순히 "문자열 번역"이 아니다. 실무에서는 아래 질문에 답해야 한다.

1. **언어 선택의 기준은 무엇인가** — 브라우저, 쿠키, 계정 설정, 도메인 중 무엇이 우선인가
2. **URL 정책은 무엇인가** — sub-path, domain, localized slug 중 어디까지 허용할 것인가
3. **데이터와 캐시는 어떻게 분리할 것인가** — locale마다 같은 데이터인가, 번역된 별도 데이터인가
4. **SEO는 어떻게 맞출 것인가** — canonical, `alternates.languages`, sitemap, 중복 페이지 정책을 어떻게 설계할 것인가
5. **쓰기 흐름은 어떻게 유지할 것인가** — Server Action, redirect, validation, flash message가 locale을 잃지 않게 할 것인가

이 글의 목표는 하나다.

> **Next.js 국제화를 라우팅 문법이 아니라, locale 결정 → 콘텐츠 로딩 → 캐시 분리 → SEO 정합성 → 쓰기 흐름 유지까지 이어지는 운영 설계로 이해하는 것**

중급 이상 개발자를 기준으로, 배경, 핵심 개념, 실무 예시, 트레이드오프, 흔한 실수, 체크리스트, 한 줄 정리까지 한 번에 정리한다.

---

## 먼저 큰 그림: 다국어 서비스는 "번역"보다 먼저 "locale contract"를 정해야 한다

국제화가 자주 실패하는 이유는 팀이 각자 다른 locale 기준을 암묵적으로 쓰기 때문이다.

- Proxy는 `Accept-Language`를 본다
- 프론트 헤더는 `locale` 쿠키를 본다
- API는 사용자 프로필의 `preferredLanguage`를 본다
- SEO는 `/en/...` 경로를 대표 URL로 본다
- 메일 발송은 시스템 기본값 `ko`를 쓴다

이 상태에서는 한 기능씩 보면 맞아 보이지만, 전체 서비스는 일관성을 잃는다.

그래서 먼저 고정해야 할 것은 문구 파일이 아니라 **locale contract**다. 보통 아래 순서가 가장 운영하기 쉽다.

1. 사용자가 명시적으로 선택한 locale 쿠키
2. 로그인 사용자 프로필의 locale 설정
3. 브라우저 `Accept-Language`
4. 시스템 기본 locale

이 우선순위가 정해져야 다음이 모두 맞는다.

- 첫 진입 redirect
- 언어 전환 버튼 동작
- 로그인 후 복귀 경로
- 메타데이터 언어 대체 링크
- 서버 액션 후 redirect 위치
- 캐시 키 분리

실무에서 중요한 포인트는 단순하다.

> **locale은 문자열이 아니라, URL·콘텐츠·캐시·SEO·쓰기 흐름이 함께 따라가는 요청 문맥이다.**

이렇게 보면 Next.js 국제화 설계도 훨씬 명확해진다.

---

## 핵심 개념 1: 라우팅 전략은 sub-path를 기본값으로 두고, domain은 분명한 운영 이유가 있을 때만 확장하는 편이 안전하다

Next.js에서 다국어 라우팅은 보통 두 방식으로 간다.

### 1) Sub-path

- `/ko/products`
- `/en/products`
- `/ja/products`

### 2) Domain

- `example.kr/products`
- `example.com/products`
- `example.co.jp/products`

초기에는 domain 전략이 더 글로벌 서비스답게 보일 수 있다. 하지만 대부분의 제품팀에게 기본값은 sub-path가 더 안전하다.

### sub-path가 기본값으로 좋은 이유

- 앱 구조가 단순하다
- 단일 배포 파이프라인으로 운영하기 쉽다
- canonical, alternates, sitemap 관리가 직관적이다
- 공통 레이아웃, 공통 컴포넌트, 공통 캐시 정책을 재사용하기 쉽다
- 분석, 모니터링, QA가 한 도메인 안에서 모인다

### domain이 필요한 경우

- 국가별 법적/상업적 요구사항이 다르다
- 콘텐츠뿐 아니라 가격, 재고, 결제 수단, 정책 문서가 국가별로 실질적으로 분리된다
- 마케팅 팀이 국가별 검색/브랜드 전략을 강하게 분리한다
- CDN, edge routing, cookie scope를 국가별로 아예 나누는 편이 더 유리하다

대부분의 SaaS, 문서 사이트, 블로그, 백오피스는 domain까지 가지 않아도 충분하다. 특히 locale별 콘텐츠 차이는 있지만 제품 데이터와 인증 경계는 동일한 경우라면 sub-path가 훨씬 유지보수하기 쉽다.

### 추천 폴더 구조

```tsx
app/
  [lang]/
    layout.tsx
    page.tsx
    products/
      page.tsx
      [slug]/
        page.tsx
```

공식 가이드처럼 `app/[lang]` 아래에 특수 파일을 넣어 모든 layout/page가 `lang` 문맥을 자연스럽게 받게 만드는 편이 좋다.

```tsx
// app/[lang]/layout.tsx
export async function generateStaticParams() {
  return [{ lang: 'ko' }, { lang: 'en' }, { lang: 'ja' }]
}

export default async function LocaleLayout({
  children,
  params,
}: LayoutProps<'/[lang]'>) {
  const { lang } = await params

  return (
    <html lang={lang}>
      <body>{children}</body>
    </html>
  )
}
```

이 구조의 핵심은 단순한 path parameter 전달이 아니다. `lang`을 라우트 트리의 최상단 문맥으로 고정해 **metadata, dictionary, cache tag, redirect 경로**가 모두 같은 locale을 기준으로 움직이게 만드는 데 있다.

---

## 핵심 개념 2: Proxy는 첫 진입 locale 협상용으로 쓰되, 최종 locale 진실의 원천은 애플리케이션 쪽에 남겨야 한다

Next.js 16 기준으로 `middleware.ts`는 `proxy.ts`로 이름이 바뀌었다. 하지만 여기서 더 중요한 것은 이름보다 책임이다.

Proxy는 다음에 잘 맞는다.

- locale prefix가 없는 첫 진입 요청 redirect
- 국가/언어 기본 landing 분기
- locale 쿠키 설정 또는 보정
- 오래된 locale 경로 rewrite

반대로 Proxy가 최종 locale truth source가 되면 금방 꼬인다.

- 로그인 사용자의 저장 locale과 브라우저 header가 다를 수 있다
- 사용자가 헤더에서 언어를 바꾼 뒤에는 `Accept-Language`보다 쿠키가 우선이어야 한다
- 제품 내부 deep link는 locale prefix가 이미 있는 상태로 들어온다
- Server Action POST는 원래 페이지 경로를 유지하면서 locale 문맥을 이어받아야 한다

### 최소 책임의 Proxy 예시

```ts
// proxy.ts
import { NextRequest, NextResponse } from 'next/server'
import { match } from '@formatjs/intl-localematcher'
import Negotiator from 'negotiator'

const SUPPORTED = ['ko', 'en', 'ja'] as const
const DEFAULT_LOCALE = 'ko'

function getLocale(request: NextRequest) {
  const cookieLocale = request.cookies.get('locale')?.value
  if (cookieLocale && SUPPORTED.includes(cookieLocale as (typeof SUPPORTED)[number])) {
    return cookieLocale
  }

  const headers = { 'accept-language': request.headers.get('accept-language') ?? '' }
  const languages = new Negotiator({ headers }).languages()
  return match(languages, SUPPORTED, DEFAULT_LOCALE)
}

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl

  const hasLocale = SUPPORTED.some(
    (locale) => pathname === `/${locale}` || pathname.startsWith(`/${locale}/`)
  )

  if (hasLocale || pathname.startsWith('/_next') || pathname.includes('.')) {
    return NextResponse.next()
  }

  const locale = getLocale(request)
  const url = request.nextUrl.clone()
  url.pathname = `/${locale}${pathname}`

  return NextResponse.redirect(url)
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)'],
}
```

여기서 중요한 점은 세 가지다.

1. **Proxy는 prefix 없는 요청만 정리한다**  
   이미 `/ko/...`로 들어온 경로를 다시 해석하려고 들지 않는다.

2. **쿠키 우선순위를 브라우저 header보다 앞에 둔다**  
   사용자가 직접 바꾼 언어는 브라우저 기본 설정보다 존중하는 편이 UX가 맞다.

3. **앱 내부의 최종 locale 유효성 검사는 여전히 page/layout에서 한다**  
   Proxy가 있다고 해서 `params.lang`을 무조건 신뢰하지 않는다.

즉 Proxy는 locale 협상 입구이고, 애플리케이션은 locale 사용 주체다. 이 구분이 있어야 디버깅이 쉬워진다.

---

## 핵심 개념 3: Dictionary Loading은 서버 우선으로 두고, Client Component에는 필요한 조각만 내려야 번들과 결합도가 동시에 줄어든다

국제화 구현이 번들 비대화로 이어지는 가장 흔한 이유는 dictionary 전체를 클라이언트에서 다루기 시작할 때다.

예를 들면 이런 흐름이다.

- `messages.ko.json`, `messages.en.json`를 전부 import 한다
- 전역 i18n provider에 큰 객체를 실어 보낸다
- Client Component 여러 곳이 전체 메시지 객체를 구독한다
- locale 추가 때마다 초기 JS 번들이 같이 커진다

App Router 기본값은 Server Component다. 그래서 dictionary도 서버 우선으로 가져가는 편이 좋다.

```ts
// app/[lang]/dictionaries.ts
import 'server-only'

const dictionaries = {
  ko: () => import('./dictionaries/ko.json').then((m) => m.default),
  en: () => import('./dictionaries/en.json').then((m) => m.default),
  ja: () => import('./dictionaries/ja.json').then((m) => m.default),
}

export type Locale = keyof typeof dictionaries

export function hasLocale(locale: string): locale is Locale {
  return locale in dictionaries
}

export async function getDictionary(locale: Locale) {
  return dictionaries[locale]()
}
```

```tsx
// app/[lang]/page.tsx
import { notFound } from 'next/navigation'
import { getDictionary, hasLocale } from './dictionaries'

export default async function HomePage({ params }: PageProps<'/[lang]'>) {
  const { lang } = await params

  if (!hasLocale(lang)) notFound()

  const dict = await getDictionary(lang)

  return <h1>{dict.home.heroTitle}</h1>
}
```

### 왜 이 구조가 좋은가

- locale별 사전 파일이 서버에서만 로드된다
- 사용하지 않는 언어의 메시지가 클라이언트 번들에 섞이지 않는다
- `hasLocale()`로 잘못된 locale을 404 처리해 런타임 에러를 줄일 수 있다
- page/layout 수준에서 필요한 dictionary만 가져와 문맥이 분명해진다

### 실무 팁: dictionary를 도메인 단위로 자르는 편이 낫다

초반에는 파일 하나로 시작해도 되지만, 서비스가 커지면 아래처럼 쪼개는 편이 좋다.

- `common`
- `auth`
- `dashboard`
- `products`
- `validation`

왜냐하면 locale 분리보다 더 빨리 커지는 것은 **메시지 도메인의 결합도**이기 때문이다. `messages.ko.json` 하나에 모든 문구를 몰아두면 충돌, 중복 키, 리뷰 난이도가 급격히 올라간다.

추천 방식은 이렇다.

```ts
const dictionaries = {
  ko: {
    common: () => import('./dictionaries/ko/common.json').then((m) => m.default),
    products: () => import('./dictionaries/ko/products.json').then((m) => m.default),
  },
  en: {
    common: () => import('./dictionaries/en/common.json').then((m) => m.default),
    products: () => import('./dictionaries/en/products.json').then((m) => m.default),
  },
}
```

필요한 route segment에서 필요한 namespace만 조립하면 locale 추가와 메시지 유지보수가 훨씬 수월해진다.

---

## 핵심 개념 4: metadata와 `alternates.languages`를 locale 라우팅과 같은 규칙으로 묶지 않으면 SEO가 조용히 망가진다

다국어 페이지에서 자주 놓치는 문제가 있다.

- 본문은 `/en/docs/cache`인데 canonical이 `/docs/cache`로 남는다
- `ko`와 `en` 페이지가 서로를 alternate로 가리키지 않는다
- locale prefix는 있는데 `<html lang>`는 기본값으로 남아 있다
- 일부 번역이 없는 페이지까지 `hreflang`을 전부 노출한다

국제화에서 metadata는 별도 부가기능이 아니라 라우팅 정책의 일부다. 즉 locale마다 페이지를 렌더링한다면, metadata도 같은 규칙으로 조립돼야 한다.

### 예시: 문서 상세 페이지 metadata

```tsx
import type { Metadata } from 'next'
import { notFound } from 'next/navigation'
import { getDocBySlug } from '@/lib/docs'
import { hasLocale } from '../dictionaries'

const SUPPORTED = ['ko', 'en', 'ja'] as const

export async function generateMetadata({
  params,
}: PageProps<'/[lang]/docs/[slug]'>): Promise<Metadata> {
  const { lang, slug } = await params

  if (!hasLocale(lang)) {
    return {
      title: 'Not Found',
      robots: { index: false, follow: false },
    }
  }

  const doc = await getDocBySlug({ lang, slug })
  if (!doc) {
    return {
      title: 'Not Found',
      robots: { index: false, follow: false },
    }
  }

  const languages = Object.fromEntries(
    doc.availableLocales.map((locale) => [
      locale,
      `/${locale}/docs/${doc.localizedSlugs[locale]}`,
    ])
  )

  return {
    title: doc.title,
    description: doc.summary,
    alternates: {
      canonical: `/${lang}/docs/${doc.localizedSlugs[lang]}`,
      languages,
    },
    openGraph: {
      title: doc.title,
      description: doc.summary,
      url: `/${lang}/docs/${doc.localizedSlugs[lang]}`,
      locale: lang,
    },
  }
}
```

### 여기서 중요한 기준

1. **canonical은 현재 locale의 대표 URL이어야 한다**  
   다국어 페이지를 하나의 canonical에 억지로 몰면 locale별 색인 전략이 흐려질 수 있다.

2. **`alternates.languages`는 실제 번역이 존재하는 locale만 노출해야 한다**  
   없는 번역을 일괄 노출하면 품질이 떨어진다.

3. **localized slug를 쓰는 경우 metadata와 본문이 같은 소스에서 slug를 계산해야 한다**  
   본문은 `/en/docs/caching`인데 alternate는 `/en/docs/cache`를 가리키는 식의 불일치를 피해야 한다.

4. **`<html lang>`와 metadata locale 정보가 맞아야 한다**  
   접근성, 검색엔진 해석, 공유 카드 품질 모두에 영향을 준다.

국제화에서 SEO 문제는 500 에러처럼 눈에 띄지 않는다. 대신 몇 주 뒤 색인 품질과 유입에서 조용히 손실이 난다. 그래서 route contract와 metadata contract를 한 세트로 봐야 한다.

---

## 핵심 개념 5: 캐시는 locale별로 분리해야 하고, 특히 tag 설계에서 locale 축을 빼먹으면 교차 오염이 생긴다

다국어 서비스의 캐시 버그는 보통 두 가지 형태로 나온다.

- 한국어 페이지를 수정했는데 영어 페이지까지 같이 무효화돼 불필요한 재생성이 발생한다
- 반대로 영어 콘텐츠만 바뀌었는데 locale 없는 태그를 써서 한국어 stale이 남거나 섞인다

예를 들어 아래는 좋지 않다.

```ts
next: {
  revalidate: 3600,
  tags: ['post-list', `post:${slug}`],
}
```

이 태그는 locale 축이 없다. 같은 slug가 locale마다 존재하거나, 목록 구성 자체가 locale별로 다르면 캐시 의미가 흐려진다.

### 더 안전한 방식

```ts
next: {
  revalidate: 3600,
  tags: [`posts:${lang}`, `post:${lang}:${slug}`],
}
```

또는 테넌트/사이트 축까지 있으면 이렇게 간다.

```ts
next: {
  revalidate: 3600,
  tags: [`site:${siteId}:posts:${lang}`, `site:${siteId}:post:${lang}:${slug}`],
}
```

### 왜 locale 분리가 중요한가

- locale별 발행 시점이 다를 수 있다
- 번역 검수 상태가 다를 수 있다
- 일부 locale만 공개 대상일 수 있다
- 검색 인덱스와 sitemap도 locale별로 따로 갱신될 수 있다

### 실무 예시: 블로그 발행 액션

```tsx
'use server'

import { revalidatePath, revalidateTag } from 'next/cache'

export async function publishPost(input: {
  lang: 'ko' | 'en' | 'ja'
  slug: string
}) {
  await savePost(input)

  revalidateTag(`posts:${input.lang}`)
  revalidateTag(`post:${input.lang}:${input.slug}`)
  revalidatePath(`/${input.lang}/blog`)
  revalidatePath(`/${input.lang}/blog/${input.slug}`)
}
```

이렇게 하면 같은 글이라도 locale별 영향 반경을 분리해 다룰 수 있다.

### 추가로 자주 놓치는 포인트: Router Cache 체감도 locale별로 본다

서버에서 tag/path를 올바르게 무효화해도, 사용자가 `/ko/blog`에서 이동했다가 돌아오는 흐름과 `/en/blog`에서 이동했다가 돌아오는 흐름은 각자 다른 RSC payload를 브라우저가 들고 있을 수 있다. 즉 "한국어에서는 반영되는데 영어에서는 안 보여요"는 서버 캐시가 아니라 locale별 클라이언트 탐색 흐름 차이일 수도 있다.

국제화에서는 stale bug를 반드시 **locale 포함 재현 경로**로 적어야 한다.

---

## 핵심 개념 6: 정적 생성은 locale 수와 곱해진다 — `generateStaticParams`를 쓸수록 빌드 비용과 invalidation 전략을 같이 설계해야 한다

Next.js 국제화 가이드에서 `generateStaticParams`는 매우 자연스러운 선택처럼 보인다.

```tsx
export async function generateStaticParams() {
  return [{ lang: 'ko' }, { lang: 'en' }, { lang: 'ja' }]
}
```

문제는 실무에서 페이지 수가 늘면 정적 경로 수가 **콘텐츠 수 × locale 수**로 늘어난다는 점이다.

예를 들어:

- 문서 2,000개
- locale 5개
- 제품 상세 4,000개
- 마케팅 랜딩 80개

이 정도만 되어도 빌드와 재검증 비용이 꽤 커진다.

### 정적 생성이 잘 맞는 경우

- 문서/블로그처럼 읽기 중심이다
- locale별 공개 콘텐츠가 명확하다
- 발행 빈도가 높지 않다
- edge가 아니라 origin 재생성 비용을 감당 가능하다

### 동적 렌더링 또는 혼합 전략이 더 나은 경우

- locale별 콘텐츠 수가 많고 계속 추가된다
- 일부 locale는 후행 번역이라 공개 시점이 제각각이다
- 제품 데이터가 자주 바뀐다
- 빌드 시간 증가가 배포 병목이 된다

### 현실적인 혼합 전략

1. 상위 landing/문서 목록만 locale별 정적 생성  
2. 상세는 인기 콘텐츠만 prebuild  
3. 나머지는 런타임 생성 + tag 기반 재검증  
4. locale별 번역 공개 시에만 해당 locale path를 무효화

즉 `generateStaticParams`는 편리하지만, 국제화에서는 단순한 DX 도구가 아니라 **빌드 비용 증폭 레버**다. locale 하나 추가가 그냥 번역 파일 하나 추가가 아니라, 정적 경로 수와 QA 범위 증가까지 뜻한다.

---

## 핵심 개념 7: Server Action과 Route Handler는 locale을 자동으로 이해하지 않는다 — 입력, redirect, validation 메시지까지 명시적으로 이어줘야 한다

다국어 UI는 읽기보다 쓰기에서 더 자주 깨진다.

예를 들어 이런 흐름이다.

- 사용자가 `/en/account/profile`에서 저장 버튼을 누른다
- Server Action이 저장은 성공한다
- 그런데 `redirect('/account/profile')`로 보내 버린다
- 결과적으로 locale prefix를 잃고 기본 언어로 떨어진다

또는 이런 문제도 흔하다.

- form validation 에러는 Zod 기본 메시지로 영어/한국어가 섞인다
- flash message는 기본 언어로만 나온다
- 메일 발송이나 background job은 locale 문맥을 잃는다

### 추천 패턴

Server Action 입력에 locale을 명시적으로 포함시킨다.

```tsx
// app/[lang]/account/profile/actions.ts
'use server'

import { redirect } from 'next/navigation'

export async function updateProfile(input: {
  lang: 'ko' | 'en' | 'ja'
  displayName: string
}) {
  await saveProfile(input)
  redirect(`/${input.lang}/account/profile`)
}
```

혹은 서버에서 `params.lang`을 함께 묶은 form action을 만든다.

```tsx
<form action={updateProfile}>
  <input type="hidden" name="lang" value={lang} />
  <input type="text" name="displayName" defaultValue={profile.displayName} />
  <button type="submit">{dict.profile.save}</button>
</form>
```

### validation 메시지도 locale contract의 일부다

실무에서 자주 놓치는 포인트는 번역 dictionary는 있는데 validation은 기본 영어로 나가는 경우다. 이건 UX 품질을 크게 깎는다.

좋은 기준은 이렇다.

- dictionary key와 validation message key를 분리한다
- Zod schema는 message literal 대신 key를 반환하게 하거나 locale-aware factory로 만든다
- Server Action이 locale별 validation formatter를 사용한다

### background 작업도 locale을 명시적으로 받는다

예를 들어 비밀번호 재설정 메일, 결제 영수증, 초대 메일은 요청 당시 locale을 같이 저장해 두는 편이 좋다.

- 현재 UI는 영어인데 메일은 한국어로 감
- 관리자 초대는 일본어 페이지에서 했는데 안내 메일은 영어로 감

이런 문제는 대부분 "locale은 화면에만 필요하다"고 가정했을 때 생긴다. 실제로 locale은 **사용자 커뮤니케이션 문맥 전체**에 필요하다.

---

## 실무 예시 1: 문서 사이트에서 locale별 정적 페이지 + dictionary + alternate 링크를 운영하는 구조

문서 사이트는 국제화 설계를 설명하기 좋은 대표 사례다.

### 요구사항

- `/ko/docs/[slug]`, `/en/docs/[slug]`
- 일부 문서는 영어만 먼저 공개
- 검색엔진에 locale별 문서를 모두 노출
- 언어 전환 시 같은 문서의 다른 locale로 이동

### 추천 구조

1. `app/[lang]` 아래 route 구성  
2. 문서 데이터는 locale+slug 기준 조회  
3. metadata에서 `alternates.languages` 구성  
4. 번역 없는 locale은 전환 버튼을 비활성 또는 fallback 안내  
5. 캐시 tag는 `doc:${lang}:${slug}` 기준 분리

### 이 구조의 장점

- locale별 색인과 canonical이 명확하다
- 번역 진행률이 다른 현실을 자연스럽게 반영할 수 있다
- 언어 전환 로직이 slug 매핑과 함께 관리된다

### 이 구조에서 자주 하는 실수

- 전환 버튼이 단순히 현재 slug만 다른 locale prefix에 붙임
- 실제 localized slug 매핑이 없어서 404 발생
- metadata는 locale별인데 sitemap은 기본 locale만 내보냄

문서 사이트일수록 "같은 문서"와 "같은 URL 패턴"을 혼동하면 안 된다. 같은 문서라도 locale별 slug, 발행 상태, 검색 대표성은 다를 수 있다.

---

## 실무 예시 2: 커머스 상품 상세에서 locale와 region을 분리하지 않으면 번역과 비즈니스 정책이 섞인다

커머스에서 흔한 실수는 locale과 region을 같은 것으로 취급하는 것이다.

- `ko`면 KR 가격
- `en`이면 US 가격
- `ja`면 JP 재고

이렇게 바로 묶으면 나중에 문제가 생긴다. 영어 사용자라고 해서 항상 미국 가격을 봐야 하는 것은 아니다. 한국 사용자가 영어 UI를 볼 수도 있고, 일본 사용자가 영어 문서를 볼 수도 있다.

### 더 안전한 구분

- **locale**: UI 언어와 형식
- **region**: 가격, 세금, 재고, 배송, 결제 정책

Next.js 국제화 설계에서도 이 분리가 중요하다.

- `lang` route param은 UI 번역에 사용
- region은 쿠키, 계정 설정, 별도 country selector로 처리
- metadata와 dictionary는 locale 기준
- 상품 가격/배송 정책은 region 기준 캐시 분리

캐시 tag도 분리하는 편이 좋다.

- `product-content:ko:slug`
- `product-content:en:slug`
- `price:kr:sku`
- `price:jp:sku`

이렇게 나누지 않으면 UI 번역 변경 때문에 가격 캐시까지 넓게 흔들리거나, 반대로 region 변경이 locale 경로 재검증과 섞여 복잡해진다.

국제화는 번역만의 문제가 아니어서, 오히려 이런 **문맥 축 분리**가 운영 안정성에 더 중요하다.

---

## 실무 예시 3: SaaS 백오피스는 다국어 마케팅 사이트와 다른 기준으로 설계해야 한다

많은 팀이 공개 마케팅 페이지 기준으로 국제화를 설계한 뒤, 같은 패턴을 백오피스에도 그대로 적용한다. 이때 자주 어긋난다.

### 마케팅/문서 사이트에서 중요한 것

- SEO
- canonical / alternates
- 정적 생성 효율
- 공유 카드 품질

### 백오피스에서 더 중요한 것

- 로그인 이후 locale 유지
- 폼 validation과 에러 메시지 일관성
- Server Action redirect 정합성
- audit log, 알림, 이메일 템플릿 locale 전달

즉 백오피스는 `hreflang`보다 **쓰기 흐름의 locale 유지**가 더 중요하다.

실무 기준으로는 아래가 잘 맞는다.

- 첫 진입만 Proxy가 locale 보정
- 로그인 이후에는 사용자 설정 locale을 우선
- locale 변경은 프로필에도 반영
- 서버 액션은 locale hidden input 또는 route param으로 명시 전달
- 시스템 알림/메일도 locale을 함께 저장

이렇게 하면 "화면은 영어인데 저장 성공 토스트는 한국어", "리다이렉트만 기본 언어" 같은 자잘하지만 치명적인 UX 균열을 줄일 수 있다.

---

## 트레이드오프 1: 라이브러리 도입(`next-intl` 등)과 최소 구현 사이 균형을 먼저 결정해야 한다

Next.js 국제화는 직접 구현할 수도 있고, 라이브러리를 쓸 수도 있다. 둘 다 장단점이 분명하다.

### 직접 구현 장점

- 구조를 완전히 이해하고 제어할 수 있다
- 단순한 다국어 사이트에는 충분하다
- 번들/런타임 의존성을 최소화할 수 있다

### 직접 구현 단점

- 메시지 포매팅, ICU, pluralization, rich text 처리에서 금방 복잡해진다
- locale 전환 훅, provider, type safety를 직접 유지해야 한다
- 팀원이 늘수록 공통 규약 없이는 금방 제각각이 된다

### 라이브러리 장점

- ICU 메시지, locale-aware formatting, hooks, tooling이 성숙해 있다
- 대규모 다국어 앱에서 유지보수가 쉬워진다

### 라이브러리 단점

- 추상화 비용이 있다
- App Router/RSC/Client 경계를 이해하지 않으면 오히려 더 헷갈릴 수 있다
- 팀이 라이브러리의 운영 모델을 같이 배워야 한다

추천은 이렇다.

- 블로그, 문서, 소규모 제품: 최소 구현으로 시작 가능
- 백오피스+마케팅+이메일+복수 팀이 함께 쓰는 서비스: 라이브러리 도입 검토 가치가 큼

중요한 건 라이브러리 유무보다 **locale contract와 route contract를 먼저 정하는 것**이다. 이게 없으면 어떤 라이브러리도 구조를 구해주지 못한다.

---

## 트레이드오프 2: localized slug는 SEO에 좋을 수 있지만 콘텐츠 운영 복잡도를 크게 올린다

예를 들어 문서 slug를 이렇게 두고 싶을 수 있다.

- `/ko/docs/캐시-전략`
- `/en/docs/cache-strategy`
- `/ja/docs/cache-strategy-ja`

이 방식은 locale별 자연스러운 URL과 검색 적합성에서 이점이 있다. 하지만 운영 비용이 급격히 올라간다.

- slug 매핑 테이블 필요
- 언어 전환 시 단순 prefix 치환 불가
- redirect 정책 복잡화
- metadata, sitemap, canonical 생성 로직도 복잡해짐

반대로 locale별로 slug를 통일하면 단순하다.

- `/ko/docs/cache-strategy`
- `/en/docs/cache-strategy`

하지만 일부 언어에서는 자연스러움이 떨어질 수 있다.

실무적으로는 다음 기준이 안전하다.

- 문서/블로그: localized slug 도입 가능, 단 매핑 체계를 먼저 마련
- 백오피스/앱 기능 경로: slug 통일이 운영상 더 유리

즉 SEO 이득이 있는 공개 콘텐츠와, 운영 단순성이 중요한 제품 경로를 같은 기준으로 보지 않는 편이 맞다.

---

## 트레이드오프 3: locale별 정적 생성은 빠르지만, 번역 출시 흐름이 잦다면 invalidation 운영이 더 중요해진다

정적 생성은 읽기 성능과 비용 면에서 강력하다. 하지만 다국어에서는 번역 팀의 작업 흐름이 끼는 순간 양상이 달라진다.

- 원문 발행 후 며칠 뒤 번역 공개
- 일부 섹션만 locale별 우선순위가 다름
- 긴급 오탈자 수정이 특정 locale에만 발생

이 경우 단순 ISR TTL만으로는 운영이 깔끔하지 않다. 보통은 locale별 on-demand revalidation이나 tag 기반 invalidation이 더 중요해진다.

즉 국제화에서는 성능보다 먼저 **출시 흐름과 캐시 무효화 흐름을 어떻게 맞출지**를 설계해야 한다.

---

## 흔한 실수 1: `Accept-Language`만 믿고 사용자의 명시적 선택을 덮어쓴다

이건 UX를 망치는 가장 흔한 실수다. 브라우저 설정은 영어지만, 사용자는 해당 서비스에서 한국어를 쓰고 싶을 수 있다. 명시적 선택을 쿠키나 프로필에 저장했다면 그 우선순위가 더 높아야 한다.

---

## 흔한 실수 2: locale 없는 캐시 태그를 써서 번역 콘텐츠가 서로 오염된다

`post-list`, `docs`, `product-detail` 같은 태그만 두면 처음엔 편하다. 하지만 다국어가 붙는 순간 stale 범위를 설명하기 어렵고, 일부 locale만 갱신하는 작업도 힘들어진다.

---

## 흔한 실수 3: Server Action redirect에서 locale prefix를 잃는다

읽기 경로는 잘 붙어 있는데, 저장 후 redirect만 기본 경로로 가는 버그가 매우 흔하다. 다국어 앱에서 POST 이후 redirect는 항상 locale-aware 해야 한다.

---

## 흔한 실수 4: metadata의 alternate 링크를 실제 번역 존재 여부와 무관하게 일괄 생성한다

없는 번역으로 `hreflang`을 뿌리면 검색엔진 신뢰도와 사용자 경험이 같이 나빠진다. 번역이 없는 locale은 전환 버튼, sitemap, alternates 모두에서 일관되게 처리해야 한다.

---

## 흔한 실수 5: locale과 region을 같은 값으로 취급한다

UI 언어와 가격/세금/배송 정책은 별도 축이다. 둘을 하나로 묶으면 국제화보다 더 큰 비즈니스 복잡도를 초래한다.

---

## 체크리스트: Next.js 다국어 서비스를 PR 전에 점검하는 질문

### Locale contract

- [ ] locale 우선순위가 쿠키/프로필/브라우저/기본값 순으로 명확한가?
- [ ] 첫 진입 redirect 규칙과 로그인 후 locale 유지 규칙이 충돌하지 않는가?
- [ ] 사용자가 직접 언어를 바꿨을 때 다음 방문에서도 유지되는가?

### Routing

- [ ] `app/[lang]` 기준으로 route tree가 일관되게 구성되어 있는가?
- [ ] locale 없는 요청은 Proxy에서만 보정하고, 앱 내부에서 다시 검증하는가?
- [ ] localized slug를 쓴다면 locale 전환 시 slug 매핑이 있는가?

### Dictionary / Rendering

- [ ] dictionary는 서버 우선으로 로드되는가?
- [ ] Client Component에 전체 메시지 객체를 불필요하게 내려보내지 않는가?
- [ ] validation, toast, email, background job까지 locale 문맥이 이어지는가?

### Metadata / SEO

- [ ] `<html lang>`와 metadata locale 정보가 일치하는가?
- [ ] canonical과 `alternates.languages`가 실제 locale 경로와 일치하는가?
- [ ] 번역이 없는 locale을 alternate나 sitemap에 노출하지 않는가?

### Cache / Build

- [ ] 캐시 태그와 무효화 경로에 locale 축이 포함되어 있는가?
- [ ] `generateStaticParams`가 locale 수만큼 빌드 비용을 키운다는 점을 고려했는가?
- [ ] 일부 locale만 갱신되는 운영 흐름에 맞는 invalidation 전략이 있는가?

### Write Flow

- [ ] Server Action/Route Handler가 locale을 명시적으로 입력받거나 보존하는가?
- [ ] redirect, flash message, validation error가 현재 locale을 유지하는가?
- [ ] 이메일/알림 발송 시 요청 당시 locale이 저장되는가?

---

## 팀 규칙으로 정리하면 더 강해진다

### 규칙 1: locale은 route param이면서 동시에 요청 문맥이다

단순히 `/ko` 경로 세그먼트로만 보지 말고, metadata, cache tag, redirect, validation, notification까지 따라가는 문맥으로 본다.

### 규칙 2: Proxy는 첫 진입 협상만 맡고, 애플리케이션이 최종 locale 정합성을 책임진다

Proxy에 로직을 과하게 밀어 넣으면 디버깅이 어려워진다. 앱 내부 `layout/page/action`에서 locale 사용 책임을 분명히 둔다.

### 규칙 3: 캐시와 SEO는 반드시 locale 축으로 설명 가능해야 한다

`post:slug`가 아니라 `post:lang:slug`, `/docs`가 아니라 `/${lang}/docs`처럼 locale을 포함한 언어로 설계해야 stale bug와 색인 문제를 추적할 수 있다.

---

## 한 줄 정리

**Next.js 국제화의 핵심은 번역 파일을 붙이는 것이 아니라, locale 결정 규칙을 먼저 고정한 뒤 `app/[lang]` 라우팅, 서버 우선 dictionary 로딩, locale-aware metadata, locale 분리 캐시, Server Action redirect 정합성을 하나의 계약으로 운영하는 데 있다.**
