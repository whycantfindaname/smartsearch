# Maintain Context7 and AnySearch contracts

## Goal

修复 Context7 自动选库错误，并补齐 PR #21 中仍缺失的 AnySearch 参数和抽取行为。

## Requirements

- Context7 auto selection 不使用固定 library id；候选必须与查询主体在 title/id 上有明确词项重合。
- description、trust、benchmark 只用于次级加权；低置信度返回空并回退 Exa。
- 显式 Context7 候选列表和 docs ID 调用保持兼容。
- `--param KEY=VALUE` 可重复，覆盖 JSON 中的同名键；无效参数在网络前失败。
- AnySearch extract 上游 payload 只含 URL，成功内容在本地按正数 max-length 截断。
- README、public skill、packaged skill 和 provider spec 同步。

## Acceptance Criteria

- [ ] React/useEffect 选择 React，React Native 选择细分库，无关高信任候选不胜出。
- [ ] 无主体匹配时 Context7 自动路由回退 Exa。
- [ ] AnySearch precedence、validation、payload、truncation focused tests 通过。
- [ ] AnySearch 可用环境的 domains/search/extract 最小 live probe 通过且无 secret 输出。

## Out Of Scope

- 不改变 Context7/AnySearch capability membership，不启用 Sciverse 默认路由。
