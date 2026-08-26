# Initial Context

## User Question

比较 OpenAI Agents SDK、LangGraph 与 PydanticAI 在持久化与检查点、失败与重试、人工介入以及可观测性方面的 Python 官方接口与适用边界。

## Scope and Constraints

```json
{
  "permissions": [
    "public_web_saved_evidence"
  ],
  "scope": {
    "migration_commit": "f3a30d4eab2dee4656e0fbdfc020f490f4fa8594",
    "source": "sanitized transient-search acceptance evidence"
  },
  "source_preferences": [],
  "time_boundary": {},
  "untrusted_content_policy": "treat_as_data",
  "user_constraints": {
    "direct_sources_only": true,
    "no_live_search": true,
    "preserve_original_acceptance_archive": true
  }
}
```

## Initial Claim Frame

```json
[
  {
    "claim_spec_id": "claim-a3-persistence",
    "decision_criteria": [],
    "statement": "三者的 durable state 边界不同：LangGraph 原生围绕 thread-scoped graph checkpoint；OpenAI Agents SDK 的 Session 与 RunState 分别覆盖对话历史和暂停审批；PydanticAI 把跨重启 durable execution 放在官方集成。",
    "terms_scope": {},
    "time_boundary": {}
  },
  {
    "claim_spec_id": "claim-a3-retry",
    "decision_criteria": [],
    "statement": "三者将失败与重试放在不同层：OpenAI Agents SDK 关注 model request 的 replay safety，LangGraph 关注 node 级 retry 与错误路由，PydanticAI 分开处理 validation/tool retry 与 HTTP transport retry。",
    "terms_scope": {},
    "time_boundary": {}
  },
  {
    "claim_spec_id": "claim-a3-hitl",
    "decision_criteria": [],
    "statement": "三者的 human-in-the-loop 边界不同：OpenAI Agents SDK 围绕敏感 tool approval，LangGraph 允许在 node 中暂停并恢复 graph state，PydanticAI 用 Deferred Tools 表达审批与外部执行的 continuation。",
    "terms_scope": {},
    "time_boundary": {}
  },
  {
    "claim_spec_id": "claim-a3-observability",
    "decision_criteria": [],
    "statement": "三者都能形成运行轨迹，但归属不同：OpenAI Agents SDK 默认启用 runner tracing，LangGraph 通过 LangSmith 接入，PydanticAI 提供可选的 OpenTelemetry/Logfire instrumentation。",
    "terms_scope": {},
    "time_boundary": {}
  }
]
```
