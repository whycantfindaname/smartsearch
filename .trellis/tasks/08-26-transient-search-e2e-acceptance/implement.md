# Implementation plan

## 1. Enter execution after the planning gate

- Present the final PRD/design/implementation summary and wait for explicit
  approval in a subsequent user message.
- Run `python3 ./.trellis/scripts/task.py start transient-search-e2e-acceptance`
  from the preview worktree only after that approval.
- Load the Trellis before-development guidance and relevant backend/provider
  spec before editing the harness or Smart Search code.
- Record all Smart Search and personal Skills heads and dirty state. Stop only
  when unrelated changes overlap a target file.

## 2. Build and self-test the task-local harness

- Add the loopback gateway, run preparation, neutral launcher, verifier, prompt
  templates, and standard-library harness tests described in `design.md`.
- Bind the launcher to
  `/Users/jasonliao/miniconda3/envs/codex/bin/python` and
  `PYTHONPATH=/Users/jasonliao/Desktop/code/Skills/5-knowledge/smartsearch-lwj_dev-wt/src`.
  Record the actual `lwj_dev` commit for every run.
- Prove with a synthetic local upstream that injection counts are exact,
  forwarding resumes at the intended ordinal, hop-by-hop headers are removed,
  and logs contain no placeholder secret or body text.
- Prove that the launcher exposes normal CLI arguments and does not append
  `--timeout` or `--max-try`.
- Prove each case receives a separate owner-only runtime directory, port,
  process group, event log, and output directory.
- Run a source `--help` check; reject the npm-installed executable as an invalid
  runtime for this acceptance.

## 3. Finalize prompts without fault leakage

- Read `~/.codex/SUBAGENT_ROUTING.md` before any dispatch.
- Generate one shared Language System Writing contract and five target prompts
  from the accepted positive specification.
- Give each worker only its target, neutral launcher path, output directory,
  active Language System and Smart Search Skill paths, and allowed output
  schema.
- Scan prompts for provider fault names, injected statuses, request ordinals,
  expected fallback routes, gateway ports, upstream URLs, keys, and verdict
  thresholds. Any hit blocks dispatch.
- Run an unread-agent check: the prompt must be sufficient to complete the
  research but insufficient to infer the hidden case.

## 4. Run preflight without consuming the doctor budget

- Check source/runtime identity, configured capability presence, loopback port
  availability, output permissions, and clean process startup without calling
  providers.
- Use config-source and capability metadata only; do not print values.
- Start each gateway and perform a local synthetic health check on a dedicated
  harness path that cannot consume the provider fault ordinal.
- If an unaffected fallback route required by a case is unavailable, repair
  the harness or select another already documented same-capability route before
  dispatch. Do not weaken the research target or fault.

## 5. Dispatch the five fresh subagents

- Wave 1: start A1 and A3 with fresh contexts and wait for both.
- Validate their event counts, CLI source identity, reports, result schema,
  citations, and security logs before continuing.
- Wave 2: start A2 alone. Enforce the one-command global doctor budget and
  confirm the initial `499` result remained a single logical attempt.
- Wave 3: start A4 and A5 with fresh contexts and wait for both.
- Do not tell workers which fault they should encounter. Do not help a worker
  by suggesting the expected recovery route after dispatch.

## 6. Judge, correct, and rerun

- Generate `verdict.json` from gateway events, CLI JSON, `run-result.json`, and
  report evidence. Parent inference must point to concrete artifact locators.
- Mark a case `HARNESS_INVALID` when the intended fault or source runtime was
  not observed. Correct the harness and rerun the same case.
- For a valid `FAIL`, locate ownership using the table in `design.md`.
- Implement runtime/test/Skill corrections on `lwj_dev` first. Keep
  `skills/smart-search-cli` and its packaged asset copy identical.
- Run the focused tests and branch-supported full suite, commit the correction,
  merge into preview, and rerun the same case with the corrected source commit.
- Continue until all five valid cases pass. A valid unresolved failure blocks
  task completion.

## 7. Preserve sanitized acceptance evidence

- Copy only sanitized final-run artifacts from `/tmp` into
  `.trellis/tasks/08-26-transient-search-e2e-acceptance/artifacts/<run-id>/`.
- Preserve per-case gateway events, CLI results, research report,
  `run-result.json`, `verdict.json`, and a parent `acceptance-summary.md`.
- Run exact-value secret scans using values loaded in memory without printing
  them, plus pattern scans for authorization headers, cookies, signed URLs,
  request bodies, hidden manifest fields, and sibling-case content.
- Keep invalid/failed-run metadata only when it is needed to audit a correction;
  sanitize it under the same rules and label its superseding run.

## 8. Conditionally synchronize the governed Skill

- If no Smart Search Skill source file changed, do not update personal Skills,
  QMD, the immutable cache, or active projections. Recheck and report existing
  commits and hashes.
- If the Skill changed, run the governed read-only adaptation audit, update
  `main:skill-packages/smart-search-cli` from the final clean `lwj_dev` commit,
  and update provenance.
- Commit personal Skills `main`, then run package-aware merges and native
  validation for `macos`, `oppo_windows`, and `oppo_linux`.
- Refresh the macOS governed activation and verify package/cache/Codex/Claude
  hashes. Run QMD only if the package workflow explicitly requires an inventory
  update caused by the new Skill source, and record that causal link.

## 9. Quality check, commit, and close

- Run harness tests, all correction-specific tests, Smart Search Skill parity,
  the branch-supported full suites after any product change, and
  `git diff --check`.
- Load and run Trellis check against every PRD acceptance criterion.
- Update `.trellis/spec/backend/provider-capability-contract.md` only if a valid
  case establishes a durable machine contract not already present.
- Commit preview task/harness/evidence artifacts. Product or Skill corrections,
  if any, must already have a preceding `lwj_dev` commit and preview merge.
- Archive the Trellis task and report Smart Search branch commits, conditional
  personal Skills commits, tests, source/runtime identity, per-case live
  research results, activation/hash evidence, and the absence of push/tag/
  release actions.

## Validation commands

Exact harness commands are added with the implementation, but the final gate
must include these repository checks when their surfaces change:

```bash
PYTHONPATH=src /Users/jasonliao/miniconda3/envs/codex/bin/python -m pytest -q
PYTHONPATH=src /Users/jasonliao/miniconda3/envs/codex/bin/python -m smart_search.cli smoke --mock --format json
diff -qr skills/smart-search-cli src/smart_search/assets/skills/smart-search-cli
git diff --check
python3 ./.trellis/scripts/task.py validate transient-search-e2e-acceptance
```

Pure task-local harness changes run their own tests and do not force an
unrelated full Smart Search suite. Any Smart Search runtime, test, or Skill
correction does require the branch-supported focused and full gates.

## Review gates and rollback points

- Gate A: no implementation or dispatch before the post-artifact user approval
  and `task.py start`.
- Gate B: no subagent dispatch until synthetic gateway/redaction tests pass and
  prompts pass the leakage scan.
- Gate C: no later wave after a shared harness/security defect is detected.
- Gate D: no `PASS` without both injected-fault evidence and a useful
  direct-source research report.
- Gate E: no personal Skills sync without an actual Smart Search Skill source
  change.
- Gate F: no task completion while a valid case remains failed.
- Abort only the affected merge/process group when a conflict or runtime
  failure occurs; preserve unrelated work and already valid evidence.
