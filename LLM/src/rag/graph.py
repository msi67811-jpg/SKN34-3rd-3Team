"""정책 검색·공고 조회·향후 세금 흐름을 연결하는 LangGraph."""

import asyncio
from collections.abc import Awaitable, Callable
from functools import partial
import logging
from typing import Literal, NotRequired, Required, TypedDict

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel, ConfigDict, Field

from src.core.config import Settings, get_settings
from src.data.contracts import UserProfile, VectorSearchResult
from src.models import get_llm
from src.rag.answer import (
    AnswerStatus,
    UnifiedAnswerResult,
    fallback_answer,
    generate_unified_answer,
)
from src.rag.contracts import EligibilityDecision
from src.rag.discovery import build_personalized_query
from src.rag.reranker import CohereRerankError, rerank_documents
from src.rag.tax import (
    TaxEvidenceDecision,
    TaxNextQuery,
    evaluate_tax_evidence,
    generate_tax_next_query,
    merge_evidence,
    resolve_legal_reference,
)
from src.vectorstores.hybrid import HybridSearch


Route = Literal["policy", "notice", "tax"]
logger = logging.getLogger(__name__)


class RouteDecision(BaseModel):
    """질문 유형과 사용자 Context 필요 여부를 담는 Router 구조화 출력."""

    model_config = ConfigDict(extra="forbid")

    route: Route = Field(description="질문의 처리 경로")
    personalized: bool = Field(
        description="개인정보나 사업정보가 있어야 답변 가능한 질문인지 여부"
    )


class GraphState(TypedDict):
    """LangGraph 전체 단계에서 공유할 최소 상태."""

    query: Required[str]
    policy_id: NotRequired[int | None]
    top_k: NotRequired[int | None]
    decision: NotRequired[EligibilityDecision | None]
    route: NotRequired[Route | None]
    personalized: NotRequired[bool]
    user_context: NotRequired[UserProfile | None]
    search_query: NotRequired[str | None]
    retrieved_docs: NotRequired[list[VectorSearchResult]]
    reranked_docs: NotRequired[list[VectorSearchResult]]
    hop_count: NotRequired[int]
    search_history: NotRequired[list[str]]
    evidence_sufficient: NotRequired[bool | None]
    notice_results: NotRequired[list[dict[str, object]]]
    notice_backend_available: NotRequired[bool]
    calculation_result: NotRequired[dict[str, object] | None]
    calculation_required: NotRequired[bool]
    calculator_unavailable: NotRequired[bool]
    missing_information: NotRequired[list[str]]
    missing_user_context: NotRequired[list[str]]
    last_retrieval_count: NotRequired[int]
    termination_reason: NotRequired[str | None]
    answer_status: NotRequired[AnswerStatus | None]
    cited_source_numbers: NotRequired[list[int]]
    answer_sources: NotRequired[list[dict[str, object]]]
    answer: NotRequired[str | None]


NoticeSearch = Callable[[GraphState], list[dict[str, object]]]
Rerank = Callable[
    [str, list[VectorSearchResult], int],
    list[VectorSearchResult],
]
TaxEvidenceEvaluator = Callable[[GraphState], Awaitable[TaxEvidenceDecision]]
TaxNextQueryGenerator = Callable[[GraphState], Awaitable[TaxNextQuery]]
TaxCalculator = Callable[[GraphState], dict[str, object]]


ROUTER_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "질문을 policy, notice, tax 중 하나로 분류하세요. "
            "policy는 지원제도·정책 문서 질문, notice는 현재 신청 가능하거나 "
            "모집 중인 실제 공고 조회 질문, tax는 세금·세법·세액감면 질문입니다. "
            "사용자 개인정보나 사업정보가 필요한 판정 질문이면 personalized를 "
            "true로 반환하세요.",
        ),
        ("human", "{query}"),
    ]
)


def initialize_state(state: GraphState) -> dict[str, object]:
    """선택 상태값을 향후 node가 안전하게 사용할 기본값으로 초기화한다."""
    return {
        "route": None,
        "personalized": False,
        "user_context": state.get("user_context"),
        "search_query": None,
        "retrieved_docs": [],
        "reranked_docs": [],
        "hop_count": 0,
        "search_history": [],
        "evidence_sufficient": None,
        "notice_results": [],
        "notice_backend_available": False,
        "calculation_result": None,
        "calculation_required": False,
        "calculator_unavailable": False,
        "missing_information": [],
        "missing_user_context": [],
        "last_retrieval_count": 0,
        "termination_reason": None,
        "answer_status": None,
        "cited_source_numbers": [],
        "answer_sources": [],
        "answer": None,
    }


async def route_question(
    state: GraphState,
    *,
    llm: BaseChatModel,
) -> dict[str, object]:
    """기존 LangChain Structured Output 방식으로 질문 경로를 결정한다."""
    router_chain = ROUTER_PROMPT | llm.with_structured_output(RouteDecision)
    decision = RouteDecision.model_validate(
        await router_chain.ainvoke(
            {"query": state["query"]},
            config={"run_name": "langgraph_question_router"},
        )
    )
    logger.info(
        "Graph route=%s personalized=%s",
        decision.route,
        decision.personalized,
    )
    return {
        "route": decision.route,
        "personalized": decision.personalized,
    }


def _select_route(state: GraphState) -> Route:
    """Router 결과를 conditional edge의 branch 이름으로 반환한다."""
    route = state.get("route")
    if route is None:
        raise ValueError("Router did not set a route")
    return route


def build_graph(
    llm: BaseChatModel | None = None,
    *,
    policy_search: HybridSearch | None = None,
    tax_search: HybridSearch | None = None,
    notice_search: NoticeSearch | None = None,
    rerank: Rerank | None = None,
    tax_evidence_evaluator: TaxEvidenceEvaluator | None = None,
    tax_next_query_generator: TaxNextQueryGenerator | None = None,
    tax_calculator: TaxCalculator | None = None,
    settings: Settings | None = None,
) -> CompiledStateGraph:
    """Structured Router와 Policy·Notice·Tax branch를 조립한다."""
    router_llm = llm or get_llm()
    settings_config = settings or get_settings()

    def configured_rerank(
        query: str,
        documents: list[VectorSearchResult],
        top_n: int,
    ) -> list[VectorSearchResult]:
        return rerank_documents(
            query,
            documents,
            top_n=top_n,
            settings=settings_config,
        )

    rerank_function = rerank or configured_rerank
    tax_retriever = tax_search or policy_search

    async def configured_evidence_evaluator(
        state: GraphState,
    ) -> TaxEvidenceDecision:
        return await evaluate_tax_evidence(
            router_llm,
            query=state["query"],
            documents=state.get("reranked_docs", []),
            user_context=state.get("user_context"),
        )

    async def configured_next_query_generator(state: GraphState) -> TaxNextQuery:
        return await generate_tax_next_query(
            router_llm,
            query=state["query"],
            documents=state.get("reranked_docs", []),
            missing_information=state.get("missing_information", []),
            user_context=state.get("user_context"),
            search_history=state.get("search_history", []),
        )

    evidence_evaluator = tax_evidence_evaluator or configured_evidence_evaluator
    next_query_generator = tax_next_query_generator or configured_next_query_generator

    async def router_node(state: GraphState) -> dict[str, object]:
        return await route_question(state, llm=router_llm)

    async def policy_node(state: GraphState) -> dict[str, object]:
        """기존 HybridSearch를 실행하고 RRF 후보를 Cohere로 재정렬한다."""
        if policy_search is None:
            logger.info("Policy retrieval unavailable")
            return {"termination_reason": "policy_retriever_unavailable"}
        search_query = state["query"]
        if state.get("personalized") and state.get("user_context") is not None:
            search_query = build_personalized_query(
                state["query"], state["user_context"]
            )
        try:
            dense_docs, bm25_docs, retrieved_docs = await asyncio.to_thread(
                partial(
                    policy_search.search_stages,
                    search_query,
                    policy_id=state.get("policy_id"),
                    top_k=settings_config.cohere_rerank_candidate_k,
                )
            )
        except Exception:
            logger.exception("Policy hybrid retrieval failed")
            return {
                "search_query": search_query,
                "termination_reason": "retrieval_error",
            }
        retrieved_docs = [
            document
            for document in retrieved_docs
            if document["policy_id"] is not None
        ]
        if not retrieved_docs:
            return {
                "search_query": search_query,
                "retrieved_docs": [],
                "reranked_docs": [],
                "termination_reason": "no_result",
            }
        try:
            reranked_docs = await asyncio.to_thread(
                rerank_function,
                search_query,
                retrieved_docs,
                state.get("top_k") or settings_config.default_top_k,
            )
        except CohereRerankError:
            logger.warning("Cohere rerank failed; using RRF results", exc_info=True)
            reranked_docs = retrieved_docs[: settings_config.default_top_k]
        logger.info(
            "Policy route counts: dense=%d bm25=%d rrf=%d rerank=%d",
            len(dense_docs),
            len(bm25_docs),
            len(retrieved_docs),
            len(reranked_docs),
        )
        return {
            "search_query": search_query,
            "retrieved_docs": retrieved_docs,
            "reranked_docs": reranked_docs,
            "termination_reason": "policy_evidence_ready",
        }

    async def notice_node(state: GraphState) -> dict[str, object]:
        """실제 Backend Notice interface가 주입되면 조회 결과만 저장한다."""
        if notice_search is None:
            logger.info("Notice backend available=false")
            return {
                "notice_results": [],
                "notice_backend_available": False,
                "termination_reason": "notice_integration_unavailable",
            }
        try:
            notice_results = await asyncio.to_thread(notice_search, state)
        except Exception:
            logger.exception("Backend notice search failed")
            return {
                "notice_results": [],
                "notice_backend_available": True,
                "termination_reason": "notice_backend_error",
            }
        logger.info("Notice route count: results=%d", len(notice_results))
        return {
            "notice_results": notice_results,
            "notice_backend_available": True,
            "termination_reason": (
                "notice_results_ready" if notice_results else "no_result"
            ),
        }

    async def tax_retrieval_node(state: GraphState) -> dict[str, object]:
        """현재 Hop Query로 Tax Hybrid Retrieval과 Cohere Rerank를 실행한다."""
        search_query = state.get("search_query") or state["query"]
        search_history = state.get("search_history", [])
        if search_query.casefold().strip() in {
            query.casefold().strip() for query in search_history
        }:
            return {
                "evidence_sufficient": False,
                "termination_reason": "duplicate_query",
            }
        if state.get("hop_count", 0) >= settings_config.tax_max_hops:
            return {
                "evidence_sufficient": False,
                "termination_reason": "max_hops",
            }
        if tax_retriever is None:
            return {
                "evidence_sufficient": False,
                "termination_reason": "tax_retriever_unavailable",
            }
        try:
            dense_docs, bm25_docs, rrf_docs = await asyncio.to_thread(
                partial(
                    tax_retriever.search_stages,
                    search_query,
                    policy_id=None,
                    top_k=settings_config.cohere_rerank_candidate_k,
                )
            )
            tax_rrf_docs = [
                document for document in rrf_docs if document["policy_id"] is None
            ]
            if tax_rrf_docs:
                try:
                    hop_docs = await asyncio.to_thread(
                        rerank_function,
                        search_query,
                        tax_rrf_docs,
                        state.get("top_k") or settings_config.default_top_k,
                    )
                except CohereRerankError:
                    logger.warning(
                        "Tax Cohere rerank failed; using RRF results",
                        exc_info=True,
                    )
                    hop_docs = tax_rrf_docs[: settings_config.default_top_k]
            else:
                hop_docs = []
        except Exception:
            logger.exception("Tax hybrid retrieval failed")
            return {
                "search_query": search_query,
                "evidence_sufficient": False,
                "termination_reason": "retrieval_error",
            }

        previous_rrf = state.get("retrieved_docs", [])
        previous_evidence = state.get("reranked_docs", [])
        accumulated_rrf = merge_evidence(previous_rrf, tax_rrf_docs)
        accumulated_evidence = merge_evidence(previous_evidence, hop_docs)
        new_evidence_count = len(accumulated_evidence) - len(previous_evidence)
        logger.info(
            "Tax hop=%d query=%r counts: dense=%d bm25=%d rrf=%d rerank=%d new=%d",
            state.get("hop_count", 0) + 1,
            search_query,
            len(dense_docs),
            len(bm25_docs),
            len(tax_rrf_docs),
            len(hop_docs),
            new_evidence_count,
        )
        return {
            "search_query": search_query,
            "search_history": [*search_history, search_query],
            "hop_count": state.get("hop_count", 0) + 1,
            "retrieved_docs": accumulated_rrf,
            "reranked_docs": accumulated_evidence,
            "last_retrieval_count": new_evidence_count,
            "termination_reason": None,
        }

    async def tax_evidence_node(state: GraphState) -> dict[str, object]:
        """누적 Tax 근거의 충분성, 사용자 정보와 계산 필요성을 판단한다."""
        if state.get("termination_reason") is not None:
            return {}
        if state.get("last_retrieval_count", 0) == 0:
            return {
                "evidence_sufficient": False,
                "missing_information": ["새로운 법령 근거"],
                "termination_reason": "no_new_evidence",
            }
        try:
            decision = await evidence_evaluator(state)
        except Exception:
            logger.exception("Tax evidence evaluation failed")
            return {
                "evidence_sufficient": False,
                "termination_reason": "evidence_error",
            }

        termination_reason = None
        if decision.missing_user_context:
            termination_reason = "missing_user_context"
        elif decision.sufficient:
            termination_reason = "evidence_sufficient"
        elif state.get("hop_count", 0) >= settings_config.tax_max_hops:
            termination_reason = "max_hops"
        logger.info(
            "Tax evidence: hop=%d sufficient=%s missing_information=%s "
            "missing_user_context=%s calculation_required=%s termination_reason=%s",
            state.get("hop_count", 0),
            decision.sufficient,
            decision.missing_information,
            decision.missing_user_context,
            decision.calculation_required,
            termination_reason,
        )
        return {
            "evidence_sufficient": decision.sufficient,
            "missing_information": decision.missing_information,
            "missing_user_context": decision.missing_user_context,
            "calculation_required": decision.calculation_required,
            "termination_reason": termination_reason,
        }

    async def tax_next_query_node(state: GraphState) -> dict[str, object]:
        """명시적 법령 참조를 우선하고 필요할 때만 LLM Query를 생성한다."""
        next_query = resolve_legal_reference(
            state.get("reranked_docs", []),
            search_history=state.get("search_history", []),
        )
        if next_query is None:
            try:
                generated = await next_query_generator(state)
                next_query = generated.query
            except Exception:
                logger.exception("Tax next query generation failed")
                return {"termination_reason": "next_query_error"}
        if next_query is None or not next_query.strip():
            return {"termination_reason": "no_next_query"}
        if next_query.casefold().strip() in {
            query.casefold().strip()
            for query in state.get("search_history", [])
        }:
            return {"termination_reason": "duplicate_query"}
        return {"search_query": next_query.strip(), "termination_reason": None}

    async def tax_calculation_node(state: GraphState) -> dict[str, object]:
        """필요할 때만 Backend Calculator boundary를 호출하고 종료 상태를 만든다."""
        if state.get("calculation_required"):
            if tax_calculator is None:
                logger.info("Tax calculator available=false")
                return {
                    "calculator_unavailable": True,
                    "termination_reason": "calculator_unavailable",
                }
            try:
                logger.info("Tax calculator available=true")
                calculation_result = await asyncio.to_thread(tax_calculator, state)
            except Exception:
                logger.exception("Backend tax calculator failed")
                return {
                    "calculator_unavailable": True,
                    "termination_reason": "calculator_error",
                }
            return {
                "calculation_result": calculation_result,
                "termination_reason": "calculation_complete",
            }
        return {}

    async def answer_node(state: GraphState) -> dict[str, object]:
        """각 branch 결과만 사용해 공통 Structured Answer를 생성한다."""
        route = state.get("route")
        if route is None:
            result = fallback_answer("error")
            return _answer_update(result, [])

        status = _answer_status(state)
        sources = _answer_source_records(state)
        if status != "success":
            result = fallback_answer(
                status,
                missing_user_context=state.get("missing_user_context"),
            )
            logger.info(
                "Graph final status=%s termination_reason=%s",
                status,
                state.get("termination_reason"),
            )
            return _answer_update(result, [])

        try:
            result = await generate_unified_answer(
                router_llm,
                query=state["query"],
                route=route,
                personalized=state.get("personalized", False),
                user_context=(
                    state.get("user_context")
                    if state.get("personalized")
                    else None
                ),
                route_context=_answer_context(state),
                status=status,
                source_count=len(sources),
            )
            cited_sources = [
                sources[source_number - 1]
                for source_number in result.cited_source_numbers
            ]
        except Exception:
            logger.exception("Unified answer generation failed")
            result = fallback_answer("error")
            cited_sources = []
        logger.info(
            "Graph final status=%s sources=%d termination_reason=%s",
            result.status,
            len(cited_sources),
            state.get("termination_reason"),
        )
        return _answer_update(result, cited_sources)

    def route_after_tax_evidence(state: GraphState) -> Literal["continue", "finish"]:
        return "finish" if state.get("termination_reason") else "continue"

    def route_after_tax_next_query(state: GraphState) -> Literal["retry", "finish"]:
        return "finish" if state.get("termination_reason") else "retry"

    graph = StateGraph(GraphState)
    graph.add_node("initialize", initialize_state)
    graph.add_node("router", router_node)
    graph.add_node("policy_node", policy_node)
    graph.add_node("notice_node", notice_node)
    graph.add_node("tax_retrieval", tax_retrieval_node)
    graph.add_node("tax_evidence", tax_evidence_node)
    graph.add_node("tax_next_query", tax_next_query_node)
    graph.add_node("tax_calculation", tax_calculation_node)
    graph.add_node("answer", answer_node)

    graph.add_edge(START, "initialize")
    graph.add_edge("initialize", "router")
    graph.add_conditional_edges(
        "router",
        _select_route,
        {
            "policy": "policy_node",
            "notice": "notice_node",
            "tax": "tax_retrieval",
        },
    )
    graph.add_edge("policy_node", "answer")
    graph.add_edge("notice_node", "answer")
    graph.add_edge("tax_retrieval", "tax_evidence")
    graph.add_conditional_edges(
        "tax_evidence",
        route_after_tax_evidence,
        {"continue": "tax_next_query", "finish": "tax_calculation"},
    )
    graph.add_conditional_edges(
        "tax_next_query",
        route_after_tax_next_query,
        {"retry": "tax_retrieval", "finish": "tax_calculation"},
    )
    graph.add_edge("tax_calculation", "answer")
    graph.add_edge("answer", END)
    return graph.compile()


def _answer_status(state: GraphState) -> AnswerStatus:
    """branch 종료 상태를 최종 사용자 응답 상태로 변환한다."""
    reason = state.get("termination_reason")
    route = state.get("route")
    if reason in {
        "policy_retriever_unavailable",
        "notice_integration_unavailable",
        "tax_retriever_unavailable",
        "calculator_unavailable",
    }:
        return "integration_unavailable"
    if reason == "missing_user_context":
        return "need_more_info"
    if reason == "no_result":
        return "no_result"
    if reason in {
        "retrieval_error",
        "notice_backend_error",
        "evidence_error",
        "next_query_error",
        "calculator_error",
    }:
        return "error"
    if route == "tax" and not state.get("reranked_docs"):
        return "no_result"
    if route == "tax" and not state.get("evidence_sufficient"):
        return "insufficient_evidence"
    if route == "policy" and not state.get("reranked_docs"):
        return "no_result"
    if route == "notice" and not state.get("notice_results"):
        return "no_result"
    return "success"


def _answer_source_records(state: GraphState) -> list[dict[str, object]]:
    """route 결과의 실제 source를 안정적 ID 기준으로 중복 제거한다."""
    records: list[dict[str, object]] = (
        list(state.get("notice_results", []))
        if state.get("route") == "notice"
        else [dict(document) for document in state.get("reranked_docs", [])]
    )
    unique_records: list[dict[str, object]] = []
    seen_keys: set[tuple[str, object]] = set()
    for index, record in enumerate(records):
        key_name = next(
            (
                name
                for name in ("chunk_id", "id", "notice_id")
                if record.get(name) is not None
            ),
            None,
        )
        key = (key_name or "position", record.get(key_name) if key_name else index)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        unique_records.append(record)
    return unique_records


def _answer_context(state: GraphState) -> dict[str, object]:
    """현재 route에 필요한 Context만 Unified Answer에 전달한다."""
    route = state.get("route")
    if route == "policy":
        decision = state.get("decision")
        return {
            "documents": _answer_source_records(state),
            "backend_decision": (
                {
                    "eligible": decision.eligible,
                    "reasons": list(decision.reasons),
                }
                if decision is not None
                else None
            ),
        }
    if route == "notice":
        return {
            "notices": _answer_source_records(state),
            "backend_available": state.get("notice_backend_available", False),
        }
    return {
        "evidence": _answer_source_records(state),
        "evidence_sufficient": state.get("evidence_sufficient"),
        "missing_information": state.get("missing_information", []),
        "missing_user_context": state.get("missing_user_context", []),
        "hop_count": state.get("hop_count", 0),
        "termination_reason": state.get("termination_reason"),
        "calculation_required": state.get("calculation_required", False),
        "calculation_result": state.get("calculation_result"),
        "calculator_available": not state.get("calculator_unavailable", False),
    }


def _answer_update(
    result: UnifiedAnswerResult,
    sources: list[dict[str, object]],
) -> dict[str, object]:
    """검증된 최종 응답을 GraphState update로 변환한다."""
    return {
        "answer": result.answer,
        "answer_status": result.status,
        "cited_source_numbers": result.cited_source_numbers,
        "answer_sources": sources,
    }
