# Implementation: smart-search v0.1.15 stable release

## Ordered Work

1. Create and validate the clean release worktree/branch; integrate the four source commits and resolve conflicts without changing the original dirty workspace.
2. Implement Context7 candidate selection and AnySearch CLI/extract deltas; sync tests, README, public skill and packaged skill.
3. Enforce Tavily disable semantics, shared error taxonomy and truthful live smoke status; update provider contract and regression tests.
4. Add PR CI, release concurrency/stable-bump detection, clean tarball smoke, version `0.1.15` and beta/stable release notes.
5. Run focused checks after each child, then full-scope Trellis check and release gates. Produce beta publish evidence and stop before remote mutation unless separately authorized.

## Required Validation

```powershell
.\.venv\Scripts\python.exe -m compileall -q src tests
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe -m smart_search.cli regression
.\.venv\Scripts\python.exe -m smart_search.cli smoke --mock --format json
npm test
npm pack --dry-run
npm publish --dry-run --access public
git diff --check
```

- Build a `.tgz`, install it into a temporary npm prefix, and run `--version`, packaged `regression`, and mock smoke.
- Run exact secret/private-endpoint scans over changed and packaged files without printing configured values.
- Run targeted live probes only for configured providers; capture status and sanitized error type, not response secrets.
- Verify missing XAI/Zhipu MCP/Sciverse keys are skipped/not_configured and make no network call.

## Release Gates

- Gate A: all code/CI/package changes pass focused and full offline checks.
- Gate B: local tarball install passes.
- Gate C: owner authorizes commit/push and beta workflow dispatch.
- Gate D: exact `0.1.15-beta.1` install and live checks pass or have explicitly accepted external blockers.
- Gate E: owner authorizes merge and `v0.1.15` tag/stable publish.

## Rollback Points

- Baseline integration commit series before product maintenance changes.
- Provider behavior changes before CI/release metadata changes.
- Version/release metadata before any remote beta action.
