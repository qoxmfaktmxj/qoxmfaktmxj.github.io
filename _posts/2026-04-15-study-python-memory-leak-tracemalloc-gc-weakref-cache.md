---
layout: post
title: "Python 메모리 누수 실전: tracemalloc, gc, weakref, 캐시와 비동기 참조를 운영 관점에서 추적하는 법"
date: 2026-04-15 11:40:00 +0900
categories: [python]
tags: [study, python, memory-leak, tracemalloc, gc, weakref, cache, asyncio, observability, performance]
permalink: /python/2026/04/15/study-python-memory-leak-tracemalloc-gc-weakref-cache.html
---

## 왜 이 주제가 실무에서 중요할까?

Python 서비스가 운영 단계로 들어가면 CPU보다 더 까다로운 문제가 하나 있다. 바로 **메모리는 천천히 차오르는데, 정확히 어디서 새는지 바로 안 보이는 상황**이다.

이 문제는 단순히 프로세스가 죽는다는 수준에서 끝나지 않는다.

- Kubernetes 환경에서는 OOMKilled가 간헐적으로 발생한다
- 워커 재시작 주기가 짧아지면서 tail latency가 흔들린다
- 캐시 적중률을 높이려던 코드가 오히려 장기 메모리 점유를 만든다
- 배치는 성공했는데 하루가 지날수록 RSS가 우상향한다
- FastAPI, Celery, Kafka consumer, 스케줄러가 몇 시간 후부터 점점 둔해진다
- 운영자는 "GC가 안 도나?" 같은 모호한 추측을 반복하게 된다

더 어려운 이유는, 메모리 문제의 상당수가 전통적인 의미의 "누수(leak)"만은 아니기 때문이다.

실무에서 자주 섞여 나타나는 현상은 대체로 네 가지다.

1. **진짜 참조 누수**
   - 객체가 더 이상 필요 없는데 전역 컬렉션, 캐시, 콜백 레지스트리, task registry에 남아 회수되지 않는 경우
2. **정상 동작이지만 과도한 보존(retention)**
   - 캐시 정책이 없어서 의도치 않게 메모리를 오래 잡는 경우
3. **Python 힙은 줄었는데 RSS가 안 내려가는 경우**
   - allocator 특성 때문에 OS 메모리 반환이 늦어 보이는 경우
4. **Python 밖 메모리 사용량 증가**
   - C extension, NumPy/Pandas 버퍼, DB driver, 압축 라이브러리 등 `tracemalloc` 밖의 영역이 커지는 경우

즉, 메모리 문제는 "한 줄 버그"보다 **객체 생명주기와 운영 관측이 맞물린 설계 문제**에 가깝다.

오늘 글은 아래 질문에 답하는 데 집중한다.

- Python 메모리 누수를 진짜 누수와 착시로 어떻게 구분할까?
- `tracemalloc`, `gc`, `weakref`는 각각 어디까지 믿어야 할까?
- 캐시, 이벤트 핸들러, 비동기 task, 전역 상태가 왜 누수의 주범이 될까?
- 운영 환경에서 어떤 계측과 절차를 기본값으로 가져가야 할까?
- 성급한 `gc.collect()`나 무제한 캐시 같은 흔한 실수를 어떻게 피할까?

핵심만 먼저 요약하면 이렇다.

- 메모리 문제의 본질은 대개 **할당량**보다 **참조가 얼마나 오래 살아남는가**에 있다
- `tracemalloc`은 Python 객체 추적에는 강하지만, **프로세스 전체 메모리 원인 분석 도구는 아니다**
- `gc`는 만능 청소기가 아니라 **순환 참조를 보조적으로 회수하는 장치**다
- `weakref`는 자동 마법이 아니라 **소유권이 없는 참조를 모델링할 때만** 효과적이다
- 실전 해법은 한 번의 덤프보다 **지속 계측 + 스냅샷 비교 + 생명주기 설계 수정**의 조합이다

---

## 배경: 왜 메모리 이슈는 재현이 어렵고, 늦게 터질까?

메모리 문제는 로컬 개발 환경에서 잘 안 보인다. 트래픽이 적고, 데이터 크기가 작고, 프로세스 수명이 짧기 때문이다.

하지만 운영에서는 조건이 완전히 달라진다.

- 같은 프로세스가 몇 시간에서 며칠씩 살아남는다
- 다양한 테넌트와 키 조합이 캐시에 쌓인다
- 예외 케이스 payload가 섞이면서 객체 크기 분포가 커진다
- 실패 재시도와 background task가 참조를 오래 붙든다
- 관측은 RSS만 보고, 개발자는 Python 객체만 보고 있어 서로 다른 그림을 본다

예를 들어 이런 상황을 생각해보자.

- API 서버는 요청당 응답 캐시를 만든다
- 캐시 키는 `tenant_id:user_id:query_hash`처럼 사실상 무한대에 가깝다
- 운영 첫날은 문제없다
- 3일 뒤부터 메모리가 천천히 우상향한다
- 개발자는 `lru_cache`를 썼으니 안전하다고 생각한다
- 실제로는 `maxsize=None` 이거나, 인스턴스 메서드에 잘못 붙여 객체 자체를 오래 붙들고 있다

이런 류의 문제는 테스트 한 번으로 잡기 어렵다. 그래서 메모리 대응은 코드 감각보다 **분류 체계**가 먼저 필요하다.

### 먼저 구분해야 하는 3가지 질문

#### 1) Python 객체 수가 늘고 있는가?

이 질문은 `tracemalloc`, 객체 카운트, 힙 스냅샷 비교로 접근한다.

#### 2) Python 객체는 줄었는데 RSS만 안 내려가는가?

이 경우 allocator, fragmentation, arena 재사용, C extension 버퍼 같은 요인을 봐야 한다.

#### 3) 증가가 누수인가, 의도된 보존인가?

캐시, 세션, 배치 버퍼, in-memory index는 설계상 보존일 수 있다. 문제는 그 보존이 **상한 없이** 커지는 순간이다.

메모리 트러블슈팅의 절반은 기술보다 이 분류를 제대로 하는 데서 끝난다.

---

## 핵심 개념 1: Python 메모리는 "누가 참조를 잡고 있나"로 이해해야 한다

Python에서 객체가 해제되는 가장 기본 원리는 참조 카운트다. 어떤 객체를 가리키는 참조가 0이 되면 해제 가능 상태가 된다. 여기에 순환 참조를 처리하기 위해 cyclic GC가 추가로 개입한다.

즉 실무적으로 중요한 질문은 이거다.

> 이 객체가 왜 아직 살아 있는가?

대부분의 메모리 문제는 아래 네 군데 중 하나에서 참조가 예상보다 오래 남기 때문에 생긴다.

- 전역 딕셔너리, 싱글톤, 모듈 레벨 리스트
- 캐시와 레지스트리
- 클로저, 콜백, signal handler, observer 목록
- 비동기 task, future, retry queue, dead-letter 보관 구조

### 전형적인 누수 패턴 1: 전역 컬렉션이 끝없이 커진다

```python
request_history: list[dict] = []


def record_request(meta: dict) -> None:
    request_history.append(meta)
```

처음엔 디버깅용으로 넣은 코드가 운영에서 누수가 된다. 더 무서운 건, 이 코드는 테스트에서도 잘 통과한다는 점이다.

### 전형적인 누수 패턴 2: 캐시인데 eviction이 없다

```python
from functools import lru_cache


@lru_cache(maxsize=None)
def load_schema(tenant_id: str, version: str) -> dict:
    ...
```

`maxsize=None`은 사실상 무제한 메모리 사용 허용과 비슷하다. 테넌트 수, 버전 수, 키 공간이 커지면 누수처럼 보이는 retention을 만든다.

### 전형적인 누수 패턴 3: 완료된 task를 registry에서 제거하지 않는다

```python
background_tasks: set = set()


def spawn(coro):
    task = asyncio.create_task(coro)
    background_tasks.add(task)
    return task
```

이 코드는 task를 추적하려는 의도 자체는 맞다. 문제는 **완료 후 정리**가 없다는 점이다. 완료된 task도 set 안에 남아 결과, 예외, 클로저 참조를 붙든다.

안전한 기본형은 이렇게 가깝다.

```python
background_tasks: set[asyncio.Task] = set()


def spawn(coro):
    task = asyncio.create_task(coro)
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)
    return task
```

### 전형적인 누수 패턴 4: 클로저가 큰 객체를 붙든다

```python
def build_handler(big_lookup: dict):
    def handler(key: str):
        return big_lookup.get(key)
    return handler
```

클로저 자체는 나쁜 게 아니다. 하지만 오래 사는 핸들러가 큰 딕셔너리를 캡처하면, 원래는 요청 범위였어야 할 데이터가 애플리케이션 수명만큼 살아남는다.

핵심은 간단하다. 메모리 이슈를 만나면 "GC가 왜 안 치우지?"보다 먼저 **무엇이 참조를 계속 붙들고 있지?**를 봐야 한다.

---

## 핵심 개념 2: `tracemalloc`은 가장 먼저 켜야 하지만, 모든 메모리를 설명하지는 못한다

`tracemalloc`은 Python 메모리 진단의 출발점으로 매우 좋다. 특히 **어느 파일/라인에서 할당이 늘고 있는지 비교**하는 데 강하다.

기본 패턴은 이렇다.

```python
import tracemalloc

tracemalloc.start(25)

# 워밍업 이후 기준 스냅샷
snap1 = tracemalloc.take_snapshot()

run_workload()

snap2 = tracemalloc.take_snapshot()
for stat in snap2.compare_to(snap1, 'lineno')[:10]:
    print(stat)
```

### `tracemalloc`이 잘하는 것

- Python 레벨 할당 hot spot 찾기
- 변경 전후 스냅샷 diff 비교
- 특정 모듈, 파일, 라인 기준 증가량 파악
- 누수 후보 코드 경로를 빠르게 좁히기

### `tracemalloc`이 못하는 것

- 프로세스 RSS 전체를 직접 설명하기
- NumPy, 일부 DB driver, 압축 라이브러리, 이미지 처리 라이브러리 등의 C 레벨 메모리 추적
- 메모리가 해제되었지만 allocator가 OS에 즉시 반환하지 않는 현상 설명

즉 `tracemalloc` 결과가 조용한데 RSS가 계속 오른다면, 두 가능성을 의심해야 한다.

1. Python 바깥 메모리가 오른다
2. Python 객체는 줄었지만 allocator 관점에서 재사용 가능한 메모리가 프로세스 내부에 남아 있다

### 실전에서 유용한 스냅샷 비교 패턴

```python
import tracemalloc
from collections.abc import Callable


def profile_growth(fn: Callable[[], None]) -> None:
    tracemalloc.start(25)

    baseline = tracemalloc.take_snapshot()
    fn()
    current = tracemalloc.take_snapshot()

    filters = [
        tracemalloc.Filter(False, "<frozen importlib._bootstrap>"),
        tracemalloc.Filter(False, "<unknown>"),
    ]

    for stat in current.filter_traces(filters).compare_to(
        baseline.filter_traces(filters),
        "lineno",
    )[:20]:
        print(stat)
```

여기서 중요한 건 **언제 baseline을 잡느냐**다.

- import 폭탄이 끝난 뒤
- connection pool이 올라온 뒤
- JIT 대신 interpreter warm-up이 끝난 뒤
- 초기 캐시 프라이밍이 끝난 뒤

즉, 애플리케이션이 정상 steady state에 들어간 다음 기준점을 잡아야 한다. 그렇지 않으면 단순 초기화 비용을 누수로 착각한다.

### 운영에서 `tracemalloc`을 항상 켜도 될까?

상황에 따라 다르다. 메모리와 성능 오버헤드가 있으므로 모든 환경의 영구 기본값으로 두기보다 아래 방식이 보통 낫다.

- 장애 재현용 canary pod에서만 활성화
- 특정 관리 엔드포인트나 feature flag로 on/off
- 샘플링된 워커에서만 활성화
- 배치 잡의 특정 실행 구간만 감싸서 스냅샷 수집

핵심은 "항상 켜기"보다 **필요할 때 일관된 절차로 켤 수 있게 해두는 것**이다.

---

## 핵심 개념 3: `gc`는 메모리 누수 해결사가 아니라 순환 참조 보조 장치다

실무에서 메모리 이슈가 생기면 `gc.collect()`를 본능처럼 넣는 경우가 많다. 하지만 이 접근은 대개 문제를 숨기거나 지연시킬 뿐이다.

먼저 모델을 정확히 잡자.

- 참조 카운트가 0이 되면 많은 객체는 즉시 해제 가능하다
- `gc`는 주로 **순환 참조**를 처리한다
- 즉, 전역 캐시나 레지스트리가 참조를 계속 들고 있으면 `gc.collect()`는 아무 소용이 없다

### `gc`가 특히 필요한 장면

- 객체 그래프가 서로를 참조하는 구조
- callback, observer, parent-child 관계가 양방향으로 얽힌 구조
- 예외 객체, traceback, frame 참조가 남는 구조

### `gc`를 볼 때 체크할 것

```python
import gc

print(gc.get_count())
print(gc.get_threshold())
```

이 숫자는 GC 세대별 상태를 보여주지만, 이것만 보고 누수를 진단할 수는 없다. 대신 아래가 더 실용적이다.

- 특정 부하 전후 `gc.get_objects()` 수 변화
- `gc.collect()` 후에도 살아남는 객체 유형
- `gc.get_referrers()`로 누가 참조를 들고 있는지 확인

예를 들면 이렇게 객체 보존 여부를 볼 수 있다.

```python
import gc


def count_type(cls: type) -> int:
    return sum(1 for obj in gc.get_objects() if isinstance(obj, cls))
```

물론 이 방법은 비용이 크고 모든 타입에 적합하지 않다. 그래서 운영 상시 계측보다는 **문제 재현 환경**에서 제한적으로 써야 한다.

### `__del__`과 finalizer는 특히 조심해야 한다

복잡한 객체 그래프에 `__del__`이 들어가면 해제 시점이 예측하기 어려워지고, 순환 참조 처리도 더 까다로워질 수 있다. 리소스 해제는 가능하면 아래 우선순위가 더 안전하다.

1. 명시적 `close()` / `aclose()`
2. context manager (`with`, `async with`)
3. 필요한 경우 `weakref.finalize`
4. 마지막 수단으로 `__del__`

실무적으로는 "GC가 언젠가 치워주겠지"보다 **생명주기를 코드로 닫아라**가 훨씬 안전한 기본값이다.

---

## 핵심 개념 4: `weakref`는 소유권이 없는 연결을 표현할 때 강력하다

`weakref`는 메모리를 마법처럼 줄여주는 도구가 아니다. 대신 **이 객체를 내가 소유하지는 않지만, 살아 있는 동안만 연결을 따라가고 싶다**는 관계를 표현할 때 매우 유용하다.

대표적인 사용처는 아래와 같다.

- observer / subscriber 목록
- 플러그인 registry
- 캐시에서 값의 생존을 강제하지 않고 싶을 때
- 부모가 자식을 소유하지만, 자식이 부모를 강하게 붙들 필요는 없을 때

### 왜 observer 패턴에서 유용할까?

이벤트 버스가 subscriber 콜백을 강한 참조로 들고 있으면, 이미 수명을 다한 객체도 해제되지 않는다.

```python
import weakref


class EventBus:
    def __init__(self):
        self._handlers = weakref.WeakSet()

    def subscribe(self, handler):
        self._handlers.add(handler)

    def publish(self, event):
        for handler in list(self._handlers):
            handler(event)
```

물론 모든 callable이 `WeakSet`에 자연스럽게 들어가는 건 아니다. bound method를 다룰 때는 `weakref.WeakMethod`가 더 적합할 수 있다. 중요한 건 구체 API보다 **관계의 소유권을 명확히 모델링하는 습관**이다.

### `weakref`가 부적합한 경우

- 캐시에 값을 반드시 보존해야 하는 경우
- 생명주기가 명확한 핵심 도메인 객체
- 참조가 사라지면 안 되는 작업 큐, 상태 저장소

즉 `weakref`는 누수 해결 버튼이 아니라, **강한 참조를 가져서는 안 되는 관계를 강제로 모델링하는 장치**다.

---

## 실무 예시 1: 멀티테넌트 응답 캐시가 메모리 누수처럼 보일 때

가장 흔한 사례 중 하나가 "성능 최적화용 캐시"다.

```python
cache: dict[str, dict] = {}


def get_dashboard(tenant_id: str, user_id: str, filters: tuple) -> dict:
    key = f"{tenant_id}:{user_id}:{filters}"
    if key not in cache:
        cache[key] = build_dashboard(tenant_id, user_id, filters)
    return cache[key]
```

처음엔 아주 잘 동작한다. 문제는 키 공간이 사실상 무제한이라는 점이다.

- tenant 수가 늘어난다
- user 조합이 늘어난다
- filters 조합이 폭발한다
- 한 번 생성된 엔트리는 끝까지 남는다

이 경우는 엄밀히 말하면 전통적 누수보다 **무제한 retention**에 가깝다. 하지만 운영 관점에서는 결과가 같다. 메모리가 계속 오른다.

### 개선 기준

1. 엔트리 수 상한이 있는가?
2. TTL이 있는가?
3. 값 크기 기준 제거 전략이 있는가?
4. 테넌트별 hot key와 cold key를 구분하는가?
5. 프로세스 로컬 캐시가 맞는가, 아니면 외부 캐시로 빼야 하는가?

예를 들어 단일 프로세스 캐시라면 최소한 아래 정도는 기본값으로 생각할 수 있다.

- `cachetools.TTLCache` 같은 TTL + 최대 크기 조합
- 값이 큰 객체는 프로세스 메모리 대신 Redis나 CDN 쪽으로 이동
- 캐시 키 cardinality를 메트릭으로 노출
- 캐시 hit rate뿐 아니라 **entry count, memory estimate, eviction count**도 함께 모니터링

많은 팀이 hit rate만 본다. 하지만 메모리 관점에서는 **어떤 키 공간을 얼마나 오래 붙들고 있나**가 더 중요하다.

---

## 실무 예시 2: 비동기 background task registry가 완료된 작업을 계속 붙드는 경우

API 서버나 consumer에서 fire-and-forget 패턴을 쓰다 보면 이런 코드가 쉽게 생긴다.

```python
tasks: set[asyncio.Task] = set()


async def schedule_email(payload: dict) -> None:
    task = asyncio.create_task(send_email(payload))
    tasks.add(task)
```

이 구조는 두 문제가 있다.

1. 완료된 task가 제거되지 않는다
2. task 내부에서 캡처한 payload, 예외, traceback이 같이 남을 수 있다

특히 예외가 발생한 task는 결과 소비 방식에 따라 traceback 체인이 메모리를 더 오래 붙들 가능성이 있다.

더 안전한 기본형은 다음과 같다.

```python
tasks: set[asyncio.Task] = set()


def create_tracked_task(coro) -> asyncio.Task:
    task = asyncio.create_task(coro)
    tasks.add(task)

    def _cleanup(done: asyncio.Task) -> None:
        tasks.discard(done)
        try:
            done.result()
        except Exception:
            logger.exception("background task failed")

    task.add_done_callback(_cleanup)
    return task
```

여기서 핵심은 세 가지다.

- registry는 **추적 목적**이지 영구 보관소가 아니다
- 완료 즉시 제거한다
- 예외를 소비하고 기록해 참조가 불필요하게 길어지지 않게 한다

더 좋은 구조는 아예 ad-hoc background task 대신 **명시적 worker queue**나 `TaskGroup` 기반 수명 관리 구조로 바꾸는 것이다. 메모리 문제는 대개 task 자체보다 **소유권이 없는 task 생성**에서 시작된다.

---

## 실무 예시 3: 배치 처리에서 리스트 누적이 눈에 띄지 않게 메모리를 잡아먹는 경우

데이터 배치 코드에서 흔한 실수는 결과를 전부 메모리에 모은 뒤 한 번에 쓰는 방식이다.

```python
rows = []
for item in source:
    rows.append(transform(item))

write_to_db(rows)
```

처음에는 데이터가 1만 건이라 괜찮다. 어느 날 500만 건이 들어오면 바로 무너진다.

이 문제는 엄밀한 의미의 누수는 아니지만, 운영자 관점에서는 메모리가 점진적으로 차오르고 오래 안 내려가는 현상으로 보인다.

### 더 안전한 기본값

- generator로 스트리밍 처리
- 일정 batch size마다 flush
- 큰 중간 결과는 디스크 스풀 또는 외부 저장소 사용
- pandas 같은 컬럼 지향 라이브러리는 chunk 단위 처리

예를 들면 이렇게 바꿀 수 있다.

```python
def iter_rows(source):
    for item in source:
        yield transform(item)


batch = []
for row in iter_rows(source):
    batch.append(row)
    if len(batch) >= 1000:
        write_to_db(batch)
        batch.clear()

if batch:
    write_to_db(batch)
```

메모리 최적화의 핵심은 종종 고급 테크닉이 아니라 **한 번에 잡는 데이터의 상한을 명시하는 것**이다.

---

## 실무 예시 4: 요청 스코프 객체가 전역 로거/콜백에 섞여 들어가는 경우

관측을 강화하려고 request 객체나 ORM session 자체를 로깅 컨텍스트에 넣는 경우가 있다. 이건 매우 위험하다.

- request body가 크면 그만큼 오래 붙든다
- ORM session은 내부적으로 많은 객체 그래프를 참조한다
- 예외 traceback과 결합되면 참조 체인이 훨씬 커진다

그래서 로깅 컨텍스트에는 아래처럼 **식별자만** 넣는 편이 안전하다.

좋은 값:

- request_id
- tenant_id
- actor_id
- trace_id
- endpoint name

나쁜 값:

- request 객체 전체
- session 객체 전체
- 응답 payload 원문
- 대형 도메인 엔티티

메모리뿐 아니라 로깅 보안과 성능 측면에서도 같은 원칙이 통한다. **운영 메타데이터는 작고, 직렬화 가능하고, 생명주기가 짧아야 한다.**

---

## 운영 절차: 메모리 이슈가 터졌을 때 어떻게 추적할까?

실무에서는 도구보다 절차가 중요하다. 내가 추천하는 기본 순서는 아래와 같다.

### 1) 먼저 Python 객체 문제인지, 프로세스 RSS 문제인지 분리한다

확인할 메트릭 예시:

- `process_resident_memory_bytes`
- 컨테이너 working set / rss
- 요청 수, 배치 건수, consumer lag
- cache entry count
- background task 수

여기서 RSS만 오르고 Python 스냅샷 증가는 미미하면, C extension 또는 allocator 관점으로 넘어가야 한다.

### 2) steady state 이후 기준 스냅샷을 잡는다

- import 직후가 아니라 워밍업 이후
- connection pool 생성 이후
- 초기 캐시 적재 이후

### 3) 같은 workload를 여러 번 반복해 증가분이 누적되는지 본다

진짜 누수는 보통 같은 시나리오를 반복할수록 증가분이 누적된다. 일회성 피크는 누수가 아닐 수 있다.

### 4) 증가한 타입과 참조 소유자를 좁힌다

- `tracemalloc` diff
- `gc.get_objects()` 기반 타입 카운트
- `gc.get_referrers()`로 참조 주체 확인

### 5) 코드 수정은 수집보다 생명주기 쪽에서 한다

문제 코드가 보이면 대개 해법은 아래 중 하나다.

- 전역 참조 제거
- 캐시 상한 도입
- 완료 후 registry cleanup
- 큰 객체 대신 식별자만 보관
- 명시적 close / context manager 도입

### 6) 수정 후에는 메모리 감소 자체보다 "증가 기울기 변화"를 본다

메모리 문제 검증에서 가장 흔한 실수가 "재현 후 메모리가 당장 크게 떨어지지 않았다"만 보고 실패로 판단하는 것이다.

중요한 건 아래다.

- 반복 workload에서 증가 기울기가 사라졌는가?
- long-running test에서 plateau가 생기는가?
- pod 재시작 없이도 안정 범위 안에 머무는가?

---

## 트레이드오프: 성능 최적화와 메모리 안정성은 자주 충돌한다

메모리 문제를 줄이려면 대개 캐시를 줄이고, 객체 수명을 짧게 하고, 중간 결과를 빨리 버려야 한다. 그런데 이 선택은 성능과 충돌한다.

### 1) 큰 캐시는 응답 시간을 줄이지만, cardinality가 크면 메모리 사고를 만든다

- 장점: 계산 비용 감소, DB 부하 감소
- 단점: 키 공간이 크면 사실상 메모리 기반 폭탄

권장 기준은 "캐시할지 말지"보다 **무엇을 얼마나 오래 어떤 상한으로 캐시할지**를 명시하는 것이다.

### 2) `weakref`는 누수를 줄일 수 있지만, 생존 보장을 약하게 만든다

- 장점: observer, plugin registry에서 참조 꼬임 감소
- 단점: 예상보다 빨리 사라질 수 있어 디버깅이 어려워질 수 있음

즉 핵심 도메인 상태 저장에는 부적합하고, 소유권 없는 연결에만 써야 한다.

### 3) aggressive GC는 메모리 피크를 줄일 수 있지만, latency를 흔들 수 있다

- 장점: 특정 워크로드에서 오래 남는 순환 참조를 빨리 정리
- 단점: 응답 지연 증가, CPU 사용량 증가, 근본 원인 은폐

GC 튜닝은 마지막 수단에 가깝다. 대부분의 서비스는 GC threshold보다 **참조 구조 설계**를 먼저 고쳐야 한다.

### 4) 배치 크기를 줄이면 메모리는 안정적이지만 처리량이 낮아질 수 있다

- 장점: peak memory 제어 쉬움
- 단점: flush 빈도 증가, I/O 호출 수 증가

이 경우는 throughput과 메모리 예산 사이의 균형점 탐색이 필요하다. 핵심은 "batch size는 상수인가"가 아니라 **메모리 예산 기준으로 동적으로 조정 가능한가**다.

---

## 흔한 실수 1: `gc.collect()`를 요청마다 호출한다

이건 거의 항상 나쁜 선택이다.

- 지연 시간이 튄다
- 근본 원인을 숨긴다
- 전역 참조나 무제한 캐시는 해결하지 못한다

정말 필요한 경우는 특정 배치 구간 종료 후 대형 순환 참조 해제를 돕는 상황 정도다. 웹 요청마다 호출하는 건 운영 기본값이 아니다.

## 흔한 실수 2: `tracemalloc`이 조용하면 누수가 없다고 결론 내린다

아니다. `tracemalloc`은 Python 메모리 할당 추적 도구지, 프로세스 전체 진실의 원천이 아니다.

- NumPy / pandas 버퍼
- 압축 라이브러리 버퍼
- DB driver 내부 메모리
- allocator fragmentation

이런 문제는 `tracemalloc`만으로 안 잡힌다.

## 흔한 실수 3: 캐시 hit rate만 보고 entry count를 보지 않는다

캐시는 성능 도구이면서 동시에 메모리 소비기다. hit rate가 좋아도 entry 수와 value size가 폭증하면 운영 실패다.

반드시 같이 봐야 할 것:

- entry count
- eviction count
- TTL 만료 수
- estimated memory size
- key cardinality 증가 추세

## 흔한 실수 4: 예외 traceback을 오래 보관한다

재처리나 디버깅 목적으로 예외 객체를 컬렉션에 쌓아두면 traceback이 frame과 로컬 변수를 붙든다. 이러면 생각보다 큰 그래프가 살아남는다.

예외 자체를 장기 보관하기보다 아래가 낫다.

- 문자열화된 요약 저장
- 필요한 식별자만 추출 저장
- 원문 traceback은 로그/외부 저장소에 남기고 메모리에는 오래 두지 않기

## 흔한 실수 5: 인스턴스 메서드에 무심코 캐시를 건다

인스턴스 메서드 캐시는 `self`까지 키에 포함될 수 있고, 객체 수명 자체를 늘릴 수 있다. 서비스 객체가 많거나 동적 생성되면 예상보다 메모리를 크게 잡는다.

이 경우는 아래를 먼저 고민해야 한다.

- 캐시를 인스턴스 대신 모듈 레벨 순수 함수로 옮길 수 있는가?
- 키 공간 상한이 있는가?
- 객체 수명과 캐시 수명이 일치하는가?

---

## 실전 체크리스트: 운영 가능한 Python 메모리 관리 기준

### 설계 단계

- [ ] 전역 컬렉션, 싱글톤, registry에 상한과 정리 규칙이 있는가?
- [ ] 캐시는 `maxsize`, TTL, eviction metric 없이 도입하지 않았는가?
- [ ] request/session/domain object 전체를 로그 컨텍스트에 넣지 않았는가?
- [ ] background task는 생성 주체와 종료 책임이 명확한가?
- [ ] 큰 중간 결과는 streaming/chunking으로 쪼갤 수 있는가?

### 구현 단계

- [ ] 완료된 task는 registry에서 제거하는가?
- [ ] callback/observer는 강한 참조가 꼭 필요한지 검토했는가?
- [ ] `with`, `async with`, `close()`, `aclose()`로 리소스 수명을 명시했는가?
- [ ] 예외 객체와 traceback을 메모리에 오래 쌓아두지 않는가?
- [ ] 디버그용 리스트/딕셔너리가 운영 코드에 남아 있지 않은가?

### 운영 단계

- [ ] RSS와 Python 메모리 관측을 구분해 보고 있는가?
- [ ] cache entry count, task 수, queue backlog를 메트릭으로 노출했는가?
- [ ] steady state 이후 `tracemalloc` 스냅샷을 수집할 절차가 있는가?
- [ ] 동일 workload 반복 시 메모리 증가 기울기를 비교하는가?
- [ ] OOM 이후 재시작 빈도만 보지 말고 증가 원인을 분류하는가?

---

## 한 단계 더: 팀 차원의 메모리 대응 문화를 만들자

메모리 문제는 개인 디버깅 역량만으로 해결되지 않는다. 팀 기본값이 중요하다.

내가 추천하는 팀 규칙은 아래와 같다.

### 1) 캐시 PR에는 반드시 상한과 관측 항목을 함께 넣는다

캐시를 도입하는 PR에서 아래 질문이 빠지면 나중에 거의 반드시 문제가 된다.

- 최대 엔트리 수는?
- TTL은?
- value 크기 추정은?
- 메트릭은 어떻게 노출할까?
- 프로세스 로컬 캐시가 맞나, 외부 캐시가 맞나?

### 2) background task는 "누가 끝내는가"를 코드에서 드러낸다

`create_task()`를 쓰는 순간, 생성 자체보다 **회수 책임**이 중요하다. 가능하면 `TaskGroup`, worker pool, queue 기반 구조를 우선한다.

### 3) 메모리 회귀 테스트를 장기 반복 시나리오로 만든다

단일 요청 성능 테스트만으로는 메모리 누수를 잘 못 잡는다. 아래처럼 보는 편이 낫다.

- 같은 시나리오 1000회 반복
- 10분, 30분, 2시간 장기 러닝
- 증가 기울기 비교
- 캐시/registry 크기 동반 관측

### 4) "메모리 떨어졌는가"보다 "상한 안에서 안정적인가"를 본다

현대 서비스는 메모리를 일부 잡아두고 재사용하는 편이 더 빠를 수 있다. 중요한 건 완전한 0 복귀가 아니라 **예산 안에서 plateau를 형성하는가**다.

즉 좋은 목표는 "항상 메모리가 작다"가 아니라 **예측 가능하게 유지된다**다.

---

## 한 줄 정리

Python 메모리 누수 대응의 핵심은 GC를 믿고 기다리는 것이 아니라, `tracemalloc`으로 증가 지점을 좁히고, `gc`와 참조 추적으로 소유권을 확인한 뒤, 캐시·레지스트리·비동기 task의 생명주기를 상한 있는 구조로 다시 설계하는 데 있다.