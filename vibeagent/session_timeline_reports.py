from __future__ import annotations

from typing import Any

from .session_timeline_format_helpers import (
    format_detail_suffix,
    format_context_compacted_event,
    format_subagent_completed_event,
    format_subagent_context_compacted_event,
    format_subagent_model_event,
    format_subagent_started_event,
    format_subagent_tool_call_event,
    format_subagent_tool_result_event,
    format_usage_suffix,
    legacy_model_raw_summary,
    model_tool_call_names,
)
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
    if event.type == "context_compacted":
        return format_context_compacted_event(prefix, payload)
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
        scope = decision.get("scope") if isinstance(decision, dict) else None
        remembered = decision.get("remembered") if isinstance(decision, dict) else None
        suffix = []
        if isinstance(approved, bool):
            suffix.append(f"approved={'yes' if approved else 'no'}")
        if isinstance(scope, str):
            suffix.append(f"scope={compact(scope, 40)}")
        if isinstance(remembered, bool):
            suffix.append(f"remembered={'yes' if remembered else 'no'}")
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
        return format_subagent_started_event(prefix, payload, max_text)
    if event.type == "subagent_model":
        return format_subagent_model_event(prefix, payload, max_text)
    if event.type == "subagent_tool_call":
        return format_subagent_tool_call_event(prefix, payload)
    if event.type == "subagent_tool_result":
        return format_subagent_tool_result_event(prefix, payload)
    if event.type == "subagent_context_compacted":
        return format_subagent_context_compacted_event(prefix, payload)
    if event.type == "subagent_completed":
        return format_subagent_completed_event(prefix, payload, max_text)
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
    if event.type == "hooks_loaded":
        sources = payload.get("sources")
        count = payload.get("count")
        error = payload.get("error")
        names = [str(source) for source in sources] if isinstance(sources, list) else []
        suffix = [f"count={count if isinstance(count, int) else '?'}"]
        if isinstance(error, str) and error.strip():
            suffix.append(f"error={compact(error, max_text)}")
        return f"{prefix} {', '.join(names) or '(no sources)'}{format_detail_suffix(suffix)}"
    if event.type == "permissions_loaded":
        sources = payload.get("sources")
        count = payload.get("count")
        error = payload.get("error")
        names = [str(source) for source in sources] if isinstance(sources, list) else []
        suffix = [f"count={count if isinstance(count, int) else '?'}"]
        if isinstance(error, str) and error.strip():
            suffix.append(f"error={compact(error, max_text)}")
        return f"{prefix} {', '.join(names) or '(no sources)'}{format_detail_suffix(suffix)}"
    if event.type == "sandbox_loaded":
        enabled = payload.get("enabled")
        active = payload.get("active")
        available = payload.get("available")
        network_disabled = payload.get("network_disabled")
        auto_allow = payload.get("auto_allow_bash_if_sandboxed")
        sources = payload.get("sources")
        error = payload.get("error")
        names = [str(source) for source in sources] if isinstance(sources, list) else []
        suffix = []
        if isinstance(enabled, bool):
            suffix.append(f"enabled={'yes' if enabled else 'no'}")
        if isinstance(active, bool):
            suffix.append(f"active={'yes' if active else 'no'}")
        if isinstance(available, bool):
            suffix.append(f"available={'yes' if available else 'no'}")
        if isinstance(network_disabled, bool):
            suffix.append(f"networkDisabled={'yes' if network_disabled else 'no'}")
        if isinstance(auto_allow, bool):
            suffix.append(f"autoAllow={'yes' if auto_allow else 'no'}")
        if isinstance(error, str) and error:
            suffix.append(f"error={compact(error, max_text)}")
        return f"{prefix} {', '.join(names) or '(no sources)'}{format_detail_suffix(suffix)}"
    if event.type == "sandbox_auto_approved":
        tool = payload.get("tool")
        request = payload.get("request")
        target = request.get("target") if isinstance(request, dict) else None
        suffix = []
        if isinstance(target, str):
            suffix.append(f"target={compact(target, max_text)}")
        return f"{prefix} {tool if isinstance(tool, str) else 'unknown'}{format_detail_suffix(suffix)}"
    if event.type == "permission_rule_evaluated":
        tool = payload.get("tool")
        effect = payload.get("effect")
        rule = payload.get("rule")
        source = payload.get("source")
        error = payload.get("error")
        suffix = []
        if isinstance(rule, str):
            suffix.append(f"rule={compact(rule, max_text)}")
        if isinstance(source, str):
            suffix.append(f"source={compact(source, 160)}")
        if isinstance(error, str):
            suffix.append(f"error={compact(error, max_text)}")
        detail = f"{effect if isinstance(effect, str) else 'unknown'} {tool if isinstance(tool, str) else 'unknown'}"
        return f"{prefix} {detail}{format_detail_suffix(suffix)}"
    if event.type in {"hook_approval_requested", "hook_approval_decision", "hook_completed", "hook_skipped"}:
        hook_event = payload.get("event")
        tool = payload.get("tool")
        source = payload.get("source")
        suffix = []
        if isinstance(source, str):
            suffix.append(f"source={compact(source, 160)}")
        handler_type = payload.get("handler_type")
        if isinstance(handler_type, str):
            suffix.append(f"handler={compact(handler_type, 40)}")
        if event.type == "hook_approval_decision":
            decision = payload.get("decision")
            approved = decision.get("approved") if isinstance(decision, dict) else None
            if isinstance(approved, bool):
                suffix.append(f"approved={'yes' if approved else 'no'}")
        if event.type in {"hook_completed", "hook_skipped"}:
            result = payload.get("result")
            status = result.get("status") if isinstance(result, dict) else None
            message = result.get("message") if isinstance(result, dict) else None
            http_status = result.get("http_status") if isinstance(result, dict) else None
            if isinstance(status, str):
                suffix.append(f"status={compact(status, 40)}")
            if isinstance(message, str) and message.strip():
                suffix.append(f"message={compact(message, max_text)}")
            if isinstance(http_status, int):
                suffix.append(f"httpStatus={http_status}")
        detail = f"{hook_event if isinstance(hook_event, str) else 'hook'} {tool if isinstance(tool, str) else 'unknown'}"
        return f"{prefix} {detail}{format_detail_suffix(suffix)}"
    if event.type in {
        "async_hook_started",
        "async_hook_completed",
        "async_hook_notifications_delivered",
        "async_hook_cancelled",
        "async_hook_discarded",
    }:
        hook_event = payload.get("event")
        target = payload.get("target")
        process_id = payload.get("process_id")
        suffix = []
        if isinstance(process_id, str):
            suffix.append(f"processId={compact(process_id, 80)}")
        if isinstance(payload.get("exit_code"), int):
            suffix.append(f"exitCode={payload['exit_code']}")
        if isinstance(payload.get("timed_out"), bool):
            suffix.append(f"timedOut={'yes' if payload['timed_out'] else 'no'}")
        if isinstance(payload.get("rewake"), bool):
            suffix.append(f"rewake={'yes' if payload['rewake'] else 'no'}")
        count = payload.get("count")
        if isinstance(count, int):
            suffix.append(f"count={count}")
        outcome = payload.get("outcome")
        if isinstance(outcome, str):
            suffix.append(f"outcome={compact(outcome, 80)}")
        detail = " ".join(
            value
            for value in (
                hook_event if isinstance(hook_event, str) else None,
                target if isinstance(target, str) else None,
            )
            if value
        )
        return f"{prefix} {detail or 'async hook'}{format_detail_suffix(suffix)}"
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
