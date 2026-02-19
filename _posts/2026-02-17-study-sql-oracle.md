---
layout: post
title: "Oracle SQL 기초: 실무에서 자주 쓰는 쿼리 패턴 마스터하기"
date: 2026-02-17 01:39:38 +0900
categories: [sql]
tags: [study, sql, oracle, database, automation]
---

## 왜 Oracle SQL을 제대로 알아야 할까?

금융, 통신, 공공기관 등 대규모 엔터프라이즈 시스템의 대부분이 Oracle 데이터베이스를 사용합니다.

효율적인 쿼리 작성은 시스템 성능에 직결되며, 잘못된 SQL은 전체 애플리케이션을 느리게 만듭니다.
특히 대용량 데이터 처리에서 인덱스 활용과 쿼리 최적화는 필수 스킬입니다.

## 핵심 개념 5가지

- **SELECT 문의 실행 순서**
  FROM → WHERE → GROUP BY → HAVING → SELECT → ORDER BY.
  이 순서를 이해해야 성능 최적화가 가능합니다
- **인덱스 활용**
  WHERE 절에서 인덱스 컬럼을 올바르게 사용하면 쿼리 속도가 수십 배 향상됩니다
- **조인(JOIN) 전략**
  INNER, LEFT, RIGHT JOIN의 차이를 정확히 이해하고 필요한 타입을 선택해야 합니다
- **집계 함수와 GROUP BY**
  COUNT, SUM, AVG 등을 GROUP BY와 함께 사용할 때 NULL 처리와 HAVING 절의 역할을 명확히 해야 합니다
- **서브쿼리와 WITH 절**
  복잡한 쿼리는 CTE를 사용해 가독성과 유지보수성을 높일 수 있습니다

## 실습 예제: 부서별 평균 급여 조회

```sql
WITH dept_avg AS (
  SELECT 
    dept_id,
    dept_name,
    AVG(salary) as avg_salary,
    COUNT(*) as emp_count
  FROM employees e
  INNER JOIN departments d ON e.dept_id = d.id
  WHERE hire_date >= TRUNC(SYSDATE, 'YYYY')
  GROUP BY dept_id, dept_name
  HAVING COUNT(*) >= 3
)
SELECT 
  dept_id,
  dept_name,
  ROUND(avg_salary, 2) as avg_salary,
  emp_count
FROM dept_avg
WHERE avg_salary > (SELECT AVG(salary) FROM employees)
ORDER BY avg_salary DESC;
```

**이 쿼리의 포인트:**
- CTE로 복잡한 로직을 단계별로 구성
- INNER JOIN으로 필요한 데이터만 결합
- HAVING으로 그룹 레벨 필터링
- 서브쿼리로 전체 평균과 비교

## 자주 하는 실수 3가지

**1. SELECT 절에 GROUP BY 없는 컬럼 포함**
```sql
-- ❌ 잘못된 예
SELECT dept_id, emp_name, AVG(salary)
FROM employees
GROUP BY dept_id;
-- emp_name이 GROUP BY에 없으면 오류 발생

-- ✅ 올바른 예
SELECT dept_id, AVG(salary)
FROM employees
GROUP BY dept_id;
```

**2. NULL 값 처리 무시**
```sql
-- ❌ commission이 NULL인 행은 계산에서 제외됨
SELECT emp_id, salary + commission as total
FROM employees;

-- ✅ NVL로 NULL을 0으로 변환
SELECT emp_id, salary + NVL(commission, 0) as total
FROM employees;
```

**3. 대소문자 구분 실수**
```sql
-- Oracle은 컬럼명을 대문자로 저장하지만, 쿼리에서는 소문자로 작성 가능
-- 하지만 문자열 비교는 대소문자를 구분하므로 주의 필요
SELECT * FROM employees WHERE dept_name = 'sales'; -- 찾지 못할 수 있음
SELECT * FROM employees WHERE UPPER(dept_name) = 'SALES'; -- 안전한 방식
```

## 오늘의 실습 체크리스트

- [ ] Oracle SQL 실행 순서(FROM → WHERE → GROUP BY → HAVING → SELECT → ORDER BY) 다시 정리하기
- [ ] 회사 DB에서 간단한 SELECT 쿼리 작성해보기 (최소 2개 테이블 조인)
- [ ] 작성한 쿼리에서 NULL 처리가 필요한 부분 찾아 NVL/COALESCE 적용하기
- [ ] EXPLAIN PLAN으로 쿼리 실행 계획 확인해보기
- [ ] GROUP BY를 사용한 집계 쿼리 1개 작성하고 HAVING 절로 필터링하기
- [ ] CTE(WITH 절)를 사용해 복잡한 쿼리를 단계별로 재작성하기

**팁**: 실무에서는 항상 EXPLAIN PLAN을 확인하고, 대용량 데이터로 성능 테스트를 먼저 진행한 후 배포하세요!
