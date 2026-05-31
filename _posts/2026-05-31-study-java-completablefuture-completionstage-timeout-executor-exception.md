---
layout: post
title: "Java CompletableFuture 실전: CompletionStage, Executor, Timeout, 예외 전파로 비동기 조합을 운영 가능하게 만드는 법"
date: 2026-05-31 11:50:00 +0900
categories: [java]
tags: [study, java, completablefuture, completionstage, async, executor, timeout, exception-handling, concurrency, backend, performance]
permalink: /java/2026/05/31/study-java-completablefuture-completionstage-timeout-executor-exception.html
---

## 배경: `CompletableFuture`는 쉬워 보이지만 운영에서는 자주 위험해진다

Java 백엔드에서 비동기 처리를 도입할 때 가장 먼저 손이 가는 도구 중 하나가 `CompletableFuture`다.

문법만 보면 꽤 단순하다.

```java
CompletableFuture<User> userFuture = CompletableFuture.supplyAsync(() -> userClient.getUser(userId));
CompletableFuture<List<Order>> ordersFuture = CompletableFuture.supplyAsync(() -> orderClient.getOrders(userId));

User user = userFuture.join();
List<Order> orders = ordersFuture.join();
```

두 API를 동시에 호출하고, 나중에 결과를 합치면 된다. 처음에는 이것만으로도 충분해 보인다.

하지만 운영 서비스에서는 곧바로 다음 문제가 튀어나온다.

- 어디선가 `join()`을 너무 일찍 호출해 병렬 호출이 사실상 순차 호출로 바뀐다
- 기본 `ForkJoinPool.commonPool()`에 blocking I/O를 태워 다른 비동기 작업까지 느려진다
- timeout을 걸었다고 믿었는데 실제 외부 요청은 계속 살아 있어 connection pool을 붙잡는다
- `exceptionally()`로 예외를 삼켜 장애가 정상 응답처럼 보인다
- `allOf()`를 썼지만 어떤 요청이 실패했는지, 어떤 요청은 성공했는지 추적하기 어렵다
- MDC, trace id, 보안 컨텍스트가 비동기 경계에서 사라져 로그가 끊긴다
- 취소(`cancel`)를 호출했지만 실제 작업은 중단되지 않아 백그라운드 부하가 계속된다
- 스레드 풀을 크게 늘렸더니 처리량은 조금 오르고 tail latency와 장애 반경은 더 커진다

`CompletableFuture`의 위험은 “비동기가 어렵다”는 추상적인 말로 끝나지 않는다. 더 정확히 말하면, `CompletableFuture`는 **작업의 실행 위치, 조합 순서, 예외 의미, timeout 경계, 자원 제한을 코드에 명확히 적지 않으면 운영에서 의도가 사라지는 API**다.

이 글은 중급 이상 Java 개발자를 기준으로 `CompletableFuture`를 단순 문법이 아니라 운영 설계 도구로 다룬다.

목표는 다음 질문에 답하는 것이다.

1. `CompletableFuture`와 `CompletionStage`를 어떻게 구분해서 읽어야 하는가
2. `thenApply`, `thenCompose`, `thenCombine`, `allOf`는 각각 어떤 조합 의미를 가지는가
3. `Async` 접미사가 붙은 메서드는 정확히 어디에서 실행되는가
4. 기본 executor를 그대로 쓰면 왜 위험한가
5. timeout, cancel, interrupt는 서로 어떻게 다르고 어디까지 믿을 수 있는가
6. 예외를 복구할지, 전파할지, 부분 성공으로 바꿀지 어떤 기준으로 결정해야 하는가
7. 실무 코드에서 비동기 조합을 테스트 가능하고 관측 가능하게 만들려면 어떤 구조가 필요한가

이 글의 결론을 먼저 말하면 이렇다.

> `CompletableFuture`의 핵심은 “비동기로 빠르게 만들기”가 아니라, **독립적인 대기 작업을 명시적으로 조합하되 executor·timeout·예외·관측성의 경계를 코드에 드러내는 것**이다.

---

## 먼저 큰 그림: `CompletableFuture`는 결과 컨테이너이면서 조합 그래프다

`CompletableFuture`를 처음 배울 때는 보통 “미래에 완료될 값”이라고 설명한다. 맞는 설명이지만 실무에서는 절반만 맞다.

`CompletableFuture`는 두 가지 성격을 동시에 가진다.

1. 아직 완료되지 않았을 수도 있는 **결과 컨테이너**
2. 완료 이후 실행될 후속 작업을 연결하는 **비동기 조합 그래프**

```java
CompletableFuture<UserProfile> profileFuture = userClient.findUser(userId)
        .thenCompose(user -> gradeClient.findGrade(user.gradeId())
                .thenApply(grade -> UserProfile.of(user, grade)))
        .exceptionally(ex -> UserProfile.anonymous(userId));
```

이 코드는 단순히 `UserProfile` 하나를 기다리는 코드가 아니다. 실제로는 다음 그래프를 만든다.

1. 사용자 조회가 끝난다
2. 사용자 결과를 이용해 등급 조회를 시작한다
3. 등급 조회가 끝나면 사용자와 등급을 합친다
4. 중간에 예외가 나면 익명 프로필로 복구한다

따라서 `CompletableFuture` 코드를 읽을 때 중요한 질문은 “어디서 값을 꺼내는가?”가 아니라 다음이다.

- 어떤 작업들이 서로 독립적인가
- 어떤 작업은 앞선 결과가 있어야만 시작되는가
- 어떤 작업은 같은 executor에서 실행되는가
- 어떤 경계에서 timeout이 적용되는가
- 어떤 예외는 복구되고 어떤 예외는 호출자에게 전파되는가
- 최종 `join()` 또는 `get()`은 어느 계층에서 한 번만 호출되는가

실무에서 성능과 안정성을 가르는 지점은 대부분 이 질문들에 있다.

---

## 핵심 개념 1: `CompletableFuture`와 `CompletionStage`를 구분해서 설계하라

`CompletableFuture`는 `Future`이면서 `CompletionStage`다. 이 말은 API 설계 관점에서 꽤 중요하다.

- `CompletableFuture`는 외부에서 완료시킬 수 있다: `complete`, `completeExceptionally`
- `CompletionStage`는 완료 이후의 조합 계약에 가깝다: `thenApply`, `thenCompose`, `handle`

서비스 메서드의 반환 타입을 습관적으로 `CompletableFuture<T>`로 열어두면, 호출자가 해당 future를 임의로 완료하거나 취소할 수 있는 여지가 생긴다.

```java
// 구현 세부사항까지 열어 둔 API
public CompletableFuture<PriceResult> calculatePrice(String productId) {
    return CompletableFuture.supplyAsync(() -> priceClient.fetch(productId), executor);
}
```

대부분의 경우 외부 호출자는 결과를 조합하면 충분하다. 완료 권한까지 줄 필요는 없다.

```java
// 조합 계약만 노출
public CompletionStage<PriceResult> calculatePrice(String productId) {
    return CompletableFuture.supplyAsync(() -> priceClient.fetch(productId), priceExecutor);
}
```

물론 내부 구현에서는 여전히 `CompletableFuture`가 필요할 수 있다. 예를 들어 callback 기반 API를 future로 감쌀 때는 직접 완료해야 한다.

```java
public CompletionStage<PaymentResult> requestPayment(PaymentCommand command) {
    CompletableFuture<PaymentResult> future = new CompletableFuture<>();

    paymentSdk.request(command, new PaymentCallback() {
        @Override
        public void onSuccess(PaymentResult result) {
            future.complete(result);
        }

        @Override
        public void onFailure(Throwable error) {
            future.completeExceptionally(error);
        }
    });

    return future;
}
```

여기서 기준은 단순하다.

- **내부에서 완료를 제어해야 한다면** `CompletableFuture`
- **외부에는 조합 가능한 비동기 결과만 보여주면 된다면** `CompletionStage`
- **동기 계층으로 넘어가는 마지막 경계에서만** `toCompletableFuture().join()` 또는 `get()`

이렇게 구분하면 API의 권한이 줄고, 테스트와 리팩터링도 쉬워진다.

---

## 핵심 개념 2: `thenApply`, `thenCompose`, `thenCombine`은 서로 다른 의도를 가진다

`CompletableFuture` 코드가 지저분해지는 가장 흔한 이유는 모든 조합을 `thenApply`로 처리하려 하기 때문이다. 세 메서드의 의미를 구분해야 한다.

### `thenApply`: 값 하나를 동기적으로 변환한다

`thenApply`는 앞 단계 결과를 받아 즉시 계산 가능한 값으로 바꾼다.

```java
CompletionStage<UserDto> dtoStage = userStage
        .thenApply(user -> new UserDto(user.id(), user.name(), user.email()));
```

여기서 mapper는 외부 I/O를 하지 않고, CPU 계산도 가볍고, 예외 의미도 단순해야 한다.

잘못된 예는 다음과 같다.

```java
CompletionStage<UserDetail> detailStage = userStage
        .thenApply(user -> orderClient.findRecentOrders(user.id())) // blocking I/O
        .thenApply(orders -> buildDetail(orders));
```

`thenApply` 안에서 blocking I/O를 호출하면, 이전 stage를 완료한 스레드가 그대로 외부 호출을 떠안는다. 이 스레드가 이벤트 루프, scheduler, 공용 풀 워커, web request thread일 수 있다면 운영 리스크가 커진다.

I/O가 필요하면 실행 위치를 명시해야 한다.

```java
CompletionStage<List<Order>> ordersStage = userStage
        .thenCompose(user -> orderService.findRecentOrdersAsync(user.id()));
```

### `thenCompose`: 다음 비동기 작업으로 평탄화한다

`thenCompose`는 `Future<Future<T>>` 형태로 중첩될 작업을 평탄화한다.

```java
CompletionStage<UserGrade> gradeStage = userService.findUser(userId)
        .thenCompose(user -> gradeService.findGrade(user.gradeId()));
```

`thenApply`로 같은 코드를 쓰면 타입이 이상해진다.

```java
CompletionStage<CompletionStage<UserGrade>> nested = userService.findUser(userId)
        .thenApply(user -> gradeService.findGrade(user.gradeId()));
```

중첩 future는 거의 항상 신호다. “앞 단계 결과로 다음 비동기 작업을 시작한다”면 `thenCompose`가 맞다.

### `thenCombine`: 독립 작업 두 개를 합친다

서로 의존하지 않는 두 작업은 먼저 동시에 시작하고 나중에 합쳐야 한다.

```java
CompletionStage<User> userStage = userService.findUser(userId);
CompletionStage<List<Order>> ordersStage = orderService.findRecentOrders(userId);

CompletionStage<UserDashboard> dashboardStage = userStage.thenCombine(
        ordersStage,
        (user, orders) -> new UserDashboard(user, orders)
);
```

중요한 점은 두 future를 **조합 전에 이미 시작**했다는 것이다.

나쁜 패턴은 다음과 같다.

```java
CompletionStage<UserDashboard> dashboardStage = userService.findUser(userId)
        .thenCompose(user -> orderService.findRecentOrders(user.id())
                .thenApply(orders -> new UserDashboard(user, orders)));
```

주문 조회가 사용자 조회 결과에 반드시 의존한다면 괜찮다. 하지만 `userId`만 있으면 주문을 조회할 수 있다면 이 코드는 불필요하게 순차화되어 있다.

### 실무 기준

- 값 변환: `thenApply`
- 앞 결과로 다음 비동기 호출 시작: `thenCompose`
- 독립적인 두 결과 결합: `thenCombine`
- 여러 독립 작업을 모두 기다림: `allOf`
- 가장 먼저 성공/완료한 결과 선택: `applyToEither`, `anyOf`

이 구분만 명확해도 `CompletableFuture` 코드의 절반은 정리된다.

---

## 핵심 개념 3: `Async` 접미사는 “비동기”가 아니라 “실행 위치 변경”으로 읽어야 한다

`thenApply`와 `thenApplyAsync`의 차이를 단순히 동기/비동기로 이해하면 위험하다.

```java
stage.thenApply(this::convert);
stage.thenApplyAsync(this::convert);
stage.thenApplyAsync(this::convert, customExecutor);
```

차이는 다음에 가깝다.

- `thenApply`: 이전 stage를 완료한 스레드에서 후속 작업이 실행될 수 있다
- `thenApplyAsync`: 기본 executor에서 후속 작업을 실행한다
- `thenApplyAsync(..., executor)`: 지정한 executor에서 후속 작업을 실행한다

즉 `Async`는 “마법처럼 안전한 비동기”가 아니라 **후속 작업을 어떤 executor에 예약할 것인가**의 문제다.

예를 들어 HTTP 요청 스레드에서 이미 완료된 future에 `thenApply`를 붙이면 후속 변환이 현재 요청 스레드에서 바로 실행될 수 있다.

```java
CompletionStage<Result> result = alreadyCompletedStage
        .thenApply(this::expensiveConvert); // 현재 스레드에서 실행될 수 있음
```

변환 비용이 크거나 blocking 가능성이 있다면 executor를 분리한다.

```java
CompletionStage<Result> result = alreadyCompletedStage
        .thenApplyAsync(this::expensiveConvert, cpuBoundExecutor);
```

다만 무조건 `Async`를 붙이는 것도 답이 아니다. stage마다 executor scheduling이 늘어나면 context switch와 queueing 비용이 생긴다. 아주 가벼운 DTO 변환까지 매번 다른 executor로 넘기면 오히려 지연 시간이 늘어날 수 있다.

실무 기준은 이렇다.

- 가벼운 순수 변환: 일반 `thenApply`
- blocking I/O 호출: 해당 I/O 전용 executor 또는 이미 비동기 API 사용
- 무거운 CPU 계산: CPU bound executor
- 컨텍스트 전파가 필요한 작업: executor 래핑 또는 task decorator 적용
- 실행 위치가 중요하지 않은 코드는 없다. 중요하지 않다고 느끼는 순간 기본값이 운영 정책이 된다.

---

## 핵심 개념 4: 기본 `ForkJoinPool.commonPool()`에 blocking I/O를 맡기지 마라

`CompletableFuture.supplyAsync()`에 executor를 넘기지 않으면 기본적으로 `ForkJoinPool.commonPool()`이 사용된다.

```java
CompletableFuture<Product> productFuture = CompletableFuture.supplyAsync(() -> productClient.get(productId));
```

데모 코드에서는 편하다. 운영 코드에서는 매우 조심해야 한다.

`commonPool`은 애플리케이션 전체에서 공유된다. 라이브러리, 다른 비동기 작업, 병렬 스트림 등이 같은 풀을 사용할 수 있다. 여기에 느린 HTTP 호출, DB 호출, 파일 I/O 같은 blocking 작업을 넣으면 공용 워커가 대기 상태로 묶인다.

문제는 단일 요청 하나가 아니라 장애 전파다.

1. 외부 상품 API가 느려진다
2. `commonPool` 워커들이 상품 API 응답 대기에 묶인다
3. 같은 풀을 쓰는 다른 기능의 비동기 작업도 지연된다
4. unrelated 기능까지 느려진다
5. 원인은 상품 API인데 장애 반경은 애플리케이션 전체로 커진다

따라서 실무에서는 목적별 executor를 명시하는 편이 안전하다.

```java
@Configuration
public class AsyncExecutorConfig {

    @Bean(destroyMethod = "shutdown")
    public ExecutorService productClientExecutor() {
        return new ThreadPoolExecutor(
                20,
                80,
                60, TimeUnit.SECONDS,
                new ArrayBlockingQueue<>(500),
                new NamedThreadFactory("product-client-"),
                new ThreadPoolExecutor.CallerRunsPolicy()
        );
    }
}
```

```java
public CompletionStage<Product> findProduct(String productId) {
    return CompletableFuture.supplyAsync(
            () -> productClient.get(productId),
            productClientExecutor
    );
}
```

여기서 중요한 것은 숫자 자체가 아니다. 중요한 건 **외부 의존성별로 queue, pool, timeout, rejection 정책을 관측하고 조정할 수 있는 경계**를 만드는 것이다.

### executor를 나누는 기준

무작정 executor를 많이 만드는 것도 좋지 않다. 운영 기준은 다음과 같다.

- 지연 특성이 다른 외부 의존성은 분리한다
- 장애 반경을 나눠야 하는 호출은 분리한다
- CPU bound와 I/O bound는 분리한다
- 호출량이 적고 중요도가 낮은 작업은 별도 작은 풀 또는 bulkhead로 제한한다
- 같은 다운스트림을 치는 작업은 같은 제한 정책 아래 묶는다

예를 들어 결제, 재고, 추천 API가 모두 외부 HTTP라고 해서 같은 executor를 쓰면 안 된다. 결제 API 장애가 추천 API 호출까지 막아서는 곤란하다. 반대로 너무 잘게 쪼개면 thread 수와 운영 복잡도가 커진다.

### queue는 성능 버퍼가 아니라 지연을 숨기는 장치다

ThreadPoolExecutor에서 queue를 크게 잡으면 순간적인 요청을 흡수할 수 있다. 하지만 queue가 커질수록 실패는 늦게 드러난다.

외부 API가 이미 느린데 queue에 작업을 계속 쌓으면 사용자는 timeout 직전까지 기다리고, 서버는 이미 의미 없는 작업을 계속 처리한다.

따라서 queue 크기는 “많을수록 좋다”가 아니다.

- 짧은 스파이크 흡수는 필요하다
- 다운스트림 장애를 무한 대기열로 숨기면 안 된다
- queue size, active thread count, rejection count를 metric으로 봐야 한다
- rejection은 무조건 나쁜 것이 아니라 overload를 빨리 드러내는 안전장치일 수 있다

---

## 핵심 개념 5: timeout은 future 완료 시간과 실제 작업 중단을 분리해서 이해해야 한다

Java 9 이후 `CompletableFuture`에는 `orTimeout`, `completeOnTimeout`이 있다.

```java
CompletionStage<Product> productStage = CompletableFuture
        .supplyAsync(() -> productClient.get(productId), productClientExecutor)
        .orTimeout(300, TimeUnit.MILLISECONDS);
```

이 코드는 300ms 안에 완료되지 않으면 future를 timeout 예외로 완료한다. 하지만 여기서 반드시 짚어야 할 점이 있다.

> future가 timeout으로 완료되었다고 해서, 이미 실행 중인 blocking HTTP 호출이 반드시 중단되는 것은 아니다.

즉 timeout에는 두 층이 있다.

1. 호출자 관점의 대기 timeout
2. 실제 I/O 클라이언트 관점의 connect/read/write timeout

`orTimeout`은 1번에 가깝다. 외부 API 호출 자체를 멈추려면 HTTP client, DB driver, SDK의 timeout도 별도로 설정해야 한다.

```java
HttpClient client = HttpClient.newBuilder()
        .connectTimeout(Duration.ofMillis(100))
        .build();

HttpRequest request = HttpRequest.newBuilder(uri)
        .timeout(Duration.ofMillis(250))
        .GET()
        .build();
```

그리고 future 레벨에서도 전체 예산을 둔다.

```java
CompletionStage<Product> productStage = CompletableFuture
        .supplyAsync(() -> productClient.get(productId), productClientExecutor)
        .orTimeout(300, TimeUnit.MILLISECONDS);
```

이중 timeout이 불필요해 보일 수 있지만, 운영에서는 역할이 다르다.

- client timeout: 실제 네트워크 작업과 자원 점유를 제한한다
- future timeout: 상위 조합 그래프가 무한정 기다리지 않게 한다
- request budget: 사용자 요청 전체의 남은 시간을 기준으로 하위 호출 시간을 배분한다

### `completeOnTimeout`은 fallback이지 성공이 아니다

`completeOnTimeout`은 timeout이 발생하면 기본값으로 완료한다.

```java
CompletionStage<Recommendation> recommendationStage = CompletableFuture
        .supplyAsync(() -> recommendationClient.get(userId), recommendationExecutor)
        .completeOnTimeout(Recommendation.empty(), 150, TimeUnit.MILLISECONDS);
```

추천 영역처럼 부가 기능이라면 괜찮다. 하지만 결제 승인, 재고 차감, 권한 검증 같은 핵심 기능에서 기본값으로 성공 처리하면 심각한 정합성 문제가 생긴다.

따라서 fallback을 넣을 때는 반드시 질문해야 한다.

- 이 값은 사용자가 보아도 안전한 degraded result인가
- 비즈니스적으로 “없음”과 “조회 실패”를 구분해야 하지 않는가
- fallback 응답을 metric으로 따로 집계하고 있는가
- fallback이 계속 발생해도 알림이 울리는가

실무에서는 fallback을 결과 타입에 드러내는 편이 안전하다.

```java
sealed interface RecommendationResult permits RecommendationResult.Success, RecommendationResult.Degraded {
    record Success(Recommendation value) implements RecommendationResult {}
    record Degraded(String reason) implements RecommendationResult {}
}
```

이렇게 하면 timeout을 정상 추천 결과와 섞어버리지 않는다.

---

## 핵심 개념 6: 예외 처리 메서드는 복구·관찰·변환의 의미가 다르다

`CompletableFuture`의 예외 처리는 처음 보면 헷갈린다.

- `exceptionally`
- `exceptionallyCompose`
- `handle`
- `whenComplete`

이 메서드들은 비슷해 보이지만 의도가 다르다.

### `exceptionally`: 예외를 값으로 복구한다

```java
CompletionStage<UserProfile> profileStage = userService.findProfile(userId)
        .exceptionally(ex -> UserProfile.guest(userId));
```

이 코드는 실패를 성공 값으로 바꾼다. 이후 stage는 정상 완료로 본다. 따라서 무분별하게 쓰면 장애가 사라진 것처럼 보인다.

사용 기준은 명확해야 한다.

- 정말 fallback 값으로 계속 진행해도 되는가
- fallback 발생을 metric/log로 남겼는가
- 호출자가 실패와 fallback을 구분해야 하는가

### `handle`: 성공과 실패를 모두 값으로 변환한다

```java
CompletionStage<SectionResult<OrderSummary>> orderSection = orderService.findSummary(userId)
        .handle((value, ex) -> {
            if (ex != null) {
                return SectionResult.failed("orders", unwrap(ex));
            }
            return SectionResult.success("orders", value);
        });
```

`handle`은 부분 성공 응답을 만들 때 유용하다. 예를 들어 마이페이지에서 주문 요약, 쿠폰, 추천, 공지 중 추천만 실패해도 전체 페이지를 실패시킬 필요가 없을 수 있다.

다만 `handle` 역시 예외를 값으로 바꾼다. 이후에는 정상 흐름이 된다. 그러므로 실패를 값으로 바꾼 사실이 타입과 metric에 드러나야 한다.

### `whenComplete`: 관찰하되 결과 의미는 바꾸지 않는다

```java
CompletionStage<Product> productStage = productService.findProduct(productId)
        .whenComplete((value, ex) -> {
            if (ex != null) {
                metrics.counter("product.lookup.failed").increment();
                log.warn("product lookup failed. productId={}", productId, ex);
            }
        });
```

`whenComplete`는 결과를 바꾸기 위한 메서드가 아니라 side effect 관찰에 가깝다. 성공은 성공대로, 실패는 실패대로 이어진다.

장애를 숨기지 않고 로그나 metric만 남기고 싶다면 `whenComplete`가 맞다.

### `exceptionallyCompose`: 실패 후 비동기 fallback을 호출한다

동기 fallback 값이 아니라 다른 비동기 경로로 복구해야 할 때가 있다.

```java
CompletionStage<Price> priceStage = primaryPriceClient.getPrice(productId)
        .exceptionallyCompose(ex -> secondaryPriceClient.getPrice(productId));
```

이때도 fallback이 무조건 좋은 것은 아니다. primary 장애 시 secondary로 요청이 몰리면서 2차 장애가 날 수 있다. fallback 호출에도 별도 timeout, rate limit, circuit breaker가 필요하다.

### 예외 래핑을 풀어야 로그가 읽힌다

`join()`은 실패 시 `CompletionException`으로 감싸고, `get()`은 `ExecutionException`으로 감싼다.

```java
try {
    return stage.toCompletableFuture().join();
} catch (CompletionException ex) {
    throw mapToApiException(unwrapCompletionException(ex));
}
```

운영 로그에 `CompletionException`만 잔뜩 보이면 원인 파악이 느려진다. root cause를 풀어내는 유틸리티를 두는 편이 좋다.

```java
static Throwable unwrap(Throwable throwable) {
    Throwable current = throwable;
    while (current instanceof CompletionException || current instanceof ExecutionException) {
        if (current.getCause() == null) {
            return current;
        }
        current = current.getCause();
    }
    return current;
}
```

---

## 핵심 개념 7: `allOf()`는 타입 정보를 잃기 때문에 결과 수집 구조를 따로 설계해야 한다

여러 future를 동시에 기다릴 때 `CompletableFuture.allOf()`를 자주 쓴다.

```java
CompletableFuture<Void> all = CompletableFuture.allOf(
        userFuture,
        orderFuture,
        couponFuture
);

all.join();
```

문제는 `allOf()`의 결과 타입이 `CompletableFuture<Void>`라는 점이다. 개별 결과는 직접 꺼내야 한다.

```java
User user = userFuture.join();
List<Order> orders = orderFuture.join();
Coupon coupon = couponFuture.join();
```

이 패턴 자체가 나쁜 것은 아니다. 하지만 실패 처리가 모호해지기 쉽다. `allOf()`는 구성 future 중 하나라도 실패하면 실패한다. 이때 어떤 stage가 실패했고 어떤 stage가 성공했는지 별도 구조가 없으면 진단이 어렵다.

필수 데이터와 선택 데이터를 분리하는 구조가 더 안전하다.

```java
CompletionStage<User> user = userService.findUser(userId); // 필수
CompletionStage<List<Order>> orders = orderService.findRecentOrders(userId); // 필수
CompletionStage<SectionResult<CouponSummary>> coupons = couponService.findCoupons(userId)
        .handle((value, ex) -> ex == null
                ? SectionResult.success("coupons", value)
                : SectionResult.failed("coupons", unwrap(ex)));

CompletionStage<Dashboard> dashboard = user.thenCombine(orders, DashboardBase::new)
        .thenCombine(coupons, (base, couponResult) -> base.withCoupons(couponResult));
```

이렇게 하면 사용자와 주문은 실패 시 전체 실패가 되고, 쿠폰은 section 실패로 내려갈 수 있다.

여러 개의 같은 타입 future를 모을 때는 helper를 둘 수 있다.

```java
public static <T> CompletionStage<List<T>> sequence(List<? extends CompletionStage<T>> stages) {
    CompletableFuture<?>[] futures = stages.stream()
            .map(CompletionStage::toCompletableFuture)
            .toArray(CompletableFuture[]::new);

    return CompletableFuture.allOf(futures)
            .thenApply(ignored -> stages.stream()
                    .map(stage -> stage.toCompletableFuture().join())
                    .toList());
}
```

단, 이 helper는 “하나 실패하면 전체 실패” 정책이다. 부분 성공이 필요하면 `Result<T>`로 감싸는 별도 helper가 필요하다.

```java
record AsyncResult<T>(String name, T value, Throwable error) {
    static <T> AsyncResult<T> success(String name, T value) {
        return new AsyncResult<>(name, value, null);
    }

    static <T> AsyncResult<T> failure(String name, Throwable error) {
        return new AsyncResult<>(name, null, error);
    }

    boolean isSuccess() {
        return error == null;
    }
}
```

---

## 실무 예시: 상품 상세 API를 비동기 조합으로 설계하기

상품 상세 화면을 생각해보자. 하나의 API 응답에 다음 데이터가 필요하다.

- 상품 기본 정보: 필수
- 판매자 정보: 필수
- 재고 상태: 필수에 가까움
- 쿠폰: 선택
- 추천 상품: 선택
- 리뷰 요약: 선택이지만 실패율을 보고 싶음

동기 코드로 쓰면 이해는 쉽지만 전체 지연 시간은 각 호출의 합에 가까워진다.

```java
public ProductDetailResponse getDetail(String productId, String userId) {
    Product product = productClient.getProduct(productId);
    Seller seller = sellerClient.getSeller(product.sellerId());
    Stock stock = stockClient.getStock(productId);
    CouponSummary coupon = couponClient.getCoupons(userId, productId);
    Recommendation recommendation = recommendationClient.getSimilarProducts(productId);
    ReviewSummary review = reviewClient.getSummary(productId);

    return ProductDetailResponse.of(product, seller, stock, coupon, recommendation, review);
}
```

이 코드는 단순하지만 다음 한계를 가진다.

- 독립 호출이 순차 실행된다
- 선택 데이터 장애가 전체 응답 장애로 번진다
- 어떤 호출이 전체 latency를 지배하는지 코드만으로 알기 어렵다
- timeout 예산이 호출별로 흩어져 있다

비동기 조합으로 바꿀 때는 무작정 `supplyAsync`를 붙이지 말고 의존성과 실패 정책을 먼저 나눠야 한다.

### 1단계: 필수 경로와 선택 경로를 나눈다

```java
public CompletionStage<ProductDetailResponse> getDetailAsync(String productId, String userId) {
    CompletionStage<Product> productStage = productGateway.getProduct(productId)
            .orTimeout(250, TimeUnit.MILLISECONDS);

    CompletionStage<Seller> sellerStage = productStage
            .thenCompose(product -> sellerGateway.getSeller(product.sellerId()))
            .orTimeout(200, TimeUnit.MILLISECONDS);

    CompletionStage<Stock> stockStage = stockGateway.getStock(productId)
            .orTimeout(150, TimeUnit.MILLISECONDS);

    CompletionStage<SectionResult<CouponSummary>> couponStage = couponGateway.getCoupons(userId, productId)
            .completeOnTimeout(CouponSummary.empty(), 120, TimeUnit.MILLISECONDS)
            .handle((value, ex) -> ex == null
                    ? SectionResult.success("coupon", value)
                    : SectionResult.failed("coupon", unwrap(ex)));

    CompletionStage<SectionResult<Recommendation>> recommendationStage = recommendationGateway.getSimilarProducts(productId)
            .completeOnTimeout(Recommendation.empty(), 120, TimeUnit.MILLISECONDS)
            .handle((value, ex) -> ex == null
                    ? SectionResult.success("recommendation", value)
                    : SectionResult.failed("recommendation", unwrap(ex)));

    CompletionStage<SectionResult<ReviewSummary>> reviewStage = reviewGateway.getSummary(productId)
            .handle((value, ex) -> ex == null
                    ? SectionResult.success("review", value)
                    : SectionResult.failed("review", unwrap(ex)));

    CompletionStage<ProductDetailBase> baseStage = productStage
            .thenCombine(sellerStage, ProductWithSeller::new)
            .thenCombine(stockStage, (productWithSeller, stock) -> new ProductDetailBase(
                    productWithSeller.product(),
                    productWithSeller.seller(),
                    stock
            ));

    return baseStage
            .thenCombine(couponStage, ProductDetailBuilder::withCoupon)
            .thenCombine(recommendationStage, ProductDetailBuilder::withRecommendation)
            .thenCombine(reviewStage, ProductDetailBuilder::withReview)
            .thenApply(ProductDetailBuilder::build);
}
```

이 코드는 길어 보이지만 정책이 보인다.

- 상품, 판매자, 재고는 필수다
- 쿠폰과 추천은 timeout 시 빈 값으로 degraded 처리한다
- 리뷰는 실패를 section 실패로 담는다
- 상품 조회 결과가 있어야 판매자 조회가 가능하므로 `thenCompose`를 쓴다
- 재고는 productId만 있으면 되므로 독립적으로 시작한다

### 2단계: gateway 내부에서 executor와 client timeout을 책임진다

상위 서비스가 모든 executor를 알 필요는 없다. 외부 의존성 호출 경계인 gateway가 실행 정책을 가진다.

```java
public class ProductGateway {
    private final ProductClient productClient;
    private final ExecutorService productExecutor;

    public CompletionStage<Product> getProduct(String productId) {
        return CompletableFuture.supplyAsync(
                () -> productClient.getProduct(productId),
                productExecutor
        );
    }
}
```

단, gateway 내부에 숨긴다고 해서 관측하지 않아도 된다는 뜻은 아니다. executor queue, active count, timeout count, fallback count를 metric으로 노출해야 한다.

### 3단계: 동기 controller 경계에서만 기다린다

Spring MVC 같은 동기 controller라면 마지막 경계에서만 기다린다.

```java
@GetMapping("/products/{productId}")
public ProductDetailResponse getDetail(
        @PathVariable String productId,
        @AuthenticationPrincipal UserPrincipal principal
) {
    try {
        return productDetailService.getDetailAsync(productId, principal.userId())
                .toCompletableFuture()
                .orTimeout(700, TimeUnit.MILLISECONDS)
                .join();
    } catch (CompletionException ex) {
        throw productDetailExceptionMapper.map(unwrap(ex));
    }
}
```

중요한 원칙은 이것이다.

> 비동기 그래프 중간에서 `join()`하지 말고, 시스템 경계에서 한 번만 동기화하라.

중간 `join()`은 병렬성을 깨뜨리고 deadlock 가능성을 키우며 timeout 예산을 흐리게 만든다.

---

## 트레이드오프: `CompletableFuture`가 항상 정답은 아니다

`CompletableFuture`는 강력하지만 모든 비동기 문제의 기본값이 되어서는 안 된다.

### 장점

- JDK 표준 API라 별도 라이브러리 의존이 없다
- 독립 I/O 작업을 병렬로 조합하기 좋다
- `thenCompose`, `thenCombine`으로 의존 그래프를 표현할 수 있다
- 기존 blocking client를 감싸 점진적으로 비동기화할 수 있다
- controller나 service 계층에서 작은 범위의 fan-out/fan-in에 적용하기 쉽다

### 단점

- cancellation이 실제 작업 중단으로 이어진다는 보장이 약하다
- backpressure 모델이 없다
- 복잡한 stream processing에는 부적합하다
- 예외 흐름이 래핑되어 디버깅이 번거롭다
- 컨텍스트 전파를 직접 챙겨야 한다
- executor 정책을 잘못 잡으면 공용 풀 오염, queue 폭주, tail latency 증가가 생긴다

### Virtual Threads와의 관계

Java 21 이후라면 “그냥 virtual thread로 순차 blocking 코드를 쓰면 안 되나?”라는 질문이 자연스럽다.

가능하다. 특히 요청 단위 코드가 단순하고, 각 호출에 timeout과 bulkhead가 잘 잡혀 있고, 비동기 조합이 코드 가독성을 크게 해친다면 virtual thread 기반 thread-per-request가 더 나을 수 있다.

하지만 `CompletableFuture`가 여전히 유용한 경우도 있다.

- 독립 작업 여러 개를 명시적으로 동시에 시작하고 결과를 조합해야 한다
- 일부 stage만 fallback 또는 부분 성공으로 바꾸고 싶다
- callback 기반 API를 감싸야 한다
- 비동기 client가 이미 `CompletionStage`를 반환한다
- 라이브러리 API 경계가 `CompletionStage` 중심이다

반대로 다음 상황에서는 virtual thread나 structured concurrency가 더 읽기 쉬울 수 있다.

- 요청 단위로 명확한 parent-child 작업 구조가 있다
- 실패 시 나머지 작업을 함께 취소해야 한다
- 코드가 `thenCompose` 체인으로 지나치게 깊어졌다
- 디버깅과 stack trace 가독성이 더 중요하다

즉 선택 기준은 유행이 아니다.

- 작은 fan-out 조합: `CompletableFuture`
- 많은 blocking I/O를 기존 코드 스타일로 처리: virtual threads
- event stream, backpressure, long-running pipeline: reactive streams 또는 메시징
- CPU 병렬 계산: 명시적 executor, parallel algorithm, batch framework

### Reactive와의 관계

Reactor, RxJava 같은 reactive 라이브러리는 backpressure와 stream 연산을 제공한다. `CompletableFuture`는 단발성 결과 조합에 가깝다.

따라서 “HTTP 호출 4개를 동시에 하고 결과를 합친다”는 문제에는 `CompletableFuture`가 충분할 수 있다. 반면 “사용자 이벤트 스트림을 계속 받아 윈도우 집계하고 downstream 속도에 맞춰 흘린다”는 문제에는 맞지 않는다.

---

## 흔한 실수 1: `join()`을 중간에 호출해 병렬성을 없앤다

나쁜 예다.

```java
Product product = productService.findProduct(productId).toCompletableFuture().join();
Seller seller = sellerService.findSeller(product.sellerId()).toCompletableFuture().join();
Stock stock = stockService.findStock(productId).toCompletableFuture().join();
```

이 코드는 future를 쓰지만 사실상 동기 순차 코드다. 특히 재고 조회가 상품 결과에 의존하지 않는다면 처음부터 같이 시작해야 한다.

```java
CompletionStage<Product> productStage = productService.findProduct(productId);
CompletionStage<Stock> stockStage = stockService.findStock(productId);

CompletionStage<ProductDetail> detailStage = productStage
        .thenCompose(product -> sellerService.findSeller(product.sellerId())
                .thenCombine(stockStage, (seller, stock) -> ProductDetail.of(product, seller, stock)));
```

원칙은 간단하다.

- 가능한 빨리 독립 작업을 시작한다
- 가능한 늦게 결과를 기다린다
- 중간에서는 조합하고, 마지막 경계에서만 동기화한다

---

## 흔한 실수 2: timeout을 하나만 걸고 전체 예산을 관리하지 않는다

각 외부 호출에 timeout이 있어도 전체 요청 timeout을 넘길 수 있다.

예를 들어 세 호출이 각각 500ms timeout이면 전체 API가 500ms 안에 끝날 것 같지만, 의존 관계와 재시도, queue 대기까지 포함하면 1초를 훌쩍 넘을 수 있다.

운영에서는 request budget을 먼저 잡아야 한다.

- 전체 API 목표: 800ms
- 상품 조회: 250ms
- 판매자 조회: 200ms
- 재고 조회: 150ms
- 쿠폰/추천: 100~150ms, 실패 시 degraded
- controller 최종 timeout: 750ms
- load balancer/client timeout: 그보다 약간 크게

그리고 각 stage의 timeout은 이 예산 안에서 의미를 가져야 한다. timeout 숫자를 여기저기 흩뿌리면 결국 아무도 전체 응답 시간을 책임지지 않는다.

---

## 흔한 실수 3: 예외를 fallback으로 바꾸고 metric을 남기지 않는다

```java
CompletionStage<CouponSummary> coupon = couponService.findCoupons(userId)
        .exceptionally(ex -> CouponSummary.empty());
```

이 코드는 사용자 경험 관점에서는 좋아 보인다. 쿠폰 서비스가 잠깐 실패해도 상품 페이지는 뜬다.

하지만 metric이 없으면 운영자는 쿠폰 서비스 장애를 모른다. 매출에 영향을 줄 수도 있는데 API는 계속 200을 반환한다.

최소한 다음 신호를 남겨야 한다.

```java
CompletionStage<CouponSummary> coupon = couponService.findCoupons(userId)
        .exceptionally(ex -> {
            Throwable cause = unwrap(ex);
            metrics.counter("coupon.lookup.fallback", "reason", cause.getClass().getSimpleName()).increment();
            log.warn("coupon fallback. userId={}, productId={}", userId, productId, cause);
            return CouponSummary.empty();
        });
```

다만 `reason` label에 예외 메시지나 productId를 넣으면 cardinality가 폭발한다. metric label은 낮은 cardinality로 제한해야 한다.

---

## 흔한 실수 4: executor를 크게 잡아 다운스트림을 더 세게 때린다

외부 API가 느릴 때 executor 크기를 키우면 당장은 queue 대기가 줄어드는 것처럼 보일 수 있다. 하지만 근본 병목이 다운스트림 용량이라면 동시 호출 수를 늘리는 것은 장애를 가속한다.

executor 크기는 “내 서버가 만들 수 있는 스레드 수”가 아니라 **다운스트림이 감당 가능한 동시 요청 수와 내 서비스의 timeout 예산**을 기준으로 정해야 한다.

예를 들어 추천 API가 p95 120ms이고 안정적으로 200 RPS를 받을 수 있다면, 단순 Little's Law 관점에서 필요한 동시성은 대략 다음과 같다.

```text
concurrency ≈ throughput × latency
            ≈ 200 req/s × 0.12 s
            ≈ 24
```

물론 스파이크, tail latency, retry, network jitter를 고려해 여유를 둬야 하지만, 무작정 500 thread를 열 이유는 없다.

운영에서는 executor를 bulkhead로 봐야 한다.

- 너무 작으면 정상 트래픽에서도 queue 대기가 커진다
- 너무 크면 다운스트림 장애를 증폭한다
- queue가 너무 크면 실패가 늦게 드러난다
- rejection 정책이 없으면 overload 시 메모리와 latency가 같이 무너진다

---

## 흔한 실수 5: MDC와 trace context가 비동기 경계에서 사라진다

동기 요청 처리에서는 `MDC`에 넣은 `traceId`가 자연스럽게 로그에 붙는다. 하지만 executor를 넘어가면 thread-local 기반 컨텍스트는 자동으로 이어지지 않는다.

```java
CompletableFuture.supplyAsync(() -> {
    log.info("calling product api"); // traceId가 없을 수 있음
    return productClient.get(productId);
}, productExecutor);
```

이 문제를 방치하면 장애 상황에서 로그가 끊긴다. 해결 방법은 환경마다 다르지만 원칙은 같다.

- task 제출 시점의 컨텍스트를 capture한다
- worker thread에서 실행하기 전에 restore한다
- 실행 후 반드시 clear한다

간단한 형태는 다음과 같다.

```java
public final class ContextAwareExecutor implements Executor {
    private final Executor delegate;

    public ContextAwareExecutor(Executor delegate) {
        this.delegate = delegate;
    }

    @Override
    public void execute(Runnable command) {
        Map<String, String> contextMap = MDC.getCopyOfContextMap();
        delegate.execute(() -> {
            Map<String, String> previous = MDC.getCopyOfContextMap();
            try {
                if (contextMap != null) {
                    MDC.setContextMap(contextMap);
                } else {
                    MDC.clear();
                }
                command.run();
            } finally {
                if (previous != null) {
                    MDC.setContextMap(previous);
                } else {
                    MDC.clear();
                }
            }
        });
    }
}
```

Spring, Micrometer Tracing, OpenTelemetry 환경에서는 이미 제공되는 context propagation 기능을 우선 검토해야 한다. 직접 구현할 때는 누락과 메모리 누수를 조심해야 한다.

---

## 흔한 실수 6: cancellation을 과신한다

`CompletableFuture.cancel(true)`를 호출하면 작업이 중단될 것처럼 느껴진다. 하지만 `CompletableFuture`의 cancel은 future를 취소 상태로 완료시키는 의미에 가깝고, 이미 실행 중인 supplier가 반드시 interrupt되는 것은 아니다.

```java
CompletableFuture<Product> future = CompletableFuture.supplyAsync(() -> productClient.get(productId), executor);
future.cancel(true);
```

이 코드가 실제 HTTP 요청을 끊는지는 사용한 client와 실행 방식에 달려 있다.

따라서 취소가 중요하다면 다음을 같이 설계해야 한다.

- HTTP client의 request timeout
- cancellable API 사용 여부
- thread interrupt에 반응하는 코드인지 여부
- 상위 요청 취소 시 하위 요청을 취소하는 구조
- 취소된 작업의 metric과 log

취소를 “자원 회수”로 믿기보다 timeout과 bulkhead로 애초에 오래 붙잡지 않게 만드는 편이 더 현실적이다.

---

## 흔한 실수 7: 테스트에서 이미 완료된 future만 써서 race를 보지 못한다

테스트에서 다음처럼 이미 완료된 future만 반환하면 조합 로직은 검증되지만 executor, timeout, 예외 순서 문제는 잘 드러나지 않는다.

```java
when(productGateway.getProduct(productId))
        .thenReturn(CompletableFuture.completedFuture(product));
```

이 테스트도 필요하다. 하지만 timeout, 부분 실패, 지연 순서도 별도로 테스트해야 한다.

```java
@Test
void recommendationTimeoutFallsBack() {
    CompletableFuture<Recommendation> never = new CompletableFuture<>();
    when(recommendationGateway.getSimilarProducts(productId)).thenReturn(never);

    ProductDetailResponse response = service.getDetailAsync(productId, userId)
            .toCompletableFuture()
            .join();

    assertThat(response.recommendation().isDegraded()).isTrue();
}
```

시간 기반 테스트는 느려지기 쉽다. 가능하면 timeout 값을 주입 가능하게 만들고, scheduler나 clock을 제어할 수 있는 구조를 고려한다. 최소한 운영 timeout 그대로 수백 ms씩 기다리는 테스트를 대량으로 만들지는 말아야 한다.

---

## 운영 관측성: future 그래프는 보이지 않으므로 신호를 직접 심어야 한다

`CompletableFuture` 조합은 코드 안에 그래프로 존재하지만, 운영 도구가 자동으로 “어느 stage가 병목인지” 완벽히 보여주지는 않는다. 따라서 중요한 stage에는 관측 신호를 심어야 한다.

### stage별 latency

외부 호출 경계에서 timer를 남긴다.

```java
public CompletionStage<Product> getProduct(String productId) {
    long start = System.nanoTime();
    return CompletableFuture.supplyAsync(() -> productClient.getProduct(productId), productExecutor)
            .whenComplete((value, ex) -> {
                long elapsed = System.nanoTime() - start;
                metrics.timer("external.product.latency").record(elapsed, TimeUnit.NANOSECONDS);
                if (ex != null) {
                    metrics.counter("external.product.error", "type", unwrap(ex).getClass().getSimpleName()).increment();
                }
            });
}
```

### executor 상태

다음 지표는 반드시 봐야 한다.

- active thread count
- pool size
- queue size
- completed task count
- rejected task count
- task wait time
- task execution time

특히 queue size만 보고 안심하면 안 된다. queue가 비어 있어도 active thread가 항상 최대치라면 이미 포화 상태일 수 있다. 반대로 queue가 쌓이기 시작했다면 사용자 latency는 이미 증가 중일 가능성이 높다.

### fallback과 degraded response

fallback은 성공이 아니다. 별도 metric으로 봐야 한다.

- `coupon.fallback.count`
- `recommendation.timeout.count`
- `review.section.failed.count`
- `dashboard.degraded.response.count`

그리고 dashboard에는 “전체 API 200 비율”뿐 아니라 “degraded 응답 비율”이 있어야 한다. 그렇지 않으면 사용자는 기능이 빠진 화면을 보고 있는데 운영자는 성공률 99.9%를 보고 있을 수 있다.

---

## 설계 패턴: 비동기 정책을 서비스 코드에 흩뿌리지 않는다

`CompletableFuture` 코드가 유지보수 어려워지는 이유 중 하나는 timeout, fallback, metric, executor 선택이 service method마다 복붙되기 때문이다.

반복 정책은 작은 유틸리티나 gateway 레벨로 모으는 편이 좋다.

```java
public final class AsyncPolicies {

    public static <T> CompletionStage<SectionResult<T>> optionalSection(
            String name,
            CompletionStage<T> stage,
            MeterRegistry metrics
    ) {
        return stage.handle((value, ex) -> {
            if (ex == null) {
                return SectionResult.success(name, value);
            }
            Throwable cause = unwrap(ex);
            metrics.counter("section.failed", "section", name, "type", cause.getClass().getSimpleName()).increment();
            return SectionResult.failed(name, cause);
        });
    }
}
```

그러면 서비스 코드는 비즈니스 의도를 더 잘 드러낸다.

```java
CompletionStage<SectionResult<CouponSummary>> coupon = AsyncPolicies.optionalSection(
        "coupon",
        couponGateway.getCoupons(userId, productId)
                .completeOnTimeout(CouponSummary.empty(), 120, TimeUnit.MILLISECONDS),
        metrics
);
```

단, 유틸리티가 모든 것을 숨기면 다시 문제가 된다. 정책 이름이 명확해야 한다.

- `optionalSection`: 실패해도 전체 응답은 유지
- `requiredStage`: 실패 시 전체 실패
- `withTimeoutMetric`: timeout 관측
- `withFallback`: fallback 발생을 명시

정책 이름만 보고도 장애 의미를 이해할 수 있어야 한다.

---

## 코드 리뷰 기준: 이 질문에 답하지 못하면 위험하다

`CompletableFuture` 코드 리뷰에서는 문법보다 운영 질문을 해야 한다.

1. 이 stage는 어떤 executor에서 실행되는가?
2. 기본 `commonPool`을 쓰고 있다면 그 이유가 명확한가?
3. blocking I/O가 `thenApply` 안에 숨어 있지 않은가?
4. 독립 작업을 불필요하게 순차화하지 않았는가?
5. 중간 `join()`으로 병렬성을 깨지 않았는가?
6. 각 외부 호출 timeout과 전체 request budget이 일관되는가?
7. timeout이 실제 client timeout과 future timeout 양쪽에 반영되어 있는가?
8. fallback은 비즈니스적으로 안전한가?
9. fallback, timeout, section failure metric이 있는가?
10. 예외를 삼키는 `exceptionally`가 장애를 숨기지 않는가?
11. `allOf()` 실패 시 어떤 작업이 실패했는지 알 수 있는가?
12. MDC, trace context, security context 전파가 필요한가?
13. executor queue와 rejection 정책은 의도적인가?
14. 취소가 필요한 작업이라면 실제 자원 중단까지 고려했는가?
15. 테스트가 성공, 실패, timeout, 부분 성공을 모두 다루는가?

이 질문에 답할 수 있으면 코드는 조금 길어도 운영 가능한 코드다. 답할 수 없다면 짧고 예쁜 체인도 위험하다.


---

## 심화 1: executor sizing은 감이 아니라 병목 위치로 계산한다

`CompletableFuture`를 쓰기 시작하면 가장 먼저 나오는 운영 질문은 thread pool 크기다.

많은 팀이 처음에는 이렇게 정한다.

- 서버 CPU가 8 core니까 16개
- 예전에도 100개쯤 썼으니까 100개
- timeout이 자주 나니까 300개
- queue가 찼으니까 1,000개

이 접근은 위험하다. executor 크기는 “내 JVM이 만들 수 있는 thread 수”가 아니라 **대기 작업의 평균 시간, 목표 처리량, 다운스트림 허용 동시성, 실패 시 차단하고 싶은 장애 반경**으로 정해야 한다.

### CPU bound와 I/O bound는 계산 기준이 다르다

CPU bound 작업은 동시에 많이 돌린다고 빨라지지 않는다. CPU core보다 훨씬 많은 작업을 runnable 상태로 만들면 context switch와 cache miss가 늘어난다.

반면 I/O bound 작업은 대부분 시간을 대기에 쓴다. thread가 응답을 기다리는 동안 CPU는 놀 수 있으므로 CPU core 수보다 많은 동시 작업이 의미 있을 수 있다.

하지만 I/O bound라고 해서 무한히 늘려도 되는 것은 아니다. 병목은 보통 아래로 이동한다.

- 외부 API rate limit
- DB connection pool
- Redis connection pool
- HTTP client connection pool
- NAT gateway 또는 load balancer connection
- downstream thread pool
- 내 서비스의 heap과 queue

즉 executor는 처리량을 늘리는 장치이면서 동시에 **다운스트림으로 흘러가는 압력을 제한하는 밸브**다.

### Little's Law로 시작점을 잡는다

대략적인 시작점은 Little's Law로 잡을 수 있다.

```text
동시성(concurrency) ≈ 처리량(throughput) × 응답시간(latency)
```

예를 들어 상품 API 호출이 다음 특성을 가진다고 하자.

- 목표 처리량: 300 RPS
- 상품 API p95 latency: 120ms
- 상품 API p99 latency: 300ms

p95 기준 동시성은 다음과 같다.

```text
300 req/s × 0.12 s = 36
```

p99 기준으로는 다음이다.

```text
300 req/s × 0.30 s = 90
```

이 숫자는 정답이 아니라 출발점이다. 운영에서는 다음을 추가로 본다.

- 외부 API가 허용하는 최대 동시 요청 수
- 내 HTTP client connection pool 크기
- timeout 발생 시 작업이 얼마나 오래 남는지
- retry가 동시성을 몇 배로 증폭하는지
- queue 대기까지 포함한 사용자 latency 목표

따라서 상품 API executor를 80으로 시작할 수는 있지만, 외부 API가 tenant당 50 concurrent request만 허용한다면 80은 이미 공격적이다.

### queue 크기는 '몇 개까지 기다릴 수 있는가'가 아니라 '얼마나 오래 기다리게 할 것인가'다

queue 1,000개는 넉넉해 보인다. 하지만 평균 처리 시간이 200ms이고 worker가 50개라면, queue 끝에 들어간 작업은 최악의 경우 몇 초 뒤에 실행될 수 있다.

사용자 요청 timeout이 800ms라면 그 작업은 실행되기도 전에 이미 의미가 없다.

그래서 queue 크기는 다음 질문으로 정해야 한다.

- 사용자가 기다릴 수 있는 남은 시간이 얼마인가?
- queue에 들어간 작업이 실행될 때 결과가 아직 필요한가?
- queue 대기 시간이 timeout budget에 포함되는가?
- overload 상황에서 빠르게 실패하는 것이 더 낫지 않은가?

실무에서는 큰 무한 queue보다 작은 bounded queue와 명확한 rejection 정책이 낫다.

```java
new ThreadPoolExecutor(
        30,
        60,
        30, TimeUnit.SECONDS,
        new ArrayBlockingQueue<>(200),
        new NamedThreadFactory("inventory-client-"),
        new ThreadPoolExecutor.AbortPolicy()
);
```

`AbortPolicy`는 예외를 던진다. 처음에는 거칠어 보이지만 overload를 빠르게 드러낸다. API 특성에 따라 `CallerRunsPolicy`도 선택할 수 있다.

단, `CallerRunsPolicy`는 호출자 thread에서 작업을 실행하므로 web request thread가 blocking I/O를 직접 수행하게 될 수 있다. 이것이 backpressure로 작동할 수도 있고, request thread 고갈로 번질 수도 있다. 반드시 부하 테스트로 확인해야 한다.

### executor metric을 해석하는 법

executor metric은 숫자만 보면 안 된다. 조합해서 읽어야 한다.

| 신호 | 해석 | 의심할 문제 |
| --- | --- | --- |
| active thread가 max 근처 | worker가 계속 바쁨 | downstream 지연, pool 과소, timeout 과대 |
| queue가 지속 증가 | 처리율보다 유입률이 큼 | overload, downstream 장애 |
| rejection 증가 | 제한 장치 작동 | 보호 성공 또는 용량 부족 |
| completed task는 증가하지만 latency도 증가 | 처리 중이지만 늦음 | queue wait, downstream p99 악화 |
| active는 낮은데 latency 증가 | executor 밖 병목 | DNS, connection pool, lock, GC |

특히 `queue size = 0`만 보고 건강하다고 판단하면 안 된다. synchronous handoff 구조이거나 max thread가 이미 포화된 상태일 수 있다.

### pool isolation의 단위

executor를 나눌지 합칠지는 장애 반경으로 결정한다.

같은 외부 시스템을 호출하는 여러 기능이 있다면 같은 executor를 쓰는 편이 전체 동시성을 제한하기 쉽다.

```text
ProductGateway
 ├─ getProduct
 ├─ getProductOptions
 └─ getProductBadges

→ product-client-executor 하나로 묶어 product system 보호
```

반대로 서로 다른 중요도와 장애 특성을 가진 의존성은 분리한다.

```text
payment-client-executor        // 핵심, 작은 queue, 엄격한 timeout
recommendation-client-executor // 선택, 작은 timeout, fallback 허용
analytics-client-executor      // 비핵심, fire-and-forget 금지, 낮은 우선순위
```

executor는 성능 튜닝 값이기도 하지만, 더 본질적으로는 **운영 격리 경계**다.

---

## 심화 2: timeout budget은 deadline으로 흘려보내야 한다

`orTimeout(300ms)` 같은 숫자를 stage마다 직접 박아 넣으면 처음에는 명확해 보인다. 하지만 API가 커지면 금방 문제가 생긴다.

```java
product.orTimeout(300, MILLISECONDS);
seller.orTimeout(300, MILLISECONDS);
stock.orTimeout(300, MILLISECONDS);
coupon.orTimeout(300, MILLISECONDS);
```

이 코드는 “모든 하위 호출은 300ms”라는 뜻일까? 아니면 “전체 요청이 300ms”라는 뜻일까? 호출이 순차로 섞이면 전체는 300ms를 훨씬 넘을 수 있다.

운영에서는 timeout을 개별 숫자보다 **deadline**으로 생각하는 편이 안전하다.

### deadline 객체

```java
public final class Deadline {
    private final long deadlineNanos;

    private Deadline(long deadlineNanos) {
        this.deadlineNanos = deadlineNanos;
    }

    public static Deadline after(Duration duration) {
        return new Deadline(System.nanoTime() + duration.toNanos());
    }

    public Duration remaining() {
        long nanos = deadlineNanos - System.nanoTime();
        return Duration.ofNanos(Math.max(0, nanos));
    }

    public boolean expired() {
        return remaining().isZero();
    }
}
```

상위 request가 800ms budget을 갖는다면 하위 호출은 그 안에서 남은 시간을 배분한다.

```java
Deadline deadline = Deadline.after(Duration.ofMillis(800));

CompletionStage<Product> product = productGateway.getProduct(productId, deadline)
        .orTimeout(deadline.remaining().toMillis(), TimeUnit.MILLISECONDS);
```

gateway 내부에서도 client timeout을 deadline 기반으로 줄일 수 있다.

```java
public CompletionStage<Product> getProduct(String productId, Deadline deadline) {
    Duration timeout = min(deadline.remaining(), Duration.ofMillis(250));
    return CompletableFuture.supplyAsync(
            () -> productClient.get(productId, timeout),
            productExecutor
    );
}
```

이 방식의 장점은 뒤늦게 시작한 작업이 이미 끝난 예산으로 오래 달리지 않는다는 점이다.

### timeout은 계층별로 의미가 다르다

한 요청에는 여러 timeout이 있다.

1. Browser 또는 mobile app timeout
2. CDN/load balancer timeout
3. API gateway timeout
4. application controller timeout
5. service 조합 timeout
6. HTTP client connect timeout
7. HTTP client read timeout
8. DB query timeout
9. executor queue wait limit

이 값들은 서로 독립적이면 안 된다. 바깥 timeout이 1초인데 내부 DB query timeout이 10초라면, 사용자는 이미 실패했는데 DB 작업은 계속 살아 있을 수 있다.

실무 기준은 보통 바깥에서 안쪽으로 갈수록 더 짧고 명확해야 한다.

```text
mobile client:         3,000ms
API gateway:           1,500ms
application request:     900ms
product detail budget:   800ms
required product call:   250ms
optional recommendation: 120ms
```

이렇게 설계하면 실패가 어디서 먼저 발생해야 하는지 예측할 수 있다.

### timeout과 retry를 같이 계산하라

retry는 timeout budget을 쉽게 망가뜨린다.

```text
요청 timeout 300ms
retry 2회
각 시도 read timeout 300ms
```

이 설정은 최악의 경우 900ms 이상을 쓸 수 있다. retry backoff까지 있으면 더 길어진다.

따라서 retry는 전체 deadline 안에서 시도별 timeout을 나눠야 한다.

```text
전체 budget: 300ms
1차 시도: 120ms
backoff: 20ms
2차 시도: 100ms
backoff: 20ms
3차 시도: 남은 시간 이내
```

그리고 모든 실패에 retry하면 안 된다.

- timeout: 제한적으로 retry 가능
- connection reset: 제한적으로 retry 가능
- 429: Retry-After 존중
- 4xx validation error: retry 금지
- 결제 승인 같은 non-idempotent 작업: idempotency key 없으면 retry 금지

`CompletableFuture` 자체는 retry 정책을 제공하지 않는다. 직접 구현하거나 resilience 라이브러리를 사용할 때도 timeout budget과 idempotency를 함께 봐야 한다.

---

## 심화 3: 예외를 기술 예외가 아니라 비즈니스 결정으로 분류하라

`CompletableFuture` 체인에서 예외는 쉽게 뭉개진다. `CompletionException`으로 감싸지고, `exceptionally`에서 fallback 값으로 바뀌고, `allOf`에서 어떤 작업이 실패했는지 흐려진다.

그래서 예외 처리는 catch 위치보다 **분류 체계**가 먼저다.

### 예외 분류 예시

상품 상세 API에서 예외를 다음처럼 나눌 수 있다.

| 분류 | 예시 | 처리 |
| --- | --- | --- |
| RequiredFailure | 상품 없음, 판매자 조회 실패 | 전체 API 실패 |
| OptionalFailure | 추천 API timeout, 리뷰 요약 실패 | section degraded |
| PolicyFailure | 성인 인증 필요, 지역 제한 | 명시적 비즈니스 응답 |
| OverloadFailure | executor rejection, bulkhead full | 빠른 실패 또는 degraded |
| UnknownFailure | 예상 못한 NPE, serialization 오류 | 전체 실패 + alert |

이 분류가 없으면 모든 예외가 “500 또는 빈 값”으로 떨어진다.

### 결과 타입으로 의미를 보존한다

선택 section은 예외를 숨기지 말고 결과 타입에 담을 수 있다.

```java
sealed interface SectionResult<T> permits SectionResult.Success, SectionResult.Degraded {

    String name();

    record Success<T>(String name, T value) implements SectionResult<T> {}

    record Degraded<T>(String name, String reason, boolean userVisible) implements SectionResult<T> {}

    static <T> SectionResult<T> success(String name, T value) {
        return new Success<>(name, value);
    }

    static <T> SectionResult<T> degraded(String name, Throwable error) {
        return new Degraded<>(name, error.getClass().getSimpleName(), true);
    }
}
```

이렇게 하면 응답 생성 시 “추천 데이터 없음”과 “추천 시스템 실패”를 구분할 수 있다.

운영에서도 이 차이는 중요하다.

- 데이터가 원래 없는 것: 정상
- timeout 때문에 빠진 것: 성능 문제
- 5xx 때문에 빠진 것: 다운스트림 장애
- 권한 때문에 빠진 것: 정책 결과

모두 같은 빈 배열로 내려가면 분석이 어려워진다.

### `exceptionally` 위치가 의미를 바꾼다

아래 두 코드는 의미가 다르다.

```java
CompletionStage<Dashboard> dashboard = productStage
        .thenCombine(reviewStage, Dashboard::withReview)
        .exceptionally(ex -> Dashboard.empty());
```

마지막에 `exceptionally`를 붙이면 상품 조회 실패도 빈 대시보드로 바뀐다. 필수 데이터 실패까지 숨길 수 있다.

반면 선택 stage에만 복구를 붙이면 의미가 좁아진다.

```java
CompletionStage<SectionResult<ReviewSummary>> reviewSection = reviewStage
        .handle((value, ex) -> ex == null
                ? SectionResult.success("review", value)
                : SectionResult.degraded("review", unwrap(ex)));

CompletionStage<Dashboard> dashboard = productStage
        .thenCombine(reviewSection, Dashboard::withReview);
```

예외 처리는 “어디에 붙였는가”가 정책이다.

### unknown exception은 과감히 실패시킨다

fallback을 많이 넣은 서비스에서 흔한 사고는 NPE, mapping bug, serialization bug까지 fallback으로 삼키는 것이다.

```java
.exceptionally(ex -> DefaultResponse.empty())
```

이 코드는 timeout도, validation bug도, NullPointerException도 모두 빈 응답으로 바꾼다. 사용자는 이상한 화면을 보고, 운영자는 한참 뒤에 데이터 이상으로 문제를 발견한다.

fallback은 예상 가능한 실패에만 적용해야 한다.

```java
.exceptionally(ex -> {
    Throwable cause = unwrap(ex);
    if (cause instanceof TimeoutException || cause instanceof DownstreamUnavailableException) {
        return DefaultResponse.degraded();
    }
    throw new CompletionException(cause);
})
```

예상 못한 버그는 빠르게 실패하고 알림을 울리는 편이 낫다.

---

## 심화 4: `allOf`를 운영 가능한 fan-out/fan-in으로 감싸기

`allOf`는 낮은 수준의 도구다. 실무 fan-out/fan-in에는 보통 더 많은 정보가 필요하다.

- 작업 이름
- 시작 시각
- 종료 시각
- 성공 여부
- 실패 원인
- timeout 여부
- fallback 여부
- 결과 필수 여부

이를 위해 작업 descriptor를 둘 수 있다.

```java
public record AsyncCall<T>(
        String name,
        boolean required,
        CompletionStage<T> stage
) {}
```

결과도 분리한다.

```java
public record AsyncCallResult<T>(
        String name,
        boolean required,
        T value,
        Throwable error,
        long elapsedMillis
) {
    boolean success() {
        return error == null;
    }
}
```

fan-out helper는 각 stage를 `handle`로 감싼 뒤 모두 기다린다.

```java
public static <T> CompletionStage<List<AsyncCallResult<T>>> collect(
        List<AsyncCall<T>> calls
) {
    List<CompletableFuture<AsyncCallResult<T>>> wrapped = calls.stream()
            .map(call -> {
                long start = System.nanoTime();
                return call.stage().handle((value, ex) -> new AsyncCallResult<>(
                        call.name(),
                        call.required(),
                        value,
                        ex == null ? null : unwrap(ex),
                        TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - start)
                )).toCompletableFuture();
            })
            .toList();

    return CompletableFuture.allOf(wrapped.toArray(CompletableFuture[]::new))
            .thenApply(ignored -> wrapped.stream()
                    .map(CompletableFuture::join)
                    .toList());
}
```

이 helper는 모든 작업을 결과 객체로 바꾸기 때문에 `allOf` 자체가 실패하지 않는다. 이후 required 실패가 있으면 정책적으로 전체 실패를 만들 수 있다.

```java
CompletionStage<List<AsyncCallResult<Object>>> collected = collect(calls);

return collected.thenApply(results -> {
    List<AsyncCallResult<Object>> requiredFailures = results.stream()
            .filter(result -> result.required() && !result.success())
            .toList();

    if (!requiredFailures.isEmpty()) {
        throw new RequiredAsyncCallFailedException(requiredFailures);
    }

    return buildResponse(results);
});
```

이 구조의 장점은 다음이다.

- 어떤 stage가 실패했는지 잃지 않는다
- required/optional 정책을 나중에 명확히 적용한다
- stage별 elapsed time을 남길 수 있다
- dashboard에서 느린 section을 찾기 쉽다

단점도 있다.

- 타입 안정성이 약해질 수 있다
- 결과 조립 코드가 복잡해진다
- 모든 stage를 같은 타입으로 다루기 위해 wrapper가 필요하다

따라서 모든 코드에 쓰기보다, stage 수가 많고 부분 성공 정책이 중요한 API에 제한적으로 쓰는 편이 좋다.

---

## 심화 5: Spring 환경에서 자주 만나는 함정

Spring Boot에서 `CompletableFuture`를 쓸 때는 프레임워크 기능과 섞이며 예상 밖의 동작이 나온다.

### `@Async`와 self-invocation

Spring의 `@Async`는 proxy 기반이다. 같은 클래스 내부에서 자기 메서드를 호출하면 proxy를 거치지 않아 비동기로 실행되지 않는다.

```java
@Service
public class ReportService {

    public CompletionStage<Report> createReport(String id) {
        return loadDataAsync(id); // self-invocation이면 @Async 미적용
    }

    @Async("reportExecutor")
    public CompletableFuture<ReportData> loadDataAsync(String id) {
        return CompletableFuture.completedFuture(loadData(id));
    }
}
```

이 코드는 기대와 달리 동기로 실행될 수 있다. 해결책은 다음 중 하나다.

- 비동기 메서드를 별도 bean으로 분리한다
- `CompletableFuture.supplyAsync(..., executor)`를 명시적으로 사용한다
- proxy 호출 구조를 명확히 만든다

개인적으로는 핵심 도메인 서비스 내부에서 `@Async` 마법에 의존하기보다 executor를 명시하는 방식을 더 선호한다. 실행 위치가 코드에 보이기 때문이다.

### `@Transactional`과 비동기 경계

트랜잭션은 thread-bound다. `@Transactional` 메서드 안에서 `supplyAsync`로 다른 thread를 사용하면 그 thread에는 기존 트랜잭션이 전파되지 않는다.

```java
@Transactional
public CompletionStage<Void> updateAndNotify(Order order) {
    orderRepository.save(order);

    return CompletableFuture.runAsync(() -> {
        // 여기서는 같은 transaction이 아니다
        notificationRepository.save(...);
    }, executor);
}
```

이 코드는 정합성 오해를 만든다.

- 비동기 작업이 먼저 실행되어 아직 commit되지 않은 데이터를 읽을 수 없다
- transaction rollback 후에도 비동기 side effect가 실행될 수 있다
- lazy loading entity를 다른 thread에서 접근하다 예외가 날 수 있다

트랜잭션 이후 비동기 side effect가 필요하면 outbox, transaction event after commit, message queue를 검토해야 한다.

```java
@Transactional
public void placeOrder(OrderCommand command) {
    Order order = orderRepository.save(Order.create(command));
    outboxRepository.save(OutboxMessage.orderPlaced(order.id()));
}
```

비동기 실행은 commit 이후 outbox consumer가 담당하는 편이 안전하다.

### SecurityContext 전파

Spring Security의 `SecurityContextHolder`도 기본적으로 thread-local이다. executor를 넘으면 인증 정보가 사라질 수 있다.

Spring은 `DelegatingSecurityContextExecutor` 같은 도구를 제공한다. 직접 MDC wrapper를 만들기 전에 보안 컨텍스트 전파 방식도 확인해야 한다.

다만 보안 컨텍스트를 무조건 전파하는 것이 정답은 아니다. 비동기 작업이 사용자 권한으로 실행되어야 하는지, 시스템 권한으로 실행되어야 하는지 명확해야 한다.

### WebFlux와 섞을 때

WebFlux 환경에서 `CompletableFuture`를 사용할 수도 있지만, blocking I/O를 `CompletableFuture.supplyAsync`로 감싸는 방식은 신중해야 한다.

- reactive chain의 backpressure와 별개 executor queue가 생긴다
- context propagation이 더 복잡해진다
- event loop thread를 막으면 치명적이다
- Mono/Flux와 CompletionStage 변환 경계가 많아지면 디버깅이 어려워진다

WebFlux에서는 가능하면 reactive client와 reactive operator를 일관되게 쓰는 편이 낫다. 단발성 외부 라이브러리 bridge 정도에만 `CompletableFuture`를 제한하는 것이 안전하다.

---

## 심화 6: 단계적 도입 전략

이미 동기 코드로 운영 중인 서비스를 한 번에 `CompletableFuture` 체인으로 바꾸면 위험하다. 성능 개선보다 장애 분석 비용이 먼저 늘 수 있다.

### 1단계: 호출 지도를 그린다

먼저 API 하나를 골라 호출 지도를 만든다.

```text
ProductDetail API
 ├─ product service       required, p95 80ms, p99 200ms
 ├─ seller service        required, p95 60ms, p99 180ms, depends on product
 ├─ stock service         required, p95 40ms, p99 120ms
 ├─ coupon service        optional, p95 100ms, p99 400ms
 ├─ recommendation        optional, p95 120ms, p99 600ms
 └─ review summary        optional, p95 90ms, p99 300ms
```

여기서 의존 관계와 필수 여부를 표시한다. 이 작업 없이 코드를 바꾸면 단순히 `supplyAsync`가 흩어진다.

### 2단계: 선택 기능부터 격리한다

처음부터 필수 경로를 비동기화하기보다 선택 section을 분리하는 것이 안전하다.

- 추천
- 쿠폰
- 리뷰 요약
- 배지
- 개인화 문구

이런 기능은 실패 시 degraded 응답으로 처리할 수 있어 비동기 도입 리스크가 낮다.

### 3단계: executor와 metric을 먼저 배포한다

코드 조합을 바꾸기 전에 executor metric과 외부 호출 latency metric을 먼저 배포하는 편이 좋다. 그래야 전후 비교가 가능하다.

비교 지표는 다음이다.

- API p50/p95/p99 latency
- downstream별 p95/p99 latency
- executor active/queue/rejection
- timeout count
- fallback count
- error rate
- heap/GC 변화

성공 기준도 미리 정해야 한다.

```text
목표:
- ProductDetail p95 900ms → 550ms 이하
- p99 2,000ms → 1,200ms 이하
- fallback 비율 1% 미만
- product executor rejection 0.1% 미만
- downstream 5xx 증가 없음
```

목표 없이 “빨라졌는지 느낌으로 확인”하면 운영 개선인지 운인지 알 수 없다.

### 4단계: kill switch를 둔다

비동기 fan-out은 다운스트림 부하를 늘릴 수 있다. 배포 후 문제가 생기면 빠르게 끌 수 있어야 한다.

- feature flag로 추천 비동기 호출 비활성화
- optional section timeout을 더 짧게 조정
- executor max pool size를 낮춤
- fallback을 강제로 반환
- 특정 downstream 호출 차단

비동기 도입의 실패는 대개 코드 bug보다 운영 제어 부재에서 커진다.

---

## 장애 시나리오별 대응

### 시나리오 1: 추천 API가 느려져 상품 상세 전체가 느려진다

증상은 이렇다.

- ProductDetail p95/p99 증가
- recommendation executor active=max
- queue 증가
- fallback은 거의 없음
- timeout count 낮음

해석은 추천 API timeout이 너무 길거나 fallback 경계가 잘못된 것이다. 선택 기능인데 전체 응답을 붙잡고 있을 가능성이 높다.

대응은 다음이다.

1. 추천 stage timeout을 사용자 영향 기준으로 줄인다
2. timeout 시 degraded section으로 전환한다
3. recommendation executor queue를 줄인다
4. fallback count와 degraded response count를 알림에 포함한다

### 시나리오 2: 공용 풀 포화로 unrelated API까지 느려진다

증상은 이렇다.

- 여러 API가 동시에 느려진다
- 특정 외부 API 장애와 시간이 겹친다
- thread dump에 `ForkJoinPool.commonPool-worker`가 blocking I/O에 묶여 있다

원인은 `supplyAsync`에서 executor를 생략한 코드일 가능성이 높다.

대응은 다음이다.

1. `CompletableFuture.supplyAsync` 호출부를 검색한다
2. executor 없는 호출을 분류한다
3. blocking I/O는 전용 executor로 이동한다
4. 공용 풀 사용을 정적 분석 또는 코드 리뷰 규칙으로 막는다

### 시나리오 3: timeout은 발생하는데 downstream 트래픽이 줄지 않는다

증상은 이렇다.

- 애플리케이션에서는 timeout 응답 증가
- downstream은 계속 높은 요청 수와 connection 점유
- executor active가 오래 유지됨

해석은 future timeout만 걸었고 실제 client request timeout/cancel이 약하다는 뜻이다.

대응은 다음이다.

1. HTTP client connect/read/request timeout 확인
2. DB query timeout 확인
3. SDK가 cancellation을 지원하는지 확인
4. future timeout과 client timeout을 deadline 기반으로 맞춘다
5. executor queue wait time을 metric으로 추가한다

### 시나리오 4: fallback 때문에 장애가 늦게 발견된다

증상은 이렇다.

- API status는 200이 많다
- 사용자 화면 일부가 비어 있다
- 매출 또는 전환율이 떨어진다
- error rate 알림은 조용하다

원인은 fallback/degraded 상태를 성공으로만 집계했기 때문이다.

대응은 다음이다.

1. fallback count를 별도 metric으로 분리한다
2. section별 degraded 비율 dashboard를 만든다
3. business KPI와 degraded 비율을 함께 본다
4. fallback이 일정 비율을 넘으면 warning alert를 울린다

### 시나리오 5: 배포 후 thread 수와 memory가 증가한다

증상은 이렇다.

- executor가 여러 개 생겼다
- 각 executor max size가 크다
- queue에 큰 request object가 쌓인다
- heap 사용량과 GC pause가 증가한다

해석은 executor isolation을 만들었지만 총량 제어가 부족한 상태다.

대응은 다음이다.

1. executor별 max thread와 queue 총합을 계산한다
2. queue에 들어가는 task가 큰 객체를 capture하지 않게 한다
3. optional 작업의 queue를 줄인다
4. request-scoped context를 필요 이상으로 복사하지 않는다
5. heap dump로 queue retained object를 확인한다

### 시나리오 6: 간헐적으로 trace id가 사라진다

증상은 이렇다.

- controller 로그에는 trace id가 있다
- 외부 호출 로그에는 trace id가 없다
- 일부 stage에서만 사라진다

원인은 executor 경계에서 MDC 또는 tracing context가 전파되지 않은 것이다.

대응은 다음이다.

1. 모든 custom executor가 context-aware wrapper를 쓰는지 확인한다
2. `thenApplyAsync`에 넘기는 executor도 동일한 wrapper인지 확인한다
3. library callback thread에서 context가 복원되는지 확인한다
4. stage별 `whenComplete` 로그에 trace id를 검증한다

---

## PR 리뷰 예시: 위험한 코드에서 운영 가능한 코드로

### 변경 전

```java
public ProductPage getPage(String productId, String userId) {
    CompletableFuture<Product> product = CompletableFuture.supplyAsync(() -> productClient.get(productId));
    CompletableFuture<Coupon> coupon = CompletableFuture.supplyAsync(() -> couponClient.get(userId));
    CompletableFuture<Review> review = CompletableFuture.supplyAsync(() -> reviewClient.get(productId));

    return ProductPage.of(
            product.join(),
            coupon.exceptionally(ex -> Coupon.empty()).join(),
            review.exceptionally(ex -> Review.empty()).join()
    );
}
```

문제는 많다.

- executor를 생략해 common pool을 쓴다
- stage별 timeout이 없다
- coupon/review fallback metric이 없다
- `exceptionally(...).join()` 위치가 어색하다
- product 실패와 optional 실패 정책이 섞여 있다
- 전체 request budget이 없다
- root cause mapping이 없다

### 변경 후

```java
public CompletionStage<ProductPage> getPageAsync(String productId, String userId, Deadline deadline) {
    CompletionStage<Product> product = productGateway.get(productId, deadline)
            .orTimeout(minMillis(deadline.remaining(), 250), TimeUnit.MILLISECONDS);

    CompletionStage<SectionResult<Coupon>> coupon = couponGateway.get(userId, productId, deadline)
            .completeOnTimeout(Coupon.empty(), minMillis(deadline.remaining(), 120), TimeUnit.MILLISECONDS)
            .handle((value, ex) -> section("coupon", value, ex));

    CompletionStage<SectionResult<Review>> review = reviewGateway.get(productId, deadline)
            .completeOnTimeout(Review.empty(), minMillis(deadline.remaining(), 150), TimeUnit.MILLISECONDS)
            .handle((value, ex) -> section("review", value, ex));

    return product
            .thenCombine(coupon, ProductPageDraft::withCoupon)
            .thenCombine(review, ProductPageDraft::withReview)
            .thenApply(ProductPageDraft::build)
            .whenComplete((value, ex) -> recordProductPageMetrics(value, ex));
}
```

controller에서는 마지막에만 기다린다.

```java
public ProductPage getPage(String productId, String userId) {
    Deadline deadline = Deadline.after(Duration.ofMillis(700));
    try {
        return productPageService.getPageAsync(productId, userId, deadline)
                .toCompletableFuture()
                .orTimeout(deadline.remaining().toMillis(), TimeUnit.MILLISECONDS)
                .join();
    } catch (CompletionException ex) {
        throw apiExceptionMapper.map(unwrap(ex));
    }
}
```

이 코드도 완벽한 정답은 아니다. 하지만 최소한 운영 질문에 답할 수 있다.

- 어떤 호출이 필수인가?
- 어떤 호출이 선택인가?
- timeout은 얼마인가?
- fallback은 어디서 일어나는가?
- executor는 gateway가 책임지는가?
- metric은 어디서 남기는가?
- 동기화는 어디서 하는가?

---

## 성능 최적화보다 먼저 지켜야 할 원칙

`CompletableFuture`를 쓰면 병렬화로 latency가 줄어들 수 있다. 하지만 성능 개선은 안정성 설계 위에서만 의미가 있다.

우선순위는 다음이어야 한다.

1. 정합성
2. 장애 격리
3. timeout budget
4. 관측성
5. 제한된 병렬화
6. 최적화

이 순서를 뒤집으면 흔히 이런 코드가 나온다.

```java
// 빠르게 만들려고 했지만 운영 정책이 사라진 코드
return CompletableFuture.allOf(a, b, c, d, e)
        .thenApply(v -> merge(a.join(), b.join(), c.join(), d.join(), e.join()))
        .exceptionally(ex -> defaultResponse());
```

겉으로는 병렬이다. 하지만 필수/선택 구분도, timeout도, 원인 추적도, fallback 의미도 사라졌다.

반대로 좋은 코드는 조금 길 수 있다.

- stage 이름이 있다
- executor 경계가 있다
- timeout이 있다
- 실패 정책이 있다
- metric이 있다
- 마지막 join 위치가 명확하다

운영 코드는 짧은 체인보다 **의도가 남는 구조**가 더 중요하다.


---

## 안티패턴 카탈로그: 코드에서 바로 찾아야 할 냄새들

`CompletableFuture` 문제는 장애가 난 뒤에야 보이는 경우가 많다. 그래서 코드 리뷰에서 냄새를 먼저 잡는 것이 중요하다.

### 안티패턴 1: executor 없는 `supplyAsync`

```java
CompletableFuture.supplyAsync(() -> externalClient.call());
```

운영 코드에서 이 한 줄은 경고 신호다. blocking I/O인지, CPU 계산인지, library callback인지 아무 정보가 없다. 기본 공용 풀을 쓰겠다는 정책인데, 대부분의 경우 의도적으로 결정한 정책이 아니다.

개선은 단순하다.

```java
CompletableFuture.supplyAsync(() -> externalClient.call(), externalClientExecutor);
```

그리고 executor 이름은 thread name에 드러나야 한다. 장애 시 thread dump에서 `pool-13-thread-7`만 보이면 원인 파악이 늦다.

### 안티패턴 2: `thenApply` 안의 외부 호출

```java
userStage.thenApply(user -> paymentClient.getPaymentMethods(user.id()));
```

이 코드는 변환처럼 보이지만 실제로는 외부 I/O다. 이전 stage를 완료한 thread가 payment 호출까지 떠안는다.

개선한다.

```java
userStage.thenCompose(user -> paymentGateway.getPaymentMethods(user.id()));
```

또는 반드시 동기 client를 감싸야 한다면 gateway 내부에서 executor를 명시한다.

### 안티패턴 3: 마지막 `exceptionally`로 모든 실패를 덮기

```java
return buildDashboard()
        .exceptionally(ex -> Dashboard.empty());
```

이 코드는 인증 실패, 필수 데이터 실패, 버그, timeout을 모두 빈 대시보드로 바꾼다. 사용자에게는 친절해 보이지만 운영에서는 위험하다.

fallback은 필요한 stage에만 좁게 붙인다.

```java
CompletionStage<SectionResult<Recommendation>> recommendation = recommendationStage
        .handle((value, ex) -> toOptionalSection("recommendation", value, ex));
```

### 안티패턴 4: `allOf` 후 무조건 `join`

```java
CompletableFuture.allOf(a, b, c).join();
return merge(a.join(), b.join(), c.join());
```

필수 작업만 있다면 가능하다. 하지만 선택 작업이 섞이면 어떤 실패가 전체 실패인지 불분명하다. `a`, `b`, `c`의 의미가 타입과 변수명에만 의존한다.

필수와 선택을 분리하거나, 결과 wrapper를 사용한다.

### 안티패턴 5: `get()`을 여러 계층에서 호출

```java
// repository-like gateway
return future.get();

// service
return otherFuture.get();

// controller
return finalFuture.get();
```

여러 계층에서 blocking하면 timeout budget이 분산되고 deadlock 추적이 어려워진다. 가능하면 비동기 타입을 유지하다가 시스템 경계에서 한 번만 동기화한다.

### 안티패턴 6: timeout 없는 optional 호출

```java
CompletionStage<Recommendation> recommendation = recommendationGateway.get(userId);
```

선택 기능이라면 더더욱 timeout이 짧아야 한다. 선택 기능이 전체 API를 붙잡으면 사용자 경험이 나빠진다.

```java
CompletionStage<Recommendation> recommendation = recommendationGateway.get(userId)
        .completeOnTimeout(Recommendation.empty(), 120, TimeUnit.MILLISECONDS);
```

단, fallback metric은 필수다.

### 안티패턴 7: timeout 숫자만 있고 이유가 없음

```java
.orTimeout(347, TimeUnit.MILLISECONDS)
```

왜 347ms인가? 상위 budget에서 나온 숫자인가? p95 기반인가? downstream SLA인가? 이유 없는 timeout은 시간이 지나면 아무도 고칠 수 없는 마법 숫자가 된다.

코드 근처에 정책 이름을 두는 편이 낫다.

```java
private static final Duration RECOMMENDATION_OPTIONAL_BUDGET = Duration.ofMillis(120);
```

### 안티패턴 8: 테스트에서 실패 경로가 없음

성공 테스트만 있는 비동기 코드는 거의 항상 불완전하다.

최소한 다음 테스트가 필요하다.

- 필수 stage 실패 시 전체 실패
- 선택 stage 실패 시 degraded 응답
- 선택 stage timeout 시 fallback
- 예외 root cause mapping
- 중간 stage가 이미 완료된 경우
- 느린 stage가 나중에 완료되는 경우

### 안티패턴 9: context capture에서 큰 객체를 잡아 둠

비동기 lambda는 주변 변수를 capture한다.

```java
CompletableFuture.supplyAsync(() -> externalClient.call(bigRequestContext), executor);
```

queue에 오래 쌓이면 `bigRequestContext` 전체가 heap에 유지된다. 필요한 값만 추출해서 넘기는 편이 좋다.

```java
String userId = context.userId();
String traceId = context.traceId();
CompletableFuture.supplyAsync(() -> externalClient.call(userId, traceId), executor);
```

### 안티패턴 10: retry를 stage마다 중첩

```java
serviceA.call().exceptionallyCompose(ex -> serviceA.call())
        .thenCombine(serviceB.call().exceptionallyCompose(ex -> serviceB.call()), this::merge);
```

각 stage가 독립적으로 retry하면 전체 요청의 시도 수가 폭발할 수 있다. retry는 timeout budget, idempotency, rate limit, circuit breaker와 함께 정책화해야 한다.

### 안티패턴 11: fire-and-forget

```java
CompletableFuture.runAsync(() -> auditClient.send(event), executor);
return response;
```

이 코드는 실패를 잃는다. 애플리케이션 종료 시 작업이 유실될 수 있고, executor queue가 쌓여도 호출자는 모른다.

감사, 결제, 알림처럼 의미 있는 side effect는 message queue나 outbox로 내구성을 확보하는 편이 낫다. 정말 best-effort라면 실패 metric과 bounded executor가 있어야 한다.

### 안티패턴 12: `CompletableFuture`를 public DTO 필드로 노출

```java
public record ProductPage(
        Product product,
        CompletableFuture<Recommendation> recommendation
) {}
```

응답 모델에 future가 들어가면 완료 책임과 직렬화 책임이 흐려진다. 비동기 조합은 service 내부에서 끝내고, 외부에는 완료된 결과 또는 명시적 section 상태를 전달하는 편이 좋다.

---

## 실무 의사결정 매트릭스

아래 매트릭스는 `CompletableFuture`를 쓸지 말지 판단할 때 유용하다.

| 상황 | 권장 접근 | 이유 |
| --- | --- | --- |
| 독립 외부 API 3~5개 조합 | CompletableFuture | fan-out/fan-in 표현이 간단함 |
| 요청마다 수십 개 이상의 동적 작업 | 제한된 executor + bulkhead + collect helper | 무제한 fan-out 방지 |
| CPU heavy 계산 | 전용 CPU executor 또는 batch 처리 | I/O executor 오염 방지 |
| 긴 stream 처리 | Reactive Streams, Kafka, Flink 등 | backpressure 필요 |
| 기존 blocking MVC를 높은 동시성으로 확장 | Virtual Threads 검토 | 코드 단순성 유지 가능 |
| callback SDK bridge | CompletableFuture wrapper | completion을 직접 제어해야 함 |
| transaction 이후 side effect | Outbox/message queue | rollback과 side effect 분리 |
| 사용자가 기다리지 않아도 되는 작업 | Queue 기반 비동기 처리 | fire-and-forget 손실 방지 |

중요한 것은 “기술 선택”보다 “실패 의미”다. 같은 추천 호출이라도 화면 부가 영역이면 fallback 가능하지만, 가격 계산에 들어가는 추천 할인이라면 필수일 수 있다.

---

## 면접 질문처럼 스스로 점검하기

다음 질문에 답해보면 `CompletableFuture` 이해도가 꽤 정확히 드러난다.

### Q1. `thenApplyAsync`를 쓰면 항상 별도 thread에서 실행되는가?

항상이라고 말하면 위험하다. 일반적으로 executor에 작업을 제출하지만, 어떤 executor를 쓰는지에 따라 실행 방식은 달라진다. 직접 executor를 넘기지 않으면 기본 executor가 사용된다. 중요한 것은 `Async`가 “안전한 비동기”가 아니라 “후속 작업 실행을 executor에 위임한다”는 점이다.

### Q2. `orTimeout`은 실제 HTTP 요청을 끊는가?

그 자체로는 보장하지 않는다. future를 timeout 예외로 완료할 뿐, 이미 실행 중인 blocking 호출이 중단되는지는 HTTP client와 작업 구현에 달려 있다. 실제 자원 회수를 위해 client timeout이 필요하다.

### Q3. `exceptionally`와 `whenComplete`의 가장 큰 차이는 무엇인가?

`exceptionally`는 실패를 값으로 복구해 이후 흐름을 정상화할 수 있다. `whenComplete`는 관찰 목적이며 결과 의미를 바꾸기 위한 도구가 아니다. 장애를 숨기지 않고 metric/log만 남기려면 `whenComplete`가 더 적합하다.

### Q4. `allOf`는 하나가 실패하면 나머지를 취소하는가?

자동으로 모든 작업을 취소한다고 기대하면 안 된다. 이미 시작된 작업은 계속 실행될 수 있다. 실패 시 나머지를 어떻게 처리할지는 별도 설계가 필요하다.

### Q5. `join()`과 `get()` 중 무엇을 써야 하는가?

둘 다 blocking이다. `get()`은 checked exception인 `ExecutionException`, `InterruptedException`을 다루고, `join()`은 unchecked `CompletionException`을 던진다. 웹 계층에서는 `join()`을 쓰더라도 root cause mapping을 반드시 해야 한다. 더 중요한 기준은 어떤 메서드를 쓰느냐보다 “어디에서 blocking하느냐”다.

### Q6. `CompletableFuture`는 backpressure를 제공하는가?

아니다. task를 만들고 executor queue에 넣는 것은 쉽지만, downstream 속도에 맞춰 유입을 자동 조절하지 않는다. backpressure가 필요한 stream 문제에는 reactive streams나 messaging 시스템이 더 적합하다.

### Q7. default executor를 쓰면 왜 문제가 될 수 있는가?

공용 풀은 애플리케이션 전체에서 공유될 수 있다. blocking I/O가 공용 풀을 점유하면 unrelated 기능까지 지연된다. 장애 격리와 관측을 위해 목적별 executor를 쓰는 편이 안전하다.

### Q8. optional section 실패를 빈 배열로 내려도 되는가?

비즈니스적으로 안전할 수는 있다. 하지만 빈 배열이 “원래 데이터 없음”인지 “조회 실패”인지 구분되지 않으면 운영 분석이 어렵다. 내부 result type과 metric에서는 구분해야 한다.

---

## 더 깊은 예시: deadline, fallback, metric을 포함한 작은 유틸리티

아래 코드는 실서비스에 그대로 붙이라는 뜻이 아니다. 어떤 책임을 분리해야 하는지 보여주는 예시다.

```java
public final class AsyncStageSupport {
    private final MeterRegistry meterRegistry;

    public AsyncStageSupport(MeterRegistry meterRegistry) {
        this.meterRegistry = meterRegistry;
    }

    public <T> CompletionStage<T> required(
            String name,
            CompletionStage<T> stage,
            Duration timeout
    ) {
        long start = System.nanoTime();
        return stage.orTimeout(timeout.toMillis(), TimeUnit.MILLISECONDS)
                .whenComplete((value, ex) -> record(name, "required", start, ex));
    }

    public <T> CompletionStage<SectionResult<T>> optional(
            String name,
            CompletionStage<T> stage,
            T fallback,
            Duration timeout
    ) {
        long start = System.nanoTime();
        return stage.completeOnTimeout(fallback, timeout.toMillis(), TimeUnit.MILLISECONDS)
                .handle((value, ex) -> {
                    record(name, "optional", start, ex);
                    if (ex == null) {
                        return SectionResult.success(name, value);
                    }
                    Throwable cause = unwrap(ex);
                    meterRegistry.counter("async.stage.degraded", "stage", name, "type", cause.getClass().getSimpleName())
                            .increment();
                    return SectionResult.degraded(name, cause);
                });
    }

    private void record(String name, String kind, long start, Throwable ex) {
        long elapsed = System.nanoTime() - start;
        meterRegistry.timer("async.stage.latency", "stage", name, "kind", kind)
                .record(elapsed, TimeUnit.NANOSECONDS);
        if (ex != null) {
            Throwable cause = unwrap(ex);
            meterRegistry.counter("async.stage.error", "stage", name, "type", cause.getClass().getSimpleName())
                    .increment();
        }
    }
}
```

이런 support class를 만들 때의 주의점은 다음이다.

- stage 이름을 userId, productId처럼 high-cardinality 값으로 만들지 않는다
- fallback을 무조건 성공 metric으로만 기록하지 않는다
- required 실패를 optional처럼 바꾸지 않는다
- timeout duration이 0 이하가 될 때 즉시 실패할지 fallback할지 정한다
- 테스트에서 metric 호출을 검증하기보다 결과 정책을 우선 검증한다

---

## 더 깊은 예시: fan-out 개수를 제한하기

사용자에게 노출할 추천 상품 20개에 대해 각각 가격, 재고, 배송 정보를 비동기로 조회한다고 하자. 단순히 20 × 3 = 60개 future를 한 번에 만들면 순간 부하가 커진다.

```java
List<CompletionStage<ItemCard>> cards = items.stream()
        .map(item -> buildCardAsync(item))
        .toList();
```

트래픽이 100 RPS라면 이 API 하나가 초당 6,000개 downstream 호출을 만들 수 있다.

이럴 때는 fan-out 자체를 제한해야 한다.

```java
public <T, R> CompletionStage<List<R>> mapLimited(
        List<T> inputs,
        int concurrency,
        Function<T, CompletionStage<R>> mapper
) {
    Semaphore semaphore = new Semaphore(concurrency);

    List<CompletionStage<R>> stages = inputs.stream()
            .map(input -> CompletableFuture.runAsync(() -> acquire(semaphore))
                    .thenCompose(ignored -> mapper.apply(input))
                    .whenComplete((value, ex) -> semaphore.release()))
            .toList();

    return sequence(stages);
}
```

위 코드는 개념 예시다. 실제 구현에서는 acquire 실패, executor 선택, interrupt 처리, timeout을 더 꼼꼼히 다뤄야 한다.

핵심은 이렇다.

- `CompletableFuture`를 많이 만든다고 자동으로 안전한 병렬 처리가 되지 않는다
- 요청 내부 fan-out에도 제한이 필요하다
- downstream별 전역 제한과 요청별 지역 제한은 별개로 봐야 한다

요청별 제한이 없으면 단일 heavy request가 executor를 독점할 수 있다. 전역 제한이 없으면 여러 요청이 합쳐져 downstream을 무너뜨릴 수 있다.

---

## 더 깊은 예시: 순차 의존성과 병렬 의존성을 섞어 읽기

복잡한 API에서는 모든 작업이 독립적이지도, 모두 순차적이지도 않다.

예를 들어 여행 예약 API를 보자.

```text
사용자 조회(required)
 ├─ 멤버십 등급 조회(required, user 필요)
 ├─ 쿠폰 조회(optional, user 필요)
 └─ 최근 검색 기록(optional, user 필요)

상품 조회(required)
 ├─ 좌석 재고 조회(required, product 필요)
 └─ 추천 보험 조회(optional, product 필요)

가격 계산(required, user grade + product + stock 필요)
```

이런 구조를 단순 chain으로 쓰면 너무 깊어진다. 먼저 큰 가지를 나눈다.

```java
CompletionStage<User> user = userGateway.getUser(userId);
CompletionStage<Product> product = productGateway.getProduct(productId);

CompletionStage<UserContext> userContext = user.thenCompose(u -> {
    CompletionStage<Grade> grade = gradeGateway.getGrade(u.gradeId());
    CompletionStage<SectionResult<Coupon>> coupon = optionalCoupon(u.id(), productId);
    CompletionStage<SectionResult<SearchHistory>> history = optionalHistory(u.id());

    return grade
            .thenCombine(coupon, UserContextDraft::withCoupon)
            .thenCombine(history, UserContextDraft::withHistory)
            .thenApply(draft -> draft.withUser(u).build());
});

CompletionStage<ProductContext> productContext = product.thenCompose(p -> {
    CompletionStage<Stock> stock = stockGateway.getStock(p.id());
    CompletionStage<SectionResult<Insurance>> insurance = optionalInsurance(p.id());

    return stock
            .thenCombine(insurance, ProductContextDraft::withInsurance)
            .thenApply(draft -> draft.withProduct(p).build());
});

CompletionStage<ReservationPreview> preview = userContext
        .thenCombine(productContext, (uc, pc) -> priceService.calculate(uc, pc));
```

이 구조의 핵심은 “계층화”다.

- user branch
- product branch
- final price branch

stage 체인을 무작정 한 줄로 쓰지 말고 도메인 단위 중간 context를 만들면 읽기 쉬워진다.

---

## 운영 문서에 남겨야 할 내용

`CompletableFuture` 기반 API를 운영한다면 코드만으로 충분하지 않다. 짧은 운영 문서가 있어야 한다.

문서에는 다음이 들어가면 좋다.

### API timeout budget

```text
ProductDetail API 목표 p95: 600ms
전체 application timeout: 800ms
required product: 250ms
required seller: 200ms
required stock: 150ms
optional coupon: 120ms
optional recommendation: 120ms
optional review: 150ms
```

### executor 정책

```text
product-client-executor
- core: 30
- max: 80
- queue: 300
- rejection: AbortPolicy
- owner: commerce-platform
- dashboard: link

recommendation-client-executor
- core: 10
- max: 30
- queue: 100
- rejection: fallback
- owner: personalization
```

### fallback 정책

```text
coupon failure: empty coupon section, degraded metric
recommendation timeout: empty recommendation, degraded metric
review failure: hide review summary, degraded metric
product failure: API 502/504 mapping
seller failure: API 502/504 mapping
stock failure: API 503 if unknown, sold-out only when confirmed
```

### 알림 기준

```text
required downstream error rate > 2% for 5m: page
optional degraded ratio > 10% for 10m: warning
executor rejection > 0.5% for 5m: page if required, warning if optional
ProductDetail p99 > 1.5s for 10m: page
```

이 문서가 있으면 새 팀원이 코드를 바꾸기 전에 운영 의도를 이해할 수 있다. 반대로 이런 문서가 없다면 timeout 숫자와 fallback 정책은 시간이 지날수록 의미를 잃는다.

---

## 마이그레이션 후 회고에서 봐야 할 지표

비동기화 배포가 끝났다고 작업이 끝나는 것은 아니다. 최소 며칠은 전후 지표를 비교해야 한다.

### latency

- API p50, p95, p99
- stage별 p95, p99
- queue wait time
- downstream latency 변화

p50만 좋아지고 p99가 나빠졌다면 병렬화로 평균은 줄었지만 tail risk를 키운 것이다.

### error와 degraded

- 전체 5xx
- required stage failure
- optional degraded ratio
- timeout count
- executor rejection count

전체 5xx가 줄어도 degraded가 크게 늘었다면 사용자 경험이 실제로 좋아졌는지 따져봐야 한다.

### resource

- thread count
- heap usage
- GC pause
- connection pool usage
- CPU utilization

비동기화는 latency를 줄이는 대신 동시 실행 수와 메모리 사용을 늘릴 수 있다. 특히 queue에 쌓인 lambda가 큰 객체를 잡고 있으면 heap이 예상보다 늘어난다.

### downstream 영향

- downstream RPS
- downstream error rate
- downstream p99
- rate limit 발생

내 API가 빨라졌지만 downstream 장애가 늘었다면 성공이 아니다. 병렬화는 호출 압력을 재배치한다.

---

## 최종 판단 기준

`CompletableFuture`를 잘 썼는지 판단하는 기준은 체인이 멋진지가 아니다.

다음 문장을 채울 수 있어야 한다.

```text
이 API는 전체 ____ms budget 안에서 동작한다.
필수 stage는 ____이고, 선택 stage는 ____이다.
각 stage는 ____ executor에서 실행된다.
각 외부 호출의 client timeout은 ____이다.
선택 stage 실패는 ____ 응답으로 바뀌며 ____ metric으로 집계된다.
필수 stage 실패는 ____ 예외로 매핑된다.
executor 포화 시 ____ 정책으로 실패하거나 제한한다.
trace context는 ____ 방식으로 전파된다.
마지막 blocking 지점은 ____이다.
```

이 문장을 못 채우면 코드는 아직 운영 가능한 수준이 아니다. 반대로 이 문장을 채울 수 있다면, 구현 스타일이 `CompletableFuture`든 virtual thread든 reactive든 중요한 운영 책임은 이미 잡혀 있다.


---

## 짧은 결론이 아니라 운영 기준으로 다시 요약하기

이 글의 내용을 실제 팀 규칙으로 줄이면 다음과 같다.

### 규칙 1: 비동기화 전에 의존 그래프를 먼저 그린다

코드를 쓰기 전에 최소한 아래를 적는다.

```text
A는 필수인가?
B는 A 결과가 필요한가?
C는 실패해도 되는가?
D는 몇 ms까지만 기다릴 것인가?
E는 어떤 executor에서 실행될 것인가?
```

이 표 없이 작성한 `CompletableFuture` 코드는 대부분 나중에 다시 풀어야 한다.

### 규칙 2: executor는 성능 옵션이 아니라 장애 격리 장치다

executor 이름, 크기, queue, rejection 정책은 운영 정책이다. 코드에 executor가 보이지 않거나 metric이 없다면, 비동기 작업은 이미 관측 불가능한 영역으로 들어간 것이다.

### 규칙 3: timeout은 숫자가 아니라 예산이다

각 stage timeout은 전체 request budget에서 나온다. timeout 숫자가 독립적으로 흩어져 있으면 전체 응답 시간은 누구도 책임지지 않는다.

### 규칙 4: fallback은 성공이 아니다

fallback은 사용자 경험을 지키는 장치일 수 있지만, 운영 지표에서는 실패 또는 degraded로 남아야 한다. 빈 배열, 기본 객체, cached value로 바꿨다면 반드시 그 사실을 세야 한다.

### 규칙 5: 마지막까지 비동기 타입을 유지한다

중간 `join()`은 병렬성을 깨고 예외 의미를 흐린다. 가능한 마지막 adapter 또는 controller 경계에서 한 번만 기다린다.

### 규칙 6: optional과 required를 같은 체인에 섞지 않는다

필수 stage는 실패해야 한다. 선택 stage는 degraded될 수 있다. 이 둘을 마지막 `exceptionally` 하나로 처리하면 장애 정책이 사라진다.

### 규칙 7: context propagation은 부가기능이 아니다

trace id가 끊기는 순간 장애 분석 시간이 길어진다. executor를 하나 만들 때마다 MDC, tracing, security context 전파 여부를 같이 결정한다.

### 규칙 8: 테스트는 시간과 실패를 포함해야 한다

비동기 코드는 성공 경로보다 timeout과 partial failure에서 더 자주 망가진다. 이미 완료된 future만 mock으로 반환하는 테스트는 충분하지 않다.

### 규칙 9: fan-out은 제한되어야 한다

한 요청 안에서 future를 몇 개 만들 수 있는지, 여러 요청이 동시에 들어올 때 downstream으로 몇 개의 호출이 나가는지 계산해야 한다. 병렬화는 무료가 아니다.

### 규칙 10: 모르면 동기 코드가 낫다

비동기 코드가 운영 정책을 숨긴다면 차라리 명확한 동기 코드가 낫다. `CompletableFuture`는 복잡도를 감당할 이유가 있을 때만 써야 한다.

---

## 팀 컨벤션 예시

실제 팀이라면 다음 정도의 컨벤션을 문서화해 둘 수 있다.

```text
1. 운영 코드에서 CompletableFuture.supplyAsync는 반드시 executor를 명시한다.
2. commonPool 사용은 테스트 또는 순수 CPU toy task로 제한한다.
3. 외부 I/O는 gateway 계층에서 CompletionStage로 감싼다.
4. service 계층은 조합 정책을 표현하고 executor 생성은 하지 않는다.
5. controller 계층은 마지막 blocking 지점만 담당한다.
6. optional stage는 SectionResult로 감싸 degraded 여부를 보존한다.
7. required stage는 fallback으로 숨기지 않는다.
8. 모든 stage timeout은 API budget 문서에서 나온 상수만 사용한다.
9. fallback, timeout, rejection은 모두 metric으로 기록한다.
10. executor별 dashboard 없이 새 비동기 fan-out을 배포하지 않는다.
```

이 컨벤션은 다소 엄격해 보이지만, 장애가 난 뒤에 원인을 찾는 비용보다 훨씬 싸다.

---

## 마지막 사례: 코드가 짧아지는 방향이 항상 좋은 방향은 아니다

아래 코드는 짧다.

```java
return CompletableFuture.allOf(user, product, coupon, review)
        .thenApply(v -> Response.of(user.join(), product.join(), coupon.join(), review.join()))
        .exceptionally(ex -> Response.empty());
```

하지만 운영 질문에는 거의 답하지 못한다.

- 어떤 stage가 필수인가?
- 어떤 stage가 선택인가?
- timeout은 어디 있는가?
- fallback은 왜 전체 empty인가?
- 어떤 executor에서 실행되는가?
- 어떤 metric이 남는가?
- 어떤 예외가 root cause인가?

반대로 아래 코드는 길다.

```java
CompletionStage<User> user = required("user", userGateway.get(userId, deadline), USER_BUDGET);
CompletionStage<Product> product = required("product", productGateway.get(productId, deadline), PRODUCT_BUDGET);
CompletionStage<SectionResult<Coupon>> coupon = optional("coupon", couponGateway.get(userId, productId, deadline), Coupon.empty(), COUPON_BUDGET);
CompletionStage<SectionResult<Review>> review = optional("review", reviewGateway.get(productId, deadline), Review.empty(), REVIEW_BUDGET);

return user
        .thenCombine(product, PageDraft::new)
        .thenCombine(coupon, PageDraft::withCoupon)
        .thenCombine(review, PageDraft::withReview)
        .thenApply(PageDraft::build);
```

하지만 정책이 보인다. 운영 코드는 이쪽이 더 낫다.

`CompletableFuture`의 좋은 사용은 “체인을 얼마나 우아하게 만들었는가”가 아니라, **미래의 장애 상황에서 누가 봐도 어디가 느리고, 어디가 실패했고, 어디까지는 의도된 degraded인지 알 수 있게 만드는 것**이다.


---

## 아주 작은 운영 원칙 하나 더: 이름을 붙이면 책임이 생긴다

비동기 stage에 이름이 없으면 metric도, 로그도, 장애 보고도 흐려진다.

`future1`, `future2`, `all` 같은 이름은 구현 순서만 말한다. `requiredProductStage`, `optionalCouponSection`, `sellerLookupStage` 같은 이름은 실패 의미를 말한다.

운영 중에는 코드 라인보다 이름이 먼저 보인다.

- `async.stage.latency{stage="coupon"}`
- `async.stage.error{stage="seller"}`
- `executor.queue.size{name="recommendation-client"}`
- `dashboard.degraded{section="review"}`

이 이름들이 곧 시스템의 지도다. 좋은 `CompletableFuture` 코드는 stage 이름, executor 이름, metric 이름이 서로 맞물려 있다. 이 셋이 다르면 장애 대응 때 사람은 같은 대상을 세 번 번역해야 한다.

따라서 새 비동기 stage를 추가할 때는 코드와 함께 다음 이름도 같이 정한다.

```text
stage name: recommendation
executor name: recommendation-client-executor
thread prefix: recommendation-client-
metric prefix: external.recommendation
fallback metric: dashboard.section.degraded{section="recommendation"}
owner: personalization
```

이 정도만 해도 운영 난이도가 크게 내려간다. 비동기는 눈에 보이지 않는 흐름을 다루는 기술이기 때문에, 이름을 붙이는 일이 곧 설계의 일부다.

---

## 체크리스트

### 설계 전

- [ ] 이 작업은 정말 비동기 조합이 필요한가, 아니면 단순 동기 코드가 더 명확한가?
- [ ] 독립 호출과 의존 호출을 구분했는가?
- [ ] 필수 데이터와 선택 데이터를 구분했는가?
- [ ] 전체 요청 timeout budget을 먼저 정했는가?
- [ ] fallback이 가능한 기능과 불가능한 기능을 구분했는가?

### 구현 중

- [ ] `supplyAsync`에 명시적 executor를 전달했는가?
- [ ] blocking I/O가 공용 풀에 올라가지 않는가?
- [ ] `thenApply`, `thenCompose`, `thenCombine`을 의도에 맞게 사용했는가?
- [ ] 중간에 `join()` 또는 `get()`을 호출하지 않는가?
- [ ] `orTimeout`과 실제 client timeout을 함께 설정했는가?
- [ ] `exceptionally`가 예외를 조용히 삼키지 않는가?
- [ ] `whenComplete`로 관측만 할 부분과 `handle`로 결과를 바꿀 부분을 구분했는가?
- [ ] `CompletionException`의 root cause를 풀어 로그와 API 예외에 반영하는가?

### 운영 전

- [ ] executor active count, queue size, rejection count를 metric으로 볼 수 있는가?
- [ ] 외부 호출별 latency, timeout, error rate가 보이는가?
- [ ] fallback/degraded response 비율을 별도 dashboard에서 보는가?
- [ ] trace id와 MDC가 비동기 경계에서도 이어지는가?
- [ ] timeout, partial failure, fallback 테스트가 있는가?
- [ ] 다운스트림 장애 시 thread pool과 queue가 어떻게 동작하는지 부하 테스트했는가?

---

## 한 줄 정리

`CompletableFuture`는 비동기를 쉽게 만드는 문법이 아니라, **독립 작업을 안전하게 조합하기 위해 executor·timeout·예외·fallback·관측성의 책임을 명확히 드러내야 하는 운영 설계 도구**다.
