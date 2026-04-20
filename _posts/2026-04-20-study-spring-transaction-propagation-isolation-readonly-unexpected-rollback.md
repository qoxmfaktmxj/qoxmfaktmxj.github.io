---
layout: post
title: "Spring 트랜잭션 전파 실전: @Transactional, REQUIRES_NEW, UnexpectedRollbackException, readOnly를 운영 기준으로 이해하기"
date: 2026-04-20 11:40:00 +0900
categories: [java]
tags: [study, java, spring, spring-boot, transaction, transactional, propagation, isolation, readonly, backend, operations]
permalink: /java/2026/04/20/study-spring-transaction-propagation-isolation-readonly-unexpected-rollback.html
---

## 배경: `@Transactional`을 오래 써도 운영에서 계속 사고가 나는 이유

Spring 백엔드에서 `@Transactional`은 너무 익숙해서 오히려 위험하다. 대부분의 팀은 아래 정도만 기억한다.

- 서비스 메서드에 `@Transactional`을 붙인다
- 예외가 나면 롤백된다
- 조회는 `readOnly = true`를 붙이면 좋다
- 분리하고 싶으면 `REQUIRES_NEW`를 쓴다

여기까지만 알고 있어도 CRUD는 돌아간다. 문제는 운영 이슈가 CRUD보다 훨씬 복잡하다는 점이다.

실제 장애는 보통 이런 형태로 온다.

- 주문 저장은 롤백됐는데 감사 로그는 남아 있다
- 내부 메서드에 `@Transactional`을 붙였는데 전혀 먹지 않는다
- 예외를 잡아서 삼켰는데 마지막에 `UnexpectedRollbackException`이 터진다
- `readOnly = true`를 붙였는데도 update SQL이 나가거나 락이 걸린다
- 외부 결제 승인 호출까지 하나의 트랜잭션에 넣었다가 DB 커넥션과 락이 과도하게 묶인다
- 배치 작업에서 `REQUIRES_NEW`를 남발했다가 connection pool이 바닥난다
- 분명 isolation을 올렸다고 생각했는데 실제로는 외부 트랜잭션 설정에 참여하면서 무시된다

이 문제들의 공통점은 하나다.

> `@Transactional`을 애노테이션 한 줄이 아니라 **트랜잭션 경계 설계 도구**로 보지 않았다는 것.

중급 이상 개발자라면 최소한 아래 질문에는 자신 있게 답할 수 있어야 한다.

1. 지금 내가 만든 트랜잭션은 물리적으로 몇 개인가
2. 이 메서드 호출은 프록시를 통과하는가, 아니면 자기 자신을 직접 부르는가
3. 내부 예외를 잡아도 최종 커밋이 가능한가, 아니면 이미 rollback-only 상태인가
4. `REQUIRES_NEW`, `NESTED`, `REQUIRED` 중 어떤 것이 정말 필요한가
5. `readOnly`, `timeout`, `isolation`은 새 트랜잭션을 만들 때와 기존 트랜잭션에 참여할 때 의미가 어떻게 다른가
6. 외부 API 호출, 메시지 발행, DB 저장을 한 덩어리로 묶는 것이 왜 자주 잘못된가

이 글은 Spring Framework / Spring Boot 기반 애플리케이션을 기준으로, 트랜잭션 전파와 롤백 규칙을 **운영 관점**에서 정리한다. 단순 문법 설명보다, 실제로 어디서 사고가 나는지와 어떤 기준으로 경계를 나눠야 하는지를 중심으로 본다.

---

## 먼저 큰 그림: 트랜잭션은 "코드 블록"이 아니라 "정합성을 보장할 범위"다

트랜잭션을 설명할 때 흔히 ACID부터 시작하지만, 실무에서 더 중요한 질문은 이거다.

> **어디까지를 하나의 실패 단위로 묶을 것인가?**

예를 들어 주문 생성 유스케이스를 생각해 보자.

- 주문 테이블 insert
- 주문 아이템 insert
- 재고 차감
- 감사 로그 저장
- 외부 결제 승인 호출
- Kafka 이벤트 발행
- 알림 발송

모든 단계를 하나의 메서드에 넣고 `@Transactional`을 붙이면 왠지 안전해 보인다. 하지만 실제로는 다음이 섞여 있다.

- **같은 데이터베이스 안에서 함께 커밋/롤백돼야 하는 작업**
- **실패해도 본 요청 성공과 분리 가능한 작업**
- **DB 트랜잭션과 원자적으로 묶을 수 없는 외부 작업**

즉 트랜잭션의 핵심은 범위를 넓히는 것이 아니라, **같이 망가져야 하는 것만 묶는 것**이다.

좋은 트랜잭션 설계는 보통 아래 순서를 따른다.

1. 도메인 정합성에 반드시 필요한 DB 변경만 같은 트랜잭션으로 묶는다
2. 부가 기록, 통계, 감사, 후처리는 필요시 별도 트랜잭션이나 비동기 후속 단계로 분리한다
3. 외부 시스템 호출은 가능하면 DB 락 구간 밖으로 뺀다
4. 메시지 발행은 outbox 같은 패턴으로 정합성을 보강한다

이 큰 그림 없이 propagation만 외우면, `REQUIRES_NEW`와 `readOnly`는 문제 해결 도구가 아니라 문제 은폐 도구가 되기 쉽다.

---

## 핵심 개념 1: `@Transactional`은 마법이 아니라 프록시 기반 인터셉션이다

Spring의 기본 트랜잭션 처리는 대개 프록시 기반이다. 즉 트랜잭션은 메서드 본문 안에 숨어 있는 것이 아니라, **프록시가 메서드 진입과 종료를 감싸면서 시작/커밋/롤백을 제어**한다.

이 전제를 놓치면 가장 흔한 함정인 self-invocation에 바로 걸린다.

### self-invocation이 왜 문제인가

```java
@Service
@RequiredArgsConstructor
public class OrderFacade {

    public void placeOrder(PlaceOrderCommand cmd) {
        validate(cmd);
        saveOrder(cmd);
    }

    @Transactional
    public void saveOrder(PlaceOrderCommand cmd) {
        // 주문 저장
    }
}
```

겉보기에는 `placeOrder()` 안에서 `saveOrder()`를 호출하니 트랜잭션이 시작될 것 같지만, 실제로는 같은 객체 내부에서 자기 메서드를 직접 호출한다. 즉 프록시를 통과하지 않는다.

결과는 다음과 같다.

- `saveOrder()`의 `@Transactional`이 적용되지 않을 수 있다
- 테스트에서는 우연히 동작해 보여도 운영에서는 전혀 기대한 경계가 형성되지 않는다
- rollback, timeout, isolation, readOnly 설정이 모두 무시된 것처럼 보일 수 있다

Spring 문서를 오래 본 사람일수록 이 사실을 알고 있다고 생각하지만, 실제 코드 리뷰에서는 여전히 자주 나온다. 이유는 간단하다. 코드가 너무 자연스럽기 때문이다.

### 안전한 패턴

가장 안전한 방법은 트랜잭션 경계를 **별도 빈으로 분리**하는 것이다.

```java
@Service
@RequiredArgsConstructor
public class OrderFacade {
    private final OrderTxService orderTxService;

    public void placeOrder(PlaceOrderCommand cmd) {
        validate(cmd);
        orderTxService.saveOrder(cmd);
    }
}

@Service
public class OrderTxService {

    @Transactional
    public void saveOrder(PlaceOrderCommand cmd) {
        // 주문 저장
    }
}
```

이렇게 하면 외부 호출이 프록시를 지나므로 트랜잭션 인터셉션이 확실해진다.

### 실무 기준

- 유스케이스 진입점과 트랜잭션 경계를 같은 public 메서드에 두는 것이 가장 단순하다
- 내부 helper 메서드에 `@Transactional`을 붙여 동작을 기대하지 않는다
- 정말 self-invocation이 필요하면 설계를 다시 나누는 편이 낫다
- AspectJ weaving 같은 대안이 있지만, 대부분의 팀에서는 운영 복잡도만 올린다

즉 첫 번째 체크포인트는 간단하다.

> 이 호출이 프록시를 통과하지 않으면, 애노테이션은 거의 주석과 비슷해질 수 있다.

---

## 핵심 개념 2: 논리 트랜잭션과 물리 트랜잭션을 구분해야 한다

Spring의 propagation을 이해할 때 가장 많이 빠지는 함정은 "메서드마다 트랜잭션 하나"라고 생각하는 것이다. 실제로는 그렇지 않다.

`REQUIRED` 기준으로는 메서드마다 **논리 트랜잭션 범위**는 생기지만, 실제 DB 커넥션 관점의 **물리 트랜잭션**은 하나일 수 있다.

예를 들어:

```java
@Service
@RequiredArgsConstructor
public class CheckoutService {
    private final OrderService orderService;
    private final InventoryService inventoryService;

    @Transactional
    public void checkout(CheckoutCommand cmd) {
        orderService.createOrder(cmd);
        inventoryService.decreaseStock(cmd);
    }
}
```

```java
@Service
public class OrderService {

    @Transactional
    public void createOrder(CheckoutCommand cmd) {
        // 주문 생성
    }
}
```

```java
@Service
public class InventoryService {

    @Transactional
    public void decreaseStock(CheckoutCommand cmd) {
        // 재고 차감
    }
}
```

세 메서드 모두 `@Transactional`이지만 propagation 기본값이 `REQUIRED`라면, 이미 바깥 `checkout()`에서 시작된 트랜잭션에 참여한다. 즉 물리 트랜잭션은 하나다.

이 점이 중요한 이유는 다음과 같다.

- 내부 서비스 하나가 rollback-only를 걸면 바깥도 결국 커밋할 수 없다
- 내부에서 선언한 isolation, timeout, readOnly가 실제로는 외부 트랜잭션에 묻혀 무시될 수 있다
- 예외를 내부에서 처리했다고 끝나는 문제가 아니다

### rollback-only가 왜 무서운가

어떤 내부 서비스가 예외를 던졌고, 상위 서비스에서 그 예외를 잡아 "그냥 로그만 남기고 계속 진행" 하기로 했다고 하자.

```java
@Transactional
public void checkout(CheckoutCommand cmd) {
    orderService.createOrder(cmd);

    try {
        couponService.useCoupon(cmd.couponId());
    } catch (Exception e) {
        log.warn("쿠폰 사용 실패", e);
    }

    paymentService.requestPayment(cmd);
}
```

만약 `couponService.useCoupon()`이 같은 `REQUIRED` 물리 트랜잭션 안에서 예외를 통해 rollback-only 상태를 만들었다면, 바깥에서 예외를 잡았다고 해도 최종 커밋 시점에 `UnexpectedRollbackException`이 날 수 있다.

이 현상은 이상한 버그가 아니라, 오히려 정직한 동작이다. Spring은 "너는 커밋한다고 생각했지만 실제론 이미 롤백 예정이었다"는 사실을 숨기지 않기 위해 예외를 던진다.

즉 propagation을 이해하지 못하면 다음과 같은 착각을 한다.

- 예외를 잡았으니 괜찮다
- 내부 메서드가 끝났으니 별개다
- 메서드마다 트랜잭션이 따로 있다

실제로는 모두 틀릴 수 있다.

---

## 핵심 개념 3: `REQUIRED`, `REQUIRES_NEW`, `NESTED`는 이름보다 실패 단위가 다르다

Propagation 옵션은 많지만, 실무에서 자주 고민하는 것은 사실 세 가지다.

- `REQUIRED`
- `REQUIRES_NEW`
- `NESTED`

핵심은 문법이 아니라 **실패 전파 방식**이다.

### 1) `REQUIRED`, 기본값이며 대개 가장 좋은 선택

의미는 단순하다.

- 기존 트랜잭션이 있으면 참여한다
- 없으면 새로 시작한다

장점은 다음과 같다.

- 같은 유스케이스 안의 DB 변경을 자연스럽게 하나로 묶기 쉽다
- 서비스 파사드에서 하위 서비스들을 호출하는 일반적인 구조와 잘 맞는다
- 대부분의 비즈니스 로직은 사실 이 기본값이면 충분하다

하지만 단점도 명확하다.

- 내부 한 군데라도 rollback-only가 되면 전체가 영향을 받는다
- 하위 서비스가 독립 실패 단위처럼 보이더라도 실제로는 독립이 아니다
- 설정이 단순해서 오히려 오해가 많다

**추천 기준**

- 주문과 주문아이템 저장처럼 반드시 함께 성공/실패해야 하는 작업
- 하나의 도메인 유스케이스를 구성하는 핵심 쓰기 경로
- 같은 DB 정합성 범위 안에 있는 상태 전이

### 2) `REQUIRES_NEW`, 새 물리 트랜잭션을 강제로 만든다

의미는 명확하다.

- 현재 트랜잭션이 있더라도 잠시 suspend한다
- 별도의 새 물리 트랜잭션을 시작한다
- 안쪽 트랜잭션은 바깥 결과와 독립적으로 커밋/롤백된다

예를 들어 감사 로그를 메인 트랜잭션과 분리하고 싶다면 이렇게 쓸 수 있다.

```java
@Service
public class AuditService {

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void writeAudit(AuditLog auditLog) {
        auditLogRepository.save(auditLog);
    }
}
```

이 패턴은 아래 상황에서 유용하다.

- 메인 비즈니스 저장이 실패하더라도 실패 기록은 남기고 싶다
- 재시도 이력, 에러 로그, 감사 로그를 독립적으로 보존하고 싶다
- 아주 짧고 단순한 보조 쓰기 작업을 별도 단위로 확실히 분리하고 싶다

하지만 여기서부터 운영 냄새가 강하게 난다.

#### `REQUIRES_NEW`의 비용

1. **커넥션을 더 오래 잡을 수 있다**
   바깥 트랜잭션이 보유한 자원 위에 안쪽 새 트랜잭션이 추가로 열린다.

2. **락과 정합성 모델이 복잡해진다**
   안쪽은 이미 커밋됐는데 바깥은 나중에 롤백될 수 있다.

3. **실패 분석이 어려워진다**
   사용자는 요청이 실패했다고 보는데 일부 데이터는 이미 남아 있다.

4. **배치/루프에서 남발하면 pool 압박이 심해진다**
   아이템 N개를 돌며 매번 `REQUIRES_NEW`를 열면 처리량과 안정성이 동시에 흔들린다.

즉 `REQUIRES_NEW`는 "안전한 분리"가 아니라, **정말로 따로 커밋돼도 되는 데이터만 분리**할 때 써야 한다.

#### 추천 사용처

- 감사 로그, 실패 이력, 운영 진단 로그
- 재처리 큐 적재처럼 본 작업과 분리된 후속 처리 기록
- 외부 정산 테이블 등 별도 보존이 필요한 아주 제한적인 쓰기

#### 피해야 할 사용처

- 본 도메인 정합성의 일부인 핵심 상태 변경
- 단순히 `UnexpectedRollbackException`을 피하고 싶어서
- 성능 문제 원인을 모른 채 "일단 쪼개보자" 식으로

### 3) `NESTED`, savepoint 기반 부분 롤백이지만 생각보다 제약이 많다

`NESTED`는 기존 트랜잭션 안에서 savepoint를 만들어 일부만 롤백할 수 있게 해준다.

개념적으로는 매력적이다.

- 바깥 큰 트랜잭션은 유지한다
- 안쪽 실패 구간만 savepoint까지 되돌린다
- 전부 별도 커밋되는 `REQUIRES_NEW`보다 덜 과감해 보인다

하지만 현실에서는 주의가 많다.

- 보통 JDBC 기반 `DataSourceTransactionManager`에서 주로 의미가 있다
- JPA 환경에서는 기대한 대로 동작하지 않거나, 팀원이 이해하기 어렵다
- savepoint를 전제로 하므로 DB와 트랜잭션 매니저 지원 여부를 봐야 한다
- 운영 팀 전체가 의미를 정확히 공유하지 못하면 코드를 읽기 어려워진다

대부분의 서비스 애플리케이션에서는 `NESTED`가 문제를 단순화하기보다 오히려 복잡성을 올린다. 그래서 특별한 이유가 없다면 `REQUIRED` 또는 아예 별도 후처리 설계로 해결하는 편이 낫다.

### 빠른 판단 기준

- **같이 커밋/롤백돼야 한다** → `REQUIRED`
- **따로 커밋돼도 된다. 실패 이력이나 감사처럼 독립 의미가 있다** → `REQUIRES_NEW`
- **부분 롤백을 savepoint로 다뤄야 하는 JDBC 특수 시나리오다** → 정말 필요할 때만 `NESTED`

Propagation은 우아한 옵션 선택이 아니라, **데이터가 실제로 어떻게 남아도 되는지에 대한 의사결정**이다.

---

## 핵심 개념 4: `readOnly`, `timeout`, `isolation`은 새 트랜잭션을 만들 때와 참여할 때 의미가 다르다

트랜잭션 속성을 설명하는 문서는 많지만, 실무에서 자주 헷갈리는 핵심은 이 부분이다.

> 기존 트랜잭션에 참여할 때는, 내가 선언한 속성이 반드시 독립적으로 적용되는 것이 아니다.

Spring 문서에서도 기본 `REQUIRED` 참여 시에는 바깥 트랜잭션 특성에 합류하며, 안쪽의 isolation/readOnly/timeout 설정은 기대한 대로 독립 적용되지 않을 수 있다고 본다.

### 1) `readOnly = true`는 만능 최적화도, 쓰기 방지 보장도 아니다

많은 팀이 `readOnly = true`를 아래 둘 중 하나로 과대해석한다.

- 이걸 붙이면 무조건 성능이 좋아진다
- 이걸 붙이면 write가 절대 불가능하다

둘 다 과장이다.

실제로 `readOnly = true`의 의미는 사용하는 트랜잭션 매니저, JPA 구현체, JDBC 드라이버, DB 종류에 따라 다르게 나타난다.

보통은 이런 효과를 기대할 수 있다.

- Hibernate flush 전략이 보수적으로 바뀌어 불필요한 dirty checking 비용을 줄일 수 있다
- DB 드라이버나 커넥션에 read-only 힌트를 줄 수 있다
- 코드 의도를 명확하게 드러낼 수 있다

하지만 다음을 절대 보장하지는 않는다.

- 모든 DB에서 물리적 쓰기 금지
- 모든 SQL 락 회피
- 언제나 눈에 띄는 성능 향상

특히 더 위험한 오해는 이것이다.

```java
@Transactional(readOnly = true)
public OrderSummary getOrderSummary(Long orderId) {
    Order order = orderRepository.findById(orderId).orElseThrow();
    order.markAsViewed();
    return OrderSummary.from(order);
}
```

이 코드는 읽기 메서드처럼 보여도, 엔티티 상태를 바꾸고 있다. 어떤 환경에서는 flush가 안 돼서 "운 좋게" 반영되지 않을 수 있고, 어떤 환경에서는 여전히 변경이 반영되거나 예상치 못한 부작용이 생길 수 있다.

즉 `readOnly = true`는 안전장치 이전에 **설계 선언**이다. 읽기 메서드에서 상태 변경 코드를 쓰지 않는 것이 먼저다.

### 2) isolation은 "내 메서드 선언"보다 "실제 시작된 물리 트랜잭션"이 중요하다

아래 코드를 보자.

```java
@Transactional
public void settle() {
    reportService.readCurrentState();
}
```

```java
@Transactional(isolation = Isolation.SERIALIZABLE)
public void readCurrentState() {
    // 조회
}
```

겉보기에는 `readCurrentState()`에 더 강한 isolation이 걸릴 것 같지만, 이미 바깥에서 `REQUIRED` 트랜잭션이 시작돼 있다면 안쪽은 그 트랜잭션에 참여할 가능성이 크다. 즉 안쪽 선언 isolation이 독립 적용되지 않을 수 있다.

이걸 모르고 있으면 "분명 SERIALIZABLE로 올렸는데 왜 그대로지?" 같은 착각을 한다.

### 3) timeout도 참여 시에는 기대와 다를 수 있다

긴 루프나 외부 호출이 있는 메서드에서 아래처럼 설정하는 경우가 있다.

```java
@Transactional(timeout = 3)
public void saveAudit() {
    // ...
}
```

그런데 이 메서드가 이미 열린 바깥 트랜잭션에 참여한다면, timeout 역시 별개로 강제되지 않을 수 있다. 결국 진짜 중요한 것은 속성 값을 외우는 게 아니라, **이 메서드가 새 물리 트랜잭션을 여는지**를 먼저 보는 것이다.

### `validateExistingTransactions`를 고려할 상황

팀이 isolation/readOnly 불일치를 민감하게 다뤄야 한다면, 트랜잭션 매니저의 `validateExistingTransactions` 설정을 통해 기존 트랜잭션 참여 시 불일치를 더 엄격하게 잡을 수 있다. 디폴트는 대체로 관대한 편이므로, 설정하지 않으면 안쪽 선언이 조용히 무시된 것처럼 보일 수 있다.

다만 이 설정은 기존 코드베이스와 충돌할 수 있으니, 도입 전에 호출 체인 전체를 한번 점검해야 한다.

---

## 핵심 개념 5: 롤백 규칙은 "예외를 던졌느냐"보다 "트랜잭션이 어떤 상태가 되었느냐"가 중요하다

Spring 트랜잭션을 처음 배울 때는 보통 이렇게 외운다.

- RuntimeException이면 롤백
- Checked Exception이면 기본적으로 롤백 아님
- 필요하면 `rollbackFor` 지정

이 규칙은 출발점으로는 맞다. 하지만 운영 문제는 여기서 끝나지 않는다.

### 1) 예외를 잡아도 rollback-only는 남을 수 있다

가장 자주 보는 케이스다.

```java
@Transactional
public void register(RegisterCommand cmd) {
    memberService.create(cmd);

    try {
        couponService.issueWelcomeCoupon(cmd.memberId());
    } catch (Exception e) {
        log.warn("쿠폰 발급 실패", e);
    }

    notificationService.enqueue(cmd.memberId());
}
```

개발자는 보통 이렇게 생각한다.

- 쿠폰 발급 실패는 부가 기능이니까 무시
- 예외를 잡았으니 메인 회원 가입은 커밋 가능

하지만 `couponService.issueWelcomeCoupon()`이 같은 `REQUIRED` 물리 트랜잭션 안에서 rollback-only를 건 상태라면, 마지막 커밋 시점에 `UnexpectedRollbackException`이 발생할 수 있다.

즉 핵심은 "내가 catch 했는가"가 아니라, **트랜잭션 매니저가 이 물리 트랜잭션을 이미 커밋 불가로 판단했는가**다.

### 2) `UnexpectedRollbackException`은 버그가 아니라 경고음이다

이 예외를 없애기 위해 대충 `REQUIRES_NEW`를 붙이거나, try-catch 위치만 바꾸는 경우가 많다. 하지만 먼저 해석해야 한다.

이 예외는 보통 아래 메시지를 전달한다.

- 내부 어딘가에서 이미 전체 롤백이 예정됐다
- 그런데 바깥 호출자는 여전히 커밋될 거라고 생각했다
- 그 오해를 그냥 넘어가면 데이터 정합성을 더 헷갈리게 만든다

즉 이 예외는 불편하지만 고마운 신호다. 시스템이 "너 지금 경계를 잘못 이해하고 있다"고 알려주는 것이다.

### 3) checked exception을 비즈니스 실패로 쓰는 팀이라면 rollback 규칙을 명시해야 한다

예를 들어 재고 부족, 중복 결제, 쿠폰 만료 같은 비즈니스 실패를 checked exception으로 설계한 팀이라면 기본 규칙만 믿고 가면 롤백이 안 될 수 있다.

```java
@Transactional(rollbackFor = OutOfStockException.class)
public void reserveStock(Long productId, int quantity) throws OutOfStockException {
    // ...
}
```

하지만 여기서 중요한 것은 checked/unchecked 선택보다도, 팀 전체의 실패 모델을 일관되게 가져가는 것이다.

실무에서는 보통 다음 둘 중 하나로 정리하는 편이 낫다.

- 도메인 실패도 RuntimeException 계열로 통일한다
- checked exception을 유지하되 rollback 정책을 매우 명시적으로 관리한다

둘을 섞으면 코드 리뷰 난이도가 급격히 올라간다.

### 4) 롤백 규칙보다 더 중요한 것은 "외부 부작용 시점"이다

트랜잭션이 롤백돼도 이미 발생한 외부 효과는 되돌릴 수 없다.

- 결제 승인 API 호출
- 이메일 발송
- Slack 알림 전송
- Kafka에 이미 발행된 메시지

즉 rollback 규칙을 정교하게 다뤄도, 외부 부작용을 트랜잭션 안에 잘못 넣으면 여전히 모호한 상태가 생긴다. 그래서 다음 섹션이 중요하다.

---

## 핵심 개념 6: DB 트랜잭션과 외부 시스템 호출은 같은 원자성으로 묶이지 않는다

많은 팀이 처음에는 이렇게 구현한다.

```java
@Transactional
public void approvePayment(ApprovePaymentCommand cmd) {
    Payment payment = paymentRepository.findById(cmd.paymentId()).orElseThrow();
    payment.markApproving();

    gatewayClient.approve(cmd);

    payment.markApproved();
    outboxRepository.save(PaymentApprovedEvent.from(payment));
}
```

겉보기에는 그럴듯하다. 하지만 실제로는 위험 구간이 많다.

- DB 트랜잭션이 열린 채로 외부 네트워크를 기다린다
- 외부 승인 성공 후 DB 커밋 전에 장애가 나면 사용자는 실패로 보고 실제로는 승인된 상태가 된다
- 재시도 시 중복 승인 위험이 생긴다
- DB 락과 커넥션 점유 시간이 늘어 전체 처리량이 떨어진다

### 더 나은 기준

1. **외부 호출은 가능하면 짧은 DB 트랜잭션 밖에서 수행한다**
2. **멱등성 키를 도입한다**
3. **DB 저장과 메시지 발행은 outbox로 연결한다**
4. **상태 머신을 명시한다**

예를 들어 결제라면 아래 흐름이 더 현실적이다.

- 트랜잭션 1: 결제 요청을 `PENDING`으로 저장, 멱등 키 발급
- 트랜잭션 종료
- 외부 PG 승인 호출
- 트랜잭션 2: 승인 결과를 반영, `APPROVED` 또는 `FAILED`로 전이
- 같은 트랜잭션에서 outbox 적재
- 비동기 발행기가 outbox를 읽어 메시지 전달

이 방식은 코드가 조금 길어지지만, 다음을 얻는다.

- DB 락 구간 축소
- 외부 실패와 내부 롤백의 경계를 명확히 분리
- 재시도 설계 가능
- 장애 복구 절차 문서화 가능

트랜잭션 전파를 잘 이해하는 팀은 보통 여기까지 같이 본다. propagation 자체보다 더 중요한 것은 **원자적으로 묶을 수 없는 작업을 억지로 한 메서드에 넣지 않는 것**이다.

---

## 핵심 개념 7: 읽기 전용 조회도 락, flush, N+1, 지연 로딩 때문에 느려질 수 있다

`readOnly = true`가 붙은 조회 메서드는 안전하고 가볍다고 생각하기 쉽다. 하지만 읽기 경로도 트랜잭션 설계를 잘못하면 느려지고, 심지어 쓰기 경로와 충돌한다.

### 흔한 오해 1: 조회 메서드는 트랜잭션이 없어도 무조건 낫다

JPA에서는 조회 후 지연 로딩이 이어질 수 있고, 일관된 읽기 스냅샷이 필요한 경우도 있다. 그래서 읽기에도 트랜잭션이 의미 있는 경우가 많다.

예를 들어:

- 같은 요청 안에서 연관 엔티티를 안정적으로 탐색해야 한다
- Open Session In View를 끄고 서비스 계층에서 DTO를 조립한다
- 조회 도중 lazy initialization 예외를 피하고 싶다

다만 중요한 것은 조회 트랜잭션을 길게 끌지 않는 것이다. readOnly 조회 안에서 외부 API 호출, 대용량 변환, 파일 생성까지 같이 해버리면 결국 커넥션을 오래 잡게 된다.

### 흔한 오해 2: readOnly 조회는 락과 무관하다

DB 엔진과 쿼리 형태에 따라 읽기 쿼리도 락 경쟁의 일부가 될 수 있다. 특히 아래 상황은 readOnly 선언과 무관하게 부담이 커진다.

- 불필요하게 긴 트랜잭션 동안 cursor나 리소스를 붙잡는 경우
- `SELECT ... FOR UPDATE` 같은 락킹 조회를 섞는 경우
- 대형 조인과 정렬로 temp 공간과 I/O를 많이 쓰는 경우
- replica가 아닌 primary에 집중되는 경우

즉 readOnly는 힌트일 뿐, **느린 조회를 빠르게 만들어 주는 마법 스위치가 아니다.**

### 흔한 오해 3: 조회 메서드 안의 엔티티 변경은 "어차피 반영 안 되겠지"

이 생각이 특히 위험하다. 환경에 따라 우연히 반영되지 않을 수는 있어도, 그 우연에 기대면 안 된다. 조회 서비스와 상태 변경 서비스를 명확히 분리하는 것이 가장 안전하다.

---

## 실무 예시: 주문 생성, 감사 로그, 아웃박스, 외부 결제를 어떻게 나눌까

이제 조금 더 현실적인 예시로 보자. 요구사항은 이렇다.

- 주문과 주문아이템은 반드시 함께 저장돼야 한다
- 재고 차감도 주문과 같은 실패 단위다
- 감사 로그는 주문 실패 여부와 무관하게 남으면 좋다
- 외부 결제 승인은 DB 트랜잭션에 오래 묶고 싶지 않다
- 주문 생성 성공 시 이벤트를 발행해야 한다

### 나쁜 예시: 모든 걸 하나에 밀어 넣기

```java
@Transactional
public void placeOrder(PlaceOrderCommand cmd) {
    Order order = orderRepository.save(Order.create(cmd));
    inventoryService.decrease(cmd.items());
    auditRepository.save(AuditLog.orderRequested(order.getId()));

    paymentGateway.approve(cmd.payment());

    kafkaTemplate.send("order.created", order.getId());
}
```

문제는 명확하다.

- 감사 로그는 메인 롤백과 함께 사라진다
- 외부 결제 호출 동안 DB 트랜잭션이 열려 있다
- Kafka 발행과 DB 커밋은 원자적으로 묶이지 않는다
- 커밋 실패 후 이미 이벤트가 나갔을 수 있다

### 더 나은 분리

#### 1단계, 핵심 도메인 저장만 한 트랜잭션으로 묶기

```java
@Service
@RequiredArgsConstructor
public class OrderCommandService {
    private final OrderRepository orderRepository;
    private final InventoryService inventoryService;
    private final OutboxRepository outboxRepository;

    @Transactional
    public Long createPendingOrder(PlaceOrderCommand cmd) {
        Order order = Order.createPending(cmd.customerId(), cmd.items(), cmd.totalAmount());
        orderRepository.save(order);

        inventoryService.decrease(cmd.items());

        outboxRepository.save(OutboxMessage.orderCreated(order.getId()));
        return order.getId();
    }
}
```

여기서는 같은 DB 안에서 함께 성공/실패해야 하는 것만 묶었다.

- 주문 저장
- 재고 차감
- outbox 적재

#### 2단계, 감사 로그는 독립 트랜잭션으로 분리

```java
@Service
@RequiredArgsConstructor
public class AuditLogService {
    private final AuditLogRepository auditLogRepository;

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void writeOrderRequested(Long orderId, String actor) {
        auditLogRepository.save(AuditLog.orderRequested(orderId, actor));
    }

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void writeOrderFailed(String reason, String actor) {
        auditLogRepository.save(AuditLog.orderFailed(reason, actor));
    }
}
```

여기서 감사 로그는 메인 정합성의 일부가 아니라 운영 추적 수단이다. 그래서 독립 커밋을 허용할 수 있다.

#### 3단계, 외부 결제는 메인 DB 트랜잭션 밖에서 처리

```java
@Service
@RequiredArgsConstructor
public class OrderFacade {
    private final OrderCommandService orderCommandService;
    private final OrderPaymentService orderPaymentService;
    private final AuditLogService auditLogService;

    public void placeOrder(PlaceOrderCommand cmd, String actor) {
        Long orderId = orderCommandService.createPendingOrder(cmd);
        auditLogService.writeOrderRequested(orderId, actor);

        try {
            orderPaymentService.approve(orderId, cmd.payment());
        } catch (Exception e) {
            auditLogService.writeOrderFailed(e.getMessage(), actor);
            throw e;
        }
    }
}
```

#### 4단계, 결제 결과 반영은 다시 짧은 트랜잭션으로

```java
@Service
@RequiredArgsConstructor
public class OrderPaymentService {
    private final OrderRepository orderRepository;
    private final OutboxRepository outboxRepository;
    private final PaymentGateway paymentGateway;

    public void approve(Long orderId, PaymentCommand paymentCommand) {
        PaymentResult result = paymentGateway.approve(paymentCommand);
        markApproved(orderId, result.approvalKey());
    }

    @Transactional
    public void markApproved(Long orderId, String approvalKey) {
        Order order = orderRepository.findById(orderId).orElseThrow();
        order.markApproved(approvalKey);
        outboxRepository.save(OutboxMessage.orderApproved(orderId, approvalKey));
    }
}
```

이 구조의 장점은 아래와 같다.

- DB 트랜잭션이 네트워크 왕복 시간에 묶이지 않는다
- 주문 생성과 재고 차감의 정합성은 유지된다
- 결제 성공/실패 전이가 명확하다
- 이벤트 발행은 outbox로 따라가므로 커밋 이후 비동기 발행이 가능하다
- 감사 로그는 독립 보존된다

### 트레이드오프도 분명하다

- 코드가 단순 CRUD보다 길어진다
- 상태 전이와 재처리 로직이 필요하다
- 모니터링 지표가 더 많아져야 한다

하지만 운영 서비스는 결국 이 복잡도를 어디선가 치른다. 초반 코드 단순성을 택하면, 나중에는 장애 분석과 수동 복구로 더 큰 비용을 낸다.

---

## Isolation 실무 판단: 숫자만 올리면 안전해지는 것이 아니다

트랜잭션 격리 수준은 보통 데이터베이스 과목에서 배우는 내용처럼 들리지만, 실제로는 성능과 일관성의 교환이다.

### `READ_COMMITTED`가 여전히 기본인 이유

대부분의 OLTP 서비스는 기본 격리 수준으로도 충분하다. 이유는 아래와 같다.

- 락 경쟁과 처리량 사이의 균형이 좋다
- 애플리케이션 레벨의 유니크 제약, 조건부 업데이트, 버전 컬럼으로 많은 문제를 해결할 수 있다
- 높은 isolation은 단순한 안전장치가 아니라 비용 증가 수단이기도 하다

### 격리 수준보다 먼저 봐야 할 것

동시성 문제를 만나면 바로 isolation을 올리기 전에 아래를 먼저 본다.

1. 유니크 인덱스로 해결 가능한가
2. `where status = 'PENDING'` 같은 조건부 update로 원자적 전이가 가능한가
3. optimistic locking 버전 컬럼으로 해결 가능한가
4. 아예 작업 큐나 선점 테이블 구조를 바꾸는 것이 나은가

예를 들어 재고 감소는 아래처럼 애플리케이션 조건식으로도 많이 해결한다.

```sql
update inventory
set quantity = quantity - :qty
where product_id = :productId
  and quantity >= :qty;
```

영향받은 row 수가 0이면 재고 부족으로 처리한다. 이런 방식은 격리 수준을 무작정 올리는 것보다 운영 친화적일 때가 많다.

### `SERIALIZABLE`은 마지막 카드에 가깝다

정말 강한 일관성이 필요한 경우가 아니면 `SERIALIZABLE`은 비용이 크다.

- 동시성 저하
- 재시도 증가
- 락/충돌 분석 복잡화
- 트래픽 증가 시 처리량 급감 가능성

즉 isolation은 "제일 센 값으로"가 아니라, **현재 문제를 가장 작은 비용으로 막는 수준**을 고르는 것이다.

---

## `REQUIRES_NEW`가 필요한 진짜 상황과, 사실은 설계 냄새인 상황

이 옵션은 실무에서 아주 자주 오용된다. 그래서 분리해서 보자.

### 진짜 필요한 경우

#### 1) 감사 로그와 실패 이력

메인 비즈니스가 롤백돼도 운영 추적은 남아야 한다면 독립 커밋이 의미 있다.

#### 2) 재처리 큐 적재

어떤 실패를 별도 워커가 회수해야 하고, 본 요청의 성공/실패와 분리해 저장해야 한다면 쓸 수 있다.

#### 3) 관리성 메타데이터

운영 상태 추적, 배치 실행 이력, dead-letter 기록처럼 "남는 것 자체"가 목적일 때.

### 사실은 냄새인 경우

#### 1) `UnexpectedRollbackException`을 숨기기 위해

문제의 원인은 경계 설계인데, 이를 이해하지 않고 안쪽만 새 트랜잭션으로 빼면 부분 커밋이 늘어난다.

#### 2) 복잡한 유스케이스를 메서드 쪼개기로 해결하려고

핵심 상태 변경이 여러 `REQUIRES_NEW`로 나뉘면 전체 정합성 모델이 깨진다.

#### 3) 성능 최적화라고 착각해서

짧은 트랜잭션이 좋아 보인다고 무조건 `REQUIRES_NEW`를 쓰면 오히려 커넥션 사용량과 커밋 횟수만 늘어난다.

#### 4) 루프 안에서 대량 호출

```java
for (Item item : items) {
    auditService.write(item); // REQUIRES_NEW
}
```

이 패턴은 아주 쉽게 병목이 된다. 대량 적재라면 배치 insert, 비동기 큐, 묶음 처리 같은 대안이 먼저다.

---

## 흔한 실수 1: 컨트롤러에서 시작한 트랜잭션 안에 외부 API를 넣는다

이건 생각보다 많이 본다.

```java
@Transactional
public PaymentResponse pay(PaymentRequest request) {
    Order order = orderRepository.findById(request.orderId()).orElseThrow();
    PaymentResult result = pgClient.approve(request);
    order.markPaid(result.approvalId());
    return PaymentResponse.success(order.getId());
}
```

문제는 다음과 같다.

- PG가 느리면 DB 커넥션과 락이 오래 유지된다
- 외부 승인 성공 후 커밋 실패 시 중간 상태가 된다
- 타임아웃과 재시도 설계가 꼬인다

**대안**

- 선저장 후 외부 호출
- 멱등 키 부여
- 결과 반영 트랜잭션 분리
- 보상/재처리 루틴 준비

---

## 흔한 실수 2: 조회 서비스에 `readOnly = true`만 붙이고 상태 변경을 몰래 넣는다

코드 리뷰에서 보이면 바로 고치는 편이 좋다.

```java
@Transactional(readOnly = true)
public UserProfile getProfile(Long userId) {
    User user = userRepository.findById(userId).orElseThrow();
    user.increaseProfileViewCount();
    return UserProfile.from(user);
}
```

왜 나쁜가.

- 읽기/쓰기 책임이 섞인다
- 환경별 flush 차이로 예측이 어려워진다
- 나중에 캐시, replica, CQRS 같은 구조로 확장하기 어렵다

조회 메서드는 조회만 하고, 카운트 증가 같은 쓰기 의도가 필요하면 별도 command로 분리하는 편이 낫다.

---

## 흔한 실수 3: 같은 클래스 안에서 메서드를 나눠 놓고 propagation이 동작한다고 믿는다

이건 앞서 본 self-invocation과 같은 문제다. 특히 아래처럼 많이 쓴다.

```java
@Service
public class SettlementService {

    public void settleAll(List<Long> ids) {
        for (Long id : ids) {
            settleOne(id);
        }
    }

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void settleOne(Long id) {
        // 정산
    }
}
```

`settleAll()`에서 `settleOne()`을 직접 부르면 기대한 새 트랜잭션이 생기지 않을 수 있다. 배치 격리 처리가 목적이면 별도 빈으로 분리하거나, 아예 배치 프레임워크 단위로 chunk/retry/skip을 설계해야 한다.

---

## 흔한 실수 4: 테스트가 통과하니 propagation도 맞다고 믿는다

트랜잭션 관련 버그는 테스트에서 잘 숨어든다.

### 이유

- `@SpringBootTest`나 `@DataJpaTest`가 테스트 자체를 트랜잭션으로 감쌀 수 있다
- 롤백 기본값 때문에 commit 시점 문제를 못 본다
- 테스트에서는 호출 구조가 단순해서 self-invocation을 우연히 안 밟는다
- H2와 실제 운영 DB가 isolation/lock/readOnly를 다르게 해석할 수 있다

### 점검 방법

- commit 이후 드러나는 문제를 보려면 테스트 중간 `flush()` 또는 실제 commit을 유도한다
- propagation을 검증하려면 서비스 호출 계층을 실제 프록시 경로로 타게 한다
- H2만 믿지 말고 가능하면 Testcontainers 등으로 운영 DB와 가까운 환경을 본다
- `UnexpectedRollbackException` 재현 테스트를 일부러 작성해 본다

트랜잭션은 특히 "테스트 통과 = 운영 안전" 공식이 잘 안 맞는 영역이다.

---

## 흔한 실수 5: 이벤트 발행을 트랜잭션 커밋 전에 직접 해버린다

```java
@Transactional
public void completeOrder(Long orderId) {
    Order order = orderRepository.findById(orderId).orElseThrow();
    order.complete();
    applicationEventPublisher.publishEvent(new OrderCompletedEvent(orderId));
}
```

이 코드는 이벤트 리스너 구조에 따라 안전할 수도, 위험할 수도 있다. 중요한 것은 이벤트가 **언제 실제 부작용을 일으키느냐**다.

- 같은 트랜잭션 안에서 즉시 처리되면 롤백 전에 외부 부작용이 발생할 수 있다
- 커밋 후 실행을 의도한다면 `@TransactionalEventListener(phase = AFTER_COMMIT)` 같은 방식이 더 명확하다
- 시스템 간 메시지 전달이라면 outbox가 더 추적 가능하다

즉 이벤트라는 포장만 씌운다고 정합성 문제가 사라지지 않는다.

---

## 실무 체크리스트: 트랜잭션 설계를 리뷰할 때 꼭 보는 항목

새 기능이나 장애 수정 PR을 볼 때, 나는 아래 체크리스트로 보는 편이 가장 효율적이라고 생각한다.

### 1) 경계 점검

- [ ] 이 메서드가 정말 하나의 실패 단위인가
- [ ] 같은 트랜잭션으로 묶어야 하는 DB 변경만 들어 있는가
- [ ] 외부 API 호출이 DB 트랜잭션 안에 들어가 있지 않은가
- [ ] 트랜잭션이 너무 길어질 여지가 없는가

### 2) 프록시/호출 구조 점검

- [ ] `@Transactional` 메서드가 외부 프록시 호출로 진입하는가
- [ ] 같은 클래스 내부 호출에 기대고 있지 않은가
- [ ] interface proxy, class proxy, method visibility 제약을 팀이 이해하고 있는가

### 3) propagation 점검

- [ ] 기본값 `REQUIRED`로 충분한데 불필요한 `REQUIRES_NEW`를 쓰지 않았는가
- [ ] `REQUIRES_NEW`가 남는 데이터의 의미를 팀이 설명할 수 있는가
- [ ] `NESTED`를 썼다면 savepoint 지원과 의도를 모두 설명 가능한가

### 4) rollback 점검

- [ ] checked exception과 unchecked exception 정책이 일관적인가
- [ ] 내부 예외를 catch한 뒤에도 rollback-only 가능성을 고려했는가
- [ ] `UnexpectedRollbackException`을 우회가 아니라 해석 대상으로 보고 있는가

### 5) readOnly / isolation / timeout 점검

- [ ] readOnly 메서드에서 상태 변경 코드가 없는가
- [ ] isolation을 높인 이유가 명확한가
- [ ] isolation 대신 유니크 키, 조건부 update, 버전 컬럼으로 풀 수 없는가
- [ ] timeout이 실제 새 물리 트랜잭션에 적용되는 구조인가

### 6) 메시지/이벤트 점검

- [ ] 커밋과 발행 순서가 명확한가
- [ ] outbox 또는 AFTER_COMMIT 구조가 필요한가
- [ ] 재시도와 멱등성이 설계돼 있는가

### 7) 운영 점검

- [ ] 슬로우 쿼리, 락 대기, connection pool 사용량을 관찰할 지표가 있는가
- [ ] 실패 시 어떤 데이터가 남고 어떤 데이터가 롤백되는지 문서화돼 있는가
- [ ] 수동 복구 절차를 설명할 수 있는가

이 체크리스트를 통과하지 못하면, 애노테이션 개수와 무관하게 트랜잭션 설계는 아직 불안정한 경우가 많다.

---

## 트레이드오프: 단순한 코드와 운영 가능한 코드 사이에서 무엇을 택할까

트랜잭션 설계를 깊게 들어가면 코드는 분명 더 길어진다.

- 파사드와 트랜잭션 서비스가 나뉜다
- 상태 전이 메서드가 늘어난다
- outbox, 감사 로그, 재처리 큐가 들어온다
- 테스트 케이스도 더 많아진다

처음 보면 과하다고 느낄 수 있다. 특히 작은 서비스나 초기 제품에서는 "그냥 서비스 하나에 `@Transactional` 붙이면 되지 않나" 싶다. 그 판단이 맞을 때도 있다.

하지만 아래 조건 중 둘 이상에 해당하면, 나는 초기에 조금 더 구조를 잡는 쪽이 맞다고 본다.

- 외부 API 호출이 포함된다
- 돈, 재고, 쿠폰, 정산처럼 복구 비용이 큰 상태가 있다
- 메시지 발행/이벤트 연동이 있다
- 트래픽 증가 가능성이 높다
- 운영자가 직접 복구할 일이 생길 수 있다

즉 트랜잭션 설계는 과잉 공학이 아니라, **나중에 사람이 직접 수습할 비용을 앞당겨 줄이는 작업**이다.

---

## 한 번 더 요약: 상황별 추천 패턴

### 상황 1, 하나의 DB 정합성 단위다

- 주문 저장
- 주문 아이템 저장
- 재고 차감

**추천**

- 같은 서비스 경계에서 `REQUIRED`
- 유스케이스 public 메서드에 트랜잭션

### 상황 2, 실패 여부와 무관하게 로그를 남기고 싶다

- 감사 로그
- 에러 이력
- 운영 진단용 기록

**추천**

- 별도 빈으로 분리
- `REQUIRES_NEW`를 제한적으로 사용

### 상황 3, 외부 시스템 호출이 있다

- 결제 승인
- 이메일 발송
- 다른 서비스 HTTP 호출

**추천**

- 가능하면 DB 트랜잭션 밖으로 이동
- 멱등 키와 재시도 설계
- 결과 반영은 별도 짧은 트랜잭션

### 상황 4, 이벤트를 발행해야 한다

- 도메인 이벤트
- MQ publish
- 후속 워커 트리거

**추천**

- outbox 또는 AFTER_COMMIT 기반 처리
- 커밋 전 직접 외부 부작용 금지

### 상황 5, 동시성 충돌이 있다

- 중복 처리
- 재고 부족
- 상태 전이 충돌

**추천**

- isolation을 무작정 올리기 전
- 유니크 키, 조건부 update, optimistic locking 검토

---

## 흔한 질문에 대한 짧은 답

### Q1. 서비스 계층의 모든 public 메서드에 `@Transactional`을 붙여도 되나?

권하지 않는다. 읽기/쓰기 경계가 흐려지고, 필요 이상으로 커넥션을 붙잡을 수 있다. 정말 유스케이스 경계인 메서드에 붙이는 편이 낫다.

### Q2. `readOnly = true`는 무조건 붙이는 게 좋은가?

조회 전용 메서드에는 의도 표현 차원에서 좋다. 하지만 성능 만능열쇠처럼 기대하면 안 된다. 더 중요한 것은 readOnly 메서드에서 쓰기 코드를 넣지 않는 것이다.

### Q3. `REQUIRES_NEW`를 쓰면 더 안전한가?

아니다. 더 독립적일 뿐이다. 그 말은 곧 부분 커밋이 늘어난다는 뜻이다. 안전이 아니라 **의도적 분리**로 이해해야 한다.

### Q4. `UnexpectedRollbackException`이 뜨면 어떻게 보나?

예외를 지우려 하지 말고, 어디서 rollback-only가 생겼는지 호출 체인을 본다. 대부분 경계 설계 오해나 부가 기능을 같은 `REQUIRED`에 넣은 구조가 원인이다.

### Q5. `NESTED`는 언제 쓰나?

정말 savepoint 기반 부분 롤백이 필요한 JDBC 시나리오에서만 제한적으로 본다. 일반적인 Spring Boot 서비스 애플리케이션에서는 자주 추천하지 않는다.

---

## 배치와 스케줄러에서는 propagation보다 "단위 작업 크기"가 먼저다

웹 요청에서는 보통 한 번의 유스케이스가 한 번의 트랜잭션과 자연스럽게 이어진다. 하지만 배치와 스케줄러는 다르다. 특히 아래 같은 작업은 트랜잭션 설계가 완전히 달라진다.

- 1만 건 주문 상태 마이그레이션
- 일별 정산 배치
- 실패 재처리 스케줄러
- 메시지 backlog 회수 작업

이때 흔히 나오는 안티패턴은 두 가지다.

### 안티패턴 1: 전체 루프를 한 트랜잭션으로 감싼다

```java
@Transactional
public void settleAll(List<Long> orderIds) {
    for (Long orderId : orderIds) {
        settle(orderId);
    }
}
```

문제는 명확하다.

- 한 건 실패가 전체 배치를 롤백한다
- DB 락과 커넥션 점유 시간이 길어진다
- 메모리 사용량과 영속성 컨텍스트 크기가 불어난다
- 장애 지점이 애매해져 재시작이 어렵다

### 안티패턴 2: 매 건 `REQUIRES_NEW`를 무지성으로 건다

```java
for (Long orderId : orderIds) {
    settlementTxService.settleOne(orderId); // REQUIRES_NEW
}
```

이 패턴은 격리 면에서는 직관적이지만, 다음 비용이 따른다.

- 건당 커밋 비용 증가
- connection pool 압박 증가
- 로깅과 모니터링 없으면 어느 건까지 성공했는지 파악 어려움
- 외부 호출이 섞이면 처리량 급감

### 더 현실적인 기준

배치에서는 보통 아래 세 축을 같이 본다.

1. **실패 시 다시 시작할 최소 단위**
2. **한 트랜잭션이 잡는 시간과 메모리**
3. **부분 성공을 허용할 수 있는가**

예를 들어 정산 배치라면 다음처럼 설계할 수 있다.

- 주문 100건씩 chunk 조회
- 각 chunk는 하나의 읽기 단위
- 실제 정산 반영은 주문 1건 또는 소규모 묶음 기준 트랜잭션
- 성공/실패 이력은 별도 테이블에 기록
- 다음 재시작 시 마지막 성공 지점 이후부터 이어감

즉 배치에서 중요한 것은 propagation enum보다 **재시작 가능한 처리 단위**다.

### 배치에서 자주 쓰는 실무 패턴

#### 1) 조회와 쓰기 분리

- ID 목록을 먼저 읽는다
- 쓰기 트랜잭션은 짧게 가져간다
- 긴 계산이나 외부 API 호출은 트랜잭션 밖에서 수행한다

#### 2) 체크포인트 저장

- 마지막 성공 ID
- 마지막 처리 시간
- 실패 건 목록
- 재시도 횟수

이런 메타데이터가 있어야 배치 실패 후 사람이 개입하지 않고 복구가 가능하다.

#### 3) skip/retry 기준 명확화

- 데이터 오류는 skip 후 이력 기록
- 외부 일시 장애는 retry
- 정합성 위반은 전체 중단

이 기준이 없으면 운영자가 매번 로그를 보고 즉석 판단하게 된다.

트랜잭션은 여기서도 중요하지만, 배치에서는 특히 **복구 가능성**이 설계의 핵심이다.

---

## 관측 가능성: 트랜잭션 설계가 좋아도 보이지 않으면 운영 품질은 낮다

트랜잭션 문제는 로그 한 줄만으로 잡히지 않는 경우가 많다. 특히 propagation, rollback-only, 외부 호출, lock wait가 얽히면 체감 증상과 실제 원인이 다르게 보인다.

그래서 나는 트랜잭션이 중요한 쓰기 경로라면 최소한 아래 관측 포인트는 있어야 한다고 본다.

### 1) 요청 단위 correlation id

- HTTP request id
- 주문 id / 결제 id / 배치 execution id
- 사용자 id 또는 actor

이 키가 없으면 부분 커밋이나 다단계 실패를 추적하기가 너무 어렵다.

### 2) 상태 전이 로그

특히 외부 시스템이 섞인다면 아래 같은 상태 전이를 명시적으로 남겨야 한다.

- `PENDING -> APPROVING`
- `APPROVING -> APPROVED`
- `APPROVING -> FAILED`
- `APPROVED -> EVENT_PUBLISHED`

이력 테이블이든 구조화 로그든 상관없지만, 전이가 보여야 한다.

### 3) DB 관점 지표

- connection pool active / idle / pending
- transaction duration 상위 percentiles
- lock wait time
- deadlock count
- slow query

트랜잭션 문제는 코드 리뷰보다 운영 지표에서 먼저 티가 나는 경우가 많다.

### 4) outbox / retry 큐 지표

outbox를 쓴다면 다음이 안 보이면 사실상 반만 구현한 것이다.

- 적재 건수
- 미발행 건수 backlog
- 재시도 횟수
- 최종 실패 건수
- 가장 오래된 미처리 레코드 나이

### 5) `UnexpectedRollbackException` 알림

이 예외는 조용히 지나가면 안 된다. 대부분 설계 오해 또는 예외 처리 흐름 문제를 뜻하므로, 에러 집계에서 별도 그룹으로 보이게 두는 편이 좋다.

관측이 갖춰지면 장점이 크다.

- propagation 오용을 빨리 찾을 수 있다
- 외부 API를 트랜잭션 안에 넣은 코드가 지표로 바로 드러난다
- 장애 원인을 "DB가 느림" 같은 추상 표현 대신 구체적으로 분리할 수 있다

---

## 장애 복구 관점에서 보는 트랜잭션 설계: 자동 롤백보다 수동 복구 비용이 더 중요할 때가 많다

팀이 트랜잭션을 논의할 때 보통은 커밋/롤백 여부만 이야기한다. 하지만 운영에서는 그보다 더 중요한 질문이 있다.

> 이 요청이 중간에 실패했을 때, 사람이 어떤 절차로 복구할 수 있는가?

예를 들어 아래 세 구조를 비교해 보자.

### 구조 A, 모든 걸 한 트랜잭션에 묶고 외부 호출도 포함

장점:

- 코드가 짧다

단점:

- 외부 승인 성공 후 DB 롤백 시 복구가 어렵다
- 정확히 어디까지 성공했는지 애매하다
- 수동 조사 비용이 높다

### 구조 B, 내부 상태와 외부 호출을 분리하고 상태 전이를 둔다

장점:

- 현재 상태가 테이블로 보인다
- 재시도 가능 지점을 정의할 수 있다
- 운영자가 "이 건은 APPROVING에서 멈췄다"고 바로 판단할 수 있다

단점:

- 상태 머신과 보정 로직이 필요하다

### 구조 C, outbox와 이력 테이블까지 둔다

장점:

- 메시지 발행 누락/중복을 추적 가능하다
- 수동 복구 절차를 문서화하기 쉽다
- 운영 툴링 자동화가 가능하다

단점:

- 초기 구현 비용이 가장 크다

내 경험상 중요한 도메인에서는 대개 B 또는 C가 결국 이긴다. 트랜잭션을 잘 설계했다는 말은 "예외가 났을 때 자동으로 롤백된다"보다, **중간 실패 상태가 눈에 보이고 복구 경로가 정의돼 있다**에 더 가깝다.

### 복구 친화적인 설계 질문

다음 질문에 답할 수 없으면, 트랜잭션 설계가 아직 약한 경우가 많다.

- 이 요청이 실패하면 남을 수 있는 상태는 몇 가지인가
- 각 상태는 정상 재시도 가능한가
- 중복 실행돼도 안전한가
- 운영자가 수동으로 되돌리거나 재처리할 방법이 있는가
- 그 절차를 사람이 새벽 3시에 10분 안에 이해할 수 있는가

트랜잭션은 코드 수준의 우아함보다, 복구 절차의 단순함으로 평가하는 편이 실제 운영에는 더 맞다.

---

## 팀 컨벤션으로 굳히면 사고가 줄어드는 규칙들

트랜잭션 관련 사고는 개인 실수이기도 하지만, 더 자주 보면 팀 규칙 부재 문제다. 다음 정도는 팀 컨벤션으로 고정해 두는 편이 효과가 좋다.

### 컨벤션 1, 유스케이스 public 메서드에만 `@Transactional`

- private helper에는 붙이지 않는다
- 같은 클래스 내부 호출에 기대지 않는다
- 트랜잭션이 필요한 쓰기 유스케이스만 명시한다

### 컨벤션 2, `REQUIRES_NEW`는 이유를 주석이나 메서드명으로 남긴다

예를 들어 아래처럼 의도를 코드에 남긴다.

```java
@Transactional(propagation = Propagation.REQUIRES_NEW)
public void persistFailureAuditIndependently(...) {
    // ...
}
```

이렇게 하면 리뷰어도 "왜 독립 커밋인가"를 바로 본다.

### 컨벤션 3, 외부 API 호출 메서드에는 기본적으로 `@Transactional` 금지

절대 규칙은 아니지만, 기본 정책으로 두면 상당수 사고를 미리 막을 수 있다. 예외가 필요하면 설계 리뷰에서 명시적으로 허용한다.

### 컨벤션 4, readOnly 메서드에서 엔티티 상태 변경 금지

리뷰에서 발견되면 성능 이슈 이전에 책임 분리 문제로 본다.

### 컨벤션 5, 이벤트 발행은 AFTER_COMMIT 또는 outbox 우선

직접 publish가 허용되는 예외 상황이 무엇인지도 문서화해 둔다.

### 컨벤션 6, 중요한 쓰기 경로는 실패 상태를 enum으로 모델링

예를 들어:

- `PENDING`
- `PROCESSING`
- `SUCCEEDED`
- `FAILED`
- `RETRY_SCHEDULED`

상태가 보이면 트랜잭션 설계와 복구 전략도 같이 명확해진다.

팀 컨벤션은 사소해 보여도, 실제로는 propagation 오용과 self-invocation 문제를 상당 부분 예방해 준다.

---

## 코드 리뷰에서 바로 걸러야 하는 냄새들

트랜잭션 관련 PR에서 아래 패턴이 보이면 한 번 더 파고드는 편이 좋다.

### 냄새 1

```java
@Transactional
public void doSomething() {
    remoteClient.call();
    repository.save(...);
}
```

질문해야 할 것:

- 왜 외부 호출이 트랜잭션 안에 있어야 하나
- 타임아웃과 재시도는 어떻게 되는가
- 멱등성은 있는가

### 냄새 2

```java
@Transactional(readOnly = true)
public void findAndTouch(...) { ... }
```

질문해야 할 것:

- 정말 조회인가, 숨은 쓰기인가
- CQRS 관점에서 분리가 필요한가

### 냄새 3

```java
try {
    service.call();
} catch (Exception ignored) {
}
```

질문해야 할 것:

- 이 예외가 같은 물리 트랜잭션을 rollback-only로 만들지 않는가
- 실패를 정말 무시해도 되는가

### 냄새 4

```java
for (...) {
    requiresNewService.save(...);
}
```

질문해야 할 것:

- 묶음 처리나 비동기화가 낫지 않은가
- connection pool과 TPS에 미치는 영향은 측정했는가

### 냄새 5

```java
public void outer() { inner(); }
@Transactional
public void inner() { ... }
```

질문해야 할 것:

- 이 호출이 정말 프록시를 통과하는가
- 설계를 왜 분리하지 않았는가

이런 냄새를 일찍 잡으면, 운영에서만 드러나는 트랜잭션 버그를 상당수 줄일 수 있다.

---

## 실전 판단 연습: 같은 요구사항도 트랜잭션 경계에 따라 결과가 완전히 달라진다

마지막으로 짧은 사고 실험을 해보자. 요구사항은 같다.

- 주문 저장
- 쿠폰 사용
- 감사 로그 저장
- 외부 결제 승인
- 주문 완료 이벤트 발행

그런데 경계를 어디에 두느냐에 따라 실패 후 남는 세계가 달라진다.

### 설계안 A, 전부 하나의 `REQUIRED`

장점:

- 코드가 제일 짧다
- 처음 구현이 빠르다

실패 후 결과:

- DB 내부 작업은 같이 롤백될 수 있다
- 하지만 외부 결제 승인과 이벤트 발행은 이미 실행됐을 수 있다
- 사람 입장에서는 "실패했는데 일부는 성공한" 가장 다루기 어려운 상태가 된다

### 설계안 B, 주문/쿠폰은 `REQUIRED`, 감사 로그는 `REQUIRES_NEW`, 결제는 바깥, 이벤트는 outbox

장점:

- 핵심 도메인 정합성은 한 트랜잭션으로 유지된다
- 감사 로그는 실패해도 남는다
- 결제와 메시지는 재시도 가능 구조로 분리된다

실패 후 결과:

- 주문 생성 실패 시 감사 로그만 남을 수 있다. 이것은 의도된 부분 커밋이다
- 결제 승인 실패 시 주문은 `PENDING_PAYMENT` 또는 `FAILED_PAYMENT` 같은 상태로 남기고 재시도할 수 있다
- 이벤트 누락 여부는 outbox backlog로 확인 가능하다

### 설계안 C, 주문, 쿠폰, 감사 로그를 모두 `REQUIRES_NEW`로 분리

장점:

- 메서드별 독립성이 커 보인다

실패 후 결과:

- 부분 커밋 조합이 너무 많아진다
- 주문만 있고 쿠폰은 없고 감사 로그는 남고 결제는 실패한 상태 같은 변형이 급격히 늘어난다
- 운영자가 상태를 이해하기 어려워진다

즉 "독립 트랜잭션이 많다"가 좋은 설계가 아니다. 오히려 중요한 것은 **허용 가능한 부분 성공 조합의 개수를 의도적으로 줄이는 것**이다.

### 실무에서 끝까지 남는 세 가지 원칙

이 글이 길었으니, 마지막으로 정말 자주 꺼내 쓰는 기준 세 개만 다시 압축하자.

1. **핵심 정합성은 짧고 굵게 묶는다**
   주문, 재고, 상태 전이처럼 반드시 함께 맞아야 하는 DB 변경만 같은 트랜잭션에 둔다.

2. **외부 부작용은 가능한 한 커밋 이후 세계로 보낸다**
   결제, 메시지 발행, 메일, 알림은 멱등성과 재시도 전략까지 같이 설계한다.

3. **부분 커밋은 의도적으로만 허용한다**
   감사 로그처럼 남아도 되는 것만 `REQUIRES_NEW`로 분리하고, 핵심 도메인 상태에는 쉽게 쓰지 않는다.

이 세 가지만 팀 전체가 공유해도, `@Transactional` 관련 장애 대부분은 "왜 이 데이터가 이렇게 남았지?" 수준까지 번지기 전에 잡힌다.

이 관점으로 보면 좋은 트랜잭션 설계는 대체로 이런 특징을 가진다.

- 핵심 정합성은 하나의 짧은 트랜잭션으로 묶는다
- 독립 보존 가치가 있는 기록만 제한적으로 분리한다
- 외부 부작용은 커밋 이후 세계에서 다룬다
- 실패 상태를 테이블과 로그에 명시한다

결국 propagation 선택은 문법 문제가 아니라, **실패 후 시스템이 설명 가능한 상태를 유지하는가**의 문제다.

---

## 마무리: 트랜잭션 전파를 이해한다는 것은 "실패 후 어떤 세계가 남는가"를 설계하는 일이다

트랜잭션 관련 글은 종종 propagation enum 설명으로 끝난다. 하지만 실무에서 중요한 것은 이름 암기가 아니다.

- 실패 후 어떤 데이터가 남아도 되는가
- 어떤 부작용은 반드시 커밋 이후에만 일어나야 하는가
- 예외를 잡은 뒤에도 정말 커밋 가능한가
- 이 메서드 호출이 프록시를 지나 실제 트랜잭션 경계를 형성하는가

결국 `@Transactional`은 DB API의 편의 기능이 아니라, **시스템 실패 모델을 코드에 새기는 도구**다.

이 관점이 생기면 다음 변화가 따라온다.

- `REQUIRES_NEW`를 덜 쓰게 된다
- 외부 API를 트랜잭션 안에 넣는 코드가 눈에 거슬리기 시작한다
- `UnexpectedRollbackException`을 회피가 아니라 설계 신호로 읽게 된다
- readOnly, isolation, timeout을 속성 값이 아니라 호출 구조와 함께 보게 된다

이 정도 기준만 잡혀도 Spring 트랜잭션 관련 운영 사고의 절반 이상은 미리 줄일 수 있다.

---

## 한 줄 정리

`@Transactional`의 핵심은 애노테이션을 어디에 붙이느냐가 아니라, **어떤 작업을 같은 실패 단위로 묶고 어떤 작업은 분리할지 운영 기준으로 설계하는 것**이다.
