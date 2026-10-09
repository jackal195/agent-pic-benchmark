# Agent PIC 数据集建设路线 v0.1

## 核心决定

数据集的基本单位是 **Agent task trace**，不是一条问答，也不是一段孤立文本。

```text
task
  -> request sequence
    -> agent/tool/state events
      -> reusable objects
        -> reuse opportunity relations
```

这样设计是因为 PIC/KV reuse 依赖上下文出现的顺序、来源、位置和状态。只保存 prompt/answer，无法回答“这个块之前是否出现过”“中间 repo 是否被修改”“它属于哪个 Agent”。

## 为什么第一站选 SWE-Gym

SWE 场景包含四个最难的问题：

1. Agent 只读取代码的局部窗口；
2. grep、test、build 等工具输出带有动态字段；
3. patch 会改变 repository snapshot；
4. planner、coder、reviewer、tester 可能共享内容但看到的位置不同。

如果 schema 能正确处理 SWE，DeepResearch 和 DeepWiki 中的文档段落复用会容易很多。反过来先做普通 RAG，容易把“语义相似”误当成“KV 可以直接复用”。

## 阶段 0：固定数据契约

先固定下面五类对象：

- `trace`：一个 task 的完整可重放轨迹；
- `event`：一次 prompt、tool call、tool output、patch 或 state update；
- `reusable_object`：文件窗口、函数、文档段落、搜索结果等可追踪对象；
- `reuse_relation`：两个对象之间的 exact、partial、cross-agent 或 invalidated 关系；
- `method_run`：某个 PIC/KV 方法在同一 trace 上的命中、开销和质量结果。

关键原则是：`reuse_relation` 属于数据集 oracle，`method_run` 属于方法实验。方法不能修改 oracle 标注来让自己看起来更好。

## 阶段 1：SWE-Gym 最小 pilot

第一轮只做少量数据，目标是验证标注链路，不追求规模：

- 20 个 repo；
- 每个 repo 5 条轨迹；
- 只解析 `read_file`、`grep/search`、`patch/edit`、`test/build`；
- 先保存原始轨迹，不在导入时丢掉工具包装和行号。

每条轨迹导出：

```text
raw trace
normalized events
repository snapshots
code objects
reuse relations
```

### 为什么先做小 pilot

SWE 标注中最容易出错的是：同一个函数在不同窗口出现、行号变化、patch 前后内容变化、工具输出动态字段。先人工核对约 100 条关系，可以尽早发现规则错误；直接处理全量数据，错误会被复制成“规模”。

## 阶段 2：对象识别

每次代码读取同时生成三种视图：

1. `raw_view`：模型真实看到的文本，包含行号和工具格式；
2. `canonical_view`：移除确认的动态字段；
3. `structural_view`：文件、类、函数或 AST 节点。

### 为什么要三种视图

`raw_view` 决定真实 KV 是否能复用；`canonical_view` 估计格式差异消除后的潜在机会；`structural_view` 研究代码级重复。三种结果必须分别报告，否则会把“同一个函数”误报成“相同 KV”。

每个对象至少绑定：

```text
repo_id
snapshot_id
file_path
raw_span
token_span
raw_hash
content_hash
structural_id
```

## 阶段 3：机会分析

对候选对象计算以下关系：

- `raw_exact_prefix`；
- `raw_exact_non_prefix`；
- `raw_partial_overlap`；
- `cross_agent`；
- `same_structural_unit`；
- `invalidated_overlap`。

先使用固定 tokenizer 计算 token overlap；在 tokenizer 未固定前，只能把 whitespace token 结果标为 prototype，不能作为最终论文数字。

每条关系保存：

```text
source_object
target_object
overlap_tokens
source_position
target_position
reuse_distance
action_scope
snapshot_compatibility
annotation_confidence
```

## 阶段 4：先测 oracle，再接方法

每个场景至少跑三条线：

1. `no_reuse`：完全重新计算；
2. `oracle_reuse`：知道所有安全的真实重复块，忽略匹配管理开销；
3. `method_run`：接入具体 PIC/KV 方法，计入查找、传输、拼接和失效开销。

### 为什么要有 oracle

方法收益低时，需要区分两种原因：场景本来没有复用机会，或者方法没有抓住已有机会。oracle 把场景上限和方法能力分开。

## 阶段 5：训练数据和评测数据

训练与评测按 task、repo、文档来源和轨迹切分。SWE 至少使用 repo-disjoint test；DeepResearch 至少使用 document-disjoint test。

训练实验固定比较：

- zero-shot；
- 原方法训练数据；
- 本数据集训练数据；
- mixed training；
- cross-domain test；
- long-context test。

训练目标也要写清楚，是 chunk 边界、匹配、admission、eviction、invalidation prediction 还是 routing policy。统一称为“训练 PIC”会掩盖不同问题。

## 第一阶段验收标准

满足以下条件后，才扩展到更多场景：

1. 一条真实 SWE 轨迹可以完整解析为 event 序列；
2. 每个代码对象可以回溯到 repo snapshot；
3. exact、partial 和 invalidated 关系可以自动生成；
4. 人工核验约 100 条关系，规则错误可解释；
5. 能输出 prefix/non-prefix/cross-agent/invalidation 四类统计；
6. 样例可以被 trace replay 重新读取。

## 现在立刻做什么

仓库当前已有 schema validator 和最小样例。下一步实现：

```text
src/agent_pic_bench/ingest_swe.py
src/agent_pic_bench/code_objects.py
src/agent_pic_bench/overlap.py
src/agent_pic_bench/metrics.py
```

第一版输入一条 SWE 轨迹，输出一份 normalized trace 和一份 reuse relation JSONL。等这条链跑通，再下载全量数据；这样数据规模增长时，规则已经可检查，后续返工会少很多。
