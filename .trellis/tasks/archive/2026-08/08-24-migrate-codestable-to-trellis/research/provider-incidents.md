# Provider Incident History

These records preserve dated causes and fix boundaries. They do not establish
current credentials, entitlement, remote availability, or upstream schemas.
The current provider contract and current code/tests remain authoritative.

## 2026-07-06: Zhipu Coding Plan MCP session failure (#17)

### Failure and cause

Zhipu search, reader, and zread requests were sent directly as JSON-RPC
`tools/call` with authorization but without an MCP session. The Coding Plan
streamable-HTTP endpoints required this sequence:

1. send JSON-RPC `initialize` to the selected endpoint;
2. read `Mcp-Session-Id` from the response header;
3. include that header on subsequent `tools/call` requests.

Without the handshake, the remote endpoint returned an `AUTH_ERROR -401`-style
failure even though the issue report's comparison showed the same key working
after initialization. Sources: [issue report](https://github.com/whycantfindaname/smartsearch/blob/020b4dc904e2b19643aeece0c00b25d011eb1fc5/.codestable/issues/2026-07-06-gh-17-zhipu-mcp-session/gh-17-zhipu-mcp-session-report.md)
and [root-cause analysis](https://github.com/whycantfindaname/smartsearch/blob/020b4dc904e2b19643aeece0c00b25d011eb1fc5/.codestable/issues/2026-07-06-gh-17-zhipu-mcp-session/gh-17-zhipu-mcp-session-analysis.md).

### Fix boundary

The fix stayed inside `ZhipuMCPProvider`: initialize lazily per provider
instance, cache the returned session id for that instance, attach it to tool
calls, and preserve masked auth/provider errors. It intentionally did not add a
generic MCP framework, a service-global session cache, a CLI/config change, or
any merger between Zhipu REST and Zhipu Coding Plan MCP. Sources:
[analysis options](https://github.com/whycantfindaname/smartsearch/blob/020b4dc904e2b19643aeece0c00b25d011eb1fc5/.codestable/issues/2026-07-06-gh-17-zhipu-mcp-session/gh-17-zhipu-mcp-session-analysis.md)
and [fix note](https://github.com/whycantfindaname/smartsearch/blob/020b4dc904e2b19643aeece0c00b25d011eb1fc5/.codestable/issues/2026-07-06-gh-17-zhipu-mcp-session/gh-17-zhipu-mcp-session-fix-note.md).

Mock HTTP tests reported that search, reader, and zread all performed
`initialize` before `tools/call` and sent `Mcp-Session-Id`. No real
`ZHIPU_MCP_API_KEY` was configured for the 2026-07-06 run, so the remote live
path remained unverified. Sources: [fix verification](https://github.com/whycantfindaname/smartsearch/blob/020b4dc904e2b19643aeece0c00b25d011eb1fc5/.codestable/issues/2026-07-06-gh-17-zhipu-mcp-session/gh-17-zhipu-mcp-session-fix-note.md)
and [review residual risk](https://github.com/whycantfindaname/smartsearch/blob/020b4dc904e2b19643aeece0c00b25d011eb1fc5/.codestable/issues/2026-07-06-gh-17-zhipu-mcp-session/gh-17-zhipu-mcp-session-review.md).

## 2026-07-06: AnySearch and Context7 contract drift (#19)

### Failure and cause

The local adapter, tests, README, and Skill copies had frozen old external
contracts:

- AnySearch domain discovery still called removed tool `list_domains`; the
  live tool set exposed `get_sub_domains`.
- The old `security.cve` shorthand omitted the current `sub_domain_params`
  structure needed for CVE search.
- Context7 examples used stale React id `/facebook/react`, while automatic
  docs routing blindly selected the first library candidate and could choose an
  unrelated result.

The root cause was external data-contract drift amplified by local tests and
published examples that encoded the stale contract. Sources: [issue report](https://github.com/whycantfindaname/smartsearch/blob/020b4dc904e2b19643aeece0c00b25d011eb1fc5/.codestable/issues/2026-07-06-gh-19-provider-contract-drift/gh-19-provider-contract-drift-report.md)
and [root-cause analysis](https://github.com/whycantfindaname/smartsearch/blob/020b4dc904e2b19643aeece0c00b25d011eb1fc5/.codestable/issues/2026-07-06-gh-19-provider-contract-drift/gh-19-provider-contract-drift-analysis.md).

### Fix boundary

The scoped repair replaced domain discovery with `get_sub_domains`, added
structured AnySearch parameter passthrough, updated examples, and made Context7
candidate selection require query-subject overlap in title/id before secondary
trust or benchmark scoring. A review follow-up prevented a preferred React id
from outranking a more specific React-family match such as React Native. The
repair did not introduce a schema-driven generic MCP layer. Sources:
[fix note](https://github.com/whycantfindaname/smartsearch/blob/020b4dc904e2b19643aeece0c00b25d011eb1fc5/.codestable/issues/2026-07-06-gh-19-provider-contract-drift/gh-19-provider-contract-drift-fix-note.md)
and [review](https://github.com/whycantfindaname/smartsearch/blob/020b4dc904e2b19643aeece0c00b25d011eb1fc5/.codestable/issues/2026-07-06-gh-19-provider-contract-drift/gh-19-provider-contract-drift-review.md).

The 2026-07-06 record reported successful local and live probes for the then
current AnySearch and Context7 contracts. Those probes are historical only;
external tool schemas, library ids, credentials, and reachability can drift
again. Source: [dated fix verification](https://github.com/whycantfindaname/smartsearch/blob/020b4dc904e2b19643aeece0c00b25d011eb1fc5/.codestable/issues/2026-07-06-gh-19-provider-contract-drift/gh-19-provider-contract-drift-fix-note.md).

### Superseded and current boundary

The incident's AnySearch provider/CLI implementation is no longer the current
architecture. AnySearch is now an external Skill selected and invoked by the
agent; it is not registered inside Smart Search and must not enter provider
fallback. The historical drift remains useful as a warning to discover and
validate external contracts instead of freezing undocumented assumptions.
Source for the superseded topology: [#19 analysis](https://github.com/whycantfindaname/smartsearch/blob/020b4dc904e2b19643aeece0c00b25d011eb1fc5/.codestable/issues/2026-07-06-gh-19-provider-contract-drift/gh-19-provider-contract-drift-analysis.md).
