"""HTTP client for the internal LLM service. Returns None when LLM is down.

LLM_API_SPEC_V1.md 경로(/rag/*, /ocr/receipt)를 먼저 호출하고, 없으면 기존 /internal/* 로 폴백한다.
"""

from __future__ import annotations

import base64
import json
import logging
import uuid
import urllib.error
import urllib.request

from core.config import LLM_API_URL, LLM_TIMEOUT_SECONDS


logger = logging.getLogger(__name__)


def llm_status() -> dict:
    health = _get("/health")
    ready = _get("/rag/ready") or _get("/internal/rag/ready")
    return {
        "url": LLM_API_URL,
        "reachable": health is not None,
        "health": health,
        "ragReady": bool(ready and ready.get("index_ready")),
        "llmConfigured": bool(ready and ready.get("llm_configured")),
    }


def ensure_index(document_ids: list[int] | None = None) -> bool:
    ready = _get("/rag/ready") or _get("/internal/rag/ready")
    if ready and ready.get("index_ready"):
        return True
    result = _post("/rag/reindex", {"documentIds": document_ids or []}) or _post(
        "/internal/rag/index", {}
    )
    return bool(result and result.get("status") in ("ready", "already_ready"))


def rag_answer(
    question: str,
    *,
    category: str | None = None,
    policy_id: int | None = None,
    decision: dict | None = None,
) -> dict | None:
    if not ensure_index():
        return None
    spec = _post(
        "/rag/chat",
        {"category": category or "tax", "question": question},
    )
    if spec and spec.get("answer"):
        return spec
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
    if image_base64:
        multipart = _post_multipart(
            "/ocr/receipt",
            filename=filename,
            image_base64=image_base64,
            mime_type=mime_type,
            timeout=max(LLM_TIMEOUT_SECONDS, 45),
        )
        if multipart:
            return multipart
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


def explain_expense(
    category: str,
    vendor: str,
    amount: int,
    items: list[str] | None = None,
) -> dict | None:
    normalized_category = (category or "").strip() or "미분류"
    normalized_vendor = (vendor or "").strip() or "상호 미상"
    normalized_items = [item.strip() for item in items or [] if item.strip()]
    spec = _post(
        "/rag/deductibility",
        {
            "category": normalized_category,
            "amount": amount,
            "vendor": normalized_vendor,
            "items": normalized_items,
        },
    )
    if spec and spec.get("basis"):
        return {
            "answer": spec["basis"],
            "deductible": spec.get("deductible"),
            "confidence": spec.get("confidence"),
            "sources": [],
        }
    return rag_answer(
        f"[expense] 사업 경비 인정 가능성. 카테고리 {normalized_category}, "
        f"상호 {normalized_vendor}, 금액 {amount}원. "
        "세법상 참고 근거를 짧게 설명하고 최종 인정은 세무서·세무사 확인이 필요하다고 고지하라.",
        category="expense",
    )


def summarize_announcement(raw_content: str, source: str | None = None) -> dict | None:
    normalized_content = (raw_content or "").strip()
    if not normalized_content:
        logger.info("Skipping LLM announcement summary because content is blank")
        return None
    spec = _post(
        "/rag/summarize-announcement",
        {"rawContent": normalized_content, "source": source or ""},
    )
    if spec:
        return spec
    return _post(
        "/internal/summarize/announcement",
        {"rawContent": normalized_content, "source": source or ""},
    )


def explain_tax_reduction(
    eligible: bool,
    reasons: list[str],
    conditions: dict | None = None,
) -> dict | None:
    spec = _post(
        "/rag/legal-basis",
        {"eligible": eligible, "reasons": reasons, "conditions": conditions or {}},
    )
    if spec:
        return spec
    return _post(
        "/internal/explain/tax-reduction",
        {"eligible": eligible, "reasons": reasons},
    )


def _get(path: str) -> dict | None:
    return _request("GET", path)


def _post(path: str, body: dict) -> dict | None:
    return _request("POST", path, body)


def _post_multipart(
    path: str,
    *,
    filename: str,
    image_base64: str,
    mime_type: str,
    timeout: float,
) -> dict | None:
    try:
        raw = base64.b64decode(image_base64)
    except (ValueError, TypeError):
        return None
    boundary = f"----skn34{uuid.uuid4().hex}"
    header = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="image"; filename="{filename}"\r\n'
        f"Content-Type: {mime_type or 'image/jpeg'}\r\n\r\n"
    ).encode("utf-8")
    footer = f"\r\n--{boundary}--\r\n".encode("ascii")
    data = header + raw + footer
    url = f"{LLM_API_URL}{path}"
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Accept": "application/json",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            payload = res.read().decode("utf-8")
            return json.loads(payload) if payload else {}
    except urllib.error.HTTPError as exc:
        _log_http_error("POST", path, exc)
        return None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        _log_transport_error("POST", path, exc)
        return None


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
    except urllib.error.HTTPError as exc:
        _log_http_error(method, path, exc)
        return None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        _log_transport_error(method, path, exc)
        return None


def _log_http_error(
    method: str,
    path: str,
    exc: urllib.error.HTTPError,
) -> None:
    """LLM 오류 응답에서 비민감 코드만 추출해 기록한다."""
    error_code = "HTTP_ERROR"
    retryable = exc.code >= 500
    try:
        raw = exc.read().decode("utf-8")
        payload = json.loads(raw) if raw else {}
        error = payload.get("error") if isinstance(payload, dict) else None
        if isinstance(error, dict):
            error_code = str(error.get("code") or error_code)
            retryable = bool(error.get("retryable", retryable))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        pass
    logger.warning(
        "LLM HTTP error: method=%s path=%s status=%s code=%s retryable=%s",
        method,
        path,
        exc.code,
        error_code,
        retryable,
    )


def _log_transport_error(method: str, path: str, exc: Exception) -> None:
    """URL·요청 본문·자격증명을 제외하고 전송 오류 종류만 기록한다."""
    logger.warning(
        "LLM transport error: method=%s path=%s type=%s",
        method,
        path,
        type(exc).__name__,
    )
