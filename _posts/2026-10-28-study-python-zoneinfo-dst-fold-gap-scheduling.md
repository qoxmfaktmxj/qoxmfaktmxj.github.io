---
layout: post
title: "Python 예약 시각 설계: zoneinfo의 DST 중복·누락 시간과 fold를 검증하는 법"
date: 2026-10-28 11:40:00 +0900
categories: [python]
tags: [study, python, datetime, zoneinfo, timezone, dst, fold, scheduling, reliability]
permalink: /python/2026/10/28/study-python-zoneinfo-dst-fold-gap-scheduling.html
---

## 문제: '매일 오전 9시'는 UTC 시각 하나가 아니다

서울에서 매일 09:00에 보고서를 발송하는 서비스라면 처음에는 다음 실행 시각을 하루 뒤로 밀기 쉽다.

```python
next_run_utc = last_run_utc + timedelta(hours=24)
```

그런데 뉴욕 고객이 같은 기능을 쓰기 시작하면 이 방식은 서머타임(DST) 전환일에 틀어진다. 사용자가 요청한 것은 **지역 시계의 매일 09:00**이지 **마지막 실행 이후 정확히 24시간**이 아니다. 전자는 달력 규칙이고 후자는 경과 시간이다. 같은 날짜라도 지역별 UTC 오프셋이 다르고, 한 지역의 오프셋도 날짜에 따라 바뀔 수 있다.

더 까다로운 문제는 전환 경계다. 미국 뉴욕의 2024년 3월 10일 02:30은 시계를 앞당기며 건너뛴 **존재하지 않는 지역 시각**이다. 2024년 11월 3일 01:30은 시계를 되돌리며 **두 번 나타난 지역 시각**이다. 단순히 `tzinfo=ZoneInfo(...)`를 붙여도 이 정책 결정은 자동으로 끝나지 않는다.

이 글은 Python 표준 라이브러리 `datetime`과 `zoneinfo`로 예약 시각을 다루는 방법을 설명한다. 핵심은 다음 세 가지를 분리하는 것이다.

1. **실행 순간(instant):** 전 세계에서 유일한 시점. 저장·비교·실행에는 UTC가 적합하다.
2. **지역 시계 시각(wall time):** 사용자가 입력한 날짜·시간과 IANA 시간대. 반복 일정의 의도다.
3. **모호성 정책:** 중복 시각에서 첫 번째·두 번째 중 어느 것을 택할지, 없는 시각은 건너뛸지·옮길지 결정한다.

`zoneinfo`는 시간대 규칙을 제공하지만 비즈니스 정책을 대신 정해 주지는 않는다. 예약 시스템은 이 정책을 데이터 모델과 검증 로직으로 드러내야 한다.

## 1. UTC 오프셋과 IANA 시간대는 다르다

다음 두 표현은 우연히 같은 순간을 나타낼 수 있다.

```text
2024-07-01T09:00:00-04:00
2024-07-01 09:00, America/New_York
```

첫 번째의 `-04:00`은 그 날짜의 오프셋만 알려 준다. 다음 겨울의 뉴욕 오전 9시가 어떤 UTC 시각인지는 이 값으로 계산할 수 없다. 두 번째의 `America/New_York`는 IANA 시간대 식별자이며, 해당 날짜에 적용되는 규칙으로 오프셋을 결정한다. 따라서 한 번의 예약된 실행은 UTC 시각으로 저장할 수 있지만, **반복 규칙**은 지역 시계 시각과 시간대 식별자를 보존해야 한다.

```python
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

zone = ZoneInfo("America/New_York")
run_at_utc = datetime(2024, 7, 1, 13, 0, tzinfo=timezone.utc)
print(run_at_utc.astimezone(zone))  # 2024-07-01 09:00:00-04:00
```

Python의 `datetime`에서 `tzinfo`가 없는 값은 **naive**, 있는 값은 **aware**다. Naive 값은 '이 값이 어느 시간대의 시각인가'라는 의미를 스스로 담지 않는다. API에서 입력받은 `2024-11-03 01:30`을 서버 로컬 시간으로 암묵 해석하면, 서버의 `TZ` 설정이나 배포 지역이 달라질 때 의미도 달라진다.

`datetime.now(timezone.utc)`처럼 aware UTC를 만들어 이벤트 발생 시각을 기록하고, 사용자 입력은 `local_date`, `local_time`, `zone_key`처럼 의미가 분명한 필드로 다루는 편이 안전하다. `UTC`와 `America/New_York`를 문자열 하나의 서로 바꿔 쓸 수 있는 시간대로 취급하지 않는다.

## 2. `replace(tzinfo=...)`는 변환이 아니라 해석이다

다음 코드는 기존 순간을 뉴욕 시각으로 **변환하지 않는다**.

```python
from datetime import datetime
from zoneinfo import ZoneInfo

wall = datetime(2024, 11, 3, 1, 30)  # naive 지역 시계 입력
candidate = wall.replace(tzinfo=ZoneInfo("America/New_York"))
```

`replace(tzinfo=...)`는 숫자로 적힌 01:30을 유지한 채 시간대 해석을 붙인다. 이미 알고 있는 UTC 순간을 뉴욕 시계로 표시하려면 `astimezone()`을 써야 한다.

```python
from datetime import timezone

instant = datetime(2024, 11, 3, 6, 30, tzinfo=timezone.utc)
print(instant.astimezone(ZoneInfo("America/New_York")))
# 2024-11-03 01:30:00-05:00
```

반대로 지역 시계 입력의 실재성을 검사할 때는 `replace()`가 후보를 만드는 데 유용하다. 다만 후보가 유효한 순간이라는 뜻은 아니다. `ZoneInfo`를 붙인다고 없는 시각에서 예외가 자동으로 발생하지 않는다. **후보를 UTC로 보냈다가 다시 지역 시계로 되돌려 검증**해야 한다.

이 차이는 외부 API 경계에서 중요하다. `2024-11-03T01:30:00-04:00`처럼 오프셋이 있는 문자열은 특정 순간을 가리키지만, `2024-11-03T01:30:00`과 `America/New_York`는 DST 중복 때문에 두 순간을 가리킬 수 있다. API가 후자를 받는다면 선택 정책을 받아야 한다.

## 3. 되돌린 시계: `fold`로 두 01:30을 구별한다

2024년 11월 3일 뉴욕에서는 01:30이 두 번 있다. Python의 PEP 495는 이 반복 구간을 구분하는 `fold` 속성을 도입했다. `fold=0`은 전환 **이전** 오프셋, `fold=1`은 전환 **이후** 오프셋을 선택한다.

```python
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ny = ZoneInfo("America/New_York")
wall = datetime(2024, 11, 3, 1, 30)

first = wall.replace(tzinfo=ny, fold=0)
second = wall.replace(tzinfo=ny, fold=1)

print(first.isoformat())   # 2024-11-03T01:30:00-04:00
print(second.isoformat())  # 2024-11-03T01:30:00-05:00
print(first.astimezone(timezone.utc))   # 2024-11-03 05:30:00+00:00
print(second.astimezone(timezone.utc))  # 2024-11-03 06:30:00+00:00
```

둘은 한 시간 떨어진 다른 순간이다. 예약 API가 '첫 번째 01:30' 또는 '두 번째 01:30'을 요구하지 않는다면 다음 중 하나를 명시해야 한다.

- 애매한 입력을 거절하고 사용자가 선택하게 한다.
- 한 번만 실행하는 업무라면 첫 번째 또는 두 번째를 제품 정책으로 고정한다.
- 시간대 전환 시 두 번 실행해야 하는 업무라면 두 순간을 **서로 다른 실행 ID**로 생성한다.

중요한 함정이 하나 있다. Python `datetime` 문서는 두 aware 값이 **같은 `tzinfo` 객체**를 가진 경우 비교와 뺄셈에서 `tzinfo`와 `fold`를 무시한다고 설명한다. 따라서 같은 `ZoneInfo`를 붙인 `first`와 `second`를 직접 빼서 실제 경과 시간을 측정하면 기대와 다를 수 있다.

```python
print(second - first)  # 0:00:00 — 지역 시계 숫자끼리 비교
print(second.astimezone(timezone.utc) - first.astimezone(timezone.utc))
# 1:00:00 — 실제 순간 사이의 경과 시간
```

경과 시간, 중복 제거 키, 실행 순서는 **UTC 순간**으로 비교한다. 지역 시계의 날짜·시각 비교는 달력 규칙에만 사용한다. `fold`는 '어느 순간인가'를 선택하는 정보이지, 동일한 `tzinfo`를 가진 datetime 산술의 동작을 바꾸는 범용 스위치가 아니다.

## 4. 앞당긴 시계: 없는 02:30은 정책 없이는 실행할 수 없다

2024년 3월 10일 뉴욕에서는 시계가 01:59:59 다음에 03:00:00으로 넘어갔다. 따라서 02:30은 현지 시계에서 발생하지 않았다.

```python
from datetime import datetime
from zoneinfo import ZoneInfo

ny = ZoneInfo("America/New_York")
imaginary = datetime(2024, 3, 10, 2, 30, tzinfo=ny)
print(imaginary.isoformat())  # 값은 만들어진다. 유효성 검사는 아니다.
```

`datetime` 생성이나 `.replace(tzinfo=ny)`만으로는 이 값이 가상의 지역 시각인지 검증되지 않는다. `fold=0/1`을 바꿔도 그 날 실제로 존재하지 않았던 02:30이 생기지는 않는다.

반복 일정에서 없는 시각을 처리하는 방식은 업무에 따라 다르다.

- **건너뛰기:** 02:30 정산 배치처럼 해당 날짜 실행이 불필요하거나 안전하게 다음 날 처리할 수 있는 경우.
- **전환 후 첫 유효 시각으로 이동:** 지정 시간이 없어도 그 날 반드시 한 번 발송해야 하는 알림.
- **입력 거절:** 일회성 법률·정산 예약처럼 운영자가 직접 판단해야 하는 경우.

'03:30으로 밀기'와 '03:00에 실행하기'도 서로 다른 정책이다. 하나는 공백 길이만큼 이동하고, 하나는 다음 유효 시각을 택한다. 구현 전에 제품 요구를 구체적인 문장으로 정해야 한다.

## 5. 실재하는 지역 시각의 UTC 후보를 구하는 코드

아래 함수는 naive 지역 시계 입력에 대해 가능한 UTC 순간을 **0개, 1개, 2개** 반환한다. 대상 범위는 `zoneinfo.ZoneInfo`가 제공하는 IANA 시간대 규칙이다. `fold` 후보를 각각 만들어 UTC 왕복 변환을 한 뒤, 원래 지역 시계 숫자와 `fold`가 모두 보존되는지 확인한다.

```python
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


def possible_instants(wall: datetime, zone: ZoneInfo) -> list[datetime]:
    if wall.tzinfo is not None:
        raise ValueError("wall must be a naive local datetime")

    instants: set[datetime] = set()
    for fold in (0, 1):
        candidate = wall.replace(tzinfo=zone, fold=fold)
        instant = candidate.astimezone(timezone.utc)
        round_trip = instant.astimezone(zone)

        if round_trip.replace(tzinfo=None) == wall and round_trip.fold == fold:
            instants.add(instant)

    return sorted(instants)
```

정상 시각에서는 `fold=0` 하나만 유효하다. 되돌린 시계의 중복 구간에서는 서로 다른 두 순간이 반환된다. 앞당긴 시계의 누락 구간에서는 원래 지역 시계 숫자로 되돌아오는 순간이 없으므로 빈 목록이다. `set`은 혹시 같은 UTC 순간이 중복 후보로 나타나더라도 하나로 접는다.

```python
ny = ZoneInfo("America/New_York")

print(possible_instants(datetime(2024, 7, 1, 9, 0), ny))
# [datetime.datetime(2024, 7, 1, 13, 0, tzinfo=datetime.timezone.utc)]

print(possible_instants(datetime(2024, 11, 3, 1, 30), ny))
# [2024-11-03 05:30 UTC, 2024-11-03 06:30 UTC]에 해당하는 두 datetime

print(possible_instants(datetime(2024, 3, 10, 2, 30), ny))
# []
```

이 함수는 **후보 탐지**만 한다. `[]`를 받았을 때 어떤 시각으로 옮길지, 두 값을 받았을 때 어느 것을 택할지는 호출자의 정책이다. 실패를 조용히 기본값으로 바꾸면 예약이 누락되거나 중복 실행되는 원인을 추적하기 어려워진다.

입력 형식도 통제해야 한다. `datetime.fromisoformat()`으로 읽은 값에 오프셋이 포함돼 있으면 aware 객체가 될 수 있다. 이미 오프셋이 있는 입력을 이 함수에 보내 `tzinfo`를 다시 붙이지 않는다. 하나의 API에서 'UTC 순간'과 '지역 시계 예약'을 함께 받는다면 요청 스키마를 구분해 서로 다른 경로로 검증하는 편이 안전하다.

## 6. 반복 일정은 지역 날짜에서 계산하고, 실행은 UTC로 한다

반복 일정의 다음 실행을 계산할 때는 이전 UTC 순간에 24시간을 더하지 않는다. **다음 지역 날짜**를 고른 다음 그 날짜의 목표 시각을 만들고, 해당 날짜의 시간대 규칙으로 UTC 후보를 다시 계산한다.

```python
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo


def next_daily_candidates(
    current_local_date: date, local_time: time, zone: ZoneInfo
) -> list[datetime]:
    if local_time.tzinfo is not None:
        raise ValueError("local_time must be naive")

    next_date = current_local_date + timedelta(days=1)
    wall = datetime.combine(next_date, local_time)
    return possible_instants(wall, zone)
```

예를 들어 2024년 3월 9일 뉴욕 09:00과 3월 10일 뉴욕 09:00 사이에는 실제로 23시간이 흐른다. `UTC + 24h` 방식은 두 번째 실행을 현지 10:00으로 밀어 버린다. 지역 날짜를 하루 증가시키는 방식은 같은 09:00이라는 사용자 의도를 보존한다.

물론 위 함수가 빈 목록을 반환하면 누락 시각 정책을 적용해야 한다. 두 목록을 반환하면 중복 시각 정책을 적용해야 한다. 스케줄러의 데이터 모델에는 최소한 다음 필드가 필요하다.

```text
schedule_id       = "weekly-report-42"
local_time        = "01:30"
zone_key          = "America/New_York"
frequency         = "daily"
fold_policy       = "first" | "second" | "both" | "reject"
gap_policy        = "skip" | "next_valid" | "reject"
next_run_at_utc   = 실제 실행할 단일 UTC 순간(또는 둘일 때 두 실행 레코드)
```

`next_run_at_utc`는 실행 큐가 정렬할 값이고, 나머지 필드는 **다음 실행을 재계산할 근거**다. UTC 순간만 저장하면 향후 DST가 바뀌었을 때 사용자가 원한 '지역 오전 9시'를 복원할 수 없다. 반대로 지역 시각만 저장하면 특정 실행을 정확히 비교·중복 제거하기 어렵다. 두 종류의 정보를 모두 보존해야 한다.

스케줄을 수정하거나 시간대 데이터가 갱신되면 향후 실행을 다시 계산할 수 있다. 이미 발송된 실행의 감사 기록은 당시 실제 실행 UTC 순간, 지역 표시 시각, 적용한 정책을 함께 남기면 좋다. 미래의 시간대 법령이 바뀌어도 과거 사건의 시점을 다시 쓰지 않기 위해서다.

## 7. 시간대 데이터는 배포 의존성이다

`zoneinfo`는 IANA 시간대 데이터가 있어야 동작한다. Python 문서에 따르면 시스템에 시간대 데이터가 있으면 이를 사용하고, 없으면 PyPI의 `tzdata` 패키지를 사용할 수 있다. 둘 다 없으면 `ZoneInfo("America/New_York")`가 `ZoneInfoNotFoundError`를 낸다. 일부 컨테이너나 Windows 배포에서 '개발 환경에서는 되는데 운영에서 실패'하는 이유가 여기에 있다.

운영 검증에서는 단순히 Python 버전만 기록하지 말고, 시간대 데이터 공급원과 갱신 절차를 확인한다. 시간대 규칙은 국가의 법령 변경 등으로 달라질 수 있다. 미래 일정을 월 단위로 미리 UTC에 모두 확정해 두었다면, 시간대 데이터 갱신 후 **아직 실행하지 않은 예약**을 다시 계산해야 할 수 있다. 반면 이미 실행한 이력의 UTC 시각은 수정하지 않는다.

이와 별개로 `ZoneInfo` 객체는 캐시를 사용한다. 시간대 데이터 파일을 교체했다고 해서 이미 떠 있는 장기 실행 프로세스가 즉시 새 규칙을 사용한다고 가정하지 않는다. 배포·재시작·캐시 관리 절차를 통해 새 규칙 적용 시점을 통제하고, 그 시점에 미실행 예약을 재생성해야 한다. 재현 가능한 테스트가 중요하면 CI와 운영에서 사용하는 시간대 데이터의 출처를 맞춘다.

## 8. 검증: 전환 전후와 산술의 의미를 함께 테스트한다

시간대 버그는 '오늘 서울 09:00' 하나만 테스트하면 보이지 않는다. 최소 검증 집합은 다음과 같다.

1. **정상 시각:** 2024-07-01 뉴욕 09:00이 UTC 13:00으로 해석되는가?
2. **중복 시각:** 2024-11-03 뉴욕 01:30에서 UTC 05:30과 06:30이 모두 나오는가?
3. **누락 시각:** 2024-03-10 뉴욕 02:30에서 후보가 없는가?
4. **반복 일정:** 2024-03-09와 3월 10일의 뉴욕 09:00이 각각 24시간이 아니라 23시간 간격인가?
5. **경과 시간:** 같은 `tzinfo` 객체를 가진 두 지역 datetime의 직접 뺄셈 대신 UTC 변환 후 뺄셈을 사용하는가?
6. **운영 의존성:** 실제 배포 이미지에서 필요한 `ZoneInfo` 키가 로드되는가?

다음처럼 핵심 경계를 자동 검증할 수 있다.

```python
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

ny = ZoneInfo("America/New_York")
assert len(possible_instants(datetime(2024, 7, 1, 9), ny)) == 1
assert [x.hour for x in possible_instants(datetime(2024, 11, 3, 1, 30), ny)] == [5, 6]
assert possible_instants(datetime(2024, 3, 10, 2, 30), ny) == []

before = possible_instants(datetime(2024, 3, 9, 9), ny)[0]
after = next_daily_candidates(datetime(2024, 3, 9).date(), time(9), ny)[0]
assert after - before == timedelta(hours=23)
assert after == datetime(2024, 3, 10, 13, tzinfo=timezone.utc)
```

정책 테스트에서는 `fold_policy`와 `gap_policy`별로 결과가 달라야 하고, 같은 실행을 큐에 재등록해도 중복 발송되지 않는지 실행 ID 설계를 확인해야 한다.

## 결론: 순간과 달력 규칙을 별도 데이터로 관리한다

- 저장·정렬·경과 시간 측정에는 aware UTC 순간을 사용한다.
- 반복 예약의 의도는 지역 날짜·시각과 IANA 시간대 키로 보존한다.
- `replace(tzinfo=...)`는 후보를 만들 뿐 유효성을 검증하지 않는다. UTC 왕복으로 누락·중복을 탐지한다.
- `fold`는 중복 시각의 두 후보를 구별한다. 같은 `tzinfo` 객체끼리 직접 뺄셈하면 경과 시간을 잘못 해석할 수 있으므로 UTC에서 계산한다.
- 누락·중복 시각의 처리는 `zoneinfo` 기능이 아니라 제품 정책이다. 이 정책과 시간대 데이터 공급원을 배포·테스트·감사 기록에 명시한다.

'매일 09:00'을 `24h`로 모델링하는 순간 사용자의 달력 규칙을 잃는다. **지역 시계에서 다음 날짜를 정하고, 검증된 UTC 순간으로 실행**하는 순서가 예약 시스템의 안정적인 경계다.

## 근거 문서

- Python `zoneinfo` 공식 문서(IANA 데이터, `fold`, 데이터 공급원): <https://docs.python.org/3.14/library/zoneinfo.html>
- Python `datetime` 공식 문서(aware/naive, 비교·산술, `astimezone`): <https://docs.python.org/3.14/library/datetime.html>
- PEP 495: Local Time Disambiguation (`fold`, gap/fold 의미): <https://peps.python.org/pep-0495/>
- IANA Time Zone Database: <https://www.iana.org/time-zones>
