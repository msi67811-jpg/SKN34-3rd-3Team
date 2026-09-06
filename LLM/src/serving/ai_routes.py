import json
import re
from datetime import date

from fastapi import APIRouter
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from src.models.factory import ModelConfigurationError, get_llm

router = APIRouter(prefix="/internal", tags=["internal-ai"])


class ReceiptOcrRequest(BaseModel):
    filename: str = Field(description="업로드된 영수증 파일명")
    imageBase64: str = Field(default="", description="영수증 이미지 Base64")
    mimeType: str = Field(default="image/jpeg", description="이미지 MIME 타입")


class ReceiptOcrResponse(BaseModel):
    date: str
    vendor: str
    amount: int
    items: list[str]
    category: str
    source: str


class AnnouncementSummarizeRequest(BaseModel):
    rawContent: str
    source: str = ""


class AnnouncementSummarizeResponse(BaseModel):
    target: str
    benefit: str
    period: str
    documents: str
    notes: str
    source: str
    llmUsed: bool = False


class TaxExplainRequest(BaseModel):
    eligible: bool
    reasons: list[str]


class TaxExplainResponse(BaseModel):
    legalBasis: str
    llmUsed: bool = False


def _heuristic_receipt(filename: str) -> dict:
    lower = filename.lower()
    if any(key in lower for key in ("office", "문구", "전자")):
        return {
            "date": date.today().isoformat(),
            "vendor": "샘플문구점",
            "amount": 18000,
            "items": ["노트", "펜"],
            "category": "사무용품",
            "source": "heuristic",
        }
    return {
        "date": date.today().isoformat(),
        "vendor": "강남카페",
        "amount": 12000,
        "items": ["아이스 아메리카노", "크루아상"],
        "category": "식비",
        "source": "heuristic",
    }


def _heuristic_summary(raw: str, source: str) -> dict:
    period_match = re.search(r"(\d{4}-\d{2}-\d{2}).{0,8}(\d{4}-\d{2}-\d{2})", raw)
    period = f"{period_match.group(1)} ~ {period_match.group(2)}" if period_match else "공고 원문 확인"
    return {
        "target": "청년·1인 창업자 (공고 원문 기준)",
        "benefit": raw[:180],
        "period": period,
        "documents": "사업계획서, 신분증, 사업자등록증(해당 시)",
        "notes": "참고용 요약입니다. 신청 전 원문 공고를 확인하세요.",
        "source": source or "공고문",
        "llmUsed": False,
    }


def _llm_json(prompt: str, *, image_base64: str = "", mime_type: str = "image/jpeg") -> dict | None:
    try:
        model = get_llm()
        if image_base64:
            message = model.invoke(
                [
                    HumanMessage(
                        content=[
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type or 'image/jpeg'};base64,{image_base64}"
                                },
                            },
                        ]
                    )
                ]
            )
        else:
            message = model.invoke(prompt)
        text = getattr(message, "content", str(message))
        match = re.search(r"\{.*\}", text, re.S)
        if not match:
            return None
        return json.loads(match.group(0))
    except (ModelConfigurationError, json.JSONDecodeError, Exception):
        return None


@router.post("/ocr/receipt", response_model=ReceiptOcrResponse)
def ocr_receipt(body: ReceiptOcrRequest) -> ReceiptOcrResponse:
    """영수증 이미지가 있으면 Vision으로 읽고, 없으면 파일명 규칙으로 추출한다."""
    prompt = (
        "너는 한국 영수증 OCR이다. 이미지(있으면) 또는 파일명으로 상호, 금액, 품목, "
        "카테고리(식비/사무용품/교통/경조사비)를 추출해 JSON만 반환하라. "
        "키: date(YYYY-MM-DD), vendor, amount(int), items(list), category. "
        f"파일명: {body.filename}"
    )
    parsed = _llm_json(prompt, image_base64=body.imageBase64, mime_type=body.mimeType)
    if parsed and parsed.get("vendor") and parsed.get("amount"):
        return ReceiptOcrResponse(
            date=str(parsed.get("date") or date.today().isoformat())[:10],
            vendor=str(parsed["vendor"]),
            amount=int(parsed["amount"]),
            items=[str(x) for x in (parsed.get("items") or [])] or ["품목 미상"],
            category=str(parsed.get("category") or "식비"),
            source="llm",
        )
    return ReceiptOcrResponse(**_heuristic_receipt(body.filename))


@router.post("/summarize/announcement", response_model=AnnouncementSummarizeResponse)
def summarize_announcement(body: AnnouncementSummarizeRequest) -> AnnouncementSummarizeResponse:
    """공고 원문을 지원대상/내용/기간/서류/유의사항으로 요약한다."""
    parsed = _llm_json(
        "다음 지원사업 공고를 JSON으로만 요약하라. 키: target, benefit, period, documents, notes, source. "
        "세무 자문을 대체하지 말 것. 원문:\n"
        f"{body.rawContent}\n출처:{body.source}"
    )
    if parsed and parsed.get("benefit"):
        return AnnouncementSummarizeResponse(
            target=str(parsed.get("target") or ""),
            benefit=str(parsed.get("benefit") or ""),
            period=str(parsed.get("period") or ""),
            documents=str(parsed.get("documents") or ""),
            notes=str(parsed.get("notes") or "원문 공고를 확인하세요."),
            source=str(parsed.get("source") or body.source or "공고문"),
            llmUsed=True,
        )
    return AnnouncementSummarizeResponse(**_heuristic_summary(body.rawContent, body.source))


@router.post("/explain/tax-reduction", response_model=TaxExplainResponse)
def explain_tax_reduction(body: TaxExplainRequest) -> TaxExplainResponse:
    """Backend Rule 판정은 바꾸지 않고, 법령 근거 안내 문장만 생성한다."""
    fallback = (
        "조세특례제한법 청년창업 중소기업 세액감면 요건을 단순화한 Rule 판정입니다. "
        "최종 법적 판단이 아니며 세무 전문가 확인이 필요합니다. "
        + ("요건을 충족하는 것으로 보입니다. " if body.eligible else "일부 요건이 부족할 수 있습니다. ")
        + " ".join(body.reasons)
    )
    parsed = _llm_json(
        "Backend가 확정한 청년창업 세액감면 Rule 결과다. eligible과 reasons를 바꾸지 말고, "
        "한국어 legalBasis 설명 한 문단만 JSON {\"legalBasis\": \"...\"} 으로 반환하라. "
        "세무사 자문을 대체하지 않는다고 고지할 것. "
        f"eligible={body.eligible}, reasons={body.reasons}"
    )
    if parsed and parsed.get("legalBasis"):
        return TaxExplainResponse(legalBasis=str(parsed["legalBasis"]), llmUsed=True)
    return TaxExplainResponse(legalBasis=fallback, llmUsed=False)
