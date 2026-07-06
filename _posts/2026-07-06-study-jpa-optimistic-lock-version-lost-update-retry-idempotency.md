---
layout: post
title: "JPA 낙관적 락 실전: @Version, Lost Update, 재시도, 멱등성으로 동시성 정합성을 지키는 법"
date: 2026-07-06 11:50:00 +0900
categories: [java]
tags: [study, java, spring, jpa, hibernate, optimistic-lock, version, concurrency, lost-update, retry, idempotency, backend, operations]
permalink: /java/2026/07/06/study-jpa-optimistic-lock-version-lost-update-retry-idempotency.html
---

## 배경: 동시성 버그는 "트래픽이 많을 때만" 생기는 문제가 아니다

JPA를 쓰는 서비스에서 동시성 문제는 생각보다 조용히 들어온다.

처음에는 모든 테스트가 통과한다. 로컬에서 주문을 생성하고, 재고를 차감하고, 쿠폰을 쓰고, 포인트를 적립해도 아무 문제 없어 보인다. 하지만 운영에서는 다음 같은 현상이 생긴다.

- 상품 재고가 1개였는데 주문이 2건 성공했다.
- 관리자 두 명이 같은 설정을 수정했는데 나중에 저장한 값이 앞선 변경을 덮어썼다.
- 사용자 포인트 차감 요청이 동시에 들어와 잔액이 음수가 됐다.
- 결제 승인 콜백과 사용자 취소 요청이 거의 동시에 들어와 주문 상태가 이상하게 꼬였다.
- 배치가 회원 등급을 갱신하는 동안 API가 같은 회원의 등급을 바꿔 일부 변경이 사라졌다.
- 실패한 요청을 재시도했더니 실제로는 두 번 처리됐다.
- `@Transactional`을 붙였는데도 "마지막 저장이 이기는" 문제가 사라지지 않았다.

이런 문제를 처음 만나면 보통 DB 락이나 트랜잭션 격리 수준부터 떠올린다. 물론 중요하다. 하지만 실무에서 더 자주 놓치는 지점은 따로 있다.

**트랜잭션은 동시성 정합성의 출발점이지, 비즈니스 충돌을 자동으로 해결해 주는 장치가 아니다.**

트랜잭션은 여러 SQL을 하나의 원자적 단위로 묶어 준다. 하지만 두 트랜잭션이 같은 row를 읽고 서로 다른 의도로 수정할 때, 어떤 변경을 허용하고 어떤 변경을 거절할지는 애플리케이션이 명시해야 한다. 특히 JPA의 dirty checking은 편리하지만, 동시에 "읽은 값을 바탕으로 나중에 update한다"는 구조를 자연스럽게 만들기 때문에 lost update를 숨기기 쉽다.

오늘 글은 중급 이상 Java 개발자를 기준으로 JPA에서 낙관적 락을 운영 가능한 수준으로 설계하는 법을 정리한다.

다룰 내용은 다음과 같다.

1. Lost Update가 왜 생기는가
2. `@Version`이 실제로 어떤 SQL과 예외를 만드는가
3. 낙관적 락과 비관적 락을 어떻게 구분해서 써야 하는가
4. 재시도는 언제 안전하고, 언제 더 위험한가
5. 멱등성 키와 상태 전이 조건이 왜 함께 필요 한가
6. JPA 엔티티, API, 배치, 메시지 컨슈머에서 어떤 패턴을 써야 하는가
7. 운영에서 어떤 로그와 지표로 충돌을 관찰해야 하는가

핵심 결론부터 말하면 이렇다.

**JPA 낙관적 락의 목적은 충돌을 없애는 것이 아니라, 조용히 덮어써질 변경을 명시적으로 실패시키고, 그 실패를 도메인 정책에 맞게 재조회·재시도·사용자 확인·보상 처리로 연결하는 것이다.**

`@Version` 하나를 붙이면 모든 동시성 문제가 해결된다고 생각하면 위험하다. `@Version`은 충돌 감지 장치다. 충돌을 어떻게 처리할지는 서비스 계층, API 계약, 메시지 처리, 사용자 경험, 운영 지표까지 같이 설계해야 한다.

---

## 문제 정의: Lost Update는 "두 번 저장했는데 마지막 값만 남는" 가장 흔한 정합성 사고다

가장 단순한 예제로 시작하자. 회원 프로필에 `nickname`과 `phone`이 있고, 관리자 화면에서 수정할 수 있다고 하자.

```java
@Transactional
public void updateProfile(Long memberId, UpdateProfileCommand command) {
    Member member = memberRepository.findById(memberId)
            .orElseThrow();

    member.changeProfile(command.nickname(), command.phone());
}
```

코드는 자연스럽다. 서비스 메서드 내부에서 엔티티를 조회하고, 도메인 메서드를 호출하고, 트랜잭션 커밋 시점에 dirty checking으로 update가 나간다.

문제는 두 요청이 겹칠 때다.

```text
T1: member(id=10, nickname="kim", phone="010-1111") 조회
T2: member(id=10, nickname="kim", phone="010-1111") 조회

T1: nickname을 "lee"로 변경
T2: phone을 "010-2222"로 변경

T1: commit
T2: commit
```

최종 결과가 어떻게 될까?

구현 방식에 따라 다르지만, 흔히 이런 결과가 나온다.

```text
nickname = "kim"
phone    = "010-2222"
```

T1이 바꾼 `nickname="lee"`가 사라졌다. T2는 닉네임을 바꿀 의도가 없었지만, T2가 들고 있던 오래된 엔티티 스냅샷을 기준으로 update가 나가면서 T1의 변경을 덮어쓸 수 있다. 이것이 lost update다.

물론 Hibernate의 기본 dirty checking은 변경된 컬럼만 update하는 방식처럼 보일 때가 많고, `@DynamicUpdate`를 쓰면 더 명확히 변경 컬럼만 update할 수 있다. 하지만 그걸로 lost update 문제가 해결됐다고 보면 안 된다.

왜냐하면 실무 충돌은 컬럼 단위로만 판단할 수 없기 때문이다.

- 닉네임과 전화번호는 독립 변경일 수 있다.
- 주문 상태와 결제 상태는 독립 변경이 아닐 수 있다.
- 재고 수량과 예약 수량은 같은 불변식을 공유할 수 있다.
- 회원 등급과 포인트 잔액은 계산 기준 시점이 맞아야 할 수 있다.
- 설정 JSON 하나 안에서 서로 다른 필드를 수정하더라도 전체 설정 버전은 충돌해야 할 수 있다.

즉 "같은 컬럼을 덮어썼는가"보다 중요한 질문은 이것이다.

> 내가 읽은 상태를 기준으로 내 변경을 적용해도 여전히 유효한가?

낙관적 락은 이 질문을 row version으로 다룬다. 내가 읽은 version과 DB의 현재 version이 다르면, 그 사이에 누군가 같은 aggregate를 바꿨다는 뜻이므로 update를 실패시킨다.

---

## 핵심 개념 1: `@Version`은 update 조건에 version을 추가해 충돌을 감지한다

JPA의 낙관적 락은 보통 엔티티에 version 필드를 추가하는 방식으로 시작한다.

```java
@Entity
public class Member {

    @Id
    private Long id;

    private String nickname;
    private String phone;

    @Version
    private Long version;

    protected Member() {
    }

    public void changeProfile(String nickname, String phone) {
        if (nickname == null || nickname.isBlank()) {
            throw new IllegalArgumentException("nickname is blank");
        }
        this.nickname = nickname;
        this.phone = phone;
    }
}
```

이제 `Member`를 조회하면 JPA는 `version` 값도 함께 들고 온다.

```sql
select
    m.id,
    m.nickname,
    m.phone,
    m.version
from member m
where m.id = ?
```

현재 version이 `7`이라고 하자. 트랜잭션 안에서 엔티티를 수정하고 flush하면 Hibernate는 대략 다음 형태의 update를 만든다.

```sql
update member
set
    nickname = ?,
    phone = ?,
    version = ?
where
    id = ?
    and version = ?
```

바인딩 관점으로 보면 이런 의미다.

```text
set version = 8
where id = 10 and version = 7
```

만약 그 사이에 다른 트랜잭션이 먼저 커밋해서 version을 `8`로 올렸다면, 이 update는 영향을 받은 row 수가 0이 된다. JPA는 "내가 읽은 version의 row가 더 이상 없다"고 판단하고 낙관적 락 예외를 던진다.

Spring 환경에서는 보통 다음 예외 계층으로 만난다.

- JPA/Hibernate 레벨: `OptimisticLockException`, `StaleObjectStateException`
- Spring 변환 후: `ObjectOptimisticLockingFailureException`, `OptimisticLockingFailureException`

중요한 점은 이것이다.

**낙관적 락은 DB가 row를 오래 잠그는 방식이 아니라, update 시점에 version 조건이 맞는지 확인하는 방식이다.**

그래서 이름 그대로 "충돌이 자주 나지 않을 것"이라고 낙관하고 진행한다. 충돌이 없으면 별도 대기 없이 빠르게 끝난다. 충돌이 있으면 뒤늦게 실패한다.

### version 필드는 비즈니스 필드가 아니다

`version`은 사용자가 입력하거나 업무 의미를 갖는 값이 아니다. JPA가 동시성 제어를 위해 관리하는 기술 필드다.

따라서 보통 다음 기준을 둔다.

- 요청 DTO에서 `version`을 직접 수정하지 않는다.
- 엔티티 메서드에서 `version++` 같은 코드를 쓰지 않는다.
- `version`은 API 응답에는 노출할 수 있지만, "수정 가능한 필드"처럼 취급하지 않는다.
- 관리자 화면이나 API에서는 충돌 감지를 위해 "내가 봤던 version"을 조건으로 활용할 수 있다.

예를 들어 관리자가 상품 정보를 수정하는 화면이라면 조회 응답에 version을 내려주고, 수정 요청에 그 version을 다시 받는 방식이 유용하다.

```java
public record ProductEditResponse(
        Long id,
        String name,
        int price,
        long version
) {
}

public record UpdateProductRequest(
        String name,
        int price,
        long version
) {
}
```

서비스에서는 엔티티의 현재 version과 요청 version을 비교해 더 친절한 오류를 만들 수 있다.

```java
@Transactional
public void updateProduct(Long productId, UpdateProductRequest request) {
    Product product = productRepository.findById(productId)
            .orElseThrow();

    if (product.version() != request.version()) {
        throw new StaleProductEditException(productId);
    }

    product.changeBasicInfo(request.name(), request.price());
}
```

이 비교는 사용자 경험을 개선하는 선제 검증이다. 최종 안전장치는 여전히 flush 시점의 `where version = ?`다. 선제 검증과 실제 update 사이에도 다른 트랜잭션이 끼어들 수 있기 때문이다.

---

## 핵심 개념 2: 낙관적 락은 aggregate 단위의 충돌 감지에 잘 맞는다

낙관적 락을 어디에 붙일지 결정할 때는 테이블보다 aggregate를 먼저 봐야 한다.

예를 들어 주문 도메인을 생각해 보자.

```text
Order
  - id
  - status
  - totalAmount
  - paymentStatus
  - deliveryStatus
  - version

OrderLine
  - id
  - orderId
  - productId
  - quantity
  - price
```

주문 상태 전이는 단순 컬럼 수정이 아니다.

- `CREATED`에서 `PAID`로 갈 수 있다.
- `PAID`에서 `SHIPPING`으로 갈 수 있다.
- `SHIPPING` 이후에는 일반 취소가 안 될 수 있다.
- 결제 콜백과 사용자 취소가 충돌할 수 있다.
- 배송 시작 후 주문 금액 변경은 금지될 수 있다.

이런 경우에는 `Order` root에 version을 두고, 주문 aggregate에 대한 중요한 변경이 같은 version 경계를 공유하도록 만드는 편이 자연스럽다.

```java
@Entity
public class Order {

    @Id
    private Long id;

    @Enumerated(EnumType.STRING)
    private OrderStatus status;

    private long totalAmount;

    @Version
    private Long version;

    protected Order() {
    }

    public void markPaid(String paymentKey) {
        if (status != OrderStatus.CREATED) {
            throw new IllegalStateException("Only CREATED order can be paid");
        }
        this.status = OrderStatus.PAID;
        this.paymentKey = paymentKey;
    }

    public void cancel() {
        if (status == OrderStatus.SHIPPING || status == OrderStatus.DELIVERED) {
            throw new IllegalStateException("Cannot cancel after shipping");
        }
        this.status = OrderStatus.CANCELLED;
    }
}
```

결제 콜백과 취소 요청이 동시에 들어온다고 하자.

```text
T1: Order version=3, status=CREATED 조회
T2: Order version=3, status=CREATED 조회

T1: markPaid()
T2: cancel()

T1: update where id=? and version=3 -> 성공, version=4
T2: update where id=? and version=3 -> 실패
```

이제 두 변경이 조용히 섞이지 않는다. 둘 중 하나는 명확히 실패한다.

그 다음 정책은 도메인이 결정해야 한다.

- 사용자가 취소 버튼을 눌렀다면 "주문 상태가 변경되었습니다. 새로고침 후 다시 시도해 주세요."라고 안내할 수 있다.
- 결제 콜백이라면 현재 주문을 재조회해 이미 취소됐는지 확인하고 결제 취소 보상을 실행할 수 있다.
- 메시지 컨슈머라면 짧은 backoff 후 재시도하거나 dead letter queue로 보낼 수 있다.

중요한 것은 낙관적 락 예외를 단순히 500 에러로 흘려보내지 않는 것이다. 충돌은 시스템 오류라기보다 비즈니스 경합이다. 경합을 어떤 사용자 경험과 보상 흐름으로 바꿀지가 설계의 핵심이다.

---

## 핵심 개념 3: 비관적 락은 "충돌 감지"가 아니라 "동시 진입 차단"이다

낙관적 락과 비관적 락은 자주 비교되지만, 둘은 문제를 푸는 방식이 다르다.

낙관적 락은 이렇게 말한다.

```text
일단 읽고 처리한다.
커밋 시점에 내가 읽은 버전이 아직 최신이면 성공한다.
아니면 실패한다.
```

비관적 락은 이렇게 말한다.

```text
처리하기 전에 row를 잠근다.
다른 트랜잭션은 내가 끝날 때까지 같은 row를 수정하지 못한다.
```

JPA에서는 repository 쿼리에 `@Lock`을 붙여 비관적 락을 사용할 수 있다.

```java
public interface StockRepository extends JpaRepository<Stock, Long> {

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select s from Stock s where s.productId = :productId")
    Optional<Stock> findByProductIdForUpdate(Long productId);
}
```

DB에서는 보통 `select ... for update` 계열 SQL로 변환된다.

```sql
select *
from stock
where product_id = ?
for update
```

### 언제 낙관적 락이 잘 맞는가

낙관적 락은 보통 다음 상황에 적합하다.

- 충돌 빈도가 낮다.
- 사용자나 시스템이 다시 시도할 수 있다.
- 읽기 비중이 높고 쓰기 경합이 낮다.
- 충돌 시 "최신 상태를 보고 다시 결정"하는 것이 자연스럽다.
- row를 오래 잠그면 오히려 처리량이 나빠진다.

예시는 다음과 같다.

- 관리자 설정 수정
- 회원 프로필 수정
- 게시글 수정
- 주문 상태 전이
- 결제 콜백과 내부 상태 전이
- 배치와 API가 같은 aggregate를 수정할 가능성이 있는 경우

### 언제 비관적 락이 더 적합한가

비관적 락은 다음 상황에서 검토한다.

- 충돌이 매우 자주 발생한다.
- 실패 후 재시도 비용이 더 크다.
- 동시에 처리하면 절대 안 되는 작은 임계 영역이 있다.
- 남은 수량, 좌석, 쿠폰 발급처럼 선착순 경쟁이 강하다.
- 외부 부작용 전에 DB 상태를 확정적으로 예약해야 한다.

예를 들어 재고 1개를 두고 수백 요청이 동시에 경쟁하는 상황에서는 낙관적 락만으로도 정합성은 지킬 수 있다. 하지만 대부분이 실패하고 재시도하면서 DB update 충돌이 폭증할 수 있다. 이때는 다음 중 하나가 더 적합할 수 있다.

- 비관적 락으로 짧게 직렬화한다.
- 원자적 update 조건을 사용한다.
- Redis나 queue로 진입을 제한한다.
- 재고 예약 테이블을 분리한다.
- hot product에 별도 shard/counter 전략을 둔다.

특히 재고 차감은 단순히 `@Version`만 붙이는 것보다 아래 같은 조건부 update가 더 직접적일 때가 많다.

```java
@Modifying
@Query("""
    update Stock s
       set s.quantity = s.quantity - :amount
     where s.productId = :productId
       and s.quantity >= :amount
""")
int decreaseIfEnough(Long productId, int amount);
```

반환 row 수가 1이면 차감 성공, 0이면 재고 부족이다. 이 방식은 version 충돌 예외보다 비즈니스 의도가 명확하다.

다만 이 쿼리는 JPA 영속성 컨텍스트를 우회하는 bulk update에 가깝기 때문에, 같은 트랜잭션에서 이미 조회한 `Stock` 엔티티가 있다면 상태 불일치가 생길 수 있다. 그래서 재고 차감 같은 경로는 아예 repository 메서드 단위로 분리하고, 이후에는 재조회하는 식으로 경계를 분명히 해야 한다.

---

## 핵심 개념 4: 재시도는 "충돌 해결"이 아니라 "정책 재평가"다

낙관적 락 예외를 보면 자동 재시도를 붙이고 싶어진다.

```java
@Retryable(
        retryFor = OptimisticLockingFailureException.class,
        maxAttempts = 3
)
@Transactional
public void updateSomething(Long id) {
    // ...
}
```

하지만 재시도는 조심해야 한다. 낙관적 락 충돌은 단순 네트워크 오류가 아니다. 내가 읽은 상태가 더 이상 최신이 아니라는 신호다. 따라서 재시도는 "같은 계산을 다시 밀어 넣기"가 아니라 "최신 상태를 다시 읽고 비즈니스 규칙을 다시 평가하기"여야 한다.

### 안전한 재시도의 조건

다음 조건을 만족할수록 재시도가 안전하다.

- 연산이 멱등적이다.
- 외부 부작용이 아직 실행되지 않았다.
- 최신 상태 기준으로 같은 의사결정을 다시 해도 된다.
- 충돌 빈도가 낮고 짧은 시간 안에 해소된다.
- 재시도 횟수와 backoff가 제한되어 있다.
- 실패 시 사용자나 운영자가 이해할 수 있는 결과가 남는다.

예를 들어 조회수 증가나 내부 카운터 갱신처럼 "최신 값 기준으로 다시 더하면 되는" 연산은 재시도가 비교적 쉽다. 하지만 결제 승인, 쿠폰 발급, 포인트 차감처럼 외부 부작용과 돈이 걸린 작업은 훨씬 엄격해야 한다.

### 위험한 재시도의 예

아래 흐름은 위험하다.

```java
@Transactional
public void approvePayment(Long orderId, PaymentCommand command) {
    Order order = orderRepository.findById(orderId).orElseThrow();
    PaymentApproval approval = paymentClient.approve(command);
    order.markPaid(approval.paymentKey());
}
```

여기서 `order.markPaid()` flush 시점에 낙관적 락 충돌이 났다고 하자. 단순히 메서드 전체를 재시도하면 `paymentClient.approve()`가 다시 호출될 수 있다. 결제 API가 자체 멱등성 키를 제공하지 않거나, 우리가 같은 키를 보내지 않았다면 중복 결제가 될 수 있다.

따라서 외부 부작용이 있는 경로는 보통 순서를 다시 설계한다.

1. DB에 요청 의도를 멱등성 키와 함께 기록한다.
2. 이미 처리된 키인지 확인한다.
3. 외부 API에는 provider가 지원하는 idempotency key를 전달한다.
4. 외부 결과를 저장할 때 낙관적 락 또는 상태 조건을 확인한다.
5. 충돌 시 최신 상태를 재조회해 보상 또는 무시 여부를 결정한다.

예시는 다음과 같다.

```java
@Transactional
public PaymentRequest preparePayment(Long orderId, String requestKey) {
    Order order = orderRepository.findById(orderId).orElseThrow();

    PaymentRequest existing = paymentRequestRepository
            .findByRequestKey(requestKey)
            .orElse(null);

    if (existing != null) {
        return existing;
    }

    order.assertPayable();
    return paymentRequestRepository.save(
            PaymentRequest.ready(orderId, requestKey, order.totalAmount())
    );
}
```

외부 결제 호출은 트랜잭션 밖에서 수행하고, 결과 반영은 다시 짧은 트랜잭션으로 처리한다.

```java
@Transactional
public void completePayment(String requestKey, PaymentApproval approval) {
    PaymentRequest request = paymentRequestRepository
            .findByRequestKey(requestKey)
            .orElseThrow();

    if (request.isCompleted()) {
        return;
    }

    Order order = orderRepository.findById(request.orderId())
            .orElseThrow();

    order.markPaid(approval.paymentKey());
    request.complete(approval.paymentKey());
}
```

이 구조에서도 낙관적 락 충돌은 날 수 있다. 하지만 충돌 지점이 "외부 결제를 다시 호출해야 하는가"와 분리되어 있다. 재시도는 DB 상태 반영 구간에만 적용할 수 있고, 결제 API는 같은 idempotency key로 보호된다.

### 재시도는 트랜잭션 경계 밖에서 걸어야 한다

Spring에서 흔히 놓치는 함정도 있다. `@Retryable`과 `@Transactional`을 같은 메서드에 붙였을 때 프록시 순서와 호출 방식에 따라 기대와 다르게 동작할 수 있다. 특히 같은 클래스 내부 메서드 호출은 프록시를 거치지 않아 retry나 transaction이 적용되지 않을 수 있다.

실무에서는 재시도 orchestration과 실제 transactional work를 분리하는 편이 더 명확하다.

```java
@Service
public class OrderPaymentUseCase {

    private final OrderPaymentTxService txService;

    public void completeWithRetry(String requestKey, PaymentApproval approval) {
        RetryTemplate retryTemplate = RetryTemplate.builder()
                .maxAttempts(3)
                .fixedBackoff(100)
                .retryOn(OptimisticLockingFailureException.class)
                .build();

        retryTemplate.execute(context -> {
            txService.completePayment(requestKey, approval);
            return null;
        });
    }
}

@Service
public class OrderPaymentTxService {

    @Transactional
    public void completePayment(String requestKey, PaymentApproval approval) {
        // reload latest state and apply domain rule
    }
}
```

재시도할 때마다 새 트랜잭션에서 최신 상태를 다시 읽는 구조가 핵심이다. 같은 영속성 컨텍스트 안에서 예외 난 엔티티를 붙잡고 다시 시도하는 것은 의미가 없다.

---

## 핵심 개념 5: 상태 전이는 version만 믿지 말고 조건을 코드와 SQL에 함께 표현해야 한다

낙관적 락은 "누군가 먼저 바꿨다"를 감지한다. 하지만 "어떤 상태에서 어떤 상태로 갈 수 있는가"는 별도 도메인 규칙이다.

주문 취소를 예로 들어 보자.

```java
@Transactional
public void cancel(Long orderId) {
    Order order = orderRepository.findById(orderId).orElseThrow();
    order.cancel();
}
```

`order.cancel()` 안에서 상태 전이를 검증한다면 기본 구조는 좋다.

```java
public void cancel() {
    if (status == OrderStatus.SHIPPING || status == OrderStatus.DELIVERED) {
        throw new IllegalStateException("Cannot cancel after shipping");
    }
    this.status = OrderStatus.CANCELLED;
}
```

하지만 매우 경쟁이 강한 경로에서는 SQL 조건까지 활용하는 편이 더 직접적일 때가 있다.

```java
@Modifying
@Query("""
    update Order o
       set o.status = 'CANCELLED',
           o.version = o.version + 1
     where o.id = :orderId
       and o.status in ('CREATED', 'PAID')
""")
int cancelIfCancellable(Long orderId);
```

이 방식은 상태 전이 조건을 update 자체에 넣는다. 반환 row 수가 0이면 이미 배송 중이거나, 존재하지 않거나, 다른 상태로 바뀐 것이다.

다만 이 방식은 JPA version 관리를 직접 건드리므로 팀의 표준을 명확히 해야 한다.

- 엔티티 기반 변경과 bulk 상태 변경을 같은 트랜잭션에서 섞지 않는다.
- bulk update 후에는 필요한 경우 `clearAutomatically` 또는 재조회로 영속성 컨텍스트를 정리한다.
- version 증가 규칙을 누락하지 않는다.
- 도메인 이벤트 발행, outbox 기록, 감사 로그를 별도 경로에서 보장한다.

대부분의 일반 서비스 로직은 엔티티 메서드 + `@Version`으로 충분하다. 하지만 hot path에서는 조건부 update가 더 나은 선택일 수 있다. 중요한 것은 두 방식을 섞어 쓰면서 서로의 전제를 깨뜨리지 않는 것이다.

---

## 실무 예시 1: 관리자 편집 화면에서 충돌을 사용자에게 설명하기

관리자 화면은 낙관적 락이 가장 잘 맞는 영역이다. 같은 상품이나 설정을 여러 사람이 동시에 수정할 가능성은 있지만, 충돌 빈도는 대체로 낮다. 그리고 충돌이 나면 사용자가 최신 값을 보고 다시 판단하는 것이 자연스럽다.

### 조회 API

```java
@GetMapping("/admin/products/{productId}")
public ProductEditResponse getProduct(@PathVariable Long productId) {
    Product product = productQueryService.getForEdit(productId);
    return ProductEditResponse.from(product);
}
```

응답에는 version을 포함한다.

```json
{
  "id": 10,
  "name": "Basic Hoodie",
  "price": 39000,
  "status": "ON_SALE",
  "version": 12
}
```

### 수정 API

```java
@PutMapping("/admin/products/{productId}")
public ResponseEntity<Void> updateProduct(
        @PathVariable Long productId,
        @RequestBody UpdateProductRequest request
) {
    productCommandService.update(productId, request);
    return ResponseEntity.noContent().build();
}
```

서비스는 사용자가 본 version과 현재 version을 비교하고, 최종적으로 JPA version update로 다시 보호한다.

```java
@Transactional
public void update(Long productId, UpdateProductRequest request) {
    Product product = productRepository.findById(productId)
            .orElseThrow();

    if (!product.hasVersion(request.version())) {
        throw new EditConflictException(productId);
    }

    product.changeSalesInfo(request.name(), request.price(), request.status());
}
```

예외 응답은 409 Conflict가 적합하다.

```java
@ExceptionHandler(EditConflictException.class)
public ResponseEntity<ErrorResponse> handleEditConflict(EditConflictException ex) {
    return ResponseEntity.status(HttpStatus.CONFLICT)
            .body(new ErrorResponse(
                    "EDIT_CONFLICT",
                    "다른 사용자가 먼저 수정했습니다. 최신 내용을 다시 확인해 주세요."
            ));
}
```

여기서 중요한 점은 409를 단순 오류로 보지 않는 것이다. 이건 사용자에게 다시 판단하라고 알려야 하는 정상적인 경합 결과다.

프론트엔드는 보통 다음 중 하나를 제공한다.

- 최신 값으로 새로고침
- 내가 수정한 값과 최신 값 비교
- 다시 적용하기
- 충돌 필드 표시

관리자 도구에서 이 UX를 만들지 않으면 낙관적 락은 "가끔 저장 실패하는 불편한 기능"으로 인식된다.

---

## 실무 예시 2: 포인트 차감은 version보다 원자적 조건 update가 더 단순할 수 있다

포인트 잔액 차감은 동시성 문제가 매우 흔한 예다.

```java
@Transactional
public void usePoint(Long memberId, long amount) {
    PointWallet wallet = walletRepository.findByMemberId(memberId)
            .orElseThrow();

    wallet.use(amount);
}
```

엔티티에 `@Version`을 붙이면 동시에 차감할 때 하나는 실패한다. 그 자체로는 정합성을 지킨다. 하지만 트래픽이 많고 차감 요청이 자주 겹친다면, 충돌 예외를 많이 처리해야 한다.

이때는 조건부 update가 더 간결할 수 있다.

```java
@Modifying
@Query("""
    update PointWallet w
       set w.balance = w.balance - :amount,
           w.version = w.version + 1
     where w.memberId = :memberId
       and w.balance >= :amount
""")
int useIfEnough(Long memberId, long amount);
```

서비스는 반환 row 수로 판단한다.

```java
@Transactional
public void usePoint(Long memberId, long amount, String idempotencyKey) {
    if (pointUsageRepository.existsByIdempotencyKey(idempotencyKey)) {
        return;
    }

    int updated = walletRepository.useIfEnough(memberId, amount);
    if (updated != 1) {
        throw new NotEnoughPointException(memberId);
    }

    pointUsageRepository.save(PointUsage.used(memberId, amount, idempotencyKey));
}
```

여기서도 멱등성 키가 중요하다. 클라이언트가 timeout 후 같은 요청을 다시 보낼 수 있기 때문이다. 잔액 차감은 한 번만 일어나야 한다.

단, 위 코드는 아직 완전하지 않다. `existsByIdempotencyKey`와 `save` 사이에도 race가 있을 수 있다. 실무에서는 `idempotency_key`에 unique constraint를 걸고, 중복 insert를 안전하게 처리해야 한다.

```sql
alter table point_usage
add constraint uk_point_usage_idempotency_key unique (idempotency_key);
```

정리하면 포인트 차감 같은 경로는 다음이 함께 있어야 한다.

- 잔액 부족을 막는 조건부 update
- 중복 요청을 막는 멱등성 키
- 멱등성 키 unique constraint
- 차감 이력 저장
- 실패 시 명확한 비즈니스 예외
- 재시도 시 같은 결과를 반환하는 API 계약

`@Version`은 이 중 하나의 선택지일 뿐이다.

---

## 실무 예시 3: 메시지 컨슈머에서는 충돌 예외를 "재처리 가능성"으로 분류해야 한다

Kafka, RabbitMQ, SQS 같은 메시지 기반 시스템에서도 낙관적 락은 자주 만난다.

예를 들어 주문 배송 상태를 업데이트하는 컨슈머가 있다고 하자.

```java
@Transactional
public void handle(DeliveryStartedEvent event) {
    Order order = orderRepository.findById(event.orderId())
            .orElseThrow();

    order.markShipping(event.deliveryId());
}
```

동시에 결제 취소나 주문 취소 이벤트가 처리되면 version 충돌이 날 수 있다.

컨슈머에서 중요한 것은 예외를 무조건 재시도하지 않는 것이다. 충돌은 다음 세 종류로 나눠야 한다.

1. **일시 충돌**
   - 다른 트랜잭션이 먼저 상태를 바꿨지만, 최신 상태를 보면 같은 이벤트를 적용할 수 있다.
   - 짧은 backoff 후 재시도 가능하다.

2. **이미 처리됨**
   - 이벤트가 중복 전달됐고 현재 상태가 이미 원하는 상태다.
   - ack하고 종료한다.

3. **비즈니스상 더 이상 적용 불가**
   - 주문이 취소됐는데 배송 시작 이벤트가 늦게 도착했다.
   - 보상 이벤트를 발행하거나 dead letter로 보내야 한다.

따라서 컨슈머는 최신 상태를 재조회한 후 판단하는 코드가 필요하다.

```java
@Transactional
public void handle(DeliveryStartedEvent event) {
    Order order = orderRepository.findById(event.orderId())
            .orElseThrow();

    if (order.isAlreadyShippingWith(event.deliveryId())) {
        return;
    }

    if (!order.canStartDelivery()) {
        deliveryCompensationService.requestStop(event.deliveryId(), order.id());
        return;
    }

    order.markShipping(event.deliveryId());
}
```

이 로직이 낙관적 락 예외로 실패하면, 컨슈머 프레임워크의 retry가 다시 호출한다. 다시 호출된 트랜잭션은 최신 상태를 읽고 위 분기를 다시 탄다.

운영에서는 다음 지표를 봐야 한다.

- 낙관적 락 충돌 횟수
- 메시지 retry 횟수
- dead letter queue 유입 수
- 이벤트 처리 지연 시간
- 같은 aggregate에 대한 이벤트 순서 역전 비율
- 보상 요청 수

충돌이 갑자기 늘었다면 단순히 retry 횟수를 늘릴 일이 아니다. 이벤트 순서, consumer concurrency, partition key, aggregate hot spot, 외부 시스템 지연을 함께 봐야 한다.

---

## 트레이드오프: 낙관적 락은 빠르고 단순하지만 충돌 처리를 밖으로 밀어낸다

낙관적 락의 장점은 분명하다.

- DB row lock을 오래 잡지 않는다.
- 읽기 많은 시스템에서 처리량이 좋다.
- 충돌이 낮은 경로에서 코드가 단순하다.
- 관리자 편집, 설정 변경, 상태 전이에 잘 맞는다.
- 충돌을 명확히 감지해 조용한 덮어쓰기를 막는다.

하지만 대가도 있다.

- 충돌은 뒤늦게 flush/commit 시점에 발견된다.
- 충돌 시 이미 계산한 작업을 버려야 할 수 있다.
- 외부 API 호출과 섞이면 보상 처리가 필요하다.
- hot row에서는 실패와 재시도가 폭증할 수 있다.
- 사용자에게 409 Conflict UX를 제공해야 한다.
- bulk update나 native query가 version 규칙을 우회할 수 있다.

비관적 락의 장점과 단점은 거의 반대다.

- 충돌 가능성이 높은 작은 임계 영역을 직렬화하기 좋다.
- 실패 후 재시도보다 대기시키는 편이 나을 때 적합하다.
- 하지만 lock wait, deadlock, timeout, 처리량 저하를 관리해야 한다.
- 외부 API 호출을 lock 안에서 하면 장애가 크게 번진다.

조건부 update는 또 다른 선택지다.

- 재고, 포인트, 쿠폰처럼 조건이 명확한 차감에는 매우 강력하다.
- 영향을 받은 row 수로 성공/실패를 판단할 수 있다.
- 하지만 엔티티 생명주기, 도메인 이벤트, 영속성 컨텍스트와 잘 분리해야 한다.

선택 기준을 간단히 정리하면 다음과 같다.

```text
관리자 편집, 문서 수정, 일반 상태 전이
  -> @Version 기반 낙관적 락

재고 차감, 포인트 사용, 쿠폰 발급
  -> 조건부 update 또는 짧은 비관적 락 검토

충돌이 낮지만 덮어쓰면 안 되는 aggregate
  -> @Version

충돌이 높고 실패 재시도 비용이 큰 hot path
  -> 비관적 락, queue, 원자적 update, shard/counter 설계 검토

외부 API 부작용이 있는 작업
  -> 멱등성 키, 요청 이력, outbox, 보상 처리와 함께 설계
```

---

## 흔한 실수 1: `@Version`을 붙였는데 bulk update가 version을 우회한다

JPA 엔티티에 `@Version`을 붙여도 모든 update가 자동으로 보호되는 것은 아니다.

예를 들어 아래 JPQL bulk update는 영속성 컨텍스트의 엔티티 단위 dirty checking을 거치지 않는다.

```java
@Modifying
@Query("""
    update Product p
       set p.status = :status
     where p.categoryId = :categoryId
""")
int updateStatusByCategory(Long categoryId, ProductStatus status);
```

이 쿼리는 version 조건을 자동으로 붙여 주지 않는다. version 증가도 직접 하지 않으면 누락될 수 있다.

그래서 bulk update를 쓸 때는 다음을 점검해야 한다.

- 이 update가 낙관적 락을 우회해도 되는가?
- version을 증가시켜야 하는가?
- 같은 트랜잭션에서 이미 조회된 엔티티가 stale해지는가?
- `clearAutomatically = true`가 필요한가?
- 이벤트, 감사 로그, 검색 색인 동기화는 어떻게 처리되는가?

예를 들어 상태를 바꾸는 bulk update라면 최소한 version 증가를 명시할 수 있다.

```java
@Modifying(clearAutomatically = true, flushAutomatically = true)
@Query("""
    update Product p
       set p.status = :status,
           p.version = p.version + 1
     where p.categoryId = :categoryId
""")
int updateStatusByCategory(Long categoryId, ProductStatus status);
```

하지만 이것도 완전한 해결책은 아니다. 각 상품별 도메인 규칙을 건너뛰기 때문이다. bulk update는 "빠른 길"인 만큼 도메인 규칙을 우회한다는 사실을 문서화해야 한다.

---

## 흔한 실수 2: 낙관적 락 예외를 잡고 같은 엔티티로 다시 저장한다

낙관적 락 예외가 났다는 것은 현재 영속성 컨텍스트의 엔티티 상태가 이미 실패했다는 뜻이다. 이 상태에서 같은 엔티티 객체를 들고 다시 저장하려 하면 문제가 더 커진다.

나쁜 예는 이런 식이다.

```java
try {
    order.markPaid(paymentKey);
    entityManager.flush();
} catch (OptimisticLockException e) {
    order.markPaid(paymentKey);
    entityManager.flush();
}
```

이 코드는 최신 상태를 다시 읽지 않는다. 충돌 원인을 재평가하지도 않는다. 실패한 상태를 억지로 다시 밀어 넣는 것에 가깝다.

올바른 방향은 다음이다.

1. 현재 트랜잭션을 실패시킨다.
2. 새 트랜잭션에서 aggregate를 다시 조회한다.
3. 최신 상태 기준으로 도메인 규칙을 다시 판단한다.
4. 적용 가능하면 다시 변경한다.
5. 적용 불가능하면 명확한 결과로 종료한다.

재시도는 기술적으로 같은 코드를 반복하는 것이 아니라, 비즈니스 의사결정을 최신 상태에서 다시 수행하는 일이다.

---

## 흔한 실수 3: 외부 API 호출을 긴 트랜잭션과 락 안에 넣는다

동시성 문제를 만나면 트랜잭션 범위를 크게 잡고 싶어진다.

```java
@Transactional
public void pay(Long orderId) {
    Order order = orderRepository.findByIdForUpdate(orderId).orElseThrow();
    PaymentApproval approval = paymentClient.approve(order);
    order.markPaid(approval.paymentKey());
}
```

이 코드는 위험하다.

- DB row lock을 잡은 채 외부 API 응답을 기다린다.
- 결제사가 느려지면 DB lock wait이 늘어난다.
- lock wait이 늘면 thread와 connection pool이 같이 밀린다.
- timeout 후 재시도가 붙으면 중복 결제 위험이 생긴다.
- 장애가 외부 API에서 DB 전체 처리량 문제로 번질 수 있다.

일반적으로 외부 API 호출은 DB 트랜잭션과 분리하는 편이 낫다. 필요한 경우 요청 의도를 먼저 저장하고, 외부 호출 후 결과를 짧은 트랜잭션으로 반영한다. outbox 패턴이나 saga를 쓰는 이유도 이 경계를 명확히 하기 위해서다.

물론 모든 시스템이 완벽한 saga를 구현해야 하는 것은 아니다. 하지만 "DB 락을 잡고 외부 API를 기다리는 코드"는 운영 장애 전파 경로가 되기 쉽다는 점을 기억해야 한다.

---

## 흔한 실수 4: 충돌률을 측정하지 않는다

낙관적 락은 충돌이 낮다는 가정 위에 서 있다. 그런데 많은 팀이 충돌률을 측정하지 않는다.

측정하지 않으면 이런 문제가 생긴다.

- 409이 정상 경합인지 장애인지 구분하지 못한다.
- 특정 상품, 회원, 주문에 hot spot이 있는지 모른다.
- retry가 성공률을 높이는지 DB 부하만 늘리는지 모른다.
- 메시지 컨슈머 concurrency가 적절한지 판단할 수 없다.
- 배치 시간대에 API 충돌이 늘어나는지 보이지 않는다.

최소한 아래 정보는 로그나 metric으로 남기는 편이 좋다.

```text
event = optimistic_lock_conflict
entity = Order
entity_id = 12345
use_case = complete_payment
attempt = 2
current_thread = payment-consumer-3
request_key = pay_20260706_abcdef
```

metric은 이런 식으로 나눌 수 있다.

- `optimistic_lock_conflict_total{entity,use_case}`
- `optimistic_lock_retry_total{entity,use_case,result}`
- `optimistic_lock_retry_exhausted_total{entity,use_case}`
- `http_409_total{api}`
- `message_retry_total{topic,event_type}`

충돌률이 낮다면 낙관적 락이 잘 맞는다는 신호다. 충돌률이 높다면 락 종류를 바꾸거나, aggregate 경계를 쪼개거나, queue/partition key를 조정하거나, hot row를 분산해야 한다.

---

## 체크리스트: JPA 낙관적 락을 운영에 넣기 전 확인할 것

아래 질문에 답할 수 있으면 동시성 설계가 훨씬 단단해진다.

### 엔티티와 aggregate

- 같은 aggregate를 동시에 수정할 수 있는 경로가 무엇인지 알고 있는가?
- version 필드는 aggregate root에 있는가?
- 자식 엔티티 변경이 root version 증가와 어떤 관계인지 정했는가?
- bulk update가 version 규칙을 우회하지 않는가?
- native query나 Querydsl update가 version 증가를 누락하지 않는가?

### API 계약

- 사용자가 편집 화면에서 본 version을 수정 요청에 포함하는가?
- 충돌 시 409 Conflict를 반환하는가?
- 409 응답 메시지가 사용자가 할 일을 설명하는가?
- 충돌 후 최신 값 조회, 비교, 재적용 UX가 있는가?
- 클라이언트 timeout 후 재요청해도 안전한 멱등성 키가 있는가?

### 서비스 로직

- 낙관적 락 예외를 500으로 방치하지 않는가?
- 재시도할 때 새 트랜잭션에서 최신 상태를 다시 조회하는가?
- 외부 API 호출이 트랜잭션과 락 안에 오래 머물지 않는가?
- 재시도 가능한 예외와 재시도하면 안 되는 비즈니스 예외를 구분하는가?
- 상태 전이 조건이 엔티티 메서드 또는 SQL 조건으로 명확히 표현되는가?

### 데이터베이스

- version 컬럼에 null이 들어갈 수 없게 되어 있는가?
- 기존 테이블에 version을 추가할 때 backfill 계획이 있는가?
- hot row에서 lock wait, deadlock, update conflict를 관찰하는가?
- 조건부 update에는 필요한 index가 있는가?
- unique constraint로 멱등성 키를 보장하는가?

### 메시지와 배치

- 메시지 중복 전달을 전제로 처리하는가?
- 이벤트 순서가 aggregate 단위로 보장되는가?
- 순서가 보장되지 않을 때 최신 상태 기준으로 무시/보상/재시도 분기가 있는가?
- 배치가 API와 같은 row를 수정할 때 충돌률을 측정하는가?
- retry exhausted 후 dead letter나 운영 알림이 있는가?

### 관측 가능성

- 낙관적 락 충돌 metric이 use case별로 나뉘어 있는가?
- retry 성공/실패 비율을 볼 수 있는가?
- 409 응답 증가를 알림으로 볼지, 정상 이벤트로 볼지 기준이 있는가?
- 특정 entity id에 충돌이 몰리는지 확인할 수 있는가?
- 충돌 증가가 배포, 배치, 이벤트 지연, 외부 API 장애와 연결되는지 추적 가능한가?

---

## 마이그레이션 팁: 운영 테이블에 version 컬럼을 추가할 때

이미 운영 중인 테이블에 `@Version`을 추가할 때도 주의가 필요하다.

가장 단순한 접근은 다음과 같다.

```sql
alter table orders add column version bigint;
update orders set version = 0 where version is null;
alter table orders alter column version set not null;
```

하지만 대용량 테이블에서는 이 작업이 락과 복제 지연을 만들 수 있다. DB 종류와 버전에 따라 DDL 비용이 다르고, default with not null이 테이블 rewrite를 유발할 수도 있다.

안전하게 하려면 expand-contract 방식으로 나누는 편이 좋다.

1. nullable version 컬럼을 추가한다.
2. 새 애플리케이션이 insert 시 version을 채우도록 배포한다.
3. 기존 row를 작은 chunk로 backfill한다.
4. version null row가 없는지 검증한다.
5. not null constraint를 추가한다.
6. 낙관적 락을 쓰는 코드 경로를 점진적으로 켠다.

JPA 엔티티에 `@Version`을 붙이는 시점과 DB 데이터 준비 시점이 어긋나면 예상치 못한 update 실패가 날 수 있다. 특히 rolling deploy 환경에서는 구버전 애플리케이션과 신버전 애플리케이션이 동시에 떠 있는 시간도 고려해야 한다.

또 하나 중요한 점은 bulk job이다. version 도입 후에도 기존 배치가 직접 SQL로 update하면서 version을 증가시키지 않으면, 애플리케이션은 그 변경을 충돌로 감지하지 못할 수 있다. version 컬럼 추가는 엔티티 코드 한 줄 변경이 아니라, 해당 테이블을 수정하는 모든 경로의 계약 변경이다.

---

## 한줄 정리

JPA의 `@Version`은 동시성 문제를 자동 해결하는 버튼이 아니라, 오래된 상태로 쓰려는 시도를 실패시키는 안전장치다. 운영 가능한 설계는 그 실패를 409 응답, 최신 상태 재조회, 제한된 재시도, 멱등성 키, 조건부 update, 보상 처리, 충돌 지표까지 이어 붙일 때 완성된다.
