"""Tokenizer adapters used by the relation annotator."""

from __future__ import annotations

from typing import Any


class TokenizerAdapter:
    """Small interface needed by the benchmark's overlap annotator."""

    name = "unknown"

    def encode(self, text: str) -> list[Any]:
        """Return token-like values used for overlap alignment.

        The prototype tokenizer intentionally returns strings; a model
        tokenizer returns integer ids.  Keeping the method here lets the
        annotator report partial code-window overlap without assuming either
        representation.
        """
        raise NotImplementedError

    def count(self, text: str) -> int:
        return len(self.encode(text))


class WhitespaceTokenizer(TokenizerAdapter):
    name = "whitespace-prototype"

    def encode(self, text: str) -> list[str]:
        return text.split()


class HuggingFaceTokenizer(TokenizerAdapter):
    def __init__(self, name: str, tokenizer: Any) -> None:
        self.name = name
        self._tokenizer = tokenizer

    def encode(self, text: str) -> list[int]:
        return self._tokenizer.encode(text, add_special_tokens=False)


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
