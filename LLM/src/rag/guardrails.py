import re

from src.data.contracts import VectorSearchResult
from src.rag.contracts import EligibilityDecision


INSUFFICIENT_EVIDENCE_ANSWER = (
    "제공된 공식 문서에서 질문에 답할 충분한 근거를 찾지 못했습니다. "
    "질문을 구체화하거나 관련 정책을 선택해 주세요."
)

_CLAUSE_SEPARATOR = re.compile(
    r"(?:그리고|그런데|하지만|또한|게다가|반면에|그러면서|하면서|해주고|알려주고|"
    r"[.!?;\n]+)"
)


class RagInputError(ValueError):
    """RAG 요청이 입력값 Guardrail을 위반했을 때 발생한다."""


def validate_question(question: str, *, max_length: int) -> str:
    """질문의 공백과 길이를 검증하고 정규화한 문자열을 반환한다.

    Args:
        question: 사용자가 입력한 원본 질문.
        max_length: 허용할 최대 문자 수.

    Returns:
        앞뒤 공백을 제거한 질문.

    Raises:
        RagInputError: 질문이 비었거나 최대 길이를 초과했을 때.
    """
    normalized_question = question.strip()
    if not normalized_question:
        raise RagInputError("question must not be blank")
    if len(normalized_question) > max_length:
        raise RagInputError(f"question must not exceed {max_length} characters")
    return normalized_question


def validate_top_k(top_k: int) -> int:
    """검색 결과 개수가 API 허용 범위인지 검사한다.

    Args:
        top_k: Vector Search에서 반환할 최대 Chunk 개수.

    Returns:
        검증이 완료된 top_k.

    Raises:
        RagInputError: top_k가 1~20 범위를 벗어났을 때.
    """
    if not 1 <= top_k <= 20:
        raise RagInputError("top_k must be between 1 and 20")
    return top_k


def is_question_in_scope(
    question: str,
    *,
    allowed_keywords: tuple[str, ...],
    blocked_keywords: tuple[str, ...] = (),
) -> bool:
    """질문의 모든 절이 정책·세무 서비스 범위에 포함되는지 검사한다.

    Args:
        question: 범위를 검사할 정규화된 사용자 질문.
        allowed_keywords: 각 질문 절에 하나 이상 포함돼야 하는 허용 키워드.
        blocked_keywords: 질문 전체에 하나라도 포함되면 차단할 키워드.

    Returns:
        차단 키워드가 없고 모든 질문 절이 허용 범위이면 True, 아니면 False.

    Notes:
        현재 키워드 기반 검사는 실제 평가 데이터가 확보되기 전의 임시 구현이다.
    """
    normalized_question = question.casefold()
    if any(
        keyword.casefold() in normalized_question for keyword in blocked_keywords
    ):
        return False

    question_clauses = [
        clause.strip() for clause in _CLAUSE_SEPARATOR.split(normalized_question)
    ]
    non_empty_clauses = [clause for clause in question_clauses if clause]
    return bool(non_empty_clauses) and all(
        any(keyword.casefold() in clause for keyword in allowed_keywords)
        for clause in non_empty_clauses
    )


def keep_grounded_results(
    results: list[VectorSearchResult],
    *,
    policy_id: int | None,
    min_score: float,
) -> list[VectorSearchResult]:
    """정책 필터와 최소 관련성 점수를 통과한 검색 결과만 유지한다.

    Args:
        results: 관련성 순서로 정렬된 Vector Search 결과.
        policy_id: 상세 검색 대상 정책 ID. None이면 정책 필터를 적용하지 않는다.
        min_score: 답변 근거로 사용할 최소 유사도 점수.

    Returns:
        입력 순서를 유지하면서 두 조건을 모두 통과한 검색 결과 목록.
    """
    return [
        search_result
        for search_result in results
        if search_result["score"] >= min_score
        and (policy_id is None or search_result["policy_id"] == policy_id)
    ]


def preserve_decision(
    decision: EligibilityDecision | None,
) -> EligibilityDecision | None:
    """Backend 판정값을 재계산하거나 변경하지 않고 그대로 반환한다.

    Args:
        decision: Backend가 Source of Truth로 확정한 선택적 자격 판정 결과.

    Returns:
        입력받은 동일한 EligibilityDecision 객체 또는 None.
    """
    return decision
