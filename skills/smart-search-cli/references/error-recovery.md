# Search Error Recovery

## Purpose

This document is the single extensible decision catalog for recovering from a
failed `smart-search search` invocation. It separates provider-level transport
retries from CLI-level logical replay. Agents must use the structured
`recovery` object when it is present and must not infer replay safety from a
vague error message.

When a new error is discovered, add its observed signature, submission
knowledge, and operator action to this catalog first. Do not copy the rule into
`SKILL.md` or another reference. Runtime code changes are needed only when the
new rule changes machine classification, automatic behavior, or the structured
output schema; a documentation-only operator response belongs here alone.

## Default budget

The default search command is:

```powershell
smart-search search QUERY --timeout 120 --max-try 5 --format json --output PATH
```

`--timeout` is the hard timeout for one logical search call. `--max-try` is the
maximum number of logical calls, including the first call. It is a bounded
safety budget, not a general retry switch. A result records
`logical_attempts`, `logical_retry_used`, and `logical_retry_max_attempts`.

## Decision matrix

| Observed outcome | Stable `error_type` | Automatic logical replay | Required handling |
| --- | --- | --- | --- |
| xAI HTTP `504` with `upstream_server_error` | `network_error` | Yes, within `--max-try` | Replay with the CLI budget only; stop on success. |
| OpenAI-compatible HTTP `429` with exact `concurrency_limit_exceeded` | `rate_limited` | Yes, within `--max-try` | Replay with the CLI budget and bounded backoff. |
| Generic HTTP `429` | `rate_limited` | No | Return the failure; do not turn ordinary rate limiting into a replay loop. |
| HTTP `499` | `request_cancelled` | No | The upstream may have accepted the request; do not duplicate it automatically. |
| Ordinary HTTP `5xx` | `network_error` | No | Preserve the failure and its provider attempts. |
| Timeout or network failure without a safe marker | `timeout` or `network_error` | No | A timeout does not prove that the request was not accepted. |
| Uncertain submission result | provider-specific or `network_error` | No | Treat the result as possibly committed; do not replay automatically. |

The safe cases require both the provider identity and the exact provider
marker. An unrelated message containing a marker is not sufficient.
Same-capability provider fallback is a separate decision and does not
authorize logical replay of the failed search.

## Structured recovery object

For actionable `concurrency_limit_exceeded` and `request_cancelled` outcomes,
failed search JSON includes `recovery` with:

- `kind`: `concurrency_limit_exceeded` or `request_cancelled`.
- `transient`: `true`.
- `safe_to_replay`: whether an automatic logical replay is safe. HTTP `499` is
  always `false`.
- `automatic_retry_exhausted`: whether the bounded automatic budget was
  consumed.
- `wait_seconds`: the cooldown to observe before a new action.
- `doctor_command`: normally `smart-search doctor --format json`.
- `doctor_max_attempts`: `1`.
- `recommendation`: the next action in plain language.

Markdown renders the same fields under `## Recovery`. Generated doctor
commands contain no user query or other search payload.

## Recovery procedure

1. Read the JSON result and preserve `provider_attempts`, `logical_attempts`,
   and `recovery`.
2. If no `recovery` object exists, do not add an agent-side retry loop. Follow
   the normal provider-specific diagnosis or evidence fallback contract.
3. For `concurrency_limit_exceeded`, wait `recovery.wait_seconds`, run
   `recovery.doctor_command` at most once, and make at most one fresh search
   only if the probe is healthy and the result is still required.
4. For `request_cancelled`, first check whether a usable result arrived through
   another channel. Only when it did not and the result remains necessary may
   the caller wait, run the one probe, and make one fresh search.
5. `doctor` is a diagnostic probe, not a repair operation. It does not clear
   upstream concurrency, cancel an already accepted request, or change
   provider configuration. Repeated probes add traffic and can worsen the
   incident.
6. Do not wrap the CLI in a shell-level `timeout`, call native web search as a
   silent fallback, or retry based only on `error_type`.

## Evidence and safety boundaries

- Keep the original query out of generated `doctor_command` values.
- Do not cite an unsuccessful search as evidence. If a fresh search is not safe
  or does not recover, use the ordinary source-discovery and `fetch` workflow
  and label the degraded path.
- Do not claim that HTTP `499` means the provider rejected the request; its
  defining property here is that submission state is uncertain.
