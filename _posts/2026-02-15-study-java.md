---
layout: post
title: "Java 스트림 API로 함수형 프로그래밍 마스터하기"
date: 2026-02-15 01:25:43 +0900
categories: [java]
tags: [study, java, spring, backend, automation]
---

# Java 스트림 API로 함수형 프로그래밍 마스터하기

## 왜 이것이 중요한가?

실무에서 대용량 데이터를 처리할 때 스트림 API는 필수입니다.
기존의 반복문 대신 선언적이고 간결한 코드를 작성할 수 있으며, 병렬 처리도 간단하게 구현할 수 있습니다.

특히 데이터 필터링, 변환, 집계 작업에서 가독성과 성능을 동시에 확보할 수 있습니다.

## 핵심 개념

- **스트림의 특징**
  일회용이며 지연 평가(lazy evaluation)를 지원합니다
- **중간 연산**
  filter, map, flatMap, distinct, sorted 등으로 파이프라인을 구성합니다
- **최종 연산**
  collect, forEach, reduce, findFirst 등으로 결과를 도출합니다
- **함수형 인터페이스**
  Predicate, Function, Consumer 등을 활용한 람다식 작성
- **병렬 스트림**
  `parallelStream()`으로 멀티스레드 처리를 자동화합니다

## 실전 예제

### Product 클래스와 데이터 준비

```java
import java.util.*;
import java.util.stream.Collectors;

public class StreamExample {
    static class Product {
        String name;
        int price;
        String category;

        Product(String name, int price, String category) {
            this.name = name;
            this.price = price;
            this.category = category;
        }
    }
}
```

### 스트림 활용 예제

```java
List<Product> products = Arrays.asList(
    new Product("노트북", 1500000, "전자제품"),
    new Product("마우스", 50000, "전자제품"),
    new Product("책", 15000, "도서"),
    new Product("키보드", 80000, "전자제품")
);

// 1. 필터링 + 매핑
List<String> expensiveItems = products.stream()
    .filter(p -> p.price > 50000)
    .map(p -> p.name)
    .collect(Collectors.toList());

// 2. 그룹핑
Map<String, List<Product>> byCategory =
    products.stream()
        .collect(Collectors.groupingBy(p -> p.category));

// 3. 집계
int totalPrice = products.stream()
    .mapToInt(p -> p.price)
    .sum();

// 4. 조건 확인
boolean hasExpensive = products.stream()
    .anyMatch(p -> p.price > 1000000);
```

## 흔한 실수

1. **스트림 재사용**
   스트림은 일회용입니다. 한 번 최종 연산을 실행하면 다시 사용할 수 없습니다.
   ```java
   Stream<Integer> stream =
       Arrays.asList(1, 2, 3).stream();
   stream.forEach(System.out::println);
   stream.forEach(System.out::println); // 에러!
   ```

2. **병렬 스트림의 무분별한 사용**
   작은 데이터셋에서는 오버헤드가 더 클 수 있습니다.

3. **null 처리 누락**
   filter나 map에서 null을 반환하면 `NullPointerException`이 발생할 수 있습니다.

4. **부작용(Side Effect) 포함**
   스트림 내에서 외부 상태를 변경하면 병렬 처리 시 예상치 못한 결과가 나옵니다.

## 오늘의 실습 체크리스트

- [ ] 기본 스트림 생성 방법 3가지 이상 실습 (Arrays.stream, Collection.stream, Stream.of)
- [ ] filter와 map을 조합한 파이프라인 작성
- [ ] collect()로 List, Map, Set으로 변환하기
- [ ] reduce()를 사용한 집계 연산 구현
- [ ] 자신의 프로젝트에서 반복문을 스트림으로 리팩토링하기
- [ ] 병렬 스트림과 순차 스트림의 성능 비교 (1000개 이상 데이터)
- [ ] Optional을 활용한 null 안전한 스트림 처리

**팁**: 스트림 API는 선언적 사고를 요구합니다. "어떻게"보다 "무엇을"에 집중하세요!
