---
layout: post
title: "Apache Spark 성능 실전: AQE, Shuffle, Skew Join, Partition 설계로 느린 배치를 구조적으로 줄이는 법"
date: 2026-04-04 11:40:00 +0900
categories: [data-infra]
tags: [study, data-infra, apache-spark, spark, aqe, shuffle, skew-join, partitioning, performance, parquet]
permalink: /data-infra/2026/04/04/study-apache-spark-aqe-shuffle-skew-join-partitioning.html
---

## 배경: Spark 작업이 느린 이유는 "클러스터가 약해서"보다 "데이터 이동을 잘못 설계해서"인 경우가 많다

Spark를 처음 쓸 때는 보통 이렇게 생각한다.

- 데이터가 커졌으니 분산 처리 엔진을 쓰면 된다
- executor 수를 늘리면 대체로 빨라질 것이다
- partition을 많이 쪼개면 병렬성이 올라가서 유리할 것이다
- 느리면 메모리를 더 주고 코어를 더 주면 해결될 것이다

초기에는 이 접근이 어느 정도 맞는다. 작은 데이터셋이나 단순 ETL에서는 리소스를 조금 늘리는 것만으로도 체감이 나온다. 하지만 데이터량이 커지고 조인, 집계, 파일 수, 테이블 수가 늘어나면 곧 같은 장면이 반복된다.

- 입력 데이터는 몇 배 늘지 않았는데 job runtime은 몇 배씩 늘어난다
- stage 대부분은 빨리 끝나는데 마지막 몇 개 task가 유독 오래 붙잡고 있다
- executor 메모리를 올렸는데도 spill이 줄지 않는다
- `spark.sql.shuffle.partitions`를 올렸더니 오히려 전체 시간이 더 길어진다
- broadcast join이 될 줄 알았는데 sort-merge join으로 바뀌어 shuffle이 폭증한다
- 특정 테넌트나 특정 날짜 데이터 때문에 한두 partition이 병목이 된다
- upstream이 만든 작은 파일이 너무 많아 scan보다 planning과 task scheduling 비용이 커진다

이 시점부터 Spark 성능 문제의 본질은 단순히 "CPU가 부족하다"가 아니다. 실제로는 **어디서 데이터를 읽고, 어떤 기준으로 나누고, 언제 shuffle하고, 어느 partition이 과도하게 커지며, 실행 중 계획을 얼마나 유연하게 바꿀 수 있는가**가 훨씬 중요해진다.

특히 중급 이상 개발자에게 중요한 질문은 아래다.

- Spark SQL에서 느린 job은 정확히 어느 단계에서 시간을 쓰는가?
- AQE(Adaptive Query Execution)는 무엇을 자동으로 해결하고, 무엇은 절대 해결하지 못하는가?
- `spark.sql.shuffle.partitions`는 크게 잡는 게 좋은가, 작게 잡는 게 좋은가?
- skew join은 감으로 의심할 것이 아니라 어떤 신호로 판단해야 하는가?
- upstream 파일 레이아웃과 downstream shuffle 비용은 어떻게 연결되는가?
- repartition, coalesce, bucket, partitionBy는 각각 언제 써야 하는가?
- Spark 튜닝에서 가장 흔한 실수는 왜 대부분 "숫자만 바꾸고 데이터 분포는 안 본다"는 데서 나오나?

오늘 글은 Spark 성능 튜닝 팁 모음이 아니다. **배치·ETL·데이터마트 파이프라인에서 Spark 작업이 느려지는 구조적 이유를 이해하고, AQE·shuffle·partition 설계를 이용해 재현 가능하게 개선하는 기준**을 정리한다.

핵심은 일곱 가지다.

1. Spark 성능의 중심은 연산량보다 **데이터 이동량과 데이터 분포**다
2. AQE는 매우 강력하지만, **나쁜 데이터 모델링과 나쁜 파일 레이아웃을 자동으로 구해주지 않는다**
3. `shuffle partitions`는 클수록 좋은 값이 아니라 **목표 task 크기와 skew 위험의 균형값**이다
4. 느린 join의 본질은 대개 알고리즘 선택보다 **잘못된 cardinality 감각과 skew 무시**에 있다
5. scan 최적화와 shuffle 최적화는 별개가 아니라 **같은 파이프라인의 앞뒤 문제**다
6. repartition/coalesce/partitionBy/broadcast hint는 기능 이름보다 **언제 데이터 이동을 유발하는지**로 이해해야 한다
7. 실무에서 가장 좋은 튜닝은 매번 수동 숫자조정이 아니라 **관측 지표와 설계 기준을 고정하는 것**이다

---

## 먼저 큰 그림: Spark job 시간은 보통 네 군데에서 새고 있다

Spark를 오래 운영하면 느린 작업은 결국 아래 네 축으로 설명되는 경우가 많다.

### 1) 읽기(scan) 비용

- 파일 수가 너무 많다
- 작은 파일이 과도하다
- 파티션 pruning이 잘 안 된다
- predicate pushdown이 충분히 안 먹는다
- 필요한 컬럼보다 너무 많이 읽는다

### 2) 데이터 이동(shuffle) 비용

- group by, distinct, join, window 때문에 대량 재분배가 발생한다
- shuffle partition 수가 과도하거나 부족하다
- network I/O, serialization, spill 비용이 커진다

### 3) 데이터 불균형(skew) 비용

- 일부 key에 데이터가 몰린다
- 특정 날짜/테넌트/상품/사용자 구간만 지나치게 크다
- task 대부분은 빨리 끝났는데 소수 task가 끝까지 붙잡고 있다

### 4) 출력(write) 비용

- 지나치게 많은 output file 생성
- overwrite 범위가 넓다
- partitionBy 전략이 downstream 조회와 맞지 않는다
- 쓰기 직전 repartition이 과도하거나 반대로 너무 부족하다

많은 팀이 2번만 본다. 그래서 shuffle tuning만 반복한다. 하지만 실제로는 1번이 나쁘면 2번이 악화되고, 4번을 잘못 쓰면 다음날 다시 1번 문제로 돌아온다.

즉 Spark 튜닝은 "느린 SQL 한 줄 고치기"보다 **입력 파일 구조 → 실행 계획 → shuffle → 출력 파일 구조**의 고리를 보는 편이 맞다.

---

## Spark 성능을 보는 가장 좋은 관점: CPU 엔진이 아니라 "분산 데이터 재배치 엔진"으로 이해하기

Spark를 RDB처럼 생각하면 자주 판단이 꼬인다. RDB에서는 인덱스, 버퍼 캐시, 단일 엔진 최적화가 핵심인 경우가 많지만, Spark에서는 훨씬 자주 아래 질문이 더 중요하다.

- 이 연산 전에 데이터가 이미 원하는 기준으로 나뉘어 있는가?
- 아니면 모든 executor 사이에서 다시 섞어야 하는가?
- 그 섞는 과정에서 일부 bucket/partition만 과도하게 커지지 않는가?
- scan 단계에서 줄였어야 할 데이터를 이미 너무 많이 들고 오지는 않았는가?

예를 들어 아래 쿼리를 보자.

```sql
SELECT o.dt, o.store_id, SUM(o.amount)
FROM fact_orders o
JOIN dim_store s
  ON o.store_id = s.store_id
WHERE o.dt BETWEEN DATE '2026-04-01' AND DATE '2026-04-03'
  AND s.region = 'KR'
GROUP BY o.dt, o.store_id;
```

겉보기에는 단순하다. 하지만 Spark 관점에서는 아래 질문이 붙는다.

- `fact_orders`는 날짜 파티션 pruning이 되는가?
- `dim_store`는 broadcast 가능한 크기인가?
- `region='KR'` 필터를 join 전에 충분히 줄였는가?
- `GROUP BY (dt, store_id)` 전에 이미 `store_id` 기준 skew가 존재하는가?
- 결과를 어떤 partition 수로 다시 나눌 것인가?

즉 SQL 한 줄보다, **그 SQL이 어떤 데이터 이동 그래프를 만드는가**가 더 중요하다.

---

## 핵심 개념 1: AQE는 "실행 중 계획 수정기"이지 만능 성능 마법이 아니다

Spark 성능 얘기에서 AQE(Adaptive Query Execution)를 빼면 이제 거의 설명이 안 된다. 하지만 AQE를 "켜면 빨라진다" 정도로 이해하면 곤란하다.

### AQE의 본질

AQE는 쿼리 실행 전에 고정한 물리 계획을 끝까지 고집하지 않고, **shuffle 이후 실제 데이터 크기와 partition 분포를 보고 실행 중 일부 계획을 다시 최적화**하는 기능이다.

즉 Spark는 원래 이렇게 움직인다.

1. logical plan 생성
2. optimized logical plan 생성
3. physical plan 선택
4. 실행

AQE가 켜져 있으면 4번 실행 중간에, 특히 shuffle이 한 번 끝난 뒤 실제 결과 크기를 보고 다음 결정을 조정할 수 있다.

- shuffle partition을 더 합칠지
- join 전략을 바꿀지
- skewed partition을 쪼갤지

이게 큰 이유는, 쿼리 컴파일 시점에는 통계가 부정확하거나 너무 거칠 수 있기 때문이다. 특히 데이터 레이크 환경에서는 테이블 통계가 RDB만큼 정교하게 유지되지 않는 경우가 많아, **정적 계획만 믿으면 잘못된 join 전략과 비효율적인 partition 수**가 쉽게 나온다.

### AQE가 잘하는 것

#### 1) Post-shuffle partition coalescing

shuffle 후 partition이 지나치게 많고 각각이 너무 작다면, AQE는 이들을 합쳐서 task 수를 줄일 수 있다.

이건 특히 아래 상황에서 유용하다.

- `spark.sql.shuffle.partitions`를 보수적으로 크게 잡았다
- 하지만 실제 필터 이후 데이터는 생각보다 작았다
- 작은 task 수백~수천 개가 스케줄링 오버헤드를 만들고 있었다

#### 2) Join 전략 재선택

정적 계획에서는 sort-merge join으로 잡혔지만, 실제 shuffle 후 한쪽 데이터가 작아졌다면 broadcast hash join 등으로 바뀔 수 있다.

이건 필터 조건이나 semi-join, 사전 집계 때문에 **실행 시점 실제 크기**가 훨씬 작아지는 쿼리에서 효과가 크다.

#### 3) Skewed partition 처리

특정 partition이 비정상적으로 크면, AQE는 그 partition을 더 잘게 나눠 병렬성을 회복하려 시도할 수 있다.

이 기능은 "task 대부분은 30초인데 마지막 2개 task만 15분 걸린다" 같은 전형적인 skew 패턴에서 특히 유용하다.

### AQE가 못하는 것

여기서 많이 실수한다. AQE는 강력하지만 아래 문제를 자동 해결하지 못한다.

#### 1) 잘못된 데이터 모델링

예를 들어 한쪽 테이블이 중복 key 폭발을 일으켜 join 결과가 100배로 불어난다면, AQE는 근본 원인을 해결하지 못한다.

#### 2) 극단적인 small file 문제

scan 단계에서 이미 파일 수가 너무 많아 planning과 open cost가 큰 상황은 AQE보다 upstream compaction과 파일 전략이 먼저다.

#### 3) 잘못된 partitionBy / repartition 남용

출력 직전 무의미하게 큰 shuffle을 만들었다면 AQE가 조금 완화할 수는 있어도, **원래 안 만들어도 됐던 이동 비용**을 제거해주지는 못한다.

#### 4) 심한 skew의 업무적 원인

예를 들어 특정 tenant가 전체 데이터의 40%를 먹는 구조라면, AQE skew split만으로는 한계가 있다. 키 설계, salting, 전처리 집계, tenant 분리 전략까지 봐야 한다.

### 실무 기준

AQE는 기본적으로 켜는 쪽이 맞다. 하지만 중요한 질문은 "AQE를 켰는가"가 아니라 아래다.

- AQE가 실제로 어떤 stage에서 plan을 바꿨는가?
- 바꿨는데도 병목이 남는다면 원인이 skew인가, file layout인가, join explosion인가?
- AQE가 완화한 뒤에도 반복적으로 느린 job 패턴이 같다면 고정 설계를 바꿔야 하지 않는가?

즉 AQE는 기본값이지, 튜닝 사고를 대신해주는 기능은 아니다.

---

## 핵심 개념 2: shuffle partition 수는 "병렬성 숫자"가 아니라 "task 단위 작업량"을 맞추는 레버다

`spark.sql.shuffle.partitions`는 Spark 튜닝에서 가장 많이 건드리는 값 중 하나다. 동시에 가장 자주 오해되는 값이기도 하다.

많은 팀이 이렇게 생각한다.

- partition 수가 많을수록 병렬성이 높으니 무조건 좋다
- 느리면 더 늘려본다
- task가 오래 걸리면 partition을 더 쪼개면 된다

하지만 실제로는 양쪽 극단 모두 문제다.

### 너무 적으면 생기는 일

- task 하나가 너무 큰 데이터를 처리한다
- 메모리 압박이 커지고 spill이 늘어난다
- skew가 있으면 일부 task가 지나치게 길어진다
- 병렬성이 부족해 cluster를 충분히 못 쓴다

### 너무 많으면 생기는 일

- scheduling overhead 증가
- shuffle metadata와 file 수 증가
- 매우 작은 task가 대량 생성되어 오히려 비효율
- output file도 과도하게 늘어날 수 있음

즉 중요한 것은 숫자 자체가 아니라, **task 하나가 다루는 데이터 크기와 분포**다.

### 어떻게 감각을 잡을까

실무에서는 보통 아래 관점으로 본다.

- shuffle 후 각 partition이 지나치게 큰가?
- 반대로 수 MB 단위의 너무 작은 task가 수천 개 생기지 않는가?
- stage time 분포가 고른가?
- 마지막 tail task가 유난히 긴가?

대개 좋은 상태는 "아주 균등하고, 각 task가 너무 크지도 너무 작지도 않은 상태"다. 절대 숫자 하나가 정답은 아니다.

### AQE와의 관계

많은 팀이 `spark.sql.shuffle.partitions`를 낮게 잡아놓고 AQE를 기대한다. 그런데 AQE는 대체로 **많이 나눈 뒤 줄이는 것**에는 강하지만, **처음부터 너무 적게 잡아 병렬성이 부족한 상태를 마술처럼 복구**하진 못한다.

그래서 실무적으로는 아래 전략이 더 자주 맞는다.

- 기본값은 다소 넉넉하게
- AQE coalesce가 실제 크기에 맞게 줄이게 함
- 다만 지나치게 과한 값으로 scheduler/file overhead를 키우지는 않음

### 중요한 함정: 입력 partition 수와 shuffle partition 수를 같은 문제로 보면 안 된다

- 입력 scan partition: 파일 분할, input split, scan 병렬성 문제
- shuffle partition: 연산 후 재배치 결과를 몇 task로 나눌지 문제

둘은 연결되지만 같은 값이 아니다. 예를 들어 input은 파일이 많아 scan task가 많더라도, 집계 후 결과는 훨씬 작아져 shuffle partition을 줄여야 할 수 있다. 반대로 input은 적당해도 key cardinality가 높고 group by가 무거우면 shuffle partition을 더 세밀하게 잡아야 할 수 있다.

---

## 핵심 개념 3: join 성능은 문법이 아니라 "크기 비대칭·카디널리티·데이터 분포"의 문제다

Spark에서 느린 작업 대부분은 join과 관련 있다. 그런데 조인 튜닝을 join hint 몇 개 수준으로 접근하면 한계가 빨리 온다.

### 먼저 구분해야 할 것: 어떤 join이 본질적으로 쉬운가

#### 1) 큰 fact + 작은 dimension

가장 이상적인 패턴이다. dimension이 충분히 작다면 broadcast join 후보가 된다.

장점:

- 큰 쪽 데이터를 재분배하지 않아도 됨
- network shuffle 감소
- 실행 계획이 비교적 안정적

주의점:

- dimension 필터를 join 전에 잘 줄였는가
- 실제 런타임 크기가 broadcast 가능한가
- executor 메모리 압박을 만들지는 않는가

#### 2) 큰 fact + 큰 fact

가장 비싼 패턴 중 하나다. 대개 sort-merge join이나 shuffle 기반 전략으로 간다.

이 경우 핵심은 아래다.

- join key cardinality
- skew 여부
- 사전 필터/사전 집계 가능성
- 한쪽 테이블을 먼저 줄일 수 있는지

#### 3) one-to-many가 아니라 many-to-many로 부풀어 오르는 join

이게 가장 위험하다. 눈에는 join 하나지만 실제로는 row 수가 폭발한다.

예를 들어 주문 fact와 클릭 로그 fact를 사용자 단위·일자 단위로 그냥 붙이면, 생각보다 훨씬 큰 중간 결과가 만들어질 수 있다. 이 경우 병목은 join algorithm보다 **모델링과 집계 타이밍**이다.

### broadcast hint는 만능이 아니다

`broadcast(dim)` 또는 SQL hint는 유용하지만, 아래를 무시하면 오히려 위험하다.

- 실제 크기가 생각보다 큼
- 필터 전 기준으로 커서 executor 메모리를 압박함
- dimension이 자주 바뀌거나 스키마가 커져 broadcast 비용이 증가함
- AQE가 더 나은 전략을 고를 수 있었는데 강제로 막아버림

즉 broadcast는 "작은 테이블이면 무조건"이 아니라, **충분히 작고, 안정적으로 작고, 반복적으로 작은 경우**에 유리하다.

### sort-merge join이 나쁘다는 뜻은 아니다

현업에서 sort-merge join은 자주 기본 전략이다. 문제는 이 전략 자체보다, 아래 상황이다.

- join 전에 줄일 수 있었던 데이터를 그대로 들고 옴
- key skew를 무시함
- 정렬과 shuffle 비용을 감당할 partition 설계가 없음
- join 뒤 바로 다시 큰 aggregation을 해서 shuffle을 두 번 크게 일으킴

즉 sort-merge join을 피하는 게 목표가 아니라, **불필요하게 큰 sort-merge join을 만들지 않는 것**이 목표다.

---

## 핵심 개념 4: skew는 Spark가 느린 가장 흔한 이유인데, 가장 늦게 발견되는 문제이기도 하다

Spark UI를 자세히 보면 stage 대부분은 비슷한 시간에 끝나는데, 일부 task만 끝까지 오래 남는 패턴이 자주 나온다. 이건 거의 전형적인 skew 신호다.

### skew가 생기는 대표 상황

- 특정 tenant가 트래픽 대부분을 차지함
- 특정 날짜/시간 구간만 데이터가 폭증함
- 특정 상품/카테고리/캠페인 key가 압도적으로 큼
- null 또는 default key 한 군데로 데이터가 몰림
- join key 한쪽이 정규화되지 않아 한 값으로 뭉침

### Spark UI에서 보는 신호

- 동일 stage 내 task duration 분산이 극단적
- bytes read / records read가 일부 task에 몰림
- spill이 특정 task에서만 심함
- job 전체 시간이 마지막 몇 task 때문에 결정됨

### skew를 단순 partition 수 증가로 해결하려 하면 왜 실패하나

많은 팀이 skew를 보면 partition 수부터 늘린다. 하지만 key 분포 자체가 치우쳐 있으면, 같은 key는 여전히 같은 bucket/partition으로 몰릴 수 있다. 즉 **균등 분할이 아니라 불균등 해시 분포**라면 partition 수만 늘려도 한계가 있다.

### 대응 전략

#### 1) AQE skew handling 활용

가장 먼저 확인할 현실적인 옵션이다. 극단적으로 큰 post-shuffle partition을 분할해 병렬성을 회복할 수 있다.

하지만 이건 완화책이지 항상 충분한 해결책은 아니다.

#### 2) 사전 집계(pre-aggregation)

join 전에 이미 key 단위로 줄일 수 있으면 크게 도움이 된다.

예:

```sql
WITH click_agg AS (
  SELECT user_id, dt, COUNT(*) AS click_cnt
  FROM raw_clicks
  WHERE dt = '2026-04-03'
  GROUP BY user_id, dt
)
SELECT ...
FROM orders o
JOIN click_agg c
  ON o.user_id = c.user_id
 AND o.dt = c.dt;
```

원래 raw-to-raw join이었다면 중간 결과가 폭발했겠지만, 먼저 줄이면 shuffle과 skew 모두 감소한다.

#### 3) salting

매우 큰 hot key가 명확하면 salting으로 분산시킬 수 있다.

예를 들어 주문 데이터의 특정 `store_id`가 지나치게 크다면,

- 큰 쪽 데이터에 `salt = rand_n` 추가
- 작은 쪽 데이터는 같은 key를 salt 값별로 복제
- `(store_id, salt)`로 join

이 방식은 효과가 크지만 비용도 있다.

- 구현 복잡성 증가
- 작은 테이블 복제 비용 발생
- 잘못 쓰면 오히려 데이터량 증가

즉 salting은 일반 해법이 아니라 **명확한 hot key를 가진 skew 대응 특수 카드**에 가깝다.

#### 4) heavy hitter 분리

가장 큰 key 몇 개는 별도 경로로 처리하고 나머지를 일반 경로로 처리하는 방법도 있다.

예:

- `tenant_id in (1, 7, 42)`는 별도 job 또는 별도 union branch
- 나머지 tenant는 일반 path

운영상 조금 번거롭지만, 멀티테넌트 서비스에서는 의외로 실전적인 방법이다.

---

## 핵심 개념 5: scan 최적화는 shuffle 최적화의 선행조건이다

Spark 튜닝 얘기에서 join, partition, AQE만 강조하면 놓치는 게 scan 단계다. 하지만 scan이 나쁘면 downstream 연산은 거의 반드시 더 나빠진다.

### scan에서 먼저 봐야 할 것

#### 1) 필요한 컬럼만 읽는가

wide table에서 `select *`는 가장 흔한 성능 손실 중 하나다. Parquet/ORC는 column pruning이 강점인데, 상단에서 쓸데없이 모든 컬럼을 끌고 오면 scan I/O와 serialization 비용이 커진다.

#### 2) partition pruning이 실제로 먹는가

테이블이 `dt` 기준 파티셔닝되어 있어도, 쿼리에서 그 조건이 함수에 감싸져 있거나 캐스팅 구조가 애매하면 pruning이 약해질 수 있다.

좋은 예:

```sql
WHERE dt BETWEEN '2026-04-01' AND '2026-04-03'
```

조심할 예:

```sql
WHERE to_date(event_time) = '2026-04-03'
```

후자는 원본 partition 컬럼과 직접 매칭되지 않으면 scan 범위가 불필요하게 넓어질 수 있다.

#### 3) 작은 파일이 과도하지 않은가

작은 파일이 많으면 생기는 일:

- 파일 open 비용 증가
- task scheduling 비용 증가
- 메타데이터 listing/planning 증가
- 실제 데이터량보다 파일 수가 병목이 됨

이 문제는 특히 스트리밍 적재, 잦은 micro-batch write, 과도한 repartition write 뒤에 자주 생긴다.

#### 4) 통계와 predicate pushdown이 살아 있는가

Parquet min/max statistics, dictionary, predicate pushdown이 잘 활용되면 scan 범위를 줄일 수 있다. 하지만 컬럼 타입이 부정확하거나, JSON string에서 나중에 파싱하는 구조라면 pushdown 여지가 줄어든다.

### 중요한 연결 고리

scan 단계에서 1TB 읽던 쿼리를 200GB로 줄이면, 그 뒤 join과 aggregation에 들어가는 shuffle도 같이 줄어든다. 즉 scan 최적화는 단지 읽기 최적화가 아니라, **후속 연산 전체 비용을 줄이는 첫 단계**다.

---

## 핵심 개념 6: repartition, coalesce, partitionBy는 이름이 비슷해 보여도 비용과 목적이 다르다

이 세 개를 헷갈리면 Spark 파이프라인이 금방 무거워진다.

### `repartition()`

보통 shuffle을 동반해 데이터를 새 기준으로 다시 고르게 나누는 데 쓴다.

유용한 경우:

- 특정 key 기준 join/groupBy 전에 분포를 재정렬하고 싶을 때
- write 전에 적정 파일 수를 만들고 싶을 때
- upstream 분포가 너무 치우쳤을 때

주의점:

- 비싼 연산이다
- 습관적으로 중간중간 넣으면 stage가 쓸데없이 늘어난다
- key 없는 `repartition(n)`은 랜덤 재분배라 의미 없는 shuffle이 될 수 있다

### `coalesce()`

주로 partition 수를 줄일 때 쓴다. 경우에 따라 shuffle 없는 축소가 가능해 비교적 저렴하다.

유용한 경우:

- 결과 데이터가 작아 output file 수를 줄이고 싶을 때
- 최종 write 전에 과도한 작은 partition을 합치고 싶을 때

주의점:

- skew된 데이터를 균등하게 재분배하는 도구는 아니다
- 병렬성 회복보다 output partition 축소용으로 보는 편이 맞다

### `partitionBy()`

write 시 디스크 레이아웃을 어떻게 나눌지 정하는 것이다. 실행 중 메모리 partition과는 목적이 다르다.

예:

```python
df.write.mode("overwrite").partitionBy("dt", "region").parquet(path)
```

장점:

- downstream pruning에 도움
- 일자/지역 단위 조회가 많다면 효과적

주의점:

- high-cardinality 컬럼에 걸면 디렉터리와 파일 수 폭발
- downstream 조회 패턴과 맞지 않으면 유지비만 커짐
- write 시점 repartition과 조합을 잘못하면 파일 폭증

### 실무 감각

- `repartition`은 실행 중 데이터 이동 설계
- `coalesce`는 결과 partition 축소 설계
- `partitionBy`는 저장 레이아웃 설계

셋을 같은 층위에서 보면 안 된다.

---

## 핵심 개념 7: Spark SQL 성능은 코드보다 데이터 레이아웃의 영향을 자주 더 크게 받는다

같은 SQL도 데이터 레이아웃이 다르면 체감 성능이 크게 달라진다.

예를 들어 일별 이벤트 테이블을 생각해보자.

### 나쁜 상태

- 하루치 데이터가 수만 개 작은 파일로 쪼개져 있음
- `dt`만 partitionBy 했고 tenant skew가 심함
- 자주 조회하는 컬럼 정렬성이 없음
- late data 보정 때문에 같은 날짜에 작은 append가 계속 발생

이 경우 Spark는 다음 순서로 손해 본다.

1. scan 단계에서 파일 수 때문에 비효율
2. 필요한 key 기준 데이터 locality가 약함
3. groupBy/join 시 shuffle 부담 증가
4. write 후 다시 작은 파일 생성

### 더 나은 상태

- hot partition 주기적 compaction
- 자주 쓰는 시간/tenant 기준으로 적절한 파티션/정렬 전략
- 지나치게 높은 cardinality partitionBy 회피
- downstream 주요 집계 단위에 맞춘 파일 크기 유지

이 관점은 특히 Iceberg, Delta, Hudi 같은 테이블 포맷과 함께 쓸 때 중요하다. 테이블 포맷이 메타데이터와 유지보수를 도와줄 수는 있어도, **업무 쿼리 패턴과 데이터 분포를 무시한 레이아웃**까지 자동으로 구원해주지는 않는다.

---

## 실무 예시 1: 일별 주문 집계 job이 40분에서 11분으로 줄어드는 전형적인 경로

상황을 보자.

- 입력: `fact_order_events`
- 조건: 최근 3일 KST 주문 이벤트
- join: `dim_store`, `dim_product`
- 출력: `mart_daily_store_sales`
- 문제: 데이터가 2배 늘었는데 runtime이 4배 이상 증가

### 초기 구조

```sql
SELECT
  o.dt,
  o.store_id,
  p.category_id,
  SUM(o.amount) AS total_amount,
  COUNT(*) AS order_cnt
FROM fact_order_events o
JOIN dim_store s
  ON o.store_id = s.store_id
JOIN dim_product p
  ON o.product_id = p.product_id
WHERE o.dt BETWEEN '2026-04-01' AND '2026-04-03'
  AND s.region = 'KR'
GROUP BY 1, 2, 3;
```

겉보기엔 괜찮다. 하지만 운영 관측 결과는 이랬다.

- `fact_order_events`는 최근 3일만 읽어도 파일 수가 지나치게 많다
- `dim_store`는 region 필터 후 매우 작지만 broadcast가 안 되고 있었다
- 특정 대형 스토어가 전체 주문의 18%를 차지해 groupBy skew가 존재했다
- `spark.sql.shuffle.partitions`를 1200으로 올려둔 상태였고, AQE는 coalesce를 하긴 했지만 마지막 task tail이 컸다

### 개선 1) dimension 필터를 먼저 줄이고 broadcast 안정화

```sql
WITH kr_store AS (
  SELECT /*+ BROADCAST */ store_id
  FROM dim_store
  WHERE region = 'KR'
)
SELECT
  o.dt,
  o.store_id,
  p.category_id,
  SUM(o.amount) AS total_amount,
  COUNT(*) AS order_cnt
FROM fact_order_events o
JOIN kr_store s
  ON o.store_id = s.store_id
JOIN dim_product p
  ON o.product_id = p.product_id
WHERE o.dt BETWEEN '2026-04-01' AND '2026-04-03'
GROUP BY 1, 2, 3;
```

핵심은 단순 hint가 아니라, **작아질 수 있는 dimension을 조인 전에 실제로 줄였다**는 점이다.

### 개선 2) product dimension에서 불필요 컬럼 제거

wide dimension에서 필요한 key와 category만 남겼다. 이러면 broadcast 부담과 serialization 비용이 줄어든다.

### 개선 3) 주문 fact를 store/day 수준으로 한 번 사전 집계

특정 리포트 요구상 product granularity가 꼭 필요한 구간만 남기고, 일부 중간 전처리를 앞단으로 이동했다. 이 조정으로 raw fact shuffle 크기가 크게 줄었다.

### 개선 4) hot store 분리 처리

상위 몇 개 store는 별도 branch로 계산하고 union했다. 완벽히 일반화된 구조는 아니지만, tail latency를 크게 줄였다.

### 결과

- scan file 수 감소
- broadcast join 적용
- shuffle bytes 감소
- skew tail 완화
- output file 수 감소

이 예시의 핵심은 숫자 하나를 튜닝한 게 아니라, **scan → join → aggregation → skew → write 전체 경로를 한 번에 본 것**이다.

---

## 실무 예시 2: 광고 클릭 로그와 전환 로그 조인에서 many-to-many 폭발을 막는 법

아래 케이스는 실무에서 꽤 흔하다.

- `click_events`: 광고 클릭 로그, 매우 큼
- `conversion_events`: 구매/가입 전환 로그, 비교적 작지만 여전히 큼
- 목적: 캠페인별 전환율 분석

초기 접근은 보통 이렇다.

```sql
SELECT ...
FROM click_events c
JOIN conversion_events v
  ON c.user_id = v.user_id
 AND c.dt = v.dt;
```

문제는 사용자 기준 하루에 클릭도 여러 건, 전환도 여러 건이면 join 결과가 many-to-many로 부풀 수 있다는 점이다. Spark 입장에서는 이게 엄청 비싼 shuffle과 중간 결과 폭발로 이어진다.

### 잘못된 대응

- executor memory 증설
- shuffle partition 수 증가
- broadcast hint 강제

대부분 근본 해결이 아니다.

### 더 나은 접근

#### 1) 먼저 분석 단위를 명확히 한다

정말 raw-to-raw join이 필요한가? 대개는 아니다.

- 사용자-일자 단위 전환 여부가 필요하다면 먼저 user/day 집계
- 캠페인 단위 클릭 수와 전환 수가 필요하다면 각자 먼저 집계

#### 2) 사전 집계 후 join

```sql
WITH click_agg AS (
  SELECT dt, campaign_id, user_id, COUNT(*) AS click_cnt
  FROM click_events
  WHERE dt BETWEEN '2026-04-01' AND '2026-04-03'
  GROUP BY dt, campaign_id, user_id
),
conv_agg AS (
  SELECT dt, user_id, COUNT(*) AS conv_cnt
  FROM conversion_events
  WHERE dt BETWEEN '2026-04-01' AND '2026-04-03'
  GROUP BY dt, user_id
)
SELECT
  c.dt,
  c.campaign_id,
  SUM(c.click_cnt) AS total_clicks,
  SUM(COALESCE(v.conv_cnt, 0)) AS total_conversions
FROM click_agg c
LEFT JOIN conv_agg v
  ON c.dt = v.dt
 AND c.user_id = v.user_id
GROUP BY 1, 2;
```

이렇게 하면 join cardinality와 shuffle 양이 크게 줄어든다.

#### 3) 필요하면 UV 기준, last-touch 기준 등 attribution 규칙을 먼저 정의

Spark 튜닝의 많은 문제가 사실은 쿼리 엔진 문제가 아니라 **분석 정의가 덜 정해진 상태에서 raw 데이터를 무리하게 붙이기 때문**이다.

---

## 실무 예시 3: AQE가 켜져 있는데도 느린 CDC 정제 job의 원인 찾기

상황:

- 소스: Debezium CDC raw topic을 적재한 Bronze 테이블
- 중간: 주문 최신 상태를 만드는 Silver 테이블
- 연산: dedup + latest row 선택 + dimension join + upsert용 write
- 증상: AQE enabled 상태인데 runtime이 불안정, 어떤 날은 8분 어떤 날은 35분

### 관측해보면

- 입력 파일 수 변동이 매우 큼
- 특정 날짜에는 late-arriving CDC가 몰려 raw volume이 급증
- `order_id` 일부 구간이 대형 판매 행사 때문에 skew
- dedup window 함수가 큰 shuffle을 유발

### 왜 AQE만으로 안 풀리나

AQE는 post-shuffle partition coalescing과 skew split을 해주지만,

- scan 전 small file 폭발
- window 직전 입력량 자체 증가
- 이벤트 폭주 시 특정 `order_id` skew
- write 전에 다시 무의미한 repartition

같은 구조적 문제는 그대로 남는다.

### 개선 포인트

#### 1) raw compaction 또는 ingestion batch size 조정

small file을 줄이지 않으면 매일 execution variance가 커진다.

#### 2) dedup 범위 축소

전 테이블 latest가 아니라, 변경 가능 기간과 watermark를 기준으로 최근 구간만 재평가한다.

#### 3) dimension join을 dedup 후로 이동

dedup 전에 붙일 필요 없는 dimension은 뒤로 미뤄 중간 row 수를 줄인다.

#### 4) write 전 repartition 기준 재검토

업무가 날짜 단위 조회 중심이면 `repartition("dt")` 혹은 적정 수 기반 재분배가 의미 있을 수 있지만, 무조건 `repartition(1000)` 같은 값은 거의 항상 다시 봐야 한다.

핵심은 AQE를 켜둔 상태에서도 **왜 어떤 날만 느린지**를 데이터 분포 관점에서 봐야 한다는 점이다. 분포가 흔들리면 실행 시간도 흔들린다.

---

## Spark UI에서 꼭 봐야 하는 것: 느린 이유를 추측하지 말고 stage 단위로 본다

Spark 튜닝은 감으로 하면 재현성이 없다. 최소한 아래는 정기적으로 보는 습관이 필요하다.

### 1) SQL 탭의 physical plan

- broadcast가 실제 적용됐는가?
- sort-merge join인가?
- exchange/shuffle이 어디서 발생하는가?
- AQE가 plan 변경을 했는가?

### 2) stage별 task duration 분포

- 대부분 비슷한가?
- 일부 tail task가 유독 긴가?
- 긴 task가 반복적으로 같은 stage에서만 나타나는가?

### 3) shuffle read/write 크기

- 어느 stage에서 데이터 이동이 갑자기 커지는가?
- join 후인가, groupBy 후인가, window 후인가?

### 4) spill(memory/disk)

- spill이 특정 stage에 집중되는가?
- 메모리 부족인지, partition 크기가 과도한지 분리해서 봐야 한다

### 5) input size / records read

- scan 단계에서 이미 예상보다 과하게 읽고 있지 않은가?
- pruning과 projection이 잘 안 먹는가?

### 6) output file 수

- 결과가 너무 많은 작은 파일로 쓰이고 있지 않은가?
- 다음 job의 scan 비용을 스스로 키우고 있지 않은가?

실무에서는 결국 아래 질문 하나로 수렴한다.

> 이 job은 compute가 느린가, data movement가 느린가, data skew가 느린가, file layout이 느린가?

이 구분이 되면 대응책이 명확해진다.

---

## 핵심 개념 8: window 함수와 dedup은 "조인보다 티가 덜 날 뿐" 매우 비싼 shuffle일 수 있다

Spark 성능 문제를 join 중심으로만 보는 팀이 많지만, 실제 현장에서는 아래 연산도 자주 병목이다.

- `row_number() over (partition by ... order by ...)`
- `dense_rank()`
- `last_value()`
- `dropDuplicates()`
- 최신 row 선택용 dedup
- sessionization이나 이벤트 순서 정렬

이 연산들이 무서운 이유는, SQL 문법상 조인처럼 눈에 띄지 않지만 **특정 key 기준으로 데이터를 다시 모으고 정렬해야 하는 경우가 많기 때문**이다.

### 왜 window가 비싼가

예를 들어 최신 주문 상태를 뽑는 쿼리가 아래와 같다고 하자.

```sql
SELECT *
FROM (
  SELECT
    order_id,
    status,
    updated_at,
    ROW_NUMBER() OVER (
      PARTITION BY order_id
      ORDER BY updated_at DESC
    ) AS rn
  FROM order_cdc_events
  WHERE dt BETWEEN '2026-04-01' AND '2026-04-03'
) t
WHERE rn = 1;
```

업무적으로는 평범하다. 하지만 물리적으로는 거의 항상 아래 비용이 따른다.

- `order_id` 기준 재분배(shuffle)
- 각 partition 내부 정렬(sort)
- 키 편중이 있으면 skew 위험
- late-arriving data가 많으면 특정 key가 비정상적으로 커질 수 있음

즉 이건 사실상 **join이 없는 대형 sort + group 정리 작업**이다.

### `dropDuplicates()`도 공짜가 아니다

DataFrame API에서 `dropDuplicates(["order_id"])`는 매우 편해 보인다. 하지만 내부적으로는 dedup 기준 키에 맞춰 데이터 재배치와 집약이 필요하다. 특히 wide row 전체를 들고 dedup하면 serialization 비용까지 커진다.

### 더 나은 대응

#### 1) dedup 범위를 시간과 변경 구간으로 줄인다

전 테이블 latest를 매번 다시 만드는 대신,

- 최근 N일만 재평가
- 변경된 business key만 추출
- watermark 밖의 안정 구간은 그대로 유지

이런 식으로 범위를 줄이면 shuffle이 급격히 감소한다.

#### 2) window 전에 불필요 컬럼을 제거한다

최신 row 선택에 필요한 컬럼만 먼저 남기고, 나중에 필요하면 다시 join하는 편이 더 나은 경우가 많다.

#### 3) 정렬 기준을 정말 다 써야 하는지 본다

`ORDER BY updated_at DESC, ingest_time DESC, source_priority DESC, ...`처럼 기준이 과도하면 sort 비용이 커진다. 업무적으로 진짜 필요한 tie-breaker만 두는 편이 낫다.

#### 4) raw latest와 serving latest를 분리한다

CDC 정제 계층에서 최신 상태를 만드는 테이블과, 리포트용 서빙 테이블을 분리하면 전체 latest 재계산 횟수를 줄이기 쉽다.

핵심은 이것이다.

> Spark에서 window/dedup은 "편한 문법"이지, "가벼운 연산"이 아니다.

---

## 핵심 개념 9: 파일 크기와 task 크기는 따로 봐야 하지만, 운영에서는 결국 같이 관리해야 한다

Spark 운영에서 자주 놓치는 것이 파일 크기와 task 크기의 관계다. 둘은 동일하지 않지만 실무에서는 강하게 연결된다.

### 파일 크기가 너무 작으면

- scan task 수가 불필요하게 많아진다
- open cost가 커진다
- scheduler overhead 증가
- metadata/listing 부하 증가
- downstream compact/rewrite 필요성 증가

### 파일 크기가 너무 크면

- scan 병렬성이 부족해질 수 있다
- 특정 파일 하나가 느린 task를 만들 수 있다
- predicate pruning이 애매한 경우 낭비가 커질 수 있다

### task 크기가 너무 크면

- spill 증가
- executor 메모리 압박 증가
- tail task 증가
- 실패 시 재시도 비용 증가

### task 크기가 너무 작으면

- 스케줄링만 하다 끝난다
- shuffle/output file이 쪼개진다
- 실제 CPU보다 orchestration cost가 커진다

### 그래서 무엇을 같이 봐야 하나

#### 1) 평균 input file size

파일 자체가 작으면 Spark 쿼리 이전에 ingestion/write 전략을 봐야 한다.

#### 2) stage별 median task input size

파일 수가 적당해 보여도, shuffle 이후 partition이 너무 작거나 클 수 있다. 즉 file과 task는 다른 레이어다.

#### 3) output file size distribution

최종 write 결과가 지나치게 잘게 쪼개졌다면 다음 job의 scan 성능이 나빠진다.

#### 4) hot partition의 file count

전체 평균보다 최근 1일, 최근 3일, 특정 tenant/date 구간의 file count가 더 중요할 때가 많다.

### 실무 감각: "하루 전체 평균"보다 "가장 자주 읽는 파티션의 상태"를 본다

데이터 레이크는 균일하지 않다. 오래된 cold partition은 좀 비효율적이어도 괜찮을 수 있지만, 최근 hot partition이 작고 많게 쪼개져 있으면 매일 반복 비용이 커진다.

즉 파일 전략은 저장비용보다 먼저 **핫 파티션 반복 조회 비용** 관점에서 결정하는 편이 좋다.

---

## 실무 예시 4: 최신 상태 테이블에서 window 병목을 줄이기 위해 "변경된 키만 재계산"하는 패턴

상황을 보자.

- Bronze: `orders_cdc_raw`
- Silver: `orders_latest`
- 요구사항: 최근 변경분을 반영해 최신 주문 상태 유지
- 기존 방식: 최근 30일 raw를 매번 읽고 `row_number()`로 최신 row 선택

초기 SQL은 대략 아래와 같다.

```sql
WITH ranked AS (
  SELECT
    order_id,
    status,
    updated_at,
    amount,
    ROW_NUMBER() OVER (
      PARTITION BY order_id
      ORDER BY updated_at DESC, ingest_time DESC
    ) AS rn
  FROM orders_cdc_raw
  WHERE dt >= date_sub(current_date(), 30)
)
SELECT *
FROM ranked
WHERE rn = 1;
```

처음엔 괜찮다. 하지만 주문량이 커지면 30일 전체를 반복 정렬하는 비용이 너무 커진다.

### 더 나은 방식

1. 최근 적재분에서 변경된 `order_id` 목록만 추출
2. 해당 key에 해당하는 과거 상태만 읽음
3. 그 좁은 집합에서만 window/dedup 수행
4. 최종 `orders_latest`에 merge

예시:

```sql
WITH changed_keys AS (
  SELECT DISTINCT order_id
  FROM orders_cdc_raw
  WHERE dt BETWEEN '2026-04-03' AND '2026-04-04'
),
relevant_history AS (
  SELECT r.*
  FROM orders_cdc_raw r
  JOIN changed_keys k
    ON r.order_id = k.order_id
),
ranked AS (
  SELECT
    order_id,
    status,
    updated_at,
    amount,
    ROW_NUMBER() OVER (
      PARTITION BY order_id
      ORDER BY updated_at DESC, ingest_time DESC
    ) AS rn
  FROM relevant_history
)
SELECT *
FROM ranked
WHERE rn = 1;
```

이 패턴의 장점은 window 대상 범위를 business key 수준으로 대폭 줄인다는 데 있다. 물론 모든 워크로드에 통하지는 않지만, CDC latest 유지 테이블에서는 자주 매우 큰 차이를 만든다.

### 트레이드오프

- 추가 단계(changed key 추출)가 필요함
- 늦게 들어온 과거 이벤트 범위를 얼마나 읽을지 watermark 정책 필요
- key 수가 지나치게 많으면 효과가 제한적일 수 있음

그럼에도 "전 범위 최신 상태 재계산"보다 훨씬 현실적인 경우가 많다.

---

## 실무 예시 5: Python UDF 때문에 plan 최적화가 끊기는 상황을 피하는 법

Spark SQL과 DataFrame API가 충분히 할 수 있는 일을 Python UDF로 감싸면 예상보다 큰 손해가 생긴다.

### 왜 문제인가

- Catalyst 최적화 여지가 줄어든다
- predicate pushdown, codegen, 벡터화 이점을 잃을 수 있다
- Python-JVM 경계 비용이 추가된다
- 직렬화/역직렬화 비용이 커진다

예를 들어 문자열 정규화, 날짜 파싱, 간단한 조건 분기까지 모두 Python UDF로 처리하면 scan 이후 row-by-row 비용이 커지고, 쿼리 최적화가 제한될 수 있다.

### 나쁜 예

```python
from pyspark.sql.functions import udf

@udf("string")
def normalize_region(x):
    if x is None:
        return None
    x = x.strip().lower()
    if x in ("kr", "korea", "south korea"):
        return "KR"
    return x.upper()
```

### 더 나은 예

가능한 범위에서는 내장 함수 조합으로 처리한다.

```python
from pyspark.sql import functions as F

region_col = (
    F.when(F.col("region").isNull(), F.lit(None))
     .when(F.lower(F.trim(F.col("region"))).isin("kr", "korea", "south korea"), F.lit("KR"))
     .otherwise(F.upper(F.trim(F.col("region"))))
)
```

### 언제 UDF가 불가피한가

- 매우 특수한 문자열 파싱
- 외부 라이브러리 의존 로직
- SQL로 표현이 지나치게 복잡한 도메인 규칙

이 경우에도 먼저 물어봐야 한다.

- 이 로직을 upstream 정규화 단계로 뺄 수 없는가?
- 전 row에 매번 적용해야 하는가?
- dimension 테이블로 풀어 join하는 게 더 낫지 않은가?

Spark에서는 "표현하기 편한 코드"보다 **엔진이 최적화할 수 있는 형태**가 훨씬 중요할 때가 많다.

---

## 설정 예시: 실무에서 자주 함께 보는 Spark SQL 옵션과 해석 포인트

아래는 개념을 잡기 위한 예시다. 절대값보다 **왜 이 설정을 보려는가**가 중요하다.

```python
spark.conf.set("spark.sql.adaptive.enabled", "true")
spark.conf.set("spark.sql.adaptive.coalescePartitions.enabled", "true")
spark.conf.set("spark.sql.adaptive.skewJoin.enabled", "true")
spark.conf.set("spark.sql.shuffle.partitions", "800")
spark.conf.set("spark.sql.autoBroadcastJoinThreshold", 64 * 1024 * 1024)
```

### 1) `spark.sql.adaptive.enabled`

기본적으로 켜는 편이 좋다. 다만 "왜 빨라졌는지"는 plan에서 확인해야 한다.

### 2) `spark.sql.adaptive.coalescePartitions.enabled`

과도하게 잘게 쪼개진 shuffle partition을 줄여 scheduler overhead를 낮출 수 있다.

### 3) `spark.sql.adaptive.skewJoin.enabled`

skew join 완화에 유용하다. 하지만 heavy hitter가 명확한 도메인에서는 여전히 사전 집계나 salting이 필요할 수 있다.

### 4) `spark.sql.shuffle.partitions`

고정 정답은 없다. job 특성, 데이터 크기, cluster 병렬성, AQE coalesce 여부와 같이 봐야 한다.

### 5) `spark.sql.autoBroadcastJoinThreshold`

무조건 크게 올린다고 좋은 게 아니다. broadcast 후보 dimension의 안정적 크기와 executor memory 여유를 같이 봐야 한다.

### 설정 튜닝에서 중요한 태도

- 전역 설정 하나로 모든 job을 해결하려 하지 말 것
- job별 특성과 데이터 분포를 먼저 볼 것
- 바꾼 설정이 physical plan과 stage 분포를 어떻게 바꿨는지 확인할 것

설정은 원인 분석을 대체하는 수단이 아니라, **원인 분석 뒤에 선택하는 레버**다.

---

## 트레이드오프 1: partition을 많이 나누면 병렬성이 좋아지지만 메타데이터와 scheduling 비용이 커진다

### 장점

- 큰 task를 잘게 쪼개 병렬 처리 가능
- skew가 약한 경우 tail latency 감소
- spill 완화 가능

### 비용

- task 수 증가
- scheduler overhead 증가
- shuffle metadata 증가
- 작은 output file 폭발 가능

즉 partition 수는 많이 나누는 게 아니라, **업무 크기와 cluster 특성에 맞게 나누는 것**이다.

---

## 트레이드오프 2: broadcast join은 빠르지만 메모리와 안정성을 먹는다

### 장점

- 큰 shuffle 감소
- 작은 dimension join에 매우 유리
- plan 단순화

### 비용

- executor 메모리 사용 증가
- 예상보다 테이블이 커지면 불안정
- hint 남용 시 AQE 재선택 여지 축소

즉 broadcast는 좋은 기본 카드지만, **항상 안전한 카드**는 아니다.

---

## 트레이드오프 3: salting은 skew를 완화하지만 쿼리와 운영 복잡도를 키운다

### 장점

- heavy hitter key를 분산 가능
- 극단적 skew에서 효과적

### 비용

- 구현 복잡성
- 작은 테이블 복제 비용
- 디버깅 난도 증가
- 일반 쿼리 재사용성 저하

즉 salting은 skew가 심각하고 business key가 명확할 때만 쓰는 편이 좋다.

---

## 트레이드오프 4: partitionBy는 조회를 빠르게 할 수 있지만 잘못 쓰면 파일/디렉터리 폭발을 만든다

### 잘 맞는 경우

- 날짜, 지역, 환경처럼 필터가 자주 쓰이고 cardinality가 과도하지 않을 때
- downstream pruning이 명확할 때

### 위험한 경우

- user_id, order_id, session_id 같은 고카디널리티 컬럼
- 쓰기 빈도가 높고 작은 배치가 많은 경우
- downstream 조회 패턴이 그 partition과 맞지 않을 때

즉 저장 partition은 **엔티티 식별자 중심이 아니라 조회/관리 단위 중심**으로 봐야 한다.

---

## 흔한 실수 1: 느리면 executor 메모리와 코어부터 올린다

리소스 증설이 도움이 될 때도 있다. 하지만 scan 폭, shuffle 구조, skew를 안 보고 메모리만 늘리면 같은 병목을 더 비싸게 돌리는 것에 가깝다.

---

## 흔한 실수 2: `spark.sql.shuffle.partitions`를 한 번 정해놓고 모든 job에 동일 적용한다

job마다 다르다.

- 작은 dimension enrichment job
- 대형 aggregation job
- wide window 계산 job
- CDC dedup job

필요한 partition 수와 task 크기가 다르다. 전역 하나로 끝내려는 사고가 문제다.

---

## 흔한 실수 3: AQE가 있으니 repartition 설계를 안 해도 된다고 생각한다

AQE는 보정장치다. 하지만 애초에 잘못된 repartition, 불필요한 exchange, 무의미한 wide transformation까지 없애주지는 못한다.

---

## 흔한 실수 4: broadcast hint를 남발한다

작아 보이던 dimension이 시간이 지나며 커질 수 있다. 처음엔 빨랐는데 어느 날 메모리 압박과 plan instability가 생기는 이유가 여기에 있다.

---

## 흔한 실수 5: skew를 partition 수 증가로만 해결하려 한다

데이터 분포가 불균형한데 partition 수만 늘리면, 큰 key는 여전히 큰 key다. skew는 분포 문제이지 단순 분할 숫자 문제가 아니다.

---

## 흔한 실수 6: raw-to-raw join을 너무 쉽게 한다

분석 정의가 애매한 상태에서 raw fact끼리 바로 붙이면 중간 결과가 폭발하기 쉽다. 대부분은 사전 집계나 의미 있는 grain 정의가 먼저다.

---

## 흔한 실수 7: output file을 다음 팀의 문제라고 생각한다

오늘 job이 만든 작은 파일은 내일 내 job의 scan 병목으로 돌아온다. Spark 파이프라인에서는 write 품질이 미래의 read 품질이다.

---

## 흔한 실수 8: Spark UI를 안 보고 코드만 고친다

같은 SQL이라도 plan, stage, shuffle, skew 신호를 봐야 한다. UI를 안 보면 개선이 우연에 의존하게 된다.

---

## 설계 체크리스트: 새 Spark 배치/ETL 파이프라인을 만들 때

### 입력 데이터

- [ ] 필요한 날짜/파티션만 읽도록 pruning 조건이 명확한가?
- [ ] 필요한 컬럼만 projection하는가?
- [ ] 작은 파일이 과도하게 쌓이지 않도록 upstream write 전략이 있는가?
- [ ] watermark 또는 late-data 범위가 정의되어 있는가?

### 조인과 집계

- [ ] join 전에 줄일 수 있는 dimension/filter가 있는가?
- [ ] raw-to-raw join 대신 사전 집계가 가능한가?
- [ ] one-to-many / many-to-many 폭발 가능성을 검토했는가?
- [ ] hot key나 heavy hitter가 있는지 확인했는가?

### 실행 계획

- [ ] AQE를 기본 활성화했는가?
- [ ] broadcast가 기대대로 적용되는가?
- [ ] shuffle partition 수가 job 특성에 맞는가?
- [ ] 불필요한 repartition/exchange가 없는가?

### 출력 레이아웃

- [ ] downstream 조회 패턴에 맞는 `partitionBy`인가?
- [ ] output file 수가 과도하지 않은가?
- [ ] overwrite/append/merge 전략이 late data 운영과 맞는가?
- [ ] 다음 단계 scan 비용까지 고려했는가?

### 관측성

- [ ] stage별 task 분산, shuffle 크기, spill을 볼 수 있는가?
- [ ] 특정 key skew를 주기적으로 점검하는가?
- [ ] job runtime뿐 아니라 input file 수, output file 수를 보는가?
- [ ] 느린 날과 빠른 날의 데이터 분포 차이를 비교할 수 있는가?

---

## 운영 체크리스트: 이미 느린 Spark job을 디버깅할 때 순서대로 볼 것

1. **scan이 과한가?**
   - 파티션 pruning이 먹는가
   - 작은 파일이 너무 많은가
   - 불필요 컬럼을 읽는가

2. **shuffle이 과한가?**
   - join/groupBy/window 어디서 큰 exchange가 발생하는가
   - 쿼리 grain이 과도하게 세밀하지 않은가

3. **skew가 있는가?**
   - tail task가 반복적으로 나타나는가
   - 특정 key가 데이터 대부분을 차지하는가

4. **join 전략이 맞는가?**
   - 작은 테이블을 충분히 줄였는가
   - many-to-many가 숨어 있지 않은가
   - broadcast를 강제할 가치가 있는가

5. **write가 미래 병목을 만드는가?**
   - output file이 너무 많지 않은가
   - partitionBy가 지나치게 세분화되지 않았는가

이 순서를 지키면 엉뚱한 값부터 만지는 일을 줄일 수 있다.

---

## 실무에서 추천하는 기본 운영 원칙

### 1) AQE는 기본 켠다. 하지만 plan 변화를 실제로 본다

설정만 켜놓고 끝내지 말고, 어떤 query/stage에서 어떤 adaptive change가 있었는지 확인해야 한다.

### 2) scan file 수와 output file 수를 런타임 메트릭으로 같이 본다

job 성공 시간만 보면 늦다. 파일 수 폭증은 다음 장애의 선행지표다.

### 3) hot key 리포트를 별도로 만든다

tenant, store, product, user 등 업무 key 분포를 주기적으로 보지 않으면 skew는 늘 뒤늦게 발견된다.

### 4) raw fact끼리 바로 붙이기 전에 grain을 먼저 정의한다

기술 튜닝보다 데이터 모델링이 더 큰 개선을 줄 때가 많다.

### 5) repartition은 의식적으로, coalesce는 목적이 분명할 때만 쓴다

"중간에 한번 정리" 같은 습관성 repartition은 비싼 실수다.

### 6) write 레이아웃을 downstream 쿼리와 함께 설계한다

배치를 만드는 팀과 조회하는 팀이 다르면 특히 중요하다. 저장 partition이 조회 패턴과 어긋나면 매일 큰 shuffle을 강제하게 된다.

---

## 한 줄 정리

Apache Spark 성능의 핵심은 리소스를 더 넣는 것이 아니라, **AQE가 잘 작동할 수 있도록 scan 범위를 줄이고, shuffle partition을 적정 task 크기로 맞추고, skew를 데이터 분포 문제로 다루며, write 레이아웃까지 포함해 데이터 이동 자체를 줄이는 것**이다.
