APP_NAME = "청년창업 지원 플랫폼 API"
APP_VERSION = "0.1.0"
APP_DESCRIPTION = """
청년·1인 창업자 맞춤형 행정·재정 지원 플랫폼의 REST API입니다.

현재는 **DB·LLM 없이** 메모리와 목업으로 동작합니다.
- 저장소: 서버 메모리 (재시작 시 샘플 데이터로 초기화)
- 챗봇/OCR/RAG: 샘플 응답

**데모 계정:** `demo@demo.com` / `demo123`  
**관리자:** `admin@demo.com` / `admin123`

로그인 후 오른쪽 위 **Authorize**에 `tok_user_1` 형태 토큰을 넣으면 보호 API를 호출할 수 있습니다.
"""
OPENAPI_TAGS = [
    {"name": "상태", "description": "서버 동작 여부 확인"},
    {"name": "인증", "description": "회원가입, 로그인, 로그아웃"},
    {"name": "사용자", "description": "개인정보·사업자 온보딩 프로필"},
    {"name": "상담", "description": "카테고리별 챗봇(목업)과 추천 질문"},
    {"name": "캘린더", "description": "세금·지원금 통합 일정"},
    {"name": "세무", "description": "세금 정보, 리마인더, 세액감면 Rule 판정"},
    {"name": "지출", "description": "영수증 등록(가짜 OCR)과 경비 안내"},
    {"name": "지원정책", "description": "정책 검색, 추천, 자격 확인, 관심 저장"},
    {"name": "관리자", "description": "관리자 로그인 및 데이터 관리"},
]
TOKEN_PREFIX = "tok_"
DEMO_EMAIL = "demo@demo.com"
DEMO_PASSWORD = "demo123"
ADMIN_EMAIL = "admin@demo.com"
ADMIN_PASSWORD = "admin123"
