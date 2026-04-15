---
layout: post
title: "dbt 실전: Incremental Model, Snapshot, Test, Lineage로 분석 테이블을 운영 가능한 상태로 만드는 법"
date: 2026-04-11 11:40:00 +0900
categories: [data-infra]
tags: [study, data-infra, dbt, analytics-engineering, incremental-model, snapshot, test, lineage, warehouse]
permalink: /data-infra/2026/04/11/study-dbt-incremental-models-snapshots-tests-lineage.html
---

## 배경: SQL은 많은데, 왜 분석 테이블은 여전히 자주 틀릴까?

데이터 조직이 어느 정도 커지면 비슷한 장면이 반복된다.

- 원천 데이터는 쌓이는데 어떤 쿼리가 진실인지 사람마다 다르게 말한다
- 대시보드 숫자가 어제와 오늘 다르고, 이유를 찾는 데 반나절이 걸린다
- 배치가 한 번 실패하면 어떤 테이블부터 다시 돌려야 하는지 파악하기 어렵다
- 데이터 모델은 늘어나는데, 어느 테이블이 어떤 소스를 믿고 있는지 lineage가 흐릿하다
- 매번 SQL 파일은 추가되지만 품질 테스트와 문서화는 뒤로 밀린다
- 느려진 모델을 incremental로 바꾸고 싶지만, late data와 중복 처리 때문에 쉽게 손대지 못한다

이 단계에서 팀이 흔히 하는 착각은 "dbt는 SQL 템플릿 도구"라는 것이다. 물론 dbt는 SQL을 더 잘 쓰게 해주는 도구가 맞다. 하지만 실무에서의 가치는 템플릿 자체보다 훨씬 크다.

> dbt의 본질은 SQL을 실행하는 편의 기능이 아니라, 데이터 변환을 **모델, 계약, 테스트, 의존성, 배포 단위**로 다루게 해주는 운영 레이어에 있다.

특히 중급 이상 개발자에게 중요한 질문은 아래다.

- dbt 모델을 어디까지 쪼개고, 어디서 합쳐야 유지보수가 쉬운가?
- incremental model은 언제 유리하고, 언제 오히려 정합성 사고를 키우는가?
- snapshot은 단순 이력 보관이 아니라 어떤 업무 문제를 해결하는가?
- schema test와 data test는 배포 게이트로 어떻게 연결해야 하는가?
- lineage는 보기 좋은 그래프가 아니라 실제 운영에서 어떤 판단을 도와야 하는가?
- Airflow, Spark, CDC, 웨어하우스 테이블 전략과 dbt는 어떻게 역할을 나눠야 하는가?

오늘 글은 dbt 문법 입문이 아니다. **Incremental Model, Snapshot, Test, Lineage를 중심으로 분석 테이블을 오래 운영 가능한 상태로 만드는 기준**을 정리한다.

핵심은 여섯 가지다.

1. dbt는 SQL 모음이 아니라 **변환 계약을 명시하는 프레임워크**다
2. incremental은 성능 최적화 기능이면서 동시에 **정합성 위험을 관리하는 설계 선택**이다
3. snapshot은 단순 백업이 아니라 **느리게 변하는 차원과 기준 시점 추적**을 위한 도구다
4. test는 품질 보조 장치가 아니라 **배포 전후 신뢰도 게이트**다
5. lineage는 시각화가 아니라 **영향 범위와 복구 순서를 드러내는 운영 지도**다
6. 잘하는 팀은 모델 수가 많은 팀이 아니라, **모델 계층과 운영 규칙이 명확한 팀**이다

---

## 먼저 큰 그림: dbt는 "SQL을 실행한다"보다 "변환의 책임 경계를 정한다"에 가깝다

dbt를 처음 도입할 때는 보통 아래 기대에서 시작한다.

- SQL 파일을 Git으로 관리할 수 있다
- 공통 매크로와 ref를 써서 재사용성을 높일 수 있다
- 문서와 테스트를 같이 둘 수 있다
- CI/CD에 연결할 수 있다

이 기대는 맞다. 하지만 운영 단계에서 더 중요한 것은 dbt가 아래 질문에 답을 강제한다는 점이다.

- 이 모델의 입력은 무엇인가?
- 이 모델의 출력 grain은 무엇인가?
- 이 모델은 테이블인가, 뷰인가, incremental인가?
- 이 컬럼은 null이면 안 되는가?
- 상위 모델은 이 모델을 어떻게 참조하는가?
- 소스 freshness가 깨지면 어디까지 영향을 받는가?

즉 dbt는 SQL을 더 편하게 쓰는 도구가 아니라, **데이터 변환을 소프트웨어처럼 구조화하게 만드는 장치**다.

이 관점이 중요한 이유는 분석 시스템의 실제 장애가 대부분 "쿼리가 틀렸다"보다 아래에서 발생하기 때문이다.

- 같은 의미의 지표가 여러 경로로 계산된다
- 수정 영향 범위를 몰라서 배포를 무서워하게 된다
- 누가 어떤 모델을 신뢰하는지 불분명하다
- 성능 튜닝과 정합성 튜닝이 서로 충돌한다
- 테이블 정의는 있는데 계약이 없다

dbt를 잘 쓰는 팀은 `models/` 디렉터리가 예쁜 팀이 아니라, **모델을 데이터 제품 단위로 사고하는 팀**이다.

---

## 핵심 개념 1: 모델 계층을 먼저 고정해야 incremental과 test가 의미를 가진다

dbt 도입 초기에 가장 흔한 실수는 소스에서 마트까지를 한두 개 대형 모델로 몰아넣는 것이다. 처음에는 빨라 보인다. 하지만 시간이 지나면 변경이 어려워지고 테스트 포인트도 사라진다.

실무에서는 보통 아래 계층을 명시적으로 나누는 편이 낫다.

### 1) staging

원천 스키마를 팀 내부 표준으로 정리하는 계층이다.

- 컬럼명 표준화
- 타입 캐스팅
- 삭제 플래그 정리
- JSON 필드 펼치기 최소화
- 원천 시스템 이상치 보정 최소화

핵심은 **비즈니스 로직을 많이 넣지 않는 것**이다. staging은 원천을 읽기 쉬운 형태로 바꾸는 계층이지, 지표 의미를 완성하는 계층이 아니다.

### 2) intermediate

여러 staging 모델을 조합해 비즈니스 이벤트 단위를 만드는 계층이다.

- 주문과 결제를 결합해 order lifecycle 만들기
- 세션화 이전의 clickstream 이벤트 정리
- 이벤트 dedup
- 상태 코드 해석
- SCD join 전 준비 데이터 구성

여기서는 비즈니스 규칙이 들어가지만, 최종 소비자 지표와 1:1로 연결되지는 않는 경우가 많다.

### 3) mart

대시보드, 리포트, 애플리케이션 분석 소비자가 직접 보는 계층이다.

- 일별 매출 fact
- 사용자 cohort 집계
- 구독 유지율 테이블
- 팀/조직 단위 KPI 모델

mart의 핵심은 쿼리 편의가 아니라 **소비 계약의 안정성**이다. 즉 mart는 내부 SQL 재료가 아니라, 다른 팀이 기대고 쓸 수 있는 제품이어야 한다.

### 왜 이 계층이 중요한가?

이 구조가 있어야 다음 판단이 쉬워진다.

- 어디까지를 incremental로 둘 것인가?
- 어떤 계층에서 테스트를 강하게 걸 것인가?
- late data를 어느 층에서 보정할 것인가?
- 어느 모델은 full refresh를 감수하고, 어느 모델은 절대 안 되는가?

계층이 없으면 incremental이 여기저기 퍼지고, 테스트는 일부 마트에만 걸리며, lineage는 복잡한 spaghetti graph가 된다.

### 실무 기준

- staging은 얇고 예측 가능해야 한다
- intermediate는 재사용 가능한 비즈니스 조립 단위여야 한다
- mart는 소비자 계약과 SLA의 중심이어야 한다

이 분리가 먼저다. 그 다음에야 incremental과 snapshot 전략이 의미를 가진다.

---

## 핵심 개념 2: Incremental Model은 "빨리 돌리기"가 아니라 "부분 재계산의 계약"이다

많은 팀이 모델이 느려지면 반사적으로 incremental을 붙인다. 하지만 incremental은 단순 성능 기능이 아니다. 정확히는 아래 질문에 대한 답이다.

> 이 모델은 전체를 다시 계산하지 않고, **일부 범위만 재계산해도 결과를 신뢰할 수 있는가?**

이 질문에 답이 흐리면 incremental은 최적화가 아니라 데이터 부채가 된다.

### incremental이 잘 맞는 경우

- 입력 데이터에 명확한 시간 축 또는 증가 키가 있다
- late data 허용 범위를 팀이 정의했다
- 고유 키 또는 merge 기준이 분명하다
- 부분 재처리 범위를 안정적으로 다시 계산할 수 있다
- 전체 refresh 비용이 너무 크다

예를 들어 `fct_orders`를 주문 완료 시각 기준으로 관리하고, 최근 3일 데이터를 재계산하는 정책이 있다면 incremental은 현실적이다.

### incremental이 위험한 경우

- 소스가 잦은 update/delete를 일으키지만 unique key 설계가 약하다
- 이벤트 도착이 불규칙해 재계산 범위를 좁게 잡기 어렵다
- 조인 대상 차원 테이블의 변경이 과거 fact 결과를 바꾼다
- 모델이 cumulative metric이라 일부 구간만 다시 계산하면 전체 정합성이 깨진다
- 소스 dedup이 upstream에서 보장되지 않는다

즉 incremental은 "input append-only"에 가까울수록 쉽고, **과거 수정이 잦을수록 설계가 어려워진다**.

### 가장 중요한 네 가지 기준

#### 1) cutoff 기준

보통 `is_incremental()` 안에서 최근 N일만 다시 읽는다.

{% raw %}
```sql
{{ config(
    materialized='incremental',
    unique_key='order_id',
    incremental_strategy='merge'
) }}

with source as (
    select *
    from {{ ref('stg_orders') }}
    {% if is_incremental() %}
      where updated_at >= (
        select coalesce(dateadd(day, -3, max(updated_at)), '2000-01-01')
        from {{ this }}
      )
    {% endif %}
),
final as (
    select
        order_id,
        customer_id,
        status,
        paid_at,
        updated_at,
        total_amount
    from source
)
select * from final
```
{% endraw %}

여기서 핵심은 SQL 문법이 아니라, **왜 최근 3일인가**에 대한 운영 근거다.

- 모바일/오프라인 이벤트가 최대 48시간 늦게 들어온다
- 결제 정산 상태가 평균 1일 안에 확정된다
- 취소/환불 상태 정정이 보통 72시간 이내에 발생한다

즉 재계산 범위는 감이 아니라 **업무 지연 분포와 데이터 수정 패턴**에 근거해야 한다.

#### 2) merge 기준과 unique key

`unique_key`가 약하면 incremental은 중복 생성기다.

- 주문 fact면 `order_id`
- 일별 사용자 집계면 `dt + user_id`
- 세션 집계면 `session_id`
- SCD join 결과면 surrogate key + validity range를 더 명확히 정의해야 할 수도 있다

핵심은 "행 하나를 무엇으로 덮어쓸 것인가"다. 이 기준이 불분명하면 merge는 느리고 결과도 흔들린다.

#### 3) late data 정책

incremental에서 가장 자주 터지는 문제는 늦게 도착한 데이터다.

예를 들어 최근 1일만 다시 읽는데, 3일 전 주문이 뒤늦게 취소되면 어떻게 할까?

선택지는 보통 셋이다.

- 최근 7일처럼 재계산 구간을 더 넓힌다
- 늦은 데이터 전용 보정 모델을 둔다
- 주기적으로 full refresh 또는 파티션 단위 rebuild를 수행한다

정답은 하나가 아니다. 중요한 것은 **어느 수준의 정확도와 비용을 교환할지 명시하는 것**이다.

#### 4) delete와 변경 전파

소스 시스템에서 hard delete가 일어나면 incremental이 놓치기 쉽다. 특히 append 위주 사고로 설계하면 삭제 반영이 늦거나 영원히 누락될 수 있다.

이때는 아래 중 하나를 분명히 해야 한다.

- delete 플래그를 CDC로 받아 soft delete로 처리한다
- merge 시 삭제 조건을 반영한다
- downstream에서 active 레코드만 별도 필터링한다
- full rebuild 주기를 둔다

삭제를 다루지 않는 incremental은 생각보다 빨리 현실과 어긋난다.

---

## 실무 예시: 주문 분석용 fact 모델을 incremental로 운영할 때 무엇을 먼저 정해야 하나

예를 들어 아래 요구가 있다고 하자.

- 주문, 결제, 환불 데이터를 묶어 `fct_order_revenue`를 만든다
- BI 팀이 일별 매출, 환불률, 결제 전환율을 본다
- 원천은 CDC 기반으로 10분 간격 적재된다
- 취소와 환불은 최대 5일 뒤 정정될 수 있다

이때 흔한 나쁜 접근은 다음이다.

- 일단 주문 테이블만 incremental merge
- 결제와 환불은 join으로 붙임
- 최근 1일만 다시 읽음
- 숫자가 틀리면 다음에 범위를 늘려봄

이렇게 하면 거의 반드시 아래 문제가 생긴다.

- 과거 주문이 늦게 환불되면 fact가 갱신되지 않는다
- 차원 조인 변경이 과거 결과를 뒤틀 수 있다
- 대시보드 일별 수치와 정산 수치가 안 맞는다
- 운영자는 어느 날짜를 다시 돌려야 하는지 모른다

더 나은 기준은 아래다.

### 1) grain을 먼저 고정한다

`fct_order_revenue`의 grain이 "주문 1건당 1행"인지, "주문-결제 시도별 1행"인지 먼저 결정해야 한다. grain이 흔들리면 unique key도 흔들리고 테스트도 약해진다.

예를 들어 주문 1건당 1행이면:

- `order_id`가 unique key
- 상태 변화는 같은 행을 업데이트
- 금액 확정 기준도 한 행 안에서 관리

반대로 결제 시도별이면 실패 결제와 재시도까지 별도 행이 생긴다. 둘 다 가능하지만, 같은 모델 안에 둘을 섞으면 안 된다.

### 2) 재계산 범위는 상태 변경 분포를 기준으로 잡는다

주문 생성은 당일에 집중되지만 환불은 최대 5일 뒤 발생한다면, 최근 7일 재계산이 더 현실적일 수 있다.

{% raw %}
```sql
{% if is_incremental() %}
where greatest(order_updated_at, payment_updated_at, refund_updated_at)
      >= (
        select coalesce(dateadd(day, -7, max(last_changed_at)), '2000-01-01')
        from {{ this }}
      )
{% endif %}
```
{% endraw %}

핵심은 주문 한 테이블의 `updated_at`만 보면 안 된다는 점이다. **최종 fact를 바꾸는 모든 입력 변화**를 cutoff에 반영해야 한다.

### 3) 테스트는 mart에만 걸지 말고 intermediate에도 건다

예를 들어 아래 테스트는 사실 mart 전에 잡히는 편이 더 좋다.

- 중복 order_id
- 음수 금액인데 환불이 아닌 케이스
- 결제 성공 상태인데 paid_at이 null
- 주문 생성일보다 환불일이 빠른 레코드

이상치를 mart까지 끌고 간 뒤 발견하면 복구 범위가 커진다.

### 4) 운영 재처리 명령을 표준화한다

잘하는 팀은 "dbt run 다시 돌려보자"로 운영하지 않는다. 예를 들어 아래를 정한다.

- 최근 7일 재계산: 기본 daily run
- 특정 날짜 재처리: `--vars '{rebuild_start: 2026-04-01, rebuild_end: 2026-04-03}'`
- full refresh: 월 1회 또는 스키마 변경 시

즉 incremental은 SQL 조건문보다 **재처리 플레이북**이 더 중요하다.

---

## 핵심 개념 3: Snapshot은 "예전 값 보관"이 아니라 기준 시점의 상태를 계약으로 남기는 장치다

dbt snapshot을 단순히 이력 테이블로 이해하면 반만 이해한 것이다. snapshot의 진짜 가치는 **시간에 따라 변하는 차원값을, 과거 시점 기준으로 다시 재현할 수 있게 만드는 것**에 있다.

이게 필요한 대표 장면은 아래다.

- 고객 등급이 바뀌는데, 과거 주문은 당시 등급 기준으로 보고 싶다
- 영업 조직 구조가 바뀌었지만, 지난 분기 실적은 당시 조직 기준으로 유지해야 한다
- 상품 카테고리 분류가 개편돼도 과거 리포트가 갑자기 바뀌면 안 된다
- 계정 상태(active, churned, suspended)를 시점별로 추적해야 한다

이런 문제를 snapshot 없이 현재 차원 테이블만 조인하면 무슨 일이 생길까?

- 과거 주문도 현재 고객 등급으로 재해석된다
- 대시보드가 소급 변경된다
- 월말 리포트 수치가 재실행 때마다 달라진다
- "왜 지난달 수치가 달라졌나"에 답하기 어려워진다

### timestamp strategy와 check strategy

dbt snapshot은 보통 두 전략을 생각한다.

- `timestamp`: `updated_at` 같은 변경 시각 기준
- `check`: 특정 컬럼 집합이 바뀌었는지 비교

실무에서는 가능하면 `timestamp`가 더 단순하고 운영하기 쉽다. 다만 소스가 신뢰 가능한 `updated_at`를 주지 않으면 `check_cols` 기반을 고려해야 한다.

{% raw %}
```sql
{% snapshot snap_customer_tier %}

{{
    config(
      target_schema='snapshots',
      unique_key='customer_id',
      strategy='timestamp',
      updated_at='updated_at'
    )
}}

select
    customer_id,
    customer_tier,
    region,
    account_manager_id,
    updated_at
from {{ ref('stg_customers') }}

{% endsnapshot %}
```
{% endraw %}

### snapshot을 어디에 써야 하나?

snapshot은 모든 차원에 무조건 쓰는 기능이 아니다. 아래 질문에 "예"가 많을수록 가치가 커진다.

- 과거 보고서가 현재 차원값에 오염되면 안 되는가?
- 값 변경 이력이 비즈니스적으로 의미가 큰가?
- SCD Type 2가 필요한가?
- 변경 전후를 비교 분석할 일이 잦은가?

반대로 값이 거의 안 바뀌고, 과거 재현 필요도 낮다면 snapshot은 과할 수 있다.

### snapshot 도입 시 자주 놓치는 점

#### 1) snapshot 자체가 정합성을 해결해주지는 않는다

snapshot 테이블이 있다고 해서 fact 조인이 자동으로 시점 정합성을 얻는 것은 아니다. fact의 event time과 snapshot validity range를 맞춰 조인해야 한다.

{% raw %}
```sql
select
    f.order_id,
    f.ordered_at,
    s.customer_tier
from {{ ref('fct_orders') }} f
left join {{ ref('snap_customer_tier') }} s
  on f.customer_id = s.customer_id
 and f.ordered_at >= s.dbt_valid_from
 and f.ordered_at < coalesce(s.dbt_valid_to, '2999-12-31')
```
{% endraw %}

핵심은 snapshot을 쌓는 것보다 **올바른 as-of join을 일관되게 쓰는 것**이다.

#### 2) 너무 많은 차원에 snapshot을 걸면 비용이 커진다

조직도, 상품 속성, 가격, 사용자 플랜, 영업 담당자, 지역 분류까지 전부 snapshot 하면 저장량과 조인 비용이 커진다. 정말 시점 재현이 필요한 차원부터 적용하는 편이 맞다.

#### 3) source의 update 품질이 나쁘면 snapshot도 흔들린다

`updated_at`가 뒤늦게 채워지거나, 변경 없이도 매번 갱신되면 snapshot 품질도 떨어진다. upstream 컬럼 신뢰도를 먼저 봐야 한다.

---

## 핵심 개념 4: Test는 "있으면 좋은 것"이 아니라 배포와 재처리의 안전장치다

dbt 테스트를 단순 QA 보조 기능으로 보면 운영이 약해진다. 실무에서 test의 핵심 가치는 아래다.

- 잘못된 스키마 변경을 빨리 막는다
- 소스 이상치를 downstream 확산 전에 잡는다
- incremental merge의 중복과 null 사고를 초기에 발견한다
- 문서와 계약을 코드 수준에서 동기화한다

### schema test와 data test를 다르게 써야 한다

#### schema test

- `not_null`
- `unique`
- `accepted_values`
- `relationships`

이 테스트는 열 계약을 명확히 해준다. 특히 mart에서는 거의 필수다.

```yaml
version: 2

models:
  - name: fct_order_revenue
    description: 주문 단위 매출 분석 fact
    columns:
      - name: order_id
        tests:
          - not_null
          - unique
      - name: order_status
        tests:
          - accepted_values:
              values: ['created', 'paid', 'cancelled', 'refunded']
      - name: customer_id
        tests:
          - relationships:
              to: ref('dim_customers')
              field: customer_id
```

#### data test

복합 비즈니스 규칙은 custom data test로 잡아야 한다.

예:

- 결제 완료인데 `paid_amount <= 0`
- 환불액이 결제액보다 큼
- `order_created_at > paid_at`
- 국가 코드와 통화 코드 조합이 정책과 다름

{% raw %}
```sql
select *
from {{ ref('fct_order_revenue') }}
where order_status = 'paid'
  and (paid_at is null or paid_amount <= 0)
```
{% endraw %}

이런 테스트는 단순 null 체크보다 훨씬 실무 가치가 크다.

### source freshness를 얕게 보면 안 된다

dbt의 freshness는 단순 메타데이터가 아니다. 특히 CDC나 배치 ingestion 위에 올라간 모델에서는 소스 freshness가 깨진 상태에서 마트를 정상 배포해도, 결과는 그럴듯하게 틀릴 수 있다.

예를 들어 아래를 연결해서 봐야 한다.

- 주문 소스 freshness 지연 2시간
- 결제 소스 freshness 정상
- 마트는 성공
- 대시보드는 주문 전환율 급락

이런 상황은 테스트 실패보다 더 위험할 수 있다. **신선하지 않은 입력 위에 만든 정상 출력**이기 때문이다.

그래서 잘하는 팀은 단순히 `dbt test`만 돌리지 않고 아래를 분리한다.

- source freshness 체크
- 모델 빌드
- 핵심 contract test
- 비즈니스 data test
- 문서 및 lineage 검증

### 배포 게이트로서의 test

실무 기준으로는 아래처럼 강도를 나누는 편이 현실적이다.

- staging: 핵심 컬럼 null/타입/accepted values 중심
- intermediate: grain, dedup, 상태 일관성 중심
- mart: unique, relationship, 핵심 KPI 불변식 중심

그리고 실패 시 정책도 정해야 한다.

- 어떤 테스트는 경고(warn)인가?
- 어떤 테스트는 즉시 배포 중단(error)인가?
- 특정 소스 freshness 지연은 어느 SLA에서 실패로 볼 것인가?

테스트는 많이 거는 것보다 **멈춰야 할 지점을 정확히 고르는 것**이 중요하다.

---

## 핵심 개념 5: Lineage는 예쁜 DAG가 아니라 영향 범위, 우선 복구 대상, 소유권을 보여줘야 한다

dbt lineage 그래프를 처음 보면 시각적으로 만족감이 크다. 하지만 운영에서 중요한 것은 그래프가 아니라 **그 그래프가 어떤 판단을 즉시 가능하게 하느냐**다.

### lineage가 실제로 도와주는 질문

- 특정 소스 컬럼이 바뀌면 어떤 마트가 영향을 받는가?
- 지금 실패한 intermediate 모델 때문에 어떤 대시보드가 위험한가?
- full refresh가 필요한 모델은 어디까지 전파되는가?
- 테스트 실패가 한 모델 문제인지, 여러 하위 소비자까지 번지는 문제인지?
- 배포를 slim CI로 줄일 때 최소 영향 범위를 어떻게 잡을 것인가?

즉 lineage는 문서화 기능이 아니라 **변경 영향 분석 도구**다.

### lineage를 운영 가능하게 만드는 조건

#### 1) ref를 일관되게 써야 한다

하드코딩된 스키마 참조가 많으면 그래프가 끊긴다. dbt가 잘 보이는 프로젝트와 안 보이는 프로젝트의 차이는 매크로 실력보다도 **의존성 표기 일관성**에 있다.

#### 2) 모델 이름이 역할을 설명해야 한다

`tmp_final_v2`, `result_new`, `mart_test_final` 같은 이름이 쌓이면 lineage는 있으나마나하다. 보통 아래 정도는 지키는 편이 좋다.

- `stg_` for staging
- `int_` for intermediate
- `dim_`, `fct_`, `agg_` for mart/serving
- 도메인과 grain이 이름에 드러나기

#### 3) exposure와 owner를 연결해야 한다

대시보드나 서비스 리포트가 어떤 mart를 쓰는지 exposure로 연결하면, 모델 실패 시 누가 영향을 받는지 더 명확해진다. lineage는 결국 기술 그래프가 아니라 **조직 그래프와 연결될 때** 운영 가치가 커진다.

### slim CI와 변경 범위 최소화

프로젝트가 커지면 전체 모델을 매번 다 돌리는 것이 비효율적이다. 이때 lineage 기반 선택 실행이 도움이 된다.

- 변경된 모델만 실행
- 그 하위 소비자만 테스트
- 핵심 mart만 우선 확인

하지만 slim CI를 안전하게 쓰려면 전제가 있다.

- lineage가 정확할 것
- 테스트가 층별로 설계돼 있을 것
- 매크로 변경의 영향 범위를 팀이 이해하고 있을 것

즉 lineage는 시각화보다 **선택 실행과 사고 반경 파악**에서 진짜 값이 나온다.

---

## 실무 설계 예시: dbt, Airflow, 웨어하우스 기능은 어떻게 역할을 나누는 편이 좋은가?

dbt 프로젝트가 커지면 흔히 경계가 섞인다. 어디까지를 dbt에서 하고, 어디부터는 웨어하우스 기능이나 오케스트레이터가 맡아야 할까?

### dbt가 잘하는 것

- SQL 기반 변환 로직 버전 관리
- 모델 의존성 선언과 선택 실행
- 테스트, 문서, lineage
- incremental/snapshot 같은 변환 레벨 관리
- 분석 엔지니어와 데이터 엔지니어의 협업 표준화

### 오케스트레이터가 잘하는 것

- 실행 시간 스케줄링
- 재시도/알림/백필 운영
- 여러 시스템 간 워크플로우 연결
- upstream ingestion 완료 조건 확인

### 웨어하우스가 잘하는 것

- MERGE, partition pruning, clustering, materialized view
- query optimization
- storage lifecycle 관리
- 권한, 리소스 큐, 워크로드 격리

핵심은 한 도구에 모든 책임을 몰지 않는 것이다. 예를 들어:

- Airflow는 언제 실행할지와 실패 시 어떻게 복구할지 담당
- dbt는 무엇을 어떤 의존성으로 변환할지 담당
- 웨어하우스는 그 변환을 어떤 물리 전략으로 빠르게 수행할지 담당

이 분리가 없으면 아래 같은 안 좋은 패턴이 나온다.

- dbt 매크로 안에 스케줄링 가정이 숨는다
- Airflow DAG 안에 SQL 로직이 너무 많이 들어간다
- 웨어하우스별 최적화가 모델 계약을 오염시킨다

실무에서는 책임 경계가 선명할수록 운영이 쉬워진다.

---

## 트레이드오프: dbt를 강하게 운영할수록 얻는 것과 잃는 것

dbt는 도입만 하면 좋아지는 도구가 아니다. 규율을 강하게 잡을수록 분명한 비용도 생긴다.

### 1) 모델 세분화 vs 실행 복잡도

모델을 잘게 나누면 재사용성과 테스트 포인트는 좋아진다. 하지만 모델 수가 너무 많으면:

- DAG가 복잡해진다
- 디버깅 이동 경로가 길어진다
- 실행 시간이 늘 수 있다
- 초보 팀원이 진입하기 어려워질 수 있다

그래서 "작게 나누는 것" 자체가 목표가 아니라, **grain과 재사용 경계가 명확한 수준으로 나누는 것**이 중요하다.

### 2) incremental 성능 vs 정합성 단순성

incremental은 비용과 시간을 줄여준다. 하지만 full refresh보다 사고 실험이 훨씬 어렵다.

- 늦은 데이터
- 부분 재처리
- 삭제 반영
- 차원 변경 소급 영향

이걸 감당할 수 없다면 느리더라도 full rebuild가 더 안전한 모델도 있다.

### 3) snapshot 이력 보존 vs 저장/조인 비용

snapshot은 과거 재현성을 준다. 대신 저장 공간과 조인 복잡도를 늘린다. 시점 재현 가치가 낮은 차원에는 과할 수 있다.

### 4) 강한 테스트 vs 운영 민감도 증가

테스트를 강하게 걸수록 위험한 배포를 줄일 수 있다. 반면 소스 품질이 아직 거친 조직에서는 실패가 잦아져 팀이 테스트를 무시하게 될 수도 있다.

그래서 중요한 것은 테스트 수보다 **실제로 멈출 만한 규칙을 고르는 것**이다.

---

## 흔한 실수: dbt 프로젝트가 커질수록 자주 보이는 안티패턴

### 1) 모든 느린 모델을 incremental로 바꾸기

느리다는 이유만으로 incremental을 붙이면 나중에 정합성 문제를 추적하는 비용이 더 커진다. 먼저 grain, late data, delete, unique key를 정해야 한다.

### 2) staging에 비즈니스 로직을 과도하게 넣기

staging은 재사용 기초층이다. 여기서 이미 지표 의미와 필터링을 많이 넣으면 downstream이 그 로직에 과도하게 결합된다.

### 3) mart에만 테스트를 걸기

문제를 제일 늦게 발견하는 방식이다. intermediate의 dedup, grain, 상태 일관성 테스트가 빠지면 mart에서 이미 복합적으로 섞인 뒤 발견한다.

### 4) snapshot을 쌓고 as-of join은 하지 않기

가장 허무한 패턴이다. snapshot은 있는데 사실상 현재값 조인만 쓰면 과거 재현성은 얻지 못한다.

### 5) source freshness를 알람만 보고 무시하기

많은 팀이 freshness 실패를 경고 수준으로만 두다가, 결국 오래된 입력으로 생성된 정상-looking 리포트를 신뢰하게 된다. 이건 조용한 장애다.

### 6) 모델 이름과 설명을 대충 짓기

프로젝트가 커질수록 가장 비싼 비용은 실행 비용보다 **이해 비용**이다. 이름과 설명이 부실하면 lineage도 문서도 의미가 줄어든다.

### 7) 웨어하우스 엔진 차이를 무시하기

BigQuery, Snowflake, Databricks, Redshift, Postgres는 incremental 전략과 성능 특성이 다르다. `merge`가 항상 정답이 아니고, `insert_overwrite`가 더 나은 엔진도 있다. dbt는 추상화를 제공하지만 물리 특성까지 지워주지는 않는다.

---

## 운영 체크리스트: 실제로 덜 망가지는 dbt 프로젝트를 위한 기준

아래 체크리스트를 주기적으로 점검하면 좋다.

### 모델 구조

- staging, intermediate, mart 계층이 이름과 디렉터리 수준에서 구분돼 있는가?
- 각 mart 모델의 grain이 문서화돼 있는가?
- 대시보드/리포트 소비 계약이 설명에 드러나는가?

### incremental

- incremental 모델마다 unique key가 명시적인가?
- 재계산 범위가 업무 지연 분포를 근거로 정해졌는가?
- late data와 delete 처리 정책이 문서화돼 있는가?
- 특정 기간 rebuild 방법이 운영 플레이북에 있는가?

### snapshot

- snapshot 대상 차원이 정말 시점 재현이 필요한가?
- `updated_at` 품질을 신뢰할 수 있는가?
- fact와 snapshot 간 as-of join 패턴이 표준화돼 있는가?

### test

- mart 핵심 키에 not null/unique가 있는가?
- accepted values와 relationship 테스트가 필요한 곳에 걸려 있는가?
- 비즈니스 data test가 핵심 지표 모델에 존재하는가?
- source freshness 실패 시 실행 중단 기준이 있는가?

### lineage / 운영

- ref/source를 일관되게 사용해 그래프가 끊기지 않는가?
- exposure와 owner 연결이 되어 있는가?
- slim CI 또는 선택 실행 기준이 정리돼 있는가?
- 실패 시 어느 모델부터 복구할지 우선순위가 보이는가?

이 체크리스트가 있다면 dbt는 단순 SQL 러너가 아니라 **분석 테이블 운영 체계**가 된다.

---

## 한 줄 정리

dbt를 잘 쓴다는 것은 SQL을 많이 쓰는 것이 아니라, **Incremental Model, Snapshot, Test, Lineage를 이용해 분석 테이블의 정합성, 재현성, 영향 범위, 복구 절차를 계약으로 만드는 것**이다.
