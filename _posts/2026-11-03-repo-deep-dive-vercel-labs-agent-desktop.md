---
layout: post
title: "Repo Deep Dive: vercel-labs/agent-desktop — 접근성 트리로 데스크톱을 조작하는 CLI"
date: 2026-11-03 07:10:33 +0900
categories: [github-repo-analysis]
repo: vercel-labs/agent-desktop
trending_rank: 1
trending_period: daily
trending_checked_at: 2026-11-03 07:10:33 +0900
trending_url: https://github.com/trending?since=daily
---

2026년 11월 3일 07:10 KST에 확인한 GitHub Trending 일간 전체 언어 목록에서 `vercel-labs/agent-desktop`가 1위였다. 이 순위는 **저장소 선정 시점의 스냅샷**이며 게시 또는 열람 시점의 실시간 순위를 뜻하지 않는다.

## 1. 프로젝트 소개

`agent-desktop`은 AI 에이전트가 데스크톱 앱의 화면 요소를 읽고 조작할 수 있도록 만든 명령줄 도구와 C 라이브러리다. 현재 저장소는 Vercel Labs 조직에 있으며, 공식 README는 macOS·Windows·Linux의 운영체제 접근성 트리를 공통 입력으로 삼는다고 설명한다. 브라우저 안의 웹페이지뿐 아니라 파일 관리자, 메모 앱, 운영체제 창처럼 데스크톱에 떠 있는 대상을 자동화하려는 상황이 사용 범위다. 다만 이 도구 자체가 목표를 해석하고 다음 행동을 계획하는 에이전트는 아니다. 무엇을 읽고 어떤 요소를 누를지 결정하며 결과를 다시 확인하는 반복은 도구를 호출하는 에이전트나 프로그램이 담당한다.

명령마다 별도의 프로세스가 실행되고 JSON 응답 하나를 출력한다. 프로그램에서 명령을 반복 실행하는 방식 외에, 릴리스에 포함된 C ABI 라이브러리를 프로세스 안으로 불러오는 경로도 제공한다. README의 Python `ctypes` 예시는 라이브러리 초기화와 어댑터 생성·해제까지만 보여주므로, 그것만으로 화면 조작 전체가 가능한 완성 예제로 오해해서는 안 된다. 기본 사용 경로는 CLI의 `snapshot → action → snapshot`이다.

## 2. 해결하려는 문제

스크린샷만 보고 버튼 위치를 추정해 좌표를 누르는 자동화는 창 크기나 배치가 달라지면 목표를 다시 찾아야 한다. 또 같은 이름의 버튼이 여러 개 있을 때 단순 문자열 검색이나 좌표 추정만으로는 어느 버튼을 지칭하는지 모호하다. `agent-desktop`은 접근성 API가 제공하는 역할, 이름, 상태와 계층을 스냅샷으로 내보내고 조작 가능한 요소마다 `@s8f3k2p9:e8` 같은 참조를 붙인다. 호출자는 이 참조를 다음 명령의 대상으로 사용한다. 따라서 기본 흐름은 픽셀 일치 검사 없이 UI의 의미적 구조를 읽는 방식이다. 스크린샷 명령도 있지만 핵심 조작 경로에 필수는 아니다.

참조가 좌표보다 영구적으로 안정적이라는 뜻은 아니다. 공식 문서는 참조가 특정 스냅샷에 속하며, UI가 바뀌었거나 대상 식별이 확실하지 않으면 `STALE_REF` 또는 `AMBIGUOUS_TARGET`을 반환한다고 명시한다. 여러 창이 후보가 되는 경우에는 창 ID를 지정해야 한다. 도구의 특징은 모든 클릭을 성공시키는 데 있지 않고, 불확실한 대상을 무작정 누르지 않도록 실패 사유와 다음 관찰 경로를 구조화한다는 데 있다.

## 3. 주요 기능

**관찰과 대상 선택.** `snapshot --app Finder -i`는 지정 앱의 창을 읽어 `window`, `snapshot_id`, `ref_count`, `complete`, 요소 트리를 포함한 JSON을 출력한다. `-i`는 상호작용 가능한 요소를 중심으로 결과를 좁힌다. 큰 앱에서는 `--skeleton`으로 얕은 구조를 먼저 확인하고, 관심 영역의 참조를 `--root`에 전달해 그 부분을 펼칠 수 있다. 반대로 정확한 역할이나 이름을 이미 알 때는 `find`로 검색하고, 상태 확인에는 `get`·`is`를 쓴다. 스냅샷의 `complete: false`는 제한 시간 안에 트리를 전부 읽지 못했다는 의미이므로 누락된 부분이 없다고 판단하면 안 된다.

**참조 기반 조작.** `click`, `type`, `set-value`, `select`, `toggle`, `scroll` 등은 관찰한 요소의 참조를 받아 동작을 시도한다. 기본 참조 동작은 접근성 API를 사용하는 headless 방식이며 포인터 이동이나 전경 창 전환, 물리적 키 입력을 하지 않는다. 물리적 입력이 필요한 동작은 별도의 `--headed` 경로로 구분된다. 공식 플랫폼 표에 따르면 Linux Wayland의 앱 포인터 입력과 네이티브 창 제어에는 제약이 있으므로, 세 운영체제를 기능까지 완전히 동일하게 지원한다고 해석해서는 안 된다.

**결과와 오류의 구분.** 모든 명령은 `ok`와 `data` 또는 `error`를 담은 JSON 봉투를 출력한다. 오류에는 `code`와 재시도 여부를 판단할 `disposition`이 들어간다. 예컨대 `STALE_REF`가 나면 새 스냅샷으로 참조를 갱신한다. 반면 클릭이 이미 전달됐을 가능성이 있는 결과는 똑같이 다시 누르지 말고 실제 UI 상태를 재관찰해야 한다. 문서의 `delivered_unverified`는 명령이 전달됐다는 보고이지 앱 안의 업무 처리가 완료됐다는 증명이 아니다. 상태를 바꾸는 자동화에서 이 차이가 특히 중요하다.

**데스크톱 주변 작업.** README에는 앱·창 나열과 실행, 알림 조회·해제, 클립보드, 대기, 세션, 트레이스 기능도 나열되어 있다. 여러 창이 열려 모호한 경우 `snapshot` 오류의 후보 창 ID를 읽고 `--window-id`로 대상을 지정하는 식으로 관찰 범위를 좁힌다. 문서상 60개 명령 이름 중 네 개의 키·마우스 누름 유지 명령은 해제 가능한 데몬이 마련될 때까지 실행을 거부한다. 따라서 명령 목록에 있다는 이유만으로 모두 사용 가능한 것은 아니다.

## 4. 사용 방법과 동작 흐름

공식 설치 문서는 npm 전역 설치와 버전 확인을 출발점으로 제시한다. npm 패키지에는 x64·ARM64용 네이티브 실행 파일과 플랫폼 보조 파일이 포함된다. 설치 전에 자신의 환경이 그래픽 데스크톱 세션인지 확인해야 한다. macOS는 접근성 권한이 필요하고 스크린샷에는 화면 기록 권한이 추가로 필요하다. Windows는 터미널과 같은 무결성 수준의 앱에는 별도 권한 허용이 필요 없지만 관리자 권한 앱에 입력하려면 실행 주체도 권한이 높아야 한다. Linux는 사용자 그래픽 세션과 `at-spi2-core`가 필요하며, 단순 SSH·TTY에서는 그 세션의 앱이 보이지 않을 수 있다.

```bash
npm install -g agent-desktop
agent-desktop version
agent-desktop status
agent-desktop list-apps
```

실제 조작은 관찰 결과에서 참조를 읽은 뒤 시작한다. 아래 Finder는 macOS 예시이며, 다른 운영체제에서는 `list-apps`에 나온 앱 이름을 사용한다. `@s8f3k2p9:e8`은 README에 실린 예시 참조일 뿐이다. 실제 실행에서는 첫 스냅샷의 `tree`에서 원하는 요소의 `ref_id`와 `available_actions`를 확인해 해당 값을 넣어야 한다. 클릭 후 다시 스냅샷을 찍어 창 제목이나 요소 상태가 기대대로 바뀌었는지 확인한다.

```bash
agent-desktop snapshot --app Finder -i
agent-desktop click @s8f3k2p9:e8
agent-desktop snapshot --app Finder -i
```

예시 JSON에서 `ok: true`와 `command: snapshot`은 관찰 명령이 실행됐다는 뜻이며, `data.window.title`은 읽은 창, `data.snapshot_id`는 참조가 속한 스냅샷, `data.complete`는 트리 읽기의 완전성을 나타낸다. `children` 아래 요소의 `role`, `name`, `available_actions`와 `ref_id`를 함께 보고 대상을 정해야 한다. `@e8`처럼 스냅샷 ID를 뺀 참조는 유효하지 않다. PowerShell에서는 `@`가 다른 문법으로 해석되므로 참조를 작은따옴표로 감싼다. 앱에 창이 여러 개라면 오류의 후보를 읽고 창 ID를 지정한 새 스냅샷에서 시작한다.

## 5. 활용 사례

**파일 관리자 작업을 검증하는 에이전트.** README의 Finder 예시처럼 다운로드 창에서 항목의 역할과 이름을 확인해 참조로 클릭하고 다시 관찰할 수 있다. 이 흐름은 에이전트가 이미 어떤 항목을 열지 결정했다는 전제에서만 의미가 있다. 클릭 응답만 보고 파일이 열렸다고 결론내리는 대신, 후속 스냅샷의 창 제목이나 트리 변화를 읽어 목표 상태를 확인한다.

**요소가 많은 업무 앱 탐색.** 공식 빠른 시작은 Slack 같은 밀집된 앱에서 `snapshot --skeleton --app Slack -i --compact`로 큰 영역을 지도처럼 본 뒤, 관심 영역에 `--root`를 적용하는 예시를 제시한다. 모든 요소를 처음부터 긴 JSON으로 받아 처리하는 대신 필요한 하위 영역을 확장한다. 다만 트리가 일부만 읽힌 경우의 `complete`와 참조 식별 가능성은 함께 점검해야 한다.

**기존 프로그램에 데스크톱 관찰을 연결하기.** CLI의 JSON 봉투를 파싱하는 프로그램은 `ok`, 오류 코드, `disposition.retry`에 따라 새 스냅샷을 얻을지 결정할 수 있다. 프로세스 실행 오버헤드를 줄이고 싶은 호스트 프로그램에는 릴리스의 C 라이브러리 경로가 문서화되어 있다. 두 경로 모두 UI의 최종 상태 확인을 호출자에게 남긴다. 또한 스냅샷·창 제목·클립보드·스크린샷·트레이스에는 사용자의 데스크톱 내용이 포함될 수 있으므로, 공식 FAQ가 안내하듯 이 결과를 공개 로그에 무심코 남겨서는 안 된다.

## 6. 참고 자료

- [vercel-labs/agent-desktop 저장소](https://github.com/vercel-labs/agent-desktop)
- [공식 README — 빠른 시작과 명령·플랫폼 표](https://github.com/vercel-labs/agent-desktop/blob/main/README.md)
- [설치 및 플랫폼별 권한 문서](https://github.com/vercel-labs/agent-desktop/blob/main/docs/install.md)
- [JSON 응답·오류 계약 문서](https://github.com/vercel-labs/agent-desktop/blob/main/docs/json-output.md)
- [공식 FAQ — 참조와 개인정보를 담는 출력](https://github.com/vercel-labs/agent-desktop/blob/main/docs/faq.md)
- [에이전트 사용 예시](https://github.com/vercel-labs/agent-desktop/blob/main/skills/agent-desktop/SKILL.md)
- [v1.0.2 릴리스](https://github.com/vercel-labs/agent-desktop/releases/tag/v1.0.2)
