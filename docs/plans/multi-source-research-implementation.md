# Smart Search 多源研究全流程实现计划

> 状态：实施前设计已部分确认
>
> 目标分支：`preview/macos-agentic-research`
>
> 首发范围：仅 macOS Preview
>
> 最后更新：2026-08-23

本文档是 Smart Search 多源研究改造的实现依据。后续新增决策同步更新本文档与 Big Picture HTML，不以聊天记录或流程图中的隐含含义作为实现依据；两者出现冲突时以本 Markdown 的明确条目为准。

面向讨论与审阅的整体视图见 [`multi-source-search-big-picture.html`](./multi-source-search-big-picture.html)。该 HTML 是随讨论持续更新的 Big Picture；本 Markdown 继续保存完整的规范性实施条目。

## 设计来源与改编边界

本项目不是从零发明一套 Search 或 Agentic Search 系统。对外介绍、内部设计文档和后续代码归属必须明确区分以下来源：

1. **多源发现阶段改编自既有 Smart Search。** 阶段 01 沿用并扩展 Smart Search 的 CLI、Provider 路由、Research、Fetch、来源处理和可观测性能力。原始项目为 [`konbakuyomu/smartsearch`](https://github.com/konbakuyomu/smartsearch)，当前多源研究 Preview 位于 [`whycantfindaname/smartsearch`](https://github.com/whycantfindaname/smartsearch)。
2. **关键文档深挖阶段源自 Mistral Agentic Search。** 阶段 02 采用“发现关键文档后转向文档内部迭代搜索、打开、导航和读取”的思路，来源包括 Mistral 的 [Agentic Search 文章](https://mistral.ai/news/agentic-search/)、[Search Toolkit 文档](https://docs.mistral.ai/studio-api/search-toolkit) 和 [`mistralai/search-starter-app`](https://github.com/mistralai/search-starter-app)。
3. **本项目负责两者之间的统一编排。** Root Agent 动态重规划、`SearchTask`、`EvidenceMiningTask`、按任务隔离的已读状态、`ProviderRun`、`EvidenceItem`、`Claim Ledger` 和统一综合属于本项目为两阶段衔接而定义的实现协议；不得反向描述为 Smart Search 或 Mistral 已经提供的完整能力。
4. **思想引用与代码复用分开管理。** 文档采用外部思想时提供文章、文档或仓库链接；后续若复制或修改 Smart Search、Mistral Search Starter App 或 Search Toolkit 的代码，必须保留对应 MIT 或 Apache-2.0 许可声明，并在实际发生代码复用时增加第三方来源清单。

本项目的 Mistral-inspired 文档深挖不调用 Mistral API，不要求 `MISTRAL_API_KEY`，也不消耗 Mistral credits；“Mistral-inspired”表示思想和工具契约来源，不表示使用 Mistral 托管服务或获得其官方背书。

## 1. 目标

把 Smart Search 从“单次搜索命令与单一 Research 路径”扩展为统一的多源研究系统：同一个 Planner 根据问题、研究强度、可用能力和成本约束生成执行计划；Smart Search 内部搜索、Provider Research Agents API、外部 Skill 与 Subagent 以混合方式执行；搜索阶段按研究角度并行探索，发现关键文档后转入文档内部深挖，所有结果最终进入统一证据管线，完成来源回读、实体去重、冲突记录和带引用综合。

最终用户仍只需要选择研究目标和强度，不需要手工编排各搜索引擎。

## 2. 已确认的产品决策

### 2.1 只保留一个 Planner

- 不新建第二套互相竞争的 Planner。
- 在现有 `build_deep_research_plan` 基础上演进为 Multi-Research Planner。
- 保留两个入口：
  - `deep`：只生成并展示计划，不执行网络请求。
  - `research`：生成计划并执行。
- 研究强度只保留 `quick`、`standard`、`deep`，不增加 `max`。

### 2.2 采用混合执行边界

- Smart Search 进程负责：内部 Provider、可直接调用的 Provider Research Agents API、统一数据结构、归一化、去重、证据处理和最终综合。
- Root Agent 负责：执行 Planner 产生的外部 Skill 与 Subagent 委派、汇总委派产物，并完成跨执行单元的裁决。
- AnySearch 不重新作为 Smart Search 内部 Provider 实现。
- Agent 调用 AnySearch 后，必须把结构化结果交回 Smart Search 的公共合并管线，不能绕过证据处理直接拼接最终答案。

### 2.3 各研究强度的执行策略

| 模式 | 默认执行范围 | Provider Research Agents 限制 |
| --- | --- | --- |
| `quick` | Smart Search 基础搜索 | 不调用 |
| `standard` | Smart Search 基础搜索；Planner 判断有必要时委派 AnySearch | 不调用 |
| `deep` | 始终执行 Smart Search Research；Planner 从当前可用的 Provider Research Agents 中选择 | 默认总共最多选择并执行 2 个 |

- 超过 2 个 Provider Research Agents 只在用户显式指定时执行。
- Provider 数量不是质量目标；Planner 应按问题类型和互补性选择来源。
- 某一执行单元不可用时记录降级，不阻断仍可产生可信结果的其他执行单元。

### 2.4 Provider Research Agents 的可用性门槛

只有同时满足以下条件的能力才能进入 Planner 的候选集合：

1. 当前机器存在对应 API Key。
2. 最小 live 请求成功。
3. 返回结果符合 Smart Search 适配契约。
4. 当前套餐、余额或 credits 确实允许调用。

仅有 Key 不代表能力可用。无余额的智谱 Key 只能作为备用配置，不能被 Planner 当作当前可执行能力。付费功能若未通过 live entitlement 验证，也不能进入默认计划。

首批 Provider Research Agents 候选包括 Firecrawl Agent、Jina DeepSearch、Exa Agent 和 Tavily Research；最终启用清单以实施时重新执行的 live capability probe 为准。

### 2.5 AnySearch 的管理和调用规则

- Smart Search 仓库保留一份完整、原样的 AnySearch Skill 快照。
- 快照首选来源固定为 `jason-liao-skills/main/skill-packages/anysearch`。
- 只有首选仓库中不存在该包时，才允许从 AnySearch 官方仓库获取。
- 不读取本地开发目录作为自动同步来源。
- Smart Search 仓库内的同步脚本只管理内置快照，不修改全局 Skill。
- 全局 AnySearch Skill 继续由 Skills 工作区自己的全局安装流程管理。
- Smart Search 内置快照优先于全局安装；内置快照缺失或损坏时才尝试全局 AnySearch Skill。
- Smart Search 只向 Agent 说明何时适合委派 AnySearch，以及 AnySearch 已具备的能力；不硬编码 Agent 必须调用某个具体子命令，由模型阅读 Skill 后自行选择。
- 若运行环境没有可用 AnySearch Skill，则记录委派不可用并继续其他搜索路径。
- `ANYSEARCH_API_KEY` 随内置快照的私有 `.env` 提供，同时保持 Git、npm 包和 wheel 中不包含明文密钥。
- Agent 将 AnySearch 结果交给公共合并管线时使用最小 JSON 协议：顶层包含原始 `query`，每条来源包含 `title`、`url`、`content`，并可选包含 `published_at`。Preview 不为该协议增加运行目录、恢复命令或状态机。

### 2.6 Subagent 的职责边界

- Planner 按研究角度、待验证主张或互相独立的问题拆分 `SearchTask`，不按 Provider 一对一拆分 Subagent。
- Smart Search 第一版定义三种项目专用 Subagent：`search_scout`、`source_curator` 和 `evidence_miner`。它们属于 Smart Search 的运行时业务架构，不复用或依赖 Infra 管理的全局通用 Agent role。
- `search_scout` 在自己的研究角度内自主选择 Smart Search、AnySearch Skill 或可用 Provider Research Agents，不为每个搜索引擎新建专用 Agent。
- `source_curator` 只在候选量超过 Root Agent 的候选上下文预算时启用；它按 `SearchTask`、主题或来源分片并行整理候选，不负责最终选择关键文档。
- `evidence_miner` 只负责单个或一组紧密相关文档的证据提取，不负责跨来源最终结论，也不得继续派生 Subagent。
- Root Agent 负责 Claim Ledger、冲突裁决和最终综合，不亲自承担逐页、逐段的常规文档挖掘。
- Codex 项目专用 Agent 分别放在 `.codex/agents/search_scout.toml`、`.codex/agents/source_curator.toml` 和 `.codex/agents/evidence_miner.toml`；`skills/smart-search-cli/agents/openai.yaml` 仅保留 Skill UI 与调用元数据，不承载 Subagent 实现。
- Harness 无关的任务输入、输出和停止条件写入 `skills/smart-search-cli/references/subagent-orchestration.md`。Claude Code、Pi 等 Harness 后续只实现自己的 Agent Adapter，不能复制出互相漂移的业务协议。
- 全局 `scout`、`worker`、`complex_worker` 和 `reviewer` 仍由 Infra 管理，只用于开发、定位、实施和审查等通用工程任务；它们不参与 Smart Search 的产品运行流程。Smart Search 仓库独立管理三种项目专用 Agent 及其调用协议。

### 2.7 候选筛选与关键文档选择

- 搜索阶段的原始 `DiscoveryCandidate`、`ResearchArtifact` 和 Provider 原始产物全部落盘；筛选只生成新的结构化视图，不删除或覆盖原始结果。
- 先由确定性代码完成字段归一化、实体去重和上下文体积估算。候选规模未超过当前模式的上下文预算时，跳过 `source_curator`，把全部 `CandidateCard` 交给 Root Agent。
- 候选规模超过上下文预算时，按 `SearchTask`、主题或来源分片，动态启动多个 `source_curator`。不得把 Root Agent 无法处理的全部候选转交给单个 Curator。
- 每个 Curator 返回 `KeySourceProposal`：建议保留、延后与淘汰的候选 ID、对应理由、覆盖缺口、不确定项和原始产物引用。该返回值是可回溯的筛选提案，不是最终关键文档清单。
- Root Agent 读取各分片提案和全局覆盖摘要，决定关键文档、补搜或降级；必要时可按候选 ID 展开原始记录、检查被延后或淘汰的候选，并要求重新筛选。
- `quick` 和候选量较小的 `standard` 通常走 Root Agent 直接选择路径；`deep` 或候选溢出时才启用并行 Curator。具体触发以候选上下文预算为准，不以固定文档数量替代体积估算。

### 2.8 无 Mistral Key 的 Agentic Docs MCP

- 文档深挖思路明确改编自 Mistral Agentic Search；参考 Mistral Search Toolkit 的 Document/Chunk 定位模型和 Starter App 的 MCP 工具语义，但不直接 Fork 或改造整套 Starter App。
- Agentic Docs MCP 作为独立 Python 3.12 Sidecar 运行，不提高 Smart Search 主 CLI 当前 Python 3.10 的最低版本。
- 保留 `search`、`open`、`navigate`、`read`、`grep`、`ingest` 和 `delete`；补齐已读 chunk 排除能力，避免重复返回已经检查过的证据。
- 第一版自行实现 Mistral-compatible MCP 工具层，并使用 SQLite FTS5 与小规模本地向量矩阵组成按 `run_id` 隔离的轻量索引；不部署 Vespa，也不依赖 Starter App 的全局 Collection。
- 新增独立的 Document Embedding 配置。API URL、Key 和 Model 默认可以复用 Smart Search 当前 `INTENT_EMBEDDING_*` 的机器级配置，但向量维度、归一化方式和 Chunker 版本必须显式配置，不能继承隐式默认值或复用意图路由阈值。
- Embedding 模型、向量维度、归一化方式和 Chunker 版本共同构成索引身份；启动时必须核验它们与现有索引一致，配置改变时明确要求重建索引，不能静默混用。
- 普通 HTML 优先使用 Smart Search 已抓取的 Markdown；抓取失败或页面结构复杂时可使用 MinerU HTML。PDF、扫描件和 Office 文档按需调用 MinerU，再把解析后的 Markdown 与原始 URL、标题和定位信息交给 MCP 摄取。
- `ingest` 必须允许把本地解析产物绑定回原始 `source_id`，避免最终引用指向 MinerU 临时目录。
- MCP 本身不保存跨任务的全局已读集合；`EvidenceMiningTask` 和 Evidence Miner 使用 `run_id`、`task_id` 与已读 chunk 列表管理任务状态，避免并行 Miner 互相污染上下文。
- MinerU 与现有 Embedding 服务仍可能消耗各自额度；本决策只保证不依赖 Mistral Key 和 Mistral credits。
- MCP、本地索引、Embedding 或 MinerU 不可用时记录降级，继续使用 Smart Search Fetch 和普通正文读取；Agentic Docs MCP 不成为 `quick`、`standard` 或 `deep` 的硬依赖。

## 3. 目标执行流程

1. 接收用户问题和 `quick | standard | deep` 模式。
2. Multi-Research Planner 分解检索意图、问题类型、时间范围、来源偏好和成本边界。
3. Planner 先生成内部搜索、Provider Research Agents、外部 Skill 和 `SearchTask` 等发现阶段执行单元，并按研究角度把互相独立的 `SearchTask` 委派给 Scout。
4. 每个 Scout 在自己的问题范围内自主使用 Smart Search、AnySearch 或可用 Provider Research Agents，返回 `DiscoveryCandidate` 或 `ResearchArtifact`，不分别生成最终报告。
5. Smart Search 保存全部原始候选和产物，再按 URL、DOI、代码仓库、论文和事件实体归一化、去重，并生成可展开的 `CandidateCard`。
6. 候选未超过上下文预算时全部交给 Root Agent；超过预算时按任务或主题分片，由多个 `source_curator` 并行生成可回溯的 `KeySourceProposal`。
7. Root Agent 根据全部 CandidateCard 或各分片提案决定关键文档、补搜或降级，并为确实影响结论的关键文档创建 `EvidenceMiningTask`。
8. `evidence_miner` 先复用已有正文；需要时调用 MinerU 得到 Markdown，再通过 Agentic Docs MCP 的 `search`、`open`、`grep`、`navigate` 和 `read` 在文档内部迭代取证。
9. 每个文档挖掘任务返回带原始来源和精确 locator 的 `EvidenceItem[]`；Agentic Docs MCP 不直接生成跨来源最终答案。
10. Root Agent 将待回答的事实主张登记到 `Claim Ledger`，关联支持证据、反驳证据、不确定性和时间信息。
11. Root Agent 对冲突来源进行显式记录和权重判断，一次性生成带引用的综合结论，不分别输出互不协调的 Provider、Scout、Curator 或 Miner 摘要。

Planner 可生成的底层执行单元仍包括：

- Smart Search 内部搜索或抓取；
- Provider Research Agents API；
- Agent 执行的外部 Skill 委派。

对应架构图：

- [`docs/architecture/multi-source-search-flow-anysearch.drawio`](../architecture/multi-source-search-flow-anysearch.drawio)
- [`docs/architecture/multi-source-search-flow-anysearch.png`](../architecture/multi-source-search-flow-anysearch.png)

当前 Draw.io 和 Skill Mermaid 是实现前草图，仍需在阶段 B 按本计划修正模式门控。修正后两者必须与本计划一致，但 Mermaid 可以压缩视觉细节。

## 4. 统一数据契约

以下结构是跨 Provider、Provider Research Agents 和外部 Skill 合并的最小公共语言。字段可在实现时细化，但不得绕开这些边界直接拼接结果。

### 4.1 `ProviderRun`

记录一次执行单元的运行事实：

- `run_id`、`step_id`
- `provider`、`capability`
- `execution_kind`：`internal | provider_research_agents | delegated_skill | delegated_agent | mcp_tool`
- `status`：`planned | running | awaiting_delegate | succeeded | partial | failed | skipped`
- 开始时间、结束时间、耗时
- 请求参数摘要、用量或成本摘要
- 原始产物引用
- 错误与降级原因

### 4.2 `DiscoveryCandidate`

表示搜索阶段发现、但尚未完成证据核验的候选来源：

- 标题、URL、摘要、发布日期和来源类型
- DOI、仓库地址或其他稳定实体标识
- 来源 Provider 与原始排名
- 与查询的初始相关性信息

### 4.3 `ResearchArtifact`

表示 Provider Research Agents 或外部 Skill 返回的研究产物：

- 执行单元和来源标识
- 研究摘要或结构化发现
- 引用列表及其原始定位信息
- Provider 自带的置信度或限制说明
- 原始响应产物引用

`ResearchArtifact` 不是最终证据；其中的关键引用仍需尽可能回读原始来源。

### 4.4 `EvidenceItem`

表示已读取并可用于支撑结论的证据：

- 规范化来源标识和可访问 URL
- 证据摘录或忠实转述
- 来源发布时间、读取时间和来源类型
- 支持或反驳的 Claim 标识
- 证据质量、时效性和直接性信息

### 4.5 `Claim Ledger`

以主张为中心保存：

- `claim_id` 和规范化主张
- 支持证据与反驳证据
- 冲突类型
- 当前判断、置信度和保留意见
- 最终答案中的引用映射

### 4.6 `SearchTask`

表示一个可由 Scout 独立完成的研究角度：

- `task_id`、原始问题和本任务研究角度
- 待回答子问题或待验证主张
- 时间范围、来源偏好和成本预算
- 可用能力提示，但不固定必须调用的 Provider 或 Skill 子命令
- 期望输出：`DiscoveryCandidate[]` 或 `ResearchArtifact[]`
- 停止原因、覆盖缺口和已使用能力

### 4.7 `EvidenceMiningTask`

表示一个关键文档内部的深挖任务：

- `task_id`、原始 `source_id`、URL、标题和已有抓取产物
- 需要验证的 Claim 或具体证据问题
- 允许使用 MinerU 和 Agentic Docs MCP 的能力信息
- 已读 chunk/source 集合、调用预算和停止条件
- 期望输出：带页码、offset、chunk locator 或代码位置的 `EvidenceItem[]`
- 未找到证据、证据冲突、解析失败或预算耗尽等终止原因

### 4.8 `CandidateCard` 与 `KeySourceProposal`

`CandidateCard` 是 Root Agent 和 Curator 阅读候选时使用的紧凑视图：

- 稳定 `candidate_id`、标题、规范 URL、来源类型和时间；
- 与当前 `SearchTask` 或 Claim 的相关性摘要；
- 发现路径、Provider 排名、重复实体信息和原始产物引用；
- 可按 `candidate_id` 展开的原始 `DiscoveryCandidate` 或 `ResearchArtifact`。

`KeySourceProposal` 是一个 Curator 分片的可回溯筛选提案：

- `shard_id`、输入候选 ID 集合和上下文体积；
- 建议保留、延后与淘汰的候选 ID 及逐项理由；
- 当前覆盖情况、证据缺口、不确定项和建议的补搜方向；
- 原始产物引用与停止原因。

Root Agent 保留最终选择权；`KeySourceProposal` 不得删除原始候选，也不能直接生成 `EvidenceMiningTask`。

## 5. 分阶段实现

### 阶段 A：公共数据契约

- 定义上述核心模型及 JSON 序列化格式。
- 定义 AnySearch 最小 JSON 结果协议及公共合并入口。
- 定义 `SearchTask`、`EvidenceMiningTask` 与 `EvidenceItem[]` 的 Harness 无关协议。
- 定义 `CandidateCard`、Curator 分片输入和 `KeySourceProposal` 的 Harness 无关协议，并保留从筛选视图回到原始候选的引用。
- 保存计划、原始产物和合并产物；Preview 不实现暂停、恢复或持久状态机。
- 先以契约测试固定输入输出，再迁移现有 Research 结果。

### 阶段 B：统一 Planner

- 在现有 Planner 上加入执行单元类型、能力探测、模式预算和最多 2 个 Provider Research Agents 的约束。
- 按研究角度而不是 Provider 拆分 `SearchTask`，并在候选合并后为关键文档生成 `EvidenceMiningTask`。
- 把关键文档选择保留为 Root Agent 的语义决策；Plan Compiler 只校验候选上下文预算、Curator 分片和任务预算是否合法。
- 保持 `deep` 只规划、`research` 规划后执行。
- Planner 输出必须可解释：说明为何选择或跳过某项能力。
- 同步修正 Draw.io、渲染图和 Skill Mermaid：产品模式只保留 `quick | standard | deep`，并明确各模式的 AnySearch 与 Provider Research Agents 门控。

### 阶段 C：Provider Research Agents 适配器

- 为通过 live capability probe 的 Firecrawl、Jina、Exa、Tavily 能力实现适配器。
- 统一超时、状态、原始响应保存和 `ResearchArtifact` 转换。
- 不为未通过套餐验证的功能编写默认执行路径。

### 阶段 D：Agent 委派与结果合并

- Planner 输出 AnySearch 委派步骤和输入契约。
- Agent 自主选择 AnySearch Skill 功能，并按最小 JSON 协议返回结果。
- 为互相独立的研究角度生成并行 `SearchTask`，由 Root Agent 委派给项目专用 `search_scout`。
- 在 Smart Search 仓库增加 `search_scout`、`source_curator` 和 `evidence_miner` 三种项目专用 Agent 定义及 Harness 无关协议；不修改或依赖 Infra 的全局 Agent role。
- 候选量超过上下文预算时动态创建多个 Curator 分片；保存全部原始候选，并验证 Root Agent 可以按候选 ID 展开任意保留、延后或淘汰项。
- Scout、Curator 和 Evidence Miner 的返回值必须进入公共合并入口，不能由 Root Agent 直接把自然语言报告拼接成最终答案。
- 公共合并入口把 AnySearch 结果送入与其他来源相同的证据处理流程。

### 阶段 E：Agentic Docs MCP 与关键文档深挖

- 以独立 Python 3.12 Sidecar 实现 Mistral-compatible MCP 工具层；保留对 Mistral Agentic Search、Search Toolkit 和 Search Starter App 的来源说明。
- 参考 `source_id`、`locator`、字符区间和稳定 chunk ID 的数据模型，自行实现按 `run_id` 隔离的 SQLite FTS5 与小规模本地向量索引；第一版不部署 Vespa。
- 实现 OpenAI-compatible Document Embedder。API URL、Key 和 Model 可以复用 Smart Search 现有机器级配置，向量维度、归一化方式和 Chunker 版本使用独立显式配置；不保留 `MISTRAL_API_KEY` 强制检查和 `MistralEmbedder` 调用路径。
- 将 MinerU 作为按需解析能力：普通网页优先复用 Smart Search Markdown，PDF、扫描件、Office 和复杂 HTML 按输入类型选择 MinerU。
- 扩展摄取协议以保留原始 URL、标题、页码或 locator；由 `EvidenceMiningTask` 和 `evidence_miner` 管理 `task_id`、已读 chunk、调用预算与停止条件，不把这些状态保存为 MCP 全局变量。
- 由 `evidence_miner` 执行文档内部循环并返回 `EvidenceItem[]`；验证 MCP 缺失、本地索引不可用、Embedding 失败和 MinerU 失败时的降级路径。

### 阶段 F：证据合并与综合

- 实现候选归一化和实体级去重。
- 生成 `CandidateCard`；候选未溢出时由 Root Agent 直接选择，溢出时并行生成 `KeySourceProposal`，再由 Root Agent 做跨分片裁决。
- 回读 Provider Research Agents 和 AnySearch 引用的原始来源。
- 合并 Scout、Curator 和 Evidence Miner 返回的结构化产物，拒绝没有原始来源定位的关键证据。
- 生成 `EvidenceItem` 和 `Claim Ledger`。
- 先实现一条可供验收观察的最小 `Research Trace`：用稳定 ID 串联 `ResearchFrame`、`SearchTask`、`EvidenceMiningTask`、`ProviderRun`、原始产物、`EvidenceItem`、`Claim Ledger` 与最终报告，并保存结构化的选择、跳过、失败和降级原因。
- `Research Trace` 只记录可审计的动作、输入输出、状态、来源定位和结构化决策依据，不保存模型的隐藏思维过程；API Key、私有配置和未授权正文不得进入 Trace。
- 处理来源冲突、时效差异和证据缺口。
- 使用统一权重生成一次性带引用结论。

### 阶段 G：更新 Preview CLI 后启动 max Benchmark 调研

- 本阶段只能在阶段 A 至 F 的代码完成并通过工程测试后启动。
- 构建并安装本分支的 Smart Search CLI 到隔离的 Preview 验收环境，使后续调研使用这次实现的新功能；该操作不替换 macOS 当前激活版本。
- 使用更新后的 Preview CLI，以 `max` 调研强度搜索和回读论文、官方产品与技术文档、开源仓库、工程博客、公开案例、Benchmark 数据集和评分说明。这里的 `max` 表示验收调研的深度，不是 Smart Search 面向用户的第四种运行模式。
- 主题一只回答：当前框架在规划、Subagent 信息交换、文档选择、文档深挖、证据综合、Research Trace 和反馈循环上是否存在更好的方案。
- 主题一必须重点检查现有搜索与 Deep Research 系统怎样把计划、委派、工具执行、原始产物、证据、冲突和最终结论连接成 Trace；比较哪些信息应当持久化、哪些只属于临时日志，以及怎样在可追溯性、恢复能力、存储与上下文成本、隐私和 Harness 无关性之间取舍。
- 主题二只回答：哪些 Search、Agentic Search 和 Deep Research Benchmark 值得后续考虑，各自怎样评分、需要哪些数据与服务、复现成本多高。
- 用户提供的 [MultiAgent 工程文章](https://mp.weixin.qq.com/s/Osm8jzocOBNvkxIXSgdiNQ) 用于检查角色拆分、上下文隔离、任务 Schema、正式消息和全局状态管理；它是工程经验来源，不替代论文、官方文档或代码证据。
- SearchSwarm（[arXiv:2606.09730](https://arxiv.org/pdf/2606.09730)）只是一条论文路径示例；调研还必须覆盖官方产品材料、开源实现、评测仓库和公开工程案例。
- 本阶段不选择最终 Benchmark、不运行 Benchmark、不生成分数，也不讨论 Codex CLI、Claude Code、Pi 等 Harness 的具体适配。
- 调研报告交给用户审阅后，再决定是否创建实际 Benchmark 运行任务以及是否替换 macOS 当前激活版本。

## 6. Benchmark 调研任务

### 6.1 启动条件

max Benchmark 调研必须同时满足：

1. 阶段 A 至 F 的功能已经实现。
2. 工程测试、打包测试和有限 live smoke test 已通过。
3. 本分支的 Smart Search CLI 已安装到隔离的 Preview 验收环境。
4. 调研会话能够实际调用该 Preview CLI 的新多源搜索功能。

### 6.2 调研问题

max 调研需要回答：

1. 当前两阶段、多 Agent 搜索框架是否存在更合理的规划、委派、信息交换、关键文档选择、文档深挖、证据综合或反馈循环设计？
2. 相关论文和公开系统如何把任务发给 Subagent、限制其上下文，并把结构化结果返回 Root Agent？
3. 对多 Agent 搜索而言，什么样的 `Research Trace` 才算好？验收时先以“结论能回溯到 Claim、证据、原文位置和执行任务；失败与降级可解释；任务可恢复；记录体积与上下文开销可控；敏感信息不泄露；不依赖特定 Harness”为候选标准，再用调研结果修订，而不是预先把这些标准视为最终答案。
4. 现有论文、官方系统、开源仓库与工程实践分别怎样保存规划、任务委派、工具调用、Subagent 返回、文档读取、证据选择、冲突处理和最终引用？它们怎样区分 Trace、运行日志、证据来源信息和模型隐藏思维过程？
5. 哪些公开 Benchmark 与这次新增的多源搜索功能相关并值得后续考虑？
6. 每个候选 Benchmark 测量什么能力，数据、语料和官方评分程序是否可获取？
7. 每个候选怎样评分，是否使用确定性指标、LLM Judge 或人工复核，结果容易受到哪些搜索源、网页变化和时间因素影响？
8. 复现每个候选需要哪些数据许可、模型/API、搜索与网页读取服务、Judge、计算资源、工程时间和大致费用？

用户提供的 Firecrawl Developer Index、Mistral Agentic Search、SearchSwarm 和 MultiAgent 工程文章只作为后续 max 调研的起始线索，不代表已经选定对应 Benchmark，也不限定来源类型。

### 6.3 调研交付物

调研完成后提交：

- 架构改进建议及其论文、官方文档、代码仓库或工程材料依据；
- 多 Agent 任务输入、结构化返回和上下文隔离方式的专项比较；
- `Research Trace` 专项报告：给出概念边界、代表性方案比较、“好 Trace”的经证据修订后的判断标准、当前实现缺口，以及最小数据模型、持久化层级和展示方式建议；
- 一条从最终报告中的 Claim 反向定位到 `Claim Ledger`、`EvidenceItem`、原文 locator、`EvidenceMiningTask` / `SearchTask` 和 `ProviderRun` 的示例 Trace，并说明哪些步骤能够恢复或重放、哪些受网页变化影响只能保留历史证据；
- 候选 Benchmark 推荐表及来源；
- 每个候选的评测对象、数据获取方式、输入输出和评分流程；
- Judge 或人工复核要求，以及搜索源和时效变化对结果解释的影响；
- 预计成本、时间、依赖和复现条件。

调研结论形成后再由用户决定具体 Benchmark、实际运行方式和是否另建验收任务。本阶段不预设或实现 Benchmark Runner 与 Harness Adapter。

## 7. 验收标准

### 7.1 功能与工程验收

- `deep` 在无网络请求的情况下产出完整可执行计划。
- `quick` 不调用 Provider Research Agents 或 AnySearch。
- `standard` 只在 Planner 判断需要时委派 AnySearch，不调用 Provider Research Agents。
- `deep` 始终包含 Smart Search Research，默认总共最多选择并执行 2 个已验证可用的 Provider Research Agents；超过 2 个必须由用户显式指定。
- AnySearch 始终作为外部 Skill 委派，不恢复为内部 Provider 或重复实现。
- AnySearch 不存在、Provider 失败或套餐不可用时，流程可降级并说明覆盖缺口。
- `search_scout` 按研究角度而不是 Provider 拆分；其产物可追溯到对应 `SearchTask`，且不会作为最终报告直接拼接。
- `search_scout`、`source_curator` 和 `evidence_miner` 均由 Smart Search 仓库管理；产品运行不依赖 Infra 的全局 `scout`、`worker`、`complex_worker` 或 `reviewer`。
- 原始候选和 Provider 产物完整保存；任何 CandidateCard 或 Curator 筛选结果都可以按稳定 ID 回到原始记录。
- 候选未超过上下文预算时不启动 Curator；候选溢出时启动多个分片 Curator，不把全部溢出上下文转交给单个 Agent。
- 每个 `KeySourceProposal` 都包含输入候选集合、保留/延后/淘汰理由、覆盖缺口、不确定项和原始产物引用；Root Agent 保留关键文档的最终选择权。
- 关键文档由 `evidence_miner` 深挖并返回结构化 `EvidenceItem[]`；Root Agent 只承担规划、裁决和综合。
- Agentic Docs MCP 在没有 `MISTRAL_API_KEY` 的环境中可启动和执行最小摄取、检索、导航与读取 smoke test，且没有请求 Mistral API。
- Agentic Docs MCP 的 API URL、Key 和 Model 可以复用现有 Embedding 机器配置；模型、维度、归一化方式或 Chunker 版本不匹配时拒绝复用旧索引并给出重建提示。
- PDF、扫描件或 Office 文档需要解析时可由 MinerU 生成 Markdown，并在最终证据中保留原始 URL 与可定位信息；普通 HTML 不默认重复送入 MinerU。
- Agentic Docs MCP、本地索引、Embedding 或 MinerU 不可用时可降级，不阻断其他仍可产生可信结果的路径。
- 并行 Evidence Miner 的索引、已读 chunk 和任务状态按 `run_id`、`task_id` 隔离，不通过 MCP 全局变量互相共享。
- 所有执行结果都能追溯到 `ProviderRun` 和原始产物。
- Provider Research Agents 的摘要不能直接充当最终证据；关键结论需要尽可能回读原始引用。
- 重复 URL、DOI、仓库和同一事件不会被当作独立证据重复加权。
- 冲突结论在 `Claim Ledger` 中可追踪，最终答案说明冲突或不确定性。
- 最终输出是一次性综合结果，并包含可定位的引用。
- Git、npm 包和 wheel 均不泄露 API Key 或私有 `.env`。
- 验收过程不修改 macOS 当前激活版本。

### 7.2 Benchmark 验收

- 阶段 A 至 F 已完成并通过工程测试，随后把本分支 CLI 安装到隔离的 Preview 验收环境。
- 使用该 Preview CLI 的新多源搜索功能，以 `max` 调研强度完成两项调研：框架改进建议；Benchmark 推荐、评分流程与复现成本。
- 架构结论同时参考论文、官方产品与技术文档、开源仓库、工程博客和公开案例，并专项检查 Root Agent 与 Subagent 的任务输入、结构化返回、上下文隔离和 Research Trace。
- Trace 专项必须区分执行 Trace、普通运行日志、证据 provenance 与模型隐藏思维过程；给出有来源依据的质量标准、当前实现缺口和最小改进建议，但不在用户审阅调研结果前扩大阶段 A 至 F 的实现范围。
- Benchmark 部分只推荐候选并说明评分与复现条件，不选择最终 Benchmark、不运行 Benchmark，也不生成分数。
- 调研结束后只提交报告并等待用户决定；未经用户看完结果后明确授权，不替换 macOS 当前激活版本。

## 8. 当前实现状态

### 已实现

- Preview 分支和 macOS 首发边界。
- 删除 Smart Search 内部 AnySearch Provider、配置和专属 CLI 命令。
- AnySearch 外部 Skill 委派的路由元数据。
- 内置 AnySearch Skill 快照、同步脚本、私有配置隔离和打包规则。
- Draw.io 流程图和 Skill Mermaid 草图已经存在；模式门控仍待阶段 B 修正。
- 最小 Preview 的单元测试与打包测试；当前 macOS 激活状态需在最终验收时现场回读。

### 尚未实现

- Multi-Research Planner 的统一可执行调度。
- Provider Research Agents 的并行执行与 entitlement 动态筛选。
- Agent 委派、AnySearch 最小 JSON 回传和公共合并入口。
- 按研究角度委派项目专用 `search_scout`，按候选体积动态委派项目专用 `source_curator`，并由项目专用 `evidence_miner` 深挖关键文档；三者共用 Harness 无关协议。
- 无 Mistral Key 的 Agentic Docs MCP Sidecar、现有 Embedding 适配、MinerU 解析衔接与已读 chunk 排除。
- `ProviderRun`、`DiscoveryCandidate`、`ResearchArtifact`、`CandidateCard`、`KeySourceProposal`、`EvidenceItem` 和 `Claim Ledger` 的完整代码实现。
- 实体去重、原始来源回读、冲突处理和统一加权综合。
- 整张流程图对应的端到端执行与验收。
- max 架构复盘与 Benchmark 推荐报告。

## 9. 尚待确认的关键问题

这些问题会改变接口或执行模型，必须在对应阶段编码前确认：

1. Provider Research Agents 的精确选择优先级，以及用户显式选择多个能力时的 CLI 表达方式。
2. 最终综合沿用当前 Smart Search 的合成模型，还是允许 Planner 独立选择合成 Provider。
3. `quick | standard | deep` 各模式允许委派多少个 SearchTask 和 EvidenceMiningTask，以及调用预算如何与全局并发上限结合。
4. Document Embedding 的默认显式维度和归一化方式，以及本地索引达到什么规模后才需要重新评估 Vespa。
5. max Benchmark 调研完成后，用户是否选择候选 Benchmark 并另建实际运行任务。

第 1 至 4 项在对应实现阶段编码前继续讨论并确定；第 5 项只能在新版 Preview CLI 完成后通过 max 调研确定。

## 10. 本轮设计依据

- Smart Search 原始仓库：<https://github.com/konbakuyomu/smartsearch>
- Smart Search 当前改编仓库：<https://github.com/whycantfindaname/smartsearch>
- Mistral Agentic Search 文章：<https://mistral.ai/news/agentic-search/>
- Mistral Search Toolkit 文档：<https://docs.mistral.ai/studio-api/search-toolkit>
- Mistral Search Toolkit Document Model：<https://docs.mistral.ai/studio-api/search-toolkit/document-model>
- Mistral Search Starter App：<https://github.com/mistralai/search-starter-app>
- MultiAgent 工程经验文章：<https://mp.weixin.qq.com/s/Osm8jzocOBNvkxIXSgdiNQ>
- SearchSwarm 论文路径示例：<https://arxiv.org/pdf/2606.09730>
- Skill 结构与 `agents/openai.yaml` 边界：`/Users/jasonliao/.codex/skills/.system/skill-creator/SKILL.md`
- MinerU 解析能力与模式边界：`/Users/jasonliao/.codex/skills/mineru-cloud-api/SKILL.md`
- 全局与项目 Subagent 所有权边界：`/Users/jasonliao/Desktop/code/Tools/jason-liao-agent-infra-macos/docs/solutions/architecture-patterns/native-default-specialized-scout-role-boundary.md`
