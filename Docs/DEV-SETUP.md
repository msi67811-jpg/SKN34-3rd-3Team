# 로컬 개발 환경 (Cursor)

`feature/backend-jjy`에 아래가 합쳐진 상태입니다.

- 백엔드·프론트 목업 (기존)
- `feature/db-schema` → `DB/schema.sql`
- `feature/data-collection` → `DB/scripts/collect_tax_law.py`
- `feature/LLM` → `LLM/` RAG 서비스
- LLM 테스트 UI → `LLM/test-ui/` (Frontend와 분리)

## 포트

| 서비스 | 포트 |
|--------|------|
| Backend mock | `8000` |
| LLM RAG | `8001` |
| Frontend | `5173` |
| LLM test UI | `5174` (직접 실행 시) |

Backend와 LLM이 둘 다 기본 8000이라, 로컬에서는 LLM을 **8001**로 둡니다.

## 1. Backend

```powershell
cd Backend
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install fastapi "uvicorn[standard]" python-multipart
py -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

- API 문서: http://127.0.0.1:8000/docs
- 데모: `demo@demo.com` / `demo123`

Cursor: Run and Debug → **Backend (mock API :8000)**

## 2. LLM

```powershell
cd LLM
copy .env.example .env
# .env 에서 PORT=8001, OPENAI_API_KEY 등 필요 시 수정
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install uv
uv sync
# 또는: uv run uvicorn main:app --host 127.0.0.1 --port 8001
uv run python -c "from src.serving.app import app; print('ok')"
uv run uvicorn main:app --host 127.0.0.1 --port 8001
```

- 헬스: http://127.0.0.1:8001/health
- API 키 없으면 인덱싱/답변은 제한될 수 있음 (구조·테스트는 로컬에서 확인 가능)

Cursor: **LLM RAG API (:8001)** 또는 compound **Backend + LLM**

## 3. Frontend (서비스 화면)

Google Drive에서 `npm install`이 깨지면 `C:\Users\...\skn-frontend`처럼 로컬 디스크로 복사 후 설치.

```powershell
cd Frontend
npm install
npm run dev
```

- http://127.0.0.1:5173 → Backend `/api` 프록시

## 4. LLM 테스트 UI (선택)

```powershell
cd LLM\test-ui
npm install
# .env 에 VITE_LLM_API_URL=http://127.0.0.1:8001
npm run dev -- --port 5174
```

## 5. DB 스키마 / 수집 스크립트

- 스키마: `DB/schema.sql` (Postgres + pgvector)
- 수집: `DB/scripts/collect_tax_law.py`  
  - 필요 패키지: `requests`, `psycopg2-binary`, `python-dotenv`  
  - `LAW_API_KEY`, DB 접속 정보는 `.env`  
  - Postgres가 떠 있고 `schema.sql` 적용된 뒤에 실행

DB 컨테이너는 아직 compose에 없을 수 있음. 스키마만 먼저 두고, DB 팀과 연동하면 됩니다.

## Cursor에서 바로 할 일

1. 이 폴더를 워크스페이스로 열기
2. Python 인터프리터: `Backend/.venv` (설정에 기본값 지정됨)
3. F5로 Backend / LLM 디버그
4. 터미널에서 Frontend `npm run dev`

## 합친 뒤 구조 요약

```
Backend/     # 목업 REST (메모리)
Frontend/    # 서비스 목업 UI
LLM/         # RAG 서비스
LLM/test-ui/ # LLM 단독 테스트 화면
DB/          # schema.sql + collect script
Docs/        # 가이드
```
