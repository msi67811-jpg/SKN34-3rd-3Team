# 진행 현황

- 갱신일: 2026-09-09
- 기준 브랜치/커밋: `develop` / `720e16f`

`Docs/TODO.md`가 전체 작업 흐름과 체크리스트라면, 이 문서는 현재 코드 기준의 실제 상태와 미해결 이슈를 정리한 것이다.

## 1. 병합 현황

| 브랜치 | 병합 커밋 | 비고 |
| --- | --- | --- |
| `feature/data-collection` | `7286a9d` (PR #9) | 세법·정책 수집 스크립트 |
| `feature/backend` | `c921867` (PR #10) | Backend API 서버 |
| `feature/LLM-connect-test` | `21c79f9` (PR #11) | LLM RAG(LangGraph) 구현 |
| `feature/data-collection` | `2bbbf3b` (PR #12) | `app_extras.sql`, HNSW 인덱스, API 키 로그 노출 수정 |
| `feature/intergration` | `8b3f0ef` (PR #13) | 서비스 간 배선, Backend 덤프 제거, 설계 문서 동기화 |
| `feature/data-collection` | `720e16f` (PR #14) | `09_add_rag_columns.sql` 삭제 및 `run_all` 호출 제거 |
| `feature/Frontend` | 미병합 | `develop`의 `Frontend/`는 `.gitkeep`만 있음 |

병합 자체는 정상임. 충돌 마커 없음. Backend 코드 유실 없음.

Backend·LLM·DB 배선은 끝났고 실데이터 챗봇 경로까지 확인함(P0-1, P0-3, P1-2 해결). 남은 것은 P0-2 `userContext`·미구현 엔드포인트와 P1-1 DB 직접 조회 전환임. `Docs/TODO.md`의 "구현 → 서비스 간 연동"은 이 둘이 끝나야 완료로 볼 수 있음.

## 2. 미해결 이슈

### P0-1. 서비스 간 통신 미배선 — 해결됨

- `docker-compose.yml`의 `backend`에 `ports`·`env_file`·`depends_on` 없음. `llm`에도 `env_file` 없음. 두 컨테이너에 애플리케이션 환경변수가 전혀 주입되지 않음
- `Backend/core/config.py:39` `LLM_API_URL` 기본값이 `http://127.0.0.1:8001`. 컨테이너 안에서는 자기 자신을 가리킴. 설계상 값은 `http://llm:8001` (`Docs/Design/ARCHITECTURE.md` §1)
- `Backend/core/config.py:41` `DATABASE_URL` 기본값도 `127.0.0.1`. Backend는 `.env`를 읽지 않아(`Backend/` 전체에 `load_dotenv` 없음) Postgres 연결 실패 시 SQLite로 내려감
- `LLM/src/core/config.py:10`의 `ROOT_ENV_FILE`이 컨테이너에서 `/.env`로 해석되고, `LLM/.dockerignore:5`가 `.env`를 제외함. LLM 컨테이너는 환경 파일을 하나도 읽지 못함
- 포트 번호 자체는 8001로 일치함. 어긋난 것은 호스트명뿐임

**조치 (PR #13)**

- `backend`에 `ports: "8000:8000"`, `environment`(`LLM_API_URL`·`DATABASE_URL`·`TOKEN_SECRET`·`LLM_TIMEOUT_SECONDS`), `depends_on` 추가. `env_file`은 쓰지 않아 OpenAI·Cohere 키가 Backend로 새지 않음
- `llm`에 `env_file: .env` 추가. 모델·검색·LangSmith까지 15개 이상을 읽으므로 통째로 넘기고 `environment`로 DB 관련만 덮어씀
- `db`에 `pg_isready` 헬스체크 추가. 없으면 Backend가 Postgres 기동 전에 붙으려다 실패하고 `Backend/core/database.py`가 조용히 SQLite로 내려감
- `Backend/Dockerfile`에 `UV_PROJECT_ENVIRONMENT=/opt/backend-venv` 추가. 바인드 마운트가 `/app/.venv`를 가려 컨테이너 기동 때마다 의존성을 재해석하던 문제
- `.env.example`에 누락 변수 9개 추가. `TOKEN_SECRET`에는 `:-` 기본값을 둠. 빈 문자열이 주입되면 `Backend/core/config.py:29`의 `os.getenv` 기본값이 무시돼 서명 키가 공백이 됨
- 코드의 `localhost` 기본값은 유지함. 서비스명은 compose가 주입하므로 `LLM/RUN_GUIDE.md`의 로컬 실행 절차가 그대로 동작함
- 설계 문서의 포트 표기 정정. `Docs/Design/ARCHITECTURE.md:27`과 `Docs/tech-stack.md`의 예시 URL을 8001로, `Docs/Design/LLM_API_SPEC.md`의 "코드가 아직 8000" 경고 2곳은 사실이 아니어서 삭제

**DB 선택**

검증용 DB는 compose의 `db` 컨테이너가 기본값이다. 외부 DB 전환은 `COMPOSE_DB_HOST`를 명시할 때만 일어난다. 작업 당시에는 팀 공용 DB에 붙으면 P0-3 `TRUNCATE`이 데이터를 지웠기 때문이며, P0-3 해결 후에도 안전한 기본값을 유지한다.

**검증**

`docker compose up -d --build` 후 db healthy, backend·llm running.

```json
{"status":"ok","storage":"sqlite-loaded","postgres":"connected","pgvector":"ready",
 "ragChunks":10523,"llm":"connected","llmUrl":"http://llm:8001"}
```

- 컨테이너 간 `http://llm:8001/health` → 200
- `curl localhost:8001/health` → `llm: configured`, `embedding: configured`, `data_source: postgres`
- backend가 보는 DB는 `db:5432/startup_platform`. 외부 DB 아님
- LLM 테스트 182 통과 8 실패. 실패는 전부 `LLM/src/data/RAG_data` 원본 PDF 부재 때문이며 이 작업과 무관함 (`LLM/RUN_GUIDE.md` 8절)

### P0-2. LLM 엔드포인트 미구현 — 해결됨

**조치 (PR #17)**

LLM이 없던 엔드포인트 4개를 구현했고 `Docs/Design/LLM_API_SPEC_V1.md`가 확정 계약으로 올라옴.

| Endpoint | 영향 기능 |
| --- | --- |
| `POST /rag/legal-basis` | FS-13 세액감면 근거 |
| `POST /ocr/receipt` | FS-15 영수증 OCR |
| `POST /rag/deductibility` | FS-17 경비처리 가능성 |
| `POST /rag/summarize-announcement` | FS-22 공고문 요약 |

- `RagChatResponse`에 `guardrail_reason` 추가. `Backend/services/chat_service.py:93,99`의 죽어 있던 분기가 살아남
- `Backend/core/llm_client.py`에 로깅 추가. `HTTPError`와 전송 오류를 분리하고 `error.code`·`retryable`를 기록함. 키와 요청 본문은 남기지 않음
- 빈 문자열로 422가 나던 경로 정리. `explain_expense()`가 `category`·`vendor`를 정규화하고, 본문이 빈 공고 요약은 호출 전에 차단함

### P0-2-1. Backend가 V1 계약을 준수하지 않음

엔드포인트는 생겼으나 Backend가 계약의 일부만 쓴다. 항목은 `Docs/Design/BACKEND_LLM_INTEGRATION_HANDOFF.md` 2절과 V1 11절이 정리한 것이며, 아래는 코드로 확인한 결과다.

| 항목 | 위치 | 근거 |
| --- | --- | --- |
| `/internal/*` fallback 7곳 잔존 | `llm_client.py` 3·23·34·38·63·84·139·156행 | V1 §1 "Backend는 이를 호출하거나 fallback 경로로 사용하지 않는다" |
| 엔드포인트별 timeout 미적용 | `LLM_TIMEOUT_SECONDS` 하나만 사용 | V1 §9가 3~180초로 확정 |
| 콜드 스타트에 `/rag/chat`을 아예 호출하지 않음 | `rag_answer()`가 `ensure_index()` 실패 시 조기 반환 | 인덱싱은 25초를 훨씬 넘김 |
| `userContext` 미전송 | `llm_client.rag_answer` | 세법 챗봇이 `need_more_info`로 끝나는 직접 원인 |
| `noticeResults` 미전송 | 같음 | notice route가 `integration_unavailable`로 종료 |
| `/rag/deductibility` 응답의 `sources`를 `[]`로 덮어씀 | `llm_client.explain_expense` | 근거 문서 유실 |
| `sources[].url` 대신 `source`를 URL로 사용 | `chat_service._sources_from_rag` | `RagChatSource`에 두 필드가 별도로 있음 |
| `status`·`llmUsed` 미사용 | `chat_service.send_message` | `grounded`만 보고 판단 |
| 관리자 재색인이 실제로 돌지 않음 | `api/admin.py` → `ensure_index()` 조기 반환 | V1이 "준비 상태와 무관하게 호출"을 요구 |

**합의 필요 항목** (`BACKEND_LLM_INTEGRATION_HANDOFF.md` 1절)

1. `category`를 Router 힌트로 둘지 허용 route 제약으로 쓸지. **코드와 V1은 이미 제약이며, 이에 맞춰 `LLM/LANGGRAPH_ARCHITECTURE.md`를 정정함.** 인계서 9절이 이 충돌을 "PR 전 해소" 대상으로 지목했으나 미해소 상태로 병합됐음
2. `/rag/reindex`의 `documentIds`가 원천 문서 ID인지 `rag_documents.id`인지. 확정 전까지 `[]`(전체 재색인)만 보낼 것
3. Tax Multi-hop을 포함한 `/rag/chat` 운영 타임아웃
4. 영수증 지원 형식과 4 MiB 제한을 정식 계약으로 확정할지

**검증 미실시**

인계서는 LLM 전체 테스트가 `222 passed`라고 적었으나 확인하지 않았음. `develop`에서 직접 측정한 값은 182 통과 8 실패이며 실패는 전부 `LLM/src/data/RAG_data` 원본 PDF 부재 때문임. PDF는 테스트 전용이고 `VECTOR_STORE_BACKEND=postgres`인 실제 구성에는 필요 없음.

### P0-3. Backend 쓰기가 벡터 인덱스를 삭제 — 해결됨

**있었던 문제**

- `Backend/core/postgres.py`의 `save_postgres()`가 `TRUNCATE ... RESTART IDENTITY CASCADE`로 시작하고 대상에 `policies`가 있었음
- `rag_documents.policy_id`가 `policies(id)`를 참조(`DB/01_schema.sql:170`)하므로 CASCADE가 `rag_documents`까지 비움
- 이 경로를 타는 `persist()` 호출이 Backend 전체에 25곳이었음

**원인**

`TRUNCATE`은 독립된 결함이 아니라 덤프 설계의 부품이었음. `persist()`는 인자가 없어 "무엇이 바뀌었는지" 모르고, 할 수 있는 일이 store 전체를 다시 쓰는 것뿐이었음. 그리고 모든 INSERT가 `id`를 명시해 두 번째 호출부터 기본키가 충돌하므로, 쓰기 전에 테이블을 비워야만 했음.

**조치 (2026-09-09)**

덤프 자체를 제거함. `save_postgres()`, `load_postgres()`, `init_postgres()`, `persist_postgres()`와 전용 헬퍼를 삭제하고 `Backend/core/postgres.py`를 481줄에서 65줄로 줄임. 남긴 것은 `_connect()`와 `postgres_status()` 두 개이며 `/health`만 사용함. `Backend/core/database.py`의 `init_db()`·`persist()`에서 Postgres 호출을 끊음.

**회귀가 없는 이유**

`save_postgres()`는 한 번도 성공한 적이 없었음. `TRUNCATE` 대상 첫 항목 `notifications`가 `01_schema.sql`에 없어 Postgres가 구문 전체를 거부했고 예외는 삼켜졌음. 따라서 Backend는 원래부터 SQLite로만 동작하고 있었고, 코드를 지워도 달라지는 것이 없음.

**검증**

정책 2,534건 · 청크 10,523건 · 세법 4,459건이 든 로컬 DB에서 확인함.

- `grep -rn "TRUNCATE\|save_postgres\|load_postgres\|persist_postgres" Backend/` 결과 없음
- 로그인과 챗봇 질의로 쓰기를 발생시킨 뒤에도 건수 전부 그대로
- `POST /chat/messages`(policy)가 `llmUsed: true`, `grounded: true` 유지
- `docker compose restart backend` 후에도 로그인 성공. SQLite 영속성은 그대로
- `/health`에 `ragChunks` 추가. `postgres_status()`가 세던 테이블이 존재하지 않는 `rag_chunks`여서 항상 0이었으므로 `rag_documents`로 정정함

**부수 효과**

`storage`가 항상 `sqlite-*`로 나옴. Backend가 Postgres에 쓰지 않는다는 실제 상태를 정확히 반영한 값임.

### P1-1. Backend가 실제 DB를 조회하지 않음

- `Backend/services/`와 `Backend/api/`에 SQL이 한 줄도 없음. 전부 `Backend/core/store.py`의 모듈 전역 dict를 읽음
- Postgres와 SQLite는 그 dict의 스냅샷 덤프 용도임
- 결과적으로 수집 스크립트가 넣은 정책 수천 건 대신 `store.py`의 데모 정책 5건이 응답됨
- 실측 대비: 로컬 DB에 정책 2,534건이 있어도 챗봇(`/chat/messages`)만 실데이터로 답하고 `GET /policies`·`/calendar`·`/tax/*`는 데모 5건을 응답함. 챗봇은 LLM이 DB를 직접 읽기 때문임

**진행 순서**

P0-3·P1-2와 한 묶음이며 아래 순서를 지킴. 스키마를 먼저 맞추면 `TRUNCATE`이 살아나 데이터를 지우므로 1단계가 앞에 와야 했음.

1. **덤프 제거** — 완료(P0-3 참고). `TRUNCATE` 소멸
2. **스키마 마이그레이션** — 완료(P1-2 참고). `DB/app_extras.sql`이 누락 테이블·컬럼을 채웠고 `meta_ids`만 의도적으로 제외함
3. **모듈별 SQL 전환** — 참조가 적은 순서로 진행해 단계마다 동작을 확인함

| 모듈 | store 참조 |
| --- | --- |
| `api/deps.py` | 2 |
| `auth_service.py` · `tax_service.py` · `user_service.py` | 각 8 |
| `notify_service.py` | 10 |
| `chat_service.py` | 11 |
| `calendar_service.py` | 17 |
| `expense_service.py` | 21 |
| `policy_service.py` | 22 |
| `api/admin.py` | 38 |

마지막에 `Backend/core/store.py`와 SQLite 경로를 제거하고, 데모 시드는 "없을 때만 INSERT"하는 별도 스크립트로 옮김. 다시 truncate-and-replace로 짜면 P0-3가 되돌아옴.

### P1-2. 스키마-코드 컬럼 불일치 — 해결됨

DB 담당이 `3f0d234 Feat: 백엔드 참조 컬럼 및 테이블 추가`로 `DB/app_extras.sql`을 신설해 채움. `notifications` 테이블과 `users.phone`·`status`, `calendar_events.user_id`, `reminders.dispatched`, `expenses.user_id`, `announcements.apply_method`, `announcement_summaries.llm_used`가 생김.

- `meta_ids`는 의도적으로 제외함. 인메모리 id 카운터를 저장하려던 덤프 산출물이라 `SERIAL`을 쓰면 개념이 사라짐. 덤프 경로도 P0-3에서 제거됨
- `calendar_events.user_id`가 들어옴에 따라 `USER` 타입(내 일정 직접 등록)을 정식 수용하기로 결정함. `Docs/Design/ERD.md`·`CLASS.md`·`API_SPEC.md`에 반영함. `notifications`도 같은 방식으로 설계 문서에 편입함
- `docker-compose.yml`의 initdb 마운트에 `02_app_extras.sql`로 추가함. 이미 데이터가 있는 DB에는 initdb가 다시 돌지 않으므로 `psql`로 한 번 직접 적용해야 함. 모든 구문이 `IF NOT EXISTS`라 재실행에 안전함
- 검증: `notifications` 테이블과 새 컬럼 7개 생성 확인. 스키마가 채워진 상태에서 Backend 쓰기를 발생시킨 뒤에도 정책 2,534건·청크 10,523건·세법 4,459건이 그대로임. 예전 코드였다면 이 시점에 `TRUNCATE`이 통과해 데이터가 지워졌을 것임

### P2-1. Frontend 미병합

- `origin/feature/Frontend`에 Vite + React 앱이 있으나 `develop`에 없음
- `LLM/RUN_GUIDE.md` 7절이 존재하지 않는 `Frontend/`에서 `npm run dev`를 실행하라고 안내함
- `docker-compose.yml`에도 frontend 서비스 없음

### P2-2. 기타

- `Backend/Dockerfile:14`가 `uv sync`를 그대로 씀. `Backend/uv.lock`이 커밋됐으므로 `--frozen`을 붙일 수 있음. `LLM/Dockerfile`은 이미 사용 중
- `setup.sh` 0바이트

## 3. 관련 문서

- 작업 체크리스트: `Docs/TODO.md`
- 데이터 구조와 스키마 적용 경로: `Docs/Design/ERD.md`
- Backend↔LLM 계약: `Docs/Design/LLM_API_SPEC_V1.md` (구 초안 `LLM_API_SPEC.md`는 기록용 보존)
- Backend 연동 인계 지침: `Docs/Design/BACKEND_LLM_INTEGRATION_HANDOFF.md`
- 시스템 구성: `Docs/Design/ARCHITECTURE.md`
- LLM 서비스 실행 절차: `LLM/RUN_GUIDE.md`
