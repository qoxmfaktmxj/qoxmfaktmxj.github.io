---
layout: post
title: "PostgreSQL work_mem 실전: Sort Spill, Hash Join, HashAggregate, Temp File로 메모리 병목을 읽는 법"
date: 2026-05-22 11:40:00 +0900
categories: [sql]
tags: [study, sql, postgresql, work-mem, sort-spill, hash-join, hashaggregate, temp-file, performance, operations]
permalink: /sql/2026/05/22/study-postgresql-work-mem-sort-spill-hash-join-hashaggregate-temp-file.html
---

## 배경: CPU도 낮고 인덱스도 있는데 왜 PostgreSQL 쿼리는 갑자기 몇 배씩 느려질까

운영 중인 PostgreSQL을 보다 보면 꽤 자주 이상한 장면을 만난다.

- 평소 300ms 안쪽이던 리포트 쿼리가 어느 날 8초를 넘긴다.
- 실행 계획은 크게 바뀐 것 같지 않은데 응답 시간이 요동친다.
- CPU가 100%도 아니고 I/O도 평소와 비슷해 보이는데 temp 파일만 급증한다.
- `ORDER BY` 하나 추가했을 뿐인데 디스크 사용량과 지연 시간이 동시에 튄다.
- `GROUP BY` 집계가 갑자기 느려지며 `HashAggregate`가 여러 batch로 쪼개진다.
- 조인 순서가 약간 바뀌었을 뿐인데 `Hash Join`이 spill 나면서 디스크를 긁기 시작한다.
- 개발 환경에서는 멀쩡한데 운영처럼 동시성이 붙는 순간 OOM 직전까지 간다.

이때 많은 팀이 가장 먼저 하는 대응은 보통 둘 중 하나다.

- `work_mem`을 크게 올린다.
- 인덱스를 하나 더 만든다.

문제는 둘 다 자주 맞지만, 둘 다 자주 틀리다는 점이다.

PostgreSQL 성능 이슈에서 메모리 병목은 단순히 “메모리가 부족하다”는 한 줄로 설명되지 않는다.

실무에서 더 정확한 질문은 이렇다.

> **어떤 실행 노드가, 어떤 이유로, 어느 시점에, 메모리 안에서 끝나지 못하고 temp 파일로 밀려났는가?**

이 질문으로 바꾸는 순간 대응도 달라진다.

- 정렬이 문제인지 해시가 문제인지 구분하게 된다.
- `work_mem`을 글로벌로 올릴지, 세션 단위로만 조정할지 판단하게 된다.
- 인덱스 추가가 답인지, 통계 갱신이 답인지, 쿼리 재구성이 답인지 분리하게 된다.
- OOM을 감수하면서 메모리를 올릴지, spill을 허용하면서 느림을 받아들일지 트레이드오프가 선명해진다.

오늘 글은 PostgreSQL 메모리 튜닝을 “`work_mem` 좀 올려보자” 수준에서 끝내지 않고, **Sort, Hash Join, HashAggregate, Temp File, 동시성, 관측성, 운영 가드레일**을 한 번에 연결해서 정리한다.

중급 이상 개발자가 실제 운영에서 아래 질문에 답할 수 있도록 구성했다.

1. `work_mem`은 정확히 어떤 실행 노드에 어떻게 적용되는가
2. 왜 같은 `work_mem` 값인데 어떤 쿼리는 빠르고 어떤 쿼리는 여전히 spill 나는가
3. Sort 계열 문제와 Hash 계열 문제는 왜 접근 방식이 달라야 하는가
4. `hash_mem_multiplier`는 언제 유용하고, 언제 오히려 숨은 위험이 되는가
5. temp 파일 급증을 어떤 지표와 로그로 추적해야 하는가
6. `work_mem` 글로벌 상향, 세션별 상향, 쿼리 구조 변경 중 무엇을 먼저 선택해야 하는가
7. 실무에서 가장 자주 하는 메모리 튜닝 실수는 무엇인가

결론부터 먼저 말하면 이렇다.

> **PostgreSQL 메모리 튜닝의 핵심은 `work_mem` 숫자 하나를 키우는 일이 아니라, 메모리 집약적 실행 노드 수와 동시성을 예측 가능한 범위 안에 두는 일이다.**

이 관점이 없으면 아주 쉽게 두 가지 극단으로 간다.

- spill을 없애겠다며 `work_mem`을 크게 올렸다가 동시 요청 때 OOM을 맞는다.
- OOM이 무서워 너무 낮게 잡았다가 중요한 리포트와 집계가 계속 temp 파일로 떨어진다.

둘 다 운영 품질을 갉아먹는다.

---

## 먼저 큰 그림: PostgreSQL의 메모리는 “쿼리당 한 번”이 아니라 “실행 노드별로 여러 번” 쓰인다

많은 사람이 `work_mem`을 처음 배울 때 이렇게 오해한다.

- 쿼리 하나가 최대 `work_mem`만 쓴다.
- 세션 하나가 최대 `work_mem`만 쓴다.
- `work_mem=64MB`면 백엔드 하나가 64MB 정도만 더 먹는다.

실제 운영에서는 거의 항상 틀린 가정이다.

PostgreSQL 공식 문서가 강조하는 핵심도 여기에 있다.

- `work_mem`은 **정렬이나 해시 테이블 같은 query operation 하나당** 기준값이다.
- 복잡한 쿼리는 **여러 sort와 hash operation을 동시에** 가질 수 있다.
- 여러 세션이 동시에 실행되면 총 메모리 사용량은 `work_mem`의 몇 배가 아니라 **수십 배, 수백 배**가 될 수 있다.
- hash 계열 연산은 `hash_mem_multiplier` 때문에 기본 `work_mem`보다 더 많이 쓸 수 있다.

즉 `work_mem=64MB`라는 숫자는 “DB 전체가 64MB 더 쓴다”는 뜻이 아니다.

더 현실적인 그림은 이렇다.

- 쿼리 A에 `Sort` 2개
- `Hash Join` 1개
- `HashAggregate` 1개
- 병렬 워커 3개
- 같은 시간에 비슷한 쿼리 10개

이 조건이면 메모리 사용량은 매우 빠르게 불어난다.

단순화해서 보면,

- sort node 하나당 대략 `work_mem`
- hash node 하나당 대략 `work_mem × hash_mem_multiplier`
- parallel worker마다 비슷한 구조가 반복될 수 있음
- 여러 세션이 동시에 돌면 같은 패턴이 중첩됨

그래서 실무에서 중요한 것은 “현재 값이 작나 크나”가 아니라 다음 네 가지다.

1. **어떤 노드가 메모리를 먹는가**
2. **한 쿼리에 그런 노드가 몇 개 있는가**
3. **병렬 워커와 동시 실행 세션이 몇 개인가**
4. **spill을 없앨 가치가 있는 쿼리인지, 그냥 허용해도 되는 쿼리인지**

이 네 가지를 빼고 `work_mem`만 건드리면 조정이 아니라 도박에 가깝다.

---

## PostgreSQL 메모리 관련 설정을 먼저 구분하자: `shared_buffers`, `work_mem`, `maintenance_work_mem`, `temp_buffers`는 역할이 다르다

메모리 이슈가 생기면 종종 서로 다른 설정이 한데 섞여 논의된다.

하지만 실무 판단을 위해서는 역할 분리가 먼저다.

### `shared_buffers`

- 테이블과 인덱스 페이지를 캐시하는 shared memory 영역
- 서버 전체가 공유한다.
- 주로 읽기 캐시와 쓰기 버퍼링 성격이다.
- 정렬 spill이나 hash spill을 직접 해결하는 설정은 아니다.

### `work_mem`

- 정렬, 해시 테이블, 일부 temp working set이 디스크로 밀리기 전까지 사용할 수 있는 **operation 단위 메모리 기준값**
- 세션별, 트랜잭션별, role별로 조정 가능하다.
- 쿼리 메모리 병목에서 가장 직접적으로 다루는 값이다.

### `hash_mem_multiplier`

- hash join, hash aggregate 같은 hash 기반 연산이 사용할 수 있는 상한을 `work_mem`보다 더 크게 잡는 multiplier
- 공식 문서 기준으로 hash 계열은 sort 계열보다 메모리 민감도가 더 크기 때문에 별도 multiplier가 있다.
- `work_mem`을 무작정 올리지 않고도 hash spill 빈도를 줄일 여지가 있다.
- 하지만 이것도 결국 동시성 환경에서는 총 메모리 소비를 키운다.

### `maintenance_work_mem`

- `VACUUM`, `CREATE INDEX`, `ALTER TABLE ADD FOREIGN KEY` 같은 maintenance 작업용
- 일반 SELECT 쿼리의 sort spill을 해결하지 않는다.
- 운영에서 자주 나오는 실수는 일반 쿼리가 느린데 `maintenance_work_mem`만 올리는 것이다.

### `temp_buffers`

- 임시 테이블용 세션 로컬 버퍼
- 일반적인 `ORDER BY` spill이나 `HashAggregate` spill의 주인공은 아니다.
- temp table-heavy 워크로드에서나 중요하다.

정리하면,

- 일반 조회/집계 쿼리의 메모리 병목 → 보통 `work_mem`, `hash_mem_multiplier`, 쿼리 구조, 통계, 인덱스
- 유지보수 작업 속도 → `maintenance_work_mem`
- 캐시 효율 → `shared_buffers`
- temp table 사용 패턴 → `temp_buffers`

이 구분이 먼저 잡혀야 대화가 정확해진다.

---

## 어떤 실행 노드가 `work_mem`을 실제로 쓰는가

실무에서는 “정렬 쿼리가 느리다” 정도로 말하지만, 실제 실행 노드는 더 다양하다.

대표적으로 아래 노드들을 기억해두면 좋다.

### 1) Sort

- `ORDER BY`
- `DISTINCT`
- `UNION` 정렬 정규화 경로 일부
- merge join 준비 정렬
- window 함수 전처리 정렬

정렬은 메모리에 다 올라가면 빠르게 끝나지만, 넘치면 external merge로 디스크 temp 파일을 사용하기 시작한다.

### 2) Hash Join

- 한쪽 입력을 build side로 메모리에 올려 hash table 생성
- 다른 쪽 입력이 probe side
- build side가 예상보다 커지거나 카디널리티 오판이 크면 batch가 늘고 spill이 발생할 수 있다.

### 3) HashAggregate

- `GROUP BY`, `COUNT(DISTINCT ...)` 주변 경로 일부
- group cardinality가 높으면 hash table이 커진다.
- 메모리에 다 못 올라가면 batch 분할, temp 사용, 속도 저하가 발생한다.

### 4) Memoize / hash-based IN subquery processing

- 최신 PostgreSQL 실행 계획에서 해시 기반 보조 구조가 붙을 수 있다.
- 규모가 크면 메모리 사용량 계산에서 무시하면 안 된다.

### 5) Materialize / tuplesort / tuplestore 계열 임시 저장

- 명칭은 다르지만 결과를 잠시 들고 있다가 재사용하는 노드들이 temp 블록을 사용할 수 있다.
- 단순히 `Sort`나 `Hash`만 보는 습관은 그래서 위험하다.

즉 temp 파일이 발생했다고 해서 무조건 `ORDER BY`가 원인인 것은 아니다.

반대로 `ORDER BY`가 있다고 해서 항상 정렬 spill이 문제인 것도 아니다.

실제 병목은 항상 **실행 계획 노드 단위**로 봐야 한다.

---

## 핵심 개념 1: Sort 계열 병목은 “정렬해야 하는 데이터 양”과 “정렬을 피할 수 있는가”가 본질이다

정렬 문제를 메모리 문제로만 보면 절반만 본 것이다.

실무에서 Sort 병목은 보통 아래 세 층으로 나눠서 봐야 한다.

1. 정렬을 **애초에 피할 수 있는가**
2. 정렬이 필요하다면 **입력 row 수를 줄일 수 있는가**
3. 그래도 정렬이 필요하다면 **메모리 안에서 끝낼 수 있는가**

많은 팀이 3번만 본다.

그래서 `work_mem`부터 올린다.

하지만 운영에서 제일 싼 해법은 대개 1번이나 2번이다.

### Sort가 메모리에 들어가면 무슨 일이 일어나는가

메모리 안에서 끝나는 정렬은 보통 디스크 spill보다 훨씬 싸다.

- temp file 생성이 없다.
- 추가 I/O가 적다.
- merge pass가 없다.
- 응답 시간의 변동성도 줄어든다.

반대로 정렬이 spill 나면 다음 현상이 생긴다.

- temp 파일 생성
- temp read/write 증가
- external merge 단계 발생
- 동시 쿼리와 temp 디스크 경합
- p95, p99 지연 증가
- 디스크 여유 공간 압박

특히 운영에서 무서운 건 평균 속도보다 tail latency다.

정렬 spill은 “조금 느려짐”으로 끝나지 않고,

- 리포트 시간대마다 튄다
- 배치와 겹칠 때만 터진다
- 특정 테넌트 데이터량에서만 재현된다
- temp 디스크 압박으로 다른 쿼리까지 흔든다

같은 식으로 나타나기 쉽다.

### Sort는 세 가지 질문으로 빠르게 판단할 수 있다

#### 질문 1) 정렬 순서를 인덱스로 대체할 수 있는가

예를 들어 아래 쿼리를 보자.

```sql
SELECT id, created_at, amount
FROM payments
WHERE tenant_id = 42
  AND status = 'DONE'
ORDER BY created_at DESC
LIMIT 50;
```

이 쿼리가 자주 호출된다면, 좋은 답은 `work_mem` 상향이 아닐 수 있다.

오히려 아래 같은 인덱스가 더 싸다.

```sql
CREATE INDEX idx_payments_tenant_status_created_desc
ON payments (tenant_id, status, created_at DESC)
INCLUDE (id, amount);
```

이렇게 되면,

- 필터링
- 정렬 순서 충족
- 일부 경우 index only scan 가능

이 동시에 풀릴 수 있다.

즉 정렬 문제를 메모리로 밀어붙이지 않고 **읽기 경로 설계**로 해결하는 것이다.

#### 질문 2) 전체를 정렬할 필요가 있는가

많은 쿼리가 실제로 필요한 것은 “전체 정렬 결과”가 아니라 “상위 N개”다.

- 최근 20건
- 매출 상위 100개 상품
- 최신 에러 50건

이때도 정렬 입력이 너무 크면 spill이 날 수 있다.

하지만 아래를 같이 보면 해결책이 바뀐다.

- `WHERE` 필터가 충분히 선택적인가
- 먼저 줄일 수 있는 집합을 줄였는가
- keyset pagination으로 바꿀 수 있는가
- 미리 집계된 요약 테이블로 우회할 수 있는가

#### 질문 3) 정렬은 한 번인가, 여러 번인가

실행 계획을 보면 놀랄 만큼 자주 sort가 여러 번 나온다.

- subquery 정렬
- DISTINCT 정렬
- merge join 준비 정렬
- window 함수용 정렬
- 최종 `ORDER BY`

이 경우 `work_mem`을 하나 올리면 sort 하나만 빨라지는 것이 아니라, **각 sort 노드가 각각 그만큼 메모리를 쓸 수 있게 된다.**

그래서 쿼리당 메모리 증폭이 생각보다 훨씬 빠르다.

### `EXPLAIN ANALYZE`에서 Sort 병목을 읽는 포인트

정렬 노드에서는 보통 아래 단서가 중요하다.

- `Sort Method: quicksort` → 메모리 내 정렬 가능성이 큼
- `Sort Method: top-N heapsort` → LIMIT 최적화 경로
- `Sort Method: external merge` → spill 발생
- `Disk:` → spill된 디스크 사용량
- `temp read` / `temp written` → 실제 temp 블록 사용

최신 PostgreSQL에서는 `EXPLAIN`에 `MEMORY` 옵션도 있지만, 운영 현실에서는 버전 차이가 있으니 최소한 아래 조합을 기본 습관으로 두는 편이 좋다.

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT ...;
```

`BUFFERS`를 같이 보면 temp blocks read/written까지 확인할 수 있다.

이게 중요한 이유는,

- 느린 원인이 shared buffer miss인지
- temp spill인지
- 단순 row 수 증가인지

를 구분할 수 있기 때문이다.

### Sort 병목에서 `work_mem` 상향이 진짜로 맞는 경우

다음 조건이 같이 맞을 때는 `work_mem` 조정이 꽤 정직하게 먹힌다.

- 정렬은 피할 수 없다.
- 입력 row 수를 크게 줄이기 어렵다.
- 쿼리 빈도는 낮고 중요도는 높다.
- 동시 실행 수가 제한적이다.
- spill 규모가 `work_mem`을 약간만 올려도 메모리 안으로 들어올 정도다.

예를 들어,

- 하루 몇 번 도는 리포트
- 운영자 전용 분석 쿼리
- 야간 배치 중 일부 집계

같은 경우다.

이런 쿼리에 세션 단위로 `work_mem`을 올리는 것은 합리적이다.

### Sort 병목에서 `work_mem` 상향이 틀린 경우

다음 경우는 메모리 상향보다 구조 변경이 먼저다.

- 정렬 대상 row 수 자체가 과도하다.
- 인덱스로 순서를 충족할 수 있다.
- LIMIT 페이지네이션을 keyset pagination으로 바꿀 수 있다.
- 같은 쿼리가 매우 자주, 동시에 많이 실행된다.
- spill 양이 너무 커서 조금 올린다고 해결되지 않는다.

예를 들어 20GB 정렬을 64MB에서 256MB로 올리는 것은 대개 본질 해결이 아니다.

느린 쿼리를 조금 덜 느리게 할 수는 있어도,

- 여전히 spill 나고
- 동시성 리스크만 키우고
- 다른 쿼리까지 압박할 수 있다.

이럴 때는 정렬을 “잘하는 법”보다 “덜 정렬하는 법”을 먼저 고민해야 한다.

---

## 실무 예시 1: 주문 목록 API의 `ORDER BY` spill을 메모리보다 읽기 경로로 먼저 해결하는 법

예시를 하나 보자.

```sql
SELECT id, order_no, created_at, total_amount
FROM orders
WHERE tenant_id = 3001
  AND status IN ('PAID', 'SHIPPED')
  AND created_at >= now() - interval '90 days'
ORDER BY created_at DESC
LIMIT 100;
```

운영에서 자주 보는 안 좋은 패턴은 이렇다.

- `tenant_id`만 인덱스가 있다.
- 최근 90일 데이터가 꽤 많다.
- 결과는 100건만 필요하지만 입력 후보는 수십만 건이다.
- 최종적으로 sort가 큰 집합 위에서 수행된다.

이때 실행 계획 일부가 아래처럼 나올 수 있다.

```text
Sort  (actual time=1480.122..1481.004 rows=100 loops=1)
  Sort Key: created_at DESC
  Sort Method: external merge  Disk: 18432kB
  Buffers: shared hit=..., temp read=2304 written=2311
```

여기서 초보 대응은 보통 `work_mem` 상향이다.

하지만 먼저 봐야 할 것은 다음이다.

1. `tenant_id`, `status`, `created_at DESC` 순서 인덱스를 만들 수 있는가
2. 반환 컬럼을 `INCLUDE`로 덮을 수 있는가
3. 최근 90일 필터가 너무 넓다면 비즈니스적으로 더 줄일 수 있는가
4. offset pagination이면 keyset으로 바꿀 수 있는가

가능한 개선안은 대개 아래 방향이다.

```sql
CREATE INDEX idx_orders_tenant_status_created_desc_cover
ON orders (tenant_id, status, created_at DESC)
INCLUDE (id, order_no, total_amount);
```

혹은 상태값 선택도가 낮아 실제로는 인덱스가 비효율적이라면,

- 상태를 별도 partial index로 분리하거나
- hot path 전용 조회 테이블을 두거나
- 최근 데이터만 다루는 파티션 전략을 고려할 수 있다.

즉 이 사례의 핵심은 “정렬이 느리다”가 아니라,

> **정렬해야 할 후보 row를 구조적으로 줄이지 못한 상태에서 메모리로 버티고 있다**

는 것이다.

이 차이를 잡아내면 튜닝 비용이 크게 줄어든다.

---

## 핵심 개념 2: Hash 계열 병목은 Sort보다 더 위험하다

정렬 spill은 느리지만 대체로 직관적이다.

반면 hash 계열 병목은 더 교묘하다.

왜냐하면 hash join과 hash aggregate는 다음 요소가 한꺼번에 얽히기 때문이다.

- build side 크기
- group cardinality
- row width
- 플래너 추정 정확도
- batch 분할
- skew
- `hash_mem_multiplier`
- 동시성

즉 “메모리가 좀 부족하다”가 아니라,

- 어떤 입력을 hash table로 잡았는지
- 그 추정이 맞았는지
- 실제 데이터 폭과 그룹 수가 어떤지
- spill이 단순 일회성인지 구조적 패턴인지

를 같이 봐야 한다.

### Hash Join의 본질: 작은 쪽을 메모리에 올려 큰 쪽이 찌르는 구조

Hash Join은 보통 이렇게 이해하면 된다.

1. build side를 읽어 hash table 생성
2. probe side를 읽으며 매칭 확인

이 구조는 build side가 충분히 작을 때 아주 효율적이다.

문제는 build side가 예상보다 커질 때다.

- 카디널리티 추정이 빗나간다.
- 필터가 생각만큼 선택적이지 않다.
- projection이 커서 row width가 불필요하게 넓다.
- 조인 순서가 비효율적이다.
- 통계가 오래돼 플래너가 작은 쪽을 잘못 고른다.

이 순간 hash table이 메모리에 못 들어가면서 batch가 늘고 temp I/O가 생긴다.

Hash Join이 느릴 때 많은 팀이 “조인이 느리다”고 말한다.

하지만 더 정확한 표현은 이렇다.

> **build side를 메모리 안에 유지하지 못하면서 조인이 디스크 분할 처리로 떨어졌다.**

이 표현이 맞아야 해결책도 맞는다.

### HashAggregate의 본질: group 수와 row width가 메모리를 결정한다

`GROUP BY`도 마찬가지다.

예를 들어 아래 집계를 보자.

```sql
SELECT tenant_id, user_id, event_type, count(*)
FROM audit_events
WHERE created_at >= now() - interval '30 days'
GROUP BY tenant_id, user_id, event_type;
```

이 쿼리가 느릴 때 단순히 “행 수가 많아서”라고만 보면 부족하다.

실제 메모리를 결정하는 것은 다음이 더 크다.

- group key cardinality
- 해시 테이블에 들고 있어야 할 상태 크기
- row width
- 중간 aggregate state 크기

즉 1천만 row라도 group 수가 작으면 꽤 버틸 수 있고,

반대로 100만 row여도 group 수가 매우 많으면 spill이 날 수 있다.

### `hash_mem_multiplier`를 이해해야 하는 이유

PostgreSQL 공식 문서는 hash 기반 operation이 sort보다 메모리 민감하다고 설명한다.

그래서 hash 계열은 `work_mem × hash_mem_multiplier`까지 메모리를 사용할 수 있다.

이 설정이 유용한 이유는 분명하다.

- sort를 위해 `work_mem` 전체를 크게 올리지 않아도 된다.
- hash join / hash aggregate만 조금 더 숨통을 틔워줄 수 있다.
- mixed workload에서 sort는 보수적으로, hash는 조금 더 공격적으로 가져가는 선택이 가능하다.

하지만 이것도 공짜가 아니다.

다음 상황을 생각해 보자.

- `work_mem = 64MB`
- `hash_mem_multiplier = 4.0`
- 병렬 워커 포함 hash node 다수
- 동시에 비슷한 분석 쿼리 여러 개 실행

이 경우 hash node 하나가 이론상 256MB 가까이 사용할 여지가 생긴다.

즉 spill은 줄어들 수 있지만,

- 메모리 총량 리스크는 커지고
- OOM 가능성도 같이 올라간다.

그래서 `hash_mem_multiplier`는 “좋은 숨은 튜닝값”이면서도,

동시성 모델 없이 올리면 사고 포인트가 된다.

### Hash 계열에서 `work_mem` 상향이 맞는 경우

아래 조건이 맞을 때는 꽤 효과적일 수 있다.

- build side 또는 group state가 메모리 경계 바로 바깥에 있다.
- 쿼리 수가 제한적이다.
- 운영상 중요한 배치나 리포트다.
- spill이 반복되며 temp I/O가 주 병목이다.
- 통계와 조인 순서는 이미 reasonable하다.

### Hash 계열에서 `work_mem` 상향이 틀린 경우

아래는 구조를 먼저 봐야 한다.

- build side가 애초에 너무 크다.
- 잘못된 조인 순서 때문에 큰 쪽을 hash table로 만들고 있다.
- `SELECT *`로 row width를 불필요하게 키우고 있다.
- `GROUP BY` key가 과도하게 넓다.
- `COUNT(DISTINCT ...)` 같은 집계를 그대로 큰 범위에 때리고 있다.
- 통계 부정확으로 row estimate가 크게 빗나간다.

이런 경우 메모리를 더 줘도 효과가 제한적이다.

심하면 spill 빈도는 줄어들지 않고 메모리 위험만 커진다.

---

## 실무 예시 2: `HashAggregate` spill은 종종 메모리보다 group cardinality 설계 문제다

예를 들어 운영 대시보드용 쿼리가 있다고 하자.

```sql
SELECT date_trunc('hour', created_at) AS bucket,
       tenant_id,
       user_id,
       event_type,
       count(*) AS cnt,
       sum(duration_ms) AS total_duration
FROM api_call_logs
WHERE created_at >= now() - interval '14 days'
GROUP BY 1, 2, 3, 4;
```

겉보기에는 흔한 집계다.

하지만 아래 요소가 겹치면 `HashAggregate`가 바로 무거워진다.

- 14일 범위가 넓다.
- `tenant_id`, `user_id`, `event_type`, 시간 버킷까지 합쳐 group 수가 매우 많다.
- row 수보다 group 수가 문제다.
- 운영자가 기대하는 것은 사실 상위 요약 몇 개뿐인데 raw log를 직접 집계한다.

이때 계획 일부가 아래처럼 나올 수 있다.

```text
HashAggregate
  Group Key: date_trunc('hour'::text, created_at), tenant_id, user_id, event_type
  Batches: 16
  Memory Usage: 65536kB
  Disk Usage: 512MB
```

이 상황에서 `work_mem`만 올리는 것은 종종 임시 처치다.

먼저 볼 질문은 아래다.

1. 정말 user_id 수준까지 실시간 집계가 필요한가
2. 시간 버킷을 hour 대신 day로 줄일 수 있는가
3. 원본 로그 대신 사전 집계 테이블을 둘 수 있는가
4. 최근 14일 전체가 아니라 24시간 + 과거 요약 테이블 분리로 갈 수 있는가
5. dashboard hot path와 ad-hoc 분석 path를 분리할 수 있는가

가능한 구조 개선은 보통 이런 식이다.

- ingest 시 또는 짧은 주기 배치로 hour-level aggregate table 생성
- 대시보드는 원본 로그가 아니라 aggregate table 조회
- user-level drill-down은 별도 상세 화면에서만 허용
- 자주 쓰는 조합만 materialized view 또는 summary table로 분리

즉 이 경우 핵심은,

> **HashAggregate가 spill 나는 이유가 메모리가 작아서가 아니라, 대시보드 요구와 저장 구조가 직접 맞붙고 있기 때문**

이라는 점이다.

이걸 놓치면 메모리 튜닝이 영구히 끝나지 않는다.

---

## 실무 예시 3: Hash Join spill은 `work_mem`보다 “작아 보여야 하는 쪽이 실제로는 크다”에서 시작하는 경우가 많다

다음 조인을 보자.

```sql
SELECT o.id,
       o.tenant_id,
       o.created_at,
       c.segment,
       p.plan_name
FROM orders o
JOIN customers c
  ON c.id = o.customer_id
JOIN plans p
  ON p.id = c.plan_id
WHERE o.created_at >= now() - interval '30 days'
  AND o.status = 'PAID'
  AND c.deleted_at IS NULL;
```

개발자는 보통 `customers`, `plans`가 차원 테이블이니 작을 것이라 기대한다.

하지만 운영에서는 다음이 흔하다.

- soft delete가 많아 `deleted_at IS NULL` 선택도가 낮다.
- `customers`가 이미 수천만 건 규모다.
- 필요한 컬럼보다 훨씬 많은 컬럼을 읽고 있다.
- 고객별 속성 확장으로 row width가 넓다.
- 통계가 오래돼 planner가 build side를 낙관적으로 본다.

그 결과 `Hash Join`이 아래처럼 보일 수 있다.

```text
Hash  
  Buckets: 1048576  Batches: 32  Memory Usage: 65536kB
  Buffers: ... temp written=...
```

여기서 중요한 신호는 `Batches`다.

- batch 1 근처 → 메모리 안에서 비교적 잘 처리
- batch 수가 커짐 → spill 또는 메모리 압박 징후

이때 좋은 대응 순서는 보통 아래다.

1. build side가 정말 작은지 다시 본다.
2. 필요한 컬럼만 projection 하도록 줄인다.
3. 필터를 더 일찍 적용할 수 있는지 본다.
4. 통계를 갱신하고 estimate/actual 오차를 본다.
5. 조인 순서가 잘못 유도되는 원인을 찾는다.
6. 그래도 근접한 메모리 경계라면 `work_mem` 또는 `hash_mem_multiplier`를 조정한다.

즉 Hash Join spill 대응은 “메모리를 올린다”보다 먼저,

- build side 축소
- row width 축소
- 통계 정확도 개선
- join shape 개선

을 점검해야 한다.

---

## 핵심 개념 3: 메모리 튜닝은 쿼리 하나가 아니라 동시성 모델의 문제다

실무에서 가장 비싼 실수는 특정 느린 쿼리 하나만 보고 글로벌 `work_mem`을 올리는 것이다.

단건 테스트에서는 효과가 있어 보인다.

문제는 운영은 단건 테스트가 아니라는 점이다.

### 왜 단일 쿼리 튜닝이 운영에서는 자주 배신하는가

예를 들어 staging에서 아래 쿼리를 실행해 보자.

- sort 1개
- hash aggregate 1개
- `work_mem=128MB`
- spill 없음
- 실행 시간 반으로 감소

여기까지만 보면 성공처럼 보인다.

그런데 운영에서는 아래가 동시에 존재한다.

- 같은 유형 쿼리 여러 개 동시 실행
- 다른 API 쿼리도 함께 실행
- autovacuum, replication, 배치 작업 등 백그라운드 부하 존재
- parallel query로 worker가 추가 메모리 사용
- 일시적 피크 시간대 존재

이 환경에서는 staging에서 안전해 보인 값이 운영에서는 쉽게 위험해진다.

### 대략적인 용량 계산 감각이 꼭 필요하다

완벽한 공식은 없다.

하지만 운영 판단용 대략식은 있다.

```text
예상 피크 추가 메모리
≈ 동시 active heavy queries
× 쿼리당 memory-heavy nodes 수
× worker multiplier
× work_mem
(해시 노드는 hash_mem_multiplier까지 고려)
```

예를 들어,

- 무거운 쿼리 동시 12개
- 쿼리당 sort 2개 + hash 1개
- parallel factor 2
- `work_mem=64MB`
- `hash_mem_multiplier=2.0`

이면 이미 매우 큰 메모리 예산이 필요하다.

여기서 중요한 건 숫자를 정밀하게 맞추는 것이 아니라,

- “이 값은 쿼리 하나엔 안전하지만 운영 전체엔 위험하다”는 감각을 갖는 것이다.

### `max_connections`로 단순 나누기 하면 안 되는 이유

가끔 이런 식 계산을 본다.

```text
RAM / max_connections = backend당 예산
```

그리고 거기서 `work_mem`을 정한다.

이건 너무 단순하다.

왜냐하면,

- 모든 연결이 동시에 무거운 sort/hash를 하지 않는다.
- 반대로 일부 시간대에는 특정 역할의 연결이 동시에 같은 무거운 쿼리를 던질 수 있다.
- connection pool 구조에 따라 active backend 수와 연결 수가 완전히 다르다.
- parallel worker와 maintenance 작업이 별도 메모리를 먹는다.

즉 실무에서 기준이 되어야 하는 것은 `max_connections` 자체보다,

- 실제 동시 active query 수
- 그중 메모리 heavy query 수
- API / 배치 / 리포트의 격리 수준
- connection pool과 workload class 분리 여부

다.

### 병렬 쿼리는 메모리 증폭기다

parallel query가 켜져 있으면 좋은 일이 많다.

- CPU 활용 향상
- 큰 스캔, 집계, 정렬의 벽시계 시간 감소

하지만 메모리 관점에서는 주의점이 있다.

- worker마다 sort/hash 구조가 반복될 수 있다.
- 한 쿼리의 메모리 소비가 기대보다 빨리 커진다.
- spill 감소를 위해 올린 `work_mem`이 병렬 환경에서는 과해질 수 있다.

그래서 병렬 쿼리가 적극적으로 쓰이는 환경이라면,

- `work_mem` 단일 값만 볼 것이 아니라
- 실제 `EXPLAIN` 계획에서 worker 수와 node 구성을 같이 봐야 한다.

---

## 핵심 개념 4: `work_mem` 조정보다 먼저 관측성을 세워야 한다

보이지 않는 메모리 병목은 늘 오해를 부른다.

운영에서 최소한 아래 네 축은 잡아두는 편이 좋다.

### 1) `EXPLAIN (ANALYZE, BUFFERS)` 습관화

이건 가장 기본이다.

왜 느린지 논쟁하기 전에,

- 어떤 node가 느린지
- actual rows가 얼마나 큰지
- temp read/write가 있는지
- `Sort Method`, `Disk`, `Batches`가 어떤지

를 봐야 한다.

가능하면 아래 포인트를 같이 읽는다.

- Sort node → `Sort Method`, `Disk`
- Hash / HashAggregate → `Batches`, `Memory Usage`, `Disk Usage`
- 상위 node → temp blocks 전파 여부
- estimate vs actual rows 차이

최신 버전이면 `MEMORY` 옵션도 도움이 되지만, 버전별 지원 차이가 있으니 운영 표준은 `ANALYZE, BUFFERS`부터 두는 편이 안전하다.

### 2) `log_temp_files`

이 설정은 temp 파일이 일정 크기 이상 생성될 때 로그를 남긴다.

이게 중요한 이유는 명확하다.

- EXPLAIN은 재현 쿼리에만 볼 수 있다.
- 운영에서 터지는 문제는 늘 재현 가능하지 않다.
- temp 파일 로그는 “언제, 어떤 백엔드에서, 얼마나 크게 spill이 났는지”의 단서를 준다.

실무에서는 보통,

- 처음에는 보수적인 임계값으로 켜고
- noisy하면 상향 조정하며
- 큰 spill 이벤트는 경보 대상으로 관리하는 식이 좋다.

### 3) `pg_stat_statements`

쿼리 단위 누적 통계가 있어야 “누가 temp를 가장 많이 쓰는가”를 볼 수 있다.

특히 temp 관련 블록 지표와 평균/총 실행 시간, 호출 횟수를 같이 봐야 한다.

이유는 다음과 같다.

- 아주 느린 한 방 쿼리인지
- 자주 실행되는 중간급 느린 쿼리인지
- temp는 조금 쓰지만 호출 수가 너무 많은지

가 서로 전혀 다른 문제이기 때문이다.

운영 최적화에서는 자주 호출되는 중간급 쿼리가 총 비용이 더 클 때가 많다.

### 4) `pg_stat_database`와 디스크 레벨 관측

DB 전체 temp 파일/바이트 추세를 봐야 한다.

왜냐하면 개별 쿼리 튜닝이 끝나도,

- 배치 시간대 temp 사용량이 폭증하는지
- 특정 배포 이후 temp 패턴이 바뀌었는지
- 디스크 여유 공간이 안정적인지

를 못 보면 운영 사고를 놓친다.

temp는 종종 “성능” 문제이면서 동시에 “용량” 문제다.

spill이 심한 시스템은 결국 다음 위험으로 이어질 수 있다.

- temp 볼륨 고갈
- noisy neighbor 현상
- I/O saturation
- 다른 중요 쿼리까지 tail latency 악화

### 5) auto_explain

운영에서 특정 임계 시간을 넘는 쿼리의 실제 계획을 자동으로 남기는 전략도 강력하다.

물론 과하게 켜면 오버헤드와 로그 폭주가 생길 수 있다.

그래도 재현이 어려운 간헐적 spill 문제를 잡을 때는 매우 유용하다.

특히,

- 배치 시간대만 느린 쿼리
- 특정 테넌트 데이터에서만 나쁜 계획
- 통계 변동 후 계획이 뒤집히는 쿼리

같은 사례에서 도움이 된다.

---

## 메모리 병목을 볼 때 `estimate vs actual`이 중요한 이유

spill 문제를 단순히 메모리 부족으로만 해석하면 통계 문제를 놓친다.

예를 들어 planner가 아래처럼 잘못 믿고 있다고 하자.

- build side는 10만 row쯤 될 것이다
- 실제는 800만 row다

그러면 어떤 일이 벌어질까.

- hash join을 싸다고 선택한다.
- 실제로는 hash table이 훨씬 커진다.
- batch 분할이 늘고 temp 파일이 생긴다.
- 운영자는 `work_mem`을 올리게 된다.

그런데 본질은 메모리 그 자체가 아니라 **오판된 실행 계획**일 수 있다.

이 경우 먼저 필요한 것은 종종 아래다.

- `ANALYZE`
- `CREATE STATISTICS`
- 쿼리 조건 구조 재검토
- 조인 순서 유도 원인 분석
- 데이터 편향 확인

즉 spill은 결과이고, 원인은 플래너 오판일 수 있다.

실무에서 이걸 잘못 보면,

- 메모리 값은 계속 커지는데
- 계획은 여전히 나쁘고
- 동시성만 더 위험해지는

방향으로 간다.

---

## 핵심 개념 5: 좋은 메모리 튜닝은 글로벌 상향보다 “범위 제한된 상향”에서 시작한다

운영에서 가장 안전한 기본 원칙 중 하나는 이렇다.

> **모든 쿼리를 위해 `work_mem`을 크게 올리기보다, 정말 필요한 쿼리/세션/역할에만 더 주는 편이 대개 낫다.**

이유는 단순하다.

- 메모리 heavy 쿼리는 전체 쿼리 중 일부다.
- API read path는 낮은 tail latency와 안정성이 더 중요할 수 있다.
- 리포트/배치는 빈도가 낮고 중요도가 높아 세션별 상향이 합리적이다.

### `SET LOCAL`을 적극적으로 고려할 만한 경우

예를 들어 관리 배치나 리포트 트랜잭션에서는 다음처럼 scope를 좁힐 수 있다.

```sql
BEGIN;
SET LOCAL work_mem = '256MB';
SET LOCAL statement_timeout = '15min';
SELECT ...;
COMMIT;
```

이 접근의 장점은 크다.

- 필요한 쿼리만 더 큰 메모리를 사용한다.
- 일반 API 트래픽까지 위험하게 만들지 않는다.
- 튜닝 효과를 비교적 명확하게 검증할 수 있다.

### role 단위 분리도 실용적이다

운영 조직이 어느 정도 분리되어 있다면,

- API role
- batch role
- analyst/reporting role

별로 메모리 정책을 다르게 가져갈 수 있다.

이건 단순 성능 튜닝이 아니라 **워크로드 격리 전략**이다.

### 글로벌 상향이 맞는 경우도 있다

물론 전체적으로 spill이 너무 잦고,

- workload가 비교적 균질하며
- active heavy query 수가 통제되고
- connection pool과 자원 격리가 잘 되어 있고
- 현재 값이 지나치게 보수적이며
- 작은 상향만으로 다수 쿼리가 안정화된다면

글로벌 `work_mem` 소폭 상향이 합리적일 수 있다.

다만 이때도 “소폭”과 “검증”이 중요하다.

예를 들어,

- 4MB → 16MB
- 8MB → 32MB

같은 단계적 조정은 괜찮지만,

- 16MB → 256MB

같은 점프는 동시성 환경에서 아주 위험할 수 있다.

---

## 실무 튜닝 플레이북: spill 쿼리를 봤을 때 무엇부터 할 것인가

운영에서 실제로 바로 쓸 수 있는 순서를 정리해 보자.

### 1단계: 어떤 노드가 spill 났는지 구분한다

- Sort인가
- Hash Join인가
- HashAggregate인가
- Materialize/기타 temp working node인가

이 구분 없이 `work_mem`부터 올리면 안 된다.

### 2단계: 입력 row 수와 row width를 먼저 줄일 수 있는지 본다

- 더 선택적인 필터 가능 여부
- projection 축소 가능 여부
- `SELECT *` 제거
- 조인 전에 줄일 수 있는 집합 여부
- dashboard/lookup용 summary table 가능 여부

메모리 사용량은 row 수뿐 아니라 row width에도 민감하다.

### 3단계: 정렬을 피하거나 줄일 수 있는지 본다

- order-by를 인덱스로 충족 가능한가
- incremental sort 가능성이 있는가
- keyset pagination으로 바꿀 수 있는가
- DISTINCT가 정말 필요한가
- window 함수 정렬 범위를 줄일 수 있는가

### 4단계: 통계와 실행 계획 오판을 점검한다

- actual rows가 estimate와 얼마나 다른가
- 데이터 편향이 큰가
- 다중 컬럼 상관관계를 planner가 모르는가
- 최근 대량 적재/삭제 이후 통계가 낡았는가

### 5단계: 그다음에만 메모리 값을 조정한다

- 글로벌인가
- role별인가
- 세션/트랜잭션별인가
- `hash_mem_multiplier`가 더 나은가

### 6단계: 동시성 환경에서 재검증한다

단건 EXPLAIN만으로 끝내지 말고,

- 실제 peak 시간대 패턴
- temp 파일 총량
- 메모리 사용량
- 쿼리 호출 수
- OOM 또는 swap 위험

까지 같이 봐야 한다.

이 순서를 지키면 “왜 이 값으로 조정하는가”가 설명 가능해진다.

---

## 핵심 개념 6: 예상 밖 spill의 절반은 숨은 정렬과 중간 결과 저장에서 나온다

실무에서 자주 생기는 오해가 하나 있다.

- `ORDER BY`가 없으니 sort가 없을 것이다.
- `GROUP BY`만 있으니 정렬보다는 집계만 보면 된다.
- 조인이 단순하니 temp 파일도 작을 것이다.

하지만 실제 계획을 보면 정렬은 훨씬 더 다양한 위치에서 등장한다.

### 숨은 sort가 자주 생기는 대표 상황

#### 1) `DISTINCT`

개발자는 중복 제거를 “필터 한 번 더 거는 정도”로 생각하기 쉽다.

하지만 planner는 상황에 따라 정렬 기반 중복 제거를 선택할 수 있다.

특히 wide row에 `DISTINCT`를 바로 걸면,

- 정렬 입력이 커지고
- temp 파일이 커지고
- 최종 결과 row 수는 적어도 중간 비용은 크게 늘어난다.

이때는 종종 다음이 더 낫다.

- 중복 제거 전에 projection 축소
- 정말 필요한 key만 먼저 distinct
- 존재 여부 확인이면 `EXISTS`로 재작성
- 불필요한 join에서 생긴 duplicate를 upstream에서 제거

#### 2) Window function

예를 들어 아래 쿼리를 보자.

```sql
SELECT user_id,
       created_at,
       amount,
       row_number() OVER (
         PARTITION BY user_id
         ORDER BY created_at DESC
       ) AS rn
FROM payments
WHERE created_at >= now() - interval '30 days';
```

겉으로 보면 집계가 아니라 분석 함수다.

하지만 실제로는 파티션별 정렬 비용이 들어간다.

- partition key가 많으면 메모리 사용이 커질 수 있다.
- 입력 범위가 넓으면 temp spill이 흔해진다.
- 후속 필터에서 `rn = 1`만 쓰더라도 전체 중간 정렬을 피하지 못하는 경우가 있다.

이런 경우에는 다음 패턴을 고민할 가치가 있다.

- 사용자별 최신 1건이면 `DISTINCT ON`이 더 단순한가
- 최신 row lookup 전용 인덱스로 문제를 푸는 편이 나은가
- window 적용 대상을 먼저 줄일 수 있는가

#### 3) Merge Join 준비 정렬

join 자체는 merge join인데, 양쪽 입력이 이미 정렬돼 있지 않다면 planner가 입력 양쪽에 sort를 추가할 수 있다.

그러면 운영자가 보기에는 “조인 하나 느리다”로 보이지만,

실제 비용 구조는 다음일 수 있다.

- 왼쪽 입력 정렬 spill
- 오른쪽 입력 정렬 spill
- 이후 merge join 수행

즉 조인 노드만 보면 원인을 놓친다.

#### 4) CTE / subquery / materialization

최신 PostgreSQL은 과거보다 CTE를 더 유연하게 다루지만,

여전히 중간 결과를 크게 물고 가는 쿼리 구조에서는 materialization 성격의 비용이 생길 수 있다.

예를 들어,

- 아주 넓은 중간 결과를 만든 뒤
- 나중 단계에서 조금만 쓰는 구조
- 같은 중간 결과를 여러 번 재사용하는 구조
- 불필요하게 `WITH` 블록을 깊게 쌓는 구조

에서는 temp blocks가 생각보다 커질 수 있다.

실무에서 자주 통하는 개선은 놀랄 만큼 단순하다.

- 중간 결과 projection 줄이기
- 필터를 가능한 앞쪽으로 당기기
- `WITH`가 읽기 좋다는 이유만으로 큰 결과를 오래 붙잡지 않기
- 재사용 가치가 크면 진짜 임시 테이블 또는 summary table로 명시적 분리하기

#### 5) `UNION`과 `UNION ALL` 혼동

`UNION`은 중복 제거가 필요하다.

즉 단순 연결이 아니라 추가 정렬 또는 hash distinct 성격의 비용이 붙을 수 있다.

반면 중복 제거가 정말 필요 없다면 `UNION ALL`이 훨씬 싸다.

이건 메모리 튜닝 이전에 쿼리 의도 정리 문제다.

### 왜 이 섹션이 중요한가

숨은 sort와 중간 결과 저장을 모르면 운영 대응이 자꾸 헛돈다.

- `ORDER BY`가 없으니 sort 아닐 거라 생각한다.
- 실제로는 window나 distinct가 정렬을 만든다.
- `work_mem`을 올렸는데도 기대만큼 안 빨라진다.
- 이유는 sort가 하나가 아니라 여러 개였기 때문이다.

즉 spill 대응의 시작점은 문법이 아니라 plan node다.

---

## 핵심 개념 7: `temp file`을 없애는 것과 `temp I/O`를 통제하는 것은 다르다

운영자가 temp 파일을 처음 보면 instinctively 이렇게 반응하기 쉽다.

- temp 파일이 생겼다 → 나쁘다
- temp 파일이 많다 → 반드시 메모리를 올려야 한다

하지만 temp 파일 운영은 조금 더 현실적으로 봐야 한다.

### temp 파일이 주는 두 가지 다른 신호

#### 신호 1) 특정 쿼리가 메모리 경계 밖으로 나간다

이건 성능 문제다.

- 정렬이 메모리 안에 안 들어간다.
- hash table이 커진다.
- 중간 결과를 disk-backed 구조로 처리한다.

#### 신호 2) 시스템 전체가 temp I/O에 민감해지고 있다

이건 운영 안정성 문제다.

- 여러 쿼리가 동시에 spill 난다.
- temp 디스크 대역폭이 경쟁 상태다.
- 다른 쿼리까지 tail latency가 악화된다.
- 여유 공간이 줄며 장애 위험이 커진다.

첫 번째 신호는 특정 쿼리 최적화로 풀 수 있다.

두 번째 신호는 워크로드 관리와 리소스 가드레일이 필요하다.

### temp I/O는 단순히 느림만 유발하지 않는다

특히 다음 상황에서는 문제 전파력이 커진다.

- 보고서 쿼리 수십 개가 같은 시각에 시작된다.
- ETL 배치와 사용자 API가 같은 인스턴스를 공유한다.
- temp가 올려진 볼륨이 데이터 볼륨과도 경합한다.
- 클라우드 디스크 burst credit이 있는 환경이다.
- temp 디렉터리 여유 공간이 작다.

이때는 개별 쿼리가 조금 spill 나는 것보다,

**spill이 겹치는 시간대가 운영 리스크**가 된다.

### temp를 다루는 현실적인 원칙

1. temp 파일을 0으로 만드는 것을 목표로 두지 않는다.
2. 대신 hot path에서의 반복 spill, 대형 spill, 동시 spill을 줄인다.
3. temp 디스크는 모니터링 대상이지, 블랙박스가 아니다.
4. 배치/리포트의 temp 사용량은 API와 분리해서 본다.
5. temp가 빠른 디스크에 있다고 해도 구조 문제까지 해결되었다고 착각하지 않는다.

### `temp_tablespaces`와 빠른 스토리지는 어디까지 도움이 될까

운영 경험상 temp를 빠른 스토리지로 분리하는 것은 꽤 유용할 수 있다.

- spill이 완전히 없어지진 않아도 피해를 줄인다.
- 본 데이터 볼륨과 경합을 줄일 수 있다.
- temp-heavy 배치의 충격을 완화할 수 있다.

하지만 이건 어디까지나 완충 장치다.

정렬과 hash가 구조적으로 과하면,

- 빠른 디스크에서도 temp는 계속 쌓이고
- tail latency는 여전히 요동치며
- 근본 원인은 남는다.

즉 temp 스토리지는 seatbelt에 가깝다.

운전 습관까지 대신해주지는 않는다.

---

## 실전 관측 SQL: temp-heavy query를 찾을 때 바로 써볼 수 있는 예시

관측은 결국 쿼리로 이어져야 한다.

환경마다 스키마와 확장 설치 여부는 다르겠지만, 아래 예시는 사고 방향을 잡는 데 유용하다.

### 예시 1) `pg_stat_statements`에서 temp를 많이 쓴 쿼리 상위 보기

```sql
SELECT queryid,
       calls,
       total_exec_time,
       mean_exec_time,
       temp_blks_read,
       temp_blks_written,
       rows,
       LEFT(query, 400) AS query_sample
FROM pg_stat_statements
WHERE temp_blks_read > 0
   OR temp_blks_written > 0
ORDER BY temp_blks_written DESC, temp_blks_read DESC
LIMIT 20;
```

이 쿼리에서 같이 봐야 하는 것은 단순 순위가 아니다.

- `calls`가 낮고 temp가 큰가 → 대형 단발성 리포트일 가능성
- `calls`가 높고 temp도 의미 있게 큰가 → 장기 비용이 더 큰 hot query일 가능성
- 평균은 짧지만 호출 수가 너무 많은가 → API path일 수 있음

즉 temp 총량과 호출 패턴을 같이 봐야 한다.

### 예시 2) DB 전체 temp 추세 확인

```sql
SELECT datname,
       temp_files,
       pg_size_pretty(temp_bytes) AS temp_bytes
FROM pg_stat_database
ORDER BY temp_bytes DESC;
```

이 지표는 개별 쿼리보다 시스템 관점에서 중요하다.

- 배포 후 temp가 전반적으로 늘었는가
- 특정 DB만 유난히 높은가
- 배치 시간대에 누적 증가 속도가 이상한가

같은 질문에 답하게 해준다.

### 예시 3) 특정 느린 쿼리의 실제 계획 확인

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT ...;
```

이때 체크리스트를 습관처럼 같이 둔다.

- sort method가 external merge인가
- hash batch 수가 큰가
- disk usage가 보이는가
- estimate와 actual rows 차이가 심한가
- temp blocks가 상위 노드에 얼마나 전파되는가

### 예시 4) temp-heavy reporting role 분리 이후 효과 검증

role 분리를 했다면,

- reporting role의 temp 사용량은 올라가도 괜찮은가
- API role의 temp 사용량은 줄었는가
- API p95가 안정화되었는가

를 같이 봐야 한다.

단순히 전체 평균만 보면 개선을 놓칠 수 있다.

### 예시 5) log_temp_files 로그와 queryid 연결

환경에 따라 자동 매핑 방식은 다르지만,

- temp 로그 시각
- backend pid
- 당시 실행 쿼리
- `pg_stat_statements` 상위 후보

를 연결할 수 있게 해두면 간헐적 사고 대응 속도가 크게 빨라진다.

운영에서 중요한 건 “쿼리를 정확히 잡는 능력”이지, 파라미터를 빨리 올리는 능력이 아니다.

---

## 실무 예시 4: offset pagination이 메모리 병목을 장기적으로 키우는 방식

많은 서비스가 초기에 아래처럼 간다.

```sql
SELECT id, created_at, title
FROM articles
WHERE tenant_id = 42
ORDER BY created_at DESC
LIMIT 50 OFFSET 50000;
```

처음엔 잘 된다.

데이터가 작기 때문이다.

하지만 시간이 지나면 다음 문제가 생긴다.

- 뒤 페이지로 갈수록 더 많은 후보 row를 스캔하고 버린다.
- order-by 경로가 비싸진다.
- planner가 sort 또는 큰 range scan을 택할 수 있다.
- tenant별 데이터가 커질수록 메모리와 I/O 비용이 누적된다.

이 문제를 단순히 `work_mem`으로 막으려 하면 결국 한계가 온다.

왜냐하면 offset pagination의 비용 구조 자체가 데이터 증가에 선형 또는 그 이상으로 나빠지기 쉽기 때문이다.

### keyset pagination이 왜 메모리에도 유리한가

예를 들어 아래처럼 바꾸면,

```sql
SELECT id, created_at, title
FROM articles
WHERE tenant_id = 42
  AND (created_at, id) < (:cursor_created_at, :cursor_id)
ORDER BY created_at DESC, id DESC
LIMIT 50;
```

잘 설계된 인덱스와 결합할 때 얻는 이점은 크다.

- 정렬 비용이 줄어든다.
- 불필요한 skip 비용이 줄어든다.
- temp spill 가능성이 낮아진다.
- page가 뒤로 갈수록 느려지는 현상이 완화된다.

즉 pagination 방식은 단순 UX 선택이 아니라 메모리 비용 모델에도 직접 연결된다.

---

## 실무 예시 5: `COUNT(DISTINCT ...)`가 왜 종종 예상보다 위험한가

분석성 쿼리에서 자주 보는 패턴이다.

```sql
SELECT tenant_id,
       COUNT(DISTINCT user_id)
FROM events
WHERE created_at >= now() - interval '7 days'
GROUP BY tenant_id;
```

겉으로는 단순 집계 같지만,

- DISTINCT 처리
- GROUP BY 처리
- 넓은 범위 스캔
- 높은 카디널리티

가 겹치면 메모리 사용이 금방 커진다.

이때 다음을 먼저 따져볼 만하다.

1. 정확한 distinct가 business critical인가
2. 근사치가 허용된다면 별도 시스템 또는 요약 테이블로 우회 가능한가
3. 미리 tenant/day 수준 summary를 적재할 수 있는가
4. raw events를 ad-hoc로만 남기고 제품 API는 summary를 사용하게 할 수 있는가

이 경우도 `work_mem`만으로 끝내기 어렵다.

문제는 연산의 비용 구조가 본질적으로 무겁기 때문이다.

---

## 핵심 개념 8: 쿼리 재작성은 “같은 의미를 더 싸게 표현하는 일”이어야 한다

성능 튜닝을 하다 보면 쿼리 재작성이 종종 과한 트릭처럼 받아들여진다.

하지만 좋은 재작성은 트릭이 아니라 의미 보존 + 비용 절감이다.

### 자주 효과가 큰 재작성 패턴

#### 1) 존재 여부 확인을 `JOIN + DISTINCT` 대신 `EXISTS`로 표현

나쁜 예:

```sql
SELECT DISTINCT u.id
FROM users u
JOIN orders o ON o.user_id = u.id
WHERE o.created_at >= now() - interval '30 days';
```

이 구조는 join 후 duplicate 제거 비용을 만든다.

더 나은 방향은 종종 이렇다.

```sql
SELECT u.id
FROM users u
WHERE EXISTS (
  SELECT 1
  FROM orders o
  WHERE o.user_id = u.id
    AND o.created_at >= now() - interval '30 days'
);
```

항상 더 빠른 것은 아니지만,

- 중복 제거 정렬/해시 비용을 줄이고
- planner가 semi join 성격으로 더 잘 최적화할 여지를 주는 경우가 많다.

#### 2) 큰 조인 전에 먼저 줄일 수 있는 집합을 줄이기

예를 들어 주문 전체와 고객 전체를 먼저 조인하기보다,

- 최근 7일 주문만 먼저 추려서
- 필요한 컬럼만 남기고
- 그다음 고객 조인

으로 가면 build/probe 양쪽 부담을 줄일 수 있다.

#### 3) 넓은 payload는 나중에 붙이기

JSONB, 긴 text, 설명 컬럼, blob reference 같은 넓은 값은,

- 정렬/집계/조인 이전에 꼭 필요하지 않다면
- 마지막 단계에 붙이거나
- 별도 lookup으로 분리하는 편이 메모리에 유리하다.

#### 4) 대형 `IN (...)` 목록은 접근 경로를 다시 생각하기

매우 큰 `IN` 목록은 planner와 메모리 모두에 부담을 줄 수 있다.

환경에 따라,

- 임시 테이블에 넣고 join
- semi join 구조
- 애플리케이션 측 분할

같은 우회가 더 운영 친화적일 수 있다.

즉 재작성의 목적은 syntax change가 아니라,

**실행 엔진이 덜 많은 row를, 덜 넓은 row로, 덜 오래 붙잡게 만드는 것**이다.

---

## 안전한 롤아웃 전략: `work_mem`을 바꿀 때는 기능 배포처럼 다뤄야 한다

운영 파라미터 변경은 종종 코드 배포보다 덜 엄격하게 다뤄진다.

하지만 `work_mem` 류 조정은 실제로는 꽤 위험한 운영 변경이다.

### 1) 기준선 먼저 확보

변경 전 최소한 아래는 잡아둔다.

- 대표 쿼리의 실행 시간
- temp 파일 총량
- p95/p99
- 메모리 사용량 또는 OOM 징후
- peak 시간대 동시 실행 패턴

이게 없으면 “좋아졌는지”를 체감에 의존하게 된다.

### 2) 변경 범위를 가장 작게 시작

가능하면 순서는 이렇다.

1. 세션/트랜잭션 단위 실험
2. 특정 role만 상향
3. 배치 전용 워커나 리포트 전용 풀만 상향
4. 마지막에만 글로벌 검토

이 순서가 좋은 이유는 blast radius가 작기 때문이다.

### 3) peak workload에서 확인

한가한 시간에만 테스트하면 종종 실패한다.

왜냐하면 spill 문제는 대개 피크에서만 진짜 모습을 드러내기 때문이다.

- 같은 쿼리가 여러 개 겹칠 때
- API와 배치가 같이 돌 때
- parallel worker가 많이 붙을 때

를 봐야 한다.

### 4) rollback 조건을 명확히 정해둔다

예를 들어 아래 중 하나라도 보이면 원복한다는 식이다.

- temp는 줄었지만 RSS/메모리 피크가 과도하게 상승
- OOM 또는 swap 징후 발생
- 다른 API p95 악화
- batch 처리량은 좋아졌지만 전체 시스템 안정성 악화

좋은 변경은 빠른 성공보다 빠른 원복 기준이 먼저다.

### 5) 문서화한다

의외로 자주 빠지는 단계다.

- 왜 값을 바꿨는가
- 어떤 쿼리 때문에 바꿨는가
- 어떤 지표가 개선됐는가
- 어느 workload에만 적용해야 하는가

가 남아 있어야 다음 운영자가 다시 같은 실험을 반복하지 않는다.

---

## 팀 의사결정을 위한 추천 질문 12개

메모리 튜닝 회의에서 아래 질문만 잘 던져도 대화 수준이 확 올라간다.

1. 이 쿼리는 hot path인가, 배치/리포트인가
2. 느린 원인이 sort인가 hash인가
3. spill이 plan node 몇 개에서 동시에 발생하는가
4. 입력 row 수를 줄일 수 있는가
5. row width를 줄일 수 있는가
6. 정렬을 인덱스로 대체할 수 있는가
7. group cardinality를 줄일 수 있는가
8. build side가 정말 작은가
9. estimate/actual rows 오차가 큰가
10. 세션 단위 상향으로 충분한가
11. peak 시간대 동시 heavy query 수는 몇 개인가
12. 이 문제는 파라미터보다 read model 설계 문제에 더 가까운가

이 질문 없이 `work_mem` 숫자부터 논의하면 대개 가장 비싼 선택을 하게 된다.

---

## 빠른 참조: 실행 계획에서 메모리 관련 노드를 읽을 때 기억할 포인트

실무에서는 느린 쿼리를 볼 때마다 처음부터 공부하듯 해석할 시간이 없다.

아래 메모는 메모리 병목 관점에서 plan node를 빠르게 읽기 위한 요약이다.

### `Sort`

- 관심 포인트: `Sort Method`, `Disk`, temp blocks
- 질문: 이 sort를 인덱스로 피할 수 있는가
- 질문: 입력 row 수를 줄일 수 있는가
- 질문: LIMIT가 있다면 top-N 경로를 더 잘 타게 만들 수 있는가

### `Incremental Sort`

- 관심 포인트: 이미 일부 정렬된 입력을 활용하는가
- 질문: 인덱스 prefix와 order-by suffix가 맞물리는가
- 질문: 완전 정렬보다 incremental이 더 유리한 데이터 분포인가
- 질문: planner가 그 경로를 선택할 만큼 prefix 선택도가 좋은가

이 노드는 “정렬이 아예 없다”는 뜻이 아니라,

**이미 얻은 순서를 최대한 재사용해 정렬 비용을 줄인다**는 뜻에 가깝다.

즉 인덱스와 정렬 요구가 조금만 맞아도 temp 비용을 크게 줄일 여지가 있다.

### `Hash`

- 관심 포인트: `Buckets`, `Batches`, `Memory Usage`
- 질문: build side가 정말 작은가
- 질문: 필요한 컬럼만 읽고 있는가
- 질문: estimate 오차 때문에 큰 쪽을 메모리에 올리고 있지 않은가

특히 `Batches`가 커지면 spill 또는 메모리 압박 신호로 보는 습관이 좋다.

### `Hash Join`

- 관심 포인트: hash node 자체와 join 상위 node의 temp 사용
- 질문: join 전에 줄일 수 있는 입력이 있는가
- 질문: semi join / exists / pre-filter로 shape를 바꿀 수 있는가
- 질문: row width가 쓸데없이 넓지 않은가

### `HashAggregate`

- 관심 포인트: `Batches`, `Memory Usage`, `Disk Usage`
- 질문: group cardinality를 줄일 수 있는가
- 질문: summary table 또는 pre-aggregation이 더 자연스러운가
- 질문: exact aggregate가 꼭 필요한가

### `GroupAggregate`

이 노드는 종종 정렬과 함께 온다.

즉 집계가 hash가 아니더라도,

- 앞단 sort 비용
- 정렬 유지 비용
- 입력 범위

를 같이 봐야 한다.

`GROUP BY`가 느리다고 해서 항상 `HashAggregate`만 문제는 아니다.

### `Materialize`

- 관심 포인트: 상위 노드의 반복 접근을 위해 중간 결과를 들고 있는가
- 질문: 중간 결과가 너무 넓거나 큰가
- 질문: 재사용 가치가 낮은데도 큰 결과를 유지하고 있지 않은가
- 질문: 쿼리 구조를 단순화할 수 있는가

### `Memoize`

최신 계획에서 보이는 이 노드는 좋은 최적화일 때도 많다.

다만 메모리 관점에서는,

- lookup cardinality
- 캐시 hit ratio
- 상위 반복 패턴

에 따라 효과와 비용이 갈린다.

즉 “좋은 노드니까 무조건 건드리지 말자”보다,

실제 반복 패턴과 row width를 같이 봐야 한다.

### `Merge Join`

merge join 자체는 메모리 폭탄이 아닐 수 있다.

하지만 그 앞단에 양쪽 sort가 붙으면 이야기가 달라진다.

그래서 merge join이 느릴 때는 join node 하나만 보지 말고,

- 왼쪽 정렬
- 오른쪽 정렬
- temp blocks 전파

를 같이 봐야 한다.

### `Nested Loop`

겉으로는 메모리 친화적일 수 있다.

하지만 planner 오판으로 outer rows가 너무 많으면,

- 반복 index lookup 폭증
- 캐시 미스 증가
- 상위 node의 materialization 증가

같은 다른 비용으로 터질 수 있다.

즉 spill이 없다고 항상 좋은 계획은 아니다.

메모리 병목을 해결하려다 다른 병목을 만들지 않는 균형이 필요하다.

---

## 워크로드 분리 관점에서 보는 실전 패턴

운영에서 메모리 문제를 가장 깔끔하게 줄이는 방법 중 하나는 사실 파라미터가 아니라 분리다.

### 패턴 1) API와 리포트를 role 단위로 분리

가장 실용적인 출발점이다.

- API role → 낮은 `work_mem`, 짧은 timeout, 높은 안정성 우선
- reporting role → 제한된 동시성, 더 높은 `work_mem`, 더 긴 timeout 허용

이 방식의 장점은 명확하다.

- hot path 보호
- 메모리 heavy query 범위 제한
- 운영 판단 단순화

### 패턴 2) connection pool을 workload별로 나누기

하나의 풀 안에서 모든 쿼리가 섞이면,

- 보고서 폭주가 API 슬롯을 잠식하고
- 메모리 heavy query가 동시에 몰리며
- temp I/O도 한꺼번에 증가한다.

반대로 pool을 분리하면,

- reporting 동시성 상한을 별도로 둘 수 있고
- batch 시작 시간을 제어할 수 있으며
- `work_mem` 정책도 더 안전하게 다르게 가져갈 수 있다.

### 패턴 3) read replica에 reporting workload 격리

모든 경우의 해법은 아니지만,

- 원본 OLTP를 보호하고
- 분석성 read를 분리하고
- 다소 공격적인 세션 메모리 정책을 replica에만 적용

하는 전략은 자주 유효하다.

물론 replica에서도 spill은 여전히 문제다.

하지만 적어도 사용자 트랜잭션 hot path와 직접 충돌하지 않게 만들 수 있다.

### 패턴 4) summary table / materialized view로 hot query shape 자체를 분리

이건 가장 본질적인 분리다.

- API는 요약 테이블만 본다.
- 상세 분석은 원본 로그를 본다.
- 고비용 집계는 사전에 계산한다.

이 패턴이 강한 이유는 메모리 튜닝 문제가 반복되지 않기 때문이다.

원본 로그가 10배 커져도,

핫패스는 상대적으로 안정적으로 유지될 수 있다.

### 패턴 5) 배치 시간대 조절

아주 단순하지만 실전적인 방법이다.

- 사용자 피크 시간대와 대형 집계 배치를 겹치지 않게 한다.
- vacuum, reindex, big report를 같은 시간에 몰지 않는다.
- temp-heavy job을 시차 배치한다.

이건 SQL 한 줄도 안 바꾸지만 효과가 클 때가 많다.

동시성은 메모리 증폭기이기 때문이다.

---

## 작은 사례 비교: 같은 문제를 세 가지 방식으로 푸는 법

다음 상황을 상상해 보자.

- 최근 30일 주문을 tenant별로 집계하는 dashboard가 느리다.
- `HashAggregate` spill이 발생한다.
- temp 파일도 크다.

가능한 대응은 크게 세 가지다.

### 대응 A) 글로벌 `work_mem` 상향

장점:

- 빠르게 시도 가능
- 일부 쿼리는 즉시 빨라질 수 있음

단점:

- 다른 workload까지 메모리 리스크 증가
- 동시성 환경에서 OOM 위험
- 구조 문제는 남음

### 대응 B) reporting role에만 `SET LOCAL work_mem`

장점:

- 효과 범위가 제한적
- 운영상 안전함
- 구조 개선 전 임시 완충으로 유용

단점:

- dashboard 호출 수가 많아지면 결국 한계
- 원본 로그 직접 집계라는 구조 문제는 남음

### 대응 C) summary table 도입

장점:

- 구조적 해결
- hot path 안정성 향상
- 메모리와 temp 비용이 장기적으로 감소

단점:

- 구현 비용
- 적재 파이프라인 관리 필요
- 데이터 freshness 계약을 새로 정의해야 함

실무에서 좋은 선택은 종종 하나만 고르는 것이 아니라,

- 단기적으로 B로 완충하고
- 중기적으로 C로 구조 전환하는 것

이다.

메모리 튜닝은 이렇게 단계적으로 보는 편이 낫다.

---

## 트레이드오프 1: spill을 허용하는 것이 항상 나쁜가

꼭 그렇지는 않다.

이건 꽤 중요한 현실 감각이다.

일부 워크로드에서는 spill을 완전히 없애는 것이 과도한 목표일 수 있다.

예를 들어,

- 하루 한두 번 도는 대형 분석 쿼리
- 운영자 수동 리포트
- 야간 비정기 backfill

같은 경우라면,

- 조금 느리더라도 spill을 허용하고
- 전체 시스템 메모리 안전성을 더 우선하는 전략이 맞을 수 있다.

왜냐하면 spill 제로를 목표로 메모리를 크게 잡으면,

- 평소 거의 안 쓰는 쿼리를 위해
- 전체 시스템 리스크를 높이는

형태가 되기 쉽기 때문이다.

즉 좋은 운영자는 모든 spill을 악으로 보지 않는다.

대신 이렇게 묻는다.

- 이 spill은 business critical hot path를 해치는가
- temp 디스크를 압박하는가
- 동시 시간대에 다른 워크로드를 흔드는가
- 쿼리 빈도에 비해 비용이 과한가

문제가 아니라면 spill을 허용하는 것도 성숙한 선택이다.

---

## 트레이드오프 2: 메모리 상향 vs 인덱스 추가 vs 쿼리 재구성

세 선택지는 종종 경쟁 관계가 아니다.

하지만 우선순위는 다르다.

### 메모리 상향이 유리한 경우

- 쿼리 중요도가 높다.
- 빈도는 낮다.
- 현재 경계값 바로 바깥이라 조금만 올리면 메모리 안으로 들어온다.
- 구조 변경 비용이 크다.

### 인덱스 추가가 유리한 경우

- 정렬 회피가 가능하다.
- hot path 조회다.
- 같은 패턴이 자주 반복된다.
- 읽기 성능 개선이 장기적으로 유리하다.

단, 인덱스는 쓰기 비용을 늘린다.

즉 `ORDER BY` 하나 없애겠다고 무분별하게 인덱스를 늘리면,

- INSERT/UPDATE 비용 증가
- vacuum 부담 증가
- HOT update 기회 감소
- 디스크 사용량 증가

로 이어질 수 있다.

### 쿼리 재구성이 유리한 경우

- group cardinality가 과도하다.
- 조인 전후 필터 위치가 비효율적이다.
- summary table이나 materialized view가 자연스럽다.
- 조회 요구와 원본 raw data가 직접 붙어 있다.

실무에서 가장 큰 성능 개선은 자주 쿼리 재구성에서 나온다.

메모리와 인덱스는 그 다음이다.

---

## 흔한 실수 1: `work_mem`을 서버 RAM에 맞춰 단순히 크게 잡는다

가장 유명한 함정이다.

예를 들어 RAM이 64GB라고 해서,

- `shared_buffers`도 크게 주고
- `work_mem`도 128MB, 256MB씩 주고
- parallel worker도 열어두고
- 리포트 쿼리도 같은 인스턴스에서 돌리면

실제 피크에서는 아주 쉽게 위험해진다.

PostgreSQL은 `work_mem`을 “필요할 때만” 쓰지만,

운영 사고는 늘 “필요한 쿼리가 겹칠 때” 발생한다.

그래서 단일 쿼리 기준으로 넉넉해 보이는 값이,

동시성 환경에서는 전혀 넉넉하지 않을 수 있다.

---

## 흔한 실수 2: spill 원인이 Sort인지 Hash인지 구분하지 않는다

둘 다 temp 파일을 만들 수 있다.

하지만 대응은 다르다.

- Sort → 인덱스, pagination, 정렬 범위 축소, incremental sort 가능성 검토
- Hash Join → build side 축소, 통계, 조인 순서, projection 축소
- HashAggregate → group cardinality, summary table, pre-aggregation, range 축소

이 구분이 없으면 모든 문제를 `work_mem` 하나로만 보게 된다.

---

## 흔한 실수 3: temp 파일을 봤는데도 디스크 관측을 안 붙인다

spill은 쿼리 느림으로만 끝나지 않는다.

다음이 같이 온다.

- temp 볼륨 압박
- I/O 지연 증가
- 다른 쿼리 tail latency 악화
- 장애 상황에서 남는 여유 공간 부족

그래서 운영에서는 temp 파일 알림과 temp 디스크 사용량 추세를 같이 봐야 한다.

“쿼리 하나 느림”이 “DB 전체 흔들림”으로 번지는 대표 경로다.

---

## 흔한 실수 4: `SELECT *`와 넓은 row width를 무시한다

메모리 집약적 쿼리에서 row width는 매우 중요하다.

같은 100만 row라도,

- 필요한 컬럼 4개만 읽는 경우
- JSONB, 긴 TEXT, 여러 조인 컬럼까지 넓게 들고 가는 경우

는 메모리 압박이 크게 다르다.

Hash Join과 HashAggregate는 특히 row width 영향을 크게 받는다.

실무에서 생각보다 자주 통하는 최적화가,

- 서브쿼리에서 필요한 컬럼만 먼저 projection
- 조인 전에 큰 payload 제거
- 집계 전에 넓은 컬럼을 제외

같은 아주 기본적인 정리다.

---

## 흔한 실수 5: `ANALYZE`와 통계 문제를 메모리 문제로 착각한다

spill이 났다고 해서 늘 메모리부터 부족한 것은 아니다.

planner가 row 수를 심하게 오판하면,

- 잘못된 join strategy 선택
- build side 크기 오판
- 정렬 비용 과소평가

가 이어진다.

이 경우 필요한 것은 종종 다음이다.

- 통계 갱신
- extended statistics
- 조건 재작성
- 데이터 skew 파악

즉 메모리는 결과이고, 플래너 오판이 원인일 수 있다.

---

## 흔한 실수 6: API와 리포트를 같은 메모리 정책으로 운영한다

서비스 운영에서는 workload class가 다르다.

- 사용자 API는 짧고 안정적인 응답이 중요하다.
- 운영자 리포트는 다소 느려도 깊은 집계가 필요하다.
- 배치는 긴 실행시간을 감수할 수 있지만 시스템 전체 안전성이 중요하다.

그런데 모두 같은 role, 같은 pool, 같은 `work_mem`으로 묶어두면,

- hot path 안정성도 잃고
- 리포트 성능도 만족 못 하고
- 튜닝 여지도 줄어든다.

가능하면 역할 분리와 scope-limited tuning이 훨씬 낫다.

---

## 흔한 실수 7: spill이 줄었는지만 보고 전체 비용을 안 본다

가끔 `work_mem`을 올리면 spill은 줄어든다.

하지만 그게 곧 전체 시스템 개선은 아니다.

확인해야 할 것은 적어도 다음이다.

- 평균 시간뿐 아니라 p95/p99
- temp 파일 총량
- 프로세스 메모리 피크
- 동시성 시간대 안정성
- OOM/swap 징후
- 다른 쿼리 성능 악화 여부

한 쿼리가 빨라졌는데 전체 시스템이 불안해졌다면 실패다.

---

## 체크리스트: PostgreSQL 메모리 병목을 봤을 때 바로 점검할 항목

### A. 증상 확인

- temp 파일 생성이 실제로 있는가
- temp 디스크 사용량이 시간대별로 튀는가
- 느린 쿼리가 특정 시간/테넌트/배치와 연동되는가
- spill이 상시인지, 피크 한정인지

### B. 실행 계획 확인

- `EXPLAIN (ANALYZE, BUFFERS)`를 봤는가
- Sort면 `Sort Method`, `Disk`를 확인했는가
- Hash면 `Batches`, `Memory Usage`, `Disk Usage`를 확인했는가
- temp read/write가 실제로 보이는가
- estimate vs actual rows 차이가 큰가

### C. 구조적 개선 가능성 확인

- 인덱스로 정렬을 피할 수 있는가
- LIMIT/OFFSET을 keyset으로 바꿀 수 있는가
- projection을 줄일 수 있는가
- 조인 전에 줄일 수 있는 입력이 있는가
- summary table 또는 materialized view가 자연스러운가
- group key를 단순화할 수 있는가

### D. 운영 가드레일 확인

- `log_temp_files`가 설정되어 있는가
- `pg_stat_statements`로 temp-heavy query를 추적하는가
- temp 디스크 용량/사용률 알림이 있는가
- batch/reporting workload가 API와 격리되어 있는가

### E. 메모리 조정 판단

- 글로벌 상향이 정말 필요한가
- role/세션/트랜잭션 단위 상향으로 충분한가
- hash 문제라면 `hash_mem_multiplier`가 더 적합한가
- parallel query 증폭 효과를 고려했는가
- 동시 active heavy query 수를 추정했는가

이 체크리스트만 있어도 `work_mem`을 무작정 올리는 실수를 크게 줄일 수 있다.

---

## 실전 운영 기준: 어떤 상황에서 어떤 선택을 추천하는가

### 상황 1) 자주 호출되는 목록 API가 `ORDER BY ... LIMIT`에서 spill 난다

추천 우선순위:

1. 정렬을 인덱스로 대체 가능한지 확인
2. keyset pagination 검토
3. 반환 컬럼을 줄이고 covering 전략 검토
4. 그다음에만 소폭 메모리 조정 검토

이 경우 글로벌 `work_mem` 상향은 보통 후순위다.

### 상황 2) 운영자 리포트가 하루 몇 번 대형 sort/hash 때문에 느리다

추천 우선순위:

1. 세션/트랜잭션 단위 `SET LOCAL work_mem`
2. 필요 시 reporting role 분리
3. temp 사용량 모니터링
4. 요약 테이블 또는 사전 집계 가능성 검토

이 경우 범위 제한된 메모리 상향이 꽤 현실적이다.

### 상황 3) `HashAggregate`가 자주 spill 나며 dashboard가 흔들린다

추천 우선순위:

1. group cardinality 자체를 줄일 수 있는지 확인
2. raw log 직접 조회 대신 summary table 검토
3. 시간 범위 축소, drill-down 분리
4. 그 후에도 필요하면 메모리 조정

핵심은 대시보드 질의 구조를 바꾸는 것이다.

### 상황 4) `Hash Join` batch 수가 커지고 temp 파일이 늘어난다

추천 우선순위:

1. build side 실제 크기 확인
2. 통계 갱신 및 estimate 오차 확인
3. projection 축소
4. 조인 순서와 필터 푸시다운 검토
5. 이후 `hash_mem_multiplier` 또는 `work_mem` 검토

### 상황 5) 전체적으로 temp 사용이 많지만 특정 쿼리 하나로 설명되지 않는다

추천 우선순위:

1. `pg_stat_statements` 상위 temp-heavy query 파악
2. 시간대별 워크로드 분리
3. batch/reporting 격리
4. 글로벌 `work_mem` 소폭 상향 여부 검토
5. temp 디스크 가드레일 강화

이 경우 문제는 쿼리 하나가 아니라 workload mix일 가능성이 높다.

---

## 한 단계 더: 메모리 병목을 애플리케이션 설계 문제로 봐야 할 때

운영을 오래 보면 결국 깨닫게 된다.

많은 PostgreSQL 메모리 문제는 DB 파라미터 문제가 아니라 애플리케이션 질의 모델 문제다.

대표 사례가 이렇다.

- 대시보드가 원본 로그를 매번 직접 스캔한다.
- 정렬/집계를 위한 조회가 API hot path에 섞여 있다.
- 사용자 목록 페이지가 offset pagination으로 끝없이 뒤 페이지를 넘긴다.
- 검색/분석/운영 조회를 같은 OLTP DB에서 모두 해결하려 한다.
- 같은 차원 조인을 반복하지만 denormalized read model이 없다.

이런 구조에서는 메모리 튜닝이 끝이 없다.

왜냐하면 데이터가 늘수록,

- sort 범위 증가
- group cardinality 증가
- build side 증가
- temp 파일 증가

가 구조적으로 따라오기 때문이다.

이 단계에서는 다음 선택이 훨씬 효과적일 수 있다.

- summary table
- materialized view
- read replica 분리
- 검색 엔진/분석 엔진 분리
- CDC 기반 read model
- hot path 전용 API 테이블 설계

즉 메모리 튜닝은 중요하지만,

**메모리로 흡수해야 할 복잡도를 질의 모델에서 미리 낮추는 설계**가 더 오래 간다.

---

## 자주 묻는 판단 포인트

### Q1. spill이 조금이라도 보이면 무조건 튜닝해야 하나?

아니다.

- 빈도
- 중요도
- temp 디스크 압박
- hot path 영향

을 같이 봐야 한다.

드문 분석 쿼리의 작은 spill은 허용 가능한 비용일 수 있다.

### Q2. `work_mem`을 얼마나 올려야 하나?

정답 공식은 없다.

대신 아래 원칙이 실용적이다.

- 문제 쿼리의 spill 규모를 본다.
- 한 단계씩 소폭 올린다.
- 단건 쿼리뿐 아니라 동시성 시간대도 같이 본다.
- 전체 메모리 사용과 temp 감소 효과를 함께 확인한다.

즉 점프보다 실험적 상향이 낫다.

### Q3. Sort 문제에는 `hash_mem_multiplier`가 도움이 되나?

아니다.

이건 hash 계열에 적용되는 여유분이다.

Sort spill이면 대체로

- 정렬 회피
- 입력 축소
- `work_mem`

쪽 판단이 더 직접적이다.

### Q4. 인덱스만 늘리면 다 해결되지 않나?

아니다.

인덱스는 읽기 경로를 개선할 수 있지만,

- 쓰기 비용 증가
- 인덱스 유지 비용 증가
- vacuum 부담 증가
- HOT update 기회 감소

라는 반대 비용이 있다.

핵심은 “정렬 회피 가치가 큰 hot path”에만 정교하게 쓰는 것이다.

### Q5. temp 파일이 많으면 스토리지만 빠르면 되지 않나?

절반만 맞다.

빠른 스토리지는 spill 비용을 낮출 수 있다.

하지만 spill이 구조적으로 많다면,

- I/O 경쟁
- 디스크 용량 압박
- 지연 변동성
- 다른 쿼리 간 간섭

은 여전히 남는다.

빠른 디스크는 완충재이지, 구조 문제의 완전한 해법은 아니다.

---

## 운영 팀을 위한 최소 원칙 10가지

1. `work_mem`은 쿼리당이 아니라 operation당이라는 감각을 팀 공통 언어로 만든다.
2. Sort와 Hash를 구분해서 이야기한다.
3. temp 파일 로그를 남기고 상위 spill 쿼리를 정기적으로 본다.
4. `EXPLAIN (ANALYZE, BUFFERS)`를 기본 습관으로 둔다.
5. estimate/actual row 오차를 항상 같이 본다.
6. 글로벌 상향보다 세션/role 범위 제한 상향을 먼저 검토한다.
7. reporting/batch와 API를 가능하면 분리한다.
8. row width와 `SELECT *`를 가볍게 보지 않는다.
9. spill 제로보다 시스템 안정성을 우선한다.
10. 반복되는 메모리 이슈는 파라미터보다 read model/summary 설계에서 다시 본다.

이 열 가지를 지키면 메모리 튜닝이 훨씬 덜 감정적이고 더 재현 가능해진다.

---

## 한 줄 정리

**PostgreSQL의 `work_mem` 튜닝은 숫자 하나를 키우는 작업이 아니라, Sort·Hash·동시성·temp 파일·질의 구조를 함께 읽어 “어떤 연산을 메모리 안에 남길 것인가”를 결정하는 운영 설계다.**
