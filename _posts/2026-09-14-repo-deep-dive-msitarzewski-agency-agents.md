---
layout: post
title: "Repo Deep Dive: msitarzewski/agency-agents"
date: 2026-09-14 09:07:37 +0900
categories: [github-repo-analysis]
tags: [github, architecture, backend, open-source, deep-dive]
repo: msitarzewski/agency-agents
stars: 152136
analyzed_at: 2026-09-14
---

## 1. 이 repo가 중요한 이유

`msitarzewski/agency-agents`는 GitHub star 152,136개를 가진 대규모 오픈소스 프로젝트다. 많은 개발자가 선택한 프로젝트이므로 README, 구조, 설정 파일만 봐도 제품화와 운영 성숙도에 대한 단서를 얻을 수 있다.

## 2. 한 문장 요약

A complete AI agency at your fingertips - From frontend wizards to Reddit community ninjas, from whimsy injectors to reality checkers. Each agent is a specialized expert with personality, processes, and proven deliverables.

## 3. 제품/문제 정의

GitHub description: A complete AI agency at your fingertips - From frontend wizards to Reddit community ninjas, from whimsy injectors to reality checkers. Each agent is a specialized expert with personality, processes, and proven deliverables.

README 초기 신호:
- # 🎭 The Agency: AI Specialists Ready to Transform Your Workflow
- > **A complete AI agency at your fingertips** - From frontend wizards to Reddit community ninjas, from whimsy injectors to reality checkers. Each agent is a specialized expert with personality, processes, and proven deli
- [![GitHub stars](https://img.shields.io/github/stars/msitarzewski/agency-agents?style=social)](https://github.com/msitarzewski/agency-agents)
- [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
- [![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://makeapullrequest.com)
- [![Sponsor](https://img.shields.io/badge/Sponsor-%E2%9D%A4-pink?logo=github)](https://github.com/sponsors/msitarzewski)
- [![Download the app](https://img.shields.io/github/v/release/msitarzewski/agency-agents-app?label=Download%20app&color=2563eb)](https://github.com/msitarzewski/agency-agents-app/releases/latest)
- > **[Agency Agents](https://agencyagents.app)** is a native app for **macOS, Linux & Windows** that browses the entire roster and installs it into Claude Code, Cursor, Codex, Gemini, Osaurus, and more — with a click. No 
- > **→ [Download the latest release](https://github.com/msitarzewski/agency-agents-app/releases/latest) · [agencyagents.app](https://agencyagents.app)**
- ## 🚀 What Is This?
- Born from a Reddit thread and months of iteration, **The Agency** is a growing collection of meticulously crafted AI agent personalities. Each agent is:
- - **🎯 Specialized**: Deep expertise in their domain (not generic prompt templates)

## 4. 아키텍처 구조

Primary language는 `Shell`이고 언어 구성은 다음과 같다.

- **Shell**: 81.2%
- **Python**: 18.0%
- **PowerShell**: 0.8%

상위 디렉터리 분포:
- `engineering/`: 64 files
- `specialized/`: 59 files
- `marketing/`: 36 files
- `scripts/`: 22 files
- `game-development/`: 21 files
- `integrations/`: 19 files
- `strategy/`: 17 files
- `gis/`: 13 files
- `security/`: 12 files
- `design/`: 10 files
- `sales/`: 9 files
- `testing/`: 9 files

## 5. 핵심 모듈

- `.github/workflows/check-divisions.yml`: name: Check Divisions Consistency / # Runs on every PR (no path filter on purpose): a new division directory must / # trip this check even when nobody touched divisions.json or the
- `.github/workflows/check-hermes-config-rewrite.yml`: name: Check Hermes Config Rewrite / # Regression test for the ensure_hermes_plugin_enabled() heredoc bug fixed / # alongside this workflow. Catches two related symptoms:
- `.github/workflows/check-runbooks.yml`: name: Check Runbooks Consistency / # Runs on every PR (no path filter on purpose): renaming or removing an agent / # must trip this check even when nobody touched strategy/runbooks
- `.github/workflows/check-tools.yml`: name: Check Tools Consistency / # Runs on every PR (no path filter on purpose): a new or renamed tool must trip / # this check even when nobody touched tools.json or the install/co
- `.github/workflows/lint-agents.yml`: name: Lint Agent Files / on: / pull_request:
- `.github/workflows/test-install.yml`: name: Test Installer / # No path filter on purpose: the installer's contract can break from the other / # side too — a renamed division, a file that loses its frontmatter, a change
- `CONTRIBUTING.md`: # 🤝 Contributing to The Agency / First off, thank you for considering contributing to The Agency! It's people like you who make this collection of AI agents better for everyone. / 
- `SECURITY.md`: # Security Policy / ## Reporting a Vulnerability / If you discover a security vulnerability in this project, please report it responsibly. Do NOT open a public GitHub issue for sec

## 6. 백엔드 개발자가 배울 점

- README에서 quickstart와 실제 설정 파일이 연결되는지 확인해야 한다.
- CI, Dockerfile, package/build 설정은 재현 가능한 개발환경의 핵심이다.
- 대형 repo일수록 public API와 internal 구현 경계를 문서화해야 유지보수가 가능하다.

## 7. 내 프로젝트에 훔쳐올 패턴

- 루트 README를 제품 랜딩처럼 구성한다.
- examples/docs/tests를 같은 흐름으로 연결한다.
- release, contributing, security 문서를 운영 표면으로 둔다.

## 8. 주의할 점 / 안티패턴

- star 수만으로 코드 품질을 단정하면 안 된다.
- README와 실제 코드 구조가 다를 수 있으므로 build/test 실행 검증이 필요하다.
- 대형 repo의 패턴을 작은 프로젝트에 그대로 복사하면 과설계가 될 수 있다.

## 9. vibe-grid / vibe-hr / jarvis / ehr-harness에 적용할 아이디어

- `vibe-grid`: public API, examples, QA matrix를 repo root에서 쉽게 찾게 만든다.
- `vibe-hr`: HR 업무 cycle별 demo와 검증 시나리오를 README/docs에 연결한다.
- `jarvis`: raw 자료보다 compiled wiki page를 제품 표면으로 만든다.
- `ehr-harness`: 설치, 실행, 안전장치, release log를 명확히 분리한다.

## 10. Source Links

- GitHub: https://github.com/msitarzewski/agency-agents
- README: https://github.com/msitarzewski/agency-agents#readme
