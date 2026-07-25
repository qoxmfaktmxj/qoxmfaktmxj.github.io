---
layout: post
title: "Repo Deep Dive: mattpocock/skills"
date: 2026-07-26 08:07:51 +0900
categories: [github-repo-analysis]
tags: [github, architecture, backend, open-source, deep-dive]
repo: mattpocock/skills
stars: 188187
analyzed_at: 2026-07-26
---

## 1. 이 repo가 중요한 이유

AI 에이전트(Claude Code, Codex 등)와의 협업에서 발생하는 4가지 핵심 실패 모드를 해결하기 위한 재사용 가능한 엔지니어링 스킬 모음. 개발자의 의도 전달 부족, 에이전트의 과도한 장황함, 코드 품질 저하, 아키텍처 부실화 문제를 체계적으로 해결하는 프레임워크 제공.

## 2. 한 문장 요약

실제 엔지니어링 경험에 기반한 작고 조합 가능한 AI 에이전트 스킬들로, 에이전트와의 협업 효율성과 코드 품질을 동시에 높이는 오픈소스 도구 모음.

## 3. 제품/문제 정의

AI 코딩 에이전트 도입 시 발생하는 4가지 주요 문제: (1) 요구사항 미정렬로 인한 오해, (2) 장황한 코드와 낮은 토큰 효율성, (3) 피드백 루프 부재로 인한 낮은 코드 품질, (4) 설계 부실로 인한 기술 부채 누적. 기존 GSD/BMAD/Spec-Kit 같은 접근법은 프로세스 제어권을 빼앗고 버그 해결을 어렵게 함.

## 4. 아키텍처 구조

플러그인 기반 모듈식 아키텍처. (1) 설치 방식: skills.sh 인스톨러(편집 가능한 로컬 복사) vs Claude Code 네이티브 플러그인(읽기 전용 관리형 번들). (2) 스킬 분류: 생산성(/grill-me), 엔지니어링(/grill-with-docs, /tdd, /diagnosing-bugs). (3) 핵심 흐름: 그릴링 세션 → 공유 언어 정의(CONTEXT.md) → ADR 문서화 → TDD 루프 → 버그 진단. (4) 멀티 에이전트 지원: Claude, Codex, Agent-Skills-standard 호환.

## 5. 핵심 모듈

1. /grill-me: 에이전트와의 상세 질의응답을 통한 요구사항 정렬. 2. /grill-with-docs: 그릴링 + 공유 언어(CONTEXT.md) + ADR 작성. 3. /tdd: Red-Green-Refactor 루프로 테스트 주도 개발 강제. 4. /diagnosing-bugs: 체계적 디버깅 프레임워크. 5. /triage: 이슈 트래커 연동(GitHub/Linear/로컬파일). 6. 설정 모듈: /setup-matt-pocock-skills로 초기화.

## 6. 백엔드 개발자가 배울 점

1. 도메인 주도 설계(DDD) 원칙: 공유 언어로 에이전트-개발자 간 의사소통 효율성 극대화. 2. 피드백 루프의 중요성: 정적 타입, 브라우저 접근, 자동화 테스트로 에이전트의 블라인드 플라이트 방지. 3. 작은 단계의 반복: 큰 작업은 피하고 빠른 피드백으로 속도 확보. 4. 일일 설계 투자: 매일 시스템 설계에 시간 할애하여 기술 부채 방지. 5. 프로세스 제어권 유지: 프레임워크가 아닌 스킬로 개발자의 자율성 보장.

## 7. 내 프로젝트에 훔쳐올 패턴

1. 그릴링 세션 패턴: 에이전트에게 상세한 질문을 강제하여 요구사항 정렬. 2. CONTEXT.md 문서화: 프로젝트 고유 용어와 개념을 한 곳에 정의하여 토큰 효율성 50% 이상 개선. 3. ADR(Architecture Decision Record) 통합: 설계 결정을 문서화하여 향후 맥락 제공. 4. Red-Green-Refactor 루프 자동화: 테스트 먼저 작성 → 실패 확인 → 구현 → 리팩토링 순서 강제. 5. 멀티 설치 방식: 로컬 편집 가능 vs 관리형 플러그인 선택지 제공. 6. 이슈 트래커 추상화: GitHub/Linear/로컬 파일 모두 지원하는 통일된 인터페이스.

## 8. 주의할 점 / 안티패턴

1. 스킬 학습 곡선: 초기 설정(/setup-matt-pocock-skills)이 필수이며 이슈 트래커 선택, 라벨 정의, 문서 저장소 설정 등 사전 준비 필요. 2. 에이전트 의존성: 스킬 효과는 사용하는 AI 모델의 능력에 크게 의존. 저급 모델은 그릴링 질문을 제대로 이해하지 못할 수 있음. 3. 문서 유지 비용: CONTEXT.md와 ADR 문서를 최신으로 유지하지 않으면 오히려 에이전트를 혼란스럽게 함. 4. 플러그인 vs 로컬 복사 선택: 플러그인은 자동 업데이트되지만 커스터마이징 불가. 로컬 복사는 유연하지만 수동 유지 필요. 5. 과도한 그릴링: 매번 /grill-me를 사용하면 토큰 낭비. 작은 변경은 직접 지시하는 것이 효율적.

## 9. vibe-grid / vibe-hr / jarvis / ehr-harness에 적용할 아이디어

1. 신규 프로젝트 시작: /grill-with-docs로 요구사항 정렬 + CONTEXT.md 작성 → 토큰 효율성 30-50% 향상. 2. 기존 프로젝트 리팩토링: /tdd 스킬로 테스트 커버리지 확보 → 에이전트의 회귀 버그 방지. 3. 버그 수정 프로세스: /diagnosing-bugs로 체계적 디버깅 → 에이전트의 무분별한 코드 변경 방지. 4. 팀 협업: CONTEXT.md를 팀 문서로 공유 → 인간 개발자와 AI 에이전트 간 언어 통일. 5. 마이크로서비스 아키텍처: ADR 문서화로 각 서비스의 설계 결정 기록 → 향후 에이전트 온보딩 시간 단축. 6. CI/CD 통합: /triage와 이슈 트래커 연동으로 자동화된 작업 흐름 구축.

## 10. Source Links

https://github.com/mattpocock/skills | https://skills.sh/b/mattpocock/skills | https://www.aihero.dev/s/skills-newsletter | https://github.com/mattpocock/course-video-manager (CONTEXT.md 예제) | https://code.claude.com/docs/en/plugins (Claude Code 플러그인 문서) | .agents/adr/0002-ship-as-a-claude-code-plugin.md (Codex 플러그인 로드맵)
