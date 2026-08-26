# OpenAI Agents SDK、LangGraph 与 PydanticAI：持久化、失败处理、人工介入与可观测性比较

## 结论

如果目标是让一个长时、分支化的 workflow 在节点级别暂停、恢复、重试、检查和修改状态，LangGraph 的官方 Python 接口最直接地覆盖了这组需求：`checkpointer` 按 `thread_id` 保存 graph state，`RetryPolicy` 与 `error_handler` 位于节点执行边界，`interrupt()` 再通过同一持久化层恢复。代价是应用必须显式设计 graph state、thread、checkpointer 以及节点副作用。[1][2][3]

OpenAI Agents SDK 更适合以 agent run 为中心的应用：`Session` 自动维护 conversation history，人工审批用可序列化的 `RunState` 暂停和恢复，model retry 则是显式启用并带有 replay-safety 判断的 runner 能力。这个边界较轻，但 session history、paused run state 与任意业务副作用的 durable workflow 不是同一层语义。[4][5][6]

PydanticAI 采取组合式路线：核心 `Agent` 提供 tool/output validation retry，Deferred Tools 处理审批和外部执行，跨重启的 durable execution 交给 Temporal、DBOS、Prefect、Restate 等官方支持集成，可观测性则通过可选的 Logfire/OpenTelemetry instrumentation 接入。[7][8][9][10]

因此，选型可以先按主导问题判断：需要原生 graph checkpoint 与任意节点暂停恢复，优先 LangGraph；需要 OpenAI agent loop、审批状态和内建 tracing 的短路径，优先 OpenAI Agents SDK；需要强类型 agent API，并愿意把 durable execution 与 telemetry 交给既有集成，优先 PydanticAI。这个判断只针对 2026-08-26 读取到的 Python 官方 rolling/latest 文档，不代表三者所有语言实现或托管产品完全等价。[1][3][4][5][11][9][10]

## 研究范围与方法

本报告面向需要为生产 agent workflow 做框架选型的工程师、研究人员和技术负责人，比较四条边界：checkpointing/state persistence、failure and retry handling、human-in-the-loop，以及 observability。研究对象是三套框架的 Python 官方文档；不比较模型供应商覆盖、RAG、部署价格、性能或 TypeScript API。

截止日期为 2026-08-26（Asia/Shanghai）。页面均按当日读取到的 rolling/latest 文档处理；只有 LangGraph fault-tolerance 页面明确显示 `langgraph>=1.2`，其余页面没有显示统一包版本，因此不从页面外推版本。检索先尝试 Context7 library resolution，再使用同能力的 Exa 官方域 discovery，最后逐页读取 direct source；discovery 只用于定位，正文结论只使用成功打开的官方页面正文。

本报告把关键概念暂定为 `session-resolved` 用法：检查点与状态持久化、重试与失败处理、human-in-the-loop、可观测性，以及 run/session state。`verified` 表示已读取并检查保存的 direct-source 正文；没有把搜索摘要或候选结果当作已核验事实。

## 1. Checkpointing 与 state persistence

### OpenAI Agents SDK：对话历史与暂停运行状态

启用 `Session` 后，runner 会在每次 run 前读取该 session 的 conversation history，并在 run 后保存本轮产生的新 items；使用相同 session 可以继续同一 stored conversation。SDK 提供 SQLite、Redis、SQLAlchemy、Dapr、MongoDB 等 session 实现，但这些实现的共同语义仍是 conversation history，而不是任意 graph 的 checkpoint。[4]

HITL 场景另有 `RunState`：暂停审批的 result 可以转换为 state，调用方在批准或拒绝后交回 runner；长时间暂停时，state 可以通过 `to_json()` 或 `to_string()` 保存，并用对应的反序列化方法恢复。因而 OpenAI Agents SDK 能覆盖“对话连续性 + 审批暂停”，但已核验文档没有把 `Session` 定义为任意节点的 graph checkpoint，不能据此推断外部工具副作用会自动 exactly-once。[5]

### LangGraph：thread-scoped checkpoint 与跨 thread store

LangGraph 明确区分两类持久化：checkpointer 保存单个 thread 的 graph state snapshots，用于对话连续性、human-in-the-loop、time travel 和 fault tolerance；store 保存 graph state 之外、跨 thread 的应用键值数据。调用 graph 时通过 config 传入 `thread_id`，checkpoint 因而绑定到该 thread。[1]

`MemorySaver`/`InMemorySaver` 将 checkpoint 放在内存中，进程重启后会丢失；官方建议生产环境使用持久 checkpointer，例如 `PostgresSaver` 或 `SqliteSaver`。这使 LangGraph 的恢复主键和持久化边界显式可见，但也要求应用自行管理 state schema、thread identity 和保留策略。[1]

### PydanticAI：把 durable execution 交给集成

PydanticAI 的 Durable Execution 文档承诺跨 transient API failure、应用错误和重启保存进度，并明确列出四个官方支持方案：Temporal、DBOS、Prefect、Restate。Temporal、DBOS、Prefect 作为附加到 agent 的 capabilities 提供，Restate 集成位于 Restate SDK；这是一种 integration-level 能力，不应与普通 `message_history` 混称为核心 agent 内建 checkpoint store。[9]

Deferred Tools 的跨进程路径也体现了这个边界：当前 run 结束后，调用方携带原 message history 和 deferred results 启动新的 run；后续 run 有自己的 `run_id`，通过 `conversation_id` 维持关联。因此 PydanticAI 的核心 agent API、外部执行 continuation 和 durable executor 是可组合的不同层。[8]

### 横向判断

三者保存的对象并不等价：LangGraph 把 graph state checkpoint 作为 runtime 核心；OpenAI Agents SDK 把 session history 与 paused `RunState` 分开；PydanticAI 则通过 durable integration 保存跨重启进度。若系统需要回到任意 graph 节点并审查或编辑状态，第一种语义最贴近需求；若系统主要是连续对话或审批暂停，后两种语义更轻，但需要另外定义业务副作用与 durable executor 的边界。[1][4][5][9]

## 2. Failure 与 retry handling

### OpenAI Agents SDK：runner-managed model retry 与 replay safety

OpenAI 的 model retry 通过 `ModelRetrySettings` opt-in；`max_retries` 表示初次 model request 之后允许的额外重试次数，policy context 还提供 `response_started`、`replay_safety` 和 `stateful_request` 等信息。普通 `RetryDecision(retry=True)` 不会绕过 provider 标记的 replay protection；只有显式设置 `approve_unsafe_replay=True` 才允许重复可能已经发生的 provider-side work。[6]

失败通过 `AgentsException` 家族暴露，`RunErrorDetails` 保存 input、new items、raw responses、last agent 以及 guardrail results；`MaxTurnsExceeded`、`ModelBehaviorError` 和 `ToolTimeoutError` 等类型使失败分类可以进入上层处理。这里的 retry 是 model-call runner 能力，不能替代业务节点的补偿、幂等或持久化设计。[12]

### LangGraph：节点边界上的策略与错误路由

LangGraph 把 retry policy 绑定到 node：`RetryPolicy` 可配置 `max_attempts`、初始间隔、指数 backoff、最大间隔、jitter 和 `retry_on` exception filter；官方参数表给出的默认 `max_attempts` 是 3，包含首次尝试。节点耗尽重试后，`error_handler` 可以接收 `NodeError`，再返回 `Command` 更新 state 或路由到补偿路径。因此不同节点可以拥有不同的故障策略，而不必把所有失败压缩成一个 agent-loop 预算。[2]

### PydanticAI：validation/tool retry 与 HTTP retry 分层

PydanticAI 的 `Agent(retries=...)` 负责 tool 与 output validation 的 retry 预算；API 文档说明整数可以同时设置两类，也可以用 `AgentRetries` 分开设置，默认两类各为 1。这个预算不等同于 model request retry。[7]

网络层 retry 由 `AsyncHTTPX2TenacityTransport`、`HTTPX2TenacityTransport` 和 `RetryConfig` 处理，可以按 `Retry-After`、指数 backoff、exception predicate 和停止条件配置；所有尝试失败后重新抛出最后一个 exception。把 validation retry 和 HTTP retry 混成一个数字，会隐藏失败发生在哪一层以及谁负责恢复。[13]

### 横向判断

这条比较轴的关键不是“谁的重试次数更多”，而是失败边界：OpenAI Agents SDK 关注 model request 的 replay safety，LangGraph 关注 node 级策略与错误路由，PydanticAI 分开处理 validation/tool 与 HTTP transport。生产系统仍需为有副作用的操作补充幂等、补偿和持久化策略；本报告只比较官方文档定义的接口，不实现或评估 runtime retry logic。[6][2][7][13]

## 3. Human-in-the-loop 与人工介入

### OpenAI Agents SDK：tool approval 与可序列化 RunState

OpenAI 的 HITL flow 专注敏感 tool call 审批：工具用 `needs_approval` 声明策略，run result 通过 `interruptions` 暴露待审批项，调用方把 result 转为 `RunState`，执行 `approve()` 或 `reject()` 后再交回 `Runner.run()`。审批可以覆盖当前 agent、handoff 和 nested `Agent.as_tool()`，并可序列化后长时间暂停。[5]

### LangGraph：任意 node 位置的 interrupt

LangGraph 的 `interrupt()` 可以放在 node 的任意位置；checkpointer 保存暂停时的 graph state，调用方用同一 `thread_id` 发送 `Command(resume=...)`，resume payload 会成为 node 中 `interrupt()` 的返回值。官方同时要求注意恢复语义：node 会从头重新执行，因此 `interrupt()` 前的副作用必须幂等；不能用宽泛的 `try/except` 包住 interrupt，也不能在恢复时改变同一 node 内 interrupt 的顺序。[3]

### PydanticAI：Deferred Tools 的 inline 与跨 run continuation

PydanticAI 用 Deferred Tools 统一审批和外部执行：`requires_approval=True` 或 `ApprovalRequired` 会产生 `DeferredToolRequests`，调用方再用 `DeferredToolResults` 返回批准、拒绝或工具结果。如果 resolver 在同一进程内，`HandleDeferredToolCalls` 可以让 agent run 在单次调用中继续；如果 resolver 在进程外，当前 run 结束，调用方携带原 message history 与 deferred results 启动新的 run，并用 `conversation_id` 关联，而不是复用暂停 run 的 `run_id`。[8]

### 横向判断

OpenAI Agents SDK 的人工介入模型围绕敏感 tool approval，LangGraph 的模型更接近可暂停、编辑和恢复 graph state，PydanticAI 则把审批与外部执行统一成 deferred result protocol。需要人工修改状态或表单式交互时，LangGraph 的粒度更通用；需要把审批接在 agent tool 上时，OpenAI 或 PydanticAI 的边界更直接。[5][3][8]

## 4. Observability

### OpenAI Agents SDK：默认 tracing 与敏感数据边界

OpenAI Agents SDK 默认对 runner、task、turn、agent、generation、function tool、guardrail、handoff 和 audio 等对象生成 trace/span，并允许通过 custom trace processor 替换或追加 exporter。generation 与 function spans 默认可能记录敏感输入输出；`trace_include_sensitive_data` 默认是 `True`，应用需要主动关闭或按组织策略处理。[11]

### LangGraph：runtime 与 LangSmith tracing 分层

LangGraph 的官方路径是 LangSmith tracing：配置 `LANGSMITH_TRACING=true` 和 API key 后记录 graph trace；使用 LangChain 时由集成自动传递上下文，不使用 LangChain 时可以用 `@traceable` 或 wrapper 保持 tracing context。因而 LangGraph runtime 与 LangSmith observability 是相邻但分离的产品层，不能把本地 checkpointer 当成 telemetry backend。[14]

### PydanticAI：可选 instrumentation 与 OpenTelemetry

PydanticAI 的 instrumentation 是可选的；启用 `logfire.instrument_pydantic_ai()` 后，每次 agent run 会生成 trace，并为 model call 与 tool function execution 产生 spans。底层采用 OpenTelemetry，可以把数据发往 Logfire，也可以发往其他 OTel-compatible backend，不必把 Logfire 当作唯一后端。[10]

### 横向判断

三者都能形成运行轨迹，但默认性和归属不同：OpenAI Agents SDK 把 tracing 放进 runner 默认行为，LangGraph 通过 LangSmith 接入，PydanticAI 则提供可选的 OTel instrumentation。无论选择哪一个，telemetry backend、敏感数据策略和持久化 checkpoint 都是不同的配置问题，需要单独验收。[11][14][10]

## 5. 选型建议

- **优先 LangGraph**：核心问题是 graph state 的 thread-scoped checkpoint、节点级 retry/error routing，以及任意节点的暂停、恢复或人工编辑；应用能够接受显式设计 state、thread、checkpointer 和副作用幂等性。[1][2][3]

- **优先 OpenAI Agents SDK**：核心问题是以 agent run 为中心的多轮对话、敏感 tool approval、可序列化的暂停运行状态，以及默认 runner tracing；应用能够把 session history、paused `RunState` 与业务 durable workflow 分开。[4][5][11]

- **优先 PydanticAI**：核心问题是类型化 Python agent API、tool/output validation retry 和 deferred tool protocol，同时团队愿意采用 Temporal、DBOS、Prefect、Restate 之一处理 durable execution，并用 OTel/Logfire 处理 telemetry。[7][8][9][10]

## 证据状态与限制

本报告实际引用的官方 direct sources 均标记为 `verified`；没有用 `unverified` 或 `missing` 的 Claim 填补比较空白。关于“某框架完全没有某能力”的绝对否定也没有进入结论，正文只陈述本次打开的官方页面定义的接口及由这些接口直接推出的边界。

限制如下：

1. 三套文档都是 rolling/latest 页面。OpenAI Agents SDK 与 PydanticAI 页面没有显示统一包版本；LangGraph fault-tolerance 页面明确显示 `langgraph>=1.2`，其他页面仍可能跨版本更新。
2. 比较对象是 Python 文档；OpenAI Agents JS、LangGraph JS 和各托管平台可能有不同接口或发布时间。
3. 本研究核验接口语义，没有安装三个包或运行示例，因此不比较实际吞吐、数据库 schema、崩溃一致性、exactly-once、trace 成本或后端 SLA。
4. PydanticAI durable execution 的统一概览已核验，但没有逐一打开 Temporal、DBOS、Prefect、Restate 子页，因此不比较四个 executor 的具体 checkpoint 粒度。
5. LangGraph fault-tolerance fetch 的部分说明段落在抽取结果中只保留了符号与参数表；本报告仅使用可完整回读的接口、参数和示例，不扩写缺失段落。

## 验收与恢复附录

以下是本次已保存 acceptance artifacts 中的执行事实，不是新的框架能力判断：

- `context7-library` 对 OpenAI Agents SDK resolution 返回 `ok=false`、`provider=context7`、`error_type=network_error` 和 HTTP 503；结果没有 `recovery`、`provider_attempts` 或 `logical_attempts`。按既定 5xx 规则，没有原样重试，转到同能力 Exa 官方域 discovery；`doctor` 不在 structured recovery 要求中，因此没有调用。
- 首次并行启动三条 Exa discovery 时，LangGraph 成功，另外两条在 provider 前被启动器拒绝，错误消息为 `parallel Smart Search invocations are not permitted`，且没有结构化 JSON。随后改为串行，并用改变后的 OpenAI/PydanticAI 查询重新提交，两条均成功。
- 一条 PydanticAI 精确 keyword discovery 返回 `ok=true`、`results=[]`、`total=0`。它被按 empty discovery 处理，而不是 provider failure；后续依据已打开的官方 API 文档内链接与更宽的官方域查询定位 direct pages。
- 执行摘要记录了 15 个官方页面 fetch 均 `ok=true`、`fallback_used=false`；正文实际引用其中 14 个来源。`native_web_used=false`、`doctor_calls=0`，未调用子代理，也未读取配置、环境、凭证或测试内部信息。

## References

1. [Persistence - LangGraph](https://docs.langchain.com/oss/python/langgraph/persistence). Accessed: 2026-08-26.
2. [Fault tolerance - LangGraph](https://docs.langchain.com/oss/python/langgraph/fault-tolerance). Accessed: 2026-08-26.
3. [Interrupts - LangGraph](https://docs.langchain.com/oss/python/langgraph/interrupts). Accessed: 2026-08-26.
4. [Sessions - OpenAI Agents SDK](https://openai.github.io/openai-agents-python/sessions). Accessed: 2026-08-26.
5. [Human-in-the-loop - OpenAI Agents SDK](https://openai.github.io/openai-agents-python/human_in_the_loop). Accessed: 2026-08-26.
6. [Retry - OpenAI Agents SDK API Reference](https://openai.github.io/openai-agents-python/ref/retry). Accessed: 2026-08-26.
7. [pydantic\_ai.agent API](https://ai.pydantic.dev/api/agent/index.md). Accessed: 2026-08-26.
8. [Deferred Tools - PydanticAI](https://pydantic.dev/docs/ai/tools-toolsets/deferred-tools). Accessed: 2026-08-26.
9. [Durable Execution - PydanticAI](https://ai.pydantic.dev/durable_execution). Accessed: 2026-08-26.
10. [Pydantic Logfire Debugging and Monitoring](https://ai.pydantic.dev/logfire). Accessed: 2026-08-26.
11. [Tracing - OpenAI Agents SDK](https://openai.github.io/openai-agents-python/tracing). Accessed: 2026-08-26.
12. [Exceptions - OpenAI Agents SDK API Reference](https://openai.github.io/openai-agents-python/ref/exceptions). Accessed: 2026-08-26.
13. [HTTP Request Retries - PydanticAI](https://pydantic.dev/docs/ai/models/http-request-retries). Accessed: 2026-08-26.
14. [Trace LangGraph applications - LangSmith](https://docs.langchain.com/langsmith/trace-with-langgraph). Accessed: 2026-08-26.
