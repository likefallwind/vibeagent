from __future__ import annotations

import json
from typing import Any

from .session_utils import compact, model_text


def model_tool_call_names(content: Any) -> list[str]:
    if not isinstance(content, list):
        return []
    names: list[str] = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "tool_call" and isinstance(block.get("name"), str):
            names.append(block["name"])
    return names


def legacy_model_raw_summary(raw: Any) -> tuple[str, list[str]]:
    if not isinstance(raw, str) or not raw.strip():
        return "", []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return raw.strip(), []
    if not isinstance(parsed, dict):
        return raw.strip(), []
    thought = parsed.get("thought")
    action = parsed.get("action")
    action_type = action.get("type") if isinstance(action, dict) else None
    message = action.get("message") if isinstance(action, dict) else None
    parts = []
    if isinstance(thought, str) and thought.strip():
        parts.append(thought.strip())
    if isinstance(message, str) and message.strip():
        parts.append(message.strip())
    names = [action_type] if isinstance(action_type, str) else []
    return "; ".join(parts), names


def format_usage_suffix(usage: dict[str, int]) -> str:
    if not (usage["input_tokens"] or usage["output_tokens"] or usage["total_tokens"]):
        return ""
    return f" (tokens={usage['input_tokens']}/{usage['output_tokens']}/{usage['total_tokens']})"


def format_detail_suffix(parts: list[str]) -> str:
    return f" ({', '.join(parts)})" if parts else ""


def format_subagent_started_event(prefix: str, payload: dict[str, Any], max_text: int) -> str:
    task = payload.get("task")
    subagent_id = payload.get("subagent_id")
    suffix = [f"id={compact(subagent_id, 80)}"] if isinstance(subagent_id, str) else []
    mode = payload.get("mode")
    if isinstance(mode, str):
        suffix.append(f"mode={compact(mode, 20)}")
    agent = payload.get("agent")
    if isinstance(agent, str):
        suffix.append(f"agent={compact(agent, 80)}")
    return f"{prefix} {compact(task, max_text) if isinstance(task, str) else '(missing task)'}{format_detail_suffix(suffix)}"


def format_subagent_model_event(prefix: str, payload: dict[str, Any], max_text: int) -> str:
    text = model_text(payload.get("content"))
    tool_names = model_tool_call_names(payload.get("content"))
    detail = compact(text, max_text) if text else "response"
    suffix = [f"toolCalls={', '.join(tool_names)}"] if tool_names else []
    return f"{prefix} {detail}{format_detail_suffix(suffix)}"


def format_subagent_tool_call_event(prefix: str, payload: dict[str, Any]) -> str:
    name = payload.get("name")
    subagent_id = payload.get("subagent_id")
    suffix = [f"id={compact(subagent_id, 80)}"] if isinstance(subagent_id, str) else []
    return f"{prefix} {name if isinstance(name, str) else 'unknown'}{format_detail_suffix(suffix)}"


def format_subagent_tool_result_event(prefix: str, payload: dict[str, Any]) -> str:
    name = payload.get("name")
    failed = payload.get("failed")
    suffix = [f"failed={'yes' if failed else 'no'}"] if isinstance(failed, bool) else []
    return f"{prefix} {name if isinstance(name, str) else 'unknown'}{format_detail_suffix(suffix)}"


def format_subagent_context_compacted_event(prefix: str, payload: dict[str, Any]) -> str:
    subagent_id = payload.get("subagent_id")
    previous_messages = payload.get("previous_messages")
    new_messages = payload.get("new_messages")
    observations = payload.get("observations")
    retained_observations = payload.get("retained_observations")
    suffix = [f"id={compact(subagent_id, 80)}"] if isinstance(subagent_id, str) else []
    mode = payload.get("mode")
    if isinstance(mode, str):
        suffix.append(f"mode={compact(mode, 20)}")
    agent = payload.get("agent")
    if isinstance(agent, str):
        suffix.append(f"agent={compact(agent, 80)}")
    if isinstance(previous_messages, int) and isinstance(new_messages, int):
        suffix.append(f"messages={previous_messages}->{new_messages}")
    if isinstance(observations, int):
        suffix.append(f"observations={observations}")
    if isinstance(retained_observations, int):
        suffix.append(f"retained={retained_observations}")
    return f"{prefix} compacted delegated context{format_detail_suffix(suffix)}"


def format_subagent_completed_event(prefix: str, payload: dict[str, Any], max_text: int) -> str:
    result = payload.get("result")
    ok = result.get("ok") if isinstance(result, dict) else None
    message = result.get("message") if isinstance(result, dict) else None
    suffix = []
    if isinstance(ok, bool):
        suffix.append(f"ok={'yes' if ok else 'no'}")
    if isinstance(message, str) and message.strip():
        suffix.append(f"message={compact(message, max_text)}")
    return f"{prefix}{format_detail_suffix(suffix)}"
