import asyncio
from typing import Any

import pytest

from src.core.config import Settings
from src.data.contracts import RagChunk, VectorSearchResult
from src.rag.graph import GraphState, RouteDecision, build_graph
from src.rag.reranker import CohereRerankError
from src.rag.answer import UnifiedAnswerResult
from src.rag.tax import TaxEvidenceDecision, TaxNextQuery
from src.vectorstores.hybrid import HybridSearch
from tests.fakes import FakeStructuredChatModel


CHUNKS: list[RagChunk] = [
    {
        "chunk_id": "policy-1-chunk-1",
        "policy_id": 1,
        "title": "예비창업 지원",
        "source": "db://policies/1",
        "page": 1,
        "content": "예비창업자의 사업화 자금과 창업 교육을 지원합니다.",
    },
    {
        "chunk_id": "policy-2-chunk-1",
        "policy_id": 2,
        "title": "청년 사업 지원",
        "source": "db://policies/2",
        "page": 1,
        "content": "청년 사업자를 위한 정책 자금 지원 조건입니다.",
    },
]


class TrackingDenseSearch:
    def __init__(self) -> None:
        self.call_count = 0

    def add_chunks(self, chunks: list[RagChunk]) -> list[str]:
        return [chunk["chunk_id"] for chunk in chunks]

    def search(
        self,
        _query: str,
        *,
        policy_id: int | None = None,
        top_k: int = 5,
    ) -> list[VectorSearchResult]:
        self.call_count += 1
        return [
            {**chunk, "score": 0.9 - index * 0.1}
            for index, chunk in enumerate(CHUNKS)
            if policy_id is None or chunk["policy_id"] == policy_id
        ][:top_k]

    def get_chunks(self) -> list[RagChunk]:
        return list(CHUNKS)


class EmptyHybridSearch:
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
        return [], [], []


def _router_llm(route: str, *, personalized: bool = False) -> Any:
    return FakeStructuredChatModel(
        {
            RouteDecision: {
                "route": route,
                "personalized": personalized,
            },
            UnifiedAnswerResult: {
                "answer": "확인된 문서 기반 답변",
                "status": "success",
                "cited_source_numbers": [1],
            },
        }
    )


def _hybrid_search(dense: TrackingDenseSearch) -> HybridSearch:
    return HybridSearch(
        dense_search=dense,
        chunks=CHUNKS,
        dense_candidate_k=3,
        bm25_candidate_k=3,
        rrf_k=60,
    )


@pytest.mark.parametrize(
    ("query", "route", "personalized"),
    [
        ("청년 창업 지원 정책에는 어떤 게 있어?", "policy", False),
        ("지금 신청 가능한 청년 창업 지원사업 있어?", "notice", False),
        ("청년창업 세액감면이 뭐야?", "tax", False),
        ("내가 청년창업 세액감면 받을 수 있어?", "tax", True),
    ],
)
def test_router_uses_structured_output(
    query: str,
    route: str,
    personalized: bool,
) -> None:
    result = asyncio.run(
        build_graph(_router_llm(route, personalized=personalized)).ainvoke(
            {"query": query}
        )
    )

    assert result["route"] == route
    assert result["personalized"] is personalized


@pytest.mark.parametrize(
    "query",
    [
        "청년 창업 지원 정책에는 어떤 게 있어?",
        "예비창업자가 받을 수 있는 지원 정책 조건 알려줘.",
    ],
)
def test_policy_route_runs_hybrid_and_rerank(query: str) -> None:
    dense = TrackingDenseSearch()
    rerank_calls: list[list[str]] = []

    def fake_rerank(
        _query: str,
        documents: list[VectorSearchResult],
        top_n: int,
    ) -> list[VectorSearchResult]:
        rerank_calls.append([document["chunk_id"] for document in documents])
        return list(reversed(documents))[:top_n]

    result = asyncio.run(
        build_graph(
            _router_llm("policy"),
            policy_search=_hybrid_search(dense),
            rerank=fake_rerank,
            settings=Settings(
                _env_file=None,
                default_top_k=2,
                cohere_rerank_candidate_k=3,
            ),
        ).ainvoke({"query": query})
    )

    assert dense.call_count == 1
    assert result["retrieved_docs"]
    assert result["reranked_docs"]
    assert rerank_calls
    assert result["reranked_docs"][0]["chunk_id"] == rerank_calls[0][-1]
    assert result["reranked_docs"][0]["source"]
    assert result["answer"] == "확인된 문서 기반 답변"
    assert result["answer_status"] == "success"
    assert result["answer_sources"]


@pytest.mark.parametrize(
    "query",
    [
        "지금 신청 가능한 청년 창업 지원사업 있어?",
        "서울에서 지금 모집 중인 창업 지원사업 알려줘.",
    ],
)
def test_notice_route_uses_only_injected_backend_interface(query: str) -> None:
    dense = TrackingDenseSearch()
    received_queries: list[str] = []

    def fake_notice_search(state: GraphState) -> list[dict[str, object]]:
        received_queries.append(state["query"])
        return [{"id": 7, "title": "현재 모집 공고"}]

    result = asyncio.run(
        build_graph(
            _router_llm("notice"),
            policy_search=_hybrid_search(dense),
            notice_search=fake_notice_search,
        ).ainvoke({"query": query})
    )

    assert dense.call_count == 0
    assert received_queries == [query]
    assert result["notice_results"] == [{"id": 7, "title": "현재 모집 공고"}]
    assert result["retrieved_docs"] == []
    assert result["answer_status"] == "success"


def test_tax_route_reports_unavailable_retriever() -> None:
    result = asyncio.run(
        build_graph(_router_llm("tax")).ainvoke(
            {"query": "청년창업 세액감면이 뭐야?"}
        )
    )

    assert result["termination_reason"] == "tax_retriever_unavailable"
    assert result["evidence_sufficient"] is False
    assert result["retrieved_docs"] == []


def test_policy_route_falls_back_to_rrf_when_cohere_fails() -> None:
    def failing_rerank(
        _query: str,
        _documents: list[VectorSearchResult],
        _top_n: int,
    ) -> list[VectorSearchResult]:
        raise CohereRerankError("temporary failure")

    result = asyncio.run(
        build_graph(
            _router_llm("policy"),
            policy_search=_hybrid_search(TrackingDenseSearch()),
            rerank=failing_rerank,
            settings=Settings(_env_file=None, default_top_k=1),
        ).ainvoke({"query": "청년 정책"})
    )

    assert result["retrieved_docs"]
    assert result["reranked_docs"] == result["retrieved_docs"][:1]


def test_notice_without_backend_returns_integration_unavailable() -> None:
    result = asyncio.run(
        build_graph(_router_llm("notice")).ainvoke(
            {"query": "서울에서 현재 모집 중인 사업 알려줘"}
        )
    )

    assert result["notice_results"] == []
    assert result["answer_status"] == "integration_unavailable"
    assert result["answer_sources"] == []


def test_policy_no_result_reaches_unified_answer_without_inventing_policy() -> None:
    result = asyncio.run(
        build_graph(
            _router_llm("policy"),
            policy_search=EmptyHybridSearch(),  # type: ignore[arg-type]
        ).ainvoke({"query": "존재하지 않는 정책"})
    )

    assert result["reranked_docs"] == []
    assert result["answer_sources"] == []
    assert result["answer_status"] == "no_result"


def test_policy_branch_does_not_call_notice_or_tax() -> None:
    notice_calls = 0

    def notice_search(_state: GraphState) -> list[dict[str, object]]:
        nonlocal notice_calls
        notice_calls += 1
        return []

    class TaxSearchThatMustNotRun:
        def search_stages(self, *_args: object, **_kwargs: object) -> object:
            raise AssertionError("Tax retrieval must not run")

    result = asyncio.run(
        build_graph(
            _router_llm("policy"),
            policy_search=_hybrid_search(TrackingDenseSearch()),
            tax_search=TaxSearchThatMustNotRun(),  # type: ignore[arg-type]
            notice_search=notice_search,
            rerank=lambda _query, documents, top_n: documents[:top_n],
        ).ainvoke({"query": "청년 창업 지원 정책 알려줘"})
    )

    assert notice_calls == 0
    assert result["answer_status"] == "success"


def test_notice_empty_result_is_no_result() -> None:
    result = asyncio.run(
        build_graph(
            _router_llm("notice"),
            notice_search=lambda _state: [],
        ).ainvoke({"query": "현재 모집 공고"})
    )

    assert result["notice_backend_available"] is True
    assert result["answer_status"] == "no_result"


def test_notice_backend_error_is_not_exposed() -> None:
    def failing_notice(_state: GraphState) -> list[dict[str, object]]:
        raise ConnectionError("sensitive backend detail")

    result = asyncio.run(
        build_graph(
            _router_llm("notice"),
            notice_search=failing_notice,
        ).ainvoke({"query": "현재 모집 공고"})
    )

    assert result["answer_status"] == "error"
    assert "sensitive" not in result["answer"]
