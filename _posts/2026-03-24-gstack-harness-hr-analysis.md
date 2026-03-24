---
layout: post
title: "gstack 상세 분석: Harness 엔지니어링, 레거시 HR, 신규 개발 적용 전략"
date: 2026-03-24 23:50:00 +0900
categories: [ai]
tags: [ai, gstack, harness-engineering, harness, developer-tools, legacy, hr, idp]
---

# gstack 상세 분석: Harness 엔지니어링, 레거시 HR, 신규 개발 적용 전략

> 대상 레포: `garrytan/gstack`

---

## 0. 한 줄 결론

`gstack`는 **“개발자 로컬에서 돌아가는 AI 에이전트용 작업 하네스(harness) + 역할 기반 워크플로 엔진”**에 가깝습니다. 반면 Harness(회사)의 IDP/CI/CD/Feature Flags/Environment Management는 **조직 차원의 플랫폼·거버넌스·배포·관찰 제어면(control plane)** 입니다.  
즉, 둘은 **대체재보다는 상보재**입니다. 실무적으로는 **“Harness는 조직 표준/온보딩/배포/가시성, gstack은 개발자 작업 실행기”**로 두는 구성이 가장 현실적입니다. [1][3][8][10][11][12][13][14][15]

---

## 1. 이 문서에서 “Harness Engineering”을 어떻게 해석했는가

질문의 “Harness Engineering”은 2026년 시점에서 두 가지로 읽힐 수 있습니다.

1. **OpenAI가 말하는 ‘harness engineering’ 개념**  
   에이전트가 신뢰성 있게 일하도록 **환경, 문서, 규칙, 테스트, 피드백 루프**를 설계하는 엔지니어링 방식입니다. [7][8][9]

2. **Harness(회사)의 엔지니어링 플랫폼/IDP/CI/CD 체계**  
   Internal Developer Portal, CI/CD, Feature Flags, Environment Management, SEI 등을 포함한 **플랫폼 엔지니어링 제품군**입니다. [10][11][12][13][14][15][16][17][18]

아래에서는 **두 해석 모두** 비교합니다.  
실무 결정에는 두 번째(제품/플랫폼 관점)가 더 직접적이지만, gstack의 철학을 이해하려면 첫 번째(개념 관점)가 중요합니다.

---

## 2. gstack 상세 분석

### 2.1. gstack는 무엇인가

gstack는 README 기준으로 **Claude Code를 “가상 엔지니어링 팀”처럼 동작시키는 스킬 세트 + 고속 헤드리스 브라우저**를 제공하는 오픈소스 스택입니다.  
설치 방식도 일반 라이브러리라기보다, **사용자 글로벌(`~/.claude/skills/gstack`) 또는 프로젝트 로컬(`.claude/skills/gstack`)에 벤더링해서 팀이 같이 쓰는 방식**을 전제로 합니다. 실제 파일을 레포 안에 커밋하는 모델이라서, 팀 공유와 재현성이 좋습니다. 라이선스는 MIT입니다. [1][6][29]

핵심 정체성은 다음 세 가지입니다.

- **로컬 에이전트 실행 하네스**: CLI/스킬/브라우저/상태 유지/안전장치를 묶은 실행 환경 [2][3][4]
- **워크플로 엔진**: 아이디어 정제 → 계획 검토 → 구현 → 리뷰 → QA → 배포 → 회고까지 이어지는 “스프린트형 흐름” [1][30]
- **지식/품질 루프**: 설계 문서, 리뷰 대시보드, QA 보고서, 테스트, 문서 갱신을 계속 남기는 구조 [1][3][30]

### 2.2. 아키텍처 핵심

#### 2.2.1. 지속형 브라우저(persistent browser)

gstack의 기술적 핵심은 **Playwright 기반 Chromium 브라우저를 매 호출마다 띄우지 않고, 로컬 데몬으로 오래 유지**한다는 점입니다.  
첫 호출은 약 3초가 들지만, 이후 호출은 약 100~200ms로 매우 빠르며, 쿠키·탭·세션 상태를 유지합니다. 이 상태는 `.gstack/browse.json` 같은 상태 파일로 관리되고, 30분 idle 시 자동 종료됩니다. [2][3]

이 설계는 특히 다음 장점이 큽니다.

- 브라우저 cold start 비용 제거
- 로그인 세션/탭 유지
- 장시간 QA/디버깅 시 맥락 손실 감소
- 개발자 로컬의 staging/사내 시스템 테스트에 유리 [2][3]

#### 2.2.2. MCP가 아니라 CLI 중심

gstack는 로컬 브라우저 자동화에서 MCP보다 **“컴파일된 CLI + stdout”** 경로가 더 단순하고 빠르다고 봅니다.  
문서에서는 gstack browse가 **컨텍스트 토큰 오버헤드가 사실상 0**이고, 일반 MCP 기반 브라우저 도구 대비 세션당 수만 토큰 절약 효과가 있다고 주장합니다. [2]

이 주장은 조직 차원 표준화 관점에서는 호불호가 갈릴 수 있지만, **로컬 개발자 생산성**만 놓고 보면 분명한 강점입니다.

#### 2.2.3. ref 기반 DOM 상호작용

gstack의 브라우저는 DOM에 `data-*`를 주입하는 대신, **접근성 트리에서 `@e1`, `@e2`, `@c1` 같은 ref를 생성**하고 Playwright Locator에 매핑합니다.  
이 방식은 CSP, SPA hydration, Shadow DOM 문제를 줄이고, stale ref도 빠르게 감지합니다. [2][3]

즉, gstack의 브라우저는 단순 스크린샷 도구가 아니라 **“에이전트가 신뢰성 있게 클릭/탐색/검증할 수 있도록 설계된 UI 하네스”**입니다.

### 2.3. 스킬/워크플로 구조

README와 skill deep dive 문서를 보면, gstack의 기본 흐름은 다음과 같습니다.

**Think → Plan → Build → Review → Test → Ship → Reflect** [1][30]

대표 스킬은 아래와 같습니다.

- `/office-hours`: 문제 재정의, YC식 질문으로 제품 방향 교정 [1][30]
- `/plan-ceo-review`: 제품 범위/야심/가치 재정렬 [1][30]
- `/plan-eng-review`: 아키텍처, 데이터 플로우, 상태 전이, 테스트 매트릭스 설계 [1][30]
- `/plan-design-review`, `/design-consultation`: 설계 품질/디자인 시스템 강화 [1][30]
- `/review`: 코드 리뷰와 일부 자동 수정 [1][30]
- `/investigate`: 무턱대고 고치지 않고 원인분석부터 강제 [1][30]
- `/qa`, `/qa-only`: 브라우저 기반 기능 검증, 회귀 테스트 생성 [1][30]
- `/cso`: OWASP Top 10 + STRIDE 기반 보안 리뷰 [1][30]
- `/ship`, `/land-and-deploy`, `/canary`, `/benchmark`: 배포/모니터링/성능 측정 [1][30]
- `/document-release`, `/retro`: 문서 갱신, 회고/지속개선 [1][30]
- `/careful`, `/freeze`, `/guard`, `/unfreeze`: 위험 작업 안전장치 [1][30]

### 2.4. 실제로 강한 부분

#### 2.4.1. “도구 모음”이 아니라 “작업 순서”를 강제한다

gstack의 가장 큰 장점은 기능 하나하나보다 **단계별 작업 순서를 강제**한다는 점입니다.  
`/office-hours`가 설계 문서를 만들고, 그 문서를 `/plan-ceo-review`와 `/plan-eng-review`가 읽고, `/plan-eng-review` 결과가 이후 `/qa`까지 이어지는 식입니다. [1][30]

즉, 프롬프트 몇 개를 모아 놓은 것이 아니라 **에이전트가 반복 가능한 프로세스를 따르도록 만든 운영체계**에 가깝습니다.

#### 2.4.2. QA와 브라우저 검증이 강하다

브라우저가 실사용 수준으로 설계되어 있습니다. `goto`, `click`, `fill`, `snapshot`, `console`, `network`, `dialog`, `responsive`, `diff`, `handoff/resume` 등 **50개 이상 명령**이 있고, 브라우저 모듈만 기준으로 **203개 테스트**를 갖고 있다고 문서화되어 있습니다. [2]

특히 `/qa`는 feature branch의 `git diff`를 읽어 영향을 받는 경로를 추정하고, 버그 수정 후 **회귀 테스트를 자동 생성**하는 방향으로 설계되어 있습니다. [30]

#### 2.4.3. 문서와 리뷰 대시보드를 남긴다

OpenAI식 harness engineering과 비슷하게, gstack도 **문서/계획/리뷰 결과를 에이전트가 다시 읽을 수 있는 자산**으로 쌓는 구조입니다.  
리뷰 결과를 대시보드 형태로 남기고, `/document-release`로 문서 stale 문제를 줄이며, `/retro`로 개선 루프를 닫습니다. [1][3][30]

#### 2.4.4. 로컬/프로젝트 벤더링 전략이 실무적이다

프로젝트 내부 `.claude/skills/gstack`로 벤더링하는 방식은 레거시/엔터프라이즈 환경에서 매우 유리합니다.

- 팀원이 같은 스킬 버전 사용
- 레포와 함께 version-pinning 가능
- “내 로컬 설정에서는 된다” 문제 감소
- IDP onboarding template에 심기 쉬움 [1][29]

### 2.5. 아쉬운 점 / 리스크

#### 2.5.1. 플랫폼 제품이 아니라 로컬 작업 하네스다

gstack는 **조직 단위 자산 카탈로그, RBAC, 중앙 정책, 점수 카드, 환경 수명주기, 기능 플래그, DORA/SEI 대시보드**를 제공하지 않습니다.  
따라서 플랫폼 엔지니어링의 control plane을 대체하진 못합니다. Harness IDP/CI/CD/FF/SEI와 경쟁하기보다, 그 위 또는 옆에서 **개발자 개인 작업 효율을 올리는 용도**가 더 맞습니다. [10][11][12][13][14][15][27]

#### 2.5.2. 매우 빠르게 변하는 프로젝트다

2026-03-24 기준 changelog는 **0.11.14.0**이며, 같은 날짜에 여러 릴리스 수준 변경이 이어지고 있습니다. GitHub 페이지상 **formal release는 아직 publish되지 않았고**, 활발한 커뮤니티 PR과 수정이 계속 들어옵니다. [5][6][28]

이 말은 곧:

- 기능이 빠르게 좋아진다
- 동시에 팀 표준으로 채택할 때는 **벤더링/버전 고정**이 필수다
- “중앙 최신 버전 자동 추종”은 위험할 수 있다

#### 2.5.3. 보안/개인정보 검토가 필요하다

gstack 자체는 로컬 브라우저와 로컬 로그 기반이며, 브라우저 쿠키 import도 비교적 조심스럽게 설계되어 있습니다.  
예를 들어 state file은 owner-only 권한을 사용하고, 서버는 localhost 바인딩과 bearer token을 사용하며, 쿠키 값은 평문으로 기록하지 않는다고 설명합니다. 텔레메트리는 기본 off이며 opt-in입니다. [1][2][3]

그래도 HR/재무/보안 시스템에 적용할 때는 별도 검토가 필요합니다.

- 어떤 AI 런타임(Claude Code/Codex/Kiro)에 코드/프롬프트가 전달되는가
- 브라우저 쿠키 import를 허용할 것인가
- staging 데이터는 충분히 마스킹되었는가
- 로컬 로그/스크린샷 산출물 보관정책은 있는가

#### 2.5.4. 오래된 모놀리식 시스템은 “하네스”가 더 중요하다

레거시 JSP/Oracle/Tibero 시스템에서 문제는 “에이전트가 코드를 못 쓴다”가 아니라 보통 다음입니다.

- 설계 문서 부재
- 테스트 부재
- 화면-쿼리-패키지-배치 의존관계 불명확
- 운영 데이터 없이는 재현 불가
- 배포/롤백 체계 취약

즉, **gstack를 잘 쓰려면 먼저 레거시 프로젝트를 에이전트가 읽을 수 있는 상태로 만드는 작업**이 선행되어야 합니다. 이 부분은 OpenAI가 말하는 harness engineering의 핵심과도 닿아 있습니다. [7][8][9]

---

## 3. gstack와 OpenAI식 “Harness Engineering” 비교

### 3.1. 공통점

OpenAI는 harness engineering을 **“모델 자체보다, 에이전트가 안정적으로 일할 수 있는 환경/문서/피드백 루프를 설계하는 일”**로 설명합니다.  
핵심 메시지는 다음과 같습니다.

- 인간은 조종하고, 에이전트는 실행한다 [7]
- 엔지니어 역할은 코드 작성보다 시스템/스캐폴딩/레버리지 설계로 이동한다 [7]
- 거대한 단일 AGENTS 문서보다, repo 내 구조화된 docs를 system of record로 삼는다 [7]
- UI/로그/메트릭/브라우저를 에이전트가 읽을 수 있게 만들어야 한다 [7]
- 아키텍처와 taste는 “원칙/불변식”으로 강제해야 한다 [7]
- 테스트/검증/리뷰/복구 루프가 많아질수록 에이전트 autonomy가 올라간다 [7]

gstack는 이 철학을 상당 부분 **제품화/도구화**한 사례로 볼 수 있습니다.

- `CLAUDE.md`, 설계 문서, review dashboard, docs update 루프 [1][3][4]
- 브라우저 자동화와 UI legibility 강화 [2][3]
- `/review`, `/qa`, `/cso`, `/ship` 같은 피드백 루프 [1][30]
- `/freeze`, `/guard` 같은 실행 경계 설정 [1][30]
- “Search Before Building”, “Boil the Lake” 같은 내장 원칙 [3][31]

즉, **gstack는 harness engineering의 실전 패키지 구현체**에 가깝습니다.

### 3.2. 차이점

하지만 둘은 초점이 다릅니다.

| 항목 | OpenAI식 harness engineering | gstack |
|---|---|---|
| 본질 | 설계 원칙/운영 철학/에이전트 시스템 공학 | 바로 쓸 수 있는 로컬 워크플로 스택 |
| 중심 | repo legibility, autonomy, agent loop, system of record | slash command 기반 역할 수행 + persistent browser |
| 런타임 | Codex harness / App Server / agent loop [8][9] | Claude/Codex/Kiro용 skill + local browser daemon [1][2][29] |
| 범위 | 제품/클라이언트/프로토콜까지 포괄 | 개발자 로컬 실행과 팀 워크플로에 집중 |
| 조직화 수준 | 개념적/플랫폼적 | 매우 실무적/즉시 사용 가능 |

OpenAI의 Codex harness는 여러 surface(TUI, IDE, 앱, 웹)를 공유하는 **App Server + JSON-RPC 프로토콜 + thread lifecycle** 중심입니다. [8][9]  
반면 gstack는 **“개발자가 지금 당장 레포 안에서 어떤 순서로 무엇을 시킬지”**에 최적화되어 있습니다. [1][2][30]

### 3.3. 판단

정리하면:

- **철학적으로**: gstack는 harness engineering과 같은 방향이다.
- **구현적으로**: gstack는 Claude/Codex/Kiro용으로 강하게 의견이 들어간 “하네스 패키지”다.
- **전략적으로**: “harness engineering을 하겠다”는 조직 목표 아래, gstack는 **로컬 실행 레이어**로 채택 가능하다.

---

## 4. gstack와 Harness(회사 플랫폼) 비교

### 4.1. Harness IDP/CI/CD 쪽이 하는 일

Harness IDP는 개발자가 소프트웨어를 **생성·탐색·관리**하게 하면서, 플랫폼 팀은 표준과 거버넌스를 자동화하는 포털입니다.  
핵심 pillar는 **Software Catalog, Workflows, Scorecards, Environment Management, Plugins, TechDocs**입니다. [10]

세부적으로 보면:

- **Software Catalog**: 서비스/API/라이브러리/웹사이트/DB 등을 한 곳에서 검색·소유자·의존관계 관리 [10][11]
- **Workflows**: `workflow.yaml` 기반 self-service workflow, Backstage Templates에서 영감 [18]
- **Scorecards**: 품질/표준 준수 평가, 점수화, 추세 추적 [12][23]
- **TechDocs**: Markdown/MkDocs 기반 docs-as-code [20][23]
- **Environment Management**: IDP+IaCM+CD를 묶은 self-service 환경 생성/운영 [15]
- **CI/CD**: step library, visual controls, approval gates, 다른 모듈과 통합 [13][24]
- **Feature Flags**: GitOps/파이프라인/자동화/모니터링 기반 기능 롤아웃 [14]
- **SEI**: DevOps 데이터 기반 병목/생산성/개발 경험 가시화 [27]

즉, Harness는 **중앙 플랫폼**입니다.

### 4.2. gstack가 하는 일

반면 gstack는 중앙 플랫폼이 아니라 **개발자 작업 런타임**입니다.

- 로컬에서 에이전트가 레포를 읽고
- 브라우저를 조작하고
- 설계/리뷰/QA/배포 준비를 진행하며
- 문서와 산출물을 남긴다 [1][2][3][30]

### 4.3. 둘의 관계: 대체인가, 보완인가

대체라기보다 다음처럼 분리해서 보는 것이 정확합니다.

| 층위 | gstack | Harness |
|---|---|---|
| 주 사용처 | 개발자 로컬/에이전트 세션 | 조직 중앙 플랫폼 |
| 핵심 가치 | 작업 실행, 리뷰, QA, 브라우저 검증, 문서 루프 | 온보딩, 카탈로그, 거버넌스, 배포, 롤아웃, 지표 |
| 강점 | 빠른 실행, 역할 기반 스킬, 실사용 QA | 표준화, RBAC, workflow, scorecard, env lifecycle |
| 약점 | 중앙 통제/정책/자산 관리 부족 | 개발자 개별 agent workflow 세밀 제어는 상대적으로 약함 |

따라서 **“Harness가 있으면 gstack가 불필요하다”도 아니고, “gstack가 있으면 Harness가 필요 없다”도 아닙니다.**

실무 권고는 아래와 같습니다.

- **Harness = control plane**
- **gstack = execution plane on developer workstation**

---

## 5. gstack를 Harness 안에 “추가”할 수 있는가

### 5.1. 직접 내장: 권장하지 않음

Harness IDP custom plugin은 **Backstage 기반 frontend plugin**을 추가하는 구조입니다.  
문서상 custom plugin은 private frontend plugin을 붙일 수 있지만, **custom backend를 같이 넣는 방식은 지원하지 않습니다.** 필요 시 backend proxy/delegate proxy로 “기존 API”를 프록시하는 모델입니다. [16][17]

문제는 gstack가 다음을 필요로 한다는 점입니다.

- 로컬 Git workspace
- 로컬 파일시스템
- 로컬 브라우저/쿠키/세션
- Bun/Playwright/Chromium
- developer-machine context

즉, gstack는 **IDP 브라우저 화면 안에서 돌아가는 프론트엔드 위젯**이 아닙니다.  
그래서 “Harness IDP custom plugin으로 gstack 자체를 직접 실행”하는 모델은 **구조적으로 맞지 않습니다.**

### 5.2. 간접 연계: 매우 현실적이고 권장됨

#### A. IDP Workflow로 gstack 포함 템플릿 생성 — **권장도 최고**

Harness Workflow는 `workflow.yaml`을 Template로 저장하고, frontend input / backend action / outputs를 정의할 수 있습니다. [18]  
Java 서비스 온보딩이나 IDP Stage 온보딩 튜토리얼처럼 **서비스 생성용 self-service onboarding flow**를 만들 수 있습니다. [19][21]

여기에 gstack를 넣는 가장 좋은 방식은 다음입니다.

- 새 서비스 생성 시 repo scaffold
- `.claude/skills/gstack/` 벤더링
- `CLAUDE.md` 기본 정책 생성
- `docs/`, `mkdocs.yml`, `catalog-info.yaml`, `.harness/` 생성
- 기본 CI/CD 파이프라인, PR 템플릿, 테스트 스켈레톤 추가

즉, **gstack를 “도구로 실행”하는 게 아니라 “레포 표준 구성요소로 주입”**하는 것입니다.

#### B. Software Catalog + TechDocs + Ingestion API 연계 — **권장**

Software Catalog는 조직 소프트웨어 자산의 단일 진실 공급원 역할을 하고, TechDocs는 Git 기반 docs-as-code를 지원합니다. [11][20][23]  
또 Catalog Ingestion API는 `catalog-info.yaml`을 직접 수정하지 않고도 메타데이터를 주입할 수 있습니다. [22]

이걸 gstack와 연결하면:

- 서비스별 gstack 채택 여부
- 최신 QA 리포트 링크
- `/review` 결과 요약
- 테스트 커버리지 증감
- owner / team lead / on-call 등

같은 정보를 Catalog에 넣어 **“에이전트 작업 품질”을 중앙에서 볼 수 있는 메타데이터**로 만들 수 있습니다.

#### C. Scorecards + OPA Governance로 준수 강제 — **권장**

Harness Scorecards는 품질/모범사례 준수를 점수화하고, Trends Dashboard로 추세를 보여줍니다. [12][23]  
또 OPA 기반 정책을 scorecard 결과와 묶어 governance에 활용할 수 있습니다. [24]

예를 들어 다음 체크를 만들 수 있습니다.

- `CLAUDE.md` 존재 여부
- `docs/architecture/` 최신성
- 최소 테스트 수 또는 smoke test 존재
- PR 전에 `/review` 산출물 업로드 여부
- 보안 민감 서비스는 `/cso` 결과 필요
- 운영 배포 전 rollback 문서 필수

이 부분은 gstack가 혼자서는 못 하는 **조직 차원의 enforce**입니다.

#### D. CI/CD / FF / Environment Management 연계 — **강력 권장**

Harness CI는 다른 Harness 모듈과 통합되고, Step Library를 제공합니다. [13][24]  
Feature Flags는 rollout 통제에 쓰이고 [14], Environment Management는 IDP+IaCM+CD를 묶어 self-service 환경 생성/운영을 제공합니다. [15]

실전에서 가장 좋은 조합은:

- **개발/리뷰/QA 준비는 gstack**
- **빌드/배포/환경/롤아웃/가드레일은 Harness**

입니다.

#### E. IDP custom plugin으로 “gstack 자체”를 감싸는 것 — **낮은 ROI**

이론상 다음도 가능합니다.

- 별도 외부 서비스로 gstack orchestration API를 만든다
- Harness custom frontend plugin이 그 API를 proxy로 호출한다 [17]
- UI에서 gstack 리포트/세션/작업 버튼을 노출한다

하지만 이 방식은 다음 이유로 권장하지 않습니다.

- gstack의 본질이 로컬 개발자 컨텍스트인데 중앙 서버형으로 바뀜
- 인증/권한/작업공간 분리/브라우저 세션 보안이 복잡
- 커스텀 백엔드를 IDP plugin 내부에 넣을 수 없음 [17]
- 운영비가 높고, gstack의 장점(로컬 즉시성)이 줄어듦

### 5.3. 최종 판단

**가능한 추가 방식**
1. **레포 템플릿/워크플로로 포함** → 매우 추천  
2. **Catalog/Scorecard/TechDocs/CI와 연결** → 매우 추천  
3. **IDP plugin으로 리포트 시각화** → 조건부 추천  
4. **IDP 내부에서 gstack 런타임 자체 실행** → 비추천  

---

## 6. 기존 인사시스템(레거시: JSP / Java / Oracle / Tibero PL/SQL) 유지보수에 어떻게 적용할까

### 6.1. 전제: “자동 코더”로 바로 투입하면 실패 확률이 높다

이런 시스템은 보통 다음 특징을 가집니다.

- 화면(JSP), 비즈니스 로직(Java), SQL/PLSQL, 배치가 강하게 얽혀 있음
- 운영 규칙이 DB 패키지/프로시저에 숨어 있음
- 테스트가 적고, 화면별 수동 검증이 많음
- HR 개인정보/권한 규칙 때문에 staging 접근이 민감함

따라서 gstack를 바로 “큰 수정 자동화” 용도로 쓰기보다, **처음에는 문맥 복원 + 영향도 분석 + 브라우저 검증 + 릴리즈 체크리스트 보조**에 쓰는 것이 맞습니다.

### 6.2. 권장 도입 단계

#### 1단계: Read-only 분석 모드부터

초기 2~4주는 아래만 수행하는 것이 좋습니다.

- `/investigate`: 장애/버그 원인분석
- `/review`: 변경 diff 리뷰
- `/qa-only`: staging 버그 리포트만 생성
- `/cso`: 인증/권한/개인정보 처리 리뷰
- `/document-release`: 운영문서, 화면 설명, 배치 문서 정리

이 단계의 목적은 “코드를 자동 수정”이 아니라, **레거시 시스템을 에이전트 친화적으로 다시 읽히게 만드는 것**입니다.

#### 2단계: 영역 고정(boundary) 후 소규모 수정

이후에는 반드시 `/freeze` 또는 `/guard`를 사용해 수정 영역을 좁혀야 합니다. [1][30]

예시:

- `src/main/webapp/hr/leave/*`
- `src/main/java/com/company/hr/leave/*`
- `db/plsql/leave/*`

이렇게 한정된 범위에서만

- JSP validation 수정
- Java service null/exception 처리
- SQL where 절 보정
- 화면 라벨/메시지/권한 조건 수정

같은 작은 변경부터 허용하는 것이 좋습니다.

#### 3단계: QA 자동화와 회귀 테스트 확보

gstack의 `/qa`는 브라우저 기반 검증과 회귀 테스트 생성 쪽이 강점입니다. [30]  
레거시 HR 시스템에 특히 가치가 큰 부분은 다음입니다.

- 로그인
- 사번 조회/인사카드 조회
- 휴가 신청/승인
- 조직도 검색
- 급여 마감 화면
- 인사발령 등록
- 권한별 메뉴 노출

이런 핵심 경로만이라도 smoke/regression 시나리오로 쌓이면, 이후부터는 gstack의 효율이 급격히 올라갑니다.

#### 4단계: `/ship`은 “준비가 된 뒤에만”

`/ship`은 테스트 프레임워크 부트스트랩, coverage audit, PR 생성까지 담당하도록 설계되어 있습니다. [30]  
하지만 레거시 HR에서는 아래가 준비되기 전까지는 **PR 준비까지만** 쓰고, `/land-and-deploy`는 보류하는 것이 안전합니다.

- CI가 안정적으로 돈다
- rollback 절차가 표준화되어 있다
- DB 변경 script와 app 배포 절차가 분리/명문화되어 있다
- 운영/개발/DBA 승인 흐름이 정리되어 있다

### 6.3. 레거시 HR 유지보수에서 가장 유용한 적용 패턴

#### 패턴 A. 화면 버그 수정

예: 휴가 신청 화면에서 특정 조건에서 validation이 깨짐

권장 흐름:

1. `/investigate`로 재현 조건, 관련 JSP/Controller/Service/SQL 파악  
2. `/qa-only`로 staging에서 사용자 플로우와 스크린샷 확보  
3. 수정 범위를 `/freeze`  
4. 작은 수정  
5. `/review`  
6. `/qa`로 재검증  
7. `/document-release`로 변경 이력과 운영 영향 문서화

#### 패턴 B. PL/SQL 영향도 분석

예: 급여 계산 패키지 수정 요청

권장 흐름:

1. 코드 수정 전에 `/investigate`로 관련 package/procedure/caller 추적  
2. 영향 객체 목록 생성  
   - 호출 Java class  
   - Mapper/DAO  
   - 배치 job  
   - 화면/메뉴  
   - 스케줄러  
3. DBA 리뷰 전용 문서 생성  
4. 실제 SQL/PLSQL 수정은 report-first, human-reviewed로 진행

여기서 gstack의 역할은 **“변경을 바로 밀어 넣는 것”보다 “영향도와 검증 포인트를 빠짐없이 뽑는 것”**입니다.

#### 패턴 C. 권한/보안 이슈

HR 시스템은 권한 문제가 매우 치명적입니다.  
`/cso`를 정기적으로 적용해 다음을 점검하는 것이 좋습니다. [1][30]

- 메뉴/URL direct access
- 권한 없는 데이터 조회
- 개인정보 마스킹 누락
- 관리자/일반 사용자 경계
- 감사로그 부족

이건 신규 개발보다 오히려 레거시에 더 가치가 큽니다.

### 6.4. 레거시 HR 프로젝트에 넣을 운영 규칙(권장)

`CLAUDE.md` 혹은 팀 표준 규칙에 최소한 아래를 넣는 것을 권합니다.

#### 권장 규칙 예시

```md
## Legacy HR System Rules

- Default mode for DB-sensitive tasks is report-first.
- Never execute destructive SQL automatically.
- Do not generate or run DROP/TRUNCATE/DELETE/UPDATE scripts without explicit approval.
- For PL/SQL changes, always produce:
  1. caller impact map
  2. rollback plan
  3. test scenario list
- Use /guard for any task touching:
  - payroll
  - personnel master
  - authorization
  - batch jobs
- Use /freeze to keep edits inside the approved package/screen/module.
- Before any code change, identify:
  - JSP / Controller / Service / SQL / Procedure dependency chain
- Prefer /qa-only on staging for sensitive flows unless explicit approval exists for auto-fix.
```

### 6.5. 레거시 적용 시 현실적인 한계

- **테스트 데이터가 없으면** `/qa` 가치가 제한됨
- **운영과 비슷한 staging이 없으면** 브라우저 자동화가 의미가 줄어듦
- **스크립틀릿 JSP / 초대형 패키지 / 동적 SQL**이 많으면 model 오류 가능성이 커짐
- **Tibero/Oracle 패키지의 숨은 업무 규칙**은 사람이 결국 승인해야 함

따라서 레거시에서는 gstack를 **“autonomous developer”**보다 **“고급 분석/리뷰/QA 조교”**로 두는 것이 초기 성공 확률이 가장 높습니다.

### 6.6. 레거시 인사시스템에 대한 최종 권고

**적용 가능**합니다.  
다만 성공 패턴은 다음입니다.

- 처음부터 대규모 자동 구현 X
- 문서화/영향도 분석/브라우저 검증/보안 리뷰부터 시작
- `/freeze`, `/guard`를 기본으로 사용
- DBA/업무담당자 승인 루프를 하네스에 포함
- 테스트와 smoke scenario를 조금씩 축적

즉, **레거시에 gstack를 적용하는 일 자체가 곧 harness engineering 작업**입니다.

---

## 7. 신규 개발에는 어떻게 활용할까

신규 개발에서는 gstack의 효율이 훨씬 높습니다.  
왜냐하면 신규 프로젝트는 처음부터 **에이전트 친화적인 repo 구조와 feedback loop**를 설계할 수 있기 때문입니다. [7][20][23]

### 7.1. 가장 좋은 사용 방식

신규 개발에서는 아래 흐름을 표준화하는 것이 좋습니다.

1. `/office-hours`  
2. `/plan-ceo-review`  
3. `/plan-design-review` 또는 `/design-consultation`  
4. `/plan-eng-review` 또는 `/autoplan`  
5. 구현  
6. `/review`  
7. `/qa`  
8. `/cso`  
9. `/ship`  
10. `/document-release`  
11. `/retro` [1][30]

이 순서는 단지 멋있어 보이는 절차가 아니라, **에이전트 품질 편차를 줄이는 장치**입니다.

### 7.2. Harness와 같이 쓸 때의 이상적인 구성

신규 개발에서는 **Harness + gstack 조합이 가장 깔끔**합니다.

#### 개발자 로컬(Execution Plane)

- gstack
- Claude/Codex/Kiro
- 로컬 브라우저 검증
- 설계/리뷰/QA/문서화

#### 조직 플랫폼(Control Plane)

- Harness IDP Workflow: 서비스 생성/표준 템플릿 [10][18][19][21]
- Software Catalog: 서비스 메타데이터/소유권/의존성 [11]
- TechDocs: docs-as-code 게시 [20][23]
- Scorecards/OPA: 품질/표준 준수 강제 [12][23][24]
- CI/CD: 빌드/테스트/배포 [13][24]
- Feature Flags: 점진적 롤아웃 [14]
- Environment Management: ephemeral/long-lived env lifecycle [15]
- SEI: 팀/조직 단위 지표 관찰 [27]

### 7.3. 신규 서비스 템플릿에 미리 넣어야 할 것

Harness IDP Workflow 또는 Cookiecutter onboarding으로 아래를 기본 제공하는 것을 추천합니다. [18][19][21]

- `.claude/skills/gstack/`
- `CLAUDE.md`
- `docs/`
- `docs/designs/`
- `ARCHITECTURE.md`
- `mkdocs.yml`
- `catalog-info.yaml`
- `workflow.yaml`
- `.harness/`
- 기본 test framework
- PR template
- rollback/runbook skeleton
- feature flag bootstrap
- smoke test skeleton

이렇게 해야 gstack가 처음부터 높은 품질로 작동합니다.

### 7.4. 신규 개발에서 gstack가 특히 강한 영역

#### A. 아이디어를 더 좋은 제품 정의로 바꾸기

`/office-hours`, `/plan-ceo-review`는 단순 feature 요청을 더 높은 가치의 제품 문제로 재정의하는 데 강합니다. [1][30]

#### B. 설계/아키텍처/테스트를 구현 전에 끌어내기

`/plan-eng-review`가 다이어그램, 실패모드, 테스트 매트릭스를 요구하는 점은 신규 프로젝트에서 매우 유리합니다. [30]

#### C. UI/브라우저 품질 확보

`/plan-design-review`, `/design-review`, `/qa`의 조합은 프론트엔드 품질 초기에 특히 강력합니다. [30]

#### D. 문서와 회고를 자동으로 남기기

신규 프로젝트는 초기에 문서화 습관을 만들기가 쉬우므로 `TechDocs + /document-release + /retro` 조합이 잘 맞습니다. [20][23][30]

### 7.5. 신규 개발에서의 실제 운영 권고

- 작은 feature 단위 PR
- 서비스 생성 시 gstack 벤더링
- 기본적으로 `/review`, `/qa`, `/cso`를 merge gate 근처에 둠
- Harness Scorecards로 “문서/테스트/보안 체크” 점수화
- Feature Flag로 risky feature는 점진 오픈
- Environment Management로 preview/ephemeral env 운영 [12][14][15]

---

## 8. “gstack + Harness” 권장 목표 아키텍처

```text
[Developer Workstation]
  └─ gstack + Claude/Codex/Kiro
      ├─ /office-hours
      ├─ /plan-*
      ├─ /review
      ├─ /qa
      ├─ /cso
      └─ /ship
            ↓
         Git PR / Artifacts / Docs

[Harness IDP]
  ├─ Workflow (service scaffolding / repo bootstrap)
  ├─ Software Catalog (owner, system, metadata)
  ├─ TechDocs (docs-as-code)
  ├─ Scorecards (quality gates)
  ├─ OPA Governance
  ├─ CI/CD
  ├─ Feature Flags
  ├─ Environment Management
  └─ SEI dashboards
```

핵심은 다음입니다.

- **gstack는 “사람+에이전트 작업 방식”을 표준화**
- **Harness는 “조직 플랫폼과 통제 방식”을 표준화**

---

## 9. 최종 추천안

### 9.1. 레거시 인사시스템

**권장 전략: 보수적 도입**

- 1차: 분석/리뷰/문서화/QA-only
- 2차: bounded edit (`/freeze`, `/guard`)
- 3차: smoke/regression 확보
- 4차: PR 준비 자동화
- 배포 자동화는 가장 나중

**핵심 메시지**  
레거시 HR에서는 gstack를 “자동 개발자”로 보지 말고, **영향도 분석 + 브라우저 검증 + 문서 복원기**로 써야 성공합니다.

### 9.2. 신규 개발

**권장 전략: 기본 작업 하네스로 채택**

- 신규 서비스 생성 템플릿에 gstack 포함
- Harness IDP Workflow로 자동 scaffold
- Scorecards/OPA로 준수 강제
- CI/CD/FF/Env Mgmt는 Harness에 맡김

**핵심 메시지**  
신규 개발에서는 gstack 효과가 매우 큽니다. 특히 초반에 repo 구조, 문서 구조, 테스트 구조를 잘 잡으면 OpenAI가 말하는 harness engineering의 효과를 실무적으로 얻을 수 있습니다. [7][8][9]

### 9.3. Harness 안에 넣을 수 있는가

- **직접 런타임 내장**: 비추천
- **Workflow/Template로 포함**: 적극 추천
- **Catalog/Scorecard/Docs/CI와 연결**: 적극 추천
- **Plugin으로 리포트 표면화**: 조건부 추천

---

## 10. 실행 우선순위 제안

### 레거시 HR 프로젝트
1. `CLAUDE.md` / 시스템 규칙 작성  
2. 화면-서비스-SQL-패키지 dependency map 생성  
3. staging smoke path 정의  
4. `/review`, `/investigate`, `/qa-only`, `/cso`부터 사용  
5. 작은 영역만 `/freeze` 후 수정 허용  

### 신규 프로젝트
1. Harness IDP workflow template 설계  
2. gstack 벤더링 포함  
3. TechDocs / Catalog / Scorecards 기본값 설정  
4. CI/CD / FF / Environment Management 연결  
5. `/review`, `/qa`, `/cso`를 팀 표준에 포함  

---

## 11. 참고 문헌 / 원문

[1] gstack README  
https://raw.githubusercontent.com/garrytan/gstack/main/README.md

[2] gstack BROWSER.md  
https://raw.githubusercontent.com/garrytan/gstack/main/BROWSER.md

[3] gstack ARCHITECTURE.md  
https://raw.githubusercontent.com/garrytan/gstack/main/ARCHITECTURE.md

[4] gstack SKILL.md  
https://raw.githubusercontent.com/garrytan/gstack/main/SKILL.md

[5] gstack CHANGELOG.md  
https://raw.githubusercontent.com/garrytan/gstack/main/CHANGELOG.md

[6] GitHub Repository Page: garrytan/gstack  
https://github.com/garrytan/gstack

[7] OpenAI — Harness engineering: leveraging Codex in an agent-first world  
https://openai.com/index/harness-engineering/

[8] OpenAI — Unlocking the Codex harness: how we built the App Server  
https://openai.com/index/unlocking-the-codex-harness/

[9] OpenAI — Unrolling the Codex agent loop  
https://openai.com/index/unrolling-the-codex-agent-loop/

[10] Harness IDP Overview  
https://developer.harness.io/docs/internal-developer-portal/overview/

[11] Harness Software Catalog Overview  
https://developer.harness.io/docs/internal-developer-portal/catalog/overview/

[12] Harness Scorecards Overview  
https://developer.harness.io/docs/internal-developer-portal/scorecards/scorecard/

[13] Harness CI Overview  
https://developer.harness.io/docs/continuous-integration/get-started/overview/

[14] Harness Feature Flags Overview  
https://developer.harness.io/docs/feature-flags/get-started/overview/

[15] Harness Environment Management Overview  
https://developer.harness.io/docs/internal-developer-portal/environment-management/overview/

[16] Harness Custom Plugins Overview  
https://developer.harness.io/docs/internal-developer-portal/plugins/custom-plugins/overview/

[17] Harness IDP Plugins Architecture  
https://developer.harness.io/docs/internal-developer-portal/plugins/delegate-proxy/

[18] Harness Workflow YAML  
https://developer.harness.io/docs/internal-developer-portal/flows/worflowyaml/

[19] Harness Java Onboarding Pipeline Tutorial  
https://developer.harness.io/docs/internal-developer-portal/tutorials/java-onboarding-pipeline/

[20] Harness TechDocs Setup  
https://developer.harness.io/docs/internal-developer-portal/catalog/integrate-tools/techdocs/enable-docs/

[21] Harness Service Onboarding Pipeline (IDP Stage)  
https://developer.harness.io/docs/internal-developer-portal/tutorials/service-onboarding-with-idp-stage/

[22] Harness Catalog Ingestion API  
https://developer.harness.io/docs/internal-developer-portal/catalog/catalog-ingestion/catalog-ingestion-api/

[23] Harness View Scorecard Results  
https://developer.harness.io/docs/internal-developer-portal/scorecards/view-scorecard/

[24] Harness OPA + Scorecards Tutorial  
https://developer.harness.io/docs/internal-developer-portal/tutorials/opa-scorecards/

[25] Harness IDP 2.0 Overview  
https://developer.harness.io/docs/internal-developer-portal/idp-2o-overview/2-0-overview-and-upgrade-path/

[26] Harness IDP Self-Managed Edition Support  
https://developer.harness.io/docs/internal-developer-portal/smp/whats-supported/

[27] Harness Software Engineering Insights Overview  
https://developer.harness.io/docs/software-engineering-insights/propelo-sei/get-started/overview/

[28] gstack package.json  
https://raw.githubusercontent.com/garrytan/gstack/main/package.json

[29] gstack setup script  
https://github.com/garrytan/gstack/blob/main/setup

[30] gstack Skill Deep Dives  
https://raw.githubusercontent.com/garrytan/gstack/main/docs/skills.md

[31] gstack Builder Ethos  
https://raw.githubusercontent.com/garrytan/gstack/main/ETHOS.md
