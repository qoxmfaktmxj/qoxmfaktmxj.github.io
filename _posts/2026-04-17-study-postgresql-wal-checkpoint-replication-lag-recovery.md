---
layout: post
title: "PostgreSQL WAL과 체크포인트 실전: 쓰기 폭증, Replication Lag, pg_wal 디스크 증가를 운영 기준으로 읽는 법"
date: 2026-04-17 11:40:00 +0900
categories: [sql]
tags: [study, sql, postgresql, wal, checkpoint, replication, replication-lag, recovery, performance, operations]
permalink: /sql/2026/04/17/study-postgresql-wal-checkpoint-replication-lag-recovery.html
---

## 배경: 왜 PostgreSQL 장애는 느린 쿼리보다 WAL과 체크포인트에서 더 자주 길게 번질까

운영 중인 PostgreSQL에서 아래 같은 장면을 한 번쯤 보게 된다.

- 평소에는 응답이 괜찮다가 배치 시간만 되면 쓰기 지연이 갑자기 커진다.
- CPU는 아직 버틸 만한데 디스크 write, fsync latency, replication lag가 동시에 튄다.
- 대량 `UPDATE` 한 번 돌렸을 뿐인데 `pg_wal` 디렉터리가 예상보다 빠르게 불어난다.
- primary는 살아 있는데 replica가 몇 분, 몇십 분씩 따라오지 못한다.
- 장애 복구 이후 한동안 I/O가 진정되지 않고, checkpoint warning이 로그에 반복된다.
- autovacuum, 인덱스 생성, 배치 upsert, CDC, 백업, 아카이빙이 서로 간섭하면서 원인을 한 번에 파악하기 어려워진다.

이때 많은 팀이 먼저 보는 것은 느린 SQL 목록이다. 그 자체는 맞는 방향이다. 다만 쓰기 시스템 관점에서 보면 PostgreSQL의 병목은 단순히 “쿼리가 무거운가”로 끝나지 않는다. **어떤 쓰기가 얼마나 많은 WAL을 만들고, 체크포인트 주기와 full-page image가 어떤 I/O 패턴을 만들며, replica와 archiver가 그 속도를 따라오는지**까지 같이 봐야 한다.

즉 실무에서 중요한 질문은 이런 쪽이다.

- PostgreSQL에서 WAL은 정확히 무엇을 위해 존재하는가
- 체크포인트는 왜 필요하고, 왜 때로는 성능 스파이크의 출발점이 되는가
- `max_wal_size`, `checkpoint_timeout`, `checkpoint_completion_target`는 실제로 어떤 운영 감각으로 조정해야 하는가
- `full_page_writes`, `wal_compression`, `synchronous_commit`은 무엇을 바꾸고 무엇을 바꾸지 못하는가
- replication lag는 네트워크 문제가 아니라 어떤 쓰기 패턴과 설정 조합에서 구조적으로 커지는가
- `pg_wal`이 커지는 현상은 언제 정상이고, 언제 위험 신호인가
- 실무에서 먼저 봐야 할 메트릭과 흔한 오판은 무엇인가

오늘 글은 PostgreSQL의 WAL과 체크포인트를 “설명형 개론”이 아니라 **운영 중 쓰기 폭증, 디스크 증가, replica 지연, 복구 시간까지 연결해서 읽는 실전 기준**으로 정리한다.

핵심만 먼저 압축하면 이렇다.

1. PostgreSQL의 모든 변경은 거의 결국 WAL을 남기며, **쓰기 성능 문제의 상당수는 데이터 파일보다 먼저 WAL 생성과 flush 패턴에서 신호가 나타난다**.
2. 체크포인트는 필수이지만, 너무 잦으면 **full-page write 증가와 랜덤 I/O 청소 비용** 때문에 시스템을 흔들 수 있다.
3. `pg_wal` 용량 증가는 단순 낭비가 아니라 **checkpoint, replica 소비 속도, archive 상태, replication slot 보존 요구**가 반영된 결과다.
4. replication lag는 단지 네트워크 속도가 아니라 **primary의 WAL 생성 속도, replica의 replay 속도, long transaction, slot 보존, 대량 변경 패턴**의 합으로 결정된다.
5. 운영 튜닝의 목표는 WAL을 무조건 적게 만드는 것이 아니라 **필요한 durability를 유지하면서 쓰기 피크를 평탄화하고, replica와 archive가 따라올 수 있는 구조를 만드는 것**이다.
6. 느린 장애 대응의 원인은 종종 쿼리 자체보다 **메트릭을 잘못 읽는 것**이다. `checkpoints_req`, WAL bytes, replay lag, slot retained WAL, archive backlog를 같이 봐야 한다.

---

## 먼저 큰 그림: WAL은 "변경 기록", 체크포인트는 "복구 출발점 정리"다

WAL, 즉 Write-Ahead Log는 이름 그대로 **데이터 파일보다 앞서 기록되는 변경 로그**다. PostgreSQL이 페이지를 바로 디스크에 덮어쓰지 않고도 crash-safe하게 동작할 수 있는 핵심이 여기에 있다.

아주 단순화하면 흐름은 이렇다.

1. 트랜잭션이 데이터를 변경한다.
2. 변경된 버퍼 페이지는 shared buffers 안에서 먼저 더러워진다.
3. 변경 사실은 WAL record로 생성된다.
4. 커밋 시점에는 필요한 WAL이 먼저 durable storage에 flush된다.
5. 실제 데이터 파일 반영은 나중에 background writer나 checkpoint 과정에서 일어난다.
6. 장애가 나면 마지막 체크포인트 이후의 WAL을 재적용해서 일관된 상태를 복구한다.

이 구조 덕분에 PostgreSQL은 두 가지를 동시에 얻는다.

- 매 변경마다 데이터 파일 전체를 즉시 동기화하지 않아도 된다.
- 장애가 나도 WAL replay를 통해 committed change를 복구할 수 있다.

하지만 이 구조는 곧 이런 뜻이기도 하다.

> **쓰기 부하가 커질수록 데이터 파일 쓰기만이 아니라 WAL 생성량, WAL flush 빈도, 체크포인트 이후의 dirty page 정리 비용이 함께 커진다.**

그래서 운영 중 쓰기 성능을 볼 때는 “테이블에 얼마나 많이 썼는가”보다 먼저 “WAL이 얼마나, 어떤 패턴으로 생성되고 소모되는가”를 같이 봐야 한다.

---

## 핵심 개념 1: WAL은 단순 로그가 아니라 durability, recovery, replication의 공통 기반이다

WAL을 성능 문제의 부산물 정도로 보면 판단이 꼬인다. PostgreSQL에서 WAL은 적어도 세 역할을 동시에 수행한다.

### 1) 장애 복구

primary가 비정상 종료되면 PostgreSQL은 마지막 checkpoint 이후 WAL을 replay해서 committed change를 되살린다. 즉 WAL은 crash recovery의 재료다.

### 2) 복제

streaming replication에서 replica는 primary가 만든 WAL을 받아서 같은 변경을 재생한다. 즉 WAL은 replica 동기화의 transport format이기도 하다.

### 3) PITR과 아카이빙

WAL archive를 보관하면 특정 시점 복구, 즉 Point-in-Time Recovery가 가능해진다. 이 경우 WAL은 백업 체인의 일부가 된다.

이 세 역할 때문에 WAL을 볼 때는 늘 아래 질문을 같이 해야 한다.

- 이 시스템은 얼마나 강한 durability를 요구하는가
- replica가 몇 대고, 동기/비동기 정책은 무엇인가
- WAL archive를 통한 PITR을 운영하는가
- logical replication, CDC, Debezium, slot 기반 소비자가 있는가

같은 200MB/s WAL 생성이라도, 단일 DB와 다수 replica + archive + logical slot 환경은 운영 의미가 완전히 다르다.

---

## 핵심 개념 2: 체크포인트는 필요하지만, 너무 잦으면 WAL과 I/O를 동시에 악화시킨다

체크포인트는 dirty buffer를 데이터 파일에 반영하고, 복구 시작점을 앞으로 당기는 작업이다. 체크포인트가 없으면 장애 시 너무 긴 WAL을 처음부터 replay해야 하므로 복구 시간이 감당되지 않는다.

하지만 체크포인트는 공짜가 아니다.

- dirty page를 디스크에 써야 한다.
- 체크포인트 직후에는 각 페이지의 첫 수정에서 full-page image가 더 많이 기록될 수 있다.
- write burst를 잘못 만들면 backend fsync와 체크포인트 쓰기가 경쟁한다.
- 자주 일어날수록 전체 WAL 양과 랜덤 I/O 부담이 오히려 증가할 수 있다.

여기서 중요한 개념이 **full-page write**다.

PostgreSQL은 torn page 문제를 피하기 위해, 체크포인트 이후 어떤 페이지가 처음 수정될 때 그 페이지의 전체 이미지를 WAL에 기록할 수 있다. 이 기능이 `full_page_writes`다. 기본적으로 매우 중요하고, 대부분의 운영 환경에서는 꺼서는 안 된다.

문제는 체크포인트가 너무 자주 발생하면, 많은 페이지가 “체크포인트 이후 첫 수정” 상태를 반복해서 만나게 된다는 점이다. 그러면 full-page image가 늘고 WAL 부피도 커진다.

즉 아래 연쇄가 가능하다.

1. `max_wal_size`가 작거나 쓰기 폭증으로 checkpoint requested가 자주 발생한다.
2. 체크포인트가 너무 자주 돈다.
3. 체크포인트 직후 첫 수정 페이지가 많아진다.
4. full-page write가 늘어나 WAL bytes가 증가한다.
5. WAL archive, replica apply, 디스크 flush 부담이 같이 커진다.
6. 시스템은 더 빨리 다음 checkpoint 조건에 닿는다.

실무에서 “checkpoint를 빨리 자주 하면 안전하지 않을까?”라는 생각이 위험한 이유가 여기 있다. 복구 시간은 짧아질 수 있지만, **운영 중 쓰기 안정성은 나빠질 수 있다**.

---

## 핵심 개념 3: `pg_wal`이 커진다는 것은 "삭제를 못 하는 이유가 있다"는 뜻이다

초급 단계에서는 `pg_wal` 디렉터리가 커지면 그냥 이상 현상처럼 보인다. 하지만 PostgreSQL 입장에서 WAL 파일은 아무 이유 없이 남지 않는다. 대개 다음 네 가지 중 하나 이상 때문이다.

### 1) 아직 checkpoint와 recycling 조건이 충족되지 않음

WAL 세그먼트는 바로 지워지기보다 재사용된다. `min_wal_size`, 최근 부하 패턴, 체크포인트 상태에 따라 일정량 유지되는 것은 정상이다.

### 2) replica가 아직 그 WAL까지 소비하지 못함

streaming replication에서 느린 replica가 있으면 필요한 WAL은 보존된다. 특히 replication slot을 쓰면 해당 consumer가 따라올 때까지 WAL 제거가 제한된다.

### 3) archive가 아직 완료되지 않음

`archive_mode=on` 환경에서는 archive command가 WAL을 외부 저장소로 넘길 때까지 보존이 필요하다. archive 지연이나 실패가 있으면 `pg_wal`이 계속 쌓일 수 있다.

### 4) logical slot 또는 CDC consumer가 늦음

Debezium 같은 논리 복제 소비자가 멈추거나 느리면 slot의 restart LSN이 앞으로 가지 않는다. 그러면 오래된 WAL이 계속 필요하다고 판단되어 `pg_wal`이 커진다.

그래서 `pg_wal` 증가를 보면 먼저 삭제부터 고민할 게 아니라 **누가 이 WAL을 아직 필요로 하는지**를 추적해야 한다.

대표적으로 확인할 질문은 다음과 같다.

- `pg_stat_replication`에서 어떤 replica의 write/flush/replay lag가 큰가
- `pg_replication_slots`에서 retained WAL이 비정상적으로 큰 slot이 있는가
- archive command 실패나 backlog가 있는가
- 최근 대량 쓰기나 인덱스 생성, backfill, bulk delete, vacuum freeze가 있었는가

---

## 핵심 개념 4: WAL 병목은 "얼마나 많이 쓰는가"보다 "어떤 방식으로 쓰는가"에서 커진다

같은 1억 건 변경이라도 WAL 패턴은 크게 달라질 수 있다.

### 비교 1, 짧은 트랜잭션 다수 vs 초대형 단일 트랜잭션

짧은 트랜잭션은 커밋 오버헤드는 있지만, replica apply와 장애 복구 관점에서는 더 다루기 쉬운 경우가 많다. 반면 초대형 단일 트랜잭션은 중간 가시화가 안 되고, replica apply, vacuum, crash recovery, lock 유지 시간에 불리하다.

### 비교 2, append-only insert vs random update

append 중심 적재는 상대적으로 페이지 locality가 좋아 WAL과 data file 패턴이 예측 가능한 편이다. 반면 넓은 범위 random update는 더 많은 페이지를 건드리고 full-page image를 많이 유발할 수 있다.

### 비교 3, chunked backfill vs 한 방 update

예를 들어 이런 SQL은 보기엔 단순하지만 운영에서는 매우 비싸다.

```sql
UPDATE orders
SET normalized_status = ...
WHERE normalized_status IS NULL;
```

수천만 행 테이블에서 이 한 줄은 아래를 동시에 일으킬 수 있다.

- 엄청난 WAL 생성
- long-running transaction
- replica lag 확대
- vacuum 부담 증가
- lock 대기와 dead tuple 누적
- 장애 시 긴 recovery

같은 목적이라도 범위를 나눠서 청크 단위로 처리하면 훨씬 다루기 쉬워진다.

```sql
UPDATE orders
SET normalized_status = ...
WHERE id > :last_id
  AND id <= :last_id + :chunk_size
  AND normalized_status IS NULL;
```

핵심은 “총 작업량”만이 아니라 **WAL 생성 속도와 시스템 흡수 속도의 균형**이다.

---

## 핵심 개념 5: replication lag는 수신, flush, replay 중 어디가 느린지 분해해서 봐야 한다

replica가 뒤처진다고 해서 다 같은 lag가 아니다. PostgreSQL 복제는 대략 아래 단계로 볼 수 있다.

1. primary가 WAL 생성
2. replica가 WAL 수신
3. replica가 WAL flush
4. replica가 WAL replay

실무에서는 자주 “lag가 있다”로만 말하지만, 느린 위치에 따라 원인이 완전히 달라진다.

### 1) 전송 지연이 큰 경우

- 네트워크 대역폭 부족
- 네트워크 지연 증가
- primary의 WAL sender 포화
- replica 측 수신 문제

### 2) flush 지연이 큰 경우

- replica 디스크 성능 부족
- WAL 저장소의 fsync latency 증가
- 스토리지 burst credit 고갈

### 3) replay 지연이 큰 경우

- replica CPU 부족
- 긴 쿼리가 replay를 막는 recovery conflict
- random I/O가 심한 변경 패턴
- 대량 DDL, 인덱스 생성, vacuum 관련 작업 영향
- huge transaction replay 부담

즉 replica lag를 볼 때는 “네트워크가 느린가요?”보다 먼저 **receive lag인지, flush lag인지, replay lag인지**를 분리해야 한다.

실무에서는 아래 뷰를 자주 같이 본다.

```sql
SELECT
  application_name,
  state,
  sync_state,
  sent_lsn,
  write_lsn,
  flush_lsn,
  replay_lsn,
  write_lag,
  flush_lag,
  replay_lag
FROM pg_stat_replication;
```

logical slot이나 CDC까지 보면 이것만으로 부족하고 slot 보존량도 봐야 한다.

```sql
SELECT
  slot_name,
  slot_type,
  active,
  restart_lsn,
  confirmed_flush_lsn
FROM pg_replication_slots;
```

운영에서 정말 위험한 것은 단순 lag 수치보다 **lag가 줄지 않는 방향으로 누적되는 구조**다.

---

## 실무 예시 1: 배치 UPDATE 하나가 checkpoint storm와 replica lag를 같이 만든 경우

상황을 가정해보자.

- `orders` 테이블 8천만 행
- nightly batch가 상태 컬럼 정규화 backfill 수행
- replica 2대, 비동기 복제
- PITR용 archive 활성화
- `max_wal_size`가 비교적 작게 설정됨

팀은 아래 SQL을 야간에 한 번 실행했다.

```sql
UPDATE orders
SET status_code = CASE ... END
WHERE status_code IS NULL;
```

문제는 이 작업이 단지 한 쿼리 느림으로 끝나지 않는다는 점이다.

### 실제로 벌어질 수 있는 일

1. 대량 row update로 WAL이 빠르게 생성된다.
2. `max_wal_size` 임계에 빨리 닿아 requested checkpoint가 증가한다.
3. 체크포인트가 자주 발생하면서 full-page write가 더 많이 붙는다.
4. WAL 양이 더 커지고 archiver와 replica가 밀린다.
5. replica replay lag가 커지고, 읽기 분산 트래픽이 stale해진다.
6. primary 디스크 flush latency가 튀고 앱 쓰기 응답도 흔들린다.

### 이 상황에서 먼저 봐야 할 것

- `checkpoints_req`가 평소보다 급증했는가
- `checkpoint_write_time`, `checkpoint_sync_time`가 비정상적으로 커졌는가
- WAL bytes/sec가 평소 배치 시간 대비 얼마나 증가했는가
- replica별 `replay_lag`가 줄어드는지, 계속 벌어지는지
- archive backlog가 생겼는가
- long transaction 하나가 너무 오래 잡혀 있는가

### 더 나은 접근

- 작업을 PK 범위 기반 청크로 나눈다.
- 각 청크 사이에 짧은 간격을 둬 replica와 archive가 따라오게 한다.
- 필요 시 배치 동시성을 줄여 WAL burst를 제어한다.
- 변경 중 `pg_stat_replication`, WAL rate, checkpoint 지표를 같이 본다.
- 배치 전후로 `max_wal_size`와 체크포인트 관련 설정이 현재 부하와 맞는지 재검토한다.

포인트는 “배치를 야간에 돌렸으니 괜찮다”가 아니라 **배치가 시스템의 WAL 흡수 속도를 넘었는가**다.

---

## 실무 예시 2: `pg_wal` 디스크가 계속 늘어나는데 원인은 느린 replica가 아니라 logical slot이었다

또 다른 흔한 시나리오는 이렇다.

- primary의 디스크 사용량이 며칠째 증가한다.
- replica lag는 눈에 띄게 크지 않다.
- 앱 트래픽은 평소 수준이다.
- `pg_wal` 디렉터리만 유독 빠르게 늘어난다.

이때 “checkpoint를 더 자주 돌리자” 같은 대응은 틀릴 가능성이 높다. 원인이 logical slot일 수 있기 때문이다.

예를 들어 Debezium connector가 장애로 멈췄다고 해보자. 그러면 slot의 `confirmed_flush_lsn`이 앞으로 가지 않는다. PostgreSQL 입장에서는 해당 consumer가 과거 WAL을 아직 읽지 않았다고 판단하므로, 필요한 WAL 세그먼트를 지울 수 없다.

이 경우 특징은 아래와 같다.

- replica streaming lag는 작거나 정상일 수 있다.
- 하지만 특정 logical slot의 retained WAL이 계속 증가한다.
- 앱은 문제없어 보여도 디스크는 계속 차오른다.
- 디스크가 임계치에 닿으면 primary 전체가 위험해진다.

실무 기준으로는 다음을 빠르게 확인해야 한다.

```sql
SELECT
  slot_name,
  slot_type,
  active,
  restart_lsn,
  confirmed_flush_lsn
FROM pg_replication_slots;
```

그리고 운영 관점에서는 질문이 바뀐다.

- 이 slot consumer는 살아 있는가
- 재시작하면 따라잡을 수 있는가
- backlog가 너무 커서 사실상 새로 snapshot을 떠야 하는가
- slot을 유지하는 비용이 primary 디스크 위험보다 작은가

복제와 CDC를 붙일 때 많은 팀이 replica lag만 알림으로 걸고, slot retained WAL은 놓친다. 그런데 실제 운영 사고는 후자에서 더 자주 길게 난다.

---

## 핵심 개념 6: `synchronous_commit`, `full_page_writes`, `wal_compression`은 모두 의미가 다르다

이 세 설정은 자주 같이 언급되지만, 해결하는 문제가 다르다.

### `synchronous_commit`

트랜잭션 커밋 시 WAL flush 확인 강도를 조절한다. 낮추면 커밋 latency는 줄 수 있지만, 최근 커밋 몇 건 손실 가능성을 받아들이는 방향이다. 즉 **latency와 durability의 교환**이다.

중요한 점은 이것이 WAL 생성량 자체를 크게 줄이는 설정은 아니라는 것이다. 주로 **커밋 대기 시간과 flush 타이밍**에 영향을 준다.

### `full_page_writes`

페이지 찢김(torn page) 방지와 crash recovery 안전성을 위한 핵심 설정이다. 일반 운영 환경에서는 끄지 않는 것이 원칙에 가깝다. 이걸 꺼서 WAL을 줄이려는 시도는 대개 매우 위험하다.

즉 이것은 성능 최적화 스위치라기보다 **안전장치**다.

### `wal_compression`

full-page image 같은 WAL 레코드 부피를 줄이는 데 도움을 줄 수 있다. 특히 업데이트가 넓은 페이지 범위에 퍼지고 full-page image 비중이 클 때 효과가 있다. 다만 CPU 비용과 압축 이득의 균형을 봐야 한다.

즉 이것은 **WAL 부피와 CPU의 교환**에 가깝다.

실무에서 흔한 오해는 아래다.

- `synchronous_commit=off` 하면 WAL 문제가 해결된다
- `full_page_writes=off` 하면 쓰기 성능이 좋아지니 괜찮다
- `wal_compression=on`이면 checkpoint 부담이 사라진다

셋 다 틀린 단순화다. 각각 다른 축을 조정하는 옵션일 뿐이고, **부하 원인 분석 없이 설정만 바꾸면 병목 위치만 이동**하는 경우가 많다.

---

## 운영에서 먼저 볼 메트릭: "쿼리 수"보다 "WAL 생성 속도와 소모 속도"를 같이 본다

아래 지표들은 같이 봐야 의미가 있다.

### 1) 체크포인트 빈도와 강제 여부

- `checkpoints_timed`
- `checkpoints_req`
- `checkpoint_write_time`
- `checkpoint_sync_time`

핵심 해석은 이렇다.

- `checkpoints_req` 비중이 높으면 `max_wal_size`나 WAL burst가 현재 부하와 안 맞을 수 있다.
- `checkpoint_sync_time`이 크면 스토리지 fsync 구간이 병목일 수 있다.
- 체크포인트 횟수 자체보다 **강제 checkpoint가 얼마나 자주 터지는가**가 더 중요하다.

### 2) WAL 생성량

PostgreSQL 버전에 따라 `pg_stat_wal`에서 WAL bytes를 볼 수 있다.

- 초당 WAL bytes
- WAL records / FPI 비중
- 특정 배치 시간대 급증 패턴

이 지표가 중요한 이유는 앱 QPS보다 먼저 쓰기 시스템 압박을 보여주기 때문이다.

### 3) 복제 지연

- `write_lag`
- `flush_lag`
- `replay_lag`
- replica별 LSN gap

중요한 것은 단일 숫자보다 **어느 단계에서 지연이 커졌는지**다.

### 4) slot backlog와 archive backlog

- logical slot retained WAL
- archive success/failure
- archive queue 증가 여부

많이 놓치는 포인트다. replica가 정상이어도 slot이나 archive가 WAL 보존을 붙잡고 있을 수 있다.

### 5) 디스크 레이턴시와 fsync 시간

WAL 문제는 결국 storage 문제와 자주 만난다.

- WAL 디바이스 write latency
- data volume write latency
- burst credit 고갈 여부
- VM/클라우드 스토리지 throttling 여부

WAL 생성량이 많아도 저장소가 받쳐주면 버틸 수 있고, 생성량이 중간이어도 fsync가 불안정하면 장애처럼 보일 수 있다.

---

## 튜닝 포인트 1: `max_wal_size`는 "많이 쓰지 마"가 아니라 "burst를 얼마나 흡수할 거냐"에 가깝다

`max_wal_size`를 너무 작게 두면 requested checkpoint가 잦아질 수 있다. 그렇다고 무한정 크게 잡으면 crash recovery 시간이 늘 수 있고, 디스크 사용량 관리가 어려워진다.

실무 감각은 아래에 가깝다.

- 쓰기 burst가 분명한 시스템이라면 너무 작은 `max_wal_size`는 해롭다.
- 낮 시간 피크, 배치 시간, 마이그레이션 시간대의 WAL rate를 보고 흡수 가능한 범위를 잡아야 한다.
- 목표는 checkpoint를 아예 없애는 게 아니라 **불필요하게 자주 강제되지 않게 만드는 것**이다.

즉 기본값을 외우는 것보다, 우리 시스템이 피크 10분 동안 얼마나 많은 WAL을 만드는지 아는 편이 훨씬 중요하다.

---

## 튜닝 포인트 2: `checkpoint_completion_target`은 쓰기 비용을 시간축으로 펴는 장치다

체크포인트가 꼭 필요하다면, 그 비용이 짧은 시간에 몰리지 않게 해야 한다. `checkpoint_completion_target`은 다음 체크포인트 전까지 어느 정도 비율의 시간에 걸쳐 체크포인트 쓰기를 분산할지 결정한다.

값을 높이면 보통 write burst를 완화하는 데 도움을 준다. 다만 이것이 디스크가 원래 못 버티는 총 작업량을 없애주는 것은 아니다. **같은 양의 청소를 더 부드럽게 나눠 쓰는 것**에 가깝다.

실무에서는 다음처럼 본다.

- checkpoint가 짧은 시간에 몰려 latency spike를 만든다면 높이는 것이 유리할 수 있다.
- 이미 전체 디스크 throughput이 한계라면 분산만으로는 부족하고, 쓰기 패턴 자체를 바꿔야 한다.

---

## 튜닝 포인트 3: `wal_compression`은 특히 full-page image 비중이 큰 환경에서 검토 가치가 있다

`wal_compression`은 흔히 “켜면 좋은가요?” 질문으로 소비되지만, 실무적으로는 아래 상황에서 특히 의미가 있다.

- 체크포인트 이후 첫 수정 페이지가 많다.
- update 중심 워크로드라 full-page image가 많이 생긴다.
- WAL 저장 공간 또는 네트워크 복제 대역폭이 민감하다.

하지만 CPU 여유가 넉넉하지 않거나, 실제 WAL의 병목이 compression 이득보다 다른 곳에 있으면 체감이 작을 수 있다. 따라서 이상적인 접근은 **켜보기 전에 WAL 생성 구성과 CPU 여유를 같이 보는 것**이다.

---

## 튜닝 포인트 4: 큰 트랜잭션 하나보다 관측 가능한 작은 트랜잭션 여러 개가 운영에 유리하다

이 원칙은 WAL, replication, recovery, lock, vacuum 거의 모든 축에서 반복된다.

### 작은 트랜잭션이 유리한 이유

- replica가 중간중간 따라붙기 쉽다.
- 장애 시 미적용 WAL 범위를 관리하기 쉽다.
- lock 점유 시간을 줄이기 좋다.
- batch progress를 추적하고 재시도하기 쉽다.
- long transaction이 vacuum을 막는 부작용을 줄이기 쉽다.

물론 너무 잘게 쪼개면 commit overhead가 늘고 애플리케이션 복잡도가 커질 수 있다. 그래서 핵심은 무조건 잘게가 아니라 **시스템이 흡수 가능한 크기와 동시성을 찾는 것**이다.

---

## 트레이드오프 정리: WAL과 체크포인트 튜닝은 항상 둘 이상을 맞바꾼다

| 선택 | 얻는 것 | 잃는 것 또는 주의점 |
| --- | --- | --- |
| `max_wal_size` 증가 | 잦은 강제 checkpoint 완화 | 디스크 사용량 증가 가능, 복구 시간 증가 가능 |
| `checkpoint_completion_target` 증가 | write burst 완화 | 총 작업량은 그대로, 너무 느리면 다음 주기와 겹침 주의 |
| `wal_compression=on` | WAL 부피 감소 가능 | CPU 비용 증가 |
| `synchronous_commit` 완화 | commit latency 감소 | 일부 최근 커밋 손실 가능성 |
| chunked batch | lag와 WAL burst 제어 쉬움 | 애플리케이션 로직 복잡도 증가 |
| 큰 단일 트랜잭션 | 구현 단순 | lag, recovery, vacuum, lock 측면 불리 |
| slot 유지 | CDC 연속성 보장 | consumer 장애 시 `pg_wal` 디스크 압박 |

운영에서 좋은 설정은 “최대한 빠른 설정”이 아니라 **우리 서비스의 데이터 손실 허용치, 복구 목표, 복제 구조, 스토리지 한계에 맞는 설정**이다.

---

## 흔한 실수 1: replication lag를 replica 한 대의 문제로만 본다

실제로는 primary의 WAL 생성 속도가 replica 처리 속도를 계속 넘는 구조일 수 있다. 이 경우 replica를 재시작하거나 네트워크만 점검해도 근본 해결이 안 된다.

질문은 이렇게 바꿔야 한다.

- 지금 lag의 원인은 replica가 느린 것인가
- 아니면 primary가 너무 빠르게 WAL을 쏟아내는가

둘은 대응이 다르다. 후자라면 batch throttling, chunking, 체크포인트 조정, 대량 작업 순서 재설계가 필요하다.

---

## 흔한 실수 2: `pg_wal`이 늘면 오래된 파일을 수동 삭제하고 싶어진다

매우 위험하다. 필요한 WAL을 억지로 지우면 복제나 복구 체인이 깨질 수 있다. `pg_wal` 증가의 원인을 확인하지 않고 파일부터 건드리는 것은 거의 최악의 대응이다.

먼저 해야 할 일은 다음이다.

- slot backlog 확인
- replica lag 확인
- archive 상태 확인
- 최근 대량 작업 확인
- 디스크 임계치와 회복 가능 시간 계산

즉 `pg_wal`은 증상이지 원인 자체가 아니다.

---

## 흔한 실수 3: checkpoint warning을 봤는데도 쿼리 튜닝만 한다

예를 들어 로그에 checkpoint가 너무 자주 발생한다는 경고가 나오고 있다면, 이는 단순 SQL 느림을 넘어 **현재 WAL burst와 checkpoint 설정이 부하에 맞지 않는다**는 신호일 수 있다.

물론 과도한 쓰기를 유발하는 쿼리를 줄이는 것도 중요하다. 하지만 그와 별개로 체크포인트 정책과 스토리지 특성을 같이 봐야 한다. 한쪽만 보면 문제를 절반만 보는 셈이다.

---

## 흔한 실수 4: 대량 마이그레이션 전에 replica와 archive 용량 예산을 계산하지 않는다

primary 디스크만 보고 작업을 시작하면 안 된다. 대량 backfill이나 인덱스 생성은 아래를 모두 압박할 수 있다.

- primary WAL volume
- replica apply backlog
- archive storage 증가
- recovery 시간 목표

실무에서는 대량 작업 전에 최소한 아래를 추정하는 편이 좋다.

- 시간당 예상 WAL 생성량
- replica가 평소 처리 가능한 apply 속도
- archive 시스템 처리량
- 디스크 여유와 안전 한계

---

## 실무 체크리스트: 쓰기 피크, replication lag, `pg_wal` 증가가 보일 때 순서대로 확인할 것

### 1) 증상 분류

- 앱 쓰기 latency 증가인가
- checkpoint warning 증가인가
- replica stale read 문제가 보이는가
- `pg_wal` 디스크 증가인가
- archive 지연인가

### 2) 현재 WAL 압박 확인

- 초당 WAL bytes가 평소 대비 얼마나 증가했는가
- 최근 배치, migration, bulk update, index build가 있었는가
- full-page image 비중이 높은가

### 3) 체크포인트 상태 확인

- `checkpoints_req`가 늘었는가
- `checkpoint_sync_time`이 큰가
- checkpoint 간격이 현재 workload에 비해 지나치게 짧은가

### 4) 복제 분해

- receive, flush, replay 중 어디가 느린가
- 특정 replica만 느린가, 전반적으로 느린가
- recovery conflict나 long query가 replay를 막는가

### 5) WAL 보존 원인 확인

- physical replica 때문인가
- logical slot 때문인가
- archive 실패 때문인가
- 단순 recycling 범위인가

### 6) 조치 우선순위

- 진행 중인 대량 작업의 속도부터 낮출 것인가
- chunking 또는 pause가 가능한가
- slot consumer 복구가 가능한가
- 디스크 임계치 전에 어떤 완화책이 가능한가
- 설정 변경은 즉시 효과가 있는가, 아니면 다음 maintenance 창에 해야 하는가

### 7) 사후 개선

- 배치 동시성과 chunk size 재설계
- WAL/replication/archive 알림 강화
- slot backlog 모니터링 추가
- checkpoint 관련 설정 재평가
- 대량 작업 runbook 보강

---

## 한 줄로 정리하면

PostgreSQL 쓰기 운영의 핵심은 쿼리를 빨리 끝내는 것만이 아니라, **WAL 생성, 체크포인트, 복제 소비, 아카이브 보존이 서로 감당 가능한 속도로 맞물리게 만드는 것**이다.
