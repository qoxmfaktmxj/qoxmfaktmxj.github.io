---
layout: post
title: "Spring Boot 종료 처리 실전: Graceful Shutdown, Readiness, SmartLifecycle, Connection Draining으로 배포 중 요청을 잃지 않는 법"
date: 2026-07-17 11:50:00 +0900
categories: [java]
tags: [study, java, spring-boot, graceful-shutdown, readiness, liveness, smartlifecycle, kubernetes, connection-draining, lifecycle, operations, backend]
permalink: /java/2026/07/17/study-java-spring-boot-graceful-shutdown-readiness-lifecycle-termination.html
---

## 배경: 배포는 "새 버전을 띄우는 일"이 아니라 이전 버전을 안전하게 내리는 일이다

Spring Boot 서비스를 운영하다 보면 배포 자동화는 생각보다 빨리 갖춘다.

- CI가 테스트를 돌린다.
- Docker image를 만든다.
- Kubernetes Deployment가 rolling update를 수행한다.
- 새 Pod가 뜨고 readiness probe가 통과한다.
- 트래픽이 새 버전으로 흘러간다.

겉으로 보기에는 충분히 현대적인 배포 파이프라인이다. 하지만 실제 장애는 "새 Pod가 잘 떴는가"보다 "기존 Pod가 내려갈 때 무엇을 놓쳤는가"에서 더 자주 생긴다.

운영에서 흔히 보이는 증상은 이렇다.

- 배포 시점에만 간헐적으로 502, 503, connection reset이 증가한다.
- 사용자는 저장 버튼을 눌렀는데 서버 로그에는 요청 처리 도중 JVM 종료가 찍힌다.
- Kafka consumer가 메시지를 처리하다 종료되어 같은 메시지가 반복 처리된다.
- scheduler가 긴 작업을 수행하던 중 중단되어 중간 상태가 남는다.
- Spring Boot graceful shutdown을 켰는데도 로드 밸런서에서 끊긴 요청이 나온다.
- readiness probe는 실패했지만 몇 초 동안 트래픽이 계속 들어온다.
- `preStop` hook에서 sleep을 넣었더니 배포 시간만 길어지고 문제는 그대로다.
- DB connection pool은 닫혔는데 background worker가 뒤늦게 query를 시도한다.
- 종료 직전에 outbox flush, metric export, audit log 기록이 일부 누락된다.
- local에서는 재현되지 않고 rolling update, node drain, spot termination, autoscaling 때만 발생한다.

이 문제를 단순히 "graceful shutdown 옵션을 켜자"로 접근하면 부족하다.

서비스 종료는 JVM 내부 이벤트 하나가 아니다. 운영 환경에서는 다음 계층이 모두 얽힌다.

```text
Kubernetes / VM / systemd / container runtime
  -> SIGTERM 전달
  -> 애플리케이션 readiness 변경
  -> 로드 밸런서 endpoint 제거
  -> 기존 connection drain
  -> HTTP server 신규 요청 차단
  -> 진행 중 요청 완료 대기
  -> scheduler / consumer / worker 중단
  -> DB pool / HTTP client / metric exporter 정리
  -> SIGKILL 전 최종 종료
```

따라서 중급 이상 Java 개발자가 봐야 할 질문은 `server.shutdown=graceful`을 켰는가가 아니다.

> 종료 신호를 받은 순간부터 프로세스가 완전히 사라질 때까지, 신규 작업 유입을 언제 막고, 진행 중 작업을 얼마나 기다리며, 완료되지 못한 작업을 어떤 상태로 남길 것인가?

오늘 글은 Spring Boot 기반 서비스를 운영 기준으로 종료 가능하게 만드는 방법을 정리한다.

다룰 내용은 다음과 같다.

1. SIGTERM, readiness, graceful shutdown, connection draining의 역할 차이
2. Spring Boot가 HTTP 요청 종료를 어떻게 처리하는지
3. Kubernetes `terminationGracePeriodSeconds`, `preStop`, probe를 어떻게 맞춰야 하는지
4. `SmartLifecycle`, `ApplicationListener`, `@PreDestroy`를 어디에 써야 하는지
5. scheduler, Kafka consumer, async executor, batch worker를 어떤 순서로 멈춰야 하는지
6. 외부 I/O와 DB 트랜잭션을 종료 경계에서 어떻게 다뤄야 하는지
7. 배포 중 5xx를 줄이기 위한 체크리스트와 테스트 방법

핵심 결론부터 말하면 이렇다.

**Graceful shutdown은 "프로세스를 천천히 죽이는 옵션"이 아니라, 신규 작업 유입 차단, 진행 중 작업의 완료 또는 포기 기준, 외부 라우팅 제거, 내부 worker 정지 순서를 하나의 계약으로 맞추는 운영 설계다.**

Spring Boot 옵션은 이 설계를 구현하는 한 조각이다. 로드 밸런서, Kubernetes probe, executor, messaging consumer, transaction boundary가 함께 맞지 않으면 배포 중 요청 유실은 계속 발생한다.

---

## 먼저 큰 그림: 종료 처리는 세 가지 시간을 맞추는 문제다

서비스 종료를 제대로 보려면 세 가지 시간을 분리해야 한다.

```text
T0: 종료 신호를 받는 시점
T1: 외부에서 이 인스턴스를 더 이상 호출하지 않는 시점
T2: 인스턴스 내부 진행 중 작업이 끝나는 시점
T3: 프로세스가 완전히 종료되는 시점
```

문제는 현실에서 이 시간이 자동으로 정렬되지 않는다는 점이다.

예를 들어 Kubernetes가 Pod에 SIGTERM을 보냈다고 하자. 애플리케이션은 종료를 시작한다. 하지만 동시에 Service endpoint 제거, Ingress 또는 cloud load balancer 반영, client keep-alive connection 정리에는 시간이 걸린다. 그 사이 기존 Pod로 요청이 들어올 수 있다.

반대로 readiness를 너무 빨리 실패시키고 내부 HTTP server도 즉시 닫으면, 아직 로드 밸런서가 endpoint 제거를 반영하지 못한 몇 초 동안 요청이 connection reset으로 깨질 수 있다.

좋은 종료 흐름은 보통 다음 순서에 가깝다.

```text
1. 종료 의도 표시
   - readiness를 false로 바꾼다.
   - 내부 worker가 새 작업을 받지 않도록 한다.

2. 외부 라우팅 제거 대기
   - load balancer, kube-proxy, ingress controller가 endpoint 제거를 반영할 시간을 둔다.
   - 이미 맺어진 keep-alive connection의 신규 요청 가능성을 줄인다.

3. 신규 요청 차단
   - HTTP server가 새 요청을 받지 않는다.
   - message consumer poll, scheduler trigger, async submission을 멈춘다.

4. 진행 중 작업 완료 대기
   - 요청, 메시지 처리, batch chunk, outbox 저장, transaction commit을 제한 시간 안에서 끝낸다.

5. 자원 정리
   - executor shutdown, consumer close, DB pool close, metric flush, log flush를 수행한다.

6. 제한 시간이 지나면 강제 종료
   - 무한정 기다리지 않는다.
   - 남은 작업은 재처리 가능하거나 명시적으로 실패 상태여야 한다.
```

여기서 중요한 것은 "기다림"만으로는 graceful이 되지 않는다는 점이다. 새 작업을 계속 받으면서 기다리면 종료가 끝나지 않는다. 반대로 새 작업을 막자마자 process를 닫으면 진행 중 작업이 깨진다. 따라서 종료 설계는 항상 **유입 차단**과 **완료 대기**를 함께 다룬다.

---

## 핵심 개념 1: SIGTERM은 종료 요청이지 "지금 당장 죽어라"가 아니다

Linux 환경에서 컨테이너나 프로세스를 종료할 때 일반적으로 먼저 `SIGTERM`이 전달된다. 이것은 애플리케이션에게 정상 종료 기회를 주는 신호다.

Kubernetes에서는 Pod 종료가 시작되면 대략 다음 흐름이 일어난다.

```text
1. Pod deletion timestamp 설정
2. preStop hook 실행
3. 컨테이너 entrypoint 프로세스에 SIGTERM 전달
4. endpoint에서 Pod 제거 반영 시작
5. terminationGracePeriodSeconds 동안 대기
6. 아직 살아 있으면 SIGKILL 전달
```

세부 순서는 runtime, hook, probe, controller, ingress 구성에 따라 체감이 조금 달라질 수 있지만 운영 관점의 핵심은 같다.

- SIGTERM을 받으면 애플리케이션은 종료를 시작해야 한다.
- grace period 안에 끝나지 않으면 SIGKILL로 강제 종료될 수 있다.
- SIGKILL은 애플리케이션 코드가 잡을 수 없다.
- shutdown hook, `@PreDestroy`, finally block은 SIGKILL 시 보장되지 않는다.

따라서 중요한 작업을 "종료 hook에서 어떻게든 마무리하자"에 기대면 위험하다. 종료 hook은 마지막 정리용이지 비즈니스 정합성의 주 수단이 아니다.

예를 들어 주문 처리 중이라면 안전한 구조는 이렇다.

- 주문 상태 변경과 outbox event 저장은 같은 DB 트랜잭션에서 끝낸다.
- 외부 메시지 발행은 별도 relay가 재시도 가능하게 한다.
- 중간에 프로세스가 죽어도 DB 상태만 보고 다시 이어갈 수 있다.
- shutdown hook은 relay를 잠시 기다리거나 metric을 flush하는 수준으로 둔다.

즉 종료 내구성은 hook이 아니라 작업 모델에서 만들어야 한다.

---

## 핵심 개념 2: Readiness와 Liveness를 종료 설계에 섞어 쓰면 안 된다

Kubernetes probe를 처음 설정할 때 가장 많이 헷갈리는 것이 readiness와 liveness다.

둘은 목적이 다르다.

```text
Readiness
  -> 이 Pod가 지금 트래픽을 받아도 되는가

Liveness
  -> 이 프로세스를 재시작해야 할 정도로 죽었는가
```

종료 처리에서 중요한 것은 readiness다. 종료를 시작한 인스턴스는 더 이상 신규 트래픽을 받으면 안 된다. 따라서 종료 의도를 감지하면 readiness는 빠르게 실패해야 한다.

반면 liveness는 조심해야 한다. 종료 중이라고 liveness가 실패하면 kubelet이 프로세스를 더 공격적으로 재시작하거나 상태 해석이 꼬일 수 있다. liveness는 "정상 종료 중"을 장애로 보지 않는 편이 낫다.

Spring Boot Actuator를 쓰면 health group으로 분리할 수 있다.

```yaml
management:
  endpoint:
    health:
      probes:
        enabled: true
      group:
        readiness:
          include: readinessState,db,redis
        liveness:
          include: livenessState
```

그리고 probe는 다음처럼 나눌 수 있다.

```yaml
readinessProbe:
  httpGet:
    path: /actuator/health/readiness
    port: 8080
  periodSeconds: 5
  failureThreshold: 1

livenessProbe:
  httpGet:
    path: /actuator/health/liveness
    port: 8080
  periodSeconds: 10
  failureThreshold: 3
```

여기서 readiness에 DB, Redis를 모두 넣어도 되는지는 서비스 성격에 따라 다르다. DB가 잠깐 느려질 때 readiness가 실패하면 Kubernetes가 트래픽을 다른 Pod로 돌린다. 모든 Pod가 같은 DB를 보는 구조라면 전체 Pod가 동시에 not ready가 되어 더 큰 문제를 만들 수도 있다.

운영 기준은 다음처럼 잡는 편이 좋다.

- readiness는 "이 인스턴스가 요청을 처리할 수 있는가"를 표현한다.
- dependency 장애를 readiness에 넣을 때는 전체 인스턴스가 동시에 빠지는 효과를 고려한다.
- 종료 중에는 readiness를 반드시 false로 만든다.
- liveness는 process deadlock, event loop 정지, 회복 불가능한 상태에 가깝게 둔다.
- 느린 dependency를 liveness 실패로 연결하지 않는다.

Spring Boot는 내부적으로 `AvailabilityChangeEvent`를 통해 readiness 상태를 바꿀 수 있다.

```java
@Component
public class ShutdownReadiness {

    private final ApplicationEventPublisher publisher;

    public ShutdownReadiness(ApplicationEventPublisher publisher) {
        this.publisher = publisher;
    }

    public void refuseTraffic() {
        AvailabilityChangeEvent.publish(
                publisher,
                this,
                ReadinessState.REFUSING_TRAFFIC
        );
    }
}
```

다만 대부분의 경우 Spring Boot 자체 종료 흐름과 Actuator probe를 함께 쓰면 충분하다. 별도 상태 전환 코드를 넣는다면 어느 시점에 호출되는지, HTTP server shutdown과 순서가 어떻게 맞는지 명확히 해야 한다.

---

## 핵심 개념 3: Spring Boot graceful shutdown은 HTTP server 요청 대기 장치다

Spring Boot 2.3 이후에는 내장 web server의 graceful shutdown을 설정할 수 있다.

```yaml
server:
  shutdown: graceful

spring:
  lifecycle:
    timeout-per-shutdown-phase: 30s
```

이 설정은 종료 시점에 web server가 진행 중인 요청이 끝나기를 기다리도록 한다. Tomcat, Jetty, Reactor Netty, Undertow 등 web server마다 동작 세부는 다르지만 목적은 같다.

- 새 요청 수락을 중단한다.
- 이미 들어온 요청이 끝날 시간을 준다.
- 설정된 timeout이 지나면 종료를 계속 진행한다.

하지만 이 옵션을 켰다고 전체 애플리케이션이 안전하게 종료되는 것은 아니다.

이 설정이 주로 다루는 것은 HTTP request lifecycle이다. 다음 항목은 별도로 봐야 한다.

- `@Scheduled` 작업
- Kafka, RabbitMQ, SQS consumer
- application event listener
- `@Async` executor
- custom thread
- batch job
- outbox relay
- WebSocket, SSE, long polling
- gRPC stream
- DB transaction timeout
- 외부 HTTP client timeout
- load balancer endpoint removal latency

또 하나 중요한 점은 `spring.lifecycle.timeout-per-shutdown-phase`가 전체 종료 timeout 하나가 아니라 lifecycle phase별 timeout이라는 점이다. `SmartLifecycle` bean의 phase에 따라 stop 순서가 나뉘며, 각 phase마다 timeout이 적용될 수 있다.

즉 종료 시간을 설계할 때는 Kubernetes grace period와 Spring lifecycle timeout을 맞춰야 한다.

```yaml
# Kubernetes
terminationGracePeriodSeconds: 60

# Spring Boot
spring:
  lifecycle:
    timeout-per-shutdown-phase: 30s
```

여기서 Kubernetes grace period가 20초인데 Spring은 30초 기다리도록 설정하면 의미가 없다. kubelet이 먼저 SIGKILL을 보낼 수 있다. 반대로 Kubernetes는 120초 기다리는데 Spring은 5초만 기다리면 진행 중 요청이 너무 빨리 끊길 수 있다.

현실적인 시작점은 다음처럼 잡을 수 있다.

```text
terminationGracePeriodSeconds: 60s
preStop or drain delay: 5~15s
HTTP graceful wait: 20~40s
worker stop wait: 20~40s
final buffer: 5~10s
```

정답은 서비스의 최대 요청 시간, consumer 처리 시간, 배포 빈도, autoscaling 전략에 따라 달라진다. 중요한 것은 숫자가 아니라 **가장 긴 정상 작업 시간이 grace period보다 짧아야 한다**는 원칙이다. 정상 작업이 5분 걸리는데 grace period가 30초라면 graceful shutdown이 아니라 강제 중단 설계다.

---

## 실무 예시 1: Kubernetes에서 endpoint 제거와 HTTP shutdown 사이의 틈 줄이기

가장 흔한 배포 중 5xx 원인은 endpoint 제거 전파와 애플리케이션 종료가 어긋나는 것이다.

다음 구성을 보자.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order-api
spec:
  replicas: 4
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    spec:
      terminationGracePeriodSeconds: 60
      containers:
        - name: app
          image: example/order-api:2026-07-17
          ports:
            - containerPort: 8080
          lifecycle:
            preStop:
              exec:
                command: ["/bin/sh", "-c", "sleep 10"]
          readinessProbe:
            httpGet:
              path: /actuator/health/readiness
              port: 8080
            periodSeconds: 5
            failureThreshold: 1
          livenessProbe:
            httpGet:
              path: /actuator/health/liveness
              port: 8080
            periodSeconds: 10
            failureThreshold: 3
```

`preStop sleep`은 흔히 쓰이는 방법이다. 목적은 간단하다. Pod 종료가 시작된 뒤 endpoint 제거가 외부 load balancer까지 전파될 시간을 벌어 주는 것이다.

하지만 이 방식에는 주의점이 있다.

첫째, sleep은 원인을 해결하는 기능이 아니라 전파 지연을 흡수하는 완충 장치다. ingress controller, cloud load balancer, service mesh, kube-proxy, client DNS/cache 구조에 따라 필요한 시간이 달라질 수 있다.

둘째, `preStop`이 실행되는 동안에도 애플리케이션이 트래픽을 받을 수 있다. 종료 의도를 애플리케이션 readiness와 함께 반영하지 않으면, sleep 중에도 신규 요청이 들어와 작업 시간이 늘어난다.

셋째, `preStop` 시간은 `terminationGracePeriodSeconds` 안에 포함된다. 60초 grace period에서 20초 sleep을 쓰면 실제 애플리케이션이 정리할 수 있는 시간은 줄어든다.

그래서 더 좋은 기준은 다음과 같다.

```text
1. 종료 시작 시 readiness false
2. endpoint 제거 전파를 위해 짧은 drain delay
3. HTTP server graceful shutdown
4. worker shutdown
5. grace period 안에서 완료
```

Spring Boot Actuator의 readiness가 종료 상태를 잘 반영하고, 내장 server graceful shutdown이 켜져 있다면 `preStop sleep`은 짧은 보정값으로만 둔다. 30초, 60초 sleep으로 문제를 덮는 것은 배포 속도와 장애 복구 속도를 함께 희생한다.

---

## 실무 예시 2: SmartLifecycle로 worker를 HTTP 서버보다 먼저 멈추기

HTTP 요청만 처리하는 단순 API라면 `server.shutdown=graceful`만으로도 꽤 많은 문제가 줄어든다. 하지만 실제 서비스에는 background worker가 있다.

예를 들어 outbox relay가 있다고 하자.

```java
@Component
public class OutboxRelay {

    private final ScheduledExecutorService executor =
            Executors.newSingleThreadScheduledExecutor();

    private final AtomicBoolean running = new AtomicBoolean(false);

    public void start() {
        if (running.compareAndSet(false, true)) {
            executor.scheduleWithFixedDelay(this::publishOnce, 0, 1, TimeUnit.SECONDS);
        }
    }

    public void stop() {
        running.set(false);
        executor.shutdown();
    }

    private void publishOnce() {
        if (!running.get()) {
            return;
        }

        // outbox table에서 발행 대상을 읽고 broker로 전송한 뒤 published 처리
    }
}
```

이런 custom worker는 Spring lifecycle과 연결하지 않으면 종료 순서가 애매하다. `@PostConstruct`에서 시작하고 `@PreDestroy`에서 멈출 수도 있지만, 여러 컴포넌트 사이의 순서를 제어하기 어렵다.

이럴 때는 `SmartLifecycle`을 고려할 수 있다.

```java
@Component
public class OutboxRelayLifecycle implements SmartLifecycle {

    private final OutboxRelay relay;
    private final AtomicBoolean running = new AtomicBoolean(false);

    public OutboxRelayLifecycle(OutboxRelay relay) {
        this.relay = relay;
    }

    @Override
    public void start() {
        if (running.compareAndSet(false, true)) {
            relay.start();
        }
    }

    @Override
    public void stop(Runnable callback) {
        try {
            if (running.compareAndSet(true, false)) {
                relay.stop();
            }
        } finally {
            callback.run();
        }
    }

    @Override
    public void stop() {
        stop(() -> { });
    }

    @Override
    public boolean isRunning() {
        return running.get();
    }

    @Override
    public int getPhase() {
        return 100;
    }
}
```

`SmartLifecycle`의 phase는 시작과 종료 순서에 영향을 준다.

- 시작할 때는 낮은 phase가 먼저 시작한다.
- 종료할 때는 높은 phase가 먼저 멈춘다.

따라서 "트래픽을 받는 컴포넌트보다 내부 worker를 먼저 멈출 것인가" 또는 "worker가 마지막까지 남아 outbox를 조금 더 비울 것인가"를 phase로 표현할 수 있다.

다만 phase를 남발하면 오히려 이해하기 어려워진다. 운영에서는 다음 정도 원칙을 추천한다.

- 새 작업을 만드는 scheduler, consumer는 먼저 멈춘다.
- 이미 들어온 HTTP 요청은 제한 시간 안에서 끝낸다.
- outbox relay, metric exporter처럼 후처리 성격의 작업은 너무 늦게까지 붙잡지 않는다.
- DB pool, broker connection, HTTP client는 해당 자원을 쓰는 worker가 멈춘 뒤 닫힌다.
- phase 값은 상수로 이름을 붙여 팀 내 의미를 공유한다.

예를 들어 lifecycle phase를 명시적으로 관리할 수 있다.

```java
public final class LifecyclePhases {
    private LifecyclePhases() {
    }

    public static final int TRAFFIC_INTAKE = 1000;
    public static final int BACKGROUND_WORKER = 500;
    public static final int RESOURCE_CLEANUP = 0;
}
```

숫자 자체보다 "무엇이 먼저 멈춰야 하는가"를 코드에 남기는 것이 중요하다.

---

## 실무 예시 3: Scheduler는 다음 실행만 막는 것이 아니라 현재 실행을 추적해야 한다

Spring의 `@Scheduled`는 편하다.

```java
@Scheduled(fixedDelay = 30000)
public void synchronizeInventory() {
    inventorySyncService.syncChangedItems();
}
```

하지만 종료 시점에는 몇 가지 질문이 필요하다.

- 종료 신호 이후 새 schedule trigger가 실행되면 안 되는가
- 이미 실행 중인 sync는 끝까지 기다릴 것인가
- 기다리는 최대 시간은 얼마인가
- 중간에 끊겨도 다음 실행에서 재개 가능한가
- 같은 작업이 새 Pod와 이전 Pod에서 동시에 실행되어도 안전한가

`@Scheduled` 작업이 단순 cache refresh라면 중간에 끊겨도 괜찮을 수 있다. 하지만 외부 시스템과 동기화하거나 DB 상태를 변경한다면 이야기가 달라진다.

중요한 작업이라면 최소한 실행 단위를 명시적으로 쪼개야 한다.

```java
@Service
public class InventorySyncService {

    @Transactional
    public SyncResult syncOnePage(SyncCursor cursor) {
        List<InventoryChange> changes = remoteInventoryClient.fetch(cursor, 100);

        for (InventoryChange change : changes) {
            inventoryRepository.upsert(change.toEntity());
        }

        return SyncResult.next(changes);
    }
}
```

그리고 scheduler는 긴 작업 하나가 아니라 작은 chunk를 반복하도록 만든다.

```java
@Component
public class InventorySyncScheduler {

    private final AtomicBoolean stopping = new AtomicBoolean(false);
    private final InventorySyncService syncService;

    public InventorySyncScheduler(InventorySyncService syncService) {
        this.syncService = syncService;
    }

    @Scheduled(fixedDelay = 30000)
    public void run() {
        if (stopping.get()) {
            return;
        }

        SyncCursor cursor = SyncCursor.initial();
        while (!stopping.get() && cursor.hasNext()) {
            SyncResult result = syncService.syncOnePage(cursor);
            cursor = result.nextCursor();
        }
    }

    @EventListener(ContextClosedEvent.class)
    public void onShutdown() {
        stopping.set(true);
    }
}
```

이 방식은 종료뿐 아니라 장애 복구에도 유리하다.

- chunk 단위 transaction으로 lock 유지 시간이 짧아진다.
- 실패 시 마지막 cursor부터 재시도하기 쉽다.
- 종료 신호가 오면 다음 chunk 시작 전에 멈출 수 있다.
- 새 Pod에서 같은 작업을 이어받기 쉽다.

단, 이것만으로 분산 환경 중복 실행이 해결되지는 않는다. replicas가 여러 개인 서비스에서 scheduler가 동시에 돌면 distributed lock, leader election, job table claim, idempotent upsert 같은 설계가 필요하다.

종료 설계의 원칙은 여기서도 같다.

> 긴 작업을 강제로 끝까지 붙잡지 말고, 짧고 재개 가능한 단위로 쪼개 종료 지점을 자연스럽게 만든다.

---

## 실무 예시 4: Kafka consumer 종료는 offset commit 전략과 같이 봐야 한다

메시지 consumer는 종료 처리에서 특히 조심해야 한다. HTTP 요청은 client가 실패를 볼 수 있지만, 메시지는 broker와 offset 상태에 따라 중복 처리 또는 유실처럼 보이는 결과가 생긴다.

Kafka consumer를 예로 보자.

```java
@KafkaListener(topics = "payment-approved", groupId = "order-service")
public void handle(PaymentApprovedEvent event) {
    orderPaymentService.markPaid(event.orderId(), event.paymentId());
}
```

종료 중에는 다음 시나리오가 가능하다.

```text
1. 메시지를 poll 했다.
2. DB transaction으로 주문 상태를 PAID로 바꿨다.
3. offset commit 전에 SIGTERM 또는 SIGKILL이 발생했다.
4. 재시작 후 같은 메시지를 다시 받는다.
```

이 경우 중복 처리가 발생한다. 이것은 Kafka가 잘못한 것이 아니라 at-least-once 처리 모델에서 자연스러운 결과다. 따라서 consumer 로직은 idempotent해야 한다.

```java
@Transactional
public void markPaid(Long orderId, String paymentId) {
    Order order = orderRepository.findById(orderId)
            .orElseThrow();

    if (order.isPaid()) {
        return;
    }

    order.markPaid(paymentId);
    paymentEventRepository.save(PaymentEvent.paid(orderId, paymentId));
}
```

하지만 단순 `isPaid()`만으로 충분하지 않을 수 있다. 같은 주문에 서로 다른 paymentId가 들어오면 오류로 봐야 한다.

```java
public void markPaid(String paymentId) {
    if (this.status == OrderStatus.PAID) {
        if (!Objects.equals(this.paymentId, paymentId)) {
            throw new IllegalStateException("order already paid by another payment");
        }
        return;
    }

    if (this.status != OrderStatus.PAYMENT_PENDING) {
        throw new IllegalStateException("order is not payable");
    }

    this.status = OrderStatus.PAID;
    this.paymentId = paymentId;
}
```

Kafka listener container도 종료 시 poll을 멈추고 진행 중 listener 처리를 기다리는 설정이 필요하다. Spring Kafka에서는 container shutdown timeout, ack mode, concurrency, error handler, transaction manager 설정을 함께 봐야 한다.

핵심 기준은 다음과 같다.

- 종료 신호 이후 새 poll을 빠르게 멈춘다.
- 이미 listener로 넘어간 메시지는 제한 시간 안에서 끝낸다.
- offset commit 전 죽을 수 있으므로 handler는 멱등해야 한다.
- 처리 시간이 grace period보다 길면 chunk를 줄이거나 메시지 단위를 다시 설계한다.
- consumer rebalance 시 partition revoke와 commit 순서를 로그로 확인한다.
- DLQ, retry topic, backoff 정책이 종료 중 예외와 충돌하지 않는지 본다.

메시지 처리에서 graceful shutdown의 목표는 "중복을 절대 만들지 않기"가 아니다. 현실적으로 at-least-once에서는 중복 가능성을 받아들이고, 중복되어도 결과가 깨지지 않게 만드는 것이 운영 가능한 목표다.

---

## 핵심 개념 4: `@PreDestroy`는 마지막 정리용이지 긴 비즈니스 처리용이 아니다

Spring bean이 제거될 때 `@PreDestroy`를 사용할 수 있다.

```java
@Component
public class ReportBuffer {

    private final List<ReportLine> buffer = new CopyOnWriteArrayList<>();

    @PreDestroy
    public void flush() {
        reportRepository.saveAll(buffer);
    }
}
```

이런 코드는 위험하다.

왜냐하면 종료 시점에 다음이 보장되지 않기 때문이다.

- DB connection pool이 아직 안전하게 열려 있는가
- transaction manager가 정상 동작하는가
- saveAll이 grace period 안에 끝나는가
- 실패했을 때 재시도할 수 있는가
- SIGKILL이 오면 어떻게 되는가
- buffer에 있는 데이터가 프로세스 메모리에만 있어도 되는가

중요한 데이터가 메모리 buffer에만 있고 종료 hook에서 저장되기를 기대하는 구조는 운영 내구성이 약하다. 더 안전한 방식은 입력 시점 또는 작은 batch 단위로 durable storage에 먼저 기록하는 것이다.

예를 들어 report line이 중요하다면 다음처럼 설계한다.

```text
요청 처리 중 report_event table에 append
  -> 별도 relay가 report storage로 전송
  -> 성공하면 published_at 기록
  -> 실패/종료 시 다음 주기에서 재시도
```

이 구조에서는 종료 hook이 relay를 조금 기다릴 수는 있지만, relay가 실패해도 원본 event가 DB에 남아 있다.

`@PreDestroy`에 적합한 작업은 대체로 다음이다.

- custom executor shutdown
- local cache 통계 flush
- metric exporter close
- client connection close
- temporary file 정리
- non-critical buffer best-effort flush

부적합한 작업은 다음이다.

- 주문 상태 변경
- 결제 취소 요청
- 유일한 event 발행
- 대량 DB migration
- 긴 외부 API 호출
- 실패하면 재처리 불가능한 업무 처리

종료 hook에 넣고 싶은 코드가 생기면 먼저 질문해야 한다.

> 이 작업이 SIGKILL 때문에 실행되지 않아도 데이터 정합성이 유지되는가?

대답이 아니면 hook이 아니라 정상 처리 경로와 재시도 가능한 저장소를 다시 설계해야 한다.

---

## 핵심 개념 5: Timeout은 종료 시간보다 짧아야 한다

종료 설계에서 자주 놓치는 것이 내부 timeout이다.

Kubernetes grace period가 60초인데 어떤 외부 API client의 read timeout이 120초라면 어떻게 될까?

```text
T0: 요청 처리 중 외부 API 호출 시작
T5: Pod 종료 시작
T60: grace period 종료, SIGKILL
T120: HTTP client timeout 예정이었지만 프로세스는 이미 죽음
```

이 경우 graceful shutdown은 의미가 약해진다. 진행 중 요청이 외부 I/O에 묶여 grace period 안에 끝나지 못하기 때문이다.

따라서 운영 기준은 다음과 같다.

- HTTP request timeout은 load balancer timeout보다 짧게 둔다.
- 내부 dependency timeout은 request timeout보다 짧게 둔다.
- transaction timeout은 grace period와 배포 중 shutdown budget보다 짧게 둔다.
- message processing timeout은 consumer shutdown timeout보다 짧게 둔다.
- scheduler chunk 처리 시간은 termination grace period보다 짧게 만든다.

예를 들어 주문 API의 request budget이 1초라면 다음처럼 정렬한다.

```text
client timeout: 1500ms
load balancer idle/request timeout: 1200ms
application request budget: 1000ms
payment API timeout: 300ms
inventory API timeout: 150ms
DB query timeout: 200ms
transaction timeout: 800ms
```

이 숫자들은 예시일 뿐이다. 중요한 것은 timeout들이 계층별로 역전되지 않는 것이다.

종료 관점에서는 "평소 timeout"뿐 아니라 "shutdown 중 deadline"도 고려할 수 있다. 종료 중에는 새 retry를 시작하지 않거나, 남은 시간이 짧으면 긴 외부 호출을 포기하는 식이다.

```java
public class ShutdownState {

    private final AtomicBoolean stopping = new AtomicBoolean(false);

    @EventListener(ContextClosedEvent.class)
    public void onClosed() {
        stopping.set(true);
    }

    public boolean isStopping() {
        return stopping.get();
    }
}
```

서비스 코드에서 모든 곳에 종료 상태를 흩뿌리는 것은 좋지 않다. 하지만 오래 걸리는 background worker, retry loop, polling loop에는 종료 상태를 전달하는 것이 유용하다.

```java
while (!shutdownState.isStopping()) {
    OutboxEvent event = outboxRepository.claimNext();
    if (event == null) {
        break;
    }
    publisher.publish(event);
    outboxRepository.markPublished(event.id());
}
```

핵심은 종료 중에 "새로운 긴 작업"을 시작하지 않는 것이다.

---

## 트레이드오프: 얼마나 기다릴 것인가

graceful shutdown의 가장 어려운 결정은 결국 대기 시간이다.

너무 짧으면 진행 중 요청이 깨진다. 너무 길면 배포와 장애 복구가 느려진다.

예를 들어 다음 두 서비스를 비교해 보자.

```text
A. 사용자 조회 API
   - p99 latency: 120ms
   - 대부분 read-only
   - retry 가능
   - 배포 빈도 높음

B. 정산 batch worker
   - chunk 처리 시간: 20~40초
   - DB write 많음
   - 중간 상태 관리 중요
   - 배포 빈도 낮음
```

A에 120초 graceful wait를 주는 것은 과하다. 배포 롤링이 느려지고 장애 Pod 교체가 지연된다. A는 짧은 request timeout과 빠른 drain이 더 중요하다.

B에 10초 grace period를 주면 거의 항상 작업이 중단된다. B는 작업 chunk를 줄이거나 checkpoint를 명확히 하고, shutdown budget을 그에 맞춰 늘려야 한다.

즉 graceful timeout은 조직 표준 하나로 끝내면 안 된다. workload별로 다르게 잡아야 한다.

판단 기준은 다음과 같다.

- 사용자 요청형 API: p99 latency와 load balancer timeout 기준
- streaming/long polling: connection 유지 정책과 재연결 UX 기준
- message consumer: 메시지 한 건 또는 batch 한 chunk 처리 시간 기준
- scheduler: 재개 가능한 chunk 크기 기준
- batch: checkpoint, lock lease, job ownership timeout 기준

또 하나의 트레이드오프는 readiness를 얼마나 빨리 내릴 것인가다.

- 빠르게 내리면 신규 트래픽 유입을 줄일 수 있다.
- 너무 민감하면 일시적 dependency 지연에도 트래픽이 출렁인다.
- probe period가 길면 종료 감지가 늦다.
- failureThreshold가 크면 제거까지 시간이 늘어난다.

운영에서는 배포 중 5xx 지표를 보며 조정해야 한다. readiness probe 설정은 YAML에 한 번 써놓고 잊는 값이 아니라, 라우팅 전파 지연과 서비스 latency를 같이 보며 다듬는 값이다.

---

## 흔한 실수 1: Graceful shutdown을 켰는데 readiness를 그대로 둔다

`server.shutdown=graceful`을 켜면 web server는 진행 중 요청을 기다린다. 하지만 외부 라우터가 여전히 해당 Pod로 트래픽을 보내면 신규 요청이 계속 들어올 수 있다.

종료 중 신규 요청 유입을 줄이려면 readiness가 false가 되어 endpoint에서 빠져야 한다. Actuator probe를 사용하고 있다면 종료 시 readiness 상태가 기대대로 바뀌는지 실제로 확인해야 한다.

확인 방법은 단순하다.

```bash
kubectl delete pod order-api-xxx
kubectl get endpoints order-api -w
kubectl logs order-api-xxx -f
```

그리고 부하를 조금 주면서 배포한다.

```bash
while true; do
  curl -s -o /dev/null -w "%{http_code}\n" https://example.com/orders/health-target
done
```

배포 중 endpoint 제거 시점, 애플리케이션 shutdown log, 5xx 발생 시점이 어떻게 겹치는지 봐야 한다.

---

## 흔한 실수 2: `preStop sleep`을 만능 해결책으로 쓴다

`preStop: sleep 10`은 도움이 될 수 있다. 하지만 문제가 생길 때마다 10초를 30초, 60초로 늘리는 것은 좋은 해결책이 아니다.

sleep이 길어지면 다음 비용이 생긴다.

- rolling update 시간이 길어진다.
- node drain이 느려진다.
- autoscaling scale-in이 지연된다.
- 긴급 rollback이 느려진다.
- 실제 애플리케이션 정리 시간은 줄어들 수 있다.

sleep을 늘리기 전에 봐야 할 것은 다음이다.

- readiness probe period와 failureThreshold
- ingress controller endpoint 반영 지연
- cloud load balancer deregistration delay
- keep-alive connection 처리
- service mesh drain 설정
- 애플리케이션 HTTP graceful shutdown timeout

sleep은 전파 지연을 흡수하는 마지막 완충이다. 핵심 설계는 readiness, connection drain, graceful wait, worker stop 순서에 있다.

---

## 흔한 실수 3: 종료 중에도 retry loop가 계속 돈다

outbox relay, external sync, consumer retry loop에서 자주 보이는 코드다.

```java
while (true) {
    try {
        publishNext();
    } catch (Exception e) {
        Thread.sleep(1000);
    }
}
```

이 코드는 종료에 취약하다.

- interrupt를 무시한다.
- shutdown 상태를 보지 않는다.
- executor shutdownNow에도 계속 버틸 수 있다.
- grace period 안에 끝나지 않는다.
- 실패 원인이 종료 때문인지 실제 장애인지 구분하기 어렵다.

최소한 다음처럼 바꿔야 한다.

```java
while (!shutdownState.isStopping() && !Thread.currentThread().isInterrupted()) {
    try {
        publishNext();
    } catch (RetryablePublishException e) {
        sleeper.sleep(Duration.ofSeconds(1));
    }
}
```

그리고 `InterruptedException`은 삼키지 않는다.

```java
try {
    Thread.sleep(1000);
} catch (InterruptedException e) {
    Thread.currentThread().interrupt();
    return;
}
```

Java 서비스에서 interrupt 처리는 종료 품질을 크게 좌우한다. custom thread, executor, blocking queue, polling loop를 쓰는 코드라면 반드시 확인해야 한다.

---

## 흔한 실수 4: 긴 요청을 graceful shutdown으로 해결하려 한다

요청 하나가 2분 걸리는 API가 있다고 하자. 사용자가 파일을 업로드하고 서버가 동기적으로 변환한 뒤 결과를 반환한다.

이 API에 3분 graceful shutdown을 주면 배포 중 요청 유실은 줄어들 수 있다. 하지만 이것은 근본 해결이 아닐 가능성이 높다.

긴 요청은 여러 문제를 만든다.

- load balancer timeout과 충돌한다.
- 배포가 느려진다.
- 장애 Pod 교체가 느려진다.
- client retry와 중복 처리 가능성이 커진다.
- 서버 thread 또는 memory를 오래 점유한다.

더 나은 설계는 작업을 비동기로 바꾸는 것이다.

```text
POST /exports
  -> export job 생성
  -> 202 Accepted + jobId 반환

worker
  -> job claim
  -> chunk 처리
  -> progress 저장
  -> 완료 시 결과 URL 저장

GET /exports/{jobId}
  -> 상태 조회
```

이 구조에서는 종료 중에도 worker가 chunk 경계에서 멈출 수 있고, 새 Pod가 job을 이어받을 수 있다. graceful shutdown은 긴 요청을 끝까지 붙잡는 도구가 아니라, 긴 작업을 안전하게 멈출 수 있는 구조와 함께 써야 한다.

---

## 흔한 실수 5: 로그에 "종료 시작"과 "종료 완료"만 남긴다

종료 문제는 배포 시점에만 짧게 나타난다. 재현이 어렵다. 그래서 로그와 지표가 없으면 감으로 고치게 된다.

종료 흐름에는 최소한 다음 로그가 필요하다.

```text
shutdown signal received
readiness changed to refusing traffic
http server graceful shutdown started
http server graceful shutdown completed or timed out
scheduler stopped
consumer container stopped
executor shutdown started
executor terminated or timed out
outbox relay stopped
datasource closing
application shutdown completed
```

지표도 유용하다.

- 배포 중 5xx count
- connection reset count
- shutdown duration
- in-flight request count at shutdown
- executor active task count at shutdown
- consumer lag at shutdown
- worker forced stop count
- shutdown timeout count

특히 "종료 시점의 in-flight 작업 수"는 중요하다. 종료가 자주 timeout나는 서비스는 대부분 작업 시간이 길거나 신규 유입 차단이 늦거나 worker가 종료 신호를 무시하고 있다.

---

## 운영 테스트: 로컬에서 Ctrl+C만 눌러서는 부족하다

graceful shutdown은 반드시 배포 환경과 비슷한 조건에서 테스트해야 한다.

로컬 테스트는 시작점이다.

```bash
java -jar app.jar
curl http://localhost:8080/slow-api
kill -TERM <pid>
```

이 테스트로 볼 수 있는 것은 Spring Boot 내부 graceful shutdown 정도다. 하지만 실제 운영 문제는 외부 라우팅과 함께 발생한다.

Kubernetes에서는 다음 테스트가 필요하다.

1. 낮은 부하를 지속적으로 준다.
2. rolling restart를 수행한다.
3. 배포 중 5xx, timeout, connection reset을 측정한다.
4. Pod log에서 shutdown phase별 시간을 본다.
5. endpoint 제거와 ingress 반영 지연을 본다.
6. consumer lag와 중복 처리 로그를 확인한다.
7. `terminationGracePeriodSeconds`를 일부러 짧게 줄여 강제 종료 시 정합성을 확인한다.

예를 들어 다음처럼 실험할 수 있다.

```bash
kubectl rollout restart deployment/order-api
kubectl rollout status deployment/order-api
```

동시에 부하 도구로 요청을 보낸다.

```bash
hey -z 2m -c 20 https://example.com/orders/test
```

그리고 다음을 확인한다.

- rolling restart 중 5xx가 0에 가까운가
- p99 latency가 과도하게 튀지 않는가
- 이전 Pod log에 graceful shutdown timeout이 없는가
- 새 Pod readiness가 충분히 준비된 뒤 트래픽을 받는가
- 종료된 Pod에서 처리 중이던 요청이 정상 응답으로 끝났는가

메시지 consumer는 일부러 처리 도중 SIGTERM을 보내야 한다. 그리고 같은 메시지가 재처리될 때 결과가 깨지지 않는지 확인해야 한다. 중복 로그가 남는 것은 괜찮다. 중복 처리 때문에 주문 상태, 재고, 포인트, 정산 금액이 틀어지는 것이 문제다.

---

## 실무 설계 패턴: 종료 가능한 서비스의 기본 구조

종료에 강한 Spring Boot 서비스는 대체로 다음 구조를 가진다.

```text
Controller
  -> 짧은 request budget
  -> 외부 I/O timeout 명시
  -> 긴 작업은 job으로 위임

Service
  -> transaction boundary 명확
  -> outbox / idempotency / state transition 사용
  -> shutdown hook에 업무 정합성을 의존하지 않음

Worker
  -> SmartLifecycle 또는 container lifecycle에 연결
  -> 새 작업 유입 차단 가능
  -> chunk 단위 처리
  -> interrupt / shutdown flag 존중

Infrastructure
  -> readiness / liveness 분리
  -> graceful shutdown timeout 설정
  -> termination grace period와 timeout 정렬
  -> endpoint drain 지연 측정

Observability
  -> shutdown phase log
  -> in-flight task metric
  -> deployment 중 error rate 추적
```

코드로 보면 핵심은 거창하지 않다. 새 작업 유입을 막고, 진행 중 작업을 추적하고, 제한 시간 안에서 종료하는 것이다.

```java
@Component
public class InFlightTasks {

    private final AtomicInteger count = new AtomicInteger();

    public <T> T track(Supplier<T> supplier) {
        count.incrementAndGet();
        try {
            return supplier.get();
        } finally {
            count.decrementAndGet();
        }
    }

    public int current() {
        return count.get();
    }
}
```

HTTP 요청은 filter에서 추적할 수 있다.

```java
@Component
public class InFlightRequestFilter extends OncePerRequestFilter {

    private final InFlightTasks inFlightTasks;

    public InFlightRequestFilter(InFlightTasks inFlightTasks) {
        this.inFlightTasks = inFlightTasks;
    }

    @Override
    protected void doFilterInternal(
            HttpServletRequest request,
            HttpServletResponse response,
            FilterChain filterChain
    ) throws ServletException, IOException {
        inFlightTasks.track(() -> {
            try {
                filterChain.doFilter(request, response);
                return null;
            } catch (IOException | ServletException e) {
                throw new FilterException(e);
            }
        });
    }
}
```

실제 운영 코드에서는 checked exception wrapping을 더 깔끔하게 처리해야 한다. 목적은 "종료 시점에 현재 처리 중인 작업이 몇 개인지 볼 수 있게 하는 것"이다. 이 지표가 있으면 graceful shutdown timeout이 왜 발생하는지 훨씬 빨리 좁힐 수 있다.

---

## 체크리스트: Spring Boot 종료 처리 점검표

배포 중 오류가 있거나 shutdown 설계를 점검할 때는 아래 항목을 순서대로 본다.

- `server.shutdown=graceful`이 설정되어 있는가
- `spring.lifecycle.timeout-per-shutdown-phase`가 workload에 맞는가
- Kubernetes `terminationGracePeriodSeconds`가 Spring timeout보다 충분히 긴가
- readiness와 liveness endpoint가 분리되어 있는가
- 종료 중 readiness가 false로 바뀌는지 실제로 확인했는가
- `preStop`이 있다면 grace period를 과도하게 잡아먹지 않는가
- cloud load balancer 또는 ingress deregistration delay를 알고 있는가
- keep-alive connection에서 배포 중 connection reset이 발생하지 않는가
- 가장 긴 정상 HTTP 요청 시간이 graceful wait보다 짧은가
- 외부 HTTP client, DB query, transaction timeout이 shutdown budget보다 짧은가
- `@Scheduled` 작업은 종료 신호 이후 새 chunk를 시작하지 않는가
- custom executor는 shutdown과 awaitTermination을 수행하는가
- retry loop는 interrupt와 shutdown flag를 존중하는가
- Kafka/Rabbit consumer는 poll 중단, 처리 완료 대기, offset/ack 전략이 명확한가
- message handler는 중복 처리에 안전한가
- 긴 batch는 checkpoint 또는 chunk 단위 재개가 가능한가
- `@PreDestroy`에 중요한 비즈니스 처리를 의존하지 않는가
- outbox, audit, event publish는 프로세스 종료와 무관하게 재시도 가능한가
- 종료 phase별 로그가 남는가
- 배포 중 5xx, connection reset, shutdown timeout 지표를 보고 있는가
- rolling restart 부하 테스트를 정기적으로 해 봤는가

이 체크리스트의 핵심은 "종료 중에도 정상 경로와 같은 정합성 모델을 유지하는가"다. 종료는 예외 상황이지만, 운영에서는 매일 배포와 scaling으로 반복되는 정상 사건이다.

---

## 한 줄 정리

Spring Boot graceful shutdown을 운영 가능하게 만들려면 HTTP server 옵션만 켜는 데서 끝내지 말고, readiness로 신규 트래픽을 빼고, lifecycle로 worker를 멈추고, timeout과 grace period를 정렬하며, 중간에 끊겨도 재처리 가능한 작업 단위로 서비스를 설계해야 한다.
