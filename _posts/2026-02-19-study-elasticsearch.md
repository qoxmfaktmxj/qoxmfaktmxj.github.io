---
layout: post
title: "Elasticsearch 역색인과 Analyzer 실전: 검색 품질을 결정하는 핵심"
date: 2026-02-19 10:08:56 +0900
categories: [data-infra]
tags: [study, elasticsearch, analyzer, inverted-index, search, infra]
---

## 왜 이 주제가 중요한가?

Elasticsearch를 도입한 뒤 검색 결과가 기대와 다르게 나오는 경우가 많습니다. 원인은 대개 **역색인 구조와 Analyzer 동작을 제대로 이해하지 못한 상태에서 기본값만 사용했기 때문**입니다.

검색 품질은 단순히 데이터를 많이 넣는다고 좋아지지 않습니다. 어떤 토큰으로 쪼개고, 어떤 필드를 `text`로 볼지 `keyword`로 볼지, 검색 시 어떤 분석 규칙을 적용할지가 훨씬 중요합니다.

## 핵심 개념

- **역색인(Inverted Index)**
  문서 중심이 아니라 "단어 → 문서" 방향으로 저장하는 구조입니다.
  전문 검색이 빠른 이유는 전체 문서를 훑지 않고 토큰별 색인만 조회하기 때문입니다.

- **Analyzer**
  텍스트를 색인 가능한 단위로 변환하는 파이프라인입니다.
  `character filter → tokenizer → token filter` 순서로 작동합니다.

- **text vs keyword**
  `text`는 토큰화되어 전문검색에 적합하고,
  `keyword`는 정확히 같은 값 비교/집계/정렬에 적합합니다.

- **검색 품질의 본질**
  사용자가 입력하는 표현과 색인된 토큰이 얼마나 잘 맞아떨어지느냐가 핵심입니다.

## 실무 예시: 상품 검색 인덱스 설계

```bash
curl -X PUT "localhost:9200/products_v2"   -H 'Content-Type: application/json' -d'
{
  "settings": {
    "analysis": {
      "analyzer": {
        "product_name_analyzer": {
          "tokenizer": "standard",
          "filter": ["lowercase"]
        }
      }
    }
  },
  "mappings": {
    "properties": {
      "name": {
        "type": "text",
        "analyzer": "product_name_analyzer",
        "fields": {
          "raw": { "type": "keyword" }
        }
      },
      "brand": { "type": "keyword" },
      "price": { "type": "integer" },
      "description": { "type": "text" }
    }
  }
}'
```

위 설계의 포인트는 `name`을 두 가지 방식으로 동시에 쓰는 것입니다.

- `name`: 전문검색
- `name.raw`: 정렬/정확 일치/집계

## Analyzer 확인 방법

```bash
curl -X POST "localhost:9200/products_v2/_analyze"   -H 'Content-Type: application/json' -d'
{
  "analyzer": "product_name_analyzer",
  "text": "Apple AirPods Pro 2"
}'
```

이 API는 실제로 텍스트가 어떤 토큰으로 잘리는지 확인할 때 매우 유용합니다.

## 검색 예시

```bash
curl -X GET "localhost:9200/products_v2/_search"   -H 'Content-Type: application/json' -d'
{
  "query": {
    "match": {
      "name": "airpods"
    }
  }
}'
```

## 흔한 실수

- 모든 필드를 `text`로 설정해서 집계/정렬이 깨짐
- 코드값/카테고리 같은 필드를 `keyword`로 두지 않음
- 한국어/영문 검색 특성을 고려하지 않고 기본 Analyzer만 사용
- `_analyze` API로 토큰을 확인하지 않고 감으로 튜닝

## 실무 체크리스트

- [ ] 검색 필드와 집계 필드를 분리했는가?
- [ ] `text`/`keyword`를 용도에 맞게 나눴는가?
- [ ] `_analyze`로 실제 토큰을 검증했는가?
- [ ] 검색 결과가 왜 그렇게 나오는지 설명 가능한가?

## 한 줄 정리

Elasticsearch 검색 품질의 절반 이상은 **쿼리보다 색인 설계와 Analyzer 선택**에서 결정됩니다.
