---
layout: post
title: "OpenTelemetry Collector 장애 내성 설계: memory_limiter, 배치, 전송 큐와 재시도의 경계"
date: 2026-11-18 11:40:00 +0900
categories: [data-infra]
tags: [study, data-infra, opentelemetry, collector, backpressure, memory-limiter, batch, sending-queue, retry, observability]
permalink: /data-infra/2026/11/18/study-opentelemetry-collector-backpressure-queue-memory-limiter.html
---

## 문제: 수집기는 살아 있는데 장애 구간의 로그가 비어 있다

애플리케이션이 OTLP로 로그와 trace를 Collector에 보낸다. 평소에는 문제가 없다. 그런데 관측 백엔드가 10분 동안 응답하지 않자 Collector 메모리가 오르고, 재시작 뒤 일부 데이터가 사라졌다. 운영자는 `retry_on_failure`를 켜 두었으니 결국 전부 전송될 거라고 생각했다.

실제로는 적어도 네 개의 경계가 있다.

```text
애플리케이션 SDK
  → receiver
  → memory_limiter → batch
  → exporter sending_queue → retry → 관측 백엔드
```

- **메모리 제한**은 새 데이터를 거절하여 프로세스가 무한정 메모리를 쓰지 않게 한다. 거절된 데이터가 자동 보관되는 것은 아니다.
- **배치**는 전송 효율을 위한 메모리 버퍼다. 내구성 있는 저장소가 아니다.
- **전송 큐**는 exporter 앞의 유한한 완충 장치다. 큐에 들어가기 전의 실패에는 exporter 재시도가 적용되지 않는다.
- **재시도**는 이미 exporter가 처리 중인 요청을 다시 보내는 정책이다. 무한 저장이나 정확히 한 번 전달을 뜻하지 않는다.

이 글은 Collector를 “전부 받아 주는 관”이 아니라 **유입량·버퍼·배출량에 한계가 있는 시스템**으로 설계하는 방법을 다룬다. 예시는 OTLP를 받는 gateway Collector 기준이며, 로그를 예로 들지만 trace와 metric에도 같은 용량 판단이 필요하다. 컴포넌트의 세부 설정과 기본값은 배포한 Collector 버전·배포판에서 다시 확인한다.

## 1. 먼저 성공의 의미를 세 단계로 나눈다

애플리케이션이 Collector로 보낸 요청에 성공 응답을 받았다는 것은 무엇을 보장할까? 배포 구성에 따라 “Collector의 현재 처리 경계에서 수락했다”는 뜻이지, 최종 백엔드에서 검색 가능하다는 뜻은 아니다. 메모리 큐라면 프로세스가 죽을 때 큐 내용이 사라질 수 있다. 디스크 큐라도 디스크 장애, 큐 포화, 재시도 소진이 남는다.

운영 계약을 다음처럼 분리하는 편이 정확하다.

| 단계 | 확인할 사실 | 그 사실만으로 보장하지 않는 것 |
| --- | --- | --- |
| receiver 수락 | Collector가 요청을 파이프라인으로 전달 | exporter 큐 적재, 최종 저장 |
| exporter 큐 적재 | 큐가 해당 요청을 받아들임 | 백엔드 반영, 영구 보존 |
| 백엔드 반영 | 대상 시스템이 요청을 받아 처리 | 검색 인덱싱 완료, 정확히 한 번 처리 |

Collector의 비동기 전송 큐는 특히 앞의 두 경계와 마지막 경계를 떨어뜨린다. 이 구분을 하지 않으면 장애가 끝난 뒤에도 “Collector가 200을 보냈는데 왜 결과가 없지?”라는 질문만 반복하게 된다. 중요한 이벤트를 **절대 잃으면 안 되는 비즈니스 기록**이라면 관측 파이프라인만을 유일한 원장으로 삼지 말고 별도의 내구성 있는 저장·전달 경로를 설계해야 한다.

### 실패 위치별 처리 흐름

| 실패 위치 | 일반적인 결과 | 운영자가 확인할 것 |
| --- | --- | --- |
| `memory_limiter`가 거절 | 앞 컴포넌트로 오류를 반환 | receiver·상위 송신자의 재시도와 실패율 |
| batch 내부에 대기 중 프로세스 종료 | 메모리상의 미전송분 손실 가능 | 재시작 전후 수락·전송량 차이 |
| exporter 큐가 가득 참 | 새 데이터의 큐 적재 실패 | enqueue 실패 지표, 큐 점유율 |
| 백엔드 일시 오류 | 재시도 가능한 오류라면 재전송 | 재시도·전송 실패 지표, 큐 체류 시간 |
| 재시도 시간 소진 | 해당 요청 손실 가능 | exporter 전송 실패, 백엔드 장애 지속 시간 |
| 디스크 큐의 저장소 오류 | 큐 적재 실패 가능 | 파일 시스템 사용량·권한·I/O 오류 |

표의 “가능”은 중요하다. 수집 방식과 앞 컴포넌트가 반환된 오류를 어떻게 다루는지에 따라 실제 데이터 손실 여부가 달라진다. 예를 들어 OTLP 송신자는 오류를 받고 다시 보낼 수 있지만, 이미 읽은 입력을 재생할 수 없는 receiver라면 같은 보장을 얻지 못한다.

## 2. `memory_limiter`는 손실 방지기가 아니라 압력 전달기다

Collector의 memory limiter는 주기적으로 메모리 사용량을 확인한다. 설정된 **soft limit**을 넘으면 새 데이터를 거절하고 앞 컴포넌트에 비영구적 오류를 돌려준다. **hard limit**을 넘으면 GC도 강제할 수 있다. `limit_mib`와 `spike_limit_mib`를 쓴다면 soft limit은 두 값의 차이다.

```yaml
processors:
  memory_limiter:
    check_interval: 1s
    limit_mib: 768
    spike_limit_mib: 192
```

이 예시의 soft limit은 576 MiB, hard limit은 768 MiB다. **컨테이너 한도가 768 MiB라는 뜻이 아니다.** 문서의 제한 값은 주로 Go heap 목표이고 프로세스 전체 메모리(RSS)는 더 클 수 있다. 컨테이너 한도, Go 런타임, receiver·processor·exporter의 버퍼, native 사용량을 함께 고려해 여유를 둬야 한다. cgroup을 쓰는 환경에서는 `limit_percentage` 방식도 공식 문서가 권장하는 선택지다. 어느 방식이든 실제 메모리 사용량으로 검증해야 한다.

`memory_limiter`를 pipeline의 첫 processor에 두는 이유는 batch나 다른 processor가 데이터를 더 쌓기 전에 압력을 전달하기 위해서다. 그러나 **거절 이후 재시도는 상위 receiver·송신자의 책임**이다. `memory_limiter`를 넣었다고 데이터가 내구성 있게 보존되지는 않는다. 유입량이 계속 처리량을 초과한다면 GC와 재시도만으로 정상 상태로 돌아올 수도 없다.

또 하나의 경계가 있다. 데이터는 limiter에 도달하기 전 receiver에서 이미 메모리를 사용할 수 있다. 특히 비-OTLP receiver에서는 이 양이 무시할 수 없을 수 있으므로 limiter 수치만으로 OOM이 절대 발생하지 않는다고 약속하면 안 된다.

## 3. batch와 sending queue의 단위를 혼동하지 않는다

`batch` processor는 여러 로그 레코드나 span을 묶어 압축과 전송 효율을 높인다. 아래 `send_batch_size`는 **전송을 촉발하는 기준**이지 절대 최대 크기가 아니다. 최대 크기를 강제하려면 `send_batch_max_size`를 따로 설정해야 한다.

```yaml
processors:
  batch:
    send_batch_size: 2048
    send_batch_max_size: 4096
    timeout: 1s
```

한편 exporter의 `sending_queue.queue_size`는 기본 `sizer: requests`일 때 **로그 레코드 수가 아니라 큐에 들어온 요청/배치 수**를 센다. “큐 2000개니까 로그 2000건만 저장한다”도, “2048건씩 묶으니 정확히 409만 건을 담는다”도 둘 다 틀리다. 배치가 timeout으로 일찍 나갈 수 있고 레코드 크기가 달라지며, 여러 신호·파이프라인·exporter가 각각 자원을 쓴다. 요청 크기가 크게 흔들리면 `sizer: items` 또는 `bytes`의 비용과 의미를 검토할 수 있지만 해당 배포판의 지원·성능을 검증한다.

큐와 재시도는 다음처럼 구분한다.

```yaml
exporters:
  otlp/backend:
    endpoint: backend.example.com:4317
    sending_queue:
      enabled: true
      queue_size: 2000
      num_consumers: 4
    retry_on_failure:
      enabled: true
      initial_interval: 5s
      max_interval: 30s
      max_elapsed_time: 10m
```

예시는 조정 전 출발점이지 권장 정답이 아니다. `num_consumers`를 늘리면 백엔드가 충분히 처리할 때 drain 속도가 오를 수 있지만, 백엔드가 이미 과부하라면 동시 요청을 더 늘려 상황을 악화시킬 수 있다. 재시도 최대 시간을 늘려도 큐가 찼을 때 새 데이터가 들어갈 자리는 생기지 않는다. 반대로 큐만 크게 잡고 재시도 시간을 짧게 두면 오래 기다린 요청이 먼저 버려질 수 있다.

Exporter helper 문서에 따르면 큐에 들어가지 못한 요청은 exporter 재시도 경로에 도달하지 않는다. 기본적으로 큐 포화 시 즉시 거절하며, `block_on_overflow`를 켜면 빈자리가 날 때까지 호출자가 대기할 수 있다. 이 선택은 앞 단계로 압력을 전달하지만 요청 지연·상위 timeout을 키운다. 따라서 “거절 대신 대기”가 무손실이라는 뜻은 아니다.

## 4. 장애 허용 시간을 숫자로 계산한다

큐 크기를 정할 때는 정상 평균 처리량보다 **백엔드가 멈췄을 때 누적되는 양**을 본다. 예를 들어 초당 600개 로그 레코드가 들어오고, 평균 120개씩 묶여 큐에 들어간다면 초당 약 5개 요청이 늘어난다. 백엔드가 완전히 멈춘 5분 동안은 약 1500개 요청이 쌓인다. `queue_size: 2000`이면 단순 계산상 약 6분 40초의 공간이다.

```text
대략적인 큐 포화 시간(초)
= (queue_size - 현재 queue_size 사용량)
  / (초당 큐 적재 요청 수 - 초당 성공적으로 배출한 요청 수)
```

이 식은 **용량 감을 잡기 위한 근사치**다. batch timeout, 레코드 크기, 재시도 중인 요청, 트래픽 급증, 병렬 consumer, signal별 큐가 결과를 바꾼다. 실제 설정은 장애 주입으로 측정한다. 특히 `queue_size`가 요청 수라면 디스크·메모리 용량도 별도로 추정해야 한다. 같은 1500개 요청이라도 로그 본문 크기가 10배면 필요한 바이트 수가 크게 달라진다.

복구 시간도 계산해야 한다. 유입이 초당 5개 요청인 동안 백엔드가 초당 8개를 처리한다면 backlog는 초당 3개씩만 줄어든다. 1500개를 비우는 데 단순 계산으로 약 500초가 더 든다. **장애가 끝났다고 backlog가 즉시 사라지지 않는다.** 이 구간에는 큐 점유율과 전송 지연이 함께 내려가는지 본다.

## 5. 재시작 시 유실 창을 줄이려면 디스크 큐를 선택적으로 쓴다

메모리 큐는 프로세스 재시작에 취약하다. Collector의 exporter helper는 `sending_queue.storage`에 storage extension을 연결해 영속 큐를 구성할 수 있다. `file_storage`는 contrib 계열 배포판에 포함되는 컴포넌트이므로 **실제 사용 중인 바이너리에 포함됐는지** 먼저 확인한다.

```yaml
extensions:
  file_storage:
    directory: /var/lib/otelcol/queue

receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317

processors:
  memory_limiter:
    check_interval: 1s
    limit_mib: 768
    spike_limit_mib: 192
  batch:
    send_batch_size: 2048
    send_batch_max_size: 4096
    timeout: 1s

exporters:
  otlp/backend:
    endpoint: backend.example.com:4317
    sending_queue:
      enabled: true
      storage: file_storage
      queue_size: 2000
      num_consumers: 4
    retry_on_failure:
      enabled: true
      initial_interval: 5s
      max_interval: 30s
      max_elapsed_time: 10m

service:
  extensions: [file_storage]
  pipelines:
    logs:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [otlp/backend]
```

이 설정에는 일부러 TLS·인증·외부 접근 제어를 생략했다. 운영에서는 백엔드와 receiver의 보안 설정을 별도 적용해야 한다. `file_storage.directory`는 쓰기 가능한 전용 경로로 잡고, 재시작뿐 아니라 **Pod 재생성 후에도** 큐를 보존해야 한다면 영속 볼륨을 사용한다. 임시 컨테이너 파일 시스템에 저장하면 프로세스 재시작 시험은 통과해도 Pod 교체 때 사라질 수 있다.

디스크 큐도 무한하지 않다. `queue_size`가 제한을 걸고 디스크 사용량·I/O 오류·파일 권한·스토리지 손상도 실패 원인이다. 파일 저장소가 제공하는 동기화 옵션은 성능과 내구성의 교환이므로 배포 요구에 맞춰 검토한다. 백엔드가 같은 요청을 두 번 처리할 가능성도 배제하지 않는다. **Collector의 재시도·영속 큐는 exactly-once 저장 보장이 아니다.**

파일 저장소가 살아 있는 큐 상태를 담고 있을 때 운영자가 디렉터리를 “정리”한다며 삭제하는 것은 backlog를 버리는 일이다. 용량 압박 시에는 삭제 전에 새 유입 제한, 백엔드 복구, 보존 우선순위를 먼저 결정한다.

## 6. 관측할 지표는 CPU보다 경계별 수량이다

장애를 조기에 잡으려면 수집기가 내보내는 자체 telemetry를 별도로 수집한다. 단, **그 자체 telemetry도 장애 난 동일 백엔드에만 보낸다면** 가장 필요한 순간에 보이지 않을 수 있다. 현장에서는 별도 scrape 경로 또는 독립적인 모니터링 경로를 둔다.

최소한 다음을 함께 본다.

1. Receiver의 수락·거절 수: 상위 송신자가 재시도해야 하는 압력이 있는가.
2. Processor의 거절 수와 프로세스 메모리/RSS: limiter가 실제로 작동하는가, 컨테이너 OOM이 먼저 나는가.
3. `otelcol_exporter_queue_size`와 `otelcol_exporter_queue_capacity`: 큐가 얼마나 차고, 복구 뒤 줄어드는가.
4. `otelcol_exporter_enqueue_failed_*`: 큐 진입 자체가 실패하는가.
5. Exporter 전송 성공·실패와 재시도: 백엔드 장애인지, 인증·영구 오류인지.
6. 디스크 큐라면 볼륨 사용량·I/O 지연·파일 시스템 오류: 큐가 실제로 기록 가능한가.

Collector 자체 지표의 구체적인 metric 이름과 label은 배포 버전에서 확인한다. 경보는 “메모리 80%” 하나보다 **큐 증가율 + 남은 포화 시간 + enqueue 실패 발생**을 결합하는 편이 행동 가능하다. 큐가 70%여도 유입이 급증 중이면 긴급하고, 90%여도 백엔드 복구 후 빠르게 비워지는 중이라면 다른 대응이 필요하다.

## 7. 배포 전 장애 주입으로 계약을 검증한다

설정 파일이 파싱된다는 것과 손실 범위를 이해했다는 것은 다르다. 스테이징 환경에서 고유 ID가 있는 테스트 로그를 일정한 속도로 보내고, 아래 순서로 세 구간을 시험한다.

### 백엔드 정지·복구

1. 유입 속도와 배치 크기, 큐 점유율을 기록한다.
2. 백엔드를 2분 정지하고 점유율이 예상 속도로 증가하는지 확인한다.
3. 백엔드를 복구하고 backlog가 감소하며 고유 ID의 도착 지연이 줄어드는지 확인한다.
4. 중복 ID와 빠진 ID를 별도로 센다. “최종 건수만 같다”면 중복과 손실이 서로 상쇄될 수 있다.

### 큐 포화

1. 충분히 오래 백엔드를 정지하여 큐를 채운다.
2. `enqueue_failed`와 상위 송신자의 오류·재시도·드롭 수를 함께 본다.
3. 큐 포화 시 요청이 거절되는지, 상위 timeout이 먼저 오는지 설정과 비교한다.
4. 복구 후 재시도 기한이 지난 요청과 끝내 도착하지 않은 ID를 확인한다.

### Collector 강제 종료·재생성

1. 큐가 찬 상태에서 프로세스를 강제 종료하고 재시작한다.
2. 메모리 큐와 디스크 큐의 결과를 비교한다.
3. Kubernetes라면 동일 Pod 내 프로세스 재시작뿐 아니라 **Pod 교체**도 시험한다.
4. 디스크 경로의 권한·남은 공간을 줄여 저장 실패 시의 오류와 알림을 검증한다.

테스트 결과는 “데이터 0건 손실”이라는 슬로건이 아니라 **어떤 장애·시간·입력률에서 어떤 경계가 데이터를 거절하거나 잃는지**로 기록한다. 운영에서 허용할 수 있는 손실·중복·지연 목표와 맞지 않으면 큐만 키울 게 아니라 상위 송신자의 재시도 보장, 영속 볼륨, 수집 계층 분리 또는 별도 메시지 큐를 검토한다.

## 설계 결론

- `memory_limiter`는 첫 processor에 두고 상위 재시도 여부를 확인한다. 메모리 보호와 데이터 보존은 별개다.
- batch 크기와 exporter 큐 크기의 **단위**를 확인한다. 요청 수를 레코드 수나 바이트 수로 오해하지 않는다.
- 재시도 시간, 큐 용량, 백엔드 복구 후 drain 속도를 하나의 장애 허용 예산으로 계산한다.
- 프로세스 재시작의 데이터 손실을 줄여야 한다면 영속 큐를 검토하되, 볼륨 수명과 디스크 실패까지 시험한다.
- Collector가 수락했다는 사실을 최종 저장이나 exactly-once 처리와 동일시하지 않는다.

## 근거 자료

- [OpenTelemetry: Collector resiliency](https://opentelemetry.io/docs/collector/resiliency/) — 전송 큐, 영속 큐, 손실 시나리오
- [Collector memory limiter processor](https://github.com/open-telemetry/opentelemetry-collector/tree/main/processor/memorylimiterprocessor) — soft/hard limit, 거절·GC·설정
- [Collector batch processor](https://github.com/open-telemetry/opentelemetry-collector/tree/main/processor/batchprocessor) — 배치 트리거와 최대 크기
- [Collector exporter helper](https://github.com/open-telemetry/opentelemetry-collector/tree/main/exporter/exporterhelper) — sending queue, retry, 영속 큐 동작
- [Collector contrib file storage extension](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/extension/storage/filestorage) — 디스크 저장소 설정과 제약
