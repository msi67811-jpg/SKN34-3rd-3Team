# Backend↔LLM 내부 API 명세서 V1

- 문서 버전: `1.0`
- 확정일: `2026-09-09`
- 상태: **Backend↔LLM API 정본(Single Source of Truth)**
- 이전 초안: `Docs/Design/LLM_API_SPEC.md` (원본 보존)

이 문서는 Backend가 LLM 서비스를 호출할 때 사용하는 내부 REST 계약의 정본이다.
기존 `LLM_API_SPEC.md`와 내용이 충돌하면 이 문서를 우선한다. 미합의 세부사항은
`BACKEND_LLM_INTEGRATION_HANDOFF.md`의 `PR 전 합의가 필요한 항목`에서 관리하고 합의 후
이 문서의 다음 버전에 반영한다.
Frontend↔Backend 계약은 `Docs/Design/API_SPEC.md`를 따른다.

## 1. 공통 규칙

- 로컬 Base URL: `http://127.0.0.1:8001`
- Docker Compose Base URL: `http://llm:8001`
- 인증: 없음. LLM 서비스는 Docker 내부망에서만 접근할 수 있어야 한다.
- Content-Type: 영수증 OCR을 제외하고 `application/json; charset=utf-8`
- 날짜: `YYYY-MM-DD`
- 금액: 원 단위 정수
- 비율·신뢰도: `0.0` 이상 `1.0` 이하 실수
- 요청 필드는 기존 Backend 경계와의 호환성을 위해 `camelCase`를 사용한다.
- 기존 LLM 구현의 `/internal/*` 경로는 구현·진단용 비공개 경로다. Backend는 이를 호출하거나 fallback 경로로 사용하지 않는다.
- 응답에 새 필드는 추가할 수 있지만 기존 필드의 이름·자료형·의미는 문서 버전 변경 없이 바꾸지 않는다.

### 답변 상태

RAG 기반 API의 `status`는 다음 값만 사용한다.

| 값 | 의미 |
| --- | --- |
| `success` | 충분한 근거로 답변 생성 성공 |
| `need_more_info` | 사용자 입력 또는 프로필 정보가 더 필요함 |
| `insufficient_evidence` | 검색은 수행했으나 답변 근거가 부족함 |
| `no_result` | 검색 결과가 없음 |
| `integration_unavailable` | Backend 제공 데이터 또는 연동 기능을 사용할 수 없음 |
| `error` | 처리 중 복구하지 못한 오류 발생 |

### 공통 오류 응답

2xx가 아닌 모든 응답은 다음 형식을 사용한다.

```json
{
  "error": {
    "code": "RAG_INDEX_NOT_READY",
    "message": "RAG index is not ready.",
    "retryable": true
  }
}
```

| HTTP | 사용 조건 |
| --- | --- |
| `400` | 의미적으로 잘못된 요청 |
| `404` | 지정한 문서 또는 리소스가 없음 |
| `409` | RAG 인덱스 미준비 등 현재 상태와 요청이 충돌함 |
| `413` | 업로드 파일 크기 초과 |
| `415` | 지원하지 않는 이미지 형식 |
| `422` | JSON 또는 필드 검증 실패 |
| `429` | 외부 모델 호출 한도 초과 |
| `502` | 외부 모델이 잘못된 결과를 반환함 |
| `503` | LLM·Embedding·DB 설정 누락 또는 서비스 사용 불가 |
| `504` | 외부 모델 또는 내부 처리 시간 초과 |

Backend는 오류의 HTTP 상태와 `error.code`를 로그에 남긴다. 사용자에게 내부 오류 메시지나 시크릿을 그대로 노출하지 않는다.

## 2. 시스템 상태

### `GET /health`

프로세스가 요청을 받을 수 있는지만 확인한다. 외부 모델이나 DB를 호출하지 않는다.

```json
{
  "status": "ok",
  "service": "policy-rag-llm",
  "version": "0.1.0",
  "components": {
    "llm": "configured",
    "embedding": "configured",
    "data_source": "postgres"
  }
}
```

구성요소 상태는 `configured`, `not_configured`, `mock`, `in_memory`, `postgres` 중 해당 구성요소에 맞는 값을 사용한다. `health=200`은 RAG 인덱스 준비를 의미하지 않는다.

### `GET /rag/ready`

RAG 요청 처리 준비 상태를 확인한다. 이 요청 자체는 인덱스를 생성하지 않는다.

```json
{
  "status": "ready",
  "index_ready": true,
  "llm_configured": true,
  "embedding_configured": true,
  "langsmith_tracing": false,
  "document_count": 9770,
  "chunk_count": 11793,
  "index_source": "cache"
}
```

- `status`: `ready` 또는 `not_ready`
- `index_source`: `cache`, `embedding` 또는 `null`

## 3. 통합 RAG 질의응답

### `POST /rag/chat`

Policy·Notice·Tax 질문을 단일 LangGraph로 처리한다.

#### Request

```json
{
  "category": "policy",
  "question": "지금 신청 가능한 서울 청년창업 지원사업이 있나요?",
  "userContext": {
    "userId": 1,
    "age": 29,
    "region": "서울",
    "businessType": "개인사업자",
    "industry": "소프트웨어",
    "businessRegisteredAt": "2026-02-01",
    "foundedAt": "2026-01-15"
  },
  "noticeResults": []
}
```

| 필드 | 필수 | 계약 |
| --- | --- | --- |
| `category` | Y | `tax`, `expense`, `saving`, `policy` 중 하나 |
| `question` | Y | 공백이 아닌 문자열, 최대 1,000자 |
| `userContext` | N | 인증 사용자 정보. 확보 가능한 경우 Backend는 항상 전달 |
| `noticeResults` | N | Backend가 조회한 실제 공고 목록 |

`userContext.userId`는 `userContext`가 존재할 때 필수이며 나머지 필드는 `null`일 수 있다. Backend가 모르는 값을 임의로 추정해서 채우지 않는다.

`noticeResults`의 각 원소는 다음 형식이다.

```json
{
  "announcementId": 10,
  "policyId": 3,
  "title": "서울 청년창업 지원사업 모집",
  "content": "공고 요약 또는 검색에 필요한 원문",
  "benefit": "사업화 자금 최대 2천만원",
  "sourceUrl": "https://example.org/announcement/10",
  "applyStartDate": "2026-09-01",
  "applyEndDate": "2026-09-30"
}
```

- `announcementId`, `title`은 필수다.
- 나머지 필드는 없거나 `null`일 수 있다.
- `noticeResults` 누락 또는 `null`: Backend 공고 조회 기능을 호출하지 못한 상태다. Notice 질문은 `integration_unavailable`로 종료한다.
- `noticeResults: []`: Backend 조회는 성공했지만 조건에 맞는 공고가 없는 상태다. `no_result`로 종료한다.
- 값이 있는 배열: LLM은 전달받은 공고만 사용하며 별도 Notice Vector 검색을 하지 않는다.

카테고리와 Graph route의 관계는 다음과 같다. `category`는 사용자 화면 분류이고 최종 `route`는 질문 의미에 따라 결정한다.

| category | 허용 route |
| --- | --- |
| `tax` | `tax` |
| `expense` | `tax` |
| `saving` | `tax`, `policy` |
| `policy` | `policy`, `notice` |

현재 모집·신청 가능 여부나 마감일을 묻는 정책 질문은 `notice`로 분류한다.

#### Response

```json
{
  "answer": "현재 조회된 공고를 기준으로 안내드립니다.",
  "sources": [
    {
      "title": "서울 청년창업 지원사업 모집",
      "url": "https://example.org/announcement/10",
      "source": "https://example.org/announcement/10",
      "excerpt": "사업화 자금 최대 2천만원"
    }
  ],
  "grounded": true,
  "route": "notice",
  "status": "success",
  "guardrail_reason": null
}
```

- `route`: `policy`, `notice`, `tax` 중 하나
- `grounded`: 답변을 뒷받침하는 실제 `sources`가 하나 이상이고 답변 검증을 통과했을 때만 `true`
- `guardrail_reason`: `out_of_scope`, `insufficient_evidence`, `generation_validation_failed` 또는 `null`
- `sources`는 실제 검색 결과 또는 Backend가 전달한 공고에서만 생성한다.
- `source`는 원천 식별자 또는 URL이고, `url`은 사용자에게 제공할 링크다. URL이 없는 문서는 `url`을 빈 문자열로 반환할 수 있다.

## 4. 세액감면 판정 근거 설명

### `POST /rag/legal-basis`

판정 자체는 Backend Rule이 수행한다. LLM은 Backend가 확정한 판정을 변경하지 않고 관련 법령 근거와 주의사항만 설명한다.

#### Request

```json
{
  "eligible": true,
  "reasons": ["나이 요건 충족", "창업 후 5년 이내"],
  "conditions": {
    "age": 29,
    "region": "서울",
    "industry": "소프트웨어",
    "businessRegisteredAt": "2026-02-01",
    "foundedAt": "2026-01-15"
  }
}
```

- `eligible`, `reasons`는 필수다.
- `conditions`와 그 하위 필드는 선택이며 누락된 값을 LLM이 추정하지 않는다.

#### Response

```json
{
  "reasons": ["나이 요건 충족", "창업 후 5년 이내"],
  "legalBasis": "관련 법령 근거 설명",
  "sources": [],
  "grounded": false,
  "status": "insufficient_evidence",
  "llmUsed": true
}
```

`reasons`와 `eligible`의 의미를 LLM이 반대로 바꾸면 안 된다. 충분한 법령 근거가 없으면 법령명·조문을 생성하지 않고 `insufficient_evidence`를 반환한다.

## 5. 영수증 OCR

### `POST /ocr/receipt`

- Content-Type: `multipart/form-data`
- 파일 필드명: `image`
- 허용 형식: `image/jpeg`, `image/png`, `image/webp`
- 최대 크기: 4 MiB

#### Response

```json
{
  "date": "2026-09-09",
  "vendor": "예시상점",
  "amount": 18000,
  "items": ["노트", "펜"],
  "category": "사무용품",
  "source": "vision",
  "llmUsed": true
}
```

- 인식하지 못한 `date`, `vendor`, `amount`, `category`는 `null`로 반환한다.
- `items`는 인식 결과가 없으면 빈 배열이다.
- LLM은 모르는 필드를 샘플 값으로 채우지 않는다. 수동 보완 또는 목업 전환은 Backend 책임이다.

## 6. 경비처리 가능성 분석

### `POST /rag/deductibility`

#### Request

```json
{
  "category": "사무용품",
  "amount": 18000,
  "vendor": "예시상점",
  "items": ["노트", "펜"]
}
```

- `category`, `amount`, `vendor`는 필수다.
- `items`는 선택이며 기본값은 빈 배열이다.
- 결과는 참고용 가능성 분석이며 최종 세무 판정을 의미하지 않는다.

#### Response

```json
{
  "deductible": true,
  "confidence": 0.85,
  "basis": "업무 관련성이 입증되고 적격 증빙이 있는 경우 경비로 인정될 수 있습니다.",
  "sources": [],
  "grounded": false,
  "status": "insufficient_evidence",
  "llmUsed": true
}
```

근거가 부족하면 `confidence`를 과도하게 높이지 않고 `basis`에 확인 필요 사항을 포함한다.

## 7. 공고문 구조화 요약

### `POST /rag/summarize-announcement`

#### Request

```json
{
  "rawContent": "공고문 원문",
  "source": "https://example.org/announcement/10"
}
```

- `rawContent`는 필수이며 공백일 수 없다.
- `source`는 선택이다.

#### Response

```json
{
  "target": "지원 대상",
  "benefit": "지원 내용",
  "period": "신청 기간",
  "documents": "필요 서류",
  "notes": "주의사항",
  "source": "https://example.org/announcement/10",
  "llmUsed": true
}
```

요약에 없는 날짜·금액·자격 조건을 추정하지 않는다. `source`는 요청값을 그대로 보존한다. 캐시 조회와 저장은 Backend 책임이다.

## 8. RAG 재색인

### `POST /rag/reindex`

#### Request

```json
{
  "documentIds": [101, 102],
  "force": false
}
```

- `documentIds`는 `rag_documents.id` 목록이다.
- 필드 누락 또는 빈 배열은 전체 문서를 대상으로 한다.
- 값이 있으면 지정한 RAG 문서만 대상으로 한다.
- `force=false`: 내용 hash와 Embedding 설정이 같은 문서는 기존 Embedding을 재사용한다.
- `force=true`: 대상 문서의 기존 캐시를 무시하고 다시 Embedding한다.
- 이미 runtime 인덱스가 준비됐더라도 명시적인 재색인 요청은 생략하지 않는다.
- 원천 `policies`, `announcements`, `tax_documents`를 수정하거나 DB schema를 변경하지 않는다.

#### Response

```json
{
  "status": "ready",
  "source": "embedding",
  "document_count": 2,
  "chunk_count": 8,
  "requested_document_ids": [101, 102]
}
```

- `status`: `ready` 또는 `already_ready`
- `source`: `cache` 또는 `embedding`
- `document_count`, `chunk_count`: 이번 요청 대상에서 준비된 수
- `requested_document_ids`: 요청이 전체 재색인이면 빈 배열

## 9. 호출 시간 제한과 재시도

| Endpoint | Backend 요청 제한 |
| --- | ---: |
| `GET /health`, `GET /rag/ready` | 3초 |
| `POST /rag/chat` | 30초 |
| `POST /rag/legal-basis` | 30초 |
| `POST /rag/deductibility` | 30초 |
| `POST /rag/summarize-announcement` | 45초 |
| `POST /ocr/receipt` | 60초 |
| `POST /rag/reindex` | 180초 |

- Backend는 `GET /health`, `GET /rag/ready`만 연결 실패 또는 `502`·`503`·`504`에서 최대 1회 재시도한다.
- 비용 중복과 중복 작업을 방지하기 위해 POST 요청은 자동 재시도하지 않는다.
- 재시도가 필요한 POST는 사용자 또는 관리자가 명시적으로 다시 요청한다.

## 10. 역할 경계

| 책임 | Backend | LLM |
| --- | --- | --- |
| 사용자 인증·권한 | Y | N |
| 사용자·사업자 Context 조립 | Y | N |
| 실제 공고 DB 조회·필터 | Y | N |
| 세액감면 Rule 판정 | Y | N |
| 답변·근거 생성 | N | Y |
| 영수증 필드 추출 | N | Y |
| 공고 요약 캐시 | Y | N |
| RAG 검색·재정렬·Embedding | N | Y |
| 원천 테이블 수정 | Y | N |
| 세액 산술 계산 | 사용자 입력과 Rule 제공 | 검증된 Python `Decimal` 계산만 수행 |

## 11. 구현 현황과 남은 연동 작업

2026-09-09 기준 LLM은 위 계약의 공개 Endpoint 8개, 요청·응답 schema, 공통 오류 응답,
카테고리 route 제한, 범위 밖 질문 Guardrail과 PostgreSQL 부분 재색인을 구현했다.

- LLM 계약 전용 테스트: `11 passed`
- LLM 전체 테스트: `222 passed`
- 실제 OpenAI·Cohere·PostgreSQL 호출 검증: 미실시
- 원본 `policies`, `announcements`, `tax_documents` 변경: 없음

Backend에는 다음 작업이 남아 있다.

- `/rag/chat`에 `userContext`, `noticeResults` 전달
- LLM 오류의 `error.code`, `error.retryable` 해석 및 로그 기록
- `/internal/*` fallback 제거
- Endpoint별 timeout 적용
- 관리자 재색인 요청을 준비 상태와 무관하게 `/rag/reindex`로 전달
- `sources[].url` 우선 사용과 `status`, `guardrail_reason`, `llmUsed` 처리
- Docker 환경에서 `LLM_API_URL=http://llm:8001` 주입

상세한 파일별 변경안과 검증 절차는 `Docs/Design/BACKEND_LLM_INTEGRATION_HANDOFF.md`를 따른다.
기존 `Docs/Design/LLM_API_SPEC.md`는 초기 설계 기록으로 보존한다.
