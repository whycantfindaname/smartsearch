# Generate citation-backed research reports

## Goal

Make every finalized Smart Search research report that relies on retrieved evidence
read like a paper: factual claims carry in-text citations, the report ends with a
clean numbered References section, and every citation remains machine-auditable
through the existing Claim and Evidence chain.

## Background

- `research-run verify` already validates `final citation -> ClaimRecord ->
  EvidenceItem -> task/attempt -> artifact snapshot -> Trace`.
- `ResearchWorkspace.materialize` currently persists caller-supplied
  `final_synthesis` and caller-supplied `citation_verification`; it does not
  render or check citation markers inside the report.
- The sibling `08-26-stage-g-reference-index` task repairs the saved Stage G
  documents and run index only. Its PRD explicitly excludes product behavior.
- The companion task is
  `jason-liao-language-system:.trellis/tasks/08-26-shared-citation-contract`.

## Requirements

### R1. Final-report input and verification

- Accept a caller-written Markdown report containing stable citation markers
  such as `[cite:<citation_id>]` together with the existing citation mapping.
- Resolve every marker through the existing citation backtrace before producing
  a finalized report.
- Reject unknown, duplicated-with-conflicting-target, unresolvable, or
  locator-invalid citation mappings. Do not infer support from a URL merely
  appearing in Trace or a CandidateCard.

### R2. Human-readable report rendering

- Render citation markers as numbered in-text citations in first-appearance
  order and append one numbered `References` section.
- Deduplicate reference entries by stable registered source identity, using the
  canonical URL only as a normalization input rather than a replacement for
  the saved artifact/snapshot identity.
- Include only sources cited by the report. A discovery-only CandidateCard may
  remain in the Workspace candidate index, but cannot appear as formal support
  for a report Claim.
- Omit unavailable bibliographic fields instead of inventing author, date,
  venue, DOI, title, or access information.
- Keep CandidateCard, EvidenceItem, ClaimRecord, artifact, and Trace IDs out of
  the reader-facing References section.

### R3. Machine-readable audit outputs

- Persist `evidence/reference_register.json`, mapping each displayed reference
  number to its citation IDs, ClaimRecord, EvidenceItems, artifact snapshot,
  locators, and canonical source metadata.
- Continue persisting `evidence/citation_verification.json` as the authoritative
  reverse-trace validation result.
- Preserve the structured Dossier, Evidence, Claim, Artifact, and Trace records
  as authorities; Markdown and the reference register are derived projections.

### R4. Product-mode and compatibility behavior

- The same finalization behavior applies to `quick`, `standard`, and `deep`
  whenever a mode produces a Research Workspace and evidence-backed final
  report.
- Extend the existing `research-run verify` plus Workspace materialization path
  instead of adding a second report workflow or bibliography service.
- Preserve existing `research-run materialize` inputs and existing Workspaces;
  raw caller-supplied projections remain readable, while the citation-backed
  final-delivery path is documented as the supported research-report workflow.
- A report with no external evidence may omit References only when it contains
  no source-dependent factual Claim and explicitly preserves the evidence gap.

### R5. Documentation and deterministic checks

- Update the Smart Search Skill source and packaged mirror, CLI contract,
  agentic research architecture, Workspace documentation, and visualizer labels
  to distinguish report References, the audit reference register, and the
  Workspace document index.
- Add focused success and failure-path tests for marker parsing, numbering,
  deduplication, missing mappings, invalid locators, candidate-only sources,
  persistence, packaged Skill parity, and all three product modes.

## Acceptance Criteria

- [ ] One `research-run verify` invocation can validate a citation-marked draft,
      render deterministic numbered citations and References, and materialize
      the result into a Research Workspace.
- [ ] Every displayed citation resolves through the full existing reverse-trace
      chain, and every displayed reference is used by at least one citation.
- [ ] Two citations to different EvidenceItems from the same registered source
      produce one reference entry while preserving both locators in the audit
      register.
- [ ] Unknown markers, conflicting mappings, invalid locators, and
      candidate-only evidence fail with actionable errors and do not write a
      partially finalized report.
- [ ] The human report contains no internal audit IDs; the reference register
      contains the complete machine mapping.
- [ ] `quick`, `standard`, and `deep` Workspace tests all cover the same report
      finalization contract.
- [ ] Existing materialization callers and previously saved Workspaces remain
      compatible.
- [ ] Focused tests, full Python tests, `npm test`, Skill parity, package smoke,
      Markdown link checks, terminology lint, and `git diff --check` pass.

## Out of Scope

- Changing Language System behavior; that belongs to the companion repository
  task.
- APA/MLA/Chicago/CSL/BibTeX rendering or reference-library management in the
  first implementation. The default output is numbered Markdown suitable for a
  durable research report.
- Building a global citation database, search index, or new service.
- Rewriting historical Stage G reports or taking ownership of the concurrent
  Stage G reference-index task.
- Changing the semantic authority or scoring model of `EvidenceItem` and
  `ClaimRecord` beyond the minimum compatible metadata needed for rendering.

## Notes

- No blocking product decision remains for planning. Numbered Markdown is the
  MVP default; publication-specific styles remain a later, evidence-backed
  extension.
- Implementation must not start until the user approves the final planning
  summary in a subsequent message.
