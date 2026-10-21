---
layout: post
title: "Java 설정 파일 교체 실전: 임시 파일, ATOMIC_MOVE, force로 손상 창 줄이기"
date: 2026-10-21 11:40:00 +0900
categories: [java]
tags: [study, java, nio, files, atomic-move, filechannel, fsync, crash-consistency, configuration, backend]
permalink: /java/2026/10/21/study-java-atomic-file-replacement-force-crash-consistency.html
---

## 문제: 저장 성공 로그 뒤에 설정 파일이 비어 있었다

서비스가 실행 중 설정 스냅샷을 `settings.json`에 저장한다고 하자. 가장 짧은 구현은 다음과 같다.

```java
Files.writeString(path, json);
```

간단하지만 기존 파일을 직접 덮어쓰는 방식은 요구사항에 따라 위험하다. `Files.writeString`에 쓰기 옵션을 따로 주지 않으면 파일을 생성하거나 기존 파일을 먼저 잘라내고 쓰는 동작을 한다. 쓰는 중 프로세스가 종료되거나 I/O 오류가 나면 읽는 쪽은 빈 파일 또는 일부만 기록된 파일을 만날 수 있다. JSON 파싱 오류가 바로 드러나면 그나마 낫다. 부분적으로도 유효한 형식이라면 잘못된 설정을 정상값으로 받아들일 수 있다.

여기서 필요한 것은 막연한 “원자적 저장”이 아니라 세 가지 서로 다른 성질의 구분이다.

1. **가시성(visibility)**: 동시에 읽는 프로세스가 쓰는 중간 바이트를 보지 않아야 한다.
2. **내구성(durability)**: 저장 완료 응답 뒤 전원이 꺼져도 새 내용을 되찾을 수 있어야 한다.
3. **동시성 제어(concurrency)**: 두 쓰기 작업이 경쟁할 때 어느 버전을 남길지 결정되어야 한다.

`ATOMIC_MOVE`는 첫 번째 문제의 중요한 도구지만 세 가지를 전부 해결하지는 않는다. 이번 글은 로컬 파일 시스템의 **단일 파일 교체**를 예로 들어 API가 보장하는 것과 운영 환경에서 별도로 증명해야 하는 것을 나눈다.

> 범위: 하나의 JVM이 생성한 스냅샷 파일을 교체하는 예시다. 객체 스토리지, 네트워크 공유 폴더, 여러 노드의 합의, 데이터베이스 트랜잭션을 대체하지 않는다.

## 실패 창을 먼저 그려 보자

기존 파일을 직접 쓰는 코드는 보통 다음 순서로 움직인다.

```text
기존 파일 열기 → 길이 0으로 자르기 → 새 바이트 일부 쓰기 → 나머지 쓰기 → 닫기
                      ↑                 ↑
                 장애 시 빈 파일     장애 시 부분 파일
```

읽기 요청이 어느 순간에 들어오는지도 결과에 영향을 준다. `synchronized`를 writer에만 붙여도 별도 프로세스의 reader는 보호하지 못한다. `FileChannel.lock()`도 참여자 모두가 같은 규약을 지키지 않는다면 일반적인 읽기 보호책이 아니다.

파일 전체를 새 버전으로 바꾸는 전략은 다음과 같다.

```text
같은 디렉터리에 임시 파일 생성
→ 임시 파일에 전체 내용 쓰기
→ 임시 파일 내용 flush/force
→ 닫기
→ 목표 경로로 atomic move
```

교체 전까지 기존 경로는 그대로 둔다. 쓰다가 실패하면 임시 파일만 정리한다. 교체가 성공하면 **그 경로를 새로 열어 읽는 reader**는 완성된 새 파일을 보게 하는 것이 목표다. 이미 열린 파일 핸들은 플랫폼별 파일 교체·핸들 의미에 따라 별도로 생각해야 한다. 여러 파일을 순서대로 읽는 작업까지 한 번에 일관되게 만드는 것도 아니다.

### 원자적 교체와 영속 저장은 다른 축이다

`Files.move(source, target, ATOMIC_MOVE)`의 계약은 지원하는 파일 시스템에서 이동을 원자적 파일 시스템 작업으로 수행한다는 것이다. 그러나 `FileChannel.force(true)`는 파일 내용과 메타데이터 변경을 저장 장치로 밀어내도록 요청하는 별개의 API다. 경로 이름을 바꾸는 디렉터리 항목의 내구성은 또 다른 문제다.

| 단계 | 주로 줄이는 위험 | 여전히 남는 질문 |
| --- | --- | --- |
| 임시 파일에 전체 쓰기 | 목표 경로의 부분 쓰기 노출 | 임시 파일이 완성되었는가 |
| `FileChannel.force(true)` | 새 파일 데이터·메타데이터의 손실 위험 | 저장장치·파일 시스템이 어떤 보장을 제공하는가 |
| `ATOMIC_MOVE` | 목표 경로가 반쯤 교체된 상태로 보이는 위험 | 이동을 지원하는가, 기존 목표를 대체하는가 |
| 디렉터리 동기화/복구 절차 | 이름 변경의 전원 장애 손실 위험 | 해당 플랫폼에서 가능한가, 실제로 검증했는가 |

즉 “atomic move 성공 = 전원 장애 후에도 새 버전이 반드시 남는다”는 등식은 성립하지 않는다. 뒤에서 운영 요구 수준에 따라 선택지를 나눈다.

## Java NIO 계약을 정확히 읽기

### 1. 임시 파일은 목표와 같은 디렉터리에 둔다

```java
Path parent = target.toAbsolutePath().normalize().getParent();
Path temp = Files.createTempFile(parent, ".settings-", ".tmp");
```

기본 임시 디렉터리(`/tmp` 등)는 목표와 다른 `FileStore`일 수 있다. JDK 문서는 `ATOMIC_MOVE`가 불가능한 예로 서로 다른 `FileStore`나 provider를 든다. 같은 디렉터리에 만든다고 **반드시** 지원되는 것은 아니지만, 불필요한 교차 파일 시스템 이동은 피할 수 있다.

목표 경로의 부모 디렉터리는 미리 만들어 둔다. 그 부모를 이번 저장 작업에서 새로 만든다면 부모 디렉터리 자체의 내구성까지 별도 검토해야 한다. 심볼릭 링크, 상대 경로, 디렉터리 권한이 공격자에 의해 바뀔 수 있는 위치라면 아래 예시만으로 안전한 경로 처리가 완성되는 것도 아니다.

### 2. `FileChannel.write`는 한 번에 전부 쓴다고 가정하지 않는다

```java
ByteBuffer buffer = ByteBuffer.wrap(payload);
while (buffer.hasRemaining()) {
    channel.write(buffer);
}
channel.force(true);
```

`write` 반환값은 실제로 쓴 바이트 수다. 남은 바이트가 있을 수 있으므로 루프가 필요하다. `force(true)`의 `true`는 내용뿐 아니라 파일 메타데이터 변경도 대상으로 삼는다. 다만 JDK 문서에도 저장 장치가 로컬인지 여부 등에 따라 실제 보장 범위가 달라진다는 단서가 있다. 이를 “모든 하드웨어에서 절대 안전”으로 번역하면 안 된다.

`StandardOpenOption.SYNC` 또는 `DSYNC`를 사용하면 매 갱신을 동기화하도록 요구할 수도 있다. 스냅샷을 한 번에 쓰는 여기서는 전체를 쓴 뒤 `force`를 호출하는 편이 의도를 드러내기 쉽다. 동기화 비용이 사라지는 것은 아니다.

### 3. `ATOMIC_MOVE`는 `REPLACE_EXISTING`과 단순히 합성되지 않는다

JDK의 `Files.move` 문서에서 가장 중요한 문장 중 하나는 이것이다. **`ATOMIC_MOVE`가 지정되면 다른 옵션은 무시된다.** 목표 파일이 이미 있을 때 기존 파일을 교체할지, 예외를 던질지는 구현별로 다르다.

따라서 아래 코드는 “어느 운영체제에서나 원자적으로 덮어쓴다”는 선언이 아니다.

```java
Files.move(temp, target, ATOMIC_MOVE, REPLACE_EXISTING);
```

`REPLACE_EXISTING`을 함께 넣어도 원자적 이동에서 교체를 강제하는 휴대 가능한 계약은 얻지 못한다. 예제에서는 `ATOMIC_MOVE`만 사용하고, 대상 환경에서 **기존 파일 교체까지 실제 지원하는지** 배포 전 확인한다. 지원하지 않으면 실패를 드러낸다. 일반 `Files.move(..., REPLACE_EXISTING)`으로 조용히 재시도하면 독자에게 약속한 원자적 가시성을 잃는다.

또한 `AtomicMoveNotSupportedException`은 “이번 조건에서는 원자적 이동을 할 수 없다”는 명시적 신호다. 다른 `IOException`도 처리해야 한다. 비원자적 이동 중 I/O 오류가 날 경우 JDK는 원본·목표가 각각 어떤 상태인지 정의하지 않는다. 실패 후 무조건 “기존 파일은 안전하다”고 일반화해서는 안 된다.

## 작은 스냅샷 파일용 구현

아래 코드는 단일 파일의 작은 스냅샷을 대상으로 한다. 한 프로세스 안의 writer는 호출자가 직렬화한다고 가정하고, 같은 디렉터리의 원자적 **기존 파일 교체**가 실제 실행 환경에서 확인되지 않으면 서비스가 이를 저장 성공으로 취급하지 않는다. 전원 장애 뒤 경로 이름의 영속성은 이 코드의 보장 범위 밖이다.

```java
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Objects;

import static java.nio.file.StandardCopyOption.ATOMIC_MOVE;
import static java.nio.file.StandardOpenOption.WRITE;

public final class AtomicSnapshotWriter {
    private AtomicSnapshotWriter() {}

    public static void replace(Path target, byte[] payload) throws IOException {
        Objects.requireNonNull(target, "target");
        Objects.requireNonNull(payload, "payload");

        Path absolute = target.toAbsolutePath().normalize();
        Path parent = absolute.getParent();
        if (parent == null || !Files.isDirectory(parent)) {
            throw new IOException("snapshot directory does not exist: " + parent);
        }

        // 임시 파일을 목표와 같은 디렉터리에 둔다.
        Path temp = Files.createTempFile(parent, ".snapshot-", ".tmp");
        try {
            try (FileChannel channel = FileChannel.open(temp, WRITE)) {
                ByteBuffer data = ByteBuffer.wrap(payload);
                while (data.hasRemaining()) {
                    channel.write(data);
                }
                channel.force(true);
            }

            // ATOMIC_MOVE 미지원 또는 기존 target 교체 거부 시 그대로 실패한다.
            Files.move(temp, absolute, ATOMIC_MOVE);
        } catch (IOException | RuntimeException original) {
            try {
                Files.deleteIfExists(temp);
            } catch (IOException cleanup) {
                original.addSuppressed(cleanup);
            }
            throw original;
        }
    }
}
```

`Files.move`가 반환한 뒤에만 저장 성공으로 취급한다. 실패할 경우 `AtomicMoveNotSupportedException`도 `IOException`으로 호출자에게 전파되어, 비원자적 이동으로 자동 후퇴하지 않는다. 정리 실패는 최초 예외의 `suppressed`에 붙여 원인을 가리지 않는다. 임시 경로가 이미 이동되어 없어졌다면 `deleteIfExists`는 아무 일도 하지 않는다. 다만 I/O 예외가 난 뒤 파일 상태를 무조건 단정하지 말고 목표 경로와 내용을 재검증해야 한다.

한 프로세스 안의 writer끼리도 동시에 `replace`를 실행하면 마지막 이동이 이긴다. 호출 측에서 직렬화하거나 버전 검사 규칙을 둬야 한다. 또한 기존 파일의 권한·소유자가 새 임시 파일에 자동 승계된다는 계약은 없다.

### 읽는 쪽의 계약

```java
byte[] bytes = Files.readAllBytes(target);
Settings settings = parseAndValidate(bytes);
```

reader는 목표 경로를 한 번 열고, 파일 전체를 읽어 **파싱과 도메인 검증**을 마친 뒤 메모리의 설정 참조를 교체한다. “파일을 읽었다”와 “유효한 새 설정을 적용했다”도 별개다. 여러 번 나눠 열면 서로 다른 세대의 파일을 조합할 수 있다. 너무 큰 파일이라면 `readAllBytes` 대신 스트리밍 검증을 쓰되 동일한 파일 핸들에서 끝까지 읽는다.

## 설계 선택: 가시성 우선인가, 전원 장애 복구까지 필요한가

운영 요구를 아래처럼 명시해 두면 옵션을 잘못 섞을 가능성이 줄어든다.

| 요구 | 접근 | 잔여 위험 |
| --- | --- | --- |
| 실행 중 reader에게 부분 파일을 보이지 않기 | 같은 디렉터리 임시 파일 + 지원 확인된 `ATOMIC_MOVE` | 전원 장애 후 새 이름의 존속은 별도 문제 |
| 새 파일의 데이터 손실 위험 낮추기 | 이동 전 `FileChannel.force(true)` | 디렉터리 항목의 영속성은 별도 문제 |
| 전원 장애 후에도 저장 성공을 강하게 보장하기 | 해당 OS/파일 시스템에서 디렉터리 동기화와 장애 복구 시험을 포함한 전용 구현 | Java의 범용 API만으로 모든 환경에 동일한 보장을 약속할 수 없음 |
| 여러 writer의 버전 충돌 방지 | 단일 writer, 외부 락 또는 버전 비교 후 저장 | 잠금 범위와 프로세스 장애 처리 필요 |
| 여러 파일을 한 단위로 게시 | 세대별 디렉터리 + manifest 전환, 또는 DB 트랜잭션 | 파일 하나의 원자적 이동만으로 해결 안 됨 |

로컬 설정 캐시처럼 원본 데이터가 다른 곳에 있고 재생성 가능하다면, 전원 장애 때는 이전 스냅샷을 쓰거나 원본에서 복원한다는 정책이 합리적일 수 있다. 반대로 결제 원장이나 유일한 데이터 사본이라면 파일 하나의 교체 함수로 트랜잭션 요구를 만족시키려 하지 말고 검증된 저장 엔진을 고려해야 한다.

### 디렉터리 동기화를 코드 한 줄로 일반화하지 않는 이유

일부 환경에서는 이름 변경 후 부모 디렉터리의 변경 사항도 저장 장치에 동기화해야 전원 장애 뒤 새 경로가 남는다는 보장을 논의할 수 있다. 하지만 Java NIO의 범용 `FileChannel` 사용 예시에서 모든 provider의 **디렉터리 열기와 `force` 지원**을 동일하게 보장할 수 없다. POSIX 로컬 파일 시스템, Windows, 네트워크 파일 시스템, 컨테이너의 볼륨 구현은 동작이 다를 수 있다.

그래서 위 구현은 “새 파일 내용의 `force`와 원자적 가시성”까지만 계약으로 내세운다. 더 강한 내구성이 필요하면 **대상 배포 조합**에서 디렉터리 동기화 구현을 선택하고 전원 장애·재부팅 후 복구 테스트를 통과시켜야 한다. `force(true)`가 반환되었다는 이유만으로 디렉터리 rename까지 영속화되었다고 기록해서는 안 된다.

## 실패 시나리오와 검증 방법

성공 경로만 테스트하면 이 패턴의 가치가 확인되지 않는다. 쓰기 단계 사이에 고의로 오류를 넣고 경로별 결과를 본다.

1. **임시 파일 생성 전 실패**: 목표 파일은 이전 버전이어야 한다.
2. **바이트 일부 쓰고 실패**: 목표 파일은 이전 버전이고 임시 파일은 정리되거나 다음 기동 시 청소 대상으로 식별되어야 한다.
3. **`force` 실패**: 새 버전으로 이동하지 않아야 한다.
4. **`ATOMIC_MOVE` 미지원**: 예외를 올리고 비원자적 대체를 수행하지 않아야 한다.
5. **기존 목표 교체 거부**: 배포 환경의 실제 의미를 기록하고 파일은 이전 버전인지 확인한다.
6. **성공 직후 재열기**: 길이, 체크섬, 파싱 결과가 기대 버전과 일치해야 한다.
7. **동시 읽기/쓰기**: reader가 완성된 구버전 또는 신버전만 관측하는지 테스트한다. 단, 이 테스트만으로 전원 장애 내구성을 입증할 수는 없다.
8. **동시 writer**: 마지막 쓰기 승리 정책이 의도한 것인지, 버전 역행이 가능한지 확인한다.

검증용 payload에는 버전 번호, 길이, SHA-256 같은 체크섬을 함께 넣을 수 있다. reader가 payload 내부의 길이·체크섬을 검증하면 잘못된 형식이나 외부 요인에 의한 손상을 더 빨리 발견한다. 체크섬은 동시성이나 내구성을 **만들어 주지는 않는다**. 문제를 드러내는 관측 수단이다.

장애 주입은 파일 시스템 권한만 바꾸는 방식보다 `createTempFile`, `write`, `force`, `move`를 감싼 작은 인터페이스를 테스트용으로 교체하는 편이 재현성이 높다. 실제 파일 시스템 의미가 중요한 `ATOMIC_MOVE`와 기존 목표 교체는 운영과 같은 provider/볼륨에서 별도 통합 테스트를 한다. 임시 파일은 예기치 않은 프로세스 종료 때 남을 수 있으므로 시작 시 `.snapshot-*` 패턴을 무조건 즉시 삭제하기보다 **활성 writer와 충돌하지 않는 정책**을 마련한다.

## 운영에서 자주 놓치는 경계

- **권한과 소유자**: 새 임시 파일의 속성이 기존 목표의 속성과 같다고 가정하지 않는다. 교체 후 접근 권한을 검증한다. 권한 조정이 필요하면 이동 전 임시 파일에 적용하고, 민감 파일이라면 생성 순간의 기본 권한도 검토한다.
- **심볼릭 링크**: `Files.move`는 목표 링크의 대상 파일을 수정하는 API가 아니다. 링크를 통한 교체를 기대하면 다른 결과가 나온다.
- **백업과 감시자**: 파일 감시 이벤트는 교체 시점의 보조 신호다. watcher가 이벤트를 한 번만 정확히 받는다는 가정 대신 버전 재조회와 검증을 둔다.
- **디스크 공간**: 교체 중에는 구버전과 신버전이 동시에 존재하므로 순간적으로 추가 공간이 필요하다. 디스크가 거의 찬 상태는 `force` 실패까지 시험한다.
- **대용량 payload**: `byte[]`는 전체 내용을 메모리에 올린다. 큰 파일은 임시 파일로 스트리밍하되 최종 길이·체크섬을 검사하고 나서 이동한다.
- **오류 기록**: `IOException`만 기록하고 “저장 완료”로 응답하지 않는다. 실패 단계, 목표 경로, 저장하려던 버전, 임시 파일 정리 실패 여부를 남긴다. 민감한 본문이나 비밀값은 로그에 싣지 않는다.
- **원격 볼륨**: NFS나 클라우드 파일 시스템은 로컬 파일 시스템과 가시성·내구성 의미가 다를 수 있다. 개발 PC의 테스트 통과만으로 운영 보장을 주장하지 않는다.

## 마무리

파일 교체의 핵심은 `ATOMIC_MOVE`라는 옵션 이름이 아니라 **어떤 실패를 독자에게 약속하지 않을 것인지** 명확히 하는 데 있다. 임시 파일을 같은 디렉터리에 만들고, 바이트를 모두 쓴 뒤 `force`, 닫기, 지원 확인된 원자적 이동을 수행하면 실행 중 부분 파일 노출을 줄일 수 있다. 하지만 기존 목표 교체는 구현별로 다르고, 전원 장애 내구성과 다중 writer의 버전 충돌은 별도 설계다.

저장 성공을 반환하기 전에 “실행 중 reader가 무엇을 보는가”, “전원이 꺼지면 무엇이 남는가”, “두 writer 중 누가 이기는가”를 각각 시험하는 것이 실무적인 완료 기준이다.

## 근거 문서

- [JDK 21 `Files.move` 및 `Files.createTempFile`](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/nio/file/Files.html)
- [JDK 21 `FileChannel.force`](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/nio/channels/FileChannel.html#force(boolean))
- [JDK 21 `StandardCopyOption.ATOMIC_MOVE`](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/nio/file/StandardCopyOption.html#ATOMIC_MOVE)
- [JDK 21 `StandardOpenOption.SYNC`와 `DSYNC`](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/nio/file/StandardOpenOption.html)
