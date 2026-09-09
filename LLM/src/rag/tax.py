"""Tax Multi-hop에서 사용하는 구조화 판단과 최소 법령 참조 해석."""

import json
import re
from decimal import Decimal, InvalidOperation
from typing import Literal

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, ConfigDict, Field

from src.data.contracts import UserProfile, VectorSearchResult
from src.data.tax_normalization import (
    decimal_text,
    extract_legal_percentages,
    normalize_legal_percentage,
)


class TaxEvidenceDecision(BaseModel):
    """법령 근거와 사용자 Context의 충족 여부를 분리한 구조화 판단."""

    model_config = ConfigDict(extra="forbid")

    sufficient: bool
    missing_information: list[str] = Field(default_factory=list)
    missing_user_context: list[str] = Field(default_factory=list)
    calculation_required: bool = False
    reason: str


class TaxNextQuery(BaseModel):
    """명시적 법령 참조가 없을 때 생성하는 다음 검색 Query."""

    model_config = ConfigDict(extra="forbid")

    query: str | None
    target_law: str | None = None
    target_article: str | None = None
    reason: str


class TaxCalculationPlan(BaseModel):
    """근거에서 추출한 최소 결정적 계산 계획."""

    model_config = ConfigDict(extra="forbid")

    calculation_type: Literal[
        "percentage_of_amount",
        "reduction_amount",
        "amount_after_reduction",
    ]
    base_amount: str | None = None
    rate_percent: str | None = None
    missing_inputs: list[str] = Field(default_factory=list)
    cited_source_numbers: list[int] = Field(default_factory=list)
    reason: str


class TaxCalculationError(ValueError):
    """입력값이나 법령 출처로 계산 계획을 검증할 수 없을 때 발생한다."""


EVIDENCE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "세법 질문에 답하기 위한 법령 근거가 충분한지 판단하세요. "
            "법령 근거 부족은 missing_information에, 사용자 나이·지역·업종·"
            "창업일 등 사용자 정보 부족은 missing_user_context에 분리하세요. "
            "세액 또는 예상 세금 계산이 필요할 때만 calculation_required를 "
            "true로 반환하고 직접 계산하지 마세요.",
        ),
        (
            "human",
            "질문: {query}\n사용자 Context: {user_context}\n"
            "정규화된 비율: {normalized_ratios}\n법령 근거:\n{evidence}",
        ),
    ]
)

NEXT_QUERY_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "부족한 세법 근거를 찾기 위한 다음 검색어 하나만 구조화해 반환하세요. "
            "이미 실행한 검색어를 반복하지 마세요. 검색을 더 구체화할 수 없으면 "
            "query를 null로 반환하세요.",
        ),
        (
            "human",
            "원 질문: {query}\n부족한 정보: {missing_information}\n"
            "사용자 Context: {user_context}\n검색 이력: {search_history}\n"
            "현재 근거:\n{evidence}",
        ),
    ]
)

CALCULATION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "세금 계산 결과를 직접 만들지 말고 계산 계획만 구조화하세요. "
            "base_amount는 질문 또는 사용자 Context에 명시된 값만 사용하고, "
            "rate_percent는 법령 근거에 실제 표시된 비율만 사용하세요. "
            "과세표준과 산출세액을 혼동하지 마세요. 값이 없으면 추정하지 말고 "
            "missing_inputs에 필요한 항목을 기록하세요. 사용한 법령 출처 번호를 "
            "cited_source_numbers에 기록하세요.",
        ),
        (
            "human",
            "질문: {query}\n사용자 Context: {user_context}\n법령 근거:\n{evidence}",
        ),
    ]
)

_NAMED_REFERENCE = re.compile(
    r"([가-힣A-Za-z0-9·]+법(?:\s+시행령|\s+시행규칙)?)\s*제\s*(\d+)\s*조"
)
_SAME_LAW_REFERENCE = re.compile(r"같은\s*법\s*제\s*(\d+)\s*조")
_ARTICLE_REFERENCE = re.compile(r"제\s*(\d+)\s*조(?:에\s*따른|의)??")
_PRESIDENTIAL_DECREE = re.compile(r"대통령령으로\s*정하는")


async def evaluate_tax_evidence(
    llm: BaseChatModel,
    *,
    query: str,
    documents: list[VectorSearchResult],
    user_context: UserProfile | None,
    normalized_ratios: list[dict[str, object]] | None = None,
) -> TaxEvidenceDecision:
    """누적 법령과 사용자 Context를 Structured Output으로 평가한다."""
    chain = EVIDENCE_PROMPT | llm.with_structured_output(TaxEvidenceDecision)
    result = await chain.ainvoke(
        {
            "query": query,
            "user_context": json.dumps(user_context, ensure_ascii=False),
            "normalized_ratios": json.dumps(
                normalized_ratios or [], ensure_ascii=False
            ),
            "evidence": _format_evidence(documents),
        },
        config={"run_name": "tax_evidence_evaluator"},
    )
    return TaxEvidenceDecision.model_validate(result)


async def generate_tax_next_query(
    llm: BaseChatModel,
    *,
    query: str,
    documents: list[VectorSearchResult],
    missing_information: list[str],
    user_context: UserProfile | None,
    search_history: list[str],
) -> TaxNextQuery:
    """Reference로 검색어를 정할 수 없을 때 다음 검색어를 생성한다."""
    chain = NEXT_QUERY_PROMPT | llm.with_structured_output(TaxNextQuery)
    result = await chain.ainvoke(
        {
            "query": query,
            "missing_information": ", ".join(missing_information),
            "user_context": json.dumps(user_context, ensure_ascii=False),
            "search_history": " | ".join(search_history),
            "evidence": _format_evidence(documents),
        },
        config={"run_name": "tax_next_query_generator"},
    )
    return TaxNextQuery.model_validate(result)


async def generate_tax_calculation_plan(
    llm: BaseChatModel,
    *,
    query: str,
    documents: list[VectorSearchResult],
    user_context: UserProfile | None,
) -> TaxCalculationPlan:
    """검색 근거와 명시적 사용자 값만 이용해 계산 계획을 생성한다."""
    chain = CALCULATION_PROMPT | llm.with_structured_output(TaxCalculationPlan)
    result = await chain.ainvoke(
        {
            "query": query,
            "user_context": json.dumps(user_context, ensure_ascii=False),
            "evidence": _format_evidence(documents),
        },
        config={"run_name": "tax_calculation_plan"},
    )
    return TaxCalculationPlan.model_validate(result)


def calculate_tax_plan(
    plan: TaxCalculationPlan,
    *,
    documents: list[VectorSearchResult],
) -> dict[str, object]:
    """검증된 기준금액과 법령 비율을 Decimal로 계산한다.

    Raises:
        TaxCalculationError: 필수 입력, 출처 또는 근거 비율이 유효하지 않을 때.
    """
    if plan.missing_inputs:
        raise TaxCalculationError("calculation inputs are missing")
    if plan.base_amount is None or plan.rate_percent is None:
        raise TaxCalculationError("base_amount and rate_percent are required")
    try:
        base_amount = Decimal(plan.base_amount.replace(",", ""))
        rate_percent = Decimal(plan.rate_percent.replace(",", ""))
    except InvalidOperation as exc:
        raise TaxCalculationError("calculation contains an invalid decimal") from exc
    if base_amount < 0:
        raise TaxCalculationError("base_amount must not be negative")
    if not Decimal(0) <= rate_percent <= Decimal(100):
        raise TaxCalculationError("rate_percent must be between 0 and 100")

    source_numbers = list(dict.fromkeys(plan.cited_source_numbers))
    if not source_numbers or any(
        number < 1 or number > len(documents) for number in source_numbers
    ):
        raise TaxCalculationError("calculation source number is invalid")
    cited_documents = [documents[number - 1] for number in source_numbers]
    supported_rates = set().union(
        *(extract_legal_percentages(document["content"]) for document in cited_documents)
    )
    if rate_percent not in supported_rates:
        raise TaxCalculationError("rate_percent is not present in cited evidence")

    proportional_amount = base_amount * rate_percent / Decimal(100)
    if plan.calculation_type == "amount_after_reduction":
        result_amount = base_amount - proportional_amount
        result_name = "amount_after_reduction"
        formula = "base_amount - (base_amount × rate_percent ÷ 100)"
    else:
        result_amount = proportional_amount
        result_name = (
            "reduction_amount"
            if plan.calculation_type == "reduction_amount"
            else "calculated_amount"
        )
        formula = "base_amount × rate_percent ÷ 100"

    try:
        values = {
            "calculation_type": plan.calculation_type,
            "base_amount": decimal_text(base_amount),
            "rate_percent": decimal_text(rate_percent),
            result_name: decimal_text(result_amount),
            "formula": formula,
            "cited_source_numbers": source_numbers,
        }
    except InvalidOperation as exc:
        raise TaxCalculationError("calculation contains an invalid decimal") from exc
    return values


def resolve_legal_reference(
    documents: list[VectorSearchResult],
    *,
    search_history: list[str],
) -> str | None:
    """누적 근거에서 최소 법령 패턴을 찾아 아직 검색하지 않은 참조를 반환한다."""
    searched = {query.casefold().strip() for query in search_history}
    for document in reversed(documents):
        content = document["content"]
        title = document["title"].strip()
        candidates = [
            f"{law_name} 제{article}조"
            for law_name, article in _NAMED_REFERENCE.findall(content)
        ]
        candidates.extend(
            f"{title} 제{article}조"
            for article in _SAME_LAW_REFERENCE.findall(content)
        )
        if _PRESIDENTIAL_DECREE.search(content) and title.endswith("법"):
            candidates.append(f"{title} 시행령")
        candidates.extend(
            f"{title} 제{article}조"
            for article in _ARTICLE_REFERENCE.findall(content)
        )
        for candidate in candidates:
            normalized = candidate.casefold().strip()
            if normalized and normalized not in searched:
                return candidate
    return None


def merge_evidence(
    existing: list[VectorSearchResult],
    new_documents: list[VectorSearchResult],
) -> list[VectorSearchResult]:
    """Chunk ID 기준으로 기존 순서를 유지하며 새로운 법령 근거만 누적한다."""
    merged = list(existing)
    seen = {document["chunk_id"] for document in existing}
    for document in new_documents:
        if document["chunk_id"] not in seen:
            merged.append(document)
            seen.add(document["chunk_id"])
    return merged


def _format_evidence(documents: list[VectorSearchResult]) -> str:
    """검색된 원문을 변경하지 않고 Prompt에서만 법령 비율을 함께 표시한다."""
    return "\n\n".join(
        f"[{index}] {document['title']}\n"
        f"{normalize_legal_percentage(document['content'])}\n"
        f"source={document['source']} chunk_id={document['chunk_id']}"
        for index, document in enumerate(documents, start=1)
    ) or "근거 없음"
