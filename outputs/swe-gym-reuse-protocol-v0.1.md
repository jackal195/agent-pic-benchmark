# SWE-Gym Reuse Opportunity Analysis Protocol v0.1

## 1. 目标

测量 repo-based Agent 轨迹中真实可复用的上下文、代码级潜在复用和 patch 导致的缓存失效，并区分它们对 PIC/KV reuse 的不同意义。

## 2. 事件解析

将每条轨迹解析为：

- issue/task 描述；
- Agent prompt 和 response；
- 文件读取窗口；
- grep/search 结果；
- test/build/lint 输出；
- patch/edit 操作；
- git diff 和 snapshot 更新；
- reviewer 或其他 Agent 的复核事件。

每个事件都绑定 `repo_id`、`snapshot_id`、`agent_id`、`event_index`。

## 3. 代码对象识别

### 3.1 Raw 对象

记录 Agent 实际收到的完整代码窗口，包括：

- 文件路径；
- 行号；
- 工具包装；
- 截断标记；
- 行号和临时路径。

它用于回答“当前方法在真实输入上是否能直接复用”。

### 3.2 Canonical 对象

额外生成去除以下字段后的代码视图：

- 行号；
- 工具名称和格式包装；
- 临时目录；
- 环境相关路径；
- 可确认的动态字段。

它用于回答“如果格式差异不影响复用，潜在机会有多大”，但不能替代 raw 结果。

### 3.3 Structural 对象

使用文件、类、函数、方法、语句或 AST 节点作为稳定对象。结构对象需要绑定 snapshot 和内容哈希，不能仅依赖函数名。

## 4. Snapshot 与 patch 规则

对每次 patch 建立状态边：

```text
snapshot_0 --patch event--> snapshot_1
```

判定规则：

- 同一 snapshot、相同 raw token：可计 exact reuse；
- 不同 snapshot、文件内容未变：可计跨 snapshot unchanged reuse；
- 不同 snapshot、对象内容改变：标记 invalidated；
- 仅函数名或路径相同：不能计 exact reuse；
- patch 影响文件但不影响某个对象：需要按对象内容哈希重新判断，不做整文件粗粒度失效。

## 5. 复用关系分类

对每一对候选对象计算：

1. `raw_exact_prefix`；
2. `raw_exact_non_prefix`；
3. `raw_partial_overlap`；
4. `canonical_overlap`；
5. `same_structural_unit`；
6. `cross_agent`；
7. `invalidated_overlap`。

推荐保留最长公共 token 区间和全部区间两个统计版本，避免多个小窗口把同一段代码重复累计。

## 6. 重点分析问题

### Q1：SWE 中 prefix reuse 是否被高估？

比较 `raw_exact_prefix` 与 `raw_exact_non_prefix + raw_partial_overlap`。如果大量代码只在上下文内部重复，prefix-only 方法的上限会明显低于整体 oracle。

### Q2：局部读取是否产生大量碎片机会？

统计同一文件、同一函数、不同窗口的重叠长度分布，并按 16/32/64/128/256 token 等尺度报告敏感性。

### Q3：跨 Agent 复用是否真实存在？

按 planner→coder、coder→reviewer、coder→tester 等角色对统计关系数量、token 数和距离。

### Q4：patch 导致多少机会失效？

报告 patch 前后对象的：

- exact 可复用比例；
- unchanged 比例；
- invalidated 比例；
- stale reuse 风险。

### Q5：工具输出是否值得缓存？

分别统计代码、搜索结果、测试输出、错误栈和自然语言分析的复用机会，并剥离动态字段后再做一个潜在上限。

## 7. SWE 指标

### Opportunity metrics

- `oracle_reusable_tokens`
- `prefix_reusable_tokens`
- `non_prefix_reusable_tokens`
- `cross_agent_reusable_tokens`
- `invalidated_tokens`
- reuse distance 的 P50/P90/P99

### Method metrics

- task success / patch correctness；
- quality delta 相对 full recompute；
- TTFT；
- prefill compute；
- cache lookup、transfer 和管理开销；
- GPU memory / CPU memory / network bytes；
- end-to-end task latency；
- stale reuse 或错误复用率。

## 8. 最小 pilot

第一轮不要覆盖全部 SWE-Gym：

1. 选 20 个 repo、每个 repo 5 条轨迹；
2. 先解析 read/grep/patch/test 四类事件；
3. 人工核验 100 条 exact、partial、invalidated 关系；
4. 对比 raw、canonical、structural 三种统计；
5. 只有 schema 稳定后，再扩展完整数据集和真实方法运行。
