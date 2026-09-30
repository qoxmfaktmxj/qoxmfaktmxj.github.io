---
layout: post
title: "2026년 9월 30일 AI 뉴스: 에이전트의 다음 경쟁은 모델 호출이 아니라 API 경계, 로컬 실행, 런타임 거버넌스다"
date: 2026-09-30 11:30:00 +0900
categories: [ai-daily-news]
tags: [ai, news, agentic-ai, mcp, api-gateway, google-cloud, anthropic, claude, local-ai, security, governance, llmops]
permalink: /ai-daily-news/2026/09/30/ai-news-daily.html
---

# 오늘의 AI Daily News

## 작성 기준

2026년 9월 30일 11:30 KST 기준으로 공개된 **공식 발표와 공식 개발자 블로그**만 확인해 작성했습니다. 이번 실행에서는 `web_search`가 Gateway의 Gemini API 키 부재로 동작하지 않았습니다. 자동화 원칙에 따라 검색 오류만으로 중단하지 않고 OpenAI News, Anthropic News, Google for Developers Blog와 각 개별 공식 발표 URL을 `web_fetch`로 직접 확인했습니다. 따라서 아래의 사실 서술은 해당 공식 출처의 발표 범위 안에 한정합니다. 시장 점유율, 비공식 벤치마크, 소셜 미디어 반응, 제3자 보도는 근거로 사용하지 않았습니다.

오늘의 흐름을 한 문장으로 요약하면 다음과 같습니다. **AI 에이전트는 더 이상 “좋은 모델에 프롬프트를 넣는 기능”이 아니라, 기존 API를 어떤 도구로 노출할지, 어떤 데이터와 코드를 로컬에 남길지, 어떤 권한·한도·세션 규칙 아래 실행할지를 설계하는 운영 시스템이 되고 있습니다.**

Google은 기존 OpenAPI 기반 REST API를 별도 MCP 서버 없이 원격 MCP 도구로 제공하는 API Gateway 기능을 Public Preview로 공개했습니다. 같은 시기 Antigravity SDK는 Gemma 4 26B A4B와 LiteRT를 통해 오프라인 로컬 agent workflow를 지원한다고 발표했습니다. 또 Google의 zero-trust agent 안내는 prompt filtering만으로는 부족하며, 도구 호출의 의미·세션 누적 행동·실행 전 차단을 함께 다뤄야 한다는 점을 구체적인 운영 패턴으로 설명합니다. Anthropic은 Claude Opus 5.5를 공개하면서 장기 작업, 비용·속도, action screening, sandbox, prompt-injection 저항성, 생물·사이버 분야의 검증 기반 접근을 함께 제시했습니다.

이 네 발표는 서로 다른 제품처럼 보이지만, 실제로는 하나의 아키텍처 질문으로 모입니다. **누가 에이전트에게 어떤 일을 시키며, 그 일이 실제 시스템의 상태를 바꾸기 전에 어떤 정책과 증거를 통과하게 할 것인가?** 모델의 품질은 그 질문의 출발점일 뿐, 운영 설계의 대체재는 아닙니다.

---

## 한눈에 보는 Top News

1. **Google Cloud API Gateway, REST API를 원격 MCP 서버로 제공하는 기능을 Public Preview로 공개**
   - 공식 발표일: 2026-09-24
   - 핵심: OpenAPI 3.0.x/3.1.x 명세에 MCP 관련 annotation을 추가하면, 기존 REST operation을 MCP `tools/call`로 변환해 제공할 수 있습니다. 기존 JWT/API key 인증, quota, logging 정책은 REST와 MCP 호출에 같은 경로로 적용됩니다.
   - 개발자 의미: agent integration의 첫 선택지는 “새 MCP 서버를 만들기”가 아니라 “이미 운영 중인 API contract와 gateway policy를 재사용할 수 있는가”가 됩니다.

2. **Google Antigravity SDK, 로컬 모델 기반 오프라인 agent workflow 지원 발표**
   - 공식 발표일: 2026-09-23
   - 핵심: LiteRT와 Gemma 4 26B A4B를 사용해 로컬 GPU/RAM 위에서 agentic assistance를 실행하고, Ollama·LM Studio·vLLM 같은 OpenAI-compatible local server와도 연결할 수 있습니다.
   - 개발자 의미: 민감 코드·문서·로그를 모두 클라우드에 보내야만 agent를 만들 수 있다는 가정이 약해집니다. 다만 로컬 실행은 보안 면제가 아니라 다른 형태의 endpoint·권한·모델 공급망 관리입니다.

3. **Google, syntax가 아니라 tool intent와 multi-turn 행동을 보는 zero-trust agent 운영 패턴 제시**
   - 핵심: Model Armor, Semantic Governance Policies, Agent Anomaly Detection을 통해 입력 단계·도구 실행 전·세션 누적 행위의 세 층을 설명합니다.
   - 개발자 의미: “프롬프트 인젝션을 막았다”는 것만으로 안전한 agent가 되지 않습니다. 승인 가능한 tool call의 business meaning, 호출 속도, 같은 대상에 대한 반복 mutation, 누적 금액·권한을 함께 측정해야 합니다.

4. **Anthropic, Claude Opus 5.5 공개: 장기 agentic work의 비용·속도·안전 제어를 함께 제시**
   - 공식 발표일: 2026-09-22
   - 핵심: Anthropic은 Opus 5.5가 Opus 5보다 typical workload에서 40% 낮은 비용, 30% 이상 빠른 출력을 제공한다고 설명하며, action screening classifier, audit 가능한 sandbox, code review, 장기·불가능 과업까지 확장한 alignment test를 함께 소개했습니다.
   - 개발자 의미: 고성능 모델 도입은 단순 endpoint 교체가 아닙니다. task-level 비용, effort 설정, fallback, action permission, review gate, safety intervention을 하나의 배포 단위로 관리해야 합니다.

---

## 오늘의 핵심 한 문장

**2026년 9월 말 AI 제품 경쟁의 중심은 모델의 답변 품질에서, 기존 업무 API를 안전하게 도구화하고·민감 작업을 적절한 실행 위치에 배치하고·모델의 행동을 실행 전과 실행 후에 감사할 수 있게 만드는 agent runtime으로 이동하고 있습니다.**

---

## 배경: “모델을 연결했다”와 “업무를 자동화했다” 사이에는 거대한 간극이 있다

LLM을 제품에 붙이는 초기 단계는 비교적 단순합니다. 사용자가 질문을 입력하고, 애플리케이션이 문맥을 보태 모델 API를 호출하고, 응답을 화면에 표시합니다. 이 구조에서는 hallucination, latency, token cost, response style이 중요한 문제입니다. 하지만 모델이 실제 업무를 수행하기 시작하면 시스템의 성격이 달라집니다. 주문 상태를 조회하고, 고객 정보를 수정하고, 환불을 요청하고, 소스 코드를 바꾸고, 배포를 시작하고, 내부 문서를 읽고, 티켓을 생성하는 순간부터 LLM은 텍스트 생성기가 아니라 권한을 가진 workflow participant가 됩니다.

이 전환에서 가장 자주 생기는 오해는 MCP나 tool calling을 “API 연동의 편의 기능”으로만 보는 것입니다. 도구 호출은 API endpoint를 발견하고 JSON argument를 보내는 기술이지만, production 환경에서 더 어려운 문제는 그 다음입니다. 이 operation은 agent에 노출해도 되는가? 읽기와 쓰기를 같은 toolset에 넣어도 되는가? 누가 tool schema를 발견할 수 있는가? agent가 호출한 API는 사람의 호출과 같은 quota와 audit path를 타는가? 잘못된 호출이 실행되기 전에 중단되는가? 여러 번의 정상 호출이 합쳐져 비정상 결과가 되는 경우는 어떻게 탐지하는가?

Google의 API Gateway MCP 발표과 zero-trust agent 안내가 중요한 이유가 여기에 있습니다. 전자는 API를 agent-ready surface로 만드는 경로를, 후자는 그 surface가 실제 권한·정책·세션 관측과 만나야 한다는 경로를 보여 줍니다. Antigravity의 로컬 모델 지원은 같은 질문을 data boundary 관점에서 확장합니다. 어떤 추론은 cloud model이 수행해도 되지만, 어떤 repository와 log와 file operation은 device 밖으로 나가면 안 될 수 있습니다. Anthropic의 Opus 5.5 발표은 더 강한 장기 agent가 등장할수록 실행 행동을 screen하고, sandbox하고, 검토하고, 비용을 제어하는 장치가 제품 스펙의 일부가 된다는 점을 보여 줍니다.

따라서 에이전트를 설계하는 팀은 모델·도구·정책·관측·사람의 개입을 분리된 체크박스가 아니라 하나의 control plane으로 봐야 합니다.

---

## 1) REST API를 MCP 도구로: 새 middleware보다 기존 정책 경로를 먼저 재사용하라

**공식 출처:** [Turn your REST APIs into MCP tools with Google Cloud API Gateway](https://developers.googleblog.com/turn-your-rest-apis-into-mcp-tools-with-google-cloud-api-gateway/)

Google은 9월 24일, Google Cloud API Gateway가 remote MCP server로 동작하는 기능을 Public Preview로 제공한다고 발표했습니다. 발표의 핵심은 단순히 “MCP를 지원한다”가 아닙니다. 이미 API Gateway 뒤에서 운영되는 REST API의 OpenAPI 명세, 인증, quota, logging을 agent 도구 호출에도 이어 붙이겠다는 접근입니다.

발표에 따르면 팀은 OpenAPI 3.0.x 또는 3.1.x 명세에 `x-google-api-management.mcp`를 추가하고, operation별로 `x-google-mcp-tool`을 설정할 수 있습니다. gateway는 MCP JSON-RPC 요청을 받아 `tools/call`을 해당 REST request로 transcode하고, backend의 응답을 MCP result로 변환합니다. 중요한 점은 이 변환이 기존 gateway 바깥에 별도 proxy를 만들지 않는다는 것입니다. 일반 REST 호출과 MCP 호출이 하나의 policy path를 공유하므로, 기존 JWT나 API-key authentication, quota, logging이 그대로 적용됩니다.

이 구조는 agent platform을 만드는 조직에 매우 실용적인 질문을 던집니다. 기존에 주문 조회, 재고 확인, CRM lookup, 사내 검색, 배포 상태 조회 같은 API가 있다면, agent 전용 middleware를 새로 만들기 전에 그 API가 이미 가진 contract와 governance를 얼마나 재활용할 수 있는지 점검해야 합니다. 새 MCP server를 빠르게 만드는 것은 쉬울 수 있습니다. 하지만 시간이 갈수록 authentication code, schema drift 대응, rate limit, log correlation, incident response, versioning을 두 군데에서 유지해야 할 가능성이 커집니다.

### MCP 전환이 API ownership을 바꾸는 방식

REST API는 원래 사람이 만드는 UI나 서비스 간 통신을 중심으로 설계되는 경우가 많았습니다. agent는 API를 다르게 사용합니다. 사람은 화면에서 버튼을 누르며 필요한 argument를 보완하지만, agent는 tool description과 schema만 보고 어떤 operation을 골라야 할지 추론합니다. 그래서 tool의 `name`, `description`, parameter schema는 문서 장식이 아니라 model behavior의 일부가 됩니다.

Google 발표도 tool description을 “모델이 언제 도구를 호출할지 결정하는 primary signal”로 설명합니다. 이는 API 설명 문구를 짧게 적어 두는 관행이 위험해질 수 있음을 뜻합니다. `getOrderStatus` 같은 이름만으로는 충분하지 않습니다. 어떤 상황에 사용해야 하는지, 어떤 범위의 정보를 돌려주는지, 어떤 identifier가 필요한지, write operation인지 read operation인지, 민감 데이터가 포함되는지, 사람 승인이나 추가 확인이 필요한지를 명료하게 설계해야 합니다.

좋은 agent tool contract는 모델 편의성뿐 아니라 운영자의 안전 요구도 드러냅니다. 예를 들어 `issue_refund` 하나로 모든 환불을 처리하기보다, `draft_refund_request`와 `approve_refund_request`를 분리하고 후자에는 사람 또는 별도 policy gate를 두는 편이 감사·rollback·least privilege에 유리합니다. “API는 이미 있으니 그대로 노출한다”는 판단은 편리하지만, UI에서 사람이 보완하던 안전장치를 agent가 건너뛰게 만들 수 있습니다.

### discovery와 execution을 분리해서 생각해야 한다

Google은 `tools/list`가 기본적으로 unauthenticated일 수 있고, production에서는 JWT로 discovery를 보호해야 한다고 안내합니다. API key로는 이 discovery method를 보호할 수 없다는 설명도 포함합니다. 반면 `tools/call`은 underlying REST operation의 인증 요구를 적용합니다.

이 차이는 매우 중요합니다. 많은 팀은 실행 권한만 보지만, 도구 이름·입력 schema·설명 자체도 공격자에게 업무 구조를 알려 줄 수 있습니다. 예컨대 `terminate_employee_access`, `export_payroll`, `rotate_signing_key` 같은 tool name이 외부에 노출되는 것만으로도 탐색 비용이 낮아집니다. discovery는 권한이 약한 정보처럼 보이지만, agent 시대에는 capability inventory의 일부입니다.

실무에서는 다음의 두 표면을 분리해 threat model에 넣어야 합니다.

- **발견 표면(discovery):** 누가 어떤 tool, resource, prompt, schema를 볼 수 있는가?
- **실행 표면(execution):** 누가 어떤 argument로 operation을 호출하고, 어떤 policy를 통과해야 하는가?

둘 중 하나만 잠가서는 충분하지 않습니다. discovery를 열어 둔 내부 개발 환경이라도 endpoint와 schema가 외부로 노출되지 않도록 network boundary를 확인해야 하고, execution이 강하게 보호되더라도 tool description이 과도한 내부 정보를 담지 않도록 해야 합니다.

### API Gateway 접근의 장점과 현재 경계

공식 발표의 장점은 명확합니다. 별도 MCP server를 build·host·maintain하지 않아도 되고, MCP와 REST traffic이 같은 quota allocation과 logging path를 공유합니다. API Hub와 연결하면 MCP-specific metadata로 publish되고 Agent Registry에 나타날 수 있다는 설명도 있습니다. 이는 enterprise에서 “어떤 agent가 어떤 tool을 쓸 수 있는가”를 중앙 inventory로 관리하려는 흐름과 맞닿아 있습니다.

동시에 Public Preview의 범위도 명시돼 있습니다. REST와 OpenAPI 3.x backend가 대상이며, MCP resources·prompts, response streaming, Model Armor payload inspection은 roadmap에 있습니다. HTTP 204처럼 empty body를 반환하는 operation은 노출되지 않고, deeply nested object schema는 `tools/list`에 완전하게 render되지 않을 수 있으며, gateway당 최대 1,000 tools라는 제한도 있습니다. MCP와 model routing을 같은 API config에서 동시에 활성화할 수 없다는 점도 설계 단계에서 확인해야 합니다.

이 경계는 “agent-ready”가 곧 “모든 API를 무제한으로 노출해도 된다”는 뜻이 아님을 보여 줍니다. Preview 기능을 도입할 때는 먼저 작은 read-only toolset으로 시작하고, schema fidelity, auth propagation, audit correlation, error handling, quota behavior를 검증한 뒤 write capability를 단계적으로 늘리는 편이 낫습니다.

### 개발자에게 의미

1. MCP server를 새로 만들기 전에 현재 OpenAPI 명세의 품질, versioning, auth·logging 경로를 inventory합니다.
2. tool description은 자연어 문서가 아니라 model routing과 security boundary의 일부로 취급합니다.
3. read / draft / approve / execute를 분리해 write action의 blast radius를 줄입니다.
4. tool discovery와 tool execution에 다른 authentication·network·audit 요구를 둡니다.
5. REST와 MCP 호출이 같은 request ID, actor identity, quota, log sink에서 상관 분석되는지 확인합니다.

### 운영 포인트

- OpenAPI 2.0 기반 gateway는 먼저 3.0.x/3.1.x migration 계획을 세웁니다.
- `tools/list`를 production에서 공개할 이유가 없다면 JWT 보호와 network access를 기본값으로 둡니다.
- tool description에 “언제/왜 사용하고, 언제 사용하지 않는가”를 포함합니다.
- API endpoint별 idempotency, retry behavior, side effect를 명시합니다. LLM agent는 timeout이나 ambiguous error 뒤에 호출을 반복할 수 있습니다.
- quota는 사용자·agent·tool·tenant 차원으로 분리해 noisy neighbor와 runaway loop를 관리합니다.
- MCP 로그를 기존 API observability와 분리하지 말고, prompt/session/tool-call/HTTP request를 correlation ID로 연결합니다.

---

## 2) 로컬 agent workflow: privacy와 비용의 해법이면서 endpoint security의 새 과제

**공식 출처:** [Introducing Support for Local AI Models in the Antigravity SDK](https://developers.googleblog.com/introducing-support-for-local-ai-models-in-the-antigravity-sdk/)

Google은 9월 23일 Antigravity SDK가 다양한 local model과 execution option을 지원하며, 초기 지원으로 Google AI Edge LiteRT 위의 Gemma 4 26B A4B를 제공한다고 발표했습니다. 공식 설명에 따르면 개발자는 로컬 GPU와 RAM을 사용해 완전 오프라인 agentic assistance를 실행할 수 있습니다. Ollama, LM Studio, vLLM 같은 OpenAI-compatible inference server도 `LocalOpenAIAgentConfig`를 통해 연결할 수 있습니다.

이 발표가 중요한 이유는 “모든 agentic workflow는 cloud LLM에 코드와 문서를 보낸다”는 전제가 약해지기 때문입니다. 규제 환경, 소스 코드 기밀성, 네트워크가 불안정한 현장, API cost가 민감한 대량 반복 업무에서는 모델의 품질만큼 execution location이 중요합니다.

공식 글은 local execution의 장점을 비용 효율, privacy, offline resiliency, hybrid workflow로 제시합니다. 특히 cloud architect가 파일명과 작업 설명 수준의 적은 정보로 plan을 세우고, 로컬 Gemma instance가 source code를 device 안에서 audit·patch·test하는 architect-builder 패턴을 소개합니다. 발표에 기재된 demo에서는 3개 취약 모듈의 audit과 patch 과정에서 97.2%의 token이 로컬·오프라인에서 처리됐다고 설명합니다. 이 수치는 특정 demo의 결과이지 모든 팀에 일반화할 수는 없지만, cloud planner와 local executor를 분리하는 설계가 실제 제품 패턴으로 부상하고 있다는 신호입니다.

### “로컬”은 data egress를 줄이지, 위험을 없애지 않는다

로컬 모델 실행을 도입할 때 가장 위험한 오해는 “데이터가 클라우드에 안 나가니 안전하다”는 결론입니다. 데이터 egress는 중요한 위험 축이지만 유일한 축이 아닙니다. 로컬 agent는 filesystem, shell, IDE, browser profile, credential helper, network socket과 더 가까이 붙기 쉽습니다. 즉 cloud API key 노출 위험이 줄어드는 대신, endpoint에서의 permission·sandbox·extension·model artifact·supply-chain 위험이 커질 수 있습니다.

따라서 local agent의 보안 설계는 다음 질문에서 시작해야 합니다.

- agent process는 어떤 workspace만 읽고 쓸 수 있는가?
- shell command와 network request는 allowlist인가, 사람 확인 후 실행인가?
- local model file과 runtime package는 어떤 provenance와 checksum으로 배포되는가?
- agent가 만든 patch는 어떤 test·lint·security scan을 거쳐 merge 가능한가?
- 사용자의 personal token, SSH key, cloud credential, browser session이 agent context에 실수로 포함될 수 있는가?
- local inference server가 LAN에 열려 있거나, 다른 process가 prompt·response를 읽을 수 있는가?

이 질문은 cloud agent에도 필요하지만, local agent에서는 권한 경계가 더 device-specific해집니다. 로컬 실행의 이상적인 형태는 “사용자 홈 전체를 맡기는 AI”가 아니라, 좁은 workspace, 최소 권한 token, 읽기 전용 source snapshot, 제한된 command set, 명시적 egress rule, 재현 가능한 test sandbox를 갖춘 작업자입니다.

### hybrid orchestration은 모델 라우팅 이상이다

Google이 소개한 cloud architect / on-device workforce 패턴은 단순한 cost optimization을 넘어 역할 분리에 관한 제안입니다. cloud model은 고수준 계획, 일반적 방법론, public documentation 기반 reasoning에 강할 수 있습니다. local model은 민감한 source, proprietary data, 반복적인 static analysis, file mutation, test execution을 담당할 수 있습니다. 그러나 이 분리는 자동으로 안전해지지 않습니다. cloud planner가 local executor에 전달하는 plan도 instruction injection이나 unsafe action을 포함할 수 있고, local executor가 반환하는 요약은 cloud로 보내기 전 민감 정보를 제거해야 합니다.

좋은 hybrid design은 경계를 명확히 합니다.

| 계층 | 권장 역할 | 보내도 되는 정보 | 보내지 말아야 할 정보 |
|---|---|---|---|
| Cloud planner | 작업 분해, 일반 지식, 공개 문서 기반 설계 | task goal, 비식별 metadata, 허용된 interface | 소스 본문, customer data, secrets, raw logs |
| Local executor | 코드 분석, patch, test, 파일 작업 | 필요한 workspace의 최소 사본 | 홈 디렉터리 전체, credential store |
| Policy layer | 권한 판정, 승인, audit | actor, tool, risk label, aggregated telemetry | 불필요한 prompt 원문·비밀값 |
| Human reviewer | merge·배포·고위험 action 승인 | diff, test result, rationale, risk evidence | 자동화가 필요로 하지 않는 private context |

표의 핵심은 cloud/local 구분 자체가 아니라 **data minimization과 capability minimization**입니다. cloud에 보내지 않는다고 해서 local process에 모든 권한을 주면 안 되고, local model이 있다고 해서 cloud planner가 source 내용을 볼 필요가 없어지는 것도 아닙니다. 각 계층이 필요한 정보와 허용된 side effect를 작게 만들어야 합니다.

### 비용 모델도 달라진다

로컬 실행은 “무료”가 아닙니다. API token bill은 줄 수 있지만 GPU/CPU, 전력, 장비 감가, model download, runtime maintenance, 개발자 지원, observability, security patch 비용이 생깁니다. 또한 성능과 latency는 client hardware에 따라 달라지고, 24GB 이상의 VRAM 또는 unified memory가 권장된다는 공식 안내처럼 hardware requirement이 제품 범위를 제한할 수 있습니다.

그래서 팀은 cloud와 local을 이분법으로 선택하기보다 task economics를 측정해야 합니다. 반복적이고 민감하며 모델 요구 수준이 적당한 작업은 local이 유리할 수 있습니다. 최신 지식, 대규모 reasoning, 높은 reliability, shared service 운영이 필요한 작업은 cloud가 더 나을 수 있습니다. 핵심은 “토큰당 가격”이 아니라 “검증된 작업 완료당 총비용”입니다. failed patch, human rework, incident risk까지 포함해야 합니다.

### 개발자에게 의미

1. 민감 코드·문서·로그가 들어가는 agent task를 data classification 기준으로 먼저 나눕니다.
2. local agent에는 workspace allowlist, filesystem mount, network egress, command policy를 명시합니다.
3. cloud planner와 local executor 사이에는 task manifest·redacted summary처럼 최소 정보 contract를 둡니다.
4. local model과 runtime도 dependency 관리 대상입니다. version pinning, provenance, update channel, rollback을 운영합니다.
5. model quality뿐 아니라 hardware coverage, support burden, test success rate, review time을 포함해 ROI를 계산합니다.

### 운영 포인트

- local inference endpoint가 기본적으로 loopback에만 bind되는지 확인합니다.
- prompt·tool trace·generated file이 어디에 저장되는지, disk encryption·retention policy와 맞는지 점검합니다.
- agent workspace와 developer의 credential directory를 분리합니다.
- autonomy는 `read → draft → test → propose → approve → execute` 순서로 단계화합니다.
- machine capability telemetry를 수집하되, source code나 secret이 telemetry로 섞이지 않도록 redaction을 둡니다.
- offline 환경의 model/runtime update와 vulnerability patch 절차를 별도로 문서화합니다.

---

## 3) zero-trust agent: 입력 필터 하나로는 multi-turn 공격을 막을 수 없다

**공식 출처:** [Build zero-trust AI agents that judge intent, not just syntax](https://developers.googleblog.com/build-zero-trust-ai-agents-that-judge-intent-not-just-syntax/)

Google의 zero-trust agent 글은 production agent security를 세 개의 보완적 층으로 설명합니다. 첫째는 Model Armor를 통한 edge prompt 검사, 둘째는 Semantic Governance Policies를 통한 tool intent의 runtime 판단, 셋째는 Agent Anomaly Detection을 통한 multi-turn·fleet-level 이상 행동 탐지입니다. 이 구분은 agent security가 한 번의 입력 또는 한 번의 tool call만으로 끝나지 않는다는 점을 잘 보여 줍니다.

### 1층: 입력을 신뢰하지 말되, 입력 검사에 모든 것을 기대하지 말라

prompt injection, malicious document, untrusted web content, user instruction의 충돌은 agent가 외부 정보를 읽을수록 늘어납니다. input screening은 분명 필요합니다. 하지만 공격자는 문장 자체가 아니라 정상적인 업무 흐름을 이용할 수 있습니다. “20달러 환불”은 개별적으로는 정책상 허용될 수 있습니다. 그 요청을 한 세션에서 8번 반복해 총 160달러를 환불하는 경우가 문제입니다. 입력 하나만 보면 악의가 드러나지 않을 수 있습니다.

그래서 edge filter는 중요한 첫 관문이지만, authorization engine의 대체재가 아닙니다. 입력이 무해해 보여도 tool argument의 business meaning, actor entitlement, target resource, amount, time window, prior actions를 판단해야 합니다.

### 2층: syntax가 아니라 intent와 business policy를 실행 전에 판정하라

Google은 Semantic Governance Policies가 tool call을 실제 실행 전에 평가하는 방식을 설명합니다. 예시에서는 디지털 소프트웨어의 30달러 초과 환불에 manager authorization이 필요하다는 자연어 constraint가 `issue_refund` 호출을 deny합니다. 정책 판정이 tool execution 전에 이루어지므로 Cloud KMS 서명이나 ledger 변경이 발생하지 않는다는 점이 핵심입니다.

이는 agent system에서 authorization이 HTTP method나 endpoint allowlist만으로 충분하지 않음을 보여 줍니다. `POST /refunds`를 호출할 수 있다는 사실과 “이 고객·이 상품·이 금액·이 상황에서 이 환불이 허용되는가”는 다른 문제입니다. 후자는 도메인 policy이며, agent의 natural-language reasoning과 deterministic business rule이 만나는 지점입니다.

다만 자연어 policy engine을 도입한다고 해서 traditional authorization을 버리면 안 됩니다. 역할 기반 접근 제어(RBAC), attribute-based access control(ABAC), 데이터베이스 constraint, transaction limit, segregation of duties, idempotency key는 계속 필요합니다. semantic policy는 이 위에 놓이는 추가 안전층이어야 합니다. LLM 기반 판단은 ambiguity를 처리하는 데 도움이 될 수 있지만, 금액 한도·권한·승인 여부처럼 명확히 code로 표현 가능한 rule을 대체할 이유는 없습니다.

### 3층: 정상 호출의 누적이 만드는 공격을 관측하라

Google 글의 multi-turn refund 예시는 agent observability가 왜 세션 단위여야 하는지 설명합니다. 단일 tool call은 모두 규칙을 통과해도, 같은 order에 대한 반복 write, 짧은 시간의 높은 call velocity, 누적 금액이 원 주문액을 넘는 패턴은 위험합니다. Agent Anomaly Detection은 tool-call velocity, repeated writes, cumulative parameter value 같은 signal을 사용한다고 설명합니다.

이 관점은 고객 지원 환불뿐 아니라 많은 업무에 적용됩니다.

- 파일 삭제 tool을 짧은 시간에 여러 directory에 반복 호출한다.
- IAM 권한 변경이 작은 범위로 여러 번 누적돼 admin 권한이 된다.
- export API를 limit을 작게 바꿔가며 반복 호출해 대량 데이터를 빼낸다.
- procurement agent가 건별 한도 아래의 주문을 여러 번 생성한다.
- coding agent가 test 실패를 해결한다며 security check를 하나씩 끈다.

각 action은 문법적으로 유효하고, 개별 policy를 통과할 수 있습니다. 위험은 sequence에 있습니다. 따라서 agent trace는 단순 debug log가 아니라 security telemetry여야 합니다. session ID, actor, tool, target entity, argument class, result, denial rationale, approval, retry, latency, token/cost, downstream side effect를 구조화해 연결해야 합니다.

### runtime policy의 장점은 빠른 수정, 위험은 policy sprawl

Google은 이상 행동을 발견한 뒤 application code 재배포 없이 runtime policy를 추가해 차단할 수 있는 장점을 설명합니다. 이는 incident response에서 큰 이점입니다. 다만 runtime policy가 계속 쌓이면 서로 충돌하거나, 왜 특정 call이 deny됐는지 운영자가 이해하기 어려워질 수 있습니다. policy 역시 코드처럼 version, owner, test, review, expiry, rollback이 필요합니다.

권장하는 방법은 policy-as-product 운영입니다. 각 policy에 목적, 대상 agent/tool, risk hypothesis, example allow/deny case, owner, 생성일, 만료·재검토일, metric을 붙입니다. staging environment에서 replay test를 하고, false positive·false negative·override·human escalation rate를 모니터링합니다. emergency deny rule은 빠르게 적용하되, 사후에 permanent policy로 정리하거나 폐기해야 합니다.

### 개발자에게 의미

1. prompt guardrail과 tool authorization을 별개 계층으로 설계합니다.
2. write tool은 target entity, amount, actor, prior state, approval context를 policy input으로 제공합니다.
3. session-level cumulative limit, velocity limit, repeated-target rule을 둡니다.
4. deny 결과도 사용자에게 안전하게 설명할 UX와 human escalation path가 필요합니다.
5. policy 변경은 code 변경처럼 review·test·version·rollback·owner를 가집니다.

### 운영 포인트

- 모든 tool call에 immutable audit event를 남기고, prompt 원문은 필요한 경우에만 최소 보존합니다.
- `ALLOW`, `DENY`, `REQUIRE_APPROVAL`, `TIMEOUT`, `RETRY`, `OVERRIDE`를 구분해 기록합니다.
- 고위험 write action은 single-turn rule과 session cumulative rule을 모두 둡니다.
- anomaly detector는 탐지 후 알림만 보내는지, 자동 hold/kill switch까지 가능한지 runbook에 명시합니다.
- 탐지 모델의 confidence가 높아도 무제한 자동 차단으로 이어지지 않게 severity별 대응을 정의합니다.
- incident drill에서 prompt injection뿐 아니라 “정상 요청의 반복” 시나리오를 반드시 테스트합니다.

---

## 4) Claude Opus 5.5: frontier model의 스펙은 성능표가 아니라 운영 계약이 된다

**공식 출처:** [Introducing Claude Opus 5.5](https://www.anthropic.com/claude-opus-5-5)

Anthropic은 Claude Opus 5.5를 Claude 5.5 family의 첫 모델로 소개하며, 대부분의 작업에서 Claude Fable 5.1 수준의 성능을 내고 Opus 5보다 실행 비용이 40% 낮다고 설명했습니다. 발표에는 benchmark와 coding 사례뿐 아니라 external evaluator 테스트, behavioral audit, 장기·불가능 과업을 포함한 alignment test, biology·cybersecurity용 safeguard, action screening classifier, audit 가능한 sandbox, code review가 함께 포함됩니다.

이 구성이 중요한 이유는 frontier model release가 점점 제품 기능 발표와 운영 계약을 동시에 담기 때문입니다. 개발자는 “무엇을 더 잘하는가”뿐 아니라 “어떤 effort setting에서, 어떤 비용으로, 어떤 safety intervention과 fallback 아래, 어떤 task를 맡길 수 있는가”를 함께 읽어야 합니다.

### 장기 작업에서는 token price보다 task economics가 중요하다

Anthropic은 Opus 5.5의 가격을 input 1M tokens당 4달러, output 1M tokens당 20달러, cache read 0.20달러로 제시하며 Opus 5보다 낮은 비용을 설명합니다. 또한 output generation이 30% 이상 빠르다고 밝혔습니다. 이 숫자는 유용하지만, agent product에선 token 단가만으로 모델을 비교하기 어렵습니다.

장기 coding task는 plan, repository exploration, tool call, test, error analysis, patch revision, final explanation을 반복합니다. 더 저렴한 모델이 여러 번 재시도해 human review를 늘린다면 실제 cost per accepted change는 높아질 수 있습니다. 반대로 비싼 모델이 한 번에 큰 diff를 만들면 review burden과 blast radius가 증가할 수 있습니다. 따라서 조직은 모델별 input/output price 외에 다음 지표를 관측해야 합니다.

- accepted task completion rate
- task당 tool call 수와 retry 수
- test pass rate 및 regression rate
- human review 시간과 rollback 빈도
- cache hit rate와 stable-context 비율
- safety intervention, refusal, escalation rate
- task 완료까지의 wall-clock time

Anthropic이 cache read 비용을 별도로 강조한 점도 agent architecture에 시사하는 바가 큽니다. repository instruction, coding standard, API schema, domain glossary, security policy처럼 안정적인 context는 가능한 한 일정한 앞부분에 두고, user request·latest diff·log처럼 변동하는 context는 뒤에 두는 설계가 필요합니다. cache는 billing optimization이면서 context discipline의 결과입니다.

### 더 긴 autonomy는 더 강한 action boundary를 요구한다

Anthropic은 Opus 5.5가 긴 작업과 자율적 수행에 강하다고 소개하면서, enterprise agent가 여러 시간 autonomous하게 실행될 때 의도대로 동작하는지 알아야 한다고 설명합니다. 이를 위해 action 전에 classifier가 screening하고, security team이 audit할 수 있는 open-source sandbox, merge 전 vulnerability를 잡는 code review를 언급합니다.

여기서 주목할 점은 안전 장치가 model prompt 안에만 있지 않다는 것입니다. model behavior, action classifier, sandbox, code review라는 여러 층이 결합됩니다. production agent를 만들 때도 같은 원칙이 필요합니다.

1. **Model layer:** 모델에게 역할·금지 행위·목표를 명확히 준다.
2. **Tool layer:** 읽기·쓰기·네트워크·배포 능력을 최소 권한으로 분리한다.
3. **Policy layer:** 요청의 actor·resource·amount·context에 따라 allow/deny/approval을 판정한다.
4. **Sandbox layer:** agent의 filesystem·network·process·secret 접근을 제한한다.
5. **Review layer:** high-impact diff와 state change에 test, scan, human approval을 둔다.
6. **Observation layer:** prompt, tool trace, artifact, result, denial, cost를 연결해 재현 가능하게 남긴다.

이 중 하나만 강해도 충분하지 않습니다. 모델이 prompt injection에 강해도 overly broad cloud credential을 가진 tool은 위험합니다. sandbox가 있어도 unsigned artifact를 user workspace에 넣으면 위험합니다. code review가 있어도 agent가 production data를 이미 변경했다면 늦습니다. defense in depth는 AI 특유의 개념이 아니라, AI가 software supply chain과 business workflow에 들어가면서 다시 중요해지는 오래된 원칙입니다.

### safety intervention은 성능 실패가 아니라 운영 신호다

Anthropic의 발표은 benchmark 결과를 production safeguards가 활성화된 상태와 연결해 설명하고, biology·cybersecurity capability에 대해 verification program을 통한 접근을 언급합니다. 개발팀은 이런 intervention을 단순히 “모델이 못 했다”는 오류로 처리해서는 안 됩니다. 정상적인 safety intervention은 policy가 의도대로 동작했다는 신호일 수 있습니다. 반대로 과도한 intervention은 legitimate workflow를 막는 false positive일 수 있습니다.

따라서 observability dashboard에는 completion rate만 아니라 refusal/intervention의 이유와 결과가 들어가야 합니다. 어떤 업무, 어떤 customer tier, 어떤 locale, 어떤 tool, 어떤 risk class에서 intervention이 발생하는지 봐야 합니다. 이 데이터가 있어야 product team은 workflow를 redesign하거나, verification path를 만들거나, human escalation을 개선할 수 있습니다.

### 개발자에게 의미

1. frontier model의 발표 수치보다 자신의 task set에서 completion·quality·review·cost를 함께 평가합니다.
2. long-running agent에는 max duration, budget, step/tool-call limit, heartbeat, cancellation, fallback을 둡니다.
3. action screening과 sandbox를 모델 system prompt의 보조 수단이 아니라 독립 enforcement layer로 둡니다.
4. capability가 높은 domain에는 verified-user·approved-workspace·human review 같은 access tier를 설계합니다.
5. safety intervention을 product metric으로 보고, false positive와 bypass attempt를 정기적으로 검토합니다.

### 운영 포인트

- preview/new model은 production critical path에 바로 고정하지 말고 fallback model을 준비합니다.
- task마다 maximum spend와 maximum wall-clock time을 정의합니다.
- coding agent의 diff size, touched-file class, test requirement에 따른 approval rule을 둡니다.
- model upgrade 시 prompt cache, tool schema, output parser, safety policy regression test를 함께 실행합니다.
- provider가 제공하는 system card·safeguard 문서는 vendor claim으로 읽되, 내부 eval과 red-team으로 재검증합니다.

---

## 네 발표가 함께 보여 주는 아키텍처: agent control plane의 다섯 층

오늘 확인한 공식 발표들을 하나의 제품 구조로 옮기면 다음 다섯 층을 생각할 수 있습니다.

1. **Capability surface — API와 tool contract**
   - 기존 REST API를 어떤 MCP tool로 노출할지, schema와 description을 어떻게 설계할지 결정합니다.
2. **Execution placement — cloud·local·hybrid**
   - 어떤 데이터와 작업을 cloud model, local model, deterministic service에 맡길지 결정합니다.
3. **Decision and policy — authorization before action**
   - model의 제안과 business rule을 분리하고, write action은 실행 전에 policy를 통과시킵니다.
4. **Runtime isolation — sandbox와 least privilege**
   - filesystem, network, credential, process, database access를 task에 필요한 최소 범위로 제한합니다.
5. **Observation and response — trace, anomaly, review**
   - 개별 call과 multi-turn sequence를 기록하고, anomaly를 탐지하며, 사람이 개입하고 policy를 개선합니다.

이 구조에서 모델은 2번과 3번 사이에서 reasoning을 제공하는 중요한 component지만, 전체 system의 policy owner가 되어서는 안 됩니다. 모델은 목표를 해석하고 후보 action을 제안할 수 있습니다. 그러나 실제 capability를 가진 gateway, runtime, database, deployment system은 deterministic하게 권한을 집행해야 합니다.

### 예시: 고객 지원 환불 agent를 안전하게 만드는 흐름

1. agent는 read-only order lookup tool로 주문을 확인합니다.
2. 모델은 환불 가능성을 설명하고 `draft_refund_request`를 생성합니다.
3. policy engine은 상품 type, amount, customer history, 승인 규칙, session cumulative amount를 평가합니다.
4. low-risk request는 제한된 `execute_refund` capability를 받을 수 있고, 고위험 request는 manager approval queue로 갑니다.
5. tool call과 policy verdict, approval, ledger result는 correlation ID로 저장됩니다.
6. 같은 order에 반복 refund, 높은 velocity, unusual amount pattern은 anomaly detector가 hold합니다.
7. incident가 발생하면 policy를 우선 조정하고, code/model/prompt 변경은 검증 뒤 배포합니다.

이 흐름은 MCP와 local model 여부에 상관없이 적용됩니다. MCP는 tool을 연결하는 protocol이고, local model은 실행 위치의 선택지이며, runtime governance는 그 둘이 실제 business system과 만날 때 필요한 운영 규율입니다.

---

## 개발 조직을 위한 30일 실행 체크리스트

### 1주차: 도구와 데이터 경계 inventory

- 현재 agent가 읽고 쓰는 API, database, filesystem, SaaS integration을 목록화합니다.
- 각 tool에 read/write/delete/deploy/financial/identity/data-export risk label을 붙입니다.
- tool description과 JSON schema가 실제 operation의 side effect를 정확히 표현하는지 검토합니다.
- cloud에 보내는 data와 local에만 남겨야 할 data를 classification합니다.
- prompt, tool trace, generated artifact, audit log의 retention 위치를 문서화합니다.

### 2주차: 최소 권한과 승인 경로 구현

- read-only toolset과 write toolset을 분리합니다.
- write tool은 draft/approve/execute로 나눌 수 있는지 검토합니다.
- service account를 agent별·environment별로 분리하고 broad admin token을 제거합니다.
- session, task, tool별 budget·time·call limit을 설정합니다.
- high-impact action의 human approval UI와 escalation SLA를 만듭니다.

### 3주차: 관측과 회복성 구축

- actor, session, prompt version, model, tool, argument class, policy verdict, result, cost를 trace로 연결합니다.
- retry와 idempotency key를 적용해 ambiguous failure의 중복 side effect를 줄입니다.
- multi-turn cumulative limit, repeated-target write, anomalous velocity alert를 구현합니다.
- cancellation, kill switch, rollback, manual recovery runbook을 연습합니다.

### 4주차: eval·red team·운영 리뷰

- 정상 task뿐 아니라 prompt injection, schema abuse, repeated small writes, sensitive-data exfiltration, tool timeout을 테스트합니다.
- false positive·false negative·approval delay·human override를 metric으로 봅니다.
- policy owner와 review cadence를 정하고, 임시 emergency rule의 만료일을 둡니다.
- model·gateway·local runtime update마다 regression suite를 실행합니다.

이 체크리스트의 목적은 거대한 platform을 한 번에 만드는 것이 아닙니다. 가장 위험하거나 가장 가치 있는 workflow 하나를 골라 tool contract, policy, trace, approval, recovery를 끝까지 연결해 보는 것입니다. 한 workflow에서 증명된 패턴만 다음 workflow로 확장해야 policy sprawl과 hidden privilege를 줄일 수 있습니다.

---

## 운영자가 매주 확인할 지표

AI agent 운영은 “요청 수”만 봐서는 부족합니다. 다음 지표를 함께 보면 capability, quality, cost, safety의 trade-off를 더 잘 이해할 수 있습니다.

- **Task completion:** 실제 업무가 성공적으로 끝난 비율. 단순 model response success와 분리합니다.
- **Human handoff:** 승인·에스컬레이션·manual recovery로 넘어간 비율과 이유.
- **Policy verdict:** allow, deny, require approval, timeout, override의 분포와 변화.
- **Tool-risk mix:** read/write/delete/deploy/export 등 risk class별 호출 비중.
- **Session behavior:** 평균 tool call 수, duration, retry, repeated-target writes, cumulative amount.
- **Quality:** test pass rate, post-merge regression, rollback, customer correction.
- **Cost:** task당 model token, cache ratio, compute, human review time, failed-run waste.
- **Security:** prompt injection detection, blocked action, anomaly finding, credential/egress policy violation.

지표는 감시 자체가 목적이 아닙니다. 예를 들어 deny rate가 높으면 model이 위험한 것일 수도 있지만, tool description이 모호하거나 approval path가 없어서 정당한 요청이 막히는 것일 수도 있습니다. completion rate가 높아도 agent가 과도한 권한으로 빠르게 일을 처리하고 있을 수 있습니다. metric은 맥락과 trace를 함께 읽을 때만 운영 의사결정에 도움이 됩니다.

---

## 결론: agent 시대의 경쟁력은 “연결”보다 “통제 가능한 실행”이다

MCP, local model, frontier coding model은 모두 강력한 기술 변화입니다. 하지만 실제 제품 차별화는 protocol 지원 여부나 benchmark 한 줄에서 끝나지 않습니다. 기존 API의 정책을 재사용해 안전하게 agent tool로 만들 수 있는가, 민감한 작업을 적절한 data boundary 안에 둘 수 있는가, 모델의 제안을 실행 전 business policy로 걸러낼 수 있는가, 세션 전체의 이상 행동을 관측하고 회복할 수 있는가가 더 중요한 질문입니다.

오늘의 공식 발표은 이 방향을 분명하게 보여 줍니다. API Gateway의 MCP 지원은 capability surface를 기존 gateway governance에 붙입니다. Antigravity의 local support는 execution placement를 cloud-only에서 hybrid로 넓힙니다. zero-trust guidance는 intent와 multi-turn behavior를 runtime에서 봐야 한다고 말합니다. Claude Opus 5.5 발표은 강한 장기 agent의 성능과 함께 screening, sandbox, verification, cost control을 스펙으로 제시합니다.

개발팀의 다음 단계는 더 많은 tool을 무작정 연결하는 일이 아닙니다. 가장 작은 high-value workflow 하나를 정하고, **명확한 tool contract → 최소 권한 → 실행 전 policy → sandbox → trace와 anomaly detection → human approval과 rollback**을 하나의 폐루프로 완성하는 일입니다. 이 루프가 없는 autonomy는 데모에서는 인상적일 수 있어도, production에서는 비용·보안·신뢰의 부채가 되기 쉽습니다.

---

## 설계 결정 가이드: 네 가지 흔한 선택을 어떻게 판단할까

### “기존 API를 MCP로 열 것인가, 전용 agent backend를 새로 만들 것인가”

기존 API Gateway 경로를 MCP로 확장하는 선택은 authentication, quota, observability, change management가 이미 성숙한 조직에서 특히 강합니다. 주문 조회, account lookup, inventory search처럼 contract가 안정적이고 read 중심인 operation은 gateway 재사용의 이점이 큽니다. 반대로 agent 특유의 long-running job, asynchronous artifact, human-in-the-loop state machine, tool-result summarization이 핵심인 workflow는 전용 orchestration backend가 더 적합할 수 있습니다.

중요한 것은 둘 중 하나를 절대 원칙으로 고르는 일이 아닙니다. API Gateway는 capability exposure와 edge policy를 담당하고, orchestration service는 task state와 approval flow를 담당하는 식으로 책임을 나눌 수 있습니다. 어떤 구조든 API의 source of truth, authorization owner, audit record, retry owner가 중복되지 않게 해야 합니다. 같은 환불 operation을 REST path와 별도 MCP server가 각각 다른 validation으로 처리하는 순간, 정책 drift가 생깁니다.

### “로컬 모델을 쓸 것인가, 클라우드 모델을 쓸 것인가”

이 질문도 이분법으로 답하기 어렵습니다. local execution이 유리한 조건은 명확합니다. source code, 개인 정보, 내부 ticket, raw log처럼 egress가 제한된 데이터가 있고, 반복적 analysis나 test처럼 model capability 요구가 과도하게 높지 않으며, 적절한 hardware와 endpoint management 역량이 있는 경우입니다. cloud execution은 최신 모델 capability, shared reliability, rapid update, 중앙화된 capacity가 중요하고 data policy가 허용하는 작업에서 강점이 있습니다.

hybrid 구조는 두 장점을 기계적으로 더하는 방식이 아니라 contract를 정하는 방식이어야 합니다. cloud가 plan을 만들 때 raw source를 보지 않아도 되는지, local executor가 summary를 반환할 때 secret·PII·code fragment를 제거하는지, local failure가 cloud retry를 무한히 유발하지 않는지, 사용자가 offline 상태일 때 approval과 audit가 어떻게 남는지를 정의해야 합니다. 이 contract가 없으면 hybrid는 단지 디버깅하기 어려운 분산 시스템이 됩니다.

### “자연어 policy를 어디까지 믿을 것인가”

Semantic policy는 “디지털 소프트웨어의 환불은 manager approval이 필요하다”처럼 business intent를 설명하는 데 유용합니다. 그러나 통화 금액, 권한 role, legal retention, 상태 전이처럼 명확하게 코드로 표현되는 rule은 deterministic control에 남겨야 합니다. 가장 안전한 구조는 hard rule과 semantic rule을 계층화하는 것입니다.

- hard rule: actor가 해당 tenant에 속하는가, amount가 absolute limit을 넘는가, approval token이 유효한가, record state가 전이 가능한가
- semantic rule: 요청의 실제 목적이 policy의 취지와 맞는가, tool description과 user intent가 충돌하지 않는가, 우회 표현이 있는가
- anomaly rule: 동일 target에 대한 반복 action, 비정상 속도, 누적 exposure가 발생하는가

세 종류의 rule을 한 모델에게 모두 맡기면 explainability와 reliability가 떨어집니다. 반대로 모든 예외를 hard-coded rule로 만들면 policy maintenance가 불가능해집니다. 경계가 분명한 rule은 code로, context-dependent한 판단은 semantic policy로, sequence-level 위험은 anomaly detection으로 두는 편이 운영에 적합합니다.

### “언제 사람이 승인해야 하는가”

human-in-the-loop은 모든 tool call에 버튼을 누르게 만드는 것이 아닙니다. 그렇게 하면 agent의 장점이 사라지고 운영자는 alert fatigue에 빠집니다. 승인 조건은 action의 되돌릴 수 없음, 금전·권한·개인정보 영향, confidence, novelty, cumulative risk를 기준으로 설계해야 합니다.

예를 들어 read-only search와 deterministic report generation은 자동 실행할 수 있습니다. code patch는 test가 통과해도 merge 전 review를 요구할 수 있습니다. access grant, financial transfer, production deploy, bulk export는 stronger approval을 요구해야 합니다. 같은 action이라도 sandbox environment에서는 자동, production에서는 two-person approval이라는 식의 environment-sensitive policy가 필요합니다.

승인 화면에는 “모델이 추천했다”만 표시하면 안 됩니다. 영향을 받는 resource, proposed change, prior actions, policy result, test evidence, rollback path, time/budget 사용량을 함께 보여 줘야 사람이 실질적인 판단을 할 수 있습니다. human approval은 책임을 넘기는 UI가 아니라, 더 좋은 evidence로 인간의 결정을 돕는 control이어야 합니다.

---

## 실패 시나리오별 운영 원칙

### 1. agent가 tool을 잘못 선택했다

가능한 원인은 tool description의 모호함, 유사한 tool name, context 부족, model routing 오류입니다. 즉시 모든 autonomy를 끄기 전에 trace를 통해 모델이 어떤 description과 argument를 보고 선택했는지 확인해야 합니다. 개선 순서는 대개 tool naming/description 정리, capability group 축소, clarification step 추가, safe default 설정입니다. 비슷한 write tool 여러 개를 동시에 노출하는 것보다, agent의 현재 task에 맞는 작은 toolset을 동적으로 제공하는 편이 선택 오류를 줄일 수 있습니다.

### 2. tool은 맞지만 argument가 위험했다

이 경우 schema validation과 business policy의 책임입니다. JSON type check는 `amount: 120`이 숫자인지 확인하지만, 120달러 환불이 해당 order와 customer에게 타당한지는 확인하지 못합니다. argument validator는 format·range·enum을, policy engine은 resource ownership·state·amount·approval을, anomaly detector는 반복성과 누적을 맡도록 분리해야 합니다. 실행 전 dry-run 또는 preview result를 만들 수 있는 operation이라면 high-risk tool에 우선 도입할 가치가 큽니다.

### 3. agent가 멈추지 않고 반복했다

runaway loop는 model failure만이 아니라 orchestration failure입니다. max steps, max tool calls, max spend, max duration, retry backoff, circuit breaker, per-target write limit이 있어야 합니다. agent가 동일 error를 반복해서 읽는 상황에서는 model을 바꾸는 것보다 tool error message를 구조화하고, retryable/non-retryable을 구분하며, explicit stop condition을 넣는 것이 더 효과적일 수 있습니다. 운영자는 session을 즉시 취소할 수 있어야 하고, cancellation 뒤 수행된 side effect를 reconciliation하는 runbook도 가져야 합니다.

### 4. local execution이 민감 정보를 의도치 않게 노출했다

로컬 환경에서는 log file, crash dump, shell history, telemetry, editor extension, local inference server가 모두 egress 경로가 될 수 있습니다. incident 대응은 source file 삭제 같은 임시 조치에 그치지 않고, 어떤 process가 어떤 data를 읽었는지, network connection이 있었는지, artifact가 backup·sync folder로 복제됐는지를 확인해야 합니다. 평소에는 workspace mount 최소화, secret redaction, local endpoint authentication, telemetry sampling policy, encrypted storage, explicit cleanup을 갖춰야 합니다.

### 5. security policy가 정상 업무를 막았다

false positive는 단순 불편이 아니라 shadow AI를 만드는 원인입니다. 사용자가 공식 agent를 우회해 개인 계정 도구를 쓰기 시작하면 조직은 더 적은 통제를 갖게 됩니다. deny event에는 안전한 수준의 rationale과 escalation path를 제공해야 합니다. 동시에 override는 무제한 bypass가 아니라 reason, approver, expiry, audit을 가진 time-bound exception이어야 합니다. policy quality는 차단 건수보다 legitimate work를 얼마나 안전하게 통과시키는지로 평가해야 합니다.

---

## Source Links

- [Google Cloud API Gateway: Turn your REST APIs into MCP tools](https://developers.googleblog.com/turn-your-rest-apis-into-mcp-tools-with-google-cloud-api-gateway/)
- [Google: Introducing Support for Local AI Models in the Antigravity SDK](https://developers.googleblog.com/introducing-support-for-local-ai-models-in-the-antigravity-sdk/)
- [Google: Build zero-trust AI agents that judge intent, not just syntax](https://developers.googleblog.com/build-zero-trust-ai-agents-that-judge-intent-not-just-syntax/)
- [Anthropic: Introducing Claude Opus 5.5](https://www.anthropic.com/claude-opus-5-5)
- [OpenAI News index](https://openai.com/news/)
- [Anthropic News index](https://www.anthropic.com/news)
- [Google for Developers Blog](https://developers.googleblog.com/)
