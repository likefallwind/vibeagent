from __future__ import annotations

import difflib


def split_replacement_lines(content: str) -> list[str]:
    if content == "":
        return []
    lines = content.splitlines(keepends=True)
    if not content.endswith(("\n", "\r")):
        lines[-1] += "\n"
    return lines

def build_simple_diff(path: str, before: str, after: str) -> str:
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
        )
    )
