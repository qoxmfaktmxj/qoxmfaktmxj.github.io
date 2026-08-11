---
layout: post
title: "Repo Deep Dive: microsoft/markitdown"
date: 2026-08-12 07:57:37 +0900
categories: [github-repo-analysis]
tags: [github, architecture, backend, open-source, deep-dive]
repo: microsoft/markitdown
stars: 173166
analyzed_at: 2026-08-12
---

## 1. 이 repo가 중요한 이유

Microsoft가 개발한 LLM 친화적 파일 변환 도구로, 다양한 문서 형식(PDF, Office, 이미지, 오디오 등)을 Markdown으로 변환하여 AI 파이프라인에 최적화된 구조화된 텍스트를 제공합니다. AutoGen 팀이 주도하며 173K+ 스타를 받은 프로덕션급 오픈소스 프로젝트입니다.

## 2. 한 문장 요약

다양한 파일 형식을 LLM이 이해하기 쉬운 Markdown으로 변환하는 경량 Python 유틸리티로, 문서 구조(제목, 표, 링크 등)를 보존하면서 AI 텍스트 분석 파이프라인에 최적화되어 있습니다.

## 3. 제품/문제 정의

LLM 기반 애플리케이션에서 다양한 문서 형식(PDF, Word, Excel, PowerPoint, 이미지, 오디오 등)을 처리할 때 원본 구조와 의미를 잃지 않으면서 효율적으로 변환해야 하는 문제. 기존 textract는 구조 보존에 약하고, 각 형식별로 별도 라이브러리를 관리해야 하는 복잡성이 있습니다.

## 4. 아키텍처 구조

플러그인 기반 모듈식 아키텍처로 설계됨: (1) 핵심 MarkItDown 클래스가 파일 타입 감지 및 라우팅 담당, (2) 형식별 컨버터(PDF, DOCX, PPTX, XLSX, 이미지, 오디오 등)가 독립적 모듈로 구현, (3) 선택적 의존성으로 필요한 형식만 설치 가능, (4) LLM 클라이언트 통합(이미지 설명, 오디오 전사, OCR), (5) 플러그인 시스템으로 3rd-party 확장 지원, (6) Azure Document Intelligence/Content Understanding 같은 클라우드 서비스 옵션 제공.

## 5. 핵심 모듈

1. markitdown (핵심): 메인 변환 엔진, 파일 타입 감지, 컨버터 라우팅 / 2. PDF 컨버터: pdfplumber 기반 텍스트/표 추출 / 3. Office 컨버터: python-docx, python-pptx, openpyxl로 Word/PowerPoint/Excel 처리 / 4. 이미지 컨버터: EXIF 메타데이터 추출, LLM Vision으로 이미지 설명 생성 / 5. 오디오 컨버터: 음성 전사(OpenAI Whisper 등) / 6. HTML/텍스트 컨버터: BeautifulSoup, CSV/JSON/XML 파싱 / 7. markitdown-ocr: LLM Vision 기반 OCR 플러그인 / 8. markitdown-mcp: Model Context Protocol 서버 / 9. 플러그인 시스템: 동적 로딩 및 확장 메커니즘.

## 6. 백엔드 개발자가 배울 점

1. 선택적 의존성 패턴: [all], [pdf], [docx] 등으로 사용자가 필요한 것만 설치하도록 설계하여 번들 크기 최소화 / 2. 추상화 계층: 각 형식별 컨버터가 공통 인터페이스 구현으로 새 형식 추가 용이 / 3. LLM 통합 패턴: llm_client, llm_model 파라미터로 OpenAI, Azure 등 다양한 제공자 지원 / 4. 보안 우선: 문서에서 권한 상승 위험을 명시하고 입력 검증 강조 / 5. 클라우드 옵션 제공: 로컬 처리와 클라우드 서비스(Azure Content Understanding)를 선택 가능하게 설계 / 6. 플러그인 아키텍처: 핵심은 가볍게 유지하고 기능 확장은 플러그인으로 / 7. 다중 출력 형식: CLI, 파이프라인, 프로그래매틱 API 모두 지원 / 8. 토큰 효율성: Markdown 선택으로 LLM 입력 비용 절감.

## 7. 내 프로젝트에 훔쳐올 패턴

1. 형식별 컨버터 팩토리 패턴: 파일 확장자/MIME 타입으로 적절한 컨버터 자동 선택 / 2. 선택적 의존성 그룹: pyproject.toml에서 extras 정의로 사용자 맞춤 설치 / 3. 플러그인 동적 로딩: entry_points로 3rd-party 플러그인 자동 발견 및 로드 / 4. LLM 클라이언트 추상화: 특정 제공자에 종속되지 않는 인터페이스 설계 / 5. 구조 보존 변환: 원본 문서의 계층 구조(제목 레벨, 표 형식, 리스트)를 Markdown으로 매핑 / 6. 메타데이터 추출: EXIF, 문서 속성 등을 YAML 프론트매터로 / 7. 스트림 처리: convert_stream()으로 메모리 효율적 처리 / 8. 다중 백엔드 지원: 로컬, Azure, 클라우드 서비스를 조건부로 사용.

## 8. 주의할 점 / 안티패턴

1. 보안: 문서에서 명시한 대로 I/O 권한이 프로세스 권한과 동일하므로 신뢰할 수 없는 입력에 대해 반드시 검증 필요 / 2. 의존성 폭증: [all] 설치 시 많은 라이브러리가 필요하므로 프로덕션 환경에서는 필요한 것만 선택 설치 / 3. 외부 서비스 의존: LLM 기반 기능(이미지 설명, 음성 전사)은 API 호출로 비용 발생 및 지연 가능 / 4. 형식 호환성: 복잡한 문서(고급 레이아웃, 임베드된 객체)는 완벽하게 변환되지 않을 수 있음 / 5. 성능: 대용량 파일(수백 MB PDF)은 메모리 사용량 증가 및 처리 시간 길어짐 / 6. 플러그인 신뢰성: 3rd-party 플러그인은 품질 보증 없으므로 신중히 선택 / 7. 버전 호환성: 의존 라이브러리(pdfplumber, python-docx 등)의 업데이트로 인한 호환성 문제 가능성.

## 9. vibe-grid / vibe-hr / jarvis / ehr-harness에 적용할 아이디어

1. 문서 기반 RAG 시스템: 다양한 형식의 기업 문서를 Markdown으로 변환하여 벡터 DB에 저장 / 2. AI 에이전트 입력 전처리: AutoGen 같은 에이전트 프레임워크에 문서 입력 시 구조 보존 변환 / 3. 멀티모달 LLM 파이프라인: 이미지, 오디오, 비디오를 포함한 문서를 통합 처리 / 4. 엔터프라이즈 문서 자동화: Office 문서 대량 변환 후 검색, 분류, 요약 자동화 / 5. 하이브리드 처리 아키텍처: 로컬 처리(빠름, 저비용)와 Azure Content Understanding(고품질)을 문서 복잡도에 따라 선택 / 6. 플러그인 기반 확장: 특정 도메인(의료, 법률) 문서 처리를 위한 커스텀 플러그인 개발 / 7. 마이크로서비스 통합: Docker 지원으로 컨테이너화된 변환 서비스 구축 / 8. 토큰 최적화: Markdown 형식으로 LLM API 비용 절감 (JSON 대비 30-40% 토큰 감소).

## 10. Source Links

['https://github.com/microsoft/markitdown', 'https://github.com/microsoft/markitdown/tree/main/packages/markitdown', 'https://github.com/microsoft/markitdown/tree/main/packages/markitdown-ocr', 'https://github.com/microsoft/markitdown/tree/main/packages/markitdown-mcp', 'https://github.com/microsoft/markitdown/tree/main/packages/markitdown-sample-plugin', 'https://pypi.org/project/markitdown/', 'https://github.com/microsoft/autogen', 'https://learn.microsoft.com/azure/ai-services/content-understanding/', 'https://github.com/deanmalmgren/textract', 'https://github.com/topics/markitdown-plugin']
