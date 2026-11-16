---
layout: post
title: "Repo Deep Dive: ag-ui-protocol/ag-ui — 에이전트와 사용자 앱을 잇는 이벤트 프로토콜"
date: 2026-11-17 07:11:14 +0900
categories: [github-repo-analysis]
repo: ag-ui-protocol/ag-ui
trending_rank: 1
trending_period: daily
trending_checked_at: 2026-11-17 07:10:32 +0900
trending_url: https://github.com/trending?since=daily
---

2026년 11월 17일 07:10 KST에 확인한 GitHub Trending 일간 전체 언어 목록에서 `ag-ui-protocol/ag-ui`가 1위였다. **이 순위는 저장소 선정 시점의 스냅샷**이며, 발행 또는 열람 시점의 실시간 순위가 아니다. 아래 내용은 저장소의 현재 README와 AG-UI 1.0 공식 명세, 개념 문서, 공개 예시를 대조해 정리했다. 예시의 실행 결과는 공식 README가 안내하는 예상 결과이며, 이 글에서 별도로 성능이나 상호운용성을 측정한 것은 아니다.

## 1. 프로젝트 소개

AG-UI(Agent–User Interaction Protocol)는 AI 에이전트와 사용자에게 보이는 애플리케이션이 대화하는 방법을 정의하는 공개 이벤트 프로토콜이다. CopilotKit이 시작했고 `ag-ui-protocol` 조직의 공개 저장소에서 커뮤니티와 함께 개발한다. 저장소는 MIT 라이선스로 배포되며, 공식 README는 현재 1.0 명세와 TypeScript·Python·.NET SDK를 안내한다. 핵심 대상은 에이전트 서버를 만드는 개발자와, 그 서버의 응답을 웹·모바일·터미널·채팅 UI에서 보여 주는 클라이언트 개발자다.

일반적인 챗 API라면 요청 하나를 보내 최종 문자열 하나를 받아도 화면을 구성할 수 있다. 그러나 도구 호출의 인자 생성 과정을 보여 주거나, 에이전트가 앱의 상태를 바꾸고, 사람의 승인을 기다렸다가 다시 실행해야 한다면 단일 최종 문자열만으로는 부족하다. AG-UI는 사용자의 요청을 담은 `RunAgentInput`을 앱에서 에이전트로 보내고, 에이전트가 실행·메시지·도구·상태 등에 관한 타입 있는 이벤트를 스트림으로 돌려주는 계약을 제공한다. 특정 UI 컴포넌트나 에이전트 프레임워크를 의무화하는 제품이 아니라 양쪽이 주고받는 데이터와 순서를 정의하는 계층이다.

## 2. 해결하려는 문제

프레임워크마다 스트리밍 텍스트, 도구 호출, 중단과 재개를 서로 다른 형태로 내보내면 프런트엔드는 각 서버에 맞춘 어댑터를 별도로 작성해야 한다. 예컨대 답변 토큰을 화면에 덧붙이는 일과 앱에서 실행할 도구의 인자를 모으는 일은 둘 다 점진적으로 도착하지만, 완료 조건과 처리 주체는 다르다. 도구 인자가 아직 전송 중인데 앱이 실행해 버리거나, 상태 변경을 단순 텍스트처럼 취급하면 사용자 경험뿐 아니라 동작도 달라진다.

AG-UI 1.0 명세는 이를 이벤트 종류와 처리 규칙으로 나눈다. 앱은 대화 기록·프런트엔드 도구·공유 상태·문맥을 `RunAgentInput`에 담고, 에이전트는 `RUN_STARTED`와 `RUN_FINISHED` 같은 실행 경계 사이에 필요한 이벤트를 보낸다. 공식 명세에서 실행 생명주기를 제외한 나머지 이벤트 계열은 필요에 따라 사용한다. 따라서 텍스트만 스트리밍하는 작은 서버부터 상태 동기화와 사용자 승인을 포함하는 서버까지 같은 기본 교환 방식으로 확장할 수 있다. 다만 프로토콜이 앱의 권한 판단이나 도구 실행을 대신하는 것은 아니다. 공식 도구 호출 명세도 부작용이 있는 동작의 실행 여부를 애플리케이션이 결정하도록 구분한다.

이 역할은 MCP나 A2A와도 다르다. 공식 비교 문서에서 MCP는 에이전트가 도구·문맥에 접근하는 계층, A2A는 에이전트 간 통신 계층, AG-UI는 에이전트가 사용자 앱과 상호작용하는 계층으로 설명한다. 하나의 서비스가 이 프로토콜들을 함께 쓸 수 있지만, AG-UI를 붙였다는 사실만으로 도구 연결이나 에이전트 간 통신이 자동으로 완성되지는 않는다.

## 3. 주요 기능

**실행과 텍스트 스트리밍.** 클라이언트는 스레드 ID·실행 ID와 대화 메시지를 담아 실행을 요청한다. 서버는 `RUN_STARTED`로 시작을 알리고, `TEXT_MESSAGE_START`로 답변 메시지를 열어 `TEXT_MESSAGE_CONTENT`의 `delta`를 순서대로 보낸 뒤 `TEXT_MESSAGE_END`와 `RUN_FINISHED`로 마무리한다. 클라이언트는 각 `delta`를 화면에 추가할 수 있고 실행 종료 이벤트로 그 메시지가 완료됐는지 판단한다. 모든 답변을 한 번에 보내는 방식과 달리 진행 중인 텍스트를 즉시 렌더링할 수 있다. 실행 중 오류와 사용자가 의도적으로 중단한 실행은 정상 완료와 다른 종료 형태로 구분된다.

**도구 호출과 프런트엔드 동작.** 에이전트가 도구를 호출하면 `TOOL_CALL_START`에 이름과 호출 ID를 싣고, `TOOL_CALL_ARGS`로 인자 문자열 조각을 보낸 다음 `TOOL_CALL_END`로 인자가 완성됐음을 알린다. 명세는 인자를 끝 이벤트 전에 실행하지 말라고 규정한다. 완성된 문자열이 유효한 JSON인지 확인하고 실제 도구를 실행하는 책임도 실행 주체에게 있다. 백엔드가 실행한 도구 결과는 같은 스트림의 `TOOL_CALL_RESULT`로 올 수 있다. 반면 프런트엔드가 실행하는 도구는 앱이 결과를 다음 실행의 입력 메시지로 돌려보낼 수 있다. 따라서 '에이전트가 호출을 제안했다'와 '앱이 권한을 확인하고 실행했다'를 분리해 읽어야 한다.

**공유 상태와 대화 동기화.** `STATE_SNAPSHOT`은 현재 상태 전체를 교체하고, `STATE_DELTA`는 기존 상태에 RFC 6902 JSON Patch를 적용한다. 예를 들어 앱과 에이전트가 함께 편집하는 폼이나 계획표에서는 전체 상태를 다시 보내는 경우와 변경 부분만 보내는 경우를 구분할 수 있다. 다음 실행은 갱신된 상태를 입력에 담아 보내므로 실행 사이에도 맥락이 이어진다. `MESSAGES_SNAPSHOT`은 상태 값이 아니라 대화 메시지 집합을 동기화하는 별도의 이벤트다. 공식 상태 명세는 상태를 원격 입력으로 취급해 앱이 사용 전에 검증해야 한다고 명시한다.

**사람의 판단을 기다리는 흐름.** 공식 인터럽트 문서는 실행이 `RUN_FINISHED`의 `interrupt` 결과로 끝날 수 있다고 설명한다. 이때 인터럽트 ID와 이유, 선택적인 응답 스키마가 전달되고, 앱은 승인·수정·거절 같은 사람의 응답을 받아 다음 `RunAgentInput.resume`에 해당 ID와 응답을 실어 새 실행을 시작한다. 이것은 단순히 긴 요청을 계속 열어 두는 방식이 아니다. 실행이 한 번 닫히고 사용자 응답을 명시한 다음 다음 실행으로 이어지는 절차다. 사용자 승인 화면을 어떻게 만들고 어떤 작업을 허용할지는 여전히 앱의 책임이다.

## 4. 사용 방법과 동작 흐름

가장 빠른 시작 경로는 README의 `npx create-ag-ui-app@latest`다. 생성 명령은 프런트엔드와 선택한 에이전트 프레임워크를 연결한 템플릿을 안내하며, 생성된 예시는 OpenAI 호출을 포함하므로 개발 서버를 실행하기 전에 `OPENAI_API_KEY`가 필요하다고 명시한다. 반면 프로토콜 자체를 확인할 때는 외부 모델 키 없이 README에 실린 작은 Python 서버와 TypeScript 클라이언트를 사용할 수 있다. 아래는 그 예시의 핵심 부분이다.

Python 3.9 이상에서 `pip install ag-ui-protocol fastapi uvicorn`으로 서버 의존성을 설치한다. HTTP 엔드포인트는 `RunAgentInput`을 받고, 요청의 `Accept` 헤더를 반영한 `EventEncoder`로 이벤트를 인코딩해 스트리밍 응답을 만든다.

```python
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from ag_ui.core import PROTOCOL_VERSION, RunAgentInput, RunStartedEvent, RunFinishedEvent, TextMessageStartEvent, TextMessageContentEvent, TextMessageEndEvent
from ag_ui.encoder import EventEncoder
import uuid

app = FastAPI()

@app.post("/")
async def run_agent(input_data: RunAgentInput, request: Request):
    encoder = EventEncoder(accept=request.headers.get("accept"))
    async def events():
        yield encoder.encode(RunStartedEvent(thread_id=input_data.thread_id, run_id=input_data.run_id, protocol_version=PROTOCOL_VERSION))
        message_id = str(uuid.uuid4())
        yield encoder.encode(TextMessageStartEvent(message_id=message_id, role="assistant"))
        yield encoder.encode(TextMessageContentEvent(message_id=message_id, delta="Hello from AG-UI!"))
        yield encoder.encode(TextMessageEndEvent(message_id=message_id))
        yield encoder.encode(RunFinishedEvent(thread_id=input_data.thread_id, run_id=input_data.run_id))
    return StreamingResponse(events(), media_type=encoder.get_content_type())
```

이를 `server.py`로 저장하고 `uvicorn server:app --port 8000`으로 연다. Node.js 20 이상인 다른 터미널에서 `npm init -y`, `npm pkg set type=module`, `npm install @ag-ui/client tsx`를 실행한 뒤 다음 클라이언트를 `client.ts`로 저장한다.

```ts
import { HttpAgent } from "@ag-ui/client";
const agent = new HttpAgent({ url: "http://localhost:8000/" });
agent.addMessage({ id: crypto.randomUUID(), role: "user", content: "Hi there!" });
await agent.runAgent({}, {
  onTextMessageContentEvent: ({ event }) => process.stdout.write(event.delta),
  onRunFinishedEvent: () => console.log("\nrun finished"),
});
```

`npx tsx client.ts`로 실행하면 README 예시에서는 `Hello from AG-UI!`가 출력된다. 서버가 문장을 한 번에 보내더라도 이벤트 유형은 스트리밍 텍스트용이며, 실제 에이전트라면 여러 `delta`를 순차적으로 보낼 수 있다. HTTP+SSE 명세에 따르면 앱은 JSON `RunAgentInput`을 POST하고 서버는 `text/event-stream` 응답으로 이벤트를 전달한다. 위 코드는 최소 통신을 보여 주는 예시이지 인증, 사용자별 접근 제어, 영속 대화 저장을 갖춘 운영 서버 예시는 아니다. 더 긴 대화나 프런트엔드 도구를 다루려면 클라이언트가 메시지와 상태를 다음 실행에 어떻게 전달하는지도 함께 구현해야 한다.

## 5. 활용 사례

**진행 상황이 보이는 대화 UI.** 공식 Dojo의 에이전트 채팅 예시는 답변이 완성되기 전에 화면에 내용을 보여 준다. 앱은 텍스트 이벤트를 사용해 현재 메시지를 갱신하고 실행 경계 이벤트로 완료 여부를 표시할 수 있다. 같은 에이전트를 터미널 UI에 연결하는 예시는 공식 클라이언트 빠른 시작 문서에 별도로 제시돼 있다. 프로토콜이 렌더링 대상을 지정하지 않기 때문에 가능한 구성이다.

**앱과 에이전트가 같은 작업 상태를 보는 화면.** Dojo의 공유 상태 예시는 에이전트와 UI 양쪽이 값을 읽고 바꾸는 상황을 보여 준다. 이 경우 단순 답변 문구보다 현재 상태 전체를 나타내는 스냅샷과 부분 수정인 델타가 중요하다. 앱은 상태 이벤트를 받은 뒤 화면에 적용하되 그 값을 신뢰된 내부 데이터로 가정하지 않아야 한다.

**승인·확인이 필요한 조작.** 공식 도구 문서는 프런트엔드가 `RunAgentInput.tools`에 앱 전용 도구를 선언하고, 에이전트가 호출을 제안하면 앱이 실행을 결정하는 흐름을 설명한다. 공식 인터럽트 예시에서는 민감한 작업 앞에서 사람의 응답을 기다리고 다음 실행에서 이어가는 흐름도 다룬다. 두 방식 모두 사용자에게 선택권을 줄 수 있지만, 도구 호출 결과를 다음 실행에 돌려주는 것과 인터럽트 ID에 대한 재개 응답을 보내는 것은 서로 다른 계약이다.

## 6. 참고 자료

- [AG-UI 저장소와 README](https://github.com/ag-ui-protocol/ag-ui) — 프로젝트 소개, SDK, 최소 서버·클라이언트 예시
- [AG-UI 1.0 이벤트 명세](https://docs.ag-ui.com/spec/1.0/events) — 이벤트 계열과 처리 규칙
- [실행 입력 명세](https://docs.ag-ui.com/spec/1.0/basic/run-input)와 [HTTP+SSE 전송 명세](https://docs.ag-ui.com/spec/1.0/basic/transports/http-sse) — 요청·응답 계약
- [도구 호출 명세](https://docs.ag-ui.com/spec/1.0/events/tool-calls)와 [상태 명세](https://docs.ag-ui.com/spec/1.0/events/state) — 호출 완료와 상태 동기화
- [인터럽트 개념 문서](https://docs.ag-ui.com/concepts/interrupts)와 [MCP·A2A 비교](https://docs.ag-ui.com/agentic-protocols) — 사람의 응답과 프로토콜 경계
- [AG-UI Dojo 공유 상태 예시](https://dojo.ag-ui.com/langgraph-fastapi/feature/shared_state)와 [클라이언트 빠른 시작](https://docs.ag-ui.com/quickstart/clients) — 공개 활용 사례
