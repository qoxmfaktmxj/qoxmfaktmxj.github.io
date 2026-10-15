---
layout: post
title: "Repo Deep Dive: n8n-io/n8n - 이벤트 한 건이 자동화가 되기까지"
date: 2026-06-30 08:13:35 +0900
categories: [github-repo-analysis]
tags: [github, n8n, workflow, automation, webhook, self-hosted]
repo: n8n-io/n8n
analyzed_at: 2026-10-16
analyzed_commit: 1903d53bc07f43729aa003fef4412a49c343e26f
---

고객 문의가 들어오면 담당자가 내용을 확인하고, 업무 시스템에 등록하고, 팀 채널에 알린다. 이 일을 자동화하려면 문의를 받는 입구, 데이터를 바꾸는 규칙, 외부 서비스의 인증, 전송 실패를 확인할 방법이 필요하다. n8n은 이 과정을 노드와 연결선으로 구성하고 실행하는 워크플로 플랫폼이다. 개발자와 기술 운영팀은 시각적 편집기에서 흐름을 만들고, 필요한 부분에 표현식이나 코드를 넣을 수 있다. [공식 README](https://github.com/n8n-io/n8n/blob/1903d53bc07f43729aa003fef4412a49c343e26f/README.md)는 업무 자동화와 AI 에이전트, Cloud와 자체 호스팅을 함께 지원하는 제품으로 소개한다.

이 글은 2026년 10월 16일 재검토 기준으로 공식 문서와 위 커밋을 읽어 새로 작성했다. 아래 고객 문의 흐름은 이해를 위한 구성 예시이며 실제 도입 사례가 아니다. 설치하거나 외부 API를 호출해 실행한 결과와 문서에서 확인한 동작을 구분하며, 공식 튜토리얼도 따로 소개한다.

## 문의를 받는 입구부터 만든다

예시의 흐름은 `Webhook → Edit Fields → If → 외부 업무 API → 팀 알림`이다. Webhook은 다른 시스템이 HTTP 요청을 보낼 수 있는 입구다. 문의 폼 서버가 요청을 보내면 이 트리거가 워크플로를 시작한다. 전용 앱 트리거가 없는 서비스도 HTTP 요청을 보낼 수 있다면 연결할 수 있다. 정해진 시간에 자료를 모으는 작업이라면 입구를 Schedule Trigger로 바꾼다.

먼저 Webhook의 메서드를 POST로 정하고 Test URL을 확인한다. 편집기에서 **Listen for Test Event**를 선택한 뒤 샘플 요청을 보내면 입력을 화면에서 볼 수 있다. 이 상태에서 문의 본문이 어느 경로에 들어오는지 살펴보고 다음 노드에 연결한다. 테스트 URL을 외부 서비스의 영구 수신 주소로 등록한 채 끝내면 안 된다.

운영에서는 워크플로를 **Publish**하고 Production URL을 발신 시스템에 등록한다. 공식 문서는 게시할 때 운영 Webhook이 등록되며, 운영 호출 데이터는 편집기 캔버스에 바로 나타나지 않는다고 설명한다. 이때는 **Executions**에서 해당 실행을 연다. 테스트와 운영 URL은 요청을 받을 조건과 실행을 확인하는 위치가 다르다. Webhook은 즉시 응답하거나 마지막 노드의 결과를 돌려주는 등 응답 방식도 선택할 수 있으므로, 발신 측이 무엇을 성공으로 볼지도 정해야 한다. [Webhook 문서](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.webhook)

## 연결선을 지나는 것은 item이다

n8n 노드 사이에는 item의 배열이 흐른다. 각 item의 일반 데이터는 `json` 안에 있으며 파일 같은 데이터에는 `binary` 구조를 사용한다. Webhook에서 실제로 관찰한 출력을 기준으로 필드를 고르는 것이 출발점이다. 다음은 문의 본문이 `body`에 들어 있다고 가정한 **설명용 입력 일부**다. 헤더 등 실제 출력의 다른 필드는 생략했다.

```json
[
  {
    "json": {
      "body": {
        "requestId": "REQ-1042",
        "email": "reader@example.com",
        "category": "billing",
        "message": "청구 내역을 확인하고 싶습니다."
      }
    }
  }
]
```

Edit Fields에서 이 값을 업무 시스템의 필드명으로 정리한다. `requestId`를 `externalId`로, `message`를 `description`으로 대응시키고 전송에 필요한 항목만 남기는 식이다. 이 노드는 새 필드를 추가하거나 기존 값을 덮어쓸 수 있고, 출력에 포함할 입력 필드도 고를 수 있다. 폼의 데이터 구조가 업무 API에 그대로 맞을 것이라고 가정하지 않고 변환 단계를 두는 것이다. [Edit Fields 문서](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.set)

item 수는 작업 횟수와도 연결된다. 대부분의 노드는 여러 item을 받아 각 item에 설정된 작업을 수행한다. 공식 데이터 문서는 두 item의 이름을 Trello 카드 이름에 연결하면 카드 두 개가 만들어지는 예를 든다. 반면 item 하나의 `json` 안에 문의 열 건이 배열로 들어 있다면, 그것만으로 문의 item 열 개가 된 것은 아니다. 건별 처리가 필요하면 배열을 개별 item으로 나누는 단계를 검토해야 한다. 현재 item이 몇 개이고 그 안의 배열이 무엇인지 확인해야 전송 건수를 이해할 수 있다. [데이터 구조 문서](https://docs.n8n.io/build/work-with-data/understand-n8ns-data-structure.md)

## 표현식으로 값을 연결하고 조건으로 경로를 나눈다

노드 설정값에는 고정 문자열뿐 아니라 입력에 따라 달라지는 expression을 넣을 수 있다. 문의 내용을 연결하는 값은 다음과 같다. 이 표현식은 문의 본문을 그대로 전달하는 예시이며 실제 필드 경로는 입력 화면에서 확인해야 한다.

{% raw %}
```javascript
{{ $json.body.message }}
```
{% endraw %}

`$json`은 현재 item의 JSON 데이터다. 입력 패널의 필드를 설정 칸으로 끌어 놓는 동작도 이런 경로 참조를 만든다. 샘플 문의 문장을 고정한 것이 아니라 다음 요청에서도 같은 경로의 값을 읽도록 설정한 것이다. 다만 Edit Fields가 구조를 바꾼 뒤라면 다음 노드는 바뀐 출력에서 필드를 찾아야 한다. 앞 노드의 출력과 뒤 노드의 입력을 번갈아 확인하는 작업이 시각적 자동화의 실질적인 디버깅 과정이다.

그다음 If에서 `category`가 `billing`인지 검사해 청구 담당 경로와 일반 문의 경로로 나눈다. 간단한 참조나 날짜 계산에는 표현식을 쓰고, 배열 재구성이나 여러 item을 함께 처리하는 복잡한 변환에는 Code 노드를 고려한다. Code 노드는 JavaScript나 Python으로 별도 처리 단계를 작성하는 수단이다. 표현식, 전용 데이터 변환 노드, Code의 역할을 구분하면 작은 필드 변환마다 긴 코드를 만들 필요가 줄어든다. [표현식과 데이터 노드 비교](https://docs.n8n.io/build/work-with-data/expressions-versus-data-nodes.md)

트리거는 실행 시점을 만들고, 필드 매핑은 서로 다른 데이터 형식을 연결하고, 조건 노드는 처리 경로를 결정한다. 업무 규칙을 연결선으로 읽을 수 있다는 점은 장점이지만 필드명이나 자료형을 이해해야 한다는 요구까지 사라지는 것은 아니다.

## 외부로 보낼 때 인증과 성공 조건을 정한다

외부 서비스의 전용 노드가 필요한 작업을 제공하면 그 노드에서 동작과 필드를 고른다. 전용 노드가 없거나 지원하지 않는 API 작업을 호출해야 한다면 HTTP Request를 쓸 수 있다. 메서드, URL, 쿼리, 헤더, JSON 본문을 설정하고 이전 노드에서 정리한 값을 매핑한다. 예시에서는 업무 API에 문의를 생성한 다음 반환된 접수번호를 팀 알림에 넣는다. 문의가 도착했다는 알림과 업무 시스템에 접수됐다는 알림을 구분할 수 있는 구성이다.

인증은 API 키나 OAuth 연결 등을 **Credentials**로 생성해 노드에서 선택한다. 공식 문서는 Credentials를 외부 서비스 접속에 쓰는 인증정보로 설명하고 서비스별로 필요한 항목을 안내한다. HTTP Request에서는 지원되는 서비스라면 Predefined Credential Type을 권장하며, 그 밖의 API에는 Header auth 등 일반 인증 방식을 설정할 수 있다. API 주소만 입력한다고 그 계정의 권한이 생기지는 않으므로 서비스의 인증 방식과 허용 범위를 확인해야 한다. [인증정보 생성 문서](https://docs.n8n.io/build/understand-workflows/create-and-edit-credentials.md), [HTTP Request 문서](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest)

자체 호스팅에서는 인증정보를 저장한 데이터베이스와 암호화 키도 운영 대상이다. n8n은 처음 실행할 때 키를 만들고 인증정보를 데이터베이스에 저장하기 전에 암호화한다. 큐 모드의 모든 워커에는 같은 암호화 키를 지정해야 한다. 따라서 서버를 새로 띄우는 절차와 저장한 인증정보를 복구할 수 있는 절차를 함께 생각해야 한다. [암호화 키 문서](https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/configuration-examples/set-a-custom-encryption-key.md)

HTTP Request의 기본 성공 조건은 2xx 응답이다. 응답 본문만으로 부족하면 상태 코드와 헤더도 출력에 포함할 수 있다. **Never Error**를 켜면 응답 코드와 무관하게 성공으로 반환하므로, 이후 조건에서 상태를 직접 판별해야 한다. 예를 들어 업무 API의 거절 응답을 받은 채 성공 알림을 보내지 않도록 해야 한다. 수신 API가 오류를 어떤 코드와 본문으로 표현하는지 알아야 이 설정을 제대로 고를 수 있다.

## 실패한 문의가 어디에 있는지 찾을 수 있어야 한다

외부 서비스가 429로 요청 빈도를 제한하면 노드의 **Retry On Fail**로 대기 후 재시도를 설정할 수 있다. 대량 item을 보내는 작업은 Loop Over Items와 Wait를 조합해 묶음을 나누고 호출 사이에 간격을 둘 수 있다. 어느 쪽을 쓰든 대기 시간은 상대 서비스의 제한을 기준으로 정한다. 재시도 기능이 있다는 이유만으로 요청 빈도 제한이 없어지지는 않는다. [호출 제한 처리 문서](https://docs.n8n.io/integrations/builtin/handle-rate-limits.md)

재시도에도 실패했을 때는 오류를 알리는 별도 흐름이 필요하다. **Error Trigger**로 시작하는 워크플로를 만들고 본래 워크플로 설정의 **Error workflow**로 지정한다. 실패한 워크플로 이름, 마지막 실행 노드, 오류 메시지 등을 알림에 담을 수 있다. 여러 워크플로가 같은 오류 처리 흐름을 사용하도록 구성할 수도 있다. 실행 URL은 실행이 데이터베이스에 저장된 경우 제공되며 트리거 단계의 오류에는 없을 수 있다. 알림 문구를 만들 때 모든 오류에 실행 링크가 있다고 가정하면 안 된다. [오류 처리 문서](https://docs.n8n.io/build/flow-logic/handle-errors-gracefully.md)

놓치기 쉬운 테스트 조건도 있다. Error Trigger는 자동 실행된 워크플로가 실패할 때 동작하며 편집기에서 수동 실행한 실패로는 오류 워크플로를 테스트할 수 없다. 운영 전 검증에는 정상 문의뿐 아니라 자동 트리거로 들어온 실패가 지정된 알림까지 도달하는지도 포함해야 한다. 필수 값 누락을 명시적 실패로 다루려면 Stop And Error를 쓰는 방법도 있다. [Error Trigger 문서](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.errortrigger)

재전송의 의미도 정해야 한다. 업무 API가 저장한 뒤 응답만 끊겼다면 같은 요청을 다시 보낼 때 중복 접수가 생길 수 있다. 이 예시에서는 `requestId`를 외부 식별자로 전달하고 수신 API의 중복 방지 규칙을 확인하는 설계를 권한다. 이는 n8n의 재시도만으로 보장되는 기능이라는 뜻이 아니다. 문의 생성과 팀 알림도 각각의 외부 작업이므로 알림 실패를 처리하면서 이미 생성된 문의를 다시 만들지 않을 방법이 필요하다.

## 공식 예제로 작은 흐름부터 읽어 본다

공식 **Build your first workflow**는 매주 월요일 오전 9시에 Schedule Trigger로 시작해 NASA의 태양 플레어 자료를 가져오는 예제다. NASA API 키를 연결하고 조회 시작일을 일주일 전으로 계산한 뒤, If에서 `classType`에 `X`가 포함되는지 검사한다. 두 갈래의 결과는 PostBin으로 보낸다. 트리거, 인증, 표현식, 조건, 외부 전송을 한 흐름 안에서 볼 수 있다.

PostBin은 결과를 임시 페이지에서 확인하는 수신 도구다. 공식 문서는 bin이 생성 후 30분 동안 유지된다고 안내한다. 예제를 운영용 기록 저장소로 받아들이면 안 되며, 실제 NASA 자료에 X 등급이 없으면 해당 분기로 나오는 item도 없을 수 있다. 튜토리얼의 **Execute step**으로 노드별 출력을 보고 **Execute Workflow**로 전체 흐름과 수신 결과를 확인하는 순서가 유용하다. 이 글에서는 해당 절차를 직접 실행하지 않았다. [공식 첫 워크플로 튜토리얼](https://docs.n8n.io/build-your-first-workflow.md)

같은 패턴으로 일정에 따라 보고서를 모으거나 폼 요청을 분류해 업무 시스템에 등록하는 흐름을 구성할 수 있다. AI 기능을 넣는다면 문의 요약이나 분류를 모델에 맡기고 다음 노드에서 활용하는 방향을 생각할 수 있다. README는 모델과 도구를 연결하는 다단계 AI 워크플로도 주요 기능으로 소개한다. 다만 위 문의 예시의 분류는 명시적 조건으로 충분하므로 AI를 반드시 거칠 필요는 없다.

## 실행 장소와 이용 조건을 결정한다

n8n Cloud는 설치 없이 시작하는 관리형 서비스다. 자체 호스팅은 배포 환경과 설정을 직접 제어하는 대신 인프라 유지보수를 맡는다. 외부 Webhook 연결, 데이터 보관, 업데이트와 장애 대응을 누가 책임질지 기준으로 선택해야 한다. 자체 호스팅에는 무료 Community와 유료 에디션이 있으며 SSO나 공유 등 기능의 제공 범위는 플랜과 에디션에 따라 다르다. 모든 기능이 무료로 같다고 가정하지 말고 필요한 기능을 비교해야 한다. [배포 방식과 에디션 안내](https://docs.n8n.io/choose-how-to-use-n8n)

라이선스도 확인 대상이다. n8n은 fair-code 모델이며 일반 부분에는 **Sustainable Use License**, 지정된 기업용 코드에는 별도 Enterprise License가 적용된다. Sustainable Use License는 자체 내부 업무, 비상업 또는 개인 용도의 사용과 수정을 허용하고, 다른 사람에게 배포하거나 제공하는 경우 비상업 목적의 무료 제공으로 제한한다. 따라서 소스 공개를 무제한 상업 재판매나 호스팅 제공 허용으로 해석하면 안 된다. 외부 고객에게 제공하는 제품이나 서비스에 넣을 때는 그 용도가 공식 조건에 맞는지 별도로 확인해야 한다. [확인한 커밋의 라이선스](https://github.com/n8n-io/n8n/blob/1903d53bc07f43729aa003fef4412a49c343e26f/LICENSE.md)

문의 한 건을 끝까지 따라가면 n8n을 평가할 지점도 구체적이 된다. 원하는 서비스를 연결할 노드나 API가 있는가, 데이터 경로를 확인할 수 있는가, 실패한 실행을 찾아 후속 조치할 수 있는가, 그 흐름을 지속해서 운영할 환경과 이용 조건이 맞는가. 이 질문에 답할 수 있을 때 업무 자동화의 범위가 분명해진다.

## 더 읽을 공식 자료

- [n8n 저장소 README](https://github.com/n8n-io/n8n/blob/1903d53bc07f43729aa003fef4412a49c343e26f/README.md)
- [첫 워크플로 만들기](https://docs.n8n.io/build-your-first-workflow.md)
- [Webhook 노드](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.webhook)
- [오류 처리](https://docs.n8n.io/build/flow-logic/handle-errors-gracefully.md)
- [Cloud와 자체 호스팅 선택](https://docs.n8n.io/choose-how-to-use-n8n)
