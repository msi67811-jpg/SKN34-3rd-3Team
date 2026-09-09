import asyncio

import pytest

from src.core.config import Settings
from src.data.contracts import VectorSearchResult
from src.rag.graph import RouteDecision, build_graph
from src.rag.answer import UnifiedAnswerResult
from src.rag.tax import (
    TaxCalculationError,
    TaxCalculationPlan,
    TaxEvidenceDecision,
    TaxNextQuery,
    calculate_tax_plan,
    evaluate_tax_evidence,
    generate_tax_calculation_plan,
    generate_tax_next_query,
)
from tests.fakes import FakeStructuredChatModel


def _tax_document(chunk_id: str, content: str) -> VectorSearchResult:
    return {
        "chunk_id": chunk_id,
        "policy_id": None,
        "title": "조세특례제한법",
        "source": f"db://tax_documents/{chunk_id}",
        "page": 1,
        "content": content,
        "score": 0.8,
    }


class SequentialTaxSearch:
    def __init__(self, results: list[list[VectorSearchResult]]) -> None:
        self.results = results
        self.call_count = 0

    def search_stages(
        self,
        _query: str,
        *,
        policy_id: int | None,
        top_k: int,
    ) -> tuple[
        list[VectorSearchResult],
        list[VectorSearchResult],
        list[VectorSearchResult],
    ]:
        index = min(self.call_count, len(self.results) - 1)
        self.call_count += 1
        result = self.results[index][:top_k]
        return result, result, result


def _router_llm() -> FakeStructuredChatModel:
    return FakeStructuredChatModel(
        {
            RouteDecision: {"route": "tax", "personalized": False},
            UnifiedAnswerResult: {
                "answer": "누적 법령 근거 기반 답변",
                "status": "success",
                "cited_source_numbers": [1],
            },
        }
    )


def _identity_rerank(
    _query: str,
    documents: list[VectorSearchResult],
    top_n: int,
) -> list[VectorSearchResult]:
    return documents[:top_n]


def _decision(
    *,
    sufficient: bool,
    missing_information: list[str] | None = None,
    missing_user_context: list[str] | None = None,
    calculation_required: bool = False,
) -> TaxEvidenceDecision:
    return TaxEvidenceDecision(
        sufficient=sufficient,
        missing_information=missing_information or [],
        missing_user_context=missing_user_context or [],
        calculation_required=calculation_required,
        reason="test",
    )


def test_tax_single_hop_stops_when_evidence_is_sufficient() -> None:
    search = SequentialTaxSearch(
        [[_tax_document("tax-1", "청년창업 세액감면 요건")]]
    )

    async def evaluate(_state: object) -> TaxEvidenceDecision:
        return _decision(sufficient=True)

    result = asyncio.run(
        build_graph(
            _router_llm(),
            tax_search=search,  # type: ignore[arg-type]
            rerank=_identity_rerank,
            tax_evidence_evaluator=evaluate,  # type: ignore[arg-type]
            settings=Settings(_env_file=None),
        ).ainvoke({"query": "청년창업 세액감면이 뭐야?"})
    )

    assert search.call_count == 1
    assert result["evidence_sufficient"] is True
    assert result["hop_count"] == 1
    assert result["termination_reason"] == "evidence_sufficient"
    assert result["answer_status"] == "success"
    assert result["answer"] == "누적 법령 근거 기반 답변"
    assert result["answer_sources"][0]["chunk_id"] == "tax-1"


def test_tax_multi_hop_accumulates_new_evidence() -> None:
    search = SequentialTaxSearch(
        [
            [_tax_document("tax-1", "감면 대상 업종 확인 필요")],
            [_tax_document("tax-2", "음식점업의 감면 적용 요건")],
        ]
    )
    decisions = iter(
        [
            _decision(sufficient=False, missing_information=["업종 요건"]),
            _decision(sufficient=True),
        ]
    )

    async def evaluate(_state: object) -> TaxEvidenceDecision:
        return next(decisions)

    async def next_query(_state: object) -> TaxNextQuery:
        return TaxNextQuery(
            query="청년창업 세액감면 음식점업 요건",
            reason="업종 요건 필요",
        )

    result = asyncio.run(
        build_graph(
            _router_llm(),
            tax_search=search,  # type: ignore[arg-type]
            rerank=_identity_rerank,
            tax_evidence_evaluator=evaluate,  # type: ignore[arg-type]
            tax_next_query_generator=next_query,  # type: ignore[arg-type]
            settings=Settings(_env_file=None, tax_max_hops=3),
        ).ainvoke({"query": "27살 서울 음식점 창업 세액감면 대상이야?"})
    )

    assert result["hop_count"] == 2
    assert result["search_history"] == [
        "27살 서울 음식점 창업 세액감면 대상이야?",
        "청년창업 세액감면 음식점업 요건",
    ]
    assert [doc["chunk_id"] for doc in result["reranked_docs"]] == [
        "tax-1",
        "tax-2",
    ]


def test_explicit_reference_has_priority_over_next_query_generator() -> None:
    search = SequentialTaxSearch(
        [
            [_tax_document("tax-1", "조세특례제한법 제6조에 따른 감면")],
            [_tax_document("tax-2", "조세특례제한법 제6조 세부 요건")],
        ]
    )
    decisions = iter([_decision(sufficient=False), _decision(sufficient=True)])
    next_query_calls = 0

    async def evaluate(_state: object) -> TaxEvidenceDecision:
        return next(decisions)

    async def next_query(_state: object) -> TaxNextQuery:
        nonlocal next_query_calls
        next_query_calls += 1
        return TaxNextQuery(query="사용되면 안 됨", reason="test")

    result = asyncio.run(
        build_graph(
            _router_llm(),
            tax_search=search,  # type: ignore[arg-type]
            rerank=_identity_rerank,
            tax_evidence_evaluator=evaluate,  # type: ignore[arg-type]
            tax_next_query_generator=next_query,  # type: ignore[arg-type]
        ).ainvoke({"query": "세액감면 근거 알려줘"})
    )

    assert next_query_calls == 0
    assert result["search_history"][1] == "조세특례제한법 제6조"


def test_duplicate_query_stops_loop() -> None:
    async def evaluate(_state: object) -> TaxEvidenceDecision:
        return _decision(sufficient=False)

    async def duplicate_query(_state: object) -> TaxNextQuery:
        return TaxNextQuery(query="세액감면 요건", reason="test")

    result = asyncio.run(
        build_graph(
            _router_llm(),
            tax_search=SequentialTaxSearch(
                [[_tax_document("tax-1", "추가 확인 필요")]]
            ),  # type: ignore[arg-type]
            rerank=_identity_rerank,
            tax_evidence_evaluator=evaluate,  # type: ignore[arg-type]
            tax_next_query_generator=duplicate_query,  # type: ignore[arg-type]
        ).ainvoke({"query": "세액감면 요건"})
    )

    assert result["hop_count"] == 1
    assert result["termination_reason"] == "duplicate_query"
    assert result["evidence_sufficient"] is False


def test_max_hops_keeps_insufficient_evidence_state() -> None:
    search = SequentialTaxSearch(
        [
            [_tax_document("tax-1", "첫 근거")],
            [_tax_document("tax-2", "두 번째 근거")],
        ]
    )
    next_queries = iter(["두 번째 검색", "세 번째 검색"])

    async def evaluate(_state: object) -> TaxEvidenceDecision:
        return _decision(sufficient=False, missing_information=["추가 근거"])

    async def next_query(_state: object) -> TaxNextQuery:
        return TaxNextQuery(query=next(next_queries), reason="test")

    result = asyncio.run(
        build_graph(
            _router_llm(),
            tax_search=search,  # type: ignore[arg-type]
            rerank=_identity_rerank,
            tax_evidence_evaluator=evaluate,  # type: ignore[arg-type]
            tax_next_query_generator=next_query,  # type: ignore[arg-type]
            settings=Settings(_env_file=None, tax_max_hops=2),
        ).ainvoke({"query": "세금 첫 검색"})
    )

    assert result["hop_count"] == 2
    assert result["termination_reason"] == "max_hops"
    assert result["evidence_sufficient"] is False
    assert result["answer_status"] == "insufficient_evidence"


def test_missing_user_context_stops_retrieval() -> None:
    async def evaluate(_state: object) -> TaxEvidenceDecision:
        return _decision(
            sufficient=True,
            missing_user_context=["창업일"],
        )

    result = asyncio.run(
        build_graph(
            _router_llm(),
            tax_search=SequentialTaxSearch(
                [[_tax_document("tax-1", "법령 근거 충분")]]
            ),  # type: ignore[arg-type]
            rerank=_identity_rerank,
            tax_evidence_evaluator=evaluate,  # type: ignore[arg-type]
        ).ainvoke({"query": "내가 감면 대상이야?"})
    )

    assert result["hop_count"] == 1
    assert result["termination_reason"] == "missing_user_context"
    assert "창업일" in result["answer"]


def test_missing_calculation_input_requests_user_value() -> None:
    async def evaluate(_state: object) -> TaxEvidenceDecision:
        return _decision(sufficient=True, calculation_required=True)

    async def plan(_state: object) -> TaxCalculationPlan:
        return TaxCalculationPlan(
            calculation_type="reduction_amount",
            base_amount=None,
            rate_percent="75",
            missing_inputs=["산출세액"],
            cited_source_numbers=[1],
            reason="산출세액 필요",
        )

    result = asyncio.run(
        build_graph(
            _router_llm(),
            tax_search=SequentialTaxSearch(
                [[_tax_document("tax-1", "계산에 필요한 법령 근거")]]
            ),  # type: ignore[arg-type]
            rerank=_identity_rerank,
            tax_evidence_evaluator=evaluate,  # type: ignore[arg-type]
            tax_calculation_planner=plan,  # type: ignore[arg-type]
        ).ainvoke({"query": "예상 세금은 얼마야?"})
    )

    assert result["calculation_result"] is None
    assert result["termination_reason"] == "missing_calculation_input"
    assert result["answer_status"] == "need_more_info"
    assert "산출세액" in result["answer"]


def test_evidence_based_decimal_calculation_reaches_unified_answer() -> None:
    async def evaluate(_state: object) -> TaxEvidenceDecision:
        return _decision(sufficient=True, calculation_required=True)

    async def plan(_state: object) -> TaxCalculationPlan:
        return TaxCalculationPlan(
            calculation_type="reduction_amount",
            base_amount="1000000",
            rate_percent="75",
            cited_source_numbers=[1],
            reason="법령 감면율 적용",
        )

    result = asyncio.run(
        build_graph(
            _router_llm(),
            tax_search=SequentialTaxSearch(
                [[_tax_document("tax-1", "산출세액의 100분의 75 감면")]]
            ),  # type: ignore[arg-type]
            rerank=_identity_rerank,
            tax_evidence_evaluator=evaluate,  # type: ignore[arg-type]
            tax_calculation_planner=plan,  # type: ignore[arg-type]
        ).ainvoke({"query": "예상 세금은 얼마야?"})
    )

    assert result["calculation_result"] == {
        "calculation_type": "reduction_amount",
        "base_amount": "1000000",
        "rate_percent": "75",
        "reduction_amount": "750000",
        "formula": "base_amount × rate_percent ÷ 100",
        "cited_source_numbers": [1],
    }
    assert result["termination_reason"] == "calculation_complete"
    assert result["answer_status"] == "success"
    assert result["normalized_ratios"][0]["percent"] == 75
    assert result["normalized_ratios"][0]["decimal"] == 0.75
    assert result["reranked_docs"][0]["content"] == "산출세액의 100분의 75 감면"


def test_tax_cohere_failure_falls_back_to_rrf() -> None:
    async def evaluate(_state: object) -> TaxEvidenceDecision:
        return _decision(sufficient=True)

    def failing_rerank(
        _query: str,
        _documents: list[VectorSearchResult],
        _top_n: int,
    ) -> list[VectorSearchResult]:
        from src.rag.reranker import CohereRerankError

        raise CohereRerankError("temporary error")

    result = asyncio.run(
        build_graph(
            _router_llm(),
            tax_search=SequentialTaxSearch(
                [[_tax_document("tax-1", "충분한 세법 근거")]]
            ),  # type: ignore[arg-type]
            rerank=failing_rerank,
            tax_evidence_evaluator=evaluate,  # type: ignore[arg-type]
        ).ainvoke({"query": "세액감면이 뭐야?"})
    )

    assert result["reranked_docs"][0]["chunk_id"] == "tax-1"
    assert result["answer_status"] == "success"


def test_tax_no_result_reaches_unified_answer() -> None:
    result = asyncio.run(
        build_graph(
            _router_llm(),
            tax_search=SequentialTaxSearch([[]]),  # type: ignore[arg-type]
            rerank=_identity_rerank,
        ).ainvoke({"query": "찾을 수 없는 세법 질문"})
    )

    assert result["reranked_docs"] == []
    assert result["evidence_sufficient"] is False
    assert result["answer_status"] == "no_result"


def test_next_query_failure_goes_to_answer_without_calculation() -> None:
    calculation_calls = 0

    async def evaluate(_state: object) -> TaxEvidenceDecision:
        return _decision(sufficient=False, missing_information=["추가 법령"])

    async def failing_next_query(_state: object) -> TaxNextQuery:
        raise RuntimeError("generation failed")

    async def calculation_plan(_state: object) -> TaxCalculationPlan:
        nonlocal calculation_calls
        calculation_calls += 1
        raise AssertionError("calculation must not run")

    result = asyncio.run(
        build_graph(
            _router_llm(),
            tax_search=SequentialTaxSearch(
                [[_tax_document("tax-1", "추가 근거가 필요하다")]]
            ),  # type: ignore[arg-type]
            rerank=_identity_rerank,
            tax_evidence_evaluator=evaluate,  # type: ignore[arg-type]
            tax_next_query_generator=failing_next_query,  # type: ignore[arg-type]
            tax_calculation_planner=calculation_plan,  # type: ignore[arg-type]
        ).ainvoke({"query": "세액감면 조건 알려줘"})
    )

    assert calculation_calls == 0
    assert result["termination_reason"] == "next_query_error"
    assert result["answer_status"] == "error"


def test_tax_decisions_use_structured_output() -> None:
    model = FakeStructuredChatModel(
        {
            TaxEvidenceDecision: {
                "sufficient": False,
                "missing_information": ["업종 요건"],
                "missing_user_context": [],
                "calculation_required": False,
                "reason": "추가 법령 필요",
            },
            TaxNextQuery: {
                "query": "조세특례제한법 음식점업 요건",
                "target_law": "조세특례제한법",
                "target_article": None,
                "reason": "업종 요건 검색",
            },
        }
    )
    documents = [_tax_document("tax-1", "감면 대상 업종 확인 필요")]

    evidence = asyncio.run(
        evaluate_tax_evidence(
            model,  # type: ignore[arg-type]
            query="음식점 창업 감면 대상이야?",
            documents=documents,
            user_context=None,
        )
    )
    next_query = asyncio.run(
        generate_tax_next_query(
            model,  # type: ignore[arg-type]
            query="음식점 창업 감면 대상이야?",
            documents=documents,
            missing_information=evidence.missing_information,
            user_context=None,
            search_history=["음식점 창업 감면 대상이야?"],
        )
    )

    assert evidence.missing_information == ["업종 요건"]
    assert next_query.query == "조세특례제한법 음식점업 요건"


def test_calculate_tax_plan_supports_half_percent_from_evidence() -> None:
    documents = [_tax_document("tax-1", "가산 비율은 1000분의 5(0.5%)이다.")]
    plan = TaxCalculationPlan(
        calculation_type="percentage_of_amount",
        base_amount="200000",
        rate_percent="0.5",
        cited_source_numbers=[1],
        reason="법령 비율 적용",
    )

    result = calculate_tax_plan(plan, documents=documents)

    assert result["calculated_amount"] == "1000"
    assert result["rate_percent"] == "0.5"


def test_calculate_tax_plan_rejects_rate_not_found_in_cited_source() -> None:
    documents = [_tax_document("tax-1", "법령상 비율은 100분의 15(15%)이다.")]
    plan = TaxCalculationPlan(
        calculation_type="reduction_amount",
        base_amount="100000",
        rate_percent="75",
        cited_source_numbers=[1],
        reason="잘못된 비율",
    )

    with pytest.raises(TaxCalculationError, match="not present"):
        calculate_tax_plan(plan, documents=documents)


def test_calculate_tax_plan_rejects_invented_source_number() -> None:
    plan = TaxCalculationPlan(
        calculation_type="reduction_amount",
        base_amount="100000",
        rate_percent="15",
        cited_source_numbers=[2],
        reason="잘못된 출처",
    )

    with pytest.raises(TaxCalculationError, match="source number"):
        calculate_tax_plan(
            plan,
            documents=[_tax_document("tax-1", "100분의 15(15%)")],
        )


def test_tax_calculation_plan_uses_structured_output() -> None:
    model = FakeStructuredChatModel(
        {
            TaxCalculationPlan: {
                "calculation_type": "amount_after_reduction",
                "base_amount": "1000000",
                "rate_percent": "75",
                "missing_inputs": [],
                "cited_source_numbers": [1],
                "reason": "법령 감면율",
            }
        }
    )

    plan = asyncio.run(
        generate_tax_calculation_plan(
            model,  # type: ignore[arg-type]
            query="산출세액 100만원의 감면 후 금액",
            documents=[_tax_document("tax-1", "100분의 75 감면")],
            user_context=None,
        )
    )

    assert plan.base_amount == "1000000"
    assert plan.rate_percent == "75"
    assert "100분의 75(75%)" in model.last_prompt_text
