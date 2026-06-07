---
layout: post
title: "2026년 6월 7일 AI 뉴스: agent 운영체계, Work IQ API, GitHub agent task API, ChatGPT Dreaming, GPT-Rosalind, Gemma 4 12B, AWS Quick와 OpenAI on Bedrock"
date: 2026-06-07 11:30:00 +0900
categories: [ai-daily-news]
tags: [ai, news, agentic-ai, openai, chatgpt, memory, dreaming, gpt-rosalind, codex, microsoft, work-iq, agent-365, assert, acs, github, copilot, google, gemma, aws, amazon-quick, bedrock, developers, operations, governance]
permalink: /ai-daily-news/2026/06/07/ai-news-daily.html
---

# 오늘의 AI Daily News

## 작성 기준

2026년 6월 7일 11:30 KST 기준으로 공개된 공식 발표와 공식 뉴스/블로그 index를 확인해 작성했습니다. 검색 API가 정상 동작하지 않는 환경을 고려해 OpenAI, Microsoft, GitHub, Google Developers, AWS, Anthropic의 공식 index와 알려진 공식 발표 URL을 직접 확인했습니다. 비공식 루머, 소셜 미디어 반응, 제3자 기사 해설은 본문 근거로 사용하지 않았습니다.

오늘은 일요일이라 "오늘 새벽 새 모델이 갑자기 나왔다"는 식의 단건 속보보다, 지난 며칠 사이 공식 발표들이 한 방향으로 모인 구조가 중요합니다. OpenAI는 ChatGPT memory를 Dreaming 기반으로 확장하고, GPT-Rosalind를 생명과학 연구 workflow와 provenance 중심으로 강화했으며, Codex를 직무별 workbench로 넓혔습니다. Microsoft는 Build 2026에서 Microsoft Agent Platform, Microsoft IQ, Work IQ APIs, Agent 365, ASSERT, Agent Control Specification, MDASH를 묶어 agent 운영체계의 표준 형태를 제시했습니다. GitHub는 Copilot cloud agent task를 REST API로 시작하고 추적할 수 있게 했고, VS Code는 Agents window, remote agent, BYOK, terminal risk assessment를 확장했습니다. Google은 Gemma 4 12B와 LiteRT-LM을 통해 로컬 멀티모달 agent의 실행면을 구체화했습니다. AWS는 Amazon Quick, Amazon Connect agentic solutions, OpenAI models/Codex/Managed Agents on Bedrock을 통해 기업 업무 agent를 AWS governance 안으로 끌어들였습니다.

핵심은 한 문장입니다.

**AI 경쟁의 중심이 "어떤 모델이 더 똑똑한가"에서 "기억, 맥락, 도구 실행, 보안, 비용, 평가, 감사, 로컬/클라우드 배포를 어떤 운영체계로 묶는가"로 이동했습니다.**

---

## 한눈에 보는 Top News

1. **Microsoft Work IQ APIs가 2026년 6월 16일 GA 예정**
   - 발표일: 2026-06-02
   - 핵심: Microsoft 365의 email, calendar, meeting, chat, file, people, line-of-business context를 agent가 쓰기 좋은 형태로 제공하는 API입니다.
   - 개발자 의미: enterprise agent는 raw search API가 아니라 의미화된 업무 context API, tool abstraction, workspace state, tenant boundary를 요구합니다.

2. **Microsoft Agent Platform: build, contextualize, run, govern, improve, surface**
   - 발표일: 2026-06-02
   - 핵심: Azure, GitHub, Microsoft IQ, Fabric, Foundry, Windows, Microsoft Security, Microsoft 365를 하나의 agent production system으로 묶는 방향입니다.
   - 개발자 의미: agent는 prompt와 모델 endpoint가 아니라 software lifecycle 대상입니다. source, eval, trace, deploy, policy, rollback이 있어야 합니다.

3. **ASSERT와 Agent Control Specification: agent 신뢰를 open eval과 runtime control로 분리**
   - 발표일: 2026-06-02
   - 핵심: ASSERT는 policy-driven evaluation framework이고, ACS는 input, LLM, state, tool execution, output checkpoint에 control을 배치하는 portable runtime control standard입니다.
   - 개발자 의미: guardrail을 system prompt에만 넣는 시대는 끝나고 있습니다. control은 versionable policy와 observable runtime event가 되어야 합니다.

4. **GitHub Copilot Agent tasks REST API가 개인 유료 플랜까지 확대**
   - 발표일: 2026-06-04
   - 핵심: Copilot Pro, Pro+, Max 사용자가 Copilot cloud agent task를 API로 시작하고 추적할 수 있게 됐습니다.
   - 개발자 의미: coding agent는 UI 속 버튼이 아니라 internal developer portal, migration script, release automation이 호출하는 programmable worker가 됩니다.

5. **VS Code의 Agents window와 BYOK, terminal safety 확장**
   - 발표일: 2026-06-04
   - 핵심: VS Code Stable preview에 Agents window가 들어오고, remote agents, Agent Host Protocol, BYOK token visibility, reasoning effort controls, command risk assessment가 확장됐습니다.
   - 개발자 의미: agent IDE의 핵심은 chat box가 아니라 multi-session review, remote execution, cost visibility, command safety, browser/screenshot context입니다.

6. **OpenAI ChatGPT Dreaming: memory의 핵심은 저장이 아니라 최신성 유지**
   - 발표일: 2026-06-04
   - 핵심: Dreaming 기반 memory architecture가 staleness, correctness, scalability 문제를 해결하기 위해 확장됩니다.
   - 개발자 의미: personalization은 `user_profile` JSON 하나로 끝나지 않습니다. memory lifecycle, provenance, expiry, conflict policy, user control이 제품 품질을 좌우합니다.

7. **OpenAI GPT-Rosalind: 생명과학 AI는 benchmark보다 workflow provenance가 중요**
   - 발표일: 2026-06-03
   - 핵심: GPT-5.5의 agentic coding/tool-use 능력과 life sciences domain intelligence를 결합하고 LifeSciBench, MedChemBench, GeneBench, LabWorkBench, Codex plugin을 공개했습니다.
   - 개발자 의미: 전문 도메인 AI는 답변 정확도만으로 출시할 수 없습니다. evidence, artifact, tool run, expert review, access control이 함께 있어야 합니다.

8. **Google Gemma 4 12B: 로컬 멀티모달 agent가 실무 선택지로 이동**
   - 발표일: 2026-06-03
   - 핵심: encoder-free dense multimodal model, audio input, 16GB VRAM/unified memory급 로컬 실행, LiteRT-LM OpenAI-compatible local server가 핵심입니다.
   - 개발자 의미: privacy, latency, offline UX가 중요한 제품은 cloud-only architecture를 당연하게 보면 안 됩니다.

9. **AWS What’s Next 2026: Amazon Quick, Connect agentic solutions, OpenAI on Bedrock**
   - 공식 index 확인 기준: AWS News Blog
   - 핵심: Amazon Quick은 업무용 AI assistant/desktop app으로 확장되고, Amazon Connect는 supply chain, hiring, customer experience, healthcare agentic solutions로 넓어집니다. OpenAI models, Codex, Managed Agents가 Bedrock limited preview로 들어갑니다.
   - 개발자 의미: 기업 AI 도입은 procurement, IAM, billing, audit, data boundary가 이미 있는 cloud control plane 안에서 움직입니다.

---

## 배경: 이제 AI 제품은 "모델 호출"이 아니라 "agent 운영체계"다

2024년의 AI 제품은 대체로 chat completion을 잘 붙이는 문제였습니다. 2025년에는 RAG, function calling, code agent, workflow automation이 실무에 들어왔습니다. 2026년 6월 첫째 주의 공식 발표들은 다음 단계를 보여 줍니다. 이제 경쟁 대상은 모델 하나가 아닙니다. 경쟁 대상은 agent가 기억하고, 조직 데이터를 이해하고, 도구를 호출하고, 산출물을 만들고, 사람이 검토하고, 보안팀이 감사하고, 비용팀이 예산을 통제하고, 개발팀이 개선할 수 있는 전체 운영체계입니다.

이 변화가 중요한 이유는 agent가 기존 앱과 다르게 동작하기 때문입니다. 기존 앱은 사용자가 버튼을 누르면 정해진 코드 경로가 실행됩니다. agent는 목표를 해석하고, 계획을 세우고, context를 찾고, 여러 tool을 호출하고, 중간 상태를 저장하고, 실패하면 우회하고, 마지막에 산출물을 냅니다. 이 과정은 길고, 불확실하고, 비용이 들며, 보안 위험도 있습니다. 그래서 agent를 production에 올리는 순간 다음 질문이 생깁니다.

- 이 agent는 어떤 데이터에 접근할 수 있는가?
- 접근 권한은 사용자 권한을 그대로 상속하는가, agent 전용 권한을 쓰는가?
- tool call 전후에 어떤 policy checkpoint가 있는가?
- 실패하거나 위험한 command를 실행하려 할 때 누가 막는가?
- 장기 작업의 중간 state는 어디에 저장되는가?
- agent가 만든 결과는 누가 검토하고 승인하는가?
- 비용은 token, credit, action minute, sandbox runtime 중 무엇으로 측정되는가?
- 같은 작업을 다음 주에 더 잘하려면 어떤 trace와 feedback이 학습 loop로 들어가는가?

Microsoft가 Build 2026에서 제시한 build, contextualize, run, govern, improve, surface 흐름은 이 질문들에 대한 엔터프라이즈형 답입니다. GitHub의 REST API는 coding agent를 자동화 가능한 worker로 만듭니다. OpenAI의 Dreaming은 personal assistant의 장기 기억이 storage 문제가 아니라 time-aware synthesis 문제임을 보여 줍니다. Google의 Gemma 4 12B는 이 실행면이 cloud에만 있어야 하는 것은 아니라고 말합니다. AWS는 모델과 agent를 고객의 기존 cloud governance로 흡수합니다.

결국 2026년의 AI 아키텍처는 다음 계층으로 정리할 수 있습니다.

- **Model layer:** GPT, Gemini, Claude, MAI, Gemma 같은 추론 엔진
- **Context layer:** Work IQ, Fabric IQ, retrieval planning, memory, semantic index, source metadata
- **Tool layer:** MCP, REST API, app connector, CLI, browser, local file, enterprise workflow action
- **Agent runtime:** sandbox, state machine, planner, worker, subagent, remote execution, retry
- **Control layer:** identity, policy, guardrail, ACS checkpoint, DLP, command risk assessment
- **Evaluation layer:** ASSERT, domain benchmark, multi-turn eval, simulation, regression suite
- **Observability layer:** traces, tool logs, provenance, cost, outcome, reviewer feedback
- **Human review layer:** PR, annotation, artifact, dashboard, approval, exception handling
- **Distribution layer:** IDE, Microsoft 365, Teams, browser, desktop app, cloud API, local server

모델만 잘 고르는 팀은 여기서 밀립니다. agent를 실제 업무에 넣으려면 이 계층들을 제품과 운영 기준으로 설계해야 합니다.

---

## 1) Microsoft Work IQ APIs: agent에게 필요한 것은 "검색 결과"가 아니라 업무 맥락이다

**공식 발표:** 2026-06-02  
**공식 출처:** https://www.microsoft.com/en-us/microsoft-365/blog/2026/06/02/announcing-the-new-work-iq-apis/

Microsoft는 Work IQ APIs가 2026년 6월 16일 일반 제공될 예정이라고 발표했습니다. Work IQ는 Microsoft 365 안의 email, calendar, meeting, chat, file, people, collaboration pattern, line-of-business system context를 agent가 사용하기 좋은 semantic layer로 가공합니다. 발표에서 강조한 장점은 intelligence, speed, efficiency, scale, security입니다.

중요한 지점은 API surface입니다. Work IQ APIs는 Chat, Context, Tools, Workspaces라는 네 영역으로 구성됩니다. Chat은 Microsoft 365 Copilot이 사용자에게 반환할 응답과 citation을 programmatic하게 제공합니다. Context는 agent가 직접 처리할 수 있도록 Copilot이 쓸 context를 구조화해서 반환합니다. Tools는 email 보내기, meeting scheduling, document upload 같은 Microsoft 365 action을 안정적인 verb/resource 구조로 제공합니다. Workspaces는 long-running agent가 중간 state, file, memory, progress, intermediate output을 tenant boundary 안에 저장할 수 있게 합니다.

### 개발자에게 의미

개발자가 enterprise agent를 만들 때 흔히 하는 실수는 "검색 API를 붙이면 context가 해결된다"고 보는 것입니다. 검색은 raw material입니다. agent가 실제 업무를 하려면 검색 결과 이상의 정보가 필요합니다. 예를 들어 "다음 주 고객 미팅 준비해줘"라는 작업에는 email thread, calendar invite, 참석자 관계, 최근 문서, CRM 상태, 미팅 목적, 이전 action item, 회사 policy가 모두 얽힙니다. 검색 결과 목록만으로는 agent가 안정적으로 실행하기 어렵습니다.

Work IQ가 보여 주는 방향은 context API가 다음 속성을 가져야 한다는 것입니다.

- **semantic index:** 단순 keyword가 아니라 사람, 조직, 문서, 회의, 업무 흐름의 의미 관계를 이해해야 합니다.
- **agent-optimized retrieval:** agent가 여러 round trip을 반복하지 않도록 필요한 context를 묶어서 줘야 합니다.
- **tool surface compression:** 수백 개 API를 직접 노출하기보다 agent가 다룰 수 있는 작은 action vocabulary로 추상화해야 합니다.
- **tenant trust boundary:** context와 중간 state가 조직 보안 경계 밖으로 흘러가지 않아야 합니다.
- **auditable action:** agent가 어떤 source를 보고 어떤 action을 했는지 추적 가능해야 합니다.
- **cost visibility:** context 호출과 tool 호출이 consumption pricing으로 이어질 때 budget dashboard가 필요합니다.

이 패턴은 Microsoft 365에만 해당하지 않습니다. Notion, Jira, Linear, Salesforce, Slack, Google Workspace, GitHub, ServiceNow 같은 업무 시스템을 운영하는 모든 플랫폼이 비슷한 압력을 받을 것입니다. 사람용 REST API는 너무 잘게 쪼개져 있고, agent용으로는 context가 부족합니다. 앞으로 SaaS 경쟁력은 "agent가 내 제품을 얼마나 안전하고 정확하게 조작할 수 있는가"로 평가될 가능성이 큽니다.

### 운영 포인트

기업이 Work IQ 같은 context API를 도입할 때는 다음을 점검해야 합니다.

1. **권한 상속 모델:** agent가 사용자 권한을 그대로 상속하는지, 별도 service principal을 쓰는지 명확해야 합니다.
2. **least privilege:** agent가 모든 Microsoft 365 데이터에 접근하지 않도록 scope를 작업별로 제한해야 합니다.
3. **workspace retention:** agent workspace에 저장된 중간 산출물의 보관 기간과 삭제 정책을 정해야 합니다.
4. **citation policy:** agent 결과가 의사결정에 쓰일 경우 source citation이 필수인지 정해야 합니다.
5. **credit budget:** Copilot Credits 기반 pricing은 팀별, 사용자별, agent별 spending limit이 필요합니다.
6. **audit review:** 누가 어떤 agent를 통해 어떤 email을 보내고 어떤 meeting을 잡았는지 audit log로 추적해야 합니다.
7. **human approval:** 외부 발송, 계약 변경, 고객 record 수정 같은 action에는 승인 단계를 둬야 합니다.

Work IQ APIs의 메시지는 분명합니다. enterprise agent의 승부처는 모델 endpoint가 아니라 context runtime입니다.

---

## 2) Microsoft Agent Platform: agent는 production software lifecycle로 들어왔다

**공식 발표:** 2026-06-02  
**공식 출처:** https://blogs.microsoft.com/blog/2026/06/02/ai-alone-wont-change-your-business-the-system-running-it-will/  
**공식 출처:** https://blogs.microsoft.com/blog/2026/06/02/microsoft-build-2026-be-yourself-at-work/

Microsoft는 AI alone이 아니라 AI를 실행하는 system이 business transformation을 만든다고 설명했습니다. 여기서 system은 GitHub, Microsoft IQ, Foundry, Agent 365, Windows, Microsoft Security, Microsoft 365, Azure를 묶은 agent platform입니다. Microsoft가 제시한 lifecycle은 build, contextualize, run, govern, improve, surface입니다.

이 구조는 agent를 "새로운 앱 유형"으로 다룹니다. agent는 GitHub에서 code, skill, tool, eval, observability asset과 함께 version 관리됩니다. Microsoft IQ로 기업 context를 붙입니다. Foundry에서 model routing, tool/action, eval, trace, policy rail을 포함한 runtime으로 실행합니다. Agent 365와 Entra, Purview, Defender로 agent estate를 관리합니다. 운영 중 생성되는 trace, outcome, feedback을 다시 eval과 optimization loop로 돌립니다. 마지막으로 Teams, Microsoft 365, 내부 앱, Windows, Azure surface에 배포합니다.

### 개발자에게 의미

개발팀 입장에서 가장 중요한 변화는 agent artifact의 단위입니다. 예전에는 prompt가 주요 artifact였습니다. 이제 prompt만으로는 부족합니다. production agent repository에는 최소한 다음이 들어가야 합니다.

- agent instruction과 role definition
- tool manifest와 permission scope
- context source definition
- memory/state schema
- policy YAML 또는 guardrail config
- eval scenario와 regression suite
- sandbox/runtime config
- observability/tracing config
- cost budget과 model routing policy
- approval workflow
- rollback plan

이 구성이 필요한 이유는 agent가 코드를 생성하는 것보다 더 넓은 일을 하기 때문입니다. agent는 고객 데이터를 읽고, 내부 문서를 요약하고, issue를 만들고, PR을 열고, meeting을 잡고, email draft를 만들고, 외부 API를 호출할 수 있습니다. 이런 action은 일반 software change처럼 review되어야 하고, 장애가 나면 incident response 대상이 되어야 합니다.

### 운영 포인트

agent platform을 도입하는 조직은 "몇 개 agent를 만들 수 있나"보다 "agent estate를 어떻게 관리하나"를 먼저 봐야 합니다.

- **catalog:** 조직 안에 어떤 agent가 존재하는지 한눈에 보여야 합니다.
- **owner:** 각 agent의 business owner, technical owner, security owner가 있어야 합니다.
- **access map:** agent별 data source와 action 권한이 보여야 합니다.
- **cost map:** agent별 token, credit, runtime, action cost가 집계되어야 합니다.
- **policy map:** 어떤 policy가 어떤 checkpoint에서 적용되는지 보여야 합니다.
- **change history:** instruction, model, tool, policy, eval 변경 이력이 남아야 합니다.
- **kill switch:** 위험 agent를 즉시 중지할 수 있어야 합니다.
- **exception process:** 정책 예외가 필요할 때 승인과 만료 기간이 있어야 합니다.

Microsoft가 말하는 agent platform은 단순히 Microsoft 제품 홍보가 아닙니다. 2026년 이후 enterprise AI 운영의 기본 checklist에 가깝습니다.

---

## 3) ASSERT와 Agent Control Specification: guardrail은 prompt가 아니라 runtime control이다

**공식 발표:** 2026-06-02  
**공식 출처:** https://devblogs.microsoft.com/foundry/build-2026-open-trust-stack-ai-agents/

Microsoft Foundry 팀은 Build 2026에서 ASSERT와 Agent Control Specification을 발표했습니다. ASSERT는 policy-driven agent evaluation framework입니다. 조직의 policy와 requirement를 입력으로 받아 agent가 실패할 수 있는 scenario를 만들고, safety/quality defect를 production 전에 찾는 구조입니다. ACS는 agent workflow의 input, LLM, state, tool execution, output checkpoint에 deterministic control logic을 넣는 portable runtime control standard입니다.

중요한 점은 eval과 enforcement가 분리되어 있다는 것입니다. ASSERT는 "어디서 실패하는가"를 찾습니다. ACS는 "어디에 어떤 control을 둘 것인가"를 정의합니다. 다시 ASSERT를 돌려 개선 여부를 확인합니다. 이는 agent trust를 closed loop로 만들려는 접근입니다.

### 개발자에게 의미

많은 팀이 guardrail을 system prompt 문장 몇 줄로 처리합니다. 예를 들어 "민감정보를 유출하지 마", "위험한 명령을 실행하지 마", "회사의 정책을 지켜" 같은 문장을 넣습니다. 이 방식은 demo에서는 그럴듯하지만 production에서는 취약합니다. agent가 tool을 호출하고, state를 업데이트하고, 외부 시스템에 action을 실행하는 순간 guardrail은 model output만 감시해서는 부족합니다.

ACS가 제시하는 checkpoint 중심 사고가 더 실용적입니다.

- **input checkpoint:** 사용자의 요청이 허용 가능한지, 정책 위반 의도가 있는지 확인
- **LLM checkpoint:** model response나 plan이 policy를 벗어나는지 확인
- **state checkpoint:** agent memory/state에 저장하면 안 되는 정보가 들어가는지 확인
- **tool execution checkpoint:** tool call이 권한, 비용, 위험 수준을 초과하는지 확인
- **output checkpoint:** 최종 결과가 외부 공유 가능한지, citation이 필요한지 확인

이렇게 나누면 control을 더 정확히 배치할 수 있습니다. 예를 들어 shell command는 tool execution checkpoint에서 risk assessment와 allow/deny policy를 적용해야 합니다. 개인정보 저장은 state checkpoint에서 막아야 합니다. 고객에게 보내는 email은 output checkpoint와 human approval을 결합해야 합니다.

### 운영 포인트

agent safety 운영팀은 다음 원칙을 세워야 합니다.

1. policy는 문서가 아니라 testable requirement여야 합니다.
2. eval은 single-turn Q&A뿐 아니라 multi-turn workflow를 포함해야 합니다.
3. control은 prompt, code, gateway, runtime 중 어디에 있는지 명확해야 합니다.
4. policy YAML은 version control되어야 합니다.
5. control event는 trace와 함께 남아야 합니다.
6. block, warn, require approval, redact, escalate 같은 action type을 구분해야 합니다.
7. production drift를 잡기 위해 sampling evaluation을 지속해야 합니다.

agent가 복잡해질수록 "우리 agent는 안전합니다"라는 선언은 의미가 없어집니다. 어떤 policy를 어떤 scenario로 평가했고, 어떤 checkpoint에서 어떤 control을 적용했고, 그 결과 defect rate가 어떻게 줄었는지가 증거입니다.

---

## 4) GitHub Copilot Agent tasks REST API: coding agent는 자동화 가능한 worker가 됐다

**공식 발표:** 2026-06-04  
**공식 출처:** https://github.blog/changelog/2026-06-04-agent-tasks-rest-api-now-available-for-copilot-pro-pro-and-max/  
**관련 공식 출처:** https://github.blog/changelog/2026-05-13-start-copilot-cloud-agent-tasks-via-the-rest-api/

GitHub는 Copilot Pro, Pro+, Max 사용자가 Agent tasks REST API로 Copilot cloud agent task를 시작하고 추적할 수 있다고 발표했습니다. 이전에는 Copilot Business와 Enterprise 중심으로 public preview가 제공됐고, 6월 4일 발표로 개인 유료 플랜까지 확대됐습니다.

Copilot cloud agent는 자체 개발 환경에서 백그라운드로 작업하고, code change를 만들고 검증한 뒤 pull request를 열 수 있습니다. REST API는 refactor나 migration을 여러 repository에 fan-out하거나, internal developer portal에서 새 repository setup을 자동화하거나, 매주 release preparation과 release note 생성을 자동화하는 용도로 설명됩니다.

### 개발자에게 의미

이 발표의 핵심은 coding agent가 IDE feature에서 platform primitive로 바뀌었다는 점입니다. UI에서 "Copilot에게 맡기기"를 누르는 수준을 넘어, 조직의 automation system이 coding agent를 worker로 호출할 수 있습니다.

예를 들어 다음 workflow가 가능해집니다.

- framework version upgrade를 50개 repo에 분산 실행
- security advisory가 뜨면 영향 repo별 patch PR 생성
- 신규 service template 생성 후 boilerplate와 CI 설정 적용
- weekly dependency update와 changelog 초안 생성
- deprecated API migration 후보를 issue에서 agent task로 전환
- release branch 생성 후 release note와 test checklist 준비

그러나 API가 생긴다는 것은 위험도 커진다는 뜻입니다. agent task를 programmatic하게 만들 수 있으면 잘못된 script 하나가 수십 개 repository에 PR을 열 수 있습니다. 따라서 rate limit, allowlist, repository scope, branch policy, reviewer assignment, CI gate가 함께 필요합니다.

### 운영 포인트

Copilot cloud agent task API를 쓰는 조직은 다음 guardrail을 둬야 합니다.

1. **repo allowlist:** agent가 작업할 수 있는 repository를 명시적으로 제한합니다.
2. **task template:** 자유 prompt보다 approved task template을 우선합니다.
3. **branch naming policy:** agent branch를 추적 가능한 prefix로 통일합니다.
4. **CI mandatory:** agent PR은 최소 build/test/security scan을 통과해야 합니다.
5. **human review:** 자동 merge는 매우 제한적으로만 허용합니다.
6. **blast radius limit:** 한 번에 생성 가능한 task 수와 변경 파일 수를 제한합니다.
7. **cost tracking:** task별 AI credit, Actions minute, runtime을 기록합니다.
8. **failure taxonomy:** compile failure, test failure, policy block, ambiguous requirement, external dependency failure를 구분합니다.

coding agent API의 가치는 "개발자를 대체한다"가 아닙니다. 반복적이고 넓게 퍼진 engineering maintenance를 scriptable하게 만들고, 사람은 review와 decision에 집중하게 하는 데 있습니다.

---

## 5) VS Code Agents window: agent IDE는 chat box가 아니라 작업 관제면이다

**공식 발표:** 2026-06-04  
**공식 출처:** https://github.blog/changelog/2026-06-04-github-copilot-in-visual-studio-code-may-releases/

GitHub의 VS Code May releases 정리에 따르면 Agents window가 VS Code Stable preview로 제공됩니다. 이 기능은 여러 project에서 agent-first로 작업하고, 변경 사항을 빠르게 review하는 dedicated surface입니다. remote agents는 SSH 또는 Dev Tunnels를 통해 remote machine에서 session을 실행하고 client 연결이 끊겨도 계속 진행될 수 있습니다. Agent Host Protocol은 여러 client 간 agent session state를 동기화하는 방향으로 발전 중입니다.

BYOK 측면에서는 air-gapped environment, custom endpoint provider, provider별 model picker, BYOK token visibility, reasoning effort controls, configurable utility models가 확장됐습니다. terminal safety에서는 verbose output compression, AI-generated command risk assessment, sensitive prompt terminal isolation, background command cleanup, `VSCODE_AGENT` environment variable이 추가됐습니다. integrated browser에는 device emulation과 screenshot attachment가 포함됩니다.

### 개발자에게 의미

agent 개발 도구는 더 이상 채팅창 하나로 충분하지 않습니다. 실제 agent 작업에는 다음 화면이 필요합니다.

- 여러 agent session을 나란히 보는 작업 관제면
- plan, diff, terminal, browser, screenshot, test output을 연결해서 보는 review surface
- remote sandbox에서 진행 중인 작업을 끊김 없이 추적하는 session model
- 어떤 model이 어떤 작업에 쓰였고 token이 얼마나 들었는지 보여 주는 cost view
- command 실행 전 위험 수준과 이유를 보여 주는 safety prompt
- verbose log를 model context에 넣기 전에 압축하는 context hygiene

이 흐름은 IDE의 역할을 바꿉니다. IDE는 더 이상 사람이 직접 코드를 입력하는 편집기만이 아닙니다. agent가 작업하고 사람이 검토하는 control room이 됩니다.

### 운영 포인트

팀 차원에서 VS Code agent 기능을 도입할 때는 다음 기준이 필요합니다.

1. agent session log와 PR이 연결되는가?
2. remote agent가 사용하는 machine image와 secret policy는 통제되는가?
3. BYOK model 사용 시 data residency와 logging 정책은 맞는가?
4. reasoning effort와 model 선택이 비용 정책을 초과하지 않는가?
5. terminal risk assessment가 override될 때 기록이 남는가?
6. browser screenshot이나 local file preview가 민감정보를 agent context에 넣지 않는가?
7. utility model까지 포함해 모든 model usage가 추적되는가?

agent IDE의 maturity는 autocomplete 품질이 아니라 작업의 검증 가능성에서 갈립니다.

---

## 6) OpenAI Dreaming: memory는 "더 많이 기억하기"보다 "시간에 맞게 정리하기"가 어렵다

**공식 발표:** 2026-06-04  
**공식 출처:** https://openai.com/index/chatgpt-memory-dreaming/

OpenAI는 ChatGPT의 memory synthesis를 개선하는 Dreaming 기반 architecture를 공개했습니다. 발표에 따르면 memory는 사용자의 preference, project, constraint를 반영해 대화가 매번 처음부터 시작하지 않도록 돕습니다. OpenAI는 memory의 목표를 useful context carry-forward, preference/constraint following, staying current over time으로 설명했습니다. Dreaming은 background process로 chat history를 참고해 memory state를 자동 curate하고, staleness와 scalability 문제를 줄이는 방향입니다. OpenAI는 compute requirement를 약 5배 줄여 Free 사용자까지 확장할 수 있게 됐고, Plus/Pro memory capacity도 늘릴 수 있다고 밝혔습니다.

### 개발자에게 의미

많은 개인화 AI 제품은 memory를 단순 저장소처럼 다룹니다. 사용자 profile table, preference JSON, vector store summary 정도로 시작합니다. 하지만 실제로는 다음 문제가 빠르게 생깁니다.

- 사용자의 선호가 바뀌었는데 오래된 선호가 계속 적용됩니다.
- 여행, 일정, 프로젝트처럼 시간에 민감한 memory가 만료되지 않습니다.
- 사용자가 농담처럼 말한 내용이 durable preference로 저장됩니다.
- 여러 project context가 섞여 엉뚱한 답변을 만듭니다.
- 개인 memory와 조직 knowledge가 뒤섞입니다.
- 사용자가 삭제한 memory가 retrieval cache나 summary에 남습니다.

Dreaming이 보여 주는 핵심은 memory가 storage가 아니라 lifecycle이라는 점입니다. 좋은 memory system은 기억을 만들고, 합치고, 압축하고, 오래된 것을 낮은 우선순위로 밀고, 충돌을 해결하고, 사용자가 검토/수정/삭제할 수 있게 해야 합니다.

개발자가 설계해야 할 memory schema는 최소한 다음을 포함해야 합니다.

- memory type: preference, fact, project, relationship, instruction, constraint, event
- scope: global, project, workspace, channel, conversation
- confidence: explicit, inferred, repeated behavior, imported source
- created_at / updated_at / last_confirmed_at
- expiry 또는 review_after
- sensitivity level
- source pointer
- conflict group
- user visibility와 editability

### 운영 포인트

memory 기능을 운영할 때 봐야 할 지표는 단순 사용량이 아닙니다.

1. **memory helpfulness rate:** memory 사용이 답변 만족도를 높였는가?
2. **stale memory incident:** 오래된 memory 때문에 틀린 추천을 했는가?
3. **unwanted personalization:** 사용자가 원하지 않는 개인화가 발생했는가?
4. **correction absorption:** 사용자의 정정이 다음 답변에 반영됐는가?
5. **delete propagation:** memory 삭제가 summary, retrieval, cache에 모두 반영됐는가?
6. **cross-scope leakage:** 개인/조직/project memory가 섞이지 않았는가?
7. **freshness eval:** 시간 흐름이 중요한 질문에서 최신성을 유지했는가?

assistant가 오래 도와줄수록 memory는 강력한 차별점이 됩니다. 동시에 privacy, trust, control 없이는 가장 위험한 기능이 됩니다.

---

## 7) GPT-Rosalind: 전문 도메인 AI는 provenance와 expert review가 제품의 일부다

**공식 발표:** 2026-06-03  
**공식 출처:** https://openai.com/index/introducing-new-capabilities-to-gpt-rosalind/

OpenAI는 GPT-Rosalind update를 발표하며 GPT-5.5의 agentic coding과 tool-use capability를 life sciences domain intelligence와 결합했다고 설명했습니다. LifeSciBench는 evidence handling, analysis, design and optimization, scientific reasoning, validation and operations, translation and communication 같은 workflow 영역을 평가합니다. MedChemBench, GeneBench, LabWorkBench도 함께 소개됐습니다. Codex plugin으로 Life Sciences Research와 Life Sciences NGS Analysis를 제공해 sourced evidence retrieval, biological interpretation, bioinformatics execution, artifact provenance를 같은 workspace에서 다룹니다.

GPT-Rosalind는 eligible organizations globally에 research preview로 제공되며, legitimate scientific research, clear public benefit, strong governance and safety oversight, controlled access, enterprise-grade security를 요구하는 trusted-access deployment 구조를 사용합니다.

### 개발자에게 의미

전문 도메인 AI의 기준은 일반 챗봇과 다릅니다. 생명과학, 의료, 법률, 금융, 보안처럼 결과의 위험과 가치가 큰 영역에서는 "답이 그럴듯하다"로는 부족합니다. 중요한 것은 결과가 어떻게 만들어졌는지입니다.

필요한 구성요소는 다음과 같습니다.

- source evidence와 citation
- tool input/output/version/parameter
- intermediate artifact
- domain-specific benchmark
- expert review workflow
- access control과 목적 기반 접근 제한
- audit envelope
- reproducibility
- refusal/escalation policy

GPT-Rosalind의 발표가 흥미로운 이유는 model update와 workflow plugin이 함께 나왔다는 점입니다. 이는 "모델이 답한다"에서 "agent가 연구 workflow를 실행하고, evidence와 artifact를 남기며, 전문가가 검토한다"로 이동하는 신호입니다.

### 운영 포인트

민감 도메인 AI를 운영할 때는 다음 질문이 필요합니다.

1. 이 agent의 결과는 의사결정용인가, 검토용 초안인가?
2. expert approval 없이는 실행되면 안 되는 단계가 무엇인가?
3. artifact provenance가 충분히 남는가?
4. benchmark가 실제 업무 난이도와 맞는가?
5. dual-use나 misuse 가능 요청을 어떻게 탐지하는가?
6. 외부 evidence와 내부 데이터를 어떻게 분리하는가?
7. model/tool version 변경 시 기존 결과 재현성이 유지되는가?
8. 안전상 거절해야 하는 요청은 어떤 escalation path로 가는가?

전문직 AI의 경쟁력은 모델 성능표보다 운영 증거에서 나옵니다.

---

## 8) Google Gemma 4 12B: 로컬 agent는 privacy와 latency를 제품 요구사항으로 만든다

**공식 발표:** 2026-06-03  
**공식 출처:** https://developers.googleblog.com/en/gemma-4-12b-the-developer-guide/  
**관련 공식 출처:** https://developers.googleblog.com/en/all-the-news-from-the-google-io-2026-developer-keynote/

Google은 Gemma 4 12B developer guide에서 dense multimodal model과 unified encoder-free architecture를 설명했습니다. 전통적인 multimodal model이 별도 vision/audio encoder를 거치는 것과 달리, Gemma 4 12B는 vision embedder와 audio wave projection을 통해 multimodal data를 LLM backbone으로 직접 연결합니다. Google은 16GB VRAM 또는 unified memory급 노트북에서 로컬 실행 가능한 developer-friendly size를 강조했고, LiteRT-LM `serve` command로 OpenAI-compatible local API server를 제공한다고 설명했습니다.

Google I/O 2026 developer keynote 정리에서는 Antigravity 2.0, Antigravity CLI, Google AI Studio integrations, Managed Agents in Gemini API, Android CLI/skills, Android Bench, Migration agent, WebMCP, Chrome DevTools for agents, HTML-in-Canvas API도 함께 제시됐습니다.

### 개발자에게 의미

로컬 모델은 "클라우드 모델보다 성능이 낮은 대체재"로만 보면 안 됩니다. 로컬 실행은 제품 요구사항을 바꿉니다.

- **privacy:** 민감한 파일, 음성, 화면, 코드가 외부로 나가지 않아야 하는 환경
- **latency:** voice edit, local UI automation, image inspection처럼 즉시 반응이 필요한 기능
- **offline:** 현장 작업, 보안망, 제한된 네트워크 환경
- **cost predictability:** cloud token cost를 피하고 device compute를 활용하는 구조
- **hybrid routing:** 쉬운 작업은 local, 어려운 작업은 cloud로 보내는 routing

Gemma 4 12B와 LiteRT-LM의 OpenAI-compatible server는 개발자에게 중요한 편의성을 줍니다. 이미 OpenAI-compatible client를 쓰는 editor, CLI, agent harness가 local endpoint를 대상으로 동작할 수 있기 때문입니다. 이는 local-first agent 실험 비용을 낮춥니다.

### 운영 포인트

로컬 agent를 production에 넣을 때는 cloud agent와 다른 운영 기준이 필요합니다.

1. device capability detection: RAM, GPU, NPU, battery, thermal 상태 확인
2. model update policy: local model version rollout과 rollback
3. data boundary: local 처리와 cloud fallback의 기준
4. prompt/tool compatibility: cloud/local model 간 tool calling 차이 처리
5. eval split: local model이 맡을 수 있는 task와 맡기면 안 되는 task 구분
6. security: local file access, screen access, microphone access 권한 통제
7. observability: 민감 데이터를 유출하지 않으면서 품질과 failure를 측정

클라우드 frontier model과 로컬 multimodal model은 경쟁 관계가 아니라 역할 분담 관계가 될 가능성이 큽니다.

---

## 9) AWS What’s Next: agent는 cloud governance 안으로 들어간다

**공식 출처:** https://aws.amazon.com/blogs/aws/top-announcements-of-the-whats-next-with-aws-2026/

AWS News Blog의 What’s Next with AWS 2026 정리에 따르면 Amazon Quick은 업무용 AI assistant로 desktop app, Free/Plus pricing, visual asset generation, Google Workspace/Zoom/Airtable/Dropbox/Microsoft Teams integrations, natural language custom app creation preview를 확장했습니다. Amazon Connect는 Decisions, Talent, Customer, Health로 확장되어 supply chain, hiring, customer experience, healthcare workflow에 agentic AI solution을 제공합니다. AWS와 OpenAI는 OpenAI models on Amazon Bedrock, Codex on Amazon Bedrock, Amazon Bedrock Managed Agents powered by OpenAI를 limited preview로 소개했습니다.

### 개발자에게 의미

AWS 발표의 핵심은 기업 AI의 배포 경로입니다. 많은 기업은 이미 AWS IAM, CloudTrail, procurement, billing, VPC, compliance, data residency, vendor management 체계를 가지고 있습니다. 새로운 AI model이나 agent를 도입할 때 별도 계정, 별도 보안 모델, 별도 청구 체계가 생기면 adoption이 느려집니다.

OpenAI models와 Codex가 Bedrock에 들어가는 구조는 이 문제를 줄입니다. 기업은 frontier model을 쓰면서도 Bedrock API, AWS credential, AWS governance, AWS cost control을 유지할 수 있습니다. Managed Agents는 agent harness와 cloud runtime을 결합해 production-ready agent를 더 빠르게 만들려는 방향입니다.

### 운영 포인트

AWS 기반 agent 도입 시 핵심은 다음입니다.

- Bedrock model access policy와 IAM boundary
- CloudTrail 기반 agent action audit
- VPC/private connectivity 필요 여부
- data residency와 logging policy
- prompt, completion, tool output retention
- cost allocation tag와 budget alarm
- sandbox runtime isolation
- Bedrock Managed Agents와 기존 Step Functions/Lambda/EventBridge workflow의 책임 분리

AWS의 메시지는 명확합니다. agent가 업무를 하려면 기업 cloud control plane 안에서 신뢰, 비용, 감사, 배포가 관리되어야 합니다.

---

## 10) OpenAI Codex for every role: agent workbench는 개발자를 넘어선다

**공식 발표:** 2026-06-02  
**공식 출처:** https://openai.com/index/codex-for-every-role-tool-workflow/

OpenAI는 Codex가 주간 500만 명 이상에게 사용되고 있으며, non-developer가 전체 Codex 사용자의 약 20%이고 개발자보다 3배 이상 빠르게 성장한다고 밝혔습니다. 새 발표는 role-specific plugins, annotations, Sites를 중심으로 합니다. data analytics, creative production, sales, product design, public equity investing, investment banking plugin이 소개됐고, 62개 app과 110개 skill을 포함한다고 설명했습니다.

### 개발자에게 의미

Codex의 확장은 "coding agent"라는 이름이 오래가지 않을 수 있음을 보여 줍니다. 실제 조직의 업무는 code, document, dashboard, design, CRM, spreadsheet, presentation, web app이 섞여 있습니다. agent가 산출물을 만들려면 IDE만으로는 부족하고, role-specific tool bundle과 artifact review surface가 필요합니다.

제품 개발자가 준비해야 할 것은 다음입니다.

- app data를 agent가 이해할 수 있는 schema로 제공
- action API에 dry-run과 approval mode 제공
- artifact에 source link와 inline annotation 제공
- tool permission을 role과 workflow별로 제한
- reusable skill/instruction을 조직 단위로 관리
- generated artifact와 human edit history를 함께 보관

업무 agent의 UX는 chat response가 아니라 work object입니다. dashboard, report, campaign board, prototype, deal review, investment memo 같은 산출물을 사람이 수정하고 승인할 수 있어야 합니다.

### 운영 포인트

직무별 agent plugin을 도입할 때는 다음이 중요합니다.

1. 어떤 app connector가 어떤 데이터에 접근하는가?
2. agent가 생성한 산출물은 draft인가, published artifact인가?
3. 외부 발송과 내부 초안의 권한 경계가 있는가?
4. role plugin instruction을 누가 승인하고 갱신하는가?
5. 업무별 hallucination cost가 어떻게 다른가?
6. generated content의 brand/legal/compliance review가 필요한가?

Codex의 방향은 agent가 개발자 도구를 넘어 업무 생산 시스템으로 확장되고 있음을 보여 줍니다.

---

## 개발자에게 의미: 2026년 하반기 AI stack을 다시 그려야 한다

오늘 확인한 공식 발표를 종합하면 개발자가 당장 바꿔야 할 관점은 다섯 가지입니다.

### 1. Context는 product feature가 아니라 platform layer다

RAG를 붙였다고 context 문제가 해결되지 않습니다. 조직 데이터는 권한, 최신성, semantic structure, source reliability, user relationship, workflow state를 모두 포함합니다. Work IQ, Microsoft IQ, OpenAI memory, Google Antigravity, AWS Quick 모두 context를 핵심 layer로 다룹니다. 자체 제품을 만드는 팀도 context API를 별도 설계해야 합니다.

### 2. Agent action은 API call이 아니라 governed operation이다

agent가 email을 보내고, PR을 만들고, calendar를 수정하고, database migration을 준비한다면 이는 단순 API call이 아닙니다. 권한, 승인, audit, rollback, cost가 붙은 operation입니다. 따라서 tool call wrapper에는 policy check, dry-run, idempotency key, audit log, human approval hook이 필요합니다.

### 3. Eval은 launch 전 checklist가 아니라 운영 loop다

ASSERT, Foundry eval, GPT-Rosalind benchmark, GitHub agent validation 흐름은 모두 같은 방향입니다. agent는 한번 평가하고 끝나는 것이 아니라 production trace와 feedback을 다시 eval로 돌려야 합니다. 특히 multi-turn, tool-use, long-running task는 static benchmark로 부족합니다.

### 4. Cost는 token만 보면 안 된다

agent cost는 token, reasoning effort, context retrieval, tool calls, sandbox runtime, CI minute, cloud storage, human review time이 합쳐집니다. GitHub, Microsoft, AWS 모두 AI credit과 consumption model을 강화하고 있습니다. 개발자는 model routing, context compression, task budget, stop condition을 제품에 넣어야 합니다.

### 5. Local/cloud hybrid가 기본 선택지가 된다

Gemma 4 12B와 LiteRT-LM은 local multimodal agent를 실무 선택지로 만듭니다. 반대로 AWS Bedrock과 Microsoft Foundry는 enterprise cloud governance를 강화합니다. 앞으로 좋은 AI 제품은 local-only나 cloud-only가 아니라 task sensitivity, latency, cost, capability에 따라 routing하는 구조가 될 가능성이 큽니다.

---

## 운영 포인트: CTO와 플랫폼팀을 위한 체크리스트

AI agent를 조직에 넣는 팀은 다음 checklist를 기준으로 현재 architecture를 점검해야 합니다.

1. **Agent catalog**
   - 조직 안에 실행 중인 agent 목록이 있는가?
   - 각 agent의 owner, purpose, data access, tool access가 보이는가?

2. **Context governance**
   - agent가 쓰는 context source가 최신성과 권한을 반영하는가?
   - 개인 memory, 조직 knowledge, project context가 분리되어 있는가?

3. **Tool control**
   - 위험 action에 dry-run, approval, rollback이 있는가?
   - tool call 전후에 policy checkpoint가 있는가?

4. **Evaluation**
   - single-turn Q&A 외에 multi-turn workflow eval이 있는가?
   - production incident가 eval scenario로 되돌아가는가?

5. **Observability**
   - agent trace, source, tool input/output, cost, reviewer feedback이 남는가?
   - 민감정보를 보호하면서도 debugging할 수 있는가?

6. **Cost management**
   - agent별 budget과 spending limit이 있는가?
   - reasoning effort, context size, retry 횟수를 제한하는가?

7. **Security**
   - secret, PII, customer data, source code 접근 정책이 명확한가?
   - local agent, cloud agent, MCP server가 모두 inventory에 잡히는가?

8. **Human review**
   - 어떤 결과는 자동 실행 가능하고, 어떤 결과는 승인 필수인지 정했는가?
   - reviewer가 plan, diff, source, tool trace를 볼 수 있는가?

9. **Deployment**
   - agent instruction, tool manifest, policy, eval, model routing을 version control하는가?
   - rollback과 kill switch가 있는가?

10. **Memory**
    - memory lifecycle, expiry, delete propagation, user editability가 있는가?
    - stale memory와 cross-context leakage를 평가하는가?

이 checklist를 통과하지 못한 agent는 아직 production system이 아니라 실험입니다.

---

## 오늘의 결론

2026년 6월 7일의 AI Daily News는 단일 속보보다 방향성이 더 중요합니다. OpenAI는 memory와 domain workflow를 깊게 만들고 있습니다. Microsoft는 agent를 enterprise operating system으로 정리하고 있습니다. GitHub는 coding agent를 API worker로 만들고 있습니다. Google은 local multimodal agent의 실용성을 끌어올리고 있습니다. AWS는 agent와 frontier model을 기존 cloud governance 안으로 흡수하고 있습니다.

이 흐름의 공통점은 분명합니다.

**AI의 다음 경쟁력은 모델 성능표가 아니라 agent execution surface입니다.**

실무 개발자와 조직이 준비해야 할 것은 "어느 모델을 쓸까"에서 끝나지 않습니다. 어떤 context를 줄지, 어떤 tool을 허용할지, 어떤 memory를 유지할지, 어떤 policy로 막을지, 어떤 eval로 검증할지, 어떤 trace로 감사할지, 어떤 비용 한도 안에서 운영할지, 어떤 화면에서 사람이 검토할지까지 설계해야 합니다.

앞으로 좋은 AI 제품은 더 많은 기능을 가진 제품이 아니라 더 신뢰할 수 있는 실행 구조를 가진 제품이 될 것입니다.

---

## 소스 링크

- OpenAI News index: https://openai.com/news/
- OpenAI - Dreaming: Better memory for a more helpful ChatGPT: https://openai.com/index/chatgpt-memory-dreaming/
- OpenAI - Introducing new capabilities to GPT-Rosalind: https://openai.com/index/introducing-new-capabilities-to-gpt-rosalind/
- OpenAI - Codex for every role, tool, and workflow: https://openai.com/index/codex-for-every-role-tool-workflow/
- OpenAI - Advancing youth safety and opportunity through global leadership: https://openai.com/index/advancing-youth-safety-and-opportunity-through-global-leadership/
- Microsoft - Microsoft Build 2026: Be yourself at work: https://blogs.microsoft.com/blog/2026/06/02/microsoft-build-2026-be-yourself-at-work/
- Microsoft - AI alone won’t change your business. The system running it will.: https://blogs.microsoft.com/blog/2026/06/02/ai-alone-wont-change-your-business-the-system-running-it-will/
- Microsoft 365 Blog - Announcing the new Work IQ APIs: https://www.microsoft.com/en-us/microsoft-365/blog/2026/06/02/announcing-the-new-work-iq-apis/
- Microsoft Security Blog - Securing code, agents, and models across the development lifecycle: https://www.microsoft.com/en-us/security/blog/2026/06/02/microsoft-build-2026-securing-code-agents-and-models-across-the-development-lifecycle/
- Microsoft Foundry Blog - Build agents you can trust across any framework with open evals and a control standard: https://devblogs.microsoft.com/foundry/build-2026-open-trust-stack-ai-agents/
- GitHub Changelog - Agent tasks REST API now available for Copilot Pro, Pro+, and Max: https://github.blog/changelog/2026-06-04-agent-tasks-rest-api-now-available-for-copilot-pro-pro-and-max/
- GitHub Changelog - Start Copilot cloud agent tasks via the REST API: https://github.blog/changelog/2026-05-13-start-copilot-cloud-agent-tasks-via-the-rest-api/
- GitHub Changelog - GitHub Copilot in Visual Studio Code, May releases: https://github.blog/changelog/2026-06-04-github-copilot-in-visual-studio-code-may-releases/
- Google for Developers Blog index: https://developers.googleblog.com/en/
- Google Developers - Gemma 4 12B: The Developer Guide: https://developers.googleblog.com/en/gemma-4-12b-the-developer-guide/
- Google Developers - All the news from the Google I/O 2026 Developer keynote: https://developers.googleblog.com/en/all-the-news-from-the-google-io-2026-developer-keynote/
- AWS News Blog - Top announcements of the What’s Next with AWS, 2026: https://aws.amazon.com/blogs/aws/top-announcements-of-the-whats-next-with-aws-2026/
- Anthropic News index: https://www.anthropic.com/news
