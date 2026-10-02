---
layout: post
title: "Repo Deep Dive: x1xhlol/system-prompts-and-models-of-ai-tools"
date: 2026-10-02 10:38:26 +0900
categories: [github-repo-analysis]
tags: [github, architecture, backend, open-source, deep-dive]
repo: x1xhlol/system-prompts-and-models-of-ai-tools
stars: 144005
analyzed_at: 2026-10-02
---

## 1. 이 repo가 중요한 이유

AI 도구들의 시스템 프롬프트와 내부 모델을 수집한 대규모 오픈소스 저장소로, 144K+ 스타를 받은 가장 포괄적인 AI 프롬프트 컬렉션. Cursor, Claude, Devin, Windsurf 등 주요 AI 코딩 도구들의 내부 동작 원리를 이해할 수 있는 유일한 공개 자료.

## 2. 한 문장 요약

30개 이상의 AI 도구(Cursor, Claude, Devin, Windsurf, Perplexity 등)의 시스템 프롬프트, 내부 도구, AI 모델 설정을 공개 수집한 보안 교육용 저장소.

## 3. 제품/문제 정의

AI 스타트업들이 자신의 시스템 프롬프트 보안을 간과하고 있으며, 프롬프트 인젝션과 시스템 프롬프트 추출 공격에 취약함. 개발자들은 상용 AI 도구의 실제 동작 방식을 알 수 없어 유사 도구 개발이나 보안 분석이 어려움.

## 4. 아키텍처 구조

단순 파일 시스템 기반 저장소 구조로 AI 도구별 디렉토리 분류(Anthropic, VSCode Agent, Cursor Prompts, Open Source prompts 등 12개 카테고리). 각 도구별로 시스템 프롬프트, 내부 도구 정의, 모델 설정을 마크다운/텍스트 파일로 저장. Discord 커뮤니티(LeaksLab)와 연동된 정보 공유 네트워크.

## 5. 핵심 모듈

1) 시스템 프롬프트 컬렉션(Cursor, Claude, Windsurf, Devin 등) 2) 내부 도구 및 함수 정의 3) AI 모델 파라미터 및 설정 4) 프롬프트 인젝션 취약점 분석 자료 5) ZeroLeaks 보안 서비스 연동 6) Discord 커뮤니티 피드백 루프

## 6. 백엔드 개발자가 배울 점

1) 보안 민감 정보의 공개는 윤리적 책임과 교육적 가치의 균형 필요 2) 오픈소스 커뮤니티 기반 정보 수집의 확장성(34K+ 포크) 3) 스타트업 보안 인식 제고를 위한 역설적 공개 전략 4) 암호화폐 기반 후원 시스템으로 익명성 보장 5) 이슈 기반 피드백 루프로 지속적 업데이트 관리

## 7. 내 프로젝트에 훔쳐올 패턴

1) 카테고리별 계층적 정보 분류 구조 2) 보안 경고와 상업적 솔루션(ZeroLeaks) 연동 모델 3) 다중 채널 커뮤니티 운영(Discord, X, Email) 4) 암호화폐/Patreon/Ko-fi 다중 후원 채널 5) 스폰서십 프로그램으로 수익화 6) 정기적 업데이트 로드맵 공개(12/07/2026)

## 8. 주의할 점 / 안티패턴

1) 시스템 프롬프트 공개는 AI 도구 제공자의 지적재산권 침해 가능성 2) 프롬프트 인젝션 공격 기술 확산으로 보안 위협 증가 3) 저장소 운영자의 법적 책임 문제(DMCA, 저작권) 4) 정보의 정확성 검증 메커니즘 부재 5) 악의적 사용자의 대규모 자동화 공격 도구 개발 가능성 6) 암호화폐 기반 후원의 규제 리스크

## 9. vibe-grid / vibe-hr / jarvis / ehr-harness에 적용할 아이디어

1) AI 보안 감사 도구 개발 시 프롬프트 인젝션 테스트 케이스 참고 2) 자체 AI 에이전트 개발 시 효과적인 시스템 프롬프트 패턴 분석 3) 프롬프트 보안 라이브러리 개발 4) AI 도구 비교 분석 플랫폼 구축 5) 내부 LLM 기반 코딩 어시스턴트의 프롬프트 설계 6) 보안 교육 및 레드팀 훈련 자료로 활용

## 10. Source Links

['https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools', 'https://discord.gg/NwzrWErdMU', 'https://zeroleaks.ai/', 'https://x.com/Lucknite', 'https://patreon.com/lucknite', 'https://ko-fi.com/lucknite', 'https://trendshift.io/repositories/14084', 'https://deepwiki.com/x1xhlol/system-prompts-and-models-of-ai-tools']
