---
layout: post
title: "Repo Deep Dive: sindresorhus/awesome - 자료를 찾고 좋은 목록을 고르는 방법"
date: 2026-04-28 08:07:17 +0900
categories: [github-repo-analysis]
tags: [github, curation, resources, awesome-list, open-source]
repo: sindresorhus/awesome
analyzed_at: 2026-10-16
analyzed_commit: bc98e517ddca672f55f9857d714fc3ea3c3540b2
---

새 기술을 배우거나 도구를 고를 때는 검색어부터 막히기도 한다. 어떤 하위 분야가 있는지 모르고, 검색 결과에 나온 프로젝트들이 서로 같은 문제를 해결하는지도 불분명하기 때문이다. `sindresorhus/awesome`는 이때 출발점으로 삼을 수 있는 주제별 목록의 인덱스다. 개발 도구를 설치하는 프로그램이나 패키지 저장소가 아니라, 여러 사람이 관리하는 자료 목록으로 길을 안내하는 문서다.

이 글은 2026년 10월 16일에 커밋 `bc98e517`의 문서와 실제 링크를 다시 확인해 작성했다. 현재 공식 GitHub 페이지의 운영 공지도 함께 확인했으며, 아래 활용 과정은 문서와 링크를 읽어 설명한 것이다. 소개된 패키지를 설치하거나 기여 요청을 제출하지는 않았다.

## 첫 화면에서는 자료보다 주제를 고른다

중앙 저장소의 입구는 [readme.md](https://github.com/sindresorhus/awesome/blob/bc98e517ddca672f55f9857d714fc3ea3c3540b2/readme.md)다. `Contents`에서 Platforms, Programming Languages, Front-End Development, Back-End Development, Databases, Security, Testing 등으로 이동할 수 있다. Books와 Work, Health and Social Science도 있으므로 개발 라이브러리만 다루는 목록은 아니다. 파일 이름이 비슷한 `awesome.md`는 인덱스가 아니라, 어떤 자료를 고르고 목록을 어떻게 관리해야 하는지 설명하는 선언문이다.

처음부터 모든 항목을 읽을 필요는 없다. 예를 들어 Node.js 서버에서 사용할 HTTP 클라이언트를 찾는다면 Platforms의 Node.js를 따라가면 된다. Python 전반을 살피려면 Programming Languages의 Python, 접근성 자료를 찾으려면 Front-End Development의 Web Accessibility가 출발점이다. 이들은 각각 `sindresorhus/awesome-nodejs`, `vinta/awesome-python`, `brunopulis/awesome-a11y`로 연결된다. 중앙 문서에서 고르는 것은 도구 하나가 아니라, 다음 탐색을 맡길 목록이다.

이 구조를 이해하면 검색 방식도 달라진다. 언어 이름처럼 넓은 단어로 시작한 뒤, 개별 목록의 목차에서 필요한 문제로 좁힐 수 있다. 반대로 이미 문제 이름을 안다면 중앙 README에서 해당 단어를 찾아 관련 목록으로 바로 이동할 수 있다. 특정 주제의 링크가 보이지 않는다고 그 분야의 자료가 없다는 뜻은 아니다. 인접한 분류와 개별 목록의 관련 목록도 살펴볼 여지가 있다.

## 목록 안으로 들어가면 후보가 보인다

[Awesome Node.js](https://github.com/sindresorhus/awesome-nodejs#readme)는 중앙 인덱스와 다른 깊이의 정보를 제공한다. 목차에 Official, Packages, Resources 등이 있고, Packages 아래에는 HTTP, Logging, Testing, Authentication 같은 구체적인 분류가 있다. HTTP 항목에는 `got`, `undici`, `ky-universal` 등의 프로젝트 링크와 짧은 설명이 놓여 있다. 중앙 인덱스의 Node.js 링크를 누른 결과가 여기서 실제 도구 후보로 바뀐다.

HTTP 요청을 보내는 도구가 필요하다는 설명용 상황을 이어 가 보자. 먼저 HTTP 분류를 읽으며 후보 이름과 설명을 파악한다. 그다음 각 후보의 공식 저장소로 이동해 지원하는 Node.js 버전, API 형태, 오류 처리 방식, 현재 유지보수 상태를 확인한다. 목록에서 발견한 설명은 비교의 시작점이고, 실제 채택 근거는 각 프로젝트의 현재 문서와 요구사항에서 얻는다. 이 글은 해당 후보들의 성능이나 우열을 검증한 비교가 아니다.

학습 자료를 찾을 때도 같은 방식이 통한다. 패키지 분류만 보지 않고 Resources의 Tutorials, Articles, Books, Courses 등으로 이동하면 도구를 사용하는 데 필요한 배경 자료를 찾을 수 있다. 하나의 목록 안에서 구현 도구와 학습 자료를 구분해 볼 수 있다는 점이 단순 검색과 다른 탐색 경험을 만든다. 다만 목록마다 목차와 범위가 다르므로 Node.js 목록의 구성이 모든 Awesome 목록에 그대로 적용되는 것은 아니다.

## 위에 있다고 더 좋은 후보는 아니다

[Awesome 선언문](https://github.com/sindresorhus/awesome/blob/bc98e517ddca672f55f9857d714fc3ea3c3540b2/awesome.md)은 많은 항목을 모으기보다 작성자나 기여자가 직접 추천할 수 있는 것을 고르라고 한다. 왜 넣었는지, 독자가 어떤 도움을 받는지도 설명하도록 권한다. 따라서 Awesome의 가치는 망라한 개수보다 선택과 설명에 있다. 모든 프로젝트를 빠짐없이 보여 주는 검색 엔진과는 목표가 다르다.

중앙 문서의 배치 역시 인기순이나 성능순으로 읽으면 안 된다. [등록 요청 규칙](https://github.com/sindresorhus/awesome/blob/bc98e517ddca672f55f9857d714fc3ea3c3540b2/pull_request_template.md)은 새 항목을 적절한 분류의 맨 아래에 추가하도록 요구한다. 이 규칙을 보아도 적어도 중앙 인덱스의 위아래 순서를 품질 점수로 해석할 근거는 없다. 개별 목록에서는 그 목록이 설명한 분류와 정렬 기준을 따로 읽어야 한다.

목록 자체를 평가할 때는 세 가지 질문이 도움이 된다. 내 목적과 범위가 맞는가, 항목 설명만 읽어도 쓰임새를 구분할 수 있는가, 연결된 프로젝트의 현재 상태를 다시 확인할 수 있는가다. 예를 들어 라이브러리 후보가 필요한데 목록이 강의와 기사에 집중한다면 좋은 목록이어도 이번 목적에는 맞지 않는다. 링크가 많아도 설명이 비슷하면 후보를 줄이는 데 도움이 적을 수 있다. 이 질문들은 공식 점수표가 아니라, 선언문의 선별 원칙을 독자의 탐색에 적용한 확인 방법이다.

배지도 등록 여부를 대신 증명하지 않는다. 선언문은 중앙 인덱스에 포함되지 않은 목록과 비공개 목록에도 Awesome 배지를 쓸 수 있다고 명시한다. 따라서 배지가 보이면 목록의 형식과 의도를 짐작할 수는 있지만, 중앙 저장소가 심사해 등재했다는 결론까지 내릴 수는 없다. 목록에 소개된 개별 프로젝트용 `Mentioned in Awesome` 배지도 별도로 정의되어 있다.

## 좋은 링크를 찾았다면 보낼 곳부터 구분한다

기여에는 서로 다른 두 경로가 있다. HTTP 라이브러리 하나를 소개하고 싶다면 해당 자료를 다루는 개별 목록의 규칙을 확인한다. 반면 새로운 주제별 목록을 중앙 인덱스에 연결하려면 `sindresorhus/awesome`의 등록 기준을 따라야 한다. 도구 하나를 중앙 인덱스에 직접 추가하는 방식으로 두 경로를 섞어서는 안 된다.

[기여 안내](https://github.com/sindresorhus/awesome/blob/bc98e517ddca672f55f9857d714fc3ea3c3540b2/contributing.md)는 목록 추가, 자기 목록 생성, 개별 목록에 항목 추가를 나누어 설명한다. 일반적인 항목 제안은 대상 목록의 README를 수정하고 변경 이유를 적어 PR을 제출하는 흐름이다. 대상 저장소의 기여 문서와 행동 강령을 먼저 읽고, 추천 이유와 기존 항목과의 차이를 설명할 수 있어야 한다. 유지관리자의 수정 요청에 대응하는 과정도 기여의 일부다.

다만 절차가 문서에 있다고 지금 접수할 수 있다는 뜻은 아니다. 검토 시점의 [중앙 저장소 공식 페이지](https://github.com/sindresorhus/awesome)는 기존 요청을 처리하기 위해 PR을 일시 중단했다고 안내하며, 협업자만 PR을 만들 수 있는 상태를 표시한다. Awesome Node.js에도 제출 일시 중단 공지가 있다. 실제 기여 전에는 해당 저장소의 현재 공지를 다시 확인해야 한다. 아래 생성 기준은 준비할 내용을 이해하기 위한 것이며, 현재 제출이 가능하다는 안내가 아니다.

## 새 목록을 만드는 일은 링크 수집보다 먼저 시작된다

자기 분야의 목록이 필요하다면 먼저 같은 주제를 다루는 기존 목록을 찾는다. [목록 생성 안내](https://github.com/sindresorhus/awesome/blob/bc98e517ddca672f55f9857d714fc3ea3c3540b2/create-list.md)는 중복이라면 새로 만들기보다 가장 좋은 기존 목록에 기여해 보라고 권한다. 새 목록을 유지하려면 범위를 정하고, 후보를 조사하고, 설명을 고치고, 오래된 항목을 재검토해야 한다. 이미 그 일을 하는 곳이 있다면 거기에 지식을 보태는 선택이 가능하다.

새 목록이 필요한 경우에는 어떤 독자에게 어떤 주제를 다루는지 짧게 정의한다. 선언문은 범위를 벗어나는 내용을 늘리기보다 이미 잘 다루는 다른 목록으로 연결하라고 한다. 그다음 직접 추천할 수 있는 후보를 추리고, 각 항목의 쓰임새를 설명하며, 탐색하기 쉬운 목차로 묶는다. 모든 것을 넣으려는 시도보다 무엇을 포함하지 않을지 결정하는 일이 중요하다.

중앙 등록을 목표로 한다면 작성 초기에 [전체 체크리스트](https://github.com/sindresorhus/awesome/blob/bc98e517ddca672f55f9857d714fc3ea3c3540b2/pull_request_template.md)를 읽는 편이 낫다. 자동 생성하지 않은 Markdown 문서, `main` 기본 브랜치, 소문자 `awesome-name-of-list` 저장소 이름, `awesome`과 `awesome-list` 토픽, `Contents` 목차와 기여 문서 등을 요구한다. 목록은 AI로 생성한 것이어서는 안 되며, 전적으로 AI가 생성한 PR도 받지 않는다고 명시한다.

내용 기준도 있다. 관리되지 않거나 보관 처리된 프로젝트, 폐기된 항목, 문서가 없는 항목은 본 목록에 넣지 말고 꼭 필요할 때 별도 Markdown 파일로 분리하도록 한다. 라이선스는 Creative Commons 계열을 요구하며 CC0를 강하게 권장한다. 중앙 저장소 자체의 [license](https://github.com/sindresorhus/awesome/blob/bc98e517ddca672f55f9857d714fc3ea3c3540b2/license)도 CC0 1.0이다. 목록 문서의 라이선스를 확인한 것과 연결된 소프트웨어의 라이선스를 확인한 것은 별개이므로, 도구를 채택할 때는 해당 프로젝트에서 다시 살펴야 한다.

생성 직후 등록하는 것도 허용하지 않는다. 체크리스트는 첫 실질적인 커밋과 공개 시점 중 더 최근 시점으로부터 최소 30일이 지나야 한다고 설명한다. PR을 준비할 때는 다른 열린 PR 최소 4건에 실질적인 검토를 수행하는 요구도 있다. 단순 승인이나 형식 검사 지적만으로는 그 검토를 채운 것으로 보지 않는다. 이는 이름과 배지만 맞추면 끝나는 등록 절차가 아니라, 자신의 목록과 다른 사람의 목록 품질을 함께 검토하는 참여 방식이다.

## 자동 검사를 통과해도 판단은 남는다

자동화가 담당하는 범위도 구분해야 한다. [워크플로](https://github.com/sindresorhus/awesome/blob/bc98e517ddca672f55f9857d714fc3ea3c3540b2/.github/workflows/main.yml)는 `main` 대상 PR 중 `readme.md` 변경에 반응한다. 호출하는 [repo_linter.sh](https://github.com/sindresorhus/awesome/blob/bc98e517ddca672f55f9857d714fc3ea3c3540b2/.github/workflows/repo_linter.sh)는 `origin/main`과의 차이에서 추가된 `https...#readme` 링크를 추출하고, 찾은 저장소를 복제한 뒤 `npx awesome-lint`를 실행한다. 대상 링크를 찾지 못하면 안내를 출력한다.

따라서 이 코드만 보고 중앙 인덱스의 모든 링크를 주기적으로 점검한다거나, 추천된 도구의 보안과 성능까지 자동 검증한다고 설명할 수는 없다. 후보 목록에 대한 형식 검사는 도움을 주지만, 자료가 주제에 맞는지와 실제로 추천할 만한지는 조사와 검토가 필요하다. 독자는 중앙 인덱스에서 주제를 고르고, 개별 목록에서 후보를 좁히고, 후보의 공식 문서에서 현재 조건을 확인하는 순서로 활용할 수 있다. 그 과정에서 얻은 지식을 적절한 목록에 보태면 다음 독자의 탐색도 더 구체적이 된다.

## 참고 자료

- [주제별 중앙 인덱스](https://github.com/sindresorhus/awesome/blob/bc98e517ddca672f55f9857d714fc3ea3c3540b2/readme.md)
- [Awesome 선언문](https://github.com/sindresorhus/awesome/blob/bc98e517ddca672f55f9857d714fc3ea3c3540b2/awesome.md)
- [기여 안내](https://github.com/sindresorhus/awesome/blob/bc98e517ddca672f55f9857d714fc3ea3c3540b2/contributing.md), [새 목록 생성 안내](https://github.com/sindresorhus/awesome/blob/bc98e517ddca672f55f9857d714fc3ea3c3540b2/create-list.md), [등록 체크리스트](https://github.com/sindresorhus/awesome/blob/bc98e517ddca672f55f9857d714fc3ea3c3540b2/pull_request_template.md)
- [탐색 예시로 확인한 Awesome Node.js](https://github.com/sindresorhus/awesome-nodejs#readme)
