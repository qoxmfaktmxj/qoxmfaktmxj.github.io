---
layout: post
title: "2026년 10월 1일 AI 뉴스: 에이전트 경제의 새 기준은 더 싼 추론이 아니라 컨텍스트·권한·모델 IP를 통제하는 운영 설계다"
date: 2026-10-01 11:30:00 +0900
categories: [ai-daily-news]
tags: [ai, news, agents, llmops, openai, gpt-6-1-sol, anthropic, claude, security, caching, governance]
permalink: /ai-daily-news/2026/10/01/ai-news-daily.html
---

# 오늘의 AI Daily News

## 작성 기준과 요약

2026년 10월 1일 11:30 KST 기준으로 공개된 **공식 발표만** 확인해 작성했다. 이번 실행에서 `web_search`는 제공자 언어 필터 오류로 결과를 반환하지 못했다. 검색 실패만으로 중단하지 않고 OpenAI News와 Anthropic News의 공식 인덱스 및 개별 발표를 직접 확인했다. 따라서 아래의 수치와 제품 설명은 각 회사의 공식 주장 범위 안에서만 다루며, 독립 검증이나 시장 순위로 확대 해석하지 않는다.

오늘의 핵심은 단순한 새 모델 출시가 아니다. OpenAI는 GPT-6.1 Sol을 통해 고급 에이전트 작업의 가격·캐시 가격·추론 노력 설정을 한 제품 표면에 올렸고, Anthropic은 Opus 5.5에서 장기 작업 성능과 action screening·sandbox·코드 검토를 함께 발표했다. 이어 OpenAI는 보호된 추론을 대규모로 추출하려는 coordinated distillation 사례도 공개했다. 세 소식은 같은 결론으로 수렴한다. **모델을 고르는 일은 이제 벤치마크 한 줄을 고르는 일이 아니라, 반복 컨텍스트를 어떻게 재사용하고, 에이전트 권한을 어디에서 끊고, 공급자 모델의 출력·추론 자산을 어떤 방식으로 취급할지 결정하는 운영 아키텍처의 문제다.**

---

## 한눈에 보는 Top News

1. **OpenAI, GPT-6.1 Sol 공개**
   - OpenAI는 agentic coding, computer use, 전문 업무에서 GPT-6 Astra에 근접한 성능을 더 낮은 비용으로 제공하는 GPT-6.1 Sol을 발표했다.
   - API 표준 가격은 입력 100만 토큰당 2달러, 캐시 입력 0.10달러, 출력 10달러다. 캐시 입력 가격은 반복 컨텍스트를 가진 agent 설계의 비용 모델을 크게 바꾼다.

2. **Anthropic, Claude Opus 5.5 공개**
   - Anthropic은 Opus 5.5가 Opus 5보다 typical workload에서 40% 낮은 비용과 30% 이상 빠른 출력을 제공한다고 설명했다.
   - 발표에는 모델 성능뿐 아니라 action별 screening classifier, 감사 가능한 sandbox, merge 전 code review, 외부 평가와 고위험 분야 safeguard가 포함됐다.

3. **OpenAI, 보호된 추론의 adversarial distillation 캠페인 차단 발표**
   - OpenAI는 7월부터 관찰한 조직적 추론 추출 시도를 계정 집행, 기술 제어, 파트너 협력으로 차단했다고 밝혔다.
   - 이는 모델 응답을 단순한 텍스트 API 결과가 아닌, 접근 제어·재생 방지·사용량 이상 탐지가 필요한 보호 자산으로 다뤄야 함을 보여 준다.

---

## 배경: ‘좋은 모델’의 단위가 endpoint에서 runtime으로 바뀌고 있다

초기 LLM 도입에서 팀의 질문은 대체로 간단했다. 어느 모델이 더 정확한가, 입력·출력 토큰 가격은 얼마인가, 응답 속도는 어떤가. 그러나 agent가 repository를 탐색하고, 문서를 읽고, 브라우저를 조작하고, 내부 API를 호출하고, 여러 세션에 걸쳐 업무를 이어가는 순간 이 질문만으로는 충분하지 않다. 같은 모델이라도 컨텍스트를 매번 새로 보내는지, 캐시를 재사용하는지, 어떤 reasoning effort로 실행하는지, 실패 때 어떤 모델로 fallback하는지, tool call을 실행 전에 누가 판정하는지에 따라 실제 비용·속도·위험이 완전히 달라진다.

GPT-6.1 Sol의 가격표와 Opus 5.5의 cache-read 가격은 이 변화를 숫자로 드러낸다. agentic coding이나 지식 작업은 시스템 프롬프트, 저장소 지침, 이전 tool trace, 문서 조각, 테스트 결과를 반복해서 참조한다. 이때 전체 request 비용보다 캐시 적중률과 컨텍스트 안정성이 더 큰 비용 변수가 될 수 있다. 반대로 장기 컨텍스트가 싸졌다는 이유로 모든 로그·비밀값·사용자 대화를 무제한으로 넣는 것은 보안과 품질 모두에 좋지 않다. 낮은 cache price는 data minimization의 면허가 아니라, 더 정교한 context lifecycle을 설계할 기회다.

동시에 OpenAI의 distillation 공지는 ‘보호된 추론’이 제품 경계 안에서 별도의 보안 대상이라는 점을 부각한다. 서비스가 보이지 않는 reasoning을 제공하지 않는다고 해서 그것이 공격 표면에서 사라지는 것은 아니다. 대화 재생, tool output, cross-session artifact, 대규모 계정 패턴을 통해 보호되어야 할 내부 정보가 드러날 수 있다. 에이전트 플랫폼의 운영자는 모델 공급자의 방어만 기대할 수 없다. 자신의 시스템에서도 secret, hidden instruction, internal tool schema, privileged trace가 어떤 경로로 복사·재사용·외부 전송될 수 있는지 다뤄야 한다.

---

## 1) GPT-6.1 Sol: 비용 하락의 핵심은 ‘더 많은 호출’이 아니라 ‘더 나은 작업 분해’다

**공식 출처:** [Introducing GPT-6.1 Sol](https://openai.com/index/introducing-gpt-6-1-sol/)

OpenAI는 9월 29일 GPT-6.1 Sol을 발표하며, agentic coding·computer use·professional work에서 GPT-6 Astra에 근접하는 성능을 Astra 표준 입력·출력 토큰 가격의 약 5분의 1 수준으로 제공한다고 설명했다. 표준 API 가격은 입력 100만 토큰당 2달러, 출력 10달러, 캐시 입력 0.10달러다. OpenAI는 이 모델이 ChatGPT Work와 Codex의 Plus·Pro·Business·Enterprise·Edu 사용자 및 API의 `gpt-6.1-sol`로 제공된다고 밝혔다.

공식 발표의 인상적인 부분은 단순한 가격 인하가 아니라 benchmark마다 effort와 작업 비용을 함께 제시한 방식이다. OpenAI는 DeepSWE 1.1에서 GPT-6 Astra와 비슷한 수준을 더 낮은 비용으로, AutomationBench에서 medium reasoning effort 기준 Opus 5.5보다 2.2포인트 높은 점수를 약 3분의 1 비용으로, OSWorld 2.0 offline set에서 GPT-6 Sol보다 7포인트 높은 결과를 제시했다. 이는 공급자 발표 수치이므로 실제 사내 작업에서 그대로 재현된다고 볼 수는 없다. 다만 팀이 ‘모델당 token price’만 보는 대신 **task completion당 비용과 성공률**을 측정해야 한다는 방향은 분명하다.

### 캐시 입력은 agent 설계의 1급 비용 지표다

캐시 입력 0.10달러/1M tokens는 표준 입력 가격보다 95% 낮다고 OpenAI는 설명한다. 이 수치가 중요한 이유는 장기 agent의 입력이 대개 두 종류로 나뉘기 때문이다.

- **안정 컨텍스트:** 시스템 지침, coding convention, tool schema, repo overview, 반복되는 정책 문서
- **변동 컨텍스트:** 현재 사용자 요청, 새 diff, 최근 test output, 실시간 DB/API 결과

안정 컨텍스트가 캐시에 잘 맞도록 request를 구성하면 비용과 latency가 줄 수 있다. 그러나 여기서의 최적화 대상은 토큰 절약 자체가 아니다. 동일한 base context를 재사용할수록 agent behavior의 재현성과 관측 가능성도 높아진다. 반대로 매 요청마다 지침 순서가 바뀌고, 오래된 trace와 새로운 trace를 무차별로 섞고, policy를 여러 곳에서 덧붙이면 캐시 효율도 떨어지고 디버깅도 어려워진다.

권장하는 request 설계는 고정 접두부와 변동 payload를 명확히 나누는 것이다. 고정 접두부에는 역할, 금지된 action, tool contract, data classification, output schema, 승인 규칙을 둔다. 변동 payload에는 현재 task와 필요한 최소 증거만 둔다. 이 경계가 명확하면 비용 최적화와 security review가 같은 방향으로 작동한다.

### reasoning effort는 품질 옵션이 아니라 배포 정책이다

OpenAI 발표은 동일 모델이라도 low·medium·maximum reasoning effort에서 비용과 평가 결과가 달라짐을 보여 준다. 예를 들어 사실성 평가에서 GPT-6.1 Sol은 low effort에서 GPT-6 Sol 대비 factual error가 포함된 응답 비율을 11.4%에서 7.7%로 낮췄다고 설명한다. 그러나 이 역시 어려운 오류 유도 대화에 대한 평가이며 일반 사용률이 아니다.

실무적으로 중요한 점은 effort를 사용자에게 노출한 드롭다운으로만 두지 않는 것이다. 업무 유형에 따라 기본값과 상한을 정해야 한다.

| 작업 유형 | 권장 접근 | 검증 기준 |
|---|---|---|
| 요약·분류·초안 | 낮은 effort, 제한된 context | 형식·근거 링크·금칙어 검사 |
| 코드 수정 제안 | 중간 effort, read-only 탐색 우선 | test·lint·diff review |
| 배포·권한 변경 | 높은 effort를 써도 자동 실행 금지 | 승인·정책 판정·rollback plan |
| 장기 조사 | 단계별 budget, 중간 산출물 저장 | source provenance·stop condition |

높은 effort가 필요한 task는 대개 더 큰 권한이나 더 큰 blast radius를 동반한다. 따라서 reasoning budget을 올릴수록 tool budget, 시간 제한, human checkpoint도 강화하는 편이 자연스럽다. ‘생각을 더 오래 하게 하면 안전하다’는 가정은 틀릴 수 있다. 더 오래 실행되는 agent는 더 많은 외부 상태를 읽고 더 많은 tool call을 시도할 기회를 갖기 때문이다.

### 개발자에게 의미

1. 모델 비교 표에 input/output 가격 외에 cache-read price, cache hit rate, task completion cost를 넣어야 한다.
2. 시스템 지침·tool schema·정책을 안정된 prefix로 관리하고, 현재 작업 증거는 작은 변동 suffix로 넣는다.
3. effort는 feature flag가 아니라 task risk class에 연동된 운영 정책으로 관리한다.
4. 벤치마크 점수보다 사내 repository, 실제 문서, 실제 승인 흐름에서의 accepted-result rate를 우선 측정한다.
5. model upgrade는 prompt regression, tool-call regression, 비용 회귀를 동시에 보는 canary로 진행한다.

### 운영 포인트

- request별 input/cached-input/output, effort, tool-call 수, 성공 여부를 trace에 남긴다.
- 캐시에 secrets·개인정보·장기 보존이 불필요한 원문을 넣지 않도록 context compiler를 둔다.
- maximum effort에는 시간·토큰·tool-call 상한을 함께 건다.
- retry는 같은 request를 무제한 반복하지 말고, 원인 분류 후 context 또는 모델을 바꾸는 명시적 전략을 사용한다.
- 비용 알람은 token 사용량뿐 아니라 task당 승인된 결과 수와 human rework 시간을 함께 본다.

---

## 2) Claude Opus 5.5: 장기 autonomy는 모델 성능과 execution guardrail을 한 패키지로 본다

**공식 출처:** [Introducing Claude Opus 5.5](https://www.anthropic.com/claude-opus-5-5)

Anthropic은 9월 22일 Claude 5.5 family의 첫 모델로 Opus 5.5를 소개했다. 공식 설명에 따르면 Opus 5.5는 Opus 5보다 typical workload에서 40% 낮은 비용, 30% 이상 빠른 출력 속도를 제공하며, 입력·출력은 각각 100만 토큰당 4달러·20달러, cache read는 0.20달러다. Anthropic은 자동 behavioral audit, 외부 평가기관 Frontier Design 및 METR의 출시 전 테스트, biology·cybersecurity 영역 safeguard를 함께 언급했다.

특히 주목할 부분은 ‘가장 좋은 coding model’이라는 주장보다, enterprise agent가 의도대로 행동하는지에 관한 제품 구성이었다. Anthropic은 모든 action을 실행 전에 screening하는 classifier, 보안팀이 감사할 수 있는 open-source sandbox, merge 전에 취약점을 포착하는 code review를 설명한다. 이 구조는 agent 안전을 모델의 refusal 품질 하나에 맡기지 않는다는 뜻이다. 모델이 안전 지시를 더 잘 따른다고 해도, 실제 shell·filesystem·browser·cloud API에 닿는 순간에는 독립된 enforcement layer가 필요하다.

### 긴 작업일수록 ‘완료’의 정의를 쪼개야 한다

장기 coding agent의 위험은 큰 diff만이 아니다. agent가 목표를 잘못 이해한 채 여러 시간 동안 합리적으로 보이는 작은 변경을 누적할 수 있다. 그 결과는 테스트가 통과해도 요구사항과 어긋난 기능, 보안 설정의 약화, reviewer가 이해하기 어려운 대규모 변경일 수 있다.

따라서 autonomy level을 다음처럼 나눌 필요가 있다.

1. **Observe:** repository와 문서를 읽고 계획·영향 범위를 보고한다.
2. **Propose:** 변경 후보와 예상 diff를 만들지만 파일을 변경하지 않는다.
3. **Execute in sandbox:** 별도 workspace에서 patch·test를 수행한다.
4. **Request approval:** diff, test result, 위험 요약, rollback 방법을 사람에게 제시한다.
5. **Merge or deploy:** CI·권한·변경관리 승인 뒤에만 실제 환경을 바꾼다.

이 단계를 두면 frontier model의 장기 추론 능력을 활용하면서도 irreversible action의 수를 줄일 수 있다. 중요한 것은 단계가 많다는 사실이 아니라, 각 단계에서 가능한 capability가 좁아진다는 점이다. `git diff`를 읽는 권한과 production secret을 회전시키는 권한은 같은 agent session에 기본으로 함께 있으면 안 된다.

### 속도와 가격은 human review의 대체 비용까지 포함해야 한다

Anthropic은 680,000-line migration, 200,000-line audit 등의 early tester 사례를 소개한다. 이는 모델의 긴 작업 능력이 커졌다는 유용한 신호지만, 고객 사례는 일반화된 성능 보장이 아니다. 조직이 실제로 측정해야 할 비용은 아래처럼 더 넓다.

- 모델 호출 비용과 캐시 비용
- sandbox compute, test runner, artifact storage 비용
- reviewer가 diff를 이해·수정·승인하는 시간
- false positive 보안 경고와 false negative 결함의 비용
- rollback, incident response, compliance evidence 비용

더 빠른 모델이 더 많은 변경을 만들어 낸다면 reviewer 병목은 오히려 커질 수 있다. 반대로 명확한 summary, 작은 commits, test evidence, policy denial reason을 함께 제공하면 높은 autonomy가 human throughput을 높일 수 있다. Anthropic이 communication의 명확성을 안전 이점으로 말한 이유도 여기에 있다. 사람이 모델 결과를 신속하고 정확하게 검증할 수 있어야 안전 제어가 실제로 작동한다.

### 개발자에게 의미

1. 장기 agent 도입은 model selection과 sandbox·action screening·review UX를 함께 평가해야 한다.
2. capability는 session 단위가 아니라 action 단위로 발급한다.
3. tool call마다 allow/deny만 기록하지 말고, approval required와 denial rationale을 구조화한다.
4. 큰 task는 plan, patch, test, review artifact를 분리해 중간에 멈추고 재개할 수 있게 한다.
5. 모델의 안전 평가 결과는 유용하지만, 자체 도메인 policy와 별도의 권한 시스템을 대체하지 않는다.

### 운영 포인트

- sandbox는 network egress, filesystem mount, credential visibility를 기본 deny로 시작한다.
- read-only 탐색과 mutation tool을 분리하고, mutation에는 idempotency와 rollback 정보를 요구한다.
- code review agent는 author agent와 독립된 context·권한을 갖도록 한다.
- agent가 실행하지 못한 action을 ‘실패’가 아니라 ‘승인 대기’로 분류해 안전한 UX를 만든다.
- 안전 classifier의 차단율, override율, 실제 incident와의 상관을 지속적으로 측정한다.

---

## 3) adversarial distillation: 출력 보안은 prompt injection 방어보다 넓다

**공식 출처:** [Disrupting a coordinated model-distillation campaign](https://openai.com/index/disrupting-a-coordinated-model-distillation-campaign/)

OpenAI는 9월 30일 보호된 reasoning을 추출하려는 coordinated campaign을 확인하고 차단했다고 발표했다. 공식 글에 따르면 이 활동은 7월 첫째 주부터 관찰됐으며, 7월 24~25일에는 4,000명 이상 사용자에 걸친 16,000건의 관련 request spike가 있었다. OpenAI는 15,000명 이상 사용자로 연결된 패턴을 확인해 7월 28일까지 차단했다고 설명한다. 회사는 데이터베이스 침해나 암호화 파괴가 아니라, model interaction을 조작해 requester에게 보이는 형태로 protected reasoning을 재현하려 했다고 밝혔다.

여기서 얻을 교훈은 특정 공급자의 사건 세부가 아니다. agent service에서 보이지 않는 내부 상태라도 여러 경로를 통해 가치 있는 artifact가 될 수 있다는 점이다. 시스템 프롬프트, hidden chain, tool schema, intermediate plan, evaluator feedback, sandbox log, cached context가 그 예다. 사용자가 볼 수 있는 최종 답변만 검토해서는 충분하지 않다.

### ‘텍스트를 숨긴다’와 ‘artifact를 보호한다’는 다르다

보호해야 할 정보는 UI에서 감추는 것만으로 안전해지지 않는다. 다음과 같은 경로를 함께 점검해야 한다.

- 대화 간 인용·복사·재생으로 이전 artifact가 다른 권한 경계에서 해석되는 경로
- tool output에 포함된 내부 header, URL, trace ID, credential fragment
- observability export, error report, support ticket에 기록된 원문 prompt
- 멀티테넌트 cache key 또는 job artifact의 격리 실패
- agent가 웹·문서에서 읽은 untrusted text가 privileged instruction처럼 다시 주입되는 경로

OpenAI는 계정 enforcement, signup·infrastructure controls, hidden reasoning의 사용자·workspace·organization·model family 간 보호 강화, streamed output hold 검사, 업계 정보 공유를 대응으로 언급했다. 이는 단일 classifier가 아니라 identity, rate, output scanning, tenancy boundary, investigation, partner coordination을 결합하는 layered defense의 사례다.

### 개발자가 적용할 수 있는 방어 모델

첫째, **최소 공개**다. 모델에게 전달하는 system instruction, tool description, error message에 꼭 필요한 정보만 둔다. ‘디버깅 편의’를 이유로 production stack trace나 internal endpoint를 사용자에게 그대로 내보내지 않는다.

둘째, **재생 방지와 binding**이다. 짧은 수명의 signed URL, job token, approval token은 사용자·tenant·task·만료 시간에 묶는다. 이전 세션의 artifact가 새 세션에서 권한 증명처럼 재사용되지 않게 한다.

셋째, **행동 기반 탐지**다. content가 정상처럼 보여도 고속 반복, 계정 클러스터, 비정상적인 context reuse, 출력 길이·형식의 반복적 탐색을 rate limit과 anomaly detection의 입력으로 삼는다.

넷째, **tool-output sanitization**이다. agent가 tool 결과를 모델에 다시 넣을 때 HTML, markdown, quoted instruction, secret-like value를 data로 취급하고, provenance를 태깅하며, 위험한 action으로 곧바로 연결하지 않는다. 모델이 외부 텍스트를 읽었다는 사실과 그 텍스트를 실행 권한으로 신뢰한다는 것은 전혀 다른 일이다.

### 운영 포인트

- 사용자 응답, model trace, tool trace, audit log의 retention과 접근 역할을 따로 정한다.
- high-volume extraction pattern과 credential stuffing을 같은 identity-risk pipeline에서 관찰한다.
- error response에 internal model configuration, hidden instruction, raw upstream body가 섞이지 않게 contract test를 둔다.
- tenant 경계를 넘는 cache·artifact 접근을 정기적으로 negative test한다.
- 공급자 incident 공지를 vendor risk register와 architecture review에 반영한다.

---

## 세 발표를 하나의 운영 청사진으로 연결하기

| 계층 | 오늘의 신호 | 팀이 해야 할 일 |
|---|---|---|
| 모델 라우팅 | Sol·Opus 모두 성능/비용/effort 조합을 강조 | task별 품질·비용·latency SLO를 정의 |
| 컨텍스트 | cache price가 agent economics의 핵심 변수 | stable prefix와 최소 변동 context를 분리 |
| 실행 | Opus 5.5가 screening·sandbox·review를 제시 | tool 권한, sandbox, approval을 모델 외부에서 강제 |
| 보안 | distillation 사례가 hidden artifact 보호를 부각 | output·trace·cache·replay를 포함한 threat model 작성 |
| 관측 | 장기 agent의 비용과 위험은 누적 행동에서 발생 | session/task/tenant 단위 trace와 kill switch 운영 |

이 표가 뜻하는 바는 단순하다. 비용이 낮아질수록 agent를 더 자주, 더 길게, 더 많은 업무에 쓰려는 압력이 커진다. 이때 가장 먼저 확장해야 할 것은 token budget만이 아니라 governance budget이다. 모델 호출량이 두 배가 되면 비용만 두 배가 되는 것이 아니라, untrusted input, tool side effect, cache retention, reviewer queue, incident surface도 함께 커질 수 있다.

---

## 바로 적용할 10개 체크리스트

1. 현재 agent request에서 stable context와 task-specific context를 분리해 token·cache 비율을 측정한다.
2. 모델별 품질 지표를 benchmark가 아닌 승인된 실제 작업 단위로 정의한다.
3. reasoning effort별 최대 시간·토큰·tool-call 수를 설정한다.
4. 모든 write tool에 `dry-run`, idempotency key, rollback 또는 compensation 경로를 둔다.
5. agent의 sandbox에서 filesystem·network·credential 접근을 명시적으로 allowlist한다.
6. tool action 전 policy decision과 action 후 result를 같은 correlation ID로 저장한다.
7. hidden prompt, raw tool output, trace export에 대한 redaction test를 CI에 추가한다.
8. cache와 job artifact를 tenant·user·task·expiry에 묶고 cross-tenant negative test를 작성한다.
9. high-cost loop, repeated write, unusual extraction pattern을 탐지하는 session-level alert를 만든다.
10. model release 때 가격·성능 평가와 함께 prompt injection, authorization bypass, data leakage regression을 재실행한다.

---

## 결론

오늘의 발표들은 AI 경쟁이 값싼 토큰으로 끝나지 않는다는 사실을 보여 준다. GPT-6.1 Sol의 낮은 캐시 입력 가격은 반복 컨텍스트를 가진 에이전트를 경제적으로 만들지만, 그 컨텍스트를 오래·넓게 보관하라는 뜻은 아니다. Claude Opus 5.5의 장기 작업 능력은 큰 업무를 위임할 가능성을 넓히지만, action screening·sandbox·review 같은 독립 통제가 없으면 위험도 함께 커진다. OpenAI의 distillation 대응은 모델의 ‘보이지 않는’ artifact조차 identity·rate·output·tenancy 제어가 필요한 공격 표면임을 확인시킨다.

따라서 개발팀의 다음 질문은 “어느 모델이 더 싸고 똑똑한가?”에서 멈추면 안 된다. **어떤 컨텍스트를 재사용할 것인가, 누가 어떤 action을 허용할 것인가, 어떤 artifact를 보존·차단·감사할 것인가, 그리고 실패했을 때 얼마나 빨리 멈추고 되돌릴 것인가?** 이 네 질문에 답하는 runtime을 갖춘 팀이 모델 가격 하락을 실제 생산성으로 바꿀 수 있다.

---

## 소스 링크

- [OpenAI — Introducing GPT-6.1 Sol](https://openai.com/index/introducing-gpt-6-1-sol/)
- [OpenAI — DevDay 2026 Recap](https://openai.com/index/devday-2026-recap/)
- [OpenAI — Disrupting a coordinated model-distillation campaign](https://openai.com/index/disrupting-a-coordinated-model-distillation-campaign/)
- [Anthropic — Introducing Claude Opus 5.5](https://www.anthropic.com/claude-opus-5-5)
- [OpenAI News](https://openai.com/news/)
- [Anthropic News](https://www.anthropic.com/news)
