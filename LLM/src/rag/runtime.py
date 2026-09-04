import asyncio
from collections.abc import Callable
from typing import Literal

from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel

from src.models import get_embedding_model, get_llm
from src.vectorstores.base import VectorSearch


class RagIndexNotReadyError(RuntimeError):
    """프로세스 내부 RAG 인덱스 준비 전에 답변을 요청할 때 발생한다."""


class RagRuntime:
    """모델 호출 없이 FastAPI 프로세스의 RAG 인덱스 상태를 관리한다."""

    def __init__(
        self,
        *,
        embedding_factory: Callable[[], Embeddings] = get_embedding_model,
        llm_factory: Callable[[], BaseChatModel] = get_llm,
    ) -> None:
        """모델 팩토리와 비어 있는 RAG 실행 상태를 초기화한다.

        Args:
            embedding_factory: 인덱싱 시 Embedding 모델을 생성할 함수.
            llm_factory: 근거가 확보된 답변 생성 시 채팅 모델을 생성할 함수.
        """
        self.embedding_factory = embedding_factory
        self.llm_factory = llm_factory
        self.index_lock = asyncio.Lock()
        self._vector_search: VectorSearch | None = None
        self.document_count = 0
        self.chunk_count = 0
        self.index_source: Literal["cache", "embedding"] | None = None

    @property
    def ready(self) -> bool:
        """프로세스 메모리에 검색 가능한 인덱스가 있으면 True를 반환한다."""
        return self._vector_search is not None

    def set_index(
        self,
        vector_search: VectorSearch,
        *,
        document_count: int,
        chunk_count: int,
        index_source: Literal["cache", "embedding"],
    ) -> None:
        """검색 인덱스와 생성 출처·문서 수를 현재 프로세스 상태로 저장한다.

        Args:
            vector_search: 검색 가능한 In-memory Vector Search 구현체.
            document_count: 인덱스에 반영된 원본 문서 개수.
            chunk_count: 인덱스에 저장된 RAG Chunk 개수.
            index_source: 로컬 캐시 또는 신규 Embedding 중 인덱스 생성 출처.
        """
        self._vector_search = vector_search
        self.document_count = document_count
        self.chunk_count = chunk_count
        self.index_source = index_source

    def require_index(self) -> VectorSearch:
        """준비된 Vector Search를 반환하고 없으면 명확한 예외를 발생시킨다.

        Returns:
            현재 FastAPI 프로세스에 적재된 VectorSearch 구현체.

        Raises:
            RagIndexNotReadyError: 인덱스를 아직 준비하지 않았을 때.
        """
        if self._vector_search is None:
            raise RagIndexNotReadyError(
                "RAG index is not ready. Call POST /internal/rag/index first."
            )
        return self._vector_search
