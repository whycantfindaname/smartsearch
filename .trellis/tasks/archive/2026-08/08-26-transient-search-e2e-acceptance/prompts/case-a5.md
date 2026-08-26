{{COMMON}}

## 研究任务

截至 2026-08-26 研究最新 Apple Mac mini 与 Mac Studio。使用 Apple 官方来源比较
announcement date、chip、memory、I/O、display support、dimensions、带地区标签的
pricing 与 product positioning。每个比较字段都要绑定相邻直接来源；地区与币种不明确
时标记证据缺口，不用第三方价格替代官方价格。先用 `search` 定位 Apple 官方候选页，
再分别对 Mac mini newsroom、Mac mini specs、Mac Studio newsroom、Mac Studio specs
这四类官方直接来源的已知 URL 执行 `fetch`。每个 URL 的标准 fetch 链结束后，若仍失败
且错误目录允许显式兼容路线，应在转向下一个 URL 前完成该 URL 的一次允许恢复。任何
返回质量门失败的内容都不能进入引用；四类来源至少各有一个 `verified` 直接来源后，才能
把答案标为完成。
