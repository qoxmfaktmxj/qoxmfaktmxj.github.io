---
layout: post
title: "Next.js App Router CSP 실전: nonce, 동적 렌더링, 정적 캐시의 충돌을 배포 전에 해결하기"
date: 2026-11-04 11:40:00 +0900
categories: [nextjs]
tags: [study, nextjs, app-router, csp, nonce, security, dynamic-rendering, static-rendering, cache, proxy]
permalink: /nextjs/2026/11/04/study-nextjs-csp-nonce-dynamic-rendering-rollout.html
---

## 문제 상황: 헤더 한 줄을 추가했는데 화면이 하얗게 뜬다

Next.js App Router 서비스에 `Content-Security-Policy`(CSP)를 적용하는 일은 보안 헤더를 더하는 작업처럼 보인다. 그러나 운영 중인 서비스에는 빌드 시 생성한 HTML, 요청마다 렌더링하는 페이지, Next.js 런타임 스크립트, 서드파티 태그, CDN 캐시가 함께 존재한다. 이 경계를 구분하지 않고 `script-src 'self'`를 일괄 적용하면 브라우저는 인라인 부트스트랩 스크립트를 거부하고, 서버 HTML은 보이지만 상호작용이 멈출 수 있다.

반대로 오류를 피하려고 `script-src 'self' 'unsafe-inline'`을 넣으면 인라인 스크립트에 대한 CSP의 방어력이 크게 약해진다. `nonce`를 쓰면 모든 문제가 해결될 것 같지만, 이번에는 정적 HTML의 성질과 충돌한다. **응답마다 달라야 하는 nonce를 빌드 시점에 만든 HTML에 안전하게 심을 수 없기 때문이다.**

이 글은 "CSP 문자열을 어디에 적나"보다 다음 설계 질문을 다룬다.

1. CSP가 보호하는 대상과 보호하지 못하는 대상은 무엇인가?
2. Next.js가 nonce를 어떤 요청 헤더에서 추출하고 어디에 적용하는가?
3. 왜 정적 페이지·ISR·CDN 캐시와 요청별 nonce를 그대로 결합할 수 없는가?
4. 보안 요구사항을 유지하면서 일부 경로만 동적으로 운영하려면 어떻게 나눌까?
5. 배포 전에 어떤 실패를 실제 응답과 브라우저에서 검증해야 할까?

예시는 **App Router 및 `proxy.ts`를 쓰는 현재 Next.js 문서 기준**이다. 오래된 버전에서 `middleware.ts`를 쓰는 프로젝트라면 파일 이름과 지원 API를 해당 버전 문서와 대조해야 한다. 코드의 도메인·정책은 예시이며, 운영 서비스의 실제 리소스 출처에 맞게 조정해야 한다.

---

## 1. 먼저 CSP를 "허용 출처 목록" 이상으로 이해한다

CSP는 브라우저에 전달하는 실행·로드 제한 정책이다. 보통 HTTP **응답** 헤더로 전달한다.

```http
Content-Security-Policy: default-src 'self'; script-src 'self'; object-src 'none'
```

`default-src`는 더 구체적인 fetch directive가 없을 때의 기본값이다. `script-src`는 JavaScript의 실행·로드 정책을 담당한다. `object-src 'none'`은 오래된 플러그인 계열 리소스를 막는다. 하지만 `default-src`가 모든 지시어의 대체값은 아니다. 예를 들어 문서를 다른 사이트가 iframe에 넣을 수 있는지를 제어하는 `frame-ancestors`는 별도로 명시해야 한다.

CSP를 데이터 검증이나 HTML 이스케이프의 대체재로 보면 안 된다. 사용자 입력이 DOM에 실행 가능한 형태로 삽입되지 않도록 만드는 것이 1차 방어이고, CSP는 그 방어가 실패했을 때 실행 경로를 더 제한하는 **심층 방어**다. 또한 CSP는 서버 측 권한 검사를 대신하지 않는다. 브라우저가 스크립트를 막았더라도 서버가 허가하지 않은 데이터 요청을 거절해야 한다.

### `self`만 허용했는데도 왜 깨질까?

Next.js는 페이지를 상호작용 가능한 상태로 만들기 위해 프레임워크 스크립트와 인라인 스크립트·스타일을 사용할 수 있다. 외부 JS 파일의 출처가 같은 도메인이라고 해도, **인라인 코드**는 별도의 허가가 없으면 엄격한 `script-src`에 막힌다. 개발 모드에서는 디버깅을 위해 필요한 정책이 프로덕션과 다를 수 있다. Next.js CSP 가이드는 개발 모드의 `'unsafe-eval'` 필요성을 별도로 설명하지만, 이를 프로덕션 정책에 그대로 복사할 이유는 없다.

브라우저 콘솔에서 아래와 같은 오류가 나면 "Next.js가 고장났다"가 아니라 실제로 적용된 CSP와 해당 태그를 먼저 비교해야 한다.

```text
Refused to execute inline script because it violates the following
Content Security Policy directive: "script-src 'self'".
```

---

## 2. nonce는 응답 단위 계약이다

Nonce(number used once)는 예측하기 어려운 값을 **요청마다 새로** 만들어 정책과 허용할 태그 양쪽에 넣는 방법이다.

```http
Content-Security-Policy: script-src 'self' 'nonce-abc123...'
```

```html
<script nonce="abc123..." src="/_next/static/chunks/app.js"></script>
```

브라우저는 정책의 `nonce-...`와 태그의 `nonce`를 비교한다. 값을 아는 서버가 렌더링한 태그만 허용하는 방식이다. 같은 HTML 문서 안의 허용된 스크립트들은 같은 nonce를 쓸 수 있지만, **다음 문서 응답에는 새 값을 써야 한다.**

흔한 오해가 세 가지 있다.

- `nonce`가 있다고 HTML 이스케이프가 불필요한 것은 아니다. 공격자가 사용자 입력을 통해 서버가 생성한 정상 태그의 `nonce` 속성까지 제어할 수 있다면 경계가 무너진다.
- 모든 인라인 코드에 nonce를 자동으로 붙이는 후처리 프록시는 위험하다. 공격자가 삽입한 스크립트에도 nonce를 붙여 줄 수 있기 때문이다.
- 정책 헤더에만 nonce가 있고 실제 스크립트 태그에는 없으면 실행되지 않는다. 반대도 마찬가지다.

### 요청 헤더와 응답 헤더를 모두 다루는 이유

Next.js 공식 가이드는 `proxy.ts`에서 nonce를 생성하고, **렌더러가 읽을 요청 헤더**에 CSP와 `x-nonce`를 넣은 뒤, **브라우저가 집행할 응답 헤더**에 CSP를 넣는 패턴을 제시한다. 둘은 역할이 다르다. 응답 헤더만 넣으면 브라우저에는 정책이 보이지만 서버 렌더링 시 Next.js가 같은 값을 읽어 태그에 반영하지 못할 수 있다. 요청 헤더만 넣으면 HTML에 nonce가 있어도 브라우저에 적용할 CSP가 없어진다.

이것을 "프록시가 두 번 헤더를 쓴다"고 보지 말고, **렌더러와 브라우저가 같은 정책을 공유하는 계약**으로 봐야 한다.

---

## 3. 작동 가능한 최소 패턴: Proxy에서 생성하고 동적 페이지에서 사용한다

아래 예시는 CSP를 적용할 경로에 대해 요청별 nonce를 만든다. 실제 서비스에서는 허용할 이미지·폰트·API·스크립트 출처를 리소스 인벤토리에 맞춰 조정한다.

```ts
// proxy.ts
import { NextRequest, NextResponse } from 'next/server'

export function proxy(request: NextRequest) {
  const nonce = Buffer.from(crypto.randomUUID()).toString('base64')
  const isDev = process.env.NODE_ENV === 'development'

  const policy = [
    "default-src 'self'",
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'${isDev ? " 'unsafe-eval'" : ''}`,
    `style-src 'self' 'nonce-${nonce}'`,
    "img-src 'self' data: blob:",
    "font-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
  ].join('; ') + ';'

  const requestHeaders = new Headers(request.headers)
  requestHeaders.set('Content-Security-Policy', policy)
  requestHeaders.set('x-nonce', nonce)

  const response = NextResponse.next({
    request: { headers: requestHeaders },
  })
  response.headers.set('Content-Security-Policy', policy)
  return response
}

export const config = {
  matcher: ['/dashboard/:path*'],
}
```

여기서는 `/dashboard`만 대상으로 삼았다. 한 번에 모든 페이지의 렌더링·캐시 정책을 바꾸지 않고 민감한 화면부터 적용할 수 있다. `/dashboard` 아래의 API나 정적 자산, 리다이렉트가 있다면 실제 경로 구조에 맞춰 matcher와 응답 헤더 적용 범위를 따로 검토해야 한다. 프록시의 matcher만 보고 보안 범위가 완성되었다고 가정하지 않는다.

`'strict-dynamic'`은 nonce로 신뢰한 스크립트가 로드하는 스크립트에 대한 정책 동작에 영향을 준다. 이를 쓸 때 `script-src 'self'`가 모든 브라우저에서 단순한 출처 허용 목록처럼 작동한다고 가정하면 안 된다. CSP 버전·브라우저 지원과 서드파티 로더의 동작을 함께 테스트한다. 최소 예시를 그대로 복사해 CDN 도메인만 추가하는 것으로 통합 테스트를 대체할 수 없다.

동적 페이지는 요청이 도착한 뒤 렌더링되도록 명시한다.

```tsx
// app/dashboard/page.tsx
import { connection } from 'next/server'
import { headers } from 'next/headers'
import Script from 'next/script'

export default async function DashboardPage() {
  await connection()
  const nonce = (await headers()).get('x-nonce') ?? undefined

  return (
    <main>
      <h1>운영 대시보드</h1>
      <p>서버에서 요청별 정책을 적용합니다.</p>
      <Script src="/dashboard-analytics.js" strategy="afterInteractive" nonce={nonce} />
    </main>
  )
}
```

`connection()`은 이 페이지가 실제 요청에 의존하도록 하는 명시적인 선택이다. `headers()`는 Proxy가 전달한 nonce를 사용자 코드에서 읽을 때 쓴다. Next.js는 요청 CSP의 `nonce-{value}` 패턴을 해석해 프레임워크가 생성한 스크립트 등에 nonce를 적용한다. 다만 사용자 코드의 스크립트, 서드파티 패키지, CSS-in-JS가 만드는 `<style>` 등은 각 통합 방식에 따라 별도 검증이 필요하다. 위 `/dashboard-analytics.js`는 예시 파일이며 실제 배포 시 파일을 제공해야 한다.

여기서 중요한 보안 경계는 `x-nonce` 값을 **클라이언트가 임의로 보낸 값으로 신뢰하지 않는 것**이다. Proxy는 매 요청마다 새 값을 생성해 요청 헤더를 덮어쓴다. 이 동작이 누락된 경로에서 `headers().get('x-nonce')`만 믿어서는 안 된다.

---

## 4. 정적 HTML과 nonce가 충돌하는 구조

정적 페이지는 빌드 시점에 HTML을 만든다. ISR은 만들어진 결과를 재사용하다가 재생성한다. CDN 역시 같은 HTML 응답을 여러 사용자에게 전달한다. 반면 nonce 기반 CSP는 요청 A와 요청 B의 값을 달리해야 한다.

```text
빌드 시점:       HTML에 nonce A가 들어감
요청 1:         응답 CSP에 nonce B가 들어감
브라우저 판정:   A != B → 스크립트 차단
```

혹은 CDN이 HTML과 CSP를 묶어 캐시하면 같은 nonce가 여러 요청에 재사용된다. 이는 "한 번만 쓰는 예측 불가능한 값"이라는 설계를 훼손한다. 헤더만 엣지에서 새로 발급하고 본문은 캐시하는 구성도 본문 스크립트와 헤더의 값이 달라져 실패한다.

Next.js 공식 CSP 가이드는 nonce를 사용할 페이지는 **동적 렌더링이 필요**하다고 명시한다. 정적 최적화와 ISR의 이점을 잃고, 요청별 렌더링 비용을 지불하게 된다. Partial Prerendering의 정적 셸도 요청별 nonce를 미리 담을 수 없으므로 그대로 결합할 수 없다.

### 선택지는 세 가지다

**A. 민감한 경로만 nonce + 동적 렌더링**

관리자 화면, 계정 설정, 결제 흐름처럼 엄격한 정책이 중요한 경로에 적용한다. 정적 마케팅 페이지까지 동적으로 바꾸지 않는다. 배포 전에는 해당 경로 전체(에러 화면, 리다이렉트, 로그인 전·후)를 테스트한다.

**B. 정적 경로에는 해시 기반 정책 검토**

내용이 안정적인 인라인 스크립트는 CSP 해시로 허용할 수 있다. 하지만 스크립트가 빌드마다 바뀌면 정책도 함께 갱신해야 한다. Next.js 문서의 Subresource Integrity(SRI) 옵션은 실험적 기능이며, App Router 정적 생성과의 대안으로 소개된다. SRI는 자산 무결성 검증이고 CSP nonce와 같은 개념이 아니다. 동적 생성 스크립트를 자동으로 해결한다고 간주하지 않는다.

**C. 정적 경로에 더 완화된 정책 사용**

필요한 경우 `unsafe-inline`을 포함한 정책으로 운영할 수 있지만, 엄격한 인라인 실행 차단 목표를 달성하지 못한다는 사실을 명시적으로 받아들여야 한다. "CSP를 설정했다"는 체크박스만으로 보안 수준을 판단하지 않는다.

| 경로 특성 | 유력한 선택 | 대가 |
| --- | --- | --- |
| 민감한 개인화 화면 | nonce + 동적 렌더링 | 요청별 서버 작업, 캐시 이점 감소 |
| 공개 정적 콘텐츠 | 해시/SRI 검토 또는 다른 정책 | 빌드 통합·정책 유지 관리 |
| 단순한 내부 화면 | 완화된 정책 후 단계적 강화 | 인라인 스크립트 차단 효과 약화 |

정답은 하나가 아니다. **정책 강도와 렌더링·캐시 구조를 함께 결정**해야 한다.

---

## 5. `next.config`의 정적 헤더와 Proxy의 동적 헤더를 혼동하지 않는다

`next.config.js`의 `headers()`는 경로별 **정적인 응답 헤더**를 선언할 때 유용하다. 그러나 파일을 빌드할 때 정해진 문자열만으로는 매 요청마다 새로운 nonce를 생성할 수 없다.

```js
// next.config.js: nonce가 필요 없는 정적 정책의 예
const csp = [
  "default-src 'self'",
  "object-src 'none'",
  "base-uri 'self'",
  "frame-ancestors 'none'",
].join('; ') + ';'

module.exports = {
  async headers() {
    return [
      {
        source: '/public/:path*',
        headers: [{ key: 'Content-Security-Policy', value: csp }],
      },
    ]
  },
}
```

이 예시는 `script-src`를 생략했으므로 `default-src`가 적용된다. 해당 경로에 인라인 스크립트가 있다면 여전히 차단될 수 있다. 설명을 위해 축약한 정책이지, 모든 공개 페이지가 이대로 작동한다는 뜻은 아니다.

설정 파일과 Proxy, CDN, 역방향 프록시에서 **같은 헤더를 중복 설정**하는 것도 조심해야 한다. 어떤 계층이 최종 응답을 덮어쓰는지, 두 정책이 동시에 전달되는지 확인해야 한다. CSP 헤더를 여러 개 받으면 브라우저는 정책을 각각 집행하므로, "뒤의 정책이 앞의 정책을 완화한다"고 기대할 수 없다. 반대로 프록시가 하나로 합치거나 덮어쓰면 의도한 제약이 사라질 수 있다. 최종 판단 기준은 설정 파일이 아니라 **실제 네트워크 응답**이다.

---

## 6. 서드파티 스크립트와 스타일은 별도 경계다

운영 서비스에서 가장 자주 깨지는 부분은 분석·결제·채팅 SDK다. 외부 스크립트 URL 하나만 정책에 추가해도 끝나지 않을 수 있다.

- SDK가 다시 다른 도메인의 스크립트를 로드하는가?
- inline bootstrap 코드를 요구하는가?
- `eval()`이나 동적 코드 생성을 쓰는가?
- `<style>`을 런타임에 삽입하는가?
- 이미지 beacon, `fetch`, WebSocket의 목적지는 어디인가?
- iframe을 생성하는가? 결제창은 `frame-src`를 따로 검토해야 한다.

`script-src`가 허용된다고 `connect-src`, `img-src`, `frame-src`, `style-src`까지 자동 허용되는 것은 아니다. `default-src` fallback과 각 directive의 실제 적용 대상을 확인한다. 특히 `style-src 'self' 'nonce-...'`를 적용한 뒤 CSS-in-JS 라이브러리가 만든 스타일 태그가 막힌다면, 모든 스타일을 `'unsafe-inline'`으로 허용하기 전에 해당 라이브러리의 nonce 전달 방법을 확인한다.

문제를 푸는 순서는 다음과 같다.

1. 브라우저가 보고한 **위반 지시어**(`effective-directive`)와 **차단된 URL**을 확인한다.
2. 그 리소스가 제품에 실제로 필요한지 결정한다.
3. 필요한 경우 최소 범위의 출처·nonce·해시 중 적합한 방법을 선택한다.
4. 정적/동적 경로와 프로덕션 빌드에서 다시 확인한다.

콘솔 오류가 사라질 때까지 도메인을 무작정 `*`로 늘리는 것은 정책 설계가 아니다.

---

## 7. 배포 전 검증: 헤더와 HTML이 같은 값을 쓰는가

CSP는 코드 리뷰만으로 확인하기 어렵다. 실제 프로덕션 빌드를 띄우고 응답을 관찰한다.

```bash
npm run build
npm run start
```

먼저 문서 응답을 헤더와 본문으로 나누어 저장한다. `curl -I`의 HEAD 응답만 보면 HTML 스크립트 태그와 비교할 수 없으므로 GET을 사용한다.

```bash
curl -sS -D /tmp/dashboard-headers-1.txt \
  -o /tmp/dashboard-body-1.html \
  http://localhost:3000/dashboard

curl -sS -D /tmp/dashboard-headers-2.txt \
  -o /tmp/dashboard-body-2.html \
  http://localhost:3000/dashboard
```

확인 항목은 네 가지다.

1. 두 응답의 `Content-Security-Policy`가 존재하는가?
2. 응답 1과 응답 2의 nonce 값이 다른가?
3. 각 HTML의 프레임워크 스크립트와 필요한 `<Script>`가 **그 응답의** 정책 값과 일치하는가?
4. 브라우저에서 초기 화면뿐 아니라 클라이언트 내비게이션·새로고침·로그인/로그아웃 후에도 오류가 없는가?

브라우저 DOM에서 nonce 속성을 볼 때는 주의한다. 브라우저는 nonce 값을 속성 조회에서 숨길 수 있으므로 `getAttribute('nonce')` 결과만으로 누락을 단정하지 말고, `element.nonce`, 원본 응답 HTML, 네트워크 패널을 함께 본다.

### 실패 재현 표

| 증상 | 우선 의심할 경계 | 확인 방법 |
| --- | --- | --- |
| 초기 HTML은 보이나 버튼이 작동하지 않음 | 인라인 런타임 스크립트 차단 | 콘솔 `script-src` 위반과 HTML nonce 비교 |
| 새로고침은 실패, 내부 이동은 성공 | 문서 응답의 정책/렌더링 차이 | 두 경로의 실제 문서 응답 비교 |
| 개발 모드만 성공 | 개발 전용 `'unsafe-eval'`·핫 리로드 차이 | `build` + `start`로 재현 |
| 일부 서버 인스턴스만 실패 | 캐시·프록시·배포 설정 불일치 | 인스턴스별 헤더/본문 쌍 비교 |
| 분석 스크립트만 실패 | 외부 출처 또는 `connect-src` 누락 | 차단 URL과 지시어 확인 |
| 정적 페이지에서만 실패 | 요청별 CSP와 빌드 HTML의 nonce 불일치 | 응답 헤더 값과 HTML 태그 값 비교 |

### Report-Only로 단계적 적용

바로 차단하기 전에 `Content-Security-Policy-Report-Only`로 위반을 관찰할 수 있다. 이는 **보고만 하고 차단하지 않는** 정책이다. 운영 중 필요한 리소스 출처를 파악하고 오탐을 줄이는 데 유용하지만, 보안 통제가 적용된 상태로 착각하면 안 된다. 보고 endpoint를 운영한다면 개인정보가 들어갈 수 있는 위반 보고 내용을 최소 수집·보관하고, 실제로 수신되는지 검증한다. 충분히 검증한 뒤 차단용 `Content-Security-Policy`로 전환한다.

CSP가 있어도 테스트는 끝나지 않는다. 사용자 입력이 포함된 화면의 이스케이프·DOM 삽입, 권한 없는 API 접근, 리다이렉트, CDN의 캐시 정책은 독립적으로 검증한다.

---

## 8. 설계 선택을 더 구체화한다: 페이지, 데이터, CDN 캐시는 같은 것이 아니다

"nonce를 쓰면 캐시를 전부 끈다"는 결론은 지나치게 넓다. 캐시의 대상이 무엇인지 나누어야 한다.

- **문서 HTML**: nonce가 포함된 스크립트 태그와 CSP 헤더가 한 쌍이다. 같은 HTML·nonce를 여러 요청에 재사용해서는 안 된다.
- **정적 자산**: 해시가 붙은 JS/CSS 파일은 별도 자산이다. 문서가 요청별로 렌더링된다고 해서 파일 내용까지 요청마다 다시 빌드하는 것은 아니다.
- **서버 데이터 조회 결과**: 애플리케이션의 캐시 정책은 별도 판단 대상이다. 공개 데이터를 적절한 범위에서 재사용할 수 있어도, 최종 HTML의 nonce 생성은 요청별로 해야 한다.
- **클라이언트 라우터 캐시**: 브라우저 내 탐색 경험과 HTTP 문서 응답 캐시는 동일하지 않다. 내부 이동만 시험하면 새 문서 요청의 헤더 오류를 놓친다.

따라서 운영 설계 문서에는 단순히 "캐시 끔"이 아니라 아래처럼 적는 것이 정확하다.

```text
/dashboard 문서 응답: 요청별 렌더링, 공유 CDN HTML 캐시 제외
/_next/static/*: 기존 불변 자산 캐시 유지
대시보드 데이터: 사용자·권한 범위가 섞이지 않도록 별도 캐시 정책 수립
```

이 구분이 없으면 보안 변경 하나로 모든 정적 자산의 캐시까지 무력화하거나, 반대로 개인화 HTML을 캐시하는 사고가 생긴다. 특히 CDN 규칙에서 `Cache-Control`을 강제로 바꾸는 경우, Next.js가 동적으로 렌더링했다는 사실만으로 안전하다고 믿지 말고 **실제 CDN 응답과 캐시 적중 로그**를 확인해야 한다.

### 경로별 정책을 나눌 때의 경계

예를 들어 공개 소개 페이지는 정적이고 `/dashboard`만 동적이라고 하자. 다음의 두 정책은 서로 다른 목적을 가진다.

```text
공개 페이지: 정적 HTML의 장점을 유지하는 CSP 설계
대시보드: 요청별 nonce를 포함한 엄격한 CSP
```

이때 `/dashboard`가 로그인 페이지로 리다이렉트된다면 그 리다이렉트 응답 자체의 헤더와 **최종 로그인 문서**의 정책을 각각 살펴야 한다. `/dashboard`의 Proxy matcher가 `/login`에는 적용되지 않을 수 있다. 로그인 페이지가 같은 서드파티 스크립트를 쓰면서 더 약한 정책에 놓여 있다면 보호 경계가 의도와 다르다. 반대로 공용 root layout에서 nonce를 무조건 읽어야 한다면 공개 페이지까지 동적으로 바뀌는지 검토해야 한다.

정책 범위는 URL 패턴만이 아니라 **렌더링 트리·리다이렉트 목적지·에러 경로**를 포함해 설계한다. `not-found`, `error`, 인증 실패 화면처럼 평소에는 보이지 않는 경로가 배포 후 첫 CSP 장애 지점이 되기 쉽다.

---

## 9. 정책을 좁힐 때는 directive별로 조사한다

CSP 위반을 한 덩어리로 보면 해결책이 무작정 `'unsafe-inline'`을 넣는 방향으로 흐른다. 실제로는 리소스 유형마다 다른 directive가 관여한다.

| 리소스/동작 | 주로 보는 directive | 흔한 실수 |
| --- | --- | --- |
| Next.js 및 업무 로직 JS | `script-src` | nonce 없는 인라인 코드, 서드파티 로더 누락 |
| CSS·런타임 스타일 | `style-src` | CSS-in-JS가 만든 `<style>`에 nonce 미전달 |
| API 호출·WebSocket | `connect-src` | API 도메인만 보고 WS 주소 누락 |
| 이미지·추적 픽셀 | `img-src` | CDN/`data:`/`blob:` 필요 여부를 확인하지 않음 |
| 웹 폰트 | `font-src` | CSS는 허용했지만 폰트 파일 출처는 차단 |
| iframe | `frame-src` | 결제·인증 iframe을 `script-src`로 해결하려 함 |
| 문서가 iframe에 포함되는 것 | `frame-ancestors` | `frame-src`와 반대 방향의 정책임을 혼동 |
| 폼 제출 대상 | `form-action` | 외부 결제·인증 제출 목적지 누락 |

`frame-src`는 **내 페이지가 삽입하는 iframe**의 출처를 제한한다. `frame-ancestors`는 **다른 페이지가 내 페이지를 삽입할 수 있는지** 제한한다. 둘은 이름이 비슷하지만 방향이 다르다. `connect-src`는 브라우저의 네트워크 연결을 제어하고 서버 측 `fetch`가 허가된 비즈니스 요청인지 판단하지 않는다.

`data:`와 `blob:`도 편의상 전체 directive에 넣지 않는다. 이미지 미리보기 같은 구체적 요구가 있을 때 `img-src`에만 허용하고, 스크립트에는 필요하지 않은 프로토콜을 열지 않는다. 외부 도메인은 와일드카드보다 정확한 호스트를 우선한다. 정책을 좁힐수록 운영 중 새 SDK를 붙일 때 검토가 필요하지만, 그 비용이 바로 정책의 가치이기도 하다.

### 개발 환경과 프로덕션 정책을 분리한다

개발 서버의 동작은 프로덕션 번들과 다르다. Next.js 문서가 개발 환경에서 `'unsafe-eval'`을 언급하는 이유도 디버깅 기능 때문이다. 이것을 해결할 때 코드에 무조건 `'unsafe-eval'`을 추가하지 않고, 환경별 표현을 명시한다.

```ts
const devOnly = process.env.NODE_ENV === 'development'
  ? " 'unsafe-eval'"
  : ''
```

프로덕션에서는 개발 전용 예외가 빠지는지 **빌드한 산출물**로 검증한다. `next dev`에서만 콘솔 오류가 없다는 것은 충분한 검증이 아니다. 정책 문자열의 공백·세미콜론, 호스트 스킴(`https:`), 하위 도메인, WebSocket 주소까지 실제 브라우저에서 확인해야 한다.

---

## 10. 실패 사례를 원인별로 추적한다

### 사례 A: 응답 헤더는 있는데 HTML 태그에는 nonce가 없다

Proxy가 `response.headers.set('Content-Security-Policy', ...)`만 실행하고 `NextResponse.next({ request: { headers: ... } })`에 수정된 요청 헤더를 전달하지 않았을 가능성을 먼저 본다. Next.js 렌더러가 요청 CSP를 볼 수 있는지 확인한다. 프록시를 통과하지 않는 경로나 정적 생성 페이지일 수도 있다.

수정 후에는 단순히 헤더가 있다는 것만 보지 않는다. GET 응답 본문의 스크립트 태그에 **같은 nonce**가 포함되는지 확인한다. 외부 프록시나 CDN이 Next.js 응답 헤더를 덮어쓰는지도 점검한다.

### 사례 B: 한 요청은 되는데 두 번째 요청부터 막힌다

캐시 계층이 헤더와 본문을 서로 다른 시점의 결과로 조합하거나, 빌드 HTML에 들어간 nonce를 반복 제공할 수 있다. 두 GET 응답의 정책 nonce와 본문 nonce를 각각 쌍으로 기록한다. `Age`, `Via`, CDN별 캐시 헤더, 서버 인스턴스 식별 로그를 함께 보면 어떤 계층에서 재사용이 일어나는지 찾기 쉽다.

이때 브라우저 캐시를 껐더니 문제가 사라졌다는 관찰만으로 해결됐다고 판단하지 않는다. 문제의 캐시가 브라우저인지 공유 CDN인지 구분해야 한다. 쿠키가 있는 요청과 없는 요청, 지역별 CDN POP, 여러 인스턴스에서 같은 검증을 반복한다.

### 사례 C: 일부 스크립트만 작동하고 결제 위젯이 비어 있다

스크립트 파일 자체는 허용되었지만 그 코드가 생성한 iframe 또는 API 연결이 차단될 수 있다. 콘솔의 첫 오류만 지우지 말고, 위젯이 실제로 쓰는 `frame-src`, `connect-src`, `img-src`를 조사한다. 결제사 문서의 권장 CSP 설정을 확인하되, 요구 도메인을 무조건 상위 와일드카드로 넓히지 않는다.

서드파티가 요구하는 인라인 bootstrap 코드가 있다면 해당 코드에 nonce를 전달할 수 있는지, 빌드 시 안정적인 코드라 해시가 더 나은지 비교한다. 라이브러리가 렌더링 이후 동적으로 생성하는 태그라면 그 라이브러리의 공식 CSP 지원 방식을 확인한다. 지원이 없다면 정책을 약화시키는 대가와 해당 기능의 필요성을 제품 차원에서 결정해야 한다.

### 사례 D: 콘솔 오류가 없는데 여전히 XSS가 가능하다

CSP는 모든 XSS를 자동으로 막는 보증서가 아니다. 정책이 넓거나, 신뢰된 스크립트가 위험한 DOM API로 악성 입력을 실행하거나, 서버가 신뢰하지 말아야 할 HTML을 그대로 출력하면 위험이 남는다. `dangerouslySetInnerHTML` 사용처, URL 기반 스크립트 로드, 사용자 입력의 HTML 변환 경로를 따로 감사한다. 권한 검증은 서버에서 수행한다.

특히 `nonce` 값을 서버가 만든 정상 `<script>`에만 부여해야 한다. 사용자 콘텐츠를 파싱한 뒤 모든 `<script>`에 일괄 nonce를 붙이는 로직은 공격 코드에도 실행 허가를 줄 수 있다. **nonce는 검증된 생성 경로의 결과**여야 한다.

---

## 11. 테스트 매트릭스를 기능·경로·응답 유형으로 만든다

보안 헤더 변경은 성공 경로만 통과하면 배포 후 깨지기 쉽다. 다음처럼 작은 매트릭스를 만들면 검증 범위를 눈으로 확인할 수 있다.

| 시나리오 | 문서 응답 확인 | 브라우저 동작 확인 |
| --- | --- | --- |
| 비로그인 사용자가 보호 경로 직접 열기 | 리다이렉트와 최종 로그인 문서 정책 | 로그인 폼 제출·오류 표시 |
| 로그인 사용자가 새로고침 | 정책/HTML nonce 일치 | 초기 hydration·이벤트 |
| 내부 링크로 보호 경로 이동 | 이후 새로고침의 문서 정책 | 라우터 탐색·데이터 갱신 |
| 권한 없는 하위 경로 | 오류/403 화면의 정책 | 접근 차단·UI 오류 없음 |
| 느린 API 또는 스트리밍 화면 | 최종 응답 헤더와 청크 | Suspense 전환·클라이언트 재개 |
| 서드파티 위젯 화면 | 해당 출처에 필요한 directive | iframe·API·추적 요청 |
| CDN 뒤 반복 요청 | `Age`/캐시 상태와 nonce 변경 | 지역·인스턴스별 동일 동작 |

검증 자동화를 만들 때는 "헤더 문자열에 `nonce-`가 포함된다"만 검사하는 테스트로 끝내지 않는다. **두 요청의 nonce가 달라야 하고, 각 응답의 태그와 헤더가 일치해야 한다**는 불변식을 검사한다. 애플리케이션 전체의 모든 스크립트 태그를 정규식 하나로 완벽히 파싱하려 하지 말고, 최소한 프레임워크 부트스트랩 태그와 직접 추가한 `Script`의 HTML을 확인한 뒤 브라우저 테스트로 보완한다.

릴리스 후에는 CSP 위반 보고의 급증, hydration 오류, 로그인 완료율, 주요 위젯 로드 성공률을 같이 본다. CSP Report-Only 데이터만 보면 사용자 영향이 없다고 착각할 수 있고, 브라우저 콘솔만 보면 서버·CDN 특정 경로를 놓칠 수 있다. 보안 정책과 제품 기능의 관측 지표를 함께 보는 것이 실무적인 배포 검증이다.

---

## 12. 운영 의사결정 체크리스트

실무에서 CSP 작업을 시작할 때는 구현보다 먼저 다음 계약을 문서화하는 편이 낫다.

- [ ] 어떤 경로가 엄격한 nonce 정책을 적용받는가? 에러·로그인·리다이렉트 경로도 포함했는가?
- [ ] 그 경로는 실제 요청마다 동적으로 렌더링되는가?
- [ ] CDN이나 프록시가 문서 HTML 또는 CSP 헤더만 독립적으로 캐시하지 않는가?
- [ ] Proxy에서 생성한 nonce가 서버 렌더러의 요청 헤더와 브라우저의 응답 헤더에 같은 값으로 전달되는가?
- [ ] 클라이언트가 보낸 `x-nonce`를 덮어쓰는가?
- [ ] 필요한 서드파티 출처와 동적 로더·스타일 삽입 방식을 조사했는가?
- [ ] 개발과 프로덕션 CSP의 차이를 의도적으로 관리하는가?
- [ ] 실제 프로덕션 빌드의 두 GET 응답에서 nonce의 일치·변경을 확인했는가?
- [ ] CSP 외에 입력 이스케이프와 서버 권한 검사를 유지하는가?

핵심은 헤더 문자열 자체가 아니다. **CSP의 신뢰 단위는 응답이고, Next.js의 렌더링·캐시 단위도 응답이다.** 두 단위를 일치시키지 않으면 엄격한 정책은 화면을 깨뜨리거나, 더 나쁘게는 보안을 강화했다는 잘못된 확신만 남긴다.

## 근거 자료

- [Next.js 공식 가이드: Content Security Policy](https://nextjs.org/docs/app/guides/content-security-policy) — Proxy nonce, 동적 렌더링 요구, 정적 생성과의 충돌, 개발/프로덕션 차이
- [Next.js 공식 문서: `headers` 설정](https://nextjs.org/docs/app/api-reference/config/next-config-js/headers) — 경로별 정적 응답 헤더의 동작
- [MDN: Content Security Policy](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CSP) — nonce·hash·Report-Only·CSP의 방어 범위
