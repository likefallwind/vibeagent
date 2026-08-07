from __future__ import annotations

import hashlib
import re


def write_process_content_sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def filter_output_lines(text: str, pattern: str | None) -> str:
    if pattern is None:
        return text
    regex = re.compile(pattern)
    return "".join(line for line in text.splitlines(keepends=True) if regex.search(line))
