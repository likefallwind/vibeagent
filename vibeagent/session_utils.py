from __future__ import annotations

from pathlib import Path
from typing import Any

from .redaction import redact_sensitive_text
from .session_id import is_valid_session_id
from .session_tool_result_failures import is_failed_tool_result


def is_local_session_id(run_id: str) -> bool:
    return run_id.startswith("local-")


def sessions_dir(project_root: str | Path) -> Path:
    return Path(project_root).resolve() / ".vibeagent" / "sessions"


def session_store_safety_error(project_root: str | Path) -> str | None:
    project = Path(project_root).resolve()
    runtime = project / ".vibeagent"
    sessions = runtime / "sessions"
    if runtime.is_symlink() or (runtime.exists() and not runtime.is_dir()):
        return "Session runtime path is not a regular directory: .vibeagent"
    if sessions.is_symlink() or (sessions.exists() and not sessions.is_dir()):
        return "Session root path is not a regular directory: .vibeagent/sessions"
    return None


def session_dir(project_root: str | Path, run_id: str) -> Path:
    if not is_valid_session_id(run_id):
        raise ValueError(f"Invalid session id: {run_id}")
    store_error = session_store_safety_error(project_root)
    if store_error:
        raise ValueError(store_error)
    path = sessions_dir(project_root) / run_id
    if path.is_symlink() or (path.exists() and not path.is_dir()):
        raise ValueError(f"Session path is not a regular directory: .vibeagent/sessions/{run_id}")
    return path


def events_path(project_root: str | Path, run_id: str) -> Path:
    path = session_dir(project_root, run_id) / "events.jsonl"
    event_error = session_events_safety_error(path)
    if event_error:
        raise ValueError(f"Session events path is not a regular file: .vibeagent/sessions/{run_id}/events.jsonl")
    return path


def session_events_safety_error(path: Path) -> str | None:
    if path.is_symlink() or (path.exists() and not path.is_file()):
        return "Session events path is not a regular file"
    return None


def as_int(value: Any) -> int | None:
    return value if isinstance(value, int) else None


def as_nonnegative_int(value: Any) -> int:
    return value if isinstance(value, int) and value >= 0 else 0


def parse_usage_payload(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        return {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "cache_creation_tokens": 0,
            "cache_read_tokens": 0,
        }
    input_tokens = as_nonnegative_int(value.get("input_tokens"))
    output_tokens = as_nonnegative_int(value.get("output_tokens"))
    total_tokens = as_nonnegative_int(value.get("total_tokens"))
    if total_tokens == 0 and (input_tokens or output_tokens):
        total_tokens = input_tokens + output_tokens
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "cache_creation_tokens": as_nonnegative_int(value.get("cache_creation_tokens")),
        "cache_read_tokens": as_nonnegative_int(value.get("cache_read_tokens")),
    }


def model_text(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, list):
        return ""
    return "".join(
        block["text"]
        for block in content
        if isinstance(block, dict) and block.get("type") == "text" and isinstance(block.get("text"), str)
    ).strip()


def has_tool_call_content(content: Any) -> bool:
    return isinstance(content, list) and any(
        isinstance(block, dict) and block.get("type") == "tool_call" for block in content
    )


def count_names(values: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return counts


def compact(value: str, max_length: int) -> str:
    collapsed = " ".join(redact_sensitive_text(value).split())
    if len(collapsed) <= max_length:
        return collapsed
    return f"{collapsed[:max_length]}..."
