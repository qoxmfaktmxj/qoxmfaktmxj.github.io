---
layout: post
title: "Kafka Log Compaction 실전: cleanup.policy, Tombstone, Dirty Ratio로 상태 복구 가능한 토픽 설계하기"
date: 2026-05-12 11:40:00 +0900
categories: [data-infra]
tags: [study, data-infra, kafka, log-compaction, cleanup-policy, tombstone, state-store, cdc, operations]
permalink: /data-infra/2026/05/12/study-kafka-log-compaction-cleanup-policy-tombstone-state-rebuild.html
---

## 배경: Kafka를 이벤트 버스로만 보면 상태 복구 토픽을 잘못 설계하게 된다

Kafka를 처음 운영할 때는 보통 append-only 이벤트 로그 관점으로 시작한다.

- 주문 생성 이벤트를 발행한다
- 결제 완료 이벤트를 발행한다
- 배송 상태 변경 이벤트를 발행한다
- 컨슈머는 순서대로 읽으며 비즈니스 처리를 수행한다

여기까지는 자연스럽다. 그런데 시스템이 조금 커지면 다른 요구가 곧 튀어나온다.

- 신규 컨슈머가 붙을 때 현재 사용자 상태를 빠르게 복구하고 싶다
- 캐시 서버가 재시작된 뒤 전체 스냅샷 파일 없이도 상태를 다시 채우고 싶다
- CDC 이벤트를 장기간 보관하되, 같은 key의 오래된 중간 상태는 계속 쌓아두고 싶지 않다
- Kafka Streams나 Flink state restore 시간이 너무 길어져 부팅 시간이 길어진다
- "이 토픽은 이력 전체"보다 "최신 상태"가 더 중요하다

이 지점에서 많은 팀이 두 가지 실수를 한다.

첫째, 상태 복구용 토픽인데도 일반 이벤트 토픽처럼 무한 append만 한다.
둘째, log compaction을 켰는데 "오래된 레코드가 바로 사라질 것"이라고 기대한다.

둘 다 운영 사고로 이어진다.

상태 복구 토픽의 핵심은 단순 저장이 아니다. **같은 key에 대한 최신 의미 상태를 장기간 유지하면서도, 복구 비용과 저장 비용을 통제하는 것**이다. Kafka의 log compaction은 바로 이 문제를 풀기 위한 기능이다.

오늘 글은 Kafka log compaction을 "토픽 옵션 하나"가 아니라, **상태 토픽 설계 계약**으로 정리한다. 중급 이상 개발자가 실제 운영에서 아래 질문에 답할 수 있도록 구성했다.

1. log compaction은 정확히 무엇을 보장하고, 무엇은 전혀 보장하지 않는가
2. `cleanup.policy=compact`와 `compact,delete`는 언제 다르게 써야 하는가
3. tombstone은 단순 delete 이벤트가 아니라 어떤 복구 계약인가
4. `min.cleanable.dirty.ratio`, `min.compaction.lag.ms`, `delete.retention.ms`는 어떤 운영 감각으로 잡아야 하는가
5. 어떤 토픽은 compaction에 잘 맞고, 어떤 토픽은 오히려 독이 되는가
6. 상태 복구, 캐시 워밍, CDC, 스트림 프로세서 restore에서 어떤 실무 패턴이 안전한가

결론부터 먼저 말하면 이렇다.

> **Kafka log compaction은 "오래된 메시지를 지우는 기능"이 아니라, key 기반 상태를 재구성 가능하게 유지하는 저장 계약이다.**

이걸 놓치면 delete가 사라지지 않거나, 반대로 지워지면 안 되는 상태가 사라지거나, 신규 컨슈머가 부팅 중에 잘못된 상태를 복원하는 일이 생긴다.

---

## 먼저 큰 그림: append-only 로그와 compacted 로그는 운영 목적이 다르다

일반 이벤트 토픽은 보통 이렇게 생각하면 된다.

- 과거에 무슨 일이 있었는지의 연속 기록
- 이벤트 순서와 이력 보존이 중요
- 동일 key의 여러 이벤트가 모두 의미를 가진다

예를 들어 `order-created`, `order-paid`, `order-shipped`는 모두 남아 있어야 한다. 과거 상태 전이 자체가 비즈니스 의미이기 때문이다.

반면 compacted 토픽은 관점이 다르다.

- 특정 key의 최신 유효 상태를 복구하는 것이 중요
- 중간 이력 전체보다 현재 값이 더 중요
- 같은 key의 오래된 값은 eventually 정리돼도 된다

예를 들어 사용자 알림 설정 토픽이라면 아래처럼 볼 수 있다.

- `user-123 -> email=true`
- `user-123 -> email=false`
- `user-123 -> email=true`

이 경우 과거 세 번의 변경 이력보다, 복구 관점에서는 마지막 상태인 `email=true`가 더 중요하다. log compaction은 이럴 때 같은 key의 이전 레코드들을 결국 정리해, **토픽 전체를 다시 읽어도 최신 상태 맵을 재구성할 수 있도록** 돕는다.

여기서 중요한 단어가 "eventually"다.

log compaction은 데이터베이스의 즉시 업데이트처럼 동작하지 않는다. write path에서 이전 값을 바로 덮어쓰지 않는다. Kafka는 계속 append하고, 나중에 background cleaner가 세그먼트를 정리한다. 그래서 compaction의 본질은 즉시성보다 **복구 가능성**이다.

이 차이를 이해하지 못하면 아래 같은 오해가 생긴다.

- 같은 key를 새로 쓰면 이전 값이 바로 사라질 것이다
- tombstone을 쓰면 delete가 즉시 반영되어 토픽에서 없어질 것이다
- compacted 토픽은 최신 상태 한 건만 항상 읽힌다
- retention과 compaction은 서로 대체 관계다

전부 틀리다. compacted 토픽에도 한동안 오래된 값이 남아 있을 수 있고, tombstone도 일정 기간은 남아 있어야 하며, consumer는 여전히 append된 여러 이벤트를 본다.

즉 compaction은 조회 API가 아니라 **스토리지 유지보수 전략**이다.

---

## 핵심 개념 1: log compaction이 실제로 보장하는 것

Kafka compaction의 핵심 보장은 생각보다 좁고, 그래서 더 정확히 이해해야 한다.

### 보장 1) 같은 key에 대해 최신 레코드 중 하나는 남도록 유지하려고 한다

Kafka cleaner는 로그 세그먼트를 스캔해 같은 key의 오래된 레코드를 제거한다. 그 결과, 시간이 충분히 지나 compaction이 수행되면 각 key에 대해 최신 레코드가 남는 방향으로 수렴한다.

이 말은 곧 다음을 뜻한다.

- compaction은 key가 있어야 의미가 있다
- key가 없거나 key 설계가 잘못되면 거의 쓸모가 없다
- value가 커도 key가 안정적이면 최신 상태 복구는 가능하다

### 보장 2) offset은 연속적인 의미 상태가 아니라 로그 위치다

오래된 레코드가 정리돼도 offset 자체가 재번호 매겨지지는 않는다. 따라서 compacted 토픽을 읽을 때는 "비어 있는 위치"가 생길 수 있다. 이 때문에 compaction은 큐 삭제가 아니라 파일 내부 청소에 가깝다.

### 보장 3) 신규 consumer는 토픽 처음부터 읽어 최신 상태 맵을 다시 만들 수 있다

이게 운영적으로 가장 중요하다.

예를 들어 로컬 캐시를 메모리에 들고 있는 서비스가 있다고 하자. 서비스가 죽었다 다시 떠도 compacted 토픽을 처음부터 읽으면, 결국 모든 key의 최신 상태를 복원할 수 있다. 이 특성 때문에 Kafka Streams state store changelog, CDC 최신 스냅샷 토픽, 분산 캐시 워밍 토픽이 compaction을 자주 사용한다.

---

## 핵심 개념 2: log compaction이 보장하지 않는 것

보장 범위를 좁게 이해해야 운영 판단이 선명해진다.

### 보장하지 않는 것 1) 즉시 삭제

같은 key에 새로운 값을 써도 이전 값은 즉시 없어지지 않는다. cleaner가 돌기 전까지는 그대로 남을 수 있다. 따라서 compacted 토픽을 tailing하는 consumer는 여전히 여러 버전의 같은 key를 볼 수 있다.

즉 compacted 토픽의 consumer는 "최신 상태만 온다"고 가정하면 안 된다. **consumer는 여전히 append 로그를 처리하지만, 장기적으로 상태 복구가 가능해지는 것**이다.

### 보장하지 않는 것 2) 전역 정렬 기반 최신성

compaction은 key 단위 최신성에 집중한다. 다른 key들 사이의 상대적 최신성을 의미 있게 정리해주지 않는다. 따라서 전체 시스템의 일관된 snapshot을 얻고 싶다면, compaction만으로는 부족하고 version, event time, snapshot cutover 같은 별도 규칙이 필요하다.

### 보장하지 않는 것 3) 잘못된 key 설계의 구원

예를 들어 주문 상태를 compacted 토픽에 쓰면서 key를 `orderId` 대신 `status`로 잡으면, 서로 다른 주문들이 같은 key 버킷으로 충돌한다. cleaner는 비즈니스 의미를 모른다. key가 같으면 이전 값 후보로 본다. 즉 compaction은 key 안정성에 전적으로 의존한다.

### 보장하지 않는 것 4) delete semantics의 자동 완성

값을 null로 보내는 tombstone은 delete 의도를 표현할 뿐이다. consumer가 그 의미를 이해하고 상태 저장소에서 실제로 삭제해야 한다. 또한 tombstone도 영원히 남는 것이 아니라 `delete.retention.ms` 이후 cleaner 대상이 될 수 있다.

---

## 핵심 개념 3: `cleanup.policy=compact`와 `compact,delete`는 다른 운영 계약이다

실무에서 자주 헷갈리는 설정이 바로 이 부분이다.

### `cleanup.policy=compact`

이 설정은 key 최신 상태 복구가 최우선인 토픽에 적합하다.

의미:

- 같은 key의 오래된 레코드는 eventually 정리한다
- 최신 레코드와 tombstone은 정책에 따라 남긴다
- 시간 기반 보존보다 상태 기반 보존이 우선이다

잘 맞는 사례:

- 사용자 설정 최신 상태
- 상품 메타데이터 최신 상태
- 캐시 워밍용 reference data
- Kafka Streams changelog
- CDC latest-state projection

### `cleanup.policy=compact,delete`

이 설정은 compaction과 retention을 같이 쓴다.

의미:

- 같은 key의 오래된 값은 정리한다
- 동시에 세그먼트 전체가 retention 조건을 넘으면 삭제할 수 있다
- 즉 "상태 복구용이지만 무한 보관은 하지 않겠다"는 선택이다

잘 맞는 사례:

- 최신 상태는 중요하지만, 아주 오래된 비활성 key는 유지 비용이 너무 큰 토픽
- 주기적으로 전체 스냅샷을 별도로 저장하고 Kafka는 최근 복구 창만 제공하는 구조
- CDC mirror 토픽이지만 장기 보관은 object storage나 lakehouse로 넘기는 구조

### 무엇을 고를까?

운영 기준은 아래처럼 잡는 편이 실용적이다.

1. **Kafka만으로 언제든 전체 상태를 복구해야 한다**면 `compact`를 먼저 검토한다.
2. **복구 창을 며칠 또는 몇 주로 제한해도 되고, 장기 스냅샷은 외부 저장소가 책임진다**면 `compact,delete`를 고려한다.
3. delete retention, bootstrap 시간, inactive key 규모를 모르면 성급히 `compact,delete`로 가지 않는다.

많은 팀이 저장 비용을 줄이려다 `compact,delete`를 쉽게 켠다. 그런데 신규 consumer가 느리게 부팅하거나 장기간 다운되었다가 돌아오는 경우, 필요한 tombstone이나 최신 레코드가 이미 retention에 걸려 사라질 수 있다. 그러면 "복구 가능한 토픽"이라는 전제가 깨진다.

---

## 핵심 개념 4: tombstone은 delete 이벤트가 아니라 상태 저장소에 대한 삭제 명령이다

Kafka에서 tombstone은 보통 **key는 있고 value는 null인 레코드**를 말한다.

예를 들어 사용자가 푸시 토큰을 삭제한 경우를 생각해 보자.

```json
key = "user-123"
value = null
```

이 레코드의 의미는 단순히 "이 이벤트는 비어 있다"가 아니다. compaction과 함께 보면 의미가 달라진다.

- downstream state store는 `user-123` 항목을 삭제해야 한다
- 나중에 cleaner가 돌면 과거 `user-123` 값들과 함께 tombstone도 정리 대상이 된다
- 그 시점 이후 신규 consumer는 해당 key가 현재 존재하지 않는다는 사실만 알면 된다

즉 tombstone은 **과거 값을 제거하라는 의도 + 현재 key가 삭제 상태라는 표식**이다.

### tombstone을 꼭 이해해야 하는 이유

삭제를 일반 이벤트로만 보내면 신규 consumer가 현재 상태를 복원할 때 문제가 생긴다.

예를 들어 아래처럼 value 기반 상태 토픽을 운영한다고 하자.

- `user-123 -> plan=premium`
- `user-123 -> plan=free`
- 사용자가 완전히 탈퇴함

여기서 탈퇴를 별도 이벤트 토픽에만 남기고 상태 토픽에는 tombstone을 쓰지 않으면, 신규 consumer가 상태 토픽만 재생했을 때 `user-123`이 여전히 존재하는 것처럼 복원될 수 있다.

즉 상태 복구 토픽에서는 삭제도 상태 변화의 일부다. tombstone을 빼먹으면 "업데이트는 복구되는데 삭제는 복구되지 않는" 반쪽 시스템이 된다.

### tombstone 운영에서 자주 놓치는 점

- serializer가 null value를 허용하는지 확인하지 않음
- schema registry 기반 역직렬화에서 null 처리 정책이 애매함
- consumer 캐시 코드가 null value를 무시하고 삭제하지 않음
- `delete.retention.ms`를 너무 짧게 잡아 느린 bootstrap consumer가 tombstone을 놓침

삭제가 중요한 도메인일수록 tombstone은 옵션이 아니라 필수 계약이다.

---

## 핵심 개념 5: compaction 품질은 cleaner가 아니라 key 설계에서 결정된다

log compaction을 켜고도 효과를 못 보는 팀의 상당수는 cleaner 설정보다 key를 잘못 설계했다.

### 좋은 key의 조건

1. **비즈니스 엔티티를 안정적으로 식별한다**
2. **같은 상태 집합이 항상 같은 key로 모인다**
3. **불필요하게 변하지 않는다**
4. **consumer가 상태 저장 구조의 primary key로 바로 쓸 수 있다**

예시:

- 사용자 프로필 최신 상태 → `userId`
- 상품 재고 최신 상태 → `skuId` 또는 `warehouseId:skuId`
- 계정별 feature flag 상태 → `accountId:flagName`

### 나쁜 key 패턴

#### 1) 랜덤 UUID를 매번 새로 key로 사용

이러면 같은 엔티티의 업데이트가 모두 다른 key가 된다. compaction은 사실상 작동하지 않는다.

#### 2) 이벤트 종류를 key로 사용

예: `USER_UPDATED`, `USER_DELETED`

서로 다른 사용자들이 같은 key로 덮인다. 복구는 깨진다.

#### 3) mutable attribute를 key에 포함

예: 이메일 주소가 변경될 수 있는데 `email`을 key로 사용

이 경우 key migration을 따로 처리하지 않으면 이전 key와 새 key가 동시에 남아 중복 상태가 된다.

### practical rule

> **compacted topic의 key는 메시지 식별자보다 상태 식별자여야 한다.**

이 문장을 기억하면 설계 실수가 많이 줄어든다.

---

## 실무 예시 1: 사용자 설정 캐시를 compacted topic으로 복구하기

가장 흔하고 안전한 패턴 중 하나다.

상황:

- 사용자별 알림 설정을 RDB에 저장한다
- API 서버는 빠른 조회를 위해 Redis 또는 in-memory cache를 쓴다
- 캐시 서버 재시작 시 전체 DB 스캔 없이 상태를 복구하고 싶다

설계:

- 토픽명: `user-preference-state`
- key: `userId`
- value: 사용자 설정 전체 스냅샷 JSON 또는 Avro record
- cleanup policy: `compact`

예시 레코드 흐름:

- `user-1 -> {email:true, push:false}`
- `user-2 -> {email:false, push:true}`
- `user-1 -> {email:true, push:true}`
- `user-2 -> null`  (계정 삭제 또는 preference row 삭제)

복구 절차:

1. 서비스 시작 시 earliest부터 읽는다
2. key/value를 로컬 맵 또는 Redis에 반영한다
3. null value면 캐시 엔트리를 삭제한다
4. 끝까지 따라잡은 뒤부터는 실시간 tailing으로 전환한다

장점:

- 별도 full snapshot 배치 없이도 상태 복구 가능
- 캐시 워밍 시간이 예측 가능
- 상태 전파와 복구 경로가 하나로 통일됨

주의점:

- 메시지 payload에 부분 변경만 넣으면 복구가 꼬일 수 있다
- 상태 토픽은 가능하면 "현재 전체 상태" 또는 복구 가능한 merge 규칙을 담아야 한다

예를 들어 `{push:true}`만 보내는 partial patch 모델은 consumer 구현이 복잡해진다. 신규 consumer는 과거 patch들을 모두 정확히 재생해야만 전체 상태를 복원할 수 있다. 운영 단순성을 원하면 **최신 상태 전체를 value로 보내는 쪽이 대개 안전하다.**

---

## 실무 예시 2: CDC latest-state projection 토픽 만들기

Debezium 같은 CDC를 붙이면 원본 변경 이벤트는 append-only로 많이 쌓인다. 이 이벤트 자체는 매우 유용하지만, 모든 downstream이 row-level 변경 이력을 다 필요로 하지는 않는다.

예를 들어 추천 시스템이나 검색 인덱서가 필요한 것은 "최신 상품 상태"일 수 있다.

이때 많이 쓰는 패턴이 두 단계 토픽이다.

1. 원본 CDC 토픽: 전체 변경 이력 보존
2. compacted projection 토픽: 최신 행 상태 보존

예시:

- raw topic: `db.inventory.products`
- compacted topic: `product-state`

흐름:

- CDC consumer가 raw topic을 읽는다
- 필요한 컬럼만 정규화한다
- key를 `productId`로 잡아 compacted topic에 최신 상태를 다시 쓴다
- delete 이벤트는 tombstone으로 변환한다

이 구조의 장점은 명확하다.

- raw CDC와 소비자 친화적 최신 상태 토픽을 분리할 수 있다
- downstream 서비스는 최신 상태 재구성에 집중할 수 있다
- 복구 속도가 빨라진다

대신 trade-off도 있다.

- 파이프라인이 한 단계 더 늘어난다
- raw와 projection 사이의 지연이 생긴다
- projection 로직의 버그가 잘못된 최신 상태를 퍼뜨릴 수 있다

그래서 이 구조에서는 raw topic이 **진실의 원천**, compacted projection은 **복구 최적화된 서빙 상태**라는 역할 구분을 분명히 해야 한다.

---

## 실무 예시 3: Kafka Streams/Flink state restore 시간을 줄이는 관점

Streams/Flink를 써 본 팀은 state restore가 생각보다 비싸다는 걸 빨리 체감한다.

- 상태 저장소가 크다
- changelog 토픽이 과도하게 비대하다
- 재배포 때 복구 시간이 길어져 rollout이 느리다
- autoscaling 시 warm-up이 길다

이때 changelog 토픽이 compacted라는 사실은 매우 중요하다. 하지만 "compacted이기만 하면 restore가 항상 빠르다"는 뜻은 아니다.

restore 시간은 아래 영향을 같이 받는다.

- key cardinality
- value 크기
- tombstone 비율
- 세그먼트 크기
- cleaner가 얼마나 잘 따라가고 있는지
- retention과 compaction 정책

예를 들어 key 수가 1천만 개인 reference dataset이면, compaction이 잘 되어도 최신 상태 1천만 건은 어차피 읽어야 한다. 즉 compaction은 restore를 0으로 만드는 마법이 아니라, **불필요한 과거 중간 버전을 줄여 restore 비용을 상한 안으로 넣는 도구**다.

따라서 stateful stream 애플리케이션 운영에서는 다음을 같이 봐야 한다.

- changelog 토픽 크기 추세
- consumer bootstrap 속도
- restore 중 broker/network 병목
- cleaner backlog
- state store checkpoint 주기

---

## 핵심 설정 1: `min.cleanable.dirty.ratio`를 어떻게 이해할 것인가

이 값은 cleaner가 세그먼트를 얼마나 "더러워졌다고" 판단할 때 정리할지를 제어한다.

직관적으로 보면 이렇다.

- dirty ratio가 높다 → 아직 유효하지 않은 중복/오래된 레코드 비율이 많다
- 설정값이 낮다 → cleaner가 더 자주 개입한다
- 설정값이 높다 → cleaner가 덜 자주 개입한다

### 낮게 잡으면 좋은 점

- 오래된 중복 레코드가 더 빨리 정리될 수 있다
- compacted 토픽 크기가 빨리 안정될 수 있다
- bootstrap restore 비용이 낮아질 수 있다

### 낮게 잡을 때 비용

- cleaner I/O와 CPU 사용량 증가
- 브로커 리소스 경쟁 가능성
- 너무 공격적이면 다른 토픽 workload와 충돌

### 운영 감각

이 값을 독립적으로 보지 말고 아래와 같이 판단하는 편이 낫다.

- restore 시간이 문제인가?
- broker disk I/O 여유가 있는가?
- compacted topic 수와 크기가 얼마나 되는가?
- cleaner backlog가 지속적으로 쌓이는가?

즉 `min.cleanable.dirty.ratio`는 "낮을수록 좋다"가 아니라, **복구 비용을 얼마나 적극적으로 선제 정리할 것인가**의 선택이다.

---

## 핵심 설정 2: `min.compaction.lag.ms`와 `max.compaction.lag.ms`

이 값들은 레코드가 얼마나 빨리 또는 늦게 compaction 대상이 될 수 있는지 조절한다.

### `min.compaction.lag.ms`

새로 쓴 레코드가 최소 얼마 동안은 compaction되지 않도록 보장한다.

이게 왜 필요할까?

consumer 중 일부가 최신 상태뿐 아니라 아주 최근 변경 흐름 자체를 잠깐은 읽어야 할 수 있기 때문이다. 또는 write 직후 바로 compaction되는 극단을 피하고 싶을 수 있다.

너무 낮으면:

- 같은 key의 연속 변경이 매우 빠르게 정리 대상으로 들어갈 수 있다
- 최근 이벤트 히스토리를 잠깐이라도 보고 싶은 소비자에게 불리할 수 있다

너무 높으면:

- 오래된 버전이 더 오래 남아 토픽 크기와 restore 비용이 증가한다

### `max.compaction.lag.ms`

레코드가 너무 오래 compaction되지 않은 채 남지 않도록 상한을 두는 성격이다.

이 값은 "eventually"의 상한을 어느 정도 운영적으로 의식하게 해준다. restore 비용과 저장 비용이 중요할수록 무한정 늦어지는 상황을 싫어하게 된다.

### practical rule

- restore 비용이 중요하고 최신 상태 위주 토픽이면 `min.compaction.lag.ms`를 과도하게 길게 두지 않는다
- 최근 변경 이력을 잠시 관찰해야 하는 운영 도구가 있으면 최소 lag를 적당히 둔다
- `max.compaction.lag.ms`는 cleaner backlog, 디스크 추세와 함께 본다

---

## 핵심 설정 3: `delete.retention.ms`는 tombstone 안전 창이다

이 값은 tombstone이 최소 얼마 동안 유지될지를 정한다. 이 설정을 얕게 보면 매우 위험하다.

왜냐하면 tombstone은 신규 consumer가 "이 key는 삭제되었다"는 사실을 학습하는 유일한 단서일 수 있기 때문이다.

### 너무 짧게 잡으면 생기는 문제

- 장시간 다운되었던 consumer가 복귀했을 때 tombstone을 놓친다
- bootstrap이 느린 대형 consumer가 중간에 삭제 상태를 보지 못할 수 있다
- 결과적으로 이미 삭제된 key가 로컬 상태에 다시 살아난다

### 너무 길게 잡으면 생기는 문제

- tombstone이 오랫동안 남아 cleaner 효율과 저장 효율이 떨어질 수 있다
- 삭제가 많은 토픽에서는 생각보다 디스크를 많이 잡아먹는다

### 운영 기준

`delete.retention.ms`는 아래 최악 조건보다 짧으면 안 된다.

- 가장 느린 bootstrap consumer가 earliest부터 끝까지 따라잡는 데 걸리는 시간
- 장기 장애 후 복귀하는 consumer의 허용 downtime
- DR/재배포 시 state restore 예상 시간

즉 이 값은 단순 retention 숫자가 아니라, **삭제 의미가 소비자에게 안전하게 전달될 수 있는 시간 창**이다.

---

## 토픽 생성 예시: 상태 복구용 compacted topic

예를 들어 `account-feature-state` 토픽을 만든다고 하자.

```bash
kafka-topics --create \
  --topic account-feature-state \
  --partitions 12 \
  --replication-factor 3 \
  --config cleanup.policy=compact \
  --config min.cleanable.dirty.ratio=0.3 \
  --config delete.retention.ms=86400000 \
  --config min.compaction.lag.ms=300000
```

여기서 중요한 건 숫자 그 자체보다 이유다.

- `cleanup.policy=compact` → 상태 복구가 주목적
- `min.cleanable.dirty.ratio=0.3` → 중복이 제법 쌓이면 cleaner가 개입
- `delete.retention.ms=1d` → 최소 하루 동안 tombstone 보존
- `min.compaction.lag.ms=5m` → 아주 최근 변경은 잠시 보존

실제 값은 workload에 맞춰 달라져야 하지만, 적어도 **복구 시간, 삭제 의미, cleaner 비용**이라는 세 축을 동시에 보고 있다는 점이 중요하다.

---

## Producer 설계: 상태 토픽은 partial event보다 materialized state에 가깝게 보라

상태 복구용 compacted topic을 운영할 때 producer는 자주 두 모델 중 하나를 택한다.

### 모델 A) 변경 이벤트를 그대로 보냄

예:

- `{"op":"set_email","value":true}`
- `{"op":"set_push","value":false}`

장점:

- payload가 작다
- 원본 행위를 보존한다

단점:

- 신규 consumer가 전체 상태를 복원하려면 모든 patch 순서를 정확히 재생해야 한다
- merge 로직이 consumer마다 중복 구현된다
- 버그가 생기면 복구가 더 어렵다

### 모델 B) 최신 상태 전체를 보냄

예:

- `{"email":true,"push":false,"sms":true}`

장점:

- consumer가 단순하다
- bootstrap 복구가 안정적이다
- downstream 서비스 간 상태 해석 차이가 줄어든다

단점:

- payload가 커질 수 있다
- 작은 변경에도 전체 상태를 다시 보낸다

상태 토픽에서는 모델 B가 의외로 더 자주 이긴다. 네트워크 비용이 아주 크지 않다면, **복구 단순성**이 운영 비용을 크게 낮춰주기 때문이다.

---

## Consumer 설계: compacted topic consumer는 "latest only"가 아니라 "upsert + delete" 소비자다

consumer 코드는 아래 전제를 가져야 한다.

1. 같은 key의 여러 버전을 볼 수 있다
2. value가 null이면 삭제로 해석해야 한다
3. out-of-band snapshot이 없다면 earliest replay가 정식 복구 경로다
4. idempotent upsert가 가능해야 한다

Python 스타일 의사코드로 보면 아래와 같다.

```python
state = {}

for record in consumer:
    key = record.key.decode("utf-8")
    value = record.value

    if value is None:
        state.pop(key, None)
        continue

    state[key] = decode(value)
```

핵심은 단순하다. compacted topic consumer는 이벤트 핸들러라기보다 **key-value materializer**에 가깝다.

실제 운영에서는 여기에 추가로 다음이 필요하다.

- bootstrap 완료 시점 표시
- lag 및 restore 시간 메트릭
- schema version 호환 처리
- tombstone 처리 통계
- 로컬 상태 스냅샷/체크포인트

---

## 트레이드오프: compaction은 저장 비용을 줄이는 대신 쓰기/복구/운영 모델을 바꾼다

log compaction은 강력하지만 무료가 아니다.

### 장점

- 최신 상태 복구가 가능하다
- 중복 중간 버전 누적으로 인한 토픽 비대화를 줄인다
- 캐시 워밍, state restore, latest-state projection에 잘 맞는다
- delete semantics를 로그 기반으로 일관되게 표현할 수 있다

### 단점

- key 설계가 조금만 틀어져도 바로 의미가 깨진다
- cleaner 리소스 사용량을 무시할 수 없다
- 즉시 정리가 아니므로 operator 기대와 어긋나기 쉽다
- consumer가 tombstone과 upsert 모델을 정확히 구현해야 한다
- 전체 이력이 필요한 use case에는 부적합하다

### compaction이 맞지 않는 경우

- 과거 모든 이벤트가 각각 비즈니스 의미를 가질 때
- audit trail이 핵심일 때
- 순차 이벤트 재생 자체가 중요한 워크플로일 때
- key 기반 최신 상태보다 이벤트 흐름 분석이 더 중요할 때

예를 들어 결제 승인 이력, 주문 상태 전이 이력, 보안 감사 로그는 compacted topic 단독으로 다루기보다 append-only event log가 먼저다.

실무에서는 둘을 분리하는 것이 가장 안전하다.

- **event topic**: 진실의 이력
- **state topic**: 복구 최적화된 최신 상태

이렇게 역할을 나누면 compaction이 필요한 이유와 아닌 이유가 명확해진다.

---

## 흔한 실수 1: compacted topic을 DB table처럼 즉시 일관된 최신값 저장소로 생각한다

Kafka는 여전히 로그다. compaction은 background maintenance다. 따라서 producer가 새 값을 썼다고 해서 reader가 토픽에 최신 버전 한 건만 존재한다고 기대하면 안 된다.

이 착각은 특히 운영자가 CLI로 topic dump를 봤을 때 심해진다.

- "왜 같은 key가 아직 여러 번 보이지?"
- "delete 했는데 왜 레코드가 남아 있지?"

정상일 수 있다. cleaner 주기와 세그먼트 상황을 봐야 한다.

---

## 흔한 실수 2: 삭제가 중요한 도메인인데 tombstone을 생략한다

업데이트만 잘 전파되고 삭제는 별도 배치나 별도 이벤트에 맡기면, 신규 consumer 복구 시 삭제 상태를 잃기 쉽다. 검색 인덱스, 캐시, feature flag, 계정 상태처럼 delete 의미가 큰 도메인에서는 tombstone이 빠지면 언젠가 유령 데이터가 되살아난다.

---

## 흔한 실수 3: key를 메시지 ID로 잡는다

메시지마다 다른 UUID를 key로 넣으면 compaction은 사실상 꺼진 것과 비슷하다. 상태 토픽의 key는 이벤트 인스턴스가 아니라 엔티티 식별자여야 한다.

---

## 흔한 실수 4: `delete.retention.ms`를 디스크 절감만 보고 과감히 줄인다

짧은 retention은 보기에는 깔끔하지만, 늦게 붙는 consumer에게 삭제 의미를 전달하지 못할 수 있다. 상태 복구 토픽에서 tombstone retention은 저장 비용보다 정합성 문제에 더 직접 연결된다.

---

## 흔한 실수 5: raw CDC와 latest-state projection을 구분하지 않는다

원본 변경 이력을 보존해야 하는 요구와 최신 상태를 빠르게 복구해야 하는 요구를 한 토픽에 모두 우겨 넣으면, 결국 retention·compaction·consumer 해석이 서로 충돌한다. 둘은 같은 데이터라도 운영 목적이 다르다.

---

## 운영 체크리스트: compacted topic을 배포하기 전에 확인할 것

- [ ] 이 토픽의 목적이 "이력 보존"인지 "최신 상태 복구"인지 명확한가?
- [ ] key가 엔티티 식별자를 안정적으로 대표하는가?
- [ ] value가 전체 상태인지, 아니라면 merge 규칙이 복구 가능하게 정의됐는가?
- [ ] delete를 tombstone으로 표현하는가?
- [ ] serializer / schema registry / consumer가 null value를 안전하게 처리하는가?
- [ ] `cleanup.policy`를 `compact`와 `compact,delete` 중 목적에 맞게 골랐는가?
- [ ] `delete.retention.ms`가 가장 느린 bootstrap/복구 시간보다 충분히 긴가?
- [ ] cleaner backlog, restore 시간, topic size를 관측하는 메트릭이 있는가?
- [ ] raw event topic과 state topic의 역할을 분리했는가?
- [ ] 신규 consumer가 earliest replay만으로 상태를 재구성할 수 있는지 실제로 검증했는가?

---

## 한 줄 정리

**Kafka log compaction의 핵심은 오래된 메시지를 치우는 것이 아니라, key 기반 최신 상태와 삭제 의미를 신규 consumer가 다시 복구할 수 있게 만드는 저장 계약이다.**
