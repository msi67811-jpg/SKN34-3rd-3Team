from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langsmith import traceable

from src.data.contracts import UserProfile, VectorSearchResult
from src.rag.contracts import EligibilityDecision
from src.rag.prompts import (
    POLICY_DISCOVERY_PROMPT,
    RAG_PROMPT,
    format_decision_context,
    format_document_context,
)
from src.rag.query_builder import format_user_context


@traceable(name="generate_answer", run_type="chain")
async def generate_answer(
    llm: BaseChatModel,
    *,
    question: str,
    results: list[VectorSearchResult],
    decision: EligibilityDecision | None,
) -> str:
    """특정 정책 근거와 Backend 판정을 이용해 답변을 생성한다.

    Args:
        llm: 답변 생성에 사용할 LangChain 채팅 모델.
        question: 사용자가 입력한 특정 정책 질문.
        results: Retriever가 반환한 관련 근거 Chunk.
        decision: Backend가 확정한 선택적 자격 판정 결과.

    Returns:
        문서 출처 번호가 포함된 자연어 답변.

    Notes:
        `ainvoke()`에서 실제 LLM API가 호출된다.
    """
    grounded_answer_chain = RAG_PROMPT | llm | StrOutputParser()
    return await grounded_answer_chain.ainvoke(
        {
            "question": question,
            "document_context": format_document_context(results),
            "decision_context": format_decision_context(decision),
        },
        config={
            "run_name": "grounded_rag_generation",
            "tags": ["rag", "grounded-answer"],
            "metadata": {
                "policy_id": results[0]["policy_id"] if results else None,
                "source_count": len(results),
            },
        },
    )


@traceable(name="generate_policy_summary", run_type="chain")
async def generate_policy_summary(
    llm: BaseChatModel,
    *,
    question: str,
    user: UserProfile,
    results: list[VectorSearchResult],
) -> str:
    """사용자 프로필과 검색 근거를 이용해 관련 정책을 요약한다.

    Args:
        llm: 정책 요약에 사용할 LangChain 채팅 모델.
        question: 사용자가 입력한 정책 탐색 질문.
        user: 검색과 설명을 개인화할 사용자·사업자 정보.
        results: 전체 정책에서 검색한 관련 근거 Chunk.

    Returns:
        관련 정책과 한계를 출처 번호와 함께 설명한 자연어 답변.

    Notes:
        사용자 프로필은 관련성 설명에만 사용하며 자격 판정에는 사용하지 않는다.
        `ainvoke()`에서 실제 LLM API가 호출된다.
    """
    policy_summary_chain = POLICY_DISCOVERY_PROMPT | llm | StrOutputParser()
    return await policy_summary_chain.ainvoke(
        {
            "question": question,
            "user_context": format_user_context(user),
            "document_context": format_document_context(results),
        },
        config={
            "run_name": "personalized_policy_summary",
            "tags": ["rag", "policy-discovery", "personalized"],
            "metadata": {
                "source_count": len(results),
                "policy_count": len({result["policy_id"] for result in results}),
            },
        },
    )
