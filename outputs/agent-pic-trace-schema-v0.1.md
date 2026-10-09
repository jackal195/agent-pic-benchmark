# Unified Trace and Reuse Annotation Schema v0.1

## 1. 分层存储

建议把数据分成四层，避免“方法命中结果”污染原始标注：

```text
raw_trace
  -> normalized_events
  -> reusable_objects + reuse_relations
  -> method_runs
```

`raw_trace` 和 `normalized_events` 是数据集资产；`method_runs` 是某个方法在指定协议下的实验输出。

## 2. Trace 主记录

```json
{
  "trace_id": "swe_repo12_task004_run01",
  "scenario": "swe",
  "task_id": "task004",
  "source_dataset": "swe-gym",
  "model_family": "model-name",
  "tokenizer_id": "tokenizer-name",
  "agents": ["planner", "coder", "reviewer"],
  "initial_state": {"repo_id": "repo12", "snapshot_id": "commit0"},
  "events": ["event-0001", "event-0002"]
}
```

## 3. Event 记录

```json
{
  "event_id": "event-0007",
  "trace_id": "swe_repo12_task004_run01",
  "request_id": "request-0003",
  "agent_id": "coder",
  "event_index": 7,
  "event_type": "tool_output",
  "tool_type": "read_file",
  "timestamp": null,
  "snapshot_id": "commit0",
  "raw_text": "...",
  "normalized_text": "...",
  "token_ids": [101, 42,  ...],
  "source_objects": ["obj-file-auth-py-span-40-90"],
  "dynamic_fields": [],
  "parent_event_id": "event-0006"
}
```

建议的 `event_type`：

- `user_request`
- `agent_prompt`
- `tool_call`
- `tool_output`
- `agent_response`
- `state_update`
- `patch`
- `test_result`
- `final_answer`

## 4. Reusable object

```json
{
  "object_id": "obj-file-auth-py-span-40-90",
  "object_type": "code",
  "source_id": "repo12",
  "path": "src/auth.py",
  "snapshot_id": "commit0",
  "raw_span": {"start_line": 40, "end_line": 90},
  "token_span": {"start": 820, "end": 1260},
  "structural_id": "function:auth.validate",
  "raw_hash": "sha256:...",
  "content_hash": "sha256:...",
  "dynamic_fields": [],
  "mutable": true
}
```

### 三种内容视图

1. `raw_text`：模型真实看到的文本；用于真实 KV 收益；
2. `canonical_text`：去除工具包装、路径和可变格式后的内容；用于潜在机会分析；
3. `structural_id`：函数、类、文档段落或网页对象等稳定标识；用于结构级分析。

三者必须分别计数，不能用 canonical overlap 冒充 raw exact hit。

## 5. Reuse relation

```json
{
  "relation_id": "rel-001",
  "source_object_id": "obj-a",
  "target_object_id": "obj-b",
  "relation_type": "exact_non_prefix",
  "overlap_tokens": 312,
  "source_position": {"start": 100, "end": 412},
  "target_position": {"start": 740, "end": 1052},
  "scope": "cross_agent",
  "source_agent_id": "planner",
  "target_agent_id": "coder",
  "source_snapshot_id": "commit0",
  "target_snapshot_id": "commit0",
  "reuse_distance_events": 8,
  "state_compatible": true,
  "annotation_confidence": "exact"
}
```

## 6. 标注规则

- exact overlap 必须在固定 tokenizer 下比较；
- 行号不同但代码相同：`content_overlap` 可为真，`raw_exact_overlap` 不一定为真；
- patch 前后相同函数名不能自动视为同一内容；必须比较 snapshot 和内容哈希；
- semantic similarity 不进入 exact opportunity 统计；
- 同一对象重复出现时，保留第一次出现、最近一次出现和全部出现关系；
- 工具输出中的时间、临时路径、随机 id 标记为 `dynamic_fields`；
- 任何因状态修改而不安全的关系必须显式标记 `invalidated`。

## 7. 数据集质量检查

发布前至少检查：

1. tokenization 可复现；
2. 所有 object 能回指 raw event；
3. 所有 code object 能回指 repo snapshot；
4. relation 的 overlap token 数可由 span 重算；
5. trace 顺序和 parent/child 关系无环；
6. train/test 没有同 repo、同文档或同 task 泄漏；
7. trace replay 成功率和缺失工具输出有统计。
