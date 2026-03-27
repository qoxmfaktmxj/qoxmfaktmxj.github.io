---
layout: post
title: "Spring Data JPA 조회 성능 실전: N+1, Fetch Join, Batch Size, EntityGraph 운영 기준"
date: 2026-03-27 11:40:00 +0900
categories: [java]
tags: [study, java, spring, jpa, hibernate, performance, backend, orm, query-optimization]
---

## 배경: JPA 성능 문제는 보통 "느린 쿼리 1개"보다 "생각보다 많이 나가는 쿼리 여러 개"에서 터진다

실무에서 JPA가 어렵게 느껴지는 이유는 문법보다 **실행 시점의 SQL이 코드에서 바로 보이지 않기 때문**이다.

특히 다음 상황에서 성능 문제가 반복된다.

- 목록 API 하나 호출했는데 쿼리가 수십~수백 개 나간다
- 개발 환경에서는 괜찮은데 운영 데이터에서 갑자기 응답 시간이 급증한다
- `LAZY`로 바꿨는데도 N+1이 사라지지 않는다
- `fetch join`으로 해결했더니 이번엔 pagination이 깨진다
- 급한 마음에 전부 `EAGER`로 바꿨다가 다른 화면이 더 느려진다

즉 핵심은 JPA를 "엔티티를 편하게 다루는 도구"로만 보면 안 되고, **조회 시점의 fetch plan을 통제하는 도구**로 봐야 한다는 점이다.

이 글은 중급 이상 개발자를 기준으로, JPA 조회 성능 이슈를 다음 순서로 정리한다.

1. 왜 N+1이 생기는가
2. `fetch join`, `EntityGraph`, `batch size`, `DTO projection`을 언제 쓰는가
3. pagination·컬렉션·중복 row가 왜 문제인가
4. 운영에서 안전한 조회 전략은 무엇인가

---

## 문제 정의: N+1은 JPA를 쓴다는 사실보다 "조회 의도를 명시하지 않았다"는 신호다

예를 들어 주문 목록을 조회한다고 하자.

- `Order` → `Member` (N:1)
- `Order` → `Delivery` (1:1)
- `Order` → `OrderItem` (1:N)
- `OrderItem` → `Product` (N:1)

코드는 평범해 보인다.

```java
@GetMapping("/api/orders")
public List<OrderSummaryResponse> orders() {
    List<Order> orders = orderRepository.findAll();

    return orders.stream()
            .map(order -> new OrderSummaryResponse(
                    order.getId(),
                    order.getMember().getName(),
                    order.getDelivery().getAddress(),
                    order.getStatus()
            ))
            .toList();
}
```

하지만 실제로는 다음과 같은 일이 벌어질 수 있다.

1. `findAll()`이 주문 목록 1번 조회
2. 각 주문마다 `member` 조회
3. 각 주문마다 `delivery` 조회
4. 상세 정보까지 펼치면 각 주문마다 `orderItems` 조회
5. 각 아이템마다 `product` 조회

결국 1개의 API가 `1 + N + N + N + M...` 구조로 부풀어 오른다.

이게 바로 N+1이다.

중요한 포인트는 이것이 단순히 LAZY 설정 하나의 문제가 아니라는 점이다.
**어떤 연관을 지금 같이 읽을지 쿼리 수준에서 명시하지 않으면, JPA는 필요한 순간마다 추가 조회를 날린다.**

---

## 핵심 개념 1: LAZY와 EAGER는 "영원한 정답"이 아니라 기본값일 뿐이다

많이 하는 오해가 있다.

- `LAZY`면 N+1이 안 생긴다
- `EAGER`면 한 번에 다 가져오니 빠르다

둘 다 절반만 맞다.

### LAZY의 본질

`LAZY`는 연관 객체를 당장 가져오지 않고 프록시로 미룬다.
장점은 불필요한 로딩을 줄일 수 있다는 점이다.
하지만 실제 사용 시점에 접근하면 추가 쿼리가 나간다.

즉,

- 안 쓰면 이득
- 반복문 안에서 쓰면 N+1 폭발

이라는 특성을 가진다.

### EAGER의 본질

`EAGER`는 연관을 즉시 로딩하려고 시도한다.
문제는 "항상 같이 필요하다"는 보장이 거의 없다는 점이다.
화면 A에서만 필요한 연관을 화면 B에서도 매번 끌고 오게 될 수 있다.

게다가 JPQL/Querydsl 쿼리에서는 `EAGER`라고 해서 항상 깔끔한 single query가 보장되는 것도 아니다.
조회 경로와 구현체 전략에 따라 추가 쿼리가 생길 수 있다.

### 실무 기준

- 엔티티 연관 기본값은 **대체로 LAZY**로 둔다
- 실제 조회 최적화는 **쿼리 단위에서 명시적으로 제어**한다
- "어디서나 빠른 엔티티"를 만들려 하지 말고 **유즈케이스별 조회 모델**을 만든다

이 기준이 흔들리면 프로젝트 후반으로 갈수록 화면마다 성능 문제가 다르게 터진다.

---

## 핵심 개념 2: JPA 조회 성능은 결국 fetch plan 설계다

fetch plan은 간단히 말해 다음 질문에 대한 답이다.

> "이 유즈케이스에서 어떤 연관을, 어느 깊이까지, 한 번에 읽을 것인가?"

실무에서는 보통 조회를 3종류로 나눠 생각하면 정리가 쉽다.

### 1) 목록 조회

특징:

- row 수가 많다
- pagination이 중요하다
- 컬렉션을 한 번에 붙이면 row 중복이 커진다

전략:

- `ToOne` 연관은 fetch join 검토
- `ToMany`는 지연 로딩 + batch 조회 또는 별도 조회
- 정말 필요한 필드만 DTO projection 고려

### 2) 상세 조회

특징:

- 한 건 혹은 소수 건 조회
- 화면에서 연관 데이터 여러 덩어리를 같이 보여줄 수 있다

전략:

- fetch join 또는 `EntityGraph` 적극 활용 가능
- 컬렉션 포함도 상대적으로 안전
- 단, 중복 row와 메모리 사용량은 확인 필요

### 3) 집계/리포트 조회

특징:

- 엔티티 그래프보다 SQL shape가 중요하다
- group by, aggregation, window function이 많다

전략:

- 엔티티보다 **DTO projection / native query / 전용 read model**이 더 적합한 경우가 많다

많은 팀이 실패하는 이유는 이 세 가지를 구분하지 않고, 모든 조회를 `findById`, `findAll`, `@OneToMany` 탐색으로 해결하려 하기 때문이다.

---

## 핵심 개념 3: fetch join은 강력하지만, 특히 컬렉션에서는 함정이 많다

### fetch join이 잘 맞는 경우: ToOne 연관

예를 들어 주문 목록에서 주문자와 배송지만 같이 보여주고 싶다면 다음처럼 `ToOne` 관계는 fetch join으로 묶기 좋다.

```java
@Query("""
    select o
    from Order o
    join fetch o.member m
    join fetch o.delivery d
    order by o.id desc
""")
List<Order> findOrderSummaries();
```

장점:

- 주문, 회원, 배송 정보를 한 번에 읽는다
- 목록 API에서 자주 발생하는 N+1을 크게 줄인다
- `ToOne` 조인은 row 폭증 위험이 상대적으로 적다

### fetch join이 위험한 경우: ToMany 컬렉션

```java
@Query("""
    select o
    from Order o
    join fetch o.orderItems oi
    join fetch oi.product p
""")
List<Order> findOrdersWithItems();
```

이 쿼리는 상세 화면 몇 건에는 유용할 수 있지만, 목록 화면에서는 문제가 된다.

#### 왜 위험한가?

1. **중복 row 증가**
   - 주문 1건에 아이템 5개면 주문 row가 5배로 불어난다
2. **pagination이 사실상 깨진다**
   - DB 기준 row paging과 애플리케이션 기준 엔티티 수 paging이 어긋난다
3. **메모리 사용량 증가**
   - 조인 결과가 커질수록 영속성 컨텍스트와 JDBC result set 부담이 커진다

Hibernate는 컬렉션 fetch join + pagination 조합에 대해 경고를 내거나 메모리 paging으로 밀어버리기도 한다. 이 패턴을 운영 목록 API에 넣으면 트래픽이 늘수록 바로 병목이 된다.

### 결론

- **목록 조회:** 컬렉션 fetch join 지양
- **상세 조회:** 건수가 작을 때만 선택적으로 허용
- **대용량 조회:** DTO projection이나 2단계 조회가 더 안전

---

## 실무 예시 1: 주문 목록 API 최적화

요구사항:

- 최근 주문 20건 조회
- 주문번호, 주문자명, 배송지, 상태, 총액 표시
- pagination 필요

### 잘못된 1차 구현

```java
public Page<OrderSummaryResponse> getOrders(Pageable pageable) {
    Page<Order> page = orderRepository.findAll(pageable);

    return page.map(order -> new OrderSummaryResponse(
            order.getId(),
            order.getMember().getName(),
            order.getDelivery().getAddress(),
            order.getStatus(),
            order.getTotalPrice()
    ));
}
```

문제:

- 페이지 20건이면 기본 1 query
- `member`, `delivery` 접근으로 최대 40 query 추가
- 총 41 query 수준으로 증가 가능

### 개선안 1: ToOne fetch join + countQuery 분리

```java
@Query(
    value = """
        select o
        from Order o
        join fetch o.member
        join fetch o.delivery
    """,
    countQuery = "select count(o) from Order o"
)
Page<Order> findPageWithMemberAndDelivery(Pageable pageable);
```

이 방식은 `ToOne`만 붙였을 때 꽤 현실적인 선택이다.

주의점:

- 정렬 컬럼이 조인 결과와 충돌하지 않는지 확인
- count 쿼리는 fetch join 없이 분리
- page size가 커질수록 실제 select 컬럼 수와 row width도 점검

### 개선안 2: DTO projection으로 바로 조회

```java
@Query("""
    select new com.example.order.api.OrderSummaryResponse(
        o.id,
        m.name,
        d.address,
        o.status,
        o.totalPrice
    )
    from Order o
    join o.member m
    join o.delivery d
""")
Page<OrderSummaryResponse> findOrderSummaryPage(Pageable pageable);
```

장점:

- API에 필요한 필드만 읽는다
- 엔티티 그래프 초기화 문제를 피할 수 있다
- 읽기 전용 목록 API에서는 더 명확하다

트레이드오프:

- 재사용성은 엔티티보다 낮다
- 화면 요구사항이 바뀌면 DTO 쿼리도 수정해야 한다
- 복잡한 조합이 많아지면 query 전용 repository가 필요하다

### 이 상황에서 내 권장안

- **목록 API**라면 DTO projection을 우선 검토
- 비즈니스 로직상 엔티티가 꼭 필요하다면 `ToOne fetch join`까지만 허용
- 컬렉션 데이터는 별도 endpoint 또는 2단계 조회로 분리

---

## 실무 예시 2: 주문 상세 API에서 컬렉션을 안전하게 다루는 방법

요구사항:

- 주문 1건 상세 조회
- 주문자, 배송지, 주문 아이템 목록, 각 상품명/가격 표시

이 경우는 목록이 아니라 상세이므로 컬렉션을 함께 읽을 여지가 있다.

```java
@Query("""
    select distinct o
    from Order o
    join fetch o.member
    join fetch o.delivery
    left join fetch o.orderItems oi
    left join fetch oi.product
    where o.id = :orderId
""")
Optional<Order> findDetailById(@Param("orderId") Long orderId);
```

여기서 `distinct`를 넣는 이유는 SQL row 중복과 JPA 엔티티 중복을 줄이기 위해서다. 다만 이것이 모든 비용을 없애주지는 않는다.

### 언제 괜찮은가?

- 단건 상세 조회
- row 수가 제한적임이 분명할 때
- 실제로 한 화면에서 다 필요할 때

### 언제 위험한가?

- 주문 상세라고 했지만 사실 내부적으로 100건을 한 번에 펼치는 배치성 API일 때
- 컬렉션 depth가 2단계 이상으로 커질 때
- JSON 직렬화 과정에서 양방향 연관이 추가 탐색을 유발할 때

### 더 안전한 대안: 2단계 조회

1. 주문 + 회원 + 배송지 조회
2. 주문 아이템 목록 별도 조회
3. 애플리케이션 레벨에서 조합

이 방식은 쿼리 수가 1번보다 약간 늘어도, row 폭증과 pagination 문제를 피하기 쉬워서 운영 안정성이 높다.

---

## 핵심 개념 4: Batch Size는 "한 번에 join"이 아니라 "한 번에 묶어서 추가 조회"다

컬렉션이나 다수의 `ToOne` 연관을 모두 fetch join으로 해결하려 하면 오히려 더 나빠진다. 이때 유용한 것이 `batch size`다.

예를 들어 주문 20건을 읽고 각 주문의 `member` 또는 `orderItems`를 lazy 로딩한다고 하자. 배치 사이즈가 없으면 주문마다 개별 쿼리가 나갈 수 있다. 하지만 Hibernate의 batch fetching을 활용하면 다음처럼 묶을 수 있다.

- 원래: `select ... where id=?` 20번
- 개선: `select ... where id in (?, ?, ..., ?)` 몇 번

### 설정 예시

```yaml
spring:
  jpa:
    properties:
      hibernate:
        default_batch_fetch_size: 100
```

또는 연관/엔티티별로 개별 지정할 수도 있다.

```java
@OneToMany(mappedBy = "order")
@BatchSize(size = 100)
private List<OrderItem> orderItems = new ArrayList<>();
```

### batch size가 특히 잘 맞는 경우

- 목록 페이지에서 `ToOne`, `ToMany` 일부를 lazy 로딩해야 할 때
- fetch join으로 row 폭증이 우려될 때
- API 응답 조립 과정에서 여러 연관을 제한적으로 읽을 때

### 주의할 점

- 숫자를 무조건 크게 잡는다고 좋은 게 아니다
- DB의 `IN` 절 길이, 실행 계획, 네트워크 패킷 크기 영향을 본다
- 흔히 100~500 사이에서 실측으로 결정한다
- batch size는 문제를 숨기는 만능약이 아니라 **조회 패턴을 완화하는 장치**다

실무적으로는 `ToOne fetch join + 컬렉션 batch fetch` 조합이 자주 안정적이다.

---

## 핵심 개념 5: EntityGraph는 리포지토리 메서드 의도를 드러내는 데 좋다

`fetch join`이 쿼리 문자열 수준 제어라면, `EntityGraph`는 "이 메서드는 이 연관까지 같이 읽는다"는 의도를 메타데이터로 표현하는 도구다.

```java
@EntityGraph(attributePaths = {"member", "delivery"})
@Query("select o from Order o where o.status = :status")
List<Order> findByStatusWithMemberAndDelivery(@Param("status") OrderStatus status);
```

장점:

- 메서드 수준에서 fetch 의도가 드러난다
- 단순 조회에서 JPQL을 덜 복잡하게 유지할 수 있다
- Spring Data JPA와 조합이 편하다

한계:

- 복잡한 조인 조건, 정렬, projection 제어는 fetch join/JPQL이 더 낫다
- 컬렉션을 여러 단계로 깊게 붙이는 순간 결국 복잡도가 커진다
- 팀이 SQL shape를 명확히 검토하지 않으면 "편해서 썼다가" 실제 쿼리를 놓치기 쉽다

### 언제 쓰면 좋은가?

- 단순한 find 메서드 확장
- `ToOne` 연관 몇 개를 안정적으로 묶고 싶을 때
- 동일한 조회 의도가 반복될 때

### 언제 DTO projection이 더 낫나?

- API 전용 읽기 모델일 때
- 필요한 필드가 엔티티 전체보다 훨씬 적을 때
- aggregation/join shape가 복잡할 때

---

## 핵심 개념 6: 엔티티 조회와 API 응답 모델을 분리해야 운영이 편해진다

많은 성능 문제는 사실 JPA의 문제가 아니라, **엔티티를 그대로 API 모델처럼 취급하는 습관**에서 시작된다.

대표적인 안 좋은 흐름은 이렇다.

1. 컨트롤러가 엔티티를 직접 반환한다
2. JSON 직렬화 중 lazy 로딩이 발생한다
3. 트랜잭션 밖에서 프록시 초기화 예외가 난다
4. 이를 피하려고 Open Session In View에 의존한다
5. 결국 웹 요청 전체에서 SQL이 새어나간다

이 흐름이 익숙하다면 구조를 다시 봐야 한다.

### 실무 권장 흐름

- 엔티티는 도메인/쓰기 모델 중심으로 유지
- 조회는 유즈케이스별 read model 또는 DTO를 둔다
- 컨트롤러는 엔티티가 아니라 응답 DTO를 반환한다
- query repository를 분리해 조회 의도를 명시한다

이렇게 하면 성능뿐 아니라 변경 영향도도 줄어든다.
예를 들어 화면 컬럼이 추가돼도 도메인 모델 전체를 흔들 필요가 없다.

---

## 트레이드오프 정리: 무엇을 언제 선택할까

### 1) fetch join

적합:

- `ToOne` 연관 최적화
- 단건 상세 조회
- row 폭증이 통제 가능한 경우

장점:

- 쿼리 수를 직접적으로 줄이기 좋다
- SQL shape가 비교적 예측 가능하다

단점:

- 컬렉션 join 시 중복 row 증가
- pagination과 충돌 가능
- 조회가 커질수록 쿼리 자체가 무거워진다

### 2) EntityGraph

적합:

- 리포지토리 메서드 단위 fetch 의도 표현
- 단순 반복 조회 패턴

장점:

- 코드 가독성이 좋다
- Spring Data 메서드와 자연스럽게 붙는다

단점:

- 복잡한 요구사항에서는 한계가 빠르다
- 실제 SQL을 안 보면 오해하기 쉽다

### 3) Batch Size

적합:

- 컬렉션 lazy loading 완화
- fetch join으로 해결하기 어려운 목록 화면

장점:

- join row 폭증 없이 쿼리 수를 줄일 수 있다
- 기존 엔티티 모델을 크게 바꾸지 않고 개선 가능

단점:

- 여전히 추가 조회는 존재한다
- 숫자 튜닝을 잘못하면 효과가 제한적이다

### 4) DTO Projection

적합:

- 읽기 전용 API
- 화면별 요구사항이 명확한 경우
- 대용량 목록, 리포트, 집계

장점:

- 필요한 데이터만 가져온다
- 엔티티 그래프 문제를 피해간다
- 성능과 응답 구조가 더 명시적이다

단점:

- 쿼리/DTO 코드가 늘어난다
- 도메인 재사용성과는 결이 다르다

### 내 실무 기준 한 줄 버전

- **쓰기/도메인 로직:** 엔티티 중심
- **읽기 API:** DTO 중심
- **연관 최적화:** ToOne fetch join 우선
- **컬렉션:** batch fetch 또는 2단계 조회 우선

---

## 흔한 실수 1: "N+1이 보이니 일단 전부 fetch join"

이건 초반에는 효과가 있어 보여도 금방 다른 문제를 만든다.

- 목록 조회에서 중복 row 증가
- 정렬/페이지네이션 이상 동작
- 쿼리 한 번이 지나치게 무거워짐
- 메모리 점유와 직렬화 비용 증가

핵심은 쿼리 수만 줄이는 것이 아니라 **총 비용을 줄이는 것**이다.
"1 query"는 목표가 아니라 수단이다.

---

## 흔한 실수 2: 엔티티 연관을 EAGER로 바꾸고 끝냈다고 생각한다

EAGER는 화면마다 다른 조회 요구를 전역 설정으로 덮는 방식이라 장기적으로 거의 항상 문제가 된다.

- 어떤 화면에서는 과조회(over-fetch)
- 어떤 화면에서는 여전히 추가 조회
- 테스트/운영 환경에서 예상이 어긋남

엔티티 매핑은 정적이고, 화면 요구사항은 동적이다. 이 둘을 같은 레벨에서 풀려 하면 설계가 꼬인다.

---

## 흔한 실수 3: 성능 측정을 로그 감으로만 한다

"왠지 빨라졌다"는 거의 항상 위험하다.
조회 최적화는 체감이 아니라 숫자로 봐야 한다.

### 최소한 확인해야 할 것

- API 1회 호출당 SQL 개수
- 가장 오래 걸린 쿼리의 실행 시간
- page size 증가 시 응답 시간 변화
- result set row 수
- DB CPU / buffer hit / index 사용 여부

### 추천 습관

- 로컬/테스트 환경에서 SQL 로그와 바인딩 값 확인
- `datasource-proxy`, `p6spy`, Hibernate statistics 등으로 query count 추적
- 주요 목록 API에 대해 query count 회귀 테스트 작성

예를 들면 "주문 목록 20건 조회 시 SQL 3개 이하" 같은 식의 기준을 둘 수 있다.
이런 테스트가 없으면 리팩터링 한 번에 다시 N+1이 들어온다.

---

## 흔한 실수 4: OSIV(Open Session In View)에 기대서 문제를 뒤로 미룬다

OSIV가 켜져 있으면 컨트롤러/뷰 직렬화 시점까지 영속성 컨텍스트가 살아 있어서 lazy 로딩이 "되긴" 한다. 그래서 당장은 편하다.
하지만 운영에서는 다음 비용이 따라온다.

- 웹 계층에서 예상치 못한 SQL 실행
- 응답 직렬화 중 N+1 발생
- 트랜잭션 경계가 흐려져 디버깅 어려움
- 서비스 계층 밖에서 DB 접근이 새어나감

실무적으로는 **OSIV를 성능 문제 해결 수단으로 쓰지 않는 편이 낫다.**
필요한 데이터는 서비스/리포지토리 계층에서 조회 의도를 명시적으로 확정하고 끝내는 쪽이 운영 가시성이 높다.

---

## 흔한 실수 5: "엔티티니까 재사용성이 높다"며 모든 조회를 엔티티로 처리한다

대규모 서비스에서 읽기 요구사항은 화면/배치/외부연동마다 다르다. 하나의 엔티티 그래프로 모든 조회를 감당하려 하면 결국 다음이 반복된다.

- 어떤 API는 필드가 너무 많다
- 어떤 API는 조인이 너무 깊다
- 어떤 API는 aggregation 때문에 엔티티가 부적합하다

읽기 모델을 분리하면 처음엔 코드가 조금 늘어도, 후반 유지보수 비용이 줄어든다. 특히 검색 화면·대시보드·관리자 목록은 엔티티 직렬화보다 DTO projection이 거의 항상 더 낫다.

---

## 운영 체크포인트: JPA 조회 성능은 코드 리뷰보다 "쿼리 리뷰"가 중요하다

아래 질문에 답하지 못하면 성능 최적화가 끝난 것이 아니다.

1. 이 API는 평균 몇 건을 조회하는가?
2. 연관 데이터는 `ToOne`인가 `ToMany`인가?
3. pagination이 필요한가?
4. 결과를 엔티티로 유지해야 하는가, DTO면 충분한가?
5. query count, row 수, 응답 시간 측정값이 있는가?
6. 최악 데이터 규모에서 동일한 전략이 유지되는가?

특히 목록 API는 "지금 20건이라 괜찮다"가 가장 위험하다. 트래픽이 늘고 필터가 늘고 정렬 조건이 추가되면 금방 병목이 된다.

---

## 실무 체크리스트

- [ ] 엔티티 연관 기본 전략을 무분별한 `EAGER` 대신 `LAZY` 중심으로 두었는가?
- [ ] 목록 조회와 상세 조회를 같은 fetch 전략으로 처리하지 않는가?
- [ ] 목록 API에서 컬렉션 fetch join + pagination 조합을 쓰고 있지 않은가?
- [ ] `ToOne` 연관은 fetch join 또는 EntityGraph로 의도적으로 최적화했는가?
- [ ] 컬렉션은 batch fetch 또는 2단계 조회로 분리했는가?
- [ ] 읽기 전용 API에서 DTO projection을 검토했는가?
- [ ] 컨트롤러가 엔티티를 직접 반환하지 않는가?
- [ ] 주요 API의 query count와 응답 시간 기준선을 테스트로 남겼는가?
- [ ] OSIV에 기대지 않고 서비스 계층 안에서 필요한 데이터를 확정하는가?
- [ ] 운영 데이터 규모를 가정한 pagination/정렬/필터 조합을 검증했는가?

---

## 한 줄 정리

JPA 조회 성능의 본질은 "N+1을 없애는 요령"이 아니라, **유즈케이스별 fetch plan을 명시하고 목록·상세·집계 조회를 다른 전략으로 설계하는 것**이다.
