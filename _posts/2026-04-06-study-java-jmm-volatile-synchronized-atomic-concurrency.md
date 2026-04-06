---
layout: post
title: "Java 동시성 실전: JMM, volatile, synchronized, Atomic으로 레이스 컨디션을 구조적으로 줄이는 법"
date: 2026-04-06 11:40:00 +0900
categories: [java]
tags: [study, java, concurrency, jmm, volatile, synchronized, atomic, cas, multithreading, performance]
permalink: /java/2026/04/06/study-java-jmm-volatile-synchronized-atomic-concurrency.html
---

## 배경: 왜 Java 동시성 문제는 로컬 테스트에서는 멀쩡한데 운영에서만 터질까?

Java 백엔드에서 진짜 무서운 버그 중 상당수는 문법 오류가 아니라 **동시성 가정의 붕괴**에서 나온다.

대표적으로 이런 장면이 반복된다.

- 분명 `boolean` 플래그 하나로 워커 종료를 제어했는데 어떤 스레드는 끝까지 종료되지 않는다
- 재고 차감 로직이 부하 테스트에서는 멀쩡했는데 운영 피크 타임에만 음수가 된다
- 캐시 재로딩 코드를 “간단히” 작성했는데 간헐적으로 이전 값이 다시 보인다
- 카운터를 `++`로 올렸을 뿐인데 지표 수치가 실제보다 작게 집계된다
- `ConcurrentHashMap`을 썼는데도 중복 생성, 부분 초기화, 불일치 상태가 발생한다

이런 문제는 공통점이 있다.

> **단일 스레드에서 당연했던 가정이 멀티스레드에서는 더 이상 당연하지 않다.**

중급 이상 개발자에게 중요한 건 단순히 “스레드는 위험하다” 수준이 아니다. 실무에서는 아래 질문에 답할 수 있어야 한다.

- `volatile`은 정확히 무엇을 보장하고 무엇을 절대 보장하지 않는가?
- `synchronized`는 단순 락인가, 아니면 메모리 가시성 도구이기도 한가?
- `AtomicInteger` 같은 원자 클래스는 왜 빠를 때가 있고, 왜 오히려 병목이 될 때가 있는가?
- `ConcurrentHashMap`을 쓰면 동기화 문제가 정말 끝나는가?
- CAS 기반 접근과 락 기반 접근은 어떤 트레이드오프를 가지는가?
- 상태 공유 자체를 줄이는 설계와, 공유 상태를 안전하게 다루는 기술은 어떻게 구분해야 하는가?

오늘 글은 `Thread` 생성법 입문이 아니다. 목표는 **Java Memory Model(JMM) 관점에서 동시성 문제를 읽고, `volatile` / `synchronized` / Atomic 계열을 어떤 상황에서 어떤 기준으로 선택해야 하는지 실무적으로 정리하는 것**이다.

핵심은 일곱 가지다.

1. 동시성 문제는 결국 **가시성(visibility)**, **원자성(atomicity)**, **순서성(ordering)** 문제로 환원된다
2. `volatile`은 가시성과 순서성 일부를 보장하지만 **복합 연산의 원자성은 보장하지 않는다**
3. `synchronized`는 상호 배제뿐 아니라 **happens-before 관계를 형성하는 메모리 동기화 도구**다
4. Atomic 계열은 CAS 기반으로 경쟁을 줄일 수 있지만 **고경합 환경에서 무조건 이기는 것은 아니다**
5. 자료구조 하나를 concurrent 버전으로 바꿨다고 해서 **업무 단위의 정합성까지 자동으로 안전해지지 않는다**
6. 대부분의 실무 문제는 “어떤 키워드를 붙일까?”보다 **공유 상태를 얼마나 줄였는가**에서 절반이 결정된다
7. 좋은 동시성 코드는 기법 자랑이 아니라 **상태 전이 규칙을 명확히 드러내는 코드**다

---

## 먼저 큰 그림: 동시성 문제를 읽는 기준은 세 가지다

실무에서 동시성 버그를 만나면 많은 팀이 곧바로 이런 반응을 보인다.

- 일단 `synchronized` 붙여보자
- `volatile`이면 되지 않나?
- `AtomicInteger`로 바꾸면 해결되지 않나?
- `ConcurrentHashMap`으로 교체하자

문제는 이 접근이 **증상 중심**이라는 점이다. 먼저 문제를 분해해야 한다.

### 1) 가시성(Visibility)

한 스레드가 변경한 값을 다른 스레드가 **언제, 어떤 시점에 볼 수 있는가**의 문제다.

예를 들어 종료 플래그를 생각해보자.

```java
public class Worker implements Runnable {
    private boolean running = true;

    @Override
    public void run() {
        while (running) {
            doWork();
        }
    }

    public void stop() {
        running = false;
    }
}
```

단일 스레드 관점에서는 아무 문제 없어 보인다. 하지만 멀티스레드에서는 `stop()`이 호출되어도 `run()` 쪽 스레드가 변경을 즉시 보지 못할 수 있다. 즉 버그의 본질은 “연산”이 아니라 **값이 보였느냐**다.

### 2) 원자성(Atomicity)

하나의 작업처럼 보이는 코드가 실제로는 여러 단계로 분해되어 중간에 끼어들 수 있는가의 문제다.

```java
count++;
```

이 한 줄은 실제로는 아래처럼 분해된다.

1. 현재 값 읽기
2. 1 더하기
3. 결과 쓰기

스레드 두 개가 동시에 이 작업을 하면 증가분 하나가 사라질 수 있다. 즉 `++`는 원자적이지 않다.

### 3) 순서성(Ordering)

코드 순서대로 썼다고 해서 CPU, JIT, 메모리 모델 관점에서 **다른 스레드가 그 순서로 관찰하는 것까지 보장되지는 않는다**는 문제다.

예를 들어 객체 초기화 후 참조를 공개한다고 믿었는데, 다른 스레드가 일부 필드만 초기화된 상태를 볼 수 있는 문제가 여기에 속한다.

---

## 핵심 개념 1: Java Memory Model(JMM)을 모르면 `volatile`과 `synchronized`를 제대로 쓸 수 없다

JMM은 “자바에서 여러 스레드가 메모리를 어떻게 읽고 쓰는지”에 대한 규칙이다. 여기서 가장 중요한 메시지는 이것이다.

> **한 스레드에서 쓴 값이 다른 스레드에 자동으로 즉시 보인다고 가정하면 안 된다.**

CPU 캐시, 레지스터, 컴파일러 최적화, 명령 재배치가 개입하면서, 우리가 코드만 보고 기대한 세계와 실제 실행 세계가 달라진다.

### happens-before를 실무적으로 이해하기

동시성 코드를 읽을 때 가장 중요한 키워드는 `happens-before`다.

간단히 말하면:

- 어떤 쓰기(write)가
- 어떤 읽기(read)보다 **먼저 발생했다고 규칙상 보장되면**
- 뒤 스레드는 앞 스레드의 결과를 안전하게 관찰할 수 있다

실무에서 자주 쓰는 happens-before 형성 수단은 아래다.

- 한 스레드 내 프로그램 순서
- `synchronized` 블록의 unlock → 이후 같은 monitor에 대한 lock
- `volatile` 변수에 대한 write → 이후 같은 변수에 대한 read
- `Thread.start()` / `Thread.join()`
- `java.util.concurrent`의 고수준 동시성 도구들(`Future`, `BlockingQueue`, `CountDownLatch` 등)

즉 JMM을 모르면 이렇게 오해하기 쉽다.

- “코드가 위에서 아래로 써 있으니 당연히 그 순서대로 보이겠지”
- “primitive 타입이면 원자적이니까 안전하겠지”
- “Concurrent 컬렉션을 썼으니 업무 로직도 안전하겠지”

실제론 그렇지 않다. **어떤 happens-before를 통해 상태를 공개했는지**가 핵심이다.

---

## 핵심 개념 2: `volatile`은 “값을 최신으로 보이게 하는 도구”에 가깝다

`volatile`은 가장 많이 오해되는 키워드다. 흔히 “가벼운 synchronized” 정도로 기억하지만, 실무에서는 더 정확하게 이해해야 한다.

### `volatile`이 보장하는 것

1. **가시성 보장**
   - 한 스레드가 `volatile` 변수에 쓴 값은 다른 스레드가 읽을 때 최신 값을 볼 수 있다
2. **일정 수준의 순서성 보장**
   - 해당 변수 전후의 읽기/쓰기 재배치를 제어해 안전한 공개(safe publication)에 기여한다

예를 들어 종료 플래그는 `volatile`과 잘 맞는 전형적인 사례다.

```java
public class Worker implements Runnable {
    private volatile boolean running = true;

    @Override
    public void run() {
        while (running) {
            doWork();
        }
    }

    public void stop() {
        running = false;
    }
}
```

이 경우 핵심은 `running` 값이 true/false로 **독립적으로 읽히고 쓰이는 단순 상태**라는 점이다.

### `volatile`이 보장하지 않는 것

가장 흔한 오해는 이것이다.

> `volatile`이면 동시성 문제를 해결한다

아니다. `volatile`은 **복합 연산의 원자성**을 보장하지 않는다.

```java
public class Counter {
    private volatile int count = 0;

    public void increment() {
        count++;
    }

    public int get() {
        return count;
    }
}
```

이 코드는 안전하지 않다. `count++`는 여전히 read-modify-write의 3단계이며, 스레드 간 경쟁이 발생하면 값이 유실된다.

즉 `volatile`이 맞는 상황은 대체로 아래다.

- 종료 플래그
- 설정값 스냅샷 참조 교체
- 한 번에 하나의 값만 읽고 쓰는 상태
- 다른 락/동기화와 함께 보조적으로 쓰는 경우

반대로 아래에는 단독으로 쓰면 안 된다.

- 카운터 증가
- `if (x == null) x = ...` 초기화
- 여러 필드가 함께 일관성을 가져야 하는 상태 전이
- “읽고 판단하고 쓰기”가 한 덩어리인 비즈니스 규칙

### `volatile`이 특히 잘 맞는 패턴: immutable snapshot 교체

운영 설정 캐시를 생각해보자.

```java
public class RoutingRuleRegistry {
    private volatile RoutingRules currentRules = RoutingRules.empty();

    public RoutingRules getCurrentRules() {
        return currentRules;
    }

    public void reload(List<Rule> loadedRules) {
        RoutingRules newRules = RoutingRules.from(loadedRules);
        currentRules = newRules;
    }
}
```

여기서 중요한 건 `RoutingRules` 자체를 **불변 객체(immutable object)** 로 설계하는 것이다. 그러면 읽는 쪽은 락 없이 현재 스냅샷 참조만 읽고, 갱신은 새 객체를 만들어 한 번에 교체하면 된다.

이 패턴은 고QPS 읽기, 저빈도 갱신에서 아주 강력하다.

---

## 핵심 개념 3: `synchronized`는 단순 락이 아니라 “임계구역 + 메모리 동기화”다

`synchronized`를 너무 오래된 키워드쯤으로 취급하는 경우가 있다. 하지만 실무에서는 여전히 중요한 기본기다.

### `synchronized`가 하는 일

1. **상호 배제(mutual exclusion)**
   - 같은 monitor를 두고 한 번에 하나의 스레드만 임계구역에 들어간다
2. **메모리 가시성 보장**
   - 한 스레드가 monitor를 빠져나올 때의 write가, 이후 같은 monitor를 획득한 스레드에 보인다

즉 `synchronized`는 단순히 “막는다”가 아니다. **임계구역 전후의 메모리 상태를 정렬한다**.

### 가장 전형적인 사용처: 복합 상태 전이 보호

```java
public class Inventory {
    private int quantity;

    public Inventory(int quantity) {
        this.quantity = quantity;
    }

    public synchronized boolean decrease(int amount) {
        if (amount <= 0) {
            throw new IllegalArgumentException("amount must be positive");
        }

        if (quantity < amount) {
            return false;
        }

        quantity -= amount;
        return true;
    }

    public synchronized int getQuantity() {
        return quantity;
    }
}
```

여기서 중요한 건 `quantity` 하나 때문이 아니다. 실제로 보호해야 하는 것은 아래 상태 전이다.

1. 현재 재고 읽기
2. 충분한지 검증
3. 차감
4. 결과 반환

이것은 하나의 비즈니스 단위다. 따라서 `AtomicInteger`로 일부를 바꾸는 것보다, **업무 의미가 있는 임계구역으로 묶는 것**이 훨씬 명확할 때가 많다.

### `synchronized`의 장점

- 코드 의도가 직관적이다
- 복합 연산을 안전하게 묶기 쉽다
- 메모리 가시성까지 함께 해결한다
- 저~중간 경합 환경에서는 충분히 빠른 경우가 많다

### `synchronized`의 한계

- 긴 임계구역에서는 대기 시간이 커진다
- 락 안에서 I/O, 외부 API 호출, 블로킹 작업을 하면 병목이 심해진다
- 락 순서가 엇갈리면 데드락 위험이 있다
- 읽기 비중이 압도적으로 높고 구조가 단순한 경우에는 과할 수 있다

### 실무 기준: 락 안에서는 “짧고 순수한 상태 변경”만 하라

아래 같은 코드는 위험하다.

```java
public synchronized void processOrder(Order order) {
    reserveStock(order);
    paymentClient.charge(order); // 외부 호출
    orderRepository.save(order); // I/O
    notificationService.send(order); // 또 외부 호출
}
```

이렇게 되면 락을 잡은 채 네트워크, DB, 타 시스템 응답을 기다리게 된다. 동시성 제어가 아니라 **병목 확대기**가 된다.

더 나은 기준은 아래다.

- 락 안: 메모리 상의 핵심 상태 검증/변경
- 락 밖: DB 반영, 메시지 발행, 외부 API 호출

물론 이때는 메모리 상태와 외부 시스템 상태를 어떻게 일관되게 맞출지 별도 설계가 필요하다. 즉 동시성 문제는 종종 트랜잭션/아키텍처 문제와 연결된다.

---

## 핵심 개념 4: Atomic 계열은 “락 없는 마법”이 아니라 CAS 기반 선택지다

`AtomicInteger`, `AtomicLong`, `AtomicReference` 같은 원자 클래스는 내부적으로 CAS(Compare-And-Set)를 활용한다.

개념은 단순하다.

1. 현재 값을 읽는다
2. 내가 기대한 값과 실제 값이 같으면 새 값으로 바꾼다
3. 다르면 누군가 먼저 바꾼 것이므로 다시 시도한다

### 왜 유용한가?

락을 오래 쥐지 않고도 단일 변수 수준의 원자적 갱신을 만들 수 있다.

```java
public class SequenceGenerator {
    private final AtomicLong sequence = new AtomicLong(0);

    public long next() {
        return sequence.incrementAndGet();
    }
}
```

이런 카운터/시퀀스는 Atomic 계열과 잘 맞는다.

### 하지만 “무조건 synchronized보다 빠르다”는 오해

경합이 약하고 연산이 단순할 때는 CAS 기반이 효율적일 수 있다. 하지만 경합이 매우 높아지면 많은 스레드가 반복적으로 CAS 실패를 겪으며 **retry 비용**이 커진다. 즉 락 대기 대신 **재시도 스핀 비용**을 치르는 셈이다.

따라서 Atomic 계열은 아래 조건에서 특히 좋다.

- 상태가 단일 변수에 가깝다
- 연산이 짧고 순수하다
- 실패 시 재시도 비용이 작다
- 블로킹 없이 높은 처리량이 필요하다

반대로 아래에서는 주의해야 한다.

- 여러 필드의 일관성을 동시에 보장해야 한다
- 읽기 후 판단 후 쓰기 로직이 복잡하다
- 재시도 루프 안에서 부작용이 섞인다
- 경합이 너무 높아 CAS 실패가 누적된다

### `AtomicReference`가 강력한 이유: 상태 전체를 원자적으로 교체할 수 있다

예를 들어 주문 처리 상태를 생각해보자.

```java
public class OrderStateMachine {
    private final AtomicReference<OrderStatus> status =
            new AtomicReference<>(OrderStatus.CREATED);

    public boolean markPaid() {
        return status.compareAndSet(OrderStatus.CREATED, OrderStatus.PAID);
    }

    public boolean ship() {
        return status.compareAndSet(OrderStatus.PAID, OrderStatus.SHIPPED);
    }

    public OrderStatus currentStatus() {
        return status.get();
    }
}
```

이 패턴은 상태 전이 규칙이 명확할 때 유용하다. 다만 상태 전이에 부가 데이터 여러 개가 함께 붙으면 단일 enum만으로는 부족해진다.

그 경우 아래처럼 **불변 상태 객체 전체를 AtomicReference로 교체**하는 접근이 더 낫다.

```java
public record CacheState(Map<String, Product> products, long loadedAtEpochMillis) {}

public class ProductCache {
    private final AtomicReference<CacheState> state =
            new AtomicReference<>(new CacheState(Map.of(), 0L));

    public CacheState getState() {
        return state.get();
    }

    public void reload(Map<String, Product> reloaded) {
        state.set(new CacheState(Map.copyOf(reloaded), System.currentTimeMillis()));
    }
}
```

이 패턴은 읽기 경합이 높고 전체 교체가 자연스러운 경우 매우 좋다.

---

## 핵심 개념 5: `LongAdder`, `ConcurrentHashMap` 같은 고수준 도구는 “문제 모양”에 맞을 때만 빛난다

### 카운터는 `AtomicLong`만 있는 게 아니다

고경합 카운터에서는 `LongAdder`가 더 유리할 때가 많다.

```java
public class Metrics {
    private final LongAdder successCount = new LongAdder();

    public void markSuccess() {
        successCount.increment();
    }

    public long successCount() {
        return successCount.sum();
    }
}
```

`LongAdder`는 내부적으로 값을 여러 셀로 분산해 경합을 줄인다. 따라서 업데이트가 매우 잦은 메트릭 수집에 잘 맞는다.

하지만 주의할 점도 있다.

- `sum()`은 순간 스냅샷 개념에 가깝다
- “지금 이 증가 직후의 정확한 전역 값”이 꼭 필요하다면 불리할 수 있다
- 시퀀스 번호 발급처럼 **정확한 단일 증가 결과**가 필요한 문제에는 맞지 않는다

즉 지표 카운팅에는 강하지만, 업무 키 발급에는 적합하지 않다.

### `ConcurrentHashMap`은 안전한 Map이지, 안전한 비즈니스 트랜잭션이 아니다

많이 나오는 실수는 이것이다.

```java
if (!map.containsKey(key)) {
    map.put(key, loadValue(key));
}
```

맵이 concurrent라고 해도 위 코드는 안전하지 않다. `containsKey`와 `put` 사이에 다른 스레드가 끼어들 수 있기 때문이다.

이럴 때는 원자적 API를 써야 한다.

```java
map.computeIfAbsent(key, this::loadValue);
```

하지만 여기서도 끝이 아니다. `computeIfAbsent` 내부 함수가 무거운 연산, 외부 호출, 예외, 부작용을 포함하면 또 다른 문제가 생긴다. 즉 **자료구조의 원자성**과 **업무 처리의 안전성**은 다르다.

### 실무 팁: 자료구조 선택 전에 먼저 물어야 할 질문

- 내가 보호하려는 것은 “값 하나”인가, “상태 전이”인가?
- 일관성이 필요한 범위는 한 필드인가, 여러 필드인가?
- 읽기가 압도적으로 많은가, 쓰기가 많은가?
- 최신성 보장이 필요한가, 대략적 스냅샷이면 되는가?
- 충돌 시 대기(blocking)가 더 싫은가, 재시도(spin)가 더 싫은가?

이 질문을 건너뛰고 도구부터 고르면 대개 나중에 다시 뜯어고치게 된다.

---

## 실무 예시 1: 종료 플래그는 `volatile`, 작업 큐는 동시성 유틸리티로 분리하라

워커 기반 배치/메시지 소비 시스템에서 자주 보는 구조다.

```java
public class EventWorker implements Runnable {
    private final BlockingQueue<Event> queue;
    private volatile boolean running = true;

    public EventWorker(BlockingQueue<Event> queue) {
        this.queue = queue;
    }

    @Override
    public void run() {
        while (running || !queue.isEmpty()) {
            try {
                Event event = queue.poll(500, TimeUnit.MILLISECONDS);
                if (event != null) {
                    process(event);
                }
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                break;
            }
        }
    }

    public void stop() {
        running = false;
    }

    private void process(Event event) {
        // 비즈니스 로직
    }
}
```

여기서 핵심은 역할 분리다.

- 종료 여부: `volatile`로 가시성 확보
- 작업 전달: `BlockingQueue`가 담당
- 인터럽트 처리: 별도 종료 신호로 관리

많은 코드가 여기서 두 가지를 섞는다.

- 종료 플래그는 일반 boolean으로 둔다
- 큐 polling과 인터럽트 정책을 대충 처리한다

그러면 종료가 늦거나, 인터럽트를 먹어버리거나, 종료 시점 정합성이 깨진다.

---

## 실무 예시 2: 읽기 많은 설정/룰 엔진은 immutable snapshot + `volatile`/`AtomicReference`가 잘 맞는다

트래픽 라우팅 규칙, 피처 플래그, 과금 정책 같은 설정은 읽기가 훨씬 많고 갱신은 드문 경우가 많다.

이때 요청마다 락을 잡으면 불필요한 병목이 생긴다. 오히려 아래 패턴이 좋다.

1. 새 설정을 별도 객체로 완전히 구성한다
2. 검증한다
3. 참조를 한 번에 교체한다
4. 읽는 쪽은 현재 스냅샷만 사용한다

```java
public record PricingPolicy(
        Map<String, BigDecimal> priceByPlan,
        LocalDateTime loadedAt
) {
    public static PricingPolicy empty() {
        return new PricingPolicy(Map.of(), LocalDateTime.MIN);
    }
}

public class PricingPolicyRegistry {
    private final AtomicReference<PricingPolicy> current =
            new AtomicReference<>(PricingPolicy.empty());

    public PricingPolicy current() {
        return current.get();
    }

    public void refresh(Map<String, BigDecimal> loaded) {
        PricingPolicy next = new PricingPolicy(Map.copyOf(loaded), LocalDateTime.now());
        current.set(next);
    }
}
```

이 구조의 장점은 명확하다.

- 읽기 경로가 매우 단순하다
- 중간 상태 노출이 없다
- 락 경합이 거의 없다
- 롤백도 쉽다(이전 스냅샷 보관 시)

단, 전제는 상태 객체가 **불변**이어야 한다는 점이다. `current.set(newState)`를 했더라도 내부 Map을 다시 수정하면 의미가 무너진다.

---

## 실무 예시 3: 재고 차감처럼 “검증 + 변경”이 붙은 문제는 임계구역을 먼저 설계하라

재고 차감은 흔한 동시성 예시지만, 실무에서는 더 중요한 포인트가 있다. 많은 팀이 아래처럼 단순 카운터 문제로만 본다.

```java
quantity.decrementAndGet();
```

하지만 실제 요구사항은 보통 이렇다.

- 수량이 충분해야 한다
- 음수가 되면 안 된다
- 이력 저장과 결제 흐름이 이어진다
- 중복 요청에 대한 방어도 필요하다

즉 문제는 “숫자 하나 감소”가 아니라 **상태 전이 규칙 보장**이다. 이런 경우는 보통 단일 JVM 메모리 동기화만으로 끝나지 않는다.

그래도 JVM 내부에서 최소한 아래 질문을 먼저 정리해야 한다.

### 애플리케이션 메모리 레벨에서 필요한 것

- 같은 객체에 대한 동시 접근 제어
- 검증과 변경의 원자성
- 읽기 스냅샷 일관성

### 시스템 전체 레벨에서 추가로 필요한 것

- DB 트랜잭션
- 낙관적 락/비관적 락
- 멱등키(idempotency key)
- 중복 결제/중복 주문 방어

즉 `AtomicInteger` 하나로 재고 문제를 푼다고 생각하면 위험하다. **메모리 내 동시성 제어와 영속 계층 정합성은 분리해서 봐야 한다.**

---

## 트레이드오프 1: `volatile` vs `synchronized` vs Atomic, 무엇을 언제 고를까?

| 상황 | 권장 선택 | 이유 |
| --- | --- | --- |
| 종료 플래그, 최신 설정 참조 | `volatile` | 단순 읽기/쓰기 + 가시성 보장에 적합 |
| 카운터, 시퀀스, 단일 값 CAS 갱신 | Atomic 계열 | 단일 변수 원자 갱신에 적합 |
| 검증 후 변경, 여러 필드 일관성 | `synchronized` 또는 명시적 락 | 복합 상태 전이를 한 덩어리로 보호하기 쉬움 |
| 읽기 압도적, 전체 교체형 상태 | `volatile` + immutable object / `AtomicReference` | 읽기 경합 최소화 |
| 고경합 메트릭 카운팅 | `LongAdder` | 분산 셀로 contention 감소 |
| 키 단위 동시 캐시 | `ConcurrentHashMap` + 원자 API | 자료구조 수준 동시성 제공 |

이 표를 외워서 끝내면 안 되고, 항상 아래를 함께 봐야 한다.

- 단일 값인가 복합 상태인가?
- 정확한 직렬화가 필요한가?
- 최신성 보장이 필요한가, 최종 일관성이면 되는가?
- 경합 패턴은 어떤가?

---

## 트레이드오프 2: 락 기반 접근과 CAS 기반 접근은 비용 구조가 다르다

### 락 기반 접근의 비용

- 경합 시 대기 시간이 발생한다
- 컨텍스트 스위칭 비용이 생길 수 있다
- 하지만 코드가 단순하고 의미 보존이 쉽다

### CAS 기반 접근의 비용

- 블로킹 대신 재시도 비용이 든다
- 고경합에서는 반복 실패로 CPU를 더 쓸 수 있다
- 단일 변수 수준에서는 빠르고 확장성이 좋다
- 복잡한 상태 전이로 갈수록 코드 이해도가 급격히 떨어질 수 있다

실무 기준으로는 이렇다.

> **업무 규칙이 복잡하면 먼저 명확한 락 기반 코드로 정합성을 맞추고, 병목이 실제로 확인될 때 더 세밀한 CAS/분할 락/고수준 동시성 구조로 최적화하는 편이 안전하다.**

동시성은 “이론상 더 빠른 코드”보다 **운영에서 덜 틀리는 코드**가 먼저다.

---

## 흔한 실수 1: `volatile`로 복합 상태를 보호하려는 시도

```java
private volatile UserSession session;
```

이 선언 자체는 문제가 아닐 수 있다. 문제는 `session` 내부 필드를 여러 곳에서 변경하는 경우다.

- 참조는 최신으로 보여도
- 내부 상태가 가변(mutable)이고
- 여러 필드가 따로따로 수정되면
- 읽는 쪽은 여전히 중간 상태를 볼 수 있다

즉 `volatile`은 참조 가시성을 보장할 뿐, **객체 내부 불변성을 자동으로 만들어주지 않는다**.

해결책은 보통 둘 중 하나다.

- 내부를 불변 객체로 바꾼다
- 복합 변경은 락으로 보호한다

---

## 흔한 실수 2: `ConcurrentHashMap`을 쓰면서 check-then-act를 그대로 유지

아래 코드는 흔하지만 경쟁 조건이 있다.

```java
if (userCache.get(userId) == null) {
    userCache.put(userId, loadUser(userId));
}
```

문제는 두 스레드가 동시에 null을 보고 둘 다 적재할 수 있다는 점이다.

대안은 아래처럼 **원자적 API**를 쓰는 것이다.

```java
userCache.computeIfAbsent(userId, this::loadUser);
```

다만 `loadUser`가 무겁거나 예외를 던지거나, 외부 부작용을 가지면 또 다른 정책이 필요하다. 결국 concurrent collection은 시작점이지 끝이 아니다.

---

## 흔한 실수 3: 락 안에서 외부 시스템 호출까지 한꺼번에 처리

이 패턴은 코드 리뷰에서 정말 자주 보인다.

- 락 획득
- DB 조회
- 외부 API 호출
- 파일 쓰기
- 로그 적재
- 락 해제

이렇게 되면 임계구역이 실제 상태 보호보다 훨씬 넓어지고, 시스템 전체 처리량이 급감한다.

원칙은 단순하다.

- 임계구역은 짧게
- 메모리 상태 보호 중심으로
- 외부 I/O는 가능한 한 밖으로

그리고 I/O를 밖으로 뺀 뒤 정합성이 필요하면, 그때는 Outbox, 재시도, 상태 머신, 멱등성 같은 상위 설계를 붙여야 한다.

---

## 흔한 실수 4: `AtomicInteger`가 있으니 비즈니스 로직도 안전하다고 믿는 것

예를 들어 아래 같은 코드가 있다.

```java
if (balance.get() >= amount) {
    balance.addAndGet(-amount);
}
```

이 코드는 안전하지 않다. 읽기와 쓰기가 분리되어 있기 때문이다. 두 스레드가 동시에 `balance.get() >= amount`를 통과할 수 있다.

이럴 때는 CAS 루프 또는 락 기반 임계구역이 필요하다.

```java
public boolean withdraw(int amount) {
    while (true) {
        int current = balance.get();
        if (current < amount) {
            return false;
        }
        int next = current - amount;
        if (balance.compareAndSet(current, next)) {
            return true;
        }
    }
}
```

이 코드는 단일 값 관점에서는 안전하다. 하지만 출금 이력 저장, 한도 검증, 감사 로그 기록까지 붙으면 다시 문제가 커진다. 즉 CAS 루프는 문제 크기가 작을 때 강하다.

---

## 흔한 실수 5: 테스트에서 재현되지 않으니 동시성 문제가 없다고 결론내리는 것

동시성 버그는 재현성이 낮다. 그래서 더 위험하다.

- 로컬에서는 코어 수가 적고 부하가 낮다
- 테스트는 스케줄링 타이밍이 단순하다
- JIT 최적화, GC, 운영 데이터 분포가 다르다
- 로그를 넣는 순간 타이밍이 바뀌어 증상이 사라지기도 한다

따라서 동시성 문제는 “한 번도 못 봤으니 없다”가 아니라 아래처럼 접근해야 한다.

- 공유 상태가 있는가?
- happens-before가 명확한가?
- 복합 연산이 분리되어 있는가?
- 읽기/쓰기 경쟁 시 불변식이 깨질 수 있는가?

즉 **증상 관찰보다 구조 검토가 먼저**다.

---

## 실무 체크리스트: Java 동시성 코드 리뷰에서 꼭 보는 항목

### 상태 모델링

- [ ] 이 상태는 정말 공유되어야 하는가?
- [ ] mutable 상태를 immutable snapshot으로 바꿀 수 없는가?
- [ ] 한 필드 문제인가, 여러 필드 일관성 문제인가?

### 메모리 가시성

- [ ] 다른 스레드가 최신 값을 봐야 하는데 happens-before가 없는 코드는 없는가?
- [ ] 종료 플래그, 설정 참조, 캐시 스냅샷에 `volatile`/원자 참조가 필요한가?
- [ ] safe publication 없이 객체 참조를 외부에 노출하지 않는가?

### 원자성

- [ ] `++`, `--`, `get-then-set`, `containsKey-then-put` 같은 패턴이 숨어 있지 않은가?
- [ ] 검증 후 변경이 한 임계구역 또는 CAS 루프로 묶여 있는가?
- [ ] 자료구조 원자성과 비즈니스 정합성을 혼동하지 않는가?

### 락 설계

- [ ] 락 범위가 너무 넓지 않은가?
- [ ] 락 안에서 DB, 네트워크, 파일 I/O를 하지 않는가?
- [ ] 락 획득 순서가 여러 군데에서 엇갈리지 않는가?

### Atomic/CAS 사용

- [ ] 단일 값 문제인데 과도하게 락을 쓰고 있지 않은가?
- [ ] CAS 실패 재시도 루프 안에 부작용이 들어가지 않았는가?
- [ ] `LongAdder`가 맞는 문제인지, `AtomicLong`이 맞는 문제인지 구분했는가?

### 운영 관점

- [ ] 고경합 지점에 대한 메트릭(실패 재시도, 큐 적체, 처리 시간)이 있는가?
- [ ] 동시성 문제를 재현할 부하/경합 테스트가 있는가?
- [ ] 단일 JVM 안전성과 DB/메시지/외부 API 정합성을 별도로 검토했는가?

---

## 한 단계 더: 대부분의 동시성 최적화보다 “공유 상태 축소”가 먼저다

실무에서 가장 과소평가되는 원칙은 이것이다.

> **가장 좋은 락은 안 잡아도 되는 락이다.**

정확히는, 가장 좋은 동시성 최적화는 공유 상태를 줄여서 **경쟁 자체를 없애는 것**이다.

예를 들면 아래 같은 개선이 먼저다.

- 전역 mutable 캐시 대신 immutable snapshot 교체
- 하나의 거대한 락 대신 키 단위 분할
- 동기 공유 상태 대신 메시지 큐 기반 비동기 처리
- 계산 가능한 값은 캐시 대신 재계산
- 요청 스코프 상태를 싱글톤에 두지 않기

도구 선택보다 구조 선택이 더 큰 효과를 내는 경우가 많다. `synchronized`냐 `AtomicReference`냐를 고민하기 전에 **왜 여러 스레드가 이 상태를 동시에 만져야 하는지**를 먼저 묻는 편이 맞다.

---

## 결론: 동시성 도구는 문법이 아니라 상태 전이 설계 도구다

Java 동시성에서 흔히 실패하는 이유는 키워드를 몰라서가 아니다. 대부분은 아래 둘 중 하나다.

1. 보호해야 할 상태 범위를 잘못 잡았다
2. happens-before 없이 값이 당연히 보일 거라고 믿었다

정리하면 이렇게 가져가면 된다.

- `volatile`은 **단순 상태의 최신값 가시성**에 강하다
- `synchronized`는 **복합 상태 전이의 명확한 보호**에 강하다
- Atomic 계열은 **단일 값의 원자 갱신과 락 회피**에 강하다
- `ConcurrentHashMap`, `LongAdder` 같은 고수준 도구는 **문제 모양에 맞을 때만** 빛난다
- 무엇보다 중요한 건 **공유 상태 자체를 줄이는 설계**다

동시성 코드는 똑똑해 보이는 코드보다 **불변식이 눈에 보이는 코드**가 오래 살아남는다.

---

## 한 줄 정리

**Java 동시성의 핵심은 `volatile`·`synchronized`·Atomic 중 하나를 맹신하는 것이 아니라, 가시성·원자성·순서성을 분리해서 보고 상태 전이 규칙에 맞는 도구를 선택하는 데 있다.**
