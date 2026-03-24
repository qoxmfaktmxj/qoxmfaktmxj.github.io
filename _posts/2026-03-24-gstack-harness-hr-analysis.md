---
layout: post
title: "gstack 상세 분석: Harness 엔지니어링, 레거시 HR, 신규 개발 적용 전략"
date: 2026-03-24 23:50:00 +0900
categories: [ai]
tags: [ai, gstack, harness-engineering, harness, developer-tools, legacy, hr, idp]
---

# gstack 레포 분석 및 OpenAI `harness engineering` 관점 적용 보고서

- 작성일: 2026-03-24
- 기준 관점: ** OpenAI가 말하는 “harness engineering”**  
  즉, 에이전트가 신뢰성 있게 일하도록 **환경(runtime), 문서/지식, 규칙/가드레일, 테스트/평가, 피드백 루프**를 설계하는 엔지니어링 방식으로 해석했다. [R1][R2][R4]
- 분석 대상:
  1. `garrytan/gstack` 레포의 구조와 설계
  2. OpenAI식 harness engineering과의 비교
  3. 기존 인사시스템(레거시: JSP, Java, Oracle, Tibero/PL-SQL) 유지보수에의 적용 방식
  4. 신규 개발 시 활용 방식

---

## 1. 결론 요약

### 한 줄 결론
**gstack는 “harness engineering 전체”가 아니라, 그 안에 들어가는 강력한 `실행/워크플로/브라우저 skill 계층`이다.**  
OpenAI식 harness engineering 전체를 대체하지는 못하지만, 그 안에 **매우 현실적으로 편입 가능한 구성요소**다. 특히 **반복 가능한 개발 workflow skill**, **지속형 브라우저 런타임**, **로컬 QA/검증 루프** 측면에서는 강하다. [R1][R2][R3][R8][R9][R10]

### 핵심 판단
1. **gstack 자체의 정체성**
   - gstack는 Garry Tan이 쓰는 agentic 개발 workflow를 skill 묶음과 브라우저 도구로 오픈소스화한 것이다.
   - 핵심은 “slash-command 기반 역할형 workflow”와 “지속형 Chromium daemon”이다. [R8][R9][R10]

2. **OpenAI harness engineering 대비 위치**
   - OpenAI가 말하는 harness engineering은 더 상위 개념이다.  
     핵심 문제를 “에이전트가 일할 환경이 underspecified 되어 있다”는 데서 보고,  
     이를 해결하기 위해 **repo-local 문서 체계, AGENTS.md, PLANS.md, custom lint, structural test, eval, recurring cleanup task, CI/feedback loop**를 만든다. [R1][R2][R4][R5][R6][R7]
   - gstack는 이 전체 체계 중에서 **skill + browser runtime + 일부 safety/test/doc generation**을 제공한다.  
     즉, **OpenAI식 harness engineering의 하위 레이어 중 하나**라고 보는 것이 정확하다. [R1][R2][R3][R8][R9]

3. **OpenAI식 harness 안에 넣을 수 있는가**
   - **예, 넣을 수 있다.** 기술적으로도 gstack는 Codex-compatible host를 위해 `.agents/skills/gstack` 또는 `~/.codex/skills/gstack` 설치를 지원한다. [R8][R11][R15]
   - 다만 “넣는다”의 의미는 **gstack 하나만 깔면 끝**이 아니라,
     - `AGENTS.md`
     - `PLANS.md`
     - `docs/` 지식 저장소
     - `scripts/`의 결정적(deterministic) 작업
     - repo-specific test/eval/CI
     를 같이 붙이는 형태여야 한다. [R1][R2][R5][R6][R7]

4. **레거시 인사시스템 적용**
   - 적용 가능하다.  
     하지만 **바로 자율 구현/배포 자동화로 가면 위험**하다.
   - 가장 맞는 시작점은:
     - `/investigate` 기반 원인분석
     - `/plan-eng-review` 기반 영향도 분석
     - `/review` 기반 PR 사전 검토
     - `/qa` 기반 staging UI 점검
     - `/document-release` 기반 문서 갱신
   - 반대로,
     - 생산 DB 직접 변경
     - payroll/평가/PII 규칙의 agent-only 승인
     - 테스트 없는 `/ship` 자동화
     는 초기에는 피해야 한다. [R6][R8][R9][R13]

5. **신규 개발 적용**
   - 신규 개발에서는 gstack가 훨씬 잘 맞는다.
   - 단, 베스트 프랙티스는 **gstack를 repo의 “표준 skill 세트”로 넣고**,  
     OpenAI식으로 **AGENTS.md + PLANS.md + docs + scripts + eval + CI**를 함께 설계하는 것이다. [R1][R2][R5][R6][R7]

---

## 2. gstack 상세 분석

## 2.1. gstack의 제품적 정체성

README 기준으로 gstack는 단순한 브라우저 툴이 아니다.  
Garry Tan은 이를 “Claude Code를 가상 엔지니어링 팀으로 바꾸는 skill 세트”로 설명한다.  
`/office-hours`, `/plan-ceo-review`, `/plan-eng-review`, `/review`, `/qa`, `/ship`, `/retro` 같은 역할형 skill들이 개발 스프린트 순서에 맞춰 배치되어 있으며, 전체 흐름은 **Think → Plan → Build → Review → Test → Ship → Reflect**다. [R8]

즉, gstack의 핵심 가치는 두 층이다.

1. **워크플로 층**
   - 개발 lifecycle을 역할별 skill로 분해해, agent가 빈 프롬프트로 방황하지 않게 한다.
   - “어떤 순서로, 어떤 성격의 판단을 하게 할 것인가”를 skill로 패키징한다. [R8][R13]

2. **실행 도구 층**
   - 특히 `/browse`가 제공하는 headless browser가 강력하다.
   - 단발성 Playwright 호출이 아니라, **지속형 브라우저 daemon**을 통해 로그인 상태, 탭, localStorage, 쿠키를 유지한다. [R9][R10]

이 조합 때문에 gstack는 단순 prompt collection보다 훨씬 실무적이다.  
반면, “repo 전체를 에이전트 친화적으로 만드는 상위 시스템”까지는 아니다.  
이 차이가 OpenAI식 harness engineering과의 핵심 구분점이다. [R1][R2]

---

## 2.2. 핵심 기술 아키텍처

### 2.2.1. 브라우저 런타임
gstack의 브라우저 레이어는 다음 구조다.

- `browse` CLI (컴파일된 바이너리)
- localhost HTTP 서버 (Bun)
- Playwright를 통한 headless Chromium
- workspace별 상태 파일 `.gstack/browse.json` [R9][R10][R11]

아키텍처 문서 기준으로:
- 첫 호출은 브라우저/서버 기동 때문에 약 3초 정도 걸릴 수 있고,
- 이후 호출은 HTTP POST + 기존 Chromium 세션 재사용으로 약 100~200ms 수준이다. [R9][R10]

이 설계는 QA, 로그인 유지, 반복 클릭, screenshot diff 같은 작업에서 매우 큰 차이를 만든다.  
OpenAI식 harness engineering 관점으로 보면, gstack는 **“환경(runtime)” 문제를 꽤 잘 푼 쪽**이다.  
OpenAI도 에이전트 성능 저하의 원인을 모델이 아니라 **환경의 underspecification**에서 찾았다. [R1][R4]

### 2.2.2. `@ref` 기반 상호작용
gstack는 Playwright locator를 직접 agent가 다루지 않고,  
`snapshot`에서 `@e1`, `@e2`, `@c1` 같은 ref를 부여해 agent가 그것을 다시 클릭/입력에 사용하게 만든다. [R9][R10]

이 방식의 장점은:
- CSS selector/XPath를 agent가 즉석에서 추측할 필요가 적다.
- DOM mutation에 의존하지 않는다.
- React/Vue/Svelte hydration이나 CSP 제약을 덜 탄다.
- stale ref를 빠르게 감지하게 설계되어 있다. [R9][R10]

레거시 JSP UI에서도 이 방식은 꽤 유효하다.  
JSP는 최신 SPA보다 DOM이 예측 가능한 편이어서, `snapshot → @ref → click/fill` 흐름이 오히려 안정적일 수 있다.  
반면 iframe-heavy 시스템이면 한계가 있다. 아키텍처 문서는 iframe support를 아직 의도적으로 미구현으로 둔다. [R9]

### 2.2.3. 로그/디버깅 능력
gstack 브라우저는 console/network/dialog를 ring buffer로 들고 가며, 디스크에도 append-only 로그를 남긴다. [R9][R10]

이 점은 레거시 운영 시스템 유지보수에서 중요하다.  
UI 자동화만으로는 안 잡히는 문제를:
- 브라우저 콘솔 에러
- 네트워크 실패
- confirm/prompt dialog
수준에서 빠르게 증거화할 수 있기 때문이다. [R10]

---

## 2.3. Skill 시스템과 workflow 설계

gstack의 skill들은 단순 “명령 모음”이 아니라, 각각 특정 역할을 갖는다. README와 skills 문서에서 확인되는 주요 skill은 다음과 같다. [R8][R13]

| 영역 | 대표 skill | 역할 |
|---|---|---|
| 문제 정의/재구성 | `/office-hours`, `/plan-ceo-review` | 요구를 다시 정의하고 제품 관점으로 재구성 |
| 설계/계획 | `/plan-eng-review`, `/plan-design-review`, `/autoplan` | 아키텍처, edge case, design 기준 확정 |
| 구현/디버깅 | `/investigate`, `/design-review` | root-cause 분석, UI 품질 개선 |
| 검토/보안 | `/review`, `/codex`, `/cso` | 코드리뷰, cross-model review, 보안 점검 |
| QA/성능/배포 | `/qa`, `/qa-only`, `/benchmark`, `/ship`, `/land-and-deploy`, `/canary` | UI 검증, 성능 baseline, PR/배포/운영 관찰 |
| 문서/회고 | `/document-release`, `/retro` | 문서 갱신, 주간 회고 |
| 안전장치 | `/careful`, `/freeze`, `/guard`, `/unfreeze` | 파괴 명령 경고, 편집 경계 설정 |

이 구조는 OpenAI가 말하는 skill 개념과 잘 맞는다.  
OpenAI는 skill을 “versioned bundle of files + `SKILL.md` manifest”로 정의하고, 반복 가능한 workflow를 codify하는 방식으로 설명한다. [R2][R3]

또한 OpenAI 문서에 따르면 Codex는 모든 skill의 메타데이터(`name`, `description`)만 먼저 보고, 실제 `SKILL.md` 전체는 그 skill을 쓰기로 결정할 때만 로드한다. 즉 **progressive disclosure** 모델이다. [R3][R6]  
gstack처럼 skill 수가 많은 레포에서는 이 특성이 매우 중요하다.  
한 번에 모든 skill instruction을 context에 밀어 넣는 방식이면 금방 무너진다.

---

## 2.4. 문서 생성, 검증, 안전장치

### 2.4.1. SKILL 문서 자동 생성
gstack 아키텍처 문서는 SKILL.md를 hand-maintained 문서로 두지 않고, template + source metadata로 생성한다고 설명한다. [R9]

핵심은:
- template에는 사람이 써야 할 workflow prose를 두고,
- 실제 command reference, snapshot flags, preamble 등은 source에서 채운다. [R9]

이 접근은 OpenAI식 harness engineering의 “문서를 system of record로 두되, 기계적으로 검증 가능한 형태로 만든다”는 방향과 잘 맞는다. [R1]

### 2.4.2. 테스트/평가
gstack는 적어도 프로젝트 자체에는 다음 성격의 검증 체계를 가진다.

- static validation
- E2E via `claude -p`
- LLM-as-judge 평가 tier [R9]
- `package.json`의 `test:evals`, `test:e2e`, `skill:check` 등 관련 스크립트 [R11]

OpenAI도 skill 개선은 결국 eval로 해야 한다고 말한다.  
“느낌상 더 좋아 보인다”가 아니라, skill invocation / expected commands / conventions / efficiency를 측정 가능한 기준으로 봐야 한다는 것이다. [R5]

다만 중요한 점은, **gstack가 자기 자신을 어느 정도 검증한다고 해서 당신의 업무 시스템이 자동으로 검증되는 것은 아니다.**  
예를 들어 인사시스템의 급여 산식 변경, 휴가 발생 로직, 조직도 권한 승계는 **별도 repo-specific eval**이 필요하다.  
이 부분이 gstack 단독 도입의 가장 흔한 오해다. [R1][R5][R6]

### 2.4.3. Safety / Security
gstack는 다음 방면에서 괜찮은 안전장치를 갖는다.

- `careful/freeze/guard`로 파괴적 명령/편집 범위를 제어 [R8][R13]
- browse 서버는 localhost 바인딩 + bearer token + `0600` state file [R9]
- cookie import는 DB read-only, in-memory decrypt, 민감값 로그 미노출 방향 [R9]
- telemetry는 opt-in이며 로컬 analytics도 제공 [R8]

레거시 HR처럼 PII/급여정보가 있는 시스템에서는 이 정도로는 충분하지 않지만, 최소한의 기반은 있다.

---

## 2.5. 강점

### 강점 1. 브라우저 기반 검증이 실용적이다
OpenAI식 harness engineering에서 runtime/tooling은 매우 중요하다.  
gstack의 browse는 이 부분을 잘 푼 사례다.  
특히 UI가 핵심인 레거시 업무 시스템이나 관리형 내부 시스템에서는 가치가 크다. [R1][R4][R9][R10]

### 강점 2. skill이 lifecycle 단위로 잘 나뉘어 있다
`/office-hours`로 문제 재정의 → `/plan-eng-review`로 설계 고정 → `/review`/`/qa`/`/ship`으로 후행 검증.  
이 흐름은 agent가 “무엇부터 해야 할지”를 명확히 만든다. [R8][R13]

### 강점 3. Codex-compatible host 편입이 가능하다
gstack README와 setup 스크립트는 Codex-compatible host용 `.agents/skills` 생성과 `~/.codex/skills/gstack` runtime root 구성을 지원한다. [R8][R11][R15]  
즉, OpenAI식 harness로 재구성할 때 기술적으로 막히지 않는다.

### 강점 4. repo-local vendoring 전략이 현실적이다
README는 `.claude/skills/gstack` 또는 `.agents/skills/gstack` 식의 **repo-local 설치**를 명시한다. [R8]  
이 방식은 OpenAI가 강조하는 “repo 안의 지식/규칙이 시스템의 실제 소스 오브 트루스”라는 방향과 잘 맞는다. [R1][R2]

### 강점 5. 문서 갱신과 회고를 workflow 안에 넣었다
많은 agent workflow가 구현 후 문서와 피드백 루프를 잃어버리는데, gstack는 `/document-release`, `/retro`를 아예 skill로 둔다. [R8][R13]  
이 점은 harness engineering과 궁합이 좋다.

---

## 2.6. 한계와 리스크

### 한계 1. gstack만으로는 “full harness engineering”이 아니다
OpenAI식 harness engineering은
- short `AGENTS.md`
- structured `docs/`
- `PLANS.md`
- custom lint / structural test
- quality/reliability/security 문서
- background cleanup loop
까지 포함한다. [R1][R2][R7]

gstack는 이 전체를 대신하지 않는다.  
특히 **당신의 비즈니스 레포 자체를 어떻게 구조화할지**는 여전히 사용자가 설계해야 한다.

### 한계 2. 도메인 지식은 기본 제공되지 않는다
gstack는 generic software workflow에는 강하지만,
- Oracle/Tibero 차이
- 인사 도메인 규칙
- 급여/근태/평가/권한 승계
- 사내 배치 스케줄
같은 지식은 제공하지 않는다.

이 부분을 repo 문서, custom skill, scripts, eval로 올리지 않으면, agent는 여전히 모른다.  
OpenAI 표현을 빌리면 “in-context에서 접근 불가능한 지식은 존재하지 않는 것과 같다.” [R1]

### 한계 3. deterministic mechanics를 직접 스크립트화해야 한다
OpenAI는 반복되는 shell recipe는 `scripts/`로 빼라고 권장한다.  
모델은 해석과 비교, 판단을 맡고, 스크립트는 고정 순서 작업을 맡는 구조가 가장 안정적이라고 한다. [R6]

gstack에도 이 철학은 부분적으로 보이지만,  
당신의 레거시 시스템 빌드/배포/DB compile/배치 검증은 별도 스크립트가 필요하다.

### 한계 4. 운영/배포 책임은 별도 설계가 필요하다
`/ship`, `/land-and-deploy`, `/canary`는 매력적이지만,
- 배포 경로가 표준화되어 있고
- staging/prod health check가 있고
- rollback이 정의되어 있고
- 변경 영향이 테스트 가능한 경우
에만 제대로 의미가 있다. [R8]

레거시 인사시스템처럼 수동 배포와 DB script 순서 의존성이 크면, 초기에 바로 이 단계로 가면 안 된다.

---

## 2.7. 소스 감사에서 발견한 주의점: 문서 드리프트가 일부 보인다

gstack는 “SKILL.md 자동 생성으로 드리프트를 줄인다”고 설명하지만, 레포 전체를 보면 **상위 문서 간 불일치가 일부 존재한다.** [R9]

### 사례 1. `/debug` vs `/investigate`
- `AGENTS.md`에는 디버깅 skill이 `/debug`로 표기되어 있다. [R12]
- README와 `docs/skills.md`는 해당 skill을 `/investigate`로 표기한다. [R8][R13]

이건 치명적 결함은 아니지만, **팀 표준으로 쓰려면 repo-local로 버전을 핀하고 실제 설치 후 skill 목록을 검증**하는 편이 낫다는 신호다.

### 사례 2. Linux cookie import 지원 설명 불일치
- `ARCHITECTURE.md`는 Linux/Windows cookie decryption이 미구현이라고 적는다. [R9]
- `BROWSER.md`의 source map은 `cookie-import-browser.ts`가 macOS와 Linux 프로필을 지원하는 듯 서술한다. [R10]
- 그런데 최근 이슈 #265는 Linux에서 `cookie-import-browser` 실패를 보고하며, macOS-only path detection을 지적한다. [R14]

즉, **Linux/WSL 환경에서 authenticated QA를 cookie import에 기대는 것은 현재 불확실**하다.  
실무 적용 시 반드시 사전 검증해야 한다.

### 이 불일치가 의미하는 것
- gstack는 매우 빠르게 진화하는 프로젝트다.
- 따라서 “문서에 있으니 된다”보다 **실제 설치 검증 + repo-local pinning + smoke test**가 중요하다.
- 이 점은 오히려 harness engineering 관점에서 더 중요한 교훈이다.  
  에이전트가 믿고 따를 문서는 **당신의 repo에서 검증된 버전**이어야 한다. [R1][R2]

---

## 2.8. 종합 평가

아래 평점은 사실 서술이 아니라, 위 분석을 바탕으로 한 **내 판단**이다.

| 항목 | 평가 | 이유 |
|---|---:|---|
| 브라우저 runtime | 5/5 | 지속형 브라우저, ref system, 로그/스크린샷/QA 루프가 매우 실용적 |
| workflow skill 품질 | 4.5/5 | lifecycle이 잘 분해돼 있고 실무 흐름이 살아 있다 |
| OpenAI식 harness 적합성 | 4/5 | skill/runtime 계층으로는 매우 적합하나, 상위 제어계층은 별도 필요 |
| 레거시 HR 직접 적용성 | 3/5 | read-only 분석, QA, review에는 좋지만 DB/배포 자동화는 보수적으로 접근해야 함 |
| greenfield 적합성 | 4.5/5 | 신규 repo를 harness-first로 설계하면 가치가 크다 |
| 문서/운영 안정성 | 3.5/5 | 자동 생성/테스트가 있으나 일부 문서 드리프트가 보여 pinning이 권장됨 |

---

## 3. OpenAI식 harness engineering과의 비교

## 3.1. OpenAI가 말하는 harness engineering의 핵심

OpenAI의 2026년 글들을 종합하면, harness engineering은 대체로 다음 요소들의 결합이다.

1. **환경(runtime)**
   - 에이전트가 일할 툴, 샌드박스, persistent runtime, 컴퓨터 환경 [R1][R4]

2. **문서/지식**
   - 큰 설명서 하나가 아니라, 짧은 `AGENTS.md`와 구조화된 `docs/`를 system of record로 둔다. [R1][R2]

3. **규칙/제약**
   - custom lint, structural test, file/layout 규칙, taste invariant, permissions [R1]

4. **계획**
   - 긴 작업은 `PLANS.md`/ExecPlan 같은 living document로 만든다. [R7]

5. **반복 workflow의 skill화**
   - 반복적이고 재사용 가능한 일을 skill로 패키징하고, description으로 routing을 제어한다. [R3][R6]

6. **테스트/평가**
   - skill eval, build checks, captured run/trace 기반 scoring [R5]

7. **피드백 루프**
   - 리뷰 피드백, cleanup task, quality score update, CI로 반복 강화 [R1][R6]

즉 harness engineering은 “프롬프트 잘 쓰기”보다 훨씬 넓다.  
**에이전트가 잘 일하도록 repo 자체를 설계하는 일**에 가깝다. [R1]

---

## 3.2. 비교 표

| 차원 | OpenAI식 harness engineering | gstack 현재 상태 | 판단 |
|---|---|---|---|
| 환경/runtime | persistent runtime, tool orchestration, agent loop, 컴퓨터 환경 [R1][R4] | browse daemon은 매우 강함. 하지만 전체 sandbox/container/orchestration은 아님. [R9][R10] | **부분 충족(강함)** |
| 문서/지식 | 짧은 AGENTS + 구조화된 docs가 source of truth [R1][R2] | gstack 자체는 문서가 풍부하지만, **사용자 repo의 지식 저장소를 자동으로 만들어주진 않음** | **부분 충족** |
| 규칙/제약 | custom lint, structural test, taste invariant, permissions [R1] | `careful/freeze/guard`는 있으나 repo-specific 구조 규칙은 별도 구현 필요 | **부분 충족(약함)** |
| 계획/장기작업 | `PLANS.md`/ExecPlan living document [R7] | gstack에 plan review skill은 있으나, repo-level living plan 체계는 별도 설계해야 함 | **부분 충족** |
| 반복 workflow | skills + scripts + metadata routing [R3][R6] | gstack의 가장 강한 지점. 역할형 skill과 workflow가 잘 구성됨. [R8][R13] | **강하게 충족** |
| 테스트/eval | skill eval, captured run, deterministic + rubric 평가 [R5] | gstack 자체 eval은 있으나, 사용자 업무용 eval은 없음 | **부분 충족** |
| 피드백 루프 | quality grade, recurring cleanup task, CI automation [R1][R6] | `/retro`, telemetry/local analytics는 있으나 repo-specific cleanup/quality loop는 직접 구축 필요 | **부분 충족** |

### 비교 결론
**gstack는 OpenAI식 harness engineering의 “skill/runtime/QA workflow 층”으로는 매우 좋다.**  
하지만 `docs`, `AGENTS.md`, `PLANS.md`, custom lint, domain eval, CI/cleanup loop까지 포함한 **전체 harness를 제공하는 것은 아니다.**

---

## 3.3. “gstack를 harness engineering 안에 추가할 수 있는가?”에 대한 판단

### 판단: 가능하다. 다만 ‘넣는 위치’가 중요하다.
gstack를 OpenAI식 harness engineering 안에 넣는 가장 좋은 위치는:

- **`AGENTS.md`가 지시하는 공식 workflow skill 세트**
- **repo-local shared skill bundle**
- **브라우저 QA/runtime tool**
- **review/release/documentation helper skill 묶음**

이다. [R2][R3][R6][R8]

반대로, gstack를 “전체 harness 솔루션”으로 오해하면 실패한다.

---

## 3.4. 권장 통합 구조

```text
repo-root/
├─ AGENTS.md
├─ PLANS.md
├─ docs/
│  ├─ architecture/
│  ├─ domain/
│  ├─ db/
│  ├─ operations/
│  ├─ incidents/
│  ├─ generated/
│  └─ quality/
├─ scripts/
│  ├─ build.sh
│  ├─ test.sh
│  ├─ db-verify.sh
│  ├─ run-smoke.sh
│  └─ collect-logs.sh
├─ .agents/
│  └─ skills/
│     ├─ gstack/
│     ├─ hr-impact-analysis/
│     ├─ oracle-tibero-review/
│     ├─ payroll-regression/
│     └─ release-readiness/
└─ .github/workflows/
   ├─ verify.yml
   ├─ skill-evals.yml
   └─ smoke.yml
```

### 각 요소의 역할
- `AGENTS.md`: repo-wide rules, build/test/deploy rules, 언제 어떤 skill을 써야 하는지 명시 [R2][R7]
- `PLANS.md`: 복잡한 기능/대규모 리팩터링의 living specification [R7]
- `docs/`: agent가 봐야 하는 “실제 지식” 저장소 [R1]
- `scripts/`: agent가 매번 재발명하면 안 되는 deterministic mechanics [R6]
- `.agents/skills/gstack`: 공통 workflow/runtime
- custom skills: HR/DB/보안/배포 도메인 workflow
- CI: stable local workflow를 자동화 [R6]

---

## 3.5. repo-local 설치 vs user-global 설치

gstack README는 Codex-compatible host 기준으로
- repo-local `.agents/skills/gstack`
- user-global `~/.codex/skills/gstack`
둘 다 지원한다. [R8][R11]

### 내 권장
- **팀 표준 / 레거시 업무 시스템**: repo-local 설치를 권장
- **개인 실험 / 개인 생산성**: user-global 가능

### 이유
OpenAI식 harness engineering은 repo를 system of record로 본다. [R1][R2]  
팀이 함께 유지하는 시스템에서는, skill 버전도 repo와 같이 묶여 있어야 한다.  
특히 gstack처럼 빠르게 진화하는 프로젝트는 상위 문서 드리프트 가능성이 있으므로, **검증된 버전을 레포 안에 고정**하는 것이 낫다.

---

## 4. 기존 인사시스템(레거시: JSP, Java, Oracle, Tibero/PL-SQL) 유지보수에 어떻게 적용할까

## 4.1. 레거시 HR 시스템의 현실

이 유형의 시스템은 보통 다음 특징을 가진다.

- JSP/Servlet 또는 Spring MVC 기반의 server-rendered UI
- Service/DAO/SQL Mapper/Stored Procedure로 이어지는 긴 호출 사슬
- 업무 규칙이 Java와 PL/SQL/Tibero package에 분산
- 급여, 근태, 인사평가, 권한, 개인정보 같은 고위험 도메인
- 테스트가 약하거나, 있어도 UI/배치/DB까지 연결되지 않음
- 운영 배포가 사람 절차에 의존하거나, DB script 순서 의존성이 큼

이런 시스템에 agent를 넣을 때 핵심 위험은 두 가지다.

1. **문맥 부족**
   - 화면 하나 바꿨는데 배치나 권한이나 산식에 파급되는 구조를 agent가 모른다.

2. **검증 부족**
   - “코드는 바뀌었는데 실제 업무 결과가 맞는지”를 자동으로 확인하는 장치가 없다.

OpenAI식 harness engineering 관점으로 보면, 이런 시스템일수록 먼저 필요한 것은 **agent에게 맡길 프롬프트**가 아니라, **문서/규칙/스크립트/검증 체계**다. [R1][R6][R7]

---

## 4.2. 적용 원칙

### 원칙 1. 처음에는 “읽기/분석/검토”부터 시작한다
초기 단계에서는 gstack를 다음 용도로 쓰는 것이 가장 안전하다.

- 장애 원인 추적: `/investigate`
- 변경 영향도 정리: `/plan-eng-review`
- PR 검토: `/review`
- staging UI 점검: `/qa`, `/qa-only`
- 릴리즈 문서 정리: `/document-release`
- 주간 회고/핫스팟 파악: `/retro` [R8][R13]

### 원칙 2. prod 쓰기 권한은 처음부터 주지 않는다
특히 다음 영역은 human gate가 필요하다.

- 급여/세액/근태 산식
- 평가 보정 로직
- 개인정보 마스킹/암호화/권한
- DB schema/package 변경
- 대량 배치/정산
- 대외 인터페이스 포맷 [R6]

### 원칙 3. `/guard` + `/freeze`를 기본으로 한다
레거시 시스템은 “고쳐서는 안 되는 주변부”가 많다.  
`/freeze`로 모듈 경계를 묶고, `/careful`/`/guard`로 파괴 명령을 경계하는 편이 좋다. [R8][R13]

### 원칙 4. deterministic 작업은 반드시 script로 뺀다
예를 들면:
- Java build
- unit/integration test
- SQL compile
- DB object invalid 체크
- 특정 배치 재현
- 결과 비교
는 agent가 매번 명령을 추측하게 하면 안 된다. [R6]

---

## 4.3. 레거시 적용은 4단계로 가는 것이 좋다

## 단계 0. 하네스 기반 만들기 (가장 중요)

### 목표
agent가 최소한 “이 시스템이 어떻게 생겼는지”와 “무엇을 하면 안 되는지”를 알게 만드는 단계.

### 해야 할 일
1. `AGENTS.md` 작성
2. `PLANS.md` 작성
3. `docs/` 구조화
4. `scripts/` 정리
5. repo-local gstack 설치 [R2][R7][R8]

### 권장 문서 구조
```text
docs/
├─ architecture/
│  ├─ system-overview.md
│  ├─ request-flow.md
│  └─ deployment-flow.md
├─ domain/
│  ├─ employee-master.md
│  ├─ org-management.md
│  ├─ attendance.md
│  ├─ payroll.md
│  ├─ evaluation.md
│  └─ approval.md
├─ db/
│  ├─ schema-map.md
│  ├─ package-index.md
│  ├─ oracle-tibero-diff.md
│  ├─ table-ownership.md
│  └─ generated/
├─ operations/
│  ├─ batch-schedule.md
│  ├─ rollback-playbook.md
│  ├─ log-locations.md
│  └─ production-checks.md
├─ incidents/
│  └─ known-failure-patterns.md
└─ tests/
   ├─ smoke-scenarios.md
   └─ golden-datasets.md
```

### 왜 이렇게까지 해야 하나
OpenAI는 `AGENTS.md`를 “큰 설명서”가 아니라 **짧은 맵**으로 쓰고, 실제 지식은 repo-local 문서에 둔다고 설명한다. [R1][R2]  
레거시 시스템일수록 이 접근이 맞다.  
사람 머릿속에만 있는 규칙은 agent 입장에서 존재하지 않기 때문이다. [R1]

---

## 단계 1. Read-only 분석/검토 자동화

이 단계에서 바로 효과가 나는 skill은 다음이다.

### `/investigate`
장애나 이상동작이 생겼을 때
- 어디서부터 데이터가 꼬였는지
- 화면 → controller → service → DAO → package → table 경로가 무엇인지
를 추적하는 용도로 적합하다. [R8][R13]

### `/plan-eng-review`
변경 요청이 들어왔을 때
- 영향 범위
- edge case
- 실패 모드
- 데이터 흐름
을 정리하는 데 적합하다. [R8][R13]

### `/review`
PR 단위로
- 빠뜨린 null/transaction/race/error path
- 불완전한 구현
- test gap
을 찾는 데 적합하다. [R8][R13]

### `/document-release`
레거시 시스템은 구현보다 문서 누락이 더 큰 리스크인 경우가 많다.  
변경 직후 화면/배치/운영문서를 같이 갱신하는 workflow가 유용하다. [R8]

---

## 단계 2. 작은 변경에 대한 bounded write 허용

이 단계부터 agent가 코드를 만지게 할 수 있다.  
단, 다음 조건을 만족하는 경우에 한한다.

- 변경 모듈 범위가 명확하다
- `/freeze <module>`로 편집 경계 설정
- 관련 build/test/db-verify script가 있다
- human reviewer가 최종 승인한다 [R6][R8]

### 예시로 적합한 작업
- 특정 JSP 화면의 입력 검증 개선
- service layer null/예외 처리 보강
- 조회 쿼리 성능 개선
- 로그 메시지 구조화
- 기존 배치의 재시도/오류 메시지 명확화
- 운영용 문서 정리

### 아직 부적합한 작업
- 대규모 schema migration
- 급여 계산식 전체 재구성
- 권한체계 재설계
- 다수 모듈을 가로지르는 배치 재배선
- 인터페이스 전문 변경

이건 OpenAI도 유사하게 설명한다.  
정형적인 correctness review나 반복 검증은 agent에 많이 맡길 수 있지만,  
API/아키텍처/이행전략/제품행동 변화처럼 “여러 합리적 선택지 중 무엇을 택할지”가 핵심인 문제는 여전히 사람 판단이 중요하다. [R6]

---

## 단계 3. UI 회귀 점검 자동화

레거시 HR 시스템에서 gstack의 browse/qa 계층은 특히 여기서 빛난다.

### 활용 포인트
- 로그인 후 메뉴 이동
- 직원등록/수정
- 조직변경
- 휴가신청/승인
- 근태조회
- 급여 preview 화면
- 평가입력/확정
- 배치결과 조회
- 첨부/다운로드 흐름 [R10]

### 권장 방식
- production이 아닌 dev/staging만 대상으로 함
- 테스트 계정과 마스킹 데이터 사용
- cookie import는 OS별 선검증 후 사용
- 불확실하면 `handoff/resume`로 사람 개입 [R10][R14]

### 왜 이게 중요한가
레거시 시스템의 많은 문제는 “코드는 컴파일되지만 화면/업무흐름이 실제로 안 된다”이다.  
브라우저 확인이 development loop 안으로 들어오면, 유지보수 품질이 눈에 띄게 좋아진다.

---

## 단계 4. 릴리즈/배포 workflow로 확장

여기까지 왔을 때만 `/ship` 계열을 고려하는 것이 좋다.

### `/ship`을 허용하기 위한 최소 조건
- 빌드/테스트 명령이 script화되어 있음
- DB 검증 명령이 고정되어 있음
- 결과 로그 수집이 가능함
- smoke scenario가 있음
- rollback 문서가 있음
- reviewer가 release gate를 승인함 [R6][R8]

### `/land-and-deploy`는 언제?
다음이 갖춰질 때까지는 권장하지 않는다.

- 배포 자동화가 이미 안정적
- canary/health check가 있음
- 운영 확인 포인트가 scriptable
- DB script 순서/복구 절차가 정형화됨
- 승인 프로세스가 정의됨

레거시 HR 시스템에서는 보통 이 단계에 도달하기까지 시간이 필요하다.

---

## 4.4. 레거시 인사시스템용으로 추가해야 하는 custom skill

OpenAI는 skills를 repo의 normal working setup 일부로 두고, `description`으로 라우팅 계약을 명확히 하라고 권장한다. [R3][R6]  
따라서 gstack만 넣지 말고, 아래 같은 **업무 특화 skill**을 같이 두는 것이 좋다.

### 1. `hr-impact-analysis`
**목적:** 화면/요구사항/버그를 입력받아 JSP → Controller → Service → DAO → Package → Table 영향도를 문서화  
**왜 필요한가:** 레거시의 가장 큰 문제는 영향 범위 가시성 부족

### 2. `oracle-tibero-review`
**목적:** SQL/PL-SQL/Tibero dialect 차이, optimizer hint, package compile 위험, invalid object 가능성 점검  
**왜 필요한가:** Oracle을 아는 agent가 Tibero를 자동으로 제대로 다룬다고 가정하면 위험

### 3. `payroll-regression-check`
**목적:** 급여/수당/공제 계산 결과를 golden dataset과 비교  
**왜 필요한가:** 코드 correctness보다 business correctness가 중요

### 4. `pii-security-review`
**목적:** 주민등록번호, 계좌, 급여, 인사평가 데이터의 마스킹/로그/권한/다운로드 경로 점검  
**왜 필요한가:** `/cso`는 generic security audit이고, HR는 개인정보 특화 룰이 더 필요

### 5. `legacy-release-readiness`
**목적:** DB script 순서, compile 로그, invalid object, smoke scenario, rollback link를 모아 release gate 판단  
**왜 필요한가:** `/ship`을 레거시 현실에 맞게 보완해야 함

### 6. `batch-reconcile`
**목적:** 배치 전/후 건수, 합계, 에러 건, 샘플 row를 비교하고 이상 여부를 요약  
**왜 필요한가:** 배치형 HR 시스템에서는 UI보다 배치 결과가 더 중요할 수 있음

---

## 4.5. 레거시 시스템용 `AGENTS.md` 예시 골격

아래는 개념 예시다. 실제 repo에 맞게 수정해야 한다.

```md
# HR Legacy Repo Guidance

## Mandatory workflow
- Use `hr-impact-analysis` before any change that touches JSP, Service, DAO, SQL mapper, or DB package.
- Use `/investigate` for bug fixing before proposing code changes.
- Use `/review` before any PR is considered complete.
- Use `legacy-release-readiness` before release tagging.

## ExecPlans
When writing complex features or refactors, create an ExecPlan in `plans/` following `PLANS.md`.

## Build and verification
- Build: `./scripts/build.sh`
- Unit tests: `./scripts/test-unit.sh`
- Integration tests: `./scripts/test-integration.sh`
- DB verify: `./scripts/db-verify.sh`
- UI smoke: `./scripts/ui-smoke.sh`

## High-risk domains
Human approval is required for:
- payroll logic
- attendance accrual rules
- PII masking/encryption
- authority inheritance
- DB schema/package changes
- external interface format changes

## Data safety
- Never run write commands against production DB.
- Use masked datasets only.
- Do not export PII into logs or markdown docs.

## Repo navigation
- Screen specs: `docs/domain/`
- DB/package map: `docs/db/`
- Incidents and failure patterns: `docs/incidents/`
- Operations and rollback: `docs/operations/`
```

이런 문서는 짧아야 한다.  
OpenAI도 `AGENTS.md`는 작게 유지하고, 반복 피드백만 codify하라고 권장한다. [R2]

---

## 4.6. 레거시 적용 시 “하지 말아야 할 것”

1. **gstack를 깔자마자 prod 배포 자동화부터 시작하지 말 것**
2. **DB와 업무 규칙을 문서화하지 않은 채 agent에게 유지보수를 맡기지 말 것**
3. **Oracle/Tibero 차이를 generic SQL reasoning에 맡기지 말 것**
4. **repo-local pinning 없이 개인 global install만 팀 표준처럼 쓰지 말 것**
5. **skill 없이 긴 자연어 prompt만 누적하지 말 것**
6. **테스트/스모크/골든데이터 없이 급여/근태/평가 로직 변경을 agent-driven으로 처리하지 말 것**

---

## 5. 신규 개발에서는 어떻게 활용할까

## 5.1. 신규 개발에는 훨씬 더 잘 맞는다

신규 개발에서는 레거시의 가장 큰 문제였던
- 숨은 의존성
- 불명확한 운영 규칙
- 테스트 부재
- 문서 부재
를 초기에 제거할 수 있다.

따라서 베스트 프랙티스는 처음부터 **harness-first repo**로 시작하는 것이다.  
OpenAI가 실제로 한 것처럼 repo-local 문서/규칙/skills/evals를 먼저 잡는 방식이 장기적으로 훨씬 강하다. [R1][R6][R7]

---

## 5.2. 신규 개발 추천 구조

```text
repo-root/
├─ AGENTS.md
├─ PLANS.md
├─ docs/
│  ├─ design-docs/
│  ├─ exec-plans/
│  ├─ generated/
│  ├─ product-specs/
│  ├─ references/
│  ├─ QUALITY_SCORE.md
│  ├─ RELIABILITY.md
│  └─ SECURITY.md
├─ scripts/
│  ├─ verify.sh
│  ├─ smoke.sh
│  ├─ start-dev.sh
│  ├─ stop-dev.sh
│  └─ collect-logs.sh
├─ .agents/skills/
│  ├─ gstack/
│  ├─ code-change-verification/
│  ├─ pr-draft-summary/
│  ├─ release-readiness/
│  └─ product-domain-skill/
└─ .github/workflows/
   ├─ verify.yml
   ├─ review.yml
   └─ smoke.yml
```

이 구조는 OpenAI 문서의 패턴과 gstack의 강점을 자연스럽게 결합한다. [R1][R6][R7][R8]

---

## 5.3. 신규 개발 추천 workflow

### 1) 문제 정의
- `/office-hours`
- 필요하면 `/plan-ceo-review`

gstack의 강점은 사용자가 말한 feature를 그냥 구현하지 않고, 문제를 다시 정의하려는 데 있다. [R8][R13]  
신규 제품에서는 이 장점이 크게 작동한다.

### 2) 기술 설계 고정
- `/plan-eng-review`
- 복잡하면 `PLANS.md` 기반 ExecPlan 생성 [R7][R8]

OpenAI는 큰 작업을 living plan으로 관리하라고 권장한다.  
신규 개발에서는 이 습관을 초기에 잡는 편이 좋다.

### 3) 디자인 기준 고정
- `/plan-design-review`
- 필요하면 `/design-consultation`

특히 UI-heavy 신규 서비스라면 이 흐름이 유용하다. [R8][R13]

### 4) 구현
- agent가 구현
- deterministic mechanics는 `scripts/`가 수행 [R6]

### 5) 검토
- `/review`
- 중요하면 `/codex`를 second opinion으로 추가 [R8]

### 6) 검증
- `/qa`
- `benchmark`, `canary`는 성숙도에 따라 도입 [R8]

### 7) PR/배포/문서
- `/ship`
- `/document-release`
- CI에서 동일 verify workflow 실행 [R6][R8]

### 8) 피드백 루프
- `/retro`
- quality/reliability/security 문서 갱신
- 반복되는 리뷰 코멘트는 `AGENTS.md` 또는 skill로 승격 [R1][R2][R6]

---

## 5.4. 신규 개발에서 정말 중요한 설계 포인트

### 포인트 1. `AGENTS.md`는 작고 강하게
OpenAI는 monolithic `AGENTS.md`가 금방 썩는다고 분명히 말한다.  
`AGENTS.md`는 table of contents 겸 routing map이어야 한다. [R1][R2]

### 포인트 2. PLANS를 living document로 운영
OpenAI의 ExecPlan 가이드는
- self-contained
- living document
- milestone
- progress
- decision log
- outcomes & retrospective
를 강조한다. [R7]

신규 개발에서는 이 문화를 초기에 심어두면, agent가 긴 작업을 안정적으로 이어가기 쉬워진다.

### 포인트 3. 반복되는 shell recipe는 script로 빼기
OpenAI는 “모델이 매번 같은 shell recipe를 재발명한다면 script가 되어야 한다”고 설명한다. [R6]  
예:
- verify stack
- dev server start/stop
- log collection
- smoke test
- seed data setup
- migration validation

### 포인트 4. skill description을 routing contract로 다루기
OpenAI 문서는 `name`과 `description`이 discovery/routing의 핵심이라고 강조한다. [R3][R6]  
신규 개발에서 custom skill을 만들 때는 “무엇을 하는가”보다 **언제 써야 하는가**를 description에 명확히 써야 한다.

### 포인트 5. local에서 안정화된 workflow만 CI로 올리기
OpenAI는 skill이 local에서 충분히 안정화된 뒤 CI에 올리라고 한다. [R6]  
즉:
- 먼저 사람이 반복해서 로컬에서 써보고
- edge case를 찾고
- script를 정리한 뒤
- CI workflow로 승격해야 한다.

---

## 5.5. 신규 개발에서 gstack를 쓰면 좋은 영역 / 덜 좋은 영역

### 매우 잘 맞는 영역
- UI가 있는 제품
- staging URL이 있는 제품
- PR review와 QA 반복이 많은 팀
- 빠른 프로토타이핑과 반복 출시
- 문서와 release handoff를 자주 잃어버리는 팀 [R8][R10]

### 보통 이상 맞는 영역
- 내부 툴
- B2B SaaS
- 운영용 dashboard
- 관리 콘솔
- 웹 기반 업무 프로세스

### 주의가 필요한 영역
- 강한 실시간성/하드웨어/드라이버 연동
- 복잡한 멀티시스템 트랜잭션
- 규제/보안이 매우 강한 시스템
- 사람이 승인해야 하는 정책결정이 많은 영역

이 경우에도 gstack를 못 쓴다는 뜻은 아니다.  
다만 **review/QA/documentation helper**로 먼저 쓰고, autonomy는 늦게 올리는 게 좋다.

---

## 6. 내가 추천하는 도입안

## 6.1. 레거시 HR 시스템용 권장안

### 추천 모델: “보수적 도입”
가장 현실적인 시나리오는 다음이다.

#### 1단계: 2~4주
- repo-local gstack 설치
- `AGENTS.md`, `PLANS.md`, `docs/`, `scripts/` 뼈대 생성
- `/investigate`, `/plan-eng-review`, `/review`만 먼저 사용

#### 2단계: 다음 2~4주
- staging UI에 `/qa` 도입
- `oracle-tibero-review`, `hr-impact-analysis` custom skill 추가
- smoke scenario 문서화

#### 3단계: 그 다음
- 골든 데이터 기반 `payroll-regression-check`
- `legacy-release-readiness`
- `/document-release`와 CI verify 연계

#### 4단계: 충분히 안정화된 후
- `/ship` 일부 허용
- 배포 자동화/운영 확인 절차가 정리되면 `/land-and-deploy` 검토

### 왜 이 경로가 좋은가
레거시 시스템의 가장 큰 병목은 “코드 작성”이 아니라
- 영향도 파악
- 운영 리스크
- 문서 부재
- 회귀 검증 부족
이기 때문이다.

gstack는 이 병목들을 줄이는 데 먼저 쓰는 것이 가장 ROI가 높다.

---

## 6.2. 신규 개발용 권장안

### 추천 모델: “harness-first + gstack as workflow layer”
신규 repo를 만들 때 처음부터 아래를 체크인하는 방식을 권장한다.

- `AGENTS.md`
- `PLANS.md`
- `docs/`
- `scripts/verify.sh`, `scripts/smoke.sh`
- `.agents/skills/gstack`
- repo-specific custom skills
- skill eval/CI workflow [R1][R5][R6][R7][R8]

### 이렇게 하면 얻는 것
- agent가 매번 초기 문맥을 다시 배우지 않는다
- 검증 방식이 repo 안에 남는다
- PR handoff와 release review가 반복 가능해진다
- 문서/테스트/피드백이 구현과 분리되지 않는다
- 팀이 늘어나도 workflow가 깨지지 않는다

---

## 6.3. 내 최종 권고

### 레거시 HR 유지보수
**도입 추천.**  
단, **“구현 자동화”가 아니라 “분석/검토/QA/문서화 자동화”부터** 시작해야 한다.

### 신규 개발
**강하게 추천.**  
단, gstack만 넣지 말고 **OpenAI식 harness engineering 요소**를 같이 설계해야 한다.

즉, 최종 권고는 다음 문장으로 요약된다.

> **gstack는 당신의 harness engineering을 대체하는 제품이 아니라,  
> 당신의 harness engineering 안에서 가장 빨리 실전 가치가 나는 workflow/runtime 계층이다.**

---

## 7. 바로 실행할 체크리스트

### 레거시 HR 시스템
- [ ] gstack를 repo-local로 설치한다.
- [ ] `AGENTS.md`를 1페이지 이내로 만든다.
- [ ] `docs/db/oracle-tibero-diff.md`를 만든다.
- [ ] `docs/domain/payroll.md`, `attendance.md`, `approval.md`를 만든다.
- [ ] `scripts/build.sh`, `test.sh`, `db-verify.sh`, `ui-smoke.sh`를 만든다.
- [ ] `/investigate`, `/review`, `/plan-eng-review`를 공식 workflow로 지정한다.
- [ ] payroll/PII/schema 변경은 human gate로 못 박는다.
- [ ] `hr-impact-analysis`, `oracle-tibero-review`, `payroll-regression-check` skill을 추가한다.

### 신규 개발
- [ ] repo 생성 시점에 `AGENTS.md`, `PLANS.md`, `docs/`, `scripts/`를 같이 체크인한다.
- [ ] `.agents/skills/gstack`를 표준 skill 세트로 넣는다.
- [ ] verify/smoke/release-readiness를 script + skill로 나눈다.
- [ ] `/office-hours` → `/plan-eng-review` → ExecPlan → `/review` → `/qa` → `/ship` 흐름을 팀 표준으로 만든다.
- [ ] eval과 CI를 함께 설계한다.

---
