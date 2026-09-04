from typing import Literal

from pydantic import BaseModel


ComponentState = Literal["configured", "not_configured", "mock", "in_memory"]


class ComponentConfiguration(BaseModel):
    """Health 응답에 포함할 구성요소별 설정 상태."""

    llm: ComponentState
    embedding: ComponentState
    data_source: ComponentState


class HealthResponse(BaseModel):
    """LLM API 프로세스 Health 응답."""

    status: Literal["ok"] = "ok"
    service: str
    version: str
    components: ComponentConfiguration


class EligibilityDecisionRequest(BaseModel):
    """Backend가 확정해 LLM에 전달하는 자격 판정 결과."""

    eligible: bool
    reasons: list[str]


class RagAnswerRequest(BaseModel):
    """특정 정책 근거 답변을 요청하는 내부 API 본문."""

    question: str
    policy_id: int | None = None
    top_k: int | None = None
    decision: EligibilityDecisionRequest | None = None


class SourceResponse(BaseModel):
    """RAG 답변에서 사용자에게 제공할 Chunk 출처."""

    chunk_id: str
    policy_id: int
    title: str
    source: str
    page: int
    excerpt: str
    score: float


class RagAnswerResponse(BaseModel):
    """특정 정책의 근거 기반 답변과 출처 응답."""

    answer: str
    grounded: bool
    sources: list[SourceResponse]
    decision: EligibilityDecisionRequest | None = None
    guardrail_reason: Literal["out_of_scope", "insufficient_evidence"] | None = None


class PolicyRecommendationRequest(BaseModel):
    """사용자 프로필 기반 전체 정책 탐색 요청."""

    user_id: int
    question: str
    top_k: int | None = None


class MatchedPolicyResponse(BaseModel):
    """검색된 정책과 해당 정책을 뒷받침하는 출처 목록."""

    policy_id: int
    title: str
    sources: list[SourceResponse]


class PolicyRecommendationResponse(BaseModel):
    """사용자 조건과 관련된 정책 탐색·요약 응답."""

    user_id: int
    answer: str
    grounded: bool
    policies: list[MatchedPolicyResponse]
    guardrail_reason: Literal["out_of_scope", "insufficient_evidence"] | None = None


class IndexRequest(BaseModel):
    """로컬 캐시 무시 여부를 지정하는 인덱스 준비 요청."""

    force: bool = False


class IndexResponse(BaseModel):
    """인덱스 준비 결과와 캐시 또는 Embedding 출처 정보."""

    status: Literal["ready", "already_ready"]
    source: Literal["cache", "embedding"]
    document_count: int
    chunk_count: int


class ReadyResponse(BaseModel):
    """현재 프로세스의 RAG 요청 처리 준비 상태."""

    status: Literal["ready", "not_ready"]
    index_ready: bool
    llm_configured: bool
    embedding_configured: bool
    langsmith_tracing: bool
    document_count: int
    chunk_count: int
    index_source: Literal["cache", "embedding"] | None
