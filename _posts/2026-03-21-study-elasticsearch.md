---
layout: post
title: "Elasticsearch Query DSL 실전: bool, filter, aggregation 제대로 쓰기"
date: 2026-03-21 10:02:24 +0900
categories: [data-infra]
tags: [study, elasticsearch, query-dsl, aggregation, filter, infra]
---

## 왜 Query DSL을 따로 배워야 할까?

Elasticsearch를 도입한 팀이 가장 자주 겪는 문제 중 하나는 "검색은 되는데 결과가 이상하다"는 것입니다. 대부분은 Query DSL의 의도를 구분하지 못해서 생깁니다.

특히 `must`, `should`, `filter`, `aggregation`을 섞어 쓸 때 의미를 잘못 이해하면 정확도와 성능이 동시에 무너집니다.

## 핵심 개념

- **must**
  반드시 만족해야 하고, score 계산에도 반영됩니다.
- **filter**
  반드시 만족해야 하지만 score 계산에는 반영되지 않습니다.
  캐시 효율이 좋아 성능상 유리합니다.
- **should**
  만족하면 점수를 올리는 조건입니다.
- **aggregation**
  검색 결과를 요약/집계하는 기능입니다.

## 실전 예시: 상품 검색 + 필터 + 집계

```bash
curl -X GET "localhost:9200/products/_search"   -H 'Content-Type: application/json' -d'
{
  "query": {
    "bool": {
      "must": [
        { "match": { "name": "airpods" } }
      ],
      "filter": [
        { "term": { "brand": "apple" } },
        { "range": { "price": { "lte": 400000 } } }
      ]
    }
  },
  "aggs": {
    "by_category": {
      "terms": { "field": "category.keyword" }
    }
  }
}'
```

## 이 쿼리의 의미

- 이름은 `airpods`와 관련성이 있어야 함
- 브랜드는 `apple`이어야 함
- 가격은 40만원 이하여야 함
- 결과와 함께 카테고리 집계도 같이 뽑음

## 왜 filter를 따로 빼야 하나?

브랜드나 가격 제한은 관련도(score)를 높이는 조건이 아니라, 단순한 제약 조건입니다. 이걸 `must`에 넣으면 불필요하게 점수 계산에 포함되어 비효율적일 수 있습니다.

## 흔한 실수

- 정확 일치가 필요한데 `match`를 사용함
- 집계용 필드에 `text` 타입을 그대로 사용함
- `filter`로 처리할 조건까지 전부 `must`에 넣음
- 검색 정확도 문제를 쿼리보다 색인 문제로 봐야 하는데 놓침

## 한 줄 정리

Elasticsearch Query DSL의 핵심은 "조건을 많이 쓰는 것"이 아니라, **관련도 계산 조건과 필터 조건을 정확히 분리하는 것**입니다.
