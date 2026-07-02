from __future__ import annotations

import re
from typing import Any


SENSITIVE_TEXT_PATTERNS = (
    (
        re.compile(r"(?i)\b(bearer\s+)[A-Za-z0-9._~+/=-]{8,}"),
        lambda match: match.group(1) + "[REDACTED]",
    ),
    (
        re.compile(r"(?i)\b(authorization\s*:\s*)(?!\s*bearer\s+)[^\r\n]+"),
        lambda match: match.group(1) + "[REDACTED]",
    ),
    (
        re.compile(r"(?i)\b([A-Z0-9_]*(?:API[_-]?KEY|TOKEN|SECRET|PASSWORD)[A-Z0-9_]*\s*[:=]\s*['\"]?)([^'\"\s&]+)"),
        lambda match: match.group(1) + "[REDACTED]",
    ),
    (
        re.compile(r"(?i)([?&](?:api[_-]?key|access[_-]?token|token|secret|password)=)[^&\s]+"),
        lambda match: match.group(1) + "[REDACTED]",
    ),
    (
        re.compile(r"\bsk-[A-Za-z0-9][A-Za-z0-9_-]{8,}\b"),
        lambda match: "[REDACTED]",
    ),
    (
        re.compile(r"\b(?:ghp_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
        lambda match: "[REDACTED]",
    ),
)


def redact_sensitive_text(value: str) -> str:
    redacted = value
    for pattern, replacement in SENSITIVE_TEXT_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def redact_jsonable_payload(value: Any) -> Any:
    if isinstance(value, str):
        return redact_sensitive_text(value)
    if isinstance(value, dict):
        return {key: redact_jsonable_payload(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_jsonable_payload(item) for item in value]
    return value
