from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Literal

from .agent_hook_results import HookRunResult


PreToolPermissionDecision = Literal["allow", "deny", "ask", "defer"]


@dataclass(frozen=True)
class ParsedPreToolHookOutput:
    permission_decision: PreToolPermissionDecision | None = None
    permission_reason: str | None = None
    updated_input: dict[str, object] | None = None
    additional_context: str | None = None


class PreToolHookOutputError(ValueError):
    pass


def parse_pre_tool_hook_output(result: HookRunResult) -> ParsedPreToolHookOutput:
    stdout = result.stdout.strip()
    if not result.ok or not stdout:
        return ParsedPreToolHookOutput()
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as error:
        if stdout.startswith(("{", "[")):
            raise PreToolHookOutputError(
                f"PreToolUse hook returned invalid JSON: {error.msg}."
            ) from error
        return ParsedPreToolHookOutput()
    if not isinstance(payload, dict):
        raise PreToolHookOutputError("PreToolUse hook JSON output must be an object.")

    specific_value = payload.get("hookSpecificOutput")
    if specific_value is not None and not isinstance(specific_value, dict):
        raise PreToolHookOutputError("hookSpecificOutput must be an object.")
    specific = specific_value if isinstance(specific_value, dict) else {}
    event_name = specific.get("hookEventName")
    if event_name is not None and event_name != "PreToolUse":
        raise PreToolHookOutputError(
            "hookSpecificOutput.hookEventName must be 'PreToolUse'."
        )

    decision = specific.get("permissionDecision")
    reason = specific.get("permissionDecisionReason")
    updated_input = specific.get("updatedInput")
    additional_context = specific.get("additionalContext")

    legacy_decision = payload.get("decision")
    if decision is None and legacy_decision in {"approve", "block"}:
        decision = "allow" if legacy_decision == "approve" else "deny"
        reason = payload.get("reason", reason)
    if decision is not None and decision not in {"allow", "deny", "ask", "defer"}:
        raise PreToolHookOutputError(
            "permissionDecision must be allow, deny, ask, or defer."
        )
    if reason is not None and not isinstance(reason, str):
        raise PreToolHookOutputError("permissionDecisionReason must be a string.")
    if updated_input is not None and not isinstance(updated_input, dict):
        raise PreToolHookOutputError("updatedInput must be an object.")
    if additional_context is not None and not isinstance(additional_context, str):
        raise PreToolHookOutputError("additionalContext must be a string.")

    return ParsedPreToolHookOutput(
        permission_decision=decision,
        permission_reason=reason.strip() if isinstance(reason, str) and reason.strip() else None,
        updated_input=updated_input,
        additional_context=(
            additional_context.strip()
            if isinstance(additional_context, str) and additional_context.strip()
            else None
        ),
    )


def merge_pre_tool_decision(
    current: PreToolPermissionDecision | None,
    candidate: PreToolPermissionDecision | None,
) -> PreToolPermissionDecision | None:
    if candidate is None:
        return current
    precedence = {"allow": 1, "ask": 2, "defer": 3, "deny": 4}
    if current is None or precedence[candidate] > precedence[current]:
        return candidate
    return current


__all__ = [
    "ParsedPreToolHookOutput",
    "PreToolHookOutputError",
    "PreToolPermissionDecision",
    "merge_pre_tool_decision",
    "parse_pre_tool_hook_output",
]
