---
layout: post
title: "Repo Deep Dive: GoogleChrome/modern-web-guidance-src — 코딩 에이전트에 최신 웹 플랫폼 사용법을 공급하는 소스"
date: 2026-11-13 07:11:55 +0900
categories: [github-repo-analysis]
repo: GoogleChrome/modern-web-guidance-src
trending_rank: 1
trending_period: daily
trending_checked_at: 2026-11-13 07:10:35 +0900
trending_url: https://github.com/trending?since=daily
---

2026년 11월 13일 07:10 KST에 확인한 GitHub Trending 일간 전체 언어 목록에서 `GoogleChrome/modern-web-guidance-src`가 1위였다. 이는 **저장소 선정 시점의 스냅샷**으로, 발행 또는 열람 시점의 실시간 순위를 뜻하지 않는다. 아래 내용은 저장소 README, Chrome for Developers 공식 문서, 실제 가이드와 CLI 검색 결과를 확인해 작성했다. 가이드를 적용한 웹앱의 성능이나 접근성을 이 글에서 별도로 측정하지는 않았다.

## 1. 프로젝트 소개

Modern Web Guidance는 웹 프런트엔드를 작성하는 AI 코딩 에이전트가 최신 브라우저 기능과 호환성 조건을 찾아 쓰도록 돕는 스킬과 명령줄 도구다. 이번에 선정된 `modern-web-guidance-src`는 사용자가 설치하는 스킬의 **소스 저장소**다. 실제 설치 대상으로 안내되는 `GoogleChrome/modern-web-guidance` 저장소와 구분해야 한다. 소스 저장소에는 가이드 원문, 검색·조회 CLI, 설치용 템플릿, 품질 평가 자료가 들어 있고, 공개 문서는 [Chrome for Developers](https://developer.chrome.com/docs/modern-web-guidance)에서 제공한다.

README는 이 프로젝트를 Google Chrome, Microsoft Edge, Mozilla Firefox, MDN 팀과 웹 개발 커뮤니티가 함께 관리한다고 설명한다. 대상 독자는 새 화면을 만드는 개발자만이 아니다. 오래된 웹앱의 동작은 그대로 두면서 불필요한 자바스크립트 우회 코드나 낡은 브라우저 대응을 검토하려는 팀도 포함된다. 코딩 에이전트에게 작업을 맡길 때 이 스킬을 연결하면, 에이전트가 필요에 맞는 짧은 가이드를 검색하고 원문을 읽은 뒤 코드를 작성하도록 유도한다. 다만 스킬 설치 자체가 코드의 정확성이나 모든 브라우저에서의 동작을 자동으로 보증하는 것은 아니다.

## 2. 해결하려는 문제

기존 코드와 모델 학습 자료에는 오늘날 브라우저가 기본으로 처리할 수 있는 일을 직접 구현한 예제가 많다. 예를 들어 입력할 때마다 `textarea.scrollHeight`를 읽어 높이를 다시 설정하거나, 팝오버를 여는 버튼에 별도의 클릭 리스너를 붙이는 방식이다. 이런 구현이 항상 틀린 것은 아니지만, 새 기능을 만들 때 그대로 복제하면 브라우저 기본 기능, 접근성 처리, 지원 범위를 검토할 기회를 놓치기 쉽다. 반대로 새 API의 이름만 알고 적용했다가 일부 브라우저에서 동작하지 않는 것도 문제다.

이 프로젝트는 요청을 바로 거대한 규칙집으로 바꾸지 않는다. 먼저 `search`로 작업과 관련된 가이드 ID를 찾고, `retrieve`로 해당 구현 예시와 제약, 대체 경로를 확인한다. 기존 코드베이스에서는 `legacy-scan`이 현대화 후보를 찾고, 에이전트가 주변 맥락을 다시 검증하도록 한다. 공식 현대화 문서는 스캐너가 전체 가이드 중 코드에서 높은 확신으로 식별할 수 있는 일부 패턴만 다룬다고 명시한다. 따라서 탐지되지 않은 코드가 곧 최신 구현이라는 뜻은 아니고, 탐지된 항목도 무조건 수정할 대상은 아니다.

## 3. 주요 기능

**가이드 검색과 조회.** `search`의 입력은 “모달 배경을 애니메이션으로 표시하기” 같은 자연어 질의다. 출력은 관련 가이드의 ID와 설명이 담긴 JSON 목록이다. 실제 CLI에서 `animate a dialog modal backdrop`을 검색했을 때 `animate-to-from-top-layer`, `light-dismiss-a-dialog`, `prevent-page-scroll-under-modal-dialog` 등이 반환됐다. 이 단계는 후보를 고르는 일이고, 실제 코드·호환성 주의사항은 `retrieve <id>`에서 읽는다. 예컨대 `animate-to-from-top-layer` 가이드는 `<dialog>`와 팝오버의 등장·퇴장에 `@starting-style`, `transition-behavior: allow-discrete`, `overlay`를 어떻게 조합하는지 설명하며, 모션 감소 설정과 지원이 부족한 브라우저에서의 종료 동작도 별도로 다룬다. 검색 결과만 보고 CSS 한 줄을 복사하는 것과 차이가 있다.

**기존 코드의 후보 탐색.** `legacy-scan <path> --json`은 HTML·CSS·JavaScript/TypeScript 및 관련 컴포넌트에서 정해진 구형 패턴을 찾는다. 공식 현대화 문서에 따르면 스캔은 로컬 파서 기반이며, 결과에는 에이전트가 해당 지점을 유지하거나 제외할지 판단할 조건이 포함된다. 예를 들어 `scrollHeight`가 텍스트 영역 자동 크기 조절이 아니라 다른 레이아웃 계산에 쓰인 경우에는 같은 문자열이라는 이유만으로 바꾸지 않아야 한다. 이 명령에는 자동 수정용 `--fix`가 없다. 출력은 최종 패치가 아니라 검토할 위치와 이유다.

**브라우저 지원 범위와 대체 경로.** 공식 시작 문서는 프로젝트의 Baseline 목표를 에이전트 지침에 적도록 안내하고, 목표가 없으면 기본값을 `Baseline Widely available`로 둔다고 설명한다. 가이드에는 기능별 지원 상태와 필요한 폴백이 실린다. 실험적인 Origin Trial 또는 빠르게 변하는 기능은 검색으로 발견할 수 있어도, 관련 설정에서 명시적으로 허용하기 전에는 `retrieve`가 가이드를 열어 주지 않는다고 README가 설명한다. 따라서 “최신 API 우선”은 “모든 새 API를 무조건 채택”한다는 뜻이 아니다.

**스킬 설치와 평가 자료.** `install`은 에이전트 환경에 맞춰 스킬을 설치하는 대화형 마법사이고, `install --choose`로 일반 웹 플랫폼 가이드와 Chrome 확장 프로그램용 팩을 선택할 수 있다. 소스 저장소는 가이드 원문뿐 아니라 실제 앱을 대상으로 한 과제·채점기와 평가 대시보드도 공개한다. README의 성능 수치는 프로젝트 측 평가 결과이므로 이 글의 독립 재현 결과로 읽어서는 안 된다.

## 4. 사용 방법과 동작 흐름

CLI 소스의 버전 검사 코드는 Node.js 22 이상을 요구한다. 설치 전 기능을 살펴볼 때는 프로젝트를 수정하지 않고 다음 두 명령을 실행할 수 있다.

```bash
npx modern-web-guidance@latest search "animate a dialog modal backdrop"
npx modern-web-guidance@latest retrieve "animate-to-from-top-layer"
```

첫 명령의 JSON 목록에서 현재 작업과 맞는 ID를 선택하고, 둘째 명령으로 그 가이드의 본문을 확인한다. 위 검색은 이 리뷰에서 실제 실행해 후보 ID를 확인했다. 조회한 가이드에는 코드 예시와 함께 `overlay` 전환, 모션 감소, 미지원 브라우저의 종료 처리처럼 구현을 결정할 조건이 있다. 긴 가이드라면 CLI가 출력 잘림을 막기 위해 내용을 임시 파일로 저장하고 위치를 알려줄 수 있으므로, 그 경우 안내된 파일의 전체 내용을 확인해야 한다.

에이전트에 통합할 때는 공식 빠른 시작의 설치 명령을 사용한다.

```bash
npx modern-web-guidance@latest install
```

설치 마법사에서 사용할 에이전트와 적용 대상을 선택한 뒤, 프로젝트에서 요구하는 브라우저 범위를 `AGENTS.md`나 `CLAUDE.md` 같은 에이전트 지침에 명시할 수 있다. 예를 들어 공식 문서는 `This project's Baseline target is Baseline 2024.`라는 문장을 보여 준다. 작업 요청이 들어오면 에이전트는 필요한 가이드를 검색하고, ID로 원문을 조회한 뒤, 예시뿐 아니라 폴백과 제약을 반영해 코드를 작성한다. 최종 결과는 실제 브라우저와 프로젝트 테스트에서 검증해야 한다.

기존 프로젝트를 점검할 때는 `npx modern-web-guidance@latest legacy-scan . --json`으로 후보를 얻을 수 있다. 출력에서 발견된 위치를 주변 코드와 함께 확인하고, 의도된 폴백이나 `@supports` 보호 구문은 제외한다. 그다음 변경 계획을 세우고 필요한 부분만 수정한다. 공식 현대화 문서도 저장소 전체를 한 번에 자동 수정하기보다 스캔·맥락 검증·보고·수정의 순서를 제시한다. CLI의 로컬 검색·조회와 별개로 README는 익명 사용 정보가 수집될 수 있으며 `DISABLE_TELEMETRY=1`로 끌 수 있다고 밝힌다.

## 5. 활용 사례

**모달과 팝오버 현대화.** Chrome 공식 첫 화면은 오래된 모달을 `<dialog>`로 옮기고 최신 CSS로 애니메이션을 추가하는 요청을 예시로 든다. 소스의 `animate-to-from-top-layer` 가이드는 등장 상태뿐 아니라 닫힐 때 요소를 top layer에 유지해야 하는 이유, `::backdrop` 처리와 지원 부족 시의 종료 함수를 설명한다. 별도의 `declarative-dialog-popover-control` 가이드는 `commandfor`·`command` 버튼으로 여닫는 HTML 예시와, 기능 미지원 브라우저에 폴리필을 조건부로 불러오는 방법을 제시한다. 두 가이드는 각각 애니메이션과 선언적 제어를 다루므로 같은 화면에서도 필요한 부분을 구분해 조회할 수 있다.

**기존 폼 코드 점검.** 공식 현대화 문서는 입력 이벤트마다 `scrollHeight`를 읽는 텍스트 영역의 대안으로 `field-sizing: content`와 최소·최대 높이를 제시한다. 이는 스캐너의 후보를 사람이 검토한 뒤 대체할 수 있는 예시이지, 모든 `scrollHeight` 사용을 삭제하라는 지시가 아니다. 같은 문서는 한글·중국어·일본어 입력 도중 Enter가 확정 입력인지 제출인지 혼동하는 리스너에 `isComposing` 등의 검사를 더하는 사례도 보여 준다. 코드를 바꾼 뒤에는 입력 방식과 대상 브라우저에서 실제 동작을 확인해야 한다.

**화면 전환의 비용 검토.** `faster-spa-view-transitions` 가이드는 작은 SPA에서 비활성 뷰에 `content-visibility: hidden`을 적용하고 `inert`, 포커스 이동을 함께 관리하는 예시를 제시한다. 돌아올 화면의 상태를 보존하는 대신 DOM과 이벤트 리스너가 메모리에 남는다는 단점도 명시한다. 따라서 뷰가 계속 생기는 앱에서는 무제한 캐시가 아니라 퇴출 정책이 필요하다. 이처럼 가이드의 적용 조건까지 읽어야 사용 사례를 올바르게 해석할 수 있다.

## 6. 참고 자료

- [선정된 소스 저장소와 README](https://github.com/GoogleChrome/modern-web-guidance-src)
- [사용자 설치용 스킬 저장소](https://github.com/GoogleChrome/modern-web-guidance)
- [Chrome for Developers: 프로젝트 소개](https://developer.chrome.com/docs/modern-web-guidance)
- [Chrome for Developers: 시작하기·검색과 조회·Baseline 설정](https://developer.chrome.com/docs/modern-web-guidance/get-started)
- [Chrome for Developers: 기존 코드 현대화 흐름](https://developer.chrome.com/docs/modern-web-guidance/modernization-workflow)
- [소스 가이드: top layer 애니메이션](https://github.com/GoogleChrome/modern-web-guidance-src/blob/main/guides/ui-behaviors/animate-to-from-top-layer/guide.md)
- [소스 가이드: 선언적 다이얼로그·팝오버 제어](https://github.com/GoogleChrome/modern-web-guidance-src/blob/main/guides/ui-behaviors/declarative-dialog-popover-control/guide.md)
- [소스 가이드: SPA 뷰 상태 보존](https://github.com/GoogleChrome/modern-web-guidance-src/blob/main/guides/performance/faster-spa-view-transitions/guide.md)
