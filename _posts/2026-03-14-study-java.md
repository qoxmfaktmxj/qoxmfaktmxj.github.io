---
layout: post
title: "Java Optional 실전: null 방어를 넘어서 의도를 표현하는 법"
date: 2026-03-14 10:04:26 +0900
categories: [java]
tags: [study, java, optional, null-safety, backend, spring]
---

## 왜 Optional을 실무에서 다시 봐야 할까?

Java에서 `NullPointerException`은 너무 흔해서 무감각해지기 쉽지만, 실제 문제는 null 자체보다 **값이 없을 수 있다는 사실을 코드가 제대로 표현하지 못하는 것**입니다.

`Optional`은 모든 곳에 남발하라고 나온 도구가 아니라, "이 값은 없을 수 있다"는 의도를 드러내기 위한 표현 장치입니다.

## 기본 사용법

```java
Optional<String> nickname = Optional.ofNullable(user.getNickname());

String displayName = nickname.orElse("게스트");
System.out.println(displayName);
```

## map / filter / orElseGet

```java
String result = Optional.ofNullable(user)
        .map(User::getProfile)
        .map(Profile::getNickname)
        .filter(name -> !name.isBlank())
        .orElseGet(() -> "기본닉네임");
```

## 언제 쓰면 좋은가?

- Repository 조회 결과
- 외부 API 응답의 선택적 필드
- 변환 체인에서 null-safe 처리

## 언제 피해야 하나?

- DTO 필드 자체를 `Optional`로 선언
- 엔티티 필드에 남발
- 단순 getter/setter 전부에 적용

## 흔한 실수

- `isPresent()` 후 `get()` 패턴으로 사실상 null 체크와 다를 바 없게 사용
- `orElse()` 안에 무거운 계산을 넣어 불필요한 연산 발생
- Optional을 컬렉션처럼 오해

## 한 줄 정리

Optional은 null을 없애는 도구가 아니라, **값의 부재 가능성을 코드 수준에서 명확히 표현하는 도구**입니다.
