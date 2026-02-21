---
layout: post
title: "Python 컨텍스트 매니저(Context Manager) 마스터하기"
date: 2026-02-21 10:03:01 +0900
categories: [python]
tags: [study, python, backend, automation]
---

## 실무에서 왜 중요한가?

컨텍스트 매니저는 파일 처리, 데이터베이스 연결, 락(Lock) 관리 등에서 리소스를 안전하게 획득하고 해제하는 패턴입니다.

`with` 문을 사용하면 예외 발생 여부와 관계없이 정리 코드가 항상 실행되므로, 메모리 누수와 연결 고갈을 방지할 수 있습니다.

## 핵심 개념

- **`__enter__()` 메서드**
  `with` 블록 진입 시 호출되며, 리소스를 획득하고 반환합니다.

- **`__exit__()` 메서드**
  `with` 블록 종료 시 항상 호출되며, 리소스를 정리합니다. 예외 정보도 받습니다.

- **`contextlib.contextmanager` 데코레이터**
  클래스 대신 제너레이터 함수로 간단하게 컨텍스트 매니저를 만들 수 있습니다.

- **예외 처리**
  `__exit__()` 메서드에서 `True`를 반환하면 예외를 억제할 수 있습니다.

- **다중 컨텍스트 매니저**
  여러 리소스를 한 번에 관리할 수 있습니다.

## 실습 예제

### 클래스 기반 컨텍스트 매니저

```python
class FileManager:
    def __init__(self, filename, mode):
        self.filename = filename
        self.mode = mode
        self.file = None
    
    def __enter__(self):
        print(f"파일 열기: {self.filename}")
        self.file = open(self.filename, self.mode)
        return self.file
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        print(f"파일 닫기: {self.filename}")
        if self.file:
            self.file.close()
        return False

# 사용 예
with FileManager('test.txt', 'w') as f:
    f.write('Hello, Context Manager!')
```

### 데코레이터 기반 컨텍스트 매니저

```python
from contextlib import contextmanager

@contextmanager
def database_connection(db_name):
    print(f"DB 연결: {db_name}")
    connection = f"Connection to {db_name}"
    try:
        yield connection
    finally:
        print(f"DB 종료: {db_name}")

# 사용 예
with database_connection('mydb') as conn:
    print(f"쿼리 실행: {conn}")
```

### 다중 컨텍스트 매니저

```python
with open('input.txt', 'r') as infile, open('output.txt', 'w') as outfile:
    for line in infile:
        outfile.write(line.upper())
```

### 예외 처리 예제

```python
class ErrorHandler:
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is ValueError:
            print(f"ValueError 처리됨: {exc_val}")
            return True  # 예외 억제
        return False

# 사용 예
with ErrorHandler():
    raise ValueError("이 에러는 억제됩니다")
print("프로그램 계속 실행")
```

## 자주 하는 실수

- **`__exit__()` 메서드 반환값 무시**
  `__exit__()`에서 `True`를 반환해야만 예외가 억제됩니다. 반환값이 없으면 예외가 전파됩니다.

- **리소스 정리 코드를 `__exit__()`에 넣지 않기**
  정리 코드를 `__enter__()`나 블록 내부에 넣으면, 예외 발생 시 실행되지 않을 수 있습니다.

- **제너레이터 함수에서 `finally` 블록 빼먹기**
  `@contextmanager` 사용 시 `finally` 블록이 없으면 리소스가 정리되지 않습니다.

- **다중 컨텍스트에서 순서 무시**
  여러 리소스를 관리할 때 획득 순서와 반대로 해제되어야 합니다. `with` 문은 이를 자동으로 처리합니다.

- **`__exit__()` 메서드에서 새로운 예외 발생**
  정리 중 예외가 발생하면 원래 예외가 가려질 수 있습니다. 신중하게 처리하세요.

## 오늘의 실습 체크리스트

- [ ] 클래스 기반 컨텍스트 매니저 구현하고 테스트하기
- [ ] `@contextmanager` 데코레이터로 간단한 매니저 만들기
- [ ] 파일 I/O에서 `with` 문 사용하기
- [ ] 다중 컨텍스트 매니저 작성하고 실행하기
- [ ] `__exit__()` 메서드의 예외 처리 로직 구현하기
- [ ] 예외 발생 시 리소스가 제대로 정리되는지 확인하기
