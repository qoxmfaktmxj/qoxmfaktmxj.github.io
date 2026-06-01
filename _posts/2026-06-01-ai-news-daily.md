---
layout: post
title: "2026년 6월 1일 AI 뉴스: Rosalind Biodefense, AWS Frontier Agents GA, 생성형 AI SRE, Google ADK 장기 실행 에이전트, Pixel 온디바이스 AI, Copilot 도입 지표"
date: 2026-06-01 11:30:00 +0900
categories: [ai-daily-news]
tags: [ai, news, openai, rosalind, biodefense, gpt-rosalind, aws, frontier-agents, security-agent, devops-agent, sre, resilience-hub, google, adk, long-running-agents, litert, on-device-ai, github, copilot, metrics, ai-adoption, developers, operations]
permalink: /ai-daily-news/2026/06/01/ai-news-daily.html
---

# 오늘의 AI Daily News

## 작성 기준

2026년 6월 1일 11:30 KST 기준으로 공개 웹, RSS, 공식 발표, 공식 제품 페이지를 확인해 정리했습니다. `web_search`는 현재 Gateway의 Gemini 검색 API 키가 없어 `missing_gemini_api_key` 오류를 반환했습니다. 그래서 OpenAI News, AWS News Blog, AWS Machine Learning Blog, AWS Security Blog, AWS DevOps/Management Tools Blog, Google Developers Blog, GitHub Changelog RSS 같은 공식 index와 개별 공식 발표 URL을 `web_fetch`로 직접 확인했습니다.

비공식 루머, 소셜 미디어 요약, 제3자 해설은 본문 근거로 사용하지 않았습니다. 공식 발표 중 일부는 5월 중순 발표지만, 오늘 확인한 공식 index와 최근 agentic AI 흐름에서 개발자·운영팀이 바로 반영해야 할 내용이라 함께 다룹니다. 어제 AI Daily News에서 이미 다룬 OpenAI 평가·거버넌스, Google Tunix, GitHub Copilot 모델 제공, OpenSearch agentic search 흐름과 중복되는 내용은 최소화하고, 오늘은 **trusted access, frontier agent GA, 보안/운영 agent, resilience governance, long-running agent architecture, on-device AI deployment, adoption analytics**에 초점을 맞췄습니다.

## 오늘의 핵심 한 문장

**2026년 6월 1일의 AI 뉴스는 “모델이 답을 잘한다”에서 “검증된 주체에게만 위험한 capability를 열고, 보안·운영·모바일·개발 조직 지표 안에서 agent가 장시간 실제 일을 수행하도록 통제한다”로 이동하고 있음을 보여 줍니다. OpenAI의 Rosalind Biodefense는 trusted access와 defensive acceleration을, AWS frontier agents는 보안 테스트와 SRE 운영의 autonomous execution을, AWS Resilience Hub는 생성형 AI 기반 resilience governance를, Google ADK는 pause/resume 가능한 durable agent architecture를, Google Tensor SDK는 edge AI 배포면을, GitHub Copilot metrics는 AI 도입 성숙도 측정을 각각 전면에 세웠습니다.**

---

## 한눈에 보는 Top News

1. **OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access**  
   - 공식 확인: 2026-05-29  
   - 핵심: OpenAI가 Rosalind Biodefense를 열고, 공중보건·바이오디펜스 임무를 가진 검증된 기관에 GPT‑Rosalind 접근을 확장했다.  
   - 개발자 의미: AI가 민감한 과학 영역에 들어갈 때 핵심은 모델 호출 능력이 아니라 접근 자격, 사용 목적, 감사 가능성, 결과 검증, dual-use risk boundary를 제품 구조로 강제하는 것이다.

2. **AWS frontier agents: Security Agent와 DevOps Agent 일반 제공**  
   - 공식 확인: 2026-06-01 KST 확인  
   - 핵심: AWS가 Security Agent와 DevOps Agent를 frontier agents로 일반 제공하며 보안 테스트와 운영 대응을 agentic workflow로 확장했다.  
   - 개발자 의미: agent가 보안과 운영의 실제 변경면에 가까워질수록 개발자는 MCP, repository indexing, observability correlation, private connection, approval gate, remediation PR workflow를 기본 설계 요소로 봐야 한다.

3. **AWS Security Agent: on-demand penetration testing GA**  
   - 공식 확인: 2026-06-01 KST 확인  
   - 핵심: AWS Security Agent가 멀티클라우드·온프레미스까지 포함한 on-demand penetration testing을 일반 제공한다.  
   - 개발자 의미: 보안 자동화가 SAST/DAST scan 결과 나열에서 “코드와 문서를 이해한 attack chain 검증”으로 이동하면, 개발팀은 threat model과 architecture doc을 실제 실행 가능한 보안 컨텍스트 자산으로 관리해야 한다.

4. **AWS Resilience Hub: 생성형 AI 기반 SRE resilience journey**  
   - 공식 확인: 2026-06-01 KST 확인  
   - 핵심: AWS가 Resilience Hub를 확장해 application model, dependency discovery, generative AI-powered failure mode analysis, modular resilience policies, organization-wide reporting을 묶었다.  
   - 개발자 의미: 개발자는 resilience를 후순위 문서가 아니라 application model, dependency graph, failure mode catalog, policy-as-code, test evidence로 설계해야 한다.

5. **Google ADK long-running agents: pause, resume, durable state**  
   - 공식 확인: 2026-05-12  
   - 핵심: Google Developers Blog가 ADK로 장기 실행 agent를 구현하는 패턴을 공개하며 stateless chatbot에서 durable workflow agent로의 전환을 강조했다.  
   - 개발자 의미: agent 제품을 만들 때 “대화 기억”보다 “명시적 상태 전이”가 우선이다. 장기 업무에서는 state machine, persistence, event resume, eval fixture가 product reliability를 좌우한다.

6. **Google Tensor SDK Beta with LiteRT: Pixel on-device AI 개발면 확대**  
   - 공식 확인: 2026-05-19  
   - 핵심: Google Tensor ML SDK가 LiteRT 통합과 100개 이상 model garden을 통해 Pixel 10 계열 on-device AI 개발을 Beta로 확장했다.  
   - 개발자 의미: 프라이버시·지연시간·오프라인 UX가 중요한 앱은 서버 LLM 호출만 보지 말고, 작은 모델과 edge runtime을 제품 아키텍처의 1급 선택지로 다뤄야 한다.

7. **GitHub Copilot usage metrics API: AI adoption phase cohort**  
   - 공식 확인: 2026-05-29  
   - 핵심: GitHub가 Copilot usage metrics API에 AI adoption phase cohort를 추가해 active user 수를 넘어 code-first, agent-first, multi-agent 성숙도를 측정하게 했다.  
   - 개발자 의미: 개발 조직의 AI 도입은 “seat를 샀는가”가 아니라 “개발자가 어떤 표면에서 어떤 workflow를 바꾸었는가”로 측정해야 한다.

---

## 배경: 2026년의 AI 제품은 “에이전트 운영체계”를 요구한다

지난 몇 년간 AI 도입의 기본 질문은 비교적 단순했습니다. 어떤 모델을 쓸 것인가, 어떤 API가 더 싸고 빠른가, 어떤 benchmark가 더 높은가, prompt를 어떻게 쓰면 답이 좋아지는가가 중심이었습니다. 그러나 오늘 확인한 공식 발표들을 하나로 묶어 보면 질문이 달라졌습니다. 이제 중요한 질문은 “AI가 조직 안에서 어떤 권한으로, 어떤 시간 범위 동안, 어떤 증거를 남기며, 어떤 실패 복구 절차를 거쳐 실제 일을 끝내는가”입니다.

OpenAI의 Rosalind Biodefense는 capability가 강해질수록 아무에게나 공개하는 것이 아니라 trusted developer, approved mission, public-health benefit, safeguards를 함께 설계해야 함을 보여 줍니다. AWS의 frontier agents는 보안과 운영처럼 실제 피해와 비용이 큰 영역에서 agent가 다단계 작업을 독립적으로 수행할 수 있음을 전면에 내세웁니다. Google ADK long-running agent 예시는 agent가 며칠 또는 몇 주 동안 기다렸다가 외부 이벤트로 재개되는 업무에서 단순 conversation history가 얼마나 취약한지를 설명합니다. Google Tensor SDK Beta는 모든 지능이 서버에서만 돌지 않고, Pixel 단말의 TPU와 LiteRT 배포 흐름으로 내려오는 방향을 보여 줍니다. GitHub Copilot cohort metric은 개발 조직의 AI 도입을 seat count가 아니라 workflow maturity로 보기 시작했음을 의미합니다.

이 변화는 개발자에게 단순한 도구 사용법 이상의 숙제를 줍니다. 이제 AI 기능을 만든다는 것은 모델 API를 감싸는 wrapper를 만드는 일이 아닙니다. 제품에는 state machine이 있어야 하고, trace와 audit log가 있어야 하며, tool permission boundary가 있어야 하고, long-running task의 pause/resume semantics가 있어야 하며, 보안·운영·비용·품질 지표가 workflow별로 분해되어야 합니다. 운영팀 역시 AI를 “새로운 SaaS”로만 구매하면 안 됩니다. AI agent는 수시간 또는 수일 동안 독립적으로 움직일 수 있고, 외부 시스템을 읽고 쓰며, 비용과 위험을 빠르게 증폭할 수 있습니다. 따라서 AI 운영은 reliability engineering, security engineering, platform engineering, governance가 합쳐진 영역이 됩니다.

오늘 글은 각 공식 발표의 사실을 정리한 뒤, 개발자와 운영팀이 바로 점검할 수 있는 설계 질문과 운영 포인트로 확장합니다. 핵심은 하나입니다. **AI agent를 도입한다는 것은 모델을 도입하는 것이 아니라, 모델이 안전하게 일할 수 있는 조직의 실행면을 설계하는 것입니다.**

## 오늘의 키워드 맵

- **Trusted access:** capability가 민감하거나 위험할수록 사용자, 목적, 데이터, 출력, 감사 범위를 통제하는 접근 모델입니다.
- **Frontier agent:** 단일 응답을 넘어 목표 달성까지 장시간 독립적으로 작업하고, 여러 도구를 사용하며, 대규모 동시 작업을 처리하는 agent 유형입니다.
- **Attack-chain validation:** 취약점을 개별 finding으로 보지 않고 실제 exploit path로 연결해 검증하는 보안 자동화 방식입니다.
- **Resilience governance:** 애플리케이션 모델, 의존성 그래프, failure mode, policy, reporting을 묶어 회복탄력성을 조직 단위로 운영하는 방식입니다.
- **Durable state:** conversation history가 아니라 명시적 상태, checkpoint, event signal로 agent workflow를 이어 가는 구조입니다.
- **Edge AI:** 모델을 단말에서 실행해 지연시간, 프라이버시, 오프라인 UX를 개선하는 배포 방식입니다.
- **AI adoption cohort:** AI 도구를 얼마나 샀는지가 아니라 개발자가 어떤 workflow 단계까지 쓰는지 측정하는 성숙도 지표입니다.

---

## 1) OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access

**공식 확인/발표 기준:** 2026-05-29  
**공식 출처:** https://openai.com/index/strengthening-societal-resilience-with-rosalind-biodefense/  
**분석 렌즈:** biosecurity / trusted access / defensive acceleration / safety governance

### 공식 발표에서 확인한 핵심 사실

- OpenAI는 방어 목적의 생명과학 AI 활용을 위해 Rosalind Biodefense 프로그램을 발표했다.
- 프로그램은 trusted developers가 GPT‑Rosalind를 활용해 pandemic preparedness, early detection, screening, epidemiological modeling, diagnostics, medical countermeasure 개발을 돕는 애플리케이션을 만들도록 지원한다.
- OpenAI는 select U.S. government and allied partners 가운데 public health와 biodefense mission이 승인된 기관에 GPT‑Rosalind trusted access를 확장한다고 밝혔다.
- 공식 글은 Fourth Eon Biosecurity, Lawrence Livermore National Laboratory, Johns Hopkins Applied Physics Laboratory, CEPI 같은 초기 협력 사례를 언급한다.
- OpenAI는 July 2025의 ChatGPT agent를 biology 영역 High Capability로 취급했고, Preparedness Framework, bio-specific capability assessments, monitoring, enforcement, expert red teaming, security controls를 함께 운영해 왔다고 설명한다.

### 왜 중요한가

OpenAI가 Rosalind Biodefense를 열고, 공중보건·바이오디펜스 임무를 가진 검증된 기관에 GPT‑Rosalind 접근을 확장했다. 이 발표의 핵심은 단순한 기능 추가가 아니라 AI 제품의 운영 기준이 바뀌고 있다는 점입니다. 이제 AI는 질문에 답하는 보조 수단에 머물지 않습니다. 보안 테스트를 실행하고, 장애 원인을 조사하고, 장기간 대기하다가 외부 이벤트로 다시 깨어나고, 민감한 과학 연구 흐름에 참여하고, 모바일 단말에서 개인 데이터를 로컬로 처리하며, 개발 조직의 workflow 자체를 바꿉니다.

이 변화가 위험한 이유는 agent가 빠르고 끈질기며 도구를 사용할 수 있기 때문입니다. 사람은 피곤하면 멈추고, 권한이 없으면 요청하고, 실수하면 동료가 눈치챌 시간이 있습니다. agent는 잘못 설계하면 잘못된 전제를 아주 빠르게 확장하고, 여러 시스템을 동시에 건드리며, 비용과 위험을 눈에 띄지 않게 누적할 수 있습니다. 반대로 잘 설계하면 사람보다 훨씬 일관되게 증거를 남기고, 반복적인 조사와 검증을 자동화하고, 취약점과 장애의 긴 꼬리를 줄일 수 있습니다.

따라서 이 발표를 읽을 때 “어떤 모델이 나왔는가”보다 “이 capability를 운영 가능한 시스템으로 만들기 위해 어떤 control plane이 필요한가”를 봐야 합니다. control plane에는 identity, permission, state, trace, eval, budget, approval, rollback, source grounding, compliance evidence가 포함됩니다.

### 개발자에게 의미

AI가 민감한 과학 영역에 들어갈 때 핵심은 모델 호출 능력이 아니라 접근 자격, 사용 목적, 감사 가능성, 결과 검증, dual-use risk boundary를 제품 구조로 강제하는 것이다.

개발자 관점에서 가장 중요한 변화는 AI 기능의 중심이 prompt engineering에서 system design으로 이동한다는 점입니다. prompt는 여전히 중요하지만, prompt만으로 production 문제를 해결할 수는 없습니다. agent가 어떤 상태에 있는지, 어떤 tool을 호출할 수 있는지, 어떤 외부 이벤트가 들어오면 어떤 checkpoint에서 재개해야 하는지, 어떤 결과가 사람의 승인을 받아야 하는지를 코드와 데이터 모델로 명시해야 합니다.

특히 이 발표는 다음과 같은 설계 전환을 요구합니다.

- **대화 로그 중심에서 상태 모델 중심으로:** 장기 workflow에서는 대화 전체를 다시 읽는 방식보다 명시적 state machine이 안정적입니다.
- **도구 연결 중심에서 권한 경계 중심으로:** tool을 많이 붙이는 것보다 tool scope, approval requirement, audit trail이 먼저입니다.
- **정확도 중심에서 회복 가능성 중심으로:** 모델이 틀릴 수 있음을 전제로 correction capture, retry policy, rollback path를 설계해야 합니다.
- **개별 기능 중심에서 운영 루프 중심으로:** release 이후에 trace, eval, feedback, cost, incident를 계속 순환시키는 구조가 필요합니다.

### 운영 포인트

운영팀은 생명과학 AI를 단순 SaaS 도입으로 보지 말고, 승인된 사용자·승인된 과업·승인된 데이터·승인된 출력 형태를 분리한 trusted access control plane으로 관리해야 한다.

운영팀은 AI 기능을 모니터링할 때 전통적인 latency와 error rate만 보면 부족합니다. 다음 지표가 함께 필요합니다.

- tool call success/failure rate
- human approval 요청 수와 승인/거절 비율
- correction rate와 repeated failure cluster
- agent run duration과 idle/resume latency
- cost per completed workflow
- unsafe action blocked count
- stale-source answer rate
- evaluation pass rate와 regression failure
- rollback 또는 compensation action 발생 수
- permission denied가 실제로 보호한 사례

### 아키텍처 관점의 해석

이 발표를 제품 아키텍처로 번역하면 최소한 다음 계층이 필요합니다.

1. **Model gateway:** 모델 선택, rate limit, budget, logging, fallback을 담당합니다.
2. **Tool gateway:** 외부 시스템 접근을 도구 단위로 통제하고, 입력 검증과 결과 redaction을 수행합니다.
3. **Policy engine:** 누가, 어떤 목적, 어떤 데이터, 어떤 action을 허용받는지 판단합니다.
4. **State store:** 장기 workflow의 checkpoint, pending signal, step transition을 저장합니다.
5. **Trace store:** reasoning trace가 아니라 operational trace, tool call, source, decision, approval evidence를 저장합니다.
6. **Eval runner:** golden workflow, adversarial case, regression suite를 지속적으로 실행합니다.
7. **Human review console:** 사람의 승인, 수정, escalation, rollback을 담당합니다.
8. **Reporting layer:** adoption, quality, cost, risk, resilience metric을 조직 단위로 보여 줍니다.

### 바로 적용할 설계 질문

1. 이 기능이 읽을 수 있는 데이터와 절대 읽으면 안 되는 데이터는 무엇인가?
2. 이 기능이 쓸 수 있는 시스템과 propose-only로 남겨야 하는 시스템은 무엇인가?
3. 결과가 틀렸을 때 사람이 어디에서 수정하고, 그 수정이 어떤 평가 데이터로 저장되는가?
4. agent가 같은 작업을 재시도할 때 idempotency key와 중복 실행 방지는 어떻게 보장되는가?
5. 모델이 호출한 tool, tool input, tool output, 최종 action은 어느 수준까지 audit log로 남는가?
6. 비용이 폭증하는 조건은 무엇이며, per-user/per-workflow/per-agent budget은 어디에서 차단되는가?
7. 승인된 사용자와 승인된 목적을 분리해 검증하는가, 아니면 로그인만 통과하면 모든 기능을 쓰는가?
8. 외부 공식 문서나 내부 지식이 stale해졌을 때 agent는 어떤 방식으로 최신성을 확인하는가?
9. 장시간 대기하는 workflow에서 thread나 process를 붙잡고 있지 않은가?
10. rollback 또는 compensation action이 필요한 실패는 어떤 class로 분류되는가?

### 실무 적용 체크리스트

- [ ] 1. OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access 관련 기능을 도입하기 전, 사용 목적과 금지 목적을 문서화한다.
- [ ] 2. 모든 agent action에 owner, timestamp, source, tool, approval 상태를 남긴다.
- [ ] 3. 권한은 사용자 권한을 그대로 위임하지 않고 agent용 최소 권한 role로 분리한다.
- [ ] 4. 장기 실행 workflow는 conversation history가 아니라 explicit state field로 진행 상태를 판단한다.
- [ ] 5. 외부 시스템을 변경하는 tool은 dry-run, diff, approval, execute 단계를 나눈다.
- [ ] 6. 검색 또는 retrieval 결과는 URL, 문서 버전, fetched time을 함께 저장한다.
- [ ] 7. 민감 영역에서는 trusted user와 trusted task를 둘 다 확인한다.
- [ ] 8. agent가 생성한 remediation 또는 운영 조치는 pull request나 change request 형태로 사람이 검토하게 한다.
- [ ] 9. 비용은 모델 토큰뿐 아니라 tool call, storage, vector search, human review, retry까지 포함해 계산한다.
- [ ] 10. 평가셋은 성공 사례뿐 아니라 stale source, partial outage, permission denied, malformed input, conflicting instruction을 포함한다.
- [ ] 11. 운영 대시보드는 run success만 보지 말고 blocked action과 refused action도 함께 본다.
- [ ] 12. 장애 대응 agent는 관측 도구, 배포 이력, 코드 변경, feature flag, incident ticket을 함께 연결해야 한다.
- [ ] 13. 보안 agent는 SAST/DAST 결과만이 아니라 architecture doc과 threat model을 함께 ingest해야 한다.
- [ ] 14. 모바일 on-device AI는 fallback path와 model artifact version rollback을 준비한다.
- [ ] 15. AI 도입 지표는 seat count가 아니라 workflow phase, PR 흐름, review 흐름, agent surface 사용으로 본다.

### 이 발표를 내부 회의에서 설명한다면

한 문장으로는 이렇게 말할 수 있습니다. **OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access은/는 AI 도입의 중심이 모델 성능 비교에서 운영 가능한 실행면 설계로 이동했음을 보여 주며, 우리 팀은 기능 출시 전부터 권한, 상태, 평가, 비용, 감사, 복구를 backlog로 관리해야 한다.**

---

## 2) AWS frontier agents: Security Agent와 DevOps Agent 일반 제공

**공식 확인/발표 기준:** 2026-06-01 KST 확인  
**공식 출처:** https://aws.amazon.com/blogs/machine-learning/aws-launches-frontier-agents-for-security-testing-and-cloud-operations/  
**분석 렌즈:** frontier agent / SRE automation / security testing / incident response

### 공식 발표에서 확인한 핵심 사실

- AWS는 AWS Security Agent on-demand penetration testing과 AWS DevOps Agent가 generally available이라고 발표했다.
- AWS는 frontier agents를 독립적으로 목표를 달성하고, 대규모 동시 작업을 처리하며, 수시간 또는 수일 동안 지속 실행되는 autonomous systems로 설명한다.
- AWS Security Agent는 source code, architecture diagrams, documentation을 ingest해 취약점이 어떻게 attack chain으로 연결되는지 검증하고, 전통적 scanner가 놓치는 context-aware finding을 찾는다고 설명한다.
- AWS DevOps Agent는 CloudWatch, Datadog, Dynatrace, New Relic, Splunk, Grafana, GitHub, GitLab, Azure DevOps, CI/CD, runbooks와 연결해 incident lifecycle 전반을 조사한다고 설명한다.
- 공식 글은 preview 고객·파트너가 DevOps Agent에서 최대 75% lower MTTR, 80% faster investigations, 94% root cause accuracy, 3–5x faster incident resolution을 보고했다고 인용한다.

### 왜 중요한가

AWS가 Security Agent와 DevOps Agent를 frontier agents로 일반 제공하며 보안 테스트와 운영 대응을 agentic workflow로 확장했다. 이 발표의 핵심은 단순한 기능 추가가 아니라 AI 제품의 운영 기준이 바뀌고 있다는 점입니다. 이제 AI는 질문에 답하는 보조 수단에 머물지 않습니다. 보안 테스트를 실행하고, 장애 원인을 조사하고, 장기간 대기하다가 외부 이벤트로 다시 깨어나고, 민감한 과학 연구 흐름에 참여하고, 모바일 단말에서 개인 데이터를 로컬로 처리하며, 개발 조직의 workflow 자체를 바꿉니다.

이 변화가 위험한 이유는 agent가 빠르고 끈질기며 도구를 사용할 수 있기 때문입니다. 사람은 피곤하면 멈추고, 권한이 없으면 요청하고, 실수하면 동료가 눈치챌 시간이 있습니다. agent는 잘못 설계하면 잘못된 전제를 아주 빠르게 확장하고, 여러 시스템을 동시에 건드리며, 비용과 위험을 눈에 띄지 않게 누적할 수 있습니다. 반대로 잘 설계하면 사람보다 훨씬 일관되게 증거를 남기고, 반복적인 조사와 검증을 자동화하고, 취약점과 장애의 긴 꼬리를 줄일 수 있습니다.

따라서 이 발표를 읽을 때 “어떤 모델이 나왔는가”보다 “이 capability를 운영 가능한 시스템으로 만들기 위해 어떤 control plane이 필요한가”를 봐야 합니다. control plane에는 identity, permission, state, trace, eval, budget, approval, rollback, source grounding, compliance evidence가 포함됩니다.

### 개발자에게 의미

agent가 보안과 운영의 실제 변경면에 가까워질수록 개발자는 MCP, repository indexing, observability correlation, private connection, approval gate, remediation PR workflow를 기본 설계 요소로 봐야 한다.

개발자 관점에서 가장 중요한 변화는 AI 기능의 중심이 prompt engineering에서 system design으로 이동한다는 점입니다. prompt는 여전히 중요하지만, prompt만으로 production 문제를 해결할 수는 없습니다. agent가 어떤 상태에 있는지, 어떤 tool을 호출할 수 있는지, 어떤 외부 이벤트가 들어오면 어떤 checkpoint에서 재개해야 하는지, 어떤 결과가 사람의 승인을 받아야 하는지를 코드와 데이터 모델로 명시해야 합니다.

특히 이 발표는 다음과 같은 설계 전환을 요구합니다.

- **대화 로그 중심에서 상태 모델 중심으로:** 장기 workflow에서는 대화 전체를 다시 읽는 방식보다 명시적 state machine이 안정적입니다.
- **도구 연결 중심에서 권한 경계 중심으로:** tool을 많이 붙이는 것보다 tool scope, approval requirement, audit trail이 먼저입니다.
- **정확도 중심에서 회복 가능성 중심으로:** 모델이 틀릴 수 있음을 전제로 correction capture, retry policy, rollback path를 설계해야 합니다.
- **개별 기능 중심에서 운영 루프 중심으로:** release 이후에 trace, eval, feedback, cost, incident를 계속 순환시키는 구조가 필요합니다.

### 운영 포인트

운영팀은 frontier agent를 “챗봇”이 아니라 장시간 실행되는 자동 조사·권고·수정 후보 생성 시스템으로 취급하고, 권한·비용·증거·재현성·rollback 기준을 runbook에 넣어야 한다.

운영팀은 AI 기능을 모니터링할 때 전통적인 latency와 error rate만 보면 부족합니다. 다음 지표가 함께 필요합니다.

- tool call success/failure rate
- human approval 요청 수와 승인/거절 비율
- correction rate와 repeated failure cluster
- agent run duration과 idle/resume latency
- cost per completed workflow
- unsafe action blocked count
- stale-source answer rate
- evaluation pass rate와 regression failure
- rollback 또는 compensation action 발생 수
- permission denied가 실제로 보호한 사례

### 아키텍처 관점의 해석

이 발표를 제품 아키텍처로 번역하면 최소한 다음 계층이 필요합니다.

1. **Model gateway:** 모델 선택, rate limit, budget, logging, fallback을 담당합니다.
2. **Tool gateway:** 외부 시스템 접근을 도구 단위로 통제하고, 입력 검증과 결과 redaction을 수행합니다.
3. **Policy engine:** 누가, 어떤 목적, 어떤 데이터, 어떤 action을 허용받는지 판단합니다.
4. **State store:** 장기 workflow의 checkpoint, pending signal, step transition을 저장합니다.
5. **Trace store:** reasoning trace가 아니라 operational trace, tool call, source, decision, approval evidence를 저장합니다.
6. **Eval runner:** golden workflow, adversarial case, regression suite를 지속적으로 실행합니다.
7. **Human review console:** 사람의 승인, 수정, escalation, rollback을 담당합니다.
8. **Reporting layer:** adoption, quality, cost, risk, resilience metric을 조직 단위로 보여 줍니다.

### 바로 적용할 설계 질문

1. 이 기능이 읽을 수 있는 데이터와 절대 읽으면 안 되는 데이터는 무엇인가?
2. 이 기능이 쓸 수 있는 시스템과 propose-only로 남겨야 하는 시스템은 무엇인가?
3. 결과가 틀렸을 때 사람이 어디에서 수정하고, 그 수정이 어떤 평가 데이터로 저장되는가?
4. agent가 같은 작업을 재시도할 때 idempotency key와 중복 실행 방지는 어떻게 보장되는가?
5. 모델이 호출한 tool, tool input, tool output, 최종 action은 어느 수준까지 audit log로 남는가?
6. 비용이 폭증하는 조건은 무엇이며, per-user/per-workflow/per-agent budget은 어디에서 차단되는가?
7. 승인된 사용자와 승인된 목적을 분리해 검증하는가, 아니면 로그인만 통과하면 모든 기능을 쓰는가?
8. 외부 공식 문서나 내부 지식이 stale해졌을 때 agent는 어떤 방식으로 최신성을 확인하는가?
9. 장시간 대기하는 workflow에서 thread나 process를 붙잡고 있지 않은가?
10. rollback 또는 compensation action이 필요한 실패는 어떤 class로 분류되는가?

### 실무 적용 체크리스트

- [ ] 1. AWS frontier agents: Security Agent와 DevOps Agent 일반 제공 관련 기능을 도입하기 전, 사용 목적과 금지 목적을 문서화한다.
- [ ] 2. 모든 agent action에 owner, timestamp, source, tool, approval 상태를 남긴다.
- [ ] 3. 권한은 사용자 권한을 그대로 위임하지 않고 agent용 최소 권한 role로 분리한다.
- [ ] 4. 장기 실행 workflow는 conversation history가 아니라 explicit state field로 진행 상태를 판단한다.
- [ ] 5. 외부 시스템을 변경하는 tool은 dry-run, diff, approval, execute 단계를 나눈다.
- [ ] 6. 검색 또는 retrieval 결과는 URL, 문서 버전, fetched time을 함께 저장한다.
- [ ] 7. 민감 영역에서는 trusted user와 trusted task를 둘 다 확인한다.
- [ ] 8. agent가 생성한 remediation 또는 운영 조치는 pull request나 change request 형태로 사람이 검토하게 한다.
- [ ] 9. 비용은 모델 토큰뿐 아니라 tool call, storage, vector search, human review, retry까지 포함해 계산한다.
- [ ] 10. 평가셋은 성공 사례뿐 아니라 stale source, partial outage, permission denied, malformed input, conflicting instruction을 포함한다.
- [ ] 11. 운영 대시보드는 run success만 보지 말고 blocked action과 refused action도 함께 본다.
- [ ] 12. 장애 대응 agent는 관측 도구, 배포 이력, 코드 변경, feature flag, incident ticket을 함께 연결해야 한다.
- [ ] 13. 보안 agent는 SAST/DAST 결과만이 아니라 architecture doc과 threat model을 함께 ingest해야 한다.
- [ ] 14. 모바일 on-device AI는 fallback path와 model artifact version rollback을 준비한다.
- [ ] 15. AI 도입 지표는 seat count가 아니라 workflow phase, PR 흐름, review 흐름, agent surface 사용으로 본다.

### 이 발표를 내부 회의에서 설명한다면

한 문장으로는 이렇게 말할 수 있습니다. **AWS frontier agents: Security Agent와 DevOps Agent 일반 제공은/는 AI 도입의 중심이 모델 성능 비교에서 운영 가능한 실행면 설계로 이동했음을 보여 주며, 우리 팀은 기능 출시 전부터 권한, 상태, 평가, 비용, 감사, 복구를 backlog로 관리해야 한다.**

---

## 3) AWS Security Agent: on-demand penetration testing GA

**공식 확인/발표 기준:** 2026-06-01 KST 확인  
**공식 출처:** https://aws.amazon.com/blogs/security/aws-security-agent-on-demand-penetration-testing-now-generally-available/  
**분석 렌즈:** pentest automation / context-aware security / remediation loop / multicloud testing

### 공식 발표에서 확인한 핵심 사실

- AWS Security Agent는 AWS, Azure, GCP, other cloud providers, on-premises를 포함한 환경에서 penetration testing을 수행한다고 설명한다.
- agent space를 애플리케이션 또는 프로젝트의 논리 경계로 만들고, 소스 코드, API specification, architecture documentation, PRD, threat model을 연결할 수 있다.
- domain ownership validation이 필요하며, 공개 endpoint 또는 VPC를 통한 private endpoint 테스트를 지원한다.
- finding은 CVSS score, application-specific severity, reproduction steps, impact analysis를 포함하고, 검증된 취약점과 attack chain을 제시한다.
- 공식 글은 task-hour 기준 과금, 평균 애플리케이션 테스트 약 24 task-hours, 전형적 예시 비용 1,200달러를 제시하되 실제 비용은 복잡도에 따라 달라질 수 있다고 설명한다.

### 왜 중요한가

AWS Security Agent가 멀티클라우드·온프레미스까지 포함한 on-demand penetration testing을 일반 제공한다. 이 발표의 핵심은 단순한 기능 추가가 아니라 AI 제품의 운영 기준이 바뀌고 있다는 점입니다. 이제 AI는 질문에 답하는 보조 수단에 머물지 않습니다. 보안 테스트를 실행하고, 장애 원인을 조사하고, 장기간 대기하다가 외부 이벤트로 다시 깨어나고, 민감한 과학 연구 흐름에 참여하고, 모바일 단말에서 개인 데이터를 로컬로 처리하며, 개발 조직의 workflow 자체를 바꿉니다.

이 변화가 위험한 이유는 agent가 빠르고 끈질기며 도구를 사용할 수 있기 때문입니다. 사람은 피곤하면 멈추고, 권한이 없으면 요청하고, 실수하면 동료가 눈치챌 시간이 있습니다. agent는 잘못 설계하면 잘못된 전제를 아주 빠르게 확장하고, 여러 시스템을 동시에 건드리며, 비용과 위험을 눈에 띄지 않게 누적할 수 있습니다. 반대로 잘 설계하면 사람보다 훨씬 일관되게 증거를 남기고, 반복적인 조사와 검증을 자동화하고, 취약점과 장애의 긴 꼬리를 줄일 수 있습니다.

따라서 이 발표를 읽을 때 “어떤 모델이 나왔는가”보다 “이 capability를 운영 가능한 시스템으로 만들기 위해 어떤 control plane이 필요한가”를 봐야 합니다. control plane에는 identity, permission, state, trace, eval, budget, approval, rollback, source grounding, compliance evidence가 포함됩니다.

### 개발자에게 의미

보안 자동화가 SAST/DAST scan 결과 나열에서 “코드와 문서를 이해한 attack chain 검증”으로 이동하면, 개발팀은 threat model과 architecture doc을 실제 실행 가능한 보안 컨텍스트 자산으로 관리해야 한다.

개발자 관점에서 가장 중요한 변화는 AI 기능의 중심이 prompt engineering에서 system design으로 이동한다는 점입니다. prompt는 여전히 중요하지만, prompt만으로 production 문제를 해결할 수는 없습니다. agent가 어떤 상태에 있는지, 어떤 tool을 호출할 수 있는지, 어떤 외부 이벤트가 들어오면 어떤 checkpoint에서 재개해야 하는지, 어떤 결과가 사람의 승인을 받아야 하는지를 코드와 데이터 모델로 명시해야 합니다.

특히 이 발표는 다음과 같은 설계 전환을 요구합니다.

- **대화 로그 중심에서 상태 모델 중심으로:** 장기 workflow에서는 대화 전체를 다시 읽는 방식보다 명시적 state machine이 안정적입니다.
- **도구 연결 중심에서 권한 경계 중심으로:** tool을 많이 붙이는 것보다 tool scope, approval requirement, audit trail이 먼저입니다.
- **정확도 중심에서 회복 가능성 중심으로:** 모델이 틀릴 수 있음을 전제로 correction capture, retry policy, rollback path를 설계해야 합니다.
- **개별 기능 중심에서 운영 루프 중심으로:** release 이후에 trace, eval, feedback, cost, incident를 계속 순환시키는 구조가 필요합니다.

### 운영 포인트

보안 운영은 finding volume을 늘리는 것이 아니라 검증된 재현 절차, business impact, remediation PR, retest loop를 줄이는 방향으로 측정해야 한다.

운영팀은 AI 기능을 모니터링할 때 전통적인 latency와 error rate만 보면 부족합니다. 다음 지표가 함께 필요합니다.

- tool call success/failure rate
- human approval 요청 수와 승인/거절 비율
- correction rate와 repeated failure cluster
- agent run duration과 idle/resume latency
- cost per completed workflow
- unsafe action blocked count
- stale-source answer rate
- evaluation pass rate와 regression failure
- rollback 또는 compensation action 발생 수
- permission denied가 실제로 보호한 사례

### 아키텍처 관점의 해석

이 발표를 제품 아키텍처로 번역하면 최소한 다음 계층이 필요합니다.

1. **Model gateway:** 모델 선택, rate limit, budget, logging, fallback을 담당합니다.
2. **Tool gateway:** 외부 시스템 접근을 도구 단위로 통제하고, 입력 검증과 결과 redaction을 수행합니다.
3. **Policy engine:** 누가, 어떤 목적, 어떤 데이터, 어떤 action을 허용받는지 판단합니다.
4. **State store:** 장기 workflow의 checkpoint, pending signal, step transition을 저장합니다.
5. **Trace store:** reasoning trace가 아니라 operational trace, tool call, source, decision, approval evidence를 저장합니다.
6. **Eval runner:** golden workflow, adversarial case, regression suite를 지속적으로 실행합니다.
7. **Human review console:** 사람의 승인, 수정, escalation, rollback을 담당합니다.
8. **Reporting layer:** adoption, quality, cost, risk, resilience metric을 조직 단위로 보여 줍니다.

### 바로 적용할 설계 질문

1. 이 기능이 읽을 수 있는 데이터와 절대 읽으면 안 되는 데이터는 무엇인가?
2. 이 기능이 쓸 수 있는 시스템과 propose-only로 남겨야 하는 시스템은 무엇인가?
3. 결과가 틀렸을 때 사람이 어디에서 수정하고, 그 수정이 어떤 평가 데이터로 저장되는가?
4. agent가 같은 작업을 재시도할 때 idempotency key와 중복 실행 방지는 어떻게 보장되는가?
5. 모델이 호출한 tool, tool input, tool output, 최종 action은 어느 수준까지 audit log로 남는가?
6. 비용이 폭증하는 조건은 무엇이며, per-user/per-workflow/per-agent budget은 어디에서 차단되는가?
7. 승인된 사용자와 승인된 목적을 분리해 검증하는가, 아니면 로그인만 통과하면 모든 기능을 쓰는가?
8. 외부 공식 문서나 내부 지식이 stale해졌을 때 agent는 어떤 방식으로 최신성을 확인하는가?
9. 장시간 대기하는 workflow에서 thread나 process를 붙잡고 있지 않은가?
10. rollback 또는 compensation action이 필요한 실패는 어떤 class로 분류되는가?

### 실무 적용 체크리스트

- [ ] 1. AWS Security Agent: on-demand penetration testing GA 관련 기능을 도입하기 전, 사용 목적과 금지 목적을 문서화한다.
- [ ] 2. 모든 agent action에 owner, timestamp, source, tool, approval 상태를 남긴다.
- [ ] 3. 권한은 사용자 권한을 그대로 위임하지 않고 agent용 최소 권한 role로 분리한다.
- [ ] 4. 장기 실행 workflow는 conversation history가 아니라 explicit state field로 진행 상태를 판단한다.
- [ ] 5. 외부 시스템을 변경하는 tool은 dry-run, diff, approval, execute 단계를 나눈다.
- [ ] 6. 검색 또는 retrieval 결과는 URL, 문서 버전, fetched time을 함께 저장한다.
- [ ] 7. 민감 영역에서는 trusted user와 trusted task를 둘 다 확인한다.
- [ ] 8. agent가 생성한 remediation 또는 운영 조치는 pull request나 change request 형태로 사람이 검토하게 한다.
- [ ] 9. 비용은 모델 토큰뿐 아니라 tool call, storage, vector search, human review, retry까지 포함해 계산한다.
- [ ] 10. 평가셋은 성공 사례뿐 아니라 stale source, partial outage, permission denied, malformed input, conflicting instruction을 포함한다.
- [ ] 11. 운영 대시보드는 run success만 보지 말고 blocked action과 refused action도 함께 본다.
- [ ] 12. 장애 대응 agent는 관측 도구, 배포 이력, 코드 변경, feature flag, incident ticket을 함께 연결해야 한다.
- [ ] 13. 보안 agent는 SAST/DAST 결과만이 아니라 architecture doc과 threat model을 함께 ingest해야 한다.
- [ ] 14. 모바일 on-device AI는 fallback path와 model artifact version rollback을 준비한다.
- [ ] 15. AI 도입 지표는 seat count가 아니라 workflow phase, PR 흐름, review 흐름, agent surface 사용으로 본다.

### 이 발표를 내부 회의에서 설명한다면

한 문장으로는 이렇게 말할 수 있습니다. **AWS Security Agent: on-demand penetration testing GA은/는 AI 도입의 중심이 모델 성능 비교에서 운영 가능한 실행면 설계로 이동했음을 보여 주며, 우리 팀은 기능 출시 전부터 권한, 상태, 평가, 비용, 감사, 복구를 backlog로 관리해야 한다.**

---

## 4) AWS Resilience Hub: 생성형 AI 기반 SRE resilience journey

**공식 확인/발표 기준:** 2026-06-01 KST 확인  
**공식 출처:** https://aws.amazon.com/blogs/aws/introducing-the-next-generation-of-aws-resilience-hub-for-generative-ai-based-sre-resilience-journey/  
**분석 렌즈:** resilience engineering / failure mode analysis / SRE governance / portfolio reporting

### 공식 발표에서 확인한 핵심 사실

- AWS News Blog는 next generation AWS Resilience Hub가 new application model, dependency discovery assessment, generative AI-powered failure mode analysis, modular resilience policies, organization-wide reporting을 제공한다고 설명한다.
- 조직이 수백 개 애플리케이션을 운영할 때 resilience goals, progress measurement, compliance proof를 일관되게 유지하기 어렵다는 문제를 겨냥한다.
- AWS Organizations와 통합해 enterprise scale에서 resilience를 평가하고, failure modes와 hidden dependencies를 식별하며, 진척도를 보고할 수 있다고 설명한다.
- SRE와 development teams가 resilience policy expectation에 합의하고 테스트를 통해 compliance를 증명하도록 돕는 구조다.
- AI가 장애 분석 문장 생성에만 쓰이는 것이 아니라, resilience model과 policy 운영을 연결하는 계층으로 들어온다는 점이 중요하다.

### 왜 중요한가

AWS가 Resilience Hub를 확장해 application model, dependency discovery, generative AI-powered failure mode analysis, modular resilience policies, organization-wide reporting을 묶었다. 이 발표의 핵심은 단순한 기능 추가가 아니라 AI 제품의 운영 기준이 바뀌고 있다는 점입니다. 이제 AI는 질문에 답하는 보조 수단에 머물지 않습니다. 보안 테스트를 실행하고, 장애 원인을 조사하고, 장기간 대기하다가 외부 이벤트로 다시 깨어나고, 민감한 과학 연구 흐름에 참여하고, 모바일 단말에서 개인 데이터를 로컬로 처리하며, 개발 조직의 workflow 자체를 바꿉니다.

이 변화가 위험한 이유는 agent가 빠르고 끈질기며 도구를 사용할 수 있기 때문입니다. 사람은 피곤하면 멈추고, 권한이 없으면 요청하고, 실수하면 동료가 눈치챌 시간이 있습니다. agent는 잘못 설계하면 잘못된 전제를 아주 빠르게 확장하고, 여러 시스템을 동시에 건드리며, 비용과 위험을 눈에 띄지 않게 누적할 수 있습니다. 반대로 잘 설계하면 사람보다 훨씬 일관되게 증거를 남기고, 반복적인 조사와 검증을 자동화하고, 취약점과 장애의 긴 꼬리를 줄일 수 있습니다.

따라서 이 발표를 읽을 때 “어떤 모델이 나왔는가”보다 “이 capability를 운영 가능한 시스템으로 만들기 위해 어떤 control plane이 필요한가”를 봐야 합니다. control plane에는 identity, permission, state, trace, eval, budget, approval, rollback, source grounding, compliance evidence가 포함됩니다.

### 개발자에게 의미

개발자는 resilience를 후순위 문서가 아니라 application model, dependency graph, failure mode catalog, policy-as-code, test evidence로 설계해야 한다.

개발자 관점에서 가장 중요한 변화는 AI 기능의 중심이 prompt engineering에서 system design으로 이동한다는 점입니다. prompt는 여전히 중요하지만, prompt만으로 production 문제를 해결할 수는 없습니다. agent가 어떤 상태에 있는지, 어떤 tool을 호출할 수 있는지, 어떤 외부 이벤트가 들어오면 어떤 checkpoint에서 재개해야 하는지, 어떤 결과가 사람의 승인을 받아야 하는지를 코드와 데이터 모델로 명시해야 합니다.

특히 이 발표는 다음과 같은 설계 전환을 요구합니다.

- **대화 로그 중심에서 상태 모델 중심으로:** 장기 workflow에서는 대화 전체를 다시 읽는 방식보다 명시적 state machine이 안정적입니다.
- **도구 연결 중심에서 권한 경계 중심으로:** tool을 많이 붙이는 것보다 tool scope, approval requirement, audit trail이 먼저입니다.
- **정확도 중심에서 회복 가능성 중심으로:** 모델이 틀릴 수 있음을 전제로 correction capture, retry policy, rollback path를 설계해야 합니다.
- **개별 기능 중심에서 운영 루프 중심으로:** release 이후에 trace, eval, feedback, cost, incident를 계속 순환시키는 구조가 필요합니다.

### 운영 포인트

운영팀은 생성형 AI SRE 도구가 제안한 failure mode를 그대로 믿기보다, 실제 dependency discovery와 게임데이/chaos test 결과로 검증하는 운영 루프를 만들어야 한다.

운영팀은 AI 기능을 모니터링할 때 전통적인 latency와 error rate만 보면 부족합니다. 다음 지표가 함께 필요합니다.

- tool call success/failure rate
- human approval 요청 수와 승인/거절 비율
- correction rate와 repeated failure cluster
- agent run duration과 idle/resume latency
- cost per completed workflow
- unsafe action blocked count
- stale-source answer rate
- evaluation pass rate와 regression failure
- rollback 또는 compensation action 발생 수
- permission denied가 실제로 보호한 사례

### 아키텍처 관점의 해석

이 발표를 제품 아키텍처로 번역하면 최소한 다음 계층이 필요합니다.

1. **Model gateway:** 모델 선택, rate limit, budget, logging, fallback을 담당합니다.
2. **Tool gateway:** 외부 시스템 접근을 도구 단위로 통제하고, 입력 검증과 결과 redaction을 수행합니다.
3. **Policy engine:** 누가, 어떤 목적, 어떤 데이터, 어떤 action을 허용받는지 판단합니다.
4. **State store:** 장기 workflow의 checkpoint, pending signal, step transition을 저장합니다.
5. **Trace store:** reasoning trace가 아니라 operational trace, tool call, source, decision, approval evidence를 저장합니다.
6. **Eval runner:** golden workflow, adversarial case, regression suite를 지속적으로 실행합니다.
7. **Human review console:** 사람의 승인, 수정, escalation, rollback을 담당합니다.
8. **Reporting layer:** adoption, quality, cost, risk, resilience metric을 조직 단위로 보여 줍니다.

### 바로 적용할 설계 질문

1. 이 기능이 읽을 수 있는 데이터와 절대 읽으면 안 되는 데이터는 무엇인가?
2. 이 기능이 쓸 수 있는 시스템과 propose-only로 남겨야 하는 시스템은 무엇인가?
3. 결과가 틀렸을 때 사람이 어디에서 수정하고, 그 수정이 어떤 평가 데이터로 저장되는가?
4. agent가 같은 작업을 재시도할 때 idempotency key와 중복 실행 방지는 어떻게 보장되는가?
5. 모델이 호출한 tool, tool input, tool output, 최종 action은 어느 수준까지 audit log로 남는가?
6. 비용이 폭증하는 조건은 무엇이며, per-user/per-workflow/per-agent budget은 어디에서 차단되는가?
7. 승인된 사용자와 승인된 목적을 분리해 검증하는가, 아니면 로그인만 통과하면 모든 기능을 쓰는가?
8. 외부 공식 문서나 내부 지식이 stale해졌을 때 agent는 어떤 방식으로 최신성을 확인하는가?
9. 장시간 대기하는 workflow에서 thread나 process를 붙잡고 있지 않은가?
10. rollback 또는 compensation action이 필요한 실패는 어떤 class로 분류되는가?

### 실무 적용 체크리스트

- [ ] 1. AWS Resilience Hub: 생성형 AI 기반 SRE resilience journey 관련 기능을 도입하기 전, 사용 목적과 금지 목적을 문서화한다.
- [ ] 2. 모든 agent action에 owner, timestamp, source, tool, approval 상태를 남긴다.
- [ ] 3. 권한은 사용자 권한을 그대로 위임하지 않고 agent용 최소 권한 role로 분리한다.
- [ ] 4. 장기 실행 workflow는 conversation history가 아니라 explicit state field로 진행 상태를 판단한다.
- [ ] 5. 외부 시스템을 변경하는 tool은 dry-run, diff, approval, execute 단계를 나눈다.
- [ ] 6. 검색 또는 retrieval 결과는 URL, 문서 버전, fetched time을 함께 저장한다.
- [ ] 7. 민감 영역에서는 trusted user와 trusted task를 둘 다 확인한다.
- [ ] 8. agent가 생성한 remediation 또는 운영 조치는 pull request나 change request 형태로 사람이 검토하게 한다.
- [ ] 9. 비용은 모델 토큰뿐 아니라 tool call, storage, vector search, human review, retry까지 포함해 계산한다.
- [ ] 10. 평가셋은 성공 사례뿐 아니라 stale source, partial outage, permission denied, malformed input, conflicting instruction을 포함한다.
- [ ] 11. 운영 대시보드는 run success만 보지 말고 blocked action과 refused action도 함께 본다.
- [ ] 12. 장애 대응 agent는 관측 도구, 배포 이력, 코드 변경, feature flag, incident ticket을 함께 연결해야 한다.
- [ ] 13. 보안 agent는 SAST/DAST 결과만이 아니라 architecture doc과 threat model을 함께 ingest해야 한다.
- [ ] 14. 모바일 on-device AI는 fallback path와 model artifact version rollback을 준비한다.
- [ ] 15. AI 도입 지표는 seat count가 아니라 workflow phase, PR 흐름, review 흐름, agent surface 사용으로 본다.

### 이 발표를 내부 회의에서 설명한다면

한 문장으로는 이렇게 말할 수 있습니다. **AWS Resilience Hub: 생성형 AI 기반 SRE resilience journey은/는 AI 도입의 중심이 모델 성능 비교에서 운영 가능한 실행면 설계로 이동했음을 보여 주며, 우리 팀은 기능 출시 전부터 권한, 상태, 평가, 비용, 감사, 복구를 backlog로 관리해야 한다.**

---

## 5) Google ADK long-running agents: pause, resume, durable state

**공식 확인/발표 기준:** 2026-05-12  
**공식 출처:** https://developers.googleblog.com/en/build-long-running-ai-agents-that-pause-resume-and-never-lose-context-with-adk/  
**분석 렌즈:** durable agents / state machine / event-driven resume / multi-agent delegation

### 공식 발표에서 확인한 핵심 사실

- Google은 HR onboarding coordinator agent 예시로 수일·수주에 걸친 enterprise workflow가 단일 API call 안에 끝나지 않는다고 설명한다.
- 핵심 아키텍처 변화로 durable memory schemas, event-driven dormancy gates, multi-agent delegation을 제시한다.
- conversation history를 계속 replay하는 방식은 context pollution, token cost explosion, idle time 후 reasoning hallucination을 만든다고 지적한다.
- ADK 예시는 explicit state machine, persistent sessions, webhook 기반 resume, ToolContext.state checkpoint, Runner.run_async와 state_delta를 사용한다.
- golden evaluations로 idle time과 webhook trigger를 짧은 시간 안에 시뮬레이션해 CI/CD에서 state machine regression을 잡는 방식을 제시한다.

### 왜 중요한가

Google Developers Blog가 ADK로 장기 실행 agent를 구현하는 패턴을 공개하며 stateless chatbot에서 durable workflow agent로의 전환을 강조했다. 이 발표의 핵심은 단순한 기능 추가가 아니라 AI 제품의 운영 기준이 바뀌고 있다는 점입니다. 이제 AI는 질문에 답하는 보조 수단에 머물지 않습니다. 보안 테스트를 실행하고, 장애 원인을 조사하고, 장기간 대기하다가 외부 이벤트로 다시 깨어나고, 민감한 과학 연구 흐름에 참여하고, 모바일 단말에서 개인 데이터를 로컬로 처리하며, 개발 조직의 workflow 자체를 바꿉니다.

이 변화가 위험한 이유는 agent가 빠르고 끈질기며 도구를 사용할 수 있기 때문입니다. 사람은 피곤하면 멈추고, 권한이 없으면 요청하고, 실수하면 동료가 눈치챌 시간이 있습니다. agent는 잘못 설계하면 잘못된 전제를 아주 빠르게 확장하고, 여러 시스템을 동시에 건드리며, 비용과 위험을 눈에 띄지 않게 누적할 수 있습니다. 반대로 잘 설계하면 사람보다 훨씬 일관되게 증거를 남기고, 반복적인 조사와 검증을 자동화하고, 취약점과 장애의 긴 꼬리를 줄일 수 있습니다.

따라서 이 발표를 읽을 때 “어떤 모델이 나왔는가”보다 “이 capability를 운영 가능한 시스템으로 만들기 위해 어떤 control plane이 필요한가”를 봐야 합니다. control plane에는 identity, permission, state, trace, eval, budget, approval, rollback, source grounding, compliance evidence가 포함됩니다.

### 개발자에게 의미

agent 제품을 만들 때 “대화 기억”보다 “명시적 상태 전이”가 우선이다. 장기 업무에서는 state machine, persistence, event resume, eval fixture가 product reliability를 좌우한다.

개발자 관점에서 가장 중요한 변화는 AI 기능의 중심이 prompt engineering에서 system design으로 이동한다는 점입니다. prompt는 여전히 중요하지만, prompt만으로 production 문제를 해결할 수는 없습니다. agent가 어떤 상태에 있는지, 어떤 tool을 호출할 수 있는지, 어떤 외부 이벤트가 들어오면 어떤 checkpoint에서 재개해야 하는지, 어떤 결과가 사람의 승인을 받아야 하는지를 코드와 데이터 모델로 명시해야 합니다.

특히 이 발표는 다음과 같은 설계 전환을 요구합니다.

- **대화 로그 중심에서 상태 모델 중심으로:** 장기 workflow에서는 대화 전체를 다시 읽는 방식보다 명시적 state machine이 안정적입니다.
- **도구 연결 중심에서 권한 경계 중심으로:** tool을 많이 붙이는 것보다 tool scope, approval requirement, audit trail이 먼저입니다.
- **정확도 중심에서 회복 가능성 중심으로:** 모델이 틀릴 수 있음을 전제로 correction capture, retry policy, rollback path를 설계해야 합니다.
- **개별 기능 중심에서 운영 루프 중심으로:** release 이후에 trace, eval, feedback, cost, incident를 계속 순환시키는 구조가 필요합니다.

### 운영 포인트

운영팀은 agent가 기다리는 시간을 thread나 polling으로 처리하지 말고 dormant state, external signal, resume log, timeout policy, compensation action으로 관리해야 한다.

운영팀은 AI 기능을 모니터링할 때 전통적인 latency와 error rate만 보면 부족합니다. 다음 지표가 함께 필요합니다.

- tool call success/failure rate
- human approval 요청 수와 승인/거절 비율
- correction rate와 repeated failure cluster
- agent run duration과 idle/resume latency
- cost per completed workflow
- unsafe action blocked count
- stale-source answer rate
- evaluation pass rate와 regression failure
- rollback 또는 compensation action 발생 수
- permission denied가 실제로 보호한 사례

### 아키텍처 관점의 해석

이 발표를 제품 아키텍처로 번역하면 최소한 다음 계층이 필요합니다.

1. **Model gateway:** 모델 선택, rate limit, budget, logging, fallback을 담당합니다.
2. **Tool gateway:** 외부 시스템 접근을 도구 단위로 통제하고, 입력 검증과 결과 redaction을 수행합니다.
3. **Policy engine:** 누가, 어떤 목적, 어떤 데이터, 어떤 action을 허용받는지 판단합니다.
4. **State store:** 장기 workflow의 checkpoint, pending signal, step transition을 저장합니다.
5. **Trace store:** reasoning trace가 아니라 operational trace, tool call, source, decision, approval evidence를 저장합니다.
6. **Eval runner:** golden workflow, adversarial case, regression suite를 지속적으로 실행합니다.
7. **Human review console:** 사람의 승인, 수정, escalation, rollback을 담당합니다.
8. **Reporting layer:** adoption, quality, cost, risk, resilience metric을 조직 단위로 보여 줍니다.

### 바로 적용할 설계 질문

1. 이 기능이 읽을 수 있는 데이터와 절대 읽으면 안 되는 데이터는 무엇인가?
2. 이 기능이 쓸 수 있는 시스템과 propose-only로 남겨야 하는 시스템은 무엇인가?
3. 결과가 틀렸을 때 사람이 어디에서 수정하고, 그 수정이 어떤 평가 데이터로 저장되는가?
4. agent가 같은 작업을 재시도할 때 idempotency key와 중복 실행 방지는 어떻게 보장되는가?
5. 모델이 호출한 tool, tool input, tool output, 최종 action은 어느 수준까지 audit log로 남는가?
6. 비용이 폭증하는 조건은 무엇이며, per-user/per-workflow/per-agent budget은 어디에서 차단되는가?
7. 승인된 사용자와 승인된 목적을 분리해 검증하는가, 아니면 로그인만 통과하면 모든 기능을 쓰는가?
8. 외부 공식 문서나 내부 지식이 stale해졌을 때 agent는 어떤 방식으로 최신성을 확인하는가?
9. 장시간 대기하는 workflow에서 thread나 process를 붙잡고 있지 않은가?
10. rollback 또는 compensation action이 필요한 실패는 어떤 class로 분류되는가?

### 실무 적용 체크리스트

- [ ] 1. Google ADK long-running agents: pause, resume, durable state 관련 기능을 도입하기 전, 사용 목적과 금지 목적을 문서화한다.
- [ ] 2. 모든 agent action에 owner, timestamp, source, tool, approval 상태를 남긴다.
- [ ] 3. 권한은 사용자 권한을 그대로 위임하지 않고 agent용 최소 권한 role로 분리한다.
- [ ] 4. 장기 실행 workflow는 conversation history가 아니라 explicit state field로 진행 상태를 판단한다.
- [ ] 5. 외부 시스템을 변경하는 tool은 dry-run, diff, approval, execute 단계를 나눈다.
- [ ] 6. 검색 또는 retrieval 결과는 URL, 문서 버전, fetched time을 함께 저장한다.
- [ ] 7. 민감 영역에서는 trusted user와 trusted task를 둘 다 확인한다.
- [ ] 8. agent가 생성한 remediation 또는 운영 조치는 pull request나 change request 형태로 사람이 검토하게 한다.
- [ ] 9. 비용은 모델 토큰뿐 아니라 tool call, storage, vector search, human review, retry까지 포함해 계산한다.
- [ ] 10. 평가셋은 성공 사례뿐 아니라 stale source, partial outage, permission denied, malformed input, conflicting instruction을 포함한다.
- [ ] 11. 운영 대시보드는 run success만 보지 말고 blocked action과 refused action도 함께 본다.
- [ ] 12. 장애 대응 agent는 관측 도구, 배포 이력, 코드 변경, feature flag, incident ticket을 함께 연결해야 한다.
- [ ] 13. 보안 agent는 SAST/DAST 결과만이 아니라 architecture doc과 threat model을 함께 ingest해야 한다.
- [ ] 14. 모바일 on-device AI는 fallback path와 model artifact version rollback을 준비한다.
- [ ] 15. AI 도입 지표는 seat count가 아니라 workflow phase, PR 흐름, review 흐름, agent surface 사용으로 본다.

### 이 발표를 내부 회의에서 설명한다면

한 문장으로는 이렇게 말할 수 있습니다. **Google ADK long-running agents: pause, resume, durable state은/는 AI 도입의 중심이 모델 성능 비교에서 운영 가능한 실행면 설계로 이동했음을 보여 주며, 우리 팀은 기능 출시 전부터 권한, 상태, 평가, 비용, 감사, 복구를 backlog로 관리해야 한다.**

---

## 6) Google Tensor SDK Beta with LiteRT: Pixel on-device AI 개발면 확대

**공식 확인/발표 기준:** 2026-05-19  
**공식 출처:** https://developers.googleblog.com/en/google-tensor-sdk-beta-with-litert/  
**분석 렌즈:** on-device AI / edge runtime / LiteRT / Pixel TPU / model delivery

### 공식 발표에서 확인한 핵심 사실

- Google Tensor ML SDK가 Experimental Access Program에서 Beta로 이동하며 Pixel 10 family의 Google Tensor TPU에서 모델을 빌드·배포·실행할 수 있게 됐다.
- Beta는 LiteRT와 통합된 unified developer workflow와 100개 이상 모델을 제공하는 Model Garden을 핵심 장점으로 제시한다.
- LiteRT는 PyTorch 또는 TFLite 모델을 변환·컴파일해 Tensor TPU를 활용하는 바이너리로 만들고, Play Feature Delivery와 AI Packs로 runtime/compiler library와 model artifact를 배포하는 흐름을 제공한다.
- fallback mechanism으로 TPU availability에 따라 CPU 또는 GPU를 secondary option으로 지정할 수 있다고 설명한다.
- Model Garden은 classic ML, speech recognition, computer vision, Gemma 3 1B, Function Gemma, EmbeddingGemma 등 on-device 기능 예시를 제시한다.

### 왜 중요한가

Google Tensor ML SDK가 LiteRT 통합과 100개 이상 model garden을 통해 Pixel 10 계열 on-device AI 개발을 Beta로 확장했다. 이 발표의 핵심은 단순한 기능 추가가 아니라 AI 제품의 운영 기준이 바뀌고 있다는 점입니다. 이제 AI는 질문에 답하는 보조 수단에 머물지 않습니다. 보안 테스트를 실행하고, 장애 원인을 조사하고, 장기간 대기하다가 외부 이벤트로 다시 깨어나고, 민감한 과학 연구 흐름에 참여하고, 모바일 단말에서 개인 데이터를 로컬로 처리하며, 개발 조직의 workflow 자체를 바꿉니다.

이 변화가 위험한 이유는 agent가 빠르고 끈질기며 도구를 사용할 수 있기 때문입니다. 사람은 피곤하면 멈추고, 권한이 없으면 요청하고, 실수하면 동료가 눈치챌 시간이 있습니다. agent는 잘못 설계하면 잘못된 전제를 아주 빠르게 확장하고, 여러 시스템을 동시에 건드리며, 비용과 위험을 눈에 띄지 않게 누적할 수 있습니다. 반대로 잘 설계하면 사람보다 훨씬 일관되게 증거를 남기고, 반복적인 조사와 검증을 자동화하고, 취약점과 장애의 긴 꼬리를 줄일 수 있습니다.

따라서 이 발표를 읽을 때 “어떤 모델이 나왔는가”보다 “이 capability를 운영 가능한 시스템으로 만들기 위해 어떤 control plane이 필요한가”를 봐야 합니다. control plane에는 identity, permission, state, trace, eval, budget, approval, rollback, source grounding, compliance evidence가 포함됩니다.

### 개발자에게 의미

프라이버시·지연시간·오프라인 UX가 중요한 앱은 서버 LLM 호출만 보지 말고, 작은 모델과 edge runtime을 제품 아키텍처의 1급 선택지로 다뤄야 한다.

개발자 관점에서 가장 중요한 변화는 AI 기능의 중심이 prompt engineering에서 system design으로 이동한다는 점입니다. prompt는 여전히 중요하지만, prompt만으로 production 문제를 해결할 수는 없습니다. agent가 어떤 상태에 있는지, 어떤 tool을 호출할 수 있는지, 어떤 외부 이벤트가 들어오면 어떤 checkpoint에서 재개해야 하는지, 어떤 결과가 사람의 승인을 받아야 하는지를 코드와 데이터 모델로 명시해야 합니다.

특히 이 발표는 다음과 같은 설계 전환을 요구합니다.

- **대화 로그 중심에서 상태 모델 중심으로:** 장기 workflow에서는 대화 전체를 다시 읽는 방식보다 명시적 state machine이 안정적입니다.
- **도구 연결 중심에서 권한 경계 중심으로:** tool을 많이 붙이는 것보다 tool scope, approval requirement, audit trail이 먼저입니다.
- **정확도 중심에서 회복 가능성 중심으로:** 모델이 틀릴 수 있음을 전제로 correction capture, retry policy, rollback path를 설계해야 합니다.
- **개별 기능 중심에서 운영 루프 중심으로:** release 이후에 trace, eval, feedback, cost, incident를 계속 순환시키는 구조가 필요합니다.

### 운영 포인트

모바일 AI 운영은 모델 정확도뿐 아니라 device support, fallback path, artifact delivery, runtime versioning, battery·thermal budget, telemetry redaction을 함께 관리해야 한다.

운영팀은 AI 기능을 모니터링할 때 전통적인 latency와 error rate만 보면 부족합니다. 다음 지표가 함께 필요합니다.

- tool call success/failure rate
- human approval 요청 수와 승인/거절 비율
- correction rate와 repeated failure cluster
- agent run duration과 idle/resume latency
- cost per completed workflow
- unsafe action blocked count
- stale-source answer rate
- evaluation pass rate와 regression failure
- rollback 또는 compensation action 발생 수
- permission denied가 실제로 보호한 사례

### 아키텍처 관점의 해석

이 발표를 제품 아키텍처로 번역하면 최소한 다음 계층이 필요합니다.

1. **Model gateway:** 모델 선택, rate limit, budget, logging, fallback을 담당합니다.
2. **Tool gateway:** 외부 시스템 접근을 도구 단위로 통제하고, 입력 검증과 결과 redaction을 수행합니다.
3. **Policy engine:** 누가, 어떤 목적, 어떤 데이터, 어떤 action을 허용받는지 판단합니다.
4. **State store:** 장기 workflow의 checkpoint, pending signal, step transition을 저장합니다.
5. **Trace store:** reasoning trace가 아니라 operational trace, tool call, source, decision, approval evidence를 저장합니다.
6. **Eval runner:** golden workflow, adversarial case, regression suite를 지속적으로 실행합니다.
7. **Human review console:** 사람의 승인, 수정, escalation, rollback을 담당합니다.
8. **Reporting layer:** adoption, quality, cost, risk, resilience metric을 조직 단위로 보여 줍니다.

### 바로 적용할 설계 질문

1. 이 기능이 읽을 수 있는 데이터와 절대 읽으면 안 되는 데이터는 무엇인가?
2. 이 기능이 쓸 수 있는 시스템과 propose-only로 남겨야 하는 시스템은 무엇인가?
3. 결과가 틀렸을 때 사람이 어디에서 수정하고, 그 수정이 어떤 평가 데이터로 저장되는가?
4. agent가 같은 작업을 재시도할 때 idempotency key와 중복 실행 방지는 어떻게 보장되는가?
5. 모델이 호출한 tool, tool input, tool output, 최종 action은 어느 수준까지 audit log로 남는가?
6. 비용이 폭증하는 조건은 무엇이며, per-user/per-workflow/per-agent budget은 어디에서 차단되는가?
7. 승인된 사용자와 승인된 목적을 분리해 검증하는가, 아니면 로그인만 통과하면 모든 기능을 쓰는가?
8. 외부 공식 문서나 내부 지식이 stale해졌을 때 agent는 어떤 방식으로 최신성을 확인하는가?
9. 장시간 대기하는 workflow에서 thread나 process를 붙잡고 있지 않은가?
10. rollback 또는 compensation action이 필요한 실패는 어떤 class로 분류되는가?

### 실무 적용 체크리스트

- [ ] 1. Google Tensor SDK Beta with LiteRT: Pixel on-device AI 개발면 확대 관련 기능을 도입하기 전, 사용 목적과 금지 목적을 문서화한다.
- [ ] 2. 모든 agent action에 owner, timestamp, source, tool, approval 상태를 남긴다.
- [ ] 3. 권한은 사용자 권한을 그대로 위임하지 않고 agent용 최소 권한 role로 분리한다.
- [ ] 4. 장기 실행 workflow는 conversation history가 아니라 explicit state field로 진행 상태를 판단한다.
- [ ] 5. 외부 시스템을 변경하는 tool은 dry-run, diff, approval, execute 단계를 나눈다.
- [ ] 6. 검색 또는 retrieval 결과는 URL, 문서 버전, fetched time을 함께 저장한다.
- [ ] 7. 민감 영역에서는 trusted user와 trusted task를 둘 다 확인한다.
- [ ] 8. agent가 생성한 remediation 또는 운영 조치는 pull request나 change request 형태로 사람이 검토하게 한다.
- [ ] 9. 비용은 모델 토큰뿐 아니라 tool call, storage, vector search, human review, retry까지 포함해 계산한다.
- [ ] 10. 평가셋은 성공 사례뿐 아니라 stale source, partial outage, permission denied, malformed input, conflicting instruction을 포함한다.
- [ ] 11. 운영 대시보드는 run success만 보지 말고 blocked action과 refused action도 함께 본다.
- [ ] 12. 장애 대응 agent는 관측 도구, 배포 이력, 코드 변경, feature flag, incident ticket을 함께 연결해야 한다.
- [ ] 13. 보안 agent는 SAST/DAST 결과만이 아니라 architecture doc과 threat model을 함께 ingest해야 한다.
- [ ] 14. 모바일 on-device AI는 fallback path와 model artifact version rollback을 준비한다.
- [ ] 15. AI 도입 지표는 seat count가 아니라 workflow phase, PR 흐름, review 흐름, agent surface 사용으로 본다.

### 이 발표를 내부 회의에서 설명한다면

한 문장으로는 이렇게 말할 수 있습니다. **Google Tensor SDK Beta with LiteRT: Pixel on-device AI 개발면 확대은/는 AI 도입의 중심이 모델 성능 비교에서 운영 가능한 실행면 설계로 이동했음을 보여 주며, 우리 팀은 기능 출시 전부터 권한, 상태, 평가, 비용, 감사, 복구를 backlog로 관리해야 한다.**

---

## 7) GitHub Copilot usage metrics API: AI adoption phase cohort

**공식 확인/발표 기준:** 2026-05-29  
**공식 출처:** https://github.blog/changelog/2026-05-29-copilot-usage-metrics-api-adds-cohorts-for-ai-adoption  
**분석 렌즈:** AI adoption analytics / developer productivity / cohort metrics / multi-agent workflow

### 공식 발표에서 확인한 핵심 사실

- GitHub는 rolling 28-day window에서 Copilot product usage를 바탕으로 engaged user를 AI adoption phase로 분류한다.
- Phase 0은 no cohort, Phase 1은 code first, Phase 2는 agent first, Phase 3은 multi-agent로 정의된다.
- user-level report에는 ai_adoption_phase 필드가 추가되고, enterprise/organization report에는 totals_by_ai_adoption_phase 배열이 추가된다.
- phase별 metric에는 total engaged users, user-initiated interaction average, code generation and acceptance averages, lines added/deleted averages, PR created/merged/reviewed averages, median time-to-merge average가 포함된다.
- GitHub는 이 분류 로직에 version field를 두어 Copilot product surface가 늘어나도 historical context를 깨지 않게 한다고 설명한다.

### 왜 중요한가

GitHub가 Copilot usage metrics API에 AI adoption phase cohort를 추가해 active user 수를 넘어 code-first, agent-first, multi-agent 성숙도를 측정하게 했다. 이 발표의 핵심은 단순한 기능 추가가 아니라 AI 제품의 운영 기준이 바뀌고 있다는 점입니다. 이제 AI는 질문에 답하는 보조 수단에 머물지 않습니다. 보안 테스트를 실행하고, 장애 원인을 조사하고, 장기간 대기하다가 외부 이벤트로 다시 깨어나고, 민감한 과학 연구 흐름에 참여하고, 모바일 단말에서 개인 데이터를 로컬로 처리하며, 개발 조직의 workflow 자체를 바꿉니다.

이 변화가 위험한 이유는 agent가 빠르고 끈질기며 도구를 사용할 수 있기 때문입니다. 사람은 피곤하면 멈추고, 권한이 없으면 요청하고, 실수하면 동료가 눈치챌 시간이 있습니다. agent는 잘못 설계하면 잘못된 전제를 아주 빠르게 확장하고, 여러 시스템을 동시에 건드리며, 비용과 위험을 눈에 띄지 않게 누적할 수 있습니다. 반대로 잘 설계하면 사람보다 훨씬 일관되게 증거를 남기고, 반복적인 조사와 검증을 자동화하고, 취약점과 장애의 긴 꼬리를 줄일 수 있습니다.

따라서 이 발표를 읽을 때 “어떤 모델이 나왔는가”보다 “이 capability를 운영 가능한 시스템으로 만들기 위해 어떤 control plane이 필요한가”를 봐야 합니다. control plane에는 identity, permission, state, trace, eval, budget, approval, rollback, source grounding, compliance evidence가 포함됩니다.

### 개발자에게 의미

개발 조직의 AI 도입은 “seat를 샀는가”가 아니라 “개발자가 어떤 표면에서 어떤 workflow를 바꾸었는가”로 측정해야 한다.

개발자 관점에서 가장 중요한 변화는 AI 기능의 중심이 prompt engineering에서 system design으로 이동한다는 점입니다. prompt는 여전히 중요하지만, prompt만으로 production 문제를 해결할 수는 없습니다. agent가 어떤 상태에 있는지, 어떤 tool을 호출할 수 있는지, 어떤 외부 이벤트가 들어오면 어떤 checkpoint에서 재개해야 하는지, 어떤 결과가 사람의 승인을 받아야 하는지를 코드와 데이터 모델로 명시해야 합니다.

특히 이 발표는 다음과 같은 설계 전환을 요구합니다.

- **대화 로그 중심에서 상태 모델 중심으로:** 장기 workflow에서는 대화 전체를 다시 읽는 방식보다 명시적 state machine이 안정적입니다.
- **도구 연결 중심에서 권한 경계 중심으로:** tool을 많이 붙이는 것보다 tool scope, approval requirement, audit trail이 먼저입니다.
- **정확도 중심에서 회복 가능성 중심으로:** 모델이 틀릴 수 있음을 전제로 correction capture, retry policy, rollback path를 설계해야 합니다.
- **개별 기능 중심에서 운영 루프 중심으로:** release 이후에 trace, eval, feedback, cost, incident를 계속 순환시키는 구조가 필요합니다.

### 운영 포인트

엔지니어링 리더는 AI 도입 대시보드를 active user 그래프에서 cohort progression, PR latency, review behavior, generated-code acceptance, agent-surface utilization로 확장해야 한다.

운영팀은 AI 기능을 모니터링할 때 전통적인 latency와 error rate만 보면 부족합니다. 다음 지표가 함께 필요합니다.

- tool call success/failure rate
- human approval 요청 수와 승인/거절 비율
- correction rate와 repeated failure cluster
- agent run duration과 idle/resume latency
- cost per completed workflow
- unsafe action blocked count
- stale-source answer rate
- evaluation pass rate와 regression failure
- rollback 또는 compensation action 발생 수
- permission denied가 실제로 보호한 사례

### 아키텍처 관점의 해석

이 발표를 제품 아키텍처로 번역하면 최소한 다음 계층이 필요합니다.

1. **Model gateway:** 모델 선택, rate limit, budget, logging, fallback을 담당합니다.
2. **Tool gateway:** 외부 시스템 접근을 도구 단위로 통제하고, 입력 검증과 결과 redaction을 수행합니다.
3. **Policy engine:** 누가, 어떤 목적, 어떤 데이터, 어떤 action을 허용받는지 판단합니다.
4. **State store:** 장기 workflow의 checkpoint, pending signal, step transition을 저장합니다.
5. **Trace store:** reasoning trace가 아니라 operational trace, tool call, source, decision, approval evidence를 저장합니다.
6. **Eval runner:** golden workflow, adversarial case, regression suite를 지속적으로 실행합니다.
7. **Human review console:** 사람의 승인, 수정, escalation, rollback을 담당합니다.
8. **Reporting layer:** adoption, quality, cost, risk, resilience metric을 조직 단위로 보여 줍니다.

### 바로 적용할 설계 질문

1. 이 기능이 읽을 수 있는 데이터와 절대 읽으면 안 되는 데이터는 무엇인가?
2. 이 기능이 쓸 수 있는 시스템과 propose-only로 남겨야 하는 시스템은 무엇인가?
3. 결과가 틀렸을 때 사람이 어디에서 수정하고, 그 수정이 어떤 평가 데이터로 저장되는가?
4. agent가 같은 작업을 재시도할 때 idempotency key와 중복 실행 방지는 어떻게 보장되는가?
5. 모델이 호출한 tool, tool input, tool output, 최종 action은 어느 수준까지 audit log로 남는가?
6. 비용이 폭증하는 조건은 무엇이며, per-user/per-workflow/per-agent budget은 어디에서 차단되는가?
7. 승인된 사용자와 승인된 목적을 분리해 검증하는가, 아니면 로그인만 통과하면 모든 기능을 쓰는가?
8. 외부 공식 문서나 내부 지식이 stale해졌을 때 agent는 어떤 방식으로 최신성을 확인하는가?
9. 장시간 대기하는 workflow에서 thread나 process를 붙잡고 있지 않은가?
10. rollback 또는 compensation action이 필요한 실패는 어떤 class로 분류되는가?

### 실무 적용 체크리스트

- [ ] 1. GitHub Copilot usage metrics API: AI adoption phase cohort 관련 기능을 도입하기 전, 사용 목적과 금지 목적을 문서화한다.
- [ ] 2. 모든 agent action에 owner, timestamp, source, tool, approval 상태를 남긴다.
- [ ] 3. 권한은 사용자 권한을 그대로 위임하지 않고 agent용 최소 권한 role로 분리한다.
- [ ] 4. 장기 실행 workflow는 conversation history가 아니라 explicit state field로 진행 상태를 판단한다.
- [ ] 5. 외부 시스템을 변경하는 tool은 dry-run, diff, approval, execute 단계를 나눈다.
- [ ] 6. 검색 또는 retrieval 결과는 URL, 문서 버전, fetched time을 함께 저장한다.
- [ ] 7. 민감 영역에서는 trusted user와 trusted task를 둘 다 확인한다.
- [ ] 8. agent가 생성한 remediation 또는 운영 조치는 pull request나 change request 형태로 사람이 검토하게 한다.
- [ ] 9. 비용은 모델 토큰뿐 아니라 tool call, storage, vector search, human review, retry까지 포함해 계산한다.
- [ ] 10. 평가셋은 성공 사례뿐 아니라 stale source, partial outage, permission denied, malformed input, conflicting instruction을 포함한다.
- [ ] 11. 운영 대시보드는 run success만 보지 말고 blocked action과 refused action도 함께 본다.
- [ ] 12. 장애 대응 agent는 관측 도구, 배포 이력, 코드 변경, feature flag, incident ticket을 함께 연결해야 한다.
- [ ] 13. 보안 agent는 SAST/DAST 결과만이 아니라 architecture doc과 threat model을 함께 ingest해야 한다.
- [ ] 14. 모바일 on-device AI는 fallback path와 model artifact version rollback을 준비한다.
- [ ] 15. AI 도입 지표는 seat count가 아니라 workflow phase, PR 흐름, review 흐름, agent surface 사용으로 본다.

### 이 발표를 내부 회의에서 설명한다면

한 문장으로는 이렇게 말할 수 있습니다. **GitHub Copilot usage metrics API: AI adoption phase cohort은/는 AI 도입의 중심이 모델 성능 비교에서 운영 가능한 실행면 설계로 이동했음을 보여 주며, 우리 팀은 기능 출시 전부터 권한, 상태, 평가, 비용, 감사, 복구를 backlog로 관리해야 한다.**

---

## 통합 분석: 오늘 발표들이 한 방향을 가리키는 이유

오늘의 발표들은 서로 다른 회사와 제품군에서 나왔지만, 하나의 큰 방향을 공유합니다. **AI가 “대답하는 시스템”에서 “일하는 시스템”으로 이동하고 있다**는 점입니다. 일하는 시스템에는 결과 책임이 있습니다. 결과 책임이 생기면 권한, 증거, 재현성, 비용, 보안, 변경 관리가 따라옵니다.

### 1. Capability가 강해질수록 access model이 중요해진다

OpenAI Rosalind Biodefense는 이 흐름을 가장 선명하게 보여 줍니다. 생명과학 영역의 frontier capability는 긍정적 활용과 dual-use risk가 동시에 존재합니다. 따라서 “모델이 있으니 모두에게 API를 연다”가 아니라, 어떤 기관이 어떤 목적의 public benefit을 위해 어떤 safeguard 아래에서 쓰는지를 관리해야 합니다. 개발자에게 이는 RBAC보다 더 넓은 ABAC(attribute-based access control), purpose binding, audit evidence, evaluation record가 필요하다는 뜻입니다.

### 2. Agent는 운영과 보안의 노동 구조를 바꾼다

AWS Security Agent와 DevOps Agent는 agent가 개발 조직의 주변 도구가 아니라 core engineering workflow 안으로 들어오고 있음을 보여 줍니다. 보안 테스트는 더 이상 연 1~2회 manual pentest 결과를 기다리는 구조에 머무르지 않습니다. 운영 대응도 2AM에 사람이 dashboard를 뒤지며 원인을 찾는 방식만으로는 충분하지 않습니다. agent는 code, telemetry, runbook, deployment history를 연결해 빠르게 hypothesis를 만들 수 있습니다. 그러나 이 장점은 동시에 governance 부담을 만듭니다. agent가 어떤 시스템을 읽었고 어떤 결론에 도달했는지 설명할 수 없다면, 빠른 자동화는 빠른 불신으로 바뀝니다.

### 3. 장기 workflow에는 memory가 아니라 state가 필요하다

Google ADK 글의 핵심은 매우 실무적입니다. 실제 업무는 짧은 채팅 세션 안에서 끝나지 않습니다. 입사 프로세스, 계약 검토, 구매 승인, 장애 후속 조치, 보안 취약점 remediation은 모두 며칠 또는 몇 주 동안 이어집니다. 이때 conversation history를 계속 붙여 넣는 방식은 context pollution과 비용 폭발, hallucinated progress를 만듭니다. 정답은 더 큰 context window가 아니라 명시적 state machine, durable session, event-driven resume입니다.

### 4. AI는 cloud-only가 아니라 edge/cloud hybrid로 간다

Google Tensor SDK Beta는 AI UX의 다른 축을 보여 줍니다. 서버 LLM이 강력해질수록 모든 기능을 서버로 보내고 싶어지지만, 사용자 경험은 항상 네트워크와 개인정보, 지연시간, 배터리 제약과 함께 움직입니다. on-device AI는 단순한 비용 절감 수단이 아니라 product trust와 responsiveness의 핵심이 될 수 있습니다. 특히 개인화, 음성, 카메라, 접근성, 번역, local action 같은 기능은 edge execution이 더 자연스럽습니다.

### 5. AI 도입은 사용량이 아니라 성숙도로 측정해야 한다

GitHub Copilot의 AI adoption phase는 중요한 신호입니다. 많은 조직이 AI 도입률을 active user 또는 license utilization으로만 봅니다. 그러나 seat를 켰다고 workflow가 바뀌는 것은 아닙니다. code completion을 쓰는 단계, agent surface를 쓰는 단계, multi-agent workflow를 쓰는 단계는 전혀 다른 조직 역량을 요구합니다. 따라서 AI ROI를 보려면 cohort progression과 PR/review/merge behavior를 함께 봐야 합니다.

---

## 개발자 실무 가이드: AI agent 기능을 설계할 때의 기준선

아래 기준선은 오늘 확인한 발표들을 실제 개발 checklist로 바꾼 것입니다. 모든 항목을 첫날부터 완벽하게 만들 필요는 없지만, 제품 요구사항 문서에는 반드시 들어가야 합니다.

### 요구사항 정의

- agent가 완료해야 하는 “업무 결과”를 명확히 정의한다. 답변 생성, 조사, 수정 제안, 실제 변경 실행은 서로 다른 결과다.
- 사용자가 원하는 결과와 조직이 허용하는 결과를 분리한다. 사용자는 자동 배포를 원해도 조직 정책은 승인 후 배포만 허용할 수 있다.
- 성공 기준을 사람이 읽는 품질 기준과 기계가 검증하는 조건으로 나눈다.
- 실패 시 agent가 멈춰야 하는 조건, 사람에게 escalation해야 하는 조건, 자동으로 재시도해도 되는 조건을 정한다.
- 외부 공식 source에 의존하는 기능은 freshness requirement를 명시한다.

### 권한과 보안

- agent용 service account를 사람 계정과 분리한다.
- read 권한과 write 권한을 tool 단위로 나눈다.
- write action은 diff preview와 approval token을 요구한다.
- secret은 prompt, trace, eval artifact에 남지 않도록 redaction한다.
- 권한 거절도 정상적인 성공 경로로 처리한다. 권한이 막혀서 안전했던 사례를 metric으로 본다.

### 상태와 지속성

- 장기 workflow는 current_step, pending_signal, owner, due_at, retry_count를 명시적으로 저장한다.
- 대기 시간은 process sleep이나 polling loop가 아니라 external event와 scheduler로 처리한다.
- resume 시 old conversation을 그대로 재주입하지 않고 필요한 state snapshot만 제공한다.
- state transition은 atomic하게 기록하고, 중복 webhook에 대해 idempotent하게 동작한다.
- 완료·취소·만료 상태를 분명히 나누고, 만료 상태에서 자동 실행이 재개되지 않게 한다.

### 평가와 품질

- golden workflow eval을 만든다. 성공 케이스보다 실패·대기·재개·권한 거절 케이스가 중요하다.
- model upgrade 전후에 같은 harness, 같은 budget, 같은 tool setup으로 비교한다.
- benchmark 점수는 harness와 함께 기록한다. tool access가 다른 benchmark는 같은 주장에 쓰지 않는다.
- 사용자 correction을 field-level로 저장해 반복 실패 cluster를 찾는다.
- agent가 cite한 source가 실제로 claim을 뒷받침하는지 source-grounding eval을 실행한다.

### 운영과 비용

- workflow별 unit economics를 계산한다. 모델 토큰, tool call, storage, review time, rerun cost를 포함한다.
- run duration이 길어지는 agent는 timeout과 budget exhaustion policy를 둔다.
- premium model 사용은 task class와 approval policy로 제한한다.
- agent가 생성한 PR, ticket, report의 downstream 처리 시간을 측정한다.
- ROI는 saved time만 보지 말고 defect reduction, MTTR reduction, coverage expansion, audit readiness로 나눠 본다.

---

## 운영 리더를 위한 의사결정 프레임

AI agent 도입은 기술 선택이면서 동시에 운영 모델 선택입니다. 다음 프레임으로 판단하면 과도한 기대와 과소한 통제를 피할 수 있습니다.

### 도입 목적

- 질문: 단순 응답 개선인가, 실제 workflow 자동화인가?
- 판단 기준: workflow 자동화라면 상태·권한·승인·복구 설계가 필수다.

### 위험 수준

- 질문: 실패가 비용·보안·법적 문제로 이어지는가?
- 판단 기준: 민감 영역이면 trusted access와 human approval을 기본값으로 둔다.

### 작업 시간

- 질문: 작업이 초 단위인가, 수일·수주 단위인가?
- 판단 기준: 장기 작업이면 durable state와 event resume이 필요하다.

### 도구 접근

- 질문: agent가 읽기만 하는가, 쓰기까지 하는가?
- 판단 기준: 쓰기 도구는 diff, approval, audit, rollback을 요구한다.

### 소스 신뢰성

- 질문: 공식 source와 내부 source를 구분하는가?
- 판단 기준: source type과 fetched time을 trace에 저장한다.

### 성과 측정

- 질문: active user만 보는가, workflow outcome을 보는가?
- 판단 기준: cohort progression과 business outcome을 함께 본다.

### 비용 통제

- 질문: 토큰 비용만 보는가, 전체 workflow 비용을 보는가?
- 판단 기준: unit economics를 workflow completion 기준으로 계산한다.

### 조직 준비도

- 질문: agent output을 검토할 사람이 있는가?
- 판단 기준: review queue와 escalation owner 없이는 자동화를 제한한다.

---

## 오늘의 실행 우선순위

오늘 발표를 우리 팀의 backlog로 바꾼다면 다음 순서가 현실적입니다.

1. **AI 기능 목록을 inventory화한다.** 어떤 기능이 답변만 하는지, 어떤 기능이 외부 시스템을 변경하는지 구분한다.
2. **tool permission matrix를 만든다.** 사용자, agent, tool, action, approval requirement를 한 장에 정리한다.
3. **장기 workflow 후보를 찾는다.** onboarding, 승인, 장애 후속 조치, 보안 remediation처럼 며칠 걸리는 업무를 state machine으로 모델링한다.
4. **eval harness를 만든다.** 단순 Q&A benchmark가 아니라 실제 workflow step, tool result, failure case를 포함한다.
5. **AI adoption dashboard를 재설계한다.** active user가 아니라 code-first, agent-first, multi-agent, PR/review impact로 본다.
6. **edge/cloud AI 분기 기준을 정한다.** 개인정보, 지연시간, 오프라인, 비용, 배터리 조건에 따라 on-device 후보를 분류한다.
7. **security와 SRE 영역의 agent 도입을 조심스럽게 pilot한다.** 하나의 서비스, 하나의 read-only 조사, 하나의 승인된 remediation loop부터 시작한다.
---

## 부록: 실무 심화 운영 노트

아래 부록은 오늘 다룬 발표를 실제 개발·보안·운영·조직 관리 항목으로 더 세분화한 것입니다. 길지만 목적은 단순합니다. AI agent를 production에 넣을 때 빠뜨리기 쉬운 질문을 가능한 한 실행 가능한 checklist로 바꾸는 것입니다.

### OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access

초점: 민감 capability의 승인·감사·목적 제한

#### 요구사항

- 요구사항-01: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 업무 결과를 명확히 명명한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-02: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 성공·실패·보류 상태를 분리한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-03: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 사람 승인 기준을 선제 정의한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-04: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 외부 공식 source 의존도를 기록한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-05: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 데이터 입력 범위를 제한한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-06: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 출력 소비자를 명확히 한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-07: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 금지 목적을 별도 목록으로 둔다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-08: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 업무 owner와 technical owner를 분리한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-09: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 초기 pilot 범위를 작게 잡는다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-10: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 장기 운영 지표를 요구사항에 포함한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-11: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 업무별 비용 상한을 둔다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-12: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 사용자 기대치를 화면에 설명한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-13: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 결과 해석 책임을 제품 문구로 명시한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-14: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 권한 상승 요청 흐름을 문서화한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-15: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 자동화 불가 조건을 명확히 한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 아키텍처

- 아키텍처-01: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 model gateway와 tool gateway를 분리한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-02: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 상태 저장소와 trace 저장소를 나눈다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-03: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 approval service를 별도 계층으로 둔다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-04: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 idempotency key를 모든 action에 부여한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-05: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 외부 이벤트 resume endpoint를 검증한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-06: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 권한 판단을 business logic 안에 숨기지 않는다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-07: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 policy engine을 reusable component로 만든다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-08: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 모델 fallback이 결과 의미를 바꾸지 않게 한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-09: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 source fetch 계층에 cache와 freshness를 둔다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-10: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 비동기 작업 queue를 관측 가능하게 만든다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-11: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 human review console을 MVP에 포함한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-12: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 run cancellation을 first-class 기능으로 만든다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-13: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 rollback hook을 workflow 끝이 아니라 설계 초기에 둔다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-14: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 tool result schema를 versioning한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-15: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 agent별 sandbox boundary를 정한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 보안

- 보안-01: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 least privilege를 agent role에 적용한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-02: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 secret redaction을 prompt 전후 모두에서 실행한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-03: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 외부 입력은 prompt injection 가능성을 전제로 처리한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-04: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 write tool에는 diff preview를 강제한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-05: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 민감 action은 multi-party approval을 고려한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-06: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 audit log는 수정 불가능한 저장소로 보낸다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-07: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 권한 거절을 error가 아닌 safety event로 기록한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-08: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 도메인 소유권 또는 대상 소유권 검증을 요구한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-09: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 cross-tenant data leak 테스트를 eval에 넣는다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-10: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 운영자 impersonation을 금지한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-11: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 session hijack 대비 토큰 수명을 짧게 둔다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-12: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 agent가 만든 파일과 사람이 만든 파일을 구분한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-13: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 공유 링크 생성은 기본 차단한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-14: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 network egress allowlist를 둔다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-15: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 보안 finding의 재현 절차를 자동 저장한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 평가

- 평가-01: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 golden path보다 실패 path를 더 많이 만든다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-02: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 장기 대기 후 resume case를 테스트한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-03: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 tool timeout과 partial failure를 넣는다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-04: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 권한 부족 시 안전하게 멈추는지 본다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-05: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 source가 오래된 경우 답변을 보류하는지 본다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-06: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 모델 변경 전후 같은 harness로 비교한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-07: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 scorer가 reward hacking에 취약하지 않은지 점검한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-08: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 human correction을 eval seed로 전환한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-09: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 비용 budget 초과 시 graceful stop을 검증한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-10: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 parallel run에서 race condition을 재현한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-11: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 중복 webhook이 이중 실행을 만들지 않는지 본다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-12: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 approval 거절 후 같은 action을 우회하지 않는지 본다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-13: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 민감 데이터 redaction snapshot을 검증한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-14: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 문서 링크가 실제 claim을 뒷받침하는지 본다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-15: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 회귀 실패를 release gate에 연결한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 운영

- 운영-01: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 run duration p50/p95/p99를 본다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-02: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 idle/resume latency를 본다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-03: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 tool failure cluster를 주간으로 triage한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-04: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 비용을 workflow completion 기준으로 계산한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-05: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 human review backlog를 capacity planning에 넣는다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-06: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 반복 correction을 product backlog로 전환한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-07: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 stale source answer를 별도 incident class로 둔다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-08: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 unsafe action blocked count를 긍정 지표로 본다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-09: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 agent timeout 원인을 분류한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-10: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 사용자 불신 신호를 qualitative review한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-11: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 운영 runbook에 agent 중단 절차를 넣는다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-12: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 external dependency outage 때 fallback을 점검한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-13: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 자동 생성 PR의 merge 후 결함률을 추적한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-14: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 agent가 만든 ticket의 reopen rate를 본다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-15: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 조직별 adoption cohort 변화를 본다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 데이터

- 데이터-01: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 입력 artifact와 출력 artifact를 별도 저장한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-02: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 source URL과 fetched_at을 함께 남긴다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-03: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 사용자 correction은 구조화해 저장한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-04: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 PII와 business secret을 분류한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-05: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 데이터 retention 기간을 workflow별로 다르게 둔다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-06: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 trace에서 reasoning이 아니라 operational evidence를 우선 저장한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-07: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 vector store에는 삭제와 재색인 절차를 둔다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-08: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 모델 학습 사용 가능 여부를 명시한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-09: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 dataset contamination 가능성을 기록한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-10: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 내부 문서 버전을 citation에 포함한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-11: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 temporary file lifecycle을 제한한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-12: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 export 가능한 report와 내부 audit log를 구분한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-13: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 데이터 품질 이슈를 agent failure와 연결한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-14: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 schema migration 시 old trace 해석을 보존한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-15: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 샘플링 로그와 전수 로그 기준을 나눈다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 비용

- 비용-01: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 premium model 사용 기준을 task class로 제한한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-02: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 agent retry마다 비용 원인을 기록한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-03: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 tool call 비용과 모델 비용을 같은 단위로 환산한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-04: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 review time을 비용 모델에 포함한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-05: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 긴 run은 budget checkpoint를 둔다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-06: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 idle time에는 compute를 점유하지 않는다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-07: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 edge inference와 cloud inference의 비용 경계를 비교한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-08: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 조직별 budget을 hard limit로 운영한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-09: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 실패한 run의 sunk cost를 추적한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-10: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 eval rerun 비용을 release planning에 넣는다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-11: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 source fetch cache로 중복 비용을 줄인다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-12: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 vector index 재생성 비용을 예측한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-13: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 automatic remediation의 재작업 비용을 본다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-14: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 비용 초과 시 사용자에게 선택지를 준다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-15: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 ROI를 시간 절감과 위험 감소로 나눠 계산한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### UX

- UX-01: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 agent가 무엇을 할 수 있고 못 하는지 화면에 밝힌다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-02: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 장기 작업은 현재 단계와 다음 대기 조건을 보여 준다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-03: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 승인 요청은 technical diff와 business impact를 함께 보여 준다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-04: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 결과 confidence보다 근거와 검증 상태를 보여 준다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-05: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 사용자가 쉽게 중단·되돌리기 할 수 있어야 한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-06: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 권한 부족 메시지는 다음 조치를 구체화한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-07: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 모바일 edge AI는 오프라인 가능 여부를 표시한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-08: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 보안 finding은 개발자가 바로 재현할 수 있게 한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-09: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 운영 조사 결과는 timeline 형태가 좋다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-10: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 AI 도입 dashboard는 팀별 성숙도를 비교 가능하게 한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-11: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 과도한 자동화보다 예측 가능한 흐름을 우선한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-12: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 사람이 수정한 내용이 다음에 반영되는지 보여 준다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-13: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 agent가 기다리는 이유를 명확히 말한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-14: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 검토 대기 queue를 숨기지 않는다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-15: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 실패 보고는 짧지만 action-oriented여야 한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 조직

- 조직-01: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 AI 운영 owner를 제품·보안·플랫폼이 공동으로 둔다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-02: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 pilot 팀의 성공을 전사 기준으로 과대 일반화하지 않는다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-03: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 agent 사용 교육은 prompt가 아니라 workflow 중심이어야 한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-04: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 보안팀과 법무팀이 release gate에 초기에 참여한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-05: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 SRE는 agent를 on-call 대체가 아니라 증강 도구로 도입한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-06: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 개발 리더는 adoption phase별 enablement를 설계한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-07: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 운영 회고에 agent action review를 포함한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-08: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 자동화가 줄인 toil과 새로 만든 review load를 같이 본다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-09: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 문서 품질은 agent 품질의 선행 지표다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-10: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 팀별 tooling fragmentation을 줄인다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-11: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 성과 보상은 사용량이 아니라 outcome 개선에 연결한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-12: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 위험이 큰 영역은 read-only pilot부터 시작한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-13: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 agent governance를 분기별로 재검토한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-14: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 vendor lock-in과 portability를 검토한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-15: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 고객 커뮤니케이션에 AI 사용 범위를 투명하게 둔다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 릴리스

- 릴리스-01: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 feature flag로 agent capability를 단계적으로 연다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-02: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 read-only에서 propose-only, approved-write 순서로 확장한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-03: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 model upgrade는 canary cohort에 먼저 적용한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-04: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 rollback은 모델과 tool policy 모두에 가능해야 한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-05: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 release note에 AI behavior change를 명시한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-06: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 eval pass 없이는 write capability를 열지 않는다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-07: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 긴 workflow 중간에 버전이 바뀌는 경우를 처리한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-08: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 기존 run의 state schema migration을 검증한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-09: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 운영 문서와 사용자 도움말을 동시에 업데이트한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-10: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 incident drill을 release 전에 실행한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-11: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 모니터링 dashboard가 먼저 준비되어야 한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-12: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 비용 alert threshold를 release checklist에 넣는다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-13: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 source connector 장애 시 degradation mode를 정의한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-14: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 human review staffing을 launch plan에 포함한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-15: OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access을/를 적용할 때는 post-release correction review를 예약한다. 이 항목은 민감 capability의 승인·감사·목적 제한 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

### AWS frontier agents: Security Agent와 DevOps Agent 일반 제공

초점: 장시간 자율 실행 agent의 보안·운영 통제

#### 요구사항

- 요구사항-01: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 업무 결과를 명확히 명명한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-02: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 성공·실패·보류 상태를 분리한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-03: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 사람 승인 기준을 선제 정의한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-04: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 외부 공식 source 의존도를 기록한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-05: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 데이터 입력 범위를 제한한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-06: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 출력 소비자를 명확히 한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-07: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 금지 목적을 별도 목록으로 둔다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-08: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 업무 owner와 technical owner를 분리한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-09: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 초기 pilot 범위를 작게 잡는다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-10: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 장기 운영 지표를 요구사항에 포함한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-11: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 업무별 비용 상한을 둔다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-12: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 사용자 기대치를 화면에 설명한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-13: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 결과 해석 책임을 제품 문구로 명시한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-14: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 권한 상승 요청 흐름을 문서화한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-15: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 자동화 불가 조건을 명확히 한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 아키텍처

- 아키텍처-01: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 model gateway와 tool gateway를 분리한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-02: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 상태 저장소와 trace 저장소를 나눈다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-03: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 approval service를 별도 계층으로 둔다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-04: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 idempotency key를 모든 action에 부여한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-05: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 외부 이벤트 resume endpoint를 검증한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-06: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 권한 판단을 business logic 안에 숨기지 않는다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-07: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 policy engine을 reusable component로 만든다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-08: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 모델 fallback이 결과 의미를 바꾸지 않게 한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-09: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 source fetch 계층에 cache와 freshness를 둔다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-10: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 비동기 작업 queue를 관측 가능하게 만든다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-11: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 human review console을 MVP에 포함한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-12: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 run cancellation을 first-class 기능으로 만든다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-13: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 rollback hook을 workflow 끝이 아니라 설계 초기에 둔다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-14: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 tool result schema를 versioning한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-15: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 agent별 sandbox boundary를 정한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 보안

- 보안-01: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 least privilege를 agent role에 적용한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-02: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 secret redaction을 prompt 전후 모두에서 실행한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-03: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 외부 입력은 prompt injection 가능성을 전제로 처리한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-04: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 write tool에는 diff preview를 강제한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-05: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 민감 action은 multi-party approval을 고려한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-06: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 audit log는 수정 불가능한 저장소로 보낸다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-07: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 권한 거절을 error가 아닌 safety event로 기록한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-08: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 도메인 소유권 또는 대상 소유권 검증을 요구한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-09: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 cross-tenant data leak 테스트를 eval에 넣는다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-10: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 운영자 impersonation을 금지한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-11: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 session hijack 대비 토큰 수명을 짧게 둔다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-12: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 agent가 만든 파일과 사람이 만든 파일을 구분한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-13: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 공유 링크 생성은 기본 차단한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-14: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 network egress allowlist를 둔다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-15: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 보안 finding의 재현 절차를 자동 저장한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 평가

- 평가-01: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 golden path보다 실패 path를 더 많이 만든다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-02: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 장기 대기 후 resume case를 테스트한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-03: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 tool timeout과 partial failure를 넣는다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-04: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 권한 부족 시 안전하게 멈추는지 본다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-05: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 source가 오래된 경우 답변을 보류하는지 본다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-06: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 모델 변경 전후 같은 harness로 비교한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-07: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 scorer가 reward hacking에 취약하지 않은지 점검한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-08: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 human correction을 eval seed로 전환한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-09: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 비용 budget 초과 시 graceful stop을 검증한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-10: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 parallel run에서 race condition을 재현한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-11: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 중복 webhook이 이중 실행을 만들지 않는지 본다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-12: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 approval 거절 후 같은 action을 우회하지 않는지 본다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-13: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 민감 데이터 redaction snapshot을 검증한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-14: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 문서 링크가 실제 claim을 뒷받침하는지 본다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-15: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 회귀 실패를 release gate에 연결한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 운영

- 운영-01: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 run duration p50/p95/p99를 본다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-02: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 idle/resume latency를 본다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-03: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 tool failure cluster를 주간으로 triage한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-04: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 비용을 workflow completion 기준으로 계산한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-05: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 human review backlog를 capacity planning에 넣는다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-06: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 반복 correction을 product backlog로 전환한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-07: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 stale source answer를 별도 incident class로 둔다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-08: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 unsafe action blocked count를 긍정 지표로 본다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-09: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 agent timeout 원인을 분류한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-10: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 사용자 불신 신호를 qualitative review한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-11: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 운영 runbook에 agent 중단 절차를 넣는다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-12: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 external dependency outage 때 fallback을 점검한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-13: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 자동 생성 PR의 merge 후 결함률을 추적한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-14: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 agent가 만든 ticket의 reopen rate를 본다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-15: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 조직별 adoption cohort 변화를 본다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 데이터

- 데이터-01: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 입력 artifact와 출력 artifact를 별도 저장한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-02: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 source URL과 fetched_at을 함께 남긴다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-03: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 사용자 correction은 구조화해 저장한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-04: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 PII와 business secret을 분류한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-05: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 데이터 retention 기간을 workflow별로 다르게 둔다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-06: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 trace에서 reasoning이 아니라 operational evidence를 우선 저장한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-07: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 vector store에는 삭제와 재색인 절차를 둔다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-08: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 모델 학습 사용 가능 여부를 명시한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-09: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 dataset contamination 가능성을 기록한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-10: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 내부 문서 버전을 citation에 포함한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-11: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 temporary file lifecycle을 제한한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-12: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 export 가능한 report와 내부 audit log를 구분한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-13: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 데이터 품질 이슈를 agent failure와 연결한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-14: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 schema migration 시 old trace 해석을 보존한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-15: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 샘플링 로그와 전수 로그 기준을 나눈다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 비용

- 비용-01: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 premium model 사용 기준을 task class로 제한한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-02: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 agent retry마다 비용 원인을 기록한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-03: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 tool call 비용과 모델 비용을 같은 단위로 환산한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-04: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 review time을 비용 모델에 포함한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-05: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 긴 run은 budget checkpoint를 둔다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-06: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 idle time에는 compute를 점유하지 않는다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-07: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 edge inference와 cloud inference의 비용 경계를 비교한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-08: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 조직별 budget을 hard limit로 운영한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-09: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 실패한 run의 sunk cost를 추적한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-10: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 eval rerun 비용을 release planning에 넣는다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-11: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 source fetch cache로 중복 비용을 줄인다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-12: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 vector index 재생성 비용을 예측한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-13: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 automatic remediation의 재작업 비용을 본다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-14: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 비용 초과 시 사용자에게 선택지를 준다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-15: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 ROI를 시간 절감과 위험 감소로 나눠 계산한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### UX

- UX-01: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 agent가 무엇을 할 수 있고 못 하는지 화면에 밝힌다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-02: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 장기 작업은 현재 단계와 다음 대기 조건을 보여 준다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-03: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 승인 요청은 technical diff와 business impact를 함께 보여 준다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-04: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 결과 confidence보다 근거와 검증 상태를 보여 준다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-05: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 사용자가 쉽게 중단·되돌리기 할 수 있어야 한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-06: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 권한 부족 메시지는 다음 조치를 구체화한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-07: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 모바일 edge AI는 오프라인 가능 여부를 표시한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-08: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 보안 finding은 개발자가 바로 재현할 수 있게 한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-09: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 운영 조사 결과는 timeline 형태가 좋다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-10: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 AI 도입 dashboard는 팀별 성숙도를 비교 가능하게 한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-11: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 과도한 자동화보다 예측 가능한 흐름을 우선한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-12: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 사람이 수정한 내용이 다음에 반영되는지 보여 준다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-13: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 agent가 기다리는 이유를 명확히 말한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-14: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 검토 대기 queue를 숨기지 않는다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-15: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 실패 보고는 짧지만 action-oriented여야 한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 조직

- 조직-01: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 AI 운영 owner를 제품·보안·플랫폼이 공동으로 둔다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-02: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 pilot 팀의 성공을 전사 기준으로 과대 일반화하지 않는다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-03: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 agent 사용 교육은 prompt가 아니라 workflow 중심이어야 한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-04: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 보안팀과 법무팀이 release gate에 초기에 참여한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-05: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 SRE는 agent를 on-call 대체가 아니라 증강 도구로 도입한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-06: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 개발 리더는 adoption phase별 enablement를 설계한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-07: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 운영 회고에 agent action review를 포함한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-08: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 자동화가 줄인 toil과 새로 만든 review load를 같이 본다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-09: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 문서 품질은 agent 품질의 선행 지표다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-10: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 팀별 tooling fragmentation을 줄인다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-11: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 성과 보상은 사용량이 아니라 outcome 개선에 연결한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-12: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 위험이 큰 영역은 read-only pilot부터 시작한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-13: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 agent governance를 분기별로 재검토한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-14: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 vendor lock-in과 portability를 검토한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-15: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 고객 커뮤니케이션에 AI 사용 범위를 투명하게 둔다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 릴리스

- 릴리스-01: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 feature flag로 agent capability를 단계적으로 연다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-02: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 read-only에서 propose-only, approved-write 순서로 확장한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-03: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 model upgrade는 canary cohort에 먼저 적용한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-04: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 rollback은 모델과 tool policy 모두에 가능해야 한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-05: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 release note에 AI behavior change를 명시한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-06: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 eval pass 없이는 write capability를 열지 않는다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-07: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 긴 workflow 중간에 버전이 바뀌는 경우를 처리한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-08: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 기존 run의 state schema migration을 검증한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-09: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 운영 문서와 사용자 도움말을 동시에 업데이트한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-10: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 incident drill을 release 전에 실행한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-11: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 모니터링 dashboard가 먼저 준비되어야 한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-12: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 비용 alert threshold를 release checklist에 넣는다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-13: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 source connector 장애 시 degradation mode를 정의한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-14: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 human review staffing을 launch plan에 포함한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-15: AWS frontier agents: Security Agent와 DevOps Agent 일반 제공을/를 적용할 때는 post-release correction review를 예약한다. 이 항목은 장시간 자율 실행 agent의 보안·운영 통제 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

### AWS Security Agent on-demand penetration testing GA

초점: attack-chain 검증과 remediation loop

#### 요구사항

- 요구사항-01: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 업무 결과를 명확히 명명한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-02: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 성공·실패·보류 상태를 분리한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-03: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 사람 승인 기준을 선제 정의한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-04: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 외부 공식 source 의존도를 기록한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-05: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 데이터 입력 범위를 제한한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-06: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 출력 소비자를 명확히 한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-07: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 금지 목적을 별도 목록으로 둔다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-08: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 업무 owner와 technical owner를 분리한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-09: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 초기 pilot 범위를 작게 잡는다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-10: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 장기 운영 지표를 요구사항에 포함한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-11: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 업무별 비용 상한을 둔다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-12: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 사용자 기대치를 화면에 설명한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-13: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 결과 해석 책임을 제품 문구로 명시한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-14: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 권한 상승 요청 흐름을 문서화한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-15: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 자동화 불가 조건을 명확히 한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 아키텍처

- 아키텍처-01: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 model gateway와 tool gateway를 분리한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-02: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 상태 저장소와 trace 저장소를 나눈다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-03: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 approval service를 별도 계층으로 둔다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-04: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 idempotency key를 모든 action에 부여한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-05: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 외부 이벤트 resume endpoint를 검증한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-06: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 권한 판단을 business logic 안에 숨기지 않는다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-07: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 policy engine을 reusable component로 만든다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-08: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 모델 fallback이 결과 의미를 바꾸지 않게 한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-09: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 source fetch 계층에 cache와 freshness를 둔다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-10: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 비동기 작업 queue를 관측 가능하게 만든다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-11: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 human review console을 MVP에 포함한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-12: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 run cancellation을 first-class 기능으로 만든다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-13: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 rollback hook을 workflow 끝이 아니라 설계 초기에 둔다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-14: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 tool result schema를 versioning한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-15: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 agent별 sandbox boundary를 정한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 보안

- 보안-01: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 least privilege를 agent role에 적용한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-02: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 secret redaction을 prompt 전후 모두에서 실행한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-03: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 외부 입력은 prompt injection 가능성을 전제로 처리한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-04: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 write tool에는 diff preview를 강제한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-05: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 민감 action은 multi-party approval을 고려한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-06: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 audit log는 수정 불가능한 저장소로 보낸다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-07: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 권한 거절을 error가 아닌 safety event로 기록한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-08: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 도메인 소유권 또는 대상 소유권 검증을 요구한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-09: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 cross-tenant data leak 테스트를 eval에 넣는다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-10: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 운영자 impersonation을 금지한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-11: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 session hijack 대비 토큰 수명을 짧게 둔다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-12: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 agent가 만든 파일과 사람이 만든 파일을 구분한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-13: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 공유 링크 생성은 기본 차단한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-14: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 network egress allowlist를 둔다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-15: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 보안 finding의 재현 절차를 자동 저장한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 평가

- 평가-01: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 golden path보다 실패 path를 더 많이 만든다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-02: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 장기 대기 후 resume case를 테스트한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-03: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 tool timeout과 partial failure를 넣는다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-04: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 권한 부족 시 안전하게 멈추는지 본다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-05: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 source가 오래된 경우 답변을 보류하는지 본다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-06: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 모델 변경 전후 같은 harness로 비교한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-07: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 scorer가 reward hacking에 취약하지 않은지 점검한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-08: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 human correction을 eval seed로 전환한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-09: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 비용 budget 초과 시 graceful stop을 검증한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-10: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 parallel run에서 race condition을 재현한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-11: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 중복 webhook이 이중 실행을 만들지 않는지 본다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-12: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 approval 거절 후 같은 action을 우회하지 않는지 본다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-13: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 민감 데이터 redaction snapshot을 검증한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-14: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 문서 링크가 실제 claim을 뒷받침하는지 본다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-15: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 회귀 실패를 release gate에 연결한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 운영

- 운영-01: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 run duration p50/p95/p99를 본다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-02: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 idle/resume latency를 본다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-03: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 tool failure cluster를 주간으로 triage한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-04: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 비용을 workflow completion 기준으로 계산한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-05: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 human review backlog를 capacity planning에 넣는다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-06: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 반복 correction을 product backlog로 전환한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-07: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 stale source answer를 별도 incident class로 둔다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-08: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 unsafe action blocked count를 긍정 지표로 본다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-09: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 agent timeout 원인을 분류한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-10: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 사용자 불신 신호를 qualitative review한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-11: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 운영 runbook에 agent 중단 절차를 넣는다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-12: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 external dependency outage 때 fallback을 점검한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-13: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 자동 생성 PR의 merge 후 결함률을 추적한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-14: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 agent가 만든 ticket의 reopen rate를 본다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-15: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 조직별 adoption cohort 변화를 본다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 데이터

- 데이터-01: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 입력 artifact와 출력 artifact를 별도 저장한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-02: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 source URL과 fetched_at을 함께 남긴다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-03: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 사용자 correction은 구조화해 저장한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-04: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 PII와 business secret을 분류한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-05: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 데이터 retention 기간을 workflow별로 다르게 둔다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-06: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 trace에서 reasoning이 아니라 operational evidence를 우선 저장한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-07: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 vector store에는 삭제와 재색인 절차를 둔다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-08: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 모델 학습 사용 가능 여부를 명시한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-09: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 dataset contamination 가능성을 기록한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-10: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 내부 문서 버전을 citation에 포함한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-11: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 temporary file lifecycle을 제한한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-12: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 export 가능한 report와 내부 audit log를 구분한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-13: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 데이터 품질 이슈를 agent failure와 연결한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-14: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 schema migration 시 old trace 해석을 보존한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-15: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 샘플링 로그와 전수 로그 기준을 나눈다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 비용

- 비용-01: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 premium model 사용 기준을 task class로 제한한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-02: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 agent retry마다 비용 원인을 기록한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-03: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 tool call 비용과 모델 비용을 같은 단위로 환산한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-04: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 review time을 비용 모델에 포함한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-05: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 긴 run은 budget checkpoint를 둔다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-06: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 idle time에는 compute를 점유하지 않는다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-07: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 edge inference와 cloud inference의 비용 경계를 비교한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-08: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 조직별 budget을 hard limit로 운영한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-09: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 실패한 run의 sunk cost를 추적한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-10: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 eval rerun 비용을 release planning에 넣는다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-11: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 source fetch cache로 중복 비용을 줄인다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-12: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 vector index 재생성 비용을 예측한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-13: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 automatic remediation의 재작업 비용을 본다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-14: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 비용 초과 시 사용자에게 선택지를 준다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-15: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 ROI를 시간 절감과 위험 감소로 나눠 계산한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### UX

- UX-01: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 agent가 무엇을 할 수 있고 못 하는지 화면에 밝힌다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-02: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 장기 작업은 현재 단계와 다음 대기 조건을 보여 준다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-03: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 승인 요청은 technical diff와 business impact를 함께 보여 준다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-04: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 결과 confidence보다 근거와 검증 상태를 보여 준다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-05: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 사용자가 쉽게 중단·되돌리기 할 수 있어야 한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-06: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 권한 부족 메시지는 다음 조치를 구체화한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-07: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 모바일 edge AI는 오프라인 가능 여부를 표시한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-08: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 보안 finding은 개발자가 바로 재현할 수 있게 한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-09: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 운영 조사 결과는 timeline 형태가 좋다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-10: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 AI 도입 dashboard는 팀별 성숙도를 비교 가능하게 한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-11: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 과도한 자동화보다 예측 가능한 흐름을 우선한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-12: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 사람이 수정한 내용이 다음에 반영되는지 보여 준다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-13: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 agent가 기다리는 이유를 명확히 말한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-14: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 검토 대기 queue를 숨기지 않는다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-15: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 실패 보고는 짧지만 action-oriented여야 한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 조직

- 조직-01: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 AI 운영 owner를 제품·보안·플랫폼이 공동으로 둔다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-02: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 pilot 팀의 성공을 전사 기준으로 과대 일반화하지 않는다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-03: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 agent 사용 교육은 prompt가 아니라 workflow 중심이어야 한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-04: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 보안팀과 법무팀이 release gate에 초기에 참여한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-05: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 SRE는 agent를 on-call 대체가 아니라 증강 도구로 도입한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-06: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 개발 리더는 adoption phase별 enablement를 설계한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-07: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 운영 회고에 agent action review를 포함한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-08: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 자동화가 줄인 toil과 새로 만든 review load를 같이 본다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-09: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 문서 품질은 agent 품질의 선행 지표다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-10: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 팀별 tooling fragmentation을 줄인다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-11: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 성과 보상은 사용량이 아니라 outcome 개선에 연결한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-12: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 위험이 큰 영역은 read-only pilot부터 시작한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-13: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 agent governance를 분기별로 재검토한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-14: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 vendor lock-in과 portability를 검토한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-15: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 고객 커뮤니케이션에 AI 사용 범위를 투명하게 둔다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 릴리스

- 릴리스-01: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 feature flag로 agent capability를 단계적으로 연다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-02: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 read-only에서 propose-only, approved-write 순서로 확장한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-03: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 model upgrade는 canary cohort에 먼저 적용한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-04: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 rollback은 모델과 tool policy 모두에 가능해야 한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-05: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 release note에 AI behavior change를 명시한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-06: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 eval pass 없이는 write capability를 열지 않는다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-07: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 긴 workflow 중간에 버전이 바뀌는 경우를 처리한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-08: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 기존 run의 state schema migration을 검증한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-09: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 운영 문서와 사용자 도움말을 동시에 업데이트한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-10: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 incident drill을 release 전에 실행한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-11: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 모니터링 dashboard가 먼저 준비되어야 한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-12: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 비용 alert threshold를 release checklist에 넣는다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-13: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 source connector 장애 시 degradation mode를 정의한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-14: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 human review staffing을 launch plan에 포함한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-15: AWS Security Agent on-demand penetration testing GA을/를 적용할 때는 post-release correction review를 예약한다. 이 항목은 attack-chain 검증과 remediation loop 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

### AWS Resilience Hub 생성형 AI SRE resilience journey

초점: 회복탄력성 정책과 failure-mode 거버넌스

#### 요구사항

- 요구사항-01: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 업무 결과를 명확히 명명한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-02: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 성공·실패·보류 상태를 분리한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-03: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 사람 승인 기준을 선제 정의한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-04: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 외부 공식 source 의존도를 기록한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-05: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 데이터 입력 범위를 제한한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-06: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 출력 소비자를 명확히 한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-07: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 금지 목적을 별도 목록으로 둔다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-08: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 업무 owner와 technical owner를 분리한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-09: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 초기 pilot 범위를 작게 잡는다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-10: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 장기 운영 지표를 요구사항에 포함한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-11: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 업무별 비용 상한을 둔다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-12: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 사용자 기대치를 화면에 설명한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-13: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 결과 해석 책임을 제품 문구로 명시한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-14: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 권한 상승 요청 흐름을 문서화한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-15: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 자동화 불가 조건을 명확히 한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 아키텍처

- 아키텍처-01: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 model gateway와 tool gateway를 분리한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-02: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 상태 저장소와 trace 저장소를 나눈다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-03: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 approval service를 별도 계층으로 둔다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-04: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 idempotency key를 모든 action에 부여한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-05: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 외부 이벤트 resume endpoint를 검증한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-06: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 권한 판단을 business logic 안에 숨기지 않는다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-07: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 policy engine을 reusable component로 만든다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-08: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 모델 fallback이 결과 의미를 바꾸지 않게 한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-09: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 source fetch 계층에 cache와 freshness를 둔다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-10: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 비동기 작업 queue를 관측 가능하게 만든다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-11: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 human review console을 MVP에 포함한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-12: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 run cancellation을 first-class 기능으로 만든다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-13: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 rollback hook을 workflow 끝이 아니라 설계 초기에 둔다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-14: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 tool result schema를 versioning한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-15: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 agent별 sandbox boundary를 정한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 보안

- 보안-01: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 least privilege를 agent role에 적용한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-02: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 secret redaction을 prompt 전후 모두에서 실행한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-03: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 외부 입력은 prompt injection 가능성을 전제로 처리한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-04: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 write tool에는 diff preview를 강제한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-05: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 민감 action은 multi-party approval을 고려한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-06: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 audit log는 수정 불가능한 저장소로 보낸다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-07: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 권한 거절을 error가 아닌 safety event로 기록한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-08: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 도메인 소유권 또는 대상 소유권 검증을 요구한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-09: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 cross-tenant data leak 테스트를 eval에 넣는다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-10: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 운영자 impersonation을 금지한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-11: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 session hijack 대비 토큰 수명을 짧게 둔다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-12: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 agent가 만든 파일과 사람이 만든 파일을 구분한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-13: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 공유 링크 생성은 기본 차단한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-14: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 network egress allowlist를 둔다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-15: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 보안 finding의 재현 절차를 자동 저장한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 평가

- 평가-01: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 golden path보다 실패 path를 더 많이 만든다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-02: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 장기 대기 후 resume case를 테스트한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-03: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 tool timeout과 partial failure를 넣는다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-04: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 권한 부족 시 안전하게 멈추는지 본다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-05: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 source가 오래된 경우 답변을 보류하는지 본다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-06: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 모델 변경 전후 같은 harness로 비교한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-07: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 scorer가 reward hacking에 취약하지 않은지 점검한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-08: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 human correction을 eval seed로 전환한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-09: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 비용 budget 초과 시 graceful stop을 검증한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-10: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 parallel run에서 race condition을 재현한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-11: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 중복 webhook이 이중 실행을 만들지 않는지 본다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-12: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 approval 거절 후 같은 action을 우회하지 않는지 본다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-13: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 민감 데이터 redaction snapshot을 검증한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-14: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 문서 링크가 실제 claim을 뒷받침하는지 본다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-15: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 회귀 실패를 release gate에 연결한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 운영

- 운영-01: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 run duration p50/p95/p99를 본다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-02: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 idle/resume latency를 본다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-03: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 tool failure cluster를 주간으로 triage한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-04: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 비용을 workflow completion 기준으로 계산한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-05: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 human review backlog를 capacity planning에 넣는다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-06: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 반복 correction을 product backlog로 전환한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-07: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 stale source answer를 별도 incident class로 둔다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-08: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 unsafe action blocked count를 긍정 지표로 본다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-09: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 agent timeout 원인을 분류한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-10: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 사용자 불신 신호를 qualitative review한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-11: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 운영 runbook에 agent 중단 절차를 넣는다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-12: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 external dependency outage 때 fallback을 점검한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-13: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 자동 생성 PR의 merge 후 결함률을 추적한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-14: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 agent가 만든 ticket의 reopen rate를 본다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-15: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 조직별 adoption cohort 변화를 본다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 데이터

- 데이터-01: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 입력 artifact와 출력 artifact를 별도 저장한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-02: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 source URL과 fetched_at을 함께 남긴다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-03: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 사용자 correction은 구조화해 저장한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-04: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 PII와 business secret을 분류한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-05: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 데이터 retention 기간을 workflow별로 다르게 둔다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-06: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 trace에서 reasoning이 아니라 operational evidence를 우선 저장한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-07: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 vector store에는 삭제와 재색인 절차를 둔다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-08: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 모델 학습 사용 가능 여부를 명시한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-09: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 dataset contamination 가능성을 기록한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-10: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 내부 문서 버전을 citation에 포함한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-11: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 temporary file lifecycle을 제한한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-12: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 export 가능한 report와 내부 audit log를 구분한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-13: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 데이터 품질 이슈를 agent failure와 연결한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-14: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 schema migration 시 old trace 해석을 보존한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-15: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 샘플링 로그와 전수 로그 기준을 나눈다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 비용

- 비용-01: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 premium model 사용 기준을 task class로 제한한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-02: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 agent retry마다 비용 원인을 기록한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-03: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 tool call 비용과 모델 비용을 같은 단위로 환산한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-04: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 review time을 비용 모델에 포함한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-05: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 긴 run은 budget checkpoint를 둔다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-06: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 idle time에는 compute를 점유하지 않는다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-07: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 edge inference와 cloud inference의 비용 경계를 비교한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-08: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 조직별 budget을 hard limit로 운영한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-09: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 실패한 run의 sunk cost를 추적한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-10: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 eval rerun 비용을 release planning에 넣는다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-11: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 source fetch cache로 중복 비용을 줄인다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-12: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 vector index 재생성 비용을 예측한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-13: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 automatic remediation의 재작업 비용을 본다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-14: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 비용 초과 시 사용자에게 선택지를 준다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-15: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 ROI를 시간 절감과 위험 감소로 나눠 계산한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### UX

- UX-01: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 agent가 무엇을 할 수 있고 못 하는지 화면에 밝힌다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-02: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 장기 작업은 현재 단계와 다음 대기 조건을 보여 준다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-03: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 승인 요청은 technical diff와 business impact를 함께 보여 준다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-04: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 결과 confidence보다 근거와 검증 상태를 보여 준다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-05: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 사용자가 쉽게 중단·되돌리기 할 수 있어야 한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-06: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 권한 부족 메시지는 다음 조치를 구체화한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-07: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 모바일 edge AI는 오프라인 가능 여부를 표시한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-08: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 보안 finding은 개발자가 바로 재현할 수 있게 한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-09: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 운영 조사 결과는 timeline 형태가 좋다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-10: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 AI 도입 dashboard는 팀별 성숙도를 비교 가능하게 한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-11: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 과도한 자동화보다 예측 가능한 흐름을 우선한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-12: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 사람이 수정한 내용이 다음에 반영되는지 보여 준다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-13: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 agent가 기다리는 이유를 명확히 말한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-14: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 검토 대기 queue를 숨기지 않는다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-15: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 실패 보고는 짧지만 action-oriented여야 한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 조직

- 조직-01: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 AI 운영 owner를 제품·보안·플랫폼이 공동으로 둔다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-02: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 pilot 팀의 성공을 전사 기준으로 과대 일반화하지 않는다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-03: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 agent 사용 교육은 prompt가 아니라 workflow 중심이어야 한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-04: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 보안팀과 법무팀이 release gate에 초기에 참여한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-05: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 SRE는 agent를 on-call 대체가 아니라 증강 도구로 도입한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-06: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 개발 리더는 adoption phase별 enablement를 설계한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-07: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 운영 회고에 agent action review를 포함한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-08: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 자동화가 줄인 toil과 새로 만든 review load를 같이 본다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-09: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 문서 품질은 agent 품질의 선행 지표다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-10: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 팀별 tooling fragmentation을 줄인다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-11: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 성과 보상은 사용량이 아니라 outcome 개선에 연결한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-12: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 위험이 큰 영역은 read-only pilot부터 시작한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-13: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 agent governance를 분기별로 재검토한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-14: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 vendor lock-in과 portability를 검토한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-15: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 고객 커뮤니케이션에 AI 사용 범위를 투명하게 둔다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 릴리스

- 릴리스-01: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 feature flag로 agent capability를 단계적으로 연다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-02: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 read-only에서 propose-only, approved-write 순서로 확장한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-03: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 model upgrade는 canary cohort에 먼저 적용한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-04: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 rollback은 모델과 tool policy 모두에 가능해야 한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-05: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 release note에 AI behavior change를 명시한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-06: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 eval pass 없이는 write capability를 열지 않는다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-07: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 긴 workflow 중간에 버전이 바뀌는 경우를 처리한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-08: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 기존 run의 state schema migration을 검증한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-09: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 운영 문서와 사용자 도움말을 동시에 업데이트한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-10: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 incident drill을 release 전에 실행한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-11: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 모니터링 dashboard가 먼저 준비되어야 한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-12: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 비용 alert threshold를 release checklist에 넣는다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-13: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 source connector 장애 시 degradation mode를 정의한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-14: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 human review staffing을 launch plan에 포함한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-15: AWS Resilience Hub 생성형 AI SRE resilience journey을/를 적용할 때는 post-release correction review를 예약한다. 이 항목은 회복탄력성 정책과 failure-mode 거버넌스 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

### Google ADK long-running agents

초점: durable state와 event-driven resume

#### 요구사항

- 요구사항-01: Google ADK long-running agents을/를 적용할 때는 업무 결과를 명확히 명명한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-02: Google ADK long-running agents을/를 적용할 때는 성공·실패·보류 상태를 분리한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-03: Google ADK long-running agents을/를 적용할 때는 사람 승인 기준을 선제 정의한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-04: Google ADK long-running agents을/를 적용할 때는 외부 공식 source 의존도를 기록한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-05: Google ADK long-running agents을/를 적용할 때는 데이터 입력 범위를 제한한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-06: Google ADK long-running agents을/를 적용할 때는 출력 소비자를 명확히 한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-07: Google ADK long-running agents을/를 적용할 때는 금지 목적을 별도 목록으로 둔다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-08: Google ADK long-running agents을/를 적용할 때는 업무 owner와 technical owner를 분리한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-09: Google ADK long-running agents을/를 적용할 때는 초기 pilot 범위를 작게 잡는다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-10: Google ADK long-running agents을/를 적용할 때는 장기 운영 지표를 요구사항에 포함한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-11: Google ADK long-running agents을/를 적용할 때는 업무별 비용 상한을 둔다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-12: Google ADK long-running agents을/를 적용할 때는 사용자 기대치를 화면에 설명한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-13: Google ADK long-running agents을/를 적용할 때는 결과 해석 책임을 제품 문구로 명시한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-14: Google ADK long-running agents을/를 적용할 때는 권한 상승 요청 흐름을 문서화한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-15: Google ADK long-running agents을/를 적용할 때는 자동화 불가 조건을 명확히 한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 아키텍처

- 아키텍처-01: Google ADK long-running agents을/를 적용할 때는 model gateway와 tool gateway를 분리한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-02: Google ADK long-running agents을/를 적용할 때는 상태 저장소와 trace 저장소를 나눈다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-03: Google ADK long-running agents을/를 적용할 때는 approval service를 별도 계층으로 둔다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-04: Google ADK long-running agents을/를 적용할 때는 idempotency key를 모든 action에 부여한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-05: Google ADK long-running agents을/를 적용할 때는 외부 이벤트 resume endpoint를 검증한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-06: Google ADK long-running agents을/를 적용할 때는 권한 판단을 business logic 안에 숨기지 않는다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-07: Google ADK long-running agents을/를 적용할 때는 policy engine을 reusable component로 만든다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-08: Google ADK long-running agents을/를 적용할 때는 모델 fallback이 결과 의미를 바꾸지 않게 한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-09: Google ADK long-running agents을/를 적용할 때는 source fetch 계층에 cache와 freshness를 둔다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-10: Google ADK long-running agents을/를 적용할 때는 비동기 작업 queue를 관측 가능하게 만든다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-11: Google ADK long-running agents을/를 적용할 때는 human review console을 MVP에 포함한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-12: Google ADK long-running agents을/를 적용할 때는 run cancellation을 first-class 기능으로 만든다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-13: Google ADK long-running agents을/를 적용할 때는 rollback hook을 workflow 끝이 아니라 설계 초기에 둔다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-14: Google ADK long-running agents을/를 적용할 때는 tool result schema를 versioning한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-15: Google ADK long-running agents을/를 적용할 때는 agent별 sandbox boundary를 정한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 보안

- 보안-01: Google ADK long-running agents을/를 적용할 때는 least privilege를 agent role에 적용한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-02: Google ADK long-running agents을/를 적용할 때는 secret redaction을 prompt 전후 모두에서 실행한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-03: Google ADK long-running agents을/를 적용할 때는 외부 입력은 prompt injection 가능성을 전제로 처리한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-04: Google ADK long-running agents을/를 적용할 때는 write tool에는 diff preview를 강제한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-05: Google ADK long-running agents을/를 적용할 때는 민감 action은 multi-party approval을 고려한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-06: Google ADK long-running agents을/를 적용할 때는 audit log는 수정 불가능한 저장소로 보낸다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-07: Google ADK long-running agents을/를 적용할 때는 권한 거절을 error가 아닌 safety event로 기록한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-08: Google ADK long-running agents을/를 적용할 때는 도메인 소유권 또는 대상 소유권 검증을 요구한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-09: Google ADK long-running agents을/를 적용할 때는 cross-tenant data leak 테스트를 eval에 넣는다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-10: Google ADK long-running agents을/를 적용할 때는 운영자 impersonation을 금지한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-11: Google ADK long-running agents을/를 적용할 때는 session hijack 대비 토큰 수명을 짧게 둔다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-12: Google ADK long-running agents을/를 적용할 때는 agent가 만든 파일과 사람이 만든 파일을 구분한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-13: Google ADK long-running agents을/를 적용할 때는 공유 링크 생성은 기본 차단한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-14: Google ADK long-running agents을/를 적용할 때는 network egress allowlist를 둔다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-15: Google ADK long-running agents을/를 적용할 때는 보안 finding의 재현 절차를 자동 저장한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 평가

- 평가-01: Google ADK long-running agents을/를 적용할 때는 golden path보다 실패 path를 더 많이 만든다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-02: Google ADK long-running agents을/를 적용할 때는 장기 대기 후 resume case를 테스트한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-03: Google ADK long-running agents을/를 적용할 때는 tool timeout과 partial failure를 넣는다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-04: Google ADK long-running agents을/를 적용할 때는 권한 부족 시 안전하게 멈추는지 본다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-05: Google ADK long-running agents을/를 적용할 때는 source가 오래된 경우 답변을 보류하는지 본다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-06: Google ADK long-running agents을/를 적용할 때는 모델 변경 전후 같은 harness로 비교한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-07: Google ADK long-running agents을/를 적용할 때는 scorer가 reward hacking에 취약하지 않은지 점검한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-08: Google ADK long-running agents을/를 적용할 때는 human correction을 eval seed로 전환한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-09: Google ADK long-running agents을/를 적용할 때는 비용 budget 초과 시 graceful stop을 검증한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-10: Google ADK long-running agents을/를 적용할 때는 parallel run에서 race condition을 재현한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-11: Google ADK long-running agents을/를 적용할 때는 중복 webhook이 이중 실행을 만들지 않는지 본다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-12: Google ADK long-running agents을/를 적용할 때는 approval 거절 후 같은 action을 우회하지 않는지 본다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-13: Google ADK long-running agents을/를 적용할 때는 민감 데이터 redaction snapshot을 검증한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-14: Google ADK long-running agents을/를 적용할 때는 문서 링크가 실제 claim을 뒷받침하는지 본다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-15: Google ADK long-running agents을/를 적용할 때는 회귀 실패를 release gate에 연결한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 운영

- 운영-01: Google ADK long-running agents을/를 적용할 때는 run duration p50/p95/p99를 본다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-02: Google ADK long-running agents을/를 적용할 때는 idle/resume latency를 본다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-03: Google ADK long-running agents을/를 적용할 때는 tool failure cluster를 주간으로 triage한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-04: Google ADK long-running agents을/를 적용할 때는 비용을 workflow completion 기준으로 계산한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-05: Google ADK long-running agents을/를 적용할 때는 human review backlog를 capacity planning에 넣는다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-06: Google ADK long-running agents을/를 적용할 때는 반복 correction을 product backlog로 전환한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-07: Google ADK long-running agents을/를 적용할 때는 stale source answer를 별도 incident class로 둔다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-08: Google ADK long-running agents을/를 적용할 때는 unsafe action blocked count를 긍정 지표로 본다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-09: Google ADK long-running agents을/를 적용할 때는 agent timeout 원인을 분류한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-10: Google ADK long-running agents을/를 적용할 때는 사용자 불신 신호를 qualitative review한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-11: Google ADK long-running agents을/를 적용할 때는 운영 runbook에 agent 중단 절차를 넣는다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-12: Google ADK long-running agents을/를 적용할 때는 external dependency outage 때 fallback을 점검한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-13: Google ADK long-running agents을/를 적용할 때는 자동 생성 PR의 merge 후 결함률을 추적한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-14: Google ADK long-running agents을/를 적용할 때는 agent가 만든 ticket의 reopen rate를 본다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-15: Google ADK long-running agents을/를 적용할 때는 조직별 adoption cohort 변화를 본다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 데이터

- 데이터-01: Google ADK long-running agents을/를 적용할 때는 입력 artifact와 출력 artifact를 별도 저장한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-02: Google ADK long-running agents을/를 적용할 때는 source URL과 fetched_at을 함께 남긴다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-03: Google ADK long-running agents을/를 적용할 때는 사용자 correction은 구조화해 저장한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-04: Google ADK long-running agents을/를 적용할 때는 PII와 business secret을 분류한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-05: Google ADK long-running agents을/를 적용할 때는 데이터 retention 기간을 workflow별로 다르게 둔다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-06: Google ADK long-running agents을/를 적용할 때는 trace에서 reasoning이 아니라 operational evidence를 우선 저장한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-07: Google ADK long-running agents을/를 적용할 때는 vector store에는 삭제와 재색인 절차를 둔다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-08: Google ADK long-running agents을/를 적용할 때는 모델 학습 사용 가능 여부를 명시한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-09: Google ADK long-running agents을/를 적용할 때는 dataset contamination 가능성을 기록한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-10: Google ADK long-running agents을/를 적용할 때는 내부 문서 버전을 citation에 포함한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-11: Google ADK long-running agents을/를 적용할 때는 temporary file lifecycle을 제한한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-12: Google ADK long-running agents을/를 적용할 때는 export 가능한 report와 내부 audit log를 구분한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-13: Google ADK long-running agents을/를 적용할 때는 데이터 품질 이슈를 agent failure와 연결한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-14: Google ADK long-running agents을/를 적용할 때는 schema migration 시 old trace 해석을 보존한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-15: Google ADK long-running agents을/를 적용할 때는 샘플링 로그와 전수 로그 기준을 나눈다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 비용

- 비용-01: Google ADK long-running agents을/를 적용할 때는 premium model 사용 기준을 task class로 제한한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-02: Google ADK long-running agents을/를 적용할 때는 agent retry마다 비용 원인을 기록한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-03: Google ADK long-running agents을/를 적용할 때는 tool call 비용과 모델 비용을 같은 단위로 환산한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-04: Google ADK long-running agents을/를 적용할 때는 review time을 비용 모델에 포함한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-05: Google ADK long-running agents을/를 적용할 때는 긴 run은 budget checkpoint를 둔다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-06: Google ADK long-running agents을/를 적용할 때는 idle time에는 compute를 점유하지 않는다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-07: Google ADK long-running agents을/를 적용할 때는 edge inference와 cloud inference의 비용 경계를 비교한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-08: Google ADK long-running agents을/를 적용할 때는 조직별 budget을 hard limit로 운영한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-09: Google ADK long-running agents을/를 적용할 때는 실패한 run의 sunk cost를 추적한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-10: Google ADK long-running agents을/를 적용할 때는 eval rerun 비용을 release planning에 넣는다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-11: Google ADK long-running agents을/를 적용할 때는 source fetch cache로 중복 비용을 줄인다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-12: Google ADK long-running agents을/를 적용할 때는 vector index 재생성 비용을 예측한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-13: Google ADK long-running agents을/를 적용할 때는 automatic remediation의 재작업 비용을 본다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-14: Google ADK long-running agents을/를 적용할 때는 비용 초과 시 사용자에게 선택지를 준다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-15: Google ADK long-running agents을/를 적용할 때는 ROI를 시간 절감과 위험 감소로 나눠 계산한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### UX

- UX-01: Google ADK long-running agents을/를 적용할 때는 agent가 무엇을 할 수 있고 못 하는지 화면에 밝힌다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-02: Google ADK long-running agents을/를 적용할 때는 장기 작업은 현재 단계와 다음 대기 조건을 보여 준다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-03: Google ADK long-running agents을/를 적용할 때는 승인 요청은 technical diff와 business impact를 함께 보여 준다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-04: Google ADK long-running agents을/를 적용할 때는 결과 confidence보다 근거와 검증 상태를 보여 준다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-05: Google ADK long-running agents을/를 적용할 때는 사용자가 쉽게 중단·되돌리기 할 수 있어야 한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-06: Google ADK long-running agents을/를 적용할 때는 권한 부족 메시지는 다음 조치를 구체화한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-07: Google ADK long-running agents을/를 적용할 때는 모바일 edge AI는 오프라인 가능 여부를 표시한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-08: Google ADK long-running agents을/를 적용할 때는 보안 finding은 개발자가 바로 재현할 수 있게 한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-09: Google ADK long-running agents을/를 적용할 때는 운영 조사 결과는 timeline 형태가 좋다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-10: Google ADK long-running agents을/를 적용할 때는 AI 도입 dashboard는 팀별 성숙도를 비교 가능하게 한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-11: Google ADK long-running agents을/를 적용할 때는 과도한 자동화보다 예측 가능한 흐름을 우선한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-12: Google ADK long-running agents을/를 적용할 때는 사람이 수정한 내용이 다음에 반영되는지 보여 준다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-13: Google ADK long-running agents을/를 적용할 때는 agent가 기다리는 이유를 명확히 말한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-14: Google ADK long-running agents을/를 적용할 때는 검토 대기 queue를 숨기지 않는다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-15: Google ADK long-running agents을/를 적용할 때는 실패 보고는 짧지만 action-oriented여야 한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 조직

- 조직-01: Google ADK long-running agents을/를 적용할 때는 AI 운영 owner를 제품·보안·플랫폼이 공동으로 둔다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-02: Google ADK long-running agents을/를 적용할 때는 pilot 팀의 성공을 전사 기준으로 과대 일반화하지 않는다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-03: Google ADK long-running agents을/를 적용할 때는 agent 사용 교육은 prompt가 아니라 workflow 중심이어야 한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-04: Google ADK long-running agents을/를 적용할 때는 보안팀과 법무팀이 release gate에 초기에 참여한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-05: Google ADK long-running agents을/를 적용할 때는 SRE는 agent를 on-call 대체가 아니라 증강 도구로 도입한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-06: Google ADK long-running agents을/를 적용할 때는 개발 리더는 adoption phase별 enablement를 설계한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-07: Google ADK long-running agents을/를 적용할 때는 운영 회고에 agent action review를 포함한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-08: Google ADK long-running agents을/를 적용할 때는 자동화가 줄인 toil과 새로 만든 review load를 같이 본다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-09: Google ADK long-running agents을/를 적용할 때는 문서 품질은 agent 품질의 선행 지표다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-10: Google ADK long-running agents을/를 적용할 때는 팀별 tooling fragmentation을 줄인다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-11: Google ADK long-running agents을/를 적용할 때는 성과 보상은 사용량이 아니라 outcome 개선에 연결한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-12: Google ADK long-running agents을/를 적용할 때는 위험이 큰 영역은 read-only pilot부터 시작한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-13: Google ADK long-running agents을/를 적용할 때는 agent governance를 분기별로 재검토한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-14: Google ADK long-running agents을/를 적용할 때는 vendor lock-in과 portability를 검토한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-15: Google ADK long-running agents을/를 적용할 때는 고객 커뮤니케이션에 AI 사용 범위를 투명하게 둔다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 릴리스

- 릴리스-01: Google ADK long-running agents을/를 적용할 때는 feature flag로 agent capability를 단계적으로 연다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-02: Google ADK long-running agents을/를 적용할 때는 read-only에서 propose-only, approved-write 순서로 확장한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-03: Google ADK long-running agents을/를 적용할 때는 model upgrade는 canary cohort에 먼저 적용한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-04: Google ADK long-running agents을/를 적용할 때는 rollback은 모델과 tool policy 모두에 가능해야 한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-05: Google ADK long-running agents을/를 적용할 때는 release note에 AI behavior change를 명시한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-06: Google ADK long-running agents을/를 적용할 때는 eval pass 없이는 write capability를 열지 않는다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-07: Google ADK long-running agents을/를 적용할 때는 긴 workflow 중간에 버전이 바뀌는 경우를 처리한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-08: Google ADK long-running agents을/를 적용할 때는 기존 run의 state schema migration을 검증한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-09: Google ADK long-running agents을/를 적용할 때는 운영 문서와 사용자 도움말을 동시에 업데이트한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-10: Google ADK long-running agents을/를 적용할 때는 incident drill을 release 전에 실행한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-11: Google ADK long-running agents을/를 적용할 때는 모니터링 dashboard가 먼저 준비되어야 한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-12: Google ADK long-running agents을/를 적용할 때는 비용 alert threshold를 release checklist에 넣는다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-13: Google ADK long-running agents을/를 적용할 때는 source connector 장애 시 degradation mode를 정의한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-14: Google ADK long-running agents을/를 적용할 때는 human review staffing을 launch plan에 포함한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-15: Google ADK long-running agents을/를 적용할 때는 post-release correction review를 예약한다. 이 항목은 durable state와 event-driven resume 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

### Google Tensor SDK Beta with LiteRT

초점: edge AI 배포와 단말 runtime 운영

#### 요구사항

- 요구사항-01: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 업무 결과를 명확히 명명한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-02: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 성공·실패·보류 상태를 분리한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-03: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 사람 승인 기준을 선제 정의한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-04: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 외부 공식 source 의존도를 기록한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-05: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 데이터 입력 범위를 제한한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-06: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 출력 소비자를 명확히 한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-07: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 금지 목적을 별도 목록으로 둔다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-08: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 업무 owner와 technical owner를 분리한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-09: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 초기 pilot 범위를 작게 잡는다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-10: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 장기 운영 지표를 요구사항에 포함한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-11: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 업무별 비용 상한을 둔다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-12: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 사용자 기대치를 화면에 설명한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-13: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 결과 해석 책임을 제품 문구로 명시한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-14: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 권한 상승 요청 흐름을 문서화한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-15: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 자동화 불가 조건을 명확히 한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 아키텍처

- 아키텍처-01: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 model gateway와 tool gateway를 분리한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-02: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 상태 저장소와 trace 저장소를 나눈다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-03: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 approval service를 별도 계층으로 둔다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-04: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 idempotency key를 모든 action에 부여한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-05: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 외부 이벤트 resume endpoint를 검증한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-06: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 권한 판단을 business logic 안에 숨기지 않는다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-07: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 policy engine을 reusable component로 만든다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-08: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 모델 fallback이 결과 의미를 바꾸지 않게 한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-09: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 source fetch 계층에 cache와 freshness를 둔다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-10: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 비동기 작업 queue를 관측 가능하게 만든다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-11: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 human review console을 MVP에 포함한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-12: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 run cancellation을 first-class 기능으로 만든다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-13: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 rollback hook을 workflow 끝이 아니라 설계 초기에 둔다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-14: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 tool result schema를 versioning한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-15: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 agent별 sandbox boundary를 정한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 보안

- 보안-01: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 least privilege를 agent role에 적용한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-02: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 secret redaction을 prompt 전후 모두에서 실행한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-03: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 외부 입력은 prompt injection 가능성을 전제로 처리한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-04: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 write tool에는 diff preview를 강제한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-05: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 민감 action은 multi-party approval을 고려한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-06: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 audit log는 수정 불가능한 저장소로 보낸다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-07: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 권한 거절을 error가 아닌 safety event로 기록한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-08: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 도메인 소유권 또는 대상 소유권 검증을 요구한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-09: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 cross-tenant data leak 테스트를 eval에 넣는다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-10: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 운영자 impersonation을 금지한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-11: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 session hijack 대비 토큰 수명을 짧게 둔다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-12: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 agent가 만든 파일과 사람이 만든 파일을 구분한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-13: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 공유 링크 생성은 기본 차단한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-14: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 network egress allowlist를 둔다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-15: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 보안 finding의 재현 절차를 자동 저장한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 평가

- 평가-01: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 golden path보다 실패 path를 더 많이 만든다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-02: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 장기 대기 후 resume case를 테스트한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-03: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 tool timeout과 partial failure를 넣는다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-04: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 권한 부족 시 안전하게 멈추는지 본다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-05: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 source가 오래된 경우 답변을 보류하는지 본다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-06: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 모델 변경 전후 같은 harness로 비교한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-07: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 scorer가 reward hacking에 취약하지 않은지 점검한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-08: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 human correction을 eval seed로 전환한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-09: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 비용 budget 초과 시 graceful stop을 검증한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-10: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 parallel run에서 race condition을 재현한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-11: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 중복 webhook이 이중 실행을 만들지 않는지 본다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-12: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 approval 거절 후 같은 action을 우회하지 않는지 본다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-13: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 민감 데이터 redaction snapshot을 검증한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-14: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 문서 링크가 실제 claim을 뒷받침하는지 본다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-15: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 회귀 실패를 release gate에 연결한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 운영

- 운영-01: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 run duration p50/p95/p99를 본다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-02: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 idle/resume latency를 본다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-03: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 tool failure cluster를 주간으로 triage한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-04: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 비용을 workflow completion 기준으로 계산한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-05: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 human review backlog를 capacity planning에 넣는다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-06: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 반복 correction을 product backlog로 전환한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-07: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 stale source answer를 별도 incident class로 둔다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-08: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 unsafe action blocked count를 긍정 지표로 본다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-09: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 agent timeout 원인을 분류한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-10: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 사용자 불신 신호를 qualitative review한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-11: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 운영 runbook에 agent 중단 절차를 넣는다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-12: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 external dependency outage 때 fallback을 점검한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-13: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 자동 생성 PR의 merge 후 결함률을 추적한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-14: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 agent가 만든 ticket의 reopen rate를 본다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-15: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 조직별 adoption cohort 변화를 본다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 데이터

- 데이터-01: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 입력 artifact와 출력 artifact를 별도 저장한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-02: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 source URL과 fetched_at을 함께 남긴다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-03: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 사용자 correction은 구조화해 저장한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-04: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 PII와 business secret을 분류한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-05: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 데이터 retention 기간을 workflow별로 다르게 둔다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-06: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 trace에서 reasoning이 아니라 operational evidence를 우선 저장한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-07: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 vector store에는 삭제와 재색인 절차를 둔다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-08: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 모델 학습 사용 가능 여부를 명시한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-09: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 dataset contamination 가능성을 기록한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-10: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 내부 문서 버전을 citation에 포함한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-11: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 temporary file lifecycle을 제한한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-12: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 export 가능한 report와 내부 audit log를 구분한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-13: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 데이터 품질 이슈를 agent failure와 연결한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-14: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 schema migration 시 old trace 해석을 보존한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-15: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 샘플링 로그와 전수 로그 기준을 나눈다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 비용

- 비용-01: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 premium model 사용 기준을 task class로 제한한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-02: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 agent retry마다 비용 원인을 기록한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-03: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 tool call 비용과 모델 비용을 같은 단위로 환산한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-04: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 review time을 비용 모델에 포함한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-05: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 긴 run은 budget checkpoint를 둔다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-06: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 idle time에는 compute를 점유하지 않는다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-07: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 edge inference와 cloud inference의 비용 경계를 비교한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-08: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 조직별 budget을 hard limit로 운영한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-09: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 실패한 run의 sunk cost를 추적한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-10: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 eval rerun 비용을 release planning에 넣는다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-11: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 source fetch cache로 중복 비용을 줄인다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-12: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 vector index 재생성 비용을 예측한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-13: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 automatic remediation의 재작업 비용을 본다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-14: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 비용 초과 시 사용자에게 선택지를 준다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-15: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 ROI를 시간 절감과 위험 감소로 나눠 계산한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### UX

- UX-01: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 agent가 무엇을 할 수 있고 못 하는지 화면에 밝힌다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-02: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 장기 작업은 현재 단계와 다음 대기 조건을 보여 준다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-03: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 승인 요청은 technical diff와 business impact를 함께 보여 준다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-04: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 결과 confidence보다 근거와 검증 상태를 보여 준다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-05: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 사용자가 쉽게 중단·되돌리기 할 수 있어야 한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-06: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 권한 부족 메시지는 다음 조치를 구체화한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-07: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 모바일 edge AI는 오프라인 가능 여부를 표시한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-08: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 보안 finding은 개발자가 바로 재현할 수 있게 한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-09: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 운영 조사 결과는 timeline 형태가 좋다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-10: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 AI 도입 dashboard는 팀별 성숙도를 비교 가능하게 한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-11: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 과도한 자동화보다 예측 가능한 흐름을 우선한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-12: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 사람이 수정한 내용이 다음에 반영되는지 보여 준다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-13: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 agent가 기다리는 이유를 명확히 말한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-14: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 검토 대기 queue를 숨기지 않는다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-15: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 실패 보고는 짧지만 action-oriented여야 한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 조직

- 조직-01: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 AI 운영 owner를 제품·보안·플랫폼이 공동으로 둔다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-02: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 pilot 팀의 성공을 전사 기준으로 과대 일반화하지 않는다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-03: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 agent 사용 교육은 prompt가 아니라 workflow 중심이어야 한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-04: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 보안팀과 법무팀이 release gate에 초기에 참여한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-05: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 SRE는 agent를 on-call 대체가 아니라 증강 도구로 도입한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-06: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 개발 리더는 adoption phase별 enablement를 설계한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-07: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 운영 회고에 agent action review를 포함한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-08: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 자동화가 줄인 toil과 새로 만든 review load를 같이 본다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-09: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 문서 품질은 agent 품질의 선행 지표다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-10: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 팀별 tooling fragmentation을 줄인다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-11: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 성과 보상은 사용량이 아니라 outcome 개선에 연결한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-12: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 위험이 큰 영역은 read-only pilot부터 시작한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-13: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 agent governance를 분기별로 재검토한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-14: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 vendor lock-in과 portability를 검토한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-15: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 고객 커뮤니케이션에 AI 사용 범위를 투명하게 둔다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 릴리스

- 릴리스-01: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 feature flag로 agent capability를 단계적으로 연다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-02: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 read-only에서 propose-only, approved-write 순서로 확장한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-03: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 model upgrade는 canary cohort에 먼저 적용한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-04: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 rollback은 모델과 tool policy 모두에 가능해야 한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-05: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 release note에 AI behavior change를 명시한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-06: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 eval pass 없이는 write capability를 열지 않는다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-07: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 긴 workflow 중간에 버전이 바뀌는 경우를 처리한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-08: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 기존 run의 state schema migration을 검증한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-09: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 운영 문서와 사용자 도움말을 동시에 업데이트한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-10: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 incident drill을 release 전에 실행한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-11: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 모니터링 dashboard가 먼저 준비되어야 한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-12: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 비용 alert threshold를 release checklist에 넣는다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-13: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 source connector 장애 시 degradation mode를 정의한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-14: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 human review staffing을 launch plan에 포함한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-15: Google Tensor SDK Beta with LiteRT을/를 적용할 때는 post-release correction review를 예약한다. 이 항목은 edge AI 배포와 단말 runtime 운영 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

### GitHub Copilot usage metrics API AI adoption phase

초점: 개발 조직의 AI 도입 성숙도 측정

#### 요구사항

- 요구사항-01: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 업무 결과를 명확히 명명한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-02: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 성공·실패·보류 상태를 분리한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-03: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 사람 승인 기준을 선제 정의한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-04: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 외부 공식 source 의존도를 기록한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-05: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 데이터 입력 범위를 제한한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-06: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 출력 소비자를 명확히 한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-07: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 금지 목적을 별도 목록으로 둔다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-08: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 업무 owner와 technical owner를 분리한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-09: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 초기 pilot 범위를 작게 잡는다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-10: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 장기 운영 지표를 요구사항에 포함한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-11: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 업무별 비용 상한을 둔다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-12: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 사용자 기대치를 화면에 설명한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-13: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 결과 해석 책임을 제품 문구로 명시한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-14: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 권한 상승 요청 흐름을 문서화한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 요구사항-15: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 자동화 불가 조건을 명확히 한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 아키텍처

- 아키텍처-01: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 model gateway와 tool gateway를 분리한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-02: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 상태 저장소와 trace 저장소를 나눈다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-03: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 approval service를 별도 계층으로 둔다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-04: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 idempotency key를 모든 action에 부여한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-05: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 외부 이벤트 resume endpoint를 검증한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-06: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 권한 판단을 business logic 안에 숨기지 않는다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-07: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 policy engine을 reusable component로 만든다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-08: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 모델 fallback이 결과 의미를 바꾸지 않게 한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-09: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 source fetch 계층에 cache와 freshness를 둔다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-10: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 비동기 작업 queue를 관측 가능하게 만든다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-11: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 human review console을 MVP에 포함한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-12: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 run cancellation을 first-class 기능으로 만든다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-13: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 rollback hook을 workflow 끝이 아니라 설계 초기에 둔다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-14: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 tool result schema를 versioning한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 아키텍처-15: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 agent별 sandbox boundary를 정한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 보안

- 보안-01: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 least privilege를 agent role에 적용한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-02: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 secret redaction을 prompt 전후 모두에서 실행한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-03: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 외부 입력은 prompt injection 가능성을 전제로 처리한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-04: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 write tool에는 diff preview를 강제한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-05: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 민감 action은 multi-party approval을 고려한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-06: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 audit log는 수정 불가능한 저장소로 보낸다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-07: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 권한 거절을 error가 아닌 safety event로 기록한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-08: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 도메인 소유권 또는 대상 소유권 검증을 요구한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-09: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 cross-tenant data leak 테스트를 eval에 넣는다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-10: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 운영자 impersonation을 금지한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-11: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 session hijack 대비 토큰 수명을 짧게 둔다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-12: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 agent가 만든 파일과 사람이 만든 파일을 구분한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-13: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 공유 링크 생성은 기본 차단한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-14: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 network egress allowlist를 둔다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 보안-15: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 보안 finding의 재현 절차를 자동 저장한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 평가

- 평가-01: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 golden path보다 실패 path를 더 많이 만든다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-02: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 장기 대기 후 resume case를 테스트한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-03: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 tool timeout과 partial failure를 넣는다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-04: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 권한 부족 시 안전하게 멈추는지 본다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-05: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 source가 오래된 경우 답변을 보류하는지 본다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-06: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 모델 변경 전후 같은 harness로 비교한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-07: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 scorer가 reward hacking에 취약하지 않은지 점검한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-08: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 human correction을 eval seed로 전환한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-09: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 비용 budget 초과 시 graceful stop을 검증한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-10: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 parallel run에서 race condition을 재현한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-11: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 중복 webhook이 이중 실행을 만들지 않는지 본다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-12: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 approval 거절 후 같은 action을 우회하지 않는지 본다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-13: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 민감 데이터 redaction snapshot을 검증한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-14: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 문서 링크가 실제 claim을 뒷받침하는지 본다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 평가-15: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 회귀 실패를 release gate에 연결한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 운영

- 운영-01: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 run duration p50/p95/p99를 본다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-02: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 idle/resume latency를 본다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-03: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 tool failure cluster를 주간으로 triage한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-04: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 비용을 workflow completion 기준으로 계산한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-05: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 human review backlog를 capacity planning에 넣는다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-06: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 반복 correction을 product backlog로 전환한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-07: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 stale source answer를 별도 incident class로 둔다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-08: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 unsafe action blocked count를 긍정 지표로 본다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-09: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 agent timeout 원인을 분류한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-10: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 사용자 불신 신호를 qualitative review한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-11: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 운영 runbook에 agent 중단 절차를 넣는다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-12: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 external dependency outage 때 fallback을 점검한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-13: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 자동 생성 PR의 merge 후 결함률을 추적한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-14: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 agent가 만든 ticket의 reopen rate를 본다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 운영-15: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 조직별 adoption cohort 변화를 본다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 데이터

- 데이터-01: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 입력 artifact와 출력 artifact를 별도 저장한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-02: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 source URL과 fetched_at을 함께 남긴다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-03: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 사용자 correction은 구조화해 저장한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-04: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 PII와 business secret을 분류한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-05: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 데이터 retention 기간을 workflow별로 다르게 둔다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-06: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 trace에서 reasoning이 아니라 operational evidence를 우선 저장한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-07: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 vector store에는 삭제와 재색인 절차를 둔다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-08: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 모델 학습 사용 가능 여부를 명시한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-09: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 dataset contamination 가능성을 기록한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-10: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 내부 문서 버전을 citation에 포함한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-11: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 temporary file lifecycle을 제한한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-12: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 export 가능한 report와 내부 audit log를 구분한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-13: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 데이터 품질 이슈를 agent failure와 연결한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-14: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 schema migration 시 old trace 해석을 보존한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 데이터-15: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 샘플링 로그와 전수 로그 기준을 나눈다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 비용

- 비용-01: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 premium model 사용 기준을 task class로 제한한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-02: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 agent retry마다 비용 원인을 기록한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-03: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 tool call 비용과 모델 비용을 같은 단위로 환산한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-04: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 review time을 비용 모델에 포함한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-05: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 긴 run은 budget checkpoint를 둔다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-06: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 idle time에는 compute를 점유하지 않는다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-07: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 edge inference와 cloud inference의 비용 경계를 비교한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-08: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 조직별 budget을 hard limit로 운영한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-09: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 실패한 run의 sunk cost를 추적한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-10: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 eval rerun 비용을 release planning에 넣는다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-11: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 source fetch cache로 중복 비용을 줄인다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-12: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 vector index 재생성 비용을 예측한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-13: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 automatic remediation의 재작업 비용을 본다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-14: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 비용 초과 시 사용자에게 선택지를 준다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 비용-15: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 ROI를 시간 절감과 위험 감소로 나눠 계산한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### UX

- UX-01: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 agent가 무엇을 할 수 있고 못 하는지 화면에 밝힌다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-02: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 장기 작업은 현재 단계와 다음 대기 조건을 보여 준다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-03: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 승인 요청은 technical diff와 business impact를 함께 보여 준다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-04: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 결과 confidence보다 근거와 검증 상태를 보여 준다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-05: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 사용자가 쉽게 중단·되돌리기 할 수 있어야 한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-06: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 권한 부족 메시지는 다음 조치를 구체화한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-07: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 모바일 edge AI는 오프라인 가능 여부를 표시한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-08: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 보안 finding은 개발자가 바로 재현할 수 있게 한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-09: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 운영 조사 결과는 timeline 형태가 좋다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-10: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 AI 도입 dashboard는 팀별 성숙도를 비교 가능하게 한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-11: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 과도한 자동화보다 예측 가능한 흐름을 우선한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-12: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 사람이 수정한 내용이 다음에 반영되는지 보여 준다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-13: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 agent가 기다리는 이유를 명확히 말한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-14: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 검토 대기 queue를 숨기지 않는다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- UX-15: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 실패 보고는 짧지만 action-oriented여야 한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 조직

- 조직-01: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 AI 운영 owner를 제품·보안·플랫폼이 공동으로 둔다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-02: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 pilot 팀의 성공을 전사 기준으로 과대 일반화하지 않는다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-03: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 agent 사용 교육은 prompt가 아니라 workflow 중심이어야 한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-04: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 보안팀과 법무팀이 release gate에 초기에 참여한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-05: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 SRE는 agent를 on-call 대체가 아니라 증강 도구로 도입한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-06: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 개발 리더는 adoption phase별 enablement를 설계한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-07: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 운영 회고에 agent action review를 포함한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-08: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 자동화가 줄인 toil과 새로 만든 review load를 같이 본다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-09: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 문서 품질은 agent 품질의 선행 지표다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-10: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 팀별 tooling fragmentation을 줄인다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-11: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 성과 보상은 사용량이 아니라 outcome 개선에 연결한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-12: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 위험이 큰 영역은 read-only pilot부터 시작한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-13: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 agent governance를 분기별로 재검토한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-14: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 vendor lock-in과 portability를 검토한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 조직-15: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 고객 커뮤니케이션에 AI 사용 범위를 투명하게 둔다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

#### 릴리스

- 릴리스-01: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 feature flag로 agent capability를 단계적으로 연다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-02: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 read-only에서 propose-only, approved-write 순서로 확장한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-03: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 model upgrade는 canary cohort에 먼저 적용한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-04: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 rollback은 모델과 tool policy 모두에 가능해야 한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-05: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 release note에 AI behavior change를 명시한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-06: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 eval pass 없이는 write capability를 열지 않는다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-07: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 긴 workflow 중간에 버전이 바뀌는 경우를 처리한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-08: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 기존 run의 state schema migration을 검증한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-09: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 운영 문서와 사용자 도움말을 동시에 업데이트한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-10: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 incident drill을 release 전에 실행한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-11: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 모니터링 dashboard가 먼저 준비되어야 한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-12: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 비용 alert threshold를 release checklist에 넣는다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-13: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 source connector 장애 시 degradation mode를 정의한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-14: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 human review staffing을 launch plan에 포함한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.
- 릴리스-15: GitHub Copilot usage metrics API AI adoption phase을/를 적용할 때는 post-release correction review를 예약한다. 이 항목은 개발 조직의 AI 도입 성숙도 측정 관점에서 단순 권장사항이 아니라 운영 중 감사, 장애 복구, 비용 통제, 사용자 신뢰를 동시에 좌우하는 기준선으로 다뤄야 한다.

---

## 소스 링크

- OpenAI Rosalind Biodefense와 GPT‑Rosalind trusted access: https://openai.com/index/strengthening-societal-resilience-with-rosalind-biodefense/
- AWS frontier agents: Security Agent와 DevOps Agent 일반 제공: https://aws.amazon.com/blogs/machine-learning/aws-launches-frontier-agents-for-security-testing-and-cloud-operations/
- AWS Security Agent: on-demand penetration testing GA: https://aws.amazon.com/blogs/security/aws-security-agent-on-demand-penetration-testing-now-generally-available/
- AWS Resilience Hub: 생성형 AI 기반 SRE resilience journey: https://aws.amazon.com/blogs/aws/introducing-the-next-generation-of-aws-resilience-hub-for-generative-ai-based-sre-resilience-journey/
- Google ADK long-running agents: pause, resume, durable state: https://developers.googleblog.com/en/build-long-running-ai-agents-that-pause-resume-and-never-lose-context-with-adk/
- Google Tensor SDK Beta with LiteRT: Pixel on-device AI 개발면 확대: https://developers.googleblog.com/en/google-tensor-sdk-beta-with-litert/
- GitHub Copilot usage metrics API: AI adoption phase cohort: https://github.blog/changelog/2026-05-29-copilot-usage-metrics-api-adds-cohorts-for-ai-adoption
- OpenAI News index: https://openai.com/news/
- AWS News Blog AI category: https://aws.amazon.com/blogs/aws/category/artificial-intelligence/
- AWS Machine Learning Blog index: https://aws.amazon.com/blogs/machine-learning/
- Google Developers Blog search/index: https://developers.googleblog.com/en/search/?q=AI
- GitHub Changelog RSS: https://github.blog/changelog/feed/

---

## 마무리

오늘의 AI 뉴스에서 가장 실용적인 결론은 간단합니다. **AI agent를 production에 넣는 순간, 우리는 모델 성능이 아니라 운영 시스템을 설계하고 있는 것입니다.** 모델은 더 강해지고, 도구 연결은 더 쉬워지고, 공식 제품들은 agentic workflow를 전면에 내세우고 있습니다. 그럴수록 개발자와 운영팀의 차별화 포인트는 더 명확해집니다. 누가 더 빨리 모델을 붙였는가가 아니라, 누가 더 안전하고, 더 검증 가능하고, 더 오래 지속되며, 더 비용 예측 가능한 agent 운영체계를 만들었는가가 승부를 가릅니다.

OpenAI의 trusted access, AWS의 frontier agents, Google의 durable ADK pattern, Google Tensor의 edge deployment, GitHub의 adoption cohort는 모두 같은 메시지를 줍니다. AI를 “기능”으로 보면 과소설계하게 되고, AI를 “운영 가능한 동료 시스템”으로 보면 필요한 구조가 보입니다. 이제 필요한 것은 더 많은 데모가 아니라 더 좋은 control plane입니다.

---

## 부록: 30일 실행 로드맵

이 로드맵은 오늘의 뉴스를 실제 조직 변화로 연결하기 위한 30일 기준안입니다. 모든 팀이 같은 속도로 움직일 필요는 없지만, AI agent를 실험 단계에서 운영 단계로 옮기려면 최소한 아래 순서의 확인이 필요합니다.

### 1주차: inventory와 위험 분류

현재 사용 중이거나 도입 예정인 AI 기능을 모두 나열하고, 기능별로 읽기 전용·제안 전용·승인 후 쓰기·자동 쓰기 등급을 붙인다.

#### Day 1

- **제품:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 제품 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **백엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 백엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **프론트엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 프론트엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **플랫폼:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 플랫폼 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **보안:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 보안 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **SRE:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. SRE 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **데이터:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 데이터 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **모바일:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 모바일 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **QA:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. QA 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **리더십:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 리더십 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.

#### Day 2

- **제품:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 제품 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **백엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 백엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **프론트엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 프론트엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **플랫폼:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 플랫폼 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **보안:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 보안 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **SRE:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. SRE 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **데이터:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 데이터 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **모바일:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 모바일 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **QA:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. QA 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **리더십:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 리더십 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.

#### Day 3

- **제품:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 제품 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **백엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 백엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **프론트엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 프론트엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **플랫폼:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 플랫폼 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **보안:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 보안 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **SRE:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. SRE 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **데이터:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 데이터 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **모바일:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 모바일 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **QA:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. QA 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **리더십:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 리더십 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.

#### Day 4

- **제품:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 제품 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **백엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 백엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **프론트엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 프론트엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **플랫폼:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 플랫폼 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **보안:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 보안 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **SRE:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. SRE 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **데이터:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 데이터 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **모바일:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 모바일 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **QA:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. QA 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **리더십:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 리더십 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.

#### Day 5

- **제품:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 제품 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **백엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 백엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **프론트엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 프론트엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **플랫폼:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 플랫폼 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **보안:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 보안 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **SRE:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. SRE 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **데이터:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 데이터 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **모바일:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 모바일 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **QA:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. QA 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **리더십:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 리더십 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.

#### Day 6

- **제품:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 제품 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **백엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 백엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **프론트엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 프론트엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **플랫폼:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 플랫폼 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **보안:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 보안 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **SRE:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. SRE 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **데이터:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 데이터 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **모바일:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 모바일 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **QA:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. QA 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **리더십:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 리더십 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.

#### Day 7

- **제품:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 제품 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **백엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 백엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **프론트엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 프론트엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **플랫폼:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 플랫폼 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **보안:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 보안 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **SRE:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. SRE 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **데이터:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 데이터 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **모바일:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 모바일 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **QA:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. QA 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **리더십:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 리더십 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.

### 2주차: state와 tool boundary 설계

장기 실행 workflow 후보를 골라 explicit state machine을 그리고, 각 단계에서 필요한 tool과 권한을 최소화한다.

#### Day 1

- **제품:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 제품 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **백엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 백엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **프론트엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 프론트엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **플랫폼:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 플랫폼 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **보안:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 보안 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **SRE:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. SRE 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **데이터:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 데이터 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **모바일:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 모바일 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **QA:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. QA 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **리더십:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 리더십 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.

#### Day 2

- **제품:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 제품 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **백엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 백엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **프론트엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 프론트엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **플랫폼:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 플랫폼 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **보안:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 보안 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **SRE:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. SRE 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **데이터:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 데이터 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **모바일:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 모바일 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **QA:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. QA 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **리더십:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 리더십 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.

#### Day 3

- **제품:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 제품 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **백엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 백엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **프론트엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 프론트엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **플랫폼:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 플랫폼 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **보안:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 보안 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **SRE:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. SRE 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **데이터:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 데이터 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **모바일:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 모바일 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **QA:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. QA 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **리더십:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 리더십 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.

#### Day 4

- **제품:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 제품 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **백엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 백엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **프론트엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 프론트엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **플랫폼:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 플랫폼 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **보안:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 보안 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **SRE:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. SRE 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **데이터:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 데이터 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **모바일:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 모바일 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **QA:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. QA 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **리더십:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 리더십 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.

#### Day 5

- **제품:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 제품 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **백엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 백엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **프론트엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 프론트엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **플랫폼:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 플랫폼 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **보안:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 보안 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **SRE:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. SRE 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **데이터:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 데이터 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **모바일:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 모바일 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **QA:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. QA 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **리더십:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 리더십 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.

#### Day 6

- **제품:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 제품 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **백엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 백엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **프론트엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 프론트엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **플랫폼:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 플랫폼 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **보안:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 보안 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **SRE:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. SRE 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **데이터:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 데이터 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **모바일:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 모바일 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **QA:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. QA 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **리더십:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 리더십 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.

#### Day 7

- **제품:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 제품 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **백엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 백엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **프론트엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 프론트엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **플랫폼:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 플랫폼 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **보안:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 보안 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **SRE:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. SRE 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **데이터:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 데이터 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **모바일:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 모바일 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **QA:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. QA 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **리더십:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 리더십 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.

### 3주차: eval과 관측성 구축

golden workflow, failure workflow, permission denied workflow, stale source workflow를 만들고, trace와 비용 dashboard를 연결한다.

#### Day 1

- **제품:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 제품 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **백엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 백엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **프론트엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 프론트엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **플랫폼:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 플랫폼 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **보안:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 보안 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **SRE:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. SRE 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **데이터:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 데이터 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **모바일:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 모바일 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **QA:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. QA 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **리더십:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 리더십 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.

#### Day 2

- **제품:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 제품 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **백엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 백엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **프론트엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 프론트엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **플랫폼:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 플랫폼 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **보안:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 보안 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **SRE:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. SRE 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **데이터:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 데이터 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **모바일:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 모바일 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **QA:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. QA 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **리더십:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 리더십 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.

#### Day 3

- **제품:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 제품 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **백엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 백엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **프론트엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 프론트엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **플랫폼:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 플랫폼 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **보안:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 보안 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **SRE:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. SRE 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **데이터:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 데이터 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **모바일:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 모바일 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **QA:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. QA 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **리더십:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 리더십 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.

#### Day 4

- **제품:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 제품 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **백엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 백엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **프론트엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 프론트엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **플랫폼:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 플랫폼 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **보안:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 보안 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **SRE:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. SRE 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **데이터:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 데이터 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **모바일:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 모바일 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **QA:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. QA 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **리더십:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 리더십 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.

#### Day 5

- **제품:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 제품 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **백엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 백엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **프론트엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 프론트엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **플랫폼:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 플랫폼 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **보안:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 보안 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **SRE:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. SRE 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **데이터:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 데이터 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **모바일:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 모바일 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **QA:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. QA 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **리더십:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 리더십 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.

#### Day 6

- **제품:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 제품 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **백엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 백엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **프론트엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 프론트엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **플랫폼:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 플랫폼 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **보안:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 보안 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **SRE:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. SRE 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **데이터:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 데이터 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **모바일:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 모바일 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **QA:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. QA 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **리더십:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 리더십 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.

#### Day 7

- **제품:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 제품 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **백엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 백엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **프론트엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 프론트엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **플랫폼:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 플랫폼 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **보안:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 보안 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **SRE:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. SRE 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **데이터:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 데이터 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **모바일:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 모바일 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **QA:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. QA 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **리더십:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 리더십 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.

### 4주차: pilot과 governance review

작은 팀 또는 작은 서비스에 read-only/p propose-only pilot을 열고, 사람 review와 운영 회고를 통해 write capability 확장 여부를 결정한다.

#### Day 1

- **제품:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 제품 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **백엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 백엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **프론트엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 프론트엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **플랫폼:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 플랫폼 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **보안:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 보안 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **SRE:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. SRE 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **데이터:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 데이터 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **모바일:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 모바일 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **QA:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. QA 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **리더십:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 리더십 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.

#### Day 2

- **제품:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 제품 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **백엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 백엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **프론트엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 프론트엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **플랫폼:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 플랫폼 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **보안:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 보안 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **SRE:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. SRE 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **데이터:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 데이터 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **모바일:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 모바일 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **QA:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. QA 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **리더십:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 리더십 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.

#### Day 3

- **제품:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 제품 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **백엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 백엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **프론트엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 프론트엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **플랫폼:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 플랫폼 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **보안:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 보안 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **SRE:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. SRE 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **데이터:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 데이터 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **모바일:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 모바일 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **QA:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. QA 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **리더십:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 리더십 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.

#### Day 4

- **제품:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 제품 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **백엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 백엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **프론트엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 프론트엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **플랫폼:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 플랫폼 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **보안:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 보안 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **SRE:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. SRE 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **데이터:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 데이터 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **모바일:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 모바일 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **QA:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. QA 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **리더십:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 리더십 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.

#### Day 5

- **제품:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 제품 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **백엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 백엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **프론트엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 프론트엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **플랫폼:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 플랫폼 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **보안:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 보안 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **SRE:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. SRE 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **데이터:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 데이터 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **모바일:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 모바일 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **QA:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. QA 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **리더십:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 리더십 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.

#### Day 6

- **제품:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 제품 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **백엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 백엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **프론트엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 프론트엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **플랫폼:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 플랫폼 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **보안:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 보안 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **SRE:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. SRE 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **데이터:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 데이터 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **모바일:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 모바일 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **QA:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. QA 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **리더십:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 리더십 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.

#### Day 7

- **제품:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 제품 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **백엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 백엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **프론트엔드:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 프론트엔드 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **플랫폼:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 플랫폼 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **보안:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 보안 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **SRE:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. SRE 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **데이터:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 데이터 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **모바일:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 모바일 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **QA:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. QA 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.
- **리더십:** 오늘의 목표는 AI agent 운영 기준을 추상 원칙에 머물게 하지 않고 실제 산출물로 남기는 것이다. 리더십 관점에서는 권한, 상태, 근거, 비용, 실패 복구 중 최소 하나를 명확한 문서·테스트·대시보드·코드 변경으로 연결해야 한다. 이 산출물은 다음 단계의 승인 기준이 되므로 “나중에 정리”하지 않는다.

### 로드맵 완료 기준

- AI 기능 inventory가 최신이다.
- agent tool permission matrix가 존재한다.
- 장기 workflow state machine 예시가 최소 1개 있다.
- eval harness가 CI 또는 수동 release gate와 연결되어 있다.
- 운영 dashboard에 비용, 실패, 승인, correction, blocked action 지표가 들어 있다.
- pilot 결과를 바탕으로 write capability 확장 여부를 판단할 수 있다.
