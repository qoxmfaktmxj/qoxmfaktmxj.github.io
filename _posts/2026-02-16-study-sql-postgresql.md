---
layout: post
title: "PostgreSQL SQL 기초: 개발자를 위한 하루 학습 가이드"
date: 2026-02-16 01:27:03 +0900
categories: [sql]
tags: [study, sql, postgresql, database, automation]
---

## 왜 PostgreSQL SQL을 배워야 할까?

현대적인 웹 애플리케이션 개발에서 데이터베이스는 필수 요소입니다. PostgreSQL은 오픈소스이면서도 엔터프라이즈급 기능을 제공하는 RDBMS로, 스타트업부터 대기업까지 광범위하게 사용됩니다. SQL을 제대로 이해하면 쿼리 성능 최적화, 데이터 무결성 보장, 복잡한 비즈니스 로직 구현이 가능해집니다.

## 핵심 개념 5가지

- **SELECT와 WHERE**: 데이터 조회의 기본. 조건에 맞는 행을 효율적으로 필터링하는 것이 성능의 첫 단계
- **JOIN**: 여러 테이블의 관계를 연결하는 핵심 기술. INNER, LEFT, RIGHT, FULL OUTER JOIN의 차이 이해 필수
- **GROUP BY와 집계함수**: COUNT, SUM, AVG, MAX, MIN을 활용한 데이터 분석
- **INDEX**: 쿼리 성능을 좌우하는 가장 중요한 최적화 도구
- **트랜잭션(Transaction)**: ACID 속성을 통한 데이터 일관성 보장

## 실습 예제: 전자상거래 데이터베이스

먼저 테이블을 생성합니다:

    CREATE TABLE users (
        id SERIAL PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        email VARCHAR(100) UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE orders (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id),
        total_amount DECIMAL(10, 2),
        order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

기본 데이터 삽입:

    INSERT INTO users (name, email) VALUES ('김개발', 'kim@example.com');
    INSERT INTO users (name, email) VALUES ('이디버그', 'lee@example.com');
    INSERT INTO orders (user_id, total_amount) VALUES (1, 50000);
    INSERT INTO orders (user_id, total_amount) VALUES (1, 75000);
    INSERT INTO orders (user_id, total_amount) VALUES (2, 30000);

**JOIN을 활용한 조회**:

    SELECT u.name, COUNT(o.id) as order_count, SUM(o.total_amount) as total_spent
    FROM users u
    LEFT JOIN orders o ON u.id = o.user_id
    GROUP BY u.id, u.name
    HAVING SUM(o.total_amount) > 0
    ORDER BY total_spent DESC;

이 쿼리는 각 사용자별 주문 수와 총 지출액을 계산합니다.

## 흔한 실수 3가지

1. **N+1 쿼리 문제**: 루프 내에서 반복적으로 쿼리를 실행하는 것. JOIN이나 서브쿼리로 해결
2. **INDEX 없이 대용량 데이터 조회**: 테이블 풀 스캔은 성능 저하의 주범. 자주 조회하는 컬럼에는 INDEX 생성
3. **트랜잭션 미사용**: 여러 쿼리가 함께 실행되어야 할 때 BEGIN/COMMIT을 빼먹으면 데이터 불일치 발생

## 오늘의 실습 체크리스트

- [ ] PostgreSQL 로컬 환경 설정 (또는 Docker 컨테이너 실행)
- [ ] 위 예제의 테이블 생성 및 데이터 삽입 실행
- [ ] SELECT + WHERE로 특정 사용자의 주문 조회
- [ ] INNER JOIN과 LEFT JOIN의 결과 차이 비교
- [ ] GROUP BY + HAVING으로 조건부 집계 쿼리 작성
- [ ] EXPLAIN ANALYZE로 쿼리 실행 계획 확인
- [ ] 간단한 INDEX 생성 후 성능 비교
- [ ] 트랜잭션 예제: 두 개의 INSERT를 하나의 트랜잭션으로 묶기

## 다음 단계

내일은 **고급 JOIN 기법**과 **윈도우 함수(Window Functions)**를 학습하세요. 이들은 복잡한 데이터 분석에 필수적입니다.
