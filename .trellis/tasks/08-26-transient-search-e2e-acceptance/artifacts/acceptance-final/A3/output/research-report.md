# OpenAI Agents SDK、LangGraph 与 PydanticAI 的持久化、失败处理、人工介入和可观测性比较

## 结论

如果目标是让一个长时、分支化 workflow 在任意节点暂停、恢复、重试、检查和修改状态，LangGraph 的官方接口最完整：`checkpointer` 以 `thread_id` 保存 graph state checkpoint，`RetryPolicy` 和 `error_handler` 位于节点执行边界，`interrupt()` 与同一持久化层结合。其代价是开发者必须显式设计 graph state、thread、checkpointer 和节点副作用。[LangGraph Persistence，“Checkpointer vs. store”，verified](https://docs.langchain.com/oss/python/langgraph/persistence) [LangGraph Fault tolerance，“Retries”与“Error handling”，verified](https://docs.langchain.com/oss/python/langgraph/fault-tolerance) [LangGraph Interrupts，“Pause using interrupt”与“Resuming interrupts”，verified](https://docs.langchain.com/oss/python/langgraph/interrupts)

OpenAI Agents SDK 更适合以 agent run 为中心的应用。它没有把已核验的 persistence 接口表述为通用 graph checkpoint：`Session` 自动持久化对话历史，暂停审批则由可序列化 `RunState` 保存并恢复；model retry 是显式启用且带 replay-safety 判断的 runner 能力。这个边界更轻，但 session history、paused run state 与任意业务副作用的 durable workflow 不是同一件事。[OpenAI Sessions，“Core session behavior”，verified](https://openai.github.io/openai-agents-python/sessions/) [OpenAI Human-in-the-loop，“How the approval flow works”与“Long-running approvals”，verified](https://openai.github.io/openai-agents-python/human_in_the_loop/) [OpenAI Retry，`ModelRetrySettings`、`RetryDecision`，verified](https://openai.github.io/openai-agents-python/ref/retry/)

PydanticAI 的取向是组合式：核心 `Agent` 提供 tool/output validation retry，HTTP transport 处理网络层 retry，Deferred Tools 处理审批和外部执行；跨重启的 durable execution 则通过 Temporal、DBOS、Prefect、Restate 等官方支持集成实现，而不是要求核心 agent loop 自己成为 checkpoint runtime。它适合希望保留类型化 Python agent API、同时选择现有 durable executor 和 OpenTelemetry 后端的团队。[PydanticAI Durable Execution，“officially supports four durable execution solutions”，verified](https://ai.pydantic.dev/durable_execution/) [PydanticAI Agent API，`Agent.__init__(retries=...)`，verified](https://ai.pydantic.dev/api/agent/index.md) [PydanticAI Deferred Tools，开头与“Human-in-the-Loop Tool Approval”，verified](https://pydantic.dev/docs/ai/tools-toolsets/deferred-tools/) [Pydantic Logfire，“Using OpenTelemetry”，verified](https://ai.pydantic.dev/logfire/)

简化选型判断如下：需要原生 graph checkpoint 与任意节点暂停恢复，选 LangGraph；需要 OpenAI agent loop、审批状态和内建 tracing 的最短路径，选 OpenAI Agents SDK；需要强类型 agent API，并愿意把 durable execution 交给 Temporal/DBOS/Prefect/Restate，把 telemetry 交给 OTel/Logfire，选 PydanticAI。该判断针对 2026-08-26 访问到的 Python 官方文档，不代表三者所有语言实现或托管产品完全等价。

## 范围与方法

- 目标读者：需要为生产 agent workflow 做框架选型的工程师、研究人员和技术负责人。
- 研究范围：Python 官方文档中的 checkpointing/state persistence、retry/failure handling、human-in-the-loop、observability；不比较模型供应商覆盖、RAG、部署价格、性能或 TypeScript API。
- 截止日期：2026-08-26（Asia/Shanghai）。官方页面均按该日的 rolling/latest 文档读取；除 LangGraph fault-tolerance 页面明确标注 `langgraph>=1.2` 外，不推断未显示的包版本。
- 关键概念：检查点与状态持久化、重试与失败处理、human-in-the-loop、可观测性、run/session state。项目术语权威查询均无命中，因此这些中文映射仅为本报告的 `session-resolved` 用法。
- 检索方法：先调用 Context7 `context7-library` 做显式 library resolution；其 HTTP 503 结束后，按 structured error 类型转到同能力 Exa 官方域 discovery，再逐页调用 `fetch`。discovery 结果只用于定位；下文 `verified` Claim 均来自成功打开的官方页面正文。

## 关键发现

### 1. Checkpointing 与 state persistence

| 比较项 | OpenAI Agents SDK | LangGraph | PydanticAI |
| --- | --- | --- | --- |
| 持久化对象 | `Session` 保存 conversation history；暂停审批保存 `RunState`。[证据，verified](https://openai.github.io/openai-agents-python/sessions/) | checkpointer 保存单个 thread 的 graph state snapshots；store 保存跨 thread 的应用数据。[证据，verified](https://docs.langchain.com/oss/python/langgraph/persistence) | durable agent 的进度由 Temporal、DBOS、Prefect、Restate 集成保存；核心 Agent 可显式传递 message history。[证据，verified](https://ai.pydantic.dev/durable_execution/) |
| 主键/关联 | session ID；HITL 恢复时传同一 session 和 `RunState`。[证据，verified](https://openai.github.io/openai-agents-python/human_in_the_loop/) | graph config 中的 `thread_id`；checkpoint 属于 thread。[证据，verified](https://docs.langchain.com/oss/python/langgraph/persistence) | Deferred Tools 的跨 run 关联使用 `conversation_id`，后续 run 使用新的 `run_id`；durable executor 的 workflow identity 由所选集成定义。[证据，verified](https://pydantic.dev/docs/ai/tools-toolsets/deferred-tools/) |
| 恢复粒度 | 对话轮次或审批暂停点。[证据，verified](https://openai.github.io/openai-agents-python/human_in_the_loop/) | checkpoint/super-step 与 thread state；interrupt 在同一 thread 上恢复。[证据，verified](https://docs.langchain.com/oss/python/langgraph/interrupts) | Deferred Tools 的外部流程结束当前 run，再以历史和结果启动新 run；durable integration 的 checkpoint 粒度不在本报告核验范围内。[证据，verified](https://pydantic.dev/docs/ai/tools-toolsets/deferred-tools/) |
| 生产边界 | 提供 SQLite、Redis、SQLAlchemy、Dapr、MongoDB 等 session 实现，但 session 语义仍是对话历史。[证据，verified](https://openai.github.io/openai-agents-python/sessions/) | `InMemorySaver` 重启即丢失；官方建议生产使用持久 checkpointer。[证据，verified](https://docs.langchain.com/oss/python/langgraph/persistence) | 核心文档明确把跨失败/重启的 durable execution 放到四个官方支持方案中。[证据，verified](https://ai.pydantic.dev/durable_execution/) |

OpenAI 的 `Session` 在每次 run 前读取历史、run 后写入新 items；HITL 的 `RunState` 则可序列化并在审批后继续。两者合起来支持“对话连续性 + 审批暂停”，但已核验文档没有把 `Session` 定义为任意节点的 graph checkpoint，因此不能据此推断外部工具副作用会自动 exactly-once。[OpenAI Sessions，“Core session behavior”与“Resuming interrupted runs with the same session”，verified](https://openai.github.io/openai-agents-python/sessions/) [OpenAI Human-in-the-loop，“Long-running approvals”，verified](https://openai.github.io/openai-agents-python/human_in_the_loop/)

LangGraph 明确区分 checkpointer 与 store：前者保存 thread-scoped graph state snapshots，后者保存跨 thread 的应用键值数据；`MemorySaver`/`InMemorySaver` 不跨进程重启，生产需要 SQLite/Postgres 等持久实现。[LangGraph Persistence，“Checkpointer vs. store”与“MemorySaver does not persist between restarts”，verified](https://docs.langchain.com/oss/python/langgraph/persistence)

PydanticAI 官方 Durable Execution 页面承诺跨 transient API failure、应用错误和重启保存进度，并列出 Temporal、DBOS、Prefect、Restate；前三者以 PydanticAI capabilities 附加到 agent，Restate 集成位于 Restate SDK。这里的可持久化执行是 integration-level 能力，不应与普通 `message_history` 混称为内建 checkpoint store。[PydanticAI Durable Execution，全文，verified](https://ai.pydantic.dev/durable_execution/)

### 2. Retry 与 failure handling

OpenAI Agents SDK 的 runner-managed model retry 是 opt-in：`ModelRetrySettings.max_retries` 表示初次请求后的额外重试次数，policy 可读取 normalized error、provider advice、`response_started`、`replay_safety` 和 stateful request 状态。普通 `RetryDecision(retry=True)` 不会绕过 replay protection；只有显式 `approve_unsafe_replay=True` 才允许重复可能已发生的 provider-side work。失败则由 `AgentsException` 家族暴露，`RunErrorDetails` 保存 input、new items、raw responses、last agent 和 guardrail results。[OpenAI Retry，`RetryDecision`、`RetryPolicyContext`、`ModelRetrySettings`，verified](https://openai.github.io/openai-agents-python/ref/retry/) [OpenAI Exceptions，`RunErrorDetails`、`MaxTurnsExceeded`、`ModelBehaviorError`、`ToolTimeoutError`，verified](https://openai.github.io/openai-agents-python/ref/exceptions/)

LangGraph 把 retry 放在 node 边界：`add_node(..., retry_policy=RetryPolicy(...))`，参数包含 `max_attempts`、指数 backoff、jitter 和 `retry_on` exception filter；页面给出的默认 `max_attempts` 是 3（含首次尝试）。节点耗尽重试后可由 `error_handler` 接收 `NodeError`，再返回 `Command` 更新 state 或跳转到补偿路径。这比 agent-loop 级重试更适合为不同节点配置不同故障策略。[LangGraph Fault tolerance，“Retries”“Parameters”“Error handling”“Route with Command”，verified](https://docs.langchain.com/oss/python/langgraph/fault-tolerance)

PydanticAI 明确分层：`Agent(retries=...)` 控制 tool 与 output validation 的预算，整数同时设置两类，`AgentRetries` 可分别设置；当前 API 文档给出的默认值是两类各 1。网络请求 retry 另由 `AsyncHTTPX2TenacityTransport`/`HTTPX2TenacityTransport` 与 `RetryConfig` 配置，支持 `Retry-After`、指数 backoff、exception predicate 和停止条件，耗尽后重新抛出最后异常。把 validation retry 与 HTTP retry 混成一个数字会隐藏语义差异。[PydanticAI Agent API，`Agent.__init__` 的 `retries` 参数，verified](https://ai.pydantic.dev/api/agent/index.md) [PydanticAI HTTP Request Retries，“Usage Example”“Best Practices”“Error Handling”，verified](https://pydantic.dev/docs/ai/models/http-request-retries/)

### 3. Human-in-the-loop

OpenAI 的 HITL 专注敏感 tool call 审批：tool 通过 `needs_approval` 声明策略，run 返回 `interruptions`，调用方把 result 转为 `RunState`，执行 `approve()`/`reject()` 后把 state 交回 `Runner.run()`。审批覆盖 handoff 和 nested `Agent.as_tool()`，并可序列化后长时间暂停。[OpenAI Human-in-the-loop，“Marking tools that need approval”“How the approval flow works”“Long-running approvals”，verified](https://openai.github.io/openai-agents-python/human_in_the_loop/)

LangGraph 的 `interrupt()` 更通用：它可以出现在 node 的任意位置，使用 checkpointer 保存 graph state，并通过同一 `thread_id` 加 `Command(resume=...)` 恢复。官方同时警告 node 恢复会从头重新执行，因此 `interrupt()` 之前的副作用必须幂等；不能把 interrupt 包在宽泛 `try/except` 中。这使它适合审批、编辑 state、表单收集和调试，但也把副作用设计责任交给应用。[LangGraph Interrupts，“Resuming interrupts”“Review and edit state”“Rules of interrupts”，verified](https://docs.langchain.com/oss/python/langgraph/interrupts)

PydanticAI 以 Deferred Tools 统一审批和外部执行。`requires_approval=True` 或 `ApprovalRequired` 产生 `DeferredToolRequests`；调用方返回 `DeferredToolResults`。若 resolver 在进程内，可用 `HandleDeferredToolCalls` 在同一 run 继续；若在进程外，当前 run 结束，调用方携带原 message history 和 deferred results 启动新的 run，并用 `conversation_id` 维持关联。它是明确的跨 run continuation，不应描述成恢复原 run ID。[PydanticAI Deferred Tools，开头、“Resolving deferred calls with a handler”“Human-in-the-Loop Tool Approval”，verified](https://pydantic.dev/docs/ai/tools-toolsets/deferred-tools/)

### 4. Observability

OpenAI Agents SDK 默认启用 tracing，自动覆盖 runner、turn、agent、generation、function tool、guardrail、handoff 和 audio spans；可用 custom trace processor 替换或追加 exporter。两个关键边界是：ZDR 组织不可用该 tracing；generation/function spans 默认可能记录敏感输入输出，`trace_include_sensitive_data` 默认是 `True`，需要主动关闭。[OpenAI Tracing，“Default tracing”“Sensitive data”“Custom tracing processors”，verified](https://openai.github.io/openai-agents-python/tracing/)

LangGraph 的官方路径是 LangSmith tracing：设置 `LANGSMITH_TRACING=true` 和 API key 后记录 graph trace；非 LangChain 组件可用 `@traceable` 或 wrapper 保持上下文。换言之，LangGraph runtime 与 LangSmith observability 是相邻但分离的产品层，不能把本地 checkpointer 当作 telemetry backend。[Trace LangGraph applications，“With LangChain”与“Without LangChain”，verified](https://docs.langchain.com/langsmith/trace-with-langgraph)

PydanticAI 的 instrumentation 是可选的。启用 `logfire.instrument_pydantic_ai()` 后，每次 agent run 产生 trace，并为 model call 与 tool function execution 产生 spans；底层采用 OpenTelemetry，既可发往 Logfire，也可发往任意 OTel-compatible backend，甚至不用 Logfire SDK 而通过 `Agent.instrument_all()` 接入原生 OTel。[Pydantic Logfire，“Using Logfire”“Using OpenTelemetry”“OTel without Logfire”，verified](https://ai.pydantic.dev/logfire/)

## 来源核验与证据状态

| 来源 | 状态 | 可回读 locator | 支持范围 |
| --- | --- | --- | --- |
| OpenAI Sessions | verified | `Core session behavior`; `Resuming interrupted runs with the same session`; `Built-in session implementations` | conversation history persistence 与 session 恢复 |
| OpenAI Human-in-the-loop | verified | `How the approval flow works`; `Long-running approvals` | `RunState`、审批、序列化与恢复 |
| OpenAI Retry | verified | `RetryDecision`; `RetryPolicyContext`; `ModelRetrySettings` | model retry、replay safety、policy context |
| OpenAI Exceptions | verified | `RunErrorDetails`; exception classes | 失败分类与错误上下文 |
| OpenAI Tracing | verified | `Default tracing`; `Sensitive data`; `Custom tracing processors` | 默认 spans、ZDR、敏感数据、exporter |
| LangGraph Persistence | verified | `Checkpointer vs. store`; troubleshooting | thread checkpoints、store、生产持久化边界 |
| LangGraph Fault tolerance | verified | `Retries`; `Parameters`; `Error handling` | node retry、timeout、`NodeError`/`Command` |
| LangGraph Interrupts | verified | `Resuming interrupts`; `Rules of interrupts` | `interrupt()`、`Command(resume=...)`、幂等要求 |
| Trace LangGraph applications | verified | `With LangChain`; `Without LangChain` | LangSmith tracing 接入 |
| PydanticAI Durable Execution | verified | `Durable Execution` 全文 | 官方 durable integrations 与能力边界 |
| PydanticAI Agent API | verified | `Agent.__init__` 的 `retries`、`instrument` | validation/tool retry 与 instrumentation 接口 |
| PydanticAI HTTP Request Retries | verified | `Usage Example`; `Error Handling` | transport retry、backoff、耗尽行为 |
| PydanticAI Deferred Tools | verified | 开头；`Human-in-the-Loop Tool Approval` | inline handler 与跨 run continuation |
| Pydantic Logfire | verified | `Using Logfire`; `Using OpenTelemetry` | Logfire/OTel traces 与 spans |

没有以 `unverified` 或 `missing` Claim 填补比较空白。关于“某框架完全没有某能力”的绝对否定没有进入结论；报告只陈述本次打开的官方页面所定义的接口及由这些接口直接推出的边界。

## 限制

1. 三套文档均为 rolling/latest 页面，OpenAI Agents SDK 与 PydanticAI 页面未在正文显示统一包版本；因此以 2026-08-26 访问日期作为版本边界。LangGraph fault-tolerance 页面明确标注 `langgraph>=1.2`，但其他页面仍可能跨版本更新。
2. 比较的是 Python 文档。OpenAI Agents JS、LangGraph JS 和各托管平台可能有不同接口或发布时间。
3. 本研究核验接口语义，没有安装三个包或运行示例；因此不比较实际吞吐、数据库 schema、崩溃一致性、exactly-once、trace 成本或后端 SLA。
4. PydanticAI durable execution 的统一概览已核验，但没有逐一打开 Temporal、DBOS、Prefect、Restate 子页；本报告不比较四个 executor 的具体 checkpoint 粒度。
5. LangGraph fault-tolerance fetch 的部分说明段落在抽取结果中只保留了符号与参数表；报告仅使用可完整回读的接口、参数和示例，不扩写缺失段落。

## 观察到的错误与恢复附录

- `context7-library` 对 OpenAI Agents SDK resolution 返回 `ok=false`、`provider=context7`、`error_type=network_error`、HTTP 503；结果没有 `recovery`、`provider_attempts` 或 `logical_attempts`。依据 Context7 5xx 规则，没有原样重试，转到同能力 Exa 官方域 discovery。doctor 未被 structured recovery 要求，因此未调用。
- 首次并行启动三条 Exa discovery 时，LangGraph 成功，另外两条在 provider 前被启动器拒绝，消息为 `parallel Smart Search invocations are not permitted`，没有结构化 JSON。恢复动作是改为串行，并改变 OpenAI/PydanticAI 查询后重新提交；两条均成功。
- 一条 PydanticAI 精确 keyword discovery 返回 `ok=true`、`results=[]`、`total=0`。这是 empty discovery，不是错误；后续依据已打开的官方 API 文档内链接与更宽的官方域查询定位 direct pages，没有把空结果写成 provider failure。

## References

访问日期均为 2026-08-26。

1. OpenAI. [Sessions — OpenAI Agents SDK](https://openai.github.io/openai-agents-python/sessions/).
2. OpenAI. [Human-in-the-loop — OpenAI Agents SDK](https://openai.github.io/openai-agents-python/human_in_the_loop/).
3. OpenAI. [Retry — OpenAI Agents SDK API Reference](https://openai.github.io/openai-agents-python/ref/retry/).
4. OpenAI. [Exceptions — OpenAI Agents SDK API Reference](https://openai.github.io/openai-agents-python/ref/exceptions/).
5. OpenAI. [Tracing — OpenAI Agents SDK](https://openai.github.io/openai-agents-python/tracing/).
6. LangChain. [Persistence — LangGraph](https://docs.langchain.com/oss/python/langgraph/persistence).
7. LangChain. [Fault tolerance — LangGraph](https://docs.langchain.com/oss/python/langgraph/fault-tolerance).
8. LangChain. [Interrupts — LangGraph](https://docs.langchain.com/oss/python/langgraph/interrupts).
9. LangChain. [Trace LangGraph applications — LangSmith](https://docs.langchain.com/langsmith/trace-with-langgraph).
10. Pydantic. [Durable Execution — PydanticAI](https://ai.pydantic.dev/durable_execution/).
11. Pydantic. [pydantic_ai.agent API](https://ai.pydantic.dev/api/agent/index.md).
12. Pydantic. [HTTP Request Retries — PydanticAI](https://pydantic.dev/docs/ai/models/http-request-retries/).
13. Pydantic. [Deferred Tools — PydanticAI](https://pydantic.dev/docs/ai/tools-toolsets/deferred-tools/).
14. Pydantic. [Pydantic Logfire Debugging and Monitoring](https://ai.pydantic.dev/logfire/).

## Execution Summary

- 只使用指定启动器执行联网研究；`native_web_used=false`。
- library resolution：1 次 Context7，观察到 1 次 HTTP 503；随后按同能力规则使用 Exa。
- discovery：成功获取 OpenAI、LangGraph、PydanticAI 官方域候选；另观察到 2 次并行调用拒绝和 1 次成功但零结果的 keyword discovery。
- direct-source verification：15 个官方页面 fetch 均 `ok=true`、`fallback_used=false`；报告实际引用其中 14 个。
- `doctor_calls=0`；未调用子代理；未读取启动器实现、配置、环境、凭证或测试内部信息。
- 仅写入本任务指定的 `research-report.md` 与 `run-result.json`，未修改仓库。
