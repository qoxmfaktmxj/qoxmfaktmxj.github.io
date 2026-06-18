---
layout: post
title: "Data Contract 실전: Schema Compatibility, Ownership, SLA, Lineage로 깨지지 않는 데이터 파이프라인을 설계하는 법"
date: 2026-06-18 11:50:00 +0900
categories: [data-infra]
tags: [study, data-infra, data-contract, schema-compatibility, ownership, sla, lineage, data-quality, governance, pipeline]
permalink: /data-infra/2026/06/18/study-data-contract-schema-compatibility-ownership-sla-lineage.html
---

## 배경: 데이터 파이프라인 장애의 상당수는 기술 장애가 아니라 계약 부재에서 시작된다

데이터 플랫폼을 처음 만들 때는 보통 수집, 적재, 변환, 대시보드에 집중한다.

- 운영 DB에서 CDC를 읽는다
- Kafka나 object storage에 원천 데이터를 쌓는다
- Spark, Flink, dbt, SQL job으로 모델을 만든다
- warehouse나 lakehouse에서 분석 테이블을 제공한다
- BI, 추천, 정산, CRM, ML feature pipeline이 그 테이블을 사용한다

이 구조 자체는 익숙하다. 문제는 규모가 조금만 커져도 데이터 장애가 코드 장애보다 더 애매하게 터진다는 점이다.

- upstream 서비스가 컬럼 타입을 `int`에서 `string`으로 바꿨는데 downstream 배치가 밤새 실패한다
- `status` 값에 `CANCELED_BY_ADMIN`이 새로 들어왔는데 대시보드는 이 값을 누락한다
- `user_id` nullable 정책이 바뀌었지만 feature pipeline은 non-null이라고 가정한다
- 이벤트 payload에 필드가 추가되었는데 schema registry에는 반영되지 않았다
- 테이블은 정상 생성됐지만 전일 대비 row count가 90% 줄었다
- 매일 07:00까지 준비되어야 하는 지표 테이블이 08:30에 완성된다
- owner가 불명확해서 장애가 나도 누구에게 물어봐야 할지 모른다
- 컬럼 의미가 바뀌었는데 이름은 그대로라 몇 주 뒤 잘못된 의사결정으로 드러난다

이런 문제는 단순히 "테스트를 더 추가하자"로 끝나지 않는다. 테스트는 필요하지만, 무엇을 보장해야 하는지부터 정해져 있어야 한다. 보장해야 할 대상이 불명확하면 테스트는 우연히 발견한 문제만 막고, 실제 중요한 변경은 계속 새어 나간다.

Data Contract는 이 지점에서 등장한다.

> **Data Contract는 데이터 생산자와 소비자 사이에서 schema, 의미, 품질, 신선도, 변경 절차, 소유권을 명시하는 운영 계약이다.**

여기서 중요한 단어는 "문서"가 아니라 "계약"이다. 문서는 읽히지 않을 수 있고, 오래되기 쉽다. 계약은 배포, 검증, 알림, 승인, lineage, incident 대응에 연결되어야 한다.

오늘 글은 Data Contract를 "데이터 거버넌스 용어"로 설명하지 않는다. 중급 이상 개발자와 데이터 엔지니어가 실제 운영에서 다음 질문에 답할 수 있도록 정리한다.

1. Data Contract는 schema registry, dbt test, 데이터 카탈로그와 무엇이 다른가
2. 어떤 항목을 계약으로 묶어야 하고, 어떤 항목은 문서로만 둬도 되는가
3. schema compatibility는 Kafka 이벤트, warehouse 테이블, lakehouse 파일에서 어떻게 다르게 적용되는가
4. SLA와 SLO는 freshness, completeness, correctness를 어떻게 수치로 바꾸는가
5. ownership과 approval flow가 없을 때 왜 data quality test만으로는 부족한가
6. contract change를 breaking, non-breaking, risky change로 어떻게 분류할 것인가
7. 실무에서 흔히 망가지는 패턴과 배포 전 체크리스트는 무엇인가

결론부터 말하면 이렇다.

**Data Contract의 핵심은 "데이터 스키마를 예쁘게 정의하는 것"이 아니라, 데이터 변경이 소비자에게 미치는 영향을 배포 전에 드러내고, 운영 중에는 위반을 빠르게 탐지하며, 책임자를 명확히 하는 것이다.**

이 관점이 중요하다. 계약은 자유를 줄이는 장치가 아니다. 오히려 생산자가 더 빠르게 변경할 수 있게 해주는 안전장치다. 어떤 변경이 안전한지, 어떤 변경은 소비자와 협의해야 하는지, 어떤 지표가 깨지면 누구에게 알려야 하는지가 명확할수록 파이프라인은 더 과감하게 진화할 수 있다.

---

## 먼저 큰 그림: Data Contract는 데이터 제품의 API 명세다

백엔드 API를 운영할 때는 대체로 계약 개념이 익숙하다.

- endpoint path
- request parameter
- response schema
- status code
- authentication
- rate limit
- backward compatibility
- versioning
- deprecation policy

API 응답에서 필드를 갑자기 지우거나 타입을 바꾸면 클라이언트가 깨진다. 그래서 OpenAPI, protobuf, GraphQL schema, consumer-driven contract test 같은 도구를 쓴다.

데이터도 마찬가지다. 다만 데이터 세계에서는 계약 경계가 더 넓고 느슨하다.

- Kafka topic의 event schema
- CDC outbox payload
- object storage의 raw file layout
- Iceberg, Delta, Hudi 같은 table format의 schema
- warehouse mart table
- ML feature table
- BI semantic model
- reverse ETL로 CRM에 보내는 segment

이들은 모두 누군가에게는 API다. 차이는 호출 방식뿐이다. API는 요청-응답으로 호출되고, 데이터 제품은 batch, stream, query, subscription, feature lookup으로 소비된다.

따라서 데이터 제품도 최소한 아래 정보를 제공해야 한다.

- 어떤 필드가 존재하는가
- 필드 타입과 nullable 정책은 무엇인가
- primary key나 natural key는 무엇인가
- row 하나가 의미하는 grain은 무엇인가
- 값의 도메인은 어디까지인가
- 언제까지 준비되어야 하는가
- 얼마나 늦거나 누락될 수 있는가
- breaking change는 어떻게 공지하고 승인받는가
- 장애가 나면 누가 대응하는가

이걸 명시하지 않은 데이터 파이프라인은 내부 API를 문서 없이 공개한 것과 비슷하다. 처음에는 잘 굴러가지만, 조직이 커질수록 변경 비용이 급격히 올라간다.

### Data Contract가 아닌 것

Data Contract를 도입할 때 가장 먼저 정리할 것은 "무엇이 아닌가"다.

Data Contract는 단순 컬럼 목록이 아니다.

```yaml
columns:
  - name: user_id
    type: string
  - name: created_at
    type: timestamp
```

이 정도는 schema description이다. 계약이 되려면 이 컬럼이 어떤 소비자에게 어떤 안정성을 제공하는지까지 포함해야 한다.

Data Contract는 데이터 카탈로그만도 아니다. 카탈로그는 검색과 이해를 돕는다. 하지만 카탈로그에 설명이 있다고 해서 배포 시 breaking change가 막히지는 않는다.

Data Contract는 dbt test만도 아니다. dbt test는 특정 시점의 결과 테이블을 검증한다. 하지만 upstream 이벤트 변경, owner 승인, deprecation window, consumer 영향 분석까지 자동으로 해결하지는 않는다.

Data Contract는 schema registry만도 아니다. schema registry는 이벤트 호환성 검증에 강하다. 하지만 freshness SLA, row count anomaly, business meaning, downstream owner까지 포괄하지 않는다.

즉 Data Contract는 여러 도구 위에 걸친 운영 레이어다.

```text
Data Contract
  ├─ schema definition
  ├─ semantic definition
  ├─ compatibility rule
  ├─ quality rule
  ├─ freshness/SLA rule
  ├─ ownership
  ├─ change management
  └─ enforcement hooks
```

도구가 아니라 계약을 먼저 정의해야 한다. 그 다음에 일부는 schema registry로, 일부는 dbt test로, 일부는 CI로, 일부는 data catalog로, 일부는 alerting으로 집행한다.

---

## 핵심 개념 1: 계약의 첫 줄은 스키마가 아니라 grain이다

데이터 계약을 만들 때 많은 팀이 컬럼부터 적는다. 하지만 실무에서 더 먼저 정해야 할 것은 grain이다.

Grain은 row 하나가 의미하는 단위다.

- `orders` 테이블: 주문 1건당 1 row
- `order_items` 테이블: 주문 상품 1개당 1 row
- `daily_user_metrics` 테이블: 사용자 1명, 날짜 1일당 1 row
- `payment_events` 토픽: 결제 상태 전이 이벤트 1건당 1 message
- `inventory_snapshot` 테이블: 상품 1개, 창고 1개, snapshot 시각 1개당 1 row

Grain이 명확하지 않으면 이후 계약이 전부 흔들린다.

예를 들어 `sales_daily`라는 테이블이 있다고 하자.

```text
date        store_id   product_id   revenue
2026-06-18  S-1        P-10         120000
```

이 row의 grain은 무엇일까?

- 매장-상품-일 단위인가
- 매장-상품-주문일 단위인가
- 매장-상품-정산일 단위인가
- 환불은 주문일에 반영되는가, 환불일에 반영되는가
- timezone은 KST인가 UTC인가
- `revenue`는 gross인가 net인가
- 쿠폰과 포인트는 차감 전인가 후인가

컬럼명과 타입만 보면 알 수 없다. 하지만 소비자는 이 답에 따라 조인, 집계, 비교, KPI 해석을 완전히 다르게 한다.

### Grain이 없을 때 생기는 장애

Grain이 모호한 테이블은 다음 문제를 만든다.

- 중복 row를 발견해도 버그인지 정상인지 판단할 수 없다
- primary key test를 걸 수 없다
- row count 변화가 정상 트래픽 증가인지 중복 적재인지 구분할 수 없다
- downstream이 임의로 `distinct`를 넣어 문제를 숨긴다
- 지표 정의가 팀마다 달라진다
- 재처리 시 동일 row를 덮어써야 하는지 append해야 하는지 애매해진다

특히 batch pipeline에서는 grain이 곧 idempotency 기준이다. 같은 날짜 파티션을 재처리할 때 `date + store_id + product_id`가 같은 row를 replace해야 하는지, event stream처럼 append해야 하는지 계약에 있어야 한다.

### 계약에 grain을 쓰는 방식

예시는 다음처럼 쓸 수 있다.

```yaml
dataset: mart.sales_daily_by_store_product
owner:
  team: data-platform
  slack: "#data-platform-oncall"
grain:
  description: "KST 기준 매장, 상품, 매출 발생일 단위의 일별 정산 전 매출"
  keys:
    - sales_date
    - store_id
    - product_id
time_semantics:
  business_timezone: Asia/Seoul
  event_time_column: paid_at
  partition_column: sales_date
```

이 정도만 있어도 downstream은 훨씬 안전해진다.

- 어떤 컬럼 조합이 유일해야 하는지 알 수 있다
- partition overwrite 기준이 명확하다
- 지연 이벤트를 어디에 반영해야 하는지 논의할 수 있다
- 날짜 집계가 UTC와 KST 사이에서 어긋나는 일을 줄일 수 있다

스키마는 중요하다. 하지만 grain이 없는 스키마는 타입만 맞는 모호한 데이터다.

---

## 핵심 개념 2: Schema Compatibility는 "필드가 있나"보다 "소비자가 계속 동작하나"를 봐야 한다

Schema compatibility를 이야기하면 보통 backward compatibility, forward compatibility, full compatibility 같은 용어가 나온다. 이벤트 스트리밍에서는 Avro, Protobuf, JSON Schema와 schema registry가 자주 등장한다.

하지만 계약 관점에서 더 중요한 질문은 단순하다.

> 이 변경 후에도 기존 소비자가 재배포 없이 계속 동작하는가?

이 질문에 답하려면 변경 종류를 나눠야 한다.

### 일반적으로 안전한 변경

다음 변경은 대체로 non-breaking으로 볼 수 있다. 단, 소비자가 엄격한 projection이나 `SELECT *` 후 positional mapping을 쓰지 않는다는 전제가 있다.

- nullable field 추가
- default가 있는 optional field 추가
- 설명, owner, tag 같은 metadata 추가
- enum 설명 추가
- 새로운 파티션 값 추가
- 관측용 컬럼 추가

예를 들어 이벤트에 `coupon_code`를 optional로 추가하는 것은 보통 안전하다.

```json
{
  "order_id": "O-100",
  "user_id": "U-9",
  "paid_amount": 25000,
  "coupon_code": null
}
```

하지만 warehouse 테이블에서는 이것도 소비자에 따라 위험할 수 있다.

- `SELECT *` 결과를 CSV로 export하는 job이 있다
- 컬럼 순서를 기준으로 ingest하는 legacy job이 있다
- BI semantic model이 새 필드를 자동 노출해 권한 문제가 생긴다
- nullable 컬럼이 사실상 PII인데 masking 정책이 빠졌다

그래서 계약은 schema compatibility와 consumer behavior를 함께 봐야 한다.

### 일반적으로 위험한 변경

다음은 대부분 breaking change로 봐야 한다.

- 필드 삭제
- 필드 rename
- 타입 축소 또는 의미 있는 타입 변경
- nullable에서 non-nullable로 변경
- primary key 또는 grain 변경
- enum 값 삭제
- 값의 단위 변경
- timezone 기준 변경
- 같은 컬럼명으로 의미 변경
- partition key 변경

예를 들어 `amount` 컬럼이 원 단위 integer였는데 소수점 포함 decimal로 바뀌면 타입 시스템상 호환될 수도 있다. 하지만 비즈니스 의미상 breaking일 수 있다.

더 위험한 것은 이름은 그대로인데 의미만 바뀌는 경우다.

```text
before: revenue = 결제 금액, 환불 미반영
after : revenue = 결제 금액 - 환불 금액
```

컬럼명도 타입도 그대로라 자동 schema check는 통과한다. 하지만 대시보드, 정산, 실험 분석은 전부 다른 값을 보게 된다. Data Contract가 semantic definition을 포함해야 하는 이유가 여기에 있다.

### Compatibility를 이벤트와 테이블에 다르게 적용해야 하는 이유

Kafka 이벤트와 warehouse 테이블은 변경 전파 방식이 다르다.

Kafka 이벤트는 소비자가 stream을 따라 읽는다. 과거 메시지와 새 메시지가 같은 토픽 안에 공존할 수 있다. 따라서 consumer는 일정 기간 여러 schema version을 처리해야 할 수 있다.

Warehouse 테이블은 보통 현재 schema가 query 시점에 적용된다. 컬럼이 삭제되면 과거 partition을 읽더라도 query 자체가 깨질 수 있다. 반대로 컬럼 추가는 비교적 쉽지만, backfill되지 않은 과거 partition에서는 null이 많을 수 있다.

Lakehouse table format은 또 다르다. Iceberg나 Delta 같은 시스템은 schema evolution을 지원하지만, 모든 변경이 업무적으로 안전한 것은 아니다. field id 기반 evolution이 rename을 기술적으로 허용하더라도, downstream SQL, BI, export job이 rename을 안전하게 받아들이는지는 별도 문제다.

그래서 contract에는 데이터 형태별 compatibility rule이 분리되어야 한다.

```yaml
compatibility:
  event:
    mode: backward
    allow_optional_field_addition: true
    allow_required_field_addition: false
    allow_field_delete: false
  table:
    allow_nullable_column_addition: true
    require_backfill_plan_for_new_metric: true
    allow_column_rename: false
    allow_grain_change: false
  semantic:
    require_consumer_approval_for_metric_definition_change: true
```

이렇게 쓰면 "스키마는 안 깨졌는데 지표가 깨졌다"는 회색 지대를 줄일 수 있다.

---

## 핵심 개념 3: Quality Rule은 많을수록 좋은 것이 아니라 실패했을 때 행동이 명확해야 한다

데이터 품질 검증은 Data Contract의 핵심 집행 수단이다. 하지만 품질 rule을 많이 넣는다고 안전해지는 것은 아니다. 실패했을 때 어떤 행동을 할지 정하지 않으면 alert noise만 늘어난다.

품질 rule은 보통 다섯 종류로 나눌 수 있다.

### 1) Schema rule

스키마 자체를 검증한다.

- 필수 컬럼 존재
- 타입 일치
- nullable 정책
- enum domain
- nested field 구조

예시:

```yaml
columns:
  - name: order_id
    type: string
    nullable: false
  - name: order_status
    type: string
    nullable: false
    allowed_values:
      - CREATED
      - PAID
      - CANCELED
      - REFUNDED
```

Schema rule은 CI나 ingestion 단계에서 막기 좋다. 깨진 스키마를 downstream까지 흘려보내지 않는 것이 목표다.

### 2) Completeness rule

데이터가 충분히 들어왔는지 본다.

- row count 최소치
- 전일 대비 row count 변화율
- key별 누락률
- partition 존재 여부
- 필수 source coverage

예시:

```yaml
quality:
  completeness:
    - name: daily_row_count_not_too_low
      metric: row_count
      partition: sales_date
      min_ratio_to_7d_median: 0.75
      severity: page
```

Completeness rule은 hard threshold보다 baseline 기반이 실용적인 경우가 많다. 월요일과 일요일 트래픽이 다르고, 이벤트성 캠페인으로 정상 급증도 발생하기 때문이다.

### 3) Correctness rule

값이 업무적으로 말이 되는지 본다.

- 금액이 음수가 아닌가
- 종료 시간이 시작 시간보다 늦은가
- 주문 상태 전이가 허용된 경로인가
- 환불 금액이 결제 금액보다 크지 않은가
- foreign key가 dimension table에 존재하는가

예시:

```sql
select count(*) as invalid_count
from mart.order_payments
where paid_amount < 0
   or refunded_amount > paid_amount
```

Correctness rule은 도메인 지식이 필요하다. 그래서 데이터 플랫폼 팀만으로는 만들기 어렵다. 생산자 서비스 팀, 분석가, 도메인 owner가 함께 정의해야 한다.

### 4) Freshness rule

데이터가 제때 도착했는지 본다.

- 최신 partition 생성 시각
- 마지막 event time
- ingestion lag
- transform completion time
- dashboard refresh time

예시:

```yaml
freshness:
  expected_ready_by: "07:00 Asia/Seoul"
  warn_after_minutes: 15
  page_after_minutes: 45
  measure_column: loaded_at
```

Freshness는 "배치가 성공했는가"와 다르다. 배치가 성공했어도 2시간 늦으면 일부 업무에서는 장애다. 반대로 배치가 실패했지만 fallback snapshot이 제공되어 소비자 영향이 없을 수도 있다.

### 5) Consistency rule

다른 데이터셋과 맞는지 본다.

- source row count와 target row count 비교
- 매출 합계가 정산 시스템과 허용 오차 안에 있는가
- CDC latest state와 warehouse dimension이 맞는가
- event stream count와 batch aggregate가 맞는가

예시:

```sql
with source as (
  select count(*) as cnt
  from raw.orders
  where order_date = date '2026-06-18'
),
target as (
  select count(*) as cnt
  from mart.orders
  where order_date = date '2026-06-18'
)
select
  abs(source.cnt - target.cnt) * 1.0 / nullif(source.cnt, 0) as diff_ratio
from source, target
```

Consistency rule은 강력하지만 비용이 크다. 모든 테이블에 걸면 쿼리 비용과 운영 부담이 커진다. 정산, KPI, ML feature처럼 영향이 큰 데이터부터 적용하는 편이 좋다.

### Rule마다 severity와 action이 있어야 한다

좋은 contract는 rule을 적는 데서 끝나지 않는다. 위반 시 행동이 있어야 한다.

```yaml
rules:
  - name: order_id_not_null
    type: not_null
    column: order_id
    severity: block
    action:
      on_ci: fail
      on_runtime: quarantine_partition
      notify: "#commerce-data-alerts"

  - name: row_count_drop
    type: anomaly
    metric: row_count
    severity: page
    action:
      on_runtime: continue_with_warning
      notify: "#data-platform-oncall"
```

모든 위반을 block하면 운영이 멈춘다. 모든 위반을 warning으로 두면 아무도 보지 않는다. severity는 소비자 영향 기준으로 나눠야 한다.

- `block`: 깨진 데이터를 공개하면 안 됨
- `page`: 데이터는 공개될 수 있지만 즉시 대응 필요
- `warn`: 추세 확인 필요
- `info`: 카탈로그나 리포트용

품질 rule은 감시 장치다. 감시 장치가 울렸을 때 누가 무엇을 해야 하는지가 없으면, 결국 모두가 alert를 무시하게 된다.

---

## 핵심 개념 4: SLA는 "배치 성공"이 아니라 소비자가 기대하는 데이터 사용 가능 시각이다

데이터 파이프라인에서 SLA를 말할 때 흔한 실수가 있다.

> "우리 Airflow DAG는 매일 06:30에 성공해야 합니다."

이건 producer 관점의 job SLA다. 소비자에게 더 중요한 것은 data product SLA다.

- 대시보드는 언제 최신 날짜를 보여줄 수 있는가
- 추천 feature는 몇 분 이내의 이벤트를 반영해야 하는가
- 정산 테이블은 영업일 기준 몇 시까지 확정되어야 하는가
- 실험 분석 테이블은 지연 이벤트를 몇 일까지 보정하는가
- reverse ETL segment는 CRM 캠페인 발송 전에 준비되는가

즉 SLA는 job completion이 아니라 **데이터 사용 가능 상태**를 기준으로 잡아야 한다.

### Freshness SLA

Freshness SLA는 데이터가 얼마나 최신이어야 하는지 정의한다.

예시:

```yaml
sla:
  freshness:
    type: batch_partition_ready
    partition: business_date
    expected_ready_by: "07:00 Asia/Seoul"
    warn_after: "15m"
    breach_after: "45m"
```

streaming feature라면 다르게 쓴다.

```yaml
sla:
  freshness:
    type: event_lag
    event_time_column: occurred_at
    p95_lag_under: "5m"
    p99_lag_under: "15m"
```

여기서 평균 lag만 보면 위험하다. 대부분은 빠르게 처리되지만 일부 key나 partition만 밀리는 경우가 있기 때문이다. 사용자 경험이나 정산 영향이 tail에 민감하다면 p95, p99를 봐야 한다.

### Completeness SLA

Completeness SLA는 "제때 도착했지만 충분히 도착했는가"를 본다.

예를 들어 07:00에 파티션이 생성됐지만 row count가 평소의 10%라면, freshness는 만족했지만 completeness는 실패다.

```yaml
sla:
  completeness:
    min_partition_row_ratio_to_baseline: 0.8
    baseline_window: "same_weekday_8w"
    critical_dimensions:
      - country
      - payment_method
```

baseline을 "최근 7일 평균"으로만 잡으면 공휴일, 주말, 월말 효과에 취약할 수 있다. 실무에서는 같은 요일, 캠페인 캘린더, 영업일 여부를 고려해야 한다.

### Correctness SLA

Correctness SLA는 더 어렵다. 모든 정합성을 수치화할 수 없기 때문이다. 하지만 핵심 데이터는 최소한 허용 오차를 둬야 한다.

```yaml
sla:
  correctness:
    reconciliation:
      source: finance.settlement_daily
      metric: net_revenue
      tolerance_ratio: 0.001
      breach_after: "1 business day"
```

정산, 매출, 과금, 재고처럼 돈이나 고객 영향이 있는 데이터는 correctness SLA가 없으면 안 된다. "쿼리가 성공했다"와 "맞는 숫자다"는 완전히 다르다.

### SLA와 SLO를 구분하자

SLA는 보통 외부 약속에 가깝고, SLO는 내부 운영 목표에 가깝다.

- SLA: 매일 07:30까지 전일 매출 테이블 제공
- SLO: 월간 99% partition이 07:00 이전 준비
- SLI: partition ready time, row count completeness, reconciliation diff

계약에는 최소한 SLI와 SLO가 있어야 한다. 법적 의미의 SLA까지 과하게 만들 필요는 없지만, "정상"의 기준은 숫자로 표현되어야 한다.

---

## 핵심 개념 5: Ownership은 장애 대응을 위한 필드가 아니라 변경 권한의 기준이다

Data Contract에서 owner를 적는 이유는 장애가 났을 때 연락하려는 목적만이 아니다. 더 중요한 것은 변경 권한을 명확히 하는 것이다.

데이터에는 보통 여러 owner가 얽힌다.

- source service owner: 원천 이벤트나 DB를 만드는 팀
- data product owner: 소비 가능한 dataset을 제공하는 팀
- business owner: 지표 정의를 승인하는 팀
- platform owner: ingestion, storage, orchestration 인프라를 운영하는 팀
- consumer owner: 대시보드, ML, reverse ETL, downstream service를 운영하는 팀

이들을 모두 "데이터팀"으로 뭉뚱그리면 변경 관리가 실패한다.

예를 들어 주문 상태 enum에 새 값이 추가된다고 하자.

```text
CREATED
PAID
SHIPPED
CANCELED
RETURN_REQUESTED
RETURNED
```

이 변경은 source service owner가 가장 먼저 안다. 하지만 downstream 영향은 data product owner가 봐야 하고, 상태 정의는 business owner가 승인해야 하며, consumer owner는 새 값을 처리할 준비가 되어야 한다.

### Owner 정보에 포함할 것

계약에는 최소한 아래가 있어야 한다.

```yaml
owner:
  producer_team: commerce-platform
  data_product_team: analytics-engineering
  business_owner: revenue-operations
  oncall:
    slack: "#commerce-data-oncall"
    escalation: "PagerDuty: commerce-data"
  review_required_from:
    - analytics-engineering
    - revenue-operations
```

owner가 사람 이름 하나면 유지보수가 어렵다. 팀과 채널, escalation policy가 더 안정적이다. 사람은 이동하고 휴가를 가지만, 팀 책임은 남아야 한다.

### Consumer registry가 있어야 변경 영향 분석이 가능하다

Breaking change를 막으려면 누가 소비하는지 알아야 한다.

소비자는 자동으로 추적되는 것이 좋다.

- dbt lineage
- warehouse query log
- BI dashboard dependency
- feature store usage
- Kafka consumer group
- reverse ETL job
- notebook scheduled job

하지만 자동 추적만 믿으면 빠지는 소비자가 생긴다. 그래서 중요한 데이터 제품은 explicit consumer registry를 함께 둔다.

```yaml
consumers:
  - name: executive-revenue-dashboard
    owner: bi-team
    criticality: high
    usage: "daily KPI"
  - name: churn-model-feature-pipeline
    owner: ml-platform
    criticality: high
    usage: "weekly training and daily inference feature"
  - name: crm-vip-segment
    owner: growth
    criticality: medium
    usage: "campaign targeting"
```

이 정보가 있으면 변경 요청 시 질문이 달라진다.

- 어떤 consumer가 깨지는가
- high criticality consumer가 있는가
- deprecation window는 얼마나 필요한가
- 병행 제공이 필요한가
- backfill이 필요한가

Ownership 없는 data quality는 화재경보기만 있고 소방 책임자가 없는 상태다.

---

## 핵심 개념 6: Contract는 CI, 배포, 런타임 세 곳에서 집행되어야 한다

계약 파일만 repository에 두면 반쪽짜리다. 계약은 변경이 발생하는 지점마다 집행되어야 한다.

### 1) CI 단계: 깨지는 변경을 merge 전에 막는다

가장 먼저 필요한 것은 contract diff다.

예를 들어 pull request에서 아래 변경이 생겼다고 하자.

```diff
- amount:
-   type: integer
-   nullable: false
+ amount:
+   type: decimal(18,2)
+   nullable: false
```

CI는 이 변경을 보고 다음을 판단해야 한다.

- 타입 변경인가
- widen인가 narrow인가
- downstream parser가 허용하는가
- metric 의미가 바뀌는가
- approval label이 필요한가
- migration plan이 첨부되어 있는가

단순 YAML diff가 아니라 semantic diff가 필요하다.

```text
Change: column amount type integer -> decimal(18,2)
Risk: risky
Required:
  - data product owner approval
  - consumer notification
  - backfill/migration plan
  - contract version bump
```

CI 단계에서는 가능한 한 빠르게 막는 것이 좋다. 깨진 데이터가 운영 storage에 들어간 뒤 막는 것보다 비용이 훨씬 낮다.

### 2) 배포 단계: producer와 consumer의 순서를 통제한다

모든 변경을 한 번에 배포할 수는 없다. 특히 breaking change는 expand-contract 패턴이 필요하다.

예를 들어 `customer_id`를 `user_id`로 바꾸고 싶다면 바로 rename하지 않는다.

1. `user_id` 새 컬럼을 optional로 추가한다
2. producer가 두 컬럼을 병행 기록한다
3. downstream consumer가 `user_id`를 읽도록 바꾼다
4. usage log로 `customer_id` 소비자가 사라졌는지 확인한다
5. deprecation window 이후 `customer_id` 제거를 승인한다

계약에는 이 단계가 migration plan으로 남아야 한다.

```yaml
migration:
  type: expand_contract
  deprecated_fields:
    - customer_id
  replacement_fields:
    - user_id
  deprecation_start: 2026-06-18
  removal_not_before: 2026-08-18
  required_consumer_migration: true
```

배포 단계의 핵심은 producer가 편한 순서가 아니라 consumer가 안전한 순서다.

### 3) 런타임 단계: 실제 데이터가 계약을 지키는지 본다

CI는 코드와 명세를 본다. 하지만 운영 데이터는 더 많은 이유로 깨진다.

- source system 장애
- partial backfill
- timezone 버그
- 늦게 도착한 이벤트
- 권한 누락
- object storage 파일 누락
- scheduler 지연
- schema drift

그래서 런타임 검증이 필요하다.

런타임 집행 위치는 여러 곳이 될 수 있다.

- ingestion 직후 raw quarantine
- bronze to silver 변환 전
- mart publish 직전
- semantic layer refresh 전
- feature serving 전
- reverse ETL 전

중요한 원칙은 "나쁜 데이터를 어디까지 흘려보낼 것인가"다.

정산 테이블처럼 영향이 큰 데이터는 publish 전 block이 필요할 수 있다. 반면 내부 탐색용 raw table은 block보다 quarantine과 warning이 더 적절할 수 있다.

```text
raw ingestion: accept + quarantine bad records
silver model: block invalid schema
mart KPI: block publish on critical rule failure
dashboard: show stale badge if freshness breached
feature pipeline: fallback to previous snapshot if current partition invalid
```

계약은 이 동작을 명시해야 한다. 그렇지 않으면 장애 때마다 사람이 임의 판단을 하게 된다.

---

## 실무 예시: 주문 매출 Mart의 Data Contract 설계

이제 실제 예시로 묶어보자. 전자상거래 서비스에서 `mart.order_revenue_daily`를 제공한다고 가정한다. 이 테이블은 경영 대시보드, 정산 검증, CRM 캠페인, ML feature pipeline에서 사용한다.

### 계약 초안

```yaml
version: 1
dataset: mart.order_revenue_daily
description: "KST 기준 주문 결제일 단위의 일별 상품 매출 집계"

owner:
  producer_team: commerce-platform
  data_product_team: analytics-engineering
  business_owner: revenue-operations
  oncall: "#commerce-data-oncall"

grain:
  description: "sales_date, store_id, product_id, payment_method 단위 1 row"
  keys:
    - sales_date
    - store_id
    - product_id
    - payment_method

time_semantics:
  business_timezone: Asia/Seoul
  event_time_column: paid_at
  partition_column: sales_date
  late_arrival_policy:
    correction_window_days: 7
    publish_mode: partition_replace

columns:
  - name: sales_date
    type: date
    nullable: false
    description: "KST 기준 결제일"
  - name: store_id
    type: string
    nullable: false
  - name: product_id
    type: string
    nullable: false
  - name: payment_method
    type: string
    nullable: false
    allowed_values:
      - CARD
      - BANK_TRANSFER
      - POINT
      - COUPON
  - name: gross_revenue
    type: decimal(18,2)
    nullable: false
    unit: KRW
    description: "환불 차감 전 결제 금액"
  - name: refund_amount
    type: decimal(18,2)
    nullable: false
    unit: KRW
  - name: net_revenue
    type: decimal(18,2)
    nullable: false
    unit: KRW
    formula: "gross_revenue - refund_amount"
  - name: order_count
    type: bigint
    nullable: false

sla:
  freshness:
    expected_ready_by: "07:00 Asia/Seoul"
    warn_after: "15m"
    breach_after: "45m"
  completeness:
    min_row_ratio_to_same_weekday_8w_median: 0.8
  correctness:
    revenue_reconciliation_tolerance_ratio: 0.001

quality:
  critical:
    - unique_key:
        columns: [sales_date, store_id, product_id, payment_method]
    - not_null:
        columns: [sales_date, store_id, product_id, payment_method, net_revenue]
    - expression:
        name: net_revenue_formula
        sql: "abs(net_revenue - (gross_revenue - refund_amount)) < 0.01"
    - expression:
        name: non_negative_counts
        sql: "order_count >= 0"
  warning:
    - anomaly:
        metric: row_count
        baseline: same_weekday_8w
        warn_if_below_ratio: 0.9

compatibility:
  allow_nullable_column_addition: true
  allow_column_delete: false
  allow_column_rename: false
  require_approval_for_metric_formula_change: true
  require_backfill_plan_for_new_metric: true

consumers:
  - name: executive-revenue-dashboard
    owner: bi-team
    criticality: high
  - name: settlement-reconciliation
    owner: finance-platform
    criticality: high
  - name: crm-vip-segment
    owner: growth
    criticality: medium
```

이 계약은 길어 보이지만, 실제로는 운영 질문에 대한 답을 압축한 것이다.

- row 하나의 의미가 무엇인가
- 어떤 key가 유일해야 하는가
- 날짜 기준은 무엇인가
- 늦게 도착한 환불은 며칠까지 반영하는가
- 금액 공식은 무엇인가
- 언제까지 준비되어야 하는가
- 어떤 변경이 breaking인가
- 누가 소비하는가
- 장애가 나면 어디로 연락하는가

### 이 계약으로 막을 수 있는 실제 사고

#### 사고 1: `payment_method` enum 추가

간편결제가 추가되어 `PAYCO` 값이 들어오기 시작한다고 하자. 기존 contract에는 허용 값이 없다.

런타임 검증은 위반을 감지한다. 하지만 이것을 무조건 block해야 할까?

정답은 업무 영향에 따라 다르다.

- 경영 대시보드에서 결제 수단별 매출을 보여주면 새 값 누락은 위험하다
- 전체 매출 합계에는 영향이 없고 unknown bucket으로 처리 가능하면 warning일 수 있다
- 정산 시스템이 해당 값을 처리하지 못하면 block해야 한다

그래서 enum 추가는 기술적으로는 non-breaking처럼 보여도, semantic compatibility상 risky change로 분류하는 편이 안전하다.

#### 사고 2: 환불 반영 기준 변경

기존에는 환불을 환불일에 반영했는데, 이제 결제일로 소급 반영하기로 했다고 하자.

컬럼명과 타입은 그대로다. 하지만 `net_revenue`의 시간 의미가 바뀐다. 이는 명백한 breaking semantic change다.

이 변경에는 최소한 다음이 필요하다.

- business owner 승인
- historical backfill 범위
- 기존 dashboard 해석 변경 공지
- 지표 전환일 명시
- 두 버전 병행 제공 여부 결정
- 소비자별 영향 분석

이런 변경을 "배치 SQL 수정"으로만 다루면 몇 주 뒤 숫자가 이상하다는 신고로 돌아온다.

#### 사고 3: 새 컬럼 추가 후 과거 partition null

`discount_amount` 컬럼을 추가한다고 하자. nullable이라 schema compatibility는 통과한다. 하지만 downstream ML feature가 이 컬럼을 쓰려면 과거 학습 기간에 값이 필요하다.

따라서 계약에는 "새 metric 컬럼은 backfill plan 필요" 규칙이 있어야 한다.

```yaml
require_backfill_plan_for_new_metric: true
```

이 규칙이 없으면 최신 데이터는 정상이고 과거 학습 데이터만 silently biased 되는 문제가 생긴다.

---

## Change Management: 변경을 세 등급으로 나눠야 속도와 안전을 같이 얻는다

모든 변경에 같은 승인 절차를 적용하면 팀은 계약을 우회한다. 반대로 모든 변경을 자동 승인하면 계약의 의미가 사라진다. 실무에서는 변경을 세 등급으로 나누는 것이 좋다.

### 1) Safe Change

기존 소비자를 깨뜨릴 가능성이 낮은 변경이다.

예시:

- optional nullable column 추가
- description 보강
- owner channel 변경
- warning rule 추가
- 새 consumer 등록
- 내부 lineage metadata 추가

처리 방식:

- CI 자동 통과 가능
- owner notification만 남김
- contract version patch 증가

단, PII나 권한 관련 필드는 optional 추가라도 safe가 아니다. 새 컬럼 하나가 개인정보 노출 경로가 될 수 있다.

### 2) Risky Change

기술적으로는 호환될 수 있지만 업무 의미나 소비자 영향이 있는 변경이다.

예시:

- enum value 추가
- metric formula 변경
- nullable 컬럼이지만 핵심 소비자가 곧 사용할 예정인 컬럼 추가
- freshness SLA 완화
- anomaly threshold 완화
- late arrival correction window 변경
- partition strategy 변경 없이 backfill 범위 확대

처리 방식:

- data product owner 승인
- 주요 consumer notification
- 필요한 경우 migration note
- contract minor version 증가

Risky change를 잘 분류해야 한다. 많은 장애는 명백한 breaking change가 아니라 risky change를 safe로 착각해서 생긴다.

### 3) Breaking Change

기존 소비자가 깨지거나 의미가 바뀌는 변경이다.

예시:

- 컬럼 삭제
- 컬럼 rename
- 타입 변경
- non-null 정책 강화
- grain 변경
- key 변경
- metric 정의 변경
- timezone 변경
- 데이터 보존 기간 단축
- table replacement

처리 방식:

- owner 승인
- consumer 승인 또는 deprecation window
- migration plan
- 병행 제공 전략
- rollback plan
- contract major version 증가

Breaking change는 나쁜 것이 아니다. 필요할 때 해야 한다. 중요한 것은 "몰래" 하지 않는 것이다.

### Contract versioning 원칙

API versioning처럼 데이터 계약도 versioning이 필요하다. 하지만 모든 변경마다 새 테이블을 만들면 운영이 복잡해진다.

실용적인 기준은 다음이다.

- patch: 설명, owner, non-breaking quality rule 추가
- minor: optional field 추가, safe/risky extension
- major: grain, semantic, required field, deletion, rename 같은 breaking change

테이블 이름에 항상 `v1`, `v2`를 붙일 필요는 없다. 그러나 breaking change가 큰 경우에는 병행 제공을 위해 물리 dataset을 나누는 편이 안전하다.

```text
mart.order_revenue_daily_v1
mart.order_revenue_daily_v2
```

또는 view를 stable interface로 두고 내부 table을 교체할 수 있다. 중요한 것은 소비자가 migration할 시간을 갖는 것이다.

---

## 트레이드오프: 계약을 강하게 걸수록 안전하지만, 너무 강하면 데이터 흐름이 멈춘다

Data Contract를 도입하면 반드시 트레이드오프가 생긴다.

### 1) Strict schema vs 빠른 실험

엄격한 schema enforcement는 장애를 줄인다. 하지만 product analytics나 실험 이벤트처럼 빠르게 필드가 바뀌는 영역에서는 너무 강한 계약이 개발 속도를 막을 수 있다.

해결책은 모든 데이터에 같은 강도를 적용하지 않는 것이다.

- 결제, 정산, 과금: strict contract
- 핵심 KPI mart: strict contract
- ML serving feature: strict contract
- product analytics raw event: flexible schema + downstream normalization
- 탐색용 로그: loose contract + retention 제한

데이터 criticality별로 계약 강도를 다르게 해야 한다.

### 2) Publish block vs stale data 제공

품질 검증 실패 시 publish를 막을지, 이전 데이터를 계속 보여줄지 결정해야 한다.

정산 데이터에서 잘못된 최신 데이터를 공개하는 것보다 stale 데이터를 명시적으로 보여주는 편이 나을 수 있다. 반대로 실시간 운영 모니터링에서는 stale 데이터가 더 위험할 수 있다.

선택지는 보통 세 가지다.

- block publish: 잘못된 데이터 공개 방지
- publish with warning: 일부 품질 저하 허용
- fallback to previous snapshot: 최신성은 잃지만 안정성 확보

계약에는 dataset별 fallback 정책이 있어야 한다.

### 3) 중앙 플랫폼 통제 vs 도메인 팀 자율성

모든 계약을 데이터 플랫폼 팀이 승인하면 병목이 된다. 모든 도메인 팀이 각자 형식을 만들면 표준화가 깨진다.

현실적인 모델은 중앙 플랫폼이 형식과 자동 검증을 제공하고, 도메인 팀이 계약 내용을 소유하는 것이다.

```text
platform team:
  - contract schema
  - CI checker
  - runtime validator
  - catalog integration
  - alert routing

domain/data product team:
  - grain definition
  - business rules
  - SLA target
  - consumer communication
  - semantic change approval
```

계약은 중앙 감시 도구가 아니라 ownership을 드러내는 인터페이스여야 한다.

### 4) 모든 소비자 추적 vs 개인정보와 비용

query log, BI lineage, notebook usage를 모두 수집하면 영향 분석이 좋아진다. 하지만 개인정보, 보안, 비용 문제가 생길 수 있다.

필요한 것은 완전한 감시가 아니라 critical consumer에 대한 충분한 가시성이다.

- high criticality dataset은 explicit consumer registry 필수
- warehouse query log는 집계/마스킹해서 lineage에 사용
- 개인 notebook은 production dependency로 자동 간주하지 않음
- scheduled job과 dashboard는 dependency로 등록

무엇을 production dependency로 볼지 기준이 있어야 한다.

---

## 흔한 실수 1: 계약을 YAML 파일로만 만들고 배포 경로에 연결하지 않는다

가장 흔한 실패다. 계약 파일은 멋지게 만들어졌지만 실제 파이프라인은 그 파일을 읽지 않는다.

이 경우 몇 달 뒤 contract는 현실과 어긋난 문서가 된다.

좋은 계약은 적어도 세 지점에 연결되어야 한다.

- PR에서 contract diff를 검사한다
- ingestion 또는 transform 단계에서 runtime rule을 실행한다
- catalog와 alert에 owner, SLA, rule 결과를 노출한다

계약이 배포 경로에 없다면 운영자는 결국 실제 코드와 쿼리를 믿게 된다. 문서와 현실이 다르면 항상 현실이 이긴다.

---

## 흔한 실수 2: nullable만 보고 안전하다고 판단한다

`nullable: true`인 컬럼 추가는 대체로 안전하다. 하지만 항상 safe는 아니다.

위험한 경우:

- 컬럼이 PII다
- BI에 자동 노출된다
- 새 컬럼이 핵심 metric으로 쓰일 예정이다
- 과거 partition backfill이 없다
- null이 의미 있는 상태인지 단순 미수집인지 구분되지 않는다
- downstream이 `coalesce(new_col, 0)`으로 잘못 해석할 수 있다

nullable은 기술적 호환성 조건일 뿐이다. 의미적 안전성은 별도로 봐야 한다.

---

## 흔한 실수 3: enum 추가를 무조건 non-breaking으로 본다

이벤트 schema 관점에서 enum 추가는 소비자가 unknown value를 허용한다면 안전할 수 있다. 하지만 업무 로직에서는 그렇지 않다.

예를 들어 주문 상태에 `PARTIALLY_REFUNDED`가 추가되면 어떤 일이 생길까?

- 매출 대시보드가 이 상태를 제외할 수 있다
- 정산 로직이 환불 완료와 미완료 사이에서 잘못 분류할 수 있다
- CS 화면에서 unknown 상태로 표시될 수 있다
- ML feature가 one-hot encoding에서 새 값을 버릴 수 있다

따라서 enum 추가는 적어도 risky change로 다루는 편이 좋다. 소비자가 unknown-safe인지 확인하는 규칙이 있으면 자동 승인 범위를 넓힐 수 있다.

---

## 흔한 실수 4: Freshness만 보고 데이터가 정상이라고 판단한다

파티션이 제시간에 만들어졌다고 데이터가 맞는 것은 아니다.

정상처럼 보이는 실패:

- row count가 10%만 들어왔지만 배치는 성공
- 특정 국가 데이터만 누락
- 환불 이벤트가 늦게 도착해 net revenue 과대 계산
- source snapshot은 오래됐지만 transform은 성공
- object storage에 빈 파일이 생겼는데 downstream table은 갱신됨

Freshness, completeness, correctness는 분리해서 봐야 한다. 하나의 "DAG success" 신호로 합치면 장애를 늦게 발견한다.

---

## 흔한 실수 5: Owner를 적었지만 escalation이 없다

계약에 owner team만 있고 알림 채널, on-call, 승인자가 없으면 장애 대응이 느려진다.

좋은 owner 정보는 실행 가능해야 한다.

- 지금 alert를 보낼 채널
- 업무 시간 외 escalation
- 변경 승인자
- 소비자 공지 채널
- business definition 담당자

특히 "business definition owner"가 없으면 metric 의미 변경 때 데이터팀이 혼자 결정하게 된다. 이는 위험하다. 매출, 활성 사용자, 이탈, 재고 같은 지표는 기술 정의가 아니라 업무 정의다.

---

## 흔한 실수 6: 모든 rule을 critical로 만든다

초기에 의욕적으로 모든 품질 rule을 critical로 만들면 배포와 배치가 자주 멈춘다. 그러면 팀은 rule을 끄거나 우회한다.

Critical rule은 정말 깨진 데이터를 공개하면 안 되는 경우에만 둔다.

Critical 후보:

- primary key uniqueness
- 핵심 금액 공식
- 필수 partition 누락
- required field null 폭증
- PII masking 실패
- 권한 없는 데이터 노출

Warning 후보:

- row count의 가벼운 변동
- 신규 enum 값 탐지
- 일부 dimension coverage 저하
- 비핵심 컬럼 null 증가

Rule은 많아도 된다. 하지만 severity는 냉정해야 한다.

---

## 흔한 실수 7: Backfill을 계약 밖의 일회성 작업으로 본다

데이터 변경에서 backfill은 예외 작업이 아니라 계약 변경의 일부다.

새 metric을 추가하면 과거 기간이 어떻게 채워지는지 정해야 한다.

- 전체 과거를 backfill할 것인가
- 특정 날짜 이후만 유효한가
- 과거 null은 unknown인가 not applicable인가
- backfill 중 consumer는 어떤 테이블을 봐야 하는가
- 재처리 시 partition overwrite인가 merge인가
- backfill 결과 검증 기준은 무엇인가

이 질문이 계약에 없으면 downstream은 각자 다르게 해석한다. 특히 ML feature와 실험 분석은 과거 데이터 일관성에 민감하다.

---

## 운영 패턴: Contract를 코드 가까이에 둘 것인가, 카탈로그에 둘 것인가

Data Contract 저장 위치도 중요한 설계다.

### Repo-first 방식

계약을 producer 또는 data product repository에 둔다.

장점:

- code review와 CI에 연결하기 쉽다
- 변경 이력이 git에 남는다
- 배포와 계약 변경을 묶기 쉽다
- 개발자 워크플로에 자연스럽다

단점:

- 조직 전체 검색성이 약할 수 있다
- 여러 repo에 흩어진다
- 비개발자가 수정하기 어렵다

### Catalog-first 방식

계약을 데이터 카탈로그나 governance 플랫폼에서 관리한다.

장점:

- 검색과 소유권 관리가 쉽다
- 비개발자 참여가 쉽다
- lineage, glossary, policy와 연결하기 좋다

단점:

- CI와 배포 경로에 연결하기 어렵다
- 변경 이력과 review가 약할 수 있다
- 실제 코드와 drift가 생길 수 있다

### 현실적인 절충

실무에서는 repo-first source of truth를 두고, catalog로 publish하는 방식이 안정적이다.

```text
contract.yaml in repo
  -> CI semantic diff
  -> deploy validator
  -> publish metadata to catalog
  -> runtime quality result back to catalog
```

이렇게 하면 개발자는 git workflow를 유지하고, 소비자는 catalog에서 계약과 품질 상태를 볼 수 있다.

---

## 실무 구현 순서: 한 번에 전사 표준을 만들지 말고 핵심 데이터부터 시작한다

Data Contract는 범위가 넓기 때문에 처음부터 전사 표준을 완성하려 하면 실패하기 쉽다. 작게 시작하되, 운영에 실제로 연결해야 한다.

### 1단계: Critical dataset 선정

먼저 장애 영향이 큰 데이터 5개에서 10개를 고른다.

후보:

- 매출 mart
- 정산 테이블
- 주문 이벤트
- 사용자 dimension
- ML serving feature
- CRM segment
- 핵심 운영 대시보드 source

중요하지 않은 데이터부터 시작하면 계약의 효과를 체감하기 어렵다.

### 2단계: 최소 계약 필드 정의

처음부터 모든 rule을 넣지 않는다. 최소 필드는 다음이면 충분하다.

- owner
- grain
- key
- schema
- freshness target
- critical quality rule
- compatibility rule
- consumer list

이 정도만 있어도 운영 품질이 크게 올라간다.

### 3단계: CI diff부터 연결

런타임 검증보다 먼저 CI diff를 붙이는 편이 효과가 빠르다. breaking schema change를 merge 전에 막을 수 있기 때문이다.

초기에는 완벽한 semantic diff가 아니어도 된다.

- 컬럼 삭제 감지
- 타입 변경 감지
- nullable 강화 감지
- key 변경 감지
- grain 변경 감지
- owner 누락 감지

### 4단계: Publish gate 추가

그 다음 publish 직전에 critical rule을 실행한다.

- unique key
- not null
- row count minimum
- 금액 공식
- partition readiness

실패 시 무조건 전체 pipeline을 죽일지, 해당 partition만 quarantine할지 정해야 한다.

### 5단계: Catalog와 alert 연결

마지막으로 소비자가 볼 수 있게 만든다.

- dataset contract
- owner
- freshness 상태
- 최근 quality result
- lineage
- breaking change notice
- deprecation schedule

계약은 생산자만 보는 문서가 아니라 소비자가 신뢰를 판단하는 화면이어야 한다.

---

## 체크리스트: Data Contract를 운영에 넣기 전에 확인할 것

### 계약 내용

- row grain이 한 문장으로 명확히 적혀 있는가?
- primary key 또는 uniqueness 기준이 있는가?
- event time, processing time, business date의 차이가 설명되어 있는가?
- timezone이 명시되어 있는가?
- 핵심 metric의 공식과 단위가 적혀 있는가?
- nullable이 "모름", "해당 없음", "수집 실패" 중 무엇인지 구분되어 있는가?
- enum 값 추가와 삭제 정책이 있는가?
- PII, masking, access policy가 계약과 연결되어 있는가?

### 변경 관리

- safe, risky, breaking change 분류 기준이 있는가?
- breaking change에 deprecation window가 있는가?
- consumer approval이 필요한 조건이 명확한가?
- contract versioning 규칙이 있는가?
- backfill 계획이 필요한 변경을 구분하는가?
- rollback 또는 fallback 정책이 있는가?

### 품질과 SLA

- freshness, completeness, correctness를 분리해서 본다?
- DAG success가 아니라 data ready 시각을 측정하는가?
- row count baseline이 요일, 시즌성, 캠페인을 고려하는가?
- critical rule과 warning rule이 구분되어 있는가?
- rule 실패 시 block, quarantine, warning, fallback 중 무엇을 할지 정해져 있는가?
- stale data를 표시하거나 이전 snapshot으로 fallback하는 정책이 있는가?

### Ownership과 Lineage

- producer owner와 data product owner가 구분되어 있는가?
- business definition owner가 있는가?
- on-call 채널과 escalation이 있는가?
- high criticality consumer가 등록되어 있는가?
- warehouse query log, BI lineage, Kafka consumer group 등 실제 사용 흔적을 볼 수 있는가?
- deprecation 공지를 보낼 대상이 명확한가?

### 집행

- contract diff가 CI에서 실행되는가?
- schema drift가 ingestion 단계에서 탐지되는가?
- critical quality rule이 publish 전에 실행되는가?
- runtime result가 catalog나 dashboard에 노출되는가?
- alert가 owner에게 라우팅되는가?
- 계약 파일과 실제 테이블 schema 사이 drift를 정기적으로 검사하는가?

---

## 한 줄 정리

Data Contract는 데이터 스키마 문서가 아니라, **데이터 변경의 영향 범위를 배포 전에 드러내고 운영 중 위반을 행동 가능한 신호로 바꾸는 생산자와 소비자 사이의 실행 계약**이다.

