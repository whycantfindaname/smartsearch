# Smart Search CLI Reference Map

This compatibility entrypoint no longer stores the full CLI contract. Read the focused reference that matches the task.

## Read These Files

- `cli-core.md`: entrypoints, command signatures, aliases, JSON/Markdown/content output expectations, exit codes, and tool policy.
- `command-patterns.md`: source-directed examples, evidence files, and everyday guardrails.
- `error-recovery.md`: provider-specific error catalog, classification, retry and replay boundaries, diagnostics, and operator actions.
- `deep-research-mode.md`: Deep Research trigger rules, offline planner, live executor, `research_plan` shape, allowed tools, gap check, provider advantage routing, and smoke matrix.
- `provider-routing.md`: intent routing diagnostics, provider capabilities, source provenance, same-capability fallback, Zhipu REST/MCP, Jina, AnySearch, Exa, Tavily, Firecrawl, Context7, and maintenance guardrails.
- `setup-config.md`: config storage, setup/config commands, skill installation, endpoint setup, OpenAI-compatible diagnostics, streaming, and router configuration.
- `regression-release.md`: regression behavior, packaged-install checks, release lanes, and release closeout lessons.

## Selection Hints

- Need to choose or explain a search/docs/fetch route: read `provider-routing.md`, then `command-patterns.md`.
- Need command syntax, aliases, output fields, or exit codes: read `cli-core.md`.
- Need setup, API keys, config paths, skill update behavior, or provider endpoint flags: read `setup-config.md`.
- Need deep search, deep research, multi-source verification, serious review, or selection/comparison research: read `deep-research-mode.md`.
- Need error classification, recovery, retry, replay, cooldown, or diagnostic guidance: read `error-recovery.md`.
- Need saved evidence files or source-first command examples: read `command-patterns.md`.
- Need release, npm/mise packaged install, or regression expectations: read `regression-release.md`.
