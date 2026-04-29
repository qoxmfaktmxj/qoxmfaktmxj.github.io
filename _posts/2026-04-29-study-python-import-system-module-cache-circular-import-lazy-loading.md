---
layout: post
title: "Python import system 실전: sys.modules, circular import, lazy import, plugin discovery, startup 성능까지 운영 기준으로 이해하기"
date: 2026-04-29 11:40:00 +0900
categories: [python]
tags: [study, python, import-system, sys-modules, circular-import, lazy-import, plugin, packaging, startup-performance]
permalink: /python/2026/04/29/study-python-import-system-module-cache-circular-import-lazy-loading.html
---

## 왜 이 주제가 실무에서 중요할까?

Python 프로젝트가 커질수록 성능 문제, 구조 문제, 배포 문제의 시작점에 `import`가 있는 경우가 정말 많다.

초기에는 잘 느껴지지 않는다.

작은 스크립트에서는 `import`가 단순히 파일을 가져오는 문장처럼 보이기 때문이다.

하지만 서비스가 커지면 아래 문제가 반복된다.

- FastAPI 앱이 cold start 때만 유독 느리다
- CLI는 간단한 하위 명령만 실행하는데도 실행 시작 시간이 길다
- 테스트 한 파일만 돌리려는데 import side effect 때문에 DB 연결이 먼저 열린다
- 모듈 구조를 정리하다가 갑자기 `cannot import name ... from partially initialized module ...` 오류가 난다
- `__init__.py`에 편의 import를 추가했더니 패키지 전체 결합도가 급격히 올라간다
- plugin 구조를 붙였는데 동적 로딩 시점과 타입 참조가 뒤엉킨다
- worker 프로세스가 많아질수록 import 비용이 부팅 시간과 메모리를 잠식한다
- 로컬에서는 되는데 배포 환경에서는 `ModuleNotFoundError`가 터진다
- editable install과 직접 `python path/to/file.py` 실행이 섞이면서 상대 import가 깨진다
- 순환 참조를 막겠다고 함수 내부 import를 남발하다가 startup은 빨라졌지만 구조는 더 나빠진다

이 문제들은 따로 떨어져 있지 않다.

대개 공통 뿌리가 있다.

바로 **Python import system을 파일 include 수준으로만 이해하고, 모듈 초기화와 실행 순서, 캐시, 패키징 경계, 런타임 비용을 한 덩어리로 보지 못하는 것**이다.

실무에서 `import`는 단순 문법이 아니다.

- 코드 의존성 그래프를 만든다
- 모듈 초기화 시점을 결정한다
- startup latency를 만든다
- 글로벌 상태 생성 시점을 결정한다
- 테스트 격리 가능성을 좌우한다
- packaging과 배포 성공률에 직접 영향을 준다
- plugin 확장성과 아키텍처 결합도를 바꾼다

즉 `import`는 문법이 아니라 **런타임 구조와 초기화 전략**에 가깝다.

오늘 글은 아래 질문에 답하는 데 집중한다.

- Python은 `import`를 내부적으로 어떤 단계로 처리할까?
- `sys.modules`는 왜 중요한가?
- 순환 import는 왜 생기고, 왜 어떤 경우는 되고 어떤 경우는 깨질까?
- startup 성능 문제를 import 관점에서 어떻게 분석해야 할까?
- `__init__.py`, 상대 import, editable install, `python -m` 실행 방식은 왜 실무에서 중요할까?
- lazy import는 언제 유용하고, 언제 냄새 나는 임시 처방일까?
- plugin discovery 구조를 import 친화적으로 설계하려면 무엇을 지켜야 할까?

핵심만 먼저 요약하면 이렇다.

- Python의 `import`는 파일 복사가 아니라 **모듈 탐색, 스펙 생성, 모듈 객체 생성, 캐시 등록, 모듈 코드 실행**의 연쇄 과정이다
- `sys.modules`는 단순 캐시가 아니라 **초기화 중인 모듈을 포함한 단일 진실 소스**다
- 순환 import의 본질은 대개 "A가 B를 참조해서"가 아니라 **초기화 시점에 아직 준비되지 않은 이름을 너무 일찍 요구하는 것**이다
- startup 성능 문제는 import 개수보다 **side effect, heavy dependency, eager initialization, package boundary 설계**가 더 크게 좌우한다
- 함수 내부 import, `TYPE_CHECKING`, entry point 기반 plugin discovery, app factory 분리는 모두 import 문제를 구조적으로 푸는 도구다
- 가장 좋은 해결은 import 우회가 아니라 **의존성 방향과 초기화 책임을 다시 설계하는 것**이다

---

## 먼저 큰 그림: Python import를 "코드 로딩"이 아니라 "초기화 파이프라인"으로 봐야 한다

많은 개발자가 아래처럼 생각한다.

```python
import app.services.user
```

겉보기에는 "해당 파일을 읽어서 쓸 수 있게 만든다" 정도로 느껴진다.

하지만 실제로는 더 많은 일이 일어난다.

1. 현재 모듈 이름을 기준으로 import 대상의 절대 이름을 해석한다
2. `sys.modules`에 이미 있는지 확인한다
3. 없으면 finder들이 모듈을 어디서 찾을지 결정한다
4. loader가 module spec을 바탕으로 모듈 객체를 만든다
5. **모듈 객체를 먼저 `sys.modules`에 등록한다**
6. 그다음 모듈 파일의 top-level 코드를 실행한다
7. 실행이 끝난 뒤 다른 코드가 그 모듈 객체를 사용한다

여기서 실무적으로 정말 중요한 포인트는 두 가지다.

### 1) import는 실행이다

모듈 파일의 top-level 코드는 선언만 하는 게 아니다.

그 안에 아래가 있으면 import 시점에 바로 실행된다.

- DB 연결 생성
- 환경 변수 읽기
- 로거 설정
- 모델 로딩
- 네트워크 호출
- 캐시 warm-up
- 파일 스캔
- plugin 등록

즉 `import`는 "가져오기"이기도 하지만 동시에 **초기화 부작용을 언제 실행할지 정하는 행위**다.

### 2) import는 한 번만 실행되는 게 아니라, "한 번 초기화되고 이후 재사용"된다

정확히 말하면 같은 인터프리터 안에서 같은 모듈 이름은 보통 한 번 초기화된 뒤 `sys.modules`에서 재사용된다.

이 특성 덕분에 import는 효율적이지만, 동시에 아래 문제도 만든다.

- 모듈 초기화 순서에 따라 동작이 달라질 수 있다
- 테스트에서 글로벌 상태가 남는다
- 순환 import 시 partially initialized module이 노출된다
- reload 없이 설정 변경이 반영되지 않는다

즉 import 이해의 출발점은 이 한 줄이다.

> Python import는 파일 include가 아니라, **이름 기반 모듈 객체 생성과 초기화 생명주기 관리**다.

---

## 배경: 왜 import 문제는 코드가 커질수록 폭발적으로 늘어날까?

작은 프로젝트에서는 import 구조가 단순하다.

- 파일 수가 적다
- 계층이 얕다
- top-level side effect가 작다
- 실행 경로도 몇 개 없다

하지만 서비스가 커지면 import 그래프가 아래처럼 복잡해진다.

- API layer가 service를 import한다
- service가 repository를 import한다
- repository가 model을 import한다
- model이 settings를 import한다
- settings가 logger를 import한다
- logger가 tracing 초기화 모듈을 import한다
- tracing이 again settings를 import한다

이제 구조 문제는 코드 라인 수보다 **초기화 순서**의 문제가 된다.

예를 들어 아래 두 코드는 같은 의존성을 표현해도 import 안정성은 크게 다르다.

### 케이스 A: 선언 중심 모듈

```python
# settings.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    db_url: str
```

이 파일은 import해도 비교적 안전하다.

### 케이스 B: 실행 중심 모듈

```python
# settings.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    db_url: str


settings = Settings()
engine = create_engine(settings.db_url)
```

이 파일은 import 시점에 환경 변수 검증과 DB 엔진 생성까지 해버린다.

즉 다른 모듈이 단지 타입이나 상수를 참조하려고 import해도, 실제로는 인프라 초기화까지 끌려온다.

이게 커지면 이런 현상이 생긴다.

- import 한 줄이 전체 서비스 bootstrap을 촉발한다
- 테스트가 단위 테스트가 아니라 사실상 통합 테스트가 된다
- 순환 import 위험이 증가한다
- startup 성능 병목이 파일 구조가 아니라 side effect에서 나온다

실무에서 import 문제는 대부분 "Python이 이상해서"가 아니라, **top-level에서 너무 많은 책임을 수행하도록 모듈을 설계했기 때문**이다.

---

## 핵심 개념 1: 모듈, 패키지, namespace package를 구분해야 import 오류를 덜 만든다

먼저 용어부터 정리하자.

### 모듈(module)

대개 `.py` 파일 하나를 말한다.

- `app/settings.py`
- `app/services/user.py`

이 파일이 import되면 하나의 모듈 객체가 된다.

### 패키지(package)

다른 모듈과 하위 패키지를 담는 디렉터리다.

전통적으로는 `__init__.py`가 있는 디렉터리다.

예를 들면:

```text
app/
  __init__.py
  settings.py
  services/
    __init__.py
    user.py
```

여기서 `app`, `app.services`는 패키지다.

### namespace package

PEP 420 이후에는 `__init__.py` 없이도 패키지처럼 동작하는 namespace package가 가능하다.

이건 대형 조직이나 plugin 구조에서 유용할 수 있지만, 실무에서는 조심해야 한다.

장점:

- 여러 배포 단위가 같은 논리 패키지 이름을 공유할 수 있다
- plugin 분리 구조에 유연하다

주의점:

- 경로와 로딩 규칙을 팀이 직관적으로 이해하기 어렵다
- IDE, tooling, packaging 설정에 따라 혼란이 생길 수 있다
- 초보 팀에서는 일반 패키지보다 디버깅 난도가 높다

### 실무 권장 기준

- 일반 서비스/백엔드 앱: **명시적 `__init__.py`가 있는 일반 패키지**를 기본값으로 둔다
- plugin 생태계나 다중 distribution 설계가 명확히 필요한 경우에만 namespace package를 검토한다

많은 `ModuleNotFoundError`는 사실 문법 문제가 아니라, **현재 코드베이스가 패키지인지 아닌지 팀이 일관되게 이해하지 못한 상태**에서 나온다.

---

## 핵심 개념 2: import는 `sys.modules` 확인으로 시작하고, 여기서 많은 현상이 설명된다

Python import 동작을 설명할 때 가장 중요한 객체는 `sys.modules`다.

```python
import sys
print(type(sys.modules))
```

보통 딕셔너리다.

키는 모듈의 절대 이름이고, 값은 이미 로드된 모듈 객체다.

예를 들면:

```python
import math
import sys

print('math' in sys.modules)  # True
print(sys.modules['math'])
```

### `sys.modules`가 중요한 이유

1. 이미 import된 모듈은 재실행하지 않고 재사용한다
2. 순환 import를 막기 위해 **초기화 중인 모듈도 미리 등록**한다
3. 테스트, monkey patch, import hook, reload 모두 이 구조에 영향을 받는다

### 순서를 정확히 이해하자

모듈 `a`를 import한다고 가정하자.

Python은 대략 아래처럼 행동한다.

1. `sys.modules['a']`가 있으면 그걸 반환하려고 한다
2. 없으면 finder/loader를 통해 새 모듈 객체를 만든다
3. **그 새 모듈 객체를 `sys.modules['a']`에 먼저 넣는다**
4. 그다음 `a.py`의 top-level 코드를 실행한다
5. 성공하면 그대로 유지한다
6. 실패하면 보통 import 예외가 올라온다

이 중 3번이 핵심이다.

초기화가 아직 끝나지 않았는데 왜 미리 넣을까?

그래야 A가 B를 import하고, B가 다시 A를 import할 때 무한 재귀 로딩을 피할 수 있기 때문이다.

하지만 이 덕분에 다른 현상도 생긴다.

### partially initialized module

모듈 객체는 존재하지만, 그 안의 이름이 아직 모두 정의되지 않았을 수 있다.

그래서 이런 오류가 나온다.

```text
ImportError: cannot import name 'X' from partially initialized module 'app.foo'
```

이 오류는 "모듈이 아예 없다"가 아니다.

정반대다.

**모듈 객체는 이미 있는데, 당신이 요청한 이름은 아직 초기화되기 전이다**라는 뜻에 가깝다.

이걸 이해하면 순환 import 디버깅이 훨씬 쉬워진다.

---

## 핵심 개념 3: import 파이프라인은 finder, loader, spec으로 구성된다

실무에서 매일 finder/loader를 직접 구현할 일은 거의 없다.

하지만 개념을 알면 import hook, plugin system, zip import, 동적 로딩을 이해하기 쉬워진다.

### 대략적인 파이프라인

- `sys.meta_path`: 어떤 finder들이 import 요청을 처리할지 담고 있음
- finder: 모듈을 어디서 어떻게 찾을지 결정
- module spec: 모듈 이름, loader, origin 등 메타데이터
- loader: 실제 모듈 객체 생성과 코드 실행 담당

표준 라이브러리로는 `importlib`가 이 세계의 공식 API다.

예를 들어 spec을 볼 수 있다.

```python
import importlib.util

spec = importlib.util.find_spec('json')
print(spec)
print(spec.origin)
```

### 왜 이걸 알아야 하나?

아래 문제를 볼 때 도움이 된다.

- plugin을 파일 시스템 스캔이 아니라 entry point로 로딩하고 싶다
- 특정 모듈이 어디서 로드됐는지 추적하고 싶다
- packaging 후 실행 환경에서 잘못된 모듈 shadowing이 있는지 확인하고 싶다
- 테스트 환경에서 import path가 꼬였는지 확인하고 싶다

### 실무적으로 기억할 한 줄

> Python import는 "파일 경로를 바로 여는 것"이 아니라, **이름에서 spec을 찾고 loader로 실행하는 추상화 계층** 위에서 돌아간다.

그래서 `sys.path`와 파일 트리만 보는 식의 디버깅이 종종 불완전하다.

---

## 핵심 개념 4: 순환 import의 본질은 순환 의존 자체보다 "초기화 시점 충돌"이다

순환 import를 설명할 때 흔히 이렇게 말한다.

- A imports B
- B imports A
- 그래서 안 된다

방향은 맞지만 충분히 정확하지는 않다.

실제로는 **어떤 이름을 언제 필요로 하느냐**가 더 중요하다.

### 깨지는 예시

```python
# a.py
from b import make_b

class A:
    pass

instance_a = A()
value = make_b(instance_a)
```

```python
# b.py
from a import instance_a


def make_b(a):
    return {'a': a}
```

이 구조가 깨지는 이유는 `b`가 `a`의 `instance_a`를 import하려는 시점에, `a`가 아직 그 이름을 만들기 전일 수 있기 때문이다.

### 될 수도 있는 예시

```python
# a.py
import b

class A:
    pass
```

```python
# b.py
import a

class B:
    pass
```

이 코드는 상황에 따라 문제 없이 import될 수도 있다.

서로 모듈 객체는 참조하지만, import 시점에 상대 모듈의 아직 미정의된 이름을 즉시 꺼내지 않기 때문이다.

### 실무 해석

순환 import의 핵심 질문은 이것이다.

- 모듈 참조 자체가 필요한가?
- 아니면 특정 이름을 import 시점에 바로 평가해야 하는가?
- 그 이름은 상대 모듈의 top-level 실행이 끝난 뒤에야 생기는가?

즉 순환 import는 그래프 이론 문제이기도 하지만 동시에 **초기화 단계에서의 eager name resolution 문제**다.

---

## 순환 import를 디버깅할 때 가장 먼저 봐야 할 신호들

순환 import가 의심될 때 실무에서 보통 보이는 신호는 아래다.

- `cannot import name ... from partially initialized module ...`
- 리팩터링 후 특정 실행 경로에서만 import 실패
- `__init__.py`에 re-export를 추가한 뒤 갑자기 깨짐
- 타입 힌트 추가만 했는데 runtime import error 발생
- 모델 모듈과 서비스 모듈이 서로 상대 이름을 직접 참조

이때 무작정 함수 내부 import로 숨기기 전에 먼저 아래를 본다.

### 1) 누가 top-level에서 누굴 즉시 참조하는가?

특히 아래 패턴이 많다.

- 모듈 import 직후 싱글톤 생성
- 클래스 정의 직후 다른 모듈 함수 호출
- decorator 인자로 다른 모듈 객체 전달
- registry에 즉시 등록
- base class / mixin / dataclass default factory가 타 모듈 심볼을 직접 요구

### 2) `from x import y`를 너무 많이 쓰고 있는가?

`import x`와 `from x import y`는 초기화 민감도가 다르다.

- `import x`: 모듈 객체 참조
- `from x import y`: 해당 이름이 import 시점에 이미 존재해야 함

순환 구조에서는 대개 `from x import y`가 더 취약하다.

### 3) `__init__.py`가 import 허브 역할을 하고 있는가?

편의 import는 깔끔해 보이지만, 실제로는 패키지 전체의 import fan-in/fan-out을 폭발시킬 수 있다.

예를 들어:

```python
# app/models/__init__.py
from .user import User
from .order import Order
from .payment import Payment
```

겉보기에는 편하다.

하지만 `from app.models import User` 한 줄이 사실상 세 파일 전체의 초기화를 부를 수 있다.

여기에 각 모델이 서로 service, settings, event handler를 다시 import하면 순환 구조가 급격히 생긴다.

---

## 실무 예시 1: FastAPI 앱에서 settings, db, models, routers가 서로 얽히는 전형적인 구조

많은 Python 백엔드가 처음에는 이런 구조로 시작한다.

```text
app/
  main.py
  settings.py
  db.py
  models.py
  routers/
    users.py
  services/
    users.py
```

초기에는 간단하다.

하지만 점점 아래 코드가 붙는다.

- `settings.py`에서 settings 싱글톤 생성
- `db.py`에서 settings import 후 engine 생성
- `models.py`에서 Base import 후 모델 정의
- `routers/users.py`에서 service import
- `services/users.py`에서 models import
- `main.py`에서 routers import
- startup 이벤트에서 db import

이런 식으로 가면 import 그래프가 앱 초기화 그래프와 동일해진다.

### 나쁜 예

```python
# settings.py
settings = Settings()
```

```python
# db.py
from app.settings import settings
engine = create_engine(settings.db_url)
SessionLocal = sessionmaker(bind=engine)
```

```python
# services/users.py
from app.db import SessionLocal
from app.models import User
```

```python
# main.py
from app.routers import users
from app.db import engine
from app.models import Base

Base.metadata.create_all(bind=engine)
```

이 구조는 다음 문제를 동시에 가진다.

- import 시점에 DB 엔진 생성
- import 시점에 ORM 메타데이터 결합
- router import만 해도 인프라 초기화 발생
- 테스트에서 특정 서비스만 import해도 DB 설정이 필요

### 더 나은 기본형

1. `settings.py`는 설정 타입과 팩토리만 둔다
2. `db.py`는 engine 생성 함수를 둔다
3. 앱 부트스트랩은 `main.py` 또는 app factory가 담당한다
4. 모델 모듈은 선언 중심으로 유지한다
5. router는 가능한 한 service interface만 의존한다

예시:

```python
# settings.py
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    db_url: str


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

```python
# db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def create_session_factory(db_url: str):
    engine = create_engine(db_url)
    return sessionmaker(bind=engine)
```

```python
# main.py
from fastapi import FastAPI
from app.settings import get_settings
from app.db import create_session_factory


def create_app() -> FastAPI:
    app = FastAPI()
    settings = get_settings()
    app.state.session_factory = create_session_factory(settings.db_url)
    return app
```

핵심은 import 시점이 아니라 **bootstrap 시점에 인프라를 초기화**하는 것이다.

이 차이가 순환 import, 테스트 용이성, startup 제어 가능성을 한 번에 개선한다.

---

## 핵심 개념 5: `from x import y`와 `import x`는 결합도와 초기화 민감도가 다르다

둘 다 자주 쓰지만, 용도가 다르다.

### `from x import y`

장점:

- 호출 시 접두어가 짧다
- 필요한 심볼이 명확하다
- type checker와 IDE가 읽기 쉬울 때가 많다

주의점:

- import 시점에 해당 이름이 즉시 준비되어 있어야 한다
- 순환 import에서 더 쉽게 깨진다
- 이름 shadowing과 re-export 구조에서 실제 출처를 놓치기 쉽다

### `import x`

장점:

- 모듈 경계를 코드에 그대로 드러낸다
- 순환 import에서 상대적으로 안전한 경우가 있다
- 심볼 출처 추적이 쉽다

주의점:

- 접두어가 길어진다
- 모듈 내부 API 변경 시 호출부가 길게 바뀔 수 있다

### 실무 추천 기준

- 모듈 경계가 중요하고, 순환 위험이 있는 도메인 계층: `import x` 선호
- 비교적 leaf module이거나 util 성격이 강한 심볼: `from x import y` 사용 가능
- 패키지 루트 re-export를 통한 광범위한 `from app import X` 남발은 주의

중요한 건 일관된 절대 규칙이 아니라, **초기화 민감한 계층에서는 모듈 참조를 더 명시적으로 유지하는 것**이다.

---

## 핵심 개념 6: `__init__.py`는 편의 파일이 아니라 패키지 초기화 지점이다

많은 팀이 `__init__.py`를 단순한 빈 파일 또는 편의 export 모음 정도로 생각한다.

하지만 이 파일도 import 시 실행된다.

즉 `import app.services`를 하면 `app/services/__init__.py`가 먼저 실행될 수 있다.

### `__init__.py`에 넣기 좋은 것

- 최소한의 패키지 메타데이터
- 매우 얕은 re-export
- side effect 없는 상수 수준 선언

### `__init__.py`에 넣기 나쁜 것

- DB 연결 생성
- 환경 변수 검증
- 대규모 하위 모듈 일괄 import
- registry 자동 스캔
- 파일 시스템 접근
- 로깅 설정

### 안티패턴

```python
# app/services/__init__.py
from .users import UserService
from .orders import OrderService
from .payments import PaymentService
from .notifications import NotificationService
```

이 패턴은 package import 하나로 서비스 전체를 초기화할 수 있다.

처음에는 편하다.

하지만 시간이 갈수록 아래 비용이 생긴다.

- 필요 없는 의존성까지 eager import
- startup 비용 증가
- 순환 import 표면적 확대
- 특정 서브모듈만 테스트하기 어려움

### 더 나은 기준

패키지 루트에서 re-export를 하더라도 아래 중 하나를 만족할 때만 하자.

- 아주 안정적인 핵심 API 표면을 만들고 싶다
- import 비용이 매우 작다
- 하위 모듈 간 결합이 약하다
- 팀이 패키지 public API와 internal API를 명확히 관리한다

그렇지 않으면 호출부가 조금 길어지는 대신, `from app.services.users import UserService`처럼 **출처를 명확히 적는 것이 장기적으로 더 싸다**.

---

## 핵심 개념 7: startup 성능 문제는 import 개수보다 top-level side effect가 더 큰 원인인 경우가 많다

"Python startup이 느리다"는 말은 종종 너무 뭉뚱그려져 있다.

실제로는 아래 원인이 섞여 있다.

- import 대상 수가 많다
- import graph가 깊다
- heavy dependency가 많다
- top-level에서 무거운 초기화가 실행된다
- 한 번만 필요할 라이브러리를 모든 실행 경로에서 eager import한다
- CLI subcommand마다 전체 앱을 import한다

### 먼저 분리해야 할 질문

#### 1) 모듈 찾기 자체가 느린가?

보통 이 경우는 상대적으로 드물다.

#### 2) C extension이나 큰 라이브러리 import가 느린가?

예:

- pandas
- numpy
- torch
- sqlalchemy + dialect 초기화
- cloud SDK

#### 3) 우리 코드의 top-level side effect가 느린가?

예:

- 설정 파일 파싱
- schema 로딩
- plugin 스캔
- network I/O
- 인증 클라이언트 생성

실무에서는 3번이 생각보다 자주 진짜 원인이다.

### 측정부터 하자

Python은 `-X importtime` 옵션을 제공한다.

```bash
python -X importtime -c "import app.main"
```

이걸 쓰면 import 트리별 시간을 볼 수 있다.

또는:

```bash
python -X importtime -m your_cli_command 2> import.log
```

이 로그를 보면 아래를 파악할 수 있다.

- 어떤 모듈이 직접 오래 걸리는가
- 어떤 상위 import가 큰 서브트리를 끌고 오는가
- CLI 경로에 불필요한 서버 의존성이 붙어 있는가

### 해석할 때 주의할 점

어떤 모듈이 느리다고 해서 그 파일 내용만 문제인 건 아니다.

그 모듈이 import하는 하위 트리 전체가 합산된 결과일 수 있다.

그래서 실전 질문은 이렇게 바뀐다.

- 이 실행 경로에서 정말 이 dependency tree가 필요했는가?
- heavy import를 bootstrap 이후로 미룰 수 있는가?
- top-level 부작용을 팩토리 함수로 내릴 수 있는가?

---

## 실무 예시 2: CLI 도구가 느린 이유는 명령이 아니라 앱 전체를 import하기 때문인 경우

많은 프로젝트에서 CLI가 이렇게 생긴다.

```python
# cli.py
from app.main import create_app
from app.jobs.backfill import run_backfill
from app.jobs.cleanup import run_cleanup
```

그리고 `python -m app.cli cleanup` 같은 명령을 실행한다.

문제는 cleanup 작업이 단순히 파일 정리 정도만 해도, `app.main` import가 web app 전체 초기화를 끌고 올 수 있다는 점이다.

이 경우 나타나는 현상은 아래와 같다.

- `--help`가 느리다
- 단순한 관리 명령도 env 검증, tracing 설정, DB 드라이버 import를 다 수행한다
- 실패 지점이 실제 명령 로직이 아니라 startup import에서 난다

### 더 나은 구조

CLI entrypoint는 하위 명령별로 필요한 의존성을 지연 로딩하거나, 최소 bootstrap만 가져와야 한다.

예를 들어:

```python
# cli.py
import argparse


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['cleanup', 'backfill'])
    args = parser.parse_args()

    if args.command == 'cleanup':
        from app.jobs.cleanup import run_cleanup
        run_cleanup()
    elif args.command == 'backfill':
        from app.jobs.backfill import run_backfill
        run_backfill()
```

이 패턴은 무조건 좋은 건 아니지만, **서브커맨드별 의존성이 크게 다른 CLI**에서는 매우 실용적이다.

단, 이걸 남용해 모든 import를 함수 안으로 숨기면 구조가 흐려질 수 있다.

그래서 기준이 중요하다.

- 실행 경로별 의존성이 크게 다르다
- startup latency가 중요한 CLI다
- heavy dependency가 일부 명령에만 필요하다

이럴 때 lazy import가 구조적 최적화가 될 수 있다.

반대로 그냥 순환 import를 감추기 위해 여기저기 함수 내부 import를 흩뿌리는 건 냄새일 가능성이 높다.

---

## 핵심 개념 8: lazy import는 성능 최적화이기도 하지만, 종종 아키텍처 경고 신호이기도 하다

lazy import는 여러 방식으로 구현할 수 있다.

- 함수 내부에서 import
- optional dependency가 필요할 때만 `importlib.import_module()` 사용
- 타입 체크 시에만 import (`TYPE_CHECKING`)
- plugin 이름 문자열을 나중에 해석

### lazy import가 잘 맞는 경우

#### 1) 선택적 기능

예:

- CSV export 시에만 pandas 필요
- 이미지 OCR 시에만 pillow / torch 필요
- admin command에서만 boto3 필요

#### 2) startup 최적화가 중요한 CLI / serverless / short-lived worker

예:

- Lambda handler
- ephemeral batch container
- 많은 subprocess를 빠르게 띄워야 하는 도구

#### 3) 타입 참조는 필요하지만 runtime import는 불필요한 경우

`TYPE_CHECKING`이 대표적이다.

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.user import UserService
```

#### 4) plugin 이름만 저장하고 실제 구현체는 실행 시점에 로딩하는 구조

이건 확장성 설계와 잘 맞는다.

### lazy import가 냄새인 경우

#### 1) 순환 import를 근본 해결 없이 숨길 때

```python
def do_work():
    from app.services.user import UserService
```

이게 한두 군데면 괜찮을 수 있다.

하지만 곳곳에 늘어나면, 구조적 문제를 런타임 지연으로 덮고 있는 것일 수 있다.

#### 2) 모듈 경계가 불분명한데 임시로 에러만 없앨 때

이 경우 나중에 테스트, type checking, code navigation, refactoring이 더 어려워진다.

#### 3) import 위치가 실행 경로마다 달라져 예측 가능성이 떨어질 때

운영 장애는 startup에서 한 번 터지는 것보다, 특정 요청 경로에서만 늦게 터지는 쪽이 더 디버깅하기 어렵다.

### 실무 판단 기준

lazy import의 질문은 "가능한가"가 아니라 이거다.

- 이 의존성은 정말 선택적인가?
- startup budget을 줄이기 위한 명확한 이유가 있는가?
- 아니면 계층 의존성 설계를 바로잡아야 하는가?

---

## 핵심 개념 9: 타입 힌트가 import 문제를 만들 수 있고, `TYPE_CHECKING`과 annotation 전략이 중요하다

중급 이상 코드베이스에서 순환 import가 갑자기 늘어나는 대표 계기 중 하나가 타입 힌트 도입이다.

예를 들어:

```python
from app.models.user import User


def send_welcome_email(user: User) -> None:
    ...
```

이 코드는 타입 힌트 목적일 뿐인데도 runtime import를 발생시킨다.

특히 서비스 계층과 모델 계층이 서로 타입을 참조하면 순환 구조가 생기기 쉽다.

### 대응 전략 1: `from __future__ import annotations`

현대 Python에서는 annotation을 지연 평가 문자열처럼 다루도록 돕는 방식이 유용하다.

```python
from __future__ import annotations
```

이걸 쓰면 많은 경우 타입 이름이 즉시 평가되지 않아 import 압력이 줄어든다.

### 대응 전략 2: `TYPE_CHECKING`

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.user import User


def send_welcome_email(user: 'User') -> None:
    ...
```

이 패턴은 런타임 import를 막으면서 정적 분석기에는 정보를 준다.

### 대응 전략 3: protocol / interface로 의존성 역전

구현체가 아니라 프로토콜이나 더 얕은 계약을 참조하면 import 결합도가 줄어든다.

```python
from typing import Protocol


class UserLike(Protocol):
    email: str
    id: int
```

서비스가 실제 ORM model 전체를 알 필요가 없다면 이런 접근이 더 좋다.

### 실무 포인트

타입 힌트 때문에 import가 꼬인다면, 문제는 타입 힌트 자체가 아니라 대개 아래 둘 중 하나다.

- 런타임에 필요 없는 타입을 runtime import하고 있다
- 계층 경계가 너무 구체 구현에 묶여 있다

즉 타입 힌트 이슈는 종종 import 문제를 드러내는 **좋은 경보 장치**이기도 하다.

---

## 핵심 개념 10: 상대 import와 실행 방식(`python file.py` vs `python -m package.module`)은 배포 안정성과 직결된다

Python에서 경로 문제는 생각보다 자주 사람을 지치게 만든다.

특히 아래 두 실행 방식은 다르게 동작한다.

```bash
python path/to/module.py
```

```bash
python -m package.module
```

### 왜 다를까?

Python은 실행 진입 방식에 따라 `__name__`, `__package__`, import base path 해석이 달라질 수 있다.

패키지 내부 모듈을 파일 직접 실행하면 상대 import가 깨질 수 있다.

예를 들어 패키지 안에서:

```python
from .utils import parse
```

이 코드는 패키지 컨텍스트에서는 안전하지만, 파일을 직접 실행하면 실패할 수 있다.

### 실무 기본 규칙

- 패키지 내부 실행 파일은 가능하면 `python -m package.module` 형태로 실행한다
- 배포 코드에서 `sys.path.append(...)`로 땜질하지 않는다
- 애플리케이션은 설치 가능한 패키지 구조를 기본값으로 둔다

### editable install이 중요한 이유

개발 환경에서 다음처럼 설치하면:

```bash
pip install -e .
```

프로젝트가 import 가능한 패키지로 동작하므로, 로컬 실행과 배포 실행 간 차이를 줄이기 쉽다.

반대로 작업 디렉터리 운에 기대어 돌아가는 코드는 CI, Docker, cron, worker 환경에서 자주 깨진다.

### 흔한 안티패턴

```python
import os
import sys
sys.path.append(os.path.dirname(__file__))
```

이건 당장 급한 불을 끌 수는 있다.

하지만 다음 비용을 만든다.

- 실행 환경마다 import 규칙이 달라짐
- shadowing 문제 추적이 어려움
- packaging으로 가는 길을 막음

실무에서는 import 경로를 런타임에서 조작하기보다, **패키지 구조와 실행 방식을 정상화하는 것**이 맞다.

---

## 실무 예시 3: plugin discovery를 파일 스캔에 의존하지 않고 import 친화적으로 설계하기

확장 가능한 시스템을 만들다 보면 plugin 구조가 필요하다.

예를 들어:

- exporter plugin
- payment provider plugin
- ingestion connector plugin
- CLI command plugin

이때 초기에 흔히 하는 방식은 디렉터리를 스캔해서 `.py` 파일을 import하는 것이다.

### 단순하지만 취약한 방식

- 파일 시스템에 plugin 폴더를 둔다
- 모든 파일을 순회한다
- 모듈 이름을 문자열로 만들어 import한다
- import side effect로 registry에 등록되게 한다

이 방식의 문제는 아래다.

- import 순서가 구조적으로 드러나지 않는다
- 테스트에서 plugin 로딩 범위를 제어하기 어렵다
- 배포 단위가 늘어나면 path 관리가 복잡해진다
- import side effect에 강하게 의존한다

### 더 나은 방식: entry point 기반 discovery

현대 Python packaging에서는 distribution metadata를 통해 plugin entry point를 선언할 수 있다.

예시 개념:

```toml
[project.entry-points."myapp.exporters"]
json = "myapp_json_exporter:JsonExporter"
parquet = "myapp_parquet_exporter:ParquetExporter"
```

런타임에서는:

```python
from importlib.metadata import entry_points


def load_exporters():
    exporters = {}
    for ep in entry_points(group='myapp.exporters'):
        exporters[ep.name] = ep.load()
    return exporters
```

### 이 패턴의 장점

- plugin 탐색 규칙이 packaging metadata에 명시된다
- 실제 구현체는 필요 시점에 로드할 수 있다
- distribution이 분리돼도 확장성이 좋다
- 테스트에서 어떤 plugin 그룹을 로드할지 제어하기 쉽다

### 중요한 설계 포인트

plugin 시스템은 종종 import 문제를 구조적으로 확대한다.

그래서 아래 원칙이 중요하다.

- core contract는 얕고 안정적으로 유지한다
- plugin 구현이 core 내부 모듈을 과도하게 import하지 않게 한다
- registration을 import side effect보다 **명시적 load 단계**로 이동시킨다
- optional dependency는 plugin 경계 밖으로 새지 않게 한다

즉 좋은 plugin 구조는 "아무 파일이나 자동 import"가 아니라, **명시적 계약과 지연 로딩** 위에서 돌아간다.

---

## 핵심 개념 11: import side effect를 줄이려면 app factory, dependency injection, 명시적 bootstrap이 중요하다

import 문제를 가장 많이 줄이는 패턴 중 하나가 app factory다.

예를 들면 FastAPI, Flask, CLI, worker 모두 아래 원칙이 좋다.

- import 시점에는 선언 위주
- 실행 시점에 명시적으로 조립
- 외부 리소스는 bootstrap 함수에서 초기화

### 왜 app factory가 import에 도움이 될까?

1. 모듈 import와 인프라 초기화를 분리한다
2. 테스트에서 부분 초기화만 할 수 있다
3. startup 순서를 제어할 수 있다
4. 순환 import가 app 전역 singleton에서 생기는 것을 줄인다

### 예시

```python
# app/factory.py
from fastapi import FastAPI
from app.api import register_routes
from app.settings import get_settings
from app.db import create_session_factory


def create_app() -> FastAPI:
    app = FastAPI()
    settings = get_settings()
    app.state.settings = settings
    app.state.session_factory = create_session_factory(settings.db_url)
    register_routes(app)
    return app
```

이 구조는 import 시점에 거의 아무 side effect도 일으키지 않는다.

실제 초기화는 `create_app()` 호출 시점에만 일어난다.

### worker / batch에서도 같은 원칙

```python
# jobs/backfill.py
from app.settings import get_settings
from app.db import create_session_factory


def run() -> None:
    settings = get_settings()
    session_factory = create_session_factory(settings.db_url)
    ...
```

여기서 중요한 건 공통 모듈이 인프라 singleton을 import 시점에 바로 만들지 않는다는 점이다.

---

## 핵심 개념 12: reload, test isolation, monkey patch도 import 생명주기의 영향을 받는다

테스트가 이상하게 흔들릴 때, 원인이 로직이 아니라 import 캐시에 있는 경우가 꽤 많다.

### 왜 그럴까?

같은 인터프리터 프로세스 안에서는 모듈이 `sys.modules`에 남는다.

그래서 다음이 생긴다.

- 한 테스트에서 변경한 전역 상태가 다른 테스트에 남음
- 환경 변수 기반 설정이 첫 import 시점 값으로 굳음
- monkey patch 타이밍이 늦으면 이미 import된 심볼에는 영향이 없음
- reload 없이 코드 수정 효과를 기대하면 어긋남

### 흔한 함정 1: settings singleton

```python
settings = Settings()
```

이게 import 시점에 만들어지면, 테스트에서 `os.environ`을 바꿔도 이미 생성된 settings에는 반영되지 않는다.

그래서 `lru_cache` 기반 팩토리와 cache clear가 더 실용적일 수 있다.

```python
@lru_cache
def get_settings() -> Settings:
    return Settings()
```

테스트에서는:

```python
get_settings.cache_clear()
```

### 흔한 함정 2: monkey patch 위치

```python
from app.service import do_work
```

이렇게 심볼을 직접 import한 뒤에는, 원 모듈을 monkey patch해도 이미 바인딩된 이름은 바뀌지 않을 수 있다.

테스트 안정성을 높이려면 아래가 유리할 때가 많다.

- 모듈 자체를 import하고 속성을 패치한다
- import 시점이 아니라 함수 호출 경계에서 의존성을 주입한다

### 흔한 함정 3: `importlib.reload()` 과신

reload는 일부 상황에서 유용하지만 만능이 아니다.

- 다른 모듈이 이미 참조한 객체는 그대로일 수 있다
- 전역 side effect는 다시 실행될 수 있다
- 하위 의존성까지 일관되게 reset되지는 않는다

대부분의 서비스 테스트에서 reload보다 나은 해법은 **초기화 시점을 명시적으로 통제하는 구조**다.

---

## 실무 예시 4: SQLAlchemy 모델과 서비스 레이어가 서로 직접 참조해서 순환 구조가 생기는 경우

Python 백엔드에서 정말 흔한 장면이다.

### 나쁜 구조

```python
# models/user.py
from app.services.passwords import hash_password

class User(Base):
    ...

    def set_password(self, raw: str) -> None:
        self.password_hash = hash_password(raw)
```

```python
# services/passwords.py
from app.models.user import User


def hash_password(raw: str) -> str:
    ...


def upgrade_hash_if_needed(user: User) -> None:
    ...
```

처음에는 자연스러워 보인다.

하지만 모델이 서비스에 의존하고, 서비스가 다시 모델에 의존하면서 결합이 순환된다.

### 더 나은 방향

#### 1) 도메인 순수 함수와 모델 동작을 분리

```python
# domain/passwords.py

def hash_password(raw: str) -> str:
    ...
```

```python
# models/user.py
from app.domain.passwords import hash_password
```

```python
# services/passwords.py
from app.domain.passwords import hash_password
```

둘 다 더 얕은 레이어를 의존하게 만들면 순환이 사라진다.

#### 2) 타입 참조는 protocol 또는 `TYPE_CHECKING`으로 약화

서비스가 꼭 ORM 모델 구체형을 알 필요가 없다면 더 좋다.

```python
from typing import Protocol


class PasswordUpgradable(Protocol):
    password_hash: str
```

이렇게 하면 모델 import 압력을 줄일 수 있다.

### 핵심 교훈

순환 import는 종종 import 문을 바꾸면 없어지는 것처럼 보이지만, 실제로는 **계층 책임이 서로 섞여 있다는 구조 신호**다.

---

## 핵심 개념 13: settings 모듈은 import 문제의 진원지가 되기 쉽다

많은 코드베이스에서 `settings.py`는 가장 먼저 import된다.

그리고 가장 많은 모듈이 다시 그걸 import한다.

즉 settings는 구조적으로 fan-out이 큰 허브다.

그런데 여기에 아래가 붙기 쉽다.

- 환경 변수 읽기
- `.env` 파일 로딩
- 파생 설정 계산
- 로거 레벨 결정
- DB URL 생성
- secret manager 호출

이 모든 것을 import 시점에 수행하면, settings는 단순 구성 데이터가 아니라 **전체 앱 bootstrap trigger**가 된다.

### 추천 패턴

#### 1) 선언과 인스턴스 생성을 분리

```python
class Settings(BaseSettings):
    ...
```

```python
@lru_cache
def get_settings() -> Settings:
    return Settings()
```

#### 2) 설정 파생 로직도 가능하면 property / 함수로 지연 평가

```python
class Settings(BaseSettings):
    db_host: str
    db_port: int

    @property
    def db_dsn(self) -> str:
        return f'postgresql://{self.db_host}:{self.db_port}/app'
```

#### 3) 비싼 외부 조회는 settings import에서 하지 않는다

예:

- secret manager fetch
- cloud metadata fetch
- certificate download

이건 bootstrap 또는 runtime initialization 계층으로 내려야 한다.

### 왜 중요한가?

settings 허브를 가볍게 유지하면:

- import graph 전반이 안정된다
- 테스트 격리가 쉬워진다
- CLI와 web app이 같은 설정 타입을 공유하되 초기화 시점은 분리할 수 있다

---

## 핵심 개념 14: import 최적화에서 "무조건 늦게"보다 "정말 필요한 경계에서만"이 중요하다

성능 최적화를 하다 보면 모든 걸 lazy하게 만들고 싶어진다.

하지만 그건 장기적으로 좋지 않다.

지나친 lazy import는 아래 비용을 만든다.

- 코드 가독성 저하
- 런타임 특정 경로에서만 ImportError 발생
- static analysis와 code navigation 품질 저하
- 실제 아키텍처 문제 은폐

그래서 균형이 필요하다.

### eager import가 좋은 경우

- 거의 모든 실행 경로에서 항상 필요하다
- import 비용이 작다
- 실패를 startup에서 빨리 드러내는 편이 낫다
- core domain dependency다

예:

- 표준 라이브러리
- 얕은 domain module
- 공통 type / error 정의

### lazy import가 좋은 경우

- optional 기능이다
- heavy dependency다
- 실패를 사용 시점에 국소화해도 괜찮다
- startup budget이 민감하다

예:

- pandas 기반 export
- cloud SDK 특정 커맨드
- admin plugin

### 판단 프레임

질문은 단순하다.

- 이 dependency는 **항상 필요**한가?
- 아니면 **경로 조건부**인가?
- import 실패를 **startup에서 즉시** 알리는 게 좋은가, **기능 진입 시점에 국소화**하는 게 좋은가?

이 질문 없이 무조건 eager 또는 lazy를 택하면 둘 다 문제를 만든다.

---

## 실무 예시 5: `TYPE_CHECKING`과 local import를 함께 써서 runtime 결합도를 낮추는 패턴

아래는 서비스 레이어에서 자주 쓸 수 있는 실용적 패턴이다.

```python
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.repositories.user import UserRepository


class UserService:
    def __init__(self, repo: 'UserRepository') -> None:
        self.repo = repo
```

이 구조의 장점은 아래다.

- 타입 정보는 유지된다
- runtime import는 줄어든다
- 생성자 주입으로 의존성 방향이 명확해진다
- 서비스와 저장소의 모듈 import 타이밍이 느슨해진다

여기에 필요할 때만 실제 구현체를 조립하는 bootstrap 계층을 더하면, import 안전성이 크게 좋아진다.

### 주의할 점

이 패턴은 타입 힌트 결합을 줄이는 데 좋지만, 근본 의존성 방향이 잘못되었으면 그것까지 자동으로 고쳐주진 않는다.

예를 들어 서비스가 저장소 구현의 내부 세부사항에 강하게 의존한다면, 문자열 annotation으로 import를 늦춰도 구조 자체는 여전히 취약하다.

---

## 핵심 개념 15: package public API를 만들 때 re-export는 선택적으로만 써야 한다

큰 패키지에서는 아래처럼 쓰고 싶어진다.

```python
from app.sdk import Client, Request, Response, Error
```

사용성 면에서는 좋다.

하지만 public API를 만들기 위해 루트 패키지에서 너무 많은 걸 re-export하면 내부 구조와 import 비용이 꼬일 수 있다.

### re-export가 유용한 경우

- 라이브러리처럼 외부 사용자-facing API가 중요하다
- 내부 구현을 바꿔도 바깥 API 표면은 안정적으로 유지하고 싶다
- 엄격하게 관리되는 소수의 핵심 심볼만 노출한다

### re-export가 위험한 경우

- 앱 코드베이스 전체에서 편의상 마구 쓴다
- 내부 모듈 간에도 루트 패키지 re-export를 경유한다
- 루트 패키지가 사실상 전체 시스템을 import하는 허브가 된다

### 실무 원칙

- 라이브러리 boundary에서는 public API를 의식적으로 설계한다
- 애플리케이션 내부에서는 출처가 드러나는 명시적 import를 선호한다
- 루트 re-export를 추가할 때는 **startup 비용과 순환 가능성**도 같이 본다

---

## 실무 예시 6: worker 프로세스가 많을수록 import 비용과 메모리 footprint가 운영 이슈가 되는 경우

백엔드 개발자는 종종 API 서버 한 프로세스만 생각한다.

하지만 실제 운영에서는 아래처럼 프로세스 수가 많다.

- gunicorn worker 여러 개
- celery worker 여러 개
- batch subprocess 여러 개
- ProcessPoolExecutor child 여러 개

이때 heavy import는 worker 수만큼 반복된다.

특히 아래 상황에서 아프다.

- startup이 느려 rolling deploy 시간이 길어짐
- autoscaling 시 cold start latency가 커짐
- 짧은 배치 프로세스가 import 시간에 대부분을 씀
- 각 프로세스가 무거운 dependency를 들고 있어 RSS가 커짐

### 대응 전략

#### 1) 진짜 필요한 worker만 heavy dependency import

예:

- CPU image job worker만 pillow/torch import
- 일반 API worker는 그걸 몰라도 되게 분리

#### 2) command/role 별 entrypoint 분리

하나의 범용 프로세스가 모든 기능 의존성을 다 들고 시작하지 않게 한다.

#### 3) top-level에서 model weights, schema, dictionary preload 금지

필요한 시점 또는 별도 warm-up 단계로 이동한다.

#### 4) `-X importtime`과 프로세스 시작 시간 메트릭을 같이 본다

단순 코드 리뷰로는 체감이 잘 안 오는 경우가 많다.

### 핵심 관점

import 비용은 1회 비용처럼 보이지만, **프로세스 수와 재기동 빈도를 곱하면 운영 비용**이 된다.

---

## 트레이드오프 1: 선언 시점 단순성 vs bootstrap 시점 제어 가능성

top-level에서 바로 객체를 만들어두면 쓰기는 편하다.

```python
engine = create_engine(...)
client = S3Client(...)
settings = Settings()
```

장점:

- 호출부가 단순하다
- 전역 접근이 쉽다
- 샘플 코드가 짧다

단점:

- import가 곧 초기화가 된다
- 테스트 격리가 어려워진다
- startup 비용이 숨는다
- 순환 import 표면이 커진다

반대로 팩토리/DI/명시적 bootstrap은 조금 더 장황하다.

장점:

- 초기화 시점을 통제할 수 있다
- 테스트 가능성이 좋아진다
- import 그래프와 런타임 그래프를 분리할 수 있다

단점:

- 조립 코드가 필요하다
- 초반 개발 속도가 약간 느려 보일 수 있다

실무적으로는 서비스가 커질수록 후자가 훨씬 싸다.

---

## 트레이드오프 2: eager import의 조기 실패 장점 vs lazy import의 startup 최적화 장점

### eager import의 좋은 점

- missing dependency를 startup에서 빨리 발견한다
- 장애가 요청 중간이 아니라 부팅 단계에서 드러난다
- 코드 흐름이 읽기 쉽다

### eager import의 아쉬운 점

- 모든 경로에서 startup 비용을 낸다
- optional feature도 강제 dependency가 된다
- CLI/worker/serverless cold start가 느려진다

### lazy import의 좋은 점

- startup 비용을 줄일 수 있다
- optional dependency를 국소화할 수 있다
- 기능별 entrypoint 최적화가 쉽다

### lazy import의 아쉬운 점

- 오류가 늦게 드러난다
- 코드 탐색성이 나빠질 수 있다
- 남용하면 구조 문제가 가려진다

### 추천 기준

- core dependency: eager
- optional / heavy / rare path dependency: lazy
- 순환 import 우회용 lazy import: 임시 조치로만 사용, 장기적으로는 구조 수정

---

## 트레이드오프 3: 편의 re-export vs 명시적 import 경계

### 편의 re-export

좋은 점:

- 사용 경험이 단순하다
- public API를 만들기 좋다

아쉬운 점:

- import fan-out이 커진다
- 실제 출처 추적이 흐려진다
- 루트 패키지가 비대해진다

### 명시적 import

좋은 점:

- 출처가 선명하다
- 디버깅이 쉽다
- 순환 구조를 눈으로 보기 좋다

아쉬운 점:

- 호출부가 길어진다
- 외부 사용성이 약간 떨어질 수 있다

애플리케이션 내부에서는 명시적 import가 대체로 이긴다.

라이브러리 public API에서는 선택적 re-export가 가치가 있다.

---

## 트레이드오프 4: plugin auto-discovery 편의성 vs 명시적 registration 안정성

### import side effect 기반 auto-registration

좋은 점:

- 구현이 간단하다
- 새 파일만 추가하면 자동 동작하기 쉽다

아쉬운 점:

- import 순서에 민감하다
- 테스트 제어가 어렵다
- startup 비용이 숨는다

### 명시적 registration / entry point 기반 로딩

좋은 점:

- 로딩 시점과 범위가 명확하다
- optional dependency 관리가 쉽다
- 배포 단위 분리가 좋다

아쉬운 점:

- 초기 설계가 조금 더 필요하다
- metadata 관리가 필요하다

확장 가능한 시스템일수록 후자가 장기적으로 안전하다.

---

## 흔한 실수 1: settings, db, logger, client를 import 시점에 다 만들어버린다

이건 정말 흔하다.

```python
settings = Settings()
engine = create_engine(settings.db_url)
redis = Redis(...)
logger = build_logger(settings.log_level)
```

당장은 편하지만, 아래 문제가 한 번에 생긴다.

- import 비용 증가
- 테스트 환경 제어 어려움
- 순환 import 위험 증가
- side effect가 숨어 코드 리뷰에서 놓치기 쉬움

해결은 보통 단순하다.

- 팩토리 함수로 내린다
- app bootstrap에서 조립한다
- cache가 필요하면 `lru_cache`로 제어한다

---

## 흔한 실수 2: 순환 import를 전부 함수 내부 import로만 덮는다

함수 내부 import는 도구다.

하지만 구조 수정 없이 만능 치료제처럼 쓰면 나중에 더 큰 빚이 된다.

신호는 이렇다.

- 같은 코드베이스에 local import가 과도하게 많다
- 호출 경로마다 import 위치가 다르다
- 코드 탐색이 어렵다
- 특정 요청에서만 늦게 ImportError가 난다

이 경우 먼저 물어야 한다.

- 왜 두 모듈이 서로를 알아야 하는가?
- 더 얕은 공통 모듈로 내릴 수 없는가?
- interface / protocol / DTO로 분리할 수 없는가?

local import는 **선택적 의존성**이나 **명확한 startup 최적화**에 쓰는 게 더 건강하다.

---

## 흔한 실수 3: `__init__.py`를 편의성 때문에 과도한 집결지로 만든다

이건 팀이 커질수록 자주 생긴다.

- 사용자는 짧은 import를 원한다
- 그래서 루트 패키지에서 모든 걸 재노출한다
- 시간이 지나면 루트 패키지가 사실상 전체 시스템을 import한다

결과:

- startup 느려짐
- 순환 import 증가
- 일부 파일만 import하기 어려워짐

`__init__.py`는 작고 얕게 유지하는 편이 낫다.

---

## 흔한 실수 4: 패키지 구조 대신 `sys.path` 조작으로 경로 문제를 해결한다

당장 편하지만 장기적으로 거의 항상 손해다.

- 로컬만 되는 코드가 된다
- CI, Docker, cron, worker에서 깨질 수 있다
- shadowing과 path precedence 버그가 생긴다

경로 문제는 packaging과 실행 방식을 바로잡아야 한다.

- 설치 가능한 패키지 구조
- `python -m`
- editable install
- 명시적 entrypoint

이 조합이 정석이다.

---

## 흔한 실수 5: 타입 힌트는 런타임 비용이 없다고 생각한다

많은 경우 아니다.

특히 runtime에서 annotation을 평가하거나, 타입을 위해 실제 모듈을 import하면 결합과 비용이 생긴다.

그래서 아래를 익숙하게 써야 한다.

- `from __future__ import annotations`
- `TYPE_CHECKING`
- protocol
- 타입 전용 모듈 분리

정적 타입 시스템을 쓰는 팀일수록 import 설계가 더 중요해진다.

---

## 흔한 실수 6: 테스트가 import 생명주기를 고려하지 않는다

테스트가 단순 함수 호출만 검증하면, import 초기화 이슈를 놓치기 쉽다.

특히 아래는 별도 체크가 필요하다.

- env 바꾼 뒤 settings cache clear가 필요한가
- monkey patch가 import 이전에 이뤄지는가
- 전역 registry가 테스트 간 누적되는가
- 모듈 import 순서가 바뀌어도 안정적인가

import 문제는 로직 버그가 아니라서, 기능 테스트만으로 잘 안 잡힌다.

---

## 흔한 실수 7: plugin 시스템을 "일단 폴더 스캔"으로 시작하고 그대로 굳힌다

초기에는 빨라 보이지만 아래 비용이 커진다.

- 배포 단위 분리 어려움
- import side effect 과다
- 어떤 plugin이 언제 로딩되는지 추적 어려움
- optional dependency 실패가 startup 전체를 깨뜨림

확장 가능성이 있다면 초기에 조금 더 투자해서 entry point 또는 명시적 등록 구조를 만드는 편이 낫다.

---

## 흔한 실수 8: import 에러를 "Python path 이상"으로만 단정한다

실제로는 path 이슈보다 아래가 더 자주 원인이다.

- partially initialized module
- re-export로 인한 간접 순환
- 파일 이름 shadowing (`json.py`, `typing.py`, `email.py` 같은)
- 작업 디렉터리 차이
- 패키지 컨텍스트가 없는 파일 직접 실행

`ModuleNotFoundError`만 보지 말고, **실행 방식, 모듈 이름, 현재 디렉터리, same-name shadowing**까지 같이 봐야 한다.

---

## 흔한 실수 9: 파일 이름으로 표준 라이브러리/서드파티를 shadowing 한다

예:

- `typing.py`
- `json.py`
- `asyncio.py`
- `sqlalchemy.py`

이건 보기보다 자주 발생한다.

Python은 import 이름을 따라 해석하므로, 로컬 파일이 표준 라이브러리나 설치 패키지를 가릴 수 있다.

이 문제는 처음엔 일부 환경에서만 발생해 더 짜증 난다.

실무 규칙으로 아래를 두는 편이 좋다.

- 표준 라이브러리/핵심 패키지 이름과 같은 파일명 금지
- 리뷰에서 파일명 자체도 본다
- import weirdness가 있으면 shadowing부터 의심한다

---

## 흔한 실수 10: startup 성능을 재기동 빈도와 함께 보지 않는다

"어차피 import는 한 번이잖아"라는 말은 일부만 맞다.

운영에서는 다음이 존재한다.

- autoscaling
- rolling restart
- short-lived jobs
- worker recycle
- serverless cold start

즉 startup 1초 차이는 실제로는 반복 비용일 수 있다.

특히 프로세스가 많이 뜨는 구조에서는 import 비용이 SLO와 배포 시간에 직접 영향을 준다.

---

## import 문제를 구조적으로 푸는 설계 원칙

이제 실전 원칙을 정리해보자.

### 원칙 1: 모듈은 선언 중심, bootstrap은 실행 중심으로 분리한다

- 모듈 top-level에서는 타입, 함수, 클래스 선언 위주
- 외부 리소스 연결과 인스턴스 생성은 bootstrap 함수로 이동

### 원칙 2: dependency direction을 얕게 유지한다

- 상위 레이어가 하위 레이어를 의존
- 하위 레이어가 다시 상위를 import하지 않기
- 공통 계약은 더 얕은 모듈로 추출

### 원칙 3: 타입 힌트 때문에 runtime import가 늘지 않게 한다

- `__future__.annotations`
- `TYPE_CHECKING`
- protocol
- DTO/contract 모듈 분리

### 원칙 4: 패키지 public API와 internal API를 구분한다

- 외부-facing SDK면 re-export를 설계적으로 관리
- 내부 애플리케이션 코드에서는 출처가 드러나는 import 선호

### 원칙 5: optional dependency는 optional path에 가둔다

- 일부 기능에만 필요한 heavy import는 lazy하게
- core bootstrap에 끌어오지 않기

### 원칙 6: import 문제는 path 조작이 아니라 packaging 정상화로 해결한다

- `pyproject.toml`
- editable install
- `python -m`
- entrypoint 스크립트

### 원칙 7: 측정 없이 startup 최적화하지 않는다

- `python -X importtime`
- 프로세스 시작 시간 메트릭
- cold start / warm start 분리

---

## 실무 예시 7: 서비스 코드를 import-safe하게 바꾸는 리팩터링 순서

기존 코드베이스가 이미 import 문제를 앓고 있다면, 한 번에 다 바꾸려 하기보다 순서가 중요하다.

### 1단계: side effect 허브를 찾는다

우선 아래 파일을 의심한다.

- `settings.py`
- `db.py`
- `__init__.py`
- `main.py`
- `registry.py`
- `plugins.py`

여기서 top-level 실행 로직을 목록화한다.

### 2단계: import graph를 그린다

완벽한 시각화 도구가 없어도 된다.

- 어떤 모듈이 fan-in이 큰가
- 어떤 모듈이 fan-out이 큰가
- 순환 구간이 어디인가

간단한 grep과 에디터 탐색만으로도 충분히 찾을 수 있다.

### 3단계: singleton을 팩토리로 바꾼다

- settings instance
- db engine
- external client
- registry initialization

이 단계만 해도 import 부담이 크게 줄어든다.

### 4단계: 타입 참조를 약화한다

- `TYPE_CHECKING`
- string annotation
- protocol
- interface module

### 5단계: `__init__.py` re-export를 축소한다

필요 최소 public API만 남긴다.

### 6단계: plugin loading을 명시적 단계로 분리한다

`import side effect` -> `load_plugins()`

### 7단계: startup 성능 측정 후 optional dependency를 lazy하게 이동한다

이 순서가 중요한 이유는, lazy import를 너무 먼저 넣으면 구조 문제를 덮어버릴 수 있기 때문이다.

---

## 실무 예시 8: data processing 코드에서 pandas import를 어디에 둘 것인가

배치나 툴링 코드에서 이런 고민이 많다.

```python
import pandas as pd
```

이 한 줄이 작은 스크립트에서는 문제없다.

하지만 아래 상황에서는 고민이 필요하다.

- CLI에 여러 서브명령이 있다
- 그중 일부만 pandas를 쓴다
- 컨테이너를 자주 띄운다
- 단순 `--help`도 느리다

### 나쁜 절충

모든 함수 안에 import를 흩뿌린다.

이건 코드만 어수선해지고 규칙성이 없다.

### 더 나은 선택지

#### 선택지 A: pandas 전용 하위 명령 모듈로 경계를 분리

```python
# cli.py
if args.command == 'report':
    from app.commands.report import main as report_main
    report_main()
```

```python
# app/commands/report.py
import pandas as pd
```

이건 import 위치가 의미적 경계와 일치한다.

#### 선택지 B: optional dependency helper로 감싼다

```python
def require_pandas():
    import pandas as pd
    return pd
```

이 방식은 선택적 기능이 분명할 때 유용하다.

### 어떤 선택이 좋은가?

- 명령/기능 경계가 분명하면 모듈 분리
- 아주 드문 path에서만 필요하면 helper lazy import
- core path라면 그냥 eager import

핵심은 **성능 최적화 방식이 코드 구조와 맞아야 한다**는 점이다.

---

## 실무 예시 9: plugin contract를 protocol로 정의해 core와 plugin의 import 결합도를 낮추기

plugin 시스템에서 core가 plugin 구현체를 너무 많이 알면 순환이 쉽게 생긴다.

### 좋은 기본형

```python
from typing import Protocol


class Exporter(Protocol):
    name: str

    def export(self, rows: list[dict]) -> bytes:
        ...
```

core는 `Exporter` 계약만 안다.

plugin 구현체는 별도 distribution 또는 별도 모듈에 둔다.

```python
class JsonExporter:
    name = 'json'

    def export(self, rows: list[dict]) -> bytes:
        ...
```

런타임 로딩은 entry point 또는 registry에서 명시적으로 한다.

이 구조의 장점은 다음과 같다.

- core가 구현체를 직접 import하지 않는다
- 타입 안정성과 확장성을 같이 가져간다
- optional dependency가 core bootstrap으로 새지 않는다

이건 import 문제를 architecture 수준에서 푸는 좋은 예다.

---

## import 관점에서 보는 좋은 모듈의 특징

좋은 모듈은 보통 아래 특징을 가진다.

- import해도 외부 세계를 크게 건드리지 않는다
- top-level이 선언 중심이다
- 필요한 dependency가 출처와 방향이 명확하다
- 타입 참조와 런타임 참조가 구분된다
- 테스트에서 독립적으로 import 가능하다
- public API와 internal implementation이 섞여 있지 않다

반대로 위험한 모듈은 이렇다.

- import가 곧 연결/초기화/등록/실행이다
- 모든 곳에서 import된다
- 상대적으로 모두를 알고 있다
- `__init__.py`와 결합해 전체 fan-out 허브 역할을 한다
- settings/db/client/global registry를 함께 움켜쥔다

좋은 import 구조는 단지 에러가 안 나는 구조가 아니다.

**예측 가능한 초기화, 측정 가능한 startup, 테스트 가능한 경계**를 가진 구조다.

---

## 운영 체크리스트

### 설계 단계

- [ ] 모듈 top-level에서 외부 리소스 초기화를 하지 않는가?
- [ ] settings, db, external client 생성 시점이 bootstrap으로 분리되어 있는가?
- [ ] 서비스/모델/저장소/인프라 계층의 의존성 방향이 일관적인가?
- [ ] plugin 시스템이 import side effect보다 명시적 load 단계에 가깝게 설계되어 있는가?
- [ ] 패키지 public API와 내부 API를 구분했는가?

### 구현 단계

- [ ] `__init__.py`에 과도한 re-export나 side effect가 없는가?
- [ ] `from x import y`가 순환 민감한 계층에서 남용되지 않는가?
- [ ] 타입 힌트용 import는 `TYPE_CHECKING` 또는 지연 annotation으로 처리했는가?
- [ ] optional/heavy dependency는 필요한 기능 경계 안으로 가뒀는가?
- [ ] 표준 라이브러리/서드파티 이름을 shadowing하는 파일명이 없는가?

### 실행/배포 단계

- [ ] 패키지 내부 실행은 `python -m` 또는 entrypoint로 일관화했는가?
- [ ] editable install 기반으로 로컬 개발 환경을 맞췄는가?
- [ ] `sys.path` 땜질 없이도 CI와 컨테이너에서 import가 안정적인가?
- [ ] cold start와 worker spawn 시간이 import 비용 때문에 과도하게 늘지 않는가?

### 테스트 단계

- [ ] settings cache clear, registry reset 등 import 상태 초기화 전략이 있는가?
- [ ] monkey patch가 import 타이밍과 충돌하지 않는가?
- [ ] 단일 서비스/모듈만 import해도 불필요한 인프라 초기화가 일어나지 않는가?
- [ ] 순환 import가 로컬 우연에 기대지 않고 안정적으로 제거되었는가?

### 성능/관측 단계

- [ ] `python -X importtime`으로 startup 병목을 실제 측정했는가?
- [ ] heavy dependency가 어떤 실행 경로에 붙는지 파악했는가?
- [ ] autoscaling, worker recycle, batch short-run 환경에서 import 비용을 합산해 보았는가?
- [ ] 최적화 전에 구조 문제와 성능 문제를 구분했는가?

---

## 현장에서 바로 적용할 추천 규칙 10개

1. `settings = Settings()`를 top-level에서 바로 만들지 말고 `get_settings()`로 감싼다
2. `engine = create_engine(...)` 같은 인프라 객체는 import 시점이 아니라 bootstrap 시점에 만든다
3. `__init__.py`는 작게 유지하고, 편의 re-export를 최소화한다
4. 순환에 민감한 계층에서는 `import module` 스타일을 우선 검토한다
5. 타입 참조는 `TYPE_CHECKING`과 annotation 지연 평가를 기본값으로 익힌다
6. optional dependency는 명확한 기능 경계 안으로 밀어 넣는다
7. plugin 등록은 import side effect 대신 명시적 load 단계로 설계한다
8. path 문제는 `sys.path` 수정이 아니라 packaging/entrypoint 정상화로 해결한다
9. startup 최적화는 감이 아니라 `-X importtime`으로 측정하고 진행한다
10. local import는 선택적 의존성이나 startup budget 때문에 쓰고, 구조적 순환은 별도 리팩터링 이슈로 관리한다

---

## 한 단계 더: import 문제를 보면 코드베이스 성숙도를 읽을 수 있다

나는 import 구조가 그 팀의 아키텍처 건강도를 꽤 잘 보여준다고 생각한다.

왜냐하면 import는 아래를 전부 드러내기 때문이다.

- 경계가 선명한가
- 초기화 책임이 분리돼 있는가
- 테스트 가능성을 고려했는가
- optional dependency를 통제하는가
- public API와 internal API를 구분하는가
- 성능과 구조를 함께 보는가

작은 프로젝트에서는 import가 단지 스타일 문제처럼 느껴질 수 있다.

하지만 팀이 커지고 서비스가 길게 운영될수록, import는 곧 유지보수성이다.

- 순환 import가 자주 난다 → 계층이 섞였을 가능성
- startup이 자꾸 느리다 → top-level side effect가 무거울 가능성
- 환경마다 import가 깨진다 → 패키징/실행 규칙이 불안정할 가능성
- 테스트 격리가 어렵다 → import 시점 singleton이 많을 가능성

즉 import 문제를 자꾸 만난다면, 그건 문법 문제가 아니라 **아키텍처가 주는 피드백**일 수 있다.

---

## 한 줄 정리

Python import system의 핵심은 단순히 파일을 불러오는 것이 아니라, **`sys.modules`를 중심으로 모듈 초기화 순서·캐시·의존성 방향·startup 비용을 함께 관리해 순환 참조와 side effect를 통제 가능한 구조로 만드는 것**이다.
