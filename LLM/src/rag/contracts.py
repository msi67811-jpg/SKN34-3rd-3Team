from dataclasses import dataclass
from typing import Literal

from src.data.contracts import VectorSearchResult


GuardrailReason = Literal["out_of_scope", "insufficient_evidence"]


@dataclass(frozen=True, slots=True)
class EligibilityDecision:
    """Backend가 확정한 자격 판정 결과."""

    eligible: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SourceCitation:
    """사용자에게 반환할 검색 근거와 출처 정보."""

    chunk_id: str
    policy_id: int
    title: str
    source: str
    page: int
    excerpt: str
    score: float

    @classmethod
    def from_search_result(
        cls,
        search_result: VectorSearchResult,
    ) -> "SourceCitation":
        """Vector 검색 결과를 출처 인용 객체로 변환한다.

        Args:
            search_result: Chunk 본문, 출처 metadata와 유사도 점수를 담은 검색 결과.

        Returns:
            공백을 정규화한 500자 근거 문구를 포함하는 SourceCitation 객체.
        """
        normalized_excerpt = " ".join(search_result["content"].split())[:500]
        return cls(
            chunk_id=search_result["chunk_id"],
            policy_id=search_result["policy_id"],
            title=search_result["title"],
            source=search_result["source"],
            page=search_result["page"],
            excerpt=normalized_excerpt,
            score=search_result["score"],
        )


@dataclass(frozen=True, slots=True)
class RagAnswer:
    """특정 정책 질의에 대한 답변·출처·판정 보존 결과."""

    answer: str
    grounded: bool
    sources: tuple[SourceCitation, ...]
    decision: EligibilityDecision | None = None
    guardrail_reason: GuardrailReason | None = None


@dataclass(frozen=True, slots=True)
class MatchedPolicy:
    """사용자 질문과 관련된 정책과 해당 검색 근거 묶음."""

    policy_id: int
    title: str
    sources: tuple[SourceCitation, ...]


@dataclass(frozen=True, slots=True)
class PolicyDiscoveryAnswer:
    """사용자 프로필 기반 전체 정책 탐색 결과."""

    user_id: int
    answer: str
    grounded: bool
    policies: tuple[MatchedPolicy, ...]
    guardrail_reason: GuardrailReason | None = None
