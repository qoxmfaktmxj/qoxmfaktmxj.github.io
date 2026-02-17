---
layout: post
title: "Elasticsearch 기초: 검색 엔진의 핵심 원리와 실무 활용"
date: 2026-02-17 10:00:00 +0900
categories: [data-infra]
tags: [study, elasticsearch, search, infra, automation]
---

## 왜 Elasticsearch를 알아야 할까?

대부분의 서비스에서 검색 기능은 핵심입니다. RDBMS의 `LIKE` 검색은 데이터가 커지면 성능이 급격히 떨어집니다. Elasticsearch는 역색인(Inverted Index) 구조를 사용해 수억 건의 데이터에서도 밀리초 단위 검색이 가능합니다. 로그 분석, 모니터링, 상품 검색, 자동완성 등 실무에서 폭넓게 사용됩니다.

## 핵심 개념

- **역색인(Inverted Index)**: 문서 내 각 단어가 어떤 문서에 포함되어 있는지를 미리 매핑해두는 구조입니다. 책의 뒷편 색인과 동일한 원리로, 전체 문서를 스캔하지 않고도 빠른 검색이 가능합니다.
- **Index / Document / Field**: RDBMS의 테이블-행-열과 대응됩니다. Index는 문서들의 모음이고, Document는 JSON 형태의 개별 데이터, Field는 Document 내의 각 키-값 쌍입니다.
- **Mapping**: 각 Field의 데이터 타입을 정의합니다. `text` 타입은 분석기를 통해 토큰화되어 전문검색이 가능하고, `keyword` 타입은 정확한 일치 검색에 사용됩니다.
- **Analyzer**: 텍스트를 색인 가능한 토큰으로 변환하는 파이프라인입니다. Character Filter → Tokenizer → Token Filter 순서로 처리되며, 한국어의 경우 `nori` 분석기를 사용합니다.
- **Sharding & Replication**: 데이터를 여러 샤드로 분산 저장하여 수평 확장이 가능하고, 레플리카를 통해 장애 시에도 데이터를 보존합니다.

## 실습 예제

### 인덱스 생성 및 문서 색인

```bash
# 인덱스 생성 (매핑 정의)
curl -X PUT "localhost:9200/products" -H 'Content-Type: application/json' -d'
{
  "mappings": {
    "properties": {
      "name":        { "type": "text", "analyzer": "standard" },
      "category":    { "type": "keyword" },
      "price":       { "type": "integer" },
      "description": { "type": "text" },
      "created_at":  { "type": "date" }
    }
  }
}'

# 문서 색인
curl -X POST "localhost:9200/products/_doc" -H 'Content-Type: application/json' -d'
{
  "name": "무선 블루투스 이어폰",
  "category": "electronics",
  "price": 45000,
  "description": "노이즈 캔슬링 지원 무선 이어폰",
  "created_at": "2026-02-17"
}'
```

### 검색 쿼리

```bash
# 전문 검색 (match)
curl -X GET "localhost:9200/products/_search" -H 'Content-Type: application/json' -d'
{
  "query": {
    "match": {
      "name": "블루투스 이어폰"
    }
  }
}'

# 복합 조건 검색 (bool query)
curl -X GET "localhost:9200/products/_search" -H 'Content-Type: application/json' -d'
{
  "query": {
    "bool": {
      "must":   [{ "match": { "name": "이어폰" }}],
      "filter": [{ "range": { "price": { "lte": 50000 }}}]
    }
  }
}'
```

### Python 클라이언트 활용

```python
from elasticsearch import Elasticsearch

es = Elasticsearch("http://localhost:9200")

# 문서 색인
es.index(index="products", document={
    "name": "기계식 키보드",
    "category": "electronics",
    "price": 89000,
    "description": "적축 기계식 키보드"
})

# 검색
result = es.search(index="products", query={
    "bool": {
        "must": [{"match": {"description": "키보드"}}],
        "filter": [{"term": {"category": "electronics"}}]
    }
})

for hit in result["hits"]["hits"]:
    print(hit["_source"]["name"], hit["_score"])
```

## 흔한 실수

- **Mapping 없이 색인 시작**: Dynamic mapping에 의존하면 `text`여야 할 필드가 `keyword`로 잡히거나 그 반대가 됩니다. 운영 환경에서는 반드시 명시적으로 매핑을 정의하세요.
- **match와 term 혼동**: `text` 필드에는 `match`, `keyword` 필드에는 `term`을 사용해야 합니다. `text` 필드에 `term` 쿼리를 쓰면 분석기를 거치지 않아 검색이 안 됩니다.
- **샤드 수 과다 설정**: 샤드당 오버헤드가 존재하므로 작은 인덱스에 샤드를 많이 설정하면 오히려 성능이 저하됩니다. 단일 샤드 크기가 10~50GB 범위가 되도록 설계하세요.
- **score 기반 정렬과 filter 미활용**: 점수가 필요 없는 조건(카테고리, 날짜 범위 등)은 `filter` 컨텍스트에 넣어야 캐싱이 되고 성능이 좋아집니다.

## 하루 실습 체크리스트

- [ ] Docker로 Elasticsearch 단일 노드 실행하기
- [ ] 인덱스 생성 시 매핑을 직접 정의하고 문서 3개 이상 색인하기
- [ ] `match`, `term`, `bool` 쿼리를 각각 실행해보고 결과 비교하기
- [ ] `_analyze` API로 텍스트가 어떻게 토큰화되는지 확인하기
- [ ] Python `elasticsearch` 라이브러리로 색인과 검색을 코드로 작성하기
