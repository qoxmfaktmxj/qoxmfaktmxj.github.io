---
layout: post
title: "MySQL 인덱스와 실행 계획(EXPLAIN) 실전: 느린 조회를 진짜로 줄이는 법"
date: 2026-03-16 10:15:39 +0900
categories: [sql]
tags: [study, sql, mysql, index, explain, performance]
---

## 왜 EXPLAIN을 알아야 할까?

MySQL 튜닝에서 가장 흔한 오해는 "인덱스를 추가하면 무조건 빨라진다"는 생각입니다. 실제로는 어떤 인덱스를, 어떤 WHERE 조건과 JOIN 순서에 맞게 설계했는지가 중요합니다.

`EXPLAIN`은 MySQL이 쿼리를 어떻게 실행하려는지 보여주는 기본 도구입니다.

## 예시 테이블

```sql
CREATE TABLE orders (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  status VARCHAR(20) NOT NULL,
  created_at DATETIME NOT NULL,
  total_amount DECIMAL(10,2) NOT NULL
);
```

## 느린 쿼리

```sql
SELECT *
FROM orders
WHERE user_id = 1001
  AND status = 'PAID'
ORDER BY created_at DESC
LIMIT 20;
```

## 인덱스 추가 전 확인

```sql
EXPLAIN SELECT *
FROM orders
WHERE user_id = 1001
  AND status = 'PAID'
ORDER BY created_at DESC
LIMIT 20;
```

## 복합 인덱스 추가

```sql
CREATE INDEX idx_orders_user_status_created
ON orders (user_id, status, created_at DESC);
```

## 왜 복합 인덱스인가?

이 쿼리는 `user_id`, `status`, `created_at`를 함께 사용합니다. 각각 단일 인덱스를 따로 두는 것보다, 실제 조회 패턴에 맞는 복합 인덱스가 더 효과적일 수 있습니다.

## 실무 체크포인트

- 자주 같이 조회되는 조건인가?
- 정렬 컬럼이 인덱스 뒤에 자연스럽게 붙는가?
- 인덱스를 추가했을 때 쓰기 비용 증가를 감당할 수 있는가?

## 흔한 실수

- SELECT 패턴 분석 없이 인덱스를 계속 추가
- EXPLAIN 결과를 안 보고 체감으로 튜닝
- 복합 인덱스 순서를 무작위로 결정

## 한 줄 정리

MySQL 성능 튜닝의 시작점은 감이 아니라, **실제 쿼리 패턴과 EXPLAIN 결과**입니다.
