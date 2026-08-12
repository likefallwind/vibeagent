from __future__ import annotations

from typing import Any


SESSION_TOOL_INPUT_REDACT_KEYS = {"content", "old", "new", "replacement", "patch", "value"}
SESSION_TOOL_RESULT_REDACT_KEYS = {"content", "diff"}


def sanitize_session_event_payload(event_type: str, payload: Any) -> Any:
    if not isinstance(payload, dict):
        return payload
    sanitized = dict(payload)
    if event_type == "tool_call":
        sanitized["input"] = sanitize_tool_call_input(sanitized.get("input"))
    if event_type == "tool_result":
        sanitized["result"] = sanitize_tool_result_payload(sanitized.get("result"))
    if event_type in {"model", "prompt_suggestion_model"}:
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
        return summarize_redacted_value(value)
    if isinstance(value, dict):
        return sanitize_tool_call_input(value)
    if isinstance(value, list):
        return [sanitize_tool_call_input(item) for item in value]
    return value


def sanitize_tool_result_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): redacted_tool_result_value(str(key), item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [sanitize_tool_result_payload(item) for item in value]
    return value


def redacted_tool_result_value(key: str, value: Any) -> Any:
    if key in SESSION_TOOL_RESULT_REDACT_KEYS:
        return summarize_redacted_value(value)
    if isinstance(value, dict):
        return sanitize_tool_result_payload(value)
    if isinstance(value, list):
        return [sanitize_tool_result_payload(item) for item in value]
    return value


def summarize_redacted_value(value: Any) -> dict[str, Any]:
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
