# Index Stage G research outputs and references

## Goal

Create a committed Stage G document index and portable evidence bundle, add paper-style References bound to saved EvidenceItems, and link the benchmark task back to the source Research Workspace.

## Requirements

- Add one committed Stage G research index that connects the implementation
  plan, acceptance reports, saved Research Workspace, and Benchmark Trellis
  task.
- Add paper-style numbered `References` sections to the architecture review
  and Benchmark recommendation report.
- Bind each referenced external source to its saved `CandidateCard` identity
  and, when available, its mined `EvidenceItem` identities.
- Add reciprocal links from the Stage G engineering gate and Benchmark task
  evidence/handoff documents back to the shared research index.
- Add a local Workspace document index and reference register without changing
  authoritative Evidence, Claim, Trace, or citation-verification records.
- Export the long-lived, non-sensitive subset of the ignored Research Workspace
  to `docs/research-runs/run-stage-g-seq-20260823T191412Z/` so References remain
  traceable after a fresh Git checkout.
- Preserve the final dossier, candidates, CandidateCards, KeySourceProposals,
  EvidenceItems, ClaimRecords, citation verification, public Trace, artifact
  metadata, research context, methodology, main log, synthesis, and reference
  register in the portable bundle.
- Exclude raw webpage snapshots, SQLite indexes, duplicate checkpoints, task
  runtime directories, credentials, and machine-local absolute paths from the
  portable bundle.
- Preserve the current conclusions, scores, dates, source URLs, run identity,
  and the boundary that no Benchmark has been selected or run.

## Acceptance Criteria

- [x] Every committed Stage G report is reachable from the shared research
      index, and each report links back to that index.
- [x] The Benchmark task points to the shared index, source reports, and saved
      Stage G run rather than maintaining an isolated evidence list.
- [x] Architecture references cover the four mined public sources and the
      implementation/provenance sources cited by the review.
- [x] Benchmark references cover every recommended candidate and distinguish
      candidate-only sources from sources with mined EvidenceItems.
- [x] The local Research Workspace manifest indexes its reports, document
      index, and reference register.
- [x] All local Markdown links and referenced Candidate/Evidence IDs resolve.
- [x] Terminology validation and lint pass; the Git diff contains no unrelated
      tracked changes.
- [x] A fresh checkout can follow every committed Stage G report to the portable
      bundle and resolve its Candidate, Evidence, Claim, artifact-metadata, and
      public-Trace entrypoints without `.smart-search/`.
- [x] The portable bundle contains no raw snapshots, SQLite databases, duplicate
      checkpoints, credentials, or machine-local absolute paths.
- [x] Bundle counts match the authoritative local Workspace and the export
      manifest names every included and excluded artifact class.

## Notes

- This is a lightweight documentation and run-index repair. It does not change
  search execution, schemas, or product behavior.
