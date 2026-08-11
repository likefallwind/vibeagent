from __future__ import annotations

import hashlib
from typing import Any


MAX_COMMENT_CHARS = 65_536


def github_comment_metadata(body: str) -> dict[str, Any]:
    return {
        "body_chars": len(body),
        "body_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
    }


def github_comment_summary(body: str, *, maximum: int = 120) -> str:
    compact = " ".join(body.split())
    return compact if len(compact) <= maximum else compact[:maximum] + "..."


def validate_github_comment_body(body: object, *, destination: str) -> str | None:
    if not isinstance(body, str) or not body.strip() or len(body) > MAX_COMMENT_CHARS:
        return f"GitHub {destination} comment body must contain 1-{MAX_COMMENT_CHARS} characters."
    if any(ord(char) < 32 and char not in "\n\r\t" for char in body):
        return f"GitHub {destination} comment body cannot contain control characters."
    return None
