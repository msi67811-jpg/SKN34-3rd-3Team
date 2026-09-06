from __future__ import annotations

from urllib.parse import urlparse

from langchain_core.embeddings import Embeddings

from src.data.contracts import RagChunk, VectorSearchResult


class PgVectorSearch:
    """Postgres pgvector에 Chunk를 저장하고 코사인 거리로 검색한다."""

    def __init__(self, embedding: Embeddings, database_url: str) -> None:
        self._embedding = embedding
        self._database_url = database_url
        self._ensure_table()

    def add_chunks(self, chunks: list[RagChunk]) -> list[str]:
        if not chunks:
            return []
        texts = [chunk["content"] for chunk in chunks]
        vectors = self._embedding.embed_documents(texts)
        conn = self._connect()
        try:
            with conn:
                with conn.cursor() as cur:
                    for chunk, vector in zip(chunks, vectors, strict=True):
                        cur.execute(
                            """
                            INSERT INTO rag_chunks
                                (chunk_id, policy_id, title, source, page, content, embedding)
                            VALUES (%s, %s, %s, %s, %s, %s, %s::vector)
                            ON CONFLICT (chunk_id) DO UPDATE SET
                                policy_id = EXCLUDED.policy_id,
                                title = EXCLUDED.title,
                                source = EXCLUDED.source,
                                page = EXCLUDED.page,
                                content = EXCLUDED.content,
                                embedding = EXCLUDED.embedding
                            """,
                            (
                                chunk["chunk_id"],
                                chunk["policy_id"],
                                chunk["title"],
                                chunk["source"],
                                chunk["page"],
                                chunk["content"],
                                _to_vector_literal(vector),
                            ),
                        )
        finally:
            conn.close()
        return [chunk["chunk_id"] for chunk in chunks]

    def count(self) -> int:
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM rag_chunks")
                return int(cur.fetchone()[0])
        finally:
            conn.close()

    def search(
        self,
        query: str,
        *,
        policy_id: int | None = None,
        top_k: int = 5,
    ) -> list[VectorSearchResult]:
        if not query.strip():
            raise ValueError("query must not be blank")
        if top_k < 1:
            raise ValueError("top_k must be at least 1")
        query_vector = _to_vector_literal(self._embedding.embed_query(query))
        sql = """
            SELECT chunk_id, policy_id, title, source, page, content,
                   1 - (embedding <=> %s::vector) AS score
            FROM rag_chunks
        """
        params: list = [query_vector]
        if policy_id is not None:
            sql += " WHERE policy_id = %s"
            params.append(policy_id)
        sql += " ORDER BY embedding <=> %s::vector LIMIT %s"
        params.extend([query_vector, top_k])
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()
        finally:
            conn.close()
        return [
            {
                "chunk_id": str(row[0]),
                "policy_id": int(row[1]),
                "title": str(row[2]),
                "source": str(row[3]),
                "page": int(row[4]),
                "content": str(row[5]),
                "score": float(row[6]),
            }
            for row in rows
        ]

    def _connect(self):
        import psycopg

        parsed = urlparse(self._database_url)
        conn = psycopg.connect(
            host=parsed.hostname or "127.0.0.1",
            port=parsed.port or 5432,
            user=parsed.username or "skn",
            password=parsed.password or "skn",
            dbname=(parsed.path or "/skn34").lstrip("/") or "skn34",
            connect_timeout=3,
        )
        return conn

    def _ensure_table(self) -> None:
        conn = self._connect()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS rag_chunks (
                            chunk_id TEXT PRIMARY KEY,
                            policy_id INT,
                            title TEXT,
                            source TEXT,
                            page INT,
                            content TEXT,
                            embedding vector(1536)
                        )
                        """
                    )
        finally:
            conn.close()


def _to_vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in values) + "]"
