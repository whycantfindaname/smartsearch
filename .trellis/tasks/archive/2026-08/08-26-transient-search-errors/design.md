# Design: transient search error handling

## Current behavior

Smart Search already has two retry layers:

1. The OpenAI-compatible provider performs transport-level retries for
   `408`, `429`, and selected `5xx` responses, honoring `Retry-After` when it is
   available.
2. The CLI performs logical retries only for an explicit terminal xAI `504`
   whose body contains `upstream_server_error`.

The current branch defaults are inconsistent. The preview branch uses
`--timeout 120 --max-try 5`; `lwj_dev` exposes `90/1`; `main` exposes the
argument but its search path does not consume `--max-try`. HTTP `499` is not in
the public provider taxonomy. A final `429 concurrency_limit_exceeded` is
therefore reported after one logical attempt, while a relay-side
`request_cancelled` is generic and has no replay-safety guidance.

## Replay boundary

The implementation distinguishes failures by whether the upstream has proven
that execution did not start.

| Failure | Submission knowledge | Automatic logical replay |
| --- | --- | --- |
| xAI terminal `504` + `upstream_server_error` | Existing explicit safe case | Yes |
| OpenAI-compatible `429` + `concurrency_limit_exceeded` | Explicitly rejected for capacity | Yes |
| Generic `429` | Reason may be quota, rate, or policy | No |
| HTTP `499` / `request_cancelled` | Caller/proxy cancelled; upstream outcome unknown | No |
| Timeout, generic `5xx`, network failure | Outcome not proven by this contract | No |

This keeps `--max-try` useful for the observed concurrency incident without
turning it into a generic replay switch that could duplicate work or billing.

## Error taxonomy

Add `request_cancelled` to `APPROVED_PROVIDER_ERROR_TYPES` and map HTTP `499`
to it in `classify_provider_exception`. The CLI exit-code mapping treats it as
a network/provider failure, preserving a nonzero network-class exit without
adding a new process exit code.

No new taxonomy value is needed for concurrency. It remains `rate_limited`,
with the provider body/code used to identify the narrower safe-retry case.

## Logical retry decision

Replace the xAI-only boolean helper with a small retry-decision helper that
returns a reason only for the two approved cases. Detection must inspect the
sanitized top-level error and `provider_attempts[]`, because different provider
paths preserve the upstream body at different levels.

The search loop will:

1. execute at most `args.max_try` logical attempts;
2. retain every provider attempt with its `logical_attempt` number;
3. sleep with the existing bounded jitter between approved attempts;
4. stop immediately for all other failures; and
5. report the retry reason and configured bound in the final result.

Defaults become `--timeout 120` and `--max-try 5` on the two development
branches. The loop is implemented on `lwj_dev` and integrated into preview;
Smart Search `main` remains the unchanged read-only baseline.

## Recovery result contract

Failed search output gains a compact `recovery` object only when special
handling is actionable:

- `kind`: `concurrency_limit_exceeded` or `request_cancelled`
- `transient`: `true`
- `safe_to_replay`: boolean
- `automatic_retry_exhausted`: boolean
- `wait_seconds`: bounded cooldown recommendation
- `doctor_command`: `smart-search doctor --format json`
- `doctor_max_attempts`: `1`
- `recommendation`: one human-readable next action

The existing top-level `recommendation` and `diagnose_command` fields remain
compatible. Markdown search errors render the recovery recommendation and next
command. The result must not synthesize a shell command containing the user's
query.

For exhausted concurrency, the recommendation is to wait for the cooldown,
run one `doctor`, and make at most one fresh search after the probe is healthy.
For `499`, the recommendation first explains that automatic replay is unsafe;
the caller may make a fresh search only when it still needs the result and has
confirmed that no usable result was returned.

## Skill behavior and extensible recovery catalog

Add `references/error-recovery.md` as the single source of truth for error
handling. It should contain the error taxonomy, replay matrix, structured
`recovery` fields, one-probe procedure, and an explicit section explaining how
to add a future error rule. A future documentation-only handling rule should
be added there without duplicating it in `SKILL.md` or the other references.

Keep the bundled `SKILL.md`, `references/command-patterns.md`,
`references/provider-routing.md`, and `references/setup-config.md` as concise
entry points that link to the catalog and describe only their local command or
provider responsibility:

- `--max-try 5` covers only the two exact safe-retry cases.
- A final concurrency failure permits one cooldown/recovery cycle, not another
  open-ended loop.
- `request_cancelled` never triggers automatic replay.
- `doctor` is a single diagnostic probe, not a repair command.
- Persistent failure is reported with the structured result rather than hidden
  behind native web search.

Runtime code changes remain necessary only when a new rule changes machine
classification, automatic behavior, or the structured output schema; a new
operator response can otherwise be documented in the catalog alone.

The source Skill and `src/smart_search/assets/skills/smart-search-cli` remain
identical within each branch.

## Branch integration

Keep Smart Search `main` unchanged and aligned with its remote main ref. Use
it only as the read-only implementation baseline. Implement and commit on
`lwj_dev`, preserve its xAI request-status lifecycle, then merge the updated
`lwj_dev` into `preview/multi-source-agentic-research`. This preserves the
existing ancestry and preview-only research runtime instead of copying files
between divergent trees.

The Trellis task remains in the existing preview worktree. Temporary isolated
worktrees host `main` and `lwj_dev` changes so the preview worktree and task
artifacts are not overwritten.

## Personal Skill synchronization

After all Smart Search branches pass:

1. audit the current macOS adaptation before updating the governed package;
2. copy the clean `lwj_dev:skills/smart-search-cli` package into
   `main:skill-packages/smart-search-cli`;
3. update the README provenance commit/ref while preserving portable local
   modifications;
4. commit the personal Skills `main` package;
5. run package-aware merges for `macos`, `oppo_windows`, and `oppo_linux`,
   resolving only genuine local adaptations;
6. validate each native branch; and
7. refresh the current macOS projections and verify source/cache/Codex/Claude
   hashes.

No branch is pushed or released as part of this task.

## Rollback

Each repository/branch is committed separately. A failed downstream merge can
be aborted without changing its branch. The Smart Search `main` implementation
ref remains the baseline and must not receive a task commit; the `lwj_dev`
implementation commit is the first rollback unit, preview integration is the
second, and native Skills merges/runtime activation are separate rollback
units. No destructive reset is required.
