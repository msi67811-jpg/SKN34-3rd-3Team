# 기술 스택
Docker Compose 기반의 컨테이너형 서비스로 구성한다.
각 서비스의 역할 및 통신 구조는 `Docs/Design/ARCHITECTURE.md`를 참고한다.

## Backend
* **Language:** Python 3.13
* **Framework:** FastAPI
* **Architecture:** Controller–Service–Model
* **Directory:** `Backend/api`, `Backend/services`, `Backend/schemas`
* **Communication:** REST API

## LLM
* **Language:** Python 3.13
* **Framework:** LangChain
* **RAG:** Vector Embedding + LLM 기반 검색·생성 파이프라인
* **OCR / Vision:** 영수증 이미지 기반 정보 추출
* **Rule Engine:** 창업자 세액감면 대상 여부 판정
* **LLM Model:** TBD
* **Dependencies:** `LLM/pyproject.toml` 기준으로 관리

## Database
* **RDBMS:** PostgreSQL
* **Vector Store:** pgvector (PostgreSQL extension)
* 관계형 데이터와 벡터 데이터 통합 관리

## Frontend
* **Framework:** React
* **Styling:** TailwindCSS

## Infrastructure
* **Container:** Docker
* **Orchestration:** Docker Compose
* **Services:** Backend, LLM, Database, Frontend
* **Network:** Docker 내부 네트워크 기반 서비스 간 통신
* **API Communication:** REST API
* 예: Backend → LLM `http://llm:8000/...`

## Dependency & Environment Management
* **Python Version:** 3.13
* **Package Manager:** uv
* Python 프로젝트의 의존성 및 가상환경을 `uv`로 관리
* 프로젝트별 `pyproject.toml` 및 `uv.lock`을 통해 의존성 버전을 고정

## Version Control
* **Git:** 소스 코드 버전 관리
* **GitHub:** 원격 저장소 및 협업 관리
* **Branch Strategy:** `main` / `develop` / `feature/*`

## 관련 문서
* **시스템 구성:** `Docs/Design/ARCHITECTURE.md`
* **데이터 구조:** `Docs/Design/ERD.md`
