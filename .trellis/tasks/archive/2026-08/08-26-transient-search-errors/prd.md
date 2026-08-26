# Handle transient Smart Search errors across branches

## Goal

Make Smart Search distinguish and safely recover from the two transient failures
observed through the OpenAI-compatible relay:

- HTTP `429` with `concurrency_limit_exceeded`, where the request was rejected
  before execution and a bounded replay is safe.
- HTTP `499` / `request_cancelled`, where the caller or proxy ended the request
  and replay safety is unknown.

Keep Smart Search `main` read-only and aligned with its remote `origin/main`.
Implement the user-visible contract on `lwj_dev`, then integrate it into
`preview/multi-source-agentic-research`, preserving each development branch's
own changes. Synchronize the resulting `smart-search-cli` instructions through
the governed personal Skills repository and refresh the active macOS Skill.

## Requirements

1. HTTP `499` must have a stable public error type, `request_cancelled`, rather
   than falling through to generic `provider_error` or `network_error`.
2. `search --max-try` must cover only failures with a proven safe replay
   boundary:
   - the existing terminal xAI `504` + `upstream_server_error` case; and
   - OpenAI-compatible `429` responses that explicitly contain
     `concurrency_limit_exceeded`.
3. The two development branches must default `search` to `--timeout 120` and
   `--max-try 5`, and the help text must state the exact retry scope.
4. Generic `429` failures and HTTP `499` must not enter the logical replay
   loop. HTTP `499` must never be automatically replayed because the upstream
   submission outcome is not proven.
5. When bounded retries are exhausted, or when a `499` occurs, JSON and
   Markdown results must provide actionable recovery information. It must say
   whether replay is safe, recommend a cooldown, limit `doctor` to one probe,
   and avoid an unbounded agent-side retry loop.
6. `doctor` must remain a connectivity/configuration probe. Documentation must
   explicitly state that repeatedly running it does not repair provider state
   and can worsen a concurrency incident.
7. The bundled Skill source and packaged asset copy in each Smart Search branch
   must remain byte-for-byte synchronized.
8. The personal `smart-search-cli` package must be updated main-first, merged
   package-aware into `macos`, `oppo_windows`, and `oppo_linux`, and the current
   macOS runtime activation must be refreshed and hash-verified.
9. Preserve branch-specific provider, research, and platform adaptations. Do
   not replace a native package with a raw upstream directory copy.
10. Smart Search `main` must remain unchanged and equal to its remote
    `origin/main`; it is only the read-only baseline used before merging the
    implementation into the development branches.

## Constraints

- Do not change CPA / CLIProxyAPI behavior or configuration in this task.
- Do not broaden automatic retry to arbitrary timeouts, generic `5xx`, generic
  `429`, or cancellation failures.
- Do not expose query text in generated shell commands or expose provider
  credentials in diagnostics.
- Do not publish, push, tag, or release without separate user authorization.
- Preserve unrelated worktree changes. Use the existing preview worktree and
  isolated worktrees for the other Smart Search branches.

## Acceptance Criteria

- [ ] Provider-classification tests map HTTP `499` to `request_cancelled` and
      keep the existing taxonomy unchanged for other statuses.
- [ ] CLI tests prove that explicit `concurrency_limit_exceeded` retries within
      `--max-try`, succeeds when capacity returns, and stops at the configured
      bound.
- [ ] CLI tests prove that generic `429` and HTTP `499` perform one logical
      attempt only.
- [ ] Exhausted concurrency and cancellation results expose the documented
      recovery contract in JSON and useful guidance in Markdown.
- [ ] Parser tests prove the `120` second / five-attempt defaults and accurate
      `--max-try` help text on both development branches.
- [ ] Targeted provider/CLI/Skill-parity tests and each development branch's
      supported full test suite pass.
- [ ] `main` remains clean and equal to `origin/main`; `lwj_dev` contains the
      implementation and `preview/multi-source-agentic-research` contains the
      integrated implementation plus its branch-appropriate bundled Skill
      updates.
- [ ] Personal Skills `main`, `macos`, `oppo_windows`, and `oppo_linux` contain
      the synchronized package with provenance updated to the new `lwj_dev`
      source commit; relevant validation passes.
- [ ] The active macOS Codex/Claude Skill projections match the governed macOS
      package hash after refresh.
- [ ] Final handoff distinguishes working-tree edits, commits, activation,
      runtime verification, and the intentionally unperformed push/release.
