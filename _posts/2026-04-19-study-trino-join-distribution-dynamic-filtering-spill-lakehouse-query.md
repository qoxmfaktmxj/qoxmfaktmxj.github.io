---
layout: post
title: "Trino 실전: Join Distribution, Dynamic Filtering, Spill로 느린 Lakehouse 쿼리를 운영 기준으로 다루는 법"
date: 2026-04-19 11:40:00 +0900
categories: [data-infra]
tags: [study, data-infra, trino, lakehouse, join-distribution, dynamic-filtering, spill, cbo, iceberg]
permalink: /data-infra/2026/04/19/study-trino-join-distribution-dynamic-filtering-spill-lakehouse-query.html
---

## 배경: 스토리지는 이미 분리했는데, 왜 Lakehouse 쿼리는 여전히 느리고 비쌀까?

데이터 플랫폼이 어느 정도 커지면 팀은 보통 비슷한 구조로 수렴한다.

- 원천 이벤트는 Kafka나 CDC로 들어온다
- 적재는 S3, HDFS, GCS 같은 오브젝트 스토리지에 쌓는다
- 테이블 포맷은 Iceberg, Delta Lake, Hive 메타데이터 중 하나를 쓴다
- 배치 변환은 Spark, Flink, dbt, Airflow가 맡는다
- 조회는 BI나 API, 분석가 SQL, 운영 대시보드가 맡는다

문제는 여기서 끝나지 않는다.

스토리지를 분리하고 파일 포맷을 컬럼형으로 바꾸고, 메타데이터 레이어까지 얹었는데도 실제 쿼리는 자꾸 기대보다 느리다.

현장에서 자주 보는 증상은 이렇다.

- 분명 Parquet인데도 스캔량이 너무 크다
- 작은 차원 테이블과 조인했을 뿐인데 메모리 에러가 난다
- 같은 쿼리가 어떤 날은 12초, 어떤 날은 90초가 걸린다
- Spark에서는 돌던 쿼리가 Trino에서는 자꾸 spill이 난다
- `AUTOMATIC`에 맡겼는데 join distribution이 의도와 다르게 잡힌다
- partition pruning이 될 줄 알았는데 사실상 full scan처럼 동작한다
- 운영자는 CPU보다 네트워크, 메모리, 작은 파일 수, split 수와 싸우게 된다

이 지점에서 Trino를 단순히 "분산 SQL 엔진"으로 이해하면 문제를 계속 표면적으로만 다루게 된다.

실무에서 Trino의 핵심은 더 구체적이다.

> Trino는 저장을 책임지는 시스템이 아니라, 이미 저장된 데이터에 대해 어떤 조인 전략을 고르고, 어떤 런타임 필터를 만들고, 어디서 메모리를 쓰고, 언제 디스크로 밀어내며, 얼마나 적게 읽게 만들 것인가를 조정하는 실행 엔진이다.

즉 Trino 튜닝은 SQL 문법보다 **읽기 경로와 실행 경로를 얼마나 예측 가능하게 만들 수 있느냐**의 문제에 가깝다.

오늘 글은 Trino 소개가 아니다.

중급 이상 개발자가 실제 Lakehouse 운영에서 자주 부딪히는 아래 질문을 기준으로, Trino를 운영 가능한 수준에서 이해하는 것이 목표다.

1. Trino 성능 문제를 볼 때 왜 CPU보다 먼저 파일 레이아웃, 통계, 조인 방향을 봐야 하는가
2. `join_distribution_type`의 broadcast, partitioned, automatic은 언제 각각 유리한가
3. Dynamic filtering은 왜 어떤 쿼리에서는 극적으로 빠르고, 어떤 쿼리에서는 거의 효과가 없는가
4. Spill은 구세주인가, 장애 완충장치인가, 아니면 느린 쿼리를 연명시키는 비용 장치인가
5. 실무에서 어떤 SQL 모양과 테이블 설계가 Trino를 빠르게 만들고, 어떤 패턴이 느리게 만드는가
6. 운영자가 Web UI, EXPLAIN, 메트릭에서 무엇을 봐야 재발 방지까지 이어지는가

결론부터 말하면, Trino 최적화의 본질은 이것이다.

**저장 구조, 통계, 조인 전략, 런타임 필터, 메모리 압박을 서로 분리해서 보지 말고 하나의 읽기 경로로 묶어 보는 것.**

이 관점이 잡히면, 단순히 "이 쿼리 왜 느리지?"에서 끝나지 않고,

- 어떤 테이블이 build side가 되어야 하는지
- 어떤 테이블은 file compaction이 먼저인지
- 어떤 쿼리는 broadcast로 강제할 가치가 있는지
- 어떤 spill은 받아들이고 어떤 spill은 구조적으로 없애야 하는지
- 어떤 지표를 대시보드에 붙여야 하는지

까지 연결된다.

---

## 먼저 큰 그림: Trino는 스토리지 최적화 도구가 아니라, 잘못 저장된 데이터를 더 비싸게 읽게 만드는 엔진이기도 하다

Trino를 처음 도입할 때 흔한 착각이 하나 있다.

"Trino가 똑똑하니까 웬만한 비효율은 엔진이 해결해주겠지"

실무에서는 이 기대가 가장 위험하다.

Trino는 저장 엔진이 아니다. 데이터를 정렬해 두지도 않고, 자동으로 compaction을 해주지도 않으며, 테이블 품질이 나빠도 마법처럼 빠르게 만들어주지 않는다. 오히려 다음 조건이 나쁘면 그 비용을 매우 정직하게 드러낸다.

- 작은 파일이 너무 많다
- 파티션 설계가 쿼리 패턴과 안 맞는다
- 테이블 통계가 없거나 오래됐다
- dimension이 실제로는 작지 않은데 broadcast처럼 기대한다
- build side와 probe side가 뒤집혀 있다
- connector가 pushdown을 충분히 못 한다
- 선택도가 높은 필터가 조인 이후에야 적용된다

즉 Trino를 잘 쓰려면 먼저 역할 경계를 분명히 해야 한다.

### Trino가 잘하는 것

- 여러 스토리지와 카탈로그를 SQL 하나로 묶어 조회하기
- 대화형 분석 쿼리를 짧은 대기시간으로 실행하기
- 비용 기반으로 join distribution과 실행 계획을 선택하기
- 런타임에 dynamic filter를 수집해 불필요한 스캔을 줄이기
- 메모리 압박 시 일부 연산을 spill로 연명시키기
- Lakehouse, warehouse, OLTP 일부 소스를 느슨하게 연결하는 federation 역할 수행하기

### Trino가 대신해주지 않는 것

- 작은 파일 정리와 compaction
- 잘못된 partition 설계 교정
- 신뢰할 수 없는 table statistics 자동 보정
- skew가 심한 데이터의 근본 해결
- 너무 큰 dimension을 갑자기 작은 build side로 바꿔주는 일
- 비즈니스적으로 잘못 작성된 SQL의 선택도 복원

이걸 한 문장으로 줄이면 이렇다.

**Trino는 좋은 데이터를 더 빨리 읽게 해주고, 나쁜 데이터를 더 빨리 읽으려다 문제를 터뜨리는 엔진이다.**

그래서 성능 이슈를 볼 때도 "클러스터 스펙을 키울까"보다 먼저 아래를 묻는 편이 낫다.

- 읽는 파일 수와 총 스캔 바이트가 적절한가
- 필터가 partition pruning, file pruning, row group pruning으로 실제 이어지는가
- join의 build side가 정말 작은가
- 동적 필터를 만들 수 있는 쿼리 형태인가
- spill이 예외 상황인지 일상인지

이 감각이 없으면 Trino 운영은 결국 더 큰 워커, 더 큰 메모리, 더 비싼 디스크를 사는 방향으로만 흐른다.

---

## 핵심 개념 1: 성능 문제의 절반은 SQL보다 저장 레이아웃과 통계에서 시작된다

Trino는 쿼리 엔진이지만, 성능의 출발점은 의외로 SQL 문장보다 테이블 상태다.

예를 들어 같은 집계를 한다고 해보자.

- 테이블 A: 날짜 기준 파티션, 파일 크기 안정적, Parquet row group 적절, 통계 최신
- 테이블 B: 하루 파티션 안에 3만 개 작은 파일, 컬럼 통계 없음, late data로 파일 난립

두 테이블에 같은 SQL을 날려도 체감 성능은 완전히 다르다.

왜냐하면 Trino가 실제로 결정하는 것은 "SQL을 어떻게 실행할까" 이전에 "애초에 몇 개 파일을 열고, 몇 개 split을 만들고, 어떤 파일은 안 읽을 수 있나"이기 때문이다.

### 파일 수가 많으면 왜 단순히 I/O만 느린 것이 아닌가

작은 파일 폭증은 단순 스캔 문제로 끝나지 않는다.

- split 수가 증가한다
- scheduler 오버헤드가 커진다
- task와 exchange 관리 비용이 늘어난다
- S3/GCS 같은 오브젝트 스토리지 요청 수가 늘어난다
- selective query도 파일을 너무 많이 열어야 해서 latency가 흔들린다
- dynamic filtering이 있어도 이미 split enumeration 비용이 커진다

즉 작은 파일 문제는 "읽는 바이트 수"만의 문제가 아니라 **읽기 전에 해야 하는 준비 작업 전체**를 비싸게 만든다.

### 통계가 왜 중요한가

Trino의 cost-based optimizer는 아래를 알아야 join 전략을 그나마 제대로 고른다.

- 각 테이블/파티션의 대략적인 row 수
- 컬럼 distinct count나 분포 힌트
- 필터 적용 후 build side가 얼마나 줄어드는지

통계가 부실하면 어떤 일이 생길까?

- `AUTOMATIC`이 사실상 안전한 추정이 아니라 보수적 선택이 된다
- 작은 차원 테이블을 broadcast하지 못하고 partitioned join으로 간다
- 반대로 생각보다 큰 build side를 복제해 워커 메모리를 압박한다
- join 순서 최적화가 기대만큼 일어나지 않는다

실무에서는 `AUTOMATIC`이 곧 "항상 최적"이 아니다.

정확히는,

> `AUTOMATIC`은 통계가 충분할 때 꽤 똑똑해질 수 있고, 통계가 빈약할 때는 그냥 덜 위험한 쪽으로 흐르거나 예상 밖 선택을 할 수 있다.

그래서 Trino 성능을 다룰 때는 SQL만 읽지 말고 테이블 메타데이터 상태도 함께 읽어야 한다.

### 운영 관점에서 먼저 확인할 것

- 최근 compaction이 정상 수행되었는가
- 하루/시간 파티션별 파일 수가 급증하지 않았는가
- Iceberg/Delta/Hive 메타데이터가 오래되지 않았는가
- 통계 수집이나 metadata refresh 주기가 너무 느리지 않은가
- 쿼리에서 실제로 쓰는 필터 축과 partition 축이 맞는가

이 단계가 빠지면 Trino 튜닝은 늘 엔진 탓으로 흐른다.

---

## 핵심 개념 2: Join Distribution은 "어떤 조인이 빠른가"가 아니라 "어떤 메모리 모델을 감당할 것인가"의 선택이다

Trino 성능에서 가장 자주 체감 차이를 만드는 것이 join distribution이다.

문서 기준으로 `join_distribution_type`은 보통 세 가지다.

- `AUTOMATIC`
- `PARTITIONED`
- `BROADCAST`

이걸 단순히 알고리즘 선택으로만 보면 부족하다. 실무에서는 아래처럼 이해하는 편이 훨씬 정확하다.

### `BROADCAST`의 본질

오른쪽 build side를 각 워커에 복제해서, 왼쪽 probe side가 로컬에서 빠르게 조인하게 만드는 방식이다.

장점:

- 작은 dimension과 큰 fact 조인에서 매우 빠를 수 있다
- probe side 재분배가 줄어 네트워크 비용이 감소한다
- dynamic filtering과 결합될 때 효과가 좋다
- 대화형 쿼리에서 latency가 크게 줄 수 있다

단점:

- 오른쪽 테이블이 각 노드 메모리에 들어가야 한다
- 필터 후에도 build side가 충분히 작다는 전제가 필요하다
- 예상보다 큰 build side가 들어오면 워커별 메모리 압박이 커진다
- skew나 잘못된 추정이 있으면 일부 노드에서 먼저 터질 수 있다

한 줄로 말하면,

**broadcast는 빠르지만 메모리를 각 노드에 선불로 요구한다.**

### `PARTITIONED`의 본질

양쪽 테이블을 조인 키 기준으로 해시 재분배한 뒤, 각 노드가 일부 키 구간만 맡아 조인하는 방식이다.

장점:

- 더 큰 조인을 다룰 수 있다
- build side 전체를 모든 노드에 복제하지 않아도 된다
- 메모리 부담이 클러스터 전체로 분산된다
- 큰 fact 대 fact에 가까운 조인에서 더 현실적이다

단점:

- 양쪽 재분배 비용이 크다
- 네트워크 shuffle이 커진다
- 선택도가 높은 작은 dimension 조인에서도 느려질 수 있다
- 데이터 skew가 있으면 특정 파티션만 과열된다

한 줄로 말하면,

**partitioned는 메모리 안정성을 얻는 대신 네트워크와 shuffle 비용을 낸다.**

### `AUTOMATIC`을 믿어도 되는가

대부분의 운영 환경에서 기본값으로는 맞다. 하지만 조건이 있다.

- 테이블 통계가 어느 정도 신뢰 가능해야 한다
- 필터가 조인 전에 얼마나 줄어드는지 optimizer가 읽을 수 있어야 한다
- connector와 catalog가 통계 정보를 충분히 제공해야 한다
- SQL이 optimizer가 해석하기 쉬운 모양이어야 한다

아래 같은 경우는 `AUTOMATIC`을 맹신하면 안 된다.

- 임시 테이블, nested subquery, CTE 확장 후 선택도 추정이 흐려진다
- 카탈로그 간 federation으로 정확한 비용 모델이 어렵다
- dimension이 "원본은 크지만 필터 후 작아지는" 형태인데 통계가 오래됐다
- 특정 테넌트 데이터 쏠림이 심해 평균값 기반 추정이 틀린다

### 어떤 기준으로 강제할까

실무에서는 아래 질문으로 접근하는 편이 낫다.

1. 필터 후 build side가 워커별 메모리에 안전하게 들어가는가
2. 지금 병목이 네트워크 shuffle인가, build 메모리인가
3. 쿼리가 반복 실행되는 고정 패턴인가, 일회성 ad-hoc인가
4. 같은 SQL을 API나 대시보드에서 초 단위로 자주 때리는가

반복성 높은 대시보드 쿼리라면, 측정 후 `BROADCAST` 강제가 가치 있을 때가 많다. 반대로 ad-hoc이나 데이터량 변동 폭이 큰 쿼리는 `AUTOMATIC` 또는 `PARTITIONED`가 더 안전하다.

---

## 핵심 개념 3: Dynamic Filtering은 "조인 후 버릴 데이터"를 읽기 전에 줄이는 런타임 최적화다

Dynamic filtering은 Trino에서 체감 효과가 매우 큰 기능 중 하나다.

개념 자체는 단순하다.

- 오른쪽 build side에서 실제 조인 키 후보를 수집한다
- 이 값을 런타임 필터로 만들어 왼쪽 probe side scan에 밀어 넣는다
- 그러면 조인에 참여할 가능성이 없는 데이터는 아예 덜 읽게 된다

특히 작은 dimension을 강하게 필터링한 뒤 큰 fact와 조인할 때 효과가 좋다.

예를 들어 이런 형태다.

```sql
SELECT sum(o.gmv)
FROM lake.orders o
JOIN lake.stores s
  ON o.store_id = s.store_id
WHERE s.region = 'KR'
  AND s.is_enterprise = true
  AND o.order_date BETWEEN DATE '2026-04-01' AND DATE '2026-04-07';
```

여기서 `stores`가 충분히 작고 `region='KR'`, `is_enterprise=true`로 더 줄어든다면, Trino는 build side에서 남은 `store_id` 집합을 런타임에 만들고 `orders` 스캔에 밀어 넣을 수 있다.

그러면 아래 비용이 줄어든다.

- fact table scan 바이트
- 원격 스토리지 읽기 요청 수
- 불필요한 split 처리량
- join 단계에서 버려질 row 수

### 왜 어떤 쿼리에서는 효과가 없을까

Dynamic filtering이 만능인 것처럼 기대하면 실망한다. 보통 아래 조건이 맞아야 잘 듣는다.

- join이 inner/right/semi join 등 지원되는 형태여야 한다
- build side가 충분히 작고 선택적이어야 한다
- connector가 runtime filter pushdown을 실제 활용해야 한다
- split enumeration 단계나 reader 단계에서 pruning으로 이어져야 한다
- 조인 키와 저장 레이아웃 사이 상관관계가 어느 정도 있어야 한다

효과가 약한 대표 사례는 이렇다.

- build side가 이미 너무 크다
- join key의 distinct 값이 너무 많아 필터가 사실상 넓다
- 파일 레이아웃이 조인 키와 상관없어 reader pruning 효과가 작다
- connector가 dynamic filter를 일부만 활용한다
- build side 수집이 늦어 probe side가 먼저 대부분 읽어버린다

즉 dynamic filtering은 "있으면 무조건 빠름"이 아니라,

**작고 선택적인 build side + 이를 활용할 수 있는 connector + 읽기 전에 멈출 수 있는 저장 구조**가 만날 때 강하다.

### 어떻게 확인할까

실무에서는 감으로 판단하지 말고 확인해야 한다.

1. `EXPLAIN`에서 `dynamicFilterAssignments`가 보이는가
2. `ScanFilterProject` 계열 노드에 dynamic filter가 붙었는가
3. `EXPLAIN ANALYZE`나 Web UI에서 dynamic filter 수집 시간이 과도하지 않은가
4. 실제 scan row/bytes가 기대만큼 줄었는가
5. dynamic filter가 생겼는데도 wall time이 안 줄면 split 수, 작은 파일, build 지연을 의심할 수 있는가

중요한 점 하나 더.

Dynamic filtering은 build side가 작을수록 유리하다. 그래서 결국 이 기능도 join direction, 통계 품질, 필터 위치에 다시 연결된다.

즉 별도 기능이 아니라 **좋은 조인 설계의 증폭기**에 가깝다.

---

## 핵심 개념 4: Spill은 실패를 늦춰주는 장치이지, 느린 쿼리를 빠르게 만들어주는 기능이 아니다

Trino 운영에서 spill은 자주 오해된다.

메모리 에러가 줄어드니 마치 안정성 기능처럼 보이지만, 실제론 훨씬 신중하게 봐야 한다.

문서 관점에서 spill은 메모리 집약적인 중간 결과를 디스크로 내려서 쿼리를 계속 진행하게 해주는 메커니즘이다. `spill_enabled`와 spill path를 설정하면 joins, aggregations, order by, window 일부 연산에서 활용될 수 있다.

하지만 현장 감각으로 번역하면 이렇다.

> Spill은 "원래 메모리 안에 있어야 가장 빠른 작업"을 디스크로 밀어내는 것이다. 그래서 성공률은 높일 수 있지만, 실행 시간은 종종 배 단위로 느려진다.

### spill이 의미 있는 경우

- 드물게 발생하는 대형 ad-hoc 쿼리를 아예 죽이지 않고 끝내고 싶다
- 운영자가 일부 느린 분석 쿼리를 허용하는 대신 클러스터 전체 장애는 피하고 싶다
- join이나 aggregation이 순간적으로 메모리 한도를 넘는 경우를 완충하고 싶다
- 반복 쿼리가 아니라 일시성 탐색 쿼리다

### spill을 일상 상태로 두면 안 되는 경우

- API/BI 대시보드 쿼리가 상시 spill 난다
- 특정 테이블 조인마다 반복적으로 spill이 발생한다
- spill volume이 워커 디스크 saturation을 유발한다
- system disk나 로그 디스크를 spill path로 써서 노드 전체가 흔들린다
- spill이 발생해도 결국 unspill 단계에서 다시 OOM이 난다

즉 spill은 **평소 성능 전략**이 아니라 **예외 완충 전략**으로 보는 편이 맞다.

### 왜 spill이 위험한가

1. 디스크 I/O가 급격히 늘어난다
2. JVM 로그와 같은 디스크를 쓰면 노드 전체가 불안정해진다
3. 쿼리 latency tail이 길어져 SLA가 흔들린다
4. 한 쿼리의 spill이 다른 쿼리에도 간접 피해를 준다
5. "돌아가긴 하네"라는 착시 때문에 근본 원인을 미루게 된다

### spill을 볼 때 함께 봐야 할 것

- query 당 spill bytes
- node별 spill path 사용률
- 디스크 saturation과 queue depth
- 어떤 operator에서 spill이 났는가(join, aggregation, sort, window)
- build side 추정치와 실제 row 수 차이
- `query_max_memory`, `query_max_memory_per_node` 설정 대비 실제 사용 패턴

특히 join spill이 반복되면 단순 메모리 조정보다 먼저 아래를 의심해야 한다.

- broadcast가 과한가
- build side를 더 줄일 수 없는가
- dimension 필터가 join 이전에 적용되는가
- 파일/파티션 pruning이 안 돼 input 자체가 너무 큰가
- skew 때문에 특정 파티션만 비대해지는가

---

## 핵심 개념 5: Trino 튜닝은 쿼리 튜닝이 아니라 "읽기 전에 얼마나 덜 읽게 할 것인가" 튜닝이다

대부분의 느린 쿼리는 join 단계에서 죽는 것처럼 보인다. 하지만 실제 원인은 그 전에 시작되는 경우가 많다.

- 너무 많은 partition을 열었다
- 너무 많은 파일을 건드렸다
- 불필요한 컬럼까지 읽었다
- 조인 전 필터가 충분히 좁혀지지 않았다
- dimension이 작아질 기회를 놓쳤다

그래서 Trino 쿼리를 튜닝할 때는 아래 순서로 보는 편이 좋다.

1. 얼마나 읽었나
2. 왜 그만큼 읽었나
3. 조인 전략이 적절했나
4. 메모리/네트워크 비용이 어디서 커졌나
5. 이 비용을 SQL 변경 없이 저장 구조에서 먼저 줄일 수 있나

### SQL에서 바로 효과가 큰 패턴

#### 1) 필터를 가능하면 조인 이전에 분명하게 만든다

좋지 않은 예:

```sql
SELECT *
FROM fact_orders o
JOIN dim_store s ON o.store_id = s.store_id
WHERE date(o.created_at) BETWEEN DATE '2026-04-01' AND DATE '2026-04-07'
  AND s.region = 'KR';
```

더 나은 예:

```sql
WITH filtered_store AS (
  SELECT store_id
  FROM dim_store
  WHERE region = 'KR'
    AND is_active = true
)
SELECT o.order_date, sum(o.gmv)
FROM fact_orders o
JOIN filtered_store s ON o.store_id = s.store_id
WHERE o.order_date BETWEEN DATE '2026-04-01' AND DATE '2026-04-07'
GROUP BY 1;
```

핵심은 형식 자체보다 **build side를 작고 명확하게 만드는 것**이다.

#### 2) partition column에 함수 감싸기를 줄인다

`date(created_at)` 같은 표현은 connector와 포맷에 따라 pruning을 약하게 만들 수 있다. 가능하면 저장된 partition column을 직접 쓰는 편이 안전하다.

#### 3) `SELECT *`를 버린다

컬럼형 포맷이라도 필요 없는 컬럼을 읽으면 디코딩과 I/O가 커진다. wide table일수록 차이가 크다.

#### 4) high-cardinality group by를 무심코 던지지 않는다

join보다 aggregation이 먼저 메모리 병목이 되기도 한다. 특히 세션 단위, 이벤트 단위 고카디널리티 집계는 spill을 부르기 쉽다.

#### 5) 너무 늦은 semi-join 필터를 피한다

`IN (subquery)`나 EXISTS가 optimizer에 의해 잘 풀리는 경우도 있지만, 구조가 복잡할수록 build/probe 관계가 흐려질 수 있다. 반복 쿼리는 실행 계획을 실제로 확인해야 한다.

---

## 실무 예시: Iceberg 기반 주문 분석 쿼리에서 90초를 11초대로 줄인 과정

가상의 예시지만, 실제 현장에서 매우 흔한 패턴을 압축해보자.

### 상황

- 저장소: S3 + Iceberg
- 엔진: Trino
- 테이블
  - `sales.fact_orders`
  - `sales.dim_store`
  - `sales.dim_campaign`
- 요구사항: 지난 7일간 한국 enterprise 스토어의 캠페인별 GMV 집계
- 증상: 쿼리가 70~90초, 일부 날은 join spill 발생

원래 쿼리:

```sql
SELECT c.campaign_type,
       sum(o.gmv) AS total_gmv
FROM sales.fact_orders o
JOIN sales.dim_store s
  ON o.store_id = s.store_id
JOIN sales.dim_campaign c
  ON o.campaign_id = c.campaign_id
WHERE o.order_date BETWEEN DATE '2026-04-01' AND DATE '2026-04-07'
  AND s.region = 'KR'
  AND s.store_tier = 'ENTERPRISE'
  AND c.is_paid = true
GROUP BY 1;
```

겉으로는 큰 문제가 없어 보인다. 그런데 내부를 보면 병목이 겹친다.

1. `fact_orders`가 하루 파티션 안에 작은 파일이 과도하게 많다
2. `dim_store` 통계가 오래돼 build side 축소를 optimizer가 과소평가한다
3. `dim_campaign`은 작지만 `dim_store`와의 조인 순서가 기대와 다르다
4. 일부 실행에서 partitioned join이 선택되며 network shuffle이 커진다
5. 조인 후 aggregation까지 이어지며 메모리 압박이 커진다

### 1단계, 저장 구조부터 확인

운영자는 먼저 SQL을 뜯기보다 테이블 상태를 봤다.

- 특정 일자 파티션의 파일 수 급증 확인
- 최근 compaction 지연 확인
- `fact_orders`의 일부 파티션이 late data 때문에 잘게 쪼개진 상태 확인

여기서 얻는 교훈은 단순하다.

**엔진 튜닝 전에 읽기 대상 품질부터 회복해야 한다.**

compaction 후 split 수가 크게 줄고 planning overhead가 먼저 내려간다.

### 2단계, build side를 명시적으로 줄였다

개선 쿼리:

```sql
WITH filtered_store AS (
  SELECT store_id
  FROM sales.dim_store
  WHERE region = 'KR'
    AND store_tier = 'ENTERPRISE'
),
filtered_campaign AS (
  SELECT campaign_id, campaign_type
  FROM sales.dim_campaign
  WHERE is_paid = true
)
SELECT c.campaign_type,
       sum(o.gmv) AS total_gmv
FROM sales.fact_orders o
JOIN filtered_store s
  ON o.store_id = s.store_id
JOIN filtered_campaign c
  ON o.campaign_id = c.campaign_id
WHERE o.order_date BETWEEN DATE '2026-04-01' AND DATE '2026-04-07'
GROUP BY 1;
```

이렇게만 바꿔도 좋은 이유는 두 가지다.

- build side 후보가 더 작고 명확해진다
- dynamic filtering이 붙을 여지가 커진다

### 3단계, 계획을 확인했다

`EXPLAIN`과 `EXPLAIN ANALYZE`에서 확인한 포인트는 아래다.

- `Distribution: REPLICATED`가 필요한 조인에서 실제로 보이는가
- `dynamicFilterAssignments`가 생성되는가
- `fact_orders` scan에서 dynamic filter가 붙는가
- input rows 대비 output rows가 얼마나 줄었는가
- aggregation 전에 이미 충분히 데이터가 좁혀졌는가

### 4단계, spill을 해결 대상이지 허용값으로 보지 않았다

초기에는 spill이 켜져 있어 쿼리가 겨우 성공했다. 하지만 이 상태를 성공으로 보지 않았다.

왜냐하면 반복 실행되는 운영 쿼리에서 spill은 결국 tail latency와 노드 불안정성을 만든다.

그래서 목표를 "쿼리가 끝난다"가 아니라 아래로 바꿨다.

- spill zero 또는 거의 zero
- broadcast 가능한 build side 크기 유지
- dynamic filter로 fact scan 감소
- compaction 이후 split 수 안정화

### 결과

- planning + scheduling overhead 감소
- join distribution이 더 일관되게 선택됨
- fact scan 바이트 감소
- spill 제거 또는 대폭 감소
- 총 실행 시간 70~90초 → 11~15초 수준

핵심은 SQL 문법 트릭 하나가 아니었다.

**저장 품질, build side 축소, dynamic filtering 확인, spill 제거를 한 흐름으로 본 것**이 효과를 냈다.

---

## 핵심 개념 6: Cost-Based Optimizer는 "똑똑한 두뇌"가 아니라 "입력 품질에 민감한 계산기"다

Trino의 cost-based optimizer, 즉 CBO를 이야기할 때 많은 팀이 두 극단으로 흔들린다.

- 너무 믿는다. 자동이니 다 맞겠지
- 아예 안 믿는다. 어차피 틀리니 힌트나 강제로 가자

둘 다 위험하다.

실무에서 CBO는 매우 유용하지만, 전제 조건이 맞을 때 그렇다. 더 정확히는 **CBO는 입력이 괜찮으면 상당히 좋은 선택을 하고, 입력이 흐리면 흐린 만큼만 판단하는 계산기**에 가깝다.

### CBO가 실제로 기대하는 것

- 테이블/파티션 단위 row 수
- 컬럼 선택도 힌트
- 필터 적용 전후 cardinality 변화
- 조인 키 분포에 대한 간접 정보
- connector가 제공하는 pushdown 가능성

즉 planner가 궁금한 것은 아주 인간적이다.

- 이 테이블이 정말 작은가
- 이 필터를 거치면 얼마나 줄어드는가
- 어떤 순서로 조인하는 게 덜 비싼가
- 여기서 broadcast해도 안전한가

그런데 현장 데이터는 자주 이 질문에 제대로 답하지 못한다.

- Iceberg snapshot은 최신인데 통계는 충분치 않다
- Hive 메타스토어 row count가 오래됐다
- 테넌트 skew 때문에 평균값이 의미가 없다
- 특정 날짜만 폭증하는데 전체 통계는 평평해 보인다
- materialized view처럼 보이지만 실제론 raw fact라 build side가 생각보다 크다

### CBO가 특히 잘 틀리는 상황

#### 1) 필터 후 급격히 작아지는 dimension

원본 dimension은 수천만 row인데,

- 국가 = KR
- enterprise = true
- active = true

같은 조건을 걸면 수만 row로 줄어드는 경우가 많다.

문제는 optimizer가 이 선택도를 정확히 못 읽으면, 사실 broadcast하면 끝날 조인을 partitioned로 잡을 수 있다는 점이다.

#### 2) 기간 편차가 큰 fact table

주말, 프로모션, 월말 정산일처럼 특정 날짜만 데이터량이 크게 튀는 테이블에서는 "지난 7일" 쿼리라 해도 어느 7일이냐에 따라 비용이 크게 달라진다.

이런 상황에서 평균 기반 통계는 자주 무너진다.

#### 3) Federation 쿼리

예를 들어 Trino가 PostgreSQL dimension과 Iceberg fact를 같이 읽는다고 해보자.

이론상 SQL은 간단하지만, 비용 추정은 순수 Lakehouse 내부 조인보다 복잡해진다. connector마다 pushdown 범위와 통계 품질이 다르기 때문이다.

#### 4) 중첩된 서브쿼리와 복잡한 CTE

사람 눈에는 읽기 좋은 SQL이라도 optimizer 입장에서는 cardinality 흐름이 흐려질 수 있다. 특히 CTE를 논리 뷰처럼 많이 쌓으면 build side 축소 기회가 덜 선명하게 보이기도 한다.

### 그래서 실무에서 어떻게 접근할까

CBO를 불신하기보다, **핵심 반복 쿼리에 대해서만 계획 품질을 검증하고 필요할 때 제한적으로 개입**하는 편이 낫다.

예를 들어 아래처럼 접근할 수 있다.

1. 기본은 `AUTOMATIC`
2. 반복성 높은 핵심 쿼리 선별
3. EXPLAIN/ANALYZE 결과와 실제 wall time 비교
4. build side와 distribution 선택이 자주 어긋나는 쿼리만 별도 세션 정책 또는 리라이팅 적용

즉 전체 시스템을 강제로 몰아가기보다, **돈이 많이 드는 쿼리만 측정 기반으로 길들인다**는 감각이 좋다.

### CBO와 사람이 역할을 나누는 법

- CBO에게 맡길 것: 일반적인 조인 순서, 통계 기반 distribution 선택
- 사람이 개입할 것: 핵심 쿼리 shape 정리, build side 축소, 통계 freshness 관리, small file 정리, 반복 쿼리 검증

결론적으로 CBO는 끄거나 맹신할 대상이 아니다.

**좋은 저장 구조와 괜찮은 통계를 준비해주면 효과를 내는 엔진 내부 협업자**로 보는 편이 가장 현실적이다.

---

## 핵심 개념 7: 같은 Trino라도 connector에 따라 "빨라질 수 있는 방식"이 다르다

Trino를 하나의 제품으로만 보면 놓치기 쉬운 사실이 있다.

쿼리는 같은 Trino가 실행하지만, 실제로 얼마나 덜 읽을 수 있는지는 connector가 크게 좌우한다.

즉 성능은 엔진 공통 규칙과 connector별 규칙의 합이다.

### Hive 계열 connector에서 자주 보는 포인트

- partition pruning이 메타스토어 정보에 강하게 의존한다
- ORC/Parquet reader 최적화, stripe/row group pruning 체감이 크다
- partition 수와 파일 수가 planning latency에 직접 영향을 준다
- 오래된 메타스토어 정보나 잘못된 partition 등록은 성능과 안정성을 동시에 해친다

Hive 스타일 테이블은 전통적으로 단순하고 익숙하지만, partition이 과도하게 잘게 쪼개지고 작은 파일이 많아지면 Trino가 가장 먼저 그 복잡도를 떠안는다.

### Iceberg에서 자주 보는 포인트

- snapshot, manifest, partition spec, file-level metadata가 읽기 계획에 영향을 준다
- compaction과 metadata maintenance가 성능 안정성에 중요하다
- hidden partitioning이나 진화한 partition spec이 편리하지만, 대표 쿼리 패턴과 맞지 않으면 체감 이점이 줄어든다
- 다양한 엔진이 같은 테이블을 만질 때 metadata 품질 일관성이 중요하다

Iceberg는 메타데이터 계층이 강력해서 운영이 쉬워 보이지만, 실제로는 snapshot 증가, manifest 읽기, late data에 따른 file fragmentation 같은 문제가 쿼리 안정성을 흔들 수 있다.

### Delta Lake 계열에서 보는 포인트

- transaction log 크기와 checkpoint 상태
- optimize/z-order 유무
- 파일 정렬/클러스터링 전략
- Trino connector가 활용 가능한 pushdown 범위

즉 Delta도 "포맷이 있으니 알아서 빠르다"가 아니라, 파일 배치와 유지보수가 성능을 좌우한다.

### JDBC/RDB connector에서 보는 포인트

- predicate pushdown 범위
- aggregation/join pushdown 범위
- 원격 DB가 감당해야 할 부하
- federation이 진짜 필요한지 여부

실무에서 자주 생기는 함정은 이렇다.

"Trino로 붙이면 다 한 곳에서 보이니까 좋다"

맞는 말이다. 하지만 그것이 곧 **원격 DB까지 포함한 전체 시스템 비용이 싸다**는 뜻은 아니다.

특히 JDBC 소스를 큰 fact와 무심코 조인하면,

- 원격 소스 부하 증가
- 통계 부정확
- pushdown 제한
- 네트워크 대기

가 한꺼번에 겹칠 수 있다.

### 같은 SQL이라도 connector별 전략이 달라져야 하는 이유

예를 들어 아래 쿼리는 문법상 동일할 수 있다.

```sql
SELECT count(*)
FROM fact_events e
JOIN dim_user u ON e.user_id = u.user_id
WHERE u.plan = 'enterprise'
  AND e.event_date >= DATE '2026-04-01';
```

하지만 운영 해석은 달라진다.

- Iceberg fact + Iceberg dim: metadata, file pruning, dynamic filtering 조합을 노린다
- Iceberg fact + PostgreSQL dim: dim을 먼저 축소한 뒤 join하거나, 아예 추출/캐시 테이블을 둘 가치가 있다
- Hive fact + Delta dim: connector별 pushdown과 통계 품질 차이를 의식해야 한다

즉 SQL은 같아도 실행 현실은 다르다.

그래서 성능 진단 문서를 만들 때도 단순히 "Trino 느린 쿼리 가이드"가 아니라,

- Iceberg 대상일 때 확인할 것
- Hive 대상일 때 확인할 것
- JDBC federation일 때 피할 것

처럼 나누는 편이 훨씬 실용적이다.

---

## 실무 예시 2: Broadcast와 Partitioned를 실제로 어떻게 비교해야 하나

운영자가 가장 흔히 하는 질문 중 하나는 이것이다.

"이 쿼리, broadcast로 강제하면 빨라질까요?"

좋은 질문이지만, 감으로 답하면 안 된다. 이유는 간단하다. broadcast는 어떤 날은 2배 빨라지지만, 어떤 날은 메모리 사고를 만든다.

그래서 비교는 반드시 **같은 기간 조건, 같은 데이터 상태, 같은 동시성 구간**에서 해야 한다.

### 비교 대상 예시

반복 실행되는 KPI 쿼리가 있다고 하자.

```sql
SELECT s.region,
       sum(o.net_revenue) AS revenue
FROM mart.fact_order o
JOIN mart.dim_store s
  ON o.store_id = s.store_id
WHERE o.order_date BETWEEN DATE '2026-04-01' AND DATE '2026-04-07'
  AND s.is_active = true
GROUP BY 1;
```

이 쿼리에 대해 아래 세 가지를 비교할 수 있다.

1. 기본값 `AUTOMATIC`
2. `SET SESSION join_distribution_type = 'BROADCAST'`
3. `SET SESSION join_distribution_type = 'PARTITIONED'`

### 무엇을 비교해야 하나

단순 wall time만 보면 안 된다. 최소한 아래를 같이 봐야 한다.

- 총 실행 시간
- peak memory per node
- spilled bytes
- physical input bytes
- network shuffled bytes
- CPU time과 scheduled time 차이
- concurrency가 올라갔을 때 tail latency 변화

### 해석 기준

#### broadcast가 좋은 신호

- wall time이 일관되게 짧다
- peak memory가 안전 범위다
- spill이 발생하지 않는다
- build side row 수가 날짜에 따라 크게 흔들리지 않는다
- 같은 쿼리를 동시 실행해도 tail latency가 폭증하지 않는다

#### partitioned가 좋은 신호

- wall time은 조금 느려도 메모리 안정성이 높다
- 특정 날짜/테넌트에서 build side 폭증이 있다
- broadcast에서는 간헐 OOM 또는 spill이 난다
- 네트워크 비용보다 메모리 안전성이 중요하다

### 흔한 잘못된 결론

"broadcast가 한 번 더 빨랐으니 무조건 broadcast"

이건 위험하다. 운영에서 중요한 것은 최고 성능보다 **최악의 날에도 버티는 분포**다. 특히 데이터량 변동이 큰 조직에서는 p50보다 p95, p99가 더 중요하다.

그래서 반복 쿼리 정책은 보통 이렇게 정한다.

- API/대시보드 핵심 쿼리: 측정 후 broadcast 고정 가능
- analyst ad-hoc: automatic 유지
- build side 변동 큰 쿼리: partitioned 또는 automatic 유지
- 월말/프로모션 특수 쿼리: 별도 리소스 그룹이나 전용 시간대 운영 검토

### 사람이 개입해야 하는 진짜 순간

`join_distribution_type`을 바꾸는 것보다 더 큰 효과가 나는 순간이 있다.

- dimension을 미리 축소한 서빙용 테이블 제공
- 자주 쓰는 filter 결과를 mart 계층으로 승격
- fact table compaction으로 split 수 정상화
- group by 키 재설계로 aggregation 메모리 압박 감소

즉 distribution 강제는 마지막 20% 개선에서 빛나고, 앞선 80%는 데이터와 SQL 구조가 만든다.

---

## 실무 예시 3: Spill이 났을 때 "메모리가 부족하다"로 끝내면 재발한다

spill 알람이 올라오면 많은 팀이 바로 메모리 값을 본다.

물론 봐야 한다. 하지만 그것만 보면 절반만 본 것이다.

spill은 결과이지 원인이 아니다.

### join spill의 전형적 원인

- build side가 기대보다 큼
- 잘못된 distribution 선택
- 필터가 조인 뒤에 적용됨
- skew로 특정 파티션 빌드 해시가 비대함
- 사실은 input 자체가 너무 커서 어느 전략도 버거움

### aggregation spill의 전형적 원인

- group by 키 카디널리티가 과도함
- distinct 집계가 많음
- pre-aggregation 없이 raw fact를 그대로 집계
- 필요한 기간보다 훨씬 넓은 범위를 읽음

### sort/window spill의 전형적 원인

- 의미 없이 전역 정렬 수행
- `row_number`, `rank`, `lead/lag`를 큰 파티션에 무심코 사용
- pagination 없이 대규모 정렬 결과를 한 번에 요구

### 진단 순서

1. 어떤 operator가 spill했는가
2. 그 operator 직전 input rows/bytes는 얼마인가
3. 그 input을 줄일 구조적 방법이 있는가
4. distribution 또는 SQL shape 변경으로 완화 가능한가
5. 그래도 unavoidable한가

여기서 5번까지 갔을 때만 spill을 "허용 가능한 비용"으로 본다.

### 운영 대시보드에 꼭 넣을 것

- query별 spilled bytes 상위 20개
- spill 발생 빈도 추세
- worker별 spill disk 사용률
- spill과 wall time 상관관계
- spill과 작은 파일 급증 시점 상관관계
- spill query와 특정 리포트/대시보드 매핑

이런 대시보드가 있으면, 단순히 "이번 주 느렸다"가 아니라

- 어떤 팀의 어떤 리포트가 문제인지
- 데이터 적재 품질 문제와 연결되는지
- 특정 모델 변경 이후 악화됐는지

까지 이어진다.

---

## 핵심 개념 8: EXPLAIN은 계획서이고, EXPLAIN ANALYZE는 부검 보고서다

Trino를 운영하면서 가장 빨리 실력이 느는 방법 중 하나는 실행 계획을 표면적으로만 보지 않는 것이다.

많은 사람이 EXPLAIN에서 join 순서만 보고 끝낸다. 하지만 실제로 중요한 것은 아래다.

- distribution이 무엇인가
- dynamic filter assignment가 붙었는가
- scan 노드의 input/output이 어떤가
- 특정 operator의 CPU, scheduled time, blocked time이 어떤가
- estimate와 actual이 얼마나 어긋나는가

### EXPLAIN에서 볼 것

#### 1) Distribution

- `REPLICATED`면 broadcast 성격
- `PARTITIONED`면 shuffle 기반 조인 성격

이 정보는 곧 메모리 모델과 네트워크 비용 모델을 알려준다.

#### 2) dynamicFilterAssignments

이게 보이면 적어도 planner는 runtime filter를 시도하고 있다는 뜻이다. 하지만 여기서 멈추면 안 된다. 실제 scan 감소로 이어졌는지는 ANALYZE나 실행 통계에서 봐야 한다.

#### 3) ScanFilterProject

필터가 어디에 붙는지, projection이 얼마나 일찍 줄어드는지, 불필요한 컬럼이 남아 있는지 확인할 수 있다.

### EXPLAIN ANALYZE에서 볼 것

#### 1) Estimate vs Actual 차이

이 차이가 크면 통계 품질이나 선택도 해석이 어긋난 것이다.

예를 들어 estimate는 10만 row인데 actual이 3억 row라면, 그 뒤 조인과 메모리 계산이 모두 무너졌을 가능성이 크다.

#### 2) Input std.dev.

작업 분산이 고르지 않다면 skew 신호일 수 있다. 특정 task만 지나치게 많은 row를 처리하면 p95가 길어진다.

#### 3) Scheduled time 대비 CPU time

scheduled time이 유독 긴데 CPU는 낮다면,

- I/O 대기
- 네트워크 대기
- blocked 상태
- spill/unspill 대기

를 의심할 수 있다.

#### 4) Physical input과 filtered ratio

읽는 양이 많고 필터 후 대부분 버려진다면, 더 앞단에서 줄일 기회를 놓친 것이다.

### 계획 읽기의 실무 습관

반복 쿼리는 아래를 스냅샷처럼 남겨두면 좋다.

- SQL 버전
- EXPLAIN 핵심 요약
- EXPLAIN ANALYZE 핵심 수치
- distribution 선택
- scan bytes
- spilled bytes
- 결과 latency

이 기록이 있으면, 성능 회귀가 생겼을 때 "느려졌어요"가 아니라 **어느 단계가 어떻게 변했는지**를 비교할 수 있다.

---

## 핵심 개념 9: Trino는 대화형 분석 엔진이지, 모든 무거운 계산을 실시간으로 견디는 만능 배치 엔진이 아니다

Trino를 오래 운영할수록 중요한 질문이 하나 생긴다.

"이 계산을 정말 Trino에서 실시간으로 해야 하나?"

이 질문을 놓치면 쿼리 튜닝만 반복하게 된다.

### Trino에 잘 맞는 일

- 짧은 기간 범위 조회
- 선택도 높은 dimension 조인
- 운영성 있는 대화형 분석
- 이미 정리된 mart 위 서빙형 집계
- 여러 소스의 가벼운 federation

### Trino에 덜 맞는 일

- 매우 큰 raw event를 장시간 full scan하는 반복 배치
- 대규모 reprocessing
- 고비용 window/정렬/복합 distinct가 반복되는 리포트
- 복잡한 ETL 변환 전체를 한 방 SQL로 처리하는 일

이때 필요한 판단은 엔진 교체가 아니라 역할 분리다.

- 무거운 재계산은 Spark/Flink/dbt batch로 미리 처리
- Trino는 결과를 빠르게 읽는 계층에 집중
- 고정 리포트는 mart나 aggregate table로 승격
- 잦은 조인은 denormalization 또는 serving table로 완화

즉 Trino의 장점을 살리려면 **실시간으로 계산해야 할 것과 미리 계산해 둘 것을 분리**해야 한다.

이 원칙이 없으면 모든 성능 문제를 Trino 세팅이나 메모리 문제로 오해하게 된다.

---

## 트레이드오프 1: Broadcast Join은 빠르지만 데이터 크기 변화에 취약하다

broadcast는 많은 경우 가장 눈에 띄게 빠르다. 하지만 운영성까지 생각하면 항상 정답은 아니다.

### 장점

- 작은 dimension 조인에서 대기시간이 짧다
- shuffle이 줄어 반복 쿼리에 유리하다
- dynamic filtering 시너지가 좋다

### 단점

- build side 크기 변동에 민감하다
- 특정 날짜, 특정 테넌트, 특정 프로모션에서 갑자기 커질 수 있다
- 노드별 메모리 여유가 줄어 다른 쿼리와 충돌한다

### 추천 기준

- 대시보드/서빙 쿼리: 측정 후 강제 고려 가능
- ad-hoc/탐색 쿼리: automatic 또는 partitioned가 더 안전
- 데이터량 변동 폭 큰 쿼리: 방송형 강제는 신중

---

## 트레이드오프 2: Dynamic Filtering은 강력하지만 build side 수집 지연과 connector 제약을 함께 가진다

dynamic filtering이 좋다고 해서 모든 조인을 그 전제로 설계하면 안 된다.

### 장점

- fact scan을 크게 줄일 수 있다
- 원격 스토리지 읽기 비용을 감소시킨다
- 선택도 높은 dimension 필터에서 체감 차이가 크다

### 단점

- build side 수집이 늦으면 probe가 먼저 진행될 수 있다
- connector가 충분히 활용하지 못하면 기대보다 약하다
- distinct 값이 너무 많으면 필터가 둔해진다
- 실행 계획과 실제 효과를 반드시 검증해야 한다

### 추천 기준

- 반복 쿼리에서 EXPLAIN/ANALYZE로 검증 후 신뢰할 것
- build side를 의도적으로 작게 만드는 모델링과 SQL 습관이 선행되어야 함

---

## 트레이드오프 3: Spill은 성공률을 높이지만 latency와 디스크 안정성을 갉아먹는다

### 장점

- 일시적 대형 쿼리를 죽이지 않고 살릴 수 있다
- 클러스터 전체 OOM을 완충할 수 있다
- 운영자가 일단 결과를 받아야 하는 상황에 유용하다

### 단점

- 매우 느려질 수 있다
- 디스크 I/O와 노드 간섭이 커진다
- 근본적인 설계 문제를 감출 수 있다
- 반복 쿼리에서는 사실상 장애 신호다

### 추천 기준

- ad-hoc 보호장치로는 유용
- 상시 운영 쿼리의 정상 상태로 받아들이면 안 됨

---

## 흔한 실수 1: `AUTOMATIC`을 쓰면서 통계 관리를 안 한다

많은 팀이 기본값에만 기대고 통계 품질을 관리하지 않는다.

그러면 자동 최적화가 자동 랜덤화처럼 느껴진다.

실제로는 optimizer가 멍청한 것이 아니라, 근거가 부족한 경우가 많다.

### 증상

- 어제는 broadcast, 오늘은 partitioned
- 동일 쿼리인데 메모리 패턴이 다름
- join 순서가 기대와 어긋남

### 대응

- 통계 수집 주기와 freshness 관리
- 특정 핵심 쿼리는 실행 계획 스냅샷 비교
- 반복 쿼리만큼은 distribution 정책을 측정 기반으로 관리

---

## 흔한 실수 2: 작은 파일 문제를 Trino 설정으로 해결하려 한다

이건 아주 흔하다.

- worker 메모리 확대
- spill 활성화
- concurrency 조정
- 재시도 증가

물론 도움이 될 때도 있다. 하지만 작은 파일 문제의 본질은 엔진이 아니라 테이블 유지보수다.

### 증상

- scan bytes보다 split 수가 이상하게 많다
- 짧은 기간 조회인데도 planning 시간이 길다
- selective query인데도 object storage request가 많다

### 대응

- compaction/optimize/cluster 정책 먼저
- late data 적재 전략 정리
- 파티션 수와 파일 크기 목표치 정의

---

## 흔한 실수 3: build side를 SQL에서 작게 만들 기회를 놓친다

아래 같은 패턴이 많다.

- 큰 dimension 전체와 조인하고 나중에 필터링
- 서브쿼리 안에서 불필요한 컬럼까지 들고 나옴
- `SELECT *`로 dimension을 넓게 복제
- 사실상 semi-join이면 될 것을 full join처럼 작성

이 실수는 broadcast 기회를 날리고 dynamic filtering 효과도 약화시킨다.

### 대응

- build side는 키 중심으로 최소화
- 조인 전 필터 적용
- 필요한 컬럼만 projection
- 존재 여부 판단이면 semi-join/exists 형태도 검토

---

## 흔한 실수 4: spill을 켠 뒤 모니터링을 안 한다

spill은 켜는 것보다 관찰이 중요하다.

### 놓치기 쉬운 것

- 어떤 operator가 spill을 유발하는지
- node별 디스크 압박 차이
- spill 때문에 다른 쿼리 tail latency가 늘어나는지
- spill path가 system disk와 충돌하는지

### 대응

- query별 spilled bytes 수집
- node disk saturation 알람
- spill 상위 쿼리 주간 리뷰
- 반복 쿼리 spill은 리라이팅/모델링 이슈로 분류

---

## 흔한 실수 5: EXPLAIN을 보고도 실제 scan 감소를 확인하지 않는다

실행 계획에 dynamic filter가 보인다고 끝이 아니다.

실제 효과를 봐야 한다.

- scan bytes가 줄었는가
- input rows가 얼마나 감소했는가
- build filter collection 시간이 과도하지 않은가
- join 이후 discarded rows가 줄었는가

즉 계획은 의도이고, 실행 통계는 현실이다.

둘을 같이 봐야 한다.

---

## 운영 체크리스트: Trino 느린 쿼리를 볼 때 최소한 이것부터 확인하자

### 1) 읽기 범위

- [ ] 파티션 pruning이 실제로 되었는가
- [ ] 작은 파일이 과도하게 많은가
- [ ] 필요한 컬럼만 읽고 있는가
- [ ] scan bytes와 split 수가 기대 수준인가

### 2) 조인 전략

- [ ] build side가 정말 작은가
- [ ] `AUTOMATIC` 선택이 합리적인가
- [ ] 필요 시 broadcast/partitioned 강제 근거가 있는가
- [ ] skew로 특정 파티션만 과열되지 않는가

### 3) Dynamic Filtering

- [ ] `dynamicFilterAssignments`가 계획에 보이는가
- [ ] connector가 실제 pushdown/pruning을 활용하는가
- [ ] build side 수집 시간이 과도하지 않은가
- [ ] 실제 scan 감소 효과가 있었는가

### 4) 메모리와 spill

- [ ] spill이 예외인지 상시 상태인지 구분했는가
- [ ] spill operator와 volume을 추적하는가
- [ ] spill path가 전용 디스크인가
- [ ] `query_max_memory`, `query_max_memory_per_node`와 현실 사용 패턴이 맞는가

### 5) 테이블 품질

- [ ] compaction/optimize가 정상적으로 돌고 있는가
- [ ] 통계 freshness가 충분한가
- [ ] partition 설계가 대표 쿼리 패턴과 맞는가
- [ ] late data 전략 때문에 파일 난립이 생기지 않는가

---

## 한 줄 정리 전에, 실무 판단 기준을 다시 압축하면

Trino 튜닝은 보통 아래 순서로 풀면 된다.

1. 먼저 덜 읽게 만든다
2. 그다음 build side를 작게 만든다
3. 그다음 dynamic filtering이 실제로 먹는지 확인한다
4. 그다음 join distribution을 측정 기반으로 조정한다
5. spill은 마지막 완충장치로만 남긴다

이 순서가 중요한 이유는, 뒤 단계로 갈수록 엔진 의존도가 커지고 앞 단계로 갈수록 구조 개선 효과가 오래가기 때문이다.

메모리만 늘리는 튜닝은 다음 데이터 증가에서 다시 깨지기 쉽다.

반대로 파일 수, 통계, build side, 필터 경로를 바로잡는 튜닝은 쿼리 여러 개에 동시에 이득을 준다.

---

## 한 줄 정리

**Trino 성능의 핵심은 빠른 조인 비법이 아니라, 좋은 저장 구조와 작은 build side를 바탕으로 dynamic filtering을 살리고 spill 없이 끝나는 읽기 경로를 만드는 것이다.**
