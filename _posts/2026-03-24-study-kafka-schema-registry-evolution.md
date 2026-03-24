---
layout: post
title: "Kafka Schema Registry 실전: Avro/Protobuf 스키마 진화와 호환성 운영 기준"
date: 2026-03-24 11:40:00 +0900
categories: [data-infra]
tags: [study, data-infra, kafka, schema-registry, avro, protobuf, json-schema, event-driven, streaming]
---

## 배경: 이벤트는 코드보다 오래 살아남고, 그래서 스키마가 사고를 만든다

Kafka를 운영하는 팀이 어느 시점에서 반드시 맞닥뜨리는 순간이 있다. 처음에는 단순하다. 주문 이벤트 하나, 결제 이벤트 하나, 컨슈머 몇 개만 붙이면 된다. 그런데 서비스 수가 늘고 팀이 분리되기 시작하면 문제가 바뀐다.

- producer는 필드를 "그냥 하나 추가"했다고 생각한다
- consumer는 그 필드가 없거나 타입이 달라서 역직렬화에 실패한다
- 어떤 팀은 같은 토픽에 다른 이벤트 타입을 섞고 싶어 한다
- 어떤 팀은 과거 메시지를 처음부터 다시 읽어야 한다
- 어떤 팀은 DB 컬럼명 그대로 외부 계약으로 새어 나간 것을 뒤늦게 후회한다

이 단계부터는 Kafka 자체보다 **이벤트 계약(contract)을 어떻게 버전 관리하고 검증할 것인가**가 더 중요해진다. Schema Registry는 보통 "Avro 쓸 때 필요한 부가 도구" 정도로 오해되지만, 실무에서의 역할은 그보다 훨씬 크다.

> Schema Registry의 본질은 직렬화 편의 기능이 아니라, producer와 consumer 사이에 강제 가능한 계약 검증 계층을 두는 것이다.

이걸 놓치면 메시지는 발행되지만 시스템은 점점 더 위험해진다. 반대로 이 계층을 제대로 두면, 이벤트 기반 아키텍처에서 가장 흔한 사고인 **배포 순서 꼬임, 재처리 실패, 필드 변경 충돌, 다팀 간 계약 드리프트**를 크게 줄일 수 있다.

오늘 글은 Kafka + Schema Registry를 "붙이는 법"이 아니라, **운영 환경에서 스키마 진화를 어떻게 통제해야 덜 망가지는가**를 기준 중심으로 정리한다. 특히 Avro, Protobuf, JSON Schema를 모두 고려하면서 다음 질문에 답하는 것이 목표다.

- 어떤 포맷을 골라야 하는가?
- compatibility mode는 무엇을 기준으로 정해야 하는가?
- subject naming 전략은 토픽 구조와 어떻게 연결되는가?
- 배포 순서와 재처리 요구가 스키마 설계를 어떻게 바꾸는가?
- 흔한 안티패턴은 무엇이고, 운영 체크리스트는 무엇인가?

---

## 먼저 큰 그림: Schema Registry는 "스키마 저장소"가 아니라 계약 운영 레이어다

Schema Registry를 도입하면 흔히 아래 흐름이 만들어진다.

1. producer가 특정 subject에 연결된 schema로 메시지를 직렬화한다
2. serializer는 schema를 registry에 등록하거나 이미 등록된 schema id를 조회한다
3. 메시지에는 보통 schema id가 함께 실리고
4. consumer는 해당 id로 schema를 찾아 역직렬화한다
5. 새로운 schema 등록 시 registry가 compatibility rule을 검사한다

여기서 중요한 것은 5번이다. 실제 운영 가치의 대부분이 여기서 나온다.

Kafka만 있을 때는 계약 충돌이 배포 후 런타임에 터진다. 하지만 registry를 두면 **배포 전에 "이 변경은 이전 계약과 양립 가능한가"를 중앙에서 차단**할 수 있다. 즉, 장애를 애플리케이션 로그에서 발견하는 대신 등록 단계에서 미리 끊어낼 수 있다.

이 차이는 생각보다 크다.

- 애플리케이션 레벨 예외는 이미 운영 메시지가 흘러간 뒤에 터진다
- registry 레벨 거부는 생산 단계에서 막는다
- 로컬 팀의 "사소한 필드 추가"가 전체 소비자 장애로 번지는 일을 줄인다
- 재처리 가능한 계약인지, 한 번 깨지면 복구가 어려운 계약인지 사전에 드러난다

즉 Schema Registry는 단순 serializer의 부속물이 아니라, **이벤트 계약 CI/CD의 게이트**에 가깝다.

---

## 핵심 개념 1: schema id, version, subject를 분리해서 이해해야 한다

Schema Registry를 처음 쓰는 팀이 자주 헷갈리는 것이 `schema id`, `version`, `subject`의 역할이다. 이 셋을 섞어서 이해하면 운영 판단이 흐려진다.

### subject

보통 호환성 검사를 적용하는 단위다. 예를 들어 `orders-value`, `payments-value`, 혹은 `orders-com.myapp.events.OrderCreated` 같은 이름이 subject가 될 수 있다.

실무적으로 subject는 단순 이름이 아니라 다음을 결정한다.

- 어떤 변경 이력이 같은 계보(lineage)로 묶이는가
- compatibility rule을 어디에 적용하는가
- 여러 이벤트 타입을 하나의 토픽에 넣을 때 경계를 어떻게 둘 것인가

### version

특정 subject 안에서의 순번이다. `v1`, `v2`, `v3`처럼 보이는 논리 버전이다. 새 스키마가 호환성 검사를 통과하면 version이 증가한다.

### schema id

실제 직렬화/역직렬화 시 참조되는 식별자다. 보통 전역적으로 고유하다. 메시지 페이로드에는 일반적으로 이 id가 실리고, consumer는 이 id를 기준으로 캐시 또는 registry 조회를 수행한다.

이 차이를 이해하면 다음이 명확해진다.

- **version은 변경 이력 관리용**이다
- **schema id는 런타임 해석용**이다
- **subject는 정책 적용 경계**다

실무에서 가장 중요한 것은 version보다 subject다. 왜냐하면 사고는 대개 "이번 스키마가 몇 번째인가"보다 **"어떤 변경들이 같은 호환성 규칙 아래 관리되고 있는가"**에서 발생하기 때문이다.

---

## 핵심 개념 2: compatibility는 단순 옵션이 아니라 배포 전략과 재처리 정책의 표현이다

Confluent 계열 Schema Registry에서 자주 보는 compatibility mode는 대략 아래처럼 이해하면 된다.

- `BACKWARD`: 새 consumer가 이전 schema로 생산된 데이터를 읽을 수 있어야 함
- `BACKWARD_TRANSITIVE`: 새 consumer가 모든 이전 버전 데이터를 읽을 수 있어야 함
- `FORWARD`: 이전 consumer가 새 schema로 생산된 데이터를 읽을 수 있어야 함
- `FORWARD_TRANSITIVE`: 이전 consumer가 모든 미래 버전까지 견딜 수 있어야 함
- `FULL`: backward + forward를 동시에 만족
- `FULL_TRANSITIVE`: 전체 이력에 대해 양방향 호환
- `NONE`: 검사를 하지 않음

여기서 핵심은 "무엇이 더 엄격한가"보다 **우리 팀의 배포/복구 방식과 맞는가**다.

### 왜 많은 팀이 BACKWARD 계열로 시작하는가

이벤트 스트리밍 시스템에서는 새 consumer를 배포한 뒤, 과거 메시지를 처음부터 다시 읽는 요구가 자주 생긴다.

- 신규 서비스가 토픽을 처음 구독한다
- 장애 복구를 위해 오프셋을 rewind 한다
- 배치 재구축이나 재색인을 위해 historical replay를 수행한다
- state store 또는 materialized view를 다시 만든다

이때 새 consumer는 과거 메시지를 읽어야 하므로, 보통 **새 consumer가 이전 데이터와 호환**되어야 한다. 그래서 실무에서는 `BACKWARD` 또는 `BACKWARD_TRANSITIVE`가 기본 후보가 되는 경우가 많다.

### BACKWARD와 BACKWARD_TRANSITIVE의 차이를 얕게 보면 안 된다

`BACKWARD`는 직전 버전과의 호환만 보장한다. 버전이 길게 누적된 토픽에서 신규 consumer가 아주 오래된 메시지까지 읽어야 한다면 이건 부족할 수 있다.

예를 들어,

- `v1 -> v2 -> v3 -> v4`로 진화했고
- registry 설정이 단순 `BACKWARD`이며
- 각 단계는 직전 버전과만 호환된다면
- `v4` consumer가 `v1` 메시지를 항상 안전하게 읽는다고 장담할 수 없다

이런 토픽은 `BACKWARD_TRANSITIVE`를 더 진지하게 고려해야 한다. 특히 아래 조건이 있으면 거의 필수에 가깝다.

- 토픽 보존 기간이 길다
- 신규 소비자가 과거 데이터를 자주 재생한다
- 배포 순서를 중앙 통제하기 어렵다
- 외부 팀 소비자가 많다

### FORWARD와 FULL은 언제 보는가

`FORWARD`는 기존 consumer가 새 producer가 만든 메시지를 읽을 수 있어야 한다는 뜻이다. 즉 producer를 먼저 올려도 구버전 consumer가 버텨야 하는 환경에 가깝다.

문제는 대부분의 팀이 이 전략을 일관되게 운영하지 못한다는 점이다. 미래 필드를 미리 예측해야 하는 경우가 많고, 포맷별 제약도 커진다. 그래서 특별한 이유가 없다면 기본값처럼 쓰기 어렵다.

`FULL`은 양방향 호환을 모두 보려는 선택이지만, 모든 subject에 무조건 걸어두면 팀 생산성이 과도하게 떨어질 수 있다. 특히 이벤트 계약이 정말로 양방향 호환이 필요한지부터 따져야 한다.

### NONE은 빠른 것이 아니라 위험을 나중으로 미루는 것이다

초기에 `NONE`으로 시작하면 스키마 등록은 편해 보인다. 하지만 그 순간부터 검증 비용은 런타임 장애와 다운스트림 복구 비용으로 이전된다. PoC 단계가 아니라면 `NONE`은 편의가 아니라 **장애를 지연시키는 설정**에 가깝다.

---

## 핵심 개념 3: 포맷 선택은 취향이 아니라 조직의 계약 성숙도와 언어 생태계에 달려 있다

Avro, Protobuf, JSON Schema는 모두 쓸 수 있지만, 잘 맞는 문제는 다르다.

### 1) Avro

Avro는 데이터 플랫폼과 이벤트 스트리밍에서 여전히 가장 무난한 기본값이다.

강점은 다음과 같다.

- 스키마 진화 규칙이 비교적 명확하다
- default value 기반의 backward 설계가 익숙하다
- JVM, Python, Connect 생태계에서 자료가 많다
- 레코드 중심 이벤트 계약에 잘 맞는다

주의할 점도 분명하다.

- nullable을 union으로 표현하는 방식이 초보자에게 직관적이지 않다
- field rename은 단순 추가/삭제보다 더 신중해야 한다
- 논리 타입(decimal, timestamp 등) 사용 규칙을 팀 내에서 고정하지 않으면 소비자 구현이 흔들린다

### 2) Protobuf

Protobuf는 gRPC나 polyglot 환경, 모바일/백엔드 공용 계약이 이미 protobuf 중심인 조직에서 강하다.

강점은 다음과 같다.

- IDL 기반 계약이 명확하다
- 다국어 코드 생성 경험이 좋다
- 네트워크/백엔드 계약을 통합 관리하기 쉽다
- 메시지 타입 체계가 명시적이다

하지만 진화 규칙은 Avro보다 실수 여지가 있다.

- field number는 wire contract이므로 함부로 재사용하면 안 된다
- 삭제한 필드 번호와 이름은 `reserved`로 남겨야 사고를 줄일 수 있다
- `oneof`, enum 확장, nested message 분리 시 호환성 함정을 이해해야 한다
- 여러 팀이 protobuf를 잘 안다고 착각하면 오히려 더 위험하다

특히 Protobuf에서 "필드 이름만 바꿨으니 안전하겠지"라는 감각은 위험하다. 사람이 보는 이름보다 **wire format에서 field number가 더 본질적**이기 때문이다.

### 3) JSON Schema

JSON Schema는 사람에게 친숙하고 디버깅이 편하다. 프론트엔드/백엔드/외부 API 문맥과 가까워서 진입장벽도 낮다.

하지만 운영 계약 관점에서는 더 엄격한 통제가 필요하다.

- 허용 범위가 너무 넓어지기 쉽다
- `additionalProperties`, `required`, enum, nullable 규칙을 느슨하게 두면 계약 드리프트가 빠르게 생긴다
- "JSON이니까 대충 읽히겠지"라는 조직 문화와 결합하면 registry를 둔 의미가 약해진다

정리하면,

- **데이터 인프라/이벤트 스트리밍 기본값**으로는 Avro가 가장 무난하고
- **gRPC/다국어 코드 생성 중심 조직**이면 Protobuf가 강력하며
- **외부 JSON 생태계와의 접점이 크되 엄격한 거버넌스를 유지할 자신이 있을 때** JSON Schema를 고려할 만하다

포맷 선택에서 더 중요한 것은 우열이 아니라 **하나의 포맷을 골랐을 때 팀이 진화 규칙을 일관되게 이해하고 리뷰할 수 있는가**다.

---

## 핵심 개념 4: subject naming strategy는 토픽 구조와 소비 모델을 사실상 결정한다

Schema Registry를 도입해도 subject naming을 대충 정하면 다시 혼란으로 돌아간다. 흔히 보는 전략은 세 가지다.

### TopicNameStrategy

보통 `<topic>-value` 형태로 subject를 잡는다.

이 전략의 의미는 명확하다.

- 한 토픽의 value는 같은 스키마 계보로 관리한다
- 토픽 단위로 강한 계약을 적용한다
- 운영자가 이해하기 쉽다

잘 맞는 경우:

- 토픽당 이벤트 타입을 하나의 도메인 흐름으로 유지할 때
- 여러 타입을 섞기보다 topic 분리를 선호할 때
- 거버넌스를 단순하게 가져가고 싶을 때

단점:

- 하나의 토픽에 여러 이벤트 타입을 자연스럽게 넣기 어렵다
- topic 설계가 세분화될수록 subject 수도 늘어난다

### RecordNameStrategy

레코드 이름 기준으로 subject를 만든다. Avro라면 보통 fully-qualified record name, Protobuf라면 message name이 기준이 된다.

장점:

- 같은 이벤트 타입을 여러 토픽에서 재사용하기 좋다
- topic보다 이벤트 타입 중심으로 계약을 관리할 수 있다

단점:

- 같은 레코드가 여러 토픽에서 쓰일 때 topic별 제약을 강제하기 어렵다
- 운영자가 "이 subject가 어느 토픽과 실제로 연결되는가"를 추적하기 어려워질 수 있다
- 무심코 같은 record name을 재사용하면 의도치 않은 결합이 생긴다

### TopicRecordNameStrategy

토픽과 레코드 이름을 함께 묶는 절충안이다.

장점:

- 한 토픽 안에 여러 이벤트 타입을 둘 수 있다
- 동시에 topic boundary도 유지한다

단점:

- naming이 길어지고 운영 복잡도가 올라간다
- 설계 원칙이 없는 팀에서는 오히려 더 헷갈린다

### 실무 판단 기준

subject naming은 serializer 옵션이 아니라 **토픽 철학의 선언**이다. 아래 기준으로 보면 판단이 쉬워진다.

- 토픽당 이벤트 타입 하나를 강하게 유지하고 싶다 → `TopicNameStrategy`
- 이벤트 타입 재사용이 핵심이고 팀이 subject governance에 익숙하다 → `RecordNameStrategy`
- 하나의 토픽에 복수 이벤트 타입을 넣되 topic 제약도 유지하고 싶다 → `TopicRecordNameStrategy`

대부분의 팀은 처음부터 멋있어 보이는 유연성보다, **TopicNameStrategy + 토픽 분리 원칙**으로 시작하는 편이 더 안전하다. 여러 이벤트를 한 토픽에 섞는 구조는 생각보다 빨리 복잡해진다.

---

## 핵심 개념 5: 스키마 진화는 필드 추가 기술이 아니라 배포 순서 설계다

스키마 변경은 코드 diff가 아니라 배포 이벤트다. 그래서 아래 순서를 기준으로 생각해야 한다.

### 소비자 우선(consumer-first) 배포

가장 흔한 안전 전략이다.

1. 새 필드를 읽을 수 있고, 없어도 동작하는 consumer를 먼저 배포
2. 이후 producer가 새 필드를 채워 보내기 시작

이 전략은 대체로 backward 계열과 잘 맞는다. 핵심은 새 필드를 **optional + default 또는 안전한 fallback**으로 설계하는 것이다.

### 생산자 우선(producer-first) 배포

구버전 consumer가 새 메시지도 읽어야 한다. forward 계열이 필요하거나, 소비자 구현이 unknown field를 무시하도록 매우 잘 설계돼 있어야 한다.

문제는 많은 조직이 이 전략을 말로만 유지한다는 점이다. 실제로는 일부 consumer가 엄격한 역직렬화에 묶여 있거나, nullable 처리/enum 확장 로직이 제각각이라 사고가 난다.

### 재처리(replay) 요구가 있으면 더 보수적으로 가야 한다

운영 토픽은 "지금 시점의 producer와 consumer"만 맞으면 끝이 아니다. 정말 어려운 순간은 아래다.

- 신규 서비스가 6개월 치 토픽을 처음부터 읽는다
- 장애 후 오프셋을 일주일 전으로 돌린다
- 분석/색인 시스템을 다시 구축한다
- compacted topic에서 마지막 값만이 아니라 과거 의미도 재해석해야 한다

이때 드러나는 것이 진짜 호환성이다. 평소엔 멀쩡해 보여도 replay 순간 깨지는 스키마가 생각보다 많다. 그래서 "현재 배포만 통과"가 아니라 **재생 가능한 계약인가**를 기준으로 설계해야 한다.

---

## 실무 예시: 주문 이벤트를 장기 운영 가능한 계약으로 바꾸기

아래는 전형적인 주문 생성 이벤트다. 처음에는 매우 단순하다.

### Avro v1

```json
{
  "type": "record",
  "name": "OrderCreated",
  "namespace": "com.example.events.order",
  "fields": [
    { "name": "event_id", "type": "string" },
    { "name": "order_id", "type": "string" },
    { "name": "user_id", "type": "string" },
    { "name": "created_at", "type": { "type": "long", "logicalType": "timestamp-millis" } }
  ]
}
```

이 상태에서는 결제 수단, 채널, 통화 같은 정보가 아직 없다. 시간이 지나면서 producer 팀은 필드를 추가하고 싶어진다.

### Avro v2: 안전한 필드 추가

```json
{
  "type": "record",
  "name": "OrderCreated",
  "namespace": "com.example.events.order",
  "fields": [
    { "name": "event_id", "type": "string" },
    { "name": "order_id", "type": "string" },
    { "name": "user_id", "type": "string" },
    { "name": "created_at", "type": { "type": "long", "logicalType": "timestamp-millis" } },
    { "name": "payment_method", "type": ["null", "string"], "default": null },
    { "name": "currency", "type": "string", "default": "KRW" }
  ]
}
```

이 변경이 비교적 안전한 이유는 다음과 같다.

- `payment_method`는 optional로 추가됐다
- `currency`는 default가 있다
- 새 consumer는 과거 메시지를 읽을 때 누락 필드를 default로 해석할 수 있다

즉 consumer-first 배포와 replay 요구를 고려한 진화다.

### 잘못된 v2 예시: required field를 기본값 없이 추가

```json
{ "name": "currency", "type": "string" }
```

겉보기엔 단순하지만, 과거 메시지에는 이 필드가 없다. backward 소비가 필요한 환경에서 이런 변경은 바로 지뢰가 된다.

### v3에서 흔히 발생하는 실수: 의미 없는 rename

producer 팀은 `user_id`를 `customer_id`로 바꾸고 싶어 할 수 있다. 문제는 스키마 관점에서 rename은 단순 cosmetic change가 아니라 계약 변경이라는 점이다.

- 구버전 consumer는 `customer_id`를 모른다
- 신버전 consumer가 과거 데이터를 읽을 때 alias/fallback 전략이 필요할 수 있다
- 저장소와 분석 파이프라인 전체에서 컬럼 의미가 바뀌는지 검토해야 한다

이럴 때는 실제 rename을 서두르기보다,

1. `customer_id`를 새 필드로 추가하고
2. 일정 기간 두 필드를 병행하며
3. 다운스트림 전환이 끝난 뒤
4. deprecation 절차를 거쳐 제거하는 편이 안전하다

즉, 스키마 진화는 코드 정리보다 **호환 기간을 운영하는 작업**에 가깝다.

### subject compatibility 설정 예시

운영 토픽을 장기 replay해야 한다면 subject 단위로 보수적인 정책을 두는 편이 낫다.

```bash
curl -X PUT http://schema-registry:8081/config/orders-value \
  -H 'Content-Type: application/json' \
  -d '{"compatibility":"BACKWARD_TRANSITIVE"}'
```

이 설정의 의미는 단순히 "엄격하게 하자"가 아니다. **새 consumer가 과거 주문 이벤트 전체를 다시 읽을 수 있어야 한다**는 운영 요구를 정책으로 고정하는 것이다.

### producer/consumer 설정에서 봐야 할 포인트

애플리케이션에서 serializer/deserializer를 붙이는 것 자체는 어렵지 않다. 실무 포인트는 그보다 아래다.

- `auto.register.schemas=true`를 무조건 켜둘 것인가
- CI 단계에서 schema 등록 검사를 먼저 수행할 것인가
- 운영에서 schema 등록 권한을 producer 애플리케이션에 직접 줄 것인가
- 실패 시 앱이 바로 죽게 둘지, fallback 없이 hard fail 시킬지

많은 팀이 로컬 개발 편의 때문에 auto-registration을 켜고 시작한 뒤, 운영에서도 그대로 둔다. 하지만 운영에서는 일반적으로 다음이 더 안전하다.

- 개발/스테이징에서는 auto-registration 허용 가능
- 운영에서는 CI 또는 배포 파이프라인에서 사전 등록/검증
- 애플리케이션 런타임은 등록보다 조회 중심

그래야 계약 변경이 애플리케이션 배포 중 부수적으로 일어나는 것이 아니라, **검토 가능한 변경 이벤트**로 승격된다.

---

## 포맷별 실무 포인트: Avro/Protobuf/JSON Schema에서 자주 갈리는 지점

### Avro에서 기억할 것

- 새 필드는 가능한 optional 또는 default와 함께 추가한다
- nullable 표현을 팀 규칙으로 통일한다
- logical type 사용 규칙(예: timestamp-millis, decimal)을 문서화한다
- field 삭제는 다운스트림 replay 요구를 먼저 확인한다

Avro는 규칙이 비교적 명확해서 운영이 수월하지만, 그만큼 팀이 "default를 왜 넣는지"를 이해하지 못하면 형식적인 복붙만 남는다.

### Protobuf에서 기억할 것

- field number는 절대 가볍게 다루지 않는다
- 삭제한 필드 번호와 이름은 `reserved` 처리한다
- enum 값 추가가 소비자 로직에 미치는 영향을 점검한다
- `oneof` 확장은 직렬화/역직렬화 경계에서 신중히 검토한다

특히 protobuf 경험이 있는 팀일수록 오히려 위험한 이유가 있다. RPC 계약 감각으로 이벤트 계약도 같은 방식으로 바꿀 수 있다고 착각하기 쉽기 때문이다. 하지만 이벤트는 오래 보존되고, 과거 데이터를 재생하며, 여러 세대의 consumer가 동시에 존재한다. 운영 조건이 더 거칠다.

### JSON Schema에서 기억할 것

- `additionalProperties`를 어디까지 허용할지 명확히 정한다
- required 필드 변화에 대한 리뷰 기준을 고정한다
- 자유로운 JSON payload가 아니라 계약 기반 payload라는 문화를 만든다
- 스키마만 있지 실제 런타임 검증이 느슨한 상황을 경계한다

JSON Schema는 빠르게 확장되는 조직에서 유혹적이지만, 아무 규칙 없이 쓰면 schema registry가 있어도 결국 "JSON blob에 문서만 하나 더 붙은 상태"가 되기 쉽다.

---

## 트레이드오프: Schema Registry는 사고를 줄이지만, 개발 속도와 구조 선택에 비용을 만든다

좋은 설계는 늘 비용을 동반한다. Schema Registry도 마찬가지다.

### 장점

- 계약 변경을 중앙에서 검증할 수 있다
- replay 가능성과 배포 순서를 정책으로 표현할 수 있다
- 다팀 환경에서 이벤트 드리프트를 줄인다
- serializer/deserializer 생태계를 활용해 표준화하기 좋다
- 문서보다 강한 실행 가능한 계약을 만들 수 있다

### 비용

- 중앙 의존성이 생긴다
- 포맷별 진화 규칙을 팀이 학습해야 한다
- subject naming을 잘못 고르면 되돌리기 어렵다
- 지나치게 엄격한 정책은 초기 실험 속도를 떨어뜨린다
- 여러 이벤트 타입을 한 토픽에 넣고 싶을 때 설계 복잡도가 급증한다

### 결국 무엇을 최적화할 것인가

아키텍처 선택은 늘 최적화 목표의 문제다.

- 속도를 최우선으로 하면 초기에 registry 없이도 갈 수 있다
- 하지만 조직이 커지고 소비자가 늘어날수록 복구 비용이 폭증한다
- 반대로 처음부터 모든 토픽에 `FULL_TRANSITIVE`를 걸면 팀이 schema 자체를 무서워하게 된다

그래서 실무에서는 보통 이렇게 간다.

- 핵심 도메인 이벤트 토픽부터 registry 강제
- replay/장기보존 토픽은 `BACKWARD_TRANSITIVE` 우선 검토
- 단기 내부 파이프라인은 더 단순한 정책 허용 가능
- subject naming은 초기에 보수적으로 고정

즉, **모든 토픽에 동일한 엄격함**보다 **토픽의 수명과 소비 패턴에 따른 차등 정책**이 더 현실적이다.

---

## 흔한 실수: 대부분은 기술 부족보다 계약 감각 부족에서 나온다

### 1) 스키마를 DTO 정도로만 본다

이벤트 스키마는 내부 코드 구조체가 아니다. 여러 서비스와 여러 시점의 데이터를 이어주는 외부 계약이다. DTO 이름 바꾸듯 필드명을 바꾸면 안 되는 이유가 여기에 있다.

### 2) compatibility mode를 의미 없이 전역 기본값으로 둔다

모든 subject에 동일한 compatibility를 복사해 두고 왜 그런지 아무도 모르는 상태가 흔하다. subject마다 replay 여부, 소비자 수, 배포 통제 수준이 다르면 정책도 달라져야 한다.

### 3) auto-registration을 운영 편의로 남발한다

런타임에 producer가 처음 보는 schema를 곧바로 등록하도록 두면, 계약 변경이 코드 배포의 부수 효과로 숨어버린다. 운영에서는 계약 변경을 의식적으로 드러내는 편이 낫다.

### 4) 하나의 토픽에 너무 많은 이벤트 타입을 섞는다

"토픽 수를 줄이자"는 이유로 여러 이벤트를 합치기 시작하면 subject naming, consumer 분기, ACL, replay 의미가 빠르게 꼬인다. 토픽 수보다 더 비싼 것은 모호한 의미다.

### 5) rename과 delete를 과소평가한다

필드 추가보다 위험한 것이 rename과 delete다. 특히 장기 replay, 데이터 웨어하우스 적재, 서드파티 소비자가 있으면 한 번 지운 필드는 생각보다 오래 문제를 남긴다.

### 6) 포맷별 세부 규칙을 추상화로 뭉갠다

"어차피 다 schema니까 비슷하겠지"라는 태도가 가장 위험하다. Avro의 default, Protobuf의 field number, JSON Schema의 openness는 서로 다른 규칙이다. 팀 리뷰 가이드도 포맷별로 달라야 한다.

### 7) registry를 뒀는데 CI 검증은 없다

registry를 두었는데도 실제 스키마 등록을 프로덕션 애플리케이션이 런타임에 처음 시도한다면, 사고 시점만 뒤로 미룬 셈이다. 등록/호환성 검사는 CI나 배포 전 단계에서 먼저 보이는 것이 좋다.

---

## 체크리스트: 운영에 넣기 전에 최소한 이것은 확인하자

### 계약 모델링

- 이 subject는 어떤 소비자들이 읽는가?
- 과거 메시지 replay가 필요한가?
- 외부 팀 또는 외부 시스템이 읽는가?
- 토픽당 이벤트 타입 하나 원칙을 유지할 것인가?

### 포맷 선택

- 조직이 Avro/Protobuf/JSON Schema 중 무엇에 가장 익숙한가?
- default/nullable/enum/decimal/timestamp 규칙을 문서화했는가?
- 포맷별 리뷰 포인트를 코드리뷰 체크리스트에 넣었는가?

### compatibility 정책

- 기본값은 왜 그 값인가?
- 이 subject는 `BACKWARD`면 충분한가, `BACKWARD_TRANSITIVE`가 필요한가?
- 운영 replay 요구와 정책이 실제로 맞는가?
- 글로벌 설정과 subject 개별 설정이 충돌하지 않는가?

### subject naming

- `TopicNameStrategy`, `RecordNameStrategy`, `TopicRecordNameStrategy` 중 선택 이유가 명확한가?
- 같은 이벤트 타입 재사용이 정말 필요한가?
- 운영자가 subject와 topic 관계를 추적할 수 있는가?

### 배포/운영

- auto-registration을 어느 환경까지 허용할 것인가?
- schema 등록 권한을 누가 가지는가?
- CI에서 호환성 검사를 수행하는가?
- schema registry 장애 시 producer/consumer의 실패 모드가 명확한가?
- schema cache hit/miss, registry latency, 4xx/5xx를 모니터링하는가?

### 진화 전략

- 필드 추가 시 optional/default 규칙이 있는가?
- rename/delete/deprecation 절차가 있는가?
- protobuf라면 removed field를 reserved 처리하는가?
- 신규 consumer가 오래된 메시지를 실제로 읽는 테스트가 있는가?

이 체크리스트가 없다면, registry를 붙였더라도 아직 계약 운영이 자동화된 것은 아니다.

---

## 한 줄 정리

Kafka Schema Registry의 핵심은 "스키마를 저장하는 것"이 아니라, **이벤트 계약의 진화 속도를 운영 가능한 규칙으로 통제하는 것**이다. 포맷 선택, subject naming, compatibility mode, 배포 순서를 하나의 설계로 묶어야 replay 가능한 스트리밍 시스템이 된다.
