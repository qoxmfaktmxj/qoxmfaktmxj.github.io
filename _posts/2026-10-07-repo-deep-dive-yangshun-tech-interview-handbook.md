---
layout: post
title: "Repo Deep Dive: yangshun/tech-interview-handbook"
date: 2026-10-07 10:29:38 +0900
categories: [github-repo-analysis]
tags: [github, architecture, backend, open-source, deep-dive]
repo: yangshun/tech-interview-handbook
stars: 143132
analyzed_at: 2026-10-07
---

## 1. 이 repo가 중요한 이유

143K+ 스타를 받은 이 프로젝트는 단순한 링크 모음이 아닌 '큐레이션된 고품질 콘텐츠'를 직접 제공함으로써 바쁜 엔지니어들이 효율적으로 기술 면접을 준비할 수 있게 한다. 100만 명 이상이 혜택을 받았으며, Blind 75 같은 검증된 학습 패턴을 기반으로 한다.

## 2. 한 문장 요약

알고리즘부터 시스템 디자인, 행동 면접, 이력서까지 기술 면접의 전 과정을 다루는 큐레이션된 무료 학습 핸드북으로, Docusaurus 기반 웹사이트와 모노레포 구조로 제공된다.

## 3. 제품/문제 정의

기술 면접 준비 시 ① 시간 부족으로 인한 비효율적 학습(수백 개 LeetCode 문제 풀이 강요), ② 알고리즘만 다루고 시스템 디자인/행동 면접/이력서 등 실무적 내용 부족, ③ 외부 링크만 모은 얕은 자료, ④ 면접 전 과정(지원→합격→협상)에 대한 통합 가이드 부재

## 4. 아키텍처 구조

pnpm 모노레포 구조 (pnpm-workspace.yaml) | apps/ (portal, website) + packages/ (tailwind-config, tsconfig) | Docusaurus 기반 정적 웹사이트 | TypeScript 메인 언어 (1.04M LOC) + JavaScript/Python/CSS 혼용 | GitHub Actions CI/CD (lint.yml, tsc.yml) | Discord/Twitter/Telegram 커뮤니티 연동

## 5. 핵심 모듈

① Grind 75 (Blind 75 진화판) - 패턴 기반 문제 세트 | ② 코딩 면접 체크리스트 - Do's & Don'ts | ③ 알고리즘 치트시트 - 주제별 분류 | ④ 이력서 가이드 - FAANG 레벨 | ⑤ 행동 면접 질문 DB | ⑥ 면접 준비 단계별 로드맵 | ⑦ Front End Interview Handbook (별도 사이트) | ⑧ 시스템 디자인 (외부 과정 연동)

## 6. 백엔드 개발자가 배울 점

① 콘텐츠 큐레이션의 가치 - 링크 모음보다 직접 작성한 고품질 콘텐츠가 훨씬 높은 engagement 생성 | ② 모노레포 + 모듈화 - 공유 설정(tsconfig, tailwind)으로 일관성 유지 | ③ 정적 생성 사이트(Docusaurus) - 빌드 시점 타입 체크(tsc.yml)로 품질 보증 | ④ 커뮤니티 중심 운영 - 다채널(Discord/Twitter/Telegram) 전략 | ⑤ 패턴 기반 학습 - 개별 문제보다 '패턴 인식'이 효율성 극대화 | ⑥ 점진적 진화 - Blind 75 → Grind 75로 지속적 개선

## 7. 내 프로젝트에 훔쳐올 패턴

① 패턴 기반 학습 프레임워크 - 알고리즘을 '유형별 패턴'으로 분류하여 전이 학습 극대화 | ② 큐레이션 전략 - '최소한의 정보로 최대 효과' 철학 | ③ 모노레포 + Docusaurus - 문서화 + 웹사이트 + 코드 예제를 하나의 저장소에서 관리 | ④ 다채널 커뮤니티 - Discord(실시간), Twitter(뉴스), Telegram(알림) 역할 분담 | ⑤ 제휴 마케팅 - AlgoMonster/Design Gurus와의 제휴로 수익화 | ⑥ 단계별 로드맵 - 초급→중급→고급 경로 명확화 | ⑦ 도메인별 분리 - Frontend는 별도 사이트로 관리하여 포커스 유지

## 8. 주의할 점 / 안티패턴

① 시스템 디자인 콘텐츠 미완성 - 외부 과정(ByteByteGo, Design Gurus)에 의존하고 있어 통합도 낮음 | ② 기여 가이드라인 부재 - 'Contributing.md'는 있으나 형식적이고 명확한 기준 없음 | ③ 콘텐츠 최신성 보증 부족 - 면접 트렌드 변화에 대한 주기적 업데이트 메커니즘 불명확 | ④ 언어별 예제 불균형 - TypeScript 중심(1.04M LOC)이라 Python/JavaScript 사용자 경험 차이 | ⑤ 과도한 외부 링크 - 자체 콘텐츠 강조하면서도 여전히 외부 과정 광고 많음 | ⑥ 모바일 최적화 - Docusaurus 기본 테마의 모바일 UX 개선 필요 | ⑦ 오프라인 버전 부재 - 인터넷 없이 학습 불가

## 9. vibe-grid / vibe-hr / jarvis / ehr-harness에 적용할 아이디어

① 기술 학습 플랫폼 개발 시 '패턴 기반 분류' 도입 - 개별 항목보다 메타 구조 설계 우선 | ② 모노레포 구조 채택 - 공유 설정(tsconfig, tailwind-config)으로 일관성 유지 | ③ Docusaurus + GitHub Pages 조합 - 문서화 + 웹사이트 + 커뮤니티를 하나로 통합 | ④ CI/CD 파이프라인 - lint.yml + tsc.yml로 PR 단계에서 품질 보증 | ⑤ 다채널 커뮤니티 전략 - 단일 플랫폼 의존 피하고 Discord/Telegram 등 분산 | ⑥ 점진적 콘텐츠 확장 - MVP(Blind 75) → 확장(Grind 75) → 도메인 분리(Frontend) 순서 | ⑦ 제휴 수익화 - 자체 콘텐츠 무료 제공하되 관련 과정 제휴로 수익 창출 | ⑧ 기여자 관리 - OpenCollective로 투명한 후원 시스템 구축

## 10. Source Links

{'main_website': 'https://www.techinterviewhandbook.org/', 'github_repo': 'https://github.com/yangshun/tech-interview-handbook', 'frontend_handbook': 'https://www.frontendinterviewhandbook.com', 'grind_75': 'https://www.techinterviewhandbook.org/grind75/', 'coding_interview_guide': 'https://www.techinterviewhandbook.org/software-engineering-interview-guide/', 'resume_guide': 'https://www.techinterviewhandbook.org/resume/', 'behavioral_questions': 'https://www.techinterviewhandbook.org/behavioral-interview-questions/', 'algorithm_cheatsheet': 'https://www.techinterviewhandbook.org/algorithms/study-cheatsheet/', 'discord_community': 'https://discord.com/invite/usMqNaPczq', 'twitter': 'https://twitter.com/techinterviewhb', 'telegram': 'https://t.me/techinterviewhandbook', 'facebook': 'https://facebook.com/techinterviewhandbook', 'docusaurus': 'https://github.com/facebook/docusaurus', 'lago_dsa_library': 'https://github.com/yangshun/lago', 'algomonster': 'https://shareasale.com/r.cfm?b=1873647&u=3114753&m=114505&urllink=&afftrack=', 'grokking_coding_interview': 'https://www.designgurus.io/course/grokking-the-coding-interview?aff=kJSIoU', 'grokking_system_design': 'https://www.designgurus.io/course/grokking-the-system-design-interview?aff=kJSIoU', 'bytebytego_system_design': 'https://bytebytego.com?fpr=techinterviewhandbook', 'opencollective': 'https://opencollective.com/tech-interview-handbook'}
