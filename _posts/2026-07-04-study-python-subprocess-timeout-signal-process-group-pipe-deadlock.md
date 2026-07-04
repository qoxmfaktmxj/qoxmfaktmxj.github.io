---
layout: post
title: "Python subprocess 운영 설계: Timeout, Signal, Process Group, Pipe Deadlock으로 외부 프로세스를 안전하게 다루는 법"
date: 2026-07-04 11:50:00 +0900
categories: [python]
tags: [study, python, subprocess, timeout, signal, process-group, pipe, deadlock, child-process, backend, reliability, operations]
permalink: /python/2026/07/04/study-python-subprocess-timeout-signal-process-group-pipe-deadlock.html
---

## 배경: subprocess는 "명령 하나 실행"이 아니라 작은 운영 경계를 여는 일이다

Python 서비스에서 외부 명령을 실행해야 하는 순간은 생각보다 자주 온다.

- 이미지 변환을 위해 `ffmpeg`를 호출한다
- PDF 생성이나 최적화를 위해 `wkhtmltopdf`, `ghostscript`, `qpdf`를 실행한다
- 백업, 압축, 암호화, 해시 계산을 위해 OS 도구를 쓴다
- 레거시 바이너리나 사내 CLI를 감싸 API로 제공한다
- 데이터 파이프라인에서 `psql`, `mysql`, `aws`, `gcloud`, `kubectl` 같은 도구를 호출한다
- 테스트 자동화에서 child process를 띄워 fixture server나 worker를 검증한다

처음에는 단순하다.

```python
import subprocess

result = subprocess.run(["convert", "input.png", "output.webp"])
```

하지만 운영 환경에서 subprocess는 단순 함수 호출이 아니다. Python 프로세스 바깥에 별도의 실행 주체를 만들고, 그 프로세스가 CPU, 메모리, 파일 디스크립터, pipe buffer, signal, working directory, environment, 권한, stdout/stderr를 따로 가진다. 즉 외부 명령을 한 줄 실행하는 순간 작은 운영 경계가 생긴다.

이 경계를 대충 다루면 장애는 꽤 거칠게 나타난다.

- 명령이 멈췄는데 timeout이 없어 web worker가 계속 점유된다
- timeout은 걸었지만 child process의 grandchild가 살아남아 CPU를 계속 쓴다
- stdout을 pipe로 열어 놓고 읽지 않아 pipe buffer가 차면서 프로세스가 교착된다
- `shell=True`로 사용자 입력을 붙였다가 command injection 위험이 생긴다
- stderr를 버려 장애 원인을 알 수 없다
- 큰 출력을 `capture_output=True`로 메모리에 모두 올려 OOM에 가까워진다
- 프로세스 종료 시 SIGTERM, SIGKILL 순서를 구분하지 않아 정리 기회를 주지 못한다
- 현재 프로세스의 환경변수와 working directory를 그대로 넘겨 재현성이 깨진다
- 실패 exit code를 무시해 실제 작업은 실패했는데 API는 성공을 반환한다

오늘 글은 `subprocess.run()` 사용법 요약이 아니다. 중급 이상 Python 개발자가 운영 코드에서 외부 프로세스를 안전하게 감싸기 위해 정해야 하는 기준을 정리한다.

이번 글에서 다룰 질문은 아래와 같다.

1. `run()`, `Popen()`, `asyncio.create_subprocess_exec()`는 각각 언제 써야 하는가
2. timeout은 왜 `timeout=` 하나로 끝나지 않는가
3. process group과 session을 왜 고려해야 하는가
4. pipe deadlock은 어떤 조건에서 생기며 어떻게 피해야 하는가
5. stdout/stderr, exit code, signal 종료를 어떻게 관측 가능한 결과로 바꿔야 하는가
6. shell, environment, working directory, 임시 파일을 어떻게 제한해야 하는가
7. 서비스, worker, batch에서 subprocess wrapper를 어떤 형태로 표준화해야 하는가

핵심 결론부터 말하면 이렇다.

**subprocess 운영 설계의 핵심은 명령 실행을 편하게 만드는 것이 아니라, 외부 프로세스의 생명주기와 자원 사용을 Python 코드의 책임 범위 안으로 다시 끌고 오는 것이다.**

외부 프로세스는 Python 예외 모델 밖에서 실패한다. 그래서 좋은 wrapper는 단순히 `subprocess.run()`을 감싸는 함수가 아니라, timeout, 종료, 출력 수집, 로그, 재시도 가능성, 보안 경계를 한 곳에서 일관되게 결정하는 작은 실행 컨테이너에 가깝다.

---

## 먼저 큰 그림: subprocess는 세 단계로 봐야 한다

외부 명령 실행은 보통 아래 세 단계로 나눌 수 있다.

1. 시작: 어떤 바이너리를 어떤 인자, 환경, 디렉터리, 권한으로 실행할 것인가
2. 실행 중: stdout/stderr를 어떻게 읽고, timeout과 취소를 어떻게 처리할 것인가
3. 종료: exit code, signal, 출력, 임시 파일, child tree를 어떻게 정리하고 해석할 것인가

초기 코드는 시작 단계에만 집중한다.

```python
subprocess.run(["ffmpeg", "-i", src, dst], check=True)
```

이 코드는 간결하지만 운영 질문에는 답하지 않는다.

- `ffmpeg`가 10분 동안 멈추면 어떻게 되는가
- 출력이 많으면 pipe가 막히지 않는가
- 실패 시 stderr는 어디에 남는가
- API 요청 취소나 worker shutdown이 오면 child process도 같이 멈추는가
- `ffmpeg`가 내부에서 추가 프로세스를 띄우면 그 프로세스도 종료되는가
- 입력 파일과 출력 파일이 같은 디스크에 있고, 중간 파일이 남으면 어떻게 치울 것인가

따라서 실무에서는 "명령 실행 코드"를 호출부마다 흩뿌리기보다, 작은 표준 wrapper를 두는 편이 안정적이다. wrapper는 팀의 실행 정책을 담는다.

- 기본 timeout
- 최대 출력 크기
- stdout/stderr 수집 방식
- process group 종료 방식
- 허용할 environment
- 실패 예외 타입
- 로깅 필드
- metric label
- 테스트 fake 주입 방식

핵심은 모든 명령을 같은 방식으로 실행하자는 뜻이 아니다. 오히려 명령마다 위험이 다르기 때문에 공통 기본값을 두고, 예외가 필요한 곳만 명시적으로 열어야 한다.

---

## 핵심 개념 1: `run()`은 짧고 출력이 제한된 동기 작업에만 기본값으로 적합하다

`subprocess.run()`은 가장 쓰기 쉬운 API다. 프로세스를 시작하고, 끝날 때까지 기다리고, 결과를 `CompletedProcess`로 돌려준다.

```python
from subprocess import run

completed = run(
    ["python", "--version"],
    text=True,
    capture_output=True,
    timeout=3,
    check=True,
)
```

이 코드는 아래 조건에서는 충분히 좋다.

- 명령이 짧게 끝난다
- 출력 크기가 작다
- child process tree가 복잡하지 않다
- streaming 로그가 필요 없다
- 실행 중 중간 제어가 필요 없다
- 동기 worker thread를 점유해도 괜찮다

하지만 `run()`은 본질적으로 "시작하고 끝날 때까지 기다리는" API다. 실행 중 제어가 필요해지면 금방 한계가 온다.

예를 들어 아래 작업은 `run()`만으로는 설계가 부족하다.

- 5분 이상 걸릴 수 있는 동영상 변환
- stdout을 실시간으로 읽어 progress를 기록해야 하는 CLI
- stdout은 파일로 보내고 stderr만 tail해야 하는 작업
- timeout 시 child process group 전체를 단계적으로 종료해야 하는 작업
- web request 취소나 worker shutdown signal과 연결해야 하는 작업
- 동시에 여러 child process를 제한된 개수로 운영해야 하는 작업

이런 경우에는 `Popen()` 또는 `asyncio.create_subprocess_exec()`로 내려가야 한다.

```python
import subprocess

proc = subprocess.Popen(
    ["ffmpeg", "-i", "input.mp4", "output.webm"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
)

stdout, stderr = proc.communicate(timeout=30)
if proc.returncode != 0:
    raise RuntimeError(stderr[-2000:])
```

`Popen()`은 번거롭다. 하지만 그 번거로움은 외부 프로세스의 생명주기를 직접 소유하기 위한 비용이다.

### `check=True`는 필수에 가깝다

`subprocess.run()`의 기본값은 exit code가 0이 아니어도 예외를 던지지 않는다.

```python
result = subprocess.run(["grep", "needle", "file.txt"])
print(result.returncode)
```

이건 CLI 스크립트에서는 괜찮을 수 있지만 서비스 코드에서는 위험하다. 실패를 성공 경로처럼 계속 진행하기 쉽다. 대부분의 작업형 명령에서는 `check=True` 또는 명시적인 return code 검사가 필요하다.

```python
result = subprocess.run(
    ["qpdf", "--check", path],
    text=True,
    capture_output=True,
    timeout=10,
)

if result.returncode != 0:
    raise DocumentValidationError(
        f"qpdf validation failed: {result.stderr[-2000:]}"
    )
```

단, exit code의 의미가 명령마다 다를 수 있다는 점은 조심해야 한다. 예를 들어 `grep`은 매칭 없음도 1로 표현한다. 이 경우 `check=True`를 무조건 쓰기보다 허용 가능한 return code를 명시하는 편이 낫다.

```python
result = subprocess.run(
    ["grep", "-q", pattern, path],
    timeout=3,
)

if result.returncode not in (0, 1):
    raise RuntimeError(f"grep failed: {result.returncode}")

matched = result.returncode == 0
```

즉 핵심은 `check=True` 자체가 아니라 **exit code를 호출부의 비즈니스 의미로 번역하는 것**이다.

---

## 핵심 개념 2: timeout은 프로세스 하나가 아니라 작업 전체의 시간 예산이다

`subprocess.run(..., timeout=10)`은 좋은 출발점이다. 하지만 운영 관점에서는 충분하지 않을 때가 많다.

```python
subprocess.run(["ffmpeg", "-i", src, dst], timeout=10, check=True)
```

이 코드는 10초 후 `TimeoutExpired`를 발생시킨다. 그러나 고려할 것이 남아 있다.

- timeout 발생 시 child process가 확실히 종료되었는가
- child가 다시 child를 만들었다면 grandchild도 종료되었는가
- timeout 전에 생성한 부분 출력 파일은 삭제되었는가
- timeout은 사용자가 기다릴 수 있는 시간과 worker가 점유될 수 있는 시간을 모두 반영하는가
- retry를 붙이면 전체 시간 예산이 몇 초까지 늘어나는가

실무에서 timeout은 개별 함수 옵션이 아니라 **작업 전체의 시간 예산**으로 봐야 한다. 예를 들어 PDF 변환 API가 15초 안에 응답해야 한다면, 다운로드 3초, 변환 8초, 업로드 3초, 정리 1초처럼 나눠야 한다. subprocess에만 15초를 주면 전체 요청은 쉽게 20초를 넘는다.

```python
from time import monotonic


class Deadline:
    def __init__(self, seconds: float) -> None:
        self.expires_at = monotonic() + seconds

    def remaining(self) -> float:
        return max(0.1, self.expires_at - monotonic())


deadline = Deadline(15)

download_input(timeout=deadline.remaining())
run_converter(timeout=deadline.remaining())
upload_output(timeout=deadline.remaining())
```

이 방식의 장점은 timeout이 흩어지지 않는다는 점이다. 각 단계가 전체 요청 예산 안에서만 실행된다.

### timeout 후 종료는 단계적으로 설계해야 한다

장시간 작업을 안전하게 멈추려면 보통 두 단계가 필요하다.

1. SIGTERM으로 정상 종료 기회를 준다
2. grace period 후에도 살아 있으면 SIGKILL로 강제 종료한다

`subprocess.run(timeout=...)`은 편하지만 이런 세밀한 종료 정책을 표현하기 어렵다. `Popen()`을 쓰면 직접 제어할 수 있다.

```python
import os
import signal
import subprocess
import time


def terminate_process_group(proc: subprocess.Popen[bytes], grace: float) -> None:
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return

    deadline = time.monotonic() + grace
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            return
        time.sleep(0.05)

    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
```

여기서 `killpg()`를 쓰는 이유는 프로세스 하나가 아니라 같은 process group 전체를 종료하기 위해서다. 이 주제는 다음 절에서 더 본다.

---

## 핵심 개념 3: process group을 만들지 않으면 grandchild가 살아남을 수 있다

많은 CLI는 내부에서 또 다른 프로세스를 띄운다.

- shell script가 여러 명령을 실행한다
- `ffmpeg` wrapper가 worker process를 만든다
- 테스트 서버가 watcher나 compiler process를 띄운다
- `npm`, `pnpm`, `pytest`, `java` 기반 도구가 child를 더 만든다

이때 Python이 직접 시작한 process만 죽이면 그 아래 grandchild가 살아남을 수 있다. 운영에서 가장 짜증나는 유형의 누수다. API 요청은 실패했는데 CPU를 먹는 프로세스가 남거나, 임시 포트를 계속 점유하거나, lock file을 붙잡고 있는 식이다.

Unix 계열에서는 새 session 또는 process group을 만들어 실행하는 방식이 흔하다.

```python
import subprocess

proc = subprocess.Popen(
    ["ffmpeg", "-i", "input.mp4", "output.webm"],
    start_new_session=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)
```

`start_new_session=True`를 주면 child가 새 session leader가 되고, 보통 `os.killpg(proc.pid, signal.SIGTERM)`로 그 group을 종료할 수 있다.

```python
import os
import signal

os.killpg(proc.pid, signal.SIGTERM)
```

이 패턴은 timeout 처리와 shutdown 처리에서 중요하다. 특히 worker나 web server가 종료될 때 Python 프로세스만 내려가고 child가 남으면 배포나 스케일 인 과정에서 리소스가 새기 쉽다.

### Windows는 별도 전략이 필요하다

Windows에서는 Unix signal과 process group 모델이 다르다. `creationflags=subprocess.CREATE_NEW_PROCESS_GROUP` 같은 옵션을 고려해야 하고, 종료 방식도 달라진다. cross-platform 라이브러리를 만든다면 OS별 종료 정책을 추상화해야 한다.

하지만 Linux 서버 운영이 기준이라면 첫 번째 원칙은 단순하다.

> 장시간 실행되거나 child를 더 만들 수 있는 명령은 process group 단위로 시작하고 process group 단위로 종료하라.

---

## 핵심 개념 4: pipe deadlock은 "출력을 안 읽는 부모" 때문에 생긴다

subprocess에서 가장 흔한 함정 중 하나가 pipe deadlock이다.

아래 코드는 위험하다.

```python
proc = subprocess.Popen(
    ["some-command"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)

proc.wait(timeout=30)
stdout = proc.stdout.read()
stderr = proc.stderr.read()
```

왜 위험할까? child process가 stdout 또는 stderr에 많은 데이터를 쓰면 OS pipe buffer가 찬다. buffer가 가득 차면 child는 더 이상 write하지 못하고 멈춘다. 그런데 parent는 `wait()`로 child 종료만 기다리고 있다. child는 parent가 pipe를 읽어 주길 기다리고, parent는 child가 종료되길 기다린다. 이것이 pipe deadlock이다.

기본 해법은 `communicate()`를 쓰는 것이다.

```python
proc = subprocess.Popen(
    ["some-command"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)

stdout, stderr = proc.communicate(timeout=30)
```

`communicate()`는 stdout/stderr를 읽으면서 프로세스 종료를 기다린다. 그래서 `wait()` 후 `read()`보다 안전하다.

하지만 `communicate()`도 모든 문제를 해결하지는 않는다. 출력이 매우 크면 stdout/stderr 전체가 메모리에 올라간다. 로그가 수백 MB 이상 나올 수 있는 명령이라면 capture 방식 자체를 바꿔야 한다.

### 출력이 클 때는 파일 또는 제한된 tail을 써라

대용량 출력에서는 아래 중 하나를 선택하는 편이 낫다.

- stdout을 파일로 보낸다
- stderr만 최근 N KB tail로 보관한다
- 로그 파일을 별도 저장소에 업로드한다
- 호출자에게 streaming으로 전달한다
- 명령 자체의 quiet 옵션을 사용한다

예를 들어 변환 작업에서는 stdout은 산출물 파일로 보내고, stderr의 일부만 장애 메시지에 담는 방식이 흔하다.

```python
from pathlib import Path
import subprocess


def run_with_stderr_tail(command: list[str], log_path: Path, timeout: float) -> None:
    with log_path.open("wb") as stderr_file:
        completed = subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=stderr_file,
            timeout=timeout,
        )

    if completed.returncode != 0:
        tail = log_path.read_bytes()[-4000:].decode("utf-8", errors="replace")
        raise RuntimeError(f"command failed: {tail}")
```

여기서 stderr 전체를 예외 메시지에 넣지 않는 점이 중요하다. 예외 메시지는 로그 시스템, APM, queue payload를 타고 이동한다. 너무 큰 문자열을 예외에 넣으면 장애 처리 자체가 느려질 수 있다.

### stdout과 stderr를 합칠지 분리할지 결정해야 한다

`stderr=subprocess.STDOUT`으로 합치면 순서 파악이 쉬워질 수 있다. 반면 stdout이 실제 결과 데이터라면 stderr와 섞이면 안 된다.

실무 기준은 이렇게 잡을 수 있다.

- stdout이 기계가 읽는 결과라면 stderr와 분리한다
- stdout이 단순 로그라면 stderr와 합쳐도 된다
- 실패 분석에는 stderr tail을 우선 남긴다
- 성공 경로에서는 불필요한 출력 capture를 줄인다

출력 수집은 디버깅 편의가 아니라 메모리와 개인정보 노출, 로그 비용까지 포함한 운영 정책이다.

---

## 핵심 개념 5: `shell=True`는 편의보다 해석 비용이 크다

`shell=True`는 편하다.

```python
subprocess.run(f"convert {src} {dst}", shell=True)
```

하지만 운영 코드에서는 기본적으로 피하는 편이 좋다. shell은 문자열을 다시 해석한다. 공백, quote, wildcard, pipe, redirection, environment expansion이 모두 의미를 가진다. 사용자 입력이 조금이라도 섞이면 command injection 위험이 생긴다.

나쁜 예시는 아래다.

```python
def resize_image(path: str) -> None:
    subprocess.run(f"convert {path} -resize 400x400 out.png", shell=True)
```

`path`에 특수 문자가 들어가면 의도하지 않은 명령이 실행될 수 있다. 안전한 기본값은 list 인자를 쓰는 것이다.

```python
def resize_image(path: str) -> None:
    subprocess.run(
        ["convert", path, "-resize", "400x400", "out.png"],
        check=True,
        timeout=10,
    )
```

list 인자를 쓰면 Python이 argument vector를 직접 전달하므로 shell quoting 문제 대부분이 사라진다.

### shell이 필요한 경우에도 경계를 좁혀야 한다

물론 shell이 필요한 경우는 있다.

- shell builtin이나 복잡한 pipeline이 필요하다
- 레거시 스크립트가 shell 문법을 전제로 한다
- 운영자가 입력한 내부 관리 명령을 그대로 실행해야 한다

그때도 원칙은 같다.

- 외부 사용자 입력을 직접 붙이지 않는다
- 가능한 값은 allowlist로 제한한다
- `shlex.quote()`를 써도 보안의 최종 해답으로 보지 않는다
- 실행 계정을 제한한다
- working directory와 environment를 명시한다
- command 전체를 audit log에 남길지, 민감값을 마스킹할지 결정한다

shell은 도구다. 하지만 shell을 켜면 Python 코드가 직접 관리하던 인자 경계가 문자열 해석기로 넘어간다. 그 비용을 알고 써야 한다.

---

## 핵심 개념 6: environment와 working directory는 재현성의 일부다

subprocess는 기본적으로 부모 프로세스의 environment를 물려받는다. 이게 편할 때도 있지만 운영에서는 문제를 숨긴다.

```python
subprocess.run(["aws", "s3", "cp", src, dst])
```

이 코드는 실행 환경에 따라 결과가 달라질 수 있다.

- 어떤 `PATH`에서 `aws`를 찾는가
- 어떤 `AWS_PROFILE`이나 credential을 쓰는가
- 어떤 locale과 timezone이 적용되는가
- 임시 파일은 어디에 만들어지는가
- 현재 working directory가 어디인가

서비스 코드에서는 되도록 environment를 명시적으로 구성하는 편이 낫다.

```python
import os
import subprocess


env = {
    "PATH": "/usr/local/bin:/usr/bin:/bin",
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "TZ": "UTC",
}

subprocess.run(
    ["/usr/bin/env", "python", "--version"],
    cwd="/tmp/job-123",
    env=env,
    timeout=5,
    check=True,
)
```

물론 모든 변수를 비우면 필요한 인증 정보나 라이브러리 경로가 빠질 수 있다. 그래서 실무에서는 allowlist 기반으로 필요한 변수만 넘기는 방식을 많이 쓴다.

```python
ALLOWED_ENV = {
    "PATH",
    "LANG",
    "LC_ALL",
    "TZ",
    "AWS_REGION",
    "AWS_DEFAULT_REGION",
}


def build_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if key in ALLOWED_ENV}
    env.setdefault("LANG", "C.UTF-8")
    env.setdefault("LC_ALL", "C.UTF-8")
    env.setdefault("TZ", "UTC")
    if extra:
        env.update(extra)
    return env
```

working directory도 마찬가지다. 상대 경로를 쓰는 명령은 `cwd`에 민감하다. API 서버의 현재 디렉터리에 기대면 배포 방식이 바뀌었을 때 깨질 수 있다. 작업별 임시 디렉터리를 만들고, 그 안에서 실행한 뒤, 성공 시 결과만 이동하는 방식이 안전하다.

---

## 실무 예시: 외부 변환 명령을 안전하게 감싸는 wrapper

아래는 Linux 서버에서 장시간 명령을 실행할 때 사용할 수 있는 작은 wrapper 예시다. 핵심은 command 실행을 한 곳에 모아 timeout, process group 종료, stderr tail, return code 번역을 일관되게 처리하는 것이다.

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import signal
import subprocess
import tempfile
import time


@dataclass(frozen=True, slots=True)
class CommandResult:
    args: tuple[str, ...]
    returncode: int
    duration_ms: int
    stderr_tail: str


class CommandTimeoutError(RuntimeError):
    pass


class CommandFailedError(RuntimeError):
    def __init__(self, result: CommandResult) -> None:
        super().__init__(
            f"command failed with exit code {result.returncode}: {result.stderr_tail}"
        )
        self.result = result


def _terminate_group(proc: subprocess.Popen[bytes], grace_seconds: float) -> None:
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return

    deadline = time.monotonic() + grace_seconds
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            return
        time.sleep(0.05)

    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def run_command(
    args: list[str],
    *,
    cwd: Path,
    timeout_seconds: float,
    allowed_returncodes: set[int] | None = None,
    env: dict[str, str] | None = None,
) -> CommandResult:
    allowed = allowed_returncodes or {0}
    started = time.monotonic()

    with tempfile.NamedTemporaryFile(prefix="cmd-stderr-", suffix=".log") as stderr_file:
        proc = subprocess.Popen(
            args,
            cwd=str(cwd),
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=stderr_file,
            start_new_session=True,
        )

        try:
            returncode = proc.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired as exc:
            _terminate_group(proc, grace_seconds=2)
            stderr_file.flush()
            stderr_file.seek(0)
            tail = stderr_file.read()[-4000:].decode("utf-8", errors="replace")
            raise CommandTimeoutError(
                f"command timed out after {timeout_seconds}s: {tail}"
            ) from exc

        duration_ms = int((time.monotonic() - started) * 1000)
        stderr_file.flush()
        stderr_file.seek(0)
        stderr_tail = stderr_file.read()[-4000:].decode("utf-8", errors="replace")

    result = CommandResult(
        args=tuple(args),
        returncode=returncode,
        duration_ms=duration_ms,
        stderr_tail=stderr_tail,
    )

    if returncode not in allowed:
        raise CommandFailedError(result)

    return result
```

이 wrapper가 완벽하다는 뜻은 아니다. 하지만 중요한 운영 기준을 보여 준다.

- stdin은 닫아 interactive 대기를 막는다
- stdout은 버리고 stderr는 파일로 받는다
- child를 새 session으로 시작한다
- timeout 시 process group 전체를 종료한다
- SIGTERM 후 SIGKILL로 단계적 종료한다
- 실패 시 stderr 전체가 아니라 tail만 예외에 담는다
- return code를 호출부 정책으로 해석한다
- 실행 시간을 결과로 남긴다

실제 서비스에서는 여기에 structured logging, metric, command name allowlist, output file 검증, retry policy를 더 붙일 수 있다.

### 변환 작업에 적용하기

예를 들어 이미지 변환 작업은 아래처럼 감쌀 수 있다.

```python
from pathlib import Path
import os
import tempfile


def convert_to_webp(input_path: Path, output_path: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="image-job-") as tmp:
        workdir = Path(tmp)
        temp_output = workdir / "output.webp"

        env = {
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
        }

        run_command(
            [
                "/usr/bin/convert",
                str(input_path),
                "-strip",
                "-resize",
                "1600x1600>",
                str(temp_output),
            ],
            cwd=workdir,
            timeout_seconds=20,
            env=env,
        )

        if not temp_output.exists() or temp_output.stat().st_size == 0:
            raise RuntimeError("converter produced empty output")

        os.replace(temp_output, output_path)
```

여기서 `os.replace()`를 쓰는 이유는 결과 파일을 마지막에 원자적으로 교체하기 위해서다. 변환 도중 실패하면 최종 경로에 깨진 파일이 남지 않는다.

---

## 비동기 서비스에서는 event loop를 막지 말아야 한다

FastAPI나 asyncio worker에서 `subprocess.run()`을 그대로 호출하면 event loop를 막을 수 있다. 짧은 명령이라도 트래픽이 쌓이면 문제가 된다.

나쁜 예시는 아래다.

```python
async def handle_upload(path: str) -> dict[str, str]:
    subprocess.run(["convert", path, "out.webp"], check=True)
    return {"status": "ok"}
```

이 코드는 `async def` 안에 있지만 내부는 동기 block이다. 실행 중 event loop가 다른 coroutine을 처리하지 못할 수 있다.

선택지는 보통 세 가지다.

1. 동기 작업을 thread/process executor로 보낸다
2. `asyncio.create_subprocess_exec()`를 쓴다
3. API 요청에서 직접 처리하지 않고 queue worker로 넘긴다

짧고 CPU를 많이 쓰지 않는 wrapper라면 executor가 현실적인 선택일 수 있다.

```python
import asyncio


async def convert_async(input_path: Path, output_path: Path) -> None:
    await asyncio.to_thread(convert_to_webp, input_path, output_path)
```

하지만 외부 프로세스 실행 자체를 비동기로 제어해야 한다면 `create_subprocess_exec()`가 낫다.

```python
import asyncio


async def run_async_command(args: list[str], timeout: float) -> bytes:
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        start_new_session=True,
    )

    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout)
    except asyncio.TimeoutError:
        os.killpg(proc.pid, signal.SIGTERM)
        try:
            await asyncio.wait_for(proc.wait(), 2)
        except asyncio.TimeoutError:
            os.killpg(proc.pid, signal.SIGKILL)
            await proc.wait()
        raise

    if proc.returncode != 0:
        raise RuntimeError(stderr[-4000:].decode("utf-8", errors="replace"))

    return stdout
```

비동기 코드에서도 핵심은 같다.

- `communicate()`로 pipe를 비운다
- timeout 시 group 단위로 종료한다
- stderr tail을 남긴다
- return code를 확인한다

다만 비동기 cancellation을 추가로 고려해야 한다. caller가 취소되면 child process도 종료되어야 한다. 그렇지 않으면 HTTP 요청은 끊겼는데 변환 프로세스는 계속 돌 수 있다.

```python
async def run_async_command(args: list[str], timeout: float) -> bytes:
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        start_new_session=True,
    )

    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout)
    except asyncio.CancelledError:
        os.killpg(proc.pid, signal.SIGTERM)
        raise
```

취소 처리에서는 cleanup을 얼마나 기다릴지, SIGKILL까지 보낼지, 취소를 다시 전파할지까지 명확히 해야 한다. 기본은 cleanup 후 `raise`다.

---

## 트레이드오프: subprocess를 쓸 것인가, 라이브러리를 쓸 것인가

외부 명령 호출은 빠른 해결책이지만 항상 최선은 아니다. 같은 기능을 Python 라이브러리로 처리할 수 있다면 장단점을 비교해야 한다.

subprocess의 장점은 분명하다.

- 이미 검증된 CLI 도구를 재사용할 수 있다
- Python 패키지로 감싸기 어려운 네이티브 기능을 쉽게 호출한다
- crash가 Python 프로세스 전체를 죽일 가능성이 상대적으로 낮다
- 메모리 누수가 있는 작업을 프로세스 단위로 격리할 수 있다
- 라이선스와 배포가 허용된다면 팀 생산성이 높다

반대로 비용도 있다.

- 실행 파일 배포와 버전 관리가 필요하다
- stdout/stderr, exit code, signal 해석을 직접 해야 한다
- 프로세스 생성 비용이 있다
- observability가 Python 함수보다 거칠다
- 입력 escaping, 임시 파일, 권한 경계가 복잡하다
- timeout과 cleanup을 실수하기 쉽다

Python 라이브러리의 장점은 타입, 예외, 테스트, 관측성이 자연스럽다는 점이다. 하지만 네이티브 확장 라이브러리라면 crash나 memory leak이 Python 프로세스에 직접 영향을 줄 수 있다. 또 라이브러리가 큰 파일을 메모리에 올리는 방식이라면 CLI streaming보다 더 위험할 수 있다.

실무 기준은 이렇게 잡을 수 있다.

- 짧고 안정적인 OS 기능 호출: subprocess 가능
- 긴 CPU 작업 또는 실패 격리가 중요한 변환: subprocess가 오히려 안전할 수 있음
- 요청마다 매우 자주 호출되는 짧은 기능: 라이브러리 우선 검토
- 복잡한 결과 객체와 세밀한 예외 처리가 필요한 기능: 라이브러리 우선 검토
- CLI가 사실상 표준이고 팀이 운영 경험을 갖고 있는 기능: subprocess wrapper 표준화

중요한 것은 "subprocess는 나쁘다"가 아니다. subprocess를 쓰는 순간 운영 경계가 생기므로 그 경계를 명시적으로 설계해야 한다는 뜻이다.

---

## 흔한 실수

### 1. 사용자 입력을 command string에 붙인다

```python
subprocess.run(f"tar -xf {filename}", shell=True)
```

사용자 입력이 섞이는 순간 위험하다. list 인자를 쓰고, 파일명은 별도 검증과 안전한 임시 디렉터리 안에서 다뤄야 한다.

### 2. timeout 없이 실행한다

외부 명령은 네트워크, 디스크, lock, 무한 대기, 버그에 걸릴 수 있다. 기본 timeout이 없는 wrapper는 운영 코드에 들어가면 안 된다.

### 3. timeout 후 parent process만 죽인다

직접 시작한 process만 종료하고 grandchild를 놓치면 누수가 생긴다. child를 새 session/process group으로 시작하고 group 단위 종료를 고려해야 한다.

### 4. `wait()` 후 `stdout.read()`를 호출한다

출력이 많으면 pipe deadlock이 생길 수 있다. pipe를 열었다면 `communicate()`를 기본으로 생각해야 한다.

### 5. 큰 출력을 전부 메모리에 capture한다

`capture_output=True`는 편하지만 출력이 클 수 있는 명령에는 위험하다. 파일, tail, streaming을 검토해야 한다.

### 6. stderr를 버린다

실패 분석에 필요한 대부분의 정보는 stderr에 있다. 성공 경로에서 모든 로그를 보관할 필요는 없지만, 실패 시 최근 stderr tail은 남기는 편이 좋다.

### 7. 현재 environment를 그대로 넘긴다

부모 프로세스의 secret, profile, locale, path가 그대로 전달된다. 재현성과 보안 측면에서 allowlist를 고려해야 한다.

### 8. 결과 파일 검증 없이 성공 처리한다

exit code가 0이어도 결과 파일이 비었거나 손상될 수 있다. 파일 존재, 크기, magic bytes, checksum, 후속 validator를 확인해야 한다.

### 9. retry를 쉽게 붙인다

subprocess 실패가 항상 재시도 가능한 것은 아니다. 입력 파일 오류, unsupported format, permission denied는 retry해도 의미가 없다. timeout, temporary file system error, 일시적인 external dependency 실패만 제한적으로 재시도해야 한다.

### 10. command wrapper를 테스트하지 않는다

subprocess wrapper는 장애 대응 코드다. timeout, non-zero exit, 큰 stderr, signal 종료, 잘못된 command, 출력 파일 누락을 테스트해야 한다.

---

## 운영 체크리스트

subprocess를 운영 코드에 넣기 전 아래 항목을 확인하자.

- 명령은 list 인자로 실행하는가
- `shell=True`가 필요하다면 입력과 quoting 경계가 명확한가
- 실행 파일 경로와 버전을 고정하거나 검증하는가
- 기본 timeout이 있는가
- 전체 요청 deadline과 subprocess timeout이 맞물려 있는가
- timeout 후 SIGTERM, SIGKILL 단계가 있는가
- child process group 전체를 종료할 수 있는가
- stdin을 닫아 interactive 대기를 막는가
- stdout/stderr를 어떻게 수집할지 정했는가
- pipe를 열었다면 deadlock 없이 읽는가
- 출력 크기 제한 또는 파일 기반 로그 전략이 있는가
- 실패 시 stderr tail이 남는가
- return code를 명령별 의미로 해석하는가
- environment allowlist 또는 명시적 env를 쓰는가
- working directory를 작업별로 분리하는가
- 임시 파일은 성공과 실패 모두에서 정리되는가
- 결과 파일을 원자적으로 이동하는가
- 결과 파일의 존재, 크기, 형식을 검증하는가
- retry 가능 실패와 불가능 실패를 구분하는가
- structured log와 metric에 command name, duration, return code, timeout 여부가 남는가
- 테스트에서 timeout, 실패 exit, 큰 출력, child cleanup을 검증하는가

---

## 한줄 정리

Python에서 subprocess를 안전하게 쓰려면 명령 실행 한 줄을 줄이는 데 집중하지 말고, timeout, process group, pipe, 출력, environment, 결과 검증을 포함한 외부 프로세스 생명주기를 하나의 운영 계약으로 감싸야 한다.
