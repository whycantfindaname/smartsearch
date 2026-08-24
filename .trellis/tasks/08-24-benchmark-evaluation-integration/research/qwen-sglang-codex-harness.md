# Qwen3.8, SGLang, and Codex Harness Plan

- Date: 2026-08-24
- Scope: planning only; no model, dataset, Provider, or judge call was run.
- Target: Linux host with eight NVIDIA A100 GPUs.

## Decision

Use Codex CLI as the first benchmark Harness and SGLang as the only model
server. Root Agent, Search Scout, Source Curator, and Evidence Miner all use
the same pinned `Qwen/Qwen3.8-27B` revision with the same reasoning setting.
The Smart Search product mode (`quick`, `standard`, or `deep`) is the treatment
variable; model, prompt wrapper, Provider configuration, benchmark cases, and
scorer remain fixed within a comparison.

The official Qwen repository documents SGLang deployment with tensor
parallelism four, 262,144-token context, `qwen3` reasoning parsing, and
`qwen3_coder` tool parsing:
<https://github.com/QwenLM/Qwen3.8#sglang>. The model card documents
`reasoning_effort` control and a native 262,144-token context:
<https://huggingface.co/Qwen/Qwen3.8-27B>.

## GPU and Serving Topology

Run two identical SGLang replicas:

```text
A100 0-3 -> Qwen3.8-27B worker A, TP=4
A100 4-7 -> Qwen3.8-27B worker B, TP=4
                    \ /
        SGLang HTTP Model Gateway
                    |
          one OpenAI-compatible URL
                    |
               Codex CLI
```

This uses all eight GPUs for two concurrent replicas instead of sharding one
27B model across all eight GPUs. SGLang continuous batching handles concurrent
Root/Subagent requests inside each replica. The exact A100 memory SKU, SGLang
container digest, CUDA/driver versions, model revision, KV-cache settings, and
maximum safe concurrency are measured and frozen during preflight rather than
guessed in this plan.

Use the HTTP gateway path. SGLang documents `/v1/responses` on its HTTP model
gateway, while its gRPC path does not yet provide the same complete endpoint
surface:
<https://github.com/sgl-project/sglang/tree/main/sgl-model-gateway>.
The implementation must pin a tested SGLang commit or image; the repository
HEAD observed during planning was
`95f5ecd3d26665423d3e6577a2a00c04f5cde733`.

## Isolated Codex Configuration

Each benchmark run uses a generated, run-local `CODEX_HOME`; it does not read
or modify the user's normal Codex configuration. The local provider points to
the SGLang gateway with `wire_api = "responses"`. `service_tier` is omitted:
it is a hosted-service control, not an SGLang experiment variable.

The run workspace is materialized from one Smart Search Git commit. A
benchmark-only overlay rewrites the project Agent TOML/YAML deployment defaults
to the same Qwen model and reasoning effort for Root, Scout, Curator, and Miner.
No Agent may retain `gpt-*`, a hosted endpoint, or a model fallback. A failed
local model request fails the case visibly instead of falling back to OpenAI or
another service.

The Harness launches one ephemeral Codex process per benchmark case and mode,
captures `--json` events, and never resumes a previous case. The prompt wrapper
contains only the benchmark question, selected Smart Search mode, required
Research Workspace path, and output format. It instructs the Root Agent to use
the project `smart-search-cli` Skill and the Root-led `research-run` flow; it
does not prescribe a fixed number of Subagents or Provider calls.

## Compatibility Gate Before Any Benchmark

The benchmark must not start until all of these pass against the exact pinned
environment:

1. SGLang readiness and model-list probes succeed.
2. Non-streaming and streaming `/v1/responses` requests succeed.
3. Qwen emits a valid function call and accepts the corresponding tool result
   in a second turn.
4. Codex completes a minimal local tool-call task through the SGLang provider.
5. Codex starts each project Subagent type and receives its structured result.
6. One five-minute Research smoke case creates a Research Workspace with Trace,
   artifacts, final answer, and citation backtrace.
7. SGLang and Codex logs prove every Root/Subagent model request used the pinned
   Qwen model; no hosted-model destination appears.

A failure is a compatibility bug to fix before evaluation, not permission to
change the model server or silently simplify the workflow.

## Live Search Boundary

Generation is local, but live search is intentionally real. Smart Search uses
the repository's normal configured/reachable/entitled Provider set. Before a
run, save masked capability status and Provider versions; during a run, retain
every Provider attempt, error, timeout, and usage observation. Do not buy
credits, auto-top-up, or switch to an unapproved key. Credit exhaustion remains
a scored case failure/degradation rather than being hidden.

This means model inference can be API-cost free, but a live-search run cannot
honestly promise zero external cost. The experiment records actual Provider
usage and distinguishes existing/free entitlement from additional paid spend.

## Mode Comparison

For every selected case, run `quick`, `standard`, and `deep` once with separate
Codex sessions and Research Workspaces. Shuffle the three-mode order per case
and execute them in a compact time block so live-Web drift does not always
favor the same mode. A failed mode remains in the denominator. Retries, if
needed for diagnosis, are stored as separate attempts and do not overwrite the
primary score.

Report each benchmark's native score by mode, plus latency, Provider/tool-call
counts, local model token usage, peak GPU memory, and failure rate. Do not turn
these into one project-specific total score.

## Run Layout

Benchmark outputs live outside the source checkout by default:

```text
<bench-root>/<run-id>/
  manifest.json
  cases/<benchmark-case-id>/<quick|standard|deep>/
    input.json
    codex-events.jsonl
    stderr.log
    final-answer.md
    case-result.json
    research-workspace/
    scorer/input.json
    scorer/output.json
  summaries/<benchmark>.json
```

`manifest.json` pins the Smart Search commit/tree state, Codex version, role
file hashes, Qwen model revision, SGLang/container/CUDA versions, GPU inventory,
benchmark commit/split, mode order, masked Provider-capability identity,
timestamps, scorer configuration, and failure policy. It stores no API keys.

## Observed Planning Pins

- Qwen3.8 repository HEAD: `2ea10dc725823bf7c3e21ce8557cbe15245132ae`
- SGLang repository HEAD: `95f5ecd3d26665423d3e6577a2a00c04f5cde733`
- Local planning Codex CLI: `0.148.0`; the Linux run must record and pin its own
  exact version.

These are planning observations, not permanent dependencies. Implementation
selects an exact tested revision and records it in the run manifest.
