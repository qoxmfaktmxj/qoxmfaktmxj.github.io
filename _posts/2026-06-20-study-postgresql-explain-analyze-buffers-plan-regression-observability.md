---
layout: post
title: "PostgreSQL EXPLAIN ANALYZE 실전: BUFFERS, SETTINGS, WAL, Plan Regression으로 느린 쿼리를 증거 기반으로 읽는 법"
date: 2026-06-20 11:50:00 +0900
categories: [sql]
tags: [study, sql, postgresql, explain-analyze, buffers, query-plan, plan-regression, performance, observability, tuning]
permalink: /sql/2026/06/20/study-postgresql-explain-analyze-buffers-plan-regression-observability.html
---

## 배경: 느린 쿼리 튜닝은 "감"보다 "증거 순서"가 먼저다

PostgreSQL 성능 이슈를 보면 같은 패턴이 반복된다.

- API 응답이 느려졌는데 애플리케이션 로그에는 SQL 한 줄만 남아 있다.
- `EXPLAIN`을 봤지만 `Seq Scan`이라는 단어만 보고 인덱스를 추가한다.
- 개발 환경에서는 빠른데 운영에서는 느리다.
- 어제까지 100ms였던 쿼리가 오늘은 5초가 됐다.
- CPU가 문제인지, I/O가 문제인지, 메모리 spill인지, 락 대기인지 구분이 안 된다.
- 쿼리를 조금 바꾸거나 통계를 갱신하니 갑자기 실행 계획이 달라진다.
- 같은 SQL인데 특정 테넌트, 특정 날짜 범위, 특정 파라미터에서만 느리다.

이때 많은 팀은 바로 해결책으로 뛰어간다.

- 인덱스를 하나 더 만든다.
- `work_mem`을 올린다.
- 쿼리를 여러 개로 쪼갠다.
- ORM fetch 옵션을 바꾼다.
- 플래너 설정을 끈다.

물론 이 중 하나가 답일 때도 있다. 하지만 중급 이상 개발자에게 더 중요한 능력은 해결책 목록을 외우는 것이 아니라, **실행 계획에서 어떤 증거를 어떤 순서로 읽어야 하는지 아는 것**이다.

PostgreSQL 튜닝에서 `EXPLAIN ANALYZE`는 단순히 "쿼리가 어떤 인덱스를 탔는지" 보는 도구가 아니다. 운영에서 제대로 쓰려면 최소한 아래를 함께 봐야 한다.

- `ANALYZE`: 실제 실행 시간과 실제 row 수
- `BUFFERS`: shared/local/temp block 접근
- `SETTINGS`: 실행에 영향을 준 세션/플래너 설정
- `WAL`: 쓰기 쿼리에서 WAL 발생량
- `TIMING`: node별 시간 측정
- `SUMMARY`: planning time, execution time
- `FORMAT JSON`: 계획 비교와 자동 분석

그리고 이 숫자들을 단순히 많이 보는 것이 아니라, **느린 원인을 좁히는 순서**로 읽어야 한다.

이번 글은 `EXPLAIN` 입문이 아니다. 이미 `Seq Scan`, `Index Scan`, `Hash Join`, `Nested Loop`, `Sort` 정도는 본 적 있는 개발자를 기준으로 한다. 목표는 운영에서 느린 쿼리를 만났을 때 다음 질문에 답하는 것이다.

1. `EXPLAIN`과 `EXPLAIN ANALYZE`는 언제 각각 써야 하는가?
2. `BUFFERS`의 `hit`, `read`, `dirtied`, `written`, `temp read/write`는 무엇을 의미하는가?
3. 실행 시간이 긴 node와 실제 병목 node는 왜 다를 수 있는가?
4. rows 추정 오차, buffer 접근, temp spill, WAL 증가를 어떤 순서로 봐야 하는가?
5. plan regression은 어떻게 저장하고 비교해야 하는가?
6. 파라미터, prepared statement, generic plan은 왜 운영에서만 느린 쿼리를 만들 수 있는가?
7. 운영에서 안전하게 실행 계획을 수집하려면 어떤 가드레일이 필요한가?

핵심 결론부터 말하면 이렇다.

> **PostgreSQL 실행 계획 분석의 목적은 "나쁜 노드 이름 찾기"가 아니라, row 추정, I/O, 메모리, 설정, 쓰기 비용 중 어느 축에서 현실과 플래너의 가정이 어긋났는지 증거로 분리하는 일이다.**

이 관점이 없으면 `Seq Scan`을 무조건 제거하려 하거나, 반대로 `Index Scan`이 있으니 괜찮다고 착각한다. 실제 운영 문제는 node 이름보다 숫자 사이의 불일치에서 더 자주 드러난다.

---

## 먼저 구분하자: `EXPLAIN`은 예측이고, `EXPLAIN ANALYZE`는 실행이다

가장 기본이지만 실무에서 가장 자주 흐려지는 구분이다.

```sql
EXPLAIN
SELECT *
FROM orders
WHERE tenant_id = 42
  AND status = 'PAID';
```

이 명령은 쿼리를 실제로 실행하지 않는다. PostgreSQL 플래너가 현재 통계와 설정을 바탕으로 "이렇게 실행할 것 같다"고 보여준다.

반면 아래는 실제로 실행한다.

```sql
EXPLAIN (ANALYZE)
SELECT *
FROM orders
WHERE tenant_id = 42
  AND status = 'PAID';
```

`ANALYZE`가 붙으면 PostgreSQL은 쿼리를 실제로 수행하고, 각 실행 노드의 실제 시간과 실제 row 수를 붙여서 보여준다.

이 차이는 단순한 문법 차이가 아니다. 운영에서 안전성과 직결된다.

### SELECT는 실행되고 결과만 버려진다

`EXPLAIN ANALYZE SELECT ...`는 SELECT를 실제 실행한다. 결과 row를 클라이언트로 보내지는 않지만, 내부적으로 읽기 작업은 수행된다.

즉 아래 비용은 실제로 발생할 수 있다.

- CPU 사용
- shared buffer 접근
- 디스크 read
- temp file 생성
- 락 대기
- 함수 실행
- parallel worker 사용

운영에서 무거운 조회 쿼리에 `EXPLAIN ANALYZE`를 붙이면 분석 자체가 부하가 될 수 있다.

### UPDATE, DELETE, INSERT도 실제로 실행된다

더 위험한 것은 쓰기 쿼리다.

```sql
EXPLAIN (ANALYZE)
UPDATE orders
SET status = 'EXPIRED'
WHERE expires_at < now()
  AND status = 'PENDING';
```

이 쿼리는 실제로 데이터를 바꾼다. 실행 계획만 보고 싶은 의도였더라도 `ANALYZE`가 붙으면 update가 수행된다.

운영에서 쓰기 쿼리의 실제 계획을 확인해야 한다면 보통 트랜잭션으로 감싼다.

```sql
BEGIN;

EXPLAIN (ANALYZE, BUFFERS, WAL)
UPDATE orders
SET status = 'EXPIRED'
WHERE expires_at < now()
  AND status = 'PENDING';

ROLLBACK;
```

이렇게 하면 논리적 변경은 롤백된다. 하지만 주의할 점이 있다.

- row lock은 실행 중 실제로 잡힌다.
- 트리거와 함수가 실행될 수 있다.
- 시퀀스 증가는 롤백되지 않을 수 있다.
- WAL은 일부 발생할 수 있다.
- 외부 시스템을 호출하는 함수가 있으면 부작용이 남을 수 있다.

따라서 쓰기 쿼리 분석은 가능하면 운영 복제본, 스테이징 데이터, 샘플 범위, 짧은 timeout을 함께 써야 한다.

### `EXPLAIN`만으로 충분한 경우

`EXPLAIN`은 실제 실행을 하지 않으므로 다음 상황에 유용하다.

- 쓰기 쿼리의 대략적인 접근 경로를 먼저 확인할 때
- 신규 인덱스가 선택될 가능성을 빠르게 볼 때
- 운영에서 무거운 쿼리를 실제 실행하기 부담스러울 때
- 쿼리 구조 변경 전후의 예상 계획을 비교할 때
- `enable_*` 설정이나 `work_mem` 변화가 플래너 선택에 주는 영향을 볼 때

하지만 `EXPLAIN`만으로는 아래를 알 수 없다.

- 실제 row 수
- 실제 실행 시간
- 실제 buffer read/hit
- 실제 temp file 사용량
- 실제 WAL 발생량
- 실제 loops 반복 횟수에서 누적되는 비용

즉 `EXPLAIN`은 가설을 세우는 도구이고, `EXPLAIN ANALYZE`는 가설을 검증하는 도구다.

---

## 실무 기본 옵션: 처음부터 이 조합으로 본다

운영 쿼리 분석에서 기본으로 추천하는 형태는 아래다.

```sql
EXPLAIN (
  ANALYZE,
  BUFFERS,
  SETTINGS,
  WAL,
  VERBOSE,
  SUMMARY,
  FORMAT TEXT
)
SELECT ...
```

항상 모든 옵션이 필요한 것은 아니지만, 중급 이상 분석에서는 `ANALYZE`와 `BUFFERS`만으로는 아쉬운 경우가 많다.

### `ANALYZE`

실제 실행한다. `actual time`, `actual rows`, `loops`가 나온다.

가장 중요한 질문은 이것이다.

> estimated rows와 actual rows가 어디서 처음 크게 벌어지는가?

실행 시간이 긴 node만 보면 늦다. row 추정이 앞단에서 틀리면 뒤쪽 join, sort, hash, aggregate가 연쇄적으로 나빠진다.

### `BUFFERS`

shared/local/temp block 접근을 보여준다.

예를 들어 이런 식이다.

```text
Buffers: shared hit=12034 read=842 dirtied=15 written=3
```

`BUFFERS`가 없으면 느린 쿼리가 CPU 중심인지, 캐시 hit 중심인지, 실제 디스크 read 중심인지, temp 파일 중심인지 판단하기 어렵다.

### `SETTINGS`

기본값이 아닌 planner 관련 설정을 보여준다.

이 옵션은 장애 분석에서 생각보다 중요하다. 같은 SQL이라도 아래 설정이 다르면 계획이 달라질 수 있다.

- `work_mem`
- `effective_cache_size`
- `random_page_cost`
- `enable_nestloop`
- `enable_hashjoin`
- `max_parallel_workers_per_gather`
- `jit`
- `plan_cache_mode`

"내 로컬에서는 다른 계획인데요"라는 대화가 나오면 `SETTINGS`가 증거가 된다.

### `WAL`

쓰기 쿼리에서 WAL record, full page image, byte 수를 보여준다.

대량 update나 delete 튜닝에서는 읽기 비용만 보면 부족하다. 실제 병목이 WAL 생성, checkpoint 압력, replication lag일 수 있다.

```sql
EXPLAIN (ANALYZE, BUFFERS, WAL)
UPDATE user_events
SET archived = true
WHERE created_at < now() - interval '180 days'
  AND archived = false;
```

이때 `WAL: records=..., fpi=..., bytes=...`가 크면 단순 실행 시간 외에 복제 지연과 스토리지 쓰기 비용까지 봐야 한다.

### `VERBOSE`

출력 컬럼, 스키마, 내부 표현을 더 자세히 보여준다.

복잡한 view, CTE, partition, expression index, generated column, 함수 호출이 섞인 쿼리에서는 `VERBOSE`가 실제로 어떤 expression이 계획에 들어갔는지 확인하는 데 도움이 된다.

### `SUMMARY`

planning time과 execution time 요약을 보여준다.

일반적인 OLTP에서는 execution time이 문제인 경우가 많지만, 동적 SQL이 복잡하거나 파티션이 많거나 join 후보가 폭발하는 쿼리에서는 planning time도 병목이 될 수 있다.

### `FORMAT JSON`

사람이 읽을 때는 `TEXT`가 편하다. 하지만 plan regression을 저장하고 비교하려면 `JSON`이 좋다.

```sql
EXPLAIN (ANALYZE, BUFFERS, SETTINGS, FORMAT JSON)
SELECT ...
```

JSON이면 CI나 사내 도구에서 다음 값을 추출하기 쉽다.

- node type 변화
- total cost 변화
- actual total time 변화
- shared read block 증가
- temp written block 증가
- join algorithm 변화
- plan rows와 actual rows 비율

실무에서는 사람이 보는 `TEXT`와 저장/비교용 `JSON`을 함께 쓰는 편이 가장 좋다.

---

## 실행 계획을 읽는 순서: 느린 node부터 보지 말고 "오차가 시작된 곳"부터 본다

아래 같은 쿼리가 있다고 하자.

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT
  o.id,
  o.created_at,
  o.total_amount,
  u.email,
  p.name AS plan_name
FROM orders o
JOIN users u ON u.id = o.user_id
JOIN subscriptions s ON s.user_id = u.id
JOIN plans p ON p.id = s.plan_id
WHERE o.tenant_id = 42
  AND o.status = 'PAID'
  AND o.created_at >= now() - interval '30 days'
  AND s.status = 'ACTIVE'
ORDER BY o.created_at DESC
LIMIT 100;
```

실행 계획에서 마지막 `Sort`나 `Nested Loop`가 오래 걸린다고 해서 그 노드가 근본 원인이라고 단정하면 안 된다. 실제 원인은 앞쪽 필터에서 row estimate가 틀어졌기 때문일 수 있다.

추천하는 읽기 순서는 이렇다.

1. 전체 실행 시간과 planning time을 확인한다.
2. 가장 큰 실제 시간 구간을 찾되, 바로 결론 내리지 않는다.
3. leaf node부터 `rows`와 `actual rows`의 비율을 본다.
4. 오차가 처음 크게 벌어지는 node를 찾는다.
5. 그 node의 조건, 통계, 파라미터, 인덱스, 데이터 분포를 확인한다.
6. 상위 node에서 buffer read, temp read/write, loops 누적이 어떻게 증폭되는지 본다.
7. 해결책을 인덱스, 통계, 쿼리 구조, 메모리, 파라미터, 운영 설정 중 어디에 둘지 나눈다.

이 순서가 중요한 이유는 단순하다. 실행 계획은 트리 구조이고, 앞단의 오판은 뒤에서 비용으로 증폭된다.

### 예시: 느린 건 Sort인데 원인은 필터 추정 오차

다음 출력 일부를 보자.

```text
Sort  (cost=8800.00..8803.00 rows=1200 width=96)
      (actual time=2200.330..2235.110 rows=180420 loops=1)
  Sort Key: o.created_at DESC
  Sort Method: external merge  Disk: 48240kB
  Buffers: shared hit=23120 read=9104, temp read=6020 written=6088
  ->  Hash Join  (cost=2100.00..8720.00 rows=1200 width=96)
                 (actual time=120.440..1850.880 rows=180420 loops=1)
        ->  Bitmap Heap Scan on orders o
            (cost=900.00..6100.00 rows=1300 width=48)
            (actual time=30.120..980.550 rows=184900 loops=1)
            Recheck Cond: (tenant_id = 42)
            Filter: ((status = 'PAID') AND (created_at >= (now() - '30 days'::interval)))
            Rows Removed by Filter: 920000
            Buffers: shared hit=17000 read=8000
```

겉으로 보면 `Sort`가 오래 걸리고 temp file도 쓴다. 그래서 `work_mem`을 올리고 싶어진다.

하지만 더 앞을 보면 핵심은 `orders` 필터다.

- 예상 row: 1,300
- 실제 row: 184,900
- 오차: 약 142배
- 필터로 제거한 row: 920,000
- shared read: 8,000 blocks

여기서 `Sort`는 결과일 가능성이 크다. 플래너는 1,300건 정렬이라고 생각했지만 실제로는 18만 건 정렬이었다. 그러니 temp file로 밀려난다.

이 경우 해결 후보는 단순히 `work_mem` 상향이 아니다.

- `tenant_id, status, created_at` 복합 인덱스가 필요한가?
- partial index로 `status = 'PAID'` 또는 활성 데이터만 좁힐 수 있는가?
- `tenant_id`별 데이터 편차 때문에 extended statistics가 필요한가?
- 최근 30일 조건이 테넌트별로 심하게 치우쳐 있는가?
- 오래된 데이터 파티션 pruning이 가능한가?
- 목록 API라면 keyset pagination으로 정렬 대상 자체를 줄일 수 있는가?

즉 `Sort`가 보인다고 정렬만 튜닝하면 원인을 놓칠 수 있다.

---

## `BUFFERS` 읽기: hit, read, dirtied, written을 구분해야 한다

`BUFFERS`는 PostgreSQL 실행 계획 분석에서 가장 실무적인 옵션이다. 그런데 출력 단어가 짧아서 오해도 많다.

대표 출력은 이런 형태다.

```text
Buffers: shared hit=5120 read=840 dirtied=12 written=4
```

이 숫자를 읽으려면 먼저 block 단위를 알아야 한다. PostgreSQL 기본 block size는 보통 8KB다. 즉 `read=840`이면 대략 6.5MB 정도를 shared buffer로 읽어온 것이다.

정확한 환산은 설치 옵션에 따라 다를 수 있지만, 대부분 운영에서는 8KB로 보면 된다.

### `shared hit`

shared buffer에 이미 있던 block을 읽었다는 뜻이다.

`hit`가 높다고 무조건 나쁜 것은 아니다. 캐시에 있는 데이터를 많이 읽은 것이다. 하지만 OLTP 단건 API에서 `shared hit=500000` 같은 숫자가 나오면, 디스크 I/O가 없어도 CPU와 메모리 대역폭을 많이 쓰고 있을 수 있다.

즉 `hit`는 "공짜"가 아니다. 디스크보다 싸지만 여전히 읽고 비교하고 필터링하는 비용이 있다.

### `shared read`

shared buffer에 없어서 OS/file system에서 읽어온 block이다.

`read`가 크면 실제 I/O가 개입했을 가능성이 높다. 다만 OS page cache에서 온 것인지 물리 디스크에서 온 것인지는 PostgreSQL 출력만으로 완전히 구분하기 어렵다.

그래도 쿼리 계획 비교에서는 매우 유용하다.

- 변경 전: `shared read=120000`
- 변경 후: `shared read=500`

이 정도 차이면 쿼리가 훨씬 적은 page를 건드리게 된 것이다.

### `shared dirtied`

쿼리가 shared buffer 안의 page를 dirty 상태로 만들었다는 뜻이다. 주로 쓰기 쿼리에서 나타난다.

`UPDATE`, `DELETE`, `INSERT`, `CREATE INDEX`, `VACUUM` 등이 관련된다.

읽기 쿼리에서도 hint bit 설정 등으로 일부 dirty가 생길 수 있지만, 대량으로 보이면 쓰기 비용을 의심해야 한다.

### `shared written`

쿼리 실행 중 dirty page가 실제로 쓰였다는 뜻이다.

이 숫자가 크면 해당 쿼리가 checkpoint, background writer, buffer pressure와 엮여 있을 수 있다. 단순 SQL 시간뿐 아니라 DB 전체 write pressure 관점에서 봐야 한다.

### `temp read` / `temp written`

정렬, hash join, hash aggregate, materialize 등이 메모리 안에서 끝나지 못하고 temp file을 사용했다는 신호다.

예시는 아래와 같다.

```text
Buffers: shared hit=9000 read=1200, temp read=3840 written=3910
Sort Method: external merge  Disk: 31280kB
```

이때는 다음 질문으로 넘어가야 한다.

- 어떤 node가 temp를 썼는가?
- Sort인가, Hash Join인가, HashAggregate인가?
- 입력 row 수가 예상보다 많았는가?
- `work_mem`이 너무 낮은가?
- 동시 실행을 고려하면 `work_mem`을 올릴 여지가 있는가?
- 정렬을 인덱스로 피할 수 있는가?
- group cardinality를 줄일 수 있는가?

중요한 점은 temp file이 보인다고 항상 `work_mem`만 올리는 것이 답은 아니라는 것이다. 정렬 대상 자체가 불필요하게 커진 경우에는 인덱스, 필터, pagination, 집계 순서가 더 좋은 답일 수 있다.

---

## `loops`가 만드는 착시: 작아 보이는 node도 반복되면 비싸다

실행 계획에서 자주 놓치는 숫자가 `loops`다.

아래 예시를 보자.

```text
Index Scan using idx_order_items_order_id on order_items i
  (cost=0.43..8.45 rows=3 width=40)
  (actual time=0.025..0.080 rows=4 loops=50000)
  Index Cond: (order_id = o.id)
  Buffers: shared hit=210000 read=1500
```

node 한 번만 보면 빠르다.

- actual time: 0.025..0.080ms
- rows: 4

하지만 `loops=50000`이다. Nested Loop의 inner side로 5만 번 실행된 것이다.

이 경우 실제 비용은 아래처럼 봐야 한다.

- 한 번당 작다.
- 하지만 5만 번 반복된다.
- buffer hit가 21만 block이다.
- read도 1,500 block 발생했다.

이런 계획은 "인덱스를 탔으니 괜찮다"가 아니다. 작은 인덱스 조회가 대량 반복되며 비용을 만든다.

### Nested Loop가 나쁜 것이 아니라, 반복 횟수와 inner 비용이 문제다

Nested Loop 자체는 매우 좋은 계획일 수 있다.

- outer row가 작다.
- inner lookup이 유니크 인덱스다.
- LIMIT로 빠르게 멈춘다.
- 캐시 적중률이 높다.

하지만 outer row가 예상보다 커지면 이야기가 달라진다.

```text
Nested Loop  (cost=0.86..1200.00 rows=100 width=80)
             (actual time=1.000..4200.000 rows=50000 loops=1)
```

플래너는 100번 정도 inner lookup을 예상했는데 실제로는 5만 번이면, Nested Loop 선택 자체가 오판이었을 수 있다.

해결 후보는 다양하다.

- outer row 수를 줄이는 복합 인덱스
- 통계 갱신 또는 extended statistics
- hash join이 가능하도록 쿼리 구조 변경
- `IN` 목록 또는 임시 테이블을 통한 배치 lookup
- 필요 컬럼만 먼저 제한한 뒤 상세 join
- N+1 형태 ORM 쿼리 제거

`loops`는 "작은 비용이 몇 번 반복됐는가"를 보여주는 숫자다. 운영에서 이걸 놓치면 느린 쿼리의 절반을 놓친다.

---

## Plan Regression: 어제 빠르던 쿼리가 오늘 느려지는 이유

쿼리 튜닝은 한 번 고치고 끝나는 작업이 아니다. 운영 데이터는 계속 변하고, PostgreSQL도 계속 다른 결정을 한다.

plan regression은 같은 SQL 또는 같은 논리 쿼리가 어느 시점부터 더 나쁜 실행 계획을 선택하는 현상이다.

대표 원인은 아래와 같다.

- 테이블 row 수 증가
- 특정 테넌트 데이터 쏠림
- 날짜 범위 변화
- 통계 stale
- autovacuum/analyze 지연
- 신규 인덱스 추가로 플래너 후보 변화
- 파티션 증가로 planning overhead 증가
- `work_mem`, `random_page_cost`, parallel 설정 변경
- prepared statement의 generic plan 선택
- PostgreSQL 버전 업그레이드
- ORM이 생성하는 SQL shape 변경

plan regression을 다루려면 실행 계획을 "그때그때 눈으로 본 결과"가 아니라, 비교 가능한 산출물로 남겨야 한다.

### 저장해야 할 최소 정보

느린 쿼리 하나를 분석할 때 최소한 아래를 같이 저장한다.

- SQL 텍스트 또는 normalized query
- 바인딩 파라미터 예시
- 실행 시각
- PostgreSQL 버전
- 주요 세션 설정
- `EXPLAIN (ANALYZE, BUFFERS, SETTINGS, FORMAT JSON)` 결과
- 대상 테이블 row count
- 주요 인덱스 목록
- `pg_stat_statements`의 평균/최대 실행 시간
- 실행 당시 `work_mem`, `jit`, parallel 관련 설정

이렇게 남겨야 나중에 "느려졌다"가 감상이 아니라 비교가 된다.

### `FORMAT JSON`으로 비교할 때 볼 값

JSON plan 비교에서 너무 많은 필드를 다 비교하면 노이즈가 많다. 처음에는 아래 정도만 봐도 충분하다.

- root `Node Type`
- join node의 `Node Type`
- scan node의 `Relation Name`, `Index Name`
- `Plan Rows`
- `Actual Rows`
- `Actual Loops`
- `Shared Hit Blocks`
- `Shared Read Blocks`
- `Temp Read Blocks`
- `Temp Written Blocks`
- `Sort Method`
- `Sort Space Used`
- `Hash Batches`
- `Peak Memory Usage`

예를 들어 변경 전후가 아래처럼 바뀌었다고 하자.

- 변경 전: `Index Scan` + `Nested Loop`, shared hit 20,000
- 변경 후: `Seq Scan` + `Hash Join`, shared read 180,000, temp written 12,000

이건 단순히 "계획이 달라졌다"가 아니라 I/O와 temp 사용이 함께 악화된 것이다.

반대로 node 이름만 보면 나빠 보이지만 실제로는 좋아진 경우도 있다.

- 변경 전: `Index Scan`, actual time 5,000ms, shared hit 600,000
- 변경 후: `Seq Scan`, actual time 800ms, shared hit 80,000

이 경우 `Seq Scan`이라는 이름에 놀라면 안 된다. PostgreSQL이 넓은 범위를 순차적으로 읽는 것이 더 싸다고 판단했고, 실제로도 더 빨랐다면 좋은 계획일 수 있다.

### CI에서 plan을 고정하면 안 되는 이유

가끔 "중요 쿼리의 실행 계획이 바뀌면 CI에서 실패시키자"는 아이디어가 나온다. 방향은 좋지만, 실행 계획을 문자 그대로 고정하는 것은 위험하다.

실행 계획은 다음에 따라 자연스럽게 바뀐다.

- PostgreSQL minor/major version
- 통계 샘플
- row count
- 설정
- 테스트 데이터 분포

따라서 CI에서는 "계획 문자열 완전 일치"보다 다음 종류의 가드레일이 현실적이다.

- full scan 금지 대상 테이블에서 `Seq Scan` 발생 여부
- temp block이 특정 임계치 이상 증가했는지
- estimated rows와 actual rows 비율이 특정 배수 이상인지
- 특정 쿼리의 p95 실행 시간이 기준을 넘는지
- 핵심 인덱스가 전혀 사용되지 않는지
- join 순서 변경으로 읽은 block 수가 크게 늘었는지

즉 계획을 얼려두는 것이 아니라, **성능 위험 신호를 지표화**하는 편이 낫다.

---

## 파라미터와 Prepared Statement: 특정 값에서만 느린 쿼리의 함정

운영에서 까다로운 문제 중 하나가 "같은 SQL인데 어떤 사용자에게만 느리다"이다.

예를 들어 아래 쿼리를 보자.

```sql
SELECT id, created_at, total_amount
FROM orders
WHERE tenant_id = $1
  AND status = $2
ORDER BY created_at DESC
LIMIT 50;
```

대부분 테넌트는 주문이 적다. 하지만 `tenant_id = 42`는 전체 주문의 40%를 가진 대형 테넌트라고 하자.

이때 좋은 계획은 파라미터에 따라 달라질 수 있다.

- 작은 테넌트: 인덱스로 빠르게 찾기
- 큰 테넌트: 더 넓은 scan 후 정렬 또는 다른 복합 인덱스 필요

PostgreSQL은 prepared statement에서 custom plan과 generic plan 사이를 선택할 수 있다. 초기에는 파라미터 값을 보고 custom plan을 만들다가, 반복 실행 비용을 고려해 generic plan을 쓰는 경우가 있다.

generic plan은 특정 파라미터 값을 깊게 반영하지 않는 범용 계획이다. 데이터 분포가 균일하면 괜찮지만, 테넌트별 편차가 큰 SaaS에서는 문제가 될 수 있다.

### 의심 신호

다음 상황이면 prepared statement와 generic plan을 의심해볼 만하다.

- p50은 빠른데 p99만 심하게 느리다.
- 특정 테넌트나 특정 상태값에서만 느리다.
- 애플리케이션에서는 느린데 psql에서 literal SQL로 실행하면 빠르다.
- `EXPLAIN`에 literal 값을 넣으면 다른 계획이 나온다.
- 배포 후 DB 드라이버 설정 변경과 함께 느려졌다.

### 확인 방법

테스트 환경에서 다음을 비교한다.

```sql
SET plan_cache_mode = force_custom_plan;
EXPLAIN (ANALYZE, BUFFERS, SETTINGS)
EXECUTE prepared_query(42, 'PAID');
```

```sql
SET plan_cache_mode = force_generic_plan;
EXPLAIN (ANALYZE, BUFFERS, SETTINGS)
EXECUTE prepared_query(42, 'PAID');
```

두 계획의 차이가 크다면, 문제는 인덱스 하나로 끝나지 않을 수 있다.

해결 후보는 아래처럼 나뉜다.

- 데이터 편차가 큰 조건을 위한 partial index
- 대형 테넌트 전용 쿼리 경로 분리
- 날짜 범위나 상태 조건을 더 명확히 제한
- extended statistics로 상관관계 보강
- generic plan이 불리한 경로에서는 prepared statement 사용 방식 조정
- 테넌트별 파티셔닝 또는 물리 모델 재검토

핵심은 "같은 SQL"이라는 말에 속지 않는 것이다. 운영 쿼리는 SQL 텍스트와 파라미터 분포가 함께 성능을 만든다.

---

## 실무 예시 1: 목록 API가 느릴 때

가장 흔한 사례부터 보자.

```sql
SELECT
  id,
  customer_id,
  status,
  total_amount,
  created_at
FROM orders
WHERE tenant_id = 42
  AND status IN ('PAID', 'SHIPPED')
ORDER BY created_at DESC
LIMIT 50 OFFSET 5000;
```

증상은 이렇다.

- 첫 페이지는 빠르다.
- 뒤 페이지로 갈수록 느려진다.
- `ORDER BY created_at DESC`가 있다.
- `OFFSET`이 커질수록 buffer 접근이 증가한다.

실행 계획에서 볼 포인트는 아래다.

```text
Limit
  ->  Index Scan using idx_orders_tenant_status_created_at on orders
        Index Cond: (tenant_id = 42)
        Filter: (status = ANY ('{PAID,SHIPPED}'::text[]))
        Rows Removed by Filter: 68000
        Buffers: shared hit=72000 read=1200
```

인덱스를 탔지만 느리다. 이유는 `OFFSET 5000`까지 앞 row를 지나가야 하기 때문이다. 게다가 status 조건이 index cond가 아니라 filter로 밀리면 더 많은 row를 읽고 버린다.

해결 접근은 순서대로 본다.

### 1) 복합 인덱스가 조건과 정렬을 같이 지원하는가

```sql
CREATE INDEX idx_orders_tenant_status_created_id
ON orders (tenant_id, status, created_at DESC, id DESC);
```

이 인덱스는 tenant와 status로 범위를 좁히고, created_at 정렬을 돕는다. 같은 created_at에 대한 tie-breaker로 id를 둔다.

### 2) OFFSET pagination을 keyset pagination으로 바꿀 수 있는가

```sql
SELECT
  id,
  customer_id,
  status,
  total_amount,
  created_at
FROM orders
WHERE tenant_id = 42
  AND status IN ('PAID', 'SHIPPED')
  AND (created_at, id) < ($last_created_at, $last_id)
ORDER BY created_at DESC, id DESC
LIMIT 50;
```

keyset pagination은 깊은 페이지에서 특히 강하다. 앞의 5,000건을 버리는 대신 마지막 cursor 이후만 읽는다.

### 3) INCLUDE로 heap fetch를 줄일 가치가 있는가

목록 API가 매우 뜨겁고 반환 컬럼이 제한적이라면 covering index를 검토한다.

```sql
CREATE INDEX idx_orders_list_cover
ON orders (tenant_id, status, created_at DESC, id DESC)
INCLUDE (customer_id, total_amount);
```

하지만 이 인덱스는 쓰기 비용과 저장 공간을 늘린다. 주문 테이블에 update가 많다면 visibility map이 자주 깨져 index only scan 효과가 제한될 수 있다.

체크할 증거는 `Heap Fetches`, `BUFFERS`, update 빈도, 인덱스 크기다.

---

## 실무 예시 2: 리포트 쿼리가 temp file을 만들 때

월별 매출 리포트를 보자.

```sql
SELECT
  date_trunc('day', paid_at) AS day,
  payment_method,
  count(*) AS order_count,
  sum(total_amount) AS revenue
FROM orders
WHERE tenant_id = 42
  AND paid_at >= '2026-05-01'
  AND paid_at < '2026-06-01'
  AND status = 'PAID'
GROUP BY 1, 2
ORDER BY 1, 2;
```

실행 계획 일부가 이렇다.

```text
HashAggregate
  (actual time=4200.100..4550.220 rows=124 loops=1)
  Group Key: date_trunc('day'::text, paid_at), payment_method
  Batches: 8  Memory Usage: 8193kB  Disk Usage: 62400kB
  Buffers: shared hit=20000 read=18000, temp read=7600 written=8200
  ->  Seq Scan on orders
        (actual time=20.000..3100.000 rows=4200000 loops=1)
        Filter: ...
```

여기서 temp file이 보인다. 하지만 바로 `work_mem`을 올리기 전에 질문을 나눈다.

### 입력 row가 너무 많은가

4,200,000 rows가 aggregate로 들어간다. 이게 업무적으로 필요한가? 월별 리포트라면 원천 주문 row를 매번 모두 읽는 구조가 맞는지 먼저 봐야 한다.

대안은 다음이다.

- 일별 summary table
- materialized view
- incremental aggregation
- 파티션 pruning
- tenant/date 복합 인덱스

### group cardinality가 큰가

결과 rows는 124건뿐이다. group cardinality는 낮다. 그런데 temp가 크다면 aggregate 전 입력 scan과 hash 작업의 메모리/배치 구조를 봐야 한다.

### 정렬과 집계를 분리할 수 있는가

`GROUP BY` 후 결과 124건 정렬은 작다. 진짜 비용은 scan과 aggregate다. `ORDER BY`를 탓하면 빗나간다.

### 세션 단위 `work_mem`이 도움이 되는가

리포트 배치처럼 동시성이 낮고 무거운 쿼리라면 세션 또는 트랜잭션 단위로 `work_mem`을 높일 수 있다.

```sql
BEGIN;
SET LOCAL work_mem = '256MB';

SELECT ...

COMMIT;
```

하지만 API 요청 경로에서 글로벌 `work_mem`을 올리는 것은 위험하다. 동시에 여러 사용자가 무거운 정렬/해시 쿼리를 실행하면 메모리 사용량이 폭발한다.

---

## 실무 예시 3: UPDATE가 느릴 때는 WAL과 index churn을 같이 본다

쓰기 쿼리는 읽기 쿼리와 다르게 봐야 한다.

```sql
EXPLAIN (ANALYZE, BUFFERS, WAL)
UPDATE sessions
SET expired = true,
    updated_at = now()
WHERE expires_at < now()
  AND expired = false;
```

실행 계획에서 이런 출력이 나올 수 있다.

```text
Update on sessions
  (actual time=0.500..8900.000 rows=0 loops=1)
  Buffers: shared hit=90000 read=15000 dirtied=38000 written=4200
  WAL: records=520000 fpi=2400 bytes=182000000
  ->  Bitmap Heap Scan on sessions
        (actual time=120.000..2100.000 rows=260000 loops=1)
        Recheck Cond: (expires_at < now())
        Filter: (NOT expired)
```

읽기 부분은 2.1초인데 전체 update는 8.9초다. 그러면 병목은 단순 scan이 아닐 수 있다.

봐야 할 것은 아래다.

- 갱신 row 수
- dirty block 수
- WAL bytes
- 갱신되는 컬럼이 인덱스에 포함되는지
- HOT update가 가능한지
- trigger 또는 foreign key cascade가 있는지
- replication lag가 증가하는지
- batch 크기가 너무 큰지

### 대량 UPDATE는 청크 처리로 운영 반경을 줄인다

한 번에 26만 건을 update하면 락, WAL, checkpoint, replication에 부담이 크다. 보통은 청크로 나눈다.

```sql
WITH target AS (
  SELECT id
  FROM sessions
  WHERE expires_at < now()
    AND expired = false
  ORDER BY expires_at
  LIMIT 5000
)
UPDATE sessions s
SET expired = true,
    updated_at = now()
FROM target t
WHERE s.id = t.id;
```

이 방식의 장점은 명확하다.

- 트랜잭션 시간이 짧아진다.
- row lock 지속 시간이 줄어든다.
- WAL 발생이 작은 덩어리로 나뉜다.
- 실패 시 재시도 범위가 작다.
- replication lag를 관찰하면서 속도를 조절할 수 있다.

단점도 있다.

- 전체 완료까지 더 오래 걸릴 수 있다.
- 배치 orchestration이 필요하다.
- idempotency와 재시작 기준을 설계해야 한다.
- `ORDER BY`와 index가 맞지 않으면 매 청크마다 비싼 scan이 반복될 수 있다.

쓰기 쿼리에서는 "한 번에 빠르게 끝내기"보다 "운영 시스템이 감당 가능한 속도로 끝내기"가 더 좋은 목표일 때가 많다.

---

## 흔한 실수 1: `Seq Scan`을 무조건 악으로 본다

`Seq Scan`은 많은 개발자가 싫어하는 단어다. 하지만 PostgreSQL에서 sequential scan은 정상적인 선택이다.

다음 상황에서는 seq scan이 더 나을 수 있다.

- 테이블 대부분을 읽어야 한다.
- 조건 선택도가 낮다.
- 인덱스 random access가 더 비싸다.
- 작은 테이블이다.
- 병렬 seq scan이 효율적이다.
- 통계상 인덱스가 도움이 안 된다.

예를 들어 전체 row의 70%를 읽어야 하는 쿼리에 인덱스를 강제로 태우면 오히려 더 느릴 수 있다. 인덱스에서 TID를 찾고 heap을 랜덤하게 방문하는 비용이 순차적으로 읽는 비용보다 클 수 있기 때문이다.

따라서 질문은 "왜 seq scan이 나왔지?"가 아니라 아래여야 한다.

- 실제로 읽어야 하는 비율이 높은가?
- 조건 선택도가 낮은가?
- 통계가 현실을 잘 반영하는가?
- 필요한 데이터가 테이블 전체에 퍼져 있는가?
- 파티션 pruning이나 partial index로 읽을 범위를 줄일 수 있는가?
- API 요구사항상 정말 그 많은 row가 필요한가?

`Seq Scan`이라는 이름만으로 인덱스를 추가하면 쓰기 비용만 늘리고 문제는 그대로일 수 있다.

---

## 흔한 실수 2: `actual time`만 보고 node 비용을 판단한다

`actual time=0.100..1000.000` 같은 숫자를 보면 해당 node가 1초 걸렸다고 생각하기 쉽다. 하지만 node 시간은 트리 실행 방식, loops, 하위 node 포함 여부를 고려해야 한다.

특히 상위 node의 시간은 하위 node 소비를 포함해서 보이는 경우가 많다. 그래서 가장 위 node가 오래 걸린다고 root node가 원인인 것은 아니다.

분석할 때는 다음을 함께 본다.

- 해당 node 자체의 작업은 무엇인가?
- child node에서 이미 시간이 소비됐는가?
- `loops`가 몇 번인가?
- rows가 얼마나 흘러 올라왔는가?
- buffers가 어느 node에서 증가했는가?
- temp file은 어느 node에서 발생했는가?

실행 계획 분석은 call stack 분석과 비슷하다. 가장 위에 보이는 시간이 항상 범인은 아니다.

---

## 흔한 실수 3: 개발 DB에서 빠른 계획을 운영에도 적용된다고 믿는다

개발 DB와 운영 DB는 보통 완전히 다른 세계다.

- row 수가 다르다.
- 데이터 분포가 다르다.
- 테넌트 편차가 다르다.
- 캐시 상태가 다르다.
- autovacuum 상태가 다르다.
- 통계 샘플이 다르다.
- 설정이 다르다.
- 하드웨어와 스토리지가 다르다.

개발 DB에서 `EXPLAIN ANALYZE`가 5ms라고 운영에서도 5ms가 아니다. 특히 성능 문제는 데이터 분포가 만든다.

운영 유사 환경을 만들 때는 단순 row count보다 아래가 더 중요하다.

- 상위 테넌트 데이터 쏠림
- status 값 분포
- 날짜별 skew
- 삭제/업데이트 비율
- NULL 비율
- hot partition과 cold partition
- 인덱스 bloat
- visibility map 상태

성능 테스트 데이터가 균일 랜덤이면 실제 운영의 가장 어려운 문제를 재현하지 못한다.

---

## 흔한 실수 4: 실행 계획 하나만 보고 인덱스를 만든다

느린 쿼리 하나를 보고 인덱스를 만들면 그 쿼리는 빨라질 수 있다. 하지만 운영 DB 전체로 보면 부작용이 생긴다.

인덱스는 읽기 최적화 도구이면서 동시에 쓰기 비용이다.

새 인덱스는 아래 비용을 만든다.

- INSERT 비용 증가
- UPDATE 비용 증가
- DELETE 비용 증가
- VACUUM 부담 증가
- 디스크 사용량 증가
- WAL 증가
- cache pressure 증가
- planner 후보 증가

그래서 인덱스 추가 전에는 최소한 다음을 확인한다.

- 같은 인덱스 prefix를 가진 기존 인덱스가 있는가?
- 새 인덱스가 다른 쿼리에도 재사용되는가?
- partial index로 더 작게 만들 수 있는가?
- INCLUDE 컬럼이 정말 필요한가?
- 쓰기 빈도가 높은 테이블인가?
- 운영에서 `CREATE INDEX CONCURRENTLY`가 필요한가?
- 실패 시 cleanup 계획이 있는가?
- 기존 인덱스 제거 후보가 생기는가?

특히 PostgreSQL에서는 유사한 복합 인덱스가 쌓이기 쉽다.

```text
(tenant_id, status)
(tenant_id, status, created_at)
(tenant_id, status, created_at, id)
(tenant_id, status, created_at DESC, id DESC) INCLUDE (total_amount)
```

이런 상태가 되면 읽기 튜닝이 아니라 인덱스 부채가 된다. 실행 계획 분석은 새 인덱스를 만드는 일이 아니라, 전체 접근 패턴을 정리하는 일이다.

---

## 운영에서 안전하게 실행 계획을 수집하는 기준

운영에서 성능 문제를 보려면 운영 데이터를 봐야 한다. 하지만 운영에서 무거운 분석을 함부로 하면 장애를 키운다.

실무 기준은 아래처럼 잡는 것이 좋다.

### 1) 먼저 `pg_stat_statements`로 후보를 좁힌다

개별 감상보다 누적 통계가 먼저다.

```sql
SELECT
  queryid,
  calls,
  total_exec_time,
  mean_exec_time,
  max_exec_time,
  rows,
  shared_blks_hit,
  shared_blks_read,
  temp_blks_read,
  temp_blks_written,
  query
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 20;
```

여기서 봐야 할 축은 여러 개다.

- 총 시간을 많이 쓰는 쿼리
- 평균이 높은 쿼리
- max가 튀는 쿼리
- temp block이 많은 쿼리
- shared read가 많은 쿼리
- calls가 너무 많은 쿼리

총 시간이 큰 쿼리와 한 번 실행이 매우 느린 쿼리는 대응 방식이 다르다.

### 2) timeout을 걸고 분석한다

운영에서 `EXPLAIN ANALYZE`를 실행해야 한다면 timeout을 둔다.

```sql
BEGIN;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '1s';

EXPLAIN (ANALYZE, BUFFERS, SETTINGS, FORMAT JSON)
SELECT ...

ROLLBACK;
```

`statement_timeout`은 분석 쿼리가 너무 오래 돌지 않게 한다. `lock_timeout`은 락 대기에 오래 묶이지 않게 한다.

### 3) 쓰기 쿼리는 가능한 복제본 또는 제한 범위에서 본다

복제본에서는 쓰기 쿼리를 실행할 수 없거나 의미가 달라질 수 있다. 그래도 읽기 부분의 접근 경로를 보거나 SELECT로 target row를 확인하는 데는 도움이 된다.

쓰기 쿼리의 실제 비용을 봐야 한다면 범위를 제한한다.

```sql
WITH target AS (
  SELECT id
  FROM sessions
  WHERE expires_at < now()
    AND expired = false
  ORDER BY expires_at
  LIMIT 1000
)
SELECT count(*)
FROM target;
```

먼저 target 선정 쿼리의 계획을 본 뒤, update는 작은 청크로 검증한다.

### 4) 민감한 literal과 개인정보는 저장하지 않는다

실행 계획 저장소를 만들 때 SQL literal에 개인정보가 섞일 수 있다.

- 이메일
- 전화번호
- 토큰
- 검색어
- 주소
- 사용자 입력 원문

plan regression 저장 시스템에서는 normalized query, masked parameter, synthetic sample을 쓰는 편이 안전하다.

---

## 체크리스트: 느린 PostgreSQL 쿼리를 볼 때 순서대로 확인할 것

아래 순서대로 보면 헛다리를 줄일 수 있다.

### 기본 정보

- 이 쿼리는 SELECT인가, 쓰기 쿼리인가?
- 단발성 리포트인가, 자주 호출되는 API인가?
- p50 문제인가, p95/p99 문제인가?
- 특정 파라미터에서만 느린가?
- 최근 배포, 인덱스 변경, 통계 변경, 데이터 증가가 있었는가?

### 실행 계획 수집

- `EXPLAIN`만 본 것인가, `EXPLAIN ANALYZE`까지 본 것인가?
- `BUFFERS`를 켰는가?
- `SETTINGS`를 켰는가?
- 쓰기 쿼리라면 `WAL`을 봤는가?
- JSON plan을 저장했는가?
- 실행 당시 바인딩 파라미터를 기록했는가?

### row 추정

- estimated rows와 actual rows가 크게 다른 node는 어디인가?
- 오차가 처음 시작되는 node는 어디인가?
- 통계가 오래됐는가?
- 컬럼 간 상관관계가 큰가?
- 특정 테넌트나 특정 상태값 skew가 있는가?

### I/O와 메모리

- `shared read`가 큰가?
- `shared hit`가 과도하게 큰가?
- temp read/write가 발생했는가?
- 어떤 node에서 spill이 발생했는가?
- `work_mem` 조정이 안전한가, 아니면 입력 row를 줄여야 하는가?

### join과 loops

- Nested Loop inner side가 과도하게 반복되는가?
- Hash Join build side가 예상보다 커졌는가?
- Join order가 데이터 크기와 맞는가?
- inner lookup 인덱스가 유니크하거나 충분히 선택적인가?

### 인덱스

- 조건, 정렬, join에 맞는 복합 인덱스가 있는가?
- 기존 인덱스 prefix로 대체 가능한가?
- partial index가 더 나은가?
- INCLUDE가 필요한가?
- 새 인덱스의 쓰기 비용은 감당 가능한가?
- `CREATE INDEX CONCURRENTLY`가 필요한가?

### 운영 가드레일

- 분석 쿼리에 timeout을 걸었는가?
- 쓰기 쿼리는 트랜잭션과 rollback으로 보호했는가?
- lock 대기 가능성을 봤는가?
- replication lag와 WAL 증가를 봤는가?
- plan regression 비교 자료를 남겼는가?

---

## 트레이드오프: 더 빠른 쿼리와 더 단순한 운영은 항상 같지 않다

성능 튜닝은 숫자를 낮추는 일처럼 보이지만, 실제로는 운영 트레이드오프를 선택하는 일이다.

### 인덱스를 추가할 것인가, 쿼리를 바꿀 것인가

인덱스는 애플리케이션 코드를 적게 바꾸고 효과를 볼 수 있다. 하지만 쓰기 비용과 저장 공간을 늘린다.

쿼리 구조 변경은 근본 해결일 수 있다. 하지만 코드 변경, 테스트, API 계약 변경이 필요하다.

목록 API의 깊은 pagination 문제라면 인덱스보다 keyset pagination이 더 근본적일 수 있다. 반대로 작은 조건 누락으로 full scan이 나는 문제라면 복합 인덱스가 명확한 답일 수 있다.

### `work_mem`을 올릴 것인가, 입력 row를 줄일 것인가

`work_mem` 상향은 빠른 완화책이다. 하지만 동시성이 붙으면 메모리 위험이 커진다.

입력 row를 줄이는 설계는 더 안전하다. 하지만 인덱스, summary table, partition, query rewrite가 필요할 수 있다.

리포트 배치처럼 통제된 경로에서는 `SET LOCAL work_mem`이 좋은 선택일 수 있다. 사용자 API 경로에서는 구조 개선이 더 낫다.

### plan stability를 원할 것인가, adaptive plan 선택을 허용할 것인가

힌트나 설정으로 특정 계획을 강제하면 당장 안정될 수 있다. 하지만 데이터가 바뀌었을 때 더 나쁜 고정 계획이 될 수 있다.

PostgreSQL 기본 철학은 힌트보다 통계와 비용 모델을 통해 좋은 계획을 고르게 하는 쪽에 가깝다. 그래서 우선순위는 보통 다음이다.

1. 통계 최신화
2. extended statistics
3. 적절한 인덱스
4. 쿼리 구조 개선
5. 설정 조정
6. 최후의 수단으로 강제성 있는 우회

---

## 한 줄 정리

`EXPLAIN ANALYZE`는 느린 쿼리의 범인을 찍어주는 버튼이 아니라, **플래너의 예상과 운영의 실제가 어디서 갈라졌는지 rows, buffers, temp, WAL, settings 증거로 추적하는 관측 도구**다.

