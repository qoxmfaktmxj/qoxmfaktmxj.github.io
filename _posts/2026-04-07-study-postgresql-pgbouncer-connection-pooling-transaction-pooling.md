---
layout: post
title: "PgBouncer 실전: Connection Storm, Transaction Pooling, Prepared Statement 함정까지 운영 기준 정리"
date: 2026-04-07 11:40:00 +0900
categories: [sql]
tags: [study, sql, postgresql, pgbouncer, connection-pooling, transaction-pooling, prepared-statements, performance, operations]
permalink: /sql/2026/04/07/study-postgresql-pgbouncer-connection-pooling-transaction-pooling.html
---

## 배경: 왜 PostgreSQL 성능 문제는 결국 쿼리보다 커넥션 설계로 터지는가

PostgreSQL 운영에서 처음 눈에 들어오는 병목은 대개 느린 쿼리다. 그래서 많은 팀이 인덱스, 실행 계획, vacuum, 통계부터 본다. 그 방향은 맞다. 다만 실서비스를 오래 운영해보면 쿼리 최적화와 별개로 훨씬 더 자주 터지는 문제가 있다.

- 애플리케이션 인스턴스 수를 조금 늘렸더니 DB CPU가 갑자기 불안정해진다
- 배치가 시작되는 시각마다 `too many clients already` 또는 타임아웃이 난다
- 평소에는 괜찮은데 배포 직후나 장애 복구 직후 응답 시간이 급격히 튄다
- 서버리스, 오토스케일, 워커 프로세스가 섞인 구조에서 커넥션 수가 예측 불가능하게 불어난다
- RDS 스펙은 높였는데도 트래픽 피크에서 오히려 더 쉽게 흔들린다

이때 많은 팀이 하는 첫 반응은 단순하다.

- `max_connections`를 더 올린다
- 애플리케이션 풀 사이즈를 넉넉히 잡는다
- 인스턴스를 더 키우면 해결될 거라 기대한다

하지만 PostgreSQL은 MySQL과도, 단순한 프록시형 데이터 저장소와도 다르다. PostgreSQL은 **연결 하나당 서버 프로세스 하나가 대응되는 구조**다. 즉 커넥션은 거의 공짜가 아니다. 커넥션 수가 늘어날수록 메모리, 컨텍스트 스위칭, lock contention, 캐시 효율, 운영 복잡도가 같이 올라간다.

그래서 실무에서는 어느 순간 질문이 바뀐다.

> **문제는 쿼리 한 건이 아니라, 동시에 붙으려는 수백 개의 연결을 시스템이 어떻게 흡수할 것인가?**

이 지점에서 등장하는 대표적인 해법이 **PgBouncer**다. 그런데 PgBouncer는 "앞에 하나 두면 빨라지는 도구"가 아니다. 제대로 쓰면 연결 폭주를 구조적으로 흡수하지만, 대충 붙이면 prepared statement, 세션 상태, 마이그레이션, advisory lock, LISTEN/NOTIFY, ORM 동작이 한 번에 꼬인다.

즉 실무의 핵심은 설치가 아니라 **pooling mode를 어떻게 선택하고, 어떤 트래픽은 통과시키고, 어떤 트래픽은 우회시키며, 애플리케이션 상태 가정을 어떻게 정리할 것인가**다.

오늘 글은 아래 질문에 답하는 데 초점을 둔다.

- PostgreSQL에서 커넥션 수가 왜 그렇게 비싼가
- PgBouncer는 정확히 무엇을 줄여주고, 무엇은 줄여주지 못하는가
- Session / Transaction / Statement Pooling은 무엇이 다르고, 실무 기본값은 무엇인가
- Transaction Pooling에서 왜 prepared statement, temp table, session variable, advisory lock이 문제되는가
- ORM, 배치, 마이그레이션, 관리 작업은 어떤 경로로 붙여야 안전한가
- pool size, max client, reserve pool을 어떻게 잡아야 운영 사고를 줄일 수 있는가

핵심만 먼저 요약하면 이렇다.

1. PostgreSQL은 커넥션 자체가 비싸므로, **애플리케이션의 동시 요청 수와 DB 커넥션 수를 분리**해야 한다
2. PgBouncer의 진짜 가치는 속도보다 **연결 수 상한 통제와 connection storm 완충**에 있다
3. 일반적인 웹 서비스 기본값은 대개 **transaction pooling**이지만, 세션 상태에 의존하는 코드가 있으면 바로 사고가 난다
4. ORM과 드라이버의 prepared statement 전략은 **PgBouncer 모드와 같이 설계**해야 한다
5. 마이그레이션, 장기 트랜잭션, LISTEN/NOTIFY, 세션 락 같은 작업은 **직접 DB 연결 우회 경로**가 필요하다
6. `max_connections`를 크게 여는 것보다 **작은 서버 연결 풀을 엄격히 관리하는 편이 더 안정적**인 경우가 많다
7. PgBouncer 도입은 인프라 작업이 아니라 **애플리케이션의 세션 가정을 드러내는 아키텍처 작업**이다

---

## 먼저 큰 그림: PostgreSQL에서 커넥션은 왜 비싼가

애플리케이션 개발자는 커넥션을 라이브러리 객체처럼 느끼기 쉽다. 필요하면 열고, 쓰고, 닫는 핸들처럼 보인다. 하지만 PostgreSQL 서버 입장에서는 다르다.

PostgreSQL은 기본적으로 **클라이언트 연결마다 백엔드 프로세스 하나**를 만든다. 따라서 연결이 늘어난다는 건 단순히 소켓 몇 개가 늘어난다는 뜻이 아니다.

- 프로세스 수 증가
- 각 프로세스의 메모리 사용량 증가
- CPU 스케줄링 비용 증가
- lock 관리 복잡도 증가
- 캐시 효율 저하 가능성 증가
- 피크 시점 연결 생성/해제 오버헤드 증가

즉, 요청 2,000개를 동시에 처리해야 한다고 해서 PostgreSQL에 2,000개 세션을 직접 열어야 하는 건 아니다. 오히려 그 반대다.

실무에서 중요한 것은 아래 두 수를 분리하는 것이다.

- **애플리케이션 동시성**: 동시에 처리 중인 HTTP 요청, 워커 잡, 배치 태스크 수
- **DB 실동시성**: 특정 시점에 실제로 SQL을 수행해야 하는 서버 연결 수

이 둘은 절대 같지 않다. 대부분의 요청은 전체 처리 시간 중 일부 구간에서만 DB를 쓴다.

예를 들어 요청 하나가 300ms 걸리고, 그중 실제 DB를 붙잡는 시간이 25ms라면 전체 요청 수에 비해 DB가 동시에 필요한 수는 훨씬 작다. 그런데 애플리케이션 풀이 인스턴스마다 넉넉하게 잡혀 있고, 오토스케일이 붙고, 워커까지 별도 풀을 갖고 있으면 실제 필요보다 훨씬 많은 세션이 PostgreSQL에 매달리게 된다.

이 구조가 만드는 대표적인 문제가 **connection storm**다.

- 배포 후 인스턴스 20대가 한 번에 기동됨
- 각 인스턴스가 시작 직후 풀을 가득 채우려 함
- 워커도 동시에 재기동되며 커넥션을 새로 잡음
- PostgreSQL은 실제 쿼리 처리 전에 연결 수용 자체로 흔들림

그래서 커넥션 풀링의 핵심 목적은 단순 재사용이 아니다.

> **애플리케이션에서 발생하는 불규칙한 연결 수요를, DB가 감당 가능한 작은 서버 연결 집합으로 완충하는 것**

PgBouncer는 바로 이 역할에 특화된 도구다.

---

## PgBouncer가 정확히 하는 일: 클라이언트 연결과 서버 연결을 분리한다

PgBouncer를 앞단에 두면 애플리케이션은 PgBouncer에 많이 붙을 수 있다. 대신 PgBouncer는 실제 PostgreSQL 서버에는 제한된 수의 연결만 유지한다.

즉 관계는 이렇게 바뀐다.

- 기존: 앱 인스턴스 여러 개 → PostgreSQL 직접 연결
- 변경: 앱 인스턴스 여러 개 → PgBouncer → PostgreSQL 소수 연결

이때 PgBouncer는 크게 두 가지를 제공한다.

### 1) 서버 연결 수 상한 관리

애플리케이션이 500개의 클라이언트 연결을 만들어도, 실제 DB 서버 연결은 예를 들어 40개만 유지하게 만들 수 있다.

### 2) 연결 생성 폭주 완충

피크 시점에 클라이언트 연결은 늘어나도, 서버 연결은 천천히 제한적으로 사용되므로 DB가 직접 connection storm를 맞지 않는다.

하지만 여기서 자주 생기는 오해가 있다.

### PgBouncer가 해주는 것

- PostgreSQL 서버의 총 연결 수 제한
- burst 상황에서의 완충
- 애플리케이션 풀 오설정의 피해 축소
- idle connection 과잉 문제 완화
- 짧은 트랜잭션 위주의 웹 요청 효율 개선

### PgBouncer가 해주지 못하는 것

- 느린 쿼리를 빠르게 바꾸는 일
- 잘못된 인덱스 설계를 해결하는 일
- 긴 트랜잭션을 짧게 바꾸는 일
- 세션 상태에 의존하는 애플리케이션을 자동 교정하는 일
- "DB 부하가 높은데 연결만 줄이면 해결될 것"이라는 착각을 현실로 만드는 일

즉, PgBouncer는 **DB 사용량을 마법처럼 줄이는 도구가 아니라, 연결 사용 패턴을 정상화하는 도구**다.

---

## 핵심 개념 1: Pooling Mode를 이해하지 못하면 PgBouncer는 바로 장애 포인트가 된다

PgBouncer를 이해할 때 가장 중요한 축은 pooling mode다. 어떤 단위로 서버 연결을 클라이언트에게 할당하고 회수할지를 결정하기 때문이다.

대표 모드는 세 가지다.

| 모드 | 서버 연결 점유 단위 | 장점 | 주요 제약 |
| --- | --- | --- | --- |
| session | 클라이언트 세션 전체 | 애플리케이션 호환성이 높음 | 연결 수 절감 효과 제한 |
| transaction | 트랜잭션 단위 | 웹 서비스에 가장 실용적, 효율 높음 | 세션 상태 의존 코드와 충돌 |
| statement | 개별 statement 단위 | 가장 공격적 풀링 | 멀티 statement transaction 등 제약이 큼 |

실무에서는 대부분 다음 원칙으로 출발한다.

- **기본 후보는 transaction pooling**
- 세션 상태 의존도가 높거나 레거시 호환성이 중요하면 session pooling 검토
- statement pooling은 특수 케이스 아니면 보수적으로 접근

왜 transaction pooling이 많이 쓰일까?

웹 요청 대부분은 아래 흐름을 가진다.

1. 요청 수신
2. 인증/검증/비즈니스 로직 일부 수행
3. 짧은 DB 트랜잭션 실행
4. 응답 반환

이 경우 PostgreSQL 연결이 꼭 필요한 시간은 짧다. transaction pooling은 **트랜잭션이 진행되는 동안만 서버 연결을 점유**하고, 커밋/롤백 이후에는 곧바로 풀로 되돌린다. 따라서 같은 수의 서버 연결로 더 많은 애플리케이션 요청을 처리할 수 있다.

문제는 여기서부터다.

애플리케이션이 눈치채지 못한 채 "한 번 연결되면 그 세션은 계속 내 것"이라고 가정하고 있으면 transaction pooling 도입 순간 가정이 깨진다.

---

## 핵심 개념 2: Transaction Pooling이 빠른 이유는 세션 환상을 버리기 때문이다

transaction pooling에서 중요한 사실은 아주 단순하다.

> **트랜잭션이 끝나면, 다음 SQL은 같은 PostgreSQL 세션에서 실행된다는 보장이 없다**

이 한 줄 때문에 문제가 생기는 패턴은 생각보다 많다.

### 안전한 것

- 단일 트랜잭션 안에서 끝나는 일반 CRUD
- 명시적 파라미터 바인딩을 사용하는 짧은 질의
- 요청 단위로 시작해서 요청 안에서 끝나는 비즈니스 트랜잭션
- 커밋 후 세션 상태를 기대하지 않는 ORM 사용 패턴

### 위험한 것

- `SET search_path = ...` 후 이후 쿼리에서 계속 그 상태를 기대하는 코드
- temp table을 만들고 다음 쿼리에서 다시 사용하는 흐름
- 세션 단위 advisory lock 사용
- `LISTEN/NOTIFY` 수신 세션 유지
- 서버 세션에 남는 prepared statement 이름 재사용 가정
- 커넥션 하나에 tenant context를 심어두는 방식

예를 들어 다음 코드는 transaction pooling에서 쉽게 깨진다.

```sql
SET search_path TO tenant_a;
SELECT * FROM orders;
```

개발자는 같은 연결에서 실행된다고 생각할 수 있지만, PgBouncer transaction mode에서는 `SET`과 `SELECT`가 서로 다른 서버 연결로 갈 수 있다. 더 정확히 말하면, 트랜잭션 경계 밖에서 세션 상태를 남기려는 발상 자체가 맞지 않다.

따라서 transaction pooling을 도입할 때는 성능 튜닝보다 먼저 다음 질문을 해야 한다.

- 우리 애플리케이션은 세션 상태를 은근히 기대하고 있지 않은가?
- ORM이나 프레임워크가 내부적으로 connection-local state를 쓰지 않는가?
- 배치와 관리 스크립트는 웹 요청과 같은 연결 정책을 써도 되는가?

실무에서 PgBouncer 도입이 까다로운 이유는 도구 설정이 아니라, 이 숨은 가정을 찾아내는 데 있다.

---

## 핵심 개념 3: Prepared Statement는 PgBouncer에서 가장 자주 부딪히는 함정 중 하나다

PgBouncer 전환 때 가장 많이 듣는 장애 증상 중 하나는 이런 형태다.

- `prepared statement "..." already exists`
- `prepared statement does not exist`
- 특정 ORM에서만 간헐적 오류 발생
- 로컬에서는 재현이 안 되는데 운영 transaction pooling에서만 깨짐

배경을 먼저 보자.

PostgreSQL의 서버 측 prepared statement는 **특정 서버 세션에 귀속**된다. 즉 어느 연결에서 `PREPARE`한 이름은 그 연결에서만 의미가 있다. 그런데 transaction pooling에서는 다음 트랜잭션이 다른 서버 연결로 갈 수 있다. 그러면 애플리케이션이 같은 연결이라고 믿고 prepared statement를 재사용할 때 문제가 생긴다.

### 왜 ORM에서 특히 자주 터질까

많은 드라이버와 ORM은 성능 최적화를 위해 내부적으로 prepared statement를 사용한다. 하지만 그 전략은 제각각이다.

- 어떤 드라이버는 서버 측 prepared statement를 적극 사용한다
- 어떤 드라이버는 일정 횟수 이상 반복된 쿼리만 prepare한다
- 어떤 ORM은 연결 단위 statement cache를 둔다
- 어떤 조합은 transaction pooling과 충돌한다

즉 "애플리케이션은 PgBouncer만 추가했을 뿐"이라고 느껴도, 실제로는 **드라이버의 statement lifecycle 가정이 바뀌는 것**이다.

### 실무 판단 기준

#### 1) 가장 안전한 출발점

- transaction pooling을 쓰되
- 서버 측 prepared statement 자동 사용 옵션을 비활성화하거나
- 드라이버가 PgBouncer 친화 모드를 제공하면 그 설정을 우선 검토한다

예를 들어 일부 드라이버는 prepare threshold를 0으로 두거나, 단순 query protocol 사용 옵션을 제공한다. 이름은 드라이버마다 다르지만 질문은 같다.

> **이 드라이버가 서버 세션에 남는 prepared statement를 기대하는가?**

#### 2) PgBouncer의 prepared statement 지원 기능을 맹신하지 말기

최근 PgBouncer 버전은 transaction pooling에서 prepared statement 호환성을 완화하는 옵션을 제공한다. 다만 이것이 모든 드라이버와 ORM 조합에서 자동으로 안전함을 보장하는 것은 아니다.

특히 아래 상황에서는 여전히 검증이 필요하다.

- 드라이버와 PgBouncer 버전 조합이 제각각인 환경
- 애플리케이션이 statement name을 직접 다루는 경우
- 세션 상태와 statement cache가 섞여 있는 레거시 코드
- 장애 시 failover, reconnect가 빈번한 환경

실무적으로는 "지원한다"보다 **우리 드라이버 조합에서 재현 테스트를 통과했는가**가 더 중요하다.

#### 3) 운영 기준

- 웹 트래픽 경로는 prepared statement 전략을 명시적으로 관리한다
- 배치와 분석 작업은 필요하면 직접 DB 연결을 사용한다
- ORM 업그레이드 시 statement 관련 설정이 바뀌지 않았는지 릴리즈 노트를 확인한다

Prepared statement 문제는 성능 최적화 옵션 하나처럼 보여도, 실제로는 **세션 정체성(session identity)을 기대하는가의 문제**다.

---

## 실무 예시 1: 일반적인 웹 서비스에서 가장 안전한 기본 구조

가장 흔한 구조는 아래와 같다.

- API 서버 여러 대
- 백그라운드 워커 몇 대
- 마이그레이션 작업
- 운영자가 실행하는 관리 스크립트

이 구조에서 추천할 수 있는 기본 원칙은 다음과 같다.

### 경로 분리

1. **웹/API 서버**
   - PgBouncer 경유
   - 기본은 transaction pooling
2. **짧은 워커 작업**
   - PgBouncer 경유 가능
   - 트랜잭션이 짧고 세션 상태를 안 쓰면 동일 정책 사용
3. **마이그레이션 / DDL / 장기 배치 / 관리 콘솔**
   - PostgreSQL 직접 연결 우회 경로 유지
4. **LISTEN/NOTIFY 소비자, 세션 락 의존 작업**
   - 직접 연결 또는 session pooling 별도 엔드포인트

즉 모든 것을 하나의 DSN으로 몰아넣는 것이 아니라, **용도별 연결 경로를 의도적으로 분리**해야 한다.

많은 팀이 처음에는 단순화를 위해 "앱도 배치도 마이그레이션도 모두 PgBouncer 같은 주소"로 맞추고 싶어 한다. 하지만 운영적으로는 이 단순화가 오히려 위험하다. 트랜잭션 특성이 다른 작업을 같은 풀 정책에 넣으면, 어느 순간 가장 까다로운 작업 때문에 전체 정책이 session mode로 후퇴하거나, 반대로 transaction mode 때문에 특정 작업이 조용히 깨진다.

---

## 실무 예시 2: 커넥션 수는 애플리케이션 인스턴스 수가 아니라 DB 예산에서 역산해야 한다

PgBouncer를 도입해도 pool sizing을 잘못 잡으면 사고는 그대로 난다. 흔한 실수는 애플리케이션 팀이 인스턴스 기준으로 풀을 잡는 것이다.

예를 들어:

- API 서버 12대
- 각 서버 애플리케이션 풀 max 30
- 워커 6대
- 각 워커 풀 max 20

이렇게 되면 애플리케이션 관점 잠재 연결 수는 금방 수백 개가 된다. PgBouncer가 있더라도 `max_client_conn`이 과도하게 커지고, 서버 풀도 그에 맞춰 무의식적으로 커지기 쉽다.

실무에서는 반대로 생각해야 한다.

### 1단계: PostgreSQL이 안정적으로 감당할 서버 연결 예산을 정한다

예를 들면 다음처럼 잡는다.

- PostgreSQL 총 `max_connections`: 300
- 그중 운영/관리/복제/예비 포함 여유: 80
- 애플리케이션 전체가 써도 되는 실제 예산: 220

그다음 이 220을 다시 나눈다.

- API용 PgBouncer pool 총합: 120
- 워커용 PgBouncer pool 총합: 60
- 배치/관리 직접 연결 예산: 20
- 장애 대응 여유: 20

### 2단계: 애플리케이션 동시성은 클라이언트 연결 큐잉으로 흡수한다

이제 API 서버는 500개의 클라이언트 연결을 받아도 된다. 다만 PostgreSQL로 실제 나가는 서버 연결은 120 이내로 제한된다. 초과 요청은 애플리케이션 혹은 PgBouncer 앞단에서 대기하게 된다.

핵심은 이것이다.

> **DB는 대개 느슨한 무한 확장 계층이 아니다. 너무 많은 병렬성을 주는 것보다, 작은 병렬성을 예측 가능하게 운영하는 편이 더 안정적이다.**

### 3단계: reserve pool은 보험이지 기본 처리량 수단이 아니다

PgBouncer의 `reserve_pool_size`는 순간 피크에 대응하는 보험으로 유용하다. 하지만 이를 상시 처리량처럼 기대하면 결국 DB 연결 수가 다시 불어난다.

실무 기준으로는 이렇게 보는 편이 좋다.

- `default_pool_size`: 평상시 허용할 정상 처리량
- `reserve_pool_size`: 짧은 버스트 흡수용
- `reserve_pool_timeout`: 정말 필요한 경우에만 추가 풀 사용

즉 reserve pool이 자주 발동한다면 설정을 칭찬할 일이 아니라, **평상시 부하나 애플리케이션 병렬성 설계를 다시 봐야 한다**는 신호다.

---

## 실무 예시 3: 서버리스, 오토스케일 환경에서 PgBouncer가 더 중요한 이유

서버리스 함수나 aggressive autoscaling 환경에서는 개별 인스턴스가 오래 살아 있지 않는다. 즉 애플리케이션 내부 풀 자체가 효율적으로 재사용되기 어렵다. 이때 PostgreSQL 직접 연결은 특히 불리해진다.

- 짧게 살아나는 실행 단위가 매번 새 연결을 연다
- 콜드 스타트와 피크 시점이 겹치면 connection storm가 심해진다
- 인스턴스 수가 급격히 늘어도 DB는 그렇게 빠르게 늘지 않는다

이런 환경에서 PgBouncer는 단순 권장 사항이 아니라 **연결 폭주를 완충하는 보호 장치**에 가깝다.

다만 여기서도 주의할 점이 있다.

- 서버리스 함수가 너무 짧은 단위로 쪼개져 있고
- 각 함수가 retry를 공격적으로 수행하고
- 트랜잭션 시간이 길며
- PgBouncer 뒤 서버 풀도 작게 잡혀 있다면

문제는 여전히 생긴다. PgBouncer는 burst를 완화하지만, 애플리케이션이 과도한 동시성과 재시도를 만들면 결국 대기열과 타임아웃으로 돌아온다.

즉 PgBouncer는 필요 조건이지 충분 조건이 아니다.

---

## 핵심 개념 4: 어떤 기능이 transaction pooling과 충돌하는지 미리 분류해야 한다

실무 도입 전에 아래 항목을 점검하면 사고를 많이 줄일 수 있다.

### 1) Session-level SET

예를 들어 아래 코드는 위험하다.

```sql
SET statement_timeout = '5s';
SET search_path = tenant_a;
SET application_name = 'batch-worker';
```

트랜잭션 안에서 `SET LOCAL`로 짧게 쓰는 것은 상대적으로 안전하지만, 세션 전체에 상태를 남기는 방식은 transaction pooling과 맞지 않는다.

**대안**

- 가능한 경우 DSN 옵션, role 기본값, 함수 파라미터로 표현
- 트랜잭션 한정 설정은 `SET LOCAL` 사용
- 멀티테넌시 문맥은 세션 상태 대신 명시적 컬럼/파라미터로 전달

### 2) Temporary Table

temp table은 세션에 귀속된다. 따라서 transaction pooling에서 다음 트랜잭션이 다른 세션으로 이동하면 temp table 재사용 가정이 깨진다.

**대안**

- CTE, unlogged staging table, 명시적 작업 테이블 사용 검토
- 정말 필요하면 direct DB 또는 session pooling 별도 경로 사용

### 3) Advisory Lock

PostgreSQL advisory lock은 세션 단위와 트랜잭션 단위가 있다. transaction pooling에서는 세션 단위 락 사용이 특히 위험하다.

**대안**

- 가능하면 transaction-level advisory lock 사용
- 락 수명과 연결 수명이 정확히 일치하는지 검증
- 장기 락은 direct DB 경로로 분리

### 4) LISTEN / NOTIFY

LISTEN은 장기 세션 유지가 본질이다. transaction pooling 기본 경로에 넣으면 안 된다.

**대안**

- 이벤트 수신 프로세스는 direct DB 또는 session pooling 사용
- 일반 CRUD 요청 경로와 DSN 분리

### 5) Long-running Transaction

트랜잭션이 길면 당연히 서버 연결 점유 시간도 길어진다. transaction pooling의 장점은 짧은 트랜잭션에서 극대화된다.

**대안**

- 배치 청크 분할
- 외부 I/O를 트랜잭션 밖으로 분리
- 장기 분석/정산 작업은 별도 경로로 우회

이 목록은 체크리스트처럼 보이지만, 본질은 하나다.

> **세션을 저장소처럼 쓰지 말고, 필요한 상태를 SQL과 트랜잭션 안으로 명시적으로 가져오라**

---

## 설정 예시: 무난한 출발점과 각 값의 의미

아래는 개념 설명용으로 단순화한 예시다.

```ini
[databases]
app = host=127.0.0.1 port=5432 dbname=appdb pool_size=40 reserve_pool=10

[pgbouncer]
listen_addr = 0.0.0.0
listen_port = 6432
auth_type = scram-sha-256
auth_file = /etc/pgbouncer/userlist.txt
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 40
reserve_pool_size = 10
reserve_pool_timeout = 3
server_reset_query = DISCARD ALL
server_check_delay = 30
ignore_startup_parameters = extra_float_digits
```

각 값은 대략 이렇게 읽으면 된다.

### `pool_mode = transaction`

웹 요청 중심 서비스의 기본값 후보다. 다만 위에서 말한 세션 상태 의존 기능을 반드시 점검해야 한다.

### `max_client_conn`

PgBouncer에 붙을 수 있는 클라이언트 연결 상한이다. 이 값은 PostgreSQL 연결 수가 아니다. 너무 작으면 애플리케이션이 바로 접속 거절을 맞고, 너무 크면 대기 요청이 과도하게 쌓여 장애 전파가 길어질 수 있다.

즉 단순히 크게 잡는 것이 아니라, **애플리케이션 timeout 정책과 함께** 잡아야 한다.

### `default_pool_size`

실제 PostgreSQL로 유지할 기본 서버 연결 수다. 가장 중요한 값 중 하나다. 이 값은 인스턴스별 추정이 아니라 **DB 전체 예산**에서 역산해야 한다.

### `reserve_pool_size`

짧은 burst를 위한 추가 서버 연결이다. 상시 사용량처럼 잡지 말고 예외 처리용으로 생각하는 편이 안전하다.

### `server_reset_query = DISCARD ALL`

서버 연결을 다른 클라이언트에 넘기기 전에 세션 상태를 초기화하는 데 도움을 준다. 다만 모든 상황을 만능으로 해결해주진 않는다. 애초에 세션 상태 의존을 줄이는 것이 우선이다.

---

## 트레이드오프 1: Session Pooling은 편하지만, 가장 중요한 장점을 놓칠 수 있다

session pooling은 애플리케이션 호환성이 높다. 기존 코드가 세션 상태를 은근히 많이 써도 잘 동작할 가능성이 높다. 그래서 레거시 전환 초기에는 매력적이다.

하지만 session pooling은 연결 점유 단위가 세션 전체다. 즉 클라이언트가 idle이어도 해당 서버 연결이 사실상 묶여 있게 된다. 그러면 PgBouncer의 핵심 장점인 **짧은 트랜잭션 사이의 서버 연결 재사용 효율**이 크게 줄어든다.

실무적으로 보면 session pooling은 다음 상황에서 고려할 수 있다.

- 레거시 호환성이 최우선인 초기 마이그레이션 단계
- LISTEN/NOTIFY 같은 장기 세션 유지 워크로드
- 세션 상태 사용을 단기간에 제거하기 어려운 특수 작업

반대로 일반 웹 API 서비스 기본값으로 session pooling을 선택하면, 결국 "PgBouncer는 달았는데 DB 연결 수는 별로 안 줄었다"는 결과가 나오기 쉽다.

즉 session pooling은 틀린 선택이 아니라 **호환성을 위해 효율을 지불하는 선택**이다.

---

## 트레이드오프 2: Transaction Pooling은 효율적이지만, 애플리케이션 설계를 더 엄격하게 만든다

transaction pooling의 장점은 명확하다.

- 더 적은 서버 연결로 더 많은 요청 처리 가능
- connection storm 완충 효과가 큼
- 짧은 요청 중심 서비스에서 가장 실용적

대신 비용도 명확하다.

- 세션 상태 의존 패턴 제거 필요
- 드라이버/ORM prepared statement 전략 검증 필요
- 배치/마이그레이션/운영 작업 경로 분리 필요
- 장애 시 문제 원인이 앱, 드라이버, PgBouncer, PostgreSQL 중 어디인지 추적 난이도 상승

즉 transaction pooling은 단순 성능 옵션이 아니라 **아키텍처의 명시성 요구 수준을 높이는 선택**이다.

나는 대부분의 신규 서비스나 개선 가능한 서비스에서는 transaction pooling 쪽이 맞다고 본다. 다만 이것은 "그냥 바꾸면 된다"가 아니라, **세션 가정 제거 작업을 할 의지가 있을 때**만 그렇다.

---

## 흔한 실수 1: `max_connections`를 크게 열면 해결된다고 믿는 것

PostgreSQL이 연결을 더 많이 받도록 `max_connections`를 크게 늘리면 일시적으로는 경고가 사라질 수 있다. 하지만 다음 문제가 따라온다.

- 메모리 사용량 증가
- 프로세스 수 증가에 따른 컨텍스트 스위칭 증가
- lock 경합과 관리 비용 증가
- 장애 시 복구해야 할 연결 수 자체 증가

즉 "더 많이 받아준다"는 것이 "더 안정적이다"를 의미하지 않는다. 오히려 PostgreSQL은 너무 많은 동시 연결보다 **작고 잘 통제된 동시성**에서 더 안정적으로 동작하는 경우가 많다.

실무에서 우선순위는 보통 아래와 같다.

1. 정말 필요한 서버 연결 예산 산정
2. PgBouncer로 상한 통제
3. 애플리케이션 병렬성, timeout, retry 정책 조정
4. 그래도 필요할 때만 `max_connections` 조정

---

## 흔한 실수 2: 애플리케이션 풀과 PgBouncer 풀을 둘 다 크게 잡는 것

애플리케이션 자체에도 풀, PgBouncer에도 풀, PostgreSQL에도 높은 `max_connections`를 두면 표면상 여유 있어 보인다. 하지만 실제로는 문제가 세 겹으로 숨어든다.

- 애플리케이션은 빨리 연결을 잡으니 괜찮아 보임
- PgBouncer는 클라이언트 연결을 많이 받아주니 괜찮아 보임
- PostgreSQL은 어느 순간 갑자기 한계에 도달함

결국 병목은 뒤로 밀릴 뿐 사라지지 않는다. 더 나쁜 점은 **대기열이 여러 층에 나뉘어** 어디서 지연이 발생하는지 파악하기 어려워진다는 것이다.

원칙은 단순하다.

- 애플리케이션 풀은 필요한 만큼만
- PgBouncer 서버 풀은 DB 예산 기반으로 작게
- timeout과 backpressure는 앞단에서 빠르게

즉 시스템은 폭주를 "수용"하는 것보다, **어디서 얼마나 대기시키고 언제 실패시킬지 명확히** 하는 편이 낫다.

---

## 흔한 실수 3: 마이그레이션과 운영 스크립트까지 transaction pooling으로 태우는 것

스키마 마이그레이션 도구나 수동 관리 스크립트는 예상보다 세션/트랜잭션에 민감하다.

- DDL이 암묵적 커밋/락과 얽힘
- 마이그레이션 도구가 세션 상태를 기대함
- 배치 스크립트가 temp table이나 장기 트랜잭션 사용
- 운영자가 psql에서 인터랙티브하게 세션 상태를 쌓아가며 작업

이런 작업을 모두 transaction pooling에 밀어 넣으면 간헐 장애가 생기고, 문제 재현도 어렵다.

그래서 운영적으로는 반드시 아래 둘을 분리해두는 것이 좋다.

- **app read/write DSN**: PgBouncer 경유
- **admin direct DSN**: PostgreSQL 직접 연결

이 우회 경로는 비효율이 아니라 안전장치다.

---

## 흔한 실수 4: timeout과 retry를 PgBouncer 도입 후에도 그대로 두는 것

PgBouncer가 있으면 연결 부족 상황이 곧바로 PostgreSQL 오류로 드러나지 않고, 대기열과 timeout 형태로 나타날 수 있다. 이때 애플리케이션이 무분별하게 retry하면 문제가 증폭된다.

예를 들어:

- 풀 대기로 이미 2초 지연
- 애플리케이션 timeout은 5초
- 실패 후 즉시 3회 retry
- 워커도 같은 정책 사용

그러면 순간 피크가 자기증폭형 부하로 바뀐다.

따라서 PgBouncer 도입 시 함께 조정해야 할 것이 있다.

- 애플리케이션 connect/query timeout
- HTTP 요청 timeout
- retry 횟수와 backoff
- 워커 동시성
- 큐 소비 속도

연결 제어는 풀 하나의 문제가 아니라 **시스템 전체 backpressure 설계**의 일부다.

---

## 관측 포인트: PgBouncer를 붙였으면 무엇을 봐야 하는가

도입 후에는 단순히 에러가 없는지만 보면 부족하다. 적어도 아래는 꾸준히 봐야 한다.

### PgBouncer 레벨

- 현재 client connection 수
- 현재 server connection 수
- waiting client 수
- pool별 active / idle / used / tested 연결 수
- reserve pool 발동 빈도
- max client 근접 여부

### PostgreSQL 레벨

- 실제 backend 수
- active vs idle in transaction 세션 비율
- long-running transaction 수
- lock wait 증가 여부
- CPU / memory / context switch / load 변화

### 애플리케이션 레벨

- DB acquire latency
- query latency p95 / p99
- timeout rate
- retry rate
- 배포 직후/복구 직후 오류율

관측의 핵심은 평균값이 아니라 **burst 시점**이다. PgBouncer는 평시보다 피크 완충에서 가치가 드러난다. 따라서 배포 직후, 배치 시작 시각, 장애 복구 직후, 오토스케일 직후의 지표를 따로 보는 것이 좋다.

---

## 도입 절차: 가장 덜 위험한 순서

PgBouncer 전환을 한 번에 전체 서비스에 적용하면 원인 파악이 어렵다. 보통은 아래 순서가 안전하다.

### 1) 애플리케이션의 세션 상태 의존성 목록화

- search_path 변경 사용 여부
- temp table 사용 여부
- advisory lock 사용 여부
- prepared statement 전략
- LISTEN/NOTIFY 사용 여부
- 장기 트랜잭션 작업 목록

### 2) direct DSN과 pooled DSN 분리

코드와 배포 환경에 두 경로를 동시에 둔다. 그래야 일부 작업만 우회시키기 쉽다.

### 3) 비핵심 워크로드부터 검증

내부 API, 저위험 배치, staging 환경 부하 테스트부터 transaction pooling을 검증한다.

### 4) prepared statement 관련 드라이버 옵션 확인

운영 장애가 가장 자주 나는 지점이라, 이 단계는 반드시 별도 체크가 필요하다.

### 5) pool size를 보수적으로 시작

처음부터 크게 잡지 말고, DB 예산보다 작게 시작한 뒤 관측하며 올린다.

### 6) 배포/복구 시나리오를 실제로 리허설

정상 트래픽보다 재기동 시 burst에서 문제가 잘 드러난다.

나는 이 작업에서 특히 6번이 중요하다고 본다. 평상시 1시간이 아니라, **재기동 30초**가 진짜 구조를 보여주는 경우가 많다.

---

## 체크리스트: PgBouncer 도입 전후에 반드시 확인할 것

### 사전 점검

- [ ] PostgreSQL이 감당할 총 서버 연결 예산을 정했다
- [ ] 웹/API, 워커, 마이그레이션, 운영 스크립트의 연결 경로를 구분했다
- [ ] transaction pooling 사용 시 세션 상태 의존 기능 목록을 만들었다
- [ ] temp table, LISTEN/NOTIFY, 세션 advisory lock 사용 여부를 확인했다
- [ ] 드라이버/ORM의 prepared statement 전략을 확인했다
- [ ] direct DSN 우회 경로를 준비했다

### 설정 점검

- [ ] `pool_mode` 선택 이유가 명확하다
- [ ] `default_pool_size`가 DB 예산 기반으로 설정되어 있다
- [ ] `reserve_pool_size`를 상시 처리량이 아닌 버스트 보험으로 잡았다
- [ ] `max_client_conn`이 애플리케이션 timeout 정책과 함께 설계되었다
- [ ] 세션 초기화 전략(`server_reset_query` 등)을 검토했다

### 운영 점검

- [ ] PgBouncer waiting client 수를 모니터링한다
- [ ] PostgreSQL long-running transaction을 모니터링한다
- [ ] 배포 직후와 복구 직후 burst 지표를 따로 본다
- [ ] retry와 timeout 정책이 풀 대기와 충돌하지 않는지 확인했다
- [ ] 마이그레이션과 운영용 경로가 pooled 경로와 분리되어 있다

---

## 한 줄 정리

**PgBouncer의 핵심은 커넥션을 재사용하는 데 있지 않고, 애플리케이션의 불규칙한 동시성을 PostgreSQL이 감당 가능한 작은 서버 연결 집합으로 변환하는 데 있다.**

---

## 마무리: PgBouncer는 성능 트릭이 아니라, 세션 환상을 걷어내는 도구다

PgBouncer를 잘 쓰는 팀은 보통 PostgreSQL을 더 깊게 이해한 팀이다. 반대로 PgBouncer를 붙였는데 계속 문제를 겪는 팀은 대개 세션 상태, 트랜잭션 경계, prepared statement, 배치 특성 같은 전제를 충분히 드러내지 못한 경우가 많다.

실무 기준으로 정말 중요한 질문은 이것이다.

- 우리 서비스는 세션이 아니라 트랜잭션 중심으로 설계돼 있는가?
- DB 연결 수를 앱 인스턴스 수가 아니라 DB 예산으로 제어하고 있는가?
- 예외적인 작업을 우회시킬 경로가 준비돼 있는가?

이 세 질문에 명확히 답할 수 있다면 PgBouncer는 꽤 큰 효과를 준다. 특히 오토스케일, 워커 혼재, 피크 변동성이 큰 환경에서는 더 그렇다.

반대로 이 질문에 답하지 못한 채 "일단 앞단에 붙여보자"로 시작하면, PgBouncer는 최적화 도구가 아니라 또 하나의 장애 지점이 된다.

결국 핵심은 설정 파일 몇 줄이 아니다.

> **세션을 믿지 말고 트랜잭션을 설계하라. 연결 수는 희망이 아니라 예산으로 통제하라.**
