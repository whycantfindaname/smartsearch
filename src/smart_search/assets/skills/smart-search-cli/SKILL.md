---
name: smart-search-cli
description: "Route AI agents to the local smart-search CLI for current web search, source-backed fact checking, URL reading, documentation search, and the Root-led Research Workflow with reproducible evidence."
---

# Smart Search CLI

Use Smart Search as the default execution layer for web retrieval and evidence-backed research. This file is a router: identify the user goal, load only the matching reference, and keep provider details and workflow mechanics out of the entrypoint.

## Decision Path

1. For an immediate answer, current fact, source discovery, or known-URL reading, start with `smart-search search "QUERY" --format json`. Read [`references/command-patterns.md`](references/command-patterns.md) when the task needs an explicit source route or evidence files.
2. When the user asks to “使用 smart-search-cli 的 Research Workflow 调研 <GOAL>” or a direct equivalent, read [`references/research-workflow.md`](references/research-workflow.md) before acting. The text after “调研” is the goal; preserve all supplied scope, source, time, language, cost, and output constraints.
3. When the user asks what workflows or research depths exist, run `smart-search modes` or `smart-search modes --format json`. The public workflows are `search` and Skill-level `Research Workflow`; `deep`, `research`, and `research-run` are advanced CLI interfaces.
4. For setup, configuration, credential storage, installed-Skill status, or endpoint diagnostics, read [`references/setup-config.md`](references/setup-config.md).
5. For any provider or recovery failure, read [`references/error-recovery.md`](references/error-recovery.md) before retrying, replaying, falling back, probing, or stopping.

## Research Depth Routing

Research Workflow supports three depth presets:

- `focused`: close the core question with a narrow but auditable evidence chain.
- `standard`: cover the core claims, main alternatives, and material limitations; this is the default.
- `deep`: broaden discovery, seek counterevidence, mine critical documents, checkpoint, and replan when material gaps remain.

Depth controls scope, discovery breadth, delegation pressure, document mining, cross-validation, replanning, and the stopping bar. It does not prescribe a fixed number of Subagents. Ordinary `search` does not use these presets.

## Shared Invariants

- Resolve ordinary CLI calls from the user's `PATH`. Research Workflow follows the source boundary in its reference and must not silently substitute another checkout or a compact single-agent command.
- Treat discovery snippets as candidates. Read key source bodies before using them for source-dependent or high-risk claims.
- Preserve commands, source URLs, provider-attempt facts, gaps, and citation mappings needed to audit the result. Never persist hidden reasoning, API keys, private configuration, or unauthorized source bodies.
- Keep fallback within the same capability. Do not use a page extractor as documentation search, Context7 as broad web search, or one main provider's credentials to fabricate another provider.
- Native web search is not an implicit fallback in this CLI-first workflow. If Smart Search is unavailable, report the blocker and recovery path.
- `doctor` is a diagnostic probe, not a repair operation. Do not repeat it as a generic recovery loop.

## Bundled AnySearch

For every Smart Search retrieval workflow, read [`bundled-skills/anysearch/CONTRACT.md`](bundled-skills/anysearch/CONTRACT.md) before deciding whether its general, vertical, batch, or URL-extraction capability applies. Invoke only the bundled Smart Search-owned adapter described there; do not wait for or request a separately installed `/anysearch` Skill.

AnySearch remains outside the Smart Search provider registry. Its adapter reads only Smart Search's private dual-key configuration and does not use project `.env` files, process credentials, or anonymous access. If the bundle, adapter, credentials, quota, or service is unavailable, record the gap and continue with other authorized routes when possible.

## Reference Router

| Need | Read |
| --- | --- |
| Named Research Workflow, depth behavior, Root lifecycle, persistence, final verification | [`references/research-workflow.md`](references/research-workflow.md) |
| Root/child ownership, ResearchRun contracts, project-agent roles, Claims, Trace, workspaces | [`references/agentic-research-architecture.md`](references/agentic-research-architecture.md) |
| Advanced `deep` planner and compact `research` executor | [`references/deep-research-mode.md`](references/deep-research-mode.md) |
| Command signatures, aliases, output fields, exit codes | [`references/cli-core.md`](references/cli-core.md) |
| Everyday commands, source-directed examples, evidence files | [`references/command-patterns.md`](references/command-patterns.md) |
| Intent routing, provider capabilities, provenance, same-capability fallback | [`references/provider-routing.md`](references/provider-routing.md) |
| Setup, private configuration, Skill installation, diagnostics | [`references/setup-config.md`](references/setup-config.md) |
| Error classes, retry/replay safety, cooldown, diagnostics, next actions | [`references/error-recovery.md`](references/error-recovery.md) |
| Regression, packaged-install checks, release lanes | [`references/regression-release.md`](references/regression-release.md) |

Keep future status-specific recovery guidance in `error-recovery.md`. Change code, tests, and specifications only when machine classification, automatic behavior, or a structured output contract must change.
