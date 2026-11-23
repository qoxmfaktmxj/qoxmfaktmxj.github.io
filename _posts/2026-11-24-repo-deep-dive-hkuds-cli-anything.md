---
layout: post
title: "Repo Deep Dive: HKUDS/CLI-Anything — 기존 소프트웨어를 에이전트용 명령으로 연결하는 두 경로"
date: 2026-11-24 07:11:12 +0900
categories: [github-repo-analysis]
repo: HKUDS/CLI-Anything
trending_rank: 3
trending_period: daily
trending_checked_at: 2026-11-24 07:10:28 +0900
trending_url: https://github.com/trending?since=daily
---

2026년 11월 24일 07:10 KST에 확인한 GitHub Trending 일간 전체 언어 목록에서 `HKUDS/CLI-Anything`는 3위였다. **이 순위는 저장소 선정 시점의 스냅샷이며, 발행 시점이나 독자가 확인하는 시점의 실시간 순위가 아니다.** 아래 설명은 현재 공개된 README와 CLI-Hub 사용 문서, 생성 명령 정의, 실제 LibreOffice 하네스 안내를 대조한 결과다. 예시 명령의 존재와 설명은 문서·소스로 확인했지만, 여기서 새 하네스를 생성하거나 실제 앱을 설치해 성능을 측정하지는 않았다.

## 1. 프로젝트 소개

CLI-Anything는 홍콩대학교 데이터 사이언스 연구실인 HKUDS가 공개한 프로젝트로, 기존 소프트웨어를 AI 에이전트가 호출할 수 있는 명령행 인터페이스로 연결하는 데 초점을 둔다. 사용자는 이미 만들어진 CLI 하네스를 CLI-Hub에서 찾아 설치할 수 있고, 원하는 대상이 없다면 AI 코딩 에이전트용 생성 명령으로 소프트웨어의 소스 코드를 분석해 새 하네스를 만들 수 있다. 두 경로는 목적이 다르다. 전자는 사용 가능한 도구를 발견하고 실행하는 패키지 관리 흐름이고, 후자는 소스와 실제 백엔드를 확인하며 명령·테스트·설치 형태를 만드는 개발 흐름이다.

여기서 하네스는 대상 프로그램을 대체하는 독립적인 그림 편집기나 문서 편집기를 뜻하지 않는다. 예를 들어 저장소의 LibreOffice 하네스는 Writer·Calc·Impress 문서를 다루는 명령을 제공하고, Microsoft Office 형식 변환이나 PDF 내보내기에는 LibreOffice의 headless 실행을 요구한다. README의 설계 설명도 실제 응용 프로그램의 백엔드 또는 유효한 프로젝트 파일과 렌더러를 연결하는 방식을 강조한다. 따라서 필요한 원본 프로그램이나 서비스가 빠져 있으면 패키지 설치만으로 해당 기능까지 사용할 수 있다고 생각해서는 안 된다. 소스가 없는 상용 GUI 전체를 자동으로 명령화한다는 의미도 아니다.

## 2. 해결하려는 문제

에이전트가 전문 소프트웨어를 다룰 때 화면 좌표와 클릭에 기대면 창 배치나 UI 변경에 작업이 흔들릴 수 있다. 반대로 개별 앱의 API를 직접 호출하려면 인증, 상태 관리, 객체 형식, 결과 해석을 대상마다 새로 익혀야 한다. CLI-Anything의 접근은 사용자가 `--help`로 명령 구조를 확인하고, 한 번 실행하는 하위 명령이나 대화형 REPL에서 작업하며, 에이전트는 `--json` 응답을 읽는 공통적인 조작 면을 마련하는 것이다. 이것이 모든 GUI 자동화를 항상 대체한다는 검증 결과는 아니지만, 문서에 나온 Writer 문서 작성이나 Blender 장면 조작처럼 명령으로 표현할 수 있는 작업에는 분명한 입력·출력 경계를 준다.

또 다른 문제는 '프로젝트 파일을 만들었다'와 '실제 앱이 결과를 올바르게 렌더링했다'가 다르다는 점이다. 저장소의 HARNESS 방법론은 원본 응용 프로그램을 호출해 결과물을 만들고, 내보낸 파일의 형식이나 내용을 테스트할 것을 요구한다. 생성 과정의 테스트 계획과 실제 파일을 쓰는 E2E 검증 단계는 이 차이를 줄이기 위한 절차다. 다만 생성기가 검증 단계를 명시한다는 사실만으로 임의의 새 대상에서 완성도나 테스트 통과를 보장하지는 않는다. README 역시 사용 가능한 소스 코드와 충분한 성능의 코딩 모델에 의존하며, 생성 결과에 추가 수정이 필요할 수 있다고 적는다.

## 3. 주요 기능

**CLI-Hub로 기존 하네스 찾기.** `cli-hub list`는 등록된 CLI를 보여 주고, `search <검색어>`는 이름·설명·분류에 맞는 후보를 찾는다. `info <이름>`은 선택한 도구의 세부 정보를 확인하는 단계다. 이어 `install`, `update`, `uninstall`은 설치 상태를 관리하고, `launch <이름> [인수]`는 설치한 도구를 실행한다. 이는 대상 앱의 작업 명령 자체와 다르다. 예를 들어 `cli-hub install gimp`는 하네스를 준비하는 단계이고, 이미지 프로젝트를 만드는 작업은 설치된 `cli-anything-gimp` 쪽 명령이 담당한다. 목록과 검색은 `--json` 출력도 안내되어 있어 에이전트가 결과를 구조적으로 읽을 수 있다.

**소스 기반 하네스 생성과 개선.** Claude Code 플러그인에서 `/cli-anything <소스 경로 또는 GitHub 저장소 URL>`을 호출하면, 명령 정의에 따라 소스 확보·분석, 명령 구조 설계, Click 기반 CLI 구현, 테스트 계획·구현·실행, 스킬 문서 생성, 패키징·로컬 설치 순서로 작업한다. 입력은 단순한 제품 이름이 아니라 분석할 수 있는 실제 소스 위치다. 상위 README의 일부 빠른 시작 문구에는 `/cli-anything gimp`처럼 이름만 쓰인 예시가 있지만, 현재 생성 명령 정의는 이름만으로는 받지 않는다고 명시한다. 따라서 재현 가능한 사용 예시는 경로나 URL을 써야 한다. `/cli-anything:refine <경로> [초점]`는 이미 만든 하네스의 빠진 기능을 분석해 명령·테스트·문서를 넓히는 별도 흐름이고, `:test`와 `:validate`는 테스트 실행과 HARNESS 기준 확인을 맡는다.

**생성된 CLI의 두 실행 방식.** 설치된 `cli-anything-<software>`는 하위 명령을 한 번씩 실행하거나, 인수 없이 시작해 REPL에서 여러 작업을 이어갈 수 있도록 설계된다. `--json`은 사람이 읽기 위한 장식적 출력과 달리 프로그램이 처리할 구조화된 응답을 제공한다. LibreOffice 하네스의 문서에는 `document new`로 편집 가능한 프로젝트를 만들고, `writer add-heading`이나 `writer add-table`로 내용을 넣고, `export render`로 결과 형식에 내보내는 명령이 실제로 적혀 있다. 문서 정보나 요소 목록은 `document info`·`writer list`로 확인한다. 생성기가 모든 대상에서 동일한 세부 명령을 낸다는 뜻은 아니며, 각 하네스의 `--help`와 사용 문서를 확인해야 한다.

**미리보기 상태 읽기.** CLI-Hub 문서는 미리보기를 지원하는 하네스가 먼저 `preview` 명령으로 번들 또는 라이브 세션을 만들고, `cli-hub previews inspect`, `html`, `watch`, `open`이 그 상태를 읽거나 표시한다고 구분한다. 특히 라이브 세션은 현재 결과를 가리키는 상태와 명령별 미리보기 이력을 읽는다. 뷰어 명령 자체가 렌더링을 실행하거나 결과를 외부에 게시하는 것은 아니다. 이 기능은 미리보기를 구현한 하네스에서만 의미가 있으며, 모든 등록 CLI에 동일하게 적용된다고 일반화할 수 없다.

## 4. 사용 방법과 동작 흐름

기존 도구를 쓰는 가장 짧은 경로는 Python 환경에서 CLI-Hub를 설치하고 등록 정보를 살펴보는 것이다. 아래 순서는 프로젝트 README와 CLI-Hub 문서의 예시다.

```bash
pip install cli-anything-hub
cli-hub search image
cli-hub info gimp
cli-hub install gimp
cli-hub launch gimp
```

`search` 결과는 설치 가능한 후보를 찾는 자료이고 `info`는 선택한 도구의 세부 사항이다. 설치 후에는 해당 CLI의 `--help`를 확인해 실제 작업 명령을 고른다. GIMP 같은 실제 앱을 감싼 하네스라면 원본 앱과 그 실행 환경도 준비해야 한다. 명령을 에이전트에서 읽을 때는 예컨대 `cli-hub list --json`처럼 JSON 출력을 요청할 수 있지만, 출력에 도구가 나열된다는 사실과 그 도구의 백엔드가 이 컴퓨터에서 정상 작동한다는 사실은 별개다.

새 하네스를 만들려면 Python 3.10 이상, 대상 소스, 지원되는 AI 코딩 에이전트가 필요하다. Claude Code 경로는 플러그인 마켓플레이스를 추가한 뒤 `cli-anything` 플러그인을 설치한다. 그 후 실제 대상 저장소를 인수로 준다.

```text
/plugin marketplace add HKUDS/CLI-Anything
/plugin install cli-anything
/cli-anything https://github.com/blender/blender
```

명령 정의상 URL을 주면 에이전트가 저장소를 로컬에 복제한 뒤 분석한다. 생성 절차가 성공했다면 대상의 `agent-harness`에서 `pip install -e .`로 로컬 설치하고 `cli-anything-<software> --help`로 명령을 확인하는 흐름이다. 테스트 단계에서는 실제 백엔드와 파일을 쓰는 E2E 테스트 및 설치된 실행 파일을 부르는 하위 프로세스 검증을 요구한다. 따라서 결과를 읽을 때는 '생성 완료'라는 설명만 보지 말고 테스트 결과, 설치된 명령의 도움말, 실제 출력물을 각각 확인해야 한다.

저장소가 제공하는 LibreOffice 예시는 `document new`로 Writer 프로젝트 JSON을 만들고, `--project`로 이를 지정해 제목과 표를 추가한 뒤 `export render`로 PDF를 내보낸다. 이때 프로젝트 JSON은 편집 상태이며 PDF는 렌더링 결과물이다. `--json document info`의 응답은 문서 종류와 요소 수 같은 상태를 기계가 읽는 용도이지 PDF 내용을 대신하는 것이 아니다. 실제 PDF 변환에는 LibreOffice/soffice가 필요하다는 점도 하네스 문서가 명시한다. 이렇게 상태 확인 명령과 최종 산출물을 나눠 보는 것이 예시 결과를 해석하는 정확한 방법이다.

## 5. 활용 사례

**문서 작성·변환 자동화.** LibreOffice 하네스의 사용 문서에는 Writer 문서 생성, 문단·제목·표 추가, Calc 셀 변경, Impress 슬라이드 추가, 기존 Office·ODF 문서 가져오기, ODF·PDF·Office 형식 내보내기가 각각 명령으로 설명돼 있다. 예를 들어 기존 DOCX를 프로젝트 JSON으로 가져와 문단을 덧붙인 뒤 수정본을 내보내는 순서를 문서가 제시한다. 그 경우 입력 파일, 편집 상태 파일, 출력 파일을 별도로 확인할 수 있다. 단, 특정 파일의 레이아웃 보존 수준은 이 글에서 검증하지 않았다.

**다이어그램을 단계적으로 제작하기.** 공식 README의 Draw.io 데모는 에이전트가 HTTPS 연결 과정을 나타내는 다이어그램을 CLI 명령으로 만들고 `.drawio` 및 `.png` 산출물을 남기는 장면을 보여 준다. TCP 연결, TLS 협상, 암호화된 데이터 교환, 종료 단계를 한 장의 그림에 담는 사례다. 이 예시는 명령으로 도형과 연결을 구성한 뒤 편집 가능한 원본과 확인용 이미지를 모두 얻는 사용 맥락을 보여 주지만, 데모의 약 4분이라는 수치를 다른 작업의 소요 시간으로 일반화할 수는 없다.

**시각 결과를 여러 번 확인하며 제작하기.** README의 FreeCAD 로버와 Blender 드론 데모는 `preview`, `preview live`, `trajectory.json`을 사용해 작업 단계별 미리보기와 명령 이력을 연결한다. 산출물을 한 번 만든 뒤 끝내는 대신, 현재 장면을 확인하고 수정하며 각 단계의 결과를 추적하는 흐름이다. CLI-Hub의 미리보기 뷰어 문서와 함께 읽으면 생성 명령이 미리보기 상태를 만들고 뷰어가 그 상태를 읽는 역할 분담을 이해할 수 있다. 실제 사용 가능 여부는 선택한 하네스가 해당 명령을 제공하는지 확인해야 한다.

## 6. 참고 자료

- [HKUDS/CLI-Anything 저장소와 README](https://github.com/HKUDS/CLI-Anything) — 두 시작 경로, 아키텍처, 데모와 제약
- [CLI-Hub 사용 문서](https://github.com/HKUDS/CLI-Anything/blob/main/cli-hub/README.md) — 검색·설치·실행, JSON 출력, 미리보기 뷰어
- [하네스 생성 명령 정의](https://raw.githubusercontent.com/HKUDS/CLI-Anything/main/cli-anything-plugin/commands/cli-anything.md) — 소스 인수 조건과 생성·검증 단계
- [CLI-Anything HARNESS 방법론](https://github.com/HKUDS/CLI-Anything/blob/main/cli-anything-plugin/HARNESS.md) — 실제 백엔드 연동과 검증 기준
- [LibreOffice 하네스 사용 문서](https://github.com/HKUDS/CLI-Anything/blob/main/libreoffice/agent-harness/cli_anything/libreoffice/README.md) — 문서·표·슬라이드 명령과 변환 요구사항
- [README의 공식 데모](https://github.com/HKUDS/CLI-Anything#-real-world-demos) — Draw.io, FreeCAD, Blender 사례
