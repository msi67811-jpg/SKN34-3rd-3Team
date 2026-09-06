from fastapi import APIRouter, Depends, Path, Query

from api.deps import get_current_user
from schemas.chat import (
    ChatMessageRequest,
    ChatMessageResponse,
    SourcesResponse,
    SuggestedQuestionsResponse,
)
from services import chat_service

router = APIRouter(prefix="/chat", tags=["상담"])


@router.get(
    "/categories/{category}/suggested-questions",
    response_model=SuggestedQuestionsResponse,
    summary="추천 질문 목록",
)
def suggested(
    category: str = Path(description="카테고리: tax / expense / saving / policy"),
):
    """카테고리별 추천 질문입니다."""
    return {"category": category, "questions": chat_service.suggested_questions(category)}


@router.post("/messages", response_model=ChatMessageResponse, summary="챗봇 질문 보내기")
def send_message(body: ChatMessageRequest, current: dict = Depends(get_current_user)):
    """LLM RAG를 우선 호출하고, 실패하면 목업 답변을 저장합니다."""
    return chat_service.send_message(current["id"], body.category, body.question)


@router.get("/messages", summary="대화 히스토리 조회")
def history(
    category: str | None = Query(default=None, description="카테고리 필터(선택)"),
    current: dict = Depends(get_current_user),
):
    """로그인한 사용자의 질문·답변 목록입니다."""
    return {"messages": chat_service.list_messages(current["id"], category)}


@router.delete("/messages", summary="대화 기록 초기화")
def clear_history(
    category: str | None = Query(default=None, description="비우면 전체, 있으면 해당 카테고리만"),
    current: dict = Depends(get_current_user),
):
    """현재 사용자의 상담 기록을 지웁니다."""
    deleted = chat_service.clear_messages(current["id"], category)
    return {"deleted": True, "count": deleted}


@router.get(
    "/messages/{message_id}/sources",
    response_model=SourcesResponse,
    summary="답변 근거 문서 조회",
)
def sources(message_id: int = Path(description="메시지 ID")):
    """해당 답변에 저장된 RAG 또는 샘플 근거 문서를 반환합니다."""
    return {"sources": chat_service.get_sources(message_id)}
