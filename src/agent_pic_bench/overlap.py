"""Token-span overlap helpers shared by opportunity annotation and reports."""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any, Dict, List

from .tokenizer import TokenizerAdapter


def longest_common_span(
    source_text: str, target_text: str, tokenizer: TokenizerAdapter
) -> Dict[str, Any]:
    """Return the longest exact contiguous token span between two views.

    This is deliberately an oracle-style textual operation.  It does not
    claim that a model can safely reuse the span: snapshot compatibility,
    position exchangeability and method-specific constraints are separate
    annotations.
    """
    source_tokens = tokenizer.encode(source_text)
    target_tokens = tokenizer.encode(target_text)
    matcher = SequenceMatcher(a=source_tokens, b=target_tokens, autojunk=False)
    match = max(matcher.get_matching_blocks(), key=lambda block: block.size)
    size = int(match.size)
    source_start = int(match.a)
    target_start = int(match.b)
    if size == 0:
        position = "none"
    elif source_start == 0 and target_start == 0:
        position = "prefix"
    elif source_start + size == len(source_tokens) and target_start + size == len(target_tokens):
        position = "suffix"
    else:
        position = "interior"
    return {
        "overlap_tokens": size,
        "source_token_span": [source_start, source_start + size],
        "target_token_span": [target_start, target_start + size],
        "position_relation": position,
        "source_token_count": len(source_tokens),
        "target_token_count": len(target_tokens),
    }

