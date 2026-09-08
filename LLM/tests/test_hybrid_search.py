import pytest

from src.data.contracts import RagChunk, VectorSearchResult
from src.vectorstores.hybrid import (
    BM25Search,
    HybridSearch,
    reciprocal_rank_fusion,
)


CHUNKS: list[RagChunk] = [
    {
        "chunk_id": "policy-101-chunk-1",
        "policy_id": 101,
        "title": "초기창업 지원",
        "source": "policy-101.pdf",
        "page": 1,
        "content": "초기 창업기업에 사업화 자금과 시장 진입을 지원합니다.",
    },
    {
        "chunk_id": "policy-110-chunk-1",
        "policy_id": 110,
        "title": "온라인 판로 지원",
        "source": "policy-110.pdf",
        "page": 2,
        "content": "청년 소상공인의 온라인 광고와 상세페이지 제작을 지원합니다.",
    },
    {
        "chunk_id": "policy-120-chunk-1",
        "policy_id": 120,
        "title": "임차보증금 이자 지원",
        "source": "policy-120.pdf",
        "page": 3,
        "content": "무주택 청년의 임차보증금 대출이자를 지원합니다.",
    },
]


class FakeDenseSearch:
    """미리 정한 순위로 결과를 반환하는 Hybrid 검색용 Dense 대역."""

    def __init__(self, results: list[VectorSearchResult]) -> None:
        """Dense 결과를 저장한다.

        Args:
            results: Hybrid Search에 전달할 순위가 있는 Dense 결과.
        """
        self.results = results

    def add_chunks(self, chunks: list[RagChunk]) -> list[str]:
        """테스트 계약을 위해 입력 Chunk ID를 그대로 반환한다."""
        return [chunk["chunk_id"] for chunk in chunks]

    def search(
        self,
        _query: str,
        *,
        policy_id: int | None = None,
        top_k: int = 5,
    ) -> list[VectorSearchResult]:
        """정책 필터와 개수 제한을 적용한 고정 Dense 결과를 반환한다."""
        return [
            result
            for result in self.results
            if policy_id is None or result["policy_id"] == policy_id
        ][:top_k]


def test_bm25_finds_keyword_match_and_preserves_metadata() -> None:
    bm25_search = BM25Search(CHUNKS)

    results = bm25_search.search("온라인 광고 상세페이지", top_k=2)

    assert results[0] == {
        **CHUNKS[1],
        "score": results[0]["score"],
    }
    assert results[0]["score"] > 0


def test_bm25_applies_policy_filter() -> None:
    bm25_search = BM25Search(CHUNKS)

    results = bm25_search.search("청년 지원", policy_id=120, top_k=3)

    assert [result["chunk_id"] for result in results] == [
        "policy-120-chunk-1"
    ]


def test_rrf_accumulates_duplicate_chunk_scores() -> None:
    dense_results = [
        _search_result(CHUNKS[0], score=0.9),
        _search_result(CHUNKS[1], score=0.8),
    ]
    bm25_results = [
        _search_result(CHUNKS[2], score=12.0),
        _search_result(CHUNKS[0], score=10.0),
    ]

    results = reciprocal_rank_fusion(
        [dense_results, bm25_results],
        rrf_k=60,
        top_k=3,
    )

    expected_accumulated_score = (1 / 61 + 1 / 62) / (2 / 61)
    assert results[0]["chunk_id"] == CHUNKS[0]["chunk_id"]
    assert results[0]["score"] == pytest.approx(expected_accumulated_score)
    assert results[0]["score"] > results[1]["score"]


def test_hybrid_search_returns_existing_result_schema() -> None:
    hybrid_search = HybridSearch(
        dense_search=FakeDenseSearch(
            [
                _search_result(CHUNKS[0], score=0.9),
                _search_result(CHUNKS[1], score=0.8),
            ]
        ),
        chunks=CHUNKS,
        dense_candidate_k=3,
        bm25_candidate_k=3,
        rrf_k=60,
    )

    results = hybrid_search.search("온라인 광고 상세페이지", top_k=2)

    assert len(results) == 2
    assert set(results[0]) == {
        "chunk_id",
        "policy_id",
        "title",
        "source",
        "page",
        "content",
        "score",
    }
    assert results[0]["chunk_id"] == CHUNKS[1]["chunk_id"]


def _search_result(chunk: RagChunk, *, score: float) -> VectorSearchResult:
    """테스트 Chunk를 지정한 점수의 검색 결과로 변환한다.

    Args:
        chunk: 변환할 RAG Chunk.
        score: Dense 또는 BM25를 흉내 낼 검색 점수.

    Returns:
        기존 Retriever schema와 같은 테스트 검색 결과.
    """
    return {**chunk, "score": score}
