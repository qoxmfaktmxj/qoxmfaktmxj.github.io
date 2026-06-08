---
layout: post
title: "Repo Deep Dive: affaan-m/ECC"
date: 2026-06-09 08:21:52 +0900
categories: [github-repo-analysis]
tags: [github, architecture, backend, open-source, deep-dive]
repo: affaan-m/ECC
stars: 210791
analyzed_at: 2026-06-09
---

## 1. 이 repo가 중요한 이유

`affaan-m/ECC`는 GitHub star 210,791개를 가진 대규모 오픈소스 프로젝트다. 많은 개발자가 선택한 프로젝트이므로 README, 구조, 설정 파일만 봐도 제품화와 운영 성숙도에 대한 단서를 얻을 수 있다.

## 2. 한 문장 요약

The agent harness performance optimization system. Skills, instincts, memory, security, and research-first development for Claude Code, Codex, Opencode, Cursor and beyond.

## 3. 제품/문제 정의

GitHub description: The agent harness performance optimization system. Skills, instincts, memory, security, and research-first development for Claude Code, Codex, Opencode, Cursor and beyond.

README 초기 신호:
- **Language:** English | [Português (Brasil)](docs/pt-BR/README.md) | [简体中文](README.zh-CN.md) | [繁體中文](docs/zh-TW/README.md) | [日本語](docs/ja-JP/README.md) | [한국어](docs/ko-KR/README.md) | [Türkçe](docs/tr/README.md) | [Рус
- # ECC
- ![ECC - the harness-native operator system for agentic work](assets/hero.png)
- [![Stars](https://img.shields.io/github/stars/affaan-m/ECC?style=flat)](https://github.com/affaan-m/ECC/stargazers)
- [![Forks](https://img.shields.io/github/forks/affaan-m/ECC?style=flat)](https://github.com/affaan-m/ECC/network/members)
- [![Contributors](https://img.shields.io/github/contributors/affaan-m/ECC?style=flat)](https://github.com/affaan-m/ECC/graphs/contributors)
- [![npm ecc-universal](https://img.shields.io/npm/dw/ecc-universal?label=ecc-universal%20weekly%20downloads&logo=npm)](https://www.npmjs.com/package/ecc-universal)
- [![npm ecc-agentshield](https://img.shields.io/npm/dw/ecc-agentshield?label=ecc-agentshield%20weekly%20downloads&logo=npm)](https://www.npmjs.com/package/ecc-agentshield)
- [![GitHub App Install](https://img.shields.io/badge/GitHub%20App-150%20installs-2ea44f?logo=github)](https://github.com/marketplace/ecc-tools)
- [![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
- ![Shell](https://img.shields.io/badge/-Shell-4EAA25?logo=gnu-bash&logoColor=white)
- ![TypeScript](https://img.shields.io/badge/-TypeScript-3178C6?logo=typescript&logoColor=white)

## 4. 아키텍처 구조

Primary language는 `JavaScript`이고 언어 구성은 다음과 같다.

- **JavaScript**: 62.0%
- **Rust**: 28.7%
- **Python**: 5.2%
- **Shell**: 3.0%
- **TypeScript**: 0.9%
- **Swift**: 0.1%
- **CSS**: 0.1%
- **PowerShell**: 0.0%

상위 디렉터리 분포:
- `docs/`: 355 files
- `commands/`: 84 files
- `agents/`: 64 files
- `assets/`: 37 files
- `<root files>/`: 27 files
- `contexts/`: 3 files
- `config/`: 1 files

## 5. 핵심 모듈

- `.github/workflows/ci.yml`: name: CI / on: / push:
- `.github/workflows/maintenance.yml`: name: Scheduled Maintenance / on: / schedule:
- `.github/workflows/monthly-metrics.yml`: name: Monthly Metrics Snapshot / on: / schedule:
- `.github/workflows/release.yml`: name: Release / on: / push:
- `.github/workflows/reusable-release.yml`: name: Reusable Release Workflow / on: / workflow_call:
- `.github/workflows/reusable-test.yml`: name: Reusable Test Workflow / on: / workflow_call:
- `.github/workflows/reusable-validate.yml`: name: Reusable Validation Workflow / on: / workflow_call:
- `.github/workflows/supply-chain-watch.yml`: name: Supply-Chain Watch / on: / schedule:
- `.opencode/package.json`: { / "name": "ecc-universal", / "version": "2.0.0-rc.1",
- `CHANGELOG.md`: # Changelog / ## 2.0.0-rc.1 - 2026-04-28 / ### Highlights
- `CONTRIBUTING.md`: # Contributing to Everything Claude Code / Thanks for wanting to contribute! This repo is a community resource for Claude Code users. / ## Table of Contents
- `SECURITY.md`: # Security Policy / ## Supported Versions / | Version | Supported          |
- `docs/es/CHANGELOG.md`: # Registro de Cambios / ## 2.0.0-rc.1 - 2026-04-28 / ### Destacados
- `docs/es/CONTRIBUTING.md`: # Contribuir a Everything Claude Code / ¡Gracias por querer contribuir! Este repositorio es un recurso comunitario para usuarios de Claude Code. / ## Tabla de Contenidos
- `docs/es/SECURITY.md`: # Política de Seguridad / ## Versiones Soportadas / | Versión | Soportada          |
- `docs/ja-JP/CHANGELOG.md`: # 変更履歴 / ## 2.0.0-rc.1 - 2026-04-28 / ### ハイライト
- `docs/ja-JP/CONTRIBUTING.md`: # Everything Claude Codeに貢献する / 貢献いただきありがとうございます！このリポジトリはClaude Codeユーザーのためのコミュニティリソースです。 / ## 目次
- `docs/ja-JP/SECURITY.md`: # セキュリティポリシー / ## サポートバージョン / | バージョン | サポート状況 |

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

- GitHub: https://github.com/affaan-m/ECC
- README: https://github.com/affaan-m/ECC#readme
