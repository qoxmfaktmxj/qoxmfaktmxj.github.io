---
layout: post
title: "Repo Deep Dive: Genymobile/scrcpy"
date: 2026-09-16 09:13:37 +0900
categories: [github-repo-analysis]
tags: [github, architecture, backend, open-source, deep-dive]
repo: Genymobile/scrcpy
stars: 149712
analyzed_at: 2026-09-16
---

## 1. 이 repo가 중요한 이유

scrcpy는 Android 기기를 PC에서 미러링하고 제어하는 오픈소스 프로젝트로, 149K+ 스타를 받은 성숙한 프로젝트입니다. 백엔드 아키텍처 관점에서 USB/TCP 통신, 실시간 비디오 스트리밍(FFmpeg), 저지연 입력 제어, 크로스플랫폼 호환성을 모두 구현한 복잡한 시스템 설계의 좋은 사례입니다.

## 2. 한 문장 요약

C 기반의 경량 Android 미러링 도구로, 클라이언트-서버 아키텍처를 통해 USB/TCP 연결로 실시간 비디오/오디오 스트리밍과 저지연 입력 제어를 35~70ms 지연시간으로 구현합니다.

## 3. 제품/문제 정의

Android 기기를 PC에서 제어하려면 기존에 무거운 에뮬레이터나 복잡한 설정이 필요했습니다. scrcpy는 다음 문제를 해결합니다: (1) 루트 권한 불필요, (2) 앱 설치 불필요, (3) 경량성(네이티브 C), (4) 높은 성능(30~120fps), (5) 낮은 지연시간(35~70ms), (6) 빠른 시작(~1초), (7) 크로스플랫폼 지원(Linux/Windows/macOS).

## 4. 아키텍처 구조

클라이언트-서버 이중 구조: (1) 클라이언트(C+SDL2): PC에서 실행되는 GUI 앱으로 비디오 렌더링, 입력 이벤트 수집, 키보드/마우스/게임패드 처리. (2) 서버(Java/Android): 기기에서 실행되는 APK로 화면 캡처, 오디오 포워딩, 입력 이벤트 주입. (3) 통신: USB ADB 또는 TCP/IP를 통한 양방향 통신. (4) 비디오 파이프라인: Android의 MediaProjection API → H.264/H.265 인코딩 → FFmpeg 디코딩 → SDL2 렌더링. (5) 오디오 파이프라인: AudioRecord → AAC 인코딩 → 클라이언트 재생. (6) 입력 제어: 키보드/마우스 이벤트 → 서버로 전송 → KeyEvent/MotionEvent 주입.

## 5. 핵심 모듈

1. app/: C 클라이언트 (main.c, screen.c, input_manager.c, controller.c) - SDL2 기반 GUI, 이벤트 루프, 렌더링. 2. server/: Java 서버 (Server.java, ScreenEncoder.java, AudioEncoder.java, Controller.java) - MediaProjection, 인코딩, 입력 주입. 3. FFmpeg 통합: 비디오 디코딩, 포맷 변환. 4. SDL2: 크로스플랫폼 윈도우/렌더링. 5. ADB 통신: USB/TCP 연결 관리. 6. Meson 빌드 시스템: 크로스플랫폼 컴파일. 7. 입력 처리: HID(Human Interface Device) 시뮬레이션, 게임패드 지원.

## 6. 백엔드 개발자가 배울 점

1. 프로토콜 설계: 간단한 바이너리 프로토콜로 클라이언트-서버 통신 (프레임 헤더, 타입, 데이터). 2. 저지연 설계: 버퍼링 최소화, 프레임 드롭 전략, 적응형 비트레이트. 3. 크로스플랫폼: 조건부 컴파일(#ifdef), 플랫폼별 입력 처리(Linux/Windows/macOS). 4. 리소스 관리: 메모리 누수 방지, 스레드 안전성(뮤텍스/세마포어). 5. 성능 최적화: 네이티브 C 사용, 불필요한 복사 제거, 효율적인 인코딩 설정. 6. 확장성: 모듈화 설계로 새로운 기능(카메라, 가상 디스플레이, V4L2) 추가 용이. 7. 문서화: 상세한 doc/ 폴더로 사용자/개발자 가이드 제공.

## 7. 내 프로젝트에 훔쳐올 패턴

1. 클라이언트-서버 분리: 무거운 작업(인코딩)을 서버에, UI(렌더링)를 클라이언트에 분리. 2. 적응형 품질 조정: 네트워크 상태에 따라 해상도/비트레이트 동적 조정. 3. 프레임 드롭 전략: 지연시간 우선으로 오래된 프레임 버림. 4. 이벤트 기반 아키텍처: 입력 이벤트를 큐에 저장 후 배치 처리. 5. 플러그인 아키텍처: 비디오/오디오 코덱, 입력 방식을 플러그인처럼 교체 가능. 6. 헬스 체크: 연결 상태 모니터링, 자동 재연결. 7. 설정 계층화: 기본값 → 환경변수 → CLI 인자 → 설정파일 순서로 우선순위 적용.

## 8. 주의할 점 / 안티패턴

1. 보안: USB 디버깅 활성화 필요 → 기기 보안 위험. 공식 소스에서만 다운로드 필수 (README 경고). 2. 호환성: Android 5.0(API 21) 이상 필요, 오디오는 Android 11+ 필요. 3. 성능 한계: 네트워크 지연에 민감, 고해상도에서 프레임 드롭 가능. 4. 플랫폼 의존성: 각 OS별로 다른 입력 처리(HID, 게임패드) 필요. 5. 권한 문제: 일부 기기(Xiaomi)에서 INJECT_EVENTS 권한 추가 필요. 6. 유지보수 부담: C+Java 혼합, FFmpeg 버전 호환성, 크로스플랫폼 테스트 복잡. 7. 실시간성: 완벽한 저지연을 보장할 수 없음 (네트워크, 기기 성능 의존).

## 9. vibe-grid / vibe-hr / jarvis / ehr-harness에 적용할 아이디어

1. 원격 제어 시스템: 클라이언트-서버 분리, 이벤트 기반 입력 처리 패턴 적용. 2. 실시간 스트리밍: 적응형 비트레이트, 프레임 드롭 전략으로 저지연 구현. 3. 크로스플랫폼 앱: Meson 빌드 시스템, 조건부 컴파일로 다중 OS 지원. 4. IoT/임베디드: 경량 C 기반 클라이언트, 효율적인 프로토콜 설계. 5. 모니터링 도구: 헬스 체크, 자동 재연결, 상태 로깅 패턴. 6. 게임/입력 처리: HID 시뮬레이션, 게임패드 지원 구현. 7. 문서화 전략: 기능별 상세 문서(doc/), FAQ, 개발 가이드 제공.

## 10. Source Links

['https://github.com/Genymobile/scrcpy', 'https://github.com/Genymobile/scrcpy/blob/master/doc/build.md', 'https://github.com/Genymobile/scrcpy/blob/master/doc/develop.md', 'https://github.com/Genymobile/scrcpy/blob/master/doc/connection.md', 'https://github.com/Genymobile/scrcpy/blob/master/doc/video.md', 'https://github.com/Genymobile/scrcpy/blob/master/doc/audio.md', 'https://github.com/Genymobile/scrcpy/blob/master/doc/control.md', 'https://github.com/Genymobile/scrcpy/blob/master/FAQ.md', 'https://blog.rom1v.com/2018/03/introducing-scrcpy/', 'https://blog.rom1v.com/2023/03/scrcpy-2-0-with-audio/']
