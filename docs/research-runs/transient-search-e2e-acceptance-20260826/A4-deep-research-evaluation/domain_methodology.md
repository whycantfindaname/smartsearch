# Domain Methodology

This workspace follows the supplied ResearchDossier contract; it does not require or imply a separate methodology agent.

## Evidence Method

- DiscoveryCandidate and CandidateCard records are discovery inputs, not proof.
- KeySourceProposal records preserve retain, defer, and reject recommendations; Root remains responsible for source selection.
- EvidenceItem records bind a ClaimSpec to a canonical source URL, immutable artifact snapshot, typed locator, stance, and qualitative evidence dimensions.
- ClaimRecord status is derived from linked support, contradiction, qualification, conflicts, and explicit gaps; no synthetic evidence score is introduced here.

## Citation and Source Handling

- Final citations must reverse-trace through ClaimRecord and EvidenceItem to the task, attempt, artifact, snapshot, and raw reference.
- Trace records observable execution facts and public decisions; it is separate from evidence provenance and does not prove source truth.
- Provider response bodies and artifact bytes are not copied into these Markdown projections. Direct source URLs and bounded EvidenceItem text remain available for review.

Current dossier declares 24 ClaimSpec records and 24 EvidenceItem records.
