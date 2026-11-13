---
layout: post
title: "2026년 11월 13일 AI 뉴스: Gemini 4 Hydrogen, 에이전트 실행·권한·비용의 운영 설계"
date: 2026-11-13 11:30:00 +0900
categories: [ai-daily-news]
tags: [ai, news, gemini, hydrogen, agentcore, bedrock, llmon, trainium, security, finops, search]
permalink: /ai-daily-news/2026/11/13/ai-news-daily.html
---

# AI Daily News | 2026년 11월 13일

**확인 시각: 2026년 11월 13일 11:30 KST.** 검색 API는 키가 없어 동작하지 않았다. 따라서 Google 공식 RSS, AWS Machine Learning Blog RSS, GitHub Changelog RSS, Hugging Face Blog RSS와 OpenAI News 인덱스를 직접 확인하고, 주요 항목은 공식 원문 또는 공식 RSS 본문과 대조했다. Google·AWS의 11월 12일 오후·저녁 UTC 게시물은 한국시간으로 **11월 13일 새벽**에 해당한다. 이 글의 ‘오늘’은 한국시간 발행 시점까지 확인한 새 자료라는 뜻이지, 모든 회사가 13일 현지 시각에 발표했다는 뜻은 아니다. 벤치마크·성능·비용 절감 수치는 발표자의 측정 또는 제품 설명으로 취급하며, 사용자 환경에서 재현된 결과로 읽지 않는다.

오늘의 큰 줄기는 두 가지다. Google은 범용 개발·검색·업무용 모델 **Gemini 4 Hydrogen**을 발표하고 AI Studio·API·Search 등으로 넓혔다. AWS는 같은 날 에이전트 런타임, 지식베이스 접근 통제, 추론비용, 게이트웨이, Trainium 서빙 등에 관한 글을 연이어 게시했다. IBM Granite 팀은 긴 컨텍스트의 **지시와 데이터 경계**를 명시하는 LLMON 프리뷰를 공개했다. 서로 다른 제품이지만 질문은 같다. 빠른 모델을 고르는 것만으로는 충분하지 않다. 모델이 어떤 자료를 읽고, 누구 권한으로 행동하며, 얼마를 쓰고, 실패 시 어떻게 중단·복구되는지를 설계해야 한다.

## Top News — 발행 시점의 핵심 발표

1. **Google, Gemini 4 Hydrogen 공개.** Google은 일상적인 코딩·에이전트 작업에 맞춘 모델이라고 소개한다. 100만 토큰 컨텍스트 전체에 동일한 단가로 입력 100만 토큰당 1.50달러, 출력 100만 토큰당 7.50달러라고 발표했다. low·medium·high·xhigh 네 단계의 thinking 설정을 제공하며 high가 기본이다. Google AI Studio·Gemini API·Search·Gemini 앱 등으로 출시한다고 설명한다. [모델 발표](https://blog.google/innovation-and-ai/models-and-research/gemini-models/introducing-gemini-4-hydrogen/)
2. **Google Search, Hydrogen 적용 발표.** 복합 질문의 의도를 더 잘 파악하고, 여러 하위 주제를 병렬 검색하는 query fan-out 및 링크 제공과 시각적 답변을 개선한다는 설명이다. 모든 사용자를 대상으로 전 세계에 제공한다고 발표했지만 실제 화면과 기능의 세부 차이는 지역·계정·언어에서 확인해야 한다. [검색 발표](https://blog.google/products-and-platforms/products/search/gemini-4-hydrogen-search-upgrade/)
3. **AWS, 차세대 AgentCore Runtime 소개.** 장시간 실행되는 코드·브라우저·도구 사용 에이전트의 세션별 격리와 탄력적 시작·유휴 자원 회수를 다룬다. 이는 모델 품질 발표가 아니라 **실행 환경의 수명 주기와 격리**에 관한 글이다. [공식 글](https://aws.amazon.com/blogs/machine-learning/run-agents-securely-and-efficiently-with-the-next-generation-agentcore-runtime/)
4. **AWS, Managed Knowledge Base 도구에 세밀한 접근 통제 설계.** 에이전트가 검색 도구의 ‘누구로 검색할지’를 자유롭게 정하게 두지 않고, 인증된 사용자 토큰과 게이트웨이 검증을 사용해 요청자의 권한으로 자료를 제한하는 예시다. HR·다중 테넌트 검색에 특히 중요하다. [공식 글](https://aws.amazon.com/blogs/machine-learning/fine-grained-access-control-for-amazon-bedrock-managed-knowledge-base-tools/)
5. **AWS, Bedrock 추론비용의 네 가지 요청 설정 분석.** 프롬프트 캐시 TTL, 서비스 티어, 추론 노력, `maxTokens`가 모델·프롬프트를 바꾸지 않고도 비용·지연·동시성에 영향을 준다고 설명한다. 설정의 지원 여부는 모델·리전에 따라 달라진다. [공식 글](https://aws.amazon.com/blogs/machine-learning/four-amazon-bedrock-inference-choices-that-affect-cost/)
6. **AWS, ‘토큰당 가격’보다 ‘완료 작업당 비용’과 ROI를 제안.** 재시도, 도구 호출, 사람의 검토·승인, 에스컬레이션과 성공률을 포함해 비교하자는 운영 프레임워크다. 별도 글에서는 IAM 주체별 비용 귀속과 예산 액션을 소개했다. [작업당 비용](https://aws.amazon.com/blogs/machine-learning/optimizing-cost-per-task-and-proving-agent-roi-on-amazon-bedrock/) · [주체별 예산](https://aws.amazon.com/blogs/machine-learning/tokenomics-at-scale-track-and-cap-amazon-bedrock-spend-per-iam-principal-with-cur-2-0-and-aws-budgets/)
7. **AWS, Bedrock·LiteLLM 기반 셀프서비스 게이트웨이 예시.** Fargate의 LiteLLM 앞에 개발자별 키·예산·관찰을 두고 Bedrock Application Inference Profile을 호출하는 참조 구조다. 특정 코딩 도구가 한 API 주소로 여러 모델에 접근하도록 하되 키·로그·비용 상태는 별도 운영해야 한다. [공식 글](https://aws.amazon.com/blogs/machine-learning/building-a-self-service-llm-gateway-with-amazon-bedrock-and-litellm/)
8. **AWS, Trainium용 SGLang-Neuron 공개.** SGLang의 서버·요청 흐름을 유지하면서 Trainium 실행부를 플러그인으로 연결한다. PyTorch·Neuron Kernel Interface·`torch.compile` 및 prefill/decode 분리를 설명한다. 모델 품질 향상이 아니라 서빙 선택지 확대다. [공식 글](https://aws.amazon.com/blogs/machine-learning/deploy-frontier-ai-models-on-aws-trainium-with-sglang-neuron/)
9. **IBM Granite 팀, LLMON과 3B·8B 프리뷰 모델 공개.** 프롬프트의 지시·데이터·요구사항을 예약 토큰 경계로 분리하고 실행 대상과 입력을 연결한다. 정적 간접 프롬프트 인젝션 벤치마크에서 개선을 보고하지만, 글도 적응형·다회차 공격에 대한 보장을 주장하지 않는다. [작성자 발표](https://huggingface.co/blog/ibm-granite/llmon-an-llm-native-markup-language-now-in-granite)
10. **GitHub, Cloudflare 서비스 토큰 탐지 추가.** Secret scanning이 `cloudflare_access_service_token`을 탐지한다. 공개 저장소의 partner secret은 발급자에게 보고되며, 사용자 secret은 공개·비공개 저장소의 경고 대상이라고 설명한다. [공식 변경사항](https://github.blog/changelog/2026-11-12-secret-scanning-adds-a-detector-for-cloudflare)
11. **GitHub, Public monitoring 경고에 직접 링크 추가.** 기업 사용자가 개별 경고의 URL을 북마크하거나 접근권한이 있는 동료와 공유할 수 있다. 단순 UI 개선처럼 보여도 사고 대응 기록과 담당자 인계에 도움이 된다. [공식 변경사항](https://github.blog/changelog/2026-11-12-public-monitoring-alerts-now-have-direct-links)
12. **AWS, Natera 실험실 운영 에이전트 사례 공개.** Jira·Confluence 지식과 AgentCore를 연결해 장비 지원 티켓의 최초 응답을 개선한 사례다. AWS·Natera가 약 130배 빠른 최초 응답과 96.2% 자동 처리 범위를 보고하지만, 임상 결과나 독립 검증을 뜻하지 않는다. [공식 사례](https://aws.amazon.com/blogs/machine-learning/how-natera-designed-an-agentic-ai-system-for-lab-ops-with-amazon-bedrock-agentcore/)

## 배경 — 모델의 속도와 운영의 신뢰성은 다른 곱셈 항이다

AI 제품의 성과를 한 모델의 벤치마크 점수로 설명하기는 점점 어렵다. 사용자는 ‘질문 하나에 답이 나오는가’보다 ‘실제 업무가 올바른 권한으로 끝났는가’를 평가한다. 개발 에이전트가 코드를 고쳤어도 테스트를 생략하고 배포권한을 초과했다면 작업 성공이 아니다. HR 에이전트가 정확한 연차 숫자를 답했더라도 다른 직원의 기록을 검색했다면 실패다. 반대로 검색 도구가 503을 반환한 사고를 모델의 추론능력 부족으로 기록해서도 개선 방향이 틀어진다. 모델, 실행기, 인증, 검색, 도구, 관찰, 검토자가 각각 별개의 품질 항이다.

Google Hydrogen 발표가 보여 주는 것은 속도와 추론의 조절이다. 네 가지 thinking 수준과 멀티모델 오케스트레이션은 모든 일을 가장 깊은 추론으로 처리하는 비용을 줄이려는 설계다. AWS 발표 묶음은 그 반대쪽 운영 면을 보완한다. 에이전트가 오래 실행되면 세션을 격리해야 하고, 검색할 때 사용자 권한을 보존해야 하며, 토큰보다 업무의 총비용을 측정해야 한다. IBM의 LLMON은 문서와 도구 응답을 모델에게 보여 줄 때 ‘자료’가 ‘명령’으로 승격되지 않도록 표현 단계에서 경계를 두려는 시도다. 어느 한 층도 다른 층을 대체하지 않는다.

이 연결을 실무 의사결정으로 바꾸면 네 개의 질문이 남는다. 첫째, 새 모델이 **같은 데이터와 같은 실패 기준**에서 실제로 더 나은가. 둘째, 에이전트가 쓰는 권한은 사용자·세션·도구 단위로 제한되는가. 셋째, 품질이 좋아진 만큼 재시도·검토·에스컬레이션을 포함한 완료 작업당 비용이 낮아지는가. 넷째, 사건이 난 뒤 어떤 입력·모델·정책·검색 자료·도구 실행이 결과를 만들었는지 복원할 수 있는가. 오늘 소식은 이 네 질문에 사용할 부품을 제공하지만 각 조직의 정답을 자동으로 제공하지는 않는다.

## 1. Gemini 4 Hydrogen — ‘빠른 기본 모델’의 실질적인 검증법

Google은 Hydrogen을 Carbon·Argon처럼 깊고 긴 작업을 맡는 모델과 구분해, 일상적인 코딩·디버깅·다단계 에이전트 실행의 효율을 강조했다. 기본 high thinking 설정에서 Artificial Analysis Intelligence Index 51점, Argon 50점, 최고 xhigh 설정 54점이라고 소개하고, 이전 3.8 Flash 대비 작업 완료 시간이 2.5배 빠르고 Terminal-Bench 4.1 점수가 18.2%에서 57%로 늘었다고 주장한다. 출처와 평가 조건이 서로 다른 숫자를 한 표에 붙여 ‘모든 개발 업무에서 3배 좋다’고 읽으면 안 된다. 자체 발표의 벤치마크·선정된 파트너 실험은 **도입 후보를 고르는 자료**이지 우리 저장소의 생산성을 보장하는 약정이 아니다. [Google 모델 발표](https://blog.google/innovation-and-ai/models-and-research/gemini-models/introducing-gemini-4-hydrogen/)

가격 설명에는 특히 두 가지 분리가 필요하다. Google이 말한 입력 100만 토큰당 1.50달러와 출력 100만 토큰당 7.50달러는 **토큰 단가**다. 100만 토큰 컨텍스트 전체에 평탄한 단가가 적용된다는 설명은 긴 입력에 별도 장문 할증이 없다는 의미로 읽을 수 있지만, 긴 자료를 무조건 넣어도 좋다는 뜻은 아니다. 재검색·도구 출력·반복 추론·실패한 재시도가 늘면 총 토큰은 여전히 늘어난다. 저장소 전체를 매번 주입하는 패턴보다 파일 탐색으로 필요한 범위만 읽는 패턴이 실제 비용·속도 양쪽에서 유리할 수 있다. Google의 수치에 세금, 리전, 캐시, 제품별 과금 정책까지 모두 들어 있다고 가정해서도 안 된다.

네 가지 thinking 수준은 모델 선택보다 작은 단위의 실험을 가능하게 한다. 예를 들어 단순 정형 요약은 low, 코드 수정과 테스트 해석은 medium 또는 high, 모호한 장애 원인 분석은 high 또는 xhigh로 시작할 수 있다. 다만 작업 분류가 어려워지면 잘못된 low 라우팅이 오류·재시도를 낳아 오히려 비용이 커진다. 그러므로 태스크 유형별로 **성공률, 검토자 수정량, 평균·P95 완료시간, 토큰량, 재시도율**을 함께 기록해야 한다. 더 싼 요청이 더 비싼 완료 작업이 되는 경우를 포착하는 것이 핵심이다.

Google은 Antigravity Orchestrator가 Carbon과 Hydrogen을 세션 안에서 전환할 수 있다고 설명하며 Terminal-Bench 4.0에서 Carbon에 가까운 성공률, 평균 24% 적은 quota 사용과 19% 빠른 완료를 보고한다. 이는 특정 벤치마크의 결과다. 다른 도구 집합, 코드베이스, 네트워크와 리뷰 절차에서도 같은 절감이 나타난다고 보장하지 않는다. 멀티모델 라우팅을 도입한다면 실험 기록에 ‘최종 답변 모델’만 남겨서는 안 된다. 누가 작업을 분해했고 어느 단계에서 다른 모델로 넘어갔는지, 각 모델의 비용과 실패가 무엇인지 trace에 남겨야 라우터를 평가할 수 있다.

### 개발자에게 의미: 기존 모델 교체는 동일 조건의 과제로 판정한다

사용 중인 저장소에서 30~50개의 대표 과제를 모은다. 쉬운 문서 수정만 고르면 지능보다 속도에 유리한 결과가 나고, 대규모 리팩터링만 모으면 기본 모델의 일상적 가치가 보이지 않는다. 버그 재현, 패치, 테스트 수정, 대형 파일 탐색, 명세 해석, 안전한 실패, 모호한 권한 요청을 섞는다. 과제마다 성공 조건과 금지 행동을 분리한다. ‘테스트 통과’와 ‘무관한 파일을 바꾸지 않음’은 다른 항목이다. 모델에 같은 도구·시간·권한을 주고, 평가자가 모델명을 보지 않은 채 결과 diff와 실행 기록을 읽도록 하면 마케팅 문구보다 신뢰도 높은 결론을 낼 수 있다.

출력 토큰이 크게 늘 수 있는 설정이므로 `max_output_tokens` 또는 해당 API의 출력 상한을 작업별로 둔다. 길어진 추론이 사용자에게 보이는 답변 품질을 높이는지, 아니면 실패한 경로를 장황하게 기록하는지 구분한다. 긴 컨텍스트는 스캔 가능한 자료 범위를 넓히지만, 자료의 출처·버전·권한을 정리하지 못하면 오류를 확대할 수도 있다. 코드 에이전트라면 문맥 길이보다 **정확한 파일 선택, 최신 브랜치, 테스트 결과의 근거**가 먼저다.

### 운영 포인트: 모델 성능 발표와 서비스 계약을 구분한다

제품마다 롤아웃·기능·사용 한도가 다를 수 있다. AI Studio에서 호출된다고 해서 조직의 리전·로그·보존정책에 맞는다는 뜻은 아니다. 사내 데이터 입력 전에는 API 약관과 관리 설정을 확인하고, 모델 식별자·thinking 수준·사용 지역·실패 시 fallback을 설정으로 고정한다. 특히 자동 fallback은 장애를 감추면서 과금과 응답 특성을 바꿀 수 있다. 중요 업무에서는 조용한 전환보다 명시적 실패나 승인된 대체 모델 경로가 분석과 책임에 유리하다. 모델 카드는 안전성 검토의 출발점으로 읽되, 내부 도구 실행 권한의 최종 안전장치는 서버 측 정책이어야 한다.

## 2. Google Search 적용 — 검색 결과의 양보다 근거 연결이 중요하다

Google은 Hydrogen을 Search에 전 세계 모든 사용자 대상으로 도입한다고 발표했다. 복합 질문과 오타를 더 잘 다루고, query fan-out으로 관련 하위 질문을 동시에 검색해 더 넓은 링크를 보여 주며, 표·이미지 같은 시각적 응답을 강화한다는 설명이다. 개발자 관점에서 중요한 변화는 ‘검색 상단에 더 긴 요약이 나온다’가 아니다. 검색 엔진이 질문을 여러 세부 의도로 분해한다면 **어느 링크를 왜 근거로 선택했는지**를 사용자가 확인할 수 있어야 한다. 링크의 범위가 늘어도 원문 내용·게시일·정정 여부가 틀리면 좋은 뉴스나 RAG가 되지 않는다. [Google Search 발표](https://blog.google/products-and-platforms/products/search/gemini-4-hydrogen-search-upgrade/)

검색 기반 제품에는 발견·획득·검증·인용의 네 단계를 분리하는 편이 좋다. 발견 단계의 요약문은 후보를 찾는 데만 사용한다. 획득 단계에서 원문을 읽고, 검증 단계에서 발행 시각과 제공자의 공식 문서인지 확인하고, 인용 단계에서 실제 읽은 URL을 사용자에게 연결한다. 특히 검색 결과의 ‘최근’ 표시는 재수집·수정 시각일 수 있어 최초 발표와 다르다. `published_at`, `updated_at`, `retrieved_at`을 한 필드에 덮어쓰면 일간 뉴스와 가격 변경 감시기가 쉽게 거짓 최신 정보를 만들게 된다.

AI 답변의 링크가 더 다양해진다는 발표가 웹 전반의 유입·콘텐츠 품질에 어떤 결과를 낼지는 별도 측정 문제다. 사이트 운영자는 검색 결과 변화만 보고 기존 SEO 또는 접근성 작업을 중단할 이유가 없다. 기계가 인용할 수 있는 명확한 날짜, 제목, 원문 URL과 정정 기록을 제공하는 것이 인간 독자에게도 도움이 된다. 검색과 생성형 답변이 한 화면에 있어도 설명을 만든 모델과 사실의 원 출처는 다른 주체다. 인용의 책임을 모델의 자신감에 위임하지 않아야 한다.

## 3. AgentCore Runtime — 에이전트 세션은 채팅 메시지보다 오래 살아남는다

AWS의 차세대 AgentCore Runtime 글은 에이전트가 수 시간 동안 실행하며 코드·브라우저·민감한 자료에 접근하는 운영 양상을 전제로 한다. 각 세션의 격리와 빠른 시작을 동시에 제공하고, 모델·도구·사람의 응답을 기다리는 동안 자원을 회수해 비용을 줄이는 방향을 설명한다. AWS가 제시한 기동·메모리 절감 수치는 해당 서비스·측정 조건의 발표치이며 자체 워크로드의 약속된 P95 지연으로 바꾸어 읽어서는 안 된다. [AWS 공식 글](https://aws.amazon.com/blogs/machine-learning/run-agents-securely-and-efficiently-with-the-next-generation-agentcore-runtime/)

실행기 설계에서 첫 문제는 ‘에이전트가 코드를 실행할 수 있는가’가 아니라 **어떤 세션의 어떤 작업 공간에서 실행하는가**다. 사용자 A의 파일과 사용자 B의 파일을 분리해도 도구 자격증명이 공유되면 격리 효과가 작아진다. 세션별 파일시스템·네트워크·환경변수·임시 토큰·로그의 수명을 각각 정해야 한다. 코드 에이전트가 셸을 쓸 때는 프로세스가 종료된 뒤 남는 산출물과 캐시에도 주의해야 한다. 재사용되는 볼륨에 이전 세션의 문서가 남으면 인증 계층이 정상이어도 데이터 경계가 깨진다.

둘째 문제는 유휴 상태의 정의다. ‘모델 호출을 기다리는 시간’과 ‘사람 승인을 기다리는 시간’은 둘 다 CPU가 거의 없지만 재개 조건이 다르다. 사람 승인이 필요한 작업은 승인 요청 ID, 직전 단계의 체크포인트, 정책 버전, 만료시각을 영속 기록에 남겨야 한다. 무작정 세션 메모리에만 보관하면 런타임이 자원을 회수했을 때 재개할 수 없다. 반대로 재시도할 때 모든 도구 호출을 다시 실행하면 결제·티켓 생성·메일 전송 같은 비멱등 작업이 중복될 수 있다. 런타임의 scale-to-zero가 경제적으로 좋아 보여도 업무 레벨의 **체크포인트와 멱등성**을 별도로 설계해야 하는 이유다.

### 개발자에게 의미: 격리의 증명은 실패 주입에서 나온다

파일 읽기 테스트만으로 충분하지 않다. 세션 A에서 임시 파일·환경변수·네트워크 연결·캐시 키를 만들고 세션 B에서 보이지 않는지 확인한다. 세션을 강제로 종료했다가 재개했을 때 어떤 자격증명이 새로 발급되는지, 로그에 비밀이 남지 않는지 검사한다. 대량 병렬 실행 중에도 세션 간 자원 격리가 유지되는지 살핀다. 이 검증은 모델의 답변 정확도와 무관하지만, 장시간 에이전트 제품의 신뢰도에는 직접 영향을 준다.

### 운영 포인트: 예산·제한·승인은 별개의 회로다

런타임의 비용 최적화가 도구의 행동을 제한하지 않는다. 세션당 최대 실행시간, 동시 세션 수, 외부 요청량, 저장공간, 모델 토큰 예산을 각각 상한으로 둔다. 사용자와 업무 중요도에 따라 기본값을 달리하고, 초과 시 일시 중단인지 실패인지 명시한다. 실행이 길어지면 서비스 장애·정책 변경·사용자 취소가 중간에 발생할 수 있으므로 취소 신호 전달과 정리 단계도 제품 기능으로 다뤄야 한다.

## 4. 지식베이스 접근 통제 — ‘검색할 사용자’를 모델에게 묻지 않는다

AWS의 Managed Knowledge Base 예시는 공동 지식베이스를 쓰는 기업 에이전트에서 매우 실제적인 오류를 다룬다. 직원 A가 자기 부서 계획을 물었는데 모델이 검색 도구 인자에 부서 B 또는 다른 사용자 ID를 넣는다면 검색 결과가 권한을 넘어설 수 있다. 모델이 악의가 없어도 실수할 수 있고, 검색 결과 안의 프롬프트 인젝션이 인자를 바꾸게 할 수도 있다. AWS의 설계 원칙은 간결하다. **요청자의 신원은 모델 입력이 아니라 인증 경로에서 확정**한다. [AWS 공식 글](https://aws.amazon.com/blogs/machine-learning/fine-grained-access-control-for-amazon-bedrock-managed-knowledge-base-tools/)

원문 예시는 Cognito 로그인으로 받은 JWT를 Gateway 호출에 전달하고, 게이트웨이 authorizer가 서명·만료·클라이언트 ID를 검사하며, request interceptor가 검색 범위를 사용자 신원에 맞게 적용하는 흐름을 제시한다. 토큰에 이메일 claim을 추가하는 Lambda도 언급한다. 중요한 것은 서비스 이름보다 신뢰 경계다. 모델은 ‘찾을 질문’은 제안할 수 있지만 ‘누구 권한으로 찾는가’는 바꾸지 못해야 한다. 접근필터는 검색 호출이 발생하기 직전 서버 측에서 구성해야 하며, 검색 결과를 받은 뒤 답변문만 지우는 방식은 이미 권한 밖 데이터가 모델 컨텍스트에 들어간 뒤라 늦다.

HR 시스템에서는 경계가 더 복잡하다. 직원 본인은 자기 급여명세서를 볼 수 있지만 동료의 것을 볼 수 없다. 관리자는 소속 직원의 휴가 승인 상태를 볼 수 있어도 급여 상세를 볼 권한은 없을 수 있다. 인사 담당자는 처리 중인 사건의 일부 필드를 볼 수 있으나 모든 첨부 파일을 열 수 있는 것은 아니다. 이 차이를 ‘HR 관련 문서’라는 하나의 벡터 인덱스 태그로 처리하면 안 된다. 사용자·조직·문서 유형·시점·목적을 포함한 권한 정책을 데이터 검색에 적용하고, 에이전트가 생성한 질의가 이를 덮지 못하도록 해야 한다.

### 개발자에게 의미: 권한 테스트는 정답 테스트보다 앞에 온다

검증 데이터에는 두 개의 문서 집합을 의도적으로 비슷하게 만든다. 같은 제목의 A·B 부서 문서, 비슷한 직원 이름, 이전 부서 소속과 현재 소속, 공개 공지와 비공개 계획을 넣는다. A 사용자가 B 문서에 있는 정확한 숫자를 질문할 때 모델이 ‘모르겠다’ 또는 ‘접근권한이 없다’고 답하면서 실제 검색 결과에도 B 자료가 없었는지 확인한다. 문장을 조심스럽게 답했어도 도구가 B 자료를 읽었다면 권한 테스트는 실패다. 도구 trace에서 실제 검색 필터와 반환 문서 ID를 검사해야 하는 이유다.

관리자 권한 이관과 퇴사 처리는 캐시 정책에도 영향을 준다. 어제까지 허용되던 문서가 오늘은 금지될 수 있다. 인덱스의 ACL 메타데이터가 늦게 갱신되면 서버의 올바른 인증만으로 결과가 안전해지지 않는다. 문서 권한 변경 시 인덱스 업데이트 완료를 어떻게 확인할지, 긴 세션의 오래된 JWT를 언제 재검증할지 정해야 한다. 마지막으로 검색 로그 자체에 민감한 제목·질문이 들어갈 수 있으므로 저장·열람권한을 별도로 제한한다.

## 5. Bedrock 비용 설정 — 같은 모델도 요청 계약이 다르면 다른 제품이다

AWS는 프롬프트 캐시의 TTL, 서비스 티어, reasoning effort, `maxTokens` 네 선택을 비용 요소로 정리했다. 일반적인 ‘모델 가격표 비교’보다 운영에 가깝다. 같은 모델·같은 사용자 질문이어도 캐시 적중률과 사고 시 출력 상한, 우선 티어, 생각에 쓰는 토큰이 다르면 실제 청구액과 대기시간이 달라진다. 이 설정은 모델별 지원과 API 필드가 달라질 수 있으므로 문서와 실행 응답의 usage metadata로 확인해야 한다. [AWS 비용 설정 글](https://aws.amazon.com/blogs/machine-learning/four-amazon-bedrock-inference-choices-that-affect-cost/)

캐시는 공통 시스템 지시와 도구 명세가 자주 재사용될 때 유용하지만 캐시 접두부가 길수록 항상 이익이라는 뜻은 아니다. AWS 글은 지원되는 Anthropic 모델의 5분·1시간 TTL, 지원되는 GPT-5.6 모델의 30분 최소 TTL 등을 예로 든다. 모델·리전·요청 형식에 따라 달라지므로 그 숫자를 모든 Bedrock 모델의 규칙으로 일반화하면 안 된다. 멀티 테넌트에서는 한 테넌트의 검색 자료가 다른 테넌트의 캐시 접두부로 섞이지 않도록 분리해야 한다. 캐시 적중과 접근 권한은 서로 다른 검증 항목이다.

`maxTokens`는 비용 상한처럼 보이지만 이보다 정교한 역할을 한다. 너무 작으면 답변이 끊기고 도구 호출 체인이 망가져 재시도 비용이 생긴다. 너무 크면 모델이 실제로 쓰지 않아도 요청 시의 할당량 계산에서 동시성에 영향을 줄 수 있다고 AWS는 설명한다. 실측 작업별 출력 분포의 P95·P99를 보고 여유분을 주되, 생각 토큰이 같은 상한을 공유하는 모델이면 그 조건으로 측정해야 한다. **최대 출력 길이**는 사고 시 피해를 줄이는 한 방어선이지만 권한 검증이나 유해행동 제한과 같지는 않다.

### 개발자에게 의미: 비용 실험의 단위는 ‘성공한 결과’다

실험 표에는 모델과 프롬프트 버전뿐 아니라 캐시 TTL, 캐시 읽기·쓰기 토큰, thinking 수준, 티어, 상한, 재시도 횟수, 성공 판정, 사람 수정 시간을 넣는다. 평균 요청당 0.01달러가 절약되어도 완료율이 떨어져 사람이 다시 처리하면 비용은 늘 수 있다. 고객 응대의 경우 한 통의 이메일 답장, 문서 추출은 한 건의 수락된 JSON, 코드 에이전트는 리뷰를 통과한 패치가 작업 단위다. ‘요청당 비용’으로만 최적화하면 실패한 요청을 숨기게 된다.

### 운영 포인트: 예산 초과는 알림과 차단을 나누어 설계한다

AWS의 별도 글은 IAM 주체 태그와 CUR 2.0·Cost Explorer로 비용을 귀속하고 AWS Budgets 액션으로 Deny 정책을 적용하는 방식을 소개한다. 그러나 하루의 비용 현황을 나중에 집계하는 시스템과 실시간 요청 차단은 같은 시간축이 아니다. 예산 경계에 가까워질 때도 이미 진행 중인 요청, 태그가 누락된 공유 역할, 비모델 인프라 비용은 별도 규칙이 필요하다. 예산 액션이 실제로 어떤 IAM 권한을 언제 막는지 파일럿 계정에서 검증하고, 서비스 운영을 전부 멈출지 저우선 업무만 지연시킬지 결정해야 한다. [AWS 주체별 예산 글](https://aws.amazon.com/blogs/machine-learning/tokenomics-at-scale-track-and-cap-amazon-bedrock-spend-per-iam-principal-with-cur-2-0-and-aws-budgets/)

## 6. ‘작업당 비용’ — 에이전트 ROI는 완료율과 사람의 시간을 포함한다

AWS의 ROI 글은 토큰 단가가 낮은 모델이 반드시 싼 모델은 아니라는 점을 사례로 풀었다. 같은 텍스트도 토크나이저마다 토큰 수가 다르고, 출력이 장황하거나 도구 스키마를 잘못 읽으면 수정 루프가 늘어난다. 생각 토큰, 캐시 읽기·쓰기, 재시도, 사람의 승인과 에스컬레이션이 업무 완료 비용을 좌우한다. 이는 단순한 재무 논쟁이 아니다. 측정 단위를 바꾸면 개발 우선순위가 달라진다. 가장 저렴한 모델로 전면 교체하는 대신, 빠른 모델은 쉬운 질의에, 깊은 모델은 실패가 큰 판단에 배치할 근거가 생긴다. [AWS ROI 글](https://aws.amazon.com/blogs/machine-learning/optimizing-cost-per-task-and-proving-agent-roi-on-amazon-bedrock/)

실무에서 유용한 기본 식은 ‘완료 작업당 비용 = 모든 시도의 모델·도구·인프라 비용 + 검토자의 시간 + 실패 후 에스컬레이션 비용을 성공한 작업 수로 나눈 값’이다. 계산의 정확한 항목은 업무별로 달라진다. 결제·의료·HR에서는 오답 수정뿐 아니라 이의 제기·감사 대응 비용도 중요하다. 반면 사내 초안 작성은 승인자의 수정 시간이 핵심일 수 있다. ROI가 좋다는 주장을 하려면 기존 인간 프로세스의 기준선을 기록해야 한다. 도입 전 처리시간과 오류율을 모른다면 도입 후 숫자가 좋아 보여도 개선폭을 알 수 없다.

AWS는 holdout 실험과 다차원 점수표를 제안한다. 여기서 중요한 것은 선택 편향을 막는 것이다. 에이전트에게 쉬운 문의만 보내고 사람에게 까다로운 문의를 남기면 에이전트의 성공률이 높아도 업무 전체의 효과는 작을 수 있다. 조건이 비슷한 사례를 대조하고, 모델이 못 한 건을 분모에서 빼지 않는다. 인간 검토가 들어간 자동화는 ‘완전 자동 처리’와 별도 범주로 표시한다. 관리자에게 보고할 때는 완료율·수정량·대기시간·사고율·총비용을 함께 보여 주어야 단일 절감률의 착시를 피할 수 있다.

## 7. LiteLLM 게이트웨이 — 한 API 주소는 단일 책임자를 뜻하지 않는다

AWS는 Bedrock Application Inference Profile을 LiteLLM으로 감싼 OpenAI 호환 API 예시를 공개했다. Fargate의 프록시, 개발자별 가상 키, RDS의 사용 상태, Valkey 캐시, Secrets Manager, CloudWatch 및 별도 관찰 도구를 포함한다. 개발자는 코딩 도구의 base URL 하나를 설정해 쓸 수 있고, 플랫폼 팀은 모델 목록과 팀별 사용량을 중앙에서 다룰 수 있다. 다만 게이트웨이가 생긴다고 정책이 자동으로 완성되지는 않는다. [AWS 게이트웨이 글](https://aws.amazon.com/blogs/machine-learning/building-a-self-service-llm-gateway-with-amazon-bedrock-and-litellm/)

원문에서 특히 실무적인 경고는 **LiteLLM이 사용자 지정 모델의 비용을 내장 가격표에서 찾지 못하면 0달러로 취급할 수 있다**는 것이다. 이때 가상 키의 spend 값이 오르지 않아 예산 제어가 작동하지 않을 수 있다. 모델 이름과 연결된 가격을 명시하고, 청구 자료와 게이트웨이 집계가 맞는지 대조해야 한다. API가 호출된다는 ‘스모크 테스트’만 통과해선 운영 가능한 게이트웨이가 아니다. 인증, 사용량 계측, 차단, 장애 처리, 로그 비밀 제거까지 시험해야 한다.

키의 권한도 분리해야 한다. 개발자별 키가 있어도 게이트웨이의 AWS 역할이 너무 넓으면 잘못된 라우팅이 고비용 모델이나 다른 리전으로 갈 수 있다. 모델별 허용 목록, 요청 크기, 동시성, 프로젝트별 예산을 정책으로 두고, 변경 기록을 남긴다. 예산이 0으로 보이는 구성 오류를 탐지하기 위해 실제 비용이 발생하는 샘플 호출을 한 번 실행한 뒤 집계값과 청구 추정치를 비교하는 운영 테스트가 필요하다. 개인정보가 들어간 프롬프트 전문 로깅은 디버깅에는 편하지만 접근권한·보존기간·마스킹 설계 없이는 새로운 위험이 된다.

## 8. SGLang-Neuron — 추론 칩 선택을 애플리케이션 API와 분리

AWS·RadixArk의 SGLang-Neuron 발표는 SGLang의 API 서버와 요청 수명주기를 유지하면서 Trainium 실행부를 out-of-tree 플러그인으로 제공한다. 플러그인은 Trainium 특화 모델·attention·MoE·graph runner를 구현하고, TorchNeuron의 PyTorch 디바이스 경로, Neuron Kernel Interface의 커널, `torch.compile`을 활용한다고 설명한다. prefill 서버와 decode 서버를 나누어 KV 캐시를 NIXL과 EFA로 옮기는 구성도 소개한다. 이는 모델 자체의 새 지능이 아니라 하드웨어·서빙 선택지의 변화다. [AWS 공식 글](https://aws.amazon.com/blogs/machine-learning/deploy-frontier-ai-models-on-aws-trainium-with-sglang-neuron/)

개발팀이 알아야 할 것은 같은 API 모양이 같은 지연·정확도·운영성을 보장하지 않는다는 점이다. 모델이 다른 칩에서 구동될 때는 지원 모델 목록, 양자화, 최대 컨텍스트, 배치 크기, 첫 토큰 지연, 초당 토큰, 긴 출력의 메모리 압력, 도구 호출 형식 등을 검증해야 한다. prefill/decode 분리는 입력이 긴 요청과 출력이 긴 요청의 자원 수요를 다르게 다루는 방법이지만, 네트워크·KV 전송의 비용과 장애 지점을 추가한다. 유휴 GPU/Trainium 비용만 보지 말고 목표 처리량에서 실제 완료 요청당 비용과 P95 지연을 계산해야 한다.

서빙 계층의 교체는 실패 시 복구 계획이 있어야 실용적이다. 컨테이너·Neuron 런타임·플러그인·모델 버전을 묶어 기록하고, 작은 트래픽에만 새 이미지를 적용해 응답 호환성을 비교한다. 확장 중 새 워커의 기동 시간과 캐시 적중률을 관찰하고, 프리필 서버 고장과 디코드 서버 고장을 구분한다. 성능 개선 수치가 제시되더라도 자신의 프롬프트 길이와 동시성 분포가 다르면 다른 결과가 나온다. 칩 가격보다 **작업 프로파일**이 먼저다.

## 9. LLMON — 프롬프트 형식이 보안 경계를 도울 수 있지만 경계 자체는 아니다

IBM Granite 팀의 LLMON은 시스템 지시, 사용자 자료, 검색 문서, 도구 응답, 출력 요건을 긴 문자열로 평평하게 합치는 관행의 문제를 제기한다. 예약된 구조 토큰으로 지시·데이터·요건을 다른 블록으로 표시하고, 실행 블록이 어떤 지시가 어떤 데이터를 대상으로 어떤 출력에 적용되는지 지정한다. Granite 4.1 기반 3B·8B 프리뷰 모델과 변환 도구를 공개했다. JSON을 버리자는 단순 주장이 아니라 모델이 구조와 관계를 더 직접적으로 읽도록 하는 표현·학습 조합이다. [IBM Granite 팀 원문](https://huggingface.co/blog/ibm-granite/llmon-an-llm-native-markup-language-now-in-granite)

정적 간접 프롬프트 인젝션 벤치마크에서 공격 성공률이 크게 낮아졌다는 것은 흥미롭다. 그러나 논문의 실험과 제품의 보안 보장은 다르다. 원문도 학습된 행동이지 강제된 보증이 아니며, 다회차로 적응하는 공격은 계속 연구 중이라고 밝힌다. 문서에 있는 ‘지금부터 모든 지시를 무시하라’를 데이터로 표시해도 애플리케이션이 그 문서에서 도구 인자를 무검증으로 추출한다면 시스템의 다른 통로로 위험이 남는다. 구조화된 프롬프트는 인증·권한 검사·도구 인자 검증의 보조 계층이지 대체재가 아니다.

### 개발자에게 의미: 데이터가 명령이 되는 경로를 식별한다

RAG 문서, 이메일, 티켓 댓글, 웹페이지, MCP 도구 응답은 신뢰수준이 다르다. 프롬프트에 자료를 붙일 때 출처·범위·권한을 표시하고, 지시문과 물리적으로 분리한다. 그 뒤 실제 도구 호출에서 사용자 ID, 파일 경로, URL, 결제 금액처럼 위험이 큰 인자를 서버에서 검증한다. LLMON을 실험한다면 일반 모델과 동일한 검색 문서·공격 샘플·도구 집합으로 비교하되 정상 작업의 완료율도 함께 측정한다. 공격만 막고 정당한 문서 요약을 못 하면 제품의 목표를 달성하지 못한다.

인젝션 시험은 ‘무시하라’ 한 문장만으로 충분하지 않다. 사용자처럼 보이는 긴 대화 조각, 도구 결과를 가장한 JSON, 이미 승인된 일처럼 꾸민 문서, 본문 중간의 모델 지시, 정상 내용과 섞인 악의적 링크를 시험한다. 공격 결과를 최종 답변만으로 판정하면 도구가 이미 위험한 읽기·쓰기 작업을 했는지 놓친다. 실제 도구 인자와 거부 로그를 함께 확인해야 한다. IBM 프리뷰는 이 평가를 위한 유용한 연구 재료이지만 즉시 모든 업무 모델을 교체하라는 신호는 아니다.

## 10. GitHub 보안 변경 — 탐지와 사고 대응의 마지막 1미터

GitHub는 Cloudflare 서비스 토큰의 새 secret scanning 탐지 패턴을 추가했다. Cloudflare Access의 서비스 토큰을 저장소에 커밋했다면 경고가 뜰 수 있지만, 새 탐지가 생긴다고 과거 유출의 영향이 사라지는 것은 아니다. 경고가 발생했을 때 실제 토큰인지 확인하고 **발급자 측에서 폐기·회전**한 뒤 유출 경로를 고쳐야 한다. Git 이력에서 문자열만 지워도 이미 복제된 비밀의 효력은 남는다. GitHub는 공개 저장소에서 탐지된 partner secret의 발급자 보고와 user secret 경고의 범위를 구분해 설명한다. [GitHub 변경사항](https://github.blog/changelog/2026-11-12-secret-scanning-adds-a-detector-for-cloudflare)

Public monitoring 경고의 직접 링크는 작은 기능이다. 그러나 보안 사고가 여러 조직과 저장소를 거칠 때는 재현 가능한 경고 ID와 접근권한이 있는 링크가 중요하다. 화면 스크린샷만 보내면 경고가 해결·재발·재분류되었는지 추적하기 어렵다. 링크를 사건 티켓에 붙이고 탐지 시각, 토큰 회전 여부, 영향 범위, 재발 방지 변경을 기록하면 업무 인계가 쉬워진다. 직접 링크가 있다는 사실은 모든 팀원이 경고를 볼 수 있다는 뜻이 아니며, GitHub는 접근권한이 있는 동료와 공유하라고 안내한다. [GitHub 변경사항](https://github.blog/changelog/2026-11-12-public-monitoring-alerts-now-have-direct-links)

AI 개발 환경은 서비스 토큰을 더 자주 접할 수 있다. 에이전트가 자동으로 `.env` 파일을 열거나 CI 로그를 요약하고, 예시 설정을 커밋하는 과정에서 비밀이 퍼질 수 있다. secret scanning은 사고를 줄이는 사후 탐지다. 처음부터 코딩 에이전트가 필요한 최소 범위의 자격증명만 보게 하고, 도구 출력에서 비밀을 가리고, 커밋 전 검사를 거는 것이 더 앞선 통제다. 발견 후에는 ‘에이전트가 실수했다’로 끝내지 말고 비밀이 왜 작업 공간에 있었고 어떤 도구 경로로 노출됐는지 추적해야 한다.

## 11. Natera 사례 — 운영 지식 자동화에서 무엇을 측정해야 하나

AWS는 Natera의 실험실 장비 지원 업무에 AgentCore를 연결한 사례를 소개했다. 장비별 고장 패턴과 해결 경험이 담당자에게 흩어져 있고, 하루 65건 이상의 티켓과 기존 평균 17.4시간의 최초 응답 시간이 부담이었다고 설명한다. 시스템은 티켓에서 장비와 증상을 분류하고 지식베이스를 찾은 뒤 원인 가설, 우선순위가 매겨진 점검 단계, 확신도 라벨이 있는 구조화된 보고서를 만든다. Jira 연동과 평가 루프를 포함한다. AWS·Natera는 약 130배 빨라진 최초 응답과 96.2% 자동 처리 범위를 보고했다. 이는 공급자 사례의 **처리량·응답 지표**이지 장비 수리의 최종 성공률이나 환자 결과에 관한 독립 검증이 아니다. [AWS·Natera 사례](https://aws.amazon.com/blogs/machine-learning/how-natera-designed-an-agentic-ai-system-for-lab-ops-with-amazon-bedrock-agentcore/)

이 사례의 진짜 교훈은 ‘에이전트를 붙이면 130배 빨라진다’가 아니다. 기관 지식이 퇴사와 팀 이동으로 사라지는 문제를 데이터로 정의하고, 티켓·문서·사람의 피드백을 연결했으며, 최초 응답 같은 명시적 KPI를 택했다는 점이다. 하지만 최초 응답을 빠르게 보내는 일과 올바른 수리 절차를 수행하는 일은 다르다. 대응 후 재오픈율, 잘못된 부품 교체, 현장 검토자의 수정량, 실제 장비 가동 복구시간을 함께 추적해야 운영 효용을 알 수 있다. 자동 생성 보고서의 확신도 라벨을 기술자의 책임을 대체하는 숫자로 읽어서는 안 된다.

HR 도메인으로 옮기면 비교적 안전한 초기 업무는 직원의 승인된 정책 문서에서 일반 절차를 찾아 담당자에게 근거를 보여 주는 것이다. 채용·징계·급여 결정의 자동 집행은 훨씬 높은 증명 책임이 필요하다. 실제 업무 흐름의 어느 단계가 정보 안내이고 어느 단계가 법적·재무적 결정인지 나누면 에이전트를 어디에 넣을지 명확해진다. 사례 발표를 기술 스택의 체크리스트로 복제하기보다 **업무 단위, 지식의 소유자, 최종 승인자, 실패 비용**을 먼저 적는 편이 빠르다.

## 개발자에게 의미 — 이번 주에 실행할 수 있는 검증 순서

1. **태스크와 실패를 정의한다.** 실제 이슈·문서 질의·장애 보고에서 대표 샘플을 모으고, 정답·허용 도구·금지 권한·승인 조건을 분리한다. 모델 평가와 권한 평가는 같은 점수로 합치지 않는다.
2. **모델 교체를 A/B로 시험한다.** Hydrogen과 현재 모델을 같은 파일·도구·시간 제한으로 실행하고, high와 low thinking의 완료율·수정량·P95 시간·총토큰을 비교한다. 공급자 벤치마크를 자사 수치로 복사하지 않는다.
3. **검색 경계를 먼저 검사한다.** 사용자 A의 문서만 보여야 하는 요청에서 실제 도구 결과에 B 문서가 없었는지 확인한다. 최종 답변이 조심스러웠다는 이유로 권한 테스트를 통과시키지 않는다.
4. **완료 작업당 비용을 기록한다.** 요청별 가격만 수집하지 말고 재시도·도구 호출·검토자 시간·에스컬레이션을 붙인다. 성공하지 못한 요청도 비용 분모에 포함한다.
5. **장시간 세션을 강제로 끊어 본다.** 중단 후 체크포인트와 자격증명이 어떻게 복원되는지, 비멱등 도구 호출이 중복되는지 확인한다. 런타임 기동 수치보다 복구 결과가 제품에 가깝다.
6. **게이트웨이 계측을 실제 청구와 대조한다.** 사용자 지정 모델 가격이 0으로 잡히지 않는지, 각 키의 예산과 라우팅 제한이 동작하는지 검증한다.
7. **비밀 탐지 경고의 처리 루프를 끝까지 돌린다.** 탐지, 토큰 폐기, 영향 조사, 코드·CI 수정, 재발 테스트를 하나의 티켓으로 기록한다. 경고 닫기는 복구의 마지막 단계다.

## 운영 포인트 — 출시 전에 합의할 최소 계약

운영 계약에는 모델 이름만 넣지 않는다. **입력 데이터 등급**, 허용된 모델·리전, 사용자·세션 신원, 도구 권한, 검색 ACL, 출력·지연·비용 상한, 재시도와 취소 규칙, 사람 승인 조건, 로그 보존기간, 사고 후 되돌리기를 함께 둔다. 이 항목을 한 번에 구현할 필요는 없지만, 어떤 항목이 아직 보장되지 않는지는 적어야 한다. ‘모델이 안전하다’는 설명과 ‘시스템이 승인되지 않은 데이터에 접근할 수 없다’는 증거는 다른 문장이다.

실험과 운영의 로그도 구분한다. 평가를 위해 전문을 무기한 저장하면 민감한 입력을 복제하는 위험이 생긴다. 반대로 아무 기록도 남기지 않으면 오류를 재현할 수 없다. 요청 ID, 모델·설정 버전, 도구 호출의 메타데이터, 권한 정책 버전, 비용 요약, 인용한 문서 ID는 기본으로 남기고, 프롬프트·원문은 필요성과 보존기간을 별도로 판단한다. 사용자에게 잘못된 답변이 갔을 때는 답변 문장만 보는 것이 아니라 검색·권한·도구·모델 각 층의 사건을 연결해야 한다.

오늘 소식의 공통점은 **‘더 빠르게 실행’과 ‘실행해도 되는가’를 함께 설계하라**는 것이다. Hydrogen의 속도, AgentCore의 런타임, LLMON의 구조, Bedrock의 비용 설정, GitHub의 비밀 탐지는 모두 부분 해법이다. 단일 제품으로 신뢰를 구매할 수는 없다. 작은 실제 태스크에서 품질과 비용을 측정하고, 권한과 중단·복구를 실패 주입으로 증명한 뒤 범위를 넓히는 것이 안전하면서도 빠른 도입 경로다.

## 소스 링크 및 확인 범위

- Google 공식 RSS: [News from Google](https://blog.google/rss/) — 11월 12일 UTC 게시 시각과 원문 링크 확인.
- Google: [Gemini 4 Hydrogen 발표](https://blog.google/innovation-and-ai/models-and-research/gemini-models/introducing-gemini-4-hydrogen/) · [개발자 안내](https://blog.google/innovation-and-ai/technology/developers-tools/build-with-gemini-4-hydrogen/) · [Search 적용](https://blog.google/products-and-platforms/products/search/gemini-4-hydrogen-search-upgrade/).
- AWS 공식 RSS: [Machine Learning Blog feed](https://aws.amazon.com/blogs/machine-learning/feed/) — 항목 제목·게시 시각·원문 본문 확인. 일부 AWS 개별 페이지는 추출 크기 제한이 있어 해당 내용은 공식 RSS의 전체 본문을 기준으로 읽었다.
- AWS: [AgentCore Runtime](https://aws.amazon.com/blogs/machine-learning/run-agents-securely-and-efficiently-with-the-next-generation-agentcore-runtime/) · [지식베이스 접근 통제](https://aws.amazon.com/blogs/machine-learning/fine-grained-access-control-for-amazon-bedrock-managed-knowledge-base-tools/) · [추론비용 설정](https://aws.amazon.com/blogs/machine-learning/four-amazon-bedrock-inference-choices-that-affect-cost/) · [작업당 비용과 ROI](https://aws.amazon.com/blogs/machine-learning/optimizing-cost-per-task-and-proving-agent-roi-on-amazon-bedrock/) · [IAM 주체별 예산](https://aws.amazon.com/blogs/machine-learning/tokenomics-at-scale-track-and-cap-amazon-bedrock-spend-per-iam-principal-with-cur-2-0-and-aws-budgets/).
- AWS: [Bedrock·LiteLLM 게이트웨이](https://aws.amazon.com/blogs/machine-learning/building-a-self-service-llm-gateway-with-amazon-bedrock-and-litellm/) · [SGLang-Neuron](https://aws.amazon.com/blogs/machine-learning/deploy-frontier-ai-models-on-aws-trainium-with-sglang-neuron/) · [Natera 운영 사례](https://aws.amazon.com/blogs/machine-learning/how-natera-designed-an-agentic-ai-system-for-lab-ops-with-amazon-bedrock-agentcore/).
- Hugging Face 공식 RSS: [Blog feed](https://huggingface.co/blog/feed.xml) · IBM Granite 팀의 [LLMON 발표](https://huggingface.co/blog/ibm-granite/llmon-an-llm-native-markup-language-now-in-granite). IBM 작성 글의 실험 결과는 IBM 측 주장으로 표시했다.
- GitHub 공식 RSS: [Changelog feed](https://github.blog/changelog/feed/) · [Cloudflare 서비스 토큰 탐지](https://github.blog/changelog/2026-11-12-secret-scanning-adds-a-detector-for-cloudflare) · [Public monitoring 직접 링크](https://github.blog/changelog/2026-11-12-public-monitoring-alerts-now-have-direct-links).
- OpenAI: [News 인덱스](https://openai.com/news/)를 확인했으나 발행 시점의 상단 새 글은 11월 11일 게시물이어서 오늘의 신규 발표로 재포장하지 않았다.
