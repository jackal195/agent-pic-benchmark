# Related Method Comparison Matrix v0.1

## 说明

以下是用于调研的统一记录表，不把论文标题直接等同于机制结论。具体字段应以论文正文、代码和实验设置核对后填写；当前未核对的格子保持为“待核对”。

| 方法 | 主要复用粒度 | 跨请求/Agent | 匹配方式 | 状态失效 | 训练 | workload | 需要重点核对 |
|---|---|---|---|---|---|---|---|
| CacheBlend | chunk / blended context（待核对） | 待核对 | 待核对 | 待核对 | 待核对 | RAG/长上下文类（待核对） | chunk 规则、质量损失、是否支持 non-prefix |
| EPIC | cache sharing（待核对） | 待核对 | 待核对 | 待核对 | 待核对 | 待核对 | 共享范围、索引和传输开销 |
| APE | cache reuse / policy（待核对） | 待核对 | 待核对 | 待核对 | 待核对 | 待核对 | 是否学习 admission/matching，训练数据来源 |
| KVLink | KV linking / sharing（待核对） | 待核对 | 待核对 | 待核对 | 待核对 | 待核对 | link 的粒度、位置约束和一致性 |
| RelayCaching | relay / distributed reuse（待核对） | 待核对 | 待核对 | 待核对 | 待核对 | 待核对 | 网络与端到端收益是否计入 |
| C2KV | cache coordination（待核对） | 待核对 | 待核对 | 待核对 | 待核对 | 待核对 | 多请求调度、失效和资源开销 |
| KVCOMM | KV communication（待核对） | 待核对 | 待核对 | 待核对 | 待核对 | 待核对 | 通信成本、硬件假设、可迁移性 |
| TokenDance | system/layout（待核对） | 待核对 | 待核对 | 待核对 | 待核对 | 待核对 | 主要解决布局、传输还是复用判定 |
| Dynamic Flow / Static Graph | system execution（待核对） | 待核对 | 待核对 | 待核对 | 待核对 | mobile NPU（待核对） | 静态/动态执行假设是否适合 Agent trace |
| LLMCBench | adjacent compression benchmark | 不直接对应 | 不直接对应 | 不直接对应 | 待核对 | model compression | 借鉴统一接口、硬件和端到端评测规范 |

## 建议的核对顺序

1. 先确认每篇论文的 cache unit 和 reuse scope；
2. 再确认是否支持 non-prefix、partial 和 cross-agent；
3. 再记录 workload、chunk 规则、tokenizer 和模型；
4. 最后记录训练数据、quality metric 和真实端到端开销。

## 统一实验基线

任何方法进入 Agent PIC benchmark 前，至少需要提供：

- 方法适配器或 HTTP 接口；
- cache hit/miss 日志；
- reused token 数；
- lookup、transfer、merge 和 invalidation 开销；
- 质量结果；
- 在同一 trace replay engine 上的端到端结果。
