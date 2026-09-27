[Guide](../README.md) · [简体中文](../zh-CN/configuration-reference.md)

# All configuration keys

Generated from current configuration metadata. All saved keys appear below. See the [configuration guide](configuration.md) for key registration, precedence, runtime environment variables, and the minimum capability profile. Supply your own credentials; unconfigured optional providers are not enabled automatically.

## Start here

| Key | Purpose and conditions | Type / values | Default |
| --- | --- | --- | --- |
| `XAI_API_KEY` | Fill this to use xAI for main search. Either this or the OpenAI-compatible block below is enough. | `secret` | Not set |
| `XAI_API_URL` | Leave it alone unless you go through a proxy or relay. | `url` | `https://api.x.ai/v1` |
| `XAI_MODEL` | Leave empty for the default model. | `text` | `grok-4-fast` |
| `XAI_TOOLS` | Comma separated. web_search and x_search are the supported values. | `web_search, x_search` | `web_search,x_search` |
| `OPENAI_COMPATIBLE_API_URL` | Any OpenAI-protocol service works. Counts as configured only together with the key below. | `url` | Not set |
| `OPENAI_COMPATIBLE_API_KEY` | The link below is OpenAI's own. Using a relay or another provider? Get the key from them instead. | `secret` | Not set |
| `OPENAI_COMPATIBLE_MODEL` | Whatever your provider documents, e.g. gpt-4o or deepseek-chat. | `text` | Not set |
| `OPENAI_COMPATIBLE_FALLBACK_MODELS` | Comma separated. Tried in order when the main model is unavailable. | `csv` | Not set |
| `OPENAI_COMPATIBLE_API_MODE` | Most services want chat-completions. | `chat-completions, responses` | `chat-completions` |
| `OPENAI_COMPATIBLE_STREAM` | Some services only think for long under streaming. | `bool` | `false` |

## Providers

| Key | Purpose and conditions | Type / values | Default |
| --- | --- | --- | --- |
| `EXA_API_KEY` | One of the two options for docs search. | `secret` | Not set |
| `EXA_BASE_URL` | Exa base URL | `url` | `https://api.exa.ai` |
| `EXA_TIMEOUT_SECONDS` | Exa timeout (seconds) | `float` | `30` |
| `CONTEXT7_API_KEY` | Looks up open-source library docs. The other docs-search option. | `secret` | Not set |
| `CONTEXT7_BASE_URL` | Context7 base URL | `url` | `https://context7.com` |
| `CONTEXT7_TIMEOUT_SECONDS` | Context7 timeout (seconds) | `float` | `30` |
| `ZHIPU_API_KEY` | Good at recent Chinese-language content. Optional; things run without it. | `secret` | Not set |
| `ZHIPU_API_URL` | Zhipu Web Search API URL | `url` | `https://open.bigmodel.cn/api` |
| `ZHIPU_SEARCH_ENGINE` | search_std, search_pro, search_pro_sogou, search_pro_quark, or a custom one. | `text` | `search_std` |
| `ZHIPU_TIMEOUT_SECONDS` | Zhipu timeout (seconds) | `float` | `30` |
| `ZHIPU_MCP_API_KEY` | One key serves both search and page fetching; the reader side satisfies the minimum profile. | `secret` | Not set |
| `ZHIPU_MCP_SEARCH_API_URL` | Zhipu Coding Plan search MCP URL | `url` | `https://open.bigmodel.cn/api/mcp/web_search_prime/mcp` |
| `ZHIPU_MCP_READER_API_URL` | Zhipu Coding Plan reader MCP URL | `url` | `https://open.bigmodel.cn/api/mcp/web_reader/mcp` |
| `ZHIPU_MCP_ZREAD_API_URL` | Zhipu Coding Plan zread MCP URL | `url` | `https://open.bigmodel.cn/api/mcp/zread/mcp` |
| `ZHIPU_MCP_TIMEOUT_SECONDS` | Zhipu Coding Plan MCP timeout (seconds) | `float` | `30` |
| `JINA_API_KEY` | Turns a page into clean text. Anonymous use does not satisfy the minimum profile. | `secret` | Not set |
| `JINA_READER_API_URL` | Jina Reader API URL | `url` | `https://r.jina.ai` |
| `JINA_SEARCH_API_URL` | Search endpoint used by Jina DeepSearch. | `url` | `https://s.jina.ai` |
| `JINA_RERANK_API_URL` | Jina endpoint used for reranking. | `url` | `https://api.jina.ai/v1/rerank` |
| `JINA_RESPOND_WITH` | Optional, e.g. readerlm-v2. | `text` | Not set |
| `JINA_TIMEOUT_SECONDS` | Jina timeout (seconds) | `float` | `30` |
| `TAVILY_API_KEY` | Does both search and fetching, so one key covers two capabilities. | `secret` | Not set |
| `TAVILY_API_URL` | Tavily API URL | `url` | `https://api.tavily.com` |
| `TAVILY_ENABLED` | Turning this off makes Tavily unused even with a key saved. | `bool` | `true` |
| `TAVILY_TIMEOUT_SECONDS` | Tavily timeout (seconds) | `float` | `30` |
| `FIRECRAWL_API_KEY` | Optional search and fetch provider. The current check only confirms a key is present, not credential or API availability. | `secret` | Not set |
| `FIRECRAWL_API_URL` | Firecrawl API URL | `url` | `https://api.firecrawl.dev/v2` |
| `TINYFISH_API_KEY` | One key enables search and page fetching. Testing makes one real request for each capability. | `secret` | Not set |
| `TINYFISH_SEARCH_API_URL` | TinyFish search URL | `url` | `https://api.search.tinyfish.ai` |
| `TINYFISH_FETCH_API_URL` | TinyFish fetch URL | `url` | `https://api.fetch.tinyfish.ai` |
| `TINYFISH_TIMEOUT_SECONDS` | TinyFish timeout (seconds) | `float` | `150` |
| `ANYSEARCH_API_KEY` | Vertical-domain search. Experimental. | `secret` | Not set |
| `ANYSEARCH_API_URL` | AnySearch MCP API URL | `url` | `https://api.anysearch.com/mcp` |
| `ANYSEARCH_TIMEOUT_SECONDS` | AnySearch timeout (seconds) | `float` | `30` |
| `SCIVERSE_API_TOKEN` | Academic paper search. Experimental, and only used when asked for explicitly. | `secret` | Not set |
| `SCIVERSE_API_URL` | Sciverse API URL | `url` | `https://api.sciverse.space` |
| `SCIVERSE_TIMEOUT_SECONDS` | Sciverse timeout (seconds) | `float` | `30` |

## Intent routing

| Key | Purpose and conditions | Type / values | Default |
| --- | --- | --- | --- |
| `SMART_SEARCH_INTENT_ROUTER` | jev selects channels and evaluates evidence with its own key; hybrid combines rules and models; rules uses rules only; off disables routing. | `hybrid, jev, off, rules` | `hybrid` |
| `TYPESAFE_API_KEY` | Separate credentials for optional semantic routing; adding a key does not switch modes. | `secret` | Not set |
| `TYPESAFE_API_URL` | TypeSafe API URL | `url` | `https://api.typesafe.ai/v1` |
| `TYPESAFE_MODEL` | JEV model | `text` | `jev-latest` |
| `SMART_SEARCH_JEV_TIMEOUT_SECONDS` | JEV judgment timeout (seconds) | `float` | `15` |
| `SMART_SEARCH_JEV_MAX_ROUNDS` | JEV maximum retrieval rounds | `int` | `3` |
| `SMART_SEARCH_JEV_MAX_CHANNELS` | JEV channels per round | `int` | `3` |
| `SMART_SEARCH_JEV_RESULTS_PER_CHANNEL` | JEV results per channel | `int` | `5` |
| `SMART_SEARCH_JEV_ROUTE_THRESHOLD` | JEV channel suitability threshold | `float` | `0.5` |
| `SMART_SEARCH_JEV_SUFFICIENCY_THRESHOLD` | JEV evidence sufficiency threshold | `float` | `0.75` |
| `SMART_SEARCH_JEV_FILTER_RESULTS` | Adds judgment calls; overall cost savings are not guaranteed. | `bool` | `false` |
| `SMART_SEARCH_JEV_FILTER_THRESHOLD` | JEV filtering threshold | `float` | `0.1` |
| `SMART_SEARCH_JEV_SYNTHESIZE` | false returns evidence; auto decides whether to summarize; true uses the configured main model. | `false, auto, true` | `false` |
| `INTENT_EMBEDDING_API_URL` | Intent embedding API URL | `url` | Not set |
| `INTENT_EMBEDDING_API_KEY` | Intent embedding API key | `secret` | Not set |
| `INTENT_EMBEDDING_MODEL` | Intent embedding model | `text` | Not set |
| `INTENT_EMBEDDING_THRESHOLD` | Between 0 and 1. | `float` | `0.74` |
| `INTENT_EMBEDDING_MARGIN` | Between 0 and 1. | `float` | `0.05` |
| `INTENT_CLASSIFIER_API_URL` | Intent classifier API URL | `url` | Not set |
| `INTENT_CLASSIFIER_API_KEY` | Intent classifier API key | `secret` | Not set |
| `INTENT_CLASSIFIER_MODEL` | Intent classifier model | `text` | Not set |
| `INTENT_ROUTER_TIMEOUT_SECONDS` | Intent router timeout (seconds) | `float` | `8` |
| `SMART_SEARCH_RESEARCH_PREFERRED_PROVIDERS` | Comma-separated provider ids to prefer during deep research. | `csv` | Not set |
| `SMART_SEARCH_RESEARCH_DISABLED_PROVIDERS` | Comma-separated provider ids to keep out of deep research entirely. | `csv` | Not set |
| `SMART_SEARCH_DOCUMENT_EMBEDDING_SOURCE` | Use intent, an OpenAI-compatible endpoint, or disable document embeddings. | `intent, off, openai-compatible` | `intent` |
| `SMART_SEARCH_DOCUMENT_EMBEDDING_DIMENSIONS` | Use 0 to keep the model's default dimensions. | `int` | `0` |
| `SMART_SEARCH_DOCUMENT_EMBEDDING_NORMALIZE` | Whether to normalize document vectors. | `bool` | `true` |
| `SMART_SEARCH_DOCUMENT_SPLITTER` | Choose markdown or character splitting. | `character, markdown` | `markdown` |
| `SMART_SEARCH_DOCUMENT_CHUNK_SIZE` | Target character count for each document chunk. | `int` | `1600` |

## Timeouts and fallback

| Key | Purpose and conditions | Type / values | Default |
| --- | --- | --- | --- |
| `XAI_SOFT_TIMEOUT_SECONDS` | When to start checking the asynchronous request status. | `float` | `120` |
| `XAI_HARD_TIMEOUT_SECONDS` | Maximum time allowed for one xAI request. | `float` | `7200` |
| `XAI_STATUS_POLL_SECONDS` | Interval between asynchronous request status checks. | `float` | `15` |
| `SMART_SEARCH_VALIDATION_LEVEL` | strict checks harder and runs slower. | `balanced, fast, strict` | `balanced` |
| `SMART_SEARCH_FALLBACK_MODE` | auto moves on to the next provider when one fails. | `auto, off` | `auto` |
| `SMART_SEARCH_MINIMUM_PROFILE` | standard refuses to run when any of the three required capabilities is missing. | `off, standard` | `standard` |
| `SMART_SEARCH_TIMEOUT_SECONDS` | Ceiling for one whole search. Raise it when a reasoning model is slow. | `float` | `300` |
| `SMART_SEARCH_PROVIDER_COOLDOWN_SECONDS` | How long a failing provider is skipped. 0 disables cooldown. | `float` | `900` |
| `SMART_SEARCH_PROVIDER_FAILURE_THRESHOLD` | Consecutive soft failures before cooldown. Auth errors cool down on the first one regardless. | `int` | `2` |
| `SMART_SEARCH_RETRY_MAX_ATTEMPTS` | Retry max attempts | `int` | `3` |
| `SMART_SEARCH_RETRY_MULTIPLIER` | Retry backoff multiplier | `float` | `1` |
| `SMART_SEARCH_RETRY_MAX_WAIT` | Retry max wait (seconds) | `int` | `10` |

## Logging and debugging

| Key | Purpose and conditions | Type / values | Default |
| --- | --- | --- | --- |
| `SMART_SEARCH_SIDECAR_PYTHON` | Explicit Python executable for the document sidecar. | `text` | Not set |
| `SMART_SEARCH_SIDECAR_TIMEOUT_SECONDS` | Maximum time for one document sidecar operation. | `float` | `120` |
| `SMART_SEARCH_LANGUAGE` | Language for the independent CLI. Choose the App language separately in its settings. | `auto, zh, en` | `auto` |
| `SMART_SEARCH_DEBUG` | Debug output | `bool` | `false` |
| `SMART_SEARCH_LOG_LEVEL` | Log level | `text` | `INFO` |
| `SMART_SEARCH_LOG_DIR` | Log directory | `text` | `logs` |
| `SMART_SEARCH_LOG_TO_FILE` | Log to file | `bool` | `false` |
| `SMART_SEARCH_OUTPUT_CLEANUP` | Clean up output | `bool` | `true` |
| `SSL_VERIFY` | Turning this off should only ever be a temporary debugging step. | `bool` | `true` |
