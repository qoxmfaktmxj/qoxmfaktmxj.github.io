---
layout: post
title: "Java 타입 모델링 실전: Record, Sealed Class, Pattern Matching으로 도메인 상태를 코드에 가두는 법"
date: 2026-06-08 11:50:00 +0900
categories: [java]
tags: [study, java, record, sealed-class, pattern-matching, domain-modeling, dto, validation, backend, architecture]
permalink: /java/2026/06/08/study-java-record-sealed-pattern-matching-domain-modeling.html
---

## 배경: Java 코드는 왜 시간이 지나면 `String`, `boolean`, `null`의 늪이 되는가

Java 백엔드 코드를 오래 운영하다 보면 처음에는 단순했던 모델이 점점 모호해진다.

처음에는 주문 상태가 문자열 하나였을 수 있다.

```java
public class Order {
    private String status;
    private String paymentStatus;
    private String deliveryStatus;
    private boolean cancellable;
    private boolean refundable;
    private String cancelReason;
}
```

이 구조는 빠르게 만들 수 있다. 데이터베이스 컬럼과도 잘 맞고, JSON 직렬화도 쉽다.

하지만 시간이 지나면 다음 문제가 생긴다.

- `status = "CANCELLED"`인데 `cancellable = true`인 데이터가 생긴다
- `cancelReason`이 필요한 상태와 없어야 하는 상태를 코드가 구분하지 못한다
- 결제 실패, 결제 대기, 결제 완료, 부분 환불을 모두 문자열 비교로 처리한다
- `null`이 "아직 없음"인지, "해당 없음"인지, "외부 시스템 오류"인지 모른다
- 서비스 곳곳에 `if ("PAID".equals(status))` 같은 조건문이 흩어진다
- 새 상태가 추가돼도 컴파일러가 누락된 분기 처리를 알려주지 않는다
- DTO, 엔티티, 도메인 객체의 책임이 섞여 테스트가 점점 방어적이 된다
- API 입력 검증은 했지만 내부 상태 전이는 여전히 아무 값이나 받을 수 있다

이런 문제는 단순히 "객체지향을 잘하자"로 해결되지 않는다. 더 구체적으로는 **도메인에서 가능한 상태와 불가능한 상태를 타입 시스템 안으로 얼마나 밀어 넣을 수 있는가**의 문제다.

Java는 예전보다 이 작업을 훨씬 잘할 수 있는 언어가 됐다.

- `record`는 불변 데이터 carrier를 간결하게 만든다
- `sealed class`와 `sealed interface`는 하위 타입의 범위를 제한한다
- pattern matching은 타입별 분기를 더 명확하게 만든다
- `switch` exhaustiveness는 누락된 상태 처리를 컴파일 단계에서 드러낼 수 있다

문제는 이 기능들을 문법으로만 외우면 실무 코드가 더 좋아지지 않는다는 점이다. `record`를 DTO 자동 생성기처럼 쓰거나, `sealed`를 상속 제한 키워드 정도로만 이해하면 금방 한계에 부딪힌다.

이 글은 중급 이상 Java 개발자를 기준으로 다음 질문에 답한다.

1. `record`를 언제 값 객체로 쓰고, 언제 DTO로만 남겨야 하는가
2. `sealed interface`는 enum과 무엇이 다르고 어떤 문제를 더 잘 표현하는가
3. pattern matching `switch`를 도메인 분기에서 어떻게 안전하게 활용할 수 있는가
4. JPA entity, API DTO, domain model 사이에서 `record`와 `sealed`를 어디에 배치해야 하는가
5. validation, serialization, persistence, 테스트에서 어떤 트레이드오프가 생기는가
6. 타입 모델링을 과하게 적용했을 때 어떤 비용이 생기고, 어디서 멈춰야 하는가

결론부터 말하면 이렇다.

> `record`, `sealed`, pattern matching의 핵심은 코드를 짧게 만드는 것이 아니라, **불가능한 상태를 표현할 수 없게 만들고 상태별 처리를 컴파일러가 감시하게 만드는 것**이다.

---

## 먼저 큰 그림: 데이터 모양과 상태 전이를 분리해서 본다

도메인 모델링을 시작할 때 흔한 실수는 "필드가 무엇인가"만 보는 것이다.

예를 들어 주문 취소 요청을 생각해 보자.

```java
public record CancelOrderRequest(
        String orderId,
        String reason,
        String actorId,
        boolean force
) {
}
```

이 타입은 입력 데이터의 모양을 보여준다. 하지만 비즈니스 상태를 충분히 설명하지는 못한다.

실무에서 더 중요한 질문은 다음이다.

- 주문은 현재 어떤 상태인가
- 어떤 상태에서는 취소가 가능한가
- 취소 사유가 반드시 필요한 경우는 언제인가
- 결제 승인 전 취소와 결제 승인 후 환불은 같은 동작인가
- 운영자가 강제 취소할 때와 고객이 취소할 때 정책이 다른가
- 이미 배송이 시작된 주문은 어떤 대체 상태로 흘러가야 하는가

이 질문들은 단순 필드 목록보다 **상태 공간(state space)** 에 가깝다.

상태 공간을 느슨하게 표현하면 코드가 모든 조합을 허용한다.

```java
public class OrderState {
    private String status;
    private String paidAt;
    private String cancelledAt;
    private String refundId;
    private String deliveryTrackingNo;
}
```

위 모델은 컴파일러 입장에서 모든 조합이 가능하다.

- 결제 전인데 환불 ID가 있음
- 취소됐는데 운송장 번호가 있음
- 배송 완료인데 `paidAt`이 없음
- 결제 실패인데 `cancelledAt`이 있음

물론 런타임 검증으로 막을 수 있다. 하지만 검증이 서비스, 컨트롤러, 이벤트 핸들러, 배치 코드에 흩어지면 결국 누락된다.

타입 모델링의 목표는 모든 규칙을 타입으로 표현하는 것이 아니다. 그건 과하다. 목표는 다음에 가깝다.

- 자주 깨지는 핵심 불변식은 생성 시점에 막는다
- 상태별로 필요한 데이터가 다르면 타입을 나눈다
- 새 상태가 추가될 때 위험한 분기 코드를 컴파일러가 알려주게 한다
- 외부 I/O와 영속성의 제약을 도메인 내부로 그대로 끌고 오지 않는다

이 관점에서 `record`, `sealed`, pattern matching은 서로 역할이 다르다.

- `record`: 값의 묶음과 불변식을 간결하게 표현한다
- `sealed`: 가능한 하위 상태의 집합을 제한한다
- pattern matching: 상태별 처리 코드를 타입 중심으로 읽게 만든다

---

## 핵심 개념 1: `record`는 getter 줄이기 도구가 아니라 값 의미를 드러내는 도구다

`record`는 보일러플레이트를 줄인다. 생성자, accessor, `equals`, `hashCode`, `toString`을 자동으로 만든다.

그래서 처음에는 DTO용 문법처럼 보인다.

```java
public record UserResponse(
        Long id,
        String name,
        String email
) {
}
```

이 사용도 나쁘지 않다. 하지만 `record`의 더 중요한 장점은 **값 객체(value object)** 를 만들 때 드러난다.

예를 들어 이메일을 계속 문자열로 다룬다고 하자.

```java
public void invite(String email) {
    if (email == null || !email.contains("@")) {
        throw new IllegalArgumentException("invalid email");
    }

    invitationRepository.save(email.toLowerCase());
}
```

이 검증은 다른 서비스에서도 반복된다. 누군가는 소문자 정규화를 빼먹고, 누군가는 공백 제거를 빼먹고, 누군가는 테스트에서만 검증한다.

값 객체로 올리면 규칙의 위치가 선명해진다.

```java
public record EmailAddress(String value) {
    public EmailAddress {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException("email must not be blank");
        }

        String normalized = value.trim().toLowerCase();
        if (!normalized.contains("@")) {
            throw new IllegalArgumentException("invalid email: " + value);
        }

        value = normalized;
    }
}
```

compact constructor에서는 파라미터를 재할당할 수 있다. 최종 필드에 대입되기 전에 정규화와 검증을 끝낼 수 있으므로 값 객체에 잘 맞는다.

이제 서비스 코드는 더 이상 이메일의 내부 규칙을 몰라도 된다.

```java
public void invite(EmailAddress email) {
    invitationRepository.save(email.value());
}
```

여기서 얻는 이득은 getter를 줄인 것이 아니다.

- 검증 위치가 생성자로 모인다
- 정규화가 한 번만 수행된다
- 잘못된 이메일이 내부 계층으로 들어오기 어렵다
- `String` 파라미터 순서 실수를 줄인다
- 테스트가 값 객체 중심으로 작아진다

### 값 객체로 좋은 `record`의 조건

`record`가 값 객체로 잘 맞으려면 몇 가지 조건이 있다.

1. 식별자보다 값 자체가 중요하다
2. 생성 이후 변경되지 않아야 한다
3. 동등성 비교가 필드 값 기준이어도 자연스럽다
4. 생성 시점에 핵심 불변식을 검증할 수 있다
5. 내부 컬렉션이나 가변 객체를 그대로 노출하지 않는다

예를 들어 금액은 좋은 후보가 된다.

```java
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.Currency;

public record Money(BigDecimal amount, Currency currency) {
    public Money {
        if (amount == null) {
            throw new IllegalArgumentException("amount must not be null");
        }
        if (currency == null) {
            throw new IllegalArgumentException("currency must not be null");
        }
        if (amount.scale() > currency.getDefaultFractionDigits()) {
            amount = amount.setScale(currency.getDefaultFractionDigits(), RoundingMode.HALF_UP);
        }
        if (amount.signum() < 0) {
            throw new IllegalArgumentException("amount must not be negative");
        }
    }

    public Money add(Money other) {
        if (!currency.equals(other.currency)) {
            throw new IllegalArgumentException("currency mismatch");
        }
        return new Money(amount.add(other.amount), currency);
    }
}
```

이 코드가 `BigDecimal`을 직접 넘기는 코드보다 나은 이유는 명확하다.

- 통화 없는 금액을 만들 수 없다
- 음수 금액이 허용되지 않는 도메인이라면 생성 단계에서 막는다
- 더하기 규칙이 값 객체 안에 있다
- 금액 계산 로직이 서비스 코드에서 반복되지 않는다

### `record`도 얕은 불변성만 제공한다

`record`를 쓴다고 모든 것이 자동으로 불변이 되지는 않는다. 특히 컬렉션이 문제다.

```java
public record Cart(List<CartLine> lines) {
}
```

이 타입은 위험하다. 외부에서 넘긴 리스트를 나중에 수정할 수 있다.

```java
List<CartLine> lines = new ArrayList<>();
Cart cart = new Cart(lines);
lines.add(new CartLine("p1", 1));
```

`Cart`는 record지만 내부 상태가 바뀐 것처럼 보인다.

방어 복사가 필요하다.

```java
import java.util.List;

public record Cart(List<CartLine> lines) {
    public Cart {
        lines = List.copyOf(lines);
        if (lines.isEmpty()) {
            throw new IllegalArgumentException("cart must have at least one line");
        }
    }

    public Money total() {
        return lines.stream()
                .map(CartLine::subtotal)
                .reduce(Money.zero(), Money::add);
    }
}
```

`record`의 불변성은 필드 참조가 바뀌지 않는다는 의미에 가깝다. 참조 대상 객체까지 깊게 불변으로 만들어 주지는 않는다.

---

## 핵심 개념 2: `sealed interface`는 enum보다 풍부한 상태 모델을 만든다

주문 상태를 enum으로 표현하는 것은 자연스럽다.

```java
public enum OrderStatus {
    CREATED,
    PAID,
    PAYMENT_FAILED,
    SHIPPED,
    CANCELLED
}
```

상태 이름만 필요하다면 enum이면 충분하다.

하지만 상태마다 필요한 데이터가 달라지면 enum은 금방 불편해진다.

- 결제 완료 상태에는 결제 승인 번호와 승인 시각이 필요하다
- 결제 실패 상태에는 실패 코드와 실패 메시지가 필요하다
- 배송 상태에는 운송장 번호와 배송사가 필요하다
- 취소 상태에는 취소 주체와 취소 사유가 필요하다

enum 하나와 nullable 필드 여러 개로 표현하면 다시 모호해진다.

```java
public class Order {
    private OrderStatus status;
    private String paymentApprovalNo;
    private String paymentFailureCode;
    private String carrier;
    private String trackingNo;
    private String cancelReason;
}
```

이럴 때 `sealed interface`가 유용하다.

```java
import java.time.Instant;

public sealed interface OrderState
        permits OrderState.Created,
                OrderState.Paid,
                OrderState.PaymentFailed,
                OrderState.Shipped,
                OrderState.Cancelled {

    record Created(Instant createdAt) implements OrderState {
    }

    record Paid(String approvalNo, Instant paidAt) implements OrderState {
        public Paid {
            if (approvalNo == null || approvalNo.isBlank()) {
                throw new IllegalArgumentException("approvalNo must not be blank");
            }
        }
    }

    record PaymentFailed(String code, String message, Instant failedAt) implements OrderState {
    }

    record Shipped(String carrier, String trackingNo, Instant shippedAt) implements OrderState {
    }

    record Cancelled(String reason, Instant cancelledAt) implements OrderState {
    }
}
```

이 구조는 상태별로 필요한 데이터를 타입 안에 둔다.

- `Paid`는 결제 승인 정보를 반드시 가진다
- `PaymentFailed`는 실패 정보를 가진다
- `Shipped`는 배송 정보를 가진다
- `Created`에는 결제 정보가 없다
- `Cancelled`에는 배송 정보가 없다

즉 잘못된 조합을 만들기가 어려워진다.

### enum과 sealed type의 선택 기준

enum이 더 좋은 경우도 많다.

- 상태가 단순 이름에 가깝다
- 각 상태가 추가 데이터를 거의 갖지 않는다
- 데이터베이스 컬럼 하나로 충분히 표현된다
- 화면 필터, 검색 조건, 권한 코드처럼 값 집합이 핵심이다
- 상태별 동작이 작고 안정적이다

반대로 sealed type이 더 좋은 경우는 다음이다.

- 상태마다 필요한 데이터가 다르다
- 상태별 검증 규칙이 다르다
- 상태별 동작이 점점 커진다
- 새 상태가 추가될 때 모든 분기 코드를 확인해야 한다
- nullable 보조 필드가 계속 늘어난다
- `if status == X then field Y must exist` 같은 규칙이 많다

핵심은 "enum은 나쁘고 sealed는 좋다"가 아니다. enum은 **상태 이름의 폐쇄 집합**을 표현하고, sealed type은 **상태 모양의 폐쇄 집합**을 표현한다.

---

## 핵심 개념 3: pattern matching `switch`는 상태별 처리를 컴파일러 감시 아래 둔다

sealed hierarchy가 힘을 발휘하는 지점은 분기 처리다.

예를 들어 주문 상태별로 고객에게 보여줄 메시지를 만든다고 하자.

```java
public String customerMessage(OrderState state) {
    return switch (state) {
        case OrderState.Created created ->
                "주문이 접수되었습니다.";
        case OrderState.Paid paid ->
                "결제가 완료되었습니다. 승인번호: " + paid.approvalNo();
        case OrderState.PaymentFailed failed ->
                "결제에 실패했습니다. 사유: " + failed.message();
        case OrderState.Shipped shipped ->
                "배송이 시작되었습니다. 운송장: " + shipped.trackingNo();
        case OrderState.Cancelled cancelled ->
                "주문이 취소되었습니다. 사유: " + cancelled.reason();
    };
}
```

여기서 중요한 점은 `default`가 없다는 것이다.

`OrderState`가 sealed이고 모든 하위 타입이 나열돼 있다면, 컴파일러는 이 switch가 모든 경우를 다뤘는지 확인할 수 있다. 나중에 `Refunded` 상태를 추가하면 이 switch는 컴파일 오류 또는 경고 신호를 낼 수 있다.

이것은 운영 코드에서 큰 차이를 만든다.

문자열과 `if` 체인에서는 새 상태 추가가 조용히 누락된다.

```java
if ("CREATED".equals(status)) {
    return "주문이 접수되었습니다.";
}
if ("PAID".equals(status)) {
    return "결제가 완료되었습니다.";
}
return "주문 상태를 확인 중입니다.";
```

이 코드는 `REFUNDED`가 추가돼도 컴파일러가 아무 말도 하지 않는다. `default`처럼 동작하는 마지막 문장이 문제를 숨긴다.

반면 sealed type과 exhaustive switch는 누락을 코드 변경 시점에 드러낸다.

### `default`를 습관적으로 넣지 않는다

실무에서 pattern matching `switch`를 쓸 때 자주 하는 실수는 모든 switch에 `default`를 넣는 것이다.

```java
return switch (state) {
    case OrderState.Created ignored -> "created";
    case OrderState.Paid ignored -> "paid";
    default -> "unknown";
};
```

이 코드는 안전해 보이지만, sealed type의 장점을 약화한다. 새 상태가 추가됐을 때 `default`가 조용히 받아 버린다.

상태 누락이 위험한 도메인이라면 `default`를 피하고 모든 타입을 명시하는 편이 낫다.

물론 외부 입력을 처리하는 경계에서는 unknown 처리가 필요할 수 있다. 그 경우에는 sealed domain model로 변환하기 전 단계에서 처리하는 편이 좋다.

```java
public OrderState parseState(OrderStateRow row) {
    return switch (row.status()) {
        case "CREATED" -> new OrderState.Created(row.createdAt());
        case "PAID" -> new OrderState.Paid(row.paymentApprovalNo(), row.paidAt());
        case "PAYMENT_FAILED" -> new OrderState.PaymentFailed(
                row.failureCode(),
                row.failureMessage(),
                row.failedAt()
        );
        case "SHIPPED" -> new OrderState.Shipped(row.carrier(), row.trackingNo(), row.shippedAt());
        case "CANCELLED" -> new OrderState.Cancelled(row.cancelReason(), row.cancelledAt());
        default -> throw new UnknownOrderStateException(row.status());
    };
}
```

이렇게 하면 외부 문자열의 불확실성은 변환 경계에서 처리되고, 내부 도메인에서는 닫힌 상태 집합을 믿고 코드를 작성할 수 있다.

---

## 핵심 개념 4: 상태 전이는 생성자보다 도메인 메서드에 둔다

상태를 타입으로 나누면 다음 질문이 생긴다.

> 상태 변경은 어디에서 일어나야 하는가?

가장 단순한 방식은 서비스에서 직접 새 상태를 만드는 것이다.

```java
public void pay(Order order, PaymentResult result) {
    order.changeState(new OrderState.Paid(result.approvalNo(), result.paidAt()));
}
```

작은 서비스라면 충분하다. 하지만 상태 전이 규칙이 중요하면 도메인 메서드로 올리는 편이 낫다.

```java
public final class Order {
    private final OrderId id;
    private final OrderState state;

    public Order(OrderId id, OrderState state) {
        this.id = id;
        this.state = state;
    }

    public Order markPaid(PaymentApproval approval) {
        if (!(state instanceof OrderState.Created)) {
            throw new InvalidOrderTransitionException(state, "markPaid");
        }
        return new Order(
                id,
                new OrderState.Paid(approval.approvalNo(), approval.approvedAt())
        );
    }

    public Order failPayment(PaymentFailure failure) {
        if (!(state instanceof OrderState.Created)) {
            throw new InvalidOrderTransitionException(state, "failPayment");
        }
        return new Order(
                id,
                new OrderState.PaymentFailed(failure.code(), failure.message(), failure.failedAt())
        );
    }

    public Order cancel(CancelReason reason, Instant cancelledAt) {
        return switch (state) {
            case OrderState.Created ignored ->
                    new Order(id, new OrderState.Cancelled(reason.value(), cancelledAt));
            case OrderState.PaymentFailed ignored ->
                    new Order(id, new OrderState.Cancelled(reason.value(), cancelledAt));
            case OrderState.Paid paid ->
                    throw new RefundRequiredException(id, paid.approvalNo());
            case OrderState.Shipped shipped ->
                    throw new AlreadyShippedException(id, shipped.trackingNo());
            case OrderState.Cancelled ignored ->
                    this;
        };
    }
}
```

여기서 `Order`를 불변 객체로 만들었다. 상태 변경은 새 객체 반환으로 표현한다.

JPA 엔티티와 잘 맞지 않아 보일 수 있다. 이 부분은 뒤에서 다룬다. 우선 도메인 관점에서 얻는 이득을 보자.

- 상태 전이 규칙이 한곳에 모인다
- 불가능한 전이는 예외로 명확히 드러난다
- 상태별 cancel 정책이 switch에 모인다
- 새 상태가 추가되면 cancel 정책도 다시 검토해야 한다
- 테스트는 데이터베이스 없이 순수 객체로 작성할 수 있다

### 전이를 상태 객체에 둘 수도 있다

다른 방식은 상태 타입 자체에 동작을 두는 것이다.

```java
public sealed interface OrderState
        permits Created, Paid, PaymentFailed, Shipped, Cancelled {

    OrderState cancel(CancelReason reason, Instant cancelledAt);
}

public record Created(Instant createdAt) implements OrderState {
    @Override
    public OrderState cancel(CancelReason reason, Instant cancelledAt) {
        return new Cancelled(reason.value(), cancelledAt);
    }
}

public record Paid(String approvalNo, Instant paidAt) implements OrderState {
    @Override
    public OrderState cancel(CancelReason reason, Instant cancelledAt) {
        throw new RefundRequiredException(approvalNo);
    }
}
```

이 방식은 객체지향적으로 보인다. 상태별 동작이 각 타입에 붙기 때문이다.

하지만 모든 경우에 더 좋은 것은 아니다.

- 상태 타입이 비즈니스 서비스 의존성을 갖기 시작하면 복잡해진다
- 하나의 유스케이스를 이해하려고 여러 파일을 오가야 할 수 있다
- 상태별 동작이 너무 많아지면 타입이 비대해진다
- persistence mapping이 더 까다로워질 수 있다

그래서 실무에서는 두 방식을 섞는다.

- 순수한 상태 전이 규칙은 도메인 객체나 상태 타입에 둔다
- 외부 호출, 트랜잭션, 이벤트 발행은 애플리케이션 서비스에 둔다
- 여러 aggregate를 건드리는 정책은 도메인 서비스 또는 애플리케이션 서비스에서 조율한다

---

## 핵심 개념 5: API DTO, 도메인 모델, JPA 엔티티를 같은 타입으로 만들지 않는다

`record`와 `sealed`를 도입할 때 가장 큰 실무 난관은 프레임워크 경계다.

Spring MVC, Jackson, Bean Validation, JPA, QueryDSL, MapStruct 같은 도구는 각자 편한 객체 모양이 있다. 이 도구들의 요구사항을 도메인 모델에 그대로 섞으면 모델이 다시 흐려진다.

### API 요청 DTO는 외부 계약이다

외부 요청은 nullable하고, 부분적이고, 잘못된 값이 들어올 수 있다. 따라서 요청 DTO는 도메인 객체보다 느슨할 수밖에 없다.

```java
public record CreateOrderRequest(
        String userId,
        List<OrderLineRequest> lines,
        String couponCode
) {
}
```

여기에 모든 도메인 규칙을 넣으려 하면 곧 문제가 생긴다.

- 인증 사용자와 요청 userId가 일치하는지 DTO 혼자 모른다
- 상품이 판매 가능한지 DTO는 모른다
- 쿠폰이 적용 가능한지 외부 조회가 필요하다
- 재고 정책은 도메인 서비스가 알아야 한다

요청 DTO의 역할은 외부 모양을 받아 최소한의 형식 검증을 하는 것이다.

```java
public record CreateOrderCommand(
        UserId userId,
        List<CreateOrderLine> lines,
        Optional<CouponCode> couponCode
) {
    public CreateOrderCommand {
        lines = List.copyOf(lines);
        if (lines.isEmpty()) {
            throw new IllegalArgumentException("order lines must not be empty");
        }
    }
}
```

컨트롤러 또는 assembler에서 DTO를 command로 변환한다.

```java
public CreateOrderCommand toCommand(CreateOrderRequest request, AuthenticatedUser user) {
    return new CreateOrderCommand(
            new UserId(user.id()),
            request.lines().stream()
                    .map(line -> new CreateOrderLine(
                            new ProductId(line.productId()),
                            Quantity.of(line.quantity())
                    ))
                    .toList(),
            Optional.ofNullable(request.couponCode()).map(CouponCode::new)
    );
}
```

이 변환 경계가 조금 번거로워 보여도 장점이 크다.

- 외부 JSON 스키마 변경이 도메인 내부로 바로 전파되지 않는다
- 도메인 객체는 더 강한 불변식을 가질 수 있다
- 테스트에서 HTTP/Jackson 없이 command와 domain을 직접 다룰 수 있다
- API 버전 변경과 내부 모델 변경을 분리할 수 있다

### JPA 엔티티는 영속성 모델이다

JPA 엔티티를 `record`로 만들고 싶을 수 있지만 대체로 맞지 않는다.

JPA 엔티티는 보통 다음 조건을 요구한다.

- 식별자 기반 identity
- 지연 로딩 proxy
- 변경 감지
- protected no-arg constructor
- mutable field
- persistence context 생명주기

반면 `record`는 다음 성격이 강하다.

- 값 기반 equality
- final field
- canonical constructor
- 얕은 불변성
- 상속 불가

따라서 JPA 엔티티는 엔티티답게 두고, 도메인 값 객체나 snapshot을 `record`로 두는 편이 보통 안전하다.

```java
@Entity
@Table(name = "orders")
public class OrderEntity {
    @Id
    private Long id;

    @Column(nullable = false)
    private String status;

    private String paymentApprovalNo;
    private String failureCode;
    private String failureMessage;
    private String carrier;
    private String trackingNo;
    private String cancelReason;

    protected OrderEntity() {
    }

    public Order toDomain() {
        return new Order(new OrderId(id), toState());
    }

    private OrderState toState() {
        return switch (status) {
            case "CREATED" -> new OrderState.Created(createdAt);
            case "PAID" -> new OrderState.Paid(paymentApprovalNo, paidAt);
            case "PAYMENT_FAILED" -> new OrderState.PaymentFailed(failureCode, failureMessage, failedAt);
            case "SHIPPED" -> new OrderState.Shipped(carrier, trackingNo, shippedAt);
            case "CANCELLED" -> new OrderState.Cancelled(cancelReason, cancelledAt);
            default -> throw new UnknownOrderStateException(status);
        };
    }
}
```

이 구조의 핵심은 JPA 엔티티를 "도메인의 진짜 모습"으로 보지 않는 것이다. 엔티티는 데이터베이스와 ORM의 제약을 반영하는 모델이고, 도메인 객체는 비즈니스 불변식을 반영하는 모델이다.

물론 모든 프로젝트에서 이렇게 분리해야 하는 것은 아니다. 단순 CRUD라면 엔티티 하나로 충분할 수 있다. 하지만 상태 전이와 정책이 복잡한 영역에서는 분리가 유지보수 비용을 낮춘다.

---

## 실무 예시: 환불 가능한 결제 상태를 타입으로 모델링하기

이제 조금 더 현실적인 예시를 보자.

결제 도메인에는 다음 상태가 있다고 하자.

1. 결제 요청 생성
2. 승인 완료
3. 승인 실패
4. 부분 환불
5. 전체 환불
6. 취소됨

문자열과 nullable 필드로 표현하면 이렇게 된다.

```java
public class Payment {
    private String status;
    private String approvalNo;
    private BigDecimal approvedAmount;
    private BigDecimal refundedAmount;
    private String failureCode;
    private String cancelReason;
}
```

이 모델은 다음 상태를 모두 허용한다.

- 승인 실패인데 승인 번호가 있다
- 전체 환불인데 환불 금액이 승인 금액보다 크다
- 취소됨인데 실패 코드도 있다
- 부분 환불인데 승인 금액이 없다

더 강한 모델로 바꿔 보자.

```java
public sealed interface PaymentState
        permits PaymentState.Requested,
                PaymentState.Approved,
                PaymentState.Failed,
                PaymentState.PartiallyRefunded,
                PaymentState.FullyRefunded,
                PaymentState.Cancelled {

    record Requested(PaymentRequestId requestId, Money requestedAmount) implements PaymentState {
    }

    record Approved(PaymentApprovalNo approvalNo, Money approvedAmount, Instant approvedAt)
            implements PaymentState {
    }

    record Failed(String code, String message, Instant failedAt) implements PaymentState {
    }

    record PartiallyRefunded(
            PaymentApprovalNo approvalNo,
            Money approvedAmount,
            Money refundedAmount,
            Instant lastRefundedAt
    ) implements PaymentState {
        public PartiallyRefunded {
            if (refundedAmount.amount().compareTo(approvedAmount.amount()) >= 0) {
                throw new IllegalArgumentException("partial refund must be less than approved amount");
            }
        }
    }

    record FullyRefunded(
            PaymentApprovalNo approvalNo,
            Money approvedAmount,
            Money refundedAmount,
            Instant refundedAt
    ) implements PaymentState {
        public FullyRefunded {
            if (refundedAmount.amount().compareTo(approvedAmount.amount()) != 0) {
                throw new IllegalArgumentException("full refund must equal approved amount");
            }
        }
    }

    record Cancelled(String reason, Instant cancelledAt) implements PaymentState {
    }
}
```

이제 환불 정책을 구현한다.

```java
public Payment refund(Money amount, Instant refundedAt) {
    return switch (state) {
        case PaymentState.Approved approved ->
                withRefundFromApproved(approved, amount, refundedAt);
        case PaymentState.PartiallyRefunded partial ->
                withAdditionalRefund(partial, amount, refundedAt);
        case PaymentState.Requested ignored ->
                throw new PaymentNotApprovedException(id);
        case PaymentState.Failed failed ->
                throw new PaymentFailedAlreadyException(id, failed.code());
        case PaymentState.FullyRefunded ignored ->
                throw new PaymentAlreadyRefundedException(id);
        case PaymentState.Cancelled ignored ->
                throw new PaymentCancelledException(id);
    };
}
```

보통 이 코드는 if문보다 길다. 하지만 더 많은 정보를 담는다.

- 환불 가능한 상태는 `Approved`, `PartiallyRefunded`뿐이다
- 나머지 상태는 왜 불가능한지 예외가 다르다
- 새 상태가 추가되면 환불 정책도 컴파일러가 다시 묻는다
- 부분 환불과 전체 환불의 금액 규칙은 생성자에서 막는다

도우미 메서드는 금액 계산을 분리한다.

```java
private Payment withRefundFromApproved(
        PaymentState.Approved approved,
        Money refundAmount,
        Instant refundedAt
) {
    Money approvedAmount = approved.approvedAmount();

    if (refundAmount.equals(approvedAmount)) {
        return new Payment(
                id,
                new PaymentState.FullyRefunded(
                        approved.approvalNo(),
                        approvedAmount,
                        refundAmount,
                        refundedAt
                )
        );
    }

    if (refundAmount.amount().compareTo(approvedAmount.amount()) > 0) {
        throw new RefundAmountExceededException(id);
    }

    return new Payment(
            id,
            new PaymentState.PartiallyRefunded(
                    approved.approvalNo(),
                    approvedAmount,
                    refundAmount,
                    refundedAt
            )
    );
}
```

여기서 중요한 건 "예쁘게 추상화했다"가 아니다. 정책의 위험 지점이 코드에 잘 보인다는 것이다.

- 승인 금액보다 큰 환불
- 부분 환불과 전체 환불의 경계
- 이미 환불된 결제에 대한 재시도
- 실패 또는 취소된 결제에 대한 잘못된 명령

이 지점들이 `String status` 비교 속에 묻히지 않는다.

---

## 트레이드오프 1: 타입 안정성을 얻는 대신 매핑 비용이 늘어난다

강한 타입 모델링은 공짜가 아니다.

가장 먼저 늘어나는 비용은 매핑 코드다.

- API request DTO에서 command로 변환
- command에서 domain value object 생성
- domain에서 JPA entity로 변환
- JPA entity row에서 sealed state 복원
- domain에서 response DTO로 변환
- event payload로 변환

작은 기능에서는 이 매핑이 과해 보인다.

```java
String userId = request.userId();
```

이면 끝날 코드를 아래처럼 쓰게 된다.

```java
UserId userId = new UserId(request.userId());
```

하지만 이 비용은 항상 낭비가 아니다. `UserId`, `OrderId`, `ProductId`가 모두 `String`이면 파라미터 순서가 뒤바뀌어도 컴파일러가 잡지 못한다.

```java
orderService.createOrder(productId, userId);
```

두 값이 모두 문자열이면 실수가 런타임까지 간다. 값 객체로 나누면 컴파일 단계에서 막힌다.

```java
orderService.createOrder(new UserId(userId), new ProductId(productId));
```

따라서 기준은 다음이다.

- 여러 도메인 ID가 같은 primitive 타입으로 섞이는가
- 잘못된 값이 들어왔을 때 장애 비용이 큰가
- 검증과 정규화가 여러 곳에서 반복되는가
- 해당 타입이 도메인 언어로 자주 등장하는가
- 테스트에서 fixture가 너무 장황해지지는 않는가

이 질문에서 "예"가 많으면 매핑 비용을 감수할 가치가 있다.

---

## 트레이드오프 2: sealed hierarchy는 닫힌 세계에는 강하지만 플러그인 구조에는 불편하다

`sealed`는 하위 타입을 제한한다. 이 제한이 장점이면서 단점이다.

주문 상태처럼 애플리케이션 내부에서 통제하는 닫힌 집합에는 잘 맞는다. 하지만 외부 모듈이 상태나 전략을 추가해야 하는 구조라면 불편하다.

예를 들어 결제 수단이 카드, 계좌이체, 간편결제 정도로 내부에서만 관리된다면 sealed type이 괜찮다.

```java
public sealed interface PaymentMethod
        permits CardPayment, BankTransfer, WalletPayment {
}
```

하지만 여러 파트너가 결제 수단을 플러그인처럼 추가해야 한다면 sealed type은 확장성을 막을 수 있다.

이런 경우에는 일반 interface와 registry 패턴이 더 나을 수 있다.

```java
public interface PaymentMethodHandler {
    boolean supports(String methodCode);

    PaymentResult pay(PaymentCommand command);
}
```

즉 sealed type은 "앞으로 절대 안 바뀐다"는 선언이 아니다. 더 정확히는 **변경이 이 모듈의 소유권 안에서 일어난다**는 선언이다.

실무 선택 기준은 다음이다.

- 같은 코드베이스 안에서 상태 집합을 관리한다면 sealed가 잘 맞다
- 외부 팀이나 플러그인이 subtype을 추가해야 한다면 일반 interface가 낫다
- 컴파일러 exhaustiveness가 중요한 정책 분기라면 sealed가 유리하다
- 런타임 discovery와 확장성이 중요하다면 sealed는 불리하다

---

## 트레이드오프 3: pattern matching은 분기를 명확하게 만들지만 비즈니스 규칙을 흩뜨릴 수도 있다

pattern matching `switch`는 읽기 좋다. 하지만 아무 곳에나 쓰면 도메인 규칙이 여러 계층에 흩어진다.

예를 들어 컨트롤러, 서비스, 이벤트 핸들러, 배치 코드가 모두 `PaymentState`를 switch한다고 하자.

```java
return switch (payment.state()) {
    case PaymentState.Approved approved -> ...
    case PaymentState.PartiallyRefunded partial -> ...
    case PaymentState.FullyRefunded refunded -> ...
    case PaymentState.Requested requested -> ...
    case PaymentState.Failed failed -> ...
    case PaymentState.Cancelled cancelled -> ...
};
```

상태별 표현은 괜찮다. 하지만 상태별 정책이 여러 곳에 퍼지면 위험하다.

- 환불 가능 여부를 A 서비스와 B 배치가 다르게 해석한다
- 화면 노출 문구와 실제 전이 정책이 섞인다
- 새 상태 추가 시 수정할 switch가 너무 많아진다
- 분기 누락은 줄었지만 정책 중복은 늘어난다

따라서 switch를 쓸 때는 성격을 나눠야 한다.

- 표현 변환: response DTO, 로그 문구, metric label
- 정책 결정: 상태 전이, 권한, 금액 계산, 이벤트 발행

표현 변환은 여러 곳에 있어도 괜찮을 수 있다. 정책 결정은 되도록 도메인 메서드나 도메인 서비스에 모으는 편이 낫다.

좋은 냄새:

```java
public boolean refundable() {
    return switch (state) {
        case PaymentState.Approved ignored -> true;
        case PaymentState.PartiallyRefunded ignored -> true;
        case PaymentState.Requested ignored -> false;
        case PaymentState.Failed ignored -> false;
        case PaymentState.FullyRefunded ignored -> false;
        case PaymentState.Cancelled ignored -> false;
    };
}
```

나쁜 냄새:

```java
// Controller
if (payment.state() instanceof PaymentState.Approved) {
    refundService.refund(payment.id(), amount);
}
```

컨트롤러가 정책을 결정하기 시작하면 도메인 모델의 의미가 약해진다. 컨트롤러는 명령을 전달하고, 환불 가능 여부는 도메인 또는 애플리케이션 서비스가 판단하는 편이 낫다.

---

## 흔한 실수 1: `record`에 비즈니스 규칙이 아니라 프레임워크 편의만 쌓는다

`record`를 DTO로 쓰는 것은 좋다. 문제는 DTO와 도메인을 구분하지 않은 채 모든 것을 하나의 record에 넣는 것이다.

```java
public record OrderRequest(
        @NotBlank String userId,
        @NotEmpty List<OrderLineRequest> lines,
        String status,
        String paymentApprovalNo,
        String trackingNo
) {
}
```

이 타입은 요청인지, 내부 명령인지, 상태 저장용인지 모호하다.

실무에서는 다음 구분이 필요하다.

- Request DTO: 외부 입력 모양
- Command: 유스케이스 실행에 필요한 내부 입력
- Domain object: 비즈니스 불변식과 상태 전이
- Entity: 저장소 매핑
- Response DTO: 외부 출력 모양

모든 계층을 무조건 나누라는 뜻은 아니다. 하지만 복잡도가 올라간 모델에서 한 타입이 모든 역할을 하면 결국 어떤 제약도 제대로 표현하지 못한다.

---

## 흔한 실수 2: compact constructor에서 검증 순서를 놓친다

`record`의 compact constructor는 편하지만 검증과 정규화 순서를 조심해야 한다.

```java
public record Username(String value) {
    public Username {
        if (value.length() < 3) {
            throw new IllegalArgumentException("too short");
        }
        value = value.trim();
    }
}
```

이 코드는 공백 제거 전에 길이를 검사한다. `"  a  "` 같은 값이 통과할 수 있다.

더 나은 순서는 정규화 후 검증이다.

```java
public record Username(String value) {
    public Username {
        if (value == null) {
            throw new IllegalArgumentException("username must not be null");
        }
        value = value.trim();
        if (value.length() < 3) {
            throw new IllegalArgumentException("username must be at least 3 characters");
        }
    }
}
```

값 객체 생성자는 작아야 하지만 대충 써도 된다는 뜻은 아니다. 그 타입의 모든 인스턴스가 이 생성자를 통과한다는 점에서 오히려 중요하다.

---

## 흔한 실수 3: `Optional`을 record 필드에 무분별하게 넣는다

`Optional`은 반환 타입에서 "없을 수 있음"을 표현할 때 유용하다. 하지만 record 필드에 무분별하게 넣으면 모델이 오히려 시끄러워질 수 있다.

```java
public record UserProfile(
        UserId id,
        Optional<String> nickname,
        Optional<String> avatarUrl,
        Optional<Instant> deletedAt
) {
}
```

이것이 항상 틀린 것은 아니다. 하지만 내부 모델에서 `Optional` 필드가 많아지면 다음 문제가 생긴다.

- JSON 직렬화 정책이 번거로워진다
- JPA/ORM 매핑과 잘 맞지 않는다
- 값이 필수인지 선택인지 생성자에서 충분히 표현하지 못한다
- 상태별로 필요한 값이 다른 문제를 Optional로 덮어 버린다

특히 상태별 필수 데이터 차이를 `Optional`로 표현하고 있다면 sealed type이 더 나을 수 있다.

```java
public record Subscription(
        SubscriptionStatus status,
        Optional<Instant> trialEndsAt,
        Optional<Instant> cancelledAt,
        Optional<String> cancellationReason
) {
}
```

이 모델은 trial, active, cancelled 상태를 하나의 타입에 몰아넣은 냄새일 수 있다.

```java
public sealed interface SubscriptionState
        permits Trial, Active, Cancelled {
}

public record Trial(Instant endsAt) implements SubscriptionState {
}

public record Active(Instant activatedAt) implements SubscriptionState {
}

public record Cancelled(Instant cancelledAt, String reason) implements SubscriptionState {
}
```

기준은 간단하다.

- 단순 부가 정보가 없을 수 있다: `Optional` 또는 nullable 정책
- 상태에 따라 필수 필드가 달라진다: sealed type 검토

---

## 흔한 실수 4: `sealed`를 모든 전략 패턴의 대체재로 쓴다

`sealed`는 하위 타입의 범위를 닫는다. 전략 패턴은 보통 확장 가능성을 열어 둔다.

할인 정책을 예로 들자.

```java
public sealed interface DiscountPolicy
        permits FixedAmountDiscount, RateDiscount, NoDiscount {
    Money apply(Money price);
}
```

초기에는 좋다. 하지만 마케팅 팀이 매주 새 정책을 만들고, A/B 테스트마다 조합이 바뀌고, 외부 설정으로 정책을 로딩해야 한다면 sealed hierarchy는 불편해진다.

이 경우에는 데이터 기반 규칙 엔진이나 일반 interface 기반 registry가 더 맞을 수 있다.

```java
public interface DiscountPolicy {
    String code();

    Money apply(Money price, DiscountContext context);
}
```

sealed type은 확장 지점이 아니라 제한 지점이다. 제한이 요구사항과 맞을 때 써야 한다.

---

## 흔한 실수 5: persistence schema를 타입 모델에 그대로 맞추려 한다

sealed state를 만들면 데이터베이스도 상태별 테이블로 나눠야 할 것 같지만, 항상 그렇지는 않다.

선택지는 여러 가지다.

1. 단일 테이블 + status 컬럼 + nullable 보조 컬럼
2. 단일 테이블 + JSON 컬럼에 상태별 payload 저장
3. 상태별 서브 테이블
4. 이벤트 소싱으로 상태 전이를 이벤트로 저장

각각 장단점이 있다.

단일 테이블은 단순하고 조회가 쉽지만 nullable 컬럼이 많아질 수 있다. JSON 컬럼은 상태별 payload를 담기 좋지만 쿼리와 migration이 까다로워질 수 있다. 서브 테이블은 정규화가 강하지만 join과 ORM mapping이 복잡해진다. 이벤트 소싱은 상태 전이 추적에 강하지만 시스템 전체 설계 비용이 크다.

중요한 것은 도메인 타입과 저장 스키마를 1:1로 맞추려는 강박을 버리는 것이다.

도메인 내부에서는 sealed type으로 안전하게 다루고, 저장 경계에서는 row mapper가 변환 책임을 가져도 된다.

```java
public PaymentState toState(PaymentRow row) {
    return switch (row.status()) {
        case "REQUESTED" -> new PaymentState.Requested(
                new PaymentRequestId(row.requestId()),
                new Money(row.requestedAmount(), row.currency())
        );
        case "APPROVED" -> new PaymentState.Approved(
                new PaymentApprovalNo(row.approvalNo()),
                new Money(row.approvedAmount(), row.currency()),
                row.approvedAt()
        );
        case "FAILED" -> new PaymentState.Failed(
                row.failureCode(),
                row.failureMessage(),
                row.failedAt()
        );
        case "PARTIALLY_REFUNDED" -> new PaymentState.PartiallyRefunded(
                new PaymentApprovalNo(row.approvalNo()),
                new Money(row.approvedAmount(), row.currency()),
                new Money(row.refundedAmount(), row.currency()),
                row.lastRefundedAt()
        );
        case "FULLY_REFUNDED" -> new PaymentState.FullyRefunded(
                new PaymentApprovalNo(row.approvalNo()),
                new Money(row.approvedAmount(), row.currency()),
                new Money(row.refundedAmount(), row.currency()),
                row.refundedAt()
        );
        case "CANCELLED" -> new PaymentState.Cancelled(row.cancelReason(), row.cancelledAt());
        default -> throw new UnknownPaymentStateException(row.status());
    };
}
```

매핑 코드는 지루하지만 중요한 방어선이다. 외부 저장소의 느슨한 데이터를 내부의 강한 모델로 복원하는 문이다.

---

## 테스트 전략: 타입 모델은 테스트 수를 줄이지만, 매핑 테스트는 더 중요해진다

강한 타입 모델을 만들면 일부 방어 테스트는 줄어든다.

예를 들어 `Money` 생성자가 음수를 막는다면, 모든 서비스 메서드에서 음수 금액 방어를 반복 테스트할 필요가 줄어든다.

```java
@Test
void money_rejects_negative_amount() {
    assertThatThrownBy(() -> new Money(new BigDecimal("-1.00"), Currency.getInstance("KRW")))
            .isInstanceOf(IllegalArgumentException.class);
}
```

대신 다음 테스트가 중요해진다.

- 값 객체 생성자 검증
- 상태 전이 메서드
- sealed state별 exhaustive 정책
- DTO to command 변환
- entity row to domain 변환
- domain to response 변환
- unknown external state 처리

상태 전이 테스트는 테이블 기반으로 쓰면 좋다.

```java
@ParameterizedTest
@MethodSource("nonRefundableStates")
void refund_rejects_non_refundable_states(PaymentState state) {
    Payment payment = new Payment(new PaymentId("p1"), state);

    assertThatThrownBy(() -> payment.refund(krw("1000"), Instant.now()))
            .isInstanceOf(PaymentRefundRejectedException.class);
}

static Stream<PaymentState> nonRefundableStates() {
    return Stream.of(
            new PaymentState.Requested(new PaymentRequestId("r1"), krw("1000")),
            new PaymentState.Failed("CARD_DECLINED", "declined", Instant.now()),
            new PaymentState.FullyRefunded(
                    new PaymentApprovalNo("a1"),
                    krw("1000"),
                    krw("1000"),
                    Instant.now()
            ),
            new PaymentState.Cancelled("user cancelled", Instant.now())
    );
}
```

테스트 기준은 "모든 분기를 다 찍자"가 아니다.

- 불가능한 상태가 생성되지 않는지
- 중요한 전이가 잘못 허용되지 않는지
- 외부 데이터가 내부 모델로 들어올 때 깨진 값을 막는지
- 새 상태 추가 시 테스트 fixture가 수정 필요성을 드러내는지

이 네 가지가 핵심이다.

---

## 운영 관점: 강한 타입 모델은 장애를 없애지 않고 장애 위치를 앞당긴다

타입 모델링을 잘하면 모든 장애가 사라질까? 아니다.

대신 장애가 더 빠르고 좁은 위치에서 드러난다.

문자열 상태 모델에서는 잘못된 데이터가 여러 계층을 지나가다가 이상한 곳에서 터질 수 있다.

- 화면 응답에서 NPE
- 배치 집계에서 잘못된 금액 계산
- 환불 API에서 외부 PG 오류
- 이벤트 컨슈머에서 알 수 없는 상태 무시

강한 타입 모델에서는 변환 경계나 생성자에서 더 빨리 실패한다.

```java
new PaymentState.FullyRefunded(approvalNo, approvedAmount, refundedAmount, refundedAt);
```

여기서 금액 불변식이 맞지 않으면 바로 예외가 난다. 운영에서는 이 예외를 잘 관측해야 한다.

따라서 다음 로그와 metric이 필요하다.

- unknown external status count
- domain mapping failure count
- invalid transition count
- validation failure reason
- state transition success/failure count
- state별 command 처리량

단순히 예외를 던지는 것만으로는 부족하다. 강한 모델이 막은 잘못된 입력이 얼마나 자주 발생하는지 관측해야 한다.

예를 들어 외부 PG에서 새 결제 상태가 추가됐는데 우리 시스템이 모른다면, mapper에서 예외가 날 것이다. 이건 좋은 실패다. 하지만 알림이 없으면 운영자는 늦게 안다.

```java
try {
    PaymentState state = paymentStateMapper.toState(row);
    return paymentRepository.save(new Payment(id, state));
} catch (UnknownPaymentStateException e) {
    metrics.counter("payment.state.unknown", "status", e.status()).increment();
    log.error("Unknown payment state from storage. status={}", e.status(), e);
    throw e;
}
```

타입 모델링은 운영 안정성의 끝이 아니라 시작이다. 잘못된 상태를 조용히 흘려보내지 않게 만드는 대신, 그 실패를 관측하고 대응할 책임이 생긴다.

---

## 단계적 도입 전략: 핵심 불변식부터 작게 올린다

기존 코드베이스에 `record`, `sealed`, pattern matching을 한 번에 적용하면 실패하기 쉽다.

추천하는 순서는 다음이다.

1. primitive obsession이 심한 값부터 record value object로 뺀다
2. 검증과 정규화가 반복되는 타입을 먼저 고른다
3. 상태별 nullable 필드가 많은 모델 하나를 sealed state로 분리한다
4. 내부 도메인 모델과 외부 DTO를 분리한다
5. mapper 테스트를 추가한다
6. 상태별 정책 switch에서 `default`를 제거한다
7. JPA entity는 당장 크게 바꾸지 말고 변환 경계를 먼저 만든다
8. 관측 지표를 추가한다

예를 들어 첫 번째 단계는 아주 작을 수 있다.

```java
public record OrderId(String value) {
    public OrderId {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException("orderId must not be blank");
        }
    }
}
```

이 작은 타입 하나만으로도 다음 실수를 줄인다.

- `OrderId`와 `UserId` 파라미터 혼동
- 빈 문자열 ID 전달
- 로그와 metric에서 ID 타입 혼동
- 테스트 fixture에서 의미 없는 문자열 남발

그다음 상태 모델을 분리한다.

```java
public sealed interface OrderState permits Created, Paid, Cancelled {
}
```

그리고 가장 위험한 유스케이스 하나에만 적용한다.

```java
public Order cancel(CancelReason reason, Instant now) {
    return switch (state) {
        case Created ignored -> new Order(id, new Cancelled(reason.value(), now));
        case Paid paid -> throw new RefundRequiredException(id, paid.approvalNo());
        case Cancelled ignored -> this;
    };
}
```

작게 적용해도 효과를 볼 수 있는 지점부터 시작해야 한다. 전체 모델을 한 번에 갈아엎는 것은 대부분의 팀에서 비용이 너무 크다.

---

## 코드 리뷰 체크리스트: Java 타입 모델링을 볼 때 묻는 질문

`record`, `sealed`, pattern matching을 코드 리뷰할 때는 문법보다 의도를 본다.

- 이 `record`는 단순 DTO인가, 값 객체인가
- 값 객체라면 생성자에서 핵심 불변식을 검증하는가
- 컬렉션 필드는 방어 복사를 하는가
- `BigDecimal`, `String`, `Long` 같은 primitive-like 타입이 도메인 의미를 잃고 돌아다니지 않는가
- 상태별 필수 데이터 차이를 nullable 필드로 덮고 있지 않은가
- enum으로 충분한 문제를 sealed hierarchy로 과하게 키우지 않았는가
- sealed type의 하위 타입 집합은 이 모듈이 소유하는가
- pattern matching switch에 불필요한 `default`가 들어가 있지 않은가
- 상태별 정책이 컨트롤러나 배치 곳곳에 흩어지지 않았는가
- API DTO와 도메인 모델이 서로 다른 변경 이유를 갖는데 한 타입으로 묶여 있지 않은가
- JPA entity를 억지로 불변 record처럼 만들려다 ORM 제약과 싸우고 있지 않은가
- mapper에서 unknown external state를 조용히 무시하지 않는가
- 새 상태가 추가됐을 때 어떤 테스트와 switch가 실패해야 하는지 명확한가
- 예외 메시지와 metric은 운영자가 원인을 찾을 수 있을 만큼 구체적인가

좋은 타입 모델은 멋있어 보이는 구조가 아니라, 팀원이 잘못된 코드를 쓰기 어렵게 만드는 구조다.

---

## 한 번 더 요약: 어디에 무엇을 쓰면 좋은가

`record`가 잘 맞는 곳:

- 값 객체
- command
- response DTO
- event payload
- read model snapshot
- 작은 불변 계산 결과

`record`가 애매한 곳:

- JPA entity
- 변경 감지가 필요한 객체
- identity 기반 생명주기를 갖는 aggregate root
- 내부에 큰 mutable graph를 들고 있는 객체
- 상속이 필요한 프레임워크 모델

`sealed`가 잘 맞는 곳:

- 상태별 데이터 모양이 다른 domain state
- 컴파일러가 누락 분기를 잡아야 하는 정책
- 내부 모듈이 하위 타입 집합을 소유하는 모델
- 실패/성공/부분성공처럼 결과 모양이 다른 유스케이스 반환

`sealed`가 애매한 곳:

- 플러그인처럼 외부 확장이 필요한 전략
- DB 코드 테이블처럼 런타임 추가가 자연스러운 값
- 단순 enum으로 충분한 상태
- 하위 타입이 너무 자주 바뀌는 실험적 정책

pattern matching이 잘 맞는 곳:

- sealed state를 response로 변환
- 상태별 metric label 생성
- 상태별 정책을 한곳에서 명시
- 타입별 command 결과 처리

pattern matching이 위험해지는 곳:

- 같은 정책 switch가 여러 계층에 복사될 때
- `default`로 새 상태를 조용히 숨길 때
- controller가 도메인 정책을 직접 판단할 때
- 외부 입력의 불확실성을 내부 모델 전체로 퍼뜨릴 때

---

## 결론: 타입은 문서가 아니라 실행되는 제약이다

문서에 "결제 완료 상태에는 승인 번호가 필요하다"고 적을 수 있다. 주석에 "취소 상태에서는 배송 정보가 없어야 한다"고 남길 수도 있다. 하지만 문서와 주석은 실행되지 않는다.

타입은 다르다.

`record` 생성자는 값을 만들 때마다 실행된다. `sealed interface`는 허용된 상태 집합을 제한한다. pattern matching `switch`는 상태별 분기를 코드에 드러낸다. exhaustive switch는 새 상태가 추가됐을 때 누락된 처리를 알려줄 수 있다.

Java의 최신 타입 모델링 기능을 잘 쓴다는 것은 유행 문법을 적용하는 일이 아니다. 팀이 자주 실수하는 비즈니스 규칙을 컴파일러와 생성자, 변환 경계에 나눠 맡기는 일이다.

좋은 기준은 단순하다.

- 값의 의미가 중요하면 primitive 대신 값 객체를 만든다
- 상태별 데이터가 다르면 nullable 필드 대신 sealed state를 검토한다
- 상태별 정책이 중요하면 exhaustive switch로 누락을 드러낸다
- 외부 DTO, JPA entity, domain model의 변경 이유를 섞지 않는다
- 타입 모델링으로 막은 실패는 metric과 로그로 관측한다

과하게 쓰면 코드가 장황해진다. 적게 쓰면 중요한 규칙이 런타임 어딘가로 새어 나간다. 실무의 균형점은 "모든 것을 타입으로 만들자"가 아니라, **깨졌을 때 비용이 큰 규칙부터 타입으로 끌어올리자**에 있다.

## 한 줄 정리

Java의 `record`, `sealed`, pattern matching은 코드를 짧게 쓰는 문법이 아니라, 도메인의 불가능한 상태를 줄이고 새 상태 추가의 위험을 컴파일 시점으로 앞당기는 설계 도구다.
