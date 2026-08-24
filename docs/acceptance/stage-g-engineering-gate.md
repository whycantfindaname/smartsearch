# Stage G 工程验收记录

> 分支：`preview/multi-source-agentic-research`
> 验收日期：2026-08-24
> 边界：Provider 与文档挖掘实跑在仓库工作树、隔离 Preview 配置和临时 run-local artifact root 中完成；随后只把既有运行产物迁移到仓库内、被 Git 忽略的持久化 Research Workspace，没有重跑 Provider。未替换当前 macOS 激活版本，未修改全局 Infra 配置，未 commit、push 或 merge。

## 结论

里程碑 A–F、仓库配置收尾和工程 E2E Gate 已通过，Stage G 的 `deep` 研究闭环已真实运行。最终运行保留 113 个候选、2 份 Curator 提案、7 份项目 Agent 结果、16 条可定位证据和 2 条 ClaimRecord；16/16 条最终引用均通过 Claim → Evidence → task/attempt → artifact/snapshot/raw ref 反向验证。两个 ClaimRecord 均为 `weakly_supported`，没有把局部公开证据外推成对整套架构或 Benchmark 的完整证明。

## 工程 Gate

| 检查 | 结果 |
| --- | --- |
| 根包测试 | `560 passed` |
| Python 3.12 Sidecar 测试 | `2 passed` |
| 源码与打包 Sidecar 镜像 | 一致；仅运行时 `__pycache__` 被排除比较 |
| Skill 源文件与打包快照 | 29 个公共文件一致 |
| Python 根包 | wheel 构建成功；包含 Sidecar、Skill、Research Workspace visualizer 和 `THIRD_PARTY_NOTICES.md` |
| Sidecar 包 | sdist 与 wheel 构建成功 |
| npm tarball | 隔离 npm 配置下安装 smoke 通过；Sidecar、Skill 与 NOTICE 均存在 |
| 词法文档路径 | Python 3.12、Search Toolkit 0.0.11、SQLite FTS5；不调用 Mistral API，不需要 Vespa/Docker |
| Secret 检查 | tracked files、wheel/sdist、Sidecar 包和 Stage G Trace/Artifact 中未命中现有 Key 形态；私有 `.env` / `runtime.conf` 未进入 tracked files |
| Diff 健康 | `git diff --check` 通过 |

自动化 E2E 覆盖 locator 复位、Claim stance、引用反向追踪、缺 Key、entitlement failure、timeout、partial、单 Provider failure、AnySearch/Sidecar/Embedding/MinerU 降级、不可信输入边界和确定性去重。Stage G 又以真实 Provider、真实网页和真实 Sidecar 复跑了关键路径。

## 隔离配置与 live 状态

验收使用独立 `SMART_SEARCH_CONFIG_DIR`，由当前 macOS 私密配置复制到临时目录后运行，原始 `~/.config/smart-search/config.json` 在复制前后摘要一致。`config path` 指向隔离目录；`config list` 中 9 个敏感字段均显示为 masked；`doctor` 返回 `ok=true`。

live probe 结果：

- OpenAI-compatible main search：chat 与 models endpoint 均为 HTTP 200；
- Context7、Exa、Tavily、Firecrawl、Jina：通用连接检查均成功；
- Firecrawl：验收结束时剩余 788 credits；
- Search Toolkit Sidecar：Python 3.12、toolkit 0.0.11、health `ok`；
- Tavily 通用 API 可达，但 Tavily Research 的真实调用返回 HTTP 432 套餐上限。因此通用 reachability 不能替代某个付费功能的 entitlement 证明。

临时配置只用于验收，不是新的凭据权威来源。仓库仍由 `src/smart_search/config.py`、`setup`、`config`、`doctor` 和配置所有权文档管理非敏感契约；AnySearch 与 MinerU 保持各自 Skill 的凭据边界。

## Stage G 运行记录

- run id：`run-stage-g-seq-20260823T191412Z`
- 模式：`deep`
- 候选：113 个 `DiscoveryCandidate` / `CandidateCard`
- Curator：Root 根据 58,895 字符的候选摘要估计动态拆成 academic 50 项和 multisource 63 项两个 shard
- 项目 Agent：2 个 Search Scout、2 个 Source Curator、3 个 Evidence Miner；全部返回结构化结果，均未创建后代
- 证据：architecture 10 条，benchmark 6 条；共 16 条 exact character-range locator
- Claim：architecture 与 benchmarks 均为 `weakly_supported`
- 最终引用：16 条；反向验证 `ok=true`
- Trace：run-local、append-only；执行事件与证据 provenance 分开记录

Provider Research Agents 同一任务并发独立尝试：

| Provider Research Agent | 结果 | 观测 |
| --- | --- | --- |
| Firecrawl Agent | timeout | 外部 run id 已保存；整体研究继续 |
| Jina DeepSearch | timeout | 整体研究继续 |
| Exa Agent | success | 7 次搜索，6.163 agent compute units，总成本 `$0.6493` |
| Tavily Research | failed | HTTP 432，当前套餐用量上限 |

发现阶段还成功运行了主搜索、Firecrawl Academic Index、Firecrawl Developer Index、两个 Search Scout 和已知 URL fetch；关键正文通过 Search Toolkit 的 `grep/read` 形成 EvidenceItem。SearchSwarm 与用户提供的 MultiAgent 文章均进入正式证据链，而不是只停留在候选列表。

## Research Workspace 与可视化

既有 Stage G 运行已迁移到：

`.smart-search/research-runs/run-stage-g-seq-20260823T191412Z`

该目录保存 `latest_dossier.json`、7 个语义检查点、19 个任务目录、Evidence/Claim 投影、16 条引用验证、28 条 metadata-only public Trace 事件、最终综合报告和三份验收报告。Dossier、原始 append-only Trace、Artifact、EvidenceItem 和 ClaimRecord 仍是权威数据；Markdown 只是可读投影。Workspace 与可视化输入不保存隐藏推理。

用户可在独立终端启动只读页面：

```bash
smart-search research-view .smart-search/research-runs/run-stage-g-seq-20260823T191412Z --port 8080
```

页面只监听 `127.0.0.1`。本次验收没有替用户启动或后台驻留该服务。

## 验收中发现并修复的问题

1. **Firecrawl Developer Index 可选字段。** live 响应缺少可选 `coverage/reranked` 时被错误判失败。适配器改为“字段存在则校验类型，不存在则接受”，新增回归测试后 live 重试成功。
2. **词法模式虚假失败。** 显式关闭 Embedding 时仍探测 OpenAI-compatible Embedding，且 `not_requested` MinerU / `not_used` fallback 被转换为失败 attempt。Sidecar 与桥接层改为只记录实际请求的组件；复跑只出现 loader、Search Toolkit ingestion 和 SQLite FTS5 成功记录。
3. **索引身份升级。** 增加 `embedding_enabled` 后，验收早期索引身份不完整，Sidecar 以 `INDEX_IDENTITY_MISMATCH` 拒绝混用。旧临时索引被保留备份并重建，新身份检查通过。这是受控重建，不是静默迁移。
4. **Harness 进程期限。** 把所有长任务放入一次 `execute` 时，外部 Harness 在约三分钟后终止进程。改用 caller-held 的逐步 add/execute/persist 后完成研究。Skill 已补充长运行分步保存 dossier 的建议；Preview 仍不声称自动恢复。

## 交付物

- [架构复盘](stage-g-architecture-review.md)
- [Benchmark 候选推荐](stage-g-benchmark-recommendations.md)
- 本工程验收记录
- 持久化 Research Workspace 与只读搜索过程可视化

下一步只剩用户审阅。Benchmark 尚未选择或运行，当前 macOS 激活版本也尚未替换。
