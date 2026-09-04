# LLM/RAG Service

사용자 프로필과 질문을 바탕으로 전체 정책 문서에서 관련 정책을 탐색·요약하는
내부 LLM 서비스다. 실제 자격 판정이 필요한 경우에는 Backend의 Rule 기반 결과를
Source of Truth로 사용하며, 이 서비스는 판정값을 변경하지 않는다.

현재 단계에서는 다음 최소 실행 기반만 제공한다.

- FastAPI 애플리케이션과 `GET /health`
- 환경변수 기반 LLM·Embedding 모델 팩터리
- Backend/DB 응답을 흉내 내는 JSON 호환 Mock 데이터 계층
- PDF 텍스트 추출·Chunking·In-memory Vector Search
- 실제 자격증명 없이도 실행 가능한 지연 초기화

원본 PDF는 읽기 전용으로 취급하고 가공 결과를 원본에 덮어쓰지 않는다. 현재는
Retriever, PromptTemplate, 근거 기반 답변과 LangSmith tracing까지 제공하며 실제
PostgreSQL+pgvector 적재와 Backend 연결은 다음 단계에서 구현한다.

## 구조

```text
LLM/
├── main.py
├── src/
│   ├── core/
│   │   └── config.py       # 환경변수 설정
│   ├── data/
│   │   ├── contracts.py       # Backend/DB 및 RAG 데이터 타입 계약
│   │   ├── document_catalog.py # 임시 PDF-policy_id mapping
│   │   └── mock_repository.py  # 교체 가능한 Mock 접근 함수
│   ├── features/
│   │   ├── pdf_loader.py      # 읽기 전용 PDF 페이지 추출
│   │   ├── chunking.py        # metadata 보존 Chunking
│   │   ├── indexing.py        # Embedding 및 인덱스 생성 시작점
│   │   ├── index_cache.py     # 로컬 index·manifest 검증 및 재사용
│   │   └── index_documents.py # 명시적으로 실행하는 임시 색인 CLI
│   ├── models/
│   │   └── factory.py      # 교체 가능한 모델 생성 진입점
│   ├── rag/
│   │   ├── retriever.py    # 검색 및 관련성 필터
│   │   ├── prompts.py      # 근거·판정 보존 PromptTemplate
│   │   ├── chain.py        # LangChain Runnable
│   │   ├── query_builder.py # 사용자 프로필 기반 검색 Query
│   │   ├── discovery.py    # 전체 정책 탐색·그룹화·요약
│   │   ├── guardrails.py   # 입력·근거 Guardrail
│   │   ├── service.py      # RAG 사용 사례 조합
│   │   └── runtime.py      # FastAPI 프로세스의 인덱스 상태
│   ├── vectorstores/
│   │   ├── base.py         # In-memory/pgvector 공통 검색 계약
│   │   └── in_memory.py    # 프로세스 내부 테스트 Vector Store
│   └── serving/
│       ├── app.py          # FastAPI 애플리케이션
│       └── schemas.py      # API 응답 스키마
└── tests/
```

## 환경 설정

`.env.example`을 `.env`로 복사한 뒤 필요한 값을 입력한다. `.env`는 Git과
Docker build context에서 제외된다.

```dotenv
LLM_MODEL=YOUR_LLM_MODEL
EMBEDDING_MODEL=YOUR_EMBEDDING_MODEL
OPENAI_API_KEY=YOUR_OPENAI_API_KEY
CORS_ORIGINS=http://localhost:5173
CHUNK_SIZE=1000
CHUNK_OVERLAP=150
DEFAULT_TOP_K=5
MIN_RELEVANCE_SCORE=0.2
MAX_QUESTION_LENGTH=1000
RAG_ALLOWED_KEYWORDS=정책,지원,지원금,보조금,장려금,창업,청년,사업,공고,신청,자격,대상,혜택,세금,세무,세법,세액,감면,절세,경비,사업자,업종,지역,주거,취업,근속,직무,문화,이전비,받을,신고,납부,기간,마감,방법,서류,금액,얼마,언제,조건
RAG_BLOCKED_KEYWORDS=파이썬,python,append,자바,javascript,코딩,프로그래밍,날씨,주식,비트코인,요리,레시피,게임
OUT_OF_SCOPE_ANSWER=그 질문에는 답변할 수 없습니다
VECTOR_INDEX_CACHE_PATH=data/processed/rag_vector_index.json

LANGSMITH_TRACING=false
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_PROJECT=skn34-3rd-project
LANGSMITH_API_KEY=YOUR_LANGSMITH_API_KEY
LANGSMITH_HIDE_INPUTS=true
LANGSMITH_HIDE_OUTPUTS=true
```

현재 모델 adapter는 OpenAI를 기본으로 사용한다. 모델 값이 비어 있거나 `YOUR_`
placeholder이면 미설정 상태로 처리하므로 Health API는 자격증명 없이도
정상 실행된다.

## Mock 데이터 사용

현재 단계에서는 실제 DB나 Backend API에 연결하지 않는다. LLM 로직에서는 Mock
상수에 직접 접근하지 않고 다음 함수만 사용한다.

```python
from src.data import get_eligibility_result, get_policy, get_user_profile

user = get_user_profile(user_id=1)
policy = get_policy(policy_id=101)
decision = get_eligibility_result(user_id=1, policy_id=101)
```

각 함수는 JSON으로 직렬화할 수 있는 Dictionary의 복사본을 반환한다. 향후 실제
Backend REST API를 사용할 때에는 이 접근 함수의 내부 구현만 교체하고 RAG 및
Prompt 코드는 동일한 반환 계약을 사용한다.

Mock 판정 결과는 Backend가 이미 계산해 전달한 값으로 간주한다. Mock 계층은
`eligible`이나 `reasons`를 계산하거나 변경하지 않는다.

## In-memory Vector Search

실제 PostgreSQL과 pgvector가 준비되기 전에는 LangChain의
`InMemoryVectorStore`를 사용한다. 테스트용 RAG Chunk를 임베딩하고 검색하는
진입점은 `src/features/indexing.py`다. Mock Chunk에는
`build_mock_vector_index()`, 실제 PDF에는 `build_document_vector_index()`를
사용한다.

실제 OpenAI Embedding을 사용하는 예시는 다음과 같다.

```python
from src.features import build_document_vector_index

# get_embedding_model()을 내부에서 호출한 뒤 add_chunks()에서 임베딩한다.
vector_search = build_document_vector_index()
results = vector_search.search(
    "지원 대상과 신청 기간을 알려줘",
    policy_id=101,
    top_k=2,
)
```

외부 API 호출 없이 구조만 테스트하려면 LangChain Fake Embedding을 주입한다.

```python
from langchain_core.embeddings import DeterministicFakeEmbedding

from src.features import build_document_vector_index

vector_search = build_document_vector_index(
    embedding=DeterministicFakeEmbedding(size=32),
)
results = vector_search.search("지원 대상", policy_id=101, top_k=2)
```

실제 OpenAI Embedding으로 PDF 5개를 인덱싱하고 선택적으로 검색하려면 다음처럼
명시적으로 실행한다. 이 명령을 실행할 때에만 Embedding API 요청과 비용이
발생한다.

```bash
cd LLM
uv run python -m src.features.index_documents \
  --query "지원 대상과 신청 기간을 알려줘" \
  --policy-id 101 \
  --top-k 3
```

현재 임시 문서 mapping은 기존 Mock 정책 제목과 맞추기 위해 `초기창업=101`,
`주거이전비=102`, `직무경험=103`, `근속장려금=104`, `문화활동비=105`로
연결한다. 실제 Backend/DB 계약이 정해지면 `document_catalog.py`만 교체한다.

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

향후 pgvector 구현체도 `src/vectorstores/base.py`의 `add_chunks()`와 `search()`
계약을 유지하면 상위 RAG 코드를 바꾸지 않고 교체할 수 있다.

## RAG API

CLI가 만든 인덱스는 CLI 종료 시 사라지므로 FastAPI 답변 API와 공유되지 않는다.
API 테스트에서는 서버 프로세스 안에 인덱스를 명시적으로 생성해야 한다.

서버 실행 후 인덱스를 준비한다. 유효한 로컬 캐시가 있으면 파일을 읽기만 하며,
캐시가 없거나 무효화됐을 때만 PDF Chunk의 OpenAI Embedding이 발생한다.

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

기본 서비스 흐름은 사용자가 정책 번호를 고르는 방식이 아니다. `user_id`로 Mock
사용자·사업자 정보를 가져온 뒤 질문과 프로필을 결합해 전체 정책 문서를 검색한다.

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

기본 설정은 `LANGSMITH_HIDE_INPUTS=true`, `LANGSMITH_HIDE_OUTPUTS=true`다. 사용자
질문과 문서 원문이 trace에 노출되지 않도록 한 보수적인 기본값이며, 개발 중
내용 확인이 반드시 필요할 때에만 팀의 개인정보 정책을 확인한 뒤 변경한다.

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
