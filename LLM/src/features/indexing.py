from pathlib import Path

from langchain_core.embeddings import Embeddings

from src.core.config import Settings, get_settings
from src.data import get_document_catalog, get_rag_chunks
from src.data.contracts import DocumentCatalogEntry, RagChunk
from src.data.document_catalog import SOURCE_PDF_DIR
from src.features.chunking import split_pdf_pages
from src.features.pdf_loader import load_pdf_pages
from src.models import get_embedding_model
from src.vectorstores.base import VectorSearch
from src.vectorstores.in_memory import InMemoryVectorSearch


def build_mock_vector_index(
    embedding: Embeddings | None = None,
) -> VectorSearch:
    """Mock Chunk를 임베딩해 검색 가능한 메모리 인덱스를 생성한다.

    Args:
        embedding: 테스트에서 주입할 Embedding 구현체. None이면 환경설정에 지정된
            실제 OpenAI Embedding 모델을 사용한다.

    Returns:
        Mock Chunk가 적재된 VectorSearch 구현체.
    """
    return build_vector_index(get_rag_chunks(), embedding=embedding)


def prepare_document_chunks(
    *,
    catalog: list[DocumentCatalogEntry] | None = None,
    source_dir: Path = SOURCE_PDF_DIR,
    settings: Settings | None = None,
) -> list[RagChunk]:
    """catalog의 PDF를 불러와 metadata가 포함된 RAG Chunk로 변환한다.

    Args:
        catalog: 처리할 PDF와 정책 ID 목록. None이면 기본 catalog를 사용한다.
        source_dir: 원본 PDF가 위치한 읽기 전용 디렉터리.
        settings: Chunk 크기와 중첩 설정. None이면 환경설정을 사용한다.

    Returns:
        모든 PDF의 페이지를 분할한 RAG Chunk 목록.
    """
    settings_config = settings or get_settings()
    document_catalog = catalog if catalog is not None else get_document_catalog()

    rag_chunks: list[RagChunk] = []
    for document_entry in document_catalog:
        page_documents = load_pdf_pages(document_entry, source_dir=source_dir)
        rag_chunks.extend(
            split_pdf_pages(
                page_documents,
                chunk_size=settings_config.chunk_size,
                chunk_overlap=settings_config.chunk_overlap,
            )
        )
    return rag_chunks


def build_document_vector_index(
    embedding: Embeddings | None = None,
    *,
    catalog: list[DocumentCatalogEntry] | None = None,
    source_dir: Path = SOURCE_PDF_DIR,
    settings: Settings | None = None,
) -> VectorSearch:
    """catalog PDF를 로드·분할·임베딩해 메모리 인덱스를 생성한다.

    Args:
        embedding: Chunk를 벡터화할 Embedding 구현체. None이면 실제 설정 모델.
        catalog: 처리할 문서 catalog. None이면 기본 catalog.
        source_dir: 원본 PDF가 위치한 읽기 전용 디렉터리.
        settings: Chunking에 사용할 설정. None이면 환경설정.

    Returns:
        실제 PDF Chunk가 적재된 VectorSearch 구현체.
    """
    rag_chunks = prepare_document_chunks(
        catalog=catalog,
        source_dir=source_dir,
        settings=settings,
    )
    return build_vector_index(rag_chunks, embedding=embedding)


def build_vector_index(
    chunks: list[RagChunk],
    *,
    embedding: Embeddings | None = None,
) -> VectorSearch:
    """RAG Chunk를 임베딩해 새로운 In-memory Vector 인덱스를 생성한다.

    Args:
        chunks: 임베딩하고 적재할 RAG Chunk 목록.
        embedding: 사용할 Embedding 구현체. None이면 환경설정의 실제 모델.

    Returns:
        Chunk가 적재되어 검색 가능한 VectorSearch 구현체.

    Raises:
        ValueError: 적재할 Chunk가 하나도 없을 때.

    Notes:
        `add_chunks()` 호출에서 문서 Embedding API 요청이 발생할 수 있다.
    """
    if not chunks:
        raise ValueError("At least one RAG chunk is required to build an index")
    embedding_model = embedding or get_embedding_model()
    vector_search = InMemoryVectorSearch(embedding=embedding_model)
    # 이 호출이 내부에서 embedding.embed_documents()를 실행한다.
    vector_search.add_chunks(chunks)
    return vector_search
