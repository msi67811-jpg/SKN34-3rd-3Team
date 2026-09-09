# 프론트엔드 수정 기록

내가 "이렇게 바꿔줘" 라고 요청한 내용과, 그에 따라 실제로 바뀐 파일을 정리한 로그.
최신 항목이 위로 온다.

## 새 요청을 추가하는 방법

아래 템플릿을 복사해 **맨 위 `---` 바로 아래**에 붙여넣는다.

```
## YYYY-MM-DD · <한 줄 제목>
**요청**: <내가 부탁한 내용 그대로 / 요약>
**변경**:
- `<파일경로>` — <무엇을 어떻게>
**메모**: <선택 - 트레이드오프, 되돌리는 법 등>
```

---

## 2026-09-07 · 백엔드 연동 준비 레이어 추가 (api.js)

**요청**: 팀원들이 올린 파일들(Backend/LLM/DB)을 브랜치로 받아왔는데 내가 만든 프론트엔드랑 연결할 수 있나? → "프론트만 연결 준비(안전)" 선택.

**변경**:
- `src/api.js` (신규) — `apiGet(path)` fetch 래퍼 + `useApi(path, fallback, map)` 훅. 백엔드 없으면 실패 → `fallback`(목데이터) 사용, `/api/*` 나오면 자동 전환. BASE = `import.meta.env.VITE_API_BASE_URL || '/api'`
- `src/App.jsx` — `import { useApi } from './api.js'` 추가
- `src/App.jsx` `DeadlinePanel` — `DEADLINES` 상수 대신 `useApi('/announcements?deadline=soon&limit=4', DEADLINES, map)` 사용 (연동 예시 1곳)

**메모**: 지금은 Backend가 스텁(`print("Hello from backend!")`)이라 실제로는 목데이터가 보임. DB(Postgres)에는 데이터 적재 완료(policies 2,907 / announcements 2,045 등). Backend가 `API_SPEC.md` 대로 구현되면 `DeadlinePanel` 은 코드 수정 없이 붙고, 나머지 데이터 지점(METRICS, CAL_EVENTS, 마이페이지 카드, 챗봇)은 `api.js` 상단 주석의 목록대로 `useApi` 로 교체하면 됨.

## 2026-09-08 · 홈 캘린더 — 중요 일정만 표시

**요청**: 메인페이지 일정관리 캘린더가 전체 다 보이지 않고 몇 가지 중요 일정만.

**변경**: `src/App.jsx`
- `pickImportant(map, maxPolicy=5)` 추가 — 세금 신고일은 전부(날짜당 최대 2건), 지원사업 마감은 **가까운 순 5건**만 남김
- 홈 `Calendar` — API 응답을 `pickImportant` 로 걸러서 표시 (`MpCalendar`·`세금 일정` 메뉴는 전체 유지)
- `cal__sub` 문구 → "이번 달 주요 일정 N건 · 전체 일정은 마이페이지에서"

## 2026-09-08 · Backend·DB·LLM 실연동 (목데이터 → 실제 API)

**요청**: 백엔드·DB·프론트·LLM 폴더 내용을 유기적으로 연결하고 홈페이지에서 구동되게.

**변경** (Frontend 쪽):
- `src/api.js` 전면 개편 — `apiGet`/`apiPost` + 엔드포인트 헬퍼 `api.{stats,announcements,policies,recommendations,calendar,taxCheck,taxDocuments,chat}` + `useApi`(실패 시 목데이터 폴백, 빈 배열도 폴백 처리)
- `Hero` — `GET /api/stats` 로 **모집 중 공고 수(860)·정책 2,907·세법 4,459** 실데이터 표시 + `● 실시간 DB 연동 중 / ○ 데모 데이터` 배지
- `DeadlinePanel` — `GET /api/announcements` 로 실제 마감 임박 공고, D-day 자동 계산
- `Calendar`(홈) / `MpCalendar`(마이페이지) — `GET /api/calendar?year&month` 로 세금 신고일 + 정책 마감일 통합. 오늘 날짜 기준으로 시작, 월 이동 시 재조회. 직접 추가/삭제는 로컬 오버레이로 유지
- `GovExplorer` — `GET /api/announcements?limit=60` 실데이터 + 지역/유형 필터, `● DB 실시간` 표시
- `TaxTool` — `POST /api/tax/tax-reduction/check` 서버 Rule Engine 병행 호출 → **DB 근거 조문 링크** 표시
- `AiConsult` — 질문 시 `POST /api/chat/messages` 로 근거 문서 검색 → 그 근거를 컨텍스트로 넣어 생성(RAG). 답변 아래 **근거 문서 목록·원문 링크**(`.msg-src`). Backend만 있어도 사용 가능하도록 입력창 활성화 조건 완화
- `styles.css` — `.msg-src` 추가

**함께 만든 것** (Frontend 외):
- `Backend/` — FastAPI 앱(`main.py`), `core/{config,db}`, `services/{policy,calendar,tax,stats,chat}_service`, `api/routes.py`, `schemas/models.py`. 지역 법정동 코드 → 시·도명 정규화 포함
- `LLM/src/serving/app.py` — 근거 기반 생성(LangChain) 또는 추출 요약
- `run_all.bat`, 루트 `README.md`(구성도·실행법·API 표·제약)

**메모**: `tax_documents.content` 평균 53자(수집 스크립트가 조문 제목만 저장) → 검색은 정확하나 답변 근거 본문이 부족. `DB/scripts/collect_tax_law.py` 보완 필요.

## 2026-09-08 · 로드맵 단계별 지원사업 + 완료 리포트 / AI 대화창 확대

**요청**: (1) 창업 로드맵에서 단계별 지원사업을 알려주고, 로드맵 완료 시 그 내용 기준으로 맞춤 지원사업을 정리해 보여주기. (2) AI 세무 Assistant 대화창을 더 크게, 글씨도 잘 보이게.

**변경**:
- `src/App.jsx` — `ROADMAP_PROGRAMS`(단계 A~Z ↔ `GOV_LISTINGS` id 매핑), `progById`, `ddayLabel`, `scoreProgram`(프로필 기반 매칭 점수+이유) 추가
- `src/App.jsx` `RoadmapGuide`
  - 각 단계 패널 하단에 **"이 단계에서 활용할 수 있는 지원사업"** 목록(기관·금액·지역·D-day)
  - 진행률 아래 **완료 리포트** — 100% 미만은 잠금 안내(남은 개수), 100% 달성 시 `추천 지원사업 Top 5(매칭 점수·이유 태그)` + `세무 체크포인트` + `다음 액션` 표시
  - **AI로 실행 계획 정리받기** 버튼 — 완료 단계·매칭 사업을 프롬프트에 넣어 `sample`로 신청 우선순위/준비서류/주의사항 생성(스트리밍·중지 지원)
- `src/App.jsx` `AiConsult` — `large` prop 추가 → `.ai--lg` 클래스 / `TaxAssistantPage` 에 `large` 적용, `tool` maxWidth 900 → 980
- `src/styles.css` — `.ai--lg`(높이 `min(74vh,760px)`, 말풍선 15px, 입력·칩·헤더 확대), 기본 `.msg` 13 → **14px**, `.rg__progs/.rg__prog/.rg__report/.rg__match/.rg__why/.rg__next` 등 추가

**메모**: 매칭 점수는 지역 일치·창업 단계 대상·마감 임박·자금 유형 가중치의 룰 기반(데모). 실서비스는 `/api/policies/recommendations` 로 교체.

## 2026-09-08 · 마이페이지 캘린더 추가 + 사이드바 메뉴 기능 구현

**요청**: (1) 대시보드 오른쪽에 일정 확인·관리 캘린더 추가. (2) 마이페이지 사이드바 메뉴별 실제 기능 구현.

**변경**: `src/App.jsx` + `src/styles.css`
- `MpCalendar` (신규) — 월 이동 · 날짜 클릭 · **일정 추가/삭제**(세금·지원사업 분류). 대시보드 우측 + `세금 일정` 메뉴에서 사용
- `MyPage` 대시보드를 `.mp-dash`(카드 4개 + 캘린더 2열) 로 재구성
- 사이드바 메뉴별 화면 연결:
  - `사업자유형 진단` → `BizTypeDiagnosis` (신규, 매출·B2B·업종 → 간이/일반 + 개인/법인 추천)
  - `세액감면 판정` → `TaxTool` (기존 재사용)
  - `세금 일정` → `MpCalendar full`
  - `탐색` → `GovExplorer` (기존, `saved` 상태를 MyPage로 리프트)
  - `저장한 정책` → `SavedPolicies` (신규, `탐색`의 ★ 저장 목록 공유)
  - `지출관리` → `ExpenseTracker` (신규, 지출 입력·분류·합산)
  - `프로필 · 설정` → `ProfileSettings` (신규, 프로필 폼 + 알림 토글)
- `GovExplorer` — `{ saved, onToggleSave }` prop 선택적으로 받도록(없으면 기존 내부 상태)
- `styles.css` — `.mp-dash` `.cal__add` `.cal__ev-del` `.exp-*` `.pf-*` 추가

**메모**: 데이터는 목/로컬 상태(추가·삭제·저장 모두 새로고침 시 초기화). 실서비스는 `/api/calendar`·`/api/policies/saved`·`/api/expenses` 연동으로 교체.

## 2026-09-08 · 창업 A-Z 로드맵 아이콘·글씨 확대

**요청**: 창업 순서(A-Z) 부분의 아이콘·글씨 등을 더 크게.

**변경**: `src/styles.css` `.rz*`
- `.rz__ico` 52×52 → **76×76**, radius 16 → 22 / `.rz__ico svg` 22 → **34**
- `.rz__t`(단계명) 13 → **17px** / `.rz__phase` 10.5 → 12.5px / `.rz__d`(설명) 11 → 13px, max-width 15ch → 17ch
- `.rz__sep`(화살표) 16 → **26px**, 위치 보정(margin-top 18 → 28) / `.rz__step` gap 9 → 13, `.rz` margin-top 44 → 60

## 2026-09-08 · 로그인 모달 소셜 버튼 위치 변경

**요청**: 네이버·카카오 버튼을 로그인 버튼 아래로.

**변경**: `src/App.jsx` `LoginModal` — 소셜 버튼 블록(+"또는" 구분선)을 이메일 폼 위 → **`</form>` 아래**(로그인/가입하기 버튼 밑)로 이동.

## 2026-09-08 · 로그인 모달에 소셜 로그인 + 회원가입 추가

**요청**: (1) 카카오·네이버 연동 로그인. (2) 로그인 모달에 회원가입 버튼 등 추가.

**변경**:
- `src/App.jsx` `LoginModal` 재구성
  - `mode` 상태(`login` / `signup`) — 모달 안에서 로그인 ↔ 회원가입 전환
  - 소셜 버튼: **카카오로 계속하기**(#FEE500, 말풍선 아이콘) / **네이버로 계속하기**(#03C75A, N 마크) + "또는" 구분선
  - 회원가입 모드: 이름 · 이메일 · 비밀번호 · 비밀번호 확인(불일치 시 인라인 에러) · `가입하기`
  - 하단: "아직 계정이 없으신가요? 회원가입" ↔ "이미 계정이 있으신가요? 로그인" 링크, "비밀번호를 잊으셨나요?"(데모 안내)
  - 모달에 `maxHeight: 90vh; overflowY: auto`
- `src/App.jsx` 상단 — `linkBtn` `fieldLabel` `socialBtn` 스타일 상수 추가

**메모**: 데모라 소셜/이메일/가입 **모두 예시로 바로 로그인**됨(`onSuccess`로 정석/카카오 사용자/네이버 사용자 등). 실서비스는 카카오·네이버 OAuth(`/oauth/authorize` 리다이렉트) + 백엔드 `/auth/*` 연동으로 교체.

## 2026-09-08 · 창업 A-Z 순차 애니메이션 강화 + 홈 섹션 화면 전체

**요청**: (1) 창업 순서(A-Z) 부분이 차례대로 나오는 애니메이션. (2) 메인페이지에서 각 섹션이 화면 전체에 나오게.

**변경**:
- `src/App.jsx` `Roadmap` — 스텝 stagger 간격 `i*80` → `i*160` ms 로 확대(7단계가 또렷하게 하나씩)
- `src/styles.css` `.rz__step` — 진입 모션 강화: `translateY(26px) scale(0.9)` → 0, `0.6s`. 아이콘도 `scale(0.5) rotate(-8deg)` → 0 로 팝인. reduced-motion 예외 추가
- `src/App.jsx` `Home` — `<main>` → `<main className="home-flow">`
- `src/styles.css` — `.home-flow > section { min-height: 100dvh; flex column center; scroll-snap-align:start }`, `html { scroll-padding-top: 66px }`, 데스크톱(≥768px) `scroll-snap-type: y proximity`, 모바일(<768px) 예외

**메모**: 09-06 에 넣었다가 병합으로 유실됐던 "한 화면에 한 섹션씩"을 다시 적용(이번엔 커밋 필요). "큰 모니터 zoom"(아래 항목)은 이번에 재적용 안 함 — 필요 시 별도 요청.

## 2026-09-06 · 큰 모니터에서도 노트북과 비슷한 비율로  *(유실됨 — 미재적용)*

**요청**: 큰 모니터로 보면 여백이 많고 노트북으로 보면 여백이 적다. 어느 모니터에서 보든 같은 비율로.

**변경**:
- `src/styles.css` — `.wrap` `max-width: 1160px` → `clamp(1120px, 82vw, 1500px)`
- `src/styles.css` — `:root { zoom }` 반응형 추가: `min-width` 1600→1.1 / 1920→1.22 / 2300→1.4 / 2800→1.65. 노트북(~1440px 이하)은 1.0

**메모**: `zoom` 이라 경계값에서 단계적으로 커짐. 연속 스케일 필요하면 JS로 전환. 배율·경계값 조정 가능.

## 2026-09-06 · 홈 메인, 한 화면에 한 섹션씩  *(09-08 에 재적용)*

**요청**: 홈 메인 화면이 2개 섹션이 동시에 보이지 않고 하나하나씩 떴으면 좋겠다.

**변경**:
- `src/App.jsx` — `Home` 의 `<main>` → `<main className="home-flow">`
- `src/styles.css` — `.home-flow > section { min-height: 100dvh; flex column center; scroll-snap-align:start }`, `html { scroll-padding-top: 66px }`, 데스크톱(≥768px) `scroll-snap-type: y proximity`, 모바일(<768px) 예외

**메모**: 스냅이 부담스러우면 `scroll-snap-type` 줄만 제거.

## 2026-09-06 · 리액트 실행 방법을 README에 정리

**요청**: 리액트 실행 방법을 정리해서 프론트엔드에 넣어줘.

**변경**:
- `README.md` — 맨 위 `## 빠른 시작`(3줄) 추가 + `## 실행` 섹션(사전요구사항, clone/pull 흐름, `npm ci`, API 프록시, 문제 해결) + `## 화면 구성` 표 갱신

## 2026-09-06 · Frontend를 창업ON 프로토타입으로 교체

**요청**: 로컬 5173(팀 스캐폴드)은 제거해도 되고, 5180(창업ON 프로토타입)을 메인 프론트엔드로 바꿔줘.

**변경**:
- `src/` — 기존 react-router 스캐폴드 전체 삭제(`router.jsx`, `pages/**`, `components/**`, `context/`, `data/`, `services/`, `styles/`)
- `src/App.jsx`, `src/styles.css` 신규 — 창업ON 프로토타입(홈 / 창업 로드맵 / AI 세무 Assistant / 지원사업 공고문 AI 분석 / AI 상담 / 마이페이지). 라우팅은 `App.jsx` 내부 `view` 상태 전환
- `src/main.jsx` — `createRoot` 마운트로 단순화
- `package.json` — `react-router-dom` 제거, `react`/`react-dom`만. `lint` 스크립트 제거
- `vite.config.js` — `port: 5173`, `open: true`, `/api` → `http://localhost:8000` 프록시
- `index.html` — 폰트 로드 + `favicon.svg` + 기본 리셋

**메모**: 프로토타입 원본은 Claude 아티팩트(`window.claude.use('sample')`)에서 이식. 로컬엔 `window.claude` 없어 AI 기능은 예시 데이터/비활성 폴백 → 실서비스는 `sampleFn` 호출부를 백엔드 `/api/chat`(RAG)로 교체. 삭제된 스캐폴드는 git 이력에 있어 복구 가능.
