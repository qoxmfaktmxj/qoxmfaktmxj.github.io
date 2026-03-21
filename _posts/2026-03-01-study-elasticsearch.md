---
layout: post
title: "Elasticsearch 샤드와 레플리카 설계: 확장성과 가용성의 균형"
date: 2026-03-01 10:13:22 +0900
categories: [data-infra]
tags: [study, elasticsearch, shard, replica, cluster, infra]
---

## 왜 샤드/레플리카를 따로 배워야 할까?

Elasticsearch를 처음 도입할 때는 검색 쿼리보다 인덱스 구조에 더 큰 실수가 나옵니다. 특히 샤드 수를 아무 생각 없이 늘리거나, 레플리카 수를 환경과 맞지 않게 설정하면 성능과 운영 안정성이 동시에 나빠집니다.

## 핵심 개념

- **Primary Shard**
  실제 데이터를 저장하는 기본 샤드입니다.
- **Replica Shard**
  Primary의 복제본입니다. 장애 대응과 읽기 확장에 사용됩니다.
- **Shard 수가 많을 때 문제**
  메타데이터/메모리/관리 비용이 증가합니다.
- **Replica 수가 많을 때 문제**
  쓰기 비용과 저장 공간 사용량이 증가합니다.

## 기본 원칙

1. 작은 인덱스에 샤드를 과도하게 나누지 말 것
2. 단일 노드 개발 환경에서는 replica를 0으로 둘 것
3. 고가용성이 필요한 운영 환경에서는 replica를 최소 1 이상 둘 것
4. 샤드 수는 데이터 증가량과 노드 수를 같이 보고 결정할 것

## 개발 환경 예시

```bash
curl -X PUT "localhost:9200/logs_dev"   -H 'Content-Type: application/json' -d'
{
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 0
  }
}'
```

## 운영 환경 예시

```bash
curl -X PUT "localhost:9200/logs_prod"   -H 'Content-Type: application/json' -d'
{
  "settings": {
    "number_of_shards": 3,
    "number_of_replicas": 1
  }
}'
```

## 샤드 상태 확인

```bash
curl -X GET "localhost:9200/_cat/shards?v"
```

## 노드 상태 확인

```bash
curl -X GET "localhost:9200/_cat/nodes?v"
```

## 실무 판단 기준

### 언제 샤드를 늘릴까?
- 단일 샤드 크기가 너무 커져 복구/재배치 시간이 부담될 때
- 병렬 검색 처리량이 부족할 때
- 노드 수가 늘어나고 데이터를 더 고르게 분산해야 할 때

### 언제 레플리카를 늘릴까?
- 읽기 부하가 매우 높을 때
- 노드 장애 시 서비스 연속성이 중요할 때

## 흔한 실수

- "무조건 샤드 많을수록 좋다"고 생각함
- 단일 노드인데 replica를 1로 둬서 yellow 상태를 방치함
- 데이터 증가량 예측 없이 인덱스를 생성함
- 운영 중 샤드 전략 변경 비용을 과소평가함

## 한 줄 정리

샤드와 레플리카는 성능 튜닝 옵션이 아니라, **클러스터 비용·복구성·확장성을 함께 결정하는 운영 설계값**입니다.
