---
layout: post
title: "Next.js Route Handlers 실전: BFF, Webhook, Streaming API 운영 기준"
date: 2026-03-26 11:40:00 +0900
categories: [nextjs]
tags: [study, nextjs, route-handler, bff, webhook, streaming, runtime, api]
---

## 배경: Route Handler를 "간단한 API 파일"로 보면 금방 무너진다

Next.js App Router를 도입한 팀은 보통 초기에 세 가지를 빠르게 익힌다.

- 서버 컴포넌트에서 직접 데이터 읽기
- Server Actions로 폼/뮤테이션 처리
- `app/api/**/route.ts`로 API 엔드포인트 만들기

문제는 여기서부터다. 많은 프로젝트에서 Route Handler가 점점 **아무거나 다 넣는 폴더**가 된다.

- 외부 백엔드 프록시
- 모바일용 REST API
- 결제사 webhook 수신
- 파일 업로드
- SSE 스트리밍
- 토큰 재발급
- 관리자용 CSV 다운로드
- 내부 서비스 간 인증 브리지

처음에는 다 같은 "서버 코드"처럼 보이지만, 운영 단계로 가면 성격이 완전히 다르다. 어떤 라우트는 **브라우저 UI를 위한 BFF(Backend for Frontend)** 이고, 어떤 라우트는 **외부 시스템이 호출하는 공개 계약**이며, 어떤 라우트는 **스트리밍 응답**이라 응답 헤더와 타임아웃 전략부터 다르다.

즉 실무에서 Route Handler의 핵심 질문은 이것이다.

> 이 코드는 단순히 데이터를 반환하는 함수인가, 아니면 HTTP 경계 전체를 책임지는 운영 계약인가?

이 질문을 놓치면 흔히 이런 문제가 발생한다.

- Server Action으로 충분한 UI mutation까지 Route Handler로 우회해서 코드 경로가 중복된다
- webhook 처리에서 멱등성이 없어 외부 서비스 재시도로 중복 반영이 발생한다
- BFF 라우트에 비즈니스 로직이 과도하게 쌓여 백엔드/프론트 모두에서 책임 경계가 흐려진다
- Edge Runtime을 멋으로 붙였다가 라이브러리 호환성과 디버깅에서 고생한다
- 스트리밍 응답에서 쿠키 설정, 버퍼링, 프록시 타임아웃을 고려하지 않아 실제 배포 환경에서 깨진다

이 글은 Next.js Route Handler 문법 소개가 아니라, **중급 이상 개발자가 Route Handler를 어디에 쓰고 어디까지 책임지게 할지 판단하는 기준**을 정리한다. 특히 아래 네 가지 실전 시나리오를 중심으로 본다.

1. **BFF**: 브라우저용 API를 프론트엔드 관점에서 정리할 때
2. **Webhook**: 외부 시스템 콜백을 안전하게 받을 때
3. **Streaming**: 진행률/토큰 스트림/대용량 응답을 보낼 때
4. **Runtime/Cache/Auth**: Node/Edge, 쿠키, 헤더, 캐시 정책을 운영 기준으로 다룰 때

목표는 `route.ts` 파일을 만드는 법이 아니라, **Route Handler를 팀이 믿고 운영할 수 있는 HTTP 경계로 설계하는 법**이다.

---

## 먼저 큰 그림: Server Component, Server Action, Route Handler는 역할이 다르다

App Router에서 가장 흔한 설계 실수는 세 가지 도구를 서로 대체 가능한 것으로 보는 것이다. 하지만 실무에서는 출발점부터 달라야 한다.

### 1) Server Component: "내 UI가 서버에서 읽을 데이터"

가장 먼저 고려할 선택지다. 같은 Next.js 앱 내부 페이지 렌더링에 필요한 읽기라면, 굳이 `/api/...`를 한 번 더 거치지 말고 서버 컴포넌트에서 직접 읽는 편이 단순하다.

```tsx
// app/dashboard/page.tsx
export default async function DashboardPage() {
  const [projects, notifications] = await Promise.all([
    getProjects(),
    getNotifications(),
  ]);

  return <Dashboard projects={projects} notifications={notifications} />;
}
```

이 경우 장점은 명확하다.

- 불필요한 API hop이 없다
- 타입/에러 흐름이 단순하다
- 인증 정보와 비밀키가 서버 안에 머문다
- 클라이언트-서버 waterfall을 줄이기 쉽다

### 2) Server Action: "내 UI가 트리거하는 내부 mutation"

폼 제출, 토글, 생성/수정/삭제처럼 **내 프론트엔드가 직접 호출하는 쓰기 작업**은 Server Action이 기본값인 경우가 많다.

```tsx
// app/posts/actions.ts
"use server";

import { revalidateTag } from "next/cache";

export async function publishPost(formData: FormData) {
  const title = String(formData.get("title") ?? "");
  await postService.publish({ title });
  revalidateTag("post:list");
}
```

장점은 다음과 같다.

- UI와 서버 mutation 경로가 자연스럽게 붙는다
- progressive enhancement가 쉽다
- 내부 타입 흐름이 매끄럽다
- 굳이 공개 HTTP 계약을 설계하지 않아도 된다

### 3) Route Handler: "HTTP 경계를 외부와 명시적으로 다뤄야 할 때"

Route Handler는 아래에 강하다.

- 외부 서비스가 호출하는 **webhook**
- 모바일 앱/외부 클라이언트가 소비할 **REST API**
- 브라우저용 **BFF**
- **SSE/스트리밍** 응답
- 파일 업로드/다운로드처럼 **HTTP 제어가 중요한 경우**
- 토큰/쿠키/헤더를 세밀하게 다뤄야 하는 경로

핵심은 이거다.

> **UI 내부 mutation이면 Server Action부터 검토하고, 외부 HTTP 계약이 필요할 때 Route Handler를 선택하라.**

이 기준이 서면 API 경로가 훨씬 덜 비대해진다.

---

## 핵심 개념 1: Route Handler의 본질은 "비즈니스 로직"이 아니라 "HTTP 경계 관리"다

실무에서 Route Handler를 잘 쓰는 팀은 이 레이어를 **얇지만 똑똑하게** 만든다. 반대로 못 쓰는 팀은 서비스 로직까지 죄다 여기에 넣는다.

Route Handler가 특히 잘하는 일은 다음과 같다.

- 요청 파싱 (`json`, `formData`, querystring, headers, cookies)
- 인증 정보 추출과 전달
- 스키마 검증과 오류를 HTTP status로 매핑
- 응답 포맷 통일
- 타임아웃/재시도/헤더 제어
- 캐시 헤더, 쿠키, CORS, redirect, streaming 같은 **HTTP 특화 제어**

반대로 아래를 Route Handler 본문에 과도하게 넣기 시작하면 위험 신호다.

- 복잡한 도메인 분기
- DB 트랜잭션 규칙 전체
- 여러 외부 시스템과의 orchestration
- 재시도/보상 로직이 섞인 긴 비즈니스 흐름

이런 로직은 서비스 레이어로 내리고, Route Handler는 **입구/출구를 관리하는 조정자** 역할에 집중하는 편이 유지보수성이 좋다.

### 권장 레이어 예시

```txt
app/api/reports/[reportId]/route.ts   # HTTP 경계
lib/validation/report.ts              # 입력 검증
lib/services/report-service.ts        # 비즈니스 로직
lib/integrations/report-api.ts        # 외부 API 연동
```

이 구조의 장점은 명확하다.

- Route Handler 테스트는 HTTP 계약 중심으로 본다
- 서비스 테스트는 도메인 규칙 중심으로 본다
- 외부 API 교체나 인증 방식 변경이 레이어별로 분리된다

### 동적 params와 request-time API는 "명시성"이 중요하다

최근 Next.js에서는 동적 세그먼트의 `params`를 비동기로 다루는 패턴이 권장된다. 쿠키도 `await cookies()`로 읽는 방향이 기본이다.

```ts
import { cookies } from "next/headers";
import type { NextRequest } from "next/server";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ reportId: string }> }
) {
  const { reportId } = await params;
  const cookieStore = await cookies();
  const session = cookieStore.get("session");

  if (!session) {
    return Response.json({ message: "unauthorized" }, { status: 401 });
  }

  return Response.json({ reportId, sessionExists: true });
}
```

이때 중요한 건 문법보다 의도다.

- 이 라우트가 **요청 시점 정보**에 의존하는지
- 인증/개인화 때문에 사실상 캐시 불가능한지
- URL segment와 query param이 도메인 키로 적절한지

즉 `route.ts`는 단순한 함수 파일이 아니라, **이 경로가 어떤 HTTP 계약을 갖는지 드러내는 설계 문서**여야 한다.

---

## 핵심 개념 2: BFF Route Handler는 "백엔드 복제본"이 아니라 프론트엔드 최적화 계층이다

프론트엔드 팀이 Route Handler를 가장 많이 쓰는 장면은 BFF다. 여기서 BFF란 "브라우저가 쓰기 좋은 모양으로 백엔드 여러 개를 조합·정규화하는 계층" 정도로 이해하면 된다.

잘 설계된 BFF는 프론트엔드 개발 속도를 높인다. 하지만 잘못 설계된 BFF는 **또 하나의 백엔드**가 된다.

### BFF가 유용한 경우

- 브라우저에 노출하면 안 되는 토큰/비밀키를 서버에서 숨겨야 함
- 여러 백엔드 응답을 프론트엔드 화면 모델 하나로 합쳐야 함
- 백엔드 오류 포맷이 제각각이라 UI 입장에서 일관된 형태로 정규화해야 함
- 요청 헤더, locale, 권한 정보를 백엔드별로 다르게 전달해야 함
- 브라우저에서 직접 호출하면 CORS/인증이 복잡함

### BFF가 과해지는 경우

- 기존 백엔드 API를 1:1로 그대로 복사한 프록시 엔드포인트가 늘어남
- 프론트엔드만 쓰는 데이터가 아닌데 BFF에서 비즈니스 규칙까지 결정함
- 동일한 비즈니스 로직이 BFF와 코어 백엔드에 중복됨
- 모바일/웹/배치가 각자 다른 BFF를 만들어 규칙이 분산됨

실무 기준으로 BFF는 **프론트엔드 최적화**까지만 책임지는 편이 좋다. 핵심 비즈니스 판단은 여전히 백엔드 서비스가 가져가는 것이 안전하다.

### 실무 예시: 관리자 대시보드용 보고서 BFF

상황은 이렇다.

- 브라우저는 `/api/reports/:id`를 호출한다
- 실제 데이터는 `billing-api`, `analytics-api`, `permissions-api` 세 곳에서 온다
- 브라우저에는 내부 서비스 URL이나 토큰을 숨기고 싶다
- UI는 복합 응답 하나만 받길 원한다

```ts
import { z } from "zod";
import { cookies, headers } from "next/headers";
import type { NextRequest } from "next/server";

const querySchema = z.object({
  includeCharts: z.enum(["true", "false"]).optional(),
});

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ reportId: string }> }
) {
  const { reportId } = await params;
  const { searchParams } = new URL(request.url);
  const parsed = querySchema.safeParse({
    includeCharts: searchParams.get("includeCharts") ?? undefined,
  });

  if (!parsed.success) {
    return Response.json(
      { message: "invalid query", issues: parsed.error.flatten() },
      { status: 400 }
    );
  }

  const cookieStore = await cookies();
  const session = cookieStore.get("session")?.value;
  const requestHeaders = await headers();
  const requestId = requestHeaders.get("x-request-id") ?? crypto.randomUUID();

  if (!session) {
    return Response.json({ message: "unauthorized" }, { status: 401 });
  }

  const includeCharts = parsed.data.includeCharts === "true";

  try {
    const [reportRes, permissionRes, chartRes] = await Promise.all([
      fetch(`${process.env.BILLING_API_URL}/reports/${reportId}`, {
        headers: {
          Authorization: `Bearer ${session}`,
          "x-request-id": requestId,
        },
        signal: AbortSignal.timeout(3000),
      }),
      fetch(`${process.env.PERMISSION_API_URL}/reports/${reportId}/access`, {
        headers: {
          Authorization: `Bearer ${session}`,
          "x-request-id": requestId,
        },
        signal: AbortSignal.timeout(1500),
      }),
      includeCharts
        ? fetch(`${process.env.ANALYTICS_API_URL}/reports/${reportId}/charts`, {
            headers: {
              Authorization: `Bearer ${session}`,
              "x-request-id": requestId,
            },
            signal: AbortSignal.timeout(4000),
          })
        : Promise.resolve(new Response(JSON.stringify(null), { status: 200 })),
    ]);

    if (permissionRes.status === 403) {
      return Response.json({ message: "forbidden" }, { status: 403 });
    }

    if (!reportRes.ok) {
      return Response.json({ message: "report fetch failed" }, { status: 502 });
    }

    const [report, permission, charts] = await Promise.all([
      reportRes.json(),
      permissionRes.json(),
      chartRes.json(),
    ]);

    return Response.json(
      {
        report,
        permission,
        charts,
        meta: { requestId },
      },
      {
        headers: {
          "Cache-Control": permission.scope === "public"
            ? "private, max-age=30, stale-while-revalidate=120"
            : "private, no-store",
        },
      }
    );
  } catch (error) {
    return Response.json(
      {
        message: "upstream timeout",
        detail: error instanceof Error ? error.message : "unknown",
      },
      { status: 504 }
    );
  }
}
```

이 예제의 포인트는 세 가지다.

1. **입력 검증**을 라우트 초입에서 한다
2. 백엔드 여러 개를 **병렬 호출**한다
3. UI가 바로 쓰기 좋은 응답으로 **정규화**한다

### BFF 설계에서 꼭 지켜야 할 기준

#### 1) 업스트림 오류를 그대로 흘리지 말고 의미 있는 HTTP 계약으로 바꿔라

예를 들어 백엔드가 아래처럼 제각각이라면,

- 서비스 A: `{ errorCode: "NO_PERMISSION" }`
- 서비스 B: `{ code: 40301, reason: "AUTH_DENIED" }`
- 서비스 C: HTML 에러 페이지

브라우저는 결국 **일관된 401/403/404/422/502** 정도만 안정적으로 다루면 된다. BFF는 이 차이를 흡수해줘야 한다.

#### 2) fan-out이 늘어날수록 타임아웃/partial failure 정책을 먼저 정하라

세 개의 백엔드를 부르는 순간부터 질문이 생긴다.

- 하나 실패하면 전체 실패인가?
- charts만 실패하면 텍스트 데이터만 보여줄 수 있는가?
- 각 서비스 타임아웃은 몇 초인가?
- 프론트엔드가 재시도해도 안전한가?

BFF에서 가장 흔한 장애는 로직 버그보다 **fan-out의 꼬리 지연(latency tail)** 이다.

#### 3) BFF는 화면 모델을 만들되, 도메인 진실의 소유자가 되면 안 된다

예를 들어 "환불 가능 여부"는 UI 편의용 boolean으로 만들어 내려줄 수 있다. 하지만 그 판단 규칙 자체를 BFF만 알고 있게 만들면 나중에 모바일, 배치, 관리자 콘솔이 각자 다른 규칙을 갖게 된다.

- **가능**: `canRefund: true` 같은 파생 필드 추가
- **위험**: 환불 정책의 핵심 분기 전체를 BFF에만 구현

---

## 핵심 개념 3: Webhook Route Handler의 핵심은 응답 속도보다 멱등성과 신뢰 경계다

외부 시스템 webhook은 일반 API와 성격이 다르다. 호출자는 브라우저가 아니라 결제사, 메시지 플랫폼, SaaS 서비스다. 이들은 네 요청이 느리거나 실패하면 **재시도**한다. 그리고 대개 순서 보장도 약하다.

즉 webhook 처리의 핵심 질문은 이것이다.

> 같은 이벤트가 두 번 오거나 순서가 바뀌어도 시스템이 안전한가?

### webhook에서 흔한 실패 패턴

- 서명 검증 전에 JSON 파싱부터 해서 위조 요청을 받아버림
- 요청 1회 = 이벤트 1회 처리라고 가정해서 중복 반영됨
- DB 반영 + 외부 발행 + 이메일 전송을 동기 처리하다가 timeout 남
- provider는 재시도했는데 우리는 중복 방지 키가 없어 같은 주문이 여러 번 확정됨
- webhook 실패 원인 추적용 request id / event id 저장이 없음

### webhook은 보통 "빠르게 검증하고, 기록하고, 비동기 처리"가 유리하다

가능한 기본 원칙은 이렇다.

1. **서명 검증**
2. **이벤트 ID 기반 멱등성 확인**
3. **수신 사실 저장**
4. **비동기 작업 큐 발행**
5. **빠르게 2xx 반환**

### 실무 예시: 결제 승인 webhook

```ts
import crypto from "node:crypto";
import type { NextRequest } from "next/server";

function verifySignature(rawBody: string, signature: string | null) {
  if (!signature) return false;

  const expected = crypto
    .createHmac("sha256", process.env.PAYMENT_WEBHOOK_SECRET!)
    .update(rawBody)
    .digest("hex");

  return crypto.timingSafeEqual(
    Buffer.from(signature),
    Buffer.from(expected)
  );
}

export async function POST(request: NextRequest) {
  const rawBody = await request.text();
  const signature = request.headers.get("x-payment-signature");

  if (!verifySignature(rawBody, signature)) {
    return Response.json({ message: "invalid signature" }, { status: 401 });
  }

  const event = JSON.parse(rawBody) as {
    event_id: string;
    type: "payment.approved" | "payment.failed";
    order_id: string;
    payment_id: string;
  };

  const alreadyProcessed = await webhookEventRepository.exists(event.event_id);
  if (alreadyProcessed) {
    return Response.json({ ok: true, deduped: true }, { status: 200 });
  }

  await db.transaction(async (tx) => {
    await webhookEventRepository.insert(tx, {
      eventId: event.event_id,
      eventType: event.type,
      payload: rawBody,
      status: "received",
    });

    await outboxRepository.enqueue(tx, {
      topic: "payment.webhook.received",
      key: event.event_id,
      payload: rawBody,
    });
  });

  return Response.json({ ok: true }, { status: 202 });
}
```

### 왜 이 패턴이 실무에서 강한가?

#### 1) 멱등성 키가 명확하다

`event_id`를 기준으로 dedupe하면, 제공자가 timeout 때문에 같은 이벤트를 다시 보내도 안전하다. webhook에서는 "재시도는 정상 동작"으로 보는 편이 맞다.

#### 2) provider latency에 덜 끌려다닌다

승인 후 후속 처리(주문 확정, 메일 발송, 분석 이벤트 적재)를 모두 동기 처리하면 provider timeout과 네 비즈니스 플로우가 강하게 결합된다. 보통은 **수신 성공**과 **후속 처리 성공**을 분리하는 편이 낫다.

#### 3) 감사 추적이 쉬워진다

나중에 문제가 생겼을 때 아래를 바로 추적할 수 있다.

- 어떤 `event_id`가 들어왔는가
- 몇 번 재시도됐는가
- 언제 수신됐는가
- 비동기 후속 처리가 어느 단계에서 실패했는가

### webhook에서 상태 코드는 "문법"이 아니라 재시도 정책이다

여기서 중요한 포인트 하나가 더 있다. 외부 시스템은 네 응답 코드를 보고 재시도 여부를 결정한다.

- `2xx`: 정상 수신으로 간주, 보통 재시도 안 함
- `4xx`: 잘못된 요청으로 간주, 재시도 안 하거나 제한적
- `5xx`: 일시 장애로 간주, 재시도 가능성 큼

그래서 webhook에서 500을 쉽게 던지면 provider가 계속 재시도하면서 문제를 증폭시킬 수 있다. 반대로 실제로는 수신했는데 500을 내려도 중복 처리가 생긴다.

**핵심은 "어디까지를 수신 완료로 볼지"를 먼저 정의하는 것**이다.

---

## 핵심 개념 4: Streaming Route Handler는 "응답 시작 시점" 이후 제약을 이해해야 한다

AI 응답 스트림, 로그 tail, 작업 진행률, 대용량 CSV 생성 상태 같은 기능을 만들다 보면 Route Handler에서 스트리밍이 필요해진다. 이때 가장 많이 놓치는 사실은 다음이다.

> 스트리밍은 단순히 데이터를 조금씩 보내는 기능이 아니라, **응답을 일찍 시작하는 대신 나중에 할 수 없는 일이 많아지는 모드**다.

특히 중요한 제약은 아래다.

- 응답을 시작한 뒤에는 쿠키 설정이 사실상 불가능하다
- 중간 오류를 기존 JSON 에러 포맷처럼 바꾸기 어렵다
- 프록시/플랫폼 버퍼링에 따라 "스트리밍처럼 보이는 척"만 할 수도 있다
- 클라이언트 연결 종료 감지와 자원 정리가 필요하다
- 일부 배포 환경에서는 idle timeout이 짧다

### 실무 예시: SSE로 리포트 생성 진행률 전달

```ts
import type { NextRequest } from "next/server";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ reportId: string }> }
) {
  const { reportId } = await params;

  const stream = new ReadableStream({
    async start(controller) {
      const encoder = new TextEncoder();

      const send = (event: string, data: unknown) => {
        controller.enqueue(
          encoder.encode(
            `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`
          )
        );
      };

      try {
        send("progress", { reportId, step: "queued", percent: 10 });

        const task = await reportService.start(reportId);
        send("progress", { reportId, step: "started", percent: 30, taskId: task.id });

        for await (const update of reportService.watch(task.id)) {
          send("progress", {
            reportId,
            step: update.step,
            percent: update.percent,
          });
        }

        send("done", { reportId, downloadUrl: `/api/reports/${reportId}/download` });
        controller.close();
      } catch (error) {
        send("error", {
          message: error instanceof Error ? error.message : "unknown",
        });
        controller.close();
      }
    },
    cancel() {
      // 클라이언트가 연결을 닫았을 때 자원 정리
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
    },
  });
}
```

### 스트리밍에서 꼭 기억할 운영 포인트

#### 1) 인증과 쿠키 처리는 스트림 시작 전에 끝내라

응답 헤더가 이미 나간 뒤에는 쿠키 수정이 어렵다. 인증이 필요한 스트림이면 **시작 전에 세션 검증을 끝내고**, 필요한 헤더를 다 준비한 뒤 스트림을 연다.

#### 2) 중간 실패를 HTTP status로 표현할 수 없다고 생각하라

스트림이 시작된 뒤에는 이미 200 OK가 나간 상태인 경우가 많다. 따라서 중간 실패는 `event: error` 같은 **애플리케이션 레벨 이벤트**로 설계해야 한다.

#### 3) 버퍼링과 프록시 타임아웃을 확인하라

로컬에서는 잘 되는데 운영에서 한 번에 몰아서 오는 경우가 흔하다. 원인은 보통 다음 중 하나다.

- CDN/프록시가 버퍼링 중
- idle timeout이 짧음
- gzip/transform이 스트리밍을 방해함
- 클라이언트가 EventSource 대신 일반 fetch로 잘못 소비 중

스트리밍은 코드보다 **배포 경로 전체**를 같이 검증해야 한다.

#### 4) 대용량 파일 다운로드와 "진행률 스트리밍"은 분리하는 편이 낫다

CSV/PDF 생성 같은 기능에서 생성과 다운로드를 같은 요청으로 묶으면 timeout과 재시도 정책이 꼬인다. 보통은 아래가 더 안정적이다.

1. 생성 요청
2. 작업 상태 polling/SSE
3. 완료 후 다운로드 URL 제공

즉 스트리밍은 파일 전송 자체보다 **상태 전달**에 더 잘 맞는 경우가 많다.

---

## 핵심 개념 5: Runtime, Cache, Auth는 성능 옵션이 아니라 운영 계약이다

Route Handler를 다룰 때 자주 나오는 말이 있다.

- Edge가 더 빠르지 않나요?
- GET이면 다 캐시되나요?
- 쿠키 읽으면 어떤 일이 생기죠?
- `revalidate`만 넣으면 충분한가요?

이 질문들은 모두 결국 **이 라우트의 운영 계약을 무엇으로 볼 것인가**에 관한 얘기다.

### 1) Runtime: 특별한 이유가 없으면 Node.js를 기본값으로 두는 편이 안전하다

실무에서는 Node.js runtime이 기본값인 경우가 많다. 이유는 단순하다.

- Node API 접근이 자유롭다
- 많은 npm 패키지가 Node 가정을 깔고 있다
- DB 드라이버, 파일 처리, 서명 검증이 더 자연스럽다
- 디버깅과 로컬 재현이 상대적으로 쉽다

반대로 Edge Runtime은 다음처럼 **명확한 이유가 있을 때만** 검토하는 편이 낫다.

- 글로벌 지리 분산이 실제로 중요한 매우 짧은 응답 경로
- Web-standard API만으로 충분한 가벼운 로직
- 이미 프로젝트/플랫폼이 Edge 중심 운영 전략을 갖고 있음

webhook, BFF, 서명 검증, DB 연동이 섞이면 보통 Node가 더 현실적이다.

### 2) 캐시는 "빠르게 보이기"보다 "틀리면 안 되는 데이터인지"부터 판단하라

Route Handler의 GET은 캐시 이득을 볼 수 있지만, 무조건 캐시하는 것이 정답은 아니다.

예를 들어 아래처럼 나눠 생각하는 편이 안전하다.

#### 캐시 친화적

- 공개 랭킹
- 환율/공지/정적 메타데이터
- 짧은 TTL이 허용되는 조회

#### 캐시 신중

- 사용자 개인화 데이터
- 권한에 따라 응답이 바뀌는 데이터
- 갱신 직후 일관성이 중요한 관리자 화면

BFF에서 인증 쿠키를 읽고 사용자별 응답을 만들면 대개 `private, no-store` 또는 매우 짧은 private cache가 맞다. 반면 공개 조회 API는 `s-maxage`, `stale-while-revalidate`, `revalidate` 같은 옵션을 적극 검토할 수 있다.

중요한 건 **캐시 전략을 라우트 단위로 명시적으로 합의하는 것**이다.

### 3) 인증은 라우트 안에서만 끝나지 않는다

Route Handler에서 인증을 다룰 때는 세 가지 층을 같이 봐야 한다.

1. **들어오는 요청의 신원**: 세션 쿠키, bearer token, signature
2. **업스트림으로 전달할 자격 증명**: 내부 API 토큰, service credential, user token relay
3. **응답의 노출 범위**: 브라우저 캐시 가능 여부, 로그에 남겨도 되는지, CORS 허용 범위

특히 BFF에서 흔한 실수는 브라우저 세션을 업스트림에 그대로 넘기면서,

- 어떤 헤더를 relay하는지 기준이 없고
- request id가 없어 추적이 어렵고
- 사용자 토큰과 서비스 토큰을 혼용하는 것이다

권장되는 기준은 아래에 가깝다.

- **필요한 최소 헤더만 전달**
- `x-request-id`, `x-user-id` 같은 추적 헤더를 명시
- 서비스 간 인증은 사용자 토큰 relay와 별도 정책으로 설계
- 에러 응답에 민감한 내부 정보를 그대로 노출하지 않음

---

## 실무 예시: Route Handler를 언제 쓰고 언제 쓰지 말아야 하는가

실제 프로젝트에서 헷갈리는 장면을 몇 가지로 정리해보자.

### 사례 1) 게시글 생성 폼

- 사용 주체: 내 웹 UI
- 작업 성격: mutation
- 외부 소비자: 없음

**권장:** Server Action 우선

이 경우 Route Handler를 만들면 오히려 UI → `/api/posts` → 서비스로 한 단계 더 돌아간다. 특별히 외부 클라이언트 계약이 필요한 게 아니라면 Server Action이 더 자연스럽다.

### 사례 2) 모바일 앱과 웹이 함께 쓰는 사용자 프로필 API

- 사용 주체: 웹, 모바일
- 작업 성격: 공통 HTTP 계약
- 외부 소비자: 있음

**권장:** Route Handler 또는 독립 백엔드 API

이 경우는 Route Handler가 적합할 수 있다. 다만 규모가 커지면 Next 앱 안에서 계속 키우기보다 독립 서비스로 분리할 시점을 같이 봐야 한다.

### 사례 3) Stripe/토스 결제 webhook

- 사용 주체: 외부 시스템
- 작업 성격: 서명 검증 + 멱등 수신
- 재시도 가능성: 높음

**권장:** Route Handler

Server Action으로 처리할 이유가 없다. HTTP 헤더, raw body, signature, idempotency가 핵심이기 때문이다.

### 사례 4) 대시보드 첫 화면 데이터 읽기

- 사용 주체: 내 웹 UI
- 작업 성격: 읽기
- SEO/초기 렌더링 중요: 높음

**권장:** Server Component 직접 fetch 우선

굳이 `/api/dashboard`를 만들어 자기 자신에게 다시 요청할 필요가 없다.

### 사례 5) AI 답변 토큰 스트림

- 사용 주체: 브라우저
- 작업 성격: 장시간 응답, streaming
- HTTP 제어 중요: 매우 높음

**권장:** Route Handler

이건 Route Handler의 강한 영역이다. 단, 스트리밍 이후 헤더/쿠키/오류 표현 제약을 반드시 고려해야 한다.

---

## 트레이드오프: Route Handler를 잘 쓰는 팀은 무엇을 포기하고 무엇을 얻는가

좋은 설계는 항상 비용을 동반한다. Route Handler도 마찬가지다.

### 1) Route Handler 중심 설계의 장점

- HTTP 계약이 명확해진다
- 외부 통합(webhook, mobile, partner API)에 대응하기 좋다
- 쿠키/헤더/redirect/streaming 같은 웹 프로토콜 제어가 유연하다
- 프론트엔드 팀이 BFF를 통해 화면 개발 속도를 높일 수 있다

### 2) Route Handler 중심 설계의 비용

- API surface가 빠르게 늘어난다
- UI 내부 호출까지 다 API화하면 중복 레이어가 된다
- BFF가 비대해지면 코어 백엔드와 책임이 겹친다
- 캐시/인증/timeout/관측성까지 챙겨야 해 운영 복잡도가 높다

### 3) Server Action 우선 설계의 장점

- 내부 UI mutation 경로가 단순하다
- 타입과 리렌더링 흐름이 자연스럽다
- 공개 API 계약을 별도 설계할 필요가 줄어든다

### 4) Server Action 우선 설계의 한계

- 외부 소비자에게 열 수 없다
- webhook/raw body/signature 같은 경계를 다루기 어렵다
- GET/streaming/public REST API처럼 HTTP 의미가 중요한 장면에 적합하지 않다

결국 핵심은 어느 도구가 더 현대적이냐가 아니라,

> **이 기능이 React UI 내부 행위인지, 아니면 외부와 맺는 HTTP 계약인지**

를 먼저 구분하는 것이다.

---

## 흔한 실수

### 1) 페이지 렌더링용 읽기까지 전부 `/api/*`로 우회한다

App Router인데도 `page.tsx -> fetch('/api/...') -> route.ts -> backend` 형태를 습관적으로 만들면 레이턴시와 복잡도만 늘어난다. UI 내부 읽기는 서버 컴포넌트 직접 fetch가 더 나은 경우가 많다.

### 2) Route Handler 안에 도메인 로직을 과도하게 넣는다

입력 검증, 헤더 처리, 응답 변환까지는 좋다. 하지만 복잡한 비즈니스 분기와 DB 규칙까지 다 쌓이면 route 파일이 곧 서비스가 된다. 라우트는 얇게, 서비스는 별도로.

### 3) webhook을 동기 비즈니스 처리로 끝내려 한다

외부 서비스는 네 비즈니스 사정을 모른다. webhook 수신은 빠르게, 후속 처리는 비동기로 분리하는 편이 보통 더 안전하다.

### 4) 멱등성 없이 재시도를 만난다

결제 승인, 구독 갱신, 메시지 delivery callback은 중복 호출이 정상이다. `event_id`, `delivery_id`, `(provider, external_id)` 같은 dedupe 키가 없으면 언젠가 사고가 난다.

### 5) Edge Runtime을 기본값처럼 사용한다

"더 최신 같아서" 또는 "더 빠를 것 같아서"만으로 Edge를 선택하면 호환성, 라이브러리, 디버깅에서 비용을 치른다. 명확한 이유가 없으면 Node가 안전하다.

### 6) 스트리밍에서 응답 시작 후에도 상태코드/쿠키를 바꿀 수 있다고 생각한다

스트리밍은 일반 JSON 응답과 제약이 다르다. 인증, 쿠키, 헤더는 시작 전에 끝내고, 중간 실패는 앱 이벤트로 표현해야 한다.

### 7) 업스트림 fan-out을 병렬화하지 않거나 timeout 없이 호출한다

BFF에서 순차 호출을 쌓으면 꼬리 지연이 심해진다. `Promise.all`, 개별 타임아웃, 부분 실패 정책이 필수다.

### 8) 관측성 없이 운영한다

`x-request-id`, provider event id, upstream latency, dedupe hit rate 같은 지표가 없으면 장애가 나도 어디서 꼬였는지 모른다.

### 9) `route.ts`와 `page.tsx`의 세그먼트 충돌을 늦게 발견한다

같은 경로 세그먼트에 페이지와 라우트를 무심코 겹치게 두면 구조가 꼬인다. 초기에 URL 설계를 명확히 해야 한다.

### 10) 에러 응답을 프레임워크 기본 예외에 맡긴다

Route Handler는 외부 계약이다. 브라우저나 외부 시스템이 안정적으로 처리할 수 있는 에러 포맷과 상태 코드를 직접 설계하는 편이 낫다.

---

## 실무 체크리스트

### 1) 도구 선택

- [ ] 이 기능은 UI 내부 mutation인가? 그렇다면 Server Action을 먼저 검토했는가?
- [ ] 이 기능은 외부 HTTP 계약(webhook, mobile API, public API, streaming)인가?
- [ ] 단순 읽기라면 서버 컴포넌트 직접 fetch로 충분하지 않은가?

### 2) Route Handler 구조

- [ ] 라우트는 요청 파싱/검증/응답 변환에 집중하고 있는가?
- [ ] 도메인 로직은 서비스 레이어로 분리했는가?
- [ ] 입력 스키마 검증이 있는가? (`zod`, validator 등)
- [ ] 에러 응답 형식과 상태 코드가 일관적인가?

### 3) BFF 운영

- [ ] 업스트림 fan-out이 병렬화되어 있는가?
- [ ] 각 업스트림 호출에 타임아웃이 있는가?
- [ ] 부분 실패 허용 여부를 정의했는가?
- [ ] 브라우저에 숨겨야 할 토큰/내부 URL이 노출되지 않는가?
- [ ] request id를 업스트림까지 전달하는가?

### 4) Webhook 운영

- [ ] raw body 기준 서명 검증을 하는가?
- [ ] 중복 이벤트를 막는 멱등 키가 있는가?
- [ ] 수신 성공과 후속 처리 성공을 분리했는가?
- [ ] event id, attempt, provider, payload hash를 저장하는가?
- [ ] 어떤 상태 코드가 provider 재시도를 유발하는지 이해하고 있는가?

### 5) Streaming 운영

- [ ] 인증과 쿠키 처리를 스트림 시작 전에 끝냈는가?
- [ ] 중간 실패를 앱 레벨 이벤트로 표현하는가?
- [ ] CDN/프록시 버퍼링과 timeout을 검증했는가?
- [ ] 클라이언트 연결 종료 시 자원 정리 경로가 있는가?

### 6) Runtime / Cache / Auth

- [ ] 특별한 이유가 없다면 Node.js runtime을 기본으로 두었는가?
- [ ] Edge를 쓰는 이유가 지연/배포 전략 관점에서 명확한가?
- [ ] 개인화/권한 데이터의 캐시 정책이 명시적인가?
- [ ] 전달하는 헤더와 자격 증명이 최소 권한 원칙을 따르는가?
- [ ] 민감 정보가 에러 응답/로그에 과도하게 남지 않는가?

### 7) 관측성

- [ ] 요청당 고유 request id가 있는가?
- [ ] 업스트림 호출별 latency/timeout/실패율을 측정하는가?
- [ ] webhook dedupe hit rate를 보는가?
- [ ] 4xx/5xx 비율을 라우트 단위로 모니터링하는가?

---

## 한 줄 정리

Next.js Route Handler의 가치는 단순히 API를 만들 수 있다는 데 있지 않다. **BFF, webhook, streaming처럼 HTTP 경계 자체가 중요한 문제를 Node/Cache/Auth/멱등성까지 포함한 운영 계약으로 설계할 때 비로소 Route Handler가 제 역할을 한다.**
