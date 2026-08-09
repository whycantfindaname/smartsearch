# Design

- Full-scope check 覆盖所有受影响 provider、CLI、docs、skills、workflows 和 package metadata。
- Live evidence 只记录 provider/status/error_type/elapsed 等脱敏字段。
- Beta 与 stable 分层：先 beta exact install evidence，再请求 merge/tag/stable 授权。
