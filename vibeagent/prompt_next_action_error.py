from __future__ import annotations

from .types import Observation


ERROR_NEXT_ACTION_KINDS = {
    "approval_denied",
    "tool_error",
}


def _approval_denied_next_action_instruction(base: str, latest: Observation) -> str:
    action_type = str(getattr(latest, "action_type", "") or "the requested action").strip()
    target = str(getattr(latest, "target", "") or "").strip()
    target_label = f" for {target}" if target else ""
    return (
        f"{base} Approval was denied for {action_type}{target_label}. "
        "Do not repeat the same approval-gated action unchanged. Use read-only inspection or a safer alternative, "
        "request a different approval only if the user intent still requires it, or explain the blocker if the task cannot proceed."
    )


def _tool_error_next_action_instruction(base: str, latest: Observation) -> str:
    tool = str(getattr(latest, "tool", "") or "unknown").strip()
    return (
        f"{base} Tool error occurred while running {tool}. "
        "Do not repeat the same tool call unchanged. Inspect the error message, correct the tool input or choose an alternate tool, "
        "then continue the task and verify before finishing."
    )


def error_next_action_instruction(base: str, latest: Observation) -> str:
    if latest.kind == "approval_denied":
        return _approval_denied_next_action_instruction(base, latest)
    if latest.kind == "tool_error":
        return _tool_error_next_action_instruction(base, latest)

    raise ValueError(f"Unsupported error next-action kind: {latest.kind}")
