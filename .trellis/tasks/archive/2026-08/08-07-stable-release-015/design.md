# Design: smart-search v0.1.15 stable release

## Branch And Task Topology

- Source workspace and Trellis parent: `D:\Dev\20_Software\21_Mine\smartsearch` / `08-07-stable-release-015`.
- Implementation workspace: `D:\Dev\20_Software\21_Mine\smartsearch-release-0.1.15` on `codex/release-0.1.15`, based on `origin/main`.
- Integrate commits in order: `18f4611`, `e5357cf`, `ebc8ce5`, then PR #21 `6a30a9a`; resolve PR #21 conflicts selectively.
- Each child task owns one independently testable deliverable. The parent owns final cross-child checks and release evidence.

## Provider Design

### Context7

- Keep explicit Context7 commands unchanged.
- Replace preferred-id mapping with a reusable candidate scoring function.
- A candidate is eligible only when query subject tokens overlap its normalized title/id tokens. Title/id exact and multi-token matches dominate; description overlap contributes less; trust and benchmark scores are tie-breakers.
- Auto research and supplemental docs routing use the same selector. No eligible candidate is an empty Context7 result and triggers same-capability Exa fallback.

### AnySearch

- Keep the current live-proven `get_sub_domains` and `tools/list` discovery behavior.
- Parse JSON object first, then repeatable `key=value` entries. Empty keys, missing `=`, invalid JSON and non-object JSON fail before network.
- Send extract only `{url}`. On successful normalized JSON, truncate `content`, `raw_content`, and result text fields locally when `max_length > 0`.

### Controls And Errors

- Centralize exception-to-contract mapping so primary search, Tavily and Firecrawl share status behavior without changing successful return shapes.
- Provider helpers may raise transport/HTTP/parse exceptions; fallback boundaries convert them to `provider_attempts[].status=error` and continue only inside the same capability.
- `TAVILY_ENABLED` is checked at provider registration and direct-call boundaries. Disabled Tavily is not configured or attempted.

### Smoke Output

- `failed_cases` contains critical failures, `degraded_cases` contains recoverable failures, and `skipped_cases` contains optional unconfigured checks.
- `status` is `failed` when critical failures exist, `degraded` when only degraded cases exist, otherwise `healthy`.
- `ok` remains `not failed_cases` for backward-compatible automation. Renderers use `status`, not only `ok`, for the overall label.

## CI And Release Design

- Add a PR/push/workflow-dispatch CI workflow with three explicit OS/runtime combinations and concurrency cancellation.
- Build a real tarball, install under a temporary prefix, and run its wrapper/version/regression/mock smoke without touching the user's global install.
- Publish workflow keeps provenance and tag-based stable publishing. Main push skips prerelease when the stable version changed relative to its first parent; tests cover merge/squash-compatible detection. Publish concurrency serializes npm releases.
- Source metadata is `0.1.15`. Manual dispatch produces `0.1.15-beta.1` under `next`; stable `v0.1.15` tag produces `latest` only after owner approval.

## Compatibility And Rollback

- Existing command names, JSON `ok`, exit codes, fallback order and explicit provider commands remain compatible.
- New public fields and `--param` are additive; more specific `error_type` values correct existing misclassification.
- Each child is committed separately only after its focused and full required gates pass. A failing child can be reverted without touching the original worktree or unrelated children.
