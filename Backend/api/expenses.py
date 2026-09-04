from fastapi import APIRouter, Depends, File, Path, Query, UploadFile

from api.deps import get_current_user
from schemas.expenses import (
    DeductibilityResponse,
    ExpenseListResponse,
    ReceiptCreateResponse,
    ReceiptExtractionResponse,
)
from services import expense_service

router = APIRouter(prefix="/expenses", tags=["지출"])


@router.post("/receipts", response_model=ReceiptCreateResponse, summary="영수증 등록")
async def upload_receipt(
    image: UploadFile = File(..., description="영수증 이미지 파일"),
    current: dict = Depends(get_current_user),
):
    """파일은 받지만 OCR 대신 샘플 상호·금액을 채웁니다."""
    filename = image.filename or "receipt.jpg"
    return expense_service.create_receipt(current["id"], filename)


@router.get(
    "/receipts/{receipt_id}",
    response_model=ReceiptExtractionResponse,
    summary="영수증 추출 결과 조회",
)
def receipt_detail(
    receipt_id: int = Path(description="영수증 ID"),
    current: dict = Depends(get_current_user),
):
    """등록된 영수증의 날짜·상호·금액 샘플 결과입니다."""
    return expense_service.get_extraction(receipt_id, current["id"])


@router.get("", response_model=ExpenseListResponse, summary="지출 내역 조회")
def expense_list(
    category: str | None = Query(default=None, description="지출 카테고리 필터(선택)"),
    current: dict = Depends(get_current_user),
):
    """분류된 지출 목록입니다."""
    return {"expenses": expense_service.list_expenses(current["id"], category)}


@router.get(
    "/{expense_id}/deductibility",
    response_model=DeductibilityResponse,
    summary="경비처리 가능성 조회",
)
def deductibility(
    expense_id: int = Path(description="지출 ID"),
    current: dict = Depends(get_current_user),
):
    """카테고리 규칙으로 경비 인정 가능성을 안내합니다."""
    return expense_service.deductibility(expense_id, current["id"])
