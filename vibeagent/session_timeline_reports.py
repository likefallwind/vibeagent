from __future__ import annotations

import json
from typing import Any

from .session_types import SessionEvent
from .session_utils import compact, model_text, parse_usage_payload


def serialize_session_timeline_event(event: SessionEvent, max_text: int = 500) -> dict[str, Any]:
    return {
        "lineNumber": event.line_number,
        "type": event.type,
        "malformed": event.malformed,
        "summary": format_session_event_timeline_item(event, max_text=max_text),
    }


def format_session_event_timeline_item(event: SessionEvent, max_text: int = 500) -> str:
    prefix = f"    - #{event.line_number} {event.type}:"
    if event.malformed:
        return f"{prefix} malformed row ({compact(event.error or 'unknown error', max_text)})"

    payload = event.payload
    if event.type == "task":
        task = payload.get("task")
        return f"{prefix} {compact(task, max_text) if isinstance(task, str) else '(missing task)'}"
    if event.type == "model":
        text = model_text(payload.get("content"))
        tool_names = model_tool_call_names(payload.get("content"))
        if not text and not tool_names:
            text, tool_names = legacy_model_raw_summary(payload.get("raw"))
        usage = parse_usage_payload(payload.get("usage"))
        usage_text = format_usage_suffix(usage)
        if text and tool_names:
            return f"{prefix} {compact(text, max_text)}; toolCalls={', '.join(tool_names)}{usage_text}"
        if text:
            return f"{prefix} {compact(text, max_text)}{usage_text}"
        if tool_names:
            return f"{prefix} toolCalls={', '.join(tool_names)}{usage_text}"
        return f"{prefix} response{usage_text}"
    if event.type in {"model_error", "subagent_model_error"}:
        error_type = payload.get("error_type")
        message = payload.get("message")
        iteration = payload.get("iteration")
        attempt = payload.get("attempt")
        attempts = payload.get("attempts")
        will_retry = payload.get("will_retry")
        suffix = []
        if isinstance(iteration, int):
            suffix.append(f"iteration={iteration}")
        if isinstance(attempt, int) and isinstance(attempts, int):
            suffix.append(f"attempt={attempt}/{attempts}")
        if isinstance(will_retry, bool):
            suffix.append(f"willRetry={'yes' if will_retry else 'no'}")
        if isinstance(error_type, str) and error_type.strip():
            suffix.append(f"type={compact(error_type, 120)}")
        if isinstance(message, str) and message.strip():
            suffix.append(f"message={compact(message, max_text)}")
        return f"{prefix}{format_detail_suffix(suffix)}"
    if event.type == "action":
        action = payload.get("action")
        action_type = action.get("type") if isinstance(action, dict) else None
        thought = payload.get("thought")
        suffix = []
        if isinstance(thought, str) and thought.strip():
            suffix.append(f"thought={compact(thought, max_text)}")
        if isinstance(action, dict) and isinstance(action.get("message"), str) and action["message"].strip():
            suffix.append(f"message={compact(action['message'], max_text)}")
        return f"{prefix} {action_type if isinstance(action_type, str) else 'unknown'}{format_detail_suffix(suffix)}"
    if event.type == "observation":
        observation = payload.get("observation")
        kind = observation.get("kind") if isinstance(observation, dict) else None
        ok = observation.get("ok") if isinstance(observation, dict) else None
        message = observation.get("message") if isinstance(observation, dict) else None
        suffix = []
        if isinstance(ok, bool):
            suffix.append(f"ok={'yes' if ok else 'no'}")
        if isinstance(message, str) and message.strip():
            suffix.append(f"message={compact(message, max_text)}")
        return f"{prefix} {kind if isinstance(kind, str) else 'unknown'}{format_detail_suffix(suffix)}"
    if event.type == "tool_call":
        name = payload.get("name")
        iteration = payload.get("iteration")
        tool_id = payload.get("id")
        detail = f"{name}" if isinstance(name, str) else "unknown"
        suffix = []
        if isinstance(iteration, int):
            suffix.append(f"iteration={iteration}")
        if isinstance(tool_id, str) and tool_id:
            suffix.append(f"id={compact(tool_id, 80)}")
        return f"{prefix} {detail}{format_detail_suffix(suffix)}"
    if event.type == "tool_result":
        result = payload.get("result")
        result_kind = result.get("kind") if isinstance(result, dict) else None
        name = payload.get("name") if isinstance(payload.get("name"), str) else result_kind
        ok = result.get("ok") if isinstance(result, dict) else None
        message = result.get("message") if isinstance(result, dict) else None
        suffix = []
        iteration = payload.get("iteration")
        if isinstance(iteration, int):
            suffix.append(f"iteration={iteration}")
        if isinstance(ok, bool):
            suffix.append(f"ok={'yes' if ok else 'no'}")
        if isinstance(message, str) and message.strip():
            suffix.append(f"message={compact(message, max_text)}")
        return f"{prefix} {name or 'unknown'}{format_detail_suffix(suffix)}"
    if event.type == "result":
        success = payload.get("success")
        status = payload.get("status")
        message = payload.get("message")
        suffix = []
        if isinstance(success, bool):
            suffix.append(f"success={'yes' if success else 'no'}")
        iterations = payload.get("iterations")
        if isinstance(iterations, int):
            suffix.append(f"iterations={iterations}")
        if isinstance(message, str) and message.strip():
            suffix.append(f"message={compact(message, max_text)}")
        return f"{prefix} {status if isinstance(status, str) else 'unknown'}{format_detail_suffix(suffix)}"
    if event.type == "approval_requested":
        request = payload.get("request")
        action = request.get("action_type") if isinstance(request, dict) else payload.get("action_type")
        risk = request.get("risk") if isinstance(request, dict) else payload.get("risk")
        target = request.get("target") if isinstance(request, dict) else payload.get("target")
        preview = request.get("preview") if isinstance(request, dict) else payload.get("preview")
        suffix = []
        if isinstance(target, str) and target.strip():
            suffix.append(f"target={compact(target, 160)}")
        if isinstance(risk, str) and risk.strip():
            suffix.append(f"risk={compact(risk, 160)}")
        if isinstance(preview, str) and preview.strip():
            suffix.append(f"preview={compact(preview, max_text)}")
        return f"{prefix} {action if isinstance(action, str) else 'unknown'}{format_detail_suffix(suffix)}"
    if event.type == "approval_decision":
        decision = payload.get("decision")
        approved = decision.get("approved") if isinstance(decision, dict) else None
        message = decision.get("message") if isinstance(decision, dict) else None
        suffix = []
        if isinstance(approved, bool):
            suffix.append(f"approved={'yes' if approved else 'no'}")
        if isinstance(message, str) and message.strip():
            suffix.append(f"message={compact(message, max_text)}")
        return f"{prefix}{format_detail_suffix(suffix)}"
    if event.type == "user_input_requested":
        request = payload.get("request")
        question = request.get("question") if isinstance(request, dict) else None
        options = request.get("options") if isinstance(request, dict) else None
        suffix = []
        if isinstance(options, list):
            suffix.append(f"options={len(options)}")
        return f"{prefix} {compact(question, max_text) if isinstance(question, str) else '(missing question)'}{format_detail_suffix(suffix)}"
    if event.type == "user_input_answered":
        result = payload.get("result")
        answer = result.get("answer") if isinstance(result, dict) else None
        cancelled = result.get("cancelled") if isinstance(result, dict) else None
        suffix = []
        if isinstance(cancelled, bool):
            suffix.append(f"cancelled={'yes' if cancelled else 'no'}")
        if isinstance(answer, str) and answer.strip():
            suffix.append(f"answer={compact(answer, max_text)}")
        return f"{prefix}{format_detail_suffix(suffix)}"
    if event.type == "subagent_started":
        task = payload.get("task")
        subagent_id = payload.get("subagent_id")
        suffix = [f"id={compact(subagent_id, 80)}"] if isinstance(subagent_id, str) else []
        mode = payload.get("mode")
        if isinstance(mode, str):
            suffix.append(f"mode={compact(mode, 20)}")
        return f"{prefix} {compact(task, max_text) if isinstance(task, str) else '(missing task)'}{format_detail_suffix(suffix)}"
    if event.type == "subagent_model":
        text = model_text(payload.get("content"))
        tool_names = model_tool_call_names(payload.get("content"))
        detail = compact(text, max_text) if text else "response"
        suffix = [f"toolCalls={', '.join(tool_names)}"] if tool_names else []
        return f"{prefix} {detail}{format_detail_suffix(suffix)}"
    if event.type == "subagent_tool_call":
        name = payload.get("name")
        subagent_id = payload.get("subagent_id")
        suffix = [f"id={compact(subagent_id, 80)}"] if isinstance(subagent_id, str) else []
        return f"{prefix} {name if isinstance(name, str) else 'unknown'}{format_detail_suffix(suffix)}"
    if event.type == "subagent_tool_result":
        name = payload.get("name")
        failed = payload.get("failed")
        suffix = [f"failed={'yes' if failed else 'no'}"] if isinstance(failed, bool) else []
        return f"{prefix} {name if isinstance(name, str) else 'unknown'}{format_detail_suffix(suffix)}"
    if event.type == "subagent_completed":
        result = payload.get("result")
        ok = result.get("ok") if isinstance(result, dict) else None
        message = result.get("message") if isinstance(result, dict) else None
        suffix = []
        if isinstance(ok, bool):
            suffix.append(f"ok={'yes' if ok else 'no'}")
        if isinstance(message, str) and message.strip():
            suffix.append(f"message={compact(message, max_text)}")
        return f"{prefix}{format_detail_suffix(suffix)}"
    if event.type == "tool_catalog_initialized":
        active = payload.get("active")
        total = payload.get("total")
        return f"{prefix} active={active if isinstance(active, int) else '?'} total={total if isinstance(total, int) else '?'}"
    if event.type == "tools_activated":
        activated = payload.get("activated")
        source = payload.get("source")
        names = [str(name) for name in activated] if isinstance(activated, list) else []
        suffix = [f"source={source}"] if isinstance(source, str) else []
        return f"{prefix} {', '.join(names) or '(none)'}{format_detail_suffix(suffix)}"
    if event.type == "step_completed":
        step = payload.get("step")
        if isinstance(step, dict):
            action = step.get("action_type")
            status = step.get("status")
            message = step.get("message")
            suffix = []
            if isinstance(status, str):
                suffix.append(f"status={status}")
            if isinstance(message, str) and message.strip():
                suffix.append(f"message={compact(message, max_text)}")
            return f"{prefix} {action if isinstance(action, str) else 'step'}{format_detail_suffix(suffix)}"
        return f"{prefix} step"
    return f"{prefix} event"


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
