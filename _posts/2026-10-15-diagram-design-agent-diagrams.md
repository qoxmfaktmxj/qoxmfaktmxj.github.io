---
layout: post
title: "Diagram Design 분석: AI 에이전트로 설명이 잘 되는 다이어그램 만들기"
date: 2026-10-15 23:34:00 +0900
categories: [ai]
tags: [ai-agent, agent-skills, diagram-design, svg, mermaid, documentation]
permalink: /ai/2026/10/15/diagram-design-agent-diagrams.html
description: "cathrynlavery/diagram-design의 설계 원칙, 설치와 작업 흐름, 기존 다이어그램 가져오기, 공식 활용 예제와 검증 범위를 살펴본다."
repo: cathrynlavery/diagram-design
analyzed_at: 2026-10-15
analyzed_commit: d97c5c7477e54cee17cfa6459190610da0643a05
---

AI에게 시스템 구성을 설명하고 다이어그램을 부탁하면 내용은 대체로 들어간다. 그런데 상자마다 색이 다르고 화살표가 겹쳐 정작 중요한 흐름은 눈에 들어오지 않는 경우가 있다. 기술 블로그에 넣으려고 만든 그림인데 그림을 이해하는 설명부터 길어지는 식이다.

`cathrynlavery/diagram-design`은 이런 문제를 다루는 저장소다. AI 에이전트가 그림을 만들 때 참고할 디자인 원칙, 다이어그램 유형별 작성법, HTML 예제와 Python 보조 도구를 함께 배포한다. 사용자는 설명할 내용을 전달하고 에이전트는 이 자료를 읽어 HTML 안에 SVG를 작성한다.

이 글은 **2026년 10월 15일 확인한 커밋 `d97c5c7`**을 기준으로 작성했다. 해당 커밋의 플러그인 버전은 `2.6.99`다. README, 실제 스킬 문서, 추출기와 내보내기 코드, 공식 예제를 대조했으며 일부 보조 스크립트는 직접 실행했다. 외부 기업의 도입 실적이나 생성 품질에 대한 성능 시험은 확인 범위에 포함하지 않았다.

## 1. 어떤 레포인가

Diagram Design은 Cathryn Lavery가 만든 오픈소스 다이어그램 제작 스킬이다. 배포 주체는 제작자의 회사 LittleMight이며 저장소는 MIT 라이선스를 사용한다. 제작자는 README에서 자신의 블로그에 어울리는 그림을 만들려고 시작했다고 설명한다. AI가 내용을 이해해도 매번 비슷한 상자 그림을 내놓으니 원하는 시각 표현을 문서로 정리했다. [저장소와 제작 배경](https://github.com/cathrynlavery/diagram-design/tree/d97c5c7477e54cee17cfa6459190610da0643a05)

역할을 나누면 이해하기 쉽다.

| 구성 | 맡는 일 |
| --- | --- |
| 사용 중인 AI 에이전트 | 요청을 해석하고 유형을 고르며 HTML과 SVG를 작성한다 |
| Diagram Design 스킬 | 강조, 배치, 연결선, 글꼴, 정보량과 검증 기준을 안내한다 |
| 로컬 Python 도구 | 기존 파일에서 구조를 추출하거나 생성물 검사와 SVG 내보내기를 수행한다 |
| 브라우저 | 완성된 HTML을 표시하고 PNG가 필요할 때 렌더링에 쓰인다 |

따라서 이 레포를 설치한다고 새로운 이미지 모델이 생기지는 않는다. 결과물의 구조와 문구를 결정하는 주체는 여전히 사용 중인 에이전트다. Diagram Design은 그 에이전트가 따라야 할 시각 표현 규칙과 작업 순서를 구체적으로 적어 둔 패키지에 가깝다.

Claude Code, Codex, GitHub Copilot, Cursor, Factory Droid, Pi 등 여러 환경에서 같은 내부 스킬을 사용하도록 구성돼 있다. 다만 호스트마다 설치와 명령 노출 방식은 다르다. 스킬만 설치하는 방식과 호스트의 플러그인으로 설치하는 방식을 구분해야 한다. [설치 방식과 호스트별 안내](https://github.com/cathrynlavery/diagram-design/blob/d97c5c7477e54cee17cfa6459190610da0643a05/docs/cookbook.md#r0-editable-install)

## 2. 무엇을 결과물로 만드는가

기본 산출물은 **인라인 SVG를 담은 HTML 파일**이다. 정적 템플릿은 별도 애플리케이션 빌드 없이 브라우저에서 열어 볼 수 있다. SVG의 도형과 글자가 파일 안에 있으므로 그림을 수정할 때도 에이전트에게 HTML을 고치도록 요청할 수 있다.

기본 글꼴은 Google Fonts에서 불러온다. 단일 HTML 파일이어도 외부 글꼴을 읽는 인터넷 요청은 발생한다. 시스템 글꼴을 선택하면 외부 글꼴 요청을 없앨 수 있지만 표시 환경에 따라 글자 폭이나 모양이 달라질 여지는 남는다.

출력 형식은 용도에 따라 골라야 한다.

| 형식 | 적합한 용도 | 전달할 때 알아둘 점 |
| --- | --- | --- |
| HTML | 브라우저 검토, 설명 카드까지 포함한 문서 | 편집의 기준 파일로 보관하기 좋다 |
| SVG | 벡터 그림 전달, 디자인 도구에서 후속 편집 | HTML의 바깥 제목이나 요약 카드는 빠진다 |
| PNG | 슬라이드, 위키, 블로그 이미지 | 픽셀 이미지이므로 도형별 수정에는 원본이 필요하다 |
| HTML과 PNG | 수정 가능한 원본과 배포 이미지를 함께 보관 | 두 파일을 같은 버전으로 관리해야 한다 |

내보내기는 HTML 전체를 화면 캡처하는 작업과 다르다. 공식 절차는 SVG 영역만 대상으로 삼는다. 전체 편집형 템플릿의 제목과 보조 설명까지 이미지에 들어간다고 기대하면 결과가 다를 수 있다. [출력 규격](https://github.com/cathrynlavery/diagram-design/blob/d97c5c7477e54cee17cfa6459190610da0643a05/skills/diagram-design/references/output-spec.md), [내보내기 범위](https://github.com/cathrynlavery/diagram-design/blob/d97c5c7477e54cee17cfa6459190610da0643a05/skills/diagram-design/references/export.md)

## 3. 디자인 규칙은 무엇이 다른가

이 스킬은 그림에 모든 정보를 넣으라고 권하지 않는다. 노드 하나가 별개의 개념을 나타내는지, 연결선이 새로운 관계를 설명하는지부터 따진다. 문단이나 표로 더 잘 전달되는 내용이라면 다이어그램을 만들지 말라는 지침도 있다.

배치에는 4px 그리드를 쓰고 강조색은 보통 한두 요소에만 준다. 기본 복잡도 기준은 노드 9개와 화살표 12개이며 넘치면 전체 그림과 상세 그림으로 나누는 방향을 제안한다. 이는 모든 유형의 절대 상한이라기보다 그림을 과밀하게 만들지 않기 위한 기본 예산이다. 유형과 의미 패턴에 따라 더 엄격한 기준이 붙을 수 있다.

연결선 규칙도 구체적이다. 서로 다른 축에 있는 노드는 직각으로 꺾어 연결하고 화살표의 라벨은 선과 떨어뜨린다. 여러 연결선이 같은 상자에 붙으면 접점을 나누며 관계없는 노드 뒤로 선을 통과시키지 않는다. 이런 규칙은 독자가 경로를 잘못 따라가는 일을 줄이려는 장치다.

예를 들어 요청 처리 흐름에서 모든 서비스를 주황색으로 칠하면 무엇이 핵심인지 알기 어렵다. 장애 원인을 설명하는 글이라면 큐와 병목 구간에만 강조를 주고 나머지 서비스는 배경으로 두는 편이 목적에 맞는다. 어떤 두 요소를 강조할지는 기술 내용과 글의 주장을 아는 사람이 판단해야 한다. [설계 원칙과 연결선 규칙](https://github.com/cathrynlavery/diagram-design/blob/d97c5c7477e54cee17cfa6459190610da0643a05/skills/diagram-design/SKILL.md)

## 4. 유형 선택은 모양보다 설명할 내용에서 시작한다

확인한 스킬 본문은 45개 시각 유형을 안내한다. 저장소 About에는 44개라는 소개가 남아 있어 숫자가 일치하지 않는다. 이 글의 기준은 해당 커밋의 `SKILL.md`다. 지원 유형 수는 업데이트 때 달라질 수 있으므로 목록 자체를 확인하는 편이 정확하다.

유형은 상자와 화살표가 있는 그림에 한정되지 않는다.

| 설명하려는 내용 | 적합한 유형 | 독자가 읽어야 할 관계 |
| --- | --- | --- |
| 한 시점의 서비스 구성 | Architecture | 구성요소, 경계와 연결 |
| 개편 전후의 구조 변화 | Architecture delta | 추가, 삭제, 이동과 연결 변경 |
| 요청과 응답의 시간 순서 | Sequence | 누가 누구에게 어떤 메시지를 보냈는가 |
| 대기, 재시도와 종료 조건 | State machine | 어떤 조건에서 상태가 바뀌는가 |
| 부서 사이의 업무 인계 | Swimlane 또는 Process | 담당자와 전달 시점 |
| 물리 테이블과 외래 키 | Database schema | 컬럼, 제약과 참조 관계 |
| 수량의 분기와 합류 | Sankey | 각 경로로 얼마나 흘렀는가 |
| 고객 접점과 내부 처리 | Service blueprint | 고객에게 보이는 단계와 뒤에서 하는 일 |

동작이나 위험이 설명의 중심이면 유형을 고르기 전에 의미 패턴을 살핀다. 큐의 적체는 병목 패턴, 허용 경로와 신뢰 경계는 보안 경로 패턴, 재시도와 취소가 있는 작업은 수명주기 패턴으로 해석하는 식이다. 패턴은 어떤 의미를 보존할지, 유형은 그것을 어떻게 배치할지 결정한다.

이 구분 덕분에 모든 요청이 Architecture 그림으로 수렴하는 것을 피할 수 있다. API 호출의 재시도 순서를 설명하려는데 서버 위치만 배치하면 예쁜 그림을 얻어도 독자가 궁금해한 동작은 설명하지 못한다. [유형 선택표](https://github.com/cathrynlavery/diagram-design/blob/d97c5c7477e54cee17cfa6459190610da0643a05/skills/diagram-design/SKILL.md#3-selection-semantic-pattern-then-visual-type), [의미 패턴](https://github.com/cathrynlavery/diagram-design/blob/d97c5c7477e54cee17cfa6459190610da0643a05/skills/diagram-design/references/semantic-patterns.md)

## 5. 설치하고 첫 그림을 만드는 흐름

저장소는 여러 에이전트에 공통 스킬을 설치할 때 다음 명령을 안내한다. 이 명령은 이 글을 위한 조사 과정에서 실행하지 않았으며 독자가 선택한 호스트에 스킬을 추가하는 설치 예시다.

```bash
npx skills add cathrynlavery/diagram-design
```

이 방식은 스킬과 참조 문서, 예제, 보조 스크립트를 설치한다. 설치 범위에는 호스트 전용 플러그인이 제공하는 슬래시 명령 등록이 포함되지 않는다. 독립 설치본은 마켓플레이스 업데이트를 자동으로 따라가지 않으며 README는 `npx skills update diagram-design`을 갱신 방법으로 안내한다. 호스트 전용 패키지를 선택했다면 해당 호스트의 설치 문서를 따라야 한다.

HTML 작성과 정적 열람은 PNG용 브라우저 도구 없이도 가능하다. 공식 환경 진단 문서는 Python 3.10 이상을 요구하고 PNG 내보내기에는 Python Playwright와 실행 가능한 Chromium을 확인하도록 한다. SVG 내보내기와 PNG 렌더링의 요구사항을 분리해서 준비하면 된다. [설치 안내](https://github.com/cathrynlavery/diagram-design/blob/d97c5c7477e54cee17cfa6459190610da0643a05/README.md), [환경 진단](https://github.com/cathrynlavery/diagram-design/blob/d97c5c7477e54cee17cfa6459190610da0643a05/skills/diagram-design/references/doctor.md)

설치 후 첫 요청에는 내용, 독자, 크기와 저장 위치를 같이 적는 편이 낫다. 다음은 이 글에서 구성한 요청 예시다.

```text
diagram-design을 사용해 주문 처리 구조를 설명하는 정적 다이어그램을 만들어줘.
독자는 백엔드 개발자와 기획자야.
구성요소는 웹 앱, API Gateway, 주문 API, 주문 큐, 워커, PostgreSQL이야.
주문 API가 큐에 메시지를 보내고 워커가 처리한 뒤 DB에 기록해.
큐를 통한 비동기 처리를 강조하고, 확인되지 않은 보안 구성을 추가하지 마.
기본 색상을 사용하고 doc-inline 크기의 HTML로 만들어줘.
그리기 전에 선택한 유형과 생략할 내용을 알려줘.
파일은 docs/diagrams/order-flow.html에 저장해줘.
```

기본 스킨이 그대로인 새 프로젝트라면 스킬은 브랜드를 설정할지, 저장한 프로필을 쓸지, 기본값으로 진행할지 확인하도록 한다. 이어서 유형과 크기, 복잡도 때문에 덜어낼 항목을 정한 뒤 HTML을 만든다. 초안을 보면 연결 방향과 빠진 조건부터 확인하고 그다음 간격과 색을 조정하면 된다.

노드 이름만 나열하는 것보다 어떤 관계를 설명할지 적어 주는 편이 유용하다. 위 요청에서도 큐가 있다는 사실과 주문 API가 큐에 메시지를 넣는다는 동작은 서로 다른 정보다. 에이전트가 모르는 연결을 임의로 채우지 않도록 명시한 부분이다.

## 6. 기존 Mermaid, draw.io, Excalidraw 파일은 어떻게 활용하나

이 레포에서 가져오기는 **내용을 추출한 뒤 새 배치로 다시 그리는 작업**이다. 원래 그림의 좌표, 색, 테마를 그대로 보존하는 파일 변환으로 생각하면 안 된다.

각 추출기는 원본을 에이전트가 읽기 쉬운 중간 표현으로 정리한다. 노드와 연결, 그룹, 순환 관계, 연결이 많은 지점, 시작점과 끝점 등을 살피고 에이전트가 그 자료로 표현할 내용을 고른다.

| 원본 | 추출에 쓰는 정보 | 그대로 이어지지 않는 부분 |
| --- | --- | --- |
| Mermaid | 노드, 메시지 순서, 상태 조건, 엔티티와 관계 | 렌더러의 배치, 테마와 스타일 |
| draw.io | 노드와 연결, 컨테이너, 기하 정보와 구조 | 원래 좌표와 색을 유지하는 배치 |
| Excalidraw | 도형, 연결, 연결된 라벨, 프레임과 그룹 | 손그림 좌표와 스타일, 이미지와 임베드 내용 |

Mermaid 가져오기는 지원하는 문법의 범위를 살펴야 한다. 확인한 추출기는 `flowchart`와 `graph`, `sequenceDiagram`, `stateDiagram-v2`, `erDiagram`을 지원한다. Diagram Design이 Gantt 그림을 만들 수 있다는 사실과 Mermaid의 `gantt` 소스를 가져올 수 있다는 주장은 구분해야 한다. [Mermaid 가져오기](https://github.com/cathrynlavery/diagram-design/blob/d97c5c7477e54cee17cfa6459190610da0643a05/skills/diagram-design/references/import-mermaid.md), [draw.io 가져오기](https://github.com/cathrynlavery/diagram-design/blob/d97c5c7477e54cee17cfa6459190610da0643a05/skills/diagram-design/references/import-drawio.md), [Excalidraw 가져오기](https://github.com/cathrynlavery/diagram-design/blob/d97c5c7477e54cee17cfa6459190610da0643a05/skills/diagram-design/references/import-excalidraw.md)

다시 그리기 전에는 네 가지를 정한다.

1. 형식: HTML, SVG, PNG 중 무엇을 전달할지.
2. 크기: 문서 본문, 슬라이드, 소셜 이미지 중 어디에 넣을지.
3. 상세도: `faithful`, `balanced`, `simplified` 중 어느 정도로 압축할지.
4. 독자: `engineer`, `mixed`, `executive` 중 누구에게 설명할지.

슬라이드용 그림에 글자를 그대로 줄여 넣는 방식은 피한다. 크기 프리셋은 캔버스와 글자 크기 기준을 함께 바꾼다. 독자와 상세도는 용어와 노드 수에 영향을 준다. 다만 `faithful`을 골라도 원본의 시각 배치를 복제한다는 뜻은 아니다.

가져오기 결과에는 무엇을 합치고 접고 버렸는지 기록하는 fidelity ledger를 남기도록 한다. 원본에 있던 연결이 사라졌다면 단순화의 결과인지 누락인지 이 기록을 보고 따져야 한다. 디자인이 깔끔해졌다는 이유만으로 원본의 기술 의미까지 보존됐다고 판단해서는 안 된다. [상세도와 출력 기준](https://github.com/cathrynlavery/diagram-design/blob/d97c5c7477e54cee17cfa6459190610da0643a05/skills/diagram-design/references/output-spec.md)

## 7. 공식 예제에서는 무엇을 설명하고 있나

아래는 저장소에 포함된 설명용 예제다. 각 이름을 누르면 공식 갤러리의 HTML을 열 수 있다. 실제 고객사의 운영 구성이나 도입 사례로 확인한 자료는 아니다.

### OAuth 토큰 갱신과 재시도

[OAuth 시퀀스 예제](https://cathrynlavery.github.io/diagram-design/example-sequence-oauth.html)는 클라이언트, Resource API, Auth 사이의 메시지를 시간 순서로 보여준다. 유효한 bearer token이면 본문을 반환한다. 401 경로에서는 토큰을 갱신한 뒤 API 호출을 재시도한다. 두 경우는 ALT 영역으로 나뉜다.

이 그림은 서버 목록보다 성공 경로와 실패 후 복구 경로의 차이를 설명한다. 인증 문서에서 처음부터 토큰 갱신의 모든 구현 세부를 나열하기보다 어떤 응답 뒤에 어떤 요청이 이어지는지 먼저 보여줄 때 적합하다. 비동기 감사 메시지도 일반 요청과 구분해 표시한다. [예제 소스](https://github.com/cathrynlavery/diagram-design/blob/d97c5c7477e54cee17cfa6459190610da0643a05/skills/diagram-design/assets/example-sequence-oauth.html)

### 주문 처리 아키텍처의 개편 전후

[Architecture delta 예제](https://cathrynlavery.github.io/diagram-design/example-architecture-delta.html)는 기존 dispatcher를 제거하고 durable order queue를 도입하는 변화를 보여준다. Orders API는 v1에서 v2로 바뀌며 워커는 구현 변경 없이 위치가 이동한다. 화면과 데이터베이스는 유지된다.

그림 가운데에는 구성요소와 연결에 대한 변경 7건을 적는다. API 변경, dispatcher 제거, 큐 추가, 워커 이동뿐 아니라 어느 연결을 다시 이었는지도 구분한다. 변경 전과 후의 그림을 따로 보여주는 것보다 무엇을 검토해야 하는지 찾기 쉽다. 특히 구성요소의 이동과 구현 자체의 변경을 구별하는 데 도움이 된다. [예제 소스](https://github.com/cathrynlavery/diagram-design/blob/d97c5c7477e54cee17cfa6459190610da0643a05/skills/diagram-design/assets/example-architecture-delta.html)

### 레거시 IT의 현재 상태

[IT current-state 예제](https://cathrynlavery.github.io/diagram-design/example-it-state.html)는 Northwind Retail이라는 예시 조직의 수집, 처리, 배포 구간을 나눈다. 매장 CSV와 공급사 XLSX가 공유 드라이브와 스프레드시트를 거쳐 온프레미스 RDBMS, 보고 포털과 이메일로 전달된다.

수작업 대사, 버전 관리가 없는 공유 폴더, 수동 새로고침 같은 문제를 해당 위치에 붙인다. 현대화 논의에서는 새 시스템 그림에 앞서 현재 누가 파일을 옮기고 어디서 기다리는지 합의할 필요가 있다. 이 유형은 이런 현황을 설명할 때 적합하다. 다만 그림에 표시된 문제를 특정 회사에 실제로 존재하는 문제로 옮겨 적어서는 안 된다. [예제 소스](https://github.com/cathrynlavery/diagram-design/blob/d97c5c7477e54cee17cfa6459190610da0643a05/skills/diagram-design/assets/example-it-state.html)

## 8. 브랜드와 한국어 문서는 어떻게 처리하나

브랜드 설정은 배경색 하나를 바꾸는 작업보다 범위가 넓다. 배경, 본문, 보조 글자와 강조색을 `paper`, `ink`, `muted`, `accent` 같은 의미 역할에 연결하고 제목과 노드 이름의 글꼴도 정한다. 웹사이트에서 스타일을 추출할 때는 제안한 변경을 먼저 보여주고 사용자의 승인을 받도록 안내한다.

여러 프로젝트를 다룬다면 설치된 스킬 파일을 매번 고치는 것보다 이름 있는 프로필을 쓰는 방식이 낫다. 공식 규약에 따르면 프로필을 `~/.diagram-design/profiles/`에 두고 프로젝트 루트의 `.diagram-design` 파일로 선택한다.

```text
profile: company-docs
```

이렇게 하면 프로젝트마다 다른 스타일을 사용할 수 있다. 관리형 플러그인 업데이트가 개인 설정을 덮어쓰는 문제도 줄일 수 있다. 프로필 자체는 별도 파일이므로 팀원에게 공유하거나 새 환경으로 옮길 때 함께 관리해야 한다. [프로필 저장과 선택 규칙](https://github.com/cathrynlavery/diagram-design/blob/d97c5c7477e54cee17cfa6459190610da0643a05/skills/diagram-design/references/profiles.md), [온보딩 절차](https://github.com/cathrynlavery/diagram-design/blob/d97c5c7477e54cee17cfa6459190610da0643a05/skills/diagram-design/references/onboarding.md)

한국어 지침도 따로 있다. 기본 라틴 글꼴만으로 한글을 표시하지 않고 노드에는 Noto Sans KR, 제목에는 Noto Serif KR 등을 연결한다. 한글 라벨은 최소 12px을 유지하고 긴 이름이 들어가지 않으면 글자를 더 줄이기보다 이름을 짧게 하도록 한다. 영문 화살표 라벨에 사용하는 작은 대문자와 자간 설정도 한글에는 그대로 적용하지 않는다.

한국어 문서에서는 이 부분을 실제 렌더링으로 확인할 필요가 있다. 영문 예제에서 넉넉한 상자라도 한글 업무명이 들어가면 줄바꿈과 폭이 달라진다. 스킬에 한국어 규칙이 있다는 사실이 모든 생성물의 가독성을 보장하지는 않는다. [한국어 라벨 지침](https://github.com/cathrynlavery/diagram-design/blob/d97c5c7477e54cee17cfa6459190610da0643a05/skills/diagram-design/references/style-guide.md#korean-labels)

## 9. 원본을 내려받아 직접 확인한 범위

소개 문구만으로 판단하지 않으려고 해당 커밋의 저장소를 임시 경로에 내려받았다. 사용자 환경에 플러그인을 설치하지는 않았고 제공된 입력과 예제에 보조 스크립트를 실행했다.

| 확인 항목 | 실행 결과 | 이 결과로 알 수 있는 범위 |
| --- | --- | --- |
| Mermaid 예제 추출 | 노드 9개, 연결 7개, 컨테이너 2개를 보고 | 입력을 구조화된 중간 표현으로 읽는 흐름 |
| OAuth HTML 자체 검사 | `OK` | 제공된 예제가 자체 검사의 조건을 통과 |
| Architecture delta HTML 자체 검사 | `OK` | 해당 예제의 구조적 검사 결과 |
| 두 HTML의 SVG 내보내기 | `--system-fonts`로 파일 생성 성공 | 글꼴 import를 생략한 SVG 추출 경로가 작동 |

저장소 루트에서 실행한 명령의 형태는 다음과 같다. 내보내기 결과 경로는 설명을 위해 단순화했다.

```bash
python skills/diagram-design/scripts/mermaid_extract.py scripts/fixtures/sample-flowchart.mmd
python skills/diagram-design/scripts/self_check.py skills/diagram-design/assets/example-sequence-oauth.html
python skills/diagram-design/scripts/export_svg.py skills/diagram-design/assets/example-sequence-oauth.html oauth.svg --system-fonts
```

Mermaid 추출 결과의 노드 9개에는 실제 도형 노드 7개와 컨테이너 2개가 포함된다. 원본 문서에 따르면 다시 그린 예제에서는 연결되지 않은 메모를 덜어내 도형 노드 6개로 정리한다. 이처럼 추출 결과와 최종 그림의 노드 수에는 차이가 있을 수 있다.

이번에는 보조 도구와 제공 예제만 확인했다. 자연어 요청으로 새 그림을 생성하는 전 과정, PNG 내보내기, 모든 유형과 호스트의 설치 성공까지 시험하지는 않았다. 두 예제의 `OK`를 모든 생성물의 품질 보증으로 확대해서 해석할 수는 없다. [추출기](https://github.com/cathrynlavery/diagram-design/blob/d97c5c7477e54cee17cfa6459190610da0643a05/skills/diagram-design/scripts/mermaid_extract.py), [자체 검사 코드](https://github.com/cathrynlavery/diagram-design/blob/d97c5c7477e54cee17cfa6459190610da0643a05/skills/diagram-design/scripts/self_check.py), [SVG 내보내기 코드](https://github.com/cathrynlavery/diagram-design/blob/d97c5c7477e54cee17cfa6459190610da0643a05/skills/diagram-design/scripts/export_svg.py)

## 10. 검사 도구가 확인하는 것과 사람이 볼 것

설치형 스킬의 `self_check.py`는 접근성 이름과 설명, 허용되지 않은 외부 자원과 실행 코드, SVG 표시 영역 밖으로 나가는 요소 등을 점검한다. 저장소 기여용 검사에는 스타일과 기하 검증도 따로 있다. 설치된 스킬에 모든 유지보수용 검사 파일이 들어 있는 것은 아니다.

하지만 구조 검사는 기술 사실의 검증을 대신하지 못한다. 화살표가 겹치지 않아도 호출 방향이 틀릴 수 있고 상태 전이가 보기 좋게 정리돼도 타임아웃 처리가 빠질 수 있다. 설명하는 시스템의 근거 자료와 결과물을 대조해야 한다.

검토할 때는 다음 순서가 실용적이다.

1. 등장한 구성요소와 관계가 원본 자료에 있는지 확인한다.
2. 분기 조건, 실패와 재시도, 상태 전이가 보존됐는지 읽는다.
3. 단순화로 삭제한 항목을 기록과 대조한다.
4. 실제 표시 크기에서 글자와 연결선이 읽히는지 확인한다.
5. HTML과 내보낸 파일을 함께 보관해 후속 수정의 기준을 남긴다.

## 11. 어떤 업무에 가져다 쓰기 좋은가

공식 예제와 작업 규약을 기준으로 보면 기술 블로그, 시스템 개편 설명, 설계 리뷰용 그림에 잘 맞는다. 다음은 확인된 기능을 바탕으로 이 글에서 제안하는 활용 방식이며 외부 조직의 도입 사례를 주장하는 내용은 아니다.

**기술 블로그의 핵심 흐름 설명.** 본문 전체를 그림 하나에 밀어 넣기보다 독자가 헷갈리는 구간을 고른다. 토큰 갱신, 큐를 통한 비동기 처리, 상태 전이처럼 순서와 조건이 중요한 내용을 한 장으로 보완하는 방식이다.

**아키텍처 개편 리뷰.** 변경 전과 후의 연결을 유지한 채 추가, 삭제와 이동을 기록하면 리뷰 범위를 구체화하기 쉽다. 같은 서비스가 자리를 옮긴 것인지, 구현이나 인터페이스까지 달라졌는지 나눠 설명할 수 있다.

**기존 업무 문서의 발표용 재구성.** 엔지니어용 Mermaid 원본은 계속 관리하고 발표할 때 별도의 설명용 그림을 만든다. 상세도를 줄였다면 생략 기록을 함께 남겨 원본과의 관계를 추적한다.

**여러 고객사의 문서 스타일 관리.** 같은 스킬을 사용하면서 프로젝트별 프로필을 선택하면 색과 글꼴을 반복 지정하는 일을 줄일 수 있다. 다만 프로필에 담긴 스타일이 내용의 정확성까지 결정하지는 않는다.

## 12. Mermaid나 수동 편집 도구와 어떻게 선택할까

| 판단 기준 | Mermaid | draw.io와 Excalidraw | Diagram Design |
| --- | --- | --- | --- |
| 수정의 중심 | 짧은 텍스트 문법 | 캔버스의 도형과 연결 | 에이전트 요청과 HTML/SVG 수정 |
| 자주 바뀌는 구조의 이력 검토 | 의미 변화의 텍스트 diff를 읽기 편하다 | 원본 파일과 화면을 함께 확인한다 | 생성된 좌표와 스타일 때문에 diff가 길어질 수 있다 |
| 세부 위치를 직접 조정 | 렌더러와 문법의 제약이 있다 | 캔버스에서 직접 옮긴다 | 에이전트에 재요청하거나 SVG 코드를 고친다 |
| 문서의 스타일에 맞춘 그림 | 테마와 설정으로 조정한다 | 작성자가 스타일을 맞춘다 | 스타일 지침과 프로필을 재사용한다 |
| 기존 Diagram Design 결과의 왕복 편집 | 전용 왕복 변환을 전제로 하지 않는다 | 원래 편집 형식으로 유지해야 편하다 | 원본 도구의 편집 파일을 다시 만드는 흐름은 아니다 |

Diagram Design 결과도 텍스트 파일이므로 Git diff는 가능하다. 다만 Mermaid처럼 짧은 의미 문법을 편집하는 경험과는 다르다. SVG 좌표나 CSS 변경이 많아지면 관계 하나가 바뀐 내용을 diff에서 찾기 어려워질 수 있다.

시스템 구성이 자주 바뀌고 코드 리뷰에서 관계 변경을 추적해야 한다면 Mermaid 원본을 유지할 이유가 있다. 발표나 발행을 앞두고 독자가 읽을 순서와 시각 표현을 다듬고 싶다면 Diagram Design을 별도 산출물 제작에 붙여 볼 만하다. 수동으로 도형을 계속 옮기는 작업이 중요하면 캔버스 편집 도구의 사용성이 더 맞을 수도 있다.

## 13. 도입 전에 알아둘 제한

같은 요청을 다시 실행해도 배치가 완전히 같다고 보장되지 않는다. SVG를 그리는 주체가 에이전트이므로 모델과 컨텍스트의 영향을 받는다. 만족스러운 HTML을 얻었다면 새로 생성하는 것보다 기존 파일을 대상으로 수정 범위를 정하는 편이 결과를 관리하기 쉽다.

가져오기는 손실 없는 왕복 변환이 아니다. 그림에 들어 있던 이미지, 스타일, 원래 좌표를 버릴 수 있고 상세도에 따라 내용도 접거나 합친다. 원본 파일은 별도로 남기는 것이 좋다.

정적 출력이 기본이지만 저장소에는 선택적인 모션 규약도 있다. 따라서 레포 전체를 JavaScript가 전혀 없는 패키지라고 설명하는 것은 부정확하다. 기본 정적 그림의 의존성과 선택 기능의 조건을 나눠 봐야 한다.

데이터 처리도 사용 중인 에이전트 환경을 따른다. 프로젝트의 개인정보 안내는 Diagram Design 자체에 별도 서버, 분석과 텔레메트리가 없다고 설명한다. 동시에 프롬프트와 파일은 에이전트 제공자가 처리하고 기본 글꼴은 Google Fonts에 요청하며 브랜드를 웹사이트에서 가져오면 해당 사이트를 방문한다고 명시한다. 로컬 Python 도구를 사용한다는 이유만으로 전체 작업이 완전한 로컬 처리라고 판단할 수는 없다. [개인정보 안내](https://github.com/cathrynlavery/diagram-design/blob/d97c5c7477e54cee17cfa6459190610da0643a05/PRIVACY.md)

이 레포를 활용하려면 설명할 관계, 독자, 출력 크기를 먼저 정한다. 그다음 스킬의 유형과 스타일 규칙을 적용하고 생성된 그림이 원본의 조건과 연결을 지켰는지 확인하면 된다. 첫 시도는 한 개의 요청 흐름이나 한 번의 구조 변경처럼 범위가 작은 문서가 적당하다.

## 참고 자료

- [분석 기준 커밋](https://github.com/cathrynlavery/diagram-design/commit/d97c5c7477e54cee17cfa6459190610da0643a05)
- [공식 갤러리](https://cathrynlavery.github.io/diagram-design/)
- [스킬 본문과 유형 선택 규칙](https://github.com/cathrynlavery/diagram-design/blob/d97c5c7477e54cee17cfa6459190610da0643a05/skills/diagram-design/SKILL.md)
- [설치부터 가져오기와 검증까지의 cookbook](https://github.com/cathrynlavery/diagram-design/blob/d97c5c7477e54cee17cfa6459190610da0643a05/docs/cookbook.md)
- [출력 규격](https://github.com/cathrynlavery/diagram-design/blob/d97c5c7477e54cee17cfa6459190610da0643a05/skills/diagram-design/references/output-spec.md)
- [MIT 라이선스](https://github.com/cathrynlavery/diagram-design/blob/d97c5c7477e54cee17cfa6459190610da0643a05/LICENSE)
