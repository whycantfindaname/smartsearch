---
doc_type: feature-qa
feature: 2026-07-06-sciverse-academic-provider
status: passed
tested: 2026-07-06
round: 1
---

# sciverse-academic-provider QA 报告

## 1. Scope And Inputs

- Design: `.codestable/features/2026-07-06-sciverse-academic-provider/sciverse-academic-provider-design.md`
- Checklist: `.codestable/features/2026-07-06-sciverse-academic-provider/sciverse-academic-provider-checklist.yaml`
- Review: `.codestable/features/2026-07-06-sciverse-academic-provider/sciverse-academic-provider-review.md`
- Evidence pack: none
- Gate results: none
- DoD results: none
- Diff basis: `git status --short` 显示本 feature 的 provider、config、service、CLI、测试、README、provider contract、public skill、packaged skill 和 CodeStable 产物改动；`git diff --stat` 显示 22 个 tracked 文件改动，另有本 feature untracked 文件。
- Baseline dirty files: 当前 dirty/untracked 文件均属于本 Sciverse feature 或其 requirement/design 产物；未发现本轮范围外 dirty 文件。
- Feature type: functional
- Core evidence gate: Sciverse 显式命令、provider HTTP adapter、service/capability 诊断、默认路由反向约束、错误映射、secret masking 和文档同步均需运行证据；真实 Sciverse live smoke 因当前环境 `SCIVERSE_API_TOKEN=not_configured` 按 design 预设作为 supporting skip，不阻塞。

## 2. Verification Matrix

| ID | 来源 | 核心性 | 场景 / 风险 | 证据类型 | 命令或动作 | 期望 | 结果 |
|---|---|---|---|---|---|---|---|
| QA-001 | design CMD-001 | core-functional | Python 语法和 import 基线 | compile | `.\.venv\Scripts\python.exe -m compileall -q src tests` | exit 0 | pass |
| QA-002 | design CMD-002 | core-functional | provider/service/CLI/smoke focused 回归覆盖 catalog/search/semantic/read/relations、参数上限、错误映射、默认路由 | test | `.\.venv\Scripts\python.exe -m pytest tests\test_sciverse_provider.py tests\test_service.py tests\test_cli.py tests\test_smoke.py -q` | 全部通过 | pass |
| QA-003 | design CMD-003 | core-functional | source checkout regression 不破坏既有 provider 架构 | regression | `.\.venv\Scripts\python.exe -m smart_search.cli regression` | 全部通过 | pass |
| QA-004 | design CMD-004 | core-functional | mock smoke 中 standard minimum profile 与 provider routing 仍可用；Sciverse 只在 explicit-only 列表 | smoke | `.\.venv\Scripts\python.exe -m smart_search.cli smoke --mock --format json` | `ok=true`，`vertical_search.explicit_only=["sciverse"]`，默认 provider attempts 无 sciverse | pass |
| QA-005 | design CMD-005 | core-functional | diff hygiene | diff | `git diff --check` | 无 whitespace error | pass |
| QA-006 | design S1 / review focus | core-functional | 未配置 token 时显式命令返回 `config_error`，不把缺 token 伪装成 provider/network 错误 | CLI | `.\.venv\Scripts\python.exe -m smart_search.cli sciverse-catalog --format json` | exit 3，`ok=false`，`error_type=config_error` | pass |
| QA-007 | design S2-S7 | core-functional | catalog/search/semantic/read/relations happy path 与 payload/response 归一化 | unit + CLI test | QA-002 | 输出包含 provider/tool/结果字段，引用关系方向清楚 | pass |
| QA-008 | design S4/S8 | core-functional | JSON 逃生舱和参数上限本地校验 | unit + CLI test | QA-002 | 非法 JSON/越界参数为 `parameter_error`，不调用 provider | pass |
| QA-009 | design S9 / review focus | core-functional | auth/parameter/rate-limit/timeout/network/provider/parse 错误映射和 CLI exit taxonomy | unit + CLI test | QA-002 | 错误类型按契约归一，config/auth exit 3，网络类 exit 4 | pass |
| QA-010 | design S10-S11 / review focus | core-functional | standard minimum profile 与默认 search/research 路由不变 | service + smoke | QA-002 + QA-004 | `required == ["main_search","docs_search","web_fetch"]`；默认 attempts 不出现 `sciverse` | pass |
| QA-011 | design S12 | core-functional | README、中文 README、public skill、packaged skill、provider contract 同步 Sciverse experimental explicit-only 边界 | regression + diff review | QA-003 + diff review | 文档未把 Sciverse 写成 docs_search 或 standard provider | pass |
| QA-012 | design security / review focus | core-functional | 不泄露真实 token 或 token-like 字符串 | secret scan | `$hits = @(rg --pcre2 -l "[0-9a-f]{32}\.[A-Za-z0-9]{16}" 2>$null); "secret_like_hits=$($hits.Count)"` | `secret_like_hits=0` | pass |
| QA-013 | design CMD-006 | supporting | 真实 Sciverse catalog live smoke | API | `.\.venv\Scripts\python.exe -m smart_search.cli sciverse-catalog --format json` with real `SCIVERSE_API_TOKEN` | 有 token 时记录脱敏响应摘要 | skipped: 当前 token 未配置，design 允许 supporting skip |

## 3. Command Results

- `.\.venv\Scripts\python.exe -m compileall -q src tests` -> exit 0：无输出，语法/import 基线通过。
- `.\.venv\Scripts\python.exe -m pytest tests\test_sciverse_provider.py tests\test_service.py tests\test_cli.py tests\test_smoke.py -q` -> exit 0：`232 passed in 5.45s`。
- `.\.venv\Scripts\python.exe -m smart_search.cli regression` -> exit 0：`256 passed in 4.83s`。
- `.\.venv\Scripts\python.exe -m smart_search.cli smoke --mock --format json` -> exit 0：`ok=true`，`failed_cases=[]`；capability status 中 `vertical_search.explicit_only=["sciverse"]`、`route_enabled.sciverse=false`。
- `git diff --check` -> exit 0：只有 LF/CRLF 工作区警告，无 whitespace error。
- `.\.venv\Scripts\python.exe -m smart_search.cli sciverse-catalog --format json` -> exit 3：返回 `ok=false`、`provider=sciverse`、`tool=list_catalog`、`error_type=config_error`、错误文本为 `SCIVERSE_API_TOKEN is not configured`。
- `$hits = @(rg --pcre2 -l "[0-9a-f]{32}\.[A-Za-z0-9]{16}" 2>$null); "secret_like_hits=$($hits.Count)"` -> exit 0：`secret_like_hits=0`。
- 未运行：带真实 token 的 live catalog/search/semantic/read/relations 链路 -> 当前环境 `SCIVERSE_API_TOKEN=not_configured`；该项在 design 中是 supporting gate，不阻塞 QA。

## 4. Scenario Results

- [x] QA-001 编译/import 基线：pass
  - Evidence: compileall exit 0。
  - Notes: 无既有红灯。
- [x] QA-002 focused provider/service/CLI/smoke 回归：pass
  - Evidence: `232 passed`。
  - Notes: 覆盖 Sciverse provider public methods、token 缺失、Bearer header、schema drift、参数上限、service profile、CLI dispatch 和 smoke。
- [x] QA-003 source checkout regression：pass
  - Evidence: `256 passed`。
  - Notes: 既有 provider、router、release workflow 回归未破坏。
- [x] QA-004 mock smoke：pass
  - Evidence: `ok=true`、`failed_cases=[]`，`vertical_search.explicit_only=["sciverse"]`。
  - Notes: Sciverse 未进入默认 route，符合 explicit-only 边界。
- [x] QA-005 diff hygiene：pass
  - Evidence: `git diff --check` 无 whitespace error。
  - Notes: LF/CRLF 警告为 Windows 工作区换行提示，不是 diff 错误。
- [x] QA-006 no-token 显式命令：pass
  - Evidence: `sciverse-catalog` 返回 `config_error`，PowerShell `$LASTEXITCODE=3`。
  - Notes: 证明当前无 token 时错误语义清楚；未宣称 live 可用。
- [x] QA-007 catalog/search/semantic/read/relations happy path：pass
  - Evidence: provider/CLI focused tests in QA-002。
  - Notes: mock 证据覆盖 normalized output 和关系方向枚举。
- [x] QA-008 JSON 逃生舱和参数上限：pass
  - Evidence: focused tests in QA-002。
  - Notes: 非法 JSON 与越界参数在本地拦截。
- [x] QA-009 错误映射和 exit taxonomy：pass
  - Evidence: focused tests in QA-002；no-token CLI 手工命令 exit 3。
  - Notes: review 第三轮指出的 schema/exit 问题已被复测覆盖。
- [x] QA-010 standard/default routing 不变：pass
  - Evidence: service tests + mock smoke。
  - Notes: `vertical_search` 中 Sciverse 是 explicit-only，不满足 standard minimum profile，也不进入默认 attempts。
- [x] QA-011 文档和 skill 同步：pass
  - Evidence: regression marker tests + diff review。
  - Notes: README、中文 README、public skill、packaged skill、provider contract 均标注 experimental explicit-only。
- [x] QA-012 secret scan：pass
  - Evidence: `secret_like_hits=0`。
  - Notes: 未发现用户曾贴过的 token-like 形态落入仓库文件。
- [x] QA-013 live smoke：skipped supporting
  - Evidence: `SCIVERSE_API_TOKEN=not_configured`。
  - Notes: 当前只能证明本地契约和 no-token 行为；真实远端授权/字段可用性留作非阻塞 residual risk。

## 5. Findings

### failed

none

### blocked

none

### residual-risk

- 真实 Sciverse live smoke 未执行，因为当前环境没有 `SCIVERSE_API_TOKEN`。design 已把它定义为 supporting gate；mock/provider/CLI/service/regression 证据已覆盖本地 blocking contract。
- OCR CLI 不可用，行级 OCR 扫描未执行；code review 已用 independent subagent 三轮审查放行。

## 6. Cleanliness

- Debug output: pass
- Temporary TODO/FIXME/XXX: pass
- Commented-out code: pass
- Unused imports / dead code from this feature: pass
- Out-of-scope files: pass
- Secrets: pass (`secret_like_hits=0`)

## 7. Verdict

- Status: passed
- Next: `cs-feat-accept`
