# Design: Smart Search workflow routing and research depth

## 1. Scope / Trigger

Smart Search has accumulated commands, product depths, provider routes, and a
Root-led Workflow in one Skill entrypoint. Users cannot predict which choices
are public workflows, advanced interfaces, or implementation details. The new
`modes` command and the public-to-Reference routing contract cross CLI, service,
Skill packaging, documentation, and managed activation layers.

## 2. Signatures

```text
smart-search modes [--format json|markdown|content] [--output PATH]

smart-search deep QUERY
  [--budget focused|standard|deep]
  [--evidence-dir PATH]
  [--format json|markdown|content]
  [--output PATH]

smart-search research QUERY
  [--budget focused|standard|deep]
  [--evidence-dir PATH]
  [--fallback auto|off]
  [--format json|markdown|content]
  [--output PATH]
```

The Research Workflow remains a Skill invocation:

```text
使用smart-search-cli的Research Workflow调研 <GOAL>
```

It is not a new CLI executor.

## 3. Contracts

### 3.1 Public information architecture

```text
Public workflows
├── search: immediate retrieval and source discovery
└── Research Workflow: caller-held evidence and Claim lifecycle
    ├── focused
    ├── standard (default)
    └── deep

Advanced interfaces
├── deep: offline rule-based plan seed
├── research: compact live executor
└── research-run: deterministic Root kernel
```

Subagent count is not a mode discriminator. Root may use zero or more project
Agents. The depth controls the permitted coverage and capability envelope, and
the evidence/stopping contract controls completion.

### 3.2 `modes` result

The service owns one static structured result so JSON and rendered output do
not duplicate semantics:

```json
{
  "ok": true,
  "mode": "modes",
  "public_workflows": [],
  "research_depths": [],
  "advanced_entrypoints": [],
  "notes": []
}
```

Each workflow records `id`, `purpose`, `invocation`, and whether research depth
applies. Each research depth records `id`, `default`, `claim_scope`,
`discovery`, `delegation`, `document_mining`, `cross_validation`, `replanning`,
and `stop_condition`. Each advanced entrypoint records its execution boundary
and how `--budget` affects it.

`modes` is deterministic and offline. It reads no private config and performs
no filesystem readiness, provider, entitlement, activation, or network probe.

### 3.3 Research depths

- `focused`: narrow, auditable evidence closure. Prefer direct/known sources;
  minimize delegation and replanning; stop after core Claims reach the minimum
  eligible evidence bar or return explicit gaps.
- `standard`: multi-source verification for core Claims and material limits;
  use project Agents and document mining when they close real gaps.
- `deep`: broad discovery, counterevidence and boundary search, critical
  document mining, Provider Research Agents, Claim-level synthesis, and
  checkpointed replanning.

No depth may turn discovery snippets into Claim evidence or weaken the
fetch-before-claim rule.

The legacy planner implementation maps the old bounded `quick` behavior to
`focused`. There is no `quick` compatibility alias. Unrelated variables such
as the OpenAI-compatible lightweight chat probe keep their existing names.

### 3.4 Skill progressive disclosure

`SKILL.md` owns only:

1. purpose and default route;
2. decision path from user intent to one Reference;
3. invariants shared by every route;
4. the conditional Reference router.

`research-workflow.md` owns the named trigger, source boundary, depth contract,
Root lifecycle, persistence, evidence finalization, language, and information
boundaries. `agentic-research-architecture.md` owns semantic roles, data types,
kernel operations, Workspace, Trace, and citation architecture.

The platform-specific `current-search-flow.md` does not belong in the governed
Skill. Stable routing and replay contracts remain in `provider-routing.md` and
`error-recovery.md`; private paths, active host models, and current availability
are not copied. Once `SKILL.md` is the router, `cli-contract.md` is redundant
and is removed.

## 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| `smart-search modes` | Return static success without provider/config access |
| `--format json|markdown|content` | Render the same structured contract |
| `--output PATH` | Use the existing output writer and exit behavior |
| `--budget quick` | Argparse/contract validation failure; no silent alias |
| `--budget focused` | Use the former bounded planner envelope |
| ResearchFrame `mode=quick` | Contract validation failure |
| ResearchFrame `mode=focused` | Valid |
| Focused evidence is insufficient | Return/record explicit gaps; do not lower evidence standards |
| Named Workflow outside preview source | Follow `research-workflow.md` and stop before retrieval |
| Removed Reference link remains | Regression/parity test failure |
| Platform snapshot text enters governed Skill | Regression test failure |

## 5. Good/Base/Bad Cases

- Good: `smart-search modes --format json` explains two public workflows,
  three depths, and three advanced interfaces without reading config.
- Base: `smart-search deep "question" --budget focused` emits a bounded plan
  containing a fetch step.
- Bad: `smart-search research "question" --budget quick` is rejected instead
  of silently translating an obsolete public value.
- Bad: the Skill tells every agent to load the full Root lifecycle or an OPPO
  Linux runtime snapshot for an ordinary search.

## 6. Tests Required

- CLI parser/output tests for `modes` JSON, Markdown, content, and output file.
- A no-probe test that replaces config/provider access with failing sentinels.
- Planner tests for `focused` caps and retained fetch.
- Contract tests accepting focused and rejecting quick.
- Skill tests proving the entrypoint routes to references, contains no detailed
  lifecycle/diagram/platform snapshot, and public/package trees match.
- README/spec tests for focused/standard/deep and the honest compact-executor
  boundary.
- Full suite, package data, tarball smoke, and branch/activation validation.

## 7. Wrong vs Correct

### Wrong

```text
SKILL.md contains every command, provider, project-Agent role, architecture
diagram, host path, and release procedure.
```

### Correct

```text
SKILL.md selects one Reference; that Reference owns the conditional procedure.
```

### Wrong

```text
research --budget focused guarantees the planner's four-step cap at runtime.
```

### Correct

```text
The current compact research executor records a focused plan but keeps its
existing fixed live pipeline; help states this limitation until runtime limits
are separately designed and implemented.
```
