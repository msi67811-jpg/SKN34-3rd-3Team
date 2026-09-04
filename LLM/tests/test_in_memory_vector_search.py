import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding

from src.data import get_rag_chunks
from src.features import build_mock_vector_index
from src.vectorstores import InMemoryVectorSearch


def test_index_embeds_and_returns_the_identical_chunk_first() -> None:
    chunks = get_rag_chunks()
    index = build_mock_vector_index(DeterministicFakeEmbedding(size=32))

    results = index.search(chunks[0]["content"], top_k=2)

    assert results[0]["chunk_id"] == chunks[0]["chunk_id"]
    assert results[0]["score"] == pytest.approx(1.0)
    assert results[0]["score"] >= results[1]["score"]


def test_search_filters_chunks_by_policy_id() -> None:
    index = build_mock_vector_index(DeterministicFakeEmbedding(size=32))

    results = index.search("지원 대상과 신청 조건", policy_id=101, top_k=5)

    assert len(results) == 2
    assert all(result["policy_id"] == 101 for result in results)


def test_search_returns_empty_list_for_unknown_policy() -> None:
    index = build_mock_vector_index(DeterministicFakeEmbedding(size=32))

    assert index.search("지원 조건", policy_id=999) == []


def test_add_chunks_does_not_mutate_mock_data() -> None:
    chunks = get_rag_chunks(policy_id=101)
    original_chunks = get_rag_chunks(policy_id=101)
    index = InMemoryVectorSearch(DeterministicFakeEmbedding(size=16))

    ids = index.add_chunks(chunks)

    assert ids == [chunk["chunk_id"] for chunk in original_chunks]
    assert chunks == original_chunks


@pytest.mark.parametrize("query", ["", "   "])
def test_blank_query_is_rejected(query: str) -> None:
    index = build_mock_vector_index(DeterministicFakeEmbedding(size=16))

    with pytest.raises(ValueError, match="query must not be blank"):
        index.search(query)


def test_invalid_top_k_is_rejected() -> None:
    index = build_mock_vector_index(DeterministicFakeEmbedding(size=16))

    with pytest.raises(ValueError, match="top_k must be at least 1"):
        index.search("지원 조건", top_k=0)
