---
layout: post
title: "Repo Deep Dive: ultraworkers/claw-code"
date: 2026-06-27 08:20:43 +0900
categories: [github-repo-analysis]
tags: [github, architecture, backend, open-source, deep-dive]
repo: ultraworkers/claw-code
stars: 194338
analyzed_at: 2026-06-27
---

## 1. 이 repo가 중요한 이유

`ultraworkers/claw-code`는 GitHub star 194,338개를 가진 대규모 오픈소스 프로젝트다. 많은 개발자가 선택한 프로젝트이므로 README, 구조, 설정 파일만 봐도 제품화와 운영 성숙도에 대한 단서를 얻을 수 있다.

## 2. 한 문장 요약

An agent-managed museum exhibit, built in Rust with Gajae-Code / LazyCodex — developed and maintained with no human intervention.

## 3. 제품/문제 정의

GitHub description: An agent-managed museum exhibit, built in Rust with Gajae-Code / LazyCodex — developed and maintained with no human intervention.

README 초기 신호:
- # Claw Code
- <img src="https://img.shields.io/badge/LazyCodex-codex%20for%20no--brainers-111111?style=for-the-badge&logo=github&logoColor=white" alt="LazyCodex banner" />
- <img src="https://img.shields.io/badge/Gajae--Code-red--claw%20agent%20harness-B22222?style=for-the-badge&logo=github&logoColor=white" alt="Gajae-Code banner" />
- <img src="https://opengraph.githubassets.com/lazycodex-card/code-yeongyu/lazycodex" alt="LazyCodex GitHub card" width="280" />
- <img src="https://opengraph.githubassets.com/gajae-code-card/Yeachan-Heo/gajae-code" alt="Gajae-Code GitHub card" width="280" />
- <h3 align="center">start with the real crab-powered harnesses</h3>
- <a href="https://github.com/code-yeongyu/lazycodex"><b>github.com/code-yeongyu/lazycodex</b></a>
- <a href="https://github.com/Yeachan-Heo/gajae-code"><b>github.com/Yeachan-Heo/gajae-code</b></a>
- <img src="https://img.shields.io/badge/Open-LazyCodex-111111?style=flat-square&logo=github&logoColor=white" alt="Open LazyCodex on GitHub" />
- <img src="https://img.shields.io/badge/Open-Gajae--Code-B22222?style=flat-square&logo=github&logoColor=white" alt="Open Gajae-Code on GitHub" />
- <img src="https://img.shields.io/badge/Discord-join%20the%20harness%20lab-5865F2?style=for-the-badge&logo=discord&logoColor=white" alt="Join the harness lab on Discord" />
- <img src="https://img.shields.io/badge/Discord-join%20the%20crab%20tank-5865F2?style=for-the-badge&logo=discord&logoColor=white" alt="Join the crab tank on Discord" />

## 4. 아키텍처 구조

Primary language는 `Rust`이고 언어 구성은 다음과 같다.

- **Rust**: 95.4%
- **Python**: 3.9%
- **Shell**: 0.4%
- **HTML**: 0.2%
- **Dockerfile**: 0.0%

상위 디렉터리 분포:
- `rust/`: 175 files
- `src/`: 100 files
- `docs/`: 26 files
- `<root files>/`: 22 files
- `scripts/`: 8 files
- `assets/`: 7 files
- `tests/`: 5 files

## 5. 핵심 모듈

- `.github/workflows/release.yml`: name: Release binaries / on: / push:
- `.github/workflows/rust-ci.yml`: name: Rust CI / on: / push:
- `.github/workflows/rust.yml`: name: Rust / on: / push:
- `CONTRIBUTING.md`: # Contributing to Claw Code / Thanks for helping improve Claw Code. This repository is a Rust-first CLI / workspace with supporting docs and compatibility fixtures.
- `SECURITY.md`: # Security Policy / ## Supported versions / Security fixes target the current `main` branch and the latest published
- `docker-compose.yml`: services: / qdrant: / image: qdrant/qdrant:latest
- `rust/Cargo.toml`: [workspace] / members = ["crates/*"] / resolver = "2"
- `rust/crates/api/Cargo.toml`: [package] / name = "api" / version.workspace = true
- `rust/crates/claw-analog/Cargo.toml`: [package] / name = "claw-analog" / version.workspace = true
- `rust/crates/claw-rag-service/Cargo.toml`: [package] / name = "claw-rag-service" / version.workspace = true
- `rust/crates/claw-rag-service/Dockerfile`: # qdrant-client currently requires a fairly recent stable Rust. / # Keep this pinned to avoid surprise breaks from `rust:latest`. / FROM rust:1.91-bookworm AS builder
- `rust/crates/commands/Cargo.toml`: [package] / name = "commands" / version.workspace = true
- `rust/crates/compat-harness/Cargo.toml`: [package] / name = "compat-harness" / version.workspace = true
- `rust/crates/mock-anthropic-service/Cargo.toml`: [package] / name = "mock-anthropic-service" / version.workspace = true
- `rust/crates/plugins/Cargo.toml`: [package] / name = "plugins" / version.workspace = true
- `rust/crates/runtime/Cargo.toml`: [package] / name = "runtime" / version.workspace = true
- `rust/crates/rusty-claude-cli/Cargo.toml`: [package] / name = "rusty-claude-cli" / version.workspace = true
- `rust/crates/telemetry/Cargo.toml`: [package] / name = "telemetry" / version.workspace = true
- `rust/crates/tools/Cargo.toml`: [package] / name = "tools" / version.workspace = true

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

- GitHub: https://github.com/ultraworkers/claw-code
- README: https://github.com/ultraworkers/claw-code#readme
