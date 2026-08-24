# Third-Party Notices

## Mistral AI Search Toolkit

- Distribution: `mistralai-search-toolkit`
- Version: `0.0.11`
- Source package: <https://pypi.org/project/mistralai-search-toolkit/0.0.11/>
- Copyright: Copyright 2026 Mistral AI
- License: Apache License 2.0, <https://www.apache.org/licenses/LICENSE-2.0>

Smart Search's Python 3.12 document-mining sidecar links to and directly reuses
the package's document models and locators, ingestion `Pipeline` and
`TextSplitter` interfaces, retrieval `QueryEngine`, retrievers, and search index
interfaces. The project-written adaptation replaces the package's unrestricted
path loader, Mistral embedder/OCR path, and Vespa implementation with a
run-local controlled artifact loader, an injected OpenAI-compatible embedder,
an external MinerU delegate-result boundary, and SQLite FTS5 plus a small local
vector matrix. The sidecar does not call the Mistral API and does not require a
Mistral API key.

The full Apache License 2.0 text is available at the URL above and in the
installed distribution's `dist-info/licenses/LICENSE` file.

## Public Agent Skills Deep Research Visualizer

- Source: <https://github.com/cafe3310/public-agent-skills>
- Copyright: github/cafe3310 contributors
- License: MIT

Smart Search's read-only Research Workspace visualizer is inspired by and
adapted from the filesystem-driven Deep Research visualizer. The adaptation
uses a Root-led search pipeline, reads Smart Search's structured public
projections, binds only to `127.0.0.1`, and does not expose raw artifacts or
configuration files. The asset-level attribution is retained in
`src/smart_search/assets/research_visualizer/NOTICE.md`.
