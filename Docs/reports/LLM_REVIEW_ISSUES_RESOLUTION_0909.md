# LLM PR 검토사항 3건 조치 기록

- 조치일: `2026-09-09`
- 대상: 문서 참조, API 정본, 빈 문자열 422 경계
- 관련 검수: `Docs/reports/LLM_INTEGRATION_AUDIT_0909.md`

## 1. 끊어진 Backend 문서 참조

`LLM/Bakcend_readme.md` 삭제 후 남아 있던 `LLM/RUN_GUIDE.md` 참조를 제거하고 다음 정본
경로로 교체했다.

```text
../Docs/Design/LLM_API_SPEC_V1.md
```

## 2. Backend↔LLM API 정본

`Docs/Design/LLM_API_SPEC_V1.md`를 Backend↔LLM API의 Single Source of Truth로 선언했다.
기존 `Docs/Design/LLM_API_SPEC.md`는 초기 초안 기록으로 보존한다. 두 문서가 충돌하면
V1을 우선한다.

Router, 부분 재색인, timeout처럼 아직 담당자 합의가 필요한 세부사항은
`Docs/Design/BACKEND_LLM_INTEGRATION_HANDOFF.md`에 별도로 표시하고, 합의 결과를 V1의 다음
버전에 반영한다.

## 3. 빈 문자열 422와 조용한 fallback

### 원인

LLM request schema는 경비 분석의 `category`, `vendor`와 공고 요약의 `rawContent`에 빈
문자열을 허용하지 않는다. Backend는 LLM의 HTTP 오류를 `None`으로 변환하므로 422 원인이
로그에 남지 않고 fallback 또는 Backend 기본 동작으로 전환될 수 있었다.

### 해결

LLM 검증은 유지했다. 빈 원문으로 모델을 호출하거나 잘못된 입력을 정상 요청으로
간주하지 않기 위해 schema 제약을 완화하지 않았다.

Backend 경계에서 다음을 적용했다.

1. `Backend/core/llm_client.py`
   - 경비 `category` 공백 → `미분류`
   - 경비 `vendor` 공백 → `상호 미상`
   - 빈 품목 문자열 제거
   - 공고 원문이 공백이면 LLM 호출 생략
   - HTTP 오류의 status, `error.code`, `retryable`을 기록
   - URL, 요청 본문, 오류 message와 자격증명은 로그에서 제외
2. `Backend/services/policy_service.py`
   - 공고 원문을 trim한 후 빈 값이면 LLM 호출 전에 명시적 422 반환
   - 사용자는 `공고문 원문이 없어 AI 요약을 생성할 수 없습니다.` 오류를 받음

### 결과

- 경비 분석은 Backend의 비어 있는 문자열 때문에 LLM schema 422로 실패하지 않는다.
- 공고 원문이 없으면 LLM API와 존재하지 않는 fallback을 호출하지 않는다.
- LLM이 다른 이유로 4xx/5xx를 반환해도 최소한 상태와 안전한 오류 코드가 Backend 로그에
  남아 조용한 성능 저하를 구분할 수 있다.
- LLM 쪽 입력 검증과 환각·불필요한 비용 방지 원칙은 유지된다.

## 4. 검증

Backend 경계 테스트는 다음을 확인한다.

- 공백 category·vendor 정규화
- 빈 공고 원문에서 LLM 호출 생략
- 공고 서비스의 명시적 422
- LLM 오류 로그에서 URL·오류 message 미노출

검증 결과:

```text
Backend unittest: 4 passed
LLM pytest:       222 passed
```

LLM 전체 회귀 테스트로 기존 계약과 Graph 동작이 유지되는 것도 확인했다. 실제 OpenAI,
Cohere, PostgreSQL 호출은 수행하지 않았다.
