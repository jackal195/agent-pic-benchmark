# Agent PIC Benchmark

面向 Agent 工作流的 Prompt / Intermediate Context（PIC）与 KV reuse 数据集和评测框架。

当前仓库包含：

- workload taxonomy 与场景选择标准；
- unified trace、reusable object 和 reuse relation schema；
- SWE-Gym repo-based trajectory 分析协议；
- 相关方法对照矩阵；
- 一个可校验 JSONL trace 的最小 Python 工具。
- 一个手工标注关系样例 `data/examples/swe-mini-relations.jsonl`。

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
```

开发安装：

```bash
python3 -m pip install -e '.[dev]'
python3 -m pytest
```

数据设计文档在 [`outputs/`](outputs/README.md)。
