---
layout: post
title: "PostgreSQL 파티셔닝 실전: Range/List/Hash, Partition Pruning, Local Index, Retention으로 대용량 테이블을 운영 가능한 상태로 만드는 법"
date: 2026-04-25 11:40:00 +0900
categories: [sql]
tags: [study, sql, postgresql, partitioning, range-partitioning, partition-pruning, local-index, retention, operations, performance]
permalink: /sql/2026/04/25/study-postgresql-partitioning-pruning-local-index-retention.html
---

## 배경: 왜 PostgreSQL 테이블은 어느 순간부터 "한 테이블로 계속 버티는 비용"이 더 커질까

운영 중인 PostgreSQL에서 데이터가 계속 쌓이다 보면, 많은 팀이 비슷한 순서로 문제를 체감한다.

- 최근 7일 데이터만 보는 API인데도 전체 테이블 인덱스가 계속 비대해진다.
- 로그나 이벤트 이력 테이블에서 오래된 데이터를 지우는 작업이 배치 시간과 vacuum 비용을 크게 밀어 올린다.
- 같은 쿼리인데도 예전보다 plan time이 늘고, hot 데이터보다 cold 데이터 관리 비용이 더 크게 느껴진다.
- 월말이나 대량 적재 시점에 특정 인덱스와 autovacuum이 유독 흔들린다.
- 보관 정책 때문에 대량 `DELETE`를 돌렸더니 WAL, replica lag, bloat가 같이 튀어 오른다.
- 조회는 대부분 최근 구간인데, 인덱스는 전체 히스토리를 다 품고 있어서 메모리 locality가 점점 나빠진다.
- 백필이나 이관 작업을 하려는데 테이블이 너무 커서 단순 작업 하나도 위험해 보인다.

이때 팀이 가장 자주 떠올리는 해법이 파티셔닝이다.

그런데 여기서도 오해가 빠르게 생긴다.

- 파티셔닝하면 무조건 빨라진다.
- 테이블이 크기만 하면 파티셔닝이 정답이다.
- 일 단위로 잘게 쪼갤수록 pruning이 잘 되니까 좋다.
- 파티셔닝하면 인덱스와 vacuum 문제도 자동으로 정리된다.
- 파티셔닝은 사실상 샤딩 비슷한 것이니 확장성 문제도 같이 풀린다.

실무에서는 이 다섯 가지가 모두 위험한 단순화다.

PostgreSQL 파티셔닝의 본질은 "큰 테이블을 쪼개는 기능"이 아니라, 더 정확히는 아래 네 가지를 통제하기 위한 운영 도구에 가깝다.

1. **어떤 데이터만 읽고 어떤 데이터는 아예 읽지 않을지**를 pruning으로 통제한다.
2. **어떤 데이터 묶음을 한 번에 버리거나 아카이브할지**를 retention 단위로 통제한다.
3. **어떤 데이터 구간만 뜨겁게 관리하고 나머지는 차갑게 둘지**를 maintenance 경계로 통제한다.
4. **인덱스와 vacuum, 백필, 백업, 이관을 어느 단위로 다룰지**를 작업 단위로 통제한다.

즉 파티셔닝은 성능 옵션이라기보다 **데이터 수명주기와 운영 반경을 설계하는 기술**이다.

이 감각이 없으면 파티셔닝은 오히려 독이 된다.

- 파티션 개수만 늘고 plan overhead만 커진다.
- unique constraint 설계가 꼬인다.
- 잘못된 partition key 때문에 pruning은 거의 안 먹는다.
- hot partition 하나에 쓰기가 몰려 체감 이득이 작다.
- future partition 누락으로 insert 장애가 난다.
- default partition에 예상치 못한 데이터가 쌓여 정리 비용이 더 커진다.

오늘 글은 PostgreSQL declarative partitioning을 문법 소개가 아니라 **운영 가능한 대용량 테이블 설계** 관점에서 정리한다.

중급 이상 개발자를 기준으로 아래 질문에 답하는 것이 목표다.

- PostgreSQL 파티셔닝은 정확히 어떤 문제에서 효과가 크고, 어떤 문제에서는 별 도움이 없을까?
- Range, List, Hash를 어떤 기준으로 선택해야 할까?
- Partition pruning은 왜 어떤 쿼리에는 잘 먹고, 어떤 쿼리에는 거의 안 먹을까?
- 파티션 테이블의 인덱스와 unique constraint는 일반 테이블과 무엇이 다를까?
- Retention, attach/detach, future partition 자동화는 어떤 운영 기준으로 설계해야 할까?
- hot partition, skew, too many partitions 같은 함정은 어떻게 피해야 할까?
- 실무에서 자주 하는 실수와 체크리스트는 무엇일까?

핵심만 먼저 요약하면 이렇다.

1. 파티셔닝은 **테이블을 빠르게 만드는 마법**이 아니라, **읽지 않아도 되는 데이터와 건드리지 않아도 되는 데이터를 분리하는 기술**이다.
2. 가장 중요한 설계는 partition key와 interval이며, 이 둘은 쿼리 필터 축·보관 단위·쓰기 집중 구간과 맞아야 한다.
3. pruning이 제대로 먹지 않으면 파티셔닝 이득은 급격히 줄고, 관리 복잡도만 남는다.
4. PostgreSQL 파티션 인덱스는 기본적으로 각 파티션별 local index이므로, unique/primary key 설계가 일반 테이블과 다르다.
5. retention이 핵심인 테이블에서는 `DELETE`보다 `DETACH/DROP PARTITION`이 훨씬 강력한 운영 도구가 된다.
6. over-partitioning, default partition 방치, 자동 생성 미비, 파티션 키가 바뀌는 UPDATE는 흔한 사고 원인이다.
7. 좋은 파티셔닝은 데이터를 더 잘게 나누는 것이 아니라, **운영자가 더 적게 스캔하고 더 쉽게 버리고 더 좁게 고칠 수 있게 만드는 것**이다.

---

## 먼저 큰 그림: PostgreSQL 파티셔닝은 "분할"보다 "경계 설정"으로 이해해야 한다

많은 팀이 파티셔닝을 처음 검토할 때 출발점이 이렇다.

- 테이블이 너무 커졌다.
- 성능이 떨어지는 것 같다.
- 그러니 쪼개자.

방향은 틀리지 않을 수 있지만, 이 사고만으로는 부족하다.

왜냐하면 파티셔닝의 진짜 가치는 "크기를 줄인다"가 아니라 **서로 다른 성질의 데이터를 같은 유지보수 반경에 묶어 두지 않는다**는 데 있기 때문이다.

예를 들어 `event_logs` 테이블이 있다고 하자.

- 조회의 95%는 최근 3일 데이터만 본다.
- 보관은 180일 한다.
- 오래된 데이터는 거의 조회하지 않는다.
- 삭제는 매일 조금씩이 아니라 한 달 단위로 지워도 된다.

이 상황에서 하나의 거대한 테이블로 계속 운영하면 아래가 같이 묶인다.

- 지금 당장 자주 읽는 최근 데이터
- 거의 읽지 않는 6개월 전 데이터
- 현재 쓰기 경로가 매번 건드리는 최신 인덱스
- retention 때문에 언젠가 제거할 과거 데이터

즉 **뜨거운 데이터와 차가운 데이터를 같은 객체로 관리하는 비용**이 계속 누적된다.

파티셔닝은 여기서 경계를 세운다.

- 최근 월/일 파티션만 hot path가 된다.
- 오래된 파티션은 거의 불변 상태로 남는다.
- retention은 row 단위 삭제가 아니라 partition 단위 폐기로 바뀐다.
- 인덱스도 전체 이력이 아니라 partition별로 잘린다.
- 백필, detach, 압축, 아카이브를 데이터 구간 단위로 적용할 수 있다.

이걸 한 문장으로 줄이면 이렇다.

> **좋은 파티셔닝은 큰 테이블을 작게 만드는 것이 아니라, 서로 다른 수명과 접근 패턴을 가진 데이터를 다른 운영 경계로 분리하는 것이다.**

그래서 파티셔닝 도입 여부를 판단할 때도 첫 질문은 "이 테이블이 크냐"보다 아래에 가깝다.

- 대부분의 쿼리가 특정 시간/키 구간만 보는가?
- 오래된 데이터를 주기적으로 버리거나 아카이브해야 하는가?
- hot set과 cold set을 분리하면 메모리 locality, vacuum, index churn이 줄어드는가?
- 대량 삭제/이관/백필을 row 단위가 아니라 구간 단위로 처리하고 싶은가?

이 질문에 강하게 "예"가 나와야 파티셔닝이 빛난다.

반대로 아래에 가깝다면 기대 이득이 크지 않을 수 있다.

- 대부분의 조회가 전체 히스토리 랜덤 접근이다.
- 파티션 키로 쿼리를 거의 걸지 않는다.
- 보관 정책이 사실상 없다.
- 테이블은 크지만 hot/cold 경계가 약하다.
- non-partition key에 대한 전역 unique 보장이 매우 중요하다.

즉 파티셔닝은 용량 문제가 아니라 **접근 패턴 문제**다.

---

## 핵심 개념 1: partition key는 "자주 필터하는 컬럼" 하나만 보고 정하면 거의 항상 부족하다

파티셔닝에서 가장 중요한 결정은 partition key다.

그리고 가장 흔한 실패 원인도 partition key다.

실무에서 key를 고를 때 많은 팀이 딱 한 가지만 본다.

- 조회에서 자주 거는 조건인가?

물론 중요하다. 하지만 그것만 보면 안 된다. 실제로는 최소 다섯 가지를 같이 봐야 한다.

### 1) 쿼리의 대표 필터 축과 맞는가

가장 기본이다.

예를 들어 대부분의 쿼리가 아래처럼 들어온다면:

```sql
SELECT *
FROM event_logs
WHERE created_at >= now() - interval '7 days';
```

`created_at` 기반 range partitioning은 매우 자연스럽다.

반대로 대부분이 `tenant_id` 중심으로 조회되는데 시간 범위는 항상 넓다면, 시간 파티셔닝은 pruning 효과가 약할 수 있다.

### 2) retention 단위와 맞는가

파티셔닝의 강력한 이득 중 하나는 오래된 데이터를 partition 단위로 버릴 수 있다는 점이다.

따라서 아래 질문이 중요하다.

- 데이터를 언제 버리는가?
- 어떤 단위로 버리는가?
- 월 단위 보관인가, 일 단위 보관인가, tenant 단위 분리인가?

예를 들어 13개월 보관 후 월 단위 폐기가 자연스럽다면 월별 range partition이 잘 맞는다.

반대로 하루 단위 TTL이 필요한 고속 로그라면 일별 partition이 더 현실적일 수 있다.

### 3) 쓰기 집중 구간을 좁힐 수 있는가

파티셔닝은 읽기뿐 아니라 쓰기 hot set을 분리하는 데도 중요하다.

`created_at` 기준 range partition은 대부분의 신규 insert가 최신 파티션에 몰리게 만든다.

이건 장점이자 단점이다.

- 장점: 오래된 파티션은 거의 건드리지 않으니 vacuum과 인덱스 churn이 hot set에 집중된다.
- 단점: 최신 partition 하나가 지나치게 뜨거워지면 그 안의 인덱스와 autovacuum 압력이 한곳에 몰릴 수 있다.

그래서 high write workload에서는 단순히 pruning만이 아니라 **hot partition의 write profile**까지 봐야 한다.

### 4) partition key가 자주 바뀌지 않는가

이건 매우 중요하다.

PostgreSQL에서 partition key가 바뀌는 UPDATE는 단순 값 변경이 아니라, 사실상 **기존 partition에서 row를 빼고 다른 partition으로 옮기는 작업**이 된다.

따라서 아래 컬럼은 보통 파티션 키로 위험하다.

- `status`
- `updated_at`
- lifecycle에 따라 자주 변하는 상태 컬럼
- business correction이 빈번한 컬럼

보통 가장 안전한 축은 아래다.

- `created_at`
- `event_date`
- immutable한 business date
- 고정 tenant 구분값

즉 **움직이는 값보다 태어날 때 정해지고 잘 안 바뀌는 값**이 유리하다.

### 5) cardinality와 skew를 감당할 수 있는가

`tenant_id`는 자주 필터에 쓰이니 좋아 보일 수 있다.

하지만 tenant가 5만 개면 list partitioning은 곧 악몽이 된다.

- 파티션 수가 폭증한다.
- 신규 tenant 온보딩이 DDL 작업이 된다.
- small partition이 너무 많아져 planning과 maintenance 오버헤드가 커진다.
- tenant 간 데이터량 편차가 크면 몇몇 파티션만 과열된다.

즉 key는 자주 조회된다고 끝이 아니라, **얼마나 많은 partition을 만들게 되는지**와 **편향이 얼마나 큰지**도 같이 봐야 한다.

### 실무 기준: key 선택 전 반드시 적어야 할 질문

나는 파티셔닝 설계 문서를 쓸 때 아래 질문을 먼저 적는 편이다.

1. 가장 중요한 조회 5개는 어떤 조건으로 데이터를 자르는가?
2. retention/archival은 어떤 단위로 수행하고 싶은가?
3. 신규 row는 어느 구간으로 몰리는가?
4. partition key는 시간이 지나도 거의 변하지 않는가?
5. 예상 partition 수는 1년, 3년 뒤 얼마인가?
6. key가 skew를 만들면 감당 가능한가?

이 여섯 개 중 세 개 이상이 애매하면, 파티셔닝이 아니라 다른 해법이 먼저일 가능성이 높다.

---

## 핵심 개념 2: Range, List, Hash는 성격이 다르다 — 많이 쓰는 순서보다 "문제 형태"로 골라야 한다

PostgreSQL declarative partitioning에서 가장 흔한 선택지는 Range, List, Hash다.

세 방식은 비슷해 보이지만 잘 맞는 문제가 다르다.

### 1) Range Partitioning

가장 많이 쓰이는 방식이다.

대표 예시는 다음과 같다.

- `created_at` 월별/일별 파티션
- `business_date` 기준 정산 데이터
- 증가하는 `id` 범위 기준 분리

#### 잘 맞는 경우

- 쿼리가 시간 범위를 자주 건다.
- retention이 날짜 단위로 명확하다.
- 오래된 데이터를 구간 단위로 detach/drop하고 싶다.
- 신규 쓰기가 최신 구간에 집중되는 것이 자연스럽다.

#### 장점

- pruning 직관성이 높다.
- retention 운영이 쉽다.
- hot/cold 분리가 잘 된다.
- 최근 파티션 인덱스만 메모리에 잘 남도록 설계하기 쉽다.

#### 주의점

- interval을 너무 잘게 잡으면 partition 수가 급증한다.
- 최신 partition에 write hotspot이 몰릴 수 있다.
- 시간 조건을 함수로 감싸면 pruning이 약해질 수 있다.

실무에서 가장 안전한 기본값은 대개 range partitioning이다.

하지만 그 이유는 "언제나 최고라서"가 아니라, 많은 운영 데이터가 **시간 기반 lifecycle**을 가지기 때문이다.

### 2) List Partitioning

명시된 값 목록으로 나누는 방식이다.

대표 예시는 다음과 같다.

- `region in ('KR', 'JP', 'US')`
- `environment in ('prod', 'staging')`
- tenant 수가 아주 적고 경계가 안정적인 경우

#### 잘 맞는 경우

- 값의 개수가 적고 안정적이다.
- 특정 값 집합이 운영적으로 완전히 다른 수명/저장 정책을 가진다.
- 조회와 권한, 아카이브 정책이 값별로 분리된다.

#### 장점

- business boundary와 잘 맞으면 직관적이다.
- 특정 고객군이나 리전별 분리가 쉬울 수 있다.
- cold tenant, premium tenant 같은 운영 차등 정책을 적용하기 쉽다.

#### 주의점

- 값 수가 늘어나기 시작하면 금방 관리가 어려워진다.
- 신규 값이 들어올 때마다 partition 생성 자동화가 필요하다.
- 데이터 skew가 크면 일부 partition만 거대해진다.

List는 "분류 기준이 명확하다"는 이유만으로 선택하면 안 된다.

**값의 개수와 변화 속도**가 핵심이다.

### 3) Hash Partitioning

해시 결과에 따라 나누는 방식이다.

대표 예시는 다음과 같다.

- 특정 키에 쓰기가 지나치게 몰리는 경우
- range만으로는 hot partition이 너무 뜨거울 때 보조 분산이 필요한 경우
- retention보다는 write spread와 병렬성을 더 중요하게 볼 때

#### 잘 맞는 경우

- 특정 key 기반 접근이 잦다.
- 한 파티션으로 쓰기가 몰리는 것을 완화하고 싶다.
- retention drop보다 write distribution이 더 큰 목적이다.

#### 장점

- 데이터가 비교적 고르게 분산되기 쉽다.
- 특정 hot partition 완화에 도움이 될 수 있다.
- 병렬 작업 단위를 만들기 쉽다.

#### 주의점

- 시간 기반 retention과 궁합이 약하다.
- 운영자가 파티션의 의미를 직관적으로 이해하기 어렵다.
- "최근 7일" 같은 범위 pruning과 직접 연결되지 않는다.

Hash는 range보다 덜 직관적이지만, 정말 write skew가 심한 워크로드에서는 유의미하다.

다만 많은 팀이 hash를 너무 빨리 꺼낸다.

실무에서는 보통 아래 순서가 낫다.

1. 먼저 range로 hot/cold를 분리한다.
2. 그래도 hot partition write pressure가 감당 안 될 때만 subpartitioning이나 hash를 검토한다.

### 추천 사고법: partitioning 목적을 먼저 한 줄로 적는다

- retention이 핵심이면 range가 먼저다.
- business boundary 분리가 핵심이면 list를 검토한다.
- write spreading이 핵심이면 hash를 검토한다.

세 방식을 동시에 섞을 수도 있다.

예를 들어:

- 상위는 `created_at` range
- 하위는 `tenant_id` hash subpartition

하지만 이 설계는 강력한 대신 복잡도도 급증한다.

그래서 혼합 설계는 아래가 분명할 때만 권한다.

- 최신 파티션 write hotspot이 실제 병목이다.
- 단일 range partition 안에서 인덱스/쓰기 압력이 너무 높다.
- subpartition 증가 비용보다 얻는 이득이 크다.

복잡도는 항상 나중에 비용 청구서를 들고 온다.

---

## 핵심 개념 3: Partition Pruning은 파티셔닝의 심장이다 — pruning이 약하면 복잡도만 남는다

파티셔닝의 체감 이득 대부분은 pruning에서 나온다.

즉 쿼리를 실행할 때 PostgreSQL이 **관련 없는 partition을 아예 스캔 후보에서 제거**해야 한다.

이게 안 되면 무슨 일이 생길까?

- 테이블은 여러 개로 나뉘었지만 실제로는 대부분을 다 본다.
- 계획 수립 비용이 늘 수 있다.
- 인덱스도 파티션별로 나뉘었지만 전체 fan-out을 계속 감수한다.
- 관리 복잡도는 올라가는데 실행 이득은 작다.

그래서 실무에서 정말 중요한 질문은 이것이다.

> **우리 대표 쿼리가 partition key에 대해 planner가 이해할 수 있는 조건을 갖고 있는가?**

### pruning이 잘 먹는 조건의 공통점

가장 단순한 형태가 가장 강하다.

```sql
SELECT count(*)
FROM event_logs
WHERE created_at >= TIMESTAMPTZ '2026-04-01 00:00:00+09'
  AND created_at <  TIMESTAMPTZ '2026-05-01 00:00:00+09';
```

이런 형태는 range partitioning과 잘 맞는다.

- 경계가 분명하다.
- 상한/하한이 명시적이다.
- 타입도 애매하지 않다.

### pruning을 약하게 만드는 흔한 패턴

#### 1) partition key를 함수로 감싸기

```sql
SELECT *
FROM event_logs
WHERE date_trunc('day', created_at) = DATE '2026-04-25';
```

이 쿼리는 사람 눈에는 명확하지만, planner 입장에서는 partition bounds와 바로 맞물리는 형태가 아닐 수 있다.

보통은 아래처럼 쓰는 편이 안전하다.

```sql
SELECT *
FROM event_logs
WHERE created_at >= TIMESTAMPTZ '2026-04-25 00:00:00+09'
  AND created_at <  TIMESTAMPTZ '2026-04-26 00:00:00+09';
```

#### 2) 암묵적 캐스팅과 타입 불일치

`timestamp`, `timestamptz`, `date`가 섞이면 pruning이 기대와 다르게 약해질 수 있다.

특히 애플리케이션에서 문자열 파라미터를 던지고 DB가 애매하게 캐스팅하게 두면, plan이 불안정해질 수 있다.

#### 3) 넓은 OR 조건과 비정형 predicate

```sql
WHERE created_at >= now() - interval '7 days'
   OR tenant_id = 42
```

이런 구조는 pruning 이점을 흐릴 수 있다.

대표 쿼리는 partition key 조건이 **핵심 필터**로 남아야 한다.

#### 4) prepared statement와 generic plan에 과도하게 기대하기

애플리케이션 프레임워크가 prepared statement를 많이 쓰는 환경에서는, 파라미터 값이 확정된 뒤 실행 시점 pruning이 일부 도움을 줄 수 있어도 plan behavior가 항상 직관적이지는 않다.

그래서 대표 쿼리는 실제 실행 계획을 보고, "우리는 pruning이 될 것이다"가 아니라 **실제로 현재 버전과 드라이버 조합에서 pruning이 되는지** 확인해야 한다.

### 좋은 실무 습관: 파티셔닝 설계와 SQL 스타일을 같이 정한다

파티셔닝은 스키마만 바꾸고 끝나는 작업이 아니다.

애플리케이션 쿼리 스타일도 같이 맞춰야 한다.

- 날짜 범위는 상한/하한 형태로 쓴다.
- partition key에 불필요한 함수를 씌우지 않는다.
- API 레벨에서 시간대와 타입을 명확히 맞춘다.
- 대표 쿼리는 `EXPLAIN`으로 실제 partition fan-out을 확인한다.

좋은 팀은 파티션 설계 문서에 DDL만 적지 않는다.

- 어떤 쿼리 형태가 pruning-friendly인지
- 어떤 ORM 패턴은 피해야 하는지
- 어떤 API 파라미터는 범위 조건으로 바꿔야 하는지

까지 같이 적는다.

### partitionwise join/aggregate는 보너스이지 출발점이 아니다

같은 key 구조로 파티셔닝된 테이블끼리는 partitionwise join이나 aggregate가 이득을 줄 수 있다.

하지만 여기서 중요한 태도는 이것이다.

- 이 기능을 노리고 무리하게 파티셔닝하지 않는다.
- 먼저 pruning과 retention, maintenance 이득이 분명해야 한다.
- partitionwise execution은 추가 이득일 뿐, 기본 가치의 근거가 되면 안 된다.

파티셔닝의 1차 목적은 여전히 **읽지 않을 것을 버리는 것**이다.

---

## 핵심 개념 4: 파티션 인덱스는 local index다 — 그래서 unique/PK 설계가 일반 테이블과 달라진다

PostgreSQL 파티셔닝을 사용할 때 많은 개발자가 처음으로 크게 걸리는 지점이 인덱스와 unique constraint다.

왜냐하면 파티션 테이블은 논리적으로 하나처럼 보여도, 실제 저장과 인덱스는 기본적으로 **각 partition별로 나뉘어 있기 때문**이다.

### local index의 의미

부모 partitioned table에 인덱스를 선언하면, 개념적으로는 전체 계층에 적용되지만 실제 데이터는 각 partition의 child index에 들어간다.

이 구조의 장점은 분명하다.

- hot partition 인덱스가 전체 히스토리 인덱스보다 훨씬 작아질 수 있다.
- 오래된 partition 인덱스는 거의 변하지 않는다.
- partition별 rebuild, reindex, tablespace 조정 같은 운영 단위를 분리하기 쉽다.

하지만 제한도 생긴다.

### 가장 중요한 제한: 전역 unique 보장이 자유롭지 않다

PostgreSQL에서 partitioned table의 unique constraint 또는 primary key는 **partition key를 포함해야 하는 경우가 많다**.

직관은 간단하다.

- uniqueness 검사가 partition별 local index에서 일어난다.
- partition key를 모르면 여러 partition에 걸친 전역 중복을 한 번에 강하게 보장하기 어렵다.

예를 들어 아래는 위험하거나 불가능한 설계가 될 수 있다.

```sql
CREATE TABLE orders (
  order_id bigint not null,
  created_at timestamptz not null,
  ...
) PARTITION BY RANGE (created_at);

ALTER TABLE orders
  ADD PRIMARY KEY (order_id);
```

왜냐하면 `order_id`만으로는 서로 다른 `created_at` 파티션에 같은 값이 들어가는 것을 local index만으로 깔끔하게 막기 어렵기 때문이다.

반면 아래는 가능성이 높다.

```sql
ALTER TABLE orders
  ADD PRIMARY KEY (created_at, order_id);
```

물론 이 설계가 곧 애플리케이션 요구와 맞는다는 뜻은 아니다.

여기서 중요한 건 **비즈니스 키와 물리 키를 분리해서 생각해야 한다**는 점이다.

### 실무에서 자주 쓰는 해법

#### 1) 파티션 키를 포함한 복합 PK/UK로 간다

시간 기반 파티셔닝이면 아래처럼 간다.

- `(created_at, order_id)`
- `(business_date, tenant_id, invoice_id)`

장점은 DB 레벨 보장이 깔끔하다는 점이다.

단점은 모든 참조와 FK 설계가 더 무거워질 수 있다는 점이다.

#### 2) 전역 ID는 시퀀스/ULID/UUID로 애플리케이션에서 사실상 고유하게 만들고, DB PK는 파티션 친화적으로 둔다

실무에서는 이 방식이 꽤 흔하다.

- `id`는 sequence/UUID/ULID로 사실상 전역 고유하게 관리
- DB PK/UK는 partition key를 포함하거나 partition별 제약으로 둔다
- 다운스트림은 `id`를 business identifier처럼 쓴다

즉 "전역 고유성"을 반드시 local partitioned index 하나로만 풀려고 하지 않는다.

#### 3) 아예 파티셔닝 대상 테이블은 로그/이력/이벤트 중심으로 제한한다

이 접근도 강력하다.

파티셔닝이 가장 잘 맞는 테이블은 보통 아래다.

- append-heavy event log
- audit history
- CDC/raw ingest
- metrics/time-series성 데이터
- 주문 상태 이력, webhook delivery log

반대로 강한 전역 unique와 복잡한 FK가 핵심인 핵심 OLTP 엔터티 본체는 파티셔닝이 꼭 이득이 아닐 수 있다.

### 인덱스 설계도 달라져야 한다

파티셔닝 후에도 아무 생각 없이 인덱스를 이전과 똑같이 가져가면 기대 이득이 줄 수 있다.

예를 들어 월별 range partition이라면 대표 hot query가 이렇다고 하자.

```sql
SELECT *
FROM event_logs
WHERE tenant_id = $1
  AND created_at >= $2
  AND created_at < $3
ORDER BY created_at DESC
LIMIT 100;
```

이 경우 각 partition에 아래 인덱스가 더 자연스럽다.

```sql
CREATE INDEX ON event_logs (tenant_id, created_at DESC);
```

중요한 포인트는 이 인덱스가 "전체 히스토리 하나의 거대한 인덱스"가 아니라, 각 partition별로 작아진다는 점이다.

이게 바로 파티셔닝의 실질적 성능 이득 중 하나다.

- 최근 partition 인덱스는 메모리에 잘 남는다.
- 오래된 partition 인덱스는 거의 건드리지 않는다.
- vacuum/reindex도 partition 단위로 판단할 수 있다.

### 인덱스 운영에서 흔한 함정

- partition 수가 많은데 인덱스도 많아 DDL 비용이 커진다.
- 새 인덱스를 전체 계층에 넣을 때 lock과 적용 절차를 과소평가한다.
- 사용하지 않는 보조 인덱스를 방치해 hot partition write cost만 올린다.
- "어차피 파티셔닝했으니 인덱스는 덜 중요하다"고 오해한다.

파티셔닝은 인덱스를 없애는 기능이 아니다.

더 정확히는 **인덱스를 더 작은 운영 단위로 쪼개는 기능**이다.

---

## 핵심 개념 5: 좋은 파티셔닝의 절반은 retention 설계다 — `DELETE`에서 `DROP/DETACH`로 사고를 바꿔야 한다

파티셔닝이 가장 시원하게 빛나는 순간은 대개 retention에서 온다.

대량 `DELETE`는 PostgreSQL에서 늘 비싸다.

왜냐하면 단순히 row가 사라지는 것이 아니라 아래 비용이 따라오기 때문이다.

- row별 삭제 처리
- WAL 증가
- vacuum 부담
- dead tuple 정리 비용
- long transaction과 충돌할 가능성
- replica lag 증가

반면 파티셔닝이 있으면 오래된 데이터 제거를 **row 단위 작업이 아니라 구조 변경 작업**으로 바꿀 수 있다.

예를 들어 월별 partition이라면:

```sql
ALTER TABLE event_logs DETACH PARTITION event_logs_2025_10;
-- 백업/아카이브 후
DROP TABLE event_logs_2025_10;
```

이 방식의 장점은 엄청나다.

- 수억 row를 지워도 row-by-row delete가 아니다.
- vacuum overhead를 크게 줄일 수 있다.
- 아카이브, 덤프, 저가 스토리지 이동 같은 후처리가 쉬워진다.
- 운영 절차가 "데이터 삭제 작업"이 아니라 "파티션 수명주기 관리"로 단순화된다.

### retention 단위를 먼저 정해야 partition interval도 정해진다

파티셔닝을 설계할 때 많은 팀이 일/주/월 partition 중 무엇이 빠른지부터 묻는다.

실무에서는 이 질문보다 아래가 먼저다.

- 얼마 동안 보관하는가?
- 어떤 단위로 버리고 싶은가?
- 대표 조회는 어느 구간을 자주 읽는가?
- 미래 파티션을 몇 개까지 미리 만들고 싶은가?

예를 들어:

- 90일 보관, 최근 1~7일 조회 중심 → 일별 partition이 자연스러울 수 있음
- 13개월 보관, 최근 1~3개월 집계 중심 → 월별 partition이 더 안정적일 수 있음
- 7년 보관, 월별 폐기/월별 결산 → 월별 또는 분기별도 고려 가능

핵심은 **drop unit = retention unit = 대표 운영 단위**가 되면 좋다는 것이다.

### future partition 자동화는 필수다

파티셔닝 운영에서 가장 허무한 장애 중 하나는 이것이다.

- 새 달이 왔는데 다음 partition이 없다.
- insert가 parent에 라우팅되지 못한다.
- 배치/서비스가 갑자기 에러를 내기 시작한다.

즉 partitioning은 DDL 한 번으로 끝나는 기능이 아니라 **달력과 함께 움직이는 자동화 작업**이다.

최소한 아래는 필요하다.

- 다음 N개 파티션 사전 생성
- 누락 감지 알람
- retention 대상 파티션 목록 점검
- default partition 모니터링

### default partition은 안전망이지만 쓰레기통이 되기 쉽다

default partition은 예상 못한 키 값이 들어와도 insert를 막지 않는 안전망이 될 수 있다.

하지만 운영에서는 자주 이렇게 된다.

- 파티션 자동 생성이 실패했다.
- 앱이 이상한 날짜 값을 넣었다.
- time zone 버그로 경계 밖 데이터가 들어왔다.
- 모든 예외 row가 default partition에 쌓였다.

그리고 몇 달 뒤,

- pruning이 흐려지고
- attach 작업이 번거로워지고
- default 정리 작업이 큰 비용으로 돌아온다.

그래서 default partition을 둘 거라면 반드시 같이 있어야 한다.

- row count 모니터링
- 기대 기준치 초과 알람
- 정리 runbook
- 왜 default로 들어왔는지 원인 추적 로깅

default는 완충장치지, 영구 저장소가 아니다.

---

## 핵심 개념 6: hot partition은 파티셔닝의 장점이자 병목 지점이다 — "최근 구간만 뜨겁다"를 어떻게 다룰지 정해야 한다

시간 기반 range partitioning을 하면 대부분의 쓰기는 최신 partition에 몰린다.

이건 나쁜 일이 아니다.

오히려 파티셔닝의 중요한 장점이다.

- hot write가 최신 partition에만 집중된다.
- 오래된 partition은 read mostly 혹은 frozen 상태가 된다.
- vacuum과 autovacuum 판단도 hot/cold를 구분해 할 수 있다.

하지만 쓰기량이 매우 큰 시스템에서는 최신 partition 하나가 다시 문제의 중심이 된다.

예를 들어 다음 현상이 생길 수 있다.

- 최신 partition 인덱스 페이지에 latch contention이 두드러진다.
- autovacuum이 hot partition에서만 계속 바쁘다.
- `updated_at` 중심 secondary index가 write amplification을 만든다.
- insert burst가 몰릴 때 특정 partition만 checkpoint pressure를 크게 받는다.

이때 많은 팀이 바로 subpartitioning으로 간다.

하지만 먼저 해야 할 것은 더 단순한 점검이다.

### 1) 정말 partition이 아니라 인덱스 설계 문제는 아닌가

hot partition이 느린 이유가 종종 아래에 있다.

- 불필요한 secondary index가 많다.
- fillfactor, HOT-friendly 설계가 부족하다.
- 자주 바뀌는 컬럼 인덱스가 write cost를 끌어올린다.
- `updated_at` 정렬 요구 때문에 너무 비싼 인덱스를 유지한다.

즉 최신 partition 병목이 항상 "파티션이 하나라서" 생기는 것은 아니다.

### 2) partition interval이 너무 넓지는 않은가

월별 파티션 하나가 지나치게 크고 뜨겁다면,

- 월별 → 일별로 더 잘게 나누는 쪽이 나을 수 있다.

다만 이 변경은 partition 수 증가라는 비용을 가져온다.

그래서 단순히 interval을 쪼개기보다 아래를 같이 본다.

- 현재 월별 파티션 크기와 index size
- hot query가 실제 보는 범위
- retention drop 단위
- 예상 파티션 수 증가 후 planning 비용

### 3) 정말 필요할 때만 hash subpartition을 검토한다

아주 높은 write throughput에서 최신 범위를 다시 hash로 나누는 설계는 의미가 있을 수 있다.

예를 들어:

- 상위: `created_at` 월별 range
- 하위: `tenant_id` hash 8-way

이 구조는 최신 월 안에서 쓰기와 인덱스를 더 분산시킬 수 있다.

하지만 대가도 크다.

- 파티션 개수가 급증한다.
- DDL 자동화가 복잡해진다.
- 모니터링과 장애 대응 포인트가 늘어난다.
- 쿼리/운영자가 구조를 이해하기 더 어려워진다.

그래서 나는 아래일 때만 hash subpartition을 진지하게 검토한다.

- hot partition 하나의 write/index pressure가 분명한 병목이다.
- 단순 인덱스 정리와 interval 조정으로 해결되지 않는다.
- 파티션 수 증가를 감당할 운영 자동화가 있다.

파티셔닝의 목적은 복잡한 구조를 자랑하는 것이 아니다.

**문제를 해결하는 최소 구조를 택하는 것**이다.

---

## 핵심 개념 7: 파티션 유지보수는 `CREATE PARTITION`보다 `ATTACH/DETACH` 플레이북이 더 중요하다

파티셔닝을 문법 수준에서만 보면 부모 테이블 만들고 child partition 몇 개 만드는 것으로 끝나 보인다.

하지만 운영에서는 그 이후가 더 중요하다.

- 미래 partition을 미리 만들 것인가
- 외부에서 적재한 테이블을 attach할 것인가
- 오래된 partition을 바로 drop할 것인가, 먼저 detach 후 검증/백업할 것인가
- default partition에 잘못 들어간 데이터를 어떻게 복구할 것인가

즉 파티셔닝의 실전 난이도는 조회 성능보다 **구조를 안전하게 바꾸고 유지하는 절차**에서 갈리는 경우가 많다.

### `CREATE TABLE ... PARTITION OF`는 가장 단순하지만, 항상 가장 좋은 운영 방식은 아니다

빈 partition을 사전에 만들어 둘 때는 가장 직관적이다.

```sql
CREATE TABLE app_event_logs_2026_06
  PARTITION OF app_event_logs
  FOR VALUES FROM ('2026-06-01 00:00:00+09') TO ('2026-07-01 00:00:00+09');
```

장점은 단순하다.

- 정의가 명확하다.
- 라우팅이 즉시 가능하다.
- 자동화 스크립트 작성이 쉽다.

하지만 아래 상황에서는 다른 접근이 더 낫다.

- 이미 별도 테이블에 데이터를 먼저 적재하고 싶다.
- bulk load 후 검증한 다음 서비스 트래픽에 노출하고 싶다.
- attach 시점을 운영자가 통제하고 싶다.
- 생성 시점 lock보다 attach 시점 lock이 더 유리하다.

### 사전 적재 후 `ATTACH PARTITION` 패턴은 대량 이관과 백필에서 매우 유용하다

실무에서 자주 쓰는 흐름은 이렇다.

1. 부모 스키마와 같은 standalone table 생성
2. 해당 테이블에 정확한 범위의 데이터 적재
3. partition bound와 동일한 `CHECK` 제약 추가
4. 검증 후 `ATTACH PARTITION`

예를 들면:

```sql
CREATE TABLE app_event_logs_2026_06_staging
  (LIKE app_event_logs INCLUDING DEFAULTS INCLUDING CONSTRAINTS);

ALTER TABLE app_event_logs_2026_06_staging
  ADD CONSTRAINT app_event_logs_2026_06_check
  CHECK (
    created_at >= TIMESTAMPTZ '2026-06-01 00:00:00+09'
    AND created_at < TIMESTAMPTZ '2026-07-01 00:00:00+09'
  );

-- bulk load / backfill / validation

ALTER TABLE app_event_logs
  ATTACH PARTITION app_event_logs_2026_06_staging
  FOR VALUES FROM ('2026-06-01 00:00:00+09') TO ('2026-07-01 00:00:00+09');
```

이 패턴이 좋은 이유는 명확하다.

- 서비스 테이블에 바로 대량 적재하지 않아도 된다.
- 검증 실패 시 attach 전 단계에서 되돌리기 쉽다.
- 운영자는 cutover 시점만 짧게 관리하면 된다.

특히 대용량 historical backfill에서는 이 방식이 훨씬 예측 가능하다.

### `CHECK` 제약을 먼저 맞춰 두는 이유

이건 꽤 실무적이면서 중요한 디테일이다.

attach할 테이블에 partition bound와 일치하는 `CHECK` 제약을 미리 두면, PostgreSQL이 attach 과정에서 "이 테이블이 정말 해당 범위만 담고 있는지" 검증할 때 불필요한 큰 스캔을 피하는 데 도움이 된다.

반대로 이 준비가 없으면 attach 과정 자체가 예상보다 무거워질 수 있다.

즉 attach 패턴의 핵심은 단순 문법이 아니라 아래다.

- attach 전에 범위를 명시적으로 봉인한다.
- 데이터 검증과 구조 전환을 분리한다.
- cutover 시간을 짧게 만든다.

### `DETACH PARTITION`은 단순 삭제 전 단계가 아니라 운영 완충지대다

오래된 데이터를 바로 `DROP TABLE` 해도 되는 환경이라면 단순하다.

하지만 실제 운영에서는 아래 요구가 흔하다.

- 삭제 전에 한 번 더 백업하고 싶다.
- 저가 스토리지로 내보내고 싶다.
- 법무/감사 요청 때문에 잠시 더 보관하고 싶다.
- 배포 당일에는 구조만 분리하고 삭제는 다음 창에 하고 싶다.

이때 `DETACH PARTITION`은 매우 유용하다.

```sql
ALTER TABLE app_event_logs
  DETACH PARTITION app_event_logs_2025_03;
```

그러면 이 파티션은 더 이상 부모 테이블 질의 대상은 아니지만, 독립 테이블로 남아 후속 작업을 수행할 수 있다.

실무에서는 이게 중요하다.

- 쿼리 대상에서 먼저 빼서 성능/정합성 영향을 줄이고
- 데이터 보존 여부는 이후 판단할 수 있기 때문이다.

### default partition이 있는 경우 attach는 더 조심해야 한다

default partition을 운영하고 있다면, 새 partition을 attach할 때 default에 "사실 이 새 파티션으로 가야 했던 row"가 섞여 있지 않은지 확인해야 한다.

이 검증을 방치하면 attach가 예상보다 무거워지거나, 정리 작업이 뒤늦게 더 어려워질 수 있다.

그래서 default partition을 두는 팀은 attach runbook에 보통 이런 항목을 같이 넣는다.

- 해당 범위 row가 default에 존재하는지 확인
- 존재한다면 먼저 이동 또는 정리
- attach 후 default row count 재검증

default는 편하지만, attach/detach 복잡도를 분명히 올린다.

### 파티션 유지보수의 핵심은 "구조 전환 시간을 짧게, 검증 시간을 길게"다

이 원칙을 기억하면 대부분의 운영 절차가 정리된다.

- 검증은 attach 전 별도 테이블에서 오래 해도 된다.
- 구조 전환은 짧고 예측 가능해야 한다.
- 삭제는 detach 후 나중에 해도 된다.
- default 정리는 평소에 자주 해야 한다.

즉 파티셔닝 운영은 단순 DDL 나열이 아니라, **데이터 검증과 구조 반영을 분리하는 기술**이다.

---

## 핵심 개념 8: 일반 테이블을 파티션 테이블로 옮기는 일은 단순 ALTER가 아니라 별도 마이그레이션 프로젝트다

PostgreSQL에서 이미 큰 일반 테이블을 운영 중이라면, 많은 팀이 자연스럽게 이렇게 생각한다.

- `ALTER TABLE ... PARTITION BY ...` 같은 식으로 바꾸면 되지 않을까?

하지만 실무에서는 그렇게 단순하지 않다.

일반 테이블을 파티션 테이블로 바꾸는 작업은 대개 **새 partitioned table을 만들고, 데이터를 이관하고, 읽기/쓰기 경로를 전환하는 프로젝트**에 가깝다.

이걸 가볍게 보면 거의 항상 일정과 위험을 과소평가하게 된다.

### 왜 이 작업이 생각보다 큰가

기존 단일 테이블에는 이미 아래가 걸려 있는 경우가 많다.

- PK/UK/FK
- trigger
- 배치 쿼리
- ad hoc 분석 쿼리
- ORM 매핑
- CDC 대상 여부
- 백업/복구 runbook

즉 "저장 방식만 바꾸면 된다"가 아니라, 테이블을 둘러싼 계약 전체를 다시 확인해야 한다.

### 현실적인 마이그레이션 기본 시퀀스

아래 흐름이 가장 많이 재사용된다.

#### 1) 새 partitioned table 생성

- 최종 스키마 확정
- partition key 및 interval 결정
- 필요한 파티션 미리 생성
- 부모/자식 인덱스 전략 문서화

#### 2) 과거 데이터 범위별 backfill

보통 시간 구간으로 잘라 진행한다.

```sql
INSERT INTO orders_p (id, tenant_id, status, amount, created_at, updated_at)
SELECT id, tenant_id, status, amount, created_at, updated_at
FROM orders
WHERE created_at >= TIMESTAMPTZ '2025-01-01 00:00:00+09'
  AND created_at <  TIMESTAMPTZ '2025-02-01 00:00:00+09';
```

이 작업은 단순 INSERT가 아니라, 실제로는 아래를 함께 봐야 한다.

- chunk size
- WAL 증가량
- replica lag
- lock 대기
- backfill 도중 신규 쓰기 처리 방식

#### 3) 신규 쓰기 동기화 전략 결정

backfill이 끝날 때까지도 원본 테이블에는 쓰기가 계속 들어온다.

그래서 보통 세 가지 중 하나를 택한다.

- 짧은 정지 창을 두고 마지막 증분만 이관 후 cutover
- 애플리케이션 dual write
- trigger 또는 CDC 기반 동기화

정답은 workload와 시스템 성숙도에 따라 다르다.

하지만 원칙은 같다.

> **과거 데이터 이관과 현재 쓰기 동기화를 분리해서 설계해야 한다.**

둘을 한 단계로 뭉치면 실패 원인 분석도 어려워진다.

#### 4) 검증 쿼리 준비

아래 검증은 필수에 가깝다.

- 범위별 row count 비교
- key 샘플 비교
- 집계 값 비교
- 최대/최소 timestamp 비교
- 누락/중복 row 확인

예를 들어:

```sql
SELECT date_trunc('day', created_at) AS d, count(*)
FROM orders
GROUP BY 1
ORDER BY 1;

SELECT date_trunc('day', created_at) AS d, count(*)
FROM orders_p
GROUP BY 1
ORDER BY 1;
```

혹은 더 직접적으로:

```sql
SELECT id
FROM orders
EXCEPT
SELECT id
FROM orders_p;
```

물론 대용량에서는 샘플링·집계·범위 검증을 조합하는 편이 현실적이다.

#### 5) 읽기/쓰기 cutover

cutover 시점에는 애플리케이션이 어떤 이름을 바라보는지 정리해야 한다.

- rename 전환
- view 전환
- 코드 배포와 함께 테이블 대상 변경
- 롤백 시 되돌리는 방법

테이블 이름 하나 바꾸는 것처럼 보여도, 운영에서는 이 순간이 가장 민감하다.

### migration에서 가장 흔한 과소평가 포인트

#### 1) 인덱스/제약 재생성 시간

데이터 이관보다 인덱스 생성과 검증이 더 오래 걸릴 수 있다.

#### 2) FK 영향 범위

상위/하위 테이블이 많이 연결돼 있으면 cutover 설계가 훨씬 복잡해진다.

#### 3) analytics 쿼리와 ad hoc SQL

앱 코드만 바꾸면 끝이라고 생각하지만, 운영 쿼리나 배치 쿼리가 기존 단일 테이블을 가정하고 있을 수 있다.

#### 4) CDC/복제/백업 시스템

Debezium, logical replication, 백업 스크립트가 테이블 구조 변화에 영향을 받을 수 있다.

즉 partition migration은 storage change이면서 동시에 ecosystem change다.

### 추천 기준: 파티션 마이그레이션은 작은 rehearsal 없이 본 작업부터 하지 않는다

가능하면 아래를 먼저 해보는 편이 좋다.

- 가장 오래된 1개 월 범위만 샘플로 이관
- 실제 backfill 속도 측정
- WAL/replica lag 측정
- 검증 쿼리 템플릿 확정
- cutover dry-run 수행

이 rehearsal이 없으면 대부분의 리스크는 추측 수준에 머문다.

---

## 핵심 개념 9: 파티셔닝 전에도 먼저 검토할 대안이 있다 — 모든 대용량 테이블이 파티셔닝부터 필요한 것은 아니다

파티셔닝이 강력한 건 맞다.

하지만 실제로는 파티셔닝 없이도 pain을 충분히 줄일 수 있는 경우가 적지 않다.

이걸 구분하지 못하면, 파티셔닝이 가장 비싼 해법이 될 수 있다.

### 대안 1: BRIN 인덱스

테이블이 시간 순으로 거의 append되고, 대표 조회가 넓은 시간 범위를 훑는다면 BRIN 인덱스가 꽤 좋은 가성비를 낼 수 있다.

이 경우 다음 장점이 있다.

- 인덱스 크기가 매우 작다.
- 대용량 append-only 테이블에 잘 맞는다.
- 파티셔닝보다 구조 변경 비용이 작다.

물론 retention drop 같은 lifecycle 이득은 없다.

즉 읽기 접근을 조금 개선하는 것이 목표라면, BRIN이 먼저일 수도 있다.

### 대안 2: Partial Index + Archive Table 분리

전체를 파티셔닝하지 않고, 최근 데이터만 빠르게 읽도록 partial index를 두고 오래된 데이터는 별도 archive table로 옮기는 전략도 있다.

예를 들어:

```sql
CREATE INDEX idx_orders_recent_tenant_created_at
ON orders (tenant_id, created_at DESC)
WHERE created_at >= now() - interval '90 days';
```

이런 접근은 다음 상황에서 현실적이다.

- 대표 조회가 항상 recent window에 집중된다.
- 오래된 데이터는 거의 조회하지 않는다.
- 전체 구조를 partitioning으로 바꾸기엔 비용이 크다.

물론 이 방식은 retention, 쿼리 라우팅, archive 조회 경로를 별도로 관리해야 한다.

### 대안 3: 단순 테이블 로테이션

아예 애플리케이션 레벨에서

- `events_current`
- `events_archive_2025`

같은 방식으로 분리하고, 읽기 대상도 명시적으로 나누는 전략이 더 단순한 경우도 있다.

이건 declarative partitioning만큼 우아하지 않을 수 있지만,

- 시스템이 단순하고
- 운영팀이 적고
- 조회 경로가 제한적이라면

오히려 더 현실적인 선택일 수 있다.

### 대안 4: 쿼리/인덱스 튜닝이 먼저인 경우

실제로 느린 이유가 파티션 부재가 아니라 아래일 수도 있다.

- 잘못된 composite index 순서
- 높은 업데이트 churn으로 인한 bloat
- 불필요한 select list
- 잘못된 join order
- 너무 넓은 JSON 연산

이 경우 파티셔닝을 도입해도 체감 이득이 작다.

그래서 나는 파티셔닝을 검토할 때 항상 이 질문을 같이 한다.

> 지금의 pain은 정말 lifecycle과 scan scope 문제인가, 아니면 여전히 query/index design 문제인가?

이 질문이 흐리면, 파티셔닝은 종종 너무 큰 해머가 된다.

---

## 실무 예시 1: 이벤트 로그 테이블을 월별 Range Partition으로 운영하기

가장 전형적인 예시는 append-heavy event log다.

요구사항을 가정해 보자.

- 하루 수천만 건 적재
- 조회의 90%는 최근 30일 이내
- 보관 기간은 13개월
- 삭제는 월 단위면 충분
- 테넌트별 최근 이벤트 조회가 많음

이 경우 월별 range partition은 매우 자연스럽다.

### 1) 부모 테이블 정의

```sql
CREATE TABLE app_event_logs (
  id bigserial not null,
  tenant_id bigint not null,
  event_type text not null,
  actor_id bigint,
  payload jsonb not null,
  created_at timestamptz not null,
  PRIMARY KEY (created_at, id)
) PARTITION BY RANGE (created_at);
```

여기서 눈여겨볼 점은 두 가지다.

- partition key인 `created_at`을 PK에 포함했다.
- `id` 하나만 PK로 고집하지 않았다.

이런 테이블에서는 `id`의 전역 uniqueness를 애플리케이션/시퀀스가 사실상 보장하고, DB 물리 제약은 partition 친화적으로 가져가는 편이 낫다.

### 2) 월별 파티션 생성

```sql
CREATE TABLE app_event_logs_2026_04
  PARTITION OF app_event_logs
  FOR VALUES FROM ('2026-04-01 00:00:00+09') TO ('2026-05-01 00:00:00+09');

CREATE TABLE app_event_logs_2026_05
  PARTITION OF app_event_logs
  FOR VALUES FROM ('2026-05-01 00:00:00+09') TO ('2026-06-01 00:00:00+09');
```

### 3) 대표 조회에 맞는 인덱스

```sql
CREATE INDEX ON app_event_logs (tenant_id, created_at DESC);
CREATE INDEX ON app_event_logs (event_type, created_at DESC);
```

부모에 생성하면 각 파티션에 대응 인덱스가 생긴다.

물론 실제 운영에서는 인덱스 추가 절차와 lock 영향도를 따로 검토해야 한다.

### 4) pruning-friendly 조회 패턴

```sql
SELECT id, event_type, actor_id, created_at
FROM app_event_logs
WHERE tenant_id = 42
  AND created_at >= TIMESTAMPTZ '2026-04-20 00:00:00+09'
  AND created_at <  TIMESTAMPTZ '2026-04-27 00:00:00+09'
ORDER BY created_at DESC
LIMIT 100;
```

이 쿼리는 최근 일부 월/일 파티션만 읽게 만들기 쉽다.

### 5) retention 운영

13개월 보관이라면 월초 배치에서 이런 절차를 둘 수 있다.

```sql
ALTER TABLE app_event_logs DETACH PARTITION app_event_logs_2025_03;
-- 백업 또는 외부 저장 후
DROP TABLE app_event_logs_2025_03;
```

이 방식은 대량 `DELETE`보다 운영 안정성이 훨씬 좋다.

### 이 설계가 특히 좋은 이유

- hot data는 최근 파티션에 몰린다.
- 오래된 파티션은 거의 불변이다.
- retention이 매우 단순해진다.
- 인덱스가 기간별로 작아져 메모리 효율이 좋아진다.

### 이 설계가 안 맞는 경우

- 대부분의 조회가 `id = ?` 같은 전기간 랜덤 point lookup뿐이다.
- 월별 보관 폐기가 실제 필요 없다.
- created_at 범위를 거의 안 건다.

즉 같은 로그 테이블이어도, 실제 접근 패턴이 다르면 파티셔닝 가치도 달라진다.

---

## 실무 예시 2: 멀티테넌트 webhook delivery 로그 — 왜 tenant list partition보다 time range가 먼저인가

이번에는 조금 더 현실적인 SaaS 운영 예시를 보자.

요구사항은 이렇다.

- `webhook_delivery_logs` 테이블이 매우 빠르게 증가한다.
- API 조회는 대체로 특정 tenant의 최근 7일 실패 건을 본다.
- 운영팀은 180일 보관 후 삭제하고 싶다.
- tenant 수는 수천 개고 상위 10개 tenant가 트래픽 대부분을 차지한다.

처음 보면 `tenant_id`로 list partitioning 하고 싶을 수 있다.

하지만 이 설계는 대개 좋지 않다.

- tenant 수가 많다.
- 신규 tenant 생성이 DDL 이벤트가 된다.
- skew가 심하다.
- retention drop이 tenant 기준으로는 맞지 않는다.

이 경우 먼저 고려할 것은 보통 아래다.

### 1단계: `created_at` 기준 range partition

```sql
CREATE TABLE webhook_delivery_logs (
  id bigserial not null,
  tenant_id bigint not null,
  endpoint_id bigint not null,
  delivery_status text not null,
  response_code integer,
  error_message text,
  created_at timestamptz not null,
  payload jsonb not null,
  PRIMARY KEY (created_at, id)
) PARTITION BY RANGE (created_at);
```

### 2단계: 각 파티션에 tenant 중심 보조 인덱스

```sql
CREATE INDEX ON webhook_delivery_logs (tenant_id, delivery_status, created_at DESC);
CREATE INDEX ON webhook_delivery_logs (endpoint_id, created_at DESC);
```

### 3단계: 대표 조회는 범위를 먼저 고정

```sql
SELECT id, endpoint_id, response_code, error_message, created_at
FROM webhook_delivery_logs
WHERE tenant_id = $1
  AND delivery_status = 'FAILED'
  AND created_at >= $2
  AND created_at <  $3
ORDER BY created_at DESC
LIMIT 200;
```

이 구조의 핵심은 tenant를 파티션 키로 쓰지 않고도, 최근 구간만 강하게 pruning하면서 tenant 보조 인덱스로 빠르게 찾는다는 점이다.

### 그러면 언제 tenant hash subpartition을 고민할까?

아래 조건이 모두 강할 때다.

- 최신 partition 하나의 쓰기량이 정말 너무 크다.
- 상위 tenant 몇 개가 최신 partition write pressure를 결정한다.
- 단순 보조 인덱스 조정으로는 버티기 어렵다.
- 운영 자동화가 subpartition 복잡도를 감당할 수 있다.

즉 **먼저 time range로 lifecycle을 잡고, 정말 필요할 때만 hash로 hot set을 더 쪼개는 것**이 일반적으로 더 안전하다.

많은 팀이 여기서 배워야 할 포인트는 이것이다.

> 자주 필터되는 컬럼이 곧 partition key는 아니다. partition key는 pruning, retention, maintenance, skew를 함께 고려한 운영 키다.

---

## 실무 예시 3: 단일 `audit_history` 테이블을 월별 파티션 구조로 옮길 때의 현실적인 cutover 시나리오

이번에는 새로 만드는 테이블이 아니라, 이미 커져버린 테이블을 옮기는 장면을 보자.

가정은 이렇다.

- `audit_history` 단일 테이블이 3TB까지 커졌다.
- 조회의 대부분은 최근 2개월이다.
- 보관 기간은 24개월이다.
- 월별 삭제가 필요하지만 현재는 대량 `DELETE` 때문에 매번 운영 부담이 크다.
- 애플리케이션은 계속 쓰기 중이라 장시간 정지는 어렵다.

이 경우 파티셔닝 자체보다 **마이그레이션 절차**가 훨씬 중요하다.

### 1단계: 새 partitioned table을 먼저 완성한다

```sql
CREATE TABLE audit_history_p (
  id bigint not null,
  tenant_id bigint not null,
  entity_type text not null,
  entity_id bigint not null,
  action text not null,
  actor_id bigint,
  payload jsonb,
  created_at timestamptz not null,
  PRIMARY KEY (created_at, id)
) PARTITION BY RANGE (created_at);
```

그리고 과거 24개월 + 미래 3개월 정도 partition을 미리 만든다.

이 단계에서 끝내야 할 것은 아래다.

- 인덱스 전략 확정
- retention job 초안 작성
- default partition 유무 결정
- 모니터링 항목 추가

즉 새 구조는 cutover 전에 이미 운영 준비까지 끝나 있어야 한다.

### 2단계: 오래된 구간부터 backfill한다

최근 데이터부터 건드리면 현재 쓰기와 충돌하기 쉽다.

보통은 아래처럼 오래된 월부터 순차 이관하는 편이 안정적이다.

```sql
INSERT INTO audit_history_p (id, tenant_id, entity_type, entity_id, action, actor_id, payload, created_at)
SELECT id, tenant_id, entity_type, entity_id, action, actor_id, payload, created_at
FROM audit_history
WHERE created_at >= TIMESTAMPTZ '2024-04-01 00:00:00+09'
  AND created_at <  TIMESTAMPTZ '2024-05-01 00:00:00+09';
```

이 과정을 한 달 단위로 쪼개면 좋은 이유는 다음과 같다.

- 검증도 같은 단위로 하기 쉽다.
- 실패 시 재시도 범위가 작다.
- WAL/replica 영향량을 월 단위로 측정할 수 있다.
- 이후 retention 단위와도 일치한다.

### 3단계: 최근 구간은 dual write 또는 증분 catch-up을 붙인다

과거 데이터 백필이 끝나도, 최근 데이터는 계속 변한다.

그래서 보통 두 방식 중 하나를 택한다.

#### 방식 A: 애플리케이션 dual write

- 일정 기간 동안 기존 `audit_history`와 `audit_history_p`에 동시에 기록
- 읽기는 아직 구 테이블 유지
- row count와 샘플 비교로 안정성 확인
- 충분히 맞으면 읽기 전환

장점:

- 동기화 상태를 명시적으로 통제하기 쉽다.
- cutover 시점 차이를 줄일 수 있다.

단점:

- 애플리케이션 코드가 더 복잡해진다.
- 실패 처리 정책을 별도로 설계해야 한다.

#### 방식 B: 짧은 정지 창 + 마지막 증분 이관

- 과거 구간은 미리 다 backfill
- cutover 직전 쓰기를 잠시 멈춤
- 마지막 최근 구간 증분만 이관
- 이름 전환 후 재개

장점:

- 애플리케이션 코드 변경이 적다.

단점:

- 정지 시간이 허용돼야 한다.
- 마지막 증분량이 예상보다 크면 창이 늘어난다.

이 선택은 결국 업무 특성과 조직 성숙도의 문제다.

### 4단계: 검증은 row count만으로 끝내지 않는다

대용량 migration에서 가장 위험한 착각은 row count가 같으면 끝났다고 보는 것이다.

실제로는 아래를 같이 본다.

- 월별 row count 비교
- tenant별 count 샘플 비교
- 최신/최소 `created_at` 비교
- 특정 action/event_type 분포 비교
- 대표 API 결과 샘플 비교

예를 들어:

```sql
SELECT tenant_id, count(*)
FROM audit_history
WHERE created_at >= TIMESTAMPTZ '2026-03-01 00:00:00+09'
  AND created_at <  TIMESTAMPTZ '2026-04-01 00:00:00+09'
GROUP BY tenant_id
ORDER BY tenant_id;
```

동일 쿼리를 새 테이블에도 적용해 diff를 본다.

### 5단계: cutover 후 바로 해야 할 일

테이블 이름만 바꾸고 끝내면 안 된다.

cutover 직후에는 아래를 집중적으로 봐야 한다.

- 대표 조회 `EXPLAIN`에서 pruning이 실제 되는가
- 최신 partition 인덱스가 예상대로 쓰이는가
- default partition에 이상 row가 쌓이지 않는가
- insert latency가 상승하지 않는가
- retention job이 새 구조에서 그대로 동작하는가

즉 cutover는 성공의 끝이 아니라, **새 구조 검증의 시작**이다.

### 이 예시에서 중요한 교훈

1. 파티셔닝은 스키마 기능이지만, migration은 배포/운영 프로젝트다.
2. backfill 단위와 retention 단위를 맞추면 검증과 복구가 쉬워진다.
3. dual write 여부는 기술 취향이 아니라 허용 가능한 정지 시간과 오류 복구 전략으로 결정한다.
4. cutover 후에는 pruning과 hot partition behavior를 즉시 확인해야 한다.

---

## 핵심 개념 10: FK, DELETE, UPDATE 모델까지 같이 봐야 파티셔닝이 진짜 운영 가능해진다

파티셔닝을 설계할 때 많은 논의가 pruning과 retention에 집중된다.

물론 중요하다.

하지만 실제 서비스에서는 아래 같은 질문이 더 어렵게 돌아온다.

- 부모/자식 관계가 많은 테이블에도 파티셔닝이 맞는가?
- `ON DELETE CASCADE`는 여전히 현실적인가?
- partition key가 포함된 복합 PK를 다른 테이블들이 어떻게 참조해야 하는가?
- 상태 변경이 많은 테이블에 파티셔닝을 넣으면 row movement 비용이 감당 가능한가?

즉 파티셔닝은 읽기 전략인 동시에 **데이터 모델 전략**이기도 하다.

### FK가 많은 핵심 엔터티 본체는 더 보수적으로 판단한다

예를 들어 `orders` 본체 테이블이 있다고 하자.

- `payments`
- `shipments`
- `refunds`
- `order_items`
- `notifications`

같은 테이블이 모두 `orders`를 참조한다.

이 상황에서 `orders`를 시간 기반 파티셔닝하면 이론상 가능해 보여도, 실무에서 바로 복잡도가 올라간다.

- PK를 `(created_at, order_id)`로 두면 참조 측 FK도 더 무거워진다.
- `order_id` 단일 전역 PK를 그대로 강하게 유지하고 싶다면 제약이 생긴다.
- 운영 쿼리와 ORM이 composite key를 자연스럽게 다루지 못할 수 있다.
- 오래된 주문도 종종 point lookup 대상이라 pruning 이득이 약할 수 있다.

그래서 파티셔닝은 보통 아래 순서로 맞는다.

1. 로그/이력/감사/이벤트 테이블
2. append-heavy 원장성 테이블
3. 일부 대형 fact성 OLTP 테이블
4. FK가 얽힌 핵심 본체 테이블은 가장 나중

이 순서를 거꾸로 가면 구현 복잡도부터 크게 느껴진다.

### `ON DELETE CASCADE`보다 partition drop이 중요한 테이블인지 구분해야 한다

히스토리/로그 테이블에서는 row 단위 삭제보다 partition 단위 폐기가 훨씬 자연스럽다.

이 경우 부모 행 삭제에 맞춰 자식 로그까지 `ON DELETE CASCADE`로 따라 지우는 설계는 오히려 맞지 않을 수 있다.

왜냐하면 이런 로그성 데이터는 보통 아래 특성을 가지기 때문이다.

- 부모 엔터티가 삭제돼도 감사 추적은 남겨야 한다.
- 보관 기준은 부모 생명주기보다 시간 정책이 더 중요하다.
- 자식 로그 삭제는 개별 row보다 기간 단위 삭제가 훨씬 싸다.

즉 파티셔닝을 도입하는 순간, 삭제 모델도 함께 다시 물어야 한다.

- 이 데이터는 row delete 중심인가?
- 아니면 retention window 끝에서 한 번에 버리는가?

### partition key를 포함하는 PK가 애플리케이션 모델에 미치는 영향

다음 설계를 보자.

```sql
PRIMARY KEY (created_at, id)
```

DB 관점에서는 partition 친화적이다.

하지만 애플리케이션에서 아래 요구가 있으면 다시 생각해야 한다.

- 외부 API가 `id` 하나만으로 리소스를 조회한다.
- 다른 테이블이 `id` 하나만 들고 참조한다.
- ORM이 composite PK를 어색하게 다룬다.
- 운영자도 `id` 하나만 보고 바로 행을 찾고 싶어 한다.

이때 선택지는 몇 가지다.

#### 선택지 A: 애플리케이션 식별자와 물리 PK를 분리한다

- 애플리케이션은 `id`를 논리 식별자로 사용
- DB는 partition key 포함 PK/UK 사용
- point lookup이 필요하면 `id` 보조 인덱스와 적절한 조회 경로를 둠

장점은 파티션 친화적 설계를 유지할 수 있다는 점이다.

단점은 모델이 조금 더 복잡해진다는 점이다.

#### 선택지 B: 본체 테이블은 비파티션으로 두고, history/log 테이블만 파티셔닝한다

이게 실제로 가장 현실적인 경우가 많다.

- `orders` 본체는 일반 테이블
- `order_status_history`, `order_events`, `order_audit_logs`만 파티셔닝

이 구조는 종종 가장 좋은 절충안이다.

- 본체는 단순 FK/PK 모델 유지
- 대용량 성장과 retention pain은 history 계층에서 해결

### UPDATE가 많은 테이블은 "partitioning이 좋은가"보다 "무슨 컬럼이 얼마나 바뀌는가"를 먼저 본다

예를 들어 `jobs` 테이블이 있고,

- `status`
- `retry_count`
- `updated_at`
- `worker_id`

가 자주 바뀐다고 하자.

이때 `updated_at` 기준 파티셔닝은 보통 좋지 않다.

- row가 자꾸 파티션 경계를 넘을 수 있다.
- UPDATE가 사실상 이동 작업이 된다.
- 애플리케이션 의미와 물리 구조가 충돌한다.

반대로 아래는 현실적일 수 있다.

- `created_at` 기준 파티셔닝
- hot recent jobs만 유지
- 오래된 completed jobs는 차가운 파티션으로 남김

즉 **변경 축과 보관 축을 구분**해야 한다.

파티셔닝은 보통 보관 축에 맞춰야지, 상태 변경 축에 맞추는 것이 아니다.

### FK/PK 설계에서 내가 자주 쓰는 질문

1. 이 테이블은 본체인가, history인가?
2. point lookup이 전기간에 걸쳐 중요한가?
3. FK가 많이 달려 있는가?
4. 전역 unique를 DB가 강하게 보장해야 하는가?
5. key가 자주 바뀌는가?

여기서 본체/전역 unique/FK가 강하면, 파티셔닝은 더 늦게 검토하는 편이 안전하다.

---

## 실전 자동화: 파티셔닝 품질은 SQL 문법보다 달력 배치와 검증 잡에서 결정된다

파티셔닝 도입 후 몇 달 지나면 결국 남는 것은 automation 품질이다.

수동으로 운영 가능한 구조는 오래 가지 않는다.

내가 기본으로 두는 자동화는 크게 네 가지다.

### 1) 미래 partition 선생성 잡

최소한 다음 2~3개 interval은 항상 미리 만들어 두는 편이 좋다.

예를 들어 월별 partition이라면:

- 현재 월
- 다음 달
- 다다음 달

까지는 상시 존재하게 둔다.

이 작업은 보통 하루 한 번 혹은 월초에만 돌려도 충분하다.

중요한 건 **생성 여부를 idempotent하게 확인**하는 것이다.

예를 들어 배치가 두 번 돌아도 문제없어야 하고, 이미 만들어진 partition은 건너뛰어야 한다.

### 2) 누락 알람

생성 잡이 있다고 끝이 아니다.

- 다음 interval partition이 존재하지 않음
- default partition row 급증
- 예상과 다른 bound가 생성됨

같은 상황을 알람으로 바로 받아야 한다.

실무에서는 생성 잡보다 알람이 더 중요할 때도 많다.

왜냐하면 장애는 "스크립트가 없어서"보다 **스크립트가 실패했는데 아무도 몰라서** 더 자주 난다.

### 3) retention 검증 잡

매일 혹은 매주 아래를 점검한다.

- 보관 기간을 초과한 partition 목록
- detach 예정 partition 존재 여부
- 실제 아카이브 완료 여부
- drop 대기 중 partition 적체 여부

이 과정을 체크하지 않으면 retention은 언젠가 밀린다.

그리고 retention이 밀리는 시스템은 대개 파티셔닝 도입 이득의 절반을 잃는다.

### 4) pruning regression 검증

이건 꽤 자주 빠지지만 중요하다.

애플리케이션 코드가 바뀌거나 ORM 버전이 올라가면, 원래 잘 되던 pruning이 약해질 수 있다.

예를 들면:

- 시간 범위를 문자열 파라미터로 애매하게 넘기기 시작했다.
- `date(created_at)` 같은 표현이 새 코드에 들어왔다.
- 리포트 쿼리가 `OR` 조건을 많이 쓰기 시작했다.

그래서 대표 쿼리 몇 개는 CI나 배포 전 점검 스크립트에서 `EXPLAIN` 결과를 비교하는 것도 가치가 있다.

### 운영 자동화 예시: 월별 partition 생성 절차

실제 구현은 도구마다 다르지만, 사고방식은 대체로 이렇다.

1. 현재 시각 기준 다음 3개월 범위 계산
2. 필요한 partition 이름과 bound 생성
3. 존재 여부 확인
4. 없으면 생성
5. 생성 후 인덱스/권한/테이블스페이스 정책 확인
6. 결과를 로그와 알람에 남김

중요한 건 SQL 자체보다 아래다.

- 실패해도 다시 돌릴 수 있는가
- 중간 성공 상태를 설명할 수 있는가
- 잘못된 bound가 생성되면 바로 탐지 가능한가

### retention 자동화 예시: detach 후 비동기 drop

나는 가능하면 한 단계로 끝내지 않는 편이다.

- 1차: 서비스 테이블에서 detach
- 2차: 백업 혹은 외부 저장 확인
- 3차: 별도 창에서 drop

이렇게 나누면 장점이 있다.

- 서비스 쿼리 영향은 먼저 제거된다.
- 삭제 자체는 더 여유 있는 시간에 수행 가능하다.
- 아카이브 누락 시 되돌릴 여지가 있다.

### 파티셔닝 자동화에서 흔한 안티패턴

#### 1) 생성만 하고 검증하지 않기

DDL이 성공했다고 해서 bound가 의도대로라는 뜻은 아니다.

#### 2) default partition을 만들어 놓고 알람을 안 걸기

이건 거의 미래 장애 예약과 비슷하다.

#### 3) retention 스크립트를 즉시 drop-only로 두기

처음에는 편하지만, 아카이브나 실수 복구가 필요해지면 runbook이 다시 생긴다.

#### 4) 운영자가 구조를 설명할 수 없는 자동화

자동화가 복잡할수록 문서와 관측이 더 중요하다.

운영자가 "지금 어떤 partition이 있어야 하고, 왜 이 partition이 비어 있는지, 왜 default가 늘었는지"를 설명 못 하면 자동화는 실패한 것이다.

### 파티셔닝 자동화의 목표는 손을 덜 쓰는 것이 아니라, 놀랄 일을 줄이는 것이다

이 문장을 꽤 중요하게 본다.

자동화는 단순 노동 절감도 맞지만, 더 본질적으로는 다음을 위해 필요하다.

- 새 달이 왔는데 insert가 막히는 일을 막는다.
- retention이 반년 밀리는 일을 막는다.
- default partition이 조용히 커지는 일을 막는다.
- attach/detach가 예기치 않은 시간에 길어지는 일을 막는다.

파티셔닝은 결국 달력과 함께 움직이는 구조다.

달력을 시스템이 기억하게 해야 사람을 덜 깨운다.

---

## 운영 관측 포인트: 파티셔닝은 만들고 끝나는 기능이 아니라 계속 보는 대상이다

파티셔닝을 도입한 뒤에도 지표를 안 보면 구조만 복잡해지고 이득을 체감하기 어렵다.

실무에서 기본적으로 보고 싶은 항목은 아래다.

### 1) 파티션 수와 증가 속도

- 현재 총 파티션 수
- 향후 3개월 예상 파티션 수
- subpartition 포함 총 객체 수
- 파티션별 크기 편차

파티션 개수는 느리게 독이 되는 지표다.

처음엔 멀쩡하지만 1년, 2년 쌓이면 planning과 maintenance 비용으로 돌아온다.

### 2) hot partition 크기와 인덱스 크기

- 최신 partition row 수
- 최신 partition table/index size
- 상위 3개 hot partition의 쓰기량
- hot partition autovacuum 빈도와 duration

파티셔닝을 했는데도 최신 partition 하나가 너무 빨리 비대해지면 interval이나 인덱스 설계를 다시 볼 신호다.

### 3) pruning이 실제로 얼마나 되는가

- 대표 쿼리의 `EXPLAIN`에서 몇 개 partition이 읽히는가
- 예상 fan-out과 실제 fan-out 차이
- ORM/쿼리 빌더가 partition key 조건을 흐리고 있지 않은가

파티셔닝 도입 후에도 대표 API 10개 정도는 주기적으로 실제 계획을 보는 편이 좋다.

### 4) default partition row count

default partition을 두었다면 가장 먼저 대시보드에 올릴 만한 지표다.

- row count
- 최근 1일 증가량
- 어떤 입력 경로가 default에 넣었는지

default가 조용히 커지는 시스템은 미래의 정리 비용을 빚처럼 쌓고 있는 셈이다.

### 5) retention job 성공 여부

- 미래 파티션 생성 성공/실패
- detach/drop 대상 파티션 수
- 아카이브 후 삭제 성공 여부
- 예상보다 오래 남은 파티션 존재 여부

파티셔닝 운영의 품질은 쿼리 성능만이 아니라 **달력 기반 작업이 얼마나 안정적으로 굴러가는가**로 드러난다.

---

## 트레이드오프: 파티셔닝은 분명 강력하지만, 공짜는 아니다

좋은 점만 보면 파티셔닝은 만능처럼 보일 수 있다.

하지만 실무에서는 아래 비용을 반드시 같이 본다.

### 트레이드오프 1: DDL 자동화와 운영 복잡도가 늘어난다

일반 테이블은 한 번 만들면 오래 간다.

파티션 테이블은 다르다.

- 미래 파티션을 만들어야 한다.
- 오래된 파티션을 정리해야 한다.
- 인덱스 추가/변경도 계층 전체를 고려해야 한다.
- attach/detach, backfill, archive runbook이 필요하다.

즉 파티셔닝은 성능 기능이면서 동시에 **운영 시스템**이다.

### 트레이드오프 2: too many partitions는 planning과 관리 비용을 키운다

파티션을 잘게 나누면 pruning이 좋아질 것 같지만, 지나치면 다음 비용이 온다.

- planner가 다뤄야 할 객체 수 증가
- 통계/메타데이터 관리 증가
- 인덱스 수 증가
- 백업/점검/DDL fan-out 증가

"일별이 더 정밀하니까 무조건 좋다"는 생각은 흔한 함정이다.

보통은 **대표 조회 범위와 retention 단위에 맞는 가장 거친 interval**부터 시작하는 편이 안전하다.

### 트레이드오프 3: non-partition-key 전역 uniqueness와 FK 설계가 까다로워진다

핵심 OLTP 엔터티 본체에서 이 제약은 꽤 크게 느껴진다.

- 단일 컬럼 전역 PK/UK를 강하게 원한다
- FK가 단순해야 한다
- 참조 경로가 많다

이런 테이블은 파티셔닝 이득보다 모델 복잡도 비용이 더 클 수 있다.

### 트레이드오프 4: partition key 변경 UPDATE는 비싸고 위험할 수 있다

`updated_at`, `status`, 재분류 가능한 business field를 key로 잡으면,

- row movement가 늘고
- 예기치 않은 write cost가 생기고
- 애플리케이션 의미도 더 복잡해진다.

그래서 파티션 키는 "자주 조회되는가"만큼이나 **잘 안 바뀌는가**가 중요하다.

### 트레이드오프 5: 파티셔닝은 샤딩이 아니다

파티셔닝은 같은 PostgreSQL 인스턴스/클러스터 안에서 logical table을 여러 physical child로 나누는 기능이다.

- 노드 간 수평 확장 자체를 해결하지 않는다.
- write throughput 한계를 무한히 밀어주지 않는다.
- 하나의 병목이 여러 파티션으로 가려질 뿐 완전히 사라지지 않을 수 있다.

즉 파티셔닝을 샤딩처럼 기대하면 실망이 크다.

파티셔닝은 어디까지나 **단일 데이터베이스 안에서 운영 경계를 잘게 만드는 기술**이다.

---

## 흔한 실수: PostgreSQL 파티셔닝을 망가뜨리는 패턴들

### 1) 작은 테이블에 너무 일찍 도입하기

테이블이 크지도 않고 retention pain도 없는데 "미리 구조를 잘 잡자"며 파티셔닝을 넣는 경우가 있다.

대개는 이르다.

파티셔닝은 미래 대비용 추상화가 아니라, **현재 pain이 명확할 때 가치가 큰 복잡도**다.

### 2) `updated_at` 같은 움직이는 컬럼을 partition key로 잡기

이건 자주 바뀌는 행을 계속 다른 partition으로 옮기게 만들 수 있다.

파티셔닝은 immutable한 lifecycle 축에 가까울수록 좋다.

### 3) interval을 너무 잘게 쪼개기

- 월별이면 충분한데 일별로 간다.
- 일별이면 충분한데 시간별로 간다.

처음에는 pruning이 예뻐 보이지만, 1년 뒤 객체 수와 plan overhead가 문제로 돌아온다.

### 4) partition key에 함수가 씌워진 쿼리를 방치하기

DDL은 잘 만들었는데 애플리케이션 쿼리가 다음처럼 작성된다.

```sql
WHERE date(created_at) = CURRENT_DATE
```

이러면 pruning 이득을 잃기 쉽다.

파티셔닝은 SQL 스타일 가이드까지 포함해야 한다.

### 5) future partition 자동화를 안 만들기

가장 전형적인 운영 사고다.

- 월이 바뀌었는데 파티션이 없음
- 서비스 insert 실패
- 긴급 DDL 수행

이건 구조 문제가 아니라 운영 준비 부족 문제다.

### 6) default partition을 만들고 모니터링하지 않기

default는 언젠가 예외 데이터를 삼킨다.

문제는 대부분 그 사실을 한참 뒤에 안다는 점이다.

### 7) 파티셔닝으로 모든 성능 문제를 해결하려 하기

파티셔닝은 특히 아래 문제를 자동으로 고치지 않는다.

- 잘못된 인덱스 설계
- 과도한 UPDATE churn
- 넓은 JSONB 스캔
- 비효율적인 join 순서
- 애플리케이션의 불필요한 fan-out query

즉 파티셔닝이 필요한 문제와 아닌 문제를 구분해야 한다.

### 8) 로그/이력 테이블과 핵심 엔터티 테이블을 같은 기준으로 판단하기

append-heavy history table에는 아주 잘 맞는 설계가,

- 강한 FK
- 전역 unique
- 잦은 상태 업데이트
- point lookup 중심

의 본체 테이블에는 꼭 맞지 않을 수 있다.

테이블 성격을 구분해야 한다.

### 9) 파티셔닝 이후 검증을 안 하기

- pruning이 실제 되는지 안 본다.
- retention job이 진짜 잘 도는지 안 본다.
- default partition 증가를 안 본다.
- hot partition index size를 안 본다.

파티셔닝은 설계보다 운영 검증에서 성공 여부가 갈린다.

---

## 도입 판단 체크리스트: 이 테이블은 정말 파티셔닝이 맞는가?

아래 질문에 많이 "예"가 나오면 파티셔닝을 진지하게 검토할 가치가 있다.

### 문제 적합성

- [ ] 테이블이 충분히 크고 계속 빠르게 증가한다.
- [ ] 대표 조회가 특정 시간/키 구간에 강하게 집중된다.
- [ ] 오래된 데이터를 주기적으로 버리거나 아카이브해야 한다.
- [ ] 대량 `DELETE`가 실제 pain point다.
- [ ] hot data와 cold data를 분리하면 운영 이득이 분명하다.

### 키/구조 적합성

- [ ] partition key 후보가 비교적 immutable하다.
- [ ] partition key가 대표 필터와 잘 맞는다.
- [ ] retention 단위와 partition interval을 자연스럽게 맞출 수 있다.
- [ ] 예상 partition 수가 감당 가능한 수준이다.
- [ ] skew가 지나치게 크지 않거나 완화 전략이 있다.

### 쿼리/애플리케이션 적합성

- [ ] 대표 SQL을 pruning-friendly 형태로 고칠 수 있다.
- [ ] ORM/쿼리 빌더가 범위 조건을 흐리지 않는다.
- [ ] non-partition-key 전역 unique 요구가 치명적이지 않다.
- [ ] partition key 변경 UPDATE가 드물다.

### 운영 준비도

- [ ] future partition 자동 생성 작업이 있다.
- [ ] retention detach/drop runbook이 있다.
- [ ] default partition 전략과 모니터링이 있다.
- [ ] `EXPLAIN`과 size metrics로 pruning 및 fan-out을 점검할 수 있다.
- [ ] 인덱스 추가/변경 절차를 파티션 계층 기준으로 운영할 수 있다.

이 체크리스트를 통과하지 못한 채 파티셔닝을 먼저 넣으면, 성능보다 관리비가 더 크게 느껴질 가능성이 높다.

---

## 추천 운영 원칙: 내가 PostgreSQL 파티셔닝을 설계할 때 기본으로 두는 기준

마지막으로, 실무에서 재사용하기 좋은 원칙만 짧게 정리하면 이렇다.

### 원칙 1: 기본은 range, 이유가 분명할 때만 list/hash로 간다

대부분의 대용량 운영 테이블은 시간 기반 lifecycle을 가진다.

그래서 range가 가장 자주 이긴다.

### 원칙 2: interval은 대표 조회와 retention이 허용하는 가장 거친 단위부터 시작한다

월로 충분하면 월, 일이 꼭 필요할 때만 일.

partition 수는 나중에 반드시 비용으로 돌아온다.

### 원칙 3: partition key는 잘 안 바뀌는 컬럼이어야 한다

움직이는 값을 키로 잡는 순간 row movement 비용과 모델 복잡도가 커진다.

### 원칙 4: pruning-friendly SQL을 같이 표준화한다

DDL만 바꾸면 절반짜리다.

애플리케이션 쿼리까지 함께 맞춰야 한다.

### 원칙 5: default partition은 만들더라도 반드시 감시한다

default는 안전장치지, 방치해도 되는 만능 통이다.

### 원칙 6: retention automation이 없으면 파티셔닝도 반쪽이다

파티셔닝의 핵심 이득은 drop/detach 같은 lifecycle 운영에서 나온다.

자동화가 빠지면 가장 큰 이득을 놓친다.

### 원칙 7: 핵심 OLTP 본체 테이블은 더 엄격하게 판단한다

로그, 이력, 이벤트는 파티셔닝과 잘 맞는다.

하지만 강한 전역 unique와 단순 FK가 중요한 본체 엔터티는 더 신중해야 한다.

---

## 한 줄 정리

PostgreSQL 파티셔닝의 핵심은 테이블을 잘게 쪼개는 것이 아니라, **쿼리가 읽어야 할 구간·운영자가 버려야 할 구간·시스템이 뜨겁게 관리해야 할 구간을 서로 다른 경계로 분리해 대용량 테이블을 운영 가능한 상태로 바꾸는 것**이다.
