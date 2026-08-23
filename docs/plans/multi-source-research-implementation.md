# Smart Search 多源研究全流程实现计划

> 状态：实施前设计已部分确认
>
> 目标分支：`preview/macos-multisource-search`
>
> 首发范围：仅 macOS Preview
>
> 最后更新：2026-08-23

本文档是 Smart Search 多源研究改造的实现依据。后续新增决策只更新本文档，不以聊天记录或流程图中的隐含含义作为实现依据。

## 1. 目标

把 Smart Search 从“单次搜索命令与单一 Research 路径”扩展为统一的多源研究系统：同一个 Planner 根据问题、研究强度、可用能力和成本约束生成执行计划；Smart Search 内部搜索、Native Research API 与外部 Skill 以混合方式执行；所有结果进入统一证据管线，完成来源回读、实体去重、冲突记录和带引用综合。

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

- Smart Search 进程负责：内部 Provider、可直接调用的 Native Research API、统一数据结构、归一化、去重、证据处理和最终综合。
- Agent 负责：理解并调用外部 Skill，尤其是 AnySearch Skill。
- AnySearch 不重新作为 Smart Search 内部 Provider 实现。
- Agent 调用 AnySearch 后，必须把结构化结果交回 Smart Search 的公共合并管线，不能绕过证据处理直接拼接最终答案。

### 2.3 各研究强度的执行策略

| 模式 | 默认执行范围 | Native Research 限制 |
| --- | --- | --- |
| `quick` | Smart Search 基础搜索 | 不调用 |
| `standard` | Smart Search 基础搜索；Planner 判断有必要时委派 AnySearch | 不调用 |
| `deep` | 始终执行 Smart Search Research；Planner 从当前可用的 Native Research 中选择 | 默认总共最多选择并执行 2 个 |

- 超过 2 个 Native Research 只在用户显式指定时执行。
- Provider 数量不是质量目标；Planner 应按问题类型和互补性选择来源。
- 某一执行单元不可用时记录降级，不阻断仍可产生可信结果的其他执行单元。

### 2.4 Native Research 的可用性门槛

只有同时满足以下条件的能力才能进入 Planner 的候选集合：

1. 当前机器存在对应 API Key。
2. 最小 live 请求成功。
3. 返回结果符合 Smart Search 适配契约。
4. 当前套餐、余额或 credits 确实允许调用。

仅有 Key 不代表能力可用。无余额的智谱 Key 只能作为备用配置，不能被 Planner 当作当前可执行能力。付费功能若未通过 live entitlement 验证，也不能进入默认计划。

首批 Native Research 候选包括 Firecrawl Agent、Jina DeepSearch、Exa Agent 和 Tavily Research；最终启用清单以实施时重新执行的 live capability probe 为准。

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

## 3. 目标执行流程

1. 接收用户问题和 `quick | standard | deep` 模式。
2. Multi-Research Planner 分解检索意图、问题类型、时间范围、来源偏好和成本边界。
3. Planner 生成三类执行单元：
   - Smart Search 内部搜索或抓取；
   - Native Research API；
   - Agent 执行的外部 Skill 委派。
4. 各执行单元返回统一 `ProviderRun`，其发现结果分别归一化为 `DiscoveryCandidate` 或 `ResearchArtifact`。
5. 合并候选，并按 URL、DOI、代码仓库、论文和事件实体去重。
6. 对关键候选读取原始网页、论文、文档或代码来源，生成 `EvidenceItem`。
7. 将待回答的事实主张登记到 `Claim Ledger`，关联支持证据、反驳证据、不确定性和时间信息。
8. 对冲突来源进行显式记录和权重判断。
9. 一次性生成带引用的综合结论，不分别输出互不协调的 Provider 摘要。

对应架构图：

- [`docs/architecture/multi-source-search-flow-anysearch.drawio`](../architecture/multi-source-search-flow-anysearch.drawio)
- [`docs/architecture/multi-source-search-flow-anysearch.png`](../architecture/multi-source-search-flow-anysearch.png)

当前 Draw.io 和 Skill Mermaid 是实现前草图，仍需在阶段 B 按本计划修正模式门控。修正后两者必须与本计划一致，但 Mermaid 可以压缩视觉细节。

## 4. 统一数据契约

以下结构是跨 Provider、Native Research 和外部 Skill 合并的最小公共语言。字段可在实现时细化，但不得绕开这些边界直接拼接结果。

### 4.1 `ProviderRun`

记录一次执行单元的运行事实：

- `run_id`、`step_id`
- `provider`、`capability`
- `execution_kind`：`internal | native_research | delegated_skill`
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

表示 Native Research 或外部 Skill 返回的研究产物：

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

## 5. 分阶段实现

### 阶段 A：公共数据契约

- 定义上述核心模型及 JSON 序列化格式。
- 定义 AnySearch 最小 JSON 结果协议及公共合并入口。
- 保存计划、原始产物和合并产物；Preview 不实现暂停、恢复或持久状态机。
- 先以契约测试固定输入输出，再迁移现有 Research 结果。

### 阶段 B：统一 Planner

- 在现有 Planner 上加入执行单元类型、能力探测、模式预算和最多 2 个 Native Research 的约束。
- 保持 `deep` 只规划、`research` 规划后执行。
- Planner 输出必须可解释：说明为何选择或跳过某项能力。
- 同步修正 Draw.io、渲染图和 Skill Mermaid：产品模式只保留 `quick | standard | deep`，并明确各模式的 AnySearch 与 Native Research 门控。

### 阶段 C：Native Research 适配器

- 为通过 live capability probe 的 Firecrawl、Jina、Exa、Tavily 能力实现适配器。
- 统一超时、状态、原始响应保存和 `ResearchArtifact` 转换。
- 不为未通过套餐验证的功能编写默认执行路径。

### 阶段 D：Agent 委派与结果合并

- Planner 输出 AnySearch 委派步骤和输入契约。
- Agent 自主选择 AnySearch Skill 功能，并按最小 JSON 协议返回结果。
- 公共合并入口把 AnySearch 结果送入与其他来源相同的证据处理流程。

### 阶段 E：证据合并与综合

- 实现候选归一化和实体级去重。
- 回读 Native Research 和 AnySearch 引用的原始来源。
- 生成 `EvidenceItem` 和 `Claim Ledger`。
- 处理来源冲突、时效差异和证据缺口。
- 使用统一权重生成一次性带引用结论。

### 阶段 F：更新 Preview CLI 后启动 max Benchmark 调研

- 本阶段只能在阶段 A 至 E 的代码完成并通过工程测试后启动。
- 构建并安装本分支的 Smart Search CLI 到隔离的 Preview 验收环境，使后续调研使用这次实现的新功能；该操作不替换 macOS 当前激活版本。
- 使用更新后的 Preview CLI，以 `max` 调研强度搜索和读取 Benchmark 的官方文档、论文、数据集、评测脚本与复现说明。这里的 `max` 表示验收调研的深度，不是 Smart Search 面向用户的第四种运行模式。
- 调研哪些 Search、Agentic Search 和 Deep Research Benchmark 适合测试这次新增的多源搜索功能，以及各 Benchmark 应如何运行。
- 调研 Codex CLI 作为 Harness 时，能否让每道题在独立会话中调用 `smart-search-cli` Skill 完成搜索并接受官方评分。
- 调研同一测试方法迁移到 Claude Code、Pi 或其他 Harness 时需要哪些适配，以及 Harness 和模型差异会怎样影响结果解释。
- 调研完成前不预先确定 Benchmark 名称、测试组合、指标、阈值或 Harness 实现。

### 阶段 G：运行选定 Benchmark 并提交验收结果

- 根据阶段 F 的调研结论选择少量适合、公开且能够复现的 Benchmark。
- 只测试本次新增的多源搜索功能，不强制运行无搜索、单 Provider、旧版 Smart Search、`Naive Union` 或组件消融对照。
- 使用调研确认的 Harness 和 Benchmark 官方评分方法逐题运行，保存问题、Skill 调用记录、答案、引用、评分、延迟、token、费用和失败信息。
- 提交调研报告、运行方法、原始结果、失败案例、替换建议和回滚说明，保持 macOS 当前激活的 `smart-search-cli` 不变。
- 用户审阅验收结果并明确同意替换后，另行建立 macOS 替换任务；验收完成本身不构成替换授权。
- macOS 替换完成并稳定运行后，再由用户决定是否合并到 `lwj_dev` 并同步其他机器；本计划不授权自动替换、push 或跨机器部署。

## 6. Benchmark 调研任务

### 6.1 启动条件

max Benchmark 调研必须同时满足：

1. 阶段 A 至 E 的功能已经实现。
2. 工程测试、打包测试和有限 live smoke test 已通过。
3. 本分支的 Smart Search CLI 已安装到隔离的 Preview 验收环境。
4. 调研会话能够实际调用该 Preview CLI 的新多源搜索功能。

### 6.2 调研问题

max 调研需要回答：

1. 哪些公开 Benchmark 与这次新增的多源搜索功能相关并值得实际运行？
2. 每个候选 Benchmark 测量什么能力，数据、语料和官方评分程序是否可获取？
3. 如何使用 Codex CLI 作为 Harness，让 Benchmark 的每个问题分别调用 `smart-search-cli` Skill 搜索并返回可评分答案？
4. 如何确认 Agent 确实调用了新功能，并保存必要的调用记录和运行结果？
5. 同一方法能否迁移到 Claude Code、Pi 或其他 Harness？需要替换哪些启动、Skill 加载和结果采集接口？
6. Harness、模型、提示词和运行预算的差异会如何限制不同结果之间的比较？
7. 选定 Benchmark 的运行成本、预计时间、并发限制和失败恢复方式是什么？

用户提供的 Firecrawl Developer Index 和 Mistral Agentic Search 页面只作为后续 max 调研的起始线索，不代表已经选定对应 Benchmark。

### 6.3 调研交付物

调研完成后提交：

- 候选 Benchmark 对照表及来源；
- 推荐实际运行的少量 Benchmark 和选择理由；
- 每个 Benchmark 在 Codex CLI 中逐题调用 Skill 的运行方案；
- Claude Code、Pi 和其他适用 Harness 的迁移判断；
- 预计成本、时间、依赖和复现条件；
- 尚不能运行的 Benchmark 及其阻碍；
- 后续实际 Benchmark 运行计划。

调研结论形成后再决定具体 Benchmark、指标、Runner 和 Harness Adapter。本计划不在代码实现前预设这些内容。

## 7. 验收标准

### 7.1 功能与工程验收

- `deep` 在无网络请求的情况下产出完整可执行计划。
- `quick` 不调用 Native Research 或 AnySearch。
- `standard` 只在 Planner 判断需要时委派 AnySearch，不调用 Native Research。
- `deep` 始终包含 Smart Search Research，默认总共最多选择并执行 2 个已验证可用的 Native Research；超过 2 个必须由用户显式指定。
- AnySearch 始终作为外部 Skill 委派，不恢复为内部 Provider 或重复实现。
- AnySearch 不存在、Provider 失败或套餐不可用时，流程可降级并说明覆盖缺口。
- 所有执行结果都能追溯到 `ProviderRun` 和原始产物。
- Native Research 的摘要不能直接充当最终证据；关键结论需要尽可能回读原始引用。
- 重复 URL、DOI、仓库和同一事件不会被当作独立证据重复加权。
- 冲突结论在 `Claim Ledger` 中可追踪，最终答案说明冲突或不确定性。
- 最终输出是一次性综合结果，并包含可定位的引用。
- Git、npm 包和 wheel 均不泄露 API Key 或私有 `.env`。
- 验收过程不修改 macOS 当前激活版本。

### 7.2 Benchmark 验收

- 阶段 A 至 E 已完成并通过工程测试，随后把本分支 CLI 安装到隔离的 Preview 验收环境。
- 使用该 Preview CLI 的新多源搜索功能，以 `max` 调研强度完成 Benchmark 文档调研。
- 调研报告明确哪些 Benchmark 值得运行、怎样运行、Codex CLI Harness 是否可行，以及 Claude Code、Pi 等 Harness 是否能够复用。
- 根据调研结论选择少量 Benchmark，只运行本次新增的多源搜索功能。
- 结果可复现到题目级，包含 Skill 调用记录、答案、引用、官方评分、延迟、token、费用和失败信息。
- Benchmark 验收结束后只提交报告并等待用户决定；未经用户看完结果后明确授权，不替换 macOS 当前激活版本。

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
- Native Research 的并行执行与 entitlement 动态筛选。
- Agent 委派、AnySearch 最小 JSON 回传和公共合并入口。
- `ProviderRun`、`DiscoveryCandidate`、`ResearchArtifact`、`EvidenceItem` 和 `Claim Ledger` 的完整代码实现。
- 实体去重、原始来源回读、冲突处理和统一加权综合。
- 整张流程图对应的端到端执行与验收。
- Benchmark max 调研报告、选定 Benchmark 的运行方法与实际验收结果。

## 9. 尚待确认的关键问题

这些问题会改变接口或执行模型，必须在对应阶段编码前确认：

1. Native Research 的精确选择优先级，以及用户显式选择多个能力时的 CLI 表达方式。
2. 最终综合沿用当前 Smart Search 的合成模型，还是允许 Planner 独立选择合成 Provider。
3. max Benchmark 调研完成后，具体选择哪些 Benchmark，以及 Codex CLI、Claude Code、Pi 的 Harness 实现方式。

第 1、2 项在对应实现阶段根据现有代码确定；第 3 项只能在新版 Preview CLI 完成后通过 max 调研确定。
