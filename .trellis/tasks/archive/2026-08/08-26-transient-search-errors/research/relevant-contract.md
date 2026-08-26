# Relevant repository contracts

Focused extract of the rules in
`.trellis/spec/backend/provider-capability-contract.md` that govern this task.
The source spec remains authoritative.

## Skill packaging

- Runtime Skill injection loads bundled package assets, not a developer's
  global Skill or local checkout.
- A Skill contract change updates both `skills/smart-search-cli/**` and
  `src/smart_search/assets/skills/smart-search-cli/**`; a source-only change
  leaves packaged users stale.
- `smart-search skills status` is read-only. `skills update` overwrites managed
  bundled files but must not change provider keys or unrelated configuration.

## Search output and retry

- JSON is the stable machine-readable contract; Markdown is the human-readable
  report format.
- Keep existing search content/source fields and observability fields stable,
  including routing, providers, provider attempts, fallback, validation, and
  capability status.
- Search timeout defaults to 120 seconds.
- Before this task, `--max-try` defaults to five and covers only completed xAI
  `504 upstream_server_error`. Results expose logical-attempt counts and label
  aggregated provider attempts with their logical attempt.
- Provider attempts may add provider-specific diagnostic fields while
  preserving the base attempt contract.

## Diagnostics and errors

- `doctor()` exposes connection tests per configured main provider and a
  backward-compatible primary-provider alias.
- `diagnose openai-compatible` is the focused stream/non-stream timeout report;
  it masks credentials and reports status, timing, HTTP status, content type,
  and observed content.
- Provider exceptions use a stable public taxonomy: parameter, auth, timeout,
  rate limit, network, parse, provider, and runtime errors. A normal empty
  response is not an exception.
- Provider exceptions remain visible in `provider_attempts`; fallback stays
  within the same capability.
- Secrets must be masked or omitted in output, tests, docs, and task artifacts.
