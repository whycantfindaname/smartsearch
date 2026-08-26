# Agentic Multi-Source Research Architecture

Read this reference when a task needs Root-led multi-source research, project-agent delegation, caller-held run state, document mining, Claim-level evidence, or citation auditability. For the older single-command planner/executor contract, also read `deep-research-mode.md`.

## Semantic ownership

Root Agent is the sole semantic planner and synthesizer. Root interprets the full conversation and user constraints, creates and revises the research plan, decides when to replan or stop, and chooses the number and sharding of project agents. Smart Search never fixes task counts, agent counts, Curator thresholds, or a universal budget ledger.

Only Root creates `SearchTask`, `EvidenceMiningTask`, and `DelegateRequest` objects. A child may return gaps and suggestions in `DelegateResult`, but those fields are advisory data. Search Scout, Source Curator, and Evidence Miner cannot create tasks, spawn children, or delegate descendants.

Smart Search is the deterministic research kernel. It validates public contracts and stable identities, compiles Root-authored operations, executes internal capabilities and Provider Research Agents, normalizes candidates and evidence, registers immutable artifacts, appends run-local Trace events, and verifies citation integrity.

## Product modes and capability selection

The product exposes exactly three modes:

- `quick`: low-latency search and known-URL reading selected by Root.
- `standard`: multi-source verification and necessary source reading; Root may add AnySearch or Search Scouts when they can close a real gap.
- `deep`: broad discovery, critical-document mining, Provider Research Agents, and Claim-level synthesis.

Root selects capabilities from their observed live status. A status snapshot must distinguish configured, reachable, entitled, unavailable, timed out, and degraded states and include its observation time. Offline planning may use a snapshot only when its freshness is visible.

Provider Research Agents is the formal name for Firecrawl Agent, Jina DeepSearch, Exa Agent, and Tavily Research. In `deep`, all four enter the plan and configured capabilities are attempted concurrently as independent attempts; missing credentials, entitlement failures, timeouts, partial results, and successes are recorded separately. One failed attempt does not terminate the whole run.

The project-agent adapter defaults are model `gpt-5.6-luna`, reasoning effort `max`, and service tier `priority`. These values configure deployment adapters and do not define product acceptance.

## Caller-held run loop

Root or its harness holds the compact `ResearchRun` dossier. Preview does not promise an automatic resume workflow. Run artifacts and append-only Trace support audit after interruption, but the caller remains responsible for preserving and resubmitting the dossier.

For long `deep` runs, prefer a checkpointed caller loop: add the next Root-decided task or small parallel batch, execute it, and persist the returned dossier before planning the next step. Do not put every long Provider Research Agent and follow-up task into one `execute` call when the Harness has a shorter process deadline. If a process is interrupted, Trace may contain events that were appended before the caller received the updated dossier; treat the last persisted dossier as caller state and the Trace as audit evidence, not as an automatic resume point.

Use `smart-search research-run` for deterministic dossier operations:

- `capabilities` observes current capability status.
- `create` validates a Root-authored frame and initial Claim specifications and creates the dossier.
- `add-search-tasks` and `add-evidence-tasks` add only Root-authored tasks.
- `execute` runs compiled internal search steps and returns the updated dossier.
- `import` validates one child `DelegateResult` against its originating request and imports candidates, a `KeySourceProposal`, or evidence.
- `document` runs allowed document operations over registered artifacts.
- `claims` derives Root-directed `ClaimRecord` updates from validated evidence.
- `decision` records Root's next decision or stop reason.
- `verify` checks final citation mappings against the dossier and registered evidence. With an optional citation-marked `draft_report`, it also renders first-appearance citation numbers, one reader-facing References section, and a deterministic audit reference register. Existing callers that omit `draft_report`, including raw `final_synthesis` Workspace projection, remain compatible.
- `materialize` projects an existing dossier into a durable Research Workspace and may persist supplied legacy `final_synthesis` and `citation_verification` outputs plus an additive, already-verified `reference_register`.

Except for `capabilities`, each operation requires `--input` and `--artifact-root`; inspect `smart-search research-run <operation> --help` for the current public signature. Add `--workspace PATH` to persist the operation's returned dossier, and repeat `--checkpoint LABEL` when the caller needs immutable named snapshots. `materialize` requires `--workspace`. The artifact root contains run-local append-only artifacts and Trace and must not be treated as a global workflow database.

`smart-search deep` remains an offline rule-based plan seed. It cannot consume runtime results and replan semantically. `smart-search research` remains the compact live executor for the existing plan-discover-fetch-gap-check path; in the Root-led architecture, treat its generated answer as an execution artifact for Root to inspect, not as a replacement for Root's final synthesis.

## Research Workspace and visual inspection

Research Workspace preserves the important public state of a run without replacing the runtime contracts. Its structured projections include the latest Dossier, immutable named checkpoints, task state, Evidence and Claim records, optional authoritative citation verification, an optional derived audit reference register, and a metadata-only `public_trace.jsonl`. It also stores human-readable context, methodology, task notes, a public decision log, and optional `final_synthesis.md` with reader-facing References.

The structured Dossier, append-only Trace, Artifact Registry, Evidence, and Claim records remain authoritative. `citation_verification.json` is the authoritative result of final reverse-trace and locator checking. `final_synthesis.md` and its numbered References are the reader projection; `reference_register.json` is the derived audit projection that retains citation, ClaimRecord, EvidenceItem, snapshot, and locator mappings; `project_manifest.json` entrypoints are only the Workspace document index. None is a second workflow database or may mutate structured state. `public_trace.jsonl` exposes only stable public identities and event metadata from Trace.

For citation-backed final delivery, Root writes exact `[cite:<citation_id>]` markers and supplies the existing citation mapping to `research-run verify`. Repeated markers are valid. Smart Search numbers registered sources by first appearance, groups EvidenceItems by stable `source_id` rather than URL alone, validates every supplied mapping and displayed marker through the complete reverse trace and locator chain, and writes the three final projections only after validation succeeds. CandidateCards and URL-only discovery records cannot become formal report references.

Do not persist hidden reasoning, chain-of-thought, API keys, private configuration, or unauthorized source bodies in any workspace file. Public logs should record observable decisions, inputs, outputs, gaps, and status transitions without reconstructing private reasoning.

The visualizer is read-only and loopback-only. The user starts it in a separate terminal with `smart-search research-view WORKSPACE --port 8080`, then opens `http://127.0.0.1:8080`. Agents must not start or background the viewer automatically.

## Project agents

The distributable definitions in `../agents/` are canonical for the three project roles. Read the matching YAML before dispatch. Use a registered project adapter when the current Harness provides one; otherwise create a Harness child from the YAML instructions and deployment defaults. Repository-local `.codex/agents/*.toml` files are development adapters that project the same contracts into Codex while this repository is open.

### Search Scout

Search Scout receives a Root-authored `DelegateRequest` and `SearchTask`. It searches only the assigned angle and allowed capabilities, then returns candidates, usage observations, artifact references, gaps, and suggestions in one `DelegateResult`. If AnySearch is allowed, it reads the resolved AnySearch Skill and chooses an operation from that Skill rather than assuming a fixed command.

### Source Curator

Source Curator receives a Root-selected candidate shard. It classifies every input candidate as retained, deferred, or rejected and returns a reversible `KeySourceProposal` with reasons, coverage gaps, uncertainties, and artifact references. Root decides whether and how many Curators to use and how to shard candidates. Curator neither deletes candidates nor chooses final key sources.

### Evidence Miner

Evidence Miner receives an `EvidenceMiningTask` bound to one registered artifact or a tightly related artifact group and one `claim_spec_id`. Its allowed document operations are `search`, `open`, `navigate`, `read`, and `grep`. It returns locator-backed `EvidenceItem` records plus not-found items, parsing gaps, conflicts, and suggestions. It cannot broaden source scope or delete artifacts.

## AnySearch and external delegate boundaries

AnySearch remains an external Skill, never a Smart Search provider or fallback member. Resolve `../skills/anysearch/SKILL.md` from the bundled snapshot first; use an installed global `$anysearch` Skill only when the snapshot is missing or unusable. Read the resolved Skill and let the model select the operation. Do not edit or reinterpret the bundled snapshot as part of Smart Search architecture work.

AnySearch returns through `DelegateResult`. Its payload preserves the original query and source items; normalized source items enter the same `DiscoveryCandidate` pipeline as other discovery. Missing credentials, quota, network, or Skill files produce an explicit gap while other routes continue.

MinerU is also an external delegate boundary. A successful MinerU `DelegateResult.payload` supplies `source_artifact_id`, `markdown`, and `parser_version`. Import the result before document execution: Smart Search validates the source assignment, registers a derived Markdown snapshot, and replaces the inline Markdown in the dossier with its `artifact_ref`. `research-run document` rejects caller-supplied raw `mineru_results`; the Sidecar reads only the registered derived snapshot. MinerU does not become an internal document tool or configuration owner.

## Candidate and evidence lifecycle

All discovery outputs first become `DiscoveryCandidate` records. Deterministic identifiers such as canonical URL, DOI, repository plus commit plus path, paper version, and content identity support exact deduplication. Suspected syndication or event overlap stays as separate candidates connected by `related_cluster_id` and `independence`; do not semantically hard-merge it.

After normalization, Smart Search returns `CandidateCard` views plus count, estimated context size, grouping suggestions, and a raw index. Root may read all candidates or create any number of Curator shards by task, topic, source type, or another semantic boundary.

The Claim lifecycle is:

```text
ClaimSpec -> EvidenceItem -> ClaimRecord
```

`EvidenceItem` binds a stable `claim_spec_id` to a registered `artifact_id`, snapshot identity, canonical URL, retrieval time, typed locator, faithful excerpt or paraphrase, and `support`, `contradict`, or `qualify` stance. Evidence quality remains qualitative across authority, directness, freshness, methodological fit, independence, and locator quality.

`ClaimRecord` links supporting, contradicting, and qualifying evidence and records conflicts, gaps, citation mappings, and one qualitative status: `supported`, `contested`, `weakly_supported`, `unsupported`, or `unresolved`. Do not collapse these dimensions into a pseudo-precise confidence score.

## Registered-artifact document mining

The Search Toolkit sidecar accepts registered `artifact_id` values only. Agent-facing operations must reject arbitrary local paths, `file://` values, directories, and unregistered URLs. Fetch or crawl URLs through Smart Search first, then register the resulting snapshot.

The isolated Python 3.12 sidecar reuses Search Toolkit document models, splitting, indexing, and `search/open/navigate/read/grep` behavior with project adapters. It uses the configured OpenAI-compatible document embedding path and a local SQLite FTS5 plus small vector-matrix index. It does not require a Mistral API key or credits and does not use Vespa or Docker.

Use `smart-search research-environment install --python <python-3.12>` to create the isolated sidecar environment and `smart-search research-environment doctor` to inspect it. Sidecar, embedding, index, or MinerU failures become independent attempts and may degrade to ordinary fetched-text reading.

## Trace and citation reverse tracing

Trace is run-local and append-only from the first public contract. Each event carries stable run/task/step/attempt identity, timestamp, parent event when applicable, artifact references, event type, and public payload. Do not store hidden reasoning, API keys, private configuration, or unauthorized source bodies in Trace.

Before final delivery, every citation must reverse trace through:

```text
final citation -> ClaimRecord -> EvidenceItem -> task and attempt -> registered artifact snapshot -> Trace event
```

If any link is missing or a locator cannot resolve against the recorded snapshot, Root must repair the evidence path, downgrade the Claim, or disclose the gap before synthesis.
