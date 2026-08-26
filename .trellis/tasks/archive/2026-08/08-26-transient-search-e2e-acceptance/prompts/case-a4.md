{{COMMON}}

## 研究任务

查找 2025-08-26 至 2026-08-26 首次发布的 Deep Research Agent 论文、benchmark 或
开源实现，重点筛选评估 source coverage、evidence faithfulness、citation correctness
或 fault recovery 的工作。区分论文、评测集和 repository，追溯原始论文或官方项目页，
并报告发布日期和证据缺口。先按 Smart Search Skill 中适用于官方域名、论文和
date-filtered low-noise discovery 的显式 source-first 路线执行一次检索；只使用该 Skill
已文档化的参数，不要通过任务启动器探测 `--help`。该 provider 请求结束后，只根据实际
返回结果选择其他允许的显式学术或 broad discovery 路线；失败后不得再次进入同一
provider，也不得使用可能静默重选失败 provider 的复合 `research` 路线。Discovery 只
生成候选：必须继续通过 `fetch`、学术读取命令或其他允许的已知 URL 路线打开至少一个
原始论文、官方项目页或源码仓库，并取得至少一个 `verified` 直接来源后才能把答案标为
完成；没有直接证据时应继续使用尚未耗尽的允许路线。
