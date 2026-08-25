# Stage G Final Synthesis

Stage G completed the multi-source agentic research engineering gate using the saved run `run-stage-g-seq-20260823T191412Z`. The run retains 113 discovery candidates, 2 source-curation proposals, 16 located EvidenceItem records, 2 ClaimRecord assessments, and 16 verified citation backtraces.

The Provider Research Agent paths were attempted together and their observed outcomes were preserved: Exa succeeded; Firecrawl and Jina timed out; Tavily failed. These failures remain visible instead of being silently dropped. Existing provider calls were not rerun during workspace migration.

## Reports

- [Portable bundle index](README.md)
- [Reference register](references.md)
- [Engineering gate](../../acceptance/stage-g-engineering-gate.md)
- [Architecture review](../../acceptance/stage-g-architecture-review.md)
- [Benchmark recommendations](../../acceptance/stage-g-benchmark-recommendations.md)

The structured `latest_dossier.json`, evidence files, artifact metadata, and
`public_trace.jsonl` are the committed execution record. Raw webpage snapshots,
local indexes, duplicate checkpoints, task runtime directories, and the raw
Trace remain excluded as documented in `export_manifest.json`. This Markdown
file is a human-readable final projection, not a replacement for the structured
authorities.
