---
layout: post
title: "PostgreSQL Autovacuum 실전: Bloat, Freeze, 장기 트랜잭션까지 운영 기준 정리"
date: 2026-04-02 11:40:00 +0900
categories: [sql]
tags: [study, sql, postgresql, autovacuum, vacuum, performance, operations]
permalink: /sql/2026/04/02/study-postgresql-autovacuum-bloat-freeze.html
---

## 배경: 왜 PostgreSQL 운영은 결국 Vacuum 이해로 돌아오는가

PostgreSQL에서 성능 문제가 생기면 많은 팀이 먼저 인덱스, 쿼리 튜닝, 커넥션 풀 크기부터 본다. 물론 다 중요하다. 그런데 운영을 오래 해보면, 특정 시점부터는 더 근본적인 문제가 드러난다.

- 분명 인덱스는 맞는데 테이블이 계속 커진다.
- 삭제한 데이터가 많은데 디스크 사용량은 잘 안 줄어든다.
- 어제까지 빠르던 쿼리가 갑자기 느려진다.
- `pg_stat_activity`를 보면 긴 트랜잭션이 하나 있는데, 그 뒤로 autovacuum이 밀린다.
- 어느 날 갑자기 `wraparound` 경고가 뜨고 팀 전체가 긴장한다.

이 문제들은 대개 한 줄로 연결된다. **MVCC 기반 스토리지 특성을 이해하지 못한 채 autovacuum을 “백그라운드 청소기” 정도로만 취급한 것**이다.

PostgreSQL은 UPDATE 시 기존 행을 덮어쓰지 않고 새 버전을 만든다. 이 덕분에 읽기/쓰기 동시성이 좋아지지만, 그 대가로 **dead tuple**, **bloat**, **transaction ID age**, **freeze**라는 운영 주제가 생긴다. Autovacuum은 단순한 최적화 기능이 아니라, PostgreSQL이 장기적으로 건강하게 살아남기 위한 필수 유지보수 메커니즘이다.

이 글은 “vacuum이 뭔지” 수준이 아니라, 실제 서비스 운영 기준으로 아래를 정리한다.

- 왜 dead tuple이 생기고 bloat로 이어지는가
- autovacuum이 실제로 하는 일은 무엇인가
- 어떤 테이블만 유독 계속 느려지는 이유는 무엇인가
- 장기 트랜잭션과 배치가 autovacuum을 어떻게 망가뜨리는가
- 어떤 지표를 봐야 사고를 미리 막을 수 있는가
- 언제 설정을 전역이 아니라 테이블 단위로 바꿔야 하는가

---

## 핵심 개념 1: MVCC, dead tuple, 그리고 “삭제했는데 왜 안 줄지?”의 정체

PostgreSQL의 MVCC(Multi-Version Concurrency Control)에서는 UPDATE와 DELETE가 곧바로 물리 삭제를 의미하지 않는다.

예를 들어 아래 UPDATE를 보자.

```sql
UPDATE orders
SET status = 'PAID'
WHERE id = 1001;
```

애플리케이션 입장에서는 “한 행 수정”이지만, 스토리지 관점에서는 다음에 가깝다.

1. 기존 row version은 더 이상 최신 상태가 아님
2. 새 row version 생성
3. 기존 row version은 어떤 트랜잭션에는 여전히 보여야 할 수 있음
4. 나중에 안전하다고 판단되면 vacuum이 회수

즉, UPDATE가 많은 테이블은 시간이 지날수록 **죽은 행 버전(dead tuple)** 이 쌓인다. DELETE도 마찬가지다. 이 공간은 즉시 운영체제에 반환되지 않는다. 우선은 **테이블 내부 재사용 가능 공간**이 되고, 적절히 관리되지 않으면 **테이블/인덱스 bloat**로 이어진다.

여기서 중요한 포인트가 두 가지다.

### 1) 일반 VACUUM은 “재사용 가능”하게 만들지, 파일을 항상 줄이진 않는다

많은 팀이 “DELETE 많이 했는데 왜 디스크가 안 줄지?”에서 당황한다. 일반 `VACUUM`은 dead tuple 공간을 향후 INSERT/UPDATE가 재사용할 수 있게 만들 뿐, 파일 자체를 즉시 최소 크기로 압축하는 도구가 아니다.

### 2) Bloat는 단순 저장공간 이슈가 아니라 조회 성능 이슈다

테이블이 실제 필요한 데이터보다 훨씬 커지면:

- buffer cache 효율이 떨어지고
- 순차/인덱스 스캔 시 더 많은 페이지를 읽고
- 인덱스도 불필요하게 커져 메모리 적중률이 떨어진다

결국 “쓰기 많은 서비스인데 읽기도 느려지는” 현상으로 돌아온다.

---

## 핵심 개념 2: Autovacuum이 실제로 하는 일

Autovacuum을 “dead tuple 청소기”로만 이해하면 절반만 아는 것이다. 실무에서 autovacuum은 최소 네 가지 역할을 가진다.

### 1) Dead tuple 회수

업데이트/삭제로 생긴 불필요한 row version을 정리해 테이블 내부 재사용 공간을 만든다.

### 2) ANALYZE를 통한 통계 갱신

플래너는 통계가 오래되면 잘못된 실행 계획을 선택한다. 예를 들어 특정 상태값이 원래 5%였는데 지금 80%가 됐는데도 예전 통계를 쓰면, 인덱스 선택이 뒤틀릴 수 있다.

### 3) Visibility Map 갱신

이건 잘 안 보이지만 중요하다. Vacuum은 어떤 페이지가 “모든 트랜잭션에 대해 가시적(all-visible)”인지 표시해 **index-only scan** 효율에도 기여한다.

### 4) Freeze 처리로 Transaction ID Wraparound 방지

이게 운영적으로 가장 중요하다. PostgreSQL의 트랜잭션 ID는 무한하지 않다. 오래 방치하면 아주 오래된 row version의 가시성 판단이 위험해질 수 있다. 이를 막기 위해 오래된 tuple을 freeze해서 wraparound 위험을 차단한다.

즉, autovacuum은 성능 최적화 기능이 아니라 **데이터베이스 생존 장치**다.

---

## 핵심 개념 3: VACUUM, VACUUM FULL, ANALYZE를 구분해야 한다

이 셋을 섞어 생각하면 운영 판단이 계속 어긋난다.

### VACUUM

- dead tuple 회수
- 공간 재사용 가능화
- visibility map 갱신
- freeze 일부 수행 가능
- 일반 DML과 병행 가능
- 보통 운영의 기본값

### VACUUM FULL

- 테이블을 재작성해 파일 크기를 적극적으로 줄임
- `ACCESS EXCLUSIVE` 락 필요
- 디스크 추가 공간도 필요
- 온라인 트래픽 환경에서는 매우 신중해야 함

### ANALYZE

- 플래너 통계 갱신
- 꼭 dead tuple 정리와 동일한 주기가 필요하진 않음
- 쓰기량보다 “분포 변화”가 클 때 더 중요함

실무 기준으로는 대부분 이렇게 생각하면 된다.

- 평상시: **autovacuum + autoanalyze**가 기본
- 심한 bloat: **원인 제거 후** 필요 시 `VACUUM FULL` 또는 테이블 재작성 계열 작업 검토
- 쿼리 계획 이상: vacuum보다 **analyze 주기/통계 품질**을 먼저 점검

---

## 실무에서 문제가 되는 패턴 1: 장기 트랜잭션이 vacuum을 막는다

Autovacuum 이슈에서 가장 자주 놓치는 원인이 장기 트랜잭션이다.

예를 들어 아래 상황을 보자.

- 리포트 배치가 `BEGIN` 후 수십 분 동안 열린 채 실행됨
- 그 사이 온라인 트래픽이 같은 테이블을 계속 UPDATE/DELETE
- vacuum은 dead tuple을 보고도 “아직 누군가 볼 수 있을지 몰라서” 완전히 회수 못함

결과:

- dead tuple 누적
- 테이블/인덱스 팽창
- autovacuum이 자주 돌지만 효과가 약함
- 결국 I/O만 많이 쓰고 bloat는 계속 남음

장기 트랜잭션 확인용으로 가장 먼저 볼 쿼리는 이런 형태다.

```sql
SELECT
  pid,
  usename,
  application_name,
  state,
  xact_start,
  now() - xact_start AS xact_age,
  wait_event_type,
  wait_event,
  query
FROM pg_stat_activity
WHERE xact_start IS NOT NULL
ORDER BY xact_start ASC;
```

여기서 핵심은 단순히 오래된 세션이 아니라, **트랜잭션이 열린 채 오래 살아 있는 세션**이다. 특히 아래는 경고 신호다.

- ORM 세션이 커넥션을 오래 잡고 있는 경우
- 배치가 큰 범위를 한 트랜잭션으로 묶는 경우
- 읽기 전용 작업인데도 명시적 트랜잭션을 길게 유지하는 경우
- 장애 분석용 세션이 `BEGIN` 상태로 방치된 경우

### 운영 원칙

- 읽기 배치도 가능하면 짧은 트랜잭션으로 끊는다.
- 청크 배치는 `LIMIT`/범위 기준으로 커밋 단위를 나눈다.
- 외부 API 호출, 파일 저장, 네트워크 대기는 트랜잭션 밖으로 뺀다.
- 관리 콘솔/스크립트의 `idle in transaction`을 반드시 경계한다.

---

## 실무에서 문제가 되는 패턴 2: “모든 테이블에 같은 autovacuum 설정”은 거의 항상 틀린다

기본 autovacuum 설정은 안전한 출발점이지, 최적값이 아니다. 문제는 테이블마다 쓰기 패턴이 너무 다르다는 데 있다.

예를 들어:

- `order_events`: 초당 수백 건 INSERT/UPDATE, 최근 데이터 핫함
- `users`: 업데이트는 적지만 조회 빈도 높음
- `batch_results`: 하루 한 번 대량 INSERT 후 거의 읽기 전용
- `session_store`: 짧은 TTL과 빈번한 UPDATE/DELETE

이 테이블들에 같은 임계값을 적용하면,

- 어떤 테이블은 너무 늦게 vacuum되고
- 어떤 테이블은 너무 자주 vacuum되어 I/O만 낭비하고
- 어떤 테이블은 analyze 부족으로 플랜이 깨진다

PostgreSQL은 테이블 단위로 autovacuum 파라미터를 조정할 수 있다.

```sql
ALTER TABLE order_events SET (
  autovacuum_vacuum_scale_factor = 0.02,
  autovacuum_vacuum_threshold = 5000,
  autovacuum_analyze_scale_factor = 0.01,
  autovacuum_analyze_threshold = 3000
);
```

이 설정의 의미는 단순하다.

- 변경이 매우 잦은 큰 테이블은 **scale factor를 낮춰 더 자주** 돌게 한다.
- 작은 테이블은 threshold가 너무 낮으면 과도한 vacuum이 발생할 수 있으니 균형을 맞춘다.

### 판단 기준

#### 큰 테이블 + 변경량 많음

- vacuum/analyze 더 자주
- scale factor 낮춤
- 필요 시 cost limit/tuning 검토

#### 작은 테이블 + 변경량 적음

- 기본값 유지가 흔히 충분
- 과도한 개별 튜닝은 관리 복잡도만 늘릴 수 있음

#### 분포가 자주 바뀌는 테이블

- vacuum보다 analyze 빈도가 더 중요할 수 있음
- 예: 특정 status, tenant, created_at 쏠림이 빠르게 변함

---

## 핵심 개념 4: Bloat는 테이블만이 아니라 인덱스에도 쌓인다

많은 팀이 테이블 크기만 보고 안심한다. 실제 운영에서는 인덱스 bloat가 더 아픈 경우도 많다.

대표 신호는 아래와 같다.

- 테이블 row 수 증가 대비 인덱스 크기가 과도하게 큼
- 같은 조회인데 cache miss가 늘어남
- `EXPLAIN (ANALYZE, BUFFERS)` 상 인덱스 접근 페이지 수가 비정상적으로 많음
- UPDATE 많은 테이블인데 인덱스 컬럼도 자주 바뀜

특히 UPDATE가 인덱스 포함 컬럼을 자주 건드리면, HOT(Heap-Only Tuple) 최적화를 못 타는 경우가 많아진다. 그러면 힙뿐 아니라 인덱스도 더 많이 흔들린다.

### HOT 업데이트를 이해해야 하는 이유

HOT는 인덱스 키가 바뀌지 않을 때 인덱스 수정 비용을 줄여주는 최적화다. 즉,

- 자주 바뀌는 컬럼을 인덱스에 무분별하게 넣으면
- HOT 기회를 줄이고
- vacuum 부담과 인덱스 bloat 가능성을 키운다

이건 단순 인덱스 설계 문제가 아니라, **쓰기 경로 최적화** 문제다.

### 실무 판단 질문

- 정말 자주 바뀌는 상태 컬럼을 인덱스에 넣어야 하나?
- 복합 인덱스가 읽기 성능 이득보다 쓰기 증폭을 더 크게 만들지 않나?
- fillfactor를 낮춰 HOT 여지를 확보할 가치가 있나?

예를 들어 핫 업데이트가 매우 많은 테이블은 이렇게 검토할 수 있다.

```sql
ALTER TABLE order_events SET (fillfactor = 80);
```

fillfactor를 낮추면 페이지 여유 공간이 늘어 HOT 업데이트 가능성이 높아질 수 있다. 대신 디스크 사용량은 증가한다. 이런 선택은 “용량”이 아니라 “쓰기 증폭과 vacuum 부담” 관점에서 평가해야 한다.

---

## 모니터링: 실제로 봐야 할 지표와 쿼리

운영에서는 “autovacuum 켜져 있음”이 중요한 게 아니다. **충분히 빨리, 충분히 효과적으로 도는지**가 중요하다.

### 1) 테이블별 dead tuple 추정치

```sql
SELECT
  schemaname,
  relname,
  n_live_tup,
  n_dead_tup,
  last_vacuum,
  last_autovacuum,
  last_analyze,
  last_autoanalyze
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC
LIMIT 20;
```

이 결과를 볼 때는 절대값만 보지 말고,

- `n_dead_tup / n_live_tup`
- 테이블 크기
- 최근 autovacuum 시각
- 업데이트 빈도

를 같이 해석해야 한다.

### 2) 오래된 transaction age 확인

```sql
SELECT
  datname,
  age(datfrozenxid) AS xid_age
FROM pg_database
ORDER BY xid_age DESC;
```

이 값은 wraparound 위험을 조기에 보는 기본 지표다. 특정 DB의 `xid_age`가 과도하게 커지면, 단순 성능 이슈가 아니라 **긴급 유지보수** 영역으로 넘어간다.

### 3) vacuum 진행 상황

```sql
SELECT
  pid,
  relid::regclass AS table_name,
  phase,
  heap_blks_total,
  heap_blks_scanned,
  heap_blks_vacuumed,
  index_vacuum_count,
  max_dead_tuples,
  num_dead_tuples
FROM pg_stat_progress_vacuum;
```

이 뷰는 “지금 vacuum이 느린지, 어디서 머무는지”를 볼 때 유용하다. 특히 I/O 병목인지, 인덱스 정리 단계가 긴지, 대형 테이블 하나가 오래 잡아먹는지 파악하는 데 좋다.

### 4) 문제 테이블 선별 기준

운영에서는 아래 중 두세 개가 같이 보이면 개입 신호다.

- 큰 테이블인데 `n_dead_tup`가 빠르게 증가
- `last_autovacuum`가 오래 비어 있거나 너무 드묾
- 해당 테이블 관련 쿼리 지연 증가
- 장기 트랜잭션 동반
- 인덱스 크기 증가율이 비정상적

---

## 실무 예시 1: 이벤트 적재 테이블이 점점 느려지는 경우

가정:

- `event_log` 테이블에 초당 수천 건 INSERT
- 처리 상태 업데이트도 자주 발생
- 최근 7일 데이터만 자주 조회
- 운영자는 “인덱스가 있는데 왜 느리지?”라고 느낌

이 경우 흔한 원인은 아래 조합이다.

1. UPDATE가 많아 dead tuple 누적
2. autovacuum 기본 설정으로는 변경량 추적이 느림
3. 인덱스가 많아 vacuum/index cleanup 비용 증가
4. 리포트 배치가 긴 트랜잭션으로 열려 회수 지연

대응은 보통 이렇게 간다.

### 1단계: 긴 트랜잭션 제거

가장 먼저 xact age 큰 세션을 없앤다. 원인을 제거하지 않으면 vacuum 튜닝 효과가 약하다.

### 2단계: 테이블 단위 autovacuum 주기 조정

```sql
ALTER TABLE event_log SET (
  autovacuum_vacuum_scale_factor = 0.01,
  autovacuum_vacuum_threshold = 10000,
  autovacuum_analyze_scale_factor = 0.005,
  autovacuum_analyze_threshold = 5000
);
```

### 3단계: 인덱스 재검토

- 최근 7일 조회 패턴에 맞는 인덱스만 남기는지
- UPDATE되는 컬럼을 불필요하게 인덱싱하지 않았는지
- 부분 인덱스나 파티셔닝이 더 적합하지 않은지

### 4단계: 오래된 데이터 아카이브/파티셔닝 검토

vacuum은 필요하지만, **데이터 생명주기 설계 부재**를 대신 해결해주진 않는다. 핫 데이터와 콜드 데이터를 한 테이블에 계속 쌓아두면 운영 부담은 결국 폭증한다.

---

## 실무 예시 2: “삭제 배치 후 디스크가 안 줄어요”에 대한 정답

대량 삭제 후 파일 크기가 그대로라서 놀라는 경우가 많다.

예:

```sql
DELETE FROM audit_logs
WHERE created_at < now() - interval '180 days';
```

이후 확인해보니 테이블 파일 크기는 거의 그대로다. 이때의 정답은 보통 셋 중 하나다.

### 경우 1) 이후에 비슷한 데이터가 다시 들어올 예정

굳이 파일을 즉시 줄일 필요가 없다. 일반 vacuum으로 재사용 가능 상태면 충분하다.

### 경우 2) 정말로 공간을 OS에 반환해야 함

- `VACUUM FULL`
- 테이블 재작성 계열 작업
- 운영 가능하다면 파티션 DROP/TRUNCATE 전략

이 중 하나를 검토해야 한다.

### 경우 3) 원래부터 파티셔닝이 맞았던 문제

로그/이력성 데이터는 대량 DELETE보다 **기간 파티션 + 파티션 DROP**이 훨씬 낫다. vacuum은 MVCC 부작용을 관리하는 도구이지, 모든 데이터 수명 정책을 대신해주지 않는다.

---

## 트레이드오프: autovacuum을 공격적으로 돌릴수록 무조건 좋은가?

아니다. 실무는 늘 균형이다.

### 공격적으로 돌렸을 때 장점

- dead tuple 누적 억제
- bloat 완화
- 통계 최신성 향상
- wraparound 리스크 감소

### 공격적으로 돌렸을 때 단점

- 백그라운드 I/O 증가
- CPU 사용 증가
- busy table이 너무 자주 청소되어 foreground latency에 영향 가능
- 설정이 복잡해져 운영 이해도 없는 팀에서는 원인 추적이 어려워짐

### 반대로 너무 느슨하면

- 테이블이 과도하게 커지고
- 통계가 늙고
- 장애가 누적되다가 한 번에 크게 터진다

그래서 권장 접근은 다음과 같다.

1. 전역 설정은 보수적으로 안정화
2. 문제 테이블만 개별 튜닝
3. 장기 트랜잭션/데이터 생명주기/인덱스 설계 같은 근본 원인을 함께 수정

즉, autovacuum 튜닝은 독립 과제가 아니라 **쓰기 패턴 설계, 배치 설계, 인덱스 설계, 아카이브 정책**과 연결된 일이다.

---

## 흔한 실수

### 1) autovacuum을 끄고 야간 수동 vacuum으로만 버티기

트래픽 패턴이 매우 예측 가능하지 않다면 위험하다. 낮 동안 급격히 쌓인 dead tuple은 야간 배치 한 번으로 항상 해결되지 않는다.

### 2) `VACUUM FULL`을 상시 처방처럼 쓰기

공간 회수는 강력하지만 락 비용이 매우 크다. 근본 원인 없이 반복하면 온라인 서비스에 더 큰 사고를 만든다.

### 3) 쿼리만 보고 인덱스를 계속 추가하기

읽기 성능은 잠깐 좋아질 수 있어도, 쓰기/ vacuum 비용이 폭증해 전체 시스템은 더 나빠질 수 있다.

### 4) 장기 트랜잭션을 무시하기

autovacuum 튜닝을 열심히 해도 장기 트랜잭션 하나가 모든 효과를 지울 수 있다.

### 5) Analyze 문제를 Vacuum 문제로 착각하기

실행 계획이 이상한데 dead tuple만 본다면 방향이 빗나간다. 데이터 분포가 변한 문제라면 autoanalyze 주기나 통계 대상 컬럼을 먼저 봐야 한다.

### 6) 로그/이력 테이블을 파티셔닝 없이 장기간 누적하기

삭제 배치와 vacuum만으로 버티면 결국 운영 비용이 계속 오른다. 데이터 수명 주기가 명확한 테이블은 구조적으로 풀어야 한다.

---

## 운영 체크리스트

### 증상 파악

- [ ] 최근 느려진 테이블이 UPDATE/DELETE 비중이 높은가?
- [ ] `pg_stat_user_tables`에서 `n_dead_tup`가 빠르게 쌓이는가?
- [ ] `last_autovacuum`, `last_autoanalyze`가 기대보다 드문가?

### 원인 확인

- [ ] `pg_stat_activity`에서 장기 트랜잭션 또는 `idle in transaction`이 있는가?
- [ ] 해당 테이블 인덱스가 너무 많거나, 자주 바뀌는 컬럼을 포함하는가?
- [ ] 대량 DELETE를 반복하면서 파티셔닝 없이 버티고 있지 않은가?

### 대응 설계

- [ ] 문제 테이블에만 autovacuum scale factor/threshold 개별 설정을 검토했는가?
- [ ] analyze 빈도와 통계 품질이 충분한가?
- [ ] fillfactor/HOT 관점에서 쓰기 경로를 점검했는가?
- [ ] 정말 필요한 경우에만 `VACUUM FULL` 또는 재작성 작업을 계획했는가?

### 예방 체계

- [ ] `xid_age`, `n_dead_tup`, autovacuum 지연을 모니터링하는가?
- [ ] 장기 트랜잭션 탐지 알람이 있는가?
- [ ] 로그/이력성 테이블에 기간 파티셔닝 또는 아카이브 전략이 있는가?

---

## 한 줄 정리

PostgreSQL autovacuum의 핵심은 “죽은 행을 청소한다”가 아니라, **MVCC의 부작용을 통제해 bloat·플랜 왜곡·wraparound 위험을 함께 관리하는 운영 체계**를 만드는 데 있다.
