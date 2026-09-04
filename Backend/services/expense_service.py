from datetime import date, datetime

from fastapi import HTTPException

from core import store

CATEGORY_RULES = {
    "사무용품": (True, 0.9, "사업용 소모품으로 경비 인정 가능성이 높습니다."),
    "식비": (True, 0.55, "업무 관련 식비는 일부 인정될 수 있으나 한도가 있습니다."),
    "교통": (True, 0.7, "출장·업무 이동이면 인정 가능성이 있습니다."),
    "접대": (False, 0.35, "접대비는 한도와 증빙 요건이 까다롭습니다."),
}


def _classify(vendor: str, amount: int) -> str:
    text = vendor.lower()
    if any(k in vendor for k in ("카페", "커피", "식당")) or "cafe" in text:
        return "식비"
    if any(k in vendor for k in ("문구", "오피스", "전자")):
        return "사무용품"
    if amount >= 30000:
        return "접대"
    return "교통"


def create_receipt(user_id: int, filename: str) -> dict:
    rid = store.next_id("receipt")
    vendor = "샘플문구점" if "office" in filename.lower() else "강남카페"
    amount = 18000
    items = ["아이스 아메리카노", "크루아상"] if "카페" in vendor else ["노트", "펜"]
    category = _classify(vendor, amount)
    deductible, confidence, basis = CATEGORY_RULES[category]
    store.receipts[rid] = {
        "id": rid,
        "user_id": user_id,
        "image_url": filename,
        "status": "done",
        "created_at": datetime.now(),
    }
    store.receipt_extractions[rid] = {
        "id": store.next_id("extract"),
        "receipt_id": rid,
        "date": date.today(),
        "vendor": vendor,
        "amount": amount,
        "items": items,
    }
    eid = store.next_id("expense")
    store.expenses[eid] = {
        "id": eid,
        "receipt_id": rid,
        "user_id": user_id,
        "category": category,
        "amount": amount,
        "date": date.today(),
        "deductible": deductible,
        "deductible_confidence": confidence,
        "deductible_basis": basis + " (OCR/LLM 미연동 목업)",
    }
    return {"receiptId": rid, "status": "done"}


def get_extraction(receipt_id: int, user_id: int) -> dict:
    receipt = store.receipts.get(receipt_id)
    if not receipt or receipt["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="영수증을 찾을 수 없습니다.")
    extraction = store.receipt_extractions[receipt_id]
    return {
        "date": extraction["date"],
        "vendor": extraction["vendor"],
        "amount": extraction["amount"],
        "items": extraction["items"],
    }


def list_expenses(user_id: int, category: str | None = None) -> list[dict]:
    rows = [e for e in store.expenses.values() if e["user_id"] == user_id]
    if category:
        rows = [e for e in rows if e["category"] == category]
    return [
        {
            "expenseId": e["id"],
            "receiptId": e["receipt_id"],
            "category": e["category"],
            "amount": e["amount"],
            "date": e["date"],
            "deductible": e["deductible"],
        }
        for e in rows
    ]


def deductibility(expense_id: int, user_id: int) -> dict:
    expense = store.expenses.get(expense_id)
    if not expense or expense["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="지출을 찾을 수 없습니다.")
    return {
        "deductible": expense["deductible"],
        "confidence": expense["deductible_confidence"],
        "basis": expense["deductible_basis"],
    }
