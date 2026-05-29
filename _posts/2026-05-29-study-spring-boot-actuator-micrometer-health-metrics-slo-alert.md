---
layout: post
title: "Spring Boot 운영 관측성 실전: Actuator, Micrometer, Health Indicator, SLO Alert로 장애를 먼저 발견하는 법"
date: 2026-05-29 11:50:00 +0900
categories: [java]
tags: [study, java, spring, spring-boot, actuator, micrometer, observability, health-check, metrics, prometheus, slo, alert, operations]
permalink: /java/2026/05/29/study-spring-boot-actuator-micrometer-health-metrics-slo-alert.html
---

## 배경: 로그를 많이 남기는 것과 운영 가능한 관측성은 다르다

Spring Boot 서비스를 운영하다 보면 처음에는 로그만으로도 충분해 보인다.

- 요청이 들어오면 controller에서 로그를 찍는다
- 외부 API를 호출하기 전후에 로그를 찍는다
- 예외가 나면 stack trace를 남긴다
- 배포 후 문제가 생기면 서버에 접속해서 로그를 검색한다

작은 서비스에서는 이 방식이 꽤 오래 버틴다. 하지만 트래픽이 늘고, 인스턴스가 여러 대가 되고, 비동기 처리와 외부 의존성이 많아지는 순간 로그 중심 운영은 금방 한계에 부딪힌다.

실무에서 자주 보는 장면은 이렇다.

- 장애는 났는데 어떤 인스턴스에서 시작됐는지 모른다
- API p95가 올라갔지만 평균 latency는 멀쩡해서 늦게 알아차린다
- DB connection pool이 고갈됐는데 애플리케이션 로그에는 별다른 오류가 없다
- Kubernetes readiness는 통과하는데 실제 비즈니스 요청은 계속 실패한다
- Redis 장애 때문에 주문 API가 느려졌지만 `/actuator/health`는 계속 `UP`이다
- 알림은 많이 오는데 정작 사용자가 영향을 받는지 판단이 안 된다
- 에러율 알림은 울렸지만 이미 SLO를 한참 태운 뒤였다
- 배포 직후 문제가 생겼는데 코드 문제인지 트래픽 변화인지 외부 의존성 문제인지 구분이 어렵다

여기서 흔한 오해가 하나 있다.

> 관측성은 로그, 메트릭, 트레이싱 도구를 붙이는 일이다.

도구는 필요하다. 하지만 운영 관측성의 본질은 도구 설치가 아니라 **서비스의 건강 상태를 사용자의 영향과 운영 의사결정 기준으로 해석할 수 있게 만드는 것**이다.

Spring Boot에서 Actuator와 Micrometer를 붙이는 일 자체는 어렵지 않다. 의존성을 추가하고 endpoint를 열고 Prometheus가 scrape하게 만들면 숫자는 나온다. 문제는 그다음이다.

- 어떤 health check가 배포 트래픽을 막아도 되는 신호인가
- 어떤 metric은 dashboard용이고, 어떤 metric은 pager를 울려야 하는가
- 평균이 아니라 p95, p99를 봐야 하는 지점은 어디인가
- business metric과 infrastructure metric을 어떻게 연결할 것인가
- label을 어디까지 붙이면 유용하고, 어디부터 비용 폭탄인가
- SLO alert는 단순 threshold alert와 어떻게 달라야 하는가
- 알림을 줄이면서도 진짜 장애를 놓치지 않으려면 무엇을 기준으로 삼아야 하는가

이 글은 중급 이상 Spring Boot 개발자를 기준으로 **Actuator, Micrometer, Health Indicator, Prometheus metric, SLO 기반 alert 설계**를 운영 관점에서 정리한다.

초점은 단순 사용법이 아니다.

- health endpoint를 liveness/readiness/startup 관점으로 나누는 법
- Micrometer metric을 cardinality 폭발 없이 설계하는 법
- timer, counter, gauge를 실무에서 어떻게 선택하는지
- endpoint latency, downstream latency, pool saturation을 함께 읽는 법
- SLO와 error budget을 alert 기준으로 바꾸는 법
- 관측성 코드를 비즈니스 코드에 과하게 침투시키지 않는 법

이 글의 결론을 먼저 한 줄로 요약하면 이렇다.

> Spring Boot 관측성의 핵심은 숫자를 많이 수집하는 것이 아니라, **사용자 영향·자원 포화·의존성 실패를 구분해 운영자가 바로 결정을 내릴 수 있는 신호 체계를 만드는 것**이다.

---

## 먼저 큰 그림: 관측성은 "무슨 일이 일어났나"보다 "지금 무엇을 해야 하나"에 답해야 한다

운영 지표를 처음 붙일 때 많은 팀이 dashboard부터 만든다.

- CPU 사용률
- JVM heap
- request count
- HTTP status code
- DB connection count
- Redis command latency
- thread count
- GC time

이 지표들은 모두 필요하다. 하지만 지표가 많다고 운영이 쉬워지는 것은 아니다. 실제 장애 상황에서 더 중요한 질문은 다음이다.

1. 사용자 요청이 실제로 실패하고 있는가
2. 실패가 특정 API에만 국한되어 있는가, 전체 서비스인가
3. 원인은 애플리케이션 내부 오류인가, downstream 지연인가, 자원 포화인가
4. 지금 트래픽을 계속 받아도 되는가, 인스턴스를 빼야 하는가
5. 배포를 롤백해야 하는가, scale out이 필요한가, 외부 의존성 degrade 처리가 필요한가
6. 이 상태가 SLO를 얼마나 빠르게 소모하고 있는가

이 질문에 답하지 못하는 metric은 dashboard 장식에 가깝다. 반대로 이 질문에 답할 수 있는 metric은 몇 개만 있어도 강력하다.

관측성 설계는 보통 네 층으로 나누는 것이 좋다.

### 1. 생존 신호: 프로세스와 런타임은 살아 있는가

- JVM process가 살아 있는가
- event loop 또는 servlet thread가 완전히 멈추지 않았는가
- deadlock, OOM, fatal startup failure가 없는가
- Kubernetes가 container를 재시작해야 하는가

이 층은 liveness와 가깝다. 실패하면 트래픽 우회보다 **프로세스 재시작**이 자연스럽다.

### 2. 수신 가능 신호: 지금 새 트래픽을 받아도 되는가

- 애플리케이션 초기화가 끝났는가
- 필수 dependency와 연결 가능한가
- DB migration, warmup, cache preload가 끝났는가
- connection pool이 완전히 고갈되어 새 요청 처리가 불가능한가

이 층은 readiness와 가깝다. 실패하면 프로세스를 죽이기보다 **load balancer에서 제외**하는 것이 자연스럽다.

### 3. 사용자 영향 신호: 실제 요청 품질은 어떤가

- 성공률이 떨어지는가
- p95/p99 latency가 올라가는가
- 특정 endpoint만 느린가
- 특정 고객군, 지역, 기능에서만 실패하는가
- timeout, rate limit, validation error, business failure를 구분할 수 있는가

이 층은 SLI(Service Level Indicator)의 중심이다. pager alert의 핵심 후보가 된다.

### 4. 원인 추적 신호: 왜 나빠졌는가

- DB pool saturation
- HTTP client connection pool saturation
- downstream API latency
- GC pause
- thread pool queue depth
- Kafka consumer lag
- cache hit ratio
- lock contention

이 층은 원인 분석과 대응에 필요하다. 단독으로 pager를 울리기보다는 사용자 영향 신호와 함께 해석해야 한다.

이 네 층을 분리하지 않으면 운영이 흔들린다. 예를 들어 DB health check 하나를 liveness에 넣어두면 DB가 10초 흔들렸다는 이유로 모든 Pod가 재시작될 수 있다. 반대로 readiness가 너무 관대하면 실제로 요청을 처리하지 못하는 인스턴스가 계속 트래픽을 받는다.

즉 Spring Boot 관측성의 첫 번째 설계 원칙은 이것이다.

> **재시작할 신호, 트래픽에서 뺄 신호, 사용자 영향 신호, 원인 분석 신호를 섞지 않는다.**

---

## 핵심개념 1: Actuator Health는 "전체 서비스 상태"가 아니라 "운영 제어 신호"다

Spring Boot Actuator를 붙이면 `/actuator/health`가 나온다. 많은 팀이 여기서 멈춘다.

```yaml
management:
  endpoints:
    web:
      exposure:
        include: health,info,metrics,prometheus
```

그리고 Kubernetes probe나 load balancer health check에 `/actuator/health`를 그대로 연결한다.

처음에는 잘 동작한다. 하지만 운영에서는 이 단순함이 위험해질 수 있다. `/actuator/health`에 DB, Redis, Kafka, disk space, custom dependency가 모두 묶이면 이 endpoint는 더 이상 하나의 의미를 갖지 않는다.

- DB가 잠깐 느리면 container를 재시작해야 하는가
- Redis가 죽으면 주문 API 전체를 트래픽에서 빼야 하는가
- Kafka broker 연결이 끊기면 HTTP API readiness도 실패해야 하는가
- optional dependency가 죽었는데 핵심 기능까지 막아야 하는가

답은 서비스마다 다르다. 그래서 Actuator health는 단일 endpoint보다 **health group**으로 설계해야 한다.

### liveness와 readiness를 분리하라

Spring Boot는 Kubernetes probe와 연결하기 좋은 health group 구성을 지원한다.

```yaml
management:
  endpoint:
    health:
      probes:
        enabled: true
      show-details: never
      group:
        readiness:
          include: readinessState,db,redis
        liveness:
          include: livenessState
```

이렇게 하면 보통 다음 endpoint를 사용할 수 있다.

- `/actuator/health/liveness`
- `/actuator/health/readiness`

중요한 것은 무엇을 어디에 넣을지다.

### liveness에는 외부 의존성을 넣지 않는 편이 안전하다

liveness는 "이 프로세스를 재시작하면 나아질 가능성이 높은가"에 답해야 한다. DB가 잠깐 죽었다고 애플리케이션 프로세스를 재시작해도 대체로 문제가 해결되지 않는다. 오히려 재시작 폭풍이 생길 수 있다.

liveness에 넣을 만한 것은 보통 내부 생존 신호다.

- Spring application context가 치명적으로 깨졌는가
- 프로세스가 deadlock 상태인가
- 자체 event loop가 멈췄는가
- fatal resource leak로 더 이상 진행이 불가능한가

반대로 아래는 liveness에 조심해야 한다.

- DB 연결
- Redis 연결
- 외부 API 연결
- Kafka broker 상태
- object storage 상태

외부 의존성 장애는 프로세스 재시작으로 해결되지 않는 경우가 많다. liveness에 넣으면 장애 상황에서 모든 Pod가 동시에 죽고 뜨는 더 큰 문제가 생긴다.

### readiness는 "새 요청을 받을 수 있는가"에 답해야 한다

readiness는 조금 다르다. 새 트래픽을 받아도 되는지를 판단해야 하므로 필수 의존성을 포함할 수 있다.

하지만 여기서도 무조건 모든 dependency를 넣으면 안 된다. 핵심은 **요청 처리에 필수인가**다.

예를 들어 주문 생성 API에서 DB가 필수라면 DB readiness 실패 시 트래픽 제외가 자연스럽다. 하지만 추천 API가 optional이고 실패 시 기본 추천으로 degrade할 수 있다면 readiness를 실패시키지 않는 편이 낫다.

의존성은 다음처럼 분류해 볼 수 있다.

| 의존성 | 장애 시 핵심 요청 처리 | readiness 포함 여부 |
| --- | --- | --- |
| Primary DB | 대부분 불가 | 포함 가능 |
| Redis cache | fallback 가능 | 보통 제외 또는 별도 group |
| Kafka producer | 요청 처리와 강결합이면 포함, outbox면 제외 가능 | 설계에 따라 다름 |
| 외부 결제 API | 결제 API에는 필수, 다른 API에는 비필수 | 서비스 경계에 따라 다름 |
| 검색 엔진 | 검색 기능에는 필수, 주문 생성에는 비필수 | 별도 group 권장 |

결국 readiness는 기술 목록이 아니라 **서비스 계약**이다.

### custom HealthIndicator는 간결하고 빠르게 작성하라

Actuator는 custom `HealthIndicator`를 만들 수 있다.

```java
@Component
class PartnerApiHealthIndicator implements HealthIndicator {

    private final PartnerApiClient client;

    PartnerApiHealthIndicator(PartnerApiClient client) {
        this.client = client;
    }

    @Override
    public Health health() {
        try {
            PartnerPingResult result = client.ping(Duration.ofMillis(300));
            if (result.available()) {
                return Health.up()
                        .withDetail("latencyMs", result.latencyMillis())
                        .build();
            }
            return Health.down()
                    .withDetail("reason", "partner_unavailable")
                    .build();
        } catch (Exception e) {
            return Health.down(e)
                    .withDetail("reason", "ping_failed")
                    .build();
        }
    }
}
```

하지만 health check를 만들 때 주의할 점이 많다.

- health check 자체가 느리면 probe가 시스템을 더 괴롭힌다
- 비싼 쿼리를 날리면 장애 상황에서 DB 부하를 키운다
- 외부 API에 실제 비즈니스 요청과 같은 비용의 ping을 보내면 장애를 증폭한다
- timeout 없이 health check를 만들면 probe thread가 쌓인다
- 상세 정보를 외부에 노출하면 내부 구조나 secret hint가 새어 나갈 수 있다

health check는 운영 제어 신호다. 그래서 원칙은 단순하다.

> **빠르고, 싸고, 결정적이며, 실패해도 시스템을 더 망가뜨리지 않아야 한다.**

### Health detail은 환경별로 다르게 노출하라

운영 환경에서 `/actuator/health`에 너무 많은 detail을 노출하면 보안 문제가 된다. DB 종류, host, broker name, 내부 component 이름이 외부에 드러날 수 있다.

```yaml
management:
  endpoint:
    health:
      show-details: when_authorized
  endpoints:
    web:
      exposure:
        include: health,prometheus,info
```

운영에서는 보통 다음 원칙이 안전하다.

- public endpoint에는 `UP/DOWN` 수준만 노출
- 내부망 또는 인증된 운영자에게만 detail 노출
- Prometheus scrape endpoint도 네트워크와 인증으로 보호
- actuator 전체를 외부 인터넷에 열지 않기

Actuator는 편의 기능이지만, 잘못 열면 운영 정보 유출 지점이 된다.

---

## 핵심개념 2: Micrometer는 metric API가 아니라 관측성의 공통 언어다

Spring Boot에서 metric을 다룰 때 사실상 표준은 Micrometer다. Micrometer는 Prometheus, Datadog, New Relic, CloudWatch 같은 backend와 애플리케이션 사이의 facade 역할을 한다.

개발자가 주로 만나는 타입은 다음이다.

- `Counter`: 누적 횟수
- `Timer`: 횟수와 시간 분포
- `DistributionSummary`: 크기나 금액처럼 시간은 아니지만 분포가 중요한 값
- `Gauge`: 현재 상태 값
- `LongTaskTimer`: 오래 지속되는 작업

문제는 어떤 지표를 어떤 타입으로 만들지다.

### Counter: 단조 증가하는 이벤트 수에만 써라

`Counter`는 증가만 하는 값이다. 요청 수, 실패 수, 처리 건수처럼 누적 이벤트에 적합하다.

```java
@Component
class OrderMetrics {

    private final Counter orderCreated;
    private final Counter orderRejected;

    OrderMetrics(MeterRegistry registry) {
        this.orderCreated = Counter.builder("orders.created")
                .description("Created order count")
                .tag("channel", "web")
                .register(registry);

        this.orderRejected = Counter.builder("orders.rejected")
                .description("Rejected order count")
                .tag("reason", "validation")
                .register(registry);
    }

    void recordCreated() {
        orderCreated.increment();
    }

    void recordRejected() {
        orderRejected.increment();
    }
}
```

Counter로 현재 값을 표현하려고 하면 안 된다. 예를 들어 queue size, active thread count, pool usage는 Counter가 아니라 Gauge다.

### Timer: HTTP 요청, DB 호출, 외부 API 호출의 기본 선택지

시간을 재야 한다면 대부분 `Timer`가 맞다.

```java
Timer.Sample sample = Timer.start(meterRegistry);
try {
    return partnerClient.request(command);
} finally {
    sample.stop(Timer.builder("partner.payment.request")
            .description("Partner payment API latency")
            .tag("operation", "authorize")
            .tag("result", resultTag)
            .publishPercentileHistogram()
            .register(meterRegistry));
}
```

Timer는 단순 평균보다 분포를 봐야 한다. 운영에서 평균 latency는 위험한 착시를 만든다.

- 99개 요청이 20ms
- 1개 요청이 5초

이 경우 평균은 그럭저럭 보일 수 있지만 사용자 한 명은 명확히 나쁜 경험을 했다. 그래서 endpoint latency는 보통 p95, p99가 중요하다.

Prometheus를 쓴다면 histogram bucket 설계를 함께 봐야 한다. 모든 metric에 histogram을 켜면 저장 비용이 커진다. 반대로 중요한 요청에 histogram이 없으면 SLO 계산이 어렵다.

### Gauge: 현재 상태를 보여주지만 해석이 까다롭다

Gauge는 현재 값을 나타낸다.

- active connection
- queue depth
- thread pool active count
- cache size
- in-flight request
- circuit breaker state

Gauge는 운영에 매우 유용하지만 alert 기준으로는 조심해야 한다. 순간값이기 때문이다.

예를 들어 DB pool active connection이 95%라고 해서 항상 장애는 아니다. 짧은 burst일 수 있다. 하지만 5분 이상 95%가 지속되고 HTTP p95도 함께 오른다면 강한 신호다.

즉 Gauge는 단독 알림보다 **지속 시간과 사용자 영향 metric과의 조합**이 중요하다.

### DistributionSummary: 크기, 금액, batch size에 적합하다

시간이 아니라 값의 분포를 보고 싶을 때는 `DistributionSummary`를 쓴다.

- 요청 payload size
- batch 처리 row 수
- 파일 업로드 크기
- 주문 금액 분포
- 메시지 크기

이 값들은 평균만 보면 위험하다. payload 평균은 작지만 일부 요청이 너무 커서 GC와 네트워크 병목을 만들 수 있다. batch 평균은 적당하지만 일부 batch가 과도하게 커서 lock 시간을 늘릴 수 있다.

### metric 이름은 도메인과 단위를 드러내야 한다

metric 이름은 나중에 query와 dashboard에서 계속 쓰인다. 처음 대충 지으면 운영자가 고생한다.

좋은 이름은 다음 성격을 가진다.

- 무엇을 재는지 명확하다
- 단위가 드러난다
- 기술 metric과 business metric이 구분된다
- tag 없이도 큰 의미가 있다

예시:

```text
http.server.requests
orders.created
orders.rejected
payment.partner.requests
payment.partner.timeout
batch.import.rows
inventory.reservation.conflicts
```

반대로 이런 이름은 피하는 편이 낫다.

```text
count
latency
api.call
process
service.metric
```

metric은 코드보다 오래 살아남는다. 이름은 운영 인터페이스다.

---

## 핵심개념 3: label/tag cardinality는 관측성 비용과 안정성을 좌우한다

Micrometer에서 tag는 강력하다. endpoint, status, method, exception, outcome 같은 tag 덕분에 metric을 여러 차원으로 자를 수 있다.

하지만 tag는 가장 위험한 지점이기도 하다. 특히 Prometheus 계열에서는 tag 조합 하나하나가 time series가 된다. cardinality가 폭발하면 저장 비용, query 성능, scrape 안정성이 모두 나빠진다.

### 절대 tag로 넣으면 안 되는 값

아래 값은 거의 항상 금지해야 한다.

- userId
- email
- orderId
- requestId
- sessionId
- access token
- raw URL path variable
- exception message 원문
- SQL 원문
- 외부 API error message 원문

예를 들어 아래 코드는 위험하다.

```java
Counter.builder("orders.failed")
        .tag("orderId", orderId.toString())
        .tag("reason", exception.getMessage())
        .register(registry)
        .increment();
```

주문이 100만 건이면 time series가 100만 개가 될 수 있다. 운영 시스템을 망가뜨리는 metric이다.

### URL path variable은 반드시 template으로 정규화하라

HTTP metric에서 자주 터지는 문제가 URI cardinality다.

나쁜 예:

```text
/api/orders/1001
/api/orders/1002
/api/orders/1003
```

좋은 예:

```text
/api/orders/{orderId}
```

Spring Boot의 기본 `http.server.requests` metric은 보통 templated URI를 사용하지만, custom metric을 만들 때 직접 path를 tag에 넣으면 쉽게 망가진다.

### exception tag는 class 수준으로 제한하라

exception message는 cardinality도 높고 민감 정보가 들어갈 수 있다. exception tag가 필요하다면 class name 또는 분류된 error code만 넣는 편이 안전하다.

```java
.tag("exception", ex.getClass().getSimpleName())
.tag("error", mapToStableErrorCode(ex))
```

여기서도 error code는 안정적인 값이어야 한다. `PAYMENT_TIMEOUT`, `VALIDATION_FAILED`, `INSUFFICIENT_STOCK`처럼 제한된 enum이 좋다.

### business tag도 제한된 차원만 허용하라

비즈니스 metric에 tag를 붙이고 싶을 때도 기준이 필요하다.

허용하기 좋은 tag:

- channel: `web`, `mobile`, `admin`, `batch`
- result: `success`, `failure`, `rejected`
- reason: 제한된 enum
- partner: 제한된 외부 파트너 이름
- region: 제한된 서비스 지역
- plan: 제한된 요금제

위험한 tag:

- customer name
- tenant id가 수천 개 이상
- campaign id가 계속 생성됨
- product id가 수십만 개
- dynamic experiment id

tenant별 관측이 꼭 필요하다면 모든 tenant를 metric label로 넣기보다, 상위 tenant만 별도 metric을 만들거나 log/trace/search backend로 넘기는 것이 낫다.

### cardinality 예산을 코드 리뷰 기준에 넣어라

metric tag는 성능 최적화보다 리뷰에서 놓치기 쉽다. 그래서 팀 기준이 필요하다.

- 새 metric 추가 시 예상 time series 수를 적는다
- tag value가 제한된 enum인지 확인한다
- path, id, message 원문은 금지한다
- dashboard에서 실제로 쓸 query를 함께 제안한다
- alert에 쓰일 metric인지, 분석용 metric인지 구분한다

관측성은 공짜가 아니다. 특히 metric cardinality는 조용히 비용과 장애를 만든다.

---

## 핵심개념 4: RED, USE, SLI를 섞어 보면 장애 위치가 빨리 보인다

운영 metric을 어디서부터 봐야 할지 막막하다면 세 가지 관점을 조합하면 좋다.

### RED: 요청 기반 서비스에 적합한 관점

RED는 보통 다음을 뜻한다.

- Rate: 요청 수
- Errors: 실패 수 또는 실패율
- Duration: 요청 시간

HTTP API, gRPC API, 외부 API client metric에 특히 잘 맞는다.

Spring Boot의 기본 HTTP metric인 `http.server.requests`는 RED 관점의 출발점이다.

Prometheus에서는 대략 이런 식으로 볼 수 있다.

```promql
# 요청률
sum(rate(http_server_requests_seconds_count{application="order-api"}[5m])) by (uri, method)

# 5xx 에러율
sum(rate(http_server_requests_seconds_count{application="order-api", status=~"5.."}[5m]))
/
sum(rate(http_server_requests_seconds_count{application="order-api"}[5m]))

# p95 latency
histogram_quantile(
  0.95,
  sum(rate(http_server_requests_seconds_bucket{application="order-api"}[5m])) by (le, uri, method)
)
```

RED는 사용자 영향에 가깝다. "사용자가 느끼는 API 품질이 나빠졌는가"를 빠르게 알려준다.

### USE: 자원 포화 분석에 적합한 관점

USE는 보통 다음을 뜻한다.

- Utilization: 자원이 얼마나 사용 중인가
- Saturation: 대기열이나 포화가 생겼는가
- Errors: 자원 오류가 있는가

DB pool, thread pool, CPU, memory, disk, network, Kafka consumer 같은 자원에는 USE 관점이 좋다.

예를 들어 HikariCP metric은 다음을 봐야 한다.

- active connections
- idle connections
- pending threads
- max connections
- connection acquisition time
- timeout count

DB pool active가 높아도 pending이 없고 acquisition time이 낮으면 아직 버틸 수 있다. 반대로 active가 max에 가깝고 pending thread가 늘며 HTTP p95가 오른다면 DB pool이 병목일 가능성이 높다.

### SLI: 사용자 약속을 수치화한 관점

SLI는 서비스 수준을 판단하는 지표다. 예를 들어 주문 API라면 다음이 될 수 있다.

- 99.9%의 주문 생성 요청이 1초 이내 성공한다
- 결제 승인 요청의 99.95%가 2초 이내 응답한다
- 상품 조회 요청의 99%가 300ms 이내 응답한다
- 배치 정산 작업이 매일 07:00 이전 완료된다

SLI는 metric 중에서도 alert와 의사결정에 직접 연결되는 핵심 지표다.

중요한 점은 모든 metric이 SLI는 아니라는 것이다.

- JVM heap 사용률은 중요하지만 그 자체가 사용자 약속은 아니다
- DB active connection은 중요하지만 그 자체가 사용자 약속은 아니다
- Kafka lag는 중요하지만 어떤 서비스에서는 사용자 영향과 직접 연결되지 않을 수 있다

운영 알림은 가능하면 SLI 중심이어야 한다. 원인 metric은 dashboard와 runbook에서 함께 봐야 한다.

### 세 관점을 함께 쓰는 예

장애 상황을 가정해 보자.

- 주문 생성 API p95가 800ms에서 4초로 상승
- 5xx 에러율은 아직 낮음
- Hikari pending thread 증가
- DB CPU 상승
- Redis metric은 정상
- 최근 배포 없음

이때 RED는 사용자 영향이 latency 중심임을 알려준다. USE는 DB pool과 DB CPU 포화를 보여준다. SLI는 "1초 이내 성공" 약속이 빠르게 깨지고 있음을 알려준다.

대응은 단순히 애플리케이션 재시작이 아니다.

- 느린 쿼리 확인
- DB connection pool 대기 확인
- 최근 트래픽 또는 배치 유입 확인
- 필요 시 heavy endpoint rate limit
- 문제 쿼리 feature flag 차단
- DB scale 또는 index hotfix 검토

좋은 관측성은 이 판단을 빠르게 만든다.

---

## 실무예시 1: 주문 API에 Actuator와 Micrometer를 운영 기준으로 붙이기

주문 API를 예로 들어보자. 이 서비스는 다음 의존성을 가진다.

- PostgreSQL: 주문 저장, 재고 예약 상태 조회
- Redis: 중복 요청 방지와 짧은 캐시
- 외부 결제 API: 결제 승인
- Kafka: 주문 생성 이벤트 발행

이때 모든 의존성을 같은 수준으로 health check에 넣으면 안 된다. 먼저 요청 경로를 나눠야 한다.

### 요청 흐름

1. HTTP 요청 수신
2. idempotency key 검증
3. 주문 command validation
4. 재고 예약
5. 결제 승인
6. 주문 저장
7. outbox 또는 Kafka event 기록
8. 응답 반환

이 구조에서 PostgreSQL은 핵심이다. DB가 안 되면 주문 저장이 불가능하다. Redis는 idempotency에 쓰이지만 DB unique key로 최종 방어가 가능하다면 optional degrade가 가능하다. Kafka는 outbox를 쓴다면 HTTP 요청 처리와 직접 결합하지 않을 수 있다. 외부 결제 API는 결제 요청에는 필수지만 전체 애플리케이션 liveness와는 별개다.

### health group 예시

```yaml
management:
  endpoints:
    web:
      exposure:
        include: health,info,prometheus,metrics
  endpoint:
    health:
      probes:
        enabled: true
      show-details: when_authorized
      group:
        liveness:
          include: livenessState
        readiness:
          include: readinessState,db
        dependencies:
          include: db,redis,paymentPartner,kafka
```

여기서 핵심은 `/health/readiness`와 `/health/dependencies`를 나눈 점이다.

- readiness: load balancer가 트래픽 투입 여부를 판단
- dependencies: 운영자가 의존성 상태를 확인

Redis나 Kafka가 흔들린다고 항상 트래픽을 제외할 필요는 없다. 하지만 운영 dashboard에서는 분명히 보여야 한다.

### 비즈니스 metric 설계

주문 생성에서 필요한 metric을 몇 개만 추려보자.

```text
orders.create.requests
orders.create.completed
orders.create.rejected
orders.create.duration
orders.payment.duration
orders.inventory.reserve.duration
orders.idempotency.duplicates
orders.outbox.pending
```

각 metric의 의미와 tag는 제한적으로 잡는다.

| metric | type | 주요 tag | 설명 |
| --- | --- | --- | --- |
| `orders.create.requests` | Counter | `channel` | 주문 생성 시도 수 |
| `orders.create.completed` | Counter | `channel`, `result` | 최종 완료/실패 수 |
| `orders.create.rejected` | Counter | `reason` | validation, duplicate, sold_out 등 |
| `orders.create.duration` | Timer | `channel`, `result` | 전체 주문 생성 latency |
| `orders.payment.duration` | Timer | `partner`, `result` | 결제 API latency |
| `orders.inventory.reserve.duration` | Timer | `result` | 재고 예약 latency |
| `orders.idempotency.duplicates` | Counter | `channel` | 중복 요청 차단 수 |
| `orders.outbox.pending` | Gauge | 없음 또는 shard | 발행 대기 outbox 수 |

여기서 `orderId`, `userId`, `productId`는 tag로 넣지 않는다. 필요하면 로그나 trace로 추적한다.

### 코드 예시: metric 기록을 도메인 흐름에 과하게 섞지 않기

metric 기록을 service method 곳곳에 흩뿌리면 비즈니스 코드가 지저분해진다. 얇은 recorder를 두는 편이 낫다.

```java
@Component
class OrderCreateMetrics {

    private final MeterRegistry registry;
    private final Counter duplicateCounter;

    OrderCreateMetrics(MeterRegistry registry) {
        this.registry = registry;
        this.duplicateCounter = Counter.builder("orders.idempotency.duplicates")
                .description("Duplicate order create requests blocked by idempotency key")
                .tag("channel", "web")
                .register(registry);
    }

    Timer.Sample start() {
        return Timer.start(registry);
    }

    void recordCompleted(Timer.Sample sample, String channel) {
        sample.stop(Timer.builder("orders.create.duration")
                .description("Order create request duration")
                .tag("channel", channel)
                .tag("result", "success")
                .publishPercentileHistogram()
                .register(registry));
    }

    void recordFailed(Timer.Sample sample, String channel, String reason) {
        sample.stop(Timer.builder("orders.create.duration")
                .description("Order create request duration")
                .tag("channel", channel)
                .tag("result", reason)
                .publishPercentileHistogram()
                .register(registry));

        Counter.builder("orders.create.rejected")
                .description("Rejected order create requests")
                .tag("reason", reason)
                .register(registry)
                .increment();
    }

    void recordDuplicate() {
        duplicateCounter.increment();
    }
}
```

서비스 코드는 이렇게 간결해진다.

```java
@Transactional
public OrderResult create(OrderCommand command) {
    Timer.Sample sample = metrics.start();
    String channel = command.channel().metricValue();

    try {
        IdempotencyResult idempotency = idempotencyService.check(command.key());
        if (idempotency.duplicate()) {
            metrics.recordDuplicate();
            metrics.recordFailed(sample, channel, "duplicate");
            return idempotency.previousResult();
        }

        Order order = orderFactory.create(command);
        inventoryService.reserve(order);
        paymentService.authorize(order);
        orderRepository.save(order);
        outboxRepository.save(OrderCreatedEvent.from(order));

        metrics.recordCompleted(sample, channel);
        return OrderResult.success(order.id());
    } catch (SoldOutException e) {
        metrics.recordFailed(sample, channel, "sold_out");
        throw e;
    } catch (PaymentTimeoutException e) {
        metrics.recordFailed(sample, channel, "payment_timeout");
        throw e;
    }
}
```

실제 프로젝트에서는 AOP, Observation API, decorator pattern을 활용할 수도 있다. 핵심은 metric이 비즈니스 의도를 가리지 않도록 경계를 잡는 것이다.

### HTTP 기본 metric과 custom business metric을 함께 봐야 한다

Spring Boot 기본 HTTP metric만으로는 주문이 왜 실패했는지 알기 어렵다.

- HTTP 400은 validation 실패인지 품절인지 모른다
- HTTP 409는 idempotency duplicate인지 재고 충돌인지 모른다
- HTTP 500은 결제 API timeout인지 DB 오류인지 모른다

반대로 business metric만 보면 전체 HTTP endpoint 품질을 놓칠 수 있다.

그래서 둘을 함께 쓴다.

- `http.server.requests`: endpoint 전체 품질
- `orders.create.*`: 도메인 결과와 실패 이유
- `payment.partner.*`: downstream 결제 품질
- `hikaricp.*`: DB pool 포화 여부

관측성은 한 metric이 모든 답을 주는 구조가 아니라, 여러 신호가 서로 원인을 좁혀 주는 구조여야 한다.

---

## 실무예시 2: SLO와 Alert를 threshold가 아니라 burn rate로 설계하기

많은 팀의 첫 alert는 threshold 기반이다.

- 5xx 에러율이 5% 넘으면 알림
- p95 latency가 1초 넘으면 알림
- CPU가 80% 넘으면 알림
- DB connection pool active가 90% 넘으면 알림

이 방식은 간단하지만 단점이 크다.

- 짧은 spike에도 알림이 울린다
- 낮은 트래픽 시간대에는 비율이 왜곡된다
- 사용자 영향이 없어도 인프라 지표만으로 알림이 온다
- 반대로 SLO를 빠르게 태우는 장애를 늦게 잡을 수 있다

SLO 기반 alert는 생각이 다르다. 먼저 사용자 약속을 정의한다.

예를 들어 주문 생성 API의 SLO를 이렇게 잡을 수 있다.

> 30일 동안 주문 생성 요청의 99.9%는 1초 이내에 성공해야 한다.

그러면 error budget은 0.1%다. 30일 요청 중 0.1%까지는 실패하거나 느릴 수 있지만, 그 이상이면 약속 위반이다.

### 좋은 SLI는 성공 조건을 명확히 가진다

주문 생성 API의 good event를 정의해 보자.

- HTTP status가 2xx 또는 의도된 409 duplicate response
- latency가 1초 이하
- 내부적으로 주문 저장까지 성공

bad event는 다음이다.

- 5xx
- timeout
- 1초 초과 응답
- 결제 승인 후 주문 저장 실패

여기서 4xx를 모두 bad로 볼지 말지는 도메인에 따라 다르다. 사용자의 잘못된 요청으로 인한 validation error를 SLO failure에 포함하면 서비스 품질과 사용자 입력 문제가 섞일 수 있다. 반면 정상 UX에서 자주 발생하는 409 conflict가 실제 사용자 실패라면 포함할 수도 있다.

중요한 것은 팀이 SLI 정의를 합의해야 한다는 점이다.

### Prometheus에서 latency SLO를 계산하는 기본 형태

Prometheus histogram을 쓴다면 1초 이하 요청 비율은 bucket으로 계산할 수 있다.

```promql
sum(rate(http_server_requests_seconds_bucket{uri="/api/orders", method="POST", le="1"}[5m]))
/
sum(rate(http_server_requests_seconds_count{uri="/api/orders", method="POST"}[5m]))
```

1초 초과 비율은 1에서 빼면 된다.

```promql
1 - (
  sum(rate(http_server_requests_seconds_bucket{uri="/api/orders", method="POST", le="1"}[5m]))
  /
  sum(rate(http_server_requests_seconds_count{uri="/api/orders", method="POST"}[5m]))
)
```

여기에 5xx 실패도 합쳐야 한다면 recording rule로 SLI를 정리하는 편이 좋다.

### burn rate alert의 감각

burn rate는 error budget을 얼마나 빠르게 쓰고 있는지를 뜻한다.

- SLO 99.9%면 허용 실패율은 0.1%
- 현재 실패율이 1%면 허용치의 10배로 budget을 태우는 중
- 현재 실패율이 5%면 허용치의 50배로 budget을 태우는 중

단순히 "에러율 1%"보다 "error budget을 10배 속도로 태우고 있다"가 운영 의사결정에 더 가깝다.

실무에서는 보통 multi-window, multi-burn-rate alert를 쓴다.

- 짧은 창: 5분, 10분. 빠른 대형 장애 감지
- 긴 창: 1시간, 6시간. 천천히 누적되는 품질 저하 감지

예시 감각은 다음과 같다.

```text
긴급 알림:
- 5분 burn rate가 매우 높고
- 1시간 burn rate도 함께 높다
- 즉 일시 spike가 아니라 지속 장애일 가능성이 높다

주의 알림:
- 30분 또는 6시간 burn rate가 중간 수준으로 높다
- 당장 전면 장애는 아니지만 SLO를 계속 소모 중이다
```

이 방식은 알림 피로를 줄이는 데 도움이 된다. CPU 90% 같은 증상보다 사용자 약속 위반 속도에 집중하기 때문이다.

### Alert는 원인보다 증상 중심으로 울리고, dashboard는 원인 중심으로 구성하라

Pager를 울리는 alert는 가능한 사용자 영향 중심이어야 한다.

좋은 pager 후보:

- checkout success SLO burn rate 높음
- payment authorization latency SLO burn rate 높음
- login API availability SLO burn rate 높음
- batch settlement deadline miss 예상

나쁜 pager 후보:

- CPU 85%
- heap 75%
- Redis latency 50ms
- 특정 thread count 증가

물론 인프라 metric도 중요하다. 하지만 대부분은 dashboard, warning, ticket, runbook trigger에 더 적합하다. 사용자 영향이 없는 자원 metric만으로 새벽에 사람을 깨우면 팀은 결국 alert를 무시하게 된다.

---

## 트레이드오프 1: Health check는 엄격할수록 안전한가, 관대할수록 안전한가

정답은 없다. health check는 너무 엄격해도, 너무 관대해도 위험하다.

### 너무 엄격한 health check의 문제

- optional dependency 장애에도 전체 인스턴스가 트래픽에서 빠진다
- probe가 외부 장애를 재시작 폭풍으로 증폭한다
- rolling deployment 중 새 Pod가 준비되지 않아 배포가 지연된다
- 일시적인 network blip이 대규모 failover를 만든다

예를 들어 readiness에 Redis를 넣었는데 Redis는 단지 캐시라면, Redis 장애 시 모든 API Pod가 NotReady가 될 수 있다. 실제로 DB fallback으로 서비스가 가능했는데도 load balancer가 트래픽을 보낼 곳을 잃는다.

### 너무 관대한 health check의 문제

- 실제로 요청 처리 불가능한 인스턴스가 계속 트래픽을 받는다
- 배포 직후 warmup이 끝나기 전에 요청이 들어온다
- DB migration 미완료 상태에서 API가 열려 오류가 난다
- connection pool이 완전히 막혔는데도 readiness가 `UP`이다

즉 관대함도 장애를 숨긴다.

### 기준은 "복구 행동"이다

health check에 넣을지 말지는 이 질문으로 판단하는 편이 좋다.

> 이 신호가 실패했을 때 운영 시스템이 취할 행동은 무엇인가?

- liveness 실패 → container 재시작
- readiness 실패 → traffic drain
- dependency health 실패 → 운영자 확인, dashboard 표시
- SLO alert 실패 → incident 대응

복구 행동이 다르면 endpoint도 다르게 나눠야 한다. 하나의 `/health`에 모든 의미를 넣는 순간 제어가 어려워진다.

---

## 트레이드오프 2: Metric을 많이 만들수록 좋은가, 적게 만들수록 좋은가

metric은 부족하면 원인 분석이 안 되고, 많으면 비용과 혼란이 커진다. 균형이 필요하다.

### metric이 부족할 때

- 장애 원인을 로그 검색에 의존한다
- 배포 전후 성능 비교가 어렵다
- 특정 endpoint만 느린지 전체가 느린지 모른다
- downstream별 latency 차이를 모른다
- business failure와 technical failure가 섞인다

### metric이 과할 때

- dashboard가 너무 많아 아무도 보지 않는다
- cardinality가 폭발한다
- 저장 비용이 늘어난다
- query가 느려진다
- alert가 많아져 무시된다
- 코드 곳곳에 metric 기록이 퍼져 유지보수가 어려워진다

### 추천 기준: 핵심 흐름부터 수직으로 관측하라

처음부터 모든 기능에 metric을 붙이기보다 핵심 사용자 흐름을 하나 고르고, 수직으로 관측하는 편이 낫다.

예를 들어 커머스라면:

1. 상품 조회
2. 장바구니
3. 주문 생성
4. 결제 승인
5. 주문 완료 이벤트 발행

각 흐름에 대해 다음만 먼저 잡아도 큰 효과가 있다.

- 요청 수
- 성공률
- p95/p99 latency
- 주요 실패 reason
- 핵심 downstream latency
- 주요 resource saturation

이후 장애 회고와 운영 질문을 바탕으로 metric을 추가한다. 관측성은 처음부터 완벽한 설계가 아니라, 운영 학습을 반영해 진화하는 체계다.

---

## 트레이드오프 3: Business metric을 애플리케이션에 넣을 것인가, 이벤트/분석 파이프라인에서 볼 것인가

주문 수, 결제 실패율, 재고 충돌 수 같은 business metric은 애플리케이션 metric으로도 볼 수 있고, 이벤트나 DW에서 분석할 수도 있다. 둘은 목적이 다르다.

### 애플리케이션 metric의 장점

- 거의 실시간으로 볼 수 있다
- alert에 연결하기 쉽다
- 배포 직후 이상 징후를 빠르게 감지한다
- 기술 metric과 같은 dashboard에서 correlation이 가능하다

### 애플리케이션 metric의 단점

- cardinality 제한이 강하다
- 장기 분석에는 부적합할 수 있다
- 정정, 보정, attribution이 어렵다
- metric backend 비용이 커질 수 있다

### 이벤트/분석 파이프라인의 장점

- 풍부한 차원 분석이 가능하다
- 사용자, 상품, 캠페인 단위 분석에 적합하다
- 장기 보관과 재처리가 가능하다
- BI와 연결하기 좋다

### 이벤트/분석 파이프라인의 단점

- 실시간성이 떨어질 수 있다
- 장애 alert에는 늦을 수 있다
- 파이프라인 지연과 서비스 장애를 구분해야 한다

실무 기준은 간단하다.

- **운영 즉시 대응이 필요한 값**은 애플리케이션 metric
- **풍부한 분석과 장기 집계가 필요한 값**은 이벤트/분석 파이프라인

예를 들어 결제 승인 실패율은 애플리케이션 metric으로 있어야 한다. 하지만 상품별 결제 실패율, 캠페인별 전환율은 분석 파이프라인이 더 적합하다.

---

## 흔한실수 1: `/actuator`를 외부에 너무 넓게 노출한다

Actuator endpoint는 운영에 편하지만 민감하다.

위험한 노출 예:

```yaml
management:
  endpoints:
    web:
      exposure:
        include: "*"
```

운영에서 `env`, `beans`, `configprops`, `heapdump`, `threaddump`, `loggers` 같은 endpoint가 외부에 열리면 보안 사고로 이어질 수 있다.

권장 원칙은 다음이다.

- 외부 공개망에는 health 정도만 제한적으로 노출
- Prometheus endpoint는 내부망 또는 인증된 scrape 경로만 허용
- 민감 endpoint는 운영자 인증과 네트워크 제한을 함께 적용
- `show-details`는 `when_authorized` 또는 `never`
- management port를 애플리케이션 port와 분리하는 것도 고려

```yaml
management:
  server:
    port: 9090
  endpoints:
    web:
      exposure:
        include: health,prometheus,info
  endpoint:
    health:
      show-details: when_authorized
```

도구를 켜는 것보다 안전하게 노출하는 것이 먼저다.

---

## 흔한실수 2: 평균 latency만 보고 p95/p99를 놓친다

평균은 운영 품질을 과소평가하기 쉽다. 특히 사용자 경험은 tail latency에 민감하다.

예를 들어 1분 동안 100개 요청이 있었다.

- 95개는 80ms
- 4개는 900ms
- 1개는 8초

평균은 약 160ms 근처로 보일 수 있다. dashboard는 멀쩡해 보인다. 하지만 실제로는 일부 사용자가 매우 나쁜 경험을 했다. p95, p99를 봐야 이 문제가 드러난다.

Spring Boot + Prometheus에서 p95/p99를 제대로 보려면 histogram 설정을 신중히 해야 한다.

```yaml
management:
  metrics:
    distribution:
      percentiles-histogram:
        http.server.requests: true
      slo:
        http.server.requests: 100ms,300ms,500ms,1s,2s,5s
```

모든 metric에 무작정 histogram을 켜면 비용이 커진다. 핵심 endpoint, 핵심 downstream client부터 적용하는 것이 현실적이다.

---

## 흔한실수 3: health check에 비싼 쿼리나 외부 호출을 넣는다

health check는 자주 호출된다. Kubernetes probe, load balancer, monitoring system이 계속 두드린다. 여기에 비싼 작업을 넣으면 health check가 장애를 감지하는 것이 아니라 장애를 만든다.

나쁜 예:

- 대량 row count 쿼리
- 여러 테이블 join
- 외부 결제 API 실제 승인 테스트
- Kafka topic metadata 전체 조회
- object storage list operation
- timeout 없는 HTTP call

좋은 health check는 다음에 가깝다.

- DB: 짧은 validation query 또는 connection check
- Redis: 짧은 ping, 제한된 timeout
- 외부 API: 전용 lightweight ping endpoint, 짧은 timeout
- Kafka: 애플리케이션 요청 처리에 필요한 최소 상태만 확인

또한 health check 실패가 실제 요청 실패와 완전히 같은 의미인지도 검토해야 한다. health check만 실패하고 실제 요청은 되는 상황, 또는 그 반대 상황이 생길 수 있다.

---

## 흔한실수 4: metric tag에 id를 넣어 cardinality를 폭발시킨다

가장 조용하고 비싼 실수다. 처음에는 문제없이 보인다. 하지만 트래픽이 늘면서 Prometheus 저장소가 커지고 query가 느려지고 scrape가 불안정해진다.

나쁜 tag:

```text
userId=123456
orderId=ORD-20260529-0001
requestId=6f2b...
path=/api/orders/123456
exception=Payment failed for order ORD-...
```

좋은 tag:

```text
channel=web
result=success
reason=payment_timeout
uri=/api/orders/{orderId}
exception=PaymentTimeoutException
```

팀 차원에서 `MeterFilter`로 일부 tag를 제한하는 것도 방법이다.

```java
@Bean
MeterFilter denyHighCardinalityTags() {
    return MeterFilter.deny(id -> id.getTags().stream().anyMatch(tag ->
            tag.getKey().equals("userId") ||
            tag.getKey().equals("orderId") ||
            tag.getKey().equals("requestId")
    ));
}
```

물론 모든 위험 tag를 코드로 막을 수는 없다. 리뷰 기준과 운영 비용 인식이 함께 필요하다.

---

## 흔한실수 5: Alert를 너무 많이 만들어 결국 아무도 믿지 않게 한다

알림은 많을수록 안전한 것이 아니다. 오히려 너무 많은 알림은 사람을 무디게 만든다.

나쁜 alert의 특징:

- 대응 행동이 명확하지 않다
- 사용자 영향이 없다
- 자주 울리지만 대부분 자동 회복된다
- 원인 metric 하나만 보고 울린다
- runbook이 없다
- 누가 봐야 하는지 ownership이 없다

좋은 alert는 다음 질문에 답해야 한다.

1. 지금 사용자가 영향을 받고 있는가
2. 이 알림을 받은 사람이 10분 안에 할 수 있는 행동이 있는가
3. 무시하면 SLO나 데이터 정합성이 깨지는가
4. 알림 메시지에 dashboard와 runbook 링크가 있는가
5. 최근 배포, dependency 상태, 주요 metric을 함께 볼 수 있는가

alert는 운영 계약이다. 만들기보다 줄이고 다듬는 일이 더 중요하다.

---

## 흔한실수 6: 로그, metric, trace의 역할을 구분하지 않는다

관측성 도구는 서로 대체재가 아니다.

### Metric

- 집계된 수치
- alert와 trend 파악에 강함
- cardinality 제한이 중요
- 개별 요청 디버깅에는 약함

### Log

- 사건의 상세 문맥
- 특정 요청, 특정 예외 분석에 강함
- 너무 많으면 비용과 검색 난이도 증가
- sampling과 구조화가 중요

### Trace

- 요청 경로와 span 간 시간 관계
- microservice와 downstream latency 분석에 강함
- sampling 정책이 중요
- 모든 비즈니스 사실을 담는 저장소가 아님

운영에서 좋은 흐름은 보통 이렇다.

1. SLO alert가 울린다
2. dashboard에서 어떤 API와 dependency가 나쁜지 본다
3. trace에서 느린 span을 확인한다
4. log에서 특정 error code와 request id를 따라간다
5. 필요하면 DB slow query, thread dump, heap dump로 내려간다

metric이 첫 신호, trace가 경로, log가 문맥이다. 셋을 같은 역할로 쓰면 비용만 늘고 효과는 줄어든다.

---

## 체크리스트: Spring Boot 관측성 설계 리뷰 기준

아래 체크리스트는 새 서비스나 운영 개선 작업에서 바로 사용할 수 있다.

### Actuator 노출

- [ ] 운영에서 노출할 endpoint 목록이 최소화되어 있는가
- [ ] `/actuator/prometheus`는 내부망 또는 인증된 경로로만 접근 가능한가
- [ ] health detail은 인증되지 않은 사용자에게 노출되지 않는가
- [ ] management port와 application port 분리 필요성을 검토했는가
- [ ] `env`, `configprops`, `heapdump`, `threaddump`, `loggers` 노출 정책이 명확한가

### Health check

- [ ] liveness와 readiness가 분리되어 있는가
- [ ] liveness에 외부 dependency를 넣지 않았는가
- [ ] readiness는 실제 새 요청 수신 가능성을 반영하는가
- [ ] optional dependency는 별도 health group 또는 dashboard로 분리했는가
- [ ] custom health check에는 짧은 timeout이 있는가
- [ ] health check가 비싼 쿼리나 실제 비즈니스 요청을 수행하지 않는가
- [ ] probe 실패 시 운영 시스템의 행동이 명확한가

### Metric 설계

- [ ] 핵심 API의 rate, error, duration을 볼 수 있는가
- [ ] 핵심 downstream의 latency와 error를 볼 수 있는가
- [ ] DB pool, thread pool, queue depth 같은 saturation metric을 볼 수 있는가
- [ ] business failure reason이 제한된 enum으로 기록되는가
- [ ] metric 이름에 의미와 단위가 드러나는가
- [ ] Counter, Timer, Gauge, DistributionSummary 선택이 적절한가
- [ ] histogram이 필요한 핵심 metric에만 적용되어 있는가

### Tag/Cardinality

- [ ] userId, orderId, requestId, sessionId가 tag로 들어가지 않는가
- [ ] URI는 path variable이 아니라 template으로 기록되는가
- [ ] exception message 원문이 tag로 들어가지 않는가
- [ ] tag value는 제한된 집합인가
- [ ] 신규 metric의 예상 time series 수를 리뷰했는가
- [ ] tenant/product/campaign 같은 고카디널리티 차원은 별도 분석 체계로 보냈는가

### SLO/Alert

- [ ] 핵심 사용자 흐름의 SLI가 정의되어 있는가
- [ ] SLO가 availability와 latency를 함께 고려하는가
- [ ] alert는 단순 threshold보다 SLO burn rate 중심인가
- [ ] pager alert는 사용자 영향 중심인가
- [ ] 원인 metric은 dashboard와 runbook에 연결되어 있는가
- [ ] 알림마다 대응 행동과 owner가 있는가
- [ ] noisy alert를 정기적으로 제거하거나 조정하는가

### 운영 대시보드

- [ ] 첫 화면에서 요청량, 에러율, p95/p99 latency를 볼 수 있는가
- [ ] 최근 배포 시점과 metric 변화를 함께 볼 수 있는가
- [ ] downstream별 latency와 error가 분리되어 있는가
- [ ] resource saturation과 사용자 영향 metric을 함께 볼 수 있는가
- [ ] 핵심 business metric이 기술 metric과 같은 시간축에서 보이는가

---

## 실무 적용 순서: 한 번에 완성하려 하지 말고 핵심 경로부터 닫아라

관측성 개선은 범위가 커지기 쉽다. 그래서 순서가 중요하다.

### 1단계: Actuator를 안전하게 노출한다

- health, info, prometheus만 우선 노출
- 외부 접근 제어 확인
- liveness/readiness 분리
- show-details 정책 정리

### 2단계: 기본 HTTP metric을 신뢰할 수 있게 만든다

- URI template 정규화 확인
- status, method, outcome tag 확인
- 핵심 endpoint histogram 설정
- p95/p99 dashboard 구성

### 3단계: 핵심 downstream metric을 붙인다

- DB pool
- HTTP client latency
- Redis latency
- Kafka publish/consume 상태
- 외부 API timeout/error

여기서 중요한 것은 client별, operation별로 볼 수 있어야 한다는 점이다. 모든 외부 API를 `external.request` 하나로 합치면 원인 분석이 어렵다.

### 4단계: business metric을 제한적으로 추가한다

- 주문 생성 성공/실패
- 결제 승인 성공/실패
- idempotency duplicate
- 재고 충돌
- outbox pending
- batch processed rows

business metric은 많지 않아도 된다. 운영 의사결정에 직접 쓰는 것부터 추가한다.

### 5단계: SLO와 alert를 정리한다

- 핵심 API의 good/bad event 정의
- latency threshold 합의
- error budget 계산
- burn rate alert 구성
- noisy infra alert 정리
- runbook 연결

### 6단계: 장애 회고로 metric을 갱신한다

장애가 끝나면 반드시 묻는다.

- 어떤 신호가 가장 먼저 나빠졌는가
- 어떤 신호가 있었으면 더 빨리 알 수 있었는가
- 어떤 dashboard가 도움이 되지 않았는가
- 어떤 alert가 너무 늦었거나 너무 시끄러웠는가
- 어떤 tag나 metric이 원인 분석을 방해했는가

관측성은 회고를 먹고 자란다. 장애를 겪고도 metric 체계가 그대로라면 같은 문제를 다시 겪을 가능성이 높다.

---

## 운영 기준 예시: 주문 서비스 Dashboard 한 장으로 보기

첫 화면 dashboard는 너무 많은 정보를 담지 않는 편이 좋다. 예를 들어 주문 서비스라면 다음 정도가 적당하다.

### 상단: 사용자 영향

- 주문 생성 요청량
- 주문 생성 성공률
- 주문 생성 p50/p95/p99 latency
- 결제 승인 성공률
- 결제 승인 p95 latency
- SLO burn rate

### 중단: 주요 실패 이유

- validation rejected
- duplicate idempotency key
- sold out
- payment timeout
- payment rejected
- database error
- unexpected exception

### 하단: 원인 후보

- Hikari active/idle/pending
- DB query latency 또는 slow query count
- HTTP client pool usage
- Redis command latency
- Kafka/outbox pending
- JVM GC pause
- Tomcat busy threads

이렇게 구성하면 장애 때 시선 이동이 자연스럽다.

1. 사용자가 영향받는가
2. 어떤 기능이 나쁜가
3. 어떤 실패 이유가 늘었는가
4. 어떤 의존성 또는 자원이 같이 나빠졌는가

Dashboard는 예쁜 그래프 모음이 아니라 사고 대응 화면이어야 한다.

---

## 한줄정리

Spring Boot에서 Actuator와 Micrometer를 붙이는 것은 시작일 뿐이고, 운영 가능한 관측성은 **liveness/readiness/의존성 상태를 분리하고, 낮은 cardinality의 핵심 metric으로 RED·USE·SLI를 연결하며, threshold가 아니라 SLO burn rate로 사용자 영향을 먼저 감지하는 설계**에서 완성된다.
