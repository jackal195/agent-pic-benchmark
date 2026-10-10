#!/bin/sh

set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
input_path=${1:-"$repo_root/work/raw/openhands-sampled/train.raw-00000-of-00003.parquet"}
output_dir=${2:-"$repo_root/work/results/openhands-shard0"}

mkdir -p "$output_dir"

PYTHONPATH="$repo_root/src:$repo_root/work/deps" \
  python3 -m agent_pic_bench.ingest_openhands \
  "$input_path" "$output_dir/normalized.jsonl"

PYTHONPATH="$repo_root/src" \
  python3 -m agent_pic_bench.metrics \
  "$output_dir/normalized.jsonl" > "$output_dir/metrics.json"

PYTHONPATH="$repo_root/src" \
  python3 -m agent_pic_bench.cross_trace \
  "$output_dir/normalized.jsonl" > "$output_dir/cross-trace.json"

printf '%s\n' "Wrote pilot results to $output_dir"
printf '%s\n' "  normalized.jsonl"
printf '%s\n' "  metrics.json"
printf '%s\n' "  cross-trace.json"
