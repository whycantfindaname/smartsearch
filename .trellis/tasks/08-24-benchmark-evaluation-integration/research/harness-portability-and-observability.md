# Harness Portability and Mode-Independent Observability

- Date: 2026-08-24
- Scope: current Smart Search checkout plus current official Harness documentation
- Status: planning only; no Harness, model server, Provider, or Benchmark was run

Exact reproducible queries, direct URLs, observed issue states and evidence
boundaries are preserved in `research/harness-web-sources.md`.

## Code Verdict

The current implementation is not yet end-to-end robust across Codex, Claude
Code, Pi, and OpenCode.

It already has a useful Harness-neutral core:

- versioned JSON contracts for ResearchFrame, SearchTask, DelegateRequest,
  DelegateResult, EvidenceItem, TraceEvent, and ResearchRun;
- a caller-held serializable ResearchDossier;
- deterministic Provider execution, artifact registration, citation checking,
  ResearchWorkspace materialization, and a read-only visualizer;
- canonical project-agent role definitions under
  skills/smart-search-cli/agents.

The missing layer is executable Harness portability. Only Codex currently has
project role adapters under .codex/agents. The Skill installer knows where to
copy a Skill for Claude Code, Pi, and OpenCode, but it does not launch their
children, translate the canonical YAML role definitions, normalize native
events, enforce the same model, or parse a terminal DelegateResult.

The accurate description is:

    Harness-neutral research protocol
      + Codex-oriented deployment artifacts
      - complete multi-Harness runtime

## Existing Mode and Visualization Boundary

ResearchFrame accepts quick, standard, and deep. The Root-led research-run path
creates Trace and can materialize a ResearchWorkspace for all three modes. The
visualizer reads mode from the dossier/manifest and has no literal deep-only
gate.

However:

- the legacy public deep planner and research executor do not automatically
  create the new ResearchWorkspace or Trace;
- current workspace and visualizer tests primarily use deep fixtures;
- the visualizer's six stages and agent-role vocabulary are fixed;
- public_trace.jsonl currently exposes only event identity metadata;
- Root replans/decisions, Agent launch/start/end, tool calls, retries,
  cancellation, claim derivation, citation verification, and final synthesis
  are not all represented as Trace events;
- there is no Benchmark run index linking every Case, Harness, and mode to its
  workspace.

Therefore the visualizer is data-format compatible with all modes, but the
end-to-end execution and test coverage are still deep-oriented.

## Required Common Harness Boundary

Every Harness adapter must implement the same lifecycle:

    DelegateRequest plus role contract
      -> launch native child
      -> execute Skill and tools
      -> capture native events
      -> return exactly one DelegateResult
      -> import result into the caller-held dossier

The adapter owns only Harness mechanics:

- isolated config/home/session;
- local Qwen endpoint and exact served model identity;
- canonical YAML role-to-native-agent projection;
- prompt/input injection;
- native process/session launch;
- timeout, cancellation, exit and retry observation;
- terminal DelegateResult parsing;
- raw native event storage;
- safe native-event-to-Trace normalization.

Root remains the semantic planner. Smart Search remains the deterministic
research kernel. No adapter may create a second evidence or workflow authority.

## Harness Feasibility

### Codex

Codex is the closest first adapter because the repository already contains
project Agent TOML files and the experiment can use an isolated CODEX_HOME plus
the Responses API. Current role files still name a hosted GPT model, so the
experiment must generate run-local overlays naming the exact SGLang-served Qwen
model and must prove from server logs that Root and every child used it.

### OpenCode

OpenCode documents custom OpenAI-compatible providers, including a Responses
provider, and native primary/subagent configuration:

- <https://opencode.ai/docs/providers/>
- <https://opencode.ai/docs/agents/>

It is a plausible direct SGLang client, but Smart Search still needs an
OpenCode role projection and event-to-Trace adapter.

### Pi

Pi's official SDK exposes model selection, Skills, project context, session
events, tool events, and an official subagent extension example:

- <https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/sdk.md>
- <https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/examples/extensions/subagent/index.ts>

It is also a plausible direct OpenAI-compatible SGLang client. The project
still needs a Pi extension/driver that converts the canonical role contract and
events into DelegateResult and Trace records.

### Claude Code

Claude Code expects Anthropic Messages semantics. Anthropic documents routing
Claude Code through an Anthropic-format LLM gateway:

- <https://docs.anthropic.com/en/docs/claude-code/llm-gateway>

SGLang has an Anthropic-compatible endpoint, but current upstream reports show
normal Claude Code plus Qwen tool flows can fail, including deferred
tool_reference history on Qwen3.8-27B:

- <https://github.com/sgl-project/sglang/issues/35692>
- <https://github.com/sgl-project/sglang/issues/24293>

Claude Code must therefore be a gated experimental adapter. It is not valid to
assume that the same SGLang deployment that passes Codex/OpenCode/Pi Responses
or Chat Completions will pass Claude Code. The exact pinned SGLang build must
pass multi-turn, multi-tool, deferred-tool, Subagent, and long-context
preflight. A protocol compatibility gateway or upstream-fixed build may be
required; it must not change the underlying Qwen checkpoint.

## Normalized Agent Trace

Raw native Harness events remain in the private Case output directory. Smart
Search imports only a safe, typed subset into its existing append-only Trace.
The normalized lifecycle should cover:

- harness_session_started and harness_session_completed;
- root_plan_created and root_replanned;
- delegate_requested, delegate_started, delegate_completed, delegate_failed,
  delegate_cancelled;
- tool_started and tool_completed with tool name, status, duration, usage and
  artifact references, but no hidden reasoning or secret-bearing payload;
- provider attempt events;
- checkpoint_materialized;
- claim_records_derived;
- root_decision_recorded;
- citation_verification_completed;
- final_synthesis_materialized.

Each normalized event needs run, Benchmark Case, Harness, mode, parent Agent,
role, task, step, attempt, timestamp, status, usage and native-event reference.
The existing Trace remains authoritative for public operational history.

## Visualization Requirements

1. quick, standard, and deep must always use the Root-led research-run path
   during evaluation and materialize one independent ResearchWorkspace.
2. Add parameterized tests proving all three modes render.
3. The viewer must distinguish completed-but-unused stages from waiting or
   failed stages so quick is not displayed as an incomplete deep run.
4. Add an Agent timeline derived from normalized public Trace events.
5. Keep hidden reasoning, private prompts, credentials and unapproved source
   bodies out of the public viewer.
6. Add a Benchmark run index:

       Benchmark Run
         -> Case
         -> Harness
         -> quick | standard | deep
         -> ResearchWorkspace viewer

7. Every score and error links back to the exact CaseAttempt and workspace.

## Cross-Harness Stability Measures

Keep Benchmark-native quality scores separate. Report Harness robustness with
operational measures:

- completed Case rate;
- valid DelegateResult rate;
- ResearchWorkspace materialization rate;
- citation-backtrace success rate;
- model/protocol/tool parsing failure rate;
- timeout/cancellation/provider failure rate;
- orphan or missing Trace-event count;
- latency, token/tool/Provider usage and peak GPU memory;
- native Benchmark score by Harness and product mode.

Do not merge these into one universal robustness score.

## Recommended Experiment Shape

1. Run protocol and Agent compatibility micro-tests for each Harness.
2. Run a small predeclared cross-Harness matrix using the same cases, Qwen
   checkpoint, reasoning setting, Smart Search commit, Provider configuration,
   scorer and failure policy:

       Harness: Codex | Claude Code | Pi | OpenCode
       Mode:    quick | standard | deep

3. Shuffle Harness and mode order within each Case and execute close in time to
   reduce live-Web drift.
4. Use the matrix to decide which Harnesses are stable enough for a larger
   Benchmark run. Do not multiply the complete public Benchmark by all twelve
   cells before the Pilot proves that this additional cost is informative.
