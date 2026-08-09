# Implementation Plan

## Ordered Work

1. Confirm `main` and PR heads are fetched and create/switch to `codex/integrate-smartsearch-prs-beta`.
2. Write Trellis planning artifacts, then run `task.py start 06-12-integrate-pr-fixes-beta`.
3. Load applicable specs with `trellis-before-dev`.
4. Integrate #12, #13, and #14 into the integration branch.
5. Resolve #12/#14 documentation semantics:
   - Runtime default remains platform temp.
   - Split skill docs describe platform temp in the Deep Research reference files.
   - Explicit stable output directory examples remain clearly labeled as explicit paths.
6. Verify public and packaged skill trees are synchronized.
7. Run source and CLI regression commands.
8. Merge the verified integration into `main`, push `origin/main`, and monitor GitHub Actions publish.
9. Verify npm `next` has advanced to the expected beta.
10. Upgrade local mise-managed `smart-search`, reshim, and run packaged regression.
11. Post separate GitHub comments on PRs #12, #13, and #14.
12. Commit and wrap up Trellis bookkeeping.

## Validation Commands

Source and packaging:

```powershell
.\.venv\Scripts\python.exe -m compileall -q src tests
.\.venv\Scripts\python.exe -m pytest -q
node npm/scripts/test-wrapper-repair.js
npm pack --dry-run
git diff --check
```

CLI:

```powershell
.\.venv\Scripts\python.exe -m smart_search.cli regression
.\.venv\Scripts\python.exe -m smart_search.cli smoke --mock --format json
.\.venv\Scripts\python.exe -m smart_search.cli deep "Deep research default evidence directory" --format json
```

Release and local upgrade:

```powershell
gh run list --branch main --limit 10
gh run view <run-id> --json status,conclusion,url,workflowName,headSha
npm view @konbakuyomu/smart-search dist-tags versions --json
mise use -g "npm:@konbakuyomu/smart-search@0.1.14-beta.7" -y --pin
mise reshim
where.exe smart-search
smart-search --version
smart-search regression
smart-search smoke --mock --format json
```

If npm publishes a newer beta number because another release lands first, replace `0.1.14-beta.7` with the live `next` value.

## Risk Controls

- Inspect `smart-search deep ... --format json` output directly and verify `evidence_dir`, `steps[].output_path`, and `steps[].command` agree.
- Search for stale `C:\tmp\smart-search-evidence` wording after integration; keep only explicit-output examples that are labeled as examples.
- Search for stale `@konbakuyomu/smart-search@next` reinstall hints; keep beta install mentions only where they are intentionally release-lane docs, not runtime repair advice.
- Do not push `main` before local checks pass.
- Do not post PR comments until integration and release validation are complete, so replies reflect the actual outcome.
