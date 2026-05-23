---
layout: post
title: "PostgreSQL timeout 설계 실전: statement_timeout, lock_timeout, idle_in_transaction_session_timeout, transaction_timeout로 장애 반경 줄이는 법"
date: 2026-05-23 11:40:00 +0900
categories: [sql]
tags: [study, sql, postgresql, statement-timeout, lock-timeout, idle-in-transaction, transaction-timeout, reliability, operations, performance]
permalink: /sql/2026/05/23/study-postgresql-timeout-budget-statement-lock-idle-in-transaction-transaction.html
---

## 배경: PostgreSQL 장애는 느린 쿼리 하나보다 "언제까지 기다리게 둘 것인가"에서 더 자주 커진다

운영 중인 PostgreSQL을 보다 보면 성능 문제를 대개 인덱스, 실행 계획, vacuum, 디스크 I/O로 먼저 설명하게 된다. 물론 그 방향은 맞다. 하지만 실제 장애 전파를 보면 그보다 더 직접적인 질문이 하나 있다.

> **이 세션과 이 쿼리를, 시스템은 얼마나 오래 기다리게 둘 것인가?**

많은 팀이 이 질문을 뒤로 미룬다. 그러다 아래 같은 장면을 반복해서 만난다.

- 온라인 API는 2초 SLA인데 DB에서는 40초까지 묵묵히 기다린다.
- 배치가 잡은 락 하나 때문에 웹 요청 수백 개가 줄줄이 대기열로 쌓인다.
- 애플리케이션은 timeout이 났다고 생각했는데 DB 안에서는 트랜잭션이 계속 살아 있다.
- ORM 세션이 `BEGIN` 이후 한참 idle 상태로 남아 autovacuum을 밀어낸다.
- 마이그레이션은 실제 DDL보다 락 대기 시간 때문에 더 위험해진다.
- 재시도 로직은 붙어 있는데, 실패를 너무 늦게 감지해서 동시성 폭탄만 키운다.
- connection pool은 멀쩡해 보여도 내부적으로는 "끝나지 않는 기다림"이 워커를 잠식한다.

이런 문제는 쿼리 문법만으로 해결되지 않는다. 핵심은 **시간 예산을 어디서 끊고, 어떤 종류의 기다림을 허용하고, 어떤 기다림은 즉시 실패로 되돌릴지 설계하는 것**이다.

PostgreSQL에는 이를 위해 몇 가지 중요한 timeout이 있다.

- `statement_timeout`
- `lock_timeout`
- `idle_in_transaction_session_timeout`
- `transaction_timeout`

이 설정들은 모두 "시간 제한"처럼 보이지만, 보호하는 대상과 의미가 완전히 다르다. 이 차이를 이해하지 못하면 흔히 두 극단으로 간다.

1. timeout을 거의 안 써서 장애 반경이 불필요하게 커진다.
2. timeout을 무작정 짧게 둬서 정상 부하에서도 취소와 재시도만 늘어난다.

오늘 글은 이 네 설정을 개별 옵션 설명으로 끝내지 않고, **API 요청, 워커, 배치, 마이그레이션, pooler, 관측성**까지 연결해서 운영 기준으로 정리한다.

이번 글에서 답하려는 질문은 아래와 같다.

1. 각 timeout은 정확히 무엇을 끊는가?
2. `statement_timeout`과 `lock_timeout`은 왜 같은 숫자로 두면 안 되는가?
3. `idle_in_transaction_session_timeout`은 왜 성능 옵션이 아니라 데이터베이스 위생 규칙에 가까운가?
4. `transaction_timeout`은 언제 유용하고, 사용 중인 PostgreSQL 버전과 왜 함께 봐야 하는가?
5. 전역 기본값, role 단위, 세션 단위, `SET LOCAL` 중 무엇을 어디에 써야 안전한가?
6. 애플리케이션 재시도, idempotency, connection pooling과 timeout은 어떻게 같이 설계해야 하는가?
7. 실무에서 가장 흔한 실수는 무엇인가?

핵심 결론만 먼저 말하면 이렇다.

1. timeout은 느린 쿼리를 벌주는 옵션이 아니라 **장애 반경을 제한하는 가드레일**이다.
2. `statement_timeout`은 작업 전체 예산이고, `lock_timeout`은 "락 때문에 기다리는 시간"만 제한한다.
3. `idle_in_transaction_session_timeout`이 없으면 애플리케이션 실수 하나가 vacuum, bloat, lock hold를 오래 끌 수 있다.
4. `transaction_timeout`은 최신 PostgreSQL 계열에서 긴 트랜잭션 수명을 직접 자를 수 있는 추가 안전장치지만, 버전 지원과 워크로드 특성을 확인해야 한다.
5. timeout은 전역 숫자 하나로 해결하는 일이 아니라 **워크로드별 시간 정책을 나누는 일**이다.
6. 재시도와 timeout은 세트다. timeout만 짧게 두고 idempotency 없이 재시도하면 장애를 더 빨리 증폭시킨다.
7. 가장 좋은 timeout 설계는 "무조건 짧게"가 아니라 **빠르게 실패해야 하는 경로와 오래 가도 되는 경로를 분리**하는 것이다.

---

## 먼저 큰 그림: timeout은 "느린 쿼리 차단기"가 아니라 시간 예산 분배기다

많은 팀이 timeout을 도입할 때 사고방식이 이렇다.

- 오래 걸리면 끊자
- 너무 느리면 죽이자
- 어차피 느린 쿼리는 나쁘니 빨리 실패하게 만들자

절반만 맞는 말이다.

실무에서 timeout이 진짜 필요한 이유는 단순히 "느린 작업 제거"가 아니다. 더 본질적인 이유는 아래 세 가지다.

### 1) 기다림에도 종류가 다르다

DB에서 느린 현상은 하나로 뭉뚱그려지기 쉽지만 실제로는 다르다.

- CPU를 쓰며 실제로 실행 중인 쿼리
- 디스크 I/O를 기다리는 쿼리
- 락을 기다리며 멈춘 쿼리
- 클라이언트 입력을 기다리며 열린 트랜잭션
- connection pool에서 재사용될 줄 알았는데 방치된 세션

각 경우에 적절한 timeout은 다르다.

예를 들어 락 대기 때문에 5초를 잃는 요청은, 실제 실행 시간 5초짜리 보고서 쿼리와 같은 정책으로 다뤄선 안 된다.

### 2) 응답 시간 예산은 애플리케이션과 DB가 같이 써야 한다

API SLA가 1.5초인데 애플리케이션 HTTP 클라이언트 timeout은 1.2초, PostgreSQL `statement_timeout`은 0, reverse proxy timeout은 30초라면 어떻게 될까?

가장 흔한 결과는 이렇다.

- 사용자나 상위 서비스는 이미 실패로 간주한다.
- DB는 뒤늦게 성공하거나 계속 실행한다.
- 후속 재시도가 겹쳐 중복 부하를 만든다.
- 개발자는 "응답은 실패인데 DB에는 반영됨" 같은 불편한 상태를 만나게 된다.

즉 timeout은 DB 내부 숫자가 아니라 **시스템 전체 deadline 체인**의 일부다.

### 3) timeout은 장애 전파 속도를 줄이는 장치다

락 대기와 장기 트랜잭션은 전염성이 있다.

- 하나의 장기 DDL 대기가 세션 수백 개를 묶는다.
- 하나의 idle transaction이 vacuum을 늦춘다.
- 하나의 느린 배치가 pool 자원을 오래 붙잡는다.
- 하나의 retry 폭주가 더 많은 lock wait를 만든다.

좋은 timeout은 개별 쿼리를 혼내는 도구가 아니라, **한 문제를 전체 시스템 문제로 번지지 않게 자르는 장치**다.

---

## timeout 관련 설정을 먼저 구분하자: 비슷해 보여도 끊는 대상이 다르다

운영 대화에서 가장 먼저 해야 할 일은 이름이 비슷한 설정들을 역할별로 구분하는 것이다.

| 설정 | 무엇을 끊는가 | 시간 측정 기준 | 주로 보호하는 것 | 대표 용도 |
| --- | --- | --- | --- | --- |
| `statement_timeout` | 너무 오래 걸리는 statement | 서버에 명령이 도착한 시점부터 완료까지 | 요청 전체 시간 예산 | API, 배치, 관리 쿼리 상한 |
| `lock_timeout` | 락 대기 중인 statement | 락 획득을 기다리는 시간만 | lock convoy 확산 방지 | 온라인 요청, DDL fast-fail |
| `idle_in_transaction_session_timeout` | 열린 트랜잭션 안에서 놀고 있는 세션 | 트랜잭션을 연 채 클라이언트 입력을 기다리는 시간 | vacuum, lock, bloat 보호 | ORM, 수동 SQL, 장시간 idle session 방지 |
| `transaction_timeout` | 너무 오래 지속된 트랜잭션을 가진 세션 | 트랜잭션 전체 수명 | 긴 트랜잭션 누수 억제 | 최신 PostgreSQL에서 추가 safety net |

여기서 중요한 포인트는 두 가지다.

1. **모두 timeout이지만, 서로 대체재가 아니다.**
2. **같은 숫자를 일괄 적용하면 보통 틀린다.**

예를 들어 `statement_timeout=2s` 하나만 두고 안심하면 다음 문제가 남는다.

- 락 때문에 1.9초를 기다리다 실제 쿼리는 5ms 만에 끝나도 사용자 입장에서는 느리다.
- 열린 트랜잭션이 idle 상태로 30분 남아 있으면 autovacuum에는 여전히 해롭다.
- 보고서 쿼리처럼 실제로 20초가 필요한 워크로드는 불필요하게 다 실패한다.

반대로 `idle_in_transaction_session_timeout`만 켜고 `lock_timeout`이 없으면, 트랜잭션을 연 채 일하지 않는 세션은 잘리더라도 **현재 락 대기 중인 온라인 요청의 폭증**은 막지 못한다.

즉 이 설정들은 경쟁 관계가 아니라 **서로 다른 종류의 위험을 덮는 레이어**다.

---

## 핵심 개념 1: `statement_timeout`은 "쿼리 속도"보다 "업무 deadline"과 맞춰야 한다

PostgreSQL 공식 문서 기준으로 `statement_timeout`은 **명령이 서버에 도착한 시점부터 완료될 때까지**의 시간을 잰다. 단위 없는 숫자는 밀리초다. 기본값 0은 비활성화다.

이 설정을 볼 때 가장 중요한 오해는 이것이다.

> `statement_timeout`은 느린 SQL만 자르는 옵션이다.

정확히는 다르다. 이 값은 **정상적으로 오래 걸리는 작업과 비정상적으로 오래 걸리는 작업을 모두 자를 수 있는 상한선**이다. 그래서 성능 값이 아니라 **업무 deadline 값**으로 다뤄야 한다.

### `statement_timeout`이 특히 유용한 경우

- 사용자 요청 지연 상한이 명확한 API
- queue consumer가 한 건 처리에 너무 오래 매달리면 안 되는 경우
- ad-hoc 관리 쿼리가 실수로 무한 대기/과도한 full scan에 빠질 수 있는 경우
- 데이터 수정 쿼리가 예상보다 오래 가면 상위 레이어가 이미 취소했을 가능성이 큰 경우

### `statement_timeout`만으로는 부족한 경우

- 락 대기와 실제 실행 시간을 구분해야 할 때
- 대기 자체가 더 위험한 온라인 경로
- 인간이 일부러 오래 돌리는 배치/분석 쿼리
- transaction을 열고 중간에 애플리케이션이 멈추는 패턴

### 가장 흔한 실수: DB timeout이 애플리케이션 timeout보다 길다

예를 들어 이런 구성이 있다고 하자.

- API gateway timeout: 2s
- 애플리케이션 DB call timeout: 1.8s
- PostgreSQL `statement_timeout`: 30s

이 구성은 겉보기엔 넉넉해 보이지만 실제로는 위험하다.

- 사용자는 2초 뒤 실패를 본다.
- DB는 최대 30초까지 계속 실행한다.
- 같은 요청이 재시도되면 중복 부하가 생긴다.
- 쓰기 요청이면 "실패처럼 보였는데 실제 반영됨"이 나온다.

실무 기본 원칙은 단순하다.

> **DB의 `statement_timeout`은 상위 호출 체인의 기대 시간보다 같거나 조금 더 짧아야 한다.**

단, 너무 촘촘하게 맞추면 네트워크 변동과 애플리케이션 직렬화 시간 때문에 거짓 실패가 늘 수 있다. 보통은 아래처럼 계단형 예산을 둔다.

- 사용자-facing API 전체 예산: 1500ms
- 앱 내부 비즈니스 처리 + 직렬화: 300ms
- DB 구간 예산: 700~900ms
- 외부 API 예산: 300~500ms

즉 `statement_timeout`은 SQL 튜닝 값이 아니라 **요청 시간 예산의 일부로 나눠진 몫**이어야 한다.

### 실무 팁: 글로벌보다 role / 세션 / `SET LOCAL`이 더 안전하다

공식 문서도 `postgresql.conf`에서 전역 `statement_timeout`을 설정하는 것을 추천하지 않는다. 이유는 모든 세션에 무차별 적용되기 때문이다.

예를 들어 다음 세 작업은 timeout 정책이 달라야 한다.

- 웹 API 읽기/쓰기 요청
- 백오피스 대량 export
- 운영자 수동 점검 쿼리

그래서 보통 다음 우선순위를 권한다.

1. 가능한 경우 **role별 기본값**으로 큰 정책을 나눈다.
2. 더 세밀한 경우 **애플리케이션 세션 단위 설정**을 둔다.
3. 특정 트랜잭션에만 다른 예산이 필요하면 **`SET LOCAL`**을 쓴다.

예:

```sql
BEGIN;
SET LOCAL statement_timeout = '900ms';
-- 이 트랜잭션 안의 핵심 mutation
UPDATE orders
SET status = 'PAID'
WHERE id = $1;
COMMIT;
```

이 패턴의 장점은 timeout 정책이 코드 유스케이스와 가까이 붙는다는 점이다.

---

## 핵심 개념 2: `lock_timeout`은 "락 때문에 기다리는 시간"만 자른다

`lock_timeout`은 매우 자주 과소평가되지만, 온라인 서비스에서는 `statement_timeout`만큼 중요할 때가 많다.

공식 문서 기준으로 `lock_timeout`은 **테이블, 인덱스, row, 기타 DB object 락을 기다리는 시간**만 잰다. 실제 쿼리 실행 시간에는 적용되지 않는다. 또한 **락 획득 시도마다 별도로** 적용된다.

즉 다음 둘은 완전히 다르다.

- 1.8초 동안 실제로 CPU/I/O를 써서 실행된 쿼리
- 1.8초 동안 락을 기다리다 마지막 5ms만 실행한 쿼리

사용자 체감은 비슷할 수 있어도 운영 의미는 다르다.

### 왜 `lock_timeout`이 중요한가

락 대기는 단순 느림이 아니라 **줄서기 증폭기**다.

예를 들어 배치 하나가 특정 row 집합을 오래 잡고 있고, 온라인 요청이 같은 row를 건드린다고 하자.

`lock_timeout`이 없으면 온라인 요청은 순서대로 계속 기다린다. 그 사이:

- 앱 워커 스레드/프로세스가 점유된다.
- connection pool 슬롯이 묶인다.
- 상위 요청이 timeout 나며 재시도가 발생한다.
- 뒤늦게 락이 풀려도 이미 사용자 요청은 실패했을 수 있다.
- 같은 row에 더 많은 세션이 몰려 convoy가 생긴다.

짧은 `lock_timeout`은 이 줄서기를 빠르게 끊어 준다.

### `statement_timeout`과 `lock_timeout`의 관계

공식 문서가 분명히 말하는 포인트가 있다.

> `statement_timeout`이 켜져 있을 때 `lock_timeout`을 같거나 더 크게 두는 것은 대체로 의미가 없다.

왜냐하면 더 먼저 발동하는 것은 결국 `statement_timeout`이기 때문이다.

실무적으로는 보통 이렇게 잡는다.

- `statement_timeout`: 요청 전체 상한
- `lock_timeout`: 그보다 훨씬 짧은 fast-fail 값

예:

- 웹 요청: `statement_timeout=1200ms`, `lock_timeout=100ms`
- 운영성 DDL: `statement_timeout=20min`, `lock_timeout=2s`
- 큐 워커: `statement_timeout=10s`, `lock_timeout=50ms` 또는 `NOWAIT/SKIP LOCKED`

즉 `lock_timeout`은 "이 작업 전체가 얼마나 오래 갈 수 있는가"가 아니라, **"락 때문에 이렇게 오래 기다릴 가치가 있는가"**에 대한 답이다.

### 자주 헷갈리는 것: `deadlock_timeout`은 대기 상한이 아니다

운영자들이 종종 `deadlock_timeout`을 `lock_timeout` 대용으로 오해한다. 하지만 성격이 다르다.

- `lock_timeout`: 일정 시간 이상 락 대기하면 statement를 중단
- `deadlock_timeout`: deadlock 검사를 언제 시작할지 관련된 내부 타이밍

즉 lock wait fast-fail을 원한다면 `deadlock_timeout`이 아니라 `lock_timeout`을 봐야 한다.

---

## 핵심 개념 3: `idle_in_transaction_session_timeout`은 성능 옵션이 아니라 "DB 위생 규칙"이다

실무에서 가장 조용하게 시스템을 망가뜨리는 패턴 중 하나는 **열린 트랜잭션 안에서 아무 일도 하지 않는 세션**이다.

공식 문서 기준으로 `idle_in_transaction_session_timeout`은 **트랜잭션을 연 상태에서 클라이언트 질의를 기다리며 idle 상태인 세션**을 일정 시간 뒤 종료한다.

이게 중요한 이유는 열린 트랜잭션이 단지 "유휴 연결"이 아니기 때문이다.

### idle transaction이 해로운 이유

#### 1) 락을 오래 잡을 수 있다

꼭 큰 락이 아니더라도, row lock이나 metadata lock이 오래 남으면 다른 세션 대기열을 만든다.

#### 2) vacuum이 dead tuple을 회수하지 못할 수 있다

열린 트랜잭션은 과거 스냅샷을 붙잡는다. 그러면 최근 dead tuple 중 일부를 vacuum이 바로 치우지 못한다. 결과적으로 bloat와 visibility 문제로 이어질 수 있다.

#### 3) 애플리케이션 버그가 드러나지 않고 누적된다

ORM 세션 관리 실수, `BEGIN` 후 예외 경로 누락, 수동 SQL 작업 중 커피 마시러 간 운영자 같은 패턴이 quietly 쌓인다.

#### 4) 장기적으로는 읽기 경로에도 영향을 준다

autovacuum 지연, visibility map 정체, dead tuple 누적은 결국 read path 품질에도 번진다. 즉 이 설정은 단순 hygiene가 아니라 성능 보호 장치이기도 하다.

### 왜 `idle_session_timeout`으로 대체하면 안 되나

`idle_session_timeout`은 트랜잭션 바깥에서 그냥 idle인 세션도 끊는다. 그러나 공식 문서도 pooler나 middleware와 함께 쓸 때는 주의를 권한다. 특히 PgBouncer 같은 계층이 있으면 예상치 못한 연결 종료와 충돌할 수 있다.

반면 `idle_in_transaction_session_timeout`은 훨씬 더 명확하다.

- 그냥 쉬고 있는 연결 전체가 문제는 아니다.
- **트랜잭션을 연 채 쉬고 있는 연결**이 문제다.

그래서 대부분의 애플리케이션에서는 `idle_session_timeout`보다 `idle_in_transaction_session_timeout`이 먼저다.

### 실무 감각: 이 값은 생각보다 짧아도 된다

웹 애플리케이션, API 서버, queue worker 기준으로 정상적인 트랜잭션이 열린 채 몇 분씩 idle인 경우는 거의 없다. 있다면 대개 버그거나 부적절한 작업 방식이다.

그래서 다음 같은 기준을 많이 쓴다.

- 웹/워커 role: 15s ~ 60s
- 운영 콘솔/수동 세션: 60s ~ 수분
- 장시간 인터랙티브 분석 세션: 별도 role로 분리

핵심은 "길게 잡아야 안전하다"가 아니다. 오히려 **짧게 잡아야 버그를 빨리 드러낸다**.

---

## 핵심 개념 4: `transaction_timeout`은 긴 트랜잭션 수명 자체를 잘라내는 최신 safety net이다

최신 PostgreSQL 문서에는 `transaction_timeout`이 있다. 이 설정은 **너무 오래 지속된 트랜잭션을 가진 세션 자체를 종료**한다. 명시적 `BEGIN`뿐 아니라 statement 하나가 암묵적으로 여는 transaction에도 적용된다.

이 설정이 유용한 이유는 아래와 같다.

- `statement_timeout`은 개별 statement 기준이다.
- `idle_in_transaction_session_timeout`은 idle 상태일 때만 본다.
- 하지만 실제 장애는 **여러 statement를 거치며 오래 살아 있는 트랜잭션**에서도 발생한다.

예를 들어 이런 흐름을 생각해 보자.

1. 트랜잭션 시작
2. 읽기 쿼리 하나 수행
3. 애플리케이션 내부 계산/외부 API 호출
4. 추가 쿼리 수행
5. 잠시 idle
6. 다시 업데이트
7. 커밋

이 경로는 각 statement가 짧아도 transaction 전체 수명이 비정상적으로 길 수 있다.

### 언제 특히 유용한가

- ORM이나 서비스 코드가 트랜잭션 범위를 지나치게 넓게 잡는 경우
- 대량 작업이 청크로 나뉘어야 하는데 하나의 transaction으로 길게 묶이는 경우
- 사람이 개입하는 승인 흐름이나 외부 API 응답을 transaction 안에서 기다리는 안티패턴
- 배치 코드가 중간 중간 SQL을 쉬엄쉬엄 실행해 `statement_timeout`을 교묘히 피해 가는 경우

### 주의할 점 1: 버전 지원을 확인해야 한다

`transaction_timeout`은 상대적으로 새로운 축에 속하므로, 사용 중인 PostgreSQL 메이저 버전에서 지원 여부를 먼저 확인해야 한다. 문서에 있다고 해서 모든 운영 환경에 당장 있는 것은 아니다. RDS, Cloud SQL, 사내 표준 버전, 확장 호환성까지 함께 확인하는 편이 안전하다.

### 주의할 점 2: 다른 timeout과의 관계가 있다

공식 문서 기준으로 `transaction_timeout`이 `idle_in_transaction_session_timeout` 또는 `statement_timeout`보다 짧거나 같으면 더 긴 쪽은 사실상 의미가 없어질 수 있다.

따라서 실무에서는 역할을 명확히 나눈다.

- `statement_timeout`: 개별 작업 상한
- `lock_timeout`: 락 대기 fast-fail
- `idle_in_transaction_session_timeout`: idle leak 차단
- `transaction_timeout`: 긴 transaction lifespan 차단

즉 `transaction_timeout`은 **나머지 설정의 대체재가 아니라 마지막 safety net**에 가깝다.

---

## 핵심 개념 5: timeout은 설정 위치와 우선순위까지 설계해야 한다

같은 숫자라도 **어디에 설정하느냐**에 따라 운영 의미가 달라진다.

PostgreSQL timeout은 보통 아래 레벨에서 만진다.

1. `postgresql.conf`
2. `ALTER SYSTEM`
3. `ALTER DATABASE`
4. `ALTER ROLE`
5. `ALTER ROLE ... IN DATABASE ...`
6. 세션 접속 후 `SET`
7. 트랜잭션 안의 `SET LOCAL`

실무에서 중요한 건 단순 우선순위 암기가 아니라 **정책의 지속 범위**를 이해하는 것이다.

### 전역 기본값은 "최소 안전망"에 가깝다

전역값은 가장 넓게 적용되므로 강력하지만, 동시에 가장 둔하다.

전역 설정에 어울리는 것은 보통 아래처럼 거의 모든 세션에 공통으로 적용해도 되는 안전장치다.

- 아주 과도한 장기 idle transaction 차단
- 정말 말도 안 되게 긴 transaction lifespan 차단
- 운영 정책상 절대 허용하지 않을 상한선

반대로 전역 설정에 바로 넣기 조심해야 하는 것은 아래다.

- 온라인 API 전용 짧은 `statement_timeout`
- 특정 배치만을 위한 긴 timeout
- DDL 작업 전용 짧은 `lock_timeout`

### role 단위 기본값은 워크로드 정책을 표현하기 좋다

애플리케이션 계정을 역할별로 분리해 두었다면 `ALTER ROLE`은 아주 좋은 기본 도구다.

예:

```sql
ALTER ROLE app_web
  SET statement_timeout = '1200ms';
ALTER ROLE app_web
  SET lock_timeout = '120ms';
ALTER ROLE app_web
  SET idle_in_transaction_session_timeout = '30s';

ALTER ROLE app_worker
  SET statement_timeout = '10s';
ALTER ROLE app_worker
  SET lock_timeout = '50ms';
ALTER ROLE app_worker
  SET idle_in_transaction_session_timeout = '30s';
```

이 방식의 장점은 다음과 같다.

- 앱 코드에 모든 기본값을 흩뿌리지 않아도 된다.
- 같은 클러스터 안에서 lane을 분리하기 쉽다.
- 누가 어떤 정책으로 붙는지 운영자가 읽기 쉽다.

### `SET LOCAL`은 유스케이스 단위 override에 가장 안전하다

같은 웹 앱 안에서도 어떤 요청은 일반 조회고, 어떤 요청은 관리자 일괄 승인일 수 있다. 이때 세션 전체 timeout을 바꾸는 것보다 transaction-local override가 더 안전하다.

```sql
BEGIN;
SET LOCAL statement_timeout = '8s';
SET LOCAL lock_timeout = '200ms';

-- 관리자 일괄 승인
UPDATE approvals
SET status = 'APPROVED', approved_at = now()
WHERE batch_id = $1
  AND status = 'PENDING';

COMMIT;
```

이 패턴은 특히 PgBouncer transaction pooling과도 궁합이 좋다. 설정이 트랜잭션 경계 안에서만 살아 있기 때문이다.

### 우선순위 자체보다 더 중요한 질문

- 이 timeout이 **모든 요청의 기본값**인가?
- 아니면 **특정 역할의 정책**인가?
- 아니면 **딱 한 use case의 예외값**인가?

이 질문에 답하지 못한 채 값만 바꾸면, 시간이 지나면 누가 왜 이 값을 넣었는지 설명이 안 된다.

---

## 핵심 개념 6: timeout은 전역값 하나보다 "워크로드별 lane 분리"가 먼저다

timeout 설계가 자주 실패하는 이유는 설정 값보다 먼저 **트래픽 종류를 분리하지 않기 때문**이다.

같은 PostgreSQL 클러스터 안에도 보통 여러 종류의 작업이 섞여 있다.

- 사용자-facing 읽기 API
- 사용자-facing 쓰기 API
- 비동기 워커/컨슈머
- 관리 배치/백필
- 스키마 마이그레이션
- 분석/리포트 쿼리
- 운영자 수동 접속

이걸 모두 같은 timeout 정책으로 다루면 꼭 한쪽이 깨진다.

### 권장 접근: 최소 3개 lane으로 나누기

#### 1) 온라인 lane

- 짧은 `statement_timeout`
- 더 짧은 `lock_timeout`
- 짧은 `idle_in_transaction_session_timeout`
- 필요 시 role 단위 설정

#### 2) 백그라운드/배치 lane

- 온라인보다 긴 `statement_timeout`
- 락 경쟁을 피해야 하면 여전히 짧은 `lock_timeout`
- 청크 처리 중심
- 트랜잭션 범위를 더 잘게 자름

#### 3) 운영/분석 lane

- 별도 사용자 또는 별도 접속 경로
- 긴 쿼리를 허용하되, 온라인 lane과 격리
- 가능하면 replica나 별도 warehouse 사용 검토

이 분리 없이는 timeout이 아니라 **업무 우선순위 충돌**이 일어난다.

---

## 실무 예시 1: 사용자-facing API는 `statement_timeout`보다 `lock_timeout`이 더 짧아야 한다

전자상거래 주문 상태 변경 API를 생각해 보자.

요구사항:

- 전체 응답 SLA 1.5초
- 사용자 체감상 300ms 이상 lock wait는 거의 허용하기 싫음
- 중복 제출이 가능하므로 idempotency key 존재

이때 자주 나오는 잘못된 설정은 아래다.

- `statement_timeout = 1500ms`
- `lock_timeout = 0`

이렇게 두면 실제 실행은 10ms짜리 쿼리라도 락 때문에 1.4초를 기다릴 수 있다. 사용자는 매우 느리다고 느끼고, 애플리케이션은 재시도를 고민하게 된다.

더 나은 접근은 이렇다.

```sql
BEGIN;
SET LOCAL statement_timeout = '900ms';
SET LOCAL lock_timeout = '120ms';

UPDATE orders
SET status = 'PAID', paid_at = now()
WHERE id = $1
  AND status = 'PENDING';

COMMIT;
```

이 조합의 의미는 명확하다.

- 락이 바로 안 잡히면 120ms 안에 실패한다.
- 락을 잡은 뒤 실제 실행도 900ms 안에 끝나야 한다.
- 실패 시 애플리케이션은 idempotency key 기준으로 안전하게 재조회/재시도 여부를 판단한다.

### 왜 좋은가

- lock convoy를 빨리 끊는다.
- pool 자원을 오래 묶지 않는다.
- 애플리케이션 재시도 정책과 정렬된다.
- 사용자는 "무한히 대기하다 실패" 대신 빠른 실패를 본다.

### 전제 조건

- 재시도 가능성 판단이 있어야 한다.
- 중복 결제/중복 발송을 막는 idempotency 또는 상태 전이 검증이 있어야 한다.
- 비즈니스적으로 "잠깐 후 다시 시도"가 가능한 경로여야 한다.

즉 timeout은 혼자 설 수 없고 **정합성 설계와 같이 가야 한다**.

---

## 실무 예시 2: 큐 워커는 락을 기다리기보다 `SKIP LOCKED`와 짧은 timeout을 선호한다

큐 테이블에서 작업을 뽑는 워커가 있다고 하자.

나쁜 패턴은 여러 워커가 같은 작업 후보를 오래 기다리는 것이다.

```sql
SELECT id
FROM job_queue
WHERE status = 'READY'
ORDER BY id
LIMIT 1
FOR UPDATE;
```

이 구조는 락 대기를 쉽게 만든다. 워커성 처리에서는 보통 **기다리기보다 다른 일을 하는 쪽**이 낫다.

```sql
WITH picked AS (
  SELECT id
  FROM job_queue
  WHERE status = 'READY'
  ORDER BY id
  LIMIT 100
  FOR UPDATE SKIP LOCKED
)
UPDATE job_queue q
SET status = 'RUNNING', started_at = now()
FROM picked
WHERE q.id = picked.id
RETURNING q.id;
```

여기에 timeout을 같이 두면 더 안전해진다.

```sql
BEGIN;
SET LOCAL statement_timeout = '5s';
SET LOCAL lock_timeout = '50ms';
-- 또는 NOWAIT / SKIP LOCKED 우선
...
COMMIT;
```

### 왜 queue worker에서 중요한가

- 워커는 보통 사람이 기다리는 요청보다 재시도/다른 작업 전환이 쉽다.
- 한 건에 오래 매달리는 것보다 전체 throughput이 중요하다.
- lock wait가 길면 같은 consumer group 전체가 느려질 수 있다.

### 여기서 자주 하는 실수

- `lock_timeout` 없이 단순히 워커 수만 늘린다.
- 같은 transaction 안에서 외부 API 호출까지 수행한다.
- statement가 취소되면 그대로 무한 재시도한다.

워커 timeout 정책의 핵심은 **빨리 포기하고, 안전하게 다시 집는다**다.

---

## 실무 예시 3: 무중단 DDL은 `statement_timeout`을 길게, `lock_timeout`을 짧게 둬야 한다

운영 중 스키마 변경에서 가장 위험한 대목은 종종 실제 실행 시간이 아니라 **시작 전에 락을 기다리는 시간**이다.

예를 들어 인덱스 생성, 제약 추가, 컬럼 변경 같은 작업을 할 때 이런 실수가 많다.

- `statement_timeout = 30min`
- `lock_timeout = 0`

이렇게 두면 DDL은 20분 내내 "아직 시작도 못 하고 락만 기다리며" 서비스에 긴 그림자를 드리울 수 있다.

더 안전한 접근은 아래다.

```sql
SET statement_timeout = '30min';
SET lock_timeout = '2s';

ALTER TABLE orders
ADD COLUMN exported_at timestamptz;
```

이 조합의 의미는 명확하다.

- 실제 작업 자체는 오래 걸려도 된다.
- 하지만 락을 바로 못 잡는다면 지금은 실행할 타이밍이 아니다.
- 즉시 실패하고 더 한가한 시점에 재시도한다.

### 왜 이 패턴이 중요한가

DDL은 실패보다 **애매하게 오래 기다리다 결국 영향을 주는 상태**가 더 나쁘다.

특히 online traffic과 겹치면 다음이 발생한다.

- DDL이 락을 기다린다.
- 뒤의 세션들이 연쇄적으로 대기한다.
- 앱 timeout과 retry가 겹친다.
- 운영자는 "DDL이 원인인지, 원래 트래픽 증가인지"를 헷갈린다.

그래서 운영성 DDL에서는 `statement_timeout`을 넉넉히 주되, **`lock_timeout`은 공격적으로 짧게** 두는 것이 일반적인 기본값이다.

---

## 실무 예시 4: ORM 기반 웹 앱은 `idle_in_transaction_session_timeout`으로 버그를 빨리 드러내야 한다

많은 웹 앱이 아래와 같은 실수를 조용히 갖고 있다.

1. 요청 시작 시 트랜잭션 오픈
2. 비즈니스 로직 중간에 외부 HTTP 호출
3. 예외 처리 한 갈래에서 rollback/close 누락
4. 세션이 열린 채 반환 또는 idle 상태로 남음

개발 환경에서는 잘 드러나지 않는다. 트래픽이 적고 autovacuum 압력도 낮기 때문이다. 하지만 운영에서는 다음 징후로 나타난다.

- `pg_stat_activity`에 `idle in transaction` 세션이 남는다.
- 특정 테이블의 dead tuple이 빨리 쌓인다.
- autovacuum이 제때 끝나지 않는다.
- 락 이슈가 드문드문 재현된다.

이때 `idle_in_transaction_session_timeout = '30s'` 같은 설정은 단순 kill switch가 아니다. **코드 결함을 조기에 발견하는 테스트 장치**가 된다.

### 추천 접근

- 앱 role에 기본 `idle_in_transaction_session_timeout`을 둔다.
- 알람/로그에서 `idle in transaction` 종료 건수를 모니터링한다.
- 종료가 발생하면 앱 로직에서 트랜잭션 범위를 점검한다.

즉 이 설정이 자주 발동한다면 "값을 늘릴까?"보다 먼저 **왜 transaction lifecycle이 새고 있는가**를 물어야 한다.

---

## 실무 예시 5: 긴 백필은 timeout을 푸는 대신 transaction을 쪼개야 한다

대량 백필이나 일회성 정정 작업에서 자주 듣는 말이 있다.

- "이 작업은 오래 걸리니까 `statement_timeout`을 꺼야겠네요."

가끔은 맞지만, 대부분은 반만 맞다.

진짜 먼저 물어야 할 질문은 아래다.

1. 이 작업이 **한 transaction**으로 길어야 하는가?
2. 청크로 나눠도 정합성을 유지할 수 있는가?
3. 락 경쟁이 생기면 fast-fail해야 하는가?
4. 실패 후 이어서 재개 가능한가?

예를 들어 다음처럼 청크 백필이 가능하다면:

```sql
UPDATE users
SET normalized_email = lower(email)
WHERE id IN (
  SELECT id
  FROM users
  WHERE normalized_email IS NULL
  ORDER BY id
  LIMIT 5000
);
```

보통 더 좋은 운영 방식은 이렇다.

- 큰 `statement_timeout` 하나로 무제한에 가깝게 열어 두지 않는다.
- 청크 단위로 transaction을 나눈다.
- 각 청크에 적당한 `statement_timeout`을 둔다.
- `lock_timeout`은 짧게 유지한다.
- 진행률 테이블이나 resume 기준점을 둔다.

즉 백필의 핵심은 timeout 해제가 아니라 **재개 가능한 청크 구조**다.

---

## 실무 예시 6: PgBouncer 환경에서는 timeout이 role/세션 정책과 충돌하지 않는지 봐야 한다

PgBouncer, 특히 transaction pooling을 쓰는 환경에서는 timeout 적용 위치가 중요하다.

### 고려할 점

#### 1) 세션 상태를 기대하는 설정 방식은 pooling mode와 충돌할 수 있다

트랜잭션 경계가 끝날 때 서버 세션이 재할당될 수 있으므로, 애플리케이션이 세션 전체에 영속된 timeout 상태를 당연하게 여기는 방식은 주의가 필요하다.

#### 2) `SET LOCAL`은 트랜잭션 안에서 더 안전하다

특정 유스케이스의 timeout을 명확히 보장하고 싶다면, 트랜잭션 안에서 `SET LOCAL`로 붙이는 편이 예측 가능하다.

#### 3) `idle_session_timeout`은 pooler와 잘 안 맞을 수 있다

공식 문서도 pooler나 middleware 환경에서는 주의하라고 말한다. pooler가 재사용하려던 연결이 예고 없이 닫히면 오히려 연결 churn이 늘 수 있다.

즉 pooler 환경에서 timeout 정책은 더더욱 **role 기본값 + transaction-local override** 조합이 안정적이다.

---

## 트레이드오프: timeout을 공격적으로 둘수록 언제나 좋은 것은 아니다

timeout이 짧을수록 장애 반경은 줄어드는 경향이 있다. 하지만 부작용도 있다.

### 장점

- lock convoy 조기 차단
- 장기 대기 감소
- pool 점유 시간 감소
- 실패 감지 속도 향상
- 코드의 transaction leak 조기 발견

### 단점

- 정상 변동까지 false timeout으로 자를 수 있음
- 재시도 트래픽이 늘 수 있음
- 보고서/백필/복잡한 집계가 지나치게 자주 실패할 수 있음
- 개발자는 근본 원인보다 값 상향으로 도망치기 쉬움

### 그래서 중요한 질문

- 이 실패는 빨리 surface 되어야 하는가?
- 재시도 가능한가?
- 중복 부수효과가 없는가?
- 느려도 끝나는 편이 나은가, 빨리 실패하는 편이 나은가?
- 이 워크로드는 온라인 lane인가, 배치 lane인가?

좋은 timeout 값은 절대값보다 **업무 성격과 failure mode**에 더 의존한다.

---

## 관측성: timeout은 설정으로 끝나지 않고, 실패를 읽을 수 있어야 의미가 있다

timeout을 걸어도 관측하지 않으면 결국 두 가지밖에 모르게 된다.

- 뭔가 가끔 실패한다.
- 값을 더 키워야 하나 고민된다.

실무에서는 최소한 아래를 같이 본다.

### 1) PostgreSQL 로그

- statement timeout 발생 빈도
- lock timeout 발생 빈도
- 어떤 쿼리 패턴에서 주로 터지는지
- 어느 시간대/배치 구간에서 집중되는지

`log_min_error_statement`가 적절히 설정되어 있으면 timeout된 statement를 함께 볼 수 있다.

### 2) `pg_stat_activity`

특히 다음 컬럼이 유용하다.

- `state`
- `wait_event_type`
- `wait_event`
- `query_start`
- `xact_start`
- `application_name`

예:

```sql
SELECT
  pid,
  usename,
  application_name,
  state,
  wait_event_type,
  wait_event,
  now() - xact_start AS xact_age,
  now() - query_start AS query_age,
  query
FROM pg_stat_activity
WHERE datname = current_database()
  AND state <> 'idle'
ORDER BY xact_age DESC NULLS LAST, query_age DESC NULLS LAST;
```

이 쿼리는 다음 질문에 도움을 준다.

- 오래된 transaction이 실제 실행 중인가, idle인가?
- lock 대기가 많은가, CPU/I/O 실행이 많은가?
- 특정 애플리케이션 이름에서만 문제가 나는가?

### 3) 애플리케이션 지표

- DB timeout 예외 건수
- 재시도 횟수
- idempotency conflict 비율
- pool checkout latency
- request timeout과 DB timeout의 상관관계

### 4) 업무 관점 지표

- 주문 실패율
- 중복 처리 방지 hit 수
- 백필 진행률
- worker 재처리율

timeout은 기술 설정이지만, 성공 여부는 결국 **업무 지표가 안정화되는가**로 봐야 한다.

---

## 장애 분석 플레이북: timeout 종류별로 조사 순서를 달리해야 한다

운영 중 timeout 알람이 올라오면 가장 흔한 실수는 원인을 하나로 단정하는 것이다. 하지만 timeout 종류에 따라 첫 질문이 달라야 한다.

### 1) `lock_timeout`이 늘어날 때

가장 먼저 볼 것:

- `pg_stat_activity`에서 `wait_event_type = 'Lock'` 세션 증가 여부
- 오래된 `xact_start` 세션 존재 여부
- 최근 DDL, 대량 UPDATE, 백필, 배치 시작 시각
- 동일 엔티티 hot row 집중 여부

대표 점검 쿼리:

```sql
SELECT
  pid,
  usename,
  application_name,
  state,
  wait_event_type,
  wait_event,
  now() - xact_start AS xact_age,
  now() - query_start AS query_age,
  query
FROM pg_stat_activity
WHERE wait_event_type = 'Lock'
ORDER BY xact_age DESC NULLS LAST, query_age DESC NULLS LAST;
```

운영 해석:

- lock timeout 증가는 보통 "쿼리가 느리다"보다 **경합이 심하다** 쪽에 가깝다.
- 원인은 인덱스 부재가 아니라 트랜잭션 범위, 락 순서, hot row, 배치 충돌일 수 있다.

### 2) `statement_timeout`이 늘어날 때

가장 먼저 볼 것:

- 실제 실행 계획 변화 여부
- temp file spill, I/O saturation, WAL pressure
- 상위 API timeout과 DB timeout 정합성
- 특정 시간대 대량 요청/배치 겹침 여부

운영 해석:

- statement timeout 증가는 진짜 느린 실행일 수도 있고,
- lock wait를 포함한 전체 대기일 수도 있고,
- 애플리케이션이 이미 포기한 뒤 DB만 뒤늦게 계속 일하는 구조일 수도 있다.

즉 무조건 인덱스 추가부터 갈 일이 아니다.

### 3) `idle_in_transaction_session_timeout`이 늘어날 때

가장 먼저 볼 것:

- ORM session lifecycle
- 예외 경로 rollback/close 누락
- 수동 SQL 사용 패턴
- 트랜잭션 안에서 외부 I/O 수행 여부

대표 점검 쿼리:

```sql
SELECT
  pid,
  usename,
  application_name,
  state,
  now() - xact_start AS xact_age,
  now() - state_change AS idle_age,
  query
FROM pg_stat_activity
WHERE state = 'idle in transaction'
ORDER BY idle_age DESC;
```

운영 해석:

- 이 수치는 DB 성능보다 애플리케이션 lifecycle 품질을 더 잘 보여준다.
- 많이 뜬다면 값이 짧은 것이 아니라 코드가 새고 있는 것이다.

### 4) `transaction_timeout`이 늘어날 때

가장 먼저 볼 것:

- transaction 내부에 들어간 외부 호출
- 청크 처리 부재
- 배치가 한 transaction에 너무 많은 row를 묶는지 여부
- 서비스 레이어에서 트랜잭션 데코레이터 범위가 과한지 여부

운영 해석:

- transaction timeout은 종종 "statement 하나가 느리다"보다
- **업무 흐름 자체가 transaction을 너무 오래 붙잡는다**는 신호다.

### 팀 운영 팁: timeout을 에러 코드 하나로 합치지 말자

애플리케이션 로깅에서 아래를 분리해 두는 편이 좋다.

- statement timeout
- lock timeout
- idle-in-transaction termination
- transaction timeout
- application-side DB call timeout

그래야 "DB timeout이 늘었다"는 막연한 알람 대신, 정확히 어느 레이어의 어떤 기다림이 늘었는지 대화가 된다.

---

## 실무 예시 7: 리포트/분석 쿼리는 primary에서 timeout만 늘리기보다 lane을 옮기는 편이 낫다

가끔 이런 요구가 나온다.

- 재무 정산 리포트가 25초 정도 걸린다.
- 그래서 `statement_timeout`을 30초, 60초, 120초로 계속 늘린다.

이 접근이 항상 틀린 것은 아니다. 하지만 온라인 트래픽과 같은 lane에서 이걸 해결하려 하면 금방 한계가 온다.

### 왜냐하면 문제의 본질이 timeout 숫자가 아닐 수 있기 때문이다

- 리포트는 큰 정렬과 집계를 수행한다.
- temp file과 `work_mem` 압력을 만든다.
- 긴 snapshot을 유지한다.
- 온라인 읽기/쓰기와 자원 경쟁을 일으킨다.

이때 primary의 일반 앱 role timeout을 계속 늘리면 다음 부작용이 생긴다.

- 원래 짧게 실패해야 할 요청까지 같이 늘어진다.
- pool 자원과 worker가 장시간 묶인다.
- 운영자는 lane 분리 대신 숫자 조정만 반복하게 된다.

### 더 나은 접근

- 분석/백오피스 role을 분리한다.
- 가능하면 replica 또는 별도 읽기 경로로 보낸다.
- 그 lane에서만 더 긴 `statement_timeout`을 허용한다.
- 온라인 role의 timeout은 짧게 유지한다.

즉 timeout 상향이 필요할 때는 먼저 **이 쿼리가 같은 lane에 있어야 하는가**를 묻는 편이 낫다.

---

## 흔한 실수 1: 모든 세션에 같은 `statement_timeout`을 건다

가장 흔한 실수다.

예를 들어 전역으로 `statement_timeout=3s`를 두면:

- 온라인 API에는 괜찮아 보일 수 있다.
- 하지만 5초짜리 정상 리포트가 다 실패한다.
- 운영자가 원인 파악하려고 돌리는 진단 쿼리도 중간에 끊긴다.
- 배치 작업은 우회 스크립트로 DB에 직접 붙기 시작한다.

결과적으로 규칙은 약해지고 예외 경로만 늘어난다.

**해법:** 최소 role 또는 workload lane 단위로 분리한다.

---

## 흔한 실수 2: `statement_timeout`과 `lock_timeout`을 같은 값으로 둔다

이 실수는 겉보기엔 단순하지만 의미를 잃게 만든다.

- `statement_timeout=2s`
- `lock_timeout=2s`

이렇게 두면 사실상 "락 때문에 오래 기다리지 말자"는 정책이 선명하지 않다. 실제로는 statement timeout이 먼저 의미를 가져가고, lock-specific fast-fail이 흐려진다.

**해법:** `lock_timeout`은 대개 `statement_timeout`보다 훨씬 짧아야 한다.

---

## 흔한 실수 3: transaction 안에서 외부 API나 사람을 기다린다

아래는 매우 흔한 안티패턴이다.

1. `BEGIN`
2. 주문 상태 읽기
3. 외부 결제 승인 API 호출
4. 응답 대기
5. 결과 업데이트
6. `COMMIT`

이 구조는 timeout 값을 어떻게 만져도 본질적으로 위험하다.

- lock을 오래 들고 있을 수 있다.
- 네트워크 지연이 transaction 수명으로 전염된다.
- timeout 나면 중간 상태 해석이 어렵다.

**해법:** 외부 I/O는 가능한 한 transaction 밖으로 빼고, transaction은 짧고 결정적인 DB 변경만 포함한다.

---

## 흔한 실수 4: `idle_in_transaction_session_timeout`이 자주 터지면 값을 늘린다

이 설정이 자주 발동한다는 건 보통 아래 중 하나다.

- ORM 세션 관리 버그
- 예외 경로 rollback 누락
- 수동 SQL 운영 습관 문제
- transaction 범위를 지나치게 넓게 잡은 설계

여기서 값만 늘리면 증상은 늦게 드러날 뿐, 문제는 계속 자란다.

**해법:** 발동 빈도를 버그 신호로 본다.

---

## 흔한 실수 5: timeout 뒤 재시도는 붙이면서 idempotency는 설계하지 않는다

timeout은 실패를 더 빨리 surface 한다. 좋은 일이다. 하지만 재시도를 곧바로 붙이면 다른 문제가 생긴다.

- 첫 번째 요청이 실제로는 반영됐을 수 있다.
- 두 번째 요청이 같은 작업을 다시 실행할 수 있다.
- 락 대기와 retry 폭주가 서로를 키울 수 있다.

**해법:** timeout을 재시도와 같이 쓸 때는 최소한 아래 중 하나가 필요하다.

- idempotency key
- 상태 전이 조건부 update
- unique constraint 기반 중복 방지
- outbox/inbox 중복 소비 방지

---

## 흔한 실수 6: timeout 발생 원인을 "DB가 느리다" 한 줄로 요약한다

timeout은 결과이지 원인이 아니다.

실제 원인은 다양하다.

- lock wait
- bad plan
- temp file spill
- vacuum 지연
- network stall
- application pool starvation
- transaction leak

`statement_timeout`이 떴다고 곧바로 인덱스부터 추가하면 방향이 빗나갈 수 있다.

**해법:** timeout 종류별로 원인 조사 루트를 나눈다.

- `lock_timeout` 많음 → lock graph, long xact, DDL/배치 충돌 확인
- `statement_timeout` 많음 → plan, I/O, spill, 상위 SLA 정합성 확인
- `idle_in_transaction_session_timeout` 많음 → ORM/session lifecycle 점검
- `transaction_timeout` 많음 → transaction scope 분해, 청크화, 외부 I/O 분리

---

## 체크리스트: PostgreSQL timeout 정책을 운영 기준으로 점검하기

### 기본 정책

- [ ] 온라인 요청, 워커, 배치, 운영 세션을 같은 timeout 정책으로 다루고 있지 않은가?
- [ ] `statement_timeout`이 상위 호출 체인의 기대 시간보다 길지 않은가?
- [ ] `lock_timeout`이 `statement_timeout`보다 충분히 짧은가?
- [ ] `statement_timeout`을 무조건 전역 `postgresql.conf`에서만 관리하고 있지 않은가?

### 트랜잭션 위생

- [ ] 앱 role에 `idle_in_transaction_session_timeout`이 있는가?
- [ ] `idle in transaction` 세션을 대시보드나 알람으로 보고 있는가?
- [ ] 외부 API 호출, 파일 I/O, 사람 승인 대기를 transaction 안에 넣지 않았는가?
- [ ] 대량 작업은 한 transaction으로 길게 묶지 않고 청크로 나누는가?

### 락과 재시도

- [ ] lock wait가 긴 경로에서 `NOWAIT`, `SKIP LOCKED`, 짧은 `lock_timeout`을 검토했는가?
- [ ] timeout 뒤 애플리케이션 재시도는 idempotency와 함께 설계되었는가?
- [ ] DDL/백필 작업은 긴 `statement_timeout` + 짧은 `lock_timeout` 조합을 쓰는가?

### 관측성

- [ ] statement timeout / lock timeout 발생 건수를 로그와 메트릭으로 분리해 보는가?
- [ ] `pg_stat_activity`에서 오래된 `xact_start`, `query_start`, `wait_event_type=Lock`를 추적하는가?
- [ ] timeout이 터졌을 때 원인 쿼리와 application_name을 연결할 수 있는가?

### 최신 기능/버전

- [ ] `transaction_timeout` 사용 전 메이저 버전과 매니지드 서비스 지원 여부를 확인했는가?
- [ ] 새 timeout을 넣기 전에 staging에서 false timeout 비율을 확인했는가?

---

## 추천 출발점: 대부분의 서비스가 처음 가져가 볼 만한 현실적 기준

아래 값은 절대 정답이 아니라 **대화 시작점**이다.

### 온라인 API role

- `statement_timeout`: 500ms ~ 2s 범위에서 SLA 기반 결정
- `lock_timeout`: 50ms ~ 200ms
- `idle_in_transaction_session_timeout`: 15s ~ 60s

### 워커 / 컨슈머 role

- `statement_timeout`: 수초 ~ 수십초
- `lock_timeout`: 매우 짧게 두거나 `NOWAIT`, `SKIP LOCKED`로 회피
- `idle_in_transaction_session_timeout`: 수십초

### DDL / 운영 마이그레이션

- `statement_timeout`: 길게
- `lock_timeout`: 매우 짧게
- 가능하면 별도 경로/계정 사용

### 분석 / 수동 쿼리

- 별도 role 분리
- 온라인 lane과 timeout 정책 분리
- 필요 시 replica 또는 별도 읽기 경로 사용

중요한 것은 숫자 자체보다 **"왜 이 lane은 이 정도를 허용하는가"가 설명 가능해야 한다는 점**이다.

---

## 한 줄 정리

> **PostgreSQL timeout 설계의 핵심은 값을 짧게 두는 것이 아니라, `statement_timeout`으로 업무 deadline을 자르고, `lock_timeout`으로 대기 전파를 막고, `idle_in_transaction_session_timeout`과 `transaction_timeout`으로 트랜잭션 위생을 강제해 각 워크로드의 장애 반경을 예측 가능한 범위 안에 두는 것이다.**
