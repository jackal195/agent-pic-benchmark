"""CLI validator for trace JSONL files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .schema import ValidationError, validate_record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Agent PIC trace JSONL")
    parser.add_argument("path", type=Path)
    args = parser.parse_args(argv)

    records = 0
    try:
        with args.path.open(encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, start=1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                    validate_record(record)
                except (json.JSONDecodeError, ValidationError, TypeError) as error:
                    print(f"{args.path}:{line_number}: {error}", file=sys.stderr)
                    return 1
                records += 1
    except OSError as error:
        print(f"{args.path}: {error}", file=sys.stderr)
        return 1

    print(f"valid: {records} trace record(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
