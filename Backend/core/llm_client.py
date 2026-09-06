"""HTTP client for the internal LLM service. Returns None when LLM is down."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from core.config import LLM_API_URL, LLM_TIMEOUT_SECONDS


def llm_status() -> dict:
    health = _get("/health")
    ready = _get("/internal/rag/ready")
    return {
        "url": LLM_API_URL,
        "reachable": health is not None,
        "health": health,
        "ragReady": bool(ready and ready.get("index_ready")),
        "llmConfigured": bool(ready and ready.get("llm_configured")),
    }


def ensure_index() -> bool:
    ready = _get("/internal/rag/ready")
    if ready and ready.get("index_ready"):
        return True
    result = _post("/internal/rag/index", {})
    return bool(result and result.get("status") in ("ready", "already_ready"))


def rag_answer(question: str, *, policy_id: int | None = None, decision: dict | None = None) -> dict | None:
    if not ensure_index():
        return None
    body: dict = {"question": question, "top_k": 5}
    if policy_id is not None:
        body["policy_id"] = policy_id
    if decision is not None:
        body["decision"] = decision
    return _post("/internal/rag/answer", body)


def extract_receipt(
    filename: str,
    *,
    image_base64: str | None = None,
    mime_type: str = "image/jpeg",
) -> dict | None:
    return _request(
        "POST",
        "/internal/ocr/receipt",
        {
            "filename": filename,
            "imageBase64": image_base64 or "",
            "mimeType": mime_type or "image/jpeg",
        },
        timeout=max(LLM_TIMEOUT_SECONDS, 45),
    )


def explain_expense(category: str, vendor: str, amount: int) -> dict | None:
    return rag_answer(
        f"[expense] 사업 경비 인정 가능성. 카테고리 {category}, 상호 {vendor}, 금액 {amount}원. "
        "세법상 참고 근거를 짧게 설명하고 최종 인정은 세무서·세무사 확인이 필요하다고 고지하라."
    )


def summarize_announcement(raw_content: str, source: str | None = None) -> dict | None:
    return _post(
        "/internal/summarize/announcement",
        {"rawContent": raw_content, "source": source or ""},
    )


def explain_tax_reduction(eligible: bool, reasons: list[str]) -> dict | None:
    return _post(
        "/internal/explain/tax-reduction",
        {"eligible": eligible, "reasons": reasons},
    )


def _get(path: str) -> dict | None:
    return _request("GET", path)


def _post(path: str, body: dict) -> dict | None:
    return _request("POST", path, body)


def _request(
    method: str,
    path: str,
    body: dict | None = None,
    timeout: float | None = None,
) -> dict | None:
    url = f"{LLM_API_URL}{path}"
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout or LLM_TIMEOUT_SECONDS) as res:
            raw = res.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, OSError):
        return None
