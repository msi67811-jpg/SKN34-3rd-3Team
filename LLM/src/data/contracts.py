from typing import TypedDict


class BusinessProfile(TypedDict):
    """사업자 정보 JSON 구조."""

    industry: str | None
    business_type: str | None
    founded_at: str | None


class UserProfile(TypedDict):
    """사용자와 사업자 정보를 결합한 JSON 구조."""

    user_id: int
    age: int | None
    region: str | None
    business: BusinessProfile


class Policy(TypedDict):
    """정책 기본 정보 JSON 구조."""

    policy_id: int
    title: str
    region: str
    industry: list[str]
    apply_start_date: str
    apply_end_date: str


class EligibilityResult(TypedDict):
    """Backend가 계산한 정책 자격 판정 결과 구조."""

    question: str
    policy_id: int
    eligible: bool
    reasons: list[str]


class RagChunk(TypedDict):
    """Embedding과 검색에 사용하는 RAG Chunk 구조."""

    chunk_id: str
    policy_id: int
    title: str
    source: str
    page: int
    content: str


class VectorSearchResult(RagChunk):
    """RAG Chunk에 유사도 점수가 추가된 검색 결과 구조."""

    score: float


class DocumentCatalogEntry(TypedDict):
    """원본 PDF와 정책 ID를 연결하는 catalog 항목 구조."""

    policy_id: int
    title: str
    file_name: str
