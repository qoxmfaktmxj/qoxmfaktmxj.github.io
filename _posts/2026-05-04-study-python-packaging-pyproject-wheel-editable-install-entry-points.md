---
layout: post
title: "Python packaging 실전: pyproject.toml, wheel, editable install, entry points, lockfile로 개발·배포·확장을 한 번에 설계하는 법"
date: 2026-05-04 11:40:00 +0900
categories: [python]
tags: [study, python, packaging, pyproject, wheel, sdist, editable-install, entry-points, dependency-management, build-backend, lockfile, operations]
permalink: /python/2026/05/04/study-python-packaging-pyproject-wheel-editable-install-entry-points.html
---

## 배경: Python packaging은 배포 마지막 단계가 아니라 개발·실행·운영 규칙의 시작점이다

Python 프로젝트가 어느 정도 커지면 결국 비슷한 순간이 온다.

- 로컬에서는 되는데 CI에서만 `ModuleNotFoundError`가 난다
- FastAPI 앱은 잘 떠 있는데 worker 이미지에서는 import 경로가 다르게 잡힌다
- CLI를 만들었는데 팀원마다 실행 방식이 제각각이라 재현이 안 된다
- `pip install -e .`로는 잘 되는데 wheel 설치 환경에서는 데이터 파일이 빠진다
- plugin 구조를 만들었는데 구현체를 import side effect로 등록하다가 startup이 무거워진다
- 앱은 lockfile에 의존하는데 라이브러리까지 exact pin을 박아 downstream 충돌을 만든다
- `requirements.txt`, `setup.py`, `setup.cfg`, `pyproject.toml`, 도구별 설정이 흩어져 있어 어느 파일이 진실인지 모른다
- Docker 이미지에서는 빌드가 되는데 사내 PyPI에 배포하면 메타데이터가 틀려 설치 단계에서 깨진다
- monorepo에서 공용 패키지를 분리하려는데 경계가 코드 구조보다 작업 디렉터리 운에 의존한다

여기서 흔한 오해가 있다.

> packaging은 릴리스 직전에만 신경 쓰면 되는 마감 작업이다.

실무에서는 정반대다.

**packaging은 코드가 어떤 이름으로 설치되고, 어떤 의존성을 가져오며, 어떤 실행 진입점을 만들고, 어떤 파일을 배포 단위에 포함하며, 개발 환경과 운영 환경 사이 차이를 얼마나 줄일지 결정하는 기본 계약**이다.

특히 중급 이상 개발자에게 packaging은 단순 문법 문제가 아니다.

- import 안정성 문제다
- 팀 개발 환경 표준화 문제다
- CI/CD 재현성 문제다
- Docker 빌드 구조 문제다
- 내부 라이브러리 배포 전략 문제다
- plugin/extension 아키텍처 문제다
- supply chain과 운영 리스크 문제다

이 글은 `pyproject.toml` 문법 소개에서 멈추지 않는다.

아래 질문에 실무 기준으로 답하려 한다.

1. 왜 modern Python packaging의 중심이 `pyproject.toml`인가?
2. `wheel`, `sdist`, `editable install`은 정확히 무엇이 다르고 언제 문제가 드러나는가?
3. `src` layout, entry point, optional dependency, lockfile을 어떻게 조합해야 로컬/CI/운영 차이를 줄일 수 있는가?
4. 앱과 라이브러리는 의존성 관리 전략이 왜 달라야 하는가?
5. plugin 구조, CLI, 내부 패키지 배포를 packaging 친화적으로 설계하려면 무엇을 고정하고 무엇을 유연하게 둬야 하는가?

핵심 결론만 먼저 말하면 이렇다.

> Python packaging의 핵심은 "파일을 묶어 배포한다"가 아니라, **코드·의존성·실행 진입점·빌드 규칙을 설치 가능한 계약으로 승격시키는 것**이다.

그리고 이 계약이 명확할수록 로컬에서 우연히 돌아가는 코드가 줄고, CI·컨테이너·배포 환경에서의 놀람이 줄어든다.

---

## 먼저 큰 그림: packaging은 빌드 시스템이 아니라 "설치 가능한 경계"를 만드는 일이다

많은 팀이 packaging을 도구 선택 문제로 시작한다.

- setuptools를 쓸까?
- hatchling이 더 낫나?
- Poetry를 써야 하나?
- uv로 갈아탈까?

물론 도구도 중요하다.

하지만 실무에서 먼저 봐야 할 것은 도구가 아니라 **배포 단위의 경계**다.

### packaging이 실제로 결정하는 것

1. **이 프로젝트의 이름은 무엇인가**
2. **설치 시 어떤 패키지가 import 가능한가**
3. **어떤 Python 버전과 의존성이 필요한가**
4. **실행 진입점은 무엇인가**
5. **소스 배포와 바이너리 배포에 어떤 파일이 들어가는가**
6. **로컬 개발과 배포 설치 방식이 얼마나 비슷한가**
7. **확장 기능은 extras나 entry point로 어떻게 노출되는가**
8. **CI가 어떤 규칙으로 빌드/검증/배포하는가**

즉 packaging은 `pip install` 한 줄의 뒷면에 있는 **운영 계약서**에 가깝다.

### packaging을 잘못 이해하면 생기는 구조적 문제

- 작업 디렉터리에 기대는 import
- 빌드 환경과 실행 환경의 분리 실패
- dev dependency와 runtime dependency 혼합
- CLI/worker/web app 각각 다른 진입점 관리
- 내부 공용 모듈이 패키지가 아니라 복붙 폴더로 남는 문제
- optional dependency가 core import 경계 밖으로 새는 문제
- wheel로 설치했을 때만 빠지는 리소스 파일

좋은 packaging은 이 문제를 예방한다.

나쁜 packaging은 배포 직전보다 **프로젝트가 커질수록** 비용이 기하급수적으로 커진다.

---

## 핵심 개념 1: `pyproject.toml`은 설정 파일 하나가 아니라 build contract의 단일 진실 소스여야 한다

modern Python packaging의 출발점은 `pyproject.toml`이다.

이 파일이 중요한 이유는 단순히 최신 문법이어서가 아니다.

`pyproject.toml`은 최소한 아래 두 가지를 명시한다.

1. **이 프로젝트를 빌드하려면 무엇이 필요한가**
2. **이 프로젝트의 메타데이터는 무엇인가**

가장 최소한의 예시는 아래처럼 생긴다.

```toml
[build-system]
requires = ["hatchling>=1.26"]
build-backend = "hatchling.build"

[project]
name = "acme-notify"
version = "0.3.0"
description = "Notification service shared package"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
  "pydantic>=2.8,<3",
  "httpx>=0.28,<0.29",
]
```

### 왜 이 구조가 중요한가

과거에는 다음 파일이 섞여 있었다.

- `setup.py`
- `setup.cfg`
- `requirements.txt`
- 도구별 설정 파일

이 상태에서는 종종 이런 일이 벌어진다.

- 설치 메타데이터는 `setup.py`에 있고
- lint/test 도구 설정은 `setup.cfg`에 있고
- 의존성은 `requirements.txt`에 있고
- 빌드 백엔드 정보는 따로 없다

즉 설치 규칙과 개발 규칙이 분산된다.

`pyproject.toml`의 장점은 **빌드 진입점과 프로젝트 메타데이터를 한 자리로 모은다**는 점이다.

### 실무 기준: `pyproject.toml`은 무엇을 담고, 무엇을 담지 말아야 하나

담아야 하는 것:

- build backend 정의
- 배포 패키지 메타데이터
- runtime dependency
- optional extras
- console scripts / entry points
- 주요 도구 설정의 기준점

무작정 넣지 말아야 하는 것:

- 배포와 무관한 임시 운영 메모
- 환경별 비밀값
- lockfile 내용을 억지로 중복한 exact dependency 목록
- Docker 전용 명령 시퀀스

`pyproject.toml`은 모든 문제를 다 넣는 만능 창고가 아니라, **설치 가능한 프로젝트에 대한 선언적 설명서**에 가까워야 한다.

---

## 핵심 개념 2: build backend 선택은 종교가 아니라 프로젝트 제약과 팀 습관의 문제다

Python packaging 이야기에서 자주 싸움이 나는 지점이 있다.

- setuptools는 낡았나?
- Poetry는 무겁나?
- Hatch가 더 깔끔한가?
- uv만 있으면 다 끝나나?

실무적으로는 도구를 과하게 이념화할 필요가 없다.

### 먼저 역할을 분리해서 보자

- **build backend**: wheel/sdist를 어떻게 만들지 결정
- **installer/resolver**: 의존성을 어떻게 해석하고 설치할지 결정
- **project manager**: 가상환경, 스크립트, lockfile, publish 경험을 어떻게 감쌀지 결정

이 역할들이 한 도구에 묶일 수도 있고 분리될 수도 있다.

### 대표적인 선택 기준

#### 1) setuptools

잘 맞는 경우:

- 레거시 패키지와의 호환성이 중요함
- 확장 모듈, 복잡한 package data, 오래된 생태계 관성이 큼
- 사내에 이미 setuptools 지식이 축적되어 있음

주의할 점:

- 과거 관성 때문에 imperative 설정이 남아 있을 수 있음
- 오래된 `setup.py` 패턴을 그대로 답습하면 modern contract의 이점을 줄임

#### 2) hatchling

잘 맞는 경우:

- pure Python 패키지 중심
- 선언적 설정을 선호함
- 메타데이터와 빌드를 단순하게 유지하고 싶음

주의할 점:

- 팀 내 레거시 setuptools 습관과 충돌할 수 있음
- 아주 특수한 빌드 커스터마이징은 별도 확인이 필요함

#### 3) poetry-core / Poetry 생태계

잘 맞는 경우:

- 이미 Poetry workflow를 팀에서 안정적으로 쓰고 있음
- dependency management와 publish 경험을 한 도구로 묶고 싶음

주의할 점:

- build backend와 tool workflow를 분리해서 이해하지 않으면 lock/publish 경계가 흐려질 수 있음
- 조직 표준이 아니라면 일부 팀원은 설치 경로를 다르게 사용하게 됨

#### 4) uv 기반 workflow

잘 맞는 경우:

- 빠른 resolver/installer가 중요함
- 앱 개발에서 reproducibility와 속도를 동시에 챙기고 싶음
- Python 도구 체인을 단순화하고 싶음

주의할 점:

- uv는 만능 build backend가 아니라 workflow 계층이라는 관점이 필요함
- 사내 배포 규칙과 CI 이미지가 아직 구형이면 전환 계획이 있어야 함

### 추천 원칙

- **도구를 바꾸는 이유가 명확할 때만 바꾼다**
- **앱과 라이브러리의 배포 성격을 먼저 정의한다**
- **팀이 디버깅 가능한 수준의 단순성을 유지한다**

나는 실무에서 아래 기준이 꽤 안전하다고 본다.

- 라이브러리: build metadata와 호환성이 가장 중요
- 앱: resolver 속도, lockfile, CI reproducibility가 더 중요
- plugin 생태계: entry point와 optional dependency 설계가 중요

즉 "최고의 도구"보다 **현재 팀이 가장 적은 실수로 일관되게 운영할 수 있는 도구**가 더 중요하다.

---

## 핵심 개념 3: `src` layout은 취향 문제가 아니라 import 오류를 조기에 드러내는 안전장치다

Python packaging을 진지하게 다루기 시작하면 거의 반드시 만나게 되는 논쟁이 있다.

- flat layout이면 충분하지 않나?
- 왜 굳이 `src/` 밑에 패키지를 넣어야 하나?

예를 들어 flat layout은 이런 구조다.

```text
project/
  pyproject.toml
  myapp/
    __init__.py
    service.py
  tests/
```

`src` layout은 보통 이렇게 간다.

```text
project/
  pyproject.toml
  src/
    myapp/
      __init__.py
      service.py
  tests/
```

### `src` layout의 핵심 장점

`src` layout은 프로젝트 루트가 우연히 `sys.path`에 잡혀도, **설치 없이 소스가 바로 import되는 착시를 줄인다**.

즉 이런 문제를 빨리 발견하게 해 준다.

- 패키지 선언이 잘못됨
- 설치 메타데이터가 틀림
- 테스트가 실제 설치된 artifact가 아니라 로컬 폴더를 보고 있음
- 작업 디렉터리에 기대는 실행 방식이 숨어 있음

### 왜 이게 실무에서 중요할까

flat layout에서는 아래 실수가 쉽게 숨는다.

```bash
pytest
python scripts/run_job.py
uvicorn myapp.main:app
```

프로젝트 루트에서만 돌리면 다 되는 것처럼 보인다.

하지만 wheel 설치 환경, 별도 working directory, Docker runtime 이미지, cron, Lambda/Cloud Run 같은 환경에서는 바로 깨질 수 있다.

`src` layout은 이 착시를 줄인다.

### `src` layout이 무조건 정답인가?

그건 아니다.

아래 경우에는 flat layout도 충분할 수 있다.

- 아주 작은 단일 스크립트성 프로젝트
- 패키지 배포보다 앱 저장소 내부 실행만 있는 경우
- 팀 전체가 packaging discipline을 이미 잘 지키는 경우

하지만 서비스가 커지고 아래가 하나라도 생기면 `src` layout의 가치가 빠르게 올라간다.

- 사내 공용 라이브러리 분리
- CLI 배포
- plugin 구조
- multiple entry points
- wheel 기반 배포
- monorepo 내부 서브패키지 운영

### 추천 기준

- **재사용 가능한 패키지/라이브러리**: `src` layout 권장
- **장기 운영 앱**: 가능하면 `src` layout 권장
- **짧은 수명의 내부 스크립트**: flat layout 허용

중요한 건 `src`를 썼느냐가 아니라, **설치된 artifact와 로컬 실행의 차이를 얼마나 빨리 드러내느냐**다.

---

## 핵심 개념 4: `wheel`, `sdist`, `editable install`은 같은 설치가 아니다

많은 팀이 여기서 헷갈린다.

- `pip install -e .`가 되면 배포도 되겠지?
- source tree에서 테스트가 통과하면 wheel도 괜찮겠지?

이건 자주 틀린다.

### 1) sdist

소스 배포본이다.

보통 아래를 담는다.

- 원본 소스 파일
- 빌드에 필요한 메타데이터
- 패키지 데이터 일부

설치 시점에는 **sdist를 받아 다시 wheel을 빌드하거나 소스 기반 설치**가 일어날 수 있다.

즉 sdist는 "소스가 충분히 들어 있는가"를 검증하는 관점이 중요하다.

자주 터지는 문제:

- `README.md` 누락
- package data 누락
- `MANIFEST.in` 또는 backend 포함 규칙 누락
- 생성 파일이 빌드 환경에 없어서 실패

### 2) wheel

설치용 빌드 artifact다.

운영 환경에서는 보통 wheel이 핵심이다.

이유는 단순하다.

- 설치가 빠르다
- 빌드 환경에 덜 의존한다
- 배포 파이프라인에서 재현성이 좋아진다

즉 배포 직전 검증은 가능하면 **wheel 설치 기준으로** 보는 편이 맞다.

### 3) editable install

개발 편의를 위한 설치다.

```bash
pip install -e .
```

혹은 팀 도구에 맞춘 동등한 명령을 쓴다.

editable install의 핵심은 **소스 수정이 설치 환경에 즉시 반영되도록 연결하는 것**이다.

이건 개발 효율에는 매우 좋다.

하지만 배포 검증을 대체하지는 못한다.

### 왜 editable이 배포 문제를 숨길 수 있나

- 소스 트리에 직접 접근하므로 wheel 포함 규칙 누락이 감춰진다
- package data 누락이 로컬 파일 접근으로 우연히 보완된다
- working directory가 같아 상대 경로 버그가 안 보인다
- entry point 스크립트 생성 여부보다 직접 `python -m ...` 실행에 의존하게 된다

### 실무 권장 검증 순서

1. 로컬 개발은 editable install로 빠르게 반복
2. CI에서는 실제 wheel/sdist를 빌드
3. **빌드된 wheel을 새로운 환경에 설치해서 테스트**
4. 필요하면 sdist에서도 설치 검증

예를 들면:

```bash
python -m build
python -m venv .venv-wheel-test
. .venv-wheel-test/bin/activate
pip install dist/*.whl
pytest
```

이 한 단계를 빼면, 배포 후에만 보이는 packaging 문제를 자주 놓친다.

---

## 핵심 개념 5: 앱과 라이브러리는 의존성 전략이 달라야 한다

여기서 많은 팀이 실수한다.

앱 운영 관점과 라이브러리 배포 관점을 섞어 버리는 것이다.

### 앱(application)의 관점

앱은 보통 **내가 실행하는 최종 산출물**이다.

그래서 중요 포인트가 다르다.

- 재현 가능한 설치
- 배포 시점 lockfile
- 이미지 빌드 안정성
- 보안 스캔 일관성
- 운영 환경 간 동일한 dependency graph

앱에서는 exact pin이나 lockfile이 꽤 중요하다.

### 라이브러리(library)의 관점

라이브러리는 **남이 설치하는 배포 단위**다.

따라서 너무 공격적인 exact pin은 오히려 해롭다.

예를 들어 이런 식은 문제를 만든다.

```toml
[project]
dependencies = [
  "httpx==0.28.1",
  "pydantic==2.8.2",
]
```

이런 exact pin은 downstream 프로젝트와 충돌을 만들기 쉽다.

대부분의 라이브러리는 **호환 가능한 범위**를 선언하고, 실제 앱에서 lock하는 편이 안전하다.

예:

```toml
[project]
dependencies = [
  "httpx>=0.28,<0.29",
  "pydantic>=2.8,<3",
]
```

### 왜 이 차이가 중요한가

앱은 한 팀이 실행 책임을 진다.

라이브러리는 여러 팀/서비스/환경에 들어간다.

즉 앱은 **재현성**이 우선이고, 라이브러리는 **호환성**이 우선이다.

### optional dependency를 어떻게 봐야 하나

`extras`는 종종 잘못 쓰인다.

좋은 예:

```toml
[project.optional-dependencies]
postgres = ["psycopg[binary]>=3.2,<4"]
redis = ["redis>=5,<6"]
cli = ["typer>=0.13,<1"]
```

이 구조는 기능 경계를 잘 드러낸다.

나쁜 예:

- 개발용 도구를 전부 `dev` extra 하나에 밀어 넣고, 실제로는 internal workflow에만 의미가 있음
- runtime에서 항상 필요한데 optional처럼 숨겨 버림
- core import 단계에서 optional dependency를 이미 import함

### 실무 원칙

- 앱 lockfile과 배포 설치 그래프는 정확하게 관리한다
- 라이브러리 메타데이터는 호환 범위를 선언한다
- optional feature는 optional dependency와 import 경계를 같이 설계한다
- dev/test 도구는 배포 metadata와 섞지 않는다

---

## 핵심 개념 6: entry point는 CLI 편의 기능이 아니라 "설치 후 실행 경로"를 표준화하는 장치다

많은 Python 프로젝트가 실행 방식을 너무 느슨하게 둔다.

- 어떤 사람은 `python app.py`
- 어떤 사람은 `python -m myapp`
- 어떤 사람은 `uvicorn myapp.main:app`
- 어떤 사람은 `scripts/run_local.sh`

이 상태는 금방 혼란으로 이어진다.

entry point는 이 혼란을 줄여 준다.

### console script 예시

```toml
[project.scripts]
acme-notify = "acme_notify.cli:main"
```

설치 후에는 이렇게 실행할 수 있다.

```bash
acme-notify send-digest
```

### 왜 이 방식이 좋은가

- 실행 이름이 설치 metadata에 명시된다
- 가상환경/운영환경에서 동일한 진입점을 쓸 수 있다
- CLI 사용자 입장에서 진입 규칙이 단순해진다
- 팀 문서와 자동화 스크립트가 깔끔해진다

### `python -m`과 entry point는 경쟁 관계가 아니다

둘은 함께 쓰는 편이 좋다.

- 내부 디버깅/개발: `python -m myapp.cli`
- 사용자/운영 진입점: `acme-notify`

중요한 것은 **어떤 실행 방식이 공식 경로인지 팀이 합의하는 것**이다.

### plugin entry points는 더 강력하다

아래처럼 확장 지점을 선언할 수 있다.

```toml
[project.entry-points."acme_notify.exporters"]
json = "acme_notify_json:JsonExporter"
slack = "acme_notify_slack:SlackExporter"
```

런타임에서는:

```python
from importlib.metadata import entry_points


def load_exporters() -> dict[str, type]:
    exporters = {}
    for ep in entry_points(group="acme_notify.exporters"):
        exporters[ep.name] = ep.load()
    return exporters
```

이 구조의 장점은 크다.

- 파일 시스템 스캔보다 배포 단위가 명확하다
- optional plugin을 distribution 단위로 분리하기 쉽다
- import side effect 없이 명시적으로 로딩할 수 있다
- 사내 확장 패키지를 독립 배포할 수 있다

즉 entry point는 단순 CLI 편의가 아니라 **실행 경계와 확장 경계를 메타데이터로 끌어올리는 장치**다.

---

## 핵심 개념 7: package data, 정적 파일, 템플릿은 "로컬 파일이 있으니까 되겠지"라고 생각하면 거의 반드시 깨진다

packaging 이슈는 Python 코드만의 문제가 아니다.

아래 자산이 들어가는 순간부터 더 까다로워진다.

- Jinja 템플릿
- SQL 파일
- JSON schema
- 기본 설정 템플릿
- CLI용 프롬프트 텍스트
- ML 모델 메타데이터
- static asset

로컬 editable 환경에서는 파일이 옆에 있으니 잘 보인다.

하지만 wheel 설치 환경에서는 포함 규칙이 없으면 바로 사라진다.

### 흔한 안티패턴

```python
from pathlib import Path

SQL = Path(__file__).parent / "queries" / "daily_report.sql"
```

이 코드 자체가 잘못은 아니다.

문제는 **그 파일이 빌드 artifact에 실제로 포함되는지**를 확인하지 않는 것이다.

### 더 안전한 접근

- backend별 package data/include 규칙을 명시한다
- 파일 접근은 패키지 리소스 관점으로 설계한다
- wheel 설치 기준 테스트를 돌린다

예를 들어 `importlib.resources`를 쓰면 설치 형태에 덜 의존적이다.

```python
from importlib.resources import files

sql_text = files("acme_notify.queries").joinpath("daily_report.sql").read_text(encoding="utf-8")
```

### 실무 기준으로 꼭 확인할 것

- 템플릿/정적 파일이 sdist와 wheel 모두에 포함되는가
- 패키지 이름과 실제 resource path가 일치하는가
- 런타임이 소스 파일 경로가 아니라 설치된 resource를 보고 있는가
- tests가 editable 환경 착시를 만들고 있지 않은가

이건 자잘한 디테일 같지만, 운영에서는 아주 자주 배포 사고 원인이 된다.

---

## 실무 예시 1: FastAPI 서비스 + 공용 SDK + CLI를 한 저장소에서 packaging 친화적으로 정리하는 법

가상의 구조를 보자.

```text
repo/
  pyproject.toml
  src/
    acme_platform/
      api/
        main.py
      sdk/
        client.py
      cli.py
      settings.py
  tests/
```

처음에는 한 패키지로도 충분할 수 있다.

하지만 시간이 지나면 요구가 늘어난다.

- API 서버는 컨테이너로 배포
- SDK는 다른 worker 저장소에서도 재사용
- CLI는 운영팀이 잡 실행에 사용

여기서 packaging 관점에서 중요한 질문은 세 가지다.

1. 이걸 하나의 distribution으로 유지할 것인가?
2. CLI와 API가 같은 runtime dependency를 공유해야 하는가?
3. SDK를 독립 배포 단위로 분리할 시점이 왔는가?

### 초기 단계의 안전한 설계

초기에는 한 distribution 안에 두되, import 경계를 분리한다.

```toml
[project]
name = "acme-platform"
dependencies = [
  "fastapi>=0.115,<1",
  "pydantic>=2.8,<3",
  "httpx>=0.28,<0.29",
]

[project.optional-dependencies]
cli = ["typer>=0.13,<1"]
postgres = ["sqlalchemy>=2.0,<3", "psycopg[binary]>=3.2,<4"]

[project.scripts]
acme-platform = "acme_platform.cli:main"
```

이 구조의 장점:

- 기본 패키지 이름은 하나로 간단하다
- CLI는 공식 진입점이 있다
- DB 기능이나 CLI 기능을 optional로 분리할 수 있다
- API/CLI/SDK 모듈이 같은 저장소에서 import 안정성을 공유한다

### 하지만 이런 냄새가 보이면 분리 시점을 검토해야 한다

- SDK를 다른 저장소가 독립적으로 사용하기 시작함
- API와 SDK의 release cadence가 다름
- CLI만 필요한 환경에 서버 dependency가 과도하게 따라옴
- 변경 영향 범위가 distribution 하나에 과도하게 묶임

그 시점에는 보통 이렇게 나눈다.

- `acme-sdk`
- `acme-api`
- `acme-cli`

중요한 건 빨리 쪼개는 게 아니라, **packaging 경계가 실제 변경 경계와 맞아떨어질 때 분리하는 것**이다.

---

## 실무 예시 2: 내부 공용 라이브러리를 배포할 때 lockfile을 같이 밀어 넣지 말아야 하는 이유

사내 공용 패키지를 만들다 보면 종종 이런 요구가 나온다.

- "문제 없게 exact version으로 잠가 두자"
- "앱에서 쓰던 lock 그대로 라이브러리에도 넣자"

이 접근은 편해 보이지만 장기적으로 충돌을 만든다.

### 왜 문제가 되나

공용 라이브러리는 여러 소비자가 가져간다.

- API 서버
- 백그라운드 worker
- 데이터 파이프라인
- 노트북/배치 작업

각 소비자는 이미 자신만의 dependency graph를 갖고 있다.

여기에 공용 라이브러리가 exact pin을 강요하면 충돌이 늘어난다.

예를 들어 공용 SDK가 아래를 요구한다고 하자.

```toml
[project]
dependencies = [
  "pydantic==2.8.2",
  "httpx==0.28.1",
]
```

어떤 서비스는 `pydantic 2.9`와 호환되고, 다른 서비스는 `httpx 0.28`의 다른 patch를 이미 쓰고 있을 수 있다.

이 경우 불필요한 resolver 충돌이 생긴다.

### 더 안전한 전략

- 라이브러리: 호환 범위를 선언
- 각 앱: lockfile로 실제 배포 그래프 고정

즉 책임을 분리한다.

- **라이브러리 책임**: 어느 범위까지 호환되는지 명시
- **앱 책임**: 실제 운영 그래프를 재현 가능하게 잠금

### 예외는 없나?

있다.

아래 경우는 다르게 볼 수 있다.

- 극도로 민감한 보안 요구로 특정 버전을 강제해야 함
- 사내 폐쇄 생태계에서 전 팀이 하나의 release train을 따름
- app-like internal package라 사실상 단일 소비자만 있음

그래도 기본값은 exact pin이 아니라 **검증된 호환 범위**가 맞다.

---

## 실무 예시 3: plugin 생태계를 만들 때 import side effect 대신 entry point를 쓰는 이유

확장 가능한 시스템은 처음엔 보통 이렇게 시작한다.

```python
# plugins/__init__.py
from .slack import SlackPlugin
from .email import EmailPlugin
from .pagerduty import PagerDutyPlugin
```

혹은 디렉터리를 스캔해서 import한다.

이 방식은 작을 때는 쉽다.

하지만 시스템이 커지면 문제를 만든다.

- plugin import 순간 optional dependency가 다 로드된다
- 없는 dependency 하나 때문에 전체 startup이 깨진다
- 어떤 plugin이 왜 등록됐는지 추적이 어렵다
- 외부 팀이 plugin을 독립 배포하기 어렵다

entry point 기반 구조는 이 문제를 줄인다.

### core package

```toml
[project.entry-points."acme_ingest.connectors"]
s3 = "acme_ingest_s3:S3Connector"
gcs = "acme_ingest_gcs:GCSConnector"
```

혹은 plugin package들이 각자 선언할 수도 있다.

### plugin package

```toml
[project]
name = "acme-ingest-snowflake"
dependencies = [
  "acme-ingest-core>=1.4,<2",
  "snowflake-connector-python>=3.12,<4",
]

[project.entry-points."acme_ingest.connectors"]
snowflake = "acme_ingest_snowflake:SnowflakeConnector"
```

### 이 구조의 실무 장점

- plugin은 distribution 단위로 독립 릴리스 가능
- core package는 plugin 구현체를 직접 import하지 않음
- optional dependency를 plugin 쪽으로 격리 가능
- 사내 팀별 책임 경계를 명확하게 나눌 수 있음
- startup 시점에 필요한 plugin만 로드 가능

### 트레이드오프

- 메타데이터 설계를 잘해야 한다
- 디버깅할 때 entry point discovery 이해가 필요하다
- 테스트에서 plugin matrix를 명시적으로 관리해야 한다

하지만 확장 생태계를 진지하게 운영할 생각이면, 이 비용은 충분히 낼 만하다.

---

## 실무 예시 4: Docker 빌드에서 packaging을 제대로 쓰면 이미지가 더 단순해진다

Python 서비스 Dockerfile이 지저분해지는 큰 이유 중 하나는 packaging 경계가 약하기 때문이다.

예를 들어 이런 패턴은 자주 보인다.

- `COPY . .`
- `pip install -r requirements.txt`
- 코드와 의존성이 섞인 채 전체 소스를 그대로 런타임 이미지에 넣음

이 방식은 나쁜 건 아니지만, 다음 문제가 생기기 쉽다.

- 의존성 캐시 효율이 떨어짐
- 테스트/문서/로컬 전용 파일이 런타임 이미지에 따라 들어감
- 실제 배포 artifact가 무엇인지 모호함

packaging 중심으로 보면 Docker 빌드도 정리된다.

### 예시 흐름

1. `pyproject.toml`과 lock 관련 파일 먼저 복사
2. 의존성 설치
3. 소스 복사
4. wheel 빌드
5. runtime 이미지에는 wheel만 설치

개념적으로는 아래와 비슷하다.

```dockerfile
FROM python:3.12-slim AS builder
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m pip install --upgrade pip build
RUN python -m build

FROM python:3.12-slim AS runtime
WORKDIR /app
COPY --from=builder /app/dist/*.whl /tmp/
RUN pip install /tmp/*.whl && rm -rf /tmp/*.whl
CMD ["acme-platform"]
```

### 이 접근의 장점

- runtime 이미지가 실제 설치 artifact 기준으로 움직인다
- 소스 트리 착시에 덜 의존한다
- 배포 전 wheel 설치 검증과 흐름이 일치한다
- 이미지가 더 예측 가능해진다

물론 앱 특성에 따라 소스 직접 복사 전략이 더 실용적인 경우도 있다.

하지만 장기적으로는 **운영 환경이 로컬 소스 트리가 아니라 설치 artifact를 기준으로 돈다**는 사실을 의식하는 편이 안전하다.

---

## 핵심 개념 8: lockfile은 중요하지만, packaging metadata를 대체하지는 못한다

최근 Python 생태계에서 lockfile의 중요성은 더 커졌다.

그 자체는 좋은 방향이다.

하지만 여기서도 경계를 구분해야 한다.

### lockfile이 잘하는 일

- 특정 시점의 resolved dependency graph 고정
- CI/배포 재현성 향상
- 보안 스캔 대상을 명확히 함
- 설치 속도와 predictability 개선

### lockfile이 못하는 일

- 라이브러리 소비자에게 호환 범위를 설명하는 것
- entry point를 선언하는 것
- build backend를 정의하는 것
- package data 포함 규칙을 선언하는 것
- 패키지 이름/버전/메타데이터를 대체하는 것

즉 lockfile은 packaging의 일부 워크플로우에 중요하지만, **프로젝트 메타데이터 자체는 아니다**.

### 실무 분리 원칙

- 배포 가능한 프로젝트 설명: `pyproject.toml`
- 설치 그래프 고정: lockfile 또는 tool-managed lock state
- CI 검증: 둘 다 사용

이 둘을 구분하지 않으면 이런 실수가 나온다.

- lockfile만 맞으면 packaging은 대충 해도 된다고 생각
- 앱용 lock 전략을 라이브러리 메타데이터에 그대로 복사
- `requirements.txt`를 project metadata처럼 취급

나는 보통 이렇게 정리한다.

> `pyproject.toml`은 프로젝트가 세상에 자신을 설명하는 문서이고, lockfile은 특정 시점에 팀이 설치를 재현하기 위한 스냅샷이다.

둘은 역할이 다르다.

---

## 실무 예시 5: monorepo에서 Python 공용 패키지를 다룰 때 가장 먼저 고정해야 할 것

monorepo는 packaging을 생략해도 당장은 돌아가기 쉽다.

같은 저장소 안에 다 있으니 import가 쉬워 보이기 때문이다.

하지만 규모가 커지면 바로 문제가 생긴다.

- 서비스 A는 루트에서 실행해야만 import됨
- 서비스 B는 IDE 설정에 따라 되고 안 됨
- 배치 작업은 경로를 수동 추가해야 함
- 공용 모듈 변경이 어디에 배포 영향을 주는지 안 보임

### monorepo에서 먼저 고정할 것

1. 각 배포 단위의 패키지 이름
2. 각 배포 단위의 버전 전략
3. 공용 패키지를 editable path로만 쓸지, 내부 index에 publish할지
4. 테스트가 설치 artifact 기준인지 소스 경로 기준인지
5. 서비스 간 의존성을 코드 경계와 릴리스 경계 중 어느 쪽으로 볼지

### 단기적으로 쉬운 길과 장기적으로 안전한 길

쉬운 길:

- `PYTHONPATH` 추가
- 경로 append
- 저장소 루트에서만 돌아가게 유지

안전한 길:

- 내부 패키지도 설치 가능한 단위로 만든다
- root workflow와 distribution metadata를 분리한다
- 필요한 경우 내부 package registry를 둔다
- 최소한 editable install 기준으로 각 하위 패키지를 정식 설치한다

monorepo의 핵심은 한 저장소라는 사실이 아니라, **여러 배포 단위를 어떻게 일관된 계약으로 운영하느냐**다.

packaging을 무시하면 monorepo의 편의는 곧 경로 지옥으로 변한다.

---

## 핵심 개념 9: build isolation을 이해하지 못하면 "로컬에서는 되는데 CI에서는 안 되는" 이유를 계속 오해한다

modern packaging에서 빌드는 보통 **격리된 환경(build isolation)** 에서 일어난다.

이 말은 중요하다.

빌드할 때 현재 개발자 가상환경에 우연히 깔려 있는 패키지에 기대면 안 된다는 뜻이기 때문이다.

### 왜 build isolation이 필요한가

- 빌드 결과가 개발자 개인 환경에 오염되지 않게 하려면
- 다른 CI runner, 다른 OS, 다른 Python 버전에서도 비슷한 규칙으로 artifact를 만들려면
- 패키지가 실제로 선언한 build dependency만으로 빌드 가능한지 검증하려면

예를 들어 아래처럼 `pyproject.toml`의 `[build-system]` 이 부실하면 문제가 난다.

```toml
[build-system]
requires = ["setuptools>=69", "wheel"]
build-backend = "setuptools.build_meta"
```

겉보기에는 멀쩡해 보여도, 빌드 중에 버전 계산이나 코드 생성, C 확장 빌드, 템플릿 전처리에 다른 도구가 필요하다면 CI에서 바로 깨질 수 있다.

### 실무에서 자주 보는 오해

#### 오해 1) "내 로컬 venv에서는 build가 되는데요?"

그건 현재 venv에 우연히 필요한 패키지가 미리 깔려 있어서일 수 있다.

#### 오해 2) "requirements-dev.txt에 있으니 되지 않나요?"

아니다.

빌드에 필요한 것은 **build-system requires** 나 backend가 요구하는 공식 경로에 있어야 한다.

#### 오해 3) "어차피 Docker에서 빌드하니 괜찮습니다"

Docker도 결국 build 환경이다.

이미지 안에서 우연히 깔린 패키지에 기대면, 베이스 이미지가 바뀌는 순간 같은 문제가 반복된다.

### build isolation 관점에서 점검할 것

- 버전 계산이 git metadata에 의존하는가?
- README 변환, 코드 생성, C 확장 빌드에 추가 의존성이 필요한가?
- backend가 문서화한 build dependency를 명시했는가?
- wheel 빌드가 네트워크 연결이나 로컬 캐시에 과도하게 기대는가?

### 중요한 실무 감각

빌드가 격리 환경에서 안정적으로 돌아가지 않으면, 그 프로젝트는 아직 packaging이 끝난 것이 아니다.

로컬 성공은 신호일 뿐이고, **격리 빌드 성공이 실제 기준**이다.

---

## 핵심 개념 10: 버전 전략은 release note용 숫자가 아니라 dependency graph와 호환성 약속이다

버전은 너무 자주 가볍게 다뤄진다.

- 대충 올리고
- 태그 찍고
- publish하고
- 깨지면 다시 올린다

내부 서비스만 있는 팀이라면 당장은 버틸 수 있다.

하지만 공용 패키지, SDK, plugin 생태계, 데이터 파이프라인 공통 유틸이 늘어나는 순간 버전은 단순 숫자가 아니다.

### 버전이 실제로 의미하는 것

- 어떤 변경이 하위 호환성을 깨는가
- 어떤 서비스가 어떤 기능 범위를 기대할 수 있는가
- rollback 시 어떤 artifact로 돌아갈 수 있는가
- plugin/core 호환 범위를 어떻게 표현할 것인가

### 라이브러리와 앱의 버전 감각은 다르다

#### 라이브러리

중요한 것:

- public API 변화 추적
- dependency range 호환성 유지
- deprecated API의 제거 시점 예고
- consumer가 upgrade risk를 가늠할 수 있는 신호 제공

#### 앱

중요한 것:

- 배포 식별성
- rollback 대상 구분
- 운영 이슈와 release artifact 연결
- infra/image/schema change와의 정합성

### 사내 패키지에서 특히 조심할 것

사내 프로젝트라고 해서 버전 규율을 대충 가져가면 안 된다.

오히려 내부 패키지는 아래 이유로 더 엄격해야 한다.

- 여러 서비스가 동시에 소비할 수 있음
- breaking change가 외부보다 덜 드러나 조용히 전파됨
- changelog와 migration note가 없으면 팀 간 커뮤니케이션 비용이 급증함

### 추천 원칙

- publish 가능한 artifact마다 고유 버전이 있어야 한다
- 같은 버전 번호로 서로 다른 artifact를 다시 올리지 않는다
- core/plugin 관계는 dependency range로 호환성을 명시한다
- 버전 결정 규칙은 자동화하되, breaking change 판단은 사람이 책임진다

packaging이 안정적이려면 버전도 설치 계약의 일부로 봐야 한다.

---

## 실무 예시 6: 내부 패키지를 사내 레지스트리에 배포할 때 필요한 최소 규율

사내 공용 Python 패키지를 운영하면 저장소 안에서만 돌던 문제들이 갑자기 조직 문제로 바뀐다.

- 어느 버전을 누가 쓰는지 안 보인다
- 팀마다 wheel을 직접 복사해 쓴다
- 동일 이름 다른 파일이 돌아다닌다
- 한 번 올린 artifact를 덮어써 버린다

이 상태는 시간이 갈수록 위험하다.

### 최소한 필요한 규율

1. **배포 대상 레지스트리를 하나로 정한다**
2. **한 버전은 immutable하게 취급한다**
3. **publish 전에 wheel 설치 테스트를 통과시킨다**
4. **consumer가 볼 수 있는 changelog 또는 release note를 남긴다**
5. **breaking change는 dependency range와 문서에 같이 반영한다**

### 추천 배포 흐름

1. PR에서 lint/test/build 수행
2. `python -m build` 로 sdist/wheel 생성
3. fresh env에서 wheel 설치 및 smoke test
4. 메인 머지 후 태그 기반 publish
5. publish 후 index에서 실제 설치 검증

### 왜 "메인 머지 직후 자동 publish"가 항상 좋은 건 아닌가

내부 유틸 패키지는 사소한 변경도 다수 서비스에 영향을 줄 수 있다.

그래서 아래 둘을 구분하는 편이 좋다.

- 코드 머지 속도
- 배포 artifact 릴리스 속도

즉 모든 merge가 자동 배포로 직결될 필요는 없다.

팀 규모가 커질수록 release cut 기준과 consumer communication이 더 중요해진다.

### 사내 패키지에서 자주 생기는 장애 패턴

- `latest` 감각으로만 의존하다가 예상치 못한 breaking change 유입
- 공용 패키지의 transitive dependency 확대가 운영 이미지 비대화로 이어짐
- wheel 검증 없이 publish해서 설치는 되지만 runtime import가 깨짐

내부 레지스트리라고 방심하면 안 된다.

오히려 조직 내부는 "빠르게 고치면 되지"라는 심리 때문에 규율이 무너지기 쉽다.

---

## 실무 예시 7: wheel-first CI를 도입하면 packaging 문제의 발견 시점이 앞당겨진다

많은 프로젝트가 CI에서 아래 정도만 확인한다.

- unit test
- lint
- type check

물론 필요하다.

하지만 packaging 관점에서는 아직 절반이다.

### 더 안전한 CI 흐름

```yaml
name: package-check

on:
  pull_request:
  push:
    branches: [main]

jobs:
  build-and-test-wheel:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: python -m pip install --upgrade pip build pytest
      - run: python -m build
      - run: python -m venv .venv-wheel
      - run: . .venv-wheel/bin/activate && pip install dist/*.whl && pytest -q
```

이 흐름이 좋은 이유는 단순하다.

- 설치 가능한 artifact를 실제로 만든다
- editable 환경이 숨기던 문제를 잡는다
- entry point, package data, dependency metadata를 함께 검증한다

### 여기에 추가하면 좋은 것

- Python 최소 지원 버전에서의 설치 테스트
- optional extras별 smoke test
- sdist install test
- CLI entry point 실행 test

예를 들어 CLI가 있다면 단순 import만 보지 말고 실제 실행을 본다.

```bash
acme-notify --help
```

plugin entry point가 있다면 discovery까지 확인한다.

```python
from importlib.metadata import entry_points

assert any(ep.group == "acme_notify.exporters" for ep in entry_points())
```

packaging 문제는 늦게 발견될수록 비용이 급격히 커진다.

CI에서 artifact 중심 검증을 넣는 것은 생각보다 큰 효과가 있다.

---

## 실무 예시 8: "작은 내부 도구"가 점점 커질 때 어떤 순서로 packaging을 강화해야 하나

현실의 많은 Python 프로젝트는 처음부터 예쁘게 시작하지 않는다.

보통 이런 흐름이다.

1. 스크립트 하나
2. 스크립트 여러 개
3. 공통 유틸 폴더 추가
4. CLI처럼 쓰기 시작
5. 다른 팀이 가져다 쓰기 시작
6. 배포와 테스트가 꼬이기 시작

이때 한 번에 완벽한 패키지 시스템으로 점프하려 하면 반발이 생긴다.

그래서 진화 순서가 중요하다.

### 단계 1: import 경계 정상화

- `sys.path.append(...)` 제거
- 패키지 디렉터리와 `__init__.py` 정리
- 공식 실행 경로를 `python -m`으로 통일

### 단계 2: `pyproject.toml` 도입

- 프로젝트 이름, 버전, Python 제약, runtime dependency 선언
- build backend 선택
- editable install로 개발 흐름 통일

### 단계 3: entry point와 extras 정리

- CLI 진입점 정의
- 선택 기능별 optional dependency 분리
- core import에서 optional dependency 새지 않게 정리

### 단계 4: wheel-first CI 도입

- build
- fresh install test
- resource/entry point 검증

### 단계 5: 필요 시 distribution 분리

- SDK 분리
- plugin package 분리
- 내부 레지스트리 publish

이 순서를 따르면 조직 저항을 줄이면서도 packaging 품질을 올릴 수 있다.

핵심은 "한 번에 다 바꾸기"가 아니라, **지금 가장 큰 우연 의존성을 제거하는 것**이다.

---

## 디버깅 플레이북: packaging 문제가 터졌을 때 어디부터 봐야 하나

packaging 문제는 에러 메시지가 친절하지 않은 경우가 많다.

그래서 증상별로 보는 순서를 갖고 있으면 좋다.

### 증상 1: 로컬에서는 되는데 CI wheel install 후 import 에러가 난다

우선 의심할 것:

- `src` layout/패키지 포함 규칙 누락
- wheel에 필요한 파일 누락
- editable 환경에서만 보이던 로컬 경로 착시
- package name과 import package 이름 불일치

확인 순서:

1. `dist/*.whl` 설치 후 실제 `site-packages` 구조 확인
2. 누락된 모듈/리소스가 artifact 안에 있는지 확인
3. `pyproject.toml`의 package include 규칙 점검

### 증상 2: `pip install .` 은 되는데 `python -m build` 가 실패한다

우선 의심할 것:

- build isolation에서 필요한 dependency 누락
- backend 설정 누락
- 동적 버전 계산/코드 생성이 로컬 환경에 기대고 있음

확인 순서:

1. `[build-system]` requires 확인
2. 빌드 중 실행되는 훅이 추가 패키지를 필요로 하는지 확인
3. git metadata 의존이나 네트워크 의존 여부 확인

### 증상 3: optional extra를 설치하지 않은 사용자에게 import 에러가 난다

우선 의심할 것:

- core import 단계에서 optional dependency를 가져옴
- `__init__.py` re-export가 무거운 모듈을 끌어옴
- plugin auto-discovery가 eager import를 함

확인 순서:

1. package import만 해도 무슨 모듈이 로드되는지 추적
2. optional 기능을 함수 내부/명시적 factory에서 로드하도록 분리
3. entry point 기반 지연 로딩 가능성 검토

### 증상 4: CLI는 설치됐는데 명령 실행이 다른 Python 환경을 본다

우선 의심할 것:

- 가상환경 활성화 문제
- 다중 Python 설치 경로 충돌
- entry point 생성 위치와 실제 PATH 불일치

확인 순서:

1. `which <command>` 또는 동등한 경로 확인
2. 해당 스크립트의 shebang이 어떤 Python을 가리키는지 확인
3. CI/배포 문서에서 공식 실행 경로를 단일화했는지 점검

### 증상 5: 데이터 파일/템플릿이 배포 후만 사라진다

우선 의심할 것:

- package data include 누락
- resource loading 방식이 소스 트리에 의존함
- wheel과 sdist 포함 규칙 차이

확인 순서:

1. built wheel 내부 파일 목록 확인
2. `importlib.resources` 기반 로딩으로 전환 가능성 검토
3. resource smoke test 추가

packaging 디버깅은 감으로 하면 길어진다.

항상 **editable 환경인지, wheel 설치 환경인지, build isolation 환경인지**를 먼저 구분하자.

---

## 실전 템플릿 1: 재사용 라이브러리용 `pyproject.toml`은 이렇게 생각하면 덜 흔들린다

재사용 가능한 라이브러리는 보통 아래 질문에 답해야 한다.

- 어떤 Python 버전을 지원하는가?
- 어떤 public API를 제공하는가?
- 어떤 optional 기능이 있는가?
- 어떤 의존성 범위까지 호환을 보장하는가?
- 어떤 CLI나 entry point가 있는가?

예시를 보자.

```toml
[build-system]
requires = ["hatchling>=1.26"]
build-backend = "hatchling.build"

[project]
name = "acme-events-sdk"
version = "1.4.0"
description = "Shared SDK for publishing and consuming platform events"
readme = "README.md"
requires-python = ">=3.11"
license = { text = "Proprietary" }
authors = [
  { name = "Platform Team", email = "platform@example.com" }
]
dependencies = [
  "pydantic>=2.8,<3",
  "httpx>=0.28,<0.29",
]

[project.optional-dependencies]
kafka = ["aiokafka>=0.11,<0.12"]
avro = ["fastavro>=1.9,<2"]
cli = ["typer>=0.13,<1"]

[project.scripts]
acme-events = "acme_events_sdk.cli:main"
```

### 여기서 실무적으로 봐야 할 포인트

#### 1) `requires-python`

생각보다 중요하다.

- 지원하지 않는 런타임에 잘못 설치되는 일을 줄여 준다
- resolver가 호환 가능한 버전을 더 빨리 고른다
- 팀 문서보다 메타데이터가 더 신뢰 가능한 기준이 된다

#### 2) dependency range

라이브러리는 downstream 소비자를 생각해야 한다.

그래서 exact pin보다 호환 범위가 기본값이다.

#### 3) optional extra

Kafka를 안 쓰는 소비자에게 `aiokafka`를 강요할 필요는 없다.

이런 분리는 설치 비용과 충돌 위험을 줄인다.

#### 4) 공식 CLI 진입점

SDK가 운영/디버깅용 CLI를 제공한다면 entry point가 유용하다.

예:

- schema validate
- event replay
- payload inspect

### 라이브러리에서 추가로 고려하면 좋은 것

- changelog 정책
- public API surface 문서화
- deprecation 정책
- 최소 지원 버전 테스트
- optional extra 조합 테스트

packaging이 잘된 라이브러리는 설치만 되는 게 아니라, **업그레이드 위험을 예측할 수 있는 라이브러리**다.

---

## 실전 템플릿 2: 애플리케이션용 `pyproject.toml`은 라이브러리와 목표가 달라야 한다

앱은 내가 운영하는 최종 산출물이다.

그래서 라이브러리보다 아래가 더 중요하다.

- 재현 가능한 설치
- 배포 artifact 일관성
- CLI/worker/web 서버 진입점 정리
- lockfile과 이미지 빌드 연동

예시:

```toml
[build-system]
requires = ["setuptools>=69", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "acme-billing-service"
version = "2026.5.4"
description = "Billing API and background jobs"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.115,<1",
  "uvicorn>=0.30,<0.31",
  "sqlalchemy>=2.0,<3",
  "psycopg[binary]>=3.2,<4",
  "pydantic>=2.8,<3",
  "alembic>=1.13,<2",
]

[project.scripts]
acme-billing-api = "acme_billing_service.api.main:main"
acme-billing-worker = "acme_billing_service.worker.main:main"
acme-billing-admin = "acme_billing_service.admin.cli:main"
```

### 앱에서는 왜 여러 entry point가 유용한가

서비스는 보통 단일 프로세스만 있지 않다.

- API 서버
- background worker
- admin task
- one-off backfill CLI

이걸 shell script로만 관리하면 팀 규모가 커질수록 실행 규칙이 흐려진다.

entry point를 명시하면 설치 artifact 수준에서 실행 표준이 생긴다.

### 앱에서 특히 조심할 것

#### 1) 운영에 필요 없는 도구를 runtime dependency에 넣지 않기

앱이라고 해도 아래는 구분하는 편이 좋다.

- 운영 프로세스에 필요한 패키지
- 테스트에만 필요한 패키지
- 개발자 도구 패키지

#### 2) wheel만 만들고 실제 실행은 소스 직접 복사로 하는 이중 체계 피하기

artifact를 만들었다면, 가능한 한 실제 배포도 그 artifact를 기준으로 맞추는 편이 좋다.

그래야 로컬 검증, CI 검증, 운영 배포가 한 방향으로 정렬된다.

#### 3) 앱 버전과 이미지 태그, DB migration, release note를 분리해서 생각하지 않기

배포 단위가 여러 개라면 이 연결이 끊기는 순간 rollback 판단이 어려워진다.

---

## 실전 템플릿 3: plugin 패키지는 core보다 "경계 명시"가 더 중요하다

plugin 패키지는 기능 자체보다 경계 설계가 중요하다.

예시를 보자.

```toml
[build-system]
requires = ["hatchling>=1.26"]
build-backend = "hatchling.build"

[project]
name = "acme-storage-s3"
version = "0.7.0"
requires-python = ">=3.11"
dependencies = [
  "acme-storage-core>=2.3,<3",
  "boto3>=1.35,<2",
]

[project.entry-points."acme_storage.backends"]
s3 = "acme_storage_s3.backend:S3Backend"
```

### plugin package에서 중요한 것

#### 1) core dependency range

plugin은 core와의 호환 범위를 메타데이터로 보여 줘야 한다.

문서에만 써 두면 늦다.

#### 2) 구현체 import 비용

S3, GCS, Azure, Snowflake 같은 backend는 의존성이 무겁다.

core import 단계에서 다 끌어오지 않게 해야 한다.

#### 3) 오류 경계

plugin 하나가 망가져도 전체 애플리케이션 부팅이 다 깨질지, 아니면 해당 plugin만 비활성화할지 정책이 있어야 한다.

이건 packaging 바깥의 런타임 정책 같아 보여도, 실제로는 dependency/entry point 설계와 직접 연결된다.

---

## 핵심 개념 11: supply chain 관점에서 packaging은 보안 문제이기도 하다

보안 이야기를 하면 흔히 취약점 스캔만 떠올리기 쉽다.

하지만 packaging은 그 이전 단계에서 이미 보안 표면을 만든다.

### packaging이 보안에 영향을 주는 지점

- 어떤 index에서 패키지를 설치하는가
- transitive dependency가 얼마나 넓게 열려 있는가
- build 시점에 외부 네트워크에 무엇을 의존하는가
- setup/build hook가 어떤 코드를 실행하는가
- 내부 패키지 이름이 공용 생태계와 충돌하지 않는가

### 실무에서 최소한 챙길 것

#### 1) 의존성 출처를 통제한다

사내 미러나 허용된 index 경로를 분명히 두지 않으면, 팀마다 다른 출처를 보게 된다.

#### 2) build가 불필요하게 네트워크에 기대지 않게 한다

빌드 시 외부에 붙어 generated file을 만들거나 version을 계산하는 구조는 재현성과 보안을 둘 다 해칠 수 있다.

#### 3) 내부 패키지 이름 전략을 정한다

너무 일반적인 이름은 혼란을 만든다.

예:

- `common-utils`
- `internal-tools`
- `shared`

이런 이름은 목적도 불분명하고 충돌 위험도 크다.

패키지 이름은 소유권과 도메인을 드러내는 편이 낫다.

#### 4) publish 권한과 artifact immutability를 운영한다

같은 버전 재업로드가 가능한 환경은 사고가 나기 쉽다.

"누가 언제 어떤 wheel을 올렸는가"를 추적 가능하게 만들어야 한다.

packaging discipline은 보안팀만의 관심사가 아니다.

실제로는 개발팀이 공급망 표면을 어디까지 줄이느냐의 문제다.

---

## 핵심 개념 12: 테스트 전략도 packaging-aware해야 한다

테스트가 많아도 packaging 문제가 계속 터지는 팀이 있다.

대개 테스트가 코드 로직만 보고, 설치 형태를 안 보기 때문이다.

### packaging-aware 테스트가 필요한 이유

- import 가능성과 실행 가능성은 다르다
- editable install과 wheel install의 동작이 다를 수 있다
- optional extras, entry point, resource file은 단순 unit test로 안 잡힐 수 있다

### 어떤 테스트가 유용한가

#### 1) wheel smoke test

- fresh venv 생성
- built wheel 설치
- 핵심 import 확인
- CLI `--help` 실행

#### 2) optional extra test

- `pip install .[postgres]`
- `pip install .[cli]`
- 각 extra 관련 기능 smoke test

#### 3) resource test

- 템플릿/SQL/schema 파일 실제 읽기
- wheel 내부 path에서도 동작하는지 확인

#### 4) 최소 지원 Python 버전 test

많은 팀이 최신 Python에서만 테스트하고, metadata에는 `>=3.10` 같은 넓은 범위를 써 둔다.

그러면 소비자는 믿고 설치했다가 런타임에서 깨질 수 있다.

### 추천 사고방식

패키지 테스트는 "함수가 맞게 동작하나"만 보는 게 아니라, **설치된 사용자가 실제로 어떤 경험을 하는가**를 확인해야 한다.

---

## 추가 함정 1: 패키지 이름과 import 이름이 다를 때 그 차이를 팀이 이해하지 못한다

Python packaging에서는 distribution 이름과 import package 이름이 항상 같을 필요는 없다.

하지만 팀이 이 차이를 이해하지 못하면 혼란이 생긴다.

예:

- 배포 이름: `acme-billing-service`
- import 이름: `acme_billing_service`

이건 자연스러운 패턴이다.

문제는 문서와 코드, 운영 스크립트가 이 차이를 섞어 쓰는 순간 생긴다.

그래서 아래를 명확히 해야 한다.

- 설치할 때 쓰는 이름
- import할 때 쓰는 이름
- CLI로 실행할 때 쓰는 이름

이 셋을 팀 문서와 README에 일관되게 보여 주자.

---

## 추가 함정 2: 패키지 경계보다 저장소 경계를 먼저 믿는다

저장소를 분리했다고 패키지 경계가 생기는 건 아니다.

반대로 같은 저장소 안에 있어도 packaging contract가 명확하면 꽤 잘 운영된다.

중요한 것은 저장소 개수가 아니라 아래다.

- install 가능한가
- 버전이 있는가
- dependency contract가 있는가
- entry point가 정리되어 있는가
- consumer가 artifact 기준으로 사용할 수 있는가

repo split은 packaging의 대체물이 아니다.

---

## 추가 함정 3: public API와 internal module을 같은 안정성으로 취급하지 않는다

packaging을 하면 자연스럽게 노출 표면이 생긴다.

그런데 아래가 섞이면 버전 관리가 어려워진다.

- public import path
- 내부 구현 모듈
- 편의 re-export

예를 들어 소비자가 `from acme_sdk.internal.http.session import Session` 같은 식으로 import하기 시작하면, 사실상 internal이 public처럼 굳어 버린다.

그래서 초기부터 아래를 분리하는 편이 좋다.

- 공식 public API 경로
- 내부 모듈 경로
- deprecated 예정 경로

packaging은 설치 계약일 뿐 아니라 **API 노출 계약**이기도 하다.

---

## 추가 함정 4: README와 메타데이터를 publish artifact의 일부로 보지 않는다

많은 팀이 README를 문서 파일 정도로만 본다.

하지만 배포된 패키지 입장에서는 README도 소비자가 보는 인터페이스다.

README에는 최소한 아래가 있어야 한다.

- 설치 방법
- 기본 import 예시
- optional extras 설명
- CLI 사용 예시
- 지원 Python 버전
- breaking change 또는 migration note 링크

문서가 빈약하면 소비자는 package metadata를 읽어도 실제 사용법을 알기 어렵다.

좋은 packaging은 좋은 README와 같이 간다.

---

## 추가 함정 5: release 이후 consumer upgrade path를 설계하지 않는다

패키지를 publish하는 것과 소비자가 안전하게 upgrade하는 것은 다른 문제다.

자주 보는 문제:

- 버전만 올리고 변경 영향 설명 없음
- deprecation 없이 import path 제거
- optional extra 구조를 바꿨는데 migration guide 없음
- plugin entry point 이름을 바꿨는데 공지 없음

packaging이 성숙한 팀은 publish만 하지 않는다.

아래도 같이 한다.

- changelog
- migration note
- breaking change 알림
- consumer test window 확보

특히 내부 공용 라이브러리는 consumer가 같은 조직 안에 있다고 해서 자동으로 잘 따라오지 않는다.

오히려 내부라서 문서화가 더 잘 안 되는 경우가 많다.

---

## 실무 의사결정 프레임: 지금 내 프로젝트에 어떤 packaging 강도가 필요한가

여기까지 보면 모든 프로젝트가 다 enterprise-grade packaging discipline을 가져야 할 것처럼 보일 수 있다.

현실은 조금 다르다.

프로젝트 성격에 따라 필요한 강도가 다르다.

### 질문 1: 이 코드를 누가 소비하는가

- 나 혼자만 쓴다
- 같은 팀 여러 사람이 쓴다
- 다른 저장소/다른 팀이 가져간다
- 사내 공용 표준처럼 쓰인다

소비자가 늘어날수록 packaging의 명시성이 중요해진다.

### 질문 2: 실행 환경이 몇 개인가

- 로컬 스크립트 한 군데
- CI + 개발 환경
- Docker + worker + cron + 서버리스
- 온프레미스/클라우드/배치 등 여러 표면

실행 표면이 늘어날수록 editable 착시를 줄여야 한다.

### 질문 3: release cadence와 영향 범위가 어떤가

- 하루짜리 분석 스크립트
- 분기별로만 손대는 내부 도구
- 매주 배포되는 서비스
- 여러 팀이 얽힌 공용 SDK

release 빈도와 영향 범위가 클수록 artifact 검증과 버전 규율이 중요해진다.

### 질문 4: optional feature와 plugin이 있는가

- 없다
- dev-only 수준으로 있다
- 고객/팀별 확장이 필요하다
- third-party connector 생태계가 있다

확장성이 클수록 entry point와 extras 설계가 핵심이 된다.

### 간단한 판단 기준

#### Level 1: 개인/단기 스크립트

필수만:

- 최소한의 `pyproject.toml`
- 공식 실행 경로 정리
- 경로 땜질 금지

#### Level 2: 팀 내부 도구/서비스

추가 권장:

- editable install 표준화
- wheel build 검증
- runtime/dev dependency 분리
- entry point 정리

#### Level 3: 공용 라이브러리/다중 소비자 패키지

강하게 권장:

- `src` layout 검토
- wheel/sdist/fresh install test
- optional extras 설계
- changelog/migration note
- 내부 레지스트리/immutable publish 규율

#### Level 4: plugin 플랫폼/조직 표준 SDK

거의 필수:

- entry point 기반 discovery
- consumer compatibility 정책
- 버전/릴리스 관리 자동화
- 최소 지원 버전 matrix test
- supply chain/registry 통제

프로젝트에 맞는 강도를 고르는 것이 중요하다.

하지만 Level 3 이상인데 Level 1 규율로 버티면, 언젠가 크게 깨진다.

---

## 30일 정비 플랜: 이미 엉켜 있는 Python 프로젝트를 packaging 친화적으로 바꾸는 순서

이미 운영 중인 프로젝트는 "처음부터 제대로" 할 수 없다.

그래서 리팩터링 순서가 중요하다.

### 1주차: 가시화

- 현재 실행 경로 목록 수집
- `requirements.txt`, `setup.py`, `pyproject.toml`, Dockerfile, CI 설정 관계 정리
- 어떤 명령이 공식 경로인지 문서화
- `sys.path.append`, `PYTHONPATH` 의존 지점 찾기

이 단계의 목표는 해결이 아니라 **현실 파악**이다.

### 2주차: 최소 계약 정리

- `pyproject.toml` 기준 메타데이터 정리
- runtime dependency와 dev dependency 분리
- `python -m` 또는 entry point 기준 실행 경로 통일
- editable install 개발 흐름 표준화

이 시점부터 로컬 개발 경험이 조금 바뀔 수 있다.

중요한 건 모두가 같은 방식으로 실행하게 만드는 것이다.

### 3주차: artifact 검증 추가

- CI에 `python -m build` 추가
- fresh venv wheel install smoke test 추가
- resource file/CLI entry point 테스트 추가
- 최소 한 환경에서 optional extra smoke test 추가

이 단계에서 보통 숨겨진 packaging 문제가 한 번에 많이 드러난다.

그게 정상이다.

오히려 지금 잡는 편이 훨씬 싸다.

### 4주차: 배포/소비자 경계 정리

- 내부 공용 모듈은 패키지 분리 필요성 검토
- 사내 레지스트리 publish 규칙 수립
- changelog/migration note 기본 양식 정리
- 버전 정책과 release cut 기준 합의

### 이 플랜의 핵심

한 달 안에 모든 걸 완벽히 하자는 뜻이 아니다.

목표는 아래다.

- 우연한 로컬 성공을 줄인다
- 설치 가능한 계약을 만든다
- 배포 artifact를 검증 가능하게 만든다
- 소비자 관점으로 프로젝트를 다시 보게 만든다

packaging 개선은 코드 예쁘게 만들기보다, **운영 놀람을 줄이는 작업**에 가깝다.

---

## 흔한 실수 1: `requirements.txt`를 project metadata로 착각한다

`requirements.txt`는 여전히 유용하다.

하지만 그 역할은 보통 다음에 가깝다.

- 특정 환경 설치 입력
- lock 결과물 또는 export 결과물
- 배포 파이프라인 보조 파일

프로젝트의 정체성을 설명하는 파일은 아니다.

아래 정보는 `requirements.txt`만으로 충분히 표현되지 않는다.

- 프로젝트 이름
- Python 버전 제약
- entry point
- optional extras
- build backend
- README/metadata

그래서 modern project에서는 `requirements.txt`가 있더라도, **그 위에 `pyproject.toml`이 있어야 한다**고 보는 편이 안전하다.

---

## 흔한 실수 2: editable install이 통과하니 packaging도 끝났다고 생각한다

이건 정말 자주 본다.

editable install은 개발 경험을 좋게 하지만, 아래를 완전히 검증하지는 않는다.

- wheel에 파일이 다 들어갔는지
- entry point가 의도대로 생성되는지
- resource loading이 설치 artifact에서도 안정적인지
- 빌드 격리 환경에서 dependency가 충분한지

개발과 배포의 검증 축을 분리해야 한다.

- 개발 축: editable install + 빠른 테스트
- 배포 축: wheel/sdist build + fresh env install test

이 두 축을 같이 굴려야 한다.

---

## 흔한 실수 3: dev dependency를 runtime dependency에 다 넣어 버린다

초기에는 편해 보인다.

```toml
[project]
dependencies = [
  "pytest",
  "ruff",
  "mypy",
  "httpx",
  "pydantic",
]
```

하지만 이건 runtime 설치를 오염시킨다.

문제점:

- 운영 이미지가 불필요하게 비대해짐
- 보안 스캔 노이즈 증가
- 실제 애플리케이션 의존성 경계가 흐려짐
- downstream 소비자가 쓸데없는 도구를 같이 깔게 됨

dev/test/tooling은 배포 metadata와 구분해야 한다.

---

## 흔한 실수 4: package data를 소스 파일 옆에 두면 자동으로 포함된다고 믿는다

실제로는 backend별 포함 규칙이 있고, wheel/sdist 동작도 다를 수 있다.

소스 트리에서 파일이 보인다는 사실과 설치 artifact에 포함된다는 사실은 다르다.

반드시 확인해야 한다.

- 어떤 파일이 패키지 일부인가
- 어떤 파일이 빌드 산출물에 포함되는가
- 코드가 설치 후 그 파일을 어떻게 찾는가

이걸 빼먹으면 배포 후 템플릿 누락, SQL 파일 누락, schema 누락이 반복된다.

---

## 흔한 실수 5: optional dependency를 선언해 놓고 core import에서 이미 가져온다

예를 들어 PostgreSQL 지원을 optional로 뒀다고 하자.

그런데 package import 시점에 아래가 실행되면 의미가 없다.

```python
import psycopg
```

이러면 `pip install mypkg`만 한 사용자도 import 단계에서 깨질 수 있다.

optional dependency는 metadata만 optional이어서는 안 된다.

- import 경계
- 기능 경계
- 초기화 시점

이 셋도 같이 optional이어야 한다.

---

## 흔한 실수 6: 버전을 코드 상수와 메타데이터에 이중 관리한다

이것도 은근 자주 깨진다.

- `pyproject.toml`의 `version = "0.8.0"`
- `__init__.py`의 `__version__ = "0.7.9"`

둘 중 하나가 어긋나는 순간 혼란이 시작된다.

가능하면 단일 소스 전략을 택하자.

- 빌드 메타데이터에서 버전 관리
- 런타임에서 필요하면 `importlib.metadata.version("package-name")` 사용
- 혹은 backend가 지원하는 동적 버전 전략을 일관되게 사용

핵심은 **버전 진실 소스를 하나로 유지하는 것**이다.

---

## 흔한 실수 7: tool migration 자체를 목표로 삼는다

setuptools에서 hatchling으로, Poetry에서 다른 도구로, 혹은 uv로 옮기는 작업은 종종 실제 문제보다 더 큰 관심을 끈다.

하지만 도구 마이그레이션은 목표가 아니라 수단이다.

다음 질문이 먼저다.

- 현재 무엇이 실제로 문제인가?
- build 속도인가?
- metadata 중복인가?
- dependency resolver 체감 속도인가?
- publish 파이프라인 호환성인가?
- 팀 onboarding 비용인가?

문제 정의 없이 도구를 바꾸면, 파일 확장자만 바뀌고 혼란은 그대로 남는다.

---

## 트레이드오프: packaging을 엄격하게 설계할수록 초기 진입 비용은 오른다

여기까지 읽으면 packaging discipline이 무조건 많을수록 좋아 보일 수 있다.

하지만 비용도 있다.

### 엄격한 packaging의 장점

- 로컬/CI/운영 차이 감소
- reusable package 구조 강화
- entry point와 plugin 확장성 향상
- artifact 기반 배포 검증 가능
- dependency 책임 구분 명확

### 엄격한 packaging의 비용

- 초기에 구조를 더 생각해야 함
- 작은 스크립트 프로젝트에는 과할 수 있음
- 팀이 build backend와 installer 역할을 이해해야 함
- CI 단계가 하나 더 늘어날 수 있음

### 그래서 어떻게 판단할까

아래 질문에 "예"가 많을수록 엄격한 packaging 가치가 높다.

- 다른 팀이나 저장소가 재사용하는가?
- 컨테이너/서버리스/배치 등 실행 환경이 여러 개인가?
- CLI나 plugin 확장이 필요한가?
- 운영 배포 사고를 줄이는 게 중요한가?
- 내부 라이브러리 생태계를 만들고 있는가?

반대로 단발성 스크립트라면 과한 ceremony는 줄여도 된다.

핵심은 완벽주의가 아니라 **경계의 명확성**이다.

---

## 바로 적용 가능한 설계 패턴

### 패턴 1: 서비스 앱

추천:

- `pyproject.toml`을 진실 소스로 둔다
- lockfile로 배포 그래프를 고정한다
- 가능하면 wheel 설치 기준 테스트를 둔다
- 운영 진입점은 entry point 또는 `python -m`으로 일관화한다

### 패턴 2: 공용 라이브러리

추천:

- `src` layout 사용 검토
- dependency는 호환 범위로 선언
- optional extras를 기능 경계에 맞게 분리
- package data 포함 규칙을 명시
- 최소/최대 호환 범위 테스트 전략을 준비

### 패턴 3: plugin 플랫폼

추천:

- entry point 기반 discovery
- core contract 최소화
- plugin별 optional dependency 격리
- startup 시 전체 import 대신 필요한 시점 로딩

### 패턴 4: monorepo 내부 공용 모듈

추천:

- 경로 append 대신 설치 가능한 패키지로 전환
- editable install 또는 내부 registry 기반 소비
- distribution 경계와 소유권을 명확화

---

## 자주 받는 질문에 대한 짧은 답

### Q1. 작은 서비스인데도 wheel build 검증이 꼭 필요할까?

작은 서비스라면 처음부터 무겁게 갈 필요는 없다.

하지만 아래 중 하나라도 해당하면 wheel 검증을 넣는 편이 좋다.

- Docker 배포를 한다
- CLI/worker가 있다
- 템플릿/SQL/resource 파일이 있다
- 팀원이 둘 이상이다

작은 비용으로 큰 놀람을 줄일 수 있다.

### Q2. `src` layout이 귀찮은데 flat layout으로도 잘할 수 없나?

할 수 있다.

다만 그 경우 더 강한 규율이 필요하다.

- 항상 editable install 기준으로 개발하기
- working directory 의존 실행을 피하기
- wheel install 테스트로 착시를 잡기

즉 flat layout 자체가 문제라기보다, **flat layout의 착시를 통제할 자신이 있는가**가 질문이다.

### Q3. library에도 lockfile을 커밋해야 하나?

개발/CI 재현용으로는 유용할 수 있다.

하지만 그 lockfile이 곧 소비자 계약은 아니다.

라이브러리는 여전히 메타데이터에서 호환 범위를 선언해야 하고, lockfile은 내부 검증 도구로 보는 편이 안전하다.

### Q4. 내부 패키지는 굳이 버전을 엄격하게 관리하지 않아도 되지 않나?

짧게 말하면 아니다.

내부 패키지는 외부보다 더 빨리 퍼지고, 깨졌을 때 책임 경로가 흐려지기 쉽다.

내부일수록 버전, changelog, publish immutability가 더 중요해진다.

### Q5. packaging을 잘하면 import 문제도 사라지나?

전부는 아니다.

순환 import나 side effect 같은 구조 문제는 여전히 따로 봐야 한다.

다만 packaging을 바로 세우면 적어도 다음은 훨씬 줄어든다.

- 경로 착시
- 로컬만 되는 실행 방식
- artifact 누락
- 환경별 설치 불일치

즉 packaging은 모든 문제의 해답은 아니지만, 많은 문제의 바닥을 평평하게 만들어 준다.

---

## 실무 체크리스트

### 메타데이터/구조

- [ ] `pyproject.toml`이 build contract의 단일 진실 소스인가?
- [ ] 패키지 이름, Python 버전 제약, runtime dependency가 명확한가?
- [ ] `src` layout이 필요한 규모인지 검토했는가?
- [ ] 버전 진실 소스가 하나인가?

### 의존성

- [ ] 앱과 라이브러리의 dependency 전략을 구분했는가?
- [ ] runtime/development/test dependency가 섞여 있지 않은가?
- [ ] optional dependency가 실제 import 경계와도 분리되어 있는가?
- [ ] lockfile의 역할과 metadata의 역할을 구분하고 있는가?

### 실행/확장

- [ ] 공식 실행 진입점이 `python -m` 또는 entry point로 정리되어 있는가?
- [ ] CLI가 있다면 `project.scripts`를 통해 설치 후 실행이 가능한가?
- [ ] plugin 구조가 있다면 import side effect 대신 entry point 또는 명시적 registry를 쓰는가?

### artifact 검증

- [ ] CI에서 wheel을 실제로 빌드하는가?
- [ ] fresh environment에서 built wheel 설치 테스트를 하는가?
- [ ] 템플릿/SQL/정적 파일이 wheel과 sdist에 포함되는가?
- [ ] editable install이 감추는 문제를 별도 검증하는가?

### 운영/배포

- [ ] Docker/runtime 이미지가 가능하면 설치 artifact 기준으로 움직이는가?
- [ ] 사내 공용 패키지 배포 경로가 명확한가?
- [ ] 경로 땜질(`PYTHONPATH`, `sys.path.append`) 없이도 실행되는가?

---

## 한 줄 정리 전에 꼭 남기고 싶은 실무 감각 하나

나는 Python packaging을 잘하는 팀의 특징이 꽤 분명하다고 느낀다.

그 팀들은 packaging을 배포 직전 체크리스트로 보지 않는다.

대신 아래처럼 본다.

- import 경계 정리 도구
- 실행 방식 표준화 도구
- 재사용 가능한 모듈 설계 도구
- 배포 artifact 검증 도구
- 운영 재현성 확보 도구

이 관점이 생기면 `pip install -e .`가 왜 중요한지, 왜 그걸로 충분하지 않은지, 왜 `pyproject.toml`과 lockfile을 구분해야 하는지, 왜 entry point가 단순 편의 기능이 아닌지가 한 번에 연결된다.

결국 packaging은 Python 프로젝트의 "마지막 포장"이 아니다.

**그 프로젝트가 어떤 경계로 설치되고 실행되고 확장될지를 미리 결정하는 아키텍처 선택**이다.

그리고 이 선택을 초기에 정리해 둘수록, 나중에 팀이 커지고 실행 환경이 늘어나도 경로 땜질 대신 계약을 중심으로 움직일 수 있다.

---

## 한 줄 정리

> Python packaging의 본질은 `pyproject.toml` 하나 잘 쓰는 데 있지 않고, **코드·의존성·artifact·실행 경로를 설치 가능한 계약으로 맞춰 로컬의 우연을 운영의 재현성으로 바꾸는 데** 있다.
