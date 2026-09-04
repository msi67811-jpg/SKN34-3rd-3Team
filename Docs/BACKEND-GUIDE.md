# 백엔드 개발 가이드

> Python 환경 설정부터 백엔드 구현 범위까지 한곳에 정리한 문서입니다.  
> 상세 설계는 `Docs/Design/` 문서를 기준으로 합니다.

---

## 1. 개발 환경 설정 (Python 3.13 + venv)

### 왜 3.13인가?

venv 자체가 3.13을 요구하는 것이 아니라, **이 프로젝트 Backend가 3.13으로 고정**되어 있습니다.

| 파일 | 내용 |
|------|------|
| `Backend/.python-version` | `3.13` |
| `Backend/pyproject.toml` | `requires-python = ">=3.13"` |
| `Backend/Dockerfile` | `python:3.13-slim` |
| `Docs/tech-stack.md` | Python 3.13, 패키지 관리 `uv` |

### Python 3.13 설치 (Windows)

```powershell
winget install Python.Python.3.13
```

설치 후 **터미널을 완전히 닫았다가 다시 열기.**

```powershell
py -0p                  # 설치된 Python 목록 확인
py -3.13 --version      # Python 3.13.x 확인
```

### venv 생성 (권장 위치)

```powershell
cd "G:\내 드라이브\3.4project\SKN34-3rd-3Team\Backend"
py -3.13 -m venv .venv
```

> `.venv`는 `.gitignore`에 포함되어 Git에 올라가지 않습니다.

### venv 활성화 (PowerShell)

```powershell
.\.venv\Scripts\Activate.ps1
python --version        # Python 3.13.x 확인
```

실행 정책 에러가 나면:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 자주 하는 실수

| 증상 | 원인 | 해결 |
|------|------|------|
| `not a git repository` | Git repo 밖에서 명령 실행 | `SKN34-3rd-3Team` 또는 `Backend` 폴더로 이동 |
| `.venv` 모듈을 로드할 수 없음 | venv 미생성 또는 경로 오류 | `py -3.13 -m venv .venv` 후 `.\.venv\Scripts\Activate.ps1` |
| PowerShell에서 activate 실패 | `.\` 접두사 누락 | `.venv\...` 대신 `.\.venv\Scripts\Activate.ps1` |
| 3.12로 venv 생성됨 | 기본 python이 3.12 | `py -3.13 -m venv .venv` 사용 |

### uv (패키지 관리, 선택)

프로젝트는 `uv`로 의존성을 관리합니다 (`Docs/tech-stack.md`).

```powershell
pip install uv
uv sync
```

### venv 명령 요약

| 상황 | 명령 |
|------|------|
| venv 켜기 | `.\.venv\Scripts\Activate.ps1` |
| venv 끄기 | `deactivate` |
| Python 버전 확인 | `python --version` |
| 설치된 Python 목록 | `py -0p` |

---

## 2. 백엔드 역할 요약

```
Frontend ──REST──▶ Backend ──내부 REST──▶ LLM 서비스
                      │
                      ▼
                 Postgres + pgvector
```

| 구분 | 역할 |
|------|------|
| **Backend** | 외부 유일 진입점. REST API, 비즈니스 로직, DB CRUD, LLM 호출 |
| **LLM** | RAG, 임베딩, OCR, 공고문 요약 (외부 직접 노출 X) |
| **Frontend** | UI. Backend API만 호출 |
| **DB** | 관계형 + 벡터 데이터 |

### Backend 내부 구조

| 계층 | 폴더 | 역할 |
|------|------|------|
| Controller | `Backend/api/` | 요청 수신, 라우팅, 입력 검증 |
| Service | `Backend/services/` | 비즈니스 로직, LLM 호출, 판정 로직 |
| Model | `Backend/schemas/` (+ ORM) | Pydantic 스키마, DB 엔티티 |
| 공통 | `Backend/core/` | 설정, DB 세션, 유틸 |

### 기술 스택

- **Language:** Python 3.13
- **Framework:** FastAPI
- **Architecture:** Controller–Service–Model
- **Package Manager:** uv

---

## 3. 백엔드가 만들어야 할 핵심 기능 (4가지)

### 3-1. 회원가입 후 온보딩 저장

맞춤 질문을 받아 사용자 정보를 DB에 저장하고, LLM 추천·판정의 컨텍스트로 사용한다.

| 항목 | 내용 |
|------|------|
| 기능 ID | FS-01~04 |
| API | `POST /auth/signup`, `POST /auth/login`, `GET/PUT /users/me`, `GET/PUT /users/me/business-profile` |
| DB | `USER`, `BUSINESS_PROFILE` |

**구현 항목**

- 회원가입·로그인 API (JWT 등 팀 합의)
- 유저 프로필 스키마 정의 및 저장 (나이, 지역, 사업자 유형, 업종, 창업일 등)
- 프로필 미완성 시 후속 기능 제한
- LLM 호출 시 프로필 컨텍스트 주입

---

### 3-2. 카테고리별 LLM 챗봇

아이콘(세금, 창업 등) 클릭 시 해당 도메인 LLM 진입. 빈 채팅이 아닌 **추천 질문**부터 표시.

| 항목 | 내용 |
|------|------|
| 기능 ID | FS-05~08 |
| API | `POST /chat/messages`, `GET /chat/messages/{messageId}/sources` |
| DB | `CHAT_MESSAGE`, `ANSWER_SOURCE` |

**구현 항목**

- 카테고리별 시스템 프롬프트 (`tax`, `expense`, `saving`, `policy`)
- 추천 질문 API (예: `GET /chat/categories/{category}/suggested-questions`)
- 대화 히스토리 저장 (질문·답변 + 근거 문서)
- 유저 프로필 컨텍스트 주입
- RAG 근거 없을 때 "확인 필요" 안내 (환각 방지)

---

### 3-3. 지원금 캘린더 + 알림

신청일·마감일을 캘린더에 표시하고, 전날 알림 및 대시보드 노출.

| 항목 | 내용 |
|------|------|
| 기능 ID | FS-11, FS-12, FS-21 |
| API | `GET /tax/calendar`, `GET/POST/DELETE /tax/reminders` |
| DB | `TAX_CALENDAR_EVENT`, `REMINDER`, `POLICY`, `ANNOUNCEMENT` |

**구현 항목**

- 일정 테이블 (세금 일정 + 지원금 신청·마감)
- 캘린더·대시보드 조회 API
- 알림 스케줄러 (`REMINDER` 테이블, 전날 알림 등)

---

### 3-4. 데이터 수집

세금·정책 자료를 크롤링 또는 문서 업로드로 수집, RAG/DB 반영.

| 항목 | 내용 |
|------|------|
| 기능 ID | FS-26, FS-27 |
| API | `POST /admin/tax-documents`, `POST /admin/policies`, `POST /admin/rag-documents/reindex` |
| DB | `TAX_DOCUMENT`, `POLICY`, `ANNOUNCEMENT`, `RAG_DOCUMENT` |

**구현 항목**

- 수집 방식 결정 (크롤링 vs 관리자 업로드) — **DB 저장 + 벡터 임베딩 권장**
- 원천 데이터 검증 후 저장
- AI가 마스터 DB를 직접 수정하지 못하게 권한·프롬프트 차단

---

### 3-5. 그 외 백엔드 범위 (후순위)

| 영역 | 기능 ID | 핵심 API |
|------|---------|----------|
| 세액감면 자동판정 | FS-13 | `POST /tax/tax-reduction/check` |
| 지출·영수증 분석 | FS-14~17 | `POST /expenses/receipts` 등 |
| 지원정책 탐색 | FS-18~23 | `GET /policies`, `GET /policies/recommendations` |
| 관리자 | FS-24~28 | `/admin/*` |

---

## 4. 반드시 알아야 할 것

### 필독 설계 문서

| 문서 | 내용 |
|------|------|
| `Docs/README.md` | 프로젝트 목표, 핵심 기능 |
| `Docs/Design/API_SPEC.md` | REST 엔드포인트 |
| `Docs/Design/ERD.md` | 테이블 관계 |
| `Docs/Design/ARCHITECTURE.md` | 시스템 구조 |
| `Docs/Design/FUNCTIONAL_SPEC.md` | 기능별 흐름·제약 |
| `Docs/Design/SEQUENCE.md` | 챗봇·세액감면 등 시퀀스 |
| `Docs/tech-stack.md` | 기술 스택 |

### 핵심 원칙

1. Frontend는 Backend만 호출 (LLM은 Backend가 내부 호출)
2. DB는 Postgres + pgvector
3. RAG 근거 없으면 "확인 필요" 표기 (환각 방지)
4. 세액감면 등은 Rule 판정 + LLM 근거 설명 결합
5. 이해 못 한 AI 생성 코드는 PR에 올리지 않기

### ERD 핵심 관계

```
USER 1:1 BUSINESS_PROFILE
USER 1:N CHAT_MESSAGE 1:N ANSWER_SOURCE
USER 1:N REMINDER ← TAX_CALENDAR_EVENT
USER 1:N SAVED_POLICY → POLICY
POLICY 1:N ANNOUNCEMENT 1:1 ANNOUNCEMENT_SUMMARY
```

---

## 5. Git 협업 규칙

| 규칙 | 설명 |
|------|------|
| 브랜치 | `main` / `develop`에 직접 push 금지 |
| 작업 브랜치 | `feature/작업명` (예: `feature/beckend-jjy`) |
| PR | 작업 완료 후 `develop` 대상 Pull Request |
| fork 동기화 | GitHub **Update branch** 또는 `git fetch upstream` |

### Git 명령 흐름

```powershell
cd "G:\내 드라이브\3.4project\SKN34-3rd-3Team"

git fetch upstream
git checkout develop
git merge upstream/develop

git checkout feature/beckend-jjy
git merge develop

git push -u origin feature/beckend-jjy
```

> `git pull`만 하면 **내 fork**에서만 가져옴. 원본 변경은 `upstream` fetch 필요.  
> push 시 브랜치 이름이 일치해야 함 (`feature/login-api` ≠ `feature/beckend-jjy`).

---

## 6. 구현 우선순위

| 순서 | 기능 | 이유 |
|------|------|------|
| 1 | 인증 + 온보딩 | 다른 기능의 전제 |
| 2 | 카테고리별 챗봇 + 추천 질문 | 핵심 UX, LLM 연동 검증 |
| 3 | 데이터 수집 + RAG 연동 | 챗봇 품질 기반 |
| 4 | 캘린더 + 알림 + 대시보드 | 프로필·정책 데이터 이후 |
| 5 | 세액감면·지출·정책 탐색 | 나머지 FS-xx |

---

## 7. 체크리스트

### 환경 설정
- [ ] Python 3.13 설치 (`py -3.13 --version`)
- [ ] `Backend` 폴더에서 venv 생성
- [ ] venv 활성화 확인
- [ ] (선택) `uv sync`

### 개발 시작 전
- [ ] `Docs/Design/` 문서 읽기
- [ ] `feature/beckend-jjy` 브랜치에서 작업
- [ ] 인증 방식 팀 합의

### PR 전
- [ ] API_SPEC과 구현 일치 확인
- [ ] 이해한 코드만 커밋
- [ ] `develop` 대상 PR 생성

---

## 8. 관련 문서 링크

- [프로젝트 개요](./README.md)
- [기술 스택](./tech-stack.md)
- [API 명세](./Design/API_SPEC.md)
- [ERD](./Design/ERD.md)
- [아키텍처](./Design/ARCHITECTURE.md)
- [기능명세](./Design/FUNCTIONAL_SPEC.md)
- [TODO](./TODO.md)

---

*Python 환경 설정 + 백엔드 구현 범위 요약 문서*
