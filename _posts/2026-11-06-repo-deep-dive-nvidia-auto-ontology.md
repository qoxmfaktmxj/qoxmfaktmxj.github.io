---
layout: post
title: "Repo Deep Dive: NVIDIA/auto-ontology — 데이터 의미를 검증 가능한 SQL 답변으로 잇는 온톨로지"
date: 2026-11-06 07:10:32 +0900
categories: [github-repo-analysis]
repo: NVIDIA/auto-ontology
trending_rank: 1
trending_period: daily
trending_checked_at: 2026-11-06 07:10:32 +0900
trending_url: https://github.com/trending?since=daily
---

2026년 11월 6일 07:10 KST에 확인한 GitHub Trending 일간 전체 언어 목록에서 `NVIDIA/auto-ontology`가 1위였다. 이 순위는 **저장소 선정 시점의 스냅샷**이며 발행·열람 시점의 실시간 순위를 뜻하지 않는다.

## 1. 프로젝트 소개

`Auto Ontology`는 NVIDIA가 공개한 데이터 분석용 오픈소스 프로젝트다. 관계형 데이터베이스의 테이블·컬럼·값을 읽어 비즈니스 용어와 관계를 표현하는 온톨로지 초안을 만들고, 사람이 이를 검토한 다음 자연어 질문을 SQL 질의와 답변으로 연결한다. 조직 안에서 같은 지표에 여러 정의가 있거나, 여러 테이블을 조인해야 하는 질문을 AI 에이전트가 처리할 때 쓰는 의미 계층이 핵심이다. 저장소 README는 기존에 소유한 시맨틱 모델을 대체하기보다 보완하는 도구라고 설명한다.

사용자는 웹 UI에서 용어 그래프를 살펴보고 채팅으로 질문할 수 있다. 외부 에이전트에는 읽기 전용 MCP 도구를 제공하고, 애플리케이션에는 인증된 REST API를 제공한다. 이 세 접근 경로가 같은 배포의 카탈로그와 질의 기능을 사용한다. 프로젝트는 Apache 2.0으로 배포되며, README와 기여 안내에 따르면 현재 외부 코드 기여는 받지 않고 통합 요청과 문제 보고는 이슈로 받는다.

## 2. 해결하려는 문제

데이터베이스 스키마만 아는 에이전트는 `매출`이 어느 컬럼의 합계인지, 반품을 포함하는지, 고객과 지역을 어떤 키로 연결해야 하는지 알기 어렵다. 질문에 맞아 보이는 SQL을 빠르게 생성해도 실제 조직의 지표 정의와 어긋나면 답변을 믿기 힘들다. 반대로 용어 설명만 따로 문서화하면 그 설명이 물리 컬럼·SQL 표현식·조인 경로와 연결되지 않아 질문을 실행할 때 다시 추측해야 한다.

Auto Ontology는 데이터 소스에서 스키마와 샘플 값을 수집하고, 용어를 컬럼에 매핑하며 관계와 SQL 속성을 묶어 의미 그래프의 초안을 만든다. 사용자가 설명과 SQL 속성을 수정·인증한 뒤 질문에 재사용하는 흐름이다. 이때 용어는 `고객`이나 `송장 행` 같은 개념, SQL 속성은 그 용어 아래에 검토된 계산식, 관계는 테이블 사이의 연결을 뜻한다. 질문 단계에서는 후보 용어와 속성을 검색하고 SQL을 작성한 뒤 필터 값과 질의를 점검한다. 따라서 단순히 데이터베이스의 테이블 목록을 프롬프트에 붙이는 방식과 달리, 무엇을 어떤 의미로 계산했는지 추적할 경로가 생긴다. 다만 자동 생성 초안 자체가 곧 공인된 정의는 아니며, README도 사람이 검사하고 인증하는 단계를 별도로 둔다.

## 3. 주요 기능

**의미 계층 생성과 검토.** 수집 서비스는 연결한 소스에서 스키마를 추출하고 컬럼을 프로파일링해 카탈로그를 구성한다. 이어 테이블별 용어를 제안해 컬럼에 연결하고, 키와 데이터를 통해 조인·브리지 테이블 관계를 추론한다. 생성된 용어·관계·SQL 속성은 Postgres에, 검색용 임베딩은 pgvector에 저장된다. UI에서 용어의 설명·동의어·관련 용어·매핑 컬럼·SQL 속성을 읽고 고칠 수 있다. README의 Wide World Importers 예시는 한 번의 컴파일 결과 31개 용어가 생긴 화면을 보여주지만, 이는 예시 데이터와 실행의 결과이지 모든 데이터베이스에서 얻는 고정값이 아니다.

**질문 가능 여부와 질의 결과.** MCP의 `check_readiness`는 컴파일된 의미 계층과 실제 SQL을 실행할 수 있는 데이터베이스 연결을 구분해 점검한다. 카탈로그에 데이터베이스 이름이 남아 있어도 연결이 끊겼다면 실행 가능하다고 보지 않는다. `check_answerable`은 질문의 개념이 온톨로지로 뒷받침되는지 선행 확인하고, `ask_question`은 답변·실행 SQL·결과 행을 별도 필드로 돌려준다. MCP 문서상 행은 최대 100개로 제한되며 `row_count`와 `truncated`로 생략 여부를 알린다. 웹 채팅에서는 SQL과 단계 추적을 보고 결과를 행·CSV·차트 형태로 확인할 수 있다. 표시된 자연어 답변만 읽는 것과 달리 실제 계산식을 함께 검사할 수 있다.

**에이전트·애플리케이션 연결.** MCP는 `search_terms`, `get_term`, `get_term_columns`, `get_term_sql_attributes`, `describe_table`처럼 의미 계층을 읽는 도구와 질문 도구를 제공한다. 공식 MCP 문서는 데이터베이스 원시 테이블을 무제한 탐색하거나 용어를 수정하는 도구는 노출하지 않는다고 명시한다. REST 경로 `POST /api/chat/completions`는 API 토큰 또는 세션 인증을 사용하며, 서버 전송 이벤트(SSE)에서 진행 단계, SQL, 최종 결과 또는 오류를 전달하고 `[DONE]`으로 끝난다. 대화 ID를 보내면 이전 완료 턴을 참조하는 후속 질문을 처리할 수 있지만, 같은 대화에서 앞 요청이 끝나기 전에 다음 요청을 보내면 충돌 응답이 난다.

**소스 연결 범위.** 공식 연결 문서는 PostgreSQL·MySQL·Databricks·Snowflake·ClickHouse·Trino·Apache Kyuubi·HeavyDB를 UI에서 추가할 수 있고, DuckDB·SQLite는 연결 문자열 방식만 제공한다고 구분한다. UI 관리 연결과 `CONNECTION_STRINGS`를 동시에 쓰면 답변과 수집이 서로 다른 연결 집합을 우선할 수 있어, 문서는 한 배포에서 한 방식을 선택하도록 권한다. 연결 범위와 인증 정보 처리까지 설정에 영향을 주므로 소스가 보인다는 사실만으로 수집과 질문이 같은 데이터에 접근한다고 가정해서는 안 된다.

## 4. 사용 방법과 동작 흐름

공식 빠른 시작은 Docker Compose v2, `uv`, NVIDIA API 키를 준비하고 Microsoft의 Wide World Importers 샘플 데이터베이스를 적재하는 경로다. 먼저 저장소를 복제하고 `.env.example`을 `.env`로 복사한다. `.env`에는 모델 API 키, 웹 인증 비밀값, 앱 URL, Postgres 비밀번호, 샘플 DB 연결 문자열, 관리자·pgAdmin 비밀번호를 설정한다. 예제 파일에 모델 역할별 자리표시자 키가 남아 있다면 실제 키로 바꾸거나 해당 줄을 제거해야 공통 키로 폴백한다. Compose가 호스트에 Postgres와 pgAdmin을 게시하므로 기본 비밀번호를 그대로 사용하지 말라는 것이 README의 안내다.

```bash
git clone https://github.com/NVIDIA/auto-ontology.git
cd auto-ontology
cp .env.example .env
# .env의 API 키·인증 비밀값·각 서비스 비밀번호·연결 문자열을 먼저 설정
docker compose up -d --wait postgres
git clone https://github.com/NVIDIA/auto-ontology-eval.git ../auto-ontology-eval
(cd ../auto-ontology-eval && uv sync && cp .env.example .env && \
  POSTGRES_PASSWORD='<.env에 설정한 Postgres 비밀번호>' \
  uv run python scripts/seed/seed_wwi.py --database-name wideworldimporters --drop)
docker compose up -d --build
```

샘플 적재 명령의 `--drop`은 대상 샘플 데이터베이스를 다시 만드는 절차이므로, 이미 데이터를 넣은 DB에 그대로 실행하는 명령으로 취급해서는 안 된다. 스택이 뜨면 `http://localhost:3000`에 접속해 설정한 관리자 계정으로 로그인한다. **Settings → Semantic Compilation**을 켜고 `Semantic compilation is ready` 상태를 확인한 다음 Chat에서 질문한다. README의 예시 질문은 2015년 6월 펜실베이니아에서 특정 상품의 매출을 묻는다. 문서에 제시된 답변은 `$588.80`, 송장 행 3개이며, 함께 나온 SQL은 `sales.invoicelines`에서 금액을 합산하고 송장·상품·고객·도시·주 테이블을 조인해 상품명·주·날짜를 필터링한다. 이 숫자는 공식 샘플 실행의 예시이지 이번 리뷰에서 스택을 가동해 재측정한 결과는 아니다. 결과를 볼 때는 답변의 금액만이 아니라 SQL의 합계 컬럼, 조인과 기간 경계를 함께 읽어야 한다.

외부 에이전트에 붙일 때는 배포된 웹 앱 주소를 지정해 공식 MCP 패키지를 실행하고, 클라이언트에는 서버의 `/mcp` URL을 등록한다. 클라이언트 재시작 후 사용자가 Auto Ontology 로그인 화면에서 인증한다. MCP 문서에 따르면 서버 자체에 공용 데이터베이스 자격 증명을 넣는 방식이 아니라 각 로그인 사용자의 권한으로 호출한다. 앱 코드에서 직접 질의할 때는 사용자 메뉴에서 발급한 API 토큰을 `x-api-key`로 보내고 SSE 스트림의 `result` 이벤트에서 `answer.response`와 `answer.sql_code`를 읽는다. `step`은 진행 상황, `error`는 실패, `[DONE]`은 스트림 종료이므로 마지막 줄을 JSON으로 파싱하면 안 된다.

## 5. 활용 사례

**영업 데이터의 용어가 포함된 질문.** 공식 Wide World Importers 예시에서 `revenue`, 상품, 지역이라는 입력을 온톨로지의 송장 행·재고 항목·주 등의 용어로 해석하고, 필요한 조인 경로를 따라 SQL을 실행한다. 매출 수치가 반환되면 사용자는 SQL과 결과 행을 대조할 수 있다. 같은 샘플 DB에는 광고비 데이터가 없으므로 광고 수익률을 묻는 공식 예시에서는 `check_answerable`이 광고비 개념의 부재를 드러내고, 에이전트가 다른 데이터 소스를 연결할지 묻는다. 이 사례는 답할 근거가 없는 질문에 임의의 수치를 채우지 않는 흐름을 보여준다.

**사내 에이전트에서 지표 정의 확인.** MCP 문서는 `활성 고객`의 뜻과 지난 분기 건수를 함께 묻는 예시를 든다. 에이전트는 먼저 `search_terms`·`get_term`으로 정의를 확인하고, `get_term_columns`와 SQL 속성 조회로 물리 데이터와 계산식을 살펴볼 수 있다. `check_readiness`와 `check_answerable`을 거쳐 `ask_question`을 호출하면 답변과 SQL·행을 각각 받아 후속 검토에 쓸 수 있다. 실제 `활성 고객` 정의와 답변 가능 여부는 연결한 조직의 데이터 및 인증된 온톨로지에 달려 있으며, 프로젝트가 공통 정의를 미리 제공한다는 뜻은 아니다.

**기존 분석 앱의 질의 화면.** 공식 Conversation API 문서의 예시처럼 `How many orders shipped last week?`를 인증된 API에 보내고 스트림에서 단계와 최종 답변을 화면에 표시할 수 있다. 후속 질문에 같은 `conversation_id`를 보내면 완료된 이전 턴의 질문·답변·SQL을 참고해 맥락을 해석한다. 결과 행과 오류는 그 재작성 입력에 포함되지 않는다. API가 반환한 `sql_code`를 사용자에게 보여주면 지난주라는 날짜 해석과 주문 집계 기준을 확인할 수 있다.

## 6. 참고 자료

- [NVIDIA/auto-ontology 저장소](https://github.com/NVIDIA/auto-ontology)
- [공식 README — 빠른 시작, 의미 계층과 질의 예시](https://github.com/NVIDIA/auto-ontology/blob/main/README.md)
- [MCP 서버 공식 문서 — 도구, 인증과 결과 필드](https://github.com/NVIDIA/auto-ontology/blob/main/docs/mcp.md)
- [Conversation API 문서 — SSE 이벤트와 대화 처리](https://github.com/NVIDIA/auto-ontology/blob/main/docs/conversation-api.md)
- [연결 문서 — 소스별 방식과 연결 우선순위](https://github.com/NVIDIA/auto-ontology/blob/main/docs/connections.md)
- [Wide World Importers 샘플 적재 저장소](https://github.com/NVIDIA/auto-ontology-eval)
