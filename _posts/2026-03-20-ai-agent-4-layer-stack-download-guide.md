---
layout: post
title: "AI 에이전트 실전 운영 4-Layer 패키지: Bootstrap→Governance→Artifacts→Tool Adapters"
date: 2026-03-20 23:12:00 +0900
categories: [ai]
tags: [ai, agentic-engineering, harness-engineering, governance, prompt, templates, tool-adapters]
---

# AI 에이전트 실전 운영 4-Layer 패키지

이 글은 **AI 에이전트 도입/운영을 바로 실행할 수 있도록 4개 레이어 문서를 단계별로 묶은 안내 글**입니다.

핵심은 단순 프롬프트 한 장이 아니라, **발견(Discovery) → 운영 규칙(Governance) → 표준 산출물(Artifacts) → 도구 강제(Adapters)**까지 일관된 체계로 연결하는 것입니다.

---

## 구성 파일 (다운로드)

아래 4개 파일은 레포의 `assets/file/` 경로에 올라가 있으며, 그대로 내려받아 사용할 수 있습니다.

- **01_BOOTSTRAP_PROMPT.md**
  - 첫 접점용 프롬프트
  - 질문 배치, 근거 태그, Discovery Packet, Layer 2 handoff 포함
  - <a href="/assets/file/01_BOOTSTRAP_PROMPT.md" download>다운로드</a>

- **02_GOVERNANCE_SPEC.md**
  - 운영 헌법/가드레일 문서
  - 모드 전이, 위험도 R0~R3, 승인 매트릭스, 품질 점수, sub-agent, skill/hook 원칙 포함
  - <a href="/assets/file/02_GOVERNANCE_SPEC.md" download>다운로드</a>

- **03_ARTIFACT_TEMPLATES.md**
  - 실제 문서 초안 생성 템플릿
  - AGENTS.md, ARCHITECTURE.md, TEST_STRATEGY.md, QUALITY_SCORE.md 등 canonical 골격 포함
  - <a href="/assets/file/03_ARTIFACT_TEMPLATES.md" download>다운로드</a>

- **04_TOOL_ADAPTERS.md**
  - 도구 투영 및 기계적 강제 레이어
  - Claude/Cursor/CI/hooks/CODEOWNERS 적용 규칙 포함
  - <a href="/assets/file/04_TOOL_ADAPTERS.md" download>다운로드</a>

---

## 설계 원칙 요약

- **Canonical source는 Layer 3 문서(Artifacts)**
- CLAUDE.md, `.cursor/rules/*`, CI, hook, CODEOWNERS는 **Layer 4 projection**으로 분리
- 각 단계 종료 시 **다음 레이어로 넘길 Handoff Packet** 제공
- 근거 태그 `[Observed] [User-stated] [Derived] [Assumption] [Proposal] [Missing]`를 전 단계에 유지

---

## 바로 쓰는 순서

1. `01_BOOTSTRAP_PROMPT.md`를 AI에 붙여 넣어 Discovery Packet 생성
2. 검토 후 `02_GOVERNANCE_SPEC.md`로 Blueprint/Governance Packet 확정
3. 승인되면 `03_ARTIFACT_TEMPLATES.md`로 canonical 문서 초안 생성
4. 마지막으로 `04_TOOL_ADAPTERS.md`로 도구별 enforcement 구성

이 순서(01→02→03→04)로 진행하면, 초안 품질뿐 아니라 운영 일관성까지 확보하기 쉽습니다.
