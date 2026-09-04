import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from langchain_core.embeddings import Embeddings

from src.core.config import Settings
from src.data.contracts import DocumentCatalogEntry
from src.data.document_catalog import SOURCE_PDF_DIR
from src.features.indexing import prepare_document_chunks
from src.vectorstores.in_memory import InMemoryVectorSearch


INDEX_CACHE_VERSION = 1


@dataclass(frozen=True, slots=True)
class IndexManifest:
    """로컬 Vector 캐시의 유효성 검증에 필요한 상태 정보."""

    version: int
    embedding_model: str
    chunk_size: int
    chunk_overlap: int
    chunk_count: int
    catalog: list[DocumentCatalogEntry]
    source_hashes: dict[str, str]


@dataclass(frozen=True, slots=True)
class CachedVectorIndex:
    """로드 또는 생성된 Vector 인덱스와 캐시 사용 결과."""

    vector_search: InMemoryVectorSearch
    document_count: int
    chunk_count: int
    loaded_from_cache: bool


def load_or_build_document_index(
    *,
    embedding: Embeddings,
    settings: Settings,
    catalog: list[DocumentCatalogEntry],
    source_dir: Path = SOURCE_PDF_DIR,
    force: bool = False,
) -> CachedVectorIndex:
    """유효한 로컬 인덱스를 로드하거나 문서를 한 번 임베딩해 저장한다.

    Args:
        embedding: 캐시 로드 후 Query Embedding 또는 신규 문서 Embedding에 사용할
            모델 구현체.
        settings: Embedding 모델명, Chunk 설정과 캐시 경로를 담은 설정.
        catalog: 인덱싱할 PDF와 정책 ID의 연결 정보.
        source_dir: 원본 PDF가 위치한 읽기 전용 디렉터리.
        force: True이면 유효한 캐시도 무시하고 문서를 다시 임베딩한다.

    Returns:
        검색 구현체, 문서·Chunk 수와 캐시 사용 여부를 담은 결과.

    Raises:
        FileNotFoundError: catalog의 PDF 파일이 없을 때.
        PdfDocumentError: PDF를 읽거나 텍스트로 변환하지 못했을 때.

    Notes:
        원본 PDF hash, 모델명, Chunk 설정, catalog 중 하나라도 달라지면 캐시를
        무효화한다. 신규 인덱스의 `add_chunks()`에서만 문서 Embedding이 발생한다.
    """
    vector_cache_path = settings.resolved_vector_index_cache_path
    manifest_path = _manifest_path(vector_cache_path)
    embedding_model_name = _embedding_identity(embedding, settings)
    current_source_hashes = _source_hashes(catalog, source_dir)

    if not force:
        stored_manifest = _read_manifest(manifest_path)
        if _cache_is_valid(
            stored_manifest,
            cache_path=vector_cache_path,
            embedding_model=embedding_model_name,
            settings=settings,
            catalog=catalog,
            source_hashes=current_source_hashes,
        ):
            try:
                cached_vector_search = InMemoryVectorSearch.load(
                    vector_cache_path,
                    embedding=embedding,
                )
            except (OSError, TypeError, ValueError, json.JSONDecodeError):
                pass
            else:
                return CachedVectorIndex(
                    vector_search=cached_vector_search,
                    document_count=len(catalog),
                    chunk_count=stored_manifest.chunk_count,
                    loaded_from_cache=True,
                )

    rag_chunks = prepare_document_chunks(
        catalog=catalog,
        source_dir=source_dir,
        settings=settings,
    )
    new_vector_search = InMemoryVectorSearch(embedding=embedding)
    # 캐시 생성 흐름에서 문서 Embedding이 발생하는 유일한 지점이다.
    new_vector_search.add_chunks(rag_chunks)

    new_manifest = IndexManifest(
        version=INDEX_CACHE_VERSION,
        embedding_model=embedding_model_name,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        chunk_count=len(rag_chunks),
        catalog=catalog,
        source_hashes=current_source_hashes,
    )
    _write_cache(
        new_vector_search,
        new_manifest,
        vector_cache_path,
        manifest_path,
    )
    return CachedVectorIndex(
        vector_search=new_vector_search,
        document_count=len(catalog),
        chunk_count=len(rag_chunks),
        loaded_from_cache=False,
    )


def _cache_is_valid(
    manifest: IndexManifest | None,
    *,
    cache_path: Path,
    embedding_model: str,
    settings: Settings,
    catalog: list[DocumentCatalogEntry],
    source_hashes: dict[str, str],
) -> bool:
    """현재 문서·설정과 저장된 manifest가 완전히 일치하는지 확인한다.

    Args:
        manifest: 로컬에서 읽은 캐시 manifest. 읽을 수 없으면 None.
        cache_path: 직렬화된 Vector 인덱스 파일 경로.
        embedding_model: 현재 설정된 Embedding 모델 식별자.
        settings: 현재 Chunk 크기와 중첩 설정.
        catalog: 현재 PDF-policy_id 연결 정보.
        source_hashes: 현재 원본 PDF별 SHA-256.

    Returns:
        기존 캐시를 안전하게 재사용할 수 있으면 True, 아니면 False.
    """
    return (
        cache_path.is_file()
        and manifest is not None
        and manifest.version == INDEX_CACHE_VERSION
        and manifest.embedding_model == embedding_model
        and manifest.chunk_size == settings.chunk_size
        and manifest.chunk_overlap == settings.chunk_overlap
        and manifest.catalog == catalog
        and manifest.source_hashes == source_hashes
    )


def _embedding_identity(embedding: Embeddings, settings: Settings) -> str:
    """캐시 검증에 사용할 Embedding 모델 식별자를 반환한다."""
    configured_name = settings.embedding_model.strip()
    return configured_name or repr(embedding)


def _source_hashes(
    catalog: list[DocumentCatalogEntry],
    source_dir: Path,
) -> dict[str, str]:
    """원본을 수정하지 않고 catalog PDF별 SHA-256을 계산한다.

    Args:
        catalog: hash를 계산할 PDF catalog.
        source_dir: 원본 PDF가 위치한 읽기 전용 디렉터리.

    Returns:
        PDF 파일명을 key, SHA-256 문자열을 value로 갖는 Dictionary.

    Raises:
        FileNotFoundError: catalog에 정의된 PDF가 없을 때.
    """
    source_hashes: dict[str, str] = {}
    for document_entry in catalog:
        source_path = source_dir / document_entry["file_name"]
        if not source_path.is_file():
            raise FileNotFoundError(f"PDF not found: {document_entry['file_name']}")
        sha256_digest = hashlib.sha256()
        with source_path.open("rb") as source_file:
            for file_block in iter(lambda: source_file.read(1024 * 1024), b""):
                sha256_digest.update(file_block)
        source_hashes[document_entry["file_name"]] = sha256_digest.hexdigest()
    return source_hashes


def _manifest_path(cache_path: Path) -> Path:
    """Vector 캐시 경로에 대응하는 manifest 경로를 반환한다."""
    return cache_path.with_suffix(".manifest.json")


def _read_manifest(path: Path) -> IndexManifest | None:
    """manifest를 읽고 손상됐거나 형식이 맞지 않으면 None을 반환한다."""
    if not path.is_file():
        return None
    try:
        manifest_data = json.loads(path.read_text(encoding="utf-8"))
        return IndexManifest(**manifest_data)
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return None


def _write_cache(
    vector_search: InMemoryVectorSearch,
    manifest: IndexManifest,
    cache_path: Path,
    manifest_path: Path,
) -> None:
    """Vector 인덱스와 manifest를 임시 파일에 쓴 뒤 원자적으로 교체한다.

    Args:
        vector_search: 직렬화할 In-memory Vector Search 구현체.
        manifest: 캐시 검증 정보를 담은 manifest.
        cache_path: 최종 Vector 인덱스 파일 경로.
        manifest_path: 최종 manifest 파일 경로.
    """
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_cache = cache_path.with_suffix(f"{cache_path.suffix}.tmp")
    temporary_manifest = manifest_path.with_suffix(f"{manifest_path.suffix}.tmp")

    vector_search.save(temporary_cache)
    temporary_manifest.write_text(
        json.dumps(asdict(manifest), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary_cache.replace(cache_path)
    temporary_manifest.replace(manifest_path)
