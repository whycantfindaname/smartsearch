<!-- TRELLIS:START -->
# Trellis Instructions

These instructions are for AI assistants working in this project.

This project is managed by Trellis. The working knowledge you need lives under `.trellis/`:

- `.trellis/workflow.md` — development phases, when to create tasks, skill routing
- `.trellis/spec/` — package- and layer-scoped coding guidelines (read before writing code in a given layer)
- `.trellis/workspace/` — per-developer journals and session traces
- `.trellis/tasks/` — active and archived tasks (PRDs, research, jsonl context)

If a Trellis command is available on your platform (e.g. `/trellis:finish-work`, `/trellis:continue`), prefer it over manual steps. Not every platform exposes every command.

If you're using Codex or another agent-capable tool, additional project-scoped helpers may live in:
- `.agents/skills/` — reusable Trellis skills
- `.codex/agents/` — optional custom subagents

Managed by Trellis. Edits outside this block are preserved; edits inside may be overwritten by a future `trellis update`.

<!-- TRELLIS:END -->

## Managed Repository Context

- Registry ID: `smartsearch` (Agent Infra companion manifest `manifests/companion-repositories.json`)
- Managed branch: `lwj_dev` (upstream mirror baseline: `main`, origin = konbakuyomu/smartsearch; publication: fork = whycantfindaname/smartsearch, branch `lwj_dev`)
- Repository convergence authority: Agent Infra registry and sync contract (fetch, classify, safe fast-forward)
- Owner workflow: this project's managed-project contract; product/runtime authority stays with this repository's own source and docs
- Delivery status: `delivery_contract` (v2).
- Read order: `AGENTS.md` -> `.jason-liao-agent-infra/managed-project.json` -> `.jason-liao-agent-infra/RUNBOOK.md` -> `.jason-liao-agent-infra/errors.md`
- Update triggers: managed branch or remote change; build/release chain change; platform activation change; service/config/secret ownership change; new stable error class; a completed reusable major update flow
- Provider/request recovery errors live in `skills/smart-search-cli/references/error-recovery.md`, not in the sync error catalog
