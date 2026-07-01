---
layout: post
title: "Java 장애 격리 실전: Timeout, Retry, Circuit Breaker, Bulkhead, Rate Limiter를 운영 기준으로 조합하는 법"
date: 2026-07-01 11:50:00 +0900
categories: [java]
tags: [study, java, resilience4j, timeout, retry, circuit-breaker, bulkhead, rate-limiter, backend, distributed-system, operations]
permalink: /java/2026/07/01/study-java-resilience4j-timeout-retry-circuit-breaker-bulkhead-ratelimiter.html
---

## 배경: 장애 대응 코드는 "예외 처리"가 아니라 실패 전파를 설계하는 일이다

Java 백엔드에서 외부 시스템 호출은 거의 피할 수 없다.

- 결제 승인 API를 호출한다.
- 회원 등급 서비스를 조회한다.
- 재고 서비스를 확인한다.
- 쿠폰 서버에 할인 가능 여부를 묻는다.
- 검색 API에서 상품 목록을 가져온다.
- 추천 서버에서 개인화 결과를 받는다.
- 메시지 브로커, Redis, 데이터베이스, object storage, 사내 HTTP API에 의존한다.

처음에는 이런 코드를 단순하게 만든다.

```java
PaymentApproval approval = paymentClient.approve(command);
order.markPaid(approval.transactionId());
```

정상 상황에서는 문제없다. 하지만 운영에서 중요한 것은 정상 경로가 아니다.

- 결제사가 300ms 안에 응답하던 API가 갑자기 8초씩 걸린다.
- 네트워크는 끊기지 않았지만 tail latency가 길어진다.
- 실패율은 3%뿐인데 retry가 붙으면서 트래픽이 3배로 튄다.
- 느린 추천 API 때문에 주문 API thread pool이 같이 고갈된다.
- 장애 난 외부 시스템을 계속 호출해 우리 서비스까지 느려진다.
- fallback을 넣었는데 품질 저하가 조용히 누적되어 비즈니스 지표가 깨진다.
- circuit breaker가 열렸지만 알림이 없어 아무도 모른다.
- timeout은 1초인데 HTTP client connection read timeout은 10초라 실제 자원은 계속 붙잡힌다.

이런 문제는 `try-catch`를 잘 쓰면 해결되는 종류가 아니다.

분산 시스템에서 실패는 단순한 예외 객체가 아니다. 실패는 **시간**, **동시성**, **트래픽 증폭**, **자원 점유**, **부분 성공**, **사용자 경험**, **데이터 정합성**을 함께 흔든다.

따라서 Java 서비스에서 resilience를 설계한다는 것은 아래 질문에 답하는 일이다.

1. 이 호출은 최대 몇 ms까지 기다릴 수 있는가?
2. 실패했을 때 재시도해도 안전한가?
3. 재시도는 어느 계층에서 몇 번까지 허용할 것인가?
4. 실패율이 올라갈 때 계속 호출할 것인가, 잠시 차단할 것인가?
5. 특정 dependency가 느려졌을 때 전체 thread pool을 같이 잡아먹지 않게 할 수 있는가?
6. 호출량을 제한해야 하는가, 동시 실행 수를 제한해야 하는가?
7. fallback은 비즈니스적으로 허용되는가, 아니면 실패를 명확히 드러내야 하는가?
8. 장애 격리 정책이 실제로 동작하는지 어떤 metric으로 볼 것인가?

오늘 글은 Resilience4j 문법 소개가 아니다. 중급 이상 Java 개발자가 운영 API에서 반드시 정해야 하는 실패 계약을 기준으로 `timeout`, `retry`, `circuit breaker`, `bulkhead`, `rate limiter`를 조합하는 법을 정리한다.

핵심 결론부터 말하면 이렇다.

**장애 격리의 핵심은 "실패를 없애는 것"이 아니라, 실패가 어디까지 퍼질 수 있는지, 얼마나 오래 기다릴지, 언제 포기할지, 어떤 품질 저하를 허용할지를 코드와 지표에 명시하는 것이다.**

Resilience4j 같은 라이브러리는 이 설계를 실행하게 해 주는 도구다. 도구를 붙인다고 resilience가 생기지는 않는다. 오히려 timeout, retry, breaker, bulkhead를 잘못 조합하면 장애를 더 빠르게 증폭시킨다.

---

## 먼저 큰 그림: 장애 격리 패턴은 서로 다른 실패 축을 다룬다

많은 팀이 resilience 패턴을 하나의 뭉치로 기억한다.

- timeout
- retry
- circuit breaker
- bulkhead
- rate limiter
- fallback

하지만 이들은 같은 문제를 푸는 도구가 아니다. 각 패턴은 서로 다른 실패 축을 다룬다.

```text
Timeout
  -> 한 호출이 자원을 얼마나 오래 붙잡을 수 있는가

Retry
  -> 일시 실패를 다시 시도해 성공률을 높일 것인가

Circuit Breaker
  -> 실패가 계속될 때 호출 자체를 잠시 차단할 것인가

Bulkhead
  -> 특정 의존성 장애가 전체 실행 자원을 고갈시키지 못하게 할 것인가

Rate Limiter
  -> 단위 시간당 호출량을 제한해 downstream과 우리 서비스를 보호할 것인가

Fallback
  -> 실패 시 어떤 낮은 품질의 결과 또는 대체 경로를 허용할 것인가
```

이 차이를 구분하지 않으면 이상한 조합이 나온다.

- timeout 없이 retry만 붙인다.
- retry를 여러 계층에 중복으로 붙인다.
- circuit breaker를 모든 예외에 열리게 해 validation 실패까지 장애로 본다.
- bulkhead 없이 virtual thread나 async fan-out만 늘린다.
- rate limiter로 동시 실행 수 문제를 해결하려 한다.
- fallback으로 장애를 숨기면서 business KPI가 무너지는지 보지 않는다.

운영 가능한 설계는 보통 다음 순서로 생각하는 편이 좋다.

1. 호출 목적을 분류한다.
2. 사용자 요청의 전체 latency budget을 정한다.
3. dependency별 timeout budget을 나눈다.
4. retry 가능 여부를 idempotency 기준으로 판단한다.
5. retry storm을 막기 위해 backoff와 jitter를 둔다.
6. 실패율이 올라갈 때 circuit breaker로 빠른 실패를 만든다.
7. bulkhead로 dependency별 동시 실행 수를 제한한다.
8. rate limiter로 단위 시간 호출량을 제한한다.
9. fallback이 허용되는 경로와 허용되지 않는 경로를 나눈다.
10. metric, log, trace, alert로 정책 효과를 확인한다.

이 순서가 중요한 이유는 resilience 정책이 서로 영향을 주기 때문이다. timeout이 너무 길면 retry는 실제로 거의 의미가 없다. retry가 너무 공격적이면 circuit breaker가 열리기 전에 downstream을 더 세게 때린다. bulkhead가 없으면 breaker가 열리기 전까지 thread pool이 먼저 고갈될 수 있다.

---

## 핵심 개념 1: Timeout은 성능 옵션이 아니라 자원 점유 상한이다

timeout은 흔히 "응답을 얼마나 기다릴 것인가"로 설명된다. 맞는 말이지만 운영에서는 더 정확히 이렇게 봐야 한다.

> Timeout은 한 실패한 dependency 호출이 우리 서비스의 thread, connection, memory, request slot을 얼마나 오래 붙잡을 수 있는지 정하는 상한이다.

예를 들어 주문 API의 목표 응답 시간이 800ms라고 하자.

```text
전체 주문 API budget: 800ms
  - 인증/권한: 50ms
  - 주문 상태 조회: 80ms
  - 재고 확인: 150ms
  - 결제 승인: 350ms
  - outbox 기록: 50ms
  - 여유/직렬화: 120ms
```

이 구조에서 결제 API timeout을 3초로 두면 전체 budget은 이미 깨졌다. 사용자는 800ms 안에 응답받을 수 없고, 요청 thread는 계속 점유된다. 트래픽이 늘면 thread pool과 connection pool이 먼저 막힌다.

### Timeout은 여러 레이어에 있다

Java 서비스에서는 timeout이 한 군데만 있지 않다.

- Controller 또는 gateway request timeout
- service method 내부 deadline
- HTTP client connect timeout
- HTTP client connection request timeout
- HTTP client read/response timeout
- Resilience4j TimeLimiter timeout
- DB query timeout
- transaction timeout
- message consumer processing timeout
- thread pool queue wait timeout

문제는 이 값들이 서로 어긋날 때 생긴다.

예를 들어 Resilience4j `TimeLimiter`를 500ms로 잡았지만 underlying HTTP client read timeout이 5초라면 어떤 일이 생길까?

- 호출자는 500ms 후 timeout으로 실패를 받는다.
- 하지만 실제 HTTP 요청은 client와 executor 구현에 따라 계속 살아 있을 수 있다.
- connection은 아직 반환되지 않을 수 있다.
- downstream은 이미 처리 중일 수 있다.
- retry가 붙어 있다면 이전 요청이 끝나기도 전에 새 요청이 나간다.

따라서 timeout은 "겉에서 빨리 포기하는 값"만으로 충분하지 않다. 실제 자원 해제를 일으키는 lower-level timeout과 함께 정렬되어야 한다.

### Deadline 전파가 필요한 이유

고정 timeout보다 더 나은 방식은 요청 단위 deadline을 갖고 dependency 호출마다 남은 시간을 계산하는 것이다.

```java
public final class RequestDeadline {
    private final Instant deadline;

    public RequestDeadline(Clock clock, Duration budget) {
        this.deadline = clock.instant().plus(budget);
    }

    public Duration remaining(Clock clock) {
        Duration remaining = Duration.between(clock.instant(), deadline);
        return remaining.isNegative() ? Duration.ZERO : remaining;
    }
}
```

그리고 외부 호출 직전에 남은 시간을 본다.

```java
Duration remaining = deadline.remaining(clock);
if (remaining.compareTo(Duration.ofMillis(120)) < 0) {
    throw new DeadlineExceededException("not enough budget for payment approval");
}

PaymentResult result = paymentClient.approve(command, remaining);
```

이 접근의 장점은 분명하다.

- 앞 단계가 늦어지면 뒤 단계가 무리하게 긴 호출을 시작하지 않는다.
- retry 여부를 남은 시간 기준으로 결정할 수 있다.
- trace에 전체 budget과 dependency별 소모 시간을 남기기 쉽다.
- gateway timeout보다 내부 timeout이 더 길어지는 실수를 줄인다.

단점도 있다. 모든 client와 service method에 deadline을 전달해야 하므로 코드가 조금 번거롭다. 하지만 중급 이상 서비스에서는 이 명시성이 대체로 비용보다 가치가 크다.

---

## 핵심 개념 2: Retry는 성공률을 높이지만 장애 트래픽도 함께 늘린다

retry는 가장 유혹적인 패턴이다.

외부 API가 가끔 실패한다. 한 번 더 호출하면 성공할 때가 있다. 그러면 retry를 붙이고 성공률을 올린다.

문제는 장애가 커질 때 retry가 트래픽 증폭기가 된다는 점이다.

```text
정상 요청 1,000 rps
실패율 상승
각 요청 2회 retry
downstream에는 최대 3,000 rps에 가까운 호출이 유입
```

downstream이 이미 느린데 retry가 더 붙으면 회복을 돕는 것이 아니라 더 늦춘다. 특히 여러 서비스가 같은 dependency를 향해 동시에 retry하면 retry storm이 된다.

### Retry 가능한 실패와 불가능한 실패를 나눠라

retry 여부는 예외 타입만으로 정하면 안 된다. 핵심 기준은 두 가지다.

1. 실패가 일시적인가?
2. 같은 요청을 다시 보내도 안전한가?

일반적으로 retry 후보가 될 수 있는 실패:

- connection timeout
- read timeout
- HTTP 429
- HTTP 503
- 일시적인 DNS 또는 network 오류
- optimistic lock conflict 중 재시도 설계가 된 경우
- serialization failure 중 idempotent transaction

retry하면 안 되는 실패:

- validation error
- authentication/authorization failure
- 잘못된 요청 payload
- 잔액 부족, 재고 부족처럼 비즈니스 거절이 확정된 경우
- idempotency key 없는 결제 승인, 송금, 포인트 차감
- downstream이 명확히 "처리됨"을 반환했는데 응답 파싱만 실패한 경우

특히 write 호출에서 retry는 위험하다.

```java
paymentClient.approve(orderId, amount);
```

이 호출이 timeout 됐다고 해서 결제가 안 된 것은 아니다. 결제사는 이미 승인했지만 응답만 늦었을 수 있다. 이때 같은 요청을 idempotency key 없이 다시 보내면 중복 결제 위험이 생긴다.

더 나은 구조는 요청마다 idempotency key를 붙이는 것이다.

```java
public PaymentApproval approvePayment(Order order) {
    String idempotencyKey = "payment-approval:" + order.id();

    return paymentClient.approve(new PaymentApprovalRequest(
            order.id(),
            order.amount(),
            idempotencyKey
    ));
}
```

idempotency key는 retry의 안전벨트다. 이 안전벨트가 없다면 write retry는 아주 보수적으로 봐야 한다.

### Backoff와 jitter는 기본값이 아니라 필수다

retry를 즉시 다시 보내면 여러 인스턴스가 동시에 같은 리듬으로 downstream을 때린다.

나쁜 retry:

```text
0ms 실패
즉시 retry
즉시 retry
최종 실패
```

더 나은 retry:

```text
0ms 실패
100ms + jitter
250ms + jitter
최종 실패
```

jitter가 중요한 이유는 모든 client가 같은 시간에 재시도하는 것을 흩어 주기 때문이다. 장애 상황에서는 평균 지연보다 동시 피크가 더 문제다.

Resilience4j 설정도 이 관점으로 읽어야 한다.

```yaml
resilience4j:
  retry:
    instances:
      payment:
        max-attempts: 3
        wait-duration: 100ms
        enable-exponential-backoff: true
        exponential-backoff-multiplier: 2
        retry-exceptions:
          - java.net.SocketTimeoutException
          - org.springframework.web.client.ResourceAccessException
        ignore-exceptions:
          - com.example.payment.PaymentRejectedException
```

여기서 `max-attempts: 3`은 "원 호출 + 재시도 2회"로 읽어야 한다. 이 값이 생각보다 커지기 쉽다. 상위 gateway, HTTP client, message consumer, SDK가 각각 retry를 갖고 있으면 총 시도 횟수는 곱으로 증가한다.

---

## 핵심 개념 3: Circuit Breaker는 장애를 고치는 도구가 아니라 빠른 실패를 만드는 도구다

circuit breaker는 실패율이 높아졌을 때 일정 시간 호출을 차단한다.

상태는 보통 세 가지로 이해하면 된다.

```text
CLOSED
  정상 호출 허용, 실패율 관찰

OPEN
  호출 차단, 즉시 실패 반환

HALF_OPEN
  일부 테스트 호출만 허용해 회복 여부 확인
```

중요한 점은 circuit breaker가 downstream을 복구하지 않는다는 것이다. breaker는 우리 서비스가 이미 나쁜 상태인 dependency를 계속 호출하며 자원을 낭비하지 않게 만든다.

### Circuit breaker가 필요한 상황

- 특정 dependency 실패율이 높아졌다.
- timeout 때문에 thread와 connection이 계속 묶인다.
- retry를 해도 성공률이 낮다.
- fallback 또는 graceful degradation이 가능하다.
- 빠른 실패가 늦은 실패보다 사용자 경험과 시스템 안정성에 낫다.

예를 들어 추천 API는 주문 상세 화면에서 부가 정보일 수 있다. 추천 서버가 장애라면 2초 기다렸다가 전체 화면을 실패시키는 것보다 추천 영역만 비우는 편이 낫다.

반대로 결제 승인 같은 핵심 write 경로는 breaker를 열더라도 fallback으로 성공 처리하면 안 된다. 이 경우 빠르게 실패시키고 사용자에게 재시도를 안내하는 편이 맞다.

### 실패율 기준은 호출량 기준과 함께 봐야 한다

breaker 설정에서 흔한 실수는 실패율만 보는 것이다.

```yaml
failure-rate-threshold: 50
```

호출 2번 중 1번 실패해도 실패율은 50%다. 하지만 표본이 너무 적으면 breaker가 과민하게 열린다. 그래서 minimum call count가 중요하다.

```yaml
resilience4j:
  circuitbreaker:
    instances:
      recommendation:
        sliding-window-type: COUNT_BASED
        sliding-window-size: 50
        minimum-number-of-calls: 20
        failure-rate-threshold: 50
        slow-call-rate-threshold: 60
        slow-call-duration-threshold: 400ms
        wait-duration-in-open-state: 10s
        permitted-number-of-calls-in-half-open-state: 5
```

여기서 봐야 할 포인트는 둘이다.

1. 실패만 보지 않고 slow call도 본다.
2. 최소 호출 수를 채우기 전에는 판단하지 않는다.

장애는 항상 HTTP 500으로 오지 않는다. 많은 장애는 "느림"으로 먼저 온다. slow call threshold를 두지 않으면 breaker가 열리기 전에 thread pool이 고갈될 수 있다.

### 어떤 예외를 실패로 볼 것인가

breaker는 모든 예외를 실패로 보면 안 된다.

```java
CircuitBreakerConfig config = CircuitBreakerConfig.custom()
        .recordException(error -> error instanceof IOException
                || error instanceof TimeoutException
                || error instanceof DownstreamUnavailableException)
        .ignoreException(error -> error instanceof BusinessRuleViolationException
                || error instanceof ValidationException)
        .failureRateThreshold(50)
        .slowCallRateThreshold(60)
        .slowCallDurationThreshold(Duration.ofMillis(400))
        .minimumNumberOfCalls(20)
        .build();
```

사용자가 잘못된 쿠폰 코드를 입력해 `InvalidCouponException`이 났다면 그것은 쿠폰 서버 장애가 아니다. 이런 비즈니스 거절까지 실패율에 넣으면 정상 트래픽이 breaker를 열 수 있다.

---

## 핵심 개념 4: Bulkhead는 "많이 기다리는 호출"의 장애 반경을 제한한다

bulkhead는 배의 격벽에서 온 비유다. 한 구획에 물이 들어와도 전체 배가 가라앉지 않도록 구획을 나누는 것이다.

백엔드 서비스에서는 특정 dependency가 느려졌을 때 전체 실행 자원을 같이 고갈시키지 않도록 제한하는 패턴이다.

예를 들어 하나의 공용 executor를 모든 외부 호출에 쓴다고 하자.

```text
common-http-executor
  - payment
  - inventory
  - recommendation
  - coupon
  - search
```

추천 API가 느려져 요청이 쌓이면 같은 executor를 쓰는 결제, 재고, 쿠폰 호출까지 밀릴 수 있다. 추천은 부가 기능인데 주문 핵심 경로까지 망가진다.

bulkhead는 이를 dependency별 또는 기능별로 나눈다.

```text
payment-bulkhead: max 30 concurrent
inventory-bulkhead: max 40 concurrent
recommendation-bulkhead: max 10 concurrent
coupon-bulkhead: max 15 concurrent
```

추천 API가 느려져도 추천 bulkhead 10개만 묶인다. 나머지 기능은 자기 할당량 안에서 계속 동작한다.

### Semaphore bulkhead와 thread pool bulkhead

Resilience4j에서는 크게 두 관점이 있다.

Semaphore bulkhead:

- 호출 동시 실행 수를 제한한다.
- 별도 thread pool을 만들지 않는다.
- 이미 사용 중인 실행 모델을 유지한다.
- blocking 호출이라면 caller thread가 호출을 수행한다.

Thread pool bulkhead:

- 별도 executor로 작업을 분리한다.
- queue와 thread 수를 따로 둔다.
- blocking I/O를 격리하기 쉽다.
- context propagation, queue wait, cancellation 관리가 더 중요해진다.

Spring MVC 기반 blocking service라면 semaphore bulkhead만으로도 충분한 경우가 많다. 이미 request thread가 blocking 호출을 수행하므로 동시 실행 수를 제한하는 것이 핵심이다.

반대로 특정 작업을 별도 executor로 보내야 하거나, legacy SDK가 blocking이고 호출 시간이 길며, caller thread와 분리할 필요가 있다면 thread pool bulkhead를 검토할 수 있다.

다만 thread pool bulkhead를 붙이면 queue가 생긴다. queue는 완충재이지만 동시에 지연을 숨긴다.

```text
thread pool: 20
queue: 200
timeout: 500ms
```

이 설정에서 queue 대기만 400ms가 걸리면 실제 downstream 호출에 남은 시간이 거의 없다. 그래서 thread pool bulkhead에는 queue wait metric과 timeout 정렬이 꼭 필요하다.

### Bulkhead 크기는 평균 처리량이 아니라 장애 시나리오로 잡는다

bulkhead 크기를 정할 때 평균 QPS만 보면 부족하다.

필요한 질문은 이런 쪽이다.

- 이 dependency가 느려졌을 때 최대 몇 개 request thread를 희생할 수 있는가?
- 이 기능이 전체 서비스에서 얼마나 중요한가?
- downstream의 허용 동시 연결 수는 얼마인가?
- timeout까지 고려했을 때 최악의 점유 시간은 얼마인가?
- peak traffic에서 queue를 만들 것인가, 빠르게 reject할 것인가?

간단한 감각식은 이렇다.

```text
필요 동시성 ~= 초당 호출 수 * 평균 또는 목표 latency
```

예를 들어 결제 호출이 peak 100 rps이고 목표 latency가 200ms라면 정상 상태 동시성은 대략 20이다. 하지만 tail latency, 순간 피크, GC pause, network jitter를 고려해 여유를 둔다. 동시에 장애 시 전체 request thread를 보호하기 위해 무한히 키우지는 않는다.

---

## 핵심 개념 5: Rate Limiter는 동시성 제한이 아니라 시간당 유입량 제한이다

rate limiter와 bulkhead는 자주 섞인다.

하지만 둘은 다르다.

```text
Bulkhead
  지금 동시에 몇 개까지 실행할 수 있는가

Rate limiter
  일정 시간 동안 몇 개까지 시작할 수 있는가
```

느린 호출 때문에 thread가 묶이는 문제는 bulkhead가 더 직접적이다. 반대로 downstream API가 초당 100건까지만 허용하거나, 특정 tenant가 과도하게 호출하는 것을 막고 싶다면 rate limiter가 맞다.

예를 들어 외부 주소 검증 API가 계약상 초당 50건까지 허용된다고 하자.

```yaml
resilience4j:
  ratelimiter:
    instances:
      addressVerification:
        limit-for-period: 50
        limit-refresh-period: 1s
        timeout-duration: 50ms
```

여기서 `timeout-duration`은 permission을 기다리는 시간이다. 이 값을 길게 잡으면 rate limit에 걸린 요청이 줄 서서 기다린다. 짧게 잡으면 빨리 실패한다.

운영 API에서는 보통 무작정 기다리게 두기보다 빠르게 실패하거나 비동기 처리로 넘기는 편이 안전하다. 특히 사용자 요청 thread를 rate limiter 대기열로 오래 붙잡아두면 rate limiter가 보호 장치가 아니라 latency 증폭기가 된다.

### Rate limiter는 어디에 둘 것인가

rate limiter 위치도 중요하다.

- gateway level: 사용자/tenant별 ingress 제어
- service level: 특정 use case 호출량 제어
- client level: downstream별 outbound 호출량 제어
- worker level: batch 또는 consumer 처리 속도 제어

예를 들어 `paymentClient`에 outbound rate limiter를 두면 우리 서비스 전체에서 결제사로 나가는 호출량을 제한할 수 있다. 하지만 tenant별 남용을 막지는 못한다. tenant별 정책은 gateway나 application layer에서 별도 key 기반 limiter로 잡아야 한다.

---

## 실무 예시 1: 상품 상세 API에서 추천 서비스 장애를 격리하기

상품 상세 페이지를 생각해 보자.

핵심 정보:

- 상품 기본 정보
- 가격
- 재고

부가 정보:

- 추천 상품
- 최근 본 사용자 통계
- 리뷰 요약

추천 서비스가 장애라고 상품 상세 전체가 실패할 필요는 없다. 이 경우 추천 호출에는 짧은 timeout, 작은 bulkhead, circuit breaker, fallback을 조합할 수 있다.

```java
public ProductDetailResponse getProductDetail(Long productId) {
    Product product = productRepository.getById(productId);
    Price price = priceClient.getPrice(productId);
    Stock stock = stockClient.getStock(productId);

    List<Recommendation> recommendations = recommendationFacade
            .getRecommendations(productId)
            .orElseGet(List::of);

    return ProductDetailResponse.of(product, price, stock, recommendations);
}
```

추천 facade는 실패를 내부에서 낮은 품질로 바꾼다.

```java
public Optional<List<Recommendation>> getRecommendations(Long productId) {
    try {
        return Optional.of(recommendationClient.fetch(productId));
    } catch (CallNotPermittedException ex) {
        metrics.increment("recommendation.breaker.open");
        return Optional.empty();
    } catch (TimeoutException | DownstreamUnavailableException ex) {
        metrics.increment("recommendation.degraded");
        return Optional.empty();
    }
}
```

여기서 중요한 점은 fallback이 조용히 묻히면 안 된다는 것이다. 추천이 비어도 API는 성공할 수 있다. 하지만 fallback 비율이 높아지면 개인화 품질, 클릭률, 매출에 영향을 줄 수 있다. 따라서 `recommendation.degraded` 같은 metric이 필요하다.

이 use case의 정책은 이렇게 정리할 수 있다.

```text
추천 서비스 정책
  - 사용자 요청 critical path이지만 핵심 정보는 아님
  - timeout: 150ms
  - retry: 없음 또는 1회 이하
  - circuit breaker: slow call 포함
  - bulkhead: 작게 제한
  - fallback: 빈 추천 또는 인기 상품 일부
  - alert: breaker open, fallback rate, slow call rate
```

---

## 실무 예시 2: 결제 승인 API에서 retry를 보수적으로 설계하기

결제 승인은 추천과 다르다. 실패를 빈 값으로 바꿀 수 없다.

결제 승인에서 중요한 질문은 다음이다.

- 승인 요청이 결제사에 도달했는가?
- 결제사가 승인했지만 응답만 실패한 것은 아닌가?
- 같은 주문에 대해 승인 요청을 다시 보내도 중복 결제가 안 나는가?
- timeout 후 상태 조회 API로 확인할 수 있는가?
- 사용자는 어떤 상태 메시지를 받아야 하는가?

결제 승인에 무작정 retry를 붙이면 위험하다.

나쁜 구조:

```java
@Retry(name = "payment")
public PaymentApproval approve(PaymentCommand command) {
    return paymentClient.approve(command);
}
```

더 나은 구조는 idempotency key와 상태 확인을 포함한다.

```java
public PaymentApproval approve(Order order) {
    String idempotencyKey = "order-payment:" + order.id();

    try {
        return paymentClient.approve(new PaymentRequest(
                order.id(),
                order.amount(),
                idempotencyKey
        ));
    } catch (PaymentTimeoutException ex) {
        return paymentStatusResolver.resolveAfterTimeout(order.id(), idempotencyKey);
    }
}
```

timeout 후 바로 실패로 볼지, 상태 조회로 확인할지는 결제사 API의 보장에 달려 있다.

```java
public PaymentApproval resolveAfterTimeout(Long orderId, String idempotencyKey) {
    PaymentStatus status = paymentClient.findStatus(idempotencyKey);

    if (status.isApproved()) {
        return PaymentApproval.from(status);
    }

    if (status.isNotFound()) {
        throw new PaymentUnknownException(orderId);
    }

    throw new PaymentPendingException(orderId);
}
```

이 구조에서 retry는 제한적으로만 허용한다.

- connect timeout: 짧은 retry 가능
- HTTP 503: idempotency key가 있으면 backoff 후 제한 retry 가능
- read timeout: 상태 확인 우선
- business reject: retry 금지
- unknown: 사용자에게 "확인 중" 상태 제공 또는 보상 프로세스

결제 같은 write 경로에서는 resilience의 목적이 "어떻게든 성공 응답을 주기"가 아니다. **중복 side effect 없이 최종 상태를 추적 가능하게 만드는 것**이 목적이다.

---

## 실무 예시 3: 내부 조회 fan-out에서 bulkhead와 deadline 조합하기

마이페이지 API가 여러 내부 서비스를 동시에 조회한다고 하자.

```text
MyPage API
  -> user-service
  -> order-service
  -> coupon-service
  -> point-service
  -> recommendation-service
```

`CompletableFuture`로 병렬화하면 평균 응답은 빨라질 수 있다.

```java
CompletionStage<User> user = userClient.getUser(userId);
CompletionStage<List<Order>> orders = orderClient.getRecentOrders(userId);
CompletionStage<List<Coupon>> coupons = couponClient.getCoupons(userId);
CompletionStage<Point> point = pointClient.getPoint(userId);
```

하지만 fan-out은 dependency 수만큼 장애면도 늘린다. 한 요청이 5개 dependency를 호출하면 100 rps가 내부적으로 500 rps가 된다. 여기에 retry까지 붙으면 더 커진다.

따라서 fan-out API에서는 아래가 중요하다.

- 전체 deadline을 먼저 정한다.
- 각 dependency별 timeout을 전체 deadline보다 작게 둔다.
- 부가 정보는 fallback 가능하게 설계한다.
- dependency별 bulkhead를 둔다.
- `allOf().join()`에서 어떤 호출이 실패했는지 잃지 않게 한다.
- metric은 전체 API latency뿐 아니라 dependency별 latency와 degraded count를 본다.

예를 들어 응답 조합 정책을 명시한다.

```java
public MyPageResponse getMyPage(Long userId, RequestDeadline deadline) {
    User user = userClient.getUser(userId, deadline.remaining(clock));

    Optional<List<Order>> orders = orderFacade.getRecentOrders(userId, deadline);
    Optional<List<Coupon>> coupons = couponFacade.getCoupons(userId, deadline);
    Optional<Point> point = pointFacade.getPoint(userId, deadline);
    Optional<List<Recommendation>> recommendations =
            recommendationFacade.getRecommendations(userId, deadline);

    return MyPageResponse.builder()
            .user(user)
            .orders(orders.orElseGet(List::of))
            .coupons(coupons.orElseGet(List::of))
            .point(point.orElse(Point.unknown()))
            .recommendations(recommendations.orElseGet(List::of))
            .degradedSections(buildDegradedSections(orders, coupons, point, recommendations))
            .build();
}
```

여기서 `user`는 필수라 실패 시 전체 API 실패로 둔다. 반면 recommendation은 실패해도 빈 목록으로 둔다. 이런 차이를 코드와 응답 모델에 드러내야 운영과 프론트엔드가 같은 의미를 공유할 수 있다.

---

## 조합 순서: Retry와 Circuit Breaker 중 무엇을 먼저 적용할 것인가

Resilience 패턴은 순서에 따라 의미가 달라진다.

예를 들어 retry가 breaker 안쪽에 있으면, 하나의 사용자 요청은 여러 번 시도한 뒤 최종 실패만 breaker에 기록될 수 있다.

```text
CircuitBreaker(
  Retry(
    actualCall
  )
)
```

반대로 retry가 breaker 바깥쪽에 있으면 각 retry 시도가 breaker를 통과하며 breaker metric에 각각 반영될 수 있다.

```text
Retry(
  CircuitBreaker(
    actualCall
  )
)
```

어느 쪽이 무조건 정답은 아니다. 하지만 운영 의미를 알아야 한다.

### Retry가 안쪽인 경우

장점:

- 일시 실패를 내부에서 흡수하고 최종 결과만 breaker가 본다.
- breaker가 너무 빨리 열리는 것을 줄일 수 있다.

단점:

- downstream에는 이미 여러 번 호출이 나갔는데 breaker 관측에는 한 번처럼 보일 수 있다.
- 장애 초기에 retry storm이 먼저 발생할 수 있다.

### Circuit breaker가 안쪽인 경우

장점:

- breaker가 열린 뒤 retry가 의미 없는 실제 호출을 반복하지 않는다.
- 각 시도 실패가 breaker에 더 직접적으로 반영된다.

단점:

- breaker가 열렸을 때 retry가 `CallNotPermittedException`을 반복 재시도하지 않도록 ignore 설정이 필요하다.
- 표본이 작으면 breaker가 과민하게 열릴 수 있다.

실무에서는 보통 다음 원칙을 둔다.

- `CallNotPermittedException`은 retry하지 않는다.
- 비즈니스 예외는 retry와 breaker 실패율에서 제외한다.
- timeout은 retry보다 안쪽 실제 호출에 적용되게 한다.
- 전체 요청 deadline은 retry 전체를 감싼다.
- bulkhead는 실제 자원 점유를 제한할 수 있는 위치에 둔다.

개념적으로는 이런 계층을 자주 쓴다.

```text
Request Deadline
  -> Bulkhead
    -> RateLimiter
      -> CircuitBreaker
        -> Retry
          -> Time-limited actual call
```

하지만 이 순서는 팀의 metric 해석 방식과 라이브러리 적용 방식에 맞춰 검증해야 한다. 중요한 것은 "어떤 순서인지 아무도 모르는 상태"를 피하는 것이다.

---

## 트레이드오프 1: 빠른 실패 vs 회복 기회

timeout을 짧게 잡고 breaker를 민감하게 열면 사용자 요청은 빨리 실패한다. 시스템 자원은 보호된다. 하지만 일시적인 짧은 지연에도 성공 기회를 잃을 수 있다.

반대로 timeout을 길게 잡고 retry를 많이 허용하면 성공률은 올라갈 수 있다. 하지만 tail latency와 자원 점유가 커지고 장애가 전파될 수 있다.

따라서 기능별로 판단해야 한다.

빠른 실패가 나은 경우:

- 검색 자동완성
- 추천 영역
- 부가 통계
- 비핵심 배너/개인화
- 사용자 요청 내 선택 정보

조금 더 기다릴 가치가 있는 경우:

- 결제 승인
- 주문 생성
- 인증/인가
- 데이터 정합성에 필수인 내부 조회
- 비동기 job의 단일 중요 단계

하지만 "중요하니 무한히 기다린다"는 답은 아니다. 중요한 호출일수록 timeout, 상태 확인, 보상 트랜잭션, 사용자 안내가 더 명확해야 한다.

---

## 트레이드오프 2: Fallback은 안정성을 주지만 품질 저하를 숨긴다

fallback은 사용자 경험을 부드럽게 만든다.

- 추천 실패 시 빈 추천을 보여준다.
- 포인트 조회 실패 시 "잠시 후 확인"을 보여준다.
- 리뷰 요약 실패 시 원본 리뷰 목록만 보여준다.
- 배송 ETA 실패 시 기본 안내 문구를 보여준다.

하지만 fallback은 실패를 숨긴다. API success rate만 보면 모든 것이 정상처럼 보인다.

그래서 fallback을 쓰는 순간 success metric을 둘로 나눠야 한다.

```text
technical success
  HTTP 200을 반환했는가

business complete success
  사용자가 기대한 모든 섹션을 정상 품질로 받았는가
```

추천 fallback이 40%인데 HTTP 200 비율이 99.9%라고 해서 정상이라고 말하면 안 된다.

fallback에는 반드시 다음 지표가 따라야 한다.

- fallback count
- fallback rate
- dependency별 fallback reason
- fallback 상태에서의 전환율 또는 핵심 business metric
- breaker open time
- degraded response ratio

응답 모델에 degraded 정보를 담을지도 고민해야 한다.

```json
{
  "productId": 100,
  "name": "Keyboard",
  "recommendations": [],
  "degradedSections": ["recommendations"]
}
```

외부 사용자에게 그대로 노출하지 않더라도 내부 log와 trace에는 남기는 편이 좋다.

---

## 트레이드오프 3: Bulkhead를 작게 잡으면 보호되고, 크게 잡으면 처리량이 오른다

bulkhead 크기는 늘 고민이다.

작게 잡으면:

- 장애 격리가 강해진다.
- downstream을 보호한다.
- 우리 서비스 전체 thread pool을 보호한다.
- 하지만 정상 피크에서 reject가 늘 수 있다.

크게 잡으면:

- 정상 처리량은 올라간다.
- 일시 피크 흡수력이 커진다.
- 하지만 downstream 장애 시 더 많은 자원이 묶인다.
- 장애 반경이 커진다.

따라서 bulkhead는 "최대 처리량을 뽑는 값"이 아니라 "장애 때 희생 가능한 동시성 한도"로 보는 편이 안전하다.

특히 부가 기능은 작은 bulkhead와 fallback이 잘 맞는다. 핵심 기능은 bulkhead를 조금 더 주되, timeout과 queue wait을 더 엄격히 관찰해야 한다.

---

## 트레이드오프 4: Retry는 사용자 성공률과 downstream 회복력을 맞바꾼다

retry는 개별 사용자 요청의 성공률을 올린다. 하지만 전체 시스템 관점에서는 추가 부하다.

따라서 retry는 아래 조건을 만족할 때만 적극적으로 쓴다.

- 실패가 일시적일 가능성이 높다.
- 요청이 idempotent하다.
- 전체 deadline 안에 재시도 시간이 들어간다.
- backoff와 jitter가 있다.
- retry 횟수 metric을 보고 있다.
- downstream 팀과 허용 정책이 합의되어 있다.

이 조건을 못 채우면 retry 대신 빠른 실패, queueing, 비동기 처리, 상태 확인, 보상 로직이 더 나을 수 있다.

---

## 흔한 실수 1: Timeout을 하나만 설정했다고 믿는다

가장 흔한 실수는 Resilience4j나 Spring 설정에 timeout 하나를 넣고 끝났다고 생각하는 것이다.

```yaml
timeout-duration: 500ms
```

하지만 실제 HTTP client는 5초를 기다릴 수 있다. connection pool에서 connection을 빌리는 데 1초를 기다릴 수 있다. thread pool queue에서 300ms를 기다릴 수 있다. gateway는 이미 1초 후 요청을 끊었을 수 있다.

timeout은 반드시 레이어별로 맞춰야 한다.

- gateway timeout
- application deadline
- bulkhead queue wait
- rate limiter permission wait
- connect timeout
- read/response timeout
- DB statement timeout
- transaction timeout

한 줄 timeout은 운영 계약이 아니다. timeout map이 운영 계약이다.

---

## 흔한 실수 2: 모든 예외를 retry한다

아래 설정은 위험하다.

```yaml
retry-exceptions:
  - java.lang.Exception
```

이러면 validation 실패, 권한 오류, 비즈니스 거절까지 retry될 수 있다. 재시도로 해결될 수 없는 실패를 반복 호출하면 latency와 부하만 늘어난다.

retry 대상은 좁게 잡아야 한다.

- timeout
- 일시 네트워크 오류
- 명시적 429/503
- 재시도 가능하다고 합의된 예외

그리고 ignore 대상도 명시한다.

- validation
- authentication
- authorization
- business rejection
- duplicate request
- insufficient balance

---

## 흔한 실수 3: Circuit breaker open을 정상 fallback으로만 처리한다

breaker가 열린 것은 중요한 운영 사건이다. 그런데 fallback이 잘 동작하면 아무도 모를 수 있다.

```java
catch (CallNotPermittedException ex) {
    return List.of();
}
```

이 코드는 사용자 화면을 보호할 수 있다. 하지만 metric과 alert가 없으면 dependency 장애를 숨긴다.

최소한 아래는 남겨야 한다.

- breaker state transition event
- open duration
- rejected call count
- fallback count
- affected endpoint
- affected tenant 또는 region

운영에서는 breaker open이 "에러가 줄었다"가 아니라 "실제 호출을 차단하기 시작했다"는 뜻이다.

---

## 흔한 실수 4: Bulkhead 없이 thread만 늘린다

트래픽이 늘고 외부 호출이 느려지면 thread pool을 키우고 싶어진다.

```yaml
server.tomcat.threads.max: 400
```

하지만 dependency가 느린 상태에서 thread만 늘리면 더 많은 요청이 동시에 같은 병목으로 들어간다. DB connection pool, HTTP connection pool, downstream capacity가 먼저 막히면 thread 증가는 장애를 늦추는 것이 아니라 키운다.

thread를 늘리기 전에 봐야 할 것은 dependency별 동시 실행 수다.

- 결제 호출이 몇 개 동시에 실행 중인가
- 재고 호출이 몇 개 동시에 실행 중인가
- 추천 호출이 몇 개 동시에 실행 중인가
- 각 dependency별 timeout까지 평균 점유 시간은 얼마인가
- 어느 호출이 request thread를 가장 오래 잡고 있는가

bulkhead는 thread 증설보다 먼저 검토할 가치가 있다.

---

## 흔한 실수 5: Rate limiter로 느린 dependency 문제를 해결하려 한다

rate limiter는 호출 시작 수를 제한한다. 이미 시작된 호출이 오래 걸리는 문제를 직접 해결하지 않는다.

느린 dependency 때문에 동시 실행이 쌓인다면 bulkhead와 timeout이 먼저다. rate limiter는 downstream 계약상 QPS를 지키거나 특정 client의 과도한 유입을 막는 데 더 잘 맞는다.

물론 둘을 함께 쓸 수 있다.

```text
Rate limiter
  -> 초당 시작량 제한

Bulkhead
  -> 동시에 실행 중인 호출 제한

Timeout
  -> 각 호출의 최대 점유 시간 제한
```

셋은 서로 대체재가 아니라 보완재다.

---

## 흔한 실수 6: Fallback을 도메인 의미 없이 만든다

fallback은 기술적으로 쉬워 보인다.

```java
return Optional.empty();
```

하지만 도메인 의미가 없으면 위험하다.

- 포인트 조회 실패를 0포인트로 보여주면 사용자는 손해를 본다고 느낀다.
- 재고 조회 실패를 재고 없음으로 처리하면 매출을 잃는다.
- 권한 서버 실패를 권한 없음으로 처리하면 정상 사용자를 막는다.
- 권한 서버 실패를 권한 있음으로 처리하면 보안 사고가 난다.
- 결제 실패를 성공으로 fallback하면 데이터 정합성이 깨진다.

fallback은 항상 도메인 결정이다. 기술팀 혼자 "빈 값이면 되겠지"로 정하면 안 된다.

fallback 후보:

- cached stale value
- empty optional section
- degraded label
- async processing accepted
- pending state
- manual review queue
- user-visible retry 안내
- hard failure

각 기능은 어떤 fallback이 허용되는지 문서화해야 한다.

---

## 운영 관측성: Resilience 정책은 metric 없이는 반쪽이다

장애 격리 코드는 붙였는데 metric이 없으면 실제로 도움 되는지 알 수 없다.

최소한 dependency별로 아래를 봐야 한다.

### 호출 결과

- success count
- failure count
- ignored error count
- timeout count
- retry attempt count
- retry exhausted count
- fallback count

### 지연

- p50, p95, p99 latency
- slow call count
- bulkhead queue wait time
- rate limiter wait time
- downstream response time

### 격리 상태

- circuit breaker state
- circuit breaker open count
- half-open trial success/failure
- bulkhead available permissions
- bulkhead rejected calls
- rate limiter rejected calls

### 비즈니스 영향

- degraded response rate
- 결제 pending count
- 추천 미노출 비율
- 쿠폰 조회 실패 후 구매 전환율
- tenant별 장애 집중도

Resilience4j는 Micrometer와 붙여 metric을 내보내기 좋다. 하지만 metric 이름이 자동으로 생긴다고 운영 관측성이 완성되는 것은 아니다. dashboard와 alert는 use case별 의미로 재구성해야 한다.

예를 들어 추천 서비스는 fallback rate가 중요하고, 결제 서비스는 unknown/pending 상태와 중복 방지 metric이 중요하다.

---

## 테스트 전략: 장애 격리 정책도 테스트해야 한다

resilience 설정은 운영에서만 검증하면 늦다. 최소한 몇 가지 테스트가 필요하다.

### 단위 테스트

- 어떤 예외가 retry 대상인지
- 어떤 예외가 retry 제외인지
- fallback이 허용되는 예외인지
- business rejection이 breaker 실패율에 포함되지 않는지
- deadline이 부족할 때 호출을 시작하지 않는지

예시:

```java
@Test
void doesNotRetryBusinessRejection() {
    PaymentClient client = mock(PaymentClient.class);
    given(client.approve(any()))
            .willThrow(new PaymentRejectedException("insufficient balance"));

    assertThatThrownBy(() -> service.approve(command))
            .isInstanceOf(PaymentRejectedException.class);

    then(client).should(times(1)).approve(any());
}
```

### 통합 테스트

- WireMock 같은 도구로 timeout, 503, 느린 응답을 재현한다.
- retry 횟수와 backoff를 확인한다.
- breaker가 open된 뒤 빠르게 실패하는지 확인한다.
- half-open에서 성공 시 closed로 돌아오는지 확인한다.
- fallback response shape이 프론트엔드 계약과 맞는지 확인한다.

### 부하 테스트

- dependency latency를 인위적으로 늘린다.
- bulkhead reject가 의도대로 발생하는지 본다.
- request thread pool이 보호되는지 본다.
- retry storm이 생기지 않는지 본다.
- fallback rate와 API p99 latency가 어떻게 움직이는지 본다.

장애 격리 정책은 평상시 성공 테스트보다 실패 주입 테스트에서 가치가 드러난다.

---

## 설정 예시: 하나의 dependency 정책을 문서처럼 읽히게 만들기

아래는 예시일 뿐이지만, 중요한 것은 설정을 use case 언어로 해석할 수 있어야 한다는 점이다.

```yaml
resilience4j:
  circuitbreaker:
    instances:
      recommendation:
        sliding-window-type: COUNT_BASED
        sliding-window-size: 100
        minimum-number-of-calls: 30
        failure-rate-threshold: 50
        slow-call-rate-threshold: 60
        slow-call-duration-threshold: 300ms
        wait-duration-in-open-state: 10s
        permitted-number-of-calls-in-half-open-state: 10

  retry:
    instances:
      recommendation:
        max-attempts: 2
        wait-duration: 50ms
        enable-exponential-backoff: true
        exponential-backoff-multiplier: 2

  bulkhead:
    instances:
      recommendation:
        max-concurrent-calls: 20
        max-wait-duration: 20ms

  ratelimiter:
    instances:
      recommendation:
        limit-for-period: 200
        limit-refresh-period: 1s
        timeout-duration: 10ms
```

이 설정은 다음 의미를 갖는다.

- 추천은 핵심 경로가 아니므로 오래 기다리지 않는다.
- 짧은 retry는 허용하지만 공격적으로 반복하지 않는다.
- 느린 호출이 많아지면 breaker를 열어 빠르게 fallback한다.
- 동시에 20개 이상 추천 호출이 쌓이면 빠르게 거절한다.
- 초당 outbound 호출량도 제한한다.

반면 결제는 전혀 다른 설정이 필요하다.

```text
payment
  - fallback으로 성공 처리 금지
  - idempotency key 필수
  - read timeout과 상태 조회 정책 정렬
  - retry는 제한적으로만 허용
  - breaker open 시 사용자에게 명확한 실패 또는 pending 안내
  - unknown 상태 reconciliation job 필요
```

같은 Resilience4j라도 dependency의 도메인 의미가 다르면 정책은 달라져야 한다.

---

## 배포 전 체크리스트

### Timeout과 deadline

- [ ] 사용자 요청의 전체 latency budget이 정의되어 있는가?
- [ ] dependency별 timeout이 전체 budget 안에 들어오는가?
- [ ] gateway timeout보다 내부 작업 timeout이 길지 않은가?
- [ ] HTTP client connect/read/connection request timeout이 설정되어 있는가?
- [ ] DB statement timeout과 transaction timeout이 필요한 경로에 있는가?
- [ ] retry 전체 시간이 deadline을 넘지 않는가?

### Retry

- [ ] retry 가능한 예외와 불가능한 예외가 분리되어 있는가?
- [ ] write 호출에는 idempotency key가 있는가?
- [ ] business rejection은 retry하지 않는가?
- [ ] backoff와 jitter가 있는가?
- [ ] 상위 계층, SDK, client 내부 retry와 중복되지 않는가?
- [ ] retry attempt count와 exhausted count를 metric으로 보는가?

### Circuit breaker

- [ ] minimum call count가 너무 낮지 않은가?
- [ ] slow call threshold가 dependency SLA와 맞는가?
- [ ] validation/business exception이 실패율에 포함되지 않는가?
- [ ] `CallNotPermittedException`을 retry하지 않는가?
- [ ] breaker state transition alert가 있는가?
- [ ] half-open trial 수가 회복 판단에 충분한가?

### Bulkhead와 rate limiter

- [ ] dependency별 동시 실행 수 상한이 있는가?
- [ ] 부가 기능과 핵심 기능이 같은 executor를 무제한 공유하지 않는가?
- [ ] bulkhead reject 시 fallback 또는 명확한 실패가 있는가?
- [ ] queue wait time을 관측하는가?
- [ ] rate limiter는 QPS 제한 목적이고 bulkhead는 동시성 제한 목적임을 구분했는가?
- [ ] tenant별 제한과 downstream별 제한을 혼동하지 않는가?

### Fallback

- [ ] fallback이 도메인적으로 허용되는가?
- [ ] fallback이 사용자에게 잘못된 사실을 보여주지 않는가?
- [ ] fallback rate를 별도 지표로 보는가?
- [ ] fallback 상태가 business KPI에 미치는 영향을 추적하는가?
- [ ] fallback으로 숨기면 안 되는 핵심 실패는 hard failure로 남기는가?

### 운영과 테스트

- [ ] dependency별 dashboard가 있는가?
- [ ] p95/p99 latency와 slow call rate를 보는가?
- [ ] retry storm을 재현하는 테스트가 있는가?
- [ ] breaker open/half-open/closed 전환 테스트가 있는가?
- [ ] bulkhead 포화 시 request thread pool이 보호되는지 부하 테스트했는가?
- [ ] 장애 상황에서 로그, trace, metric이 같은 dependency 이름으로 연결되는가?

---

## 한줄정리

Java 서비스의 장애 격리는 Resilience4j 어노테이션을 붙이는 일이 아니라, 각 dependency 호출에 대해 **얼마나 기다리고, 언제 재시도하고, 언제 차단하고, 얼마나 격리하고, 어떤 품질 저하를 허용하며, 그 결과를 어떻게 관측할지 정하는 운영 계약**이다.
