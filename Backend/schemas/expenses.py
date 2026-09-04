from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class ReceiptCreateResponse(BaseModel):
    model_config = ConfigDict(title="영수증 등록 결과")
    receiptId: int = Field(description="영수증 ID")
    status: str = Field(description="처리 상태")


class ReceiptExtractionResponse(BaseModel):
    model_config = ConfigDict(title="영수증 추출 결과")
    date: date = Field(description="거래일")
    vendor: str = Field(description="상호")
    amount: int = Field(description="금액")
    items: list[str] = Field(description="품목")


class ExpenseItem(BaseModel):
    model_config = ConfigDict(title="지출 항목")
    expenseId: int = Field(description="지출 ID")
    receiptId: int = Field(description="영수증 ID")
    category: str = Field(description="분류")
    amount: int = Field(description="금액")
    date: date = Field(description="날짜")
    deductible: bool = Field(description="경비 인정 가능 여부")


class ExpenseListResponse(BaseModel):
    model_config = ConfigDict(title="지출 목록")
    expenses: list[ExpenseItem] = Field(description="지출들")


class DeductibilityResponse(BaseModel):
    model_config = ConfigDict(title="경비처리 가능성")
    deductible: bool = Field(description="인정 가능 여부")
    confidence: float = Field(description="신뢰도 (0~1)")
    basis: str = Field(description="안내 문구")
