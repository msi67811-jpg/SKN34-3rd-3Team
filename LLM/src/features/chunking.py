from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.data.contracts import RagChunk


KOREAN_DOCUMENT_SEPARATORS = ["\n\n", "\n", "다. ", "요. ", ". ", " ", ""]


def split_pdf_pages(
    pages: list[Document],
    *,
    chunk_size: int,
    chunk_overlap: int,
) -> list[RagChunk]:
    """PDF 페이지를 출처 metadata가 보존된 RAG Chunk로 분할한다.

    Args:
        pages: PDF 페이지 본문과 정책·출처 metadata를 담은 Document 목록.
        chunk_size: Chunk 하나에 허용할 최대 문자 수.
        chunk_overlap: 인접한 Chunk가 공유할 문자 수.

    Returns:
        결정적인 chunk_id와 원본 페이지 metadata가 포함된 RAG Chunk 목록.

    Raises:
        ValueError: Chunk 설정이 잘못됐거나 페이지 필수 metadata가 없을 때.
    """
    _validate_chunk_settings(chunk_size, chunk_overlap)
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=KOREAN_DOCUMENT_SEPARATORS,
        length_function=len,
    )

    rag_chunks: list[RagChunk] = []
    for page_document in pages:
        policy_id, title, source, page_number = _extract_page_metadata(page_document)
        chunk_contents = [
            chunk_content.strip()
            for chunk_content in text_splitter.split_text(page_document.page_content)
            if chunk_content.strip()
        ]
        for chunk_number, chunk_content in enumerate(chunk_contents, start=1):
            rag_chunks.append(
                {
                    "chunk_id": (
                        f"policy-{policy_id}-page-{page_number}-chunk-{chunk_number}"
                    ),
                    "policy_id": policy_id,
                    "title": title,
                    "source": source,
                    "page": page_number,
                    "content": chunk_content,
                }
            )
    return rag_chunks


def _validate_chunk_settings(chunk_size: int, chunk_overlap: int) -> None:
    """Chunk 크기와 중첩 범위가 유효한지 검사한다.

    Args:
        chunk_size: Chunk 하나에 허용할 최대 문자 수.
        chunk_overlap: 인접한 Chunk가 공유할 문자 수.

    Raises:
        ValueError: 크기가 1보다 작거나 중첩이 음수 또는 크기 이상일 때.
    """
    if chunk_size < 1:
        raise ValueError("chunk_size must be at least 1")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap must not be negative")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")


def _extract_page_metadata(document: Document) -> tuple[int, str, str, int]:
    """페이지 Document에서 필수 정책·출처 metadata를 추출한다.

    Args:
        document: metadata를 추출할 PDF 페이지 Document.

    Returns:
        policy_id, 문서 제목, 출처 파일명, 페이지 번호 순서의 tuple.

    Raises:
        ValueError: 필수 metadata가 하나 이상 없을 때.
    """
    required_fields = ("policy_id", "title", "source", "page")
    missing_fields = [
        field_name
        for field_name in required_fields
        if field_name not in document.metadata
    ]
    if missing_fields:
        raise ValueError(f"Missing page metadata: {', '.join(missing_fields)}")

    metadata = document.metadata
    return (
        int(metadata["policy_id"]),
        str(metadata["title"]),
        str(metadata["source"]),
        int(metadata["page"]),
    )
