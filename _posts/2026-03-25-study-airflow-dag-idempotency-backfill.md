---
layout: post
title: "Airflow 배치 파이프라인 실전: DAG 멱등성, Backfill, Late Data 운영 기준"
date: 2026-03-25 11:40:00 +0900
categories: [data-infra]
tags: [study, data-infra, airflow, dag, idempotency, backfill, late-data, batch, orchestration]
---

## 배경: 배치는 "한 번 돌면 끝"이 아니라 "다시 돌려도 안 망가져야" 한다

Airflow를 처음 도입한 팀은 대개 DAG를 "스케줄 잡아서 작업 순서대로 실행해주는 도구" 정도로 이해한다. 이 관점 자체는 틀리지 않다. 다만 운영 단계로 가면 문제의 핵심은 스케줄링이 아니라 **재실행과 복구**로 이동한다.

실제 장애는 보통 아래처럼 발생한다.

- 새벽 2시 배치가 중간 단계에서 실패했고 7시 출근 후 재실행해야 한다
- 원본 데이터가 3시간 늦게 도착해서 이미 끝난 일별 집계를 다시 계산해야 한다
- 코드 버그를 수정한 뒤 지난 14일 데이터를 backfill해야 한다
- DAG는 성공으로 찍혔지만 일부 파티션만 비어 있어서 다시 채워야 한다
- 다운스트림 테이블이 `INSERT` 중심으로 설계돼 있어 재실행할수록 중복이 쌓인다

즉 배치 운영의 진짜 질문은 이것이다.

> 이 DAG를 오늘 한 번 성공시키는 것이 아니라, 내일 다시 돌려도 결과가 예측 가능하도록 설계했는가?

Airflow는 orchestration 도구이지 데이터 정합성을 자동으로 보장해주는 도구가 아니다. DAG를 예쁘게 그려도, 태스크 간 의존성이 깔끔해도, **출력 테이블 계약이 멱등적이지 않으면** 재실행 순간부터 운영 비용이 폭발한다.

이 글은 Airflow 사용법 자체보다, 중급 이상 개발자가 실무에서 반드시 부딪히는 세 가지 축을 기준으로 정리한다.

1. **DAG 멱등성(idempotency)**: 같은 실행 범위를 여러 번 처리해도 결과가 같아야 한다
2. **Backfill 전략**: 과거 구간을 다시 채울 때 현재 운영 데이터와 충돌하지 않아야 한다
3. **Late Data 대응**: 늦게 들어온 원천 데이터가 있을 때 어떤 단위로 재계산할지 명확해야 한다

목표는 Airflow 문법 암기가 아니라, **배치 파이프라인을 복구 가능한 시스템으로 설계하는 기준**을 잡는 것이다.

---

## 먼저 큰 그림: Airflow의 성공 여부와 데이터의 성공 여부는 다를 수 있다

Airflow UI에서 DAG run이 `success`라고 찍혀 있어도 데이터가 올바르다는 뜻은 아니다. 반대로 일부 태스크가 실패해도 데이터 레벨에서는 이미 부분 반영이 끝난 상태일 수도 있다.

이 차이를 이해해야 한다.

### Airflow가 보장하는 것

- 태스크 실행 순서와 의존성 관리
- 재시도, 스케줄링, 실행 이력 저장
- 태스크 단위 성공/실패 상태 추적
- 큐잉, 워커 분산, 운영 UI 제공

### Airflow가 보장하지 않는 것

- SQL/파이썬 태스크 내부 로직의 멱등성
- 중복 적재 방지
- late data의 자동 재처리
- backfill 시 현재 운영 데이터와의 충돌 방지
- 다운스트림 테이블의 최종 정합성

그래서 Airflow를 잘 쓰는 팀과 그렇지 않은 팀의 차이는 DAG 개수가 아니라 **데이터 계약과 재실행 철학**에 있다.

잘하는 팀은 다음 질문에 답이 있다.

- 이 태스크는 어느 `data interval`을 책임지는가?
- 결과를 append할 것인가, replace할 것인가, merge할 것인가?
- 같은 interval을 다시 실행하면 어떻게 되는가?
- late data는 자동 복구인가, 수동 backfill인가?
- 실패 지점부터 재개 가능한가, 아니면 전체 구간을 다시 계산해야 하는가?

이 질문에 답이 없으면 DAG는 늘어나도 운영은 나아지지 않는다.

---

## 핵심 개념 1: execution time보다 data interval을 중심으로 사고해야 한다

Airflow 초보 시절에는 `2026-03-25 02:00에 도는 DAG`처럼 시간을 기준으로 생각하기 쉽다. 하지만 실무에서는 **언제 돌았는가보다 어떤 데이터 구간을 처리했는가**가 더 중요하다.

예를 들어 매일 새벽 2시에 전날 주문 합계를 집계하는 DAG가 있다고 하자.

- 실행 시각: `2026-03-25 02:00`
- 실제 처리 대상: `2026-03-24 00:00 ~ 2026-03-25 00:00`

이 구분이 중요한 이유는 재실행과 backfill 때문이다.

동일한 `2026-03-24` 구간을 다시 계산해야 할 때,

- 스케줄러 입장에서는 다른 시점의 재실행일 수 있지만
- 데이터 입장에서는 **같은 interval의 재처리**다

즉 멱등성은 "이 시각의 태스크를 다시 실행해도 안전한가"보다 **"이 interval의 산출물을 다시 만들어도 결과가 같아지는가"**로 정의하는 편이 정확하다.

### 왜 `{{ ds }}`만 믿으면 위험한가

많은 DAG가 템플릿 변수 하나로 날짜를 받아 쿼리를 작성한다.

```sql
where dt = '{{ ds }}'
```

이 패턴 자체는 가능하지만, 아래가 불분명하면 사고가 난다.

- `ds`가 논리 날짜인지, 실제 데이터 종료일인지
- 타임존이 UTC인지 로컬인지
- 업스트림 적재 지연이 있을 때 재실행 기준 날짜가 무엇인지
- 일 집계인지 시간 집계인지

실무에서는 `logical_date` 자체보다 **`data_interval_start`, `data_interval_end`를 명시적으로 사용**하는 편이 운영상 더 안전하다.

예를 들어,

```python
@task
def build_query(data_interval_start=None, data_interval_end=None):
    return f"""
    insert into ...
    select ...
    where event_time >= '{data_interval_start}'
      and event_time < '{data_interval_end}'
    """
```

이렇게 해야 태스크가 어떤 범위를 책임지는지 코드 수준에서 드러난다.

### 실무 기준

- 스케줄은 트리거 조건이다
- 데이터 interval은 처리 계약이다
- 멱등성/late data/backfill은 모두 interval 기준으로 설계해야 한다

이 원칙이 빠지면 Airflow DAG는 단순 cron의 확장판에 머무른다.

---

## 핵심 개념 2: 멱등성은 태스크 옵션이 아니라 출력 모델의 속성이다

팀에서 "이 DAG는 멱등적으로 만들자"라고 말할 때, 종종 재시도 옵션만 떠올린다. 하지만 진짜 멱등성은 Airflow 설정이 아니라 **결과를 쓰는 방식**에서 결정된다.

같은 `2026-03-24` 주문 집계를 두 번 돌렸을 때 결과가 같아지려면, 출력 테이블이 아래 중 하나로 설계돼야 한다.

### 1) 파티션 replace

가장 직관적인 방식이다.

- 대상 파티션을 비우고
- 해당 interval 결과를 다시 전량 적재한다

예:

```sql
delete from mart_daily_order_summary
where dt = '2026-03-24';

insert into mart_daily_order_summary (dt, store_id, order_count, total_amount)
select
    date(order_time) as dt,
    store_id,
    count(*) as order_count,
    sum(total_amount) as total_amount
from ods_orders
where order_time >= '2026-03-24 00:00:00+09:00'
  and order_time < '2026-03-25 00:00:00+09:00'
group by 1, 2;
```

장점:

- 이해하기 쉽다
- interval 단위 재처리가 단순하다
- 데이터 검증이 명확하다

단점:

- 파티션 단위 쓰기 비용이 크다
- 대용량 테이블에서는 락/쓰기 부하가 커질 수 있다
- 삭제 후 적재 실패 시 공백 구간이 생길 수 있다

그래서 가능하면 **staging 테이블에 먼저 계산 후 atomic swap** 또는 transaction 묶음을 고려해야 한다.

### 2) MERGE / UPSERT

행 단위 고유 키가 명확하다면 merge가 유용하다.

```sql
merge into mart_daily_order_summary t
using (
    select
        date(order_time) as dt,
        store_id,
        count(*) as order_count,
        sum(total_amount) as total_amount
    from ods_orders
    where order_time >= '2026-03-24 00:00:00+09:00'
      and order_time < '2026-03-25 00:00:00+09:00'
    group by 1, 2
) s
on t.dt = s.dt and t.store_id = s.store_id
when matched then update set
    order_count = s.order_count,
    total_amount = s.total_amount,
    updated_at = now()
when not matched then insert (dt, store_id, order_count, total_amount, updated_at)
values (s.dt, s.store_id, s.order_count, s.total_amount, now());
```

장점:

- 부분 재계산이 가능하다
- 키 단위 upsert에 적합하다
- 공백 파티션을 만들지 않고 덮어쓰기 가능하다

단점:

- delete semantics가 별도로 필요하다
- 소스에서 빠진 행을 타깃에서 어떻게 제거할지 정의해야 한다
- 엔진별 성능/락 특성이 다르다

즉 MERGE는 강력하지만, "소스 결과가 타깃의 완전한 진실인가"를 먼저 정해야 한다.

### 3) append-only + dedup downstream

이 방식은 로그성 원천에는 맞지만, 집계/mart 테이블에는 신중해야 한다.

```sql
insert into fact_order_events (...) values (...)
```

같은 interval을 다시 돌리면 중복이 생길 수 있으므로 downstream에서 `event_id`나 `(dt, key, version)` 기준으로 제거해야 한다.

이 구조는 원천 fact 저장에는 괜찮지만, **최종 리포팅용 테이블**에는 운영 난도가 높다.

### 핵심 판단

멱등성은 결국 아래 질문으로 환원된다.

> 같은 interval을 다시 실행했을 때, 출력 테이블이 "추가"되는가, "대체"되는가, "갱신"되는가?

이게 정해져야 Airflow 재실행 버튼을 안심하고 누를 수 있다.

---

## 핵심 개념 3: Backfill은 단순 재실행이 아니라 과거 구간을 현재 시스템에 다시 삽입하는 작업이다

Backfill을 가볍게 보면 안 된다. 운영 중인 파이프라인에 과거 구간을 다시 흘려넣는 순간, 다음 문제가 동시에 발생한다.

- 이미 적재된 현재 데이터와 충돌할 수 있다
- 과거 스키마와 현재 스키마가 다를 수 있다
- 소스 원천 보존 기간이 짧으면 일부 데이터가 이미 사라졌을 수 있다
- 다운스트림 캐시/인덱스/리포트가 부분적으로만 다시 계산될 수 있다

즉 backfill은 "예전 날짜로 DAG를 한 번 더 돌리기"가 아니라, **과거 구간의 데이터를 현재 계약으로 다시 복원하는 배치 이벤트**다.

### Backfill 전에 먼저 정해야 할 것

#### 1) 범위

- 하루인가, 일주일인가, 6개월인가?
- 연속 구간인가, 특정 날짜들만 다시 돌릴 것인가?

#### 2) 산출물 전략

- 기존 결과를 완전히 대체할 것인가?
- 누락분만 보완할 것인가?
- 별도 테이블에 재계산 후 검증 뒤 스왑할 것인가?

#### 3) 리소스 격리

- 운영 DAG와 같은 워커 풀을 쓸 것인가?
- 백필 때문에 정시 DAG가 밀리지 않는가?

#### 4) 검증 기준

- 기존 집계와 몇 % 차이면 정상인가?
- row count, amount sum, distinct key 수를 비교할 것인가?

Backfill이 위험한 이유는 코드가 아니라 **운영 흐름에 끼어드는 데이터량** 때문이다.

### Airflow의 catchup과 backfill은 같은 것이 아니다

실무에서 자주 혼동한다.

- `catchup=True`: 스케줄 누락 구간을 scheduler가 논리적으로 채우는 동작
- 운영자가 수행하는 backfill: 이미 끝난 구간을 **의도적으로 다시 계산**하는 작업

둘은 비슷해 보이지만 목적이 다르다.

- catchup은 스케줄 정합성 복원에 가깝고
- backfill은 데이터 정합성 복원에 가깝다

따라서 운영 기준은 다음이 더 중요하다.

- backfill 전용 DAG parameter를 둘 것인가
- `full_refresh=true` 같은 명시 플래그가 필요한가
- 정상 스케줄과 백필 스케줄을 같은 코드 경로로 태울 것인가
- 백필 시 동시 실행 한도를 별도로 제한할 것인가

### 추천 패턴

백필을 자주 하는 테이블이라면 처음부터 아래처럼 설계하는 편이 낫다.

- interval 기반 파라미터화
- 출력 파티션 replace 또는 deterministic merge
- 검증 쿼리 내장
- 백필 전용 pool/queue 분리
- "재실행해도 동일 결과"를 기본 가정으로 둔 SQL 작성

이렇게 해야 backfill이 예외 대응이 아니라 일상 운영 행위가 된다.

---

## 핵심 개념 4: Late Data는 장애가 아니라 계약이다

원천 데이터가 늦게 들어오는 것은 특별한 예외가 아니라 흔한 현실이다.

- 모바일 이벤트가 오프라인 상태였다가 몇 시간 뒤 업로드된다
- 외부 제휴 정산 파일이 오전이 아니라 오후에 도착한다
- 업스트림 ETL이 지연되어 전날 데이터 일부가 점심때 채워진다
- 메시지 브로커 지연으로 특정 파티션만 늦게 적재된다

이때 많은 팀이 두 가지 실수를 한다.

### 실수 1) "DAG 성공"이면 끝난 것으로 본다

새벽 2시 배치가 성공했더라도 오전 6시에 전날 데이터 3%가 추가 유입됐다면, 집계는 이미 낡았다.

### 실수 2) late data를 발견할 때마다 수동 재실행한다

운영자가 매번 감으로 날짜를 골라 다시 돌리는 구조는 오래 못 간다.

### 더 좋은 질문

late data 대응에서는 아래를 먼저 정해야 한다.

- 어느 정도 지연까지를 정상 범위로 볼 것인가?
- 특정 지연 시간 내에는 자동 재계산할 것인가?
- 데이터가 닫히는 watermark는 무엇인가?
- 최종 확정치와 잠정치(preliminary)를 구분할 것인가?

예를 들어 일별 매출 집계라면 아래 같은 정책을 둘 수 있다.

- D+0 새벽 2시: 전일 잠정 집계 생성
- D+1 새벽 2시: late data 반영한 1차 확정
- D+3 새벽 2시: 마지막 보정 윈도우
- D+3 이후 변경은 수동 backfill 요청으로만 처리

이 정책이 있으면 late data는 더 이상 예외가 아니다. **정의된 재계산 창(window)** 안에서 자동 운영되는 계약이 된다.

### Watermark 개념을 배치에도 도입해야 한다

스트리밍 시스템에서 watermark를 이야기할 때만 늦은 데이터 개념을 다루는 팀이 많지만, 배치도 사실상 동일하다.

- "이 시점까지 들어온 데이터만 오늘 집계에 포함한다"
- "이 날짜는 아직 닫히지 않았으므로 provisional 상태다"
- "3일이 지나면 해당 파티션은 closed 상태다"

이런 기준이 있어야 downstream도 숫자의 의미를 이해한다. CFO용 리포트와 운영 모니터링용 대시보드는 **같은 테이블을 써도 닫힘 시점이 다를 수 있다**.

---

## 실무 예시: 주문 일별 집계 DAG를 재실행/백필/late data에 강하게 만들기

상황을 구체화해보자.

- 원천: `ods_orders`
- 출력: `mart_daily_order_summary`
- 집계 기준: KST 일자
- 요구사항:
  - 매일 새벽 전일 데이터 집계
  - late data는 3일 동안 자동 반영
  - 코드 수정 시 지정 구간 backfill 가능
  - 재실행해도 중복/누락 없어야 함

### 출력 테이블 설계

```sql
create table if not exists mart_daily_order_summary (
    dt date not null,
    store_id bigint not null,
    order_count bigint not null,
    paid_order_count bigint not null,
    total_amount numeric(18,2) not null,
    updated_at timestamptz not null,
    primary key (dt, store_id)
);
```

핵심은 primary key가 interval + business key로 고정돼 있다는 점이다. 이러면 merge/update 대상이 명확해진다.

### DAG 설계 원칙

1. 기본 스케줄은 매일 02:10 KST
2. 한 번 실행할 때 `target_dates`를 1일이 아니라 최근 3일로 확장 가능
3. 각 날짜는 독립 태스크 또는 동적 태스크 매핑으로 분리
4. 각 날짜는 자신 파티션만 다시 계산
5. 결과 검증 후 최종 commit

### Airflow 예시 코드

```python
from __future__ import annotations

from airflow import DAG
from airflow.decorators import task
from airflow.utils.dates import days_ago
import pendulum

KST = pendulum.timezone("Asia/Seoul")

with DAG(
    dag_id="mart_daily_order_summary_v2",
    schedule="10 2 * * *",
    start_date=days_ago(1),
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 2},
    render_template_as_native_obj=True,
    tags=["mart", "orders"],
) as dag:

    @task
    def resolve_target_dates(data_interval_end=None, dag_run=None):
        conf = dag_run.conf or {}
        if conf.get("target_dates"):
            return conf["target_dates"]

        base = data_interval_end.in_timezone(KST).date()
        return [str(base.subtract(days=days)) for days in range(1, 4)]

    @task
    def rebuild_partition(target_date: str):
        # 1) staging 계산
        # 2) row count / sum 검증
        # 3) merge 또는 partition replace
        # 4) 메타데이터 기록
        return {"target_date": target_date, "status": "ok"}

    rebuild_partition.expand(target_date=resolve_target_dates())
```

포인트는 DAG 자체가 "전일 1건 처리"가 아니라 **대상 interval 집합을 계산하는 컨트롤러**처럼 동작한다는 점이다.

### SQL 적용 패턴: staging + validate + merge

운영에서는 바로 본 테이블에 쓰기보다 staging을 거치는 편이 훨씬 안전하다.

```sql
create temporary table stg_daily_order_summary as
select
    timezone('Asia/Seoul', order_time)::date as dt,
    store_id,
    count(*) as order_count,
    count(*) filter (where order_status = 'PAID') as paid_order_count,
    coalesce(sum(total_amount), 0) as total_amount
from ods_orders
where order_time >= :start_ts
  and order_time < :end_ts
group by 1, 2;
```

그 다음 최소한 아래를 검증한다.

- row count > 0 또는 기대 범위 확인
- `total_amount >= 0`
- `dt`가 단일 날짜인지
- store_id null 여부

이후 merge:

```sql
merge into mart_daily_order_summary t
using stg_daily_order_summary s
on t.dt = s.dt and t.store_id = s.store_id
when matched then update set
    order_count = s.order_count,
    paid_order_count = s.paid_order_count,
    total_amount = s.total_amount,
    updated_at = now()
when not matched then insert (
    dt, store_id, order_count, paid_order_count, total_amount, updated_at
) values (
    s.dt, s.store_id, s.order_count, s.paid_order_count, s.total_amount, now()
);
```

### 소스 삭제/변경 대응

여기서 한 단계 더 생각해야 한다. 만약 특정 날짜의 일부 store가 소스에서 아예 사라졌다면 단순 merge만으로는 타깃의 stale row가 남는다. 이 경우 두 가지 전략 중 하나를 선택해야 한다.

#### 전략 A) 대상 날짜 전체 replace

- 해당 날짜 파티션 또는 키 범위를 먼저 삭제
- staging 결과를 전량 insert

가장 안전하지만 쓰기 비용이 크다.

#### 전략 B) merge + not matched by source delete

DB 엔진이 지원한다면 소스에 없는 행을 삭제한다.

```sql
when not matched by source and t.dt = :target_date then delete
```

이 기능이 없다면 delete + insert가 더 명확할 수 있다.

핵심은 **소스가 완전 집합인지, 변경분 집합인지**를 명확히 하는 것이다.

---

## 운영에서 자주 마주치는 트레이드오프

좋은 설계는 늘 비용과 함께 온다. Airflow 배치도 예외가 아니다.

### 1) 파티션 전체 replace vs row-level merge

#### 파티션 전체 replace

- 장점: 단순하고 설명 가능성이 높다
- 장점: 재실행 의미가 분명하다
- 단점: 대용량 구간에서는 비용이 크다
- 단점: 잘못 설계하면 삭제 후 실패 시 공백 발생

#### row-level merge

- 장점: 증분 반영이 가능하다
- 장점: late data 일부 보정에 유리하다
- 단점: stale row 정리 규칙이 복잡하다
- 단점: 키 설계가 불명확하면 중복/누락을 숨기기 쉽다

일 집계처럼 결과 크기가 관리 가능하면 replace가 더 단순하고 안전한 경우가 많다. 반대로 거대한 fact 적재는 merge/upsert 또는 append+dedup가 현실적일 수 있다.

### 2) 즉시 확정치 vs 지연 허용 후 확정치

#### 즉시 확정치

- 장점: 리포트 단순성
- 단점: late data에 취약

#### 지연 허용 후 확정치

- 장점: 숫자 신뢰도 상승
- 단점: 사용자에게 provisional/final 의미를 설명해야 함

비즈니스가 원하는 것은 보통 "빠른 숫자"와 "정확한 숫자" 둘 다다. 한 테이블에 두 요구를 무리하게 섞기보다, **잠정 집계와 확정 집계를 분리**하는 것이 더 현실적일 수 있다.

### 3) scheduler 중심 자동화 vs 운영자 개입 여지

모든 late data를 자동 보정하려 하면 리소스 비용이 커진다. 반대로 수동 운영만 두면 사람 의존이 커진다.

실무적으로는 아래 절충이 많다.

- 최근 3일은 자동 재계산
- 그 이전은 수동 backfill
- 수동 backfill도 interval, dry-run, validation rule이 있는 표준 경로로 실행

이렇게 해야 자동화 범위와 운영 통제가 균형을 잡는다.

---

## 흔한 실수

### 1) Airflow retry를 멱등성과 혼동한다

재시도는 단지 태스크를 한 번 더 실행할 뿐이다. SQL이 append-only라면 retry할수록 데이터가 더 망가질 수 있다.

### 2) 출력 키가 없는데 merge부터 쓴다

`upsert`는 마법이 아니다. 고유 키가 불명확하면 같은 비즈니스 엔티티가 여러 행으로 쪼개져 중복 집계가 생긴다.

### 3) late data 정책 없이 "전날 1회 집계"만 설계한다

현실의 데이터는 늦게 들어온다. 이 사실을 무시하면 운영자는 결국 매일 수동 재실행 버튼을 누르게 된다.

### 4) backfill을 운영 DAG와 같은 리소스 풀에 무제한으로 태운다

과거 90일 backfill 때문에 오늘 새벽 정시 DAG가 밀리면 복구 작업이 또 다른 장애가 된다.

### 5) 데이터 interval 대신 wall clock 기준으로 쿼리를 짠다

`now() - interval '1 day'` 같은 식은 재실행 시 의미가 달라진다. interval 기반으로 고정된 범위를 계산해야 한다.

### 6) 검증 없는 적재를 성공으로 본다

row count, sum, null key, 대상 날짜 범위 같은 기본 검증이 없으면 태스크 성공이 데이터 성공을 가리지 못한다.

### 7) 소스 삭제 의미를 정의하지 않는다

소스에서 빠진 데이터가 정정인지, 지연인지, 단순 누락인지 정의가 없으면 merge 결과는 쉽게 stale 상태가 된다.

### 8) 파티션 단위 원자성을 고려하지 않는다

삭제 후 insert 사이에 실패하면 해당 날짜 데이터가 통째로 비는 사고가 난다. staging과 transaction, swap 전략을 먼저 검토해야 한다.

---

## 실무 체크리스트

### DAG 설계

- [ ] 각 태스크가 담당하는 `data interval`이 코드와 문서에 명확한가?
- [ ] `logical_date`가 아니라 `data_interval_start/end` 기준으로 처리 범위를 정의했는가?
- [ ] 재실행 대상 날짜를 파라미터로 명시적으로 넣을 수 있는가?
- [ ] 운영 스케줄과 backfill 실행 경로를 구분했는가?

### 출력 모델

- [ ] 출력 테이블에 interval + business key 기준의 고유성이 있는가?
- [ ] 같은 interval 재실행 시 replace/merge/append 중 어떤 모델인지 명확한가?
- [ ] stale row 삭제 전략이 있는가?
- [ ] delete 후 insert 사이 공백을 막는 transaction 또는 staging 전략이 있는가?

### Late Data 대응

- [ ] 정상 지연 허용 범위가 정의되어 있는가?
- [ ] 자동 재계산 window가 있는가? (예: 최근 3일)
- [ ] provisional/final 데이터의 의미가 합의되어 있는가?
- [ ] downstream 소비자가 숫자의 닫힘 시점을 이해하는가?

### Backfill 운영

- [ ] backfill 전용 pool/queue 또는 동시성 제한이 있는가?
- [ ] backfill 범위, 실행자, 이유가 기록되는가?
- [ ] row count / sum / distinct key 비교 등 검증 절차가 있는가?
- [ ] backfill 후 재색인/캐시무효화/리포트 재계산 같은 후속 작업이 정의되어 있는가?

### 관측성

- [ ] DAG 성공 여부 외에 데이터 품질 지표를 모니터링하는가?
- [ ] 파티션별 row count 급감/급증 알람이 있는가?
- [ ] 늦게 도착한 소스 레코드 비율을 측정하는가?
- [ ] 수동 재실행이 얼마나 자주 발생하는지 운영 메트릭으로 보고 있는가?

---

## 한 줄 정리

Airflow 배치 운영의 핵심은 DAG를 제시간에 한 번 돌리는 것이 아니라, **같은 data interval을 다시 처리해도 결과가 예측 가능하도록 멱등성·backfill·late data 정책을 출력 테이블 계약까지 포함해 설계하는 것**이다.
