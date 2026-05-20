---
layout: post
title: "Next.js Observability 실전: instrumentation.ts, OpenTelemetry, Trace Propagation, Server Action 계측으로 느린 요청을 추적하는 법"
date: 2026-05-20 11:40:00 +0900
categories: [nextjs]
tags: [study, nextjs, observability, instrumentation, opentelemetry, tracing, server-action, route-handler, logging, operations]
permalink: /nextjs/2026/05/20/study-nextjs-instrumentation-opentelemetry-trace-propagation-server-actions-observability.html
---

## 배경: Next.js 서비스가 느려지는 이유는 많지만, 어디서 느려졌는지 모르면 결국 감으로 고치게 된다

App Router로 서비스를 운영하다 보면 성능 이슈는 꽤 다양한 얼굴로 나타난다.

- 어떤 페이지는 평소엔 빠른데 특정 시간대만 유독 느리다
- Server Action 저장 버튼을 누르면 가끔 8초씩 걸리는데 재현이 잘 안 된다
- Route Handler는 200을 반환했는데 사용자는 중간에 timeout을 겪었다고 말한다
- 캐시를 넣었더니 평균은 빨라졌지만 p95는 오히려 더 흔들린다
- 외부 API가 느린지, DB가 느린지, 우리 코드가 느린지 한눈에 안 보인다
- Proxy, Server Component, Route Handler, Server Action이 한 요청 흐름에 섞여 있는데 병목 지점이 분리되지 않는다
- 로그는 많은데 서로 request id가 안 맞아 한 건의 요청을 끝까지 따라가기 어렵다

초기에는 보통 이렇게 대응한다.

- `console.time()`를 몇 군데 찍는다
- 느려 보이는 함수에 로그를 추가한다
- 배포 후 다시 눌러 본다
- 그래도 원인을 못 찾으면 `revalidate`나 `maxDuration`만 손본다

문제는 이 방식이 금방 한계에 닿는다는 점이다.

Next.js 운영 성능 문제의 본질은 단순히 "함수 하나가 느리다"가 아니다.

- 하나의 사용자 요청이 여러 서버 경계를 통과한다
- 일부는 캐시되고 일부는 동적으로 실행된다
- 일부는 스트리밍되고 일부는 action 이후 재렌더된다
- 외부 BFF, DB, SaaS API, 큐, 파일 저장소까지 호출 체인이 이어진다

즉 실무에서 필요한 것은 개별 로그 몇 줄이 아니라 다음이다.

> **한 요청이 어디서 시작해 어떤 서버 경계를 지나고, 어느 외부 의존성에서 시간을 썼으며, 어떤 실패가 어떤 사용자 경험으로 이어졌는지 추적할 수 있는 구조**

이 글은 Next.js에서 observability를 붙이는 법을 얕게 훑는 글이 아니다. 중급 이상 개발자를 기준으로 아래 질문에 답하는 것이 목표다.

1. `instrumentation.ts`는 정확히 어떤 책임을 가져야 하는가
2. OpenTelemetry를 붙일 때 span을 어디까지, 어떤 이름으로, 어떤 속성으로 남겨야 하는가
3. Route Handler, Server Action, 외부 fetch, DB 호출, 큐 적재를 하나의 trace로 어떻게 연결할 것인가
4. 로그와 trace를 어떻게 함께 써야 "로그는 많은데 원인 추적은 안 되는" 상태를 피할 수 있는가
5. 성능 최적화 전에 어떤 관측 지표와 경보를 먼저 고정해야 하는가
6. 흔한 실수와 운영 체크리스트는 무엇인가

결론부터 먼저 말하면 이렇다.

> **Next.js observability의 핵심은 로그를 많이 남기는 것이 아니라, 사용자 요청 경계와 서버 실행 경계를 trace로 연결하고, 그 위에 로그·메트릭·에러를 같은 상관관계 키로 얹어 "왜 느린지"를 추측이 아니라 증거로 설명할 수 있게 만드는 데 있다.**

---

## 먼저 큰 그림: Next.js 관측성은 "페이지" 단위가 아니라 "요청 흐름" 단위로 설계해야 한다

많은 팀이 observability를 화면 기준으로 생각한다.

- `/dashboard`가 느리다
- `/api/upload`가 느리다
- `/admin/posts/[id]` 저장이 느리다

물론 출발점으로는 맞다. 하지만 실제 병목은 화면 경계보다 더 아래에 있다.

예를 들어 게시글 발행 버튼 하나를 눌렀다고 해보자.

1. 브라우저가 Server Action을 호출한다
2. 서버에서 권한을 검증한다
3. DB 트랜잭션으로 상태를 바꾼다
4. 캐시 무효화를 수행한다
5. 외부 검색 인덱싱 API를 호출한다
6. 감사 로그를 적재한다
7. 액션 결과로 페이지를 다시 렌더한다
8. 일부 컴포넌트는 fresh fetch를 다시 수행한다

사용자는 그냥 "발행 버튼이 느리다"고 느끼지만, 서버 안에서는 여러 단계가 겹친다.

그래서 관측성 구조를 아래처럼 나누는 편이 좋다.

### 1) 진입 경계

- Proxy
- Route Handler
- Server Action
- 페이지 최초 렌더

여기서는 요청이 시작됐다는 사실과 기본 문맥을 잡는다.

### 2) 작업 경계

- 인증/인가
- DB 읽기/쓰기
- 외부 HTTP 호출
- 큐 적재
- 캐시 무효화
- 템플릿 렌더/직렬화

여기서는 시간이 어디서 쓰였는지와 실패 지점을 본다.

### 3) 결과 경계

- 응답 상태 코드
- redirect / notFound / error.tsx 진입 여부
- 사용자 체감 latency
- 재시도 여부

여기서는 실패가 어떤 표면으로 드러났는지 본다.

이렇게 보면 자연스럽게 기준이 정리된다.

- **로그는 사건 설명**에 강하다
- **메트릭은 추세 감지**에 강하다
- **트레이스는 한 요청의 원인 추적**에 강하다

셋을 섞어 쓰되, 중심축은 trace가 되는 편이 좋다. 특히 Next.js처럼 서버 경계가 여러 개인 구조에서는 더 그렇다.

---

## 핵심 개념 1: `instrumentation.ts`의 역할은 "모든 계측 로직을 우겨 넣는 곳"이 아니라 런타임 부트스트랩을 고정하는 것이다

Next.js의 `instrumentation.ts`를 처음 보면 마치 여기에 모든 계측 코드를 넣어야 할 것처럼 느껴질 수 있다. 실무에서는 그렇게 가져가면 오히려 복잡해진다.

`instrumentation.ts`의 더 현실적인 역할은 아래에 가깝다.

1. 런타임 시작 시 한 번 필요한 계측 초기화
2. OpenTelemetry SDK 또는 exporter 등록
3. 공통 resource 속성 설정
4. 환경별 on/off 제어
5. 자동 계측과 수동 계측이 만날 기반 준비

즉 여기는 **관측 프레임워크의 진입점**이지, 비즈니스 로직을 넣는 곳이 아니다.

### 좋은 책임 예시

- 서비스 이름, 버전, 배포 환경 등록
- OTLP exporter, console exporter, vendor SDK 초기화
- 샘플링 비율 설정
- fetch/HTTP/DB auto instrumentation 부트스트랩

### 나쁜 책임 예시

- 특정 도메인 action의 span 이름 결정
- 사용자 권한 검사 로직 직접 삽입
- 페이지별 성능 분기 로직
- 에러 매핑 정책 구현

### 최소 부트스트랩 예시

```ts
// instrumentation.ts
import { registerOTel } from '@vercel/otel'

export function register() {
  registerOTel({
    serviceName: 'web-hr',
  })
}
```

위 예시는 아주 최소 형태다. 하지만 운영 환경에서는 보통 서비스 메타데이터와 exporter 정책을 더 분명히 두는 편이 좋다.

```ts
// instrumentation.ts
import { registerOTel } from '@vercel/otel'

export function register() {
  registerOTel({
    serviceName: 'web-hr',
    attributes: {
      'deployment.environment': process.env.NODE_ENV ?? 'development',
      'service.namespace': 'frontend',
      'service.version': process.env.NEXT_PUBLIC_APP_VERSION ?? 'unknown',
    },
  })
}
```

핵심은 여기서 끝내지 않는 것이다. `instrumentation.ts`가 있어도 실제로 span 품질이 나쁘면 운영 가치는 낮다. 부트스트랩은 시작일 뿐이고, 중요한 건 **어떤 경계에 어떤 수동 계측을 추가하느냐**다.

---

## 핵심 개념 2: 자동 계측만으로는 부족하고, 수동 span은 "비즈니스 경계"에 맞춰야 한다

OpenTelemetry를 붙이면 어느 정도 자동 계측이 가능하다.

- inbound HTTP 요청
- outbound fetch / HTTP 클라이언트 호출
- 일부 DB 드라이버 호출
- 런타임 기본 span

이건 분명히 유용하다. 하지만 자동 계측만으로는 중요한 질문에 답하기 어렵다.

예를 들어 아래 차이는 자동 계측이 잘 설명해주지 못한다.

- 외부 API가 느린 것인가, 우리가 재시도를 세 번 해서 느린 것인가
- DB 쿼리가 느린 것인가, 권한 체크 쿼리와 본문 조회 쿼리가 여러 번 중복된 것인가
- 저장 액션이 느린 것인가, 저장 후 재렌더 fetch가 느린 것인가
- 같은 `/api/orders` 요청인데 왜 어떤 건 200ms고 어떤 건 4초인가

그래서 수동 span이 필요하다. 다만 아무 데나 넣으면 안 된다.

### 수동 span을 넣기 좋은 경계

#### 1) 비즈니스 use case 시작/종료

- `publish-post`
- `approve-leave-request`
- `create-payment-intent`
- `sync-candidate-profile`

#### 2) 외부 의존성 의미 단위

- `cms.fetch-draft-post`
- `search.reindex-post`
- `slack.send-alert`

#### 3) 비싼 조합 로직

- 권한 확인 + 멤버십 조회 + feature flag 조회
- 여러 DB/HTTP 결과를 합치는 대시보드 집계

#### 4) 재시도/백오프 래퍼

- 같은 HTTP 호출이 왜 길어졌는지 드러내기 위해

### 수동 span을 넣지 말아야 할 곳

- 단순 getter/setter 수준의 너무 작은 함수
- span 이름이 도메인 의미 없이 `step1`, `processData` 같은 곳
- 성능 영향보다 노이즈가 더 큰 루프 내부

즉 기준은 단순하다.

> **자동 계측은 인프라 경계를, 수동 계측은 도메인 경계를 드러내야 한다.**

---

## 핵심 개념 3: 좋은 span 이름은 기술 스택이 아니라 운영 질문에 답할 수 있어야 한다

트레이스를 붙였는데도 여전히 도움이 안 되는 팀은 span 이름이 나쁘다.

예를 들면 이런 식이다.

- `handleRequest`
- `fetchData`
- `dbCall`
- `process`

이 이름들은 코드 작성자에게는 익숙해도, 장애 상황에서는 거의 쓸모가 없다.

좋은 span 이름은 보통 아래 둘 중 하나다.

### 1) 사용자/도메인 행동 중심

- `post.publish`
- `leave-request.approve`
- `payroll.preview.generate`
- `candidate.resume.parse`

### 2) 외부 시스템 상호작용 중심

- `cms.get-post-by-slug`
- `prisma.member.update`
- `authz.check-project-access`
- `queue.export-job.enqueue`

이렇게 두면 나중에 trace를 보며 바로 질문이 가능해진다.

- 어디서 시간이 가장 많이 쓰였는가
- 어떤 도메인 작업이 자주 실패하는가
- 어떤 외부 시스템 때문에 대시보드가 흔들리는가

### 권장 네이밍 규칙

- `도메인.행동`
- `시스템.동작`
- 필요하면 `도메인.행동.세부단계`

예:

- `post.publish.validate-input`
- `post.publish.update-db`
- `post.publish.revalidate-cache`
- `post.publish.enqueue-search-sync`

이 규칙의 장점은 span만 봐도 작업 순서가 읽힌다는 점이다.

---

## 핵심 개념 4: 속성(attribute)은 많이 넣는 것보다 "필터링과 상관관계에 필요한 것"만 일관되게 넣는 편이 낫다

span을 만들면 이것저것 다 넣고 싶어진다.

- user id
- email
- slug
- tenant id
- post title
- raw payload
- SQL 결과 건수
- entire request body

이렇게 가면 금방 두 가지 문제가 생긴다.

1. 개인정보/민감정보가 추적 시스템으로 과도하게 흘러간다
2. 검색과 집계에 진짜 필요한 키가 오히려 묻힌다

실무적으로는 아래처럼 최소 핵심 속성을 일관되게 두는 편이 좋다.

### 요청 공통

- `app.route`
- `app.request_id`
- `app.tenant_id`
- `enduser.id` 또는 내부 사용자 식별자
- `http.method`
- `http.status_code`

### 도메인 작업

- `app.action`
- `app.resource_id`
- `app.resource_type`
- `app.result` (`success`, `retry`, `validation_error` 등)

### 외부 의존성

- `peer.service`
- `http.url` 또는 정규화된 endpoint label
- `net.peer.name`
- `db.system`
- `db.operation`

### 넣지 않는 편이 좋은 것

- 이메일, 전화번호, 주민번호 같은 직접 식별 정보
- 자유 텍스트 본문 전체
- 인증 토큰, 쿠키 값, Authorization 헤더
- 너무 큰 payload 원문

좋은 원칙 하나는 이렇다.

> **attribute는 디버깅을 위해 남기되, 원문 데이터 저장소로 쓰지 않는다.**

필요하면 원문은 애플리케이션 로그나 별도 감사 저장소에 남기고, trace에는 검색 가능한 식별자만 넣는다.

---

## 핵심 개념 5: Route Handler와 Server Action은 같은 "서버 작업"처럼 보여도 관측 포인트가 다르다

Next.js 운영에서 자주 헷갈리는 부분이다. 둘 다 서버에서 실행되지만, 추적 포인트는 꽤 다르다.

### Route Handler에서 특히 봐야 할 것

- HTTP 메서드와 경로
- 인증 방식(웹훅 서명, 세션, 토큰)
- 응답 코드와 latency
- 외부 호출 fan-out
- body size, upload/download 성격

### Server Action에서 특히 봐야 할 것

- 어떤 UI 액션에서 호출됐는가
- mutation 전 검증/인가 단계
- DB 트랜잭션 시간
- 후속 revalidation 시간
- action 후 재렌더 fetch 비용

즉 Route Handler는 API 서버에 가깝고, Server Action은 **UI mutation과 후속 서버 렌더가 결합된 경계**에 더 가깝다.

그래서 Server Action에서는 아래 같은 span 구조가 특히 유용하다.

```ts
'use server'

import { trace } from '@opentelemetry/api'

export async function publishPost(input: { postId: string }) {
  return await trace.getTracer('next-app').startActiveSpan('post.publish', async (span) => {
    span.setAttribute('app.resource_type', 'post')
    span.setAttribute('app.resource_id', input.postId)

    try {
      await validatePublishRequest(input)
      await updatePostStatus(input.postId)
      await revalidatePostViews(input.postId)

      span.setAttribute('app.result', 'success')
      return { ok: true }
    } catch (error) {
      span.recordException(error as Error)
      span.setAttribute('app.result', 'error')
      throw error
    } finally {
      span.end()
    }
  })
}
```

여기서 포인트는 단순히 action 하나를 감쌌다는 게 아니다.

- 어떤 리소스에 대한 action인지 명확하다
- 실패 시 exception이 trace에 남는다
- 이후 하위 span이 있으면 publish 흐름 아래에 묶인다

실무에서는 여기에 세부 span을 더 나눌 수 있다.

- `post.publish.authorize`
- `post.publish.tx`
- `post.publish.revalidate`
- `post.publish.enqueue-index-sync`

이 정도면 "왜 느린지"가 꽤 선명해진다.

---

## 핵심 개념 6: 외부 fetch는 단순히 자동 추적되게 두는 것보다, 재시도와 실패 분류를 span에 드러내야 한다

대부분의 Next.js 앱은 결국 외부 HTTP 호출을 많이 한다.

- 내부 BFF
- CMS
- 결제 API
- 이메일 발송 API
- AI API
- 파일 저장소 서명 URL API

자동 계측만 켜두면 HTTP span은 잡힌다. 하지만 실무에서 진짜 궁금한 건 더 구체적이다.

- 200이긴 한데 왜 4초가 걸렸는가
- timeout 뒤 재시도해서 성공한 것인가
- 429를 맞고 backoff를 탔는가
- upstream이 느린 것인가, 우리 쪽 circuit breaker가 지연시킨 것인가

이런 건 래퍼 레벨 수동 span이나 event가 훨씬 낫다.

```ts
import { trace } from '@opentelemetry/api'

const tracer = trace.getTracer('next-app')

export async function fetchWithRetry(url: string, init?: RequestInit) {
  return tracer.startActiveSpan('cms.get-post-by-slug', async (span) => {
    let attempt = 0
    let lastError: unknown

    while (attempt < 3) {
      attempt += 1
      try {
        span.addEvent('http.attempt', { attempt })
        const res = await fetch(url, init)
        span.setAttribute('http.status_code', res.status)

        if (!res.ok && res.status >= 500) {
          throw new Error(`upstream error: ${res.status}`)
        }

        span.setAttribute('app.retry_count', attempt - 1)
        return res
      } catch (error) {
        lastError = error
        if (attempt >= 3) break
        await new Promise((resolve) => setTimeout(resolve, attempt * 200))
      }
    }

    span.recordException(lastError as Error)
    span.setAttribute('app.result', 'retry_exhausted')
    throw lastError
  })
}
```

이렇게 하면 단순 HTTP latency가 아니라 **재시도 포함 실제 비용**이 드러난다.

---

## 핵심 개념 7: DB 계측은 "쿼리 문자열 수집"보다 트랜잭션 경계와 N+1 신호를 먼저 잡는 편이 실용적이다

관측을 처음 붙일 때 DB에서 가장 흔한 욕심은 SQL을 전부 보고 싶다는 것이다. 물론 도움이 될 수 있다. 하지만 운영 관점에서는 우선순위가 조금 다르다.

### 먼저 잡아야 할 것

1. 어떤 요청/액션에서 DB 시간이 긴가
2. 읽기 쿼리가 몇 번 호출됐는가
3. 트랜잭션이 얼마나 오래 유지되는가
4. 동일 엔티티 조회가 반복되는가
5. 외부 API 대기와 DB 락 대기가 어떻게 겹치는가

예를 들어 Server Action 하나가 느린데 실제 원인은 이럴 수 있다.

- 권한 확인 쿼리 3개
- 본문 조회 2개
- 중복 존재 확인 2개
- 실제 update 1개
- 저장 후 재조회 2개

즉 느린 원인이 한 쿼리의 절대 시간보다 **요청당 호출 패턴**일 때가 많다.

### 실무 권장 포인트

- span attribute로 `db.system`, `db.operation`, `app.model` 정도를 남긴다
- raw SQL 전체 수집은 민감도와 비용을 고려해 제한한다
- 트랜잭션 wrapper에 별도 span을 둔다
- 요청별 query count, total db duration 메트릭을 같이 본다

예시:

```ts
import { trace } from '@opentelemetry/api'

const tracer = trace.getTracer('next-app')

export async function withTracedTransaction<T>(name: string, fn: () => Promise<T>): Promise<T> {
  return tracer.startActiveSpan(name, async (span) => {
    span.setAttribute('db.system', 'postgresql')
    span.setAttribute('app.tx', true)

    try {
      return await fn()
    } catch (error) {
      span.recordException(error as Error)
      throw error
    } finally {
      span.end()
    }
  })
}
```

이런 구조는 나중에 "발행 액션이 느리다"를 "발행 액션 중 DB 트랜잭션이 2.8초를 먹는다" 수준으로 바꿔 준다.

---

## 핵심 개념 8: 로그는 trace를 대체하지 못하고, trace id가 없는 구조화 로그는 반쪽짜리다

Next.js 앱에서 여전히 로그는 중요하다. 다만 로그만으로는 한 요청을 따라가기 어렵다.

예를 들어 이런 로그가 있다고 하자.

- `publish start`
- `db updated`
- `cms sync failed`
- `publish complete`

겉보기엔 충분해 보이지만, 실제 운영에서는 문제가 많다.

- 어느 요청의 로그인지 모른다
- 같은 시각 다른 사용자의 요청과 섞인다
- 외부 HTTP span, DB span과 연결되지 않는다
- 에러 모니터링에서 본 stack trace와 같은 사건인지 확인이 어렵다

그래서 구조화 로그에는 최소한 trace/span 상관관계 키를 넣는 편이 좋다.

### 권장 로그 필드

- `trace_id`
- `span_id`
- `request_id`
- `tenant_id`
- `user_id` 또는 내부 actor id
- `route`
- `action`
- `result`

예:

```ts
logger.info('post publish completed', {
  trace_id,
  span_id,
  request_id,
  tenant_id,
  actor_id,
  post_id,
  result: 'success',
})
```

이렇게 하면 운영자가 trace 화면에서 로그로, 로그에서 trace 화면으로 왕복할 수 있다.

### 왜 중요한가

trace는 흐름을 보여주고, 로그는 맥락을 설명한다.

- trace만 있으면 왜 실패했는지 텍스트 설명이 부족할 수 있다
- 로그만 있으면 어느 하위 호출이 병목인지 모른다

둘을 같은 상관관계 키로 묶어야 진짜 운영 도구가 된다.

---

## 핵심 개념 9: 에러 관측은 500 개수보다 "어느 경계에서 어떤 분류로 실패했는가"가 더 중요하다

에러 모니터링을 처음 붙이면 보통 상태 코드나 uncaught exception 수부터 본다. 물론 필요하다. 하지만 Next.js 실무에서는 이걸로 부족하다.

예를 들어 같은 500이어도 운영 의미는 다르다.

- 외부 CMS timeout
- 권한 검증 실패를 잘못 500으로 매핑한 경우
- DB unique conflict를 예외 처리 못한 경우
- 캐시 무효화 이후 재렌더 fetch가 실패한 경우
- Server Action 내부 validation 오류가 boundary를 잘못 타고 올라간 경우

그래서 span에는 결과 분류를 남기고, 에러도 가능한 한 경계별로 맵핑하는 편이 좋다.

### 예시 분류

- `validation_error`
- `authorization_denied`
- `upstream_timeout`
- `upstream_5xx`
- `db_conflict`
- `retry_exhausted`
- `unexpected_error`

이런 분류가 있으면 단순 에러 건수보다 훨씬 실용적인 질문이 가능하다.

- 최근 저장 실패 증가가 validation UX 문제인가
- CMS 장애 때문에 preview 화면만 느린가
- DB 충돌이 특정 action에만 몰리는가
- retry가 성공해서 겉으로는 200이지만 실제 latency를 악화시키는가

---

## 실무 예시 1: 게시글 발행 Server Action을 end-to-end로 추적하기

상황을 가정해 보자.

- 관리자 화면에서 게시글 발행 버튼을 누른다
- 권한을 확인한다
- DB 상태를 `draft -> published`로 바꾼다
- 검색 인덱스를 갱신한다
- 캐시를 무효화한다
- 감사 로그를 남긴다

사용자 관점에서는 버튼 하나지만, 관측해야 할 포인트는 꽤 많다.

### 권장 span 구조

- `post.publish`
  - `post.publish.authorize`
  - `post.publish.tx`
    - `db.post.update`
    - `db.audit-log.insert`
  - `post.publish.search-index.sync`
  - `post.publish.revalidate`

### 예시 코드

```ts
'use server'

import { trace } from '@opentelemetry/api'
import { revalidatePath, revalidateTag } from 'next/cache'

const tracer = trace.getTracer('next-app')

export async function publishPost(input: { postId: string; slug: string }) {
  return tracer.startActiveSpan('post.publish', async (span) => {
    span.setAttribute('app.resource_type', 'post')
    span.setAttribute('app.resource_id', input.postId)

    try {
      await tracer.startActiveSpan('post.publish.authorize', async (child) => {
        await requirePermission('post:publish')
        child.end()
      })

      await tracer.startActiveSpan('post.publish.tx', async (child) => {
        await db.$transaction(async (tx) => {
          await tx.post.update({
            where: { id: input.postId },
            data: { status: 'PUBLISHED' },
          })

          await tx.auditLog.create({
            data: { action: 'post.publish', resourceId: input.postId },
          })
        })
        child.end()
      })

      await tracer.startActiveSpan('post.publish.search-index.sync', async (child) => {
        await syncPostToSearch(input.postId)
        child.end()
      })

      await tracer.startActiveSpan('post.publish.revalidate', async (child) => {
        revalidateTag(`post:${input.postId}`)
        revalidatePath(`/admin/posts/${input.postId}`)
        revalidatePath(`/blog/${input.slug}`)
        child.end()
      })

      span.setAttribute('app.result', 'success')
      return { ok: true }
    } catch (error) {
      span.recordException(error as Error)
      span.setAttribute('app.result', 'error')
      throw error
    } finally {
      span.end()
    }
  })
}
```

### 이 구조로 얻는 것

- 느린 원인이 권한 확인인지, DB인지, 검색 동기화인지 분리된다
- 검색 동기화 실패만 반복되는지 볼 수 있다
- 캐시 무효화까지 action latency에 포함되는지 판단할 수 있다
- 추후 검색 동기화를 비동기 queue로 빼야 할지 근거가 생긴다

---

## 실무 예시 2: Route Handler 기반 파일 업로드 API에서 병목을 분리하기

파일 업로드는 특히 자주 오해된다.

- 사용자는 "업로드 API가 느리다"고 느낀다
- 실제로는 파일 파싱, 서명 URL 발급, 저장소 업로드, 메타데이터 DB 저장이 섞여 있다

### 나누어 볼 경계

- `upload.prepare`
- `storage.presign`
- `storage.put-object`
- `upload.metadata.save`

만약 presigned URL 방식이라면, 실제 대용량 업로드는 브라우저가 저장소로 직접 보낼 수도 있다. 이 경우 Route Handler에서 봐야 할 것은 파일 전송 시간이 아니라 **서명 URL 발급과 메타데이터 저장 지연**일 수 있다.

즉 trace를 붙이면 이런 질문이 가능해진다.

- 서버가 느린가, 브라우저-스토리지 구간이 느린가
- 업로드 API timeout은 진짜 서버 처리 시간이 원인인가
- 같은 업로드 기능인데 특정 테넌트만 메타데이터 저장이 느린가

관측이 없으면 전부 "업로드 느림"으로 뭉개진다.

---

## 실무 예시 3: 대시보드 SSR이 느릴 때 캐시 문제와 upstream 문제를 분리하기

대시보드 페이지 하나가 느리다고 해서 원인이 하나인 경우는 드물다.

예를 들어 `/app/[tenant]/dashboard`가 있다고 하자.

- incidents 집계
- deployments 집계
- billing usage
- 현재 사용자 권한
- feature flag

이 다섯 개를 서버에서 동시에 읽는다.

이때 trace를 보면 보통 세 부류가 나온다.

### 1) 한 upstream이 압도적으로 느리다

예: billing usage API가 2.4초

→ 이 경우는 캐시, timeout, precompute를 검토할 수 있다.

### 2) 각각은 200~300ms인데 너무 많다

→ fan-out 개수 축소, 집계 API 통합, BFF 도입, request memoization 점검이 필요하다.

### 3) fetch는 빠른데 전체 렌더가 느리다

→ Suspense 경계, RSC 트리 구조, 중복 fetch, 직렬 await가 문제일 수 있다.

즉 trace는 단순 latency 측정이 아니라 **최적화 방향을 결정하는 지도**가 된다.

---

## 실무 예시 4: webhook 처리에서 "실패했는데 재시도해야 하는가"를 추적 가능하게 만들기

웹훅은 observability가 특히 중요하다.

- 외부 서비스는 재시도를 한다
- 우리도 멱등 처리를 해야 한다
- 2xx를 너무 빨리 반환하면 실제 후처리 실패가 묻힐 수 있다
- 반대로 오래 붙잡으면 상대방 timeout과 중복 전송이 늘어난다

이때 trace에서 보고 싶은 건 단순 status code가 아니다.

- 서명 검증에 걸린 시간
- 이벤트 중복 판단 시간
- DB 저장 여부
- 큐 적재 여부
- 최종 ack 시점

### 권장 span 구조

- `webhook.github.push.receive`
  - `webhook.verify-signature`
  - `webhook.deduplicate`
  - `webhook.enqueue`

이 구조가 있으면 웹훅 장애를 훨씬 더 정확히 나눌 수 있다.

- 서명 검증 실패 증가
- dedup 저장소 병목
- 큐 적재 실패
- 외부는 재시도 중인데 우리는 이미 중복 처리 중

---

## 트레이드오프: observability는 공짜가 아니고, 특히 샘플링·비용·개인정보 사이 균형이 중요하다

관측은 많이 붙일수록 좋아 보이지만 실제로는 비용과 위험이 함께 온다.

### 1) span을 너무 많이 만들면 노이즈와 비용이 커진다

- 저장 비용 증가
- 검색 속도 저하
- 정말 중요한 span이 묻힘

### 2) attribute를 너무 자세히 넣으면 개인정보 위험이 생긴다

- email, 본문, 토큰, 주소 같은 값이 실수로 올라갈 수 있다
- 추적 시스템 권한 범위가 앱 운영보다 넓을 수도 있다

### 3) 샘플링을 너무 보수적으로 하면 재현 어려운 느린 요청을 놓친다

- 평균 요청만 보이고 tail latency 원인이 사라진다

### 4) 샘플링을 너무 공격적으로 하면 비용이 빠르게 커진다

- 특히 고QPS Route Handler나 공개 페이지는 부담이 크다

### 내 추천 기준

- 에러 trace는 가급적 높은 비율로 보존
- 정상 trace는 경로별 차등 샘플링
- 고가치 mutation, 결제, 게시, 승인 흐름은 샘플링 우대
- 정적 공개 페이지는 메트릭 중심, trace는 상대적으로 보수적

즉 observability도 전부 동일한 엄격도로 다루기보다 **업무 중요도와 디버깅 가치에 따라 차등 설계**하는 편이 현실적이다.

---

## 흔한 실수 1: 자동 계측이 있으니 수동 계측은 필요 없다고 생각한다

자동 계측은 시작으로는 좋다. 하지만 운영에서 필요한 건 비즈니스 질문에 답하는 trace다.

- 어떤 action이 느린가
- 어떤 권한 검사 때문에 지연이 늘어나는가
- 어떤 외부 동기화가 mutation latency를 잡아먹는가

이건 수동 span 없이는 잘 안 보인다.

---

## 흔한 실수 2: 수동 span을 너무 작은 함수에 남발한다

모든 함수마다 span을 달면 trace가 예뻐 보일 수는 있다. 하지만 운영 가치는 오히려 떨어진다.

- 노이즈 증가
- 부모-자식 구조 해석 어려움
- 저장 비용 증가

span은 "중요한 경계"에 둬야 한다. 함수 수집이 목적이 아니다.

---

## 흔한 실수 3: trace와 로그의 상관관계 키가 없다

이 경우 제일 답답하다.

- trace 화면에서 실패 span은 보이는데 실제 비즈니스 맥락 로그를 못 찾는다
- 로그엔 에러가 있는데 어느 trace와 연결되는지 모른다

`trace_id`, `span_id`, `request_id`를 구조화 로그에 넣는 것만으로 운영성이 크게 달라진다.

---

## 흔한 실수 4: attribute에 민감정보를 너무 많이 넣는다

관측이 잘 되는 것과 개인정보가 과도하게 퍼지는 것은 다르다.

- 이메일 원문
- 본문 전문
- access token
- 쿠키 값

이런 건 trace에 남기지 않는 편이 좋다. 디버깅 가치보다 위험이 더 크다.

---

## 흔한 실수 5: 평균 latency만 보고 tail latency를 놓친다

운영 체감은 평균보다 p95, p99에서 더 많이 깨진다.

- 평소 200ms인데 가끔 6초
- 대부분 빠른데 특정 tenant만 느림
- 성공률은 높지만 retry 때문에 특정 action이 흔들림

trace는 바로 이 tail 원인을 보기 위해 필요한 경우가 많다. 평균만 보면 캐시 넣고 끝났다고 착각하기 쉽다.

---

## 흔한 실수 6: Server Action 이후 재렌더 비용을 따로 보지 않는다

Next.js에서는 mutation 자체보다, 그 뒤에 따라오는 재검증과 재렌더 fetch가 더 길 수 있다. 그런데 많은 팀이 action 함수 본문만 보고 끝낸다.

이 경우 사용자는 여전히 느리다고 느끼는데 서버팀은 "DB update는 100ms인데요"라고 답하게 된다.

즉 mutation observability는 **쓰기 자체 + 후속 UI 재구성 비용**까지 봐야 맞다.

---

## 체크리스트

Next.js 서비스에 observability를 붙이거나 점검할 때는 아래 항목을 먼저 보면 좋다.

### 부트스트랩

- [ ] `instrumentation.ts`에서 서비스 이름, 환경, 버전이 등록되는가
- [ ] exporter와 샘플링 정책이 환경별로 분리되는가
- [ ] 자동 계측이 켜져 있어 inbound/outbound 기본 span이 보이는가

### 수동 span 설계

- [ ] Server Action, Route Handler, 주요 use case에 상위 span이 있는가
- [ ] span 이름이 `도메인.행동` 또는 `시스템.동작` 규칙을 따르는가
- [ ] 너무 작은 함수에 span을 남발하지 않는가

### 속성/보안

- [ ] `tenant_id`, `request_id`, `resource_id` 같은 상관관계 키가 일관되게 들어가는가
- [ ] 이메일, 토큰, 본문 전문 같은 민감정보를 span attribute에 넣지 않는가
- [ ] 에러 분류 값이 `validation_error`, `upstream_timeout`처럼 운영 의미를 가지는가

### 로그 연계

- [ ] 구조화 로그에 `trace_id`, `span_id`, `request_id`가 포함되는가
- [ ] trace 화면에서 관련 로그를 찾을 수 있는가
- [ ] 동일 요청의 로그와 span이 시간상 자연스럽게 이어지는가

### 성능 운영

- [ ] 평균뿐 아니라 p95/p99 latency를 경로와 action 기준으로 보는가
- [ ] retry가 성공해도 latency를 악화시키는 경로를 추적할 수 있는가
- [ ] DB 시간, 외부 HTTP 시간, 렌더 시간 중 무엇이 큰지 분리해서 볼 수 있는가
- [ ] Server Action 이후 재렌더 비용을 별도로 관측하는가

### 장애 대응

- [ ] 웹훅, 업로드, 결제, 발행 같은 고가치 흐름은 우선 샘플링되는가
- [ ] 에러 trace가 너무 많이 버려지지 않는가
- [ ] trace 없이도 핵심 경로의 메트릭과 경보가 존재하는가

---

## 바로 적용할 최소 순서

이미 운영 중인 Next.js 서비스라면 아래 순서가 가장 현실적이다.

1. `instrumentation.ts`로 OTel 부트스트랩을 먼저 고정한다
2. 상위 3개 핵심 경로에만 수동 span을 추가한다
   - 예: 로그인, 저장, 발행
3. 구조화 로그에 `trace_id`, `request_id`를 연결한다
4. 외부 fetch 래퍼와 DB 트랜잭션 래퍼에 공통 span을 둔다
5. p95가 높은 Route Handler와 Server Action부터 세부 span을 늘린다
6. 마지막으로 샘플링과 attribute 정리를 다듬는다

처음부터 모든 경로를 완벽히 추적하려 하기보다, **가장 자주 느리거나 가장 중요한 흐름을 증거 기반으로 설명할 수 있게 만드는 것**이 먼저다.

---

## 한 줄 정리

> **Next.js observability의 핵심은 `instrumentation.ts`로 계측 기반을 열고, Route Handler·Server Action·외부 fetch·DB 트랜잭션을 하나의 trace로 이어서, 로그와 메트릭까지 같은 상관관계 키로 묶어 "어디서 왜 느린가"를 감이 아니라 증거로 답할 수 있게 만드는 데 있다.**
