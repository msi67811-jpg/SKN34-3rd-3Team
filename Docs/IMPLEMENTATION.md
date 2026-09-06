# 구현 현황 (목업 다듬기 + LLM·DB 연동)

`feature/beckend-jjy` 기준으로, 설계 문서(`FUNCTIONAL_SPEC`, `API_SPEC`, `ARCHITECTURE`)를
프론트에서 실제로 눌러 볼 수 있게 만든 작업 기록이다.

---

## 1. 한 줄 요약

프론트는 `feature/LLM` 스택(React 19 + Vite 7 + Tailwind 4)을 쓰고,
Backend 목업 API에 **SQLite 저장**과 **LLM 내부 API 호출**을 붙였다.
LLM이 꺼져 있거나 인덱스가 없으면 예전처럼 목업 답변으로 내려간다.

| 구분 | 하는 일 | 아직 남는 일 |
|------|---------|----------------|
| Frontend | 로그인~캘린더·챗·정책·세무·지출·관리자, 알림함, 밝은 디자인 | 실제 SMTP/FCM 키는 환경변수 |
| Backend | REST + SQLite + 서명 토큰 + 알림/메일 대기열 + Postgres 상태 | 앱 데이터 전량을 Postgres로 이전 |
| LLM | RAG, Vision OCR, DATABASE_URL이면 **pgvector 적재** | 문서 대량 파이프라인 |
| DB 팀 산출물 | `schema.sql` + compose `db`(pgvector/pg16) | 수집 스크립트 자동 적재 |

---

## 2. 지금 돌아가는 흐름

```
브라우저 :5173
    → Frontend `/api` 프록시
        → Backend :8000
            → SQLite  `Backend/data/app.db`
            → LLM     :8001  (살아 있으면)
```

- 판정(세액감면, 정책 자격, 사업자 유형)은 **Backend Rule이 진실**
- LLM은 답변·근거 설명·공고 요약·영수증 필드 추출만 담당
- Frontend는 LLM을 직접 부르지 않는다. 예외는 개발용 **LLM Lab** (`/llm-lab`)

---

## 3. 목업에서 다듬은 것

- 채팅: 카테고리(tax/expense/saving/policy) + 추천 질문 + 히스토리 + 근거 목록
- 세금 메모: JSON 입력을 세목/메모 필드로 변경
- 정책: 관심 저장 목록, 공고 AI 요약 버튼
- 지출: OCR 출처 표시 (`llm` / `heuristic` / `mock`)
- 로그인·레이아웃 문구, 사이드바에 DB/LLM 연결 상태
- 빠져 있던 `Backend/api/admin.py` 복구 (`/admin/*`)
- 관리자 화면: `/admin/login`, 대시보드, 사용자 상태, 세법·정책 등록, RAG 재색인
- 영수증 Vision OCR(이미지 전송), 지출 분류 수정, 경비 RAG 설명
- 정책 추천 점수, 캘린더는 저장·추천 정책 마감만 표시, 리마인더 삭제/임박 표시
- 상담 근거 없으면 샘플 출처를 붙이지 않고 "확인 필요" 표시
- 로그인 토큰은 HMAC 서명 + 만료 (기존 `tok_user_1`도 읽음)

---

## 4. DB로 만든 기능

로컬에서는 **SQLite**가 `DB/schema.sql`과 같은 테이블을 만든다 (pgvector 컬럼만 제외).
서버를 재시작해도 회원, 온보딩, 채팅, 리마인더, 지출, 관심 정책이 남는다.

| 기능 | 테이블 |
|------|--------|
| 회원가입/로그인/온보딩 | `users`, `business_profiles` |
| 챗봇 기록·근거 | `chat_messages`, `answer_sources` |
| 캘린더·리마인더 | `calendar_events`, `reminders` |
| 세액감면 결과 | `tax_reduction_results` |
| 영수증·지출 | `receipts`, `receipt_extractions`, `expenses` |
| 정책·공고·관심 | `policies`, `announcements`, `announcement_summaries`, `saved_policies` |

첫 실행 시 데모 계정과 샘플 정책을 seed 한 뒤 파일로 저장한다.
경로: `Backend/data/app.db` (`SQLITE_PATH`로 변경 가능)

팀 Postgres가 준비되면 같은 스키마로 옮기면 된다. 수집 스크립트는 그대로 사용:

- `DB/scripts/collect_tax_law.py` — 세법
- `DB/scripts/collect_gov24.py` — 정부24 정책

---

## 5. LLM으로 만든 기능 (프론트에서 사용)

Backend `core/llm_client.py`가 `LLM_API_URL`(기본 `http://127.0.0.1:8001`)을 호출한다.

| 화면 | Backend API | LLM API | 실패 시 |
|------|-------------|---------|---------|
| AI 상담 | `POST /chat/messages` | `POST /internal/rag/answer` (+ 필요 시 index) | 카테고리 목업 답변 |
| 답변 근거 | `GET /chat/messages/{id}/sources` | RAG `sources` 저장분 | 국세청·K-Startup 샘플 |
| 세액감면 | `POST /tax/tax-reduction/check` | `POST /internal/explain/tax-reduction` | Rule 문구만 |
| 영수증 | `POST /expenses/receipts` | `POST /internal/ocr/receipt` | 파일명 규칙 추출 |
| 공고 요약 | `GET /announcements/{id}/summary` | `POST /internal/summarize/announcement` | 원문 규칙 요약 |
| RAG 재색인 | `POST /admin/rag-documents/reindex` | `POST /internal/rag/index` | `skipped` |

OpenAI 키가 없어도 LLM 프로세스만 켜져 있으면 OCR/요약은 **heuristic** 응답을 준다.
키가 있고 RAG 인덱스가 준비되면 상담은 근거 기반 답변을 쓴다.

개발용 직접 RAG 화면은 프론트 **LLM Lab** (`Frontend/src/pages/LlmLab.jsx`).

---

## 6. 로컬에서 확인하는 방법

터미널 3개 (또는 Cursor Run and Debug).

**Backend :8000**

```powershell
cd Backend
.\.venv\Scripts\Activate.ps1
py -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

**LLM :8001** (RAG·OCR·요약을 쓰려면)

```powershell
cd LLM
uv run uvicorn main:app --host 127.0.0.1 --port 8001
```

**Frontend :5173** (Google Drive `npm`이 깨지면 로컬 복사본)

```powershell
cd C:\Users\playdata2\skn-frontend
npm run dev
```

1. http://127.0.0.1:5173 로그인 `demo@demo.com` / `demo123`
2. 온보딩 저장 → 홈 캘린더에서 일정 클릭(리마인더)
3. AI 상담에서 추천 질문 전송 (LLM 켜면 RAG, 꺼면 목업)
4. 지원정책 → 자격 확인, 관심 저장, 공고 AI 요약
5. 세무 → 유형 진단, 감면 판정
6. 지출 → 영수증 업로드
7. 왼쪽 메뉴 하단에서 DB·LLM 연결 상태 확인
8. http://127.0.0.1:8000/health 에 `storage`, `llm` 필드 확인

---

## 7. 파일 위치

```
Backend/core/database.py     SQLite 저장/복원
Backend/core/llm_client.py   LLM HTTP 클라이언트
Backend/api/admin.py         관리자 API
LLM/src/serving/ai_routes.py OCR·공고요약·감면설명
Frontend/src/pages/          서비스 화면
Frontend/src/pages/LlmLab.jsx LLM 단독 테스트
Docs/IMPLEMENTATION.md       이 문서
```

---


