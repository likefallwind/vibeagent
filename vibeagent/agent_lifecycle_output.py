from __future__ import annotations

from dataclasses import dataclass
import json

from .agent_hook_results import HookRunResult


@dataclass(frozen=True)
class ParsedLifecycleHookOutput:
    context: str | None = None
    system_message: str | None = None
    watch_paths: tuple[str, ...] | None = None
    display_content: str | None = None
    decision: str | None = None
    reason: str | None = None
    plain_text: bool = False
    stop_reason: str | None = None
    continue_: bool | None = None


def parse_lifecycle_hook_output(result: HookRunResult) -> ParsedLifecycleHookOutput:
    if not result.ok or not result.stdout.strip():
        return ParsedLifecycleHookOutput()
    stripped = result.stdout.strip()
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        return ParsedLifecycleHookOutput(context=stripped, plain_text=True)
    if not isinstance(payload, dict):
        return ParsedLifecycleHookOutput()
    specific = payload.get("hookSpecificOutput")
    specific_payload = specific if isinstance(specific, dict) else {}
    context = specific_payload.get(
        "additionalContext", payload.get("additionalContext")
    )
    reason = payload.get("reason")
    stop_reason = payload.get("stopReason")
    continue_value = payload.get("continue")
    system_message = payload.get("systemMessage")
    return ParsedLifecycleHookOutput(
        context=context if isinstance(context, str) and context.strip() else None,
        system_message=(
            system_message
            if isinstance(system_message, str) and system_message.strip()
            else None
        ),
        watch_paths=_watch_paths_output(payload, specific_payload),
        display_content=_display_content_output(payload, specific_payload),
        decision=(
            payload.get("decision")
            if isinstance(payload.get("decision"), str)
            else None
        ),
        reason=reason if isinstance(reason, str) and reason.strip() else None,
        stop_reason=(
            stop_reason if isinstance(stop_reason, str) and stop_reason.strip() else None
        ),
        continue_=continue_value if isinstance(continue_value, bool) else None,
    )


def lifecycle_blocking_message(
    result: HookRunResult,
    output: ParsedLifecycleHookOutput,
) -> str | None:
    if result.handler_type in {"prompt", "agent"} and result.status == "blocked":
        return result.message
    if result.exit_code == 2:
        return result.stderr.strip() or result.message
    if output.decision == "block":
        return output.reason or "Configured hook blocked this lifecycle event."
    if output.continue_ is False:
        return output.stop_reason or "Configured hook stopped this lifecycle event."
    if output.context and result.event == "Stop" and not output.plain_text:
        return output.context
    return None


def _watch_paths_output(
    payload: dict[str, object],
    specific_payload: dict[str, object],
) -> tuple[str, ...] | None:
    missing = object()
    value = specific_payload.get("watchPaths", payload.get("watchPaths", missing))
    if value is missing:
        return None
    if (
        not isinstance(value, list)
        or len(value) > 100
        or any(not isinstance(path, str) for path in value)
    ):
        return None
    return tuple(value)


def _display_content_output(
    payload: dict[str, object],
    specific_payload: dict[str, object],
) -> str | None:
    missing = object()
    value = specific_payload.get(
        "displayContent", payload.get("displayContent", missing)
    )
    return value if isinstance(value, str) else None


__all__ = [
    "ParsedLifecycleHookOutput",
    "lifecycle_blocking_message",
    "parse_lifecycle_hook_output",
]
