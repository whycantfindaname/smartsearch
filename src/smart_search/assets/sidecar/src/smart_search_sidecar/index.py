from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

import numpy as np
from mistralai.search.toolkit.context import IngestContext, RetrievalContext
from mistralai.search.toolkit.document import ChunkType, Document
from mistralai.search.toolkit.search import (
    GrepMode,
    KeywordSearchQuery,
    KeywordStoreIndex,
    NavigationDirection,
    SearchResult,
    SearchResultChunk,
    SourceNotFoundError,
    VectorSearchQuery,
    VectorStoreIndex,
)
from pydantic import ConfigDict

from smart_search_sidecar.errors import IndexIdentityMismatch, SidecarError

_DEFAULT_INGEST_CONTEXT = IngestContext()
_DEFAULT_RETRIEVAL_CONTEXT = RetrievalContext()


class ArtifactRetrievalContext(RetrievalContext):
    model_config = ConfigDict(frozen=True)

    artifact_id: str
    exclude_ids: frozenset[str] = frozenset()


def _fts_terms(value: str) -> list[str]:
    return re.findall(r"\w+", value, flags=re.UNICODE)


def _fts_query(value: str, *, phrase: bool = False) -> str:
    terms = _fts_terms(value)
    if not terms:
        return ""
    escaped = [term.replace('"', '""') for term in terms]
    if phrase:
        return '"' + " ".join(escaped) + '"'
    return " AND ".join(f'"{term}"' for term in escaped)


class SQLiteIndexBackend:
    def __init__(self, path: Path, identity: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.identity = identity
        self.identity_mismatch: IndexIdentityMismatch | None = None
        self._create_schema()
        self._check_identity()

    def close(self) -> None:
        self.connection.close()

    def _create_schema(self) -> None:
        try:
            with self.connection:
                self.connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS index_meta (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS artifacts (
                        source_id TEXT PRIMARY KEY,
                        document_id TEXT NOT NULL,
                        metadata_json TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS chunks (
                        chunk_id TEXT PRIMARY KEY,
                        source_id TEXT NOT NULL,
                        locator TEXT NOT NULL,
                        start_offset INTEGER NOT NULL,
                        end_offset INTEGER NOT NULL,
                        chunk_type TEXT NOT NULL,
                        parent_ref TEXT,
                        content TEXT NOT NULL,
                        metadata_json TEXT NOT NULL,
                        embedding_json TEXT
                    );
                    CREATE INDEX IF NOT EXISTS chunks_source_position
                    ON chunks(source_id, start_offset, end_offset);
                    CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                        chunk_id UNINDEXED,
                        source_id UNINDEXED,
                        content,
                        tokenize='unicode61'
                    );
                    """
                )
        except sqlite3.OperationalError as exc:
            raise SidecarError(
                "FTS5_UNAVAILABLE", "SQLite FTS5 is required by the sidecar."
            ) from exc

    def _check_identity(self) -> None:
        encoded = json.dumps(self.identity, sort_keys=True, separators=(",", ":"))
        row = self.connection.execute(
            "SELECT value FROM index_meta WHERE key = 'index_identity'"
        ).fetchone()
        if row is None:
            with self.connection:
                self.connection.execute(
                    "INSERT INTO index_meta(key, value) VALUES ('index_identity', ?)",
                    (encoded,),
                )
            return
        actual = json.loads(row["value"])
        if actual != self.identity:
            self.identity_mismatch = IndexIdentityMismatch(self.identity, actual)

    def require_identity(self) -> None:
        if self.identity_mismatch is not None:
            raise self.identity_mismatch

    def _require_source(self, source_id: str) -> None:
        row = self.connection.execute(
            "SELECT 1 FROM artifacts WHERE source_id = ?",
            (source_id,),
        ).fetchone()
        if row is None:
            raise SourceNotFoundError(source_id)

    def replace_lexical_document(self, document: Document) -> None:
        self.require_identity()
        metadata_json = json.dumps(
            document.metadata.model_dump(mode="json"), sort_keys=True
        )
        with self.connection:
            self.connection.execute(
                "DELETE FROM chunks_fts WHERE source_id = ?", (document.source_id,)
            )
            self.connection.execute(
                "DELETE FROM chunks WHERE source_id = ?", (document.source_id,)
            )
            self.connection.execute(
                "INSERT OR REPLACE INTO artifacts(source_id, document_id, metadata_json) VALUES (?, ?, ?)",
                (document.source_id, document.id, metadata_json),
            )
            for chunk in document.chunks:
                chunk_metadata = chunk.metadata.model_dump(mode="json")
                chunk_metadata["document"] = document.metadata.model_dump(mode="json")
                encoded_metadata = json.dumps(chunk_metadata, sort_keys=True)
                self.connection.execute(
                    """
                    INSERT INTO chunks(
                        chunk_id, source_id, locator, start_offset, end_offset,
                        chunk_type, parent_ref, content, metadata_json, embedding_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
                    """,
                    (
                        chunk.id,
                        chunk.source_id,
                        chunk.locator,
                        chunk.start_offset,
                        chunk.end_offset,
                        chunk.chunk_type.value,
                        chunk.parent_ref,
                        chunk.content,
                        encoded_metadata,
                    ),
                )
                self.connection.execute(
                    "INSERT INTO chunks_fts(chunk_id, source_id, content) VALUES (?, ?, ?)",
                    (chunk.id, chunk.source_id, chunk.content),
                )

    def store_embeddings(self, document: Document) -> None:
        self.require_identity()
        with self.connection:
            for chunk in document.chunks:
                if chunk.embedding is None:
                    raise SidecarError(
                        "EMBEDDING_MISSING",
                        "Vector indexing requires every chunk embedding.",
                    )
                updated = self.connection.execute(
                    "UPDATE chunks SET embedding_json = ? WHERE chunk_id = ? AND source_id = ?",
                    (
                        json.dumps(chunk.embedding, separators=(",", ":")),
                        chunk.id,
                        document.source_id,
                    ),
                )
                if updated.rowcount != 1:
                    raise SidecarError(
                        "INDEX_INCONSISTENT",
                        "Vector index could not find its lexical chunk.",
                    )

    def delete_document(self, source_id: str) -> None:
        self.require_identity()
        with self.connection:
            self.connection.execute(
                "DELETE FROM chunks_fts WHERE source_id = ?", (source_id,)
            )
            self.connection.execute(
                "DELETE FROM chunks WHERE source_id = ?", (source_id,)
            )
            self.connection.execute(
                "DELETE FROM artifacts WHERE source_id = ?", (source_id,)
            )

    def _result_from_row(
        self,
        row: sqlite3.Row,
        *,
        score: float,
        include_metadata: bool = True,
        include_content: bool = True,
        distance: float | None = None,
    ) -> SearchResult:
        return SearchResult(
            chunk=SearchResultChunk(
                id=row["chunk_id"],
                source_id=row["source_id"],
                locator=row["locator"],
                start_offset=row["start_offset"],
                end_offset=row["end_offset"],
                chunk_type=ChunkType(row["chunk_type"]),
                parent_ref=row["parent_ref"],
                content=row["content"] if include_content else "",
                metadata=json.loads(row["metadata_json"]) if include_metadata else {},
            ),
            score=score,
            distance=distance,
        )

    def keyword_search(
        self,
        query: KeywordSearchQuery,
        context: ArtifactRetrievalContext,
    ) -> list[SearchResult]:
        self.require_identity()
        self._require_source(context.artifact_id)
        expression = _fts_query(query.query)
        if not expression:
            return []
        excluded = set(query.exclude_ids) | set(context.exclude_ids)
        params: list[Any] = [expression, context.artifact_id]
        exclusion_sql = ""
        if excluded:
            placeholders = ",".join("?" for _ in excluded)
            exclusion_sql = f" AND c.chunk_id NOT IN ({placeholders})"
            params.extend(sorted(excluded))
        params.append(query.top_k)
        rows = self.connection.execute(
            f"""
            SELECT c.*, bm25(chunks_fts) AS lexical_rank
            FROM chunks_fts
            JOIN chunks AS c ON c.chunk_id = chunks_fts.chunk_id
            WHERE chunks_fts MATCH ? AND c.source_id = ? {exclusion_sql}
            ORDER BY lexical_rank ASC, c.start_offset ASC
            LIMIT ?
            """,
            params,
        ).fetchall()
        return [
            self._result_from_row(
                row,
                score=1.0 / (1.0 + abs(float(row["lexical_rank"]))),
                include_metadata=query.include_metadata,
                include_content=query.include_content,
            )
            for row in rows
        ]

    def vector_search(
        self,
        query: VectorSearchQuery,
        context: ArtifactRetrievalContext,
    ) -> list[SearchResult]:
        self.require_identity()
        self._require_source(context.artifact_id)
        query_vector = np.asarray(query.embedding, dtype=np.float32)
        expected_dimension = int(self.identity["embedding_dimension"])
        if query_vector.shape != (expected_dimension,):
            raise SidecarError(
                "EMBEDDING_DIMENSION_MISMATCH",
                "Query embedding does not match the configured index identity.",
            )
        excluded = set(query.exclude_ids) | set(context.exclude_ids)
        rows = self.connection.execute(
            "SELECT * FROM chunks WHERE source_id = ? AND embedding_json IS NOT NULL",
            (context.artifact_id,),
        ).fetchall()
        candidates = [row for row in rows if row["chunk_id"] not in excluded]
        if not candidates:
            return []
        matrix = np.asarray(
            [json.loads(row["embedding_json"]) for row in candidates], dtype=np.float32
        )
        if matrix.ndim != 2 or matrix.shape[1] != expected_dimension:
            raise SidecarError(
                "INDEX_INCONSISTENT", "Stored vector matrix has an invalid dimension."
            )
        if self.identity["embedding_normalization"] == "l2":
            scores = matrix @ query_vector
        else:
            query_norm = np.linalg.norm(query_vector)
            row_norms = np.linalg.norm(matrix, axis=1)
            denominator = row_norms * query_norm
            scores = np.divide(
                matrix @ query_vector,
                denominator,
                out=np.zeros_like(row_norms),
                where=denominator != 0,
            )
        order = np.argsort(-scores)[: query.top_k]
        return [
            self._result_from_row(
                candidates[int(index)],
                score=float(scores[int(index)]),
                distance=float(1.0 - scores[int(index)]),
                include_metadata=query.include_metadata,
                include_content=query.include_content,
            )
            for index in order
        ]

    def get_chunk(self, chunk_id: str) -> SearchResult | None:
        self.require_identity()
        row = self.connection.execute(
            "SELECT * FROM chunks WHERE chunk_id = ?", (chunk_id,)
        ).fetchone()
        return None if row is None else self._result_from_row(row, score=0.0)

    def navigate(
        self,
        source_id: str,
        start_offset: int,
        end_offset: int,
        direction: NavigationDirection,
        *,
        top_k: int,
        content_type: ChunkType,
    ) -> list[SearchResult]:
        self.require_identity()
        self._require_source(source_id)
        if direction == NavigationDirection.NEXT:
            rows = self.connection.execute(
                """
                SELECT * FROM chunks
                WHERE source_id = ? AND chunk_type = ? AND start_offset >= ?
                ORDER BY start_offset ASC LIMIT ?
                """,
                (source_id, content_type.value, end_offset, top_k),
            ).fetchall()
        else:
            rows = self.connection.execute(
                """
                SELECT * FROM chunks
                WHERE source_id = ? AND chunk_type = ? AND end_offset <= ?
                ORDER BY end_offset DESC LIMIT ?
                """,
                (source_id, content_type.value, start_offset, top_k),
            ).fetchall()[::-1]
        return [self._result_from_row(row, score=0.0) for row in rows]

    def read(
        self,
        source_id: str,
        start_offset: int | None,
        end_offset: int | None,
        *,
        content_type: ChunkType,
        top_k: int,
    ) -> list[SearchResult]:
        self.require_identity()
        self._require_source(source_id)
        clauses = ["source_id = ?", "chunk_type = ?"]
        params: list[Any] = [source_id, content_type.value]
        if start_offset is not None:
            clauses.append("start_offset >= ?")
            params.append(start_offset)
        if end_offset is not None:
            clauses.append("end_offset <= ?")
            params.append(end_offset)
        params.append(top_k)
        rows = self.connection.execute(
            f"SELECT * FROM chunks WHERE {' AND '.join(clauses)} ORDER BY start_offset ASC LIMIT ?",
            params,
        ).fetchall()
        return [self._result_from_row(row, score=0.0) for row in rows]

    def grep(
        self,
        source_id: str,
        pattern: str,
        *,
        mode: GrepMode,
        content_type: ChunkType,
        top_k: int,
    ) -> list[SearchResult]:
        self.require_identity()
        self._require_source(source_id)
        expression = _fts_query(pattern, phrase=mode == GrepMode.PHRASE)
        if not expression:
            return []
        rows = self.connection.execute(
            """
            SELECT c.* FROM chunks_fts
            JOIN chunks AS c ON c.chunk_id = chunks_fts.chunk_id
            WHERE chunks_fts MATCH ? AND c.source_id = ? AND c.chunk_type = ?
            ORDER BY c.start_offset ASC LIMIT ?
            """,
            (expression, source_id, content_type.value, top_k),
        ).fetchall()
        return [self._result_from_row(row, score=0.0) for row in rows]


def _artifact_context(context: RetrievalContext) -> ArtifactRetrievalContext:
    if not isinstance(context, ArtifactRetrievalContext):
        raise SidecarError(
            "ADAPTER_CONTEXT_REQUIRED",
            "Project index adapter requires artifact-scoped context.",
        )
    return context


class SQLiteKeywordIndex(KeywordStoreIndex):
    def __init__(self, backend: SQLiteIndexBackend) -> None:
        self.backend = backend

    async def index_document(
        self, document: Document, context: IngestContext = _DEFAULT_INGEST_CONTEXT
    ) -> None:
        del context
        self.backend.replace_lexical_document(document)

    async def delete_document(
        self, doc_id: str, context: IngestContext = _DEFAULT_INGEST_CONTEXT
    ) -> None:
        del context
        self.backend.delete_document(doc_id)

    async def search(
        self,
        query: KeywordSearchQuery,
        context: RetrievalContext = _DEFAULT_RETRIEVAL_CONTEXT,
    ) -> list[SearchResult]:
        return self.backend.keyword_search(query, _artifact_context(context))


class SQLiteVectorIndex(VectorStoreIndex):
    def __init__(self, backend: SQLiteIndexBackend) -> None:
        self.backend = backend

    async def index_document(
        self, document: Document, context: IngestContext = _DEFAULT_INGEST_CONTEXT
    ) -> None:
        del context
        self.backend.store_embeddings(document)

    async def delete_document(
        self, doc_id: str, context: IngestContext = _DEFAULT_INGEST_CONTEXT
    ) -> None:
        del context
        self.backend.delete_document(doc_id)

    async def search(
        self,
        query: VectorSearchQuery,
        context: RetrievalContext = _DEFAULT_RETRIEVAL_CONTEXT,
    ) -> list[SearchResult]:
        return self.backend.vector_search(query, _artifact_context(context))


class SQLiteNavigableIndex:
    """Structural implementation of Search Toolkit's NavigableIndex protocol."""

    def __init__(self, backend: SQLiteIndexBackend) -> None:
        self.backend = backend

    async def navigate(
        self,
        source_id: str,
        start_offset: int,
        end_offset: int,
        direction: NavigationDirection,
        *,
        top_k: int = 1,
        content_type: ChunkType = ChunkType.CONTENT,
        context: RetrievalContext = _DEFAULT_RETRIEVAL_CONTEXT,
    ) -> list[SearchResult]:
        del context
        return self.backend.navigate(
            source_id,
            start_offset,
            end_offset,
            direction,
            top_k=top_k,
            content_type=content_type,
        )

    async def read(
        self,
        source_id: str,
        start_offset: int | None,
        end_offset: int | None,
        *,
        content_type: ChunkType = ChunkType.CONTENT,
        top_k: int = 20,
        context: RetrievalContext = _DEFAULT_RETRIEVAL_CONTEXT,
    ) -> list[SearchResult]:
        del context
        return self.backend.read(
            source_id,
            start_offset,
            end_offset,
            content_type=content_type,
            top_k=top_k,
        )

    async def get_chunk(
        self,
        chunk_id: str,
        *,
        context: RetrievalContext = _DEFAULT_RETRIEVAL_CONTEXT,
    ) -> SearchResult | None:
        del context
        return self.backend.get_chunk(chunk_id)

    async def grep(
        self,
        source_id: str,
        pattern: str,
        *,
        mode: GrepMode = GrepMode.PHRASE,
        content_type: ChunkType = ChunkType.CONTENT,
        top_k: int = 5,
        context: RetrievalContext = _DEFAULT_RETRIEVAL_CONTEXT,
    ) -> list[SearchResult]:
        del context
        return self.backend.grep(
            source_id,
            pattern,
            mode=mode,
            content_type=content_type,
            top_k=top_k,
        )
