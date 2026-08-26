# 六家 Provider 官方错误与限流契约对 Smart Search 恢复目录的审计

## 结论

截至 2026-08-26，xAI、OpenAI、Exa、Tavily、Firecrawl 和 Jina Reader 的公开文档不能被压缩成“429 和 5xx 都重试、其余 4xx 都不重试”的单一规则。OpenAI 在同一个 HTTP 429 下区分临时速率限制、credits、组织或项目 spend limit 以及组织 usage limit；Exa 用 `tag` 区分权限、功能、robots 和内容策略等原因；Firecrawl 要求以错误表的 `Retryable` 列判断；Jina Reader 在本次核验中只提供限流维度，错误与重试契约仍缺少直接证据。[cite:c-xai-errors][cite:c-xai-rate][cite:c-openai-errors][cite:c-exa-errors][cite:c-tavily-errors][cite:c-firecrawl-errors][cite:c-jina-rate]

因此，Smart Search 的恢复目录需要同时保留共享 HTTP 分类与 provider-native identity。transport retry、same-capability fallback 和 logical replay 仍应分层理解；provider 文档可以解释上游错误，但不能替代 Smart Search 已观察到的本地 signature。[cite:c-openai-errors][cite:c-exa-errors][cite:c-firecrawl-errors]

本次交付只迁移并改写接受报告及其 citation mapping，不修改运行时 retry logic，也不声称迁移已经修复任何 provider error。

## 范围与方法

本报告比较六家 provider 的公开官方错误、限流和等待信号。broad `search` 与官方域名 discovery 只用于获得候选线索；进入正文的外部证据来自已保存且成功读取的 direct-source command output。核验日期统一为 2026-08-26。Jina 的错误体、429 header 和 backoff 证据状态为 `missing`，不是已验证的 provider contract。

本文使用的临时术语中，`error identity` 指能够改变恢复动作的 HTTP status、provider code/tag、SDK exception 或 response shape；`retry boundary` 指允许重试的错误集合、等待信号和最大尝试边界；`structured recovery` 指 CLI JSON 中机器可读的恢复字段。这些定义只服务本报告，不改变项目术语表。

## Provider-by-provider findings

### xAI

[Debugging Errors | xAI Docs](https://docs.x.ai/developers/debugging) 的 `Status Codes` 表列出 400、401、403、404、405、415、422 和 429；其中 429 的处理建议是降低请求速率或提高限额。[cite:c-xai-errors] [Rate Limits | xAI Docs](https://docs.x.ai/developers/rate-limits) 说明每个 team 按 model 维护 RPS 与 TPM 两个维度的限额，超过任一限额返回 429，并给出 exponential backoff 示例。[cite:c-xai-rate]

两页保存内容分别标注 `Last updated: May 13, 2026` 与 `Last updated: June 20, 2026`。[cite:c-xai-errors][cite:c-xai-rate]

xAI 的公开页面在本次保存内容中没有建立通用 5xx retry 表，也没有为本报告的 Claim 提供 `Retry-After`、reset header 或“请求尚未执行”的保证。因此，Smart Search 本地观察到的 exact `504 + upstream_server_error` 只能记录为本地 implementation signature；公开 xAI 文档既不把它建立为 provider contract，也不能据此证明 logical replay 安全。[cite:c-xai-errors][cite:c-xai-rate] 本报告不修改现有运行时行为，相关 replay policy 留待独立任务处理。

### OpenAI

[Error codes | OpenAI API](https://developers.openai.com/api/docs/guides/error-codes) 在 429 下分别列出 `credit_balance_exhausted`、temporary request rate limit、`organization_spend_limit_exceeded`、`project_spend_limit_exceeded` 和 `organization_usage_limit_exceeded`。同一页面明确说明，重试 billing、spend 或 quota 错误不会恢复 API access，必须先更新相应 credits 或 limit。[cite:c-openai-errors]

[Rate limits | OpenAI API](https://developers.openai.com/api/docs/guides/rate-limits) 将 `Retry-After` 定义为临时 rate-limit error 的最小等待秒数，并说明 `x-ratelimit-*` headers 提供 requests、tokens 和 reset 信息；因此，“等待 provider window”只能用于 temporary rate-limit 429，不能覆盖需要用户动作的 429。[cite:c-openai-rate]

对恢复目录的直接影响是：generic 429 不能只由共享 HTTP status 决定 operator action。credits、spend limit 和 usage limit 需要 user-action 分支；只有证据表明是 temporary rate limit 时，才适用等待窗口和 backoff。[cite:c-openai-errors][cite:c-openai-rate]

### Exa

[Error Codes | Exa](https://exa.ai/docs/reference/error-codes) 规定一般错误体包含 `requestId`、`error` 和 `tag`，并把 `tag` 作为程序化识别错误类型的字段；429 使用只含 `error` 的简化格式。[cite:c-exa-errors]

Exa 的 403 不等于单一的鉴权错误：官方标签包括 `ACCESS_DENIED`、`FEATURE_DISABLED`、`ROBOTS_FILTER_FAILED`、`PROHIBITED_CONTENT` 和 `CONTENT_FILTER_ERROR`。HTTP 422 也可能表示 `/contents` URL fetch 失败，或 `/websets` query decomposition 无法处理；`/contents` 还会在 `statuses` 中返回逐 URL 的错误标签。[cite:c-exa-errors] [Rate Limits | Exa](https://exa.ai/docs/reference/rate-limits) 另外按 endpoint 给出 QPS 表，例如 `/search` 为 10 QPS、`/contents` 为 100 QPS、`/answer` 为 10 QPS。[cite:c-exa-rate]

Exa 页面显示 `Error Codes` 最后修改于 2026-07-19，`Rate Limits` 最后修改于 2026-07-20。[cite:c-exa-errors][cite:c-exa-rate]

因此，恢复目录不应把 Exa 的全部 403 归入 `auth_error`，也不应把全部 422 解释成 parameter filtering。应先保留 provider-native `tag`、`requestId` 以及 `/contents` 的 per-URL status，再决定具体 operator action。[cite:c-exa-errors]

### Tavily

[Errors Code | Tavily Help Center](https://help.tavily.com/articles/8645538886-understanding-http-errors) 将 432 定义为 plan limit exceeded、将 433 定义为 pay-as-you-go limit exceeded；相应解决方案是升级 plan 或提高 PAYGO limit，而不是等待一个未被该页面定义的 reset。[cite:c-tavily-errors] 同一页面对 429 的建议是降低请求频率并使用 exponential backoff，500 则建议数分钟后重试。[cite:c-tavily-errors] 该帮助页的保存内容仍标注 `Last updated 1 year ago`，因此本报告保留核验日期 2026-08-26，并不把该页面时间标记解释成更精确的发布日期。[cite:c-tavily-errors]

[Rate Limits | Tavily Docs](https://docs.tavily.com/documentation/rate-limits) 按 development/production environment 及 endpoint 给出 RPM 表；429 响应包含 `retry-after` 秒数，官方要求 retry logic 尊重该值。[cite:c-tavily-rate]

对目录而言，432 的“wait for its reset”动作没有得到已保存官方错误页的支持，应改为 plan/PAYGO action 的证据边界；429 则应把 `retry-after` 作为最小等待信号，而不是只保留共享 status 分类。[cite:c-tavily-errors][cite:c-tavily-rate]

### Firecrawl

[Errors | Firecrawl Docs](https://docs.firecrawl.dev/api-reference/errors) 说明所有 non-2xx response 都返回 `success: false` 与 string `error`，部分 endpoint 还会提供 `details` 或 `code`。[cite:c-firecrawl-errors] 其错误表明确把 408、429、500、502、503、504 标为 `Retryable`，422 为 `Sometimes`，并指出 429 可区分 rate limit 与 concurrency limit。[cite:c-firecrawl-errors]

Firecrawl 的 retry guidance 要求以 `Retryable` 列为权威，不能只按 HTTP status 推断；429 在可用时带有秒数型 `Retry-After`，至少应等待该值。[cite:c-firecrawl-errors] 这支持把 provider-native matrix 作为上游解释层，同时保持 Smart Search 现有机器行为与本报告的 runtime out-of-scope 边界分离。

### Jina Reader

[Reader | Jina AI](https://jina.ai/reader/) 的限流页说明限制按 RPM 与 TPM 追踪，并按 IP/API key 执行；提供 API key 时，限流按 key 而非 IP 计算。Reader API 表还列出无 key、free、paid 和 premium key 的 RPM 档位。[cite:c-jina-rate]

同一页面的文字写作“tracked in three ways”，随后正文只列出 RPM 与 TPM；这是页面内部表述不一致。本次已保存的 Reader 页面没有公开 Reader error response shape、HTTP error table、429 retry、backoff 或 `Retry-After` 内容，因此 Jina 的 error identity 与 retry boundary 保持 `missing`。[cite:c-jina-rate]

这意味着目录中关于 Jina 429 可由 RPM、token、per-key/IP 或 concurrency 触发的更强说法，不能仅凭该官方 Reader 页面标记为 verified provider contract；需要实现日志、测试或新的 sanitized signature 才能升级证据状态。[cite:c-jina-rate]

## 对恢复目录的审计结论

1. **OpenAI-compatible 429：高优先级。** 保留 exact `concurrency_limit_exceeded` 作为 Smart Search 已观察的本地 signature，但把 generic 429 的 operator action 拆成 temporary rate limit 与 credits/spend/usage limit；后者不能靠等待窗口恢复。[cite:c-openai-errors][cite:c-openai-rate]
2. **Exa 403/422：高优先级。** 以官方 `tag` 和 endpoint context 解释 403 与 422，不将其统一翻译成 `auth_error` 或 parameter error。[cite:c-exa-errors]
3. **Tavily 432/429：中高优先级。** 432/433 走 plan/PAYGO action；429 读取并尊重 `retry-after`。[cite:c-tavily-errors][cite:c-tavily-rate]
4. **Firecrawl retry matrix：中优先级。** 以 `Retryable` 列而不是 shared 5xx 分类作为 provider-native 解释边界；422 的 `Sometimes` 不能被简化为固定 retry/no-retry。[cite:c-firecrawl-errors]
5. **Jina 文档边界：中优先级。** 只把 RPM/TPM 与 IP/API-key 维度标为已核验；错误体、retry header、backoff 和 429 语义继续标记为缺口。[cite:c-jina-rate]

本轮还观察到一个独立的协调层问题：并行启动第二个 Smart Search invocation 时，接受结果记录了四次纯文本 `parallel Smart Search invocations are not permitted`，没有 JSON、`error_type` 或 `recovery`；这不是 provider 官方契约，也不应被误写成 provider error。该观察只作为 acceptance mechanics 保留，不在本次迁移中改变 CLI 或 runtime policy。

## 证据状态与限制

本报告中的 xAI、OpenAI、Exa、Tavily、Firecrawl 和 Jina 页面均保留了原始标题、URL、日期或 locator；成功读取的 direct-source 正文标为 `verified`。Jina 仅限流维度为 `verified`，错误与重试字段为 `missing`。broad `search` 的 content、discovery results 以及 `https://r.jina.ai/docs` 的失败读取（状态为 `unverified`）没有被用来证明 provider 官方契约。

报告比较的是 2026-08-26 能读取的公开文档，不证明每个 provider 的实时生产响应一定包含文档中的全部字段。文档可能变化；本报告不把未读取的 Smart Search 源码、配置或测试当作已核验依据。

## 接受材料中的执行观察

1. broad `search` 的 top-level result 为 `ok=true`；logical attempt 1 和 2 出现 `rate_limited`、HTTP 429、`concurrency_limit_exceeded`，attempt 3 成功，`logical_attempts=3`、`logical_retry_used=true`、`fallback_used=false`、top-level `recovery=null`；接受记录为等待内建 bounded logical replay、没有外层重试或 `doctor`。
2. 并行官方 discovery 的四次拒绝发生后，接受流程改变查询并逐条串行发起一次 fresh discovery；这改变了执行条件，不是原样重放失败命令。
3. Jina OpenAPI URL fetch 记录为 HTTP 422 `AssertionFailureError: Could not resolve hostname`；provider attempts 为 `tavily:empty`、`jina:parameter_error`、`firecrawl:empty`，`fallback_used=true`、`structured_recovery_present=false`；接受流程没有原样重试，而是把 Jina 主张收窄到成功读取的官方 Reader 页面。
4. `doctor_calls=0`，没有使用 native web、浏览器、直接 provider HTTP、`curl` 或 `wget`。
