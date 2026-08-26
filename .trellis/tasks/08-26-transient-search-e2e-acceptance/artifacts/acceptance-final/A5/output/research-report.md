# 截至 2026-08-26 的 Apple Mac mini 与 Mac Studio 官方比较

## 结论

截至 2026-08-26，Apple 最新 Mac mini 于 2026-08-25 发布，提供 M6 与 M5 Pro；最新 Mac Studio 同日发布，提供 M5 Max 与 M5 Ultra。Mac mini 以更小机身、较低美国起售价和最多三台外接显示器覆盖通用桌面、专业工作室及常驻式本地 AI 场景；Mac Studio 以更高内存上限、更多 Thunderbolt 5、最多八台外接显示器和明显更高的美国起售价面向本地 AI 与极高负载的专业工作流。[1][2][3][4]

若核心约束是体积、成本或普通到中高强度专业工作，Mac mini 是直接匹配；若工作负载需要 128GB 以上统一内存、五至八台显示器、更多高速扩展或 M5 Ultra，Mac Studio 才提供相应能力。[1][2][3][4]

## 范围与方法

本报告比较截至 2026-08-26 Apple 官方页面所列的最新 Mac mini 与 Mac Studio，字段限定为 announcement date、chip、unified memory、I/O、display support、dimensions、带地区标签的 pricing 和 Apple 的 product positioning。研究先用一次 Smart Search `search` 定位 Apple 官方候选页，再依次对 Mac mini Newsroom、Mac mini technical specifications、Mac Studio Newsroom 和 Mac Studio technical specifications 的已知 URL 执行标准 `fetch`。搜索结果与摘要只用于定位；表格和结论仅使用实际打开且通过质量检查的四个 Apple 直接来源。

本文使用 `verified` 表示已经打开直接来源并核对对象、字段与正文；`unverified` 表示只有线索但未读原文；`missing` 表示没有支持当前主张的证据。产品定位按 Apple 的原文意图概括，属于厂商定位，不是独立性能评测。

## 关键发现

| 比较字段 | Mac mini | Mac Studio |
| --- | --- | --- |
| Announcement date | 2026-08-25。[1] | 2026-08-25。[3] |
| Chip | M6；M5 Pro 可选最高 18-core CPU、20-core GPU。[1][2] | M5 Max 可选最高 18-core CPU、40-core GPU；M5 Ultra 可选最高 36-core CPU、80-core GPU。[3][4] |
| Unified memory | M6 各配置从 16GB 或 24GB 起，最高 32GB；M5 Pro 从 24GB 起，最高 64GB。[2] | M5 Max 从 36GB 起，最高 128GB；M5 Ultra 从 96GB 起，最高 512GB，512GB 需要最高配 M5 Ultra。[4] |
| I/O | 前置两个 USB-C（USB 3，最高 10Gb/s）与 3.5mm 耳机孔；后置三个 Thunderbolt 4（M6）或 Thunderbolt 5（M5 Pro）、HDMI、2.5Gb Ethernet，可选 10Gb Ethernet。[2] | 后置四个 Thunderbolt 5、两个 USB-A、HDMI 2.1、10Gb Ethernet 与 3.5mm 耳机孔；前置两个 USB-C（M5 Max）或两个 Thunderbolt 5（M5 Ultra），并有 SDXC UHS-II 卡槽。[4] |
| Display support | M6 与 M5 Pro 均最多支持三台外接显示器；最高分辨率组合因芯片、端口和刷新率而异，单屏路线可达 8K 60Hz。[2] | M5 Max 最多支持五台、M5 Ultra 最多支持八台外接显示器；两者均支持单屏路线最高 8K 60Hz，具体组合受显示器数量与刷新率约束。[4] |
| Dimensions | 高 5.0cm，宽 12.7cm，深 12.7cm；M6 重 0.67kg，M5 Pro 重 0.73kg。[2] | 高 9.5cm，宽 19.7cm，深 19.7cm；M5 Max 重 2.7kg，M5 Ultra 重 3.6kg。[4] |
| Pricing（美国，Apple 标注为 “U.S.”） | M6 起价 US$899；M5 Pro 起价 US$1,699。教育价未纳入主比较。[1] | M5 Max 起价 US$2,499；M5 Ultra 起价 US$5,499。教育价与租赁价未纳入主比较。[3] |
| Product positioning | Apple 将其定位为可用于家庭、专业工作室和常驻式 agentic computing 的多用途超紧凑桌面；M5 Pro 面向更复杂的专业工作流。[1] | Apple 将其定位为面向 on-device AI 与最极端专业工作流的高性能专业桌面，目标用户包括创作者、开发者、AI 研究者和数据科学家。[3] |

Mac Studio 的主要差异不只来自芯片名称。它将统一内存上限从 Mac mini 的 64GB 提高到 512GB，将最大外接显示器数量从三台提高到八台，并提供 10Gb Ethernet、后置四个 Thunderbolt 5 以及 Ultra 机型前置两个 Thunderbolt 5；这些能力直接服务大型本地模型、多显示器和高速扩展场景。[2][4]

Mac mini 的决定性优势是紧凑尺寸与较低进入价格：体积为 12.7cm × 12.7cm × 5.0cm，美国 M6 起价 US$899；Mac Studio 为 19.7cm × 19.7cm × 9.5cm，美国 M5 Max 起价 US$2,499。[1][2][3][4]

## 来源核验与证据状态

| 来源 | 类型 | 状态 | 可回读 locator | 支持范围 |
| --- | --- | --- | --- | --- |
| Apple Mac mini Newsroom [1] | Apple 官方新闻稿 | `verified` | 页面顶部日期；“Mac mini with the All-New M6”；“Mac mini with M5 Pro”；“Best-in-Class Connectivity”；“Pricing and Availability” | 发布日期、芯片、部分内存与连接性、美国定价、产品定位 |
| Apple Mac mini Technical Specifications [2] | Apple 官方规格页 | `verified` | “Chip”；“Memory”；“Display Support”；“Connections and Expansion”；“Size and Weight” | 芯片配置、统一内存、I/O、显示支持、尺寸与重量 |
| Apple Mac Studio Newsroom [3] | Apple 官方新闻稿 | `verified` | 页面顶部日期；“Mac Studio with M5 Max”；“Mac Studio with M5 Ultra”；“Blazing-Fast Storage and Pro Connectivity”；“Pricing and Availability” | 发布日期、芯片、部分内存与连接性、美国定价、产品定位 |
| Apple Mac Studio Technical Specifications [4] | Apple 官方规格页 | `verified` | “Chip”；“Memory”；“Display Support”；“Connections and Expansion”；“Size and Weight” | 芯片配置、统一内存、I/O、显示支持、尺寸与重量 |

未将 discovery 搜索摘要列为证据，也未将任何质量门失败的页面内容纳入引用。四类要求来源均至少有一个 `verified` 直接来源。

## 限制

价格只核验到 Apple 新闻稿明确标注的美国起售价；本报告用 `US$` 表示该美国美元价格语境。其他地区价格、税费、实时商店配置价和供货状态未核验，证据状态为 `missing`，因此不作跨地区价格比较。[1][3]

技术规格页是截至核验时的动态官方页面，而新闻稿固定于 2026-08-25；后续配置或价格变化会使本报告过时。显示支持行压缩了多种分辨率、刷新率和端口组合，采购前应按目标显示器组合回读规格页的完整 “Display Support” 段落。[2][4]

本报告比较厂商公布的规格与定位，没有执行独立 benchmark、噪声、功耗或实际应用性能测试；因此不把 Apple 的性能宣传外推为独立测量结论。

## 观察到的错误与恢复附录

四个 Apple 已知 URL 的标准 `fetch` 均完成了内建同能力链：首个 provider 返回公开错误类型 `quality_error`，原因是低质量挑战页；后续 provider 返回 `empty`。这些内容全部被排除。根据 active Smart Search Skill 的 error-recovery 目录，在每个 URL 的标准链耗尽后，各执行一次明确允许的 `anysearch-extract` 兼容路线；四次均返回 `ok: true` 且正文与目标 Apple 页面、标题和所需章节一致，因而用于直接来源核验。

没有结果包含要求运行诊断探针的 structured recovery 对象，因此 `doctor` 调用次数为 0。没有原样重复失败命令，没有 Agent、shell 或脚本级外层重试，也没有使用原生 web、浏览器或其他网络路径。

## References

1. Apple. [Apple’s new Mac mini, featuring M6 and M5 Pro, delivers a massive leap in AI performance, supercharging the leading desktop for always-on agentic computing](https://www.apple.com/newsroom/2026/08/apple-unveils-a-more-powerful-mac-mini-featuring-the-all-new-m6-and-m5-pro/). Newsroom, 2026-08-25. Accessed 2026-08-26.
2. Apple. [Mac mini — Technical Specifications](https://www.apple.com/mac-mini/specs/). Accessed 2026-08-26.
3. Apple. [Apple introduces new Mac Studio with M5 Max and M5 Ultra — the ultimate desktop for on-device AI and the most extreme pro workflows](https://www.apple.com/newsroom/2026/08/apple-introduces-new-mac-studio-with-m5-max-and-m5-ultra/). Newsroom, 2026-08-25. Accessed 2026-08-26.
4. Apple. [Mac Studio — Technical Specifications](https://www.apple.com/mac-studio/specs/). Accessed 2026-08-26.

## Execution Summary

- **Status:** Complete；四类要求的 Apple 直接来源均已打开并达到 `verified`，研究问题全部覆盖。
- **Actions & Changes:** 执行一次官方来源定位搜索、四次标准 fetch 与四次目录允许的兼容提取；仅生成本报告与结构化结果。
- **Verification & Findings:** 搜索成功；四次标准 fetch 均记录 `quality_error` 后接 `empty`；四次兼容提取均 `ok: true`；`doctor` 调用 0 次。
- **Deviations & Risks:** 标准 fetch 未产生可引用正文，按错误目录切换到显式兼容路线；非美国价格与动态商店价格保持证据缺口。
- **Commands & Artifacts:** 命令 JSON 保存在 `output/commands/`；机器结果保存在 `output/run-result.json`。
