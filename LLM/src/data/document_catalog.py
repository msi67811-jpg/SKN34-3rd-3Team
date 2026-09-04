from copy import deepcopy
from pathlib import Path

from src.data.contracts import DocumentCatalogEntry


SOURCE_PDF_DIR = Path(__file__).resolve().parent

# Backend/DB가 문서-정책 관계를 제공하기 전까지 사용하는 임시 mapping이다.
_DOCUMENT_CATALOG: tuple[DocumentCatalogEntry, ...] = (
    {
        "policy_id": 103,
        "title": "청년 직무경험 지원사업 공고",
        "file_name": "01_청년_직무경험_지원사업_공고.pdf",
    },
    {
        "policy_id": 102,
        "title": "청년 주거이전비 지원사업 공고",
        "file_name": "02_청년_주거이전비_지원사업_공고.pdf",
    },
    {
        "policy_id": 101,
        "title": "지역청년 초기창업 사업화지원 공고",
        "file_name": "03_지역청년_초기창업_사업화지원_공고.pdf",
    },
    {
        "policy_id": 104,
        "title": "중소기업 청년근속장려금 지원사업 공고",
        "file_name": "04_중소기업_청년근속장려금_지원사업_공고.pdf",
    },
    {
        "policy_id": 105,
        "title": "청년 문화활동비 지원사업 공고",
        "file_name": "05_청년_문화활동비_지원사업_공고.pdf",
    },
)


def get_document_catalog() -> list[DocumentCatalogEntry]:
    """공용 원본을 변경할 수 없도록 문서 catalog 복사본을 반환한다.

    Returns:
        원본 PDF 파일명, 제목, 임시 policy_id를 담은 catalog 목록.
    """
    return deepcopy(list(_DOCUMENT_CATALOG))
