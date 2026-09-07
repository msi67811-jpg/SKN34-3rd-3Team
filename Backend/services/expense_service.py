from datetime import date, datetime

from fastapi import HTTPException

from core import store
from core.database import persist
from core.llm_client import explain_expense, extract_receipt

CATEGORY_RULES = {
    "사무용품": (True, 0.9, "사업용 소모품으로 경비 인정 가능성이 높습니다."),
    "식비": (True, 0.55, "업무 관련 식비는 일부 인정될 수 있으나 한도가 있습니다."),
    "교통": (True, 0.7, "출장·업무 이동이면 인정 가능성이 있습니다."),
    "경조사비": (False, 0.35, "경조사비는 한도와 증빙 요건이 까다롭습니다."),
}


def _normalize_category(category: str | None) -> str | None:
    if category == "접대":
        return "경조사비"
    return category


def _classify(vendor: str, amount: int, hinted: str | None = None) -> str:
    hinted = _normalize_category(hinted)
    if hinted in CATEGORY_RULES:
        return hinted
    text = vendor.lower()
    if any(k in vendor for k in ("카페", "커피", "식당")) or "cafe" in text:
        return "식비"
    if any(k in vendor for k in ("문구", "오피스", "전자")):
        return "사무용품"
    if amount >= 30000:
        return "경조사비"
    return "교통"


def _apply_rule(expense: dict, category: str) -> None:
    category = _normalize_category(category) or "식비"
    deductible, confidence, basis = CATEGORY_RULES.get(category, CATEGORY_RULES["식비"])
    expense["category"] = category
    expense["deductible"] = deductible
    expense["deductible_confidence"] = confidence
    expense["deductible_basis"] = basis


def create_receipt(
    user_id: int,
    filename: str,
    *,
    image_base64: str | None = None,
    mime_type: str = "image/jpeg",
) -> dict:
    llm = extract_receipt(filename, image_base64=image_base64, mime_type=mime_type)
    if llm:
        vendor = llm.get("vendor") or "상호 미상"
        amount = int(llm.get("amount") or 0)
        items = llm.get("items") or []
        spent = date.fromisoformat(str(llm.get("date") or date.today())[:10])
        category = _classify(vendor, amount, llm.get("category"))
        source = llm.get("source") or "heuristic"
    else:
        vendor = "샘플문구점" if "office" in filename.lower() else "강남카페"
        amount = 18000
        items = ["아이스 아메리카노", "크루아상"] if "카페" in vendor else ["노트", "펜"]
        spent = date.today()
        category = _classify(vendor, amount)
        source = "mock"

    rid = store.next_id("receipt")
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
        "date": spent,
        "vendor": vendor,
        "amount": amount,
        "items": items,
        "source": source,
    }
    eid = store.next_id("expense")
    store.expenses[eid] = {
        "id": eid,
        "receipt_id": rid,
        "user_id": user_id,
        "category": category,
        "amount": amount,
        "date": spent,
        "deductible": True,
        "deductible_confidence": 0.5,
        "deductible_basis": "",
    }
    _apply_rule(store.expenses[eid], category)
    store.expenses[eid]["deductible_basis"] = (
        f"{store.expenses[eid]['deductible_basis']} (추출: {source})"
    )
    persist()
    return {"receiptId": rid, "status": "done", "ocrSource": source}


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
        "ocrSource": extraction.get("source") or "mock",
    }


def list_expenses(
    user_id: int,
    category: str | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
) -> list[dict]:
    rows = [e for e in store.expenses.values() if e["user_id"] == user_id]
    if category:
        rows = [e for e in rows if e["category"] == category]
    if from_date:
        rows = [e for e in rows if e["date"] >= from_date]
    if to_date:
        rows = [e for e in rows if e["date"] <= to_date]
    return [
        {
            "expenseId": e["id"],
            "receiptId": e["receipt_id"],
            "category": _normalize_category(e["category"]) or e["category"],
            "amount": e["amount"],
            "date": e["date"],
            "deductible": e["deductible"],
            "items": (store.receipt_extractions.get(e["receipt_id"]) or {}).get("items") or [],
        }
        for e in rows
    ]


def update_category(expense_id: int, user_id: int, category: str) -> dict:
    expense = store.expenses.get(expense_id)
    if not expense or expense["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="지출을 찾을 수 없습니다.")
    category = _normalize_category(category) or category
    if category not in CATEGORY_RULES:
        raise HTTPException(status_code=400, detail="지원하지 않는 카테고리입니다.")
    _apply_rule(expense, category)
    persist()
    return deductibility(expense_id, user_id)


def deductibility(expense_id: int, user_id: int) -> dict:
    expense = store.expenses.get(expense_id)
    if not expense or expense["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="지출을 찾을 수 없습니다.")
    extraction = store.receipt_extractions.get(expense["receipt_id"]) or {}
    vendor = extraction.get("vendor") or "상호 미상"
    rag = explain_expense(
        expense["category"],
        vendor,
        expense["amount"],
        items=list(extraction.get("items") or []),
    )
    basis = expense["deductible_basis"]
    llm_used = False
    sources: list[str] = []
    if rag and (rag.get("answer") or rag.get("basis")):
        basis = rag.get("answer") or rag.get("basis")
        llm_used = True
        if rag.get("deductible") is not None:
            expense["deductible"] = bool(rag["deductible"])
        if rag.get("confidence") is not None:
            expense["deductible_confidence"] = float(rag["confidence"])
        sources = [
            item.get("title") or item.get("source") or "세법 자료"
            for item in (rag.get("sources") or [])
            if item
        ]
        expense["deductible_basis"] = basis
        persist()
    return {
        "deductible": expense["deductible"],
        "confidence": expense["deductible_confidence"],
        "basis": basis,
        "llmUsed": llm_used,
        "sources": sources,
    }


def delete_expense(expense_id: int, user_id: int) -> None:
    expense = store.expenses.get(expense_id)
    if not expense or expense["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="지출을 찾을 수 없습니다.")
    receipt_id = expense["receipt_id"]
    del store.expenses[expense_id]
    still_used = any(row["receipt_id"] == receipt_id for row in store.expenses.values())
    if not still_used:
        store.receipts.pop(receipt_id, None)
        store.receipt_extractions.pop(receipt_id, None)
    persist()
