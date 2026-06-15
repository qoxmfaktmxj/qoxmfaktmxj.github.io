---
layout: post
title: "Java GC 운영 튜닝 실전: G1, ZGC, Heap Sizing, Allocation Rate, JFR로 지연과 메모리 비용을 읽는 법"
date: 2026-06-15 11:50:00 +0900
categories: [java]
tags: [study, java, gc, g1gc, zgc, heap, allocation-rate, jfr, latency, memory, performance, operations]
permalink: /java/2026/06/15/study-java-gc-g1-zgc-heap-sizing-allocation-rate-jfr.html
---

## 배경: GC 튜닝은 옵션 암기가 아니라 지연 시간과 메모리 비용의 예산 관리다

Java 서비스를 운영하다 보면 GC는 자주 "갑자기 느려진 원인"으로 지목된다.

장애 회고에서 흔히 나오는 문장은 비슷하다.

- "GC가 많이 돌았다"
- "Full GC 때문에 멈췄다"
- "heap을 늘렸더니 괜찮아졌다"
- "G1 옵션을 좀 조정해야 할 것 같다"
- "ZGC로 바꾸면 해결되지 않을까?"

문제는 이 표현들이 대부분 증상과 원인을 섞어 말한다는 점이다. GC가 많이 돈 것은 원인일 수도 있지만, 더 자주 **애플리케이션이 너무 많은 객체를 만들고 있다는 신호**다. Full GC가 발생한 것은 collector 선택의 문제일 수도 있지만, 실제로는 leak, promotion 실패, humongous allocation, metaspace 증가, off-heap 메모리 압박, container memory limit 오해가 섞인 결과일 수 있다.

운영에서 GC 문제는 보통 다음처럼 나타난다.

- p95/p99 latency가 일정 주기마다 튄다
- CPU 사용률이 높지 않은데 요청 timeout이 늘어난다
- heap 사용량은 내려갔다 올라가지만 RSS는 계속 커진다
- Kubernetes에서 OOMKilled가 발생했는데 Java heap dump는 생각보다 작다
- 새 버전 배포 후 allocation rate가 늘어 GC CPU가 증가한다
- 캐시를 늘렸더니 평균 응답은 좋아졌지만 tail latency가 나빠졌다
- batch 작업이 도는 시간대에 API 서버까지 흔들린다
- `-Xmx`를 늘렸더니 장애 빈도는 줄었지만 장애 한 번의 정지 시간이 길어졌다
- GC 알고리즘을 바꿨는데 DB connection pool, thread pool, external API timeout 문제가 함께 드러난다

이런 상황에서 `-XX:MaxGCPauseMillis=100` 같은 옵션 하나만 만지면 해결될 것처럼 보인다. 하지만 실무에서 GC 튜닝은 그렇게 단순하지 않다.

GC는 크게 세 가지 예산을 동시에 다룬다.

1. **지연 시간 예산**: 요청이 멈춰도 되는 시간은 얼마인가
2. **처리량 예산**: CPU를 GC에 얼마나 쓸 수 있는가
3. **메모리 예산**: heap, metaspace, direct memory, thread stack, native memory까지 합쳐 얼마를 쓸 수 있는가

이 셋은 서로 공짜로 교환되지 않는다. 낮은 pause time을 원하면 보통 더 많은 CPU와 여유 메모리가 필요하다. heap을 크게 잡으면 GC 빈도는 줄 수 있지만 정리해야 할 live object가 많아져 특정 구간의 비용이 커질 수 있다. 캐시를 크게 잡으면 DB 부하는 줄지만 old generation 압박과 compaction 비용이 늘 수 있다.

이 글은 중급 이상 Java 개발자를 기준으로 GC를 운영 지표와 코드 구조의 문제로 읽는 방법을 정리한다.

초점은 단순 옵션 목록이 아니다.

- heap sizing을 container memory limit과 함께 계산하는 법
- allocation rate, live set, promotion, old generation 압박을 구분하는 법
- G1과 ZGC를 "무엇이 더 빠른가"가 아니라 "어떤 비용 모델인가"로 비교하는 법
- JFR, GC log, Native Memory Tracking으로 원인을 좁히는 방법
- 코드 레벨에서 GC 부담을 줄이는 실무 패턴과 역효과
- 튜닝 전에 반드시 확인해야 할 체크리스트

결론부터 말하면 이렇다.

> Java GC 튜닝의 핵심은 collector 옵션을 외우는 것이 아니라, **allocation rate와 live set을 측정하고 지연 시간·CPU·메모리 예산 중 무엇을 살리고 무엇을 지불할지 명확히 선택하는 것**이다.

---

## 먼저 큰 그림: GC는 "죽은 객체 정리기"가 아니라 메모리 흐름 제어 장치다

GC를 너무 단순하게 이해하면 "객체가 쌓이면 JVM이 알아서 치운다" 정도로 끝난다. 맞는 말이지만 운영 판단에는 부족하다.

서비스 관점에서 JVM 메모리는 계속 흐른다.

1. 요청이 들어온다
2. DTO, 문자열, 컬렉션, lambda, stream 중간 객체, JSON tree가 만들어진다
3. 대부분은 요청 처리 중 사라진다
4. 일부는 캐시, 세션, 큐, thread local, static holder, connection pool, metrics registry에 남는다
5. 남은 객체가 old generation 또는 long-lived 영역을 차지한다
6. GC는 짧게 살 객체와 오래 살 객체를 구분하며 공간을 회수한다

여기서 중요한 지표는 단순 heap 사용량 하나가 아니다.

- **allocation rate**: 초당 얼마나 많은 객체를 새로 만드는가
- **live set**: GC 후에도 살아남는 객체가 얼마나 되는가
- **object lifetime**: 객체가 얼마나 오래 살아남는가
- **promotion rate**: young 영역에서 old 영역으로 얼마나 넘어가는가
- **GC pause time**: 애플리케이션 스레드가 멈추는 시간이 얼마인가
- **GC CPU time**: GC 작업이 CPU를 얼마나 쓰는가
- **fragmentation**: 빈 공간은 있지만 큰 객체를 놓기 어려운 상태인가
- **native memory**: heap 밖 메모리가 container limit을 압박하는가

예를 들어 heap 사용량 그래프가 톱니 모양으로 보인다고 하자.

```
heap used
  ^
  |        /|        /|        /|
  |       / |       / |       / |
  |      /  |      /  |      /  |
  |_____/   |_____/   |_____/   |____> time
```

이 그래프만 보고 "정상"이라고 판단하면 위험하다. 더 물어봐야 한다.

- 톱니가 올라가는 속도는 배포 전보다 빨라졌는가
- 내려간 뒤 바닥선이 점점 올라가는가
- young GC만 도는가, mixed/old cycle까지 도는가
- GC 중 p99 latency가 얼마나 튀는가
- 같은 트래픽에서 GC CPU가 얼마나 늘었는가
- heap 밖 RSS도 같이 증가하는가

GC는 독립된 JVM 내부 문제가 아니다. 요청 패턴, serialization 방식, cache policy, batch size, DB fetch size, logging, metrics cardinality, thread 수, container limit이 모두 연결된다.

따라서 GC 튜닝의 첫 번째 원칙은 이것이다.

> **GC를 보기 전에 메모리 흐름을 본다.**

---

## 핵심 개념 1: heap size는 크게 잡는 값이 아니라 운영 예산에서 역산하는 값이다

GC 문제를 만나면 가장 쉬운 대응은 heap을 늘리는 것이다.

```
-Xms1g -Xmx1g
```

에서

```
-Xms4g -Xmx4g
```

로 바꾸면 당장은 문제가 사라질 수 있다. young 영역 여유가 생기고 GC 빈도가 줄며 old generation 압박도 늦게 온다.

하지만 heap 증설은 비용이 있다.

- container memory limit을 넘길 위험이 커진다
- live set이 크면 marking, remembered set, relocation 비용이 커진다
- memory leak 발견이 늦어진다
- Pod density가 떨어져 인프라 비용이 증가한다
- 장애가 날 때 heap dump 생성과 전송 비용이 커진다
- cold start와 warmup 중 메모리 압박이 커질 수 있다

그래서 heap은 "크면 좋다"가 아니라 전체 프로세스 메모리 예산 안에서 정해야 한다.

Kubernetes에서 memory limit이 2GiB인 Java API 서버를 예로 들자.

JVM 프로세스가 쓰는 것은 heap만이 아니다.

| 영역 | 예시 |
| --- | --- |
| Java heap | 객체, 배열, 캐시, 컬렉션 |
| Metaspace | class metadata, proxy class, generated class |
| Code cache | JIT compiled code |
| Thread stack | platform thread stack, native stack |
| Direct buffer | Netty, NIO, HTTP client, database driver |
| GC native structure | collector 내부 metadata |
| libc/native allocation | compression, TLS, DNS, font, image, JNI |
| observability agent | APM, profiler, exporter |

`-Xmx2g`를 주면 2GiB limit 안에 heap 2GiB만 들어가는 것이 아니다. heap 바깥 메모리 때문에 OOMKilled가 날 수 있다.

운영에서 더 현실적인 계산은 이런 식이다.

```
container limit: 2048 MiB
reserved native/overhead: 500~700 MiB
heap budget: 1200~1400 MiB
headroom: 100~200 MiB
```

대략적인 시작점은 다음처럼 잡을 수 있다.

```bash
JAVA_TOOL_OPTIONS="
  -Xms1280m
  -Xmx1280m
  -XX:MaxMetaspaceSize=256m
  -XX:MaxDirectMemorySize=256m
"
```

물론 이 값은 정답이 아니다. thread 수, Netty 사용 여부, APM agent, class loading 패턴, direct buffer 사용량에 따라 달라진다. 중요한 것은 `Xmx`만 보고 메모리 용량을 판단하지 않는 것이다.

### `Xms`와 `Xmx`를 같게 할지 다르게 할지

운영 서버에서는 `Xms`와 `Xmx`를 같게 두는 구성이 흔하다.

장점은 명확하다.

- heap 확장 비용과 변동성을 줄인다
- capacity planning이 단순해진다
- GC ergonomics가 더 예측 가능해진다
- container memory request/limit 설계와 맞추기 쉽다

하지만 항상 정답은 아니다.

- 매우 작은 서비스가 많고 메모리 밀도가 중요하면 초기 heap을 작게 두는 편이 나을 수 있다
- traffic spike가 드문 작업자라면 최대치만 크게 열어둘 수 있다
- serverless 또는 scale-to-zero 환경에서는 초기 메모리 비용이 중요할 수 있다

기준은 "정적 공식"이 아니라 운영 특성이다.

- 고정 트래픽 API 서버: `Xms = Xmx`가 예측 가능하다
- batch worker: 작업 크기와 동시성에 맞춰 상한을 강하게 둔다
- 작은 background service: 초기 heap을 낮추고 실제 RSS를 관찰한다
- latency-sensitive service: heap resizing 변수를 줄이는 편이 안전하다

---

## 핵심 개념 2: allocation rate와 live set을 구분하지 않으면 튜닝 방향이 반대로 간다

GC 문제를 볼 때 가장 먼저 나누어야 할 질문은 두 가지다.

1. 객체를 너무 많이 새로 만드는가
2. 객체가 너무 오래 살아남는가

이 둘은 해결책이 다르다.

### allocation rate가 높은 경우

초당 수백 MB에서 수 GB 단위로 객체를 계속 만든다고 하자. 요청 하나당 객체는 금방 죽지만 요청량이 많아 young GC가 자주 발생한다.

증상은 보통 이렇다.

- young GC가 매우 자주 돈다
- GC 후 heap 바닥선은 크게 증가하지 않는다
- old generation 사용량은 비교적 안정적이다
- CPU에서 GC 비중이 높아진다
- latency spike가 짧고 빈번하다

원인은 코드에 있을 가능성이 크다.

- JSON을 `String -> JsonNode -> DTO`로 여러 번 변환한다
- stream pipeline이 작은 컬렉션에 과하게 사용된다
- logging에서 문자열 포맷팅이 무조건 수행된다
- 요청마다 큰 `Map<String, Object>`를 만든다
- DB 결과를 전부 메모리에 올린 뒤 필터링한다
- metrics tag cardinality가 높아 내부 객체가 계속 늘어난다
- validation, mapping, serialization 단계가 같은 데이터를 반복 복사한다

이 경우 heap을 무작정 늘리면 GC 빈도는 줄 수 있지만 근본 원인은 남는다. 오히려 객체 생성 비용이 CPU와 cache locality를 계속 잡아먹는다.

### live set이 큰 경우

반대로 GC 후에도 살아남는 객체가 많다면 문제는 다르다.

증상은 보통 이렇다.

- GC 후 heap 바닥선이 높다
- old generation 사용량이 계속 증가한다
- mixed GC 또는 old GC의 비용이 커진다
- Full GC 또는 evacuation failure 위험이 커진다
- heap dump에서 캐시, queue, map, thread local, listener registry가 크게 보인다

원인은 장수 객체다.

- TTL 없는 in-memory cache
- 무제한 queue
- request-scoped 데이터를 `ThreadLocal`에 넣고 제거하지 않음
- static collection에 listener, callback, tenant context를 누적
- batch 결과 전체를 메모리에 보관
- WebSocket/session 상태를 JVM local memory에 과하게 보관
- high-cardinality metrics label이 계속 새 series를 만든다

이 경우 allocation 최적화보다 **보유 정책**이 중요하다.

- 캐시에 maximum size와 TTL을 둔다
- queue capacity와 backpressure를 명확히 한다
- `ThreadLocal.remove()`를 보장한다
- listener lifecycle을 명시한다
- batch는 chunk 단위로 처리하고 중간 결과를 버린다
- metrics tag value를 제한한다

GC 튜닝에서 가장 중요한 분기점은 여기다.

> **많이 만들고 금방 죽는 문제인지, 적게 만들어도 오래 붙잡는 문제인지 먼저 구분한다.**

---

## 핵심 개념 3: G1은 기본 선택지에 가깝지만, pause target은 약속이 아니라 목표다

현대 Java 서버에서 G1은 매우 흔한 기본 선택지다. G1은 heap을 region으로 나누고, young collection과 mixed collection을 통해 pause time 목표를 맞추려 한다.

G1을 이해할 때 핵심은 이름 그대로 **Garbage First**다. 회수 효율이 높은 region을 우선적으로 수거해 제한된 pause 시간 안에서 최대한 많은 공간을 확보하려는 전략이다.

하지만 여기서 많은 팀이 `MaxGCPauseMillis`를 오해한다.

```bash
-XX:MaxGCPauseMillis=100
```

이 옵션은 "GC pause가 100ms를 절대 넘지 않는다"는 보장이 아니다. collector가 이 값을 목표로 ergonomics를 조정할 뿐이다.

실제 pause가 길어질 수 있는 상황은 많다.

- live object가 많아 복사할 객체가 많다
- remembered set 관리 비용이 크다
- humongous object가 많이 할당된다
- old generation 압박이 커져 mixed collection이 무거워진다
- CPU가 부족해 concurrent marking이 제때 끝나지 않는다
- container CPU limit 때문에 GC thread가 충분히 돌지 못한다
- allocation spike가 marking 주기를 앞질러 공간이 부족해진다

### G1에서 자주 보는 운영 신호

G1 로그와 JFR에서 다음 신호를 보면 방향이 달라진다.

| 신호 | 의미 | 우선 확인 |
| --- | --- | --- |
| Young GC 빈번 | allocation rate 높음 | serialization, mapping, temporary collection |
| Mixed GC 증가 | old region 회수 필요 | cache, long-lived object, promotion |
| Humongous allocation | 큰 배열/문자열/byte buffer | payload size, batch size, compression buffer |
| To-space exhausted | 복사할 여유 region 부족 | heap 여유, live set, allocation spike |
| Concurrent marking 지연 | old 압박을 따라가지 못함 | CPU limit, IHOP, allocation rate |
| Full GC 발생 | 정상 cycle로 회수 실패 | leak, fragmentation, humongous, heap 부족 |

예를 들어 큰 JSON 응답을 문자열로 조립하는 서비스가 있다고 하자.

```java
public String exportOrders(List<Order> orders) {
    List<OrderRow> rows = orders.stream()
            .map(OrderRow::from)
            .toList();

    return objectMapper.writeValueAsString(rows);
}
```

주문 수가 작을 때는 괜찮다. 하지만 한 번에 수십만 건을 처리하면 다음 객체들이 동시에 생길 수 있다.

- `orders` 전체 목록
- `rows` 전체 목록
- row DTO
- JSON serializer 내부 buffer
- 최종 `String`
- UTF-8 byte array

G1 입장에서 이는 단순 young allocation이 아니라 큰 배열과 humongous object 문제로 이어질 수 있다.

더 나은 구조는 streaming이다.

```java
public void exportOrders(OutputStream out, OrderQuery query) throws IOException {
    try (SequenceWriter writer = objectMapper.writer()
            .writeValuesAsArray(out)) {
        orderRepository.scan(query, order -> {
            try {
                writer.write(OrderRow.from(order));
            } catch (IOException e) {
                throw new UncheckedIOException(e);
            }
        });
    }
}
```

핵심은 GC 옵션이 아니라 객체 생존 범위를 줄이는 것이다. 전체 결과를 한 번에 들고 있지 않으면 live set과 큰 객체 압박이 동시에 줄어든다.

---

## 핵심 개념 4: ZGC는 pause를 낮추는 도구지만 메모리와 CPU 비용을 공짜로 없애지 않는다

ZGC는 낮은 pause time을 목표로 하는 collector다. 큰 heap에서도 애플리케이션 정지 시간을 작게 유지하려는 설계가 핵심이다.

그래서 latency-sensitive 서비스에서 매력적이다.

- p99 latency spike를 줄이고 싶다
- heap이 크지만 긴 stop-the-world pause를 피하고 싶다
- 요청 지연 편차가 사용자 경험에 크게 영향을 준다
- 짧은 pause를 위해 CPU와 메모리 여유를 지불할 수 있다

하지만 ZGC를 "GC 문제 해결 버튼"처럼 보면 위험하다.

ZGC도 다음 문제를 없애지 않는다.

- 객체를 너무 많이 만드는 비용
- live set이 너무 큰 비용
- memory leak
- off-heap memory 증가
- DB connection pool 병목
- external API timeout
- CPU bound 작업의 과도한 동시성
- 잘못된 cache policy

낮은 pause를 얻기 위해 collector가 concurrent 작업을 더 많이 수행하면 CPU 비용과 메모리 headroom 요구가 늘 수 있다. 즉 애플리케이션이 멈추는 시간은 줄어도 전체 CPU 사용량이나 메모리 여유 요구는 달라질 수 있다.

### G1과 ZGC를 선택하는 실무 기준

단순히 "무엇이 더 좋다"가 아니라 서비스 성격을 봐야 한다.

| 기준 | G1이 잘 맞는 경우 | ZGC를 검토할 만한 경우 |
| --- | --- | --- |
| 기본 안정성 | 일반적인 API, worker, batch | 낮은 tail latency가 핵심인 API |
| heap 크기 | 중소형 heap, 예측 가능한 live set | 큰 heap, pause 민감 서비스 |
| CPU 여유 | CPU budget이 빡빡함 | concurrent GC CPU를 지불할 여유 |
| pause 목표 | 수십~수백 ms 허용 | 짧은 pause가 중요한 SLA |
| 운영 단순성 | 기본값 중심 운영 선호 | GC 지표를 적극적으로 관찰 가능 |
| 문제 원인 | allocation/live set 개선 여지 큼 | pause 자체가 비즈니스 리스크 |

collector 전환 전에 반드시 해야 할 질문은 이것이다.

1. 현재 장애가 진짜 GC pause 때문인가
2. pause가 아니라 allocation CPU 또는 memory leak 문제는 아닌가
3. `p99`와 `max` latency 중 어느 지표가 사용자를 괴롭히는가
4. CPU request/limit에 concurrent collector가 쓸 여유가 있는가
5. heap, direct memory, metaspace를 포함한 headroom은 충분한가
6. rollback 가능한 방식으로 A/B 또는 canary를 할 수 있는가

ZGC로 바꾸는 것은 좋은 선택일 수 있다. 하지만 좋은 선택이 되려면 목적이 분명해야 한다.

> "GC가 문제 같다"가 아니라 "사용자 요청 p99를 흔드는 STW pause를 줄이기 위해 CPU와 메모리 여유를 지불하겠다"가 되어야 한다.

---

## 실무 예시 1: API 서버의 p99 spike를 GC log와 JFR로 좁히기

상황을 가정해 보자.

- Spring Boot API 서버
- Pod memory limit 2GiB
- `-Xms1200m -Xmx1200m`
- G1 사용
- 평상시 p95는 80ms
- 5분마다 p99가 1.5초까지 튄다
- CPU 평균은 45% 정도

처음에는 DB 문제처럼 보였다. 하지만 DB query latency는 안정적이다. 애플리케이션 로그에서는 timeout이 드문드문 보인다.

이때 바로 옵션을 바꾸기보다 세 가지를 켠다.

```bash
JAVA_TOOL_OPTIONS="
  -Xms1200m
  -Xmx1200m
  -Xlog:gc*,safepoint:file=/var/log/app/gc.log:time,uptime,level,tags:filecount=5,filesize=50m
  -XX:StartFlightRecording=filename=/var/log/app/app.jfr,settings=profile,dumponexit=true,maxage=30m,maxsize=512m
"
```

운영에서는 로그 경로, 파일 크기, 보존 정책을 반드시 맞춰야 한다. GC 로그가 디스크를 채우면 다른 장애가 된다.

수집 후 확인할 것은 다음이다.

1. p99 spike 시간과 GC pause 시간이 겹치는가
2. pause 종류가 young, mixed, full, remark, cleanup 중 무엇인가
3. spike 직전에 allocation rate가 튀는가
4. GC 후 heap 바닥선이 올라가는가
5. JFR allocation flame graph에서 어떤 타입이 상위에 있는가
6. thread dump에서 safepoint 외 다른 blocking이 있는가

분석 결과 JFR에서 `byte[]`, `char[]`, `String`, `LinkedHashMap`, `JsonNode` allocation이 높게 나왔다고 하자. 특정 endpoint가 대형 JSON payload를 받아 `JsonNode`로 파싱한 뒤 다시 DTO로 변환하고 있었다.

나쁜 구조는 이런 식이다.

```java
public ImportResult importUsers(String rawJson) throws IOException {
    JsonNode root = objectMapper.readTree(rawJson);
    List<UserImportRow> rows = new ArrayList<>();

    for (JsonNode node : root.get("users")) {
        rows.add(objectMapper.treeToValue(node, UserImportRow.class));
    }

    return userImportService.importAll(rows);
}
```

문제는 여러 겹이다.

- 전체 JSON 문자열이 메모리에 있다
- `JsonNode` tree 전체가 메모리에 있다
- DTO list 전체가 메모리에 있다
- import 처리 중 결과 객체도 누적된다
- 큰 요청 하나가 young/old 경계를 흔든다

개선 방향은 streaming과 chunk 처리다.

```java
public ImportResult importUsers(InputStream in) throws IOException {
    ImportAccumulator accumulator = new ImportAccumulator();

    try (JsonParser parser = objectMapper.getFactory().createParser(in)) {
        expectStartObject(parser);
        moveToUsersArray(parser);

        List<UserImportRow> chunk = new ArrayList<>(500);
        while (parser.nextToken() == JsonToken.START_OBJECT) {
            chunk.add(objectMapper.readValue(parser, UserImportRow.class));

            if (chunk.size() == 500) {
                accumulator.add(userImportService.importChunk(chunk));
                chunk.clear();
            }
        }

        if (!chunk.isEmpty()) {
            accumulator.add(userImportService.importChunk(chunk));
        }
    }

    return accumulator.toResult();
}
```

이 개선은 GC 옵션을 바꾸지 않는다. 하지만 효과는 GC에 직접 나타난다.

- 요청당 peak live object가 줄어든다
- 큰 `JsonNode` tree가 사라진다
- DTO list가 chunk 크기만큼만 유지된다
- young GC 빈도와 pause 변동성이 줄 수 있다
- old generation으로 넘어가는 객체가 줄 수 있다

이런 식으로 GC 분석은 코드 구조 개선으로 이어져야 한다.

---

## 실무 예시 2: 캐시를 늘렸더니 GC는 줄었지만 장애 반경이 커진 경우

이번에는 반대 사례다.

외부 상품 API가 느려서 local cache를 넣었다고 하자.

```java
private final Map<String, ProductSnapshot> productCache = new ConcurrentHashMap<>();

public ProductSnapshot getProduct(String productId) {
    return productCache.computeIfAbsent(productId, productClient::fetch);
}
```

처음에는 효과가 좋다. 외부 API 호출이 줄고 평균 응답 시간이 내려간다.

하지만 운영 시간이 길어질수록 문제가 생긴다.

- heap 사용량 바닥선이 계속 오른다
- old generation이 점점 커진다
- mixed GC가 무거워진다
- 배포 후 몇 시간 지나면 p99가 튄다
- 신규 상품이 많았던 날 OOM이 발생한다

이 문제는 collector를 바꿔도 본질이 남는다. 캐시가 보유 정책 없이 계속 자라기 때문이다.

더 나은 구조는 maximum size, TTL, weight, metric을 명시하는 것이다.

```java
Cache<String, ProductSnapshot> productCache = Caffeine.newBuilder()
        .maximumWeight(200_000_000)
        .weigher((String key, ProductSnapshot value) -> value.estimatedBytes())
        .expireAfterWrite(Duration.ofMinutes(10))
        .recordStats()
        .build();

public ProductSnapshot getProduct(String productId) {
    return productCache.get(productId, productClient::fetch);
}
```

여기서 중요한 것은 라이브러리 이름이 아니라 정책이다.

- 얼마나 오래 들고 있을 것인가
- 몇 개 또는 몇 바이트까지 허용할 것인가
- stale 데이터를 허용할 것인가
- miss storm을 어떻게 막을 것인가
- eviction이 성능에 어떤 영향을 주는가
- 캐시 hit rate와 heap pressure를 함께 볼 수 있는가

캐시는 GC 관점에서 "성능 최적화"이면서 동시에 "old generation에 장수 객체를 넣는 행위"다. 평균 응답 시간을 낮추는 대신 memory pressure와 tail latency 비용을 지불한다.

따라서 캐시 도입 후에는 최소한 다음 지표를 같이 본다.

- cache size
- estimated weight
- hit/miss/eviction count
- load latency
- old generation usage
- GC after-collection heap usage
- p95/p99 latency

캐시는 성공해도 위험하고 실패해도 위험하다. 성공하면 더 많은 데이터를 오래 들고 있게 되고, 실패하면 miss storm으로 downstream을 때린다.

---

## 실무 예시 3: OOMKilled인데 heap dump는 작을 때는 native memory를 의심한다

Kubernetes에서 Java Pod가 OOMKilled 되었는데 heap dump를 보면 `Xmx`까지 차지 않았다. 이때 "JVM이 이상하다"고 생각하기 쉽지만, 대부분 heap 밖 메모리 문제다.

예를 들어 설정이 이렇다.

```bash
container memory limit: 1024Mi
-Xmx768m
```

남은 256MiB에 모든 native overhead가 들어가야 한다.

- metaspace
- code cache
- thread stack
- direct buffer
- GC native metadata
- TLS/native library
- APM agent
- libc allocation

이 구성은 생각보다 빠듯하다. 특히 thread 수가 많거나 Netty/direct buffer를 많이 쓰면 위험하다.

확인을 위해 Native Memory Tracking을 사용할 수 있다.

```bash
JAVA_TOOL_OPTIONS="
  -XX:NativeMemoryTracking=summary
  -XX:+UnlockDiagnosticVMOptions
"
```

실행 중에는 `jcmd`로 확인한다.

```bash
jcmd <pid> VM.native_memory summary
```

분석할 때는 다음을 본다.

- Java heap committed
- Class/metaspace
- Thread
- Code
- GC
- Internal
- Arena Chunk
- NIO/direct buffer 관련 항목

thread가 원인이라면 thread dump와 pool 설정을 본다.

```java
Executors.newCachedThreadPool();
```

같은 구성이 요청 폭증 시 platform thread를 많이 만들 수 있다. 각 thread stack은 native memory를 사용한다.

direct buffer가 원인이라면 Netty, HTTP client, database driver, file transfer, compression 경로를 본다. 특히 큰 파일 업로드/다운로드를 heap 밖 buffer로 처리하는 경우 `Xmx`와 별도로 `MaxDirectMemorySize`를 관리해야 한다.

```bash
-XX:MaxDirectMemorySize=256m
```

단, 상한만 걸면 해결되는 것은 아니다. 상한에 닿으면 direct buffer allocation failure가 나거나 I/O latency가 나빠질 수 있다. 근본적으로는 buffer lifetime, streaming, connection pool, backpressure가 같이 맞아야 한다.

OOMKilled를 줄이는 기본 원칙은 다음이다.

1. container limit에서 heap을 먼저 뺀 뒤 native headroom을 남긴다
2. thread 수와 stack 비용을 계산한다
3. direct memory 상한과 실제 사용 경로를 확인한다
4. metaspace가 계속 증가하면 classloader leak, dynamic proxy, hot reload 경로를 본다
5. APM agent와 profiler의 메모리 비용도 예산에 넣는다

---

## 트레이드오프: GC 튜닝은 항상 무언가를 지불한다

GC 옵션과 구조 개선은 대부분 trade-off다. 한쪽만 좋아지는 선택은 드물다.

### heap을 늘린다

장점:

- GC 빈도가 줄 수 있다
- allocation spike에 대한 완충이 커진다
- old generation 압박이 늦게 온다
- 임시 대응으로 장애 빈도를 줄일 수 있다

비용:

- Pod당 메모리 비용이 늘어난다
- live set이 크면 marking/relocation 비용이 커진다
- memory leak 발견이 늦어진다
- OOM 시 heap dump 처리 비용이 커진다
- container native headroom이 줄 수 있다

### heap을 줄인다

장점:

- Pod density가 좋아진다
- leak이 빨리 드러난다
- 작은 live set에서는 GC가 가벼워질 수 있다
- 비용 관리가 쉬워진다

비용:

- allocation spike에 취약하다
- GC 빈도가 늘 수 있다
- old generation 압박이 빨리 온다
- tail latency가 나빠질 수 있다

### G1 pause target을 낮춘다

장점:

- collector가 짧은 pause를 목표로 더 보수적으로 움직인다
- latency-sensitive 서비스에서 spike 완화에 도움이 될 수 있다

비용:

- 목표가 보장되지는 않는다
- GC 빈도가 늘고 처리량이 줄 수 있다
- live set이 크면 의미가 제한적이다
- CPU limit이 낮으면 오히려 따라가지 못할 수 있다

### ZGC로 바꾼다

장점:

- stop-the-world pause를 크게 줄일 수 있다
- 큰 heap에서 latency 편차를 줄이는 데 유리할 수 있다
- tail latency가 중요한 서비스에 적합할 수 있다

비용:

- concurrent GC CPU 비용을 지불해야 한다
- 메모리 headroom이 더 중요해진다
- allocation/live set 문제가 사라지지는 않는다
- 운영팀이 새 지표와 로그를 읽을 수 있어야 한다

### 객체 생성을 줄인다

장점:

- allocation rate가 줄어 young GC와 CPU 부담이 줄 수 있다
- serialization/mapping 비용이 감소한다
- latency와 처리량이 동시에 좋아질 수 있다

비용:

- 코드가 복잡해질 수 있다
- pooling을 잘못 쓰면 더 큰 버그가 생긴다
- premature optimization 위험이 있다
- 불변성과 단순성을 해칠 수 있다

### 캐시를 늘린다

장점:

- downstream latency와 부하를 줄인다
- 평균 응답 시간이 좋아질 수 있다
- 장애 시 일부 기능을 유지할 수 있다

비용:

- old generation live set이 커진다
- stale data와 consistency 문제가 생긴다
- eviction 정책이 없으면 leak과 비슷해진다
- miss storm과 cache stampede를 설계해야 한다

---

## 흔한 실수 1: 평균 latency만 보고 GC 영향을 놓친다

GC 문제는 평균보다 tail latency에서 먼저 드러난다.

예를 들어 1분에 요청 60,000건이 있고, 그중 100건만 2초 튄다고 하자. 평균 latency는 거의 움직이지 않을 수 있다. 하지만 사용자와 timeout은 그 100건을 느낀다.

GC 영향을 볼 때는 최소한 다음을 함께 본다.

- p50, p95, p99, max latency
- GC pause duration
- safepoint time
- request timeout count
- downstream timeout과의 시간 상관관계
- Pod별 latency 분포

평균 CPU, 평균 heap, 평균 latency만 보면 장애가 숨는다.

---

## 흔한 실수 2: Full GC가 없으면 괜찮다고 판단한다

Full GC는 강한 신호지만, Full GC가 없다고 GC 문제가 없는 것은 아니다.

다음 상황도 충분히 문제다.

- young GC가 너무 자주 돌아 CPU를 먹는다
- mixed GC가 길어져 p99를 흔든다
- concurrent marking이 CPU를 지속적으로 사용한다
- allocation stall이 발생한다
- safepoint가 GC 외 이유로 길어진다
- direct memory pressure 때문에 heap 지표만 정상으로 보인다

운영 관점에서는 "Full GC 여부"보다 "사용자 요청에 영향을 주는 정지와 CPU 비용"이 더 중요하다.

---

## 흔한 실수 3: object pooling으로 GC를 줄이려다 버그를 만든다

객체 생성을 줄이겠다고 직접 pool을 만드는 경우가 있다.

```java
class BufferPool {
    private final Queue<byte[]> pool = new ConcurrentLinkedQueue<>();

    byte[] borrow() {
        byte[] buffer = pool.poll();
        return buffer != null ? buffer : new byte[1024 * 1024];
    }

    void release(byte[] buffer) {
        pool.offer(buffer);
    }
}
```

이 코드는 단순해 보이지만 운영에서는 위험하다.

- release 누락 시 leak이 된다
- 큰 buffer가 계속 old generation에 남는다
- 이전 데이터가 지워지지 않으면 보안 문제가 된다
- pool이 무제한이면 메모리 상한이 없다
- 작은 요청도 큰 buffer를 붙잡을 수 있다
- 동시성 버그가 생기기 쉽다

JVM의 young allocation은 매우 빠르다. 짧게 살 작은 객체를 억지로 pooling하는 것은 대개 손해다.

pooling이 필요한 경우는 보통 제한적이다.

- 매우 큰 buffer
- 생성 비용이 큰 native resource
- 수명과 반환을 엄격히 관리할 수 있는 구조
- 상한과 metric이 있는 pool
- thread confinement이 명확한 경우

대부분의 서비스에서는 직접 pooling보다 다음이 먼저다.

- 전체 materialization 제거
- streaming 처리
- batch/chunk 크기 제한
- 불필요한 중간 변환 제거
- cache와 queue 상한 설정
- logging/metrics allocation 점검

---

## 흔한 실수 4: GC 로그를 켜지 않은 상태로 옵션부터 바꾼다

GC 튜닝은 측정 없이 하면 거의 운에 가깝다.

최소한 운영 또는 staging 부하 테스트에서 GC 로그를 남겨야 한다.

```bash
-Xlog:gc*,safepoint:file=gc.log:time,uptime,level,tags:filecount=5,filesize=50m
```

그리고 변경 전후로 같은 기준을 비교한다.

- total allocation rate
- GC count
- pause p95/p99/max
- GC CPU 비중
- old generation after GC
- Full GC 여부
- RSS
- application p95/p99 latency
- error/timeout count

옵션을 하나 바꿨다면 한 번에 여러 개를 같이 바꾸지 않는 편이 좋다. 여러 옵션을 동시에 바꾸면 무엇이 효과였는지 알기 어렵다.

---

## 흔한 실수 5: container CPU limit을 무시한다

GC는 CPU를 쓴다. 특히 concurrent collector는 애플리케이션과 동시에 CPU를 나눠 쓴다.

Kubernetes에서 CPU limit이 낮게 잡힌 상태에서 GC target만 공격적으로 낮추면 기대와 다르게 동작할 수 있다.

- concurrent marking이 늦어진다
- GC worker가 충분히 실행되지 못한다
- 애플리케이션 thread와 GC thread가 CPU를 경쟁한다
- throttling 때문에 pause와 latency가 불규칙해진다

GC 지표를 볼 때는 CPU throttling도 함께 봐야 한다.

- container CPU usage
- CPU throttled time
- GC CPU time
- request concurrency
- run queue saturation

GC pause가 길어 보이지만 실제 원인은 CPU throttling인 경우도 있다.

---

## 운영 체크리스트: GC 튜닝 전에 확인할 것

아래 체크리스트를 순서대로 보면 불필요한 옵션 실험을 줄일 수 있다.

### 1. 문제 정의

- 어떤 사용자 지표가 나빠졌는가: p95, p99, timeout, error rate, throughput
- 문제가 특정 endpoint, tenant, batch, 시간대에 몰리는가
- 배포, 트래픽, 데이터 크기, dependency 변화가 있었는가
- GC pause와 사용자 지표가 시간상 겹치는가

### 2. JVM 메모리 구조

- container memory limit과 request는 얼마인가
- `Xmx`가 limit 대비 과하게 크지 않은가
- metaspace, direct memory, thread stack 예산을 남겼는가
- RSS와 heap used가 서로 다른 패턴으로 움직이는가
- OOM이 Java OOME인지 container OOMKilled인지 구분했는가

### 3. GC 로그와 JFR

- GC log가 켜져 있는가
- pause p95/p99/max를 봤는가
- young, mixed, full, remark, cleanup을 구분했는가
- allocation rate와 promotion rate를 봤는가
- JFR allocation hot type과 call stack을 확인했는가
- safepoint 원인이 GC 외 다른 이벤트는 아닌가

### 4. 객체 생성 경로

- 요청당 큰 JSON/XML/CSV를 전체 materialization하지 않는가
- DTO 변환이 여러 번 중복되지 않는가
- stream/lambda가 hot path에서 과도한 중간 객체를 만들지 않는가
- logging message가 disabled level에서도 생성되지 않는가
- `String.format`, regex, date formatter, mapper 생성이 반복되지 않는가
- large array, `byte[]`, `char[]`, `String` allocation 상위 경로를 확인했는가

### 5. 장수 객체와 보유 정책

- cache에 size/TTL/weight 상한이 있는가
- queue에 capacity와 backpressure가 있는가
- thread local cleanup이 보장되는가
- static map/listener registry가 무한히 커지지 않는가
- metrics label cardinality가 통제되는가
- session, websocket, tenant context가 heap에 과하게 남지 않는가

### 6. Collector 선택

- 현재 collector의 pause와 CPU 비용을 측정했는가
- G1 기본값에서 문제가 무엇인지 명확한가
- pause target 변경 전후를 비교할 수 있는가
- ZGC 전환 시 CPU와 memory headroom이 충분한가
- canary와 rollback 계획이 있는가

### 7. 변경 검증

- 하나의 변경만 적용했는가
- 같은 부하에서 전후 비교했는가
- p99뿐 아니라 GC CPU, RSS, error rate도 봤는가
- peak traffic과 batch 시간대 모두 확인했는가
- heap dump와 JFR 파일 보관 정책을 정했는가

---

## 실무 기준: 어떤 순서로 대응할 것인가

장애 중에는 완벽한 분석보다 피해 축소가 먼저다. 하지만 순서를 정해두면 덜 흔들린다.

### 1단계: 즉시 완화

- 문제가 되는 endpoint나 batch 동시성을 줄인다
- batch size, page size, upload size를 제한한다
- 캐시나 queue가 무제한이면 임시 상한을 둔다
- Pod memory limit과 `Xmx` 관계를 점검한다
- OOM 위험이 크면 heap보다 native headroom을 먼저 확인한다
- p99를 흔드는 Pod를 교체하되, GC log/JFR 증거를 남긴다

### 2단계: 증거 수집

- GC log, JFR, heap dump, NMT를 확보한다
- application latency와 GC event를 시간축으로 맞춘다
- allocation hot path와 live object dominator를 확인한다
- 배포 전후 allocation rate, old after GC, RSS를 비교한다

### 3단계: 구조 개선

- 전체 materialization을 streaming/chunk로 바꾼다
- cache, queue, buffer에 상한을 둔다
- high-cardinality metric을 정리한다
- request-scoped 데이터를 thread local/static에 남기지 않는다
- 중복 mapping과 serialization을 줄인다

### 4단계: JVM 옵션 조정

- heap size와 native headroom을 재계산한다
- G1 pause target, region 관련 신호, IHOP 관련 신호를 신중히 검토한다
- latency 요구가 강하면 ZGC canary를 검토한다
- CPU limit과 GC thread 경쟁을 함께 본다

이 순서가 중요한 이유는 단순하다. 코드가 무제한으로 객체를 만들고 오래 붙잡는 상태에서 collector만 바꾸면 문제의 모양만 바뀐다.

---

## 한 줄 정리

Java GC 운영 튜닝은 `G1이냐 ZGC냐`를 고르는 문제가 아니라, **allocation rate와 live set을 측정해 지연 시간·CPU·메모리 예산 사이의 교환을 명시적으로 설계하는 작업**이다.
