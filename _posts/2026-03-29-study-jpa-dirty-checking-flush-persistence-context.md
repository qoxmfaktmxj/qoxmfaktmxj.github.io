---
layout: post
title: "JPA 영속성 컨텍스트 실전: Dirty Checking, Flush, 준영속 상태를 정확히 다루는 법"
date: 2026-03-29 11:40:00 +0900
categories: [java]
tags: [study, java, spring, jpa, hibernate, persistence-context, dirty-checking, flush, backend, orm]
---

## 배경: JPA를 오래 써도 쓰기 경로에서 계속 사고가 나는 이유

JPA 관련 성능 글은 대개 조회 최적화와 N+1에 집중된다. 물론 중요하다. 하지만 운영 장애는 조회보다 **쓰기 경로에서 JPA를 오해해서** 터지는 경우도 많다.

대표적으로 이런 상황이다.

- 엔티티 값을 바꿨는데 `save()`를 안 불렀는데도 DB가 수정돼서 당황한다
- 반대로 값을 바꿨는데 SQL이 바로 안 나가서 "왜 반영이 안 되지?"라고 착각한다
- 벌크 업데이트 한 번 넣었더니 같은 트랜잭션 안에서 조회 결과가 뒤섞인다
- 컨트롤러에서 받은 엔티티를 그대로 `merge()`했다가 null 값이 덮어써진다
- 배치 처리에서 `flush()` 없이 수만 건을 쌓다가 메모리와 성능이 같이 무너진다

이 문제들의 공통 원인은 같다.

> JPA를 "SQL 자동 생성기"로만 보고, **영속성 컨텍스트가 어떻게 상태를 추적하고 언제 SQL을 내보내는지**를 정확히 이해하지 못한 것.

조회에서는 fetch plan을 설계해야 하고, 쓰기에서는 **영속성 컨텍스트의 생명주기와 flush 타이밍**을 통제해야 한다. 이걸 놓치면 테스트에서는 통과하는데 운영에서만 이상한 데이터 정합성 문제를 만난다.

이 글은 중급 이상 개발자를 기준으로 다음을 정리한다.

1. 영속성 컨텍스트가 정확히 무엇을 보장하는가
2. dirty checking은 어떤 원리로 동작하는가
3. flush는 언제 발생하고 왜 중요한가
4. 벌크 연산, 준영속(detached), `merge()`가 왜 위험한가
5. 실무에서 안전한 업데이트 패턴은 무엇인가

---

## 핵심 개념 1: 영속성 컨텍스트는 단순 캐시가 아니라 "현재 트랜잭션의 쓰기 작업장"이다

영속성 컨텍스트를 흔히 1차 캐시라고 설명하지만, 그 표현만으로는 절반밖에 설명되지 않는다.

영속성 컨텍스트는 다음을 함께 제공한다.

- **엔티티 동일성 보장**: 같은 PK를 같은 트랜잭션 안에서 조회하면 같은 객체 인스턴스를 돌려준다
- **변경 감지(dirty checking)**: 엔티티의 상태 변화를 추적한다
- **쓰기 지연(write-behind)**: SQL을 즉시 보내지 않고 적절한 시점에 모아 실행한다
- **연관 관계 관리의 기준점**: 객체 그래프와 DB 반영 순서를 조정한다

즉 JPA의 핵심은 "엔티티를 들고 있다가 끝날 때 SQL로 번역해주는 unit of work"에 가깝다.

예를 들어 아래 코드는 별도의 `save()`가 없어도 수정 SQL이 나간다.

```java
@Transactional
public void changeStatus(Long orderId) {
    Order order = orderRepository.findById(orderId)
            .orElseThrow();

    order.changeStatus(OrderStatus.SHIPPED);
}
```

이 메서드가 끝날 때 트랜잭션이 커밋되면, JPA는 `order`가 영속 상태였고 값이 바뀌었다는 사실을 알고 update SQL을 만든다.

이 동작은 마법처럼 보이지만 사실 매우 구체적인 규칙 위에서 움직인다.

### 엔티티 상태는 최소 네 가지로 나뉜다

1. **비영속(transient)**
   - new로 만들었지만 아직 영속성 컨텍스트에 들어가지 않은 상태
2. **영속(managed)**
   - 현재 영속성 컨텍스트가 추적 중인 상태
3. **준영속(detached)**
   - 한때 영속이었지만 현재는 추적에서 벗어난 상태
4. **삭제(removed)**
   - 삭제 예약된 상태

실무에서 중요한 것은 "객체를 들고 있다"와 "JPA가 추적하고 있다"가 완전히 다른 말이라는 점이다.

- 영속 상태에서 값 변경 → dirty checking 대상
- 준영속 상태에서 값 변경 → 그냥 평범한 자바 객체 변경일 뿐

이 차이를 모르면 `merge()` 남발, DTO 없는 엔티티 바인딩, 장수 세션 같은 위험한 코드로 흘러가기 쉽다.

---

## 핵심 개념 2: Dirty Checking의 본질은 "변경 이벤트 감지"가 아니라 "flush 시점의 상태 비교"다

많은 개발자가 dirty checking을 이벤트 리스너처럼 생각한다. 즉 엔티티의 setter가 호출되는 순간 JPA가 즉시 변경을 기록한다고 오해한다. 실제로는 보통 더 단순하다.

JPA 구현체(Hibernate)는 영속 엔티티를 로딩하거나 저장할 때 **초기 상태 스냅샷**을 들고 있다가, flush 시점에 현재 상태와 비교한다. 달라진 필드가 있으면 update SQL을 만든다.

즉 핵심은 두 가지다.

1. 지금 엔티티가 **영속 상태인지**
2. 지금이 **flush가 일어나는 시점인지**

### dirty checking이 잘 작동하는 전형적인 패턴

```java
@Transactional
public void updateMemberProfile(Long memberId, String nickname, String phone) {
    Member member = memberRepository.findById(memberId)
            .orElseThrow();

    member.changeProfile(nickname, phone);
}
```

이 패턴이 좋은 이유는 다음과 같다.

- 수정 대상이 명확하다
- 현재 트랜잭션 안에서 조회한 영속 엔티티를 수정한다
- 변경 의도가 메서드로 캡슐화되어 있다
- commit 시점에 dirty checking이 자연스럽게 동작한다

### dirty checking이 오해를 부르는 패턴

```java
@Transactional
public void updateMember(Member member) {
    member.setNickname("new-name");
}
```

겉보기엔 비슷하지만, 파라미터 `member`가 현재 영속인지 보장되지 않는다.

- 컨트롤러에서 넘어온 객체일 수 있다
- 이전 트랜잭션에서 조회된 준영속 객체일 수 있다
- 테스트에선 우연히 되는데 실제 요청 경계에서는 안 될 수 있다

실무 기준으로는 **서비스 메서드 내부에서 다시 조회한 영속 엔티티를 변경하는 패턴**이 가장 안전하다.

### 부분 업데이트가 dirty checking과 잘 맞는 이유

dirty checking은 "수정된 필드만 update"하는 최적화보다도, **도메인 규칙을 엔티티 메서드에 모으기 좋다**는 장점이 크다.

```java
@Entity
public class Member {
    // ...

    public void changeProfile(String nickname, String phone) {
        if (nickname == null || nickname.isBlank()) {
            throw new IllegalArgumentException("nickname is blank");
        }
        this.nickname = nickname;
        this.phone = phone;
    }
}
```

이렇게 하면 서비스는 "무엇을 바꿀지"에 집중하고, 엔티티는 "어떻게 유효하게 바꿀지"를 책임진다.

반대로 화면에서 온 JSON을 엔티티에 그대로 덮어쓰면 dirty checking의 장점보다 위험이 더 커진다.

---

## 핵심 개념 3: Flush는 commit의 동의어가 아니다

실무에서 가장 많이 헷갈리는 지점이 여기다.

- **flush**: 영속성 컨텍스트의 변경 사항을 DB에 SQL로 반영
- **commit**: 트랜잭션을 최종 확정

즉 flush는 SQL을 보내는 행위이고, commit은 그 결과를 확정하는 행위다.
DB 트랜잭션 안에서는 flush가 먼저 일어나도 commit 전이라면 다른 트랜잭션에서 아직 확정 상태로 보이지 않을 수 있다.

### flush가 발생하는 대표 시점

1. **트랜잭션 커밋 직전**
2. **JPQL/Criteria 쿼리 실행 직전**
   - 현재 변경사항이 쿼리 결과에 영향을 줄 수 있기 때문
3. **명시적 `entityManager.flush()` 호출 시**

아래 예제를 보자.

```java
@Transactional
public void changeAndQuery(Long orderId) {
    Order order = orderRepository.findById(orderId).orElseThrow();
    order.changeStatus(OrderStatus.CANCELLED);

    long cancelledCount = orderRepository.countByStatus(OrderStatus.CANCELLED);
}
```

`countByStatus()`가 JPQL/쿼리 메서드를 실행하는 순간, JPA는 현재 트랜잭션의 변경사항이 쿼리 결과에 반영돼야 한다고 판단해 먼저 flush할 수 있다.

즉 **SQL이 안 보인다고 아직 변경이 없는 것이 아니고**, **SQL이 보인다고 이미 커밋된 것도 아니다.**

이 차이를 이해하지 못하면 로그를 보고 잘못된 결론을 내리기 쉽다.

### `saveAndFlush()`를 습관처럼 쓰면 안 되는 이유

Spring Data JPA를 쓰다 보면 `saveAndFlush()`가 만능처럼 보일 수 있다. 하지만 대부분의 일반적인 요청 처리에서는 불필요하다.

무분별한 즉시 flush는 다음 문제를 만든다.

- DB round trip 증가
- 배치 insert/update 최적화 약화
- 트랜잭션 안에서 SQL 실행 시점이 앞당겨져 락 보유 시간이 길어질 수 있음
- 코드가 flush 타이밍에 의존하면서 테스트/운영 동작이 복잡해짐

명시적 flush가 필요한 경우는 제한적이다.

- 뒤이어 실행할 쿼리가 반드시 현재 변경사항을 기준으로 해야 할 때
- DB constraint 위반을 메서드 중간에 조기 감지하고 싶을 때
- 대량 배치 처리에서 메모리 사용을 제어하고 싶을 때

즉 flush는 제어 도구이지, 습관적 기본값이 아니다.

---

## 핵심 개념 4: 쓰기 지연은 성능 최적화이자 사고 유발 포인트다

JPA는 persist/update/delete를 호출했다고 해서 SQL을 바로 보내지 않는다. 내부 액션 큐에 쌓아두었다가 flush 시점에 순서와 제약을 고려해 실행한다. 이것이 쓰기 지연이다.

장점은 분명하다.

- 여러 변경을 한 번에 모아 전송 가능
- JDBC batch와 결합하면 대량 처리 효율 향상
- 객체 그래프 변경을 SQL 순서로 정렬하기 쉬움

하지만 개발자는 종종 이 특성을 잊고 "코드 한 줄 = SQL 한 줄"로 생각한다. 그러면 다음과 같은 오해가 생긴다.

### 오해 1: `persist()` 직후 select 하면 DB에 있어야 한다

동일 트랜잭션 안에서는 영속성 컨텍스트가 우선이라 엔티티를 다시 찾으면 보일 수 있다. 하지만 그건 DB에 이미 commit돼서가 아니라 **현재 컨텍스트가 들고 있기 때문**일 수 있다.

### 오해 2: 중간에 예외가 나도 이미 나간 SQL은 확정이다

flush로 SQL이 실행됐더라도 commit 전이면 롤백될 수 있다. 반대로 DB trigger, 외부 시스템 호출, 락 경쟁 같은 부수 효과는 이미 관찰될 수 있다. 그래서 flush와 commit을 분리해서 이해해야 한다.

### 오해 3: 테스트에서 통과했으니 운영도 안전하다

`@Transactional` 테스트는 테스트 종료 시 롤백되므로 flush 타이밍 문제나 제약 조건 위반이 감춰지는 경우가 있다. 실제 운영 시점과 동일한 제약 검증을 보고 싶으면 중간 flush를 넣어봐야 한다.

```java
@Test
void duplicateEmailShouldFail() {
    memberRepository.save(new Member("a@test.com"));
    memberRepository.save(new Member("a@test.com"));

    entityManager.flush();
}
```

이렇게 해야 unique constraint 위반이 테스트 종료 시점이 아니라 테스트 본문에서 드러난다.

---

## 핵심 개념 5: 벌크 업데이트는 빠르지만 영속성 컨텍스트를 무시한다

벌크 update/delete는 대량 데이터 변경에서 매우 유용하다. 문제는 이 연산이 **영속성 컨텍스트를 거치지 않고 DB를 직접 때린다**는 점이다.

예를 들어 아래 코드를 보자.

```java
@Modifying
@Query("update Coupon c set c.expired = true where c.expiresAt < :now")
int expireCoupons(@Param("now") LocalDateTime now);
```

이 쿼리는 빠르다. 하지만 같은 트랜잭션 안에서 이미 로딩된 `Coupon` 엔티티가 있다면, 그 객체는 여전히 이전 상태를 들고 있을 수 있다.

즉 DB는 `expired = true`인데 메모리 안 엔티티는 `false`로 남는다.

### 왜 위험한가

- 후속 비즈니스 로직이 stale entity를 기준으로 동작할 수 있다
- API 응답이 DB 상태와 달라질 수 있다
- 테스트에서는 잘 안 드러나다가 특정 트랜잭션 흐름에서만 터진다

### 실무 대응 기준

1. 벌크 연산 후에는 **즉시 clear 또는 트랜잭션 분리**를 고려한다
2. Spring Data JPA라면 `@Modifying(clearAutomatically = true, flushAutomatically = true)` 옵션을 검토한다
3. 벌크 연산과 엔티티 기반 로직을 같은 유즈케이스에 과도하게 섞지 않는다

```java
@Modifying(clearAutomatically = true, flushAutomatically = true)
@Query("update Coupon c set c.expired = true where c.expiresAt < :now")
int expireCoupons(@Param("now") LocalDateTime now);
```

다만 `clearAutomatically = true`는 현재 영속성 컨텍스트의 관리 상태를 비워버리므로, 앞에서 로딩한 엔티티를 이후에 계속 수정하려는 로직과는 충돌할 수 있다. 편리하지만 부작용을 이해한 뒤 써야 한다.

---

## 핵심 개념 6: `merge()`는 "편한 업데이트"가 아니라 신중하게 다뤄야 할 복원 도구다

많은 팀에서 JPA 업데이트를 설명할 때 `merge()`를 예제로 먼저 보여준다. 하지만 실무에서는 `merge()`를 기본 업데이트 패턴으로 권장하기 어렵다.

왜냐하면 `merge()`는 전달된 객체를 그대로 관리 상태로 바꿔주는 것이 아니라,

1. 동일 식별자의 관리 엔티티를 찾거나 새로 로딩하고
2. 전달받은 객체의 값을 그 관리 엔티티에 복사한 뒤
3. 관리 엔티티를 반환하기 때문이다

이 과정 때문에 특히 "화면에서 온 부분 필드만 가진 객체"를 그대로 merge하면 위험하다.

### 흔한 사고 시나리오

```java
@PostMapping("/members/{id}")
public void update(@PathVariable Long id, @RequestBody Member request) {
    request.setId(id);
    entityManager.merge(request);
}
```

겉보기엔 간단하지만,

- 요청 바디에 없는 필드가 null로 들어올 수 있고
- 그 null이 기존 값 위에 덮어써질 수 있으며
- 어느 필드가 실제 수정 의도인지 코드에서 드러나지 않는다

즉 `merge()`는 의도 기반 업데이트보다 **상태 전체 복사**에 가깝다.

### 더 안전한 대안

- 요청 DTO를 받는다
- 서비스에서 관리 엔티티를 조회한다
- 명시적 메서드로 필요한 필드만 바꾼다

```java
@Transactional
public void updateMember(Long memberId, UpdateMemberRequest request) {
    Member member = memberRepository.findById(memberId)
            .orElseThrow();

    member.changeProfile(request.nickname(), request.phone());
}
```

이 패턴이 조금 더 길어 보여도 운영 안정성은 훨씬 높다.

### `merge()`가 상대적으로 맞는 경우

- 정말로 전체 상태 스냅샷을 다시 붙여야 하는 특수한 경우
- 장수 세션/분산 편집처럼 detached graph 재조립이 필요한 경우
- 프레임워크 내부 동작을 명확히 이해하고 제어 가능한 경우

대부분의 일반적인 웹 요청 업데이트에는 굳이 `merge()`를 기본 선택지로 둘 이유가 없다.

---

## 실무 예시 1: 일반 요청 처리에서는 "조회 후 변경"이 가장 예측 가능하다

주문 상태 변경 API를 생각해보자.

```java
@Service
@RequiredArgsConstructor
public class OrderService {

    private final OrderRepository orderRepository;

    @Transactional
    public void markAsPaid(Long orderId, PaymentConfirmedCommand cmd) {
        Order order = orderRepository.findById(orderId)
                .orElseThrow(() -> new IllegalArgumentException("order not found"));

        order.markAsPaid(cmd.paymentId(), cmd.paidAt());
    }
}
```

이 패턴의 장점은 명확하다.

- 현재 트랜잭션 안의 managed entity를 수정하므로 dirty checking이 안정적으로 동작
- 도메인 규칙을 엔티티 메서드에 모을 수 있음
- 어떤 필드가 왜 바뀌는지 코드 의도가 선명함
- 낙관적 락(`@Version`)과도 자연스럽게 결합 가능

여기서 굳이 `orderRepository.save(order)`를 다시 호출할 필요는 없다. 이미 managed 상태이기 때문이다.

물론 `save()`를 한 번 더 호출해도 구현상 큰 문제는 없을 수 있다. 하지만 팀원에게 잘못된 mental model을 심어준다. 결국 "JPA에서는 수정할 때 무조건 save"라는 오해가 퍼지고, 영속 상태와 준영속 상태의 차이가 코드에서 흐려진다.

---

## 실무 예시 2: 배치 처리에서는 `flush()`와 `clear()`를 세트로 생각해야 한다

수만 건을 한 트랜잭션에서 처리할 때는 dirty checking이 편리함보다 비용으로 바뀔 수 있다. 영속성 컨텍스트가 너무 커지면 다음 문제가 생긴다.

- 메모리 사용량 증가
- flush 시 비교 비용 증가
- 예상보다 긴 GC/응답 지연

예를 들어 대량 쿠폰 발급 배치를 생각해보자.

```java
@Transactional
public void issueCoupons(List<CouponIssueCommand> commands) {
    int batchSize = 1000;

    for (int i = 0; i < commands.size(); i++) {
        couponRepository.save(Coupon.issue(commands.get(i)));

        if ((i + 1) % batchSize == 0) {
            entityManager.flush();
            entityManager.clear();
        }
    }

    entityManager.flush();
    entityManager.clear();
}
```

여기서 `flush()`만 하고 `clear()`를 안 하면 이미 처리한 엔티티들이 계속 managed 상태로 남아 컨텍스트가 비대해진다. 반대로 `clear()`만 하고 flush를 안 하면 아직 SQL로 반영되지 않은 변경이 날아갈 수 있다.

즉 대량 처리에서는 보통 **flush + clear를 짝으로** 가져간다.

다만 배치 크기는 고정 공식이 없다.

- 엔티티 크기
- 연관관계 수
- JDBC batch 설정
- DB 락/redo log 특성
- 메모리 한도

이 조합에 따라 100, 500, 1000 중 최적점이 달라진다. 결국 측정이 필요하다.

---

## 실무 예시 3: 읽기 전용 트랜잭션은 성능 힌트이지 만능 보호막이 아니다

`@Transactional(readOnly = true)`를 붙이면 "쓰기 방지"라고 생각하기 쉽다. 하지만 이것 역시 구현체와 사용 방식에 따라 다르게 동작한다.

일반적으로 얻는 효과는 다음에 가깝다.

- flush 최적화 또는 스냅샷 관리 비용 감소 힌트
- JDBC/DB 레벨의 read-only 최적화 가능성
- 의도 표현

하지만 이것이 항상 강제적인 쓰기 금지는 아니다.

- 구현체/드라이버/DB 조합에 따라 실제 강제 수준이 다르다
- 엔티티 값을 바꿨다고 해서 무조건 예외가 즉시 나는 것은 아니다
- 코드 작성자가 "어차피 readOnly니까 안전"이라고 방심하면 오히려 문제를 늦게 발견한다

따라서 read-only 트랜잭션은 성능 힌트와 의도 표현으로 보되, **쓰기 방지의 최후 방어선**으로 믿으면 안 된다. 중요한 것은 서비스 메서드 자체를 읽기/쓰기 유즈케이스로 분리하는 구조다.

---

## 트레이드오프: 엔티티 변경 감지는 편리하지만, 모든 쓰기에 무조건 정답은 아니다

dirty checking 중심 모델은 분명 강력하다. 하지만 모든 상황에서 최적은 아니다.

### 1) 장점

- 비즈니스 규칙을 엔티티 메서드에 자연스럽게 모을 수 있다
- 수정 의도가 코드에 잘 드러난다
- 낙관적 락, 연관관계 관리, 트랜잭션 경계와 잘 맞는다
- 일반 CRUD/업무 흐름에서는 생산성과 안정성이 높다

### 2) 단점

- 대량 업데이트에는 비효율적일 수 있다
- 영속성 컨텍스트를 이해하지 못하면 디버깅 난도가 급상승한다
- 벌크 연산, 외부 SQL, 캐시와 섞이면 상태 불일치가 생길 수 있다
- detached graph 병합 같은 시나리오에서는 의도보다 과한 상태 복사가 일어나기 쉽다

### 3) 언제 다른 접근이 더 나은가

아래 경우에는 엔티티 수정보다 다른 방식이 낫다.

- 수십만 건 일괄 상태 변경 → 벌크 update 또는 배치 SQL
- 집계성/통계성 갱신 → 전용 SQL 또는 stored procedure 검토
- 읽기 모델 동기화 → CQRS read model 갱신 파이프라인
- 단순 카운터 증가/감소 → 조건부 update SQL이 더 명확한 경우 많음

핵심은 "JPA니까 무조건 엔티티를 조회해서 바꾸자"가 아니라, **유즈케이스의 데이터 shape와 트래픽 특성에 맞는 쓰기 전략을 고르는 것**이다.

---

## 흔한 실수 1: DTO 없이 엔티티를 API 요청/응답 모델로 직접 쓴다

이 패턴은 초반에는 빠르지만, 결국 영속 상태와 외부 입력이 뒤섞인다.

문제는 다음과 같다.

- 수정 가능 필드가 과도하게 노출됨
- 의도하지 않은 null overwrite 위험
- LAZY 필드 직렬화 문제
- 컨트롤러와 영속성 컨텍스트 결합 심화

쓰기 경로에서는 특히 위험하다. DTO로 경계를 분리하고, 엔티티는 서비스 내부에서만 변경하는 편이 훨씬 안전하다.

---

## 흔한 실수 2: 벌크 연산 뒤에 같은 엔티티를 그대로 믿는다

아래 패턴은 자주 보인다.

1. 주문 목록을 조회한다
2. 벌크 update로 상태를 바꾼다
3. 아까 조회한 엔티티 리스트를 그대로 응답한다

그러면 메모리 상태와 DB 상태가 다를 수 있다. 벌크 연산 이후에는 재조회 또는 clear를 기본 습관으로 가져가는 것이 안전하다.

---

## 흔한 실수 3: flush 타이밍을 로깅 결과만 보고 판단한다

Hibernate SQL 로그를 보면 "여기서 update가 나갔네?"라고 결론 내리고 싶어진다. 하지만 그 로그만으로는 다음이 구분되지 않는다.

- flush인지 commit인지
- 현재 트랜잭션 안에서만 보이는 상태인지
- 다른 쿼리 실행을 위해 선행 flush된 것인지

운영 장애 분석에서는 SQL 로그, 트랜잭션 경계, 락 대기, 예외 발생 시점을 함께 봐야 정확하다.

---

## 흔한 실수 4: 테스트에서 flush를 생략한 채 제약 조건 검증을 믿는다

unique key, foreign key, not null 위반은 실제로는 flush 시점에 드러나는 경우가 많다. 그런데 테스트가 끝날 때 한꺼번에 롤백되면 본문에서는 안 보이고 지나갈 수 있다.

그래서 다음과 같은 테스트는 자주 필요하다.

- 중복 저장 직후 `flush()` 호출
- FK 연결 해제 직후 `flush()` 호출
- 삭제/삽입 순서가 민감한 로직에서 중간 `flush()` 호출

즉 JPA 테스트는 "메서드 호출이 끝났다"가 아니라 **"실제 SQL 검증이 일어났는가"**까지 봐야 한다.

---

## 운영 체크리스트: JPA 쓰기 경로를 안전하게 만드는 질문들

- [ ] 서비스 메서드가 **조회 후 managed entity 변경** 패턴을 따르는가?
- [ ] API 요청 모델과 엔티티를 분리했는가?
- [ ] `merge()` 사용 지점을 설명 가능하게 제한했는가?
- [ ] 벌크 update/delete 뒤에 clear 또는 재조회 전략이 있는가?
- [ ] 대량 배치에서 flush/clear 주기를 측정 기반으로 잡았는가?
- [ ] 테스트에서 필요한 지점에 명시적 flush를 넣어 제약 조건을 조기 검증하는가?
- [ ] `saveAndFlush()`가 습관적으로 쓰이지 않고, 이유 있는 곳에만 존재하는가?
- [ ] readOnly 트랜잭션을 "쓰기 금지 마법"으로 오해하지 않는가?
- [ ] 낙관적 락(`@Version`)이 필요한 업데이트 경합 지점에 적용돼 있는가?
- [ ] 외부 SQL, 배치, 캐시와 JPA 상태 불일치가 생길 수 있는 경계를 문서화했는가?

---

## 한 줄 정리

JPA 쓰기 경로의 핵심은 `save()` 호출 횟수가 아니라, **영속성 컨텍스트가 어떤 엔티티를 추적하고 언제 flush하며 벌크 연산·준영속 상태와 어디서 충돌하는지**를 정확히 통제하는 데 있다.
