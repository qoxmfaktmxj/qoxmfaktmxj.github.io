---
layout: post
title: "Lakehouse Table Maintenance 실전: Snapshot, Compaction, Vacuum, Schema Evolution으로 Iceberg와 Delta Lake를 운영하는 법"
date: 2026-07-03 11:50:00 +0900
categories: [data-infra]
tags: [study, data-infra, lakehouse, iceberg, delta-lake, compaction, vacuum, snapshot, schema-evolution, small-files, partitioning, data-platform]
permalink: /data-infra/2026/07/03/study-lakehouse-table-maintenance-snapshot-compaction-vacuum-schema-evolution.html
---

## 배경: Lakehouse는 파일을 쌓는 시스템이 아니라 테이블을 계속 고치는 운영 시스템이다

데이터 플랫폼을 만들 때 object storage는 매력적이다. S3, GCS, Azure Blob 같은 저장소는 싸고, 크고, 내구성이 좋다. Parquet이나 ORC 같은 columnar format을 쓰면 압축률과 scan 성능도 괜찮다. 그래서 처음에는 구조가 단순하다.

```text
application events
  -> Kafka 또는 batch collector
  -> object storage에 Parquet 적재
  -> Spark, Trino, DuckDB, Athena, BigQuery 외부 테이블로 조회
```

작은 팀에서는 이 방식만으로도 꽤 오래 버틴다. 날짜별 파티션 디렉터리를 만들고, 하루치 파일을 쌓고, SQL 엔진이 읽게 하면 된다.

```text
s3://warehouse/events/date=2026-07-03/part-0001.parquet
s3://warehouse/events/date=2026-07-03/part-0002.parquet
```

하지만 실무 데이터가 커지고 소비자가 늘어나면 곧 단순 파일 적재 방식의 한계가 드러난다.

- streaming sink가 5초마다 작은 Parquet 파일을 만들어 쿼리가 느려진다
- 배치 재처리 중 일부 파일만 교체되어 소비자가 중간 상태를 읽는다
- schema가 바뀌었는데 예전 파일과 새 파일이 섞여 엔진마다 다르게 해석한다
- partition column을 잘못 잡아 특정 쿼리가 수천 개 파일을 읽는다
- CDC update/delete를 append-only 파일 구조에 억지로 넣다가 중복 row가 생긴다
- 오래된 snapshot을 지우지 않아 metadata와 storage 비용이 계속 증가한다
- vacuum을 과하게 돌려 time travel, rollback, 장기 실행 쿼리가 깨진다
- compaction job이 본 업무 쿼리와 경쟁해 warehouse 비용을 폭발시킨다
- 데이터 품질 장애를 되돌리고 싶은데 어떤 파일 세트가 정상 버전인지 모른다

Lakehouse table format은 이 문제를 해결하기 위해 등장했다. Apache Iceberg, Delta Lake, Apache Hudi는 모두 object storage 위에 "테이블"이라는 추상화를 올린다. 단순히 파일 목록을 읽는 것이 아니라, metadata log와 snapshot을 통해 특정 시점의 일관된 파일 집합을 읽게 한다.

하지만 여기서 자주 생기는 오해가 있다.

> Iceberg나 Delta Lake를 쓰면 파일 관리 문제가 자동으로 사라진다.

그렇지 않다. Table format은 일관성, snapshot, schema evolution, partition evolution, delete/update 같은 기능을 제공한다. 하지만 운영자는 여전히 파일 크기, compaction 주기, snapshot 보존 기간, metadata 정리, schema 변경 절차, partition 전략, query pattern, rollback 정책을 설계해야 한다.

오늘 글은 "Iceberg와 Delta Lake 중 무엇이 더 좋은가" 같은 얕은 비교가 아니다. 중급 이상 개발자와 데이터 엔지니어가 lakehouse 테이블을 실제 운영할 때 마주치는 질문을 기준으로 정리한다.

1. Lakehouse table format이 단순 Parquet 디렉터리와 본질적으로 다른 점은 무엇인가
2. Snapshot, manifest, transaction log는 쿼리 일관성과 rollback에 어떤 의미를 갖는가
3. Small file 문제는 왜 생기고 compaction은 언제 성능 개선이 아니라 비용 폭탄이 되는가
4. Partitioning, clustering, sorting은 어떤 쿼리 패턴에 각각 효과가 있는가
5. Schema evolution은 어떤 변경이 안전하고 어떤 변경이 위험한가
6. Vacuum과 snapshot expiration은 storage 절감과 복구 가능성 사이에서 어떻게 조율해야 하는가
7. CDC, streaming, batch backfill이 섞인 테이블을 어떻게 안전하게 운영할 것인가
8. 배포 전과 장애 대응 시 확인해야 할 체크리스트는 무엇인가

결론부터 말하면 이렇다.

**Lakehouse 운영의 핵심은 object storage에 파일을 많이 쌓는 것이 아니라, 쿼리 엔진이 읽어야 할 "유효한 파일 집합"을 작고, 일관되고, 되돌릴 수 있게 유지하는 것이다.**

파일은 데이터의 물리적 표현일 뿐이다. 운영자가 관리해야 할 대상은 더 넓다. snapshot의 수명, metadata의 크기, 파일의 분포, delete file의 누적, schema와 partition의 진화, 쿼리의 pruning 가능성, 장애 시 복구 지점까지 하나의 테이블 수명주기로 봐야 한다.

---

## 먼저 큰 그림: Lakehouse 테이블은 데이터 파일과 메타데이터 파일의 조합이다

단순 Hive-style external table은 보통 디렉터리 구조를 기준으로 파일을 찾는다.

```text
events/
  dt=2026-07-01/
    part-000.parquet
    part-001.parquet
  dt=2026-07-02/
    part-000.parquet
    part-001.parquet
```

엔진은 path와 partition 값을 보고 파일을 읽는다. 이 구조는 쉽지만 치명적인 문제가 있다. "이 테이블의 현재 버전이 정확히 어떤 파일들의 집합인가"를 강하게 표현하기 어렵다. 배치 job이 기존 파일을 지우고 새 파일을 쓰는 중간에 쿼리가 들어오면, 소비자는 일부는 옛 파일, 일부는 새 파일인 중간 상태를 읽을 수 있다.

Iceberg와 Delta Lake는 파일 목록을 직접 디렉터리에서 추론하지 않는다. 테이블 metadata가 현재 snapshot 또는 log version을 가리키고, 그 버전이 유효한 data file 목록을 정의한다.

개념적으로는 다음과 같다.

```text
Table pointer
  -> current snapshot or log version
      -> metadata files
          -> data files
          -> delete files
          -> partition stats
          -> schema and partition spec
```

읽는 쪽은 "현재 snapshot"에 포함된 파일만 읽는다. 쓰는 쪽은 새 파일을 만든 뒤 metadata를 원자적으로 갱신한다. 이 덕분에 object storage처럼 rename이나 directory transaction이 약한 환경에서도 테이블 단위의 일관성을 만들 수 있다.

### Iceberg의 관점

Iceberg는 snapshot, manifest list, manifest file, data file metadata를 명시적으로 계층화한다. Snapshot은 특정 시점의 테이블 상태다. Manifest는 data file 목록과 각 파일의 partition value, record count, column-level statistics 같은 정보를 담는다.

대략적인 구조는 다음과 같다.

```text
metadata.json
  -> current-snapshot-id
      -> snapshot
          -> manifest-list
              -> manifest files
                  -> data files
                  -> delete files
```

Iceberg가 강한 부분은 table metadata를 통해 partition evolution, hidden partitioning, snapshot isolation, position/equality delete, branch/tag 같은 기능을 비교적 정교하게 제공한다는 점이다. 쿼리 엔진은 metadata를 보고 불필요한 파일을 건너뛸 수 있다.

### Delta Lake의 관점

Delta Lake는 `_delta_log` 디렉터리에 transaction log를 쌓는다. 각 commit은 JSON action으로 표현되고, 일정 주기마다 checkpoint Parquet이 만들어져 log replay 비용을 줄인다.

```text
_delta_log/
  00000000000000000000.json
  00000000000000000001.json
  00000000000000000002.json
  00000000000000000010.checkpoint.parquet
```

각 log version은 add file, remove file, metadata change, protocol change 같은 action을 담는다. 읽는 쪽은 특정 version까지의 log를 해석해 유효한 파일 목록을 만든다.

Delta의 강점은 Spark 생태계와의 결합, transaction log의 직관성, optimize/vacuum 같은 운영 명령의 익숙함이다. Databricks 환경에서는 liquid clustering, deletion vectors, change data feed 등 운영 편의 기능도 함께 제공된다.

### 공통으로 중요한 것

두 format의 내부 구현은 다르지만 운영자가 봐야 할 질문은 비슷하다.

- 현재 테이블 버전은 어떤 파일을 유효하다고 보는가
- 새 write가 commit되기 전 소비자가 중간 파일을 읽지 않는가
- 실패한 write가 만든 orphan file은 어떻게 정리되는가
- 오래된 snapshot 또는 log version은 얼마나 보존할 것인가
- metadata 파일 자체가 너무 커지지 않는가
- 파일 단위 통계가 쿼리 pruning에 충분한가
- update/delete가 누적되며 read amplification을 만들지 않는가

Lakehouse를 제대로 운영하려면 "데이터 파일"만 볼 것이 아니라 "테이블 상태를 결정하는 metadata"를 함께 봐야 한다.

---

## 핵심 개념 1: Snapshot은 백업이 아니라 읽기 일관성의 단위다

Snapshot을 단순히 과거 버전으로 돌아가기 위한 기능으로만 이해하면 부족하다. Snapshot은 읽기 일관성의 단위다.

예를 들어 매일 새벽 주문 mart를 갱신한다고 하자.

```text
old snapshot
  -> order_mart의 어제까지 정상 파일 목록

new write
  -> 오늘 재계산한 새 파일들을 object storage에 업로드
  -> metadata에 새 파일 목록 추가, 옛 파일 제거 표시
  -> commit 성공

new snapshot
  -> order_mart의 새 파일 목록
```

중요한 점은 commit이 성공하기 전까지 독자는 old snapshot을 계속 읽는다는 것이다. 새 data file이 storage에 이미 존재하더라도 metadata에 commit되지 않았다면 테이블의 현재 상태가 아니다. 반대로 commit이 성공하면 독자는 new snapshot을 읽는다.

이 원리가 없으면 batch overwrite는 위험하다.

```text
1. 기존 date=2026-07-02 파일 삭제
2. 새 date=2026-07-02 파일 일부 쓰기
3. job 실패
```

단순 디렉터리 기반 테이블에서는 이 중간 상태가 그대로 노출될 수 있다. Lakehouse table format은 "파일을 쓰는 일"과 "그 파일을 테이블에 공개하는 일"을 분리한다.

### Snapshot isolation이 주는 실무 효과

Snapshot isolation은 다음 장점을 만든다.

- 장기 실행 쿼리가 시작 시점의 파일 집합을 안정적으로 읽는다
- 배치 재처리 중에도 소비자가 반쯤 갱신된 결과를 읽지 않는다
- 장애가 난 write의 미완성 파일을 테이블에서 제외할 수 있다
- 잘못된 commit을 발견하면 이전 snapshot으로 rollback할 수 있다
- 특정 version을 기준으로 데이터 품질 검증과 재현을 할 수 있다

예를 들어 BI 대시보드가 09:00에 쿼리를 시작했고, 09:03에 ETL job이 새 snapshot을 commit했다고 하자. Snapshot isolation이 있다면 BI 쿼리는 시작 시점의 snapshot을 끝까지 읽는다. 중간에 파일 목록이 바뀌어 결과가 흔들리는 일을 피한다.

### Snapshot은 무한히 보존하면 안 된다

하지만 snapshot을 많이 보존할수록 비용이 든다.

- metadata 파일 수가 늘어난다
- 오래된 data file이 삭제되지 못한다
- query planning 시 고려해야 할 metadata가 커진다
- object storage list/get 요청이 늘 수 있다
- branch/tag, rollback 정책이 복잡해진다

그래서 snapshot retention 정책이 필요하다.

```text
운영 테이블 예시
  - 최근 7일 snapshot은 보존
  - 일별 주요 배치 완료 snapshot은 30일 보존
  - 품질 검증 전 snapshot은 tag로 고정
  - 그 외 중간 commit snapshot은 만료 대상
```

여기서 무조건 "짧게 보존"도 답이 아니다. 너무 빨리 snapshot을 지우면 rollback이 어려워지고, 장기 실행 쿼리나 downstream 재처리가 깨질 수 있다. Snapshot은 storage 비용과 복구 가능성 사이의 정책이다.

---

## 핵심 개념 2: Small file은 storage 문제가 아니라 planning과 scheduling 문제다

Lakehouse 운영에서 가장 흔한 성능 장애는 small file 문제다. Object storage는 큰 파일을 순차적으로 읽을 때 강하다. 반대로 수만, 수십만 개의 작은 파일은 여러 층에서 비용을 만든다.

```text
나쁜 상태
  partition dt=2026-07-03
    180,000 files
    average file size 2 MB

좋은 상태에 가까운 예
  partition dt=2026-07-03
    400 files
    average file size 256 MB
```

작은 파일이 많으면 단순히 storage 용량만 늘어나는 것이 아니다.

- query planner가 읽을 파일 목록을 만드는 시간이 길어진다
- object storage metadata 요청이 많아진다
- task 수가 지나치게 많아져 scheduler overhead가 커진다
- 각 task가 읽는 데이터가 작아 CPU와 I/O 효율이 떨어진다
- 파일 단위 통계가 잘게 쪼개져 pruning 효과가 애매해진다
- compaction이 계속 밀리면 나중에 한 번에 큰 비용이 든다

Small file은 특히 streaming sink에서 자주 생긴다. 낮은 latency를 위해 micro-batch를 짧게 잡으면 commit마다 작은 파일이 만들어진다.

```text
Kafka -> Spark Structured Streaming -> Delta/Iceberg
trigger interval: 10 seconds
active partitions: 300
```

이 경우 10초마다 최대 300개 파티션에 파일이 생길 수 있다. 하루가 지나면 파일 수가 폭발한다.

### Compaction은 파일을 합치는 작업이지만, 사실은 테이블을 다시 쓰는 작업이다

Compaction의 기본 아이디어는 작다.

```text
many small files -> fewer large files
```

하지만 운영 관점에서는 단순 merge가 아니다. Compaction은 기존 data file을 읽고, 새 data file을 쓰고, metadata에서 옛 파일을 제거하고 새 파일을 추가하는 rewrite 작업이다.

Iceberg에서는 `rewrite_data_files`, Delta에서는 `OPTIMIZE`나 compaction job이 대표적이다.

```sql
-- 개념 예시: Delta Lake
OPTIMIZE events
WHERE dt = '2026-07-03';

-- 개념 예시: Iceberg Spark procedure
CALL catalog.system.rewrite_data_files(
  table => 'analytics.events',
  options => map(
    'target-file-size-bytes', '536870912'
  )
);
```

Compaction은 다음 비용을 가진다.

- 전체 또는 일부 파일을 다시 읽는다
- 새 파일을 다시 쓴다
- object storage PUT 비용이 든다
- table commit 충돌 가능성이 생긴다
- 실행 중인 쿼리와 I/O를 경쟁한다
- 잘못 잡으면 최근 hot partition만 계속 건드린다

따라서 "small file이 있으니 매시간 전체 테이블 optimize"는 위험하다. Compaction은 범위와 목표를 좁혀야 한다.

### 좋은 compaction 정책의 기준

실무에서는 아래 기준을 함께 본다.

- 평균 파일 크기: 너무 작거나 너무 큰가
- 파일 수: partition별 파일 수가 query planning에 부담을 주는가
- 최근 write 빈도: 아직 계속 쓰이는 hot partition인가
- query pattern: 실제로 자주 조회되는 partition인가
- delete/update 누적: data file뿐 아니라 delete file도 정리해야 하는가
- warehouse 비용: compaction 비용보다 query 절감 효과가 큰가
- SLA: compaction이 늦어져도 소비자 성능 요구를 만족하는가

예를 들어 클릭 이벤트 raw 테이블은 최근 2시간 파티션에 계속 쓰기가 발생한다. 이 구간을 너무 자주 compaction하면 write와 compaction이 충돌하고, 방금 합친 파일이 다시 작은 파일로 쪼개진다. 반대로 하루가 지난 cold partition은 더 이상 쓰기가 적으므로 큰 파일로 정리하기 좋다.

```text
권장에 가까운 운영 패턴
  - hot zone: 최근 1-3시간, 작은 파일 허용, 낮은 latency 우선
  - warm zone: 최근 1-2일, 주기적 incremental compaction
  - cold zone: 3일 이전, 큰 파일과 clustering 유지, compaction 빈도 낮춤
```

이런 zone 개념을 두면 compaction job이 테이블 전체를 무작정 훑지 않는다.

---

## 핵심 개념 3: Partitioning은 디렉터리 설계가 아니라 pruning 계약이다

Partitioning은 데이터를 디렉터리에 나누는 기능처럼 보인다. 하지만 lakehouse에서 partitioning의 본질은 query pruning이다. 쿼리가 읽지 않아도 되는 파일을 metadata 단계에서 제거할 수 있어야 한다.

흔한 파티션은 날짜다.

```text
dt=2026-07-03
```

날짜 조건이 자주 붙는 이벤트 테이블이라면 날짜 파티션은 자연스럽다.

```sql
SELECT count(*)
FROM events
WHERE dt = DATE '2026-07-03';
```

하지만 모든 column을 partition으로 만들면 안 된다. Cardinality가 높은 column을 그대로 partition하면 small file이 폭발한다.

```text
나쁜 예
  dt=2026-07-03/user_id=U-000001/part.parquet
  dt=2026-07-03/user_id=U-000002/part.parquet
  dt=2026-07-03/user_id=U-000003/part.parquet
```

사용자별 조회가 많다고 해서 `user_id`를 물리 파티션으로 잡으면 대부분의 파티션이 작아진다. 이 경우에는 bucketing, clustering, sorting, file-level statistics, secondary index 성격의 기능을 검토하는 편이 낫다.

### Hidden partitioning과 partition evolution

Iceberg가 자주 강조하는 기능 중 하나가 hidden partitioning이다. 사용자는 `event_time`으로 조건을 쓰고, 테이블은 내부적으로 `days(event_time)` 같은 transform을 partition spec으로 쓸 수 있다.

```sql
SELECT *
FROM events
WHERE event_time >= TIMESTAMP '2026-07-03 00:00:00'
  AND event_time <  TIMESTAMP '2026-07-04 00:00:00';
```

사용자가 `dt` 같은 별도 컬럼을 정확히 넣지 않아도 엔진이 partition pruning을 할 수 있다. 이는 실무에서 중요하다. 사용자가 `event_time`과 `dt` 조건을 불일치하게 넣어 잘못된 결과를 만드는 일을 줄일 수 있기 때문이다.

Partition evolution도 중요하다. 처음에는 일 단위 partition이 충분했지만 데이터가 커져 시간 단위가 필요해질 수 있다.

```text
초기
  partition: days(event_time)

변경 후
  partition: hours(event_time)
```

단순 Hive table에서는 과거 디렉터리 구조와 새 디렉터리 구조가 섞여 운영이 지저분해질 수 있다. Iceberg 같은 format은 partition spec을 metadata로 관리해 과거 파일과 새 파일이 서로 다른 partition spec을 가져도 하나의 테이블로 다룰 수 있다.

### Partition을 고를 때 봐야 하는 질문

Partition column은 데이터 생산자 관점이 아니라 소비 쿼리 관점에서 고른다.

- 대부분 쿼리가 어떤 시간 범위를 조회하는가
- point lookup이 많은가, range scan이 많은가
- write가 동시에 얼마나 많은 partition에 분산되는가
- partition cardinality가 하루 기준 어느 정도인가
- partition 하나의 평균 데이터 크기는 적절한가
- late arriving data가 과거 partition에 얼마나 자주 들어오는가
- backfill이 기존 partition을 자주 다시 쓰는가
- retention과 삭제 정책이 partition 단위로 떨어지는가

좋은 partition은 쿼리를 줄이고, 운영 job의 범위를 제한하며, retention을 단순하게 만든다. 나쁜 partition은 파일 수와 metadata를 늘리고, compaction 비용을 키우며, write 충돌을 만든다.

---

## 핵심 개념 4: Clustering과 sorting은 partition 다음의 물리 설계다

Partitioning만으로 충분하지 않은 경우가 많다. 예를 들어 이벤트 테이블에서 날짜 조건은 거의 항상 붙지만, 그 안에서 `customer_id`, `session_id`, `country`, `event_name` 조건이 자주 붙는다고 하자.

```sql
SELECT *
FROM events
WHERE event_time >= TIMESTAMP '2026-07-03 00:00:00'
  AND event_time <  TIMESTAMP '2026-07-04 00:00:00'
  AND customer_id = 'C-100';
```

날짜 partition만 있으면 하루치 파일은 줄일 수 있지만, 그 안에서는 여전히 많은 파일을 읽을 수 있다. 이때 clustering, sorting, Z-order, liquid clustering 같은 물리 배치 전략이 도움이 된다.

핵심은 파일 내부 또는 파일 집합 수준에서 비슷한 값을 가까이 배치해 file-level statistics로 pruning을 잘하게 만드는 것이다.

```text
정렬되지 않은 파일
  file-1: customer_id C-001 ... C-999가 섞임
  file-2: customer_id C-001 ... C-999가 섞임

customer_id 기준으로 잘 모인 파일
  file-1: customer_id C-001 ... C-100
  file-2: customer_id C-101 ... C-200
```

Parquet 파일에는 row group과 column statistics가 있다. Lakehouse metadata에도 파일 수준 min/max, null count, record count 같은 정보가 들어간다. 값이 잘 모여 있으면 쿼리 엔진이 "이 파일에는 찾는 값이 없다"고 판단하기 쉽다.

### Sorting이 항상 좋은 것은 아니다

정렬은 read 성능을 개선할 수 있지만 write 비용을 키운다.

- 데이터 shuffle 비용이 든다
- 큰 sort 작업이 spill을 만들 수 있다
- streaming sink에서는 낮은 latency와 충돌한다
- 너무 많은 column을 기준으로 정렬하면 효과가 희석된다
- query pattern이 바뀌면 오래된 정렬 전략이 부채가 된다

따라서 sorting key는 신중히 골라야 한다.

좋은 후보:

- 자주 filter에 쓰인다
- cardinality와 분포가 pruning에 유리하다
- 시간 partition 안에서 함께 조회되는 경우가 많다
- 데이터가 너무 자주 update되지 않는다

나쁜 후보:

- 거의 모든 쿼리에 쓰이지 않는다
- 값이 한쪽으로 심하게 치우쳐 있다
- 매번 다른 ad-hoc column 조합이 쓰인다
- write path에서 계산 비용이 크다

실무에서는 "partition으로 크게 줄이고, clustering/sorting으로 partition 내부 scan을 줄인다"는 순서가 안전하다.

---

## 핵심 개념 5: Schema Evolution은 컬럼 추가보다 의미 변경이 어렵다

Lakehouse format은 schema evolution을 지원한다. 컬럼 추가, rename, type promotion, nullable 변경 같은 기능을 제공한다. 하지만 "기능이 있다"와 "운영에서 안전하다"는 다르다.

Schema 변경은 크게 세 종류로 나눌 수 있다.

```text
대체로 안전한 변경
  - nullable 컬럼 추가
  - default를 가진 optional field 추가
  - metadata 설명 추가

주의가 필요한 변경
  - 컬럼 rename
  - int -> long 같은 type widening
  - nested field 추가
  - partition spec 변경

위험하거나 breaking에 가까운 변경
  - 컬럼 삭제
  - nullable -> non-nullable
  - string -> int 같은 incompatible type 변경
  - 같은 컬럼명의 business meaning 변경
  - timestamp timezone 의미 변경
```

중요한 것은 물리 schema만이 아니다. 같은 `amount` 컬럼이라도 의미가 바뀌면 소비자는 깨진다.

```text
기존 amount
  - 쿠폰 차감 전 결제 금액

변경 후 amount
  - 쿠폰 차감 후 실결제 금액
```

타입은 그대로 `decimal(18,2)`일 수 있다. 하지만 지표는 완전히 바뀐다. Table format의 schema evolution 기능은 이런 의미 변경을 자동으로 막아주지 않는다. Data contract, 릴리즈 노트, consumer 영향 분석이 필요하다.

### Rename은 생각보다 위험하다

Iceberg처럼 field id를 관리하는 format은 rename을 비교적 안전하게 처리할 수 있다. 컬럼 이름이 바뀌어도 내부 field id가 유지되면 예전 파일과 새 파일을 같은 logical column으로 볼 수 있다.

하지만 모든 엔진과 tool이 field id semantics를 똑같이 존중하는 것은 아니다. 어떤 connector나 downstream export는 이름 기반으로 처리할 수 있다. BI semantic layer, dbt model, notebook, ad-hoc query는 rename에 약하다.

따라서 rename은 다음 절차로 처리하는 편이 안전하다.

1. 새 컬럼을 추가한다
2. 일정 기간 두 컬럼을 함께 제공한다
3. downstream 사용처를 이전한다
4. 사용량을 확인한다
5. deprecated 컬럼을 제거한다

이 방식은 느리지만 예측 가능하다. 특히 여러 엔진이 같은 테이블을 읽는 환경에서는 보수적으로 가는 것이 낫다.

### Timestamp와 timezone은 별도 정책으로 다뤄야 한다

Lakehouse에서 timestamp는 자주 사고를 만든다.

- producer는 KST local time을 보냈다
- Spark는 session timezone 기준으로 해석했다
- Trino는 UTC timestamp처럼 읽었다
- partition transform은 UTC 기준 day로 잘랐다
- BI는 사용자의 browser timezone으로 표시했다

이 경우 schema는 모두 timestamp로 보이지만 지표 날짜가 어긋난다.

테이블 계약에는 최소한 아래가 있어야 한다.

```yaml
time_semantics:
  event_time_column: occurred_at
  storage_timezone: UTC
  business_timezone: Asia/Seoul
  partition_transform: days(occurred_at)
  late_arrival_policy: "event_time 기준 7일 이내 허용"
```

Timestamp 의미를 문서가 아니라 계약과 테스트로 잡아야 한다. 특히 한국 서비스처럼 KST 기준 일별 지표가 중요한 경우 UTC day와 KST day의 경계가 매일 9시간 어긋난다는 점을 계속 의식해야 한다.

---

## 핵심 개념 6: Update와 Delete는 read amplification을 만든다

Object storage의 columnar file은 row-level update에 원래 강하지 않다. Parquet 파일 중 한 row만 바꾸기 위해 파일 전체를 제자리에서 수정하는 구조가 아니다. Lakehouse format은 이를 해결하기 위해 copy-on-write, merge-on-read, delete file, deletion vector 같은 방식을 쓴다.

개념적으로 두 접근이 있다.

### Copy-on-write

변경 대상 row가 들어 있는 data file을 새 파일로 다시 쓴다.

```text
old file A: rows 1-1000
update row 10
new file A': rows 1-1000 with row 10 updated
metadata: old file A removed, new file A' added
```

장점:

- 읽기가 단순하다
- 쿼리 시 추가 delete merge 비용이 적다
- batch analytics에 유리하다

단점:

- 작은 update에도 큰 파일 rewrite가 필요할 수 있다
- write 비용이 크다
- high-frequency CDC에 부담이 될 수 있다

### Merge-on-read 또는 delete file 방식

기존 data file은 그대로 두고 삭제/변경 정보를 별도 파일에 기록한다. 읽을 때 data file과 delete 정보를 합쳐 해석한다.

```text
data file A
delete file D: file A의 position 10 삭제
new data file B: updated row 10 추가
```

장점:

- write latency와 비용을 낮출 수 있다
- CDC ingest에 유리하다
- 작은 변경을 빠르게 반영할 수 있다

단점:

- 읽을 때 delete file을 함께 봐야 한다
- delete file이 누적되면 read amplification이 커진다
- 주기적인 rewrite/compaction이 필요하다

### CDC 테이블에서 특히 중요한 것

CDC를 lakehouse에 적재하면 insert만 있는 로그와 현재 상태 테이블을 구분해야 한다.

```text
append-only change log table
  - 모든 변경 이벤트를 순서대로 저장
  - audit, replay, lineage에 유리
  - query할 때 현재 상태를 직접 얻기 어렵다

current state table
  - primary key 기준 최신 row만 유지
  - serving, BI, mart에 유리
  - update/delete 처리와 compaction이 필요
```

두 요구를 하나의 테이블로 억지로 만족시키려 하면 문제가 생긴다. 원천 변경 이력은 append-only로 보존하고, 별도 current table을 merge/upsert로 유지하는 설계가 더 명확하다.

```text
db_cdc.orders_changelog
  -> append-only, 원본 순서와 operation 보존

mart.orders_current
  -> order_id 기준 최신 상태
  -> merge job 또는 streaming upsert
```

CDC upsert 테이블은 다음 운영 지표를 꼭 봐야 한다.

- data file 수
- delete file 수 또는 deletion vector 크기
- merge job latency
- primary key 중복 여부
- out-of-order event 비율
- tombstone 보존 기간
- compaction 이후 read 성능 변화

Update/delete 지원을 켰다고 운영이 끝난 것이 아니다. 변경 파일을 계속 정리하지 않으면 읽기 비용이 뒤늦게 폭발한다.

---

## 핵심 개념 7: Vacuum은 청소가 아니라 복구 가능성을 줄이는 작업이다

Vacuum 또는 remove orphan files, expire snapshots는 storage 비용을 줄이는 데 필요하다. 하지만 이 작업은 되돌릴 수 있는 과거를 줄인다.

Lakehouse 테이블에는 보통 세 종류의 "지워도 될 것 같은 파일"이 있다.

```text
1. 더 이상 현재 snapshot에서 참조하지 않는 오래된 data file
2. 실패한 write가 남긴 orphan file
3. 만료된 metadata, manifest, transaction log
```

이 파일들을 영원히 두면 비용이 증가한다. 하지만 너무 빨리 지우면 문제가 생긴다.

- 장기 실행 쿼리가 시작 시점 snapshot의 파일을 읽지 못한다
- time travel query가 실패한다
- 잘못된 배치 결과를 이전 버전으로 rollback할 수 없다
- downstream job이 특정 version을 기준으로 재처리할 수 없다
- 복제나 catalog sync가 늦은 환경에서 참조 깨짐이 생긴다

### Vacuum retention은 SLA와 함께 정해야 한다

Retention 기간은 감으로 정하면 안 된다. 아래 시간을 고려해야 한다.

- 가장 긴 쿼리 실행 시간
- 가장 긴 downstream 재처리 지연
- 데이터 품질 검증이 끝나는 시간
- 장애를 발견하고 rollback을 결정하는 평균 시간
- 백업 또는 cross-region replication 지연
- catalog와 query engine cache 만료 시간
- 법적 또는 감사 요구가 있는 보존 기간

예를 들어 매일 03:00에 mart를 만들고, 09:00에 데이터 품질 리포트가 나오며, 업무팀이 12:00에 이상을 발견할 수 있다고 하자. Snapshot을 2시간만 보존하면 오전에 발견한 문제를 쉽게 rollback할 수 없다.

운영 정책 예시는 다음과 같다.

```text
bronze/raw table
  - data file retention: 30-90일 이상
  - snapshot retention: 짧게 가능하나 원천 로그 보존 우선
  - orphan cleanup: 보수적으로

silver/current table
  - snapshot retention: 7-14일
  - vacuum: 품질 검증 완료 후
  - delete file compaction: 주기적

gold/mart table
  - 중요 배치 완료 snapshot tag: 30일
  - 일반 중간 snapshot: 7일
  - rollback window: 업무 SLA와 맞춤
```

정답은 없다. 하지만 "storage 줄이려고 매일 24시간 이전 파일을 다 지운다"는 식의 단순 정책은 위험하다.

### Orphan file 정리는 별도 안전장치가 필요하다

Orphan file은 metadata에서 참조하지 않는 파일이다. 실패한 write, aborted job, 잘못된 manual upload, 경로 이동 실수로 생긴다.

문제는 "지금 metadata에서 참조하지 않는다"가 항상 "영원히 필요 없다"는 뜻은 아니라는 점이다. Commit 중인 writer가 아직 metadata를 갱신하기 전일 수 있고, catalog 지연 때문에 최신 상태를 못 봤을 수도 있다.

따라서 orphan cleanup은 충분한 grace period를 둬야 한다.

```text
orphan cleanup 후보
  - 마지막 수정 시간이 3일 이상 지난 파일
  - 현재 metadata snapshot 어디에서도 참조하지 않음
  - active writer가 쓰는 staging prefix가 아님
  - job run id 또는 commit id 기준으로 실패 확정
```

특히 여러 writer가 같은 table location에 접근하는 환경에서는 cleanup job이 writer의 임시 파일을 지우지 않도록 staging 경로와 권한을 분리하는 것이 좋다.

---

## 실무 예시: 주문 이벤트 Lakehouse 테이블을 설계해 보기

가상의 커머스 서비스를 생각해 보자. 주문, 결제, 환불 이벤트가 Kafka로 들어오고, 데이터 플랫폼은 이를 lakehouse에 적재한다.

요구사항은 다음과 같다.

- 원천 이벤트는 감사와 재처리를 위해 보존해야 한다
- 주문의 현재 상태를 빠르게 조회할 수 있어야 한다
- 일별 매출 mart는 KST 기준으로 계산해야 한다
- 환불은 발생일 기준 지표와 주문일 기준 지표 모두 필요하다
- BI는 최근 90일을 자주 조회한다
- 데이터 품질 장애가 있으면 최소 7일 안에는 rollback할 수 있어야 한다
- CDC와 batch backfill이 모두 들어올 수 있다

이 요구를 하나의 테이블에 넣으면 복잡해진다. 대신 계층을 나눈다.

```text
bronze.order_events_raw
  - Kafka 이벤트 원본 append-only
  - event_id, aggregate_id, event_type, event_version, occurred_at, ingested_at, payload
  - partition: days(ingested_at) 또는 days(occurred_at), 운영 목적에 따라 결정

silver.orders_current
  - order_id 기준 최신 주문 상태
  - merge/upsert
  - partition: bucket(order_id) 또는 days(updated_at) 조합 검토
  - delete/update 정리 필요

silver.order_events_normalized
  - payload를 정규화한 append-only 이벤트
  - event_time 기준 품질 검증
  - schema evolution 관리

gold.sales_daily
  - KST 기준 일별 매출 mart
  - grain: sales_date, store_id, product_id
  - partition: sales_date
  - batch 재계산과 overwrite가 중심
```

### Bronze 설계

Bronze는 원본 보존이 목적이다. 여기서 지나치게 정제하려 하면 복구와 재처리가 어려워진다.

```sql
CREATE TABLE bronze.order_events_raw (
  event_id        string,
  aggregate_id    string,
  event_type      string,
  event_version   int,
  occurred_at     timestamp,
  ingested_at     timestamp,
  kafka_topic     string,
  kafka_partition int,
  kafka_offset    long,
  payload         string
)
USING iceberg
PARTITIONED BY (days(ingested_at));
```

왜 `ingested_at` partition을 고려할까? Raw ingestion 운영에서는 "언제 들어왔는가"가 재처리와 장애 추적에 중요하다. 지연 이벤트가 한 달 전 `occurred_at`을 갖고 들어오더라도 오늘 ingest partition에 쓰면 write path가 안정적이다. 반대로 event-time 기반 분석에는 normalized 또는 mart 계층에서 event time partition을 쓴다.

Bronze compaction 정책은 낮은 latency와 파일 수 사이의 균형이다.

```text
bronze compaction
  - 최근 2시간은 작은 파일 허용
  - 2-48시간 구간은 256MB 목표로 incremental compaction
  - 48시간 이후는 거의 변경 없음, compaction 빈도 낮춤
  - 원본 보존이 중요하므로 vacuum은 보수적으로
```

### Silver current 설계

현재 상태 테이블은 `order_id` 기준 upsert가 필요하다.

```sql
MERGE INTO silver.orders_current t
USING staged_order_changes s
ON t.order_id = s.order_id
WHEN MATCHED AND s.sequence_no > t.sequence_no THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *;
```

여기서 핵심은 순서 기준이다. CDC나 이벤트 스트림은 지연과 재시도로 out-of-order가 발생할 수 있다. 단순히 "나중에 처리된 이벤트가 최신"이라고 보면 틀린다.

필요한 필드는 다음과 같다.

```text
order_id
status
amount
paid_at
refunded_at
updated_at
source_sequence_no
source_commit_lsn 또는 binlog position
event_id
ingested_at
```

`source_sequence_no`나 commit log position이 있어야 늦게 도착한 예전 이벤트가 최신 row를 덮어쓰는 일을 막을 수 있다.

이 테이블의 운영 포인트는 read amplification이다. Upsert가 잦으면 delete file이나 작은 rewritten file이 늘어난다. 따라서 current table은 별도 rewrite/compaction 정책이 필요하다.

```text
orders_current maintenance
  - delete file 수가 data file 수의 일정 비율을 넘으면 rewrite
  - primary key 중복 검증
  - sequence 역전 이벤트 카운트 모니터링
  - merge job 실패 시 bronze에서 재생 가능해야 함
```

### Gold mart 설계

Gold mart는 소비자 계약이 가장 중요하다.

```yaml
dataset: gold.sales_daily
grain:
  keys: [sales_date, store_id, product_id]
  description: "KST 기준 매출 발생일, 매장, 상품 단위의 일별 순매출"
time_semantics:
  business_timezone: Asia/Seoul
  event_time_column: paid_at
  refund_policy: "주문일 기준 차감 mart와 환불일 기준 mart를 분리"
freshness:
  expected_ready_at: "매일 07:30 Asia/Seoul"
quality:
  - primary key unique
  - sales_date not null
  - revenue >= 0 for gross table
  - row count deviation within threshold
```

Gold는 batch overwrite가 많다. 이때 snapshot isolation의 장점이 크다. 새 날짜 파티션을 계산하고 품질 검증을 통과한 뒤 commit하면 소비자는 중간 상태를 읽지 않는다.

운영 방식은 다음처럼 잡을 수 있다.

```text
1. sales_date=D-1 mart 계산
2. 임시 테이블 또는 staged write로 결과 생성
3. row count, uniqueness, amount reconciliation 검증
4. target table에 overwrite commit
5. 성공 snapshot에 tag 부여
6. downstream BI refresh
7. 7-30일 보존 후 snapshot 만료
```

이 구조에서 중요한 것은 "파일 쓰기"보다 "검증된 snapshot을 공개하는 절차"다.

---

## 트레이드오프: Lakehouse 운영에서 자주 하는 선택들

### 1. Latency vs File Size

Streaming latency를 낮추면 파일이 작아진다. 파일을 크게 만들려면 더 오래 buffer하거나 compaction을 자주 해야 한다.

```text
낮은 latency 우선
  - 장점: 빠른 데이터 반영
  - 단점: small file 증가, compaction 필요

큰 파일 우선
  - 장점: scan 효율과 planning 비용 개선
  - 단점: 데이터 반영 지연, 장애 시 재처리 범위 증가
```

실시간성이 꼭 필요한 테이블과 그렇지 않은 테이블을 분리하는 것이 좋다. 모든 테이블에 1분 latency를 요구하면 유지보수 비용이 크게 늘어난다.

### 2. Copy-on-write vs Merge-on-read

읽기가 많은 mart는 copy-on-write가 단순하다. 업데이트가 많은 CDC current table은 merge-on-read 계열이 유리할 수 있다.

하지만 merge-on-read는 나중에 정리 비용이 온다. 읽기 성능을 중요하게 보는 소비자가 많다면 delete file 누적을 모니터링하고 rewrite job을 정기적으로 돌려야 한다.

### 3. Partition Granularity

일 단위 partition은 단순하고 안정적이다. 시간 단위 partition은 pruning을 더 잘할 수 있지만 partition 수와 파일 수를 늘린다.

```text
일 단위가 적합한 경우
  - 대부분 쿼리가 하루 이상 범위
  - 하루 데이터 크기가 적절히 큼
  - write partition 수를 줄이고 싶음

시간 단위가 적합한 경우
  - 최근 몇 시간 조회가 많음
  - 하루 데이터가 너무 큼
  - 시간 단위 retention이나 replay가 필요
```

Partition evolution이 가능한 format이라도 처음 설계를 대충 해도 된다는 뜻은 아니다. 바꾸는 비용이 낮아질 뿐, 소비 쿼리와 운영 job을 다시 점검해야 한다.

### 4. Long Retention vs Storage Cost

Snapshot을 오래 보존하면 복구가 쉽다. 하지만 오래된 파일이 계속 남아 비용이 든다.

중요한 것은 테이블별 차등 정책이다.

```text
raw: 감사와 재처리를 위해 오래 보존
silver: 운영 rollback window 중심
gold: 업무 검증과 보고 주기 중심
temporary/staging: 짧게 보존
```

모든 테이블에 같은 vacuum 정책을 적용하면 either 비용이 새거나 복구 가능성이 사라진다.

### 5. Engine Portability vs Vendor Feature

Iceberg와 Delta 모두 여러 엔진에서 읽을 수 있지만, 모든 기능이 모든 엔진에서 똑같이 작동하지는 않는다.

- 특정 엔진은 deletion vector를 완전히 지원하지 않을 수 있다
- rename semantics가 field id 기반인지 이름 기반인지 다를 수 있다
- catalog lock과 commit conflict 처리 방식이 다를 수 있다
- time travel syntax와 권한 모델이 다를 수 있다
- optimize, clustering, vacuum 명령이 vendor 확장일 수 있다

따라서 "표준 format이라 어디서나 안전"이라고 가정하면 안 된다. 실제 소비 엔진 목록을 기준으로 지원 matrix를 관리해야 한다.

---

## 흔한 실수 1: Raw, Current, Mart를 한 테이블로 합친다

원본 로그 보존, 현재 상태 조회, 분석용 집계는 서로 다른 요구다.

```text
raw log
  - append-only
  - 중복과 지연을 원본 그대로 보존
  - 재처리 가능성 우선

current state
  - key 기준 최신값
  - upsert/delete 필요
  - query convenience 우선

mart
  - 명확한 grain과 품질 계약
  - overwrite와 재계산 가능성
  - 소비자 안정성 우선
```

이 셋을 한 테이블에 넣으면 schema, partition, compaction, retention 정책이 서로 충돌한다. 계층을 나누면 storage는 조금 늘 수 있지만 운영 의미가 선명해진다.

## 흔한 실수 2: Compaction을 성능 문제의 만능 해결책으로 본다

쿼리가 느릴 때 무조건 compaction을 돌리면 원인을 놓칠 수 있다.

먼저 확인할 것은 다음이다.

- partition pruning이 되는가
- 쿼리가 필요한 column만 읽는가
- file-level statistics가 있는가
- 특정 partition에 파일이 과도하게 몰렸는가
- delete file 때문에 read amplification이 생겼는가
- join 순서와 broadcast 전략이 적절한가
- catalog metadata loading이 병목인가

Compaction은 파일 수와 크기의 문제를 해결한다. 잘못된 partition, 부정확한 통계, 비효율적인 join, 과도한 select star까지 해결하지는 못한다.

## 흔한 실수 3: Vacuum을 먼저 자동화한다

비용 절감 때문에 vacuum을 빠르게 자동화하는 팀이 많다. 하지만 rollback, time travel, 장기 실행 쿼리 정책이 없는 상태에서 vacuum을 돌리면 장애 대응 카드가 사라진다.

순서는 다음이 낫다.

1. 테이블별 복구 요구사항을 정한다
2. snapshot retention을 정한다
3. 장기 실행 쿼리와 downstream lag를 측정한다
4. dry-run 또는 candidate listing으로 삭제 대상을 검토한다
5. 작은 범위에서 vacuum을 실행한다
6. 삭제 후 time travel, 주요 쿼리, downstream job을 확인한다
7. 자동화한다

## 흔한 실수 4: Schema 변경을 table format 기능에만 맡긴다

Lakehouse format이 컬럼 추가를 지원한다고 해서 downstream이 안전한 것은 아니다. BI, notebook, reverse ETL, ML feature pipeline, ad-hoc SQL은 예상보다 schema change에 취약하다.

Schema 변경에는 최소한 아래 절차가 필요하다.

- 변경 유형 분류: safe, risky, breaking
- 영향을 받는 소비자 목록 확인
- dual-write 또는 compatibility window 결정
- data contract와 catalog 설명 갱신
- staging table에서 대표 쿼리 검증
- rollback 방법 준비
- 배포 후 query failure와 null ratio 모니터링

## 흔한 실수 5: Backfill을 실시간 write와 같은 경로에 무작정 흘린다

대량 backfill은 lakehouse 테이블에 큰 영향을 준다.

- 과거 partition에 대량 파일이 추가된다
- snapshot이 크게 증가한다
- compaction 범위가 넓어진다
- streaming job과 commit conflict가 생긴다
- 지표가 과거 날짜에서 갑자기 바뀐다
- downstream incremental model이 변경을 감지하지 못할 수 있다

Backfill은 별도 run id, 별도 staging, 검증 후 publish 절차가 필요하다.

```text
backfill pattern
  1. 대상 기간과 테이블 version 고정
  2. staging path/table에 결과 생성
  3. row count와 reconciliation 검증
  4. target partition overwrite 또는 merge
  5. commit snapshot 기록
  6. downstream 재처리 범위 공지
  7. backfill 후 compaction 계획 실행
```

---

## 운영 지표: Lakehouse 테이블도 SLO가 필요하다

Lakehouse 운영은 "쿼리가 느리다"라는 민원으로 시작되면 늦다. 테이블별 health metric을 미리 봐야 한다.

### 파일과 메타데이터 지표

- partition별 파일 수
- 평균, p50, p95 파일 크기
- 최근 24시간 commit 수
- snapshot 수와 metadata 크기
- manifest 또는 log replay 시간
- orphan file 후보 수
- compaction 대상 파일 수
- data file 대비 delete file 비율

### 쿼리 지표

- planning time
- scan file count
- scan bytes
- pruned file 비율
- spilled bytes
- query p95/p99 latency
- 가장 비싼 쿼리 패턴
- select star 비율

### 데이터 품질 지표

- freshness lag
- row count deviation
- primary key duplicate count
- null ratio 변화
- enum unknown value count
- event time과 ingest time 지연 분포
- late arriving data 비율
- schema mismatch 또는 reader failure

### 운영 지표

- compaction job 성공률과 소요 시간
- vacuum 삭제 파일 수와 dry-run 차이
- merge/upsert conflict 수
- commit retry 수
- catalog lock wait time
- storage 비용
- query engine 비용

이 지표를 테이블별로 봐야 한다. Raw log table과 gold mart의 정상 범위는 다르다. 예를 들어 raw table은 작은 파일을 어느 정도 허용할 수 있지만, mart table은 일정한 파일 크기와 낮은 planning time이 중요하다.

---

## 설계 패턴 1: Bronze는 event-time보다 ingest-time 운영성을 우선한다

Lakehouse를 처음 설계할 때 자주 하는 논쟁이 있다.

```text
원천 이벤트 테이블을 event_time으로 partition해야 할까,
아니면 ingested_at으로 partition해야 할까?
```

정답은 테이블 목적에 달려 있다. 하지만 bronze raw table이라면 ingest-time partition이 운영적으로 더 안전한 경우가 많다.

이유는 간단하다. Raw table은 분석 의미보다 수집 사실을 보존하는 계층이다. 이벤트가 실제로 언제 발생했는지도 중요하지만, 플랫폼이 언제 받았고 어떤 offset에서 읽었고 어떤 payload였는지를 안정적으로 남기는 것이 더 중요하다.

모바일 앱 이벤트를 예로 들어보자.

```text
event A
  occurred_at: 2026-06-25 10:00:00
  ingested_at: 2026-07-03 11:49:00
  reason: 사용자가 일주일 동안 오프라인이었다가 앱을 열며 전송
```

Raw table을 `days(occurred_at)`으로 partition하면 오늘 들어온 이벤트가 8일 전 partition에 쓰인다. Late data가 많으면 과거 partition이 계속 열려 있게 된다. Streaming writer는 수많은 과거 partition에 작은 파일을 흩뿌릴 수 있고, compaction 대상도 넓어진다.

반대로 `days(ingested_at)`으로 partition하면 오늘 들어온 데이터는 오늘 partition에 쌓인다. 수집 장애를 추적하기 쉽고, Kafka offset과 ingestion run을 기준으로 재처리하기도 쉽다.

그렇다고 event_time을 버리라는 뜻은 아니다. Raw table에는 반드시 event_time column을 보존해야 한다. 다만 물리 partition은 ingestion 운영성을 우선하고, event-time 분석은 silver나 gold에서 처리하는 편이 명확하다는 뜻이다.

```text
bronze.events_raw
  partition: days(ingested_at)
  purpose: 수집 사실, replay, audit

silver.events_normalized
  partition: days(event_time)
  purpose: 정규화된 분석 이벤트

gold.daily_event_metrics
  partition: metric_date
  purpose: 소비자 계약을 가진 집계
```

이렇게 나누면 late data 정책도 계층별로 달라진다.

- Bronze는 늦은 데이터를 원본 그대로 받는다
- Silver는 event_time 기준으로 정규화하고 품질 경고를 만든다
- Gold는 지표 확정과 재계산 정책에 따라 과거 날짜를 수정한다

실무에서 중요한 것은 "하나의 partition 전략으로 모든 목적을 만족시키지 않는다"는 점이다.

---

## 설계 패턴 2: Hot Table과 Serving Table을 분리한다

Lakehouse 테이블을 serving 용도로 쓰려는 요구가 늘고 있다. 예를 들어 운영 대시보드가 최근 15분 이벤트를 조회하거나, ML feature pipeline이 최신 사용자 상태를 읽거나, reverse ETL이 세그먼트 테이블을 자주 훑는 식이다.

문제는 lakehouse가 모든 serving 요구에 자연스럽게 맞는 것은 아니라는 점이다. 특히 다음 조건이 있으면 조심해야 한다.

- 초 단위 latency가 필요하다
- point lookup이 많다
- row-level update가 매우 잦다
- 동시성이 높다
- p99 latency가 엄격하다
- 작은 결과를 매우 자주 조회한다

Lakehouse는 대용량 scan과 batch/near-real-time analytics에 강하다. 반면 key-value serving이나 OLTP lookup은 별도 serving store가 더 적합할 수 있다.

따라서 두 계층을 분리하는 패턴이 유용하다.

```text
hot operational path
  Kafka -> stream processor -> Redis/Elasticsearch/PostgreSQL serving table

analytical path
  Kafka -> lakehouse bronze/silver/gold -> BI/ML/batch analytics
```

예를 들어 "최근 5분간 주문 이상 탐지"는 stream processor와 state store가 더 적합할 수 있다. 반면 "최근 90일 매출 추이와 캠페인별 전환 분석"은 lakehouse mart가 적합하다.

둘을 억지로 하나로 합치면 다음 문제가 생긴다.

- lakehouse table에 너무 작은 micro-batch write가 많아진다
- serving 요구 때문에 compaction을 계속 미룬다
- 분석 쿼리와 operational query가 리소스를 경쟁한다
- p99 latency 요구를 맞추려고 비싼 warehouse를 상시 켜둔다
- upsert/delete가 많아져 read amplification이 증가한다

분리한다고 해서 데이터가 두 벌이라 나쁜 것이 아니다. 각 계층의 SLA가 다르면 물리 저장소도 다를 수 있다. 중요한 것은 source event id와 sequence를 공유해 서로 검증할 수 있게 만드는 것이다.

```text
검증 예시
  - serving store의 order_count와 gold mart의 order_count 차이
  - Kafka offset 기준 처리 지연
  - late event가 serving에는 반영됐지만 mart에는 아직 미확정인지 여부
```

Lakehouse를 분석의 중심으로 두되, 모든 serving 요구를 lakehouse에 밀어 넣지 않는 판단이 필요하다.

---

## 설계 패턴 3: Branch와 Tag를 운영 배포에 활용한다

Iceberg의 branch/tag나 Delta의 version/time travel은 단순 조회 편의 기능을 넘어 배포 전략으로 쓸 수 있다. 핵심은 "검증되지 않은 결과를 main snapshot으로 바로 공개하지 않는다"는 점이다.

예를 들어 중요한 정산 mart를 재계산한다고 하자. 단순한 방식은 바로 target table에 overwrite하는 것이다.

```text
job -> gold.settlement_daily overwrite -> consumers read
```

이 방식은 snapshot isolation 덕분에 중간 상태 노출은 줄일 수 있다. 하지만 commit이 성공한 뒤 품질 문제가 발견되면 이미 소비자가 잘못된 snapshot을 읽을 수 있다.

더 안전한 방식은 staged publish다.

```text
1. staging branch 또는 staging table에 결과 작성
2. 품질 검증 실행
3. reconciliation 결과 확인
4. 승인 또는 자동 조건 통과
5. main branch/tag로 publish
```

개념적으로는 소프트웨어 배포와 비슷하다.

```text
feature branch
  -> test
  -> promote
  -> main
```

데이터에서도 같은 사고방식이 통한다.

```text
recompute branch
  -> row count check
  -> primary key check
  -> amount reconciliation
  -> consumer sample query
  -> promote to production snapshot
```

이 패턴은 특히 다음 상황에서 효과가 크다.

- 정산, 회계, 과금처럼 오차 비용이 큰 mart
- 대규모 backfill
- schema 변경을 동반한 재처리
- ML feature table의 재생성
- 여러 downstream이 같은 table version을 참조해야 하는 경우

물론 branch/tag 기능은 엔진과 catalog 지원에 따라 다르다. 모든 환경에서 같은 방식으로 쓸 수 있는 것은 아니다. 그래도 운영 개념은 유지할 수 있다. 기능이 부족하면 staging table과 atomic swap 또는 view pointer를 사용할 수 있다.

```text
대안 패턴
  - gold.sales_daily_staging에 결과 작성
  - 검증 후 gold.sales_daily view가 새 table/version을 가리키게 변경
  - 이전 table은 rollback window 동안 보존
```

핵심은 publish 단계를 명시적으로 만들고, 검증 전 결과를 소비자가 읽지 않게 하는 것이다.

---

## 도구별 차이를 볼 때의 기준

Iceberg, Delta Lake, Hudi 중 무엇을 선택할지 묻는 질문은 자주 나온다. 하지만 "어느 것이 더 좋다"는 답은 보통 쓸모가 없다. 더 좋은 질문은 "우리 workload에서 어떤 실패 모드와 운영 요구가 중요한가"다.

### Catalog와 권한 모델

Lakehouse table format은 catalog와 함께 봐야 한다. 테이블 metadata를 어디에 두고, 권한을 어떻게 통제하고, 여러 엔진이 어떤 방식으로 commit하는지가 중요하다.

확인할 질문:

- Hive Metastore, AWS Glue, Nessie, Unity Catalog, REST catalog 중 무엇을 쓰는가
- commit conflict를 catalog가 어떻게 감지하는가
- branch/tag가 필요한가
- table location 권한과 catalog 권한이 분리되어 있는가
- 사용자가 object storage path를 직접 읽어 metadata 우회를 할 수 있는가
- row/column-level access control이 필요한가

Catalog 권한이 약하면 table format의 일관성을 우회하는 접근이 생긴다. 예를 들어 누군가가 storage path의 Parquet 파일을 직접 읽으면 delete file, snapshot, schema evolution semantics를 무시할 수 있다.

### Multi-engine 지원

하나의 테이블을 Spark, Trino, Flink, Athena, DuckDB, Python library가 함께 읽을 수 있다면 편하다. 하지만 multi-engine은 테스트 범위를 늘린다.

확인할 질문:

- 모든 엔진이 같은 snapshot을 읽는가
- update/delete semantics를 모두 지원하는가
- timestamp type을 같은 방식으로 해석하는가
- nested schema와 field id를 보존하는가
- compaction 후 모든 엔진에서 query가 정상인가
- vendor-specific feature를 쓰면 다른 엔진이 읽을 수 있는가

Multi-engine 환경에서는 가장 약한 reader가 운영 제약이 된다. 특정 기능이 Spark에서는 잘 되지만 Trino에서는 읽기 실패한다면 production table에 적용하기 어렵다.

### Streaming sink 성숙도

Streaming write가 중요한 환경이라면 sink의 성숙도가 핵심이다.

확인할 질문:

- exactly-once 또는 idempotent commit을 어떻게 구현하는가
- checkpoint와 table commit의 관계는 무엇인가
- 실패 후 같은 micro-batch가 재실행되면 중복 파일이 생기지 않는가
- schema evolution 중 streaming job이 어떻게 반응하는가
- partition evolution 후 writer가 정상 동작하는가
- small file을 완화할 writer-side 옵션이 있는가

Streaming sink는 단순 batch writer보다 장애 모드가 많다. 특히 checkpoint는 성공했지만 table commit이 애매한 상태, table commit은 성공했지만 checkpoint가 실패한 상태를 반드시 테스트해야 한다.

### Maintenance 기능

운영 자동화가 가능한지도 중요하다.

확인할 질문:

- data file rewrite를 조건별로 실행할 수 있는가
- delete file rewrite가 가능한가
- metadata rewrite 또는 log checkpoint 기능이 있는가
- orphan file cleanup이 dry-run을 지원하는가
- snapshot expiration이 tag/branch를 존중하는가
- maintenance job의 결과를 metric으로 남길 수 있는가

초기 PoC에서는 read/write만 본다. 하지만 production에서는 maintenance 기능의 차이가 더 크게 느껴진다.

---

## 테스트 전략: Lakehouse 변경은 데이터와 메타데이터를 함께 검증한다

Lakehouse 테이블 테스트는 일반 SQL 결과 검증만으로 부족하다. 데이터 값, 테이블 metadata, 파일 분포, 소비 엔진 호환성을 함께 확인해야 한다.

### 1. 데이터 계약 테스트

기본 품질 테스트는 여전히 필요하다.

```sql
-- primary key 중복 확인
SELECT sales_date, store_id, product_id, count(*)
FROM gold.sales_daily
GROUP BY 1, 2, 3
HAVING count(*) > 1;

-- null ratio 확인
SELECT
  count(*) AS total_rows,
  sum(CASE WHEN store_id IS NULL THEN 1 ELSE 0 END) AS null_store_id
FROM gold.sales_daily;
```

하지만 품질 테스트는 table semantics를 알아야 한다. Raw table에서 중복 event_id가 보이면 producer retry를 의미할 수 있고, current table에서 중복 primary key가 보이면 명확한 장애다.

### 2. Snapshot 전후 비교

중요한 배포나 backfill은 이전 snapshot과 새 snapshot을 비교해야 한다.

```text
비교 항목
  - row count
  - key count
  - amount sum
  - null ratio
  - enum distribution
  - min/max event_time
  - partition별 변화량
```

단순 총합만 보면 위험하다. 전체 매출 합계는 비슷하지만 특정 store의 값이 크게 바뀌었을 수 있다. Partition별, key group별, business dimension별 비교가 필요하다.

### 3. Query plan 회귀 테스트

데이터 값이 맞아도 쿼리 비용이 폭증할 수 있다. Partition 변경, clustering 변경, compaction 실패는 query plan에 영향을 준다.

대표 쿼리를 정해 아래를 비교한다.

- planning time
- selected file count
- scanned bytes
- output rows
- spill 여부
- execution time

이 테스트는 특히 schema evolution과 partition evolution 후 중요하다. 쿼리 조건은 그대로인데 partition pruning이 사라질 수 있다.

### 4. Multi-engine smoke test

여러 엔진이 같은 테이블을 읽는다면 최소 smoke test가 필요하다.

```text
Spark:
  SELECT count(*) FROM table WHERE dt = current_date - interval '1' day

Trino:
  SELECT count(*) FROM table WHERE dt = current_date - interval '1' day

Athena 또는 DuckDB:
  대표 partition sample query
```

같은 count가 나오는지만으로 충분하지 않다. Timestamp, decimal, nested field, delete semantics가 포함된 sample을 넣어야 한다.

### 5. Maintenance dry-run 테스트

Vacuum, orphan cleanup, snapshot expiration은 dry-run을 먼저 해야 한다.

검토할 항목:

- 삭제 후보 파일 수
- 삭제 후보 총 size
- 가장 최근 수정 시각
- 참조 중인 snapshot 여부
- tag/branch 보호 여부
- active writer의 staging path 포함 여부

Dry-run 결과가 평소보다 크게 튀면 자동 실행을 막아야 한다. Maintenance job에도 guardrail이 필요하다.

---

## 비용 모델: 싸게 저장해도 비싸게 읽으면 실패다

Object storage는 저렴하지만 lakehouse 전체 비용은 storage만이 아니다.

```text
총 비용
  = storage cost
  + object request cost
  + metadata planning cost
  + compute scan cost
  + compaction/rewrite cost
  + failed job/retry cost
  + 운영 인력 비용
```

Small file 문제는 이 비용 구조를 잘 보여준다. 파일당 크기가 작으면 storage 용량은 크게 늘지 않을 수 있다. 하지만 object GET/LIST 요청, query planning, scheduler overhead, compute idle time이 증가한다.

Compaction도 비용이다. Compaction을 돌리면 쿼리 비용이 줄 수 있지만, compaction 자체가 데이터를 다시 읽고 쓴다. 따라서 "얼마나 절약되는가"를 봐야 한다.

예를 들어 어떤 테이블이 하루 100번 조회되고, compaction 전후로 쿼리당 scan 비용이 30% 줄어든다고 하자. 이 테이블은 compaction 가치가 높다. 반대로 한 달에 한 번 읽는 archival table을 매일 compaction하면 낭비다.

비용 판단은 다음 기준으로 한다.

- 조회 빈도가 높은가
- 쿼리당 scan bytes가 큰가
- compaction 후 scan file count가 줄어드는가
- compaction 비용이 반복 쿼리 절감액보다 작은가
- compaction이 업무 시간대 리소스를 방해하지 않는가
- storage retention을 줄여도 복구 SLA를 만족하는가

즉 maintenance는 "깨끗해서 좋은 일"이 아니라 경제적 선택이다. 모든 테이블을 완벽하게 정리할 필요는 없다. 중요한 테이블부터 정리한다.

---

## 운영 자동화 예시: Table Health Score를 만든다면

데이터 플랫폼이 커지면 사람이 모든 테이블을 매일 볼 수 없다. 그래서 table health score 같은 요약 지표가 유용하다.

예시는 다음과 같다.

```text
health score inputs
  - freshness lag
  - p95 query planning time
  - average file size
  - files per partition
  - delete file ratio
  - snapshot count
  - last successful compaction age
  - last vacuum dry-run anomaly
  - quality test failure count
  - schema change in last 7 days
```

점수 자체가 완벽할 필요는 없다. 목적은 "어느 테이블을 먼저 봐야 하는가"를 정하는 것이다.

```text
red
  - freshness SLA 위반
  - 품질 테스트 실패
  - vacuum 위험 후보
  - delete file 비율 급증

yellow
  - 파일 수 증가 추세
  - compaction 지연
  - planning time 증가
  - schema 변경 후 smoke test 미완료

green
  - SLA 준수
  - 파일 크기 정상
  - 품질 테스트 통과
  - maintenance 최근 성공
```

이 점수를 Slack 알림이나 dashboard로 만들면 운영 우선순위가 명확해진다. 단, 점수는 owner와 함께 봐야 한다. Raw archival table의 파일 크기와 gold dashboard table의 파일 크기를 같은 기준으로 평가하면 잘못된 알림이 많아진다.

---

## 심화 운영: Writer 설정은 테이블 품질의 절반이다

Lakehouse 품질을 이야기할 때 compaction과 vacuum에 집중하기 쉽다. 하지만 많은 문제는 애초에 writer 설정에서 시작된다. 나쁜 writer가 계속 작은 파일, 잘못된 partition, 불안정한 schema를 만들면 maintenance job은 뒤처리만 하다가 끝난다.

Writer에서 확인해야 할 것은 다음이다.

- target file size
- writer parallelism
- shuffle partition 수
- partition distribution
- commit interval
- checkpoint interval
- schema merge 허용 여부
- dynamic overwrite 범위
- retry와 idempotency
- staging path와 temp file 정책

### Target file size는 읽기 엔진 기준으로 정한다

많은 팀이 target file size를 무작정 128MB 또는 1GB로 정한다. 하지만 적정 크기는 workload에 따라 다르다.

작은 파일이 유리한 경우:

- 낮은 latency가 중요하다
- partition 하나의 데이터가 작다
- point-like query가 많다
- compaction 전 임시 상태를 허용한다

큰 파일이 유리한 경우:

- scan query가 많다
- columnar compression 효과를 키우고 싶다
- scheduler overhead를 줄이고 싶다
- cold partition을 안정적으로 보관한다

대략적인 출발점은 256MB에서 512MB 정도가 많지만, 이것은 규칙이 아니라 시작값이다. Trino, Spark, Athena, Databricks, EMR, 자체 Presto cluster는 모두 최적점이 다를 수 있다. 중요한 것은 파일 크기를 "설정값"으로 끝내지 않고 실제 query metric으로 검증하는 것이다.

```text
검증 방법
  1. 대표 partition 하나를 선택한다
  2. 128MB, 256MB, 512MB, 1GB 파일 분포를 실험한다
  3. 대표 쿼리의 planning time, scan time, spill, cost를 비교한다
  4. compaction 비용까지 포함해 총 비용을 계산한다
```

큰 파일이 항상 좋은 것도 아니다. 너무 큰 파일은 task 병렬성을 낮출 수 있고, 일부 row group만 필요한 쿼리에서도 큰 파일 metadata를 다뤄야 한다. 또한 update/delete가 잦은 table에서는 큰 파일 하나를 다시 쓰는 비용이 커진다.

### Writer parallelism은 partition 수와 함께 봐야 한다

Spark job에서 shuffle partition을 크게 잡으면 병렬성이 늘어난다. 하지만 각 task가 여러 partition에 조금씩 쓰면 파일 수가 급증한다.

예를 들어 하루 24개 hour partition에 쓰는 job이 있고, shuffle partition이 2000이라고 하자. 데이터 분포가 고르지 않으면 각 hour partition마다 수백 개의 작은 파일이 생길 수 있다.

문제의 형태는 보통 이렇다.

```text
배치 입력: 50GB
shuffle partitions: 2000
output partitions: dt, hour, country
결과: 평균 5MB 파일 수만 개
```

이 경우 해결은 compaction만이 아니다. writer 단계에서 분포를 조정해야 한다.

- output partition column 기준으로 repartition한다
- 너무 세밀한 partition column을 제거한다
- adaptive query execution을 점검한다
- writer target file size를 명시한다
- streaming에서는 trigger interval과 max files per trigger를 조정한다
- hot key가 있으면 salting 또는 별도 경로를 검토한다

핵심은 "파일 수는 writer 병렬성의 부산물"이라는 점이다. Maintenance가 아니라 write path 설계에서 절반은 결정된다.

### Schema merge 자동 허용은 편하지만 위험하다

일부 엔진은 write 시 schema merge를 자동으로 허용한다. 새 컬럼이 들어오면 table schema에 자동 추가하는 식이다. 개발 환경에서는 편하지만 production raw table을 제외하면 위험할 수 있다.

위험한 이유:

- producer 오타가 새 컬럼으로 굳어질 수 있다
- nested schema가 의도치 않게 커진다
- downstream이 예상하지 못한 컬럼을 보게 된다
- schema drift가 품질 장애로 늦게 발견된다
- type conflict가 엔진마다 다르게 처리될 수 있다

Raw ingestion에서는 unknown field를 payload로 보존하는 것이 낫고, normalized table에서는 명시적 schema 변경 절차를 거치는 것이 낫다.

```text
권장 정책
  bronze raw:
    - 원본 payload 보존
    - schema drift 감지와 알림
    - 자동 table schema 확장은 제한적으로

silver/gold:
    - 명시적 schema change PR
    - contract test
    - consumer 영향 분석
```

Schema merge는 개발 속도를 높일 수 있지만 운영 계약을 흐리게 만든다. 특히 gold mart에서는 자동 schema merge를 거의 금지하는 편이 안전하다.

---

## 심화 운영: Incremental Processing과 Snapshot의 관계

Lakehouse에서는 incremental processing이 흔하다. 매번 전체 테이블을 다시 계산하지 않고 변경된 부분만 처리한다.

예시는 다음과 같다.

```text
1. 마지막 처리 snapshot id를 저장한다
2. 그 이후 추가된 파일 또는 변경된 partition을 찾는다
3. 해당 범위만 downstream table에 반영한다
```

이 방식은 효율적이지만 snapshot retention과 강하게 묶인다. Downstream job이 마지막으로 처리한 snapshot이 만료되면, "그 이후 변경분"을 정확히 계산하기 어려워질 수 있다.

### Incremental consumer가 있으면 retention을 마음대로 줄일 수 없다

예를 들어 `silver.events_normalized`를 읽어 `gold.daily_metrics`를 만드는 incremental job이 있다고 하자.

```text
gold job last_processed_snapshot = 1200
silver current_snapshot = 1250
```

Job은 1201부터 1250까지의 변경을 읽으면 된다. 그런데 snapshot expiration이 1200 이전 metadata를 지워버리면 어떻게 될까? 구현에 따라 incremental diff를 만들 수 없거나, 전체 재처리를 해야 할 수 있다.

따라서 snapshot retention은 downstream incremental lag보다 길어야 한다.

```text
snapshot retention >= max downstream lag + recovery buffer
```

여기서 downstream lag는 단순히 평소 지연만이 아니다. 주말, 장애, 배포 중단, backfill 대기까지 고려해야 한다.

### Incremental 처리는 append-only와 upsert table에서 다르다

Append-only table은 비교적 단순하다. 새 snapshot에 추가된 data file을 읽으면 된다.

```text
snapshot 100 -> files A, B
snapshot 101 -> files A, B, C
incremental: file C
```

하지만 upsert/delete table은 어렵다.

```text
snapshot 100 -> file A
snapshot 101 -> delete row in A, add file B
```

Downstream은 단순히 file B만 읽으면 안 된다. 삭제 또는 변경도 반영해야 한다. Change data feed, delete file 해석, merge logic이 필요하다.

그래서 current state table을 downstream incremental source로 쓸 때는 주의해야 한다. 가능한 경우 append-only changelog를 source로 두고, current state는 serving 또는 조회 편의 테이블로 사용하는 편이 낫다.

```text
더 명확한 구조
  bronze/silver changelog append-only
    -> incremental downstream
    -> current table materialization
```

### Snapshot 기반 재처리의 기준점

Snapshot id는 재현성 있는 기준점이다. 장애 분석이나 모델 학습에서도 유용하다.

```text
ML training dataset
  source table: silver.user_events
  snapshot id: 34567
  feature table: gold.user_features
  snapshot id: 8910
  generated_at: 2026-07-03T03:00:00Z
```

이 정보를 남기면 나중에 같은 데이터 버전으로 실험을 재현할 수 있다. 반대로 "2026년 7월 3일쯤의 데이터"처럼 모호하게 기록하면, vacuum과 compaction 이후 같은 상태를 되찾기 어렵다.

Production ML이나 정산 시스템은 snapshot id 또는 table version을 lineage에 반드시 남기는 것이 좋다.

---

## 심화 운영: 데이터 삭제와 개인정보 삭제 요청

Lakehouse에서는 개인정보 삭제 요청도 별도 설계가 필요하다. Object storage 기반 테이블은 append와 scan에 강하지만, 특정 사용자의 데이터를 즉시 찾아 지우는 작업은 비싸다.

요구사항은 보통 다음과 같이 충돌한다.

- 원천 로그는 감사와 재처리를 위해 오래 보존해야 한다
- 개인정보 삭제 요청은 정해진 기한 안에 처리해야 한다
- snapshot/time travel은 과거 파일을 보존한다
- backup과 replica에도 데이터가 남을 수 있다
- downstream mart와 feature table에도 파생 데이터가 있다

단순히 current snapshot에서 row를 삭제하는 것으로는 충분하지 않을 수 있다. 과거 snapshot, delete file, backup, downstream table 정책까지 봐야 한다.

### 삭제 요청 처리 범위

삭제 요청이 들어오면 최소한 아래 범위를 정의해야 한다.

```text
scope
  - raw event table
  - normalized event table
  - current state table
  - mart table
  - ML feature table
  - exported files
  - backup/replica
  - time travel snapshot
```

모든 데이터를 즉시 물리 삭제해야 하는지, logical delete와 snapshot expiration으로 충분한지, 법무/보안 정책에 따라 다르다. 중요한 것은 table maintenance 정책이 개인정보 삭제 정책과 충돌하지 않게 하는 것이다.

예를 들어 time travel을 90일 보존하면서 개인정보 삭제는 30일 내 완료해야 한다면, 삭제된 사용자의 row가 과거 snapshot에 남는 문제를 어떻게 다룰지 정해야 한다.

### Delete-heavy workload의 성능 문제

사용자 단위 삭제가 많으면 delete file이 늘어난다.

```text
DELETE FROM events
WHERE user_id = 'U-123';
```

대형 이벤트 테이블에서 이런 삭제가 반복되면 많은 data file에 작은 delete marker가 쌓인다. 쿼리는 매번 data file과 delete file을 함께 읽어야 하므로 느려진다.

대응 방법은 몇 가지다.

- user_id 기반 clustering을 일부 적용해 삭제 범위를 줄인다
- 삭제 요청을 batch로 모아 처리한다
- delete file rewrite를 주기적으로 실행한다
- 일정 기간 후 data file rewrite로 물리 삭제를 확정한다
- raw table의 개인정보 필드를 tokenization 또는 encryption으로 분리한다

개인정보 삭제는 데이터 모델링 단계에서 고려해야 한다. 나중에 대형 raw table에서 사용자별 삭제를 빠르게 하려고 하면 비용이 크다.

### 암호화와 키 삭제 전략

일부 환경에서는 개인 식별 정보를 별도 암호화하고, 삭제 요청 시 키를 폐기하는 방식도 검토한다. 이를 crypto-shredding이라고 부르기도 한다.

개념은 다음과 같다.

```text
raw event payload
  user attributes encrypted with per-user or per-tenant key

deletion request
  key disabled or destroyed
  encrypted data remains but practically unreadable
```

이 방식은 강력할 수 있지만 모든 문제를 해결하지는 않는다.

- 파생 테이블에 평문 값이 남으면 소용없다
- 키 관리 시스템의 감사와 권한이 중요하다
- 분석 쿼리에서 복호화 비용과 권한 처리가 필요하다
- 법적 요구가 물리 삭제를 요구할 수 있다

따라서 암호화 전략도 lakehouse table lifecycle과 함께 설계해야 한다.

---

## 심화 운영: 데이터 품질 검증은 Commit 전후로 나뉜다

데이터 품질 검증을 언제 실행할지도 중요하다. Commit 전에 검증할 수 있는 것과 commit 후에만 검증 가능한 것이 다르다.

### Commit 전 검증

Staging 결과를 만들고 아직 production snapshot으로 공개하지 않은 상태에서 검증한다.

좋은 후보:

- schema compatibility
- primary key uniqueness
- row count 범위
- amount reconciliation
- null ratio
- partition coverage
- enum value check
- sample business query

Commit 전 검증은 잘못된 결과가 소비자에게 보이기 전에 막을 수 있다는 장점이 있다. 단점은 검증 비용이 배포 latency를 늘린다는 점이다.

중요한 mart라면 commit 전 검증을 강하게 걸어야 한다. Raw ingestion처럼 계속 들어오는 테이블은 commit 전 모든 검증을 걸기 어렵기 때문에 commit 후 모니터링을 함께 사용한다.

### Commit 후 검증

Production snapshot이 공개된 뒤 실제 query engine과 downstream 관점에서 검증한다.

좋은 후보:

- 대표 BI query 성공 여부
- multi-engine read smoke test
- query planning time 변화
- downstream dbt model 성공 여부
- dashboard refresh 성공 여부
- feature pipeline input count

Commit 후 검증은 실제 소비 환경을 보기 때문에 중요하다. 예를 들어 Spark에서는 검증이 통과했지만 Trino에서 timestamp 해석 문제로 실패할 수 있다. Commit 전 Spark-only 검증만으로는 놓친다.

### 품질 실패 시 자동 rollback 기준

모든 실패에 자동 rollback을 걸면 위험하다. 일시적인 downstream query 실패 때문에 정상 데이터를 되돌릴 수 있다. 반대로 명확한 데이터 오염은 빠르게 rollback해야 한다.

자동 rollback 후보:

- primary key 중복이 0이어야 하는 table에서 중복 발생
- row count가 이전 7일 평균 대비 90% 이상 감소
- 정산 금액 reconciliation이 threshold 초과
- 필수 partition 누락
- schema breaking change 감지

수동 판단 후보:

- 일부 dashboard query timeout
- null ratio 소폭 증가
- 특정 dimension 분포 변화
- downstream non-critical job 실패

Rollback은 기술 기능이 아니라 운영 정책이다. 어떤 실패가 자동 rollback인지, 어떤 실패는 owner 판단인지 미리 정해야 한다.

---

## 장애 대응 시나리오 1: 잘못된 배치가 mart를 덮어썼다

상황:

```text
sales_daily mart가 07:00 배치 후 전일 대비 40% 감소했다.
원인은 promotion_amount 계산식 변경으로 확인됐다.
BI 대시보드는 이미 새 snapshot을 보고 있다.
```

대응 순서:

1. 현재 snapshot/version과 직전 정상 snapshot/version을 확인한다
2. 문제가 있는 commit의 writer job, run id, 변경 파일 범위를 기록한다
3. 품질 검증을 위해 직전 snapshot 기준 row count와 금액 합계를 비교한다
4. 업무 영향이 크면 직전 정상 snapshot으로 rollback하거나 restore commit을 만든다
5. 잘못된 job을 중지하고 수정 배치를 staging에서 재검증한다
6. 수정 snapshot을 새로 publish한다
7. 잘못된 snapshot은 즉시 vacuum하지 않고 incident window 동안 보존한다

중요한 점은 rollback 후에도 사고 분석을 위해 잘못된 snapshot을 잠시 보존하는 것이다. 바로 지워버리면 원인 분석과 재현이 어려워진다.

## 장애 대응 시나리오 2: 쿼리 planning 시간이 갑자기 길어졌다

상황:

```text
최근 3일 동안 events 테이블 쿼리 시작 시간이 5초에서 90초로 증가했다.
실제 scan bytes는 크게 늘지 않았다.
```

가능한 원인:

- 작은 파일이 급증했다
- manifest 또는 transaction log가 커졌다
- checkpoint 생성이 지연되었다
- partition별 파일 수가 비정상적으로 늘었다
- catalog cache가 자주 무효화된다
- delete file이 누적되어 planning에서 고려할 항목이 늘었다

대응:

1. 최근 commit history와 파일 수 증가를 확인한다
2. 특정 writer가 작은 파일을 만들기 시작했는지 본다
3. hot partition과 cold partition을 분리해 compaction 후보를 잡는다
4. metadata rewrite 또는 checkpoint 생성을 실행한다
5. 대표 쿼리에서 scan file count와 planning time을 비교한다
6. streaming trigger interval, shuffle partition, target file size를 조정한다

여기서 바로 cluster size를 키우면 비용만 늘 수 있다. Planning 병목은 compute scale-out으로 해결되지 않는 경우가 많다.

## 장애 대응 시나리오 3: Vacuum 후 일부 쿼리가 실패한다

상황:

```text
오전 vacuum 이후 장기 실행 리포트 job이 file not found로 실패했다.
```

가능한 원인:

- retention 기간이 장기 실행 쿼리보다 짧았다
- query engine이 old snapshot을 잡고 있었는데 파일이 삭제됐다
- catalog cache 또는 version pinning 정책을 고려하지 않았다
- downstream job이 time travel version을 참조하고 있었다

대응:

1. 삭제된 파일 목록과 vacuum 실행 시각을 확인한다
2. 실패한 쿼리의 시작 시각과 참조 version을 확인한다
3. object storage versioning이나 backup에서 복구 가능한지 본다
4. retention policy를 즉시 늘리고 vacuum job을 중지한다
5. dry-run 검증과 장기 실행 쿼리 감지 로직을 추가한다

이 장애는 예방이 가장 중요하다. Vacuum은 "정리 작업"이 아니라 "복구 가능한 과거를 줄이는 배포"처럼 다뤄야 한다.

---

## 배포 전 체크리스트

Lakehouse 테이블을 새로 만들거나 운영 정책을 바꾸기 전에는 아래를 확인한다.

### 테이블 설계

- 이 테이블은 raw, current, mart 중 무엇인가
- row 하나의 grain이 명확한가
- primary key 또는 natural key가 정의되어 있는가
- append-only인지 upsert/delete가 필요한지 결정했는가
- event time, ingest time, business timezone을 구분했는가
- 소비자가 주로 쓰는 쿼리 패턴을 확인했는가

### Partition과 물리 배치

- partition column이 실제 filter 조건과 맞는가
- partition cardinality가 너무 높지 않은가
- partition 하나의 평균 데이터 크기가 적절한가
- late arriving data가 과거 partition에 쓰일 때 비용을 계산했는가
- clustering/sorting이 필요한 쿼리 패턴이 있는가
- target file size와 writer parallelism을 정했는가

### Write와 Commit

- batch overwrite가 snapshot 단위로 원자적으로 공개되는가
- streaming sink가 small file을 과도하게 만들지 않는가
- commit conflict가 발생할 때 retry 정책이 있는가
- failed write의 orphan file을 정리할 방법이 있는가
- backfill은 staging과 검증 절차를 거치는가
- 여러 writer가 같은 table location에 접근하지 않도록 권한을 분리했는가

### Schema와 계약

- schema 변경 절차가 safe, risky, breaking으로 나뉘는가
- nullable, default, type promotion 정책이 있는가
- timestamp와 timezone 의미가 문서화되어 있는가
- rename과 delete는 deprecation window를 거치는가
- downstream 소비자 목록과 owner를 알고 있는가
- data contract와 catalog가 함께 갱신되는가

### Maintenance

- compaction 주기와 범위가 테이블별로 정의되어 있는가
- hot, warm, cold partition을 다르게 다루는가
- snapshot retention과 vacuum retention이 복구 요구와 맞는가
- metadata rewrite 또는 log checkpoint 정책이 있는가
- delete file 또는 deletion vector 누적을 모니터링하는가
- maintenance job이 업무 쿼리와 리소스를 과도하게 경쟁하지 않는가

### Observability

- 파일 수, 평균 파일 크기, snapshot 수를 보고 있는가
- query planning time과 scan file count를 보고 있는가
- freshness, row count, duplicate, null ratio 테스트가 있는가
- compaction/vacuum 실행 결과가 기록되는가
- rollback 가능한 snapshot/version이 명시되어 있는가
- 장애 시 어느 snapshot이 정상인지 빠르게 찾을 수 있는가

---

## 팀 운영 모델: Lakehouse 테이블에는 owner와 runbook이 필요하다

Lakehouse가 커지면 테이블은 코드와 같은 운영 자산이 된다. 단순히 "data platform 팀이 storage를 관리한다"로는 부족하다.

테이블마다 최소한 아래 정보가 있어야 한다.

```yaml
table: gold.sales_daily
owner:
  team: analytics-engineering
  oncall: "#analytics-oncall"
contract:
  grain: [sales_date, store_id, product_id]
  freshness_sla: "07:30 Asia/Seoul"
  retention: "snapshot 30 days, data 3 years"
maintenance:
  compaction: "daily after publish, target 512MB"
  vacuum: "weekly, retention 30 days, dry-run required"
  quality_checks:
    - primary_key_unique
    - row_count_anomaly
    - revenue_reconciliation
rollback:
  procedure: "restore previous tagged snapshot"
  max_window: "30 days"
consumers:
  - BI sales dashboard
  - finance reconciliation
  - CRM segmentation
```

이 정보가 없으면 장애 때 사람들은 storage path, job log, dashboard query를 뒤지며 시간을 쓴다. 반대로 owner, freshness, rollback, maintenance 정책이 있으면 대응이 빨라진다.

특히 중요한 것은 runbook이다.

- compaction 실패 시 재시도해도 되는가
- vacuum dry-run에서 예상보다 많은 파일이 나오면 누구에게 알리는가
- schema 변경 PR은 누가 승인하는가
- backfill 후 downstream을 어떻게 재실행하는가
- rollback 시 어떤 dashboard refresh를 다시 돌리는가
- orphan cleanup이 삭제하면 안 되는 prefix는 무엇인가

Lakehouse는 데이터 엔지니어링과 플랫폼 운영의 경계에 있다. 그래서 코드보다 운영 문서가 더 중요해지는 순간이 많다.

---

## 한 줄 정리

Lakehouse table format을 도입했다면 이제 시작이다. 안정적인 운영은 snapshot으로 일관성을 만들고, compaction으로 파일 분포를 관리하며, schema evolution을 계약으로 통제하고, vacuum을 복구 정책과 함께 다루는 데서 나온다.

**파일을 저장하는 것은 쉽고, 유효한 테이블 상태를 오래 건강하게 유지하는 것이 어렵다.**
