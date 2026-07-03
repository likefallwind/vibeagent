from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from .action_parsing import ActionParseError
from .agent_observation_utils import summarize
from .redaction import redact_jsonable_payload
from .types import ContentBlock, ListFilesObservation, Observation, ToolErrorObservation


def format_exception(error: Exception) -> str:
    text = str(error).strip()
    if not text:
        return type(error).__name__
    return f"{type(error).__name__}: {summarize(text, 1000)}"


def compact_session_context(value: str | None, max_length: int = 4000) -> str | None:
    if value is None:
        return None
    compact = "\n".join(line.rstrip() for line in value.strip().splitlines() if line.strip())
    if len(compact) <= max_length:
        return compact
    return f"{compact[:max_length]}..."


def list_files_action_path(action: object) -> str | None:
    if getattr(action, "type", None) != "list_files":
        return None
    return str(getattr(action, "path", None) or ".")


def build_repeated_list_observation(repeated_list: ListFilesObservation) -> ListFilesObservation:
    return ListFilesObservation(
        kind="list_files",
        path=repeated_list.path,
        files=repeated_list.files,
        total=repeated_list.total,
        truncated=repeated_list.truncated,
        message=(
            f"Already listed {repeated_list.path}: {repeated_list.message} "
            "Do not call list_files for this path again. Choose a useful tool call or answer directly."
        ),
    )


def find_repeated_list_observation(action: object, observations: list[Observation]) -> ListFilesObservation | None:
    path = list_files_action_path(action)
    if path is None:
        return None

    for observation in reversed(observations):
        if observation.kind == "list_files" and observation.path == path:
            return observation
    return None


def normalize_assistant_content(value: Any) -> list[ContentBlock]:
    if isinstance(value, str):
        return [{"type": "text", "text": value}]
    if isinstance(value, list):
        return [dict(block) for block in value if isinstance(block, dict)]
    return []


def content_blocks_to_text(content: list[ContentBlock]) -> str:
    return "".join(block["text"] for block in content if block.get("type") == "text" and isinstance(block.get("text"), str))


def tool_error_observation(tool_name: str, error: ActionParseError) -> Observation:
    return ToolErrorObservation(kind="tool_error", tool=tool_name or "unknown", message=f"Invalid tool input: {error}")


def summarize_command(result: object) -> str:
    exit_code = getattr(result, "exit_code")
    timed_out = getattr(result, "timed_out")
    timeout_ms = getattr(result, "timeout_ms", "unknown")
    truncated = getattr(result, "stdout_truncated", False) or getattr(result, "stderr_truncated", False)
    output = getattr(result, "stderr") or getattr(result, "stdout") or "(no output)"
    return f"exit={exit_code} timedOut={timed_out} timeoutMs={timeout_ms} outputTruncated={truncated} {summarize(output, 300)}"


def append_session_event(session_dir: Path, event_type: str, payload: dict[str, Any]) -> None:
    session_dir.mkdir(parents=True, exist_ok=True)
    event = redact_jsonable_payload(to_jsonable({"type": event_type, **payload}))
    with (session_dir / "events.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return to_jsonable(asdict(value))
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    return value
