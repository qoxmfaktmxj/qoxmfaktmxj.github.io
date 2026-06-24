---
layout: post
title: "Stream Processing 실전: Watermark, Late Data, Checkpoint, Idempotent Sink로 지연 데이터까지 안전하게 집계하는 법"
date: 2026-06-24 11:50:00 +0900
categories: [data-infra]
tags: [study, data-infra, stream-processing, flink, watermark, late-data, checkpoint, idempotency, event-time, exactly-once]
permalink: /data-infra/2026/06/24/study-stream-processing-watermark-late-data-checkpoint-idempotent-sink.html
---

## 배경: 스트림 처리는 "실시간 배치"가 아니라 시간과 실패를 다루는 운영 시스템이다

데이터 파이프라인을 처음 만들 때는 보통 배치가 먼저다.

- 전날 주문을 모아 일별 매출을 만든다
- 로그를 object storage에 쌓고 Spark job으로 집계한다
- warehouse에 fact table과 mart table을 만든다
- BI와 정산, 추천, CRM, ML feature pipeline이 그 결과를 사용한다

이 구조는 이해하기 쉽다. 입력 범위가 명확하고, 실패하면 같은 날짜 파티션을 다시 만들면 된다. 하지만 제품과 조직이 커지면 배치만으로는 늦는 순간이 온다.

- 결제 완료 후 몇 초 안에 부정 거래 탐지를 해야 한다
- 배송 상태가 바뀌면 운영 대시보드가 즉시 반영되어야 한다
- 유저 행동 이벤트를 실시간 feature로 바꿔 추천에 써야 한다
- 광고 예산 소진율을 분 단위로 보고 입찰을 조정해야 한다
- 장애 탐지를 위해 로그와 metric을 계속 집계해야 한다
- 고객 세그먼트를 거의 실시간으로 갱신해 CRM으로 보내야 한다

그래서 Kafka, Flink, Kafka Streams, Spark Structured Streaming, Materialize, RisingWave 같은 도구를 붙인다. 처음에는 간단해 보인다.

```text
Kafka topic -> stream job -> aggregate -> sink table
```

하지만 운영에 들어가면 곧 아래 질문들이 터진다.

- 이벤트가 3분 늦게 도착하면 어느 집계 창에 넣어야 하는가
- 모바일 기기가 오프라인이었다가 1시간 뒤 보낸 이벤트는 버릴 것인가
- 처리 시간 기준 12:00에 들어온 이벤트와 실제 발생 시간 11:55인 이벤트 중 무엇이 중요한가
- job이 실패했다가 재시작하면 이미 sink에 쓴 결과를 다시 쓰는가
- checkpoint는 성공했지만 외부 DB write는 애매하게 성공한 경우 어떻게 복구하는가
- window 결과를 한 번만 내보내야 하는가, 늦은 이벤트가 오면 수정본을 다시 내보내야 하는가
- Kafka offset commit, Flink checkpoint, sink transaction은 어떤 순서로 맞물리는가
- 백필을 스트림 job에 흘려보내면 실시간 트래픽과 어떻게 구분할 것인가

이 문제들은 단순히 "Flink 설정값을 잘 잡자"로 끝나지 않는다. 스트림 처리는 시간 의미, 상태 저장, 실패 복구, 외부 시스템 쓰기, 재처리 정책을 하나의 계약으로 묶어야 한다.

오늘 글은 스트림 처리 입문 문법이 아니다. 중급 이상 개발자와 데이터 엔지니어가 실무 설계에서 답해야 하는 질문을 기준으로 정리한다.

1. Processing time과 event time은 왜 다르고, 언제 무엇을 기준으로 삼아야 하는가
2. Watermark는 늦은 데이터를 "없애는 기능"이 아니라 어떤 운영 선언인가
3. Window, state, checkpoint는 어떻게 연결되고 어디서 비용이 커지는가
4. Exactly-once라는 표현은 왜 sink까지 포함하지 않으면 위험한가
5. Late data를 drop, side output, update, retraction 중 어떤 방식으로 처리할 것인가
6. 실시간 집계와 백필을 같은 파이프라인에서 다룰 때 어떤 경계가 필요한가
7. 운영에서 자주 터지는 실수와 배포 전 체크리스트는 무엇인가

결론부터 말하면 이렇다.

**스트림 처리의 핵심은 "빨리 계산하기"가 아니라, 이벤트가 발생한 시간과 처리되는 시간의 차이를 명시하고, 실패 후에도 같은 의미의 결과로 수렴하게 만드는 것이다.**

이 관점이 중요하다. 낮은 latency만 좇으면 늦은 이벤트와 장애 복구에서 결과가 흔들린다. 반대로 정확성만 좇으면 watermark가 끝없이 늦어지고 state가 커져 실시간성이 사라진다. 운영 가능한 스트림 시스템은 이 둘 사이의 비용을 명시적으로 선택한다.

---

## 먼저 큰 그림: 스트림 파이프라인은 네 개의 계약으로 나뉜다

스트림 처리 시스템을 도구 이름으로만 보면 복잡하다. 하지만 운영 관점에서는 네 개의 계약으로 쪼개면 선명해진다.

```text
Source contract
  -> 어떤 이벤트를 어떤 순서와 중복 가능성으로 읽는가

Time contract
  -> 이벤트 시간을 어떻게 해석하고 늦은 데이터를 어디까지 기다리는가

State contract
  -> 중간 집계와 join 상태를 어디에 저장하고 어떻게 복구하는가

Sink contract
  -> 결과를 외부 시스템에 어떤 멱등성/트랜잭션 기준으로 쓰는가
```

예를 들어 Kafka에서 주문 이벤트를 읽어 1분 단위 매출을 집계하고 PostgreSQL에 쓰는 파이프라인이 있다고 하자.

```text
orders topic
  -> parse OrderPaid
  -> event time 기준 1분 tumbling window
  -> store_id별 amount sum
  -> revenue_minute table upsert
```

이 파이프라인은 겉보기에는 단순하다. 하지만 운영 계약은 꽤 많다.

- Kafka record key는 무엇인가
- 같은 이벤트가 두 번 들어오면 어떻게 deduplicate 하는가
- `paid_at`이 event time인가, Kafka append time이 event time인가
- watermark는 최대 몇 분 지연을 허용하는가
- window 결과는 언제 확정되는가
- 늦게 온 이벤트는 기존 window를 수정하는가, 버리는가
- checkpoint interval은 얼마이고 state backend는 무엇인가
- PostgreSQL write는 insert-only인가, upsert인가, transaction commit인가
- 재시작 후 같은 window 결과를 다시 쓰면 최종 결과가 바뀌는가

이 질문에 답하지 않은 상태로 "Flink job 하나 만들었다"라고 말하면 위험하다. 코드는 돌아갈 수 있지만, 장애와 지연 이벤트가 들어오는 순간 결과의 의미가 바뀐다.

### 배치와 스트림의 차이는 데이터 크기가 아니라 완료 조건이다

배치는 입력 범위가 닫혀 있다.

```text
2026-06-23 00:00:00 <= paid_at < 2026-06-24 00:00:00
```

입력 범위가 닫혀 있으니 "이 날짜의 집계가 끝났다"는 판단이 쉽다. 물론 지연 데이터가 있으면 배치도 어렵지만, 적어도 job 실행 시점과 대상 파티션은 분리되어 있다.

스트림은 입력이 계속 열린다.

```text
계속 들어오는 orders topic
```

따라서 스트림에서는 완료 조건을 시스템이 직접 만들어야 한다. 이때 등장하는 개념이 watermark다. Watermark는 "이 시간 이전의 이벤트는 이제 대부분 도착했다고 봐도 된다"는 신호다.

이 말에는 일부러 "대부분"이라는 단어가 들어간다. 분산 시스템에서 모든 이벤트가 완벽히 제시간에 도착한다고 보장하기 어렵기 때문이다. 모바일 네트워크, producer 재시도, Kafka broker 장애, connector 지연, clock skew, 백필, 재처리 등으로 이벤트는 얼마든지 늦게 도착한다.

Watermark는 늦은 데이터를 없애는 마법이 아니다. **정확성과 latency 사이의 운영 선택을 코드와 설정으로 선언하는 장치**다.

---

## 핵심 개념 1: Processing Time과 Event Time을 섞으면 지표가 조용히 틀어진다

스트림 처리에서 가장 먼저 정해야 할 것은 시간 기준이다.

### Processing Time

Processing time은 이벤트가 stream processor에 도착해 처리되는 시간이다.

```text
event occurred at 11:58:30
producer sent at 11:59:10
Kafka appended at 11:59:11
Flink processed at 12:00:03
```

Processing time 기준이면 이 이벤트는 12:00 근처 데이터다. 구현은 쉽다. 시스템 clock만 보면 되고 watermark 설계도 거의 필요 없다.

장점:

- latency가 낮다
- 구현과 운영이 단순하다
- 늦은 데이터 처리 정책이 단순해진다
- 모니터링성 집계처럼 "지금 들어오는 것"이 중요한 경우 적합하다

단점:

- 장애나 지연이 지표 의미를 바꾼다
- 재처리하면 결과가 달라질 수 있다
- 모바일/IoT/외부 연동 이벤트처럼 발생 시간과 도착 시간이 벌어지는 도메인에 취약하다
- 과거 이벤트 백필을 흘리면 현재 지표가 오염된다

Processing time은 "시스템이 본 시간"이다. 운영 metric, ingestion rate, queue lag, alerting처럼 처리 순간 자체가 의미 있는 데이터에는 잘 맞는다.

### Event Time

Event time은 비즈니스 이벤트가 실제로 발생한 시간이다.

```json
{
  "event_id": "evt-100",
  "order_id": "ord-100",
  "amount": 49000,
  "paid_at": "2026-06-24T11:58:30+09:00"
}
```

Event time 기준이면 이 이벤트는 11:58 window에 들어간다. 12:00:03에 처리되더라도 비즈니스 의미는 11:58의 결제다.

장점:

- 비즈니스 지표 의미가 안정적이다
- 재처리해도 같은 시간 창으로 수렴할 수 있다
- 백필과 실시간 처리를 같은 시간 의미로 다룰 수 있다
- 지연 도착 이벤트를 올바른 과거 window에 반영할 수 있다

단점:

- watermark와 late data 정책이 필요하다
- producer clock과 event timestamp 품질에 의존한다
- state 보관 시간이 길어질 수 있다
- 결과 확정 시점이 늦어진다

실무에서 매출, 주문, 행동 분석, 정산, feature 생성처럼 비즈니스 발생 시간이 중요한 데이터는 대부분 event time을 기준으로 삼아야 한다. 반대로 시스템 관측 지표나 ingestion 상태는 processing time이 더 자연스럽다.

### 가장 위험한 패턴: 입력은 event time인데 window는 processing time

아래 코드는 빠르게 만들 수 있다.

```java
stream
    .keyBy(event -> event.storeId)
    .window(TumblingProcessingTimeWindows.of(Time.minutes(1)))
    .sum("amount");
```

하지만 주문 이벤트라면 이 코드는 위험하다. Kafka 장애로 5분 밀린 이벤트가 한꺼번에 들어오면, 실제 결제 시간과 상관없이 현재 1분 window 매출이 폭증한다. 대시보드는 "지금 매출이 급증했다"고 보지만 실제로는 지연된 과거 이벤트가 한 번에 처리된 것이다.

반대로 event time window를 쓰면 늦게 도착한 이벤트도 원래 결제 시각의 window에 들어간다.

```java
stream
    .assignTimestampsAndWatermarks(
        WatermarkStrategy
            .<OrderPaid>forBoundedOutOfOrderness(Duration.ofMinutes(3))
            .withTimestampAssigner((event, timestamp) -> event.paidAt.toEpochMilli())
    )
    .keyBy(event -> event.storeId)
    .window(TumblingEventTimeWindows.of(Time.minutes(1)))
    .sum("amount");
```

이 코드는 지표 의미를 비즈니스 시간에 맞춘다. 대신 결과는 최대 3분 정도 늦게 확정될 수 있고, 3분보다 더 늦은 이벤트를 어떻게 처리할지 결정해야 한다.

---

## 핵심 개념 2: Watermark는 "어디까지 기다릴 것인가"에 대한 선언이다

Watermark를 한 문장으로 정리하면 이렇다.

> Watermark T는 "이제 event time이 T 이하인 이벤트는 대부분 도착했다고 보고 window를 닫아도 된다"는 신호다.

예를 들어 watermark가 `12:00:00`까지 진행되었다면, 시스템은 12:00 이전 window들을 닫을 수 있다. 하지만 이후에 `11:59:30` 이벤트가 절대 오지 않는다는 뜻은 아니다. 그런 이벤트가 오면 late data다.

### Bounded out-of-orderness

가장 흔한 watermark 전략은 bounded out-of-orderness다.

```text
watermark = 지금까지 관측한 최대 event time - 허용 지연
```

예를 들어 허용 지연을 3분으로 잡고, 지금까지 가장 큰 event time이 12:05라면 watermark는 12:02다.

```text
max observed event time = 12:05:00
allowed lateness        = 00:03:00
watermark               = 12:02:00
```

이 설정은 "대부분의 이벤트는 발생 후 3분 안에 도착한다"는 가정을 코드로 표현한다. 중요한 것은 이 값이 순수 기술값이 아니라 도메인과 운영 데이터에서 나와야 한다는 점이다.

허용 지연을 너무 짧게 잡으면:

- late data가 많이 발생한다
- 집계 결과가 자주 누락되거나 보정된다
- downstream이 불완전한 값을 보게 된다

허용 지연을 너무 길게 잡으면:

- 결과 확정 latency가 길어진다
- window state를 오래 들고 있어야 한다
- checkpoint 크기와 복구 시간이 커진다
- dashboard와 alerting이 느려진다

즉 watermark는 정확성과 latency의 교환비다.

### Watermark는 파티션 단위 지연에 민감하다

Kafka source를 읽는 경우 watermark는 partition별 진행 상황의 영향을 받는다. 어떤 partition 하나가 오래 idle 상태이거나 매우 오래된 event time만 내보내면 전체 watermark가 멈출 수 있다.

예를 들어 partition 0은 12:10 이벤트까지 왔고 partition 1은 11:50에서 멈췄다면, 전체 operator watermark는 느린 쪽에 끌려갈 수 있다. 그러면 window가 닫히지 않고 state가 계속 쌓인다.

이를 막기 위해 Flink에서는 idle source partition 감지가 중요하다.

```java
WatermarkStrategy
    .<OrderPaid>forBoundedOutOfOrderness(Duration.ofMinutes(3))
    .withIdleness(Duration.ofMinutes(1));
```

`withIdleness`는 한동안 이벤트가 없는 partition을 watermark 계산에서 제외할 수 있게 해준다. 단, 이 값도 조심해야 한다. 실제로 느린 partition인데 idle로 판단하면 늦은 이벤트가 늘어날 수 있다.

### Watermark 지표는 반드시 모니터링해야 한다

스트림 job의 lag만 보면 부족하다. Kafka consumer lag가 낮아도 watermark가 멈춰 있으면 event-time window 결과는 나오지 않을 수 있다.

운영에서 봐야 할 지표는 최소한 다음과 같다.

- source별 current watermark
- operator별 watermark 차이
- event time과 processing time의 skew
- late record count
- dropped late record count
- window state size
- checkpoint duration과 alignment time
- sink commit latency

특히 "Kafka lag는 0인데 대시보드가 갱신되지 않는다"는 장애는 watermark가 멈췄거나 window가 닫히지 않은 경우가 많다.

---

## 핵심 개념 3: Late Data 정책은 버리기 전에 비즈니스 의미부터 정해야 한다

Watermark 이후에 도착한 이벤트는 late data다. 하지만 late data라고 해서 무조건 버려도 되는 것은 아니다. 어떤 도메인에서는 늦은 이벤트가 매우 중요하다.

- 결제 이벤트가 늦게 왔다면 매출과 정산에 반영되어야 한다
- 사기 탐지 이벤트가 늦게 왔다면 사후 조치라도 필요하다
- 클릭 로그가 늦게 왔다면 실시간 추천에는 늦었지만 분석에는 필요할 수 있다
- 배송 이벤트가 늦게 왔다면 고객 알림은 늦었어도 상태 이력은 맞아야 한다

Late data 처리 방식은 보통 네 가지로 나뉜다.

### 1) Drop

허용 지연을 넘은 이벤트를 버린다.

장점:

- 구현이 단순하다
- downstream 결과가 한 번 확정되면 바뀌지 않는다
- state 보관 비용을 통제하기 쉽다

단점:

- 데이터 손실이 생긴다
- 비즈니스 지표가 과소 집계될 수 있다
- 버린 데이터에 대한 감사와 재처리 경로가 없으면 나중에 설명이 어렵다

Drop은 시스템 metric이나 임시 대시보드에는 가능하다. 하지만 정산, 과금, 핵심 KPI에는 매우 신중해야 한다. 버리더라도 side output이나 dead-letter topic에 남겨야 한다.

### 2) Side Output

너무 늦은 이벤트를 별도 stream이나 topic으로 보낸다.

```text
main output: 정상 window 집계
side output: watermark 이후 도착한 late events
```

장점:

- 실시간 파이프라인 latency를 유지할 수 있다
- 늦은 이벤트를 분석하거나 별도 보정 배치로 처리할 수 있다
- drop보다 감사 가능성이 높다

단점:

- 보정 파이프라인이 추가된다
- downstream 소비자가 main 결과와 correction 결과를 함께 이해해야 한다
- late data가 많아지면 운영 복잡도가 커진다

실무에서는 main stream은 빠르게 유지하고, late event는 correction topic으로 보내 배치 보정이나 별도 upsert로 처리하는 방식이 자주 쓰인다.

### 3) Update

늦은 이벤트가 오면 이미 낸 window 결과를 다시 계산해 수정본을 내보낸다.

예를 들어 11:59 window의 매출을 100만 원으로 냈는데, 늦은 주문이 도착해 105만 원으로 업데이트한다.

```text
window 11:59 store A revenue = 1,000,000
late event +50,000
window 11:59 store A revenue = 1,050,000
```

장점:

- 최종 결과 정확도를 높일 수 있다
- upsert sink와 잘 맞는다
- dashboard가 "잠정값 -> 확정값" 모델을 표현할 수 있다

단점:

- downstream이 update를 처리할 수 있어야 한다
- append-only sink에는 부적합하다
- 동일 window 결과가 여러 번 바뀔 수 있다

Update 모델을 쓸 때는 결과 테이블에 상태를 명시하는 것이 좋다.

```sql
CREATE TABLE revenue_minute (
    window_start timestamptz NOT NULL,
    window_end timestamptz NOT NULL,
    store_id text NOT NULL,
    revenue numeric NOT NULL,
    version bigint NOT NULL,
    is_final boolean NOT NULL,
    updated_at timestamptz NOT NULL,
    PRIMARY KEY (window_start, store_id)
);
```

`is_final`이 없으면 소비자는 이 값이 잠정 집계인지 확정 집계인지 알 수 없다.

### 4) Retraction

이전 결과를 취소하고 새 결과를 내보낸다. SQL 기반 streaming이나 changelog stream에서 중요하다.

```text
- window 11:59 store A revenue = 1,000,000
+ window 11:59 store A revenue = 1,050,000
```

장점:

- downstream이 changelog를 정확히 반영할 수 있다
- join, aggregation, materialized view와 잘 맞는다

단점:

- 소비자가 retraction semantics를 이해해야 한다
- 단순 append consumer는 처리하기 어렵다
- sink connector와 저장소 선택이 제한된다

Retraction은 강력하지만 운영 난이도가 높다. 모든 소비자가 "이전 값을 빼고 새 값을 더한다"는 의미를 정확히 구현해야 하기 때문이다.

---

## 핵심 개념 4: Checkpoint는 Kafka offset 저장이 아니라 상태와 입력 위치의 일관된 스냅샷이다

스트림 job은 상태를 가진다.

- window별 중간 합계
- deduplication을 위한 event id set
- join을 위한 반대편 stream buffer
- CEP pattern state
- aggregate accumulator
- sink transaction handle

job이 실패하면 이 상태를 복구해야 한다. 단순히 Kafka offset만 다시 잡으면 안 된다. offset은 입력 위치일 뿐이고, 그 위치까지 처리하며 만든 중간 상태가 함께 맞아야 한다.

Checkpoint는 이 둘을 일관되게 묶는다.

```text
checkpoint N
  - Kafka partition offsets
  - operator state
  - keyed state
  - pending sink transaction metadata
```

Flink 기준으로 checkpoint가 성공하면, job은 장애 후 checkpoint N 시점의 상태와 source offset에서 재개할 수 있다. 이때 checkpoint 이후 처리했던 일부 이벤트는 다시 읽힐 수 있다. 따라서 sink가 멱등적이거나 transaction-aware여야 최종 결과가 흔들리지 않는다.

### Checkpoint interval의 트레이드오프

Checkpoint interval을 짧게 잡으면:

- 장애 시 재처리 범위가 줄어든다
- recovery point objective가 좋아진다
- 하지만 checkpoint overhead가 늘어난다
- state backend와 storage 부하가 커진다

Checkpoint interval을 길게 잡으면:

- 평시 overhead가 줄어든다
- 하지만 장애 시 더 많은 이벤트를 재처리한다
- sink 중복 write 가능 구간이 커진다
- 복구 후 watermark 진행이 늦어질 수 있다

따라서 interval은 "무조건 10초"나 "무조건 5분"으로 정하면 안 된다. state 크기, 입력 처리량, sink transaction timeout, 장애 복구 목표를 같이 봐야 한다.

### State TTL은 정확도 정책이다

Deduplication을 위해 event id를 state에 저장한다고 하자.

```text
event_id -> seen
```

이 state를 영원히 들고 있을 수는 없다. TTL이 필요하다. 하지만 TTL은 메모리 최적화가 아니라 중복 제거 보장 기간을 뜻한다.

```text
deduplication TTL = 24 hours
```

이 말은 "24시간 안에 재도착한 중복 이벤트는 제거하지만, 그 이후의 중복은 다시 처리될 수 있다"는 뜻이다. 이것이 비즈니스적으로 허용되는지 확인해야 한다.

Window state도 마찬가지다. Allowed lateness를 10분으로 잡으면 window state를 최소한 watermark 이후 10분은 유지해야 한다. 더 오래 보정하려면 더 오래 유지하거나 별도 correction pipeline이 필요하다.

---

## 핵심 개념 5: Exactly-once는 source부터 sink까지 이어져야 의미가 있다

스트림 처리에서 가장 위험한 표현 중 하나가 exactly-once다. 도구 문서에서 exactly-once를 지원한다고 해서 비즈니스 결과가 반드시 한 번만 반영되는 것은 아니다.

더 정확히는 범위를 나눠야 한다.

```text
Source read exactly-once
  Kafka offset과 checkpoint가 일관되게 저장되는가

State update exactly-once
  같은 이벤트가 복구 후 state에 중복 반영되지 않는가

Sink write exactly-once
  외부 시스템에 결과가 중복 또는 유실 없이 반영되는가

Business effect exactly-once
  downstream 업무 동작이 중복 실행되지 않는가
```

Flink 내부 state는 checkpoint로 exactly-once에 가깝게 복구할 수 있다. 하지만 JDBC sink에 `INSERT`를 날리는 순간 이야기가 달라진다.

### 위험한 sink 패턴: append-only insert

다음 sink는 장애 복구에 취약하다.

```sql
INSERT INTO revenue_minute_events (
    window_start,
    store_id,
    revenue,
    emitted_at
) VALUES (?, ?, ?, now());
```

job이 sink에 insert한 뒤 checkpoint 완료 전에 죽으면, 재시작 후 같은 이벤트를 다시 처리해 같은 window 결과를 또 insert할 수 있다. 결과 테이블이 append-only라면 downstream은 중복을 직접 제거해야 한다.

### 더 안전한 패턴: deterministic key upsert

집계 결과는 보통 deterministic key를 갖는다.

```text
window_start + window_end + store_id
```

이 key로 upsert하면 같은 결과를 다시 써도 최종 상태가 흔들리지 않는다.

```sql
INSERT INTO revenue_minute (
    window_start,
    window_end,
    store_id,
    revenue,
    version,
    is_final,
    updated_at
) VALUES (?, ?, ?, ?, ?, ?, now())
ON CONFLICT (window_start, store_id)
DO UPDATE SET
    revenue = EXCLUDED.revenue,
    version = GREATEST(revenue_minute.version, EXCLUDED.version),
    is_final = EXCLUDED.is_final,
    updated_at = now();
```

단, 이 예시도 완벽하지 않다. `version`이 단조 증가하지 않거나, 오래된 update가 늦게 도착해 최신 값을 덮으면 문제가 된다. 그래서 sink에는 결과 version이나 checkpoint id, window finality를 함께 설계해야 한다.

### Two-phase commit sink

Kafka sink, Iceberg sink, 일부 database sink는 checkpoint와 연동된 two-phase commit을 제공한다.

흐름은 대략 이렇다.

```text
1. checkpoint N 이전 데이터를 pending transaction에 write
2. checkpoint N snapshot에 transaction handle 저장
3. checkpoint N이 완료되면 transaction commit
4. 실패하면 pending transaction abort 또는 복구 후 commit
```

이 방식은 강력하지만 비용이 있다.

- sink가 transaction을 지원해야 한다
- transaction timeout과 checkpoint interval이 맞아야 한다
- pending transaction이 쌓이면 운영 부담이 생긴다
- 외부 시스템 장애가 checkpoint 완료를 지연시킬 수 있다

따라서 "exactly-once sink"가 항상 답은 아니다. 많은 집계성 파이프라인에서는 deterministic key upsert와 멱등 설계가 더 단순하고 견고하다.

---

## 실무 예시: 주문 매출 1분 집계 파이프라인 설계

이제 구체적인 예시를 보자.

요구사항:

- `order-paid` Kafka topic을 읽는다
- KST 기준 결제 발생 시각으로 1분 매출을 집계한다
- 매장별 매출을 PostgreSQL `revenue_minute` 테이블에 쓴다
- 대부분의 이벤트는 2분 안에 도착하지만, 모바일 결제 재시도 때문에 10분 늦는 경우도 있다
- 대시보드는 1분 단위로 빠르게 보고 싶고, 정산용 mart는 정확해야 한다

이 요구사항은 하나의 결과로 풀기 어렵다. 실시간성과 정확성 요구가 다르기 때문이다. 좋은 설계는 결과를 두 층으로 나누는 것이다.

```text
Realtime layer
  - allowed out-of-orderness: 2 minutes
  - allowed lateness: 3 minutes
  - dashboard용 provisional aggregate

Correction layer
  - late event side output
  - 24시간 이내 지연 이벤트를 보정
  - 정산/분석 mart에 최종 반영
```

### 이벤트 스키마

최소한 아래 필드가 필요하다.

```json
{
  "event_id": "evt-20260624-0001",
  "event_type": "OrderPaid",
  "event_version": 1,
  "order_id": "ord-100",
  "store_id": "store-7",
  "amount": 49000,
  "currency": "KRW",
  "paid_at": "2026-06-24T11:48:31+09:00",
  "produced_at": "2026-06-24T11:48:33+09:00"
}
```

여기서 `paid_at`은 event time이다. `produced_at`은 지연 관측에 쓴다. `event_id`는 deduplication에 쓴다. `event_version`은 schema evolution과 consumer compatibility에 필요하다.

### Window key

집계 key는 명확해야 한다.

```text
window_start_kst + store_id + currency
```

통화가 하나뿐이라도 key에 넣을지 결정해야 한다. 나중에 다중 통화가 생길 수 있으면 처음부터 계약에 명시하는 편이 낫다. 반대로 KRW만 영구적으로 보장한다면 currency를 차원으로 쓰지 않아도 된다.

### 결과 테이블

대시보드용 테이블은 upsert 가능하게 설계한다.

```sql
CREATE TABLE revenue_minute (
    window_start timestamptz NOT NULL,
    window_end timestamptz NOT NULL,
    store_id text NOT NULL,
    currency text NOT NULL,
    order_count bigint NOT NULL,
    revenue_amount numeric(18, 2) NOT NULL,
    source_event_count bigint NOT NULL,
    version bigint NOT NULL,
    is_final boolean NOT NULL,
    watermark_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    PRIMARY KEY (window_start, store_id, currency)
);
```

중요한 컬럼은 `is_final`, `watermark_at`, `version`이다.

- `is_final=false`: 아직 late update 가능성이 있는 잠정값
- `is_final=true`: 이 파이프라인의 허용 지연 기준으로 확정된 값
- `watermark_at`: 어떤 watermark 기준으로 만들어진 결과인지
- `version`: 오래된 write가 최신 write를 덮지 않게 하는 단조 증가 값

대시보드는 `is_final=false`인 값을 보여줄 수 있다. 다만 UI나 API에서 "잠정" 상태를 표현해야 한다. 정산용 데이터는 `is_final=true` 또는 correction layer 반영 후 결과만 사용해야 한다.

### Late event side output

2분 watermark와 3분 allowed lateness를 넘은 이벤트는 바로 버리지 않는다.

```text
late-order-paid topic
  key: order_id
  value:
    - original event
    - observed_at
    - current_watermark
    - lateness_ms
    - reason
```

이 topic은 세 가지 용도로 쓴다.

- late data 비율 모니터링
- 별도 보정 job 입력
- producer 또는 네트워크 지연 원인 분석

특히 late event 비율이 갑자기 올라가면 stream job 문제가 아니라 upstream producer, mobile SDK, Kafka Connect, network 장애일 수 있다.

### Deduplication

Producer 재시도나 CDC 재처리 때문에 같은 `event_id`가 다시 들어올 수 있다. Stream job에서 deduplication을 한다면 TTL을 명시해야 한다.

```text
dedup key: event_id
ttl: 24 hours
```

이 계약은 "24시간 이내 중복은 제거한다"는 뜻이다. 정산에서 7일 후 재처리 중복까지 막아야 한다면 stream state TTL만으로는 부족하다. sink table의 unique key나 별도 processed event table, batch reconciliation이 필요하다.

---

## 트레이드오프: 정확성, 지연, 비용은 동시에 최적화되지 않는다

스트림 처리 설계에서 가장 흔한 실패는 세 가지를 모두 원하면서 아무것도 명시하지 않는 것이다.

```text
낮은 latency
높은 correctness
낮은 state/storage cost
```

현실에서는 셋 중 하나 이상을 비용으로 낸다.

### Watermark를 짧게 잡는 선택

좋은 점:

- 결과가 빨리 나온다
- window state가 빨리 정리된다
- dashboard latency가 낮다

나쁜 점:

- late data가 늘어난다
- 보정 로직이 필요해진다
- 최종 정확도를 별도 경로로 맞춰야 한다

적합한 곳:

- 실시간 운영 대시보드
- 알림성 지표
- 빠른 탐지가 중요한 시스템

### Watermark를 길게 잡는 선택

좋은 점:

- 늦은 이벤트를 main path에서 더 많이 흡수한다
- 결과 보정 빈도가 줄어든다
- 최종 집계 정확도가 높아진다

나쁜 점:

- 결과 확정이 늦어진다
- state 크기와 checkpoint 비용이 커진다
- 장애 복구 시간이 길어질 수 있다

적합한 곳:

- 정산 전 집계
- 정확성이 latency보다 중요한 mart
- 지연 이벤트가 도메인 특성상 흔한 데이터

### Upsert sink를 쓰는 선택

좋은 점:

- 재처리와 late update에 강하다
- dashboard가 최신 값을 쉽게 조회한다
- 장애 후 중복 write의 영향을 줄인다

나쁜 점:

- append-only log보다 감사 추적이 약할 수 있다
- write amplification과 lock 경합이 생길 수 있다
- 오래된 update가 최신 값을 덮지 않도록 version 관리가 필요하다

적합한 곳:

- materialized aggregate
- 최신 상태 테이블
- API 조회용 serving table

### Append-only sink를 쓰는 선택

좋은 점:

- 감사와 재현성이 좋다
- downstream이 changelog를 직접 처리할 수 있다
- lakehouse/object storage와 잘 맞는다

나쁜 점:

- 소비자가 dedup/retraction/update semantics를 알아야 한다
- 단순 조회에는 별도 compaction이나 materialization이 필요하다
- 중복 write가 쌓일 수 있다

적합한 곳:

- raw event archive
- changelog stream
- 재처리 가능한 분석 원천

---

## 흔한 실수 1: Kafka lag만 보고 스트림이 정상이라고 판단한다

Kafka consumer lag가 0이면 입력을 다 읽었다는 뜻에 가깝다. 하지만 event-time processing에서는 그것만으로 충분하지 않다.

아래 상황을 보자.

```text
Kafka lag: 0
current watermark: 10:30
processing time: 11:50
window output: 멈춤
```

lag는 없지만 watermark가 80분 뒤처져 있다. 이 경우 window가 닫히지 않아 결과가 안 나올 수 있다. 원인은 다양하다.

- 특정 partition의 event time이 오래된 값에서 멈췄다
- idle partition 처리가 없다
- producer clock이 잘못되어 과거 timestamp가 계속 들어온다
- 백필 이벤트가 실시간 topic에 섞였다
- timestamp assigner가 잘못된 필드를 보고 있다

운영 대시보드에는 lag와 watermark를 함께 보여야 한다. "읽었는가"와 "event time이 진행되는가"는 다른 질문이다.

---

## 흔한 실수 2: Producer timestamp를 검증하지 않는다

Event time은 producer가 넣어주는 경우가 많다. 그런데 producer clock이 틀리거나 timezone 처리가 잘못되면 downstream 전체가 흔들린다.

대표적인 문제:

- `paid_at`을 local time 문자열로 보내 timezone이 사라진다
- 모바일 기기 clock이 몇 시간 틀어져 있다
- 서버가 UTC를 보내는데 consumer가 KST로 파싱한다
- event 발생 시간이 아니라 발행 시간이 들어간다
- 재처리 batch가 현재 시간을 event time으로 넣는다

따라서 source contract에는 timestamp 품질 규칙이 있어야 한다.

```text
event_time must be:
  - ISO-8601 with timezone
  - not more than 24h in the future
  - not older than 30d for realtime topic
  - produced_at >= event_time in normal online flow
```

규칙을 어기는 이벤트는 main stream에 넣기 전에 quarantine topic으로 보내는 편이 낫다. 잘못된 timestamp 하나가 watermark를 오염시키면 전체 job이 느려질 수 있다.

---

## 흔한 실수 3: Backfill을 실시간 topic에 그대로 섞는다

과거 30일 주문 이벤트를 다시 흘려보내야 할 때가 있다. 이때 실시간 topic에 그대로 publish하면 event-time job이 크게 흔들릴 수 있다.

- watermark가 과거 이벤트 때문에 이상하게 움직인다
- late data가 폭증한다
- dashboard가 과거 보정 이벤트를 실시간 장애로 오해한다
- dedup state TTL을 넘은 중복이 다시 반영된다
- sink upsert가 오래된 결과로 최신 값을 덮을 수 있다

백필은 별도 계약이 필요하다.

가능한 패턴:

- realtime topic과 backfill topic을 분리한다
- backfill job은 별도 consumer group과 별도 sink staging table을 쓴다
- 결과를 merge할 때 version과 cutover time을 둔다
- dashboard용 realtime table과 정산용 corrected table을 분리한다
- backfill event에는 `replay_id`, `replayed_at`, `original_event_time`을 넣는다

백필은 운영 행위다. 이벤트만 다시 보내면 끝나는 것이 아니라, downstream이 그것을 "현재 발생한 일"로 오해하지 않게 해야 한다.

---

## 흔한 실수 4: Checkpoint 성공을 sink 성공과 같은 뜻으로 본다

Checkpoint가 성공했다는 것은 stream processor 내부 상태와 source offset이 저장되었다는 뜻이다. Sink까지 정확히 한 번 반영되었다는 뜻은 sink 구현에 따라 다르다.

JDBC sink가 단순 batch insert라면 다음 상황이 가능하다.

```text
1. window result를 DB에 write
2. DB commit 성공
3. checkpoint 완료 전 job 실패
4. 재시작 후 같은 window result 다시 write
```

이때 sink가 upsert이면 최종 상태가 같을 수 있다. append-only insert이면 중복 row가 생긴다. 외부 API 호출이면 고객에게 알림이 두 번 갈 수도 있다.

따라서 sink별로 아래를 명시해야 한다.

- 같은 record를 다시 write해도 결과가 같은가
- primary key나 idempotency key가 있는가
- transaction이 checkpoint와 연동되는가
- 오래된 write를 막는 version 조건이 있는가
- 실패 후 사람이 재처리할 수 있는 감사 로그가 있는가

스트림 job의 exactly-once 설정만 보고 외부 효과까지 exactly-once라고 말하면 안 된다.

---

## 흔한 실수 5: State 크기 증가를 데이터 증가로만 본다

State가 커지는 이유는 입력량 증가만이 아니다.

- watermark가 멈춰 window state가 닫히지 않는다
- allowed lateness가 너무 길다
- dedup TTL이 과도하게 길다
- key cardinality가 예상보다 높다
- hot key 때문에 특정 task에 state가 몰린다
- join 상대 stream이 늦어져 buffer가 쌓인다
- source partition idleness가 감지되지 않는다

State가 커지면 checkpoint도 느려진다. Checkpoint가 느려지면 복구 지점이 멀어지고, 재시작 후 재처리량이 늘어난다. 재처리량이 늘면 sink 중복 가능 구간도 커진다.

따라서 state는 단순 저장소 비용이 아니라 장애 복구 시간과 정확성 비용이다.

운영에서는 key cardinality, state size by operator, checkpoint bytes, checkpoint duration, full restart time을 함께 봐야 한다.

---

## 배포 전 체크리스트

스트림 파이프라인을 운영에 올리기 전에는 아래 질문에 답해야 한다.

### Source

- Kafka topic의 key는 비즈니스 순서 요구와 맞는가
- 이벤트에 stable `event_id`가 있는가
- producer retry로 중복이 생길 수 있는가
- schema version과 compatibility 정책이 있는가
- 백필 이벤트와 실시간 이벤트를 구분할 수 있는가

### Time

- event time 필드는 무엇인가
- timezone이 명시되어 있는가
- producer clock skew를 탐지하는가
- watermark 전략과 허용 지연은 실제 지연 분포를 보고 정했는가
- idle partition 처리가 필요한가
- late data를 drop, side output, update, retraction 중 무엇으로 처리하는가

### State

- window state 보관 기간은 얼마인가
- deduplication TTL은 비즈니스 중복 허용 기간과 맞는가
- state backend와 checkpoint storage는 운영 부하를 감당하는가
- checkpoint interval과 timeout은 sink transaction timeout과 충돌하지 않는가
- hot key나 높은 cardinality에 대한 대응이 있는가

### Sink

- sink write는 append인가 upsert인가 changelog인가
- deterministic primary key가 있는가
- 같은 결과를 다시 써도 최종 상태가 같은가
- 오래된 update가 최신 값을 덮지 못하게 version 조건이 있는가
- `is_final`, `watermark_at`, `updated_at` 같은 결과 신뢰도 필드가 있는가
- 외부 API 호출처럼 되돌리기 어려운 side effect가 있는가

### Operations

- Kafka lag와 watermark lag를 함께 모니터링하는가
- late data rate alert이 있는가
- checkpoint failure와 duration alert이 있는가
- sink error와 retry가 DLQ 또는 감사 로그로 남는가
- 백필 runbook과 중단 방법이 있는가
- 재처리 후 결과 검증 쿼리가 있는가

---

## 실무 설계 원칙

마지막으로 운영에서 쓸 수 있는 원칙을 정리한다.

### 1. 대시보드와 정산을 같은 결과로 해결하려 하지 말라

대시보드는 빠른 잠정값이 중요하다. 정산은 늦더라도 정확한 최종값이 중요하다. 둘을 한 테이블과 한 SLA로 묶으면 둘 다 애매해진다.

대시보드용 realtime aggregate와 정산용 corrected aggregate를 분리하면 설계가 단순해진다.

### 2. Late data는 예외가 아니라 정상 입력으로 취급하라

분산 환경에서 늦은 이벤트는 항상 생긴다. late data 정책이 없다는 것은 사실상 무작위 정책을 쓰고 있다는 뜻이다. 버릴지, 보정할지, 수정본을 낼지, 별도 topic으로 보낼지 정해야 한다.

### 3. Sink를 먼저 생각하라

Stream processor 내부만 보면 정확해 보여도 sink가 append-only insert라면 장애 후 중복이 생긴다. 결과 저장소가 upsert를 지원하는지, transaction을 지원하는지, changelog를 이해하는지에 따라 전체 설계가 달라진다.

### 4. Backfill은 별도 모드로 설계하라

백필은 실시간 처리의 큰 예외다. 과거 event time을 대량으로 넣기 때문에 watermark, state, sink version을 흔든다. 별도 topic, 별도 job, staging table, merge step을 두는 편이 안전하다.

### 5. Watermark 지연을 SLO로 관리하라

스트림 job의 SLO는 처리량만으로 부족하다.

```text
P95 event-time lag < 3 minutes
late event ratio < 0.1%
checkpoint success rate > 99.9%
sink commit latency P95 < 10 seconds
```

이런 식으로 event-time 관점의 SLO를 잡아야 실제 사용자와 비즈니스가 체감하는 신선도를 관리할 수 있다.

---

## 한줄 정리

**운영 가능한 스트림 처리는 빠른 코드가 아니라, event time, watermark, late data, checkpoint, sink idempotency를 하나의 결과 계약으로 묶어 장애와 재처리 후에도 같은 의미로 수렴하게 만드는 설계다.**
