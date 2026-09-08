import asyncio
from collections.abc import Callable
from functools import partial
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel
from starlette.concurrency import run_in_threadpool

from src.core.config import Settings, get_settings
from src.core.database import DatabaseConfigurationError
from src.core.langsmith import LangSmithConfigurationError
from src.data import MockDataNotFoundError, get_document_catalog
from src.data.mock_repository import get_user_profile as get_mock_user_profile
from src.data.postgres_repository import (
    DatabaseDataNotFoundError,
    get_user_profile as get_database_user_profile,
)
from src.features.document_processing import PdfDocumentError
from src.features.indexing import (
    load_or_build_document_index,
    load_or_build_postgres_index,
)
from src.models import ModelConfigurationError, get_embedding_model, get_llm
from src.rag.contracts import EligibilityDecision, SourceCitation
from src.rag.discovery import PolicyDiscoveryService
from src.rag.graph import GraphState, build_graph
from src.rag.guardrails import RagInputError, validate_question, validate_top_k
from src.serving.schemas import (
    EligibilityDecisionRequest,
    IndexRequest,
    IndexResponse,
    MatchedPolicyResponse,
    PolicyRecommendationRequest,
    PolicyRecommendationResponse,
    RagAnswerRequest,
    RagAnswerResponse,
    ReadyResponse,
    SourceResponse,
)
from src.vectorstores.base import VectorSearch
from src.vectorstores.hybrid import HybridSearch


class RagIndexNotReadyError(RuntimeError):
    """프로세스 내부 RAG 인덱스 준비 전에 답변을 요청할 때 발생한다."""


class RagRuntime:
    """FastAPI 프로세스의 RAG 인덱스와 모델 생성 함수를 관리한다."""

    def __init__(
        self,
        *,
        embedding_factory: Callable[[], Embeddings] = get_embedding_model,
        llm_factory: Callable[[], BaseChatModel] = get_llm,
        notice_search: Callable[[GraphState], list[dict[str, object]]] | None = None,
        tax_calculator: Callable[[GraphState], dict[str, object]] | None = None,
    ) -> None:
        """모델 팩토리와 비어 있는 RAG 실행 상태를 초기화한다.

        Args:
            embedding_factory: 인덱싱 시 Embedding 모델을 생성할 함수.
            llm_factory: 근거가 확보된 답변 생성 시 채팅 모델을 생성할 함수.
        """
        self.embedding_factory = embedding_factory
        self.llm_factory = llm_factory
        self.notice_search = notice_search
        self.tax_calculator = tax_calculator
        self.index_lock = asyncio.Lock()
        self._vector_search: VectorSearch | None = None
        self.document_count = 0
        self.chunk_count = 0
        self.index_source: Literal["cache", "embedding"] | None = None

    @property
    def ready(self) -> bool:
        """프로세스 메모리에 검색 가능한 인덱스가 있으면 True를 반환한다."""
        return self._vector_search is not None

    def set_index(
        self,
        vector_search: VectorSearch,
        *,
        document_count: int,
        chunk_count: int,
        index_source: Literal["cache", "embedding"],
    ) -> None:
        """검색 인덱스와 문서 수를 현재 프로세스 상태로 저장한다.

        Args:
            vector_search: 검색 가능한 In-memory Vector Search 구현체.
            document_count: 인덱스에 반영된 원본 문서 개수.
            chunk_count: 인덱스에 저장된 RAG Chunk 개수.
            index_source: 로컬 캐시 또는 신규 Embedding 중 인덱스 생성 출처.
        """
        self._vector_search = vector_search
        self.document_count = document_count
        self.chunk_count = chunk_count
        self.index_source = index_source

    def require_index(self) -> VectorSearch:
        """준비된 Vector Search를 반환하고 없으면 명확한 예외를 발생시킨다.

        Returns:
            현재 FastAPI 프로세스에 적재된 VectorSearch 구현체.

        Raises:
            RagIndexNotReadyError: 인덱스를 아직 준비하지 않았을 때.
        """
        if self._vector_search is None:
            raise RagIndexNotReadyError(
                "RAG index is not ready. Call POST /internal/rag/index first."
            )
        return self._vector_search

    def require_hybrid_index(self, settings: Settings) -> HybridSearch:
        """준비된 Dense 인덱스를 기존 BM25·RRF 검색과 결합해 반환한다."""
        vector_search = self.require_index()
        if isinstance(vector_search, HybridSearch):
            return vector_search
        return HybridSearch(
            dense_search=vector_search,
            chunks=vector_search.get_chunks(),
            dense_candidate_k=settings.hybrid_dense_candidate_k,
            bm25_candidate_k=settings.hybrid_bm25_candidate_k,
            rrf_k=settings.hybrid_rrf_k,
        )


router = APIRouter(prefix="/internal/rag", tags=["internal-rag"])


def get_runtime(request: Request) -> RagRuntime:
    """현재 FastAPI 애플리케이션의 RAG runtime을 반환한다.

    Args:
        request: 애플리케이션 상태에 접근할 FastAPI 요청 객체.

    Returns:
        프로세스 내부 Vector 인덱스를 관리하는 RagRuntime.
    """
    return request.app.state.rag_runtime


@router.get("/ready", response_model=ReadyResponse)
async def ready(
    rag_runtime: RagRuntime = Depends(get_runtime),
    settings_config: Settings = Depends(get_settings),
) -> ReadyResponse:
    """외부 API 호출 없이 RAG 인덱스와 모델 설정 상태를 반환한다.

    Args:
        rag_runtime: 현재 프로세스의 인덱스 상태를 보관하는 runtime.
        settings_config: LLM, Embedding과 LangSmith 설정.

    Returns:
        인덱스 준비 여부, 모델 설정 상태와 문서·Chunk 수.
    """
    return ReadyResponse(
        status="ready" if rag_runtime.ready else "not_ready",
        index_ready=rag_runtime.ready,
        llm_configured=settings_config.llm_configured,
        embedding_configured=settings_config.embedding_configured,
        langsmith_tracing=settings_config.langsmith_configured,
        document_count=rag_runtime.document_count,
        chunk_count=rag_runtime.chunk_count,
        index_source=rag_runtime.index_source,
    )


@router.post("/index", response_model=IndexResponse)
async def create_index(
    request_body: IndexRequest | None = None,
    rag_runtime: RagRuntime = Depends(get_runtime),
    settings_config: Settings = Depends(get_settings),
) -> IndexResponse:
    """로컬 캐시를 우선 사용해 현재 프로세스의 RAG 인덱스를 준비한다.

    Args:
        request_body: 유효한 캐시를 무시할지 지정하는 선택적 요청 본문.
        rag_runtime: 인덱스와 모델 팩토리를 보관하는 현재 프로세스 runtime.
        settings_config: 캐시 경로, 모델명과 Chunk 설정.

    Returns:
        인덱스 상태, 생성 출처와 문서·Chunk 수.

    Raises:
        HTTPException: 설정 누락, PDF 처리 또는 Embedding 요청에 실패했을 때.
    """
    force_rebuild = request_body.force if request_body is not None else False
    if rag_runtime.ready and not force_rebuild:
        return _index_response(rag_runtime, "already_ready")

    async with rag_runtime.index_lock:
        if rag_runtime.ready and not force_rebuild:
            return _index_response(rag_runtime, "already_ready")

        try:
            embedding_model = rag_runtime.embedding_factory()
            if settings_config.vector_store_backend == "postgres":
                cached_vector_index = await run_in_threadpool(
                    partial(
                        load_or_build_postgres_index,
                        embedding=embedding_model,
                        settings=settings_config,
                        force=force_rebuild,
                    )
                )
            else:
                document_catalog = get_document_catalog()
                cached_vector_index = await run_in_threadpool(
                    partial(
                        load_or_build_document_index,
                        embedding=embedding_model,
                        settings=settings_config,
                        catalog=document_catalog,
                        force=force_rebuild,
                    )
                )
            runtime_search: VectorSearch = cached_vector_index.vector_search
            if settings_config.retrieval_mode == "hybrid":
                runtime_search = HybridSearch(
                    dense_search=cached_vector_index.vector_search,
                    chunks=cached_vector_index.vector_search.get_chunks(),
                    dense_candidate_k=settings_config.hybrid_dense_candidate_k,
                    bm25_candidate_k=settings_config.hybrid_bm25_candidate_k,
                    rrf_k=settings_config.hybrid_rrf_k,
                )
            rag_runtime.set_index(
                runtime_search,
                document_count=cached_vector_index.document_count,
                chunk_count=cached_vector_index.chunk_count,
                index_source=(
                    "cache"
                    if cached_vector_index.loaded_from_cache
                    else "embedding"
                ),
            )
        except (ModelConfigurationError, DatabaseConfigurationError) as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc
        except (FileNotFoundError, PdfDocumentError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(exc),
            ) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Document embedding failed.",
            ) from exc

    return _index_response(rag_runtime, "ready")


@router.post("/answer", response_model=RagAnswerResponse)
async def answer(
    request_body: RagAnswerRequest,
    rag_runtime: RagRuntime = Depends(get_runtime),
    settings_config: Settings = Depends(get_settings),
) -> RagAnswerResponse:
    """사용자 질문을 LangGraph의 Policy·Notice·Tax 흐름으로 처리한다.

    Args:
        request_body: 질문, 선택적 정책 ID, top-k와 Backend 판정 결과.
        rag_runtime: 준비된 Vector Search와 LLM 팩토리를 제공하는 runtime.
        settings_config: 검색·Guardrail·LangSmith 설정.

    Returns:
        근거 기반 답변, 출처, 판정 보존값과 Guardrail 사유.

    Raises:
        HTTPException: 인덱스 미준비, 입력 오류 또는 외부 모델 호출 실패 시.
    """
    try:
        normalized_question = validate_question(
            request_body.question,
            max_length=settings_config.max_question_length,
        )
        result_limit = validate_top_k(
            request_body.top_k or settings_config.default_top_k
        )
        eligibility_decision = _to_domain_decision(request_body.decision)
        user_context = None
        if request_body.user_id is not None:
            user_context = (
                get_database_user_profile(request_body.user_id, settings_config)
                if settings_config.vector_store_backend == "postgres"
                else get_mock_user_profile(request_body.user_id)
            )
        hybrid_search = (
            rag_runtime.require_hybrid_index(settings_config)
            if rag_runtime.ready
            else None
        )
        graph = build_graph(
            rag_runtime.llm_factory(),
            policy_search=hybrid_search,
            tax_search=hybrid_search,
            notice_search=rag_runtime.notice_search,
            tax_calculator=rag_runtime.tax_calculator,
            settings=settings_config,
        )
        graph_result = await graph.ainvoke(
            {
                "query": normalized_question,
                "policy_id": request_body.policy_id,
                "top_k": result_limit,
                "decision": eligibility_decision,
                "user_context": user_context,
            }
        )
        source_responses = [
            _graph_source_response(source)
            for source in graph_result.get("answer_sources", [])
            if "chunk_id" in source and "content" in source
        ]
        return RagAnswerResponse(
            answer=str(graph_result["answer"]),
            route=graph_result["route"],
            status=graph_result["answer_status"],
            grounded=bool(source_responses),
            sources=source_responses,
            decision=request_body.decision,
            guardrail_reason=(
                "insufficient_evidence"
                if graph_result["answer_status"]
                in {"no_result", "insufficient_evidence"}
                else "generation_validation_failed"
                if graph_result["answer_status"] == "error"
                else None
            ),
        )
    except RagIndexNotReadyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except (ModelConfigurationError, LangSmithConfigurationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except (MockDataNotFoundError, DatabaseDataNotFoundError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except RagInputError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="RAG answer generation failed.",
        ) from exc


def _to_domain_decision(
    decision: EligibilityDecisionRequest | None,
) -> EligibilityDecision | None:
    """API 판정 요청을 변경 불가능한 내부 판정 객체로 변환한다.

    Args:
        decision: Backend가 전달한 API 판정 객체 또는 None.

    Returns:
        reasons를 tuple로 고정한 내부 판정 객체 또는 None.
    """
    if decision is None:
        return None
    return EligibilityDecision(
        eligible=decision.eligible,
        reasons=tuple(decision.reasons),
    )


def _index_response(
    runtime: RagRuntime,
    response_status: Literal["ready", "already_ready"],
) -> IndexResponse:
    """현재 runtime 상태를 인덱스 API 응답으로 변환한다.

    Args:
        runtime: 문서·Chunk 수와 인덱스 생성 출처를 보관하는 runtime.
        response_status: 신규 준비 또는 기존 준비 상태를 나타내는 값.

    Returns:
        JSON 직렬화 가능한 IndexResponse 객체.
    """
    return IndexResponse(
        status=response_status,
        source=runtime.index_source or "embedding",
        document_count=runtime.document_count,
        chunk_count=runtime.chunk_count,
    )


@router.post("/recommendations", response_model=PolicyRecommendationResponse)
async def recommend_policies(
    request_body: PolicyRecommendationRequest,
    rag_runtime: RagRuntime = Depends(get_runtime),
    settings_config: Settings = Depends(get_settings),
) -> PolicyRecommendationResponse:
    """Mock 사용자 프로필과 질문을 이용해 전체 정책을 검색·요약한다.

    Args:
        request_body: 사용자 ID, 질문과 검색할 최대 Chunk 수.
        rag_runtime: 준비된 Vector Search와 LLM 팩토리를 제공하는 runtime.
        settings_config: 검색·Guardrail·LangSmith 설정.

    Returns:
        사용자 ID, 관련 정책별 출처, 요약과 Guardrail 사유.

    Raises:
        HTTPException: 사용자·인덱스가 없거나 입력 또는 외부 모델 호출 실패 시.
    """
    try:
        vector_search = rag_runtime.require_index()
        user_profile = (
            get_database_user_profile(request_body.user_id, settings_config)
            if settings_config.vector_store_backend == "postgres"
            else get_mock_user_profile(request_body.user_id)
        )
        discovery_service = PolicyDiscoveryService(
            vector_search=vector_search,
            llm_factory=rag_runtime.llm_factory,
            settings=settings_config,
        )
        discovery_answer = await discovery_service.discover(
            request_body.question,
            user=user_profile,
            top_k=request_body.top_k,
        )
        return PolicyRecommendationResponse(
            user_id=discovery_answer.user_id,
            answer=discovery_answer.answer,
            grounded=discovery_answer.grounded,
            policies=[
                MatchedPolicyResponse(
                    policy_id=matched_policy.policy_id,
                    title=matched_policy.title,
                    sources=[
                        _to_source_response(source)
                        for source in matched_policy.sources
                    ],
                )
                for matched_policy in discovery_answer.policies
            ],
            guardrail_reason=discovery_answer.guardrail_reason,
        )
    except RagIndexNotReadyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except (MockDataNotFoundError, DatabaseDataNotFoundError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except (ModelConfigurationError, LangSmithConfigurationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except RagInputError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Policy recommendation generation failed.",
        ) from exc


def _to_source_response(source: SourceCitation) -> SourceResponse:
    """내부 출처 객체를 FastAPI 응답 schema로 변환한다.

    Args:
        source: RAG 서비스가 생성한 Chunk 출처 객체.

    Returns:
        API JSON 직렬화에 사용할 SourceResponse 객체.
    """
    return SourceResponse(
        chunk_id=source.chunk_id,
        policy_id=source.policy_id,
        title=source.title,
        source=source.source,
        page=source.page,
        excerpt=source.excerpt,
        score=source.score,
    )


def _graph_source_response(source: dict[str, object]) -> SourceResponse:
    """Graph가 선택한 실제 Vector 문서를 기존 API 출처 schema로 변환한다."""
    content = " ".join(str(source["content"]).split())[:500]
    return SourceResponse(
        chunk_id=str(source["chunk_id"]),
        policy_id=(
            int(source["policy_id"])
            if source.get("policy_id") is not None
            else None
        ),
        title=str(source["title"]),
        source=str(source["source"]),
        page=int(source["page"]),
        excerpt=content,
        score=float(source["score"]),
    )
