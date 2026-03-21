---
layout: post
title: "Elasticsearch 기초: 검색 엔진의 핵심 이해하기"
date: 2026-03-21 10:02:24 +0900
categories: [data-infra]
tags: [study, elasticsearch, search, infra, automation]
---

## 왜 Elasticsearch가 중요한가?

Elasticsearch는 대규모 데이터에서 빠른 검색을 가능하게 하는 핵심 인프라입니다. 로그 분석, 전문 검색, 실시간 분석이 필요한 모든 프로젝트에서 필수적입니다.

실제 프로젝트에서 데이터베이스만으로는 수백만 건의 레코드를 빠르게 검색할 수 없습니다. Elasticsearch는 이 문제를 해결합니다.

## 핵심 개념

- **Index (인덱스)**
  데이터베이스의 테이블과 유사한 개념입니다. 검색 가능한 데이터의 모음입니다.

- **Document (문서)**
  인덱스 내의 개별 데이터 단위입니다. JSON 형식으로 저장됩니다.

- **Shard (샤드)**
  인덱스를 여러 부분으로 나누어 분산 저장합니다. 성능과 확장성을 높입니다.

- **Replica (복제본)**
  샤드의 복사본으로, 장애 대응과 읽기 성능을 향상시킵니다.

- **Mapping (매핑)**
  문서의 필드 타입을 정의합니다. 데이터베이스 스키마와 유사합니다.

## 실습: 기본 CRUD 작업

먼저 인덱스를 생성하고 문서를 추가해봅시다.

```bash
curl -X PUT "localhost:9200/products" -H 'Content-Type: application/json' -d'{
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 1
  },
  "mappings": {
    "properties": {
      "name": {"type": "text"},
      "price": {"type": "integer"},
      "category": {"type": "keyword"}
    }
  }
}'
```

이제 문서를 추가합니다.

```bash
curl -X POST "localhost:9200/products/_doc" -H 'Content-Type: application/json' -d'{
  "name": "무선 마우스",
  "price": 25000,
  "category": "전자기기"
}'
```

검색 쿼리를 실행합니다.

```bash
curl -X GET "localhost:9200/products/_search" -H 'Content-Type: application/json' -d'{
  "query": {
    "match": {
      "name": "마우스"
    }
  }
}'
```

## 일반적인 실수

- **Text vs Keyword 혼동**
  Text는 전문 검색용(분석됨), Keyword는 정확 매칭용(분석 안 됨)입니다. 용도에 맞게 선택하세요.

- **과도한 샤드 설정**
  샤드가 너무 많으면 오버헤드가 증가합니다. 일반적으로 노드당 1-3개 샤드가 적절합니다.

- **Mapping 없이 시작**
  동적 매핑은 편하지만 예측 불가능합니다. 프로덕션에서는 명시적 매핑을 정의하세요.

- **쿼리 성능 무시**
  복잡한 쿼리는 성능을 저하시킵니다. 인덱싱 전략으로 최적화하세요.

## 오늘의 실습 체크리스트

- [ ] Elasticsearch 로컬 환경 설정 (Docker 또는 직접 설치)
- [ ] 간단한 인덱스 생성 및 매핑 정의
- [ ] 샘플 문서 5개 이상 추가
- [ ] match, term, range 쿼리 각각 실행해보기
- [ ] 검색 결과의 _score 값 이해하기
- [ ] GET 요청으로 특정 문서 조회하기
- [ ] 문서 업데이트 및 삭제 작업 수행
