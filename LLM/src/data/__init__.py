"""RAG 데이터 계약, 임시 catalog와 Mock 데이터 접근 함수."""

from src.data.document_catalog import get_document_catalog
from src.data.mock_repository import (
    MockDataNotFoundError,
    get_eligibility_result,
    get_policy,
    get_rag_chunks,
    get_user_profile,
)

__all__ = [
    "MockDataNotFoundError",
    "get_eligibility_result",
    "get_document_catalog",
    "get_policy",
    "get_rag_chunks",
    "get_user_profile",
]
