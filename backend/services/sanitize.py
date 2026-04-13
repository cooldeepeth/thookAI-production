"""
XSS sanitization layer for free-text user input.

This module implements SECR-02 (OWASP Input Validation Cheat Sheet compliant)
using Python's standard-library ``html.escape`` to HTML-escape user-supplied
text before it is written to MongoDB. The escaping is idempotent at the
storage layer, so the same value read back is still safe to render inside
any HTML context.

Design choices:
- Standard library only — no ``bleach`` or other dependencies. ThookAI's API
  is JSON-only and does not accept rich-text HTML from users, so a pure
  escape (not a whitelist sanitizer) is sufficient.
- Non-string values pass through unchanged so the helpers are safe to call
  on mixed dicts containing integers, booleans, None, lists, etc.
- Functions never mutate their inputs — they return new values.
"""

from __future__ import annotations

import html
from typing import Any

FREE_TEXT_FIELDS: frozenset[str] = frozenset(
    {
        "name",
        "bio",
        "writing_samples",
        "raw_input",
        "description",
        "content",
        "hook_type",
        "answer",
        "title",
        "summary",
    }
)


def sanitize_text(value: Any) -> Any:
    """HTML-escape a string value.

    Uses ``html.escape(value, quote=True)`` which escapes
    ``& < > " '`` so the result is safe in any HTML context.
    Non-string values are returned unchanged so the helper is safe to use
    on dict values of mixed types.
    """
    if not isinstance(value, str):
        return value
    return html.escape(value, quote=True)


def sanitize_dict(
    data: dict[str, Any],
    fields: frozenset[str] = FREE_TEXT_FIELDS,
) -> dict[str, Any]:
    """Return a new dict with the specified string fields HTML-escaped.

    The input dict is not mutated. Fields not in ``fields`` are copied
    through unchanged. Non-string values in matching fields are also
    passed through unchanged.
    """
    return {
        key: sanitize_text(value) if key in fields and isinstance(value, str) else value
        for key, value in data.items()
    }
