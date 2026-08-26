# Initial Context

## User Question

审计 xAI、OpenAI、Exa、Tavily、Firecrawl 和 Jina Reader 的官方错误身份、重试边界与限流等待信号，并记录 Smart Search 的接受观察。

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
    "claim_spec_id": "claim-xai-error-identity",
    "decision_criteria": [],
    "statement": "xAI 官方 Debugging Errors 页面以 HTTP status 和错误消息描述错误，并将 429 定义为达到 inference rate limit；公开页面没有建立 Smart Search 本地 exact 504 + upstream_server_error marker 的 provider contract。",
    "terms_scope": {},
    "time_boundary": {}
  },
  {
    "claim_spec_id": "claim-xai-rate-limits",
    "decision_criteria": [],
    "statement": "xAI 官方 Rate Limits 页面按 model 说明 RPS 与 TPM 限制，超过限制返回 429，并给出 exponential backoff 处理示例。",
    "terms_scope": {},
    "time_boundary": {}
  },
  {
    "claim_spec_id": "claim-openai-error-boundary",
    "decision_criteria": [],
    "statement": "OpenAI 官方错误码页面在 HTTP 429 下区分 credits、temporary rate limit、organization/project spend limit 和 organization usage limit，并说明 billing、spend 或 quota 错误不能靠重试恢复。",
    "terms_scope": {},
    "time_boundary": {}
  },
  {
    "claim_spec_id": "claim-openai-rate-signals",
    "decision_criteria": [],
    "statement": "OpenAI 官方 Rate Limits 页面把 Retry-After 定义为 temporary rate-limit error 的最小等待时间，并提供 x-ratelimit 相关 header。",
    "terms_scope": {},
    "time_boundary": {}
  },
  {
    "claim_spec_id": "claim-exa-error-identity",
    "decision_criteria": [],
    "statement": "Exa 官方错误码页面使用 requestId、error 和 tag 识别错误，并将 403 与 422 细分为权限、功能、内容策略和处理失败等 provider-native 情况。",
    "terms_scope": {},
    "time_boundary": {}
  },
  {
    "claim_spec_id": "claim-exa-rate-limits",
    "decision_criteria": [],
    "statement": "Exa 官方 Rate Limits 页面按 endpoint 提供 QPS 限制。",
    "terms_scope": {},
    "time_boundary": {}
  },
  {
    "claim_spec_id": "claim-tavily-error-boundary",
    "decision_criteria": [],
    "statement": "Tavily 官方错误页将 432/433 作为 plan 或 PAYGO limit，并要求升级 plan 或提高 limit；429 使用降速和 exponential backoff，500 可稍后重试。",
    "terms_scope": {},
    "time_boundary": {}
  },
  {
    "claim_spec_id": "claim-tavily-rate-signals",
    "decision_criteria": [],
    "statement": "Tavily 官方 Rate Limits 页面说明 429 响应包含 retry-after 秒数，并要求 retry logic 尊重该值。",
    "terms_scope": {},
    "time_boundary": {}
  },
  {
    "claim_spec_id": "claim-firecrawl-retry-matrix",
    "decision_criteria": [],
    "statement": "Firecrawl 官方错误页要求以 Retryable 列作为恢复判断权威，而不是只根据 HTTP status 推断。",
    "terms_scope": {},
    "time_boundary": {}
  },
  {
    "claim_spec_id": "claim-jina-rate-limit-evidence",
    "decision_criteria": [],
    "statement": "Jina Reader 官方页面核验了 RPM、TPM 以及按 IP/API key 执行的限流维度，但没有提供本次所需的 error identity、429 retry、backoff 或 Retry-After 证据。",
    "terms_scope": {},
    "time_boundary": {}
  }
]
```
