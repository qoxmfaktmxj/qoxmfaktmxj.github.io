---
layout: post
title: "Python 데이터 검증: Pydantic으로 안전한 코드 작성하기"
date: 2026-02-14 17:33:09 +0900
categories: [python]
tags: [study, python, backend, automation]
---

# Python 데이터 검증: Pydantic으로 안전한 코드 작성하기

## 왜 중요한가?

실무 프로젝트에서 API 요청, 데이터베이스 입력, 설정 파일 파싱 등 외부 데이터를 다룰 때 타입 검증은 필수입니다. Pydantic을 사용하면 런타임 에러를 사전에 방지하고, 자동 문서화와 IDE 자동완성을 얻을 수 있습니다.

## 핵심 개념

- **BaseModel**: Pydantic의 기본 클래스로 데이터 구조를 정의하고 자동 검증
- **타입 힌팅**: Python 타입 어노테이션으로 필드의 데이터 타입 명시
- **Validators**: 커스텀 검증 로직으로 비즈니스 규칙 적용
- **직렬화/역직렬화**: JSON, dict 간 자동 변환으로 API 통신 간편화
- **에러 처리**: 구조화된 ValidationError로 명확한 오류 메시지 제공

## 실전 예제

    from pydantic import BaseModel, Field, validator
    from typing import Optional
    from datetime import datetime

    class UserProfile(BaseModel):
        name: str = Field(..., min_length=2, max_length=50)
        email: str
        age: int = Field(..., ge=0, le=150)
        bio: Optional[str] = None
        created_at: datetime = Field(default_factory=datetime.now)

        @validator('email')
        def validate_email(cls, v):
            if '@' not in v:
                raise ValueError('유효한 이메일 형식이 아닙니다')
            return v.lower()

        @validator('name')
        def validate_name(cls, v):
            if not v.replace(' ', '').isalpha():
                raise ValueError('이름은 문자만 포함해야 합니다')
            return v.strip()

    # 사용 예
    try:
        user = UserProfile(
            name="김개발",
            email="dev@example.com",
            age=28
        )
        print(user.dict())  # {'name': '김개발', 'email': 'dev@example.com', ...}
        print(user.json())  # JSON 문자열
    except Exception as e:
        print(f"검증 실패: {e}")

## 흔한 실수

1. **타입 힌팅 생략**: `name: str` 대신 `name` 만 작성하면 검증이 작동하지 않음
2. **Optional 오용**: `Optional[str]` 사용 시 `None` 값이 자동으로 허용되므로 필수 필드는 명시적으로 `...` 사용
3. **Validator 순서 무시**: 여러 validator가 있을 때 실행 순서를 고려하지 않으면 예상치 못한 결과 발생
4. **에러 메시지 무시**: ValidationError의 상세 정보를 활용하지 않으면 디버깅이 어려움
5. **성능 고려 부족**: 대량의 데이터 검증 시 복잡한 validator는 성능 저하 유발

## 오늘의 실습 체크리스트

- [ ] Pydantic 설치 확인: `pip install pydantic`
- [ ] 간단한 BaseModel 클래스 정의 (최소 3개 필드)
- [ ] Field 제약조건 추가 (min_length, ge, le 등)
- [ ] 커스텀 validator 1개 이상 작성
- [ ] 유효한 데이터와 잘못된 데이터로 테스트
- [ ] ValidationError 메시지 확인 및 분석
- [ ] dict() 및 json() 메서드로 직렬화 테스트
- [ ] 실제 프로젝트의 API 요청 모델에 적용해보기

**팁**: Pydantic v2는 성능이 크게 개선되었으니 최신 버전 사용을 권장합니다.
