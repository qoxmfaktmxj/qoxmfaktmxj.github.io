---
layout: post
title: "PostgreSQL autovacuum 실전: vacuum cost, dead tuples, freeze age, bloat로 쓰기 많은 테이블을 안정적으로 운영하는 법"
date: 2026-05-25 11:40:00 +0900
categories: [sql]
tags: [study, sql, postgresql, autovacuum, vacuum, bloat, freeze, dead-tuples, xid, operations, performance]
permalink: /sql/2026/05/25/study-postgresql-autovacuum-vacuum-cost-dead-tuples-freeze-bloat.html
---

## 배경: PostgreSQL은 왜 CPU보다 먼저 "죽은 튜플 청소"에서 무너질까

운영 중인 PostgreSQL에서 느린 쿼리, 높은 I/O, 커지는 디스크, 뜬금없는 `VACUUM` 로그, replica 지연, 갑자기 길어진 index scan을 보다 보면 결국 같은 질문으로 돌아오게 됩니다.

> **이 테이블은 지금 데이터를 쓰고 있는가, 아니면 이미 지워졌어야 할 과거의 흔적을 계속 끌고 다니고 있는가?**

PostgreSQL은 MVCC를 쓰기 때문에 `UPDATE`와 `DELETE`가 곧바로 기존 row를 덮어쓰지 않습니다. 그 대신 이전 버전 row가 남고, 더 이상 보이지 않게 된 버전은 나중에 vacuum이 회수합니다. 이 구조 덕분에 읽기 일관성과 동시성을 얻지만, 대가도 분명합니다.

- update-heavy 테이블은 **죽은 튜플(dead tuple)** 이 빠르게 쌓인다.
- vacuum이 제때 못 돌면 table/index **bloat** 가 커진다.
- bloat가 커지면 cache hit ratio가 괜찮아 보여도 실제 I/O와 latency가 나빠진다.
- 오래 열린 transaction 하나가 vacuum progress를 막아 freeze까지 밀어낼 수 있다.
- autovacuum worker가 부족하거나 cost 정책이 보수적이면 "늘 돌고 있는데도 못 따라가는" 상태가 된다.
- 반대로 vacuum을 너무 공격적으로 돌리면 foreground workload와 I/O를 두고 싸운다.

실무에서는 특히 이런 착시가 자주 나옵니다.

- CPU는 높지 않은데 응답 시간이 점점 나빠진다.
- `EXPLAIN` 상 논리는 비슷한데 heap fetch와 random I/O가 증가한다.
- 디스크는 충분한데 왜 테이블 크기가 줄지 않는다.
- `VACUUM`은 돌아가는데 왜 dead tuple이 줄지 않는다.
- `autovacuum`이 문제인지, 긴 transaction이 문제인지, fillfactor가 문제인지 구분이 안 된다.

이때 필요한 것은 "autovacuum 켜져 있으니 괜찮다" 수준의 이해가 아니라, **어떤 테이블이 왜 청소 속도보다 더 빨리 더러워지고 있는지, 그리고 그 청소 정책이 현재 workload와 맞는지 판단하는 운영 기준**입니다.

오늘 글은 PostgreSQL 공식 문서와 실무 패턴을 기준으로 아래 질문에 답하는 방향으로 정리합니다.

1. autovacuum은 정확히 무엇을 언제 트리거하는가?
2. dead tuple, visibility map, freeze age, bloat는 어떻게 연결되는가?
3. `autovacuum_vacuum_scale_factor`와 `autovacuum_vacuum_threshold`를 왜 테이블 크기별로 다르게 봐야 하는가?
4. `vacuum_cost_limit`, `vacuum_cost_delay`, worker 수는 언제 병목이 되는가?
5. insert-heavy 테이블과 update-heavy 테이블의 튜닝 포인트는 왜 다른가?
6. long transaction, replica feedback, idle in transaction은 왜 vacuum을 망가뜨리는가?
7. 언제 `VACUUM`, `VACUUM (ANALYZE)`, `VACUUM FULL`, `REINDEX`, `pg_repack` 같은 다른 조치를 고려해야 하는가?

핵심 결론부터 먼저 말하면 이렇습니다.

1. autovacuum은 단순 housekeeping이 아니라 **PostgreSQL write path의 일부**다.
2. 큰 테이블에 default scale factor를 그대로 두면 vacuum은 대개 "너무 늦게" 시작한다.
3. vacuum 문제는 자주 CPU 문제가 아니라 **heap/index footprint와 XID age 문제**로 나타난다.
4. worker 수와 cost 정책이 너무 보수적이면 autovacuum은 살아 있어도 workload를 못 따라간다.
5. 반대로 cost를 무작정 올리면 foreground latency와 I/O jitter를 키운다.
6. 제일 흔한 root cause는 vacuum daemon 자체보다 **긴 transaction, 잘못된 workload 패턴, 테이블별 정책 부재**다.
7. 좋은 운영은 전역 숫자 하나가 아니라 **테이블별 write 특성에 맞춘 vacuum budget 설계**다.

---

## 먼저 큰 그림: autovacuum은 성능 옵션이 아니라 MVCC 부채 상환 시스템이다

PostgreSQL의 MVCC에서는 row를 바꿀 때 과거 버전이 즉시 사라지지 않습니다. 그래서 읽는 쪽은 쓰는 쪽과 큰 락 충돌 없이 과거 snapshot을 볼 수 있습니다. 하지만 그 대가로 DB는 계속해서 두 종류의 부채를 떠안습니다.

### 1) 저장 공간 부채

`UPDATE`와 `DELETE`가 쌓일수록 더 이상 어떤 transaction에서도 필요하지 않은 row version이 남습니다.

- heap page에 죽은 row가 쌓인다.
- index entry도 함께 늘어난다.
- page density가 낮아진다.
- scan은 더 많은 page를 읽게 된다.
- cache가 같은 row 수를 담기 위해 더 큰 footprint를 써야 한다.

### 2) transaction age 부채

PostgreSQL은 transaction ID wraparound를 피하기 위해 row visibility metadata를 주기적으로 freeze 해야 합니다. 이 작업이 밀리면 단순 성능 문제가 아니라 **cluster safety 문제**가 됩니다.

즉 vacuum은 두 가지를 동시에 맡습니다.

- dead tuple 회수와 visibility maintenance
- xid age 관리와 anti-wraparound safety

이 점을 이해해야 autovacuum을 "백그라운드 청소기"가 아니라 **계속 발생하는 MVCC 부채를 갚는 엔진**으로 볼 수 있습니다.

---

## autovacuum이 하는 일: vacuum과 analyze는 비슷해 보여도 목적이 다르다

autovacuum은 이름 때문에 vacuum만 떠올리기 쉽지만 실제로는 두 계열 작업을 관리합니다.

### autovacuum의 vacuum 역할

- dead tuple 회수
- visibility map 갱신
- page를 future reuse 가능 상태로 만듦
- transaction ID / multixact age 관리
- 필요 시 aggressive vacuum / anti-wraparound vacuum 수행

### autovacuum의 analyze 역할

- 통계 갱신
- planner가 row count, distinct, correlation, most common values 등을 더 정확히 추정하도록 도움
- update/insert/delete 이후 실행 계획 품질 유지

실무에서는 둘을 섞어 말하다가 판단이 흐려집니다.

- 쿼리 플랜이 갑자기 나빠짐 → analyze 이슈일 수 있음
- 테이블/인덱스가 점점 커짐 → vacuum 이슈일 가능성이 큼
- 둘 다 밀리면 성능과 footprint가 동시에 나빠짐

그래서 autovacuum 튜닝은 항상 **회수 정책(vacuum)** 과 **통계 정책(analyze)** 를 분리해서 봐야 합니다.

---

## 핵심 개념 1: dead tuple이 많다는 말은 단순 삭제량이 아니라 "재사용되지 못한 과거"가 많다는 뜻이다

dead tuple은 단순히 `DELETE`를 많이 쳤다는 뜻이 아닙니다. 오히려 실무에서 더 흔한 원인은 `UPDATE`입니다.

예를 들어 주문 테이블에서 이런 컬럼들이 자주 바뀐다고 합시다.

- 상태
- 재시도 횟수
- 마지막 처리 시각
- 정산 플래그
- 배송 추적 상태

각 update는 기존 row version을 남깁니다. HOT update가 성립하면 index churn을 줄일 수 있지만, heap 안에는 여전히 과거 버전 부채가 생깁니다. 그리고 HOT가 깨지는 update가 많으면 index bloat까지 함께 커집니다.

이때 자주 나오는 오해가 있습니다.

> dead tuple이 많으면 그만큼 즉시 디스크가 줄어든다.

아닙니다. vacuum의 기본 목적은 OS에 파일을 반납하는 것이 아니라 **PostgreSQL 내부에서 page space를 재사용 가능 상태로 만드는 것**입니다. 그래서 dead tuple이 사라져도 파일 크기는 그대로일 수 있습니다. 그 대신 이후 insert/update가 그 공간을 reuse 하며 성능과 footprint 악화를 늦추는 방식입니다.

즉 vacuum이 성공했다는 판단은 단순 파일 크기가 아니라 아래 관점으로 봐야 합니다.

- dead tuple 비율이 줄었는가
- same table workload에서 page reuse가 되는가
- visibility가 개선되어 index-only scan 기회가 커지는가
- xid age가 안전 범위로 관리되는가

---

## 핵심 개념 2: default scale factor는 큰 테이블에서 너무 느릴 수 있다

PostgreSQL default는 범용적이지만, write-heavy production에선 자주 느슨합니다.

대표적으로 vacuum 트리거는 아래 식으로 생각할 수 있습니다.

- vacuum trigger ≈ `autovacuum_vacuum_threshold + autovacuum_vacuum_scale_factor * reltuples`
- analyze trigger ≈ `autovacuum_analyze_threshold + autovacuum_analyze_scale_factor * reltuples`

문제는 큰 테이블입니다.

예를 들어 row 수 5천만인 테이블에서 `autovacuum_vacuum_scale_factor=0.2` 라면 vacuum 시작 전 허용 dead tuple 규모가 매우 커질 수 있습니다. 이건 작은 테이블에서는 합리적이어도 큰 테이블에서는 너무 늦습니다.

왜냐하면 큰 테이블은 아래 문제가 동시에 생기기 때문입니다.

- dead tuple 수 자체가 너무 커져 page churn이 심해짐
- vacuum 한 번 돌 때 걸리는 시간이 길어짐
- vacuum이 느리게 시작할수록 한 번에 갚아야 할 부채가 커짐
- worker가 다른 큰 테이블과도 경쟁함
- analyze도 늦어져 plan quality까지 같이 흔들릴 수 있음

그래서 실무 기본 원칙은 이렇습니다.

> **큰 write-heavy 테이블일수록 scale factor를 낮추고 threshold를 상대적으로 더 명시적으로 보는 편이 낫다.**

예를 들어 자주 바뀌는 대형 테이블은 아래처럼 별도 정책을 두는 경우가 많습니다.

- 더 낮은 `autovacuum_vacuum_scale_factor`
- 더 낮은 `autovacuum_analyze_scale_factor`
- 필요하면 테이블별 `autovacuum_vacuum_cost_limit` 상향
- fillfactor 조정으로 HOT update 여지 확보

중요한 점은 모든 테이블을 공격적으로 돌리라는 뜻이 아니라, **작은 reference table과 대형 event table을 같은 숫자로 관리하지 말라**는 것입니다.

---

## 핵심 개념 3: vacuum cost는 "친절함"과 "추격력"의 균형이다

vacuum은 foreground workload와 자원을 공유합니다. 그래서 PostgreSQL은 cost-based delay를 둡니다.

핵심은 단순합니다.

- 너무 빠르게 돌면 foreground I/O와 cache locality를 해칠 수 있다.
- 너무 느리게 돌면 dead tuple accumulation을 못 따라간다.

여기서 보는 대표 설정이 아래입니다.

- `vacuum_cost_limit`
- `vacuum_cost_delay`
- autovacuum용 override (`autovacuum_vacuum_cost_limit`, `autovacuum_vacuum_cost_delay`)
- worker 수 (`autovacuum_max_workers`)
- naptime (`autovacuum_naptime`)

### cost를 너무 보수적으로 잡았을 때의 증상

- autovacuum은 계속 도는데 dead tuple이 잘 안 줄어듦
- 테이블 몇 개가 늘 backlog 상위권에 남음
- peak 시간만 지나면 미처 못 끝난 vacuum이 다음 cycle로 밀림
- anti-wraparound vacuum이 나중에 더 공격적으로 나타남
- bloat가 누적되며 결국 더 큰 maintenance가 필요해짐

### cost를 너무 공격적으로 잡았을 때의 증상

- write latency jitter 증가
- storage IOPS pressure 상승
- replica replay lag 증가 가능
- background writer / checkpoint pressure와 합쳐져 foreground tail latency 악화

그래서 실무에서 묻는 질문은 "vacuum을 빨리 돌릴까 말까"가 아니라 아래에 가깝습니다.

1. 이 workload는 지금 부채 상환 속도가 생성 속도를 따라가고 있는가?
2. backlog 상위 테이블 몇 개가 전체 footprint를 왜곡하고 있는가?
3. 전체 cluster 기본값보다 테이블별 override가 더 적절한가?
4. storage headroom과 latency budget이 어느 정도인가?

---

## insert-heavy와 update-heavy는 같은 vacuum 튜닝 문제가 아니다

최근 PostgreSQL은 insert-triggered autovacuum 관련 옵션도 제공하고, insert-only workload에도 visibility/freeze 측면 관리가 필요합니다. 하지만 여전히 운영 관점에서 insert-heavy와 update-heavy는 구분해서 봐야 합니다.

### update/delete-heavy 테이블

주요 관심사:

- dead tuple 증가
- heap bloat
- index bloat
- HOT update 성립률
- page reuse 여부
- write amplification

주요 대응:

- 낮은 vacuum scale factor
- fillfactor 조정
- 자주 바뀌는 indexed column 재검토
- partitioning / archive 분리
- worker/cost 증설

### insert-heavy append table

주요 관심사:

- analyze freshness
- visibility map / freeze progression
- 오래된 큰 table segment의 age 관리
- retention 정책과 partition drop

주요 대응:

- analyze cadence 확보
- 오래 쌓이는 partition의 freeze age 모니터링
- partition-based retention
- 필요 시 insert-triggered vacuum/analyze 정책 검토

즉 insert 위주 테이블에 update-heavy 기준 튜닝을 그대로 적용하면 쓸데없이 공격적일 수 있고, 반대로 update-heavy 테이블에 append-only 감각으로 접근하면 cleanup이 항상 늦습니다.

---

## visibility map과 index-only scan: vacuum은 단순 청소가 아니라 읽기 성능에도 관여한다

많은 팀이 vacuum을 write path maintenance로만 봅니다. 하지만 읽기 성능에도 직접 연결됩니다.

visibility map이 잘 관리되면 planner/executor는 index-only scan에서 heap 확인을 줄일 수 있습니다. 반대로 page visibility가 나쁘면 index-only scan 후보여도 실제 heap fetch가 많이 발생할 수 있습니다.

이 말은 곧 다음을 의미합니다.

- vacuum이 밀리면 단순 dead tuple 문제를 넘어 read amplification이 커질 수 있다.
- reporting query가 느려지는 원인이 planner가 아니라 visibility quality일 수 있다.
- 큰 read-heavy table도 update churn이 있으면 vacuum 품질이 읽기 효율을 흔든다.

그래서 운영 중 아래 패턴이 보이면 vacuum 관점도 함께 봐야 합니다.

- index-only scan 기대 쿼리가 heap fetch를 많이 함
- 같은 index인데 체감 latency가 점점 길어짐
- 테이블 row 수는 비슷한데 relation size와 buffer usage가 커짐

---

## freeze age와 anti-wraparound: 느린 성능 문제를 넘어 안전 문제로 가는 구간

autovacuum의 가장 중요한 safety 역할은 XID wraparound 방지입니다. 이건 optional tuning이 아닙니다.

트랜잭션 ID는 무한하지 않기 때문에 오래된 tuple metadata는 freeze 되어야 합니다. 이 작업이 계속 밀리면 PostgreSQL은 anti-wraparound vacuum을 더 강하게 수행하려고 합니다. 실무에서 이 단계까지 오면 이미 좋지 않습니다.

왜냐하면 이 구간은 보통 아래를 동반하기 때문입니다.

- backlog가 오랫동안 누적되어 있었음
- 몇몇 테이블이 장기간 vacuum unfriendly 상태였음
- 긴 transaction 또는 replica feedback가 cleanup horizon을 밀었을 수 있음
- 평소의 완만한 background maintenance 대신 더 급하고 비싼 작업이 필요해짐

즉 좋은 운영은 anti-wraparound가 잘 막아 주니까 괜찮다가 아니라,

> **그 단계까지 가지 않도록 평소 age distribution과 vacuum cadence를 관리하는 것**

입니다.

실무 체크 포인트는 아래입니다.

- age가 높은 relation 상위 목록
- autovacuum이 오래 못 끝나는 relation
- idle in transaction session 존재 여부
- logical/physical replication feedback 영향
- 오래 살아 있는 batch / ETL transaction

---

## long transaction이 왜 autovacuum을 망가뜨리는가

autovacuum 문제에서 자주 범인이 daemon 쪽으로 몰리지만, 실제로는 application/session behavior가 root cause인 경우가 많습니다.

대표적인 것이 long transaction입니다.

### 흔한 long transaction 원인

- ORM 세션이 transaction을 열고 외부 API 호출을 기다림
- 배치가 큰 범위를 한 transaction으로 처리
- 수동 SQL 세션이 `BEGIN` 후 오래 방치됨
- `idle in transaction` 커넥션이 pool 안에 남아 있음
- replica feedback가 vacuum cleanup horizon을 늦춤

이런 세션이 있으면 vacuum은 dead tuple을 당장 제거하거나 freeze를 충분히 진행하지 못할 수 있습니다. 그 결과는 아래처럼 보입니다.

- autovacuum은 실행되지만 효과가 약함
- dead tuple이 줄지 않거나 금방 다시 증가함
- age가 예상보다 빨리 올라감
- bloat가 누적됨
- table/index size가 계속 커짐

즉 autovacuum 튜닝 전에 아래 질문을 먼저 해야 합니다.

1. cleanup horizon을 미는 오래된 transaction이 있는가?
2. `idle_in_transaction_session_timeout` 같은 위생 규칙이 설정되어 있는가?
3. batch chunking이 가능한데 한 번에 너무 크게 묶고 있지 않은가?
4. replica feedback를 켰다면 그 비용을 이해하고 있는가?

---

## 실무 튜닝 접근: 전역값 하나보다 테이블 등급제를 먼저 만들어라

autovacuum은 cluster 전체 설정만으로 끝내기 쉽지만, 효과적인 운영은 테이블을 몇 가지 클래스로 나누는 것에서 시작합니다.

### A. 작은 reference / dimension table

특징:

- row 수 작음
- write 빈도 낮음
- planner 통계 중요

전략:

- 기본값 유지 가능
- analyze freshness만 확인

### B. 대형 append table

특징:

- insert 위주
- partitioning 가능성이 높음
- retention / archive 중요

전략:

- partition lifecycle 관리
- analyze cadence 확보
- freeze age 모니터링

### C. update-heavy OLTP hot table

특징:

- 상태 컬럼 자주 변경
- index도 많음
- HOT update 성립률이 중요
- dead tuple, bloat, I/O amplification이 핵심

전략:

- 낮은 vacuum/analyze scale factor
- fillfactor 조정
- 테이블별 cost limit 상향 검토
- index 구조 재평가

### D. bulk maintenance / queue-like table

특징:

- burst write
- delete/consume 패턴 강함
- vacuum backlog가 순간적으로 치솟음

전략:

- partition 또는 periodic truncate 전략 검토
- queue 소비 방식 최적화
- 필요 시 별도 maintenance window 활용

이렇게 분류해 두면 default를 맹신하는 대신 "왜 이 테이블만 매일 아픈가"를 설명할 수 있게 됩니다.

---

## fillfactor와 HOT update: autovacuum만 만지면 절반만 고친다

update-heavy 테이블에서 autovacuum이 힘든 이유는 cleanup이 느려서만이 아닙니다. **애초에 새 버전 생성 패턴이 비효율적**일 수도 있습니다.

특히 HOT update가 잘 성립하지 않으면 index churn까지 같이 늘어납니다. 이때 볼 포인트는 아래입니다.

- 자주 바뀌는 컬럼이 인덱스에 포함되어 있는가?
- page 내 여유 공간이 거의 없어 HOT chain이 잘 안 이어지는가?
- fillfactor를 너무 빡빡하게 잡아 모든 update가 page split / new page write를 유도하는가?

fillfactor를 조금 낮춰 page 내 여유 공간을 남기면 HOT update 기회를 늘릴 수 있습니다. 물론 trade-off도 있습니다.

- 더 많은 초기 disk footprint
- read locality 변화 가능성
- workload에 따라 효과가 제한적일 수 있음

하지만 write-heavy hot table에서는 fillfactor 조정이 autovacuum burden을 구조적으로 줄이는 경우가 적지 않습니다. 즉 vacuum은 증상 완화이고, fillfactor/HOT는 발생량 억제입니다.

---

## bloat를 봐야 할 때: 테이블만 보지 말고 index도 같이 봐라

실무에서 자주 하는 실수는 heap size만 보고 vacuum 상태를 판단하는 것입니다. 하지만 update-heavy workload에서는 index bloat가 더 먼저 체감되는 경우도 많습니다.

대표 증상:

- index scan이 같은 조건인데 점점 더 많은 page를 건드림
- cache pressure 증가
- write cost 증가
- checkpoint / WAL 부담 증가

여기서 중요한 사실은 일반 vacuum이 모든 index bloat 문제를 완전히 되돌리지는 않는다는 점입니다. 경우에 따라 아래 조치가 필요할 수 있습니다.

- `REINDEX` 또는 `REINDEX CONCURRENTLY`
- `pg_repack`
- schema / index 전략 재설계
- partition rotation

즉 autovacuum은 매우 중요하지만 만능은 아닙니다. 이미 많이 부풀어 오른 relation은 "앞으로 더 나빠지지 않게" 만드는 것과 "지금의 부풀음을 되돌리는 것"을 분리해서 봐야 합니다.

---

## 관측 포인트: 어디를 보면 autovacuum이 따라가는지 판단할 수 있나

운영에서 숫자를 볼 때는 아래 질문에 맞춰 지표를 묶는 편이 좋습니다.

### 1) 부채가 얼마나 쌓이고 있는가

- relation별 dead tuple 추세
- relation size / index size 증가율
- write volume 대비 tuple churn

### 2) 상환이 실제로 이뤄지고 있는가

- autovacuum 실행 빈도
- 한 번 실행 시 처리량과 duration
- 같은 relation이 반복적으로 backlog 상위에 머무는지
- worker 부족 징후

### 3) 안전이 밀리고 있는가

- relation age / frozenxid age 상위 목록
- anti-wraparound 경고 여부
- long transaction / idle in transaction 유무

### 4) 사용자 영향이 생기고 있는가

- heap fetch 증가
- index scan latency 증가
- I/O 및 temp가 아닌 relation footprint 증가
- replica lag / checkpoint pressure 동반 여부

핵심은 단일 메트릭이 아니라 **부채 생성 속도 vs 상환 속도**를 같이 보는 것입니다.

---

## 흔한 실수 1: scale factor만 낮추고 worker/cost는 그대로 둔다

이건 매우 흔합니다.

- 트리거는 더 자주 걸리게 만들었다.
- 하지만 worker 수와 처리 속도는 그대로다.
- 결과적으로 더 많은 vacuum job이 큐에 쌓인다.
- 겉보기엔 더 부지런해졌지만 실제 backlog는 줄지 않는다.

즉 트리거 민감도와 처리 용량은 같이 봐야 합니다.

- start를 앞당기면
- workers / cost / storage headroom / table별 우선순위도 함께 설계해야 합니다.

---

## 흔한 실수 2: 전역 default 하나로 모든 테이블을 해결하려 한다

작은 테이블, 큰 테이블, queue table, append table, hot OLTP table은 write profile이 다릅니다. 그런데 모든 relation에 같은 scale factor와 threshold를 두면 대개 아래 둘 중 하나가 됩니다.

- 큰 hot table에는 너무 늦다.
- 작은 조용한 table에는 너무 잦다.

실무에서는 보통 전역 기본값은 "무난한 바닥선" 으로 두고, 진짜 문제 relation만 per-table storage parameter로 조정하는 접근이 더 현실적입니다.

---

## 흔한 실수 3: vacuum 문제를 쿼리 튜닝만으로 해결하려 한다

query tuning은 중요합니다. 하지만 아래 문제는 SQL 개선만으로는 충분하지 않을 수 있습니다.

- dead tuple 과다
- relation footprint 증가
- xid age 상승
- long transaction으로 인한 cleanup block
- index bloat

예를 들어 쿼리 하나를 800ms에서 200ms로 줄여도, 테이블이 원래보다 4배 부풀어 있고 vacuum backlog가 계속 쌓이면 몇 주 뒤 같은 문제가 다른 쿼리로 다시 돌아옵니다.

---

## 흔한 실수 4: VACUUM FULL을 "청소 버튼"처럼 쓴다

`VACUUM FULL`은 실제 파일 축소가 필요할 때 강력하지만, 일반 autovacuum 대체재가 아닙니다. 더 무겁고 락 영향도 큽니다. 그래서 아래처럼 판단해야 합니다.

### 보통 먼저 볼 것

- 일반 vacuum cadence 개선
- table별 autovacuum 정책 조정
- fillfactor / HOT 개선
- long transaction 제거
- partitioning / retention 정리

### 그 다음 고려할 것

- relation이 이미 심하게 부풀어 있고
- 단순 reuse로는 부족하며
- maintenance window가 있고
- rewrite 비용과 lock 영향을 감수할 수 있을 때

즉 `VACUUM FULL`은 운영 전략이 아니라 복구 수단에 가깝습니다.

---

## 실무 체크리스트: 쓰기 많은 테이블의 autovacuum을 볼 때 순서

### 1. 가장 먼저 workload를 분류한다

- append-heavy인가
- update-heavy인가
- queue/delete-heavy인가
- partition 가능한가

### 2. backlog relation을 찾는다

- dead tuple 상위
- age 상위
- size 증가 상위
- autovacuum duration 상위

### 3. 긴 transaction과 replica 영향부터 제거한다

- idle in transaction
- batch giant transaction
- feedback horizon

### 4. per-table 정책을 검토한다

- vacuum scale factor
- analyze scale factor
- threshold
- cost limit
- fillfactor

### 5. worker capacity와 storage budget을 함께 본다

- worker 수
- cost policy
- IOPS 여유
- foreground latency 영향

### 6. 이미 생긴 bloat는 별도 계획으로 다룬다

- REINDEX
- pg_repack
- partition rotation
- maintenance window

---

## 추천 접근 예시: 기본값 유지 vs 적극 조정

### 경우 A. 작은 서비스, 쓰기량 낮음

- 기본 autovacuum 설정 유지 가능
- 다만 long transaction 차단은 필수
- analyze freshness와 age만 정기 점검

### 경우 B. 중간 규모 OLTP, 몇 개 hot table 존재

추천:

- 전역 기본값은 과격하게 바꾸지 않음
- hot table만 scale factor 하향
- fillfactor 조정 검토
- autovacuum logs와 dead tuple trend 관측
- worker/cost를 소폭 상향

### 경우 C. 대규모 write-heavy 서비스

추천:

- relation class별 vacuum 정책 문서화
- hot table per-table override 적극 사용
- partitioning / retention 전략 병행
- anti-wraparound / age 대시보드 별도 운영
- reindex / repack playbook 준비
- app transaction hygiene를 SLO 수준으로 관리

---

## 한 줄 정리

> **PostgreSQL autovacuum 튜닝의 핵심은 청소를 더 자주 시키는 것이 아니라, MVCC 부채가 생성되는 속도와 상환되는 속도를 relation별로 균형 맞추는 것이다.**

---

## 마무리

autovacuum은 잘 돌 때 존재감이 거의 없습니다. 그래서 많은 팀이 문제를 겪기 전까지는 중요도를 과소평가합니다. 하지만 PostgreSQL 운영에서 autovacuum은 optional background task가 아니라, write-heavy workload를 장기적으로 버티게 만드는 핵심 장치입니다.

정리하면 이렇게 기억하면 좋습니다.

- dead tuple은 삭제 흔적이 아니라 미래 성능을 갉아먹는 footprint 부채다.
- 큰 테이블에 default scale factor를 그대로 두면 vacuum이 늦을 가능성이 높다.
- worker/cost 없이 trigger만 민감하게 만들면 backlog만 늘 수 있다.
- long transaction과 replica feedback는 autovacuum을 조용히 망가뜨리는 대표 원인이다.
- 이미 커진 bloat는 autovacuum만으로 완전히 되돌리지 못할 수 있다.
- 가장 현실적인 접근은 전역값 하나가 아니라 **문제 relation에 대한 테이블별 운영 정책**이다.

읽기 성능이 조금씩 나빠지고, relation size가 은근히 커지고, autovacuum 로그가 자주 보이기 시작했다면 그건 "청소가 열심히 되고 있다"는 신호일 수도 있지만, 반대로 **이미 부채가 커지고 있다는 조기 경보**일 수도 있습니다.

좋은 운영은 그 신호를 CPU 100%가 되기 전에 읽는 데서 시작합니다.
