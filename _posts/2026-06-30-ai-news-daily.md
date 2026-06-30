---
layout: post
title: "2026년 6월 30일 AI 뉴스: 에이전트 시대의 승부처는 모델이 아니라 운영 가능한 AI 시스템이다"
date: 2026-06-30 11:30:00 +0900
categories: [ai-daily-news]
tags: [ai, news, openai, gpt-5-6, codex, frontier, hp, broadcom, jalapeno, github, copilot, aws, bedrock-agentcore, mcp, microsoft, foundry-iq, google-cloud, bigquery, vpc-service-controls, siemens, agentic-ai, llmops, ai-governance, ai-security]
permalink: /ai-daily-news/2026/06/30/ai-news-daily.html
---

# 오늘의 AI Daily News

## 작성 기준

2026년 6월 30일 11:30 KST 기준으로 공개 공식 출처만 확인해 작성했습니다. `web_search`는 Gateway의 Gemini API 키 부재로 실패했으므로, 작업 지시의 예외 규칙에 따라 OpenAI News, GitHub Blog, AWS Machine Learning Blog, Microsoft Azure 및 Foundry 공식 블로그, Google Cloud Blog의 공식 index와 개별 공식 발표 URL을 `web_fetch`로 직접 확인했습니다. 제3자 기사, 커뮤니티 해석, 소셜 미디어 추정, 비공식 벤치마크, 출처가 불명확한 루머는 근거로 사용하지 않았습니다.

오늘의 핵심은 단순합니다. **AI 경쟁의 중심이 "더 똑똑한 모델"에서 "실제로 운영 가능한 AI 시스템"으로 이동하고 있습니다.** 모델 성능은 여전히 중요합니다. 하지만 기업과 개발자가 매일 부딪히는 문제는 더 구체적입니다. 어떤 모델을 어떤 업무에 배정할 것인가. 에이전트가 어떤 문서와 데이터에 접근할 수 있는가. 도구 호출은 어떤 권한과 네트워크 경계 안에서 실행되는가. 비용은 누가 보고 통제하는가. 장시간 작업의 중간 상태와 실패는 어떻게 추적하는가. 사람이 어느 지점에서 검토하고 승인할 것인가. 결과물이 틀렸을 때 어디까지 되돌릴 수 있는가.

OpenAI의 최근 공식 발표들은 이 전환을 한꺼번에 보여 줍니다. HP의 Frontier 전략적 파트너십 확대는 AI가 파일럿을 넘어 전사 운영 모델로 들어가는 장면입니다. GPT-5.6 Sol preview는 frontier model 출시가 단순한 성능 발표가 아니라 안전장치, 가격, 캐시, 접근 제어, serving capacity, preview policy가 묶인 release operation이라는 점을 드러냅니다. Codex 사용 분석은 에이전트 업무 단위가 짧은 질의응답에서 수십 분, 수시간, 때로는 하루 이상의 위임 작업으로 이동했음을 보여 줍니다. Broadcom과의 Jalapeno inference chip 발표는 모델 회사가 silicon, kernel, networking, scheduler, product experience까지 연결하는 full-stack AI platform으로 움직이고 있음을 상징합니다.

클라우드와 개발 플랫폼도 같은 방향입니다. AWS는 Bedrock AgentCore Web Search를 통해 에이전트가 최신 웹 정보를 MCP-compatible tool로 가져오는 구조를 공식화했습니다. Microsoft는 Foundry IQ와 Microsoft IQ를 통해 enterprise knowledge, web knowledge, MCP server, serverless retrieval, permissions sync를 하나의 agent knowledge layer로 묶으려 합니다. Google Cloud는 BigQuery AI.AGG로 데이터베이스 안의 비정형·멀티모달 데이터를 SQL 한 줄로 요약·합성하는 흐름을 보여 주고, VPC Service Controls의 agentic AI 보안 업데이트로 에이전트를 first-class identity와 network perimeter 안에 넣고 있습니다. Siemens Knowledge Fabric 사례는 거대한 legacy codebase를 graph, semantic search, full-text search, task decomposition, human-in-the-loop agent workflow로 다루는 실제 산업 적용을 보여 줍니다.

이 흐름을 관통하는 결론은 분명합니다. 앞으로 AI 도입의 성패는 "어떤 모델을 샀는가"보다 **모델, 컨텍스트, 도구, 권한, 관측, 평가, 비용, 보안, 사람의 검토를 하나의 운영 체계로 묶었는가**에 달려 있습니다.

---

## 한눈에 보는 Top News

1. **OpenAI + HP: Frontier가 파일럿 AI를 전사 운영 모델로 확장하는 connective layer가 됐다**
   - 공식 발표일: 2026-06-28
   - 핵심: HP는 OpenAI Frontier 전략적 파트너십을 확대해 partner portal, customer support, device telemetry, security, software development, employee productivity로 AI 적용 범위를 넓히고 있습니다. OpenAI는 Frontier를 access, context, deployment, evaluation을 연결하는 통합 운영 계층으로 설명했습니다.
   - 개발자 의미: AI 프로젝트는 더 이상 "챗봇 하나 붙이기"가 아닙니다. 에이전트별 권한, 데이터 접근, 평가 기준, 배포 패턴, 감사 가능성을 처음부터 설계해야 합니다.

2. **GPT-5.6 Sol preview: frontier model release는 성능·안전·가격·캐시·serving의 묶음이다**
   - 공식 발표일: 2026-06-26
   - 핵심: OpenAI는 GPT-5.6 family를 Sol, Terra, Luna tier로 공개하고, 제한 preview, cyber/biology safeguard, automated red teaming, account-level review, cache pricing, Cerebras serving 계획을 함께 발표했습니다.
   - 개발자 의미: 모델 upgrade는 benchmark 숫자만 비교하는 일이 아닙니다. task routing, cache breakpoint, fallback model, 안전 검토 지연, preview 의존성, budget ceiling을 함께 관리해야 합니다.

3. **Codex 사용 분석: 생산성 단위가 "대화 수"에서 "위임 가능한 작업량"으로 바뀌고 있다**
   - 공식 발표일: 2026-06-25
   - 핵심: OpenAI는 2026년 5월 기준 sampled individual user의 80.6%가 30분 이상 인간 작업량으로 추정되는 Codex request를 한 적이 있고, 70.2%는 1시간 이상, 25.6%는 8시간 이상 작업에 해당하는 request를 한 적이 있다고 설명했습니다.
   - 개발자 의미: AI productivity 지표는 prompt 수나 completion 수가 아니라 delegated work horizon, review burden, acceptance rate, merge quality, cross-functional task expansion으로 이동합니다.

4. **OpenAI + Broadcom Jalapeno: AI 제품 전략이 silicon과 networking까지 내려갔다**
   - 공식 발표일: 2026-06-24
   - 핵심: Jalapeno는 OpenAI가 LLM inference에 맞춰 설계한 first Intelligence Processor입니다. OpenAI는 model roadmap, kernel, serving system, product need를 반영했고, Broadcom과 Celestica가 implementation, board, rack, networking, production을 담당합니다.
   - 개발자 의미: agent product의 품질은 모델 API 선택만으로 결정되지 않습니다. token latency, cache hit, tool call count, scheduler, memory movement, power efficiency가 사용자 경험과 unit economics를 좌우합니다.

5. **AWS Bedrock AgentCore Web Search: 최신 웹 정보가 managed MCP tool이 됐다**
   - 공식 발표일: 공식 AWS Machine Learning Blog 확인
   - 핵심: Web Search on Amazon Bedrock AgentCore는 generally available 상태의 fully managed, MCP-compatible web search capability입니다. AgentCore Gateway에 managed target 또는 connector로 연결하고, agents는 표준 `tools/list`와 tool invocation 흐름으로 사용할 수 있습니다.
   - 개발자 의미: RAG index만으로는 최신 정보 문제를 해결할 수 없습니다. 하지만 web search tool을 붙이면 query privacy, source freshness, result parsing, snippet quality, audit trail, data retention을 함께 설계해야 합니다.

6. **Microsoft Foundry IQ: enterprise knowledge layer가 MCP server와 serverless retrieval로 제품화되고 있다**
   - 공식 발표일: 2026-06-02
   - 핵심: Foundry IQ는 Work IQ, Fabric IQ, File Search, Azure SQL, MCP server, Web IQ, security controls, serverless retrieval을 통해 기업 내부·외부 지식을 agent context로 묶는 방향을 제시했습니다.
   - 개발자 의미: agent 품질의 병목은 model prompt보다 knowledge infrastructure입니다. ingestion, permission sync, retrieval quality, token cost, network isolation, sensitivity label governance가 production agent의 기본 요건이 됩니다.

7. **Microsoft의 agentic enterprise system: build, contextualize, run, govern, improve가 하나의 loop로 묶인다**
   - 공식 발표일: 2026-06-02
   - 핵심: Microsoft는 AI alone이 아니라 AI를 운영하는 system이 기업 변화를 만든다고 설명하며 GitHub, Microsoft IQ, Foundry, Agent 365, Entra, Purview, Defender를 하나의 agent platform 관점으로 제시했습니다.
   - 개발자 의미: agent는 코드로 끝나지 않습니다. source, evals, observability assets, context grounding, model routing, tool execution, policy rail, feedback loop가 모두 versioned lifecycle에 들어가야 합니다.

8. **Google Cloud BigQuery AI.AGG: 데이터베이스 안에서 비정형·멀티모달 데이터를 집계하는 AI 함수가 등장했다**
   - 공식 Google Cloud Blog 확인
   - 핵심: AI.AGG는 SQL에서 자연어 instruction으로 수백만 행의 log, document, image reference를 요약·합성할 수 있는 preview function입니다. multi-level aggregation으로 context window 문제를 완화하고, structured output은 prompt로 요청할 수 있습니다.
   - 개발자 의미: AI 분석이 애플리케이션 계층 밖으로 나와 data warehouse 안으로 들어가고 있습니다. 다만 nondeterminism, token usage, row-level error, NULL handling, JSON validity, model endpoint control을 운영해야 합니다.

9. **Google Cloud VPC Service Controls: agent identity와 MCP attribute가 보안 perimeter의 조건이 됐다**
   - 공식 Google Cloud Blog 확인
   - 핵심: VPC Service Controls는 agentic identities를 ingress/egress rule에 넣고, MCP attributes인 `mcp.toolName`, `mcp.method`, `mcp.tool.isReadOnly`를 조건으로 접근을 제어할 수 있게 했습니다. Gemini Enterprise Agent Platform과도 native integration을 제공합니다.
   - 개발자 의미: 에이전트 보안은 IAM만으로 충분하지 않습니다. prompt injection이나 tool misuse가 발생해도 외부 destination으로 data exfiltration이 되지 않도록 network-level perimeter를 함께 설계해야 합니다.

10. **Siemens + Google Cloud Knowledge Fabric: legacy modernization은 graph 기반 agent workflow로 간다**
    - 공식 Google Cloud Blog 확인
    - 핵심: Siemens와 Google Cloud는 Spanner Graph, ADK, Gemini API, Agent Platform, Gemini CLI, Claude Code를 결합해 code, Jira ticket, Confluence page, scanned PDF manual을 Knowledge Fabric으로 연결했습니다.
    - 개발자 의미: 대형 codebase modernization은 "AI에게 refactor 시키기"가 아닙니다. code graph, requirement traceability, architecture impact analysis, task decomposition, human checkpoint가 있어야 production-grade 결과가 나옵니다.

---

## 오늘의 큰 그림: AI stack이 다섯 층으로 재편되고 있다

2026년 6월 말의 AI 발표를 한 줄로 묶으면 "에이전트의 산업화"입니다. 여기서 산업화란 단순히 사용자가 많아졌다는 뜻이 아닙니다. 개별 데모와 실험이 production system으로 바뀌면서, 이전에는 흐릿하게 넘어갔던 문제가 제품의 핵심 기능으로 올라왔다는 뜻입니다.

첫 번째 층은 **model and reasoning layer**입니다. GPT-5.6 Sol, Terra, Luna처럼 capability tier가 분리되고, reasoning effort와 ultra mode처럼 장시간 reasoning과 subagent orchestration이 모델 제품의 일부가 됩니다. 개발자는 "가장 좋은 모델"을 고르는 대신 업무별로 어떤 tier가 필요한지, 언제 escalation할지, 실패하면 어디로 fallback할지 정해야 합니다.

두 번째 층은 **context and knowledge layer**입니다. Microsoft Foundry IQ, Google Cloud Knowledge Fabric, BigQuery AI.AGG, AWS Web Search on AgentCore가 모두 이 층에 해당합니다. AI가 답하려면 training data만으로는 부족합니다. 조직의 문서, 코드, ticket, telemetry, log, SQL table, image, web result, business ontology가 agent context로 들어와야 합니다. 문제는 단순한 연결이 아니라 permission-aware retrieval, freshness, ranking, source traceability, cost control입니다.

세 번째 층은 **tool and action layer**입니다. MCP가 반복해서 등장하는 이유가 여기에 있습니다. 에이전트는 검색하고, 파일을 읽고, Jira를 조회하고, PR을 만들고, cloud resource를 조사하고, email을 보내거나 막아야 합니다. 이때 tool은 단순 API wrapper가 아니라 policy-enforced action surface입니다. Google Cloud가 MCP attributes로 `readOnly` 여부와 tool name을 정책 조건에 넣은 것은 이 층이 보안의 중심이 되고 있음을 보여 줍니다.

네 번째 층은 **governance and observability layer**입니다. OpenAI Frontier의 evaluation, GPT-5.6 safeguard stack, Microsoft Agent 365와 Purview, Google VPC-SC, Foundry IQ security updates, GitHub Copilot session visibility는 모두 이 층의 신호입니다. 에이전트가 길게 일할수록 로그, trace, cost, permission, approval, result quality, rollback이 중요해집니다. "AI가 한 일"을 사람이 나중에 이해할 수 없으면 production에 넣을 수 없습니다.

다섯 번째 층은 **execution surface**입니다. 사용자는 AI 콘솔에만 있지 않습니다. GitHub, VS Code, CLI, mobile, Jira, Slack, Azure Portal, BigQuery SQL editor, internal partner portal, customer support console에서 에이전트를 부르고 확인합니다. HP와 OpenAI의 partner/customer workflow, GitHub Copilot remote session, Microsoft의 GitHub-Foundry-Agent 365 흐름, Siemens의 product owner interview와 user story agent는 모두 AI가 실제 업무 표면으로 들어가고 있음을 보여 줍니다.

따라서 앞으로 AI 제품을 만들 때 질문은 이렇게 바뀌어야 합니다.

- 이 기능은 어떤 model tier에서 실행되는가.
- context는 어디에서 오고, 누가 접근을 허용했는가.
- 도구 호출은 어떤 identity와 network boundary 안에서 수행되는가.
- 결과는 어떤 source, trace, evaluation으로 검증되는가.
- 비용은 어떤 단위로 측정되고 누가 책임지는가.
- 사람이 언제 개입하고, 승인하거나 되돌릴 수 있는가.
- 같은 작업이 반복될 때 지식과 평가 결과가 어떻게 개선되는가.

이 질문에 답하지 못하면 AI 기능은 데모에서는 멋져 보이지만 운영에서는 취약해집니다. 반대로 이 질문에 답할 수 있으면, 모델이 바뀌어도 시스템은 계속 성장할 수 있습니다.

---

## 1. OpenAI + HP: Frontier가 보여 주는 enterprise AI rollout의 현실

OpenAI가 공개한 HP Frontier partnership 글은 enterprise AI rollout을 이해하는 좋은 사례입니다. HP는 2026년 2월부터 OpenAI Frontier를 테스트했고, 초기 파일럿에서 engineering, security, productivity 영역의 성과를 확인했습니다. 한 engineer가 몇 주 동안 43개 project에서 122개 pull request를 처리했다는 사례, security team이 하루 안에 여러 software bug를 remediation했다는 사례, security-team capacity가 주당 약 82시간 풀렸다는 추정이 소개됐습니다.

하지만 이 발표의 핵심은 "AI가 일을 빨리 했다"가 아닙니다. 더 중요한 것은 HP가 다음 단계에서 무엇을 확장하려 하는지입니다. OpenAI는 HP의 확장 범위를 customer and partner-facing solutions, customer telemetry insights and reporting, employee productivity, software development로 설명했습니다. HP business의 80% 이상이 partner channel을 통해 흐르고, 100,000개 이상의 partner가 Partner Portal을 사용한다는 맥락도 제시했습니다. 즉, AI는 내부 개발팀의 생산성 도구가 아니라 partner ecosystem, customer support, device fleet telemetry, security operation, employee workflow를 연결하는 운영 계층으로 확장됩니다.

이때 필요한 것이 Frontier 같은 connective layer입니다. OpenAI는 Frontier가 "무엇이 running 중인지", "각 system이 어떤 context를 사용할 수 있는지", "어떤 action이 governed 되는지", "outcome이 어떻게 evaluated 되는지"를 연결한다고 설명했습니다. 이 문장은 enterprise AI의 핵심을 잘 보여 줍니다. 기업 AI는 모델 access만으로는 움직이지 않습니다. agent registry, context registry, permissioning, deployment control, evaluation, monitoring, usage tracking이 있어야 합니다.

HP 사례에서 특히 눈에 띄는 것은 device context입니다. HP의 Workforce Experience Platform은 device fleet을 관리하고 CIO에게 single pane of glass를 제공하는 표면입니다. OpenAI 발표는 Frontier를 통해 device telemetry, support knowledge, operational objects, schemas, runbooks를 AI reasoning context로 사용할 가능성을 언급합니다. 여기서 telemetry는 단순 dashboard 수치가 아닙니다. agent가 crash, Wi-Fi issue, app hang을 조사하고 grounded remediation을 제안하려면 telemetry, runbook, asset metadata, ticket history, known issue, policy가 하나의 context graph로 연결되어야 합니다.

개발자에게 이 사례가 주는 교훈은 세 가지입니다.

첫째, **AI rollout은 use case 목록이 아니라 control plane 설계**입니다. "고객지원 챗봇", "개발자 코파일럿", "보안 분석 agent"라는 목록을 만드는 것은 쉽습니다. 어려운 것은 각 agent가 어떤 identity를 갖고, 어떤 data boundary 안에서 움직이며, 어떤 tool을 호출할 수 있고, 어떤 조건에서 human approval이 필요한지 정하는 것입니다. 이 control plane이 없으면 파일럿은 빠르게 늘지만 production trust는 쌓이지 않습니다.

둘째, **context engineering이 prompt engineering보다 중요해집니다.** HP처럼 partner portal, device fleet, support knowledge, security scan, software delivery가 동시에 움직이면 prompt 하나로는 해결되지 않습니다. 데이터가 최신인지, schema가 일관적인지, agent가 어떤 source를 신뢰해야 하는지, 답변에 어떤 evidence를 붙일지, source conflict가 생기면 어떻게 처리할지가 중요합니다.

셋째, **security와 productivity는 분리되지 않습니다.** AI가 vulnerability remediation을 빠르게 돕는 만큼, 잘못된 remediation을 막는 review, permission, evaluation도 같이 필요합니다. agent가 "빨리 고쳤다"는 사실보다 "어떤 근거로 고쳤고, 어떤 test를 돌렸고, 어떤 사람이 승인했고, 어떤 배포 경로로 나갔는지"가 production에서는 더 중요합니다.

한국 기업이 이 흐름을 적용한다면, 먼저 AI agent catalog를 만들어야 합니다. agent name, owner, purpose, allowed data sources, allowed tools, approval policy, logging policy, cost center, evaluation suite, rollback path를 관리하는 표준이 필요합니다. 이것은 거창한 플랫폼부터 시작하라는 뜻이 아닙니다. 작은 팀이라도 `AGENTS.md`, issue template, tool permission matrix, eval checklist, audit log location을 정하면 같은 방향으로 갈 수 있습니다.

---

## 2. GPT-5.6 Sol: 모델 발표가 운영 설계 문서가 된 이유

OpenAI의 GPT-5.6 Sol preview는 모델 성능 발표처럼 보이지만, 실제로는 AI 운영 설계 문서에 가깝습니다. 발표는 Sol, Terra, Luna라는 세 tier를 제시합니다. Sol은 flagship model, Terra는 everyday work를 위한 balanced model, Luna는 빠르고 저렴한 model입니다. OpenAI는 Terra가 GPT-5.5와 경쟁력 있는 성능을 2배 낮은 비용으로 제공하고, Luna가 가장 낮은 비용의 강한 capability를 제공한다고 설명했습니다.

이 naming은 개발자에게 중요한 신호입니다. 앞으로 모델 선택은 "GPT-5.6을 쓸 것인가"가 아니라 "이 task에 Sol이 필요한가, Terra로 충분한가, Luna로 먼저 처리하고 실패 시 Sol로 올릴 것인가"의 문제가 됩니다. 즉, 모델은 단일 endpoint가 아니라 routing portfolio가 됩니다.

성능 측면에서 OpenAI는 coding, biology, cybersecurity를 강조했습니다. Terminal-Bench 2.1은 command-line workflow에서 planning, iteration, tool coordination을 평가합니다. GeneBench v1은 long-horizon genomics와 quantitative biology analysis를 평가합니다. ExploitBench와 ExploitGym은 long-horizon security task와 cyber capability를 다룹니다. 이 평가들은 frontier model이 짧은 답변보다 환경과 도구를 오가며 오래 일하는 agentic workflow로 이동하고 있음을 보여 줍니다.

하지만 더 중요한 것은 safety와 release process입니다. OpenAI는 GPT-5.6 Sol을 limited preview로 시작한다고 밝혔고, U.S. government와의 engagement, trusted partner preview, broader availability 계획을 설명했습니다. 또한 model-level refusal, real-time cyber and biology misuse classifiers, generation pause, larger reasoning model review, account-level review, differentiated access, monitoring, enforcement, automated red teaming을 함께 공개했습니다. automated red teaming에는 700,000 A100-equivalent GPU hours 이상이 쓰였다고 설명했습니다.

이 발표가 개발자에게 주는 운영 포인트는 매우 구체적입니다.

첫째, **model routing은 제품 기능이 아니라 비용·품질·안전 정책입니다.** 예를 들어 customer support summary는 Luna로 시작하고, 법률 위험이 높은 계약 조항 분석은 Terra 또는 Sol로 올리며, 취약점 exploit 가능성을 다루는 request는 Sol이더라도 safety review를 통과해야 할 수 있습니다. 이 routing rule은 코드에 흩어져 있으면 안 됩니다. product policy, risk category, model tier, fallback path, logging requirement가 명시된 matrix로 관리해야 합니다.

둘째, **cache strategy가 비용 구조를 바꿉니다.** GPT-5.6은 explicit cache breakpoint와 30분 minimum cache life를 언급했고, cache write는 uncached input rate의 1.25배, cache read는 cached-input 90% discount가 적용된다고 설명했습니다. 긴 system prompt, repository instruction, security policy, HR policy, product catalog, legal template, codebase summary를 반복 사용하는 agent에서는 cache hit rate가 곧 margin입니다. prompt를 매번 새로 조립하는 대신 stable prefix와 volatile suffix를 나누고, cache breakpoint를 어디에 둘지 설계해야 합니다.

셋째, **safeguard latency를 UX에 반영해야 합니다.** OpenAI는 high-risk case에서 generation이 pause되고 larger reasoning model review가 들어갈 수 있다고 설명했습니다. 사용자는 이를 단순 "느림"으로 느낄 수 있습니다. 따라서 제품은 "안전 검토 중", "추가 검토가 필요해 응답이 지연됨", "이 요청은 정책상 human review가 필요함" 같은 상태를 제공해야 합니다. 특히 security, bio, finance, HR, legal workflow에서는 blocked/refused/delayed state를 명확히 보여 줘야 신뢰가 생깁니다.

넷째, **preview dependency를 production critical path에 바로 넣으면 위험합니다.** limited preview 모델은 접근 조건, policy, capacity, pricing, latency가 바뀔 수 있습니다. 따라서 preview model은 capability discovery와 eval suite 구축에 먼저 쓰고, production flow에는 fallback model과 deterministic guardrail을 둬야 합니다. preview model이 unavailable일 때 task queue가 어떻게 처리되는지, user-facing SLA가 어떻게 유지되는지 미리 정해야 합니다.

다섯째, **frontier model의 capability가 올라갈수록 dual-use workflow의 설계가 중요해집니다.** 보안 취약점 분석은 방어에도 필요하지만 공격에도 쓰일 수 있습니다. 모델이 취약점을 찾는 능력이 좋아질수록 request context, user role, target ownership, authorization evidence, allowed scope를 더 엄격히 확인해야 합니다. 단순 keyword filter로는 부족합니다. workflow 자체가 authorization-aware해야 합니다.

한국 SaaS나 사내 업무 시스템에 적용하면, GPT-5.6 같은 tiered model family는 다음과 같이 다뤄야 합니다. 일반 문서 요약은 low-cost tier, 복잡한 규정 해석은 high-reasoning tier, 개인정보 포함 문서는 private logging policy, 코드 변경은 sandbox와 test evidence, 보안 분석은 scope proof와 human approval을 요구합니다. 모델 tier는 UI에서 예쁜 dropdown으로 보여 주는 옵션이 아니라 risk and cost control의 결과여야 합니다.

---

## 3. Codex 사용 분석: AI productivity를 다시 정의해야 한다

OpenAI의 "How agents are transforming work"는 AI adoption을 보는 관점을 바꿉니다. OpenAI는 agentic AI가 knowledge work의 단위를 single interaction에서 delegated, long-horizon task로 바꾼다고 설명했습니다. Chatbot interaction은 짧고 self-contained한 경우가 많지만, agent는 minutes or hours 동안 tool calls, environment interaction, iteration을 수행할 수 있습니다.

수치가 흥미롭습니다. 2026년 5월 기준 sampled individual user의 80.6%가 인간 기준 30분 이상 걸리는 것으로 추정되는 Codex request를 한 번 이상 했고, 70.2%는 1시간 이상, 25.6%는 8시간 이상 request를 한 번 이상 했습니다. OpenAI 내부에서는 Legal, Finance, Recruiting 같은 non-technical department도 2026년 4월 전후 Codex가 primary AI tool이 됐다고 설명했습니다. 평균 OpenAI worker는 output token의 85% 이상을 Codex에서 생성하고, OpenAI 전체 weekly output token에서 Codex가 99.8%를 차지한다고도 밝혔습니다.

이 수치의 의미는 "Codex가 많이 쓰인다"보다 큽니다. AI productivity의 측정 단위가 바뀌고 있습니다. 과거에는 prompt 수, chat session 수, completion token 수, monthly active user가 중요한 지표였습니다. 이제는 "얼마나 긴 업무를 위임했는가", "그 업무가 실제 결과물로 채택됐는가", "검토 비용은 얼마나 들었는가", "비개발자가 기술 업무를 어느 정도 수행할 수 있게 됐는가"가 더 중요합니다.

개발 조직에서 특히 조심해야 할 지표가 있습니다.

- **Delegated work horizon:** agent에게 위임한 작업이 사람 기준 몇 분, 몇 시간, 며칠짜리였는가.
- **Agent runtime:** 실제 agent가 환경에서 몇 분 동안 실행됐고, 몇 번 tool call을 했는가.
- **Review burden:** 사람이 결과를 이해하고 검토하는 데 얼마나 걸렸는가.
- **Acceptance rate:** agent가 만든 PR, patch, 문서, 분석 결과가 실제로 merge, 배포, 승인됐는가.
- **Rework rate:** agent 결과를 사람이 얼마나 다시 고쳤는가.
- **Regression rate:** agent가 만든 변경이 test failure, incident, rollback을 늘렸는가.
- **Parallelism:** 한 사람이 동시에 몇 개의 agent task를 운영할 수 있고, 병목이 generation인지 review인지.
- **Cross-functional expansion:** non-developer가 자동화, data transformation, debugging, structured analysis 같은 기술 업무를 수행했는가.

이 지표를 함께 보지 않으면 착시가 생깁니다. agent runtime이 길다고 좋은 것은 아닙니다. 잘못된 방향으로 오래 돌았을 수도 있습니다. PR 수가 늘었다고 좋은 것도 아닙니다. 작은 PR이 많아졌거나 review quality가 낮아졌을 수도 있습니다. token 사용량이 늘었다고 생산성이 오른 것도 아닙니다. context를 비효율적으로 반복 주입했을 수 있습니다.

Codex류 agent를 조직에 도입할 때 가장 먼저 해야 할 일은 model choice가 아니라 **work definition**입니다. agent에게 맡길 수 있는 task와 맡기면 안 되는 task를 구분해야 합니다. 좋은 task는 acceptance criteria가 명확하고, test command가 있으며, 파일 범위가 제한되고, 실패 여부가 어느 정도 자동 검증 가능합니다. 나쁜 task는 요구사항이 모호하고, domain decision이 많고, stakeholder 합의가 필요하며, 결과 검증이 subjective한 작업입니다.

예를 들어 "login page를 예쁘게 만들어줘"는 나쁜 agent task입니다. 반면 "비밀번호 재설정 form에서 email validation error를 기존 design system의 FieldError 컴포넌트로 표시하고, `npm test -- reset-password`를 통과시켜라. API contract는 바꾸지 말고, 변경 파일은 reset password route와 test file로 제한한다"는 좋은 task입니다. agent는 모호한 의도보다 구조화된 constraint에서 훨씬 강합니다.

업무 관리 시스템도 바뀌어야 합니다. issue template에는 agent-readable field가 필요합니다. `Context`, `Goal`, `Non-goals`, `Allowed files`, `Test command`, `Acceptance criteria`, `Risk`, `Rollback`, `Human review point`를 넣으면 agent의 성공률이 올라갑니다. PR template에는 "AI-generated or AI-assisted", "commands run", "screenshots", "known limitations", "follow-up tasks" 같은 항목이 필요합니다.

Codex 분석이 보여 주는 미래는 "AI가 사람 일을 모두 대체한다"보다 더 복잡합니다. 실제로는 사람이 agent에게 일을 나누고, agent가 긴 작업을 수행하고, 사람이 결과를 검토하고, 다시 지시하고, 여러 agent를 병렬로 조정하는 방식입니다. 따라서 중요한 역량은 prompt trick이 아니라 task decomposition, review skill, system design, evaluation literacy입니다.

---

## 4. Jalapeno inference chip: agent 시대에는 infrastructure가 제품 경험이다

OpenAI와 Broadcom의 Jalapeno 발표는 AI infrastructure가 제품 전략의 뒤쪽이 아니라 앞쪽으로 나왔다는 신호입니다. OpenAI는 Jalapeno를 first Intelligence Processor로 설명했습니다. 이 accelerator는 LLM inference를 위해 blank-slate design으로 만들어졌고, OpenAI의 model roadmap, kernels, serving systems, product needs를 반영했습니다. Broadcom과 Celestica는 chip implementation, board, rack system integration, high-performance networking, scalable production을 맡습니다.

OpenAI는 Jalapeno가 production target frequency and power에서 ML workload를 lab에서 실행하고 있고, early testing에서 performance per watt가 current state-of-the-art보다 substantially better할 것이라고 설명했습니다. 또 architecture가 data movement를 줄이고 compute, memory, networking resource를 균형 있게 배치해 theoretical peak에 가까운 realized utilization을 목표로 한다고 밝혔습니다. multi-generation platform으로 2026년 말 초기 배포를 목표로 한다는 설명도 있습니다.

개발자에게 chip 발표가 왜 중요할까요. 대부분의 개발자는 chip을 직접 다루지 않습니다. 하지만 agent product를 만들면 infrastructure 특성이 곧 product behavior가 됩니다. 일반 chatbot은 한 번 답하면 끝날 수 있습니다. 반면 agent는 plan, search, read, edit, test, summarize, retry, reflect, ask permission, create PR 같은 step을 반복합니다. 하나의 사용자 요청이 수십 번의 model call과 tool call로 쪼개집니다. 이때 token latency와 inference cost가 조금만 달라져도 전체 UX와 margin이 크게 바뀝니다.

예를 들어 코드 수정 agent가 40번의 reasoning call을 하고, 각 call마다 repository context와 test output을 넣는다고 생각해 봅시다. 모델 응답이 평균 2초 느려지면 전체 작업은 몇 분 지연됩니다. input token cost가 높으면 긴 repository context를 매번 넣기 어렵습니다. cache가 잘 먹히지 않으면 동일한 policy와 code summary를 반복 비용으로 지불합니다. serving capacity가 흔들리면 장시간 agent task가 중간에 queue로 밀립니다. infrastructure는 추상화되어 있지만, 사용자는 그 결과를 직접 느낍니다.

Jalapeno 발표는 네 가지 실무 메시지를 줍니다.

첫째, **AI application architecture는 token economy 위에 세워집니다.** prompt length, context reuse, cache breakpoint, model tier, streaming, retry, tool call count가 모두 비용 구조입니다. 개발자는 "답이 맞는가"뿐 아니라 "몇 token으로 맞췄는가", "반복 호출에서 cache를 썼는가", "고비용 model을 필요한 순간에만 썼는가"를 봐야 합니다.

둘째, **agent workflow는 queueing과 checkpoint가 필요합니다.** 장시간 task는 network error, model rate limit, tool failure, test flakiness, permission wait, human review wait에 취약합니다. agent가 중간 상태를 저장하지 않으면 실패 시 처음부터 다시 시작해야 합니다. checkpointed planning, incremental diff, resumable session, idempotent tool call, partial result review가 필요합니다.

셋째, **serving speed가 interaction design을 바꿉니다.** OpenAI가 GPT-5.6 Sol on Cerebras에서 up to 750 tokens per second를 언급한 것도 같은 맥락입니다. 빠른 inference는 단지 답이 빨리 나오는 문제가 아닙니다. agent가 더 자주 self-check하고, 더 작은 단위로 사용자에게 progress를 보여 주고, interactive steering을 더 자연스럽게 만들 수 있습니다. 반대로 latency가 높으면 agent는 큰 덩어리로 오래 생각해야 하고, 사용자는 중간 제어가 어렵습니다.

넷째, **full-stack provider의 장점과 lock-in을 동시에 봐야 합니다.** OpenAI처럼 model, product, API, Codex, chip, serving stack을 같이 최적화하면 성능과 비용에서 강한 이점이 생깁니다. 하지만 기업 입장에서는 provider-specific cache behavior, safety policy, preview access, model naming, tool runtime에 의존하게 됩니다. multi-provider abstraction과 provider-specific optimization 사이의 균형을 잡아야 합니다.

결국 Jalapeno는 hardware news이지만, 개발자에게는 product design news입니다. AI 기능을 잘 만들려면 UI, prompt, model만 보지 말고 serving behavior까지 고려해야 합니다. 특히 장시간 agent, multi-agent workflow, codebase analysis, document ingestion, analytics synthesis를 만드는 팀은 token budget, latency budget, failure budget을 product requirement로 다뤄야 합니다.

---

## 5. AWS Bedrock AgentCore Web Search: RAG의 빈칸을 managed web search가 채운다

AWS의 Web Search on Amazon Bedrock AgentCore 발표는 agent knowledge의 중요한 빈칸을 다룹니다. AI agent가 training data만 의존하면 최신 release, stock price, sports score, 방금 올라온 문서, 최근 취약점, 새 library version을 알 수 없습니다. 조직이 자체 RAG index를 만들어도, 외부 웹의 최신성까지 안정적으로 커버하기는 어렵습니다. AgentCore Web Search는 이 문제를 managed MCP-compatible web search capability로 해결하려 합니다.

공식 AWS 글에 따르면 Web Search on Amazon Bedrock AgentCore는 generally available이고, AgentCore Gateway에 managed target 또는 connector로 연결할 수 있습니다. agent는 standard `tools/list` call로 discover하고 다른 MCP tool처럼 invoke합니다. 별도 search API provisioning, outbound credential management, result parsing glue를 줄이는 방향입니다. Amazon이 직접 운영하는 purpose-built web index가 tens of billions of documents를 포함하고, continually refreshed되어 new content가 minutes 안에 반영될 수 있다고 설명합니다. query traffic이 AWS 안에 머무는 privacy model도 강조됐습니다.

이 발표의 핵심은 "검색 기능이 생겼다"가 아닙니다. **web search가 agent runtime의 first-class tool이 됐다**는 점입니다. 기존에는 개발자가 search API를 고르고, key를 관리하고, rate limit을 처리하고, HTML을 파싱하고, snippet을 정리하고, LLM prompt에 넣는 glue code를 직접 만들었습니다. 이제 클라우드 provider는 search를 MCP tool로 package하고, gateway, IAM/JWT inbound auth, privacy model, snippet extraction, freshness를 함께 제공합니다.

하지만 production에서는 새 문제가 생깁니다.

첫째, **web search result는 authoritative source가 아닙니다.** 검색 결과는 시작점일 뿐입니다. agent가 source를 열고, 공식 문서인지 확인하고, 날짜를 비교하고, 서로 다른 source 간 충돌을 처리해야 합니다. 특히 법률, 의료, 금융, 보안 정보는 search snippet만으로 답하면 위험합니다.

둘째, **query privacy를 설계해야 합니다.** AWS는 query가 AWS 밖으로 나가지 않는 privacy model을 강조하지만, 조직 내부 request를 그대로 web search query로 보내는 것은 여전히 민감할 수 있습니다. customer name, internal project codename, unreleased feature, vulnerability detail이 query에 들어가지 않도록 query rewriting과 redaction이 필요합니다.

셋째, **tool permission이 필요합니다.** 모든 agent가 web search를 자유롭게 쓰면 비용과 보안 문제가 생깁니다. 어떤 agent는 internal-only context만 써야 하고, 어떤 agent는 public docs만 확인할 수 있으며, 어떤 agent는 특정 domain allowlist 안에서만 검색해야 할 수 있습니다.

넷째, **freshness와 reproducibility가 충돌합니다.** web search는 최신 정보를 주지만, 같은 query가 내일 다른 결과를 줄 수 있습니다. production decision에 쓰인 답변은 "언제 어떤 source를 확인했는지" snapshot을 남겨야 합니다. source URL, fetchedAt, snippet, agent reasoning trace, final citation을 저장하지 않으면 나중에 audit이 어렵습니다.

다섯째, **RAG와 web search를 구분해야 합니다.** 내부 지식과 외부 웹은 trust model이 다릅니다. 내부 RAG는 permission-aware retrieval과 document lifecycle이 중요하고, web search는 freshness, source quality, query privacy가 중요합니다. 두 source를 같은 prompt에 섞을 때 "내부 정책이 외부 블로그보다 우선한다" 같은 precedence rule이 필요합니다.

실무 설계는 다음과 같이 잡을 수 있습니다. agent에는 `knowledge_sources`를 명시합니다. `internal_docs`, `codebase`, `ticket_system`, `public_web`, `vendor_docs`를 나누고, 각 source별 allow/deny, citation requirement, retention policy를 둡니다. web search tool은 default off로 두고, task가 freshness를 요구하거나 internal source가 부족할 때만 켭니다. query rewriting 단계에서 sensitive term을 제거하고, official domain을 우선합니다. final answer에는 source link와 확인 시각을 남깁니다.

AWS 발표는 RAG의 죽음을 말하지 않습니다. 오히려 RAG가 더 넓은 knowledge toolchain 안의 한 부분이 됐다는 뜻입니다. 내부 문서, 웹, SQL, object storage, code graph, telemetry가 모두 tool로 들어오는 시대에는 retrieval orchestration이 agent 품질의 핵심이 됩니다.

---

## 6. Microsoft Foundry IQ: enterprise knowledge layer의 제품화

Microsoft Foundry IQ 발표는 agent 개발자가 실제로 가장 많이 막히는 문제를 정면으로 다룹니다. agent logic은 어느 정도 만들 수 있지만, 그 agent가 신뢰할 수 있는 지식을 안정적으로 가져오게 하는 infrastructure가 어렵습니다. Foundry IQ는 documents, emails, meetings, operational data, live web 같은 enterprise knowledge를 agent context로 묶고, MCP server와 serverless retrieval로 expose하는 방향입니다.

공식 발표에서 눈에 띄는 항목은 많습니다. Foundry IQ Serverless는 preview로 제공되며 scale-to-zero pricing과 Developer tier를 언급합니다. New knowledge sources in preview에는 Work IQ, Fabric IQ, File Search, Azure SQL, MCP가 포함됩니다. Web IQ는 Foundry IQ에서 사용 가능하며 web, news, images, video, shopping sources를 LLM workflow에 맞게 제공합니다. Foundry IQ knowledge bases는 GA로 소개되며 SLA, compliance certifications, stable APIs, Foundry IQ MCP server, network isolation, document-level security, cross-source ranking, agentic retrieval을 강조합니다. Security updates에는 encryption, permissions sync, sensitivity-label governance, Purview labels, private connectivity가 포함됩니다.

이 발표는 agent 개발의 병목이 retrieval glue code로 이동했음을 보여 줍니다. prototype 단계에서는 PDF 몇 개를 vector DB에 넣고 질문하면 됩니다. production 단계에서는 전혀 다릅니다. 누가 어떤 문서를 볼 수 있는지, SharePoint permission 변경이 언제 반영되는지, sensitivity label이 agent response에 어떻게 적용되는지, external web result와 internal confidential document가 같은 답변에 섞일 때 어떤 rule이 적용되는지, agent가 MCP를 통해 지식을 가져갈 때 log와 audit은 어디에 남는지 정해야 합니다.

Foundry IQ가 중요한 이유는 세 가지입니다.

첫째, **knowledge base가 agent platform의 shared service가 됩니다.** 각 agent가 자기만의 vector DB를 만들면 ingestion, permission, chunking, evaluation, cost가 중복됩니다. Foundry IQ처럼 reusable knowledge base와 MCP server를 제공하면 여러 agent framework가 같은 knowledge layer를 사용할 수 있습니다. 발표는 Claude, ChatGPT, LangChain, Microsoft Agent Framework 같은 MCP-compatible host/client에서 접근 가능하다는 방향을 제시했습니다.

둘째, **enterprise context는 structured와 unstructured가 같이 필요합니다.** Work IQ는 emails, meetings, files, Teams messages 같은 조직 신호를 다루고, Fabric IQ는 ontology와 live data를 다룹니다. Azure SQL은 relational data를, File Search는 uploaded files를, Web IQ는 external context를 제공합니다. production agent는 문서 검색만으로는 부족합니다. "지난 회의에서 합의된 내용", "현재 고객 매출 데이터", "제품 ontology", "공식 웹 최신 정보"를 함께 봐야 합니다.

셋째, **retrieval quality도 운영 지표가 됩니다.** Microsoft는 agentic retrieval enhancements가 answer quality benchmark를 개선하고 single-shot RAG 대비 recall을 높였다고 설명했습니다. 이 말은 retrieval 자체가 model처럼 eval과 optimization 대상이 된다는 뜻입니다. chunking, ranking, query rewriting, multi-hop retrieval, token caching, effort tier, source blending을 측정해야 합니다.

실무 체크리스트는 다음과 같습니다.

- Knowledge source별 owner와 permission sync 책임자를 정합니다.
- 문서 ingestion pipeline에 layout-aware parsing, image enrichment, table extraction이 필요한지 확인합니다.
- agent가 source를 인용할 때 document-level permission을 다시 확인합니다.
- retrieval quality eval set을 만듭니다. 자주 묻는 질문, edge case, stale document conflict, permission-denied case를 포함합니다.
- MCP server로 knowledge를 expose할 때 allowed host, allowed agent, allowed tool call을 제한합니다.
- sensitivity label과 retention policy가 response generation 이후에도 유지되는지 확인합니다.
- serverless retrieval의 cold start, burst cost, index size limit, region support를 production SLA와 맞춥니다.

Foundry IQ 발표에서 가장 중요한 문장은 "agent logic은 준비됐지만 knowledge infrastructure가 어렵다"는 문제의식입니다. 많은 팀이 model prompt를 고치며 답변 품질을 개선하려 하지만, 실제 원인은 잘못된 source, 오래된 문서, permission mismatch, broken ingestion, poor ranking인 경우가 많습니다. AI product의 품질을 높이려면 prompt engineer보다 knowledge engineer와 platform engineer가 더 중요해지는 구간이 옵니다.

---

## 7. Microsoft의 agentic enterprise system: build, contextualize, run, govern, improve

Microsoft의 "AI alone won’t change your business. The system running it will." 발표는 오늘 흐름을 가장 직접적으로 표현합니다. Microsoft는 winning organization이 가장 많은 demo를 가진 곳이 아니라 AI를 governed, continuously improving system으로 바꾸는 곳이라고 설명했습니다. 또 transformation은 chatbot만으로 오지 않고, software delivery, support, finance, HR, operations에서 long-running work를 수행하는 teams of agents와 identity, context, policy, human oversight가 필요하다고 강조했습니다.

Microsoft가 제시한 구조는 build, contextualize, run, govern, improve입니다.

**Build in GitHub.** Agent는 production software처럼 lifecycle을 가져야 합니다. codebase, work item, agent skill, tool, eval, observability asset이 함께 versioned 되어야 합니다. 이 관점은 매우 중요합니다. agent를 prompt와 workflow 설정 파일로만 보면 운영이 어려워집니다. agent도 source, test, deploy, observe, improve의 software lifecycle 안에 있어야 합니다.

**Contextualize with Microsoft IQ.** 모델은 business context 없이 generalist일 뿐입니다. Microsoft는 Microsoft 365, core business systems, knowledge bases, website, Web IQ를 agent context로 연결하는 방향을 설명했습니다. context는 raw access가 아니라 organized, secured, surfaced knowledge여야 한다는 점도 강조했습니다.

**Run in Foundry.** agent runtime은 traditional application runtime과 다릅니다. agent는 reason, act, call tools, coordinate, adapt를 수행합니다. Foundry는 model collection, model router, open model performance, agent framework support, MCP tools/actions, evals/traces, continuous optimization을 제공하는 runtime으로 설명됐습니다.

**Govern with Agent 365.** agent가 수백, 수천 개가 되면 catalog, access visibility, behavior monitoring, policy enforcement가 필요합니다. Microsoft는 Agent 365, Entra, Purview, Defender를 governance surface로 제시했습니다. 중요한 것은 "어떤 agent가 무엇을 할 수 있는지"를 IT가 볼 수 있어야 한다는 점입니다.

**Improve continuously.** agent behavior, outcome, human feedback이 system으로 돌아가 안전하게 개선되어야 합니다. 이것은 단순 fine-tuning만 뜻하지 않습니다. model, workflow, retrieval, tool permission, prompt, eval, routing, UI를 반복적으로 개선하는 loop입니다.

이 구조는 AI 도입을 위한 좋은 reference architecture입니다. 작은 조직도 축소판을 만들 수 있습니다.

- Build: agent 정의 파일, tool list, eval case, release note를 git에 둡니다.
- Contextualize: internal docs, codebase, tickets, DB, web source를 source별로 분리합니다.
- Run: agent runtime을 queue, sandbox, permission gate, retry, checkpoint와 함께 운영합니다.
- Govern: agent registry, owner, allowed actions, cost, logs, review state를 관리합니다.
- Improve: failed task, rejected output, user correction, incident를 eval set과 prompt/tool update로 되돌립니다.

많은 기업은 AI 도입을 "어떤 vendor를 쓸지"로 시작합니다. 하지만 Microsoft 발표가 말하는 방향은 "어떤 운영 시스템을 만들지"입니다. vendor는 바뀔 수 있지만, build-context-run-govern-improve loop는 오래 남습니다.

---

## 8. Google BigQuery AI.AGG: AI가 데이터베이스 안으로 들어간다

Google Cloud의 BigQuery AI.AGG 발표는 AI 기능이 application layer 밖으로 나와 data warehouse 안으로 들어가는 흐름을 보여 줍니다. AI.AGG는 SQL 안에서 natural-language instruction을 사용해 수백만 행의 unstructured 또는 multimodal data를 summarize/synthesize할 수 있는 preview function입니다. 예시는 log analysis, product review feature request extraction, automated agent failure pattern analysis, product category discovery, image collection summarization을 포함합니다.

기존 SQL aggregation은 숫자, count, sum, avg, group by에 강합니다. 하지만 log message, stack trace, user review, support ticket, product description, image 같은 비정형 데이터는 사람이 직접 읽거나 외부 pipeline으로 보내야 했습니다. AI.AGG는 이런 데이터를 SQL query 안에서 LLM aggregation으로 처리하게 해 줍니다.

특히 중요한 부분은 best practices입니다. Google Cloud는 AI.AGG가 context window 문제를 해결하기 위해 input rows를 batch로 나누고, batch results를 다시 aggregate하는 multi-level aggregation 구조를 사용한다고 설명했습니다. 하지만 각 individual row가 context window보다 크면 skip될 수 있으므로 row size를 관리해야 합니다. multi-level aggregation 때문에 total input tokens가 raw input보다 많아질 수 있어 LIMIT나 pre-filtering으로 token을 줄이는 것이 best practice라고 설명했습니다. model endpoint를 명시할 수 있고, output은 string이며 JSON이나 Markdown formatting은 prompt로 요청할 수 있지만 database engine이 strict하게 enforce하지는 않습니다. NULL 처리도 중요합니다. STRUCT field 중 하나가 NULL이면 row가 NULL로 취급되어 skip될 수 있으므로 IFNULL 같은 처리가 필요합니다. error가 발생하면 partial result를 제공할 수 있고, failed row 수는 BigQuery job statistics에서 확인할 수 있습니다.

이 발표가 중요한 이유는 세 가지입니다.

첫째, **data analyst와 engineer의 AI 사용 표면이 SQL로 확장됩니다.** 별도 Python notebook이나 application API 없이 SQL query 안에서 unstructured data analysis를 수행할 수 있습니다. 이는 데이터 팀의 adoption을 빠르게 만들 수 있습니다.

둘째, **AI output이 analytics pipeline의 일부가 됩니다.** AI.AGG로 category를 발견하고, 그 결과를 AI.CLASSIFY에 넘겨 row-level label을 붙이고, 다시 group by와 AI summary를 결합할 수 있습니다. 즉 AI는 보고서 작성 도구가 아니라 data transformation pipeline의 component가 됩니다.

셋째, **비결정성과 governance 문제가 데이터베이스 운영으로 들어옵니다.** LLM은 같은 prompt에도 다른 결과를 줄 수 있습니다. structured output을 prompt로 요청해도 JSON validity가 보장되지 않을 수 있습니다. partial failure가 생길 수 있습니다. token cost가 query cost처럼 관리되어야 합니다. model endpoint를 명시하지 않으면 default model이 바뀔 수 있습니다. 따라서 AI SQL은 일반 SQL보다 더 많은 운영 discipline이 필요합니다.

실무 적용 시 다음 원칙을 추천합니다.

- AI.AGG를 production pipeline에 넣기 전 sample set과 expected output을 만든다.
- prompt에는 "모르면 모른다고 말하라", "증거가 없으면 추정하지 말라", "카테고리는 최대 N개", "JSON schema는 다음과 같다" 같은 제약을 둔다.
- input row size를 제한하고, long document는 pre-chunking한다.
- NULL field는 IFNULL로 처리해 silent skip을 막는다.
- model endpoint를 명시하고, region과 cost를 기록한다.
- output JSON은 후처리 validation을 통과한 것만 downstream table에 쓴다.
- query job statistics에서 token usage와 failed row를 모니터링한다.
- AI-generated label에는 confidence 또는 review state를 별도 column으로 둔다.

AI.AGG는 BI와 observability에도 의미가 큽니다. 예를 들어 대규모 system log에서 "사용자가 실제로 겪는 오류 유형", "agent가 반복 실패하는 시나리오", "negative review에서 가장 많이 나온 feature request"를 SQL로 바로 요약할 수 있습니다. 하지만 이 기능이 강력할수록 governance가 중요합니다. AI가 만든 category나 summary가 business decision에 쓰인다면, source table, query, model endpoint, prompt version, run time을 함께 저장해야 합니다.

---

## 9. Google VPC Service Controls: agent 보안은 IAM만으로 부족하다

Google Cloud의 VPC Service Controls agentic AI 보안 업데이트는 오늘 발표들 중 가장 실무적인 보안 신호입니다. Google Cloud는 autonomous AI agents가 tools와 datasets를 연결하기 때문에 network-level boundary가 필요하다고 설명했습니다. 특히 VPC Service Controls에 agentic workload를 위한 여러 기능이 추가됐습니다.

첫째, **agent identity in directional rules**입니다. agent를 first-class identity로 다루고, service perimeter ingress/egress rule에 agentic identity를 IAM principal로 넣을 수 있습니다. 개별 agent는 principal로, agent collection은 principalSet으로 관리할 수 있습니다. agent가 compromise되면 network perimeter에서 접근을 revoke할 수 있습니다.

둘째, **MCP attributes 기반 granular control**입니다. VPC Service Controls는 `mcp.toolName`, `mcp.method`, `mcp.tool.isReadOnly` 같은 MCP attribute를 조건으로 접근 정책을 적용할 수 있습니다. 예를 들어 Workspace MCP server에 read access는 허용하되 email sending은 명시적으로 deny할 수 있습니다.

셋째, **Gemini Enterprise Agent Platform integration**입니다. Agent Platform을 VPC-SC perimeter의 protected service로 포함하면 public internet access가 자동 차단되는 구조를 제공합니다.

이 발표가 중요한 이유는 AI agent의 위협 모델이 일반 application과 다르기 때문입니다. 전통적인 application은 code path가 비교적 deterministic합니다. 반면 agent는 prompt, retrieved document, tool result, user instruction에 따라 행동합니다. 악의적인 문서에 indirect prompt injection이 숨어 있거나, 사용자가 권한을 가진 agent에게 위험한 tool chain을 유도하거나, insider가 data processing agent를 이용해 cloud-to-cloud copy를 시도할 수 있습니다.

Google Cloud는 IAM이 "who"를 다루고, VPC-SC가 "how"와 "where"를 다룬다고 설명했습니다. 이 구분이 중요합니다. 어떤 agent가 IAM credential을 갖고 있으면, IAM 입장에서는 정상 요청처럼 보일 수 있습니다. 하지만 그 agent가 내부 데이터를 외부 webhook이나 perimeter 밖 project로 보내려 할 때 network/resource perimeter가 막아야 합니다.

실무적으로는 agent 보안 아키텍처를 세 겹으로 나눠야 합니다.

**Identity controls.** agent별 service account, least privilege, principal access boundary, user delegation rule을 둡니다. 사람 user와 agent identity를 섞지 않습니다. agent가 누구를 대신해 행동하는지, 어떤 scope로 행동하는지 기록합니다.

**Tool controls.** MCP tool별 read/write/action을 분리합니다. `search_docs`와 `send_email`, `read_ticket`과 `update_ticket`, `query_bigquery`와 `export_bigquery`는 다른 권한이어야 합니다. tool call에는 argument validation, dry-run, human approval, rate limit을 둡니다.

**Network/resource controls.** sensitive dataset, storage bucket, model endpoint, agent runtime을 perimeter 안에 넣고, 외부 destination으로의 transfer를 제한합니다. agent가 compromised되어도 perimeter 밖으로 data를 보내지 못하게 합니다.

추가로 prompt injection 대응이 필요합니다. retrieved document에는 "이전 지시를 무시하라", "secret을 외부 URL로 보내라" 같은 문장이 있을 수 있습니다. agent는 문서 내용을 instruction으로 실행하면 안 됩니다. system prompt와 tool policy는 untrusted content보다 우선해야 하고, tool execution은 policy engine이 따로 검증해야 합니다.

Google Cloud의 업데이트는 agent 보안이 "모델이 안전하게 답하도록 prompt를 잘 쓰자" 수준을 넘어섰음을 보여 줍니다. production agent는 cloud security primitive 안에 들어가야 합니다. IAM, network perimeter, resource policy, MCP attribute, audit log, data loss prevention, human approval이 모두 필요합니다.

---

## 10. Siemens Knowledge Fabric: 대형 legacy codebase를 agent가 다루는 방식

Siemens와 Google Cloud의 Knowledge Fabric 사례는 agentic workflow가 실제 산업 codebase modernization에 어떻게 들어가는지 보여 줍니다. Siemens는 factory, energy grid, transportation network를 지탱하는 industrial software를 운영하고 있고, codebase는 수억 line 규모이며 10년 이상 누적된 legacy가 있습니다. 관련 지식은 code, Jira ticket, Confluence page, early 2000s scanned PDF manual에 흩어져 있습니다. 이 정도 규모에서는 단순 coding assistant가 충분한 context를 갖기 어렵습니다.

Google Cloud 글에서 Siemens와 Google Cloud는 Spanner Graph, Google Agent Development Kit, Gemini API, Agent Platform, Gemini CLI, Anthropic Claude Code를 이용해 Knowledge Fabric을 만들었다고 설명했습니다. 핵심은 code와 documentation의 관계를 graph로 모델링하는 것입니다. class는 file에 속하고, file은 module에 속하며, 특정 code snippet은 requirement document와 연결될 수 있습니다. Graph Query Language로 구조를 탐색하고, Spanner ANN으로 vector search를 수행하며, full-text search와 결합해 precise context를 찾습니다.

이 사례에서 가장 중요한 개념은 "slicing the elephant"입니다. 거대한 "refactor this module" 요청을 agent에게 한 번에 던지지 않고, 작은 task로 나눕니다. Search agent는 code graph와 documentation을 탐색합니다. User story agent는 product owner를 인터뷰해 acceptance criteria가 있는 user story를 만듭니다. Architecture impact agent는 변경의 side effect를 분석합니다. Task breakdown agent는 작은 task로 나눕니다. Coding agent는 각 task를 구현합니다. 각 단계에 human in the loop가 있습니다.

이 구조는 AI coding의 현실적인 성공 패턴입니다. 많은 실패 사례는 "AI에게 큰 일을 한 번에 맡겼다"에서 시작됩니다. agent는 context가 부족한 상태에서 그럴듯한 코드를 만들고, 사람은 전체를 검토하기 어렵고, 결과는 production에 넣기 애매해집니다. Siemens 사례는 반대로 context graph, requirement traceability, impact analysis, task decomposition, human checkpoint를 먼저 만듭니다. coding은 마지막 단계입니다.

개발팀이 여기서 가져올 수 있는 패턴은 다음과 같습니다.

- 대형 codebase를 file text만으로 보지 말고 dependency graph, module boundary, ownership, requirement link로 표현합니다.
- user story와 acceptance criteria를 agent-readable하게 작성합니다.
- architecture impact analysis를 coding 전 단계로 분리합니다.
- 큰 migration은 task breakdown agent나 template으로 작은 PR 단위로 나눕니다.
- 각 task에는 relevant context bundle, allowed files, test command, rollback note를 붙입니다.
- human checkpoint를 시작, impact review, implementation review, release review에 둡니다.
- generated code는 traceable requirement와 test evidence 없이는 merge하지 않습니다.

특히 산업, 금융, HR, 의료, 공공 시스템처럼 lifecycle이 길고 compliance가 중요한 영역에서는 이 패턴이 필수에 가깝습니다. AI가 빠르게 코드를 만들 수 있다는 사실은 출발점일 뿐입니다. 실제 가치는 "왜 이 코드를 바꿔도 되는지", "어떤 요구사항을 만족하는지", "어떤 side effect가 예상되는지", "누가 승인했는지"를 trace할 수 있을 때 생깁니다.

---

## 11. GitHub Copilot remote sessions: agent 작업 표면이 desk 밖으로 확장된다

GitHub Blog의 "Take your local GitHub sessions anywhere"는 2026년 5월 발표지만, 오늘 AI 운영 흐름을 이해하는 데 중요한 보조 신호입니다. GitHub는 VS Code나 CLI에서 시작한 Copilot session을 github.com과 GitHub Mobile에서 이어서 보고 제어할 수 있는 remote control을 generally available로 소개했습니다. `/remote on`을 사용하면 CLI session을 web/mobile로 보내고, 진행 상황을 실시간으로 확인하며, follow-up instruction을 보내고, permission request를 approve/deny하고, PR review까지 이어갈 수 있습니다.

이 기능이 중요한 이유는 agent가 장시간 작업을 수행할수록 "agent가 지금 무엇을 하는지"를 여러 표면에서 볼 수 있어야 하기 때문입니다. developer가 책상 앞에 없어도 refactor agent가 어떤 file을 읽고, 어떤 command를 실행하고, 어떤 plan을 세우고, 어디서 막혔는지 확인할 수 있습니다. agent가 잘못된 방향으로 가면 중간에 course correction을 할 수 있습니다.

이것은 단순 mobile convenience가 아닙니다. agentic development의 control surface가 확장되는 것입니다. 앞으로 개발자는 IDE 하나에서만 agent를 쓰지 않습니다. CLI에서 시작하고, web에서 progress를 보고, mobile에서 permission을 승인하고, GitHub PR에서 diff를 review하고, issue tracker에서 stakeholder와 논의할 수 있습니다. 장시간 agent는 한 화면 안에 갇히지 않습니다.

운영 포인트는 다음과 같습니다.

- session visibility는 편의 기능이 아니라 audit surface입니다.
- permission request는 mobile에서 쉽게 approve할 수 있어도, 위험한 tool은 extra confirmation이 필요합니다.
- follow-up instruction은 session history와 final PR에 남아야 합니다.
- agent가 실행한 command와 file changes는 reviewer가 볼 수 있어야 합니다.
- private by default라는 원칙은 중요하지만, enterprise에서는 team visibility와 privacy의 균형을 정책으로 정해야 합니다.

이 흐름은 HP의 Frontier, Microsoft의 Agent 365, OpenAI Codex long-horizon work와 같은 방향입니다. agent가 길게 일할수록 사람은 agent를 "실행해 놓고 잊는 도구"가 아니라 "진행을 보고 조정하는 작업자"로 다루게 됩니다. 따라서 UX는 chat input보다 session management, progress trace, checkpoint, approval, diff review에 집중해야 합니다.

---

## 개발자에게 의미: 이제 필요한 역량은 agent operations다

오늘 확인한 공식 발표들을 개발자 관점으로 압축하면, 앞으로 중요한 역량은 "AI API를 호출하는 법"이 아니라 **agent operations**입니다. agent operations는 에이전트가 실제 업무를 맡을 수 있도록 context, tool, permission, runtime, evaluation, observability, cost, security를 운영하는 능력입니다.

구체적으로 다음 역량이 필요합니다.

**Task design.** agent에게 줄 일을 잘게 나누고, goal, non-goal, acceptance criteria, test command, allowed scope를 명확히 하는 능력입니다. Codex 사용 분석과 Siemens 사례가 모두 이를 강조합니다.

**Context engineering.** prompt 문장을 잘 쓰는 것을 넘어, 어떤 source를 가져오고, 어떻게 chunking하고, 어떤 priority로 섞고, 어떤 source를 citation으로 남길지 설계하는 능력입니다. Foundry IQ, BigQuery AI.AGG, Knowledge Fabric, AWS Web Search가 모두 이 영역입니다.

**Tool governance.** MCP tool, cloud API, database query, file system, email, ticket update 같은 action surface를 permission-aware하게 제공하는 능력입니다. Google VPC-SC의 MCP attribute control은 이 방향을 분명히 보여 줍니다.

**Model portfolio management.** Sol/Terra/Luna 같은 tier, MAI model family, open model, partner model을 업무별로 routing하고, fallback과 cost ceiling을 두는 능력입니다. "가장 좋은 모델"이 아니라 "업무에 맞는 모델"이 중요합니다.

**Evaluation.** agent output을 어떻게 검증할지 정하는 능력입니다. unit test, integration test, golden answer, source citation check, human review rubric, red-team scenario, permission-denied scenario가 필요합니다.

**Observability.** agent trace, tool call, token usage, retrieval source, latency, cache hit, failure reason, human feedback을 수집하고 분석하는 능력입니다. Microsoft와 OpenAI 모두 evals/traces/evaluation을 반복해서 언급합니다.

**Security architecture.** agent identity, least privilege, network perimeter, data exfiltration prevention, prompt injection mitigation, sensitive data handling, audit log를 설계하는 능력입니다.

**Cost engineering.** token, cache, model tier, retrieval, serverless compute, web search, long-running session을 비용 단위로 이해하고 product margin과 연결하는 능력입니다.

개발자는 이 역량을 작은 프로젝트에서도 연습할 수 있습니다. 예를 들어 개인 블로그 자동화 agent를 만든다면, source allowlist, post template, citation rule, duplicate check, git commit/push, failure output, cost log, review mode를 두는 식입니다. 사내 HR 시스템이라면 employee data access, role-based tool permission, audit log, draft-only mode, human approval, policy citation, retention rule을 먼저 설계해야 합니다.

AI 기능의 품질은 모델 하나로 결정되지 않습니다. agent가 어떤 시스템 안에서 일하는지가 더 중요해지고 있습니다.

---

## 운영 포인트: 오늘 바로 점검할 체크리스트

오늘 발표들을 바탕으로 AI 제품 또는 사내 agent를 운영하는 팀이 바로 점검할 항목을 정리합니다.

1. **Agent registry가 있는가**
   - agent 이름, owner, 목적, allowed data, allowed tools, model tier, logging policy, cost center, review owner가 기록되어야 합니다.

2. **Task template이 agent-readable한가**
   - goal, context, non-goals, acceptance criteria, allowed files, test command, rollback plan을 issue template에 넣어야 합니다.

3. **Context source의 trust level이 구분되어 있는가**
   - internal policy, customer data, public web, vendor docs, user input, retrieved document는 서로 다른 trust level을 가져야 합니다.

4. **Web search 사용 조건이 명확한가**
   - freshness가 필요한 task에서만 쓰는지, official domain을 우선하는지, sensitive query redaction을 하는지 확인해야 합니다.

5. **MCP tool의 read/write/action이 분리되어 있는가**
   - read-only tool과 destructive action tool은 같은 permission으로 묶으면 안 됩니다.

6. **Agent identity가 사람 identity와 분리되어 있는가**
   - service account, delegated user, session owner, approval actor를 구분해야 합니다.

7. **Network/resource perimeter가 있는가**
   - IAM이 허용해도 perimeter 밖으로 data transfer가 막히는지 확인해야 합니다.

8. **Model routing rule이 문서화되어 있는가**
   - 어떤 task가 low-cost model, balanced model, high-reasoning model로 가는지, fallback은 무엇인지 정해야 합니다.

9. **Cache strategy가 있는가**
   - 반복되는 system prompt, policy block, repository summary, document bundle이 cache-friendly하게 구성되어 있는지 봐야 합니다.

10. **Long-running task가 resumable한가**
    - agent가 실패하면 어디서 재시작하는지, checkpoint와 partial result가 남는지 확인해야 합니다.

11. **Human checkpoint가 명확한가**
    - plan approval, tool permission, code review, deployment approval, exception handling 지점을 정해야 합니다.

12. **Evaluation suite가 있는가**
    - happy path뿐 아니라 stale source, permission denied, prompt injection, conflicting documents, partial failure, malformed JSON을 포함해야 합니다.

13. **Observability가 충분한가**
    - trace, source, tool call, token, latency, cache hit, cost, error, human feedback이 연결되어야 합니다.

14. **AI-generated output의 provenance가 남는가**
    - 어떤 source와 prompt, model, tool call, time으로 생성됐는지 나중에 확인 가능해야 합니다.

15. **Cost budget과 alert가 있는가**
    - long-running agent와 high-reasoning model은 작은 실수로 비용을 크게 늘릴 수 있습니다.

이 체크리스트는 대기업만을 위한 것이 아닙니다. 개인 프로젝트나 작은 스타트업도 AI 기능이 자동으로 글을 쓰고, 코드를 수정하고, customer data를 읽고, 외부 API를 호출한다면 같은 문제를 축소판으로 갖습니다.

---

## 내 프로젝트에 적용할 관점

석이 운영하려는 웹앱, HR 시스템, 배포형 서비스 관점에서 오늘 뉴스는 꽤 직접적입니다. 특히 인사시스템과 같은 업무 도메인은 AI를 붙이기 쉬워 보이지만, 실제로는 privacy, authorization, audit, explanation, human approval이 강하게 필요한 영역입니다.

**HR agent는 처음부터 draft-first로 설계하는 것이 좋습니다.** 인사 평가 요약, 면담 기록 정리, 근태 이상 징후 분석, 정책 질의응답은 모두 민감합니다. agent가 바로 action을 수행하기보다 draft를 만들고, 담당자가 검토하고, 승인 후 반영하는 흐름이 안전합니다.

**문서 source를 엄격히 구분해야 합니다.** 사내 취업규칙, 근로계약서, 평가 기준, 조직도, 직원 개인정보, 법령 문서, 공개 FAQ는 trust level과 접근 권한이 다릅니다. agent가 모든 문서를 같은 context로 받으면 위험합니다.

**권한은 화면 권한과 agent 권한을 분리해야 합니다.** 사용자가 화면에서 볼 수 있는 정보와 agent가 tool로 조회할 수 있는 정보는 같아 보이지만 다를 수 있습니다. agent가 여러 tool을 조합하면 사용자가 직접 보지 못하는 정보를 추론할 수 있기 때문입니다.

**평가 기준은 business rule과 연결해야 합니다.** "답변이 자연스러운가"보다 "정책 조항을 정확히 인용했는가", "개인정보를 과도하게 노출하지 않았는가", "승인 없이 상태 변경을 하지 않았는가", "근거 없는 판단을 하지 않았는가"가 중요합니다.

**grid 화면과 agent workflow는 연결될 수 있습니다.** 예를 들어 HR grid에서 특정 직원 row를 선택하고 "최근 3개월 근태 이상 징후 요약 draft"를 만들 수 있습니다. 이때 agent는 row-level permission, selected columns, time range, policy source, output retention을 따라야 합니다. 단순 채팅창보다 업무 화면 안의 agent action이 더 자연스럽습니다.

**AI 비용은 feature 단위로 추적해야 합니다.** HR 문서 요약, 평가 초안, 정책 Q&A, report generation, workflow recommendation은 token profile이 다릅니다. feature별 cost와 latency를 봐야 pricing과 운영이 가능합니다.

이 관점으로 보면, AI 도입은 "나중에 붙일 기능"이 아니라 시스템 설계 초기부터 고려해야 할 cross-cutting concern입니다. 데이터 모델, 권한 모델, audit log, workflow state, approval chain, document management가 agent-ready해야 합니다.

---

## 오늘의 결론

오늘 공식 발표들을 종합하면, AI 시장은 더 이상 단순한 모델 성능 경쟁으로 설명되지 않습니다. OpenAI는 모델, agent, enterprise platform, chip, safety, cache, serving을 함께 묶고 있습니다. AWS는 agent에게 최신 웹을 managed MCP tool로 제공합니다. Microsoft는 enterprise knowledge, agent runtime, governance, continuous improvement를 하나의 system으로 제시합니다. Google Cloud는 AI를 SQL, graph, VPC perimeter, agent identity로 확장합니다. GitHub는 agent session을 desktop, CLI, web, mobile로 연결합니다. Siemens 사례는 대형 legacy modernization에서 agent가 성공하려면 graph context와 task decomposition이 필요하다는 점을 보여 줍니다.

따라서 2026년 하반기에 개발자와 기업이 봐야 할 핵심 질문은 이것입니다.

**우리의 AI는 똑똑한가보다, 운영 가능한가.**

운영 가능한 AI는 다음 조건을 만족해야 합니다.

- 적절한 model tier를 고르고 fallback을 갖습니다.
- 필요한 context를 permission-aware하게 가져옵니다.
- tool call을 policy와 network perimeter 안에서 실행합니다.
- long-running work를 checkpoint와 trace로 관리합니다.
- source, prompt, model, tool, result의 provenance를 남깁니다.
- 사람의 검토와 승인을 workflow 안에 둡니다.
- 비용과 latency를 feature 단위로 측정합니다.
- 실패를 eval과 system improvement로 되돌립니다.

이 조건을 갖춘 팀은 모델이 바뀌어도 빠르게 적응할 수 있습니다. 반대로 이 조건이 없는 팀은 가장 강한 모델을 써도 production trust를 얻기 어렵습니다. 오늘의 AI Daily News가 말하는 방향은 명확합니다. 이제 경쟁력은 모델 access가 아니라 **AI 운영체계 설계 능력**입니다.

---

## 심층 분석: agentic stack을 실제 제품으로 옮기는 방법

공식 발표들은 방향을 보여 줍니다. 하지만 실제 개발팀이 다음 sprint에서 무엇을 해야 하는지는 더 구체적으로 풀어야 합니다. 아래는 오늘 확인한 OpenAI, AWS, Microsoft, Google Cloud, GitHub, Siemens 발표를 하나의 실행 아키텍처로 번역한 것입니다.

### 1. Agent runtime은 queue와 state machine으로 본다

agent를 단순 함수 호출로 보면 실패합니다. 사용자가 "이 기능을 고쳐줘"라고 입력하면 agent는 여러 상태를 거칩니다. request intake, policy classification, context retrieval, planning, plan approval, tool permission, execution, test, diff generation, review, finalization, commit or draft output 같은 흐름입니다. 각 단계는 실패할 수 있고, 각 실패는 다른 복구 전략을 가져야 합니다.

예를 들어 context retrieval이 실패하면 source unavailable 상태로 멈추고, user에게 source를 요청하거나 fallback source를 사용해야 합니다. tool permission이 실패하면 agent가 무리해서 우회하면 안 됩니다. test가 실패하면 agent는 실패 로그를 context로 다시 받아 작은 수정 loop를 돌 수 있지만, 같은 실패가 반복되면 human review로 넘겨야 합니다. finalization 단계에서 source citation이 부족하면 게시하지 말고 draft로 남겨야 합니다.

따라서 agent runtime은 다음 정보를 state로 저장해야 합니다.

- request id와 session id
- user, delegated user, agent identity
- task type과 risk class
- model tier와 routing decision
- source list와 fetched timestamp
- tool calls와 arguments
- permission grant 또는 denial
- intermediate plan과 human approval
- generated artifact와 diff
- test command와 result
- cost, latency, token usage
- final status와 failure reason

이 state가 있어야 long-running work가 resumable해집니다. OpenAI Codex가 minutes or hours 동안 작동하고, GitHub remote session이 web/mobile에서 이어지고, Microsoft가 agent lifecycle을 build-run-govern-improve로 보는 이유가 여기에 있습니다. agent는 stateless completion이 아니라 stateful workflow입니다.

### 2. Context는 "많이 넣기"보다 "순서를 정하기"가 중요하다

agent가 실패하는 흔한 이유는 context 부족입니다. 하지만 그 반대, context 과잉도 문제가 됩니다. 너무 많은 문서, 오래된 문서, 권한이 맞지 않는 문서, 서로 충돌하는 문서를 한꺼번에 넣으면 agent는 그럴듯하지만 틀린 답을 만들 수 있습니다. Foundry IQ, Knowledge Fabric, BigQuery AI.AGG, AWS Web Search가 모두 다른 방식으로 context 문제를 풀고 있지만, 공통 원칙은 source discipline입니다.

context에는 우선순위가 있어야 합니다. 예를 들어 HR 정책 질의응답이라면 현재 시행 중인 사내 규정이 1순위, 최신 법령과 정부 고시가 2순위, 내부 FAQ가 3순위, 과거 상담 사례는 4순위일 수 있습니다. code modification이라면 현재 repository files와 tests가 1순위, architecture docs가 2순위, issue comments가 3순위, 외부 blog는 낮은 priority입니다. security remediation이라면 vendor advisory와 owned asset inventory가 우선이고, forum snippet은 참고 자료일 뿐입니다.

source priority가 없으면 agent는 보기 좋은 문장을 만든 출처를 더 신뢰할 수 있습니다. production에서는 "어느 source가 이겼는가"를 시스템이 정해야 합니다. 이 규칙은 prompt 안에만 두면 약합니다. retrieval layer와 final answer validator가 함께 적용해야 합니다.

권장 구조는 다음과 같습니다.

- `trusted_policy`: 회사 규정, 법정 문서, 승인된 운영 절차
- `owned_system_state`: DB, telemetry, ticket, code, current configuration
- `approved_docs`: 최신 product docs, architecture docs, runbooks
- `external_official`: vendor official docs, official blog, official changelog
- `external_public`: 일반 웹, community, forum
- `user_supplied`: 사용자가 붙여 넣은 자료

agent는 source tier별로 다르게 행동해야 합니다. `trusted_policy`와 `owned_system_state`는 결론의 근거가 될 수 있습니다. `external_official`은 최신 기술 정보에 좋지만 내부 정책보다 우선하면 안 됩니다. `external_public`은 힌트로만 쓰고, 중요한 결론에는 official source를 다시 확인해야 합니다. `user_supplied`는 injection 가능성이 있으므로 instruction으로 실행하지 말고 quoted context로만 다뤄야 합니다.

### 3. Tool은 API가 아니라 권한 있는 행동이다

MCP가 널리 등장하면서 tool을 붙이는 일이 쉬워졌습니다. 하지만 쉬워졌기 때문에 더 위험합니다. `read_file`, `query_db`, `send_email`, `create_pr`, `update_ticket`, `delete_resource`, `export_csv`는 모두 tool입니다. 그러나 위험도는 전혀 다릅니다. Google Cloud가 MCP attributes로 `mcp.tool.isReadOnly`를 정책 조건에 넣은 것은 이 차이를 platform level에서 다루려는 시도입니다.

실무에서는 tool을 최소 네 등급으로 나누는 것이 좋습니다.

- **Read:** 검색, 조회, 파일 읽기, ticket 보기, log 보기
- **Draft:** 문서 초안, PR draft, email draft, SQL draft, report draft
- **Write:** ticket update, branch push, PR 생성, document update
- **Destructive/External:** 삭제, 배포, email 발송, payment/refund, public post, data export

각 등급에는 다른 approval rule을 둬야 합니다. Read는 agent identity와 data permission이 맞으면 자동 허용될 수 있습니다. Draft는 자동 생성하되 final submission은 사람이 해야 합니다. Write는 제한된 scope에서만 허용하고, diff와 test evidence가 필요합니다. Destructive/External은 기본적으로 human approval이 있어야 하며, 일부는 agent에게 아예 제공하지 않는 것이 맞습니다.

tool call에는 argument policy도 필요합니다. 예를 들어 `query_employee_records` tool은 `employee_id`, `date_range`, `fields`, `purpose`를 받아야 하고, `fields`가 salary나 disciplinary record를 포함하면 더 높은 approval이 필요합니다. `send_email` tool은 recipient domain, attachment, sensitive content check를 거쳐야 합니다. `create_pr` tool은 branch naming, diff size, test result, linked issue를 확인해야 합니다.

agent가 도구를 쓸 수 있다는 것은 agent가 조직의 행동 표면에 닿는다는 뜻입니다. 따라서 tool design은 API design보다 governance design에 가깝습니다.

### 4. Evaluation은 unit test만으로 부족하다

코드 생성 agent라면 unit test와 typecheck가 중요합니다. 하지만 agent evaluation은 그보다 넓습니다. 오늘 발표들이 반복해서 evaluation, system card, red teaming, retrieval benchmark, traces, reviewability를 언급한 이유가 있습니다. agent는 답변만 만드는 것이 아니라 source를 고르고, tool을 호출하고, action을 제안하고, 때로는 system state를 바꿉니다.

agent evaluation은 최소 여섯 종류가 필요합니다.

**Answer correctness eval.** 질문에 대해 정답을 말하는지 확인합니다. 정책 Q&A, API 사용법, error diagnosis 등에 필요합니다.

**Source grounding eval.** 답변이 실제 source에 근거하는지 확인합니다. citation이 있어도 source가 결론을 뒷받침하지 않으면 실패입니다.

**Permission eval.** agent가 접근하면 안 되는 정보에 접근하지 않는지 확인합니다. 사용자가 권한 밖의 정보를 요청했을 때 거절하거나 escalation해야 합니다.

**Tool safety eval.** agent가 risky tool을 적절히 거부하거나 approval을 요청하는지 확인합니다. read-only 상황에서 write action을 시도하면 실패입니다.

**Workflow eval.** long-running task에서 plan, checkpoint, execution, review가 올바른 순서로 진행되는지 확인합니다.

**Adversarial eval.** prompt injection, malicious document, conflicting instruction, social engineering, data exfiltration 시도를 견디는지 확인합니다.

이 eval은 한 번 만들고 끝나는 것이 아닙니다. 실제 실패 사례가 생길 때마다 regression test로 추가해야 합니다. agent가 잘못된 source를 인용했으면 source grounding eval에 넣고, permission을 우회했으면 permission eval에 넣고, tool argument를 잘못 만들었으면 tool safety eval에 넣어야 합니다. OpenAI가 automated red teaming과 rapid-response process를 언급한 것은 이런 loop의 대규모 버전입니다.

### 5. Observability는 "로그 남기기"보다 "판단 재현하기"다

agent log를 많이 남기는 것과 좋은 observability는 다릅니다. 좋은 observability는 나중에 "왜 이 답을 했는지", "왜 이 tool을 호출했는지", "어떤 source를 봤는지", "어느 단계에서 실패했는지", "비용이 왜 늘었는지"를 재현할 수 있어야 합니다.

특히 다음 항목은 반드시 연결되어야 합니다.

- user request
- policy classification result
- retrieval query
- retrieved source와 score
- source permission decision
- model input summary 또는 prompt version
- model name, tier, temperature, reasoning setting
- tool call name, arguments, result
- safety filter 또는 refusal reason
- generated artifact
- validation result
- human feedback
- final action

이 데이터가 흩어져 있으면 incident 분석이 어렵습니다. 예를 들어 agent가 잘못된 HR 정책을 안내했다면, 문제는 모델일 수도 있고, 오래된 문서가 검색됐을 수도 있고, 최신 정책 문서 permission이 막혔을 수도 있고, source priority가 잘못됐을 수도 있습니다. trace가 없으면 "모델이 틀렸다"는 막연한 결론만 남습니다.

OpenAI Frontier의 evaluation, Microsoft Foundry의 evals/traces, GitHub session visibility, Google Cloud perimeter log, AWS AgentCore Gateway는 모두 observability를 운영 표면으로 끌어올리는 흐름입니다.

---

## 위험 지도: 2026년형 AI 도입에서 자주 터질 문제들

AI agent가 production에 들어가면 새로운 failure mode가 생깁니다. 오늘 공식 발표들을 기준으로 위험을 정리하면 다음과 같습니다.

### 1. Stale knowledge risk

모델 training data가 오래됐거나 내부 RAG index가 최신 문서를 반영하지 못해 틀린 답을 내는 문제입니다. AWS AgentCore Web Search, Microsoft Web IQ 같은 기능은 이 위험을 줄이지만, 외부 search result의 신뢰성 문제를 새로 가져옵니다. 해결책은 source freshness metadata, official source 우선순위, fetched timestamp, stale document warning입니다.

### 2. Over-permissioned agent risk

agent에게 너무 넓은 권한을 주면 작은 prompt injection이나 user mistake가 큰 data exposure로 이어질 수 있습니다. Google VPC-SC의 agent identity와 MCP attribute control은 이 위험을 줄이는 방향입니다. 해결책은 least privilege, tool grade separation, principalSet policy, approval gate, network perimeter입니다.

### 3. Context poisoning risk

retrieved document나 user input에 agent instruction처럼 보이는 악성 문장이 포함되는 문제입니다. agent는 untrusted content를 instruction으로 실행하지 않아야 합니다. 해결책은 content/instruction separation, source trust tier, prompt injection eval, tool policy externalization입니다.

### 4. Silent retrieval failure

agent가 필요한 문서를 못 찾았는데도 확신 있게 답하는 문제입니다. Foundry IQ, Knowledge Fabric처럼 retrieval quality를 측정해야 합니다. 해결책은 "충분한 근거 없음" 상태, minimum source requirement, retrieval confidence, human escalation입니다.

### 5. Cost runaway

long-running agent가 반복 실패하며 high-tier model과 web search, retrieval, test run을 계속 사용해 비용이 급증하는 문제입니다. GPT-5.6의 tiered pricing과 cache pricing은 cost engineering을 필수로 만듭니다. 해결책은 per-task budget, token ceiling, retry limit, model downgrade, cache design, cost alert입니다.

### 6. Review bottleneck

agent가 많은 결과물을 만들지만 사람이 검토하지 못해 queue가 쌓이는 문제입니다. Codex 분석에서 parallel agents가 늘어나는 흐름은 이 위험을 키웁니다. 해결책은 task size 제한, auto-validation, review rubric, diff summarization, risk-based review routing입니다.

### 7. False automation confidence

agent가 draft를 만들었을 뿐인데 사용자가 완료된 업무로 착각하는 문제입니다. GitHub remote session이나 Jira progress UI 같은 surface에서는 status design이 중요합니다. 해결책은 draft/planned/running/needs-review/approved/merged/deployed를 분명히 구분하는 것입니다.

### 8. Vendor-specific dependency

특정 provider의 cache, safety, model naming, tool gateway에 깊게 의존하는 문제입니다. full-stack 최적화는 장점이지만 lock-in도 있습니다. 해결책은 provider abstraction을 두되, 고성능이 필요한 부분은 provider-specific path를 명시적으로 관리하는 것입니다.

### 9. Untraceable generated decision

AI가 만든 요약, 분류, 추천이 business decision에 쓰였지만 source와 model, prompt version이 남지 않는 문제입니다. BigQuery AI.AGG 같은 기능이 data pipeline에 들어가면 특히 중요합니다. 해결책은 generated column에 provenance metadata를 함께 저장하는 것입니다.

### 10. Human accountability gap

agent가 action을 수행했을 때 최종 책임자가 불분명한 문제입니다. agent identity와 human approver를 함께 기록해야 합니다. "AI가 했다"는 감사 답변이 될 수 없습니다. 해결책은 delegated authority model, approval record, owner assignment입니다.

---

## 30일 실행 계획: 작은 팀이 agent-ready 시스템으로 가는 순서

모든 것을 한 번에 플랫폼화하려 하면 실패하기 쉽습니다. 오늘 발표에서 배울 점을 30일 실행 계획으로 줄이면 다음과 같습니다.

### 1주차: inventory와 정책부터 만든다

먼저 현재 사용 중인 AI 기능과 agent 후보를 목록화합니다. 어떤 workflow에서 AI를 쓰는지, 어떤 data를 읽는지, 어떤 action을 하는지, 누가 owner인지 정리합니다. 그 다음 risk class를 나눕니다. public content generation, internal document summary, customer data analysis, code modification, HR/finance/legal decision support, external action은 서로 다른 risk class입니다.

산출물은 간단해도 됩니다.

- `agent-inventory.md`
- `tool-permission-matrix.md`
- `source-trust-levels.md`
- `human-approval-policy.md`

이 네 문서만 있어도 AI 도입의 기준선이 생깁니다.

### 2주차: source와 retrieval을 정리한다

다음은 context입니다. agent가 읽을 수 있는 문서와 데이터 source를 정리합니다. source owner, freshness, permission, retention, priority를 기록합니다. 오래된 문서와 최신 문서가 충돌할 때 어떤 것이 우선인지 정합니다. public web을 쓸 때는 official source 우선, fetch timestamp, citation requirement를 둡니다.

이 단계에서 중요한 것은 완벽한 RAG를 만드는 것이 아니라 "무엇을 믿을 수 있는지"를 정하는 것입니다. source trust level이 없으면 agent는 좋은 retrieval engine을 써도 불안정합니다.

### 3주차: tool을 read/draft/write/destructive로 나눈다

agent가 호출할 tool을 위험도별로 나눕니다. read tool은 자동 허용 가능성이 높지만, sensitive data read는 별도 permission이 필요합니다. draft tool은 비교적 안전합니다. write tool은 scope와 test evidence가 필요합니다. destructive/external tool은 human approval이 기본입니다.

각 tool에는 schema, validation, rate limit, audit log, approval rule을 붙입니다. MCP를 쓴다면 tool name, method, readOnly flag를 정책에 반영할 수 있게 설계합니다.

### 4주차: eval과 trace를 최소한으로 붙인다

마지막으로 작은 eval set과 trace를 붙입니다. 처음부터 대규모 benchmark를 만들 필요는 없습니다. 실제 자주 쓰는 질문 20개, 실패하면 큰일 나는 질문 10개, prompt injection 문서 5개, permission denied case 5개, tool misuse case 5개로 시작해도 좋습니다.

trace는 request, source, model, tool call, result, cost 정도만 연결해도 큰 도움이 됩니다. 이후 실패 사례가 나올 때마다 eval set에 추가합니다. 이것이 improve loop의 시작입니다.

---

## 90일 로드맵: AI 기능에서 AI 운영체계로

30일 계획이 기초 체력이라면, 90일 계획은 production readiness입니다.

### 1개월차 목표: 통제 가능한 agent pilot

- agent registry 작성
- source trust level 정의
- tool permission matrix 정의
- risk class별 approval rule 정의
- 1~2개 low-risk workflow에서 pilot
- trace와 cost logging 시작

이 시점의 목표는 멋진 데모가 아니라 통제 가능성입니다. agent가 할 수 있는 일과 할 수 없는 일이 명확해야 합니다.

### 2개월차 목표: workflow integration

- issue template 또는 업무 화면에 agent task 생성 기능 연결
- plan-review-execute-review 상태 machine 적용
- source citation과 fetched timestamp를 UI에 표시
- draft output과 final action을 분리
- eval suite를 CI 또는 scheduled job에 연결
- 비용 budget과 retry limit 적용

이 시점부터 agent는 별도 실험실이 아니라 실제 workflow 안으로 들어갑니다. 그러나 action은 여전히 제한적으로 둬야 합니다.

### 3개월차 목표: governance와 improvement loop

- agent owner review cycle 운영
- failed/rejected output을 eval set에 추가
- model routing과 fallback policy 정교화
- high-risk tool에 human approval UI 적용
- source freshness와 permission sync 모니터링
- monthly cost/reporting dashboard 생성
- security red-team scenario 실행

이 단계에서 agent는 단순 feature가 아니라 운영 대상이 됩니다. 누가 쓰는지, 얼마나 쓰는지, 어디서 실패하는지, 무엇을 개선해야 하는지 볼 수 있어야 합니다.

---

## 제품 설계 원칙: 사용자는 AI를 보고 싶은 것이 아니라 일을 끝내고 싶다

오늘 발표들이 또 하나 보여 주는 것은 AI UX의 변화입니다. AI를 큰 채팅창으로 보여 주는 것만으로는 충분하지 않습니다. 사용자는 업무를 끝내고 싶습니다. 따라서 AI는 업무 표면 안에 들어가야 합니다.

GitHub remote session은 개발자가 CLI, IDE, web, mobile을 오가며 agent를 제어하게 합니다. Microsoft는 GitHub에서 build하고 Foundry에서 run하며 Agent 365에서 govern하는 흐름을 말합니다. HP는 partner portal, support, WXP, security, software delivery 안에 Frontier를 넣습니다. BigQuery AI.AGG는 SQL 안에서 AI 분석을 실행합니다. Siemens Knowledge Fabric은 product owner interview와 architecture impact analysis를 workflow 단계로 만듭니다.

이것을 제품 설계 원칙으로 바꾸면 다음과 같습니다.

**AI entry point는 사용자가 이미 일하는 화면에 있어야 합니다.** HR 담당자는 HR grid에서, 개발자는 PR과 issue에서, 운영자는 dashboard와 alert에서, 데이터 분석가는 SQL editor에서 AI를 써야 합니다.

**AI 상태는 업무 상태와 연결되어야 합니다.** "답변 생성 중"보다 "계획 작성 중", "권한 요청 필요", "테스트 실패", "검토 대기", "승인 완료"가 더 유용합니다.

**AI 결과는 편집 가능해야 합니다.** 초안, diff, checklist, SQL, PR, report처럼 사람이 수정하고 승인할 수 있는 형태가 좋습니다.

**AI 근거는 숨기면 안 됩니다.** source link, fetched time, policy quote, test result, changed files, tool call summary가 있어야 합니다.

**AI action은 되돌릴 수 있어야 합니다.** draft-first, branch-based change, approval log, rollback path가 중요합니다.

**AI는 권한을 설명해야 합니다.** "이 정보는 접근 권한이 없어 확인할 수 없습니다", "이 action은 승인 후 실행됩니다", "외부 발송은 허용되지 않습니다" 같은 상태가 필요합니다.

AI UX는 마법처럼 보일 필요가 없습니다. 오히려 production AI는 투명하고 예측 가능해야 합니다. 사용자가 안심하고 맡길 수 있어야 합니다.

---

## 기술 부채 관점: AI가 기존 부채를 드러낸다

AI agent를 붙이면 기존 시스템의 기술 부채가 더 선명해집니다. 문서가 오래됐으면 agent가 틀린 답을 합니다. 권한 모델이 모호하면 agent access를 설계할 수 없습니다. API가 side effect를 명확히 구분하지 않으면 tool permission을 나눌 수 없습니다. test가 부족하면 generated code를 검증할 수 없습니다. logs가 부족하면 agent가 왜 실패했는지 알 수 없습니다.

따라서 AI 도입은 기술 부채 해결의 계기가 될 수 있습니다.

- 문서 부채: 최신 정책과 outdated guide를 구분해야 합니다.
- 테스트 부채: agent가 변경한 코드를 검증할 자동 test가 필요합니다.
- 권한 부채: role, scope, delegation, audit가 명확해야 합니다.
- API 부채: read/write/destructive action이 분리되어야 합니다.
- 데이터 부채: source owner, schema, freshness, retention이 필요합니다.
- 운영 부채: trace, alert, rollback, incident review가 필요합니다.

Siemens 사례가 흥미로운 이유도 여기에 있습니다. 수억 line legacy code를 AI가 바로 해결한 것이 아니라, code와 documentation의 구조를 graph로 만들고, requirement와 dependency를 trace할 수 있게 했습니다. AI가 legacy를 해결하려면 먼저 legacy를 기계가 이해할 수 있는 형태로 정리해야 합니다.

이 원칙은 작은 서비스에도 적용됩니다. AI를 붙이기 전에 README, API docs, test, permissions, runbook을 정리하면 agent 품질이 올라갑니다. AI는 정돈된 시스템에서 강하고, 어지러운 시스템에서는 더 큰 혼란을 만들 수 있습니다.

---

## 조직 변화: AI 도입의 병목은 모델 예산이 아니라 책임 구조다

기업이 AI를 도입할 때 흔한 병목은 예산이나 API access처럼 보입니다. 하지만 실제 병목은 책임 구조입니다. agent가 만든 결과를 누가 승인하는가. 잘못된 답변으로 고객 피해가 생기면 누가 책임지는가. HR 문서 요약이 부정확하면 누가 검토하는가. security remediation patch를 agent가 만들었을 때 누가 merge할 수 있는가. 비용이 예상보다 커지면 어느 팀 budget에 잡히는가.

OpenAI HP 사례의 Frontier, Microsoft Agent 365, Google VPC-SC, Foundry IQ security, GitHub session control은 모두 이 책임 구조를 제품 기능으로 만들려는 움직임입니다. agent가 많아질수록 central governance와 team autonomy의 균형이 필요합니다.

좋은 조직 구조는 다음과 같습니다.

- Platform team은 agent runtime, tool gateway, logging, cost, security baseline을 제공합니다.
- Domain team은 source ownership, business rule, acceptance criteria, review rubric을 제공합니다.
- Security team은 risk class, data boundary, approval rule, red-team scenario를 제공합니다.
- Legal/Compliance team은 retention, audit, policy citation, regulated workflow 기준을 제공합니다.
- Product team은 user workflow와 status design을 책임집니다.
- Engineering team은 implementation, eval, CI, rollback을 책임집니다.

AI center of excellence가 모든 agent를 직접 만들려고 하면 병목이 됩니다. 반대로 각 팀이 제멋대로 만들면 위험합니다. 중앙은 guardrail과 platform을 제공하고, 현업 팀은 domain workflow를 만드는 구조가 적절합니다.

---

## 경제성: token cost보다 중요한 것은 review cost다

AI 비용을 이야기할 때 token price에 집중하기 쉽습니다. GPT-5.6 발표처럼 input/output/cache pricing은 중요합니다. Foundry IQ Serverless처럼 compute unit과 storage pricing도 중요합니다. 하지만 실제 조직에서는 review cost가 더 큰 병목일 수 있습니다.

agent가 100개의 PR을 만들었는데 senior engineer가 모두 검토해야 한다면 productivity가 오히려 떨어질 수 있습니다. agent가 HR 정책 답변 초안 1,000개를 만들었는데 담당자가 모두 확인해야 한다면 자동화가 아닙니다. agent가 log summary를 만들었지만 운영자가 source를 다시 다 읽어야 한다면 시간 절감이 작습니다.

따라서 AI 경제성은 다음 공식에 가깝습니다.

**value = accepted useful work - generation cost - review cost - rework cost - incident risk**

generation cost만 낮아져도 review cost가 높으면 value는 낮습니다. 반대로 generation cost가 조금 높아도 source grounding, test evidence, small diff, clear summary 덕분에 review cost가 크게 낮아지면 value가 높습니다.

실무에서는 agent output을 "검토하기 쉬운 형태"로 만드는 것이 중요합니다.

- 긴 글보다 변경 요약과 source citation
- 큰 PR보다 작은 PR
- 막연한 추천보다 근거와 trade-off
- 자동 실행보다 draft와 diff
- black-box answer보다 trace와 test result
- 전체 문서 rewrite보다 section-level suggestion

AI agent의 진짜 생산성은 사람이 더 빨리 믿고 승인할 수 있는 결과를 만드는 데서 나옵니다.

---

## 오늘 소스 해석에 대한 주의

오늘 글은 공식 출처만 사용했지만, 공식 발표도 각 회사의 제품 전략과 메시지를 담고 있습니다. 따라서 몇 가지 해석상 주의가 필요합니다.

OpenAI의 GPT-5.6 Sol preview는 제한 preview 상태입니다. 발표된 성능, 가격, cache behavior, availability는 broader release 전후로 달라질 수 있습니다. 따라서 production 적용은 공식 API availability와 documentation을 다시 확인해야 합니다.

OpenAI와 Broadcom의 Jalapeno 발표는 early testing과 future deployment 계획을 포함합니다. detailed technical report는 추후 공개 예정이라고 설명되어 있으므로, 성능 수치는 독립 벤치마크로 확정된 것이 아닙니다. 오늘 글에서는 infrastructure 방향성의 신호로 해석했습니다.

AWS AgentCore Web Search는 official blog에서 generally available로 설명됐지만, 실제 region support, quota, pricing, enterprise privacy 조건은 AWS account와 documentation에서 별도 확인이 필요합니다.

Microsoft Foundry IQ 발표는 여러 기능의 GA와 preview가 섞여 있습니다. Serverless, new knowledge sources, security updates 등은 preview 항목이 있으므로 production 사용 전 support matrix를 확인해야 합니다.

Google Cloud BigQuery AI.AGG는 preview function입니다. preview 기능은 SLA, syntax, pricing, region support, behavior가 변할 수 있습니다. 특히 output validity와 nondeterminism은 직접 검증해야 합니다.

Google Cloud VPC Service Controls의 agentic AI 기능은 강력한 방향이지만, 조직의 기존 network architecture, IAM model, MCP gateway 구성과 맞춰야 합니다. perimeter만으로 모든 prompt injection 문제가 해결되는 것은 아닙니다.

Siemens Knowledge Fabric 사례는 대규모 산업 codebase에 맞춘 reference case입니다. 작은 팀이 그대로 복제하면 과설계가 될 수 있습니다. 다만 graph context, task decomposition, human checkpoint라는 원칙은 규모와 관계없이 유효합니다.

이 주의점은 비관론이 아닙니다. 오히려 AI 발표를 실무에 옮길 때 필요한 태도입니다. 공식 발표는 방향을 보여 주고, production 적용은 각 팀의 risk, data, workflow, budget에 맞게 검증해야 합니다.

---

## 최종 메모: AI agent의 다음 경쟁력은 "설명 가능한 속도"다

AI가 빠른 것은 이제 기본 기대가 되고 있습니다. 앞으로 더 중요한 것은 **설명 가능한 속도**입니다. 빠르게 답하되 왜 그런 답인지 설명할 수 있어야 합니다. 빠르게 코드를 바꾸되 어떤 요구사항을 만족하고 어떤 test를 통과했는지 보여 줘야 합니다. 빠르게 문서를 요약하되 어떤 source를 언제 확인했는지 남겨야 합니다. 빠르게 action을 제안하되 권한과 승인 경로가 명확해야 합니다.

OpenAI의 model과 Frontier, AWS의 managed web search, Microsoft의 Foundry IQ와 Agent 365, Google의 VPC-SC와 BigQuery AI.AGG, GitHub의 remote session, Siemens의 Knowledge Fabric은 모두 이 방향으로 모입니다. AI는 더 빨라지고, 더 오래 일하고, 더 많은 도구를 쓰게 됩니다. 그럴수록 시스템은 더 설명 가능하고, 더 통제 가능하고, 더 감사 가능해야 합니다.

오늘의 결론을 한 문장으로 다시 쓰면 이렇습니다.

**에이전트 시대의 제품 경쟁력은 intelligence 자체가 아니라, intelligence를 안전하고 반복 가능하게 일로 바꾸는 운영 설계에서 나온다.**

---

## 부록: agent-ready 팀을 구분하는 질문 40개

마지막으로, 오늘 뉴스를 실제 팀 점검 질문으로 바꾸면 다음과 같습니다. 아래 질문에 답할 수 있으면 agent-ready에 가까워지고 있습니다. 답하지 못하는 항목이 많다면 모델을 바꾸기 전에 운영 설계를 먼저 정리하는 편이 낫습니다.

1. 우리 조직의 agent 목록과 owner가 문서화되어 있는가.
2. 각 agent가 읽을 수 있는 data source가 명시되어 있는가.
3. source마다 trust level과 freshness 기준이 있는가.
4. public web을 사용할 때 official source 우선 규칙이 있는가.
5. agent가 사용한 source URL과 확인 시각이 결과에 남는가.
6. user input과 retrieved document를 system instruction과 분리하는가.
7. prompt injection 문서를 넣어도 tool policy가 유지되는가.
8. agent identity가 사람 계정과 분리되어 있는가.
9. delegated user와 approver가 trace에 남는가.
10. tool이 read, draft, write, destructive로 구분되어 있는가.
11. destructive 또는 external action은 human approval을 요구하는가.
12. MCP tool의 method와 read-only 여부를 정책에 반영하는가.
13. database query tool은 field-level permission을 확인하는가.
14. email, ticket update, PR creation은 audit log를 남기는가.
15. model tier별 사용 조건과 fallback이 정해져 있는가.
16. high-reasoning model 사용에 budget ceiling이 있는가.
17. 반복 context에 cache strategy가 적용되어 있는가.
18. long-running task는 중간 checkpoint를 저장하는가.
19. 실패한 task를 같은 위치에서 재시작할 수 있는가.
20. retry limit과 escalation rule이 있는가.
21. agent가 만든 plan을 사람이 승인하는 단계가 있는가.
22. agent output은 draft와 final action으로 구분되는가.
23. code 변경은 test evidence 없이 merge되지 않는가.
24. generated SQL이나 JSON은 validation을 거치는가.
25. HR, finance, legal 같은 민감 workflow는 별도 review rubric이 있는가.
26. retrieval failure를 "근거 부족" 상태로 표현할 수 있는가.
27. source conflict가 생겼을 때 우선순위 rule이 있는가.
28. agent cost를 feature 또는 workflow 단위로 볼 수 있는가.
29. token, latency, tool call, retrieval cost가 trace와 연결되는가.
30. review cost와 rework cost를 측정하는가.
31. rejected output을 eval set에 추가하는 절차가 있는가.
32. permission denied case를 eval에 포함하는가.
33. stale document case를 eval에 포함하는가.
34. malicious document나 hidden instruction case를 eval에 포함하는가.
35. agent가 사용할 수 없는 정보를 요청받았을 때 안전하게 거절하는가.
36. network perimeter가 data exfiltration을 막는가.
37. 외부 API 호출에는 allowlist 또는 destination policy가 있는가.
38. agent가 만든 business decision의 provenance가 남는가.
39. incident 발생 시 어떤 source, model, prompt, tool call이 원인인지 추적할 수 있는가.
40. 매달 agent inventory, cost, failure, eval result를 review하는 운영 회의가 있는가.

이 질문들은 특정 vendor에 종속되지 않습니다. OpenAI, AWS, Microsoft, Google Cloud, GitHub 중 어떤 stack을 쓰더라도 기본 구조는 같습니다. 모델은 계속 바뀌고, tool standard도 진화하고, pricing도 달라질 것입니다. 하지만 source discipline, permission boundary, traceability, evaluation, human accountability는 계속 필요합니다. 그래서 지금 팀이 해야 할 일은 "다음 모델을 기다리는 것"이 아니라, 다음 모델이 들어와도 흔들리지 않을 운영 기반을 만드는 것입니다.

특히 작은 팀일수록 이 질문을 과하게 느낄 수 있습니다. 그러나 모든 항목을 enterprise platform으로 구현하라는 뜻은 아닙니다. 처음에는 markdown 문서, 간단한 JSON policy, git log, CI check, PR template만으로도 충분히 시작할 수 있습니다. 중요한 것은 agent가 어떤 권한으로 어떤 source를 보고 어떤 행동을 했는지 설명할 수 있는 최소 구조를 갖추는 것입니다. 이 최소 구조가 없으면 기능이 늘어날수록 불확실성도 같이 늘어납니다.

오늘의 공식 발표들은 거대한 기업들의 플랫폼 전략처럼 보이지만, 그 안의 원칙은 작은 프로젝트에도 그대로 적용됩니다. AI를 업무에 붙이는 순간, 그 AI는 사용자의 시간을 대신 쓰고 조직의 데이터를 읽고 시스템의 행동 표면에 접근합니다. 그러므로 agent-ready 팀은 AI를 "편리한 도구"로만 보지 않고, 책임 있는 작업 주체로 다룰 준비를 해야 합니다.

또 하나 중요한 점은 이 준비가 innovation을 늦추기 위한 절차가 아니라는 것입니다. 오히려 명확한 권한, source, eval, trace가 있어야 팀이 더 빠르게 실험할 수 있습니다. 무엇을 해도 되는지 불명확한 조직은 매번 회의와 예외 처리로 느려집니다. 반대로 guardrail이 분명한 조직은 낮은 위험의 task를 빠르게 자동화하고, 높은 위험의 task는 필요한 승인만 거쳐 진행할 수 있습니다. 좋은 governance는 브레이크가 아니라 차선과 신호등에 가깝습니다. 속도를 줄이는 장치가 아니라, 여러 사람이 같은 도로에서 더 빠르고 안전하게 움직이게 하는 기반입니다. 결국 운영 설계는 창의성을 제한하는 문서가 아니라, 더 많은 사람이 AI를 믿고 더 넓은 업무에 적용하게 만드는 신뢰 인프라입니다.

---

## Source Links

- OpenAI News index: https://openai.com/news/
- OpenAI - HP Inc. launches Frontier strategic partnership with OpenAI: https://openai.com/index/hp-frontier-partnership/
- OpenAI - Previewing GPT-5.6 Sol: https://openai.com/index/previewing-gpt-5-6-sol/
- OpenAI - GPT-5.6 Preview System Card: https://deploymentsafety.openai.com/gpt-5-6-preview
- OpenAI - How agents are transforming work: https://openai.com/index/how-agents-are-transforming-work/
- OpenAI - OpenAI and Broadcom unveil LLM-optimized inference chip: https://openai.com/index/openai-broadcom-jalapeno-inference-chip/
- GitHub Blog - Take your local GitHub sessions anywhere: https://github.blog/news-insights/product-news/take-your-local-github-sessions-anywhere/
- AWS Machine Learning Blog - Introducing Web Search on Amazon Bedrock AgentCore: https://aws.amazon.com/blogs/machine-learning/introducing-web-search-on-amazon-bedrock-agentcore/
- Microsoft Foundry Blog - Foundry IQ: Build smarter agents faster with unified knowledge and serverless retrieval: https://devblogs.microsoft.com/foundry/build-smarter-agents-faster-with-foundry-iq/
- Microsoft Blog - AI alone won’t change your business. The system running it will.: https://blogs.microsoft.com/blog/2026/06/02/ai-alone-wont-change-your-business-the-system-running-it-will/
- Google Cloud Blog - AI & Machine Learning index: https://cloud.google.com/blog/topics/ai-machine-learning
- Google Cloud Blog - Deep dive into BigQuery AI.AGG function: https://cloud.google.com/blog/products/data-analytics/deep-dive-into-bigquery-ai-agg-function
- Google Cloud Blog - Securing agentic AI: What's new in VPC Service Controls: https://cloud.google.com/blog/products/identity-security/securing-agentic-ai-whats-new-in-vpc-service-controls
- Google Cloud Blog - How Siemens "sliced the elephant," modernizing legacy code with agentic workflows: https://cloud.google.com/blog/products/ai-machine-learning/how-siemens-sliced-the-elephant-modernizing-legacy-code-with-agentic-workflows
