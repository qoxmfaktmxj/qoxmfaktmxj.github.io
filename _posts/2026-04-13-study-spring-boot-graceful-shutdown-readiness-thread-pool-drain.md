---
layout: post
title: "Spring Boot Graceful Shutdown 실전: SIGTERM, Readiness, Thread Pool Drain으로 배포 중 요청 유실 줄이는 법"
date: 2026-04-13 11:40:00 +0900
categories: [java]
tags: [study, java, spring, spring-boot, graceful-shutdown, kubernetes, readiness, thread-pool, backend, operations]
permalink: /java/2026/04/13/study-spring-boot-graceful-shutdown-readiness-thread-pool-drain.html
---

## 배경: 왜 배포할 때만 간헐적인 502, 타임아웃, 중복 실행이 터질까?

운영 중인 Spring Boot 서비스를 배포할 때 아래 현상을 겪는 팀이 많다.

- 롤링 배포 중 일부 요청이 502나 connection reset으로 실패한다
- 사용자는 결제를 눌렀는데 응답은 실패했고, 서버 로그를 보면 실제로는 처리된 것처럼 보인다
- `@Async` 작업이 중간에 사라지거나, 반대로 재시도 로직과 겹쳐 중복 실행된다
- Kafka consumer나 스케줄러가 내려가는 동안 마지막 메시지 처리 상태가 불분명해진다
- Kubernetes에서는 Pod가 종료됐다고 생각했는데, ALB나 Ingress에서는 한동안 계속 트래픽이 들어온다

이 문제는 단순히 "서버를 천천히 끄면 된다" 수준이 아니다. 실제 원인은 대개 세 가지 층위가 엉켜 있다.

1. **프로세스 종료 시점**을 애플리케이션이 어떻게 해석하는가
2. **트래픽 차단 시점**과 **실제 종료 시점** 사이의 간극을 어떻게 메우는가
3. **진행 중인 작업**(HTTP 요청, 비동기 작업, 메시지 처리, 배치, DB 트랜잭션)을 어디까지 완료하고 어디서 끊을 것인가

즉 graceful shutdown은 설정 한 줄 문제가 아니라 **종료 프로토콜 설계** 문제다.

중급 이상 개발자라면 아래를 분리해서 이해해야 한다.

- `SIGTERM`을 받았을 때 Spring Boot는 정확히 무엇을 하는가
- `server.shutdown=graceful`만 켜면 정말 안전한가
- readiness probe와 load balancer deregistration 사이의 시간차를 어떻게 흡수할 것인가
- Tomcat/Undertow/Netty의 요청 종료 동작은 무엇이 다른가
- `ThreadPoolTaskExecutor`, `@Scheduled`, MQ consumer, 배치 작업은 웹 요청 종료와 왜 다른 기준이 필요한가
- graceful shutdown 시간을 길게 잡는 것이 항상 좋은 선택이 아닌 이유는 무엇인가

이 글은 Spring Boot 기반 서비스를 기준으로 **배포 중 요청 유실을 줄이고, 종료 시 정합성을 높이는 실무 패턴**을 정리한다.

---

## 먼저 큰 그림: 종료는 "프로세스를 죽이는 일"이 아니라 "새 요청 중단 → 진행 중 작업 정리 → 자원 반납" 순서다

graceful shutdown을 제대로 설계하려면 종료를 3단계로 봐야 한다.

### 1) 새 요청을 더 이상 받지 않는다

가장 먼저 해야 할 일은 이 인스턴스를 **트래픽 대상에서 제외**하는 것이다.

- Kubernetes readiness probe 실패 처리
- Service/Endpoint 제거
- ALB, Nginx, Ingress, Service Mesh의 라우팅 제외
- 내부 클라이언트가 connection pool에서 해당 인스턴스를 더 이상 선택하지 않도록 유도

이 단계가 빠지면 애플리케이션이 종료 절차에 들어가도 계속 새 요청이 들어온다.

### 2) 이미 시작된 작업은 정책에 따라 정리한다

이 단계가 진짜 어렵다. 모든 작업을 무조건 끝까지 기다리는 것이 정답은 아니다.

- 30ms짜리 API는 잠깐 기다리면 대부분 자연 종료된다
- 40초짜리 리포트 생성 API는 끝까지 기다리면 배포 시간이 과도하게 늘어난다
- MQ consumer는 offset commit 시점에 따라 중복 처리와 유실 가능성이 달라진다
- `@Async` 작업은 큐에 쌓인 작업까지 기다릴지, 실행 중인 작업만 기다릴지 판단해야 한다

즉 서비스마다 **종료 허용 시간과 중단 정책**이 달라야 한다.

### 3) 마지막으로 자원을 반납하고 프로세스를 끝낸다

- DB connection pool close
- 메시지 consumer stop
- executor shutdown
- metric flush, log drain
- 애플리케이션 컨텍스트 종료

중요한 점은, 1번이 충분히 앞서지 않으면 2번이 끝날 기회가 없다는 것이다. 많은 장애가 여기서 나온다.

> graceful shutdown의 본질은 "종료를 늦추는 것"이 아니라, **종료 전에 더 이상 새 일을 받지 않도록 시스템 전체를 정렬하는 것**이다.

---

## 핵심 개념 1: `SIGTERM`과 `SIGKILL`을 구분하지 못하면 graceful shutdown은 절반만 이해한 것이다

리눅스, 컨테이너, Kubernetes 환경에서 종료 시퀀스는 보통 아래 흐름으로 진행된다.

1. 오케스트레이터나 운영자가 프로세스 종료 요청
2. 프로세스에 `SIGTERM` 전달
3. 애플리케이션이 종료 훅과 shutdown 절차 수행
4. 제한 시간 안에 끝나지 않으면 강제 종료(`SIGKILL`)

여기서 실무적으로 중요한 메시지는 하나다.

> graceful shutdown은 `SIGTERM` 구간 안에서만 가능하다.

`SIGKILL`은 애플리케이션이 가로챌 수 없다. 즉 아래 상황은 graceful shutdown 실패다.

- 종료 유예 시간(`terminationGracePeriodSeconds`)이 너무 짧다
- readiness 전환은 늦고, 긴 요청은 오래 걸리며, executor drain은 더 오래 걸린다
- 결국 오케스트레이터가 `SIGKILL`을 보내고 미완료 작업은 중간에 끊긴다

따라서 설계 순서는 항상 이렇다.

1. 종료 절차에 필요한 시간을 추정한다
2. 해당 시간보다 오케스트레이터 grace period를 넉넉하게 잡는다
3. 그보다 더 짧은 내부 타임아웃으로 애플리케이션 쪽 정리 시간을 통제한다

예를 들어:

- 애플리케이션 내부 graceful shutdown 목표: 20초
- Executor drain 최대 대기: 15초
- LB deregistration buffer: 5초
- Kubernetes `terminationGracePeriodSeconds`: 30~40초

이런 식으로 **안쪽 타임아웃 < 바깥쪽 강제 종료 시간** 구조를 잡아야 한다.

---

## 핵심 개념 2: Spring Boot의 graceful shutdown은 "웹 서버 종료"이지 "애플리케이션 전체 정책"이 아니다

Spring Boot 2.3+에서는 graceful shutdown 지원이 내장되어 있다.

```yaml
server:
  shutdown: graceful
spring:
  lifecycle:
    timeout-per-shutdown-phase: 20s
```

이 설정을 켜면 Spring Boot는 컨텍스트 종료 과정에서 웹 서버를 곧바로 내려버리지 않고, **진행 중인 요청이 끝날 시간을 잠시 부여**한다.

하지만 여기서 자주 생기는 오해가 있다.

> `server.shutdown=graceful`을 켰다고 해서 `@Async`, MQ consumer, 스케줄러, 외부 워커까지 모두 안전하게 정리되는 것은 아니다.

이 설정이 주로 다루는 것은 **내장 웹 서버 레벨의 요청 처리 종료**다. 즉 범위는 다음과 같이 나뉜다.

### 이 설정이 직접적으로 다루는 것

- 새로운 HTTP 연결/요청 수락 중단
- 이미 처리 중인 웹 요청의 종료 대기
- 웹 서버 connector/container 수준의 shutdown 절차

### 이 설정만으로는 충분하지 않은 것

- 사용자 정의 `ExecutorService` 정리
- `ThreadPoolTaskExecutor` 큐에 남은 작업 정책
- `@Async` 작업 종료 대기
- Kafka/RabbitMQ consumer 중단 순서
- 스케줄러 중복 실행 방지
- 장시간 배치 작업 중단 또는 재개 전략
- 외부 시스템에 대한 exactly-once가 아닌 side effect 정합성

즉 graceful shutdown은 Spring Boot 옵션 하나로 끝나는 기능이 아니라, **웹 계층 + 비동기 계층 + 메시지 계층 + 인프라 계층을 함께 맞추는 운영 설계**다.

---

## 핵심 개념 3: 트래픽 차단은 애플리케이션 종료보다 먼저 일어나야 한다

운영에서 가장 흔한 안티패턴은 이렇다.

- Pod가 종료 신호를 받는다
- 애플리케이션은 종료를 시작한다
- 그런데 로드밸런서는 아직 이 인스턴스를 healthy로 보고 계속 트래픽을 보낸다
- 결과적으로 종료 중인 서버가 새 요청까지 받다가 실패율이 튄다

그래서 종료 시퀀스는 보통 아래 순서를 가져야 한다.

1. **readiness false 전환**
2. 로드밸런서/서비스 디스커버리에서 인스턴스 제거 전파 대기
3. 그 뒤에 실제 요청 drain
4. 마지막으로 프로세스 종료

### Kubernetes에서 자주 쓰는 구성

- readiness probe로 트래픽 제외 여부 제어
- `preStop` 훅으로 짧은 대기 또는 앱 내부 drain 시작
- 충분한 `terminationGracePeriodSeconds`

예시 관점에서 보면 이런 식이다.

```yaml
lifecycle:
  preStop:
    exec:
      command: ["/bin/sh", "-c", "sleep 5"]
terminationGracePeriodSeconds: 30
```

이 설정이 항상 최선은 아니지만, 메시지는 분명하다.

- `SIGTERM` 직후 바로 프로세스 정리만 시작하면 늦다
- readiness 실패가 upstream에 전파될 시간을 줘야 한다

### `sleep` 기반 preStop의 한계

실무에서는 `preStop: sleep 5`를 자주 보는데, 이 방식은 단순하지만 한계가 있다.

- 5초가 충분한지 환경마다 다르다
- readiness 상태를 실제로 바꾸지 않으면 의미가 약하다
- LB deregistration 지연이 길면 여전히 부족할 수 있다
- 앱 내부 상태와 무관하게 무조건 기다리기만 한다

더 좋은 방식은 **애플리케이션이 스스로 drain 모드로 전환**하는 것이다.

예를 들어:

- drain 플래그를 켜고 readiness는 즉시 false 반환
- health endpoint는 `OUT_OF_SERVICE` 노출
- 새 요청은 빠르게 거절하거나 아예 라우팅 대상에서 제외
- 이미 진행 중인 요청과 비동기 작업만 정리

Spring Boot Actuator를 쓰면 readiness/liveness를 분리해 다루기 좋다.

```yaml
management:
  endpoint:
    health:
      probes:
        enabled: true
  health:
    livenessstate:
      enabled: true
    readinessstate:
      enabled: true
```

이후 Kubernetes readiness probe를 `/actuator/health/readiness`에 연결하면 종료 제어가 훨씬 명확해진다.

---

## 핵심 개념 4: 웹 요청은 "연결 종료"보다 "업무 완료 경계"를 기준으로 봐야 한다

그레이스풀 셧다운을 이야기할 때 많은 문서가 "진행 중인 요청을 기다린다"고만 설명한다. 하지만 실무에서 더 중요한 질문은 이거다.

> 어떤 시점을 "요청이 안전하게 끝났다"고 볼 것인가?

예를 들어 결제 승인 API를 보자.

```java
@Transactional
public PaymentResponse approve(PaymentRequest request) {
    Payment payment = paymentService.createPending(request);
    gatewayClient.approve(payment);
    payment.markApproved();
    return PaymentResponse.success(payment.getId());
}
```

이 요청이 종료 중인 서버에서 처리되다가 중간에 끊기면 여러 경우가 생긴다.

- DB 반영 전에 끊겨 아예 실패
- 외부 PG 승인 후 응답 전에 끊겨 사용자는 실패로 인지하지만 실제 승인됨
- 응답 직전 connection close로 클라이언트 재시도, 중복 승인 위험 증가

즉 graceful shutdown의 목적은 단순히 HTTP 200을 더 많이 주는 것이 아니라, **업무 단위의 모호한 중간 상태를 줄이는 것**이다.

그래서 중요한 것은 요청 시간 자체보다도 아래 항목이다.

- 요청이 **멱등성 키(idempotency key)** 를 가지고 있는가
- 외부 호출과 DB 커밋 순서를 어떻게 잡았는가
- 재시도 시 중복 처리 방어가 있는가
- 응답 실패와 업무 실패를 분리해서 해석할 수 있는가

graceful shutdown은 이 문제를 해결하는 마지막 방어선이지, 근본 대책은 아니다. 근본 대책은 **멱등성, outbox, 재처리 가능성, 상태 머신 설계**다.

---

## 핵심 개념 5: `ThreadPoolTaskExecutor`와 `@Async`는 따로 정리해야 한다

웹 요청은 서버가 drain해줄 수 있어도, 애플리케이션 내부 executor는 별도 정책이 필요하다.

대표적인 오해는 이렇다.

- `@Async`는 어차피 백그라운드니까 종료 시 알아서 끝나겠지
- executor bean은 스프링 빈이니 컨텍스트 종료 시 자동으로 완전히 안전하게 마무리되겠지

실제로는 그렇지 않다. 기본 설정에 따라 아래가 달라진다.

- 큐에 쌓인 작업까지 끝낼지
- 현재 실행 중인 작업만 기다릴지
- 종료 대기 시간을 얼마나 줄지
- timeout 이후 인터럽트를 걸지

실무에서는 `ThreadPoolTaskExecutor`를 명시적으로 설정하는 편이 안전하다.

```java
@Bean
public ThreadPoolTaskExecutor applicationTaskExecutor() {
    ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
    executor.setCorePoolSize(16);
    executor.setMaxPoolSize(32);
    executor.setQueueCapacity(200);
    executor.setThreadNamePrefix("app-async-");
    executor.setWaitForTasksToCompleteOnShutdown(true);
    executor.setAwaitTerminationSeconds(15);
    executor.initialize();
    return executor;
}
```

### 이 설정의 의미

- `setWaitForTasksToCompleteOnShutdown(true)`
  - 종료 시점에 실행 중 작업을 바로 버리지 않고 완료를 기다린다
- `setAwaitTerminationSeconds(15)`
  - 다만 무한정 기다리지는 않고 15초까지만 기다린다

하지만 이것도 만능은 아니다. 큐에 2,000개 작업이 쌓여 있고 각 작업이 10초 걸리면 15초 안에 끝날 수 없다. 따라서 executor 종료 전략은 **큐 용량, 작업 길이, 재처리 가능성**과 함께 봐야 한다.

### `@Async` 작업을 안전하게 만들기 위한 실무 기준

1. **짧고 재시도 가능한 작업만 둔다**
2. 긴 작업은 MQ, 배치, 워크플로 엔진으로 분리한다
3. shutdown 시 유실되어도 되는지, 재실행해도 되는지 명확히 한다
4. 큐 적체가 큰 작업을 HTTP 요청 종료 뒤에 붙이지 않는다
5. 종료 시간을 늘리는 대신 작업 구조를 짧게 쪼갠다

많은 팀이 graceful shutdown 시간을 60초, 120초로 계속 늘리는데, 그 전에 먼저 물어야 한다.

> 이 작업은 정말 웹 애플리케이션 프로세스 종료에 매달려 있어야 하는가?

---

## 핵심 개념 6: 스케줄러와 메시지 컨슈머는 HTTP와 다른 종료 규칙이 필요하다

웹 요청은 대개 request-response 경계가 있다. 반면 스케줄러와 메시지 컨슈머는 "작업 중간 상태"가 더 길고 복잡하다.

### 1) `@Scheduled` 작업

문제 상황은 대개 이렇다.

- 1분마다 실행되는 정산 작업이 배포 중 두 인스턴스에서 겹친다
- 종료 직전 시작한 스케줄 작업이 절반만 처리하고 끝난다
- 재시작 후 같은 배치가 다시 돌아 중복 반영된다

이 영역에서는 graceful shutdown만으로 부족하고 아래가 필요하다.

- 분산 락 또는 leader election
- 잡 실행 이력 테이블
- chunk 단위 checkpoint
- 작업 멱등성 보장

즉 스케줄러는 "예쁘게 종료"보다 **중단 후 다시 시작해도 안전한 구조**가 더 중요하다.

### 2) Kafka/RabbitMQ Consumer

메시지 컨슈머는 offset/ack 시점이 핵심이다.

- 처리 전에 commit하면 유실 위험
- 처리 후 commit하면 재시작 시 중복 처리 가능
- shutdown 중 rebalance가 일어나면 파티션 이동과 중복 처리 창이 생긴다

여기서 graceful shutdown의 실무 목표는 명확하다.

1. 새 메시지 poll/consume를 중단한다
2. 이미 받은 메시지는 가능하면 짧은 시간 안에 처리 마무리한다
3. 커밋 가능한 것만 커밋하고, 나머지는 재처리 가능한 상태로 남긴다

즉 메시지 계층에서는 graceful shutdown의 핵심 성과 지표가 "응답 성공률"이 아니라 아래다.

- 중복 처리 건수
- 유실 추정 건수
- rebalance 중 처리 지연
- shutdown 직전/직후 lag 변화

---

## 서버 종류별 차이: Tomcat, Undertow, Netty는 모두 같지 않다

Spring Boot 애플리케이션이라도 내장 서버 구현체에 따라 graceful shutdown 체감이 달라질 수 있다.

### Tomcat

- 전통적인 서블릿 기반 구조
- 요청 처리 스레드 풀과 connector 제어 관점이 비교적 직관적이다
- 많은 팀이 가장 익숙하게 운영한다

Tomcat 환경에서는 connector가 새 요청 수락을 멈추고, 진행 중 요청이 끝나길 기다리는 식으로 이해하면 된다. 다만 keep-alive 연결이나 프록시 계층 타이밍에 따라 완전히 즉시 차단되는 것처럼 보이지 않을 수 있다.

### Undertow

- 경량 서버로 빠르고 단순한 구성에 강점이 있다
- graceful shutdown 동작은 가능하지만, 운영 조직이 Tomcat에 비해 관측 경험이 적은 경우가 많다

### Netty(WebFlux)

- 이벤트 루프 기반
- 논블로킹 처리 모델이라 스레드/작업 종료 감각이 서블릿과 다르다
- 논블로킹이라도 외부 블로킹 호출이 끼어 있으면 종료 지연이 생긴다

중요한 점은, 어떤 서버를 쓰든 공통 원칙은 같다.

1. 새 요청 수락 중단
2. 진행 중 요청 drain
3. 타임아웃 이후 강제 종료

다만 **관측 포인트와 병목 위치**가 다르다. 서블릿에서는 worker thread, WebFlux에서는 event loop 차단과 외부 blocking I/O가 더 중요한 관측 포인트가 된다.

---

## 실무 예시 1: Kubernetes 롤링 배포에서 요청 유실을 줄이는 최소 구성

가장 현실적인 시나리오를 보자. Spring Boot API 서버를 Kubernetes에 배포하고 있고, Ingress/ALB 뒤에서 롤링 업데이트를 수행한다.

### 권장 흐름

1. readiness probe 활성화
2. 종료 시 애플리케이션이 readiness false 전환
3. `preStop`으로 아주 짧은 버퍼 제공
4. `server.shutdown=graceful` 활성화
5. `spring.lifecycle.timeout-per-shutdown-phase` 설정
6. executor 종료 정책 설정
7. Pod grace period를 내부 종료 시간보다 넉넉하게 배치

### 예시 설정

```yaml
server:
  shutdown: graceful
spring:
  lifecycle:
    timeout-per-shutdown-phase: 20s
management:
  endpoint:
    health:
      probes:
        enabled: true
  health:
    readinessstate:
      enabled: true
    livenessstate:
      enabled: true
```

Kubernetes 쪽에서는 다음을 함께 본다.

- readiness probe interval / failure threshold
- `preStop` 지연
- `terminationGracePeriodSeconds`
- Ingress/LB deregistration 지연 시간

### 흔한 실패 패턴

- 앱은 20초 기다리는데 Pod grace period는 10초라서 결국 `SIGKILL`
- readiness probe 주기가 너무 길어 제외 전파가 늦음
- `preStop sleep 5`는 넣었지만 readiness는 그대로 true
- 장기 요청이 많은데 timeout 없이 무작정 기다려 배포 슬롯 점유
- HPA 축소와 롤링 배포가 겹쳐 동시에 too many pods terminating 상태 발생

즉 graceful shutdown은 애플리케이션 설정만 맞춰서는 안 되고, **오케스트레이터 파라미터와 합이 맞아야 한다**.

---

## 실무 예시 2: 결제/주문 API에서 종료 중 중복 실행을 줄이는 패턴

종료 중 가장 위험한 API는 외부 부수효과가 있는 요청이다.

- 결제 승인
- 주문 생성
- 쿠폰 발급
- 이메일/SMS 발송
- 재고 차감

이런 API는 graceful shutdown이 잘 되어도 네트워크 끊김, client timeout, LB 재시도 때문에 중복 실행 창이 생긴다. 그래서 아래 패턴이 필요하다.

### 1) 멱등성 키 도입

```java
public OrderResponse placeOrder(String idempotencyKey, OrderRequest request) {
    return orderFacade.handle(idempotencyKey, request);
}
```

- 동일 키로 들어온 요청은 같은 결과를 반환
- 서버 종료 직전 응답이 끊겨도 클라이언트 재시도 시 중복 주문 방지

### 2) 상태 머신을 명확히 설계

예:

- `PENDING`
- `PROCESSING`
- `APPROVED`
- `FAILED`
- `CANCELLED`

종료 중 재시작이 일어나도 중간 상태를 기준으로 후속 복구가 가능해야 한다.

### 3) 외부 이벤트는 outbox로 분리

응답 직전 메시지 발행 실패/중복 문제를 줄이려면 DB 트랜잭션 안에서 outbox를 기록하고, 별도 퍼블리셔가 전송하는 방식이 안전하다.

graceful shutdown은 여기에 추가로 도움을 준다. 종료 중인 인스턴스가 새 요청을 안 받고, 이미 실행 중인 요청만 정리하면 **중간 상태 노출 창 자체가 줄어든다**.

---

## 핵심 트레이드오프: 종료를 오래 기다리면 안정적인가, 느린가?

graceful shutdown에는 명확한 트레이드오프가 있다.

### 기다리는 시간을 길게 잡을 때의 장점

- 진행 중인 긴 요청이 끝날 확률 증가
- 배치/비동기 작업 유실 감소
- 사용자 체감 오류율 감소 가능

### 단점

- 롤링 배포 시간이 길어진다
- 노드 축소/장애 복구 속도가 느려진다
- 오래 걸리는 잘못된 요청 때문에 종료가 지연된다
- connection drain이 길어져 리소스 회수 속도가 떨어진다

즉 종료 시간을 늘리는 것은 **증상 완화책**일 뿐, 근본 해결책이 아니다.

실무적으로는 아래 우선순위가 더 좋다.

1. 긴 요청을 줄이거나 비동기로 분리
2. 멱등성과 재처리 가능성 확보
3. readiness 차단을 빠르게 하고 drain 시간을 짧고 예측 가능하게 유지
4. 마지막으로 shutdown timeout을 조정

---

## 흔한 실수 1: readiness와 liveness를 같은 의미로 쓰기

이 둘은 목적이 다르다.

- **liveness**: 프로세스가 죽었는지, 재시작이 필요한지
- **readiness**: 지금 트래픽을 받아도 되는지

종료 중에는 보통 이렇게 되어야 한다.

- liveness는 당장 false가 될 필요 없음
- readiness는 빠르게 false가 되어야 함

종료 중 readiness까지 계속 true면 트래픽이 계속 유입된다. 반대로 일시적인 다운스트림 장애 때 liveness까지 false로 만들어버리면 불필요한 재시작 루프가 생긴다.

---

## 흔한 실수 2: DB 트랜잭션 시간과 HTTP timeout을 분리하지 않기

긴 트랜잭션은 graceful shutdown에서 치명적이다.

- 락을 오래 잡는다
- 종료 대기 시간을 잡아먹는다
- 중간 실패 시 복구 범위가 커진다

실무 기준으로는 아래가 좋다.

- 외부 API 호출 전후 트랜잭션 경계를 신중히 자른다
- 하나의 요청 안에 너무 많은 DB 변경을 몰아넣지 않는다
- 정말 오래 걸리는 작업은 상태 저장 후 비동기 처리한다

"graceful shutdown이 있으니 긴 요청도 괜찮다"는 생각은 위험하다. graceful shutdown은 긴 트랜잭션을 정당화하지 않는다.

---

## 흔한 실수 3: 로그만 보고 종료가 잘 됐다고 착각하기

종료 로그에 "Shutting down ExecutorService"가 찍혔다고 안전 종료가 보장되는 것은 아니다. 운영에서는 최소한 아래 지표를 같이 봐야 한다.

- terminating pod에서의 5xx 비율
- 종료 직전/직후 p95, p99 latency
- in-flight requests 수
- executor active count, queue depth
- Kafka consumer lag 변화
- shutdown phase duration
- 강제 종료(`SIGKILL`) 비율

관측 없이는 graceful shutdown 품질을 개선할 수 없다.

### 추천 관측 항목

- drain 시작 시각
- readiness false 전환 시각
- 마지막 요청 종료 시각
- executor 종료 완료 시각
- 프로세스 종료 시각

이 네 시각만 남겨도 종료 병목이 어디 있는지 훨씬 빨리 찾을 수 있다.

---

## 흔한 실수 4: 종료 훅에서 무거운 작업을 추가로 시작하기

`@PreDestroy`나 shutdown hook 안에서 아래 같은 일을 넣는 경우가 있다.

- 대량 데이터 정리 배치 시작
- 외부 API 호출로 마지막 상태 동기화
- 수천 건 메시지 flush
- 오래 걸리는 캐시 warm-up/backup

이건 매우 위험하다. 종료 훅은 **새 일을 시작하는 장소가 아니라, 현재 일을 빨리 정리하는 장소**여야 한다.

종료 훅에서 해야 할 일은 가볍고 결정적이어야 한다.

- 새 입력 차단
- 현재 작업 종료 대기
- 상태 플래그 정리
- 최소한의 자원 반환

---

## 체크리스트: Spring Boot 서비스의 graceful shutdown 운영 점검표

배포 전에 아래를 확인하면 대부분의 큰 사고를 줄일 수 있다.

### 애플리케이션 설정

- `server.shutdown=graceful`이 활성화되어 있는가
- `spring.lifecycle.timeout-per-shutdown-phase`가 현실적인 값인가
- `@Async`/사용자 정의 executor가 종료 정책을 명시적으로 갖는가
- 장기 작업은 HTTP 요청 수명과 분리되어 있는가

### 인프라 설정

- readiness probe와 liveness probe가 분리되어 있는가
- 종료 시 readiness가 즉시 false로 바뀌는가
- `terminationGracePeriodSeconds`가 앱 내부 timeout보다 충분히 큰가
- LB/Ingress deregistration 지연을 감안했는가
- `preStop`은 앱의 실제 drain 전략과 일치하는가

### 업무 정합성

- 멱등성 키가 필요한 API에 적용되어 있는가
- 외부 부수효과 호출은 중복/재시도에 안전한가
- 메시지 처리에서 ack/commit 시점이 명확한가
- 스케줄러/배치 작업은 재시작 후 재처리가 가능한가

### 관측성

- 종료 시작, readiness false, 마지막 요청 완료 시각이 로그/메트릭으로 남는가
- 강제 종료 비율을 측정하는가
- 종료 중 5xx와 timeout 비율을 따로 볼 수 있는가

---

## 추천 실무 기준: 이렇게 정리하면 대부분의 서비스가 크게 좋아진다

아래 기준은 범용적인 출발점으로 괜찮다.

1. **HTTP 요청은 짧게 유지한다**
   - 긴 리포트, 대량 처리, 외부 시스템 fan-out은 비동기화한다
2. **readiness를 종료 제어의 첫 스위치로 쓴다**
   - 종료 신호보다 먼저 또는 동시에 트래픽 차단을 시작한다
3. **graceful shutdown timeout은 15~30초 수준에서 시작한다**
   - 무작정 길게 잡지 말고 지표를 보며 조정한다
4. **executor와 consumer 종료 정책을 명시한다**
   - 기본값에 기대지 않는다
5. **멱등성과 재처리 가능성을 먼저 설계한다**
   - graceful shutdown은 마지막 안전장치다
6. **강제 종료 비율을 운영 지표로 본다**
   - 한 번도 측정하지 않았다면 실제 품질을 모르는 것이다

---

## 한 줄 정리

Spring Boot graceful shutdown의 핵심은 `server.shutdown=graceful` 자체가 아니라, **readiness로 새 요청을 먼저 끊고, 진행 중인 HTTP·비동기·메시지 작업을 각자 맞는 정책으로 drain한 뒤, 강제 종료 전에 예측 가능하게 끝내는 종료 프로토콜을 갖추는 것**이다.
