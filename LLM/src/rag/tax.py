"""Tax Multi-hop에서 사용하는 구조화 판단과 최소 법령 참조 해석."""

import json
import re

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, ConfigDict, Field

from src.data.contracts import UserProfile, VectorSearchResult


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
            "질문: {query}\n사용자 Context: {user_context}\n법령 근거:\n{evidence}",
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
) -> TaxEvidenceDecision:
    """누적 법령과 사용자 Context를 Structured Output으로 평가한다."""
    chain = EVIDENCE_PROMPT | llm.with_structured_output(TaxEvidenceDecision)
    result = await chain.ainvoke(
        {
            "query": query,
            "user_context": json.dumps(user_context, ensure_ascii=False),
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
    """Structured 판단 Prompt에 전달할 실제 법령 근거만 직렬화한다."""
    return "\n\n".join(
        f"[{index}] {document['title']}\n{document['content']}\n"
        f"source={document['source']} chunk_id={document['chunk_id']}"
        for index, document in enumerate(documents, start=1)
    ) or "근거 없음"
