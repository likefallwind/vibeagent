from __future__ import annotations


def split_nonempty_lines(value: str) -> list[str]:
    return [line for line in value.splitlines() if line.strip()]


def usage_error(usage: str, error: object) -> str:
    return f"{usage}\nError: {error}"


def git_output_payload(output: str, *, truncated: bool, max_output_chars: int) -> dict[str, object]:
    lines = output.splitlines()
    return {
        "text": output,
        "chars": len(output),
        "lines": len(lines),
        "truncated": truncated,
        "maxOutputChars": max_output_chars,
    }


def git_log_items(log: str) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for line in split_nonempty_lines(log):
        short_hash, _, subject = line.partition(" ")
        items.append(
            {
                "hash": short_hash,
                "subject": subject,
                "raw": line,
            }
        )
    return items
