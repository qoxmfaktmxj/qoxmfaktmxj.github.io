---
layout: post
title: "Java Spring Transaction 실전: Propagation, Isolation, Timeout, ReadOnly, Proxy 경계로 데이터 정합성을 지키는 법"
date: 2026-06-26 11:50:00 +0900
categories: [java]
tags: [study, java, spring, transaction, propagation, isolation, timeout, readonly, proxy, jpa, database, backend, operations]
permalink: /java/2026/06/26/study-java-spring-transaction-propagation-isolation-timeout-readonly.html
---

## 배경: `@Transactional`은 편의 어노테이션이 아니라 실패 경계를 정하는 설계 도구다

Spring 기반 Java 백엔드에서 트랜잭션은 너무 익숙해서 오히려 가볍게 다뤄지기 쉽다.

서비스 메서드 위에 `@Transactional`을 붙인다. Repository에서 JPA entity를 조회한다. 값을 바꾸고 메서드를 빠져나오면 commit된다. 예외가 나면 rollback된다. 처음에는 이 정도 이해만으로도 CRUD 기능을 만들 수 있다.

하지만 운영 코드에서 트랜잭션 문제는 대체로 "어노테이션을 붙였는가"가 아니라 **어디부터 어디까지를 하나의 실패 단위로 볼 것인가**에서 터진다.

- 주문 생성과 재고 차감은 같은 트랜잭션이어야 하는가
- 결제 승인 API 호출은 DB 트랜잭션 안에서 실행해도 되는가
- 이벤트 발행은 commit 전인가, commit 후인가
- `REQUIRES_NEW`로 감사 로그를 남기면 본 작업이 실패해도 로그는 남아야 하는가
- 읽기 API에 `readOnly=true`를 붙이면 정말 DB가 읽기 전용으로 보장하는가
- `@Transactional`을 private 메서드나 같은 클래스 내부 호출에 붙이면 적용되는가
- checked exception이 발생하면 rollback되는가
- 격리 수준을 올리면 정합성이 좋아지는 대신 어떤 lock 비용을 지불하는가
- timeout이 걸렸을 때 DB 쿼리, JDBC driver, connection pool, HTTP client timeout은 함께 정렬되어 있는가

이 질문을 피해 가면 코드가 멀쩡해 보여도 데이터는 조용히 어긋난다.

실무 장애는 보통 이런 모양으로 나타난다.

- 주문 row는 생성됐지만 재고 차감 이벤트는 발행되지 않았다
- 외부 결제 승인은 성공했는데 DB commit이 실패해 서비스는 결제 사실을 모른다
- `@Transactional`을 붙였는데 self-invocation 때문에 실제로는 트랜잭션이 열리지 않았다
- `UnexpectedRollbackException`이 배포 후에만 발생한다
- `REQUIRES_NEW`를 남발해 connection pool이 예상보다 빨리 고갈된다
- 긴 배치 트랜잭션이 운영 테이블 row lock을 오래 잡아 API까지 느려진다
- `readOnly=true` 조회에서 lazy loading과 flush가 섞여 예상 밖의 SQL이 나간다
- 격리 수준을 `SERIALIZABLE`로 올렸더니 정합성은 좋아졌지만 retry 설계가 없어 장애율이 올라갔다

따라서 Spring Transaction을 잘 쓴다는 것은 단순히 `@Transactional` 속성을 외우는 일이 아니다.

> Spring Transaction의 핵심은 비즈니스 작업 단위를 명확히 정하고, 그 경계 안에서 DB 변경, 예외 의미, 격리 수준, timeout, 외부 시스템 호출, 이벤트 발행 순서를 일관되게 설계하는 것이다.

이 글은 중급 이상 Java 개발자를 기준으로 `@Transactional`을 운영 설계 관점에서 다룬다.

1. Spring Transaction은 AOP proxy와 PlatformTransactionManager를 통해 어떻게 동작하는가
2. propagation은 단순 옵션이 아니라 호출 그래프의 실패 경계를 어떻게 바꾸는가
3. isolation level은 어떤 이상 현상을 막고 어떤 lock/abort 비용을 만든다
4. rollback 규칙은 checked/unchecked exception, catch, rollback-only 상태와 어떻게 연결된다
5. readOnly와 timeout은 성능 옵션이 아니라 운영 의도를 드러내는 계약이다
6. JPA flush, lazy loading, dirty checking은 transaction boundary와 어떻게 맞물린다
7. 외부 API, event publishing, outbox, audit log는 트랜잭션 안팎에서 어떻게 배치해야 한다
8. 흔한 실수와 배포 전 체크리스트는 무엇인가

결론부터 말하면 이렇다.

**`@Transactional`은 데이터를 안전하게 저장해 주는 마법이 아니다. 안전한 트랜잭션은 propagation, isolation, rollback rule, timeout, readOnly, proxy 경계, 외부 I/O 분리를 함께 설계할 때 만들어진다.**

---

## 먼저 큰 그림: 트랜잭션은 "DB commit"이 아니라 작업 단위의 계약이다

트랜잭션을 좁게 보면 DB의 `BEGIN`, `COMMIT`, `ROLLBACK`이다. 하지만 애플리케이션 설계에서는 조금 더 넓게 봐야 한다.

하나의 비즈니스 작업은 보통 여러 단계를 가진다.

```text
요청 수신
  -> 입력 검증
  -> 권한 확인
  -> 현재 상태 조회
  -> 도메인 규칙 검사
  -> DB 변경
  -> 부가 기록 저장
  -> 이벤트 발행 예약
  -> 캐시 무효화
  -> 응답 반환
```

이 중 어떤 단계가 같은 트랜잭션에 들어가야 하는지 정해야 한다.

예를 들어 주문 취소를 생각해 보자.

```text
cancelOrder(orderId, actor)
  1. 주문 조회
  2. 취소 가능 상태인지 검사
  3. 주문 상태를 CANCELLED로 변경
  4. 재고 복구 기록 생성
  5. 환불 요청 이벤트 저장
  6. 감사 로그 저장
  7. 알림 발송
```

여기서 1~5는 대체로 같은 DB 트랜잭션에 있어야 한다. 주문 상태만 바뀌고 환불 이벤트가 사라지면 안 된다. 반대로 7의 알림 발송은 DB 트랜잭션 안에서 직접 실행하면 위험하다. 알림 서버가 느려지면 주문 row lock을 오래 잡고, 알림은 성공했는데 DB commit이 실패하는 역전 상황도 생긴다.

감사 로그는 정책에 따라 다르다.

- 주문 취소가 실패하면 감사 로그도 없어야 한다면 같은 트랜잭션
- 실패한 시도도 반드시 남겨야 한다면 별도 트랜잭션 또는 독립 저장소
- 보안 감사라면 본 작업 rollback과 별도로 보존해야 할 수 있음

즉 트랜잭션 경계는 "어디에 어노테이션을 붙일까"가 아니라 "이 작업에서 함께 성공하거나 함께 실패해야 하는 것은 무엇인가"로 정해야 한다.

### Spring Transaction의 실제 동작은 proxy를 통과할 때 시작된다

Spring에서 선언적 트랜잭션은 보통 AOP proxy로 구현된다.

```java
@Service
public class OrderService {

    @Transactional
    public void cancelOrder(Long orderId) {
        Order order = orderRepository.getById(orderId);
        order.cancel();
    }
}
```

호출자는 실제 `OrderService` 객체를 직접 부르는 것이 아니라 Spring이 만든 proxy를 호출한다.

```text
Controller
  -> OrderService proxy
      -> TransactionInterceptor
          -> begin transaction
          -> target.cancelOrder()
          -> commit or rollback
```

이 구조 때문에 중요한 규칙이 생긴다.

- Spring bean 외부에서 public 메서드를 호출해야 transaction advice가 적용된다
- 같은 클래스 내부에서 `this.someTransactionalMethod()`를 호출하면 proxy를 거치지 않는다
- private 메서드에 `@Transactional`을 붙여도 일반적인 proxy 방식에서는 기대한 대로 동작하지 않는다
- final class, final method, interface 기반 proxy 여부 같은 proxy 제약을 이해해야 한다

가장 흔한 실수는 self-invocation이다.

```java
@Service
public class BillingService {

    public void billAll(List<Long> orderIds) {
        for (Long orderId : orderIds) {
            this.billOne(orderId); // 트랜잭션 proxy를 거치지 않는다
        }
    }

    @Transactional
    public void billOne(Long orderId) {
        // 기대와 달리 새 트랜잭션이 열리지 않을 수 있다
    }
}
```

해결책은 보통 메서드를 다른 bean으로 분리하거나, 외부 호출 경계를 명확히 만드는 것이다.

```java
@Service
public class BillingBatchService {
    private final SingleBillingService singleBillingService;

    public BillingBatchService(SingleBillingService singleBillingService) {
        this.singleBillingService = singleBillingService;
    }

    public void billAll(List<Long> orderIds) {
        for (Long orderId : orderIds) {
            singleBillingService.billOne(orderId);
        }
    }
}

@Service
public class SingleBillingService {

    @Transactional
    public void billOne(Long orderId) {
        // 주문 하나의 과금 작업 단위
    }
}
```

이 설계는 단순히 Spring proxy 문제를 피하는 것만이 아니다. 배치 전체와 주문 한 건의 실패 단위를 분리한다는 의도가 코드 구조에 드러난다.

---

## 핵심 개념 1: propagation은 호출 그래프의 실패 단위를 바꾼다

`Propagation.REQUIRED`는 기본값이다. 이미 트랜잭션이 있으면 참여하고, 없으면 새로 시작한다.

```java
@Transactional
public void placeOrder(PlaceOrderCommand command) {
    orderService.createOrder(command);
    inventoryService.reserve(command.items());
    paymentEventService.enqueue(command.payment());
}
```

하위 서비스가 모두 `REQUIRED`라면 하나의 트랜잭션에 참여한다.

```text
placeOrder transaction
  ├─ createOrder
  ├─ reserve inventory
  └─ enqueue payment event
```

이 구조에서는 중간 어디서든 unchecked exception이 발생하면 전체가 rollback된다. 주문 생성, 재고 예약, 결제 이벤트 저장이 함께 성공하거나 함께 실패한다.

이게 가장 자연스러운 기본값이다. 하지만 모든 작업이 항상 같은 실패 단위를 가져야 하는 것은 아니다. propagation은 이 지점을 조절한다.

### REQUIRED: 대부분의 비즈니스 변경 기본값

`REQUIRED`는 "상위 작업의 일부"라는 뜻이다.

```java
@Transactional(propagation = Propagation.REQUIRED)
public void reserveInventory(List<OrderLine> lines) {
    // 상위 주문 트랜잭션에 참여
}
```

장점:

- 작업 단위가 단순하다
- 전체 rollback 의미가 명확하다
- connection 사용량이 예측 가능하다
- JPA persistence context가 자연스럽게 공유된다

주의점:

- 하위 메서드에서 예외를 catch해도 transaction이 rollback-only로 표시될 수 있다
- 하위 작업이 오래 걸리면 상위 트랜잭션 전체가 길어진다
- 독립적으로 남겨야 하는 기록까지 함께 rollback될 수 있다

실무에서는 기본적으로 비즈니스 상태 변경은 `REQUIRED`로 시작하는 것이 좋다. 다른 propagation은 "왜 실패 단위를 분리해야 하는가"가 설명될 때만 쓴다.

### REQUIRES_NEW: 별도 transaction이지만 공짜가 아니다

`REQUIRES_NEW`는 현재 트랜잭션을 잠시 멈추고 새 트랜잭션을 연다.

```java
@Transactional(propagation = Propagation.REQUIRES_NEW)
public void writeAuditLog(AuditLog log) {
    auditLogRepository.save(log);
}
```

대표 사용 사례는 감사 로그, 실패 이력, outbox 보조 기록처럼 본 작업과 독립적으로 남겨야 하는 데이터다.

```java
@Transactional
public void changeUserRole(ChangeRoleCommand command) {
    try {
        User user = userRepository.getById(command.userId());
        user.changeRole(command.newRole());
        auditLogService.writeAuditLog(AuditLog.success(command));
    } catch (RuntimeException ex) {
        auditLogService.writeAuditLog(AuditLog.failure(command, ex));
        throw ex;
    }
}
```

이 구조에서는 본 작업이 rollback되어도 audit log는 commit될 수 있다.

하지만 `REQUIRES_NEW`는 비용이 있다.

- 기존 transaction connection과 별도 connection이 필요할 수 있다
- 반복문 안에서 호출하면 connection pool 압박이 커진다
- 바깥 transaction이 잡은 lock과 안쪽 transaction이 접근하는 row가 충돌할 수 있다
- 독립 commit으로 인해 데이터 의미가 더 복잡해진다
- 테스트에서 단일 rollback으로 정리되지 않는 데이터가 남을 수 있다

특히 바깥 트랜잭션이 connection 하나를 잡고 있고, 안쪽 `REQUIRES_NEW`가 새 connection을 요구하면 동시 요청 수가 많을 때 pool exhaustion이 빨리 온다.

```text
동시 요청 50개
  각 요청: outer transaction connection 1개 점유
  각 요청 내부: REQUIRES_NEW audit connection 추가 요구
  pool size 50이면 안쪽 트랜잭션이 대기하며 전체가 멈출 수 있음
```

따라서 `REQUIRES_NEW`는 "rollback을 피하고 싶다"는 가벼운 이유로 쓰면 안 된다. 독립 commit이 실제 비즈니스 요구인지, connection pool capacity가 충분한지, 실패 시 의미가 일관적인지 함께 봐야 한다.

### NESTED: savepoint 기반 부분 rollback

`NESTED`는 기존 트랜잭션 안에 savepoint를 만들고 일부만 되돌릴 수 있게 한다. 모든 transaction manager와 DB 조합에서 동일하게 지원되는 것은 아니다.

```java
@Transactional(propagation = Propagation.NESTED)
public void applyOptionalCoupon(Order order, Coupon coupon) {
    coupon.validateFor(order);
    order.applyCoupon(coupon);
}
```

개념적으로는 다음과 같다.

```text
outer transaction begin
  savepoint A
    optional coupon logic
  rollback to savepoint A if coupon fails
  continue outer transaction
outer commit
```

사용할 수 있는 상황은 제한적이다.

- 같은 transaction 안에서 일부 작업만 되돌리고 계속 진행해야 한다
- DB savepoint를 지원한다
- JPA flush timing과 savepoint 동작을 충분히 테스트했다

실무에서는 `NESTED`보다 작업을 명시적으로 분리하거나 보상 로직을 두는 편이 더 이해하기 쉬운 경우가 많다.

### NOT_SUPPORTED, NEVER, MANDATORY: 의도를 강하게 드러내는 옵션

자주 쓰이지는 않지만, 특정 상황에서는 유용하다.

`NOT_SUPPORTED`는 transaction 없이 실행한다. 긴 리포트 조회, 외부 API 호출, 파일 생성처럼 DB transaction을 잡고 있으면 안 되는 작업을 분리할 때 쓸 수 있다.

`MANDATORY`는 반드시 기존 transaction 안에서만 실행되어야 한다는 뜻이다. 도메인 내부 저장 메서드가 독립 호출되면 위험한 경우 의도를 드러낼 수 있다.

`NEVER`는 transaction 안에서 호출되면 예외를 낸다. 실수로 긴 외부 I/O가 transaction 내부에 들어오는 것을 막고 싶을 때 사용할 수 있다.

다만 이런 옵션은 팀 전체가 의미를 공유하지 않으면 오히려 혼란을 만든다. 코드 리뷰 기준과 함께 써야 한다.

---

## 핵심 개념 2: isolation은 "더 높이면 안전"이 아니라 이상 현상과 비용의 선택이다

트랜잭션 격리 수준은 동시성 상황에서 어떤 현상을 허용할지 정한다.

Spring에서는 보통 다음처럼 지정한다.

```java
@Transactional(isolation = Isolation.READ_COMMITTED)
public void approveOrder(Long orderId) {
    // ...
}
```

하지만 격리 수준은 DB마다 구현과 기본값이 다르다. PostgreSQL, MySQL InnoDB, Oracle은 같은 이름이라도 세부 동작이 다를 수 있다. 따라서 Spring enum만 보고 판단하면 안 되고, 실제 DB의 MVCC와 lock 정책을 함께 봐야 한다.

### READ COMMITTED: 운영 기본값으로 자주 적합하다

`READ_COMMITTED`는 commit된 데이터만 읽는다. 다른 transaction이 아직 commit하지 않은 변경은 보지 않는다.

장점:

- 동시성이 좋다
- 많은 RDBMS의 기본값 또는 실무 기본값으로 적합하다
- 일반적인 API 쓰기 작업에서 비용과 정합성 균형이 좋다

한계:

- 같은 transaction 안에서 같은 조건으로 다시 조회하면 결과가 달라질 수 있다
- lost update, write skew 같은 문제는 별도 제어가 필요하다
- "조회 후 없으면 insert" 같은 로직은 unique constraint 없이는 안전하지 않다

예를 들어 쿠폰 사용을 처리한다고 하자.

```java
@Transactional
public void useCoupon(Long couponId, Long userId) {
    Coupon coupon = couponRepository.findUsable(couponId, userId)
            .orElseThrow(CouponNotFoundException::new);

    coupon.markUsed();
}
```

동시에 두 요청이 같은 쿠폰을 읽으면 둘 다 "사용 가능"하다고 판단할 수 있다. 이 문제는 격리 수준만 믿기보다 아래 조합으로 막는 것이 일반적이다.

- `used_at is null` 조건을 포함한 update
- optimistic locking version column
- unique constraint
- pessimistic lock
- idempotency key

### REPEATABLE READ: 반복 조회 안정성은 좋아지지만 모든 경쟁을 막지는 않는다

`REPEATABLE_READ`는 transaction 동안 같은 row를 반복해서 읽을 때 결과가 안정적이다. MySQL InnoDB에서는 기본값으로 많이 만난다.

장점:

- 같은 row 반복 조회 안정성이 좋다
- 일부 phantom 문제를 DB 구현이 추가로 막기도 한다
- 긴 계산 중 기준 snapshot을 유지해야 할 때 유용하다

주의점:

- snapshot이 오래 유지되면 vacuum, undo log, MVCC storage에 부담이 생긴다
- 서로 다른 row 조건 조합에서 write skew가 여전히 가능할 수 있다
- lock을 명시적으로 잡지 않으면 "읽고 판단한 조건"이 commit 시점까지 유지된다고 착각하기 쉽다

예를 들어 당직자를 최소 1명 유지해야 한다고 하자.

```java
@Transactional(isolation = Isolation.REPEATABLE_READ)
public void leaveOnCall(Long engineerId) {
    long activeCount = onCallRepository.countActive();
    if (activeCount <= 1) {
        throw new IllegalStateException("at least one engineer required");
    }

    onCallRepository.deactivate(engineerId);
}
```

두 명이 동시에 빠지면 각 transaction은 activeCount를 2로 보고 각각 자신을 비활성화할 수 있다. 최종적으로 0명이 될 수 있다. 이런 문제는 isolation만으로 막기 어렵고, constraint, lock, serializable retry, aggregate row lock 같은 설계가 필요하다.

### SERIALIZABLE: 강한 격리에는 retry 설계가 따라와야 한다

`SERIALIZABLE`은 가장 강한 수준의 격리 의미를 제공한다. 하지만 비용이 크다.

- lock 경합 또는 serialization failure가 증가할 수 있다
- transaction을 짧게 유지해야 한다
- 실패 시 재시도 가능한 구조가 필요하다
- 외부 API 호출이 transaction 안에 있으면 재시도 의미가 위험해진다

`SERIALIZABLE`을 쓰는 코드는 보통 이렇게 생겨야 한다.

```java
public void reserveWithRetry(ReserveCommand command) {
    retryTemplate.execute(context -> {
        reservationService.reserveSerializable(command);
        return null;
    });
}

@Transactional(isolation = Isolation.SERIALIZABLE, timeout = 3)
public void reserveSerializable(ReserveCommand command) {
    Inventory inventory = inventoryRepository.getBySku(command.sku());
    inventory.reserve(command.quantity());
}
```

중요한 점은 retry 바깥과 안쪽을 나누는 것이다. 같은 transaction 안에서 재시도하는 것이 아니라, 실패한 transaction을 끝내고 새 transaction으로 다시 시도해야 한다.

또한 재시도 가능한 작업이어야 한다.

- DB 상태 변경만 포함되어 있고 idempotent하면 비교적 안전하다
- 외부 결제 승인, 문자 발송, 이메일 발송을 포함하면 재시도 시 중복 부작용이 생긴다
- 재시도 횟수와 backoff가 없으면 장애 상황에서 DB를 더 압박한다

### 격리 수준보다 먼저 constraint를 설계하라

많은 정합성 문제는 transaction isolation만으로 풀기보다 DB constraint와 atomic update로 푸는 편이 더 단단하다.

예를 들어 사용자별 하루 1회 출석 체크는 isolation level을 높이기보다 unique constraint가 핵심이다.

```sql
create unique index ux_attendance_user_date
    on attendance(user_id, attendance_date);
```

애플리케이션은 중복 insert 예외를 도메인 결과로 매핑한다.

```java
@Transactional
public AttendanceResult checkIn(Long userId, LocalDate date) {
    try {
        attendanceRepository.save(new Attendance(userId, date));
        return AttendanceResult.created();
    } catch (DataIntegrityViolationException ex) {
        return AttendanceResult.alreadyCheckedIn();
    }
}
```

이 방식은 동시 요청에서도 안전하다. "먼저 조회하고 없으면 저장" 패턴보다 단순하고, DB가 가장 잘하는 일을 DB에 맡긴다.

---

## 핵심 개념 3: rollback 규칙은 예외 타입, catch 위치, rollback-only 상태까지 봐야 한다

Spring의 기본 rollback 규칙은 많은 장애의 출발점이다.

기본적으로 runtime exception과 error는 rollback 대상이고, checked exception은 rollback 대상이 아니다.

```java
@Transactional
public void importUsers(File file) throws IOException {
    List<User> users = parse(file); // IOException 발생 가능
    userRepository.saveAll(users);
}
```

위 코드에서 `IOException`이 발생하면 기본 규칙만으로는 rollback되지 않을 수 있다. 의도와 다르면 명시해야 한다.

```java
@Transactional(rollbackFor = IOException.class)
public void importUsers(File file) throws IOException {
    List<User> users = parse(file);
    userRepository.saveAll(users);
}
```

반대로 비즈니스 예외를 checked exception으로 설계했다면 rollback 정책을 반드시 정해야 한다.

```java
@Transactional(rollbackFor = BusinessRuleViolationException.class)
public void approve(ApproveCommand command) throws BusinessRuleViolationException {
    // ...
}
```

### 예외를 catch하면 rollback도 같이 생각해야 한다

가장 위험한 패턴은 transaction 안에서 예외를 잡고 정상 흐름처럼 계속 진행하는 것이다.

```java
@Transactional
public void processOrder(Long orderId) {
    try {
        paymentService.charge(orderId);
    } catch (PaymentFailedException ex) {
        orderRepository.markPaymentFailed(orderId);
    }

    orderRepository.markProcessed(orderId);
}
```

이 코드가 의도한 의미는 불명확하다.

- 결제 실패도 정상 처리로 볼 것인가
- 결제 실패 상태와 처리 완료 상태가 동시에 가능한가
- `paymentService.charge()`가 내부에서 transaction을 rollback-only로 표시했는가
- 외부 결제 호출이 이미 실행됐는가

특히 하위 `REQUIRED` 메서드에서 runtime exception이 발생해 transaction이 rollback-only로 표시된 뒤 상위에서 catch하면, 마지막 commit 시점에 `UnexpectedRollbackException`이 발생할 수 있다.

```java
@Transactional
public void outer() {
    try {
        innerService.innerRequired();
    } catch (RuntimeException ignored) {
        // 계속 진행한다고 생각하지만 transaction은 rollback-only일 수 있음
    }
}
```

이 상황은 "예외를 잡았는데 왜 rollback되냐"가 아니라, 이미 같은 transaction이 실패 상태가 되었기 때문이다.

해결 방향은 세 가지다.

1. 실패하면 전체 작업을 실패시킨다
2. 실패해도 계속해야 하는 작업은 transaction 밖으로 분리한다
3. 독립 실패 단위가 필요하면 `REQUIRES_NEW`나 별도 작업 큐를 사용한다

### rollbackFor를 넓게 잡는 것도 답이 아닐 수 있다

모든 예외에 대해 rollback하고 싶어서 아래처럼 쓰는 팀도 있다.

```java
@Transactional(rollbackFor = Exception.class)
```

이 방식은 단순하지만 위험할 수 있다.

- recoverable checked exception까지 모두 rollback된다
- 파일 없음, 외부 선택 데이터 없음 같은 도메인상 정상 분기도 실패로 처리될 수 있다
- 호출자가 예외 의미를 구분하기 어려워진다
- "예외를 던지는 validation"과 "시스템 실패"가 섞인다

좋은 기준은 예외 타입을 기술 계층이 아니라 도메인 의미로 정리하는 것이다.

- 입력이 잘못되어 상태 변경을 하면 안 된다: rollback
- 외부 시스템 일시 실패로 작업을 완료할 수 없다: rollback 또는 retry
- 선택 기능 실패지만 핵심 변경은 유지한다: 별도 transaction 또는 후속 보상
- 이미 처리된 idempotent 요청이다: 예외보다 성공 결과로 매핑

---

## 핵심 개념 4: readOnly는 최적화 힌트이면서 "쓰기 금지 의도"를 드러내는 계약이다

조회 메서드에는 흔히 `@Transactional(readOnly = true)`를 붙인다.

```java
@Transactional(readOnly = true)
public OrderDetail getOrderDetail(Long orderId) {
    Order order = orderRepository.getById(orderId);
    return OrderDetail.from(order);
}
```

`readOnly=true`는 여러 효과를 가질 수 있다.

- Spring과 transaction manager에 읽기 전용 의도를 전달한다
- Hibernate flush mode를 조정해 dirty checking/flush 비용을 줄일 수 있다
- 일부 DB에서는 read-only transaction 힌트로 전달될 수 있다
- 코드 리뷰에서 "이 메서드는 쓰기를 하면 안 된다"는 신호가 된다

하지만 오해하면 안 된다.

**`readOnly=true`가 모든 환경에서 물리적으로 쓰기를 완전히 막아 주는 것은 아니다.**

DB, driver, transaction manager, ORM 설정에 따라 실제 강제 수준이 달라질 수 있다. 따라서 readOnly는 성능 최적화와 의도 표현으로 쓰되, 보안/정합성의 유일한 방어선으로 삼으면 안 된다.

### readOnly 안에서 entity를 수정하지 말라

아래 코드는 위험하다.

```java
@Transactional(readOnly = true)
public OrderDetail viewOrder(Long orderId) {
    Order order = orderRepository.getById(orderId);
    order.markViewed(); // 조회 메서드에서 상태 변경
    return OrderDetail.from(order);
}
```

Hibernate flush mode 때문에 실제 update가 안 나갈 수도 있고, 다른 설정에서는 나갈 수도 있다. 더 나쁜 점은 코드 의미가 흐려진다는 것이다. 조회와 쓰기가 섞이면 캐시 정책, replica routing, transaction isolation, 테스트 기대값이 모두 애매해진다.

조회 중 부수 효과가 필요하면 별도 경계로 분리한다.

```java
@Transactional(readOnly = true)
public OrderDetail getOrderDetail(Long orderId) {
    Order order = orderRepository.getById(orderId);
    return OrderDetail.from(order);
}

@Transactional
public void recordOrderViewed(Long orderId, Long viewerId) {
    orderViewRepository.save(new OrderView(orderId, viewerId));
}
```

또는 조회 이벤트를 outbox/analytics pipeline으로 분리한다. 핵심은 읽기 모델 생성과 상태 변경을 같은 메서드에 숨기지 않는 것이다.

### OSIV와 lazy loading은 readOnly 경계를 흐리게 만든다

Spring Boot 애플리케이션에서 Open Session In View(OSIV)가 켜져 있으면 controller/view rendering 시점까지 persistence context가 살아 있을 수 있다.

장점은 lazy loading이 편하다는 것이다. 단점은 transaction boundary가 흐려지고, view layer에서 예상치 못한 SQL이 나가며, connection 점유 시간이 길어질 수 있다는 것이다.

```java
@GetMapping("/orders/{id}")
public OrderResponse getOrder(@PathVariable Long id) {
    Order order = orderService.getOrder(id);
    return OrderResponse.from(order); // 여기서 lazy loading이 발생할 수 있음
}
```

중급 이상 코드베이스에서는 보통 조회 메서드 안에서 필요한 데이터를 명시적으로 가져오고 DTO로 변환하는 편이 운영상 안전하다.

```java
@Transactional(readOnly = true)
public OrderResponse getOrder(Long orderId) {
    Order order = orderRepository.findDetailById(orderId)
            .orElseThrow(OrderNotFoundException::new);

    return OrderResponse.from(order);
}
```

fetch join, entity graph, projection, query model을 적절히 선택해 transaction 안에서 필요한 데이터를 완성하고, 바깥 계층에는 detached DTO를 넘긴다.

---

## 핵심 개념 5: timeout은 transaction 하나만의 속성이 아니라 전체 대기 예산의 일부다

`@Transactional(timeout = 5)`는 transaction timeout을 지정한다.

```java
@Transactional(timeout = 5)
public void closeDailySettlement(LocalDate date) {
    settlementRepository.aggregate(date);
    settlementRepository.markClosed(date);
}
```

하지만 timeout을 붙였다고 해서 모든 대기 작업이 정확히 5초에 멈춘다고 믿으면 안 된다.

실제 운영에는 여러 timeout이 있다.

- HTTP server request timeout
- Spring transaction timeout
- JDBC statement timeout
- DB lock timeout
- connection pool acquisition timeout
- external HTTP client timeout
- message broker send timeout
- load balancer timeout
- Kubernetes termination grace period

이 값들이 서로 어긋나면 이상한 현상이 생긴다.

```text
HTTP request timeout: 30s
transaction timeout: 10s
JDBC query timeout: unset
DB lock timeout: unset
Hikari connectionTimeout: 30s
external API timeout: 60s
```

이 상태에서 DB lock wait가 발생하면 애플리케이션 transaction timeout은 지났지만 DB 쿼리는 계속 대기하거나, client는 이미 timeout됐는데 서버는 뒤늦게 commit을 시도할 수 있다.

좋은 운영 기준은 timeout을 계층별로 정렬하는 것이다.

```text
사용자 요청 전체 예산: 3s
  인증/검증: 100ms
  DB transaction: 1.5s
  외부 API: transaction 밖에서 800ms
  응답 생성: 100ms
  여유: 500ms
```

DB 작업이 lock에 오래 걸리면 빠르게 실패시키고, 실패를 사용자 또는 큐 재시도로 넘기는 편이 낫다. 무한 대기는 pool과 thread를 잡아먹으며 장애 반경을 키운다.

### timeout은 긴 작업을 안전하게 만드는 장치가 아니다

긴 배치 작업에 큰 transaction timeout을 주는 것은 해결책이 아닐 수 있다.

```java
@Transactional(timeout = 3600)
public void migrateAllUsers() {
    List<User> users = userRepository.findAll();
    for (User user : users) {
        user.migrate();
    }
}
```

문제점:

- persistence context가 커진다
- lock을 오래 잡는다
- 실패 시 전체 rollback 비용이 크다
- replication lag, vacuum, undo log 부담이 커진다
- 재시작 지점이 없다

배치는 보통 chunk 단위로 트랜잭션을 나눠야 한다.

```java
public void migrateAllUsers() {
    Slice<Long> ids = userRepository.findIds(PageRequest.of(0, 500));
    while (!ids.isEmpty()) {
        userMigrationChunkService.migrateChunk(ids.getContent());
        ids = userRepository.findNextIds(ids.nextPageable());
    }
}

@Transactional(timeout = 10)
public void migrateChunk(List<Long> userIds) {
    List<User> users = userRepository.findAllById(userIds);
    users.forEach(User::migrate);
}
```

chunk 단위 설계는 timeout뿐 아니라 장애 복구, 모니터링, backpressure, lock 범위에도 유리하다.

---

## 핵심 개념 6: JPA flush는 commit 시점까지 기다리지 않을 수 있다

JPA를 쓰면 entity 값을 바꾸고 repository save를 명시적으로 호출하지 않아도 update가 나간다. dirty checking 때문이다.

```java
@Transactional
public void renameUser(Long userId, String name) {
    User user = userRepository.getById(userId);
    user.rename(name);
}
```

이 코드는 transaction commit 시점에 flush되어 update된다. 하지만 flush는 commit 때만 일어나는 것이 아니다.

- JPQL/Criteria query 실행 전
- 명시적 `entityManager.flush()`
- transaction commit 전
- flush mode 설정에 따른 자동 flush 지점

이 때문에 아래 코드에서 생각보다 일찍 SQL이 나갈 수 있다.

```java
@Transactional
public void changeEmail(Long userId, String newEmail) {
    User user = userRepository.getById(userId);
    user.changeEmail(newEmail);

    boolean exists = userRepository.existsByEmail(newEmail); // query 전 flush 가능
    if (exists) {
        throw new DuplicateEmailException();
    }
}
```

검증 쿼리 전에 update가 flush되면 unique constraint 충돌이나 쿼리 결과 오염이 생길 수 있다. 좋은 흐름은 검증 순서를 먼저 정리하는 것이다.

```java
@Transactional
public void changeEmail(Long userId, String newEmail) {
    if (userRepository.existsByEmail(newEmail)) {
        throw new DuplicateEmailException();
    }

    User user = userRepository.getById(userId);
    user.changeEmail(newEmail);
}
```

물론 동시성까지 고려하면 unique constraint는 여전히 필요하다.

### flush와 외부 API 호출 순서를 섞지 말라

가장 위험한 패턴은 DB 변경을 persistence context에 쌓아 둔 상태에서 외부 API를 호출하는 것이다.

```java
@Transactional
public void approvePayment(Long orderId) {
    Order order = orderRepository.getById(orderId);
    order.markPaymentRequested();

    PaymentResult result = paymentClient.approve(order.paymentKey()); // 외부 I/O

    order.markPaid(result.approvedAt());
}
```

이 코드에는 여러 문제가 있다.

- transaction이 외부 API 대기 시간만큼 길어진다
- DB lock이 오래 유지될 수 있다
- 외부 결제는 성공했는데 commit이 실패할 수 있다
- timeout/retry가 transaction과 외부 API 양쪽에 걸쳐 복잡해진다
- 재시도 시 결제 중복 승인 위험이 있다

더 안전한 설계는 작업을 단계로 나누는 것이다.

```text
1. DB transaction: 결제 요청 상태와 idempotency key 저장
2. transaction 밖: 결제 API 호출
3. DB transaction: 결제 결과 반영
4. outbox/event: 후속 처리 발행
```

또는 결제 요청 자체를 outbox에 저장하고 worker가 처리한다.

```java
@Transactional
public void requestPayment(Long orderId) {
    Order order = orderRepository.getById(orderId);
    order.markPaymentPending();

    outboxRepository.save(PaymentRequestedEvent.of(order));
}
```

worker는 outbox를 읽어 외부 API를 호출하고, idempotency key로 중복 호출을 흡수하며, 결과를 별도 transaction에서 반영한다.

이 구조는 즉시성은 조금 낮아질 수 있지만 실패 복구와 관측성이 훨씬 좋아진다.

---

## 실무 예시: 주문 생성 트랜잭션을 어떻게 나눌 것인가

온라인 주문 생성 흐름을 예로 들어 보자.

요구사항:

- 사용자가 장바구니 상품을 주문한다
- 재고를 예약한다
- 주문 번호를 생성한다
- 결제 요청을 준비한다
- 주문 생성 이벤트를 발행한다
- 실패 시 중복 주문이 생기면 안 된다
- 결제 API는 외부 시스템이라 느리거나 실패할 수 있다

나쁜 출발점은 모든 것을 한 transaction에 넣는 것이다.

```java
@Transactional
public OrderResponse placeOrder(PlaceOrderCommand command) {
    Order order = orderRepository.save(Order.create(command));
    inventoryService.reserve(command.items());

    PaymentResult payment = paymentClient.approve(command.paymentKey()); // 외부 API
    order.markPaid(payment.approvedAt());

    eventPublisher.publishEvent(new OrderPlacedEvent(order.getId()));
    return OrderResponse.from(order);
}
```

문제점:

- 외부 결제 API 대기 동안 DB transaction이 열린다
- event publish가 commit 전인지 후인지 불명확하다
- 결제 성공 후 commit 실패 시 보상 처리가 어렵다
- event listener가 같은 transaction 안에서 DB를 읽으면 아직 commit 전 상태를 볼 수 있다
- 사용자가 재시도하면 주문과 결제 중복이 생길 수 있다

더 운영 가능한 구조는 다음처럼 나눈다.

```java
@Service
public class OrderApplicationService {
    private final OrderTransactionService orderTransactionService;
    private final PaymentRequester paymentRequester;

    public OrderResponse placeOrder(PlaceOrderCommand command) {
        OrderCreatedResult created = orderTransactionService.createOrder(command);
        paymentRequester.request(created.paymentRequestId());
        return OrderResponse.from(created);
    }
}
```

주문 생성 transaction은 DB 정합성에 집중한다.

```java
@Service
public class OrderTransactionService {

    @Transactional(timeout = 3)
    public OrderCreatedResult createOrder(PlaceOrderCommand command) {
        IdempotencyKey key = IdempotencyKey.of(command.idempotencyKey());

        orderRequestRepository.saveIfAbsent(key);

        Order order = Order.create(command.userId(), command.items());
        orderRepository.save(order);

        inventoryService.reserve(order.getLines());

        PaymentRequest paymentRequest = PaymentRequest.pending(order.getId(), key);
        paymentRequestRepository.save(paymentRequest);

        outboxRepository.save(OrderPlacedEvent.of(order));

        return OrderCreatedResult.of(order, paymentRequest);
    }
}
```

결제 요청은 별도 경계에서 처리한다.

```java
@Service
public class PaymentRequester {

    public void request(Long paymentRequestId) {
        // 동기 호출이 필요하다면 transaction 밖에서 짧은 timeout으로 호출
        PaymentApproval approval = paymentClient.approve(paymentRequestId);
        paymentResultService.recordApproval(paymentRequestId, approval);
    }
}

@Service
public class PaymentResultService {

    @Transactional(timeout = 3)
    public void recordApproval(Long paymentRequestId, PaymentApproval approval) {
        PaymentRequest request = paymentRequestRepository.getById(paymentRequestId);
        request.markApproved(approval);

        Order order = orderRepository.getById(request.orderId());
        order.markPaid(approval.approvedAt());

        outboxRepository.save(PaymentApprovedEvent.of(order));
    }
}
```

이 구조의 핵심은 다음이다.

- DB 변경은 짧은 transaction 안에서 끝낸다
- 외부 API는 DB transaction 밖에서 호출한다
- 외부 API 중복 호출은 idempotency key로 흡수한다
- 이벤트 발행은 outbox에 저장하고 commit 후 dispatcher가 처리한다
- 주문 생성 실패와 결제 승인 실패를 같은 rollback 단위로 억지로 묶지 않는다

트레이드오프도 있다.

- 코드가 더 길어진다
- 상태가 `PENDING_PAYMENT`, `PAID`, `PAYMENT_FAILED`처럼 늘어난다
- 사용자에게 즉시 결제 완료 응답을 줄지, 비동기 처리 상태를 줄지 UX 결정이 필요하다
- outbox dispatcher와 재시도 모니터링이 필요하다

하지만 운영 서비스에서는 이 복잡성이 자주 정당화된다. 외부 시스템을 DB transaction 안에 넣는 단순함은 장애 시 더 큰 비용으로 돌아온다.

---

## 트레이드오프: 짧은 transaction, 강한 정합성, 단순 코드 셋을 모두 얻기는 어렵다

트랜잭션 설계에는 항상 교환비가 있다.

### transaction을 크게 잡으면

장점:

- 코드가 단순하다
- 한 번에 rollback되므로 사고 모델이 쉽다
- 여러 entity 변경을 같은 persistence context에서 다룰 수 있다
- 즉시 일관성을 얻기 쉽다

단점:

- lock 유지 시간이 길어진다
- 외부 I/O가 섞이면 장애 반경이 커진다
- connection 점유 시간이 늘어난다
- timeout과 retry가 어려워진다
- 실패 시 전체 작업 비용이 커진다

### transaction을 작게 나누면

장점:

- lock 범위가 줄어든다
- connection 점유 시간이 짧다
- 외부 시스템 장애와 DB 변경을 분리할 수 있다
- 재시도와 보상 처리를 설계하기 쉽다
- 배치와 worker 확장성이 좋아진다

단점:

- 중간 상태가 생긴다
- 상태 머신과 후속 처리 모니터링이 필요하다
- eventual consistency를 사용자와 운영자가 이해해야 한다
- 중복 처리와 idempotency 설계가 필수다

### isolation을 높이면

장점:

- 일부 동시성 이상 현상을 DB가 막아 준다
- 애플리케이션 코드가 단순해질 수 있다
- 중요한 정합성 구간에서 강한 보장을 얻을 수 있다

단점:

- lock 대기 또는 serialization failure가 늘 수 있다
- retry가 필수가 된다
- transaction을 짧게 유지해야 한다
- 처리량이 떨어질 수 있다

### constraint와 atomic update를 활용하면

장점:

- DB가 강한 정합성 경계를 제공한다
- 애플리케이션 race condition이 줄어든다
- 동시성 테스트가 단순해진다

단점:

- 예외 매핑이 필요하다
- migration과 online schema change를 신중히 해야 한다
- 도메인 규칙이 DB와 코드 양쪽에 흩어질 수 있다

좋은 설계는 "항상 짧은 transaction"이나 "항상 강한 isolation"이 아니다. 데이터의 중요도, 동시성 수준, 외부 시스템 참여 여부, 복구 요구사항에 맞게 실패 단위를 선택하는 것이다.

---

## 흔한 실수: Spring Transaction에서 자주 터지는 운영 사고

### 1. private 메서드에 `@Transactional`을 붙인다

```java
public void run() {
    saveSomething();
}

@Transactional
private void saveSomething() {
    // 적용되지 않는다고 봐야 한다
}
```

proxy 기반 선언적 transaction은 일반적으로 외부 public 호출 경계에서 동작한다. private 메서드에 붙인 어노테이션은 코드 독자에게 잘못된 안정감을 준다.

### 2. 같은 클래스 내부 호출로 propagation이 무시된다

```java
public void outer() {
    innerRequiresNew();
}

@Transactional(propagation = Propagation.REQUIRES_NEW)
public void innerRequiresNew() {
}
```

이 구조는 proxy를 거치지 않기 때문에 의도한 새 transaction이 열리지 않을 수 있다. 별도 bean으로 분리하거나 호출 구조를 바꿔야 한다.

### 3. transaction 안에서 외부 API를 호출한다

DB lock과 connection을 잡은 채 네트워크를 기다리는 것은 운영에서 큰 위험이다. 외부 API는 timeout, retry, idempotency, circuit breaker가 필요하고, DB transaction과 같은 실패 단위로 묶기 어렵다.

### 4. 이벤트를 commit 전에 발행한다

```java
@Transactional
public void createOrder() {
    Order order = orderRepository.save(...);
    applicationEventPublisher.publishEvent(new OrderCreatedEvent(order.getId()));
}
```

listener가 즉시 실행되면 아직 commit되지 않은 데이터를 읽거나, 이후 rollback된 이벤트를 외부로 내보낼 수 있다. 필요한 경우 `@TransactionalEventListener(phase = AFTER_COMMIT)` 또는 outbox를 검토해야 한다.

### 5. `REQUIRES_NEW`로 모든 문제를 덮는다

독립 commit은 강력하지만 connection pool, lock, 데이터 의미를 복잡하게 만든다. 감사 로그처럼 명확한 요구가 있을 때만 쓰고, 반복 호출에서는 pool 사용량을 계산해야 한다.

### 6. checked exception rollback을 잊는다

파일 처리, 외부 SDK, legacy API는 checked exception을 자주 던진다. 해당 예외가 발생했을 때 DB 변경을 유지할지 되돌릴지 명시해야 한다.

### 7. readOnly 조회에서 entity를 수정한다

`readOnly=true`는 "쓰기가 절대 불가능"이라는 보증이 아니다. 조회 메서드에서 상태 변경을 하면 ORM flush mode와 설정에 따라 결과가 달라지고, 코드 의미가 흐려진다.

### 8. 긴 배치를 하나의 transaction으로 묶는다

대량 처리에는 chunk, cursor, paging, checkpoint, 재시작 설계가 필요하다. 하나의 거대한 transaction은 실패 비용과 lock 범위를 키운다.

### 9. DB constraint 없이 애플리케이션 조회로만 중복을 막는다

```java
if (!repository.existsByEmail(email)) {
    repository.save(new User(email));
}
```

동시 요청에서는 둘 다 `false`를 보고 저장할 수 있다. unique constraint와 예외 매핑이 필요하다.

### 10. transaction timeout과 query timeout을 맞추지 않는다

transaction timeout만 설정하고 JDBC statement timeout, DB lock timeout, connection pool timeout이 비어 있으면 대기 예산이 실제로 지켜지지 않을 수 있다.

---

## 테스트 전략: transaction 코드는 happy path보다 경쟁과 실패를 검증해야 한다

트랜잭션 코드는 단위 테스트만으로 충분하지 않다. 특히 JPA, DB constraint, lock, isolation, propagation은 실제 DB와 붙여야 의미가 드러난다.

### rollback 규칙 테스트

checked exception이 rollback되는지 확인한다.

```java
@Test
void importUsers_rollsBackOnIOException() {
    assertThatThrownBy(() -> userImportService.importUsers(brokenFile))
            .isInstanceOf(IOException.class);

    assertThat(userRepository.count()).isZero();
}
```

### propagation 테스트

감사 로그가 본 transaction rollback과 독립적으로 남아야 한다면 그 요구를 테스트한다.

```java
@Test
void auditLog_commitsEvenWhenBusinessTransactionRollsBack() {
    assertThatThrownBy(() -> roleService.changeRoleWithFailure(command))
            .isInstanceOf(RuntimeException.class);

    assertThat(userRepository.findById(command.userId()).get().role())
            .isEqualTo(originalRole);
    assertThat(auditLogRepository.findByUserId(command.userId()))
            .isNotEmpty();
}
```

### 동시성 테스트

동일 쿠폰 사용, 재고 차감, 계좌 이체 같은 코드는 동시에 실행해 봐야 한다.

```java
@Test
void couponCanBeUsedOnlyOnceUnderConcurrency() throws Exception {
    int threads = 20;
    ExecutorService executor = Executors.newFixedThreadPool(threads);
    CountDownLatch ready = new CountDownLatch(threads);
    CountDownLatch start = new CountDownLatch(1);

    List<Future<CouponUseResult>> futures = new ArrayList<>();
    for (int i = 0; i < threads; i++) {
        futures.add(executor.submit(() -> {
            ready.countDown();
            start.await();
            return couponService.use(couponId, userId);
        }));
    }

    ready.await();
    start.countDown();

    long successCount = futures.stream()
            .map(this::getUnchecked)
            .filter(CouponUseResult::success)
            .count();

    assertThat(successCount).isOne();
}
```

이런 테스트는 느리고 까다롭다. 하지만 중요한 정합성 규칙에는 가치가 있다. 가능하면 Testcontainers로 운영 DB와 가까운 환경에서 검증한다.

### commit 후 이벤트 테스트

outbox나 `AFTER_COMMIT` listener는 rollback 상황에서 이벤트가 나가지 않는지 확인해야 한다.

```java
@Test
void eventIsNotPublishedWhenTransactionRollsBack() {
    assertThatThrownBy(() -> orderService.createOrderWithFailure(command))
            .isInstanceOf(RuntimeException.class);

    assertThat(outboxRepository.findAll()).isEmpty();
}
```

---

## 체크리스트: `@Transactional`을 붙이기 전에 확인할 것

### 작업 단위

- 이 메서드는 하나의 비즈니스 작업 단위인가
- 함께 commit되어야 하는 변경과 따로 처리되어야 하는 작업을 구분했는가
- 외부 API, 메시지 발행, 파일 I/O가 transaction 안에 들어가 있지 않은가
- 중간 상태가 생긴다면 상태 이름과 복구 경로가 명확한가

### propagation

- 기본값 `REQUIRED`로 충분한가
- `REQUIRES_NEW`를 쓴다면 독립 commit이 실제 요구사항인가
- 반복문 안에서 `REQUIRES_NEW`를 호출해 connection pool을 압박하지 않는가
- self-invocation으로 transaction advice가 빠지는 곳은 없는가
- private/final 메서드에 어노테이션을 붙여 잘못된 기대를 만들지 않았는가

### isolation과 constraint

- 동시성 이상 현상이 실제로 어떤 형태로 가능한지 설명할 수 있는가
- unique constraint, foreign key, check constraint, optimistic lock을 활용했는가
- isolation level을 올렸다면 lock/abort/retry 비용을 감당할 수 있는가
- `SERIALIZABLE` 또는 lock 기반 코드는 재시도 정책이 있는가

### rollback

- checked exception 발생 시 rollback 여부를 명시했는가
- catch한 예외가 transaction을 rollback-only로 만든 상태는 아닌가
- 비즈니스 예외와 시스템 예외의 의미가 분리되어 있는가
- 중복 요청, 이미 처리된 요청은 예외가 아니라 idempotent 성공으로 매핑할 수 있는가

### readOnly와 JPA

- 조회 메서드에 `readOnly=true`를 붙이고 쓰기를 섞지 않았는가
- 필요한 lazy association을 transaction 안에서 명시적으로 로딩했는가
- OSIV에 기대어 view/controller에서 SQL이 나가지 않는가
- query 전 자동 flush로 검증 순서가 꼬이지 않는가

### timeout과 운영

- transaction timeout, JDBC query timeout, DB lock timeout, connection pool timeout이 정렬되어 있는가
- 긴 batch는 chunk 단위 transaction으로 나뉘어 있는가
- timeout 후 재시도 가능한 작업과 재시도하면 안 되는 작업을 구분했는가
- lock wait, deadlock, serialization failure를 관측하고 알림 받을 수 있는가

### 이벤트와 후속 처리

- commit 전 이벤트와 commit 후 이벤트를 구분했는가
- 외부 메시지 브로커 발행이 DB commit과 원자적이지 않다는 점을 고려했는가
- outbox가 필요할 정도로 이벤트 유실이 치명적인가
- 후속 worker가 idempotent하게 재처리할 수 있는가

---

## 한줄정리

Spring Transaction을 운영에서 잘 쓰려면 `@Transactional`을 붙이는 위치보다 **무엇을 같은 실패 단위로 묶고, 무엇을 transaction 밖으로 밀어내며, propagation·isolation·rollback·timeout·readOnly·proxy 경계를 어떤 계약으로 고정할지**를 먼저 설계해야 한다.
