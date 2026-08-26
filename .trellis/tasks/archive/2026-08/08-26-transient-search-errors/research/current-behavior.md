# Current behavior evidence

## Repository and branches

- Repository: `/Users/jasonliao/Desktop/code/Skills/5-knowledge/smartsearch`
- `main`: `ae02b4b`, tracks `origin/main`
- `lwj_dev`: `57c12bc`, tracks `fork/lwj_dev`
- `preview/multi-source-agentic-research`: `663fcf0`, tracks the matching fork
  branch and is the current worktree.
- `lwj_dev` descends from `main`; preview descends from `lwj_dev`.

## Error classification

`src/smart_search/provider_errors.py` maps `429` to `rate_limited`, `5xx` to
`network_error`, and other HTTP statuses to `provider_error`. It has no `499`
mapping and `request_cancelled` is not an approved error type.

## Provider retry layer

`src/smart_search/providers/openai_compatible.py` treats `408`, `429`, and
selected `5xx` responses as retryable. It honors `Retry-After` for `429` and
otherwise uses bounded exponential jitter. A final
`concurrency_limit_exceeded` can therefore appear only after this transport
layer is exhausted.

## CLI logical retry layer

- The retry predicate recognizes only an xAI Responses attempt containing both
  `HTTP 504` and `upstream_server_error`.
- Preview defaults to timeout `120` and max try `5`.
- `lwj_dev` defaults to timeout `90` and max try `1`.
- `main` exposes max try `1`, but its search execution path does not loop on
  `args.max_try`.
- Existing tests explicitly assert that nonmatching failures stop after one
  logical attempt.

## Diagnostics

`doctor()` performs live provider connection tests plus capability/configuration
checks. `diagnose_openai_compatible()` performs a lightweight chat check and
both streaming and non-streaming search-shape probes. Neither command mutates or
repairs provider state; repeated invocations add provider traffic.

## Skill state

The current Skill says to use `--timeout 120 --max-try 5` and not add an
agent-side retry loop, but it describes this only as resilient xAI behavior.
It classifies `429` generically and does not mention `499`, safe replay, a
cooldown, or a one-probe `doctor` limit.

The Smart Search repository keeps two bundled copies:

- `skills/smart-search-cli`
- `src/smart_search/assets/skills/smart-search-cli`

They are currently identical and must remain so.

## Personal Skills governance

The governed package is `main:skill-packages/smart-search-cli`. The macOS,
OPPO Windows, and OPPO Linux branches project it into `skills/smart-search-cli`
through package-aware merges. The current provenance points to Smart Search
`lwj_dev` at `57c12bc`.
