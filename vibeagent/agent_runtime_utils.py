from __future__ import annotations

import json
from threading import RLock
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from .action_parsing import ActionParseError
from .agent_multimodal import pending_image_tool_exchange, pending_image_tool_result_count
from .agent_observation_utils import summarize
from .prompt_observations import format_observations
from .prompts import build_messages
from .redaction import redact_jsonable_payload
from .session_event_sanitization import sanitize_session_event_payload
from .session_event_observers import notify_session_event_observers
from .types import ApprovalPolicy, ChatMessage, ContentBlock, ListFilesObservation, Observation, PlanItem, ToolErrorObservation
from .workspace_core import RunWorkspace
from .workspace_instruction_state import reset_loaded_instruction_documents


AGENT_MESSAGE_COMPACT_THRESHOLD = 18
AGENT_MESSAGE_COMPACT_CHAR_THRESHOLD = 96_000
AGENT_COMPACT_OBSERVATION_LIMIT = 20
AGENT_COMPACT_CONTEXT_MAX_LENGTH = 12_000
_SESSION_EVENT_WRITE_LOCK = RLock()


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


def message_history_char_count(messages: list[ChatMessage]) -> int:
    return sum(
        len(message.role)
        + (
            len(message.content)
            if isinstance(message.content, str)
            else len(json.dumps(message.content, ensure_ascii=False, sort_keys=True))
        )
        for message in messages
    )


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
    approval_policy: ApprovalPolicy = "ask",
    system_prompt: str | None = None,
    append_system_prompt: str | None = None,
    force: bool = False,
    reason: str | None = None,
    char_threshold: int = AGENT_MESSAGE_COMPACT_CHAR_THRESHOLD,
) -> list[ChatMessage]:
    previous_chars = message_history_char_count(messages)
    message_threshold_reached = len(messages) > threshold
    char_threshold_reached = previous_chars > char_threshold
    if not force and not message_threshold_reached and not char_threshold_reached:
        return messages

    prior_context = build_compacted_agent_context(
        observations,
        plan=plan,
        original_prior_context=original_prior_context,
        observation_limit=observation_limit,
        max_context_length=max_context_length,
    )
    compacted_messages = build_messages(
        task,
        workspace,
        observations,
        prior_context=prior_context,
        approval_policy=approval_policy,
        system_prompt=system_prompt,
        append_system_prompt=append_system_prompt,
    )
    pending_image_exchange = pending_image_tool_exchange(messages)
    compacted_messages.extend(pending_image_exchange)
    new_chars = message_history_char_count(compacted_messages)
    if compacted_messages == messages or ((force or char_threshold_reached) and new_chars >= previous_chars):
        return messages
    resolved_reason = reason or compaction_threshold_reason(message_threshold_reached, char_threshold_reached)
    reset_count, reset_error = _reset_path_instruction_state(workspace, "main")
    append_session_event(
        workspace.session_dir,
        "context_compacted",
        {
            "iteration": iteration,
            "previous_messages": len(messages),
            "new_messages": len(compacted_messages),
            "previous_chars": previous_chars,
            "new_chars": new_chars,
            "observations": len(observations),
            "plan_items": len(plan),
            "retained_observations": min(len(observations), observation_limit),
            "retained_image_tool_results": pending_image_tool_result_count(messages),
            "reason": resolved_reason,
            "path_instruction_sources_reset": reset_count,
            "path_instruction_reset_error": reset_error,
        },
    )
    return compacted_messages


def _reset_path_instruction_state(workspace: RunWorkspace, consumer_id: str) -> tuple[int, str | None]:
    try:
        return reset_loaded_instruction_documents(workspace, consumer_id), None
    except (OSError, ValueError) as error:
        return 0, str(error)


def compaction_threshold_reason(message_threshold_reached: bool, char_threshold_reached: bool) -> str:
    if message_threshold_reached and char_threshold_reached:
        return "message_and_char_threshold"
    if char_threshold_reached:
        return "char_threshold"
    return "message_threshold"


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
        sections.extend(f"- {format_compacted_plan_item(item)}" for item in current_plan)
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


def format_compacted_plan_item(item: PlanItem) -> str:
    text = f"{item.status}: {item.step}"
    if item.active_form:
        text += f" (activeForm: {item.active_form})"
    return text


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
    duration_ms = getattr(result, "duration_ms", 0)
    truncated = getattr(result, "stdout_truncated", False) or getattr(result, "stderr_truncated", False)
    output = getattr(result, "stderr") or getattr(result, "stdout") or "(no output)"
    return f"exit={exit_code} timedOut={timed_out} timeoutMs={timeout_ms} durationMs={duration_ms} outputTruncated={truncated} {summarize(output, 300)}"


def append_session_event(session_dir: Path, event_type: str, payload: dict[str, Any]) -> None:
    session_dir.mkdir(parents=True, exist_ok=True)
    event = redact_jsonable_payload(sanitize_session_event_payload(event_type, to_jsonable(payload)))
    event = {"type": event_type, **event}
    with _SESSION_EVENT_WRITE_LOCK:
        with (session_dir / "events.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    notify_session_event_observers(session_dir, event)


def to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return to_jsonable(asdict(value))
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(item) for item in value]
    return value
