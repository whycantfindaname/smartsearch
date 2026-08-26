# Research Report Finalization Contract

## 1. Scope / Trigger

This contract applies when `research-run verify` receives a Root-written Markdown
`draft_report`, or when a verified report and audit register are projected into a
Research Workspace. It spans runtime validation, CLI output, filesystem
materialization, and the read-only visualizer.

The structured Dossier, append-only Trace, Artifact Registry, EvidenceItems, and
ClaimRecords remain semantic authorities. `citation_verification.json` is the
authoritative reverse-trace validation result. The rendered Markdown report,
`reference_register.json`, and manifest entrypoints are reader, audit, and
navigation projections respectively.

## 2. Signatures

```python
verify_final_citations(
    dossier: ResearchDossier,
    *,
    citations: Sequence[Mapping[str, str]],
    artifact_root: str | Path,
    draft_report: str | None = None,
) -> dict[str, Any]

ResearchWorkspace.materialize(
    dossier: ResearchDossier,
    *,
    checkpoint_labels: Sequence[str] = (),
    final_synthesis: str | None = None,
    citation_verification: Mapping[str, Any] | None = None,
    reference_register: Mapping[str, Any] | None = None,
) -> dict[str, Any]
```

```text
smart-search research-run verify \
  --input JSON_OR_PATH --artifact-root PATH \
  [--workspace PATH] [--checkpoint LABEL]...
```

## 3. Contracts

- `draft_report` uses exact `[cite:<citation_id>]` markers. Display numbers are
  derived in first-appearance order; callers never author display numbers.
- Each citation mapping supplies `citation_id`, `claim_record_id`, and
  `evidence_id`. Exact duplicate mappings are idempotent; conflicting duplicates
  fail.
- A draft with nonempty citation mappings must use at least one supplied marker.
  Empty mappings plus no markers preserve the legacy/no-external-evidence path.
- References are grouped by stable `EvidenceItem.source_id`. Canonical URLs
  normalize aliases but do not replace the registered source and snapshot chain.
- The reader-facing `References` section contains only available bibliographic
  metadata and canonical URLs. It never contains CandidateCard, ClaimRecord,
  EvidenceItem, artifact, snapshot, attempt, citation, or Trace IDs.
- `reference_register.json` records display number, source identity and URL
  metadata, citation IDs, ClaimRecord IDs, EvidenceItem IDs and locators,
  task/step/attempt identity, artifact ID, snapshot ID, and raw artifact ref.
- `quick`, `standard`, and `deep` use the same finalization contract.
- A legacy caller may still supply raw `final_synthesis` and
  `citation_verification`. Replacing a finalized report without a replacement
  register removes the stale register only after Workspace run identity passes.

## 4. Validation & Error Matrix

| Condition | Required result |
| --- | --- |
| Marker has no supplied mapping | `ContractValidationError` names the marker |
| Same citation ID targets different Claim/Evidence pairs | Reject as conflicting duplicate |
| Mapping is CandidateCard-only or URL-only | Reject; discovery is not report evidence |
| Nonempty mappings but draft has no markers | Reject before Workspace writes |
| Claim, Evidence, task, attempt, artifact, snapshot, Trace, or locator link fails | Reject with the citation or broken link identified |
| Evidence and registered artifact canonical URLs conflict | Reject before rendering |
| Draft already contains a `References` heading | Reject; Smart Search owns final numbering |
| Register disagrees with verification, dossier, attempt ID, raw ref, locator, or source identity | `ResearchWorkspaceError` before final projections change |
| Register contains an unused displayed reference | Reject |
| Workspace belongs to another run | Reject without changing its report or register |
| Legacy report replaces a citation-backed report without a new register | Remove the stale register and its manifest entrypoint |

## 5. Good / Base / Bad Cases

- **Good:** two cited EvidenceItems with different locators and one `source_id`
  render one reference number; both locator mappings remain in the register.
- **Base:** citation-only `verify` without `draft_report` returns the legacy
  verification fields and does not synthesize report projections.
- **Good no-evidence base:** an empty mapping and marker-free draft may omit
  References; semantic writing rules remain responsible for expressing the gap.
- **Bad:** a URL copied from a CandidateCard is presented as support without a
  ClaimRecord and EvidenceItem backtrace.
- **Bad:** a new raw report is written while an older report's audit register is
  left attached.

## 6. Tests Required

- Runtime: first-appearance numbering, repeated markers, same-source
  deduplication, missing metadata, multiple locators, all three modes, unknown
  and malformed markers, conflicting mappings, no-marker mappings, invalid
  locator, CandidateCard-only input, and canonical URL conflict.
- Workspace: report/register/manifest persistence, byte-idempotence, authoritative
  field cross-checks including attempt ID and raw ref, unused reference and
  internal-ID rejection, legacy stale-register cleanup, wrong-run no-mutation,
  and validation failure before final projection changes.
- CLI: JSON returns verification plus rendered projections, Markdown/content
  returns the report, and one `verify --workspace` writes all final projections.
- Visualizer and release: projection labels remain distinct, source/package Skill
  mirrors match, package smoke passes, and `git diff --check` is clean.

## 7. Wrong vs Correct

### Wrong

```python
# URL presence is not evidence authority, and display numbers are not caller state.
draft_report = "Result [1]."
citations = [{"citation_id": "1", "url": candidate.canonical_url}]
```

### Correct

```python
draft_report = "Result [cite:citation-result]."
citations = [{
    "citation_id": "citation-result",
    "claim_record_id": claim.claim_record_id,
    "evidence_id": evidence.evidence_id,
}]
```

The runtime validates the complete chain, assigns `[1]`, renders one References
entry, and emits the separate audit register.
