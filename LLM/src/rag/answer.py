"""Policy·Notice·Tax 상태를 공통 사용자 응답으로 변환한다."""

import json
from typing import Literal

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, ConfigDict, Field


AnswerStatus = Literal[
    "success",
    "need_more_info",
    "insufficient_evidence",
    "no_result",
    "integration_unavailable",
    "error",
]


class UnifiedAnswerResult(BaseModel):
    """Graph 최종 응답의 최소 Structured Output."""

    model_config = ConfigDict(extra="forbid")

    answer: str
    status: AnswerStatus
    cited_source_numbers: list[int] = Field(default_factory=list)


ANSWER_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "주어진 route Context에만 근거해 한국어로 직접 답하세요. 검색, 계산, "
            "법령 참조 추적을 새로 수행하지 마세요. Context에 없는 정책·공고·세법 "
            "내용을 만들지 마세요. 출처는 1부터 시작하는 번호로만 선택하세요. "
            "status는 반드시 {status}로 반환하세요.",
        ),
        (
            "human",
            "route={route}\npersonalized={personalized}\n질문: {query}\n"
            "사용자 Context: {user_context}\nroute Context:\n{route_context}",
        ),
    ]
)


async def generate_unified_answer(
    llm: BaseChatModel,
    *,
    query: str,
    route: str,
    personalized: bool,
    user_context: dict[str, object] | None,
    route_context: dict[str, object],
    status: AnswerStatus,
    source_count: int,
) -> UnifiedAnswerResult:
    """route에 필요한 Context만 전달해 최종 Structured Output을 생성한다."""
    chain = ANSWER_PROMPT | llm.with_structured_output(UnifiedAnswerResult)
    result = UnifiedAnswerResult.model_validate(
        await chain.ainvoke(
            {
                "query": query,
                "route": route,
                "personalized": personalized,
                "user_context": json.dumps(user_context, ensure_ascii=False),
                "route_context": json.dumps(route_context, ensure_ascii=False),
                "status": status,
            },
            config={"run_name": "langgraph_unified_answer"},
        )
    )
    if result.status != status:
        raise ValueError("Unified answer changed the deterministic status")
    invalid_numbers = [
        number
        for number in result.cited_source_numbers
        if number < 1 or number > source_count
    ]
    if invalid_numbers:
        raise ValueError("Unified answer cited an unavailable source")
    if source_count and not result.cited_source_numbers:
        raise ValueError("Unified answer must cite at least one available source")
    return result.model_copy(
        update={"cited_source_numbers": list(dict.fromkeys(result.cited_source_numbers))}
    )


def fallback_answer(
    status: AnswerStatus,
    *,
    missing_user_context: list[str] | None = None,
) -> UnifiedAnswerResult:
    """근거가 없거나 integration이 없을 때 LLM 호출 없이 안전하게 응답한다."""
    messages: dict[AnswerStatus, str] = {
        "success": "확인된 근거를 바탕으로 답변했습니다.",
        "need_more_info": "정확한 판단을 위해 추가 정보가 필요합니다.",
        "insufficient_evidence": "현재 확인된 근거만으로는 확정하기 어렵습니다.",
        "no_result": "현재 조건에 맞는 결과를 찾지 못했습니다.",
        "integration_unavailable": "현재 실제 데이터를 조회하거나 계산할 수 없습니다.",
        "error": "요청을 처리하는 중 오류가 발생했습니다.",
    }
    answer = messages[status]
    if status == "need_more_info" and missing_user_context:
        answer = "정확한 판단을 위해 다음 정보가 필요합니다: " + ", ".join(
            missing_user_context
        )
    return UnifiedAnswerResult(answer=answer, status=status)
