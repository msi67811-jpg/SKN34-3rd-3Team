import asyncio
from collections.abc import Callable

from langchain_core.exceptions import OutputParserException
from langchain_core.language_models.chat_models import BaseChatModel
from langsmith import traceable, tracing_context
from pydantic import ValidationError

from src.core.config import Settings
from src.core.langsmith import configure_langsmith
from src.data.contracts import UserProfile
from src.rag.chain import (
    compact_policy_discovery,
    format_policy_discovery_answer,
    generate_policy_summary,
)
from src.rag.contracts import (
    GeneratedPolicyDiscovery,
    MatchedPolicy,
    PolicyDiscoveryAnswer,
    SourceCitation,
)
from src.rag.context_builder import PromptContext, build_prompt_context
from src.rag.guardrails import (
    GenerationValidationError,
    INSUFFICIENT_EVIDENCE_ANSWER,
    is_question_in_scope,
    validate_citation_numbers,
    validate_generated_policy_ids,
    validate_generated_text,
    validate_policy_citations,
    validate_question,
    validate_top_k,
)
from src.rag.retriever import retrieve_relevant_chunks
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
        self._vector_search = vector_search
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
            retrieve_relevant_chunks,
            self._vector_search,
            personalized_query,
            policy_id=None,
            top_k=top_k,
            min_score=self._settings.min_relevance_score,
        )
        relevant_chunks = [
            chunk for chunk in relevant_chunks if chunk["policy_id"] is not None
        ]
        if not relevant_chunks:
            return PolicyDiscoveryAnswer(
                user_id=user["user_id"],
                answer=INSUFFICIENT_EVIDENCE_ANSWER,
                grounded=False,
                policies=(),
                guardrail_reason="insufficient_evidence",
            )

        prompt_context = build_prompt_context(
            relevant_chunks,
            max_context_characters=self._settings.max_context_characters,
            max_chunks_per_policy=self._settings.max_chunks_per_policy,
        )
        try:
            structured_discovery = await generate_policy_summary(
                self._llm_factory(),
                question=question,
                user=user,
                prompt_context=prompt_context,
            )
            structured_discovery = compact_policy_discovery(structured_discovery)
            matched_policies = _build_matched_policies(
                structured_discovery,
                prompt_context,
            )
            policy_titles = {
                policy.policy_id: policy.title for policy in matched_policies
            }
            generated_answer = format_policy_discovery_answer(
                structured_discovery,
                policy_titles=policy_titles,
            )
        except (GenerationValidationError, OutputParserException, ValidationError):
            return PolicyDiscoveryAnswer(
                user_id=user["user_id"],
                answer=self._settings.invalid_generation_answer,
                grounded=False,
                policies=(),
                guardrail_reason="generation_validation_failed",
            )

        return PolicyDiscoveryAnswer(
            user_id=user["user_id"],
            answer=generated_answer,
            grounded=True,
            policies=matched_policies,
            guardrail_reason=None,
        )


@traceable(name="build_personalized_query", run_type="chain")
def build_personalized_query(question: str, user: UserProfile) -> str:
    """사용자 질문과 제공된 프로필 정보를 의미 검색용 Query로 결합한다.

    Args:
        question: 사용자가 입력한 정책 탐색 질문.
        user: 검색 개인화에 사용할 사용자·사업자 정보.

    Returns:
        질문과 누락되지 않은 프로필 필드를 결합한 검색 Query.
    """
    business_profile = user["business"]
    profile_descriptions = [
        _format_profile_value("나이", user["age"], suffix="세"),
        _format_profile_value("지역", user["region"]),
        _format_profile_value("업종", business_profile["industry"]),
        _format_profile_value("사업자 유형", business_profile["business_type"]),
        _format_profile_value("창업일", business_profile["founded_at"]),
    ]
    available_descriptions = [
        description
        for description in profile_descriptions
        if description is not None
    ]
    profile_context = ", ".join(available_descriptions) or "제공된 사용자 조건 없음"
    return f"사용자 질문: {question}\n사용자 조건: {profile_context}"


def _format_profile_value(
    label: str,
    value: object | None,
    *,
    suffix: str = "",
) -> str | None:
    """검색 Query용 프로필 필드를 누락값 없이 한 구절로 만든다."""
    if value is None or str(value).strip() == "":
        return None
    return f"{label} {value}{suffix}"


def _build_matched_policies(
    structured_discovery: GeneratedPolicyDiscovery,
    prompt_context: PromptContext,
) -> tuple[MatchedPolicy, ...]:
    """구조화 정책 출력을 실제 Retriever 정책·출처 객체로 변환한다.

    Args:
        structured_discovery: LLM이 반환한 정책별 구조화 요약.
        prompt_context: LLM에 실제 제공한 번호가 있는 검색 근거.

    Returns:
        검색 결과에서 policy_id, 제목과 출처를 가져온 정책별 결과.

    Raises:
        GenerationValidationError: 빈 요약, 알 수 없는 정책 또는 잘못된 출처일 때.
    """
    validate_generated_text(structured_discovery.overview, field_name="overview")
    retrieved_policy_ids = {
        chunk["policy_id"] for chunk in prompt_context.selected_chunks
    }
    validate_generated_policy_ids(
        [policy.policy_id for policy in structured_discovery.policies],
        retrieved_policy_ids=retrieved_policy_ids,
    )

    matched_policies: list[MatchedPolicy] = []
    for generated_policy in structured_discovery.policies:
        validate_generated_text(generated_policy.summary, field_name="summary")
        citation_numbers = validate_citation_numbers(
            generated_policy.cited_source_numbers,
            source_count=len(prompt_context.selected_chunks),
        )
        validate_policy_citations(
            generated_policy.policy_id,
            citation_numbers,
            prompt_context.selected_chunks,
        )
        policy_chunks = tuple(
            prompt_context.selected_chunks[source_number - 1]
            for source_number in citation_numbers
        )
        representative_chunk = policy_chunks[0]
        matched_policies.append(
            MatchedPolicy(
                policy_id=representative_chunk["policy_id"],
                title=representative_chunk["title"],
                sources=tuple(
                    SourceCitation.from_search_result(policy_chunk)
                    for policy_chunk in policy_chunks
                ),
            )
        )
    return tuple(matched_policies)
