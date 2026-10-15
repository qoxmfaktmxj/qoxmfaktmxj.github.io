---
layout: post
title: "Repo Deep Dive: multica-ai/andrej-karpathy-skills, 에이전트의 과잉 구현을 줄이는 네 원칙"
date: 2026-07-05 08:10:20 +0900
categories: [github-repo-analysis]
tags: [github, ai-coding, claude-code, cursor, agent-skills]
repo: multica-ai/andrej-karpathy-skills
analyzed_at: 2026-10-16
analyzed_commit: 2c606141936f1eeef17fa3043a72095b4765b9c2
---

“목록을 CSV로 내려받게 해줘”라고 했더니 에이전트가 내보내기 프레임워크를 만든다. CSV에 더해 JSON을 지원하고, 백그라운드 작업과 알림 설정을 넣는다. 옆에 있던 조회 함수도 정리한다. 결과물이 그럴듯해 보여도 정작 사용자가 원한 데이터 범위는 확인하지 않았다면, 검토할 코드는 늘고 요구사항은 여전히 불명확하다.

`andrej-karpathy-skills`는 이런 상황을 줄이려는 코딩 에이전트용 행동 지침이다. Claude Code로 기능을 만들거나 기존 코드를 수정하는 개발자가 주된 독자이며, Cursor에서 쓰는 방법도 제공한다. 새로운 모델이나 코드 분석기를 설치하는 프로젝트가 아니다. 에이전트에게 무엇을 먼저 확인하고 어디까지 변경하며 무엇으로 완료를 판단할지 알려주는 문서를 배포한다.

이번 재검토 기준일은 2026년 10월 16일이며, 확인한 문서는 커밋 `2c60614`를 기준으로 한다. 현재 저장소 주소의 소유자는 `multica-ai`이고, 플러그인 메타데이터의 저자는 `forrestchang`이다. README는 Andrej Karpathy의 관찰에서 출발했다고 설명한다. 따라서 Karpathy 본인이 배포하거나 운영하는 공식 도구로 소개해서는 안 된다. README에서 함께 홍보하는 Multica 역시 이 지침 파일 자체와는 별도 프로젝트다. [README](https://github.com/multica-ai/andrej-karpathy-skills/blob/2c606141936f1eeef17fa3043a72095b4765b9c2/README.md), [플러그인 메타데이터](https://github.com/multica-ai/andrej-karpathy-skills/blob/2c606141936f1eeef17fa3043a72095b4765b9c2/.claude-plugin/plugin.json)

## 구현에 앞서 질문이 필요한 지점을 찾는다

네 원칙은 코딩 전에 생각하기, 단순함 우선, 필요한 부분만 변경하기, 검증 가능한 목표로 실행하기다. 이 문구를 외우는 것보다 하나의 요청에 적용해 보는 편이 이해하기 쉽다. 아래의 주문 목록 CSV 작업과 요청문은 원칙을 설명하기 위해 구성한 가상 사례이며 실제 도입 사례나 실행 결과가 아니다.

가상의 관리 화면에서 사용자가 “주문 목록을 CSV로 내려받게 해줘”라고 요청했다고 하자. 에이전트가 모든 주문을 조회해 서버의 임시 파일로 저장하면 동작하는 코드를 만들 수는 있다. 그러나 사용자가 원한 것이 현재 검색 조건에 맞는 주문인지, 현재 페이지의 주문인지, 전체 이력인지는 결정되지 않았다. 파일을 브라우저에서 받을지, 어떤 열을 포함할지도 남아 있다.

첫 원칙인 Think Before Coding은 이 빈칸을 조용히 채우지 말라는 지침이다. 이 사례라면 먼저 현재 화면의 검색 조건과 기존 다운로드 기능을 살펴보고, 코드만으로 알 수 없는 범위를 질문한다. “현재 검색 조건에 맞는 전체 주문을 브라우저에서 받는 기능으로 이해했다. 현재 페이지만 필요한 경우에는 구현 범위가 달라진다”처럼 자신의 이해와 대안을 드러내는 방식이다. 모든 질문을 사용자에게 떠넘기기보다 이미 확인할 수 있는 사실과 사용자가 결정해야 할 사항을 구분하는 데 의미가 있다.

공식 `EXAMPLES.md`에도 사용자 데이터 내보내기 요청을 받고 전체 사용자, 형식, 필드, 저장 위치를 임의로 정하는 사례가 나온다. 중요한 것은 질문의 개수보다 구현을 바꾸는 가정을 찾아내는 일이다. 요구가 충분히 명확한데도 같은 내용을 되묻는 절차로 사용하면 이 원칙의 목적에서 멀어진다. [공식 내보내기 예제](https://github.com/multica-ai/andrej-karpathy-skills/blob/2c606141936f1eeef17fa3043a72095b4765b9c2/EXAMPLES.md#example-1-hidden-assumptions)

## 요구가 정해졌다면 미래 기능을 미리 만들지 않는다

가상 사례의 요구가 “현재 검색 조건에 맞는 주문 번호, 주문일, 상태를 CSV로 받는다”로 정해졌다고 하자. 이제 문제는 정반대다. 에이전트가 나중을 대비한다며 내보내기 형식 인터페이스, 출력 전략 클래스, 예약 실행 설정을 만들 수 있다. 지금 필요한 출력 형식은 하나인데 사용자는 새 구조까지 읽고 검증해야 한다.

Simplicity First는 현재 요구를 해결하는 최소 코드를 선택하라고 한다. 기존 검색 로직을 활용할 수 있다면 그 흐름에 CSV 응답을 추가하는 접근부터 검토한다. 다른 형식이나 예약 실행이 실제 요구로 들어왔을 때 구조를 확장해도 된다. 다만 최소 코드라는 말만 보고 데이터 권한이나 CSV 값 처리처럼 현재 기능을 성립시키는 조건을 생략해서는 안 된다. 무엇이 불필요한지는 줄 수보다 현재 요구와 연결되는지로 판단해야 한다.

이 판단을 보여주는 공식 예제가 할인 계산이다. 문서는 여러 전략과 설정 객체를 조립하는 구현과, 금액에 비율을 곱하는 작은 함수를 대비한다. 복잡한 설계 패턴 자체를 금지하는 주장이 아니라 필요가 생기기 전에 그 비용을 지불하지 말라는 설명이다. 지침 파일도 한 번만 쓰는 코드의 추상화와 요청하지 않은 설정 가능성을 경계한다. [할인 계산 예제](https://github.com/multica-ai/andrej-karpathy-skills/blob/2c606141936f1eeef17fa3043a72095b4765b9c2/EXAMPLES.md#example-1-over-abstraction), [지침 원문](https://github.com/multica-ai/andrej-karpathy-skills/blob/2c606141936f1eeef17fa3043a72095b4765b9c2/CLAUDE.md)

## 좋은 아이디어라도 이번 변경에 섞지 않는다

CSV 기능을 구현하다가 주변 조회 코드의 이름이 어색하고 오래된 주석도 눈에 들어올 수 있다. 에이전트가 이를 한꺼번에 고치면 CSV 결과가 달라진 이유를 추적하기 어려워진다. 작은 기능 추가를 검토하는 사람이 조회 동작과 포맷 변경까지 함께 판단해야 하기 때문이다.

Surgical Changes는 변경된 각 줄이 요청과 직접 이어져야 한다는 기준을 제시한다. 기존 스타일을 따르고, 고장 나지 않은 주변 코드를 리팩터링하지 않으며, 관련 없는 미사용 코드를 발견하면 알려주되 임의로 지우지 않는다. 반대로 자신이 바꾼 코드 때문에 import가 사용되지 않게 됐다면 그 정리는 이번 작업에 포함된다. “정리하지 않는다”가 아니라 정리의 원인을 구분하는 규칙이다.

가상 CSV 작업에서는 다운로드 버튼, 필요한 응답 처리, 그 동작을 확인하는 테스트가 변경 이유로 설명되어야 한다. 오래된 조회 함수의 이름을 바꾼 줄이 있다면 왜 내보내기에 필요한지 따져 볼 수 있다. 이 기준 덕분에 사람도 리뷰 중 “왜 이 줄이 바뀌었는가”를 같은 언어로 물을 수 있다. 공식 문서의 업로드 로깅 예제는 로그를 추가하면서 따옴표, 타입 힌트, 반환 로직까지 바꾸는 경우를 보여준다. [로깅 변경 예제](https://github.com/multica-ai/andrej-karpathy-skills/blob/2c606141936f1eeef17fa3043a72095b4765b9c2/EXAMPLES.md#example-2-style-drift)

## 완료 기준은 코드 작성 전에 적는다

범위를 좁혀도 “CSV 기능 구현 완료”만으로는 충분하지 않다. 버튼이 생겼지만 검색 조건이 빠졌거나, 파일의 열 순서가 잘못됐을 수 있다. Goal-Driven Execution은 작업 지시를 관찰 가능한 결과로 바꾸라고 한다. 가상 사례에서는 다음처럼 요청할 수 있다.

```text
기존 주문 목록에 CSV 다운로드를 추가한다.
범위: 현재 검색 조건에 맞는 주문, 주문 번호/주문일/상태 세 열.
완료 기준:
1. 검색 조건 밖 주문이 파일에 포함되지 않는다.
2. 헤더와 각 행의 열 순서가 일치한다.
3. 조회 결과가 없을 때도 정해진 헤더를 내려받는다.
4. 기존 목록 조회 테스트가 통과한다.
구현 전에 확인할 가정과 검증 계획을 짧게 제시한다.
```

이 요청문 역시 설명용이다. 실제 프로젝트에서는 권한, 데이터 크기, 인코딩 등 필요한 조건을 확인해 기준을 조정해야 한다. 중요한 변화는 에이전트가 “그럴듯한 코드” 대신 확인할 결과를 향해 작업한다는 점이다. 버그 수정이라면 먼저 증상을 재현하고, 수정 후 같은 검증이 통과하는지 확인하는 순서가 된다. 테스트를 실행하지 못했다면 완료 보고에서도 그 한계를 구분해야 한다. [목표와 검증을 연결하는 스킬 지침](https://github.com/multica-ai/andrej-karpathy-skills/blob/2c606141936f1eeef17fa3043a72095b4765b9c2/skills/karpathy-guidelines/SKILL.md)

## 실제로 적용할 때는 사용하는 도구의 경로를 고른다

Claude Code에서는 플러그인 방식과 프로젝트 지침 파일 방식을 안내한다. 확인한 README의 플러그인 설치 명령은 다음 두 단계다. 첫 줄은 마켓플레이스를 등록하고, 둘째 줄은 그 마켓플레이스의 플러그인을 설치한다.

```text
/plugin marketplace add forrestchang/andrej-karpathy-skills
/plugin install andrej-karpathy-skills@karpathy-skills
```

현재 검토한 주소는 `multica-ai`이지만 README에는 위와 같이 `forrestchang` 경로가 남아 있다. 여기서는 명령을 임의로 바꾸지 않고 문서 그대로 소개한다. 실제 설치 성공이나 주소 리다이렉트는 이번 검토에서 시험하지 않았다. 메타데이터상 플러그인 버전은 `1.0.0`이며 `skills/karpathy-guidelines`를 제공한다. [README 설치 안내](https://github.com/multica-ai/andrej-karpathy-skills/blob/2c606141936f1eeef17fa3043a72095b4765b9c2/README.md#install), [플러그인 정의](https://github.com/multica-ai/andrej-karpathy-skills/blob/2c606141936f1eeef17fa3043a72095b4765b9c2/.claude-plugin/plugin.json)

한 프로젝트에만 적용하려면 `CLAUDE.md`의 내용을 프로젝트 지침에 넣는 방법이 있다. 기존 파일이 있다면 덮어쓰기 전에 팀 규칙과 합칠 부분을 검토한다. 테스트 명령, 수정할 수 없는 경로, 기존 오류 처리 방식처럼 프로젝트에 필요한 정보는 이 네 원칙과 함께 둔다. 문서가 짧다고 해서 프로젝트의 맥락까지 대신 제공하는 것은 아니다.

Cursor에서는 `.cursor/rules/karpathy-guidelines.mdc`를 프로젝트의 같은 경로로 복사하는 방법을 안내한다. 이 규칙은 `alwaysApply: true`로 제공되며, 문서는 Cursor의 규칙 설정 화면에서 등록 여부를 확인하도록 한다. 선택 사항으로 개인 스킬 디렉터리에 `SKILL.md`를 복사하거나 연결하는 방법도 설명한다. Claude Code 플러그인을 설치하면 Cursor에도 그대로 적용된다고 생각해서는 안 된다. [Cursor 적용 안내](https://github.com/multica-ai/andrej-karpathy-skills/blob/2c606141936f1eeef17fa3043a72095b4765b9c2/CURSOR.md)

## 지침을 넣은 뒤에는 응답과 diff를 본다

이 저장소의 파일은 에이전트에게 제공하는 지시문이다. 파일을 두었다는 사실만으로 모든 응답이 네 원칙을 지킨다고 판정할 수는 없다. 적용 후에는 구현 전에 중요한 가정이 드러나는지, 요청하지 않은 기능이 줄었는지, 각 변경의 이유를 설명할 수 있는지, 완료 보고에 실제 검증 결과가 있는지를 살펴본다. 전후 개선율이나 모델별 효과를 수치로 보장하는 근거는 이번 검토에서 확인하지 않았다.

신중함에도 비용은 있다. 문서 자체가 속도보다 주의를 우선하는 성향을 밝히고, 오타 수정 같은 사소한 작업에는 판단을 사용하라고 한다. 명백한 한 줄 변경까지 긴 질문과 계획으로 늘리는 방식으로 적용할 필요는 없다. 반대로 여러 해석이 가능한 기능 추가나 기존 동작을 건드리는 수정에서는 이런 짧은 규칙이 변경의 경계를 합의하는 출발점이 된다.

라이선스는 README와 플러그인 메타데이터에 MIT로 표시되어 있다. 다만 확인한 커밋의 파일 목록에는 별도 `LICENSE` 파일이 없었다. 이번 글은 공개 문서와 메타데이터를 검토했으며 플러그인 설치, 에이전트 응답 비교, 예제 코드 실행은 수행하지 않았다.

## 참고 자료

- [검토한 커밋의 README](https://github.com/multica-ai/andrej-karpathy-skills/blob/2c606141936f1eeef17fa3043a72095b4765b9c2/README.md)
- [네 원칙을 담은 CLAUDE.md](https://github.com/multica-ai/andrej-karpathy-skills/blob/2c606141936f1eeef17fa3043a72095b4765b9c2/CLAUDE.md)
- [공식 설명 예제 EXAMPLES.md](https://github.com/multica-ai/andrej-karpathy-skills/blob/2c606141936f1eeef17fa3043a72095b4765b9c2/EXAMPLES.md)
- [Cursor 사용법](https://github.com/multica-ai/andrej-karpathy-skills/blob/2c606141936f1eeef17fa3043a72095b4765b9c2/CURSOR.md)
- [마켓플레이스 등록 정보](https://github.com/multica-ai/andrej-karpathy-skills/blob/2c606141936f1eeef17fa3043a72095b4765b9c2/.claude-plugin/marketplace.json)
