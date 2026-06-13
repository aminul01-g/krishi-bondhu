"""Token utilities for estimating and truncating prompts.

Uses `tiktoken` when available; otherwise falls back to a simple
character-to-token heuristic (~4 chars per token).
"""
from __future__ import annotations

from typing import Optional

try:
    import tiktoken  # type: ignore
    _HAS_TIKTOKEN = True
except Exception:
    _HAS_TIKTOKEN = False


def estimate_tokens(text: str, model: Optional[str] = None) -> int:
    """Estimate token count for `text`.

    If `tiktoken` is available it will be used; otherwise falls back
    to len(text) // 4 as a rough estimate.
    """
    if not text:
        return 0
    if _HAS_TIKTOKEN:
        try:
            if model:
                enc = tiktoken.encoding_for_model(model)
            else:
                enc = tiktoken.get_encoding("cl100k_base")
            return len(enc.encode(text))
        except Exception:
            return max(1, len(text) // 4)
    # conservative fallback
    return max(1, len(text) // 4)


def truncate_by_tokens(text: str, max_tokens: int, model: Optional[str] = None) -> str:
    """Truncate text so it fits within `max_tokens` tokens.

    Keeps the tail (most recent context) which is typically more
    relevant in conversational prompts.
    """
    if max_tokens <= 0:
        return ""
    if not text:
        return text

    if _HAS_TIKTOKEN:
        try:
            if model:
                enc = tiktoken.encoding_for_model(model)
            else:
                enc = tiktoken.get_encoding("cl100k_base")
            tokens = enc.encode(text)
            if len(tokens) <= max_tokens:
                return text
            truncated_tokens = tokens[-max_tokens:]
            return enc.decode(truncated_tokens)
        except Exception:
            # fallback to char heuristic below
            pass

    # approximate by characters
    avg_chars_per_token = 4
    max_chars = max_tokens * avg_chars_per_token
    if len(text) <= max_chars:
        return text
    truncated = text[-max_chars:]
    # drop a leading partial line if present
    if "\n" in truncated:
        truncated = truncated[truncated.index("\n") + 1 :]
    return truncated
