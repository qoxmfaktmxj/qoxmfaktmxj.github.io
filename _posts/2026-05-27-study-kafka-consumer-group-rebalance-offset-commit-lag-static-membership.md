---
layout: post
title: "Kafka Consumer Group 실전: Rebalance, Offset Commit, Lag, Static Membership로 컨슈머를 안정적으로 운영하는 법"
date: 2026-05-27 11:50:00 +0900
categories: [data-infra]
tags: [study, data-infra, kafka, consumer-group, rebalance, offset-commit, lag, static-membership, cooperative-sticky, operations]
permalink: /data-infra/2026/05/27/study-kafka-consumer-group-rebalance-offset-commit-lag-static-membership.html
---

## 배경: Kafka Consumer는 메시지를 읽는 코드가 아니라 운영 계약이다

Kafka를 처음 붙일 때 Consumer 코드는 아주 단순해 보인다.

- 토픽을 subscribe 한다
- `poll()`로 레코드를 가져온다
- 비즈니스 로직을 실행한다
- offset을 commit 한다
- lag를 모니터링한다

여기까지만 보면 Consumer는 큐에서 메시지를 꺼내 처리하는 클라이언트처럼 느껴진다. 하지만 실제 운영 장애를 보면 Consumer 쪽 문제는 생각보다 깊다.

- 배포할 때마다 리밸런싱이 길어져 처리량이 몇 분씩 0이 된다
- consumer instance는 살아 있는데 `max.poll.interval.ms`를 넘겨 group에서 쫓겨난다
- auto commit을 켜 둔 탓에 처리 실패 메시지가 이미 commit 되어 유실처럼 보인다
- 반대로 commit을 늦게 해서 장애 복구 후 같은 주문을 여러 번 처리한다
- lag가 늘었는데 원인이 처리 속도인지, 파티션 skew인지, downstream DB 병목인지 구분이 안 된다
- 컨슈머 수를 늘렸는데 partition 수보다 많아 일부 인스턴스는 놀고 있다
- retry를 토픽 안에서 막 하다가 head-of-line blocking으로 정상 메시지까지 밀린다
- rolling deploy만 했는데 전체 group이 stop-the-world처럼 멈춘다

이런 문제는 단순히 옵션 몇 개를 늘리면 끝나지 않는다.

실무에서 Kafka Consumer Group의 본질은 더 정확히 이렇다.

> **Kafka Consumer Group은 토픽 파티션을 여러 프로세스에 배분하고, 처리 진행 위치를 저장하며, 장애·배포·확장 순간에도 중복과 유실의 경계를 선택하는 분산 실행 계약이다.**

이 관점이 중요하다.

Consumer 운영은 단순 읽기 성능 문제가 아니라 아래를 동시에 다루는 일이다.

- partition ownership을 누가 갖는가
- consumer가 죽었다고 언제 판단할 것인가
- 처리 완료와 offset commit 사이의 순서를 어떻게 둘 것인가
- retry, DLQ, pause, backpressure를 어디에 둘 것인가
- lag를 어떤 지표로 해석할 것인가
- 배포와 scale-out이 처리 중 메시지에 어떤 영향을 주는가

오늘 글은 Kafka Consumer 입문서가 아니다. 중급 이상 개발자가 실제 운영에서 아래 질문에 답할 수 있도록 Consumer Group을 구조적으로 정리한다.

1. Consumer Group과 partition assignment는 어떤 책임 분배 모델인가
2. Rebalance는 왜 발생하고, 왜 처리량을 갑자기 0으로 만들 수 있는가
3. `session.timeout.ms`, `heartbeat.interval.ms`, `max.poll.interval.ms`는 서로 무엇이 다른가
4. Offset commit은 언제 유실을 만들고 언제 중복을 만드는가
5. Cooperative Sticky Assignor와 Static Membership은 어떤 종류의 배포 장애를 줄여주는가
6. Lag는 단순 밀린 메시지 수가 아니라 어떤 운영 신호로 읽어야 하는가
7. retry, DLQ, backpressure, idempotency를 어떻게 묶어야 안전한가

결론부터 먼저 말하면 이렇다.

**Kafka Consumer 운영의 핵심은 “빨리 읽기”가 아니라, partition ownership과 offset commit을 비즈니스 처리 완료 기준에 맞춰 일관되게 설계하는 것이다.**

이걸 놓치면 Consumer는 평소에는 멀쩡하다가 배포, 장애, 트래픽 피크, downstream 지연 같은 순간에 갑자기 메시지를 잃거나, 중복 처리하거나, group 전체가 멈춘다.

---

## 먼저 큰 그림: Consumer Group은 파티션을 나눠 갖는 실행 클러스터다

Kafka 토픽은 partition으로 나뉜다. Consumer Group은 같은 `group.id`를 가진 consumer들이 그 partition들을 나눠 처리하는 구조다.

핵심 규칙은 단순하다.

- 하나의 partition은 같은 group 안에서 동시에 하나의 consumer만 처리한다
- 하나의 consumer는 여러 partition을 맡을 수 있다
- consumer 수가 partition 수보다 많으면 남는 consumer는 놀 수 있다
- 다른 group은 같은 토픽을 독립적으로 다시 읽을 수 있다

예를 들어 `orders` 토픽이 partition 6개이고, `billing-consumer` group에 consumer 3개가 있다면 보통 각 consumer가 partition 2개씩 맡는다.

```text
orders-0 -> consumer-A
orders-1 -> consumer-A
orders-2 -> consumer-B
orders-3 -> consumer-B
orders-4 -> consumer-C
orders-5 -> consumer-C
```

여기서 consumer 하나가 죽으면 어떻게 될까?

```text
orders-0 -> consumer-A
orders-1 -> consumer-A
orders-2 -> consumer-B
orders-3 -> consumer-B
orders-4 -> consumer-B
orders-5 -> consumer-A
```

이처럼 group 안에서 partition ownership을 다시 나누는 과정이 rebalance다.

### Consumer Group이 주는 장점

Consumer Group은 운영적으로 아주 강력하다.

- 처리량을 consumer 수로 수평 확장할 수 있다
- consumer 장애 시 다른 consumer가 partition을 이어받을 수 있다
- group별로 독립적인 offset을 유지할 수 있다
- 같은 토픽을 여러 서비스가 각자 다른 목적에 맞게 소비할 수 있다

하지만 대가도 있다.

- partition 수가 확장성의 상한이 된다
- rebalance 중에는 partition ownership이 흔들린다
- offset commit 기준을 잘못 잡으면 중복이나 유실이 발생한다
- 특정 partition에 메시지가 몰리면 consumer 수를 늘려도 해결되지 않는다
- 처리 시간이 길면 group membership 자체가 불안정해진다

즉 Consumer Group은 “자동 분산 처리”가 아니라 **partition 단위 작업 소유권을 조정하는 프로토콜**이다.

이걸 작업 큐처럼만 보면 위험하다. 일반적인 작업 큐에서는 워커가 메시지 하나를 가져가 ack한다. Kafka에서는 partition 순서와 offset이 중심이다. 메시지 하나하나의 ack가 아니라, partition별 읽기 위치를 앞으로 움직이는 방식이다.

---

## 핵심 개념 1: Partition은 병렬성 단위이면서 순서 보장 단위다

Kafka에서 partition은 두 가지 의미를 동시에 가진다.

### 1) 병렬 처리 단위

Consumer Group 안에서 partition은 작업을 나누는 최소 단위다. 한 partition을 같은 group의 두 consumer가 동시에 처리하지 않는다.

따라서 최대 병렬성은 기본적으로 partition 수에 묶인다.

```text
partition 3개, consumer 10개
=> 동시에 실제 처리 가능한 consumer는 최대 3개
```

물론 consumer 내부에서 thread pool로 레코드 처리를 더 병렬화할 수는 있다. 하지만 이 경우 offset commit, partition ordering, 실패 복구가 훨씬 어려워진다. 그래서 Consumer scaling의 기본 단위는 여전히 partition이다.

### 2) 순서 보장 단위

Kafka는 같은 partition 안의 offset 순서를 보장한다. 반대로 서로 다른 partition 사이의 전역 순서는 보장하지 않는다.

이 말은 곧 key 설계가 중요하다는 뜻이다.

- 같은 주문의 상태 변경은 같은 partition으로 가야 순서를 유지할 수 있다
- 같은 사용자 잔액 변경은 같은 key를 써야 순서를 유지할 수 있다
- 전체 토픽 전역 순서를 기대하면 partition을 늘리는 순간 전제가 깨진다

예를 들어 주문 이벤트에서 key를 `orderId`로 잡으면 같은 주문의 이벤트는 보통 같은 partition에 들어간다.

```text
order-1 created -> orders-2 offset 10
order-1 paid    -> orders-2 offset 18
order-1 shipped -> orders-2 offset 32
```

Consumer는 partition 안에서는 이 순서를 유지하며 처리할 수 있다.

하지만 key를 랜덤하게 잡거나 round-robin으로 보내면 같은 주문 이벤트가 여러 partition에 흩어진다. 이 경우 Consumer Group은 아무리 잘 운영해도 비즈니스 순서를 보장할 수 없다.

### 운영 기준

Partition 설계는 Producer 단계에서 끝나는 것처럼 보이지만 Consumer 운영에 직접 영향을 준다.

- 처리 병렬성을 높이고 싶으면 partition 수가 충분해야 한다
- 같은 key 순서가 중요하면 key 분포가 안정적이어야 한다
- 특정 key가 너무 hot하면 partition 하나가 병목이 된다
- partition 수를 늘리면 미래 메시지 분포는 바뀔 수 있지만 기존 메시지는 이동하지 않는다

Consumer lag가 특정 partition에만 몰린다면 consumer 수를 늘리는 것보다 key skew와 partition 분포를 먼저 봐야 한다.

---

## 핵심 개념 2: Rebalance는 장애 복구 기능이지만, 동시에 장애 증폭 지점이다

Rebalance는 Consumer Group 운영에서 가장 중요하고 가장 자주 오해되는 개념이다.

Rebalance가 일어나는 대표 상황은 다음과 같다.

- consumer 인스턴스가 새로 group에 join 한다
- consumer가 종료되거나 heartbeat를 보내지 못한다
- topic partition 수가 바뀐다
- subscription 대상 토픽이 바뀐다
- `max.poll.interval.ms`를 넘겨 consumer가 느린 것으로 판단된다
- group coordinator가 바뀌거나 broker 장애가 발생한다

Rebalance 자체는 필요한 기능이다. consumer가 죽었는데 partition을 영원히 붙잡고 있으면 안 되기 때문이다. 문제는 rebalance 방식에 따라 처리 중단 시간이 커질 수 있다는 점이다.

### Stop-the-world에 가까운 rebalance

전통적인 eager rebalance에서는 group 구성 변화가 생기면 모든 consumer가 일단 partition을 revoke한다. 이후 coordinator가 새 assignment를 계산하고 다시 assign한다.

흐름은 대략 이렇다.

```text
1. consumer-C가 새로 join
2. group 전체 rebalance 시작
3. consumer-A, B가 기존 partition revoke
4. assignment 재계산
5. consumer-A, B, C가 새 partition assign
6. 처리 재개
```

이때 문제가 생긴다.

- 실제로 이동할 partition이 일부뿐이어도 전체 consumer가 멈출 수 있다
- 처리 중이던 batch를 정리하고 commit해야 한다
- downstream 호출이 길면 revoke 처리가 지연된다
- rolling deploy 때 인스턴스 하나씩 바꿔도 매번 group 전체가 흔들린다

그래서 운영자는 “consumer를 하나 추가했을 뿐인데 lag가 갑자기 치솟는” 장면을 보게 된다.

### Rebalance가 장애를 증폭하는 패턴

가장 흔한 패턴은 다음이다.

1. downstream DB가 느려진다
2. consumer 처리 시간이 길어진다
3. `poll()` 호출 간격이 벌어진다
4. `max.poll.interval.ms`를 넘긴 consumer가 group에서 제외된다
5. rebalance가 발생한다
6. 다른 consumer가 partition을 이어받지만 downstream은 여전히 느리다
7. group 전체가 계속 흔들리고 lag가 더 커진다

즉 rebalance는 원인이 아니라 결과일 수 있다. 하지만 결과로 발생한 rebalance가 다시 처리량을 떨어뜨려 장애를 증폭한다.

그래서 Consumer 장애를 볼 때는 “왜 rebalance가 났나”만 보지 말고 아래를 같이 봐야 한다.

- 처리 시간이 늘어난 원인이 무엇인가
- `poll()` loop가 막히는 구조인가
- batch 크기가 너무 큰가
- downstream timeout이 너무 긴가
- consumer가 종료 시 partition revoke를 제대로 처리하는가
- 배포 전략이 group을 계속 흔드는가

---

## 핵심 개념 3: Heartbeat, Session Timeout, Max Poll Interval은 서로 다른 실패 감지 장치다

Kafka Consumer 설정에서 자주 헷갈리는 세 가지가 있다.

- `heartbeat.interval.ms`
- `session.timeout.ms`
- `max.poll.interval.ms`

이 값들은 모두 “consumer가 살아 있는가”와 관련 있지만 의미가 다르다.

### `heartbeat.interval.ms`: group coordinator에게 보내는 생존 신호 주기

Consumer는 group coordinator에게 주기적으로 heartbeat를 보낸다. heartbeat는 “나 아직 group member로 살아 있다”는 신호다.

일반적으로 `heartbeat.interval.ms`는 `session.timeout.ms`보다 훨씬 작게 잡는다.

예를 들어:

```properties
heartbeat.interval.ms=3000
session.timeout.ms=10000
```

이 경우 3초마다 heartbeat를 보내고, 10초 동안 heartbeat가 없으면 coordinator는 consumer가 죽었다고 판단할 수 있다.

### `session.timeout.ms`: heartbeat가 끊겼다고 판단하는 시간

`session.timeout.ms`는 consumer 프로세스 장애, 네트워크 단절, stop-the-world GC, node 장애 등을 감지하는 기준이다.

너무 짧으면:

- 일시적인 GC pause나 네트워크 흔들림에도 rebalance가 잦아진다
- group이 민감하게 흔들린다

너무 길면:

- 진짜 죽은 consumer의 partition 인계가 늦어진다
- 장애 복구 시간이 길어진다

따라서 session timeout은 장애 감지 속도와 false positive 사이의 trade-off다.

### `max.poll.interval.ms`: 애플리케이션이 계속 처리 루프를 돌고 있는지 보는 시간

`max.poll.interval.ms`는 heartbeat와 다른 문제를 잡는다.

Consumer 프로세스는 살아 있고 heartbeat thread도 동작하지만, 애플리케이션 처리 로직이 너무 오래 걸려 다음 `poll()`을 호출하지 못할 수 있다.

예를 들어:

```text
poll()로 500건을 가져옴
각 레코드 처리에서 외부 API 호출
일부 API가 30초씩 지연
전체 batch 처리에 8분 소요
max.poll.interval.ms=5분
=> consumer는 살아 있지만 group에서 제외될 수 있음
```

이 설정은 “살아 있음”이 아니라 **처리 loop가 정상적으로 진행되는가**를 본다.

### 세 설정을 같이 이해해야 하는 이유

실무에서 자주 나오는 잘못된 해결책이 있다.

> `max.poll.interval.ms` 에러가 나니까 값을 크게 늘리자.

물론 임시 완화는 될 수 있다. 하지만 근본 원인이 batch 처리 시간, downstream timeout, thread pool 포화라면 timeout만 늘리는 것은 문제를 늦게 발견하게 만들 뿐이다.

운영 기준은 이렇게 잡는 편이 낫다.

- `session.timeout.ms`: 프로세스/네트워크 장애 감지 기준
- `heartbeat.interval.ms`: session timeout보다 충분히 짧게
- `max.poll.interval.ms`: 최악의 정상 batch 처리 시간을 반영하되, 무한히 키우지 않기
- `max.poll.records`: 한 번에 가져오는 처리량을 제어해 poll loop 시간을 제한
- downstream timeout: `max.poll.interval.ms` 안에 들어오도록 상한 설계

즉 Consumer 안정성은 Kafka 설정 하나가 아니라 **poll loop 시간 예산**으로 봐야 한다.

---

## 핵심 개념 4: Offset Commit은 처리 완료가 아니라 “여기까지 다시 읽지 않겠다”는 선언이다

Consumer 운영에서 가장 중요한 문장 하나를 꼽으라면 이것이다.

> **Offset commit은 메시지를 처리했다는 사실의 저장이 아니라, 장애 복구 시 이 offset 이전은 다시 읽지 않겠다는 선언이다.**

이 차이를 이해해야 유실과 중복의 경계를 잡을 수 있다.

### Kafka offset의 의미

각 partition은 offset이 증가하는 로그다.

```text
orders-0 offset 100
orders-0 offset 101
orders-0 offset 102
```

Consumer가 offset 102까지 처리했다면 보통 commit할 값은 “다음에 읽을 offset”인 103이다.

```text
committed offset = 103
=> 장애 복구 후 103부터 읽음
```

즉 commit된 offset 자체는 마지막 처리 offset이 아니라 다음 시작 위치다.

### Auto Commit의 위험

`enable.auto.commit=true`를 켜면 Consumer가 주기적으로 offset을 자동 commit한다.

간단한 데모나 유실이 크게 중요하지 않은 로그성 처리에는 편할 수 있다. 하지만 비즈니스 이벤트 처리에서는 조심해야 한다.

문제는 auto commit이 **비즈니스 처리 완료와 정확히 묶이지 않는다**는 점이다.

예를 들어:

```text
1. poll()로 offset 100~199를 가져옴
2. auto commit이 offset 200을 먼저 저장
3. offset 150 처리 중 DB 오류 발생
4. consumer 재시작
5. committed offset 200부터 시작
6. offset 150~199는 다시 읽지 않음
```

이 경우 메시지는 Kafka에는 있었지만 Consumer 관점에서는 사실상 유실처럼 보인다.

정확히는 Kafka가 메시지를 잃은 것이 아니다. Consumer가 “200 이전은 다 처리했다”고 선언해버린 것이다.

### Manual Commit의 기본 원칙

비즈니스 처리에서는 보통 manual commit을 쓴다.

```properties
enable.auto.commit=false
```

그리고 처리 성공 이후 commit한다.

흐름은 이렇게 잡는다.

```text
1. poll()
2. 레코드 처리
3. 외부 DB/ API / 파일 쓰기 성공 확인
4. offset commit
```

이렇게 하면 처리 성공 전 장애가 나도 offset이 앞으로 가지 않으므로 메시지를 다시 읽을 수 있다. 대신 중복 처리는 발생할 수 있다.

즉 manual commit의 기본 모델은 대개 **at-least-once**다.

- 처리 성공 후 commit 전에 죽으면 다시 처리된다
- 처리 중 실패하면 다시 처리된다
- 따라서 downstream은 idempotent해야 한다

### Commit Sync와 Commit Async

Kafka Consumer에는 보통 동기 commit과 비동기 commit이 있다.

- `commitSync()`: commit 완료를 기다림
- `commitAsync()`: callback 기반, 처리량에 유리하지만 실패 처리 주의 필요

`commitSync()`는 단순하고 안전하지만 latency가 늘 수 있다. 특히 매 레코드마다 sync commit하면 처리량이 급격히 낮아진다.

`commitAsync()`는 빠르지만 이전 commit 실패와 이후 commit 성공이 섞일 수 있다. 순서를 잘못 다루면 오래된 offset으로 되돌아가는 문제를 만들 수 있다.

실무 기본값은 보통 다음 중 하나다.

1. batch 단위 처리 후 `commitSync()`
2. 평소에는 `commitAsync()`, 종료/revoke 시 `commitSync()`
3. partition별 처리 완료 offset을 추적하고 안전한 offset만 주기적으로 commit

중요한 것은 commit API 선택보다 **처리 완료 기준과 commit 기준이 일치하는가**다.

---

## 핵심 개념 5: At-least-once는 쉬워 보이지만 idempotency 없이는 안전하지 않다

Kafka Consumer에서 가장 현실적인 기본 모델은 at-least-once다.

의미는 이렇다.

- 메시지를 잃지 않기 위해 처리 성공 후 offset을 commit한다
- 장애 시 같은 메시지가 다시 처리될 수 있다
- 따라서 downstream write는 중복을 견뎌야 한다

문제는 많은 팀이 “중복이 가끔 있을 수 있다”를 말로만 알고, 실제 비즈니스 로직에는 반영하지 않는다는 것이다.

### 중복이 사고가 되는 사례

예를 들어 결제 완료 이벤트를 처리한다고 하자.

```text
offset 501: payment-completed(order-123, amount=30000)
```

Consumer가 이 이벤트를 읽고 아래 작업을 한다.

1. 주문 상태를 PAID로 변경
2. 포인트 적립
3. 알림 발송
4. offset commit

만약 3번까지 성공하고 4번 commit 전에 consumer가 죽으면 어떻게 될까?

재시작 후 같은 offset 501을 다시 읽는다.

이때 idempotency가 없으면:

- 포인트가 두 번 적립된다
- 알림이 두 번 발송된다
- 감사 로그가 중복된다
- downstream 외부 API가 중복 호출된다

Kafka 관점에서는 정상적인 at-least-once 동작이다. 문제는 비즈니스 side effect가 중복을 견디지 못한 것이다.

### Idempotency의 실무 패턴

중복 처리를 막는 기본 패턴은 다음이다.

#### 1) 이벤트 고유 ID 저장

처리한 이벤트 ID를 DB에 저장하고, 이미 처리한 이벤트면 skip한다.

```sql
CREATE TABLE processed_events (
  consumer_name text NOT NULL,
  event_id text NOT NULL,
  processed_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (consumer_name, event_id)
);
```

처리 시:

```text
1. transaction 시작
2. processed_events insert 시도
3. 이미 있으면 중복으로 판단하고 종료
4. 비즈니스 write 수행
5. transaction commit
6. offset commit
```

이 방식은 간단하지만 event id가 안정적으로 있어야 한다.

#### 2) 비즈니스 상태 전이를 멱등하게 만들기

예를 들어 주문 상태 변경은 아래처럼 설계할 수 있다.

```sql
UPDATE orders
SET status = 'PAID', paid_at = :paid_at
WHERE order_id = :order_id
  AND status <> 'PAID';
```

이미 PAID라면 다시 처리해도 추가 side effect가 없도록 만든다.

#### 3) Outbox/Inbox 패턴 사용

마이크로서비스 간 이벤트 처리에서는 inbox 테이블을 두어 “이 consumer가 이 event를 처리했다”는 사실과 비즈니스 상태 변경을 같은 DB transaction으로 묶는다.

```text
Kafka read
  -> DB transaction
       -> inbox insert
       -> domain update
       -> side effect 예약
     commit
  -> offset commit
```

이렇게 하면 Kafka offset commit과 DB write 사이를 완전히 원자적으로 묶지는 못해도, 재처리 시 DB 쪽에서 중복을 흡수할 수 있다.

### Exactly-once에 대한 현실적인 경계

Kafka는 transaction과 idempotent producer를 통해 특정 경계 안에서 exactly-once semantics를 제공할 수 있다. 특히 Kafka Streams나 consume-process-produce 파이프라인에서는 강력하다.

하지만 Consumer가 외부 DB, REST API, 이메일, 결제 API 같은 시스템에 side effect를 내는 순간 이야기가 달라진다.

- Kafka transaction은 외부 DB commit을 자동으로 묶어주지 않는다
- 이메일 발송은 rollback할 수 없다
- 결제 API는 같은 요청을 두 번 보내면 진짜로 두 번 처리될 수 있다
- DB와 Kafka offset commit은 기본적으로 다른 transaction manager다

그래서 일반 애플리케이션 Consumer의 안전성은 보통 “Kafka exactly-once를 켰는가”보다 **외부 side effect가 idempotent한가**에 달려 있다.

---

## 핵심 개념 6: Rebalance 중 commit과 revoke 처리를 설계하지 않으면 중복 폭이 커진다

Consumer가 partition을 잃는 순간을 가볍게 보면 안 된다. Rebalance가 발생하면 기존 consumer가 맡던 partition을 다른 consumer가 이어받는다. 이때 처리 중이던 레코드와 offset commit 상태가 어긋날 수 있다.

Kafka Consumer에는 보통 rebalance listener를 등록해 partition revoke/assign 시점을 다룬다.

개념적으로는 다음 흐름이다.

```java
consumer.subscribe(List.of("orders"), new ConsumerRebalanceListener() {
    public void onPartitionsRevoked(Collection<TopicPartition> partitions) {
        // 이 consumer가 partition 소유권을 잃기 직전
        // 처리 완료된 offset을 commit하고, in-flight 작업을 정리한다
    }

    public void onPartitionsAssigned(Collection<TopicPartition> partitions) {
        // 새 partition을 맡은 직후
        // 필요한 local state를 초기화하거나 seek 위치를 확인한다
    }
});
```

### Revoke 시점에 해야 할 일

운영적으로 중요한 것은 `onPartitionsRevoked`다.

여기서 해야 하는 일은 보통 다음이다.

- 해당 partition의 in-flight 처리를 중단하거나 완료 대기한다
- 처리 완료된 offset만 계산한다
- 가능하면 sync commit으로 안전하게 저장한다
- local buffer나 batch 상태를 정리한다
- 더 이상 해당 partition의 결과를 commit하지 않도록 막는다

이 처리가 없으면 어떤 일이 생길까?

```text
1. consumer-A가 orders-0 offset 100~150 처리 중
2. rebalance 발생
3. orders-0이 consumer-B로 이동
4. consumer-A의 오래 걸리던 작업이 뒤늦게 성공
5. consumer-A가 예전 partition offset을 commit하거나 side effect를 낸다
6. consumer-B도 같은 구간을 처리한다
```

결과적으로 중복 폭이 커지고, 심하면 partition ownership이 없는 consumer가 늦은 commit을 시도하는 이상한 상황이 된다.

### Thread pool 처리 시 더 조심해야 한다

Consumer poll loop에서 레코드를 thread pool에 던지고 바로 다음 poll을 도는 구조는 처리량을 높일 수 있다. 하지만 offset commit은 어려워진다.

특히 partition 안의 offset 순서를 유지해야 한다.

예를 들어 partition `orders-0`에서 offset 10, 11, 12를 병렬 처리한다고 하자.

```text
offset 10 처리 중
offset 11 성공
offset 12 성공
offset 10 실패
```

이때 13을 commit하면 offset 10은 다시 읽지 않는다. 따라서 partition별로 “연속적으로 성공한 가장 큰 offset”만 commit해야 한다.

안전한 commit 기준은 다음에 가깝다.

```text
commit 가능한 offset = partition별로 앞에서부터 연속 성공한 마지막 offset + 1
```

병렬 처리를 하려면 이 offset tracking을 직접 해야 한다. 그게 부담스럽다면 partition 단위 순차 처리나 작은 batch 처리로 시작하는 편이 더 안전하다.

---

## 핵심 개념 7: Cooperative Sticky Assignor는 리밸런싱의 충격을 줄인다

전통적인 eager rebalance는 group 전체가 partition을 모두 내려놓고 다시 받는 방식에 가깝다. 이 방식은 단순하지만 rolling deploy나 scale-out 때 충격이 크다.

이를 완화하기 위해 Kafka에는 cooperative rebalance 방식이 있다. 대표적으로 `CooperativeStickyAssignor`를 사용할 수 있다.

```properties
partition.assignment.strategy=org.apache.kafka.clients.consumer.CooperativeStickyAssignor
```

### Cooperative 방식의 핵심

Cooperative rebalance는 가능한 한 기존 assignment를 유지하고, 실제로 이동해야 하는 partition만 단계적으로 revoke한다.

장점은 분명하다.

- 모든 consumer가 한 번에 멈추는 상황을 줄인다
- 이동하지 않는 partition은 계속 처리할 수 있다
- rolling deploy 중 lag spike를 완화할 수 있다
- assignment가 덜 흔들려 local cache나 state 유지에 유리하다

하지만 오해하면 안 된다.

Cooperative가 rebalance를 없애는 것은 아니다. rebalance의 범위와 충격을 줄이는 것이다.

### Sticky의 의미

Sticky assignor는 가능한 한 기존 partition 배정을 유지하려고 한다. 예를 들어 consumer-A가 `orders-0`, `orders-1`을 맡고 있었다면, group 변화 후에도 가능하면 계속 맡게 한다.

이게 중요한 이유는 다음 때문이다.

- consumer local cache가 따뜻하게 유지된다
- partition별 connection이나 state를 재사용할 수 있다
- assignment 변경으로 생기는 commit/revoke 작업이 줄어든다
- stateful consumer에서 복구 비용이 줄어든다

### 도입 시 주의점

Cooperative assignor로 바꿀 때는 rolling upgrade 호환성을 확인해야 한다. 모든 consumer가 같은 assignor 전략을 호환 가능한 방식으로 사용해야 한다.

운영에서는 보통 다음 순서로 접근한다.

1. 현재 Kafka client 버전과 broker 호환성 확인
2. consumer group별 assignment strategy 확인
3. staging에서 rolling deploy 중 rebalance 시간과 lag spike 비교
4. revoke listener가 cooperative 방식에 맞게 동작하는지 확인
5. 점진적으로 production group 적용

Cooperative rebalance는 좋은 기본값이 될 수 있지만, 잘못된 commit 처리나 너무 긴 processing time을 대신 해결해주지는 않는다.

---

## 핵심 개념 8: Static Membership은 재시작을 장애로 보지 않게 만드는 장치다

Consumer rolling deploy에서 rebalance가 잦다면 Static Membership도 중요한 선택지다.

Kafka Consumer에 `group.instance.id`를 설정하면 해당 consumer instance가 group 안에서 고정된 identity를 가진다.

```properties
group.id=billing-consumer
group.instance.id=billing-consumer-3
```

### Dynamic Membership의 문제

기본적으로 consumer는 group에 join할 때마다 member id를 새로 받을 수 있다. 컨테이너가 재시작되면 coordinator 입장에서는 기존 member가 사라지고 새 member가 들어온 것처럼 보인다.

짧은 rolling restart에서도 group membership이 흔들릴 수 있다.

### Static Membership의 효과

Static Membership은 안정적인 instance identity를 제공한다. 같은 `group.instance.id`를 가진 consumer가 짧은 시간 안에 재시작해 돌아오면, group은 이를 완전히 새로운 member로 보기보다 기존 member의 복귀로 다룰 수 있다.

효과는 다음과 같다.

- 짧은 재시작 중 불필요한 rebalance를 줄인다
- partition assignment가 더 안정적으로 유지된다
- stateful consumer나 local cache consumer에 유리하다
- rolling deploy 중 lag spike가 줄 수 있다

### 주의할 점

Static Membership은 강력하지만 운영 규칙이 필요하다.

- `group.instance.id`는 group 안에서 반드시 유일해야 한다
- Kubernetes라면 StatefulSet처럼 stable identity가 있는 배포 방식과 잘 맞는다
- Deployment처럼 pod 이름이 매번 바뀌는 구조에서는 identity 관리가 까다롭다
- 같은 id를 가진 consumer 두 개가 동시에 뜨면 fencing 문제가 생길 수 있다
- 진짜 죽은 instance의 partition 회수는 session timeout 정책에 영향을 받는다

즉 Static Membership은 “재시작이 잦은 consumer를 안정화하는 도구”이지, 무조건 모든 consumer에 붙이는 마법 옵션은 아니다.

---

## 핵심 개념 9: Lag는 밀린 메시지 수가 아니라 처리 파이프라인의 증상이다

Kafka Consumer 운영에서 가장 많이 보는 지표는 lag다.

단순 정의는 쉽다.

```text
lag = log end offset - committed offset
```

하지만 운영 해석은 훨씬 복잡하다.

Lag가 늘었다는 말은 “처리가 느리다”일 수도 있지만, 구체적으로는 여러 원인이 있다.

- producer 유입량이 평소보다 늘었다
- consumer 처리 시간이 느려졌다
- downstream DB/API가 느려졌다
- 특정 partition에 key skew가 생겼다
- rebalance가 반복되어 처리 공백이 생겼다
- commit이 지연되지만 실제 처리는 되고 있다
- poison pill 메시지 하나가 partition을 막고 있다
- consumer 수가 partition 수보다 부족하다
- fetch 설정이나 batch 크기가 비효율적이다

따라서 lag는 시작점이지 결론이 아니다.

### Group lag와 Partition lag를 나눠 봐야 한다

전체 group lag만 보면 중요한 신호를 놓친다.

예를 들어 전체 lag가 100만이라고 하자.

케이스 A:

```text
orders-0 lag 166k
orders-1 lag 167k
orders-2 lag 166k
orders-3 lag 167k
orders-4 lag 167k
orders-5 lag 167k
```

전체적으로 유입량이 처리량보다 많거나 consumer 전체가 느린 상황이다.

케이스 B:

```text
orders-0 lag 950k
orders-1 lag 10k
orders-2 lag 10k
orders-3 lag 10k
orders-4 lag 10k
orders-5 lag 10k
```

이건 partition skew, 특정 key hot spot, 특정 partition poison pill 가능성을 먼저 봐야 한다. consumer 수를 단순히 늘려도 `orders-0`은 여전히 한 consumer만 처리한다.

### Lag 증가 속도를 봐야 한다

lag 절대값보다 중요한 것은 증가 속도다.

- lag가 크지만 일정하게 줄고 있다면 복구 중이다
- lag가 작지만 계속 증가하면 곧 장애가 된다
- lag가 톱니처럼 튀면 rebalance나 batch commit 주기를 의심한다
- 특정 시간대만 증가하면 upstream burst 또는 downstream batch lock을 의심한다

운영 대시보드에는 최소한 아래가 함께 있어야 한다.

- topic/group/partition별 lag
- records consumed rate
- records produced rate
- processing latency
- commit latency
- rebalance count/time
- poll interval
- downstream latency/error rate

Lag만 보면 Kafka 문제처럼 보이지만, 실제 원인은 DB connection pool 고갈인 경우가 매우 흔하다.

### Commit lag와 처리 lag가 다를 수 있다

Consumer가 레코드를 이미 처리했지만 commit을 늦게 하고 있다면 lag는 커 보일 수 있다.

반대로 auto commit이 먼저 나가면 lag는 작아 보이지만 실제 처리는 실패했을 수 있다.

그래서 중요한 서비스에서는 Kafka lag 외에 애플리케이션 내부 지표도 둔다.

- poll 받은 offset
- 처리 시작 offset
- 처리 완료 offset
- commit 완료 offset
- partition별 in-flight count
- oldest in-flight age

이 지표가 있으면 “Kafka lag가 큰데 실제 처리도 밀린 건가, commit만 늦은 건가”를 구분할 수 있다.

---

## 실무 예시 1: 주문 이벤트 Consumer의 안전한 기본 구조

주문 결제 이벤트를 처리하는 Consumer를 예로 들어보자.

요구사항은 다음이다.

- 결제 완료 이벤트를 잃으면 안 된다
- 같은 이벤트가 두 번 들어와도 주문 상태와 포인트가 중복 반영되면 안 된다
- 알림 발송은 중복 가능성이 있지만 최대한 줄여야 한다
- 장애 복구 후 다시 읽어도 안전해야 한다

### 권장 흐름

```text
1. Kafka poll
2. 레코드 검증
3. DB transaction 시작
4. inbox 테이블에 event_id insert
5. 이미 있으면 중복으로 판단하고 비즈니스 처리 skip
6. 주문 상태 변경
7. 포인트 적립 ledger insert
8. 알림 발송 요청을 outbox 테이블에 기록
9. DB transaction commit
10. offset commit
11. 별도 outbox publisher가 알림 발송
```

여기서 핵심은 외부 side effect를 Consumer 처리 transaction 안에서 직접 수행하지 않는 것이다.

알림 API를 바로 호출하면 다음 문제가 생긴다.

```text
DB 업데이트 성공
알림 발송 성공
offset commit 전 consumer crash
재처리
알림 재발송
```

Outbox로 밀어두면 알림 발송도 별도 idempotency key로 제어할 수 있다.

### Commit 단위

매 레코드마다 commit하면 안전해 보이지만 처리량이 낮다. 보통은 partition별 batch 처리 후 commit한다.

단, batch 안에서 일부 실패가 있으면 조심해야 한다.

```text
offset 100 성공
offset 101 성공
offset 102 실패
offset 103 성공
```

이 경우 104를 commit하면 102를 잃는다. 안전한 commit은 102 이전까지다.

그래서 단순 batch Consumer에서는 실패가 나면 해당 partition 처리를 멈추고, 성공한 연속 offset까지만 commit한 뒤 retry 정책으로 넘기는 편이 안전하다.

---

## 실무 예시 2: 느린 외부 API가 Consumer Group을 흔드는 경우

다음 상황을 생각해보자.

- Consumer는 이벤트를 읽고 외부 정산 API를 호출한다
- 평소 API latency는 200ms다
- 장애 시 20초까지 느려진다
- `max.poll.records=500`
- `max.poll.interval.ms=300000` यानी 5분

최악의 경우 batch 하나가 500 * 20초 = 10,000초가 된다. 물론 실제로는 병렬 호출을 하겠지만, 제한 없는 병렬 호출은 외부 API를 더 무너뜨릴 수 있다.

이때 자주 보이는 잘못된 대응은 다음이다.

```properties
max.poll.interval.ms=3600000
```

1시간으로 늘리면 group에서 쫓겨나는 문제는 줄 수 있다. 하지만 장애 감지가 늦어지고, partition ownership이 오래 묶이며, lag 복구가 더 예측 불가능해진다.

### 더 나은 접근

1. `max.poll.records`를 처리 가능한 크기로 낮춘다
2. 외부 API timeout을 명확히 둔다
3. retry는 즉시 무한 반복하지 않는다
4. 실패 이벤트는 retry topic이나 DLQ로 분리한다
5. partition별 pause/resume을 사용해 backpressure를 건다
6. downstream 장애 지표와 Consumer lag를 같이 본다

예를 들어:

```properties
max.poll.records=100
max.poll.interval.ms=300000
request.timeout.ms=30000
```

그리고 애플리케이션에서 외부 API timeout을 2~3초 수준으로 두고, 실패한 메시지는 retry topic으로 보낸다.

```text
orders.events
  -> billing-consumer
      success -> commit
      retryable failure -> billing.retry.1m topic + commit
      non-retryable failure -> billing.dlq topic + commit
```

이 구조에서는 원본 partition이 poison pill 하나 때문에 오래 막히지 않는다. 대신 retry topic 설계와 idempotency가 중요해진다.

---

## 실무 예시 3: Retry를 같은 partition 안에서 계속하면 정상 메시지도 같이 막힌다

Consumer에서 처리 실패가 났을 때 가장 단순한 코드는 이렇다.

```text
try 처리
catch 실패하면 sleep 후 다시 처리
```

처음에는 괜찮아 보인다. 하지만 Kafka partition은 순서가 있으므로 offset 하나가 계속 실패하면 뒤 메시지도 처리하지 못한다.

```text
offset 10 poison pill
offset 11 정상
offset 12 정상
offset 13 정상
```

순서 보장이 반드시 필요한 도메인이라면 offset 10을 해결하기 전 11 이후를 처리하면 안 될 수 있다. 하지만 많은 경우 실패 메시지 하나 때문에 정상 메시지 수천 개가 밀리는 것은 더 큰 장애다.

### Retry topic 패턴

운영에서는 보통 retry topic을 둔다.

```text
orders.events
orders.retry.1m
orders.retry.10m
orders.retry.1h
orders.dlq
```

처리 흐름은 다음이다.

```text
1. 원본 topic 처리 실패
2. retry 가능한 오류인지 판단
3. retry count와 next retry time을 header에 기록
4. retry topic으로 발행
5. 원본 offset은 commit
6. retry consumer가 나중에 다시 처리
7. 반복 실패 시 DLQ로 이동
```

이 방식의 장점은 원본 partition이 계속 앞으로 간다는 점이다.

단점도 있다.

- 원본 partition 순서를 깨뜨릴 수 있다
- retry topic 발행과 offset commit 사이에 또 다른 원자성 문제가 생긴다
- retry storm을 막기 위한 지연, backoff, rate limit이 필요하다
- DLQ 운영 프로세스가 없으면 메시지 무덤이 된다

### 언제 원본 partition에서 멈춰야 하나?

모든 실패를 retry topic으로 빼는 것도 위험하다.

원본 순서가 절대적으로 중요한 경우가 있다.

- 계좌 잔액 변경
- 동일 주문의 상태 전이
- 재고 차감 이벤트
- version 기반 projection

이 경우 offset 10을 건너뛰고 11을 처리하면 상태가 깨질 수 있다. 이때는 partition을 pause하고 운영 개입 또는 제한된 retry를 수행하는 편이 맞다.

기준은 다음이다.

- 순서가 비즈니스 정합성에 필수이면 partition 내 재시도 또는 pause
- 개별 이벤트 독립성이 높으면 retry topic으로 분리
- 실패 원인이 데이터 자체이면 DLQ
- 실패 원인이 일시적 downstream이면 backoff retry

---

## 실무 예시 4: Pause/Resume은 소비 중단이 아니라 partition별 backpressure 도구다

Kafka Consumer에는 특정 partition 소비를 일시 중단하는 `pause()`와 다시 시작하는 `resume()`이 있다.

이 기능은 다음 상황에서 유용하다.

- 특정 partition의 in-flight 작업이 너무 많다
- downstream API rate limit에 걸렸다
- 특정 tenant/key의 처리를 잠시 늦춰야 한다
- retry 가능한 오류가 일시적으로 발생했다
- 메모리 buffer가 상한에 도달했다

중요한 점은 pause해도 heartbeat는 계속 유지해야 한다는 것이다. 즉 consumer loop는 멈추면 안 된다.

잘못된 코드:

```text
실패 발생
Thread.sleep(10분)
다음 poll 호출 안 함
max.poll.interval.ms 초과
rebalance 발생
```

더 나은 구조:

```text
실패 발생
해당 partition pause
짧은 주기로 poll은 계속 호출
재개 시간이 되면 resume
처리 재개
```

Pause/Resume은 Consumer Group membership을 유지하면서 특정 partition 처리량을 제어하는 방법이다.

다만 이것도 남용하면 안 된다.

- 너무 오래 pause하면 lag가 계속 쌓인다
- pause 상태가 관측되지 않으면 장애인지 의도인지 모른다
- 재시작 시 pause 상태 복구 정책이 필요할 수 있다
- partition별 backpressure가 전체 SLA와 맞는지 봐야 한다

대시보드에는 pause된 partition 수와 pause duration도 지표로 두는 것이 좋다.

---

## 설정 기준: 안전한 Consumer Group 기본값을 어떻게 잡을까

정답 설정은 없다. 하지만 운영 기본값을 잡는 사고방식은 있다.

### 1) 처리 완료 후 commit

```properties
enable.auto.commit=false
```

비즈니스 이벤트라면 auto commit은 피하는 편이 안전하다. 처리 완료와 offset commit을 애플리케이션 기준으로 묶어야 한다.

### 2) 한 번에 가져올 양 제한

```properties
max.poll.records=100
```

값은 처리 시간과 record 크기에 따라 다르다. 중요한 것은 `max.poll.records * worst_case_processing_time`이 `max.poll.interval.ms` 안에 들어와야 한다는 점이다.

### 3) Heartbeat와 session timeout은 너무 공격적으로 잡지 않기

```properties
heartbeat.interval.ms=3000
session.timeout.ms=10000
```

이런 조합은 흔한 출발점이지만, GC pause, 네트워크 환경, broker 부하에 따라 조정해야 한다.

### 4) 처리 시간이 긴 Consumer는 poll loop를 분리해서 설계

긴 작업을 poll thread에서 직접 오래 수행하면 `max.poll.interval.ms` 문제가 생긴다. 하지만 무작정 thread pool로 던지면 offset tracking이 어려워진다.

중간 지점은 다음이다.

- partition별 worker queue를 둔다
- partition 순서를 유지한다
- in-flight 상한을 둔다
- poll loop는 heartbeat와 fetch를 계속 수행한다
- commit 가능한 연속 offset만 계산한다

복잡도가 부담스럽다면 처음에는 작은 batch 순차 처리로 시작하는 편이 낫다.

### 5) Rebalance 충격 완화

```properties
partition.assignment.strategy=org.apache.kafka.clients.consumer.CooperativeStickyAssignor
```

그리고 환경이 맞으면 static membership을 고려한다.

```properties
group.instance.id=<stable-instance-id>
```

단, 모든 group에 기계적으로 넣지 말고 배포 방식과 identity 안정성을 확인한다.

### 6) Fetch 설정은 record 크기와 latency 목표에 맞춘다

Consumer 처리량에는 fetch 설정도 영향을 준다.

- `fetch.min.bytes`
- `fetch.max.wait.ms`
- `max.partition.fetch.bytes`
- `receive.buffer.bytes`

소량 저지연 서비스라면 너무 큰 batch를 기다리면 p99가 나빠질 수 있다. 반대로 대량 처리 배치형 Consumer라면 어느 정도 모아서 가져오는 것이 효율적이다.

하지만 fetch 튜닝은 보통 마지막 단계다. 먼저 처리 시간, commit 기준, downstream 병목, rebalance를 봐야 한다.

---

## 트레이드오프 1: 처리량을 높일수록 commit 정합성은 어려워진다

Consumer 성능을 높이는 방법은 많다.

- `max.poll.records`를 키운다
- batch 처리한다
- thread pool로 병렬 처리한다
- commit 주기를 늦춘다
- fetch batch를 키운다

하지만 처리량 최적화는 대부분 commit 정합성을 어렵게 만든다.

### 큰 batch의 장점

- fetch/commit overhead가 줄어든다
- DB bulk insert나 batch API 호출이 가능하다
- 네트워크 효율이 좋아진다

### 큰 batch의 단점

- 실패 시 재처리 범위가 커진다
- 처리 시간이 길어져 `max.poll.interval.ms`에 가까워진다
- batch 중간 실패 시 commit 가능한 offset 계산이 어려워진다
- poison pill 하나가 큰 batch 전체를 막을 수 있다

### 병렬 처리의 장점

- CPU와 I/O 대기를 더 잘 활용한다
- downstream latency를 숨길 수 있다
- partition 수가 적어도 어느 정도 처리량을 끌어올릴 수 있다

### 병렬 처리의 단점

- partition 순서 보장이 깨질 수 있다
- 연속 offset commit 추적이 필요하다
- in-flight 작업 취소와 revoke 처리가 어려워진다
- memory pressure가 커진다

운영 기준은 명확하다.

**먼저 정확한 commit 모델을 만든 뒤, 그 모델이 허용하는 범위 안에서 batch와 병렬성을 키워야 한다.**

반대로 처리량부터 높이고 나중에 commit을 맞추려 하면 거의 항상 사고가 난다.

---

## 트레이드오프 2: 빠른 장애 감지와 불필요한 리밸런싱은 반대 방향으로 움직인다

`session.timeout.ms`를 짧게 잡으면 죽은 consumer를 빨리 감지한다. 장애 복구가 빠르다.

하지만 너무 짧으면:

- GC pause
- 네트워크 jitter
- broker 일시 부하
- container CPU throttle

같은 이유로 멀쩡한 consumer도 죽었다고 판단될 수 있다. 그러면 rebalance가 자주 발생하고 처리량이 흔들린다.

반대로 timeout을 길게 잡으면 false positive는 줄지만, 진짜 죽은 consumer의 partition을 오래 회수하지 못한다.

따라서 설정은 서비스 성격에 따라 달라진다.

### 저지연 온라인 Consumer

- 장애 감지는 비교적 빠르게
- batch는 작게
- downstream timeout도 짧게
- lag spike에 민감하게 알림

### 대량 배치형 Consumer

- 처리 시간이 길 수 있으므로 `max.poll.interval.ms` 여유 필요
- batch 크기와 commit 단위 최적화
- session timeout은 불필요한 rebalance를 줄이는 방향
- 복구 시간보다 처리량이 더 중요할 수 있음

### Stateful Consumer

- assignment 안정성이 중요
- cooperative sticky와 static membership 고려
- local state warmup 시간 반영
- rebalance 횟수 자체를 줄이는 것이 중요

한 가지 설정 묶음을 모든 Consumer에 복사하는 것은 위험하다. Consumer마다 처리 시간, side effect, 순서 요구사항, 복구 목표가 다르다.

---

## 트레이드오프 3: 원본 순서 보장과 빠른 장애 우회는 충돌한다

Retry/DLQ 설계에서 가장 어려운 지점은 순서다.

원본 partition에서 실패 메시지를 붙잡고 있으면 순서는 지킨다. 하지만 정상 메시지도 모두 막힌다.

Retry topic으로 빼면 원본 처리는 계속된다. 하지만 실패 메시지가 나중에 처리되어 순서가 바뀔 수 있다.

### 순서가 더 중요한 경우

- 계좌 입출금 ledger
- 재고 증감
- 같은 주문의 상태 machine
- CDC 기반 projection
- aggregate version을 순서대로 적용해야 하는 이벤트

이 경우에는 실패 메시지를 쉽게 건너뛰면 안 된다. partition pause, 제한된 retry, 운영 알림, 수동 복구가 필요할 수 있다.

### 진행성이 더 중요한 경우

- 이메일/푸시 발송
- 검색 색인 업데이트
- analytics event 적재
- 독립적인 webhook 처리
- 추천 feature update

이 경우 실패 메시지를 retry topic이나 DLQ로 분리해 정상 흐름을 유지하는 것이 더 낫다.

결국 retry 전략은 Kafka 기술 문제가 아니라 **도메인 정합성 정책**이다.

---

## 흔한 실수 1: Consumer 수만 늘리면 lag가 줄 거라고 믿는다

Consumer 수를 늘리는 것은 가장 쉬운 대응이다. 하지만 항상 효과가 있는 것은 아니다.

효과가 있는 경우:

- partition 수가 consumer 수보다 충분히 많다
- lag가 여러 partition에 고르게 분포한다
- downstream이 추가 처리량을 감당할 수 있다
- consumer CPU나 I/O가 병목이다

효과가 없는 경우:

- partition 수가 이미 consumer 수보다 적다
- lag가 특정 partition 하나에 몰려 있다
- downstream DB/API가 병목이다
- poison pill 하나가 partition을 막고 있다
- rebalance가 너무 자주 발생해 추가 consumer가 오히려 흔든다

Scale-out 전에는 최소한 partition별 lag와 downstream latency를 봐야 한다.

---

## 흔한 실수 2: Auto Commit을 켜고 처리 성공을 가정한다

Auto commit은 Consumer 예제 코드에서는 편하다. 하지만 실제 업무 이벤트에서는 위험하다.

특히 아래 조건이면 피하는 편이 좋다.

- DB write가 있다
- 외부 API side effect가 있다
- 처리 실패 시 반드시 재처리해야 한다
- 메시지 유실이 비즈니스 사고가 된다
- batch 중 일부 실패가 가능하다

Auto commit은 “읽었다”에 가까운 기준이지 “비즈니스 처리가 끝났다”와는 거리가 있다.

---

## 흔한 실수 3: `max.poll.interval.ms`만 크게 늘려 장애를 숨긴다

`max.poll.interval.ms` 에러는 결과다. 처리 loop가 너무 오래 걸렸다는 신호다.

값을 키우기 전에 확인해야 한다.

- `max.poll.records`가 너무 큰가
- 레코드 하나 처리 p99가 얼마인가
- 외부 API timeout이 지나치게 긴가
- thread pool queue가 무제한인가
- DB connection pool 대기가 긴가
- poison pill에서 무한 retry하고 있는가
- GC pause나 CPU throttle이 있는가

Timeout을 늘리는 것은 마지막 보정이어야 한다.

---

## 흔한 실수 4: DLQ를 만들고 운영 프로세스를 만들지 않는다

DLQ는 실패 메시지 쓰레기통이 아니다. 운영 가능한 DLQ에는 최소한 다음이 있어야 한다.

- 왜 실패했는지 error code와 stack trace 요약
- 원본 topic/partition/offset
- event key와 event id
- retry count
- 최초 실패 시각과 마지막 실패 시각
- 재처리 도구
- 폐기 기준
- 알림 기준

DLQ에 쌓이는 메시지를 아무도 보지 않으면, 그것은 유실을 이름만 바꿔 저장한 것이다.

---

## 흔한 실수 5: Rebalance 지표를 보지 않는다

Consumer lag만 보고 rebalance를 안 보면 원인을 놓친다.

반드시 봐야 할 지표는 다음이다.

- rebalance total count
- rebalance duration
- assigned partition count
- revoked partition count
- failed rebalance count
- time since last rebalance
- partition lost 이벤트

배포 시간대에 lag가 튄다면 rebalance 지표와 같이 겹쳐봐야 한다. 여기서 문제가 보이면 cooperative sticky, static membership, graceful shutdown, preStop hook, 처리 중 commit 전략을 함께 검토해야 한다.

---

## 운영 체크리스트: Consumer Group을 배포하기 전 확인할 것

### Partition과 key

- [ ] partition 수가 목표 처리량과 consumer 수에 충분한가
- [ ] key가 순서 보장 단위와 일치하는가
- [ ] hot key나 tenant skew 가능성이 있는가
- [ ] partition별 lag를 볼 수 있는가

### Offset commit

- [ ] `enable.auto.commit=false`가 필요한 업무인가
- [ ] 처리 성공 기준과 commit 기준이 일치하는가
- [ ] batch 중 일부 실패 시 commit 가능한 offset 계산이 명확한가
- [ ] commit 실패 시 재시도/종료 정책이 있는가
- [ ] revoke 시 처리 완료 offset을 sync commit하는가

### Idempotency

- [ ] event id가 안정적으로 존재하는가
- [ ] 중복 이벤트를 DB에서 흡수할 수 있는가
- [ ] 외부 API 호출에 idempotency key가 있는가
- [ ] 알림/이메일 같은 side effect를 outbox로 분리했는가
- [ ] 재처리해도 ledger나 상태가 깨지지 않는가

### Poll loop와 timeout

- [ ] `max.poll.records`가 최악 처리 시간 기준으로 안전한가
- [ ] `max.poll.interval.ms`가 정상 batch 처리 시간을 반영하는가
- [ ] 외부 API timeout이 무한정 길지 않은가
- [ ] poll thread가 장시간 blocking되지 않는가
- [ ] thread pool queue와 in-flight 상한이 있는가

### Rebalance

- [ ] cooperative sticky assignor를 검토했는가
- [ ] static membership이 배포 방식과 맞는가
- [ ] graceful shutdown 시 새 poll을 멈추고 in-flight를 정리하는가
- [ ] partition revoke listener가 안전하게 commit하는가
- [ ] rolling deploy 중 lag spike를 측정했는가

### Retry와 DLQ

- [ ] retry 가능한 오류와 불가능한 오류를 구분하는가
- [ ] retry backoff와 최대 횟수가 있는가
- [ ] 순서가 중요한 이벤트를 retry topic으로 빼도 되는가
- [ ] DLQ 메시지에 원본 offset과 실패 이유가 남는가
- [ ] DLQ 재처리 도구와 알림 기준이 있는가

### Observability

- [ ] group/partition별 lag를 본다
- [ ] consumed rate와 produced rate를 같이 본다
- [ ] processing latency와 commit latency를 분리해서 본다
- [ ] rebalance count와 duration을 본다
- [ ] downstream latency/error를 Consumer 지표와 같이 본다
- [ ] pause된 partition과 oldest in-flight age를 본다

---

## 코드 리뷰에서 바로 잡아야 할 안티패턴

Consumer 코드를 리뷰할 때는 아래 패턴을 특히 조심해야 한다.

### 1) poll 후 바로 commit

```text
records = poll()
commit()
process(records)
```

처리 전 commit은 유실을 만든다.

### 2) 처리 thread pool에 던지고 offset은 batch 끝으로 commit

```text
for record in records:
    executor.submit(process(record))
commit(records.last.offset + 1)
```

작업 완료를 기다리지 않고 commit하면 실패 메시지를 잃는다.

### 3) 실패 시 무한 sleep

```text
while true:
    try process(record)
    catch sleep(5 minutes)
```

poll loop가 멈추고 rebalance가 발생할 수 있다. partition pause나 retry topic을 검토해야 한다.

### 4) partition 상관없이 완료 offset max만 commit

```text
commit(max(successOffsets) + 1)
```

partition별로 따로 계산해야 한다. 그리고 연속 성공 offset만 commit해야 한다.

### 5) 외부 side effect 후 idempotency 없이 commit

```text
callPaymentApi()
sendEmail()
commit()
```

commit 전 장애 시 외부 side effect가 중복될 수 있다. idempotency key, outbox, processed event store가 필요하다.

---

## 실전 설계 예시: Consumer 유형별 추천 방향

### 1) 결제/정산 Consumer

특징:

- 중복 처리 위험이 큼
- 유실 허용 어려움
- 순서와 idempotency 중요

추천:

- manual commit
- inbox/outbox 패턴
- event id 기반 중복 제거
- 작은 batch
- retry topic 신중히 사용
- DLQ 운영 알림 강하게
- partition key는 비즈니스 aggregate 기준

### 2) 검색 색인 Consumer

특징:

- 최종 상태 반영이 중요
- 중복 처리 대체로 허용 가능
- 일부 순서 역전은 version으로 방어 가능

추천:

- manual commit
- document version 비교
- retry topic 적극 사용
- DLQ 후 재색인 도구 제공
- bulk indexing으로 처리량 확보
- lag보다 색인 freshness 지표 추가

### 3) 알림 발송 Consumer

특징:

- 외부 API side effect
- 중복 발송이 사용자 경험 문제
- 지연 허용 범위가 비교적 명확

추천:

- idempotency key 필수
- 발송 요청 outbox 분리
- provider rate limit에 맞춘 pause/resume
- retry backoff
- 중복 발송 방지 테이블
- DLQ 운영 화면 필요

### 4) 분석 이벤트 적재 Consumer

특징:

- 처리량 중요
- 일부 중복은 downstream dedup 가능
- 순서 중요도가 낮은 경우 많음

추천:

- batch 처리
- 큰 fetch/batch 튜닝 가능
- retry topic 사용
- object storage flush 정책 명확화
- schema validation 실패는 DLQ
- lag와 적재 지연을 별도로 측정

### 5) Stateful Projection Consumer

특징:

- partition assignment 안정성 중요
- local state 또는 cache 존재
- 재시작 비용 큼

추천:

- cooperative sticky assignor
- static membership 검토
- partition key와 state shard 일치
- restore 시간 지표화
- revoke 시 state flush
- version/order 검증

---

## 장애 대응 절차: Lag가 갑자기 늘었을 때 무엇을 볼까

Lag 알림이 왔을 때 바로 consumer replica를 늘리기 전에 다음 순서로 본다.

### 1단계: 어느 partition인가

- 모든 partition이 같이 늘었는가
- 특정 partition만 늘었는가
- 특정 consumer가 맡은 partition만 늘었는가

특정 partition만 늘면 key skew, poison pill, 해당 partition owner 문제를 본다.

### 2단계: 유입량이 늘었는가

- producer rate가 증가했는가
- 특정 배치나 캠페인이 이벤트를 폭증시켰는가
- 평소 대비 record size가 커졌는가

유입량 증가라면 capacity 문제일 수 있다.

### 3단계: 처리 시간이 늘었는가

- processing latency p95/p99
- downstream DB/API latency
- thread pool queue depth
- connection pool wait
- error rate와 retry count

처리 시간이 늘었다면 Kafka보다 downstream이 원인일 가능성이 높다.

### 4단계: Rebalance가 있었는가

- 최근 배포가 있었는가
- rebalance count가 증가했는가
- `max.poll.interval.ms` 초과 로그가 있는가
- coordinator 변경이나 broker 장애가 있었는가

Rebalance가 원인이면 assignment strategy, graceful shutdown, timeout, poll loop를 본다.

### 5단계: Commit이 밀렸는가

- 처리 완료 offset과 commit offset 차이
- commit latency
- commit failure 로그
- coordinator 요청 지연

처리는 됐는데 commit만 밀렸다면 lag 지표가 과장되어 보일 수 있다.

### 6단계: 임시 조치와 재발 방지 분리

임시 조치:

- consumer scale-out
- 특정 partition pause/resume
- retry topic 우회
- downstream rate limit 완화
- poison pill DLQ 이동

재발 방지:

- key skew 개선
- partition 증설
- idempotency 보강
- batch 크기 조정
- cooperative/static membership 적용
- timeout budget 재설계
- DLQ 운영화

장애 중에는 빠른 복구가 우선이지만, 복구 후에는 반드시 “왜 lag가 늘었는가”를 partition, processing, rebalance, commit 네 축으로 분해해야 한다.

---

## 마무리: Consumer Group은 읽기 코드가 아니라 분산 처리의 경계다

Kafka Consumer 운영은 겉으로는 단순하다. 하지만 실제로는 partition ownership, offset commit, rebalance, retry, idempotency, observability가 모두 맞물린다.

중요한 기준을 다시 정리하면 다음과 같다.

- partition은 병렬성 단위이자 순서 보장 단위다
- rebalance는 장애 복구 기능이지만 처리 중단을 만들 수 있다
- heartbeat와 session timeout은 프로세스 생존을 보고, `max.poll.interval.ms`는 처리 loop 진행성을 본다
- offset commit은 “여기까지 다시 읽지 않겠다”는 선언이다
- 유실을 피하려면 처리 성공 후 commit하고, 중복을 견디려면 idempotency가 필요하다
- retry topic은 진행성을 높이지만 순서를 깨뜨릴 수 있다
- lag는 원인이 아니라 증상이며, partition별로 해석해야 한다
- cooperative sticky와 static membership은 배포 중 rebalance 충격을 줄이는 좋은 도구다

Consumer를 안정화한다는 것은 설정을 많이 아는 것이 아니다. **비즈니스 처리 완료 기준과 Kafka offset 진행 기준을 같은 언어로 맞추는 것**이다.

마지막 한 줄로 정리하면 이렇다.

> **Kafka Consumer Group은 빠르게 읽는 장치가 아니라, 장애가 나도 어디까지 처리했고 어디부터 다시 읽을지를 팀이 합의한 방식대로 지키게 만드는 실행 계약이다.**
