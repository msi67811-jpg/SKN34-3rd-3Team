# LLM/RAG Service

사용자 프로필과 질문을 바탕으로 전체 정책 문서에서 관련 정책을 탐색·요약하는
내부 LLM 서비스다. 실제 자격 판정이 필요한 경우에는 Backend의 Rule 기반 결과를
Source of Truth로 사용하며, 이 서비스는 판정값을 변경하지 않는다.

현재 단계에서는 다음 최소 실행 기반만 제공한다.

- FastAPI 애플리케이션과 `GET /health`
- 환경변수 기반 LLM·Embedding 모델 팩터리
- PostgreSQL 사용자·정책·공고문 조회와 테스트용 Mock 데이터 계층
- DB 원천 문서 Chunking·pgvector 저장 및 In-memory 테스트 대역
- 실제 자격증명 없이도 실행 가능한 지연 초기화

원본 PDF는 읽기 전용으로 취급하고 가공 결과를 원본에 덮어쓰지 않는다. 현재는
Retriever, PromptTemplate, 근거 기반 답변과 LangSmith tracing을 제공한다. 실제
PostgreSQL 연결과 pgvector 구현은 완료됐으며 최초 Vector 적재는 명시적인 인덱싱
요청으로만 실행한다. Backend 내부 REST 연결은 다음 단계다.

## 구조

```text
LLM/
├── data/                  # 원본과 분리한 중간·가공·캐시 데이터
├── models/                # 로컬 모델 자산을 위한 예약 영역
├── main.py
├── src/
│   ├── core/
│   │   ├── config.py       # 환경변수 설정
│   │   └── database.py     # PostgreSQL 연결 생성
│   ├── data/
│   │   ├── contracts.py       # Backend/DB 및 RAG 데이터 타입 계약
│   │   ├── document_catalog.py # 임시 PDF-policy_id mapping
│   │   ├── mock_repository.py  # 자동 테스트용 Mock 접근 함수
│   │   └── postgres_repository.py # 실제 사용자·정책·공고문 조회
│   ├── evaluation/
│   │   ├── evaluator.py       # 평가 schema와 전체 실행 흐름
│   │   ├── metrics.py         # 검색·Guardrail 지표 계산
│   │   └── run_evaluation.py  # HTTP adapter와 평가 CLI
│   ├── features/
│   │   ├── document_processing.py # PDF 로드와 Chunking
│   │   ├── indexing.py        # Embedding·인덱스·로컬 캐시
│   │   └── index_documents.py # 명시적으로 실행하는 임시 색인 CLI
│   ├── models/
│   │   └── factory.py      # 교체 가능한 모델 생성 진입점
│   ├── rag/
│   │   ├── retriever.py    # 검색 및 관련성 필터
│   │   ├── prompts.py      # 근거·판정 보존 PromptTemplate
│   │   ├── chain.py        # 구조화 생성·출력 분량·문자열 변환
│   │   ├── context_builder.py # Prompt 길이·정책별 Chunk 제한
│   │   ├── discovery.py    # 전체 정책 탐색·그룹화·요약
│   │   ├── guardrails.py   # 입력·근거 Guardrail
│   │   ├── service.py      # RAG 사용 사례 조합
│   │   └── contracts.py    # RAG 도메인·구조화 출력 schema
│   ├── vectorstores/
│   │   ├── base.py         # In-memory/pgvector 공통 검색 계약
│   │   ├── hybrid.py       # BM25와 RRF Hybrid Search
│   │   ├── in_memory.py    # 프로세스 내부 테스트 Vector Store
│   │   └── postgres.py     # 실제 PostgreSQL pgvector Search
│   └── serving/
│       ├── app.py          # FastAPI 애플리케이션
│       ├── rag_routes.py   # API endpoint와 프로세스 runtime
│       └── schemas.py      # API 요청·응답 schema
└── tests/
```

## 환경 설정

`.env.example`을 `.env`로 복사한 뒤 필요한 값을 입력한다. `.env`는 Git과
Docker build context에서 제외된다.

```dotenv
LLM_MODEL=YOUR_LLM_MODEL
EMBEDDING_MODEL=YOUR_EMBEDDING_MODEL
OPENAI_API_KEY=YOUR_OPENAI_API_KEY
DATABASE_URL=postgresql://YOUR_USER:YOUR_PASSWORD@localhost:5432/YOUR_DATABASE
DATABASE_CONNECT_TIMEOUT=5
VECTOR_STORE_BACKEND=postgres
CORS_ORIGINS=http://localhost:5173
CHUNK_SIZE=1000
CHUNK_OVERLAP=150
DEFAULT_TOP_K=5
MIN_RELEVANCE_SCORE=0.2
RETRIEVAL_MODE=hybrid
HYBRID_DENSE_CANDIDATE_K=20
HYBRID_BM25_CANDIDATE_K=20
HYBRID_RRF_K=60
MAX_QUESTION_LENGTH=1000
MAX_CONTEXT_CHARACTERS=12000
MAX_CHUNKS_PER_POLICY=2
RAG_ALLOWED_KEYWORDS=정책,지원,지원금,보조금,장려금,창업,청년,사업,공고,신청,자격,대상,혜택,세금,세무,세법,세액,감면,절세,경비,사업자,업종,지역,주거,취업,근속,직무,문화,이전비,받을,신고,납부,기간,마감,방법,서류,금액,얼마,언제,조건
RAG_BLOCKED_KEYWORDS=파이썬,python,append,자바,javascript,코딩,프로그래밍,날씨,주식,비트코인,요리,레시피,게임
OUT_OF_SCOPE_ANSWER=그 질문에는 답변할 수 없습니다
INVALID_GENERATION_ANSWER=답변 근거를 정확히 확인하지 못했습니다. 다시 시도해 주세요.
VECTOR_INDEX_CACHE_PATH=data/processed/rag_vector_index.json

LANGSMITH_TRACING=false
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_PROJECT=skn34-3rd-project
LANGSMITH_API_KEY=YOUR_LANGSMITH_API_KEY
LANGSMITH_HIDE_INPUTS=false
LANGSMITH_HIDE_OUTPUTS=false
```

현재 모델 adapter는 OpenAI를 기본으로 사용한다. 모델 값이 비어 있거나 `YOUR_`
placeholder이면 미설정 상태로 처리하므로 Health API는 자격증명 없이도
정상 실행된다.

## 실제 DB와 테스트용 Mock 데이터

기본 실행은 PostgreSQL의 `users`, `business_profiles`, `policies`,
`announcements`를 사용한다. `LLM/.env`의 `DATABASE_URL`이 실제 값이면 이를
사용하고, placeholder이면 저장소 루트 `.env`의 PostgreSQL 항목을 사용한다.

```env
VECTOR_STORE_BACKEND=postgres
```

Mock repository와 PDF In-memory 인덱스는 외부 DB·모델 호출이 없어야 하는 자동
테스트와 독립 개발에만 사용한다.

```env
VECTOR_STORE_BACKEND=in_memory
```

## PostgreSQL + pgvector Search

운영 경로는 DB의 정책·공고문을 읽고 Chunking한 뒤 `rag_documents`의 pgvector
컬럼에 파생 데이터를 저장한다. 원본 `policies`와 `announcements`는 수정하지
않는다. 현재 RAG가 필요한 Chunk ID, 본문, 정책 ID, 출처, 페이지, content hash와
Embedding 모델 컬럼이 DB에 없으면 스키마를 변경하지 않고 오류를 반환한다.

서버에서 인덱스를 준비한다.

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/internal/rag/index
```

최초 실행에는 실제 DB 원천 문서 전체의 Embedding 비용이 발생한다. 이후에는
`content_hash`와 `embedding_model`이 동일한 Chunk를 재사용하고 신규·변경 Chunk만
다시 임베딩한다.

테스트용 In-memory 구현도 동일한 `VectorSearch` 계약을 유지한다.

```python
from langchain_core.embeddings import DeterministicFakeEmbedding

from src.features import build_document_vector_index

vector_search = build_document_vector_index(
    embedding=DeterministicFakeEmbedding(size=32),
)
results = vector_search.search("지원 대상", policy_id=101, top_k=2)
```

프로세스 안의 In-memory 인덱스는 종료 시 사라지지만 직렬화된 로컬 캐시는
`data/processed/rag_vector_index.json`과 `rag_vector_index.manifest.json`에 남는다.
다음 서버 실행에서는 PDF, Embedding 모델, Chunk 설정과 catalog가 동일하면 이
캐시를 읽어 문서 재임베딩을 생략한다.

다음 조건 중 하나가 변경되면 인덱스를 다시 생성한다.

- 원본 PDF SHA-256
- Embedding 모델명
- `CHUNK_SIZE` 또는 `CHUNK_OVERLAP`
- PDF-policy_id catalog
- 캐시 schema version

강제로 다시 임베딩하려면 CLI에서는 `--force`, API에서는
`{"force": true}`를 사용한다. 생성된 캐시에는 Chunk 본문과 vector가 포함되므로
Git에 올리지 않으며 `LLM/.gitignore`에서 제외한다.

PostgreSQL과 In-memory 구현은 모두 `src/vectorstores/base.py`의
`add_chunks()`, `search()`, `get_chunks()` 계약을 유지한다.

### Hybrid Retrieval

기본 검색은 동일한 Chunk 집합의 Dense와 BM25 순위를 RRF로 결합한다.
`HYBRID_DENSE_CANDIDATE_K`와 `HYBRID_BM25_CANDIDATE_K`는 각 검색기가 RRF에
제공할 후보 수이고, `HYBRID_RRF_K`는 순위 점수 격차를 조절한다.
최종 후보 수는 API의 `top_k` 또는 `DEFAULT_TOP_K`를 사용한다.

기존 Dense 기준을 독립적으로 실행할 때는 다음을 설정한 후 서버를
재시작한다.

```dotenv
RETRIEVAL_MODE=dense
```

### LangGraph와 Tax Multi-hop

질문 Router는 `policy`, `notice`, `tax`를 Structured Output으로 분류한다. Policy는
기존 Dense + BM25 + RRF 결과에 Cohere Rerank를 적용하고, Notice는 Vector 검색 없이
Backend 조회 경계만 사용한다. 현재 Backend에 Notice 구현이 없어 실제 호출은 연결
전이며 임의 endpoint나 DB 조회를 만들지 않는다.

Tax는 각 Hop에서 동일한 Hybrid Retrieval과 Cohere Rerank를 실행한 뒤 법령 근거와
사용자 정보의 부족 여부를 분리해 평가한다. 명시적 법령 참조를 다음 Query보다 먼저
사용하며, `TAX_MAX_HOPS` 도달·반복 Query·새 근거 없음이면 근거 부족 상태로 종료한다.
세금 계산이 필요해도 현재 Backend Calculator가 없으면 LLM이 직접 계산하지 않고
`calculator_unavailable` 상태를 남긴다. Backend 함수는 Tool Calling이 아니라
LangGraph node에 주입하는 일반 호출 경계다.

세 branch는 모두 `answer` node에서 합류한다. 성공한 요청은 route에 필요한 실제
검색/조회 결과만 Structured Output 모델에 전달하며, 최종 출처는 모델이 생성하지
않고 실제 결과의 번호를 검증해 선택한다. 무결과, 사용자 정보 부족, 근거 부족,
Backend 미연결과 내부 오류는 서로 다른 `status`로 반환한다.

```text
success | need_more_info | insufficient_evidence | no_result |
integration_unavailable | error
```

`POST /internal/rag/answer`가 실제 LangGraph 실행 진입점이다. 기존 요청 필드
`question`, `policy_id`, `top_k`, `decision`을 유지하고 개인화 Context 조회를 위한
선택적 `user_id`를 받는다. 응답에는 기존 `answer`, `grounded`, `sources`, `decision`,
`guardrail_reason`과 함께 `route`, `status`가 포함된다. 정책 추천과 retrieval 평가
entry point는 기존 흐름을 유지한다.

```dotenv
COHERE_API_KEY=YOUR_COHERE_API_KEY
COHERE_RERANK_MODEL=rerank-v4.0-fast
COHERE_RERANK_CANDIDATE_K=20
TAX_MAX_HOPS=3
```

## RAG API

FastAPI 답변 전에 검색 인덱스를 명시적으로 준비해야 한다.

PostgreSQL 모드에서는 실제 정책·공고문을 조회해 신규·변경 Chunk만 임베딩한다.
In-memory 테스트 모드에서는 유효한 로컬 캐시가 있으면 PDF 재임베딩을 생략한다.

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/internal/rag/index
```

응답의 `source`가 `cache`이면 문서 임베딩을 재사용했고, `embedding`이면 새로
임베딩했다는 의미다.

준비 상태를 확인한다.

```powershell
Invoke-RestMethod -Uri http://localhost:8000/internal/rag/ready
```

### 사용자 기반 정책 탐색

기본 서비스 흐름은 사용자가 정책 번호를 고르는 방식이 아니다. `user_id`로 실제
PostgreSQL 사용자·사업자 정보를 가져온 뒤 질문과 프로필을 결합해 전체 정책
문서를 검색한다. 실제 사용자와 사업자 프로필이 없으면 404를 반환한다.

```powershell
$body = @{
    user_id = 1
    question = "내 조건과 관련된 지원정책을 알려줘"
    top_k = 5
} | ConvertTo-Json

Invoke-RestMethod `
    -Method Post `
    -Uri http://localhost:8000/internal/rag/recommendations `
    -ContentType "application/json" `
    -Body $body
```

이 흐름에서 `policy_id`는 사용자 입력이 아니라 검색된 정책을 구분하는 결과값이다.
프로필은 관련성 검색에만 사용하며 지원 자격을 확정하지 않는다.

### 관련 없는 질문 Guardrail

원문 질문에 `RAG_BLOCKED_KEYWORDS`가 포함되거나, `그리고`, `하지만`, 문장부호
등으로 나눈 각 절 중 하나라도 `RAG_ALLOWED_KEYWORDS`를 포함하지 않으면 Vector
Search 전에 요청을 차단한다. 따라서 정책 질문 뒤에 프로그래밍·날씨 같은 다른
요청을 섞어도 전체 요청이 차단된다. 이 경우 Query Embedding, LLM과 LangSmith
호출은 발생하지 않으며 `OUT_OF_SCOPE_ANSWER`의 문구를 반환한다.

```json
{
  "user_id": 1,
  "answer": "그 질문에는 답변할 수 없습니다",
  "grounded": false,
  "policies": []
}
```

현재 허용·차단 키워드와 절 분리 규칙은 실제 운영 데이터가 없는 상태의 임시
규칙이다. 엄격한 차단 때문에 IT 창업 지원정책처럼 차단 키워드와 정책 문맥이 함께
있는 정상 질문도 거절할 수 있다. 데이터와 평가셋이 확보되면 오탐·미탐을 확인해
목록을 조정하거나 별도 분류기로 교체한다. 응답 문구는 `.env`의
`OUT_OF_SCOPE_ANSWER`만 변경하면 코드 수정 없이 바꿀 수 있다.

### 구조화 출력과 생성 결과 검증

LLM은 자유 문자열 대신 Pydantic schema로 답변·정책 요약·출처 번호를 반환한다.
실제 policy_id, 문서 제목, 페이지와 score는 LLM 출력을 신뢰하지 않고 Retriever
결과에서만 가져온다.

Prompt에 전달하기 전 다음 Context 제한을 적용한다.

- 중복 chunk_id 제거
- 정책별 최대 `MAX_CHUNKS_PER_POLICY`개 유지
- 전체 `MAX_CONTEXT_CHARACTERS` 제한
- Chunk를 중간에서 자르지 않음
- Prompt에 포함된 Chunk만 API sources로 반환

Prompt는 `<user_profile>`, `<backend_decision>`, `<retrieved_documents>`,
`<user_question>` 경계를 사용한다. LLM이 존재하지 않는 출처 번호나 검색되지 않은
policy_id를 생성하거나 빈 답변을 반환하면 `grounded=false`,
`guardrail_reason=generation_validation_failed`와 `INVALID_GENERATION_ANSWER` 문구를
반환한다.

Prompt 버전은 `prompts.py`의 `POLICY_DISCOVERY_PROMPT_VERSION`과
`DECISION_EXPLANATION_PROMPT_VERSION`에서 관리하며 LangSmith metadata에 기록한다.

현재 간결성 규칙을 반영한 Prompt 버전은 `policy-discovery-v3`와
`decision-explanation-v2`다. 특정 정책 답변은 결론부터 3~5문장으로 작성하고,
정책 탐색 답변은 관련성 높은 정책 최대 3개만 보여준다. 정책별 관련 이유와 추가
확인사항은 각각 최대 2개, 전체 제한사항은 1개로 제한한다. LLM이 이 개수를
초과해도 `chain.py`가 최종 응답에서 다시 제한한다.

정책 추천의 사용자 출력은 `chain.py` formatter가 `정책명 → 자격 → 지원 내용 →
신청기간 → 출처` 순서로 조합한다. 제한 조건, 관련 이유, 확인사항과 전체 안내는
Structured Output 내부에는 유지하지만 기본 `answer` 문자열에서는 중복과 길이를
줄이기 위해 표시하지 않는다. 기존 `summary`도 내부 호환성을 위해 유지하되 최종
문자열 형식에는 사용하지 않는다. `overview`는 LLM 문장 대신 compact된 실제 정책
수를 기준으로 `회원님과 관련이 높은 정책 N개를 찾았습니다.`로 만든다. 문서에서
찾지 못한 항목은 임의 생성하지 않고 `확인 필요`로 표시한다.

### 특정 정책 상세 질의와 Backend 판정 설명

검색 결과에서 정책 하나를 선택한 뒤 상세 질문하거나 Backend 판정 결과를 설명할
때에는 `/internal/rag/answer`를 사용한다. 이 요청에서는 질문 Embedding과 검색
근거 기반 LLM 호출이 발생한다.

```powershell
$body = @{
    question = "청년창업 지원사업의 지원 대상은 누구야?"
    policy_id = 101
    top_k = 3
} | ConvertTo-Json

Invoke-RestMethod `
    -Method Post `
    -Uri http://localhost:8000/internal/rag/answer `
    -ContentType "application/json" `
    -Body $body
```

Backend가 확정한 판정 결과를 선택적으로 함께 보낼 수도 있다. `eligible`과
`reasons`는 LLM이 재계산하지 않고 응답에도 동일하게 반환한다.

```json
{
  "question": "나는 이 정책 대상이야?",
  "policy_id": 101,
  "top_k": 3,
  "decision": {
    "eligible": true,
    "reasons": ["연령 조건 충족", "지역 조건 충족"]
  }
}
```

## LangSmith

`.env`에서 `LANGSMITH_TRACING=true`와 실제 `LANGSMITH_API_KEY`를 설정하면
`skn34-3rd-project` 프로젝트에 `policy_discovery`, `build_personalized_query`,
`retrieve_documents`, `build_prompt_context`, `generate_policy_summary` trace가
기록된다. 특정 정책 상세 답변에서는 `rag_answer`, `generate_answer`도 기록된다.

개발 중 trace 확인을 위해 `LANGSMITH_HIDE_INPUTS=false`,
`LANGSMITH_HIDE_OUTPUTS=false`를 사용한다. 이 설정에서는 사용자 질문, 프로필,
검색 문서와 모델 답변이 LangSmith에 기록될 수 있으므로 실제 개인정보나 비공개
문서를 사용하기 전에는 두 값을 `true`로 변경한다.

LangSmith가 비활성화돼 있으면 tracing Client를 생성하거나 네트워크 요청을 보내지
않는다. API Key는 코드 또는 로그에 출력하지 않는다.

## 검색·Guardrail 평가

`src/evaluation/`은 정책 검색 순위를 P@k, R@k, MRR, AP@k로 평가하고 Guardrail을
이진 분류 지표로 평가한다. 검색 지표의 평가 단위는 Chunk가 아니라 사용자에게
반환된 `policy_id` 순위다.

- P@k: 상위 k개 중 관련 정책 비율
- R@k: 전체 관련 정책 중 상위 k개에서 찾은 비율
- MRR: 첫 관련 정책 순위의 역수 평균
- AP@k: 관련 정책을 만날 때의 Precision 합을 `min(관련 정책 수, k)`로 나눈 값
- Guardrail: Accuracy, Precision, Recall, F1, TP, FP, TN, FN

AP@k는 검색된 정답만 평균내지 않고 놓친 관련 정책도 감점하는 표준 분모를 사용한다.
Guardrail에서 `out_of_scope`와 `insufficient_evidence`는 모두 차단으로 계산한다.

현재 [샘플 평가셋](evaluation/sample_cases.json)은 평가 코드 검증용이며 실제 서비스
성능을 의미하지 않는다. 실제 데이터가 확보되면 질문, 사용자 ID, 기대 정책 ID와
차단 기대값을 교체한다.

```json
{
  "case_id": "startup-support-001",
  "user_id": 1,
  "question": "초기 창업자를 위한 지원정책을 알려줘",
  "relevant_policy_ids": [101],
  "should_block": false
}
```

FastAPI 서버를 실행한 상태에서 평가한다.

```powershell
cd LLM
uv run python -m src.evaluation.run_evaluation --prepare-index --k 5
```

`--prepare-index`는 유효한 로컬 Vector 캐시를 메모리에 로드한다. 평가 결과는
`evaluation/results/latest_report.json`에 저장되며 Git에서 제외된다. 관련 질문은
Query Embedding과 LLM 호출이 발생하므로 실제 평가셋을 반복 실행할 때 API 비용에
주의한다. 무관 질문이 사전 Guardrail에서 차단되면 외부 모델을 호출하지 않는다.

## 로컬 실행

```bash
cd LLM
uv sync
uv run uvicorn main:app --reload
```

- Health Check: `http://localhost:8000/health`
- OpenAPI 문서: `http://localhost:8000/docs`

또는 다음 명령으로 `HOST`, `PORT`, `RELOAD` 설정을 사용해 실행할 수 있다.

```bash
uv run python main.py
```

## 테스트

```bash
cd LLM
uv run pytest
```

테스트는 Fake Embedding과 Fake Chat Model을 사용하며 OpenAI, LangSmith 또는
실제 DB에 접속하지 않는다.

## React 테스트 UI

`Frontend/`에는 React와 TailwindCSS로 만든 LLM 전용 임시 상태 확인 화면이 있다.
최종 서비스 아키텍처에서는 Frontend가 Backend만 호출하지만, 이 화면은 개발 중
LLM 서비스의 `/health`를 직접 확인하기 위한 도구다.

```bash
cd Frontend
npm install
npm run dev
```

기본 LLM API 주소는 `http://localhost:8000`이며 `Frontend/.env`의
`VITE_LLM_API_URL`로 변경할 수 있다.

## Docker

저장소 루트 Compose에는 `llm` 서비스가 이미 등록되어 있지만 포트와 환경변수
전달은 아직 정의되어 있지 않다. 다른 담당 영역인 루트 Compose를 수정하지
않았으므로, Docker를 통한 호스트 접근과 실제 연동 전 해당 설정을 팀에서
추가해야 한다.
