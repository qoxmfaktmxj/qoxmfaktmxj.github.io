---
layout: post
title: "Java UTF-8 파일 수집 실전: 잘못된 바이트, BOM, 크기 제한을 검증하고 데이터 손상을 막는 법"
date: 2026-11-25 11:40:00 +0900
categories: [java]
tags: [study, java, utf-8, charsetdecoder, codingerroraction, bom, file-ingestion, data-validation, backend]
permalink: /java/2026/11/25/study-java-utf8-ingestion-strict-decoding-bom.html
---

## 문제: 수집은 성공했는데 고객 이름이 바뀌었다

외부 시스템에서 CSV나 JSON 파일을 받아 DB에 반영하는 배치를 생각해 보자. 파일 이름은 `.csv`이고 계약서에는 UTF-8이라고 적혀 있다. 구현은 다음처럼 시작하기 쉽다.

```java
String body = new String(Files.readAllBytes(path), StandardCharsets.UTF_8);
parseAndSave(body);
```

하지만 파일 안에 깨진 UTF-8 바이트가 섞여 있다면 이 코드는 반드시 실패하는 검증기가 아니다. `String(byte[], Charset)` 생성자는 잘못된 입력을 해당 문자셋의 기본 대체 문자열로 바꾼다. 흔히 화면에 보이는 `�`(U+FFFD)가 그 흔적이다. 파서가 그 문자열도 유효한 이름으로 받으면, 원본과 다른 값이 저장된다. 나중에 오류를 알아도 어떤 바이트가 있었는지 문자열만으로 복원할 수 없다.

문제는 “문자열을 어떻게 읽을까”보다 **외부 바이트를 신뢰할 수 있는 데이터로 승격시키는 경계**를 어디에 둘까이다. 여기서는 다음 정책을 명시한다.

- 파일 계약은 UTF-8이다. 다른 인코딩을 추측하지 않는다.
- 잘못된 UTF-8은 조용히 고치지 않고 해당 파일을 거절한다.
- 맨 앞의 UTF-8 BOM은 허용하되 제거한다. 중간에 나타난 U+FEFF까지 무조건 지우지 않는다.
- 이 예제의 파일은 최대 8 MiB다. 초과하면 파싱 전에 거절한다.
- 디코딩 성공과 업무 데이터 검증 성공은 별도 단계다. 둘 다 통과하기 전에는 영속 상태를 변경하지 않는다.

이 정책은 모든 입력에 대한 정답이 아니다. 사람이 쓴 메모를 최대한 살리는 편집기와, 고객 식별자를 받아 자동 반영하는 배치는 실패 허용 범위가 다르다. 중요한 것은 두 용도를 같은 암묵적 디코딩 기본값에 맡기지 않는 것이다.

## 바이트·문자·업무 필드는 서로 다른 계층이다

파일 수집 과정을 세 경계로 나누면 실패 위치가 선명해진다.

```text
바이트 스트림
  ↓ UTF-8 디코딩: 바이트 시퀀스가 유효한가?
문자열
  ↓ CSV/JSON 파싱: 문법이 유효한가?
필드 값
  ↓ 업무 검증: ID·날짜·중복·참조가 유효한가?
DB 반영
```

UTF-8 디코더가 성공해도 CSV 따옴표가 맞지 않을 수 있다. CSV 파서가 성공해도 필수 고객 ID가 비었을 수 있다. 반대로 CSV 파서가 깨진 문자열을 받아들였다고 해서 원본 바이트가 유효했다는 뜻도 아니다.

로그와 오류 코드를 이 단계에 맞춰 구분하자. `INVALID_ENCODING`, `INVALID_FORMAT`, `INVALID_RECORD`를 모두 “파일 파싱 실패”로 합치면, 공급자가 인코딩을 고쳐야 하는지 우리가 매핑 규칙을 고쳐야 하는지 알기 어렵다.

### `�`를 검색하는 것으로 충분하지 않은 이유

디코딩 후 U+FFFD를 찾아 거절하는 방식은 정확한 검증이 아니다. 원본이 **정상적인 UTF-8로 인코딩된 U+FFFD 문자**를 실제로 포함할 수도 있다. 그 경우 단지 문자만 보고는 원본이 손상됐는지 알 수 없다. 반대로 대체가 일어난 뒤에는 어떤 잘못된 바이트가 몇 개였는지도 잃어버린다. 검사는 디코딩 **시점**에 해야 한다.

## Java 디코더의 오류 정책을 명시한다

`CharsetDecoder`는 잘못된 바이트 시퀀스(malformed input)와, 문자셋으로 매핑할 수 없는 입력(unmappable character)에 대한 동작을 따로 설정한다. `CodingErrorAction`의 선택지는 `REPORT`, `REPLACE`, `IGNORE`다.

| 정책 | 결과 | 데이터 수집 경계에서의 의미 |
| --- | --- | --- |
| `REPORT` | 오류를 호출자에게 알림 | 파일을 격리하고 공급자에게 수정 요청 가능 |
| `REPLACE` | 대체 문자로 진행 | 원문 손실을 허용한다는 명시적 선택 필요 |
| `IGNORE` | 문제 입력을 버리고 진행 | 필드 값이 조용히 붙거나 짧아질 위험 |

정확성을 우선하는 수집에서는 두 오류 유형 모두 `REPORT`로 둔다. `CharsetDecoder`의 기본 오류 동작도 `REPORT`지만, 파일 계약의 핵심 정책이라면 코드에 적어 두는 편이 리뷰에 유리하다. 디코더는 상태를 가지므로 여러 파일을 동시에 처리할 때 하나를 공유하지 말고 파일마다 새로 만든다.

```java
CharsetDecoder decoder = StandardCharsets.UTF_8.newDecoder()
        .onMalformedInput(CodingErrorAction.REPORT)
        .onUnmappableCharacter(CodingErrorAction.REPORT);

String text = decoder.decode(ByteBuffer.wrap(bytes)).toString();
```

`decode`가 실패하면 `CharacterCodingException` 계열 예외가 발생한다. 여기서는 예외를 잡아 성공값처럼 빈 문자열을 반환하면 안 된다. 파일 수준의 실패로 올려서 재처리·격리 경로로 보내야 한다.

> UTF-8에 대해 “한 바이트가 한 글자”라고 가정해 바이트 배열을 임의의 길이로 잘라 각각 `new String`으로 만들면, 경계에 걸친 다중 바이트 문자가 깨질 수 있다. 스트리밍할 때는 상태를 유지하는 `Reader`/디코더가 청크 경계를 처리하도록 맡긴다.

## BOM은 별도 계약이다

UTF-8 BOM은 파일 맨 앞의 `EF BB BF` 세 바이트다. 이 바이트는 UTF-8로 디코딩하면 U+FEFF가 된다. Java의 일반적인 UTF-8 문자열 디코딩을 “BOM을 자동으로 지우는 파서”로 취급하면 위험하다. CSV 첫 헤더가 실제로는 `customer_id`가 아니라 `\uFEFFcustomer_id`가 되어 열 이름 조회가 실패할 수 있다.

정책은 셋 중 하나를 고른다.

1. **거절**: 공급자 계약이 BOM 없는 UTF-8이라면 명확한 오류로 돌린다.
2. **맨 앞에서만 제거**: 여러 외부 도구가 파일을 생성하고 BOM이 허용된다면 수집 경계에서 한 번 제거한다.
3. **그대로 유지**: 내용 자체를 보존해야 하는 텍스트 처리에서는 문자로 취급한다.

아래 예제는 두 번째다. **원시 바이트의 첫 3개**가 정확히 `EF BB BF`인지 확인한다. 디코딩된 문자열 어디에 있든 U+FEFF를 일괄 삭제하지 않는다. 후자는 실제 데이터 변경이며, 앞의 BOM이 두 번 붙은 경우 같은 비정상 입력을 감출 수 있다. 이 예제에서는 두 번째 U+FEFF가 내용에 남으므로 후속 헤더 검증에서 드러나게 된다.

참고로 UTF-16의 BOM, 다른 인코딩의 흔적, 임의의 제어 문자를 이 세 바이트 규칙으로 해결할 수는 없다. 인코딩 자동 감지는 별도의 불확실한 추론 문제다. API 계약에 인코딩을 명시할 수 있다면 그 편이 더 안전하다.

## 크기 제한을 포함한 작은 파일용 구현

아래 코드는 **파일당 8 MiB 이하**라는 운영 계약을 전제로 전체 파일을 메모리에 읽는다. 제한을 `Files.size(path)`로만 먼저 확인하지 않는다. 크기 검사와 실제 읽기 사이에 파일이 바뀔 수 있고, 스트림이나 가상 파일의 크기는 기대와 다를 수 있기 때문이다. `readNBytes(MAX_BYTES + 1)`로 제한보다 딱 한 바이트 더 읽어 초과를 판단한다.

```java
import java.io.IOException;
import java.io.InputStream;
import java.nio.ByteBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CharsetDecoder;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Objects;

public final class StrictUtf8Files {
    private static final int MAX_BYTES = 8 * 1024 * 1024;

    private StrictUtf8Files() {}

    public static String read(Path path) throws IOException {
        Objects.requireNonNull(path, "path");

        byte[] bytes;
        try (InputStream input = Files.newInputStream(path)) {
            bytes = input.readNBytes(MAX_BYTES + 1);
        }
        if (bytes.length > MAX_BYTES) {
            throw new IOException("UTF-8 file exceeds 8 MiB: " + path);
        }

        int offset = hasUtf8Bom(bytes) ? 3 : 0;
        CharsetDecoder decoder = StandardCharsets.UTF_8.newDecoder()
                .onMalformedInput(CodingErrorAction.REPORT)
                .onUnmappableCharacter(CodingErrorAction.REPORT);
        try {
            return decoder.decode(
                    ByteBuffer.wrap(bytes, offset, bytes.length - offset)
            ).toString();
        } catch (CharacterCodingException e) {
            throw new IOException("Invalid UTF-8 in file: " + path, e);
        }
    }

    private static boolean hasUtf8Bom(byte[] bytes) {
        return bytes.length >= 3
                && (bytes[0] & 0xff) == 0xef
                && (bytes[1] & 0xff) == 0xbb
                && (bytes[2] & 0xff) == 0xbf;
    }
}
```

이 코드는 **최대 읽기 바이트 수**를 제한하지만, 메모리 사용량이 8 MiB로 고정된다는 뜻은 아니다. 바이트 배열, 디코딩 결과의 버퍼, 최종 문자열, 이어지는 파서의 객체가 함께 존재한다. 동시 업로드 수가 많다면 파일 크기 제한뿐 아니라 동시 처리 수와 메모리 예산도 정해야 한다. `MAX_BYTES + 1` 계산은 이 상수가 충분히 작은 정수인 예제에서만 안전하다. 설정으로 한도를 받는 일반 라이브러리라면 정수 오버플로를 별도로 검증해야 한다.

파일 내용이 읽는 동안 다른 프로세스에 의해 바뀔 수도 있다. 이 예제가 **원본 파일의 스냅샷 일관성**을 보장하지는 않는다. 공급 측에서 완성된 파일만 원자적으로 게시하거나, 수집 측에서 별도 staging 위치에 먼저 고정한 뒤 읽는 운영 계약이 필요하다.

### 예외를 어디서 처리할까

파일 하나의 오류가 배치 전체를 중단해야 하는지는 업무 정책이다. 하지만 다음처럼 예외를 먹고 성공으로 취급하면 안 된다.

```java
// 나쁜 예: 손상된 파일을 빈 정상 파일로 둔갑시킨다.
try {
    return StrictUtf8Files.read(path);
} catch (IOException e) {
    return "";
}
```

대신 파일 상태를 `REJECTED_ENCODING` 또는 `REJECTED_TOO_LARGE`로 남기고, 원본 바이트를 접근 통제된 격리 저장소에 보존할지 결정한다. 로그에는 파일 식별자, 공급자, 오류 유형을 남기되 고객 정보와 원본 전체를 찍지 않는다. 같은 파일을 재시도할 때는 원본 해시나 공급자 파일 ID로 중복 반영을 막는다. 인코딩 오류는 같은 입력을 그대로 재시도해도 사라지지 않으므로 자동 재시도 폭주 대상이 아니다.

## 큰 파일은 스트리밍하되, 검증 단위를 다시 설계한다

전체 파일을 메모리에 둘 수 없다면 `InputStreamReader`에 **명시적으로 설정한 디코더**를 넘길 수 있다. `Reader`가 바이트 경계에 걸친 문자를 처리한다.

```java
CharsetDecoder strict = StandardCharsets.UTF_8.newDecoder()
        .onMalformedInput(CodingErrorAction.REPORT)
        .onUnmappableCharacter(CodingErrorAction.REPORT);

try (var input = Files.newInputStream(path);
     var reader = new java.io.BufferedReader(
             new java.io.InputStreamReader(input, strict))) {
    String line;
    while ((line = reader.readLine()) != null) {
        processLine(line);
    }
}
```

단, 이것만으로 앞 절의 계약이 자동 구현되지는 않는다.

- 이 코드는 BOM을 제거하지 않는다. 허용할 것이라면 입력 스트림 시작에서 **한 번만** 판별하거나 첫 문자에 대한 명시적 정책을 구현한다.
- `readLine()`은 줄 끝 문자를 제거한다. 정확한 원문 보존이나 디지털 서명 검증에 쓰면 안 된다.
- 줄 길이에 상한이 없다. 한 줄이 수 기가바이트인 공격적 입력이라면 전체 파일을 스트리밍해도 한 줄에서 메모리가 고갈될 수 있다. 줄 또는 레코드 길이 제한을 추가한다.
- 100만 번째 줄에서 인코딩 오류가 발견될 수 있다. 앞의 99만 줄을 이미 DB에 커밋했다면 파일 단위 원자성을 잃는다.

마지막 항목이 가장 중요하다. 큰 파일 수집은 단순히 읽기 API를 바꾸는 문제가 아니다. 선택지는 예를 들면 다음과 같다.

| 방식 | 장점 | 비용·주의점 |
| --- | --- | --- |
| 검증 후 전체 반영 | 파일 단위 성공/실패가 선명 | 임시 저장 공간과 2회 읽기 필요 |
| staging 테이블에 적재 후 승격 | 대용량에도 검증·중복 확인 가능 | 임시 데이터 정리·승격 트랜잭션 설계 필요 |
| 레코드별 부분 반영 | 빠른 진행·부분 복구 가능 | 어떤 레코드까지 반영됐는지 추적하고 재처리 멱등성 확보 필요 |

한 파일의 모든 레코드가 유효해야 반영되는 업무라면, 디코딩·파싱·업무 검증을 완료한 뒤 staging 데이터를 승격하는 방식이 보통 이해하기 쉽다. 검증 단계에서 외부 원본이 바뀌지 않도록 같은 스냅샷을 읽어야 한다. 반대로 부분 반영을 허용한다면 “성공한 줄과 실패한 줄”을 명시적으로 기록하고 재실행 계약을 세워야 한다.

## 실제로 확인할 실패 사례

단위 테스트에서는 **문자열을 다시 인코딩한 값만** 만들지 말고, 문제 바이트를 직접 생성한다. 문자열에서 출발하면 이미 유효한 UTF-8이 되어 잘못된 입력을 재현하지 못한다.

```java
// 정상: 한글 3바이트 문자를 포함한 UTF-8
byte[] valid = "고객A".getBytes(StandardCharsets.UTF_8);

// 잘못된 입력: 2바이트 문자의 첫 바이트만 있고 이어지는 바이트가 없다.
byte[] truncated = {(byte) 0xC3};

// UTF-8 BOM + ASCII 헤더. 정책대로라면 결과는 "customer_id".
byte[] bomHeader = {(byte) 0xEF, (byte) 0xBB,
        (byte) 0xBF, 'c', 'u', 's', 't', 'o', 'm', 'e', 'r', '_', 'i', 'd'};
```

검증 항목은 다음처럼 분리한다.

1. 정상 UTF-8은 정확히 같은 문자로 읽힌다.
2. 잘린 다중 바이트 시퀀스와 잘못된 이어쓰기 바이트는 실패한다.
3. `EF BB BF`가 맨 앞에 있을 때만 제거된다.
4. 정확히 한도 크기는 허용하고 한도보다 1바이트 큰 파일은 거절된다.
5. 유효한 UTF-8로 인코딩된 U+FFFD 자체는 인코딩 오류로 오판하지 않는다. 해당 문자를 금지할지는 업무 검증에서 결정한다.
6. 실패한 파일은 DB에 **0건** 반영된다. 부분 반영 정책이라면 그 규칙대로 기록된다.
7. 거절 사유와 원본 파일 식별자가 관측되며, 원본 고객 데이터는 일반 로그에 남지 않는다.

운영에서 깨진 파일이 들어왔을 때는 공급자에게 “UTF-8로 다시 저장해 달라”는 모호한 요청보다, 계약 인코딩, 최초 오류 파일 ID, 원본 해시, 격리 여부를 제공하는 편이 재현에 도움이 된다. 바이트 오프셋까지 필요하다면 별도의 진단 도구나 디코더 루프를 사용하되, 민감한 원본 바이트를 공개 로그에 기록하지는 않는다. 위 간단한 `decode` 호출이 정확한 오류 바이트 오프셋을 자동으로 제공한다고 가정해서는 안 된다.

## 설계 결론

외부 텍스트 파일에서 “읽기 성공”은 “정확한 데이터 수집 성공”이 아니다. `new String(bytes, UTF_8)`의 편리함은 손상 입력을 대체 문자로 이어갈 수 있다는 의미이기도 하다. 정확성이 필요한 경계에서는 `CharsetDecoder`의 `REPORT`를 명시하고, BOM·최대 크기·파싱·업무 검증·반영 단위를 각각 독립된 정책으로 정해야 한다.

작은 파일에서는 제한된 바이트를 읽어 엄격하게 디코딩한 뒤 검증할 수 있다. 큰 파일에서는 스트리밍 디코딩을 쓰되, **뒤늦게 발견되는 오류와 이미 반영한 데이터**를 함께 설계해야 한다. 조용히 고치는 수집기보다, 원본과 실패 이유를 보존하며 명확히 거절하는 수집기가 운영 중 데이터 정합성을 지키기 쉽다.

## 근거 자료

- [Java SE 21 `String(byte[], Charset)` — malformed/unmappable 입력의 대체 동작](<https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/String.html#%3Cinit%3E(byte%5B%5D,java.nio.charset.Charset)>)
- [Java SE 21 `CharsetDecoder` — 오류 정책과 디코딩 절차](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/nio/charset/CharsetDecoder.html)
- [Java SE 21 `CodingErrorAction` — REPORT, REPLACE, IGNORE](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/nio/charset/CodingErrorAction.html)
- [Java SE 21 `InputStreamReader` — 디코더 지정과 읽기 버퍼링](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/io/InputStreamReader.html)
- [Java SE 21 `InputStream.readNBytes(int)` — 지정 길이까지 읽는 계약](<https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/io/InputStream.html#readNBytes(int)>)
- [RFC 3629 — UTF-8 문법과 BOM 관련 설명](https://www.rfc-editor.org/rfc/rfc3629)
