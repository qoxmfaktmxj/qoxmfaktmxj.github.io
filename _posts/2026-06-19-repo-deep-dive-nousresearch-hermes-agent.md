---
layout: post
title: "Repo Deep Dive: NousResearch/hermes-agent - 요청을 기억과 반복 작업으로 이어가는 개인 에이전트"
date: 2026-06-19 08:58:41 +0900
categories: [github-repo-analysis]
tags: [github, ai-agent, hermes-agent, memory, skills, automation]
repo: NousResearch/hermes-agent
analyzed_at: 2026-10-16
analyzed_commit: 7bf3766f3db72d4643d1a78d18e51c1d9ddf1d6d
---

터미널에서 매번 같은 프로젝트 위치와 작업 규칙을 설명하고, 지난주 조사 결과를 다시 찾아 붙이는 일이 번거로울 때가 있다. 답변을 잘하는 모델만으로는 이 문제가 모두 해결되지 않는다. 대화를 저장하고, 필요한 파일을 읽고, 다음 작업에서도 쓸 절차를 남기는 실행 환경이 필요하다.

Nous Research의 Hermes Agent는 이런 일을 맡기는 개인 AI 에이전트다. 사용자는 터미널이나 연결한 메신저에서 요청하고, Hermes는 설정된 모델에 판단을 맡기면서 파일, 터미널, 웹 등의 도구를 호출한다. 작업 이력과 짧은 메모리, 재사용할 스킬을 함께 관리하므로 한 번의 대화 이후에도 이어서 활용할 여지가 생긴다. 코딩 보조뿐 아니라 자료 조사와 정기 보고처럼 여러 단계를 반복하는 작업에 관심 있는 사용자가 살펴볼 만하다.

이 글은 2026년 10월 16일 재검토 기준으로 공식 문서와 커밋 `7bf3766`을 확인해 새로 작성했다. 설치와 실제 대화, 봇 연결, 예약 실행은 수행하지 않았다. 아래 절차는 문서에서 확인한 사용법이며, 직접 구성한 요청은 따로 표시한다.

## 처음에는 검증하기 쉬운 대화 하나를 만든다

시작 순서는 설치, 모델 연결, 첫 대화, 세션 재개다. 공식 Quickstart도 기본 대화가 정상 동작하는지 확인한 뒤 메신저나 예약 기능을 추가하도록 안내한다. macOS와 Windows에서는 Desktop 설치 프로그램을 제공하며, 명령줄만 설치하는 경로도 있다. Linux, macOS, WSL2용 명령은 다음과 같다.

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
```

Windows 네이티브 설치는 PowerShell에서 다음 명령을 사용한다. WSL2 경로와 네이티브 경로 중 자신의 환경에 맞는 하나를 고르면 된다.

```powershell
iex (irm https://hermes-agent.nousresearch.com/install.ps1)
```

설치 후 새 셸에서 `hermes setup`으로 초기 구성을 진행하거나 `hermes model`로 제공자와 모델을 선택한다. 이어 `hermes`로 대화에 들어간다. 공식 첫 요청 예제에는 현재 디렉터리에서 주요 프로젝트 파일을 찾아 달라는 요청이 있다. 선택한 모델이 표시되고, 필요한 파일 읽기나 터미널 도구가 동작하며, 다음 질문에도 정상 응답하는지가 확인 기준이다. 종료한 뒤 `hermes --continue`로 방금 대화를 다시 여는 것까지 확인하면 첫 사용의 범위가 명확해진다. [공식 Quickstart](https://hermes-agent.nousresearch.com/docs/getting-started/quickstart)

모델 연결은 필수다. Nous Portal, OpenRouter, Anthropic, OpenAI API, Google Gemini 등의 연동이 문서에 있고, Ollama나 vLLM처럼 직접 운영하는 서버도 호환 엔드포인트로 연결할 수 있다. 다만 API 주소만 입력하면 모든 모델이 같은 수준으로 동작한다고 볼 수는 없다. 현재 Quickstart는 최소 64,000토큰의 문맥 창을 요구하며, 로컬 서버도 그 크기로 실제 제공하도록 설정해야 한다. 제공자 문서는 도구 호출이 일반 텍스트로 출력되는 경우 모델과 서버의 도구 호출 설정을 확인하라고 설명한다. [모델 제공자와 로컬 서버 설정](https://hermes-agent.nousresearch.com/docs/integrations/providers)

## 요청 하나가 답변이 되기까지

다음은 흐름을 설명하기 위해 직접 구성한 요청이다. 공식 사용 사례나 실행 결과가 아니다.

> 현재 저장소의 테스트 실행 방법을 찾아 정리해 줘. 우선 README와 설정 파일만 읽고, 파일은 수정하지 마. 근거가 있는 명령과 아직 확인하지 못한 부분을 나눠 알려 줘.

사용자 입장에서는 한 문장을 보냈지만, 내부에서는 여러 차례의 판단이 이어질 수 있다. Hermes가 현재 세션의 기록과 도구 설명을 모델에 전달하면, 모델은 파일을 읽을지 바로 답할지 결정한다. 도구 호출이 나오면 Hermes가 해당 함수를 실행하고 결과를 다시 모델에 전달한다. 모델은 읽은 내용이 부족하면 다른 파일을 요청하고, 충분해지면 근거와 함께 답변한다. 이 입력, 도구 실행, 결과 재입력의 반복이 에이전트의 작업 과정이다. [공식 아키텍처의 데이터 흐름](https://github.com/NousResearch/hermes-agent/blob/7bf3766f3db72d4643d1a78d18e51c1d9ddf1d6d/website/docs/developer-guide/architecture.md)

여기서 확인해야 할 것은 말투보다 실제로 호출한 도구와 결과다. 예제에서는 파일 읽기만 허용했으므로 테스트를 실행했다고 말한다면 요청 범위를 벗어난 것이다. 다음 요청에서 실행까지 허용하더라도, 제시한 명령과 실제 종료 결과가 일치하는지 살펴야 한다. Hermes는 작업을 대신 진행할 수 있지만, 자연어로 한 완료 선언이 실행 증거를 대신하지는 않는다.

사용할 수 있는 도구도 설정에 따라 달라진다. `hermes tools`에서 플랫폼별 도구 묶음을 조정할 수 있으며, 웹 검색과 브라우저 기능은 선택한 서비스의 인증이나 구성이 필요할 수 있다. 모델이 연결됐다는 사실만으로 모든 외부 도구까지 준비되는 것은 아니다. [도구와 도구 묶음](https://hermes-agent.nousresearch.com/docs/user-guide/features/tools)

## 지난 대화, 짧은 기억, 작업 절차는 서로 다르다

첫 작업을 끝냈다고 다음 세션에서 모든 세부 사항을 그대로 기억하는 것은 아니다. Hermes가 정보를 이어가는 방식은 세 가지로 구분해 이해하는 편이 좋다.

| 남기는 정보 | 맡는 역할 | 다음 작업에서 쓰는 방식 |
| --- | --- | --- |
| 세션 기록 | 실제 대화와 도구 사용 이력 | 같은 세션을 재개하거나 과거 기록을 검색한다 |
| 메모리 | 환경 정보와 사용자 선호처럼 짧고 지속적인 사실 | 세션 시작 시 모델의 문맥에 넣는다 |
| 스킬 | 반복할 작업의 순서와 주의점 | 관련 작업을 할 때 절차 문서를 읽는다 |

기본 메모리는 `MEMORY.md`와 `USER.md`로 구성된다. 전자는 환경과 작업 관례, 후자는 사용자 선호를 담으며, 세션 시작 때 고정된 스냅샷으로 들어간다. 현재 세션에서 새로 저장한 내용은 디스크에 기록되지만, 시작 때 주입된 블록 자체는 바뀌지 않는다. 필요한 과거 세부 대화는 SQLite와 FTS5 기반 `session_search`로 찾는다. 현재 상세 문서는 검색 결과가 실제 메시지이며 LLM 요약을 거치지 않는다고 명시한다. README의 개괄 설명보다 이 구체적인 동작을 기준으로 이해해야 한다. [지속 메모리와 세션 검색](https://github.com/NousResearch/hermes-agent/blob/7bf3766f3db72d4643d1a78d18e51c1d9ddf1d6d/website/docs/user-guide/features/memory.md)

예제 작업에서 “이 저장소에서는 수정 전 테스트 명령을 먼저 확인한다”는 관례는 짧은 메모리에 어울린다. 어느 파일을 열어 어떤 순서로 검증하고 결과를 작성하는지까지 길어지면 스킬로 옮기는 편이 맞다. 스킬은 `SKILL.md` 형태의 절차이며, 에이전트는 필요한 내용을 불러오고 `skill_manage`로 생성하거나 수정할 수 있다. 사용자는 `/learn`으로 방금 함께 수행한 방법이나 특정 문서를 스킬로 정리하도록 요청할 수도 있다. 자동 저장 여부와 생성된 내용은 직접 검토해야 한다. [스킬 시스템](https://github.com/NousResearch/hermes-agent/blob/7bf3766f3db72d4643d1a78d18e51c1d9ddf1d6d/website/docs/user-guide/features/skills.md)

프로젝트가 말하는 자기 개선은 이처럼 경험을 메모와 절차로 남겨 다음 요청에 활용하는 흐름이다. 이 설명만으로 대화할 때마다 연결된 모델의 가중치를 재학습한다고 해석해서는 안 된다. 메모리와 스킬은 모델에 제공하는 입력과 작업 방법을 바꾼다. 저장소에 학습용 실행 기록을 생성하는 별도 기능이 있다는 사실과, 일반 사용 중 파일로 지식을 유지하는 기능은 구분해야 한다.

메신저에서는 세션 경계도 사용 습관에 영향을 준다. 게이트웨이를 재시작해도 같은 채팅 세션은 이어질 수 있다. 공식 문서는 작업 완료나 주제 변경 시 `/new`를 사용해 새 메모리 스냅샷을 읽도록 안내한다. “기억했다”는 답을 받았는데 다음 세션에서 잊었다면 저장 파일에 실제 항목이 생겼는지, 같은 프로필을 쓰는지부터 확인한다. [메모리 문제 해결](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory#troubleshooting-i-told-it-to-remember-and-the-next-session-it-forgot)

## 모델, 실행 장소, 대화 채널을 나눠 고른다

설정에서 혼동하기 쉬운 세 축이 있다. 모델 제공자는 판단을 수행할 LLM에 접속하는 곳이다. 터미널 백엔드는 명령이 실행되는 환경이다. 채널은 사용자가 요청하고 결과를 받는 통로다. 예를 들어 Telegram으로 요청하고, OpenRouter의 모델을 사용하며, 명령은 Docker에서 실행하는 구성이 가능하다.

터미널 백엔드는 현재 문서 기준 `local`, `docker`, `ssh`, `singularity`, `modal`, `daytona`, `vercel_sandbox`를 지원한다. 이 선택은 로컬 모델 사용 여부와 별개다. `docker`를 고른다고 모델 추론까지 컨테이너 안으로 옮겨지는 것은 아니며, 원격 백엔드는 해당 환경의 계정과 접속 구성이 필요하다. [터미널 백엔드 목록](https://github.com/NousResearch/hermes-agent/blob/7bf3766f3db72d4643d1a78d18e51c1d9ddf1d6d/website/docs/user-guide/features/tools.md#terminal-backends)

메신저 연동은 단일 게이트웨이 프로세스가 맡는다. 공식 문서는 Telegram, Discord, Slack, WhatsApp, Signal, Email 외에도 여러 플랫폼을 안내한다. 구현과 설치 방식은 채널마다 다르며, Home Assistant는 별도 카탈로그 플러그인이다. `hermes gateway setup`에서 연결할 플랫폼을 구성하고, 게이트웨이를 실행한 뒤 메시지를 주고받는 순서다. 사용자 허용 목록이나 DM 페어링도 설정해야 한다. 지원 목록이 길다는 이유만으로 채널마다 음성, 파일, 명령 기능이 같다고 가정해서는 안 된다. [게이트웨이와 플랫폼별 안내](https://hermes-agent.nousresearch.com/docs/user-guide/messaging)

## 한 번 성공한 일을 정기 작업으로 바꿀 때

공식 Cron 문서에는 매일 오전 9시에 Hacker News의 AI 뉴스를 확인하고 Telegram으로 요약을 보내 달라는 예제가 있다. 이는 프로젝트가 제시한 활용 예이며, 특정 조직의 도입 사례나 이 글에서 실행한 결과는 아니다. 자연어 요청을 받으면 Hermes가 예약 관리 도구를 호출해 작업을 등록할 수 있다. [공식 예약 예제](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron#through-natural-conversation)

반복 실행은 지금 대화를 계속 읽는 방식과 다르다. 일반적인 에이전트 예약 작업은 실행할 때마다 새 세션을 만들고, 지정한 요청과 연결된 스킬을 바탕으로 동작한다. 따라서 “아까와 똑같이 해 줘”만 남기면 부족하다. 조사 대상, 저장 위치, 결과 형식, 실패를 판단할 조건을 예약 요청이나 스킬에 담아야 한다. 프로젝트 안에서 실행하려면 작업 디렉터리도 명시해야 한다.

예약 실행을 담당하는 게이트웨이 프로세스가 살아 있어야 한다는 운영 조건도 있다. 작업 등록과 실제 실행 성공, 결과 전달 성공은 각각 확인할 대상이다. `hermes cron list`와 `hermes cron status`로 등록 상태와 스케줄러 상태를 확인하고, 실행 기록과 수신 결과를 살펴야 한다. 먼저 대화에서 성공한 작업을 만들고, 절차를 스킬로 정리한 다음 예약으로 옮기는 순서가 이해하기 쉽다. [예약 작업의 실행 방식](https://github.com/NousResearch/hermes-agent/blob/7bf3766f3db72d4643d1a78d18e51c1d9ddf1d6d/website/docs/user-guide/features/cron.md#how-it-works)

## 맡길 범위는 도구와 저장 내용을 보고 정한다

Hermes는 명령을 실행하고 파일을 바꿀 수 있으므로 실행 환경의 권한이 중요하다. 기본 로컬 백엔드는 사용자의 컴퓨터에서 동작한다. 위험 명령 승인 기능이 있더라도 운영체제 권한과 격리 환경을 대신하지는 않는다. Docker나 원격 환경을 선택할 때도 공유 경로와 전달하는 인증 정보를 확인해야 한다. [공식 보안 문서](https://github.com/NousResearch/hermes-agent/blob/7bf3766f3db72d4643d1a78d18e51c1d9ddf1d6d/website/docs/user-guide/security.md)

지속 메모리와 스킬도 검토 대상이다. 잘못된 전제를 저장하면 다음 작업에서도 재사용할 수 있다. 문서는 `memory.write_approval`과 `skills.write_approval`로 저장 전 검토를 켜는 방법을 제공한다. 모델 호출뿐 아니라 대화 압축과 백그라운드 검토에도 호출 비용이 생길 수 있으므로, 선택한 제공자의 과금과 활성화한 기능을 함께 살펴야 한다.

소스는 [MIT 라이선스](https://github.com/NousResearch/hermes-agent/blob/7bf3766f3db72d4643d1a78d18e51c1d9ddf1d6d/LICENSE)로 공개돼 있다. 모델 API와 외부 도구 서비스에는 각자의 이용 조건이 적용된다. 처음부터 많은 기능을 연결하기보다, 작은 요청에서 도구 결과를 확인하고 같은 세션을 재개해 본 뒤 기억과 절차를 남겨 보면 이 프로젝트의 쓰임을 판단하기 쉽다.

### 참고 자료

- [공식 저장소 README](https://github.com/NousResearch/hermes-agent/blob/7bf3766f3db72d4643d1a78d18e51c1d9ddf1d6d/README.md)
- [공식 Quickstart](https://hermes-agent.nousresearch.com/docs/getting-started/quickstart)
- [모델 제공자 문서](https://hermes-agent.nousresearch.com/docs/integrations/providers)
- [메모리 문서](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory)
- [스킬 문서](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills)
- [예약 작업 문서](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron)
