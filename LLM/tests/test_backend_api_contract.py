"""Backend↔LLM V1 공개 계약을 고정하는 회귀 테스트."""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from src.serving.app import create_app
from src.serving.rag_routes import MAX_RECEIPT_BYTES, RagRuntime
from src.serving.schemas import RagChatRequest


CANONICAL_OPERATIONS = {
    ("/health", "get"),
    ("/rag/ready", "get"),
    ("/rag/reindex", "post"),
    ("/rag/chat", "post"),
    ("/rag/legal-basis", "post"),
    ("/rag/deductibility", "post"),
    ("/rag/summarize-announcement", "post"),
    ("/ocr/receipt", "post"),
}


def build_contract_client() -> TestClient:
    """외부 모델을 생성하지 않는 V1 계약 검증용 client를 만든다."""
    return TestClient(create_app(runtime=RagRuntime()))


def test_openapi_exposes_every_v1_backend_operation() -> None:
    schema = create_app(runtime=RagRuntime()).openapi()

    exposed_operations = {
        (path, method)
        for path, path_item in schema["paths"].items()
        for method in path_item
        if method in {"get", "post", "put", "patch", "delete"}
    }

    assert CANONICAL_OPERATIONS <= exposed_operations


def test_chat_contract_serializes_typed_context_and_notice_dates() -> None:
    request = RagChatRequest.model_validate(
        {
            "category": "policy",
            "question": "현재 신청 가능한 정책이 있나요?",
            "userContext": {
                "userId": 1,
                "age": 29,
                "region": "서울",
                "businessType": "개인사업자",
                "industry": "소프트웨어",
                "businessRegisteredAt": "2026-02-01",
                "foundedAt": "2026-01-15",
            },
            "noticeResults": [
                {
                    "announcementId": 10,
                    "policyId": 3,
                    "title": "서울 청년창업 지원사업 모집",
                    "content": "공고 원문",
                    "benefit": "사업화 자금 지원",
                    "sourceUrl": "https://example.com/notices/10",
                    "applyStartDate": "2026-09-01",
                    "applyEndDate": "2026-09-30",
                }
            ],
        }
    )

    body = request.model_dump(mode="json")
    assert body["userContext"]["userId"] == 1
    assert body["noticeResults"][0]["announcementId"] == 10
    assert body["noticeResults"][0]["applyEndDate"] == "2026-09-30"


@pytest.mark.parametrize("category", ["tax", "expense", "saving", "policy"])
def test_chat_contract_accepts_every_frontend_category(category: str) -> None:
    request = RagChatRequest.model_validate(
        {"category": category, "question": "세금 또는 정책 질문"}
    )

    assert request.category == category


def test_chat_contract_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        RagChatRequest.model_validate(
            {
                "category": "policy",
                "question": "지원정책 질문",
                "userContext": {"userId": 1, "unknown": "value"},
            }
        )


def test_validation_error_always_uses_v1_error_envelope() -> None:
    client = build_contract_client()

    response = client.post(
        "/rag/chat",
        json={"category": "unknown", "question": "질문"},
    )

    assert response.status_code == 422
    assert set(response.json()) == {"error"}
    assert set(response.json()["error"]) == {"code", "message", "retryable"}
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert response.json()["error"]["retryable"] is False


def test_unknown_path_uses_v1_error_envelope() -> None:
    client = build_contract_client()

    response = client.get("/not-a-real-endpoint")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
    assert response.json()["error"]["retryable"] is False


def test_receipt_contract_rejects_empty_image() -> None:
    client = build_contract_client()

    response = client.post(
        "/ocr/receipt",
        files={"image": ("receipt.png", b"", "image/png")},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_receipt_contract_rejects_image_over_four_mib() -> None:
    client = build_contract_client()

    response = client.post(
        "/ocr/receipt",
        files={
            "image": (
                "receipt.png",
                b"x" * (MAX_RECEIPT_BYTES + 1),
                "image/png",
            )
        },
    )

    assert response.status_code == 413
    assert response.json()["error"] == {
        "code": "PAYLOAD_TOO_LARGE",
        "message": "receipt image must not exceed 4 MiB",
        "retryable": False,
    }
