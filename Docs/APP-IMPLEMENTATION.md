# 백엔드·프론트 구현 설명

> DB와 LLM 없이, 설계 문서(`API_SPEC`, `ERD`, `FUNCTIONAL_SPEC`)를 기준으로 만든 **목업 구현**입니다.  
> 서버를 재시작하면 메모리 데이터는 초기 샘플로 돌아갑니다.

---

## 1. 한 줄 요약

| 구분 | 한 일 | 아직 안 한 일 |
|------|--------|----------------|
| Backend | FastAPI REST API, 인증, 온보딩, 캘린더, Rule 판정, 정책 검색, 챗봇/OCR **목업** | Postgres, 실제 JWT 비밀키, LLM/RAG 호출 |
| Frontend | React + Tailwind 화면, 로그인부터 홈/챗/정책/세무/지출까지 API 연동 | 디자인 시스템 고도화, 관리자 화면 |



---

## 2. 실행 방법

터미널 두 개를 엽니다.

```powershell
cd "G:\내 드라이브\3.4project\SKN34-3rd-3Team\Backend"
py -3.13 -m pip install fastapi "uvicorn[standard]" python-multipart
py -3.13 -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

```powershell
cd "G:\내 드라이브\3.4project\SKN34-3rd-3Team\Frontend"
npm install
npm run dev
```

Google Drive 폴더에서 `npm install`이 `EBADF` / `EPERM`로 실패하면, 소스만 로컬 디스크(예: `C:\Users\playdata2\skn-frontend`)로 복사한 뒤 그곳에서 `npm install` 하세요. `node_modules`는 Git에 올리지 않습니다.

- 프론트: http://localhost:5173
- API 문서: http://127.0.0.1:8000/docs
- 프론트는 `/api/*` 요청을 Vite가 백엔드 `8000`으로 프록시합니다.

---

## 3. 백엔드 코드 설명

구조는 `Docs/tech-stack.md`의 Controller–Service–Model을 따릅니다.

```
Backend/
  main.py            # FastAPI 앱, CORS, 라우터 등록, /health
  api/               # Controller. URL만 받고 Service 호출
  services/          # 비즈니스 로직 (Rule, 목업 답변)
  schemas/           # Pydantic 요청/응답 모델
  core/store.py      # 메모리 DB (dict). 나중에 ORM으로 교체
  core/security.py   # 비밀번호 해시, 단순 토큰 tok_user_1
```

### 저장 방식

`core/store.py`가 Postgres 대신입니다. 서버 시작 시 `seed()`가 샘플 유저·정책·세금 일정을 넣습니다.

나중에 DB를 붙일 때 **Service는 유지하고 store만 SQL로 바꾸면** 됩니다.

### 인증

- `POST /auth/signup`, `/auth/login`
- 토큰 형식: `tok_user_{id}` (연습용, JWT 아님)
- 보호 API는 `Authorization: Bearer ...` 필요 (`api/deps.py`)

### LLM 없이 한 부분

| API | 동작 |
|-----|------|
| `POST /chat/messages` | 카테고리별 고정 안내문 + 유저 프로필 이름/지역을 앞에 붙임 |
| `GET .../suggested-questions` | 하드코딩된 추천 질문 |
| `GET .../sources` | 국세청·K-Startup 샘플 근거 2개 |
| `POST /expenses/receipts` | 파일명은 받지만 OCR 없이 샘플 상호/금액 생성 |
| `POST /admin/rag-documents/reindex` | `skipped` 상태만 반환 |

### DB 없이 한 Rule 로직 (진짜 로직)

| 기능 | 파일 | 규칙 |
|------|------|------|
| 세액감면 판정 | `services/tax_service.py` | 만 39세 이하, 창업 5년 이내, 배제 업종 아님 |
| 정책 추천/자격 | `services/policy_service.py` | `eligibility_rule` 문자열 비교 |
| 사업자 유형 진단 | `services/tax_service.py` | 예상 매출 8천만원 기준 |
| 경비 가능성 | `services/expense_service.py` | 카테고리별 고정 확률 |

이 부분은 LLM이 생겨도 **Rule은 Backend에 남기고**, LLM은 근거 설명만 추가하면 됩니다.

### API와 화면 매핑

| 화면 | 주요 API |
|------|----------|
| 로그인 | `POST /auth/login`, `POST /auth/signup` |
| 온보딩 | `PUT /users/me`, `PUT /users/me/business-profile` |
| 홈 캘린더 | `GET /calendar`, `GET/POST /tax/reminders`, `GET /policies/recommendations` |
| AI 상담 | `GET /chat/categories/{category}/suggested-questions`, `POST /chat/messages` |
| 지원정책 | `GET /policies`, `GET /policies/{id}`, `GET .../eligibility` |
| 세무 | `POST /tax/business-type/diagnosis`, `POST /tax/tax-reduction/check` |
| 지출 | `POST /expenses/receipts`, `GET /expenses` |

전체 엔드포인트는 `Docs/Design/API_SPEC.md`와 맞췄고, 추천 질문·채팅 히스토리(`GET /chat/messages`)만 목업 편의를 위해 추가했습니다.

---

## 4. 프론트 코드 설명

```
Frontend/src/
  api.js                 # fetch 래퍼. 토큰을 Authorization에 붙임
  App.jsx                # 라우팅. 토큰 없으면 /login
  components/Layout.jsx  # 왼쪽 메뉴
  pages/
    Login.jsx            # 로그인/회원가입
    Onboarding.jsx       # 나이·지역·사업자 정보
    Home.jsx             # 월 캘린더 + 알림 + 추천 정책
    Chat.jsx             # 카테고리 탭, 추천 질문, 대화
    Policies.jsx         # 검색 목록
    PolicyDetail.jsx     # 상세, 자격, 관심 저장
    Tax.jsx              # 유형 진단 + 세액감면
    Expenses.jsx         # 영수증 업로드 + 지출 목록
    Profile.jsx          # 저장된 프로필 조회
```

- `vite.config.js`의 proxy 때문에 프론트 코드는 `/api/auth/login`처럼 호출합니다.
- 스타일은 Tailwind. 색은 深绿(`pine`) + 종이색(`paper`)입니다.
- 상태는 대부분 페이지 안 `useState`. 토큰만 `localStorage`에 둡니다.

---

## 5. 나중에 교체할 지점

```
chat_service.send_message
    지금: MOCK_ANSWERS[category]
    나중: http://llm:8000 호출 후 answer/sources 저장

expense_service.create_receipt
    지금: 파일명으로 샘플 OCR
    나중: LLM Vision/OCR 결과 저장

core/store.py
    지금: dict
    나중: SQLAlchemy + Postgres 테이블 (ERD와 컬럼명이 같음)
```

---

## 6. 구현하지 않은 것

- 실제 메일/푸시 알림 발송 (리마인더는 DB 역할의 메모리에만 저장)
- 관리자 전용 화면 (API는 `/admin/*` 로 있음, 계정 `admin@demo.com` / `admin123`)
- 크롤링·원본 문서 수집
- Docker로 프론트까지 묶기 (백엔드 포트 8000만 compose에 추가)

---

*목업 구현 기준. 설계 문서가 바뀌면 API부터 맞추면 됩니다.*
