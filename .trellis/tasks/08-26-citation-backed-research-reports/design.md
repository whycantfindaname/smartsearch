# Citation-backed research report design

## Ownership boundary

Smart Search owns source identity, snapshots, EvidenceItems, ClaimRecords,
citation mappings, deterministic rendering, persistence, and reverse-trace
validation. Language System owns the shared writing rule that decides when a
source-dependent Claim requires an adjacent citation, when an output requires
References, and how unsupported Claims must be expressed. The two repositories
share a behavior contract; neither copies the other's state.

## Data flow

```text
Root-written Markdown with [cite:citation_id]
        + citation mappings
        + ResearchDossier
                    |
                    v
research-run verify
  1. parse markers
  2. validate citation backtrace and locators
  3. group cited evidence by registered source identity
  4. number sources by first appearance
  5. render Markdown and References
  6. build reference_register.json
                    |
                    v
ResearchWorkspace.materialize
  final_synthesis.md
  evidence/citation_verification.json
  evidence/reference_register.json
  project_manifest.json entrypoints
```

## Contracts

### Citation markers

The draft uses stable citation IDs rather than author-supplied display numbers.
One marker may contain one citation ID. Adjacent markers may render as a compact
group if the current Markdown renderer can do so without ambiguous mapping.
Display numbers are assigned only after validation.

### Reference identity

The primary grouping key is the registered artifact/snapshot source identity.
Canonical URL normalization may merge aliases only when they resolve to the same
registered source. Multiple EvidenceItems and locators can point to one displayed
reference and remain distinct in the audit register.

### Reader projection and audit projection

`final_synthesis.md` contains ordinary bibliographic information and URLs.
`reference_register.json` contains internal IDs and locator detail.
`citation_verification.json` continues to prove the complete backtrace. None of
these projections becomes a second authority for Claims or Evidence.

### Failure behavior

Finalization is atomic. Validation completes before the report, register, or
manifest entrypoints are replaced. A validation failure returns a parameter or
contract error with the citation ID and failed link, leaving the last valid
Workspace projection unchanged.

## Compatibility

- Reuse the existing `verify_final_citations` and `ResearchWorkspace.materialize`
  path; do not introduce a new top-level report service.
- Keep accepting legacy caller-supplied `final_synthesis` and
  `citation_verification` payloads.
- Add optional finalized-report outputs without changing Dossier serialization
  for old runs unless a minimal backward-compatible metadata field is required.
- Preserve the visualizer's read-only relationship to Workspace projections.

## Expected implementation surfaces

- `src/smart_search/research_runtime.py`: marker validation, reference grouping,
  and rendered report result.
- `src/smart_search/research_workspace.py`: atomic reference-register and
  manifest projection.
- `src/smart_search/cli.py`: compatible `verify`/Workspace input-output wiring.
- `src/smart_search/assets/research_visualizer/`: expose report/reference audit
  status without treating Markdown as authority.
- `skills/smart-search-cli/` and packaged mirrors: document the final-delivery
  workflow and ownership boundary.
- Focused runtime, Workspace, CLI, visualizer, release-parity, and E2E tests.

## Rollback

The change is additive. Reverting the implementation and documentation removes
the renderer/register while leaving existing Dossiers, Evidence, Claims,
Workspaces, and caller-supplied reports readable. No data migration or service
cutover is required.

## Cross-repository dependency

The Language System companion task must describe numbered Markdown as the
general default when a multi-source durable output requires References, while
preserving user, venue, and existing-document overrides. It must not claim
ownership of rendering, indexing, or source storage. Smart Search
implementation can be verified independently; live Language System activation
is a separate managed-Skills publication step.
