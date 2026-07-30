---
layout: post
title: "Matt Pocock Skills 심층 분석: AI에게 개발을 맡기지 않고, 엔지니어링 규율을 조합하는 법"
date: 2026-07-30 13:00:00 +0900
categories: [ai]
tags: [ai, agent-skills, matt-pocock, codex, claude-code, skills-sh, tdd, domain-modeling, spec-driven-development, engineering-workflow]
permalink: /ai/2026/07/30/matt-pocock-skills-real-engineers-analysis.html
---

> **분석 대상**: [mattpocock/skills](https://github.com/mattpocock/skills)  
> **기준 커밋**: [`2ab9580`](https://github.com/mattpocock/skills/tree/2ab958093e83e0ec752e6c1c5932da465bf23e0c)  
> **조사 기준일**: 2026-07-30  
> **라이선스**: MIT  
> **핵심 질문**: 이 저장소는 어떤 실패를 해결하려고 만들어졌고, 언제 써야 하며, 개발자들은 무엇에 반응하고 있는가?

---

## 0. 결론부터: 이 저장소는 AI 개발 프레임워크가 아니라 "엔지니어링 규율의 표준 라이브러리"다

`mattpocock/skills`를 단순한 프롬프트 모음으로 보면 핵심을 놓친다.

이 저장소의 진짜 제품은 코드 생성기가 아니다. 요구사항 정렬, 도메인 언어, 테스트 주도 개발, 버그 진단, 아키텍처 개선, 코드 리뷰, 이슈 분해처럼 **소프트웨어 엔지니어가 원래 지켜야 했던 규율을 에이전트가 반복 실행할 수 있는 작은 절차로 패키징한 것**이다. [R1][R3]

핵심 주장은 세 문장으로 압축할 수 있다.

1. AI가 틀리는 가장 큰 원인은 모델이 약해서가 아니라 **사람과 에이전트가 서로 다른 문제를 풀고 있기 때문**이다.
2. 이를 해결하려고 거대한 개발 프로세스를 통째로 설치하면 일관성은 얻지만 **사용자의 통제권과 디버깅 가능성**을 잃기 쉽다.
3. 따라서 필요한 순간에 필요한 규율만 호출할 수 있도록 **작고, 읽을 수 있고, 수정 가능한 skill**로 쪼개야 한다.

이 관점에서 `skills`는 GSD, BMAD, Spec Kit와 정면으로 같은 제품을 만들려는 프로젝트가 아니다. 오히려 "프로세스 전체를 소유하는 프레임워크"와 "개발자가 조립하는 규율 라이브러리" 사이의 경계를 선명하게 그으려는 시도에 가깝다. [R1][R13][R14][R15]

### 한 줄 평가

> **AI에게 개발을 맡기는 패키지가 아니라, 개발자가 통제권을 유지한 채 AI에게 엔지니어링 습관을 이식하는 패키지다.**

---

## 1. 왜 이런 저장소가 필요해졌나

AI 코딩 도구의 첫 번째 경쟁은 "누가 코드를 더 많이 생성하는가"였다. 하지만 실제 프로젝트에서는 생성량이 늘수록 다른 병목이 더 크게 드러난다.

- 요구사항을 잘못 이해해 며칠치 코드를 엉뚱한 방향으로 작성한다.
- 프로젝트 용어를 모르기 때문에 같은 개념을 파일마다 다른 이름으로 부른다.
- 테스트를 작성하지만 구현 세부사항만 검증해 리팩터링 때 모두 깨진다.
- 버그를 재현하기 전에 코드를 훑고 첫 번째 가설에 바로 수정부터 한다.
- 기능은 동작하지만 구조가 얕은 모듈과 중복 추상화로 가득해진다.
- "완료"라는 에이전트의 자기평가를 검증 없이 받아들인다.

Matt Pocock은 README에서 이 문제를 네 가지 실패 모드로 정리한다. [R1]

| 실패 모드 | 표면 증상 | 저장소가 제시하는 해법 |
|---|---|---|
| 에이전트가 원하는 것을 만들지 않음 | 요구사항 미정렬, 뒤늦은 재작업 | `grill-me`, `grill-with-docs` |
| 에이전트가 지나치게 장황함 | 용어 불일치, 긴 설명, 탐색 비용 | 공유 언어 `CONTEXT.md`, 도메인 모델링 |
| 코드가 실제로 동작하지 않음 | 추측 구현, 약한 테스트, 디버깅 실패 | `tdd`, `diagnosing-bugs` |
| 코드베이스가 진흙덩어리가 됨 | 얕은 모듈, 높은 결합, 변경 비용 증가 | `codebase-design`, `improve-codebase-architecture` |

중요한 점은 네 문제를 "더 좋은 모델로 교체하면 해결된다"고 보지 않는다는 것이다.

모델이 아무리 좋아져도 요구사항이 모호하면 더 빠르게 잘못 구현한다. 생성 속도가 빨라질수록 잘못된 아키텍처도 더 빠르게 복제된다. 결국 AI 시대에는 소프트웨어 공학의 기본기가 덜 중요해지는 것이 아니라, **기본기를 매번 재현하는 실행 장치가 더 중요해진다.**

---

## 2. 이 저장소가 해결하려는 핵심 문제: 통제권과 재사용성의 동시 확보

GSD, BMAD, Spec Kit 같은 접근법은 아이디어에서 구현까지 일관된 경로를 제공한다. 이들은 잘 정의된 시작점과 다음 단계를 알려준다는 장점이 있다.

반면 Matt Pocock의 문제 제기는 이렇다.

> 전체 프로세스를 프레임워크가 소유하면, 프로세스 내부에서 버그가 생겼을 때 사용자가 고치기 어렵고 자신의 방식으로 일부만 바꾸기도 어렵다. [R1]

이 비판은 "프레임워크는 나쁘다"는 뜻이 아니다. 제어의 단위를 어디에 둘 것인지에 대한 선택이다.

```text
전체 프로세스형
아이디어 → 정해진 분석 → 정해진 명세 → 정해진 계획 → 정해진 구현
          프레임워크가 흐름과 상태를 소유

조합형 skill
현재 문제 → 필요한 규율 A → 필요한 규율 B → 사용자가 다음 단계 결정
           각 skill은 작고 독립적이며 수정 가능
```

전체 프로세스형은 팀에 공통 절차가 없거나 AI 개발을 처음 도입할 때 강하다. 반대로 이미 자체 이슈 트래커, ADR 규칙, CI, 리뷰 문화가 있는 팀에는 기존 체계와 충돌할 수 있다.

`mattpocock/skills`는 후자를 겨냥한다. "우리 프로세스를 버리고 이 방식으로 갈아타라"가 아니라, **지금 사용하는 프로세스의 약한 고리에 필요한 규율을 꽂아 넣으라**는 제안이다.

---

## 3. 내부 구조: 실행 코드는 작고, 설계는 Markdown에 들어 있다

기준 커밋을 직접 확인하면 저장소의 실체는 의외로 단순하다.

- 활성 배포 대상: Claude Code 플러그인 manifest 기준 **22개 skill**
- 저장소 전체: engineering, productivity, misc, personal, in-progress, deprecated를 포함해 **41개 `SKILL.md`**
- `skills.sh` 페이지: 과거·비활성 항목까지 포함한 **49개 항목**
- 런타임의 중심: 복잡한 애플리케이션 코드가 아니라 `SKILL.md`, 참조 문서, 작은 설정 파일
- 패키지 스크립트: changeset/version 관리 중심이며, 별도의 대규모 런타임이나 서버가 없음 [R2][R11][R17][R18]

숫자가 서로 다른 이유는 "49개가 모두 현재 안정판"이기 때문이 아니다.

Claude Code 플러그인은 `engineering`과 `productivity`의 선별된 22개만 노출한다. 반면 저장소에는 실험 중인 skill, 개인용 skill, 폐기된 skill도 함께 존재한다. `skills.sh` 통계에는 현재 트리에 없는 과거 항목까지 남아 있다. 따라서 설치 수를 해석할 때는 **현재 안정판의 개수와 레지스트리의 누적 항목 수를 분리**해야 한다. [R2][R11]

### 왜 Markdown 중심 구조가 중요한가

이 구조는 세 가지 효과를 만든다.

1. **읽을 수 있다**  
   에이전트가 어떤 절차를 따를지 사람이 직접 검토할 수 있다.

2. **수정할 수 있다**  
   `skills.sh` 방식으로 설치하면 프로젝트 안의 일반 파일이 되므로 팀 사정에 맞게 바꿀 수 있다.

3. **모델과 도구를 바꾸기 쉽다**  
   특정 모델 API를 직접 호출하는 코드보다 자연어 절차와 파일 규약에 중심을 두기 때문에 Claude Code, Codex 등 여러 에이전트에 이식하기 쉽다.

다만 "모델 독립적"이라는 표현을 "모든 모델에서 동일하게 동작한다"로 오해하면 안 된다. skill은 실행 바이너리가 아니라 **행동 지침**이다. 지침 준수 능력, 도구 접근, sub-agent 지원, 컨텍스트 크기가 다른 환경에서는 결과도 달라진다.

---

## 4. 가장 중요한 설계: user-invoked와 model-invoked의 분리

이 저장소는 skill을 기능 영역보다 먼저 **누가 호출할 수 있는가**로 나눈다. [R3]

### User-invoked skill

사람이 직접 이름을 입력해야 실행된다.

- `grill-me`
- `grill-with-docs`
- `to-spec`
- `to-tickets`
- `implement`
- `triage`
- `improve-codebase-architecture`
- `wayfinder`
- `handoff`
- `teach`

이들은 대화를 길게 끌거나, 파일을 만들거나, 이슈를 게시하거나, 구현·커밋까지 수행할 수 있는 **오케스트레이션 명령**이다. 모델이 임의로 시작하면 사용자의 흐름을 빼앗을 수 있으므로 암시적 호출을 차단한다.

### Model-invoked skill

사람이 직접 호출할 수도 있고, 현재 작업과 맞으면 모델이 자동으로 선택할 수도 있다.

- `grilling`
- `domain-modeling`
- `tdd`
- `diagnosing-bugs`
- `prototype`
- `research`
- `codebase-design`
- `code-review`
- `resolving-merge-conflicts`

이들은 여러 상위 흐름에서 재사용되는 **작업 규율**이다.

### 호출 그래프가 통제권을 지키는 방식

```text
사람
 └─ user-invoked skill
      ├─ model-invoked discipline A
      └─ model-invoked discipline B

금지:
model → user-invoked skill 자동 시작
user-invoked skill A → user-invoked skill B 연쇄 실행
```

예를 들어 `grill-me`의 본문은 놀랄 만큼 짧다.

```text
Run a /grilling session.
```

`grill-with-docs`도 `grilling`과 `domain-modeling`을 조합하는 얇은 오케스트레이터다. 실제 재사용 가능한 규율은 model-invoked skill에 두고, 사용자가 보는 명령은 얇게 유지한다. [R3][R5]

이 구조는 함수 설계와 닮았다.

- user-invoked skill: 애플리케이션 유스케이스
- model-invoked skill: 재사용 가능한 도메인 로직
- `SKILL.md` description: 라우팅 조건
- 프로젝트 문서: 실행 시 주입되는 상태와 정책

즉, 프롬프트를 길게 복사하는 모음이 아니라 **호출 경계와 의존 방향을 가진 작은 행동 모듈 시스템**이다.

---

## 5. 핵심 skill 1: `grill-me` — 사람도 모르는 요구사항을 드러내는 인터뷰

`grill-me`와 `grilling`은 이 저장소에서 가장 많이 설치된 기능이다. `skills.sh` 기준 `grill-me`는 69.96만, `grill-with-docs`는 59.29만 설치로 표시된다. [R2]

왜 코드 작성 skill이 아니라 질문 skill이 1위일까?

AI 개발의 가장 비싼 실패는 문법 오류가 아니다. **정확하게 구현된 잘못된 기능**이다.

`grilling`은 다음 규칙을 강제한다. [R5]

- 의사결정 트리의 가지를 하나씩 따라간다.
- 한 번에 질문 하나만 한다.
- 각 질문에는 에이전트의 추천 답도 함께 제시한다.
- 파일이나 환경에서 찾을 수 있는 사실은 사용자에게 묻지 않고 직접 조사한다.
- 사실은 에이전트가 찾되, 결정은 사용자에게 돌려준다.
- 공동 이해에 도달했다는 사용자의 확인 전에는 구현하지 않는다.

이 방식은 흔한 "추가 정보가 필요합니다"와 다르다.

좋은 그릴링은 질문 수를 늘리는 것이 아니라 **결정의 의존성을 정렬**한다.

예를 들어 권한 기능을 만든다면 UI 색상부터 묻는 것이 아니라 다음 순서로 간다.

```text
권한의 주체는 사용자·역할·조직 중 무엇인가?
  └─ 상속이 있는가?
       └─ 충돌 시 deny와 allow 중 무엇이 우선인가?
            └─ 변경 이력은 감사 대상인가?
                 └─ 그 결정이 API와 UI에 어떤 상태를 만드는가?
```

앞 질문의 답이 뒤 질문의 선택지를 바꾸기 때문에 한 번에 열 개를 묻지 않는다.

### 언제 특히 효과적인가

- 사용자도 아직 요구사항을 정확히 설명하지 못하는 신규 기능
- 정책 예외가 많은 인사·급여·권한·결재 도메인
- "대충 이런 느낌"에서 실제 제품 결정을 뽑아내야 하는 기획
- 팀원마다 같은 단어를 다른 뜻으로 쓰는 프로젝트
- 구현보다 잘못된 결정의 비용이 큰 변경

### 언제 과한가

- 오탈자 수정
- 이미 재현 테스트와 기대 결과가 명확한 버그
- 기계적 라이브러리 버전 변경
- 결정이 아니라 실행만 남은 작은 작업

모든 변경에 그릴링을 적용하면 토큰과 의사결정 피로가 늘어난다. 이 skill의 가치는 "항상 질문하라"가 아니라 **모호성이 비싼 작업을 식별해 그때 깊게 질문하라**는 데 있다.

---

## 6. 핵심 skill 2: `grill-with-docs` — 대화를 프로젝트의 공유 언어로 압축한다

그릴링만 하면 좋은 대화는 남지만, 다음 세션의 에이전트는 그 대화를 모른다. `grill-with-docs`는 여기에 `domain-modeling`을 결합한다.

주요 산출물은 두 가지다.

1. `CONTEXT.md`의 공유 언어
2. 필요할 때만 작성하는 ADR(Architecture Decision Record)

### 공유 언어가 왜 토큰 최적화인가

도메인 용어가 없으면 매번 긴 설명이 필요하다.

```text
용어 없음:
"강좌 섹션 안의 수업이 파일 시스템에서 실제 파일 위치를 갖게 될 때
관련 상위 항목들도 함께 실제 상태로 바뀌는 과정"

공유 언어 있음:
"materialization cascade"
```

한 번 합의한 용어는 변수명, 함수명, 파일명, 이슈 제목, 테스트 이름에 반복 사용된다. 에이전트가 코드를 탐색할 때도 같은 개념을 검색하기 쉬워진다. [R1][R4]

이것은 단순히 답변을 짧게 만드는 기법이 아니다.

```text
도메인 개념
  → 합의된 용어
      → 코드 식별자
          → 테스트 이름
              → 이슈·ADR
                  → 다음 세션의 탐색 키워드
```

같은 언어가 저장소 전체를 관통하면 에이전트의 탐색 공간이 줄어든다.

### ADR을 남발하지 않는 점도 중요하다

`domain-modeling`은 모든 대화를 문서로 만들지 않는다. 미래의 작업자가 같은 결정을 다시 뒤집을 가능성이 있고, 그 이유가 코드만으로 자명하지 않을 때 ADR을 제안한다.

문서가 많아질수록 컨텍스트가 좋아지는 것은 아니다. 낡은 문서는 강한 잘못된 신호다. 이 저장소의 좋은 부분은 문서화를 강조하면서도 **"필요한 결정만 기록한다"는 절제**를 함께 둔 점이다.

---

## 7. 핵심 skill 3: `tdd` — 테스트 개수보다 테스트가 놓이는 seam을 먼저 합의한다

`tdd`는 흔한 "테스트 먼저 작성" 프롬프트보다 훨씬 구체적이다. 핵심은 Red-Green 자체보다 **어디를 테스트할지 먼저 합의하는 것**이다. [R6]

여기서 seam은 내부 구현을 들여다보지 않고 행동을 관찰할 수 있는 공개 경계다.

```text
나쁜 테스트:
private 함수 호출
내부 collaborator mock 검증
DB를 직접 조회해 UI 동작을 우회 검증

좋은 테스트:
공개 API 요청 → 응답·상태 변화 관찰
사용자 동작 → 화면에 보이는 결과 관찰
CLI 입력 → stdout·exit code 관찰
```

skill은 테스트를 작성하기 전에 seam 목록을 사용자와 합의하도록 요구한다. 이유는 단순하다. 테스트를 많이 만드는 것은 쉽지만, 잘못된 경계에 만든 테스트는 리팩터링을 막는 부채가 된다.

### 세 가지 안티패턴

`tdd`는 특히 다음을 금지한다.

1. **구현 결합 테스트**  
   동작은 그대로인데 내부 구조를 바꾸면 깨지는 테스트

2. **동어반복 테스트**  
   구현과 같은 계산으로 기대값을 만들어 항상 맞을 수밖에 없는 테스트

3. **수평 슬라이싱**  
   모든 테스트를 먼저 상상해서 만든 뒤 모든 구현을 한꺼번에 작성하는 방식

대신 하나의 행동을 끝까지 관통하는 tracer bullet을 반복한다.

```text
행동 하나 선택
  → 그 행동의 실패 테스트
      → 통과할 최소 구현
          → 다음 행동으로 이동
```

AI는 미리 많은 코드를 생성하는 데 능하다. 바로 그 능력 때문에 "미래에 필요할 것 같은 추상화"와 "아직 검증되지 않은 테스트"도 대량 생성한다. 이 skill은 생성량을 늘리는 대신 **한 번에 허용되는 추측의 크기**를 줄인다.

---

## 8. 핵심 skill 4: `diagnosing-bugs` — 가설보다 먼저 빨간 피드백 루프를 만든다

AI 에이전트의 전형적인 디버깅 실패는 다음과 같다.

```text
에러 메시지 확인
  → 관련 있어 보이는 파일 검색
      → 첫 번째 그럴듯한 원인 선택
          → 여러 파일 수정
              → "수정했습니다"
```

`diagnosing-bugs`는 이 순서를 뒤집는다. [R7]

```text
피드백 루프 구축
  → 재현 및 최소화
      → 3~5개 반증 가능한 가설
          → 한 번에 변수 하나만 계측
              → 회귀 테스트
                  → 수정·정리·사후 분석
```

가장 강한 문장은 이것이다.

> **빨간 상태를 만들 수 있는 한 개의 실행 명령이 없으면 다음 단계로 가지 않는다.**

실패 신호는 다음 조건을 충족해야 한다.

- 사용자가 보고한 바로 그 증상을 잡는다.
- 같은 입력에 같은 판정을 내린다.
- 몇 분이 아니라 몇 초 안에 반복할 수 있다.
- 사람이 계속 클릭하지 않아도 에이전트가 실행할 수 있다.

재현 수단도 테스트 하나로 제한하지 않는다.

- 실패 테스트
- `curl` 또는 HTTP 스크립트
- CLI fixture와 stdout diff
- Playwright/Puppeteer 브라우저 스크립트
- 실제 trace 재생
- 최소 시스템 harness
- property/fuzz loop
- `git bisect run`
- 구버전과 신버전의 differential test

이 skill의 본질은 버그 지식이 아니라 **추측을 실험으로 바꾸는 순서**다.

### 특히 잘 맞는 문제

- 특정 데이터에서만 발생하는 장애
- 간헐적 race condition
- 성능 회귀
- 여러 서비스 사이에서 발생하는 통합 버그
- "수정했다는데 다시 발생하는" 장기 미해결 문제

### 주의할 점

재현 환경에 접근할 수 없거나 운영 데이터가 있어야만 발생하는 문제라면 skill만으로 해결되지 않는다. 이 경우 올바른 행동은 추측 수정을 강행하는 것이 아니라 HAR, 로그, core dump, 화면 녹화, 임시 운영 계측 같은 **관측 수단을 요청하는 것**이다.

---

## 9. 핵심 skill 5: `improve-codebase-architecture` — AI가 만든 엔트로피를 AI로 정리하되, 선택은 사람이 한다

AI는 기존 패턴을 매우 빠르게 복제한다. 좋은 패턴도 복제하지만, 얕은 wrapper, 중복된 mapper, 의미 없는 service 계층도 같은 속도로 늘린다.

`improve-codebase-architecture`는 코드베이스를 훑어 "deep module"로 바꿀 후보를 찾는다. [R9]

deep module은 작은 인터페이스 뒤에 많은 복잡성을 감춘다.

```text
얕은 모듈:
인터페이스 복잡도 ≈ 내부 구현 복잡도
사용자가 내부 사정을 대부분 알아야 함

깊은 모듈:
작은 인터페이스 << 내부가 처리하는 복잡도
호출자는 안정적인 seam만 이해하면 됨
```

이 skill은 무작정 전체 저장소를 리팩터링하지 않는다.

1. 최근 커밋에서 자주 바뀐 hot spot을 먼저 찾는다.
2. 이해하려면 여러 작은 파일을 계속 오가야 하는 영역을 찾는다.
3. 현재 추상화를 삭제했을 때 복잡성이 흩어지는지, 오히려 한곳에 모이는지 deletion test를 적용한다.
4. 후보별 Before/After 시각 자료를 HTML 보고서로 만든다.
5. 사용자가 하나를 선택하면 그때 그릴링으로 인터페이스와 경계를 결정한다.

핵심은 **발견은 에이전트가 하고, 투자 결정은 사람이 한다**는 점이다.

모든 구조적 불편을 고칠 필요는 없다. 최근에도 바뀌지 않고 앞으로도 바뀔 가능성이 낮은 영역을 아름답게 만드는 것은 YAGNI 위반일 수 있다. 그래서 최근 변경 hot spot에 우선순위를 두는 설계가 현실적이다.

---

## 10. 핵심 skill 6: `code-review` — 코드 품질과 요구사항 충족을 분리해 검사한다

코드 리뷰가 실패하는 흔한 이유는 "좋아 보이는 코드"와 "요구한 기능"을 한 번에 판단하기 때문이다.

`code-review`는 diff를 두 개의 독립 축으로 나눈다. [R8]

| 축 | 질문 | 근거 |
|---|---|---|
| Standards | 저장소의 규칙과 코드 품질 기준을 지켰는가? | 코딩 표준, 프로젝트 문서, Fowler smell baseline |
| Spec | 원래 이슈·PRD·명세를 정확히 구현했는가? | 이슈, PRD, 사용자 요구 |

두 리뷰는 서로의 판단에 오염되지 않도록 별도 sub-agent에서 병렬 실행한다.

이 분리는 중요한 실패를 드러낸다.

- 코드가 아름답지만 잘못된 기능을 만들 수 있다.
- 요구사항은 맞지만 저장소의 구조와 규칙을 망가뜨릴 수 있다.

마지막에도 두 점수를 하나로 합치지 않는다. Standards 8점, Spec 8점을 평균 내 8점이라고 하면 "요구사항 누락" 같은 치명적 문제를 코드 스타일 점수가 상쇄할 수 있기 때문이다.

### 실무적 가치

maker와 checker를 분리하는 것만큼이나, **checker 내부의 평가 기준도 분리**한다는 점이 좋다.

다만 이 skill은 sub-agent와 이슈 트래커 접근을 전제로 한다. 병렬 에이전트가 없거나 명세가 저장소 밖에만 있는 환경에서는 같은 품질로 실행되지 않는다.

---

## 11. 전체 개발 흐름은 어떻게 조합되는가

이 저장소는 하나의 강제 파이프라인을 제공하지 않지만, `ask-matt`가 권장하는 기본 흐름은 존재한다.

```text
아이디어·모호성
  → grill-with-docs
      → 공유 언어 + ADR
          → to-spec
              → to-tickets
                  → implement
                      ├─ tdd
                      ├─ diagnosing-bugs
                      └─ code-review
```

### 단계별 책임

| 단계 | 산출물 | 실패를 막는 장치 |
|---|---|---|
| `grill-with-docs` | 합의된 결정, 용어, 필요 시 ADR | 요구사항 미정렬 |
| `to-spec` | 문제·해법·사용자 스토리·구현/테스트 결정 | 대화 맥락 손실 |
| `to-tickets` | end-to-end vertical slice와 blocking edge | 너무 큰 작업, 잘못된 병렬화 |
| `implement` | 테스트를 통과한 코드와 커밋 | 실행 누락 |
| `code-review` | Standards/Spec 독립 검토 | 자기검증 편향 |

`to-tickets`는 작업을 frontend/backend/database 같은 수평 계층으로 나누지 않는다. 스키마부터 UI까지 좁은 사용자 행동 하나를 끝까지 완성하는 vertical slice로 만든다. 각 slice는 새 컨텍스트 창 하나에 들어갈 크기여야 하고, 다른 ticket과의 blocking edge를 명시한다. [R10]

이 방식은 여러 에이전트를 무조건 동시에 실행하는 것보다 현실적이다.

```text
Ticket 01: 최소 데이터 모델 + 조회 API + 빈 화면 표시
    ├─ Ticket 02: 생성 동작 end-to-end
    └─ Ticket 03: 수정 동작 end-to-end
          └─ Ticket 04: 권한 예외 end-to-end
```

병렬화 가능한 frontier만 동시에 작업하고, 나머지는 선행 결정이 끝난 뒤 시작한다.

---

## 12. `wayfinder`: 한 세션에 담기지 않는 큰 작업을 위한 지도

큰 마이그레이션은 처음부터 정확한 구현 ticket으로 쪼갤 수 없다. 아직 모르는 것이 무엇인지도 모르는 "fog of war" 상태이기 때문이다.

`wayfinder`는 이때 구현 계획 대신 **결정 지도**를 만든다.

- 목적지: 최종적으로 어떤 상태가 되어야 하는가
- 결정된 것: 이미 합의한 사실
- 미정인 것: 아직 답이 없는 질문
- decision ticket: 구현이 아니라 조사와 결정을 위한 이슈
- blocking edge: 어떤 결정을 먼저 내려야 다음 질문을 풀 수 있는가

예를 들어 Oracle 기반 인사시스템을 PostgreSQL로 옮기는 작업이라면 곧바로 테이블별 마이그레이션 ticket 100개를 만들지 않는다.

```text
Map: HR 데이터 계층 PostgreSQL 전환
  ├─ Decision: PL/SQL 업무 규칙 중 DB에 남길 것은 무엇인가?
  ├─ Decision: 이력성 테이블의 시간 모델을 어떻게 보존하는가?
  ├─ Decision: 무중단 전환에 CDC가 필요한가?
  └─ Decision: Oracle 전용 타입을 어떤 경계에서 변환하는가?
```

각 조사 결과가 다음 지도의 정확도를 높인다. 이는 계획을 한 번에 완성하려는 접근보다 **불확실성을 일급 작업으로 취급**한다는 점에서 좋다.

---

## 13. 설치 방식 두 가지는 철학도 다르다

README는 두 설치 방식을 단순한 편의 차이가 아니라 서로 다른 소유 모델로 설명한다. [R1][R11]

### Claude Code 플러그인

```bash
claude plugins install mattpocock-skills
```

- 선별된 활성 skill 전체를 관리형 read-only bundle로 설치
- 제작자가 업데이트하면 구독자에게 업데이트가 전달됨
- 로컬에서 직접 뜯어고치는 용도는 아님
- "fork"보다 "subscribe"에 가까움

### Codex 및 기타 에이전트: `skills.sh`

```bash
npx skills@latest add mattpocock/skills
```

- 필요한 skill과 설치 대상을 선택
- 프로젝트 안에 일반 파일로 복사
- 팀 사정에 맞게 직접 수정 가능
- 업데이트 시점도 사용자가 통제
- "subscribe"보다 "fork and own"에 가까움

### 둘을 동시에 설치하면 안 되는 이유

README는 두 방식을 함께 쓰면 모든 skill이 중복된다고 경고한다. 같은 이름과 비슷한 description의 skill이 두 벌 있으면 모델 라우팅이 모호해지고 업데이트 버전도 갈릴 수 있다.

### Codex 네이티브 플러그인이 아직 없는 이유

저장소 ADR에 따르면 Claude Code manifest는 여러 skill 경로를 배열로 선택할 수 있지만, 조사 기준 Codex plugin manifest는 단일 경로만 받는다. 저장소의 `skills/` 아래에는 안정판뿐 아니라 deprecated, in-progress, personal 항목도 있어 전체 폴더를 노출할 수 없다. symlink 기반 선별 디렉터리도 설치 캐시 복사 과정에서 유지되지 않았다. [R11]

따라서 현재는:

- Claude Code: native plugin
- Codex 및 기타: `skills.sh`
- Codex native plugin: 저장소 구조 또는 manifest 기능이 바뀔 때 재검토

이 결정은 "모든 도구를 지원한다"는 마케팅보다 **배포 경계가 실제로 어떻게 다른지 기록한 좋은 ADR 사례**다.

---

## 14. 언제 쓰면 가장 좋은가

### 14.1 요구사항이 모호하지만 구현 비용이 큰 기능

추천 조합:

```text
grill-with-docs → prototype(필요 시) → to-spec → to-tickets
```

예:

- 조직·직책·겸직이 얽힌 인사 권한
- 결재선 자동 구성
- 평가 등급 조정 정책
- 가격·할인·환불 규칙
- 여러 상태를 갖는 B2B workflow

질문을 건너뛰었을 때 재작업 비용이 큰 도메인일수록 효과가 커진다.

### 14.2 오래된 코드베이스의 고질적인 버그

추천 조합:

```text
diagnosing-bugs → tdd → code-review
```

예:

- 특정 고객 데이터에서만 발생하는 오류
- 간헐적인 batch 누락
- 트랜잭션 경계 문제
- N+1 또는 lock contention 성능 회귀
- 브라우저 세션과 서버 상태가 함께 얽힌 버그

핵심은 수정 전에 자동 재현 루프를 확보하는 것이다.

### 14.3 에이전트가 빠르게 만든 코드가 점점 변경하기 어려워질 때

추천 조합:

```text
improve-codebase-architecture → codebase-design → grilling → ADR
```

예:

- 같은 개념이 여러 service와 util에 흩어짐
- wrapper가 많지만 실제 복잡성을 감추지 못함
- 테스트를 위해 내부 함수를 계속 export함
- 기능 하나를 바꾸려면 파일 수십 개를 수정함

### 14.4 여러 세션과 여러 에이전트에 걸친 대규모 작업

추천 조합:

```text
wayfinder → decision tickets → to-spec → to-tickets → handoff
```

예:

- 데이터베이스 전환
- 모놀리스 분리
- 인증 체계 교체
- 디자인 시스템 재구축
- 장기 성능 개선 프로그램

### 14.5 이미 자체 프로세스가 있는 숙련된 팀

이 저장소의 가장 좋은 고객은 의외로 AI 개발 초보가 아니라 **자신의 개발 방식을 이미 설명할 수 있는 팀**일 수 있다.

기존 CI, 이슈 트래커, ADR, 리뷰 규칙을 버리지 않고 약한 부분만 skill로 보강할 수 있기 때문이다.

---

## 15. 언제 쓰지 않는 편이 좋은가

### 15.1 5분짜리 기계적 변경

문구 수정, 단순 rename, 명확한 설정값 변경까지 그릴링과 spec을 거치면 절차가 작업보다 커진다.

### 15.2 빠른 탐색 자체가 목적인 throwaway 실험

정답이 있는 기능 구현이 아니라 "이 아이디어가 가능한가?"를 확인하는 단계라면 전체 흐름보다 `prototype` 하나가 낫다.

### 15.3 팀의 용어와 테스트 경계가 아직 전혀 합의되지 않은 상태에서 전면 자동화

skill은 합의를 대신 만들 수 있지만, 조직의 결정권까지 대신 가질 수는 없다. 이해관계자가 다른 말을 하는데 에이전트만 workflow를 실행하면 문서화된 혼란을 만들 뿐이다.

### 15.4 운영 변경을 무승인으로 실행하는 자율 루프

`implement`는 현재 브랜치에 커밋까지 수행하도록 지시한다. issue publishing, 파일 작성, 커밋 등은 단순한 조언이 아니라 실제 side effect다. 운영 DB 변경, 배포, 권한 변경처럼 비가역성이 큰 단계는 별도 사람 승인을 유지해야 한다. [R10]

### 15.5 결정적 재현성이 필요한 규제·감사 환경의 단독 통제 수단

자연어 skill은 정책을 설명하지만 반드시 강제하지는 않는다. 보안 규칙과 감사 요구는 다음처럼 기계적 통제와 함께 써야 한다.

- CI policy
- branch protection
- 정적 분석
- schema validation
- 권한 분리
- 승인 workflow
- 감사 로그

skill은 guardrail을 설명하는 층이지, 권한 시스템 자체가 아니다.

---

## 16. GSD·BMAD·Spec Kit과 무엇이 다른가

먼저 공정하게 구분해야 한다. 아래 비교는 Matt Pocock의 README가 제시한 문제의식을 기준으로 하되, 각 프로젝트의 공식 설명도 함께 반영한 것이다. "어느 것이 무조건 우월한가"가 아니라 **어떤 제어 단위가 필요한가**의 차이다. [R1][R13][R14][R15]

| 관점 | Matt Pocock Skills | GSD | BMAD | GitHub Spec Kit |
|---|---|---|---|---|
| 기본 단위 | 작은 독립 skill | context/spec-driven 시스템 | 역할·workflow 중심 방법론 | spec-driven 전체 흐름 |
| 핵심 약속 | 통제 가능한 조합 | 경량 계획·실행·검증 | 규모 적응형 Agile AI 개발 | 명세를 실행 가능한 중심 산출물로 |
| 사용 흐름 | 필요한 skill만 선택 | 정해진 상태와 단계 활용 | 12+ 전문 역할, 34+ workflow | constitution → specify → plan → tasks → implement |
| 커스터마이징 | 파일을 직접 수정하기 쉬움 | 시스템 규약 안에서 확장 | module·workflow 단위 확장 | extension·preset·bundle |
| 절차의 무게 | 낮음~중간, 선택에 따라 변화 | 중간 | 중간~높음 | 중간~높음 |
| 강점 | 기존 팀 프로세스에 부분 도입 | 컨텍스트와 실행 흐름의 일관성 | 넓은 lifecycle과 전문 역할 | 조직적 명세 중심 개발 |
| 주요 위험 | 조합을 사용자가 직접 설계해야 함 | 상태·절차가 기존 방식과 충돌 가능 | 역할과 산출물이 과해질 수 있음 | 작은 변경에도 명세 절차가 무거울 수 있음 |
| 가장 맞는 상황 | 숙련자가 통제권을 유지하고 싶을 때 | 일관된 agent workflow가 필요할 때 | 분석부터 배포까지 넓은 안내가 필요할 때 | 명세를 조직의 중심 자산으로 삼을 때 |

### GSD와의 차이

GSD는 스스로를 meta-prompting, context engineering, spec-driven development 시스템으로 설명한다. 즉, 작업 상태와 개발 흐름을 하나의 운영 방식으로 묶는 쪽에 가깝다. [R13]

`mattpocock/skills`는 그 정도의 전체 상태 머신을 기본값으로 강제하지 않는다. 대신 `grilling`, `tdd`, `diagnosing-bugs` 같은 규율을 꺼내 기존 workflow에 삽입한다.

### BMAD와의 차이

BMAD는 PM, Architect, Developer, UX 등 12개 이상의 전문 역할과 34개 이상의 workflow, 규모 적응형 계획을 제공한다. 복잡한 프로젝트에서 "다음에 무엇을 해야 하는지" 알려주는 폭넓은 체계가 강점이다. [R14]

Matt의 접근은 역할극보다 **행동 규율**에 초점을 둔다. "Architect 에이전트가 누구인가"보다 "아키텍처 후보를 어떤 vocabulary와 판단 순서로 검토하는가"가 중요하다.

### Spec Kit과의 차이

Spec Kit은 constitution, specify, plan, tasks, implement로 이어지는 명세 중심 개발을 제공하며 30개 이상의 AI coding agent integration을 지원한다. 명세를 코드 앞의 일회성 문서가 아니라 구현을 생성하는 중심 아티팩트로 올린다. [R15]

`mattpocock/skills`에도 `to-spec`과 `to-tickets`가 있지만, 반드시 모든 변경이 이 경로를 지나야 한다고 요구하지 않는다. 버그라면 곧바로 `diagnosing-bugs`를, 아키텍처 문제라면 `improve-codebase-architecture`를 선택할 수 있다.

### 선택 기준

```text
"우리 팀에 AI 개발 절차가 전혀 없다"
  → GSD, BMAD, Spec Kit 같은 전체 흐름이 빠른 출발점

"이미 절차는 있고, 특정 단계가 약하다"
  → Matt Pocock Skills의 부분 도입이 유리

"작업마다 절차의 무게를 다르게 하고 싶다"
  → 조합형 skill이 유리

"모든 팀이 같은 산출물과 단계를 따라야 한다"
  → 전체 프로세스형이 유리
```

---

## 17. 사용자들은 무엇에 열광하고 있는가

2026-07-30 조회 기준 GitHub 공개 지표는 다음과 같다. [R2][R12]

- Stars: **194,856**
- Forks: **16,786**
- Watchers/Subscribers: **1,129**
- 공개 후 약 6개월
- `skills.sh` 표시 누적 설치: **12.1M**

이 블로그의 [2026-07-26 자동 분석 글](/github-repo-analysis/2026/07/26/repo-deep-dive-mattpocock-skills.html)에는 당시 star가 188,187로 기록돼 있다. 나흘 뒤 194,856이므로 **4일 동안 6,669개, 하루 평균 약 1,667개** 증가했다.

단, `skills.sh`의 설치 수는 고유 사용자 수가 아니다. 재설치, 업데이트, 자동화 호출, 과거 skill을 포함할 수 있다. 12.1M명을 의미한다고 읽어서는 안 된다. 그럼에도 skill별 상대 순위는 어떤 문제가 강하게 반응을 얻는지 보여준다.

### 설치 상위 skill

| 순위 | skill | `skills.sh` 표시 설치 수 | 사용자가 반응한 문제 |
|---:|---|---:|---|
| 1 | `grill-me` | 699.6K | 구현 전 요구사항 정렬 |
| 2 | `grill-with-docs` | 592.9K | 대화를 공유 언어·ADR로 축적 |
| 3 | `improve-codebase-architecture` | 572.7K | AI가 만든 구조적 엔트로피 |
| 4 | `tdd` | 551.3K | 동작하지 않는 코드와 약한 테스트 |
| 5 | `setup-matt-pocock-skills` | 501.8K | 실제 프로젝트에 연결하는 초기 설정 |
| 6 | `handoff` | 469.3K | 세션 간 컨텍스트 손실 |
| 7 | `triage` | 468.9K | 이슈를 agent-ready 상태로 정리 |
| 8 | `prototype` | 452.3K | 큰 구현 전 설계 질문 검증 |

가장 흥미로운 사실은 `implement`가 1위가 아니라는 점이다.

사람들이 가장 많이 가져간 것은 "코드를 더 빨리 써라"가 아니라:

- 먼저 나에게 질문하라.
- 우리가 쓰는 언어를 기억하라.
- 망가진 구조를 찾아라.
- 테스트로 피드백을 만들어라.
- 다음 세션에 제대로 넘겨라.

즉, 열광의 중심은 생성 능력이 아니라 **통제, 정렬, 지속성, 품질 회복**이다.

### 왜 이렇게 빠르게 퍼졌을까

#### 1. 문제의 이름을 정확히 붙였다

"AI가 멍청하다"가 아니라 misalignment, feedback loop, shared language, ball of mud라는 소프트웨어 공학의 언어로 실패를 설명한다.

#### 2. 도입 비용이 낮다

서버, 데이터베이스, 별도 SaaS가 필요 없다. 몇 개의 Markdown 파일을 설치하고 필요한 명령부터 쓸 수 있다.

#### 3. 결과를 읽고 고칠 수 있다

블랙박스 orchestration engine이 아니라 사람이 검토 가능한 파일이다. 마음에 들지 않으면 fork해서 바꿀 수 있다.

#### 4. "AI가 엔지니어링을 대체한다"는 피로감에 반대 서사를 제공한다

저장소의 문구는 의도적으로 "real engineering, not vibe coding"을 전면에 둔다. AI 도구를 쓰면서도 자신의 전문성과 통제권을 잃고 싶지 않은 개발자의 정체성과 맞닿는다.

#### 5. 저자의 신뢰와 배포 채널이 있다

Matt Pocock은 교육 콘텐츠와 약 6만 명 규모라고 밝힌 newsletter audience를 갖고 있다. 좋은 아이디어만큼이나 빠르게 설명하고 배포할 수 있는 채널이 성장에 영향을 준다. [R1]

---

## 18. 이 저장소의 진짜 혁신은 새 이론보다 "좋은 기본기의 패키징"이다

TDD, ubiquitous language, ADR, deep module, tracer bullet, maker/checker는 새로운 개념이 아니다.

저장소 README도 The Pragmatic Programmer, Domain-Driven Design, Extreme Programming, A Philosophy of Software Design 같은 오래된 소프트웨어 공학의 문장을 적극 인용한다. [R1]

그렇다면 왜 지금 새롭게 느껴질까?

사람에게 좋은 원칙을 설명하는 것과 에이전트가 매 작업에서 그 원칙을 실행하도록 만드는 것은 다른 문제이기 때문이다.

```text
책의 원칙:
"작고 의도적인 단계로 진행하라"

실행 가능한 skill:
- 한 번에 seam 하나
- 실패 테스트 하나
- 통과할 최소 구현
- 다음 vertical slice
- full suite는 마지막
```

```text
책의 원칙:
"버그를 재현하라"

실행 가능한 skill:
- red-capable 명령 한 개를 제시
- 실제 한 번 실행한 출력 첨부
- 결정적이고 빠른지 체크
- 없으면 가설 단계 진입 금지
```

새로운 것은 원칙 자체가 아니라 **원칙을 호출 가능하고 조합 가능한 행동 프로토콜로 변환한 방식**이다.

---

## 19. 냉정하게 봐야 할 한계

### 19.1 자연어 지침은 기계적 강제가 아니다

`tdd`에 Red before Green이라고 적혀 있어도 모델이 항상 지킨다는 보장은 없다. branch protection이나 테스트 실패 차단처럼 결정적인 통제와 다르다.

최선의 구성은 다음과 같다.

```text
Skill: 올바른 행동 순서를 안내
Script/Test: 결과를 기계적으로 검증
CI: 통과하지 못한 변경을 차단
Human Review: 정책·위험·제품 판단
```

### 19.2 "어떤 모델에서도 동작"과 "같은 품질"은 다르다

긴 문서 이해, 도구 사용, 질문 품질, sub-agent orchestration 능력이 다른 모델에서는 동일한 skill도 성능 차이가 난다.

특히 `code-review`는 병렬 sub-agent, `improve-codebase-architecture`는 코드 탐색과 HTML 보고서, `triage`는 이슈 트래커 쓰기 권한에 기대므로 host 기능이 약하면 축소 실행된다.

### 19.3 조합의 책임이 사용자에게 있다

작고 독립적인 것은 장점이지만, 어떤 skill을 어떤 순서로 사용할지는 결국 사용자가 설계해야 한다.

- `grill-me`를 언제 생략할지
- spec이 필요한 작업과 바로 진단할 작업을 어떻게 구분할지
- 어떤 단계에서 사람 승인을 받을지
- 팀의 기존 workflow와 어떤 문서가 source of truth인지

이 판단이 어렵다면 전체 프로세스형 도구가 더 편할 수 있다.

### 19.4 문서가 낡으면 오히려 강한 오답을 만든다

`CONTEXT.md`와 ADR이 실제 코드와 어긋나면 에이전트는 낡은 결정을 자신 있게 반복한다. 문서의 존재보다 freshness와 ownership이 중요하다.

### 19.5 공개된 행동 평가 체계가 약하다

기준 커밋의 `package.json`은 changeset과 version 관리 스크립트만 제공한다. skill의 행동 품질을 자동으로 비교하는 eval suite나 회귀 테스트는 뚜렷하게 보이지 않는다. [R17]

Markdown 지침은 작은 문구 변경에도 모델 행동이 크게 달라질 수 있다. 규모가 커질수록 다음이 필요해질 것이다.

- 대표 시나리오 fixture
- 모델별 실행 결과 평가
- skill 변경 전후 비교
- 금지 행동 준수율
- 비용·턴 수·성공률 회귀 측정

### 19.6 유지보수 집중도가 높다

GitHub contributors API 조회 기준 주요 기여는 Matt Pocock 한 사람에게 크게 집중돼 있다. 명확한 철학과 빠른 의사결정에는 유리하지만, 조직 표준으로 채택할 때는 특정 maintainer의 방향 전환과 업데이트 속도를 고려해야 한다. [R16]

### 19.7 관리형 자동 업데이트는 supply-chain 경계다

Claude Code 플러그인은 편리하지만 업데이트된 지침이 에이전트의 파일 쓰기, 이슈 게시, 커밋 행동에 영향을 줄 수 있다.

- 중요한 팀은 버전을 pin한다.
- 변경 로그를 검토한다.
- 쓰기 권한을 최소화한다.
- 자동 배포와 운영 데이터 권한을 skill에 직접 연결하지 않는다.

read-only bundle이라는 말은 "skill 파일을 사용자가 수정하지 못한다"는 뜻이지, **에이전트의 실행이 읽기 전용이라는 뜻은 아니다.**

---

## 20. 실무 도입 전략: 전부 설치하지 말고 실패 모드 하나부터 고쳐라

가장 나쁜 도입은 22개를 모두 설치하고 모든 작업에 전체 흐름을 적용하는 것이다.

### 1단계: 현재 가장 비싼 실패를 고른다

| 현재 증상 | 먼저 도입할 skill |
|---|---|
| 만든 뒤 요구사항이 자주 바뀜 | `grill-with-docs` |
| 같은 용어를 팀마다 다르게 사용 | `domain-modeling` |
| 버그 수정이 재발함 | `diagnosing-bugs` |
| 테스트가 리팩터링을 방해함 | `tdd` |
| AI가 만든 코드가 빠르게 복잡해짐 | `improve-codebase-architecture` |
| 구현은 했지만 요구와 자주 어긋남 | `code-review` |
| 큰 프로젝트가 세션마다 방향을 잃음 | `wayfinder`, `handoff` |

### 2단계: 2주 동안 한 workflow에서만 시험한다

예를 들어 버그 수정에만 적용한다.

```text
버그 이슈
  → diagnosing-bugs로 재현 명령 확보
      → tdd로 회귀 테스트
          → 수정
              → code-review의 Spec 축으로 원 증상 확인
```

### 3단계: 전후 지표를 비교한다

측정 후보:

- 수정 후 30일 이내 재발률
- 첫 수정이 실제 원인을 해결한 비율
- PR당 재작업 횟수
- 요구사항 확인을 위해 오간 메시지 수
- 테스트가 행동이 아닌 구현 변경으로 깨진 비율
- 작업 시작부터 검증 가능한 첫 결과까지의 시간

토큰 수만 보면 그릴링은 비싸 보일 수 있다. 하지만 재작업이 줄면 전체 비용은 낮아질 수 있다. 반대로 재작업이 줄지 않는데 대화만 길어진다면 그 skill은 현재 작업에 과한 것이다.

### 4단계: 팀 방식으로 fork한다

`skills.sh`로 설치한 파일을 그대로 신성시하지 말고 다음을 조정한다.

- 이슈 트래커와 라벨
- ADR 위치와 형식
- 테스트 seam 승인 방식
- 커밋 여부
- sub-agent 허용 범위
- 운영 변경 승인점
- 금지 명령과 보안 규칙

이 저장소의 철학을 가장 충실하게 따르는 방법은 원본을 그대로 지키는 것이 아니라 **자신의 엔지니어링 방식에 맞게 고치는 것**이다.

---

## 21. 프로젝트 유형별 추천 조합

### 신규 SaaS

```text
setup
→ grill-with-docs
→ prototype
→ to-spec
→ to-tickets
→ implement + tdd
→ code-review
```

좋은 이유:

- 제품 결정과 도메인 언어를 초기에 맞출 수 있다.
- vertical slice로 빠르게 사용자 행동을 확인할 수 있다.
- 초기 생성 속도가 아키텍처 엔트로피로 바뀌는 것을 늦춘다.

### 레거시 인사시스템

```text
domain-modeling
→ diagnosing-bugs
→ research
→ to-spec
→ tdd
→ code-review
```

좋은 이유:

- 오래된 업무 용어와 실제 코드 이름의 차이를 먼저 드러낸다.
- JSP, Java, Oracle/Tibero, PL/SQL 사이의 버그를 재현 루프로 좁힌다.
- 기존 행동을 보존할 seam을 먼저 합의한다.

주의:

- 급여, 평가, 개인정보, 생산 DB 변경은 agent-only 승인으로 두면 안 된다.
- 테스트가 없는 레거시에서는 먼저 characterization test 또는 재현 harness를 확보해야 한다.

### 빠르게 성장한 AI 생성 코드베이스

```text
improve-codebase-architecture
→ codebase-design
→ grilling
→ ADR
→ tracer-bullet refactor tickets
```

좋은 이유:

- 모든 곳을 정리하려 하지 않고 자주 바뀌는 hot spot부터 고른다.
- 리팩터링을 미학이 아니라 locality, leverage, test seam으로 평가한다.

### 오픈소스 유지보수

```text
triage
→ diagnosing-bugs
→ to-tickets
→ implement
→ code-review
→ handoff
```

좋은 이유:

- 모호한 이슈를 agent-ready 상태로 바꾼다.
- 외부 PR을 Standards와 Spec으로 나눠 검토할 수 있다.
- maintainer가 세션을 넘겨도 조사 근거를 보존한다.

---

## 22. 이 저장소에서 가져와야 할 가장 중요한 다섯 가지 패턴

### 패턴 1: 사실은 에이전트가 찾고, 결정은 사람에게 묻는다

나쁜 질문:

> 이 프로젝트는 PostgreSQL을 쓰나요?

좋은 행동:

> 설정과 compose 파일을 확인해 PostgreSQL 사용 사실을 찾은 뒤, 스키마 변경 정책처럼 사람의 판단이 필요한 것만 묻는다.

### 패턴 2: 대화를 공유 언어로 압축한다

반복 설명을 프롬프트에 계속 붙이지 말고 `CONTEXT.md`의 용어로 만든다. 용어는 문서, 코드, 테스트, 이슈를 연결하는 검색 키가 된다.

### 패턴 3: 버그 가설 전에 판정기를 만든다

수정 능력보다 중요한 것은 같은 증상을 몇 초마다 재현하고 판정하는 loop다.

### 패턴 4: 리뷰 축을 합치지 않는다

코드 품질과 요구사항 충족을 별도로 평가한다. 하나가 다른 하나의 실패를 상쇄하지 못하게 한다.

### 패턴 5: 큰 작업은 구현 ticket보다 decision ticket으로 시작한다

모르는 것이 많은 상태에서 정교한 구현 계획을 만드는 척하지 않는다. 먼저 불확실성을 줄이는 조사와 결정을 작업으로 인정한다.

---

## 23. 최종 평가

| 평가 축 | 점수 | 판단 |
|---|---:|---|
| 문제 정의 | 9.5/10 | AI 개발의 실제 실패를 소프트웨어 공학 언어로 정확히 짚음 |
| 도입 용이성 | 9/10 | Markdown 중심, 선택 설치, 별도 서버 불필요 |
| 조합 가능성 | 9.5/10 | user/model invocation 분리와 얇은 orchestration이 뛰어남 |
| 기존 프로세스 호환성 | 9/10 | 전체 교체 없이 약한 단계만 보강 가능 |
| 결정적 신뢰성 | 6.5/10 | 자연어 지침이므로 CI·권한·테스트의 기계적 강제가 별도로 필요 |
| 모델 간 일관성 | 7/10 | 이식은 쉽지만 결과 품질은 host와 모델 능력에 영향 |
| 팀 거버넌스 | 7.5/10 | setup·tracker·ADR 구조는 좋지만 권한·eval·버전 고정은 팀이 보완해야 함 |
| 장기 유지보수 | 7.5/10 | 빠른 개선은 강점, 높은 변경 속도와 maintainer 집중은 리스크 |

### 종합 판단

`mattpocock/skills`는 "AI 개발을 자동화하는 완성품"으로 보면 부족하다. 스스로 workflow 엔진, CI, 권한 시스템, 평가 harness를 제공하지 않는다.

하지만 "우리 팀의 엔지니어링 규율을 에이전트가 반복 수행하게 만드는 출발점"으로 보면 매우 강력하다.

특히 다음 조건에서 추천할 가치가 높다.

- AI가 만든 코드의 양보다 재작업과 구조 악화가 더 큰 문제가 됐다.
- 이미 이슈 트래커, CI, 리뷰 문화를 갖고 있다.
- 특정 프레임워크에 전체 프로세스의 통제권을 넘기고 싶지 않다.
- skill 파일을 읽고 자신의 방식으로 수정할 의지가 있다.

---

## 24. 결론: 사람들이 열광하는 것은 더 강한 에이전트가 아니라, 다시 엔지니어가 되는 방법이다

이 저장소의 인기에서 가장 중요한 신호는 star 숫자만이 아니다.

가장 많이 설치된 skill이 구현 자동화가 아니라 `grill-me`, `grill-with-docs`, `improve-codebase-architecture`, `tdd`라는 사실이다. 사람들은 이미 코드가 충분히 빨리 생성된다는 것을 안다. 이제 부족한 것은 속도가 아니라 방향, 구조, 검증, 기억이다.

`mattpocock/skills`가 제안하는 답은 보수적이면서도 급진적이다.

- 요구사항이 모호하면 질문한다.
- 같은 언어를 쓴다.
- 작은 단계로 진행한다.
- 테스트 가능한 경계를 만든다.
- 버그를 먼저 재현한다.
- 설계를 매일 돌본다.
- 만든 사람과 검사하는 사람을 분리한다.
- 최종 결정권은 사람에게 둔다.

모두 오래된 원칙이다. 달라진 것은 이제 그 원칙을 사람만 기억하는 것이 아니라 **에이전트가 호출할 수 있는 실행 단위로 저장한다는 것**이다.

> AI 시대의 경쟁력은 코드를 가장 많이 생성하는 능력이 아니라,  
> **어떤 규율을 언제 호출하고 어디에서 멈출지 설계하는 능력**에 가까워지고 있다.

이 저장소는 그 변화를 가장 이해하기 쉬운 형태로 보여준다.

---

## 참고 자료

- **[R1]** Matt Pocock, [Skills For Real Engineers — README](https://github.com/mattpocock/skills/blob/2ab958093e83e0ec752e6c1c5932da465bf23e0c/README.md)
- **[R2]** skills.sh, [mattpocock/skills 설치 통계](https://skills.sh/mattpocock/skills) — 2026-07-30 조회
- **[R3]** Matt Pocock, [Model-invoked vs user-invoked](https://github.com/mattpocock/skills/blob/2ab958093e83e0ec752e6c1c5932da465bf23e0c/.agents/invocation.md)
- **[R4]** Matt Pocock, [`setup-matt-pocock-skills`](https://github.com/mattpocock/skills/blob/2ab958093e83e0ec752e6c1c5932da465bf23e0c/skills/engineering/setup-matt-pocock-skills/SKILL.md)
- **[R5]** Matt Pocock, [`grilling`](https://github.com/mattpocock/skills/blob/2ab958093e83e0ec752e6c1c5932da465bf23e0c/skills/productivity/grilling/SKILL.md)
- **[R6]** Matt Pocock, [`tdd`](https://github.com/mattpocock/skills/blob/2ab958093e83e0ec752e6c1c5932da465bf23e0c/skills/engineering/tdd/SKILL.md)
- **[R7]** Matt Pocock, [`diagnosing-bugs`](https://github.com/mattpocock/skills/blob/2ab958093e83e0ec752e6c1c5932da465bf23e0c/skills/engineering/diagnosing-bugs/SKILL.md)
- **[R8]** Matt Pocock, [`code-review`](https://github.com/mattpocock/skills/blob/2ab958093e83e0ec752e6c1c5932da465bf23e0c/skills/engineering/code-review/SKILL.md)
- **[R9]** Matt Pocock, [`improve-codebase-architecture`](https://github.com/mattpocock/skills/blob/2ab958093e83e0ec752e6c1c5932da465bf23e0c/skills/engineering/improve-codebase-architecture/SKILL.md)
- **[R10]** Matt Pocock, [`to-spec`](https://github.com/mattpocock/skills/blob/2ab958093e83e0ec752e6c1c5932da465bf23e0c/skills/engineering/to-spec/SKILL.md), [`to-tickets`](https://github.com/mattpocock/skills/blob/2ab958093e83e0ec752e6c1c5932da465bf23e0c/skills/engineering/to-tickets/SKILL.md), [`implement`](https://github.com/mattpocock/skills/blob/2ab958093e83e0ec752e6c1c5932da465bf23e0c/skills/engineering/implement/SKILL.md)
- **[R11]** Matt Pocock, [ADR 0002 — Claude Code plugin 배포와 Codex plugin 보류](https://github.com/mattpocock/skills/blob/2ab958093e83e0ec752e6c1c5932da465bf23e0c/.agents/adr/0002-ship-as-a-claude-code-plugin.md)
- **[R12]** GitHub REST API, [mattpocock/skills repository metadata](https://api.github.com/repos/mattpocock/skills) — 2026-07-30 조회
- **[R13]** GSD, [gsd-build/get-shit-done](https://github.com/gsd-build/get-shit-done)
- **[R14]** BMAD, [bmad-code-org/BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD)
- **[R15]** GitHub, [github/spec-kit](https://github.com/github/spec-kit)
- **[R16]** GitHub REST API, [mattpocock/skills contributors](https://api.github.com/repos/mattpocock/skills/contributors) — 2026-07-30 조회
- **[R17]** Matt Pocock, [`package.json`](https://github.com/mattpocock/skills/blob/2ab958093e83e0ec752e6c1c5932da465bf23e0c/package.json)
- **[R18]** Matt Pocock, [Claude Code plugin manifest](https://github.com/mattpocock/skills/blob/2ab958093e83e0ec752e6c1c5932da465bf23e0c/.claude-plugin/plugin.json)
