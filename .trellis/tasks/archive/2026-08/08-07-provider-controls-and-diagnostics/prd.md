# Fix provider controls and diagnostics

## Goal

让 Tavily 开关、provider error telemetry 和 live smoke 健康状态与真实执行一致。

## Requirements

- `TAVILY_ENABLED=false` 从 capability、routing、doctor、smoke 和 direct calls 全面禁用 Tavily且不联网。
- HTTP/timeout/network/parse/tool failures 映射到批准的稳定 error taxonomy。
- Tavily/Firecrawl exceptions 记录为 error attempts；正常空结果记录 empty。
- live smoke 增加 `status` 和 `skipped_cases`；degraded 保持 exit 0，failed 非零。
- 缺少可选 key 时明确 skipped/not_configured，禁止网络。

## Acceptance Criteria

- [ ] Tavily disabled no-network tests 覆盖 search、fetch、map、capability、doctor、smoke。
- [ ] error taxonomy 覆盖 400/401/403/408/422/429/5xx/timeout/network/parse。
- [ ] fallback attempt telemetry 区分 error 与 empty。
- [ ] smoke JSON/Markdown/content/exit tests 覆盖 healthy/degraded/failed/skipped。

## Out Of Scope

- 不新增 Firecrawl 开关，不更改 provider fallback 能力边界。
