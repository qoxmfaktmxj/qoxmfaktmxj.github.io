---
layout: post
title: "Repo Deep Dive: NousResearch/hermes-agent"
date: 2026-06-19 08:58:41 +0900
categories: [github-repo-analysis]
tags: [github, architecture, backend, open-source, deep-dive]
repo: NousResearch/hermes-agent
stars: 196989
analyzed_at: 2026-06-19
---

## 1. 이 repo가 중요한 이유

Nous Research의 자체 개선 AI 에이전트로, 경험으로부터 스킬을 생성하고 대화를 검색하며 사용자 모델을 구축하는 폐쇄형 학습 루프를 갖춘 유일한 에이전트입니다. 모든 LLM 제공자를 지원하며 $5 VPS부터 GPU 클러스터까지 어디서나 실행 가능한 엔터프라이즈급 에이전트 프레임워크입니다.

## 2. 한 문장 요약

자체 학습 루프, 멀티플랫폼 게이트웨이, 스킬 자동 생성, 세션 간 메모리 관리를 갖춘 프로덕션급 AI 에이전트 프레임워크로, 어떤 LLM이든 사용 가능하고 Telegram/Discord/Slack 등 다양한 채널에서 실행됩니다.

## 3. 제품/문제 정의

기존 AI 에이전트는 단일 채널(CLI 또는 API)에 제한되고, 학습 능력이 없으며, 특정 LLM에 종속되고, 확장성이 낮으며, 세션 간 컨텍스트 손실이 발생합니다. Hermes는 이를 해결하기 위해 멀티채널 게이트웨이, 자동 스킬 생성, LLM 무관 아키텍처, 분산 실행 환경, 지속적 메모리 시스템을 제공합니다.

## 4. 아키텍처 구조

마이크로서비스 기반 아키텍처: (1) CLI/TUI 계층 - 로컬 터미널 인터페이스, (2) 게이트웨이 계층 - Telegram/Discord/Slack/WhatsApp/Signal 통합, (3) 에이전트 코어 - LLM 라우팅, 도구 실행, 메모리 관리, (4) 스킬 엔진 - 자동 스킬 생성/개선, (5) 메모리 시스템 - FTS5 기반 세션 검색, Honcho 사용자 모델링, (6) 실행 환경 - 로컬/Docker/SSH/Singularity/Modal/Daytona 지원, (7) 스케줄러 - Cron 기반 자동화. Python 백엔드(45MB), TypeScript 프론트엔드(7.4MB) 혼합 구성.

## 5. 핵심 모듈

1. agent/ - 에이전트 핵심 로직, LLM 호출, 도구 오케스트레이션 2. hermes_cli/ - CLI 인터페이스, TUI, 커맨드 라우팅 3. gateway/ - 멀티플랫폼 메시징 게이트웨이 (Telegram/Discord/Slack 등) 4. acp_adapter/ - 에이전트 커뮤니케이션 프로토콜 5. acp_registry/ - 스킬 레지스트리 관리 6. cron/ - 스케줄된 작업 실행 엔진 7. apps/ - 웹 UI, 데스크톱 앱, 보조 애플리케이션 8. datagen-config-examples/ - 학습 데이터 생성 설정 9. docker/ - 컨테이너 배포 설정 10. docs/ - 공식 문서

## 6. 백엔드 개발자가 배울 점

1. 멀티채널 통합: 단일 게이트웨이로 여러 메시징 플랫폼을 추상화하면 운영 복잡도를 크게 줄일 수 있습니다. 2. LLM 무관성: 제공자 추상화 계층을 통해 모델 전환을 코드 변경 없이 처리하면 유연성이 극대화됩니다. 3. 폐쇄형 학습 루프: 에이전트 자신의 경험으로부터 스킬을 자동 생성하고 개선하는 메커니즘이 장기 가치를 창출합니다. 4. 분산 실행: 로컬/클라우드/서버리스 환경을 동일한 인터페이스로 지원하면 배포 유연성이 극대화됩니다. 5. 메모리 아키텍처: FTS5 + LLM 요약으로 세션 간 컨텍스트를 효율적으로 유지할 수 있습니다. 6. 도구 RPC: 서브에이전트와 Python 스크립트의 RPC 호출로 복잡한 파이프라인을 단순화할 수 있습니다.

## 7. 내 프로젝트에 훔쳐올 패턴

1. 게이트웨이 패턴: 여러 메시징 채널을 단일 프로세스로 통합하는 어댑터 패턴 (Telegram/Discord/Slack 통합 사례) 2. LLM 라우팅: 제공자별 API 차이를 추상화하는 프로바이더 팩토리 패턴 (OpenAI/Claude/Nous Portal 지원) 3. 스킬 자동 생성: 복잡한 작업 후 LLM이 자동으로 재사용 가능한 스킬을 생성하는 메타-프롬프팅 패턴 4. 세션 검색: FTS5 + LLM 요약으로 대규모 대화 히스토리에서 관련 컨텍스트를 효율적으로 검색 5. 사용자 모델링: Honcho 방식의 변증법적 사용자 프로필 구축으로 개인화 강화 6. 서브에이전트 병렬화: 독립적인 작업을 격리된 에이전트로 분산 실행하는 패턴 7. 환경 추상화: 로컬/Docker/SSH/Singularity/Modal/Daytona를 동일 인터페이스로 지원하는 백엔드 전략 8. 자동 스킬 개선: 사용 중 스킬 성능을 모니터링하고 자동으로 프롬프트를 최적화하는 피드백 루프

## 8. 주의할 점 / 안티패턴

1. 복잡한 의존성: Python(45MB) + TypeScript(7.4MB) + Node.js + ripgrep + ffmpeg + Git 등 다양한 런타임 필요 → 설치 실패 가능성 높음, 특히 Windows 네이티브 환경에서 주의 2. 멀티플랫폼 테스트 부족: Windows 네이티브 지원이 최근 추가되어 엣지 케이스 존재 가능 3. 메모리 오버헤드: 세션 검색, 사용자 모델링, 스킬 관리를 위한 메모리 누적 → 장기 실행 시 메모리 누수 모니터링 필수 4. LLM 비용 증가: 자동 스킬 생성, 세션 요약, 사용자 모델링으로 인한 추가 LLM 호출 → 비용 제어 필요 5. 보안: 멀티채널 게이트웨이로 인한 공격 표면 증가, API 키 관리 복잡도 증가 6. 스킬 품질: 자동 생성된 스킬의 정확도/안정성 보장 부족, 수동 검증 필요 7. 제공자 의존성: Nous Portal, OpenRouter 등 제3자 서비스에 대한 의존도 증가 8. 문서화: 고급 기능(서브에이전트, 커스텀 도구, 환경 설정)의 문서화 부족

## 9. vibe-grid / vibe-hr / jarvis / ehr-harness에 적용할 아이디어

1. 멀티채널 챗봇: 기존 단일 채널 봇을 Hermes 게이트웨이 패턴으로 리팩토링하여 Telegram/Discord/Slack 동시 지원 2. LLM 애플리케이션: 특정 LLM에 종속된 코드를 Hermes의 프로바이더 추상화 패턴으로 변경하여 모델 전환 유연성 확보 3. 자동화 플랫폼: 반복적인 작업을 Hermes의 Cron + 스킬 자동 생성으로 자동화하고, 성능 저하 시 자동 개선 4. 엔터프라이즈 에이전트: 내부 도구를 Hermes의 도구 RPC로 통합하고, 서브에이전트로 병렬 처리 5. 데이터 분석 파이프라인: 복잡한 분석 작업을 Hermes의 스킬 + 서브에이전트로 분해하여 재사용성 극대화 6. 개인화 시스템: Honcho 방식의 사용자 모델링을 적용하여 세션 간 개인화 강화 7. 비용 최적화: Modal/Daytona 서버리스 환경으로 유휴 시간 비용 제거, 필요 시에만 활성화 8. 학습 데이터 생성: Hermes의 궤적 생성/압축 기능으로 다음 세대 도구 호출 모델 학습 데이터 자동 생성

## 10. Source Links

['https://github.com/NousResearch/hermes-agent', 'https://hermes-agent.nousresearch.com/', 'https://hermes-agent.nousresearch.com/docs/', 'https://discord.gg/NousResearch', 'https://nousresearch.com', 'https://portal.nousresearch.com', 'https://openrouter.ai', 'https://novita.ai', 'https://build.nvidia.com', 'https://huggingface.co', 'https://agentskills.io', 'https://github.com/plastic-labs/honcho', 'https://hermes-agent.nousresearch.com/docs/getting-started/termux', 'https://hermes-agent.nousresearch.com/docs/user-guide/features/tool-gateway']
