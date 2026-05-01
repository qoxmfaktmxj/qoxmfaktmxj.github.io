---
layout: post
title: "Next.js Runtime 배치 실전: Node.js, Edge, Proxy, preferredRegion, maxDuration로 요청 경계를 설계하는 법"
date: 2026-05-01 11:40:00 +0900
categories: [nextjs]
tags: [study, nextjs, runtime, nodejs, edge, proxy, preferred-region, max-duration, route-segment-config, performance, operations]
permalink: /nextjs/2026/05/01/study-nextjs-runtime-nodejs-edge-proxy-preferred-region-max-duration.html
---

## 배경: Next.js의 Runtime 선택은 성능 옵션이 아니라 요청-데이터 경계를 어디에 둘지 정하는 아키텍처 문제다

App Router를 쓰다 보면 `export const runtime = "edge"` 같은 한 줄이 꽤 매력적으로 보인다.

- 사용자와 더 가까운 곳에서 실행되니 더 빠를 것 같다
- 인증 게이트, A/B 테스트, 기능 플래그 같은 처리가 전부 Edge에 잘 맞아 보인다
- `preferredRegion`, `maxDuration` 같은 옵션도 있으니 세밀한 제어가 가능해 보인다
- 예전 `middleware.ts` 경험이 있으면 진입점에서 거의 모든 요청 정책을 통제할 수 있을 것처럼 느껴진다

문제는 여기서부터다. 실무에서는 Runtime 선택이 생각보다 자주 잘못된다.

- Edge로 옮겼는데 실제로는 DB가 한 지역에만 있어 오히려 왕복이 늘어난다
- Proxy에서 모든 인증을 끝냈다고 믿었다가 Server Action과 Route Handler에서 권한 구멍이 생긴다
- 파일 업로드, PDF 생성, AI 스트리밍, 압축 처리 같은 무거운 작업을 Edge로 옮겼다가 라이브러리 제약에 막힌다
- `preferredRegion`을 선언했는데 배포 플랫폼에서 기대한 방식으로 동작하지 않아 디버깅이 길어진다
- `maxDuration`을 늘리면 타임아웃 문제가 끝날 줄 알았는데, 실제 병목은 외부 API나 DB 락이라 체감 개선이 없다
- Next.js 16 이후 `middleware`가 `proxy`로 바뀐 사실을 놓치고, 오래된 문서와 섞어 설계하다 책임 경계가 흐려진다

핵심은 단순하다.

> **Next.js Runtime은 "어디서 실행할까"의 문제가 아니라, 어떤 요청을 어떤 제약과 어떤 데이터 거리에서 처리할지 정하는 운영 설계다.**

특히 중급 이상 개발자에게 중요한 질문은 아래 다섯 가지다.

1. 이 코드는 **사용자와 가까워야** 빠른가, 아니면 **데이터와 가까워야** 빠른가
2. 이 요청은 **Node.js API, 파일 시스템, DB 드라이버, 무거운 npm 패키지**를 필요로 하는가
3. 이 로직은 **렌더링 전 교통정리**인가, 아니면 **실제 읽기/쓰기 비즈니스 처리**인가
4. 이 경로는 **지역 배치**가 성능에 의미가 있는가, 아니면 운영 복잡도만 늘리는가
5. 이 작업은 **타임아웃 예산**을 늘려야 해결되는가, 아니면 요청 구조 자체를 분리해야 하는가

이 글은 Runtime 문법 소개가 아니라, **Node.js Runtime, Edge Runtime, `proxy.ts`, `preferredRegion`, `maxDuration`를 어떻게 조합해야 실무에서 덜 깨지는지**를 정리한다.

---

## 먼저 큰 그림: Runtime 선택은 "사용자와의 거리"보다 "데이터와의 거리"를 먼저 봐야 한다

많은 팀이 Edge를 생각할 때 첫 문장을 이렇게 잡는다.

- "사용자에게 더 가까우니 빠르다"

이 말은 반만 맞다. 실제 응답 시간은 보통 아래 합으로 결정된다.

1. 사용자 → 실행 환경
2. 실행 환경 → 데이터 저장소
3. 실행 환경 내부 연산 시간
4. 외부 API 호출 시간
5. 캐시 히트/미스 여부
6. 직렬화, 스트리밍, 압축, 업로드 비용

즉 **사용자와 가까운 것**만으로는 충분하지 않다. 특히 DB가 한 지역에 몰려 있으면 오히려 Edge가 손해일 수 있다.

### 예시 1) 글로벌 마케팅 랜딩 + 정적/공개 데이터

- 사용자는 여러 대륙에 퍼져 있다
- 데이터는 거의 읽기 전용이다
- 요청마다 DB 왕복이 필요하지 않다
- 지역별 리다이렉트, 기능 플래그, 공개 설정값 정도만 본다

이 경우는 Edge가 잘 맞을 가능성이 있다.

### 예시 2) 멀티테넌트 B2B 대시보드 + 단일 리전 DB

- 사용자는 글로벌일 수 있다
- 하지만 실제 데이터는 서울 혹은 버지니아 한 곳의 DB에 있다
- 조직 권한 확인, 집계 쿼리, 감사 로그 기록이 필요하다
- 응답 대부분이 DB 왕복에 지배된다

이 경우는 Edge로 옮겨도 **사용자→Edge** 구간만 줄고, **Edge→DB** 구간이 더 길어져 총합이 나빠질 수 있다.

### 실무 기준으로 바꾸면

Runtime 선택은 다음 질문 순으로 보는 편이 안전하다.

1. **이 요청이 데이터 저장소를 얼마나 자주 만지는가**
2. **그 저장소가 어디에 있는가**
3. **Node.js 전용 의존성이 있는가**
4. **응답 시간을 줄이려는 이유가 네트워크 거리인지, CPU/IO/락 때문인지**
5. **캐시, 프리컴퓨트, 백그라운드화로 풀 문제인지**

이 순서를 지키면 "일단 Edge" 같은 감정적인 결정을 많이 피할 수 있다.

---

## 핵심 개념 1: 기본값은 Node.js Runtime이고, Edge는 "명확한 이유가 있을 때만" 선택하는 편이 맞다

Next.js 공식 문서 기준으로 App Router의 기본 Runtime은 **Node.js**다. 이 기본값은 괜히 있는 게 아니다.

Node.js Runtime이 강한 이유는 단순하다.

- 대부분의 npm 패키지가 문제 없이 동작한다
- DB 드라이버, ORM, 파일 시스템, 압축, 이미지 처리 같은 실무 기능이 자연스럽다
- 디버깅과 로컬 재현이 상대적으로 쉽다
- 보통 팀이 이미 가진 서버 지식과 더 잘 맞는다

반면 Edge Runtime은 선택지가 아니라 **제약을 감수하는 설계**에 가깝다.

- 모든 Node.js API를 지원하지 않는다
- 일부 패키지는 아예 동작하지 않거나 우회가 필요하다
- 공식 문서상 Edge Runtime은 ISR을 지원하지 않는다
- Next.js 16 기준으로 Cache Components와 `runtime: "edge"`는 함께 지원되지 않는다

즉 실무 기본값은 아래처럼 잡는 편이 안전하다.

### 권장 기본값

- **페이지/레이아웃/Route Handler는 일단 Node.js Runtime으로 시작한다**
- Edge는 측정 가능한 지리적 지연 이점이 있고, 의존성 제약을 모두 통과할 때만 올린다

```tsx
// app/dashboard/page.tsx
// runtime을 선언하지 않으면 기본은 nodejs
export default async function DashboardPage() {
  const summary = await getDashboardSummary();
  return <Dashboard summary={summary} />;
}
```

### Edge를 고민할 만한 신호

- 응답 대부분이 가벼운 읽기이며 DB 왕복이 거의 없다
- 국가/지역별 rewrite, redirect, locale 분기처럼 "입구 판단"이 핵심이다
- 기능 플래그, 퍼블릭 설정값, 간단한 실험군 배정 등 CPU/메모리 요구가 작다
- Web Standard API 기반으로 충분하고 Node 전용 라이브러리가 거의 없다

### Node를 고수해야 하는 신호

- Prisma, native addon, 파일 업로드/가공, PDF/이미지 생성, 압축, 대용량 스트림 처리
- 내부 DB가 단일 리전이고 대부분 요청이 그 DB를 본다
- 오래 실행되는 작업이나 외부 API fan-out이 많다
- 감사 로그, 큐 적재, 백오피스 권한 검증처럼 비즈니스 후처리가 많다

실무에서 중요한 건 "Edge가 더 최신 기술이라서"가 아니다. **기본 복잡도를 올리지 않고도 성능 이득이 분명한가**가 기준이어야 한다.

---

## 핵심 개념 2: Proxy는 렌더링 전 교통정리 레이어이고, 실제 비즈니스 처리의 종착점이 아니다

Next.js 16에서는 기존 `middleware.ts`가 **`proxy.ts`로 이름이 바뀌었다.** 이 변화는 단순한 리네이밍 이상이다. 이름부터 책임을 더 분명하게 드러낸다.

Proxy는 다음에 강하다.

- 리다이렉트
- 리라이트
- 헤더/쿠키 기반 빠른 분기
- locale 경로 보정
- 공개/비공개 경로의 1차 교통정리
- 아주 얕은 인증 게이트

반대로 Proxy를 최종 권한 판정기처럼 쓰면 곧 문제가 생긴다.

- Server Action과 Route Handler가 별도 POST 경로로 실행될 때 정책이 어긋날 수 있다
- 리소스 단위 인가나 DB 기반 권한 검증을 Proxy에 과하게 밀어 넣으면 전체 요청 비용이 커진다
- 코드상으로는 "막은 것처럼 보이는데" 실제 쓰기 경계에서는 검증이 빠질 수 있다

공식 문서 기준으로도 중요한 포인트가 있다.

- Proxy는 **기본적으로 Node.js runtime**을 사용한다
- Proxy 파일에서는 **`runtime` route segment config를 사용할 수 없다**
- 즉 "Proxy도 Edge로 돌리자"는 발상이 이제는 더더욱 기본 경로가 아니다

### Next.js 16 스타일의 기본 예시

```ts
// proxy.ts
import { NextRequest, NextResponse } from 'next/server'

export function proxy(request: NextRequest) {
  const pathname = request.nextUrl.pathname
  const session = request.cookies.get('session')?.value

  if (pathname.startsWith('/app') && !session) {
    const loginUrl = new URL('/login', request.url)
    loginUrl.searchParams.set('from', pathname)
    return NextResponse.redirect(loginUrl)
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/app/:path*'],
}
```

이 레이어의 책임은 분명하다.

- 세션이 없으면 입구에서 막는다
- 그렇다고 해서 조직 권한, 리소스 소속, 액션 권한까지 끝났다고 보지는 않는다
- 실제 읽기/쓰기 권한은 Page, Layout, Server Action, Route Handler에서 다시 확인한다

### 왜 이 구분이 중요할까

예를 들어 `/app/acme/members/123` 수정 화면을 생각해 보자.

- Proxy: 세션 쿠키 존재 여부 확인, 로그인 리다이렉트
- Layout/Page: `acme` 조직 멤버인지 확인
- Server Action: `member:update` 권한이 있는지, `123`이 실제 `acme` 조직 멤버인지 확인

이렇게 쪼개야 보안도 맞고 성능도 맞다.

> **Proxy는 빠른 진입 제어까지, 최종 권한 판정은 실제 서버 실행 지점에서**

이 규칙을 지키면 Runtime 선택도 훨씬 명확해진다.

---

## 핵심 개념 3: Edge Runtime의 진짜 제약은 "속도"보다 "호환성"과 "운영 반경"에 있다

Edge Runtime을 검토할 때 제일 먼저 보는 문장은 보통 "사용자에게 더 가깝다"다. 실무에서는 오히려 아래 두 문장이 더 중요하다.

1. **모든 Node.js API를 지원하지 않는다**
2. **일부 패키지는 기대대로 동작하지 않는다**

이 차이는 생각보다 크다.

### Edge에서 흔히 부딪히는 문제

- `fs` 기반 파일 접근 불가
- Node 전용 `crypto` 사용 패턴과 Web Crypto 간 차이
- native addon 의존 패키지 불가
- 오래된 SDK나 내부 유틸이 `Buffer`, stream, TCP, 파일 경로를 전제함
- ORM/DB 드라이버가 Edge-compatible 모드가 아니면 바로 막힘

### 특히 위험한 착시

개발 환경에서는 동작해 보이는데 실제 배포 환경 Edge에서 깨지는 경우다.

- 로컬은 Node.js라 잘 돌아간다
- 코드 리뷰에서도 특별히 이상해 보이지 않는다
- 배포 후 특정 런타임에서만 패키지 호환성 오류가 발생한다

그래서 Edge를 선택하기 전에는 기능보다 먼저 **의존성 감사**가 필요하다.

### Runtime 결정 전에 체크해야 할 항목

- 이 경로가 직접 혹은 간접적으로 `fs`, native addon, Node-only 패키지를 쓰는가
- 내부 공용 유틸이 Node 전제 코드를 숨기고 있지 않은가
- DB/ORM 접근이 Edge 호환 모드인지, 아니면 HTTP 브리지/프록시가 필요한가
- 암호화, 서명, 해시 로직이 Web Crypto 기반으로 안전하게 옮겨지는가
- 스트리밍, 압축, 대용량 업로드처럼 메모리 압력이 있는가

### 운영 관점에서 더 본질적인 질문

호환성만 통과했다고 끝이 아니다. 다음도 봐야 한다.

- 오류가 났을 때 디버깅 난도는 올라가지 않는가
- 성능 이득보다 런타임 이원화 비용이 더 크지 않은가
- 팀이 Node와 Edge 두 실행 모델을 동시에 이해할 준비가 되어 있는가

실무에서는 **Edge-compatible** 과 **Edge-appropriate** 를 구분해야 한다.

- Edge-compatible: 기술적으로 돌아간다
- Edge-appropriate: 실제 서비스 운영에서 이 선택이 이득이다

둘은 전혀 같은 말이 아니다.

---

## 핵심 개념 4: `preferredRegion`은 마법이 아니라 배포 플랫폼에 전달하는 힌트다

`preferredRegion`을 처음 보면 꽤 강력해 보인다.

- 특정 리전에 배치하고 싶다
- 여러 리전에 복제하고 싶다
- 글로벌로 퍼뜨리고 싶다

공식 문서 기준으로 `preferredRegion`은 **route segment의 선호 배치 지역을 배포 플랫폼에 전달하는 옵션**이다. 여기서 중요한 단어는 "전달한다"다. 즉 동작 의미는 플랫폼 의존적이다.

```tsx
export const runtime = 'edge'
export const preferredRegion = 'global'
```

또는

```tsx
export const runtime = 'edge'
export const preferredRegion = ['iad1', 'sfo1']
```

### 꼭 알아야 할 점

1. **플랫폼별 지원이 다르다**  
   같은 Next.js 코드라도 배포 플랫폼마다 해석이 다를 수 있다.

2. **부모 layout에서 상속되지만 병합되지는 않는다**  
   가장 가까운 부모 값을 상속받고, 자식이 새 값을 주면 override 된다.

3. **배열은 "그중 하나를 고른다"가 아니라 "모든 나열된 지역에 배치"에 가깝다**  
   이 차이를 오해하면 비용과 운영 복잡도가 크게 늘 수 있다.

4. **Vercel 기준으로는 Edge runtime일 때만 region 옵션이 의미를 갖는 경우가 많다**  
   즉 Node.js runtime에서 같은 기대를 하면 어긋날 수 있다.

### 실무에서 자주 하는 오해

#### 오해 1) `preferredRegion = "global"`이면 무조건 빨라진다

아니다. 공개 읽기에는 도움이 될 수 있지만, 매 요청이 한 지역 DB를 봐야 한다면 전체 지연은 오히려 늘 수 있다.

#### 오해 2) 여러 리전을 나열하면 자동으로 가장 좋은 곳 하나만 선택한다

공식 문서 기준 설명은 그렇지 않다. 배열은 **나열한 지역 모두에 배치**되는 방식으로 이해해야 안전하다.

#### 오해 3) 지역 선언만 하면 데이터 일관성 문제도 해결된다

그렇지 않다. 배치 지역과 데이터 복제 전략은 별개다. 지역을 넓히면 오히려 캐시, 세션, 쓰기 일관성 설계가 더 어려워질 수 있다.

### 좋은 사용 예시

- 전 세계 공통 공개 설정값 읽기
- 국가/대륙별 리다이렉트나 locale landing 처리
- 퍼블릭 feature flag, pricing card, 실험군 분기처럼 쓰기보다 읽기 중심인 경로

### 나쁜 사용 예시

- 매 요청마다 단일 리전 DB를 읽는 대시보드
- 결제/정산/권한 변경처럼 강한 일관성이 필요한 쓰기 경로
- 큐 적재, 파일 가공, 대용량 리포트 생성처럼 지역보다 처리 제약이 더 중요한 작업

---

## 핵심 개념 5: `maxDuration`은 타임아웃 문제를 숨기는 스위치가 아니라 "이 요청이 오래 걸리는 이유"를 드러내는 도구다

`maxDuration`은 server-side logic의 최대 실행 시간을 초 단위로 힌트하는 route segment config다.

```tsx
export const maxDuration = 30
```

공식 문서 기준으로 중요한 포인트는 두 가지다.

1. 이 값은 **배포 플랫폼이 실행 제한을 적용할 때 참고하는 빌드 출력 정보**다
2. **Page 레벨에 설정하면 그 페이지에서 사용하는 Server Actions의 기본 timeout에도 영향을 준다**

즉 `maxDuration`은 유용하지만, 이것만으로 느린 요청이 좋은 요청이 되는 건 아니다.

### 먼저 구분해야 할 느림의 원인

#### 1) 정말 오래 걸리는 작업

- PDF 생성
- 대용량 CSV export
- AI 요약/번역/생성 호출
- 여러 외부 API fan-out
- 오래 걸리는 DB 집계

이 경우 `maxDuration`이 필요할 수 있다.

#### 2) 구조가 잘못된 작업

- 원래 백그라운드 큐로 보내야 할 일을 동기 요청에 묶어 둠
- N+1 쿼리 때문에 오래 걸림
- 락 경쟁, 느린 인덱스, 외부 API 재시도 폭증이 병목임
- 업로드 후 후처리를 요청-응답 사이클에 다 몰아넣음

이 경우는 `maxDuration`을 늘려도 근본 해결이 아니다.

### 좋은 사용 예시

```tsx
// app/reports/[id]/page.tsx
export const maxDuration = 60

export default async function ReportPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const report = await getReport(id)
  return <ReportDetail report={report} />
}
```

이 페이지에서 쓰는 Server Action이 비교적 긴 문서 생성, 승인 워크플로우, 외부 저장소 업로드를 수행한다면 `maxDuration`이 현실적인 안전장치가 될 수 있다.

### 하지만 더 자주 맞는 해법은 이쪽이다

- 요청은 job 생성만 하고 빠르게 끝낸다
- 실제 긴 작업은 큐/백그라운드 워커가 처리한다
- UI는 polling, SSE, webhook, optimistic status로 진행률을 본다

즉 `maxDuration`을 건다는 것은 보통 다음 질문으로 이어져야 한다.

> **이 작업이 정말 사용자 요청-응답 안에 있어야 하는가?**

이 질문을 빼먹으면 타임아웃만 늦추고 UX는 그대로 나쁜 상태가 된다.

---

## 핵심 개념 6: Runtime 선택은 캐시 전략, 스트리밍, 권한 경계와 같이 봐야 한다

Runtime을 독립 변수처럼 다루면 자주 실패한다. 실제로는 아래 요소와 강하게 얽혀 있다.

### 1) 캐시 전략

공식 문서 기준으로 Edge Runtime은 ISR을 지원하지 않는다. 즉 "public content + 재검증" 모델을 강하게 활용하는 페이지라면 무심코 Edge로 옮기기 어렵다.

또한 Next.js 16 문서 기준으로 Cache Components와 `runtime: "edge"`도 함께 지원되지 않는다. 캐시를 적극 활용하는 App Router 설계라면 Node 기본값이 훨씬 안전한 경우가 많다.

### 2) 스트리밍

두 Runtime 모두 배포 어댑터에 따라 스트리밍을 지원할 수 있다. 즉 스트리밍이 필요하다고 해서 자동으로 Edge가 정답은 아니다.

오히려 질문은 이쪽이 맞다.

- 이 스트림은 지리적으로 사용자 가까운 곳에서 시작되는 게 중요한가
- 아니면 DB/권한/AI SDK/파일 처리와 붙어 있어 Node가 더 자연스러운가

### 3) 인증과 권한

Proxy에서 빠른 리다이렉트는 가능해도, 실제 조직 권한·리소스 소속·감사 로그는 대개 Node 기반의 서버 경계에서 끝내는 편이 안정적이다.

### 4) 데이터 페치 패턴

- 내부 읽기: Server Component 우선
- 내부 mutation: Server Action 우선
- 외부 HTTP 계약: Route Handler
- 진입 전 빠른 경로 제어: Proxy

이 역할 분리가 되어야 Runtime 선택도 깔끔해진다. 그렇지 않으면 "Route Handler도 있고 Server Action도 있고 Proxy도 있는데 다 Edge로 옮겨야 하나?" 같은 혼란이 생긴다.

---

## 실무 예시 1: 글로벌 마케팅 사이트의 국가별 진입 제어는 Proxy가 맞지만, 개인화 권한 판정까지 넣으면 과하다

마케팅 사이트에서 흔한 요구사항은 이렇다.

- 한국 사용자는 `/ko`
- 일본 사용자는 `/ja`
- 로그인 사용자는 `/app`으로 보내기
- 특정 캠페인 파라미터는 별도 랜딩으로 rewrite

이런 것은 Proxy가 잘한다.

```ts
// proxy.ts
import { NextRequest, NextResponse } from 'next/server'

const SUPPORTED = ['ko', 'en', 'ja']

function pickLocale(request: NextRequest) {
  const header = request.headers.get('accept-language') ?? ''
  const locale = header.split(',')[0]?.split('-')[0]?.toLowerCase()
  return SUPPORTED.includes(locale) ? locale : 'en'
}

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl

  if (pathname.startsWith('/_next') || pathname.includes('.')) {
    return NextResponse.next()
  }

  const hasLocale = SUPPORTED.some(
    (locale) => pathname === `/${locale}` || pathname.startsWith(`/${locale}/`)
  )

  if (!hasLocale) {
    const locale = pickLocale(request)
    const url = request.nextUrl.clone()
    url.pathname = `/${locale}${pathname}`
    return NextResponse.redirect(url)
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)'],
}
```

이건 좋다. 하지만 여기에 아래를 한꺼번에 넣기 시작하면 냄새가 난다.

- 조직 멤버십 DB 조회
- 세밀한 권한 매트릭스 해석
- 리소스 소속 확인
- 감사 로그 기록
- 차단 사용자 정책, 플랜 제한, 결제 상태 검증

이것들은 Proxy보다 실제 서버 실행 지점에서 처리하는 편이 맞다.

### 정리

- **입구 분기**: Proxy
- **실제 사용자 문맥 확정**: Layout/Page
- **실제 쓰기 승인**: Server Action/Route Handler

이렇게 쪼개면 Runtime 설계가 안정된다.

---

## 실무 예시 2: 퍼블릭 기능 플래그 읽기 API는 Edge를 검토할 수 있지만, 관리자 수정 API는 Node가 더 자연스럽다

같은 기능 플래그 도메인이라도 읽기와 쓰기는 전혀 다르다.

### 퍼블릭 읽기 API

- 사용자에게 가까운 응답이 유리하다
- 응답이 작고 단순하다
- DB 직접 연결이 아니라 글로벌 KV나 공개 config 서비스일 수 있다
- 권한이 거의 없거나 아주 단순하다

이 경우는 Edge를 검토할 수 있다.

```ts
// app/api/public-flags/route.ts
export const runtime = 'edge'
export const preferredRegion = 'global'

export async function GET() {
  const res = await fetch('https://config.example.com/public-flags', {
    cache: 'no-store',
  })

  if (!res.ok) {
    return Response.json({ message: 'failed to load flags' }, { status: 502 })
  }

  const flags = await res.json()
  return Response.json(flags, {
    headers: {
      'Cache-Control': 's-maxage=30, stale-while-revalidate=300',
    },
  })
}
```

### 관리자 수정 API

- 권한 검증이 필요하다
- 감사 로그를 남겨야 한다
- 변경 즉시 반영과 롤백이 중요하다
- 단일 원본 저장소를 건드린다

이 경우는 보통 Node가 맞다.

```ts
// app/api/admin/flags/[key]/route.ts
export const runtime = 'nodejs'
export const maxDuration = 15

export async function PATCH(
  request: Request,
  { params }: { params: Promise<{ key: string }> }
) {
  const { key } = await params
  const body = await request.json()

  const viewer = await requireAdminViewer()
  await updateFlag({ key, value: body.value, actorId: viewer.userId })

  return Response.json({ ok: true })
}
```

### 왜 읽기/쓰기를 같은 Runtime으로 묶으면 안 될까

읽기는 지리적 근접성이 더 중요할 수 있지만, 쓰기는 보통 **권한, 데이터 일관성, 후처리**가 더 중요하다. 이 차이를 무시하면 성능도 보안도 둘 다 흐려진다.

---

## 실무 예시 3: AI 스트리밍이나 대용량 Export는 Edge보다 Node + `maxDuration` + 비동기화가 더 현실적일 때가 많다

겉으로 보기엔 AI 채팅, 문서 변환, 리포트 export는 "스트리밍이니까 Edge"처럼 느껴질 수 있다. 실제로는 그렇지 않다.

이런 작업은 자주 다음 특성을 가진다.

- 외부 AI SDK나 내부 보안 래퍼를 사용한다
- 권한 검증이 세밀하다
- 원문 문서나 DB 데이터를 많이 읽는다
- 결과를 S3/GCS 같은 저장소에 업로드해야 한다
- 수초~수십초가 걸릴 수 있다

이 경우는 Node가 더 자연스러운 경우가 많다.

```ts
// app/api/reports/export/route.ts
export const runtime = 'nodejs'
export const maxDuration = 60

export async function POST(request: Request) {
  const viewer = await requireViewer()
  const input = await request.json()

  const job = await createExportJob({
    actorId: viewer.userId,
    filters: input.filters,
  })

  return Response.json({ jobId: job.id }, { status: 202 })
}
```

그리고 실제 무거운 작업은 워커로 넘긴다.

- Route Handler: 작업 생성만 담당
- 워커: DB 조회, 파일 생성, 업로드 수행
- UI: job status polling 혹은 SSE로 진행률 표시

### 여기서 얻는 이점

- 요청 타임아웃 압박 감소
- 재시도와 실패 복구가 쉬움
- 사용자 체감은 빨라짐
- Runtime을 괜히 Edge로 비틀지 않아도 됨

즉 스트리밍이 가능하냐보다 더 중요한 질문은 **이 작업이 온라인 동기 작업이어야 하냐**다.

---

## 실무 예시 4: 단일 리전 DB를 쓰는 SaaS 대시보드는 "사용자 가까움"보다 "데이터 가까움"이 더 중요하다

이 케이스가 실무에서 가장 흔하다.

- 사용자는 미국, 유럽, 한국에 퍼져 있다
- 애플리케이션 DB는 한 리전에 있다
- 조직 권한, 감사 로그, 트랜잭션, 백오피스 쓰기가 많다
- 대시보드에서 집계와 상세 데이터가 함께 노출된다

이런 서비스는 Runtime을 억지로 글로벌화할수록 오히려 복잡해질 수 있다.

### 잘못된 접근

- 상세 페이지도 Edge
- 관리자 API도 Edge
- 기능 플래그, 권한, 대시보드 읽기, 저장 전부 Edge

이렇게 가면 실제로는 거의 모든 요청이 멀리 있는 DB를 다시 본다. 그러면 사용자→실행환경 거리는 줄어도, 실행환경→DB 거리가 커져 총합이 나빠질 수 있다.

### 더 현실적인 접근

- 대시보드 Page/Layout: Node.js runtime
- 실제 읽기: Server Component에서 직접 DB/BFF 호출
- 실제 쓰기: Server Action 혹은 Route Handler
- Proxy: 로그인 리다이렉트 같은 얕은 진입 제어만
- 필요하면 퍼블릭/마케팅 구간만 별도로 Edge 고려

이렇게 분리하면 서비스 코어와 퍼블릭 엣지를 구분할 수 있다.

### 중요한 사고방식

SaaS 대시보드는 대개 "콘텐츠 배포"보다 "정합성 있는 업무 처리"에 가깝다. 이런 경로에서 Runtime의 우선순위는 보통 아래 순서다.

1. 데이터와의 거리
2. 권한 검증의 명확성
3. 패키지/SDK 호환성
4. 장애 시 디버깅 가능성
5. 그다음에 사용자와의 거리

---

## 실무 예시 5: Page 레벨 `maxDuration`은 Server Action timeout 정책을 화면 단위로 맞출 때 유용하다

공식 문서에서 실무적으로 꽤 중요한 포인트가 하나 있다. **Page 레벨 `maxDuration`은 그 페이지에서 사용하는 Server Actions의 기본 timeout에도 영향을 줄 수 있다.**

이건 승인, 발행, 리포트 요청 같은 백오피스 화면에서 꽤 유용하다.

```tsx
// app/admin/posts/[id]/page.tsx
export const maxDuration = 20

import { publishPost, rebuildOgImage } from './actions'

export default async function AdminPostPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const post = await getPostForAdmin(id)

  return (
    <form action={publishPost}>
      <input type="hidden" name="id" value={post.id} />
      <button type="submit">발행</button>
      <button formAction={rebuildOgImage}>OG 이미지 재생성</button>
    </form>
  )
}
```

이 패턴의 장점은 다음과 같다.

- 관련 액션들의 실행 예산을 화면 단위로 맞추기 쉽다
- "이 화면은 일반 CRUD보다 조금 무겁다"는 사실을 코드로 드러낼 수 있다
- 팀이 timeout 정책을 경로 기준으로 대화하기 쉬워진다

하지만 역시 여기서도 질문이 필요하다.

- 이 액션이 사용자 대기형이어야 하는가
- 재시도와 실패 복구가 중요한가
- 작업 완료가 즉시 필요하지 않다면 job queue가 더 낫지 않은가

`maxDuration`은 좋은 도구지만, **길어진 요청을 정당화하는 도구**가 되어서는 안 된다.

---

## 의사결정 매트릭스: 어떤 요청을 어디에 둘까

| 상황 | 우선 선택 | 이유 |
|---|---|---|
| 페이지 진입 전 로그인 여부 확인 | Proxy | 빠른 리다이렉트/재작성에 적합 |
| 내부 읽기 + DB/ORM 접근 | Server Component + Node | API hop 없이 데이터에 가깝고 호환성 좋음 |
| 내부 폼/버튼 기반 mutation | Server Action + Node | UI 흐름과 자연스럽고 권한 검증 넣기 좋음 |
| 외부 서비스 webhook | Route Handler + Node | HTTP 계약, 서명 검증, 후처리에 유리 |
| 퍼블릭 경량 읽기 API | Route Handler + Edge 검토 | 지리적 근접성과 간단한 응답이 이점일 수 있음 |
| 대용량 export / AI 생성 / 문서 변환 | Route Handler + Node + 비동기화 | timeout/호환성/후처리 측면에서 안전 |
| 글로벌 locale redirect | Proxy | 렌더링 전 교통정리에 적합 |
| 단일 리전 DB SaaS 대시보드 | Node 중심 | 데이터 거리와 권한 경계가 더 중요 |

이 표를 팀 위키에 붙여두면 Runtime 논쟁이 훨씬 덜 감정적으로 흘러간다.

---

## 트레이드오프 1: Edge는 지리적 지연을 줄일 수 있지만, 데이터 일관성과 의존성 제약을 더 비싸게 만들 수 있다

### Edge 쪽 장점

- 공개 읽기 경로에서 사용자 체감 지연을 줄일 여지가 있다
- 리다이렉트, 리라이트, 경량 분기에 잘 맞는다
- 일부 글로벌 콘텐츠/설정값 제공에 유리하다

### Edge 쪽 비용

- Node.js API와 패키지 제약
- 런타임 이원화로 인한 디버깅 비용 증가
- 단일 리전 데이터 저장소와의 거리 증가 가능성
- 캐시/일관성 전략 복잡화

즉 Edge의 핵심 이점은 "어디서나 더 빠름"이 아니라 **특정 유형의 읽기 요청에 한해 더 빠를 수 있음**이다.

---

## 트레이드오프 2: Proxy를 강하게 쓰면 진입 제어는 깔끔해지지만, 실제 권한 로직을 과신하면 위험하다

### Proxy를 쓰는 이점

- 경로 단위 교통정리가 깔끔하다
- 로그인 리다이렉트, locale 보정, A/B 버킷팅에 좋다
- 페이지 렌더 전에 가벼운 정책을 적용할 수 있다

### Proxy를 과신할 때 문제

- Server Action/Route Handler에서 최종 권한 검증이 빠진다
- 인증은 있는데 인가는 없는 시스템이 된다
- 모든 요청 입구에서 무거운 검증을 돌려 전체 성능이 나빠진다

그래서 Proxy는 강력하지만, **얇게 유지할수록 더 오래 버틴다.**

---

## 트레이드오프 3: `maxDuration`을 늘리면 실패 빈도는 줄 수 있지만, 시스템 설계가 더 좋아지는 것은 아니다

### 늘리는 편이 맞는 경우

- 짧게는 안 끝나는 작업이지만 여전히 사용자 대기형으로 가치가 있다
- 플랫폼 기본 제한이 현실보다 지나치게 짧다
- 작업 시간이 비교적 예측 가능하다

### 늘리면 안심만 주고 문제는 남는 경우

- 원래 비동기 job이어야 하는데 억지로 동기로 붙들고 있다
- 느린 원인이 DB 설계, 외부 API 품질, 재시도 폭발이다
- 동일 경로에서 트래픽 피크 시 병목이 더 심해진다

즉 `maxDuration`은 성능 튜닝 스위치보다 **실행 예산 선언**에 가깝다.

---

## 흔한 실수 1: "사용자에게 더 가깝다"만 보고 Edge를 선택한다

가장 흔한 실수다. 실제 응답 시간이 어디서 소비되는지 안 보고 Runtime부터 바꾸면 기대와 다른 결과가 나온다.

### 교정 질문

- 이 요청은 DB를 보나
- 그 DB는 어디 있나
- 외부 API는 어디 있나
- 직렬화/압축/AI 호출이 더 큰 병목 아닌가

---

## 흔한 실수 2: Proxy에서 인증만 하면 Server Action과 Route Handler도 안전하다고 믿는다

이건 보안 사고로 이어질 수 있다.

- Proxy는 입구 제어일 뿐이다
- 최종 권한 판정은 실제 읽기/쓰기 경계에서 다시 해야 한다
- 특히 멀티테넌트 서비스는 리소스 소속 검증까지 필요하다

---

## 흔한 실수 3: `preferredRegion`을 인프라 추상화처럼 이해한다

실제로는 배포 플랫폼으로 전달되는 힌트다. 지원 방식도 플랫폼마다 다르고, 부모-자식 병합도 일어나지 않는다. 특히 배열이 "후보 중 하나 선택"이 아니라 "나열된 지역 전체 배치"라는 점을 놓치기 쉽다.

---

## 흔한 실수 4: Edge-compatible 과 Edge-appropriate 를 구분하지 않는다

코드가 돌아간다고 해서 좋은 배치라는 뜻은 아니다.

- 기술적으로 가능한가
- 운영적으로 이득인가

이 두 단계가 모두 통과해야 한다.

---

## 흔한 실수 5: 타임아웃이 나면 무조건 `maxDuration`부터 올린다

이건 증상 완화일 수는 있어도 구조 개선은 아니다.

- 긴 작업은 큐로 빼는 게 더 나을 수 있다
- 느린 쿼리나 외부 API가 병목이면 duration만 늘어날 뿐이다
- 사용자는 오래 기다리는 UX 자체를 더 싫어할 수 있다

---

## 체크리스트: Runtime을 바꾸기 전에 꼭 확인할 것

### Runtime 선택

- [ ] 이 경로는 Node.js 기본값으로도 충분하지 않은가?
- [ ] Edge가 필요한 이유를 "감"이 아니라 실제 지연 구조로 설명할 수 있는가?
- [ ] 데이터와 가까워야 하는지, 사용자와 가까워야 하는지 구분했는가?

### 의존성/호환성

- [ ] `fs`, native addon, Node-only 패키지가 간접적으로라도 없는가?
- [ ] DB/ORM/암호화/압축/파일 처리 라이브러리가 대상 Runtime과 호환되는가?
- [ ] 로컬 Node 환경에서만 우연히 돌아가는 코드를 Edge로 착각하지 않았는가?

### Proxy 책임

- [ ] Proxy는 리다이렉트/리라이트/얕은 게이트에만 머무는가?
- [ ] 실제 권한 판정이 Page/Layout/Server Action/Route Handler에 남아 있는가?
- [ ] matcher 범위가 과도하게 넓어 모든 요청 비용을 키우지 않는가?

### Region/Timeout

- [ ] `preferredRegion`이 실제 배포 플랫폼에서 어떤 의미인지 확인했는가?
- [ ] 부모 상속과 자식 override 규칙을 이해하고 있는가?
- [ ] `maxDuration`이 구조적 병목을 숨기는 용도로 쓰이지 않는가?
- [ ] 긴 작업은 큐/비동기화가 더 낫지 않은가?

### 운영성

- [ ] 장애 시 로그, 추적, 재현 방법이 Runtime별로 준비되어 있는가?
- [ ] 팀이 Node와 Edge 두 모델을 동시에 유지할 이유가 충분한가?
- [ ] 퍼블릭 경로와 코어 업무 경로를 다른 기준으로 배치하고 있는가?

---

## 팀 규칙으로 정리하면 더 강해진다

Runtime 관련 논쟁이 반복되는 팀이라면 아래 세 규칙을 문서화할 가치가 있다.

### 규칙 1: 새 경로는 기본적으로 Node.js Runtime에서 시작한다

Edge는 예외다. 성능 측정이나 분명한 지리적 요구가 없으면 기본값을 지킨다.

### 규칙 2: Proxy는 얇게 유지하고, 최종 권한 판정은 실제 서버 경계에서 한다

Proxy는 교통정리, Server Component/Action/Route Handler는 실질 처리. 이 책임 분리를 강제하면 보안과 성능 모두 안정된다.

### 규칙 3: `preferredRegion`과 `maxDuration`은 선언 전에 운영 이유를 남긴다

왜 특정 지역이 필요한지, 왜 timeout 예산을 늘리는지 PR 설명에 남기면 나중에 훨씬 덜 헷갈린다.

---

## 한 줄 정리

**Next.js Runtime 설계의 핵심은 Edge를 많이 쓰는 것이 아니라, Proxy는 얇은 진입 제어에 두고, 실제 읽기·쓰기 경로는 Node.js 기본값에서 데이터 거리·패키지 호환성·타임아웃 예산을 기준으로 배치해 지연과 복잡도를 함께 줄이는 데 있다.**
