from fastapi.testclient import TestClient

from src.serving.app import app


client = TestClient(app)


def test_legal_basis_spec_endpoint() -> None:
    response = client.post(
        "/rag/legal-basis",
        json={
            "eligible": True,
            "conditions": {"age": 28, "region": "서울", "industry": "IT", "foundedAt": "2024-01-01"},
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert "legalBasis" in body
    assert any("28" in item for item in body["reasons"])


def test_summarize_announcement_spec_endpoint() -> None:
    response = client.post(
        "/rag/summarize-announcement",
        json={"rawContent": "청년 창업 지원금 공고 2026-09-01 ~ 2026-09-30 온라인 신청"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["benefit"]
    assert "period" in body


def test_ocr_receipt_spec_endpoint() -> None:
    response = client.post(
        "/ocr/receipt",
        files={"image": ("office-receipt.jpg", b"fake-bytes", "image/jpeg")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["vendor"]
    assert isinstance(body["amount"], int)
