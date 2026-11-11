---
layout: post
title: "PostgreSQL 예약 중복 방지 실전: tstzrange와 Exclusion Constraint로 동시성까지 지키기"
date: 2026-11-11 11:40:00 +0900
categories: [sql]
tags: [study, sql, postgresql, range-type, tstzrange, exclusion-constraint, gist, concurrency, booking]
permalink: /sql/2026/11/11/study-postgresql-exclusion-constraint-range-booking-overlap.html
---

## 문제: 조회 후 INSERT는 예약의 불변식을 보장하지 않는다

회의실 예약 API가 다음 쿼리로 빈 시간을 확인한다고 하자.

```sql
SELECT 1
FROM bookings
WHERE resource_id = 42
  AND status = 'confirmed'
  AND starts_at < :new_end
  AND ends_at > :new_start
LIMIT 1;
```

결과가 없으면 `INSERT`한다. 단일 요청에서는 그럴듯하지만, 동시에 들어온 두 요청은 모두 빈 결과를 보고 각각 예약을 저장할 수 있다. 애플리케이션의 `if not exists`는 **사용자에게 빠른 피드백을 주는 조회**일 뿐, 동시 쓰기를 막는 데이터베이스 불변식이 아니다. 트랜잭션으로 두 문장을 묶어도 기본 `READ COMMITTED`에서는 이 조회가 미래의 다른 행을 잠그지 않는다. `SELECT ... FOR UPDATE` 역시 아직 존재하지 않는 예약 행을 잠글 수 없다.

필요한 규칙은 단순하다.

> 같은 자원에 대해 확정된 두 예약의 시간 구간은 겹치면 안 된다.

하지만 `UNIQUE(resource_id, starts_at)`은 시작 시각이 다른 중첩을 놓친다. `CHECK` 제약은 한 행의 시작·종료 순서를 검사할 수 있어도 다른 행과 비교하는 불변식을 표현하지 못한다. 이 글은 PostgreSQL의 range type과 `EXCLUDE USING gist`를 이용해 **쓰기 경로가 여러 개여도 유지되는 규칙**으로 옮긴다.

## 1. 경계부터 정한다: `[시작, 종료)`

예약 A가 10:00~11:00이고 B가 11:00~12:00이면 보통 두 예약은 허용해야 한다. 그래서 시작은 포함하고 종료는 제외하는 반열린 구간 `[)`을 쓴다.

```sql
SELECT
  tstzrange('2026-11-11 10:00+09'::timestamptz,
            '2026-11-11 11:00+09'::timestamptz, '[)')
  &&
  tstzrange('2026-11-11 11:00+09'::timestamptz,
            '2026-11-11 12:00+09'::timestamptz, '[)') AS overlaps;
-- false
```

`&&`는 두 범위가 겹치는지 검사하는 연산자다. 오른쪽 예약을 10:59에 시작하면 결과는 `true`다. 경계를 정의하지 않고 `starts_at <= new_end AND ends_at >= new_start`를 쓰면 맞닿은 예약도 충돌로 취급한다. 경계 정책은 API, DB 제약, UI에 동일하게 적용해야 한다.

`tsrange`는 시간대 없는 timestamp의 범위이고, `tstzrange`는 `timestamptz`의 범위다. 서로 다른 시간대의 예약을 같은 자원에 배치한다면 실제 순간을 비교하는 `tstzrange`가 적합하다. 클라이언트가 보내는 시각에는 UTC 또는 명시적 오프셋을 요구하고, 반복 예약의 지역 달력 규칙은 별도 모델로 보관한다. `2026-11-11 10:00`처럼 오프셋 없는 문자열을 세션 시간대에 맡기면 배포 환경에 따라 의미가 달라진다.

## 2. 데이터 모델: 단일 행의 유효성과 행 사이의 충돌을 분리한다

아래 예시는 `confirmed` 예약만 자원을 점유한다. `cancelled`는 감사·이력용으로 남기지만 점유하지 않는다. `pending`을 둘 계획이라면 그것이 실제 홀드인지부터 정책을 결정해야 한다.

```sql
CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE TABLE bookings (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    resource_id bigint NOT NULL,
    during      tstzrange NOT NULL,
    status      text NOT NULL DEFAULT 'confirmed',
    created_at  timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT bookings_status_check
      CHECK (status IN ('confirmed', 'cancelled')),
    CONSTRAINT bookings_finite_nonempty_check
      CHECK (
        NOT isempty(during)
        AND NOT lower_inf(during)
        AND NOT upper_inf(during)
        AND lower_inc(during)
        AND NOT upper_inc(during)
      ),
    CONSTRAINT bookings_no_confirmed_overlap
      EXCLUDE USING gist (
        resource_id WITH =,
        during WITH &&
      ) WHERE (status = 'confirmed')
);
```

`btree_gist`는 `bigint`에 대한 `=` 비교를 GiST 인덱스에서 사용할 수 있게 한다. 범위의 `&&`와 자원 번호의 `=`가 **둘 다 참**인 두 행을 배제한다. 다른 회의실의 같은 시각은 허용된다. PostgreSQL은 exclusion constraint를 뒷받침하는 인덱스를 만든다. 애플리케이션에서 겹침 검사를 재구현하는 것과 달리 이 규칙은 배치 작업, 운영 SQL, 다른 API 서버의 쓰기에도 적용된다.

`during NOT NULL`은 중요하다. 범위가 `NULL`이면 겹침 비교 결과도 참이 아니어서 규칙을 우회할 수 있다. 빈 범위도 어떤 범위와도 겹치지 않으므로 따로 거절한다. 무한 경계를 허용하면 실수로 전체 기간을 점유할 수 있어 여기서는 막았다. `[)` 경계 검사도 모델 정책을 명시한 것이다. 이러한 검사는 *한 행의 형식*을 담당하고, exclusion constraint는 *행 사이의 관계*를 담당한다.

```sql
INSERT INTO bookings (resource_id, during)
VALUES (
  42,
  tstzrange('2026-11-11 10:00+09', '2026-11-11 11:00+09', '[)')
);

-- 경계가 맞닿으므로 성공
INSERT INTO bookings (resource_id, during)
VALUES (
  42,
  tstzrange('2026-11-11 11:00+09', '2026-11-11 12:00+09', '[)')
);

-- 같은 자원에서 앞 예약과 겹치므로 SQLSTATE 23P01
INSERT INTO bookings (resource_id, during)
VALUES (
  42,
  tstzrange('2026-11-11 10:30+09', '2026-11-11 11:30+09', '[)')
);
```

마지막 문장이 실패하면 현재 트랜잭션은 오류 상태다. 계속 SQL을 실행하려면 애플리케이션이 트랜잭션을 롤백하거나, 사전에 만든 savepoint로 되돌려야 한다.

## 3. 동시성: 먼저 조회한 요청이 승리하는 것이 아니다

두 세션이 같은 자원에 겹치는 예약을 동시에 넣는 상황을 생각해 보자.

```text
세션 A                            세션 B
BEGIN                            BEGIN
겹침 조회: 없음                  겹침 조회: 없음
INSERT 예약 A                    INSERT 예약 B
COMMIT                           COMMIT
```

조회 결과만 믿으면 둘 다 저장될 수 있다. exclusion constraint가 있으면 두 삽입이 모두 확정되는 상태는 허용되지 않는다. 충돌하는 미확정 쓰기 때문에 한쪽이 대기할 수 있고, 최종적으로 한쪽은 `23P01`(exclusion_violation)로 실패한다. 어느 쪽이 성공할지는 스케줄링에 따라 달라질 수 있다. DB가 보장하는 것은 *승자 선정 순서*가 아니라 **확정된 상태에서 불변식이 깨지지 않는 것**이다.

이 규칙을 얻기 위해 모든 예약 트랜잭션을 `SERIALIZABLE`로 올릴 필요는 없다. 반대로 exclusion constraint가 모든 비즈니스 판단을 대체하는 것도 아니다. 요금 계산, 권한, 운영 시간, 사용자별 한도는 별도로 검증해야 한다. 충돌 조회를 미리 해 사용자에게 후보 시간을 보여줄 수는 있지만, 실제 예약 성공 판정은 쓰기 결과로 해야 한다.

API에서는 제약 이름과 SQLSTATE를 기준으로 오류를 분류한다. 에러 메시지 문자열을 파싱하지 않는다.

```python
# 드라이버별 속성명은 다르므로 아래는 경계 처리의 의사 코드다.
try:
    with db.transaction():
        db.execute(
            """INSERT INTO bookings (resource_id, during)
               VALUES (:resource_id,
                       tstzrange(:starts_at, :ends_at, '[)'))""",
            params,
        )
except DatabaseError as exc:
    if sqlstate(exc) == "23P01" and constraint_name(exc) == "bookings_no_confirmed_overlap":
        raise BookingConflict("선택한 시간에 이미 확정된 예약이 있습니다") from exc
    raise
```

`23P01`은 일정 충돌처럼 사용자가 다른 슬롯을 선택해야 하는 결과다. 맹목적으로 같은 입력을 즉시 재시도해도 성공하지 않는다. 다만 네트워크 오류로 결과를 모르는 경우에는 같은 예약을 두 번 만들지 않도록 **요청 idempotency key**를 별도 unique 제약으로 설계해야 한다. exclusion constraint는 중복 요청의 동일성까지 판별하지 않는다.

## 4. 변경·취소·교환에서 발생하는 미묘한 실패

`UPDATE`도 제약 대상이다. 확정 예약의 시간을 다른 확정 예약 위로 옮기려 하면 실패한다. `status='cancelled'`로 바꾸면 부분 exclusion constraint의 대상에서 빠지므로 자리를 비울 수 있다. 다만 취소와 새 예약이 여러 SQL로 나뉜다면 업무적으로 원자성이 필요한 범위를 하나의 트랜잭션으로 묶는다.

두 예약의 시간을 서로 교환할 때는 **중간 상태**가 문제다. 최종 결과는 유효해도 첫 번째 `UPDATE` 순간에는 두 구간이 겹친다. 이런 작업이 필요하다면 제약을 지연 가능하게 정의할 수 있다.

```sql
-- 새 테이블 설계 시 제약 정의의 끝에 추가한다.
CONSTRAINT bookings_no_confirmed_overlap
  EXCLUDE USING gist (resource_id WITH =, during WITH &&)
  WHERE (status = 'confirmed')
  DEFERRABLE INITIALLY IMMEDIATE
```

```sql
BEGIN;
SET CONSTRAINTS bookings_no_confirmed_overlap DEFERRED;

-- 두 예약의 during을 각각 상대의 기존 구간으로 변경한다.
UPDATE bookings SET during = :slot_b WHERE id = :booking_a;
UPDATE bookings SET during = :slot_a WHERE id = :booking_b;

COMMIT; -- 최종 상태에서 제약 검사. 충돌하면 여기서 실패할 수 있다.
```

지연 검사는 교환 트랜잭션을 가능하게 하지만 실패 시점을 `COMMIT`까지 미룬다. 커밋 오류를 포착하고 전체 트랜잭션을 다시 설계해야 하며, 애플리케이션이 커밋 전에 성공 응답을 보내면 안 된다. 또 `ON CONFLICT`의 arbiter로 지연 가능한 제약을 사용할 수 없으므로 upsert 전략과 함께 설계해야 한다. 교환 요구가 없다면 기본 즉시 검사 제약이 단순하다.

한편 취소 이력을 같은 테이블에 계속 쌓으면 부분 인덱스는 확정 예약만 담지만 테이블 전체의 저장·보존 정책은 별개다. 과거 예약을 삭제하거나 아카이브하는 정책은 감사 요건에 맞춰 정한다.

## 5. 운영 중인 테이블에 붙일 때: 중복 데이터부터 찾아야 한다

기존 테이블에 제약을 붙이기 전에 현재 위반 행을 찾아야 한다. 정확히 같은 `status` 규칙과 `&&`를 사용해야 검증 쿼리와 제약이 어긋나지 않는다.

```sql
SELECT a.id AS booking_a, b.id AS booking_b,
       a.resource_id, a.during AS slot_a, b.during AS slot_b
FROM bookings AS a
JOIN bookings AS b
  ON a.resource_id = b.resource_id
 AND a.id < b.id
 AND a.during && b.during
WHERE a.status = 'confirmed'
  AND b.status = 'confirmed'
ORDER BY a.resource_id, a.id, b.id;
```

위 쿼리는 조사용이다. 전체 셀프 조인은 데이터가 크면 비싸므로 자원·기간을 나눠 조사하고 실행 계획을 확인한다. 찾은 중복을 무조건 삭제하지 말고 실제 소유자, 승인 이력, 결제 상태를 대조해 정리한다. `NULL`, 빈 범위, 끝이 없는 범위, 역전된 시작·종료도 별도로 검사한다. 데이터 정리와 새 쓰기 차단 사이에 경합 창이 생길 수 있으므로 배포 순서를 계획해야 한다.

기존 `starts_at`/`ends_at` 컬럼을 사용하는 경우 한 번에 전환하려 하지 말고 다음과 같이 단계를 나눈다.

1. 입력 시간대와 `[)` 경계를 확정하고, 기존 데이터에서 `starts_at >= ends_at` 및 중첩을 조사한다.
2. `during`을 추가하고 기존 행을 배치 단위로 채운다. 변환 중에는 앱이 두 표현을 일관되게 쓰도록 한다.
3. 새 쓰기 경로를 제한하거나 유지보수 창을 잡고, 마지막 중복 점검 후 제약을 추가한다.
4. 실제 쓰기 오류와 지연을 관찰한 뒤 읽기 경로를 `during`으로 옮기고 구 컬럼을 제거한다.

`ALTER TABLE ... ADD CONSTRAINT ... EXCLUDE`는 기존 데이터 검사와 뒷받침 인덱스 생성이 필요하다. 대용량 운영 테이블에서 이를 가벼운 메타데이터 변경처럼 취급하면 안 된다. 일반 `CREATE INDEX CONCURRENTLY`만 먼저 실행했다고 곧바로 exclusion constraint가 생기는 것도 아니다. 락·실행 시간·롤백 계획을 사전 환경에서 측정한다.

## 6. 부하와 인덱스 선택: 정확성과 조회 속도는 다른 질문이다

GiST 인덱스는 제약 집행에 필요하고, 다음과 같은 후보 조회에도 활용될 수 있다.

```sql
SELECT id, during
FROM bookings
WHERE resource_id = 42
  AND status = 'confirmed'
  AND during && tstzrange(
        '2026-11-11 09:00+09',
        '2026-11-11 18:00+09',
        '[)'
      );
```

하지만 인덱스가 있다고 언제나 빠른 것은 아니다. 작은 테이블에서는 순차 스캔이 합리적일 수 있고, 자원별 예약 분포·기간 선택도·상태 조건에 따라 계획이 달라진다. `EXPLAIN (ANALYZE, BUFFERS)`로 **실제 대표 데이터**에서 확인한다. 전체 예약을 날짜순으로 페이지네이션하거나 특정 사용자의 이력을 조회하는 요구라면 별도 B-tree 인덱스가 필요할 수 있다. 제약용 GiST를 모든 조회의 만능 인덱스로 취급하지 않는다.

장기 예약 하나가 광범위한 시간대를 점유할 수 있다. 그런 예약을 허용할지, 최대 길이를 둘지, 운영 점검 시간을 예외적으로 관리할지도 도메인 정책이다. 최대 길이를 강제한다면 `CHECK (upper(during) - lower(during) <= interval '...')`처럼 한 행 제약으로 표현할 수 있다. 실제 제한값은 업무 요구에 맞춰 결정한다.

## 7. 검증 시나리오: SQL 문법보다 상태 전이를 시험한다

배포 전에는 적어도 다음 사례를 두 개의 독립 세션과 사전 데이터셋에서 확인한다.

- 같은 자원, 완전히 같은 구간: 하나만 성공하는가?
- 같은 자원, 일부만 겹치는 구간: `23P01`로 거절되는가?
- 같은 자원, 종료와 시작이 정확히 맞닿은 구간: 둘 다 허용되는가?
- 서로 다른 자원, 같은 구간: 둘 다 허용되는가?
- 취소된 예약과 같은 구간의 새 확정 예약: 허용되는가?
- 취소 예약을 다시 확정할 때 이미 다른 예약이 있으면: 거절되는가?
- 빈 구간, 무한 경계, `NULL` 범위: 행 형식 검사로 거절되는가?
- 두 세션의 동시 삽입: 최종 확정 행이 중첩되지 않는가?
- 지연 제약을 택했다면 시간 교환: 커밋 성공과 커밋 실패를 모두 처리하는가?

제약의 실제 정의는 카탈로그에서 확인할 수 있다.

```sql
SELECT conname,
       condeferrable,
       condeferred,
       pg_get_constraintdef(oid) AS definition
FROM pg_constraint
WHERE conrelid = 'bookings'::regclass
  AND conname = 'bookings_no_confirmed_overlap';
```

실패 테스트는 같은 트랜잭션을 계속 재사용하지 않도록 주의한다. 오류 뒤에는 롤백하고 새 트랜잭션에서 다음 사례를 실행한다. 동시성 테스트에서는 두 세션이 실제로 겹치게 시작했는지 기록하고, 성공 응답 수뿐 아니라 **최종 저장 상태**를 검사한다.

## 결론

예약 중복은 조회 쿼리를 조금 더 정교하게 만든다고 해결되지 않는다. 그 쿼리가 다른 쓰기와 경쟁하는 순간, 애플리케이션 확인과 DB 불변식의 차이가 드러난다. PostgreSQL에서는 `tstzrange`로 경계를 명시하고, `EXCLUDE USING gist (resource_id WITH =, during WITH &&)`로 같은 자원의 중첩 확정 예약을 거절할 수 있다.

핵심 설계 선택은 세 가지다. **어떤 상태가 자원을 점유하는가**, **끝 시각을 포함할 것인가**, **충돌 시 사용자에게 어떤 결과를 줄 것인가**. 이 정책을 정한 뒤 제약과 오류 처리를 연결하면, 여러 API·배치·운영 경로가 있어도 같은 규칙을 공유할 수 있다.

## 근거 문서

- [PostgreSQL: Constraints — Exclusion Constraints](https://www.postgresql.org/docs/current/ddl-constraints.html#DDL-CONSTRAINTS-EXCLUSION)
- [PostgreSQL: Range Types — Inclusive and Exclusive Bounds, Constraints](https://www.postgresql.org/docs/current/rangetypes.html)
- [PostgreSQL: `btree_gist` extension](https://www.postgresql.org/docs/current/btree-gist.html)
- [PostgreSQL: `CREATE TABLE` — EXCLUDE, DEFERRABLE](https://www.postgresql.org/docs/current/sql-createtable.html)
- [PostgreSQL: Error Codes — `23P01`](https://www.postgresql.org/docs/current/errcodes-appendix.html)
- [PostgreSQL: `INSERT` — `ON CONFLICT` limitations](https://www.postgresql.org/docs/current/sql-insert.html)
