# Agent PIC 数据集总表 v0.1

## 这张表的目的

本表先回答“每个数据集能测什么”，再决定是否对它做 reuse annotation。
不要把所有数据集都硬改造成同一种 benchmark：有的数据适合训练，有的适合方法评测，有的适合真实 workload 分析，有的只能作为受控压力测试。

## 先区分四类资源

| 类型 | 它回答的问题 | 典型资源 |
|---|---|---|
| 真实 Agent 轨迹 | Agent 实际如何调用工具、读取内容、修改状态 | OpenHands/SWE-Gym trajectories、DeepResearch trajectories、MindGames |
| 任务/环境 benchmark | Agent 能否完成任务，环境和答案如何验证 | SWE-bench、SWE-QA-Pro、BrowseComp-Plus、MACHIAVELLI |
| 受控 PIC/KV benchmark | 已知内容可复用时，方法能否安全、高效地复用 | SCBench、KVShareArena、Boxoffice |
| 静态内容/训练数据 | 学习代码、文档、检索或工具使用，但不一定有完整请求顺序 | DeepWiki 文档集、DeepResearch-9K demonstrations |

## 场景覆盖矩阵

标记含义：

- A：有完整或较完整的 Agent/环境轨迹，适合做 workload 分析
- B：适合构造可重放评测，但需要补请求/上下文关系
- C：适合训练或静态质量评测，不能直接证明自然复用
- D：受控合成或专门方法 benchmark，不能代表自然 workload

| 场景 | 主要 reusable object | 候选数据集/资源 | 轨迹 | 状态/版本 | 适合 PIC train | 适合 PIC eval | 复用机会类型 | 当前判断 |
|---|---|---|---|---|---|---|---|---|
| DeepResearch / web research | 搜索结果、网页段落、引用、研究报告、子 Agent report | OpenResearcher-Dataset、DeepResearch-traj、DeepResearch-9K | A | 页面/检索状态需核查 | 是 | 是 | 跨问题证据、同文档不同位置、multi-hop non-prefix、报告交接 | 首要候选 |
| 固定语料深度搜索 | query、正例文档、hard negative、检索结果 | BrowseComp-Plus | B | 固定 corpus，强 | 较弱 | 是 | 可控 evidence reuse、检索结果重排、位置变化 | 评测首要候选 |
| DeepWiki / repo understanding | 文档段落、代码片段、函数、架构图、引用 | CodeWikiBench；第三方 DeepWiki 文档集 | B/C | commit 级信息取决于资源 | 是 | 是 | 文档→代码、代码→文档、同 repo 多问题复用 | 不能把 DeepWiki 产品本身当数据集 |
| SWE repo-based trajectory | issue、代码窗口、grep、测试输出、patch、repo snapshot | SWE-Gym/OpenHands trajectories、SWE-bench trajectories、SWE-rebench、SWE-smith、SWE-Next | A | SWE-Gym/SWE-bench 部分有 commit；轨迹需逐项核查 | 是 | 是 | 同 repo 跨 task、patch invalidation、prefix/non-prefix、工具输出复用 | 当前已做 SWE-Gym 原型 |
| Repo-level QA | 问题、跨文件证据、代码窗口、最终答案 | SWE-QA-Pro、SWE-QA、LongCodeQA、CodeReQA | B | SWE-QA-Pro 明确有 commit_id；通常没有完整自然轨迹 | 是 | 是 | 同 repo 多问题共享文件/函数、证据窗口复用 | 适合补充 SWE trajectory |
| Persistent coding workspace | 代码状态、跨轮需求、测试、workspace snapshot | EvoCode-Bench | A/B | 持久 workspace、累计测试、状态 lineage | 是 | 是 | 跨轮上下文、旧状态失效、需求演化、重复读取 | 重要缺口场景 |
| Multi-agent collaboration | specialist report、计划、消息、共享 memory、judge input | KVShareArena Agent Reports、MindGames、各类 planner/coder/reviewer logs | A/B | 取决于资源 | 是 | 是 | 跨 Agent report、不同 system prompt、non-prefix assembly | 需要明确自然/合成来源 |
| AI game / social strategy | public/private observation、聊天、动作、状态、奖励、memory | MACHIAVELLI、MindGames/MGC2025、HanabiLogs/HanabiRewards、Werewolf logs、TextArena | A | 游戏状态通常明确 | 是 | 是 | 跨回合状态、公共信息、私有信息、跨局 memory、角色消息 | 作为独立大场景 |
| Persistent memory / service agent | timeline、工具结果、用户状态、memory read/write/update | Momento、MEMTRACK、MUMBench/相关 memory benchmarks | A/B | 时间顺序和状态是核心 | 是 | 是 | 跨 session、stale memory、冲突更新、权限边界 | PIC 与 memory 交叉场景 |
| Long-context shared context | shared context、follow-up query、multi-turn/multi-request | SCBench | B/D | 受控，强 | 较弱 | 是 | exact prefix、multi-request、multi-turn、query shift | KV lifecycle baseline |
| Cross-context / cross-checkpoint KV | retrieved chunks、agent reports、producer/receiver checkpoint | KVShareArena | D | 实验状态由 harness 控制 | 否 | 是 | position shift、source blindness、checkpoint shift、repair | 方法评测基准 |
| Controlled stale-cache stress test | synthetic chunks、warmup/eval query、cache version | Boxoffice | D | 完全可控 | 否 | 是 | aligned/flipped context、stale cache、多版本 chunk | 不能当自然 workload |

## 已核实的代表性资源

### 1. DeepResearch

- `OpenResearcher-Dataset / DeepResearch-traj`：包含完整多轮 web-browsing trajectory、工具调用和最终正确性信息；适合做搜索结果、网页证据和多轮研究轨迹分析。[1][2]
- `DeepResearch-9K`：9,000 个 deep-research 问题及高质量搜索轨迹，适合训练/评测 research agent；需要核查其轨迹是否完整保留每次检索返回内容以及许可细节。[3]
- `BrowseComp-Plus`：在固定、人工核验的文档语料上评测 deep-search agent，带 gold/supporting documents 和 hard negatives；它是强评测集，但不是自然 web 到达流量。[4]

### 2. DeepWiki / repository understanding

- `CodeWikiBench`：22 个开源 repository，包含 commit、文档树、结构化文档和评价 rubric；适合 repo documentation / code-document grounding 评测。[5]
- DeepWiki 产品本身不是一个公开、标准化的 Agent trajectory dataset。Hugging Face 上的 `deepwiki`、`deepwiki3`、`deepwiki4`、`deepwiki10` 等资源应单独记录来源、版本、许可和生成方式，不能直接当成官方 DeepWiki trajectory。
- DeepWiki 类数据的主要机会是“文档段落 ↔ 代码对象”复用，而不是先假设存在跨用户 KV reuse。

### 3. SWE / repo-based

- `SWE-Gym`：2,438 个真实 Python 软件工程任务、11 个 repo、可执行环境和测试；OpenHands trajectories 是当前最适合做 repo-based reuse opportunity 分析的资源之一。[6]
- `SWE-bench` 系列：任务、repo、base commit 和测试验证强，但原始任务集不等于完整 Agent trajectory；应把任务集和公开 trajectory 分开登记。[7]
- `SWE-QA-Pro`：260 个 QA、26 个 long-tail repository，字段包含 repo、commit_id、cluster、qa_type、question、answer；它适合 repository-level QA evaluation，也可以构造同 repo 多问题共享证据的 PIC workload，但不能直接声称是自然 trajectory。[8]
- `SWE-rebench`、`SWE-smith`、`SWE-Next`、`agentic-coding-trajectories`：适合扩大 coding-agent 训练和轨迹覆盖；必须逐个记录是否真实、是否合成、是否包含完整 tool observation、是否带 base commit。

### 4. AI game

- `MACHIAVELLI`：文本冒险游戏环境，包含大量场景和行为/伦理标注；适合长轨迹、状态转移和决策上下文研究，但不是天然 KV reuse benchmark。[9]
- `MindGames / MGC2025`：四类多 Agent 游戏，释放 29,571 局、94,132 条 player trajectories 和 turn-level observations/actions/rewards；适合跨 Agent 公共信息、私有信息、聊天和状态复用分析。[10]
- `HanabiLogs / HanabiRewards`：1,520+ 完整 Hanabi trajectories 和 560+ 带 move-level utility 的 games；适合合作 Agent、部分可观测状态和动作价值训练。[11]
- Werewolf/Avalon logs：适合社会推理、公共辩论、私有角色信息和跨局 memory；需要核查每个资源的 license、完整性和是否含模型真实输入。[12]

### 5. PIC/KV 专门评测

- `SCBench`：12 个任务、multi-turn 和 multi-request shared context，覆盖 string retrieval、semantic retrieval、global information 和 multi-task；适合作为 KV lifecycle baseline。[13]
- `KVShareArena`：明确评测 retrieved evidence 和 agent reports，并交叉 context change 与 producer checkpoint change；同时报告质量、prefill compute、KV bytes 和 latency；这是方法评测集，不是自然 workload 数据集。[14]
- `Boxoffice`：程序生成 fictional movie corpus，保证 evaluation chunk 已在 warmup 中出现，并控制 aligned/flipped/stale cache 等 reuse pattern；适合作为受控 stress test，不应冒充真实用户流量。[15]

## 每个数据集必须补齐的 registry 字段

```text
dataset_id
canonical_name
aliases
scene
resource_type: trajectory | task | environment | static_content | controlled_stress
source_url
paper_url
code_url
license
version_or_commit
size
unit: task | session | trajectory | turn | query | game | document | chunk
has_full_trajectory
has_tool_calls
has_tool_observations
has_agent_identity
has_request_order
has_wall_clock
has_repo_or_world_state
has_version_or_snapshot
has_public_private_boundary
has_answer_or_reward
natural_reuse_evidence: yes | no | unknown
controlled_reuse_constructable: yes | no | unknown
train_role: primary | auxiliary | no
 eval_role: primary | auxiliary | no
reusable_object
candidate_reuse_pairs
main_failure_modes
provenance_confidence
next_action
```

## 不同场景应该构造什么“合理复用机会”

### DeepResearch

不要简单复制同一个问题。应构造：

1. 不同问题共享同一网页或同一证据段落；
2. 同一证据在不同检索排序和不同上下文位置出现；
3. 多跳问题中 source A、source B 分别被不同请求读取，后续由 synthesis agent 组合；
4. 页面更新后只让受影响的证据失效；
5. 区分 search result snippet、正文、引用和最终报告。

### DeepWiki

应构造：

1. 不同代码问题共享同一函数/模块；
2. 文档问题先读 wiki section，代码问题再读 source span；
3. 同一 repo 不同 commit 的文档和代码对齐；
4. 架构图、调用图、代码窗口分别作为对象；
5. 文档生成和问答使用不同上下文顺序，测试位置迁移。

### SWE

应保留真实 trajectory，不人为复制作为主结果。可做两条 track：

- natural track：从 SWE-Gym/OpenHands 等真实轨迹统计自然重复；
- controlled replay：固定 repo snapshot 和 task，构造 planner→coder→reviewer、不同窗口、patch 前后和失败重试场景。

必须记录：path、view_range、函数/AST、snapshot、patch、tool output、动态字段和测试结果。

### AI game

应按游戏状态而不是简单文本重复构造：

1. 同一公共历史对不同玩家的可见上下文；
2. 不同玩家共享公共消息，但保留私有信息边界；
3. 跨回合重复状态与状态变化；
4. 跨局 memory 与 stale reputation；
5. 合作、竞争、欺骗和部分可观测分别评测。

## 第一版不要做的事

- 不把所有数据集拼成一个分数；
- 不把静态 QA 数据集说成完整 Agent trajectory；
- 不把 synthetic reuse 说成 natural reuse；
- 不把工具返回说成模型 serialized request；
- 不把同一个 repo/path 直接当成同一段内容；
- 不把 exact reuse、semantic similarity 和结构相似混成一个指标；
- 不先追求覆盖几十个数据集而不核查 provenance、license、字段和可重放性。

## 第一版推荐主线

1. 建立全场景 registry：DeepResearch、DeepWiki、SWE、AI Game、Persistent Memory、PIC/KV controlled。
2. 每个场景选一个主数据集和一个补充数据集，不先全量下载。
3. 先统一检查字段和可重放性，再决定标注器是否复用。
4. 保留两种结果：natural reuse opportunity 与 controlled reuse evaluation。
5. SWE-Gym/OpenHands 作为第一条真实 trajectory 分析线；BrowseComp-Plus、SWE-QA-Pro、CodeWikiBench 作为可控/任务补充；SCBench、KVShareArena、Boxoffice 作为方法评测对照；MindGames/Hanabi/MACHIAVELLI 作为 AI game 轨迹线。

## Sources

[1] https://huggingface.co/datasets/IPF/DeepResearch-traj
[2] https://github.com/TIGER-AI-Lab/OpenResearcher
[3] https://arxiv.org/html/2603.01152
[4] https://aclanthology.org/2026.acl-long.1023/
[5] https://github.com/FSoft-AI4Code/CodeWikiBench
[6] https://github.com/SWE-Gym/SWE-Gym
[7] https://www.swebench.com/SWE-bench/guides/datasets/
[8] https://huggingface.co/datasets/TIGER-Lab/SWE-QA-Pro-Bench
[9] https://github.com/aypan17/machiavelli
[10] https://arxiv.org/html/2605.29512v1
[11] https://arxiv.org/pdf/2601.18077v1
[12] https://kaggle.com/datasets/kaggle/werewolf-dataset
[13] https://huggingface.co/datasets/microsoft/SCBench
[14] https://arxiv.org/html/2609.10266v1
[15] https://arxiv.org/abs/2609.31415

机器可读登记表：`data/dataset_registry.json`。它是当前研究计划的工作表，
其中 `verify_sample`、`unknown` 和 `analyze` 表示需要下载样本或运行适配器后再确认，
不是已经完成的事实标签。
