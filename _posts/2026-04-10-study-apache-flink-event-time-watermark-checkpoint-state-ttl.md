---
layout: post
title: "Apache Flink 실전: Event Time, Watermark, Checkpoint, State TTL로 지연 이벤트를 안정적으로 처리하는 기준"
date: 2026-04-10 11:40:00 +0900
categories: [data-infra]
tags: [study, data-infra, apache-flink, flink, event-time, watermark, checkpoint, state, state-ttl, stream-processing]
permalink: /data-infra/2026/04/10/study-apache-flink-event-time-watermark-checkpoint-state-ttl.html
---

## 배경: 스트리밍이 어려운 이유는 "실시간"보다 "늦게 오는 데이터"에 있다

배치 시스템에서는 보통 데이터가 다 모인 뒤 계산한다. 그래서 핵심 질문이 비교적 단순하다.

- 언제 배치를 돌릴 것인가
- 실패하면 어디서 재시작할 것인가
- 결과를 append할 것인가 replace할 것인가

그런데 스트리밍으로 오면 상황이 달라진다.

- 이벤트는 순서대로 오지 않는다
- 같은 사용자 이벤트가 서로 다른 파티션과 네트워크 경로를 타고 뒤늦게 도착한다
- 모바일 클라이언트는 오프라인 상태였다가 몇 분, 몇 시간 뒤에 한꺼번에 업로드한다
- CDC 이벤트는 소스 DB 커밋 순서와 소비 순서가 항상 직관적으로 맞지 않는다
- 장애가 나면 "어디까지 처리됐는가"와 "어디까지 저장됐는가"를 동시에 따져야 한다

이 시점부터 문제의 본질은 단순히 빠르게 계산하는 것이 아니다. **시간을 무엇으로 정의할 것인가, 늦게 도착한 데이터를 어디까지 받아줄 것인가, 장애가 나도 상태를 잃지 않고 다시 이어갈 수 있는가**가 핵심이 된다.

Apache Flink가 강한 이유는 여기 있다. Flink는 단순히 Kafka 메시지를 읽어 SQL 한 번 적용하는 도구가 아니라, **시간 개념과 상태(state)를 중심으로 스트리밍 파이프라인을 장기 운영할 수 있게 해주는 엔진**에 가깝다.

특히 중급 이상 개발자가 실무에서 반드시 부딪히는 질문은 아래다.

- Processing Time, Event Time, Ingestion Time은 언제 무엇을 기준으로 선택해야 하나?
- Watermark는 "늦게 온 데이터 허용 시간" 정도로만 이해하면 왜 자꾸 사고가 나나?
- Window 집계와 Keyed State는 어떻게 다르고, 언제 각각을 써야 하나?
- Checkpoint와 Savepoint는 둘 다 상태 저장 같은데 운영에서 왜 역할이 다르나?
- Exactly-once는 정말 끝까지 보장되는가, 아니면 특정 경계까지만 보장되는가?
- State TTL을 켜면 메모리 문제가 끝나는가, 아니면 정합성과 조회 결과가 달라질 수 있는가?

오늘 글은 Flink 입문 문법이 아니라, **지연 이벤트와 장애를 견디는 스트리밍 파이프라인을 Event Time, Watermark, Checkpoint, State TTL 관점에서 설계하는 기준**을 정리한다.

핵심은 여섯 가지다.

1. 스트리밍에서 시간은 벽시계가 아니라 **이벤트가 실제로 발생한 시점**으로 다뤄야 하는 경우가 많다
2. Watermark는 단순 지연 허용값이 아니라 **이 시점 이전 이벤트는 거의 다 왔다고 판단하는 시스템 계약**이다
3. Flink State는 기능이 아니라 **정합성과 비용을 동시에 책임지는 저장소**로 봐야 한다
4. Checkpoint는 장애 복구의 기준점이고 Savepoint는 운영 변경의 기준점이다
5. Exactly-once는 엔진 옵션 한 줄이 아니라 **소스, 상태, 싱크까지 포함한 end-to-end 설계 문제**다
6. State TTL은 메모리 절감 도구이면서 동시에 **데이터 의미를 바꾸는 정책**이므로 업무 규칙과 함께 설계해야 한다

---

## 먼저 큰 그림: Flink는 "메시지 소비기"보다 "시간과 상태를 다루는 실행 엔진"으로 이해하는 편이 맞다

Flink를 처음 볼 때는 Kafka consumer를 좀 더 고급스럽게 만든 느낌으로 이해하기 쉽다. 하지만 그렇게 보면 중요한 절반을 놓친다.

실무에서 Flink가 하는 일은 보통 아래 네 가지를 동시에 처리한다.

1. 외부 시스템에서 이벤트를 지속적으로 읽는다
2. 이벤트를 key 기준으로 분산하고 상태를 유지한다
3. 시간 기반 계산을 위해 watermark와 timer를 사용한다
4. 장애가 나도 상태와 입력 위치를 일관되게 복구한다

즉 Flink는 단순한 stateless 변환기가 아니다. 오히려 **상태를 오래 들고 있으면서, 그 상태를 특정 시간 의미 아래서 안전하게 업데이트하는 분산 시스템**에 가깝다.

이 관점이 중요한 이유는 아래와 같다.

### 1) 같은 집계라도 배치 사고방식과 스트리밍 사고방식이 다르다

예를 들어 "10분 단위 주문 수 집계"를 만든다고 하자.

배치에서는 보통 이렇게 생각한다.

- 10분이 끝난 뒤 쿼리 한 번 돌리면 된다
- 늦게 들어온 데이터는 다음 배치나 보정 배치에서 다시 처리한다

스트리밍에서는 다르게 본다.

- 지금 이 순간 10분 윈도우의 결과를 얼마나 신뢰할 수 있는가
- 3분 늦게 들어온 이벤트를 같은 윈도우에 포함할 것인가
- 이미 방출한 결과를 수정할 것인가 무시할 것인가
- 상태를 얼마나 오래 유지할 것인가

즉 계산식보다 **시간 경계와 결과 수정 정책**이 더 중요해진다.

### 2) Flink의 성능 문제는 CPU보다 상태와 시간 정책에서 많이 나온다

운영에서 자주 보는 증상은 이런 것들이다.

- job은 돌지만 결과가 늦게 나온다
- watermark가 정체돼 윈도우가 닫히지 않는다
- state가 계속 불어나 checkpoint 시간이 길어진다
- 재시작 후 같은 데이터가 다시 나가 sink 중복이 생긴다
- TTL을 켰더니 조인 결과가 예상보다 빠지기 시작한다

이건 대부분 단순 연산량 문제가 아니라, **event time 설계, watermark 생성 방식, state lifecycle, checkpoint 크기, sink idempotency** 문제다.

### 3) Flink는 결국 "언제 결과를 확정할 것인가"를 다루는 도구다

배치에서는 데이터가 모두 모인 뒤 계산하니 확정 시점이 비교적 자연스럽다. 스트리밍에서는 그렇지 않다. 그래서 모든 설계가 결국 이 질문으로 모인다.

> 이 결과를 언제까지 잠정치로 보고, 어느 시점부터 거의 확정치로 간주할 것인가?

Watermark, allowed lateness, side output, checkpoint, state TTL 모두 이 질문의 다른 표현이다.

---

## 핵심 개념 1: Processing Time, Event Time, Ingestion Time은 성능 옵션이 아니라 비즈니스 의미 선택이다

Flink를 배울 때 제일 먼저 나오는 개념 중 하나가 시간 모델이다. 보통 정의는 금방 외운다.

- Processing Time: 연산자가 이벤트를 처리한 시각
- Event Time: 이벤트가 실제로 발생한 시각
- Ingestion Time: 시스템에 들어온 시각

문제는 정의를 아는 것과 올바르게 선택하는 것이 완전히 다르다는 점이다.

### Processing Time이 잘 맞는 경우

Processing Time은 가장 단순하다.

- 이벤트 timestamp가 신뢰하기 어렵다
- 매우 낮은 지연이 중요하고 약간의 시간 왜곡을 감수할 수 있다
- 내부 운영 메트릭처럼 "들어온 순간 기준" 처리면 충분하다
- 정합성보다 반응 속도가 중요한 단기 알림성 처리다

예를 들어 "최근 1분간 API 에러 로그가 몇 건 들어왔는가" 같은 운영 알림은 processing time으로도 충분한 경우가 많다. 이벤트가 10초 늦게 들어왔다고 해서 본질이 크게 바뀌지 않기 때문이다.

### Event Time이 꼭 필요한 경우

반대로 아래는 event time이 사실상 필수다.

- 모바일 클릭/주문 이벤트처럼 네트워크 지연이 흔하다
- 광고, 결제, 사용자 행동 분석처럼 실제 발생 시점이 중요하다
- 여러 소스 간 조인에서 시계 차이와 지연을 견뎌야 한다
- 시간 순서 기반 sessionization, funnel, dedup을 한다

예를 들어 사용자의 장바구니 담기와 결제가 3분 간격으로 발생했는데, 결제 이벤트가 네트워크 문제로 2분 늦게 도착했다고 하자. processing time으로 보면 관계가 뒤틀릴 수 있다. event time으로 봐야 비즈니스 의미가 유지된다.

### Ingestion Time은 왜 애매한가

Ingestion time은 과거에는 event time보다 단순하고 processing time보다 안정적인 절충안처럼 여겨졌지만, 실무에서 요즘은 주력 선택지로 많이 쓰이지 않는다. 이유는 명확하다.

- 진짜 이벤트 발생 시각을 대체하지 못한다
- 시스템 유입 지연이 있으면 비즈니스 의미가 왜곡된다
- 그래도 processing time보다 구현 단순성 이점이 압도적이지는 않다

즉 대부분의 실무 판단은 결국 둘 중 하나다.

- **정말 이벤트 시각이 중요하면 event time**
- **그 정도까지 필요 없고 단순성과 즉시성이 더 중요하면 processing time**

### 자주 하는 실수: Event Time을 선택해놓고 처리 방식은 Processing Time처럼 운영한다

이게 꽤 흔하다.

- event timestamp를 붙여두긴 했는데 watermark를 거의 현재 시각으로 밀어버린다
- late event 정책이 없어서 사실상 늦은 이벤트를 버린다
- 결과 방출은 빠르게 하는데 정정 경로가 없다

이러면 이름만 event time이고 실제 운영은 processing time에 가깝다. 결국 중요한 것은 `timestamp` 컬럼 존재 여부가 아니라, **늦게 온 이벤트를 시스템이 어떻게 해석하고 처리하는가**다.

---

## 핵심 개념 2: Watermark는 "조금 늦어도 받아준다"가 아니라 "여기까지는 거의 끝났다"라는 판단 기준이다

Watermark를 단순히 "3분 늦은 데이터 허용"처럼 외우면 운영에서 계속 흔들린다. Watermark의 본질은 아래에 가깝다.

> 현재 시점에서 시스템이 보기에, 이 시각 이전의 이벤트는 대부분 도착했다고 판단하는 신호

즉 watermark는 데이터 완료 신호의 근사치다.

### 왜 이게 중요한가

윈도우 집계는 언젠가 닫혀야 결과를 내보낼 수 있다. 그런데 event time에서는 미래에 늦은 이벤트가 올 수도 있다. 그래서 시스템은 "이 정도면 거의 다 왔다"는 기준이 필요하다. 그 기준이 watermark다.

예를 들어 `B` 시점의 watermark가 10:05라고 하자. 이 말은 보통 아래 의미다.

- 10:05 이전 이벤트는 대부분 도착했다고 본다
- 10:05 이전 윈도우는 방출 또는 정리 대상이 될 수 있다
- 이후 들어오는 10:04 이벤트는 late event로 처리할 수 있다

### bounded out-of-orderness를 너무 단순하게 보면 안 되는 이유

많이 쓰는 방식이 "최대 5분 지연" 같은 bounded out-of-orderness watermark다. 예를 들어 아래 같은 개념이다.

```java
WatermarkStrategy
  .<OrderEvent>forBoundedOutOfOrderness(Duration.ofMinutes(5))
  .withTimestampAssigner((event, ts) -> event.getEventTime())
```

이 설정을 보면 사람들은 쉽게 이렇게 이해한다.

- 모든 이벤트는 5분 안에 온다
- 그러니 5분만 기다리면 안전하다

하지만 실제 운영은 훨씬 복잡하다.

- 평균 지연은 30초지만, 특정 OS 버전 앱은 20분 지연될 수 있다
- 대부분 파티션은 빠른데 한 파티션만 매우 느릴 수 있다
- 밤에는 정상인데 출근 시간대 네트워크 품질이 나빠질 수 있다
- CDC source는 커밋 지연이 특정 테이블에서만 길어질 수 있다

즉 watermark 지연값은 단순 평균이 아니라, **정확도와 지연 사이의 계약값**이다.

### watermark가 너무 빠르면 생기는 일

- 윈도우가 너무 빨리 닫힌다
- 늦게 도착한 정상 이벤트가 late event가 된다
- 본 집계 결과와 배치 정산 결과가 계속 어긋난다
- side output과 보정 로직이 폭증한다

### watermark가 너무 느리면 생기는 일

- 결과 방출이 늦어진다
- 윈도우 상태가 오래 유지된다
- checkpoint 크기와 state 사용량이 늘어난다
- 다운스트림 알림/대시보드 지연이 커진다

결국 watermark는 성능 튜닝 숫자가 아니라, **업무 정확도와 결과 지연을 어떻게 교환할지 결정하는 운영 파라미터**다.

### idle source를 고려하지 않으면 watermark 전체가 멈출 수 있다

실무에서 특히 자주 놓치는 부분이다. Flink는 여러 파티션이나 서브태스크의 watermark를 종종 최소값 기준으로 전파한다. 이때 한 파티션이 더 이상 데이터가 안 들어오는데 idle로 표시되지 않으면, 그 파티션의 watermark가 전체 진행을 붙잡을 수 있다.

증상은 이렇다.

- 일부 파티션은 잘 흐르는데 전체 윈도우가 닫히지 않는다
- Kafka 특정 파티션이 한동안 비어 있으면 결과가 안 나간다
- 운영자는 "job은 살아 있는데 왜 숫자가 멈췄지"를 겪는다

이 문제를 막으려면 watermark 전략에서 **idle source 감지**를 반드시 같이 봐야 한다.

### 운영 기준: watermark는 코드 상수보다 데이터 지연 분포 기반으로 잡는다

좋은 질문은 "5분이 적당할까"가 아니라 아래다.

- p95, p99 이벤트 지연은 얼마인가
- 특정 국가, 앱 버전, 파티션에서 지연 꼬리가 긴가
- 결과를 2분 빨리 내는 대신 몇 %의 늦은 이벤트를 보정 경로로 보내는가
- downstream이 업데이트를 받아들일 수 있는가

즉 watermark 값은 감으로 찍는 숫자가 아니라, **실제 지연 분포를 보고 정하는 SLA**다.

---

## 핵심 개념 3: Window는 편한 집계 도구지만, 실무에서는 "결과 수정 정책"까지 같이 설계해야 한다

Flink에서 window는 매우 강력하다. 하지만 단순히 `TumblingEventTimeWindows.of(...)` 문법만 알고 들어가면 금방 한계에 부딪힌다.

### 윈도우의 본질

윈도우는 무한 스트림을 유한 계산 단위로 자르는 방법이다. 예를 들어 아래처럼 쓸 수 있다.

- 5분 단위 매출 집계
- 1시간 단위 에러 카운트
- 30분 inactivity 기준 세션 집계

하지만 실무에서 진짜 중요한 것은 윈도우 종류보다 아래다.

- 언제 윈도우를 닫을 것인가
- 늦게 온 데이터를 반영할 것인가
- 이미 방출한 결과를 수정할 것인가
- 상태를 언제 정리할 것인가

### Tumbling, Sliding, Session을 기능보다 비용 관점으로 봐야 한다

#### Tumbling Window

- 가장 이해하기 쉽다
- 한 이벤트는 보통 한 윈도우에만 속한다
- 집계 결과 해석이 단순하다
- 운영 리포트, 분 단위 KPI에 자주 잘 맞는다

#### Sliding Window

- 같은 이벤트가 여러 윈도우에 중복 포함될 수 있다
- 결과는 촘촘하게 나오지만 상태와 계산량이 커진다
- 1시간 이동평균 같은 곳에 유용하다
- 잘못 쓰면 state가 빠르게 불어난다

#### Session Window

- 사용자 inactivity 기준으로 세션을 만든다
- 사용자 행동 분석에는 강력하다
- 늦은 이벤트가 오면 세션 병합이 발생할 수 있다
- 결과 수정 정책이 더 중요해진다

### allowed lateness는 공짜 기능이 아니다

`allowedLateness`를 두면 윈도우 종료 뒤 일정 시간 동안 늦게 온 이벤트를 받아 다시 계산할 수 있다. 직관적으로 좋아 보이지만 비용이 있다.

- 윈도우 상태를 더 오래 유지해야 한다
- 결과를 여러 번 수정해 내보낼 수 있다
- sink가 업데이트형 출력을 받아야 한다
- downstream 테이블이나 캐시가 upsert를 지원해야 한다

즉 allowed lateness를 쓰려면 먼저 물어봐야 한다.

- 결과를 정정할 경로가 있는가
- 아니면 late event를 별도 side output으로 빼서 배치 보정할 것인가

### 실무 판단: 늦은 데이터 처리 방식은 보통 세 가지다

#### 1) 바로 수정 반영

- 윈도우 결과를 update/retract 형태로 재발행
- 실시간 대시보드, 알림 시스템에 적합할 수 있음
- downstream이 upsert semantics를 지원해야 함

#### 2) side output으로 분리 후 별도 보정

- 실시간 파이프라인은 기준 시점까지만 처리
- 늦은 이벤트는 별도 토픽/테이블로 보내 배치 보정
- 운영 구조는 늘지만 의미가 명확함

#### 3) 일정 수준 이상 늦으면 폐기

- 반응 속도가 매우 중요하고 늦은 이벤트 비율이 낮을 때 가능
- 다만 폐기율과 영향 범위를 반드시 측정해야 함

즉 window 설계에서 중요한 것은 문법보다 **결과를 정정할지, 보정할지, 버릴지의 정책**이다.

---

## 핵심 개념 4: Flink State는 메모리 캐시가 아니라 장애 복구와 정합성을 떠받치는 저장 계층이다

Flink를 처음 쓸 때 state를 단순히 "연산 중간값"으로 보기 쉽다. 하지만 운영 단계에서 state는 훨씬 더 무겁다.

- aggregation의 누적 값
- dedup을 위한 최근 event id 집합
- join을 위한 양쪽 스트림의 보류 데이터
- 세션 계산을 위한 사용자별 활동 기록
- 타이머 발화를 위한 키별 시간 정보

즉 state는 실시간 계산의 편의 기능이 아니라, **과거 이벤트의 맥락을 미래 이벤트와 연결하는 저장소**다.

### Keyed State를 잘못 이해하면 왜 위험한가

예를 들어 사용자별 최근 주문 상태를 유지한다고 하자. `user_id`로 keyBy 후 `ValueState`에 상태를 넣는 순간, 다음 사실이 생긴다.

- state 크기는 사용자 수와 거의 비례해 커질 수 있다
- hot key가 있으면 특정 태스크만 과도하게 무거워질 수 있다
- checkpoint 시 이 상태를 저장해야 한다
- TTL 정책이 없으면 사실상 무기한 누적될 수 있다

즉 keyed state를 쓴다는 건 곧 **운영 저장소 하나를 job 안에 들이는 것**과 비슷하다.

### Window State와 Keyed State를 구분해야 한다

둘 다 상태지만 목적이 다르다.

- Window State: 특정 시간 구간 결과를 만들기 위해 잠시 유지되는 상태
- Keyed State: 시간 구간과 무관하게 key 기준 문맥을 오래 유지하는 상태

예를 들어 "10분 주문 수"는 window state로 충분할 수 있다. 반면 "같은 주문 ID 중복 이벤트를 24시간 동안 제거"는 keyed state가 더 자연스럽다.

이걸 구분 못하면 자주 이런 일이 생긴다.

- 단순 시간 집계를 복잡한 keyed state + timer로 과구현한다
- 반대로 긴 문맥이 필요한 문제를 window로 억지 해결하려다 상태 정리가 꼬인다

### RocksDB 상태 백엔드는 왜 자주 등장하나

메모리 상태가 빠르더라도 큰 상태에서는 한계가 빨리 온다. 그래서 실무에서 Flink 대규모 state job은 RocksDB 기반 상태 백엔드를 자주 쓴다. 이유는 단순하다.

- 큰 상태를 디스크 기반으로 더 안정적으로 담을 수 있다
- checkpoint와 증분 스냅샷에 유리한 경우가 많다
- 메모리 압박을 완화할 수 있다

하지만 공짜는 아니다.

- 직렬화 비용과 로컬 디스크 I/O가 늘 수 있다
- state access latency가 메모리보다 커질 수 있다
- compaction, local disk 사용량, checkpoint 스토리지 비용을 같이 봐야 한다

즉 RocksDB는 "대규모 state의 현실적 선택지"이지, 무조건 빠른 기본값은 아니다.

### 중요한 감각: state 설계가 곧 비용 설계다

state를 설계할 때는 아래를 같이 봐야 한다.

- key cardinality가 얼마나 큰가
- 각 key당 보존해야 하는 값이 얼마인가
- 상태를 얼마나 오래 유지해야 하는가
- 재시작 시 checkpoint restore 시간이 얼마나 허용되는가
- state가 커질수록 결과 지연과 비용이 어떻게 변하는가

즉 Flink state는 자료구조가 아니라 **지연, 스토리지, 복구 시간, 운영 난이도를 결정하는 핵심 자산**이다.

---

## 핵심 개념 5: Checkpoint와 Savepoint는 비슷해 보여도 목적이 다르다

둘 다 상태를 저장하니 헷갈리기 쉽다. 하지만 운영 관점에서 구분이 매우 중요하다.

### Checkpoint의 역할

Checkpoint는 주기적으로 찍는 장애 복구 기준점이다.

- job이 살아 있는 동안 자동으로 생성된다
- source offset, operator state, keyed state를 함께 묶는다
- 장애 후 가장 최근 일관된 상태로 복구하는 데 쓴다

즉 checkpoint는 **runtime safety net**이다.

### Savepoint의 역할

Savepoint는 보통 운영자가 의도적으로 만드는 상태 스냅샷이다.

- 버전 업그레이드
- 코드 변경 후 재배포
- 병렬도 조정
- 계획된 점검 및 재시작

즉 savepoint는 **planned change를 위한 이동 지점**에 가깝다.

### 왜 둘을 섞어 생각하면 안 되나

운영 중 흔한 오해는 이런 것이다.

- checkpoint만 잘 찍히면 배포 변경도 마음대로 될 것이다
- savepoint만 있으면 장애 복구도 같은 식으로 하면 된다

하지만 실제로는 다르다.

- checkpoint는 짧은 주기로 자동 관리되며 장애 복구에 최적화된다
- savepoint는 호환성, 연산자 UID, 상태 매핑 변경 등을 신중히 다뤄야 한다

특히 코드 변경 시 operator UID 관리가 불안정하면 savepoint restore가 꼬일 수 있다. 그래서 Flink 운영에서는 **상태를 가진 연산자의 identity를 안정적으로 유지하는 습관**이 중요하다.

### checkpoint 주기와 timeout은 어떻게 볼까

checkpoint를 너무 자주 찍으면?

- I/O 오버헤드가 커진다
- backpressure가 있을 때 checkpoint alignment 비용이 커질 수 있다
- 대형 state job은 오히려 전체 처리량에 영향을 준다

반대로 너무 드물게 찍으면?

- 장애 시 재처리 구간이 길어진다
- 복구 후 duplicate 처리 부담이 커진다
- source와 sink 외부 시스템에 미치는 재실행 영향이 커진다

결국 checkpoint 주기는 **복구 시 잃어도 되는 시간과 steady-state 오버헤드의 균형**이다.

### unaligned checkpoint를 언제 고민할까

backpressure가 심한 파이프라인에서는 aligned checkpoint가 지연될 수 있다. 이런 상황에서 unaligned checkpoint가 도움이 될 수 있다. 다만 이것도 만능은 아니다.

- 네트워크 버퍼까지 스냅샷에 포함될 수 있어 저장량이 커질 수 있다
- 특정 병목 구조에서는 도움이 크지만, 근본적인 backpressure 원인을 해결하지는 못한다

즉 unaligned checkpoint는 구조적 병목을 가리는 옵션이 아니라, **checkpoint 진행이 막히는 환경에서 복구 가능성을 높이는 도구**로 봐야 한다.

---

## 핵심 개념 6: Exactly-once는 Flink 내부 옵션이 아니라 end-to-end 계약이다

Flink는 exactly-once 처리를 강하게 내세우지만, 이 말을 너무 넓게 믿으면 사고가 난다.

### Flink가 강하게 보장하는 구간

적절한 source와 checkpoint 기반 하에서 Flink는 보통 아래 구간에서 강한 일관성을 제공할 수 있다.

- source offset 관리
- operator state 업데이트
- 장애 후 동일 checkpoint 기준 복구

즉 엔진 내부 상태 관점에서는 매우 강력하다.

### 하지만 sink 경계에서 이야기가 달라진다

예를 들어 결과를 아래로 내보낸다고 하자.

- Kafka topic
- JDBC sink
- Elasticsearch
- object storage
- 외부 HTTP API

이때 truly end-to-end exactly-once가 되려면 sink도 해당 의미를 받아줘야 한다.

### sink별 현실

#### Kafka transactional sink

- 비교적 강한 exactly-once 구성이 가능하다
- checkpoint와 트랜잭션 경계를 맞춘다
- 소비자도 isolation 설정을 제대로 써야 의미가 산다

#### JDBC upsert sink

- 보통 idempotent upsert로 의미적 exactly-once에 가깝게 맞춘다
- 진짜 물리적 exactly-once라기보다 중복 재적용해도 결과가 같도록 설계하는 편이 많다

#### 외부 HTTP API

- 거의 항상 exactly-once가 어렵다
- idempotency key, dedup table, outbox 패턴 같은 보완이 필요하다

즉 실무에서 더 안전한 질문은 이것이다.

> Flink 내부 exactly-once를 바깥 시스템에서도 유지할 수 있는가, 아니면 sink를 멱등적으로 설계해 결과적 중복을 제거할 것인가?

### TwoPhaseCommitSinkFunction류 접근을 만능으로 보면 안 된다

2PC 기반 sink 패턴은 강력하지만, 운영 복잡성도 높다.

- 외부 시스템이 prepare/commit semantics를 지원해야 한다
- 트랜잭션 타임아웃과 checkpoint 간격 관계를 관리해야 한다
- 복구 시 미완료 트랜잭션 정리가 필요하다

그래서 많은 팀은 이론적 exactly-once보다 **업무 키 기반 idempotent sink**를 택한다. 예를 들어 집계 결과를 `(window_start, store_id)` 기준 upsert하면 중복 재전송이 있어도 최종 결과는 같게 만들 수 있다.

실무적으로는 이 방식이 더 단단한 경우가 많다.

---

## 핵심 개념 7: State TTL은 메모리 청소 기능이 아니라 "얼마나 오래 문맥을 기억할 것인가"를 정하는 정책이다

State TTL을 처음 보면 좋아 보인다.

- 오래된 state를 지워준다
- 메모리 사용량을 낮춰준다
- state 무한 증가를 막아준다

맞는 말이다. 하지만 중요한 절반은 빠져 있다. TTL은 곧 **업무적으로 얼마 동안 과거를 기억할 것인가**를 정한다.

### TTL이 잘 맞는 사례

- 최근 24시간 dedup
- 최근 30분 세션 추적
- 7일 동안 다시 올 수 있는 이벤트 상관관계 유지
- 일정 기간 이후 의미가 사라지는 임시 조인 상태

예를 들어 결제 중복 처리에서 같은 `payment_id`를 48시간만 기억하면 충분하다면 TTL은 훌륭하다.

### TTL이 위험해지는 사례

- 실제 지연 이벤트는 72시간 뒤에도 올 수 있는데 TTL을 24시간으로 둠
- 고객 활동 재개가 드문 서비스인데 세션 문맥을 너무 빨리 지움
- 조인 상대 스트림이 느릴 수 있는데 한쪽 상태를 일찍 삭제함

이 경우 결과는 단순 메모리 최적화가 아니라 **정합성 손실**이다.

### TTL을 쓰면 결과가 달라질 수 있다는 점을 받아들여야 한다

예를 들어 주문 이벤트와 배송 이벤트를 `order_id`로 조인한다고 하자. 배송 이벤트가 늦게 올 수 있는데 주문 상태 TTL이 6시간이면, 7시간 뒤 도착한 배송 이벤트는 조인에 실패할 수 있다.

즉 TTL은 단순한 캐시 만료가 아니다. **업무적으로 그 이후 이벤트는 연결하지 않겠다**는 선언과 같다.

### TTL 설계 기준

TTL을 정할 때는 아래를 같이 봐야 한다.

- 실제 이벤트 지연 분포
- 비즈니스상 최대 허용 지연
- state 비용 증가 곡선
- 늦은 이벤트 누락이 미치는 영향
- 배치 보정 경로 존재 여부

좋은 운영은 보통 이렇게 간다.

- 실시간 파이프라인은 합리적 TTL로 메모리와 지연을 통제
- TTL 밖 늦은 이벤트는 별도 보정 경로로 보냄
- TTL 만료율과 늦은 이벤트 비율을 지속 모니터링

---

## 실무 예시 1: 주문 스트림 10분 매출 집계에서 Event Time과 Watermark를 어떻게 잡을까

상황을 보자.

- Kafka에 주문 생성 이벤트가 들어온다
- 대시보드에는 10분 단위 매출이 보인다
- 모바일 앱 환경상 일부 이벤트는 2~3분 늦게 들어온다
- 아주 드물게 20분 이상 늦는 이벤트도 있다

### 나쁜 첫 구현

- processing time tumbling window 사용
- 늦은 이벤트는 그냥 현재 시점 집계에 포함
- 결과는 빠르지만 정산 데이터와 계속 어긋남

### 더 나은 설계

- event time 기준 10분 tumbling window
- watermark는 지연 분포 기반으로 예를 들어 4~5분 수준에서 시작
- 5분 이상 늦은 이벤트는 side output으로 보내 별도 보정
- sink는 `(window_start, store_id)` 기준 upsert

예시 코드는 아래처럼 잡을 수 있다.

```java
stream
  .assignTimestampsAndWatermarks(
      WatermarkStrategy
        .<OrderEvent>forBoundedOutOfOrderness(Duration.ofMinutes(5))
        .withTimestampAssigner((event, ts) -> event.getEventTimeMillis())
        .withIdleness(Duration.ofMinutes(1))
  )
  .keyBy(OrderEvent::getStoreId)
  .window(TumblingEventTimeWindows.of(Time.minutes(10)))
  .allowedLateness(Time.minutes(2))
  .sideOutputLateData(lateTag)
  .aggregate(new SalesAgg(), new SalesWindowResultFn())
```

### 여기서 중요한 판단

- allowed lateness를 둘 경우 대시보드가 update를 받아야 한다
- side output late data는 배치 보정 또는 별도 audit 경로가 있어야 한다
- watermark 5분은 정답이 아니라 시작점이며, 실제 late 비율을 보고 조정해야 한다

### 추천 운영 지표

- 윈도우별 late event 비율
- watermark lag
- 윈도우 결과 최초 방출 지연
- 수정 방출 횟수
- 대시보드 수치와 정산 배치 수치 차이

이 지표를 보지 않으면 watermark는 감으로 유지될 수밖에 없다.

---

## 실무 예시 2: 결제 중복 방지에서 Keyed State와 TTL을 어떻게 써야 하나

상황:

- PG 재시도, 네트워크 재전송, 소비자 재시작 때문에 같은 결제 이벤트가 중복 유입될 수 있다
- 목표는 같은 `payment_id`를 일정 기간 한 번만 처리하는 것

가장 직관적인 방식은 keyed state에 최근 처리 여부를 저장하는 것이다.

```java
public class PaymentDedupProcess extends KeyedProcessFunction<String, PaymentEvent, PaymentEvent> {

    private transient ValueState<Boolean> seen;

    @Override
    public void open(Configuration parameters) {
        StateTtlConfig ttl = StateTtlConfig
            .newBuilder(org.apache.flink.api.common.time.Time.hours(48))
            .setUpdateType(StateTtlConfig.UpdateType.OnCreateAndWrite)
            .build();

        ValueStateDescriptor<Boolean> desc = new ValueStateDescriptor<>("seen-payment", Boolean.class);
        desc.enableTimeToLive(ttl);
        seen = getRuntimeContext().getState(desc);
    }

    @Override
    public void processElement(PaymentEvent value, Context ctx, Collector<PaymentEvent> out) throws Exception {
        if (seen.value() == null) {
            seen.update(true);
            out.collect(value);
        }
    }
}
```

### 이 방식의 장점

- 구현이 단순하다
- sink 중복을 크게 줄일 수 있다
- idempotency key 처리 구조가 명확하다

### 하지만 꼭 따져야 할 점

- 48시간 뒤 다시 동일 payment_id가 오면 새 이벤트로 간주된다
- TTL이 processing time 기반 정리인지, event time 의미와 얼마나 어긋나는지 확인해야 한다
- state backend가 커질수록 checkpoint 비용이 증가한다

### 실무 판단

- PG 재전송 패턴상 대부분 24시간 내 재시도라면 TTL 48시간은 현실적일 수 있다
- 반대로 배치 재적재나 상류 재전송이 3일 뒤에도 가능하다면 TTL이 너무 짧다
- 장기 중복 방지가 필요하면 Flink state만으로 끝내지 말고 외부 idempotency store를 고려해야 한다

즉 dedup은 "state에 넣고 TTL 걸면 끝"이 아니라, **중복이 발생하는 최대 시간 범위를 얼마나 신뢰성 있게 커버할 것인가**의 문제다.

---

## 실무 예시 3: 주문 이벤트와 배송 이벤트 스트림 조인에서 왜 state TTL이 정합성 문제로 이어지나

상황:

- 주문 생성 이벤트 stream A
- 배송 시작 이벤트 stream B
- `order_id` 기준으로 두 스트림을 연결해 리드타임 계산

직관적으로는 interval join이나 keyed co-process로 구현하면 된다. 문제는 실제 도착 순서다.

- 주문은 즉시 들어오지만 배송은 몇 시간 뒤 들어올 수 있다
- 어떤 경우는 CDC 지연으로 주문 이벤트가 더 늦게 올 수도 있다

이때 흔한 실수는 아래다.

- 주문 state TTL 1시간
- 배송 state TTL 1시간
- 운영 초반엔 잘 되다가 야간 지연 구간에서 누락 증가

왜냐하면 TTL이 실제 최대 도착 지연보다 짧아서, 조인 전에 상태가 사라지기 때문이다.

### 더 나은 접근

- 양쪽 스트림 도착 지연 분포를 별도로 본다
- state TTL은 더 긴 쪽 지연 + 안전 여유를 포함한다
- 너무 긴 TTL이 부담되면 late pair를 별도 reconciliation topic으로 보낸다
- 최종 리포트는 실시간 결과 + 보정 배치를 합쳐 본다

핵심은 이것이다.

> 스트림 조인의 state TTL은 성능 숫자가 아니라, 두 이벤트가 만날 수 있는 최대 시간차에 대한 업무 가정이다.

---

## 실무 예시 4: checkpoint는 성공하는데 복구가 계속 느린 job의 원인은 무엇일까

상황:

- job은 2분마다 checkpoint 성공
- state 크기는 수백 GB
- 장애 후 복구 시간이 20분 이상 걸림
- 운영팀은 "checkpoint 잘 찍히는데 왜 복구가 이렇게 느리지"를 겪음

이 문제는 자주 checkpoint 성공 여부만 보고 안심해서 생긴다.

### 가능한 원인

- state 자체가 너무 큼
- 키 cardinality가 지나치게 크고 TTL이 없음
- checkpoint storage 대역폭이 부족함
- restore 시 원격 상태 다운로드가 병목임
- operator 병렬도 변경으로 state 재분배 비용이 큼

### 이때 봐야 할 것

- checkpoint duration만이 아니라 restore duration
- total state size와 incremental checkpoint size
- state backend 종류와 local disk 상태
- TTL 적용 가능 여부
- 불필요한 wide state 구조 존재 여부

즉 checkpoint 성공률은 시작일 뿐이다. 운영 기준은 **장애 후 어느 시간 안에 정상 처리량으로 돌아오는가**까지 포함해야 한다.

---

## 실무 예시 5: Flink SQL로 빠르게 만들었는데 update semantics를 몰라 sink가 망가지는 경우

Flink SQL은 생산성이 좋다. 하지만 window aggregation과 join 결과가 항상 append-only는 아니다.

예를 들어 event time window + late data를 쓰면 결과가 다음처럼 변할 수 있다.

- 첫 방출: `(window=10:00, store=1, amount=100)`
- 늦은 이벤트 반영 후 수정: `(window=10:00, store=1, amount=130)`

만약 sink가 단순 append 로그 테이블이라면, 두 레코드가 모두 남을 수 있다. 그러면 downstream은 어떤 값이 최종값인지 스스로 해석해야 한다.

### 그래서 먼저 확인해야 할 것

- 현재 쿼리 결과가 append stream인가 changelog stream인가
- sink가 upsert/delete/retract를 지원하는가
- primary key 선언이 필요한가
- late data 반영 시 downstream이 수정 이벤트를 소화할 수 있는가

Flink SQL이 편한 만큼 더 자주 생기는 실수는, **결과 형태를 append로 착각한 채 운영 sink에 연결하는 것**이다.

---

## 트레이드오프 1: 빠른 watermark는 지연을 줄이지만 늦은 이벤트 손실과 보정 비용을 키운다

### 장점

- 윈도우가 빨리 닫힌다
- 대시보드 숫자가 빨리 나온다
- state 유지 시간이 줄어든다
- checkpoint 부담이 줄어들 수 있다

### 비용

- 늦은 이벤트가 더 많이 late 처리된다
- 보정 경로가 복잡해진다
- 실시간 수치와 확정 수치 차이가 커질 수 있다

즉 빠른 watermark는 공격적인 운영 모드다. downstream이 정정이나 보정을 잘 받아줄 때만 안정적이다.

---

## 트레이드오프 2: 긴 allowed lateness는 정확도를 올리지만 상태와 sink 복잡도를 키운다

### 장점

- 늦은 이벤트를 더 많이 본 집계에 반영할 수 있다
- 배치 보정 의존이 줄어든다
- 최종 실시간 수치의 정확도가 올라간다

### 비용

- 윈도우 상태가 오래 남는다
- 결과 수정 이벤트가 많아질 수 있다
- sink가 upsert/changelog를 제대로 처리해야 한다
- 사용자는 숫자가 자꾸 바뀌는 경험을 할 수 있다

즉 실시간 대시보드가 꼭 한 번만 값을 내야 하는 시스템이라면 긴 allowed lateness는 맞지 않을 수 있다.

---

## 트레이드오프 3: 큰 state는 풍부한 문맥을 제공하지만 checkpoint, 복구, 비용을 급격히 늘린다

### 장점

- 긴 기간 dedup 가능
- 복잡한 조인과 세션 계산 가능
- 실시간에서 더 많은 업무 규칙을 처리 가능

### 비용

- checkpoint 시간이 길어진다
- restore가 느려진다
- RocksDB/local disk/storage 비용이 증가한다
- hot key와 skew 문제가 더 심각해진다

즉 state는 많이 들수록 좋은 것이 아니라, **실시간에서 꼭 필요한 최소 문맥만 유지하는 것**이 중요하다.

---

## 트레이드오프 4: end-to-end exactly-once를 밀어붙일수록 운영 복잡도도 같이 올라간다

### 장점

- 중복과 유실을 구조적으로 줄일 수 있다
- 재시작과 장애 대응 시 의미가 명확하다
- 금융, 정산, 청구 영역에서 강력하다

### 비용

- sink 제약이 커진다
- 트랜잭션 타임아웃과 checkpoint 관계를 관리해야 한다
- 디버깅 난도가 올라간다
- 외부 시스템 호환성 한계에 자주 부딪힌다

그래서 많은 팀은 "완전한 exactly-once"보다 **Flink 내부 exactly-once + 외부 sink idempotency** 조합을 더 현실적으로 선택한다.

---

## 흔한 실수 1: 이벤트 timestamp만 있으면 event time을 제대로 쓰고 있다고 생각한다

timestamp 컬럼이 있어도 watermark 전략, late event 정책, sink update semantics가 없으면 실질적으로 event time 운영이 아니다.

---

## 흔한 실수 2: watermark를 고정 상수로 두고 실제 지연 분포를 보지 않는다

서비스 국가, 디바이스, 네트워크, 소스 종류가 바뀌면 지연 분포도 바뀐다. watermark는 한 번 정하고 끝나는 값이 아니다.

---

## 흔한 실수 3: idle partition을 무시해 전체 watermark 정체를 만든다

특정 파티션이 한동안 비어 있을 때 전체 윈도우가 닫히지 않는 문제는 실무에서 아주 흔하다. source idleness 설정을 기본 체크 항목으로 넣는 편이 낫다.

---

## 흔한 실수 4: state TTL을 메모리 최적화 옵션으로만 본다

TTL은 그 시간이 지나면 과거 문맥을 잊겠다는 뜻이다. dedup, join, 세션 결과가 실제로 달라질 수 있다.

---

## 흔한 실수 5: checkpoint 성공률만 보고 복구 시간을 보지 않는다

운영 SLA는 "checkpoint가 성공하는가"보다 **장애 후 몇 분 안에 정상 서비스로 복귀하는가**에 더 가깝다.

---

## 흔한 실수 6: Flink SQL 결과를 append stream으로 착각한다

window update, join retraction, late event 수정이 있는 쿼리는 changelog일 수 있다. sink가 이를 수용하지 못하면 결과 해석이 망가진다.

---

## 흔한 실수 7: exactly-once를 엔진 옵션 한 줄로 끝났다고 생각한다

source, state, sink, 외부 트랜잭션, 소비자 읽기 방식까지 맞아야 의미가 산다. 그렇지 않으면 멱등 설계가 더 현실적일 수 있다.

---

## 설계 체크리스트: 새 Flink 파이프라인을 만들기 전에

### 시간 모델

- [ ] 이 파이프라인은 processing time으로 충분한가, 아니면 event time이 필수인가?
- [ ] event timestamp의 품질은 신뢰할 수 있는가?
- [ ] 여러 소스 간 시계 차이나 지연 특성이 다른가?

### watermark와 late data

- [ ] 실제 지연 분포(p95, p99, tail)를 측정했는가?
- [ ] idle partition/source를 처리하는가?
- [ ] 늦은 이벤트는 수정 반영, side output, 폐기 중 무엇으로 다룰 것인가?
- [ ] 결과 지연 SLA와 정확도 SLA를 문서화했는가?

### state

- [ ] 어떤 state가 필요한지, key cardinality는 얼마나 되는지 알고 있는가?
- [ ] state TTL은 업무상 기억해야 하는 최대 시간과 맞는가?
- [ ] RocksDB 등 상태 백엔드 선택 이유가 명확한가?
- [ ] hot key나 skew 가능성을 점검했는가?

### checkpoint와 복구

- [ ] checkpoint 간격은 복구 손실 허용 범위와 맞는가?
- [ ] timeout, min pause, concurrent checkpoint 설정이 job 특성과 맞는가?
- [ ] restore time을 측정하고 있는가?
- [ ] 배포/병렬도 조정 시 savepoint 운영 절차가 있는가?

### sink semantics

- [ ] 결과가 append인지 changelog인지 알고 있는가?
- [ ] sink가 upsert/delete/retract를 수용하는가?
- [ ] end-to-end exactly-once가 가능한가, 아니면 idempotent sink가 현실적인가?
- [ ] sink 중복 발생 시 어떻게 감지하고 복구할 것인가?

---

## 운영 체크리스트: 이미 돌아가는 Flink job이 흔들릴 때 순서대로 볼 것

1. **watermark가 정상적으로 전진하는가?**
   - 특정 source나 partition이 멈춰 있지 않은가
   - idle 처리 누락은 없는가

2. **late event 비율이 급증했는가?**
   - 앱 버전, 국가, 토픽 파티션별 편차가 있는가
   - watermark가 너무 공격적인가

3. **state 크기가 비정상적으로 늘고 있는가?**
   - TTL 누락 또는 너무 긴 TTL은 아닌가
   - key cardinality 증가 원인이 있는가

4. **checkpoint는 빨라도 restore가 느리지 않은가?**
   - total state size, incremental size, storage bandwidth를 보라
   - 장애 이후 실제 복구 시간을 측정하라

5. **sink semantics가 결과 형태와 맞는가?**
   - append로 흘려보냈는데 사실 update stream은 아닌가
   - 중복과 재처리를 downstream이 감당할 수 있는가

이 순서를 지키면 증상만 보고 무작정 병렬도나 리소스부터 올리는 실수를 줄일 수 있다.

---

## 실무에서 추천하는 기본 운영 원칙

### 1) watermark는 추정이 아니라 관측값으로 유지한다

late event 비율, watermark lag, 결과 수정 빈도를 정기 지표로 둬야 한다.

### 2) state는 기능 단위가 아니라 비용 단위로 검토한다

새 state 하나를 추가할 때마다 checkpoint, restore, storage, skew 영향을 같이 보는 습관이 중요하다.

### 3) 실시간 파이프라인과 보정 경로를 분리해 생각한다

모든 늦은 이벤트를 실시간 경로 하나에서 완벽히 처리하려 하면 구조가 과도하게 복잡해진다. 실시간과 보정을 나누면 시스템이 훨씬 안정적일 때가 많다.

### 4) sink는 가능한 한 멱등적으로 만든다

Flink 내부 정확성이 좋아도 외부 시스템이 약하면 운영이 흔들린다. 업무 키 기반 upsert나 idempotency key 전략이 현실적으로 강하다.

### 5) checkpoint 성공만 보지 말고 restore rehearsal도 한다

장애는 실전에서 난다. 복구 시간이 길면 checkpoint 성공률이 높아도 체감 SLA는 무너진다.

### 6) savepoint와 operator UID 관리를 배포 절차에 포함한다

상태를 가진 job은 일반 stateless 서비스처럼 배포하면 안 된다. 상태 매핑 안정성이 곧 운영 안정성이다.

---

## 한 줄 정리

Apache Flink를 실무에서 잘 쓰는 핵심은 단순히 실시간으로 계산하는 것이 아니라, **Event Time과 Watermark로 결과 확정 시점을 설계하고, Checkpoint와 State TTL로 장애 복구와 상태 비용을 통제하며, sink까지 포함한 end-to-end 의미를 맞추는 것**이다.
