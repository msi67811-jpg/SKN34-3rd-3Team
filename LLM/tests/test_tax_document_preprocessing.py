import pytest

from src.core.config import Settings
from src.data.contracts import TaxDocumentRow
from src.data.postgres_repository import (
    build_tax_document_content,
    clean_tax_document,
    prepare_tax_documents,
)


def test_clean_tax_document_uses_shared_text_cleaning() -> None:
    cleaned = clean_tax_document(
        {
            "id": 3,
            "title": "  소득세법&nbsp;제1조  ",
            "law_name": "소득세법\u200b",
            "content": "<p>납세 의무</p>\r\n  내용",
            "source": " https://example.com/law ",
        }
    )

    assert cleaned == {
        "tax_document_id": 3,
        "title": "소득세법 제1조",
        "law_name": "소득세법",
        "content": "납세 의무 내용",
        "source": "https://example.com/law",
    }
    assert build_tax_document_content(cleaned) == (
        "문서명: 소득세법 제1조\n법령명: 소득세법\n내용: 납세 의무 내용"
    )


def test_prepare_tax_documents_omits_empty_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows: list[TaxDocumentRow] = [
        {
            "id": 4,
            "title": None,
            "law_name": "부가가치세법",
            "content": "  과세 대상  ",
            "source": None,
        }
    ]
    monkeypatch.setattr(
        "src.data.postgres_repository.load_tax_documents", lambda _settings: rows
    )

    assert prepare_tax_documents(Settings(_env_file=None)) == [
        {
            "tax_document_id": 4,
            "content": "법령명: 부가가치세법\n내용: 과세 대상",
            "metadata": {"law_name": "부가가치세법"},
        }
    ]
