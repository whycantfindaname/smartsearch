# Stage G Portable Research Evidence Bundle

> Run ID: `run-stage-g-seq-20260823T191412Z`
> Mode: `deep`
> Research period: 2026-08-23 to 2026-08-24
> Exported: 2026-08-26

This directory preserves the long-lived, non-sensitive evidence from the Stage
G Research Workspace. It lets a fresh Git checkout trace report references back
to discovery candidates, mined evidence, claims, artifact metadata, execution
attempts, and the public Trace without requiring the ignored `.smart-search/`
runtime directory.

This is a portable evidence bundle, not an executable Research Workspace. Raw
webpage snapshots, local search indexes, duplicate checkpoints, and per-task
runtime directories are intentionally excluded.

## Entry points

| Purpose | File |
| --- | --- |
| Run identity, counts, and portable entrypoints | [Project Manifest](project_manifest.json) |
| Included and excluded artifact classes | [Export Manifest](export_manifest.json) |
| Final structured research state | [Research Dossier](latest_dossier.json) |
| Paper-style source register | [References](references.md) |
| Discovery results | [Candidates](evidence/candidates.jsonl) and [CandidateCards](evidence/candidate_cards.jsonl) |
| Source-selection proposals | [KeySourceProposals](evidence/key_source_proposals.jsonl) |
| Mined evidence | [EvidenceItems](evidence/evidence_items.jsonl) |
| Final claims | [ClaimRecords](evidence/claim_records.json) |
| Claim-to-source verification | [Citation verification](evidence/citation_verification.json) |
| Observable execution events | [Public Trace](public_trace.jsonl) |
| Artifact identities and source URLs | [Artifact registry](artifacts.jsonl) |
| Human-readable run narrative | [Main log](main_log.md) and [final synthesis](final_synthesis.md) |

The intended provenance path is:

```text
Report reference
  -> CandidateCard or EvidenceItem
  -> ClaimRecord and citation verification
  -> task and execution attempt in latest_dossier.json
  -> Artifact identity in artifacts.jsonl
  -> source URL and public Trace event
```

## Authoritative reports

- [Stage G research index](../../acceptance/stage-g-research-index.md)
- [Engineering gate](../../acceptance/stage-g-engineering-gate.md)
- [Architecture review](../../acceptance/stage-g-architecture-review.md)
- [Benchmark recommendations](../../acceptance/stage-g-benchmark-recommendations.md)
- [Benchmark task handoff](../../../.trellis/tasks/08-24-benchmark-evaluation-integration/HANDOFF.md)

## Included evidence

The bundle preserves 113 discovery candidates, 113 CandidateCards, 2
KeySourceProposals, 16 EvidenceItems, 2 ClaimRecords, 63 execution attempts, 28
public Trace events, and 27 artifact metadata records. Citation verification
records 16 successful Claim-to-artifact backtraces.

## Deliberate exclusions and limits

- `runtime/**/raw/*.bin`: downloaded webpage payloads are not committed.
- `runtime/**/document-index/*.sqlite3`: generated local search indexes are not
  portable evidence.
- `checkpoints/`: intermediate snapshots duplicate the final dossier.
- `task_task-*/`: task state and result files are represented by the final
  dossier and public Trace.
- Run-local report copies: the canonical reports live under `docs/acceptance/`.

Artifact IDs, snapshot IDs, `raw_ref` values, and original Trace references are
retained as historical provenance identifiers even when their payload files are
excluded. Consequently, this bundle can audit the recorded citation chain but
cannot independently replay character-range locator verification without the
original local snapshots.
