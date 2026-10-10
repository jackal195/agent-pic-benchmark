# Content/KV Reuse 评测工作整理与数据集启示 v0.1

这份笔记把目前资料中的方法按“它们假设什么已经重复”和“它们真正评测了什么”重新整理。它不是论文最终综述；每一项都保留证据等级，避免把宣传材料里的 hit rate 直接当成自然 Agent workload 的复用率。

## 1. 先把问题拆成两层

现有工作大多解决第二层，而本项目必须同时建立第一层：

```text
层 A：真实 workload 中，哪些内容/计算真的再次出现？
      跨独立问题、跨 Agent、跨请求、版本是否兼容、位置能否交换

层 B：给定这些机会，一个方法能安全复用多少？
      命中、重算/修复、质量损失、TTFT、传输和管理成本
```

如果只报告层 B 的 cache hit rate，合成重复请求也能得到很漂亮的数字，却回答不了“真实 Agent 场景是否值得做”。因此数据集的 oracle 标注和方法运行必须分开保存。

## 2. 方法谱系：从固定块到可移动 token span

| 工作/方向 | 复用单位 | 主要突破 | 评测中必须追问 | 证据等级 |
|---|---|---|---|---|
| vLLM/Paged Prefix Cache | 固定 block 的 exact prefix | 工程化前缀复用基线 | 内容换序后是否完全失效；block 大小和 tokenizer | 背景基线 |
| CacheBlend | chunk，配合选择性重算 | non-prefix chunk 的 KV blending | chunk 如何构造；重复是否来自合成相似问题；重算比例和质量 | 资料已核对方向 |
| EPIC | chunk 边界 token | 用边界重算近似跨 chunk 依赖 | 固定 K 是否公平；部分块、长短文档和质量损失 | 资料已核对方向 |
| CacheCraft | chunk 内 token 的注意力选择 | 用注意力决定保留/重算 token | attention 选择开销；是否支持变长 span；是否含自然跨用户轨迹 | 资料已核对方向 |
| Span Query | 表达式树中的 span/子树 | 显式声明哪些连接可交换，支持重排和位置适配 | “可并行”不等于“可换序”；语义许可由谁提供；尾块精度 | 用户附件已核对 |
| CachePrune | 可变长度 token segment | 隐私过滤后的细粒度跨请求分享 | sensitive token、false negative、片段检索和安全泄漏 | arXiv 2605.23640 已核对 |
| TokenDance | 多 Agent 共享中间内容/布局 | 面向协作 Agent 的系统复用 | 共享的是广播内容、system prompt 还是自然检索结果 | 项目先前登记，待逐篇核验 |
| KVCOMM / RelayCaching | Agent 工作流中的 KV 通信/中继 | 跨调用或设备共享 KV | reuse rate 分母、网络字节、端到端时延、质量 | 项目先前登记，待逐篇核验 |
| CacheSlide | 位置/布局适配的缓存 | 在特定训练适配器下扩大可复用范围 | 训练数据、位置适配器成本、SWE 中共享内容是否只是 system prompt | 项目先前登记，待逐篇核验 |
| APE / KVLink / C2KV 等 | 策略、链接或协调层 | 解决 admission、连接、调度或共享管理 | 机制粒度和真正的 reused token；不能只看系统吞吐 | 待逐篇核验 |

这里最重要的变化是：复用单位已经从“文件/固定 chunk”逐渐走向“可变长度 token span”，但安全边界没有消失。一个片段是否能搬到新位置，至少需要单独标注：

```text
exact identity      内容是否逐 token 相同
state compatibility 版本/环境是否仍然有效
position semantics   是否允许换位置
partial-span safety 截取一部分是否会破坏依赖
privacy boundary    是否允许跨 Agent/跨用户共享
```

## 3. 对 Agent 数据集的直接结论

### 3.1 SWE 不能只做文件级

SWE Agent 通常通过 editor view、grep、测试输出看到局部窗口。同一个文件可能出现：

- 同一个函数的不同 line window；
- 同一段代码带不同的行号或工具包装；
- patch 前后同一路径但内容已经变化；
- shell 输出中夹杂动态路径、时间和随机 id。

所以对象层级应为：

```text
repo snapshot → file path → line window → function/class/AST → tokenizer span
```

当前仓库的 OpenHands 导入器已经开始保存 `path`、`view_range`、`observation_kind` 和 `is_mutation`；关系分析也不再把 mutation 事件当作一次读取。但真实 pilot 的旧统计仍然是 path-level，不能写成最终代码级结论。

### 3.2 “出现过”不能代替“进入模型请求”

每个候选内容至少经历三个状态：

```text
存在于 repo/语料库
  → 被工具返回
    → 进入某个模型请求的序列化上下文
```

只有最后一层才是 KV reuse 的直接机会。公开数据若缺少完整序列化请求，只能报告“工具返回层”的上限，并明确标注假设，不能称为真实 KV 命中率。

### 3.3 复用来源必须拆开

同一段内容可能来自完全不同的机制，最终报告至少分为：

1. 同一问题换 Agent；
2. 同一源任务的不同子问题；
3. 不同源任务但共享 repo/知识库；
4. 不同领域的偶然文本重复；
5. 同一对象不同版本，需判定 unchanged 或 invalidated。

第 1 类适合评测多 Agent 协作，第 3 类才是跨独立问题/跨用户机会的较强证据；第 4 类不能未经语义和状态检查就算作可复用。

## 4. 统一评测坐标系

每个 workload、方法和切分都应填下面这张“六轴卡片”：

| 轴 | 最小字段 | 例子 |
|---|---|---|
| 身份 | task/question/agent/request | `task_17`, `coder`, `request_08` |
| 内容 | raw/canonical/structural hash | 带行号文本、去包装代码、函数 AST |
| 版本 | snapshot、patch、content hash | `commit0`、文件未变、对象已失效 |
| 位置 | token span、prefix/interior/suffix | `[820,1260)`、换序后 interior |
| 语义 | exchangeable、order-sensitive、unknown | RAG 文档可换序，代码 patch 上下文通常不可假定可换序 |
| 结果 | quality、TTFT、compute、bytes | exact hit、部分重算、stale reuse、任务成功率 |

### Oracle 指标

- `raw_exact_prefix_tokens`
- `raw_exact_non_prefix_tokens`
- `partial_overlap_tokens`
- `cross_agent_reusable_tokens`
- `cross_source_task_reusable_tokens`
- `invalidated_tokens`
- `unknown_version_tokens`
- `reuse_distance_p50/p90/p99`

### 方法指标

- request/token/block hit rate（分母必须写清）；
- reused token 数与重算 token 数；
- stale reuse / 错误复用率；
- 质量相对 full recompute 的变化；
- TTFT、端到端时延、prefill compute；
- lookup、merge、位置适配、传输和缓存管理开销；
- GPU/CPU/网络字节和峰值内存。

## 5. 评测构造的红线

1. 合成相似问题可以作为压力测试，但必须与自然轨迹分栏；
2. 固定 system prompt 的共享不能冒充跨任务内容复用；
3. 同一个原始任务派生出的多个问题不能直接当作独立用户；
4. 函数名、文件路径或标题相同不能直接推出内容 exact；
5. canonical overlap 只能是潜在机会，不能直接计入 KV exact hit；
6. 只给最终答案的数据集不能作为主要 opportunity benchmark；
7. 公开轨迹缺少时间戳时，不能伪装成真实在线到达顺序；
8. 方法若依赖训练的位置适配器，质量和成本比较必须把训练与适配开销写出来。

## 6. 当前项目的判断

本项目最清晰的研究缺口不是“再做一个 cache hit rate”，而是提供一个方法无关的、可复查的 **Agent reusable-content oracle**：

```text
真实/可重放轨迹
  → 代码/文档/工具输出 span 标注
  → 跨问题、跨 Agent、跨版本机会
  → exchangeability 与 partial-span 安全标签
  → oracle 上限
  → 统一 adapter 下的真实方法收益
```

因此下一阶段的优先级应是：先把 SWE 的 `view_range`、编辑影响范围和 token span 稳定下来，再把同一套 schema 扩展到 BrowseComp/DeepResearch、DeepWiki 和持久状态场景。论文方法表可以并行扩展，但在没有核对原文实验请求和分母前，统一标为“待核验”，不提前填数字。

## 7. OpenHands-SWE-Gym shard 的口径修正结果

对同一份 2,019 条轨迹重新导入后，关系分析只在 observation→observation 之间配对，并排除了 mutation 事件；同时增加了最长连续 token span 和跨 trace 的 task 聚合。结果为：

| 指标 | 修正后结果 | 能说明什么 |
|---|---:|---|
| observation 事件 | 13,630 | 有对象且被视为读取/工具返回的事件 |
| observation 关系 | 36,499 | 关系对数量，不是请求命中率 |
| raw exact 关系 | 6,037（16.54%） | 当前 raw 文本视图下的 exact 关系比例 |
| snapshot 已知且兼容 | 16,586（45.44%） | 仍需按代码 span 进一步拆分 |
| 明确发生对象修改 | 2,237（6.13%） | `observation → mutation → observation` 口径 |
| 状态未知 | 17,676（48.43%） | 主要来自 shell 可能改文件 |
| prefix / non-prefix 关系 | 8,601 / 26,513 | 非前缀机会明显不能被忽略 |
| 跨 task 首次见 proxy | 790 / 6,666（11.85%） | 每个 task 只统计首次引入，使用 JSONL 顺序，非真实时间到达率 |

这组数字仍不是论文最终结果：当前 shard 只有一个 `openhands` Agent，尚不能支持真实跨 Agent 结论；对象 ID 仍以 path 为主，`view_range` 还需要和实际代码内容、函数/AST 及固定模型 tokenizer 对齐。它的作用是证明分析链路的口径正在变得可解释，而不是宣布 SWE 的最终收益。

