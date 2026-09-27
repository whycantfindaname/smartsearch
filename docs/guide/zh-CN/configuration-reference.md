[手册目录](../README.md) · [English](../en/configuration-reference.md)

# 全部配置项

由当前配置元数据生成。下表列出全部可保存键；申请 Key、配置优先级、运行环境变量及最低能力要求见[配置指南](configuration.md)。未设置的密钥必须由用户提供；可选服务未配置时不会自动启用。

## 先配这三样

| 配置键 | 用途及条件 | 类型 / 取值 | 默认值 |
| --- | --- | --- | --- |
| `XAI_API_KEY` | 用 xAI 做主搜索时填这个。和下面的 OpenAI 兼容接口二选一即可。 | `secret` | 未设置 |
| `XAI_API_URL` | 用官方地址就别动。走代理或中转时才改。 | `url` | `https://api.x.ai/v1` |
| `XAI_MODEL` | 留空用默认模型。 | `text` | `grok-4-fast` |
| `XAI_TOOLS` | 逗号分隔。可选 web_search 和 x_search。 | `web_search, x_search` | `web_search,x_search` |
| `OPENAI_COMPATIBLE_API_URL` | 任何兼容 OpenAI 协议的服务都行。要和下面的 key 一起填才算配好。 | `url` | 未设置 |
| `OPENAI_COMPATIBLE_API_KEY` | 下面的链接是 OpenAI 官方的。用中转或第三方服务的话，key 去对应服务商那里拿。 | `secret` | 未设置 |
| `OPENAI_COMPATIBLE_MODEL` | 按服务商文档填，例如 gpt-4o、deepseek-chat。 | `text` | 未设置 |
| `OPENAI_COMPATIBLE_FALLBACK_MODELS` | 逗号分隔。主模型不可用时按顺序往下试。 | `csv` | 未设置 |
| `OPENAI_COMPATIBLE_API_MODE` | 大多数服务用 chat-completions。 | `chat-completions, responses` | `chat-completions` |
| `OPENAI_COMPATIBLE_STREAM` | 部分服务只在流式下才肯长时间思考。 | `bool` | `false` |

## 数据源

| 配置键 | 用途及条件 | 类型 / 取值 | 默认值 |
| --- | --- | --- | --- |
| `EXA_API_KEY` | 文档检索能力的两个选项之一。 | `secret` | 未设置 |
| `EXA_BASE_URL` | Exa 地址 | `url` | `https://api.exa.ai` |
| `EXA_TIMEOUT_SECONDS` | Exa 超时（秒） | `float` | `30` |
| `CONTEXT7_API_KEY` | 查开源库文档用。文档检索能力的另一个选项。 | `secret` | 未设置 |
| `CONTEXT7_BASE_URL` | Context7 地址 | `url` | `https://context7.com` |
| `CONTEXT7_TIMEOUT_SECONDS` | Context7 超时（秒） | `float` | `30` |
| `ZHIPU_API_KEY` | 国内时效内容搜得比较好。属于可选增强，不配也能跑。 | `secret` | 未设置 |
| `ZHIPU_API_URL` | 智谱搜索地址 | `url` | `https://open.bigmodel.cn/api` |
| `ZHIPU_SEARCH_ENGINE` | search_std / search_pro / search_pro_sogou / search_pro_quark，或自定义。 | `text` | `search_std` |
| `ZHIPU_TIMEOUT_SECONDS` | 智谱超时（秒） | `float` | `30` |
| `ZHIPU_MCP_API_KEY` | 一个 key 同时提供搜索和网页抓取，抓取那一路可以满足最低配置。 | `secret` | 未设置 |
| `ZHIPU_MCP_SEARCH_API_URL` | 智谱 MCP 搜索地址 | `url` | `https://open.bigmodel.cn/api/mcp/web_search_prime/mcp` |
| `ZHIPU_MCP_READER_API_URL` | 智谱 MCP 阅读地址 | `url` | `https://open.bigmodel.cn/api/mcp/web_reader/mcp` |
| `ZHIPU_MCP_ZREAD_API_URL` | 智谱 MCP zread 地址 | `url` | `https://open.bigmodel.cn/api/mcp/zread/mcp` |
| `ZHIPU_MCP_TIMEOUT_SECONDS` | 智谱 MCP 超时（秒） | `float` | `30` |
| `JINA_API_KEY` | 把网页转成干净正文。注意没有 key 的匿名模式不算满足最低配置。 | `secret` | 未设置 |
| `JINA_READER_API_URL` | Jina Reader 地址 | `url` | `https://r.jina.ai` |
| `JINA_SEARCH_API_URL` | Jina DeepSearch 使用的搜索地址。 | `url` | `https://s.jina.ai` |
| `JINA_RERANK_API_URL` | 需要重排时使用的 Jina 地址。 | `url` | `https://api.jina.ai/v1/rerank` |
| `JINA_RESPOND_WITH` | 可留空。例如 readerlm-v2。 | `text` | 未设置 |
| `JINA_TIMEOUT_SECONDS` | Jina 超时（秒） | `float` | `30` |
| `TAVILY_API_KEY` | 搜索和抓取都能做，一个 key 顶两类能力。 | `secret` | 未设置 |
| `TAVILY_API_URL` | Tavily 地址 | `url` | `https://api.tavily.com` |
| `TAVILY_ENABLED` | 关掉之后即使填了 key 也不会被使用。 | `bool` | `true` |
| `TAVILY_TIMEOUT_SECONDS` | Tavily 超时（秒） | `float` | `30` |
| `FIRECRAWL_API_KEY` | 可选的搜索与抓取渠道。当前仅检查 Key 是否填写，不验证凭据或接口可用性。 | `secret` | 未设置 |
| `FIRECRAWL_API_URL` | Firecrawl 地址 | `url` | `https://api.firecrawl.dev/v2` |
| `TINYFISH_API_KEY` | 一个 Key 支持搜索和网页抓取。测试会各发起一次真实请求。 | `secret` | 未设置 |
| `TINYFISH_SEARCH_API_URL` | TinyFish 搜索地址 | `url` | `https://api.search.tinyfish.ai` |
| `TINYFISH_FETCH_API_URL` | TinyFish 抓取地址 | `url` | `https://api.fetch.tinyfish.ai` |
| `TINYFISH_TIMEOUT_SECONDS` | TinyFish 超时（秒） | `float` | `150` |
| `ANYSEARCH_API_KEY` | 垂直领域搜索，实验性。 | `secret` | 未设置 |
| `ANYSEARCH_API_URL` | AnySearch 地址 | `url` | `https://api.anysearch.com/mcp` |
| `ANYSEARCH_TIMEOUT_SECONDS` | AnySearch 超时（秒） | `float` | `30` |
| `SCIVERSE_API_TOKEN` | 学术论文检索，实验性，只在明确指定时才会被用到。 | `secret` | 未设置 |
| `SCIVERSE_API_URL` | Sciverse 地址 | `url` | `https://api.sciverse.space` |
| `SCIVERSE_TIMEOUT_SECONDS` | Sciverse 超时（秒） | `float` | `30` |

## 意图路由

| 配置键 | 用途及条件 | 类型 / 取值 | 默认值 |
| --- | --- | --- | --- |
| `SMART_SEARCH_INTENT_ROUTER` | jev 按语义选渠道并判断证据，需单独 Key；hybrid 结合规则和模型；rules 只用规则；off 关闭路由。 | `hybrid, jev, off, rules` | `hybrid` |
| `TYPESAFE_API_KEY` | 可选语义路由的独立凭据；填写不会自动切换路由模式。 | `secret` | 未设置 |
| `TYPESAFE_API_URL` | TypeSafe 地址 | `url` | `https://api.typesafe.ai/v1` |
| `TYPESAFE_MODEL` | JEV 模型 | `text` | `jev-latest` |
| `SMART_SEARCH_JEV_TIMEOUT_SECONDS` | JEV 单次判断超时（秒） | `float` | `15` |
| `SMART_SEARCH_JEV_MAX_ROUNDS` | JEV 最多检索轮数 | `int` | `3` |
| `SMART_SEARCH_JEV_MAX_CHANNELS` | JEV 每轮最多渠道数 | `int` | `3` |
| `SMART_SEARCH_JEV_RESULTS_PER_CHANNEL` | JEV 每个渠道结果数 | `int` | `5` |
| `SMART_SEARCH_JEV_ROUTE_THRESHOLD` | JEV 渠道适用概率阈值 | `float` | `0.5` |
| `SMART_SEARCH_JEV_SUFFICIENCY_THRESHOLD` | JEV 证据充分概率阈值 | `float` | `0.75` |
| `SMART_SEARCH_JEV_FILTER_RESULTS` | 会增加判断请求；无法保证总费用减少。 | `bool` | `false` |
| `SMART_SEARCH_JEV_FILTER_THRESHOLD` | JEV 过滤阈值 | `float` | `0.1` |
| `SMART_SEARCH_JEV_SYNTHESIZE` | false 返回证据；auto 按需汇总；true 使用已配置主模型汇总。 | `false, auto, true` | `false` |
| `INTENT_EMBEDDING_API_URL` | 向量接口地址 | `url` | 未设置 |
| `INTENT_EMBEDDING_API_KEY` | 向量接口 Key | `secret` | 未设置 |
| `INTENT_EMBEDDING_MODEL` | 向量模型 | `text` | 未设置 |
| `INTENT_EMBEDDING_THRESHOLD` | 0 到 1 之间。 | `float` | `0.74` |
| `INTENT_EMBEDDING_MARGIN` | 0 到 1 之间。 | `float` | `0.05` |
| `INTENT_CLASSIFIER_API_URL` | 分类模型地址 | `url` | 未设置 |
| `INTENT_CLASSIFIER_API_KEY` | 分类模型 Key | `secret` | 未设置 |
| `INTENT_CLASSIFIER_MODEL` | 分类模型 | `text` | 未设置 |
| `INTENT_ROUTER_TIMEOUT_SECONDS` | 路由超时（秒） | `float` | `8` |
| `SMART_SEARCH_RESEARCH_PREFERRED_PROVIDERS` | 逗号分隔的 provider id，深度研究时优先走这些。 | `csv` | 未设置 |
| `SMART_SEARCH_RESEARCH_DISABLED_PROVIDERS` | 逗号分隔的 provider id，深度研究时完全不走这些。 | `csv` | 未设置 |
| `SMART_SEARCH_DOCUMENT_EMBEDDING_SOURCE` | 选择 intent、OpenAI 兼容接口或关闭文档嵌入。 | `intent, off, openai-compatible` | `intent` |
| `SMART_SEARCH_DOCUMENT_EMBEDDING_DIMENSIONS` | 填 0 使用模型默认维度。 | `int` | `0` |
| `SMART_SEARCH_DOCUMENT_EMBEDDING_NORMALIZE` | 是否对文档向量做归一化。 | `bool` | `true` |
| `SMART_SEARCH_DOCUMENT_SPLITTER` | 可选 markdown 或 character。 | `character, markdown` | `markdown` |
| `SMART_SEARCH_DOCUMENT_CHUNK_SIZE` | 每个文档块的目标字符数。 | `int` | `1600` |

## 超时与兜底

| 配置键 | 用途及条件 | 类型 / 取值 | 默认值 |
| --- | --- | --- | --- |
| `XAI_SOFT_TIMEOUT_SECONDS` | 首次请求多久后开始查询异步状态。 | `float` | `120` |
| `XAI_HARD_TIMEOUT_SECONDS` | 一条 xAI 请求允许占用的最长时间。 | `float` | `7200` |
| `XAI_STATUS_POLL_SECONDS` | 查询异步请求状态的间隔。 | `float` | `15` |
| `SMART_SEARCH_VALIDATION_LEVEL` | strict 查得更严也更慢。 | `balanced, fast, strict` | `balanced` |
| `SMART_SEARCH_FALLBACK_MODE` | auto 会在一个数据源失败后自动换下一个。 | `auto, off` | `auto` |
| `SMART_SEARCH_MINIMUM_PROFILE` | standard 会在三类必需能力缺一时直接报错。关掉之后出问题更难查。 | `off, standard` | `standard` |
| `SMART_SEARCH_TIMEOUT_SECONDS` | 一整条搜索从开始到结束的上限。推理模型慢的时候需要调大。 | `float` | `300` |
| `SMART_SEARCH_PROVIDER_COOLDOWN_SECONDS` | 一个数据源挂了之后多久不再尝试。填 0 关闭冷却。 | `float` | `900` |
| `SMART_SEARCH_PROVIDER_FAILURE_THRESHOLD` | 连续失败几次才冷却。鉴权错误第一次就冷却，不看这个值。 | `int` | `2` |
| `SMART_SEARCH_RETRY_MAX_ATTEMPTS` | 重试次数 | `int` | `3` |
| `SMART_SEARCH_RETRY_MULTIPLIER` | 重试退避倍数 | `float` | `1` |
| `SMART_SEARCH_RETRY_MAX_WAIT` | 重试最长等待（秒） | `int` | `10` |

## 日志与调试

| 配置键 | 用途及条件 | 类型 / 取值 | 默认值 |
| --- | --- | --- | --- |
| `SMART_SEARCH_SIDECAR_PYTHON` | 运行文档解析 Sidecar 的显式 Python 路径。 | `text` | 未设置 |
| `SMART_SEARCH_SIDECAR_TIMEOUT_SECONDS` | 文档 Sidecar 单次操作的最长时间。 | `float` | `120` |
| `SMART_SEARCH_LANGUAGE` | 独立 CLI 的语言偏好；App 界面语言在设置中单独选择。 | `auto, zh, en` | `auto` |
| `SMART_SEARCH_DEBUG` | 调试输出 | `bool` | `false` |
| `SMART_SEARCH_LOG_LEVEL` | 日志级别 | `text` | `INFO` |
| `SMART_SEARCH_LOG_DIR` | 日志目录 | `text` | `logs` |
| `SMART_SEARCH_LOG_TO_FILE` | 写日志文件 | `bool` | `false` |
| `SMART_SEARCH_OUTPUT_CLEANUP` | 清理输出 | `bool` | `true` |
| `SSL_VERIFY` | 关掉只该是临时排查手段。 | `bool` | `true` |
