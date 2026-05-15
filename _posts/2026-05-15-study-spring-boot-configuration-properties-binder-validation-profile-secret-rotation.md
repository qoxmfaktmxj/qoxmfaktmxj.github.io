---
layout: post
title: "Spring Boot 설정 관리 실전: @ConfigurationProperties, Binder, Validation, Profile, Secret Rotation으로 운영 실수 줄이는 법"
date: 2026-05-15 11:40:00 +0900
categories: [java]
tags: [study, java, spring, spring-boot, configuration-properties, binder, validation, profile, secrets, backend, operations]
permalink: /java/2026/05/15/study-spring-boot-configuration-properties-binder-validation-profile-secret-rotation.html
---

## 배경: 설정은 코드보다 덜 보이지만, 운영 사고는 더 자주 만든다

Spring Boot 서비스를 오래 운영하면 코드 버그보다 설정 버그가 더 무섭다는 걸 자주 체감한다.

실제 장애는 대체로 이런 모양으로 온다.

- 운영에서만 `PAYMENT_API_KEY`가 비어 있어 애플리케이션이 부팅 직후 죽는다
- `timeout=5000` 하나를 누가 밀리초로 이해하고, 누가는 초로 이해해 외부 호출이 전부 끊긴다
- `@Value` 문자열 주입이 여기저기 흩어져 어떤 설정이 실제로 어디에 쓰이는지 팀이 설명하지 못한다
- dev/profile에서는 잘 되는데 prod/profile에서만 Bean 충돌이나 누락이 난다
- `application-prod.yml`과 환경변수 override가 겹치면서 어떤 값이 최종 승자인지 아무도 모른다
- secret rotation을 위해 값을 바꿨는데 커넥션 풀, 토큰 캐시, 클라이언트 빈은 예전 값을 계속 잡고 있다
- config server나 쿠버네티스 시크릿을 붙였지만, 바꿔도 되는 설정과 재기동이 필요한 설정을 구분하지 않아 더 혼란스러워진다

여기서 흔한 오해가 있다.

> 설정은 코드 바깥의 값일 뿐이다.

아니다. 운영 관점에서 설정은 **애플리케이션의 런타임 계약(runtime contract)** 이다.

- 어떤 값은 없으면 절대 부팅하면 안 된다
- 어떤 값은 형식만 맞으면 안 되고, 비즈니스 범위까지 검증해야 한다
- 어떤 값은 재배포 없이 바꿀 수 있어야 하고
- 어떤 값은 절대 런타임 변경 대상으로 취급하면 안 된다
- 어떤 값은 로그에 노출되면 안 되고
- 어떤 값은 여러 필드가 함께 일관성을 만족해야 한다

즉 설정 관리의 핵심은 `application.yml` 파일을 잘 쓰는 요령이 아니라, 아래 질문에 답할 수 있게 만드는 일이다.

1. 이 설정은 어떤 도메인 경계를 가진 구성 객체인가
2. 이 값이 빠지거나 이상하면 언제, 어떤 방식으로 실패해야 하는가
3. 어떤 override 경로를 공식 지원하고, 어디까지 허용할 것인가
4. secret은 어디에 두고, 누가 어떻게 회전시키며, 애플리케이션은 그 변화에 어떻게 반응하는가
5. 테스트에서 설정 계약을 어떻게 검증할 것인가

이 글은 중급 이상 개발자를 기준으로 Spring Boot의 설정 관리를 **`@ConfigurationProperties`, Binder, Validation, Profile, Secret Rotation` 중심으로 운영 기준에서 정리한다. 문법 소개보다 더 중요한 초점은 다음이다.

- 설정을 문자열 조각이 아니라 도메인 객체로 다루는 법
- fail-fast와 유연성 사이에서 어디까지 엄격해야 하는지
- profile, env var, external config를 섞을 때 경계를 어떻게 설계해야 하는지
- secret rotation과 런타임 재로딩을 어디까지 허용해야 하는지
- 테스트와 관측성을 통해 설정 사고를 배포 전에 줄이는 법

이 글의 결론을 먼저 한 줄로 요약하면 이렇다.

> Spring Boot 설정 관리의 핵심은 값을 주입하는 것이 아니라, **운영에서 바뀔 수 있는 계약을 타입·검증·경계·회전 전략까지 포함해 설계하는 것**이다.

---

## 먼저 큰 그림: 설정은 "상수 모음"이 아니라 "런타임 계약"이다

팀에서 설정을 다룰 때 흔히 두 가지 극단으로 흐른다.

- 모든 값을 `@Value`로 빨리 꽂아 넣는다
- 반대로 모든 것을 동적 설정으로 만들고 언제든 바꿀 수 있게 하려 한다

둘 다 장기적으로는 비용이 크다.

`@Value("${foo.bar}")`는 처음엔 빠르다. 하지만 서비스가 커질수록 아래 문제가 바로 생긴다.

- 문자열 키가 코드 전역에 흩어진다
- 같은 의미의 값이 여러 위치에서 중복 주입된다
- 기본값, 단위, 허용 범위, 관련 필드 조합이 한 곳에 모이지 않는다
- 어떤 설정이 실제 필수인지 코드만 보고 판단하기 어렵다
- 리팩터링 시 IDE가 도메인 단위로 도와주지 못한다

반대로 모든 설정을 런타임 변경 가능하게 만들면 또 다른 문제가 생긴다.

- Bean 초기화 시점에 결정돼야 할 설정까지 중간에 바꾸려 한다
- 커넥션 풀 크기, thread pool, datasource credential처럼 재기동이 자연스러운 값까지 hot reload 대상으로 착각한다
- 여러 설정이 동시 변경돼야 의미가 있는데 일부만 반영돼 불일치 상태가 생긴다
- 누가 언제 무엇을 바꿨는지 운영 추적이 어려워진다

그래서 먼저 나눠야 할 것은 기술이 아니라 **설정의 성격**이다.

### 설정은 보통 네 종류로 나뉜다

1. **부팅 필수 설정**
   - 없으면 애플리케이션이 시작되면 안 된다
   - 예: 외부 API base URL, datasource URL, 필수 credential

2. **부팅 시 구조를 결정하는 설정**
   - Bean 생성, pool 크기, 기능 활성화 여부처럼 런타임 변경이 부자연스럽다
   - 예: executor size, cache backend 선택, feature module on/off

3. **운영 튜닝 설정**
   - timeout, retry 횟수, 배치 청크 크기처럼 조정 가능하지만 검증과 관찰이 필요하다
   - 예: read timeout, max attempts, backoff, poll interval

4. **비밀 값(secret)**
   - 저장 위치, 노출 통제, 회전 방식이 일반 설정과 달라야 한다
   - 예: API key, DB password, signing key

이 분류가 먼저 잡혀야 아래 판단이 쉬워진다.

- `@ConfigurationProperties`로 타입화할지
- `@Validated`로 부팅 차단할지
- profile로 갈지, 조건부 Bean으로 갈지
- 재배포가 필요한지, 런타임 리로드를 허용할지
- 시크릿 매니저를 붙일지, env var로 충분한지

즉 설정 관리의 첫 단추는 YAML 문법이 아니라 **변경 모델(change model)** 을 정의하는 일이다.

---

## 핵심 개념 1: `@ConfigurationProperties`는 편의 기능이 아니라 "설정 도메인 모델링" 도구다

Spring Boot 설정 관리에서 가장 큰 분기점은 `@Value`를 얼마나 빨리 졸업하느냐다.

`@Value`가 나쁜 것은 아니다. 아주 국소적인 한두 값에는 여전히 쓸 수 있다. 예를 들면 이런 수준이다.

- 빌드 버전 표시
- 단순 feature flag 한 개
- 테스트에서만 쓰는 임시 플래그

하지만 아래 징후가 보이면 거의 확실히 `@ConfigurationProperties`로 올려야 한다.

- 관련 값이 3개 이상 묶여 있다
- 단위 변환이나 기본값이 있다
- 값들 사이의 제약 조건이 있다
- 여러 컴포넌트가 같은 설정 집합을 공유한다
- 팀이 그 설정 묶음을 도메인 개념으로 부르고 있다

예를 들어 결제 파트너 호출 설정은 대체로 하나의 객체여야 한다.

```java
@ConfigurationProperties(prefix = "partner.payment")
@Validated
public record PaymentClientProperties(
        @NotNull URI baseUrl,
        @NotNull Duration connectTimeout,
        @NotNull Duration readTimeout,
        @Min(1) @Max(5) int maxAttempts,
        @NotNull Duration backoff,
        @NotBlank String apiKey,
        boolean enabled
) {}
```

이렇게 잡으면 좋은 점이 많다.

- `partner.payment.*`가 하나의 경계로 드러난다
- 타입 변환이 자동으로 된다
- 필수값과 범위를 선언적으로 검증할 수 있다
- IDE 메타데이터와 자동완성이 더 좋아진다
- 테스트에서 구성 객체 단위로 검증하기 쉽다
- 같은 설정을 여러 Bean이 공유해도 의미가 흩어지지 않는다

### 왜 `@Value`보다 구조적으로 유리한가

`@Value` 기반 코드는 보통 이렇게 퍼진다.

```java
@Component
public class PaymentClient {

    public PaymentClient(
            @Value("${partner.payment.base-url}") String baseUrl,
            @Value("${partner.payment.connect-timeout:1000}") long connectTimeout,
            @Value("${partner.payment.read-timeout:3000}") long readTimeout,
            @Value("${partner.payment.api-key:}") String apiKey
    ) {
        // ...
    }
}
```

이 방식의 문제는 단순히 예쁘지 않다는 수준이 아니다.

- `1000`, `3000`이 ms인지 sec인지 생성자만 봐선 약하다
- `api-key`가 빈 문자열이어도 진짜 허용인지 모호하다
- 같은 설정을 다른 Bean에서도 다시 주입하면 기준이 분산된다
- `base-url` 문자열 검증을 각 클래스가 알아서 해야 한다
- 관련 값 묶음이 리팩터링 단위가 되지 못한다

반면 `@ConfigurationProperties`는 “문자열 키를 소비하는 코드”를 “타입이 있는 구성 객체를 소비하는 코드”로 바꾼다.

```java
@Configuration
@EnableConfigurationProperties(PaymentClientProperties.class)
public class PaymentClientConfig {

    @Bean
    RestClient paymentRestClient(PaymentClientProperties properties) {
        // properties 기반으로 생성
        return RestClient.builder().baseUrl(properties.baseUrl().toString()).build();
    }
}
```

이제 나머지 애플리케이션은 키 이름을 몰라도 된다. `partner.payment.base-url`을 아는 코드는 설정 바인딩 계층으로 제한된다.

### 설정 객체는 "기술별"이 아니라 "문제별"로 나눠야 한다

설정 모델링에서 또 자주 하는 실수가 있다.

- `ClientProperties`
- `FeatureProperties`
- `CommonProperties`

이렇게 너무 추상적으로 묶는 것이다. 그러면 다시 거대한 쓰레기통 객체가 된다.

더 좋은 기준은 **운영에서 함께 바뀌고 함께 이해돼야 하는가**다.

예를 들어 아래는 같은 객체로 묶는 편이 자연스럽다.

- 파트너 결제 API base URL
- connect/read timeout
- retry/backoff
- 인증 헤더 키

반면 아래는 분리하는 편이 낫다.

- 결제 API 호출 설정
- 결제 후 비동기 정산 배치 설정
- 결제 웹훅 검증 설정

모두 “결제”와 관련 있어도 변경 주체, 장애 영향도, 운영 주기가 다르기 때문이다.

즉 `@ConfigurationProperties`는 YAML 구조 예쁘게 만드는 도구가 아니라, **운영에서 함께 설명해야 하는 값들을 한 경계로 묶는 도구**다.

---

## 핵심 개념 2: Binder를 이해해야 단위, 기본값, 리스트, 맵, 중첩 객체를 안전하게 다룰 수 있다

Spring Boot Binder는 생각보다 강력하다. 많은 팀이 단순 문자열 바인딩 정도로만 여기지만, 실무에서 중요한 부분은 오히려 아래다.

- `Duration`, `DataSize`, `URI`, `InetAddress` 같은 타입 변환
- kebab-case / camelCase / underscore 환경변수 매핑
- 리스트, 맵, 중첩 객체 바인딩
- 생성자 바인딩을 통한 불변 객체 구성
- 기본값과 null 의미 분리

이걸 이해하지 못하면 설정이 "잘 읽히는 것처럼 보이지만 실제 의미는 불명확한 상태"가 된다.

### 단위가 있는 값은 문자열이나 숫자로 남기지 말자

아래 두 설정을 보자.

```yaml
partner:
  payment:
    connect-timeout: 500
    read-timeout: 3000
```

이 값만 보고는 팀이 합의하지 않으면 의미가 불명확하다.

- 500ms인가
- 500초인가
- 과거엔 ms였는데 누군가 sec라고 오해한 건 아닌가

그래서 timeout, TTL, 주기, 크기 같은 값은 가능하면 타입으로 바꿔야 한다.

```java
@ConfigurationProperties(prefix = "partner.payment")
public record PaymentClientProperties(
        Duration connectTimeout,
        Duration readTimeout,
        DataSize maxResponseSize
) {}
```

```yaml
partner:
  payment:
    connect-timeout: 500ms
    read-timeout: 3s
    max-response-size: 2MB
```

이렇게 되면 좋은 점이 명확하다.

- 문서 없이도 의미가 드러난다
- 잘못된 단위를 부팅 시점에 더 빨리 잡을 수 있다
- 코드 내부에서는 `Duration` 연산을 바로 할 수 있다
- 설정 리뷰가 훨씬 쉬워진다

### 기본값은 "없으면 이 값"인지 "명시적으로 0/false를 허용"하는지 분리해야 한다

운영에서 자주 겪는 문제는 기본값이 너무 조용히 적용된다는 점이다.

예를 들어 `retry.max-attempts=0`이 의미 있는 값인지, 아니면 설정 누락을 감추는 값인지 구분이 필요하다.

record 기반 설정 객체에서는 이런 식으로 기본값을 줄 수 있다.

```java
@ConfigurationProperties(prefix = "batch.cleanup")
public record CleanupJobProperties(
        @DefaultValue("false") boolean enabled,
        @DefaultValue("1000") int chunkSize,
        @DefaultValue("30s") Duration lockTtl
) {}
```

하지만 운영적으로 더 중요한 질문은 이것이다.

> 기본값이 정말 안전한가, 아니면 누락을 조용히 덮어 버리는가?

예를 들면:

- `chunkSize=1000`은 안전한 기본값이 될 수 있다
- `apiKey=""`는 대개 안전한 기본값이 아니다
- `baseUrl=http://localhost:8080`도 운영 서비스에는 위험한 기본값이다
- `enabled=false`는 기능 토글에 따라 안전할 수 있지만, 필수 파이프라인이라면 오히려 장애 은닉이 될 수 있다

즉 기본값은 편의 장치이지만, **필수 계약을 흐리게 만들면 안 된다**.

### 리스트와 맵은 강력하지만, override 규칙을 이해하지 못하면 독이 된다

예를 들어 다수 파트너 엔드포인트를 맵으로 받을 수 있다.

```java
@ConfigurationProperties(prefix = "routing")
public record RoutingProperties(
        Map<String, URI> partnerEndpoints,
        List<String> bypassCountries
) {}
```

이 패턴은 좋다. 다만 profile이나 env var override가 섞이면 리스트/맵 병합 규칙이 생각보다 직관적이지 않을 수 있다. 누군가는 “추가”된다고 기대하지만 실제로는 “대체”되기도 한다.

그래서 운영에서 자주 바뀌는 리스트/맵 설정은 아래를 함께 정해야 한다.

- 전체 교체인지 부분 교체인지
- profile 파일에서 덮을지 외부 파일에서 덮을지
- env var로 다뤄도 사람이 실수 없이 관리 가능한지

특히 길고 중첩된 리스트를 환경변수로 관리하는 것은 대부분 좋지 않다. 사람이 운영 콘솔에서 실수할 확률이 매우 높다.

### 생성자 바인딩과 불변성이 주는 운영상 이점

Spring Boot 3에서는 record 기반 불변 설정 객체가 꽤 자연스럽다. 이 방식의 진짜 장점은 단순 취향이 아니다.

- 설정이 한 번 바인딩되면 중간에 변경되지 않는다
- 필수값 누락이 더 빨리 드러난다
- `setter` 기반 부분 초기화 상태를 줄인다
- 테스트에서 예상 상태를 만들기 쉽다

설정은 일반 도메인 엔티티보다 오히려 불변에 가까운 편이 안전하다. 런타임 중간에 setter로 변경 가능한 설정 객체는 추적이 더 어렵다.

---

## 핵심 개념 3: Validation은 "예쁘게 검사"하는 기능이 아니라 "잘못된 부팅을 막는 차단기"다

설정 검증에서 가장 흔한 실수는 형식 변환만 되면 된다고 생각하는 것이다.

예를 들어 Binder가 아래 값을 문제 없이 읽었다고 해 보자.

- `read-timeout: 0ms`
- `max-attempts: 999`
- `base-url: http://localhost`
- `cron: every day`

기술적으로는 일부가 바인딩될 수 있다. 하지만 운영적으로는 거의 틀린 값일 가능성이 높다.

그래서 Validation의 목표는 단순히 DTO 검사가 아니라 **잘못된 운영 배포를 시작 단계에서 차단하는 것**이다.

### `@Validated`와 Bean Validation을 적극적으로 써야 하는 이유

```java
@ConfigurationProperties(prefix = "partner.payment")
@Validated
public record PaymentClientProperties(
        @NotNull URI baseUrl,
        @NotNull Duration connectTimeout,
        @NotNull Duration readTimeout,
        @Min(1) @Max(3) int maxAttempts,
        @NotNull Duration backoff,
        @NotBlank String apiKey
) {}
```

이 정도만 해도 꽤 많은 사고를 막는다.

- 빠진 secret
- 0 이하 재시도 횟수
- null timeout
- 빈 문자열 credential

하지만 실무에서는 필드 단독 검증보다 **필드 간 관계 검증**이 더 중요할 때가 많다.

예를 들어 이런 규칙이 있을 수 있다.

- `connectTimeout < readTimeout`
- `maxAttempts > 1`이면 `backoff`는 0이 아니어야 함
- `enabled=false`면 `apiKey`를 요구하지 않음
- `mode=WEBHOOK`이면 `webhookSecret` 필수

이런 경우는 커스텀 검증이나 초기화 로직에서 명시적으로 막는 편이 낫다.

```java
@ConfigurationProperties(prefix = "partner.payment")
@Validated
public record PaymentClientProperties(
        boolean enabled,
        URI baseUrl,
        Duration connectTimeout,
        Duration readTimeout,
        int maxAttempts,
        Duration backoff,
        String apiKey
) {
    public PaymentClientProperties {
        if (enabled && (apiKey == null || apiKey.isBlank())) {
            throw new IllegalArgumentException("partner.payment.api-key is required when enabled=true");
        }
        if (connectTimeout != null && readTimeout != null && !connectTimeout.minus(readTimeout).isNegative()) {
            throw new IllegalArgumentException("connect-timeout must be smaller than read-timeout");
        }
    }
}
```

문법 취향은 다를 수 있다. 중요한 것은 **설정 제약이 코드에 명시적으로 드러나야 한다**는 점이다.

### fail-fast가 대체로 맞지만, 항상 그런 것은 아니다

운영 관점에서 기본 원칙은 이렇다.

> 필수 설정이 이상하면 서비스는 조용히 살아 있지 말고, 아예 부팅에 실패하는 편이 낫다.

이 원칙이 특히 중요한 경우:

- 결제, 인증, 정산, 데이터 적재처럼 핵심 기능이 걸린 설정
- 잘못 떠도 일부 요청만 은근히 실패하는 유형
- 장애가 늦게 드러날수록 피해가 커지는 유형

예를 들면 결제 서비스가 `apiKey` 없이 떠서 10분 뒤 첫 결제 요청에서야 401을 뱉는 것보다, 배포 시점에 바로 죽는 쪽이 훨씬 낫다.

다만 완전 fail-fast만이 정답은 아니다. 예외도 있다.

- 선택 기능(feature module)로 비활성화 가능한 경우
- 특정 외부 연동이 없으면 일부 기능만 막고 코어는 살릴 수 있는 경우
- 개발 환경에서 편의상 샘플 기본값이 허용되는 경우

이때도 중요한 것은 조용한 degrade가 아니라 **의도된 degrade** 여야 한다는 점이다.

- 로그에 명확히 남길 것
- health indicator나 startup banner에서 상태를 노출할 것
- 해당 기능이 비활성화됐음을 운영자가 즉시 알 수 있을 것

### 검증 실패 메시지도 운영 자산이다

검증을 잘 걸어도 메시지가 불친절하면 밤중 장애 대응 때 오히려 시간을 잡아먹는다.

나쁜 예:

- `Failed to bind properties under 'foo.bar'`
- `Validation failed for object='...'`

더 좋은 예:

- `partner.payment.api-key is required when enabled=true`
- `batch.cleanup.chunk-size must be between 100 and 5000`
- `report.storage.s3-bucket must not be blank in prod profile`

설정 검증 메시지는 개발자 친화성보다 **운영자 복구 속도**에 직접 영향을 준다.

---

## 핵심 개념 4: Profile은 환경 분리 도구이지, 논리 분기 남용 도구가 아니다

Spring 팀에서 오래 일한 개발자일수록 `@Profile` 과다 사용의 비용을 잘 안다. 처음엔 깔끔해 보이지만, 일정 규모를 넘기면 어떤 Bean이 어떤 환경에서 살아나는지 정신 모델이 무너진다.

### profile이 잘 맞는 경우

- 로컬 개발용 fake adapter와 운영용 real adapter 전환
- dev/stage/prod처럼 인프라 구성이 본질적으로 다른 환경
- 완전히 별도 datasouce나 stub client를 써야 하는 테스트 환경

예를 들면 아래는 비교적 자연스럽다.

```java
@Configuration
@Profile("local")
class LocalMailConfig {
    @Bean
    MailSender mailSender() {
        return new FakeMailSender();
    }
}

@Configuration
@Profile("prod")
class ProdMailConfig {
    @Bean
    MailSender mailSender(MailProperties properties) {
        return new SmtpMailSender(properties.host(), properties.port());
    }
}
```

### profile이 남용되기 쉬운 경우

- 기능 토글을 전부 profile로 표현
- 고객사별 분기를 profile로 표현
- 운영 튜닝 값 차이를 profile로 계속 복제
- `prod`, `prod-a`, `prod-b`, `prod-k8s`, `prod-dr` 식으로 끝없이 늘어남

이 시점부터는 profile이 환경 분리 도구가 아니라 **조건문 숨김 장치**가 된다.

### profile보다 속성 기반 분기가 나은 경우가 많다

예를 들어 저장소 구현을 바꾸고 싶다면 아래처럼 속성 기반 조건이 더 읽기 쉬울 때가 많다.

```java
@Configuration
class StorageConfig {

    @Bean
    @ConditionalOnProperty(prefix = "storage", name = "type", havingValue = "s3")
    ObjectStorage s3Storage(S3StorageProperties properties) {
        return new S3ObjectStorage(properties);
    }

    @Bean
    @ConditionalOnProperty(prefix = "storage", name = "type", havingValue = "local")
    ObjectStorage localStorage(LocalStorageProperties properties) {
        return new LocalObjectStorage(properties.basePath());
    }
}
```

이 방식의 장점은 다음과 같다.

- 결정 기준이 설정 값으로 드러난다
- profile 조합을 외워야 하지 않는다
- 같은 환경에서도 값만 바꿔 전략을 바꿀 수 있다
- 테스트에서 특정 속성만 주입해 분기를 재현하기 쉽다

### 파일 우선순위와 override 경로를 팀 규칙으로 고정해야 한다

Spring Boot는 다양한 설정 소스를 지원한다.

- `application.yml`
- `application-{profile}.yml`
- 환경변수
- JVM system properties
- 커맨드라인 인자
- 외부 config import
- 쿠버네티스 ConfigMap / Secret 마운트

문제는 “유연하다”가 곧 “예측 가능하다”는 뜻은 아니라는 점이다.

운영 혼란을 줄이려면 팀 차원에서 아래를 미리 정하는 게 좋다.

1. 공통 기본값은 어디에 둔다
2. 환경별 차이는 profile 파일에 둘지, 외부 주입으로 뺄지
3. secret은 절대 Git에 두지 않는지
4. 운영 override의 공식 경로가 env var인지, mounted file인지, config server인지
5. 긴 구조화 설정은 env var 대신 파일 기반으로 제한할지

내 기준은 대체로 이렇다.

- **작고 단순한 스칼라 값 override**: env var 가능
- **구조화된 리스트/맵/중첩 객체**: 외부 파일이나 config import 권장
- **secret**: 전용 secret store 또는 secret mount 우선
- **기능 분기**: profile 남용보다 속성 기반 조건 우선

즉 profile은 강력하지만, 무한 분기용으로 쓰기 시작하면 결국 “이 서버에서 왜 이 Bean이 떴지?”라는 질문에 아무도 빨리 답하지 못하게 된다.

---

## 핵심 개념 5: Secret은 일반 설정이 아니다 — 저장 위치, 노출 경로, 회전 전략을 따로 설계해야 한다

많은 팀이 secret을 `application-prod.yml` 밖으로 빼는 것까지만 하고 끝낸다. 물론 Git에 넣지 않는 것은 기본이다. 하지만 운영적으로는 거기서부터가 시작이다.

secret을 제대로 다루려면 최소한 네 가지를 분리해서 생각해야 한다.

1. **저장**: 어디에 보관하는가
2. **주입**: 애플리케이션에 어떤 경로로 전달하는가
3. **노출 통제**: 로그, 에러 메시지, actuator, dump에서 새지 않는가
4. **회전**: 값이 바뀔 때 누가 어떤 순서로 반영하는가

### secret 주입 경로는 "편한 것"보다 "사고 면적이 작은 것"이 중요하다

자주 보는 선택지는 아래다.

- 환경변수
- 파일 마운트
- Vault / AWS Secrets Manager / GCP Secret Manager 같은 외부 secret store
- 쿠버네티스 Secret + volume/env injection

각 방식의 장단점은 분명하다.

- **환경변수**
  - 장점: 간단하고 어디서나 지원된다
  - 단점: 프로세스 환경 dump, 운영 콘솔 노출, 복잡한 구조 표현 한계

- **파일 마운트**
  - 장점: 긴 값, 인증서, 키 파일 관리에 유리
  - 단점: 파일 변경 감지와 권한 관리 전략이 필요하다

- **외부 secret store**
  - 장점: 접근 제어, 감사 로그, 회전 자동화가 강하다
  - 단점: 부팅 의존성, 네트워크 실패, SDK/연동 복잡성이 생긴다

어떤 것을 고르든 중요한 원칙은 같다.

- secret은 애플리케이션 로그에 절대 노출되지 않게 할 것
- `toString()`이나 예외 메시지에 그대로 실리지 않게 할 것
- actuator env/configprops 노출 정책을 검토할 것
- secret 값을 일반 설정 객체 전체 로그와 함께 찍지 말 것

### secret rotation은 "값만 바꾸면 끝"이 아니다

운영에서 자주 놓치는 지점이 바로 회전이다. 예를 들어 결제 API key를 바꿨다고 하자. 그러면 실제로는 아래 질문이 따라온다.

- 기존 in-flight 요청은 어떤 키를 쓰는가
- connection pool이나 client bean이 키를 캐시하는가
- upstream가 구 키와 신 키를 일정 시간 동시 허용하는가
- 롤백 시 이전 키로 되돌리는 절차가 있는가
- 애플리케이션 재기동이 필요한가, 무중단 반영이 가능한가

즉 secret rotation은 단순 저장소 문제가 아니라 **프로토콜과 운영 절차 문제**다.

특히 아래 유형은 재기동 없는 회전이 생각보다 어렵다.

- datasource password
- TLS key / certificate
- 장기 보관되는 SDK client 내부 credential
- startup 시점에 토큰을 교환해 캐시하는 클라이언트

이 경우 억지로 동적 반영을 시도하는 것보다, **짧은 재배포/롤링 재시작이 더 단순하고 안전한 전략**일 때가 많다.

### secret을 설정 객체에 넣더라도 취급은 달라야 한다

`@ConfigurationProperties`에 secret을 포함하는 것 자체는 괜찮다. 다만 아래 기준은 꼭 지키는 편이 좋다.

- secret 포함 객체를 통째로 로그하지 않는다
- actuator `env`, `configprops` 노출을 최소화한다
- health endpoint 응답에 secret 존재 여부를 지나치게 상세히 싣지 않는다
- 진단 로그에서는 길이, hash, 마지막 4자리 정도만 제한적으로 쓴다

예를 들어 아래는 좋지 않다.

```java
log.info("payment properties={}", properties);
```

record나 data class의 자동 `toString()`이 secret까지 노출할 수 있기 때문이다.

운영팀이 밤중에 로그를 뒤지는 순간, 가장 조용히 터지는 사고가 바로 이런 종류다.

---

## 핵심 개념 6: 모든 설정을 동적 리로드 대상으로 만들지 말자 — 재기동이 자연스러운 값과 아닌 값을 구분해야 한다

설정 관리 성숙도가 올라가면 곧바로 나오는 요구가 있다.

> 값을 바꿨을 때 재배포 없이 바로 반영되면 더 좋지 않을까?

물론 어떤 경우에는 맞다. 하지만 여기서 욕심을 내면 시스템이 오히려 덜 예측 가능해진다.

### 동적 반영이 잘 맞는 설정

- 배치 주기, 청크 크기 같은 운영 튜닝 값
- feature flag 성격의 토글
- 외부 API timeout, retry 정도의 보수적 튜닝 값
- 읽기 전용 캐시 TTL 같은 비핵심 파라미터

### 동적 반영이 까다롭거나 재기동이 더 나은 설정

- datasource URL, username, password
- thread pool core size / max size
- Netty/Tomcat 서버 포트와 커넥터 구조
- Bean graph 자체를 바꾸는 설정
- 여러 필드가 원자적으로 동시에 바뀌어야 의미가 있는 설정

문제는 팀이 이 둘을 구분하지 않고 “가능하면 다 hot reload”로 가기 쉽다는 점이다.

동적 설정은 다음 비용을 늘린다.

- 어떤 시점에 어떤 값이 유효했는지 추적 비용
- 일부 Bean은 바뀌고 일부는 예전 값을 쓰는 불일치 위험
- 레이스 컨디션과 관측 난이도
- 테스트 복잡성

### `@RefreshScope`류의 도구는 문제를 해결하기도 하지만, 추상화 비용도 크다

Spring Cloud 계열을 쓰면 특정 Bean에 refresh 메커니즘을 붙일 수 있다. 이것이 필요한 경우도 있다. 다만 아래를 반드시 생각해야 한다.

- refresh 시점에 기존 객체와 신규 객체가 동시에 살아도 괜찮은가
- in-flight 요청은 어떤 값을 쓰는가
- 캐시된 토큰/세션/커넥션은 어떻게 정리되는가
- refresh 이벤트 실패 시 롤백 또는 재시도 전략이 있는가

많은 경우 운영 현실은 더 단순하다.

- 바뀌는 빈도가 낮다
- 재기동 비용이 크지 않다
- 롤링 재배포 체계가 이미 있다

그렇다면 억지 동적 반영보다 **짧고 예측 가능한 재배포 절차**가 더 낫다.

좋은 기준은 이렇다.

> 값이 바뀌었을 때 애플리케이션 내부 상태도 함께 재구성돼야 한다면, 동적 리로드보다 재기동을 기본값으로 두는 편이 안전하다.

---

## 핵심 개념 7: 설정 테스트는 통합 테스트의 부가물이 아니라, 배포 전 계약 검증 단계다

설정 사고의 많은 부분은 코드 테스트가 아니라 **설정 계약 테스트**로 더 빨리 잡을 수 있다.

### `ApplicationContextRunner` 같은 도구로 바인딩 계약을 잘라서 검증하자

설정 객체 검증에는 전체 스프링 부팅이 과할 때가 많다. 아래처럼 작은 단위 검증이 매우 유용하다.

```java
class PaymentClientPropertiesTest {

    private final ApplicationContextRunner contextRunner = new ApplicationContextRunner()
            .withUserConfiguration(TestConfig.class)
            .withPropertyValues(
                    "partner.payment.base-url=https://api.partner.com",
                    "partner.payment.connect-timeout=500ms",
                    "partner.payment.read-timeout=2s",
                    "partner.payment.max-attempts=2",
                    "partner.payment.backoff=200ms",
                    "partner.payment.api-key=test-key"
            );

    @Test
    void bindsProperties() {
        contextRunner.run(context -> {
            var properties = context.getBean(PaymentClientProperties.class);
            assertThat(properties.readTimeout()).isEqualTo(Duration.ofSeconds(2));
        });
    }
}
```

이 테스트가 주는 이점은 꽤 크다.

- 설정 키 변경이 기존 계약을 깨는지 빨리 알 수 있다
- 기본값 동작을 문서 대신 테스트로 고정할 수 있다
- 검증 실패 메시지를 실제로 확인할 수 있다
- profile/override 조합 일부를 작게 재현할 수 있다

### 설정 스모크 테스트가 특히 중요한 경우

- 외부 secret store 연동
- profile별 Bean graph 차이
- prod 전용 필수 설정
- 데이터소스, 메시지 브로커, object storage 같은 인프라 의존성

이 경우에는 아주 얇은 startup smoke test가 큰 가치를 만든다.

- prod-like profile로 최소 부팅 가능 여부 확인
- 필수 env var 누락 시 명확히 실패하는지 확인
- actuator health에서 비정상 상태가 어떻게 보이는지 확인

### 문서보다 테스트가 강한 이유

운영 위키에 “이 값은 초 단위입니다”라고 써 두는 것보다, `Duration` 바인딩과 검증 테스트를 걸어 두는 편이 훨씬 오래 간다. 사람은 위키를 덜 읽고, 배포 파이프라인은 테스트를 안 지나가면 멈춘다.

설정은 특히 그렇다. 문서가 낡아도 서비스는 뜬다. 하지만 테스트가 깨지면 배포가 멈춘다. 운영 안정성 측면에서는 그 차이가 크다.

---

## 실무 예시 1: 결제 파트너 클라이언트 설정을 "문자열 주입"에서 "계약 모델"로 바꾸기

문제 상황을 가정해 보자.

- 결제 파트너 A 호출용 `RestClient`가 있다
- base URL, timeout, retry, api key가 필요하다
- 운영/스테이징/로컬 환경마다 값이 다르다
- key rotation이 분기마다 한 번씩 일어난다
- 장애가 나면 timeout/retry를 빠르게 조정해야 한다

많은 팀의 첫 구현은 이런 느낌이다.

```java
@Service
public class PartnerPaymentClient {

    private final RestClient restClient;
    private final String apiKey;
    private final int maxAttempts;

    public PartnerPaymentClient(
            RestClient.Builder builder,
            @Value("${partner.payment.base-url}") String baseUrl,
            @Value("${partner.payment.api-key}") String apiKey,
            @Value("${partner.payment.max-attempts:1}") int maxAttempts
    ) {
        this.restClient = builder.baseUrl(baseUrl).build();
        this.apiKey = apiKey;
        this.maxAttempts = maxAttempts;
    }
}
```

처음엔 된다. 하지만 시간이 지나면 아래가 곧 따라온다.

- connect/read timeout 추가
- backoff 추가
- 특정 상태코드만 retry
- 운영에서 partner disable 스위치 추가
- API key rotation 절차 추가

이 시점에서 구조를 올리는 편이 낫다.

```java
@ConfigurationProperties(prefix = "partner.payment")
@Validated
public record PaymentClientProperties(
        boolean enabled,
        @NotNull URI baseUrl,
        @NotNull Duration connectTimeout,
        @NotNull Duration readTimeout,
        @Min(1) @Max(3) int maxAttempts,
        @NotNull Duration backoff,
        @NotBlank String apiKey
) {}
```

```java
@Configuration
@EnableConfigurationProperties(PaymentClientProperties.class)
public class PartnerPaymentClientConfig {

    @Bean
    @ConditionalOnProperty(prefix = "partner.payment", name = "enabled", havingValue = "true")
    PartnerPaymentClient partnerPaymentClient(
            RestClient.Builder builder,
            PaymentClientProperties properties
    ) {
        // timeout, retry, header 주입 등 구성
        return new PartnerPaymentClient(builder, properties);
    }
}
```

```yaml
partner:
  payment:
    enabled: true
    base-url: https://api.partner-payments.com
    connect-timeout: 300ms
    read-timeout: 1500ms
    max-attempts: 2
    backoff: 200ms
```

운영상 장점은 분명하다.

- 어떤 값을 조정 가능한지 한 객체에서 보인다
- 비활성화 조건이 명시적이다
- timeout과 retry를 구조적으로 검증할 수 있다
- secret만 외부 secret source에서 override하는 전략을 쓰기 쉽다
- 클라이언트 재구성 필요 여부를 판단하기 쉬워진다

그리고 중요한 한 가지. **api key rotation은 설정 저장소 문제로 끝나지 않는다.**

- 롤링 재배포로 반영할지
- refresh 메커니즘으로 반영할지
- 파트너가 old/new key 동시 허용 윈도우를 제공하는지
- 실패 시 이전 키로 되돌릴 운영 절차가 있는지

이 질문에 답하지 않으면 “secret store 붙였다”는 사실만으로는 운영 안전성이 올라가지 않는다.

---

## 실무 예시 2: 배치 작업 설정에서 chunk, 락 TTL, 동시성을 안전하게 다루기

배치/스케줄링 설정은 특히 숫자 몇 개를 대충 박아 두기 쉽다. 그런데 여기서 사고가 많이 난다.

예를 들어 정산 배치가 있고 설정 항목이 아래 같다고 하자.

- 실행 주기
- 청크 크기
- worker 동시성
- 분산 락 TTL
- 재처리 lookback 기간

이걸 전부 `@Value` 숫자 주입으로 처리하면, 어느 순간 운영에서 아래가 벌어진다.

- chunk size를 100000으로 올려 DB 부하 폭증
- lock TTL을 30초로 둬서 아직 돌고 있는 작업 위에 중복 실행 시작
- worker concurrency를 DB connection pool보다 크게 잡아 스스로 병목 생성
- lookback period와 watermark 정책이 충돌해 중복 처리 발생

이런 설정은 묶어서 봐야 한다.

```java
@ConfigurationProperties(prefix = "settlement.job")
@Validated
public record SettlementJobProperties(
        @NotBlank String cron,
        @Min(100) @Max(5000) int chunkSize,
        @Min(1) @Max(16) int workerConcurrency,
        @NotNull Duration lockTtl,
        @NotNull Duration lookback,
        boolean enabled
) {
    public SettlementJobProperties {
        if (lockTtl != null && lockTtl.compareTo(Duration.ofMinutes(1)) < 0) {
            throw new IllegalArgumentException("settlement.job.lock-ttl must be at least 1 minute");
        }
    }
}
```

여기서 진짜 중요한 것은 필드 하나하나보다 **관계 규칙**이다.

- `workerConcurrency <= datasource.maxPoolSize - headroom`
- `lockTtl >= 예상 최대 처리 시간`
- `chunkSize` 증가는 DB write batch 전략과 같이 조정
- `lookback` 증가는 멱등성/중복 제거 전략과 세트로 검토

이 관계는 보통 YAML만 봐서는 잘 안 보인다. 그래서 설정 객체 + 검증 + 운영 문서 + 메트릭을 함께 가져가야 한다.

좋은 운영 패턴은 보통 이렇다.

- 청크 크기와 동시성 변경은 배포 노트에 남긴다
- 실행 시간, 처리량, DB saturation을 함께 본다
- lock TTL 변경은 배치 최대 처리 시간 관측과 같이 움직인다
- 긴급 튜닝 가능한 값과 재배포 필요한 값을 분리한다

즉 배치 설정은 단순 숫자 모음이 아니라 **처리량-정합성-중복 실행 위험을 조절하는 제어판**이다.

---

## 실무 예시 3: profile 파일 지옥을 피하면서 멀티 환경 구성을 단순화하기

환경이 늘어나면 흔히 이렇게 된다.

- `application.yml`
- `application-local.yml`
- `application-dev.yml`
- `application-stage.yml`
- `application-prod.yml`
- `application-prod-k8s.yml`
- `application-prod-dr.yml`

처음에는 편하지만, 어느 순간부터 아래 질문에 답하기 어려워진다.

- prod-dr는 prod를 얼마나 상속하는가
- stage와 prod 차이는 정확히 무엇인가
- 어떤 값은 Git에 있고 어떤 값은 환경변수에 있는가
- 누가 어떤 값을 override했는가

이런 상황에서 내가 선호하는 원칙은 **프로파일은 구조 차이만, 운영 값 차이는 외부 주입 우선** 이다.

예를 들면:

- `application.yml`: 공통 기본값과 로컬에서도 안전한 기본 정책
- `application-local.yml`: 로컬 개발용 fake adapter, 더 관대한 로그 레벨
- `application-prod.yml`: 운영 공통 구조 선택
- 세부 운영 값: env var 또는 mounted external file
- secret: secret store 또는 secret mount

이렇게 하면 얻는 장점이 있다.

- Git에 있는 환경 파일 수가 과도하게 늘지 않는다
- 환경별 구조 차이와 운영 수치 차이를 분리할 수 있다
- 스테이징/프로덕션에서 같은 artifact를 더 자연스럽게 재사용한다
- 값 차이를 배포 파이프라인이나 인프라 레이어에서 통제하기 쉽다

물론 trade-off도 있다.

- 인프라 자동화가 약하면 외부 주입 관리가 더 어려울 수 있다
- 운영 콘솔에서 env var가 많아지면 가독성이 떨어질 수 있다
- 구조화된 긴 설정은 file mount 쪽이 더 적합할 수 있다

그래도 핵심은 같다.

> profile 파일을 계속 늘려 복잡성을 숨기기보다, 어떤 값이 코드 저장소에 있고 어떤 값이 배포 환경에 있는지 경계를 명확히 하는 편이 장기적으로 낫다.

---

## 트레이드오프: 강한 설정 계약은 안전하지만, 변경 유연성을 줄일 수 있다

설정 관리를 엄격하게 할수록 분명히 좋아지는 점이 있다.

- 잘못된 배포를 더 일찍 막는다
- 타입과 검증 덕분에 리뷰가 쉬워진다
- 운영 중 원인 추적 속도가 빨라진다
- 설정 의도가 코드 구조에 남는다

하지만 비용도 있다.

### 1. fail-fast는 안전하지만, 일부 기능만 degrade하는 유연성은 줄어든다

예를 들어 추천 시스템 연동이 부가 기능이라면, 설정 누락 시 전체 서비스 부팅 실패가 과할 수도 있다. 이때는 `enabled=false` 기반 degrade가 더 낫다.

반대로 결제, 인증처럼 핵심 기능이면 degrade보다 fail-fast가 맞다.

즉 기준은 기술이 아니라 **비즈니스 임계도**다.

### 2. 불변 설정 객체는 예측 가능하지만, 동적 변경에는 덜 유연하다

record 기반 불변 객체는 안전하다. 다만 런타임 refresh를 강하게 요구하는 환경에서는 추가 설계가 필요하다.

- 새 설정 스냅샷 교체 전략
- refresh 시점 일관성
- 기존 Bean 재생성 비용

그래서 “변경 가능해야 한다”는 요구가 있을수록 먼저 물어야 한다.

- 정말 실시간 동적 변경이 필요한가
- 롤링 재배포로 충분하지 않은가
- 변경 실패 시 되돌림 전략이 있는가

### 3. 속성 기반 조건은 읽기 좋지만, 조합이 많아지면 테스트 부담이 늘어난다

`@ConditionalOnProperty`는 profile 남용을 줄여 주지만, 분기 수가 늘어나면 테스트 케이스도 늘어난다. 결국 어떤 분기든 **허용하는 조합의 수를 줄이는 설계**가 중요하다.

### 4. 외부 secret store는 보안과 감사에 강하지만, 부팅 의존성과 운영 복잡성을 추가한다

Vault나 Secrets Manager는 강력하다. 하지만 네트워크/권한/토큰 만료/부팅 의존성을 더한다. 작은 서비스나 단순 내부 도구라면 쿠버네티스 Secret + 짧은 롤링 재시작이 더 실용적일 수 있다.

즉 최고의 해법은 없다. 다만 아래 정도는 꽤 보편적으로 유효하다.

- 핵심 설정은 타입화하고 검증한다
- secret은 일반 설정과 다른 취급을 한다
- 동적 반영은 꼭 필요한 값만 허용한다
- override 경로를 팀 규칙으로 고정한다

---

## 흔한 실수: 설정 자체보다 "설정의 책임"을 모호하게 두는 것이 더 위험하다

실무에서 특히 자주 보는 실수를 정리하면 이렇다.

### 1. `@Value`를 너무 오래 붙잡는다

초기 속도는 빠르지만, 결국 문자열 키가 코드 전체에 퍼진다. 설정이 도메인 객체가 아니라 전역 상수처럼 흐르기 시작하면 나중에 수습 비용이 커진다.

### 2. timeout, TTL, 크기 값을 숫자로만 둔다

`5000`, `60`, `1024` 같은 숫자는 문맥이 빠지면 거의 항상 오해를 만든다. `Duration`, `DataSize`로 올리는 것만으로도 사고 확률이 크게 줄어든다.

### 3. 기본값이 설정 누락을 숨긴다

필수 credential에 빈 문자열 기본값을 주거나, 중요한 endpoint를 localhost 기본값으로 두면 테스트는 편해져도 운영 사고는 더 커진다.

### 4. profile을 조건문 대용으로 쓴다

환경 분리를 넘어서 고객사별, 기능별, 세부 튜닝별로 profile을 늘리면 결국 Bean graph를 아무도 설명하지 못하게 된다.

### 5. secret이 포함된 설정 객체를 그대로 로그한다

운영 진단 중 가장 쉽게 새는 경로가 바로 로그다. `toString()` 습관 하나로 사고가 난다.

### 6. hot reload를 만능처럼 본다

값이 바뀌면 객체 내부 상태와 외부 연결도 같이 바뀌어야 하는 설정이 많다. 이걸 무시한 동적 반영은 조용히 더 위험한 상태를 만든다.

### 7. 설정 테스트를 하지 않는다

코드 로직 테스트만 있고 설정 계약 테스트가 없으면, 배포 파이프라인은 “코드는 맞는데 설정은 틀린” 상태를 막지 못한다.

### 8. override 경로를 팀 규칙으로 정하지 않는다

어떤 값은 YAML, 어떤 값은 env var, 어떤 값은 JVM 옵션, 어떤 값은 콘솔 수동 입력으로 흩어져 있으면 원인 추적 속도가 급격히 느려진다.

---

## 오늘 바로 적용할 체크리스트

아래 체크리스트만 점검해도 설정 사고를 꽤 줄일 수 있다.

- 관련 설정 3개 이상이 `@Value`로 흩어져 있다면 `@ConfigurationProperties`로 묶었는가
- timeout, TTL, 크기 값을 `Duration`, `DataSize` 같은 타입으로 올렸는가
- 필수값 누락 시 서비스가 조용히 뜨지 않고 명확히 실패하는가
- `@Validated`와 범위 검증이 핵심 설정에 적용돼 있는가
- 필드 간 관계 규칙을 코드에서 명시적으로 검증하는가
- profile이 환경 분리 이상으로 과도하게 분기 수를 늘리고 있지 않은가
- 운영 override의 공식 경로가 팀 내에서 하나로 정리돼 있는가
- secret이 로그, actuator, 예외 메시지에 노출되지 않도록 막았는가
- secret rotation 절차가 저장소 변경 외에 애플리케이션 반영 방식까지 포함하는가
- 동적 리로드 허용 대상과 재기동 대상 설정을 구분했는가
- prod-like 설정으로 최소 부팅 스모크 테스트가 있는가
- 설정 객체 단위 바인딩/검증 테스트가 CI에 포함돼 있는가

---

## 마무리: 좋은 설정 관리는 "값을 바깥으로 빼는 일"이 아니라 "운영 변경을 설계하는 일"이다

Spring Boot는 설정을 다루기 편한 프레임워크다. 문제는 편리함이 곧 설계 품질을 보장하지 않는다는 점이다.

애플리케이션이 커질수록 설정은 단순한 외부화 값이 아니라 아래를 동시에 담게 된다.

- 어떤 기능이 어떤 조건에서 켜지는가
- 무엇이 필수 계약이고 무엇이 선택 옵션인가
- 어떤 변화는 재배포 없이 허용할 것인가
- 비밀 값은 어디에 저장하고 어떻게 회전할 것인가
- 운영자가 장애 시 어떤 메시지로 문제를 좁혀 갈 수 있는가

이 관점이 생기면 몇 가지 변화가 따라온다.

- `@Value`가 빠른 해법이 아니라 임시 해법처럼 보이기 시작한다
- 설정 구조를 도메인 경계로 묶게 된다
- 기본값을 넣기 전에 “이게 누락 은닉은 아닌가”를 먼저 묻게 된다
- hot reload 요구를 들었을 때도 먼저 일관성과 복구 전략을 따지게 된다
- secret을 단순 문자열이 아니라 운영 수명주기를 가진 자산으로 보게 된다

결국 좋은 설정 관리는 YAML을 잘 쓰는 기술이 아니다. **배포 후에도 설명 가능한 상태를 유지하도록 런타임 계약을 설계하는 기술**이다.

이 기준만 팀에 자리 잡아도, “왜 prod에서만 안 뜨지?”, “왜 값은 바꿨는데 반영이 안 됐지?”, “왜 secret rotation 후 일부 인스턴스만 깨지지?” 같은 질문의 상당수를 배포 전에 줄일 수 있다.

---

## 한 줄 정리

Spring Boot 설정 관리의 핵심은 프로퍼티를 읽는 것이 아니라, **설정이라는 런타임 계약을 타입·검증·override 경계·secret 회전 전략까지 포함해 운영 가능하게 설계하는 것**이다.
