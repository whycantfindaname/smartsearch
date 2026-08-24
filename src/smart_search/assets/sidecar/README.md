# Smart Search document-mining sidecar

This package is an isolated Python 3.12 JSON-lines sidecar for Milestone C. It
does not call the Mistral API and does not require a Mistral key, Vespa, or
Docker. The process reads one JSON object per stdin line and writes one response
per stdout line. The exposed operations are `health`, `ingest`, `search`,
`open`, `navigate`, `read`, and `grep`; there is deliberately no `delete`
operation.

## Search Toolkit 0.0.11 reuse

The implementation imports and directly uses these public APIs:

- `mistralai.search.toolkit.document.Document`, `DocumentChunk`,
  `DocumentMetadata`, `DocumentChunkMetadata`, `compute_char_locator`, and
  `compute_id`;
- `mistralai.search.toolkit.ingestion.File` and
  `mistralai.search.toolkit.ingestion.extractors.base.DocumentExtractor`;
- `mistralai.search.toolkit.ingestion.pipelines.Pipeline`;
- `mistralai.search.toolkit.ingestion.text_splitters.TextSplitter` through the
  concrete `CharacterTextSplitter`;
- `mistralai.search.toolkit.embedders.base.Embedder` and `EmbeddingResult`;
- `mistralai.search.toolkit.retrieval.QueryEngine`, `KeywordRetriever`, and
  `VectorRetriever`;
- `mistralai.search.toolkit.search.KeywordStoreIndex`, `VectorStoreIndex`,
  `NavigableIndex`, `NavigationDirection`, `GrepMode`, and the Search Toolkit
  query/result models.

The Toolkit `FileLoader` is not used. Its contract accepts paths and storage
locations, which conflicts with the project rule that agent-facing document
tools may only resolve an `artifact_id` already registered in the current
sidecar run. `RegisteredArtifactLoader` is therefore a project adapter and
fails closed on paths, `file://` values, URLs, and unknown identifiers.

The project also replaces `MistralEmbedder` with an injected OpenAI-compatible
HTTP embedder, replaces Vespa with SQLite FTS5 plus a run-local NumPy vector
matrix, and treats MinerU as an external delegate result. No MinerU credential
is accepted or copied into this component.

## Protocol summary

Every request has an `id` and `op`. Successful responses are
`{"id": ..., "ok": true, "result": ...}`. Failures use
`{"id": ..., "ok": false, "error": {"code": ..., "message": ...}}` and
do not terminate the process.

`ingest` may carry a `registered_artifact` object containing inline Markdown or
plain text, canonical `source_url`, and `snapshot_identity`. Registration occurs
in run-local memory before the controlled loader is called. No operation accepts
a local path or asks the sidecar to fetch a URL.

Configuration is injected through CLI flags or environment variables. Secrets
are read only from `SMART_SEARCH_EMBEDDING_API_KEY` and are never returned by
`health` or errors. See `python -m smart_search_sidecar --help` for the
non-secret settings.
