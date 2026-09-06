# Frontend

`feature/LLM` 스택(React 19 + Vite 7 + Tailwind 4)을 기준으로, Backend mock API와
LLM Lab을 한 앱에서 사용합니다.

## 화면

- 로그인 / 온보딩 / 프로필
- 홈 캘린더·리마인더
- AI 상담 (Backend mock)
- 지원정책 검색·추천·자격 확인
- 세무·감면 (유형 진단 / 세액감면 Rule)
- 지출·영수증 (OCR mock)
- LLM Lab (실제 RAG: `http://127.0.0.1:8001`)

## 실행

Backend(8000)를 먼저 띄운 뒤:

```bash
npm install
npm run dev
```

Google Drive 경로에서 `npm install`이 실패하면 로컬 디스크에 설치한 뒤
`node_modules`를 쓰거나, 아래처럼 로컬 vite로 실행합니다.

```powershell
C:\Users\playdata2\skn-frontend\node_modules\.bin\vite.cmd
```

기본 주소: `http://localhost:5173`  
Vite는 `/api`를 Backend `8000`으로 프록시합니다.

## 환경 변수

`.env.example`을 `.env`로 복사:

- `VITE_LLM_API_URL` — LLM 서비스 (기본 `http://127.0.0.1:8001`)
- `VITE_BACKEND_API_URL` — 비우면 `/api` 프록시 사용

데모 계정: `demo@demo.com` / `demo123`
