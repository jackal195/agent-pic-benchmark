# Agent PIC Workload Taxonomy v0.1

## 1. 研究对象

本项目研究 Agent 工作流中上下文中间结果的复用机会和实际收益。一个 workload 不是一组独立问答，而是由任务、请求序列、Agent 角色、工具调用、环境状态和最终结果组成的可重放轨迹。

核心对象：

- `task`：一个需要完成的长期目标；
- `request`：一次送入模型的请求及其上下文；
- `agent`：执行请求的角色或实例；
- `context object`：组成请求上下文的可追踪对象；
- `reuse opportunity`：两个请求之间满足一定兼容条件的潜在复用关系。

## 2. 场景分类

| 场景 | 主要对象 | 典型复用关系 | 主要失效因素 |
|---|---|---|---|
| DeepResearch | 搜索结果、网页段落、引用、研究计划 | 多轮研究或子 Agent 共享资料 | 页面更新、排序变化、截断不同 |
| DeepWiki | 文件、函数、模块说明、代码关系 | 不同页面/问题反复访问同一 repo | 文件修改、窗口变化、版本不同 |
| SWE | issue、局部代码窗口、grep、测试输出、patch | planner/coder/reviewer/tester 共享 repo 信息 | patch、行号变化、动态工具输出 |
| AI Game | 状态观察、历史轨迹、规则、策略摘要 | 多轮决策或不同 Agent 共享世界状态 | 每步状态变化、旧状态失效 |
| Multi-agent collaboration | 计划、memory、工具结果、中间结论 | Agent 间交接和复核 | 角色提示不同、上下文位置变化 |

## 3. 复用维度

每条复用关系至少沿以下维度标注：

| 维度 | 值示例 | 说明 |
|---|---|---|
| token relation | `exact`, `partial`, `none` | 原始 token 序列是否重叠 |
| position relation | `prefix`, `interior`, `suffix`, `reordered` | 重叠块在请求中的位置 |
| scope | `same_request`, `cross_request`, `cross_agent` | 发生范围 |
| object type | `document`, `code`, `tool_output`, `memory` | 可复用对象类别 |
| state compatibility | `same_snapshot`, `unchanged`, `changed`, `unknown` | 环境状态是否兼容 |
| distance | 请求距离、时间距离 | 从上次出现到本次出现的距离 |
| confidence | `exact`, `structural`, `semantic` | 标注证据强度 |

`semantic` 只表示潜在语义复用，不应直接计入 exact KV reuse 收益。

## 4. 场景选择标准

一个数据集候选只有同时满足以下条件，才适合纳入主要 benchmark：

1. 能恢复请求顺序，而不是只有最终答案；
2. 能追踪上下文对象来源；
3. 能区分 Agent、请求和环境状态；
4. 能在不改变任务目标的前提下重放或构造跨请求关系；
5. 能验证复用后的质量或任务完成结果。

只有静态 prompt/answer 对、没有事件顺序和对象来源的数据，可作为辅助质量集，不作为主要 PIC opportunity benchmark。

## 5. 推荐数据切分

- `in_domain`：同一场景内的新任务；
- `cross_task`：任务类型不同但对象类型相近；
- `cross_domain`：例如 DeepResearch 训练、SWE 测试；
- `repo_disjoint`：SWE 测试 repo 不出现在训练集；
- `document_disjoint`：研究材料或网页集合不重叠；
- `long_context`：更长轨迹或更大上下文；
- `position_shift`：可交换场景中改变对象位置，测试位置鲁棒性。

## 6. 每个场景必须报告的统计量

- 每个 task 的 request 数和 agent 数；
- 上下文 token 数分布；
- exact prefix / exact non-prefix / partial overlap 比例；
- cross-agent opportunity 比例；
- reuse distance 分布；
- snapshot 或状态变化导致的 invalidation 比例；
- oracle 可复用 token 数及其占比；
- 轨迹重放成功率和缺失工具输出比例。
