# Smart Search 多源研究全流程实现计划

> 状态：里程碑 A–F、配置收尾、工程 E2E Gate 与阶段 G 已完成；等待用户审阅，尚未替换当前 macOS 激活版本
>
> 目标分支：`preview/multi-source-agentic-research`
>
> 首发范围：仅 macOS Preview
>
> 最后更新：2026-08-24

本文档是 Smart Search 多源研究改造的权威实现依据。后续实现、验收和配套图示必须与本文一致；聊天记录、Big Picture HTML、Draw.io 或 Mermaid 与本文冲突时，以本文的明确条目为准。

面向讨论与审阅的整体视图见 [`multi-source-search-big-picture.html`](./multi-source-search-big-picture.html)。该 HTML、Draw.io 和 Skill Mermaid 是便于审阅的派生视图，不单独形成产品契约。

## 1. 目标与来源边界

Smart Search 将扩展为由 Root Agent 驱动的多源研究系统。主流程是“多源发现 → 候选整理 → 关键文档深挖 → 可定位证据 → Claim 级综合”。用户只需给出研究目标、`quick | standard | deep` 强度及成本或时间约束；Root Agent 负责语义规划和最终表达，Smart Search 提供确定性的研究内核。

本项目明确复用和改编以下来源：

1. **多源发现能力沿用并扩展 Smart Search。** CLI、Provider 路由、Search、Research、Fetch、来源处理和可观测性来自 [`konbakuyomu/smartsearch`](https://github.com/konbakuyomu/smartsearch) 及当前改编仓库 [`whycantfindaname/smartsearch`](https://github.com/whycantfindaname/smartsearch)。
2. **文档深挖直接复用 Mistral Search Toolkit。** Python 3.12 Sidecar 直接安装并使用 PyPI 上的 [`mistralai-search-toolkit`](https://pypi.org/project/mistralai-search-toolkit/)，复用其 `Document`、`DocumentChunk`、locator、`Pipeline`、`TextSplitter`、`QueryEngine`，以及 `search`、`open`、`navigate`、`read`、`grep` 工具循环。本项目在这些组件周围实现受控输入、存储、Embedding 和解析适配。
3. **项目自有部分是两阶段编排协议。** `ResearchFrame`、`SearchTask`、`EvidenceMiningTask`、Root 持有的 `ResearchRun`、委派往返、候选摘要、Claim 生命周期、Trace 和引用完整性检查属于本项目契约。
4. **许可与归属必须随代码保留。** Smart Search、Mistral Search Toolkit 及其他实际复用代码保留对应来源、版权和适用许可证。文档中的思想引用与实际代码复用清单分别管理。

该集成不调用 Mistral API，不要求 `MISTRAL_API_KEY`，不消耗 Mistral credits。它应描述为“基于 Search Toolkit、带项目适配器的集成”，不得宣称项目独立发明了相同接口，也不得扩大为未经验证的兼容性承诺。

## 2. 权威架构决策

### 2.1 唯一语义控制面

Root Agent 是唯一的语义 Planner 和 Synthesizer。Root Agent：

- 从完整对话和 `ResearchFrame` 形成、修改和终止研究计划；
- 决定 `SearchTask` 的分解方式和要使用的搜索能力；
- 决定启动零个、一个或多个 Search Scout、Source Curator 和 Evidence Miner，并决定如何分片；
- 根据候选、证据、冲突和缺口决定何时重规划；
- 根据研究充分性、预期信息增益、用户成本/时间约束和已观察缺口决定何时停止；
- 维护 Claim 语义并生成最终带引用综合。

只有 Root Agent 可以创建或委派任务。Search Scout、Source Curator 和 Evidence Miner 可以返回覆盖缺口、风险和后续任务建议，但不得创建子任务或派生后代 Agent。

Smart Search 是确定性研究内核，负责：

- Schema 校验和稳定身份校验；
- 能力状态读取与报告；
- 将 Root 的计划编译为合法内部步骤和委派请求；
- 执行 Smart Search 内部能力和 Provider Research Agents；
- 归一化候选、证据和执行结果；
- 保存原始产物、快照和 run-local Trace；
- 检查 locator、Claim 关联和最终引用完整性。

现有 `build_deep_research_plan` 仅作为离线规则基线和计划种子。它可以向 Root 提供保守建议，不能读取运行结果后自行做语义重规划，也不拥有最终综合。

### 2.2 调用方持有运行状态

Preview 采用调用方持有状态的显式往返协议。Root/Harness 持有紧凑的 `ResearchRun` JSON dossier，调用 Smart Search 的确定性操作，并保存返回的更新对象与产物引用。

Preview 不建设暂停/恢复工作流引擎，不承诺自动恢复。进程中断后，现有 dossier 和 Trace 可供人工审计；只有后续定义可重入步骤、状态重建和恢复验收后，才能增加自动恢复能力。

外部委派使用：

```text
Root creates DelegateRequest
→ Harness launches the selected project Agent or Skill
→ child returns DelegateResult
→ Smart Search validates and normalizes the result
→ Root updates ResearchRun and decides the next action
```

所有公共对象使用稳定的 `schema_version`、`run_id`、`task_id`、`step_id`、`attempt_no` 和 `artifact_refs`。重复结果必须能归属到原任务和原尝试；Preview 不以此承诺自动重放或恢复。

### 2.3 研究强度与动态资源选择

保留 `quick`、`standard`、`deep` 三种产品模式，不增加第四种强度：

| 模式 | 产品意图 | Root 的能力选择 |
| --- | --- | --- |
| `quick` | 低延迟直接检索 | 从基础搜索与已知 URL 读取能力中动态选择 |
| `standard` | 多源核验与必要的文档回读 | 动态组合 Smart Search 基础能力；需要补充发现时可委派 AnySearch 或 Search Scout |
| `deep` | 广覆盖研究、关键文档深挖与 Claim 级综合 | 动态组合基础能力、项目 Subagent 和四类 Provider Research Agents |

不设置固定 `SearchTask` 数、固定 Subagent 数、固定候选阈值或统一预算账本。Root 根据研究充分性、预期信息增益、用户成本/时间约束和观察到的缺口动态决策。

Smart Search 记录实际尝试、开始/结束时间、耗时、可观测用量、Provider 状态和失败原因。硬边界仅来自：

- 用户明确给出的时间、成本、调用或范围限制；
- Harness、平台和本机资源限制；
- Provider 超时、并发或套餐限制；
- 防止重复计费和失控重试的安全重试规则。

### 2.4 能力池与选择权

Root 可从以下 Smart Search 能力池动态选择基础能力；具体 Provider 和功能以运行时已配置、可达、已授权的 live 状态为准：

- 通用与时效性网页搜索；
- 官方文档、API 与 SDK 检索；
- 学术论文与研究资料发现；
- 代码仓库与开发者资料发现；
- 已知 URL 的 fetch、read 和来源回读；
- crawl、extract 与 batch 操作。

主要能力示例包括：

- Firecrawl Developer Index、Research、Crawl、Batch；
- Tavily Search、Extract、Crawl、Research；
- Exa Search、Deep Search、Agent；
- Jina Search、Reader、DeepSearch、Reranker。

这些名称描述主能力池，不保证每次运行全部可用。Capability 状态必须区分未配置、配置存在但不可达、无 entitlement、超时、降级和可用，且带观察时间；离线计划只能使用已有状态快照并明确其新鲜度。

在 `deep` 中，Firecrawl Agent、Jina DeepSearch、Exa Agent 和 Tavily Research 四类 Provider Research Agent 都进入计划，并在各自已配置时并发尝试。每个能力分别产生一条 `ExecutionAttempt`：缺少 Key、entitlement 失败、超时、部分结果和成功都是独立结果；任何单项失败都不能使整个研究运行失败。实现不得恢复旧的 Provider 数量上限，也不得按一个适配器完成后才规划下一个适配器。

### 2.5 AnySearch 的独立所有权

- AnySearch 始终是独立 Skill，不成为 Smart Search 内部 Provider 或内部实现。
- Smart Search 仓库保留完整、原样的 AnySearch Skill 快照；首选来源为 `jason-liao-skills/main/skill-packages/anysearch`，该包不存在时才允许使用官方来源。
- 仓库同步脚本管理内置快照，并保留 Smart Search-owned adapter 与 runtime 覆盖；不复制私有配置。
- 内置适配器是唯一 AnySearch 入口；快照或适配器缺失时记录 unavailable，研究继续使用其他能力。
- Root 或 Root 委派的 Search Scout 阅读 Skill 后自行选择具体 AnySearch 功能，Smart Search 不硬编码子命令。
- AnySearch 不可用时返回明确的委派结果和覆盖缺口，研究继续使用其他能力。
- `ANYSEARCH_API_KEY` 与 `ANYSEARCH_API_KEY_FALLBACK` 只由 bundled adapter 从 Smart Search 私有 `config.json` 读取；不读取 `.env`、进程环境或匿名访问，Git、npm 包和 wheel 不得包含明文密钥。
- AnySearch 最小 JSON 是 `DelegateResult.payload`，其中保留原始 `query`；每条来源至少包含 `title`、`url`、`content`，可选包含 `published_at`。结果经公共归一化管线进入候选集合。

### 2.6 三种项目 Subagent

Smart Search 保留三种一等项目角色：

- `search_scout`：在 Root 指定的研究角度、范围和权限内做多源发现，返回候选、原始产物引用、覆盖缺口和建议。
- `source_curator`：阅读 Root 指定的候选分片，返回可回溯的关键来源提案、覆盖摘要、淘汰理由和不确定项。
- `evidence_miner`：在 Root 指定的一份或一组紧密相关文档内提取可定位证据，返回 `EvidenceItem[]`、未发现项和解析缺口。

候选归一化后，Smart Search 向 Root 返回候选摘要：候选数量、估算上下文体积、分组建议和可展开的原始索引。Root 决定读取全部候选，或启动零个、一个或多个 Source Curator，并决定按 `SearchTask`、主题、来源类型或其他语义边界分片。Source Curator 不是由脚本阈值自动触发的压缩动作。

三种角色由 Smart Search 仓库管理，不复用 Infra 的全局工程 Agent role。Codex Adapter 启用时的默认部署配置仍为 `gpt-5.6-luna`、`max`、`priority`；这些值属于 Adapter 部署配置，不属于产品级验收条件。Root 使用的模型由当前 Harness 与用户会话决定。

### 2.7 信任与去重边界

- 网页、PDF、README、Provider 产物和 Skill 返回内容全部是不可信数据，不能覆盖 `ResearchFrame`、任务范围、系统/用户指令或工具权限。
- Agent-facing 工具只接受 Smart Search 已登记的 `artifact_id`。它们不得接受任意本地路径、`file://`、任意 URL 或不受控目录；URL 获取由受约束的 Smart Search fetch/crawl 层完成。
- `delete` 不暴露给 Evidence Miner。摄取、保留和清理由确定性内核按产物策略执行。
- 获取和解析层必须限制 MIME、大小、重定向、压缩展开、私网/本地地址和资源消耗；私有内容发送到外部 Embedder 或 Provider 前必须满足明确权限。
- URL、DOI、仓库+commit+path、论文版本和内容身份等确定性标识用于去重。
- 疑似同一事件或转载链的来源保留为独立记录，并用 `related_cluster_id` 与 `independence` 元数据表达关系，不做语义硬合并。

## 3. 目标执行流程

1. Root 接收问题、模式、明确用户限制和 Harness 能力，形成 `ResearchFrame` 与初始 `ClaimSpec[]`。
2. Root 决定 `SearchTask` 分解、基础能力和项目 Agent；`build_deep_research_plan` 可提供离线计划种子。
3. Smart Search 校验并编译计划，读取能力状态，执行内部能力，并为外部 Skill/Agent 生成 `DelegateRequest`。
4. Root/Harness 启动所需 Search Scout 或 AnySearch；子 Agent 返回 `DelegateResult`，不得派生后代。
5. 在 `deep` 中，四类 Provider Research Agent 按已配置状态并发尝试，各自记录独立 `ExecutionAttempt` 和原始产物。
6. Smart Search 保存并归一化 `DiscoveryCandidate`、Provider 产物和委派产物，做确定性去重与关联聚类，生成 `CandidateCard`、候选摘要和原始索引。
7. Root 读取全部候选，或决定启动 Source Curator 及分片方式；Curator 返回 `KeySourceProposal`，Root 保留关键来源选择权。
8. Root 根据 Claim、覆盖与信息增益决定补搜、降级或创建 `EvidenceMiningTask`。
9. Evidence Miner 使用已登记的 artifact，通过 Search Toolkit 的 `search`、`open`、`navigate`、`read`、`grep` 循环取证；需要解析时由 MinerU 产生受控 Markdown 产物。
10. Smart Search 校验 `EvidenceItem` 的快照身份、typed locator、Claim 关联和原始产物引用。
11. Root 将 `ClaimSpec` 更新为 `ClaimRecord`，记录支持、反驳、限定、冲突和未解决状态；必要时重新规划。
12. Root 判断证据充分后生成一次性综合答案；Smart Search 执行引用完整性检查并保存最终映射与 Trace。

## 4. 公共数据契约

### 4.1 稳定信封

以下对象必须具有 `schema_version`，并按其层级携带 `run_id`、`task_id`、`step_id`、`attempt_no` 和 `artifact_refs`。ID 在同一 `ResearchRun` 内稳定，原始产物只追加，不被筛选视图覆盖。

### 4.2 `ResearchFrame` 与 `ResearchRun`

`ResearchFrame` 定义问题、范围、时间边界、来源偏好、用户限制、权限和不可信内容规则。

`ResearchRun` 是 Root/Harness 持有的紧凑 JSON dossier，至少包含：

- 当前 `ResearchFrame`、`ClaimSpec[]` 和任务引用；
- 已观察的能力状态及观察时间；
- `ExecutionAttempt[]`、委派往返引用和候选摘要；
- 当前证据缺口、Root 的下一步决定和停止原因；
- Trace 与原始产物索引引用。

它不是服务端工作流状态机，也不构成自动恢复承诺。

### 4.3 `SearchTask`、`DelegateRequest` 与 `DelegateResult`

`SearchTask` 描述一个由 Root 定义的研究角度，包括子问题/`claim_spec_id`、时间范围、来源偏好、允许能力、权限、用户限制和期望输出。

`DelegateRequest` 绑定原 `SearchTask`、角色或 Skill、输入 artifact、权限和输出 Schema。`DelegateResult` 绑定原请求与 attempt，包含结构化 payload、原始产物引用、实际用量/耗时、缺口、建议和终止状态。只有 Root 能把建议转换为新任务。

### 4.4 `ExecutionAttempt`

每次内部能力、Provider Research Agent、Skill、项目 Agent、解析器或工具调用都形成独立尝试，记录：

- `execution_kind`、Provider 和 capability；
- 提交、轮询或流式读取所需的外部 job/cursor 元数据；
- 开始、截止、完成时间和终止状态；
- 实际请求摘要、可观测用量、重试安全性；
- 原始产物引用、错误与降级原因。

长任务适配器可以具有不同生命周期；公共契约统一事实记录，不强迫各 Provider 伪装成同步请求。

### 4.5 候选与研究产物

`DiscoveryCandidate` 表示尚未完成证据核验的来源，包含稳定 `candidate_id`、标题、规范 URL、摘要、发布日期、来源类型、稳定实体标识、发现路径、原始排名和产物引用。

Provider 或 Agent 研究产物可以携带摘要和引用列表，但仍属于候选层。关键主张必须尽可能回读原始来源后才能形成 `EvidenceItem`。

`CandidateCard` 是候选的紧凑视图。候选摘要包含 count、estimated context size、grouping suggestions 和 raw index；任何卡片、摘要或 Curator 提案都必须能按稳定 ID 展开原始记录。

`KeySourceProposal` 包含分片输入 ID、建议保留/延后/淘汰项及理由、覆盖缺口、不确定项和原始引用。它不能删除候选、创建挖掘任务或替 Root 做最终选择。

### 4.6 Claim 与 Evidence 生命周期

公共生命周期固定为：

```text
ClaimSpec → EvidenceItem → ClaimRecord
```

`ClaimSpec` 在规划阶段定义待验证主张、术语/范围、时间边界和判定条件。`SearchTask` 与 `EvidenceMiningTask` 引用稳定 `claim_spec_id`。

`EvidenceItem` 必须包含：

- `source_id`、canonical URL、`artifact_id` 和不可混淆的 snapshot identity；
- `retrieved_at`、content type、parser/chunker 标识与版本；
- typed locator，例如 page+character range、character range、section、chunk 或 repository+commit+file+line；
- 证据摘录或忠实转述、`claim_spec_id` 与 `stance = support | contradict | qualify`；
- authority、directness、freshness、methodological fit、independence、locator quality 等定性证据维度。

`ClaimRecord` 关联支持、反驳和限定证据，记录冲突、缺口、引用映射和定性状态：`supported | contested | weakly_supported | unsupported | unresolved`。第一版不计算跨维度统一分数或伪精确置信度。

### 4.7 `EvidenceMiningTask`

该任务由 Root 创建，绑定一份或一组紧密相关的受控 artifact、`claim_spec_id`、允许工具、已读 locator、用户/平台限制和期望输出。Evidence Miner 返回 `EvidenceItem[]`、未找到项、解析失败、内容冲突和建议；它不能扩大来源范围或创建后续任务。

### 4.8 `TraceEvent`

最小 append-only Trace 从公共契约首版开始：

```json
{
  "schema_version": "1",
  "event_id": "...",
  "run_id": "...",
  "task_id": "...",
  "step_id": "...",
  "attempt_no": 1,
  "parent_event_id": "...",
  "event_type": "...",
  "timestamp": "...",
  "artifact_refs": []
}
```

Trace 只记录可审计的输入输出、状态、公开决策依据、失败、降级和引用关系；不保存模型隐藏思维过程、API Key、私有配置或未授权正文。Preview Trace 是 auditable、run-local、append-only 的历史记录。

## 5. Search Toolkit 文档深挖集成

Python 3.12 Sidecar 直接复用 Apache-2.0 许可的 `mistralai-search-toolkit` Python 发行包，Smart Search 主 CLI 的最低 Python 版本不因此上调。项目适配边界如下：

- 复用 `Document`、`DocumentChunk` 和 locator 作为文档与证据定位基础；
- 复用 `Pipeline`、`TextSplitter`、`QueryEngine` 及 `search/open/navigate/read/grep` 循环；
- 用现有 OpenAI-compatible Embedding 配置替换 `MistralEmbedder`；
- 用 MinerU 替换 Mistral OCR 路径；
- 将可自由读取 URL、本地路径或目录的 loader 替换为只接受已登记 `artifact_id` 的受控 loader；
- 不向 Evidence Miner 暴露删除能力；
- 实现项目自有 Search Toolkit storage/index adapter：SQLite FTS5 加小型本地向量矩阵；
- 不部署 Vespa，也不使用 Docker；
- Embedding 模型、维度、归一化方式、Splitter/Chunker 版本共同形成索引身份，身份不匹配时拒绝混用并明确要求重建；
- 普通网页优先复用 Smart Search 已抓取的 Markdown；PDF、扫描件、Office 或复杂内容按需委派 MinerU。Smart Search 只接受绑定到请求输入 artifact 的结构化 `DelegateResult`，将受限大小的 Markdown 登记为不可变派生 snapshot，并保留原 URL、parent artifact、parser identity 和 typed locator；
- Sidecar、Embedding、索引或 MinerU 失败时保留独立 `ExecutionAttempt`，可降级到 Smart Search Fetch 和普通正文读取。

实现必须在依赖锁定、NOTICE/许可证和第三方来源清单中保留 Mistral attribution 与适用许可。

## 6. 垂直实现里程碑

### 里程碑 A：架构、公共契约与 Trace

- 固定 Root 唯一语义控制面与 Smart Search 确定性内核边界。
- 定义 `ResearchFrame`、`ResearchRun`、Claim 生命周期、任务、委派、执行尝试、候选、证据和 Trace Schema。
- 实现 Plan Compiler 的 Schema、能力状态、权限和显式硬边界校验。
- 固定不可信内容与受控 artifact 输入策略。

### 里程碑 B：内部端到端证据闭环

- 仅用 Smart Search 内部 discovery/fetch 跑通 Root plan → candidate → key source → evidence → ClaimRecord → cited answer。
- 保存原始产物、typed locator 和 append-only Trace。
- 验证 Root 可观察结果、补充任务并按充分性停止。

### 里程碑 C：Search Toolkit 文档挖掘

- 建立 Python 3.12 Sidecar 和项目 storage/index、Embedding、MinerU、受控 loader 适配器。
- 复用完整文档模型和 `search/open/navigate/read/grep` 循环。
- 接入 Evidence Miner，并验证 locator、已读排除、索引身份与降级。

### 里程碑 D：Search Scout 与 AnySearch

- 实现 `DelegateRequest` / `DelegateResult` 往返和 Harness Adapter。
- 保留 AnySearch Skill 快照与所有权边界。
- 允许 Root 动态启动所需 Search Scout；验证其结果归属、原始产物、公共候选管线和 Trace。

### 里程碑 E：四类 Provider Research Agent 与主能力扩展

- 同一里程碑实现 Firecrawl Agent、Jina DeepSearch、Exa Agent、Tavily Research 的独立生命周期适配。
- 在 `deep` 中按已配置状态并发尝试四类能力，分别报告缺 Key、entitlement、超时、partial 和 success。
- 扩展并验证通用/current、docs/API、academic、code/developer、known-URL、crawl/extract/batch 主能力池。
- 回读关键引用，确保单个 Provider 失败不阻断整体研究。

### 里程碑 F：多 Agent、Curator 与证据质量增量

- Root 可动态启动多个 Scout、Curator 和 Miner；只有 Root 创建任务。
- 实现候选摘要、Root 决定的 Curator 分片和可回溯 `KeySourceProposal`。
- 完善确定性去重、`related_cluster_id`、independence、冲突和定性证据状态。
- 完成最终引用完整性检查和 Claim/证据/locator/Trace 反向追踪。

### 配置收尾：仓库环境与运行配置

里程碑 A–F 完成后、工程 E2E Gate 之前，统一管理本仓库新增能力的配置。该阶段不建立第二套配置系统，继续以 `src/smart_search/config.py`、`smart-search setup`、`smart-search config` 和 `smart-search doctor` 为 Smart Search 配置入口：

- 建立配置所有权清单，逐项记录配置键、所属组件、是否敏感、默认值、读取优先级、保存位置和诊断方式。
- Firecrawl、Jina、Exa、Tavily 的 Research 能力优先复用现有 Provider Key 和 endpoint；只有官方 API 契约确实要求不同参数时才新增配置键，不复制同一凭据。
- Search Toolkit Sidecar、Document Embedding 和本地索引只新增运行所需的最小非敏感配置；需要密钥的 Embedder 复用现有 OpenAI-compatible 配置或显式引用已有配置，不另存一份密钥。
- MinerU 若继续通过独立 Skill 调用，其 Key 和套餐配置仍由 MinerU Skill 管理；Smart Search 只记录能力状态和委派结果。只有后续改为仓库内直接调用时，才把对应键纳入 Smart Search 配置入口。
- AnySearch bundled adapter 只使用 Smart Search 私有双密钥 `config.json`；同步和安装保留本地 `.env`、`runtime.conf` 与 adapter，Git、npm 包和 wheel 只包含示例文件，不复制私有配置。
- 新增或调整的配置必须同步到 CLI setup/config、`doctor` 的 masked 输出、两份 Skill 配置文档、打包清单和配置测试；不得只依赖开发机 shell profile 或未记录的 wrapper 注入。
- 使用独立 `SMART_SEARCH_CONFIG_DIR` 建立 Preview 配置并运行 `config path`、`config list`、`doctor`、组件健康检查和最小 live probe。不得覆盖当前 macOS 激活版本使用的 `~/.config/smart-search/config.json`。
- 对 Git tracked files、npm 包、wheel、Trace 和日志执行密钥泄漏检查；任何真实 Key、token、私有 endpoint 或未授权正文都不能进入版本控制和发布产物。

配置收尾的交付物是仓库内可维护的配置契约、更新后的 setup/doctor 行为、隔离 Preview 配置和验证记录。将验证后的配置应用到当前 macOS 激活版本，仍需用户在看完全部验收结果后单独批准。

### 工程 E2E Gate

配置收尾完成后，阶段 G 前必须通过一组小型、冻结、可复查的工程端到端验证。用例数量由覆盖目标决定，不写死任务数。至少验证：

- locator 能重新定位到对应 artifact snapshot；
- 标记为 support/contradict/qualify 的证据确实对应 ClaimSpec；
- 从最终引用可回溯到 ClaimRecord、EvidenceItem、任务、执行尝试和原始产物；
- missing key、entitlement failure、timeout、partial result 和单项 Provider failure 被准确报告；
- AnySearch、Sidecar、Embedding、MinerU 或某个 Provider 不可用时，其他有效路径继续运行并明确覆盖缺口；
- 不可信内容不能改变任务范围、权限或工具输入边界；
- 确定性重复不会重复计证，疑似同事件来源保留关联和独立性信息。

Gate 同时记录实际耗时、Provider/模型/工具调用和可观测用量，供 Root 的后续决策与用户审阅使用；这些观测值不转化为固定产品配额。

### 阶段 G：deep 验收研究

阶段 G 只能在里程碑 A–F 完成且工程 E2E Gate 通过后启动：

- 将本分支 CLI 安装到隔离 Preview 验收环境，不替换 macOS 当前激活版本。
- 使用新实现的 `deep` 能力做实施后架构复盘，研究规划、Subagent 信息交换、文档选择、文档挖掘、证据综合、Trace 和反馈循环的公开替代方案。
- 调研 Search、Agentic Search 与 Deep Research 的公开 Benchmark，形成候选推荐、评分流程、数据与服务依赖、复现成本和时效性风险。
- 来源覆盖论文、官方产品/技术文档、开源仓库、工程文章和公开案例；用户提供的 MultiAgent 文章、SearchSwarm 等只作为起始线索。
- 将重要中间产物、最终综合和引用验证投影到持久化 Research Workspace；提供由用户显式启动的 `127.0.0.1` 只读可视化页面。结构化 Dossier、Trace、Artifact、EvidenceItem 和 ClaimRecord 保持权威，Markdown 不成为第二套状态源。
- 阶段 G 不选择 Benchmark、不运行 Benchmark、不生成 Benchmark 分数。用户审阅报告后，再决定是否创建独立 Benchmark 运行任务。

## 7. 验收标准

### 7.1 架构与功能

- Root 是唯一语义 Planner 和 Synthesizer；`build_deep_research_plan` 只提供离线规则种子。
- Smart Search 只承担确定性内核职责，能校验合同、执行能力、归一化、存储 Trace/产物并检查引用完整性。
- `quick | standard | deep` 均保留；任务数、Agent 数和 Curator 使用方式由 Root 动态决定。
- `deep` 对四类已配置 Provider Research Agent 并发尝试，结果彼此独立，单项失败不终止运行。
- Root 接收候选摘要和原始索引，并自行决定全读或启动任意数量 Curator 及其分片。
- AnySearch 只以独立 Skill 运行，其 `DelegateResult.payload` 进入公共候选管线。
- 三种项目 Agent 返回结构化结果、缺口和建议，不创建后代；其具体模型配置不决定产品验收。
- `ClaimSpec → EvidenceItem → ClaimRecord` 生命周期完整，EvidenceItem 有 snapshot identity 与 typed locator。
- 证据使用定性维度和定性状态，不生成伪精确统一分数。
- Trace 从首版公共契约开始、append-only、run-local、可审计，且不声称可自动恢复。
- `research-run ... --workspace`、不可变语义 checkpoint 和 `research-view` 能保存并查看公开研究过程，不写入隐藏推理或改变结构化运行状态。

### 7.2 Search Toolkit 集成

- Python 3.12 Sidecar 直接复用指定 Search Toolkit 模型、Pipeline 和工具循环。
- OpenAI-compatible Embedding、MinerU、受控 artifact loader 和 SQLite FTS5+小型向量矩阵作为项目适配器工作。
- 无 Mistral Key、Mistral credits、Vespa 或 Docker 也可完成最小摄取、检索、导航和读取。
- Agent-facing 工具拒绝任意本地路径、`file://` 和未登记 URL；Evidence Miner 无删除工具。
- 证据可回到原始 URL、快照和 locator；组件失败有独立记录和可解释降级。
- Mistral attribution、版本、许可证和项目修改边界均可审计。

### 7.3 安全、产物与发布边界

- 外部内容始终按不可信数据处理，不能扩大任务范围或权限。
- 原始候选、Provider 产物、委派产物和文档快照只追加保存；筛选不覆盖原始记录。
- 所有新增配置都有唯一所有者、保存位置、读取优先级和 masked 诊断输出；同一密钥不在多个配置域重复保存。
- 隔离 Preview 使用独立 `SMART_SEARCH_CONFIG_DIR`，配置验证不得覆盖当前 macOS 激活配置。
- AnySearch 和 MinerU 保持各自 Skill 的凭据所有权，除非后续明确改变调用边界。
- Git、npm 包、wheel、Trace 和日志不泄露 API Key、私有配置或未授权正文。
- 工程 E2E Gate 在阶段 G 前通过，并覆盖 locator、Claim support、Trace、失败报告和降级。
- 阶段 G 只提交架构复盘与 Benchmark 推荐研究，等待用户决定。
- 用户审阅全部验收结果前，不激活到当前 macOS 运行版本。
- 未经明确授权，不 commit、push、merge、跨工作区同步或修改全局配置。

## 8. 当前实现状态

### 已实现

- Preview 分支和 macOS 首发边界。
- Smart Search 内部 AnySearch Provider、配置和专属 CLI 命令已删除。
- AnySearch 外部 Skill 委派路由元数据、内置快照、同步脚本、私有配置隔离和打包规则。
- Root-led 公共协议、Plan Compiler、caller-held `ResearchRun`、append-only Trace、Artifact Registry 与稳定身份校验。
- Smart Search 内部 discovery/fetch 到 `DiscoveryCandidate`、`EvidenceItem`、`ClaimRecord` 和引用反向回溯的闭环。
- Python 3.12 Search Toolkit Sidecar、SQLite FTS5/本地向量适配、受控 artifact loader、组件降级与独立健康检查。
- Search Scout、Source Curator、Evidence Miner 三种项目角色的业务协议、Codex Adapter 和打包快照。
- Firecrawl Agent、Jina DeepSearch、Exa Agent、Tavily Research 四类 Provider Research Agents 的独立生命周期适配与 `deep` 并发执行。
- 候选摘要、Root 决定的 Curator 分片、全运行精确去重、关联聚类元数据、定性证据状态和引用完整性检查。
- MinerU 外部委派边界：只允许从已登记输入 artifact 导入受控 Markdown 派生 snapshot，拒绝调用方直接注入未登记正文。
- 配置所有权文档、setup/config/doctor、隔离 `SMART_SEARCH_CONFIG_DIR` 和 `research-environment` 安装/健康检查入口。
- Draw.io、PNG、Skill Mermaid、项目 Agent 说明与双份 Skill 资源同步。
- Research Workspace 持久化、语义 checkpoint、metadata-only public Trace 投影和 `127.0.0.1` 只读可视化页面。

### 已完成验收，等待用户审阅

- 工程 E2E Gate 已通过：根包 560 项测试、Sidecar 2 项独立测试、wheel/npm 打包一致性、隔离配置 live doctor、组件健康检查和密钥泄漏检查均完成。
- 阶段 G 已用新 `deep` 流程完成真实多源研究：113 个候选、2 份 Curator 提案、7 份项目 Agent 结果、16 条 EvidenceItem 和 16/16 引用反向验证。
- Stage G 既有运行已迁移到仓库内、被 Git 忽略的持久化 Research Workspace，并通过只读 visualizer 数据契约复核；迁移没有重跑 Provider。长期证据另行导出到 Git 管理的 [`docs/research-runs/run-stage-g-seq-20260823T191412Z/`](../research-runs/run-stage-g-seq-20260823T191412Z/README.md)，排除 raw payload、SQLite、重复 checkpoints 和逐任务运行目录。
- 统一入口见 [`docs/acceptance/stage-g-research-index.md`](../acceptance/stage-g-research-index.md)；架构复盘见 [`docs/acceptance/stage-g-architecture-review.md`](../acceptance/stage-g-architecture-review.md)，Benchmark 推荐见 [`docs/acceptance/stage-g-benchmark-recommendations.md`](../acceptance/stage-g-benchmark-recommendations.md)，工程证据见 [`docs/acceptance/stage-g-engineering-gate.md`](../acceptance/stage-g-engineering-gate.md)。References 中的 CandidateCard 与 EvidenceItem ID 可在 fresh checkout 中回到可移植证据包；只有字符级 locator 重放仍需要本地完整 Workspace。
- 当前 macOS 激活版本的替换不属于自动收尾步骤，必须等待用户审阅全部验收结果并另行批准。

## 9. 验收现场结果与剩余决策

以下项目属于实现或部署配置，不改变本文架构：

1. 隔离 live doctor 证明主搜索、Context7、Exa、Tavily、Firecrawl 和 Jina 的通用连接可用；功能级实跑进一步证明 Exa Agent 可用、Tavily Research 受当前套餐 HTTP 432 限制，Firecrawl Agent 与 Jina DeepSearch 在本次查询中超时。
2. 阶段 G 的文档挖掘显式使用 lexical-only 配置；Search Toolkit 0.0.11、SQLite FTS5 与 exact locator 路径可用，不调用 Mistral API，也不依赖 Vespa/Docker。OpenAI-compatible Embedding 仍是可选配置，不是本次证据链的前提。
3. Root 根据 113 个候选和约 58,895 字符的候选摘要动态安排 2 个 Curator shard，并在补充证据阶段新增第 3 个 Evidence Miner；业务协议固定，委派数量没有写死。
4. 用户仍需决定是否选择候选 Benchmark 并另建运行任务，以及是否把当前 Preview 替换到 macOS 激活版本。

这些配置必须通过当前源代码、官方契约和 live probe 决定。配置变化更新实现记录和验收证据，不得重新分配 Root 与 Smart Search 的所有权。

## 10. 设计依据

- Smart Search 原始仓库：<https://github.com/konbakuyomu/smartsearch>
- Smart Search 当前改编仓库：<https://github.com/whycantfindaname/smartsearch>
- Mistral Agentic Search：<https://mistral.ai/news/agentic-search/>
- Mistral Search Toolkit：<https://docs.mistral.ai/studio/search/search-toolkit>
- Mistral Search Toolkit Document Model：<https://docs.mistral.ai/studio/search-toolkit/document-model>
- `mistralai-search-toolkit` Python 发行包：<https://pypi.org/project/mistralai-search-toolkit/>
- Mistral Search Starter App：<https://github.com/mistralai/search-starter-app>
- MultiAgent 工程经验文章：<https://mp.weixin.qq.com/s/Osm8jzocOBNvkxIXSgdiNQ>
- SearchSwarm 论文路径示例：<https://arxiv.org/pdf/2606.09730>
- MinerU 解析能力与模式边界：`/Users/jasonliao/.codex/skills/mineru-cloud-api/SKILL.md`
- 全局与项目 Subagent 所有权边界：`/Users/jasonliao/Desktop/code/Tools/jason-liao-agent-infra-macos/docs/solutions/architecture-patterns/native-default-specialized-scout-role-boundary.md`

## 11. 自动化与发布限制

用户已授权在 `preview/multi-source-agentic-research` 分支实现本计划并执行隔离验收；Infra、全局 Agent routing/config 和当前 macOS 激活状态保持不变。实现不得自动 commit、push、merge、跨工作区同步或激活。任何上述外部状态变化仍需用户明确授权，并分别报告 source、Preview 安装、激活和 live 验证证据。
