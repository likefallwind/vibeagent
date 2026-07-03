from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from .action_parsing import ActionParseError
from .agent_observation_utils import summarize
from .prompt_observations import format_observations
from .prompts import build_messages
from .redaction import redact_jsonable_payload
from .types import ChatMessage, ContentBlock, ListFilesObservation, Observation, PlanItem, ToolErrorObservation
from .workspace_core import RunWorkspace


AGENT_MESSAGE_COMPACT_THRESHOLD = 18
AGENT_COMPACT_OBSERVATION_LIMIT = 20
AGENT_COMPACT_CONTEXT_MAX_LENGTH = 12_000
SESSION_TOOL_INPUT_REDACT_KEYS = {"content", "old", "new", "replacement", "patch", "value"}


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


def compact_agent_message_history(
    task: str,
    workspace: RunWorkspace,
    messages: list[ChatMessage],
    observations: list[Observation],
    plan: list[PlanItem],
    original_prior_context: str | None,
    iteration: int,
    threshold: int = AGENT_MESSAGE_COMPACT_THRESHOLD,
    observation_limit: int = AGENT_COMPACT_OBSERVATION_LIMIT,
    max_context_length: int = AGENT_COMPACT_CONTEXT_MAX_LENGTH,
) -> list[ChatMessage]:
    if len(messages) <= threshold:
        return messages

    prior_context = build_compacted_agent_context(
        observations,
        plan=plan,
        original_prior_context=original_prior_context,
        observation_limit=observation_limit,
        max_context_length=max_context_length,
    )
    compacted_messages = build_messages(task, workspace, observations, prior_context=prior_context)
    append_session_event(
        workspace.session_dir,
        "context_compacted",
        {
            "iteration": iteration,
            "previous_messages": len(messages),
            "new_messages": len(compacted_messages),
            "observations": len(observations),
            "plan_items": len(plan),
            "retained_observations": min(len(observations), observation_limit),
        },
    )
    return compacted_messages


def build_compacted_agent_context(
    observations: list[Observation],
    plan: list[PlanItem] | None = None,
    original_prior_context: str | None = None,
    observation_limit: int = AGENT_COMPACT_OBSERVATION_LIMIT,
    max_context_length: int = AGENT_COMPACT_CONTEXT_MAX_LENGTH,
) -> str:
    recent_observations = observations[-observation_limit:]
    current_plan = plan or []
    sections = [
        "Compacted current-run context:",
        f"Total observations so far: {len(observations)}.",
        f"Current task plan items: {len(current_plan)}.",
        f"Recent observations retained: {len(recent_observations)}.",
    ]
    if current_plan:
        sections.append("Current task plan:")
        sections.extend(f"- {item.status}: {item.step}" for item in current_plan)
    if original_prior_context:
        compacted_prior = compact_session_context(original_prior_context)
        if compacted_prior:
            sections.extend(["Original prior-session context:", compacted_prior])
    sections.extend(
        [
            "Compacted current-run observations:",
            format_observations(recent_observations),
        ]
    )
    compacted = "\n".join(sections)
    return compact_session_context(compacted, max_context_length) or ""


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
    event = redact_jsonable_payload(sanitize_session_event_payload(event_type, to_jsonable(payload)))
    event = {"type": event_type, **event}
    with (session_dir / "events.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def sanitize_session_event_payload(event_type: str, payload: Any) -> Any:
    if not isinstance(payload, dict):
        return payload
    sanitized = dict(payload)
    if event_type == "tool_call":
        sanitized["input"] = sanitize_tool_call_input(sanitized.get("input"))
    if event_type == "model":
        sanitized["content"] = sanitize_model_event_content(sanitized.get("content"))
    return sanitized


def sanitize_model_event_content(content: Any) -> Any:
    if not isinstance(content, list):
        return content
    sanitized_blocks: list[Any] = []
    for block in content:
        if not isinstance(block, dict) or block.get("type") != "tool_call":
            sanitized_blocks.append(block)
            continue
        sanitized_block = dict(block)
        sanitized_block["input"] = sanitize_tool_call_input(sanitized_block.get("input"))
        sanitized_blocks.append(sanitized_block)
    return sanitized_blocks


def sanitize_tool_call_input(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): redacted_tool_input_value(str(key), item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [sanitize_tool_call_input(item) for item in value]
    return value


def redacted_tool_input_value(key: str, value: Any) -> Any:
    if key in SESSION_TOOL_INPUT_REDACT_KEYS:
        return summarize_redacted_tool_input_value(value)
    if isinstance(value, dict):
        return sanitize_tool_call_input(value)
    if isinstance(value, list):
        return [sanitize_tool_call_input(item) for item in value]
    return value


def summarize_redacted_tool_input_value(value: Any) -> dict[str, Any]:
    summary: dict[str, Any] = {"redacted": True}
    if isinstance(value, str):
        summary.update({"type": "string", "chars": len(value), "lines": len(value.splitlines())})
    elif isinstance(value, list):
        summary.update({"type": "list", "items": len(value)})
    elif isinstance(value, dict):
        summary.update({"type": "object", "keys": len(value)})
    elif value is None:
        summary.update({"type": "null"})
    else:
        summary.update({"type": type(value).__name__})
    return summary


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
