---
layout: post
title: "EHR6 하네스 엔지니어링 세팅 점검 보고서"
date: 2026-03-19 14:45:00 +0900
categories: [ai]
tags: [ai, harness-engineering, codex, claude-code, setup, report, software-engineering]
---

> 원본 문서: `C:\Users\kms\Desktop\dev\EHR_6\docs\HARNESS-SETUP-REPORT.md`
> 게시 목적: EHR6 저장소의 하네스 엔지니어링 세팅 상태를 블로그용으로 정리

# EHR6 하네스 엔지니어링 세팅 점검 보고서

> 점검일: 2026-03-19
> 작성: Claude Code (Opus 4.6)

---

## 1. 하네스 전체 흐름 요약

```
┌─────────────────────────────────────────────────────────────────────┐
│                    EHR6 HARNESS SYSTEM                               │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ 1. GUARDRAILS (가드레일) — "하지 마"                          │   │
│  │    CLAUDE.md 핵심 규칙 6개 + core-beliefs 10개 금지사항       │   │
│  │    Hooks: block-dangerous.sh (rm -rf, DROP TABLE 등 차단)     │   │
│  │    ehr-frontend/CLAUDE.md, ehr-backend/CLAUDE.md 모듈별 규칙  │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                            ↓                                         │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ 2. PLAN & SPEC (계획·명세) — "먼저 써"                       │   │
│  │    /sdd {feature} → docs/exec-plans/active/{feature}.md      │   │
│  │    @legacy-analyst → Oracle 스키마 + 레거시 코드 분석         │   │
│  │    /oracle-mapper {table} → Mapper+DTO 자동 생성 절차         │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                            ↓                                         │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ 3. IMPLEMENTATION (구현) — "명세대로 만들어"                   │   │
│  │    @implementer → Mapper XML → DTO → Service → Controller    │   │
│  │                   → Route Handler → *Client.tsx + IBSheet     │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                            ↓                                         │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ 4. VERIFICATION LOOPS (검증) — "맞는지 확인해"                │   │
│  │    /tdd {feature} → RED → GREEN → REFACTOR                   │   │
│  │    @qa-tester → JUnit 5 + Playwright 테스트                   │   │
│  │    @sql-reviewer → Oracle 컬럼명·유효기간 정합성 점검         │   │
│  │    @security-reviewer → SQL Injection, XSS, 시크릿 점검      │   │
│  │    Hooks: post-edit-lint.sh → 수정 후 lint/build 리마인더     │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                            ↓                                         │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ 5. OBSERVABILITY (관측) — "상태를 기록해"                     │   │
│  │    QUALITY_SCORE.md → 도메인별 품질 등급 (A~F)               │   │
│  │    tech-debt-tracker.md → 기술 부채 추적                      │   │
│  │    exec-plans/active/ → 진행 상황 기록                        │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### 표준 워크플로 (새 기능 구현 시)

```
요청 수신
  ↓
/sdd {feature}          ← SDD: 명세 작성
  ├── @legacy-analyst   ← Oracle·레거시 분석
  └── exec-plans/active/{feature}.md 생성
  ↓
/tdd {feature}          ← TDD: 테스트 먼저
  ├── @qa-tester        ← 테스트 작성 (RED)
  └── JUnit / Playwright 실패 확인
  ↓
@implementer            ← 코드 구현 (GREEN)
  └── Mapper → DTO → Service → Controller → Frontend
  ↓
검증 루프               ← 자동 + 수동 검증
  ├── @qa-tester        ← 테스트 실행 (PASS 확인)
  ├── @sql-reviewer     ← SQL 정합성
  ├── @security-reviewer ← 보안
  └── Hooks             ← lint/build 리마인더
  ↓
완료
  ├── exec-plans/completed/로 이동
  └── QUALITY_SCORE.md 등급 갱신
```

---

## 2. 파일 인벤토리 — 무엇이 어디에 있는가

### 2.1 가이드라인 파일 (에이전트가 읽는 규칙)

| 파일 | 줄 수 | 역할 | 도구 호환 | 상태 |
|------|------|------|----------|------|
| `CLAUDE.md` (루트) | 135줄 | 프로젝트 맵 + 워크플로 + 핵심 규칙 | Claude Code | ✅ 완성 |
| `AGENTS.md` (루트) | ? | Codex 가이드라인 | OpenAI Codex | ✅ 존재 (미확인) |
| `ARCHITECTURE.md` | 171줄 | 레이어 모델, 의존성, 데이터 흐름 | 공통 | ✅ 완성 |
| `ehr-frontend/CLAUDE.md` | 57줄 | 프론트엔드 특화 규칙 | Claude Code | ✅ 완성 |
| `ehr-backend/CLAUDE.md` | 84줄 | 백엔드 특화 규칙 | Claude Code | ✅ 완성 |

### 2.2 설계 문서 (왜 그렇게 하는가)

| 파일 | 줄 수 | 역할 | 상태 |
|------|------|------|------|
| `docs/design-docs/core-beliefs.md` | 78줄 | 황금 원칙 10개 + 금지사항 10개 | ✅ 완성 |
| `docs/design-docs/index.md` | 21줄 | 설계 문서 목차 + ADR 4개 | ✅ 완성 |
| `docs/HARNESS-ENGINEERING.md` | 960줄 | 하네스 방법론 전체 가이드 | ✅ 완성 |
| `docs/EHR6-MASTER-PLAN.md` | 672줄 | Phase 0~10 마스터 플랜 | ✅ 완성 |

### 2.3 운영 문서 (지금 어떤 상태인가)

| 파일 | 줄 수 | 역할 | 상태 |
|------|------|------|------|
| `docs/QUALITY_SCORE.md` | 44줄 | 도메인별 품질 등급 | ✅ 완성 |
| `docs/exec-plans/active/phase1-tsys-screens.md` | 56줄 | Phase 1 진행 상황 | 🔄 Step 4 대기 |
| `docs/exec-plans/tech-debt-tracker.md` | 30줄 | 기술 부채 4건 추적 | ✅ 완성 |
| `docs/product-specs/index.md` | 26줄 | 화면별 요구사항 목차 | ✅ 완성 |

### 2.4 하네스 인프라 (.claude/)

| 파일 | 역할 | 유형 | 상태 |
|------|------|------|------|
| `.claude/settings.json` | Hooks 등록 (Pre + Post) | 설정 | ✅ 완성 |
| `.claude/hooks/block-dangerous.sh` | 치명적 명령 차단 (6종) | PreToolUse | ✅ 테스트 완료 |
| `.claude/hooks/post-edit-lint.sh` | 수정 후 lint/build 리마인더 | PostToolUse | ✅ 테스트 완료 |
| `.claude/agents/legacy-analyst.md` | 레거시 분석 (Read-only) | Subagent | ✅ 완성 |
| `.claude/agents/implementer.md` | 코드 구현 (스키마 드리븐) | Subagent | ✅ 완성 |
| `.claude/agents/qa-tester.md` | 테스트 작성/실행 (TDD) | Subagent | ✅ 완성 |
| `.claude/agents/sql-reviewer.md` | Oracle SQL 정합성 (Read-only) | Subagent | ✅ 완성 |
| `.claude/agents/security-reviewer.md` | 보안 리뷰 (Read-only) | Subagent | ✅ 완성 |
| `.claude/skills/sdd/SKILL.md` | `/sdd` 명세 작성 워크플로 | Skill | ✅ 완성 |
| `.claude/skills/tdd/SKILL.md` | `/tdd` 테스트 우선 워크플로 | Skill | ✅ 완성 |
| `.claude/skills/oracle-mapper/SKILL.md` | `/oracle-mapper` Mapper 생성 | Skill | ✅ 완성 |
| `.claude/skills/legacy-analyze/SKILL.md` | `/legacy-analyze` 분석 포크 | Skill | ✅ 완성 |
| `.claude/launch.json` | frontend/backend 서버 실행 설정 | 설정 | ✅ 완성 |

---

## 3. Hooks 상세 — 무엇을 차단/알림하는가

### 3.1 PreToolUse: block-dangerous.sh

| # | 차단 대상 | 정규식 | 피드백 메시지 |
|---|----------|--------|-------------|
| 1 | `rm -rf` / `rm -f` | `rm\s+-(r\|f\|rf\|fr)\s` | 파일 시스템 보호 |
| 2 | `DROP TABLE` / `TRUNCATE` | `DROP\s+TABLE\|TRUNCATE\s+TABLE` | DB 파괴 방지 |
| 3 | `DELETE FROM` (WHERE 없음) | `DELETE\s+FROM\s+\w+\s*$` | 전체 행 삭제 방지 |
| 4 | `git push --force` | `git\s+push\s+.*--force` | 원격 히스토리 보호 |
| 5 | `git reset --hard` | `git\s+reset\s+--hard` | 로컬 변경 보호 |
| 6 | `git clean -f` | `git\s+clean\s+-(f\|fd\|df)` | 미추적 파일 보호 |
| 7 | `ALTER TABLE` | `ALTER\s+TABLE` | Oracle 스키마 보호 |

**동작**: exit 2 → Bash 명령 차단 + stderr 메시지가 Claude에게 피드백

### 3.2 PostToolUse: post-edit-lint.sh

| 파일 패턴 | 리마인더 내용 |
|----------|-------------|
| `*.ts, *.tsx, *.js, *.jsx` | `npm run lint` 실행 권장 |
| `*.java` | `./gradlew build` 실행 권장 |
| `*Mapper.xml` | sql-reviewer로 점검 권장 |

**동작**: exit 0 항상 (차단 아님, 피드백만 제공)

---

## 4. Agents 상세 — 누가 무슨 역할인가

| Agent | 권한 | 모델 | 파일 수정 | 핵심 역할 |
|-------|------|------|----------|----------|
| **legacy-analyst** | Read, Grep, Glob, Bash | Sonnet | ❌ 금지 | Oracle 스키마 분석, 레거시 코드 참조, 영향도 정리 |
| **implementer** | Read, Grep, Glob, Edit, Write, Bash | Sonnet | ✅ 가능 | 명세 기반 코드 구현 (Mapper→DTO→Service→Controller→Frontend) |
| **qa-tester** | Read, Grep, Glob, Edit, Write, Bash | Sonnet | ✅ 가능 | 테스트 작성/실행, 커버리지 보고 |
| **sql-reviewer** | Read, Grep, Glob, Bash | Sonnet | ❌ 금지 | Mapper XML ↔ Oracle 스키마 정합성 검증 |
| **security-reviewer** | Read, Grep, Glob, Bash | Sonnet | ❌ 금지 | SQL Injection, XSS, 인증, 시크릿 점검 |

**설계 원칙:**
- Read-only 에이전트 (analyst, sql-reviewer, security-reviewer)에는 `disallowedTools: Edit, Write` 명시
- 구현/테스트 에이전트만 파일 수정 가능
- 모든 에이전트에 Oracle 테이블 규칙(ENTER_CD, 컬럼명 등) 내장

---

## 5. Skills 상세 — 어떤 워크플로가 있는가

| Skill | 명령어 | 인자 | 하네스 위치 | 연동 에이전트 |
|-------|--------|------|-----------|-------------|
| **sdd** | `/sdd {feature}` | 기능명 | Plan & Spec | @legacy-analyst |
| **tdd** | `/tdd {feature}` | 기능명 | Verification Loops | @qa-tester |
| **oracle-mapper** | `/oracle-mapper {table}` | 테이블명 | Implementation | @sql-reviewer |
| **legacy-analyze** | `/legacy-analyze {target}` | 대상 | Plan & Spec | @legacy-analyst (fork) |

---

## 6. 문서 일관성 점검 — 불일치/누락 발견

### 6.1 발견된 불일치

| # | 위치 | 이슈 | 심각도 | 설명 |
|---|------|------|--------|------|
| 1 | `EHR6-MASTER-PLAN.md` §1-2 | TSYS**002** 언급 | Medium | 실제는 TSYS005 사용. 마스터 플랜이 오래된 정보 |
| 2 | `EHR6-MASTER-PLAN.md` §5.1 | Mapper 예시에 `GRP_CD, GRP_NM` 사용 | Medium | 실제 컬럼은 GRCODE_CD, GRCODE_NM |
| 3 | `EHR6-MASTER-PLAN.md` §5.1 | `ENTER_CD = #{enterCd}` (TSYS001에서) | Medium | TSYS001에는 ENTER_CD 없음 |
| 4 | `EHR6-MASTER-PLAN.md` §5.2 | `enterCd=0001` 사용 | Low | 실제는 "HR", "IJ", "DEMO" |
| 5 | `design-docs/index.md` | ADR-004에 "TSYS003 아닌" 표현만 있고 상세 없음 | Low | 결정 근거 문서 부재 |
| 6 | `QUALITY_SCORE.md` | 하네스 관련 점수(TDD 커버리지, SDD 준수율) 미포함 | Low | 관측 가능성 부족 |
| 7 | `CLAUDE.md` §MVP | "🔄 TSYS 시스템관리" — SDD/TDD 적용 여부 미기록 | Info | 워크플로 적용 추적 미흡 |

### 6.2 누락 항목

| # | 항목 | 설명 | 우선순위 |
|---|------|------|---------|
| 1 | `docs/exec-plans/active/` 디렉토리 비어있음 | `phase1-tsys-screens.md`만 존재. SDD 워크플로의 산출물 저장소인데 사실상 미활용 | High |
| 2 | 테스트 인프라 미구축 | Backend JUnit 5 테스트 디렉토리, Frontend Playwright 설정 자체가 없을 수 있음 | High |
| 3 | `docs/references/` 비어있음 | llms.txt (IBSheet7, Oracle 등 외부 참조) 미작성 | Medium |
| 4 | `docs/generated/` 비어있음 | DB 스키마 자동 생성 문서 없음 | Medium |
| 5 | `AGENTS.md` 내용 미확인 | CLAUDE.md와 동기화 필요 (SDD/TDD/Subagent 반영 여부) | Medium |
| 6 | Playwright 설정 | `ehr-frontend/playwright.config.ts` 존재 여부 미확인 | Medium |
| 7 | JUnit 5 테스트 디렉토리 | `ehr-backend/src/test/` 구조 미확인 | Medium |
| 8 | `MEMORY.md` (Claude 장기 기억) | 프로젝트 컨텍스트 저장 상태 — 별도 관리 중 | Info |

---

## 7. 기술 부채 현황

| # | 영역 | 설명 | 심각도 | 상태 |
|---|------|------|--------|------|
| TD-001 | Backend/SysCode | TSYS005_SEQ.NEXTVAL 시퀀스 존재 여부 미검증 | High | 🔴 미해결 |
| TD-002 | Frontend/SysCodesClient | 엑셀 다운로드 미구현 (placeholder) | Medium | 🟡 미구현 |
| TD-003 | Backend/CommonCodeMapper | TSYS003 → TSYS005 전환 필요 가능성 | Medium | 🟡 확인 필요 |
| TD-004 | Frontend/Login | enterCd 하드코딩 확인 필요 | Low | 🟡 확인 필요 |
| **TD-005** | **Docs/MASTER-PLAN** | **마스터 플랜 §5 코드 예시 오래된 정보 (TSYS002, GRP_CD)** | **Medium** | **🔴 신규** |
| **TD-006** | **Test/Backend** | **JUnit 5 테스트 인프라 미구축** | **High** | **🔴 신규** |
| **TD-007** | **Test/Frontend** | **Playwright E2E 테스트 인프라 미구축** | **High** | **🔴 신규** |

---

## 8. Phase 1 진행 상황 (현재 위치)

```
Phase 1: TSYS 시스템관리
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[x] Step 1: Backend API 스캐폴딩          ██████████ 100%
[x] Step 2: Frontend IBSheet 화면         ██████████ 100%
[x] Step 3: SysCodeMapper.xml TSYS005     ██████████ 100%
[ ] Step 4: 런타임 검증                    ░░░░░░░░░░   0%  ← 여기!
[ ] Step 5: 에러 핸들링 & 엣지케이스       ░░░░░░░░░░   0%
```

**Step 4에서 해야 할 것:**
1. Backend 재시작 후 `/api/sys/codes/groups` API 응답 확인
2. Frontend에서 실제 IBSheet 데이터 표시 확인
3. CRUD 시나리오 테스트 (추가/수정/삭제)
4. TSYS005_SEQ.NEXTVAL 시퀀스 존재 확인 (TD-001)

---

## 9. 즉시 해야 할 작업 목록

### 우선순위 1: 런타임 검증 (Phase 1 Step 4)

| # | 작업 | 예상 소요 |
|---|------|----------|
| 1 | Backend 재시작 + TSYS005 API 테스트 | 10분 |
| 2 | TSYS005_SEQ 시퀀스 존재 확인 | 5분 |
| 3 | Frontend 데이터 표시 확인 | 10분 |
| 4 | CRUD 전체 시나리오 테스트 | 20분 |

### 우선순위 2: 테스트 인프라 구축 (TD-006, TD-007)

| # | 작업 | 예상 소요 |
|---|------|----------|
| 1 | JUnit 5 테스트 디렉토리 + 첫 테스트 | 30분 |
| 2 | Playwright 설정 + 첫 E2E 테스트 | 30분 |

### 우선순위 3: 문서 정합성 (TD-005)

| # | 작업 | 예상 소요 |
|---|------|----------|
| 1 | EHR6-MASTER-PLAN.md §5 코드 예시 수정 (TSYS002→005, GRP_CD→GRCODE_CD) | 15분 |
| 2 | AGENTS.md에 SDD/TDD/Subagent 반영 | 20분 |
| 3 | QUALITY_SCORE.md에 하네스 메트릭 추가 | 10분 |

---

## 10. 하네스 성숙도 자가 진단

| 항목 | 상태 | 점수 |
|------|------|------|
| **CLAUDE.md** 존재 (~100줄 맵 역할) | ✅ 135줄, 맵+워크플로 포함 | 10/10 |
| **ARCHITECTURE.md** 존재 | ✅ 171줄, 레이어+의존성+데이터흐름 | 10/10 |
| **core-beliefs.md** 존재 | ✅ 78줄, 원칙 10개+금지 10개 | 10/10 |
| **Hooks (PreToolUse)** 설정 | ✅ 7개 차단 규칙 | 9/10 |
| **Hooks (PostToolUse)** 설정 | ✅ 3개 리마인더 | 7/10 |
| **Subagent** 정의 | ✅ 5개 역할 분리 | 9/10 |
| **Skills** 정의 | ✅ 4개 워크플로 | 8/10 |
| **exec-plans/** 운영 | 🔄 1개만 존재 | 5/10 |
| **테스트 인프라** (JUnit + Playwright) | ❌ 미구축 | 0/10 |
| **QUALITY_SCORE** 운영 | 🔄 존재하나 하네스 메트릭 없음 | 4/10 |
| **기술 부채 추적** | ✅ 7건 추적 중 | 7/10 |
| **하위 CLAUDE.md** (frontend + backend) | ✅ 2개 완성 | 10/10 |
| | | |
| **총점** | | **89/120 (74%)** |

### 등급: **B — 대부분 구조 완성, 테스트 인프라와 실행 검증 미완**

```
A (90%+): 프로덕션 레벨 하네스 — 모든 구성요소 가동 중
B (70%+): 구조 완성 — 검증 루프와 관측 강화 필요    ← 현재
C (50%+): 기본 골격 — 핵심 구성요소 다수 누락
D (30%+): 초기 — CLAUDE.md 정도만 있는 상태
F (<30%): 하네스 없음
```

---

## 부록: 전체 파일 트리 (.claude/ + docs/)

```
EHR_6/
├── CLAUDE.md                    (135줄) 프로젝트 맵
├── AGENTS.md                    (?)     Codex 가이드라인
├── ARCHITECTURE.md              (171줄) 아키텍처
│
├── .claude/
│   ├── settings.json            Hooks 등록
│   ├── launch.json              서버 실행 설정
│   ├── hooks/
│   │   ├── block-dangerous.sh   PreToolUse: 치명적 명령 차단
│   │   └── post-edit-lint.sh    PostToolUse: 수정 후 리마인더
│   ├── agents/
│   │   ├── legacy-analyst.md    레거시 분석 (Read-only)
│   │   ├── implementer.md       코드 구현
│   │   ├── qa-tester.md         테스트 (TDD)
│   │   ├── sql-reviewer.md      SQL 점검 (Read-only)
│   │   └── security-reviewer.md 보안 리뷰 (Read-only)
│   └── skills/
│       ├── sdd/SKILL.md         /sdd 명세 작성
│       ├── tdd/SKILL.md         /tdd 테스트 우선
│       ├── oracle-mapper/SKILL.md /oracle-mapper 생성
│       └── legacy-analyze/SKILL.md /legacy-analyze 분석
│
├── ehr-frontend/
│   └── CLAUDE.md                (57줄) 프론트엔드 규칙
│
├── ehr-backend/
│   └── CLAUDE.md                (84줄) 백엔드 규칙
│
└── docs/
    ├── HARNESS-ENGINEERING.md   (960줄) 하네스 방법론
    ├── EHR6-MASTER-PLAN.md      (672줄) 마스터 플랜
    ├── QUALITY_SCORE.md         (44줄)  품질 등급
    ├── HARNESS-SETUP-REPORT.md  이 파일
    ├── design-docs/
    │   ├── core-beliefs.md      (78줄)  황금 원칙
    │   └── index.md             ADR 목차
    ├── exec-plans/
    │   ├── active/
    │   │   └── phase1-tsys-screens.md  Phase 1 진행 상황
    │   └── tech-debt-tracker.md       기술 부채
    └── product-specs/
        └── index.md             화면 요구사항 목차
```
