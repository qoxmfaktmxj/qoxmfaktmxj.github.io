---
layout: post
title: "Next.js 인증·인가 아키텍처 실전: Middleware, Server Components, Session Rotation을 일관되게 설계하는 법"
date: 2026-04-18 11:40:00 +0900
categories: [nextjs]
tags: [study, nextjs, authentication, authorization, session, middleware, server-components, server-actions, route-handlers, security]
permalink: /nextjs/2026/04/18/study-nextjs-authentication-authorization-session-rotation.html
---

## 배경: Next.js에서 인증은 로그인 화면이 아니라 요청 경로 전체의 일관성 문제다

App Router로 서비스를 키우다 보면 인증은 금방 단순한 로그인 기능이 아니게 된다.

초기에는 대개 이렇게 시작한다.

- 로그인 성공 시 쿠키 저장
- `middleware.ts`에서 쿠키 있으면 통과, 없으면 `/login`으로 리다이렉트
- 클라이언트에서 `user.role === "admin"`이면 관리자 버튼 노출
- 데이터 수정은 Server Action이나 Route Handler에서 처리

작은 데모에서는 잘 돌아간다. 그런데 서비스가 커지면 곧 균열이 생긴다.

- Middleware에서는 통과했는데 실제 페이지에서 권한이 없어 500이 난다
- Server Component에서는 조직 멤버십을 체크했는데 Server Action에서는 같은 검증이 빠진다
- 권한 버튼만 숨겼을 뿐 API는 그대로 열려 있다
- JWT 만료와 세션 갱신 타이밍이 꼬여 사용자가 간헐적으로 로그아웃된다
- Edge Runtime에서 하던 검증 로직이 Node 전용 라이브러리 때문에 배포 환경마다 다르게 깨진다
- 멀티테넌트 서비스인데 `projectId`만 보고 수정해 다른 조직 데이터가 섞인다

이 문제의 핵심은 구현 기술이 아니라 **신뢰 경계를 어디에 두는지 불명확한 상태**다.

인증 아키텍처는 최소한 아래 질문에 일관되게 답해야 한다.

1. 사용자가 누구인지 어디서 확인할 것인가
2. 어떤 조직과 어떤 권한을 갖는지 어디서 확정할 것인가
3. 읽기 요청과 쓰기 요청에서 검증 책임을 어디에 둘 것인가
4. 세션 만료, 회수, 회전을 어떤 규칙으로 운영할 것인가
5. Edge, Server Component, Server Action, Route Handler가 각각 어디까지 믿을 수 있는가

이 글은 단순한 로그인 예제가 아니다. 목표는 다음 한 문장이다.

> **Next.js에서 인증(Authentication), 인가(Authorization), 세션(Session Lifecycle)을 각 실행 지점의 책임에 맞게 나눠서 운영 가능한 구조로 만드는 것**

중급 이상 개발자를 기준으로, 배경부터 실무 구조, 세션 회전, 트레이드오프, 흔한 실수, 체크리스트까지 한 번에 정리한다.

---

## 먼저 큰 그림: 인증, 인가, 세션은 같은 문제가 아니다

인증 아키텍처가 흔들리는 가장 큰 이유는 세 가지를 한 덩어리로 취급하기 때문이다.

### 1) Authentication, 당신이 누구인가

- 로그인 성공 여부
- 세션 쿠키나 토큰이 유효한가
- 사용자가 탈퇴, 정지, 잠금 상태는 아닌가

### 2) Authorization, 당신이 무엇을 해도 되는가

- 이 조직의 멤버인가
- 이 프로젝트를 읽을 수 있는가
- 이 액션을 실행할 역할이나 권한 스코프가 있는가
- 같은 관리자라도 `billing:write`, `member:invite`, `project:deploy` 범위가 다른가

### 3) Session Lifecycle, 그 신뢰를 얼마나 오래 유지할 것인가

- 세션 유효 기간은 얼마나 되는가
- 활동 중 자동 연장할 것인가
- 로그아웃이나 비밀번호 변경 시 어떻게 회수할 것인가
- 탈취된 쿠키를 재사용하지 못하게 회전할 것인가

이 셋을 분리해서 설계해야 하는 이유는 각 단계의 비용과 책임이 다르기 때문이다.

- **Authentication**은 대부분의 요청에서 필요하다
- **Authorization**은 리소스와 액션마다 다르다
- **Session Lifecycle**은 보안과 UX 사이 균형이다

실무에서는 보통 이렇게 정리하는 편이 가장 안정적이다.

- Middleware: 거친 1차 게이트, 공개/비공개 경로 구분
- Server Component: 읽기 요청 기준의 최종 사용자 문맥 확정
- Server Action/Route Handler: 쓰기 요청 기준의 최종 권한 검증
- 세션 저장소: 회수, 만료, 회전 규칙의 원천
- Client Component: 권한을 표현할 수는 있지만, 권한을 결정하지는 않음

이 구조가 잡히면 인증 버그의 대부분이 줄어든다.

---

## 핵심 개념 1: Middleware는 "최종 권한 판정기"가 아니라 "빠른 교통정리 레이어"다

`middleware.ts`를 처음 쓰면 모든 인증 로직을 여기 넣고 싶어진다. 하지만 그렇게 가면 곧 성능과 복잡도 둘 다 무너진다.

Middleware가 잘하는 일은 아래에 가깝다.

- 공개 경로와 보호 경로를 빠르게 나눈다
- 세션 쿠키 존재 여부나 서명 형태를 가볍게 확인한다
- 로그인 페이지, 대시보드, 설정 페이지 같은 큰 경로 그룹을 리다이렉트한다
- locale, A/B 테스트, 보안 헤더, 기본 사용자 힌트를 함께 정리한다

반대로 Middleware가 최종 책임을 지기 어려운 일도 분명하다.

- DB를 조회해 조직 멤버십과 세부 권한까지 매 요청 확인하는 일
- 복잡한 리소스별 인가 정책 계산
- 쓰기 요청의 부작용 이전 최종 승인
- 서비스 계정, 내부 API 토큰, 웹훅 서명처럼 별도 인증 체계가 필요한 경우

왜냐하면 Middleware는 **모든 요청의 입구**이기 때문이다. 여기서 무거운 검증을 하면 비용이 전체 트래픽에 곱해진다.

좋은 기준은 이렇다.

> Middleware는 "이 요청이 아예 사설 구역으로 들어갈 자격이 있는가"까지만 빠르게 판단하고, 실제 리소스 접근 권한은 서버 실행 지점에서 다시 확인한다.

예를 들어 `/app/:path*`는 로그인 사용자만 접근 가능하고, `/admin/:path*`는 관리자 후보만 진입시키되 실제 세부 권한은 서버에서 재확인하는 식이다.

```ts
// middleware.ts
import { NextRequest, NextResponse } from "next/server";

const PUBLIC_PATHS = ["/", "/login", "/signup", "/pricing"];

function isPublicPath(pathname: string) {
  return PUBLIC_PATHS.some((path) => pathname === path || pathname.startsWith(`${path}/`));
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (pathname.startsWith("/_next") || pathname.includes(".")) {
    return NextResponse.next();
  }

  if (isPublicPath(pathname)) {
    return NextResponse.next();
  }

  const session = request.cookies.get("session")?.value;

  if (!session) {
    const loginUrl = request.nextUrl.clone();
    loginUrl.pathname = "/login";
    loginUrl.searchParams.set("from", pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api/public|_next/static|_next/image|favicon.ico).*)"],
};
```

위 코드는 단순하다. 하지만 의도가 분명하다.

- 세션이 없으면 입구에서 차단
- 세션이 있다고 해서 권한까지 확정했다고 보지는 않음
- 실제 권한은 페이지, 액션, API에서 다시 확인

이 구조가 중요하다.

---

## 핵심 개념 2: Server Component는 "읽기 요청의 신뢰 원점"으로 두는 편이 안전하다

App Router에서는 페이지와 레이아웃이 Server Component로 동작한다. 이 지점은 읽기 흐름에서 사용자의 실제 문맥을 확정하기에 아주 좋다.

왜냐하면 여기서는 다음 작업을 자연스럽게 할 수 있기 때문이다.

- 쿠키를 읽는다
- 세션 저장소를 조회한다
- 현재 사용자와 조직 컨텍스트를 로드한다
- 권한이 없으면 `redirect()` 또는 `notFound()`로 종료한다
- 이후 하위 컴포넌트에 안전한 Viewer 객체만 전달한다

실무에서는 보통 `requireViewer`, `requireOrgMember`, `requirePermission` 같은 서버 유틸을 둔다.

```ts
// src/lib/auth/viewer.ts
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { db } from "@/lib/db";

export async function requireViewer() {
  const sessionId = (await cookies()).get("session")?.value;

  if (!sessionId) {
    redirect("/login");
  }

  const session = await db.session.findUnique({
    where: { id: sessionId },
    include: {
      user: true,
      memberships: {
        include: { organization: true },
      },
    },
  });

  if (!session || session.expiresAt < new Date()) {
    redirect("/login");
  }

  if (session.user.status !== "ACTIVE") {
    redirect("/suspended");
  }

  return {
    userId: session.userId,
    email: session.user.email,
    memberships: session.memberships,
  };
}
```

이 유틸의 장점은 단순 편의성이 아니다.

### 1) 읽기 요청마다 사용자 문맥이 일관된다

페이지마다 쿠키 파싱, 세션 조회, 사용자 상태 확인을 제각각 하지 않아도 된다.

### 2) 민감한 판단을 클라이언트로 내리지 않는다

클라이언트는 이미 서버가 승인한 결과만 본다.

### 3) 레이아웃 단계에서 권한 없는 사용자 흐름을 빨리 정리할 수 있다

예를 들어 조직 대시보드 전체를 감싸는 레이아웃에서 멤버십을 확인하면 하위 페이지마다 중복 코드를 줄일 수 있다.

```tsx
// app/(app)/[orgSlug]/layout.tsx
import { notFound } from "next/navigation";
import { requireViewer } from "@/lib/auth/viewer";
import { db } from "@/lib/db";

export default async function OrgLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ orgSlug: string }>;
}) {
  const viewer = await requireViewer();
  const { orgSlug } = await params;

  const membership = await db.membership.findFirst({
    where: {
      userId: viewer.userId,
      organization: { slug: orgSlug },
      status: "ACTIVE",
    },
    include: { organization: true },
  });

  if (!membership) {
    notFound();
  }

  return <>{children}</>;
}
```

여기서 중요한 점은 **읽기 권한을 레이아웃이나 페이지에서 실제 데이터 접근 직전 확인한다**는 것이다. Middleware를 통과했다고 끝난 게 아니다.

---

## 핵심 개념 3: Server Action과 Route Handler는 쓰기 요청의 최종 승인 지점이다

많은 팀이 여기서 한 번 크게 다친다.

- 페이지 진입은 멤버만 허용했다
- 버튼도 권한 있는 사용자에게만 보이게 했다
- 그런데 Server Action에서 실제 권한 확인이 없다

이 상태에서는 브라우저 콘솔, 스크립트, 재사용된 form action, 내부 링크 복사 등으로 우회 호출이 가능하다. UI 제어는 UX일 뿐, 보안 장치가 아니다.

Server Action과 Route Handler에서는 항상 다시 확인해야 한다.

1. 사용자 식별
2. 조직/테넌트 경계 확인
3. 리소스 소속 확인
4. 액션 단위 권한 확인
5. 쓰기 수행
6. 감사 로그와 캐시 무효화 처리

```ts
// app/(app)/[orgSlug]/projects/[projectId]/actions.ts
"use server";

import { revalidatePath } from "next/cache";
import { requireViewer } from "@/lib/auth/viewer";
import { db } from "@/lib/db";

export async function updateProjectName(input: {
  orgSlug: string;
  projectId: string;
  name: string;
}) {
  const viewer = await requireViewer();

  const membership = await db.membership.findFirst({
    where: {
      userId: viewer.userId,
      organization: { slug: input.orgSlug },
      status: "ACTIVE",
    },
  });

  if (!membership) {
    throw new Error("조직 접근 권한이 없습니다.");
  }

  const allowedRoles = ["OWNER", "ADMIN", "PROJECT_EDITOR"];

  if (!allowedRoles.includes(membership.role)) {
    throw new Error("프로젝트 수정 권한이 없습니다.");
  }

  const project = await db.project.findFirst({
    where: {
      id: input.projectId,
      organizationId: membership.organizationId,
      deletedAt: null,
    },
  });

  if (!project) {
    throw new Error("대상을 찾을 수 없습니다.");
  }

  await db.project.update({
    where: { id: project.id },
    data: {
      name: input.name,
      updatedById: viewer.userId,
    },
  });

  await db.auditLog.create({
    data: {
      actorId: viewer.userId,
      organizationId: membership.organizationId,
      action: "project.update_name",
      targetType: "project",
      targetId: project.id,
    },
  });

  revalidatePath(`/${input.orgSlug}/projects/${project.id}`);
}
```

이 정도면 "너무 중복 아닌가" 싶을 수 있다. 하지만 쓰기 경계에서는 이 중복이 비용이 아니라 안전장치다.

특히 멀티테넌트 서비스에서는 `projectId`만 믿고 업데이트하면 안 된다. 반드시 **현재 사용자 멤버십이 속한 조직 안의 리소스인지** 같이 검증해야 한다.

Route Handler도 같다.

```ts
// app/api/projects/[projectId]/route.ts
import { NextRequest, NextResponse } from "next/server";
import { requireApiViewer } from "@/lib/auth/api-viewer";

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ projectId: string }> }
) {
  const viewer = await requireApiViewer(request);
  const { projectId } = await params;

  if (!viewer.permissions.includes("project:write")) {
    return NextResponse.json({ message: "forbidden" }, { status: 403 });
  }

  return NextResponse.json({ ok: true, projectId });
}
```

핵심은 하나다.

> **화면 진입 권한과 데이터 변경 권한은 같은 곳에서 한 번만 확인하면 충분한 문제가 아니다. 쓰기 경계에서는 반드시 다시 확인해야 한다.**

---

## 핵심 개념 4: 세션 저장 방식은 "구현 취향"이 아니라 회수 전략의 선택이다

Next.js 인증에서 가장 먼저 부딪히는 선택 중 하나가 이것이다.

- DB 세션 기반 쿠키
- 자체 검증 가능한 JWT 쿠키
- Access Token + Refresh Token 이중 구조

각 방식은 장단점이 분명하다.

| 방식 | 장점 | 단점 | 잘 맞는 경우 |
|---|---|---|---|
| DB 세션 + HttpOnly 쿠키 | 회수와 강제 로그아웃이 쉽다 | 매 요청 저장소 조회 비용이 있다 | 관리형 SaaS, 백오피스, B2B 멀티테넌트 |
| Self-contained JWT 쿠키 | 검증이 빠르고 분산 시스템에 편하다 | 회수가 어렵고 권한 변경 반영이 늦다 | 짧은 수명의 단순 인증, 외부 API 게이트웨이 |
| Access + Refresh Token | 모바일, 외부 API, 다중 클라이언트에 유연하다 | 구현과 회전 로직이 가장 복잡하다 | SPA + 모바일 앱 + 외부 API가 함께 있는 구조 |

웹 앱 기준으로는 여전히 **서버 저장소 기반 세션 + HttpOnly Secure 쿠키**가 가장 운영하기 쉽다.

이 방식이 강한 이유는 다음과 같다.

- 관리자 강제 로그아웃이 쉽다
- 비밀번호 변경, 계정 잠금, 권한 회수 반영이 빠르다
- 세션 디바이스 목록 관리가 쉽다
- 감사 로그와 세션 추적을 연결하기 좋다
- JWT처럼 "이미 발급된 권한 정보"가 오래 떠돌지 않는다

반면 JWT가 무조건 나쁜 건 아니다. 다만 웹 앱에서 JWT를 택할 때는 아래를 감수해야 한다.

- 권한 변경 즉시 반영이 어렵다
- 로그아웃이 실질적으로 "클라이언트 삭제"가 되기 쉽다
- 토큰 수명을 길게 잡으면 탈취 리스크가 커진다
- 너무 많은 권한/조직 정보를 토큰에 담으면 stale claim 문제가 생긴다

실무 추천은 대개 이렇게 간다.

### 내부 웹 앱 중심이라면

- `session_id`만 쿠키에 저장
- 실제 사용자 상태와 권한은 서버에서 로드
- 짧은 idle timeout + 적당한 absolute timeout
- 중요한 이벤트에서 세션 회수

### 외부 API, 모바일 앱까지 함께 운영한다면

- 웹: 세션 쿠키 중심
- 외부 API: 별도 bearer token 또는 OAuth 계층
- refresh token rotation은 모바일/API 클라이언트에 집중
- 웹 인증과 외부 API 인증을 같은 규칙으로 억지 통합하지 않음

이 분리를 안 하면 웹 세션 문제와 외부 클라이언트 토큰 문제가 한 코드베이스에서 뒤엉킨다.

---

## 핵심 개념 5: Session Rotation은 보안 강화 기능이면서 동시에 장애 유발 포인트다

세션 회전은 이름만 보면 어렵지만 핵심은 단순하다.

> 오래 살아남는 인증 수단을 한 번 쓰고 끝내지 말고, 재사용 위험이 커지기 전에 새 식별자로 교체하자.

실무에서 자주 쓰는 회전 규칙은 두 층이다.

### 1) Sliding Expiration

사용자가 활동 중이면 세션 만료를 조금씩 뒤로 민다.

- 장점: UX가 좋다
- 단점: 무한 세션이 되기 쉬우니 absolute timeout이 필요하다

예시:

- idle timeout: 30분
- absolute timeout: 14일
- 마지막 회전 후 6시간 이상 지났으면 session id 재발급

### 2) Refresh Token Rotation

특히 모바일/API에서 많이 쓰는 방식이다.

- refresh token을 쓸 때마다 새 refresh token 발급
- 이전 토큰은 즉시 폐기
- 이미 사용된 refresh token이 재사용되면 탈취 의심으로 세션 패밀리 전체 폐기

이 개념을 웹 세션에도 응용할 수 있다. 예를 들어 중요한 권한 변경 후 세션 버전을 올리고, 예전 버전 쿠키는 더 이상 통과시키지 않는 식이다.

```ts
// pseudo code
if (session.lastRotatedAt < now - 6 hours) {
  const nextSession = await rotateSession(session.id);
  setSessionCookie(nextSession.id);
}
```

다만 여기서 장애가 자주 난다.

- 탭 두 개가 동시에 오래된 세션으로 요청
- 첫 요청이 회전 성공
- 두 번째 요청은 이미 폐기된 세션으로 들어와 로그아웃 처리

이 문제를 줄이려면 아래 중 하나가 필요하다.

- 짧은 유예 윈도우를 둔다
- 세션 패밀리와 현재 활성 버전을 별도로 관리한다
- 회전 직후 이전 세션을 즉시 hard delete하지 않고 soft invalid 상태로 둔다
- 중복 회전 요청을 idempotent하게 처리한다

즉 Session Rotation은 "좋은 보안 습관"이면서 동시에 **레이스 컨디션 설계 문제**다. 여기서 준비 없이 구현하면 인증 시스템이 가장 불안정한 부분이 된다.

---

## 실무 예시: B2B 멀티테넌트 대시보드에서 인증 흐름을 어떻게 나눌까

가정해보자. 서비스는 이런 구조다.

- 경로: `/{orgSlug}/projects/{projectId}`
- 사용자 한 명이 여러 조직에 속할 수 있다
- 조직별 역할이 다르다
- 페이지 읽기와 수정 액션이 모두 존재한다
- 웹 앱과 일부 API가 함께 있다

이때 추천하는 책임 분리는 아래와 같다.

### 1) 로그인

- 이메일/비밀번호 또는 SSO 성공
- 서버가 세션 저장소에 세션 생성
- 쿠키에는 `session_id`만 저장
- 쿠키 옵션은 `HttpOnly`, `Secure`, `SameSite=Lax`, `Path=/`

### 2) Middleware

- `/login`, `/signup`, `/public/*`는 통과
- `/app`, `/{orgSlug}` 등 보호 경로는 세션 쿠키 없으면 리다이렉트
- 여기서 조직 권한까지 확정하지는 않음

### 3) 레이아웃 또는 페이지 Server Component

- 세션 조회
- 사용자 활성 상태 확인
- `orgSlug`에 대한 멤버십 확인
- 없으면 `notFound()` 또는 권한 페이지로 전환

### 4) 페이지 내부 읽기 데이터

- 현재 조직 ID를 기준으로만 조회
- 사용자가 넘긴 `projectId`를 단독 신뢰하지 않음
- 항상 `organizationId`를 함께 where 조건에 넣음

### 5) Server Action 또는 Route Handler

- 다시 세션 확인
- 같은 조직 멤버인지 확인
- 액션 단위 권한 검증
- 변경 수행
- 감사 로그 기록
- `revalidatePath`, `revalidateTag` 등 후처리

### 6) 로그아웃, 비밀번호 변경, 관리자 강제 차단

- 세션 저장소 레코드 폐기 또는 세션 버전 증가
- 이후 쿠키는 즉시 무효
- 다른 디바이스도 함께 정리 가능

이 구조를 코드 디렉터리로 옮기면 대략 이런 느낌이다.

```txt
src/
  lib/
    auth/
      viewer.ts
      permissions.ts
      session.ts
      rotate-session.ts
  app/
    login/
      page.tsx
      actions.ts
    (app)/
      [orgSlug]/
        layout.tsx
        projects/
          [projectId]/
            page.tsx
            actions.ts
    api/
      projects/
        [projectId]/route.ts
middleware.ts
```

핵심은 인증 유틸이 흩어지지 않고, 읽기와 쓰기 경계에서 재사용되도록 만드는 것이다.

---

## 실무 예시 2: 권한 모델은 Role만으로 끝내지 말고 Action 중심으로 읽는 편이 낫다

처음에는 `ADMIN`, `MEMBER`, `VIEWER` 정도로 시작해도 된다. 하지만 서비스가 커질수록 역할 이름만으로는 부족해진다.

예를 들어 `ADMIN`도 아래 권한이 항상 같지 않다.

- 멤버 초대 가능
- 결제 정보 수정 가능
- 배포 승인 가능
- 분석 데이터 export 가능
- 감사 로그 열람 가능

그래서 내부적으로는 역할을 그대로 쓰더라도, 실제 코드에서는 최종적으로 액션 스코프를 해석하는 편이 좋다.

```ts
const roleToPermissions = {
  OWNER: [
    "project:read",
    "project:write",
    "member:invite",
    "billing:write",
  ],
  ADMIN: [
    "project:read",
    "project:write",
    "member:invite",
  ],
  VIEWER: ["project:read"],
} as const;

export function hasPermission(role: keyof typeof roleToPermissions, permission: string) {
  return roleToPermissions[role].includes(permission as never);
}
```

이 구조의 장점은 크다.

- UI 표시 여부를 세밀하게 제어 가능
- Server Action 검증과 API 검증을 같은 언어로 표현 가능
- 역할 이름이 바뀌어도 액션 정책은 유지 가능
- 나중에 커스텀 역할, 기능 플래그, 엔터프라이즈 플랜 권한으로 확장하기 쉽다

즉 **Role은 운영 편의용 라벨이고, 실제 인가는 Action 단위로 판단하는 편이 오래 버틴다**.

---

## 트레이드오프: 보안, 성능, 운영 편의는 동시에 최대로 얻기 어렵다

인증 설계는 거의 항상 절충이다. 대표적인 선택지를 정리하면 다음과 같다.

### 1) Middleware에서 어디까지 검증할 것인가

- 많이 검증할수록 입구에서 빨리 막는다
- 하지만 매 요청 비용이 커지고 Edge 제약을 많이 받는다

추천은 이렇다.

- Middleware: 존재 여부, 기본 서명, 공개/비공개 경로 판정
- 서버: 실제 사용자 상태와 권한 판정

### 2) JWT에 권한을 얼마나 담을 것인가

- 많이 담을수록 서버 조회가 줄 수 있다
- 하지만 권한 변경 즉시 반영이 어렵고 stale claim이 생긴다

권한이 자주 바뀌는 B2B 서비스라면 가볍게 가져가는 편이 낫다.

### 3) 세션 저장소 조회를 매번 할 것인가

- 보안과 회수성은 좋아진다
- 그러나 트래픽이 크면 저장소 부하가 늘어난다

타협안은 보통 이런 식이다.

- 짧은 TTL 캐시를 둔 세션 조회
- session version, revokedAt 같은 최소 정보만 빠르게 확인
- 고비용 사용자 프로필 로드는 필요한 곳에서만 수행

### 4) Sliding Session을 얼마나 공격적으로 쓸 것인가

- 자주 회전할수록 탈취 대응은 좋아진다
- 하지만 레이스 컨디션과 스토리지 쓰기량이 늘어난다

보안이 아주 강한 제품이 아니라면 요청마다 회전보다 **주기적 회전 + absolute timeout**이 현실적이다.

### 5) Server Action 중심으로 갈 것인가, Route Handler를 유지할 것인가

- Server Action은 웹 폼 UX와 가깝고 코드 흐름이 자연스럽다
- Route Handler는 외부 클라이언트, API 계약, CSRF/헤더 제어가 더 명확하다

실무에서는 섞어 쓰는 편이 일반적이다.

- 웹 앱 내부 폼/버튼: Server Action
- 외부 연동/API/웹훅: Route Handler

중요한 건 둘 다 같은 인증 유틸과 권한 정책을 공유해야 한다는 점이다.

---

## 흔한 실수: 인증이 있는 것처럼 보이지만 실제로는 비일관적인 상태들

실무에서 자주 보는 실수를 정리하면 아래와 같다.

### 1) Middleware만 통과하면 됐다고 생각한다

이건 가장 흔한 오해다. Middleware는 입장권 확인에 가깝다. 리소스별 인가는 서버에서 다시 해야 한다.

### 2) 버튼 숨김을 권한 제어로 착각한다

클라이언트 렌더링은 보안 경계가 아니다. 액션과 API는 항상 서버에서 재검증해야 한다.

### 3) `projectId`나 `orgSlug`를 URL에서 받았다고 그대로 믿는다

멀티테넌트 서비스는 항상 **사용자 멤버십 + 리소스 소속**을 함께 확인해야 한다.

### 4) JWT에 역할과 조직 정보를 너무 많이 넣는다

권한 변경 후에도 예전 claim이 살아남아 stale authorization이 된다.

### 5) 로그아웃이 쿠키 삭제로만 끝난다

서버 세션을 폐기하지 않으면 탈취된 쿠키나 병렬 세션이 그대로 살아 있을 수 있다.

### 6) 세션 회전 레이스를 고려하지 않는다

탭 여러 개, 자동 새로고침, 백그라운드 요청 때문에 회전 직후 인증 실패가 간헐적으로 발생한다.

### 7) CSRF를 완전히 잊는다

쿠키 기반 인증을 쓰는 Route Handler에서 상태 변경 요청을 받는다면 SameSite 정책, origin 검증, 필요시 CSRF 토큰까지 고려해야 한다.

### 8) 감사 로그를 남기지 않는다

누가 어떤 조직의 어떤 리소스를 언제 바꿨는지 남기지 않으면 권한 사고가 나도 추적이 안 된다.

### 9) 권한 에러와 존재하지 않음 에러를 무분별하게 섞는다

외부에 리소스 존재를 숨겨야 할 때는 `404`, 내부 관리 UI에서는 `403`이 더 적절할 수 있다. 보안 정책과 UX를 함께 결정해야 한다.

---

## 운영 체크포인트: 배포 전에 반드시 확인할 것들

인증은 구현보다 운영에서 더 자주 흔들린다. 아래 항목은 배포 전 점검용으로 추천할 만하다.

### 세션/쿠키

- [ ] 세션 쿠키에 `HttpOnly`, `Secure`, `SameSite`가 설정되어 있는가
- [ ] 로그아웃 시 서버 세션도 함께 폐기하는가
- [ ] idle timeout과 absolute timeout을 분리해 정의했는가
- [ ] 세션 회전 정책이 있고, 병렬 요청 레이스를 고려했는가

### 서버 검증

- [ ] Server Component에서 사용자 문맥을 일관되게 로드하는 유틸이 있는가
- [ ] Server Action과 Route Handler에서 권한을 다시 확인하는가
- [ ] 멀티테넌트 리소스 조회 시 조직 ID를 함께 where 조건에 넣는가
- [ ] 권한 정책이 역할 이름이 아니라 액션 기준으로 해석 가능한가

### 보안/운영

- [ ] 계정 잠금, 강제 로그아웃, 비밀번호 변경 시 세션 회수 전략이 있는가
- [ ] 관리자 액션에 감사 로그가 남는가
- [ ] CSRF, origin 검증, 서비스 계정 토큰 같은 별도 인증 경로를 구분했는가
- [ ] Edge Runtime과 Node Runtime에서 사용하는 인증 라이브러리 제약을 이해하고 있는가

### UX

- [ ] 만료 직전 세션 갱신이 사용자에게 갑작스러운 로그아웃으로 보이지 않는가
- [ ] 권한 없음과 로그인 필요 상태의 리다이렉트 UX가 구분되는가
- [ ] 로그인 후 원래 가려던 경로로 복귀하는 `from` 처리에 루프가 없는가

---

## 한 줄 정리

> **Next.js 인증 아키텍처의 핵심은 Middleware, Server Component, Server Action, Route Handler가 각자 다른 책임을 갖도록 분리하고, 실제 권한 판정은 항상 서버의 마지막 실행 지점에서 다시 확인하는 것이다.**
