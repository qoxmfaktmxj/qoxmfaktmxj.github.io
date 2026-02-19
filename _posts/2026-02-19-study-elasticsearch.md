---
layout: post
title: "Elasticsearch 기초: 검색 엔진의 핵심 이해하기"
date: 2026-02-19 10:08:56 +0900
categories: [data-infra]
tags: [study, elasticsearch, search, infra, automation]
---

## 왜 Elasticsearch를 배워야 할까?

실제 프로젝트에서 데이터베이스만으로는 빠른 검색과 복잡한 쿼리를 처리하기 어렵습니다. Elasticsearch는 대규모 데이터셋에서 밀리초 단위의 검색 응답을 제공하며, 로그 분석, 전문 검색(full-text search), 실시간 분석 등 데이터 인프라의 핵심 역할을 합니다. Netflix, Uber, Airbnb 같은 대규모 서비스들이 모두 Elasticsearch를 운영 중입니다.

## 핵심 개념

- **클러스터(Cluster)**: 여러 노드로 구성된 Elasticsearch 인스턴스 그룹. 데이터 분산 저장과 고가용성을 제공합니다.
- **인덱스(Index)**: 관계형 데이터베이스의 테이블과 유사한 개념. 문서들의 논리적 그룹입니다.
- **문서(Document)**: JSON 형식의 데이터 단위. 각 문서는 고유한 ID를 가집니다.
- **샤드(Shard)**: 인덱스를 분할한 물리적 단위. 병렬 처리와 확장성을 제공합니다.
- **매핑(Mapping)**: 문서의 필드 타입과 분석 방식을 정의하는 스키마입니다.

## 실습: 기본 CRUD 작업

먼저 Elasticsearch가 실행 중이라고 가정합니다(기본 포트: 9200).

    # 1. 인덱스 생성
    curl -X PUT "localhost:9200/products" -H 'Content-Type: application/json' -d'{
      "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0
      },
      "mappings": {
        "properties": {
          "name": {"type": "text"},
          "price": {"type": "integer"},
          "category": {"type": "keyword"}
        }
      }
    }'

    # 2. 문서 추가
    curl -X POST "localhost:9200/products/_doc" -H 'Content-Type: application/json' -d'{
      "name": "무선 이어폰",
      "price": 89000,
      "category": "electronics"
    }'

    # 3. 검색 쿼리
    curl -X GET "localhost:9200/products/_search" -H 'Content-Type: application/json' -d'{
      "query": {
        "match": {
          "name": "이어폰"
        }
      }
    }'

    # 4. 문서 업데이트
    curl -X POST "localhost:9200/products/_doc/1/_update" -H 'Content-Type: application/json' -d'{
      "doc": {
        "price": 79000
      }
    }'

    # 5. 문서 삭제
    curl -X DELETE "localhost:9200/products/_doc/1"

## 자주 하는 실수

**1. 매핑을 무시하고 데이터 삽입하기**
- 문제: 동적 매핑으로 인해 예상치 못한 타입 변환이 발생합니다.
- 해결: 인덱스 생성 시 명확한 매핑을 정의하세요.

**2. 모든 필드를 text로 설정하기**
- 문제: 정확한 매칭이 필요한 필드(ID, 카테고리)까지 분석되어 검색 성능이 저하됩니다.
- 해결: 정확한 매칭이 필요하면 `keyword` 타입을 사용하세요.

**3. 샤드 개수를 무분별하게 늘리기**
- 문제: 샤드가 많을수록 오버헤드가 증가하고 검색 속도가 느려집니다.
- 해결: 데이터 크기와 쿼리 패턴에 맞게 샤드를 설정하세요(일반적으로 1-5개).

**4. 인덱스 삭제 후 복구 불가능**
- 문제: 실수로 인덱스를 삭제하면 데이터가 완전히 사라집니다.
- 해결: 중요한 인덱스는 백업을 유지하고, 삭제 전 확인 절차를 거치세요.

## 오늘의 실습 체크리스트

- [ ] Elasticsearch 설치 및 실행 확인 (curl -X GET "localhost:9200")
- [ ] 간단한 인덱스 생성하기
- [ ] 샘플 문서 3개 이상 삽입하기
- [ ] match 쿼리로 검색 테스트하기
- [ ] term 쿼리와 match 쿼리의 차이 이해하기
- [ ] 문서 업데이트 및 삭제 작업 수행하기
- [ ] Kibana Dev Tools에서 위 작업들을 반복하기
