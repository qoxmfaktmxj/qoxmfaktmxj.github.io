---
layout: post
title: "Repo Deep Dive: morluto/rea"
date: 2026-10-15 09:29:17 +0900
categories: [github-repo-analysis]
tags: [github, architecture, backend, open-source, deep-dive]
repo: morluto/rea
stars: 241575
analyzed_at: 2026-10-15
---

## 1. 이 repo가 중요한 이유

`morluto/rea`는 GitHub star 241,575개를 가진 대규모 오픈소스 프로젝트다. 많은 개발자가 선택한 프로젝트이므로 README, 구조, 설정 파일만 봐도 제품화와 운영 성숙도에 대한 단서를 얻을 수 있다.

## 2. 한 문장 요약

Reverse engineer anything with agents, from app behavior down to native binaries.

## 3. 제품/문제 정의

GitHub description: Reverse engineer anything with agents, from app behavior down to native binaries.

README 초기 신호:
- **English** · [简体中文](docs/readme/README_zh.md) · [繁體中文](docs/readme/README_zh-TW.md) · [日本語](docs/readme/README_ja.md) · [한국어](docs/readme/README_ko.md) · [Türkçe](docs/readme/README_tr.md) · [Русский](docs/readme/README
- # REA: Reverse Engineer Anything
- ### One MCP for reverse engineering across binaries, applications, and runtime behavior.
- **See a feature you like. Understand how it works, down to the binary level.**
- [![npm version](https://img.shields.io/npm/v/rea-agents?style=flat-square&color=cb3837)](https://www.npmjs.com/package/rea-agents)
- [![MCP tool catalog](https://img.shields.io/badge/MCP-tool_catalog-5c4ee5?style=flat-square)](docs/mcp-contracts.md#generated-catalog)
- [![Node.js requirements](https://img.shields.io/badge/Node.js-requirements-339933?style=flat-square&logo=nodedotjs&logoColor=white)](#what-you-can-analyze)
- [![skills.sh](https://skills.sh/b/morluto/rea?style=flat-square)](https://skills.sh/morluto/rea/reverse-engineer-anything)
- [![MIT license](https://img.shields.io/badge/license-MIT-f4c430?style=flat-square)](LICENSE)
- [![Discord](https://img.shields.io/discord/1556595354999332884?logo=discord&logoColor=white&label=Discord&color=5865F2)](https://discord.gg/GkcryMnJDM)
- <a href="https://trendshift.io/repositories/82054?utm_source=repository-badge&amp;utm_medium=badge&amp;utm_campaign=badge-repository-82054" target="_blank" rel="noopener noreferrer"><img src="https://trendshift.io/api/ba
- **[Website](https://rea.tools/) · [Guides](https://rea.tools/guides/) · [Showcases](https://rea.tools/showcase/)**

## 4. 아키텍처 구조

Primary language는 `TypeScript`이고 언어 구성은 다음과 같다.

- **TypeScript**: 83.5%
- **JavaScript**: 9.4%
- **HTML**: 2.7%
- **Python**: 2.1%
- **Java**: 1.4%
- **C++**: 0.3%
- **CSS**: 0.2%
- **Swift**: 0.2%
- **C**: 0.1%
- **Shell**: 0.0%

상위 디렉터리 분포:
- `scripts/`: 379 files
- `src/`: 310 files
- `docs/`: 99 files
- `experiments/`: 77 files
- `bridge/`: 32 files
- `<root files>/`: 23 files
- `licenses/`: 19 files
- `native/`: 5 files

## 5. 핵심 모듈

- `.github/workflows/ci-full-pr.yml`: name: Full PR qualification / on: / pull_request:
- `.github/workflows/ci-timings.yml`: name: CI timings / on: / schedule:
- `.github/workflows/ci.yml`: name: CI / on: / push:
- `.github/workflows/mutation.yml`: name: Mutation sweep / on: / schedule:
- `.github/workflows/nativeaot-fixtures.yml`: name: Source-built NativeAOT fixtures / on: / workflow_dispatch:
- `.github/workflows/pages.yml`: name: Documentation build / on: / workflow_dispatch:
- `.github/workflows/pr-readiness.yml`: name: PR readiness / on: / pull_request_target:
- `.github/workflows/pr-title.yml`: name: PR title / on: / pull_request:
- `.github/workflows/real-binary-layout.yml`: name: Real offline binary layout / on: / workflow_dispatch:
- `.github/workflows/real-browser.yml`: name: Real browser verification / on: / workflow_call:
- `.github/workflows/real-cutter.yml`: name: Real upstream Cutter verification / on: / workflow_dispatch:
- `.github/workflows/real-evm-interface.yml`: name: Real offline EVM interface / on: / workflow_dispatch:
- `.github/workflows/real-ghidra-windows.yml`: name: Real Ghidra Windows E2E / on: / repository_dispatch:
- `.github/workflows/real-go-binary.yml`: name: Real Go binary metadata / on: / workflow_dispatch:
- `.github/workflows/real-hopper-linux.yml`: name: Real Hopper Linux E2E / on: / workflow_dispatch:
- `.github/workflows/real-hopper.yml`: name: Real Hopper E2E / on: / workflow_dispatch:
- `.github/workflows/real-javascript-recovery.yml`: name: Real JavaScript recovery / on: / workflow_call:
- `.github/workflows/real-packet-capture.yml`: name: Real packet capture / on: / workflow_dispatch:
- `.github/workflows/real-recorded-crash.yml`: name: Real recorded crash evidence / on: / workflow_dispatch:
- `.github/workflows/real-signal-recording.yml`: name: Real signal recording / on: / workflow_dispatch:

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

- GitHub: https://github.com/morluto/rea
- README: https://github.com/morluto/rea#readme
