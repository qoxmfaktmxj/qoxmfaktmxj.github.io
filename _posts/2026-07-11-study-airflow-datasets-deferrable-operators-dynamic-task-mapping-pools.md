---
layout: post
title: "Airflow 오케스트레이션 운영 설계: Datasets, Deferrable Operator, Dynamic Task Mapping, Pool로 DAG를 확장하는 법"
date: 2026-07-11 11:50:00 +0900
categories: [data-infra]
tags: [study, data-infra, airflow, datasets, deferrable-operator, dynamic-task-mapping, pool, dag, orchestration, scheduler, data-platform]
permalink: /data-infra/2026/07/11/study-airflow-datasets-deferrable-operators-dynamic-task-mapping-pools.html
---

## 배경: Airflow 병목은 코드보다 운영 모델에서 먼저 온다

Airflow를 처음 도입할 때는 DAG 파일 몇 개로 시작한다. 매일 새벽에 주문 데이터를 집계하고, 로그를 object storage에서 warehouse로 적재하고, 모델 학습용 feature를 만든다. 이 단계에서는 `schedule`, `task`, `dependency`, `retry` 정도만 알아도 꽤 많은 일을 할 수 있다.

문제는 DAG 수가 늘어나면서 시작된다.

- 원천 테이블이 준비된 뒤에만 downstream DAG를 실행하고 싶다
- 하루에 한 번 돌던 DAG가 지역, 고객사, 파티션 단위로 수백 개 태스크를 만들어야 한다
- 외부 API 응답이나 Spark job 완료를 기다리는 sensor가 worker slot을 계속 잡아먹는다
- 특정 warehouse cluster나 외부 SaaS API에 동시에 너무 많은 요청이 몰린다
- 장애 이후 catchup과 backfill이 운영 중인 정규 배치를 밀어낸다
- DAG는 쪼개졌지만 데이터 준비 상태, 리소스 제한, fan-out 기준이 코드 곳곳에 흩어진다

이때부터 Airflow의 난이도는 "DAG를 작성하는 법"이 아니라 **오케스트레이션 제어면을 설계하는 법**으로 바뀐다. 제어면이라는 말이 거창해 보일 수 있지만 핵심은 단순하다.

> 언제 실행할지, 무엇을 몇 개로 나눠 실행할지, 기다리는 동안 무엇을 점유할지, 동시에 얼마나 실행할지를 시스템 차원에서 제어해야 한다.

이 글은 기존의 DAG 멱등성, backfill, late data 설계와는 다른 층위를 다룬다. 데이터 결과가 재실행에 안전해야 한다는 원칙은 여전히 중요하지만, 오늘의 초점은 **Airflow 자체를 확장 가능하게 운영하는 패턴**이다.

중급 이상 개발자와 데이터 엔지니어라면 아래 기능을 단순 문법이 아니라 운영 설계 도구로 봐야 한다.

1. **Datasets**: DAG 사이의 데이터 준비 이벤트를 명시한다
2. **Dynamic Task Mapping**: 실행 시점에 fan-out 단위를 결정한다
3. **Deferrable Operator**: 오래 기다리는 작업이 worker slot을 점유하지 않게 한다
4. **Pools와 priority**: 외부 시스템과 내부 executor의 동시성 예산을 보호한다
5. **DAG-level concurrency**: catchup, max active runs, task concurrency를 함께 설계한다

결론부터 말하면 이렇다.

**Airflow를 오래 운영하려면 DAG 파일을 많이 만드는 능력보다, 데이터 이벤트와 리소스 예산을 명시적으로 모델링하는 능력이 더 중요하다.**

---

## 먼저 큰 그림: Airflow는 작업 큐이면서 의존성 그래프이고 리소스 중재자다

Airflow를 cron 대체재로만 보면 기능 선택이 단순해진다.

```text
매일 02:00 실행
  -> extract
  -> transform
  -> load
```

하지만 실제 플랫폼에서는 한 DAG가 혼자 존재하지 않는다.

```text
raw ingestion DAG
  -> staging validation DAG
  -> mart build DAG
  -> feature generation DAG
  -> dashboard refresh DAG
  -> notification DAG
```

여기서 중요한 질문은 "각 DAG의 schedule을 어떻게 잡을 것인가"가 아니다. 진짜 질문은 이것이다.

- upstream 데이터가 준비되었다는 사실을 downstream이 어떻게 알 것인가
- 여러 upstream 중 일부만 준비되었을 때 downstream은 기다릴 것인가, 부분 실행할 것인가
- 같은 DAG가 날짜별, 파티션별, 고객사별로 동시에 떠도 되는가
- 실행 개수가 늘어났을 때 worker, database, warehouse, 외부 API 중 무엇이 먼저 병목이 되는가
- sensor와 long-running job은 worker slot을 오래 점유해도 되는가
- 장애 복구용 backfill이 정규 운영 workload를 방해하지 않게 만들 수 있는가

Airflow의 scheduler는 DAG 정의를 보고 task instance를 만들고, executor는 실행 가능한 task를 worker로 보낸다. 이때 task가 실행된다는 것은 단순히 Python 함수가 호출된다는 뜻이 아니다. metadata DB row가 늘어나고, executor queue를 사용하고, worker slot을 점유하고, 외부 시스템에 부하를 만든다.

그래서 Airflow 운영 설계는 네 가지 계약으로 나누면 이해하기 쉽다.

```text
Trigger contract
  -> 무엇이 이 DAG run을 시작하게 하는가

Expansion contract
  -> 실행 시점에 작업을 어떤 단위로 나누는가

Waiting contract
  -> 기다림이 필요한 작업은 어떤 자원을 점유하는가

Concurrency contract
  -> Airflow와 외부 시스템에 동시에 얼마만큼의 부하를 허용하는가
```

Datasets는 trigger contract를, dynamic task mapping은 expansion contract를, deferrable operator는 waiting contract를, pools와 concurrency 설정은 concurrency contract를 다룬다.

이 기능들을 따로 외우면 "새로운 Airflow 문법"처럼 보인다. 함께 보면 DAG가 늘어나도 플랫폼이 무너지지 않게 만드는 운영 장치다.

---

## 핵심 개념 1: Datasets는 DAG 간 의존성을 시간표가 아니라 데이터 이벤트로 바꾼다

전통적인 Airflow DAG는 schedule 중심이다.

```python
with DAG(
    dag_id="build_daily_order_mart",
    schedule="0 3 * * *",
):
    ...
```

이 방식은 단순하고 예측 가능하다. 하지만 upstream 데이터가 언제 준비되는지 변동이 큰 환경에서는 schedule만으로는 부족하다.

예를 들어 raw order ingestion DAG가 있다.

- 보통 01:20에 끝난다
- 월요일에는 원천 API가 느려서 02:10에 끝난다
- 장애 복구일에는 04:00에 끝난다
- 특정 파티션 검증 실패로 일부 날짜만 다시 적재된다

downstream mart DAG를 매일 03:00에 고정 실행하면 평소에는 잘 돌아간다. 그러나 upstream이 늦으면 비어 있는 staging을 읽고 성공하거나, 실패 후 재시도하며 불필요한 부하를 만든다. 반대로 너무 늦게 schedule을 잡으면 정상일에도 latency가 늘어난다.

이때 Datasets를 사용하면 "03:00이 되었는가"가 아니라 **어떤 데이터 산출물이 갱신되었는가**를 DAG trigger 조건으로 삼을 수 있다.

### Dataset으로 산출물 이벤트 표현하기

개념적으로는 upstream task가 dataset을 업데이트하고, downstream DAG가 그 dataset을 구독한다.

```python
from airflow import Dataset
from airflow.decorators import dag, task
from pendulum import datetime

orders_raw = Dataset("s3://company-data/raw/orders/dt")

@dag(
    dag_id="ingest_orders_raw",
    start_date=datetime(2026, 7, 1, tz="Asia/Seoul"),
    schedule="0 1 * * *",
    catchup=False,
)
def ingest_orders_raw():
    @task(outlets=[orders_raw])
    def extract_orders():
        # API -> object storage
        # validation 성공 후에만 dataset update 이벤트를 발생시킨다.
        return "ok"

    extract_orders()

ingest_orders_raw()
```

downstream은 schedule에 dataset을 넣는다.

```python
@dag(
    dag_id="build_order_mart",
    start_date=datetime(2026, 7, 1, tz="Asia/Seoul"),
    schedule=[orders_raw],
    catchup=False,
)
def build_order_mart():
    ...

build_order_mart()
```

이 구조의 장점은 명확하다.

- upstream 완료 시점이 흔들려도 downstream은 데이터 준비 후 실행된다
- DAG 간 의존성을 `ExternalTaskSensor`보다 더 선언적으로 표현할 수 있다
- 산출물 중심으로 lineage를 읽기 쉬워진다
- schedule chain보다 데이터 플랫폼의 실제 의존 관계에 가깝다

하지만 Datasets가 모든 문제를 해결하지는 않는다.

### Dataset은 "데이터가 올바르다"를 자동 보장하지 않는다

Dataset update 이벤트는 task 성공과 연결된다. task가 성공으로 끝났다고 해서 데이터 품질이 자동으로 보장되는 것은 아니다. 따라서 dataset을 outlet으로 선언하는 task는 최소한 아래 조건을 만족해야 한다.

- 대상 파티션 쓰기가 완료되었다
- row count, null check, 중복 key check 같은 기본 검증이 통과했다
- downstream이 읽을 경로와 catalog metadata가 갱신되었다
- 실패 시 부분 산출물이 보이지 않도록 staging 또는 atomic publish 전략을 쓴다

나쁜 패턴은 extract task가 파일 몇 개를 쓰기 시작하자마자 성공으로 끝나고 dataset 이벤트를 발생시키는 것이다. downstream은 "dataset이 준비되었다"고 믿고 실행되지만 실제로는 일부 파일만 존재할 수 있다.

Dataset은 데이터 준비 이벤트를 표현하는 기능이지, 데이터 계약 전체를 대체하는 기능이 아니다.

### 여러 dataset을 조합할 때의 함정

하나의 mart DAG가 주문, 결제, 환불 데이터를 모두 필요로 한다고 하자.

```python
schedule=[orders_raw, payments_raw, refunds_raw]
```

이 구조를 쓸 때는 각 dataset 이벤트가 어떤 날짜 파티션을 의미하는지 조심해야 한다. Airflow의 dataset 이벤트는 URI 수준의 이벤트이지, 기본적으로 `dt=2026-07-10` 같은 파티션 의미를 강하게 타입화하지 않는다.

따라서 실무에서는 다음 중 하나를 선택해야 한다.

- dataset URI에 파티션 단위를 넣어 세밀하게 모델링한다
- downstream DAG 안에서 처리 대상 interval을 다시 계산하고 검증한다
- dataset은 trigger hint로만 쓰고, 실제 readiness는 warehouse metadata table로 확인한다

예를 들어 대규모 플랫폼에서는 별도 readiness table을 두기도 한다.

```sql
create table data_asset_readiness (
    asset_name text not null,
    partition_date date not null,
    status text not null,
    row_count bigint,
    checksum text,
    published_at timestamptz not null,
    primary key (asset_name, partition_date)
);
```

Dataset 이벤트는 downstream을 깨우는 역할을 하고, downstream은 이 테이블을 조회해 필요한 모든 파티션이 `published`인지 확인한다. 이 방식은 조금 더 복잡하지만, 파티션 단위 데이터 계약을 명확히 만들 수 있다.

### Dataset을 써야 하는 경우와 아닌 경우

Dataset이 잘 맞는 경우:

- DAG 간 의존성이 시간보다 데이터 산출물에 가깝다
- upstream 완료 시각 변동이 크다
- downstream DAG가 여러 upstream 산출물을 기다려야 한다
- 데이터 lineage를 DAG 코드에 드러내고 싶다
- schedule chain과 sensor가 복잡해져 운영자가 읽기 어렵다

Dataset이 애매한 경우:

- 단순히 매일 정해진 시각에 실행하면 충분하다
- upstream과 downstream이 같은 DAG 안의 task dependency로 표현 가능하다
- 파티션별 readiness가 매우 중요하지만 별도 metadata 모델이 없다
- dataset 이벤트만으로는 어떤 구간을 처리해야 하는지 판단하기 어렵다

좋은 기준은 이것이다.

> Dataset은 "이 산출물이 publish되면 downstream을 시작한다"는 의미가 팀에서 합의되어 있을 때 강력하다.

그 합의가 없으면 dataset은 이름만 멋진 trigger가 되고, 실제 운영 판단은 여전히 코드 곳곳에 흩어진다.

---

## 핵심 개념 2: Dynamic Task Mapping은 fan-out을 코드 작성 시점이 아니라 실행 시점으로 미룬다

Airflow DAG는 기본적으로 parse time에 구조가 정해진다. 그래서 예전에는 고객사 100개를 처리하려면 DAG 파일을 만들 때 100개 task를 반복문으로 생성하는 패턴이 흔했다.

```python
for tenant in TENANTS:
    build_tenant_report(tenant)
```

이 방식은 작은 규모에서는 괜찮다. 하지만 tenant 목록이 DB에서 바뀌거나, 날짜별 파일 목록을 실행 시점에 object storage에서 읽어야 하거나, upstream 결과에 따라 처리 단위가 달라지면 parse time 반복문은 한계가 있다.

Dynamic task mapping은 이 문제를 해결한다. 먼저 실행 시점에 처리 대상 목록을 만들고, 그 결과를 기준으로 task instance를 확장한다.

### 파티션 목록 기반 fan-out

예를 들어 object storage에 도착한 파티션 목록을 읽어 검증 작업을 병렬로 수행한다고 하자.

```python
from airflow.decorators import dag, task
from pendulum import datetime

@dag(
    dag_id="validate_arrived_partitions",
    start_date=datetime(2026, 7, 1, tz="Asia/Seoul"),
    schedule="@hourly",
    catchup=False,
    max_active_runs=1,
)
def validate_arrived_partitions():
    @task
    def list_partitions() -> list[dict]:
        return [
            {"dt": "2026-07-11", "region": "kr"},
            {"dt": "2026-07-11", "region": "jp"},
            {"dt": "2026-07-11", "region": "sg"},
        ]

    @task
    def validate_partition(partition: dict) -> dict:
        # row count, schema, duplicate key check
        return {**partition, "status": "valid"}

    validate_partition.expand(partition=list_partitions())

validate_arrived_partitions()
```

이 구조의 핵심은 `list_partitions()`가 실행된 뒤에야 몇 개의 `validate_partition` task instance가 생기는 것이다. 실제 데이터 도착 상태에 맞춰 fan-out할 수 있다.

### Dynamic mapping이 필요한 대표 사례

- S3/GCS prefix 아래에 도착한 파일 목록별 처리
- tenant, account, workspace별 리포트 생성
- warehouse partition별 품질 검증
- 모델 학습 대상 segment별 feature 생성
- API pagination 결과별 후속 처리
- 데이터 contract 위반 목록별 remediation task 실행

정적 DAG 반복문과 dynamic mapping의 차이는 "반복문 위치"가 아니다. 운영 의미가 다르다.

```text
정적 반복문
  -> DAG parse 시점에 처리 단위가 이미 알려져 있다

dynamic mapping
  -> DAG run 실행 중에 처리 단위가 결정된다
```

이 차이는 배포와 운영 모두에 영향을 준다.

정적 반복문은 코드 변경이나 variable 변경이 scheduler parse에 영향을 준다. 처리 대상이 너무 많으면 DAG parse가 느려지고 UI가 무거워진다. 반면 dynamic mapping은 실제 DAG run에서 필요한 만큼 task instance를 만들 수 있어 데이터 기반 fan-out에 적합하다.

### 너무 큰 fan-out은 scheduler와 metadata DB를 압박한다

Dynamic task mapping은 편하지만 남용하면 Airflow metadata DB가 먼저 아파진다. mapping 결과가 10개, 100개라면 자연스럽다. 그러나 한 DAG run에서 50,000개 task instance를 만들면 이야기가 달라진다.

각 mapped task는 metadata DB row, scheduling decision, log, 상태 전이를 만든다. 작업 자체가 아주 작다면 task 실행 시간보다 Airflow orchestration overhead가 더 커질 수 있다.

예를 들어 파일 10만 개를 파일 하나당 task 하나로 처리하는 DAG는 대개 나쁜 설계다.

```text
bad:
  file 1개 = task 1개

better:
  prefix 또는 shard 단위로 묶어서 task 1개가 여러 파일 처리
```

실무 기준은 대략 이렇게 잡을 수 있다.

- task 하나가 수 초 이하라면 너무 잘게 쪼갰을 가능성이 크다
- mapped task 수가 수천 개 이상이면 batch size와 shard 전략을 검토한다
- 실패 재시도 단위가 의미 있는 크기인지 확인한다
- UI에서 운영자가 실패 원인을 읽을 수 있는 단위인지 본다
- metadata DB와 scheduler 성능 지표를 함께 본다

Dynamic mapping은 병렬성을 공짜로 주는 기능이 아니다. **작업 단위를 실행 시점에 결정할 수 있게 해주는 기능**이다. 병렬성은 그 다음에 pools, executor capacity, 외부 시스템 한도와 함께 조절해야 한다.

### map, reduce 패턴에서 XCom 크기를 조심하라

mapped task 결과를 모아 downstream task에서 reduce하는 패턴도 흔하다.

```python
@task
def summarize(results: list[dict]):
    ...

summarize(validate_partition.expand(partition=list_partitions()))
```

작은 dict 목록이라면 괜찮다. 하지만 각 task가 큰 payload를 XCom으로 넘기면 metadata DB가 커지고 scheduler/UI 성능이 떨어진다. Airflow XCom은 대용량 데이터 전달 계층이 아니다.

좋은 패턴은 이렇다.

- mapped task는 결과 자체가 아니라 결과 위치 또는 요약 metadata만 반환한다
- 큰 결과는 object storage, warehouse, artifact store에 저장한다
- reduce task는 경로 목록이나 manifest를 읽어 집계한다

예를 들어 각 partition 검증 결과를 JSON 파일로 저장하고 XCom에는 URI만 남긴다.

```python
@task
def validate_partition(partition: dict) -> str:
    result_uri = f"s3://company-data/validation/{partition['dt']}/{partition['region']}.json"
    # validation result write
    return result_uri
```

이렇게 하면 Airflow metadata DB는 orchestration metadata만 다루고, 데이터 payload는 데이터 저장소가 맡는다.

---

## 핵심 개념 3: Deferrable Operator는 기다림의 비용을 worker에서 triggerer로 옮긴다

Airflow 운영에서 자주 보이는 병목 중 하나가 sensor다.

- S3 파일이 생길 때까지 기다린다
- 외부 API job이 완료될 때까지 polling한다
- Dataproc, EMR, Spark, dbt Cloud, Fivetran connector 상태를 기다린다
- upstream DAG run 완료를 기다린다

기본 sensor가 `poke` 모드로 동작하면 worker slot을 점유한 채 주기적으로 조건을 확인한다. 기다리는 시간이 30분이고 sensor가 200개라면, 실제로 CPU를 쓰지 않아도 worker capacity를 크게 잠식한다.

`reschedule` 모드는 poke 사이에 worker slot을 반납할 수 있지만, 모든 operator가 자연스럽게 지원하는 것은 아니고 scheduling overhead가 생긴다. Airflow 2.x 이후의 deferrable operator는 이 문제를 더 구조적으로 다룬다.

### deferrable의 동작 직관

Deferrable operator는 조건을 기다리는 동안 task를 defer 상태로 보내고, triggerer 프로세스가 비동기 이벤트를 감시한다. 조건이 만족되면 task가 다시 worker에 올라와 후속 처리를 마친다.

```text
worker starts task
  -> external job submit
  -> task defers and releases worker slot
  -> triggerer waits asynchronously
  -> event arrives
  -> task resumes on worker
  -> finalize
```

이 구조의 장점은 명확하다.

- 기다리는 task가 worker slot을 오래 점유하지 않는다
- long polling workload가 많아도 worker를 실제 계산 작업에 쓸 수 있다
- 외부 job orchestration과 Airflow executor capacity를 분리하기 쉽다

예를 들어 Spark job을 제출한 뒤 완료를 기다리는 task가 있다고 하자. Spark cluster에서 40분 동안 처리하는 동안 Airflow worker가 할 일은 거의 없다. 이때 worker slot을 잡고 기다리는 것은 낭비다. deferrable operator를 쓰면 제출 직후 slot을 반납하고, 완료 이벤트가 왔을 때만 다시 worker가 필요하다.

### deferrable을 써야 하는 경우

- 외부 시스템 상태를 오래 polling한다
- sensor 개수가 많아 worker slot 고갈이 자주 발생한다
- task 대부분의 시간이 CPU 계산이 아니라 대기다
- Spark, Kubernetes, cloud batch job처럼 Airflow 밖에서 실제 실행이 일어난다
- worker auto-scaling 비용을 줄이고 싶다

반대로 아래 경우에는 굳이 deferrable이 핵심이 아닐 수 있다.

- task가 대부분 로컬 Python 계산이다
- 대기 시간이 짧고 sensor 수가 적다
- operator/provider가 deferrable mode를 안정적으로 지원하지 않는다
- triggerer 운영과 모니터링을 아직 준비하지 않았다

### triggerer도 운영 대상이다

Deferrable operator를 도입할 때 흔한 실수는 worker slot만 보고 triggerer를 잊는 것이다. 기다림의 비용은 사라지는 것이 아니라 triggerer로 이동한다. 따라서 triggerer 프로세스 상태, 이벤트 루프 지연, capacity, provider 호환성을 모니터링해야 한다.

운영 체크 포인트는 다음과 같다.

- triggerer 프로세스가 고가용성으로 떠 있는가
- deferrable task 수 증가에 따라 triggerer CPU와 memory가 안정적인가
- provider 버전이 사용하는 deferrable operator를 제대로 지원하는가
- trigger event가 누락되거나 재개가 지연될 때 alert이 있는가
- triggerer 장애 후 task가 정상적으로 복구되는지 테스트했는가

Deferrable operator는 "sensor를 빠르게 만드는 옵션"이 아니다. Airflow worker가 실제 실행에 집중하도록 **대기 상태를 별도 런타임으로 분리하는 설계**다.

---

## 핵심 개념 4: Pools는 외부 시스템의 동시성 예산을 Airflow에 알려주는 장치다

Airflow worker가 100개 task를 동시에 실행할 수 있다고 해서 외부 시스템도 100개 요청을 받아도 된다는 뜻은 아니다.

예를 들어 다음 시스템들은 각각 별도의 한도를 가진다.

- PostgreSQL reporting replica: 동시 heavy query 5개
- Snowflake warehouse: 비용과 queue time을 고려해 동시 transform 12개
- 외부 CRM API: 초당 요청 20개, 동시 job 3개
- Elasticsearch cluster: bulk indexing worker 8개
- 내부 feature store: partition write 동시 10개

Airflow executor capacity만 보고 병렬성을 열면 외부 시스템이 먼저 병목이 된다. 그 결과는 DAG 실패가 아니라 더 나쁜 형태로 나타난다.

- warehouse query queue가 길어져 전체 배치 시간이 늘어난다
- DB connection pool이 고갈된다
- 외부 API rate limit으로 retry storm이 발생한다
- bulk write가 cluster CPU를 밀어붙여 온라인 query latency가 튄다
- 하나의 backfill이 정규 운영 DAG를 모두 밀어낸다

Pools는 이런 외부 시스템 예산을 Airflow scheduler에 알려주는 기능이다.

### pool을 리소스별로 나누기

예를 들어 warehouse transform용 pool을 만든다.

```text
pool: warehouse_heavy_transform
slots: 8
```

그리고 무거운 SQL task에 이 pool을 지정한다.

```python
run_heavy_transform = SQLExecuteQueryOperator(
    task_id="run_heavy_transform",
    conn_id="warehouse",
    sql="sql/build_large_mart.sql",
    pool="warehouse_heavy_transform",
    pool_slots=2,
)
```

가벼운 query는 `pool_slots=1`, 매우 무거운 transform은 `pool_slots=2` 또는 `4`처럼 가중치를 둘 수 있다. 이렇게 하면 Airflow worker가 충분히 남아 있어도 warehouse 예산을 넘는 task는 scheduler가 대기시킨다.

중요한 점은 pool을 Airflow 내부 기술 기준이 아니라 **외부 병목 기준**으로 설계해야 한다는 것이다.

좋은 pool 이름:

- `warehouse_heavy_transform`
- `crm_api_write`
- `spark_cluster_submit`
- `reporting_replica_query`
- `elasticsearch_bulk_index`

애매한 pool 이름:

- `default_big`
- `team_a_pool`
- `slow_tasks`
- `batch_pool`

pool 이름만 보고 어떤 리소스를 보호하는지 알아야 운영자가 판단할 수 있다.

### pool은 rate limit이 아니다

Pool은 동시성 제한이다. 초당 요청 수를 직접 제한하는 rate limiter는 아니다. 외부 API가 "초당 20회" 제한을 가진다면 pool만으로는 부족할 수 있다. task 내부에서 token bucket, backoff, provider hook의 retry 설정, API gateway rate limit을 함께 써야 한다.

Pool이 잘하는 것:

- 동시에 실행 중인 task 수 제한
- 무거운 작업의 slot 가중치 표현
- 여러 DAG가 공유하는 외부 리소스 보호

Pool이 잘하지 못하는 것:

- 초당 요청 수 제한
- payload 크기 기반 동적 제한
- 외부 시스템 실시간 부하에 따른 자동 조절
- task 내부 loop에서 발생하는 수천 개 API call 제어

따라서 API를 다루는 task는 보통 두 층의 제어가 필요하다.

```text
Airflow pool
  -> 동시에 실행되는 task 수 제한

task 내부 rate limiter
  -> task 하나가 보내는 요청 속도 제한
```

둘 중 하나만 있으면 장애 형태가 달라질 뿐 완전히 안전하지 않다.

### priority_weight는 장애 복구 때 빛난다

Pool을 쓰다 보면 queue가 생긴다. 이때 모든 task가 같은 우선순위라면 backfill, ad-hoc 재처리, 정규 운영 배치가 서로 섞인다. 운영적으로 중요한 것은 정규 SLA를 가진 DAG가 밀리지 않도록 우선순위를 두는 것이다.

예를 들어 매일 아침 08:00 전에 완료되어야 하는 executive dashboard refresh는 backfill보다 우선되어야 한다. 반대로 과거 180일 재처리는 낮은 priority로 pool의 남는 capacity를 사용하게 둘 수 있다.

```python
critical_refresh = SQLExecuteQueryOperator(
    task_id="critical_refresh",
    conn_id="warehouse",
    sql="sql/refresh_dashboard.sql",
    pool="warehouse_heavy_transform",
    priority_weight=100,
)

historical_backfill = SQLExecuteQueryOperator(
    task_id="historical_backfill",
    conn_id="warehouse",
    sql="sql/backfill_old_partition.sql",
    pool="warehouse_heavy_transform",
    priority_weight=10,
)
```

이 설정은 단순 튜닝이 아니다. 조직이 어떤 workload를 먼저 살릴지 Airflow에 표현하는 일이다.

---

## 핵심 개념 5: DAG-level concurrency는 catchup과 함께 설계해야 한다

Airflow에는 동시성을 제어하는 설정이 여러 층에 있다. 이들이 서로 겹치기 때문에 하나만 보고 판단하면 예상과 다른 실행 패턴이 나온다.

대표적으로 아래가 있다.

- `max_active_runs`: 한 DAG에서 동시에 active 상태일 수 있는 DAG run 수
- `max_active_tasks`: 한 DAG에서 동시에 실행 가능한 task 수
- task-level `pool`: 공유 리소스별 slot 제한
- task-level `task_concurrency` 또는 유사 설정: 특정 task의 동시 실행 제한
- environment-level parallelism: 전체 Airflow 인스턴스의 최대 task 실행 수
- executor/worker capacity: 실제 실행 슬롯

이 설정은 catchup과 backfill 때 특히 중요하다.

### catchup이 만드는 예상 밖의 폭발

매일 도는 DAG가 30일 동안 멈췄다가 다시 켜졌다고 하자. `catchup=True`이고 시작일 이후 실행되지 않은 interval이 많으면 scheduler는 과거 DAG run을 만들 수 있다.

이때 `max_active_runs`가 높고 task fan-out도 크면 순식간에 수백, 수천 개 task instance가 생긴다.

```text
30 missed DAG runs
  x 40 mapped tasks per run
  = 1,200 task instances
```

이 자체가 항상 나쁜 것은 아니다. 문제는 외부 시스템이 이 부하를 감당할 준비가 되어 있느냐다. warehouse pool, API pool, max active runs가 없다면 복구 작업이 정규 운영을 압도한다.

실무에서는 DAG 성격별로 기본값을 다르게 둔다.

### 정규 일별 mart DAG

```python
@dag(
    dag_id="build_daily_mart",
    schedule="0 3 * * *",
    catchup=True,
    max_active_runs=1,
    max_active_tasks=8,
)
def build_daily_mart():
    ...
```

특징:

- 날짜 순서가 중요하다
- 같은 mart table을 여러 interval이 동시에 쓰면 위험할 수 있다
- backfill은 느려도 예측 가능해야 한다

`max_active_runs=1`은 보수적이지만 운영 친화적이다. 과거 구간을 순서대로 처리하고, output partition 충돌 가능성을 줄인다.

### 독립 파티션 검증 DAG

```python
@dag(
    dag_id="validate_partitions",
    schedule="@hourly",
    catchup=False,
    max_active_runs=2,
    max_active_tasks=32,
)
def validate_partitions():
    ...
```

특징:

- 각 파티션 검증이 독립적이다
- 실패 단위가 작다
- output write가 크지 않다
- 빠른 병렬성이 중요하다

이 경우는 동시성을 더 열 수 있다. 대신 metadata DB와 pool을 모니터링해야 한다.

### 대규모 backfill 전용 DAG

정규 DAG에 backfill 로직을 억지로 태우는 대신, backfill 전용 DAG를 별도로 두는 것도 좋은 선택이다.

```python
@dag(
    dag_id="backfill_order_mart_manual",
    schedule=None,
    catchup=False,
    max_active_runs=1,
    max_active_tasks=4,
)
def backfill_order_mart_manual():
    ...
```

이 DAG는 낮은 priority와 별도 pool을 사용한다.

```text
pool: warehouse_backfill
slots: 2
priority: low
```

이렇게 하면 정규 운영 DAG의 SLA를 보호하면서 과거 재처리를 수행할 수 있다.

### 동시성 설정의 판단 기준

동시성은 "빨리 끝내기"가 아니라 "어디까지 동시에 실패해도 감당 가능한가"로 정해야 한다.

아래 질문에 답해보면 적정값이 나온다.

- 같은 DAG run 여러 개가 같은 테이블이나 파티션을 동시에 쓸 수 있는가
- source API가 동시에 몇 개 요청까지 허용하는가
- warehouse가 heavy query 몇 개까지 안정적인가
- task 하나가 실패하면 재시도 비용은 얼마인가
- 100개 task가 동시에 실패하면 alert와 로그를 운영자가 읽을 수 있는가
- catchup이 켜졌을 때 missed interval이 몇 개까지 쌓일 수 있는가

Airflow 설정값은 숫자지만, 실제 의미는 운영 정책이다.

---

## 실무 예시: 데이터 준비 이벤트 기반 mart 빌드 DAG 설계

가상의 이커머스 데이터 플랫폼을 생각해보자.

요구사항은 다음과 같다.

- 주문, 결제, 환불 raw 데이터가 각각 다른 DAG에서 적재된다
- 세 raw 데이터가 모두 특정 날짜에 대해 publish되면 일별 mart를 만든다
- mart는 국가별로 병렬 생성한다
- warehouse heavy transform은 동시에 8 slot만 허용한다
- 외부 dashboard refresh는 mart 성공 후 실행하되 API 동시 호출은 2개로 제한한다
- raw 적재 지연이 있으면 schedule이 아니라 데이터 준비 이벤트를 기준으로 실행하고 싶다

이 설계는 여러 Airflow 기능을 함께 써야 한다.

### 1단계: 데이터 산출물을 Dataset으로 선언한다

```python
orders_raw = Dataset("warehouse://raw.orders")
payments_raw = Dataset("warehouse://raw.payments")
refunds_raw = Dataset("warehouse://raw.refunds")
daily_order_mart = Dataset("warehouse://mart.daily_order")
```

각 raw ingestion DAG는 검증 성공 후 outlet을 발생시킨다.

```python
@task(outlets=[orders_raw])
def publish_orders_raw(data_interval_start=None, data_interval_end=None):
    # extract -> stage -> validate -> publish
    # readiness table에도 partition_date, row_count, checksum 기록
    ...
```

중요한 것은 publish task가 실제 publish 완료 후에만 성공해야 한다는 점이다.

### 2단계: mart DAG는 dataset 이벤트로 깨우되 readiness table을 다시 확인한다

```python
@dag(
    dag_id="build_daily_order_mart",
    schedule=[orders_raw, payments_raw, refunds_raw],
    catchup=False,
    max_active_runs=1,
    max_active_tasks=12,
)
def build_daily_order_mart():
    ...
```

Dataset 이벤트는 DAG를 시작시키는 신호다. 하지만 DAG 내부에서는 어떤 날짜를 처리할지 readiness table로 확정한다.

```python
@task
def find_ready_partitions() -> list[dict]:
    """
    readiness table에서 orders/payments/refunds가 모두 published인 날짜와 국가를 찾는다.
    이미 mart가 성공한 partition은 제외한다.
    """
    return [
        {"dt": "2026-07-10", "country": "KR"},
        {"dt": "2026-07-10", "country": "JP"},
        {"dt": "2026-07-10", "country": "SG"},
    ]
```

이렇게 하면 dataset이 DAG를 깨우고, 실제 처리 단위는 운영 metadata로 결정된다.

### 3단계: 국가별 mart 빌드는 dynamic mapping으로 확장한다

```python
@task(pool="warehouse_heavy_transform", pool_slots=2)
def build_country_mart(partition: dict) -> str:
    dt = partition["dt"]
    country = partition["country"]
    output_partition = f"dt={dt}/country={country}"

    # staging table에 먼저 계산
    # 품질 검증 후 mart partition publish
    # 성공 시 artifact URI 또는 partition key 반환
    return output_partition

published_partitions = build_country_mart.expand(
    partition=find_ready_partitions()
)
```

여기서 `pool_slots=2`를 준 이유는 country mart 하나가 warehouse에 꽤 무거운 query를 날린다고 가정했기 때문이다. pool 전체가 8 slot이면 동시에 4개 country mart만 실행된다.

### 4단계: publish 결과를 모아 manifest를 만든다

```python
@task(outlets=[daily_order_mart])
def publish_manifest(partitions: list[str]) -> str:
    # mart publish metadata 기록
    # lineage, row count, checksum, generated_at 저장
    return "warehouse://mart.daily_order/manifest/2026-07-10"
```

이 task가 성공해야 downstream dashboard DAG가 `daily_order_mart` dataset 이벤트를 받을 수 있다.

### 5단계: dashboard refresh는 API pool과 deferrable operator를 고려한다

dashboard refresh가 외부 SaaS API job을 제출하고 완료를 기다리는 구조라면, 두 가지가 필요하다.

- `dashboard_api` pool로 동시 제출 수 제한
- provider가 지원한다면 deferrable operator로 완료 대기 중 worker slot 반납

```python
refresh_dashboard = SomeDashboardRefreshOperator(
    task_id="refresh_dashboard",
    dashboard_id="daily-order",
    pool="dashboard_api",
    deferrable=True,
)
```

만약 provider가 deferrable을 지원하지 않는다면, API job submit task와 status polling sensor를 분리하고 `reschedule` 또는 별도 lightweight polling 전략을 검토한다.

이 예시는 단순한 DAG 코드보다 운영 계약이 더 중요하다는 것을 보여준다.

```text
Dataset
  -> raw publish와 mart publish 이벤트 표현

Readiness table
  -> 파티션 단위 준비 상태 검증

Dynamic task mapping
  -> 준비된 country partition만 fan-out

Pool
  -> warehouse와 dashboard API 동시성 보호

Deferrable operator
  -> 외부 job 대기 중 worker slot 보호

max_active_runs/max_active_tasks
  -> DAG run 폭주 방지
```

이 정도 구조가 잡히면 DAG 수가 늘어나도 운영자가 어디를 조절해야 하는지 알 수 있다.

---

## 트레이드오프: 선언적 오케스트레이션은 복잡도를 없애지 않고 위치를 바꾼다

Datasets, dynamic mapping, deferrable operator, pools를 쓰면 Airflow가 더 우아해 보인다. 하지만 이 기능들은 복잡도를 없애지 않는다. 복잡도가 숨어 있던 위치를 명시적인 운영 모델로 옮긴다.

### Datasets의 트레이드오프

장점:

- 시간표가 아니라 데이터 준비 이벤트로 DAG를 연결한다
- DAG 간 관계를 더 읽기 쉽게 만든다
- upstream 지연에 자연스럽게 대응한다

비용:

- dataset 이벤트와 파티션 의미를 별도로 설계해야 한다
- task 성공과 데이터 품질 성공을 혼동하기 쉽다
- 복잡한 조건은 readiness table이나 data catalog와 함께 써야 한다

### Dynamic task mapping의 트레이드오프

장점:

- 실행 시점 데이터에 따라 fan-out할 수 있다
- 정적 DAG 반복문보다 유연하다
- tenant/partition/file 단위 처리에 잘 맞는다

비용:

- mapped task 수가 커지면 metadata DB와 scheduler 부담이 커진다
- UI가 복잡해질 수 있다
- XCom payload 관리가 중요해진다
- 너무 작은 작업을 task로 쪼개면 orchestration overhead가 커진다

### Deferrable operator의 트레이드오프

장점:

- worker slot을 오래 점유하는 sensor 비용을 줄인다
- 외부 job 대기 workload에 적합하다
- worker capacity를 실제 실행 작업에 집중시킨다

비용:

- triggerer 운영과 모니터링이 필요하다
- provider별 안정성과 기능 차이를 확인해야 한다
- 대기 상태와 재개 상태를 이해해야 장애 대응이 가능하다

### Pools의 트레이드오프

장점:

- 외부 시스템 동시성 예산을 Airflow에 표현한다
- 여러 DAG가 공유하는 병목 리소스를 보호한다
- backfill과 정규 workload 간 충돌을 줄인다

비용:

- pool 값이 너무 낮으면 전체 처리량이 불필요하게 낮아진다
- pool 값이 너무 높으면 보호 효과가 사라진다
- rate limit과 혼동하면 API 장애를 막지 못한다
- 운영 중 리소스 변화에 맞춰 조정해야 한다

즉 이 기능들의 도입 기준은 "Airflow 최신 기능이라서"가 아니다. DAG 간 의존성, fan-out, 대기 비용, 외부 리소스 한도가 실제 운영 문제가 되었을 때 도입해야 한다.

---

## 흔한 실수 1: Dataset 이벤트만 믿고 데이터 품질 검증을 생략한다

Dataset을 도입하면 downstream DAG가 깔끔하게 실행된다. 그래서 팀이 "upstream이 dataset을 업데이트했으니 준비 완료"라고 착각하기 쉽다.

하지만 upstream task가 다음 상태에서도 성공할 수 있다면 위험하다.

- 일부 파일만 쓰고 성공
- schema drift가 있는데 row count만 보고 성공
- 중복 key가 있는데 append만 하고 성공
- catalog partition 등록 전에 성공
- retry 중 이전 partial output이 남아 있음

해결책은 dataset outlet을 publish task 마지막에만 두는 것이다. publish task는 다음을 포함해야 한다.

- staging output 생성
- 품질 검증
- atomic publish 또는 partition swap
- readiness metadata 기록
- 그 뒤 dataset event 발생

Dataset은 "검증된 산출물 publish"와 연결될 때 의미가 있다.

---

## 흔한 실수 2: Dynamic mapping으로 너무 작은 작업까지 task로 만든다

파일 하나, API row 하나, 고객 한 명을 각각 task로 만들면 병렬성이 좋아 보인다. 하지만 Airflow task는 가벼운 함수 호출이 아니라 orchestration 단위다.

작업 단위가 너무 작으면 다음 문제가 생긴다.

- scheduler가 task instance를 관리하는 시간이 실제 처리 시간보다 커진다
- metadata DB가 커진다
- task log가 너무 잘게 쪼개져 운영자가 읽기 어렵다
- retry storm이 발생한다
- UI가 느려진다

해결책은 shard 단위를 둔다.

```text
bad:
  1 file -> 1 task

better:
  1 prefix/hour/tenant shard -> 1 task

best:
  실패 복구와 운영 관찰이 가능한 최소 의미 단위 -> 1 task
```

Airflow는 대용량 분산 처리 엔진이 아니다. Spark, Flink, warehouse가 해야 할 내부 병렬 처리를 Airflow task 수로 대체하지 말아야 한다.

---

## 흔한 실수 3: sensor를 늘리면서 worker만 증설한다

Sensor가 worker slot을 잡아먹어 queue가 쌓이면 가장 쉬운 대응은 worker를 늘리는 것이다. 하지만 sensor 대부분이 "기다리는 일"이라면 worker 증설은 비용 효율이 낮다.

먼저 확인해야 할 것은 다음이다.

- sensor가 poke 모드인가
- reschedule 모드가 가능한가
- deferrable operator가 provider에서 지원되는가
- sensor timeout과 poke interval이 현실적인가
- 외부 job completion event를 더 직접적으로 받을 수 있는가

worker를 늘리기 전에 기다림을 worker 밖으로 빼는 설계를 검토해야 한다.

---

## 흔한 실수 4: pool을 팀별로만 나눈다

팀별 pool은 예산 관리에는 도움이 될 수 있다. 하지만 외부 시스템 보호에는 약하다. 팀 A와 팀 B가 같은 warehouse를 두드리는데 pool이 팀별로만 나뉘어 있으면 warehouse 관점의 총 동시성 제한이 없다.

pool은 우선 리소스별로 잡는 편이 좋다.

```text
warehouse_heavy_transform
warehouse_light_query
crm_api_write
reporting_replica_read
spark_submit
```

그 위에 팀별 quota가 필요하다면 별도 정책이나 DAG priority, queue, executor 분리로 보완한다. pool의 1차 목적은 "누가 쓰는가"보다 "무엇을 보호하는가"다.

---

## 흔한 실수 5: catchup을 켜놓고 max_active_runs를 방치한다

`catchup=True` 자체는 나쁜 설정이 아니다. 데이터 interval을 놓치지 않고 처리해야 하는 DAG에는 필요하다. 문제는 catchup이 만드는 과거 DAG run 폭주를 제어하지 않는 것이다.

특히 dynamic mapping과 결합되면 폭발이 커진다.

```text
missed 20 runs
  x each run maps to 100 partitions
  = 2,000 task instances
```

여기에 pool이 없고 warehouse query가 무겁다면 복구가 아니라 장애 확산이 된다.

해결책:

- 정규 DAG는 `max_active_runs=1` 또는 보수적인 값으로 시작한다
- backfill은 별도 DAG 또는 별도 pool로 분리한다
- 대규모 과거 재처리는 낮은 priority를 준다
- mapped task 수 상한과 shard 크기를 둔다
- catchup 테스트를 staging에서 실제 interval 수로 해본다

Airflow의 catchup은 편리하지만, 운영 예산 없이 켜면 scheduler가 과거 일을 너무 성실하게 밀어붙인다.

---

## 체크리스트: Airflow DAG가 늘어나기 전에 확인할 것

### Trigger contract

- DAG 실행 조건이 시간인지 데이터 준비 이벤트인지 명확한가
- Dataset을 쓴다면 task 성공과 데이터 publish 성공이 일치하는가
- 파티션 단위 readiness를 별도 metadata로 검증하는가
- upstream 지연 시 downstream이 빈 데이터를 읽지 않는가
- dataset URI와 실제 데이터 자산 이름 규칙이 팀 내에서 일관적인가

### Expansion contract

- fan-out 단위가 parse time에 고정되어야 하는가, 실행 시점에 결정되어야 하는가
- dynamic mapping 결과 개수가 운영 가능한 수준인가
- task 하나가 너무 작거나 너무 크지 않은가
- mapped task 결과를 XCom에 크게 싣고 있지 않은가
- 실패 재시도 단위가 운영자가 이해할 수 있는 단위인가

### Waiting contract

- sensor가 worker slot을 오래 점유하고 있지 않은가
- provider가 deferrable operator를 지원하는가
- triggerer 프로세스 모니터링과 alert이 있는가
- timeout, poke interval, retry 정책이 외부 시스템 SLA와 맞는가
- 외부 job submit과 completion wait가 분리되어 있는가

### Concurrency contract

- 보호해야 할 외부 리소스별 pool이 있는가
- pool slot 수가 실제 시스템 capacity와 연결되어 있는가
- API rate limit은 pool 외에 task 내부에서도 제어하는가
- `max_active_runs`, `max_active_tasks`, environment parallelism의 관계를 이해하고 있는가
- catchup과 backfill이 정규 운영 workload를 밀어내지 않는가
- priority 정책이 SLA 중요도와 맞는가

### Operational contract

- DAG run이 실패했을 때 재실행 범위가 명확한가
- mapped task 일부 실패 시 partial output을 어떻게 처리하는가
- Airflow metadata DB 크기와 scheduler lag를 보고 있는가
- DAG parse 시간이 늘어나지 않는가
- 로그, XCom, task instance 수가 운영자가 감당 가능한가
- 새 DAG를 추가할 때 어떤 pool과 dataset을 써야 하는지 문서화되어 있는가

---

## 한줄정리

Airflow를 안정적으로 확장하려면 DAG를 더 많이 작성하는 것보다, **데이터 이벤트는 Datasets로, 실행 단위는 Dynamic Task Mapping으로, 기다림은 Deferrable Operator로, 외부 리소스 한도는 Pools와 concurrency 설정으로 명시하는 운영 모델**을 먼저 설계해야 한다.
