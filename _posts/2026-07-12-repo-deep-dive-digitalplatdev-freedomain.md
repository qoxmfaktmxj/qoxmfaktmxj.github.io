---
layout: post
title: "Repo Deep Dive: DigitalPlatDev/FreeDomain - 무료 이름을 신청하고 DNS와 갱신까지 관리하기"
date: 2026-07-12 08:04:56 +0900
categories: [github-repo-analysis]
tags: [github, domain, dns, nameserver, documentation, free-domain]
repo: DigitalPlatDev/FreeDomain
analyzed_at: 2026-10-16
analyzed_commit: 9c7c54110705760267b07b6e6a6d406d1172a1bf
---

웹사이트를 처음 공개할 때는 서버보다 주소를 먼저 고민하기도 한다. 개인 소개 페이지나 작은 오픈소스 프로젝트에 기억하기 쉬운 이름을 붙이고 싶은데, 도메인 등록부터 비용이 든다. DigitalPlat FreeDomain은 지원하는 이름 공간 아래에서 공개 이름을 등록하고, 사용자가 고른 DNS와 호스팅에 연결하도록 돕는 서비스다. 이 저장소는 그 서비스를 이용하는 안내서와 DNS 학습 자료를 제공한다.

이번 글은 2026년 10월 16일 확인한 공식 자료를 기준으로 새로 작성했다. 공식 홈페이지와 약관, 저장소의 신청 및 갱신 안내를 확인했으며 계정 생성이나 실제 등록은 하지 않았다. 대시보드는 조사 환경에서 접근이 제한되어 로그인 이후의 최신 신청 화면은 확인하지 못했다. 아래 절차는 공식 문서를 따라 설명하되, 특정 이름의 신청 가능 여부나 최종 비용을 확인한 것으로 읽어서는 안 된다.

## 먼저 무엇을 받는 서비스인지 구분한다

공식 홈페이지는 `*.dpdns.org`, `*.us.kg`, `*.qzz.io`, `*.xx.kg`, `*.qd.je`를 공개 이름 공간으로 안내한다. 예를 들어 `example.dpdns.org`처럼 접미사 앞에 원하는 이름을 붙이는 형태다. 다섯 개의 최상위 도메인을 무료로 소유하는 상품이라는 뜻은 아니다. 운영 약관은 이를 제공되는 이름 공간 아래의 공개 서브도메인 등록으로 설명한다. 상위 이름 공간 자체나 영구적인 도메인 소유권을 판매하는 서비스도 아니다. [공식 홈페이지](https://domain.digitalplat.org/)와 [이용약관](https://domain.digitalplat.org/terms-of-service/)에서 이 범위를 확인할 수 있다.

등록한 이름은 외부 권한 DNS 서버에 위임할 수 있다. 권한 DNS는 그 이름에 대한 실제 레코드를 보관하고 답하는 서버다. FreeDomain에서 이름을 확보한 뒤 외부 DNS에 웹사이트 주소를 적고, 별도로 준비한 호스팅에서 페이지를 제공하는 구조다. 개인 사이트, 커뮤니티 안내 페이지, 학습용 배포처럼 이름과 서버를 직접 연결해 보고 싶은 사람이 활용할 수 있다.

저장소를 내려받는 일과 서비스에 가입하는 일도 다르다. [README](https://github.com/DigitalPlatDev/FreeDomain/blob/9c7c54110705760267b07b6e6a6d406d1172a1bf/README.md)는 FreeDomain 저장소를 공개 안내 및 학습 자료로 소개하고, 애플리케이션 소스는 별도 [Domain-OSS 저장소](https://github.com/DigitalPlatDev/Domain-OSS)에 있다고 명시한다. FreeDomain을 복제했다고 운영 서비스 계정이나 이름을 얻는 것은 아니다. 저장소의 [AGPL-3.0 라이선스](https://github.com/DigitalPlatDev/FreeDomain/blob/9c7c54110705760267b07b6e6a6d406d1172a1bf/LICENSE)도 공개 자료의 이용 조건이며 등록 서비스의 승인이나 유지 조건을 대신하지 않는다.

## 무료라는 안내 다음에 확인할 조건

[FAQ](https://github.com/DigitalPlatDev/FreeDomain/blob/9c7c54110705760267b07b6e6a6d406d1172a1bf/documents/domains/faq.md)에 적힌 기본 한도는 사용자 계정당 도메인 한 개다. 확보한 이름 아래에 `blog.example.dpdns.org` 같은 하위 이름을 만드는 작업은 외부 DNS에서 할 수 있다. 이것을 FreeDomain에서 별도 이름을 계속 무료 등록할 수 있다는 의미로 확대하면 안 된다. 같은 FAQ는 GitHub 별표가 필수 조건이 아니라고도 명시한다.

서비스 약관에는 제한된 무료 슬롯과 추가 등록 용량을 위한 Buy Slot이 구분되어 있다. 슬롯은 신청 가능 용량이며, Buy Slot은 그 용량을 늘리는 일회성 서비스 요금이다. 특정 이름의 확보나 영구 사용권, 향후 갱신을 보장하는 구매가 아니다. 접미사 목록만 보고 모두 같은 조건으로 등록할 수 있다고 판단할 수는 없다. 현재 슬롯 수와 접미사별 요구 조건, 표시되는 요금은 신청 직전에 확인한다. [이용약관의 슬롯 정책](https://domain.digitalplat.org/terms-of-service/)이 판단 근거다.

신청 자격도 확인해야 한다. 약관은 최소 13세를 제시하면서 거주지 법률이 더 높은 연령을 요구하면 그 기준을 따르도록 하고, 미성년자는 보호자의 동의와 감독을 요구한다. 조직을 대신해 신청하는 사람에게는 그 조직을 대표할 권한도 필요하다. 실제 적용 조건은 신청자가 약관에서 확인해야 한다.

유지 조건은 요금만의 문제가 아니다. [허용 이용 정책](https://domain.digitalplat.org/acceptable-use-policy/)은 피싱, 악성코드, 스팸, 사칭과 함께 다중 계정으로 무료 용량을 늘리거나 제한을 우회하는 행위를 금지한다. 등록 정보는 정확하게 유지하고, 보안이나 악용 신고에 응답해야 한다. 외부 호스팅에서 문제가 발생했더라도 그 주소로 연결하는 사용자의 책임이 사라지는 것은 아니다. 이름을 받은 뒤에도 공개하는 서비스와 계정 관리를 계속 맡아야 한다.

## 계정을 만들기 전에 DNS 서비스부터 고른다

신청에 필요한 기본 준비물은 계속 접근할 수 있는 이메일, 정확한 이름 또는 조직명, 연락처와 주소다. 이메일은 복구와 정책 안내를 받는 통로이므로 곧 접근을 잃을 수 있는 수단은 운영에 불리하다. 공식 [계정 생성 안내](https://github.com/DigitalPlatDev/FreeDomain/blob/9c7c54110705760267b07b6e6a6d406d1172a1bf/documents/tutorial/platform/1.1-account-registration.md)는 실제 정보를 입력하고, 연락 정보와 청구 정보를 구분해 검토하도록 설명한다. 정보가 어떻게 수집되고 이용되는지는 [개인정보 처리방침](https://domain.digitalplat.org/privacy-policy/)을 함께 읽어야 한다.

다음으로 사용할 외부 DNS를 정한다. DNS 조회 기능만 있는 서비스가 아니라, 등록하려는 전체 이름의 존을 만들고 권한 네임서버 호스트명을 제공할 수 있어야 한다. 존은 그 이름 아래의 DNS 설정을 담는 관리 단위다. 외부 DNS가 배정한 네임서버 값은 FreeDomain에 넣고, 웹사이트나 메일 레코드는 그 외부 DNS에서 관리한다.

공식 연결 안내에는 Cloudflare 화면이 등장하지만 이는 인터페이스 예시다. DigitalPlat이 해당 업체를 보증한다는 뜻은 아니며, 외부 서비스의 지원 범위와 요금, 보안 설정은 별도로 확인해야 한다. 무료 도메인 등록에 DNS, 웹 서버, 이메일 계정의 모든 비용이 함께 포함되는 것은 아니다. [제품 범위 안내](https://github.com/DigitalPlatDev/FreeDomain/blob/9c7c54110705760267b07b6e6a6d406d1172a1bf/documents/tutorial/platform/1.0-product-boundaries.md)는 웹 파일 업로드, 서버 구성, HTTPS 인증서와 메일함을 별도 작업으로 구분한다.

## 원하는 이름을 확인하고 결과를 기록한다

공식 문서의 신청 흐름은 대시보드 공지 확인부터 시작한다. 등록 중단, 접미사별 제한, 슬롯이나 가격이 바뀔 수 있으므로 오래된 화면을 따라 바로 제출하는 방식은 피한다. 원하는 이름을 외부 DNS에 추가해 배정받은 네임서버를 준비한 뒤, 대시보드의 Register에서 이름과 접미사를 선택하고 Check availability로 확인한다. 확인 대상은 짧은 이름 부분만이 아니라 결과로 만들어지는 전체 주소다.

최종 제출 전에는 전체 철자, 접미사, 네임서버 호스트명, 등록자 정보, 정책 동의와 표시된 슬롯 또는 요금을 검토한다. 네임서버 자리에 웹 서버 IP나 공개 DNS 리졸버 주소를 넣으면 역할이 맞지 않는다. 공식 안내의 `ns1.dns-service.example` 같은 값은 형식을 설명하는 가상 호스트명이다. 실제 신청에서는 선택한 DNS 서비스가 배정한 값을 넣어야 한다. [도메인 등록 안내](https://github.com/DigitalPlatDev/FreeDomain/blob/9c7c54110705760267b07b6e6a6d406d1172a1bf/documents/tutorial/platform/1.2-domain-registration.md)가 이 확인 순서를 제공한다.

제출 이후에는 Domain List에서 정확한 이름과 상태, 만료일을 확인한다. 신청 버튼을 눌렀다는 사실과 등록 완료는 다르다. 보류 또는 거절로 표시되면 화면의 사유를 확인한다. 이름 중복, 잘못된 네임서버, 불완전한 등록 정보나 접미사 제한을 살피는 단계다. 성공한 경우에도 만료일과 담당 계정을 비공개 관리 기록에 남겨야 이후 갱신을 놓치지 않는다.

## DNS 연결은 두 화면을 오가는 작업이다

FreeDomain과 외부 DNS는 서로 다른 설정을 맡는다. FreeDomain에는 이름의 권한을 어느 네임서버에 위임할지 저장한다. 외부 DNS에는 그 이름으로 웹사이트, 메일이나 검증 서비스를 찾는 방법을 저장한다. 외부 DNS의 존에서 NS 레코드만 고쳐 놓고 FreeDomain의 위임 설정을 그대로 두면 상위에서 찾아가는 경로가 바뀌지 않을 수 있다.

[공식 네임서버 연결 예제](https://github.com/DigitalPlatDev/FreeDomain/blob/9c7c54110705760267b07b6e6a6d406d1172a1bf/documents/tutorial/platform/1.3-connect-nameservers.md)는 외부 DNS에 전체 도메인을 추가하고 배정된 네임서버를 빠짐없이 복사한 뒤, FreeDomain의 등록 또는 관리 화면에 저장하도록 안내한다. 이어 다음 명령으로 위임된 값을 확인한다.

```bash
dig NS example.dpdns.org
```

이는 공식 문서의 설명용 명령이며 이 글에서 실행하지 않았다. 실제 확인 시에는 예시 도메인을 본인의 이름으로 바꾸고, 응답에 표시된 NS가 저장한 네임서버와 일치하는지 본다. 위임이 맞더라도 웹사이트 레코드를 만들지 않았다면 접속할 목적지는 아직 없다.

외부 DNS에서는 호스팅이 요구하는 레코드를 만든다. 직접 서버를 운영하는 경우 A는 IPv4, AAAA는 IPv6 주소를 연결하고, `www` 같은 별칭은 CNAME을 쓸 수 있다. 메일 서비스는 MX와 해당 업체가 요구하는 TXT 등을 별도로 설정한다. [DNS 레코드 교재](https://github.com/DigitalPlatDev/FreeDomain/blob/9c7c54110705760267b07b6e6a6d406d1172a1bf/documents/tutorial/dns/2.1-record-types.md)에 나오는 `192.0.2.10`은 문서용 예시 주소다. 그대로 복사하지 말고 실제 호스팅에서 지정한 값을 사용해야 한다.

문제가 생기면 어느 단계까지 성공했는지 나누어 확인한다. Domain List에 이름이 없으면 등록 상태부터 본다. 이름은 있지만 NS가 다르면 위임 설정을 확인한다. NS는 맞고 A가 없으면 외부 DNS 존을 본다. DNS가 맞는데 웹 연결이 실패하면 서버와 방화벽을 확인하고, HTTP는 되지만 HTTPS가 실패하면 인증서와 웹 서버 설정을 살핀다. [배포 안내](https://github.com/DigitalPlatDev/FreeDomain/blob/9c7c54110705760267b07b6e6a6d406d1172a1bf/documents/tutorial/website/3.5-deploy-and-connect.md)는 DNS 조회와 실제 HTTP 응답 확인을 별도 단계로 둔다. 기다리는 것만으로 누락된 레코드나 서버 설정이 만들어지지는 않는다.

## 유지와 갱신까지 신청 과정에 포함한다

이름이 처음 연결되었다면 다음 확인 대상은 만료일이다. [상태 및 갱신 안내](https://github.com/DigitalPlatDev/FreeDomain/blob/9c7c54110705760267b07b6e6a6d406d1172a1bf/documents/tutorial/platform/1.4-status-and-renewal.md)는 등록 상태와 만료일의 기준을 대시보드로 정한다. 갱신 기간, 비용, 슬롯 규칙과 유예 처리는 바뀔 수 있다고 명시하므로, 모든 접미사에 같은 기간이나 자동 무료 갱신이 적용된다고 가정하지 않는다.

운영 기록에는 도메인, 담당자, 계정 이메일, 만료일, 외부 DNS와 호스팅을 함께 적어 두면 좋다. 공식 문서는 만료 90일, 60일, 30일, 7일 전 알림을 예로 들지만 이는 알림 일정의 예시다. 갱신 버튼이 열리는 기간이라는 뜻은 아니다. 실제 갱신 가능 기간을 확인한 다음 그 안에서 담당자가 행동하도록 알림을 정한다.

갱신 시에는 현재 공지와 연락처를 확인하고, 표시된 결과와 요금 및 슬롯 사용을 검토한 뒤 한 번 제출한다. 그다음 Domain List에서 새 만료일을 확인해야 완료로 볼 수 있다. 응답이 불분명하다고 반복 제출하기보다 먼저 현재 상태를 확인한다. 만료나 정지로 상위 위임이 중단되었다면 외부 DNS의 A 레코드를 고치는 것만으로 복구할 수 없다.

사용을 끝낼 때도 이름을 그냥 방치하지 않는다. [만료 및 운영 교재](https://github.com/DigitalPlatDev/FreeDomain/blob/9c7c54110705760267b07b6e6a6d406d1172a1bf/documents/tutorial/operations/5.2-renewal-and-expiration.md)는 이메일, 계정 복구, OAuth 콜백과 신뢰 목록 등에서 해당 이름을 제거하도록 안내한다. 나중에 다른 사람이 같은 이름을 등록할 가능성을 고려해야 하기 때문이다. 무료로 시작한 실험이라도 다른 서비스의 신뢰 관계에 연결했다면 정리 작업이 필요하다.

이 저장소는 등록 방법만 보고 끝내기보다 [학습 가이드](https://github.com/DigitalPlatDev/FreeDomain/blob/9c7c54110705760267b07b6e6a6d406d1172a1bf/LEARN.md)를 따라 DNS와 배포까지 이해할 때 유용하다. 제품별 신청 절차와 일반적인 DNS 교재가 분리되어 있어, 정책 변경과 기술 개념을 혼동하지 않고 읽을 수 있다. 약관상 별도 서면 보장이 없는 서비스는 최선 노력 기준이며 지속적인 가용성이나 갱신을 약속하지 않는다. 중요한 서비스에 연결하려면 이름의 중단 가능성과 다른 주소로 옮길 경로까지 고려해야 한다.

## 이어 읽을 공식 자료

- [DigitalPlat Domains 홈페이지](https://domain.digitalplat.org/): 공개 이름 공간과 공식 신청 입구
- [이용약관](https://domain.digitalplat.org/terms-of-service/), [허용 이용 정책](https://domain.digitalplat.org/acceptable-use-policy/), [개인정보 처리방침](https://domain.digitalplat.org/privacy-policy/): 신청과 유지에 적용되는 서비스 정책
- [FreeDomain 튜토리얼 목차](https://github.com/DigitalPlatDev/FreeDomain/blob/9c7c54110705760267b07b6e6a6d406d1172a1bf/documents/tutorial/index.md): 계정, 신청, 위임, 갱신과 일반 DNS 교재
- [FreeDomain FAQ](https://github.com/DigitalPlatDev/FreeDomain/blob/9c7c54110705760267b07b6e6a6d406d1172a1bf/documents/domains/faq.md): 문서상 기본 한도와 외부 DNS 이용 범위
