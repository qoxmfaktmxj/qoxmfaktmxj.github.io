---
layout: post
title: "Java Thread Dump 분석 실전: CPU 스파이크, Deadlock, Pool Starvation, Blocked Thread를 운영 증거로 읽는 법"
date: 2026-07-20 11:50:00 +0900
categories: [java]
tags: [study, java, thread-dump, deadlock, cpu, blocked-thread, thread-pool, starvation, jstack, jcmd, operations, performance, backend]
permalink: /java/2026/07/20/study-java-thread-dump-deadlock-cpu-pool-starvation.html
---

## 배경: Thread dump는 장애 이후에 보는 로그가 아니라 장애 중에 읽어야 하는 증거다

Java 서비스를 운영하다 보면 모니터링 그래프가 먼저 이상 신호를 보낸다.

- CPU가 갑자기 90% 이상으로 올라간다.
- 응답 시간이 늘어나는데 GC pause는 크지 않다.
- Tomcat, Undertow, Netty worker thread가 바쁘다고 나온다.
- DB connection pool이 고갈되었지만 DB 자체는 느리지 않다.
- Kafka consumer lag가 늘어나는데 consumer 프로세스는 살아 있다.
- scheduler job이 끝나지 않아 다음 실행이 밀린다.
- 배포 후 특정 API에서만 p99 latency가 크게 튄다.
- lock wait, blocked thread, deadlock 의심 로그가 간헐적으로 보인다.
- heap 사용량은 안정적인데 Pod가 CPU throttling에 걸린다.

이때 가장 흔한 대응은 애플리케이션 로그를 뒤지고, slow query를 보고, GC log를 확인하고, 최근 배포 diff를 읽는 것이다. 모두 필요하다. 하지만 Java 런타임이 지금 무엇을 하고 있는지 가장 직접적으로 보여주는 증거는 **thread dump**다.

Thread dump는 특정 시점 JVM 안의 thread 목록, 상태, stack trace, lock 소유와 대기 정보를 찍은 스냅샷이다. 겉보기에는 긴 stack trace 덩어리라서 부담스럽다. 하지만 운영 관점에서 보면 질문은 꽤 명확하다.

```text
지금 CPU를 쓰는 thread는 누구인가
어떤 thread가 lock을 잡고 있고 누가 기다리는가
thread pool의 worker가 어떤 작업에 묶여 있는가
외부 I/O 대기인지, 내부 lock 경합인지, 무한 루프인지
모든 요청 thread가 같은 지점에서 멈췄는가
몇 초 뒤에도 같은 stack이 반복되는가
```

Thread dump 분석을 단순히 "jstack 출력 읽기"로 생각하면 실무에서 잘 쓰기 어렵다. 장애는 한 장의 dump만으로 판별되지 않는 경우가 많다. CPU 문제는 OS thread id와 JVM thread를 매칭해야 하고, pool starvation은 dump와 metric을 함께 봐야 하며, deadlock은 JVM이 감지하는 monitor deadlock보다 넓은 의미의 자원 대기까지 포함한다.

오늘 글은 중급 이상 Java 개발자가 운영 현장에서 thread dump를 증거로 읽는 방법을 정리한다.

다룰 내용은 다음과 같다.

1. Thread dump에서 thread 상태와 lock 정보를 어떻게 읽을 것인가
2. CPU 스파이크를 `top`, `jcmd`, `jstack`으로 어떻게 좁힐 것인가
3. `BLOCKED`, `WAITING`, `TIMED_WAITING`, `RUNNABLE`을 오해하면 왜 원인 분석이 틀어지는가
4. deadlock, lock convoy, pool starvation, connection pool 고갈을 어떻게 구분할 것인가
5. Spring Boot, Tomcat, Executor, Kafka consumer에서 자주 보이는 stack 패턴은 무엇인가
6. thread dump를 여러 장 찍어 변화와 반복을 비교하는 방법
7. 운영에서 흔히 하는 실수와 배포 전 체크리스트는 무엇인가

결론부터 말하면 이렇다.

**Thread dump 분석의 핵심은 stack trace를 많이 아는 것이 아니라, thread 상태와 반복되는 대기 지점을 운영 지표와 연결해 "지금 병목이 실행 중인지, 대기 중인지, 고갈 중인지"를 구분하는 것이다.**

---

## 먼저 큰 그림: Thread dump는 JVM의 순간 사진이고, 장애 원인은 시간 흐름에 있다

Thread dump 한 장은 특정 시점의 상태만 보여준다.

```text
11:50:01 thread dump
  worker-1 RUNNABLE at OrderService.calculate()
  worker-2 BLOCKED on InventoryLock
  worker-3 WAITING on HikariPool
```

이 정보는 유용하지만 부족하다. 다음 순간에는 상태가 바뀔 수 있다.

```text
11:50:06 thread dump
  worker-1 RUNNABLE at OrderService.calculate()
  worker-2 BLOCKED on InventoryLock
  worker-3 WAITING on HikariPool
```

5초 뒤에도 같은 thread가 같은 stack에 있으면 의미가 달라진다. 단순히 우연히 그 순간 그 코드를 실행한 것이 아니라, 특정 작업이 오래 걸리거나 같은 자원 대기에서 풀리지 않고 있을 가능성이 커진다.

운영 분석에서는 보통 한 장보다 여러 장이 필요하다.

```bash
jcmd <pid> Thread.print > dump-1.txt
sleep 5
jcmd <pid> Thread.print > dump-2.txt
sleep 5
jcmd <pid> Thread.print > dump-3.txt
```

또는 `jstack`을 쓸 수 있다.

```bash
jstack -l <pid> > dump-1.txt
```

요즘 JDK에서는 `jcmd <pid> Thread.print`를 더 선호할 만하다. `jcmd`는 thread dump 외에도 VM flags, GC heap info, JFR 제어 등 운영 진단 명령을 같은 도구로 다룰 수 있기 때문이다. 하지만 현장에서 중요한 것은 도구 이름보다 **동일한 프로세스에 대해 짧은 간격으로 여러 장을 남기는 것**이다.

Thread dump는 단독 증거가 아니다. 아래 신호와 함께 읽어야 한다.

- CPU 사용률과 CPU throttling 여부
- GC pause와 allocation rate
- request latency와 error rate
- thread pool active count, queue size, rejected count
- DB connection pool active, idle, pending count
- Kafka consumer lag, poll interval, commit latency
- external API timeout, retry, circuit breaker 상태
- OS load average, run queue, context switch

같은 `RUNNABLE` stack이라도 CPU를 태우는 계산 루프인지, socket read로 kernel 안에서 대기 중인지에 따라 해석이 완전히 다르다. 같은 `WAITING`이라도 정상적으로 queue에서 일을 기다리는 worker인지, connection pool을 기다리며 요청 thread가 막힌 것인지에 따라 대응이 다르다.

따라서 thread dump 분석은 세 단계로 보는 편이 좋다.

```text
1. 분류
   -> thread 이름, pool, 상태, stack top을 기준으로 묶는다.

2. 반복 확인
   -> 여러 dump에서 같은 thread나 같은 stack pattern이 반복되는지 본다.

3. 운영 지표 연결
   -> CPU, latency, pool, DB, queue metric과 맞춰 원인 후보를 좁힌다.
```

---

## 핵심 개념 1: Thread 상태 이름은 원인명이 아니라 관찰값이다

Java thread dump에는 보통 다음 상태가 나온다.

```text
NEW
RUNNABLE
BLOCKED
WAITING
TIMED_WAITING
TERMINATED
```

운영에서 자주 보는 것은 `RUNNABLE`, `BLOCKED`, `WAITING`, `TIMED_WAITING`이다. 여기서 가장 중요한 원칙은 이것이다.

> Thread state는 "왜 느린가"의 답이 아니라, JVM이 그 순간 thread를 어떤 상태로 보고 있는지에 대한 관찰값이다.

### RUNNABLE은 항상 CPU를 태운다는 뜻이 아니다

`RUNNABLE`이라는 이름 때문에 많은 사람이 "지금 CPU에서 실행 중"이라고 해석한다. 실제로는 그렇지 않을 수 있다. Java thread state의 `RUNNABLE`은 JVM 관점에서 실행 가능하거나 native call 안에서 실행 중인 상태를 넓게 포함한다.

예를 들어 socket read 중인 thread가 `RUNNABLE`로 보일 수 있다.

```text
"http-nio-8080-exec-42" #91 daemon prio=5 os_prio=0 cpu=12.31ms elapsed=120.33s tid=0x... nid=0x3a1 runnable
   java.lang.Thread.State: RUNNABLE
    at sun.nio.ch.SocketDispatcher.read0(Native Method)
    at sun.nio.ch.SocketDispatcher.read(SocketDispatcher.java:47)
    at sun.nio.ch.NioSocketImpl.tryRead(NioSocketImpl.java:256)
    at java.net.SocketInputStream.read(SocketInputStream.java:185)
    at org.postgresql.core.VisibleBufferedInputStream.readMore(...)
```

이 stack은 Java 코드가 계산 루프를 돌고 있다는 뜻이 아니다. DB나 네트워크 응답을 기다리고 있을 수 있다. 따라서 CPU 스파이크를 분석할 때는 단순히 `RUNNABLE` thread 수를 세면 안 된다. OS 수준에서 어떤 native thread id가 CPU를 쓰는지 확인해야 한다.

### BLOCKED는 Java monitor 진입 대기다

`BLOCKED`는 보통 `synchronized` monitor에 들어가려다가 다른 thread가 lock을 들고 있어서 기다리는 상태다.

```text
"http-nio-8080-exec-12" #72 prio=5 tid=0x... nid=0x22f waiting for monitor entry
   java.lang.Thread.State: BLOCKED (on object monitor)
    at com.example.inventory.InventoryCache.get(InventoryCache.java:41)
    - waiting to lock <0x0000000712ab91c0> (a com.example.inventory.InventoryCache)
```

그리고 lock을 소유한 thread는 보통 이렇게 보인다.

```text
"scheduler-1" #54 prio=5 tid=0x... nid=0x1c2 runnable
   java.lang.Thread.State: RUNNABLE
    at com.example.inventory.InventoryCache.refresh(InventoryCache.java:75)
    - locked <0x0000000712ab91c0> (a com.example.inventory.InventoryCache)
```

이 경우 분석의 핵심은 기다리는 thread가 아니라 **lock을 잡고 있는 thread가 무엇을 오래 하고 있는가**다. 기다리는 thread가 많아 보여도 원인은 하나의 long critical section일 수 있다.

### WAITING은 정상 대기일 수도 있고 자원 고갈일 수도 있다

`WAITING`은 `Object.wait()`, `LockSupport.park()`, `Thread.join()` 같은 대기에서 자주 보인다. thread pool worker가 queue에서 일을 기다릴 때도 정상적으로 보일 수 있다.

```text
"pool-3-thread-7" #87 prio=5 tid=0x... waiting on condition
   java.lang.Thread.State: WAITING (parking)
    at jdk.internal.misc.Unsafe.park(Native Method)
    at java.util.concurrent.locks.LockSupport.park(LockSupport.java:341)
    at java.util.concurrent.locks.AbstractQueuedSynchronizer$ConditionNode.block(...)
    at java.util.concurrent.LinkedBlockingQueue.take(LinkedBlockingQueue.java:435)
    at java.util.concurrent.ThreadPoolExecutor.getTask(ThreadPoolExecutor.java:1062)
```

이 stack은 worker가 놀고 있다는 뜻에 가깝다. 문제일 가능성은 낮다.

반면 요청 thread가 connection pool을 기다리는 stack은 의미가 다르다.

```text
"http-nio-8080-exec-31" #101 prio=5 tid=0x... waiting on condition
   java.lang.Thread.State: TIMED_WAITING (parking)
    at jdk.internal.misc.Unsafe.park(Native Method)
    at java.util.concurrent.locks.LockSupport.parkNanos(LockSupport.java:269)
    at java.util.concurrent.SynchronousQueue$TransferStack.transfer(...)
    at com.zaxxer.hikari.util.ConcurrentBag.borrow(ConcurrentBag.java:151)
    at com.zaxxer.hikari.pool.HikariPool.getConnection(HikariPool.java:180)
```

여기서는 `TIMED_WAITING` 자체가 원인이 아니다. 요청 thread가 DB connection을 얻지 못하고 기다리고 있다는 사실이 중요하다. 이때 봐야 할 것은 HikariCP active connection 수, pending count, slow query, transaction duration, connection leak이다.

### TIMED_WAITING은 timeout이 있다는 뜻이지 안전하다는 뜻이 아니다

`TIMED_WAITING`은 제한 시간이 있는 대기다. `sleep`, `parkNanos`, timed wait, socket timeout 등에서 보인다. 제한 시간이 있으니 괜찮다고 생각하기 쉽지만, 운영에서는 제한 시간이 너무 길거나 너무 많이 반복되어 장애가 될 수 있다.

예를 들어 외부 API 호출 timeout이 30초이고 Tomcat worker가 200개라고 하자. 외부 API가 느려졌을 때 200개 요청 thread가 모두 `TIMED_WAITING`에 묶이면 서버는 살아 있지만 새 요청을 처리하지 못한다.

따라서 중요한 질문은 이것이다.

- timeout 값이 사용자 요청의 전체 deadline보다 짧은가
- 대기 중인 thread 수가 pool capacity를 잠식하는가
- retry가 같은 pool에서 추가 대기를 만들어내는가
- circuit breaker나 bulkhead가 더 앞단에서 부하를 자르는가

---

## 핵심 개념 2: CPU 스파이크는 OS thread id와 JVM thread를 매칭해야 한다

CPU가 높을 때 thread dump만 보면 답이 흐릿하다. 먼저 OS가 어떤 thread에 CPU를 쓰고 있는지 봐야 한다.

Linux에서는 다음 흐름이 실용적이다.

```bash
pid=$(pgrep -f 'java')
top -H -p "$pid"
```

`top -H`는 프로세스 안의 native thread별 CPU 사용률을 보여준다. 여기서 높은 CPU를 쓰는 thread의 id를 확인한다. 예를 들어 `top`에서 thread id가 `9251`로 나왔다면 16진수로 바꾼다.

```bash
printf '%x\n' 9251
```

결과가 `2423`이면 thread dump에서 `nid=0x2423`을 찾는다.

```bash
jcmd "$pid" Thread.print > dump.txt
grep -n 'nid=0x2423' dump.txt
```

이제 실제로 CPU를 쓰는 Java stack을 볼 수 있다.

CPU 스파이크의 흔한 패턴은 다음과 같다.

### 무한 루프 또는 종료 조건 누락

```text
"http-nio-8080-exec-17" #88 prio=5 os_prio=0 cpu=91023.20ms nid=0x2423 runnable
   java.lang.Thread.State: RUNNABLE
    at com.example.pricing.DiscountRuleEngine.match(DiscountRuleEngine.java:142)
    at com.example.pricing.DiscountRuleEngine.evaluate(DiscountRuleEngine.java:89)
    at com.example.order.OrderPriceService.calculate(OrderPriceService.java:57)
```

여러 dump에서 같은 line 근처에 계속 머문다면 루프, 큰 컬렉션 순회, 비효율 알고리즘, regex backtracking을 의심한다.

### 정규식 catastrophic backtracking

```text
java.util.regex.Pattern$Loop.match(Pattern.java:4894)
java.util.regex.Pattern$GroupTail.match(Pattern.java:4820)
java.util.regex.Pattern$BranchConn.match(Pattern.java:4698)
```

입력 길이가 길거나 악의적인 문자열이 들어오면 특정 regex가 CPU를 오래 잡아먹을 수 있다. 이 경우 thread dump에는 애플리케이션 코드보다 `java.util.regex` stack이 반복된다. 대응은 regex 단순화, possessive quantifier, atomic group, 입력 길이 제한, 파서 교체다.

### JSON 직렬화와 reflection 비용

```text
com.fasterxml.jackson.databind.ser.BeanSerializer.serialize(...)
com.fasterxml.jackson.databind.ser.std.CollectionSerializer.serializeContents(...)
com.example.api.ReportController.export(...)
```

큰 응답을 직렬화하거나 순환 참조, lazy loading, 거대한 object graph가 섞이면 CPU가 직렬화에 묶일 수 있다. 이 경우 해결은 thread pool 증설이 아니라 응답 shape 축소, pagination, streaming, DTO 분리, fetch plan 정리다.

### 압축, 암호화, 해시 계산

```text
java.util.zip.Deflater.deflateBytesBytes(Native Method)
javax.crypto.Cipher.doFinal(...)
java.security.MessageDigest.digest(...)
```

이 stack은 CPU 사용 자체가 정상일 수 있다. 문제는 그 작업이 request thread에서 수행되어 latency를 잡아먹는지, batch worker로 격리되어 있는지, input size 제한이 있는지다.

CPU 분석에서 피해야 할 결론은 "RUNNABLE이 많으니 CPU 문제"다. 실제 순서는 반대다.

```text
OS에서 CPU를 쓰는 native thread 확인
  -> nid로 JVM thread 매칭
  -> 여러 dump에서 stack 반복 확인
  -> 코드 경로와 입력 크기, 최근 변경, metric 연결
```

---

## 핵심 개념 3: Deadlock은 JVM이 감지하는 것보다 넓다

JVM thread dump는 Java monitor deadlock을 감지해 마지막에 출력해 주기도 한다.

```text
Found one Java-level deadlock:
=============================
"worker-1":
  waiting to lock monitor 0x..., which is held by "worker-2"
"worker-2":
  waiting to lock monitor 0x..., which is held by "worker-1"
```

이런 경우는 비교적 명확하다. 두 thread가 서로의 lock을 기다린다. 해결 방향도 lock 순서 고정, lock 범위 축소, timeout 있는 `tryLock`, 불변 데이터 구조, actor/queue 모델 전환처럼 비교적 정해져 있다.

하지만 운영에서 더 자주 만나는 것은 JVM이 "deadlock"이라고 직접 말하지 않는 교착 상태다.

### Lock convoy

하나의 lock을 오래 잡는 thread 때문에 많은 thread가 줄을 서는 상황이다.

```text
"http-nio-8080-exec-1" BLOCKED
  waiting to lock InventoryCache

"http-nio-8080-exec-2" BLOCKED
  waiting to lock InventoryCache

"scheduler-1" RUNNABLE
  locked InventoryCache
  at InventoryCache.refresh(...)
  at InventoryRepository.findAll(...)
```

여기서 문제는 `scheduler-1`이 lock을 잡은 상태로 DB 조회나 외부 API 호출을 하고 있다는 점이다. critical section 안에서 느린 I/O를 하면 lock 대기자가 폭증한다.

좋은 구조는 보통 다음과 같다.

```java
public void refresh() {
    Map<String, Item> loaded = repository.findAllAsMap(); // lock 밖에서 느린 I/O

    synchronized (this) {
        this.items = Map.copyOf(loaded); // lock 안에서는 짧게 교체
    }
}
```

lock은 공유 상태를 바꾸는 짧은 구간에만 써야 한다. I/O, sleep, retry, callback 호출, 사용자 코드 실행은 lock 안에 두지 않는 것이 기본이다.

### Thread pool starvation

Thread pool starvation은 모든 worker가 대기 작업에 묶여 새 작업이 실행되지 못하는 상태다. JVM은 이를 deadlock으로 감지하지 않을 수 있다.

예를 들어 같은 executor 안에서 부모 작업이 자식 작업을 제출하고 결과를 기다린다고 하자.

```java
ExecutorService executor = Executors.newFixedThreadPool(10);

public Report buildReport(List<Long> ids) {
    List<Future<Row>> futures = ids.stream()
            .map(id -> executor.submit(() -> loadRow(id)))
            .toList();

    return merge(futures.stream().map(this::get).toList());
}
```

만약 `buildReport` 자체도 같은 executor의 worker에서 실행되고, worker 10개가 모두 부모 작업으로 채워진 뒤 각자 자식 작업을 제출하고 기다리면 자식 작업이 실행될 worker가 없다.

dump에서는 이렇게 보일 수 있다.

```text
"report-pool-1" WAITING
  at java.util.concurrent.FutureTask.get(FutureTask.java:190)
  at com.example.report.ReportService.buildReport(ReportService.java:61)

"report-pool-2" WAITING
  at java.util.concurrent.FutureTask.get(FutureTask.java:190)
  at com.example.report.ReportService.buildReport(ReportService.java:61)
```

queue에는 작업이 쌓여 있지만 실행할 worker가 없다. 해결은 단순히 pool size를 늘리는 것이 아닐 수 있다.

- 부모 작업과 자식 작업 executor를 분리한다.
- 같은 pool 안에서 blocking join을 하지 않는다.
- 작업을 작은 단위로 쪼개되 bounded concurrency를 둔다.
- `CompletableFuture` 조합에서 `join` 위치를 마지막 경계로 제한한다.
- batch fan-out 크기를 pool capacity와 외부 dependency capacity에 맞춘다.

### Connection pool starvation

요청 thread가 모두 DB connection을 기다리는 상황도 흔하다.

```text
"http-nio-8080-exec-44" TIMED_WAITING
  at com.zaxxer.hikari.pool.HikariPool.getConnection(HikariPool.java:...)
  at org.hibernate.engine.jdbc.connections.internal.DatasourceConnectionProviderImpl.getConnection(...)
```

원인은 여러 가지다.

- slow query가 connection을 오래 점유한다.
- transaction 범위가 너무 넓다.
- 외부 API 호출을 DB transaction 안에서 수행한다.
- connection leak이 있다.
- request thread 수가 DB pool보다 훨씬 크고 backpressure가 없다.
- retry가 connection 대기를 증폭한다.
- batch job이 API와 같은 pool을 쓴다.

이때 Hikari maximumPoolSize만 늘리면 DB가 버티지 못해 더 큰 장애가 날 수 있다. 먼저 transaction duration, query latency, pool pending count, DB max connection, request concurrency를 함께 봐야 한다.

---

## 핵심 개념 4: Thread 이름은 운영 설계 문서다

Thread dump에서 가장 먼저 봐야 하는 것은 thread 이름이다.

```text
"http-nio-8080-exec-31"
"boundedElastic-42"
"ForkJoinPool.commonPool-worker-7"
"kafka-consumer-3"
"scheduling-1"
"pool-17-thread-9"
```

좋은 thread 이름은 어떤 subsystem이 막혔는지 바로 알려준다. 나쁜 이름은 모든 것이 `pool-17-thread-9`로 보이게 만든다.

운영 가능한 Java 서비스는 executor를 만들 때 이름을 붙여야 한다.

```java
@Bean
public ThreadPoolTaskExecutor invoiceExecutor() {
    ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
    executor.setThreadNamePrefix("invoice-worker-");
    executor.setCorePoolSize(8);
    executor.setMaxPoolSize(16);
    executor.setQueueCapacity(200);
    executor.initialize();
    return executor;
}
```

또한 pool metric을 함께 노출해야 한다.

- active thread count
- pool size
- queue size
- completed task count
- rejected task count
- task duration
- wait time in queue

Thread dump는 "지금 어떤 stack인가"를 보여주고, metric은 "얼마나 자주, 얼마나 오래 그런가"를 보여준다. 둘 중 하나만 있으면 판단이 약하다.

### ForkJoinPool.commonPool은 덤프에서 경고 신호일 수 있다

`CompletableFuture.supplyAsync()`에 executor를 넘기지 않으면 기본적으로 `ForkJoinPool.commonPool()`을 쓴다.

```java
CompletableFuture.supplyAsync(() -> externalClient.call());
```

dump에서 이런 thread가 많이 보인다면 확인해야 한다.

```text
"ForkJoinPool.commonPool-worker-5"
  at java.net.SocketInputStream.read(...)
  at com.example.ExternalClient.call(...)
```

공용 풀은 CPU 작업에는 적합할 수 있지만 blocking I/O를 무심코 태우면 다른 비동기 작업과 간섭한다. 특히 여러 라이브러리와 애플리케이션 코드가 같은 common pool을 공유하면 장애 반경이 커진다.

대응은 명확하다.

- 외부 I/O용 bounded executor를 따로 둔다.
- timeout과 queue capacity를 명시한다.
- rejection policy를 관측 가능하게 만든다.
- request 전체 deadline보다 내부 stage timeout을 짧게 둔다.
- MDC, trace context propagation을 처리한다.

---

## 실무 예시 1: CPU는 높은데 GC도 DB도 조용한 경우

상황을 가정해 보자.

```text
증상
  - CPU 95%
  - p99 latency 4초
  - GC pause 정상
  - DB slow query 없음
  - 특정 검색 API 배포 후 발생
```

먼저 PID를 찾고 native thread별 CPU를 본다.

```bash
pid=$(pgrep -f 'app.jar')
top -H -p "$pid"
```

CPU를 많이 쓰는 TID가 `18472`라고 하자.

```bash
printf '%x\n' 18472
# 4828
```

thread dump에서 `nid=0x4828`을 찾는다.

```text
"http-nio-8080-exec-77" #177 prio=5 os_prio=0 cpu=52330.12ms elapsed=60.13s nid=0x4828 runnable
   java.lang.Thread.State: RUNNABLE
    at java.util.regex.Pattern$Branch.match(Pattern.java:4734)
    at java.util.regex.Pattern$GroupHead.match(Pattern.java:4789)
    at java.util.regex.Pattern$Loop.match(Pattern.java:4894)
    at java.util.regex.Pattern$GroupTail.match(Pattern.java:4820)
    at java.util.regex.Matcher.match(Matcher.java:1756)
    at java.util.regex.Matcher.matches(Matcher.java:712)
    at com.example.search.SearchFilterParser.isValid(SearchFilterParser.java:38)
```

5초 간격으로 찍은 dump에서도 같은 stack이 반복된다. 최근 검색 API에서 사용자 입력 filter expression을 regex로 검증하는 코드가 추가되었다. 특정 입력이 catastrophic backtracking을 만든 것이다.

대응은 thread 수 증설이 아니다.

- 입력 문자열 최대 길이를 제한한다.
- 위험한 regex를 제거하거나 선형 시간 파서로 바꾼다.
- regex에 possessive quantifier 또는 atomic group을 적용한다.
- 요청 timeout과 rate limit을 둔다.
- 문제 입력을 재현 테스트로 남긴다.

이 사례에서 thread dump가 준 핵심 증거는 "CPU가 Java regex engine 안에서 소비되고 있다"는 점이다. GC나 DB를 더 보는 것은 후순위다.

---

## 실무 예시 2: 모든 요청이 느린데 CPU는 낮은 경우

이번에는 증상이 다르다.

```text
증상
  - CPU 25%
  - request latency 급증
  - Tomcat active thread 최대치 근접
  - Hikari pending threads 증가
  - DB CPU는 높지 않음
```

thread dump에는 비슷한 stack이 많이 보인다.

```text
"http-nio-8080-exec-101" TIMED_WAITING
  at jdk.internal.misc.Unsafe.park(Native Method)
  at java.util.concurrent.locks.LockSupport.parkNanos(LockSupport.java:269)
  at com.zaxxer.hikari.util.ConcurrentBag.borrow(ConcurrentBag.java:151)
  at com.zaxxer.hikari.pool.HikariPool.getConnection(HikariPool.java:180)
  at com.zaxxer.hikari.HikariDataSource.getConnection(HikariDataSource.java:128)
  at org.hibernate.engine.jdbc.connections.internal.DatasourceConnectionProviderImpl.getConnection(...)
  at com.example.order.OrderService.createOrder(OrderService.java:44)
```

여기서 CPU가 낮은 것은 서버가 여유롭다는 뜻이 아니다. 요청 thread가 DB connection을 기다리며 멈춰 있기 때문에 CPU를 쓰지 못하는 것이다.

다음으로 봐야 할 것은 connection을 이미 잡고 있는 thread의 stack이다. dump에서 JDBC query 실행 중인 thread를 찾는다.

```text
"http-nio-8080-exec-32" RUNNABLE
  at sun.nio.ch.SocketDispatcher.read0(Native Method)
  at org.postgresql.core.VisibleBufferedInputStream.readMore(...)
  at org.postgresql.core.QueryExecutorImpl.processResults(...)
  at org.hibernate.loader.ast.internal.SingleIdLoadPlan.load(...)
  at com.example.payment.PaymentService.confirm(PaymentService.java:88)
  at com.example.order.OrderService.createOrder(OrderService.java:57)
```

코드를 보니 `@Transactional` 메서드 안에서 외부 결제 API 호출까지 수행하고 있었다.

```java
@Transactional
public OrderResult createOrder(CreateOrderCommand command) {
    Order order = orderRepository.save(command.toOrder());
    PaymentResult payment = paymentClient.confirm(command.paymentKey()); // transaction 안의 외부 I/O
    order.markPaid(payment.approvedAt());
    return OrderResult.from(order);
}
```

이 구조에서는 외부 API가 느려질 때 DB connection도 함께 오래 점유된다. 요청이 늘어나면 Hikari pool이 고갈되고, 새 요청은 connection을 기다린다.

개선 방향은 transaction 경계와 외부 I/O 경계를 분리하는 것이다.

```java
public OrderResult createOrder(CreateOrderCommand command) {
    Order order = orderCreator.createPendingOrder(command);

    PaymentResult payment = paymentClient.confirm(command.paymentKey());

    return orderPaymentMarker.markPaid(order.id(), payment);
}
```

물론 결제 도메인은 정합성 요구가 높으므로 단순히 트랜잭션을 쪼개는 것으로 끝나지 않는다. pending 상태, idempotency key, outbox, 보상 처리, 결제 승인 조회 재시도 같은 설계가 필요하다. 하지만 thread dump가 알려준 운영 사실은 분명하다.

> DB connection pool 장애처럼 보였지만 실제 원인은 transaction 안의 느린 외부 I/O였다.

---

## 실무 예시 3: Kafka consumer lag가 늘어나는데 프로세스는 살아 있는 경우

Kafka consumer 장애도 thread dump로 많은 단서를 얻을 수 있다.

증상은 다음과 같다.

```text
증상
  - consumer lag 지속 증가
  - 애플리케이션 health는 UP
  - CPU 낮음
  - 에러 로그 거의 없음
  - rebalance가 가끔 발생
```

dump를 보면 consumer thread가 메시지 처리 중 외부 API를 기다리고 있다.

```text
"kafka-consumer-orders-0" TIMED_WAITING
  at java.lang.Thread.sleep(Native Method)
  at com.example.retry.FixedBackoffSleeper.sleep(FixedBackoffSleeper.java:22)
  at com.example.delivery.DeliveryClient.callWithRetry(DeliveryClient.java:71)
  at com.example.orders.OrderEventHandler.handle(OrderEventHandler.java:44)
  at org.springframework.kafka.listener.KafkaMessageListenerContainer$ListenerConsumer.doInvokeOnMessage(...)
```

문제는 retry sleep이 consumer thread 안에서 수행된다는 점이다. 처리량은 급격히 떨어지고, `max.poll.interval.ms`를 넘으면 rebalance가 발생할 수 있다. rebalance가 다시 처리를 늦추고 lag가 더 늘어난다.

해결은 상황에 따라 다르지만 원칙은 비슷하다.

- consumer poll thread를 긴 외부 I/O와 retry sleep에 묶지 않는다.
- 실패 이벤트는 retry topic, delayed queue, outbox, DLQ로 분리한다.
- 처리 timeout을 명시하고 무한 재시도를 금지한다.
- idempotent handler를 만들어 재처리 가능하게 한다.
- partition concurrency와 downstream capacity를 맞춘다.
- lag, processing time, retry count, DLQ count를 함께 본다.

Thread dump는 "consumer가 죽은 것이 아니라 살아 있는 채로 느린 retry에 묶여 있다"는 사실을 보여준다.

---

## 트레이드오프: Thread를 늘리면 빨라질까

장애 중에 가장 유혹적인 대응은 thread pool 크기를 늘리는 것이다.

```yaml
server:
  tomcat:
    threads:
      max: 400
```

또는 executor pool을 키운다.

```java
executor.setMaxPoolSize(100);
executor.setQueueCapacity(10000);
```

어떤 상황에서는 도움이 된다. CPU가 낮고 외부 I/O 대기 시간이 길며 downstream이 충분히 버틸 수 있다면 concurrency 증가로 throughput이 올라갈 수 있다.

하지만 많은 운영 장애에서 thread 증설은 병목을 뒤로 밀 뿐이다.

- DB connection pool이 먼저 고갈된다.
- 외부 API rate limit에 더 빨리 걸린다.
- lock 경합이 심해진다.
- context switching이 늘어난다.
- queue 대기 시간이 길어져 timeout이 더 늦게 터진다.
- 장애 반경이 커지고 복구 시간이 늘어난다.
- p50은 좋아져도 p99가 나빠질 수 있다.

Thread 수는 처리량을 만드는 자원이면서 동시에 부하를 증폭하는 레버다. 따라서 pool 크기는 항상 아래 capacity와 함께 정해야 한다.

```text
request thread
  <= application CPU budget
  <= DB connection pool
  <= external API concurrency limit
  <= downstream queue capacity
  <= timeout budget
  <= retry budget
```

운영적으로 더 좋은 질문은 "thread를 몇 개로 늘릴까"가 아니라 다음이다.

- 어떤 작업이 blocking인가
- blocking 작업은 별도 pool로 격리되어 있는가
- queue는 bounded인가
- queue가 찼을 때 거부, fallback, shed load 중 무엇을 할 것인가
- timeout은 전체 deadline 안에 들어오는가
- retry는 동시성 폭증을 만들지 않는가
- thread가 기다리는 동안 어떤 scarce resource를 잡고 있는가

---

## 흔한 실수 1: Dump 한 장만 보고 원인을 단정한다

Thread dump 한 장에는 우연이 많이 섞인다. 특정 thread가 그 순간 `HashMap.get`에 있었다고 해서 `HashMap.get`이 병목인 것은 아니다. 요청이 정상적으로 그 코드를 지나가던 순간일 수 있다.

반복이 중요하다.

```bash
for i in 1 2 3 4 5; do
  jcmd <pid> Thread.print > "dump-$i.txt"
  sleep 5
done
```

그리고 다음을 비교한다.

- 같은 thread가 같은 stack에 계속 있는가
- thread는 바뀌지만 같은 stack pattern이 반복되는가
- lock owner가 계속 같은가
- waiting 대상 lock object가 같은가
- pool worker가 모두 같은 외부 I/O에 묶였는가
- CPU를 쓰는 native thread id가 계속 같은가

장애 분석에서 "반복되는 stack"은 강한 신호다.

## 흔한 실수 2: BLOCKED thread 수만 보고 lock을 기다리는 쪽을 고친다

`BLOCKED` thread가 100개 보이면 기다리는 코드가 문제처럼 보인다. 하지만 대부분은 lock을 잡고 있는 한 thread가 핵심이다.

찾아야 하는 것은 다음이다.

```text
- waiting to lock <0x...>
- locked <0x...>
```

같은 object id를 기준으로 대기자와 소유자를 연결해야 한다. 소유자가 lock 안에서 무엇을 하는지 보면 원인이 드러난다. lock 안에서 DB 조회, HTTP 호출, 파일 I/O, 큰 컬렉션 정렬, callback 호출을 하고 있다면 그 부분을 lock 밖으로 옮기는 것이 우선이다.

## 흔한 실수 3: Connection pool 크기를 먼저 늘린다

Hikari pending이 늘면 `maximumPoolSize`를 키우고 싶어진다. 하지만 connection pool은 DB의 동시성 예산을 애플리케이션에 나누어 주는 장치다. pool을 키우면 대기 시간이 줄 수도 있지만 DB CPU, lock, I/O, buffer cache 경쟁이 커져 전체 latency가 더 나빠질 수 있다.

먼저 확인할 것은 이것이다.

- connection checkout 시간이 긴가
- query 실행 시간이 긴가
- transaction이 오래 열려 있는가
- connection leak detection 로그가 있는가
- 외부 I/O를 transaction 안에서 하는가
- batch와 API가 같은 pool을 쓰는가
- DB max connection과 다른 서비스 사용량은 얼마인가

## 흔한 실수 4: WAITING thread를 모두 문제로 본다

대기 중인 thread가 많아도 정상일 수 있다. 대부분의 pool worker는 일이 없으면 queue에서 기다린다. scheduler도 다음 실행까지 기다린다. Netty event loop도 selector에서 기다릴 수 있다.

문제는 "기다린다"가 아니라 **무엇을 기다리며, 그 thread가 원래 일을 처리해야 할 시점인가**다.

정상 대기 예:

```text
ThreadPoolExecutor.getTask
LinkedBlockingQueue.take
ScheduledThreadPoolExecutor$DelayedWorkQueue.take
```

주의할 대기 예:

```text
HikariPool.getConnection
FutureTask.get
CompletableFuture.join
CountDownLatch.await
Object.wait on application monitor
Thread.sleep inside retry loop
```

## 흔한 실수 5: Thread dump를 남기지 않고 재시작부터 한다

운영 장애에서 재시작은 필요할 수 있다. 하지만 재시작 전에 가능한 한 증거를 남겨야 한다.

최소한 다음은 남기는 편이 좋다.

```bash
date
jcmd <pid> Thread.print > thread-$(date +%Y%m%d-%H%M%S)-1.txt
sleep 5
jcmd <pid> Thread.print > thread-$(date +%Y%m%d-%H%M%S)-2.txt
jcmd <pid> VM.flags > vm-flags.txt
jcmd <pid> GC.heap_info > heap-info.txt
```

CPU 문제라면 `top -H -p <pid>` 결과도 같이 남긴다. 컨테이너 환경에서는 `kubectl top pod`, cgroup throttling 지표, node CPU pressure도 함께 보존한다.

---

## 실무 체크리스트: Thread dump를 운영에 쓸 수 있게 만드는 기준

장애가 나기 전에 준비해야 할 것:

- JDK 도구가 들어 있는 runtime image 또는 debug sidecar를 준비한다.
- thread 이름이 subsystem을 드러내도록 executor를 설정한다.
- 모든 custom executor에 pool size, queue size, active count metric을 붙인다.
- Tomcat/Jetty/Undertow worker thread metric을 수집한다.
- HikariCP active, idle, pending, timeout metric을 수집한다.
- Kafka listener processing time, lag, rebalance count를 본다.
- 외부 API client에 timeout, retry, circuit breaker, bulkhead metric을 붙인다.
- request trace id가 비동기 경계에서도 유지되게 한다.
- thread dump 수집 runbook을 문서화한다.
- 운영자가 PID, container, Pod, Java process를 빠르게 찾을 수 있어야 한다.

장애 중에 확인할 것:

- dump를 최소 3장 이상, 5~10초 간격으로 찍는다.
- CPU 문제면 native thread id와 `nid`를 매칭한다.
- 같은 stack이 반복되는지 확인한다.
- `BLOCKED` thread의 lock owner를 찾는다.
- 요청 thread가 Hikari, 외부 API, `Future.get`, `join` 중 어디에 묶였는지 본다.
- pool worker가 queue에서 정상 대기 중인지, 작업 안에서 blocked인지 구분한다.
- thread dump 시각과 metric spike 시각을 맞춘다.
- 최근 배포 변경과 반복 stack의 코드 경로를 연결한다.
- 재시작 전 가능한 증거를 저장한다.

코드 리뷰 때 볼 것:

- `synchronized` 안에서 I/O를 하지 않는가
- `@Transactional` 안에서 외부 API를 호출하지 않는가
- 같은 executor 안에서 작업을 제출하고 `get()`으로 기다리지 않는가
- `CompletableFuture`에 executor를 명시했는가
- common pool에 blocking I/O를 태우지 않는가
- queue capacity가 무한대에 가깝지 않은가
- timeout 없는 외부 호출이 없는가
- retry가 같은 thread를 오래 붙잡지 않는가
- bulkhead 없이 request thread가 downstream 장애를 그대로 흡수하지 않는가
- lock 순서가 여러 곳에서 뒤집히지 않는가

---

## 한줄 정리

Thread dump는 긴 stack trace 모음이 아니라, Java 서비스가 장애 순간에 CPU를 쓰는지, lock을 기다리는지, pool이 고갈되었는지, 외부 I/O에 묶였는지를 보여주는 운영 증거다. 좋은 분석은 dump 여러 장의 반복 패턴을 CPU, latency, pool, DB, queue 지표와 연결해 병목의 종류를 좁히는 데서 시작한다.
