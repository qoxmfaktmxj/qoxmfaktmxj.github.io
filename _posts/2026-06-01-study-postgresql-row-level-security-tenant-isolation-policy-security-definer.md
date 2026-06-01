---
layout: post
title: "PostgreSQL Row-Level Security 실전: Tenant Isolation, Policy, SECURITY DEFINER로 멀티테넌트 데이터 격리를 설계하는 법"
date: 2026-06-01 11:50:00 +0900
categories: [sql]
tags: [study, sql, postgresql, row-level-security, rls, tenant-isolation, policy, security-definer, multi-tenant, authorization, operations]
permalink: /sql/2026/06/01/study-postgresql-row-level-security-tenant-isolation-policy-security-definer.html
---

## 배경: 멀티테넌트 SaaS의 가장 위험한 버그는 느린 쿼리보다 "다른 고객 데이터가 보이는 쿼리"다

PostgreSQL 운영에서 성능 문제는 눈에 잘 띈다. CPU가 오르고, slow query log가 쌓이고, `EXPLAIN`을 보면 plan이 이상하고, autovacuum이나 WAL 지표가 흔들린다. 그래서 팀도 비교적 빨리 반응한다. 그런데 멀티테넌트 SaaS에서 더 조용하지만 훨씬 치명적인 문제가 있다.

> **쿼리는 빠르고 성공했는데, 사실 다른 tenant의 row까지 읽거나 수정했다.**

이 문제는 장애처럼 보이지 않는다. API는 200을 반환한다. DB는 오류를 내지 않는다. 모니터링은 정상이다. 하지만 보안 사고, 개인정보 유출, 고객 신뢰 붕괴, 법적 리스크로 바로 이어질 수 있다. 특히 B2B SaaS, 사내 업무 시스템, HR/급여/계약/결제/분석 플랫폼에서는 tenant 격리가 제품의 부가 기능이 아니라 **존재 조건**이다.

실무에서 tenant 격리는 보통 애플리케이션 코드로 시작한다.

```sql
SELECT *
FROM invoices
WHERE tenant_id = $1
  AND status = 'OPEN';
```

이 패턴 자체가 틀린 것은 아니다. 문제는 시간이 지나면서 쿼리 표면이 폭발한다는 점이다.

- API 조회 쿼리에는 `tenant_id`가 붙어 있지만 관리자 배치에는 빠진다.
- 신규 개발자가 만든 리포트 쿼리 하나가 tenant 조건을 누락한다.
- ORM relation preload가 내부적으로 별도 쿼리를 만들며 scope를 잃는다.
- CSV export, webhook retry, 검색 인덱싱, 데이터 보정 스크립트가 우회 경로가 된다.
- `UPDATE ... FROM`이나 `DELETE`에서 join 대상에는 tenant 조건이 있는데 대상 테이블에는 빠진다.
- `SECURITY DEFINER` 함수 하나가 의도보다 넓은 권한으로 실행된다.
- 운영자가 임시로 만든 view나 materialized view가 row boundary를 흐린다.

이때 필요한 것은 "개발자가 조심한다"가 아니다. 조심은 중요하지만, 반복 가능한 통제 수단이 아니다. 중급 이상 개발자에게 필요한 질문은 이것이다.

> **tenant 조건을 애플리케이션 컨벤션이 아니라 데이터베이스의 강제 규칙으로 내릴 수 있는가?**

PostgreSQL의 Row-Level Security, 줄여서 RLS는 이 질문에 대한 강력한 답이다. RLS를 켜면 테이블 단위로 row 가시성 정책을 정의할 수 있다. 사용자가 어떤 row를 `SELECT`, `INSERT`, `UPDATE`, `DELETE`할 수 있는지 정책으로 제한한다. 즉 애플리케이션 쿼리가 `WHERE tenant_id = ...`를 깜빡해도 DB가 자동으로 row-level 필터를 추가하는 것처럼 동작한다.

하지만 RLS도 마법은 아니다. 대충 켜면 다음과 같은 새로운 함정이 생긴다.

- table owner나 superuser가 RLS를 우회한다는 사실을 모르고 테스트한다.
- `USING`과 `WITH CHECK`의 차이를 모른 채 쓰기 정책을 만든다.
- tenant context를 session 변수에 넣었는데 connection pooling과 충돌한다.
- `SECURITY DEFINER` 함수가 RLS를 우회하거나 search_path 공격 표면을 만든다.
- 정책 함수가 너무 무거워 모든 쿼리의 planner와 실행 비용을 키운다.
- 인덱스가 tenant boundary와 맞지 않아 RLS는 안전하지만 성능은 망가진다.
- 관리자/지원/감사 role을 만들다가 예외 정책이 본 정책보다 복잡해진다.

이 글은 PostgreSQL RLS를 "문법 소개"가 아니라 **멀티테넌트 데이터 격리를 실제 운영 가능한 보안·성능·개발 경험 문제로 설계하는 방법**으로 정리한다.

이번 글에서 답하려는 질문은 아래와 같다.

1. RLS는 PostgreSQL 실행 흐름에서 어떤 방식으로 row 가시성을 강제하는가?
2. `USING`과 `WITH CHECK`는 왜 완전히 다른 의미인가?
3. tenant context를 `current_setting` 기반으로 둘 때 connection pool과 어떻게 충돌하는가?
4. table owner, `BYPASSRLS`, `FORCE ROW LEVEL SECURITY`를 왜 반드시 이해해야 하는가?
5. `SECURITY DEFINER` 함수는 언제 필요하고, 언제 tenant 격리를 깨는 우회로가 되는가?
6. RLS 정책은 인덱스, planner, partitioning, view, migration과 어떻게 엮이는가?
7. 실무에서 테스트·관측·운영 체크리스트는 어떻게 만들어야 하는가?

핵심 결론부터 먼저 말하면 이렇다.

1. RLS는 애플리케이션의 `WHERE tenant_id = ?` 컨벤션을 **DB 강제 정책**으로 끌어내리는 도구다.
2. `SELECT/UPDATE/DELETE` 가시성은 `USING`, `INSERT/UPDATE`로 새로 만들어지는 row 검증은 `WITH CHECK`가 담당한다.
3. 멀티테넌트 SaaS에서는 RLS만큼이나 **tenant context 주입 방식**이 중요하다.
4. table owner, superuser, `BYPASSRLS` role은 정책을 우회할 수 있으므로 운영 role 설계가 RLS 설계의 절반이다.
5. `SECURITY DEFINER`는 예외 권한을 캡슐화하는 좋은 도구이지만, search_path와 RLS 우회 가능성을 통제하지 않으면 가장 위험한 구멍이 된다.
6. RLS는 보안 기능이지만 성능 기능처럼 다뤄야 한다. tenant_id 선행 인덱스, 정책 함수 비용, plan cache 영향을 함께 봐야 한다.
7. 좋은 RLS 설계는 "정책을 많이 쓰는 것"이 아니라 **기본 경로는 단순하게 막고, 예외 경로는 좁고 감사 가능하게 여는 것**이다.

---

## 먼저 큰 그림: RLS는 쿼리 작성 규칙이 아니라 테이블 접근 계약이다

애플리케이션 레이어에서 tenant 격리를 구현하는 가장 흔한 방식은 repository, service, ORM scope에 tenant 조건을 붙이는 것이다.

예를 들어 Java/Spring이라면 `TenantContext`를 만들고 repository 메서드에서 tenant id를 파라미터로 받는다. Python/FastAPI라면 dependency에서 tenant를 resolve한 뒤 SQLAlchemy query에 filter를 붙인다. Next.js나 API 서버에서도 비슷하게 request context에서 tenant를 읽어 쿼리에 전달한다.

이 방식은 직관적이고, 처음에는 충분해 보인다. 하지만 확장될수록 세 가지 약점이 커진다.

### 1) 모든 쿼리 작성자가 같은 규칙을 지켜야 한다

코드베이스가 작을 때는 가능하다. 하지만 서비스가 커지면 쿼리는 여러 형태로 늘어난다.

- 온라인 API
- 내부 관리자 화면
- 검색 인덱싱 작업
- 통계 배치
- 고객지원 도구
- 데이터 보정 스크립트
- 마이그레이션
- BI 연결
- 임시 운영 쿼리

이 모든 경로에서 tenant 조건을 빠뜨리지 않는다는 것은 생각보다 어려운 요구다. 특히 "한 번만 돌릴 스크립트"와 "관리자만 쓰는 화면"이 가장 위험하다.

### 2) 쿼리 조합이 복잡해질수록 scope가 새기 쉽다

간단한 단일 테이블 조회는 쉽다.

```sql
SELECT *
FROM projects
WHERE tenant_id = $1;
```

하지만 아래처럼 join, subquery, CTE, `UPDATE ... FROM`, `INSERT ... SELECT`, relation preload가 섞이면 누락 지점이 늘어난다.

```sql
UPDATE invoices i
SET status = 'OVERDUE'
FROM payment_terms t
WHERE i.payment_term_id = t.id
  AND t.due_days < 30;
```

이 쿼리는 `payment_terms`에는 어떤 조건이 있을 수 있지만, `invoices` 대상 row에 tenant boundary가 명확히 걸려 있지 않다. 코드 리뷰에서 잡을 수도 있지만, 사람이 매번 잡아야 한다면 언젠가 빠진다.

### 3) 보안 요구사항과 개발자 경험이 충돌한다

모든 쿼리에 tenant 조건을 명시하라는 규칙은 안전하지만 개발자 경험을 떨어뜨린다. 개발자가 매번 같은 조건을 붙이다 보면 boilerplate가 늘고, 복잡한 쿼리에서는 실제 비즈니스 조건보다 보안 조건이 더 많이 보인다. 그러면 팀은 편의를 위해 helper를 만들고, helper가 또 다른 우회 경로가 된다.

RLS는 이 균형을 바꾼다. 테이블이 스스로 "이 session이 볼 수 있는 row는 무엇인가"를 판단하게 만든다. 애플리케이션은 tenant context를 DB session에 설정하고, DB는 모든 쿼리에 일관된 row boundary를 적용한다.

---

## 핵심 개념 1: RLS 정책은 보이지 않는 `WHERE`가 아니라 권한 판정식에 가깝다

RLS를 설명할 때 흔히 "DB가 자동으로 `WHERE tenant_id = current_tenant()`를 붙여준다"고 말한다. 직관적으로는 맞지만, 운영 설계에서는 조금 더 엄밀하게 봐야 한다.

RLS는 테이블별로 정책을 정의하고, PostgreSQL이 해당 테이블 접근 시 정책 expression을 평가해 row를 허용하거나 거부한다. 정책은 SQL expression이므로 column, function, session setting, role 등을 참조할 수 있다.

기본 흐름은 이렇다.

```sql
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_documents_select
ON documents
FOR SELECT
USING (tenant_id = current_setting('app.tenant_id')::uuid);
```

이제 RLS가 적용되는 role이 `documents`를 조회하면, policy의 `USING` 조건을 만족하는 row만 보인다.

```sql
SELECT id, title
FROM documents
WHERE status = 'ACTIVE';
```

애플리케이션 쿼리에는 tenant 조건이 없어도, 결과는 현재 session의 `app.tenant_id`에 맞는 row로 제한된다.

하지만 이것을 단순히 문자열로 붙는 `WHERE`라고 생각하면 곤란하다. RLS는 SQL rewrite와 planner 단계에서 보안 barrier 성격의 qual로 들어가며, 함수 volatility, leakproof 여부, join 순서, view, `SECURITY DEFINER` 같은 요소와 상호작용한다. 실무 관점에서는 내부 구현의 모든 세부를 외울 필요는 없지만, 적어도 아래 감각은 필요하다.

- RLS 정책도 쿼리 비용의 일부다.
- 정책 expression이 복잡하면 모든 접근이 복잡해진다.
- 정책에서 호출하는 함수의 volatility와 비용은 plan에 영향을 준다.
- RLS는 권한 시스템과 붙어 있으므로 owner/superuser/role 속성에 따라 적용 여부가 달라진다.
- RLS는 row를 숨기는 기능이지, 무조건 column masking이나 감사 로그를 대신하는 기능은 아니다.

즉 RLS는 "편리한 자동 필터"가 아니라, 테이블의 접근 계약을 SQL로 선언하는 기능이다.

---

## 핵심 개념 2: `USING`과 `WITH CHECK`를 구분하지 못하면 쓰기 경로가 뚫린다

RLS에서 가장 중요한 문법 차이는 `USING`과 `WITH CHECK`다.

### `USING`: 어떤 기존 row에 접근할 수 있는가

`USING`은 이미 존재하는 row가 해당 명령에서 보이거나 대상이 될 수 있는지를 판단한다.

- `SELECT`: 어떤 row가 조회 결과에 포함되는가
- `UPDATE`: 어떤 기존 row를 업데이트 대상으로 삼을 수 있는가
- `DELETE`: 어떤 기존 row를 삭제 대상으로 삼을 수 있는가

예를 들어 아래 정책은 현재 tenant의 row만 조회·수정·삭제 대상으로 허용한다.

```sql
CREATE POLICY tenant_documents_visible
ON documents
USING (tenant_id = current_setting('app.tenant_id')::uuid);
```

명령별 정책을 따로 만들지 않고 `FOR ALL` 기본 성격으로 둘 수도 있지만, 실무에서는 읽기와 쓰기 의도가 달라지는 경우가 많아 명시적으로 나누는 편이 안전하다.

### `WITH CHECK`: 새 row 상태가 허용되는가

`WITH CHECK`는 `INSERT`나 `UPDATE` 이후 새로 만들어질 row가 정책을 만족하는지를 검증한다.

```sql
CREATE POLICY tenant_documents_insert
ON documents
FOR INSERT
WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid);
```

이 정책이 없거나 잘못되어 있으면 어떤 일이 생길까?

- 사용자는 자기 tenant row만 볼 수 있다.
- 하지만 insert 시 다른 tenant_id를 가진 row를 만들 수 있다.
- 또는 update로 자기 row의 tenant_id를 다른 tenant로 바꿀 수 있다.

이건 단순 버그가 아니라 데이터 소유권 훼손이다. 특히 `INSERT ... SELECT`, bulk import, admin tool에서 자주 발생한다.

### `UPDATE`에는 두 개가 모두 필요하다

`UPDATE`는 기존 row를 대상으로 잡고, 새 row version을 만든다. 그래서 두 질문을 모두 해야 한다.

1. 이 사용자가 이 기존 row를 업데이트 대상으로 볼 수 있는가? → `USING`
2. 업데이트 후 row가 여전히 허용된 상태인가? → `WITH CHECK`

```sql
CREATE POLICY tenant_documents_update
ON documents
FOR UPDATE
USING (tenant_id = current_setting('app.tenant_id')::uuid)
WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid);
```

이 정책은 사용자가 자기 tenant row만 업데이트할 수 있고, 업데이트 후에도 tenant_id가 자기 tenant로 남아 있어야 함을 의미한다.

실무에서는 tenant_id 컬럼을 아예 application role에서 수정하지 못하게 막는 것도 좋다.

```sql
REVOKE UPDATE (tenant_id) ON documents FROM app_user;
```

단, column-level privilege와 ORM 동작이 충돌할 수 있으므로 테스트가 필요하다. 그래도 핵심 소유권 컬럼은 DB 권한으로 한 번 더 잠그는 편이 좋다.

---

## 핵심 개념 3: tenant context는 RLS의 심장이다

RLS 정책은 결국 "현재 요청의 tenant가 누구인가"를 알아야 한다. PostgreSQL 안에서 이 값을 전달하는 대표적인 방법은 custom setting을 쓰는 것이다.

```sql
SELECT set_config('app.tenant_id', '018f3d7b-4d2b-7b6d-9a1e-9f7f6a0c1234', true);
```

그리고 정책에서 읽는다.

```sql
current_setting('app.tenant_id')::uuid
```

여기서 세 번째 인자 `true`는 `SET LOCAL`에 해당한다. 현재 transaction 범위에서만 설정하고 transaction이 끝나면 사라지게 한다. 이 차이가 매우 중요하다.

### session-local vs transaction-local

`set_config(name, value, false)` 또는 `SET app.tenant_id = ...`는 session 범위다. connection이 살아 있는 동안 유지된다. connection pool을 쓰는 웹 서비스에서는 위험하다. 이전 요청의 tenant_id가 다음 요청으로 새는 사고가 날 수 있다.

반면 `set_config(name, value, true)` 또는 `SET LOCAL app.tenant_id = ...`는 transaction 범위다. transaction이 끝나면 자동으로 되돌아간다.

멀티테넌트 API에서는 보통 아래 패턴이 안전하다.

```sql
BEGIN;
SELECT set_config('app.tenant_id', $1, true);
-- business queries
COMMIT;
```

애플리케이션에서는 request마다 transaction boundary를 명확히 잡고, 그 안에서 tenant context를 설정해야 한다.

### transaction pooling과의 충돌

PgBouncer transaction pooling을 쓰면 session 상태에 의존하는 설계가 특히 위험해진다. transaction pooling에서는 transaction이 끝날 때 서버 connection이 pool로 돌아가고, 다음 transaction은 다른 backend connection에서 실행될 수 있다.

따라서 다음 방식은 위험하다.

```sql
SET app.tenant_id = '...';
SELECT * FROM documents;
```

같은 logical request처럼 보여도 실제 서버 connection이 바뀌거나, session 설정이 예상과 다르게 남을 수 있다. transaction pooling 환경에서는 반드시 transaction 안에서 `SET LOCAL` 또는 `set_config(..., true)`를 사용해야 한다.

```sql
BEGIN;
SET LOCAL app.tenant_id = '018f3d7b-4d2b-7b6d-9a1e-9f7f6a0c1234';
SELECT * FROM documents;
COMMIT;
```

### context 누락은 fail-open이 아니라 fail-closed로 만들어야 한다

`current_setting('app.tenant_id')`는 설정이 없으면 오류를 낸다. 이 동작은 오히려 안전하다. tenant context가 없으면 쿼리가 실패해야 한다.

하지만 어떤 팀은 오류를 피하려고 아래처럼 쓴다.

```sql
current_setting('app.tenant_id', true)::uuid
```

두 번째 인자 `true`는 missing_ok다. 설정이 없으면 `NULL`을 반환한다. 정책이 `tenant_id = NULL`이면 결과가 없으므로 괜찮아 보일 수 있다. 하지만 정책 expression이 복잡해지면 `NULL` 처리 때문에 예상과 다른 결과가 나올 수 있다. 또 디버깅이 어려워진다.

개인적으로는 핵심 tenant 정책에서는 명시적으로 실패하는 방식을 선호한다.

```sql
CREATE OR REPLACE FUNCTION app_current_tenant_id()
RETURNS uuid
LANGUAGE sql
STABLE
AS $$
  SELECT current_setting('app.tenant_id')::uuid
$$;
```

그리고 정책에서는 이 함수를 쓴다.

```sql
USING (tenant_id = app_current_tenant_id())
WITH CHECK (tenant_id = app_current_tenant_id())
```

이렇게 하면 정책이 읽기 쉬워지고, tenant context가 없을 때 명확히 실패한다.

---

## 핵심 개념 4: table owner, superuser, `BYPASSRLS`, `FORCE ROW LEVEL SECURITY`는 반드시 테스트해야 한다

RLS를 처음 적용할 때 가장 흔한 착각은 "테이블에 RLS를 켰으니 모든 사용자가 정책을 탄다"는 것이다. 실제로는 그렇지 않다.

PostgreSQL에서 superuser와 `BYPASSRLS` 속성을 가진 role은 RLS를 우회할 수 있다. 또한 기본적으로 table owner도 자기 테이블의 RLS를 우회한다. 이 특성은 관리 작업에는 필요하지만, 애플리케이션 테스트와 운영 role 설계를 어렵게 만든다.

### 나쁜 role 구조

```sql
-- 애플리케이션이 마이그레이션 owner role로 접속한다
app_db_owner owns tables
app connects as app_db_owner
```

이 구조에서는 앱이 RLS를 켰다고 생각해도 실제 애플리케이션 접속 role이 table owner라 정책을 우회할 수 있다. 테스트에서는 모든 데이터가 보이고, 운영에서도 정책이 강제되지 않는다.

### 더 나은 role 구조

```sql
-- schema/table owner
app_owner

-- migration 전용
app_migrator

-- 애플리케이션 런타임
app_user

-- 고객지원/운영 read-only
support_reader

-- 감사/보안 제한 role
audit_reader
```

테이블은 `app_owner`가 소유하고, 실제 애플리케이션은 `app_user`로 접속한다. `app_user`는 필요한 DML 권한만 받고, RLS 적용 대상이 된다.

```sql
ALTER TABLE documents OWNER TO app_owner;

GRANT SELECT, INSERT, UPDATE, DELETE ON documents TO app_user;
GRANT USAGE ON SCHEMA public TO app_user;
```

그리고 owner에게도 RLS를 강제하고 싶다면 다음을 쓴다.

```sql
ALTER TABLE documents FORCE ROW LEVEL SECURITY;
```

`FORCE ROW LEVEL SECURITY`는 table owner에게도 RLS를 적용한다. 다만 superuser나 `BYPASSRLS` role까지 막는 것은 아니다. 운영 DB에서 애플리케이션 role에 `BYPASSRLS`가 있으면 사실상 RLS 설계가 무력화된다.

### 검증 쿼리

운영 점검에는 role 속성을 반드시 확인해야 한다.

```sql
SELECT rolname, rolsuper, rolbypassrls
FROM pg_roles
WHERE rolname IN ('app_owner', 'app_migrator', 'app_user', 'support_reader');
```

그리고 테이블별 RLS 상태도 본다.

```sql
SELECT n.nspname AS schema_name,
       c.relname AS table_name,
       c.relrowsecurity,
       c.relforcerowsecurity
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind = 'r'
  AND n.nspname NOT IN ('pg_catalog', 'information_schema')
ORDER BY 1, 2;
```

RLS는 정책 SQL만 보는 것이 아니라 **어떤 role로 실제 접속하는지**까지 봐야 완성된다.

---

## 실무 예시 1: 기본 SaaS 테이블에 tenant RLS 적용하기

예시로 `projects`, `documents`, `comments`가 있는 B2B SaaS를 생각해 보자. 모든 업무 데이터는 `tenant_id`를 갖는다.

```sql
CREATE TABLE tenants (
  id uuid PRIMARY KEY,
  name text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE projects (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  name text NOT NULL,
  status text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE documents (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  project_id uuid NOT NULL REFERENCES projects(id),
  title text NOT NULL,
  body text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
```

기본 인덱스는 tenant 조건과 주요 조회 조건을 함께 고려한다.

```sql
CREATE INDEX projects_tenant_status_created_idx
ON projects (tenant_id, status, created_at DESC);

CREATE INDEX documents_tenant_project_created_idx
ON documents (tenant_id, project_id, created_at DESC);
```

RLS helper function을 만든다.

```sql
CREATE SCHEMA IF NOT EXISTS app;

CREATE OR REPLACE FUNCTION app.current_tenant_id()
RETURNS uuid
LANGUAGE sql
STABLE
AS $$
  SELECT current_setting('app.tenant_id')::uuid
$$;
```

테이블에 RLS를 켠다.

```sql
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects FORCE ROW LEVEL SECURITY;

ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents FORCE ROW LEVEL SECURITY;
```

정책을 만든다.

```sql
CREATE POLICY projects_tenant_select
ON projects
FOR SELECT
USING (tenant_id = app.current_tenant_id());

CREATE POLICY projects_tenant_insert
ON projects
FOR INSERT
WITH CHECK (tenant_id = app.current_tenant_id());

CREATE POLICY projects_tenant_update
ON projects
FOR UPDATE
USING (tenant_id = app.current_tenant_id())
WITH CHECK (tenant_id = app.current_tenant_id());

CREATE POLICY projects_tenant_delete
ON projects
FOR DELETE
USING (tenant_id = app.current_tenant_id());
```

`documents`도 같은 방식이다.

```sql
CREATE POLICY documents_tenant_select
ON documents
FOR SELECT
USING (tenant_id = app.current_tenant_id());

CREATE POLICY documents_tenant_insert
ON documents
FOR INSERT
WITH CHECK (tenant_id = app.current_tenant_id());

CREATE POLICY documents_tenant_update
ON documents
FOR UPDATE
USING (tenant_id = app.current_tenant_id())
WITH CHECK (tenant_id = app.current_tenant_id());

CREATE POLICY documents_tenant_delete
ON documents
FOR DELETE
USING (tenant_id = app.current_tenant_id());
```

이제 애플리케이션 요청은 다음 순서를 지킨다.

```sql
BEGIN;
SET LOCAL app.tenant_id = '018f3d7b-4d2b-7b6d-9a1e-9f7f6a0c1234';

SELECT id, title
FROM documents
WHERE project_id = '018f3d8c-2b5f-793f-95b2-0f6d1e1c9999'
ORDER BY created_at DESC
LIMIT 50;

COMMIT;
```

쿼리에 `tenant_id`가 없어도 RLS가 적용된다. 하지만 성능을 위해 애플리케이션 쿼리에 tenant 조건을 중복으로 넣는 것도 나쁘지 않다.

```sql
SELECT id, title
FROM documents
WHERE tenant_id = app.current_tenant_id()
  AND project_id = $1
ORDER BY created_at DESC
LIMIT 50;
```

중복처럼 보이지만 장점이 있다.

- 개발자가 쿼리 의도를 명확히 읽을 수 있다.
- planner가 복합 인덱스를 더 직관적으로 활용할 수 있다.
- RLS는 최후 방어선으로 남는다.

즉 RLS를 쓴다고 애플리케이션에서 tenant 조건을 완전히 숨겨야 하는 것은 아니다. 개인적으로는 **보안은 RLS로 강제하고, 성능과 가독성은 명시적 tenant 조건으로 보강하는 방식**을 선호한다.

---

## 실무 예시 2: 사용자 멤버십 기반 정책으로 확장하기

tenant만으로 충분하지 않은 서비스도 많다. 같은 tenant 안에서도 사용자마다 접근 가능한 project가 다를 수 있다.

```sql
CREATE TABLE project_members (
  tenant_id uuid NOT NULL,
  project_id uuid NOT NULL,
  user_id uuid NOT NULL,
  role text NOT NULL,
  PRIMARY KEY (tenant_id, project_id, user_id)
);
```

이제 document는 같은 tenant라도 project membership이 있는 사용자만 볼 수 있다고 하자. session에는 tenant_id와 user_id를 넣는다.

```sql
CREATE OR REPLACE FUNCTION app.current_user_id()
RETURNS uuid
LANGUAGE sql
STABLE
AS $$
  SELECT current_setting('app.user_id')::uuid
$$;
```

정책은 이렇게 만들 수 있다.

```sql
CREATE POLICY documents_project_member_select
ON documents
FOR SELECT
USING (
  tenant_id = app.current_tenant_id()
  AND EXISTS (
    SELECT 1
    FROM project_members pm
    WHERE pm.tenant_id = documents.tenant_id
      AND pm.project_id = documents.project_id
      AND pm.user_id = app.current_user_id()
  )
);
```

이 정책은 더 정교하지만 비용도 더 크다. 모든 document 접근에 membership check가 들어간다. 따라서 인덱스가 반드시 필요하다.

```sql
CREATE INDEX project_members_user_lookup_idx
ON project_members (tenant_id, project_id, user_id);

CREATE INDEX documents_tenant_project_idx
ON documents (tenant_id, project_id);
```

여기서 중요한 판단이 있다.

- 모든 쿼리마다 membership `EXISTS`를 평가할 것인가?
- 애플리케이션에서 접근 가능한 project_id 목록을 먼저 좁힐 것인가?
- 권한이 자주 바뀌지 않는다면 별도 access table이나 materialized 구조를 둘 것인가?
- 관리자 role, audit role은 membership을 우회해야 하는가?

RLS는 복잡한 권한 모델도 표현할 수 있지만, 표현할 수 있다고 해서 항상 DB 정책에 다 넣는 것이 좋은 것은 아니다. 정책이 너무 복잡해지면 SQL 성능과 디버깅이 어려워진다.

실무 기준은 이렇다.

- tenant boundary는 거의 항상 RLS에 넣는다.
- tenant 내부의 세밀한 권한은 자주 쓰는 핵심 테이블부터 제한적으로 넣는다.
- 복잡한 workflow 권한은 애플리케이션에서 먼저 검증하고, RLS는 최소 안전 경계를 담당하게 한다.
- 예외 권한은 별도 role이나 좁은 함수로 캡슐화한다.

---

## 실무 예시 3: 관리자·고객지원·감사 role은 어떻게 열어야 할까

현실적인 SaaS에는 일반 사용자만 있지 않다. 고객지원 담당자는 여러 tenant를 볼 수 있어야 할 수 있고, 보안 감사자는 모든 tenant의 일부 metadata를 읽어야 할 수 있다. 운영 배치는 cross-tenant aggregate를 만들어야 할 수 있다.

가장 위험한 방식은 애플리케이션 role 하나에 모든 예외를 넣는 것이다.

```sql
-- 위험한 사고방식
app_user can read tenant rows
app_user can also support-read all tenants when flag is set
app_user can also run maintenance
```

이렇게 하면 정책이 곧 조건문 덩어리가 된다.

```sql
USING (
  tenant_id = app.current_tenant_id()
  OR current_setting('app.is_support', true) = 'true'
  OR current_setting('app.is_batch', true) = 'true'
)
```

처음엔 편해 보이지만, 시간이 지나면 어떤 경로가 왜 열리는지 알기 어려워진다. 더 나은 방식은 role을 분리하는 것이다.

### 일반 앱 role

```sql
CREATE ROLE app_user NOLOGIN;
```

일반 앱 role은 tenant RLS를 탄다.

```sql
CREATE POLICY documents_app_user_select
ON documents
FOR SELECT
TO app_user
USING (tenant_id = app.current_tenant_id());
```

### 고객지원 role

고객지원은 모든 row를 보게 할 수도 있지만, 보통은 목적 제한이 필요하다. 예를 들어 지원 도구에서 명시적으로 선택한 tenant만 보게 한다.

```sql
CREATE ROLE support_reader NOLOGIN;

CREATE OR REPLACE FUNCTION app.support_tenant_id()
RETURNS uuid
LANGUAGE sql
STABLE
AS $$
  SELECT current_setting('app.support_tenant_id')::uuid
$$;

CREATE POLICY documents_support_select
ON documents
FOR SELECT
TO support_reader
USING (tenant_id = app.support_tenant_id());
```

이렇게 하면 고객지원도 무제한 전체 조회가 아니라, ticket이나 승인 흐름에서 설정된 특정 tenant 범위만 볼 수 있다.

### 감사 role

감사 role은 원문 전체가 아니라 metadata만 보는 view를 제공하는 편이 낫다.

```sql
CREATE VIEW audit_document_metadata AS
SELECT tenant_id, id, project_id, created_at, updated_at
FROM documents;

GRANT SELECT ON audit_document_metadata TO audit_reader;
```

단, view와 RLS의 상호작용은 PostgreSQL 버전과 view 소유자, `security_invoker` 설정에 따라 달라질 수 있다. 기본 view는 소유자 권한으로 동작하는 특성이 있어 RLS 기대와 다르게 보일 수 있다. PostgreSQL 15 이후에는 `security_invoker` view를 활용할 수 있다.

```sql
CREATE VIEW audit_document_metadata
WITH (security_invoker = true)
AS
SELECT tenant_id, id, project_id, created_at, updated_at
FROM documents;
```

버전과 권한 모델을 확인하지 않고 view를 "안전한 제한 창"으로 믿으면 위험하다. view를 보안 경계로 쓸 때는 반드시 실제 접속 role로 테스트해야 한다.

---

## `SECURITY DEFINER`: 필요한 예외 권한을 좁게 열기 위한 칼, 잘못 쓰면 RLS 우회 터널

RLS를 운영하다 보면 일반 role로는 할 수 없지만 애플리케이션에 꼭 필요한 작업이 생긴다.

예를 들어 사용자가 초대 링크를 수락할 때, 아직 tenant 멤버가 아니지만 invitation row를 읽어야 한다. 또는 tenant 생성 시 여러 테이블에 초기 데이터를 넣어야 한다. 또는 고객지원 담당자가 승인된 ticket 범위에서만 특정 조치를 해야 한다.

이때 `SECURITY DEFINER` 함수를 사용할 수 있다. `SECURITY DEFINER` 함수는 호출자가 아니라 함수 소유자의 권한으로 실행된다.

```sql
CREATE OR REPLACE FUNCTION app.accept_invitation(p_token text)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = app, public, pg_temp
AS $$
DECLARE
  v_invitation invitations%ROWTYPE;
BEGIN
  SELECT *
  INTO v_invitation
  FROM invitations
  WHERE token = p_token
    AND expires_at > now()
    AND accepted_at IS NULL;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'invalid invitation';
  END IF;

  INSERT INTO tenant_members (tenant_id, user_id, role)
  VALUES (v_invitation.tenant_id, app.current_user_id(), v_invitation.role);

  UPDATE invitations
  SET accepted_at = now()
  WHERE id = v_invitation.id;
END;
$$;

REVOKE ALL ON FUNCTION app.accept_invitation(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION app.accept_invitation(text) TO app_user;
```

이 패턴은 강력하다. 일반 app_user에게 `invitations` 전체 조회 권한을 주지 않고도, 초대 수락이라는 좁은 동작만 열 수 있다.

하지만 `SECURITY DEFINER`는 매우 조심해야 한다.

### 위험 1: 함수 owner가 table owner면 RLS를 우회할 수 있다

함수는 owner 권한으로 실행된다. 함수 owner가 RLS를 우회하는 table owner라면, 함수 내부 쿼리가 RLS를 타지 않을 수 있다. 의도한 예외라면 괜찮지만, 의도하지 않았다면 tenant 격리 구멍이다.

따라서 definer 함수에는 별도 owner role을 두고 권한을 최소화하는 편이 좋다.

```sql
CREATE ROLE app_function_owner NOLOGIN;
-- 필요한 테이블/컬럼 권한만 부여
```

그리고 함수 내부에서 tenant 검증을 명시적으로 한다.

```sql
IF v_invitation.tenant_id <> app.current_tenant_id() THEN
  RAISE EXCEPTION 'tenant mismatch';
END IF;
```

초대 수락처럼 tenant가 아직 없는 흐름은 별도 threat model이 필요하다. token entropy, 만료, one-time use, audit log를 함께 설계해야 한다.

### 위험 2: `search_path` 공격

`SECURITY DEFINER` 함수에서 `search_path`를 고정하지 않으면, 공격자가 같은 이름의 함수나 객체를 자기 schema에 만들어 definer 권한으로 실행되게 유도할 수 있다. 그래서 definer 함수에는 항상 `SET search_path`를 명시한다.

```sql
SECURITY DEFINER
SET search_path = app, public, pg_temp
```

가능하면 함수 내부 객체는 schema-qualified name으로 쓰는 편이 더 안전하다.

```sql
SELECT * FROM app.invitations WHERE ...;
```

### 위험 3: 너무 넓은 함수 API

아래 같은 함수는 위험하다.

```sql
CREATE FUNCTION app.run_admin_sql(sql text) RETURNS void ...
```

극단적인 예이지만, 현실에서는 조금 덜 노골적인 형태로 나타난다.

- arbitrary table name을 받아 동적 SQL 실행
- arbitrary tenant_id를 받아 cross-tenant 조회
- JSON payload를 받아 여러 종류의 조치 수행
- role check 없이 상태 변경
- audit log 없이 예외 작업 수행

`SECURITY DEFINER` 함수는 작고 구체적이어야 한다. 함수 이름이 업무 행위를 설명해야 하고, 입력 파라미터는 최소여야 하며, 내부에서 권한·tenant·상태를 다시 검증해야 한다.

---

## RLS와 성능: 안전해졌는데 갑자기 느려지는 이유

RLS는 보안 기능이지만, 운영에서는 성능 기능처럼 봐야 한다. 모든 쿼리에 정책 predicate가 추가되기 때문이다.

### 1) tenant_id 인덱스가 없으면 RLS는 안전한 full scan이 된다

가장 기본은 tenant boundary와 주요 조회 조건을 함께 인덱싱하는 것이다.

```sql
CREATE INDEX documents_tenant_status_created_idx
ON documents (tenant_id, status, created_at DESC);
```

많은 서비스에서 모든 테이블에 `tenant_id`가 있어도 인덱스는 업무 조건 위주로만 만든다.

```sql
CREATE INDEX documents_status_created_idx
ON documents (status, created_at DESC);
```

RLS 적용 후 대부분 쿼리는 tenant_id 조건을 포함하게 된다. 그러면 인덱스 설계도 바뀌어야 한다. 멀티테넌트 OLTP에서는 대개 `tenant_id`를 선행 컬럼으로 둔 복합 인덱스가 기본값에 가깝다.

하지만 항상 tenant_id가 첫 번째여야 하는 것은 아니다. 매우 selective한 global key 조회, unique id 조회, cross-tenant admin query는 다른 인덱스가 필요할 수 있다. 중요한 것은 RLS 이후 실제 실행 계획을 `EXPLAIN (ANALYZE, BUFFERS)`로 다시 확인하는 것이다.

### 2) 정책 함수는 가볍고 STABLE해야 한다

아래 정책은 단순하다.

```sql
tenant_id = app.current_tenant_id()
```

`app.current_tenant_id()`가 `current_setting`만 읽는 `STABLE` SQL 함수라면 부담이 작다. 반면 정책 함수가 매번 테이블을 조회하거나 외부 복잡한 계산을 하면 모든 쿼리에 비용이 붙는다.

나쁜 예시:

```sql
USING (app.can_access_document(id, app.current_user_id()))
```

이 함수가 내부에서 여러 테이블을 조회한다면, 문서 row마다 접근 권한 계산이 반복될 수 있다. planner가 최적화하기 어렵고, row 수가 늘수록 급격히 느려진다.

더 나은 방향은 권한 모델을 join 가능한 테이블과 인덱스로 표현하는 것이다.

```sql
USING (
  tenant_id = app.current_tenant_id()
  AND EXISTS (
    SELECT 1
    FROM project_members pm
    WHERE pm.tenant_id = documents.tenant_id
      AND pm.project_id = documents.project_id
      AND pm.user_id = app.current_user_id()
  )
)
```

그래도 비용이 크면 접근 가능한 project 범위를 materialized table로 유지하거나, API에서 먼저 project_id를 좁히는 방식과 조합한다.

### 3) prepared statement와 plan cache를 확인해야 한다

RLS 정책이 `current_setting`을 참조하면 tenant 값은 실행 시 session setting에 따라 달라진다. 일반적으로 안전하지만, prepared statement와 generic plan이 섞이면 특정 tenant 분포에 최적화되지 않은 plan이 선택될 수 있다.

예를 들어 어떤 tenant는 row가 100개, 어떤 tenant는 1억 개를 갖고 있다면 같은 쿼리라도 최적 plan이 다를 수 있다. RLS가 tenant 조건을 숨기면 개발자가 이 skew를 놓치기 쉽다.

대응은 다음과 같다.

- 큰 tenant와 작은 tenant를 나눠 `EXPLAIN`한다.
- tenant_id를 애플리케이션 쿼리에 명시적으로 넣어 planner가 더 잘 보게 한다.
- 통계 target, extended statistics, partitioning 필요성을 검토한다.
- ORM/드라이버의 prepared statement 전략을 확인한다.
- 극단적으로 skew가 큰 tenant는 물리 분리나 partitioning을 고려한다.

### 4) RLS는 column masking이 아니다

RLS는 row 단위 가시성이다. 같은 row 안의 일부 column만 감추는 기능은 아니다. 민감 컬럼을 role별로 제한하려면 column privilege, view, 별도 테이블 분리, application masking을 함께 써야 한다.

```sql
REVOKE SELECT (body) ON documents FROM support_reader;
```

하지만 column-level privilege는 ORM이나 `SELECT *`와 충돌할 수 있고, 운영 복잡도를 만든다. 민감 데이터가 강하게 분리되어야 한다면 테이블 자체를 나누는 편이 더 명확할 때가 많다.

---

## RLS와 파티셔닝: tenant 격리와 대용량 운영을 같이 볼 때

데이터가 커지면 tenant_id 기반 RLS만으로는 부족할 수 있다. 특히 tenant 수가 많고, 일부 대형 tenant가 전체 데이터 대부분을 차지하면 인덱스와 vacuum, retention, 백업 전략까지 영향을 받는다.

파티셔닝과 RLS를 함께 쓸 때는 세 가지 패턴이 있다.

### 1) 시간 기반 파티셔닝 + tenant_id 인덱스

로그, 이벤트, 이력 테이블은 시간 range partition이 자연스럽다.

```sql
CREATE TABLE audit_events (
  tenant_id uuid NOT NULL,
  id uuid NOT NULL,
  occurred_at timestamptz NOT NULL,
  event_type text NOT NULL,
  payload jsonb NOT NULL
) PARTITION BY RANGE (occurred_at);
```

각 파티션에는 tenant_id 포함 인덱스를 둔다.

```sql
CREATE INDEX audit_events_2026_06_tenant_time_idx
ON audit_events_2026_06 (tenant_id, occurred_at DESC);
```

RLS는 parent table에 적용한다. 다만 PostgreSQL 버전과 파티션 정책 상속 동작을 확인하고, 실제 파티션 접근이 정책을 타는지 테스트해야 한다.

### 2) tenant hash partitioning

tenant별 데이터가 균등하고, 쿼리가 대부분 tenant 단위라면 hash partitioning도 고려할 수 있다.

```sql
PARTITION BY HASH (tenant_id)
```

이 방식은 특정 파티션에 tenant subset을 모아 인덱스 크기와 maintenance 범위를 줄일 수 있다. 하지만 tenant별 retention이나 대형 tenant 분리에는 약하다.

### 3) 대형 tenant 물리 분리

일부 tenant가 너무 크면 shared table + RLS 모델이 운영상 불리할 수 있다. 이때는 해당 tenant를 별도 schema, 별도 database, 별도 cluster로 분리하는 하이브리드 모델을 고려한다.

RLS는 멀티테넌시의 유일한 답이 아니다. tenant isolation의 수준은 고객 규모, 규제, 성능, 비용, 운영 인력에 따라 달라진다.

- 작은 tenant 다수: shared table + RLS
- 중간 규모 B2B: shared table + RLS + partitioning
- 대형/규제 tenant: dedicated schema/database/cluster
- 초고위험 데이터: 물리 분리 + 별도 암호화/감사 체계

중요한 것은 RLS를 "보안 완료"로 착각하지 않는 것이다. RLS는 shared-table 모델에서 row boundary를 강제하는 좋은 도구지만, noisy neighbor, 백업 단위, 암호화 키, 장애 반경, 법적 데이터 위치 요구까지 자동으로 해결하지는 않는다.

---

## 마이그레이션 전략: 기존 테이블에 RLS를 안전하게 붙이는 순서

이미 운영 중인 서비스에 RLS를 도입할 때는 한 번에 켜면 위험하다. 쿼리 누락, role 문제, 성능 문제, 배치 실패가 한꺼번에 드러날 수 있다.

권장 순서는 다음과 같다.

### 1단계: 데이터 모델 점검

먼저 모든 tenant-scoped 테이블을 분류한다.

- 반드시 `tenant_id`가 있어야 하는 테이블
- tenant에 간접 귀속되는 테이블
- global reference table
- 운영/감사용 cross-tenant table
- join table
- materialized aggregate table

간접 귀속 테이블은 특히 위험하다. 예를 들어 `comments`가 `document_id`만 갖고 있고 `tenant_id`가 없다면, RLS 정책이 매번 documents를 join해야 한다. 이 방식은 가능하지만 비용과 복잡도가 크다. 실무에서는 핵심 하위 테이블에도 `tenant_id`를 중복 저장하는 편이 안전하고 빠른 경우가 많다.

```sql
ALTER TABLE comments ADD COLUMN tenant_id uuid;
-- backfill
-- NOT NULL, FK, index 추가
```

중복 저장은 정규화 관점에서는 찝찝할 수 있지만, 멀티테넌트 보안과 성능에서는 매우 실용적이다. 대신 `tenant_id` 정합성을 FK나 trigger, application invariant로 관리해야 한다.

### 2단계: runtime role 분리

앱이 table owner로 접속하고 있다면 먼저 role을 분리한다.

- `app_owner`: object owner
- `app_migrator`: migration
- `app_user`: runtime
- `app_readonly`: read-only runtime 또는 BI 제한

이 단계에서 권한 부족으로 깨지는 쿼리를 먼저 찾는다.

### 3단계: shadow policy 작성과 테스트

RLS를 바로 켜기 전에 정책 expression을 일반 WHERE 조건으로 넣어 주요 쿼리 성능을 본다.

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM documents
WHERE tenant_id = '...'
  AND status = 'ACTIVE';
```

대형 tenant, 소형 tenant, 빈 tenant, 권한 없는 tenant를 모두 테스트한다.

### 4단계: staging에서 RLS 적용

staging에서 실제 app_user role로 접속해 RLS를 켠다.

```sql
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
```

처음에는 `FORCE ROW LEVEL SECURITY`까지 바로 켜지 말고 owner/role 차이를 관찰할 수 있다. 하지만 최종 운영에서는 owner 우회 여부를 명확히 결정해야 한다.

### 5단계: 배치·관리자·리포트 경로 점검

대부분의 사고는 온라인 API가 아니라 주변 경로에서 난다.

- nightly batch
- customer support tool
- admin dashboard
- BI query
- search indexing
- webhook retry
- data correction script
- migration verification

각 경로가 어떤 DB role로 접속하고, tenant context를 어떻게 설정하며, cross-tenant 접근이 필요한지 문서화한다.

### 6단계: production rollout

운영 적용은 테이블별 또는 기능별로 나누는 편이 안전하다. 적용 직후 아래를 관찰한다.

- 권한 오류 증가
- 빈 결과 증가
- slow query 증가
- index scan/seq scan 변화
- connection pool transaction 경계 오류
- batch 실패
- support tool 오류

RLS 도입은 보안 변경이면서 동시에 runtime behavior 변경이다. feature flag처럼 rollout하고 rollback 경로를 준비하는 편이 좋다.

---

## 테스트 전략: RLS는 단위 테스트보다 "권한 행렬 테스트"가 중요하다

RLS는 로직이 단순해 보여도 테스트를 소홀히 하면 위험하다. 특히 owner role로 테스트하면 아무 의미가 없다. 반드시 실제 runtime role로 테스트해야 한다.

### 테스트 축

최소한 아래 축을 조합한다.

- role: app_user, support_reader, audit_reader, migrator
- tenant context: tenant A, tenant B, missing tenant, invalid tenant
- command: SELECT, INSERT, UPDATE, DELETE
- row state: own tenant row, other tenant row, global row, deleted/archived row
- write path: tenant_id 유지, tenant_id 변경 시도, project_id 변경 시도
- function path: SECURITY DEFINER 함수, 일반 SQL, view, batch function

### 예시 테스트 케이스

```sql
-- tenant A context
BEGIN;
SET LOCAL ROLE app_user;
SET LOCAL app.tenant_id = 'tenant-a-uuid';

-- A row는 보여야 한다
SELECT count(*) FROM documents WHERE tenant_id = 'tenant-a-uuid';

-- B row는 직접 조건을 줘도 안 보여야 한다
SELECT count(*) FROM documents WHERE tenant_id = 'tenant-b-uuid';

-- B tenant row insert는 실패해야 한다
INSERT INTO documents (id, tenant_id, project_id, title, body)
VALUES ('...', 'tenant-b-uuid', '...', 'x', 'x');

ROLLBACK;
```

자동 테스트에서는 기대 결과를 명확히 해야 한다.

- 조회는 0 rows가 맞는가, 오류가 맞는가?
- insert/update 위반은 어떤 SQLSTATE로 실패하는가?
- context 누락은 반드시 실패하는가?
- support role은 승인된 tenant만 보는가?

### property-style 테스트도 유용하다

권한 테스트는 예시 몇 개보다 invariant가 중요하다.

- 어떤 app_user도 자기 tenant가 아닌 row id를 알더라도 읽을 수 없어야 한다.
- 어떤 app_user도 row의 tenant_id를 다른 tenant로 바꿀 수 없어야 한다.
- 어떤 app_user도 `INSERT ... SELECT`로 다른 tenant 데이터를 복제할 수 없어야 한다.
- support_reader는 ticket에 매핑된 tenant 범위 밖을 볼 수 없어야 한다.
- SECURITY DEFINER 함수는 허용된 business action 외 임의 row 변경을 하지 않아야 한다.

이 invariant를 테스트 데이터 생성기로 반복 검증하면 RLS 회귀를 잡기 쉽다.

---

## 관측과 운영: RLS는 켰는지보다 "정책이 실제로 기대대로 작동하는지"를 봐야 한다

PostgreSQL은 RLS가 적용되어 row가 숨겨졌다는 사실을 매번 별도 로그로 남기지 않는다. 그래서 운영 관측성은 직접 설계해야 한다.

### 1) 권한 오류와 빈 결과를 구분한다

RLS에서 `SELECT`는 보통 권한 오류가 아니라 row가 없는 것처럼 보인다. 반면 `INSERT/UPDATE`의 `WITH CHECK` 위반은 오류가 날 수 있다. 애플리케이션 로그에서 아래를 구분해야 한다.

- 실제 데이터가 없음
- 권한상 보이지 않음
- tenant context 누락
- policy 위반으로 쓰기 실패
- role 권한 부족

사용자에게는 모두 404처럼 보일 수 있지만, 운영 로그에서는 다르게 남겨야 한다.

### 2) tenant context를 request log와 DB log에 연결한다

애플리케이션 로그에는 tenant_id, user_id, request_id를 남긴다. DB에는 `application_name`에 request class나 service name을 넣고, 가능하면 query tag를 사용한다.

```sql
SET LOCAL application_name = 'api:documents:list';
```

PostgreSQL 기본 로그에 custom setting이 자동으로 찍히는 것은 아니므로, 애플리케이션 로그와 query 로그를 연결할 수 있는 request id 전략이 필요하다.

### 3) RLS 정책 변경은 마이그레이션보다 더 엄격하게 리뷰한다

RLS 정책 변경은 코드 변경보다 데이터 노출 범위를 직접 바꾼다. 따라서 리뷰 체크리스트가 필요하다.

- 어떤 role에 영향을 주는가?
- 읽기와 쓰기 모두 검토했는가?
- `USING`과 `WITH CHECK`가 대칭이어야 하는가, 의도적으로 다른가?
- context 누락 시 fail-closed인가?
- owner/definer 우회가 있는가?
- 인덱스와 실행 계획을 확인했는가?
- support/audit/batch 경로 영향은 확인했는가?
- rollback하면 기존 데이터 정합성은 유지되는가?

---

## 트레이드오프: RLS를 쓰면 무엇을 얻고 무엇을 잃는가

RLS는 강력하지만 공짜가 아니다. 선택 전에 장단점을 분명히 봐야 한다.

### 장점 1: tenant 조건 누락 사고를 구조적으로 줄인다

가장 큰 장점이다. 개발자가 쿼리 하나에 tenant 조건을 빠뜨려도 DB가 막아준다. 특히 임시 쿼리, 신규 기능, 배치, 관리자 도구에서 방어력이 커진다.

### 장점 2: 보안 정책이 테이블 근처에 남는다

애플리케이션 서비스가 여러 개로 늘어나도 DB 정책은 중앙에 남는다. Node.js API, Python worker, Java batch가 같은 테이블을 보더라도 동일한 row boundary를 강제할 수 있다.

### 장점 3: 테스트 가능한 보안 계약이 된다

RLS 정책은 SQL 객체이므로 migration, review, test 대상으로 만들 수 있다. "우리 팀은 tenant 조건을 잘 붙인다"보다 훨씬 검증 가능하다.

### 단점 1: 디버깅이 어려워진다

쿼리만 봐서는 왜 row가 안 보이는지 알기 어렵다. 개발자는 실제 role, session setting, 정책, owner, view, definer function을 함께 봐야 한다. 온보딩 비용이 생긴다.

### 단점 2: 성능 튜닝 표면이 늘어난다

정책 predicate가 모든 쿼리에 붙는다. 인덱스, plan cache, tenant skew, policy 함수 비용을 같이 봐야 한다. 기존 쿼리 튜닝보다 한 층 더 복잡하다.

### 단점 3: 예외 권한 설계가 어려워진다

지원, 감사, 배치, 마이그레이션은 cross-tenant 접근이 필요할 수 있다. 이 예외를 아무렇게나 열면 RLS의 의미가 약해진다. 반대로 너무 엄격하면 운영이 막힌다.

### 단점 4: ORM과 충돌할 수 있다

일부 ORM은 connection/transaction boundary, prepared statement, migration role, relation loading을 추상화한다. RLS를 쓰려면 ORM이 DB session context를 어떻게 다루는지 정확히 알아야 한다.

결론적으로 RLS는 보안 민감한 멀티테넌트 서비스에는 강력히 추천할 수 있지만, 도입은 설계 작업이다. "켜면 안전해진다"가 아니라 **role, context, policy, index, test를 함께 배포해야 안전해진다**.

---

## 흔한 실수 12가지

### 1) 애플리케이션이 table owner로 접속한다

RLS를 켰지만 런타임 role이 owner라 정책을 우회한다. 가장 먼저 role 구조를 분리해야 한다.

### 2) `FORCE ROW LEVEL SECURITY` 필요 여부를 검토하지 않는다

owner 우회를 허용할지, owner에게도 강제할지 명확히 정해야 한다. 테스트 환경과 운영 환경의 owner 구조가 다르면 더 위험하다.

### 3) `USING`만 만들고 `WITH CHECK`를 빠뜨린다

읽기는 막았지만 insert/update로 다른 tenant row를 만들 수 있다. 쓰기 정책은 반드시 별도 테스트한다.

### 4) session-level `SET`을 connection pool에서 사용한다

이전 요청 tenant context가 다음 요청으로 새는 사고가 날 수 있다. transaction-local `SET LOCAL`을 기본으로 삼아야 한다.

### 5) context 누락을 조용히 0 rows로 처리한다

tenant context가 없으면 보통 오류가 나는 편이 낫다. 조용한 빈 결과는 장애를 늦게 발견하게 만든다.

### 6) 정책 함수를 너무 똑똑하게 만든다

RLS 함수 안에 복잡한 권한 엔진을 넣으면 모든 쿼리가 느려지고 추론이 어려워진다. 정책은 단순하고 인덱스 친화적으로 유지한다.

### 7) `SECURITY DEFINER`에 `search_path`를 고정하지 않는다

definer 함수의 기본 보안 수칙이다. search_path를 고정하고, 가능하면 schema-qualified object name을 사용한다.

### 8) support/admin 예외를 app_user 정책에 섞는다

예외가 늘어나면 정책이 `OR` 조건 덩어리가 된다. role을 분리하고, 예외는 좁은 view나 function으로 제공한다.

### 9) view를 보안 경계로 믿고 실제 role 테스트를 하지 않는다

view owner, invoker/definer 성격, PostgreSQL 버전에 따라 RLS 적용 기대가 달라질 수 있다. 반드시 실제 접속 role로 검증한다.

### 10) tenant_id 인덱스 없이 RLS를 켠다

보안은 좋아졌지만 모든 쿼리가 느려질 수 있다. RLS 적용 전후 실행 계획을 비교해야 한다.

### 11) 마이그레이션과 배치를 잊는다

온라인 API만 통과하고 nightly batch가 전부 실패하는 일이 흔하다. 모든 DB 접속 경로를 inventory로 만들어야 한다.

### 12) RLS를 데이터 암호화나 감사 로그 대체물로 오해한다

RLS는 row 접근 제어다. 암호화, masking, audit, retention, backup isolation은 별도 설계가 필요하다.

---

## 운영 체크리스트

RLS를 production에 적용하기 전 최소한 아래를 확인한다.

### 데이터 모델

- [ ] tenant-scoped 테이블 목록이 정리되어 있는가?
- [ ] 각 테이블에 직접 또는 간접 tenant boundary가 있는가?
- [ ] 간접 tenant 테이블은 성능과 정책 복잡도를 감당할 수 있는가?
- [ ] 핵심 하위 테이블에 `tenant_id` 중복 저장이 필요한지 검토했는가?
- [ ] tenant_id 정합성을 FK, unique key, trigger, application invariant 중 무엇으로 보장할지 정했는가?

### Role과 권한

- [ ] table owner와 runtime app role이 분리되어 있는가?
- [ ] app role에 superuser 또는 `BYPASSRLS`가 없는가?
- [ ] `FORCE ROW LEVEL SECURITY` 적용 여부를 테이블별로 결정했는가?
- [ ] migration role과 batch role의 권한이 분리되어 있는가?
- [ ] support/audit role은 필요한 범위만 볼 수 있는가?

### 정책

- [ ] `SELECT`, `INSERT`, `UPDATE`, `DELETE`별 정책이 명확한가?
- [ ] `USING`과 `WITH CHECK`의 차이를 반영했는가?
- [ ] context 누락 시 fail-closed인가?
- [ ] 정책 함수는 단순하고 `STABLE`이며 인덱스 친화적인가?
- [ ] 예외 정책이 일반 정책에 과도한 `OR`로 섞이지 않았는가?

### 애플리케이션

- [ ] request transaction 시작 후 `SET LOCAL app.tenant_id`를 설정하는가?
- [ ] PgBouncer transaction pooling과 호환되는가?
- [ ] ORM relation loading과 lazy loading이 tenant context 안에서 실행되는가?
- [ ] background job도 tenant context를 명시적으로 설정하는가?
- [ ] cross-tenant job은 별도 role과 별도 감사 로그를 쓰는가?

### 성능

- [ ] RLS 적용 전후 `EXPLAIN (ANALYZE, BUFFERS)`를 비교했는가?
- [ ] tenant_id 포함 복합 인덱스가 주요 쿼리에 맞게 있는가?
- [ ] 대형 tenant와 소형 tenant 모두 plan을 확인했는가?
- [ ] policy 내부 `EXISTS` 대상 테이블에 적절한 인덱스가 있는가?
- [ ] prepared statement/generic plan 이슈를 확인했는가?

### 보안과 운영

- [ ] `SECURITY DEFINER` 함수는 search_path를 고정했는가?
- [ ] definer 함수 owner 권한이 최소화되어 있는가?
- [ ] definer 함수 입력이 좁고 business action 단위인가?
- [ ] view가 보안 경계라면 `security_invoker` 또는 실제 동작을 검증했는가?
- [ ] 정책 변경에 코드 리뷰와 테스트 게이트가 있는가?
- [ ] 권한 오류, policy 위반, context 누락이 로그에서 구분되는가?
- [ ] rollback 절차가 준비되어 있는가?

---

## 한 줄 정리

PostgreSQL RLS는 멀티테넌트 SaaS에서 `tenant_id` 조건을 개발자 기억에 맡기지 않고 데이터베이스의 강제 계약으로 만드는 도구지만, 안전하게 쓰려면 정책 SQL보다 먼저 **role 분리, transaction-local tenant context, `USING`/`WITH CHECK`, `SECURITY DEFINER` 통제, tenant-aware 인덱스, 실제 role 테스트**를 함께 설계해야 한다.
