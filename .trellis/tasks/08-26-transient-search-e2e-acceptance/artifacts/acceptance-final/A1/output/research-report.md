# 六家 Provider 官方错误与限流契约对 Smart Search 恢复目录的审计

## 结论

截至 2026-08-26，六家 provider 的官方契约不能归约为“429 和 5xx 都重试、其余 4xx 都不重试”。OpenAI 会用同一个 HTTP 429 表示临时速率限制、余额耗尽、组织或项目 spend limit、组织 usage limit；Firecrawl 明确要求以错误表的 `Retryable` 列为准；Exa 的 `tag` 会把鉴权、权限、内容策略、处理失败与请求校验分开。Smart Search 现有恢复目录的分层原则——transport retry、same-capability fallback、logical replay 分开——是正确的，但若只保留共享 HTTP 分类，会丢失决定 operator action 的 provider-native identity。[OpenAI Error Codes](https://developers.openai.com/api/docs/guides/error-codes)（`API errors`、`429` 各小节，verified）[Firecrawl Errors](https://docs.firecrawl.dev/api-reference/errors)（`Errors` 表、`Retry guidance`，verified）[Exa Error Codes](https://exa.ai/docs/reference/error-codes)（`Error Response Structure`、`API Error Tags`，verified）

本次发现四项可直接行动的目录缺口或不一致：

1. OpenAI-compatible 的 generic 429 operator action 写成“honor the provider window”，不足以处理 OpenAI 的 credits、spend limit 与 usage limit 429；这些错误必须先改变账户状态，等待窗口本身无效。
2. Exa 的 HTTP 403 被统一归为 `auth_error`，与官方 `ACCESS_DENIED`、`FEATURE_DISABLED`、`ROBOTS_FILTER_FAILED`、`PROHIBITED_CONTENT`、`CONTENT_FILTER_ERROR` 不一致；HTTP 422 也同时包含 URL fetch 或 query decomposition 的处理失败，不能一律解释为参数过滤错误。
3. Tavily 432 的目录动作包含“wait for its reset”，官方错误页只给出升级 plan；同时官方 429 明确返回 `retry-after`，目录没有把该 header 写入 operator boundary。
4. 本轮实际观察到并行启动第二个 Smart Search invocation 时只返回纯文本 `parallel Smart Search invocations are not permitted`，没有返回 JSON、`error_type` 或 `recovery`；CLI/local invocation channel 没有该 signature。

## 范围与方法

目标读者是维护 Smart Search provider classification、structured recovery 与 operator catalog 的工程人员。研究只比较 xAI、OpenAI、Exa、Tavily、Firecrawl 和 Jina Reader 的公开官方错误/限流文档，以及当前已激活的 `[REDACTED_LOCAL_PATH] 配置、gateway、manifest、密钥或进程环境。

关键概念在本报告中的临时定义如下，状态均为 `session-resolved`：`error identity` 指能够改变恢复动作的 HTTP status、provider code/tag、SDK exception 或 response shape；`retry boundary` 指允许重试的错误集合、等待信号和最大尝试边界；`structured recovery` 指 CLI JSON 中机器可读的恢复字段；`evidence locator` 指官方页面的 heading/table 或本地目录的行号。中心 Claim 是“共享 HTTP 分类不足以表达六家 provider 的恢复语义”，证据状态为 `verified`；Jina 的错误体和 retry header Claim 为 `missing`。

执行顺序遵守任务合同：先运行一次覆盖六家的 broad `search`；其内容仅作为候选线索。随后用官方域名限定的 `exa-search` 做 discovery，再以 `fetch` 打开直接页面。只有 `fetch` 成功且正文支持 Claim 的页面进入 verified sources。核验日期统一为 2026-08-26。

## 关键发现

| Provider | 官方 error identity | 官方 retry boundary | 限流与等待信号 | 证据状态与 locator |
| --- | --- | --- | --- | --- |
| xAI | 公开调试页以 HTTP status 与错误消息识别错误；列出 400、401、403、404、405、415、422、429。已检查页面没有支持 broad synthesis 所称统一 `error.type/error.code` 或 `x-ratelimit-*` header。 | 429 应降低请求速率；限流页给出最多 5 次、`2 ** attempt` 的 exponential backoff 示例。调试页未给出一般 5xx retry 表。 | 每模型 RPS 与 TPM；超限返回 429。未在已检查页面找到 `Retry-After`/reset header。 | `verified`：[Debugging Errors](https://docs.x.ai/developers/debugging) 的 `Status Codes`；[Rate Limits](https://docs.x.ai/developers/rate-limits) 的 `Per-model limits`、`Handling rate limit errors`。 |
| OpenAI | HTTP status、部分 provider `code` 与官方 SDK exception class 共同构成 identity。429 至少区分 `credit_balance_exhausted`、temporary request rate limit、`organization_spend_limit_exceeded`、`project_spend_limit_exceeded`、`organization_usage_limit_exceeded`。 | 临时 429、500、503 和部分 timeout/internal error 可在短暂等待后重试；credits、spend、usage/quota 类 429 必须先改变账户状态。自管 HTTP client 应限制 attempts 和总时长；官方 SDK 已对 eligible errors 自动重试。 | `Retry-After` 是临时 429 的最小等待秒数；还公开 request/token/project-token 的 limit、remaining、reset headers。缺失或无效时使用 exponential backoff with jitter。 | `verified`：[Error Codes](https://developers.openai.com/api/docs/guides/error-codes) 的 `API errors`、`RateLimitError`；[Rate Limits](https://developers.openai.com/api/docs/guides/rate-limits) 的 header 表、`Retrying with exponential backoff`。 |
| Exa | 一般错误体含 `requestId`、`error`、`tag`；429 使用仅含 `error` 的简化格式。`tag` 是程序化 identity；`/contents` 还在 `statuses` 中返回 per-URL tag 与 `httpStatusCode`。 | 429 使用 exponential backoff；500、502、503 在短暂等待后重试。400、401、402、404、409 需要修正输入、凭证、余额或资源状态。403 可能是权限、plan、robots 或内容策略；422 可能是处理失败。 | 官方 rate-limit 页只给 endpoint QPS；已检查页面未给出 `Retry-After` 或 reset header。 | `verified`：[Error Codes](https://exa.ai/docs/reference/error-codes) 的 `Error Response Structure`、`API Error Tags`、`Content Fetch Status Tags`；[Rate Limits](https://exa.ai/docs/reference/rate-limits) 的 endpoint table。 |
| Tavily | 官方错误页以 HTTP status 与 message 区分 400、401、432、433、429、500。 | 429 应降低速率并执行 exponential backoff；500 可在数分钟后重试。400/401 修正请求或 key；432/433 改变 plan/PAYGO limit。 | 429 响应包含 `retry-after` 秒数，官方要求 retry logic 尊重该值。不同 key environment 与 endpoint 有不同 RPM。 | `verified`：[Understanding HTTP Errors](https://help.tavily.com/articles/8645538886-understanding-http-errors) 的各 status 小节；[Rate Limits](https://docs.tavily.com/documentation/rate-limits) 的 rate tables、`Handling Rate Limit Responses`。 |
| Firecrawl | 所有 non-2xx 返回 `success: false` 与 string `error`，部分 endpoint 增加 `details`、`code`。官方表以 HTTP + typical `error` + `Retryable` 联合决定恢复。 | 明确 retryable：408、429、500、502、503、504；422 是 `Sometimes`；400、401、402、403、404、409、413 为 No。重试使用 bounded exponential backoff with jitter。 | 429 在可用时包含秒数型 `Retry-After`；必须至少等待该值。429 又区分 rate limit 与 concurrency limit。 | `verified`：[Errors](https://docs.firecrawl.dev/api-reference/errors) 的 `Error response shape`、`Errors` table、`Retry guidance`、`429 responses`。 |
| Jina Reader | 已检查官方 Reader 页面没有公开 Reader error response shape、HTTP error table 或 provider error code。 | 已检查页面没有 429 retry、backoff、`Retry-After` 或不可重试边界。 | 页面说明 RPM/TPM 按 IP/API key 计数，并列出 Reader endpoint 的 tier limits；正文写“tracked in three ways”却只列 RPM 与 TPM，属于官方页面内部计数表述不一致。 | 限流维度 `verified`，error/retry `missing`：[Jina Reader](https://jina.ai/reader/) 的 `Rate Limit`、FAQ `What's the rate limit?`。 |

### Smart Search 恢复目录的具体差异

**OpenAI-compatible 429：高优先级。** 目录把 exact `concurrency_limit_exceeded` 作为唯一允许 bounded logical replay 的 429，这是安全边界；但 generic 429 的 operator action 是“Honor the provider window”。OpenAI 官方明确说明 credits、spend limit 与 usage limit 429 不能靠重试恢复。目录应在已观察到相应 sanitized marker 后加入 user-action 分支，至少把“等待窗口”限定为 temporary rate-limit 429。当前依据：`error-recovery.md` lines 147–159（verified local）与 [OpenAI Error Codes](https://developers.openai.com/api/docs/guides/error-codes) 的 429 table（verified external）。

**Exa 403/422 与 provider-native tag：高优先级。** 目录 lines 178–181 将 400/422 归为 `parameter_error`、401/403 归为 `auth_error`。Exa 官方表明 403 可以是权限、feature、robots 或内容策略，422 可以是 URL fetch/query decomposition processing failure；一般错误还提供 `tag` 和 `requestId`，`/contents` 提供 per-URL `statuses`。建议先检查当前实现是否保留这些字段，再决定是改 machine classification 还是只增加 operator rule；不能只改文档声称已支持。依据：`error-recovery.md` lines 169–183 与 [Exa Error Codes](https://exa.ai/docs/reference/error-codes)（均 `verified`）。

**Tavily 432 与 429 header：中高优先级。** 目录 line 241 允许 Tavily 432 “wait for its reset”，官方页面只给出升级 plan；该等待分支为 `unverified`，应删除或补直接来源/真实 signature。目录 line 239 对 429 只说 shared classification 与 same-capability fallback，遗漏官方 `retry-after` 的最小等待语义。若当前 transport 没有把 header 安全投影到结构化输出，应把这一点记录为实现缺口，而不是让 Agent猜测。依据：`error-recovery.md` lines 231–244、[Tavily HTTP Errors](https://help.tavily.com/articles/8645538886-understanding-http-errors)、[Tavily Rate Limits](https://docs.tavily.com/documentation/rate-limits)（verified）。

**Firecrawl retry matrix：中优先级。** 目录 lines 266–278 把 `5xx` 统一交给 shared classification，并保留若干内部 scrape code；官方文档则要求以 `Retryable` 列为权威，并明确 response shape、408/429/500/502/503/504、422 `Sometimes` 与 `Retry-After`。建议将官方 identity 作为上游解释层，保持 Smart Search 已实现行为为机器权威；新增条目前仍需实现或真实 signature 证据。依据：`error-recovery.md` lines 259–292 与 [Firecrawl Errors](https://docs.firecrawl.dev/api-reference/errors)（verified）。

**Jina 文档支持边界：中优先级。** 目录 line 254 声称 Jina 429 可表示 RPM、token、per-key/IP 或 concurrency，并给出等待/降并发动作。官方 Reader 页面支持 RPM、TPM、per-key/IP 与独立的最大并发描述，但未把 concurrency 绑定到 429，也未给 error body、retry header 或 backoff。该目录条目可能来自实现观察，因此结论是“官方证据不足”，不是“实现错误”；需要现有测试/log locator 或一次 sanitized live signature 才能升级为 verified implementation contract。

**并行 invocation 拒绝：高优先级、直接观察。** 本轮并行发起五个 `exa-search` 时，一个成功，四个返回纯文本 `parallel Smart Search invocations are not permitted`；失败调用没有返回可回读的失败 JSON。目录的 CLI/local invocation channel（lines 109–119）只覆盖 argparse、版本漂移、参数范围与输出路径，缺少该协调层错误。若此拒绝是预期行为，应至少记录 submission state、串行 fresh request 边界与无 `doctor` 动作；若所有联网命令都承诺 JSON，应补 machine classification 和输出写入测试。

### 现有目录中保持正确的边界

xAI 官方建议应用层对 429 做 exponential backoff，而 Smart Search 目录禁止对 generic 429 做自动 logical replay；两者位于不同恢复层，不构成矛盾。目录 lines 57–66 对 transport retry、provider fallback、logical replay 的区分应保留。xAI 的 exact `504 + upstream_server_error` 和 OpenAI-compatible 的 exact `429 + concurrency_limit_exceeded` 是 Smart Search 实现契约；官方页面没有提供同样 marker 也不能推翻已观察、测试支持的本地规则。

## 来源核验与证据状态

所有列入 References 的页面均由指定启动器 `fetch` 成功打开，状态为 `verified`，locator 如下：

- xAI：`Debugging Errors > Status Codes`；`Rate Limits > Per-model limits / Handling rate limit errors`。
- OpenAI：`Error codes > API errors / RateLimitError`；`Rate limits > rate-limit headers / Retrying with exponential backoff`。
- Exa：`Error Codes > Error Response Structure / API Error Tags / Content Fetch Status Tags`；`Rate Limits > endpoint table`。
- Tavily：`Errors Code > 400/401/432/433/429/500`；`Rate Limits > Handling Rate Limit Responses`。
- Firecrawl：`Errors > Error response shape / Errors table / Retry guidance / 429 responses`。
- Jina：`Reader > Rate Limit` 与 FAQ `What's the rate limit?`；error identity 与 retry boundary 为 `missing`。

broad `search` 的 content 与 discovery results 均未作为 verified 证据。`https://r.jina.ai/docs` 的直接读取失败，状态为 `unverified`，未进入 sources。

## 限制

本报告比较的是 2026-08-26 可读取的官方公开文档，不证明每个 provider 的实时生产响应一定包含文档中的所有字段。Smart Search 目录自称以当前实现、tests 与已观察 signature 为机器权威；本任务没有读取其源码或测试，因此建议项分为“官方文档与目录文字直接不一致”和“需要实现证据确认”两类。

Jina 的官方 Reader 页面只能支持限流维度，不能支持错误体、429 header 或 backoff。Exa、Tavily 和 xAI 的公开页面没有为本次 Claim 提供统一 reset-header 契约；相关字段保持 `missing`，不采用 broad synthesis 的泛化。官方文档会变化，所有时间敏感事实的核验日期为 2026-08-26。

## 观察到的错误与恢复附录

1. broad `search`：top-level `ok=true`；logical attempt 1 与 2 实际出现 `rate_limited`、HTTP 429、`concurrency_limit_exceeded`，attempt 3 成功。`logical_attempts=3`、`logical_retry_used=true`、`fallback_used=false`、top-level `recovery=null`。动作：等待内建 bounded replay 完成，没有外层重试或 `doctor`。
2. 并行官方 discovery：四个 invocation 返回纯文本 `parallel Smart Search invocations are not permitted`，没有返回结构化失败 JSON。动作：并行条件结束后改写查询并逐条串行发起一次 fresh discovery；四条均成功。该动作改变了执行条件，不是原样重复失败命令。
3. Jina OpenAPI URL fetch：top-level `ok=false`、`error_type=parameter_error`；Tavily 与 Firecrawl attempts 为 `empty`，Jina attempt 返回 HTTP 422 `AssertionFailureError` / `Could not resolve hostname`，`fallback_used=true`、`recovery=null`。动作：不原样重试，不调用 `doctor`，缩小 Jina Claim 到已成功读取的官方 Reader 页面。

`doctor_calls=0`。没有使用 native web、浏览器、直接 provider HTTP、`curl`、`wget` 或其他网络路径。

## References

1. xAI, [Debugging Errors](https://docs.x.ai/developers/debugging), verified 2026-08-26.
2. xAI, [Rate Limits](https://docs.x.ai/developers/rate-limits), verified 2026-08-26.
3. OpenAI, [Error Codes](https://developers.openai.com/api/docs/guides/error-codes), verified 2026-08-26.
4. OpenAI, [Rate Limits](https://developers.openai.com/api/docs/guides/rate-limits), verified 2026-08-26.
5. Exa, [Error Codes](https://exa.ai/docs/reference/error-codes), page showed `Last modified July 19, 2026`; verified 2026-08-26.
6. Exa, [Rate Limits](https://exa.ai/docs/reference/rate-limits), page showed `Last modified July 20, 2026`; verified 2026-08-26.
7. Tavily, [Understanding HTTP Errors](https://help.tavily.com/articles/8645538886-understanding-http-errors), page showed `Last updated 1 year ago`; verified 2026-08-26.
8. Tavily, [Rate Limits](https://docs.tavily.com/documentation/rate-limits), verified 2026-08-26.
9. Firecrawl, [Errors](https://docs.firecrawl.dev/api-reference/errors), verified 2026-08-26.
10. Jina AI, [Reader](https://jina.ai/reader/), verified 2026-08-26.

## Execution Summary

- **Status:** Complete；六家 provider 均完成官方 discovery，10 个直接页面成功核验，Jina error/retry 证据缺口已显式保留。
- **Actions & Changes:** 仅在指定 output 目录创建研究报告、机器结果和 command JSON；未修改仓库。
- **Verification & Findings:** 对照当前 `error-recovery.md` 的共享分类、六家 channel 与 safe replay matrix；识别 4 项直接可行动缺口及 2 项需实现证据确认的边界。
- **Deviations & Risks:** 观察到并行 invocation 拒绝与 Jina OpenAPI fetch 失败；均按 structured/observable result 缩小路线，没有 native web 或 `doctor`。
- **Commands & Artifacts:** broad `search` 使用 `--timeout 120 --max-try 5`；所有联网步骤保存于 `output/commands/*.json`，主产物为 `output/research-report.md` 与 `output/run-result.json`。
