# Frontend · 청년 창업 & 세금 내비게이터 (창업ON)

토스증권 랜딩 톤(넉넉한 여백 · 화이트 배경 · 블루 포인트)을 참고한 React 프론트엔드입니다.
홈 · 창업 로드맵 · AI 세무 Assistant · 지원사업 공고문 AI 분석 · AI 상담 · 마이페이지 화면을 포함합니다.

## 빠른 시작

> 사전 조건: Node.js 18 이상 (`node -v` 로 확인)

```bash
cd Frontend        # 저장소 루트에서
npm install        # 최초 1회 / package.json·lock 이 바뀐 뒤. (권장: npm ci)
npm run dev        # → http://localhost:5173  (브라우저 자동 실행)
```

- 중단: 터미널에서 `Ctrl + C`
- 포트 5173 이 사용 중이면 5174… 로 자동 이동
- `git pull` 로 최신 코드를 받은 뒤에는 `npm install` 을 다시 실행
- 자세한 설명·문제 해결은 아래 [실행](#실행) 참고

## 스택

- React 18 + Vite 5
- 라우팅: `App.jsx` 내부 상태 기반 뷰 전환 (`home` / `page` / `mypage`) — 라우터 라이브러리 미사용
- 스타일: 단일 `src/styles.css`, CSS 변수 기반 라이트·다크 토큰 + 반응형
- AI 기능: `window.claude.use('sample')` 런타임(있을 때만). 없으면 예시 데이터/비활성으로 폴백
  → 실서비스에서는 각 컴포넌트의 `sampleFn` 호출부를 백엔드 `/api/chat` (RAG)로 교체

## 실행

### 사전 요구사항

- Node.js **18 이상** (Vite 5 기준, 20 LTS 권장) — `node -v` 로 확인
- npm (Node 설치 시 포함)

### 처음 받는 사람 (clone 후 최초 1회)

```bash
git clone https://github.com/SKNETWORKS-FAMILY-AICAMP/SKN34-3rd-3Team.git
cd SKN34-3rd-3Team/Frontend

npm ci               # package-lock.json 그대로 설치 (권장). 없으면 npm install
cp .env.example .env # 백엔드 API 주소 설정 (기본값 /api 프록시면 그대로 둬도 됨)

npm run dev          # http://localhost:5173 (포트 사용 중이면 5174…로 자동)
```

### 이미 clone 했고, 다른 사람이 push한 걸 받아서 실행할 때

```bash
cd SKN34-3rd-3Team
git pull                     # 최신 코드 받기
cd Frontend
npm ci                       # package.json / lock 이 바뀌었을 수 있으니 pull 후 매번
npm run dev
```

### 기타 명령

```bash
npm run build     # 프로덕션 빌드 → dist/
npm run preview   # 빌드 결과 로컬 미리보기
```

### git이 나르지 않는 것 → 각자 PC에서 생성

| 저장소에 올라감 (pull 시 받음) | `.gitignore` (각자 생성) |
|---|---|
| `src/`, `index.html`, `package.json`, **`package-lock.json`**, `.env.example`, `vite.config.js` | **`node_modules/`**, `.env`, `dist/` |

- `node_modules/` 는 push되지 않으므로 **clone·pull 후 `npm ci`(또는 `npm install`) 필수**.
- `npm ci` 는 `package-lock.json` 과 100% 동일하게 설치해 "내 PC에선 됐는데" 문제를 줄인다. `package.json` 을 직접 고쳐 의존성을 추가/변경할 때만 `npm install`.
- `.env` 는 개인 설정이라 공유하지 않는다. 새 환경변수가 생기면 `.env.example` 에 키를 추가해 커밋한다.

### API 프록시

개발 서버는 `/api` 요청을 `http://localhost:8000`(FastAPI)으로 프록시합니다. (`vite.config.js`)
현재 화면은 목/예시 데이터로 동작하며, 백엔드가 안 떠 있어도 화면 확인에는 지장이 없습니다.

### 자주 나는 문제

| 증상 | 조치 |
|---|---|
| `vite: command not found` / 모듈 없음 | `npm ci` 를 안 했거나 실패 → 다시 실행 |
| `EADDRINUSE` (포트 충돌) | 5173 사용 중 → Vite가 자동으로 다음 포트 사용, 또는 `npm run dev -- --port 5180` |
| Node 버전 에러 | Node 18+ 로 업그레이드 (nvm 등) |
| 설치가 계속 깨짐 | `rm -rf node_modules package-lock.json && npm install` (lock 재생성은 팀 공유 후) |

## 폴더 구조

```
Frontend/
├─ index.html          진입 HTML (폰트 로드 + 기본 리셋)
├─ vite.config.js       Vite 설정 (port 5173, /api 프록시)
├─ public/favicon.svg
└─ src/
   ├─ main.jsx          createRoot 마운트
   ├─ App.jsx           전체 컴포넌트·상태·뷰 전환 (아래 "화면 구성" 참고)
   └─ styles.css        전체 스타일 (라이트·다크 토큰, 반응형, 애니메이션)
```

## 화면 구성

`App.jsx` 가 `view` 상태로 화면을 전환한다 (URL 라우팅 없음).

| view | 화면 | 주요 컴포넌트 |
|---|---|---|
| `home` | 홈 랜딩 — Hero · 마감 임박 공고 · 창업 일정 캘린더 · AI 대화 데모 · 창업 A–Z 로드맵 · 지표+시작 CTA | `Hero` `Calendar` `ChatDemo` `Roadmap` `Closing` |
| `page` (`roadmap`) | 창업 로드맵 가이드 — 7단계 체크리스트 + 단계별 "AI에게 물어보기" | `RoadmapGuide` |
| `page` (`tax`) | AI 세무 Assistant — 세액감면 자동 판정 예시 대화 + 실시간 질의 + 판정 계산기·신고 일정 | `TaxAssistantPage` (`AiConsult` + `TaxTool`) |
| `page` (`gov`) | 지원사업 공고문 AI 분석 — 공고문 → 지원대상/내용/기간/서류/유의사항 구조화 | `AnnouncementAnalyzer` |
| `page` (`ai`) | AI 상담 — 세무·창업 자유 질의 | `AiConsult` |
| `mypage` | 로그인 후 대시보드 — 세액감면 요약 · 다가오는 일정 · 추천 정책 · 최근 AI 상담 · AI 상담 탭 | `MyPage` `AiConsult` |

상단 햄버거(≡) → 슬라이드 메뉴에서 각 `page` 뷰와 로그인/로그아웃 진입.

## 다음 작업 (TODO)

- [ ] 목/예시 데이터 → 백엔드 API 연동 (`GET /api/policies`, `POST /api/chat` 등, `Docs/Design/API_SPEC.md`)
- [ ] AI 호출부(`sampleFn`)를 RAG 백엔드 호출로 교체, 답변 근거(출처) 표기
- [ ] 세액감면 판정 규칙(`TaxTool`) 백엔드 Rule Engine 으로 이전
- [ ] 회원가입/로그인 실제 인증(토큰) + 개인정보·사업자정보 입력 폼
- [ ] 필요 시 `react-router-dom` 도입해 URL 라우팅으로 전환
- [ ] 지출 분석(영수증 OCR) 화면 신규
- [ ] 접근성(포커스 트랩, aria) 점검 · 세무 정보 면책 문구 상시 노출
