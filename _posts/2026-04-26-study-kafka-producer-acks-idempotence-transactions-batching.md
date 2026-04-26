---
layout: post
title: "Kafka Producer 실전: acks, Idempotence, Transactions, Batching으로 유실 없이 처리량까지 잡는 법"
date: 2026-04-26 11:40:00 +0900
categories: [data-infra]
tags: [study, data-infra, kafka, producer, acks, idempotence, transactions, batching, linger-ms, exactly-once]
permalink: /data-infra/2026/04/26/study-kafka-producer-acks-idempotence-transactions-batching.html
---

## 배경: Kafka를 쓴다고 자동으로 안전한 이벤트 발행이 되는 것은 아니다

Kafka를 도입한 팀이 초반에 가장 많이 신경 쓰는 것은 보통 컨슈머다.

- lag가 얼마나 쌓이는가
- 리밸런싱이 왜 자주 일어나는가
- 재시도와 DLQ를 어떻게 나눌 것인가
- 스키마 진화를 어떻게 통제할 것인가

그런데 운영 사고를 조금 더 오래 보다 보면, 실제 문제의 출발점이 프로듀서 쪽인 경우가 아주 많다.

- 이벤트를 보냈다고 믿었는데 브로커 장애 순간 일부 메시지가 실제로는 기록되지 않았다
- 재시도는 잘 됐는데 중복 발행이 생겨 다운스트림 정산이 두 번 실행됐다
- 처리량을 높이려고 설정을 손댔더니 지연은 줄었지만 순서가 어긋났다
- `acks=all`로 바꿨는데도 ISR 축소 상황에서 기대한 수준의 내구성이 나오지 않았다
- exactly-once를 켰다고 생각했지만 실제로는 DB 쓰기와 Kafka 발행 사이가 여전히 찢어져 있었다
- TPS를 올리려고 `linger.ms`, `batch.size`, compression을 조정하다가 tail latency가 튀었다

즉 Kafka Producer를 단순히 “메시지를 보내는 클라이언트”로 보면 운영 판단이 계속 얕아진다.

실무에서 Producer의 본질은 더 정확히 이렇다.

> Kafka Producer는 애플리케이션의 쓰기 요청을, 복제 로그에 대한 내구성·순서·중복·지연·처리량 계약으로 변환하는 계층이다.

이 관점이 중요하다.

왜냐하면 프로듀서 설정 몇 개는 단순 튜닝값이 아니라, 아래를 직접 바꾸기 때문이다.

- 장애 순간 메시지를 잃을 가능성
- 같은 이벤트가 두 번 기록될 가능성
- 같은 key의 순서가 뒤집힐 가능성
- 브로커가 흔들릴 때 애플리케이션의 backpressure 형태
- 네트워크와 CPU를 어떤 방식으로 처리량으로 바꿀지

오늘 글은 Kafka Producer 옵션을 나열하는 입문서가 아니다.

중급 이상 개발자가 실제 운영 환경에서 아래 질문에 답할 수 있도록, **acks, retries, idempotence, transactions, batching**을 중심으로 Producer를 구조적으로 정리한다.

핵심 질문은 여섯 가지다.

1. `acks`는 단순 응답 정책이 아니라 어떤 복제 내구성 계약인가
2. 처리량을 높이는 batching은 왜 latency, 메모리, 압축 효율과 함께 봐야 하는가
3. 재시도는 언제 안전하고, 언제 중복과 순서 역전을 만드는가
4. Idempotent Producer는 어떤 종류의 중복을 막고, 어떤 중복은 전혀 막지 못하는가
5. Kafka transaction은 정확히 어디까지 exactly-once를 보장하고, 어디서 경계가 끊기는가
6. 운영자는 어떤 설정 조합을 기본값으로 두고, 어떤 경우에만 더 공격적으로 튜닝해야 하는가

결론부터 먼저 말하면 이렇다.

**Kafka Producer 운영의 핵심은 “빠르게 보내기”가 아니라, 어떤 장애와 어떤 비용을 허용할지 명확히 정한 뒤 그에 맞는 쓰기 계약을 고르는 것**이다.

---

## 먼저 큰 그림: Producer는 내구성, 순서, 처리량 세 축을 동시에 조정하는 장치다

Kafka Producer를 다룰 때 가장 위험한 착각은 설정을 개별 옵션으로 보는 것이다.

예를 들어 아래는 서로 독립적인 옵션처럼 보인다.

- `acks`
- `retries`
- `enable.idempotence`
- `max.in.flight.requests.per.connection`
- `linger.ms`
- `batch.size`
- `compression.type`

하지만 실무에서는 이 값들이 하나의 시스템으로 움직인다.

예를 들어,

- `acks=1`은 지연을 줄일 수 있지만 리더 장애 직전 응답 성공 메시지가 유실될 수 있다
- `retries`를 키우면 일시 장애 복원력은 늘지만 중복 가능성과 지연 상한을 같이 봐야 한다
- `enable.idempotence=true`는 재시도 중복을 줄여주지만, 애플리케이션 레벨 중복 키 문제까지 해결해주지는 않는다
- `linger.ms`를 키우면 batch 효율은 좋아지지만 소량 트래픽의 p99 latency가 나빠질 수 있다
- `max.in.flight.requests.per.connection`은 처리량을 높이지만 잘못 조합하면 재시도 시 순서 깨짐 가능성이 생긴다

즉 Producer 튜닝은 “옵션 최적화”가 아니라, 아래 세 축을 어디에 둘지 정하는 일이다.

### 1) 내구성

브로커 장애나 네트워크 흔들림이 있을 때, 발행 성공으로 간주한 메시지가 실제로 남아 있는가?

### 2) 순서와 중복 제어

같은 key의 이벤트가 예상 순서대로 기록되는가? 재시도 중복으로 인해 같은 비즈니스 이벤트가 두 번 기록되지는 않는가?

### 3) 처리량과 지연

프로듀서가 네트워크 round trip, 압축, batch 묶음을 통해 얼마나 효율적으로 전송하는가? 그 대가로 tail latency는 얼마나 감수하는가?

이 세 축은 동시에 최고로 만들기 어렵다.

그래서 Producer 설계의 출발점은 “Kafka 기본값이 뭔가”가 아니라 아래 질문이어야 한다.

- 이 토픽의 이벤트를 잃으면 얼마나 큰가?
- 같은 이벤트가 두 번 들어가면 더 위험한가, 늦게 들어가면 더 위험한가?
- 요청당 지연보다 초당 처리량이 더 중요한가?
- 다운스트림이 중복을 흡수할 수 있는가?
- 외부 DB 상태와 Kafka 발행을 함께 묶어야 하는가?

이 질문이 정리되면 설정은 그 다음이다.

---

## 핵심 개념 1: `acks`는 응답 속도 옵션이 아니라 복제 로그에 대한 신뢰 수준이다

`acks`는 흔히 이렇게만 외운다.

- `0`: 응답 안 기다림
- `1`: 리더만 기다림
- `all`: ISR 전체 확인

틀린 설명은 아니지만, 운영 판단에는 너무 얕다.

실제로 `acks`는 **프로듀서가 어떤 시점부터 “이 메시지는 써졌다고 믿겠다”라고 선언할 것인가**를 정하는 옵션이다.

### `acks=0`

프로듀서는 브로커 응답을 기다리지 않는다.

장점:

- 가장 낮은 전송 지연
- 매우 높은 발행 처리량 가능

단점:

- 전송 실패를 애플리케이션이 거의 알기 어렵다
- 브로커가 실제로 기록하지 못해도 성공처럼 보일 수 있다
- 운영성 있는 이벤트 파이프라인 기본값으로는 부적합하다

실무에서는 지표성 fire-and-forget 로그처럼 일부 손실을 감수하는 경우가 아니라면 거의 추천하기 어렵다.

### `acks=1`

리더 파티션이 메시지를 로컬 로그에 append하면 성공 응답을 돌려준다.

장점:

- `acks=all`보다 지연이 낮은 경우가 많다
- 복제 대기 비용 없이 기본적인 성공/실패를 감지할 수 있다

단점:

- 리더가 응답 후 follower 복제 전에 장애 나면 데이터가 사라질 수 있다
- 특히 리더 선출 타이밍과 ISR 축소 상황에서 예상보다 취약할 수 있다

즉 `acks=1`은 “Kafka에 썼다”가 아니라, **현재 리더 한 대에만 썼다**에 더 가깝다.

### `acks=all`

리더가 현재 ISR(In-Sync Replicas) 기준 복제 확인을 받은 뒤 응답한다.

이때 자주 놓치는 포인트는 `acks=all`만으로 충분하지 않다는 점이다.

함께 봐야 할 것이 `min.insync.replicas`다.

예를 들어 replication factor가 3이어도, `min.insync.replicas=1`이면 ISR이 한 대만 남은 상황에서도 리더는 쓸 수 있다. 이 경우 `acks=all`의 의미가 체감상 `acks=1`처럼 약해질 수 있다.

즉 실무에서는 아래처럼 함께 이해해야 한다.

- `replication.factor`: 복제본 총 수
- `min.insync.replicas`: 쓰기 성공으로 인정하기 위한 최소 ISR 수
- `acks=all`: 그 최소 ISR 정책을 따르겠다는 프로듀서 측 선택

### 운영 기준

아래 조합이 보통 중요한 이벤트의 안전한 기본값이다.

- topic replication factor: 3 이상
- `min.insync.replicas=2`
- producer `acks=all`

이 조합의 의미는 명확하다.

> 한 브로커가 장애 나더라도, 최소 두 복제본에 기록되기 전에는 성공으로 보지 않겠다.

물론 대가도 있다.

- follower 지연이 커지면 producer latency가 늘어난다
- ISR 축소 시 쓰기 실패가 더 자주 발생할 수 있다
- 즉 가용성보다 내구성을 우선한 선택이다

이게 중요한 이유는, 많은 팀이 `acks=all`을 켜고 “이제 안전하다”고 안심하기 때문이다. 실제로는 topic ISR 정책과 브로커 상태까지 같이 봐야 비로소 의미가 생긴다.

---

## 핵심 개념 2: Batch는 단순 묶음이 아니라 네트워크 round trip을 처리량으로 바꾸는 방법이다

Kafka Producer가 빠른 이유 중 하나는 메시지를 한 건씩 보내지 않고 batch로 묶기 때문이다.

여기서 핵심 설정이 보통 다음이다.

- `batch.size`
- `linger.ms`
- `compression.type`
- `buffer.memory`

이 설정을 잘못 이해하면 두 가지 극단으로 간다.

- batch를 거의 못 만들어 네트워크 효율이 나빠진다
- batch를 과하게 키워 tail latency와 메모리 압박이 커진다

### `batch.size`: 한 파티션에 대해 얼마나 묶을 것인가

Producer는 파티션별로 레코드를 버퍼링하고, 일정 크기까지 모이면 한 번에 보낸다.

`batch.size`를 키우면 보통 아래 효과가 있다.

- request 수 감소
- 압축 효율 증가
- broker append 효율 개선
- throughput 상승 가능

하지만 무조건 크게 잡는다고 좋은 것은 아니다.

- 낮은 트래픽 토픽은 그만큼 채워지지 않아 이득이 적다
- 메모리 사용량이 늘 수 있다
- 큰 batch 하나가 실패하면 재시도 비용도 커진다

### `linger.ms`: 얼마나 더 기다려 batch를 키울 것인가

트래픽이 폭주하지 않는 서비스에서는 `batch.size`보다 `linger.ms`가 batch 품질에 더 큰 영향을 줄 때가 많다.

`linger.ms=0`이면 보낼 수 있는 순간 바로 전송한다. 지연은 줄지만 묶음 효율이 떨어질 수 있다.

`linger.ms`를 몇 ms라도 주면,

- 더 많은 레코드가 한 batch로 모인다
- compression ratio가 좋아진다
- request 수가 줄어 broker/네트워크 효율이 좋아진다

대신,

- 특히 저QPS 토픽에서 p95/p99 latency가 늘 수 있다
- 동기 API처럼 즉시 반응이 중요한 경로에는 거슬릴 수 있다

실무 감각으로는 이렇다.

- 주문 완료 이벤트처럼 사용자 응답 경로에 직접 붙은 발행: 너무 큰 `linger.ms`는 주의
- 로그 적재, 비동기 후처리 이벤트: 작은 지연을 주고 batching 효율을 얻는 편이 낫다

### `compression.type`: 네트워크를 CPU로 바꾸는 결정

compression은 batch가 클수록 더 이득이 커진다.

- `snappy`: 보통 무난한 기본값
- `lz4`: 빠른 압축/해제와 좋은 처리량 균형
- `zstd`: 더 좋은 압축률, 경우에 따라 CPU 비용 증가
- `gzip`: 압축률은 좋지만 실시간 처리 경로에서 상대적으로 무거울 수 있음

운영에서는 “어떤 알고리즘이 최고냐”보다 아래를 보는 편이 맞다.

- 네트워크 병목이 큰가, CPU 병목이 큰가
- 메시지 크기 분포가 어떤가
- broker와 consumer까지 포함한 전체 비용이 어떤가

### 실무 팁

1. `linger.ms`는 0 또는 아주 작게 고정할 것이 아니라, 실제 p95 latency와 request rate를 보며 조정한다
2. batch 효율은 토픽별 트래픽 패턴에 따라 다르다
3. 고QPS 토픽은 자연스럽게 batch가 만들어지므로 `batch.size` 영향이 더 크고, 저QPS 토픽은 `linger.ms` 영향이 더 크다
4. compression은 Producer만이 아니라 Consumer CPU와 Broker 디스크/네트워크까지 포함한 시스템 비용으로 판단한다

---

## 핵심 개념 3: 재시도는 복원력 장치이지만, 순서와 중복의 위험도 같이 만든다

프로듀서 재시도는 필수에 가깝다. 네트워크 일시 오류, leader election, request timeout은 실제 운영에서 흔하기 때문이다.

문제는 재시도를 단순히 “많을수록 안전”으로 보면 안 된다는 점이다.

### 재시도에서 먼저 봐야 할 것

- `retries`
- `retry.backoff.ms`
- `delivery.timeout.ms`
- `request.timeout.ms`
- `max.in.flight.requests.per.connection`

이 다섯 개는 함께 봐야 한다.

### 왜 재시도만 켜면 끝이 아닌가

예를 들어 같은 파티션에 대해 두 개의 request가 순서대로 나갔다고 하자.

1. request A 전송
2. request B 전송
3. A는 timeout
4. B는 성공
5. A 재시도 성공

이 경우 잘못된 설정 조합에서는 **로그상 순서가 B 뒤에 A가 기록되는 상황**이 생길 수 있다.

특히 과거에는 idempotence 없이 `max.in.flight.requests.per.connection`이 큰 상태에서 이 문제가 중요했다. 지금도 원리를 이해하지 않으면 순서 보장을 과신하게 된다.

### `max.in.flight.requests.per.connection`

한 커넥션에서 응답을 기다리지 않고 동시에 보낼 수 있는 request 수다.

값이 크면 처리량에는 도움이 된다.

하지만 재시도와 결합되면 순서 문제가 중요해진다. 특히 같은 파티션/같은 key 순서가 중요한 토픽이라면, 이 값을 무심코 키우는 것은 위험할 수 있다.

Idempotent Producer를 사용할 때도 일반적으로 **5 이하 제한**이 중요하다. Kafka는 이 범위 안에서 sequence를 관리해 재시도 중복과 순서 꼬임 위험을 줄인다.

### `delivery.timeout.ms`와 `request.timeout.ms`

많은 팀이 `retries`만 보고 끝낸다. 하지만 실제로는 “언제 최종 실패로 보느냐”가 더 중요하다.

- `request.timeout.ms`: 개별 요청 응답을 얼마나 기다릴지
- `delivery.timeout.ms`: send 호출 이후 최종적으로 얼마나 오래 전달을 시도할지

즉 재시도는 무한 의지가 아니라 **시간 예산 안에서의 시도**다.

이 시간이 너무 짧으면 일시 장애 복구 전에 포기한다.
너무 길면 애플리케이션은 오래 대기하고, 상위 서비스는 이미 timeout으로 실패 처리했는데 백그라운드에서 뒤늦게 발행이 성공할 수도 있다.

이런 상황은 특히 HTTP 요청 경로에서 위험하다.

- 클라이언트는 실패로 봄
- 서버는 응답 timeout
- Kafka에는 나중에 이벤트가 기록됨
- 재시도 API를 또 호출하면 중복 비즈니스 이벤트 생성 가능

즉 Producer timeout 전략은 애플리케이션의 request timeout, 재시도 정책, idempotency key 전략과 함께 봐야 한다.

---

## 핵심 개념 4: Idempotent Producer는 “브로커 재시도 중복”을 막아주지만 “비즈니스 중복”까지 해결하지는 않는다

`enable.idempotence=true`는 Kafka Producer에서 가장 가치 대비 효과가 큰 설정 중 하나다.

이 기능이 하는 일은 단순하지만 중요하다.

Producer가 같은 파티션에 대해 재시도하면서 같은 레코드를 다시 보내더라도, 브로커가 producer id와 sequence number를 기준으로 **중복 append를 막아준다**.

### 무엇을 해결해주는가

- ack 손실 또는 timeout 후 재시도에서 같은 메시지가 두 번 기록되는 문제
- leader 장애 복구 과정에서 producer가 “성공했는지 실패했는지 애매한” 요청을 다시 보낼 때 생기는 중복

즉 idempotence는 **프로듀서-브로커 사이 전송 경계에서의 중복 제어**다.

### 무엇을 해결하지 못하는가

아래는 idempotent producer가 해결하지 못한다.

- 애플리케이션이 같은 비즈니스 이벤트를 두 번 생성하는 문제
- 같은 주문 요청이 API 재시도로 두 번 들어오는 문제
- DB write는 성공하고 Kafka publish는 실패해 상위 로직이 다시 전체 작업을 수행하는 문제
- 서로 다른 producer 인스턴스가 같은 의미의 이벤트를 각각 보내는 문제

즉 이런 중복을 막으려면 여전히 필요하다.

- 비즈니스 idempotency key
- outbox pattern
- consumer-side deduplication
- unique constraint 또는 상태 전이 검증

### 왜 기본값처럼 보는 편이 좋은가

대부분의 운영 토픽에서 프로듀서 재시도는 필요하다. 그리고 재시도가 필요한 이상, 브로커 레벨 중복 방지는 거의 필수다.

게다가 최신 Kafka 클라이언트에서는 idempotence의 비용이 과거보다 훨씬 관리 가능하다.

그래서 특별히 ultra-low-latency와 매우 느슨한 손실 허용 로그 스트림이 아니라면, 보통 다음을 기본 출발점으로 두는 편이 낫다.

- `acks=all`
- `enable.idempotence=true`
- 적절한 `retries`
- `max.in.flight.requests.per.connection<=5`

이 조합은 적어도 “일시 장애 재시도로 인해 같은 레코드가 두 번 써지는” 사고를 크게 줄여준다.

---

## 핵심 개념 5: Transaction은 강력하지만, exactly-once의 경계를 정확히 이해해야 한다

Kafka transaction은 자주 과대평가되거나 과소평가된다.

과대평가는 보통 이런 식이다.

- transaction 켰으니 이제 end-to-end exactly-once다

과소평가는 이런 식이다.

- 너무 복잡하니 쓸모 없다

둘 다 절반만 맞다.

### Kafka transaction이 잘하는 것

Kafka transaction은 기본적으로 **여러 파티션/토픽에 대한 write와 consumer offset commit을 하나의 원자적 단위로 묶는 기능**이다.

대표적인 사용처는 다음이다.

- Kafka에서 읽고 가공한 뒤 다른 Kafka 토픽에 쓰는 stream processing
- consume-process-produce 파이프라인에서 “출력 이벤트와 입력 offset commit”을 함께 원자화하는 경우

예를 들어,

1. input topic에서 메시지 읽음
2. 변환 후 output topic에 여러 레코드 씀
3. input offset commit
4. 위 과정을 하나의 transaction으로 묶음

이렇게 하면 중간 장애 시,

- 출력만 남고 offset은 안 남는 상태
- offset만 커밋되고 출력은 없는 상태

같은 찢어진 상태를 줄일 수 있다.

### Kafka transaction이 못 하는 것

여기서 가장 중요한 경계가 나온다.

Kafka transaction은 **Kafka 내부 자원**에 대해서만 원자성을 강하게 제공한다.

즉 아래는 자동으로 해결되지 않는다.

- DB insert + Kafka publish
- 외부 API 호출 + Kafka publish
- Redis 업데이트 + Kafka publish
- S3 파일 저장 + Kafka publish

이 영역은 여전히 분산 트랜잭션 문제다.

그래서 서비스 애플리케이션에서 가장 흔한 정답은 Kafka transaction 자체보다 **outbox pattern**인 경우가 많다.

- 먼저 로컬 DB 트랜잭션으로 비즈니스 상태와 outbox row를 함께 저장
- 별도 relay가 outbox를 읽어 Kafka 발행
- 다운스트림은 event id 기준 멱등 처리

이 구조가 더 현실적인 이유는, DB와 Kafka를 2PC처럼 묶기보다 **경계를 명확히 나누고 재처리 가능한 흐름**으로 만들기 때문이다.

### transaction을 고려할 만한 경우

- Kafka Streams/Flink 같은 스트림 처리 경로
- consume-process-produce가 대부분 Kafka 내부에서 닫히는 구조
- 중간 중복보다 원자적 파이프라인이 훨씬 중요한 경우
- 운영팀이 transaction abort, fencing, producer recovery를 이해하고 다룰 수 있는 경우

### transaction 도입 시 주의점

- `transactional.id`를 안정적으로 관리해야 한다
- 동일한 `transactional.id`를 가진 중복 인스턴스는 fencing될 수 있다
- abort가 잦아지면 지연과 운영 복잡도가 급격히 오른다
- consumer도 `isolation.level=read_committed`를 써야 transaction 효과를 온전히 본다

즉 transaction은 강력한 기능이지만, **“중복 없는 발행”과 “외부 시스템까지 포함한 원자성”을 한 번에 해결해주는 만능 스위치가 아니다.**

---

## 실무 예시 1: 주문 생성 이벤트를 유실 없이 발행해야 하는 서비스

예를 들어 주문 서비스가 `order.created` 이벤트를 발행한다고 하자.

요구사항은 이렇다.

- 이벤트 유실은 매우 치명적이다
- 중복도 위험하지만 consumer에서 event id 기준 멱등 처리는 가능하다
- 사용자 응답 지연은 너무 길어지면 안 된다
- DB 저장과 이벤트 발행 사이 찢어진 상태를 줄여야 한다

이 경우 Producer만으로 문제를 다 해결하려 하면 한계가 있다.

### 권장 구조

1. 주문 DB transaction 안에서 주문 row와 outbox row를 함께 기록
2. outbox relay가 Kafka Producer로 발행
3. Producer는 `acks=all`, `enable.idempotence=true` 사용
4. consumer는 `event_id` 또는 `order_id + event_type + version` 기준 멱등 처리

### Producer 예시

```java
Properties props = new Properties();
props.put("bootstrap.servers", "kafka-1:9092,kafka-2:9092,kafka-3:9092");
props.put("key.serializer", "org.apache.kafka.common.serialization.StringSerializer");
props.put("value.serializer", "io.confluent.kafka.serializers.KafkaAvroSerializer");
props.put("acks", "all");
props.put("enable.idempotence", "true");
props.put("retries", Integer.toString(Integer.MAX_VALUE));
props.put("delivery.timeout.ms", "120000");
props.put("request.timeout.ms", "30000");
props.put("retry.backoff.ms", "200");
props.put("max.in.flight.requests.per.connection", "5");
props.put("compression.type", "lz4");
props.put("linger.ms", "5");
props.put("batch.size", Integer.toString(64 * 1024));
```

이 설정의 의미는 이렇다.

- 응답은 최소 ISR에 기록된 뒤에만 성공으로 본다
- 일시 장애엔 충분히 재시도한다
- 재시도 중복은 idempotence로 줄인다
- 아주 큰 지연은 피하면서 짧은 batching 효율은 챙긴다

핵심은 Producer를 잘 설정하는 것보다, **DB와 Kafka 사이를 outbox로 끊어낸 구조적 판단**이다.

---

## 실무 예시 2: 고QPS 분석 이벤트 파이프라인에서 처리량을 극대화해야 하는 경우

이번에는 클릭/노출 이벤트처럼 유실이 약간 허용되지만 처리량이 매우 큰 토픽을 보자.

요구사항:

- 초당 수십만 건
- 약간의 지연 증가는 허용 가능
- 일부 손실은 매우 제한적으로 허용 가능하지만 중복 폭증은 싫다
- 네트워크 비용이 커서 압축 효율이 중요하다

이 경우는 주문 이벤트와 판단이 달라질 수 있다.

### 고려 포인트

- `linger.ms`를 더 주어 batch 효율 극대화
- `compression.type=zstd` 또는 `lz4` 검토
- key 전략을 통해 파티션 분산 확보
- 이벤트 loss budget이 명확하다면 일부 토픽은 덜 엄격한 durability도 검토 가능

하지만 여기서도 무조건 `acks=1`로 내리는 것은 조심해야 한다.

왜냐하면 큰 트래픽 파이프라인일수록 장애 순간 손실량이 한 번에 커지기 때문이다.

즉 high-throughput 토픽이라고 해서 안전성을 자동으로 포기하는 것이 아니라,

- 정말 손실 예산이 있는지
- 다운스트림 집계에서 보정 가능한지
- 브로커 네트워크/디스크가 진짜 병목인지

를 먼저 봐야 한다.

실무에서는 이런 토픽도 `acks=all + idempotence`를 유지한 채, batching/compression 쪽을 조정해 해결하는 경우가 꽤 많다.

---

## 트레이드오프: 무엇을 얻고 무엇을 포기하는가

Kafka Producer 튜닝은 결국 명확한 트레이드오프 선택이다.

### 1) `acks=all` vs `acks=1`

- `acks=all`
  - 장점: 더 강한 내구성
  - 단점: follower 지연, ISR 축소 영향으로 latency/가용성 비용 증가
- `acks=1`
  - 장점: 더 낮은 지연
  - 단점: 리더 장애 타이밍 손실 위험

### 2) 작은 `linger.ms` vs 큰 `linger.ms`

- 작게 두면 즉시성은 좋다
- 크게 두면 throughput/압축 효율은 좋다
- 대신 저QPS 토픽의 tail latency가 악화될 수 있다

### 3) idempotence 사용 vs 미사용

- 사용하면 재시도 중복을 크게 줄일 수 있다
- 미사용하면 설정 자유도는 약간 넓을 수 있지만 운영 사고 비용이 커진다
- 대부분의 비즈니스 이벤트는 사용 쪽이 낫다

### 4) transaction 사용 vs outbox 중심 설계

- transaction은 Kafka 내부 파이프라인 원자화에 강하다
- outbox는 DB와 Kafka 사이 경계 관리에 강하다
- 서비스 애플리케이션에서는 outbox가 더 현실적이고, stream processing 경로에서는 transaction이 유리할 수 있다

핵심은 “최고 설정”이 하나 있는 것이 아니라, **도메인별 실패 비용이 다른 만큼 기준도 달라져야 한다**는 점이다.

---

## 흔한 실수: Producer를 잘못 다루면 장애가 조용히 커진다

### 실수 1) `acks=all`만 켜고 `min.insync.replicas`는 보지 않는다

이 경우 기대한 내구성이 나오지 않을 수 있다. Producer 설정은 토픽/브로커 정책과 세트다.

### 실수 2) idempotence가 비즈니스 중복까지 막아준다고 믿는다

막아주는 것은 같은 producer session의 재시도 중복에 가깝다. 주문 API 이중 호출까지 해결하지는 않는다.

### 실수 3) `retries`를 키워놓고 상위 request timeout과 맞추지 않는다

클라이언트는 실패로 봤는데 서버 내부에서는 뒤늦게 publish가 성공해 중복 재요청 사고가 날 수 있다.

### 실수 4) `linger.ms`를 무조건 0으로 둔다

낮은 지연만 보고 batching 효율을 포기하면 broker/network 비용이 불필요하게 커질 수 있다.

### 실수 5) transaction을 만능 exactly-once 스위치로 착각한다

외부 DB와 Kafka를 함께 묶는 문제는 여전히 남는다. 경계가 어디까지인지 명확히 이해해야 한다.

### 실수 6) 순서가 중요한 토픽인데 key 전략과 in-flight 설정을 가볍게 본다

Kafka의 순서는 전체 토픽 순서가 아니라 **같은 파티션 안에서의 순서**다. key 설계가 곧 순서 모델이다.

### 실수 7) 성능 튜닝을 producer 단독으로만 본다

compression, batch, request rate는 broker disk flush, network, consumer CPU와 함께 봐야 한다. Producer만 빠르면 전체 시스템이 빨라지는 것이 아니다.

---

## 운영 체크리스트: 실전에선 무엇부터 확인할까

아래 체크리스트는 Producer 설정 리뷰 때 거의 항상 유효하다.

### 내구성

- 이 토픽은 손실 허용이 가능한가, 불가능한가?
- `acks`와 topic `min.insync.replicas`가 의도와 맞는가?
- replication factor가 최소 3인가?
- ISR 축소 시 write failure를 받아들일 준비가 되어 있는가?

### 중복/순서

- `enable.idempotence=true`를 기본으로 두는가?
- `max.in.flight.requests.per.connection`이 순서 요구사항과 맞는가?
- 비즈니스 idempotency key가 따로 있는가?
- consumer가 event id 기준 멱등 처리를 할 수 있는가?

### 지연/처리량

- `linger.ms`가 실제 traffic pattern에 맞는가?
- `batch.size`가 너무 작거나 과하게 크지 않은가?
- compression 알고리즘이 네트워크/CPU 병목 구조와 맞는가?
- low-QPS 토픽과 high-QPS 토픽을 같은 기준으로 튜닝하고 있지 않은가?

### 실패 복원력

- `delivery.timeout.ms`와 상위 서비스 timeout이 정렬되어 있는가?
- retry backoff가 너무 공격적이지 않은가?
- 브로커 장애, leader election, throttling 시 metric과 alert가 있는가?

### 아키텍처 경계

- DB + Kafka 원자성이 필요한가?
- 그렇다면 transaction보다 outbox가 더 현실적인가?
- stream processing 파이프라인이라면 transaction + read_committed가 필요한가?

---

## 한 줄 정리

**Kafka Producer 실전의 핵심은 옵션 암기가 아니라, 내구성·순서·중복·처리량의 계약을 먼저 정하고 `acks`, idempotence, retry, batching, transaction을 그 계약에 맞게 조합하는 것이다.**
