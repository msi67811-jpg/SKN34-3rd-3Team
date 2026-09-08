# LLM Test UI

LLM/RAG 기능을 독립적으로 확인하기 위한 임시 개발 화면이다. 프로젝트 기술
스택에 맞춰 React와 TailwindCSS로 구성했다.

LLM FastAPI 서비스의 상태 확인과 RAG API 테스트를 제공한다.

- LLM API 실행 여부
- LLM 모델 설정 여부
- Embedding 모델 설정 여부
- In-memory Vector Store 사용 여부
- PDF RAG 인덱스 생성
- Mock `user_id`, 사용자 질문과 `top_k` 전달
- 사용자 프로필을 반영한 전체 정책 검색
- 관련 정책 요약, grounded 상태와 정책별 출처 표시

인덱스 생성 버튼은 먼저 로컬 캐시를 확인한다. 캐시가 유효하면 문서 Embedding을
다시 하지 않고, 캐시가 없거나 원본·설정이 변경됐을 때만 OpenAI Embedding API가
호출된다. 질문 전송 시에는 Query Embedding과 LLM API가 호출된다. API Key는
Frontend에 저장하거나 전달하지 않는다.

## 실행

LLM API를 먼저 실행한 다음 테스트 UI를 실행한다.

```bash
npm install
npm run dev
```

기본 접속 주소는 `http://localhost:5173`이다. LLM API 주소를 변경하려면
`.env.example`을 `.env`로 복사하고 `VITE_LLM_API_URL`을 설정한다.

이 화면은 개발 중에만 LLM을 직접 호출한다. 최종 서비스에서는 설계 문서에
따라 Frontend가 Backend REST API를 호출해야 한다.
