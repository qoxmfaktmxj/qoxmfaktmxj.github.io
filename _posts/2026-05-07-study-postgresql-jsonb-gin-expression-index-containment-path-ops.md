---
layout: post
title: "PostgreSQL JSONB 인덱싱 실전: GIN, jsonb_path_ops, Expression Index로 느린 메타데이터 검색을 운영 가능한 상태로 만드는 법"
date: 2026-05-07 11:40:00 +0900
categories: [sql]
tags: [study, sql, postgresql, jsonb, gin, indexing, expression-index, jsonb-path-ops, query-tuning, performance]
permalink: /sql/2026/05/07/study-postgresql-jsonb-gin-expression-index-containment-path-ops.html
---

## 배경: 왜 JSONB는 처음엔 편한데 데이터가 쌓이면 갑자기 "검색 가능한 쓰레기통"이 되기 쉬울까

PostgreSQL에서 `jsonb`는 정말 강력하다.

- 제품 스키마가 자주 바뀌는 이벤트 payload를 빨리 저장할 수 있다.
- 외부 API 응답 원문을 유실 없이 적재할 수 있다.
- 고객별 커스텀 속성, feature flag, 실험 설정, webhook 메타데이터를 유연하게 담을 수 있다.
- 정규화 전에 탐색적으로 데이터를 쌓아두고 나중에 모델링할 여지를 남길 수 있다.

그래서 많은 팀이 아래 같은 흐름으로 `jsonb`를 도입한다.

- 처음에는 몇 개 key만 저장한다.
- 곧 검색 조건이 늘어난다.
- 그러다 `payload->>'status'`, `payload @> ...`, `metadata ? 'campaign_id'` 같은 쿼리가 API와 배치 전반에 퍼진다.
- 어느 날부터는 분명 인덱스를 만들었다고 생각했는데도 쿼리가 느리고, 쓰기 성능도 같이 흔들린다.

이 시점에 자주 나오는 오해가 있다.

- JSONB는 GIN 인덱스 하나만 만들면 다 빨라진다.
- `@>`만 쓰면 무조건 잘 탄다.
- key 하나를 뽑아 비교하는 쿼리도 JSONB GIN이 알아서 해결해 준다.
- `jsonb_ops`와 `jsonb_path_ops`는 그냥 취향 차이다.
- JSONB 검색이 느리면 GIN 인덱스를 더 만들면 된다.
- JSONB가 유연하니까 스키마 설계는 나중에 생각해도 된다.

실무에서는 이 여섯 가지가 거의 다 위험한 단순화다.

`jsonb`의 핵심 난점은 저장이 아니라 **검색 패턴이 한 종류가 아니라는 점**이다.

- 어떤 쿼리는 특정 key 존재 여부를 본다.
- 어떤 쿼리는 특정 key의 문자열 값 equality를 본다.
- 어떤 쿼리는 JSON 전체 일부 포함 여부를 본다.
- 어떤 쿼리는 배열 안의 원소 포함 여부를 본다.
- 어떤 쿼리는 `created_at` 같은 일반 컬럼과 함께 좁혀서 최근 데이터만 본다.
- 어떤 쿼리는 정렬과 페이지네이션까지 필요하다.

즉 `jsonb`는 "한 종류의 검색 문제"가 아니라 **여러 종류의 조건이 섞인 검색 표면**이다. 그래서 인덱스도 하나의 만능 무기가 아니라, **쿼리 형태별로 다른 전략**이 필요하다.

오늘 글은 PostgreSQL `jsonb` 인덱싱을 문법 소개가 아니라 **운영 가능한 검색 설계** 관점에서 정리한다. 목표는 아래 질문에 답하는 것이다.

- JSONB 검색이 느릴 때 가장 먼저 구분해야 할 쿼리 형태는 무엇인가?
- GIN은 정확히 어떤 쿼리에 강하고, 어떤 쿼리에는 기대보다 약한가?
- `jsonb_ops`와 `jsonb_path_ops`는 무엇이 다르고 언제 골라야 하는가?
- `payload->>'status' = 'PAID'` 같은 비교는 왜 expression index가 더 나은 경우가 많은가?
- GIN 하나로 끝내지 말고 B-tree와 어떻게 역할을 분리해야 하는가?
- JSONB 업데이트가 많은 테이블에서 인덱스 비용은 왜 급격히 커지는가?
- 흔한 실수와 체크리스트는 무엇인가?

핵심만 먼저 요약하면 이렇다.

1. JSONB 튜닝의 출발점은 `jsonb` 자체가 아니라 **실제 쿼리 패턴 분류**다.
2. GIN은 만능 인덱스가 아니라 **containment/존재성 기반 검색**에 특히 강한 구조다.
3. `payload->>'field' = 'value'` 같은 scalar equality는 GIN보다 **expression B-tree index**가 더 직관적이고 빠를 때가 많다.
4. `jsonb_ops`는 더 넓은 연산자를 지원하지만 더 크고 무거울 수 있고, `jsonb_path_ops`는 더 좁은 목적에 최적화되지만 만능이 아니다.
5. JSONB 인덱스 설계는 읽기 성능만이 아니라 **쓰기 비용, pending list, vacuum, bloat, HOT 저해**까지 같이 봐야 한다.
6. 좋은 설계는 "JSONB에 다 넣고 GIN 하나"가 아니라, **자주 조회하는 필드는 승격시키고 나머지는 유연하게 남기는 혼합 모델**이다.

---

## 먼저 큰 그림: JSONB 인덱싱은 "문서 저장"이 아니라 "검색 계약"을 설계하는 일이다

많은 팀이 `jsonb`를 도입할 때의 마음은 비슷하다.

- 지금은 스키마가 자주 바뀐다.
- 일단 유연하게 넣고 나중에 정리하자.
- PostgreSQL이니까 검색도 어느 정도 되겠지.

여기까지는 자연스럽다. 문제는 대개 그다음이다.

예를 들어 `events` 테이블이 있다고 하자.

```sql
CREATE TABLE events (
  id bigserial primary key,
  tenant_id bigint not null,
  event_type text not null,
  created_at timestamptz not null,
  payload jsonb not null
);
```

초기에는 `payload`가 단순 저장용처럼 보인다.

- 결제 이벤트면 결제 수단, 카드 브랜드, 실패 코드
- 주문 이벤트면 주문 채널, 쿠폰, 배송 타입
- 마케팅 이벤트면 캠페인 id, 유입 소스, 실험 버전

하지만 제품이 커지면 `payload`는 금방 조회 표면이 된다.

- 실패한 카드 결제만 보고 싶다.
- 특정 캠페인으로 유입된 최근 구매만 보고 싶다.
- `country = KR`이면서 `is_guest = false`인 로그인 이벤트를 찾고 싶다.
- 배열 안에 특정 feature flag가 있던 요청만 보고 싶다.

즉 JSONB는 "유연한 저장소"였다가 곧 **조건 검색 대상**이 된다.

여기서 중요한 태도는 이것이다.

> **JSONB 컬럼을 도입하는 순간, 나중에 어떤 조건으로 검색할지까지 같이 설계해야 한다.**

왜냐하면 쿼리 형태에 따라 가장 맞는 인덱스가 완전히 달라지기 때문이다.

- 특정 key 존재 여부 → GIN이 잘 맞을 수 있다.
- key의 scalar equality → expression B-tree가 더 자연스러울 수 있다.
- 최근 7일 + tenant_id + JSON key equality → 일반 컬럼 인덱스와 JSON 인덱스를 조합해야 할 수 있다.
- 정렬까지 필요한 조회 → GIN만으로는 부족하다.

이 감각이 없으면 흔히 아래 같은 상태가 된다.

- `payload` 전체에 GIN 하나 생성
- API는 `payload->>'status' = 'PAID'` 형태로 작성
- planner는 expression 비교 때문에 기대만큼 GIN을 못 씀
- 팀은 인덱스가 있는데 왜 느린지 혼란스러움
- 결국 expression index를 또 만들고, write cost가 급증함

즉 JSONB 인덱싱의 핵심은 인덱스 문법이 아니라 **쿼리 계약을 먼저 분류하는 것**이다.

---

## 핵심 개념 1: JSONB 검색 패턴은 크게 네 종류로 나눠서 봐야 한다

실무에서 `jsonb` 관련 쿼리는 대체로 아래 네 가지로 분류하면 판단이 쉬워진다.

### 1) 존재 여부 확인

```sql
WHERE payload ? 'campaign_id'
```

혹은 배열/여러 key에 대해:

```sql
WHERE payload ?| array['campaign_id', 'utm_source']
```

이런 쿼리는 "이 key가 있느냐"가 핵심이다.

### 2) containment 포함 여부 확인

```sql
WHERE payload @> '{"status":"PAID"}'::jsonb
```

혹은 더 복합적으로:

```sql
WHERE payload @> '{"payment":{"method":"card"}}'::jsonb
```

이건 JSON 문서가 특정 부분 구조를 포함하는지 보는 패턴이다.

### 3) scalar 추출 후 일반 비교

```sql
WHERE payload->>'status' = 'PAID'
```

```sql
WHERE (payload->>'retry_count')::int >= 3
```

```sql
WHERE payload->>'country' IN ('KR', 'JP')
```

이건 사실상 JSON 내부 값을 꺼내 **일반 SQL 값처럼 비교**하는 패턴이다.

### 4) 일반 컬럼과 결합된 혼합 검색

```sql
WHERE tenant_id = 42
  AND created_at >= now() - interval '7 days'
  AND payload->>'status' = 'FAILED'
ORDER BY created_at DESC
LIMIT 100;
```

실제 API는 대개 이 네 번째 패턴이 많다. JSON만 보지 않고, 테넌트·시간 범위·상태·정렬이 함께 들어간다.

### 왜 이 분류가 중요할까

이 네 패턴은 전부 `jsonb`를 쓰지만, planner와 인덱스가 보는 관점은 다르다.

- 존재 여부와 containment는 GIN과 잘 맞을 수 있다.
- scalar equality/range는 expression B-tree가 더 직접적일 수 있다.
- 시간 범위 + 정렬이 중요하면 B-tree가 주도권을 가져야 할 수 있다.
- 하나의 API 안에서 BitmapAnd나 두 단계 필터가 더 나을 수도 있다.

즉 **JSONB = GIN**으로 단순화하면, 절반은 맞고 절반은 틀리다.

좋은 팀은 먼저 대표 쿼리를 아래처럼 분류한다.

1. key 존재 확인형
2. 포함 여부형
3. scalar 값 비교형
4. 일반 컬럼 결합형
5. 정렬/페이지네이션 동반형

이 표를 먼저 만들면, 어떤 필드는 GIN에 맡기고 어떤 필드는 승격시켜 B-tree로 다뤄야 하는지 훨씬 선명해진다.

---

## 핵심 개념 2: GIN은 JSON 문서를 "통째로 빠르게 찾는 마법"이 아니라 "문서 안의 토큰 역색인"에 가깝다

GIN을 이해할 때 가장 도움이 되는 비유는 검색 엔진의 inverted index다.

일반 B-tree 인덱스는 "이 값의 순서는 무엇인가"에 강하다.

- equality
- range
- order by
- prefix-like(상황에 따라)

반면 GIN은 "이 문서 안에 어떤 구성 요소가 들어 있는가"를 빠르게 찾는 쪽에 가깝다.

JSONB에 GIN을 만들면 PostgreSQL은 문서 내부의 key, 값, 경로 같은 검색 단서를 인덱싱해 두고, 특정 조건과 매칭되는 row 후보를 빠르게 찾는다.

예를 들어:

```sql
CREATE INDEX idx_events_payload_gin
ON events USING gin (payload);
```

이 인덱스는 아래 같은 조건에 특히 잘 맞을 수 있다.

```sql
WHERE payload @> '{"status":"PAID"}'::jsonb
```

```sql
WHERE payload ? 'campaign_id'
```

### GIN이 강한 이유

`jsonb` 전체를 row마다 순회하지 않고, 인덱스에서 조건과 관련된 후보 row 집합을 먼저 좁힐 수 있기 때문이다.

특히 아래 상황에서 체감 이득이 크다.

- 테이블이 크다.
- JSONB 문서가 중간 이상 크기다.
- 조건이 충분히 selective하다.
- API가 containment/존재 여부 검색을 자주 한다.

### 하지만 GIN의 한계도 분명하다

#### 1) 정렬을 해결하지 않는다

```sql
WHERE payload @> '{"status":"FAILED"}'::jsonb
ORDER BY created_at DESC
LIMIT 100;
```

GIN은 후보 row를 찾는 데 도움을 줄 수 있지만, `ORDER BY created_at DESC` 자체를 만족시키지는 못한다. 결국 정렬 전략이나 다른 인덱스 설계가 함께 필요할 수 있다.

#### 2) scalar 추출 비교를 항상 가장 잘 푸는 것은 아니다

```sql
WHERE payload->>'status' = 'FAILED'
```

이건 containment가 아니라 "텍스트 값 비교"다. 이 패턴은 expression index가 더 직접적일 때가 많다.

#### 3) 쓰기 비용이 작지 않다

JSONB에 GIN을 걸면 insert/update/delete 때 인덱스 유지비가 커진다. 특히 문서가 크거나 key 다양성이 높으면 더 그렇다.

#### 4) recheck가 발생할 수 있다

GIN은 후보를 빠르게 찾지만, 실제 row에서 다시 조건을 확인하는 recheck가 붙는 경우가 있다. 즉 인덱스 hit = 최종 정답은 아니다.

### 중요한 결론

GIN은 강력하지만, 본질은 **JSON 내부 포함/존재 검색을 위한 대형 역색인**이다. 그래서 다음 질문을 먼저 해야 한다.

- 나는 문서의 일부 포함 여부를 찾는가?
- 아니면 key를 뽑아 일반 값처럼 비교하는가?
- 정렬과 시간 범위가 더 중요한가?

이 구분 없이 GIN부터 만들면, 인덱스는 크고 무거운데 체감 속도는 기대보다 작을 수 있다.

---

## 핵심 개념 3: `jsonb_ops`와 `jsonb_path_ops`는 성능 튜닝 이전에 "지원 연산자 범위"가 다르다

GIN을 만들 때 흔히 놓치는 선택지가 operator class다.

대표적으로 많이 보는 것이 아래 두 가지다.

```sql
CREATE INDEX idx_events_payload_gin_ops
ON events USING gin (payload jsonb_ops);
```

```sql
CREATE INDEX idx_events_payload_gin_path_ops
ON events USING gin (payload jsonb_path_ops);
```

이 둘은 단순히 "어느 쪽이 더 빠른가" 문제가 아니다. 먼저 **어떤 연산자를 주로 쓸 것인가**가 다르다.

### `jsonb_ops`

보통 기본값으로 많이 쓰이고, 더 넓은 종류의 JSONB 연산을 지원하는 쪽이다. 존재 여부(`?`, `?|`, `?&`)와 containment 계열을 폭넓게 다루고 싶은 경우에 더 안전한 기본값이 된다.

장점:

- 지원 범위가 넓다.
- 여러 형태의 JSONB 검색을 한 인덱스로 수용하기 쉽다.
- key 존재 여부 검색이 중요한 테이블에 유리하다.

단점:

- 인덱스가 더 커질 수 있다.
- write 비용도 더 무거워질 수 있다.
- 정말 containment 중심 워크로드라면 과한 범용성일 수 있다.

### `jsonb_path_ops`

더 좁은 목적에 최적화된 쪽으로 생각하는 편이 실무적으로 좋다. 특히 containment (`@>`) 중심 패턴이 아주 많고, 존재 여부 연산 전체를 다 포괄할 필요가 없을 때 고려 가치가 크다.

장점:

- containment 중심 검색에서 더 작은 인덱스와 더 좋은 locality를 기대할 수 있다.
- 범위가 좁은 만큼 효율이 좋을 수 있다.

단점:

- 더 넓은 JSONB 연산자를 다 받아주길 기대하면 안 된다.
- `?` 계열 존재 여부 검색이 핵심이면 맞지 않을 수 있다.
- 팀이 연산자 사용 규칙을 안 지키면 "인덱스가 있는데 왜 안 타지?" 문제가 생긴다.

### 선택 기준을 한 문장으로 줄이면

- **여러 연산자를 폭넓게 쓰고 존재 여부 검색도 중요하다 → `jsonb_ops`**
- **대부분이 `@>` 중심이고 인덱스 크기/효율을 더 중시한다 → `jsonb_path_ops`**

### 실무에서 정말 중요한 포인트

operator class 선택은 DDL 취향이 아니라 **애플리케이션 쿼리 규약**과 연결된다.

예를 들어 팀이 아래 둘을 섞어 쓰면:

- 어떤 API는 `payload->>'status' = 'PAID'`
- 어떤 API는 `payload @> '{"status":"PAID"}'`
- 어떤 API는 `payload ? 'campaign_id'`

한 종류의 GIN만으로 모두 만족시키기 어렵다. 결국 아래 둘 중 하나를 해야 한다.

1. 쿼리 패턴을 표준화한다.
2. 중요한 필드는 별도 expression index/일반 컬럼으로 승격한다.

즉 operator class 선택은 인덱스 최적화라기보다, **우리가 JSON을 어떤 방식으로 질의할지의 표준화 문제**다.

---

## 핵심 개념 4: `payload->>'field' = 'value'`는 GIN보다 expression B-tree index가 더 나은 경우가 많다

이건 실무에서 가장 자주 헷갈리는 지점 중 하나다.

많은 팀이 `jsonb` 전체에 GIN을 걸고 나서 아래 쿼리도 당연히 빨라질 거라 기대한다.

```sql
SELECT id, created_at
FROM payments
WHERE payload->>'status' = 'FAILED';
```

그런데 이 패턴은 containment가 아니라 **텍스트 추출 후 equality 비교**다. 이 경우 아래 같은 expression index가 더 직접적이다.

```sql
CREATE INDEX idx_payments_payload_status
ON payments ((payload->>'status'));
```

정수 비교가 필요하면:

```sql
CREATE INDEX idx_jobs_retry_count
ON jobs (((payload->>'retry_count')::int));
```

### 왜 expression index가 강할까

planner 입장에서 이건 그냥 일반 scalar 값 인덱스와 비슷해지기 때문이다.

- equality 비교가 직관적이다.
- B-tree 비용 모델이 익숙하다.
- 정렬과 결합하기 쉽다.
- 범위 비교(`>=`, `BETWEEN`)도 다루기 쉽다.

예를 들어 최근 실패 작업 100건을 보려면 아래처럼 더 직접적인 인덱스를 만들 수 있다.

```sql
CREATE INDEX idx_jobs_status_created_at
ON jobs ((payload->>'status'), created_at DESC);
```

이건 다음 쿼리에 매우 잘 맞는다.

```sql
SELECT id, created_at
FROM jobs
WHERE payload->>'status' = 'FAILED'
ORDER BY created_at DESC
LIMIT 100;
```

GIN은 정렬을 해결하지 못하지만, B-tree expression index는 equality + order by까지 한 번에 맞출 수 있다.

### containment로 억지 변환하는 것이 항상 좋은가?

어떤 팀은 expression index를 만들기 싫어서 쿼리를 아래처럼 바꾼다.

```sql
WHERE payload @> '{"status":"FAILED"}'::jsonb
```

이게 틀린 것은 아니다. 하지만 항상 좋은 선택도 아니다.

- 쿼리 가독성이 떨어질 수 있다.
- 숫자/불리언/문자열 타입이 섞이면 표현 실수가 늘 수 있다.
- 정렬/복합 조건에서는 B-tree expression이 더 자연스러울 수 있다.
- 특정 필드가 사실상 1급 비즈니스 속성이면 JSON 안에만 둘 이유가 약해진다.

### 좋은 판단 기준

- containment/문서 포함 여부가 핵심 → GIN 우선 검토
- 특정 key 값을 일반 컬럼처럼 자주 비교 → expression B-tree 우선 검토
- 그 값으로 정렬/범위 검색/페이지네이션까지 함 → expression B-tree 쪽이 더 자주 이김

실무에서는 `jsonb` 전체 GIN + 자주 쓰는 몇 개 key expression index 조합이 아주 흔하다.

---

## 핵심 개념 5: JSONB 인덱싱은 결국 "승격할 필드"를 고르는 작업이다

JSONB를 오래 운영하다 보면 결국 같은 질문에 도착한다.

> **이 필드는 아직도 문서의 일부인가, 아니면 이미 중요한 1급 조회 속성인가?**

예를 들어 아래 세 필드를 생각해보자.

- `campaign_id`
- `status`
- `experiment_variant`

세 필드 모두 처음엔 `payload` 안에 들어 있어도 이상하지 않다. 하지만 시간이 지나면 성격이 달라진다.

### 아직 JSONB 안에 남겨도 괜찮은 경우

- 일시적으로만 조회한다.
- 조건에 거의 안 걸린다.
- 값 종류가 다양하지만 비즈니스 핵심이 아니다.
- 저장은 필요하지만 검색 빈도는 낮다.

### 승격을 고려해야 하는 경우

- 거의 모든 API가 이 값을 필터로 쓴다.
- 운영 대시보드와 배치가 반복해서 이 값을 조건으로 쓴다.
- 정렬, group by, partial index, unique-like 규칙에 관여한다.
- 타입 안정성이 중요하다.
- 값 해석이 코드 전체의 핵심 계약이 되었다.

예를 들어 `status`가 결제 흐름의 핵심이라면, 아래처럼 생각하는 편이 더 낫다.

- `status`는 일반 컬럼으로 승격
- 부가 메타데이터만 `payload`에 남김

```sql
CREATE TABLE payments (
  id bigserial primary key,
  tenant_id bigint not null,
  status text not null,
  created_at timestamptz not null,
  payload jsonb not null
);
```

이렇게 하면 얻는 것이 많다.

- 단순 B-tree 인덱스 사용 가능
- 통계 품질이 더 좋아짐
- 제약/partial index/집계가 쉬워짐
- JSON 파싱/캐스팅 실수가 줄어듦

즉 JSONB 설계의 성숙 단계는 보통 이렇다.

1. 초기엔 유연성을 위해 JSONB에 많이 넣는다.
2. 운영하면서 실제 조회 패턴이 드러난다.
3. 중요한 필드를 점진적으로 승격한다.
4. 남는 JSONB는 진짜 비정형/보조 메타데이터 용도로 유지한다.

이걸 실패하면 어떤 일이 생길까?

- 핵심 비즈니스 속성이 JSON 안에 계속 갇혀 있다.
- 인덱스가 점점 복잡해진다.
- 쿼리마다 캐스팅/표현식이 달라진다.
- 데이터 품질 제약을 걸기 어려워진다.
- 결국 "유연성"이 아니라 "애매한 구조"가 된다.

JSONB는 목적지가 아니라 완충지대인 경우가 많다.

---

## 핵심 개념 6: 일반 컬럼과 JSONB를 함께 검색하는 쿼리는 "하나의 만능 인덱스"보다 역할 분리가 중요하다

실제 서비스에서 더 많은 쿼리는 이런 형태다.

```sql
SELECT id, created_at, payload
FROM webhook_logs
WHERE tenant_id = $1
  AND created_at >= $2
  AND created_at < $3
  AND payload @> '{"delivery_status":"FAILED"}'::jsonb
ORDER BY created_at DESC
LIMIT 100;
```

이 쿼리의 핵심은 네 가지가 동시에 있다는 점이다.

- tenant filter
- time range
- JSON condition
- order by + limit

이때 많은 사람이 "복합 GIN 하나로 끝낼 수 있지 않을까"를 떠올리지만, 실무에서는 **역할 분리**가 더 중요할 때가 많다.

예를 들면 아래 조합이다.

```sql
CREATE INDEX idx_webhook_logs_tenant_created_at
ON webhook_logs (tenant_id, created_at DESC);

CREATE INDEX idx_webhook_logs_payload_gin
ON webhook_logs USING gin (payload jsonb_path_ops);
```

planner는 상황에 따라:

- 시간 범위와 테넌트 필터를 먼저 강하게 줄이고
- 그 후보에 JSON 조건을 적용하거나
- 두 인덱스 bitmap을 조합할 수 있다

물론 언제나 이상적으로 동작하는 것은 아니다. 하지만 중요한 포인트는 이것이다.

> **일반 컬럼과 JSON 조건이 함께 있을 때는 GIN 하나에 모든 책임을 몰지 않는 편이 더 예측 가능하다.**

### 왜 역할 분리가 유리한가

#### 1) 정렬 책임을 B-tree가 가져갈 수 있다

최근 100건 같은 조회는 B-tree `(tenant_id, created_at DESC)`가 훨씬 자연스럽다.

#### 2) JSON 조건은 selective할 때만 GIN이 큰 힘을 낸다

JSON 값이 너무 흔하면 GIN이 후보를 많이 뿌려서 체감 이득이 작을 수 있다.

#### 3) 쿼리 형태가 바뀌어도 일반 컬럼 인덱스는 재사용성이 높다

시간 범위와 테넌트는 대개 여러 조회에 공통으로 등장한다.

#### 4) 쓰기 비용을 통제하기 쉽다

JSONB 전체 GIN을 여러 개 두는 것보다, 일반 컬럼 B-tree + 필요한 JSON 인덱스 하나가 더 낫다.

### 실무에서 자주 쓰는 구조

- 최근 데이터 조회가 많다 → `(tenant_id, created_at DESC)`
- 특정 JSON 상태 equality가 많다 → `((payload->>'status'))`
- 드물지만 다양한 ad hoc containment 검색이 있다 → `GIN(payload)`

즉 하나의 쿼리도 사실은 여러 층의 조건으로 나뉜다. 그 층을 분리해서 인덱스 책임도 나누는 편이 더 안정적이다.

---

## 핵심 개념 7: GIN의 진짜 비용은 읽기보다 쓰기에서 체감되는 경우가 많다

JSONB 인덱싱에서 가장 늦게 드러나는 문제는 읽기 성능이 아니라 쓰기 비용이다.

특히 아래 상황에서 그렇다.

- 이벤트 적재량이 많다.
- JSON 문서가 크다.
- key 종류가 다양하다.
- update가 자주 일어난다.
- GIN 인덱스를 여러 개 걸어 둔다.

### 왜 쓰기 비용이 커질까

GIN은 문서 내부의 검색 단서를 많이 인덱싱한다. 즉 row 하나가 들어와도 단일 B-tree key 하나 추가보다 훨씬 많은 작업이 될 수 있다.

특히 큰 payload라면:

- 인덱스 항목 수가 많아질 수 있다.
- pending list가 쌓일 수 있다.
- vacuum/cleanup 부담이 커질 수 있다.
- update 시 기존 문서와 새 문서 차이가 크면 인덱스 churn이 커진다.

### update-heavy JSONB는 특히 위험하다

예를 들어 이런 테이블은 위험 신호다.

```sql
CREATE TABLE jobs (
  id bigserial primary key,
  status text not null,
  updated_at timestamptz not null,
  payload jsonb not null
);
```

그리고 `payload` 안의 아래 필드가 자주 바뀐다고 하자.

- retry_count
- last_error
- worker_id
- progress

이 경우 JSONB 전체 GIN은 조회에는 좋아 보여도, update churn이 심한 시스템에서는 쓰기 비용을 크게 키울 수 있다.

### 여기서 중요한 운영 감각

- JSONB 전체 GIN은 read-heavy, append-heavy 워크로드에 더 잘 맞는다.
- update-heavy 문서에는 더 보수적으로 적용해야 한다.
- 자주 바뀌는 필드는 JSON 밖으로 빼거나, 정말 필요한 expression index만 최소화하는 편이 낫다.

즉 JSONB 인덱싱은 읽기 패턴만으로 결정하면 반쪽짜리다. **문서가 얼마나 자주 바뀌는지**가 거의 같은 비중으로 중요하다.

---

## 핵심 개념 8: HOT, bloat, vacuum까지 같이 봐야 JSONB 인덱싱을 오래 버틸 수 있다

이전 글에서 HOT Update와 index churn 이야기를 다뤘듯이, 인덱스가 많아질수록 update cost는 커지기 쉽다. JSONB는 여기에 더 불리한 면이 있다.

### 1) 큰 row 자체가 page 재사용을 어렵게 만든다

`jsonb` payload가 크면 같은 page 안에서 새 버전을 유지하기 어렵다. 그러면 HOT 기회가 줄고, heap과 index 모두 churn이 커질 수 있다.

### 2) JSON 내부 작은 변경도 문서 전체 변경처럼 다뤄질 수 있다

애플리케이션 입장에서는 `progress` 하나만 바꿨다고 느껴도, 저장 관점에서는 큰 JSON 문서의 새 버전이 생긴다.

### 3) 여러 expression index + GIN이 겹치면 write amplification이 커진다

예를 들어 아래 조합은 읽기엔 좋아 보여도 쓰기에는 비싸다.

- `GIN(payload)`
- `((payload->>'status'))`
- `((payload->>'retry_count')::int)`
- `((payload->>'worker_id'))`

각 update 때 이 인덱스들이 전부 관여할 수 있다.

### 4) vacuum 지연과 인덱스 비대화가 따라온다

테이블이 계속 갱신되는데 vacuum이 따라오지 못하면 dead tuple과 인덱스 비대화가 같이 누적될 수 있다.

### 그래서 실무 기준은 이렇다

- 자주 바뀌는 key는 문서 밖으로 빼는 것이 먼저다.
- JSONB 전체 GIN은 정말 필요한 테이블에만 둔다.
- expression index는 "있으면 좋음"이 아니라, 실제 대표 쿼리 근거가 있을 때만 둔다.
- update-heavy 테이블에서는 인덱스 수 자체를 더 엄격하게 제한한다.

즉 JSONB 인덱싱은 단순 조회 최적화가 아니라 **저장 구조와 갱신 모델까지 포함한 설계**다.

---

## 실무 예시 1: 결제 이벤트 로그에서 실패 코드 검색을 빠르게 만들기

가정은 이렇다.

- `payment_events`는 append-heavy 로그 테이블이다.
- 최근 30일 실패 결제 분석이 잦다.
- payload에는 `status`, `error_code`, `provider`, `card_brand`가 들어 있다.
- 조회는 테넌트 + 최근 기간 + 상태/실패 코드 조합이 많다.

### 나쁜 출발점

```sql
CREATE INDEX idx_payment_events_payload_gin
ON payment_events USING gin (payload);
```

그리고 모든 쿼리를 이런 식으로 해결하려 한다.

```sql
WHERE tenant_id = 42
  AND created_at >= now() - interval '30 days'
  AND payload @> '{"status":"FAILED","error_code":"P05"}'::jsonb
ORDER BY created_at DESC
LIMIT 100;
```

이 방식이 틀린 것은 아니지만, 항상 최선도 아니다.

### 더 현실적인 설계

```sql
CREATE INDEX idx_payment_events_tenant_created_at
ON payment_events (tenant_id, created_at DESC);

CREATE INDEX idx_payment_events_status
ON payment_events ((payload->>'status'));

CREATE INDEX idx_payment_events_error_code
ON payment_events ((payload->>'error_code'));
```

필요하면 ad hoc 분석용으로만 추가:

```sql
CREATE INDEX idx_payment_events_payload_gin_path
ON payment_events USING gin (payload jsonb_path_ops);
```

### 왜 이 구조가 더 현실적인가

- 최근 100건 조회는 `tenant_id, created_at`가 먼저 강하게 줄인다.
- `status`, `error_code`는 equality 비교라 expression index가 직관적이다.
- 드문 복합 containment 분석은 GIN이 받는다.
- 핵심 운영 조회와 탐색성 조회를 분리할 수 있다.

### 여기서 얻는 교훈

결제 실패 코드는 이미 핵심 운영 필드다. JSON 안에 있어도, 인덱싱 관점에서는 사실상 별도 컬럼처럼 다뤄야 한다.

---

## 실무 예시 2: 고객 프로필 custom attributes에서 정말 GIN이 필요한 경우

이번에는 반대로 GIN이 매우 잘 맞는 예시를 보자.

`customer_profiles.attributes`에 아래 같은 자유 속성이 있다고 하자.

```json
{
  "industry": "retail",
  "region": "apac",
  "plan": "enterprise",
  "feature_flags": ["beta_checkout", "smart_coupon"],
  "integrations": {
    "slack": true,
    "salesforce": false
  }
}
```

제품 요구사항:

- 특정 속성이 있는 고객 찾기
- 특정 조합을 포함하는 고객 세그먼트 찾기
- ad hoc 운영 질의가 많음
- 정렬보다 세그먼트 membership 판단이 중요

이 경우 아래 패턴은 GIN과 잘 맞는다.

```sql
WHERE attributes ? 'industry'
```

```sql
WHERE attributes @> '{"plan":"enterprise"}'::jsonb
```

```sql
WHERE attributes @> '{"integrations":{"slack":true}}'::jsonb
```

### 추천 설계

```sql
CREATE INDEX idx_customer_profiles_attributes_gin
ON customer_profiles USING gin (attributes jsonb_ops);
```

여기서 `jsonb_ops`가 더 자연스러운 이유는 존재 여부와 다양한 형태의 검색을 함께 받을 가능성이 크기 때문이다.

### 하지만 이것도 선을 지켜야 한다

만약 `plan`으로 거의 모든 API가 필터링된다면, 그 시점부터는 아래를 같이 고민해야 한다.

```sql
CREATE INDEX idx_customer_profiles_plan
ON customer_profiles ((attributes->>'plan'));
```

혹은 아예 `plan` 컬럼 승격.

즉 GIN이 잘 맞는 테이블이어도, 모든 key가 영원히 JSON 안에만 남아야 한다는 뜻은 아니다.

---

## 실무 예시 3: 작업 큐 메타데이터에서 JSONB를 과하게 인덱싱하면 왜 오히려 느려지는가

이번에는 실패 사례에 가까운 예시다.

`job_queue` 테이블이 있고, payload 안에 아래가 들어 있다고 하자.

- `attempt`
- `last_error`
- `worker`
- `priority`
- `tenant_id`
- `job_type`

처음엔 편해 보여서 payload 전체 GIN과 여러 expression index를 다 건다.

```sql
CREATE INDEX idx_job_queue_payload_gin ON job_queue USING gin (payload);
CREATE INDEX idx_job_queue_attempt ON job_queue (((payload->>'attempt')::int));
CREATE INDEX idx_job_queue_priority ON job_queue (((payload->>'priority')::int));
CREATE INDEX idx_job_queue_worker ON job_queue ((payload->>'worker'));
CREATE INDEX idx_job_queue_job_type ON job_queue ((payload->>'job_type'));
```

문제는 이 테이블이 read-heavy가 아니라 **update-heavy queue**라는 점이다.

- attempt가 계속 증가한다.
- worker가 바뀐다.
- last_error가 갱신된다.
- 상태가 자주 바뀐다.

이런 구조에서는 인덱스가 너무 많아져 쓰기 경로가 먼저 무너질 수 있다.

### 더 좋은 방향

- 핵심 queue 제어용 필드(`status`, `priority`, `available_at`, `tenant_id`)는 일반 컬럼으로 승격
- payload는 작업 입력/결과 보조 메타데이터 중심으로 축소
- JSONB 인덱스는 정말 필요한 탐색 쿼리에만 제한

즉 queue처럼 상태 변경이 잦은 시스템에서는 JSONB 인덱싱보다 **컬럼 모델 재설계**가 더 큰 개선을 줄 때가 많다.

---

## 운영 관측 포인트: JSONB 인덱스가 실제로 도움이 되는지 무엇을 봐야 하는가

JSONB 인덱싱도 결국 관측 없이 믿으면 안 된다. 내가 기본으로 보는 항목은 아래다.

### 1) 대표 쿼리의 실제 plan

- GIN이 정말 사용되는가
- Bitmap Index Scan 후 recheck가 과도한가
- expression index가 기대대로 선택되는가
- 정렬이 병목으로 남는가

### 2) rows 추정 오차

JSONB 조건은 통계가 일반 컬럼만큼 풍부하지 않아 selectivity 오판이 생기기 쉽다. 그래서 `EXPLAIN ANALYZE`에서 estimated rows와 actual rows 차이를 꼭 본다.

### 3) 인덱스 크기 증가 속도

- GIN 인덱스 크기
- expression index 총량
- 테이블 대비 인덱스 비율

JSONB는 문서가 커지고 key 다양성이 높아지면 인덱스도 빠르게 비대해질 수 있다.

### 4) 쓰기 지표

- insert/update latency
- vacuum pressure
- dead tuple 증가
- checkpoint/WAL 증가

JSONB 인덱스 문제는 종종 읽기보다 쓰기에서 먼저 드러난다.

### 5) 쿼리 패턴 drift

처음에는 `@>` 중심이었는데, 시간이 지나 `payload->>'status'`, `payload->>'provider'`, `payload->>'country'` 같은 scalar 비교가 늘어날 수 있다. 이 drift를 방치하면 처음의 GIN 설계가 점점 덜 맞아진다.

즉 인덱스는 한 번 만들고 끝나는 게 아니라, **쿼리 형태가 바뀌는지**를 계속 봐야 한다.

---

## 트레이드오프: JSONB 인덱싱은 유연성과 운영 비용의 교환이다

좋은 점만 보면 JSONB는 거의 만능처럼 보인다.

- 스키마 변경이 빠르다.
- 실험 속도가 높다.
- 외부 payload 보존이 쉽다.
- 일부 검색도 된다.

하지만 대가도 명확하다.

### 트레이드오프 1: 유연성은 통계 품질과 제약 강도를 희생하기 쉽다

일반 컬럼은 타입, nullability, 통계, 인덱스, 제약을 더 정확히 다루기 쉽다. JSONB는 유연하지만 그만큼 planner와 데이터 품질 관리에 불리할 수 있다.

### 트레이드오프 2: GIN은 읽기에 좋을 수 있지만 쓰기에는 비싸다

특히 대형 payload, update-heavy workload, 높은 key 다양성 조합에서 그렇다.

### 트레이드오프 3: 하나의 GIN으로 다 해결하려 하면 정렬과 범위 검색에서 막힌다

JSON 포함 검색과 일반 SQL 정렬은 다른 문제다.

### 트레이드오프 4: expression index를 늘릴수록 컬럼화와 다를 바 없는 운영 비용이 생긴다

이 시점에서는 오히려 진짜 중요한 필드를 컬럼으로 올리는 편이 더 단순할 수 있다.

### 트레이드오프 5: JSONB는 임시 유연성에는 강하지만 핵심 OLTP 모델의 최종 형태로는 한계가 있다

핵심 속성이 많아질수록 JSONB는 저장소보다 부채가 되기 쉽다.

즉 JSONB의 장점은 "무제한 자유"가 아니라 **초기 불확실성을 흡수할 수 있는 완충력**에 있다.

---

## 흔한 실수: PostgreSQL JSONB 인덱싱을 망가뜨리는 패턴들

### 1) `jsonb` 전체 GIN 하나로 모든 쿼리를 해결하려 하기

이건 가장 흔한 오해다. containment에는 좋을 수 있어도, scalar equality/정렬/범위 검색까지 모두 최적은 아니다.

### 2) 자주 조회하는 key를 끝까지 JSON 안에만 두기

운영상 핵심 속성은 결국 승격하는 편이 더 낫다.

### 3) `payload->>'count'`를 문자열 비교로 두기

숫자인데 text comparison으로 남겨 두면 의미와 성능이 둘 다 꼬일 수 있다. 필요한 경우 expression index에 명시적 캐스팅이 들어가야 한다.

### 4) operator class와 실제 쿼리 연산자를 맞추지 않기

`jsonb_path_ops`를 골라 놓고 존재 여부 검색을 광범위하게 기대하면 나중에 어긋난다.

### 5) update-heavy 테이블에 GIN과 expression index를 과도하게 얹기

읽기보다 쓰기에서 먼저 무너질 수 있다.

### 6) JSON key 이름/타입 규칙을 표준화하지 않기

어떤 row는 `retryCount`, 어떤 row는 `retry_count`, 어떤 row는 문자열 `"3"`, 어떤 row는 숫자 `3`이면 인덱스 이전에 데이터 계약부터 무너진다.

### 7) 일반 컬럼 필터와 정렬을 무시하고 JSON 인덱스만 튜닝하기

대부분의 API 병목은 사실 최근 데이터 범위/tenant filter/정렬에서 더 크게 갈린다.

### 8) expression index를 많이 만들면서 실제 사용률을 점검하지 않기

읽히지 않는 JSON expression index는 쓰기 비용만 만든다.

---

## 도입 판단 체크리스트: 이 JSONB 필드는 어떻게 다루는 것이 맞는가?

### GIN이 잘 맞는가

- [ ] key 존재 여부 검색이 자주 있는가
- [ ] `@>` containment 검색이 대표 패턴인가
- [ ] ad hoc 세그먼트/탐색성 질의가 많은가
- [ ] append-heavy라 write 비용을 감당할 수 있는가

### expression index가 더 맞는가

- [ ] `payload->>'field' = ...` 형태가 자주 등장하는가
- [ ] 숫자/날짜/불리언 비교가 필요한가
- [ ] 정렬/범위 검색까지 함께 필요한가
- [ ] 이 값이 API 핵심 필터인가

### 아예 컬럼 승격이 맞는가

- [ ] 거의 모든 조회가 이 값을 참조하는가
- [ ] 타입 안정성이 중요한가
- [ ] 제약, partial index, 집계, 조인에 자주 쓰이는가
- [ ] update 비용보다 모델 명확성이 더 중요한가

### 운영 준비가 되었는가

- [ ] 대표 쿼리 plan을 실제로 확인했는가
- [ ] write latency와 vacuum 영향까지 볼 수 있는가
- [ ] key naming/type 규약이 있는가
- [ ] 어떤 필드를 언제 승격할지 기준이 있는가

이 체크리스트를 통과하지 못하면 JSONB 인덱스는 구조적 해법이 아니라 임시 땜질이 되기 쉽다.

---

## 추천 운영 원칙: 내가 JSONB를 설계할 때 기본으로 두는 기준

### 원칙 1: 먼저 쿼리를 분류하고 그다음 인덱스를 만든다

`?`, `@>`, `->>`, 범위 검색, 정렬을 섞어 쓰면서 인덱스는 하나로 해결하려 하지 않는다.

### 원칙 2: 핵심 비즈니스 속성은 너무 오래 JSON 안에 두지 않는다

유연성은 좋지만, 핵심 계약은 결국 명시 구조가 더 강하다.

### 원칙 3: GIN은 탐색성/containment에, B-tree는 scalar/정렬에 강하다는 기본 구도를 잊지 않는다

이 단순한 구도만 지켜도 많은 시행착오를 줄일 수 있다.

### 원칙 4: update-heavy 테이블에서는 인덱스를 더 인색하게 만든다

읽기 최적화보다 쓰기 안정성이 먼저인 경우가 많다.

### 원칙 5: expression index가 늘어나기 시작하면 "이 필드를 컬럼으로 올릴 시점인가"를 다시 묻는다

JSONB가 편한지, 그냥 구조가 늦게 정리되고 있는지 구분해야 한다.

### 원칙 6: operator class는 성능 옵션이 아니라 쿼리 표준의 일부로 본다

팀이 어떤 연산자를 쓸지 정하지 않으면 인덱스 선택도 흔들린다.

### 원칙 7: JSONB는 저장의 자유를 주지만, 검색의 자유까지 공짜로 주지는 않는다

검색 자유는 결국 인덱스, 계약, 구조화 비용으로 다시 청구된다.

---

## 한 줄 정리

PostgreSQL JSONB 인덱싱의 핵심은 `jsonb` 전체에 GIN 하나를 거는 것이 아니라, **containment는 GIN으로, scalar 비교와 정렬은 expression/B-tree로, 정말 중요한 속성은 일반 컬럼으로 승격해 JSON의 유연성과 운영 가능한 검색 성능 사이에 명확한 경계를 세우는 것**이다.
