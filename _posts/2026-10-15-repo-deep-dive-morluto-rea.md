---
layout: post
title: "Repo Deep Dive: morluto/rea — 실행 파일과 앱의 동작을 증거로 추적하는 도구"
date: 2026-10-15 09:29:17 +0900
categories: [github-repo-analysis]
tags: [github, reverse-engineering, mcp, electron, binary]
repo: morluto/rea
stars: 241575
analyzed_at: 2026-10-15
trending_rank: 1
trending_period: daily
trending_checked_at: 2026-10-15 19:18:56 +0900
trending_url: https://github.com/trending?since=daily
---

2026년 10월 15일 19:18 KST에 확인한 GitHub Trending 일간 전체 언어 목록에서 `morluto/rea`는 1위였다. 이 순위는 **선정 시점의 스냅샷**이며 발행 후에도 유지된다는 뜻은 아니다. 이 글은 저장소 README와 공식 문서를 바탕으로 REA가 무엇을 조사하고, 결과를 어떻게 활용하는지 살펴본다.

## 1. 프로젝트 소개

REA(Reverse Engineer Anything)는 소스 코드가 없는 애플리케이션이나 실행 파일을 조사할 때 AI 에이전트가 사용할 수 있는 **MCP 서버와 CLI**다. 사용자가 “이 앱의 검색 기능은 어떻게 작동하나?”처럼 질문하면, 에이전트는 REA의 도구로 대상의 코드·파일·실행 흔적을 살펴보고 근거와 한계를 함께 받는다. 같은 조사 도구를 터미널에서도 사용할 수 있다.

조사 범위는 네이티브 바이너리뿐 아니라 JavaScript/Electron 앱, 웹사이트, .NET 어셈블리, Android APK, 저장된 네트워크 캡처 등으로 넓다. 다만 **모든 대상에 동일한 수준의 분석이 가능한 것은 아니다.** 네이티브 의사코드 추출에는 Hopper·Ghidra·IDA 중 하나가 필요하고, 정적 JavaScript 분석에는 이런 네이티브 엔진이 필요하지 않다. 브라우저 관찰에는 Chrome 계열 브라우저가, APK 분석에는 JADX와 JDK가 필요하다. 따라서 “무엇이든”이라는 이름은 단일 명령으로 모든 플랫폼을 완벽하게 복원한다는 의미가 아니다.

## 2. 해결하려는 문제

다른 앱에서 본 기능을 이해하려면 보통 파일 포맷 확인, 역컴파일, JavaScript 모듈 탐색, 브라우저 네트워크 관찰을 각각 다른 도구로 수행해야 한다. 얻은 결과를 한데 모아 “어느 코드와 관찰이 이 결론을 뒷받침하는가”를 정리하는 일도 별도 작업이다. REA는 이 조사 단계를 에이전트가 호출할 수 있는 인터페이스로 연결한다.

핵심은 **질문 → 조사 → 증거 확인 → 추가 질문**의 반복이다. 에이전트가 대상의 관련 부분을 찾고, REA가 의사코드·어셈블리·모듈 관계·네트워크 관찰 같은 자료를 반환한다. 에이전트는 그 자료를 근거로 설명하거나 구현을 시도할 수 있다. REA 자체가 원본 제품의 전체 소스 코드를 복구하거나, 분석 결과를 검증 없이 완성된 코드로 보장하는 것은 아니다. 특히 정적 파일 조사와 실제 프로그램을 실행·조작하는 런타임 관찰은 효과와 전제 조건이 다르다.

## 3. 주요 기능

**네이티브 프로그램 조사.** 지원 분석 엔진을 연결하면 함수의 의사코드와 어셈블리, 문자열, 심볼, 호출 관계, 참조를 살펴볼 수 있다. 특정 기능의 진입점에서 관련 함수로 내려가며 가설을 좁히는 식이다. 바이너리 형식과 호스트 운영체제에 따라 사용할 수 있는 엔진과 결과가 다르므로 대상에 맞는 provider를 먼저 골라야 한다.

**JavaScript·Electron 앱 조사.** 추출된 앱 디렉터리 또는 ASAR를 입력하면 모듈·import·source map·라우트·IPC·네이티브 애드온의 연결 정보를 얻는다. 예컨대 화면 기능이 renderer의 API에서 preload를 거쳐 main process의 IPC 처리로 이어지는지 추적할 수 있다. 정적 분석은 공급된 파일을 읽는 방식으로, 분석 대상 앱을 실행해야만 하는 것은 아니다.

**웹과 다른 아티팩트 조사.** Chrome 계열 브라우저를 통한 페이지 구조, 스크립트와 네트워크 관찰, 요청한 스크린샷을 다룬다. .NET은 메타데이터와 CIL 명령을 정적으로 읽고, Android APK는 manifest·클래스·디컴파일된 메서드와 참조를 살핀다. HAR/SAZ 같은 저장된 네트워크 캡처와 SQLite 데이터베이스, WASM 등도 각기 다른 요구 도구와 범위로 지원한다. 이 기능들은 하나의 만능 파서가 아니라 대상별 조사 도구 묶음으로 이해하는 편이 정확하다.

**근거와 한계 표시.** README는 분석 결과에 결론의 근거와 한계를 포함한다고 설명한다. 따라서 결과를 읽을 때 “무엇을 실제로 관찰했는가”, “어떤 부분은 추론인가”, “추가 검증이 필요한가”를 분리할 수 있다. 에이전트가 이 자료로 코드를 작성하더라도 재현 테스트는 별도로 필요하다.

## 4. 사용 방법과 동작 흐름

README의 기본 요구사항은 Node.js 22.x(22.19 이상), 24.x(24.11 이상) 또는 26 이상과 npm이다. 에이전트에 연결하려면 `npx rea-agents setup`을 실행하고 지원 에이전트를 선택한다. 설정이 제안하는 MCP 등록과 워크플로 지침을 검토·승인한 뒤 에이전트를 재시작한다. README에는 Claude Code, Codex, Cursor, Gemini CLI 등이 지원 대상으로 나와 있다.

설치 후에는 예를 들어 “Notes 앱 검색이 어떻게 동작하는지 근거를 보여주고 비슷한 기능을 만들어줘”라고 요청할 수 있다. 에이전트가 REA를 호출해 관련 부분을 조사하고 반환된 증거를 바탕으로 설명과 후속 작업을 수행한다. 분석 도구만 먼저 확인하고 싶다면 추출된 JavaScript/Electron 앱에 대해 `npx -y rea-agents@latest analyze-javascript-application /absolute/path/to/app --json`을 사용할 수 있다. 이 결과에는 모듈·import·Electron 경계와 근거가 포함된다.

네이티브 대상을 다룰 때는 먼저 Hopper·Ghidra·IDA 같은 provider를 준비해야 한다. JavaScript 정적 조사처럼 별도 네이티브 엔진이 필요 없는 경로와 혼동하면 안 된다. 또 REA는 대상을 로컬에서 분석하지만 **에이전트가 받은 조사 결과는 사용 중인 모델 제공자의 데이터 정책을 따른다.** 실행 관찰 기능은 사용자 권한으로 대상을 실행하거나 조작할 수 있으므로 정적 읽기와 구분해 사용해야 한다.

## 5. 실제 활용 사례

공식 쇼케이스의 **DX-Ball** 사례는 사운드 호출에서 위치별 패닝 계산 함수를 따라가며 불완전한 의사코드를 C로 재구성한다. 이 사례에서는 원본 x86 테스트 3,205건과 컴파일된 함수 바이트 63개를 비교했다고 설명한다. 단순히 “비슷해 보인다”가 아니라 원본 동작과 산출물을 대조한 예다.

**Notion** 사례는 Electron의 renderer에서 클립보드 API를 찾고 preload·IPC를 지나 main process로 이어지는 경로를 추적한다. 화면에서 보이는 복사/붙여넣기 동작이 어떤 프로세스 경계를 거치는지 알고 싶을 때 적합한 조사 방식이다. **TH04** 사례는 PC-98 게임의 16비트 명령에서 탄환 각도 계산을 복원하고 재구성한 C++ 결과를 당시 컴파일러 출력과 비교한다. 세 사례 모두 “기능 설명”에서 멈추지 않고 실제 근거와 재현 가능한 비교 대상으로 내려가는 REA의 사용법을 보여준다.

## 6. 참고 자료

- [REA GitHub 저장소](https://github.com/morluto/rea) 및 [README](https://github.com/morluto/rea#readme)
- [설치와 provider 준비](https://github.com/morluto/rea/blob/main/docs/installation.md)
- [CLI와 Evidence 안내](https://github.com/morluto/rea/blob/main/docs/cli.md)
- [분석 대상과 필요 도구](https://github.com/morluto/rea#what-you-can-analyze)
- [공식 쇼케이스](https://rea.tools/showcase/): [DX-Ball](https://rea.tools/showcase/dx-ball/), [Notion](https://rea.tools/showcase/notion/), [TH04](https://rea.tools/showcase/th04/)
