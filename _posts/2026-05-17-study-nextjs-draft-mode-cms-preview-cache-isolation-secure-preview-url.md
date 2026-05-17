---
layout: post
title: "Next.js Draft Mode 실전: CMS Preview, Cache Isolation, Secure Preview URL로 게시 전 콘텐츠를 안전하게 운영하는 법"
date: 2026-05-17 11:40:00 +0900
categories: [nextjs]
tags: [study, nextjs, draft-mode, cms, preview, cache, route-handler, metadata, security]
permalink: /nextjs/2026/05/17/study-nextjs-draft-mode-cms-preview-cache-isolation-secure-preview-url.html
---

## 배경: 게시 전 미리보기는 "편의 기능"이 아니라 게시 파이프라인의 신뢰도를 결정하는 운영 경계다

콘텐츠 팀이 있는 서비스에서 Next.js를 쓰다 보면 언젠가 반드시 이 요구가 나온다.

- 발행 전 원고를 실제 화면처럼 보고 싶다
- 헤드리스 CMS에서 저장한 초안을 바로 확인하고 싶다
- SEO 메타데이터와 본문이 같이 맞는지 보고 싶다
- 번역 중인 locale만 따로 검수하고 싶다
- 정적 생성 사이트라도 매번 전체 빌드 없이 수정 사항을 확인하고 싶다

초기에는 이 요구가 단순해 보인다. 보통은 이렇게 시작한다.

- `app/api/draft/route.ts`를 만든다
- `draftMode().enable()`을 호출한다
- CMS에서 `/api/draft?slug=/posts/foo` 같은 URL을 연다
- 페이지에서 `draftMode().isEnabled`를 보고 draft API를 읽는다

여기까지는 금방 된다. 문제는 운영에 들어간 뒤다.

- 미리보기 링크가 외부로 새어 누구나 초안을 볼 수 있다
- `slug`를 그대로 redirect해서 open redirect 취약점이 생긴다
- draft 응답이 published 캐시를 오염시켜 일반 사용자도 초안이 보인다
- 반대로 published 캐시가 남아 편집자는 미리보기인데도 예전 글을 본다
- `generateMetadata()`는 발행 버전을 읽고 본문은 draft 버전을 읽어 제목과 본문이 엇갈린다
- 미리보기 페이지가 검색엔진에 노출돼 staging 성격의 URL이 색인된다
- preview 종료 경로가 없어 편집자가 계속 draft 쿠키를 물고 다닌다
- 다국어/다중 테넌트/권한 분기가 붙으면서 preview URL 규칙이 금방 지저분해진다

즉 Draft Mode는 단순히 "쿠키 하나 켜는 기능"이 아니다.

> **Draft Mode의 본질은 정적 사이트의 일부 요청만 안전하게 동적으로 전환하고, published 세계와 draft 세계를 캐시·보안·SEO 차원에서 분리하는 운영 설계**다.

이 글은 Next.js Draft Mode 문법 소개가 아니라, 중급 이상 개발자 기준으로 아래를 한 번에 정리한다.

1. 왜 Draft Mode를 단순한 토글로 보면 사고가 나는지
2. CMS Preview URL을 어떻게 안전하게 열어야 하는지
3. published/draft 데이터를 어떻게 분리해 캐시 오염을 막는지
4. 메타데이터, noindex, 권한, locale을 어떻게 함께 맞추는지
5. 실무에서 자주 깨지는 지점과 운영 체크리스트는 무엇인지

---

## 먼저 큰 그림: Draft Mode는 "렌더링 모드 전환 + 데이터 소스 분기 + 검수용 요청 문맥"의 조합이다

Draft Mode를 안정적으로 이해하려면 흐름을 세 층으로 나눠 보는 편이 좋다.

### 1) 진입 경계

CMS 또는 내부 관리자 UI가 preview URL을 연다.

- secret 검증
- 대상 문서 존재 여부 검증
- 허용된 slug로 정규화
- Draft Mode 쿠키 설정
- 안전한 내부 경로로 redirect

### 2) 읽기 경계

페이지, 레이아웃, 메타데이터 생성 로직이 `draftMode().isEnabled`를 보고 **published 소스와 draft 소스 중 무엇을 읽을지** 결정한다.

- published: CDN/정적 캐시 친화
- draft: 요청 시점 조회, private/no-store 성격

### 3) 종료 경계

검수가 끝났으면 Draft Mode를 꺼야 한다.

- preview exit route 또는 Server Action
- 편집자에게 현재 preview 상태 표시
- 검색엔진 비노출 보장

이 세 층을 분리하지 않으면 보통 진입 경계의 보안 문제, 읽기 경계의 캐시 문제, 종료 경계의 UX 문제가 한꺼번에 섞인다.

실무에서 가장 중요한 관점은 단순하다.

> **Draft Mode는 초안 조회 권한이 있는 일부 요청만 published 경로에서 잠시 분기시키는 기능이지, 사이트 전체를 preview 앱으로 바꾸는 기능이 아니다.**

---

## 핵심 개념 1: Draft Mode는 쿠키 기능이 아니라 "정적 기본값을 요청 시점 렌더링으로 전환하는 스위치"다

Next.js App Router에서 Draft Mode를 켜면 내부적으로는 `__prerender_bypass` 쿠키가 설정되고, 해당 요청 문맥에서는 정적으로 재사용되던 결과 대신 fresh evaluation이 일어난다.

이걸 단순히 "편집자 쿠키" 정도로만 이해하면 놓치는 포인트가 있다.

### 왜 중요한가

정적 생성 사이트의 핵심 장점은 캐시 재사용이다. 그런데 preview는 정반대 요구를 가진다.

- 아직 발행되지 않은 데이터여야 한다
- 최신 저장본이 즉시 보여야 한다
- 다른 사용자와 캐시를 공유하면 안 된다
- 검수자가 수정할 때마다 build를 다시 돌리면 안 된다

즉 preview 요청은 의도적으로 published 경로의 최적화에서 이탈해야 한다.

### 운영적으로 이해해야 할 사실

1. **Draft Mode는 요청 문맥이다**  
   특정 브라우저 세션의 일부 요청만 preview 세계로 보낸다.

2. **Draft Mode는 published 캐시를 덮어쓰면 안 된다**  
   draft 응답이 공용 캐시에 저장되면 사고다.

3. **Draft Mode는 페이지 본문뿐 아니라 메타데이터에도 영향을 줘야 한다**  
   제목, 설명, canonical, robots가 본문과 다른 소스를 읽으면 검수가 틀어진다.

4. **Draft Mode는 영구 상태가 아니다**  
   "켜고 끝"이 아니라 종료 플로우까지 있어야 한다.

### Cache Components 관점에서의 의미

Next.js 최신 모델에서는 Cache Components 사용 시 Draft Mode가 활성화되면 캐시 지시어 스코프 안의 함수/컴포넌트도 요청마다 fresh evaluation 된다. 이 덕분에 preview 요청이 published 캐시를 오염시키지 않도록 설계하기 쉬워진다.

하지만 이 사실이 "아무 설계도 필요 없다"는 뜻은 아니다. 왜냐하면 실제 서비스는 보통 아래를 같이 갖기 때문이다.

- 외부 CMS API 캐시
- 사내 BFF 캐시
- CDN 레벨 캐시
- 애플리케이션 내부 `use cache`, `unstable_cache`, tag revalidation
- locale/tenant별 데이터 분기

따라서 Next.js가 preview 요청을 동적으로 바꿔 준다고 해도, **내가 직접 만든 캐시 키와 데이터 선택 로직까지 자동으로 안전해지지는 않는다.**

---

## 핵심 개념 2: Preview URL의 핵심 리스크는 open redirect가 아니라 "권한 없는 초안 진입"과 "경로 위조"다

Draft Mode 예제를 보면 흔히 이런 코드로 시작한다.

```ts
import { draftMode } from 'next/headers'
import { redirect } from 'next/navigation'

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const secret = searchParams.get('secret')
  const slug = searchParams.get('slug')

  if (secret !== process.env.CMS_PREVIEW_SECRET || !slug) {
    return new Response('Unauthorized', { status: 401 })
  }

  const draft = await draftMode()
  draft.enable()
  redirect(slug)
}
```

데모에는 충분하지만 운영에는 부족하다. 가장 큰 문제는 `slug`를 그대로 신뢰한다는 점이다.

### 여기서 실제로 터지는 문제

- 존재하지 않는 경로를 preview로 열어 404 검수 동선이 꼬인다
- CMS 데이터와 무관한 임의 경로로 preview 진입이 가능해진다
- 외부 URL 또는 예상치 못한 경로로 redirect될 여지가 생긴다
- locale prefix, tenant prefix, canonical slug 정합성이 깨진다
- secret이 한번 노출되면 사실상 사이트 전체의 초안 탐색기가 된다

### 더 안전한 기준

1. **secret만 확인하지 말고 slug가 실제 CMS 엔트리와 매핑되는지 확인한다**
2. **redirect 대상은 querystring의 raw slug가 아니라 CMS가 반환한 canonical path를 쓴다**
3. **가능하면 entry id, locale, preview token scope를 함께 검증한다**
4. **preview URL은 public share link가 아니라 editor workflow의 연장선으로 취급한다**

### 권장 Route Handler 예시

```ts
import { draftMode } from 'next/headers'
import { redirect } from 'next/navigation'
import { z } from 'zod'

const previewQuerySchema = z.object({
  secret: z.string().min(1),
  slug: z.string().min(1),
  locale: z.string().optional(),
})

type CmsPreviewEntry = {
  slug: string
  locale: string
  status: 'draft' | 'published'
}

async function getPreviewEntryBySlug(input: { slug: string; locale?: string }): Promise<CmsPreviewEntry | null> {
  // CMS preview API 조회
  return cmsClient.getPreviewEntryBySlug(input)
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const parsed = previewQuerySchema.safeParse({
    secret: searchParams.get('secret'),
    slug: searchParams.get('slug'),
    locale: searchParams.get('locale') ?? undefined,
  })

  if (!parsed.success) {
    return new Response('Invalid preview query', { status: 400 })
  }

  if (parsed.data.secret !== process.env.CMS_PREVIEW_SECRET) {
    return new Response('Unauthorized', { status: 401 })
  }

  const entry = await getPreviewEntryBySlug({
    slug: parsed.data.slug,
    locale: parsed.data.locale,
  })

  if (!entry) {
    return new Response('Preview target not found', { status: 404 })
  }

  const draft = await draftMode()
  draft.enable()

  redirect(`/${entry.locale}/blog/${entry.slug}`)
}
```

이 구조의 핵심은 간단하다.

- URL 파라미터는 검증 대상일 뿐 진실의 원천이 아니다
- 진실의 원천은 CMS preview API 또는 내부 콘텐츠 저장소다
- redirect는 항상 **검증 후 재계산된 내부 경로**를 쓴다

실무에서는 이 차이 하나로 preview 보안 수준이 크게 달라진다.

---

## 핵심 개념 3: Draft Mode의 진짜 난제는 "draft를 어떻게 보여줄까"가 아니라 "published와 어떻게 섞이지 않게 할까"다

많은 팀이 preview 구현 초기에 집중하는 것은 draft 데이터를 읽는 방법이다. 하지만 운영 단계에서 더 자주 터지는 것은 cache contamination이다.

대표적인 사고 패턴은 이렇다.

- published fetch에 붙은 tag를 draft fetch에도 재사용한다
- draft 응답을 `unstable_cache`에 그대로 태운다
- BFF가 preview 헤더를 무시하고 응답을 공용 캐시에 넣는다
- metadata fetch와 page fetch가 서로 다른 캐시 정책을 쓴다
- locale/tag가 캐시 키에 안 들어가 다른 언어의 초안이 섞인다

### published와 draft를 분리하는 최소 원칙

#### 1) 데이터 소스를 분리한다

가장 단순한 구조는 아래 둘 중 하나다.

- published API와 preview API를 아예 분리
- 동일 API라도 preview 토큰/파라미터로 명시적 분기

```ts
import { draftMode } from 'next/headers'

export async function getPostBySlug(slug: string, locale: string) {
  const { isEnabled } = await draftMode()

  if (isEnabled) {
    return cmsClient.getDraftPost({ slug, locale })
  }

  return cmsClient.getPublishedPost({ slug, locale })
}
```

핵심은 함수 이름보다 계약이다.

- preview 요청이면 unpublished 필드까지 볼 수 있는가
- scheduled publish 상태도 보여줄 것인가
- 삭제 예정 콘텐츠를 어떻게 다룰 것인가
- 번역 미완성일 때 fallback locale을 허용할 것인가

이 계약이 애매하면 preview는 보이는데 실제 발행 후 화면이 달라진다.

#### 2) 캐시 키를 공유하지 않는다

published 세계와 draft 세계는 캐시 관점에서 별도 키 공간으로 생각하는 편이 안전하다.

```ts
import { unstable_cache } from 'next/cache'

const getPublishedPostCached = unstable_cache(
  async (slug: string, locale: string) => {
    return cmsClient.getPublishedPost({ slug, locale })
  },
  ['cms-post-published'],
  {
    tags: ['post:published'],
  }
)
```

반대로 preview는 대개 캐시를 피하거나, 꼭 필요하다면 아주 짧고 private한 범위로만 제한한다.

```ts
export async function getPreviewPost(slug: string, locale: string) {
  return cmsClient.getDraftPost({ slug, locale })
}
```

실무 기준으로는 preview 요청에 공용 캐시 최적화를 욕심내지 않는 편이 맞다. 검수 트래픽은 보통 제한적이고, 사고 비용이 훨씬 크기 때문이다.

#### 3) metadata와 page body가 같은 소스를 읽게 만든다

초안 검수에서 자주 놓치는 부분이 metadata다.

- 본문은 draft
- `generateMetadata()`는 published
- OG 이미지 생성은 published
- canonical은 published slug

이러면 편집자는 실제 발행 화면을 검수했다고 생각하지만, 사실 중요한 SEO 표면이 다른 버전을 보고 있는 셈이다.

```tsx
import { draftMode } from 'next/headers'
import type { Metadata } from 'next'

async function getPostForRender(slug: string, locale: string) {
  const { isEnabled } = await draftMode()
  return isEnabled
    ? cmsClient.getDraftPost({ slug, locale })
    : cmsClient.getPublishedPost({ slug, locale })
}

export async function generateMetadata({ params }: { params: Promise<{ locale: string; slug: string }> }): Promise<Metadata> {
  const { locale, slug } = await params
  const post = await getPostForRender(slug, locale)
  const { isEnabled } = await draftMode()

  return {
    title: post.seoTitle ?? post.title,
    description: post.seoDescription,
    robots: isEnabled ? { index: false, follow: false } : undefined,
  }
}
```

이렇게 해야 검수자가 보는 제목, 설명, 로봇 정책이 실제 렌더 소스와 맞는다.

---

## 핵심 개념 4: 실무에서 Preview는 콘텐츠만 검수하는 게 아니라 "출판 전 사용자 경험 전체"를 검수해야 한다

Draft Mode가 붙는 순간 검수 대상은 본문 텍스트를 넘는다.

- 헤더 badge가 제대로 뜨는가
- OG/title/description이 draft 기준으로 맞는가
- 관련 글, 추천 글, 네비게이션 제목이 함께 맞는가
- locale fallback이 의도대로 작동하는가
- 비공개 글인데 검색엔진 차단이 확실한가
- 미리보기 상태에서 저장 후 다시 봐도 최신본인가

그래서 preview UI는 가능하면 명시적이어야 한다.

### 추천하는 최소 UX

1. 현재 preview 상태를 보여 주는 배지
2. preview 종료 버튼
3. 초안/발행 상태 표시
4. 마지막 저장 시각 또는 revision id 표시
5. noindex/noarchive 성격의 메타 정책

예를 들면 이런 식이다.

```tsx
import Link from 'next/link'
import { draftMode } from 'next/headers'

export async function PreviewBanner() {
  const { isEnabled } = await draftMode()
  if (!isEnabled) return null

  return (
    <div className="bg-amber-100 px-4 py-3 text-sm text-amber-950">
      Preview mode is on. You are viewing draft content.
      <Link className="ml-3 underline" href="/api/draft/disable">
        Exit preview
      </Link>
    </div>
  )
}
```

이런 UI가 사소해 보여도 편집자 경험에 큰 차이를 만든다. 특히 운영 이슈가 터졌을 때 "지금 내가 초안을 보고 있는지, 발행본을 보고 있는지"가 즉시 드러나야 디버깅이 빨라진다.

### robots/noindex는 거의 기본값으로 봐도 된다

preview 상태의 페이지는 검색엔진에 노출될 이유가 거의 없다. 그래서 metadata에서 preview일 때 `noindex, nofollow`를 넣는 편이 안전하다.

또 CDN이나 프록시 레벨에서도 preview 응답에 대해 아래 성격을 분명히 하는 편이 좋다.

- `private`
- `no-store`
- 공유 캐시 비활성

Next.js가 Draft Mode에서 관련 헤더 성격을 잡아 주더라도, 사내 BFF나 외부 CDN 규칙이 별도로 있다면 그 계층도 함께 점검해야 한다.

---

## 핵심 개념 5: Draft Mode는 켜는 것보다 "끝내는 흐름"이 더 중요하다

운영에서 자주 잊히는 것이 disable 경로다.

편집자가 preview를 본 뒤 Draft Mode를 끄지 않으면 다음 문제가 생긴다.

- 일반 페이지를 보면서도 계속 draft 응답을 본다
- 버그 제보가 들어왔는데 재현이 안 된다
- QA가 preview 쿠키를 유지한 채 캡처를 남겨 혼선이 생긴다
- 발행 후에도 옛 draft 데이터를 보고 "배포가 안 됐다"고 오해한다

### 최소한의 종료 Route Handler

```ts
import { draftMode } from 'next/headers'
import { redirect } from 'next/navigation'

export async function GET(request: Request) {
  const draft = await draftMode()
  draft.disable()

  const { searchParams } = new URL(request.url)
  const returnTo = searchParams.get('returnTo')

  if (returnTo && returnTo.startsWith('/')) {
    redirect(returnTo)
  }

  redirect('/')
}
```

여기서도 기준은 같다.

- 외부 URL로 나가는 redirect는 허용하지 않는다
- 상대 경로나 허용된 내부 path만 받는다
- 가능하면 현재 문서의 published 경로로 돌려보낸다

### 저장 후 즉시 재검수 흐름도 설계해야 한다

CMS에서 초안을 저장하면 preview 페이지를 새로고침할 때 최신본이 보여야 한다. 이때 흔히 두 가지 접근이 있다.

1. preview 요청은 항상 no-store 성격으로 읽는다
2. preview도 짧은 TTL을 두되 revision id를 키로 넣는다

대부분의 콘텐츠 검수 화면에서는 1번이 더 안전하다. 반면 초안 미리보기가 아주 무겁고 조회 비용이 큰 경우에는 2번을 고민할 수 있다.

하지만 2번을 택할 때도 조건이 있다.

- revision id가 확실히 바뀌는가
- metadata와 body가 같은 revision을 보는가
- locale별 revision 분리가 되는가
- editor A와 editor B의 권한 차이가 캐시에 섞이지 않는가

이 질문에 답이 흐리면 preview 캐시는 포기하는 편이 낫다.

---

## 실무 예시: Headless CMS 블로그의 Draft Mode를 어떻게 구조화할까

아래는 블로그/콘텐츠 사이트에서 비교적 안전하게 가져갈 수 있는 구조다.

### 폴더 예시

```txt
app/
  api/
    draft/
      route.ts           # preview 진입
    draft/disable/
      route.ts           # preview 종료
  [locale]/
    (content)/
      blog/
        [slug]/
          page.tsx
          loading.tsx
lib/
  cms/
    client.ts
    queries.ts
    get-post.ts
  preview/
    resolve-preview-target.ts
    preview-schema.ts
components/
  preview-banner.tsx
```

### 데이터 읽기 계층 예시

```ts
import { draftMode } from 'next/headers'

type GetPostInput = {
  slug: string
  locale: string
}

export async function getPostForRender({ slug, locale }: GetPostInput) {
  const { isEnabled } = await draftMode()

  if (isEnabled) {
    return cmsClient.getDraftPost({ slug, locale })
  }

  return cmsClient.getPublishedPost({ slug, locale })
}

export async function getRelatedPostsForRender({ slug, locale }: GetPostInput) {
  const { isEnabled } = await draftMode()

  return isEnabled
    ? cmsClient.getDraftRelatedPosts({ slug, locale })
    : cmsClient.getPublishedRelatedPosts({ slug, locale })
}
```

이렇게 하면 페이지 본문뿐 아니라 관련 글, 추천 섹션도 같은 preview 문맥을 공유할 수 있다.

### 페이지 예시

```tsx
import { notFound } from 'next/navigation'
import { getPostForRender, getRelatedPostsForRender } from '@/lib/cms/get-post'

export default async function BlogPostPage({
  params,
}: {
  params: Promise<{ locale: string; slug: string }>
}) {
  const { locale, slug } = await params

  const [post, relatedPosts] = await Promise.all([
    getPostForRender({ slug, locale }),
    getRelatedPostsForRender({ slug, locale }),
  ])

  if (!post) notFound()

  return (
    <article>
      <h1>{post.title}</h1>
      <p>{post.summary}</p>
      <div dangerouslySetInnerHTML={{ __html: post.html }} />
      <aside>
        {relatedPosts.map((item) => (
          <a key={item.id} href={`/${locale}/blog/${item.slug}`}>
            {item.title}
          </a>
        ))}
      </aside>
    </article>
  )
}
```

### metadata 예시

```tsx
import type { Metadata } from 'next'
import { draftMode } from 'next/headers'
import { getPostForRender } from '@/lib/cms/get-post'

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string; slug: string }>
}): Promise<Metadata> {
  const { locale, slug } = await params
  const [post, { isEnabled }] = await Promise.all([
    getPostForRender({ slug, locale }),
    draftMode(),
  ])

  if (!post) {
    return {
      title: 'Not Found',
      robots: { index: false, follow: false },
    }
  }

  return {
    title: post.seoTitle ?? post.title,
    description: post.seoDescription ?? post.summary,
    robots: isEnabled ? { index: false, follow: false } : undefined,
    alternates: {
      canonical: isEnabled ? undefined : `https://example.com/${locale}/blog/${post.slug}`,
    },
  }
}
```

포인트는 preview일 때 canonical을 무심코 published URL로 박아 넣지 않는 것이다. 검수 중 canonical이 꼭 필요하지 않다면 아예 비우거나, 운영 정책에 맞는 별도 처리로 두는 편이 안전하다.

---

## 트레이드오프: Draft Mode를 어디까지 "실제 서비스와 똑같게" 만들 것인가

Draft Mode 설계에서 자주 부딪히는 선택지는 결국 이것이다.

### 선택지 A: 실제 서비스와 거의 동일하게 보여 준다

장점

- 편집자가 발행 후 결과를 더 정확히 예측할 수 있다
- 실서비스 컴포넌트 재사용률이 높다
- QA와 콘텐츠 검수가 한 화면에서 이뤄진다

단점

- published/draft 분기 로직이 서비스 전역으로 퍼질 수 있다
- 캐시, 권한, metadata, 추천 로직까지 모두 preview-aware 해야 한다
- 잘못 설계하면 production 경로가 preview 복잡도에 오염된다

### 선택지 B: preview 전용 단순 페이지를 둔다

장점

- 구현이 단순하다
- 보안/캐시 격리가 쉽다
- 운영 리스크가 낮다

단점

- 실제 발행 화면과 차이가 날 수 있다
- 편집자 입장에서 "진짜로 어떻게 보일지" 확신이 떨어진다
- 메타데이터, 추천 블록, 레이아웃 차이를 놓치기 쉽다

### 내 추천

대부분의 팀에는 **실서비스 컴포넌트를 재사용하되, preview 진입 경계와 데이터 계층만 분리하는 절충안**이 가장 좋다.

즉 이렇게 가져가는 편이 안정적이다.

- UI 트리: 최대한 동일
- 데이터 소스: published/draft 분리
- cache policy: preview는 보수적으로
- metadata/robots: preview 전용 정책 추가
- 진입/종료 route: 명시적으로 분리

이 방식이 편집 경험과 운영 안정성의 균형이 가장 좋다.

---

## 흔한 실수

### 1) `slug`를 querystring에서 받아 바로 redirect한다

가장 흔하고, 가장 피해야 할 실수다. preview 대상은 항상 CMS나 내부 저장소에서 재확인해야 한다.

### 2) preview와 published가 같은 캐시 태그를 공유한다

예를 들어 `post:123` 같은 태그 하나로 draft/published를 모두 묶으면 무효화 시점에 경계가 흐려진다. 최소한 published 전용 태그와 preview 조회 경로를 구분하는 편이 낫다.

### 3) 본문만 preview이고 metadata는 published다

검수 단계에서 오히려 SEO 사고를 키우는 패턴이다. `generateMetadata()`도 같은 소스를 바라보게 해야 한다.

### 4) preview 페이지에 noindex를 안 건다

검색엔진 노출은 생각보다 우발적으로 생긴다. robots 정책은 기본값으로 넣는 편이 안전하다.

### 5) preview 종료 경로가 없다

편집자와 QA가 스스로 상태를 제어할 수 있어야 한다. disable 경로가 없으면 디버깅 비용이 급격히 커진다.

### 6) locale/tenant 문맥을 preview 경로에서 잃어버린다

`/ko/blog/foo`와 `/en/blog/foo`가 모두 존재하는 서비스에서 locale을 querystring에만 맡기면 쉽게 꼬인다. preview target resolve 단계에서 canonical locale path를 재계산해야 한다.

### 7) preview를 보안 기능 없이 "링크만 알면 되는 모드"로 둔다

특히 B2B, 법무, 채용, 가격 정책, 미공개 릴리스 노트처럼 초안 노출 비용이 큰 서비스에서는 위험하다. secret 관리, 접근 제어, 만료 정책을 반드시 고려해야 한다.

---

## 체크리스트

배포 전에 아래 항목을 확인하면 Draft Mode 관련 사고를 많이 줄일 수 있다.

- [ ] preview Route Handler가 secret을 검증한다
- [ ] `slug`를 그대로 redirect하지 않고 CMS/내부 저장소에서 재확인한다
- [ ] preview 대상이 없으면 Draft Mode를 켜지 않고 실패한다
- [ ] preview와 published가 서로 다른 데이터 선택 로직을 가진다
- [ ] preview 응답이 공용 캐시를 오염시키지 않는다
- [ ] metadata와 본문이 같은 preview/published 소스를 읽는다
- [ ] preview 상태에서 `robots: noindex, nofollow` 정책이 적용된다
- [ ] preview 배너와 종료 링크가 있다
- [ ] disable route가 외부 redirect를 허용하지 않는다
- [ ] locale/tenant별 canonical path 재계산이 된다
- [ ] 저장 직후 최신본이 보이는지 실제 CMS 편집 흐름에서 검증했다
- [ ] 발행 후 preview를 끈 상태에서 published 화면과 다시 비교 검증했다

---

## 한 줄 정리

> **Next.js Draft Mode의 핵심은 초안을 보여주는 기능 자체가 아니라, preview 요청만 안전하게 동적으로 분기하고 published 세계와 draft 세계를 캐시·보안·SEO 차원에서 끝까지 분리하는 운영 설계다.**
