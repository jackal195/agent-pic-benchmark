# Agent PIC/KV Reuse Dataset v0.1

这一版把项目拆成四份可以独立评审的设计文档：

1. [Agent PIC workload taxonomy](agent-pic-workload-taxonomy-v0.1.md)
2. [Unified trace and annotation schema](agent-pic-trace-schema-v0.1.md)
3. [SWE-Gym reuse opportunity protocol](swe-gym-reuse-protocol-v0.1.md)
4. [Related-method comparison matrix](related-method-matrix-v0.1.md)

## 当前假设

本文档中的 PIC 暂按“prompt/intermediate/KV reuse”这一类上下文中间结果复用问题处理。若学长材料中 PIC 有特定全称，只需要替换术语，不影响数据结构和评测分层。

## 统一原则

- 原始 Agent 轨迹、可复用对象标注、方法实际命中结果分开保存。
- exact token reuse、结构相同、语义相似不能混为一个指标。
- oracle opportunity 和真实方法收益分开报告。
- 训练集与评测集按 task、repo、document、agent trajectory 做去泄漏切分。
- SWE 中的 repository snapshot、patch 和工具动态字段必须进入标注。
