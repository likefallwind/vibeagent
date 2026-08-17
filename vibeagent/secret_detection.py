from __future__ import annotations

import re


SECRET_LIKE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private key block", re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")),
    (
        "credential assignment",
        re.compile(
            r"\b(?P<name>[A-Z0-9_]*(?:API[_-]?KEY|TOKEN|SECRET|PASSWORD|ACCESS[_-]?KEY)[A-Z0-9_]*)"
            r"\s*[:=]\s*[\"']?(?P<value>[A-Za-z0-9_./+=:-]{24,})",
            re.IGNORECASE,
        ),
    ),
    ("OpenAI API key", re.compile(r"\bsk-[A-Za-z0-9_-]{24,}\b")),
    ("GitHub token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{30,}\b")),
    ("AWS access key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
)


def secret_like_line_label(line: str) -> str | None:
    for label, pattern in SECRET_LIKE_PATTERNS:
        match = pattern.search(line)
        if not match:
            continue
        if label == "credential assignment":
            name = match.groupdict().get("name")
            value = match.groupdict().get("value")
            if not secret_like_assignment_is_high_confidence(name, value):
                continue
            return name.upper() if isinstance(name, str) and name else label
        return label
    return None


def secret_like_assignment_is_high_confidence(name: object, value: object) -> bool:
    if not isinstance(name, str) or not isinstance(value, str):
        return True
    normalized_name = name.upper().replace("-", "_")
    normalized_value = value.lower()
    if normalized_name.endswith(
        ("_PATH", "_TRUNCATED", "_WARNINGS", "_TOKENS", "_FINDINGS", "_TOTAL")
    ):
        return False
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        return False
    if any(
        marker in normalized_value
        for marker in ("testsecret", "placeholder", "dummy", "example", "redacted")
    ):
        return False
    if value.startswith(("src/", "tests/", "test/")) or value.endswith(
        (".py", ".txt", ".json", ".md")
    ):
        return False
    return True


__all__ = [
    "SECRET_LIKE_PATTERNS",
    "secret_like_assignment_is_high_confidence",
    "secret_like_line_label",
]
