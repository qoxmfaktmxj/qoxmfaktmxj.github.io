---
layout: post
title: "JPA 대량 쓰기 실전: Hibernate JDBC Batching, flush/clear, ID 전략, order_inserts로 배치 성능과 정합성을 함께 잡는 법"
date: 2026-05-02 11:40:00 +0900
categories: [java]
tags: [study, java, spring, jpa, hibernate, jdbc-batching, batch-insert, batch-update, flush-clear, backend, performance, operations]
permalink: /java/2026/05/02/study-jpa-jdbc-batching-hibernate-batch-write-flush-clear-identity.html
---

## 배경: `saveAll()`만 믿고 대량 쓰기를 올리면 왜 운영에서 바로 무너지나

JPA를 쓰는 팀이 일정 규모를 넘기면 거의 반드시 한 번은 만난다.

- 엑셀 업로드 5만 건이 예상보다 20배 느리다
- 야간 배치가 아침까지 안 끝난다
- `saveAll()`을 썼는데도 insert가 한 줄씩 날아간다
- 업데이트 작업 하나에 힙 메모리가 계속 쌓인다
- 배치 성능을 올리려다 DB 락 시간이 길어지고 롤백 비용이 폭증한다
- `IDENTITY`를 쓰는 엔티티는 왜 batch가 안 붙는지 설명이 안 된다
- `@DynamicUpdate`, cascade, orphanRemoval을 켜 놓고 배치가 깨지는 줄도 모른다

여기서 흔한 오해가 있다.

> 대량 쓰기 성능 문제는 JPA가 느려서 생긴다.

절반만 맞다. 더 정확히 말하면 **대량 쓰기에서는 ORM·ID 생성 전략·영속성 컨텍스트·JDBC 드라이버·DB 트랜잭션 설계가 서로 어긋날 때** 성능과 안정성이 같이 무너진다.

조회 최적화 글은 많다. N+1, fetch join, projection 이야기는 팀 내에서도 자주 공유된다. 그런데 실무 운영 이슈는 조회보다 **쓰기 경로의 구조적 비효율**에서 터지는 경우가 많다. 이유는 간단하다. 대량 쓰기는 아래 비용이 한꺼번에 겹치기 때문이다.

- 애플리케이션 레벨: 엔티티 생성, dirty checking, 영속성 컨텍스트 메모리
- ORM 레벨: SQL shape 분산, flush 타이밍, action queue 정렬
- JDBC 레벨: batch 크기, statement 재사용, driver rewrite 여부
- DB 레벨: WAL/redo, lock, index maintenance, FK check, undo/rollback cost
- 운영 레벨: 재시도, 멱등성, 부분 실패 복구, 작업 재개 지점

즉 대량 쓰기 최적화의 핵심은 단순히 `hibernate.jdbc.batch_size` 하나 넣는 것이 아니다.

**어떤 쓰기 경로를 엔티티 단위로 유지할지, 어디서 chunk를 끊을지, 어떤 ID 전략이 batch를 막는지, 언제 JPA를 포기하고 JDBC/native bulk로 내려갈지**를 결정하는 일이다.

이 글은 중급 이상 개발자를 기준으로 아래를 정리한다.

1. Hibernate JDBC batching이 실제로 동작하는 조건
2. `IDENTITY`, `SEQUENCE`, 앱 생성 ID가 batch 성능에 미치는 차이
3. `flush()` / `clear()` / chunk commit을 어떻게 잡아야 하는지
4. cascade, `@DynamicUpdate`, version 컬럼, 연관관계가 batch를 어떻게 깨뜨리는지
5. 실무에서 insert/update/backfill 배치를 어떻게 설계하면 운영 가능한지
6. 언제 JPA를 유지하고, 언제 `JdbcTemplate`, bulk SQL, `COPY`/`LOAD DATA`로 내려가야 하는지

이 글의 결론을 먼저 한 줄로 요약하면 이렇다.

> JPA 대량 쓰기의 성패는 `saveAll()` 호출 횟수가 아니라, **SQL 모양을 얼마나 균질하게 만들고 영속성 컨텍스트·트랜잭션·ID 생성 전략을 batch 친화적으로 설계했는가**에 달려 있다.

---

## 먼저 큰 그림: 대량 쓰기에서 진짜 병목은 “엔티티 수”가 아니라 “쓰기 경로의 불일치”다

팀에서 배치 성능 이슈를 처음 겪으면 보통 이렇게 본다.

- row 수가 많다
- JPA 객체가 많다
- DB insert/update가 많다
- 그래서 느리다

틀린 말은 아니다. 하지만 이 설명만으로는 문제를 절반밖에 못 본다. 실제로는 같은 10만 건 insert여도 구조에 따라 체감 성능이 완전히 달라진다.

예를 들어 아래 두 작업을 비교해 보자.

### 작업 A

- 단일 엔티티 타입
- `SEQUENCE` 또는 애플리케이션 생성 ID
- 컬럼 shape가 거의 동일
- `hibernate.jdbc.batch_size=500`
- `order_inserts=true`
- 500건마다 `flush()` + `clear()`
- 한 chunk당 짧은 트랜잭션

### 작업 B

- `IDENTITY` 기반 PK
- 여러 엔티티 타입이 뒤섞임
- `@DynamicUpdate`로 SQL shape가 계속 달라짐
- cascade로 자식 insert/update/delete가 섞임
- 5만 건을 한 트랜잭션으로 몰아넣음
- 중간 flush 없음

둘 다 “JPA로 10만 건 쓴다”는 문장으로 표현할 수 있지만, 실제 비용 구조는 완전히 다르다.

작업 A는 적어도 다음이 정렬되어 있다.

- 동일 SQL shape
- 배치 가능한 ID 전략
- 작은 영속성 컨텍스트
- 제어 가능한 트랜잭션 길이
- 실패 후 재시작 가능한 chunk 경계

작업 B는 반대로 거의 모든 레이어가 배치에 적대적이다.

- PK 획득 때문에 즉시 insert가 필요함
- SQL 모양이 흩어짐
- write-behind queue가 과도하게 커짐
- dirty checking 비용이 계속 증가함
- 롤백 비용과 락 보유 시간이 비정상적으로 커짐

즉 대량 쓰기는 “몇 건이냐”보다 **배치 가능한 shape로 정규화되어 있느냐**가 훨씬 중요하다.

---

## 핵심 개념 1: Hibernate JDBC batching은 “같은 SQL을 묶어 보내는 것”이지 “엔티티를 자동으로 뭉개주는 마법”이 아니다

대량 쓰기를 이해할 때 가장 먼저 잡아야 할 개념이 이것이다.

Hibernate의 JDBC batching은 대략 이런 흐름으로 동작한다.

1. 애플리케이션이 엔티티를 persist 또는 변경한다
2. Hibernate는 이를 action queue에 모은다
3. flush 시점에 SQL을 만든다
4. **같은 SQL shape**를 갖는 statement끼리 JDBC batch로 묶는다
5. driver가 이를 DB에 더 효율적으로 전달한다

즉 batching의 핵심은 “엔티티 개수”가 아니라 **동일 prepared statement를 반복해서 바인딩할 수 있느냐**다.

### 왜 SQL shape가 중요한가

아래와 같은 insert는 batch로 잘 묶인다.

```sql
insert into product (id, name, price, status) values (?, ?, ?, ?)
```

이 SQL이 수백 번 반복되면 driver는 같은 statement에 파라미터만 바꿔서 묶어 보낼 수 있다.

반면 아래처럼 섞이면 batch 효율이 급격히 떨어진다.

- `product` insert와 `product_option` insert가 번갈아 나감
- 같은 엔티티여도 null 컬럼/동적 업데이트 때문에 SQL column set이 계속 달라짐
- flush 시점에 insert와 update와 delete가 뒤섞임

즉 batch 성능을 높인다는 말은 결국 다음 질문으로 환원된다.

> **내 쓰기 경로가 Hibernate가 같은 SQL을 연속적으로 만들기 쉬운 구조인가?**

### 기본 설정 예시

보통 시작점은 아래와 같다.

```properties
spring.jpa.properties.hibernate.jdbc.batch_size=500
spring.jpa.properties.hibernate.order_inserts=true
spring.jpa.properties.hibernate.order_updates=true
```

이 세 옵션이 의미하는 바는 단순하다.

- `batch_size`: JDBC batch에 몇 건까지 묶을지
- `order_inserts`: insert action을 엔티티 타입/SQL shape 기준으로 정렬해 batch 기회를 늘림
- `order_updates`: update도 비슷하게 정렬해 batch 기회를 늘림

하지만 여기서 멈추면 안 된다. 이 설정은 **기회를 열어 줄 뿐**, 실제 batch가 붙는지는 아래에 달려 있다.

- ID 생성 전략
- flush 타이밍
- SQL shape 일관성
- version/optimistic locking 설정
- JDBC 드라이버 지원 방식
- DB 엔진 특성

### driver 레벨 최적화도 별개다

같은 JDBC batch라도 driver가 DB에 어떻게 전달하느냐는 다를 수 있다.

예를 들어 많이 보는 설정은 이런 것들이다.

- MySQL 계열: `rewriteBatchedStatements=true`
- PostgreSQL 계열: `reWriteBatchedInserts=true`

이건 “JPA 설정”이 아니라 “JDBC 드라이버가 batch SQL을 어떻게 재작성해 전송할지” 문제다. 즉 ORM 레벨에서 batch를 켰다고 끝이 아니다.

실무에서는 다음처럼 봐야 한다.

1. Hibernate 통계나 SQL 로그로 batch가 실제로 묶였는지 확인
2. DB 측 statement count, rows written, network round-trip 감소 여부 확인
3. p95/p99 latency와 전체 배치 시간 개선을 같이 확인

대량 쓰기에서 **설정했다 = 적용됐다** 는 거의 항상 틀린 가정이다.

---

## 핵심 개념 2: ID 생성 전략이 insert batching을 거의 결정해 버린다

대량 insert에서 제일 자주 놓치는 축이 PK 생성 전략이다. 특히 `IDENTITY`를 기본처럼 쓰는 팀은 여기서 바로 batch 성능이 깨진다.

### 왜 `IDENTITY`가 문제인가

`IDENTITY`는 DB가 row insert 시점에 PK를 생성해 준다. 즉 Hibernate 입장에서는 insert를 실제로 보내기 전까지 ID를 알 수 없다.

이 말은 곧 다음 뜻이다.

- 엔티티를 `persist()`했다고 해서 메모리에서만 쌓아 둘 수 없음
- PK를 얻기 위해 insert를 더 즉시 실행해야 함
- 결과적으로 insert batching 기회가 크게 줄어듦

실무에서 자주 보는 코드가 이렇다.

```java
@Transactional
public void importProducts(List<ProductCommand> commands) {
    for (ProductCommand command : commands) {
        productRepository.save(Product.from(command));
    }
}
```

여기서 엔티티가 `GenerationType.IDENTITY`라면, 개발자는 save를 루프 안에서 돌리더라도 “JPA가 알아서 모아 주겠지”라고 기대하기 쉽다. 하지만 실제로는 PK 획득 때문에 한 줄씩 insert가 나가는 경우가 많다.

### `SEQUENCE`가 왜 훨씬 batch 친화적인가

반면 sequence 기반 전략은 DB insert 전에 ID를 확보할 수 있다. 그러면 Hibernate는 엔티티를 action queue에 모아 뒀다가 flush 시점에 batch insert로 밀어 넣기 훨씬 쉬워진다.

특히 sequence를 쓸 때는 allocation size까지 같이 봐야 한다.

```java
@Id
@GeneratedValue(strategy = GenerationType.SEQUENCE, generator = "product_seq")
@SequenceGenerator(name = "product_seq", sequenceName = "product_seq", allocationSize = 100)
private Long id;
```

`allocationSize`가 너무 작으면 sequence nextval 호출이 과도해져 또 병목이 될 수 있다. 반대로 너무 크게 잡으면 ID 갭이 생길 수 있다. 대부분의 서비스에서는 ID 연속성보다 쓰기 처리량이 중요하므로, **갭을 허용하고 allocation을 늘리는 쪽**이 더 실용적이다.

### 앱 생성 ID도 강력한 대안이다

대량 쓰기 경로에서는 DB 생성 키 대신 다음을 고려할 수 있다.

- UUID v7
- ULID
- Snowflake 계열 ID
- 별도 ID 서비스

장점은 분명하다.

- insert 전에 ID 확보 가능
- JDBC batch에 유리
- 부모-자식 연관관계를 메모리에서 먼저 구성하기 쉬움
- 외부 시스템과 멱등 키를 공유하기도 편함

하지만 단점도 있다.

- 랜덤성이 큰 키는 clustered index locality를 해칠 수 있음
- 문자열 PK는 인덱스/스토리지 비용이 증가할 수 있음
- 팀 전체가 ID 체계와 정렬 특성을 이해해야 함

그래서 내 기준은 이렇다.

- **OLTP 일반 CRUD**: 기존 전략 유지 가능
- **대량 insert 핵심 경로**: `SEQUENCE + allocationSize` 또는 앱 생성 ID를 우선 검토
- **MySQL auto increment에 강하게 묶인 구조**: JPA batch 최적화 기대치를 낮추고 `JdbcTemplate`/bulk loader 대안을 빨리 검토

### 흔한 오해: PK만 받으면 되니 `IDENTITY`여도 batch에 큰 차이 없다

아니다. insert batching에서 ID 전략은 사소한 옵션이 아니라 **실행 시점**을 바꾸는 핵심 조건이다. 엔티티 10만 건을 언제 SQL로 내보낼 수 있느냐는 결국 PK를 언제 알 수 있느냐와 연결된다.

---

## 핵심 개념 3: `flush()`와 `clear()`는 배치에서 선택 옵션이 아니라 메모리·성능·정합성 제어 장치다

조회 중심 코드에서는 `flush()`를 직접 볼 일이 많지 않다. 하지만 대량 쓰기에서는 얘기가 달라진다.

### 영속성 컨텍스트를 방치하면 무슨 일이 생기나

엔티티를 수만 건 persist하거나 수정하면, Hibernate는 이를 영속성 컨텍스트와 action queue 안에 들고 있게 된다. 그러면 시간이 갈수록 비용이 쌓인다.

- managed entity 수 증가
- dirty checking 대상 증가
- 1차 캐시 메모리 사용량 증가
- flush 시점 비교 비용 증가
- GC 압력 증가

즉 배치 작업에서 “한 트랜잭션으로 끝까지 몰아넣기”는 보통 성능과 안정성을 동시에 해친다.

### 기본 패턴: chunk + flush + clear

```java
@Transactional
public void importProducts(List<ProductCommand> commands) {
    int batchSize = 500;

    for (int i = 0; i < commands.size(); i++) {
        entityManager.persist(Product.from(commands.get(i)));

        if ((i + 1) % batchSize == 0) {
            entityManager.flush();
            entityManager.clear();
        }
    }

    entityManager.flush();
    entityManager.clear();
}
```

여기서 의미는 명확하다.

- `flush()`: 지금까지 모은 SQL을 DB로 보낸다
- `clear()`: 이미 처리한 managed entity를 영속성 컨텍스트에서 비운다

둘은 짝으로 생각하는 편이 안전하다.

- `flush()` 없이 `clear()`만 하면 아직 반영되지 않은 변경을 잃을 수 있다
- `clear()` 없이 `flush()`만 하면 메모리와 dirty checking 비용이 계속 남는다

### batch size는 고정 공식이 없다

현실에서는 100, 300, 500, 1000 중 무엇이 맞는지 측정으로 정해야 한다. 영향을 주는 요소가 많기 때문이다.

- row 크기
- 인덱스 수
- FK 존재 여부
- DB log flush 특성
- driver batch 처리 방식
- JVM 힙 크기
- 트랜잭션 timeout

내 경험상 “일단 500 또는 1000으로 시작하고 측정하면서 내리는” 전략이 보통 낫다. 너무 공격적으로 5000, 10000을 넣으면 오히려 다음 문제가 생긴다.

- chunk 하나의 rollback 비용 급증
- 락 보유 시간 증가
- 한 번의 실패가 되돌리는 양이 커짐
- GC spike와 tail latency 악화

### 더 중요한 건 트랜잭션 chunk다

`flush()/clear()`만 하고 트랜잭션을 하나로 계속 유지하면, 메모리는 줄여도 롤백 비용과 락 보유 시간 문제는 여전히 남는다. 그래서 대량 쓰기에서는 보통 **transaction chunk**도 같이 설계해야 한다.

예를 들면 아래처럼 500건 단위로 별도 트랜잭션을 여는 구조가 더 운영 친화적이다.

```java
public void importAll(List<ProductCommand> commands) {
    List<List<ProductCommand>> chunks = Lists.partition(commands, 500);
    for (List<ProductCommand> chunk : chunks) {
        productBatchTxService.importChunk(chunk);
    }
}

@Service
public class ProductBatchTxService {

    @Transactional
    public void importChunk(List<ProductCommand> chunk) {
        for (ProductCommand command : chunk) {
            entityManager.persist(Product.from(command));
        }
        entityManager.flush();
        entityManager.clear();
    }
}
```

이 구조의 장점은 명확하다.

- 실패 범위가 500건으로 제한됨
- 재시작/재처리 지점이 선명함
- 락과 rollback 부담이 줄어듦
- 작업 진행률 추적이 쉬움

즉 배치에서 `flush()/clear()`는 성능용 트릭이 아니라, **작업을 운영 가능한 단위로 자르는 설계 수단**이다.

---

## 핵심 개념 4: `order_inserts`, `order_updates`가 중요한 이유는 “쓰기 순서를 바꾸어 SQL shape를 모으기” 때문이다

많은 팀이 이 옵션을 켜 놓고 왜 효과가 있는지까지는 잘 설명하지 못한다. 핵심은 단순하다.

대량 쓰기에서 batch를 깨는 대표 원인 중 하나는 **entity type이 번갈아 섞이는 것**이다.

예를 들어 이런 로직을 보자.

```java
for (OrderImportRow row : rows) {
    Order order = Order.from(row);
    OrderLine line1 = OrderLine.from(order, row.line1());
    OrderLine line2 = OrderLine.from(order, row.line2());

    entityManager.persist(order);
    entityManager.persist(line1);
    entityManager.persist(line2);
}
```

이 구조는 자연스럽지만 flush 시점 SQL은 대략 이렇게 뒤섞이기 쉽다.

- `insert into orders ...`
- `insert into order_line ...`
- `insert into order_line ...`
- `insert into orders ...`
- `insert into order_line ...`

Hibernate가 action을 정렬하지 않으면 같은 statement가 연속하지 않아 batch 기회를 놓치기 쉽다. `order_inserts=true`는 이런 action을 가능한 한 비슷한 SQL끼리 모아준다.

### 그래도 한계는 있다

이 옵션은 만능이 아니다. 다음 경우에는 여전히 batch 효율이 떨어질 수 있다.

- FK 제약 때문에 완전히 자유롭게 reorder할 수 없음
- 엔티티 타입은 같아도 SQL 컬럼 구성이 달라짐
- secondary table, nullable dynamic column, `@DynamicInsert` 등으로 shape가 흔들림
- cascade persist/update/delete가 복잡하게 섞임

즉 `order_inserts`, `order_updates`는 **shape를 모으는 보조 도구**이지, 나쁜 쓰기 구조를 숨겨 주는 도구가 아니다.

### 실무 팁: 부모/자식 저장도 의도적으로 나누면 더 낫다

엔티티 그래프를 한 번에 cascade persist하는 방식은 코드가 짧아 보이지만, 대량 쓰기에서는 종종 성능과 디버깅을 함께 해친다.

오히려 아래처럼 분리하는 편이 예측 가능할 때가 많다.

1. 부모 엔티티 chunk insert
2. 필요한 ID 확보
3. 자식 엔티티 chunk insert

물론 도메인에 따라 한 트랜잭션 안에서 같이 가야 할 때도 있다. 중요한 건 **객체 그래프 편의성**보다 **SQL batching shape**를 먼저 보는 시선이다.

---

## 핵심 개념 5: update batching은 insert보다 더 까다롭고, `@DynamicUpdate`와 version 컬럼이 자주 발목을 잡는다

insert는 상대적으로 shape가 일정하다. update는 그렇지 않다. 대량 update에서 batch가 잘 안 붙는 이유는 대개 두 가지다.

- 업데이트 대상 컬럼이 row마다 달라진다
- optimistic locking/version 처리 때문에 SQL 결과 검증이 필요하다

### `@DynamicUpdate`는 OLTP에서는 좋을 수 있어도 배치에는 독이 될 수 있다

예를 들어 `@DynamicUpdate`를 쓰면 Hibernate는 변경된 컬럼만 포함한 update SQL을 만들 수 있다. 일반 요청에서 불필요한 column write를 줄이는 데는 장점이 있다.

하지만 대량 배치에서는 문제가 된다.

- row A: `status`, `processed_at`만 변경
- row B: `status`, `processed_at`, `error_message` 변경
- row C: `status`만 변경

그러면 SQL shape가 매번 달라져 batching이 잘 안 된다.

즉 **일반 요청에서의 미세 최적화**가 **배치에서는 statement 분산**으로 돌아올 수 있다.

### version 컬럼과 update count 검증

낙관적 락을 쓰는 엔티티는 update 결과 row count 검증이 중요하다. 배치 update에서는 driver가 batch update count를 어떻게 반환하는지, Hibernate가 이를 어떻게 해석하는지도 같이 봐야 한다.

실무 기준으로는 다음을 체크해야 한다.

- version 컬럼이 있는 엔티티도 batch update 대상인가
- driver가 정확한 update count를 돌려주는가
- optimistic locking 충돌 시 batch 전체/부분 실패를 어떻게 해석할 것인가
- 실패한 chunk 재처리 정책이 있는가

즉 update batching은 단순 성능 이슈가 아니라 **정합성 검증이 끼어드는 쓰기 경로**다.

### 상태 전이 배치에서는 조건부 update가 더 나을 때가 많다

아래처럼 엔티티를 하나씩 로딩해서 상태를 바꾸는 패턴은 직관적이지만, 대량 작업에서는 비효율적일 수 있다.

```java
@Transactional
public void expireCoupons(List<Long> ids) {
    for (Long id : ids) {
        Coupon coupon = couponRepository.findById(id).orElseThrow();
        coupon.expire();
    }
}
```

배치성 상태 전이라면 아래처럼 조건부 bulk SQL이 더 나을 수도 있다.

```sql
update coupon
set status = 'EXPIRED', expired_at = now()
where status = 'ACTIVE'
  and expires_at < now();
```

물론 이렇게 하면 영속성 컨텍스트 우회, 도메인 이벤트 누락, 엔티티 콜백 미실행 같은 trade-off가 생긴다. 그래서 중요한 것은 “JPA 엔티티 변경이냐 bulk SQL이냐”를 종교처럼 고르는 게 아니라, **유즈케이스별로 어느 비용이 더 중요한지 판단하는 것**이다.

---

## 핵심 개념 6: cascade, orphanRemoval, 엔티티 라이프사이클 콜백은 배치에서 종종 보이지 않는 비용 폭탄이 된다

JPA는 관계형 데이터를 객체 그래프로 다루기 편하게 해 준다. 문제는 그 편의가 대량 쓰기에서는 종종 너무 비싸다는 점이다.

### cascade persist/update/delete의 숨은 비용

```java
@OneToMany(mappedBy = "order", cascade = CascadeType.ALL, orphanRemoval = true)
private List<OrderLine> lines = new ArrayList<>();
```

일반 요청에서는 깔끔하다. 하지만 대량 쓰기에서 이런 구조는 다음 문제를 만들기 쉽다.

- 부모 하나당 자식 수가 많아 영속성 컨텍스트가 급격히 커짐
- insert/update/delete SQL이 예측보다 많이 발생함
- orphanRemoval이 diff 계산과 delete를 유발함
- 컬렉션 전체 교체 코드가 delete+insert 폭탄이 되기 쉬움

예를 들어 아래 코드는 아주 위험하다.

```java
order.changeLines(newLines);
```

겉보기에는 “주문 라인 갈아끼우기”지만, 구현에 따라 기존 자식 전부 delete 후 새 자식 전부 insert가 될 수 있다. OLTP 단건 요청이면 괜찮을 때도 있지만, 수천·수만 건 배치에서는 DB와 WAL을 순식간에 터뜨릴 수 있다.

### entity listener / callback도 배치에서는 비용이다

`@PrePersist`, `@PreUpdate`, 도메인 이벤트 발행, 감사 로그 적재 같은 로직이 엔티티 라이프사이클에 묶여 있다면 대량 쓰기 경로에서 예상보다 큰 CPU 비용과 외부 부작용이 생길 수 있다.

- row마다 JSON 직렬화
- row마다 암호화/복호화
- row마다 이벤트 객체 생성
- row마다 로그 남김

대량 쓰기 경로는 보통 **핫패스**다. 여기서는 엔티티 편의보다 **불필요한 부수효과 제거**가 더 중요해질 때가 많다.

### 실무 기준

- 대량 쓰기 경로에는 entity graph 전체 저장보다 **평평한 write model**을 선호
- orphanRemoval은 배치 경로에서 정말 필요한지 다시 점검
- row당 무거운 listener/callback은 분리 가능 여부 검토
- “도메인적으로 아름다운 구조”와 “대량 쓰기 운영 가능성”을 분리해서 판단

---

## 핵심 개념 7: 배치 성능은 ORM 옵션보다 “작업 재개 가능성”까지 포함해 설계해야 진짜 실전이다

대량 쓰기 글이 종종 놓치는 부분이 있다. 바로 **실패 이후 세계**다.

성능만 보고 5만 건을 한 번에 때려 넣는 구조는 개발 환경에서는 빨라 보일 수 있다. 하지만 운영에서는 다음 질문을 피할 수 없다.

- 3만 2천 건 처리 중 1건이 unique constraint에 걸리면 어떻게 할까
- 배치 중간 장애 후 어디서 재개할까
- 이미 처리한 row를 재실행해도 안전한가
- chunk 일부만 commit된 상태를 어떻게 추적할까

즉 대량 쓰기 설계의 핵심은 throughput만이 아니라 **resume, retry, idempotency**다.

### 안전한 배치가 보통 갖는 속성

1. 입력의 순서가 안정적이다
2. chunk 경계가 명확하다
3. 각 chunk의 성공/실패가 기록된다
4. 이미 처리한 항목을 건너뛸 수 있다
5. 재실행해도 중복 부작용이 제한된다

예를 들어 백필 작업이라면 아래 정보가 있으면 훨씬 안전하다.

- 마지막 성공 PK 또는 cursor
- chunk size
- 시작 시각 / 종료 시각
- 성공 건수 / 실패 건수
- 재시도 횟수
- 실패 row 원인

### 트랜잭션을 짧게 끊어야 하는 진짜 이유

짧은 트랜잭션은 단지 DB 락을 줄여서 좋은 것이 아니다. 운영에서는 더 큰 의미가 있다.

- 실패 범위를 작게 제한
- 부분 성공 상태를 설명 가능하게 만듦
- 수동 복구 없이 재시작 가능성 상승
- timeout/rollback 비용 절감

배치 설계를 잘한다는 것은 “JPA batch를 켰다”가 아니라,
**문제가 생겼을 때 사람이 새벽에 봐도 어디까지 성공했고 다음에 무엇을 다시 돌려야 하는지 알 수 있게 만든다**는 뜻에 더 가깝다.

---

## 실무 예시 1: 상품 마이그레이션 insert를 JPA batch로 운영 가능한 구조로 만드는 법

상황을 하나 가정해 보자.

- 외부 공급사 CSV에서 상품 20만 건 적재
- 중복 키는 건너뛰어야 함
- 상품과 상품가격 이력이 함께 저장돼야 함
- 운영 DB는 PostgreSQL
- 일반 요청 트래픽과 같은 시간대에 공존

### 나쁜 예시: 한 메서드에 다 넣기

```java
@Transactional
public void importAll(List<ProductCsvRow> rows) {
    for (ProductCsvRow row : rows) {
        Product product = Product.from(row);
        product.addPriceHistory(PriceHistory.initial(row.price()));
        productRepository.save(product);
    }
}
```

이 구조의 문제는 명확하다.

- 부모/자식 insert가 섞여 SQL shape가 흔들린다
- 20만 건 managed entity가 컨텍스트에 쌓일 수 있다
- 하나 실패하면 전체 롤백 비용이 너무 크다
- 어디까지 성공했는지 추적이 어렵다

### 더 나은 구조

#### 1) 읽기와 검증을 먼저 평탄화

- CSV 파싱
- 필수값 검증
- 중복 natural key 정규화
- 필요한 참조 데이터 prefetch

#### 2) write model을 평평하게 분리

- `ProductInsertRow`
- `PriceHistoryInsertRow`

#### 3) 500건 단위 chunk 트랜잭션

```java
public void importAll(List<ProductInsertRow> rows) {
    for (List<ProductInsertRow> chunk : Lists.partition(rows, 500)) {
        productImportTxService.importChunk(chunk);
    }
}

@Service
public class ProductImportTxService {

    @Transactional
    public void importChunk(List<ProductInsertRow> chunk) {
        for (ProductInsertRow row : chunk) {
            Product product = Product.of(row.id(), row.name(), row.price(), row.status());
            entityManager.persist(product);
        }
        entityManager.flush();
        entityManager.clear();
    }
}
```

#### 4) 가격 이력은 별도 chunk로 저장

도메인 정합성상 같은 트랜잭션이 꼭 필요하다면 같이 묶을 수 있다. 하지만 상품과 가격 이력을 굳이 객체 그래프로 cascade persist해야 하는지는 다시 봐야 한다. row 수가 매우 크다면 아래 중 하나가 더 나을 수 있다.

- 같은 chunk 트랜잭션 안에서 parent 먼저 persist 후 child persist
- child 테이블은 `JdbcTemplate.batchUpdate`로 분리
- 더 크면 PostgreSQL `COPY` 계열 검토

### 관측 포인트

- chunk당 소요 시간
- batch당 DB statement 수
- PostgreSQL `reWriteBatchedInserts` 적용 여부
- JVM 힙 사용량
- unique violation 발생 비율

대량 import에서는 ORM 아름다움보다 **진행률과 재시작 가능성**이 훨씬 중요하다.

---

## 실무 예시 2: 상태 전이 update 배치에서 엔티티 변경과 bulk SQL을 어떻게 고를까

이번에는 주문 상태를 `READY -> EXPIRED`로 넘기는 야간 작업을 보자.

요구사항은 이렇다.

- 만료 대상은 수십만 건
- 주문 만료 시 audit row가 남아야 함
- 주문별 후속 이벤트는 Kafka로 보내야 함
- 중복 만료는 허용하면 안 됨

여기서 많은 팀이 처음에는 엔티티 방식으로 시작한다.

```java
@Transactional
public void expire(List<Long> orderIds) {
    for (Long orderId : orderIds) {
        Order order = orderRepository.findById(orderId).orElseThrow();
        order.expire();
        auditRepository.save(AuditLog.expired(orderId));
    }
}
```

이 구조는 도메인 메서드가 자연스럽지만, 규모가 커지면 문제가 생긴다.

- row별 select + update
- audit insert까지 섞임
- 이벤트 발행 위치에 따라 정합성이 복잡해짐
- dirty checking 비용 증가

### 더 실전적인 접근 1: 대상 식별과 상태 전이를 분리

1. 만료 대상 ID 목록을 작은 page로 조회
2. 각 page를 chunk 단위로 처리
3. 상태 전이는 조건부 update 또는 제한된 엔티티 변경으로 수행
4. audit/outbox는 같은 chunk 트랜잭션 안에서 기록

예를 들어 상태 전이 자체는 조건부 SQL이 더 명확할 수 있다.

```sql
update orders
set status = 'EXPIRED', expired_at = now(), version = version + 1
where id = :id
  and status = 'READY'
  and expires_at < now();
```

영향받은 row가 1이면 성공, 0이면 이미 다른 경로에서 처리됐거나 조건 불일치다. 이 방식의 장점은 다음과 같다.

- 엔티티 로딩 생략 가능
- 동시성 제어가 명시적
- update SQL shape가 일정
- retry/중복 실행 판단이 쉬움

대신 단점도 분명하다.

- 엔티티 메서드/콜백 우회
- 영속성 컨텍스트 일관성 직접 관리 필요
- 도메인 이벤트를 별도 outbox로 처리해야 함

### 더 실전적인 접근 2: 엔티티를 써야 한다면 읽기와 쓰기를 chunk 단위로 끊기

```java
public void expireAll() {
    while (true) {
        List<Long> ids = orderQueryRepository.findExpiredCandidates(1000);
        if (ids.isEmpty()) {
            return;
        }
        orderExpireTxService.expireChunk(ids);
    }
}

@Service
public class OrderExpireTxService {

    @Transactional
    public void expireChunk(List<Long> ids) {
        List<Order> orders = orderRepository.findAllById(ids);
        for (Order order : orders) {
            order.expire();
            outboxRepository.save(OutboxMessage.orderExpired(order.getId()));
        }
        entityManager.flush();
        entityManager.clear();
    }
}
```

이 구조는 pure bulk SQL보다 느릴 수 있지만, 다음이 필요할 때는 충분히 타당하다.

- 엔티티 규칙 재사용
- `@Version` 기반 낙관적 락 유지
- 도메인 메서드 내 검증 로직 유지
- 상태 전이 이벤트를 outbox와 함께 기록

중요한 것은 **“배치니까 무조건 bulk SQL”도 아니고 “JPA니까 무조건 엔티티”도 아니라는 점**이다.

---

## 실무 예시 3: 대규모 backfill에서는 JPA 배치보다 “cursor 설계”가 더 중요하다

backfill은 특히 실수하기 쉽다. 보통 운영 중 테이블에 신규 컬럼이 추가되었거나, 파생 값을 나중에 채우는 작업에서 발생한다.

예를 들어 주문 테이블에 `search_key` 컬럼을 새로 추가했고, 과거 3천만 건에 대해 값을 채워야 한다고 하자.

여기서 가장 위험한 접근은 offset pagination이다.

```sql
select * from orders order by id limit 1000 offset 5000000
```

이 방식은 뒤로 갈수록 느려지고, 중간 변경에도 약하다. backfill에서는 보통 **keyset cursor**가 맞다.

### 추천 구조

1. `last_id` 기준으로 대상 조회
2. 읽기 page와 쓰기 chunk를 분리
3. 각 chunk는 짧은 트랜잭션
4. 성공 후 checkpoint 저장

```java
public void backfill() {
    Long cursor = checkpointRepository.load("order-search-key-backfill");

    while (true) {
        List<OrderSliceRow> rows = orderQueryRepository.findNextSlice(cursor, 1000);
        if (rows.isEmpty()) {
            return;
        }

        orderBackfillTxService.processChunk(rows);
        cursor = rows.get(rows.size() - 1).id();
        checkpointRepository.save("order-search-key-backfill", cursor);
    }
}
```

이 구조에서 중요한 것은 JPA보다도 다음이다.

- checkpoint가 있는가
- 재실행 시 어디서 이어갈 수 있는가
- 이미 채운 row를 건너뛸 수 있는가
- 읽기 쿼리가 PK 순서로 안정적인가

### backfill에서 JPA를 쓸 때의 기준

- row당 도메인 로직이 꽤 있다 → JPA 엔티티 업데이트 고려
- 단순 계산 결과 컬럼 채움 → SQL update 또는 `JdbcTemplate`가 더 낫다
- 수천만 건 + 단순 파생값 → DB native bulk 또는 ETL성 툴이 낫다

Backfill은 ORM 교과서보다 **운영 재개 가능성**이 훨씬 중요하다.

---

## 언제 JPA batch를 유지하고, 언제 `JdbcTemplate`/native bulk로 내려가야 할까

이 질문은 팀 생산성과 운영 성능을 동시에 좌우한다. 내 기준은 아래처럼 나눈다.

### JPA batch를 유지해도 좋은 경우

- 엔티티 규칙과 검증을 재사용해야 한다
- row 수가 많아도 수만~수십만 수준이고 chunk 처리로 충분하다
- 도메인 이벤트/outbox를 엔티티 경계 안에서 관리하는 편이 안전하다
- 여러 테이블 간 정합성을 같은 트랜잭션 안에서 유지해야 한다
- 배치 빈도가 낮고 개발 복잡도를 과도하게 올리고 싶지 않다

### `JdbcTemplate.batchUpdate`가 더 나은 경우

- 쓰기 shape가 매우 단순하다
- 엔티티 로딩/dirty checking 이점이 거의 없다
- insert/update 대상 컬럼이 명확하고 평평하다
- row 수가 크고, 객체 생성 오버헤드도 아깝다
- SQL을 직접 제어해야 한다

### native bulk SQL이 더 나은 경우

- 상태 전이/플래그 변경처럼 set 기반 update가 적합하다
- 조건식으로 원자성을 보장할 수 있다
- 엔티티 콜백/라이프사이클이 꼭 필요하지 않다
- 결과 row count로 성공 판정이 가능하다

### DB 전용 bulk loader가 더 나은 경우

- 수백만~수천만 건 적재
- 파일 기반 적재가 가능하다
- 앱 서버에서 엔티티를 일일이 만들 이유가 없다
- 최대 throughput이 가장 중요하다

예를 들어 PostgreSQL의 `COPY`, MySQL 계열의 `LOAD DATA`, 데이터 웨어하우스 적재 방식은 JPA보다 훨씬 맞는 문제들이 분명히 있다.

즉 좋은 팀은 “ORM을 끝까지 고집하는 팀”이 아니라,
**유즈케이스별로 JPA / JDBC / native bulk / loader를 구분해 쓸 수 있는 팀**이다.

---

## 측정 없이는 거의 항상 착각한다: 배치 최적화에서 꼭 봐야 할 지표

대량 쓰기는 체감으로 판단하면 거의 틀린다. 꼭 수치로 봐야 한다.

### 애플리케이션 레벨

- 전체 처리 건수 / 초당 처리량
- chunk당 시간
- flush 시간
- GC pause / 힙 사용량
- 예외 비율

### ORM 레벨

- 실제 batch statement 개수
- prepared statement 생성 수
- flush 횟수
- 엔티티 insert/update 수
- batch hit ratio 비슷한 체감 지표

Hibernate 통계나 datasource-proxy, p6spy 같은 도구가 여기에 도움이 된다. 단, SQL 로그 전체를 그대로 켜면 배치 성능 실험 자체를 왜곡할 수 있으니 주의해야 한다.

### DB 레벨

- statement per second
- rows inserted/updated per second
- WAL/redo 증가량
- lock wait
- deadlock
- replication lag
- autovacuum 또는 checkpoint pressure

특히 PostgreSQL에서는 대량 update가 WAL과 bloat를 밀어 올릴 수 있고, MySQL/InnoDB에서는 redo/undo와 secondary index maintenance가 병목이 되기 쉽다. 앱만 보고 있으면 반만 보는 셈이다.

### 최적화 실험 순서 예시

1. baseline 측정
2. `batch_size`만 적용
3. `order_inserts` / `order_updates` 적용
4. flush/clear 주기 조정
5. transaction chunk 조정
6. ID 전략 변경 가능성 검토
7. JPA vs `JdbcTemplate` 비교

이 순서를 밟아야 “무엇이 진짜 효과를 냈는지” 알 수 있다.

---

## 트레이드오프: JPA 대량 쓰기는 편의와 제어 사이의 균형 문제다

JPA batch가 매력적인 이유는 분명하다.

### 장점

- 엔티티 규칙과 검증 재사용
- 트랜잭션 경계 안에서 도메인 정합성 유지 용이
- 코드 가독성과 유지보수성 우수
- outbox, audit, 도메인 이벤트를 같은 유즈케이스에서 다루기 쉬움
- 일반 CRUD 코드와 mental model을 공유 가능

### 단점

- 영속성 컨텍스트 메모리 관리 필요
- ID 전략에 크게 영향받음
- SQL shape가 흔들리면 batch 효율 급감
- 대규모 pure bulk 작업에서는 객체 오버헤드가 아까움
- ORM 내부 동작을 이해하지 못하면 디버깅 난이도 상승

### 결국 어떤 기준으로 고를까

나는 보통 아래 순서로 판단한다.

1. 이 작업이 엔티티 규칙 재사용 가치가 큰가
2. set 기반 SQL로 더 명확하게 표현 가능한가
3. row 수와 작업 빈도가 어느 정도인가
4. 실패 재개와 멱등성이 무엇으로 가장 단순해지는가
5. 팀이 현재 운영할 수 있는 복잡도는 어디까지인가

예쁘게 말하면 trade-off고, 현실적으로 말하면 **어디에 복잡도를 둘 것인가**의 문제다.

- JPA 유지 → 애플리케이션 복잡도 낮춤, 성능 튜닝 필요
- JDBC/native → 성능/제어 향상, 애플리케이션 코드가 더 노출됨
- DB loader → 최고 처리량 가능, 파이프라인 구조가 달라짐

---

## 흔한 실수 1: `saveAll()`을 썼으니 batch가 자동 적용됐다고 믿는다

`saveAll()`은 컬렉션을 저장한다는 API일 뿐, JDBC batch를 보장하는 API가 아니다.

아래 조건이 안 맞으면 그냥 save를 여러 번 부르는 것과 큰 차이가 없을 수 있다.

- batch_size 설정 없음
- `IDENTITY` 사용
- SQL shape 분산
- flush 타이밍 부적절
- driver rewrite 미적용

즉 `saveAll()`은 편의 API이지, 성능 계약이 아니다.

---

## 흔한 실수 2: `IDENTITY`를 유지한 채 JPA insert batch 성능을 과하게 기대한다

이건 정말 자주 본다.

- 팀 표준이 `IDENTITY`
- 모든 엔티티가 auto increment
- 대량 insert가 느림
- `hibernate.jdbc.batch_size`만 올림
- 체감 개선 거의 없음

이 경우는 코드보다 **키 생성 시점**이 병목일 가능성이 높다. 대량 쓰기 핵심 경로만이라도 `SEQUENCE`나 앱 생성 ID로 분리할 수 있는지 검토해야 한다.

---

## 흔한 실수 3: `flush()`만 하고 `clear()`를 안 하거나, 반대로 `clear()`만 한다

`flush()`만 계속 호출하면 SQL은 나가도 managed entity는 계속 남는다. 결국 메모리와 dirty checking 비용이 쌓인다.

반대로 `clear()`만 해 버리면 아직 반영되지 않은 변경이 날아갈 수 있다.

배치에서는 둘을 세트로 생각하는 습관이 중요하다.

---

## 흔한 실수 4: 5만 건을 한 트랜잭션으로 처리하고 “원자성”이라고 부른다

그건 대개 원자성보다 **운영 불가능성**에 가깝다.

- 하나 실패 시 전체 rollback 비용 과도
- 락 보유 시간 과도
- timeout 위험 증가
- 실패 후 어디서 재개할지 불명확

정말 전부가 한 번에 성공/실패해야 하는 드문 요구가 아니라면, 보통은 chunk transaction이 더 현실적이다.

---

## 흔한 실수 5: `@DynamicUpdate`를 아무 생각 없이 켜 두고 update batch가 안 붙는 이유를 모른다

일반 요청에서는 변경 컬럼만 update하는 것이 좋아 보인다. 하지만 대량 update에서는 SQL shape 분산으로 batch 효율이 깨질 수 있다.

특히 야간 상태 전이, 마이그레이션, backfill 같은 작업에서는 “statement 수를 줄이기 위해 동적 update를 켰다”가 아니라 “statement 모양을 고르게 만들어 batch를 키운다”가 더 중요할 때가 많다.

---

## 흔한 실수 6: 연관 엔티티 전체를 갈아끼우는 코드가 delete/insert 폭탄이라는 사실을 모른다

배치에서 컬렉션 교체는 매우 위험하다.

- orphanRemoval이 켜져 있음
- 기존 자식 전부 제거
- 새 자식 전부 persist
- 결과적으로 엄청난 delete + insert 발생

단건 화면 저장에서는 문제 없던 코드가 배치에서만 터지는 대표 패턴이다.

---

## 흔한 실수 7: 성능 테스트 없이 운영 시간대에 바로 돌린다

대량 쓰기는 테스트 데이터와 운영 데이터 분포 차이에 매우 민감하다.

- 인덱스 수
- FK 구성
- 기존 table bloat
- replica lag
- autovacuum pressure
- 동시 요청 트래픽

개발 환경에서 빨랐다는 말은 운영에서 거의 의미가 없다. 최소한 staging 또는 운영과 가까운 데이터 분포에서 chunk 크기, DB 부하, 롤백 시나리오를 확인해야 한다.

---

## 흔한 실수 8: 이벤트 발행을 배치 row마다 즉시 외부로 보낸다

배치 update나 insert 후 외부 MQ/Kafka/HTTP를 row마다 바로 호출하면 다음 문제가 생긴다.

- 트랜잭션 커밋 전 외부 부작용 발생
- 실패 시 중복 발행/누락 복구가 어려움
- 처리량 급감
- downstream rate limit 초과

대량 쓰기에서는 특히 **outbox**가 잘 맞는다.

- DB write와 outbox insert를 같은 트랜잭션에 둔다
- 별도 발행기가 비동기로 전송한다
- 재시도와 관측이 쉬워진다

---

## 실무 체크리스트: JPA 대량 쓰기 PR을 리뷰할 때 꼭 보는 항목

### 1) ID 전략

- [ ] `IDENTITY`가 batch insert를 구조적으로 막고 있지 않은가
- [ ] `SEQUENCE`라면 allocation size가 너무 작지 않은가
- [ ] 앱 생성 ID가 더 단순한 대안은 아닌가

### 2) batching 설정

- [ ] `hibernate.jdbc.batch_size`가 설정되어 있는가
- [ ] `order_inserts`, `order_updates`가 필요한 경로인가
- [ ] JDBC driver batch rewrite 옵션까지 점검했는가

### 3) 영속성 컨텍스트

- [ ] chunk마다 `flush()` / `clear()`가 있는가
- [ ] managed entity 수가 무한히 늘어나지 않는가
- [ ] read-after-write가 필요한 경로와 clear 타이밍이 충돌하지 않는가

### 4) 트랜잭션 경계

- [ ] 한 트랜잭션이 지나치게 길지 않은가
- [ ] 실패 범위가 chunk 수준으로 제한되는가
- [ ] timeout, lock hold time, rollback cost를 고려했는가

### 5) SQL shape

- [ ] insert/update SQL이 충분히 균질한가
- [ ] `@DynamicUpdate`, cascade, orphanRemoval이 batch를 깨지 않는가
- [ ] 여러 엔티티 타입이 번갈아 섞여 있지 않은가

### 6) 정합성·운영성

- [ ] optimistic locking/version 충돌 전략이 있는가
- [ ] 재시작 checkpoint가 있는가
- [ ] 멱등성이 보장되거나 중복 실행 정책이 있는가
- [ ] 성공/실패 건수와 마지막 cursor를 추적하는가

### 7) 대안 비교

- [ ] 이 경로는 정말 JPA 엔티티가 필요한가
- [ ] `JdbcTemplate.batchUpdate`가 더 단순하지 않은가
- [ ] bulk SQL 또는 DB loader가 더 맞는 문제는 아닌가

### 8) 관측 가능성

- [ ] chunk당 처리 시간, rows/sec, DB 부하를 볼 수 있는가
- [ ] batch가 실제로 묶였는지 확인 가능한가
- [ ] 실패 row와 원인을 추적 가능한가

이 체크리스트를 통과하지 못하면, “코드는 돌아간다”와 “운영 가능하다” 사이 거리가 꽤 멀다.

---

## 상황별 빠른 판단 가이드

### 상황 1: 1만~10만 건 수준의 insert, 엔티티 규칙 재사용 필요

**추천**

- JPA 유지
- `SEQUENCE` 또는 앱 생성 ID
- batch_size + order_inserts
- 300~1000 단위 chunk + flush/clear

### 상황 2: 상태 플래그 대량 전이, 도메인 규칙보다 처리량 우선

**추천**

- 조건부 bulk update 우선 검토
- 필요하면 outbox 별도 적재
- 영속성 컨텍스트 stale state 주의

### 상황 3: 수백만 건 이상 단순 적재

**추천**

- `JdbcTemplate.batchUpdate` 또는 DB 전용 bulk loader 우선
- JPA 엔티티 생성 오버헤드 최소화

### 상황 4: 운영 중 backfill, 실패 재개가 가장 중요

**추천**

- keyset cursor
- checkpoint 저장
- 짧은 chunk transaction
- 이미 처리한 row skip 전략

### 상황 5: 부모-자식 그래프 전체를 저장해야 함

**추천**

- cascade를 당연시하지 말고 SQL shape부터 확인
- 부모/자식 저장을 단계적으로 분리할 수 있는지 검토
- PK 전략과 flush 순서를 함께 설계

---

## 마무리: 대량 쓰기에서 중요한 것은 ORM을 믿는 태도가 아니라, 어디까지 ORM에 맡길지 정확히 아는 태도다

JPA는 일반적인 업무 개발 생산성을 크게 올려 준다. 문제는 그 편의 모델을 그대로 대량 쓰기에 가져가면서도, 내부 동작은 여전히 단건 CRUD처럼 상상한다는 데 있다.

하지만 대량 쓰기의 현실은 훨씬 물리적이다.

- statement가 몇 개 나가는가
- 같은 SQL이 얼마나 연속하는가
- PK를 언제 아는가
- 영속성 컨텍스트가 얼마나 커지는가
- 트랜잭션을 어디서 끊는가
- 실패했을 때 어디서 다시 시작하는가

이 관점을 갖추면 선택이 선명해진다.

- JPA batch로 충분한 작업은 더 안정적으로 만들 수 있다
- JPA가 불리한 작업은 빨리 JDBC/native bulk로 우회할 수 있다
- 성능 문제를 “JPA라서” 같은 뭉뚱그린 설명 대신 구체적 병목으로 나눌 수 있다

결국 대량 쓰기 최적화는 ORM 옵션 튜닝 대회가 아니다.

**애플리케이션 모델, SQL shape, 트랜잭션 경계, 운영 복구 모델을 함께 설계하는 일**이다.

---

## 한 줄 정리

JPA 대량 쓰기의 핵심은 `saveAll()`이 아니라, **ID 생성 전략·SQL shape·flush/clear 주기·chunk 트랜잭션을 batch 친화적으로 맞추고, 그 한계를 넘는 순간엔 과감하게 JDBC/native bulk로 내려가는 판단력**이다.
