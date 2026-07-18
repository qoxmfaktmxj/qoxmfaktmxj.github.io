---
layout: post
title: "PostgreSQL Logical Replication 실전: Publication, Subscription, Replica Identity, Slot Lag, Initial Sync로 데이터 분배를 운영하는 법"
date: 2026-07-18 11:50:00 +0900
categories: [sql]
tags: [study, sql, postgresql, logical-replication, publication, subscription, replica-identity, replication-slot, wal, initial-sync, operations]
permalink: /sql/2026/07/18/study-postgresql-logical-replication-publication-subscription-replica-identity-slot-lag-initial-sync.html
---

## 배경: 읽기 복제와 이벤트 스트리밍 사이에는 "논리 복제"라는 운영 경계가 있다

PostgreSQL 운영을 하다 보면 처음에는 primary 하나와 read replica 몇 대로 충분하다. 조회 부하를 replica로 빼고, 장애 시 replica를 승격할 수 있으면 꽤 안정적인 구조처럼 보인다. 하지만 서비스가 커지면 단순한 physical streaming replication만으로는 풀기 어려운 요구가 생긴다.

- 특정 테이블만 다른 DB로 복제하고 싶다.
- 결제, 정산, 검색, 분석 시스템에 필요한 컬럼만 안정적으로 전달하고 싶다.
- 운영 DB 전체를 넘기지 않고 멀티테넌트 데이터 일부만 분리하고 싶다.
- PostgreSQL 메이저 버전 업그레이드나 마이그레이션을 긴 중단 없이 진행하고 싶다.
- CDC 도구 없이도 PostgreSQL 내부 기능으로 row 변경을 다른 PostgreSQL에 흘리고 싶다.
- replica는 필요하지만 인덱스, 권한, 스키마, 테이블 집합을 source와 다르게 운영하고 싶다.
- streaming replica처럼 byte-for-byte 복제는 싫고, 테이블 단위의 명시적 계약이 필요하다.

이때 등장하는 기능이 **Logical Replication**이다. 이름 그대로 WAL에 남은 변경을 물리적 블록 단위가 아니라 논리적 row 변경으로 해석해서 다른 PostgreSQL로 전달한다.

하지만 논리 복제는 "복제 켜기" 기능이 아니다. 운영에서 제대로 쓰려면 publication, subscription, replication slot, replica identity, initial table sync, DDL 전파, conflict, lag, WAL retention, failover까지 함께 이해해야 한다. 특히 중급 이상 개발자가 놓치기 쉬운 지점은 이것이다.

> Logical Replication은 데이터 복사 도구가 아니라 **테이블 단위 변경 스트림을 장기 운영하는 계약**이다.

이 관점이 없으면 시작은 쉽지만 운영은 어려워진다. `CREATE PUBLICATION`과 `CREATE SUBSCRIPTION`만으로 데모는 금방 된다. 그러나 실제 서비스에서는 아래 문제가 곧바로 나타난다.

- 구독자가 멈춘 동안 source의 `pg_wal`이 계속 커진다.
- `UPDATE`와 `DELETE`가 되지 않고 replica identity 오류가 난다.
- 초기 복사 중 테이블이 너무 커서 source와 target 양쪽에 부하가 생긴다.
- DDL은 자동 전파되지 않아 어느 날 replication worker가 깨진다.
- target에 unique constraint가 달라서 apply conflict가 발생한다.
- 구독 DB가 느려져 slot lag가 커지고, 어느 순간 source 디스크가 위험해진다.
- schema 변경, backfill, bulk update가 logical replication lag를 폭발시킨다.

이번 글은 Logical Replication의 문법 소개가 아니다. 운영에서 "이 기능을 어디까지 믿고, 어디서부터 설계 책임을 져야 하는가"를 정리한다.

오늘 다룰 질문은 아래와 같다.

1. Logical Replication은 physical replication, CDC Outbox, dump/restore와 무엇이 다른가?
2. Publication과 Subscription은 어떤 계약을 만들고, 어떤 것은 계약하지 않는가?
3. Replication Slot은 왜 필요하며, 왜 source 디스크를 터뜨릴 수 있는가?
4. Replica Identity는 `UPDATE`와 `DELETE` 복제에서 왜 결정적인가?
5. Initial sync는 어떤 순서로 일어나며, 대용량 테이블에서 무엇을 조심해야 하는가?
6. DDL, constraint, sequence, trigger, partition table은 어떤 운영 함정을 갖는가?
7. Lag와 conflict를 어떤 뷰로 관측하고, 장애 시 어떤 순서로 대응해야 하는가?
8. 실무에서 Logical Replication을 도입하기 전 체크리스트는 무엇인가?

핵심 결론부터 압축하면 이렇다.

1. Logical Replication은 PostgreSQL 간 테이블 단위 변경 복제에 강하지만, 전체 DB를 완전히 동일하게 유지하는 기능은 아니다.
2. Publication은 "무엇을 내보낼지", Subscription은 "어디서 받아 어떻게 적용할지"를 정하는 계약이다.
3. Replication Slot은 consumer가 읽어야 할 WAL을 보존하므로, subscriber가 멈추면 source의 WAL retention 문제가 된다.
4. `UPDATE`와 `DELETE`를 안정적으로 복제하려면 primary key 또는 적절한 `REPLICA IDENTITY`가 필수다.
5. Initial sync는 단순 복사가 아니라 snapshot, copy worker, apply worker, 동시 변경 catch-up이 겹치는 부하 이벤트다.
6. DDL, sequence 값, 권한, 인덱스, trigger 동작은 자동으로 "운영 의도대로" 맞춰지지 않는다.
7. 좋은 설계는 복제 성공보다 **복제 지연, 재시작, 충돌, 재동기화, 중단 가능한 배포 절차**를 먼저 정의한다.

---

## 먼저 큰 그림: Physical Replication과 Logical Replication은 목적이 다르다

PostgreSQL 복제를 이야기할 때 가장 먼저 구분해야 할 것은 physical replication과 logical replication이다.

Physical streaming replication은 primary의 WAL을 블록 수준으로 replica에 재생한다. 결과적으로 replica는 primary와 거의 같은 데이터 디렉터리 상태를 유지한다. 보통 read replica, hot standby, HA 구성을 위해 쓴다.

Logical replication은 WAL을 논리적 변경 이벤트로 해석한다.

```text
source table row change
  -> WAL
  -> logical decoding
  -> publication
  -> replication slot
  -> subscription worker
  -> target table INSERT/UPDATE/DELETE
```

즉 physical replication이 "서버 전체 상태를 따라가는 복제"에 가깝다면, logical replication은 "선택한 테이블의 row 변경을 target에 적용하는 복제"에 가깝다.

### Physical replication이 맞는 경우

아래 요구라면 보통 physical replication이 먼저다.

- read replica를 만들고 싶다.
- primary 장애 시 빠르게 승격할 standby가 필요하다.
- 전체 DB를 동일하게 유지하고 싶다.
- DDL, sequence, extension, system catalog까지 source와 동일하게 따라가야 한다.
- 복제본에서 임의 쓰기는 필요 없다.

Physical replica는 source와 강하게 묶인다. 대신 운영자가 이해해야 할 계약이 비교적 명확하다. 같은 클러스터 계열의 byte stream을 따라가며, standby는 기본적으로 읽기 전용이다.

### Logical replication이 맞는 경우

아래 요구라면 logical replication을 검토할 만하다.

- 특정 테이블만 복제하고 싶다.
- target DB에서 별도 인덱스나 권한을 운영하고 싶다.
- 버전 업그레이드나 DB 분리 마이그레이션을 점진적으로 하고 싶다.
- 일부 테이블은 source에서 target으로, 다른 일부는 다른 경로로 이동시키고 싶다.
- source 전체를 노출하지 않고 필요한 데이터 집합만 전달하고 싶다.
- target에서 조회 전용 모델, 검색용 모델, 정산용 모델을 만들고 싶다.

하지만 logical replication은 자유도가 높은 만큼 계약이 느슨하다. 테이블 구조, constraint, sequence, DDL, 트리거, 충돌 처리, slot lag를 운영자가 직접 다뤄야 한다.

정리하면 이렇다.

```text
Physical replication
  - 서버 전체 상태를 강하게 따라간다
  - HA와 read replica에 적합하다
  - target을 source와 다르게 운영하기 어렵다

Logical replication
  - 테이블 단위 변경을 선택적으로 전달한다
  - 마이그레이션, 데이터 분배, 일부 테이블 복제에 적합하다
  - 스키마와 운영 계약을 직접 관리해야 한다
```

Logical Replication을 "더 유연한 read replica"라고 이해하면 위험하다. 더 정확히는 **PostgreSQL 내장 CDC에 가까운 테이블 변경 적용 시스템**이다.

---

## 핵심 개념 1: Publication은 "내보낼 변경 집합"을 정의한다

Logical Replication의 source 쪽 핵심 객체는 publication이다. Publication은 어떤 테이블의 어떤 변경을 내보낼지 정의한다.

가장 단순한 형태는 아래와 같다.

```sql
CREATE PUBLICATION app_pub
FOR TABLE orders, payments, customers;
```

기본적으로 publication은 `INSERT`, `UPDATE`, `DELETE`, `TRUNCATE` 변경을 내보낼 수 있다. 필요하면 작업 종류를 제한할 수 있다.

```sql
CREATE PUBLICATION order_insert_pub
FOR TABLE orders
WITH (publish = 'insert');
```

이 설정은 target에 과거 상태 동기화보다 append-only 적재가 필요한 경우에 쓸 수 있다. 하지만 대부분의 운영 복제에서는 update와 delete까지 포함할지 신중하게 판단해야 한다.

### Publication은 테이블 집합 계약이다

Publication을 만들 때 가장 중요한 질문은 "무엇을 복제할 것인가"가 아니라 "무엇을 복제하지 않을 것인가"다.

예를 들어 주문 도메인에서 아래 테이블이 있다고 하자.

```text
orders
order_items
payments
payment_attempts
refunds
coupons
audit_logs
internal_job_locks
```

정산 DB로 보낼 publication에 `orders`, `payments`, `refunds`만 넣으면 될까? 아닐 수 있다. 정산 계산에 `order_items`의 금액, 할인, 세율이 필요하면 함께 가야 한다. 반대로 `internal_job_locks`는 복제하면 target에서 의미 없는 잡음이 된다.

Publication 설계는 테이블 목록 작성이 아니라 **도메인 읽기 모델의 경계 정의**다.

### `FOR ALL TABLES`는 편하지만 계약이 너무 넓다

PostgreSQL은 모든 테이블을 publication에 포함하는 방식도 제공한다.

```sql
CREATE PUBLICATION all_tables_pub
FOR ALL TABLES;
```

마이그레이션 초기 검증이나 통제된 내부 환경에서는 유용할 수 있다. 하지만 운영에서 장기적으로 쓰기에는 위험한 경우가 많다.

- 새 테이블이 의도치 않게 복제 대상이 될 수 있다.
- 개인정보나 내부 운영 테이블이 target으로 흘러갈 수 있다.
- target에 없는 테이블 때문에 subscription apply가 실패할 수 있다.
- 복제 범위가 넓어져 lag와 WAL retention 비용이 커진다.
- 팀이 publication을 데이터 계약으로 인식하기 어렵다.

가능하면 장기 운영 publication은 명시적 테이블 목록으로 시작하는 편이 낫다.

```sql
CREATE PUBLICATION settlement_pub
FOR TABLE
  orders,
  order_items,
  payments,
  refunds;
```

### Row filter와 column list는 강력하지만 더 강한 계약 관리가 필요하다

최신 PostgreSQL에서는 publication에 row filter나 column list를 사용할 수 있다. 예를 들어 특정 tenant만 내보내거나, 필요한 컬럼만 내보내는 방식이다.

```sql
CREATE PUBLICATION tenant_42_pub
FOR TABLE orders
WHERE (tenant_id = 42);
```

또는 컬럼을 제한할 수 있다.

```sql
CREATE PUBLICATION customer_public_pub
FOR TABLE customers (id, tenant_id, display_name, updated_at);
```

이 기능은 데이터 최소화와 보안 경계에 좋다. 하지만 운영 복잡도도 커진다.

- filter 조건이 바뀌면 target 데이터의 의미가 바뀐다.
- target에 이미 복제된 row가 filter 밖으로 나갈 때 어떻게 처리할지 판단해야 한다.
- column list에서 빠진 컬럼은 target에서 source와 다르게 관리될 수 있다.
- 애플리케이션이 "복제본에는 모든 컬럼이 있다"고 가정하면 장애가 난다.

즉 publication filter는 단순 성능 옵션이 아니다. **데이터 계약의 일부**다. 문서화, 변경 절차, 검증 쿼리가 함께 있어야 한다.

---

## 핵심 개념 2: Subscription은 target의 apply 계약이다

Target 쪽 핵심 객체는 subscription이다. Subscription은 source에 접속해서 publication 변경을 받아 target table에 적용한다.

```sql
CREATE SUBSCRIPTION app_sub
CONNECTION 'host=source-db port=5432 dbname=app user=repl_user password=...'
PUBLICATION app_pub;
```

이 명령을 실행하면 target PostgreSQL은 source에 접속하고, 필요한 경우 replication slot을 만들고, publication 대상 테이블을 초기 복사한 뒤, 이후 변경을 apply worker로 계속 적용한다.

### Subscription은 target schema를 만들어주지 않는다

초보자가 가장 자주 하는 오해가 이것이다.

> Publication에 테이블이 있으니 subscription을 만들면 target 테이블도 자동 생성되겠지.

그렇지 않다. Logical Replication은 target의 테이블 구조를 자동으로 만들어주는 마이그레이션 도구가 아니다. Target에는 복제 받을 테이블이 미리 있어야 한다.

예를 들어 source에 아래 테이블이 있다.

```sql
CREATE TABLE orders (
  id BIGINT PRIMARY KEY,
  tenant_id BIGINT NOT NULL,
  status TEXT NOT NULL,
  total_amount NUMERIC(18, 2) NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL
);
```

Target에도 compatible한 테이블이 필요하다.

```sql
CREATE TABLE orders (
  id BIGINT PRIMARY KEY,
  tenant_id BIGINT NOT NULL,
  status TEXT NOT NULL,
  total_amount NUMERIC(18, 2) NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL
);
```

컬럼 순서까지 완전히 같을 필요는 없지만, 복제되는 컬럼을 target이 받아들일 수 있어야 한다. 타입, not null, default, constraint, generated column, identity column, trigger가 섞이면 검증해야 할 것이 늘어난다.

### Target은 source와 달라도 되지만, 달라지는 이유가 명확해야 한다

Logical replication의 장점 중 하나는 target을 source와 다르게 설계할 수 있다는 점이다.

예를 들어 source는 OLTP 쓰기에 최적화되어 있고 target은 조회에 최적화되어 있을 수 있다.

```sql
-- source에는 없는 조회용 인덱스를 target에만 만든다
CREATE INDEX idx_orders_settlement_status_date
ON orders (status, updated_at DESC)
WHERE status IN ('PAID', 'REFUNDED');
```

이 방식은 유용하다. Source의 쓰기 경로에 인덱스 비용을 추가하지 않고 target 조회를 빠르게 만들 수 있다. 하지만 target이 source와 달라질수록 운영 질문도 늘어난다.

- target constraint가 source보다 엄격하면 apply conflict가 날 수 있다.
- target trigger가 실행되면 복제 apply가 의도치 않은 부작용을 만들 수 있다.
- target default가 source와 달라도 복제 컬럼이 명시되면 default가 적용되지 않을 수 있다.
- target partition 구조가 source와 다르면 routing과 constraint를 따로 검증해야 한다.

좋은 기준은 단순하다.

> Target schema는 source와 달라도 되지만, 차이는 모두 의도적이어야 하고 apply 실패 가능성을 테스트해야 한다.

### Subscription 옵션은 "처음 복사할지"와 "slot을 어떻게 만들지"를 결정한다

Subscription 생성 시 자주 중요한 옵션이 있다.

```sql
CREATE SUBSCRIPTION app_sub
CONNECTION 'host=source-db dbname=app user=repl_user password=...'
PUBLICATION app_pub
WITH (
  copy_data = true,
  create_slot = true,
  enabled = true,
  slot_name = 'app_sub_slot'
);
```

`copy_data = true`는 publication 대상 테이블의 기존 데이터를 target으로 초기 복사한다. `false`로 두면 기존 row는 복사하지 않고, subscription 이후 발생한 변경만 받는다.

마이그레이션에서는 보통 `copy_data = true`가 필요하다. 반면 이미 dump/restore나 다른 방식으로 target을 채워두고 변경 catch-up만 하고 싶다면 `copy_data = false`를 고려할 수 있다.

`create_slot = true`는 source에 replication slot을 자동 생성한다. 운영에서는 slot 이름을 명시하는 편이 좋다. 그래야 모니터링, 알림, 장애 대응 문서에서 정확한 객체를 지칭할 수 있다.

---

## 핵심 개념 3: Replication Slot은 안정성을 주지만 source 디스크를 위험하게 만들 수 있다

Logical Replication에서 replication slot은 매우 중요하다. Slot은 source가 "이 consumer가 어디까지 WAL을 읽었는지" 기억하는 장치다.

Slot이 없으면 subscriber가 잠시 끊긴 동안 source가 필요한 WAL을 제거해버릴 수 있다. 그러면 subscriber는 놓친 변경을 복구할 방법이 없다. Slot이 있으면 source는 subscriber가 아직 읽지 않은 WAL을 보존한다.

문제는 바로 그 장점에서 나온다.

> Subscriber가 오래 멈추면 source는 WAL을 계속 보존하고, 결국 `pg_wal` 디스크를 압박한다.

이것은 버그가 아니라 slot의 본질이다. Slot은 consumer의 복구 가능성을 위해 source의 저장 공간을 담보로 잡는다.

### Slot lag는 "subscriber가 느리다"를 넘어 "source가 WAL을 버리지 못한다"는 뜻이다

Source에서 slot 상태를 확인할 때는 `pg_replication_slots`를 본다.

```sql
SELECT
  slot_name,
  plugin,
  slot_type,
  active,
  restart_lsn,
  confirmed_flush_lsn,
  pg_size_pretty(
    pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)
  ) AS retained_wal
FROM pg_replication_slots
WHERE slot_type = 'logical';
```

여기서 `retained_wal`이 커진다는 것은 source가 해당 slot 때문에 오래된 WAL을 지우지 못하고 있다는 뜻이다.

상황별 해석은 다르다.

- `active = true`인데 retained WAL이 계속 커진다: subscriber가 연결은 되어 있지만 apply 속도가 source WAL 생성 속도를 못 따라간다.
- `active = false`이고 retained WAL이 커진다: subscriber가 끊겼거나 subscription이 멈췄다.
- 특정 slot 하나만 크다: 해당 consumer만 병목이다.
- 모든 slot이 같이 커진다: source 쓰기 폭증, network, target I/O, 공통 인프라 문제를 의심한다.

### `max_slot_wal_keep_size`는 보험이지 설계가 아니다

PostgreSQL에는 slot이 무한정 WAL을 붙잡지 못하도록 제한하는 설정이 있다.

```conf
max_slot_wal_keep_size = '20GB'
```

이 설정은 source 디스크를 보호하는 데 도움이 된다. 하지만 subscriber 관점에서는 위험한 결과를 만든다. 제한을 넘어서 필요한 WAL이 제거되면 해당 slot의 consumer는 더 이상 이어받지 못하고 재초기화가 필요할 수 있다.

따라서 이 값은 "장애를 막는 완전한 해결책"이 아니라 "source 디스크 전체 장애를 피하기 위한 마지막 가드레일"이다.

실무 기준은 아래에 가깝다.

- slot별 retained WAL 경고를 둔다.
- subscriber 중단 허용 시간을 계산한다.
- source의 최대 WAL 생성량을 피크 기준으로 추정한다.
- `max_slot_wal_keep_size`는 계산된 복구 시간보다 조금 큰 값이 아니라, source 생존을 우선하는 값으로 둔다.
- 제한 초과 시 재동기화 절차를 문서화한다.

예를 들어 source가 피크 시간에 50GB/hour WAL을 만들고, subscriber를 최대 2시간 중단할 수 있어야 한다면 단순 계산으로 100GB 이상이 필요하다. 하지만 source 디스크가 200GB뿐이라면 이 요구는 구조적으로 불가능하다. 이때는 디스크 증설, 쓰기 피크 조정, subscriber 성능 개선, 복제 범위 축소, 별도 CDC 인프라를 검토해야 한다.

### 사용하지 않는 slot은 반드시 제거해야 한다

Logical replication 테스트 후 slot을 남겨두는 실수는 위험하다. 사용하지 않는 inactive slot도 WAL을 붙잡을 수 있다.

```sql
SELECT slot_name, active
FROM pg_replication_slots
WHERE slot_type = 'logical';
```

정말 사용하지 않는 slot이라면 제거한다.

```sql
SELECT pg_drop_replication_slot('old_test_slot');
```

다만 운영 slot을 잘못 제거하면 subscriber가 이어받을 수 없게 된다. 삭제 전에는 subscription, 모니터링, 장애 대응 문서를 확인해야 한다.

---

## 핵심 개념 4: Replica Identity는 UPDATE와 DELETE의 주소표다

Logical Replication에서 `INSERT`는 비교적 단순하다. 새 row를 target에 넣으면 된다. 하지만 `UPDATE`와 `DELETE`는 target에서 어떤 row를 바꿀지 찾아야 한다.

이때 필요한 것이 **Replica Identity**다.

기본적으로 PostgreSQL은 primary key를 replica identity로 사용한다. Primary key가 있으면 update/delete 변경 이벤트에 key 정보가 포함되고, subscriber는 target에서 해당 row를 찾아 적용할 수 있다.

```sql
CREATE TABLE orders (
  id BIGINT PRIMARY KEY,
  status TEXT NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL
);
```

이 테이블은 별도 설정 없이 update/delete 복제가 가능하다.

문제는 primary key가 없는 테이블이다.

```sql
CREATE TABLE audit_events (
  event_time TIMESTAMPTZ NOT NULL,
  actor_id BIGINT NOT NULL,
  action TEXT NOT NULL,
  payload JSONB NOT NULL
);
```

이 테이블에 update/delete가 발생하면 logical replication은 target row를 식별할 안정적인 키가 없다. 이때 오류가 날 수 있다.

### 선택지 1: Primary key를 둔다

가장 좋은 해결책은 복제 대상 테이블에 primary key를 두는 것이다.

```sql
ALTER TABLE audit_events
ADD COLUMN id BIGSERIAL PRIMARY KEY;
```

운영 테이블에서 primary key는 복제뿐 아니라 애플리케이션 동시성, 디버깅, 데이터 정정, 감사에도 도움이 된다. "append-only라서 primary key가 없어도 된다"는 판단은 장기 운영에서 자주 비용으로 돌아온다.

### 선택지 2: Unique index를 replica identity로 지정한다

Primary key를 만들기 어렵지만 unique index가 있다면 replica identity로 지정할 수 있다.

```sql
CREATE UNIQUE INDEX uq_audit_events_natural
ON audit_events (event_time, actor_id, action);

ALTER TABLE audit_events
REPLICA IDENTITY USING INDEX uq_audit_events_natural;
```

단, 이 index는 nullable 컬럼 문제와 실제 유일성을 주의해야 한다. 업무적으로 "대충 유일할 것"은 replica identity로 쓰기 어렵다. Target에서 row를 정확히 찾지 못하면 apply 오류나 잘못된 변경으로 이어진다.

### 선택지 3: `REPLICA IDENTITY FULL`을 쓴다

마지막 선택지로 전체 row 이전 값을 식별 정보로 보내는 방식이 있다.

```sql
ALTER TABLE audit_events REPLICA IDENTITY FULL;
```

이 설정은 primary key가 없어도 update/delete를 복제할 수 있게 해준다. 하지만 비용이 크다.

- 변경 이벤트가 커진다.
- WAL 양이 늘 수 있다.
- Target에서 row를 찾는 비용이 커진다.
- JSONB, TEXT, 큰 컬럼이 있으면 부담이 급격히 커진다.
- 동일 row 식별이 비효율적이고 conflict 분석도 어려워진다.

따라서 `REPLICA IDENTITY FULL`은 "편한 해결책"이 아니라 "키를 설계하지 못한 비용을 WAL과 apply 성능으로 지불하는 선택"에 가깝다.

### Append-only 테이블도 정책을 명확히 해야 한다

"우리는 이 테이블에 insert만 하니까 replica identity가 필요 없다"고 말할 수 있다. 기술적으로는 맞을 수 있다. 하지만 운영에서는 다음 질문을 해야 한다.

- 정말 update/delete가 영원히 없는가?
- 잘못 들어간 데이터를 정정할 때는 어떻게 할 것인가?
- retention delete가 필요한가?
- partition detach/drop으로만 정리할 것인가?
- 향후 backfill이 update로 들어올 가능성은 없는가?

Append-only 계약이 명확하면 publication에서 insert만 내보내는 것도 방법이다.

```sql
CREATE PUBLICATION audit_insert_pub
FOR TABLE audit_events
WITH (publish = 'insert');
```

이렇게 하면 update/delete 복제 요구를 애초에 제외한다. 중요한 것은 암묵적 기대가 아니라 명시적 계약이다.

---

## 핵심 개념 5: Initial Sync는 "처음 한 번 복사"가 아니라 가장 큰 부하 이벤트다

Subscription을 만들 때 `copy_data = true`면 target은 publication 대상 테이블의 기존 데이터를 복사한다. 이를 initial table synchronization이라고 볼 수 있다.

작은 테이블에서는 별일 아니다. 하지만 수천만, 수억 row 테이블에서는 initial sync 자체가 운영 이벤트다.

### Initial sync에서 벌어지는 일

단순화하면 흐름은 아래와 같다.

1. Subscription이 생성된다.
2. Source에 logical replication slot이 만들어진다.
3. 대상 테이블별로 초기 복사 worker가 source에서 데이터를 읽어 target에 적재한다.
4. 복사 중 source에서 발생한 변경은 WAL과 slot을 통해 보존된다.
5. 초기 복사가 끝나면 table sync worker가 catch-up하고, main apply worker가 이후 변경을 적용한다.

이 구조에서 중요한 점은 초기 복사가 오래 걸릴수록 source의 WAL 보존 압력이 커질 수 있다는 것이다. 복사 중에도 source는 계속 쓰기를 받고, subscriber가 아직 적용하지 못한 변경은 slot 뒤에 쌓인다.

### 대용량 테이블 initial sync의 위험

대용량 테이블을 복제할 때 흔한 장애 모드는 아래와 같다.

- Source에서 긴 sequential scan이 발생해 I/O가 증가한다.
- Target에서 대량 insert와 index maintenance 때문에 write latency가 커진다.
- Target 인덱스가 많으면 초기 적재가 매우 느려진다.
- Source 쓰기량이 많아 slot retained WAL이 빠르게 증가한다.
- Table sync worker가 실패하고 재시도하면서 부하가 반복된다.
- 중간에 DDL이 바뀌어 복제가 깨진다.
- Target constraint가 source 데이터와 맞지 않아 복사 도중 실패한다.

따라서 큰 테이블은 "일단 subscription 만들고 보자"가 아니라 사전 리허설이 필요하다.

### 실무 접근: 먼저 schema, constraint, 용량, 쓰기량을 계산한다

Initial sync 전에 최소한 아래를 확인한다.

```sql
SELECT
  relname,
  n_live_tup,
  pg_size_pretty(pg_total_relation_size(relid)) AS total_size
FROM pg_stat_user_tables
WHERE relname IN ('orders', 'order_items', 'payments')
ORDER BY pg_total_relation_size(relid) DESC;
```

그리고 테이블별 쓰기량과 WAL 생성량을 본다.

```sql
SELECT
  now() AS measured_at,
  pg_current_wal_lsn() AS current_lsn;
```

운영에서는 일정 간격으로 LSN 차이를 재서 피크 WAL 생성량을 추정한다.

```sql
SELECT pg_size_pretty(
  pg_wal_lsn_diff('0/8000000'::pg_lsn, '0/4000000'::pg_lsn)
);
```

정확한 숫자보다 중요한 것은 감이다. "이 테이블은 4시간 복사될 수 있고, 피크 시간에는 시간당 30GB WAL이 생긴다"면 source는 최소 120GB 이상의 slot 보존 압력을 받을 수 있다. 여기에 기존 replica, archive, checkpoint 여유까지 더해야 한다.

### Target index 전략: 처음부터 모든 인덱스를 만들지 말지 판단한다

Target에 인덱스가 많으면 initial sync가 느려질 수 있다. 대량 insert 중에는 인덱스 maintenance가 계속 발생하기 때문이다. 경우에 따라서는 target 테이블을 먼저 최소 인덱스로 만들고, 초기 복사 후 필요한 조회 인덱스를 `CREATE INDEX CONCURRENTLY`로 추가하는 전략을 쓴다.

하지만 이 선택도 트레이드오프가 있다.

- 인덱스가 없으면 초기 적재는 빠르다.
- 초기 적재 후 인덱스 생성은 별도 시간이 걸린다.
- apply worker가 update/delete를 적용하려면 target에서 row를 찾을 key index가 필요하다.
- unique constraint가 없으면 잘못된 중복이 늦게 발견될 수 있다.

실무에서는 primary key와 apply에 필요한 최소 constraint는 유지하고, 조회 최적화용 보조 인덱스는 초기 적재 후 추가하는 방식을 많이 검토한다.

### `copy_data = false`는 빠르지만 위험한 선택이다

이미 target에 데이터를 채워두었다면 아래처럼 기존 데이터 복사를 건너뛸 수 있다.

```sql
CREATE SUBSCRIPTION app_sub
CONNECTION 'host=source-db dbname=app user=repl_user password=...'
PUBLICATION app_pub
WITH (copy_data = false, slot_name = 'app_sub_slot');
```

이 방식은 마이그레이션에서 유용하다. 예를 들어 `pg_dump`, snapshot restore, storage-level copy로 target을 준비한 뒤 logical replication으로 변경분만 따라잡게 할 수 있다.

하지만 매우 중요한 조건이 있다.

> Target의 시작 데이터가 source의 어느 시점과 일치하는지 알아야 한다.

그 기준점이 없으면 누락이나 중복을 검증할 수 없다. `copy_data = false`는 "복사를 생략하니 편하다"가 아니라 "초기 데이터 일치성을 다른 절차로 보장했다"는 선언이어야 한다.

---

## 실무 예시 1: 정산용 PostgreSQL로 주문 데이터 일부 복제하기

서비스 DB가 있고, 정산 팀이 별도 PostgreSQL에서 주문과 결제 데이터를 조회해야 한다고 하자. API로 매번 source를 조회하면 운영 DB 부하가 커지고, 배치 dump는 지연이 너무 길다. 이때 logical replication으로 정산용 DB를 구성할 수 있다.

### Source schema

```sql
CREATE TABLE orders (
  id BIGINT PRIMARY KEY,
  tenant_id BIGINT NOT NULL,
  order_no TEXT NOT NULL,
  status TEXT NOT NULL,
  total_amount NUMERIC(18, 2) NOT NULL,
  ordered_at TIMESTAMPTZ NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE payments (
  id BIGINT PRIMARY KEY,
  order_id BIGINT NOT NULL,
  status TEXT NOT NULL,
  paid_amount NUMERIC(18, 2) NOT NULL,
  approved_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE refunds (
  id BIGINT PRIMARY KEY,
  payment_id BIGINT NOT NULL,
  status TEXT NOT NULL,
  refunded_amount NUMERIC(18, 2) NOT NULL,
  requested_at TIMESTAMPTZ NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL
);
```

정산에는 이 세 테이블만 필요하다고 판단했다. Source에 publication을 만든다.

```sql
CREATE PUBLICATION settlement_pub
FOR TABLE orders, payments, refunds;
```

### Target schema

Target에는 같은 컬럼을 받아들일 수 있는 테이블을 만든다. 그리고 정산 조회에 맞춘 인덱스를 추가한다.

```sql
CREATE TABLE orders (
  id BIGINT PRIMARY KEY,
  tenant_id BIGINT NOT NULL,
  order_no TEXT NOT NULL,
  status TEXT NOT NULL,
  total_amount NUMERIC(18, 2) NOT NULL,
  ordered_at TIMESTAMPTZ NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX idx_orders_settlement_date
ON orders (ordered_at DESC, tenant_id)
WHERE status IN ('PAID', 'REFUNDED', 'CANCELED');
```

Source에는 이 partial index가 없을 수 있다. 정산 DB의 조회 패턴에만 필요하기 때문이다. 이 점이 logical replication의 장점이다.

### Subscription 생성

```sql
CREATE SUBSCRIPTION settlement_sub
CONNECTION 'host=source-db port=5432 dbname=app user=settlement_repl password=...'
PUBLICATION settlement_pub
WITH (
  slot_name = 'settlement_sub_slot',
  copy_data = true,
  create_slot = true,
  enabled = true
);
```

이후 target에서 상태를 확인한다.

```sql
SELECT
  subname,
  status,
  received_lsn,
  latest_end_lsn,
  last_msg_send_time,
  last_msg_receipt_time
FROM pg_stat_subscription;
```

Source에서는 slot retained WAL을 확인한다.

```sql
SELECT
  slot_name,
  active,
  pg_size_pretty(
    pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)
  ) AS retained_wal
FROM pg_replication_slots
WHERE slot_name = 'settlement_sub_slot';
```

### 이 설계에서 중요한 운영 질문

정산 DB는 조회용이라고 해도 완전한 복제본은 아니다. 운영 계약을 분명히 해야 한다.

- 정산 화면은 몇 분 지연까지 허용하는가?
- 지연이 10분을 넘으면 화면을 막을 것인가, 지연 배지를 보여줄 것인가?
- source에서 DDL이 바뀔 때 target schema는 누가 먼저 반영하는가?
- target에서 임의로 데이터를 수정해도 되는가?
- 정산 DB 장애 시 source 디스크 보호를 위해 subscription을 disable할 것인가, slot을 drop할 것인가?
- 재초기화가 필요한 경우 어느 시간대에, 어떤 순서로 진행할 것인가?

Logical replication은 데이터를 전달하지만, 운영 의미는 팀이 정해야 한다.

---

## 실무 예시 2: PostgreSQL 메이저 버전 업그레이드를 logical replication으로 준비하기

Logical replication은 PostgreSQL 메이저 버전 업그레이드에도 자주 쓰인다. 예를 들어 PostgreSQL 15에서 17로 옮기고 싶지만 긴 중단이 어렵다고 하자.

전략은 대략 이렇다.

1. 새 버전 PostgreSQL cluster를 준비한다.
2. Source schema를 target에 반영한다.
3. Source에 publication을 만든다.
4. Target에 subscription을 만들고 초기 복사한다.
5. Application dual-read 또는 shadow validation을 수행한다.
6. Lag가 충분히 작아지면 쓰기를 잠시 멈춘다.
7. 마지막 LSN까지 catch-up했는지 확인한다.
8. Application connection을 target으로 전환한다.
9. 일정 기간 source를 보존하고 rollback 계획을 유지한다.

이 방식은 downtime을 줄일 수 있지만, "무중단 업그레이드"라는 말처럼 간단하지 않다.

### DDL과 extension은 직접 맞춰야 한다

Logical replication은 DDL을 자동으로 target에 적용하지 않는다. Source에서 아래처럼 컬럼을 추가한다고 target이 자동으로 바뀌지 않는다.

```sql
ALTER TABLE orders
ADD COLUMN risk_score INTEGER;
```

Publication이 해당 컬럼을 내보내는데 target에 컬럼이 없으면 apply가 실패할 수 있다. 따라서 migration window 동안에는 DDL 절차를 엄격히 관리해야 한다.

일반적인 순서는 아래와 같다.

1. Target에 backward-compatible schema를 먼저 적용한다.
2. Source에 같은 schema를 적용한다.
3. Application을 새 컬럼을 쓰도록 배포한다.
4. 복제 상태를 확인한다.
5. 호환성 제거 변경은 cutover 이후 별도로 진행한다.

특히 column rename, type change, not null 추가, enum 변경, partition 변경은 리허설이 필요하다.

### Sequence 값은 자동으로 안전하게 맞춰진다고 보면 안 된다

Logical replication은 table row 변경을 복제한다. 하지만 sequence의 현재 값은 일반적인 row 변경처럼 계속 복제되는 개념이 아니다.

Cutover 후 target에서 insert를 시작할 때 sequence가 낮으면 primary key 충돌이 날 수 있다.

따라서 전환 전에는 sequence를 source의 최대 값 이상으로 맞춘다.

```sql
SELECT setval(
  'orders_id_seq',
  (SELECT max(id) FROM orders)
);
```

여러 테이블이 있으면 이 작업을 자동 점검 스크립트로 만드는 편이 안전하다. Sequence mismatch는 테스트에서는 잘 안 보이다가 전환 직후 첫 insert에서 터지는 유형의 장애다.

### Cutover는 lag 숫자만 보고 하면 안 된다

전환 직전에는 target이 source를 거의 따라잡았는지 봐야 한다. 하지만 단순히 "lag가 0처럼 보인다"만으로는 부족하다.

확인해야 할 것은 아래다.

- source 쓰기가 실제로 멈췄는가?
- subscription worker가 에러 없이 실행 중인가?
- source current LSN과 subscriber received/apply LSN이 맞는가?
- row count와 checksum 표본 검증이 통과했는가?
- sequence 값이 보정되었는가?
- application migration이 target schema와 호환되는가?
- rollback 경로가 남아 있는가?

전환 절차는 문서가 아니라 실행 가능한 runbook이어야 한다. 담당자가 터미널에서 어떤 SQL을 치고, 어떤 숫자를 보고, 어떤 기준이면 진행/중단할지 정해야 한다.

---

## 트레이드오프 1: Logical Replication은 느슨한 결합을 주지만 정합성 책임을 남긴다

Logical replication의 장점은 source와 target을 느슨하게 연결할 수 있다는 점이다.

- 테이블 일부만 복제한다.
- target에 별도 인덱스를 만든다.
- target 버전을 source와 다르게 가져갈 수 있다.
- target을 특정 업무용 read model로 최적화한다.
- 마이그레이션 중 양쪽을 비교할 수 있다.

하지만 이 자유도는 곧 책임이다.

### 전체 정합성이 아니라 publication 정합성이다

Publication에 포함되지 않은 테이블은 복제되지 않는다. 그래서 target에서 join할 때 source에서 당연했던 참조가 깨질 수 있다.

예를 들어 `orders`는 복제하지만 `coupons`는 복제하지 않는다고 하자. Target에서 주문별 할인명을 보여주려 하면 데이터가 없다. 이때 target 개발자가 source와 같은 모델이라고 가정하면 문제가 된다.

Logical replication target은 "source DB의 복사본"이 아니라 "publication이 정의한 데이터 제품"에 가깝다.

### Apply 순서는 보장 범위를 이해해야 한다

Logical replication은 source의 커밋된 변경을 순서대로 전달하려고 한다. 하지만 여러 subscription, 여러 publication, partition, 병렬 apply, 외부 consumer가 섞이면 애플리케이션이 기대하는 도메인 순서와 다르게 느껴질 수 있다.

같은 aggregate의 순서가 중요하다면 primary key, updated_at, version, commit timestamp, outbox event id 같은 별도 기준을 둬야 한다. "복제니까 알아서 업무 순서가 맞겠지"라고 두면 target에서 중간 상태를 읽을 수 있다.

### Target 쓰기는 매우 조심해야 한다

Logical replication target은 기술적으로 일반 PostgreSQL이다. 원한다면 직접 update도 가능하다. 하지만 복제 대상 테이블에 수동 쓰기를 섞으면 conflict 가능성이 생긴다.

예를 들어 target에서 row를 수정했는데 source에서 같은 primary key의 update가 오면 source 변경이 target 변경을 덮을 수 있다. Target에서 row를 삭제했는데 source update가 오면 apply 오류가 날 수 있다.

따라서 일반적인 운영 기준은 아래다.

- 복제 대상 테이블은 target에서 직접 쓰지 않는다.
- target 전용 파생 테이블은 별도로 둔다.
- 정정이 필요하면 source에서 정정하고 복제로 흘린다.
- 예외적 수동 수정은 runbook과 감사 로그를 남긴다.

---

## 트레이드오프 2: CDC Outbox와 Logical Replication은 대체 관계가 아니다

이전 글에서 CDC Outbox를 다뤘다면, 자연스럽게 이런 질문이 생긴다.

> Debezium Outbox를 쓸까, PostgreSQL Logical Replication을 쓸까?

둘은 겹치는 부분이 있지만 완전히 같은 문제를 푸는 도구는 아니다.

### Logical Replication이 자연스러운 경우

- Target도 PostgreSQL이다.
- 테이블 상태 자체를 복제하고 싶다.
- 별도 Kafka 인프라 없이 PostgreSQL 간 데이터 분배를 하고 싶다.
- 마이그레이션, 버전 업그레이드, reporting DB 구성이 목적이다.
- row-level table state가 중요하다.

### CDC Outbox가 자연스러운 경우

- Kafka, Pulsar 같은 broker로 이벤트를 발행해야 한다.
- 여러 언어와 서비스가 event를 소비한다.
- 비즈니스 이벤트 이름과 payload contract가 중요하다.
- 테이블 변경 그대로가 아니라 도메인 이벤트를 발행해야 한다.
- consumer가 PostgreSQL이 아닐 수 있다.

예를 들어 `orders.status`가 `PAID`로 바뀐 사실을 정산 PostgreSQL에 반영하려면 logical replication이 적절할 수 있다. 반면 `OrderPaid`라는 도메인 이벤트를 재고, 이메일, 추천, 데이터 플랫폼에 발행하려면 outbox가 더 자연스럽다.

테이블 복제와 이벤트 발행을 섞으면 책임이 흐려진다. Logical replication은 row state를 전달하고, outbox는 business event를 전달한다. 둘을 함께 쓸 수도 있지만 같은 역할을 두 번 맡기면 중복과 충돌이 생긴다.

---

## 흔한 실수 1: Primary key 없는 테이블을 publication에 넣는다

가장 흔하고 가장 빨리 터지는 실수다.

Insert만 있는 테이블이라고 생각하고 publication에 넣었는데, 나중에 데이터 정정 update가 발생한다. 그러면 replica identity 문제가 드러난다.

대응 기준은 명확하다.

- 복제 대상 테이블에는 가능하면 primary key를 둔다.
- update/delete가 있을 수 있으면 replica identity를 사전에 점검한다.
- append-only라면 publication publish 옵션으로 insert-only 계약을 명시한다.
- `REPLICA IDENTITY FULL`은 임시 우회로 보고 비용을 계산한다.

점검 쿼리는 아래처럼 만들 수 있다.

```sql
SELECT
  n.nspname AS schema_name,
  c.relname AS table_name,
  c.relreplident AS replica_identity
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind = 'r'
  AND n.nspname NOT IN ('pg_catalog', 'information_schema')
  AND NOT EXISTS (
    SELECT 1
    FROM pg_index i
    WHERE i.indrelid = c.oid
      AND i.indisprimary
  )
ORDER BY 1, 2;
```

이 결과에 publication 대상 테이블이 있다면 그냥 넘어가면 안 된다.

---

## 흔한 실수 2: DDL도 같이 복제된다고 믿는다

Logical replication은 schema migration 도구가 아니다. Source에서 컬럼을 추가하거나 타입을 바꾸면 target도 맞춰야 한다.

특히 위험한 변경은 아래다.

- source에 새 NOT NULL 컬럼 추가
- target에 없는 컬럼을 source publication column list에 포함
- 컬럼 타입을 호환되지 않게 변경
- enum 값 추가나 변경
- partition 구조 변경
- primary key 변경
- replica identity 변경

좋은 운영 방식은 schema 변경을 "source DB 작업"이 아니라 "source와 subscriber 전체 작업"으로 보는 것이다.

마이그레이션 PR이나 배포 문서에는 최소한 아래가 들어가야 한다.

- source DDL
- target DDL
- publication 변경 여부
- subscription 영향
- backward-compatible 순서
- rollback 가능 여부
- lag와 apply error 확인 방법

---

## 흔한 실수 3: Slot lag 알림 없이 subscription만 만든다

Logical replication은 처음 며칠은 조용히 잘 동작할 수 있다. 그러다 subscriber가 장애로 멈추거나 target disk가 느려지는 순간 source에 문제가 생긴다.

Slot lag 알림이 없으면 source의 `pg_wal` 증가를 너무 늦게 발견한다.

최소한 아래 지표는 모니터링해야 한다.

- slot별 retained WAL bytes
- subscription worker 상태
- apply error 로그
- source WAL 생성량
- target apply lag
- target disk usage
- target transaction conflict

경고 기준은 절대값과 증가 속도를 함께 둔다.

예를 들어 retained WAL이 10GB를 넘으면 warning, 50GB를 넘으면 critical 같은 고정 기준도 필요하지만, 10분 동안 20GB가 증가하는 속도 기준이 더 중요할 때도 있다.

---

## 흔한 실수 4: Initial sync를 업무 시간에 바로 시작한다

작은 테이블이면 괜찮다. 하지만 큰 테이블 initial sync는 source와 target 모두에 실제 부하를 만든다.

실무에서는 아래 절차를 권장한다.

1. 스테이징에서 동일한 테이블 크기 또는 샘플 배율로 리허설한다.
2. source table size와 row count를 측정한다.
3. target insert throughput을 측정한다.
4. source WAL 생성량과 slot retained WAL 증가 속도를 관측한다.
5. 업무 피크 시간을 피한다.
6. 실패 시 subscription disable, drop, 재생성 절차를 준비한다.
7. target 인덱스 전략을 정한다.

특히 initial sync 중 실패하면 "어디까지 복사됐는지"와 "재시작하면 어떤 상태가 되는지"를 알아야 한다. 대용량 복제는 항상 재시도 비용까지 포함해서 계획해야 한다.

---

## 흔한 실수 5: Sequence 보정을 잊고 cutover한다

마이그레이션에서 logical replication으로 target을 따라잡게 한 뒤 application을 target으로 전환할 때 sequence 보정을 잊는 경우가 있다.

Source에서 `orders.id`가 10,000,000까지 갔는데 target sequence는 1,000에 머물러 있으면 전환 후 insert에서 충돌이 난다.

전환 전에는 모든 sequence를 점검해야 한다.

```sql
SELECT setval('orders_id_seq', (SELECT max(id) FROM orders));
SELECT setval('payments_id_seq', (SELECT max(id) FROM payments));
SELECT setval('refunds_id_seq', (SELECT max(id) FROM refunds));
```

Identity column도 같은 관점으로 봐야 한다. Row 값은 복제되어도 "다음 번호를 어디서 시작할지"는 별도 운영 항목이다.

---

## 흔한 실수 6: Target constraint를 더 엄격하게 만들어 apply conflict를 만든다

Target은 source와 다르게 설계할 수 있다. 하지만 target constraint가 source 데이터보다 엄격하면 복제 apply가 멈출 수 있다.

예를 들어 source에는 과거 데이터 때문에 `email` 중복이 있는데 target에 unique index를 만든다고 하자.

```sql
CREATE UNIQUE INDEX uq_customers_email
ON customers (email);
```

Initial sync 중 중복 row가 들어오면 실패한다. 또는 나중에 source에서 허용된 데이터가 target에서는 거부된다.

Target에 constraint를 추가하려면 먼저 source 데이터가 그 constraint를 만족하는지 검증해야 한다.

```sql
SELECT email, count(*)
FROM customers
GROUP BY email
HAVING count(*) > 1
LIMIT 20;
```

조회 최적화용 partial index는 비교적 안전하지만, unique constraint, not null, foreign key는 apply 실패와 직결된다. 특히 foreign key는 source와 target의 테이블 복제 순서, 누락 테이블, 지연 상태에 따라 문제를 만들 수 있다.

---

## 운영 관측: 어디서 무엇을 봐야 하는가

Logical replication 운영은 source와 target을 동시에 봐야 한다.

### Source에서 볼 것

Publication 목록:

```sql
SELECT pubname, puballtables, pubinsert, pubupdate, pubdelete, pubtruncate
FROM pg_publication;
```

Publication 대상 테이블:

```sql
SELECT
  p.pubname,
  n.nspname AS schema_name,
  c.relname AS table_name
FROM pg_publication p
JOIN pg_publication_rel pr ON pr.prpubid = p.oid
JOIN pg_class c ON c.oid = pr.prrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
ORDER BY 1, 2, 3;
```

Logical slot 상태:

```sql
SELECT
  slot_name,
  active,
  restart_lsn,
  confirmed_flush_lsn,
  pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)) AS retained_wal
FROM pg_replication_slots
WHERE slot_type = 'logical'
ORDER BY pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn) DESC;
```

WAL sender 상태:

```sql
SELECT
  pid,
  application_name,
  state,
  sent_lsn,
  write_lsn,
  flush_lsn,
  replay_lsn,
  write_lag,
  flush_lag,
  replay_lag
FROM pg_stat_replication;
```

### Target에서 볼 것

Subscription 상태:

```sql
SELECT
  subid,
  subname,
  pid,
  relid,
  received_lsn,
  latest_end_lsn,
  last_msg_send_time,
  last_msg_receipt_time
FROM pg_stat_subscription;
```

테이블 sync 상태:

```sql
SELECT
  srsubid,
  srrelid::regclass AS table_name,
  srsubstate,
  srsublsn
FROM pg_subscription_rel
ORDER BY 2;
```

Subscription 정의:

```sql
SELECT subname, subenabled, subslotname, subpublications
FROM pg_subscription;
```

여기서 중요한 것은 숫자를 보는 것보다 해석 순서다.

1. Target subscription worker가 살아 있는가?
2. Source slot이 active인가?
3. Retained WAL이 증가 중인가?
4. Target apply LSN이 source current LSN을 따라잡고 있는가?
5. 특정 테이블 sync가 멈춰 있는가?
6. PostgreSQL 로그에 apply conflict가 있는가?
7. 최근 DDL, bulk update, index 작업, target 장애가 있었는가?

장애 대응은 이 순서로 좁혀야 한다. 처음부터 slot을 drop하거나 subscription을 재생성하면 복구 가능성을 스스로 없앨 수 있다.

---

## 장애 대응 시나리오: Subscriber가 하루 동안 멈췄다

가장 현실적인 시나리오를 보자. Target DB 점검 중 문제가 생겨 subscription이 하루 동안 멈췄다. Source는 계속 쓰기를 받았다.

먼저 source에서 slot 상태를 본다.

```sql
SELECT
  slot_name,
  active,
  pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)) AS retained_wal
FROM pg_replication_slots
WHERE slot_name = 'settlement_sub_slot';
```

결과가 180GB retained WAL이라고 하자. 이때 선택지는 대략 세 가지다.

### 선택지 A: Subscriber를 복구해서 따라잡게 한다

Target 장애가 해결 가능하고 source 디스크 여유가 충분하다면 가장 안전하다. Subscription을 다시 enable하고 apply 속도를 관측한다.

```sql
ALTER SUBSCRIPTION settlement_sub ENABLE;
```

그리고 retained WAL이 줄어드는지 본다. 줄지 않거나 더 커지면 target apply 속도가 source 생성 속도를 못 따라가는 것이다. 이때는 target I/O, index, constraint, worker 상태를 봐야 한다.

### 선택지 B: 잠시 source 쓰기 피크를 낮춘다

Subscriber가 따라잡을 수 있도록 bulk job, backfill, 대량 update를 멈춘다. 실시간 서비스 쓰기를 멈출 수는 없더라도 배치성 쓰기만 낮춰도 catch-up이 가능해질 수 있다.

이 선택은 기술보다 운영 조율에 가깝다. 어느 job을 멈출 수 있는지, 고객 영향은 무엇인지, 다시 켜는 기준은 무엇인지가 정해져 있어야 한다.

### 선택지 C: Slot을 버리고 재초기화한다

Source 디스크가 위험하고 subscriber가 곧 따라잡을 수 없다면 slot을 drop하고 재초기화를 선택할 수 있다.

하지만 이것은 복제 연속성을 포기하는 결정이다. Target은 더 이상 빠진 변경을 자동으로 이어받을 수 없다.

일반적인 절차는 아래에 가깝다.

1. Target 조회 서비스를 중단하거나 stale 상태로 표시한다.
2. Subscription을 disable/drop한다.
3. Source slot을 drop한다.
4. Target 데이터를 정리하거나 새 schema에 다시 적재한다.
5. Subscription을 재생성한다.
6. Initial sync를 다시 수행한다.
7. 검증 후 서비스를 재개한다.

이 결정을 장애 중 즉흥적으로 하면 위험하다. Logical replication을 운영한다면 "slot 포기와 재초기화" 절차도 미리 있어야 한다.

---

## 배포 절차: DDL 변경을 안전하게 흘리는 순서

Source와 target 모두에 `orders` 테이블이 있고, 새 컬럼 `risk_level`을 추가한다고 하자. Application은 처음에는 이 컬럼을 쓰지 않고, 나중에 값을 채운다.

안전한 순서는 보통 아래와 같다.

### 1단계: Target에 nullable 컬럼을 먼저 추가한다

```sql
ALTER TABLE orders
ADD COLUMN risk_level TEXT;
```

Target이 먼저 새 컬럼을 받아들일 수 있게 한다. 이 단계는 source 복제에 영향을 주지 않는다.

### 2단계: Source에 nullable 컬럼을 추가한다

```sql
ALTER TABLE orders
ADD COLUMN risk_level TEXT;
```

이제 source에서 새 컬럼 값이 생겨도 target이 받을 수 있다.

### 3단계: Application이 새 컬럼을 쓰도록 배포한다

Application이 `risk_level`을 채우기 시작한다. 이 변경은 logical replication을 통해 target으로 간다.

### 4단계: Backfill을 작은 chunk로 수행한다

```sql
UPDATE orders
SET risk_level = 'LOW'
WHERE id > :last_id
  AND id <= :last_id + 10000
  AND risk_level IS NULL;
```

대량 backfill은 WAL과 replication lag를 키운다. chunk size, sleep, lock timeout, statement timeout, target apply lag를 같이 봐야 한다.

### 5단계: Not null이나 constraint는 검증 후 추가한다

Source와 target 모두 null이 없는지 확인한다.

```sql
SELECT count(*)
FROM orders
WHERE risk_level IS NULL;
```

그 다음 constraint를 추가한다. Not null 전환은 테이블 크기와 PostgreSQL 버전에 따라 lock과 scan 비용이 달라질 수 있으므로 별도 리허설이 필요하다.

이 순서의 핵심은 호환성이다. Target이 먼저 받을 수 있게 만들고, source가 보내기 시작하고, application이 사용하고, 마지막에 제약을 강화한다.

---

## 체크리스트: 도입 전 반드시 확인할 것

Logical replication을 운영에 넣기 전에는 아래 항목을 확인한다.

### 데이터 계약

- Publication 이름이 목적을 설명하는가?
- `FOR ALL TABLES`를 피하고 명시적 테이블 목록을 쓰는가?
- 복제 제외 테이블의 이유가 문서화되어 있는가?
- row filter나 column list를 쓴다면 target 데이터 의미가 문서화되어 있는가?
- target이 source 전체 복사본인지, 특정 업무 read model인지 명확한가?

### 테이블 구조

- 복제 대상 테이블에 primary key가 있는가?
- update/delete가 필요한 테이블의 replica identity가 적절한가?
- `REPLICA IDENTITY FULL`을 쓰는 테이블은 크기와 변경량을 계산했는가?
- target schema가 복제 컬럼을 모두 받을 수 있는가?
- target constraint가 source 데이터를 거부하지 않는가?
- sequence와 identity column 보정 절차가 있는가?

### 초기 동기화

- 테이블별 row count와 total size를 측정했는가?
- initial sync 예상 시간을 계산했는가?
- source WAL 생성량과 retained WAL 여유를 계산했는가?
- target insert throughput과 disk 여유를 확인했는가?
- target 보조 인덱스를 언제 만들지 정했는가?
- 실패 후 재시작 또는 재초기화 절차가 있는가?

### 운영 관측

- slot별 retained WAL 알림이 있는가?
- subscription worker 상태 알림이 있는가?
- PostgreSQL apply error 로그를 수집하는가?
- target lag를 사용자 화면이나 운영 대시보드에서 볼 수 있는가?
- source disk usage와 WAL 증가 속도 알림이 있는가?
- inactive logical slot 점검 주기가 있는가?

### 배포와 장애 대응

- DDL 변경 runbook이 source와 target 순서를 포함하는가?
- bulk update/backfill 시 lag 제한 기준이 있는가?
- subscriber 장기 중단 시 source 보호 기준이 있는가?
- slot drop과 재초기화 결정 기준이 있는가?
- cutover 시 쓰기 중단, LSN 확인, row 검증, sequence 보정 절차가 있는가?
- rollback 가능한 시간과 방법이 명확한가?

---

## 한 줄 정리

PostgreSQL Logical Replication은 `CREATE PUBLICATION`과 `CREATE SUBSCRIPTION`으로 시작할 수 있지만, 운영에서 성공하려면 publication 범위, replica identity, initial sync 부하, slot lag, DDL 절차, conflict 대응까지 하나의 데이터 계약으로 설계해야 한다.
