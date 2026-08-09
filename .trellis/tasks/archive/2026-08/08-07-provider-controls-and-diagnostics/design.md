# Design

- 使用共享异常分类 helper，保留各 helper 的成功返回 shape。
- provider helper 不再吞 HTTP/transport/parse failure；fallback boundary 负责记录并继续同能力 fallback。
- Tavily enabled predicate 在 registration 与显式 call boundary 双重执行。
- smoke 由 failed/degraded/skipped case lists 派生 status；renderer 使用 status 展示总体健康度。
