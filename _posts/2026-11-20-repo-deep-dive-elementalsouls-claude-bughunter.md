---
layout: post
title: "Repo Deep Dive: elementalsouls/Claude-BugHunter — 보안 점검 과정을 기술·검증·보고로 잇는 스킬 묶음"
date: 2026-11-20 07:12:54 +0900
categories: [github-repo-analysis]
repo: elementalsouls/Claude-BugHunter
trending_rank: 1
trending_period: daily
trending_checked_at: 2026-11-20 07:10:40 +0900
trending_url: https://github.com/trending?since=daily
---

2026년 11월 20일 07:10 KST에 확인한 GitHub Trending 일간 전체 언어 목록에서 `elementalsouls/Claude-BugHunter`가 1위였다. **이는 저장소를 선정한 시점의 순위 스냅샷이며, 발행 시점이나 이 글을 읽는 시점의 실시간 순위가 아니다.** 아래 내용은 저장소의 README를 설치·사용 안내, CLI 안내, 실제 명령 정의와 대조한 것이다. 저장소가 기록한 검증 사례는 공개 문서로 확인했지만, 이 글을 위해 취약점 탐지율이나 현장 성능을 별도로 측정하지는 않았다.

## 1. 프로젝트 소개

Claude-BugHunter는 Sachin Sharma가 공개한 Claude Code용 버그 바운티·외부 레드팀 점검 스킬 묶음이다. 일반적인 단일 보안 프롬프트가 아니라, 조사 방법론, 취약점 유형별 판단 자료, 증거 정리, 보고 단계의 지침을 각각 필요할 때 불러 쓰도록 구성한 프로젝트다. 현재 README와 플러그인 메타데이터는 83개 스킬과 15개 슬래시 명령을 안내한다. 저장소 설명에는 공개된 버그 바운티 보고서에서 정리한 681개 패턴과 기업용 인증·외부 인프라 점검 자료가 포함됐다고 적혀 있다. 이 숫자는 저장소의 자체 집계이지 독립적인 품질 보증 지표는 아니다.

대상 독자는 자신이 소유한 시스템, 명시적으로 범위에 포함된 버그 바운티 자산, 계약으로 허가받은 시스템 또는 훈련 환경을 점검하는 연구자다. README와 `SECURITY.md`는 외부에서 접근 가능한 공격 표면을 범위로 정하고, 내부 Active Directory 침투나 침투 후 지속성·횡적 이동은 다루지 않는다고 명시한다. 따라서 이 묶음은 대상을 자동으로 안전하게 검사해 주는 서비스가 아니라, 허가된 점검에서 사람이 판단하고 사용하는 작업 지침과 보조 도구에 가깝다.

## 2. 해결하려는 문제

보안 점검에서 URL과 응답을 모으는 일, 의심스러운 동작을 실제 취약점으로 검증하는 일, 프로그램 규정에 맞는 보고서를 쓰는 일은 서로 다른 작업이다. 단편적인 페이로드 목록만 있으면 무엇을 먼저 확인할지 알기 어렵고, 일반적인 대화형 답변만 있으면 특정 취약점 유형의 확인 조건이나 반례가 누락되기 쉽다. 저장소의 사용 안내는 점검을 범위 확인, 정찰, 유형별 조사, 검증, 증거 수집, 보고의 흐름으로 설명한다. 각 단계에 대응하는 스킬을 불러와 앞 단계에서 얻은 자료를 다음 판단에 사용하게 하는 것이 이 프로젝트의 접근 방식이다.

특히 '응답 코드가 200이었다'는 관찰과 '타인의 데이터에 접근할 수 있다'는 검증된 영향은 다르다. `triage-validation`의 7개 질문에는 실제 재현 요청, 프로그램이 인정하는 영향, 대상의 범위, 접근 전제, 이미 알려진 동작 여부, 입증된 영향, 제출하면 안 되는 유형이 포함된다. `/triage` 명령은 의심 사례를 보고서로 옮기기 전에 이 질문을 적용하고, `/validate`는 더 자세한 제출 전 점검으로 이어진다. 문서에 적힌 게이트가 있다고 해서 모델이 항상 정확하게 판단하거나 실제 허가 범위를 자동으로 알아낸다는 뜻은 아니다. 범위 문서와 원본 요청·응답을 확인할 책임은 여전히 사용자에게 있다.

## 3. 주요 기능

**주제별 스킬과 대화 명령.** README는 웹 애플리케이션 취약점 유형을 다루는 `hunt-*` 스킬과 정찰, 기업 외부 서비스, 보고·검증 스킬을 구분한다. 사용자가 Claude Code에서 대상과 조사 상황을 설명하면 해당 주제의 스킬을 불러오는 사용법을 제시한다. 반면 `/hunt`, `/recon`, `/triage`, `/report` 같은 명령은 작업의 단계가 분명할 때 호출하는 인터페이스다. 실제 `commands/hunt.md`를 보면 `/hunt`는 대상 표기를 해석하고 점검 모드를 고른 뒤, 범위 확인·정찰·검증 명령으로 연결한다. 스킬이 지식을 제공하는 것과 슬래시 명령이 순서를 안내하는 것은 역할이 다르다.

**대상별 작업 공간과 범위 자료.** 복제 설치에 포함된 `hunt <대상이름>` 셸 함수는 대상별 작업 폴더를 만들고 `CLAUDE.md`, `scope.md`, `findings/`, `evidence/`, `notes.md` 등 점검 자료의 자리를 마련한다. `scope.md`에는 허용 자산과 제외 자산, 허용된 영향, 점검 규칙을 사용자가 채워야 한다. 스캐폴더가 폴더를 생성한다고 허가가 입증되는 것은 아니며, 실제 범위 검토 전에 활성 테스트를 시작해서는 안 된다. 플러그인 설치는 스킬과 명령을 제공하지만 이 `hunt` 함수는 복제 설치 쪽에 포함된다는 점도 README의 설치 비교표에서 구분한다.

**독립 실행 CLI.** `cbh`는 Claude Code 대화 밖에서 쓰는 별도 Python 실행기다. `recon`은 인증서 투명성 자료와 선택적인 `subfinder` 결과를 모아 DNS·HTTP 확인 결과와 정찰 요약을 남긴다. `surface`는 생성된 매니페스트를 읽어 우선순위별 표면을 보여 주고, `classify`는 URL 형태와 스킬 설명 키워드를 대조해 살펴볼 `hunt-*` 자료를 제안한다. `triage`는 발견 내용 마크다운을 7개 질문의 신호와 비교하며, `report`는 입력한 사실을 기반으로 플랫폼별 보고서 초안을 만든다. `docs/cbh-cli.md`에 따르면 빠진 내용은 `(fill in)`으로 남기므로 완성된 제출물로 간주할 수 없다. 실제 `python3 scripts/cbh.py --help`에서도 이 다섯 하위 명령을 확인했다. CLI는 결정적 라우팅·초안 도구이지 모델이 수행하는 대화형 판단이나 실제 취약점 검증을 대체하지 않는다.

**검증과 증거 관리.** `/triage`의 빠른 판단 뒤 `/validate`로 넘어가는 절차와, 증거를 남기기 전에 `evidence-hygiene` 스킬로 쿠키·개인정보·HAR 내용을 검토하는 절차가 문서화돼 있다. 이는 발견을 무조건 보고하도록 밀어붙이는 기능과 다르다. 공개된 OWASP Juice Shop 검증 기록에는 일부 시나리오의 실제 HTTP 확인 결과와 소스 확인 결과가 서로 구분돼 있다. 그 기록은 특정 훈련 환경에서 수행한 사례이지, 83개 스킬 전부의 효과나 다른 시스템에서의 성공률을 증명하지는 않는다.

## 4. 사용 방법과 동작 흐름

Claude Code에서 쓰려면 설치 안내에 따라 Claude Code와 사용 가능한 계정 또는 API 접근이 필요하다. 가장 간단한 설치 경로는 Claude Code 안에서 다음 두 명령으로 저장소의 플러그인 마켓플레이스를 추가하고 플러그인을 설치하는 것이다.

```text
/plugin marketplace add elementalsouls/Claude-BugHunter
/plugin install claude-bughunter@elementalsouls
```

이 경로는 이름공간이 붙은 스킬과 슬래시 명령을 제공한다. 별도 `cbh` 실행기와 `hunt` 셸 함수가 자동으로 생기지는 않는다. 대상별 폴더 생성까지 쓰려면 저장소를 복제한 뒤 macOS·Linux에서는 `bash scripts/install.sh`, Windows에서는 `pwsh ./scripts/install.ps1`을 실행하는 경로가 README와 `INSTALL.md`에 있다. 설치 스크립트는 사용자 설정과 에이전트의 스킬 경로를 변경하므로 실행 전 내용을 확인하고, 필요하면 검토한 태그 또는 커밋에 고정하는 것이 저장소의 보안 안내와도 맞다. HackerOne API 자격 정보는 선택 사항이며, 공개 자료만 쓰는 데 필수는 아니다.

예를 들어 허가된 훈련 대상을 준비했다면 복제 설치 후 `hunt training-lab`으로 대상별 작업 공간을 만들고, 그곳의 `scope.md`에 허용 범위를 먼저 기록한다. 이후 Claude Code에서 `/recon`으로 자산 정보를 정리하고, 조사할 표면을 고른 뒤 관련 `hunt-*` 스킬을 참조한다. 의심 사례가 생기면 관찰과 재현 근거를 발견 내용 파일에 남기고 `/triage`와 `/validate`를 거친다. 증거에서 민감 정보를 가린 뒤 `/report`로 보고서 초안을 작성한다. 이는 문서가 안내하는 흐름이며, 실제 조사 결과는 대상과 허가 조건에 따라 달라진다.

CLI만 확인하려면 Python 3.9 이상에서 복제한 저장소의 `python3 scripts/cbh.py --help`로 명령 목록을 볼 수 있다. `cbh recon`의 결과는 `recon/<대상>/` 아래의 호스트 목록, `RECON_SUMMARY.md`, `manifest.json` 등으로 남는다. 요약은 수집된 응답과 다음 검토 대상을 읽는 자료이고, 매니페스트는 `surface`가 우선순위를 읽는 입력이다. `classify`가 제안한 스킬 이름은 조사 방향을 뜻할 뿐 취약점 발견을 뜻하지 않는다. `triage` 결과 역시 문서에 설명된 키워드 기반 신호 판정이므로 원본 증거를 다시 살펴야 한다. 이 글에서는 외부 자산에 대해 정찰이나 공격 명령을 실행하지 않았다.

## 5. 활용 사례

**훈련 환경에서 전체 흐름을 연습하는 경우.** `USAGE.md`는 OWASP Juice Shop을 초보자가 연습할 수 있는 대상으로 제시한다. 대상별 폴더와 범위를 준비한 뒤 정찰, 유형별 조사, 검증, 증거 정리, 보고서 초안 작성까지 이어 보는 시나리오다. 저장소의 Juice Shop 검증 문서는 실제 HTTP로 확인한 항목과 브라우저 실행 대신 소스에서 확인한 항목을 구별하므로, 사례를 읽을 때도 어떤 단계까지 재현됐는지 나눠 봐야 한다.

**허가된 버그 바운티 프로그램의 보고 전 검토.** 프로그램 범위가 정해져 있고 발견 후보의 요청·응답이 있을 때 `/triage`의 7개 질문으로 보고 가능성을 점검한 다음 `/validate`와 증거 정리를 거쳐 `/report`로 초안을 만드는 흐름이 문서화돼 있다. 목적은 많은 후보를 바로 제출하는 것이 아니라 영향과 범위가 확인되지 않은 주장을 걸러내는 것이다. 최종 제출 여부와 공개 가능 시점은 프로그램 규칙에 따라 사람이 판단해야 한다.

**반복 정찰 결과를 팀이 검토하는 경우.** CLI 안내의 `recon → surface → classify` 흐름에서는 매니페스트에 호스트와 우선순위가 남고, URL 분류 결과는 살펴볼 스킬과 패턴 자료를 가리킨다. 대화형 조사를 시작하기 전에 수집 결과를 동일한 형식으로 정리할 수 있다는 장점이 있지만, 우선순위는 코드의 규칙에 따른 제안이다. `P1` 표기만으로 실제 취약성이나 침투 가능성이 입증되는 것은 아니다.

## 6. 참고 자료

- [Claude-BugHunter 저장소와 README](https://github.com/elementalsouls/Claude-BugHunter) — 프로젝트 범위, 설치 경로, 인터페이스 비교
- [설치 안내](https://github.com/elementalsouls/Claude-BugHunter/blob/main/INSTALL.md)와 [사용 안내](https://github.com/elementalsouls/Claude-BugHunter/blob/main/USAGE.md) — 요구사항과 단계별 작업 흐름
- [CLI 안내](https://github.com/elementalsouls/Claude-BugHunter/blob/main/docs/cbh-cli.md)와 [정찰 매니페스트 명세](https://github.com/elementalsouls/Claude-BugHunter/blob/main/docs/recon-manifest.md) — 하위 명령의 입력·출력과 결과 해석
- [`/hunt` 명령 정의](https://github.com/elementalsouls/Claude-BugHunter/blob/main/commands/hunt.md)와 [`/triage` 명령 정의](https://github.com/elementalsouls/Claude-BugHunter/blob/main/commands/triage.md) — 실제 단계 연결과 질문
- [보안·허가 범위 안내](https://github.com/elementalsouls/Claude-BugHunter/blob/main/SECURITY.md)와 [Juice Shop 검증 기록](https://github.com/elementalsouls/Claude-BugHunter/blob/main/docs/verification/juice-shop-2026-05-15.md) — 사용 경계와 공개 검증 사례
