---
layout: post
title: "MySQL SQL 기초: 개발자를 위한 일일 학습 가이드"
date: 2026-02-16 14:23:05 +0900
categories: [sql]
tags: [study, sql, mysql, database, automation]
---

# MySQL SQL 기초: 개발자를 위한 일일 학습 가이드

## 왜 이것이 중요한가?

MySQL은 전 세계 웹 애플리케이션의 **60% 이상**에서 사용되는 가장 인기 있는 관계형 데이터베이스입니다.

효율적인 SQL 작성 능력은 애플리케이션 성능, 데이터 무결성, 개발 생산성에 직접적인 영향을 미칩니다.
잘못된 쿼리는 느린 응답 속도와 서버 과부하를 초래하므로, 기초부터 탄탄히 다지는 것이 필수입니다.

## 핵심 개념

- **CRUD 연산**: CREATE(INSERT), READ(SELECT), UPDATE, DELETE - 모든 데이터 조작의 기본
- **JOIN 연산**: INNER JOIN, LEFT JOIN, RIGHT JOIN을 통한 다중 테이블 데이터 결합
- **인덱싱**: WHERE, ORDER BY 절의 성능을 극적으로 향상시키는 핵심 최적화 기법
- **트랜잭션**: ACID 특성을 보장하여 데이터 일관성 유지
- **쿼리 최적화**: EXPLAIN을 활용한 실행 계획 분석 및 성능 개선

## 실습 예제

### 기본 테이블 생성

```sql
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### CRUD 연산 실습

```sql
-- INSERT: 데이터 삽입
INSERT INTO users (name, email)
VALUES ('김개발', 'kim@example.com');

-- SELECT: 데이터 조회
SELECT * FROM users WHERE name LIKE '김%';

-- UPDATE: 데이터 수정
UPDATE users
SET email = 'kim.dev@example.com'
WHERE id = 1;

-- DELETE: 데이터 삭제
DELETE FROM users WHERE id = 1;
```

### JOIN을 활용한 관계형 데이터 조회

```sql
CREATE TABLE posts (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    title VARCHAR(200),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

사용자와 게시물을 함께 조회합니다:

```sql
SELECT u.name, p.title
FROM users u
INNER JOIN posts p ON u.id = p.user_id;
```

### 인덱스 생성으로 성능 향상

```sql
CREATE INDEX idx_email ON users(email);
CREATE INDEX idx_user_id ON posts(user_id);
```

### 쿼리 성능 분석

```sql
EXPLAIN SELECT * FROM users
WHERE email = 'kim@example.com';
```

## 흔한 실수

1. **N+1 쿼리 문제**
   루프 내에서 반복적으로 쿼리 실행 → JOIN이나 배치 처리로 해결
2. **인덱스 미사용**
   WHERE 절에 함수 적용 시 인덱스 활용 불가
   예: `WHERE YEAR(created_at) = 2026`
3. **와일드카드 앞에 %**
   `LIKE '%keyword'`는 인덱스를 사용하지 못함
4. **트랜잭션 미사용**
   여러 쿼리의 원자성 미보장 → 데이터 불일치 발생
5. **SELECT \***
   불필요한 컬럼까지 조회 → 명시적으로 필요한 컬럼만 선택

## 오늘의 실습 체크리스트

- [ ] 로컬 MySQL 서버 실행 확인 (`mysql -u root -p`)
- [ ] 새로운 데이터베이스 생성 (`CREATE DATABASE practice_db;`)
- [ ] users 테이블 생성 및 5개 이상의 샘플 데이터 INSERT
- [ ] SELECT로 다양한 WHERE 조건 실습 (AND, OR, IN, BETWEEN)
- [ ] 두 개 이상의 테이블 생성 후 INNER JOIN 실습
- [ ] UPDATE와 DELETE 연산 안전하게 실습 (WHERE 조건 필수)
- [ ] 자주 조회되는 컬럼에 INDEX 생성
- [ ] EXPLAIN으로 쿼리 실행 계획 확인
- [ ] 간단한 트랜잭션 작성 (BEGIN, COMMIT, ROLLBACK)
- [ ] 오늘 작성한 모든 쿼리를 파일로 저장

---

**팁**: 매일 최소 1시간씩 실제 쿼리를 작성하고 실행해보세요. 이론만으로는 SQL 감각이 생기지 않습니다. 내일은 고급 쿼리 최적화와 윈도우 함수를 다루겠습니다!
