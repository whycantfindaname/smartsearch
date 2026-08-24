# Research Runtime Configuration

This document is the configuration ownership contract for the multi-source
agentic-research Preview. Smart Search keeps one configuration entry point:
`smart-search setup`, `smart-search config`, and `smart-search doctor` backed by
`src/smart_search/config.py`.

## Ownership

| Component | Configuration | Sensitive | Owner and storage | Diagnostic |
| --- | --- | --- | --- | --- |
| Firecrawl Search/Agent/Crawl/Batch | `FIRECRAWL_API_KEY`, `FIRECRAWL_API_URL` | Key: yes | Existing Smart Search config or process environment | `config list`, `doctor`, research attempt |
| Tavily Search/Extract/Crawl/Research | `TAVILY_API_KEY`, `TAVILY_API_URL`, `TAVILY_ENABLED`, `TAVILY_TIMEOUT_SECONDS` | Key: yes | Existing Smart Search config or process environment | `config list`, `doctor`, research attempt |
| Exa Search/Deep/Agent | `EXA_API_KEY`, `EXA_BASE_URL`, `EXA_TIMEOUT_SECONDS` | Key: yes | Existing Smart Search config or process environment | `config list`, `doctor`, research attempt |
| Jina Reader/DeepSearch/Reranker | `JINA_API_KEY`, `JINA_READER_API_URL`, `JINA_SEARCH_API_URL`, `JINA_RERANK_API_URL`, `JINA_RESPOND_WITH`, `JINA_TIMEOUT_SECONDS` | Key: yes | Existing Smart Search config or process environment | `config list`, `doctor`, research attempt |
| Search Toolkit Sidecar | `SMART_SEARCH_SIDECAR_PYTHON`, `SMART_SEARCH_SIDECAR_TIMEOUT_SECONDS` | No | Smart Search config | `config list`, `doctor`, Sidecar health |
| Document index identity | `SMART_SEARCH_DOCUMENT_EMBEDDING_SOURCE`, `SMART_SEARCH_DOCUMENT_EMBEDDING_DIMENSIONS`, `SMART_SEARCH_DOCUMENT_EMBEDDING_NORMALIZE`, `SMART_SEARCH_DOCUMENT_SPLITTER`, `SMART_SEARCH_DOCUMENT_CHUNK_SIZE` | No | Smart Search config | `config list`, `doctor`, Sidecar health |
| Document Embedding endpoint/key/model | Reuses `INTENT_EMBEDDING_API_URL`, `INTENT_EMBEDDING_API_KEY`, and `INTENT_EMBEDDING_MODEL` by default; `openai-compatible` may explicitly reuse the existing OpenAI-compatible domain | Key: yes | Existing Smart Search config; no duplicated document-specific key | Masked `config list`, `doctor`, embedding attempt |
| AnySearch | `ANYSEARCH_API_KEY` or the bundled snapshot's private `.env` | Yes | AnySearch Skill | Delegate result and provenance check |
| MinerU | MinerU Skill configuration | Yes | MinerU Skill | Delegate result |

There is one Jina credential. DeepSearch and Reranker reuse the existing
`JINA_API_KEY`; setup never asks for or creates feature-specific Jina keys.

`SMART_SEARCH_DOCUMENT_EMBEDDING_DIMENSIONS=0` means that the Sidecar records
the dimension returned by the first successful embedding request. That observed
dimension becomes part of the index identity. A later mismatch is a rebuild
condition, never an implicit mixed index.

## Precedence and boundaries

Smart Search retains the existing precedence order: process environment first,
then the selected `config.json`, then defaults. `SMART_SEARCH_CONFIG_DIR`
selects the complete Smart Search configuration domain. Research code must not
read a second repository-root `.env`.

Provider credentials are reused by their new Research capabilities. Key
presence means only `configured`; it does not prove reachability or entitlement.
Every live attempt records its own observed status and timestamp.

AnySearch and MinerU remain external Skills. Smart Search records capability and
delegate status but does not copy their credentials into `config.json`.

The sidecar reuses only the open-source `mistralai-search-toolkit` Python
package. It does not call Mistral APIs and has no `MISTRAL_API_KEY`. Its local
index is SQLite/FTS5 plus run-local vectors; Vespa and Docker are neither
configured nor required. `research-environment doctor` verifies these claims
through the sidecar protocol fields `mistral_api_used=false`,
`vespa_used=false`, and `docker_required=false`.

## Isolated sidecar environment

The Preview sidecar is a Python 3.12 package with dependencies that must not be
assumed to exist in a global interpreter. Installation therefore requires an
explicit Python 3.12 interpreter and creates a dedicated virtual environment:

```bash
export SMART_SEARCH_CONFIG_DIR="$(mktemp -d)/smart-search-preview"
smart-search research-environment install \
  --python /absolute/path/to/python3.12 \
  --format json
smart-search research-environment doctor --format json
```

By default the virtual environment is
`$SMART_SEARCH_CONFIG_DIR/research-sidecar`, and only its Python path is saved
as `SMART_SEARCH_SIDECAR_PYTHON` in that selected Preview `config.json`. The
command installs the repository's `sidecar/` package into the virtual
environment, runs the real stdio health protocol, and saves the path only after
health succeeds. `--environment PATH` may select another isolated location.
The command does not install packages into the supplied Python 3.12
interpreter.

## Preview verification

Use an isolated directory and never target the currently activated macOS
configuration during implementation or acceptance:

```bash
export SMART_SEARCH_CONFIG_DIR="$(mktemp -d)/smart-search-preview"
smart-search config path --format json
smart-search config list --format json
smart-search doctor --format json
smart-search research-environment doctor --format json
```

Populate that Preview directory by explicit `setup --non-interactive` or
`config set` calls. `config list` includes an `effective_research_config`
section with value sources for the Jina endpoints and document-sidecar keys;
API keys remain masked and are not duplicated. Invalid Jina HTTP(S) endpoints,
document index settings, or sidecar timeouts are rejected by `config set` and
non-interactive setup before any setup value is written. `doctor` includes the
same effective values plus a real `research_environment` health result.

Do not copy unmasked output into tests, Trace, logs, Git,
npm packages, or wheels. Applying a verified configuration to the active macOS
installation requires separate user approval.
