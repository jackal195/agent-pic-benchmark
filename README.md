# Agent PIC Benchmark

面向 Agent 工作流的 Prompt / Intermediate Context（PIC）与 KV reuse 数据集和评测框架。

当前仓库包含：

- workload taxonomy 与场景选择标准；
- unified trace、reusable object 和 reuse relation schema；
- SWE-Gym repo-based trajectory 分析协议；
- 相关方法对照矩阵；
- 一个可校验 JSONL trace 的最小 Python 工具。
- 一个手工标注关系样例 `data/examples/swe-mini-relations.jsonl`。
- 代码窗口/工具输出的 span 级原型：`view_range`、最长连续 token overlap、位置类型和 mutation 排除。

## 快速开始

```bash
cd /Users/jackal/Documents/agent-pic-benchmark
PYTHONPATH=src python3 -m agent_pic_bench.validate_trace data/examples/swe-mini.jsonl
PYTHONPATH=src python3 -m agent_pic_bench.annotate_reuse data/examples/swe-mini.jsonl
```

开发阶段默认使用 `whitespace-prototype`。固定评测模型后，可安装 Hugging Face 适配器并传入模型 tokenizer：

```bash
python3 -m pip install -e '.[hf]'
PYTHONPATH=src python3 -m agent_pic_bench.annotate_reuse \
  data/examples/swe-mini.jsonl \
  --tokenizer MODEL_OR_TOKENIZER_ID

PYTHONPATH=src python3 -m agent_pic_bench.metrics \
  work/normalized/openhands-shard0.jsonl

PYTHONPATH=src python3 -m agent_pic_bench.cross_trace \
  work/normalized/openhands-shard0.jsonl

./scripts/run_openhands_pilot.sh
```

脚本会在 `work/results/openhands-shard0/` 生成 `relations.jsonl`，它是后续
PIC 方法评测使用的 reuse oracle 候选标注，不是具体缓存方法的命中结果。

`metrics` 中的 `prefix_relations`、`non_prefix_relations` 和
`overlap_tokens` 是机会分析指标，不是实际 KV 命中率；只有接入具体方法并
重放序列化请求后，才能报告真实 hit、TTFT 和质量变化。

`cross_trace` 用 task_id 聚合独立轨迹，并把 JSONL 顺序明确标为排序假设；没有
真实时间戳时，它只能作为可复查的跨任务 proxy，不能包装成线上用户到达率。

`annotate_reuse` 会把每条轨迹中的 observation 两两比较，输出扁平的
`relations.jsonl`。其中 `exchangeable`、`order_sensitive` 和
`partial_span_safe` 当前保守标为 `unknown`，不会把代码重复误判成可以随意搬运。

开发安装：

```bash
python3 -m pip install -e '.[dev]'
python3 -m pytest
```

数据设计文档在 [`outputs/`](outputs/README.md)。

现有场景与数据集总表见 [`outputs/dataset-registry-v0.1.md`](outputs/dataset-registry-v0.1.md)。

机器可读的数据集登记表位于 `data/dataset_registry.json`，可用下面命令检查：

```bash
PYTHONPATH=src python3 -m agent_pic_bench.validate_registry data/dataset_registry.json
```

汇报时可以直接参考 [`outputs/reporting-guide-v0.1.md`](outputs/reporting-guide-v0.1.md)。

导入真实 OpenHands-SWE-Gym 轨迹需要 Parquet 依赖：

```bash
python3 -m pip install -e '.[parquet]'
PYTHONPATH=src python3 -m agent_pic_bench.ingest_openhands \
  work/raw/openhands-sampled/train.raw-00000-of-00003.parquet \
  work/normalized/openhands-sample.jsonl \
  --limit 20
```
