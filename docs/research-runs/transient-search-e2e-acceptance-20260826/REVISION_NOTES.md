# 修订说明

本目录按照 Language System 的技术文档与修订合约重写。修订目标是让读者先获得可用结论，再按需进入机器证据；没有改变原验收的运行时行为，也没有把未核验的搜索候选提升为正式来源。

## 主要表达与结构调整

| 原表达或结构 | 当前表达或结构 | 原因 |
| --- | --- | --- |
| 报告末尾散列 URL 或手工 References | 主张后紧邻编号引用，由 `reference_register.json` 确定性生成 References | 让显示引用可反查 ClaimRecord、EvidenceItem、artifact snapshot 与 locator |
| 搜索结果、网页正文和本地验收记录混在同一证据层 | Web 直接来源进入 citation-backed evidence；本地运行记录只作为脱敏 search materials 链接 | 防止把搜索线索或本地执行事实误写成外部事实来源 |
| `agentic`、`workflow`、`multi-stage`、`multi-agent` 混用 | 按原文的组织方式分别表述 | 避免仅凭“组件较多”推断 multi-agent |
| “最新”“最近一个月”等相对时间未显式锚定 | 报告写明检索日、时间窗和日期判据 | 保证时间敏感结论可复核 |
| 验收日志长期依赖 Trellis 归档路径 | 持久 Workspace 保存报告、公开 Trace、证据注册表和脱敏搜索材料 | 让 task 归档后仍可阅读与审计 |

## 术语候选

本轮没有需要加入全局 terminology 的新词条。Research Workspace、ClaimRecord、EvidenceItem、citation verification、reference register、Trace、provider、`doctor` 等继续保持项目既有英文 identity；中文解释只在首次出现或边界容易混淆时补充。

## 未改变的内容

- 未修改 Smart Search 的错误分类、retry 或 replay 逻辑。
- 未重新运行任何实时调研命令或 `doctor`。
- 未改写原 Trellis 归档；持久目录是脱敏、可重建的投影。
