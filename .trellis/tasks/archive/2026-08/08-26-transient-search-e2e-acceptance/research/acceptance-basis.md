# Acceptance basis

## Authority

This task validates the behavior completed under
`.trellis/tasks/archive/2026-08/08-26-transient-search-errors`. The archived
`prd.md`, `design.md`, `implement.md`, `research/current-behavior.md`, and
`research/relevant-contract.md` define the accepted retry, recovery, branch,
and Skill-synchronization boundary.

The current source contract is
`.trellis/spec/backend/provider-capability-contract.md`. The active operator
contract is `skills/smart-search-cli/SKILL.md` plus the focused
`skills/smart-search-cli/references/error-recovery.md` catalog. The packaged
asset copy under `src/smart_search/assets/skills/smart-search-cli` must remain
identical whenever a Skill correction is made.

## Verified planning-time state

Read-only checks on 2026-08-26 established:

- `main` and `origin/main` both resolve to
  `ae02b4b02f79104460a4ebcfc2778f73911bda9d`.
- `lwj_dev` resolves to
  `812dd3ba6a373febd8331cf734c11949af527eb1`.
- preview resolves to
  `01a32fb6bbbf41f7670faf60b796ab0dea452cc5`.
- All three Smart Search worktrees were clean before this task; preview then
  gained only the new untracked Trellis task directory.
- The source Skill and packaged asset directories had no diff.
- Source `search --help`, run with the Codex conda Python and `PYTHONPATH=src`,
  reported timeout `120`, max try `5`, and the two exact safe logical retry
  signatures.
- The global npm executable was
  `/Users/jasonliao/.nvm/versions/node/v24.14.1/bin/smart-search`, version
  `0.1.16`, and still reported max try `1`. It cannot be used for this
  acceptance.
- `/usr/bin/python3` was Python 3.9 without `httpx`. The source runtime must use
  `/Users/jasonliao/miniconda3/envs/codex/bin/python`, where `httpx 0.28.1` was
  available.
- Active Codex and Claude Skill entrypoints both resolved through the immutable
  macOS cache. Their `SKILL.md` hash matched the source at
  `b4c71c4c3f6db8c002f4926ab88fe901ec33837d5190b09e7cb02d4ee7957c71`.
- Their `error-recovery.md` hash matched the source at
  `724997917aa96f5cb833bae840879f5b5d03795cc0854dcdc20ae87e7c47b386`.
- Governed personal Skills heads were: `main`
  `cf56dae02b6ffac2c740d2229290a862f43bfdc8`, `macos`
  `ff048aefb647698091bd09d6abace74e2310eb57`, `oppo_windows`
  `3fce3bc4ecaa2a501cdebed5cdb84dc859d46686`, and `oppo_linux`
  `c279fa78f43b13090db69253e10f999583da274c`.
- Personal Skills provenance already pointed to the current Smart Search
  `lwj_dev` commit `812dd3ba6a373febd8331cf734c11949af527eb1`.

These values are the planning baseline. The harness must record fresh values at
execution time and treat drift as an explicit new baseline, not silently reuse
this snapshot.

## Language decisions

The Smart Search project has no project termbase or glossary entry for the
five terms that control this task. Language System global search also returned
no accepted result. The following mappings are session-resolved and are not
global proposals:

| Concept | Preferred form in this task | Scope |
| --- | --- | --- |
| fault injection | 故障注入（fault injection） | A parent-controlled provider response used to test recovery behavior |
| end-to-end acceptance | 端到端验收（end-to-end acceptance） | Research request through Skill, CLI, provider route, recovery, evidence, and report |
| test-information leakage | 验收信息泄露（test-information leakage） | A worker learning the hidden fault, expectation, credentials, or sibling results |
| Agentic IQA | 智能体式图像质量评估（Agentic IQA） | IQA methods whose agent or workflow actively chooses tools, stages, or collaborators |
| recovery policy | 恢复策略（recovery policy） | Rules that choose retry, fallback, diagnosis, fresh request, or stop behavior |

No `global-propose` action is authorized or needed.

## Acceptance implications

1. Runtime identity is part of every verdict because the installed npm CLI and
   source checkout expose different behavior.
2. Fault observation and research usefulness are independent gates. A correct
   error trace with an incomplete report fails; a good report that bypassed the
   fault is harness-invalid.
3. Search snippets remain discovery leads. Reports must fetch and inspect the
   direct official page, original paper, project page, or repository before a
   claim is `verified`.
4. The error catalog is the durable extension point. A new operator response
   normally changes one provider/channel chapter; machine classification,
   retry/fallback behavior, or output schema still requires code and tests.
5. QMD, personal Skills synchronization, and activation are consequences of a
   changed governed Skill source, not generic acceptance steps.
