---
layout: post
title: "Elasticsearch 매핑과 인덱스 템플릿 실전: 스키마 폭주를 막는 법"
date: 2026-03-10 10:01:13 +0900
categories: [data-infra]
tags: [study, elasticsearch, mapping, index-template, schema, infra]
---

## 왜 매핑 설계가 중요한가?

Elasticsearch를 쓰다 보면 초기에는 빠르게 붙지만, 시간이 지나면 필드 타입 충돌과 동적 매핑 남용 때문에 운영이 어려워집니다. 이 문제는 대부분 **처음부터 매핑과 템플릿을 명시적으로 관리하지 않았기 때문**입니다.

## 핵심 개념

- **Mapping**
  각 필드의 타입과 검색 방식을 정의합니다.
- **Dynamic Mapping**
  문서가 들어올 때 Elasticsearch가 자동으로 필드 타입을 추론합니다.
- **Index Template**
  특정 패턴의 인덱스에 공통 설정/매핑을 자동 적용합니다.

## 로그 인덱스 템플릿 예제

```bash
curl -X PUT "localhost:9200/_index_template/app_logs_template"   -H 'Content-Type: application/json' -d'
{
  "index_patterns": ["app-logs-*"] ,
  "template": {
    "settings": {
      "number_of_shards": 1,
      "number_of_replicas": 0
    },
    "mappings": {
      "dynamic": "strict",
      "properties": {
        "timestamp": { "type": "date" },
        "level": { "type": "keyword" },
        "service": { "type": "keyword" },
        "message": { "type": "text" },
        "trace_id": { "type": "keyword" }
      }
    }
  }
}'
```

## 왜 `dynamic: strict`가 유용한가?

로그나 이벤트 수집 시스템에서는 잘못된 필드가 무한정 들어오며 스키마를 오염시키는 경우가 많습니다. `strict`로 두면 의도하지 않은 필드 유입을 초기에 차단할 수 있습니다.

## 템플릿이 적용된 인덱스 생성

```bash
curl -X PUT "localhost:9200/app-logs-2026.03.10"
```

## 매핑 확인

```bash
curl -X GET "localhost:9200/app-logs-2026.03.10/_mapping"
```

## 실무 팁

- 로그/이벤트 인덱스는 템플릿 없이 운영하지 말 것
- 날짜, 코드, enum 값은 `keyword`/`date`를 명확히 지정할 것
- 검색용 본문만 `text`로 둘 것
- 동적 필드 허용 범위를 최소화할 것

## 흔한 실수

- 모든 신규 필드를 자동 생성에 맡김
- 숫자가 문자열로 들어와도 그냥 넘어감
- 로그 인덱스가 서비스별로 제멋대로 커짐
- Kibana에서 보이기만 하면 괜찮다고 생각함

## 한 줄 정리

Elasticsearch 매핑은 단순 스키마가 아니라, **검색 품질과 운영 안정성을 동시에 지키는 계약**입니다.
