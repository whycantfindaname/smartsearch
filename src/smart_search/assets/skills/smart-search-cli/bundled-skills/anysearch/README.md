# anysearch

## Source

- Upstream repository: `https://github.com/anysearch-ai/anysearch-skill.git`
- Upstream local checkout: `/Users/jasonliao/Desktop/code/Skills/5-knowledge/anysearch-skill`
- Upstream path: `.`
- Upstream branch/ref: `main`
- Upstream snapshot commit: `4d6cef918e9338c9deef43b81ac0f7e22606825f`; time=`2026-08-21T16:00:26+08:00`; message=`Merge pull request #39 from anysearch-ai/feat_http-cli`

## Local Modifications

- Copied the minimal runnable package: `CONTRACT.md`, `.env.example`, `requirements.txt`, `runtime.conf.example`, `scripts/`, `LICENSE`, and `NOTICE`.
- Kept the upstream CLI scripts and shared schema files unchanged so their source snapshot remains auditable.
- Added `scripts/smart_search_anysearch.py`, the Smart Search-owned adapter and only active bundled entrypoint.
- Added this README for source tracking, package scope, and secrets policy.

## Invocation

Smart Search invokes the adapter:

```bash
python3 /path/to/anysearch/scripts/smart_search_anysearch.py search "query" --max_results 5
```

The adapter preserves the upstream Python CLI's subcommands and Markdown output. Its standard-library transport fallback keeps the unchanged Python CLI usable when the optional `requests` package is absent.

## Credential boundary

Normal calls read only these two fields from Smart Search's private `config.json`:

```json
{
  "ANYSEARCH_API_KEY": "<primary key>",
  "ANYSEARCH_API_KEY_FALLBACK": "<fallback key>"
}
```

The file is resolved from non-empty `SMART_SEARCH_CONFIG_DIR/config.json`, then the platform's existing Smart Search config location. The two values must be distinct, non-empty strings. An explicit `--api_key VALUE` is a one-call override and disables fallback.

This bundled adapter never reads `.env` or process environment values for credentials and never makes anonymous requests. It sends a non-empty `Authorization: Bearer …` header on every network request. It may try the fallback once only after a valid primary response with HTTP `401`, `403`, or `429`; transport, malformed/schema, local-argument, and `5xx` failures do not switch keys. It never stores response credentials such as `auto_registered.api_key`.

Do not put real keys in this repository, `.env.example`, runtime files, logs, tests, or documentation. The parent Smart Search config remains machine-private and is never copied by snapshot sync.
