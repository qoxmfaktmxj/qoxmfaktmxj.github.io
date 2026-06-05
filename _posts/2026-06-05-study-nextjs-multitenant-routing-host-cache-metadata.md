---
layout: post
title: "Next.js 멀티테넌트 라우팅 실전: Host Header, Middleware, Cache Key, Metadata로 테넌트 경계를 안전하게 설계하는 법"
date: 2026-06-05 11:50:00 +0900
categories: [nextjs]
tags: [study, nextjs, multi-tenant, host-header, middleware, cache, metadata, routing, app-router, security, operations]
permalink: /nextjs/2026/06/05/study-nextjs-multitenant-routing-host-cache-metadata.html
---

## 배경: 멀티테넌트 Next.js는 URL만 나누면 끝나는 문제가 아니다

SaaS를 만들다 보면 어느 순간 "고객사별 화면"을 제공해야 한다. 처음에는 단순해 보인다.

- `acme.example.com`은 ACME 고객사 화면이다.
- `globex.example.com`은 Globex 고객사 화면이다.
- `/acme/dashboard`처럼 path prefix로 나눌 수도 있다.
- 고객사별 로고, 색상, 도메인, SEO metadata만 다르게 보여주면 된다.

하지만 운영 단계로 가면 이 문제는 단순 라우팅이 아니라 **테넌트 경계 설계**가 된다. 특히 Next.js App Router에서는 Server Components, Route Handlers, Middleware, 캐시, metadata, static generation, image optimization, CDN이 한 요청 안에서 섞인다. 이 조합을 가볍게 보면 다음과 같은 사고가 생긴다.

- A 고객사의 대시보드 HTML이 캐시에 저장되어 B 고객사에게 노출된다.
- middleware에서는 `Host`를 보고 tenant를 찾았지만, 서버 컴포넌트의 데이터 fetch 캐시는 tenant와 무관한 key로 재사용된다.
- `generateMetadata()`가 tenant별 title을 만들지만 canonical URL은 기본 도메인으로 고정되어 검색 색인이 꼬인다.
- preview 또는 admin route가 tenant context 없이 동작해 잘못된 고객사 콘텐츠를 수정한다.
- route handler의 webhook 검증은 통과했지만 path tenant와 payload tenant가 달라 다른 tenant 데이터가 갱신된다.
- `x-forwarded-host`를 무조건 신뢰했다가 프록시 밖에서 위조된 host를 받아 tenant spoofing이 가능해진다.
- wildcard domain을 연결했는데 DNS, TLS, middleware matcher, cookie domain 정책이 서로 다른 기준으로 동작한다.
- 개발 환경에서는 `localhost:3000/acme`로 잘 됐지만 배포 환경에서는 `acme.example.com`과 `www.example.com`이 캐시와 쿠키를 공유한다.

멀티테넌트 라우팅에서 가장 위험한 착각은 "URL에서 tenant slug만 파싱하면 된다"는 생각이다. 실제로는 tenant slug를 얻는 것보다 그 slug가 **어디까지 신뢰 가능한지**, **어떤 캐시 경계에 포함되는지**, **어떤 권한·데이터·메타데이터·쿠키 정책과 결합되는지**가 훨씬 중요하다.

이 글은 중급 이상 Next.js 개발자를 기준으로 멀티테넌트 라우팅을 실무 운영 관점에서 정리한다. 단순히 `middleware.ts`에서 rewrite하는 예제가 아니라, 다음 질문에 답하는 것을 목표로 한다.

1. subdomain 방식과 path prefix 방식은 어떤 라우팅·캐시·쿠키 트레이드오프를 가지는가?
2. `Host`, `x-forwarded-host`, `x-forwarded-proto`는 어디까지 믿을 수 있는가?
3. middleware에서 tenant를 판별한 뒤 App Router 내부로 어떻게 전달해야 일관성이 유지되는가?
4. Next.js 캐시가 tenant 데이터를 섞지 않게 하려면 cache key와 revalidation tag를 어떻게 설계해야 하는가?
5. `generateMetadata()`, canonical, Open Graph, sitemap은 tenant별로 어떻게 분리해야 하는가?
6. route handler, webhook, server action은 URL tenant와 인증 tenant를 어떻게 검증해야 하는가?
7. 운영에서 어떤 로그와 테스트가 있어야 tenant leakage를 빨리 발견할 수 있는가?

핵심 결론부터 말하면 이렇다.

> 멀티테넌트 Next.js의 핵심은 "tenant slug를 라우팅에 넣는 것"이 아니라, **tenant identity를 신뢰 가능한 요청 컨텍스트로 확정하고, 데이터 fetch·캐시·metadata·권한·쿠키의 모든 경계에 같은 tenant key를 반복해서 반영하는 것**이다.

이 원칙을 놓치면 화면은 그럴듯하게 분리되어도, 캐시나 metadata나 webhook 같은 보이지 않는 경로에서 tenant 경계가 무너진다.

---

## 핵심개념 1: tenant slug와 tenant identity는 다르다

멀티테넌트 구현을 시작할 때 가장 먼저 구분해야 할 단어가 있다.

- `tenantSlug`: URL에 드러나는 문자열이다. 예를 들어 `acme`, `globex`다.
- `tenantDomain`: 고객사가 연결한 도메인이다. 예를 들어 `hr.acme.com`이다.
- `tenantId`: DB 안에서 tenant를 식별하는 안정적인 내부 ID다.
- `tenantContext`: 요청 처리 중 사용할 tenant 관련 정보 묶음이다.
- `principal`: 로그인한 사용자 또는 API client의 인증 주체다.

이 다섯 개를 하나로 뭉개면 코드가 짧아지는 대신 사고 가능성이 커진다. `acme.example.com`에서 `acme`를 파싱했다고 해서 그 문자열이 곧바로 DB의 tenant ID가 되어서는 안 된다. slug는 바뀔 수 있고, 재사용될 수 있으며, 대소문자·punycode·trailing dot·포트·preview domain 같은 정규화 문제가 있다. 더구나 custom domain을 쓰면 URL에는 slug가 아예 없을 수도 있다.

좋은 흐름은 보통 아래처럼 생긴다.

1. 요청의 host와 path를 정규화한다.
2. 정규화된 host/path에서 routing tenant hint를 추출한다.
3. 이 hint를 tenant registry에서 조회해 내부 `tenantId`로 확정한다.
4. 확정된 tenant가 활성 상태인지, 도메인이 검증되었는지 확인한다.
5. 로그인 사용자 또는 API client가 해당 tenant에 접근 가능한지 별도로 확인한다.
6. 이후 데이터 조회, 캐시 key, 로그, metadata에는 slug 대신 안정적인 `tenantId`를 우선 사용한다.

여기서 중요한 점은 **라우팅 tenant와 인증 tenant를 분리해서 검증한다**는 것이다. URL이 `acme.example.com`이라고 해서 로그인 사용자가 ACME 소속이라는 뜻은 아니다. 반대로 사용자가 ACME 소속이라고 해서 path의 tenant를 무시해도 된다는 뜻도 아니다. 두 값이 모두 있고, 둘이 일치해야 한다.

```ts
type TenantContext = {
  tenantId: string;
  slug: string;
  canonicalHost: string;
  matchedBy: "subdomain" | "custom-domain" | "path";
};

type Principal = {
  userId: string;
  tenantIds: string[];
  role: "owner" | "admin" | "member" | "viewer";
};

function assertTenantAccess(tenant: TenantContext, principal: Principal) {
  if (!principal.tenantIds.includes(tenant.tenantId)) {
    throw new Error("TENANT_ACCESS_DENIED");
  }
}
```

이 코드는 일부러 단순하다. 핵심은 tenant를 URL 문자열로만 보지 않는 것이다. URL은 tenant를 찾기 위한 단서이고, tenant identity는 registry와 권한 검증을 거쳐 확정되는 내부 계약이어야 한다.

---

## 핵심개념 2: subdomain 방식과 path prefix 방식은 운영 비용이 다르다

멀티테넌트 라우팅은 크게 두 방식으로 나뉜다.

```text
Subdomain 방식
https://acme.example.com/dashboard
https://globex.example.com/dashboard

Path prefix 방식
https://example.com/acme/dashboard
https://example.com/globex/dashboard
```

두 방식 모두 가능하지만 운영 특성이 다르다.

Subdomain 방식은 고객사별 브랜드 경험이 좋다. cookie domain, canonical URL, Open Graph, custom domain 확장도 자연스럽다. 대신 wildcard DNS, TLS 인증서, host 기반 routing, preview deployment, local development 설정이 더 복잡하다. CDN과 애플리케이션이 `Host`를 같은 방식으로 이해해야 하며, `www`, apex domain, admin domain을 명확히 제외해야 한다.

Path prefix 방식은 시작하기 쉽다. `app/[tenant]/dashboard/page.tsx`처럼 App Router 구조와 잘 맞고, local development도 편하다. 하지만 쿠키와 캐시가 같은 host 안에서 공유되므로 tenant 경계가 URL path와 데이터 fetch key에 더 강하게 의존한다. SEO 관점에서도 canonical과 sitemap을 세심하게 설계해야 한다. 고객사가 custom domain을 원하면 결국 host 기반 로직을 추가해야 할 수 있다.

실무에서는 아래 기준으로 결정하는 편이 안전하다.

| 기준 | subdomain | path prefix |
| --- | --- | --- |
| 고객사별 브랜딩 | 강함 | 보통 |
| 초기 구현 난이도 | 높음 | 낮음 |
| wildcard DNS/TLS 필요 | 필요 | 불필요 |
| cookie 분리 | 쉬움 | 신중한 설계 필요 |
| custom domain 확장 | 자연스러움 | 별도 설계 필요 |
| App Router 파일 구조 | rewrite가 필요할 수 있음 | 동적 segment와 잘 맞음 |
| CDN cache key | host 포함 여부 확인 필요 | path 포함으로 비교적 명확 |
| SEO canonical | host별 분리 쉬움 | prefix 정합성 필요 |

중요한 것은 어떤 방식을 고르든 **tenant resolution의 단일 진입점**을 두는 것이다. subdomain은 middleware에서, path prefix는 page에서, route handler는 또 다른 방식으로 tenant를 해석하면 시간이 지나며 기준이 갈라진다.

권장 구조는 다음과 같다.

- `resolveTenantFromRequest(request)`를 하나 만든다.
- middleware, server component helper, route handler가 같은 규칙을 공유한다.
- host/path 정규화 규칙과 reserved slug 목록을 한곳에서 관리한다.
- tenant registry 조회 결과를 내부 `tenantId`로 바꾼다.
- 이후에는 `tenantId`를 모든 데이터 접근 함수의 필수 인자로 둔다.

이렇게 하면 라우팅 방식이 바뀌어도 데이터 계층과 권한 계층은 크게 흔들리지 않는다.

---

## 핵심개념 3: Host Header는 필요하지만 무조건 신뢰하면 안 된다

subdomain이나 custom domain을 쓰면 `Host` header가 tenant 판별의 출발점이 된다. 하지만 `Host`는 네트워크 경계에서 다뤄야 하는 입력값이다. 특히 애플리케이션이 직접 인터넷에 노출되는지, CDN이나 reverse proxy 뒤에 있는지에 따라 신뢰 기준이 달라진다.

문제는 보통 아래에서 시작된다.

```ts
const host = request.headers.get("x-forwarded-host")
  ?? request.headers.get("host");
```

이 코드는 흔히 보이지만 그대로 두면 위험하다. `x-forwarded-host`는 원래 proxy가 원본 host를 전달하기 위해 넣는 header다. 그런데 애플리케이션이 이 header를 어떤 proxy에서 받았는지 검증하지 않으면, 외부 사용자가 직접 조작한 값을 믿을 수도 있다.

운영 기준은 다음처럼 잡는 편이 좋다.

- 애플리케이션 앞단에 신뢰 가능한 CDN/proxy가 있는지 명확히 한다.
- 플랫폼이 제공하는 host header 규칙을 문서로 확인한다.
- `x-forwarded-host`를 쓸 때는 trusted proxy 경계에서만 사용한다.
- host는 lowercase, port 제거, trailing dot 제거, punycode 처리 등 정규화한다.
- 허용된 base domain, custom domain registry에 없는 host는 404 또는 기본 landing으로 보낸다.
- `localhost`, preview domain, admin domain, static asset domain은 tenant 후보에서 제외한다.

예시는 다음과 같다.

```ts
const RESERVED_SUBDOMAINS = new Set(["www", "admin", "api", "static"]);

function normalizeHost(rawHost: string | null): string | null {
  if (!rawHost) return null;

  const withoutPort = rawHost.split(":")[0]?.trim().toLowerCase();
  if (!withoutPort) return null;

  return withoutPort.endsWith(".")
    ? withoutPort.slice(0, -1)
    : withoutPort;
}

function extractSubdomainTenant(host: string, baseDomain: string) {
  if (!host.endsWith(`.${baseDomain}`)) return null;

  const subdomain = host.slice(0, -1 * (`.${baseDomain}`.length));
  if (!subdomain || RESERVED_SUBDOMAINS.has(subdomain)) return null;

  return subdomain;
}
```

이 정도 코드가 전부는 아니다. custom domain, wildcard domain, preview deployment, apex domain까지 고려하면 더 많은 분기가 필요하다. 하지만 방향은 같다. host는 tenant를 찾는 입력값이지, 검증 없이 신뢰할 내부 권한 값이 아니다.

특히 `Host`를 기반으로 redirect URL을 만들 때는 더 조심해야 한다.

```ts
// 위험한 패턴
return NextResponse.redirect(`https://${request.headers.get("host")}/login`);
```

host가 위조되면 open redirect나 phishing 표면이 될 수 있다. redirect destination은 tenant registry에 등록된 canonical host나 서비스가 관리하는 base URL에서 조립해야 한다.

---

## 핵심개념 4: Middleware는 tenant를 찾는 데 좋지만 모든 것을 해결하지 않는다

Next.js middleware는 요청 초기에 실행되므로 tenant routing에 자연스럽게 어울린다. host를 읽고, path를 rewrite하고, header를 붙이고, 인증이 필요한 경로를 gate할 수 있다.

예를 들어 subdomain을 path segment로 rewrite할 수 있다.

```ts
import { NextRequest, NextResponse } from "next/server";

export async function middleware(request: NextRequest) {
  const tenant = await resolveTenantFromRequest(request);

  if (!tenant) {
    return NextResponse.next();
  }

  const url = request.nextUrl.clone();

  if (!url.pathname.startsWith(`/_sites/${tenant.slug}`)) {
    url.pathname = `/_sites/${tenant.slug}${url.pathname}`;
  }

  const response = NextResponse.rewrite(url);
  response.headers.set("x-tenant-id", tenant.tenantId);
  response.headers.set("x-tenant-slug", tenant.slug);

  return response;
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|robots.txt|sitemap.xml).*)",
  ],
};
```

이 패턴은 유용하다. 하지만 middleware를 tenant 설계의 전부로 보면 곤란하다. 이유는 세 가지다.

첫째, middleware에서 붙인 header를 애플리케이션 내부에서 다시 읽을 때 신뢰 경계가 모호해질 수 있다. 외부 요청도 같은 header 이름을 보낼 수 있기 때문이다. middleware가 내부 header를 덮어쓰더라도, route handler나 server component가 middleware를 거치지 않는 경로로 실행되는 경우까지 생각해야 한다.

둘째, middleware에서 DB를 매 요청마다 조회하면 latency와 장애 반경이 커진다. tenant registry는 비교적 작은 데이터지만, edge runtime 제약과 DB client 제약을 함께 고려해야 한다. tenant lookup을 edge에서 할지, Node runtime에서 할지, CDN cache 또는 signed metadata를 둘지 결정해야 한다.

셋째, middleware rewrite는 URL 구조를 바꿔도 데이터 fetch cache key를 자동으로 안전하게 만들어주지 않는다. 페이지 경로가 tenant별로 분리되어도 서버 컴포넌트 안의 `fetch("https://api.example.com/settings")`가 tenant를 포함하지 않으면 같은 응답이 재사용될 수 있다.

따라서 middleware의 역할은 이렇게 제한하는 편이 좋다.

- 요청에서 tenant hint를 찾는다.
- 명백히 잘못된 host/path를 early reject한다.
- 필요한 경우 내부 route로 rewrite한다.
- tenant context를 downstream이 확인할 수 있게 전달한다.
- 하지만 최종 권한 검증과 데이터 접근 제한은 서버 계층에서 다시 수행한다.

middleware는 gatekeeper이지, 데이터 보안의 최종 방어선이 아니다.

---

## 핵심개념 5: 캐시 key에 tenant가 빠지면 화면이 분리되어도 데이터가 섞인다

Next.js App Router의 장점 중 하나는 서버 렌더링과 캐시를 적극적으로 사용할 수 있다는 점이다. 하지만 멀티테넌트에서는 이 장점이 위험해질 수 있다. 캐시는 "같은 요청이면 같은 응답을 재사용한다"는 전제 위에서 동작한다. 문제는 개발자가 생각하는 "같은 요청"과 실제 cache key가 다를 수 있다는 것이다.

아래 코드를 보자.

```ts
export async function getTenantTheme() {
  const response = await fetch("https://api.example.com/theme", {
    next: { revalidate: 3600 },
  });

  return response.json();
}
```

이 함수는 tenant별 테마를 가져오는 것처럼 보일 수 있다. 하지만 URL이 tenant를 포함하지 않고, header도 cache key에 기대한 방식으로 반영되지 않으면 문제가 생긴다. ACME 요청에서 받은 theme가 Globex 요청에 재사용될 수 있다.

안전한 방향은 tenant identity를 데이터 접근 함수의 인자로 강제하고, fetch URL 또는 cache key에 명시적으로 포함하는 것이다.

```ts
export async function getTenantTheme(tenantId: string) {
  const response = await fetch(
    `https://api.example.com/tenants/${tenantId}/theme`,
    {
      next: {
        revalidate: 3600,
        tags: [`tenant:${tenantId}:theme`],
      },
    }
  );

  if (!response.ok) {
    throw new Error("TENANT_THEME_FETCH_FAILED");
  }

  return response.json();
}
```

DB를 직접 조회하고 `unstable_cache` 같은 함수를 쓴다면 cache key를 더 노골적으로 관리해야 한다.

```ts
import { unstable_cache } from "next/cache";

export function getCachedTenantSettings(tenantId: string) {
  return unstable_cache(
    async () => {
      return db.tenantSettings.findUniqueOrThrow({
        where: { tenantId },
      });
    },
    ["tenant-settings", tenantId],
    {
      tags: [`tenant:${tenantId}:settings`],
      revalidate: 300,
    }
  )();
}
```

여기서 볼 지점은 두 가지다.

1. cache key 배열에 `tenantId`가 들어간다.
2. revalidation tag에도 `tenantId`가 들어간다.

tag를 `tenant-settings`처럼 전역으로 두면 한 tenant의 설정 변경이 모든 tenant의 cache를 무효화한다. 반대로 tag에 tenant를 넣지 않고 key에만 tenant를 넣으면 특정 tenant만 재검증하기 어렵다. 실무에서는 보통 아래처럼 계층형 tag를 둔다.

```text
tenant:{tenantId}
tenant:{tenantId}:settings
tenant:{tenantId}:theme
tenant:{tenantId}:navigation
tenant:{tenantId}:page:{pageId}
```

이렇게 하면 전체 tenant 변경, 설정 변경, 특정 페이지 변경을 구분해서 revalidate할 수 있다.

캐시 정책에서 자주 쓰는 기준은 다음과 같다.

- tenant별로 달라지는 데이터는 반드시 `tenantId`를 key나 URL에 넣는다.
- 로그인 사용자별 데이터는 public cache가 아니라 request-scoped 또는 no-store로 둔다.
- 권한에 따라 결과가 달라지는 조회는 `tenantId`뿐 아니라 role 또는 principal boundary도 고려한다.
- 전역 데이터와 tenant 데이터는 함수 이름부터 분리한다.
- revalidation tag는 운영자가 의도한 무효화 범위와 같은 계층으로 설계한다.

캐시는 성능 도구지만 멀티테넌트에서는 보안 경계이기도 하다. cache key에 tenant가 빠진다는 것은 WHERE 절에서 tenant 조건이 빠지는 것과 비슷한 위험이다.

---

## 실무예시 1: tenant context를 모든 데이터 접근 함수의 첫 번째 인자로 둔다

멀티테넌트 코드베이스에서 가장 효과적인 습관은 데이터 접근 함수의 시그니처를 강제하는 것이다.

나쁜 예시는 다음과 같다.

```ts
async function getProjects() {
  return db.project.findMany({
    orderBy: { updatedAt: "desc" },
  });
}
```

이 함수는 처음에는 특정 tenant 화면에서만 호출될 수 있다. 하지만 시간이 지나면 admin page, export job, server action, route handler에서 재사용된다. 그때 tenant 조건이 빠진 함수라는 사실을 놓치기 쉽다.

좋은 예시는 다음과 같다.

```ts
type RequestContext = {
  tenantId: string;
  principalId: string;
  role: "owner" | "admin" | "member" | "viewer";
  requestId: string;
};

async function getProjects(ctx: RequestContext) {
  return db.project.findMany({
    where: {
      tenantId: ctx.tenantId,
      archivedAt: null,
    },
    orderBy: { updatedAt: "desc" },
  });
}
```

이 방식의 장점은 단순하다.

- 함수 호출부에서 tenant가 보인다.
- 테스트에서 tenant 누락을 잡기 쉽다.
- 로그에 `requestId`, `tenantId`를 함께 넣기 쉽다.
- server action과 route handler가 같은 데이터 함수를 재사용할 수 있다.
- cache key 설계가 자연스럽게 따라온다.

더 엄격하게 하려면 tenant가 필요한 repository와 tenant가 필요 없는 repository를 패키지나 파일명으로 분리한다.

```text
lib/data/global/get-plan-catalog.ts
lib/data/tenant/get-projects.ts
lib/data/tenant/get-members.ts
lib/data/tenant/update-project.ts
```

전역 데이터는 정말 전역이어야 한다. 가격표, feature flag 정의, public marketing content 같은 것들이다. 반면 고객사 설정, 프로젝트, 멤버, 권한, 감사 로그, billing account는 tenant 데이터다. 이 둘이 같은 `lib/data` 폴더에 섞이면 리뷰에서 놓치기 쉽다.

실무 코드 리뷰에서는 다음 질문을 습관적으로 던지는 것이 좋다.

> 이 함수의 결과는 tenant에 따라 달라지는가? 그렇다면 `tenantId`가 함수 인자, WHERE 조건, cache key, revalidation tag에 모두 들어갔는가?

이 질문 하나만 반복해도 tenant leakage 가능성을 크게 줄일 수 있다.

---

## 실무예시 2: App Router 구조는 라우팅 방식과 내부 tenant boundary를 분리한다

Path prefix 방식을 쓴다면 파일 구조는 비교적 단순하다.

```text
app/
  [tenant]/
    dashboard/
      page.tsx
    settings/
      page.tsx
```

하지만 subdomain과 custom domain까지 지원하려면 외부 URL 구조와 내부 App Router 구조를 분리하는 편이 낫다.

```text
app/
  (marketing)/
    page.tsx
    pricing/
      page.tsx
  _sites/
    [tenant]/
      dashboard/
        page.tsx
      settings/
        page.tsx
  admin/
    tenants/
      page.tsx
```

middleware는 `acme.example.com/dashboard`를 내부적으로 `/_sites/acme/dashboard`로 rewrite한다. 사용자는 여전히 subdomain URL을 보지만, App Router는 tenant segment를 명확히 가진다.

```ts
export default async function DashboardPage({
  params,
}: {
  params: Promise<{ tenant: string }>;
}) {
  const { tenant: tenantSlug } = await params;
  const ctx = await requireTenantContext(tenantSlug);
  const projects = await getProjects(ctx);

  return <Dashboard projects={projects} />;
}
```

여기서 `requireTenantContext()`는 단순 slug parser가 아니다. 다음을 수행해야 한다.

- slug 또는 host로 tenant registry를 조회한다.
- tenant가 활성 상태인지 확인한다.
- 현재 인증 principal이 해당 tenant에 접근 가능한지 확인한다.
- request-scoped context를 만든다.
- 필요하면 audit log에 tenant resolution 결과를 남긴다.

이 구조의 장점은 외부 URL이 바뀌어도 내부 경로가 안정적이라는 점이다. 나중에 custom domain을 붙여도 결국 내부 route는 `/_sites/[tenant]`로 수렴한다. 반대로 내부 경로와 외부 경로가 완전히 같아야 한다고 고집하면 subdomain, path prefix, custom domain을 동시에 지원할 때 분기와 예외가 늘어난다.

단, rewrite를 쓸 때는 metadata와 canonical URL에 주의해야 한다. 내부 경로 `/_sites/acme/dashboard`가 canonical로 노출되면 안 된다. metadata 생성은 반드시 tenant의 public URL을 기준으로 해야 한다.

---

## 실무예시 3: tenant별 Metadata와 canonical을 별도 책임으로 둔다

멀티테넌트 서비스에서 metadata는 장식이 아니다. 검색 엔진, 링크 미리보기, 공유 카드, 고객사 브랜딩, 중복 색인 방지와 연결된다.

예를 들어 ACME의 공개 채용 페이지가 있다고 하자.

```text
https://acme.example.com/jobs/backend-engineer
https://globex.example.com/jobs/backend-engineer
```

두 URL은 path가 같아도 완전히 다른 tenant의 콘텐츠일 수 있다. 이때 `generateMetadata()`가 tenant를 반영하지 않으면 title, description, Open Graph image, canonical이 잘못 나간다.

```ts
import type { Metadata } from "next";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ tenant: string; slug: string }>;
}): Promise<Metadata> {
  const { tenant: tenantSlug, slug } = await params;
  const ctx = await getPublicTenantContext(tenantSlug);
  const job = await getPublicJob(ctx.tenantId, slug);
  const canonical = `https://${ctx.canonicalHost}/jobs/${job.slug}`;

  return {
    title: `${job.title} | ${ctx.displayName}`,
    description: job.summary,
    alternates: {
      canonical,
    },
    openGraph: {
      title: `${job.title} | ${ctx.displayName}`,
      description: job.summary,
      url: canonical,
      siteName: ctx.displayName,
      images: [
        {
          url: `https://${ctx.canonicalHost}/api/og/jobs/${job.id}`,
          width: 1200,
          height: 630,
        },
      ],
    },
  };
}
```

중요한 것은 metadata도 데이터 접근이라는 점이다. tenant context 없이 metadata를 만들면 화면은 맞는데 검색 결과나 공유 카드가 틀릴 수 있다. 더 위험한 경우 비공개 tenant 이름이나 내부 slug가 Open Graph 이미지 URL에 노출될 수 있다.

운영에서는 metadata 관련 규칙을 명확히 두는 것이 좋다.

- canonical은 내부 rewrite path가 아니라 public URL로 만든다.
- custom domain이 검증된 tenant는 custom domain을 canonical로 쓸지 기본 subdomain을 쓸지 정책을 정한다.
- 비공개 tenant 페이지에는 `robots: { index: false }`를 명확히 둔다.
- sitemap은 tenant별 public content만 포함한다.
- Open Graph image route도 tenant 접근 정책을 따른다.
- metadata fetch에도 tenant별 cache key와 tag를 사용한다.

metadata는 사용자가 보는 화면 바깥에 있지만, 멀티테넌트에서는 외부 세계에 노출되는 또 하나의 데이터 표면이다.

---

## 실무예시 4: Server Action과 Route Handler는 URL tenant, form tenant, auth tenant를 서로 대조한다

멀티테넌트에서 쓰기 경로는 읽기 경로보다 더 엄격해야 한다. 특히 Server Action과 Route Handler는 사용하기 편한 만큼 tenant 검증이 흐려질 수 있다.

위험한 Server Action 예시는 다음과 같다.

```ts
"use server";

export async function updateProjectName(projectId: string, name: string) {
  const session = await auth();

  if (!session?.user) {
    throw new Error("UNAUTHORIZED");
  }

  await db.project.update({
    where: { id: projectId },
    data: { name },
  });
}
```

이 코드는 로그인 여부만 확인한다. `projectId`가 다른 tenant의 값이면 어떻게 되는가? DB의 id가 추측 불가능한 UUID라고 해도 그것은 보안 설계가 아니라 우연에 기대는 것이다.

더 안전한 패턴은 tenant context를 먼저 확정하고, update 조건에 tenant를 포함하는 것이다.

```ts
"use server";

export async function updateProjectName(
  tenantSlug: string,
  projectId: string,
  name: string
) {
  const ctx = await requireTenantContext(tenantSlug);

  const updated = await db.project.updateMany({
    where: {
      id: projectId,
      tenantId: ctx.tenantId,
    },
    data: { name },
  });

  if (updated.count !== 1) {
    throw new Error("PROJECT_NOT_FOUND_OR_FORBIDDEN");
  }

  revalidateTag(`tenant:${ctx.tenantId}:projects`);
}
```

`updateMany`를 쓰는 이유는 `where`에 tenant 조건을 함께 넣기 쉽기 때문이다. ORM에 따라 composite unique key를 만들어 `where: { tenantId_id: { tenantId, id } }`처럼 처리할 수도 있다. 핵심은 쓰기 조건에 tenant가 들어가야 한다는 점이다.

Webhook도 마찬가지다. 예를 들어 route가 `/api/tenants/[tenant]/webhooks/billing`이고 payload에도 `tenantId`가 있다면 둘을 비교해야 한다.

```ts
export async function POST(
  request: Request,
  { params }: { params: Promise<{ tenant: string }> }
) {
  const { tenant } = await params;
  const ctx = await requireWebhookTenantContext(tenant, request);
  const payload = await verifyBillingWebhook(request);

  if (payload.tenantId !== ctx.tenantId) {
    return new Response("tenant mismatch", { status: 400 });
  }

  await applyBillingEvent(ctx, payload);
  return new Response("ok");
}
```

URL tenant, payload tenant, 인증 tenant가 모두 같은 방향을 가리켜야 한다. 하나라도 빠지면 운영 중에 "정상적으로 성공한 잘못된 쓰기"가 생긴다.

---

## 트레이드오프 1: Edge에서 tenant를 찾을 것인가, Node에서 찾을 것인가

Next.js middleware는 edge runtime에서 실행되는 경우가 많다. edge에서 tenant를 빠르게 판별하면 사용자와 가까운 위치에서 routing을 결정할 수 있다. 하지만 모든 tenant resolution을 edge에 밀어 넣는 것이 항상 좋은 것은 아니다.

Edge tenant resolution의 장점은 다음과 같다.

- 잘못된 host를 빠르게 reject할 수 있다.
- subdomain을 내부 route로 rewrite하기 쉽다.
- static asset이나 public page 요청을 early routing할 수 있다.
- 일부 플랫폼에서는 CDN cache와 궁합이 좋다.

단점도 있다.

- 일반적인 DB client를 쓰기 어렵거나 비효율적일 수 있다.
- tenant registry 변경 반영 지연을 고려해야 한다.
- 복잡한 권한 검증을 넣으면 middleware가 무거워진다.
- edge와 node가 서로 다른 tenant resolution 규칙을 갖게 될 위험이 있다.

Node tenant resolution은 반대로 느릴 수 있지만 DB 접근과 인증 검증이 자연스럽다. 그래서 실무에서는 둘을 나누는 방식이 자주 쓰인다.

- Edge middleware: host/path 정규화, reserved domain reject, rewrite, 가벼운 tenant hint 전달
- Node server layer: tenant registry 최종 조회, session 검증, role 검증, 데이터 접근

tenant registry가 크지 않다면 edge에서 읽을 수 있는 별도 manifest를 둘 수도 있다.

```json
{
  "acme.example.com": {
    "tenantId": "ten_123",
    "slug": "acme",
    "canonicalHost": "acme.example.com"
  },
  "hr.globex.com": {
    "tenantId": "ten_456",
    "slug": "globex",
    "canonicalHost": "hr.globex.com"
  }
}
```

하지만 이 manifest는 권한 검증이 아니라 routing hint로만 써야 한다. 최종 데이터 접근 전에는 서버 계층에서 tenant 상태와 principal 권한을 다시 확인해야 한다.

---

## 트레이드오프 2: 정적 생성과 tenant별 개인화는 서로 긴장 관계에 있다

Next.js는 정적 생성과 캐시를 잘 활용하면 빠르다. 공개 페이지가 많은 멀티테넌트 서비스라면 tenant별 landing page, 채용 공고, 문서, help center를 정적으로 만들고 싶을 수 있다. 하지만 tenant별 개인화와 권한 기반 UI가 섞이면 정적 생성은 위험해진다.

공개 콘텐츠는 정적 생성과 잘 맞는다.

- tenant 공개 프로필
- 공개 채용 공고
- 공개 문서
- 공개 가격 안내
- tenant별 브랜드 asset

반대로 아래는 정적 생성과 맞지 않는다.

- 로그인 사용자 권한에 따라 달라지는 navigation
- 사용자별 dashboard
- tenant 멤버 목록
- 결제 정보
- 관리자 설정
- feature flag에 따라 달라지는 민감한 기능 노출

문제는 한 페이지 안에 둘이 섞일 때다. 예를 들어 공개 채용 페이지는 정적 생성하고 싶지만, 로그인한 내부 관리자에게만 "편집" 버튼을 보여주고 싶을 수 있다. 이때 전체 페이지를 사용자별로 동적 렌더링하면 성능 장점이 줄고, 반대로 정적 페이지에 권한 UI를 섞으면 잘못 캐시될 수 있다.

실무에서는 페이지를 데이터 민감도 기준으로 나누는 편이 좋다.

- public tenant content는 tenant별 cache를 허용한다.
- authenticated tenant content는 request-scoped로 처리한다.
- admin-only controls는 별도 client island나 별도 route에서 가져온다.
- public page의 revalidation은 tenant content publish 이벤트와 연결한다.

즉 "페이지 단위로 static/dynamic을 결정"하기보다, **데이터 조각별로 cache boundary를 설계**해야 한다.

---

## 트레이드오프 3: 쿠키 도메인은 편의성과 격리 사이의 선택이다

subdomain 기반 멀티테넌트에서 로그인 쿠키를 어디에 둘지 결정해야 한다.

```text
Domain=.example.com
acme.example.com과 globex.example.com이 쿠키를 공유한다.

Host-only cookie
acme.example.com에서 발급된 쿠키는 acme.example.com에만 전송된다.
```

공유 쿠키는 SSO 경험이 좋다. 사용자가 여러 tenant에 접근할 때 다시 로그인하지 않아도 된다. 하지만 tenant별 세션 격리는 약해진다. 세션 안에 현재 tenant를 잘못 저장하면 subdomain 이동 시 꼬일 수 있고, CSRF나 origin 정책도 더 신중해야 한다.

Host-only cookie는 격리가 강하다. tenant별로 세션이 분리된다. 하지만 여러 tenant를 오가는 사용자는 로그인 경험이 불편할 수 있고, 중앙 admin domain과 tenant domain 사이의 인증 흐름을 별도로 설계해야 한다.

중요한 것은 쿠키가 tenant boundary를 대신하지 않는다는 점이다. 어떤 방식을 골라도 서버에서는 다음을 검증해야 한다.

- session의 principal이 존재하는가?
- 요청의 tenant context가 확정되었는가?
- principal이 그 tenant에 접근 가능한가?
- role이 해당 action을 수행할 수 있는가?
- CSRF 또는 origin 검증이 필요한 쓰기 요청인가?

쿠키 정책은 UX와 보안의 트레이드오프다. 하지만 tenant authorization은 항상 서버에서 명시적으로 수행해야 한다.

---

## 흔한실수 1: middleware rewrite만 믿고 데이터 함수에 tenant 조건을 넣지 않는다

가장 흔한 실수다. 외부 URL이 `acme.example.com/projects`이고 내부 route가 `/_sites/acme/projects`라서 tenant가 분리되었다고 느낀다. 하지만 실제 데이터 함수가 아래처럼 생겼다면 경계는 없다.

```ts
await db.project.findMany({
  where: { status: "ACTIVE" },
});
```

라우팅 분리는 화면을 고르는 일이고, 데이터 조건은 row를 고르는 일이다. 둘은 별개다. 모든 tenant 데이터 조회에는 tenant 조건이 들어가야 한다.

---

## 흔한실수 2: `headers()`에서 읽은 host로 canonical과 redirect를 만든다

요청 host를 그대로 canonical에 넣으면 preview domain, internal domain, 잘못된 host가 검색 엔진에 노출될 수 있다. redirect에 그대로 넣으면 open redirect 표면이 될 수도 있다.

canonical과 redirect는 tenant registry의 `canonicalHost` 또는 서비스 설정의 public base URL에서 만들어야 한다. 요청 header는 입력값이고, public URL은 검증된 출력값이어야 한다.

---

## 흔한실수 3: revalidateTag를 전역으로 호출한다

tenant 설정이 바뀔 때 `revalidateTag("settings")`를 호출하면 모든 tenant의 설정 캐시가 날아간다. 성능 문제만이 아니다. 어떤 코드가 tag를 잘못 공유하고 있다면 tenant 데이터가 섞일 가능성도 의심해야 한다.

tag는 의도한 무효화 범위를 표현해야 한다.

```ts
revalidateTag(`tenant:${tenantId}:settings`);
```

전역 tag는 정말 전역 데이터에만 써야 한다.

---

## 흔한실수 4: custom domain 검증 상태를 무시한다

고객사가 `hr.acme.com`을 연결하려면 보통 DNS 검증이 필요하다. 그런데 검증되지 않은 domain도 tenant registry에 들어가고, 애플리케이션이 이를 바로 신뢰하면 문제가 생긴다. 누군가 남의 domain을 등록하거나, DNS가 아직 전파되지 않았거나, 예전 tenant의 domain이 재사용되는 상황이 생길 수 있다.

custom domain에는 최소한 다음 상태가 필요하다.

- `pending`: 등록되었지만 검증되지 않음
- `verified`: DNS/TLS 검증 완료
- `disabled`: 운영자가 비활성화
- `conflict`: 다른 tenant 또는 예약 domain과 충돌

tenant resolution은 `verified` domain만 public host로 인정해야 한다.

---

## 흔한실수 5: metadata와 sitemap을 전역 기준으로 만든다

화면과 API는 tenant별로 잘 나뉘어 있는데 sitemap만 전역 쿼리로 모든 공개 페이지를 긁는 경우가 있다. 이때 비공개 tenant 페이지나 preview content가 노출될 수 있다.

sitemap 생성도 tenant-aware 데이터 접근 함수로 만들어야 한다. 공개 여부, canonical host, robots 정책, tenant 상태를 함께 봐야 한다. `generateMetadata()`도 같은 기준을 써야 한다.

---

## 흔한실수 6: 로그에 tenantId가 없다

장애가 났을 때 "어느 tenant에서 발생했는지" 모르면 멀티테넌트 운영은 급격히 어려워진다. 특히 캐시 leakage나 권한 오류는 request path만으로는 추적하기 어렵다.

모든 서버 로그에는 최소한 다음 필드를 남기는 것이 좋다.

- `requestId`
- `tenantId`
- `tenantSlug`
- `canonicalHost`
- `principalId`
- `route`
- `cacheTag` 또는 revalidation 대상
- `matchedBy`

물론 개인정보나 secret은 남기면 안 된다. 하지만 tenant context 자체는 운영 추적의 핵심이다.

---

## 운영 체크리스트: 멀티테넌트 Next.js를 배포하기 전 확인할 것

아래 체크리스트는 코드 리뷰와 배포 전 점검에 그대로 써도 좋다.

### 라우팅

- reserved subdomain 목록이 있는가?
- host 정규화 규칙이 한곳에 있는가?
- custom domain은 검증 완료 상태만 사용되는가?
- preview domain, localhost, admin domain이 tenant 후보에서 제외되는가?
- middleware matcher가 `_next/static`, `_next/image`, favicon, robots, sitemap을 의도대로 제외하거나 처리하는가?
- 외부 URL과 내부 rewrite path의 관계가 문서화되어 있는가?

### tenant context

- `resolveTenantFromRequest()` 또는 동등한 단일 진입점이 있는가?
- slug와 내부 `tenantId`가 분리되어 있는가?
- tenant 상태(active, suspended, deleted)를 확인하는가?
- routing tenant와 인증 principal의 tenant 권한을 대조하는가?
- route handler와 server action에서도 같은 tenant 검증을 사용하는가?

### 데이터 접근

- tenant 데이터 함수는 `tenantId` 또는 `RequestContext`를 필수 인자로 받는가?
- 모든 SELECT/UPDATE/DELETE 조건에 tenant가 포함되는가?
- composite unique key 또는 `updateMany`로 쓰기 경계를 강제하는가?
- admin 예외 경로는 별도 함수와 감사 로그를 가지는가?
- 테스트에서 다른 tenant 데이터가 조회되지 않는지 확인하는가?

### 캐시

- tenant별 fetch URL 또는 cache key에 `tenantId`가 들어가는가?
- `unstable_cache` key 배열에 tenant가 포함되는가?
- revalidation tag가 tenant 단위로 분리되는가?
- 사용자별/권한별 데이터는 public cache에서 제외되는가?
- 한 tenant의 설정 변경이 다른 tenant cache를 무효화하지 않는가?
- cache hit 로그나 trace에서 tenant key를 확인할 수 있는가?

### metadata와 SEO

- canonical은 내부 rewrite path가 아니라 public URL로 생성되는가?
- tenant별 title, description, Open Graph image가 분리되는가?
- 비공개 tenant는 `noindex` 처리되는가?
- sitemap은 공개 tenant와 공개 content만 포함하는가?
- custom domain과 기본 subdomain 중 canonical 우선순위가 정해져 있는가?

### 보안

- `Host`와 `x-forwarded-host` 신뢰 기준이 명확한가?
- redirect URL을 request host에서 직접 만들지 않는가?
- cookie domain 정책이 tenant 격리 모델과 일치하는가?
- CSRF 또는 origin 검증이 쓰기 요청에 적용되는가?
- URL tenant, form tenant, payload tenant, auth tenant를 대조하는가?
- webhook payload의 tenant와 route tenant가 일치하는가?

### 관측성

- 로그에 requestId와 tenantId가 포함되는가?
- tenant resolution 실패, 권한 실패, cache revalidation이 별도 이벤트로 남는가?
- 특정 tenant만 느린지 전체가 느린지 구분할 수 있는가?
- tenant별 오류율, latency, cache hit ratio를 볼 수 있는가?
- custom domain 검증 실패와 TLS 문제를 알림으로 받는가?

---

## 테스트 전략: tenant leakage는 happy path 테스트로 잡히지 않는다

멀티테넌트 테스트의 핵심은 "ACME가 ACME 데이터를 잘 보는가"가 아니다. 그건 기본 happy path다. 중요한 테스트는 "ACME 요청에서 Globex 데이터가 절대 보이지 않는가"다.

추천하는 테스트 구조는 다음과 같다.

1. 두 개 이상의 tenant fixture를 만든다.
2. 각 tenant에 같은 slug의 project, 같은 제목의 page, 같은 path의 public content를 만든다.
3. ACME principal로 Globex resource id에 접근한다.
4. subdomain, path prefix, route handler, server action을 모두 같은 기준으로 테스트한다.
5. 캐시를 한 번 warm-up한 뒤 다른 tenant 요청을 보내 섞이지 않는지 확인한다.
6. metadata와 sitemap도 tenant별로 검증한다.

예를 들어 통합 테스트는 이런 의도를 가져야 한다.

```ts
test("tenant cache does not leak project list across hosts", async () => {
  await seedTenant("acme", [{ name: "ACME Payroll" }]);
  await seedTenant("globex", [{ name: "Globex Payroll" }]);

  const acmeFirst = await requestWithHost("acme.example.test", "/projects");
  expect(acmeFirst.text).toContain("ACME Payroll");
  expect(acmeFirst.text).not.toContain("Globex Payroll");

  const globex = await requestWithHost("globex.example.test", "/projects");
  expect(globex.text).toContain("Globex Payroll");
  expect(globex.text).not.toContain("ACME Payroll");

  const acmeSecond = await requestWithHost("acme.example.test", "/projects");
  expect(acmeSecond.text).toContain("ACME Payroll");
  expect(acmeSecond.text).not.toContain("Globex Payroll");
});
```

여기서 중요한 포인트는 첫 번째 ACME 요청으로 캐시를 만든 뒤 Globex 요청을 한다는 점이다. 단순한 DB 조건 테스트로는 Next.js cache leakage를 놓칠 수 있다.

Server Action 테스트에서는 다른 tenant의 resource id를 의도적으로 넣어야 한다.

```ts
test("project update is scoped by tenant", async () => {
  const acme = await seedTenant("acme");
  const globex = await seedTenant("globex");
  const globexProject = await seedProject(globex.tenantId);

  await expect(
    updateProjectNameAs(acme.owner, acme.slug, globexProject.id, "Hacked")
  ).rejects.toThrow("PROJECT_NOT_FOUND_OR_FORBIDDEN");
});
```

멀티테넌트 테스트는 불편할수록 좋다. 실수로 tenant 조건을 빼면 테스트가 바로 깨져야 한다.

---

## 설계 패턴: tenant-aware service boundary를 만든다

규모가 커지면 page, server action, route handler 곳곳에서 직접 tenant 검증을 반복하기 어렵다. 이때는 tenant-aware service boundary를 두는 편이 좋다.

```ts
export async function createTenantService(tenantSlug: string) {
  const ctx = await requireTenantContext(tenantSlug);

  return {
    ctx,
    projects: {
      list: () => getProjects(ctx),
      rename: (projectId: string, name: string) =>
        renameProject(ctx, projectId, name),
    },
    members: {
      list: () => getMembers(ctx),
      invite: (email: string) => inviteMember(ctx, email),
    },
    settings: {
      get: () => getTenantSettings(ctx),
      updateTheme: (theme: ThemeInput) => updateTenantTheme(ctx, theme),
    },
  };
}
```

이 패턴의 목적은 멋진 추상화를 만드는 것이 아니다. tenant context 없이 tenant 데이터 함수가 호출되는 경로를 줄이는 것이다. page나 action은 먼저 tenant service를 만들고, 이후 작업은 그 service를 통해 수행한다.

단, 이 service가 너무 커지면 모든 책임이 한곳에 몰린다. 도메인별 service를 분리하되 공통 `RequestContext` 타입과 `requireTenantContext()`를 공유하는 정도가 현실적이다.

```text
lib/tenant/context.ts
lib/projects/project-service.ts
lib/members/member-service.ts
lib/settings/settings-service.ts
```

그리고 lint rule이나 코드 리뷰 규칙으로 `db.project` 직접 접근을 제한할 수도 있다. 모든 팀에 필요한 것은 아니지만, tenant leakage 리스크가 큰 B2B SaaS라면 충분히 가치가 있다.

---

## 운영 시나리오: 고객사가 custom domain을 바꾸는 날

멀티테넌트 라우팅 설계가 제대로 되었는지는 고객사가 도메인을 바꾸는 날 드러난다.

예를 들어 ACME가 기존 `acme.example.com` 대신 `people.acme.com`을 canonical로 쓰고 싶다고 하자. 좋은 설계라면 변경 흐름은 다음과 같다.

1. 운영자가 `people.acme.com`을 tenant domain registry에 `pending` 상태로 추가한다.
2. 시스템이 DNS 검증용 TXT 또는 CNAME 값을 제공한다.
3. 고객사가 DNS를 설정한다.
4. 검증 job이 domain을 `verified`로 바꾼다.
5. 운영자가 canonical host를 `people.acme.com`으로 변경한다.
6. metadata, sitemap, Open Graph URL이 새 canonical host를 사용한다.
7. 기존 `acme.example.com`은 301 redirect 또는 secondary domain으로 유지한다.
8. cache tag `tenant:ten_123:*`를 재검증한다.
9. 로그에서 host별 traffic 전환을 확인한다.

나쁜 설계라면 이 모든 변경이 코드 배포와 환경 변수 수정, sitemap 수동 생성, middleware 예외 추가로 흩어진다. 그러면 도메인 변경은 단순 설정 변경이 아니라 장애 유발 작업이 된다.

멀티테넌트에서 tenant registry는 단순 조회 테이블이 아니다. 라우팅, canonical, domain verification, tenant status, branding, cache invalidation의 기준점이다. 이 registry가 안정적이어야 Next.js 애플리케이션도 안정적으로 tenant를 다룰 수 있다.

---

## 마무리: 멀티테넌트 라우팅은 프론트엔드 라우팅이 아니라 제품 경계다

Next.js로 멀티테넌트 화면을 만드는 것은 어렵지 않아 보인다. `[tenant]` segment를 만들거나 middleware에서 subdomain을 rewrite하면 첫 화면은 금방 나온다. 하지만 실무 난이도는 그 다음부터 시작된다.

멀티테넌트에서 tenant는 단순 URL 파라미터가 아니다. 데이터 소유권, 권한, 캐시, metadata, 쿠키, 로그, 도메인 검증, SEO가 모두 tenant identity에 의존한다. 그래서 tenant를 "라우팅 파라미터"로만 다루면 어느 순간 보이지 않는 경로에서 사고가 난다.

좋은 설계는 반복적이다.

- 요청에서 tenant hint를 추출한다.
- registry에서 내부 tenant identity로 확정한다.
- principal 권한과 대조한다.
- 데이터 접근 조건에 tenant를 넣는다.
- cache key와 revalidation tag에 tenant를 넣는다.
- metadata와 canonical을 tenant public URL로 만든다.
- 로그와 테스트에서 tenant 경계를 계속 검증한다.

이 반복이 귀찮아 보일 수 있다. 하지만 멀티테넌트 SaaS에서 이 반복은 중복 코드가 아니라 안전장치다. 같은 tenant key가 라우팅, 데이터, 캐시, 권한, metadata에 계속 등장할 때 시스템은 예측 가능해진다.

## 한줄정리

Next.js 멀티테넌트 라우팅은 `Host`나 `[tenant]`를 파싱하는 기술이 아니라, 확정된 `tenantId`를 데이터 조건·캐시 key·metadata·권한 검증·로그에 끝까지 관통시키는 운영 설계다.
