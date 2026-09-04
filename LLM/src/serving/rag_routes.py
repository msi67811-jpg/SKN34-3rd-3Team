from functools import partial
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from starlette.concurrency import run_in_threadpool

from src.core.config import Settings, get_settings
from src.core.langsmith import LangSmithConfigurationError
from src.data import MockDataNotFoundError, get_document_catalog, get_user_profile
from src.features.index_cache import load_or_build_document_index
from src.features.pdf_loader import PdfDocumentError
from src.models import ModelConfigurationError
from src.rag.contracts import EligibilityDecision, SourceCitation
from src.rag.discovery import PolicyDiscoveryService
from src.rag.guardrails import RagInputError
from src.rag.runtime import RagIndexNotReadyError, RagRuntime
from src.rag.service import RagService
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
            document_catalog = get_document_catalog()
            embedding_model = rag_runtime.embedding_factory()
            cached_vector_index = await run_in_threadpool(
                partial(
                    load_or_build_document_index,
                    embedding=embedding_model,
                    settings=settings_config,
                    catalog=document_catalog,
                    force=force_rebuild,
                )
            )
            rag_runtime.set_index(
                cached_vector_index.vector_search,
                document_count=cached_vector_index.document_count,
                chunk_count=cached_vector_index.chunk_count,
                index_source=(
                    "cache"
                    if cached_vector_index.loaded_from_cache
                    else "embedding"
                ),
            )
        except ModelConfigurationError as exc:
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
    """특정 정책 문서와 선택적 Backend 판정을 근거로 답변한다.

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
        vector_search = rag_runtime.require_index()
        rag_service = RagService(
            vector_search=vector_search,
            llm_factory=rag_runtime.llm_factory,
            settings=settings_config,
        )
        eligibility_decision = _to_domain_decision(request_body.decision)
        rag_answer = await rag_service.answer(
            request_body.question,
            policy_id=request_body.policy_id,
            top_k=request_body.top_k,
            decision=eligibility_decision,
        )
        return RagAnswerResponse(
            answer=rag_answer.answer,
            grounded=rag_answer.grounded,
            sources=[_to_source_response(source) for source in rag_answer.sources],
            decision=(
                EligibilityDecisionRequest(
                    eligible=rag_answer.decision.eligible,
                    reasons=list(rag_answer.decision.reasons),
                )
                if rag_answer.decision is not None
                else None
            ),
            guardrail_reason=rag_answer.guardrail_reason,
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
        user_profile = get_user_profile(request_body.user_id)
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
    except MockDataNotFoundError as exc:
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
