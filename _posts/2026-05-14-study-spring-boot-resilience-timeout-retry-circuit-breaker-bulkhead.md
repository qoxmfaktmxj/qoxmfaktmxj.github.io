---
layout: post
title: "Spring Boot 복원력 실전: Timeout, Retry, Circuit Breaker, Bulkhead로 장애를 전파하지 않는 법"
date: 2026-05-14 11:40:00 +0900
categories: [java]
tags: [study, java, spring, spring-boot, resilience4j, timeout, retry, circuit-breaker, bulkhead, backend, operations]
permalink: /java/2026/05/14/study-spring-boot-resilience-timeout-retry-circuit-breaker-bulkhead.html
---

## 배경: 장애는 "실패"보다 "기다림과 재시도" 때문에 더 크게 번진다

Spring Boot 서비스가 운영 단계에 들어가면 진짜 어려운 문제는 코드가 정상 동작하느냐가 아니다. **부분 실패(partial failure)** 를 얼마나 통제 가능한 범위에 가둘 수 있느냐가 더 중요하다.

실무에서 더 자주 보는 사고는 아래와 같다.

- 외부 API 한 군데가 3초 느려졌는데 전체 API p95가 8초까지 치솟는다
- 한 번의 네트워크 흔들림에 retry가 겹치면서 downstream QPS가 3배로 폭증한다
- connection pool은 충분한데 request thread가 대기 상태로 묶여 전체 서버가 질식한다
- 실패율은 높지 않은데도 tail latency가 커져 autoscaling만 계속 돈다
- timeout이 너무 길어 장애 감지가 늦고, 너무 짧아 정상 요청까지 잘려 나간다
- `@Retryable`을 붙였더니 POST 중복 처리, 재고 중복 차감, 외부 결제 중복 승인 같은 더 큰 문제가 생긴다
- fallback을 넣었는데 실제로는 stale data를 조용히 뿌리며 비즈니스 오류를 숨긴다

여기서 중요한 오해 하나가 있다.

> 장애 대응은 예외를 잘 잡는 기술이다.

아니다. 운영에서 복원력(resilience)은 **예외 처리 기술**보다 **용량 보호와 실패 전파 제어 기술**에 가깝다.

즉 아래 질문에 답할 수 있어야 한다.

1. 어느 의존성이 느려지면 우리 요청 예산(latency budget)이 먼저 깨지는가
2. 어떤 실패는 즉시 실패시키고, 어떤 실패만 재시도할 것인가
3. 어느 시점에서 회로를 열어 더 이상 downstream을 두드리지 않아야 하는가
4. thread, connection, in-flight request를 어디서 제한해야 전체 서비스가 살아남는가
5. fallback은 사용자 경험을 지키는 장치인지, 장애를 숨기는 장치인지
6. 각 정책이 실제로 효과가 있는지 어떤 메트릭으로 검증할 것인가

이 글은 중급 이상 개발자를 기준으로 Spring Boot 서비스의 복원력을 **timeout, retry, circuit breaker, bulkhead 중심으로 운영 기준에서** 정리한다. 문법 소개보다 더 중요한 초점은 다음이다.

- 어떤 장애를 어떤 계층에서 끊을지
- 각 패턴이 서로 어떻게 충돌하는지
- 잘못된 기본값이 왜 장애를 증폭시키는지
- 실무에서 바로 적용 가능한 구성과 점검 기준은 무엇인지

이 글의 결론을 먼저 한 줄로 요약하면 이렇다.

> 복원력의 핵심은 "실패를 없애는 것"이 아니라, **느린 의존성과 반복 재시도로부터 내 서비스의 시간·스레드·연결 수를 보호하는 것**이다.

---

## 먼저 큰 그림: 복원력은 에러 핸들링이 아니라 "예산 관리"다

대부분의 팀은 복원력을 예외 처리 관점으로 먼저 본다.

- 실패하면 catch 한다
- 다시 시도한다
- 안 되면 fallback 한다

이 순서 자체가 나쁜 것은 아니다. 하지만 운영 사고는 보통 예외가 던져질 때보다 **예외가 늦게 던져질 때** 더 커진다.

예를 들어 주문 API가 아래 의존성에 순차적으로 의존한다고 하자.

- 인증/권한 조회: 30ms
- 상품 가격 조회: 80ms
- 쿠폰 검증 API: 150ms
- 재고 확인 API: 120ms
- 결제 사전 검증 API: 300ms

정상 시에는 700ms 안팎에 끝난다. 그런데 쿠폰 API가 갑자기 3초씩 느려지면 어떤 일이 벌어질까?

- 요청 하나가 더 오래 살아남는다
- request thread 점유 시간이 늘어난다
- 동시 처리 가능한 요청 수가 감소한다
- upstream 재시도나 사용자 새로고침이 겹친다
- 재시도로 downstream 부하가 다시 증가한다
- 결국 실패율보다 먼저 latency와 saturation이 무너진다

즉 장애는 보통 다음 순서로 전파된다.

1. 일부 downstream이 느려진다
2. timeout이 늦어 요청이 길게 매달린다
3. thread, connection, in-flight request가 쌓인다
4. 재시도가 부하를 증폭시킨다
5. 다른 정상 의존성까지 함께 느려진다
6. 전체 서비스가 실패율과 무관하게 질식한다

그래서 복원력 설계의 첫 번째 질문은 "에러를 어떻게 잡을까"가 아니라 다음이어야 한다.

> **요청 하나가 의존성 하나 때문에 우리 자원을 얼마나 오래 붙잡을 수 있게 둘 것인가?**

이 질문에 답하려면 패턴을 개별 기능으로 보지 말고 하나의 방어선으로 봐야 한다.

- **timeout**: 기다릴 수 있는 최대 시간을 자른다
- **retry**: 재시도 가능한 실패만 제한적으로 다시 시도한다
- **circuit breaker**: 이미 나쁜 의존성을 잠시 우회한다
- **bulkhead**: 특정 의존성이 전체 스레드/동시성을 먹지 못하게 격리한다
- **fallback**: 일부 기능 축소를 통해 핵심 흐름을 살린다

이 다섯 가지를 한 세트로 봐야 한다. 어느 하나만 세게 걸면 오히려 부작용이 커진다.

---

## 핵심 개념 1: Timeout은 네트워크 옵션이 아니라 서비스의 시간 예산이다

팀에서 timeout을 잡을 때 가장 흔한 실수는 "충분히 넉넉하게" 두는 것이다. 이유는 단순하다.

- 너무 짧으면 정상 요청도 실패할까 봐 걱정된다
- 너무 길면 어쨌든 언젠가 응답은 올 것 같아 보인다

운영에서는 대체로 반대다. **길게 기다린 성공**은 시스템 전체 관점에서 실패보다 더 비쌀 수 있다.

### 왜 긴 timeout이 위험한가

예를 들어 servlet 기반 Spring Boot API 서버가 있고, request thread pool이 사실상 Tomcat worker thread에 묶여 있다고 하자. 외부 API timeout을 10초로 두면 다음 일이 가능해진다.

- 사용자 한 요청이 10초 동안 worker thread를 붙잡는다
- 동시 요청 200개만 쌓여도 thread가 금방 고갈된다
- timeout이 지나서야 실패하므로 복구 신호도 늦다
- upstream은 서버가 죽은 줄 알고 또 재시도한다

즉 timeout은 "실패 시점"이 아니라 **자원 해제 시점**이다.

### timeout은 어떻게 잡아야 하나

좋은 기준은 downstream 하나하나를 독립적으로 보는 것이 아니라, **상위 요청의 전체 latency budget을 먼저 정하는 것**이다.

예를 들어 주문 생성 API의 SLO가 아래라고 하자.

- p95 800ms
- p99 1500ms

이때 내부 단계를 대략 이렇게 나눌 수 있다.

- 인증/권한: 100ms
- 재고 조회: 150ms
- 쿠폰 검증: 150ms
- 결제 사전 검증: 250ms
- 내부 DB/직렬화/여유 버퍼: 150ms

그러면 개별 timeout은 "개별 의존성이 최대로 버틸 수 있는 시간"이 아니라 **전체 예산 안에서 줄 수 있는 몫**으로 정해야 한다.

즉 "쿠폰 API는 원래 가끔 2초 걸리니 timeout 3초"가 아니라,

> 주문 API가 800ms 안에 끝나야 한다면 쿠폰 API에 300ms를 줄 수 있는가?

를 먼저 물어야 한다.

### connect timeout과 read timeout을 분리해서 봐야 한다

timeout은 하나가 아니다.

- **connect timeout**: 소켓 연결을 얼마나 기다릴지
- **read/response timeout**: 응답 바이트를 얼마나 기다릴지
- **pool acquire timeout**: connection pool이나 client pool에서 자원을 얼마나 기다릴지
- **overall deadline**: 상위 요청 전체에서 남은 시간

실무에서는 read timeout만 걸고 끝내는 경우가 많은데, 그러면 이미 pool 대기나 connect 대기에서 시간을 다 써버릴 수 있다.

특히 아래 상황은 자주 놓친다.

- HTTP client pool acquire가 500ms 대기
- connect가 200ms
- read가 2초
- 상위 요청 SLA는 1초

코드는 timeout을 걸었다고 생각하지만 실제로는 상위 예산을 이미 넘어섰다.

### Spring Boot에서 흔한 구현 기준

Spring Boot 3 계열에서 `RestClient`나 `WebClient`, 혹은 Apache HttpClient 기반 클라이언트를 쓴다면 최소한 아래를 분리해야 한다.

```java
@Bean
RestClient partnerRestClient(RestClient.Builder builder) {
    var requestConfig = RequestConfig.custom()
            .setConnectionRequestTimeout(Timeout.ofMilliseconds(100))
            .setConnectTimeout(Timeout.ofMilliseconds(200))
            .setResponseTimeout(Timeout.ofMilliseconds(500))
            .build();

    var httpClient = HttpClients.custom()
            .setDefaultRequestConfig(requestConfig)
            .evictExpiredConnections()
            .evictIdleConnections(TimeValue.ofSeconds(30))
            .build();

    return builder
            .requestFactory(new HttpComponentsClientHttpRequestFactory(httpClient))
            .build();
}
```

숫자는 예시일 뿐이지만 메시지는 분명하다.

- pool acquire를 무제한으로 두지 않는다
- connect는 짧게 본다
- read timeout은 상위 예산을 기준으로 자른다
- idle connection 정리와 pool 정책도 함께 본다

### deadline 전파가 더 중요하다

서비스 간 hop이 여러 개면 개별 timeout만으로는 부족하다. 상위 요청에 800ms가 남았는데 하위 서비스가 자기 기준으로 700ms timeout을 또 잡으면, 체인 전체는 금방 예산을 초과한다.

그래서 가능하면 아래 둘 중 하나가 필요하다.

- 요청 컨텍스트에 deadline을 넣고 하위 호출에 남은 시간을 전파
- 최소한 상위 유스케이스별로 의존성 timeout profile을 분리

특히 하나의 `RestClient`를 전 서비스에서 공용으로 쓰면, 조회 API와 결제 API와 배치 API가 같은 timeout을 공유하게 된다. 이것은 편해 보여도 거의 항상 잘못된 추상화다.

---

## 핵심 개념 2: Retry는 "실패 복구" 도구가 아니라 "선별적 재실행" 도구다

retry는 직관적으로 좋아 보인다. 한 번 실패했으니 한 번 더 시도하면 성공할 수 있다. 실제로도 transient failure에서는 효과가 있다.

- 일시적 네트워크 흔들림
- 매우 짧은 upstream failover 순간
- connection reset 같은 간헐 오류
- optimistic locking 충돌처럼 짧은 경쟁 조건

하지만 retry는 비용이 큰 연산이다. 요청 하나를 두 번, 세 번 다시 보내는 순간 downstream 입장에서는 **부하 증폭기**가 된다.

### 언제 retry가 맞는가

아래 세 조건이 동시에 맞을 때만 먼저 검토하는 편이 안전하다.

1. **실패가 일시적(transient)일 가능성이 높다**
2. **호출이 멱등적이거나 멱등성 키로 보호된다**
3. **상위 요청 예산 안에서 재시도해도 의미가 있다**

예를 들어 `GET /inventory/{id}`는 retry 후보가 될 수 있다. 반면 아래는 바로 위험하다.

- 결제 승인 POST
- 쿠폰 사용 POST
- 재고 차감 POST
- 외부 파트너에 side effect를 남기는 요청

이런 요청은 retry 전에 먼저 멱등성 키 설계부터 해야 한다.

### 멱등성 없는 retry가 만드는 사고

가장 흔한 운영 사고는 이것이다.

- 외부 결제 승인 API를 호출했다
- 응답 직전에 네트워크가 끊겼다
- 우리 서비스는 실패로 인식했다
- retry가 다시 승인 요청을 보냈다
- 외부 시스템은 첫 번째 요청을 이미 처리했다

결과는 중복 결제, 중복 주문, 중복 포인트 차감이다.

즉 retry 정책을 코드로 쓰기 전에 먼저 확인해야 할 것은 예외 타입이 아니라 다음이다.

> **이 호출을 다시 보내도 비즈니스적으로 같은 결과로 수렴하는가?**

### backoff와 jitter가 없는 retry는 한꺼번에 죽는다

retry를 켜 놓고 interval을 0ms 또는 고정 100ms로 두는 경우가 많다. 장애 상황에서는 이 구성이 매우 위험하다.

- 동시에 실패한 요청들이 같은 타이밍에 몰린다
- downstream이 회복될 시간을 주지 못한다
- thundering herd를 스스로 만든다

그래서 실무에서는 보통 아래 원칙을 쓴다.

- **소수의 짧은 retry**만 허용한다
- **지수 backoff**를 사용한다
- **jitter**를 넣어 재시도 타이밍을 흩뜨린다
- 총 retry 시간이 상위 deadline을 넘지 않게 한다

예시:

```java
@Bean
Retry inventoryRetry() {
    var config = RetryConfig.custom()
            .maxAttempts(3)
            .intervalFunction(IntervalFunction.ofExponentialRandomBackoff(
                    Duration.ofMillis(80),
                    2.0,
                    0.5
            ))
            .retryExceptions(SocketTimeoutException.class, ConnectException.class)
            .ignoreExceptions(BusinessException.class, IllegalArgumentException.class)
            .failAfterMaxAttempts(true)
            .build();

    return Retry.of("inventoryClient", config);
}
```

여기서 중요한 것은 `maxAttempts=3`보다도 다음이다.

- 무엇을 retry하고
- 무엇을 retry하지 않으며
- 총 대기 시간이 얼마나 되는가

### retry는 계층 하나에서만 하는 편이 안전하다

실무에서 재시도가 폭발하는 대표 패턴은 **중첩 retry**다.

- 클라이언트 SDK가 3번 재시도
- 우리 서비스 코드가 3번 재시도
- API Gateway가 2번 재시도
- 사용자가 새로고침 2번

이 조합이면 최악의 경우 downstream에는 3 × 3 × 2 × 2 = 36개의 요청이 갈 수 있다.

그래서 꼭 정해야 한다.

- retry는 gateway에서 할 것인가
- client SDK에서 할 것인가
- application service에서 할 것인가

모든 계층에서 조금씩 하는 것이 아니라, **가장 문맥을 잘 아는 계층 한 곳에서 제한적으로 하는 것**이 보통 더 낫다.

---

## 핵심 개념 3: Circuit Breaker는 에러율보다 "회복 불가능한 대기"를 차단하는 장치다

circuit breaker를 설명할 때 흔히 "실패율이 높아지면 회로를 연다"고 말한다. 맞지만 절반만 맞다. 운영에서 더 무서운 것은 실패보다 **느린 성공**과 **늦은 실패**다.

예를 들어 downstream이 완전히 죽지 않고, 20%는 100ms, 80%는 4초 걸리는 상태라고 해 보자.

- 실패율만 보면 breaker가 늦게 반응할 수 있다
- 그러나 우리의 worker thread와 connection은 이미 심각하게 묶인다
- 결과적으로 우리 서비스는 failure rate가 아니라 slow call rate 때문에 먼저 죽는다

그래서 circuit breaker를 잡을 때는 아래 두 축을 같이 봐야 한다.

- **failure rate threshold**
- **slow call rate threshold**

### 상태 전이 개념을 운영 관점에서 이해하기

circuit breaker는 보통 아래 상태를 가진다.

- **CLOSED**: 정상적으로 요청을 보냄
- **OPEN**: 일정 시간 동안 아예 요청을 보내지 않음
- **HALF_OPEN**: 일부 probe 요청만 보내 회복 여부를 확인

여기서 중요한 것은 breaker가 "장애를 숨기는 장치"가 아니라 **이미 나쁜 의존성 때문에 내 자원이 계속 소모되는 것을 멈추는 장치**라는 점이다.

### 어떤 단위로 breaker를 나눌 것인가

실무에서 breaker를 너무 크게 잡으면 오작동이 많다.

- `externalApiBreaker` 하나로 모든 파트너 API를 묶는다
- 읽기/쓰기/검색/승인을 모두 같은 breaker에 묶는다

이렇게 하면 한 기능의 장애가 전혀 다른 기능까지 차단한다.

더 나은 기준은 아래다.

- **의존성 + 기능 경로 단위**로 분리한다
- 읽기와 쓰기를 분리한다
- 핵심 경로와 부가 경로를 분리한다

예를 들어 아래처럼 쪼개는 편이 낫다.

- `coupon-validate-breaker`
- `inventory-read-breaker`
- `payment-precheck-breaker`
- `recommendation-read-breaker`

특히 추천, 랭킹, 개인화 같은 부가 기능은 빠르게 열리고 빨리 우회되도록 두는 편이 핵심 주문 흐름 보호에 유리하다.

### Resilience4j 예시

```java
@Bean
CircuitBreaker paymentPrecheckBreaker() {
    var config = CircuitBreakerConfig.custom()
            .slidingWindowType(CircuitBreakerConfig.SlidingWindowType.COUNT_BASED)
            .slidingWindowSize(50)
            .minimumNumberOfCalls(20)
            .failureRateThreshold(50.0f)
            .slowCallDurationThreshold(Duration.ofMillis(400))
            .slowCallRateThreshold(60.0f)
            .waitDurationInOpenState(Duration.ofSeconds(10))
            .permittedNumberOfCallsInHalfOpenState(5)
            .recordExceptions(SocketTimeoutException.class, ConnectException.class)
            .ignoreExceptions(BusinessException.class)
            .build();

    return CircuitBreaker.of("paymentPrecheck", config);
}
```

여기서 눈여겨볼 부분은 `slowCallDurationThreshold`다. 이 값은 그냥 느리다는 느낌이 아니라, **상위 API 예산 안에서 downstream이 소비해도 되는 최대 몫**을 기준으로 잡아야 한다.

### breaker가 있다고 timeout을 늦춰도 되는가

아니다. breaker는 timeout의 대체재가 아니다.

- timeout이 없으면 개별 호출이 너무 오래 붙든다
- breaker는 충분한 실패 표본이 쌓여야 열린다
- 첫 번째 느린 요청들에 대한 자원 보호는 timeout이 담당한다

정리하면,

- **timeout은 한 요청을 자르는 장치**
- **breaker는 여러 요청 패턴을 보고 의존성 자체를 잠시 우회하는 장치**

둘은 역할이 다르다.

---

## 핵심 개념 4: Bulkhead는 thread pool 장난이 아니라 "전파 반경 제한"이다

복원력에서 가장 과소평가되는 패턴이 bulkhead다. 이유는 retry와 circuit breaker가 더 화려해 보이기 때문이다. 그런데 실제 운영에서 전체 서비스 생존성에 제일 직접적인 영향을 주는 것은 bulkhead인 경우가 많다.

### 왜 bulkhead가 필요한가

서비스가 여러 의존성을 동시에 호출한다고 해 보자.

- 주문 핵심 경로: 재고, 결제 사전 검증
- 부가 경로: 추천, 리뷰 요약, 배너, 개인화

이때 추천 API가 느려졌다고 해서 주문 핵심 경로까지 같은 worker 자원을 놓고 경쟁하면 안 된다. 그런데 별도 격리가 없으면 실제로 그렇게 된다.

- servlet thread가 추천 응답을 기다리며 오래 묶인다
- 부가 기능 호출이 동시성을 먹는다
- 핵심 경로 요청도 줄을 선다

즉 bulkhead의 목적은 실패를 막는 것이 아니라,

> **특정 의존성의 느림이 전체 서비스 용량을 잠식하지 못하게 하는 것**

이다.

### semaphore bulkhead와 thread-pool bulkhead

Resilience4j 기준으로 크게 두 종류를 생각할 수 있다.

1. **Semaphore Bulkhead**
   - 동시 실행 수를 제한
   - 가볍고 단순함
   - 같은 스레드 모델 안에서 in-flight 개수만 제한할 때 적합

2. **Thread Pool Bulkhead**
   - 별도 큐와 스레드 풀로 격리
   - 비동기/별도 실행 경계가 필요한 경우 유용
   - 잘못 쓰면 큐 적체를 숨기기 쉽다

servlet 기반 동기 애플리케이션에서는 먼저 질문해야 한다.

- 이미 Tomcat worker thread가 요청을 처리 중인데, downstream 호출마다 또 별도 thread pool을 만드는 것이 진짜 필요한가?

많은 경우 답은 아니다. 이중 큐잉과 컨텍스트 전환만 늘어난다. 그래서 동기 호출 경로에서는 보통 아래 전략이 더 낫다.

- request 자체는 기존 worker에서 처리
- 특정 dependency 호출 수만 semaphore로 제한
- 제한 초과 시 빠르게 실패 또는 degraded fallback

예시:

```java
@Bean
Bulkhead recommendationBulkhead() {
    var config = BulkheadConfig.custom()
            .maxConcurrentCalls(20)
            .maxWaitDuration(Duration.ofMillis(0))
            .build();

    return Bulkhead.of("recommendation", config);
}
```

이 설정의 의미는 분명하다.

- 추천 API는 동시 20개까지만 허용
- 넘치면 기다리지 않고 즉시 차단
- 핵심 주문 경로의 자원을 끝없이 잠식하지 못하게 함

### queue는 완충장치가 아니라 지연 저장소가 될 수 있다

팀들이 thread-pool bulkhead를 쓰면서 자주 저지르는 실수는 큐를 넉넉하게 잡는 것이다.

- core 20
- max 50
- queue 1000

겉으로는 안정적이다. 실제로는 장애를 늦게 드러낸다.

- 요청은 거절되지 않지만 오래 큐에서 대기한다
- 사용자 체감 latency는 급증한다
- 시스템은 이미 과부하인데 metrics는 한참 뒤에야 실패로 보인다

운영 시스템에서는 **짧은 큐 + 빠른 거절**이 종종 더 건강하다. 거절된 요청은 적어도 장애 신호를 빨리 만들고, 핵심 경로 자원을 지킨다.

---

## 핵심 개념 5: Fallback은 UX를 살릴 수 있지만, 정합성까지 대신해 주지는 않는다

fallback은 복원력 패턴 중 가장 오해가 많은 도구다. 화면이 예쁘게 내려오고 에러 페이지가 줄어드니 좋아 보인다. 하지만 fallback은 잘못 설계하면 장애를 조용히 숨긴다.

### fallback이 유효한 경우

다음처럼 **정확하지 않아도 되는 정보**에는 fallback이 유용하다.

- 추천 상품 대신 베스트셀러 목록 보여주기
- 개인화 배너 대신 기본 배너 보여주기
- 리뷰 요약 대신 "리뷰를 불러오지 못했습니다" 표시
- 환율 캐시나 랭킹 캐시처럼 짧은 stale 허용

### fallback이 위험한 경우

반대로 아래는 fallback이 아니라 **도메인 오류 은폐**가 되기 쉽다.

- 재고 확인 실패 시 "재고 있음"으로 간주
- 쿠폰 검증 실패 시 "할인 가능"으로 처리
- 결제 사전 검증 실패 시 그냥 승인 흐름 진행
- 권한 조회 실패 시 기본 권한 부여

이런 fallback은 장애를 줄이는 게 아니라, 잘못된 비즈니스 결과를 만든다.

### stale data fallback의 운영 기준

캐시 fallback을 쓸 때는 반드시 아래를 명시해야 한다.

- stale 허용 기간은 얼마인가
- 어떤 화면/업무에서만 허용되는가
- stale 응답임을 내부적으로 식별 가능한가
- 메트릭과 로그에서 fallback 비율을 볼 수 있는가

즉 fallback은 "있으면 좋다"가 아니라 **정확도 손실을 어디까지 용인할지 문서화된 정책**이어야 한다.

---

## 핵심 개념 6: 패턴을 섞는 순서가 중요하다 — Timeout → Bulkhead → Retry → Circuit Breaker

복원력 패턴은 순서가 바뀌면 부작용이 크게 달라진다. 실무에서 자주 권하는 기본 사고 순서는 이렇다.

1. **timeout**으로 한 요청의 대기 상한을 자른다
2. **bulkhead**로 동시성 소비량을 제한한다
3. **retry**는 정말 필요한 실패에만 짧게 붙인다
4. **circuit breaker**로 나쁜 상태가 지속될 때 아예 우회한다
5. 필요 시 **fallback**으로 기능 축소 응답을 준다

왜 이런 순서인가?

- timeout이 없으면 retry와 breaker 모두 늦게 반응한다
- bulkhead가 없으면 느린 의존성이 전체 자원을 먹는다
- retry를 먼저 세게 걸면 부하만 증폭한다
- breaker는 패턴이 누적된 뒤에야 의미가 있다

### 잘못된 조합 예시

가장 위험한 조합 중 하나는 아래다.

- read timeout 3초
- retry 3회
- queue 500
- circuit breaker minimumNumberOfCalls 100

이 조합은 장애 초반에 거의 무방비다.

- 요청 하나가 최악의 경우 9초 이상 매달림
- 큐에 오래 대기
- breaker는 100건 쌓일 때까지 늦게 열림
- 이미 서비스는 질식 상태

반대로 아래는 훨씬 방어적이다.

- response timeout 300~500ms
- semaphore bulkhead로 동시성 제한
- retry 1회 또는 2회, jitter 포함
- slow call rate 기반 breaker
- 부가 기능에만 fallback

정답 숫자는 서비스마다 다르지만 철학은 같다.

> **오래 버티는 성공보다, 빨리 포기하는 실패가 전체 시스템을 더 오래 살린다.**

---

## 실무 예시: 주문 API에서 추천·쿠폰·재고 의존성을 함께 다룰 때

이제 조금 더 현실적인 예시를 보자. 주문 상세 화면 API가 아래를 호출한다고 하자.

- 주문 조회 DB
- 재고 가용성 API
- 쿠폰 추천 API
- 개인화 추천 API

초기 구현은 흔히 이렇다.

```java
@Service
@RequiredArgsConstructor
public class OrderDetailService {
    private final OrderRepository orderRepository;
    private final InventoryClient inventoryClient;
    private final CouponClient couponClient;
    private final RecommendationClient recommendationClient;

    public OrderDetailResponse getOrderDetail(Long orderId, Long userId) {
        Order order = orderRepository.findById(orderId)
                .orElseThrow(() -> new OrderNotFoundException(orderId));

        InventoryAvailability inventory = inventoryClient.getAvailability(order.getProductId());
        CouponSuggestion coupon = couponClient.getSuggestion(userId, order.getProductId());
        Recommendation recommendation = recommendationClient.getRecommendation(userId);

        return OrderDetailResponse.of(order, inventory, coupon, recommendation);
    }
}
```

정상 시에는 잘 돌아간다. 하지만 추천 API가 느려지면 주문 상세 전체가 느려진다. 쿠폰 API 장애가 길어지면 request thread가 계속 묶인다. 재고 API 오류가 순간적으로 나면 전체 화면이 500이 된다.

### 1) dependency별 중요도를 먼저 나눈다

이 시점에서 먼저 해야 할 일은 기술 선택이 아니라 **비즈니스 중요도 분리**다.

- 주문 조회: 핵심, 실패 시 전체 실패
- 재고 가용성: 핵심에 가깝지만 짧은 실패 허용 정책 필요
- 쿠폰 추천: 부가 기능, degraded 가능
- 개인화 추천: 부가 기능, fallback 가능

이 분리 없이는 모든 의존성에 같은 retry, 같은 timeout, 같은 breaker를 붙이게 된다. 그것이야말로 가장 흔한 안티패턴이다.

### 2) 클라이언트마다 timeout과 breaker를 분리한다

예를 들어 정책을 이렇게 나눌 수 있다.

- inventory: timeout 200ms, retry 1회, fallback 없음 또는 "확인 불가"
- coupon suggestion: timeout 150ms, retry 없음, fallback 빈 응답
- recommendation: timeout 120ms, bulkhead 20, breaker 빠르게 open, fallback 베스트셀러

이렇게 **업무 중요도와 SLA에 맞춰 의존성별 budget을 따로 잡는 것**이 핵심이다.

### 3) 코드 예시

```java
@Service
@RequiredArgsConstructor
public class OrderDetailService {
    private final OrderRepository orderRepository;
    private final InventoryFacade inventoryFacade;
    private final CouponFacade couponFacade;
    private final RecommendationFacade recommendationFacade;

    public OrderDetailResponse getOrderDetail(Long orderId, Long userId) {
        Order order = orderRepository.findById(orderId)
                .orElseThrow(() -> new OrderNotFoundException(orderId));

        InventoryAvailability inventory = inventoryFacade.fetch(order.getProductId());
        CouponSuggestion coupon = couponFacade.fetchOrEmpty(userId, order.getProductId());
        Recommendation recommendation = recommendationFacade.fetchOrDefault(userId);

        return OrderDetailResponse.of(order, inventory, coupon, recommendation);
    }
}
```

```java
@Component
@RequiredArgsConstructor
public class RecommendationFacade {
    private final RecommendationClient client;
    private final CircuitBreaker breaker;
    private final Bulkhead bulkhead;

    public Recommendation fetchOrDefault(Long userId) {
        Supplier<Recommendation> supplier = () -> client.getRecommendation(userId);

        Supplier<Recommendation> protectedCall = Decorators.ofSupplier(supplier)
                .withBulkhead(bulkhead)
                .withCircuitBreaker(breaker)
                .decorate();

        try {
            return protectedCall.get();
        } catch (BulkheadFullException | CallNotPermittedException ex) {
            return Recommendation.defaultItems();
        } catch (Exception ex) {
            return Recommendation.defaultItems();
        }
    }
}
```

이 예시는 단순해 보이지만 의도가 분명하다.

- 추천 기능은 핵심 주문 흐름을 막지 않는다
- 추천 의존성의 느림은 bulkhead로 격리한다
- breaker가 열리면 더 이상 downstream을 두드리지 않는다
- fallback은 베스트셀러 같은 안전한 대체값으로 한정한다

반면 재고 확인은 같은 방식으로 다루면 안 된다. 재고는 잘못된 fallback이 비즈니스 오류를 만들기 때문이다.

### 4) 재고 확인은 빠른 실패와 명시적 상태가 더 낫다

재고 API가 확인 불가일 때의 정책은 아래처럼 더 보수적이어야 한다.

- 주문 확정 직전이면 실패 처리
- 상세 화면이면 `availability=UNKNOWN`으로 명시
- 운영에서는 UNKNOWN 비율을 메트릭으로 추적

즉 fallback은 "항상 기본값"이 아니라 **도메인이 허용하는 축소 결과**여야 한다.

---

## 핵심 개념 7: Observability 없이는 복원력 설정이 아니라 민간요법이다

복원력 패턴은 값만 넣는다고 끝나지 않는다. 실제로 효과가 있는지 봐야 한다. 그렇지 않으면 timeout이 너무 짧은지, breaker가 너무 민감한지, retry가 과한지 알 수 없다.

최소한 아래 메트릭은 의존성별로 분리해서 봐야 한다.

### 1) latency 분포

- 평균보다 p95, p99가 중요하다
- 성공 latency와 실패 latency를 분리해서 봐야 한다
- retry 포함 후의 end-to-end latency도 따로 봐야 한다

### 2) outcome 분포

- success
- timeout
- connection error
- bulkhead reject
- circuit open reject
- fallback served

이 구분이 없으면 그냥 500 개수만 보고 끝나는데, 복원력 튜닝에는 거의 도움이 안 된다.

### 3) saturation 지표

- thread pool active count
- queue depth
- connection pool pending acquire
- bulkhead concurrent call count
- breaker open 상태 비율

복원력은 결국 자원 보호이기 때문에 saturation 지표가 핵심이다.

### 4) retry 증폭률

운영에서 꼭 봐야 하는 지표 중 하나가 이것이다.

- 원 요청 수 대비 실제 outbound request 수

예를 들어 사용자 요청 1만 건인데 outbound call이 2만 5천 건이면, retry나 fan-out 때문에 증폭이 일어나고 있다는 뜻이다.

### Micrometer 태깅 기준 예시

- dependency=`inventory`
- operation=`getAvailability`
- outcome=`success|timeout|open|bulkhead_reject|fallback`
- attempt=`1|2|3`

이 정도만 잘 잡아도 "느려서 실패한 것인지", "회로가 열려서 즉시 거절된 것인지", "재시도가 응답시간을 얼마나 늘렸는지"가 보인다.

---

## 핵심 개념 8: 읽기 경로와 쓰기 경로는 같은 복원력 정책을 쓰면 안 된다

실무에서 많이 놓치는 경계가 하나 더 있다. **조회(read) 경로와 명령(write/side effect) 경로는 실패 비용이 다르다.** 그런데 팀에서 복원력 공통 모듈을 만들 때 둘을 같은 `Retry`, 같은 timeout, 같은 fallback 규칙으로 묶는 경우가 많다.

### 조회 경로의 기본 철학

조회 경로는 대체로 아래 특성을 가진다.

- 멱등적이다
- 일부 데이터가 빠져도 화면 축소 응답이 가능하다
- 부가 기능은 stale/fallback 허용 여지가 있다
- 사용자 재시도가 자연스럽게 발생한다

그래서 조회 경로에서는 다음이 비교적 자연스럽다.

- 짧은 timeout
- 소수의 retry
- 빠른 breaker open
- fallback 또는 partial response
- aggressive bulkhead

### 쓰기 경로의 기본 철학

반면 쓰기 경로는 다르다.

- side effect가 생긴다
- 중복 실행 비용이 크다
- "부분 성공 후 응답 실패"가 더 위험하다
- fallback이 도메인 오류를 만들기 쉽다

예를 들어 결제 승인, 쿠폰 사용, 재고 차감은 "한 번 더 시도하면 되지"가 성립하지 않는다. 이 경로는 복원력의 중심이 retry가 아니라 다음에 있어야 한다.

- **멱등성 키**
- **명령 상태 추적**
- **명확한 timeout과 실패 반환**
- **비동기 보상 또는 재처리 전략**
- **outbox/inbox 같은 정합성 패턴**

즉 읽기 경로의 복원력은 주로 "서비스를 계속 보여 주는 능력"이고, 쓰기 경로의 복원력은 주로 **중복 없이 실패를 복구 가능한 상태로 남기는 능력**이다.

### 왜 같은 retry 정책이 위험한가

아래와 같은 공통 설정은 겉보기에는 깔끔하다.

```java
RetryConfig commonRetry = RetryConfig.custom()
        .maxAttempts(3)
        .waitDuration(Duration.ofMillis(100))
        .build();
```

하지만 실제로는 다음을 한데 묶어 버린다.

- 상품 조회 GET
- 배송비 계산 GET
- 결제 승인 POST
- 포인트 차감 POST

이렇게 되면 "공통화"가 아니라 **업무 의미 제거**가 된다.

내 기준으로는 다음처럼 나누는 편이 더 안전하다.

- **read profile**: 짧은 timeout + 제한적 retry + fallback 가능
- **write profile**: 더 보수적인 timeout + inline retry 최소화 + 멱등성 필수 + fallback 금지
- **async processing profile**: 사용자 응답 경로 밖에서 queue 기반 재처리, DLQ, 보상 프로세스 적용

즉 복원력은 기술 공통화보다 **업무 경로 분류**가 먼저다.

---

## 실무 예시 2: 결제 승인 경로에서는 "재시도"보다 "멱등성과 상태 머신"이 먼저다

복원력 이야기를 하다 보면 팀이 제일 먼저 묻는 질문이 있다.

> 결제 승인 API가 timeout 나면 한 번 더 때리면 안 되나?

답은 "그 전에 먼저 확인할 것이 훨씬 많다"다.

### 나쁜 구현 예시

```java
@Transactional
public PaymentResult approve(PaymentCommand command) {
    Payment payment = paymentRepository.save(Payment.pending(command));

    ApprovalResponse response = pgClient.approve(command.orderId(), command.amount());

    payment.approve(response.approvalId());
    return PaymentResult.success(payment.getId());
}
```

이 코드의 위험은 여러 가지다.

- PG 호출과 DB 트랜잭션이 한 덩어리로 묶여 있다
- 외부 호출이 느리면 DB connection과 락을 오래 잡을 수 있다
- 응답 직전에 네트워크가 끊기면 PG는 성공, 우리는 실패로 인식할 수 있다
- 이 상태에서 inline retry를 걸면 중복 승인 가능성이 생긴다

### 더 나은 기준

결제 같은 쓰기 경로는 아래 질문을 먼저 정리해야 한다.

1. 외부 파트너가 **idempotency key**를 지원하는가
2. 우리 쪽에서 같은 key로 중복 명령을 식별할 수 있는가
3. 승인 요청의 현재 상태를 `PENDING`, `APPROVED`, `FAILED`, `UNKNOWN` 등으로 남길 수 있는가
4. 응답을 못 받아도 나중에 **상태 조회** 또는 **정산 대사**로 복구 가능한가

즉 이 경로에서 복원력은 retry보다 **상태 머신 설계**와 더 가깝다.

### 추천 흐름 예시

1. 내부적으로 `payment_request_id`를 만든다
2. 이를 idempotency key로 PG에 전달한다
3. 호출 timeout이 나도 즉시 같은 요청을 무작정 재전송하지 않는다
4. 상태를 `UNKNOWN` 또는 `PENDING_CONFIRMATION`으로 남긴다
5. 별도 조회 API, webhook, reconciliation job으로 최종 상태를 확인한다

예시 스케치:

```java
public PaymentResult approve(PaymentCommand command) {
    Payment payment = paymentRepository.createPending(command);

    try {
        ApprovalResponse response = pgClient.approve(
                payment.getRequestId(),
                command.orderId(),
                command.amount()
        );

        paymentRepository.markApproved(payment.getId(), response.approvalId());
        return PaymentResult.approved(payment.getId());
    } catch (SocketTimeoutException ex) {
        paymentRepository.markUnknown(payment.getId(), ex.getMessage());
        return PaymentResult.pendingConfirmation(payment.getId());
    }
}
```

이 방식은 겉보기에는 덜 화려하다. 사용자는 즉시 확정 응답을 못 받을 수도 있다. 하지만 운영 관점에서는 더 건강하다.

- 중복 승인 위험을 줄인다
- 나중에 상태 복구 가능한 기록을 남긴다
- "실패인지 성공인지 모르는 상태"를 정직하게 모델링한다

복원력의 중요한 원칙 중 하나는 이것이다.

> **불확실한 성공을 확실한 실패처럼 다루지 말고, 불확실한 상태 자체를 모델링하라.**

### 이때 retry는 어디로 가는가

결제 승인 같은 경로에서 retry가 완전히 사라지는 것은 아니다. 다만 위치가 바뀐다.

- 사용자 동기 응답 경로에서는 inline retry를 최소화
- 비동기 확인 작업이나 reconciliation job에서 제한적으로 재조회
- 파트너가 안전한 idempotent replay를 지원할 때만 명시적으로 재전송

즉 쓰기 경로의 복원력은 "즉시 다시 때리기"보다 **안전하게 재개 가능한 상태를 남기는 것**이 우선이다.

---

## 검증 방법: 복원력 설정은 로컬 성공이 아니라 실패 주입으로 검증해야 한다

timeout, retry, breaker, bulkhead를 넣었더라도 실제 장애에서 기대대로 동작하는지는 별개의 문제다. 복원력은 정상 플로우 테스트만으로는 검증되지 않는다.

### 1) 느린 성공을 의도적으로 만든다

가장 먼저 해야 할 테스트는 500 에러보다 **느린 성공**이다.

- downstream 응답을 100ms, 300ms, 800ms, 2s로 인위적으로 지연
- 어느 지점에서 timeout이 발생하는지 확인
- slow call rate가 breaker에 반영되는지 확인
- fallback이 의도한 경로에서만 동작하는지 확인

느린 성공은 운영에서 훨씬 흔하고, 자원 보호 관점에서도 더 치명적이다.

### 2) 오류 타입을 나눠서 주입한다

- connect timeout
- read timeout
- TCP reset
- HTTP 429
- HTTP 500
- business 4xx

이들을 한 묶음으로 보면 안 된다. 예를 들어 429는 backoff 정책이 중요하고, 400 계열 business error는 retry 대상이 아니며, connect timeout은 network/transient 성격일 가능성이 있다.

### 3) 부하와 함께 본다

복원력 설정은 단건 호출 테스트보다 **동시 부하**에서 의미가 드러난다.

- 동시 요청 50, 100, 300으로 올렸을 때 bulkhead reject가 예상대로 생기는가
- reject가 생겨도 핵심 경로 p95는 방어되는가
- retry 때문에 outbound request 수가 몇 배로 증가하는가
- queue depth, Tomcat active thread, DB pool pending이 어떻게 변하는가

### 4) 성공률만 보지 말고 회복 시간도 본다

breaker를 넣은 뒤에는 장애 종료 후 얼마나 빨리 정상으로 복귀하는지도 중요하다.

- open 상태가 너무 오래 유지되지는 않는가
- half-open probe 수가 너무 적거나 많지 않은가
- 회복 직후 retry storm이 다시 발생하지 않는가

### 5) 대시보드와 알람을 패턴별로 나눈다

운영에서 유용한 알람 예시는 이런 식이다.

- `dependency=inventory, outcome=timeout` 비율 급증
- `dependency=recommendation, outcome=bulkhead_reject` 비율 급증
- `dependency=payment, circuit_state=open` 지속 시간 증가
- `outbound_calls / inbound_requests` 비율 급증

이 정도까지 가야 복원력 설정이 실제 운영 장치가 된다.

---

## 트레이드오프: 복원력 패턴은 안정성과 정확도, 비용 사이의 교환이다

복원력 이야기를 할 때 종종 "이 패턴을 넣으면 더 좋아진다"는 식으로 단선적으로 말한다. 실무에서는 항상 교환이 있다.

### 1) 짧은 timeout vs 정상 요청 절단 위험

- timeout을 짧게 잡으면 자원 보호는 좋아진다
- 하지만 tail latency가 원래 큰 downstream에서는 정상 요청도 잘릴 수 있다
- 결국 SLA와 비즈니스 중요도에 따라 조정해야 한다

### 2) retry 성공률 개선 vs 부하 증폭

- 짧은 network glitch에는 retry가 효과적이다
- 그러나 장애가 지속될 때는 downstream을 더 빨리 무너뜨린다
- retry는 성공률을 올리는 동시에 비용을 늘리는 장치다

### 3) aggressive breaker vs false open

- 빠르게 회로를 열면 자원은 보호된다
- 대신 일시적 흔들림에도 너무 빨리 degraded 상태로 들어갈 수 있다
- 핵심 경로와 부가 경로의 민감도를 다르게 잡아야 한다

### 4) fallback UX 개선 vs 데이터 정확도 저하

- 사용자 경험은 부드러워진다
- 대신 stale/partial data가 늘어난다
- 어느 업무에 stale 허용이 가능한지 도메인 합의가 필요하다

### 5) 격리 강화 vs 운영 복잡도 증가

- dependency별 client, breaker, metrics, alert를 나누면 안정성은 좋아진다
- 하지만 설정 수가 늘고 운영 복잡도도 증가한다
- 따라서 모든 API를 같은 수준으로 분리할 필요는 없고, 핵심/고위험 의존성부터 시작하는 편이 낫다

---

## 흔한 실수: 패턴은 넣었는데 오히려 장애가 더 커지는 경우

아래는 실제로 매우 자주 보는 실수들이다.

### 1) timeout보다 retry 횟수를 먼저 늘린다

장애 상황에서 "한 번 더 해 보자"는 직관은 강하다. 하지만 timeout이 길면 retry는 느린 실패를 여러 번 반복하는 것뿐이다.

### 2) POST에도 무조건 retry를 건다

멱등성 키 없이 side effect 호출을 재전송하는 것은 복원력이 아니라 사고 유발이다.

### 3) breaker를 dependency 전체에 하나만 둔다

검색 API 문제 때문에 결제 검증까지 막히는 식의 과도한 차단이 생긴다.

### 4) fallback을 너무 낙관적으로 둔다

재고 확인 실패 시 재고 있음으로 간주하는 식의 fallback은 장애보다 더 큰 비즈니스 피해를 만든다.

### 5) bulkhead 큐를 크게 둔다

겉보기 성공률은 유지되지만 실제 사용자 경험은 급격히 악화된다. 긴 큐는 종종 실패를 늦게 드러내는 장치다.

### 6) 재시도를 여러 계층에서 동시에 켠다

gateway, SDK, application, client가 모두 retry하면 downstream이 제일 먼저 죽는다.

### 7) metrics 없이 값만 복붙한다

다른 팀 블로그에서 가져온 `timeout=2s`, `failureRate=50%`, `maxConcurrentCalls=25`는 대개 맥락이 없다. 메트릭 없이 쓰면 그냥 숫자 장식이다.

### 8) 비즈니스 예외와 시스템 예외를 구분하지 않는다

재고 부족, 권한 없음, 잘못된 입력 같은 예외는 retry 대상이 아니다. 이런 예외까지 같은 버킷에 넣으면 breaker가 불필요하게 열린다.

---

## 운영 체크리스트: Spring Boot 서비스 복원력 점검 항목

배포 전이나 장애 회고 때 아래 항목을 체크하면 좋다.

### 기본 구조

- [ ] 핵심 경로와 부가 경로를 구분했는가
- [ ] 의존성별 latency budget이 문서화되어 있는가
- [ ] 공용 HTTP client 하나에 모든 timeout을 몰아넣지 않았는가

### Timeout

- [ ] connect, pool acquire, response timeout을 분리했는가
- [ ] timeout 값이 상위 API SLO 안에서 설명 가능한가
- [ ] 너무 긴 timeout 때문에 worker thread가 오래 묶이지 않는가

### Retry

- [ ] retry 대상 예외가 transient failure로 한정되어 있는가
- [ ] POST/side effect 호출은 멱등성 키 없이는 retry하지 않는가
- [ ] retry 횟수, backoff, jitter가 설정되어 있는가
- [ ] 여러 계층에서 중첩 retry가 일어나지 않는가

### Circuit Breaker

- [ ] dependency + operation 단위로 breaker를 나눴는가
- [ ] failure rate뿐 아니라 slow call rate도 보고 있는가
- [ ] 핵심 경로와 부가 경로의 breaker 민감도가 같은 값으로 묶여 있지 않은가

### Bulkhead

- [ ] 느린 부가 기능이 핵심 경로 자원을 잠식하지 못하도록 격리했는가
- [ ] 큐 길이가 과도하지 않은가
- [ ] reject가 발생했을 때 빠르게 degrade할 수 있는가

### Fallback

- [ ] fallback이 비즈니스 오류를 숨기지 않는가
- [ ] stale/partial 응답 허용 범위가 명시되어 있는가
- [ ] fallback 비율을 메트릭으로 관측할 수 있는가

### Observability

- [ ] dependency별 p95/p99 latency를 보는가
- [ ] timeout/open/reject/fallback outcome을 구분하는가
- [ ] outbound call amplification 비율을 보는가
- [ ] bulkhead saturation, pool pending, breaker state를 대시보드로 확인 가능한가

---

## 적용 순서 제안: 팀에서 복원력을 도입할 때 어디서부터 시작할까

복원력 패턴을 한 번에 다 넣으려 하면 실패한다. 내 기준으로는 아래 순서가 가장 현실적이다.

### 1단계: timeout과 관측부터 정리

가장 먼저 해야 할 일은 retry나 breaker가 아니라 timeout과 메트릭이다.

- dependency별 timeout 분리
- p95/p99 측정
- timeout, connection error, slow call 비율 수집

이 단계 없이 다른 패턴을 넣으면 튜닝 근거가 없다.

### 2단계: 부가 기능부터 bulkhead와 fallback 적용

추천, 배너, 개인화, 리뷰 요약 같은 부가 기능은 복원력 패턴 효과를 보기 좋다.

- 핵심 경로를 막지 않도록 격리
- degrade UX를 설계하기 쉬움
- false open의 리스크가 상대적으로 낮음

### 3단계: 핵심 쓰기 경로는 멱등성과 빠른 실패 기준부터

주문, 결제, 쿠폰 사용, 재고 차감 같은 쓰기 경로는 retry보다 먼저 다음을 확보해야 한다.

- 멱등성 키
- 중복 처리 방지
- 실패 시 재시도 책임 주체 정의
- 정확한 timeout과 회복 프로토콜

### 4단계: breaker 임계값을 실측 기반으로 조정

처음부터 완벽한 threshold는 없다.

- 정상 주간 트래픽
- 피크 시간대
- 장애 리허설 또는 chaos 테스트

를 통해 threshold를 조정해야 한다.

---

## 한 줄 정리

> Spring Boot 복원력의 핵심은 예외를 예쁘게 처리하는 것이 아니라, **느린 의존성과 무분별한 재시도로부터 내 서비스의 시간 예산·동시성·정합성을 보호하도록 timeout, retry, circuit breaker, bulkhead를 역할별로 분리해 설계하는 것**이다.
