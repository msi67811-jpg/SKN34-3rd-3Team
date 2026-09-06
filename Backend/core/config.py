import os
from pathlib import Path

APP_NAME = "청년창업 지원 플랫폼 API"
APP_VERSION = "0.2.0"
APP_DESCRIPTION = """
청년·1인 창업자 맞춤형 행정·재정 지원 플랫폼의 REST API입니다.

- **DB**: Postgres(`DATABASE_URL`, 기본 `admin/admin1234@startup_platform`). 없으면 SQLite로 동작합니다.
- **LLM**: `LLM_API_URL`(기본 `http://127.0.0.1:8001`)이 살아 있으면 RAG/OCR/요약을 호출하고, 실패 시 목업으로 내려갑니다.
- Rule 판정(세액감면·정책 자격)은 Backend에 두고, LLM은 근거 설명만 붙입니다.

**데모 계정:** `demo@demo.com` / `demo123`  
**관리자:** `admin@demo.com` / `admin123`
"""
OPENAPI_TAGS = [
    {"name": "상태", "description": "서버·DB·LLM 연결 여부"},
    {"name": "인증", "description": "회원가입, 로그인, 로그아웃"},
    {"name": "사용자", "description": "개인정보·사업자 온보딩 프로필"},
    {"name": "상담", "description": "카테고리별 챗봇(RAG 우선, 실패 시 목업)"},
    {"name": "캘린더", "description": "세금·지원금 통합 일정"},
    {"name": "세무", "description": "세금 정보, 리마인더, 세액감면 Rule + LLM 근거"},
    {"name": "지출", "description": "영수증 OCR(LLM)과 경비 안내"},
    {"name": "지원정책", "description": "정책 검색, 추천, 자격 확인, 공고 요약, 관심 저장"},
    {"name": "관리자", "description": "관리자 로그인 및 데이터 관리"},
    {"name": "알림", "description": "앱 알림함, 메일 대기열, 브라우저 푸시"},
]
TOKEN_PREFIX = "tok_"
TOKEN_SECRET = os.getenv("TOKEN_SECRET", "skn34-local-dev-secret")
TOKEN_TTL_SECONDS = int(os.getenv("TOKEN_TTL_SECONDS", str(7 * 24 * 3600)))
DEMO_EMAIL = "demo@demo.com"
DEMO_PASSWORD = "demo123"
ADMIN_EMAIL = "admin@demo.com"
ADMIN_PASSWORD = "admin123"

BACKEND_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_ROOT / "data"
SQLITE_PATH = Path(os.getenv("SQLITE_PATH", str(DATA_DIR / "app.db")))
LLM_API_URL = os.getenv("LLM_API_URL", "http://127.0.0.1:8001").rstrip("/")
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "25"))
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:admin1234@127.0.0.1:5432/startup_platform")
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "noreply@skn34.local")
