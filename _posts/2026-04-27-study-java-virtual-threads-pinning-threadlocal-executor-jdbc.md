---
layout: post
title: "Java Virtual Threads 실전: Pinning, ThreadLocal, Executor, JDBC 경계를 운영 기준으로 이해하기"
date: 2026-04-27 11:40:00 +0900
categories: [java]
tags: [study, java, concurrency, virtual-thread, loom, threadlocal, executor, jdbc, backend, performance]
permalink: /java/2026/04/27/study-java-virtual-threads-pinning-threadlocal-executor-jdbc.html
---

## 배경: 왜 스레드를 늘리면 처리량이 오르지 않고, 비동기로 바꾸면 코드가 망가질까?

Java 백엔드에서 동시성 문제를 다루다 보면 두 가지 극단 사이를 오가게 된다.

- 플랫폼 스레드 기반 thread-per-request 모델은 이해하기 쉽지만, 동시 접속이 늘면 스레드 수와 메모리, 컨텍스트 스위칭 비용이 빠르게 한계에 닿는다
- 반대로 비동기·리액티브 모델은 높은 동시성을 만들 수 있지만, 콜백/체인 중심 코드가 복잡해지고 디버깅과 장애 분석 난이도가 크게 올라간다

그래서 많은 팀이 한 번쯤 이런 기대를 품는다.

> Virtual Threads만 켜면 기존 blocking 코드 그대로 초고성능 서버가 되지 않을까?

여기서 사고가 시작된다.

실무에서는 보통 이런 식으로 실패한다.

- 기존 `fixedThreadPool(200)`을 `newVirtualThreadPerTaskExecutor()`로만 바꿨는데도 응답 시간이 크게 나아지지 않는다
- 스레드는 수만 개가 떠도 결국 DB connection pool 30개에서 다 막힌다
- `synchronized` 안에서 JDBC나 HTTP 호출을 하다가 carrier thread pinning 때문에 기대한 확장성이 안 나온다
- `ThreadLocal`에 사용자 정보, 권한, 거대한 캐시, request-scoped 객체를 이것저것 넣어 두었다가 메모리 사용량과 추적 복잡도가 커진다
- CPU bound 작업까지 가상 스레드로 밀어 넣었다가 오히려 runnable이 과도하게 몰려 tail latency가 증가한다
- “스레드가 싸다”는 말만 믿고 backpressure 없이 다운스트림 호출을 폭증시켜 외부 시스템을 먼저 무너뜨린다

즉 Virtual Threads의 핵심은 “스레드를 많이 만들어도 된다”가 아니라,
**어떤 병목이 스레드였고 어떤 병목은 여전히 스레드가 아닌지를 구분하는 능력**이다.

이 글은 중급 이상 개발자를 기준으로 다음 질문에 답하는 데 집중한다.

1. Virtual Threads는 정확히 무엇을 싸게 만든 것인가
2. 왜 “더 빠른 스레드”가 아니라 “더 많은 대기 동시성”을 위한 도구라고 해야 하는가
3. pinning, `ThreadLocal`, JDBC, 외부 API, CPU task가 각각 어떤 병목을 만드는가
4. virtual-thread adoption에서 무엇을 바꾸고, 무엇은 그대로 두고, 무엇은 오히려 더 엄격히 관리해야 하는가
5. 운영에서 어떤 지표와 도구로 효과와 부작용을 확인해야 하는가

---

## 먼저 큰 그림: Virtual Threads는 비동기 프로그래밍의 대체재라기보다, blocking 스타일을 다시 확장 가능하게 만드는 장치다

Virtual Threads를 이해할 때 가장 먼저 버려야 할 오해는 이것이다.

> Virtual Threads는 CPU를 더 빨리 돌리는 기술이다.

아니다. Virtual Threads의 핵심 가치는 **속도(speed)** 보다 **동시성(concurrency)** 에 있다.

예를 들어 요청 하나가 아래 순서로 동작한다고 하자.

1. HTTP 요청 수신
2. 인증 조회
3. DB 조회
4. 외부 결제/정책 API 호출
5. 응답 생성

이 요청의 대부분 시간은 CPU 계산보다 **대기(waiting)** 에 쓰인다.

- 소켓 읽기 대기
- DB 응답 대기
- 외부 API 응답 대기
- 잠깐의 락 대기

플랫폼 스레드에서는 요청 하나가 대기하는 동안에도 OS 스레드 하나를 계속 점유한다. 동시 요청이 늘면 결국 OS 스레드 수가 제약이 된다.

Virtual Threads는 여기서 모델을 바꾼다.

- 요청은 여전히 “스레드 하나”로 순차적 코드 안에서 처리한다
- 하지만 blocking I/O를 기다리는 동안에는 그 virtual thread가 carrier(OS) thread를 계속 붙잡고 있지 않는다
- 그 사이 carrier thread는 다른 virtual thread 실행에 재사용될 수 있다

즉 얻는 것은 다음과 같다.

- 코드 스타일은 thread-per-request 그대로 유지
- 동시 대기 수는 훨씬 크게 확장
- stack trace, 디버깅, 예외 전파, 로컬 변수 기반 코드는 비교적 단순하게 유지

하지만 이것이 의미하는 바는 분명하다.

- **대기 시간이 많은 I/O 중심 서비스**에서는 효과가 크다
- **CPU를 오래 태우는 계산 중심 서비스**에서는 효과가 제한적이다
- **스레드 병목**은 줄여주지만 **DB pool, rate limit, 락 경합, 다운스트림 용량 병목**은 그대로 남는다

Virtual Threads는 “복잡한 비동기 코드를 안 써도 높은 동시성을 만들 수 있게 해 주는 것”이지,
“용량 계획을 안 해도 되는 면허증”이 아니다.

---

## 핵심 개념 1: Virtual Thread는 “가벼운 요청 단위”이지 “미리 만들어 두는 자원 풀”이 아니다

플랫폼 스레드 시대에 팀들이 익숙해진 습관 하나가 있다.

- 스레드는 비싸다
- 그러니 풀링해야 한다
- pool size를 잘 정해야 한다

이 습관을 그대로 Virtual Threads에 가져오면 바로 삐끗한다.

Virtual Threads는 값싼 task carrier다. 따라서 기본 발상은 다음과 같이 바뀌어야 한다.

- **작업마다 새 virtual thread를 만든다**
- 스레드 자체를 풀링하지 않는다
- 대신 진짜 희소 자원만 별도로 제한한다

가장 단순한 형태는 이렇다.

```java
try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
    Future<UserProfile> profile = executor.submit(() -> profileClient.fetch(userId));
    Future<List<Order>> orders = executor.submit(() -> orderRepository.findRecentOrders(userId));
    Future<CouponInfo> coupon = executor.submit(() -> couponClient.getAvailableCoupons(userId));

    return new DashboardResponse(
            profile.get(),
            orders.get(),
            coupon.get()
    );
}
```

이 코드의 장점은 단순하다.

- 각 작업이 순차 코드처럼 읽힌다
- 예외가 스레드 경계 밖으로 자연스럽게 전파된다
- 스레드 생성 비용에 대한 과도한 공포 없이 작업 단위 분리가 가능하다

여기서 중요한 건 **“스레드를 제한하는 대신 자원을 제한한다”** 는 관점 전환이다.

예를 들어 아래는 나쁜 습관이다.

```java
ExecutorService executor = Executors.newFixedThreadPool(200);
```

플랫폼 스레드에서는 이것이 “동시성 제한 + 자원 보호” 역할도 어느 정도 했다. 하지만 Virtual Threads로 가면 이 책임을 분리해야 한다.

- 스레드 수 제한은 더 이상 핵심 제어점이 아니다
- DB connection 수, 외부 API QPS, downstream concurrency, 메모리 사용량이 핵심 제어점이다

즉 Virtual Threads 시대의 기본 질문은 이것이다.

> 지금 내가 제한하려는 것은 정말 스레드인가, 아니면 다른 병목인가?

---

## 핵심 개념 2: mount / unmount / parking을 이해해야 pinning 문제를 읽을 수 있다

Virtual Thread는 실행될 때 carrier thread에 **mount** 된다. 그리고 blocking I/O나 park 가능한 지점에서 멈출 때는 carrier에서 **unmount** 될 수 있다. 이게 핵심이다.

- 실행 중: virtual thread가 어떤 carrier 위에서 돌고 있다
- 대기 가능 지점 도달: virtual thread가 내려오고 carrier가 풀린다
- 재개 가능 시점: 다른 carrier에 다시 mount되어 이어서 실행될 수 있다

이 메커니즘 덕분에 수많은 virtual thread가 적은 수의 OS thread를 공유할 수 있다.

문제는 **pinning** 이다.

pinning은 virtual thread가 대기 중이어도 carrier를 놓지 못하는 상태다. 대표적으로 조심해야 할 상황은 다음과 같다.

- `synchronized` 블록/메서드 안에서 오래 걸리는 blocking 작업을 수행할 때
- native method 또는 foreign function 호출 구간이 길 때

pinning이 곧 버그는 아니다. 하지만 확장성에는 큰 악영향을 줄 수 있다.

예를 들어 아래 코드는 위험하다.

```java
public class InventoryGateway {
    private final Object monitor = new Object();

    public InventorySnapshot refresh(String productId) {
        synchronized (monitor) {
            InventorySnapshot snapshot = inventoryClient.fetch(productId); // 오래 걸릴 수 있는 I/O
            cache.put(productId, snapshot);
            return snapshot;
        }
    }
}
```

문제는 임계구역 안에서 실제 희소 자원이 “자바 객체 상태”가 아니라 “느린 I/O”가 되어 버렸다는 점이다.

- lock을 오래 잡는다
- virtual thread는 pinning될 수 있다
- carrier thread가 장시간 묶인다
- 동시성 확장 효과가 기대보다 크게 줄어든다

더 나은 기준은 아래다.

1. **짧은 메모리 상태 변경만 임계구역에 둔다**
2. 오래 걸리는 I/O는 lock 밖으로 뺀다
3. 꼭 명시적 락이 필요하면 `ReentrantLock` 등 대안을 검토한다
4. pinning이 실제 병목인지 JFR로 확인한다

예를 들면:

```java
public class InventoryGateway {
    private final ReentrantLock lock = new ReentrantLock();

    public InventorySnapshot refresh(String productId) {
        InventorySnapshot latest = inventoryClient.fetch(productId);

        lock.lock();
        try {
            cache.put(productId, latest);
            return latest;
        } finally {
            lock.unlock();
        }
    }
}
```

여기서 포인트는 “무조건 `synchronized`를 버려라”가 아니다.

- 짧고 빈도가 낮은 임계구역이면 `synchronized`도 충분히 좋다
- 문제는 **오래 걸리는 blocking 작업을 락 안에 넣는 습관**이다
- Virtual Threads는 이 안티패턴을 더 빨리 드러나게 만들 뿐이다

---

## 핵심 개념 3: Virtual Threads는 JDBC connection pool을 없애주지 않는다

현실의 많은 Java 서비스에서 가장 큰 병목은 스레드보다 DB다.

예를 들어:

- 웹 요청 동시성 8,000
- virtual thread 수 8,000+
- HikariCP 최대 connection 40

이 상황에서 8,000개의 요청이 동시에 DB를 두드리면 어떻게 될까?

답은 간단하다.

- 스레드는 많이 만들 수 있다
- 하지만 DB connection은 40개뿐이다
- 나머지는 pool 대기열에서 기다린다
- 결국 처리량 상한은 DB가 결정한다

즉 Virtual Threads의 의미는 “DB 없이도 된다”가 아니라,
**DB를 기다리는 동안 OS thread를 낭비하지 않는다**에 가깝다.

이 차이는 매우 중요하다.

### 좋은 효과

- DB 대기 중인 요청이 많아도 플랫폼 스레드 폭증을 줄일 수 있다
- thread-per-request 스타일을 유지한 채 높은 대기 동시성을 수용할 수 있다

### 그대로 남는 문제

- connection pool size가 작으면 전체 latency는 여전히 커진다
- 느린 쿼리, 잠금 대기, long transaction은 그대로 치명적이다
- DB가 감당 못 할 수준으로 요청을 몰아넣으면 장애 지점만 뒤로 밀린다

그래서 Virtual Threads 도입 시 자주 필요한 패턴이 **희소 자원 앞단 제한**이다.

```java
public class ReportService {
    private final Semaphore dbSlots = new Semaphore(30);

    public Report generate(ReportCommand command) {
        dbSlots.acquireUninterruptibly();
        try {
            return reportRepository.generate(command);
        } finally {
            dbSlots.release();
        }
    }
}
```

이 패턴은 “스레드를 30개만 쓰자”가 아니다.

- virtual thread는 얼마든지 생성 가능
- 하지만 **DB에 동시에 들어가는 작업 수**는 정책적으로 제한
- 대기 자체는 값싼 virtual thread가 담당

실무에서는 이 사고 전환이 중요하다.

> 플랫폼 스레드 풀은 종종 “숨은 backpressure 장치” 역할을 했다. Virtual Threads로 갈 때는 그 역할을 의식적으로 다시 설계해야 한다.

---

## 핵심 개념 4: `ThreadLocal`은 다시 쓸 수 있지만, 공짜라고 생각하면 안 된다

JDK 21의 Virtual Threads는 `ThreadLocal`을 지원한다. 그래서 많은 기존 라이브러리와 프레임워크가 큰 수정 없이 동작한다. 이 점은 도입 장벽을 크게 낮춘다.

하지만 여기서 또 다른 오해가 생긴다.

> ThreadLocal이 되니까 예전 습관을 그대로 유지해도 된다.

정답은 “일부는 된다, 하지만 더 신중해야 한다”다.

### Virtual Threads에서 `ThreadLocal`이 특히 조심스러운 이유

1. virtual thread 수가 훨씬 많아질 수 있다
2. task마다 짧게 생성되고 빠르게 사라질 수 있다
3. request context 외에 무거운 객체를 습관적으로 넣으면 총량이 커진다
4. thread pool reuse 가정에 기대던 코드가 의미를 잃을 수 있다

예를 들어 아래 정도는 대체로 자연스럽다.

- trace id
- auth principal
- locale
- 작은 request context

반면 아래는 더 신중해야 한다.

- 수 MB 단위의 대형 객체
- 캐시성 데이터
- 커넥션/세션/리소스 핸들
- 명시적 cleanup이 필요한 값

특히 팀에서 종종 보이는 안티패턴은 이것이다.

```java
private static final ThreadLocal<Map<String, Object>> CONTEXT =
        ThreadLocal.withInitial(HashMap::new);
```

그리고 여러 레이어에서 이 map에 이것저것 넣는다.

- 사용자 정보
- 실험군 정보
- 권한 목록
- 감사 로깅 데이터
- 임시 계산 결과

플랫폼 스레드 풀 환경에서는 그래도 “적은 수의 재사용 스레드”라는 제약이 있었지만, Virtual Threads에서는 request 단위 생성이 너무 쉬워지므로 이런 구조의 비용을 다시 보게 된다.

실무 기준은 이렇다.

- `ThreadLocal`은 **작고 명확한 컨텍스트**에만 쓴다
- 무거운 값은 명시적 파라미터나 별도 context 객체로 전달한다
- 라이브러리/프레임워크가 MDC, transaction context처럼 쓰는 건 자연스럽지만, 애플리케이션 레벨 남용은 줄인다
- 기존 코드가 “worker thread가 오래 살아남는다”는 가정을 하고 있지 않은지 검토한다

한마디로,
`ThreadLocal`이 동작한다는 사실과 `ThreadLocal`이 좋은 설계라는 사실은 다르다.

---

## 핵심 개념 5: CPU bound 작업은 Virtual Threads보다 여전히 작업량 통제가 먼저다

Oracle 문서에서도 강조하는 메시지가 있다. Virtual Threads는 **오래 기다리는 작업**, 특히 I/O bound 작업에 잘 맞는다. 반대로 긴 CPU 연산을 더 빨리 처리해 주는 도구는 아니다.

예를 들어 아래 작업들은 Virtual Threads의 주 타깃이 아니다.

- 대규모 JSON/Parquet 변환
- 암호화/압축/이미지 처리
- 복잡한 규칙 엔진 계산
- 대형 컬렉션 정렬/집계
- 머신러닝 추론을 CPU로 직접 돌리는 경우

이런 작업은 결국 CPU 코어 수가 상한을 만든다. 여기서 virtual thread를 수천 개 띄우면,
좋은 일이 생기는 게 아니라 runnable 경쟁만 커질 수 있다.

### 나쁜 예시

```java
try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
    for (Order order : orders) {
        executor.submit(() -> heavyPricingCalculation(order));
    }
}
```

겉보기에는 멋져 보이지만, 실제로는 아래 문제가 생길 수 있다.

- CPU saturation
- run queue 증가
- GC pressure 증가
- tail latency 증가
- 다른 요청 처리 지연

CPU bound 작업은 여전히 다음 기준이 맞다.

- 코어 수 기반 병렬성 제한
- bounded executor 또는 work-stealing pool 검토
- 큰 작업은 배치화
- 요청 경로와 분리
- 필요하면 캐시/사전 계산/벡터화/네이티브 라이브러리 검토

즉 Virtual Threads는 “모든 concurrency 도구의 상위호환”이 아니다.

### 간단한 판단 기준

- **대부분의 시간이 I/O 대기** → Virtual Threads 유리
- **대부분의 시간이 CPU 연산** → Virtual Threads 효과 제한적, 별도 병렬성 통제 필요
- **I/O와 CPU가 섞임** → 구간을 분리해서 각각 다른 정책 적용

실무에서 가장 안전한 패턴은 “요청 처리 스레드 모델”과 “고비용 계산 모델”을 구분하는 것이다.

---

## 핵심 개념 6: Virtual Threads를 도입해도 backpressure와 rate limit는 더 중요해진다

플랫폼 스레드 풀이 작을 때는 원하지 않아도 일정 수준의 보호 효과가 있었다.

- 풀 크기 200
- 큐 크기 1,000
- 그 이상은 거절

이 구조는 종종 서비스 품질을 떨어뜨리기도 했지만, 동시에 외부 시스템을 무한정 때리는 것을 막아 주기도 했다.

Virtual Threads는 이 완충장치를 약하게 만든다. 왜냐하면 작업 생성이 매우 쉬워지기 때문이다.

예를 들어 주문 목록 API가 요청 하나당 외부 가격 API를 50번 호출한다고 하자.

- 요청 1,000개 유입
- virtual thread 기반 fan-out 무제한
- 외부 API에 순간 50,000개 수준 호출 시도

이제 병목은 우리 서버 스레드가 아니라 **다운스트림 보호 정책**이 된다.

그래서 Virtual Threads 도입 시 아래 설계가 더 중요해진다.

### 1) 다운스트림별 동시성 제한

```java
public class PricingClient {
    private final Semaphore concurrentCalls = new Semaphore(100);

    public PriceResult fetchPrice(String productId) throws Exception {
        concurrentCalls.acquire();
        try {
            return httpClient.fetch(productId);
        } finally {
            concurrentCalls.release();
        }
    }
}
```

### 2) 타임아웃

- connection timeout
- read timeout
- 전체 request deadline
- retry budget

### 3) bulkhead 분리

- 가격 API 장애가 배송 API까지 전염되지 않게 분리
- 기능별 limit / circuit breaker / queue 구분

### 4) fail-fast 정책

- 다운스트림 포화 시 조용히 더 기다리지 않고 빠르게 실패
- 사용자 경험과 시스템 보호 사이의 균형 설계

Virtual Threads는 blocking 스타일을 다시 확장 가능하게 해 주지만,
그만큼 **업무 수준의 제어 장치**를 코드로 드러내야 한다.

---

## 핵심 개념 7: “도입됐다”보다 “관측 가능하다”가 더 중요하다

Virtual Threads는 동작 여부만 확인하면 안 된다. 실제 운영 효과를 보려면 관측 포인트가 필요하다.

특히 아래를 봐야 한다.

- throughput 증가 여부
- p95 / p99 latency 변화
- DB pool wait 증가 여부
- 외부 API saturation 여부
- pinning 발생 빈도
- carrier thread 사용 패턴
- timeout / reject / retry 변화

### JFR에서 꼭 볼 것

Oracle 문서 기준으로 JFR에는 virtual thread 관련 이벤트가 있다.

- `jdk.VirtualThreadPinned`
- `jdk.VirtualThreadSubmitFailed`
- 필요시 `jdk.VirtualThreadStart`, `jdk.VirtualThreadEnd`

특히 `jdk.VirtualThreadPinned`는 아주 중요하다.

이 이벤트가 반복적으로 보이면 다음을 의심할 수 있다.

- `synchronized` 안의 blocking I/O
- native/foreign call 장기 수행
- 라이브러리 내부 pinning hotspot

### Thread dump도 해석 방식이 달라진다

virtual thread가 많아지면 “스레드 수가 많다” 자체는 이상 신호가 아닐 수 있다. 대신 아래를 봐야 한다.

- 대부분이 어떤 자원을 기다리는가
- carrier thread 수와 CPU 사용률은 어떤가
- DB pool 대기가 많은가
- 특정 외부 API timeout이 누적되는가

즉 예전처럼 “스레드 3,000개니까 무조건 비정상”이라고 보면 오판할 수 있다.

### 운영 지표에서 함께 봐야 할 것

1. Tomcat/Jetty/Netty 또는 프레임워크 요청 지표
2. JDBC connection active / pending / timeout
3. downstream client별 concurrency / latency / error rate
4. semaphore wait time, queue depth, rejection count
5. CPU usage, load average, GC pause

Virtual Threads는 좋은 기술이지만, 실제 성과는 결국 **병목 이동을 얼마나 빨리 읽느냐**에 달려 있다.

---

## 실무 예시: 주문 집계 API를 Virtual Threads로 바꿀 때 어디까지가 이득이고, 어디부터가 새 병목인가

다음과 같은 API를 가정하자.

- 사용자 프로필 조회
- 최근 주문 조회
- 쿠폰 조회
- 추천 상품 조회
- 각 결과를 합쳐 대시보드 응답 생성

기존에는 `CompletableFuture` 체인과 별도 thread pool로 구현되어 있었다.

### 기존 방식의 문제

- 비동기 체인이 길어져 예외 전파가 복잡하다
- 디버깅 시 stack trace가 끊겨 보인다
- timeout, fallback, logging 문맥이 분산된다
- 단순한 read aggregation인데 코드가 과도하게 ceremony를 가진다

### Virtual Threads로 바꾼 1차 개선

```java
public DashboardResponse getDashboard(long userId) throws Exception {
    try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
        Future<UserProfile> profile = executor.submit(() -> profileClient.fetch(userId));
        Future<List<Order>> orders = executor.submit(() -> orderRepository.findRecentOrders(userId));
        Future<Coupons> coupons = executor.submit(() -> couponClient.fetch(userId));
        Future<Recommendations> recommendations = executor.submit(() -> recommendationClient.fetch(userId));

        return new DashboardResponse(
                profile.get(),
                orders.get(),
                coupons.get(),
                recommendations.get()
        );
    }
}
```

좋아진 점은 분명하다.

- 순차 코드처럼 읽힌다
- blocking API 그대로 활용 가능하다
- 작업 분리가 직관적이다
- 장애 분석 시 요청 단위 흐름이 더 잘 보인다

하지만 여기서 끝내면 절반만 한 것이다.

### 2차 점검: 진짜 병목 파악

이 API에서 실제 제약은 다음일 수 있다.

- 프로필 API: 동시 200까지만 안전
- 쿠폰 API: 레이트 리밋 엄격
- 추천 API: p99가 긴 편
- DB: connection pool 40

그렇다면 스레드 모델 변경만으로는 부족하다. 아래처럼 보호 장치를 넣어야 한다.

```java
public class DashboardFacade {
    private final Semaphore profileSlots = new Semaphore(200);
    private final Semaphore couponSlots = new Semaphore(80);
    private final Semaphore recommendationSlots = new Semaphore(50);

    public DashboardResponse getDashboard(long userId) throws Exception {
        try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
            Future<UserProfile> profile = executor.submit(() -> withPermit(profileSlots, () -> profileClient.fetch(userId)));
            Future<List<Order>> orders = executor.submit(() -> orderRepository.findRecentOrders(userId));
            Future<Coupons> coupons = executor.submit(() -> withPermit(couponSlots, () -> couponClient.fetch(userId)));
            Future<Recommendations> recommendations = executor.submit(() -> withPermit(recommendationSlots, () -> recommendationClient.fetch(userId)));

            return new DashboardResponse(
                    profile.get(),
                    orders.get(),
                    coupons.get(),
                    recommendations.get()
            );
        }
    }

    private <T> T withPermit(Semaphore semaphore, CheckedSupplier<T> supplier) throws Exception {
        semaphore.acquire();
        try {
            return supplier.get();
        } finally {
            semaphore.release();
        }
    }
}
```

이제 의미가 달라진다.

- 스레드는 요청 모델을 단순하게 유지한다
- 실제 희소 자원은 별도 정책으로 보호한다
- 서비스 전체 동작이 더 예측 가능해진다

### 여기서 추가로 봐야 할 것

- fan-out 요청 전체 deadline
- 부분 실패 허용 범위
- retry가 concurrency 폭증을 재귀적으로 만들지 않는지
- 추천 API처럼 느린 의존성은 fallback 가능한지

즉 Virtual Threads는 설계를 단순화할 수 있지만,
**아키텍처 판단 자체를 대신해 주지는 않는다.**

---

## JDBC와 ORM에서 특히 조심할 경계: “blocking 스타일이 쉬워졌다”와 “트랜잭션이 싸졌다”는 다르다

JDBC 호출은 Virtual Threads와 궁합이 좋을 수 있다. 기존 blocking JDBC 코드를 굳이 리액티브 드라이버로 전면 교체하지 않고도 높은 대기 동시성을 수용할 수 있기 때문이다.

하지만 이것도 한계가 명확하다.

### 그대로 좋아지는 점

- DB 응답 대기 중 플랫폼 스레드 낭비 감소
- thread-per-request / transaction-per-request 모델 유지 용이
- 기존 서비스 코드의 전환 비용 절감

### 그대로 위험한 점

- 긴 트랜잭션은 여전히 connection을 오래 점유한다
- 느린 쿼리는 여전히 전체 처리량을 무너뜨린다
- lock wait, deadlock, row contention은 스레드 모델과 별개다
- ORM의 N+1, flush 폭주, 잘못된 fetch plan은 그대로 남는다

특히 팀이 자주 빠지는 함정은 이것이다.

> Virtual Threads를 도입했으니 connection pool도 크게 안 중요해졌다.

오히려 반대다. 동시 요청을 더 많이 받아낼 수 있게 되면, **DB에 무리한 동시성 압력이 더 직접적으로 전달될 수 있다.**

그래서 Virtual Threads + JDBC 조합에서는 다음이 더 중요해진다.

- 짧은 트랜잭션 유지
- 느린 쿼리 제거
- connection timeout 엄격화
- pool pending 관측
- 읽기/쓰기 분리 전략 검토
- 무한 fan-out 쿼리 방지

한 줄로 말하면:

> Virtual Threads는 blocking JDBC를 덜 불편하게 만들 수는 있어도, 나쁜 DB 설계를 가려주지는 못한다.

---

## 프레임워크 적용 관점: “켜면 된다”보다 “어떤 라이브러리가 어떤 가정을 하는가”를 먼저 봐야 한다

실무 도입은 보통 프레임워크 위에서 일어난다. 여기서 중요한 질문은 “지원하느냐” 하나가 아니라 아래 네 가지다.

1. 요청 처리 경로가 blocking I/O 중심인가
2. 사용하는 라이브러리가 오래된 native blocking 또는 과도한 `synchronized` 구간을 갖고 있지 않은가
3. 기존 thread pool이 사실상 rate limit 역할을 하고 있지 않았는가
4. MDC, 트랜잭션 컨텍스트, 보안 컨텍스트가 스레드 모델 변경 후에도 의도대로 유지되는가

특히 Spring 계열 서비스에서는 다음을 같이 점검하는 편이 좋다.

- 웹 요청 스레드 모델
- `@Async` executor 설정
- 스케줄러 executor
- JDBC pool 크기
- HTTP client connection pool / max in-flight
- 로그 MDC 전파
- 보안/트랜잭션 컨텍스트 전달

이때 중요한 원칙이 하나 있다.

> 요청을 받는 스레드 모델과, 비동기 후처리/배치/CPU 작업용 executor 정책을 한 덩어리로 보지 말 것.

Virtual Threads는 보통 **요청-응답형 blocking I/O 경로**에서 가장 큰 이득을 준다. 반대로 배치, CPU 집약 처리, 대형 메시지 소비는 별도 executor 전략이 더 적합할 수 있다.

---

## 트레이드오프: 코드 단순성과 자원 통제 사이에서 무엇을 얻고 무엇을 잃나

Virtual Threads가 매력적인 이유는 분명하다.

### 얻는 것

- thread-per-request 스타일 유지
- 예외 처리, 디버깅, stack trace 가독성 향상
- blocking 라이브러리 재사용성 증가
- 높은 대기 동시성 확보
- 비동기 콜백 체인 감소

### 잃거나 새로 필요해지는 것

- thread pool이 제공하던 암묵적 backpressure 감소
- 다운스트림 보호를 명시적으로 설계해야 함
- pinning hotspot 점검 필요
- `ThreadLocal`/context 사용량 재검토 필요
- 스레드 수 대신 다른 병목 지표를 더 많이 봐야 함

특히 조직 차원에서의 트레이드오프도 있다.

- **개발 생산성**은 좋아질 수 있다
- 하지만 **운영 설계 미숙**은 더 빨리 드러난다
- 그래서 “개발팀이 쓰기 쉬운 기술”인 동시에 “SRE/플랫폼팀이 제어 포인트를 다시 설계해야 하는 기술”이기도 하다

---

## 흔한 실수 1: Virtual Threads를 도입하면서 기존 bounded pool을 없애고, 보호 장치도 함께 없애 버린다

이건 가장 자주 나오는 실수다.

이전 구조:

- 요청 처리 스레드 200
- 외부 API 호출 executor 100
- 큐 제한 있음

변경 후:

- 요청당 virtual thread 자유 생성
- 외부 API 호출도 무제한 submit
- 세마포어, rate limiter, circuit breaker 없음

결과는 명확하다.

- 우리 서버는 예전보다 덜 막힌다
- 대신 외부 API와 DB가 더 빨리 무너진다
- 장애 파급 반경이 커진다

Virtual Threads 도입은 보호 장치 제거가 아니라 **보호 장치 위치 이동**이다.

---

## 흔한 실수 2: `synchronized` 안에서 HTTP/JDBC 호출을 하고도 확장성이 안 나온 이유를 모른다

이 문제는 평소에는 숨어 있다가 Virtual Threads 도입 후 지표에서 더 눈에 띄게 나온다.

다시 강조하지만 pinning은 “잘못된 문법”이 아니다. 하지만 아래 조합은 특히 위험하다.

- 큰 임계구역
- 높은 호출 빈도
- 느린 blocking I/O
- 가끔 발생하는 tail latency

이 네 가지가 겹치면 carrier thread가 자주 묶이고, virtual thread의 이점이 상당 부분 사라질 수 있다.

점검 순서는 보통 이렇다.

1. JFR에서 pinned 이벤트 확인
2. 해당 코드 경로의 lock 구간 확인
3. lock 내부 I/O 여부 확인
4. 임계구역 축소 또는 다른 동기화 방식 검토

---

## 흔한 실수 3: Virtual Threads면 CPU 작업도 무한 병렬화해도 된다고 믿는다

이건 concurrency와 parallelism을 혼동한 전형적인 케이스다.

- concurrency: 동시에 진행 중인 작업 수
- parallelism: 동시에 CPU에서 실제 계산되는 작업 수

Virtual Threads는 전자를 쉽게 늘린다. 하지만 후자는 코어 수를 뛰어넘지 못한다.

그래서 CPU heavy 작업에서는 다음을 먼저 고민해야 한다.

- 정말 병렬화가 필요한가
- 작업 크기를 쪼개는 게 이득인가
- 캐시 또는 사전 계산으로 줄일 수 있는가
- 별도 배치/워크큐로 보내는 게 낫지 않은가

---

## 흔한 실수 4: `ThreadLocal`을 request context가 아니라 만능 저장소로 사용한다

Virtual Threads가 `ThreadLocal`을 지원한다는 사실은 호환성 측면에서 큰 장점이다. 하지만 애플리케이션 설계 측면에서는 여전히 절제가 필요하다.

특히 아래는 냄새다.

- 메서드 파라미터로 넘기기 귀찮아서 다 `ThreadLocal`에 넣음
- cleanup 시점이 모호함
- 로깅용 context와 비즈니스 상태가 뒤섞임
- 테스트에서 값이 새지 않는다고 안심하지만 실제 구조는 점점 불투명해짐

Virtual Threads 시대에도 좋은 기준은 같다.

- 명시적으로 전달할 수 있는 것은 명시적으로 전달
- 진짜 cross-cutting context만 `ThreadLocal` 사용
- 값은 작고 수명은 짧게 유지

---

## 흔한 실수 5: “스레드가 싸다”를 “리소스가 싸다”로 오해한다

스레드가 싸졌다고 해서 아래가 싸진 것은 아니다.

- DB connection
- 소켓
- 외부 API quota
- 파일 핸들
- 메모리
- 락
- 캐시 공간

이 오해는 부하 테스트에서 자주 드러난다.

- 스레드 덤프는 멀쩡해 보인다
- 그런데 DB pending이 치솟는다
- 외부 API 429가 증가한다
- p99 latency가 악화된다

즉 “스레드 한계가 사라졌다”는 말은 “이제 다른 한계가 훨씬 선명하게 보인다”는 말에 가깝다.

---

## 흔한 실수 6: 효과 검증 없이 일부 벤치마크만 보고 전면 전환한다

Virtual Threads는 워낙 매력적인 기술이라 작은 PoC 결과만 보고 전면 도입 유혹이 크다. 하지만 안전한 순서는 보통 아래다.

1. I/O 대기 비중이 높은 경로를 찾는다
2. 그 경로만 제한적으로 전환한다
3. throughput, latency, DB pending, downstream error를 비교한다
4. pinning, timeout, backpressure 문제를 보완한다
5. 그다음 적용 범위를 넓힌다

특히 이 기술은 “지원된다”와 “우리 서비스에 맞다” 사이의 간격이 작지 않다.

---

## 실무 체크리스트: Virtual Threads 도입 전에 꼭 보는 항목

### 1) 워크로드 성격 점검

- 이 경로는 I/O 대기 비중이 높은가
- CPU intensive 구간이 길지 않은가
- 대기 시간이 주로 DB, HTTP, 파일, MQ 어디서 발생하는가

### 2) 희소 자원 점검

- DB connection pool 크기와 pending 지표가 있는가
- 외부 API별 동시성 제한이 있는가
- HTTP client connection pool과 timeout이 적절한가
- retry가 concurrency를 증폭시키지 않는가

### 3) pinning 점검

- `synchronized` 안에 느린 I/O가 있는가
- native/foreign call 비중이 높은 라이브러리가 있는가
- JFR `jdk.VirtualThreadPinned`를 볼 수 있는가

### 4) 컨텍스트 점검

- MDC, 보안 컨텍스트, 트랜잭션 컨텍스트가 의도대로 전달되는가
- `ThreadLocal`에 무거운 값을 넣고 있지 않은가
- 애플리케이션 코드가 worker thread 재사용을 암묵적으로 가정하지 않는가

### 5) backpressure 점검

- 기존 thread pool이 사실상 보호 장치 역할을 하고 있지 않았는가
- 세마포어, rate limiter, bulkhead, circuit breaker가 필요한 경로는 어디인가
- 무제한 fan-out이 가능한 코드가 숨어 있지 않은가

### 6) 관측 가능성 점검

- p50/p95/p99 latency 비교가 가능한가
- throughput과 에러율 비교가 가능한가
- DB pending, timeout, pool exhaustion을 보는가
- JFR / thread dump / 애플리케이션 지표를 함께 해석할 준비가 되어 있는가

### 7) rollout 전략 점검

- 한 번에 전면 전환하지 않는가
- 고가치 I/O 경로부터 단계적으로 적용하는가
- 문제 시 쉽게 되돌릴 수 있는가

---

## 한 번 더 요약: Virtual Threads가 특히 잘 맞는 경우와 덜 맞는 경우

### 잘 맞는 경우

- 요청당 blocking I/O가 많다
- 코드 복잡도를 줄이고 싶다
- 비동기 체인이 과도하게 복잡하다
- thread-per-request 모델을 유지하고 싶다
- 기존 라이브러리를 blocking 스타일로 재사용하고 싶다

### 덜 맞는 경우

- 긴 CPU 계산이 대부분이다
- 다운스트림 보호 정책이 전혀 없다
- `synchronized` 안의 느린 I/O가 많다
- DB/외부 API 병목이 이미 심각하다
- 관측 도구 없이 “좋아질 것 같아서” 도입하려 한다

---

## 코드 리뷰에서 바로 걸러야 하는 냄새들

### 냄새 1

“Virtual Threads로 바꿨으니 fixed thread pool 제한은 다 지웁시다.”

→ 제한을 지우기 전에, 그 제한이 보호하던 자원이 무엇이었는지 먼저 식별해야 한다.

### 냄새 2

“DB 대기 많아도 괜찮아요. 스레드는 충분하니까요.”

→ 스레드 여유와 DB 여유는 별개다. connection pending이 쌓이면 latency는 그대로 망가진다.

### 냄새 3

“성능 안 나와서 `synchronized`를 전부 `volatile`로 바꾸겠습니다.”

→ pinning 문제를 메모리 모델 문제와 혼동하면 더 큰 정합성 버그를 만든다.

### 냄새 4

“메서드 파라미터가 많으니 그냥 `ThreadLocal`에 넣죠.”

→ 일시적 편의가 장기적 불투명성을 만든다.

### 냄새 5

“CPU 작업도 task마다 virtual thread로 뿌리면 확장되겠죠?”

→ 그것은 확장이 아니라 과도한 경쟁일 가능성이 높다.

---

## 마무리: Virtual Threads를 잘 쓴다는 것은 “스레드 비용”이 아니라 “병목의 정체”를 더 정확히 구분하는 일이다

Virtual Threads의 진짜 가치는 단순하다.

- blocking 코드를 덜 죄책감 있게 유지할 수 있다
- 높은 동시성을 더 자연스럽게 다룰 수 있다
- 비동기 체인의 복잡도를 줄일 수 있다
- 요청 단위 사고 모델을 되찾을 수 있다

하지만 실무 기준으로 더 중요한 메시지는 따로 있다.

> 스레드가 가벼워질수록, 스레드가 아닌 병목은 더 선명해진다.

그래서 성숙한 도입은 보통 이런 모습에 가깝다.

- Virtual Threads로 요청 모델을 단순하게 만든다
- DB, 외부 API, CPU, 락, 메모리 같은 실제 희소 자원을 별도로 통제한다
- pinning과 timeout을 관측한다
- 단계적으로 rollout하고 지표로 검증한다

이 순서를 지키면 Virtual Threads는 “새로운 유행 기능”이 아니라,
**Java 서버 애플리케이션을 다시 단순하게 만들면서도 확장 가능하게 유지하는 현실적인 도구**가 된다.

## 한 줄 정리

Virtual Threads는 blocking 코드를 빠르게 만드는 기술이 아니라, **I/O 대기 중심 서비스에서 thread-per-request 모델을 다시 확장 가능하게 만들되, 진짜 병목인 DB·다운스트림·락·CPU를 더 명시적으로 통제하게 만드는 기술**이다.
