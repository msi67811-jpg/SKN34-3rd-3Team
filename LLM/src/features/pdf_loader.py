from pathlib import Path

from langchain_core.documents import Document
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from src.data.contracts import DocumentCatalogEntry
from src.data.document_catalog import SOURCE_PDF_DIR


class PdfDocumentError(RuntimeError):
    """PDF를 RAG 문서로 변환할 수 없을 때 사용하는 기본 예외."""


class PdfDocumentNotFoundError(PdfDocumentError):
    """문서 catalog가 가리키는 PDF 파일이 없을 때 발생한다."""


class PdfTextNotFoundError(PdfDocumentError):
    """PDF에서 추출할 수 있는 텍스트가 없을 때 발생한다."""


def load_pdf_pages(
    entry: DocumentCatalogEntry,
    *,
    source_dir: Path = SOURCE_PDF_DIR,
) -> list[Document]:
    """PDF 한 개를 읽기 전용으로 열어 텍스트가 있는 페이지를 반환한다.

    Args:
        entry: PDF 파일명, 정책 ID와 제목이 정의된 문서 catalog 항목.
        source_dir: 원본 PDF가 위치한 읽기 전용 디렉터리.

    Returns:
        페이지 본문과 정책·출처 metadata를 담은 LangChain Document 목록.

    Raises:
        PdfDocumentNotFoundError: catalog에 지정된 PDF 파일이 없을 때.
        PdfTextNotFoundError: 모든 페이지에서 텍스트를 추출하지 못했을 때.
        PdfDocumentError: 경로가 잘못됐거나 PDF를 정상적으로 읽지 못했을 때.
    """
    file_name = entry["file_name"]
    if Path(file_name).name != file_name:
        raise PdfDocumentError("Catalog file_name must not contain a directory path")

    pdf_path = source_dir / file_name
    if not pdf_path.is_file():
        raise PdfDocumentNotFoundError(f"PDF not found: {file_name}")

    page_documents: list[Document] = []
    try:
        with pdf_path.open("rb") as pdf_stream:
            pdf_reader = PdfReader(pdf_stream)
            for page_number, pdf_page in enumerate(pdf_reader.pages, start=1):
                page_content = (pdf_page.extract_text() or "").strip()
                if not page_content:
                    continue
                page_documents.append(
                    Document(
                        page_content=page_content,
                        metadata={
                            "policy_id": entry["policy_id"],
                            "title": entry["title"],
                            "source": file_name,
                            "page": page_number,
                        },
                    )
                )
    except (OSError, PdfReadError) as exc:
        raise PdfDocumentError(f"Unable to read PDF: {file_name}") from exc

    if not page_documents:
        raise PdfTextNotFoundError(f"No extractable text in PDF: {file_name}")
    return page_documents
