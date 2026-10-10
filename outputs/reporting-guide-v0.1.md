# Agent PIC Benchmark 汇报稿 v0.1

## 一句话介绍

我们在做一个面向 Agent 工作流的 PIC/KV reuse benchmark，研究不同 Agent、不同问题和不同请求之间，代码、文档和工具输出何时重复出现，哪些重复内容在版本和位置变化后仍然可以安全复用，以及具体方法能够带来多少真实端到端收益。

## 先讲清楚为什么要做

现有 KV reuse 工作通常从一个已经构造好的重复场景出发，比较不同缓存方法的命中率、TTFT 和质量损失。这样可以评估“方法能不能复用”，但不能回答“真实 Agent workload 中究竟有没有足够多的复用机会”。

现有 LongBench、RULER 和普通 RAG QA 也很少保留 Agent 的完整工具轨迹、对象来源、版本变化和跨 Agent 身份。因此不同论文在 chunk 大小、请求构造、分母和质量指标上不统一，结果很难横向比较。

## 核心问题

对一个独立 Agent task 的每次首次读取，我们问四件事：

1. 其他 task 或 Agent 以前是否见过同一内容？
2. 内容是逐 token 相同、局部重叠，还是只有结构相似？
3. 中间 repository 或环境是否发生修改？
4. 这段内容能否移动到新位置，或需要部分重算和位置适配？

所以数据单位不是最终答案，而是：

```text
task → request → agent/tool/state event → reusable object → reuse relation
```

## 系统设计

```text
真实 Agent 轨迹
      ↓
事件标准化
      ↓
代码/文档/工具输出对象标注
      ↓
版本、位置、跨任务和交换性分析
      ↓
oracle 可复用上限
      ↓
统一方法接口和 trace replay
      ↓
质量、TTFT、计算量、传输量和管理开销
```

## 为什么先做 SWE

SWE 同时包含局部代码读取、grep 和测试输出、patch 修改以及 planner/coder/reviewer 等协作关系。它能检验数据集最容易出错的部分：同一文件的局部窗口、patch 前后版本、动态工具输出和非前缀重叠。

当前第一版从 OpenHands-SWE-Gym trajectory 开始，保留完整原始 message，同时生成统一事件：

- `path` 与 `view_range`；
- `raw_text` 与去除 `cat -n` 包装的 `normalized_text`；
- `source_objects` 与 `source_spans`；
- `snapshot_id`、`state_effect`、`changed_objects`；
- `observation_kind` 与 `is_mutation`。

## 当前已经得到的结果

在 OpenHands-SWE-Gym 第一 shard 的 2,019 条轨迹上，修正为 observation→observation 配对后得到：

| 指标 | 结果 |
|---|---:|
| observation 事件 | 13,630 |
| observation 关系 | 36,499 |
| raw exact 关系 | 6,037（16.54%） |
| snapshot 已知且兼容 | 16,586（45.44%） |
| 明确经历对象修改 | 2,237（6.13%） |
| 状态未知 | 17,676（48.43%） |
| prefix / non-prefix 关系 | 8,601 / 26,513 |

按每个 task 的首次内容引入统计，JSONL 顺序下的跨 task proxy 为 790 / 6,666，即 11.85%。它是机会分析结果，不是实际 KV 命中率，也不是线上用户复用率。

## 现阶段结论

第一，SWE 中存在大量非前缀重叠，prefix-only 方法的理论上限可能明显低于整体复用上限。

第二，path-level 统计会把同一文件的多个窗口混在一起，最终需要下沉到 line window、函数/AST 和 token span。

第三，OpenHands-SWE-Gym 当前 shard 只有一个 Agent，因此它适合验证代码读取、版本修改和跨 task 机会分析，暂时不能作为真实跨 Agent 复用的证据。

第四，公开 trajectory 缺少完整序列化模型请求和真实时间戳，因此当前结果应称为工具返回层的 reuse opportunity proxy。

## 方法比较应该怎么做

后续所有 CacheBlend、EPIC、CacheCraft、Span Query、CachePrune、KVCOMM 等方法统一接入同一套 trace replay，至少报告：

- oracle reusable tokens；
- request、block 和 token hit rate，并写清分母；
- reused、recomputed 和 stale tokens；
- 任务成功率或答案质量；
- TTFT、端到端延迟、prefill compute；
- lookup、merge、位置适配、传输和缓存管理开销。

这样可以区分“场景本来没有复用机会”和“方法没有抓住机会”。

## 汇报时不要说错的三句话

- 不要把 36,499 条 relation 说成 36,499 次 KV 命中。
- 不要把同一路径说成同一段代码，必须结合内容 hash 和 span。
- 不要把 JSONL 顺序下的跨 task proxy 说成真实跨用户复用率。

## 最后怎么收束

我们的目标是建立一个方法无关的 reusable-content oracle，再用统一接口比较不同 PIC/KV 方法的实际收益。当前已经完成 SWE 轨迹导入、事件标准化、mutation 排除、局部 overlap、版本兼容和跨 task 首次引入分析；下一步是接入真实 repository snapshot，生成函数/AST/token span，并运行统一的 KV 方法适配器。
