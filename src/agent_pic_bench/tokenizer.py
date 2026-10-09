"""Tokenizer adapters used by the relation annotator."""

from __future__ import annotations

from typing import Any


class TokenizerAdapter:
    """Small interface needed by the benchmark's overlap annotator."""

    name = "unknown"

    def count(self, text: str) -> int:
        raise NotImplementedError


class WhitespaceTokenizer(TokenizerAdapter):
    name = "whitespace-prototype"

    def count(self, text: str) -> int:
        return len(text.split())


class HuggingFaceTokenizer(TokenizerAdapter):
    def __init__(self, name: str, tokenizer: Any) -> None:
        self.name = name
        self._tokenizer = tokenizer

    def count(self, text: str) -> int:
        return len(self._tokenizer.encode(text, add_special_tokens=False))


def load_tokenizer(name: str) -> TokenizerAdapter:
    """Load a named tokenizer, keeping the prototype dependency-free."""
    if name == "whitespace-prototype":
        return WhitespaceTokenizer()

    try:
        from transformers import AutoTokenizer
    except ImportError as error:
        raise RuntimeError(
            "A Hugging Face tokenizer requires `pip install -e '.[hf]'`."
        ) from error

    return HuggingFaceTokenizer(
        name,
        AutoTokenizer.from_pretrained(name, use_fast=True),
    )
