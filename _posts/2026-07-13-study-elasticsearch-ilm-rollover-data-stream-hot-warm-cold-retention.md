---
layout: post
title: "Elasticsearch ILM 실전: Rollover, Data Stream, Hot-Warm-Cold, Retention으로 로그 인덱스를 오래 운영하는 법"
date: 2026-07-13 11:50:00 +0900
categories: [data-infra]
tags: [study, data-infra, elasticsearch, ilm, rollover, data-stream, hot-warm-cold, retention, shard, operations]
permalink: /data-infra/2026/07/13/study-elasticsearch-ilm-rollover-data-stream-hot-warm-cold-retention.html
---

## 배경: 검색은 잘 되는데 클러스터가 점점 무거워지는 이유

Elasticsearch를 로그, 이벤트, 검색 보조 저장소로 붙이는 일은 어렵지 않다. 처음에는 인덱스를 하나 만들고 문서를 넣고, Kibana나 API로 검색하면 된다.

```bash
curl -X PUT "localhost:9200/app-logs-2026.07.13" \
  -H 'Content-Type: application/json' \
  -d '{
    "mappings": {
      "properties": {
        "@timestamp": { "type": "date" },
        "service": { "type": "keyword" },
        "level": { "type": "keyword" },
        "message": { "type": "text" },
        "trace_id": { "type": "keyword" }
      }
    }
  }'
```

문제는 운영 3개월 뒤부터 시작된다.

- 인덱스가 하루에 하나씩 늘어났는데 shard 수가 수천 개가 된다.
- 오래된 로그는 거의 보지 않지만 hot node의 disk와 heap을 계속 잡아먹는다.
- daily index를 쓰는데 어떤 날은 3GB, 어떤 날은 180GB라 shard 크기가 들쭉날쭉하다.
- retention 삭제 job이 실패해도 아무도 모르다가 disk watermark에 걸린다.
- 새 인덱스에는 template이 적용되지 않아 mapping이 깨지고 검색 쿼리가 실패한다.
- alias를 잘못 바꿔 write가 구 인덱스로 들어간다.
- rollover 조건을 문서 수로만 잡아 큰 문서가 몰린 날 shard가 과도하게 커진다.
- cold tier로 옮긴 뒤에도 대시보드가 같은 쿼리를 날려 사용자 체감이 나빠진다.
- 삭제는 자동화했지만 snapshot, 감사 보존, 법적 보존 기간과 맞지 않는다.

Elasticsearch에서 로그성 데이터의 어려움은 "검색 쿼리 하나를 빠르게 만드는 것"보다 **계속 들어오는 데이터를 어떤 크기로 자르고, 어떤 노드에 두고, 언제 읽기 전용으로 바꾸고, 언제 버릴 것인가**에 있다.

이 문제를 다루는 핵심 도구가 ILM(Index Lifecycle Management), rollover, data stream, hot-warm-cold tier, retention이다.

오늘 글은 ILM 설정 예제를 복사하는 글이 아니다. 중급 이상 개발자와 운영자가 Elasticsearch를 장기 운영할 때 반드시 정해야 하는 기준을 정리한다.

이번 글에서 답하려는 질문은 아래와 같다.

1. daily index와 rollover는 무엇이 다르고 언제 바꿔야 하는가?
2. ILM phase는 hot, warm, cold, frozen, delete를 어떤 운영 의미로 나누는가?
3. data stream은 alias 기반 write index보다 무엇을 더 안전하게 만드는가?
4. shard 크기, rollover 조건, retention 기간은 어떤 순서로 결정해야 하는가?
5. hot-warm-cold tier를 넣으면 비용은 줄지만 어떤 쿼리와 운영 복잡도가 생기는가?
6. index template, component template, ingest pipeline, mapping 변경은 lifecycle과 어떻게 연결되는가?
7. 흔한 실수와 배포 전 체크리스트는 무엇인가?

결론부터 말하면 이렇다.

**Elasticsearch ILM의 핵심은 오래된 인덱스를 자동 삭제하는 기능이 아니라, 데이터의 쓰기 경로, 조회 빈도, 저장 비용, 복구 시간, 보존 정책을 인덱스 단위의 운영 계약으로 만드는 것이다.**

---

## 먼저 큰 그림: Elasticsearch 로그 운영은 인덱스 생명주기 문제다

로그와 이벤트 데이터는 보통 append-only에 가깝다.

- 지금 들어온 문서는 계속 추가된다.
- 과거 문서는 거의 수정하지 않는다.
- 최근 1시간 또는 24시간 데이터는 자주 본다.
- 7일 전 데이터는 장애 분석 때만 본다.
- 90일 전 데이터는 감사나 보안 조사 때만 본다.
- 일정 기간이 지나면 삭제하거나 외부 archive로 넘긴다.

이런 데이터는 OLTP 테이블처럼 "하나의 큰 테이블을 계속 업데이트"하는 모델보다 시간 단위로 잘라서 운영하는 편이 자연스럽다. Elasticsearch에서는 이 단위가 인덱스다.

```text
app-logs-000001  -> 과거 write index
app-logs-000002  -> 과거 write index
app-logs-000003  -> 현재 write index
```

인덱스 생명주기는 대략 이렇게 흘러간다.

```text
생성
  -> write 대상
  -> rollover로 새 write index 생성
  -> 이전 인덱스 read-only
  -> warm tier로 이동
  -> force merge 또는 replica 조정
  -> cold tier로 이동
  -> snapshot 기반 보관 또는 검색 빈도 낮춤
  -> retention 만료 후 delete
```

ILM은 이 흐름을 정책으로 만든다.

```json
{
  "policy": {
    "phases": {
      "hot": {
        "actions": {
          "rollover": {
            "max_primary_shard_size": "40gb",
            "max_age": "1d"
          }
        }
      },
      "warm": {
        "min_age": "2d",
        "actions": {
          "forcemerge": { "max_num_segments": 1 },
          "shrink": { "number_of_shards": 1 }
        }
      },
      "delete": {
        "min_age": "30d",
        "actions": {
          "delete": {}
        }
      }
    }
  }
}
```

이 설정만 보면 단순해 보인다. 하지만 실제 판단은 설정 바깥에 있다.

- 왜 primary shard 크기를 40GB로 잡았는가?
- `max_age`와 `max_primary_shard_size` 중 어느 조건이 먼저 발동될 것인가?
- warm phase에서 shrink가 가능한 shard 배치 조건이 만족되는가?
- force merge가 hot write 성능에 영향을 주지 않는가?
- 30일 삭제가 보안, 감사, 고객 계약과 맞는가?
- delete 전에 snapshot이 완료됐는지 보장하는가?
- 검색 대시보드는 warm/cold 인덱스까지 기본 조회하는가?

ILM은 좋은 기본값이 아니라, 팀이 데이터 생명주기를 명시적으로 정했다는 증거여야 한다.

---

## 핵심 개념 1: Daily Index는 단순하지만 데이터 크기 변동에 약하다

가장 흔한 시작점은 daily index다.

```text
app-logs-2026.07.11
app-logs-2026.07.12
app-logs-2026.07.13
```

장점은 분명하다.

- 사람이 이해하기 쉽다.
- 날짜별 삭제가 쉽다.
- 특정 날짜 장애 분석이 직관적이다.
- index pattern으로 대시보드를 만들기 쉽다.
- 초반에는 ILM 없이도 cron job으로 관리할 수 있다.

하지만 daily index는 날짜가 곧 크기라는 가정을 깔고 있다. 운영에서는 이 가정이 자주 깨진다.

예를 들어 평소에는 하루 20GB 로그가 들어오지만, 장애가 난 날에는 같은 로그가 200GB 들어올 수 있다. daily index를 고정하면 어떤 날은 shard가 너무 작고, 어떤 날은 shard가 너무 커진다.

```text
정상일
  app-logs-2026.07.11
  primary shard 5개
  shard당 4GB

장애일
  app-logs-2026.07.12
  primary shard 5개
  shard당 40GB

폭주일
  app-logs-2026.07.13
  primary shard 5개
  shard당 120GB
```

Elasticsearch에서 shard는 너무 작아도 문제고 너무 커도 문제다.

너무 작은 shard가 많으면:

- cluster state가 커진다.
- master node 부담이 커진다.
- query fan-out이 늘어난다.
- heap overhead가 증가한다.
- file descriptor와 segment 관리 비용이 늘어난다.

너무 큰 shard가 생기면:

- recovery와 relocation 시간이 길어진다.
- force merge와 snapshot 시간이 길어진다.
- hot node disk pressure가 커진다.
- 장애 시 한 shard를 옮기는 단위가 너무 무거워진다.
- query 하나가 특정 shard에서 오래 걸릴 수 있다.

따라서 daily index는 "하루 데이터 크기가 안정적이고, retention도 날짜 단위이며, shard 크기가 적절하게 유지되는 동안"에는 좋다. 반대로 데이터 양이 크게 흔들리거나, 서비스별 로그량 편차가 크거나, burst가 잦다면 rollover가 더 자연스럽다.

---

## 핵심 개념 2: Rollover는 날짜가 아니라 크기와 시간 조건으로 write index를 교체한다

Rollover는 현재 write index가 특정 조건을 만족하면 새 write index를 만들고 쓰기 대상을 바꾸는 방식이다.

```text
app-logs-000001  -> rollover 조건 만족
app-logs-000002  -> 새 write index
```

대표 조건은 아래와 같다.

- `max_primary_shard_size`
- `max_size`
- `max_docs`
- `max_age`
- `min_docs`

실무에서는 보통 `max_primary_shard_size`와 `max_age`를 함께 쓴다.

```json
{
  "rollover": {
    "max_primary_shard_size": "40gb",
    "max_age": "1d"
  }
}
```

이 의미는 "하루가 지나거나 primary shard 하나가 40GB에 도달하면 새 인덱스로 넘긴다"에 가깝다.

중요한 점은 rollover가 daily index보다 무조건 좋은 것이 아니라는 것이다. rollover는 인덱스 크기를 안정화하는 대신 이름과 시간 경계가 느슨해진다.

```text
app-logs-000124
  포함 범위: 2026-07-13 00:00:00 ~ 2026-07-13 18:24:11

app-logs-000125
  포함 범위: 2026-07-13 18:24:12 ~ 2026-07-14 09:10:03
```

날짜와 인덱스가 1:1로 맞지 않는다. 따라서 조회는 인덱스 이름이 아니라 `@timestamp` 필터와 data stream/index pattern을 기준으로 해야 한다.

### Rollover 조건을 정하는 순서

롤오버 조건은 감으로 정하면 안 된다. 보통 아래 순서가 좋다.

1. 목표 primary shard 크기를 정한다.
2. 하루 또는 시간당 ingest 양을 측정한다.
3. primary shard 수를 정한다.
4. 목표 shard 크기에 도달하는 시간을 계산한다.
5. 검색 대시보드의 시간 범위와 retention 단위를 맞춘다.
6. burst가 있을 때 어느 조건이 먼저 발동될지 검증한다.

예를 들어 하루 600GB 로그가 들어오고 primary shard 목표를 40GB로 잡는다고 하자.

```text
하루 ingest: 600GB
목표 shard 크기: 40GB
필요 primary shard-day: 600 / 40 = 15
```

하루에 인덱스 하나를 만들고 primary shard 15개를 둘 수도 있다. 하지만 shard 15개짜리 인덱스가 매일 생기는 것이 query fan-out과 운영에 맞는지 봐야 한다.

다른 선택도 가능하다.

```text
primary shard 5개
rollover 목표: primary shard 40GB
인덱스 하나의 총 primary data: 5 * 40GB = 200GB
하루 600GB라면 하루 약 3회 rollover
```

이 방식은 인덱스 수는 늘지만 shard 크기가 안정적이다. 검색은 최근 24시간 기준으로 약 3개 인덱스에 fan-out된다. 팀이 감당 가능한 query pattern인지 확인해야 한다.

### `max_docs`보다 shard size를 우선해야 하는 이유

문서 수는 직관적이지만 로그에서는 위험할 수 있다. 문서 하나가 500B일 때와 20KB일 때 같은 `max_docs`는 전혀 다른 shard 크기를 만든다.

```text
10억 docs * 500B  -> 약 500GB raw 전후
10억 docs * 20KB  -> 약 20TB raw 전후
```

물론 압축과 mapping에 따라 실제 크기는 달라진다. 그래도 운영 관점에서 disk, recovery, snapshot, merge 비용은 문서 수보다 byte size에 더 가깝다. 그래서 rollover 기준은 보통 `max_primary_shard_size`를 중심으로 잡고, `max_age`로 시간 상한을 둔다.

---

## 핵심 개념 3: Data Stream은 시계열 write path를 안전하게 표준화한다

Elasticsearch 7.9 이후 시계열 데이터에는 data stream을 우선 고려할 수 있다. Data stream은 여러 backing index를 하나의 논리 이름으로 감싸고, 현재 write index를 자동 관리한다.

```text
data stream: logs-app-default

backing indices:
  .ds-logs-app-default-2026.07.11-000001
  .ds-logs-app-default-2026.07.12-000002
  .ds-logs-app-default-2026.07.13-000003  <- write index
```

data stream을 쓰려면 기본적으로 `@timestamp` 필드가 필요하고, index template에 data stream 설정이 들어가야 한다.

```bash
curl -X PUT "localhost:9200/_ilm/policy/logs-app-ilm" \
  -H 'Content-Type: application/json' \
  -d '{
    "policy": {
      "phases": {
        "hot": {
          "actions": {
            "rollover": {
              "max_primary_shard_size": "40gb",
              "max_age": "1d"
            }
          }
        },
        "delete": {
          "min_age": "30d",
          "actions": { "delete": {} }
        }
      }
    }
  }'
```

```bash
curl -X PUT "localhost:9200/_index_template/logs-app-template" \
  -H 'Content-Type: application/json' \
  -d '{
    "index_patterns": ["logs-app-*"],
    "data_stream": {},
    "template": {
      "settings": {
        "index.lifecycle.name": "logs-app-ilm",
        "number_of_shards": 3,
        "number_of_replicas": 1
      },
      "mappings": {
        "properties": {
          "@timestamp": { "type": "date" },
          "service": { "type": "keyword" },
          "level": { "type": "keyword" },
          "trace_id": { "type": "keyword" },
          "message": { "type": "text" }
        }
      }
    }
  }'
```

```bash
curl -X POST "localhost:9200/logs-app-default/_doc" \
  -H 'Content-Type: application/json' \
  -d '{
    "@timestamp": "2026-07-13T02:50:00Z",
    "service": "checkout",
    "level": "ERROR",
    "trace_id": "8e4a...",
    "message": "payment gateway timeout"
  }'
```

Data stream의 장점은 아래와 같다.

- write index 교체를 직접 alias로 관리하지 않아도 된다.
- rollover와 backing index 관리가 자연스럽다.
- 시계열 데이터라는 의도가 구조에 드러난다.
- `@timestamp` 기반 데이터 모델을 강제하기 쉽다.
- Elastic Agent, Beats, 로그 파이프라인과 궁합이 좋다.

하지만 모든 데이터에 맞는 것은 아니다. Data stream은 append 중심 시계열에 적합하다. 기존 문서를 자주 업데이트하거나 delete-by-query를 자주 돌리거나, custom routing과 복잡한 alias 전략이 필요하면 일반 index + alias가 더 맞을 수 있다.

실무 기준은 이렇게 잡을 수 있다.

| 데이터 성격 | 권장 방식 | 이유 |
| --- | --- | --- |
| 애플리케이션 로그 | data stream | append-only, timestamp 중심, rollover 적합 |
| metric | data stream | 시계열, retention 명확 |
| 보안 이벤트 | data stream | 장기 보존과 tier 이동 필요 |
| 상품 검색 색인 | 일반 index + alias | 재색인, 업데이트, 검색 alias 전략 중요 |
| 사용자 프로필 색인 | 일반 index | document update가 많음 |
| 이벤트 원장 | 경우에 따라 다름 | append-only지만 audit, delete 정책 제약 확인 필요 |

---

## 핵심 개념 4: ILM phase는 저장 비용이 아니라 조회 계약을 바꾸는 단계다

ILM phase를 단순히 "hot은 비싼 디스크, cold는 싼 디스크"로 이해하면 반만 맞다. phase 변경은 조회 성능, 복구 시간, merge 정책, replica 수, snapshot 전략까지 바꾸는 운영 계약이다.

### Hot phase

Hot phase는 현재 쓰기가 들어오는 단계다.

주요 특징:

- write load가 있다.
- refresh, segment 생성, merge가 활발하다.
- 최근 대시보드와 알림 쿼리가 집중된다.
- indexing throughput과 search latency를 동시에 봐야 한다.
- rollover 조건이 중요하다.

Hot tier에는 보통 빠른 SSD와 충분한 CPU/heap을 둔다. 여기서 무리한 force merge나 shrink를 하면 쓰기 성능을 해칠 수 있다.

### Warm phase

Warm phase는 더 이상 쓰지 않지만 비교적 자주 조회되는 단계다.

예시:

- 최근 2일~14일 로그
- 장애 사후 분석에 자주 쓰이는 범위
- 대시보드 기본 기간에는 잘 안 걸리지만 검색 요청은 종종 오는 범위

Warm phase에서는 아래 작업을 고려한다.

- read-only 전환
- force merge
- shrink
- replica 수 조정
- allocation tier 이동

```json
{
  "warm": {
    "min_age": "2d",
    "actions": {
      "readonly": {},
      "forcemerge": { "max_num_segments": 1 },
      "allocate": {
        "include": { "_tier_preference": "data_warm" }
      }
    }
  }
}
```

Force merge는 segment 수를 줄여 검색 비용을 줄일 수 있지만, I/O를 크게 사용한다. 모든 인덱스가 동시에 warm phase에 들어가면 warm node가 merge 작업으로 바빠질 수 있다. 그래서 rollover 주기, phase min_age, node capacity를 함께 봐야 한다.

### Cold phase

Cold phase는 거의 조회하지 않지만 검색 가능 상태로 남겨야 하는 단계다.

예시:

- 30일~90일 보안 로그
- 고객 문의나 감사 요청 때만 보는 이벤트
- 장기 장애 분석용 raw log

Cold tier에서는 비용을 줄이는 대신 검색 latency가 나빠질 수 있다. 사용자가 "90일치 로그 검색"을 아무 생각 없이 대시보드 기본값으로 돌리면 cold tier의 느린 저장소가 쿼리 병목이 된다.

따라서 cold phase를 도입할 때는 UI와 API 계약도 바꿔야 한다.

- 기본 조회 범위는 hot/warm으로 제한한다.
- cold 범위 조회는 명시적 선택으로 둔다.
- 오래 걸릴 수 있다는 UX를 제공한다.
- async search나 background export를 고려한다.
- cold query의 동시 실행 수를 제한한다.

### Delete phase

Delete phase는 retention 만료 후 인덱스를 제거한다. 가장 단순해 보이지만 실무에서는 가장 위험한 단계이기도 하다.

삭제 전에 확인해야 할 질문:

- 법적 보존 기간과 맞는가?
- 고객 계약상 보존 기간과 맞는가?
- 보안 감사 로그는 별도 archive가 필요한가?
- snapshot 완료 여부를 확인하는가?
- delete 실패 시 알림이 있는가?
- 실수로 미래 timestamp가 들어온 문서 때문에 retention 계산이 꼬이지 않는가?

ILM delete는 편하지만 복구 버튼이 아니다. 삭제된 인덱스를 되살리려면 snapshot이 있어야 한다. 따라서 "30일 뒤 삭제"는 "30일 뒤 없어져도 된다"가 아니라, "30일 뒤 Elasticsearch online search 계층에서 제거하고, 필요하면 어디에서 복구할 수 있다"까지 포함해야 한다.

---

## 실무 예시: 애플리케이션 로그용 Data Stream + ILM 설계

가정해보자.

- 서비스 로그가 하루 평균 300GB 들어온다.
- 장애 때는 하루 900GB까지 튈 수 있다.
- 최근 24시간은 알림과 대시보드가 자주 조회한다.
- 최근 14일은 장애 분석에 필요하다.
- 90일은 보안 감사 목적으로 검색 가능해야 한다.
- 180일은 object storage archive로만 보관한다.
- Elasticsearch online cluster에서는 90일 이후 삭제한다.

이 경우 설계는 아래처럼 시작할 수 있다.

### 1. 목표 shard 크기

운영 목표 primary shard 크기를 30~50GB 범위로 잡는다. 여기서는 40GB로 둔다.

```text
평균 300GB/day
primary shard 3개
인덱스 하나의 목표 primary data = 3 * 40GB = 120GB
평균 하루 약 2.5회 rollover

폭주 900GB/day
하루 약 7.5회 rollover
```

평균일에는 하루 2~3개 backing index, 폭주일에는 7~8개 backing index가 생긴다. daily index보다 인덱스 수는 늘 수 있지만 shard 크기가 안정적이다.

### 2. ILM policy

```bash
curl -X PUT "localhost:9200/_ilm/policy/app-logs-90d-policy" \
  -H 'Content-Type: application/json' \
  -d '{
    "policy": {
      "phases": {
        "hot": {
          "actions": {
            "rollover": {
              "max_primary_shard_size": "40gb",
              "max_age": "12h"
            }
          }
        },
        "warm": {
          "min_age": "2d",
          "actions": {
            "readonly": {},
            "forcemerge": { "max_num_segments": 1 },
            "allocate": {
              "include": {
                "_tier_preference": "data_warm"
              }
            }
          }
        },
        "cold": {
          "min_age": "14d",
          "actions": {
            "allocate": {
              "include": {
                "_tier_preference": "data_cold"
              }
            }
          }
        },
        "delete": {
          "min_age": "90d",
          "actions": {
            "delete": {}
          }
        }
      }
    }
  }'
```

`max_age: 12h`는 트래픽이 낮은 날에도 write index가 너무 오래 열려 있지 않게 하는 상한이다. 하지만 이 값은 조직마다 달라진다. 하루 단위 운영이 더 중요하면 `1d`가 나을 수 있다.

### 3. Component template

공통 settings와 mappings를 component template로 분리하면 여러 로그 스트림이 같은 규칙을 공유하기 쉽다.

```bash
curl -X PUT "localhost:9200/_component_template/app-logs-settings" \
  -H 'Content-Type: application/json' \
  -d '{
    "template": {
      "settings": {
        "index.lifecycle.name": "app-logs-90d-policy",
        "number_of_shards": 3,
        "number_of_replicas": 1,
        "index.codec": "best_compression"
      }
    }
  }'
```

```bash
curl -X PUT "localhost:9200/_component_template/app-logs-mappings" \
  -H 'Content-Type: application/json' \
  -d '{
    "template": {
      "mappings": {
        "dynamic": false,
        "properties": {
          "@timestamp": { "type": "date" },
          "service": { "type": "keyword" },
          "environment": { "type": "keyword" },
          "level": { "type": "keyword" },
          "trace_id": { "type": "keyword" },
          "span_id": { "type": "keyword" },
          "logger": { "type": "keyword" },
          "message": { "type": "text" },
          "error.type": { "type": "keyword" },
          "error.stack_trace": { "type": "text", "index": false }
        }
      }
    }
  }'
```

여기서 `dynamic: false`는 의도하지 않은 필드 폭주를 막기 위한 선택이다. 로그는 필드가 쉽게 늘어난다. 사용자 agent, request header, custom label을 전부 field로 열어두면 mapping explosion이 생긴다.

중요한 필드만 명시적으로 색인하고, 나머지는 `_source`에만 남기거나 ingest 단계에서 정리하는 편이 안전하다.

### 4. Index template + data stream

```bash
curl -X PUT "localhost:9200/_index_template/app-logs-template" \
  -H 'Content-Type: application/json' \
  -d '{
    "index_patterns": ["logs-app-*"],
    "data_stream": {},
    "priority": 200,
    "composed_of": [
      "app-logs-settings",
      "app-logs-mappings"
    ]
  }'
```

이제 `logs-app-prod` 같은 data stream으로 문서를 보내면 backing index가 template과 ILM policy를 따라 생성된다.

```bash
curl -X POST "localhost:9200/logs-app-prod/_doc" \
  -H 'Content-Type: application/json' \
  -d '{
    "@timestamp": "2026-07-13T02:50:00Z",
    "service": "payment-api",
    "environment": "prod",
    "level": "WARN",
    "trace_id": "trace-123",
    "message": "retrying payment approval after timeout"
  }'
```

### 5. 조회 경로 제한

운영에서 자주 빠지는 부분이 조회 경로다. ILM만 만들고 대시보드는 90일 전체를 기본 검색하게 두면 tier 설계가 무너진다.

좋은 기본값은 다음과 같다.

- 실시간 대시보드: 최근 15분~1시간
- 장애 분석 기본값: 최근 24시간
- 수동 조사: 최근 14일
- 장기 감사: 14~90일, 별도 화면 또는 async export

검색 API에서도 guardrail을 둔다.

```text
기본 검색 API
  max range: 14d
  대상: hot + warm

감사 검색 API
  max range: 90d
  대상: hot + warm + cold
  async 처리
  동시 실행 제한
  audit log 기록
```

데이터 tier를 나누는 순간 검색 경험도 나눠야 한다. 저장소만 cold로 옮기고 조회 UX를 그대로 두면 사용자는 "Elasticsearch가 느려졌다"고 느낀다.

---

## 트레이드오프 1: 인덱스 수를 줄이면 shard가 커지고, shard를 안정화하면 인덱스 수가 늘 수 있다

Rollover 설계에서 항상 만나는 trade-off다.

인덱스 수를 적게 유지하려면:

- rollover interval이 길어진다.
- 인덱스당 데이터가 커진다.
- shard 크기가 커질 수 있다.
- recovery, relocation, snapshot 단위가 무거워진다.

Shard 크기를 안정적으로 유지하려면:

- burst 때 rollover가 자주 일어난다.
- backing index 수가 늘어난다.
- query fan-out이 늘 수 있다.
- ILM step이 더 자주 실행된다.

정답은 "인덱스 적게"도 아니고 "shard 작게"도 아니다. 목표는 운영 가능한 shard 크기와 query fan-out 사이의 균형이다.

보통은 다음 지표를 같이 본다.

- primary shard 평균 크기와 p95 크기
- index count와 shard count 증가율
- 최근 24시간 쿼리가 타는 index 수
- cluster state size
- master node heap
- relocation/recovery 소요 시간
- snapshot duration
- ILM failed step count

Shard 크기 권장값은 버전, 하드웨어, 워크로드에 따라 다르지만, 로그성 데이터에서는 20~50GB primary shard를 자주 출발점으로 잡는다. 이 숫자를 절대 규칙으로 외우기보다, 복구 시간과 검색 latency를 기준으로 검증해야 한다.

---

## 트레이드오프 2: Warm phase 최적화는 비용을 줄이지만 재처리와 검색 유연성을 낮춘다

Warm phase에서 force merge, shrink, best compression을 적용하면 저장 비용과 검색 비용을 줄일 수 있다.

하지만 대가도 있다.

### Force merge

장점:

- segment 수가 줄어든다.
- read-only 인덱스 검색 비용이 줄 수 있다.
- file handle과 segment metadata 부담이 줄 수 있다.

단점:

- I/O와 CPU를 많이 쓴다.
- 작업 시간이 길 수 있다.
- 잘못된 시점에 돌리면 hot write와 경쟁한다.
- force merge 후 삭제된 문서 처리 방식이 기대와 다를 수 있다.

### Shrink

장점:

- shard 수를 줄여 오래된 인덱스의 관리 비용을 낮춘다.
- warm/cold query fan-out을 줄일 수 있다.

단점:

- shrink 조건이 까다롭다.
- 원본 shard가 같은 노드에 모여야 한다.
- 작업 중 allocation과 disk 여유가 필요하다.
- 나중에 병렬 검색 성능이 필요해져도 되돌리기 어렵다.

### Best compression

장점:

- 저장 공간을 줄일 수 있다.

단점:

- CPU 비용이 늘 수 있다.
- hot indexing path에는 부담이 될 수 있다.

따라서 warm phase 최적화는 "오래된 로그니까 무조건 압축"이 아니라 조회 빈도와 복구 요구를 보고 결정해야 한다. 장애가 많은 서비스에서 최근 7일 로그를 자주 뒤지는 팀이라면 warm phase를 너무 공격적으로 최적화하지 않는 편이 나을 수 있다.

---

## 트레이드오프 3: Retention은 비용 정책이면서 제품·보안·법무 계약이다

개발팀은 retention을 저장 비용 문제로 보기 쉽다.

```text
로그가 너무 많으니 30일 지나면 지우자.
```

하지만 운영에서는 retention이 여러 계약과 연결된다.

- 보안 감사 로그는 90일 이상 필요할 수 있다.
- 결제, 인증, 관리자 작업 로그는 더 오래 필요할 수 있다.
- 개인정보가 포함된 로그는 짧게 보관해야 할 수 있다.
- 고객별 엔터프라이즈 계약에 보존 기간이 명시될 수 있다.
- 내부 사고 대응 프로세스가 30일 이전 데이터를 요구할 수 있다.
- 법적 보존 요청이 들어오면 특정 기간 삭제를 멈춰야 할 수 있다.

그래서 retention은 "모든 로그 30일" 하나로 끝내기 어렵다. 로그를 등급별로 나누는 편이 낫다.

```text
debug/application log
  online retention: 14d
  archive: optional

security audit log
  online retention: 90d
  archive: 1y

admin activity log
  online retention: 180d
  archive: 3y

payment trace log
  online retention: 90d
  archive: policy dependent
```

이렇게 나누면 data stream도 분리하는 편이 좋다.

```text
logs-app-prod
logs-security-prod
logs-admin-prod
logs-payment-prod
```

모든 것을 하나의 거대한 `logs-*` stream에 넣고 필드로만 구분하면 lifecycle 정책을 다르게 적용하기 어렵다. 데이터의 보존 계약이 다르면 인덱스 생명주기도 분리해야 한다.

---

## 흔한 실수 1: ILM policy를 만들었지만 template에 연결하지 않는다

ILM policy만 만들어서는 아무 일도 일어나지 않는다. 새 인덱스가 해당 policy를 settings로 가져야 한다.

```json
{
  "settings": {
    "index.lifecycle.name": "app-logs-90d-policy"
  }
}
```

문제는 수동으로 만든 첫 인덱스에는 policy가 붙었는데, rollover 후 새 인덱스나 다른 서비스 인덱스에는 template이 적용되지 않는 경우다.

확인해야 할 명령:

```bash
curl -X GET "localhost:9200/logs-app-prod/_ilm/explain"
```

```bash
curl -X GET "localhost:9200/_index_template/logs-app-template"
```

```bash
curl -X POST "localhost:9200/_index_template/_simulate_index/logs-app-prod"
```

`_simulate_index`는 새 인덱스가 어떤 template과 settings를 받을지 확인할 때 유용하다. 운영 배포 전에 반드시 보는 편이 좋다.

---

## 흔한 실수 2: Rollover alias와 write index를 헷갈린다

Data stream을 쓰지 않고 alias 기반 rollover를 쓸 때는 write alias 설정이 중요하다.

초기 인덱스:

```bash
curl -X PUT "localhost:9200/app-logs-000001" \
  -H 'Content-Type: application/json' \
  -d '{
    "aliases": {
      "app-logs-write": {
        "is_write_index": true
      }
    }
  }'
```

ILM 설정:

```json
{
  "settings": {
    "index.lifecycle.name": "app-logs-policy",
    "index.lifecycle.rollover_alias": "app-logs-write"
  }
}
```

여기서 자주 생기는 실수:

- alias 이름과 `rollover_alias`가 다르다.
- 여러 인덱스가 `is_write_index: true`를 가진다.
- write alias가 아니라 실제 index name으로 문서를 넣는다.
- 초기 인덱스 이름이 `-000001` 패턴을 따르지 않는다.
- rollover 후 producer가 여전히 구 인덱스에 직접 쓴다.

이런 문제는 data stream을 쓰면 상당 부분 줄어든다. 그래서 append-only 로그라면 data stream을 우선 검토하는 편이 좋다.

---

## 흔한 실수 3: Mapping 변경을 lifecycle과 분리해서 생각한다

로그 필드는 계속 변한다. 새 서비스가 배포되면서 필드가 추가되고, 타입이 바뀌고, nested 구조가 들어온다.

문제는 이미 생성된 backing index의 mapping은 쉽게 바꿀 수 없다는 점이다. 새 template을 수정해도 과거 backing index가 자동으로 바뀌지 않는다.

예를 들어 `user_id`가 처음에는 숫자로 들어왔다.

```json
{ "user_id": 123 }
```

나중에 다른 서비스가 문자열로 보낸다.

```json
{ "user_id": "guest-123" }
```

동적 mapping이 켜져 있으면 첫 문서가 타입을 결정해버릴 수 있다. 이후 문서는 색인 실패하거나 의도와 다르게 처리된다.

운영 기준:

- 공통 로그 필드는 component template로 명시한다.
- ID류는 대체로 `keyword`를 우선한다.
- 숫자 계산이 필요한 필드만 numeric type으로 둔다.
- 원문 검색이 필요한 필드만 `text`로 둔다.
- stack trace처럼 검색 가치가 낮고 큰 필드는 `index: false`를 고려한다.
- 새 필드는 staging stream에서 template simulation과 샘플 색인을 먼저 검증한다.
- mapping breaking change는 새 data stream 또는 새 index pattern으로 분리한다.

Mapping은 검색 품질만의 문제가 아니라 ILM과도 연결된다. 잘못된 mapping으로 문서 색인이 실패하면 write index에 데이터가 빠지고, rollover와 retention은 정상처럼 보여도 실제 로그는 유실된다.

---

## 흔한 실수 4: Timestamp 품질을 검증하지 않는다

Data stream과 ILM은 시간 기반 데이터에서 강력하지만, `@timestamp` 품질이 나쁘면 운영이 흔들린다.

대표 문제:

- 애플리케이션 로컬 시간이 잘못되어 미래 timestamp가 들어온다.
- client time을 믿었다가 1970년 또는 2099년 데이터가 들어온다.
- timezone 파싱이 잘못되어 하루가 밀린다.
- ingest time과 event time이 섞인다.
- retry로 늦게 들어온 과거 이벤트가 최신 write index에 들어온다.

Data stream은 write 시점의 backing index에 문서를 넣는다. 문서의 `@timestamp`가 과거라고 해서 과거 backing index로 자동 라우팅되는 모델이 아니다. 따라서 늦게 들어온 이벤트는 최신 backing index에 들어갈 수 있다.

이것 자체는 문제가 아닐 수 있다. 검색은 `@timestamp` 필터로 하면 된다. 하지만 retention을 "문서 timestamp 기준"으로 오해하면 위험하다. ILM은 인덱스 나이를 기준으로 phase를 진행한다. 인덱스 안에 매우 오래된 이벤트가 섞여 있어도 인덱스 생성 시점 기준으로 삭제된다.

따라서 timestamp 정책을 명확히 해야 한다.

- `@timestamp`는 event time인가, ingest time인가?
- event time이 너무 과거거나 미래면 reject할 것인가, 보정할 것인가?
- 원본 event time과 ingest time을 둘 다 저장할 것인가?
- late arrival 허용 범위는 얼마인가?
- retention은 index age 기준으로 충분한가, 문서 event time 기준이 필요한가?

많은 로그 시스템에서는 아래처럼 둘을 분리한다.

```json
{
  "@timestamp": "2026-07-13T02:50:00Z",
  "event.created": "2026-07-13T02:49:58Z",
  "event.ingested": "2026-07-13T02:50:03Z"
}
```

이렇게 하면 검색과 지연 분석이 쉬워진다.

---

## 흔한 실수 5: 삭제 자동화만 믿고 ILM 실패를 모니터링하지 않는다

ILM은 자동으로 보이지만 실패할 수 있다.

실패 원인 예시:

- shrink 조건 불충족
- allocation tier에 노드가 없음
- disk watermark 초과
- rollover alias 오류
- policy 이름 변경
- 권한 문제
- snapshot 또는 searchable snapshot 관련 설정 오류
- force merge 장기 실행

ILM 상태는 주기적으로 봐야 한다.

```bash
curl -X GET "localhost:9200/_ilm/status"
```

```bash
curl -X GET "localhost:9200/logs-app-prod/_ilm/explain"
```

```bash
curl -X GET "localhost:9200/_cat/indices/logs-app-*?v&s=index"
```

운영 알림으로는 최소한 아래를 잡는다.

- ILM failed step count
- disk watermark
- shard count 급증
- unassigned shard
- rollover 미발생 또는 과도한 발생
- primary shard size p95
- data tier별 disk 사용률
- old index가 delete phase를 지나도 남아 있는지

Retention 자동화는 "돌아갈 것이다"가 아니라 "실패하면 바로 알 수 있다"까지 포함해야 한다.

---

## 운영 체크리스트

ILM과 data stream을 적용하기 전에는 아래를 확인한다.

### 데이터 분류

- [ ] 로그, metric, audit, trace, 검색 색인의 생명주기를 분리했는가?
- [ ] 같은 data stream 안의 문서들이 같은 retention 정책을 가져도 되는가?
- [ ] 개인정보 또는 보안 민감 필드가 포함되는가?
- [ ] 삭제 전 archive나 snapshot이 필요한가?

### Rollover와 shard

- [ ] 하루 평균 ingest와 p95/p99 burst ingest를 측정했는가?
- [ ] 목표 primary shard 크기를 정했는가?
- [ ] primary shard 수가 future growth와 query fan-out에 맞는가?
- [ ] `max_primary_shard_size`와 `max_age`가 모두 필요한가?
- [ ] rollover가 너무 자주 또는 너무 늦게 발생하지 않는지 시뮬레이션했는가?

### Template과 mapping

- [ ] index template이 실제 data stream 이름과 match되는가?
- [ ] `_simulate_index`로 settings, mappings, ILM policy 적용을 확인했는가?
- [ ] 공통 필드는 component template로 관리하는가?
- [ ] 동적 mapping 허용 범위를 정했는가?
- [ ] timestamp 필드와 timezone 정책을 명확히 했는가?

### Tier와 phase

- [ ] hot/warm/cold node의 역할과 disk 성능이 분리되어 있는가?
- [ ] warm phase의 force merge, shrink가 실제로 필요한가?
- [ ] cold query의 UX와 API 제한이 있는가?
- [ ] phase 전환 시점이 조회 패턴과 맞는가?
- [ ] tier별 disk watermark와 capacity planning이 있는가?

### Retention과 복구

- [ ] delete phase가 법적, 보안, 고객 계약과 맞는가?
- [ ] delete 전 snapshot 완료 여부를 확인할 수 있는가?
- [ ] 삭제된 인덱스를 복구하는 runbook이 있는가?
- [ ] ILM 실패 알림이 있는가?
- [ ] 장기 감사 조회는 online cluster인지 archive 복구인지 정했는가?

---

## 한 줄 정리

Elasticsearch ILM을 잘 쓴다는 것은 오래된 인덱스를 자동으로 지우는 것이 아니라, **데이터가 들어오는 순간부터 삭제되는 순간까지의 크기, 위치, 조회 비용, 보존 책임을 인덱스 생명주기 계약으로 고정하는 것**이다.
