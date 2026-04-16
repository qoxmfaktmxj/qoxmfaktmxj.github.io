---
layout: post
title: "Apache Pinot 실전: Segment, Partitioning, Star-Tree, Upsert로 초저지연 분석 API를 운영하는 기준"
date: 2026-04-16 11:40:00 +0900
categories: [data-infra]
tags: [study, data-infra, apache-pinot, pinot, realtime-analytics, segment, partitioning, star-tree, upsert, olap]
permalink: /data-infra/2026/04/16/study-apache-pinot-segment-partitioning-star-tree-upsert-low-latency-analytics.html
---

## 배경: 대시보드는 실시간이어야 하는데, 웨어하우스만으로는 왜 자꾸 늦고 비싸질까?

서비스가 커질수록 분석 요구는 두 갈래로 갈라진다.

하나는 느려도 괜찮은 배치형 분석이다.

- 어제 매출을 정산한다
- 주간 리텐션을 계산한다
- 월간 KPI를 검증한다
- 머신러닝 학습용 피처를 만든다

다른 하나는 늦으면 곧바로 가치가 떨어지는 조회다.

- 지금 5분간 광고 캠페인 CTR이 급락했는가
- 특정 테넌트의 에러율이 방금 치솟았는가
- 운영 화면에서 방금 주문된 건이 집계 API에 바로 반영되는가
- 상품 상세 페이지가 현재 어떤 필터 조합에서 가장 많이 눌리는가
- 장애 대응 중 특정 서비스의 최근 15분 지표를 1초 안에 계속 새로고침할 수 있는가

이런 요구는 SQL만으로 해결되지 않는다.

정확히는 SQL 엔진보다 저장 구조와 질의 경로가 달라져야 한다.

많은 팀이 여기서 처음 부딪히는 현실은 비슷하다.

- PostgreSQL read replica에 분석 쿼리를 붙였더니 운영 트래픽과 서로 흔든다
- BigQuery, Athena, Spark는 강력하지만 초저지연 API 응답용으로는 과하고 비용도 커진다
- Elasticsearch는 검색에는 잘 맞지만 집계 구조를 설계하다 보면 운영 감각이 어긋난다
- ClickHouse는 빠르지만 테이블 레이아웃과 쿼리 패턴 설계가 잘못되면 merge, mutation, 비용이 새 병목이 된다
- Redis는 너무 비싸고, 사전 집계 캐시는 요구사항이 늘어날수록 폭발한다

이 지점에서 자주 등장하는 선택지 중 하나가 Apache Pinot다.

Pinot는 단순히 빠른 OLAP DB가 아니다.

실무에서는 더 정확히 이렇게 이해하는 편이 맞다.

> Pinot는 이벤트 스트림과 사용자 조회 사이에서, 초저지연 분석 질의를 위한 읽기 경로를 강하게 설계한 분산 분석 저장소다.

즉 “데이터를 쌓아 두는 곳”이라기보다,

- 최근 데이터가 계속 유입되고
- 특정 차원 필터가 반복되고
- 집계 응답 시간이 API 수준으로 짧아야 하며
- 테넌트, 시간, 캠페인, 상품, 지역 같은 축으로 반복 조회되고
- 장애 상황에서도 부분 실패를 감당해야 하는

그런 환경에 맞게 설계된 시스템이다.

하지만 Pinot도 만능은 아니다.

- warehouse를 대체하는 만능 엔진이 아니고
- 복잡한 대형 join에 강한 시스템도 아니며
- upsert를 켜면 공짜로 최신 상태 조회가 해결되는 것도 아니고
- star-tree만 붙이면 모든 집계가 빨라지는 것도 아니다
- 세그먼트와 파티션을 잘못 설계하면 빠른 엔진이 아니라 빠르게 비싸지는 엔진이 된다

오늘 글은 Pinot 입문이 아니다.

중급 이상 개발자가 실제 운영 도입 전 반드시 정리해야 할 질문을 기준으로,

**Segment, Partitioning, Star-Tree, Upsert를 중심으로 Pinot를 운영 가능한 수준으로 설계하는 기준**을 정리한다.

핵심 질문은 여섯 가지다.

1. Pinot는 warehouse, search engine, OLTP DB와 각각 어떤 경계에서 나눠 써야 하는가
2. Segment와 partition은 단순 저장 구조가 아니라 질의 응답 시간에 어떻게 직접 영향을 주는가
3. Star-Tree는 언제 강력하고, 언제 오히려 저장 비용과 설계 복잡도만 올리는가
4. Upsert는 어떤 엔터티 조회에 잘 맞고, 어떤 이벤트 로그에는 오히려 독이 되는가
5. 실시간 수집과 배치 보정, late event, reprocessing을 어떤 구조로 분리해야 하는가
6. 운영 지표와 흔한 실패 패턴을 무엇부터 봐야 장애 복구 속도가 빨라지는가

결론부터 말하면 Pinot의 핵심은 “실시간 분석 DB”라는 한 줄 설명이 아니다.

더 정확한 본질은 이것이다.

**질의 패턴이 반복되는 초저지연 집계 문제를, 세그먼트 라우팅과 인덱스, 사전 집계, 최신 상태 유지 정책으로 구조적으로 줄이는 시스템**이다.

이 관점을 놓치면 Pinot는 좋은 선택이 아니다.

이 관점을 정확히 잡으면,

- 대시보드 API가 warehouse 의존에서 분리되고
- 운영성 있는 실시간 집계 계층을 만들 수 있으며
- 캐시 계층이 무한정 늘어나는 문제를 줄이고
- 데이터 플랫폼과 서비스 API 사이 경계를 더 명확하게 만들 수 있다.

---

## 먼저 큰 그림: Pinot는 “실시간 수집”보다 “예측 가능한 읽기 경로”에 더 강한 시스템이다

Pinot를 처음 볼 때 많은 사람이 Kafka 연동과 실시간 ingestion에 먼저 꽂힌다.

물론 중요하다.

하지만 운영 관점에서 더 중요한 것은 쓰기보다 읽기다.

왜냐하면 Pinot를 도입하는 이유는 대개 ingest 그 자체가 아니라,

- 특정 시간 범위를 빠르게 자르고
- 특정 차원으로 필터링하고
- count, sum, max, percentile 같은 집계를 반복 수행하고
- 최근 데이터와 과거 데이터가 함께 보이게 하고
- 그 결과를 사람 또는 서비스 API가 즉시 소비하게 만드는 것

이기 때문이다.

이 점에서 Pinot는 아래 시스템들과 역할이 다르다.

### PostgreSQL/MySQL 같은 OLTP와의 차이

OLTP는 보통 다음을 우선한다.

- 단건 row 읽기와 수정
- 강한 트랜잭션 정합성
- 인덱스를 통한 point lookup
- 짧고 예측 가능한 CRUD

Pinot는 보통 다음을 우선한다.

- append 중심 이벤트 유입
- 집계와 스캔이 많은 질의
- 컬럼형 저장과 인덱스 기반 필터 축소
- segment 단위 라우팅과 병렬 처리
- 실시간과 배치 세그먼트의 병행 조회

즉 주문 한 건을 안전하게 업데이트하는 시스템이 아니라,

**수많은 이벤트를 빨리 요약해서 읽게 하는 시스템**에 가깝다.

### Warehouse(BigQuery, Snowflake, Redshift, Spark)와의 차이

웨어하우스는 보통 아래에 강하다.

- 큰 범위 full scan
- 복잡한 join과 batch transform
- 대규모 backfill
- BI/ELT 친화적 모델링
- 데이터 정확도 중심의 재계산

Pinot는 보통 아래에 강하다.

- 최근 구간 반복 조회
- 지연 민감 API
- 제한된 형태의 집계성 질의
- 자주 쓰는 필터 축의 빠른 pruning
- 사용자 facing 대시보드, 운영 모니터링, near-real-time 분석

즉 warehouse는 “정답을 계산하는 시스템”에 가깝고,

Pinot는 “반복 질의를 매우 빠르게 서비스하는 시스템”에 더 가깝다.

둘 중 하나만 고르는 문제가 아니라,

**정답 계산 계층과 초저지연 서빙 계층을 분리할 필요가 있을 때 Pinot가 의미가 커진다.**

### Elasticsearch와의 차이

Pinot와 Elasticsearch를 같은 부류로 보는 경우가 많다.

둘 다 검색/집계가 가능하고 분산 저장 구조를 가진다.

하지만 의도는 꽤 다르다.

Elasticsearch는 텍스트 검색과 문서 검색, relevance, log 탐색에 강하다.

Pinot는 low-latency OLAP 집계에 더 직접적이다.

예를 들어,

- 텍스트 검색, 로그 원문 탐색, fuzzy search가 중요하면 Elasticsearch 쪽이 자연스럽고
- 시간 범위 + 다차원 필터 + 반복 집계 응답이 핵심이면 Pinot 쪽이 더 자연스럽다.

### ClickHouse와의 차이

Pinot와 ClickHouse는 자주 같이 언급된다.

둘 다 빠른 분석 엔진이기 때문이다.

하지만 운영 감각은 다르다.

ClickHouse는 저장 레이아웃과 merge, 정렬 키 설계가 매우 중요하고, raw부터 rollup까지 하나의 세계로 가져가는 경우가 많다.

Pinot는 실시간 ingestion, segment 단위 질의 분산, 다양한 인덱스 조합, star-tree 기반 사전 집계, hybrid table 모델이 더 중심에 있다.

대략 이렇게 나누면 감이 좋다.

- 초저지연 API 서빙, 반복 집계, Kafka 직접 연동, hybrid serving이 중요하다 → Pinot가 잘 맞을 수 있다
- 대형 분석 저장, 폭넓은 SQL, 대규모 배치 질의, 저장 압축과 읽기 효율 최적화가 중요하다 → ClickHouse가 더 자연스러울 수 있다

물론 절대 규칙은 아니다.

핵심은 도구 이름이 아니라 읽기 패턴이다.

### Pinot를 도입해도 되는 질문

아래 질문에 “예”가 많으면 Pinot 후보가 된다.

- 최근 수분~수시간 데이터를 거의 실시간으로 조회해야 하는가
- 쿼리 패턴이 대체로 정형적이고 반복적인가
- API 응답 시간 요구가 수백 ms~수 초 수준으로 민감한가
- 자주 사용하는 필터 차원이 비교적 명확한가
- full warehouse query 대신 serving-oriented storage가 필요한가
- 배치와 실시간을 한 화면에서 합쳐 보여줄 필요가 있는가

반대로 아래가 핵심이면 Pinot가 과할 수 있다.

- 복잡한 ad-hoc 분석이 대부분이다
- 대형 join과 자유도가 높은 SQL이 핵심이다
- 최신성보다 정확한 재계산이 중요하다
- 서빙 레이어보다 데이터 변환 레이어가 더 큰 문제다

즉 Pinot의 본질은 “실시간 수집”이 아니라,

**읽기 경로가 충분히 반복적이고 지연 민감할 때 그 경로를 구조적으로 단순화하는 것**이다.

---

## 핵심 개념 1: Segment는 저장 단위가 아니라 라우팅, 병렬성, 인덱스 효율을 동시에 결정하는 질의 기본 단위다

Pinot를 이해할 때 가장 먼저 잡아야 할 개념은 segment다.

초보 시절에는 segment를 단순한 파일 조각처럼 본다.

하지만 실무에서는 segment가 아래를 거의 동시에 결정한다.

- 어떤 서버가 질의를 처리할 것인가
- 어느 정도 병렬성이 생길 것인가
- 어떤 인덱스 메타데이터를 읽을 것인가
- 어느 범위를 스캔하고 어느 범위를 건너뛸 수 있는가
- 실시간 segment와 offline segment를 어떻게 합쳐 읽을 것인가

즉 segment는 저장 단위이자 질의 실행 단위다.

### Pinot의 읽기 경로를 아주 단순하게 보면

1. 브로커가 질의를 받는다
2. 질의 조건을 보고 어떤 세그먼트가 후보인지 추린다
3. 서버들이 각 세그먼트를 병렬로 읽는다
4. 부분 집계를 수행한다
5. 브로커가 결과를 머지해 반환한다

이 과정에서 세그먼트 수와 크기, 시간 분포, 파티션 메타데이터, 인덱스 상태가 응답 시간에 직접 영향을 준다.

### segment가 너무 작으면 왜 문제인가

많은 팀이 ingestion을 빨리 반영하려고 세그먼트를 지나치게 자주 flush한다.

그러면 좋아 보인다.

- 최신 데이터가 더 빨리 질의 가능해진다
- 실시간성이 좋아 보인다

하지만 곧 비용이 돌아온다.

- 세그먼트 개수가 급증한다
- 브로커 메타데이터 관리 비용이 커진다
- 질의 시 fan-out이 늘어난다
- 인덱스 메타데이터가 더 잘게 쪼개져 전체 overhead가 증가한다
- compaction이나 segment replacement 전략이 복잡해진다

즉 초저지연을 얻으려다가 라우팅 비용으로 잃을 수 있다.

### segment가 너무 크면 왜 문제인가

반대로 세그먼트를 과도하게 크게 만들면,

- 특정 질의가 훨씬 큰 덩어리를 읽어야 하고
- pruning 효율이 떨어지고
- 실시간 데이터 반영 간격이 길어지고
- 재적재나 rebuild 시 비용이 커지고
- 단일 세그먼트 skew가 생길 수 있다.

결국 핵심은 “무조건 큰 세그먼트”도 아니고 “무조건 자주 flush”도 아니다.

**자주 쓰는 질의 범위와 ingest량, freshness 요구를 같이 놓고 segment life cycle을 맞춰야 한다.**

### 실무에서 segment를 볼 때의 질문

- 최근 1시간 질의가 많은가, 최근 1일 질의가 많은가
- 시간 필터가 거의 항상 들어가는가
- 테넌트별 접근 패턴이 뚜렷한가
- 하나의 질의가 평균 몇 개 세그먼트를 두드리는가
- 세그먼트당 row 수와 크기가 너무 극단적이지 않은가
- broker fan-out이 지연의 주원인인가, server scan이 주원인인가

이 질문을 먼저 던져야 한다.

### consuming segment와 immutable segment를 다르게 봐야 한다

실시간 테이블에서는 현재 ingest 중인 consuming segment와 flush된 immutable segment가 공존한다.

이 차이는 운영에서 중요하다.

- consuming segment는 최신성을 주지만 질의 비용이 더 불안정할 수 있다
- immutable segment는 인덱스와 최적화가 안정적이다
- 너무 긴 consuming 구간은 최신성은 좋지만 메모리와 질의 편차를 키울 수 있다
- 너무 짧은 consuming 구간은 최신성은 좋지만 세그먼트 폭증을 만든다

즉 “실시간”이라는 한 단어 안에,

- flush 주기
- commit 주기
- 세그먼트 수
- query fan-out
- 메모리 사용량
- index build 비용

이 다 들어 있다.

### 세그먼트 설계를 잘했을 때 생기는 효과

- 시간 조건이 있는 질의가 빠르게 필요한 세그먼트만 읽는다
- fan-out이 줄어 tail latency가 안정된다
- 서버 간 workload skew가 줄어든다
- 인덱스 효율이 높아진다
- real-time과 offline을 함께 붙여도 응답 편차가 낮아진다

Pinot에서 응답 시간이 흔들릴 때,

SQL 한 줄보다 먼저 봐야 할 것이 세그먼트다.

---

## 핵심 개념 2: Partitioning은 “데이터를 나누는 기능”이 아니라 “질의 후보를 버리는 기능”으로 이해해야 한다

분산 분석 시스템에서 partition이라는 단어는 너무 익숙해서 오히려 자주 헷갈린다.

Pinot에서도 partition을 그냥 “샤딩” 정도로 이해하면 설계가 어긋난다.

실무에서는 partition의 핵심 효과를 이렇게 잡는 편이 좋다.

> 좋은 partitioning은 읽어야 할 세그먼트를 늘리는 것이 아니라, 읽지 않아도 되는 세그먼트를 더 공격적으로 버리게 만든다.

즉 partitioning의 목적은 분산 자체보다 pruning이다.

### 어떤 차원으로 partitioning을 고민해야 하는가

보통 아래 축이 후보가 된다.

- tenant_id
- campaign_id
- user_region
- organization_id
- event_date 또는 time bucket
- account_id

하지만 자주 필터링된다고 무조건 partitioning 대상이 되는 것은 아니다.

### 좋은 partition key의 조건

1. **질의에서 자주 명시적으로 필터링된다**
2. **값 분포가 너무 한쪽으로 쏠리지 않는다**
3. **조회 패턴이 반복적이다**
4. **운영적으로 라우팅 이점이 분명하다**
5. **데이터 재분배 비용을 감당할 수 있다**

예를 들어 멀티테넌트 분석 API에서 거의 모든 질의가 `tenant_id = ?`를 포함한다면,

tenant 기반 partitioning은 매우 강력할 수 있다.

반면 `country`처럼 필터는 자주 있지만 값 불균형이 심하고 단독 필터 가치가 낮다면,

인덱스로 처리하는 편이 나을 수도 있다.

### time partition만으로는 부족한 경우

많은 팀이 시간축만으로 충분하다고 생각한다.

물론 시간 조건은 거의 항상 중요하다.

하지만 실제 API 질의는 보통 시간만 보지 않는다.

- 최근 15분, 특정 tenant의 클릭 수
- 최근 1시간, 특정 캠페인의 전환율
- 최근 24시간, 특정 조직의 에러 분포

즉 시간은 기본이고,

그 위에 tenant나 campaign 같은 access pattern 축이 하나 더 있어야 질의 후보를 많이 줄일 수 있다.

### partition을 과하게 세밀하게 두면 생기는 문제

여기서 흔히 나오는 욕심이 있다.

- 시간도 나누자
- tenant도 나누자
- region도 나누자
- campaign도 나누자

이렇게 되면 좋아 보이지만 현실은 다르다.

- 세그먼트 수가 급증한다
- 특정 키에만 데이터가 몰려 skew가 생긴다
- ingestion path가 복잡해진다
- rebalancing 비용이 커진다
- query routing 규칙을 이해하기 어려워진다
- 운영자가 어떤 질의가 왜 느린지 직관적으로 파악하기 어려워진다

partition은 많이 나눌수록 이득인 기능이 아니다.

**읽지 않을 세그먼트를 명확하게 버리는 데 충분한 정도로만 나누는 것**이 중요하다.

### partition과 replica를 헷갈리면 안 된다

운영 중 자주 섞이는 개념이 partition과 replica다.

- partition은 데이터 분산 및 질의 pruning과 관련이 있고
- replica는 가용성과 부하 분산과 관련이 있다

즉 replica를 늘린다고 pruning이 좋아지는 것은 아니고,

partition을 늘린다고 가용성이 자동으로 해결되는 것도 아니다.

### 멀티테넌트 서비스에서 자주 쓰는 감각

멀티테넌트 분석 API라면 아래를 같이 본다.

- 대부분의 질의가 tenant filter를 포함하는가
- 극단적 고트래픽 tenant가 소수 존재하는가
- tenant 간 noisy neighbor를 라우팅 수준에서 줄일 가치가 있는가
- SLA가 모든 tenant에 동일한가, premium tenant가 따로 있는가

이런 서비스에서는 table을 하나만 두고 모든 tenant를 섞는 전략보다,

- tenant 중심 partitioning
- 중요 고객 전용 테이블 분리
- 라우팅 최적화

같은 선택이 훨씬 효과적일 수 있다.

### partition은 쿼리 설계와 함께 봐야 한다

partitioning을 아무리 잘해도,

애플리케이션 쿼리가 그 partition key를 질의에 거의 넣지 않으면 이득이 줄어든다.

즉 인프라 설계와 API 설계가 연결돼야 한다.

- 서버가 tenant filter를 항상 강제하는가
- 시간 범위를 기본 파라미터로 받는가
- limit 없는 전역 집계를 막는가
- wide scan이 필요한 화면은 캐시 또는 rollup으로 분리하는가

이런 계약이 없으면 partitioning 효과는 반감된다.

---

## 핵심 개념 3: 인덱스는 많이 붙이는 기술이 아니라 쿼리 패턴별로 책임을 분리하는 기술이다

Pinot를 소개할 때 자주 보이는 장점 중 하나가 다양한 인덱스다.

- inverted index
- range index
- bloom filter
- text index
- json index
- star-tree index

처음 보면 든든하다.

하지만 실무에서는 반대로 더 위험해질 수 있다.

“필터 자주 쓰는 컬럼에 다 인덱스 붙이면 되겠지”라고 시작하면,

- 세그먼트 build 시간이 늘고
- 저장 비용이 커지고
- ingestion latency가 올라가고
- 운영자는 왜 빨라졌는지, 왜 느려졌는지 설명하기 어려워진다.

즉 인덱스의 핵심은 개수보다 역할 분리다.

### inverted index는 어떤 때 강한가

정확 일치 필터가 반복될 때 강하다.

예를 들어,

- tenant_id
- campaign_id
- region_code
- status
- event_type

같은 컬럼은 inverted index와 잘 맞는다.

특히 필터 선택도가 어느 정도 있고 질의에서 자주 등장하면 효과가 크다.

다만 모든 dimension에 다 붙일 필요는 없다.

질의 빈도와 선택도를 먼저 봐야 한다.

### range index는 어떤 때 생각할까

범위 조건이 잦고 단순 숫자/시간 컬럼에 유용하다.

예를 들어,

- price
- latency_ms
- score
- event_time

다만 time filter는 세그먼트 pruning과 time column 설계만으로도 상당 부분 해결되는 경우가 많다.

즉 range index를 추가하기 전에,

- 세그먼트 시간 분포가 잘 잡혀 있는지
- 쿼리가 정말 세그먼트 내부 범위 탐색에서 병목이 있는지

를 먼저 확인해야 한다.

### bloom filter는 point lookup성 필터가 있을 때만 신중하게

특정 ID 존재 여부나 고선택도 equality filter에 의미가 있을 수 있다.

하지만 이것도 무조건 좋은 것은 아니다.

잘 안 쓰는 컬럼에 bloom filter를 남발하면 저장 비용만 늘어난다.

### text/json index는 검색 요구가 있을 때만 명확히

Pinot가 JSON과 text를 다룰 수 있다고 해서,

문서 검색 시스템처럼 기대하면 안 된다.

실시간 분석 맥락에서 필요한 수준의 보조 검색 기능으로 이해하는 편이 안전하다.

### Star-Tree는 일반 인덱스와 완전히 다른 계층이다

여기서 가장 중요한 것이 star-tree다.

star-tree는 단순히 “빠르게 찾아주는 인덱스”가 아니다.

정확히는,

**반복되는 집계 패턴을 세그먼트 내부에 부분 사전 집계 형태로 물리화하는 구조**에 가깝다.

즉 count, sum, min, max 같은 집계가 특정 차원 조합에서 자주 반복되면,

매번 raw row를 스캔하는 대신 더 작은 pre-aggregated tree를 읽을 수 있다.

이게 강력한 이유는 명확하다.

- 대시보드 API는 같은 쿼리 패턴을 계속 반복한다
- 차원 조합이 제한적일 때가 많다
- 사용자마다 필터 값만 다르고 질의 모양은 비슷하다

이 조건에서는 star-tree가 압도적으로 유리할 수 있다.

하지만 제한도 뚜렷하다.

- 모든 질의 패턴을 커버하지 못한다
- 차원 조합이 너무 많으면 저장 비용이 급증한다
- 집계 함수 조합을 잘못 선택하면 기대 이득이 작다
- 운영자는 어떤 쿼리가 star-tree를 타고 어떤 쿼리가 raw scan으로 떨어지는지 알아야 한다

즉 star-tree는 “Pinot가 빠른 이유”라기보다,

**반복 집계 경로를 아주 강하게 최적화하는 선택적 가속 장치**다.

### 인덱스 전략을 고를 때의 질문

- 질의에서 거의 항상 등장하는 equality filter는 무엇인가
- 시간 조건 외에 강한 pruning 축이 있는가
- point lookup성 ID 질의가 실제로 많은가
- JSON/text 검색은 보조 기능인가, 핵심 기능인가
- 반복 집계 패턴이 충분히 정형화되어 있는가
- ingestion 비용 증가를 받아들일 수 있는가

실무적으로는 이렇게 나누는 편이 좋다.

- 세그먼트 pruning: 시간, partition, routing
- row/column pruning: inverted, range, bloom 등
- aggregate acceleration: star-tree

이 세 층을 섞지 않아야 설계가 선명해진다.

---

## 핵심 개념 4: Star-Tree는 “모든 대시보드를 빠르게 하는 마법”이 아니라 “정형 집계를 위한 저장 비용 전환”이다

Star-tree는 Pinot를 공부할 때 가장 매력적으로 보이는 기능 중 하나다.

실제로도 강력하다.

하지만 이해를 잘못하면 가장 먼저 과투자하기 쉬운 기능이기도 하다.

### star-tree를 한 문장으로 정리하면

특정 차원 조합과 집계 함수에 대해,

세그먼트 내부에 부분 집계 구조를 미리 만들어 두는 것이다.

즉 아래 같은 쿼리가 반복될 때 특히 강하다.

- 최근 1시간, tenant별 총 클릭 수
- 최근 24시간, campaign + country 기준 매출 합계
- 최근 7일, app_version별 에러 건수
- 특정 organization의 endpoint별 p95 latency 추세

이런 질의는 사용자마다 값은 달라도 모양은 비슷하다.

Pinot는 이 반복성을 이용해,

raw data scan의 양을 줄이는 쪽으로 성능을 얻는다.

### 언제 star-tree가 특히 잘 맞는가

1. 차원 조합이 어느 정도 고정돼 있다
2. 집계 함수가 count/sum/min/max 같은 전형적 형태다
3. 쿼리가 대시보드/모니터링/API에서 반복된다
4. raw scan 비용이 병목으로 드러난다
5. 약간의 저장/ingestion 비용 증가를 감수할 수 있다

예를 들어 광고 운영 대시보드는 대표적이다.

- time range
- advertiser_id
- campaign_id
- country
- device_type
- metric sum/count

같은 패턴이 하루에도 수없이 반복된다.

이런 곳에서는 star-tree가 매우 잘 맞는다.

### 언제 star-tree가 애매한가

- 질의 차원 조합이 너무 다양하다
- ad-hoc 탐색이 대부분이다
- distinct count나 복잡한 함수가 중심이다
- 차원 cardinality가 너무 높고 조합이 많다
- 어떤 쿼리를 가속해야 하는지 팀이 명확히 모르고 있다

이 경우 star-tree는 “뭔가 빠를 것 같은 인덱스”로 도입됐다가,

저장 비용과 운영 복잡도만 올릴 수 있다.

### star-tree 설계에서 가장 중요한 기준

#### 1) 상위 5~10개 질의 패턴을 먼저 고정한다

star-tree는 데이터 전체를 위해 만드는 것이 아니라,

자주 반복되는 상위 질의 집합을 위해 만든다.

즉 먼저 해야 할 일은 인덱스 생성이 아니라 workload 분석이다.

- 가장 많이 호출되는 API는 무엇인가
- tail latency가 높은 질의는 무엇인가
- 차원 조합이 비슷한 질의가 얼마나 반복되는가
- 그 질의의 SLA가 왜 중요한가

#### 2) 차원 split 순서를 비즈니스 패턴으로 정한다

차원을 많이 넣는 것보다,

앞쪽에 어떤 축을 둘지 더 중요하다.

- tenant가 거의 항상 들어가면 tenant 우선
- 시간 버킷 집계가 핵심이면 coarse time bucket을 우선
- country/device는 후순위일 수 있다

#### 3) 모든 metric을 넣지 않는다

star-tree는 저장 비용을 먹는다.

따라서 자주 쓰는 집계 함수만 넣는 편이 좋다.

- COUNT
- SUM(revenue)
- MAX(latency)
- MIN(latency)

같이 핵심 metric만 먼저 넣고,

나머지는 raw path로 남기는 식이 현실적이다.

#### 4) “빨라지는가”보다 “어떤 질의가 확실히 빨라지는가”를 봐야 한다

운영 관점에서는 평균 응답 시간보다,

- 특정 API p95가 안정됐는가
- 특정 대시보드 로딩이 체감상 해결됐는가
- 브로커 fan-out 후 server scan 시간이 줄었는가

가 더 중요하다.

### star-tree는 캐시와도 다르다

캐시는 질의 결과 단위로 저장하는 경우가 많다.

star-tree는 결과가 아니라 집계 경로를 가속한다.

그래서 장점이 있다.

- 값이 달라도 구조가 같으면 이득을 본다
- 캐시 키 폭발이 덜하다
- 시간 범위만 살짝 바뀌는 질의에도 효과가 남을 수 있다

하지만 한계도 있다.

- 쿼리 모양이 다르면 효과가 약하다
- 임의 SQL 전반을 가속하지는 못한다

즉 star-tree는 cache replacement가 아니라,

**반복 집계용 물리 설계**다.

---

## 핵심 개념 5: Upsert는 로그 저장 전략이 아니라 “최신 상태 뷰”를 만들기 위한 설계다

Pinot를 논할 때 upsert는 자주 오해된다.

“업데이트도 되네” 정도로 이해하면 절반만 맞다.

Pinot의 upsert는 OLTP의 row update와는 다르다.

실무에서 더 정확한 의미는 이렇다.

> 동일 primary key에 대해 가장 최신 레코드를 query path에서 유효 상태로 간주하게 만드는 최신 상태 유지 전략.

즉 엔터티의 current view를 실시간 분석용으로 보여주고 싶을 때 강력하다.

예를 들어,

- 주문의 현재 상태
- 광고 캠페인의 최신 budget/status
- 디바이스의 마지막 heartbeat 상태
- 사용자 프로필의 최신 속성 스냅샷

같은 문제에서는 upsert가 잘 맞을 수 있다.

### upsert가 잘 맞는 상황

- primary key가 명확하다
- 최신 버전 비교 기준 컬럼이 있다
- “가장 최근 상태” 조회가 중요하다
- append-only raw 로그와 current state를 분리해 생각할 수 있다
- 메모리 비용과 관리 복잡도를 감당할 수 있다

### upsert가 위험한 상황

- 사실은 모든 변경 이력을 보존해야 한다
- late event, out-of-order event가 자주 발생한다
- primary key 설계가 불안정하다
- 비교 컬럼 기준이 명확하지 않다
- 최신 상태와 집계를 한 테이블 의미로 동시에 해결하려 한다

이런 상황에서 upsert는 독이 되기 쉽다.

왜냐하면 raw event store와 current state store는 요구사항이 다르기 때문이다.

### raw 로그와 upsert 테이블을 분리하는 감각

많은 팀이 처음에는 테이블을 줄이고 싶어 한다.

그래서 하나의 테이블에,

- 이벤트 이력도 남기고
- 최신 상태도 보고
- 집계도 하고
- 장애 분석도 하고 싶어 한다.

거의 항상 오래 못 간다.

실무에서는 아래처럼 나누는 편이 훨씬 안전하다.

1. **append-only event table**
   - 모든 원본 이벤트 보존
   - 재계산과 감사에 유리
   - 집계용 기반 데이터

2. **upsert current-state table**
   - 최신 상태 조회 전용
   - 운영 화면/API에 적합
   - 낮은 지연의 entity status 응답용

3. 필요하다면 **rollup table**
   - 반복 집계를 위한 사전 요약

이렇게 나누면 semantics가 선명해진다.

### upsert의 실제 비용을 과소평가하면 안 된다

upsert는 편리하지만 공짜가 아니다.

- primary key 관리 비용이 있다
- 최신성 비교를 위한 컬럼 기준이 필요하다
- out-of-order 이벤트 처리 전략이 필요하다
- tombstone 또는 delete semantics를 설계해야 한다
- 메모리 사용량이 커질 수 있다
- compaction 및 segment replacement 정책이 중요해진다

즉 upsert는 쓰기 편의가 아니라,

**최신 상태 유지라는 비즈니스 요구를 메모리와 운영 복잡도로 사오는 선택**에 가깝다.

### partial update에 대한 태도

부분 업데이트가 가능하다고 해도,

처음부터 복잡하게 쓰기보다 전체 레코드 최신 상태를 다시 만드는 방식이 더 단순한 경우가 많다.

왜냐하면 partial update는 아래를 함께 고민해야 하기 때문이다.

- null 처리 규칙
- 기존 값 유지/덮어쓰기 정책
- 컬럼별 merge 전략
- 늦게 도착한 이벤트의 우선순위

업무 의미가 강하게 얽힌다.

복잡한 부분 업데이트는 데이터 제품 팀이 의미를 명확히 설명할 수 있을 때만 쓰는 편이 안전하다.

---

## 핵심 개념 6: Hybrid Table은 “실시간도 보고 과거도 보자”가 아니라 “freshness와 correctness 경계를 분리하자”는 설계다

Pinot가 실무에서 매력적인 이유 중 하나는 hybrid table 전략이다.

간단히 말하면,

- real-time table로 최근 데이터를 빠르게 ingest하고
- offline table로 안정적이고 최적화된 세그먼트를 관리하며
- query 시 둘을 함께 읽어 하나의 논리 뷰처럼 제공한다.

이 구조가 중요한 이유는 freshness와 correctness가 종종 충돌하기 때문이다.

### real-time만으로 가면 생기는 문제

- late event 보정이 어렵다
- 재처리와 backfill 운영이 까다롭다
- 세그먼트 수와 ingestion 비용이 누적된다
- 장기 보관 전략이 거칠어질 수 있다

### offline만으로 가면 생기는 문제

- 최신 데이터 반영이 느리다
- 운영 화면/알림/대시보드 요구를 못 맞춘다
- near-real-time API 계층을 따로 만들게 된다

### hybrid가 주는 운영상의 장점

- 최근 몇 시간은 real-time으로 빠르게 본다
- 전일 또는 검증 완료 구간은 offline으로 안정적으로 본다
- backfill이나 정정 데이터는 offline rebuild로 반영한다
- 실시간성과 정합성을 한 테이블 의미에 우겨 넣지 않아도 된다

즉 hybrid의 본질은 convenience가 아니라 경계 설정이다.

### freshness window를 명확히 정의해야 한다

운영에서 가장 중요한 질문은 이것이다.

- 최근 몇 분/몇 시간 구간은 provisional data인가
- 언제 offline 쪽이 source of truth가 되는가
- real-time과 offline이 겹치는 window는 어떻게 정리하는가
- late data가 들어오면 어느 계층에서 정정하는가

이 답이 없으면 hybrid는 편리한 기능이 아니라 이중 진실의 시작이 된다.

### 실무적으로 자주 쓰는 구조

- 최근 6시간 또는 24시간은 real-time table 위주
- 하루 단위 batch/stream compaction 후 offline segment 생성
- 일정 지연 이후 offline이 authoritative source가 됨
- API는 freshness 설명을 붙이거나, 특정 화면은 provisional badge를 둠

이런 구조를 잡으면,

데이터팀과 서비스팀 모두 기대치를 맞추기 쉬워진다.

---

## 실무 예시 1: 광고 운영 대시보드에서 Pinot를 어떻게 배치해야 하는가

상황을 가정해 보자.

광고 플랫폼이 있고,

- 노출, 클릭, 전환 이벤트가 Kafka로 들어온다
- 운영 대시보드에서 최근 5분, 1시간, 24시간 지표를 본다
- 필터는 advertiser_id, campaign_id, country, device_type, placement 정도다
- 주요 metric은 impression, click, conversion, spend, revenue다
- 대시보드 응답 SLA는 500ms~1.5초 수준이다

이 문제는 전형적인 Pinot 후보군이다.

### 왜 warehouse 단독으로 버티기 어려운가

- 최신 데이터 반영 주기를 짧게 가져가면 적재 비용이 올라간다
- 반복되는 집계 질의를 매번 큰 테이블에서 계산한다
- API 호출량이 늘면 BI용 엔진과 serving 요구가 충돌한다
- 사용자별 필터 조합 캐시가 빠르게 폭증한다

### Pinot 테이블 설계의 기본 방향

1. 원본 이벤트 raw table을 real-time으로 수집한다
2. 시간 + advertiser 또는 campaign 축으로 pruning이 잘 되게 설계한다
3. equality filter가 잦은 차원에 inverted index를 둔다
4. 반복 집계가 많은 조합에는 star-tree를 검토한다
5. 정산용 정답은 여전히 warehouse에서 관리한다

### 질의 패턴을 먼저 고정해 보자

가장 많이 호출되는 질의가 아래라고 하자.

- 최근 15분 advertiser 단위 클릭/전환 합계
- 최근 1시간 campaign별 spend top N
- 최근 24시간 country + device 기준 CTR 분포
- 특정 campaign의 minute bucket time series

이 경우 star-tree 후보 차원은 비교적 명확하다.

- advertiser_id
- campaign_id
- country
- device_type
- minute_bucket 또는 hour_bucket

모든 차원을 넣는 게 아니라,

상위 API를 기준으로 split 순서를 정해야 한다.

### 개념 예시 config

```json
{
  "tableName": "ad_events_rt",
  "tableType": "REALTIME",
  "segmentsConfig": {
    "timeColumnName": "event_time",
    "schemaName": "ad_events"
  },
  "indexingConfig": {
    "invertedIndexColumns": [
      "advertiser_id",
      "campaign_id",
      "country",
      "device_type"
    ],
    "rangeIndexColumns": [
      "event_time"
    ],
    "starTreeIndexConfigs": [
      {
        "dimensionsSplitOrder": [
          "advertiser_id",
          "campaign_id",
          "country",
          "device_type",
          "minute_bucket"
        ],
        "functionColumnPairs": [
          "COUNT__*",
          "SUM__spend",
          "SUM__revenue",
          "SUM__click_count",
          "SUM__conversion_count"
        ],
        "maxLeafRecords": 10000
      }
    ]
  }
}
```

실제 운영에서는 이 config보다,

아래 판단이 더 중요하다.

- advertiser_id가 거의 항상 필터에 들어가는가
- minute_bucket을 star-tree 차원으로 둘 만큼 time-series API가 반복되는가
- spend/revenue 집계가 전체 요청의 대부분인가
- distinct user 기반 KPI는 별도 경로가 필요한가

### 이 구조의 장점

- 반복 집계 API가 안정적으로 빨라진다
- 쿼리 결과 캐시 의존이 줄어든다
- 최신 데이터가 수 분 내 반영된다
- tenant/advertiser 기준 noisy neighbor를 줄이기 쉽다

### 이 구조의 트레이드오프

- distinct 계열 지표는 여전히 별도 전략이 필요하다
- star-tree 저장 비용과 ingestion 비용이 증가한다
- 정산/재무 기준 숫자는 warehouse 쪽 authoritative source와 분리해야 한다
- 너무 많은 dimension을 넣으면 오히려 설계가 망가진다

### 실무 팁

광고 대시보드에서 가장 흔한 실패는 “모든 지표를 하나의 테이블로 해결하려는 욕심”이다.

실제로는 아래처럼 나누는 것이 낫다.

- raw event Pinot table
- high-traffic API용 rollup/star-tree 최적화 table
- finance-grade warehouse mart

이렇게 나눠야 제품팀, 운영팀, 데이터팀이 같은 숫자를 다르게 기대하는 문제를 줄일 수 있다.

---

## 실무 예시 2: 주문 상태 API에 Upsert를 적용할 때 무엇을 분리해야 하는가

이번에는 이커머스나 배달 서비스 상황을 보자.

주문 상태는 계속 바뀐다.

- CREATED
- PAID
- PREPARING
- SHIPPED
- DELIVERED
- CANCELED

운영자는 “지금 현재 상태”를 빠르게 보고 싶다.

반면 데이터 분석가는 상태 변경 이력을 모두 보존하고 싶다.

이 두 요구를 하나의 테이블로 동시에 풀려고 하면 거의 항상 의미가 충돌한다.

### 권장 구조

1. **order_events_raw**
   - 주문 상태 변경 이력을 append-only로 저장
   - 감사, 재처리, 퍼널 분석, SLA 계산에 사용

2. **order_current_state**
   - `order_id` 기준 upsert
   - 최신 상태 API와 운영 화면에 사용

3. 필요하면 **order_status_rollup**
   - 분 단위/시간 단위 상태별 건수 집계
   - 대시보드 가속용

### 왜 이렇게 나누는가

raw table의 질문은 이렇다.

- 이 주문은 어떤 순서로 상태가 바뀌었는가
- 어느 단계에서 지연이 생겼는가
- 특정 구간 재처리가 가능한가

upsert table의 질문은 이렇다.

- 지금 이 주문 상태는 무엇인가
- 현재 PREPARING 상태 주문은 몇 개인가
- 특정 매장의 현재 미완료 주문 수는 몇 개인가

질문 자체가 다르다.

그래서 저장 semantics도 달라야 한다.

### upsert config를 고민할 때의 핵심 질문

- `order_id`가 진짜 stable primary key인가
- 비교 기준은 `event_version`인가, `updated_at`인가
- 늦게 도착한 이벤트가 더 옛 상태를 덮어쓰지 않게 할 장치가 있는가
- 취소/삭제 같은 tombstone semantics는 어떻게 표현할 것인가
- current state table을 몇 일 보관할 것인가, 전체를 계속 유지할 것인가

### 자주 하는 실수

#### 1) timestamp만 믿고 version semantics를 무시한다

분산 시스템에서는 out-of-order event가 흔하다.

단순 timestamp 비교만으로는 더 오래된 상태가 늦게 와서 현재 상태를 덮어쓸 수 있다.

가능하면 version 또는 sequence 의미를 더 선호해야 한다.

#### 2) current state 집계를 raw truth처럼 사용한다

current state 테이블은 “지금 상태”에는 좋지만,

과거 시점 재구성이나 상태 전이 분석에는 충분하지 않다.

#### 3) delete 의미를 설계하지 않는다

주문 취소, 엔터티 비활성화, GDPR 삭제 같은 사건이 생기면,

단순 upsert만으로는 테이블 의미가 흐려질 수 있다.

### 운영상 얻는 이점

이 구조를 잘 잡으면,

- 운영 화면의 current status 응답이 빨라지고
- 최근 상태 기준 집계도 빠르게 만들 수 있으며
- raw event는 별도 보존돼 재처리와 감사가 가능하고
- 서비스 API와 데이터 분석의 요구를 서로 덜 해친다.

즉 upsert는 update 기능이 아니라,

**최신 상태 뷰를 명시적으로 분리하는 설계 선택**으로 보는 편이 맞다.

---

## 실무 예시 3: 멀티테넌트 SaaS 분석 API에서 tenant isolation을 어떻게 설계할까

멀티테넌트 SaaS에서는 성능보다 더 어려운 문제가 하나 있다.

바로 noisy neighbor다.

일부 대형 고객이 전체 질의를 흔들기 시작하면,

소형 고객도 같이 느려진다.

이때 Pinot는 단순 성능 엔진이 아니라 isolation 도구가 될 수 있다.

### 상황

- 모든 고객이 같은 분석 API를 쓴다
- 거의 모든 질의가 `tenant_id`를 포함한다
- premium 고객은 대시보드 새로고침 빈도가 높다
- 최근 7일, 최근 24시간, 최근 1시간 기준 집계가 많다
- 전체 데이터를 합치는 전역 리포트는 상대적으로 적다

### 설계 포인트

#### 1) tenant_id를 질의 계약에 강제한다

API 계층에서 tenant filter를 반드시 넣도록 설계해야 한다.

질의마다 tenant가 빠질 수 있으면 partitioning과 routing 설계 이점이 크게 줄어든다.

#### 2) tenant 기반 partitioning 또는 dedicated table 전략을 검토한다

모든 tenant를 동일하게 취급하지 않아도 된다.

예를 들어,

- long tail 고객은 shared table
- 초대형 고객은 dedicated table 또는 별도 cluster

처럼 나누면 tail latency가 안정될 수 있다.

#### 3) 시간 범위를 기본 파라미터로 강제한다

tenant filter만으로는 부족하다.

최근 30분, 24시간, 7일처럼 명시적 시간 범위를 강제해야 세그먼트 pruning 효과가 살아난다.

#### 4) 전역 leaderboard나 cross-tenant 집계는 별도 경로로 분리한다

멀티테넌트 isolation 전략과 전역 집계 요구를 같은 질의 레이어에 섞으면 설계가 흔들린다.

### API 설계와 함께 봐야 할 체크

- free-form SQL을 허용할 것인가
- 허용한다면 tenant filter injection과 guardrail이 있는가
- group by cardinality 제한이 있는가
- top N만 허용할 것인가
- 결과 row 제한이 있는가
- time window 상한이 있는가

### 실제 효과

이 전략을 쓰면,

- tenant별 조회 SLA 예측 가능성이 높아지고
- 특정 고객의 스파이크가 전체 시스템에 번지는 범위를 줄일 수 있으며
- query planner보다 API contract가 성능을 더 많이 좌우하게 된다.

이 점이 중요하다.

Pinot 성능 문제의 일부는 infra보다 제품 API 설계에서 만들어진다.

즉 테이블 설계만으로는 절반이다.

---

## 실무 예시 4: Late Event와 Backfill이 많은 환경에서 Hybrid를 어떻게 운영할까

실시간 이벤트 시스템은 거의 항상 지연 데이터를 만난다.

- 모바일 앱 오프라인 전송
- 네트워크 지연
- 업스트림 버그 수정 후 재전송
- CDC 지연
- 집계 오류 정정

이런 환경에서 real-time ingestion만 믿고 가면 언젠가 정합성 비용이 폭발한다.

### 나쁜 구조

- 모든 것을 real-time table 하나에 넣는다
- 늦게 온 이벤트도 거기서만 처리한다
- 재처리와 보정도 같은 경로로 해결하려 한다
- 어떤 데이터가 provisional인지 nobody knows

이 구조는 처음에는 간단하지만,

시간이 지나면 질문이 꼬인다.

- 어제 숫자가 왜 오늘 바뀌었지
- 늦게 도착한 이벤트가 어디까지 반영됐지
- 지난주 데이터를 다시 밀어 넣었는데 중복은 없나
- 실시간 집계와 백오피스 숫자가 왜 다르지

### 더 나은 구조

1. 최근 구간은 real-time table로 서빙한다
2. 검증 완료 구간은 offline table로 수렴시킨다
3. late data는 offline 재빌드 또는 정정 파이프라인에서 흡수한다
4. UI/API는 freshness 경계를 명시한다

### 예시 운영 정책

- 최근 6시간 데이터는 real-time dominant
- 6시간 이전 데이터는 nightly batch를 거친 offline dominant
- late event는 최대 3일까지 offline rebuild로 반영
- 운영 대시보드는 provisional badge를 최근 구간에 표시
- 재무/정산 숫자는 offline authoritative mart만 사용

### 왜 이 정책이 중요한가

이런 기준이 있어야,

- 제품팀이 숫자 차이를 이해하고
- 운영팀이 장애 상황에서 어느 구간을 믿어야 하는지 알며
- 데이터팀이 backfill과 정정의 범위를 명확히 제어할 수 있다.

### Pinot 혼자 다 해결하려고 하지 말자

late event와 correctness 문제는 Pinot 기능만으로 끝나지 않는다.

- Kafka 재처리 정책
- warehouse backfill 파이프라인
- 원천 데이터의 idempotency
- 이벤트 버전 정책
- downstream consumer 기대치

가 같이 맞물려야 한다.

즉 hybrid는 기능이 아니라 조직 간 계약이다.

---

## 트레이드오프 1: 세그먼트를 더 잘게 쪼개면 최신성은 좋아지지만 fan-out과 운영 비용이 증가한다

실시간 분석 시스템에서 가장 흔한 유혹은 “더 빨리 보이게 하자”다.

그래서 flush를 더 자주 하고,

작은 세그먼트를 많이 만든다.

얻는 것:

- 최신 데이터 노출 지연 감소
- 이벤트 반영 체감 개선
- 짧은 time window 질의에 유리할 수 있음

잃는 것:

- 브로커 fan-out 증가
- 세그먼트 메타데이터 증가
- 쿼리 tail latency 변동성 증가
- 운영자가 튜닝해야 할 파라미터 증가
- 장기적으로 compaction/merge 운영 부담 증가

즉 freshness는 공짜가 아니다.

제품이 요구하는 최소 freshness와 infra가 감당 가능한 세그먼트 운영 사이 타협이 필요하다.

---

## 트레이드오프 2: 강한 partitioning은 pruning을 돕지만 skew와 재분배 비용을 키울 수 있다

partitioning을 공격적으로 잡으면,

특정 질의는 엄청 빨라질 수 있다.

특히 tenant 또는 account 기반 질의가 거의 전부라면 체감 이득이 크다.

하지만 대가도 있다.

- 핫 키에 데이터가 집중될 수 있다
- 특정 partition 서버만 과열될 수 있다
- tenant 성장 패턴이 바뀌면 재설계가 필요하다
- 전역 집계 경로와 충돌할 수 있다
- 운영자가 shard/partition topology를 이해해야 한다

즉 “partition을 더 많이 하자”가 아니라,

**누구를 위해 pruning을 최적화하는지**를 분명히 해야 한다.

---

## 트레이드오프 3: Star-Tree는 반복 집계에 매우 강하지만 ad-hoc 자유도와 저장 비용을 희생한다

star-tree는 상위 몇 개 API를 살리는 데 아주 좋다.

하지만 아래를 받아들여야 한다.

- 모든 질의가 빨라지지 않는다
- 설계 시점에 workload를 알아야 한다
- 저장/ingestion 비용이 증가한다
- 쿼리 패턴이 바뀌면 재설계가 필요하다

즉 star-tree는 유연성보다 예측 가능성을 택하는 선택이다.

서비스형 대시보드에는 잘 맞지만,

“유저가 뭘 물어볼지 모르겠다”는 탐색형 BI 전체를 대신하진 않는다.

---

## 트레이드오프 4: Upsert는 최신 상태 조회를 쉽게 만들지만 메모리와 semantics 복잡도를 키운다

upsert는 보기엔 단순하다.

같은 키면 최신 것만 살아남는다.

하지만 실무 의미는 결코 단순하지 않다.

- 최신을 무엇으로 정의하는가
- 지연 이벤트가 오면 어떻게 하는가
- delete는 어떻게 표현하는가
- 이력을 잃어도 되는가
- current state 집계와 raw event 집계를 어떻게 분리하는가

즉 upsert는 속도 기능이 아니라 데이터 의미 기능이다.

모델 의미가 불분명하면 성능보다 정합성 문제가 먼저 터진다.

---

## 트레이드오프 5: Pinot를 서빙 계층으로 쓰면 API는 빨라지지만 데이터 아키텍처는 더 명확히 분리해야 한다

Pinot를 잘 도입하면 많은 것이 좋아진다.

- 운영 대시보드가 빨라진다
- near-real-time API가 단순해진다
- 캐시 폭발이 줄어든다
- warehouse에 직접 붙던 serving 트래픽이 분리된다

하지만 동시에 요구도 생긴다.

- warehouse와 Pinot의 책임 경계를 문서화해야 한다
- 숫자 차이가 날 수 있는 freshness window를 설명해야 한다
- raw, current state, rollup을 분리해야 한다
- API contract를 더 엄격하게 가져가야 한다

즉 성능을 얻는 대신,

**데이터 제품의 의미 경계를 더 분명히 설계해야 한다.**

---

## 흔한 실수 1: Pinot를 warehouse 대체재로 바로 생각한다

Pinot는 강력하지만 warehouse와 목적이 다르다.

복잡한 대형 join, 광범위한 ad-hoc SQL, 정확한 재계산 중심의 업무를 Pinot 하나로 몰아넣으면,

결국 성능도 의미도 흐려진다.

Pinot는 serving path를 줄이는 도구로 보는 편이 안전하다.

---

## 흔한 실수 2: segment 문제를 쿼리 문법 문제로만 본다

질의가 느리면 SQL 튜닝부터 떠올리기 쉽다.

하지만 Pinot에서는,

- fan-out된 세그먼트 수
- segment 크기 편차
- consuming segment 비중
- time pruning 효율
- routing skew

가 더 큰 원인인 경우가 많다.

느린 쿼리는 먼저 어떤 세그먼트를 얼마나 읽는지부터 봐야 한다.

---

## 흔한 실수 3: partition key를 “자주 보이는 컬럼” 기준으로만 고른다

자주 보인다고 좋은 partition key는 아니다.

- 질의에서 항상 필터되는가
- 값 분포가 너무 치우치지 않는가
- 운영상 이 partition을 이해하고 유지할 수 있는가

를 함께 봐야 한다.

그렇지 않으면 pruning보다 skew가 더 커진다.

---

## 흔한 실수 4: star-tree를 많이 만들수록 좋다고 생각한다

star-tree는 강력하지만 비싸다.

상위 질의 패턴이 명확하지 않은 상태에서 star-tree를 늘리면,

- 저장 비용 증가
- ingestion 비용 증가
- 운영 복잡도 증가
- 실제 체감 성능 이득 미미

라는 결과가 나오기 쉽다.

star-tree는 많이 만드는 기능이 아니라,

가장 비싼 질의 몇 개를 겨냥해 만드는 기능이다.

---

## 흔한 실수 5: upsert 하나로 이력 보존과 최신 상태 조회를 동시에 해결하려 한다

이건 거의 항상 문제를 만든다.

최신 상태가 필요하면 current state table을 만들고,

이력이 필요하면 raw event를 따로 보존해야 한다.

한 테이블에 두 의미를 넣으면,

나중에 데이터 제품, 감사, 장애 분석이 모두 꼬인다.

---

## 흔한 실수 6: API에 guardrail이 없어서 Pinot의 장점을 스스로 지운다

Pinot 테이블을 아무리 잘 설계해도,

애플리케이션이 아래를 허용하면 금방 무너진다.

- 무제한 시간 범위
- tenant 없는 전역 질의
- 초고카디널리티 group by 남발
- row limit 없는 상세 탐색
- 자유 SQL 그대로 실행

즉 serving DB에는 serving 계약이 필요하다.

성능 문제의 상당수는 인프라가 아니라 API 정책 문제다.

---

## 흔한 실수 7: freshness와 correctness의 경계를 문서화하지 않는다

실시간 분석 시스템에서는 숫자가 약간 바뀌는 것이 자연스러울 수 있다.

문제는 그 사실을 팀이 모르고 있을 때다.

- 최근 30분은 provisional인가
- 하루 마감 후 숫자가 확정되는가
- backfill 후 지난주 숫자가 바뀔 수 있는가

이런 정의가 없으면 제품팀과 운영팀은 시스템을 불신하게 된다.

---

## 흔한 실수 8: Pinot에 너무 많은 역할을 얹는다

Pinot는 잘 쓰면 아주 유용하다.

하지만 아래를 동시에 모두 기대하면 무리다.

- warehouse
- OLTP
- search engine
- cache replacement for every query
- master data store

좋은 도입은 역할을 줄이는 방향이다.

나쁜 도입은 역할을 늘리는 방향이다.

---

## 설계 체크리스트: Pinot 도입 전에 반드시 확인할 것

### 1) 질의 패턴이 정말 반복적인가

- 상위 API 10개가 전체 트래픽 대부분을 차지하는가
- time range + dimension filter + aggregate 형태가 주류인가
- ad-hoc 자유 SQL보다 정형 질의가 많은가

### 2) freshness 요구를 숫자로 설명할 수 있는가

- 5초 이내인가
- 1분 이내인가
- 15분 이내여도 충분한가
- 이 freshness를 위해 segment fan-out 비용을 감당할 가치가 있는가

### 3) serving path와 truth path를 분리할 준비가 되었는가

- Pinot는 서빙용
- warehouse는 정답/재계산용
- raw와 rollup, current state 의미를 분리할 수 있는가

### 4) partition key를 workload 기준으로 설명할 수 있는가

- 왜 tenant인가
- 왜 campaign인가
- 왜 시간만으로 충분하지 않은가
- 왜 이 partition은 pruning에 실제 도움이 되는가

### 5) 어떤 인덱스를 왜 붙이는지 설명할 수 있는가

- inverted index 후보 컬럼은 무엇인가
- range index가 실제로 필요한가
- bloom filter는 어떤 point lookup을 위한 것인가
- star-tree는 어떤 상위 질의를 위한 것인가

### 6) upsert semantics가 명확한가

- primary key는 무엇인가
- latest 비교 기준은 무엇인가
- late event는 어떻게 처리하는가
- tombstone/delete를 어떻게 표현하는가

### 7) hybrid window가 정의되어 있는가

- real-time이 authoritative한 구간은 어디까지인가
- offline이 authoritative한 시점은 언제인가
- 겹치는 구간이 있을 때 어떤 쪽을 우선하는가

### 8) API guardrail이 준비되어 있는가

- 시간 범위 상한
- tenant filter 강제
- group by 제한
- top N 제한
- row limit
- timeout 정책

### 9) 관측 지표가 준비되어 있는가

- broker p95/p99 latency
- server scan time
- segment count growth
- ingestion lag
- consuming segment 수
- partition skew
- query fan-out

### 10) 운영 조직 간 기대치가 맞춰져 있는가

- 제품팀은 provisional data를 이해하는가
- 운영팀은 freshness/correctness 경계를 아는가
- 데이터팀은 backfill 책임 범위를 아는가

이 질문에 답이 흐리면,

Pinot 도입은 기술 선택보다 조직 선택에서 먼저 흔들릴 가능성이 크다.

---

## 운영 체크리스트: 이미 돌고 있는 Pinot가 느려질 때 우선 보는 순서

### 1) 느린 질의가 어떤 세그먼트를 몇 개 읽는지 본다

- fan-out이 갑자기 늘었는가
- time pruning이 깨졌는가
- 특정 partition이 과도하게 읽히는가

### 2) broker와 server 중 어디가 병목인지 구분한다

- broker merge가 느린가
- server scan이 느린가
- network shuffle/serialization 비용이 큰가

### 3) consuming segment 비중과 flush 전략을 점검한다

- 실시간 최신성 요구 때문에 세그먼트가 너무 잘게 쪼개졌는가
- 반대로 consuming segment가 너무 오래 살아 메모리/질의 편차를 만드는가

### 4) 특정 tenant 또는 key의 skew를 확인한다

- premium 고객 한 곳이 대부분 부하를 만들고 있는가
- 라우팅 상 특정 서버에 집중이 생겼는가

### 5) 인덱스가 실제 workload와 맞는지 다시 본다

- 자주 쓰는 필터에 inverted index가 빠졌는가
- 안 쓰는 컬럼 인덱스만 많아졌는가
- star-tree가 기대한 쿼리를 실제로 가속하는가

### 6) API 계층에서 wide query가 유입되는지 점검한다

- 갑자기 전역 범위 질의가 늘었는가
- limit 없는 exploratory query가 서비스 트래픽으로 들어오는가
- 새 기능이 기존 guardrail을 우회했는가

### 7) hybrid/late data 정책이 깨졌는지 확인한다

- offline build 지연으로 real-time 구간이 과도하게 길어졌는가
- backfill이 실시간 질의와 충돌하고 있는가
- 데이터 중복 또는 누락 window가 생겼는가

### 8) 세그먼트 라이프사이클을 장기 추세로 본다

하루 평균은 괜찮아도,

몇 주 단위로 보면 다음이 누적될 수 있다.

- 세그먼트 수 증가
- partition imbalance
- storage 증가
- compaction 지연
- star-tree rebuild 비용 증가

Pinot 운영은 단발성 쿼리 튜닝보다,

세그먼트 라이프사이클을 읽는 능력이 더 중요하다.

---

## 도입 판단을 더 선명하게 만드는 질문 12개

아래 질문에 답해 보면 Pinot가 맞는지 훨씬 빨리 보인다.

1. 사용자는 데이터를 몇 초 안에 보고 싶어 하는가
2. 그 freshness가 정말 비즈니스 가치를 만드는가
3. 질의 패턴은 정형적인가, 탐색적인가
4. 같은 차원 조합이 반복되는가
5. 시간 필터가 사실상 항상 존재하는가
6. tenant/account 같은 강한 access dimension이 있는가
7. 정답 시스템과 서빙 시스템을 분리할 수 있는가
8. current state와 event history를 분리할 수 있는가
9. API guardrail을 넣을 수 있는가
10. ingestion 비용 증가를 받아들일 수 있는가
11. backfill과 late data 운영 프로세스가 있는가
12. 운영자가 세그먼트와 질의 fan-out을 이해할 수 있는가

대체로,

- “반복 집계 + 낮은 지연 + 명확한 질의 축 + serving 분리 가능”이면 Pinot가 빛나고
- “자유 분석 + 복잡 join + 정답 재계산 중심”이면 warehouse나 다른 경로가 더 자연스럽다.

---

## 실무 적용 순서: 처음부터 크게 가지 말고 한 경로를 확실히 살리는 편이 낫다

Pinot 도입 초기에 가장 좋은 전략은,

가장 고통이 큰 질의 경로 하나를 정확히 살리는 것이다.

예를 들어,

- 운영 대시보드의 최근 1시간 광고 성과 API
- 특정 tenant의 실시간 오류율 차트
- 주문 current status 카운트 API

같이 business value가 뚜렷한 경로를 고른다.

그리고 아래 순서로 간다.

1. 상위 질의 패턴을 5~10개 정의한다
2. 시간 범위와 필수 필터를 API에서 강제한다
3. 최소한의 인덱스와 partition으로 시작한다
4. 병목을 측정한 뒤 star-tree를 추가한다
5. raw, rollup, current state를 필요 시 분리한다
6. hybrid/offline 정정 경계를 문서화한다

이 순서가 좋은 이유는,

Pinot의 진짜 가치는 “빨라 보이는 기능 수”가 아니라

**한 경로를 안정적으로 낮은 지연으로 만들고, 그 이유를 팀이 설명할 수 있는 상태**에 있기 때문이다.

---

## 한 줄 정리

Apache Pinot는 실시간 분석 DB라는 이름보다, 반복되는 초저지연 집계 질의를 세그먼트 라우팅, partition pruning, star-tree 가속, upsert 기반 최신 상태 분리로 안정적으로 서빙하게 해주는 분석 서빙 계층으로 이해할 때 가장 잘 쓸 수 있다.
