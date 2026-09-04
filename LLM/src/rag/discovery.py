import asyncio
from collections.abc import Callable

from langchain_core.language_models.chat_models import BaseChatModel
from langsmith import traceable, tracing_context

from src.core.config import Settings
from src.core.langsmith import configure_langsmith
from src.data.contracts import UserProfile, VectorSearchResult
from src.rag.chain import generate_policy_summary
from src.rag.contracts import MatchedPolicy, PolicyDiscoveryAnswer, SourceCitation
from src.rag.guardrails import (
    INSUFFICIENT_EVIDENCE_ANSWER,
    is_question_in_scope,
    validate_question,
    validate_top_k,
)
from src.rag.query_builder import build_personalized_query
from src.rag.retriever import RagRetriever
from src.vectorstores.base import VectorSearch


class PolicyDiscoveryService:
    """자격을 판정하지 않고 사용자 프로필과 관련된 정책을 탐색한다."""

    def __init__(
        self,
        *,
        vector_search: VectorSearch,
        llm_factory: Callable[[], BaseChatModel],
        settings: Settings,
    ) -> None:
        """사용자 기반 정책 탐색 서비스의 의존성을 초기화한다.

        Args:
            vector_search: 전체 정책 문서를 검색할 구현체.
            llm_factory: 검색 근거가 있을 때만 채팅 모델을 생성할 함수.
            settings: 검색 임계값, Guardrail과 LangSmith 설정.
        """
        self._retriever = RagRetriever(
            vector_search,
            min_score=settings.min_relevance_score,
        )
        self._llm_factory = llm_factory
        self._settings = settings

    async def discover(
        self,
        question: str,
        *,
        user: UserProfile,
        top_k: int | None = None,
    ) -> PolicyDiscoveryAnswer:
        """사용자 프로필과 질문을 결합해 관련 정책을 검색·요약한다.

        Args:
            question: 사용자가 입력한 정책 탐색 질문.
            user: 검색 Query와 답변 문맥에 사용할 사용자·사업자 정보.
            top_k: 전체 정책에서 검색할 최대 Chunk 개수. None이면 설정 기본값.

        Returns:
            관련 정책별 출처, 요약 답변과 Guardrail 차단 사유를 담은 결과.

        Raises:
            RagInputError: 질문 또는 top_k가 허용 범위를 벗어났을 때.
            LangSmithConfigurationError: tracing 설정이 불완전할 때.

        Notes:
            사용자 정보는 검색 관련성에만 사용하며 지원 자격을 판정하지 않는다.
        """
        normalized_question = validate_question(
            question,
            max_length=self._settings.max_question_length,
        )
        result_limit = validate_top_k(
            top_k if top_k is not None else self._settings.default_top_k
        )
        if not is_question_in_scope(
            normalized_question,
            allowed_keywords=self._settings.allowed_rag_keywords,
            blocked_keywords=self._settings.blocked_rag_keywords,
        ):
            return PolicyDiscoveryAnswer(
                user_id=user["user_id"],
                answer=self._settings.out_of_scope_answer,
                grounded=False,
                policies=(),
                guardrail_reason="out_of_scope",
            )
        langsmith_runtime = configure_langsmith(self._settings)

        with tracing_context(
            project_name=langsmith_runtime.project_name,
            tags=["rag", "policy-discovery", "in-memory"],
            metadata={"flow": "personalized-policy-discovery"},
            enabled=langsmith_runtime.enabled,
            client=langsmith_runtime.client,
        ):
            return await self._discover_traced(
                normalized_question,
                user=user,
                top_k=result_limit,
            )

    @traceable(name="policy_discovery", run_type="chain")
    async def _discover_traced(
        self,
        question: str,
        *,
        user: UserProfile,
        top_k: int,
    ) -> PolicyDiscoveryAnswer:
        """개인화 검색부터 정책별 요약까지 LangSmith 하위 trace로 실행한다.

        Args:
            question: 입력 검증과 범위 검사를 통과한 정책 탐색 질문.
            user: 개인화 검색 Query와 답변 문맥에 사용할 사용자 프로필.
            top_k: 전체 정책에서 검색할 최대 Chunk 개수.

        Returns:
            근거가 없으면 차단 결과, 있으면 정책별 출처와 요약을 담은 결과.
        """
        personalized_query = build_personalized_query(question, user)
        relevant_chunks = await asyncio.to_thread(
            self._retriever.retrieve,
            personalized_query,
            policy_id=None,
            top_k=top_k,
        )
        if not relevant_chunks:
            return PolicyDiscoveryAnswer(
                user_id=user["user_id"],
                answer=INSUFFICIENT_EVIDENCE_ANSWER,
                grounded=False,
                policies=(),
                guardrail_reason="insufficient_evidence",
            )

        generated_summary = await generate_policy_summary(
            self._llm_factory(),
            question=question,
            user=user,
            results=relevant_chunks,
        )
        return PolicyDiscoveryAnswer(
            user_id=user["user_id"],
            answer=generated_summary.strip(),
            grounded=True,
            policies=_group_chunks_by_policy(relevant_chunks),
            guardrail_reason=None,
        )


def _group_chunks_by_policy(
    retrieved_chunks: list[VectorSearchResult],
) -> tuple[MatchedPolicy, ...]:
    """검색 순서를 유지하면서 Chunk를 policy_id별 결과로 묶는다.

    Args:
        retrieved_chunks: 관련성 순서로 정렬된 Chunk 검색 결과.

    Returns:
        최초 등장한 정책 순서를 유지한 정책별 출처 묶음.
    """
    chunks_by_policy: dict[int, list[VectorSearchResult]] = {}
    for retrieved_chunk in retrieved_chunks:
        chunks_by_policy.setdefault(retrieved_chunk["policy_id"], []).append(
            retrieved_chunk
        )

    return tuple(
        MatchedPolicy(
            policy_id=policy_id,
            title=policy_results[0]["title"],
            sources=tuple(
                SourceCitation.from_search_result(policy_chunk)
                for policy_chunk in policy_results
            ),
        )
        for policy_id, policy_results in chunks_by_policy.items()
    )
