---
layout: post
title: "Next.js Middleware 실전: 인증 게이트, A/B 테스트, 지역화 구현"
date: 2026-03-19 14:00:00 +0900
categories: [nextjs]
tags: [study, nextjs, middleware, auth, ab-test, i18n, edge]
---

## Middleware란

`middleware.ts`는 요청이 페이지나 API에 도달하기 **전에** Edge Runtime에서 실행되는 코드다. 응답을 가로채 리다이렉트, 헤더 추가, 쿠키 설정, 경로 재작성을 할 수 있다.

```
요청 → Middleware (Edge) → 캐시 확인 → Server Component/API Route → 응답
```

주요 특성:
- **Edge Runtime** 실행 (Node.js API 일부 사용 불가)
- 모든 경로에 대해 실행 (매처로 범위 제한 가능)
- 응답 전 처리이므로 레이턴시가 극히 낮아야 함

## 기본 구조

```ts
// middleware.ts (프로젝트 루트)
import { NextRequest, NextResponse } from "next/server";

export function middleware(request: NextRequest) {
  // 요청 정보: request.nextUrl, request.cookies, request.headers
  return NextResponse.next(); // 통과
}

export const config = {
  // 적용할 경로 패턴 (없으면 모든 경로)
  matcher: ["/dashboard/:path*", "/api/:path*"],
};
```

## 활용 1: 인증 게이트

JWT를 쿠키에서 읽어 미인증 사용자를 로그인 페이지로 보낸다.

```ts
import { NextRequest, NextResponse } from "next/server";
import { jwtVerify } from "jose";

const PUBLIC_PATHS = ["/login", "/signup", "/api/auth"];

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // 공개 경로는 통과
  if (PUBLIC_PATHS.some((p) => pathname.startsWith(p))) {
    return NextResponse.next();
  }

  const token = request.cookies.get("session")?.value;

  if (!token) {
    const loginUrl = request.nextUrl.clone();
    loginUrl.pathname = "/login";
    loginUrl.searchParams.set("from", pathname); // 로그인 후 원래 경로로
    return NextResponse.redirect(loginUrl);
  }

  try {
    const secret = new TextEncoder().encode(process.env.JWT_SECRET!);
    await jwtVerify(token, secret);
    return NextResponse.next();
  } catch {
    // 토큰 만료/위조
    const response = NextResponse.redirect(new URL("/login", request.url));
    response.cookies.delete("session");
    return response;
  }
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
```

**jose** 라이브러리를 쓰는 이유: Edge Runtime은 `jsonwebtoken` 같은 Node.js 전용 라이브러리를 지원하지 않는다. `jose`는 Web Crypto API 기반이라 Edge에서도 동작한다.

## 활용 2: A/B 테스트

새 랜딩 페이지를 50% 사용자에게만 노출한다. 쿠키로 버킷을 고정해 같은 사용자가 매번 같은 버전을 보게 한다.

```ts
import { NextRequest, NextResponse } from "next/server";

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (pathname !== "/landing") return NextResponse.next();

  // 기존 버킷 쿠키 확인
  const bucket = request.cookies.get("ab_landing")?.value;

  if (bucket === "new") {
    return NextResponse.rewrite(new URL("/landing-v2", request.url));
  }

  if (bucket === "control") {
    return NextResponse.next();
  }

  // 첫 방문: 랜덤 배정
  const isNew = Math.random() < 0.5;
  const response = isNew
    ? NextResponse.rewrite(new URL("/landing-v2", request.url))
    : NextResponse.next();

  response.cookies.set("ab_landing", isNew ? "new" : "control", {
    maxAge: 60 * 60 * 24 * 30, // 30일 고정
    httpOnly: true,
  });

  return response;
}
```

`rewrite`는 URL은 그대로 두고 내부적으로 다른 페이지를 렌더링한다. 사용자 주소창은 `/landing`으로 유지된다.

## 활용 3: 지역화(i18n) 리다이렉트

Accept-Language 헤더를 읽어 자동으로 언어별 경로로 보낸다.

```ts
import { NextRequest, NextResponse } from "next/server";

const LOCALES = ["ko", "en", "ja"];
const DEFAULT_LOCALE = "ko";

function getLocale(request: NextRequest): string {
  const acceptLang = request.headers.get("accept-language") ?? "";
  const preferred = acceptLang.split(",")[0].split("-")[0].toLowerCase();
  return LOCALES.includes(preferred) ? preferred : DEFAULT_LOCALE;
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // 이미 로케일 접두사가 있으면 통과
  const hasLocale = LOCALES.some(
    (l) => pathname.startsWith(`/${l}/`) || pathname === `/${l}`
  );

  if (hasLocale) return NextResponse.next();

  // 정적 파일 제외
  if (pathname.startsWith("/_next") || pathname.includes(".")) {
    return NextResponse.next();
  }

  const locale = getLocale(request);
  const url = request.nextUrl.clone();
  url.pathname = `/${locale}${pathname}`;
  return NextResponse.redirect(url);
}
```

## 헤더 주입 패턴

하위 컴포넌트에서 읽어야 하는 값(요청 경로, 사용자 역할 등)을 헤더로 전달할 수 있다.

```ts
export function middleware(request: NextRequest) {
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-pathname", request.nextUrl.pathname);

  return NextResponse.next({ request: { headers: requestHeaders } });
}
```

Server Component에서 읽기:

```ts
import { headers } from "next/headers";

export default function Layout() {
  const pathname = headers().get("x-pathname");
  // ...
}
```

## 주의사항 요약

| 항목 | 내용 |
|---|---|
| DB 직접 쿼리 | 불가 (Edge Runtime 제한) |
| 무거운 연산 | 금지 (모든 요청에 영향) |
| 쿠키 암호화 | 민감 정보는 반드시 서명/암호화 |
| matcher 설정 | 정적 파일 (`_next/static`) 제외 필수 |
| 디버깅 | `console.log`는 터미널에 출력됨 |

## 오늘의 적용 체크리스트

- [ ] 보호가 필요한 경로에 Middleware 인증 게이트 추가
- [ ] A/B 테스트 대상 페이지 식별 및 버킷 쿠키 설계
- [ ] i18n 필요 시 로케일 감지 로직 `middleware.ts`로 통합
- [ ] `matcher` 설정으로 불필요한 경로 실행 제외
- [ ] Edge 환경 호환 라이브러리(`jose`, `@auth/edge`) 로 교체
