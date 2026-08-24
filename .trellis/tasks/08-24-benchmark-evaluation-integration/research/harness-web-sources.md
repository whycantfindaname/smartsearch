# Harness Web Research Sources

- Verified: 2026-08-24, Asia/Shanghai
- Scope: Codex, Claude Code, Pi, OpenCode and SGLang compatibility evidence used
  by the Harness portability assessment
- Status: documentation research only; no Harness or model endpoint was run

## Reproducible Search Log

The earlier exploratory calls did not persist a verbatim query log. To avoid
inventing historical keystrokes, the following exact normalized queries were
re-run on 2026-08-24 and are the reproducible search record for the saved
conclusions:

1. `site:docs.anthropic.com/en/docs/claude-code LLM gateway Anthropic Messages custom endpoint`
2. `site:github.com/sgl-project/sglang Claude Code Qwen3.8 tool_reference Anthropic endpoint`
3. `site:opencode.ai/docs OpenAI-compatible custom provider agents subagents`
4. `site:github.com/badlogic/pi-mono coding-agent SDK session events tools skills subagent extension`
5. `site:docs.sglang.ai OpenAI compatible API server quickstart SGLang`
6. `site:github.com/sgl-project/sglang SGLang OpenAI compatible server quickstart`

These queries are search intents made exact for reproduction; they are not
claimed to be byte-for-byte copies of the earlier unpersisted tool calls.

## Claude Code

### Official LLM gateway documentation

- Requested URL: <https://docs.anthropic.com/en/docs/claude-code/llm-gateway>
- Current destination observed during verification:
  <https://code.claude.com/docs/en/llm-gateway>
- Evidence used:
  - Claude Code can be pointed at an organization-operated gateway.
  - Provider-independent routing depends on the gateway exposing an
    Anthropic-format endpoint.
  - The gateway must continue forwarding new Claude Code protocol features as
    Claude Code evolves.
  - Anthropic explicitly says it does not support routing Claude Code to
    non-Claude models through a gateway.
- Design consequence: Qwen through Claude Code is an experimental,
  compatibility-gated path. Documentation proves the gateway protocol shape,
  not Qwen compatibility or support.

### CLI reference

- URL: <https://docs.anthropic.com/en/docs/claude-code/cli-usage>
- Evidence used: Claude Code exposes non-interactive/structured-output surfaces
  suitable for an isolated Driver, subject to version-specific verification.
- Linux action: pin the Claude Code version and verify the exact output/event
  contract rather than relying on this planning snapshot.

## SGLang

### OpenAI-compatible server

- URL:
  <https://github.com/sgl-project/sglang/blob/main/docs/docs/get-started/quickstart.mdx>
- Evidence used: SGLang documents Linux/NVIDIA deployment and an
  OpenAI-compatible HTTP API.
- Design consequence: Codex, OpenCode and Pi are plausible direct clients, but
  each still needs a real Tool Call and event-contract preflight.

### Issue #35692 — Qwen3.8 deferred tool references

- URL: <https://github.com/sgl-project/sglang/issues/35692>
- State observed: open; opened 2026-08-20.
- Reproduction reported by upstream: SGLang 0.5.17/main with the stock
  Qwen3.8-27B chat template. A `tool_reference` retained in Claude Code history
  can make later Anthropic `/v1/messages` requests fail with HTTP 500.
- Design consequence: this is the direct evidence for treating Claude Code +
  Qwen3.8 as gated rather than assumed working. Linux preflight must include
  ToolSearch/deferred-tool history and retries in the same session.
- Revalidation rule: check issue/linked-PR status and reproduce against the
  exact pinned SGLang commit; an open issue is evidence of risk, not proof that
  every future build remains broken.

### Issue #24293 — Anthropic streaming multi-tool event shape

- URL: <https://github.com/sgl-project/sglang/issues/24293>
- State observed: closed; opened 2026-05-03.
- Scope reported upstream: an Anthropic streaming sequence could emit a
  `text_delta` against an open `tool_use` block during multiple tool calls,
  causing the Anthropic SDK/Claude Code to reject the stream. The report used
  Qwen3.6-27B-FP8, not Qwen3.8-27B.
- Design consequence: retain a parallel/multi-tool streaming test, but do not
  describe this closed, different-model report as a current Qwen3.8 blocker.

### Issue #28792 — Claude Code prompt validation

- URL: <https://github.com/sgl-project/sglang/issues/28792>
- State observed: open; opened 2026-06-20.
- Scope reported upstream: Claude Code requests could fail or be interpreted
  incorrectly by SGLang's Anthropic endpoint because of prompt/message format
  validation. The report used Qwen3.6 and SGLang 0.5.11–0.5.13.
- Design consequence: retain a system-message and long-history protocol test;
  do not treat this issue as a Qwen3.8-specific reproduction.

## OpenCode

### Custom Provider

- URL: <https://opencode.ai/docs/providers/>
- Evidence used: OpenCode documents custom base URLs and custom
  OpenAI-compatible providers, including configuration for local endpoints.
- Design consequence: a run-local OpenCode config can point at the same SGLang
  Qwen endpoint without changing the checkpoint.

### Primary Agents and Subagents

- URL: <https://opencode.ai/docs/agents/>
- Evidence used: OpenCode documents primary/subagent modes and Task permissions.
- Design consequence: canonical Smart Search role YAML can be projected into
  OpenCode-native Agent definitions, but that projection and event importer do
  not exist in the current repository.

## Pi

### SDK

- Requested URL:
  <https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/sdk.md>
- Destination observed during verification:
  <https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/sdk.md>
- Evidence used: the SDK exposes programmatic sessions, model selection, Skill
  loading, lifecycle/event subscription and automated pipelines.
- Revalidation rule: the upstream repository/package identity changed or
  redirected during this research. Pin the actual Linux dependency commit and
  package name before implementing the Pi Driver.

### Extension and Subagent references

- Extensions:
  <https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/extensions.md>
- Subagent example:
  <https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/examples/extensions/subagent/index.ts>
- Evidence used: Pi provides Agent/Tool/session events and a Subagent extension
  pattern that can host the Smart Search project roles.
- Design consequence: the Pi Driver can likely use an extension/SDK boundary,
  but Smart Search still needs its own role projection, terminal
  `DelegateResult` parser and Trace normalizer.

## Codex and Local Code Evidence

Codex feasibility in this audit was primarily derived from the installed
`codex-sdk` Skill and the repository's `.codex/agents/*.toml`, rather than a
new web query. The code-level evidence and file locations are recorded in:

- `research/harness-portability-and-observability.md`

The current project Agent TOML files remain deployment artifacts, not proof
that an isolated SGLang/Qwen Benchmark Driver exists.

## Evidence Boundary

- Official documentation supports protocol and extension feasibility.
- GitHub Issues support risk hypotheses and required regression cases.
- Neither source type proves that the current Smart Search checkout works on a
  target Harness.
- Only the Linux protocol Micro-suite and 4×3 Pilot can provide runtime proof.
- Before implementation, re-open every URL, record current status/commit, and
  update this file if upstream behavior changed.
