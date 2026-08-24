from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

from mistralai.search.toolkit.document import (
    Document,
    DocumentChunk,
    DocumentChunkMetadata,
    DocumentMetadata,
    compute_char_locator,
    compute_id,
)
from mistralai.search.toolkit.ingestion import File
from mistralai.search.toolkit.ingestion.extractors.base import DocumentExtractor
from mistralai.search.toolkit.ingestion.pipelines import Pipeline
from mistralai.search.toolkit.ingestion.text_splitters import (
    CharacterTextSplitter,
    MarkdownTextSplitter,
    MarkdownTextSplitterConfig,
    TextSplitter,
)
from mistralai.search.toolkit.retrieval import QueryEngine
from mistralai.search.toolkit.retrieval.retrievers import (
    KeywordRetriever,
    VectorRetriever,
)
from mistralai.search.toolkit.search import (
    GrepMode,
    NavigableIndex,
    NavigationDirection,
    SearchResult,
)

from smart_search_sidecar import __version__
from smart_search_sidecar.config import TOOLKIT_VERSION, SidecarConfig
from smart_search_sidecar.embedding import OpenAICompatibleEmbedder
from smart_search_sidecar.errors import SidecarError
from smart_search_sidecar.index import (
    ArtifactRetrievalContext,
    SQLiteIndexBackend,
    SQLiteKeywordIndex,
    SQLiteNavigableIndex,
    SQLiteVectorIndex,
)
from smart_search_sidecar.registry import (
    ArtifactRegistry,
    RegisteredArtifactLoader,
    parse_registered_artifact,
)

LOCATOR_RE = re.compile(r"^(?:page:(?P<page>\d+):)?char:(?P<start>\d+)-(?P<end>\d+)$")

TOOLKIT_REUSE = [
    "mistralai.search.toolkit.document.Document",
    "mistralai.search.toolkit.document.DocumentChunk",
    "mistralai.search.toolkit.document.DocumentMetadata",
    "mistralai.search.toolkit.document.DocumentChunkMetadata",
    "mistralai.search.toolkit.document.compute_char_locator",
    "mistralai.search.toolkit.document.compute_id",
    "mistralai.search.toolkit.ingestion.File",
    "mistralai.search.toolkit.ingestion.extractors.base.DocumentExtractor",
    "mistralai.search.toolkit.ingestion.pipelines.Pipeline",
    "mistralai.search.toolkit.ingestion.text_splitters.TextSplitter",
    "mistralai.search.toolkit.ingestion.text_splitters.CharacterTextSplitter",
    "mistralai.search.toolkit.ingestion.text_splitters.MarkdownTextSplitter",
    "mistralai.search.toolkit.embedders.base.Embedder",
    "mistralai.search.toolkit.embedders.base.EmbeddingResult",
    "mistralai.search.toolkit.retrieval.QueryEngine",
    "mistralai.search.toolkit.retrieval.retrievers.KeywordRetriever",
    "mistralai.search.toolkit.retrieval.retrievers.VectorRetriever",
    "mistralai.search.toolkit.search.KeywordStoreIndex",
    "mistralai.search.toolkit.search.VectorStoreIndex",
    "mistralai.search.toolkit.search.NavigableIndex",
    "mistralai.search.toolkit.search.NavigationDirection",
    "mistralai.search.toolkit.search.GrepMode",
]


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _attempt(
    attempt_no: int,
    component: str,
    status: str,
    *,
    kind: str,
    reason: str | None = None,
    artifact_refs: list[str] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "attempt_no": attempt_no,
        "component": component,
        "execution_kind": kind,
        "status": status,
        "observed_at": _now(),
        "artifact_refs": artifact_refs or [],
    }
    if reason:
        result["reason"] = reason
    return result


class RegisteredArtifactExtractor(DocumentExtractor):
    """Create Toolkit document models from an already-controlled in-memory File."""

    async def extract(self, file: File, context: Any = None) -> Document:
        del context
        content = file.raw.decode("utf-8")
        locator = compute_char_locator(0, len(content))
        shared_metadata = {
            "source_url": file.metadata["source_url"],
            "snapshot_identity": file.metadata["snapshot_identity"],
            "retrieved_at": file.metadata.get("retrieved_at"),
            "content_type": file.metadata["mimetype"],
            "parser": file.metadata["parser"],
            "derived_artifact_ref": file.metadata.get("derived_artifact_ref"),
        }
        chunk = DocumentChunk(
            source_id=file.source_id,
            locator=locator,
            start_offset=0,
            end_offset=len(content),
            parent_ref=compute_id(file.source_id),
            content=content,
            metadata=DocumentChunkMetadata(**shared_metadata),
        )
        return Document(
            source_id=file.source_id,
            content=content,
            chunks=[chunk],
            metadata=DocumentMetadata(extractor_type="text", **shared_metadata),
        )


def _validate_top_k(value: Any, *, default: int) -> int:
    if value is None:
        return default
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value <= 0
        or value > 200
    ):
        raise SidecarError(
            "INVALID_REQUEST", "top_k must be an integer between 1 and 200."
        )
    return value


def _locator_string(value: Any) -> str:
    if isinstance(value, str):
        locator = value
    elif isinstance(value, dict) and value.get("type") == "character_range":
        locator = value.get("toolkit_locator")
    else:
        raise SidecarError(
            "INVALID_LOCATOR",
            "Locator must be a Toolkit locator or typed character_range.",
        )
    if not isinstance(locator, str) or LOCATOR_RE.fullmatch(locator) is None:
        raise SidecarError(
            "INVALID_LOCATOR", "Locator is not a recognized Toolkit character range."
        )
    return locator


def _typed_locator(locator: str) -> dict[str, Any]:
    match = LOCATOR_RE.fullmatch(locator)
    if match is None:
        raise SidecarError(
            "INDEX_INCONSISTENT", "Stored chunk has an unsupported locator."
        )
    typed: dict[str, Any] = {
        "type": "character_range",
        "start": int(match.group("start")),
        "end": int(match.group("end")),
        "toolkit_locator": locator,
    }
    if match.group("page") is not None:
        typed["page"] = int(match.group("page"))
    return typed


class DocumentMiningService:
    def __init__(self, config: SidecarConfig) -> None:
        self.config = config
        self.registry = ArtifactRegistry()
        self.loader = RegisteredArtifactLoader(self.registry)
        self.backend = SQLiteIndexBackend(
            config.state_dir / "index.sqlite3", config.index_identity
        )
        self.keyword_index = SQLiteKeywordIndex(self.backend)
        self.vector_index = SQLiteVectorIndex(self.backend)
        self.navigable_index = SQLiteNavigableIndex(self.backend)
        if not isinstance(self.navigable_index, NavigableIndex):
            raise SidecarError(
                "ADAPTER_CONTRACT_FAILED",
                "SQLite navigation adapter does not satisfy Search Toolkit NavigableIndex.",
            )
        self.embedder = OpenAICompatibleEmbedder(
            base_url=config.embedding_base_url,
            model_name=config.embedding_model,
            dimension=config.embedding_dimension,
            normalization=config.embedding_normalization,
            api_key=config.embedding_api_key,
            timeout_seconds=config.request_timeout_seconds,
        )
        self.text_splitter: TextSplitter
        if config.splitter == "markdown":
            self.text_splitter = MarkdownTextSplitter(
                MarkdownTextSplitterConfig(chunk_size=config.chunk_size)
            )
        else:
            self.text_splitter = CharacterTextSplitter(chunk_size=config.chunk_size)
        self.pipeline = Pipeline(
            loader=None,
            extractor=RegisteredArtifactExtractor(),
            text_splitter=self.text_splitter,
            stores=self.keyword_index,
            pipeline_version=f"smart-search-sidecar-{__version__}",
        )

    def close(self) -> None:
        self.backend.close()

    def _require_usable_index(self) -> None:
        self.backend.require_identity()

    async def dispatch(self, request: dict[str, Any]) -> dict[str, Any]:
        operation = request.get("op")
        handlers = {
            "health": self.health,
            "ingest": self.ingest,
            "search": self.search,
            "open": self.open,
            "navigate": self.navigate,
            "read": self.read,
            "grep": self.grep,
        }
        handler = handlers.get(operation)
        if handler is None:
            raise SidecarError(
                "UNKNOWN_OPERATION",
                "Unsupported operation. Evidence Miner has no delete operation.",
                details={"supported": list(handlers)},
            )
        return await handler(request)

    def _check_fields(self, request: dict[str, Any], allowed: set[str]) -> None:
        unexpected = sorted(set(request) - allowed - {"id", "op"})
        if unexpected:
            raise SidecarError(
                "UNCONTROLLED_INPUT",
                "Request contains fields outside the controlled protocol.",
                details={"fields": unexpected},
            )

    async def health(self, request: dict[str, Any]) -> dict[str, Any]:
        self._check_fields(request, set())
        mismatch = self.backend.identity_mismatch
        return {
            "status": "degraded" if mismatch else "ok",
            "sidecar_version": __version__,
            "python": "3.12",
            "protocol": "stdio-jsonl-v1",
            "operations": [
                "health",
                "ingest",
                "search",
                "open",
                "navigate",
                "read",
                "grep",
            ],
            "delete_exposed": False,
            "mistral_api_used": False,
            "vespa_used": False,
            "docker_required": False,
            "toolkit": {
                "distribution": "mistralai-search-toolkit",
                "version": TOOLKIT_VERSION,
                "reused_imports": TOOLKIT_REUSE,
                "explicit_replacements": {
                    "mistralai.search.toolkit.ingestion.loaders.FileLoader": (
                        "not reused: its path/storage-location input contract cannot enforce run-local artifact_id-only access"
                    ),
                    "mistralai.search.toolkit.embedders.MistralEmbedder": (
                        "replaced by OpenAICompatibleEmbedder through the public Embedder interface"
                    ),
                    "Mistral OCR": "replaced by an external MinerU delegate-result boundary",
                    "Vespa": "replaced by SQLite FTS5 and a local NumPy vector matrix",
                },
            },
            "index_identity": self.config.index_identity,
            "index_identity_mismatch": None if mismatch is None else mismatch.details,
        }

    def _mineru_content(
        self,
        request: dict[str, Any],
        fallback_content: str,
        artifact_id: str,
    ) -> tuple[str, dict[str, Any] | None, list[dict[str, Any]]]:
        delegate = request.get("mineru_delegate_result")
        attempts: list[dict[str, Any]] = []
        if delegate is None:
            attempts.append(
                _attempt(
                    1,
                    "fetched_text_fallback",
                    "success",
                    kind="fallback",
                    artifact_refs=[artifact_id],
                )
            )
            return fallback_content, None, attempts
        if not isinstance(delegate, dict):
            raise SidecarError(
                "INVALID_MINERU_RESULT", "mineru_delegate_result must be an object."
            )
        allowed = {"status", "markdown", "error", "artifact_ref", "parser_version"}
        unexpected = sorted(set(delegate) - allowed)
        if unexpected:
            raise SidecarError(
                "INVALID_MINERU_RESULT",
                "MinerU delegate result contains unsupported fields; credentials are never accepted.",
                details={"fields": unexpected},
            )
        status = delegate.get("status")
        if status == "success":
            markdown = delegate.get("markdown")
            if not isinstance(markdown, str) or not markdown:
                raise SidecarError(
                    "INVALID_MINERU_RESULT",
                    "Successful MinerU result requires non-empty markdown.",
                )
            if len(markdown.encode("utf-8")) > self.config.max_artifact_bytes:
                raise SidecarError(
                    "ARTIFACT_TOO_LARGE",
                    "MinerU Markdown exceeds the configured byte limit.",
                )
            artifact_ref = delegate.get("artifact_ref")
            if not isinstance(artifact_ref, str) or not artifact_ref:
                raise SidecarError(
                    "INVALID_MINERU_RESULT",
                    "Successful MinerU result requires artifact_ref.",
                )
            parser_version = delegate.get("parser_version")
            if not isinstance(parser_version, str) or not parser_version:
                raise SidecarError(
                    "INVALID_MINERU_RESULT",
                    "Successful MinerU result requires parser_version.",
                )
            attempts.append(
                _attempt(
                    1,
                    "mineru",
                    "success",
                    kind="delegate",
                    artifact_refs=[artifact_ref],
                )
            )
            return (
                markdown,
                {"artifact_ref": artifact_ref, "parser_version": parser_version},
                attempts,
            )
        if status not in {"failed", "unavailable"}:
            raise SidecarError(
                "INVALID_MINERU_RESULT",
                "MinerU status must be success, failed, or unavailable.",
            )
        error = delegate.get("error")
        reason = error if isinstance(error, str) and error else f"mineru {status}"
        attempts.append(_attempt(1, "mineru", status, kind="delegate", reason=reason))
        attempts.append(
            _attempt(
                2,
                "fetched_text_fallback",
                "success",
                kind="fallback",
                artifact_refs=[artifact_id],
            )
        )
        return fallback_content, None, attempts

    async def ingest(self, request: dict[str, Any]) -> dict[str, Any]:
        self._check_fields(
            request, {"artifact_id", "registered_artifact", "mineru_delegate_result"}
        )
        self._require_usable_index()
        registered_payload = request.get("registered_artifact")
        if registered_payload is not None:
            artifact = parse_registered_artifact(
                registered_payload,
                max_artifact_bytes=self.config.max_artifact_bytes,
            )
            if request.get("artifact_id") != artifact.artifact_id:
                raise SidecarError(
                    "INVALID_ARTIFACT",
                    "Request artifact_id must match registered_artifact.artifact_id.",
                )
            self.registry.register(artifact)
        artifact = self.registry.require(request.get("artifact_id"))
        content, mineru_metadata, attempts = self._mineru_content(
            request, artifact.content, artifact.artifact_id
        )
        file = self.loader.load(artifact.artifact_id, content_override=content)
        if mineru_metadata is not None:
            metadata = dict(file.metadata)
            metadata["parser"] = {
                "name": "mineru-delegate",
                "version": mineru_metadata["parser_version"],
            }
            metadata["derived_artifact_ref"] = mineru_metadata["artifact_ref"]
            file = file.model_copy(update={"metadata": metadata})
        attempts.append(
            _attempt(
                len(attempts) + 1,
                "controlled_artifact_loader",
                "success",
                kind="loader",
                artifact_refs=[artifact.artifact_id],
            )
        )
        try:
            document = await self.pipeline.run_file(file)
        except Exception as exc:
            attempts.append(
                _attempt(
                    len(attempts) + 1,
                    "search_toolkit_pipeline",
                    "failed",
                    kind="ingestion",
                    reason=self._safe_error_reason(exc),
                    artifact_refs=[artifact.artifact_id],
                )
            )
            raise SidecarError(
                "INGESTION_FAILED",
                "Search Toolkit ingestion pipeline failed.",
                details={"component_attempts": attempts},
            ) from exc
        attempts.append(
            _attempt(
                len(attempts) + 1,
                "search_toolkit_pipeline",
                "success",
                kind="ingestion",
                artifact_refs=[artifact.artifact_id],
            )
        )
        vector_indexed = False
        if not self.config.embedding_enabled:
            attempts.append(
                _attempt(
                    len(attempts) + 1,
                    "sqlite_fts5",
                    "success",
                    kind="lexical_index",
                    artifact_refs=[artifact.artifact_id],
                )
            )
        else:
            try:
                embedded_document = await self.embedder.process(document)
                attempts.append(
                    _attempt(
                        len(attempts) + 1,
                        "openai_compatible_embedding",
                        "success",
                        kind="embedding",
                    )
                )
            except Exception as exc:  # noqa: BLE001 - embedding degradation must preserve lexical ingest
                attempts.append(
                    _attempt(
                        len(attempts) + 1,
                        "openai_compatible_embedding",
                        "degraded",
                        kind="embedding",
                        reason=self._safe_error_reason(exc),
                    )
                )
                attempts.append(
                    _attempt(
                        len(attempts) + 1,
                        "sqlite_fts5",
                        "success",
                        kind="lexical_fallback",
                        artifact_refs=[artifact.artifact_id],
                    )
                )
            else:
                try:
                    await self.vector_index.index_document(embedded_document)
                    vector_indexed = True
                    attempts.append(
                        _attempt(
                            len(attempts) + 1,
                            "local_vector_matrix",
                            "success",
                            kind="index",
                        )
                    )
                except Exception as exc:  # noqa: BLE001 - vector index degradation preserves FTS5
                    attempts.append(
                        _attempt(
                            len(attempts) + 1,
                            "local_vector_matrix",
                            "degraded",
                            kind="index",
                            reason=self._safe_error_reason(exc),
                        )
                    )
                attempts.append(
                    _attempt(
                        len(attempts) + 1,
                        "sqlite_fts5",
                        "success",
                        kind="lexical_fallback",
                        artifact_refs=[artifact.artifact_id],
                    )
                )
        return {
            "artifact_id": artifact.artifact_id,
            "source_url": artifact.source_url,
            "snapshot_identity": artifact.snapshot_identity,
            "document_id": document.id,
            "chunk_count": len(document.chunks),
            "locators": [_typed_locator(chunk.locator) for chunk in document.chunks],
            "vector_indexed": vector_indexed,
            "index_identity": self.config.index_identity,
            "component_attempts": attempts,
        }

    def _safe_error_reason(self, exc: Exception) -> str:
        current: BaseException | None = exc
        while current is not None:
            if isinstance(current, SidecarError):
                return current.code
            current = current.__cause__
        return type(exc).__name__

    def _context(
        self, artifact_id: str, request: dict[str, Any]
    ) -> ArtifactRetrievalContext:
        excluded = (
            self.registry.read_chunk_ids(artifact_id)
            if request.get("exclude_read", True)
            else set()
        )
        already_read = request.get("already_read_locators", [])
        if not isinstance(already_read, list):
            raise SidecarError(
                "INVALID_REQUEST", "already_read_locators must be a list."
            )
        for locator_value in already_read:
            locator = _locator_string(locator_value)
            excluded.add(compute_id(artifact_id, locator))
        return ArtifactRetrievalContext(
            artifact_id=artifact_id, exclude_ids=frozenset(excluded)
        )

    async def search(self, request: dict[str, Any]) -> dict[str, Any]:
        self._check_fields(
            request,
            {"artifact_id", "query", "top_k", "exclude_read", "already_read_locators"},
        )
        self._require_usable_index()
        artifact = self.registry.require(request.get("artifact_id"))
        query = request.get("query")
        if not isinstance(query, str) or not query.strip():
            raise SidecarError("INVALID_REQUEST", "query must be non-empty text.")
        top_k = _validate_top_k(request.get("top_k"), default=10)
        context = self._context(artifact.artifact_id, request)
        attempts: list[dict[str, Any]] = []
        try:
            engine = QueryEngine(
                retriever=[
                    KeywordRetriever(self.keyword_index),
                    VectorRetriever(self.vector_index, self.embedder),
                ]
            )
            engine_result = await engine.search(query, top_k=top_k, context=context)
            results = engine_result.results
            attempts.append(
                _attempt(
                    1, "search_toolkit_query_engine", "success", kind="hybrid_retrieval"
                )
            )
        except Exception as exc:  # noqa: BLE001 - hybrid retrieval degrades to lexical QueryEngine
            attempts.append(
                _attempt(
                    1,
                    "search_toolkit_query_engine",
                    "degraded",
                    kind="hybrid_retrieval",
                    reason=self._safe_error_reason(exc),
                )
            )
            try:
                engine = QueryEngine(retriever=KeywordRetriever(self.keyword_index))
                engine_result = await engine.search(query, top_k=top_k, context=context)
                results = engine_result.results
                attempts.append(
                    _attempt(2, "sqlite_fts5", "success", kind="lexical_fallback")
                )
            except Exception as fallback_exc:
                attempts.append(
                    _attempt(
                        2,
                        "sqlite_fts5",
                        "failed",
                        kind="lexical_fallback",
                        reason=self._safe_error_reason(fallback_exc),
                    )
                )
                raise SidecarError(
                    "SEARCH_FAILED",
                    "Hybrid and lexical retrieval both failed.",
                    details={"component_attempts": attempts},
                ) from fallback_exc
        deduplicated: dict[str, SearchResult] = {}
        for result in results:
            existing = deduplicated.get(result.chunk.id)
            if existing is None or result.score > existing.score:
                deduplicated[result.chunk.id] = result
        ordered = sorted(
            deduplicated.values(), key=lambda item: item.score, reverse=True
        )[:top_k]
        return {
            "artifact_id": artifact.artifact_id,
            "source_url": artifact.source_url,
            "snapshot_identity": artifact.snapshot_identity,
            "results": [self._serialize_result(item) for item in ordered],
            "excluded_read_count": len(context.exclude_ids),
            "component_attempts": attempts,
        }

    def _require_owned_chunk(self, artifact_id: str, chunk_id: Any) -> SearchResult:
        if not isinstance(chunk_id, str) or not chunk_id:
            raise SidecarError("INVALID_REQUEST", "chunk_id must be non-empty text.")
        result = self.backend.get_chunk(chunk_id)
        if result is None or result.chunk.source_id != artifact_id:
            raise SidecarError(
                "CHUNK_NOT_FOUND",
                "chunk_id does not belong to the registered artifact.",
            )
        return result

    async def open(self, request: dict[str, Any]) -> dict[str, Any]:
        self._check_fields(request, {"artifact_id", "chunk_id", "before", "after"})
        self._require_usable_index()
        artifact = self.registry.require(request.get("artifact_id"))
        center = self._require_owned_chunk(
            artifact.artifact_id, request.get("chunk_id")
        )
        before = _validate_top_k(request.get("before"), default=1)
        after = _validate_top_k(request.get("after"), default=1)
        previous = await self.navigable_index.navigate(
            artifact.artifact_id,
            center.chunk.start_offset or 0,
            center.chunk.end_offset or 0,
            NavigationDirection.PREVIOUS,
            top_k=before,
        )
        following = await self.navigable_index.navigate(
            artifact.artifact_id,
            center.chunk.start_offset or 0,
            center.chunk.end_offset or 0,
            NavigationDirection.NEXT,
            top_k=after,
        )
        results = [*previous, center, *following]
        self.registry.mark_read(
            artifact.artifact_id, {result.chunk.id for result in results}
        )
        return self._navigation_response(artifact, results)

    async def navigate(self, request: dict[str, Any]) -> dict[str, Any]:
        self._check_fields(request, {"artifact_id", "chunk_id", "direction", "top_k"})
        self._require_usable_index()
        artifact = self.registry.require(request.get("artifact_id"))
        center = self._require_owned_chunk(
            artifact.artifact_id, request.get("chunk_id")
        )
        try:
            direction = NavigationDirection(request.get("direction"))
        except ValueError as exc:
            raise SidecarError(
                "INVALID_REQUEST", "direction must be next or previous."
            ) from exc
        top_k = _validate_top_k(request.get("top_k"), default=1)
        results = await self.navigable_index.navigate(
            artifact.artifact_id,
            center.chunk.start_offset or 0,
            center.chunk.end_offset or 0,
            direction,
            top_k=top_k,
        )
        self.registry.mark_read(
            artifact.artifact_id, {result.chunk.id for result in results}
        )
        return self._navigation_response(artifact, results)

    async def read(self, request: dict[str, Any]) -> dict[str, Any]:
        self._check_fields(request, {"artifact_id", "start", "end", "top_k"})
        self._require_usable_index()
        artifact = self.registry.require(request.get("artifact_id"))
        start = request.get("start")
        end = request.get("end")
        if start is not None and (
            not isinstance(start, int) or isinstance(start, bool) or start < 0
        ):
            raise SidecarError(
                "INVALID_REQUEST", "start must be a non-negative integer or null."
            )
        if end is not None and (
            not isinstance(end, int) or isinstance(end, bool) or end < 0
        ):
            raise SidecarError(
                "INVALID_REQUEST", "end must be a non-negative integer or null."
            )
        if start is not None and end is not None and end < start:
            raise SidecarError("INVALID_REQUEST", "end must not be smaller than start.")
        top_k = _validate_top_k(request.get("top_k"), default=20)
        results = await self.navigable_index.read(
            artifact.artifact_id, start, end, top_k=top_k
        )
        self.registry.mark_read(
            artifact.artifact_id, {result.chunk.id for result in results}
        )
        return self._navigation_response(artifact, results)

    async def grep(self, request: dict[str, Any]) -> dict[str, Any]:
        self._check_fields(request, {"artifact_id", "pattern", "mode", "top_k"})
        self._require_usable_index()
        artifact = self.registry.require(request.get("artifact_id"))
        pattern = request.get("pattern")
        if not isinstance(pattern, str) or not pattern.strip():
            raise SidecarError("INVALID_REQUEST", "pattern must be non-empty text.")
        try:
            mode = GrepMode(request.get("mode", "phrase"))
        except ValueError as exc:
            raise SidecarError(
                "INVALID_REQUEST", "mode must be phrase or term."
            ) from exc
        top_k = _validate_top_k(request.get("top_k"), default=5)
        results = await self.navigable_index.grep(
            artifact.artifact_id,
            pattern,
            mode=mode,
            top_k=top_k,
        )
        self.registry.mark_read(
            artifact.artifact_id, {result.chunk.id for result in results}
        )
        return self._navigation_response(artifact, results)

    def _navigation_response(
        self, artifact: Any, results: Iterable[SearchResult]
    ) -> dict[str, Any]:
        materialized = list(results)
        return {
            "artifact_id": artifact.artifact_id,
            "source_url": artifact.source_url,
            "snapshot_identity": artifact.snapshot_identity,
            "results": [self._serialize_result(result) for result in materialized],
        }

    def _serialize_result(self, result: SearchResult) -> dict[str, Any]:
        document_metadata = result.chunk.metadata.get("document", {})
        return {
            "chunk_id": result.chunk.id,
            "artifact_id": result.chunk.source_id,
            "content": result.chunk.content,
            "score": result.score,
            "distance": result.distance,
            "locator": _typed_locator(result.chunk.locator),
            "source_url": document_metadata.get("source_url"),
            "snapshot_identity": document_metadata.get("snapshot_identity"),
            "retrieved_at": document_metadata.get("retrieved_at"),
            "content_type": document_metadata.get("content_type"),
            "parser": document_metadata.get("parser"),
            "pipeline_version": document_metadata.get("pipeline_version"),
            "chunker": {
                "name": self.config.index_identity["splitter"],
                "version": self.config.index_identity["splitter_version"],
                "chunk_size": self.config.index_identity["splitter_chunk_size"],
            },
            "retriever_id": result.retriever_id,
        }
