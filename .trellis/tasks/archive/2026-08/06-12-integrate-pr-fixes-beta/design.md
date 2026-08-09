# Technical Design

## Integration Strategy

Use `codex/integrate-smartsearch-prs-beta` as the only working branch. Pull the three PR changes into that branch and resolve overlaps there. `main` remains unchanged until the integrated branch has passed the full regression plan.

Do not rewrite contributor PR branches. The final comments on #12, #13, and #14 should point to the integrated result rather than asking contributors to rebase unless a follow-up is truly needed.

## Code Boundaries

Runtime changes are narrowly scoped:

- `src/smart_search/service.py` owns Deep Research planner defaults. The default evidence directory should use `tempfile.gettempdir()` plus `smart-search-evidence/<timestamp>-<slug>`.
- `tests/test_service.py` owns the regression proving the generated evidence directory is absolute, rooted under platform temp, and used by every planned output command.
- `npm/bin/smart-search.js` owns runtime repair messages for the npm wrapper.
- `npm/scripts/test-wrapper-repair.js` owns wrapper behavior regression.

Documentation and skill assets are split but must stay synchronized:

- Public skill: `skills/smart-search-cli/**`
- Packaged skill: `src/smart_search/assets/skills/smart-search-cli/**`

`tests/test_regression.py` should verify all markdown/YAML skill assets match across public and packaged copies.

## #12 / #14 Contract Reconciliation

#12 changes the real runtime default from a Windows-specific `C:/tmp/...` root to the platform temporary directory.

#14 moves Deep Research content out of `cli-contract.md` into focused references such as `deep-research-mode.md` and `command-patterns.md`. The integrated docs should therefore avoid keeping the platform-temp contract only in the old `cli-contract.md`. The contract should be present where users and agents will actually read the split docs:

- `deep-research-mode.md`: explain `evidence_dir` semantics and the default platform-temp root.
- `command-patterns.md`: show command examples that either use explicit `--evidence-dir PATH` or refer to the CLI-generated `evidence_dir`, without implying `C:/tmp` is the default.
- `cli-contract.md`: keep high-level pointers and cross-reference the focused docs.

The packaged copy must receive the exact same text.

## Release And Rollback

The release path is:

1. Verify the integration branch locally.
2. Merge or fast-forward the integration result into local `main`.
3. Push `main` to `origin/main`.
4. Watch the GitHub Actions publish workflow and verify npm `next`.
5. Upgrade local mise to the published beta and run packaged regression.

If local checks fail, keep fixes on the integration branch and do not push `main`.

If the GitHub Actions publish fails after pushing `main`, inspect the failed run and fix forward on `main` with another commit. Do not delete npm versions or force-push published history.

If npm `next` advances to a different version before this publish completes, recompute the expected next beta from live `npm view` and update validation accordingly.

## Risks

- #12 and #14 both touch the same Deep Research contract, so a clean textual merge can still leave stale semantics.
- The public and packaged skill copies can drift if only one tree is edited.
- `npm pack --dry-run` may surface packaging omissions after the reference split.
- GitHub Actions publish may take time or fail for external registry/auth reasons.
- Local mise may point at an older shim even after install, so final verification must use both `where.exe smart-search` and bare `smart-search --version`.
