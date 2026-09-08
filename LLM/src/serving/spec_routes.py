"""LLM_API_SPEC.md 계약 엔드포인트. 기존 /internal/* 는 호환용으로 유지한다."""

from __future__ import annotations

import base64
from typing import Literal

from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel, Field

from src.core.config import Settings, get_settings
from src.serving.ai_routes import (
    AnnouncementSummarizeRequest,
    ReceiptOcrRequest,
    TaxExplainRequest,
    explain_tax_reduction,
    ocr_receipt,
    summarize_announcement,
)
from src.serving.rag_routes import RagRuntime, answer, create_index, get_runtime, ready
from src.serving.schemas import IndexRequest, RagAnswerRequest


router = APIRouter(tags=["spec-llm"])

DEDUCT_RULES = {
    "사무용품": (True, 0.9, "사업용 소모품으로 경비 인정 가능성이 높습니다."),
    "식비": (True, 0.55, "업무 관련 식비는 일부 인정될 수 있으나 한도가 있습니다."),
    "교통": (True, 0.7, "출장·업무 이동이면 인정 가능성이 있습니다."),
    "경조사비": (False, 0.35, "경조사비는 한도와 증빙 요건이 까다롭습니다."),
}


class ChatSpecRequest(BaseModel):
    category: Literal["tax", "expense", "saving", "policy"]
    question: str


class ChatSpecSource(BaseModel):
    title: str
    url: str = ""
    excerpt: str = ""


class ChatSpecResponse(BaseModel):
    answer: str
    sources: list[ChatSpecSource]
    grounded: bool | None = None
    guardrail_reason: str | None = None


class LegalConditions(BaseModel):
    age: int | None = None
    region: str | None = None
    industry: str | None = None
    businessRegisteredAt: str | None = None
    foundedAt: str | None = None


class LegalBasisRequest(BaseModel):
    eligible: bool
    conditions: LegalConditions | None = None
    reasons: list[str] = Field(default_factory=list)


class LegalBasisResponse(BaseModel):
    reasons: list[str]
    legalBasis: str
    llmUsed: bool = False


class OcrSpecResponse(BaseModel):
    date: str | None
    vendor: str | None
    amount: int | None
    items: list[str] | None
    source: str | None = None


class DeductibilityRequest(BaseModel):
    category: str
    amount: int
    vendor: str = ""
    items: list[str] = Field(default_factory=list)


class DeductibilityResponse(BaseModel):
    deductible: bool
    confidence: float
    basis: str


class SummarizeRequest(BaseModel):
    rawContent: str
    source: str = ""


class SummarizeResponse(BaseModel):
    target: str
    benefit: str
    period: str
    documents: str
    notes: str
    source: str
    llmUsed: bool = False


class ReindexRequest(BaseModel):
    documentIds: list[int] | None = None
    force: bool = False


class ReindexResponse(BaseModel):
    status: str


def _reasons_from_conditions(conditions: LegalConditions | None, reasons: list[str]) -> list[str]:
    if reasons:
        return list(reasons)
    if not conditions:
        return []
    built = []
    if conditions.age is not None:
        built.append(f"나이 {conditions.age}세")
    if conditions.region:
        built.append(f"지역 {conditions.region}")
    if conditions.industry:
        built.append(f"업종 {conditions.industry}")
    if conditions.foundedAt:
        built.append(f"창업일 {conditions.foundedAt}")
    if conditions.businessRegisteredAt:
        built.append(f"사업자등록일 {conditions.businessRegisteredAt}")
    return built


@router.get("/rag/ready")
async def rag_ready(
    rag_runtime: RagRuntime = Depends(get_runtime),
    settings_config: Settings = Depends(get_settings),
):
    return await ready(rag_runtime=rag_runtime, settings_config=settings_config)


@router.post("/rag/chat", response_model=ChatSpecResponse)
async def rag_chat(
    body: ChatSpecRequest,
    rag_runtime: RagRuntime = Depends(get_runtime),
    settings_config: Settings = Depends(get_settings),
):
    inner = RagAnswerRequest(question=f"[{body.category}] {body.question}", top_k=5)
    result = await answer(inner, rag_runtime=rag_runtime, settings_config=settings_config)
    sources = [
        ChatSpecSource(title=item.title, url=item.source or "", excerpt=item.excerpt)
        for item in result.sources
    ]
    return ChatSpecResponse(
        answer=result.answer,
        sources=sources,
        grounded=result.grounded,
        guardrail_reason=result.guardrail_reason,
    )


@router.post("/rag/legal-basis", response_model=LegalBasisResponse)
def rag_legal_basis(body: LegalBasisRequest):
    reasons = _reasons_from_conditions(body.conditions, body.reasons)
    explained = explain_tax_reduction(TaxExplainRequest(eligible=body.eligible, reasons=reasons))
    return LegalBasisResponse(
        reasons=reasons,
        legalBasis=explained.legalBasis,
        llmUsed=explained.llmUsed,
    )


@router.post("/ocr/receipt", response_model=OcrSpecResponse)
async def ocr_receipt_spec(image: UploadFile = File(..., description="영수증 이미지")):
    content = await image.read()
    image_b64 = base64.b64encode(content).decode("ascii") if content else ""
    parsed = ocr_receipt(
        ReceiptOcrRequest(
            filename=image.filename or "receipt.jpg",
            imageBase64=image_b64,
            mimeType=image.content_type or "image/jpeg",
        )
    )
    return OcrSpecResponse(
        date=parsed.date,
        vendor=parsed.vendor,
        amount=parsed.amount,
        items=parsed.items,
        source=parsed.source,
    )


@router.post("/rag/deductibility", response_model=DeductibilityResponse)
async def rag_deductibility(
    body: DeductibilityRequest,
    rag_runtime: RagRuntime = Depends(get_runtime),
    settings_config: Settings = Depends(get_settings),
):
    deductible, confidence, basis = DEDUCT_RULES.get(body.category, DEDUCT_RULES["식비"])
    items = ", ".join(body.items) if body.items else "품목 미상"
    question = (
        f"[expense] 사업 경비 인정 가능성. 카테고리 {body.category}, 상호 {body.vendor}, "
        f"금액 {body.amount}원, 품목 {items}. 세법상 참고 근거를 짧게 설명하고 "
        "최종 인정은 세무서·세무사 확인이 필요하다고 고지하라."
    )
    try:
        inner = RagAnswerRequest(question=question, top_k=5)
        result = await answer(inner, rag_runtime=rag_runtime, settings_config=settings_config)
        if result.answer:
            basis = result.answer
    except Exception:
        pass
    return DeductibilityResponse(deductible=deductible, confidence=confidence, basis=basis)


@router.post("/rag/summarize-announcement", response_model=SummarizeResponse)
def rag_summarize(body: SummarizeRequest):
    parsed = summarize_announcement(
        AnnouncementSummarizeRequest(rawContent=body.rawContent, source=body.source)
    )
    return SummarizeResponse(
        target=parsed.target,
        benefit=parsed.benefit,
        period=parsed.period,
        documents=parsed.documents,
        notes=parsed.notes,
        source=parsed.source,
        llmUsed=parsed.llmUsed,
    )


@router.post("/rag/reindex", response_model=ReindexResponse)
async def rag_reindex(
    body: ReindexRequest | None = None,
    rag_runtime: RagRuntime = Depends(get_runtime),
    settings_config: Settings = Depends(get_settings),
):
    force = bool(body and body.force)
    result = await create_index(
        IndexRequest(force=force),
        rag_runtime=rag_runtime,
        settings_config=settings_config,
    )
    return ReindexResponse(status=result.status)
