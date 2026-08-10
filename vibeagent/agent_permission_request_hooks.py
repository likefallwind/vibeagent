from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Literal

from .agent_hook_results import HookRunResult


PermissionRequestBehavior = Literal["allow", "deny"]


@dataclass(frozen=True)
class ParsedPermissionRequestHookOutput:
    behavior: PermissionRequestBehavior | None = None
    message: str | None = None


@dataclass(frozen=True)
class PermissionRequestHookOutcome:
    behavior: PermissionRequestBehavior | None = None
    message: str | None = None
    results: tuple[HookRunResult, ...] = ()


class PermissionRequestHookOutputError(ValueError):
    pass


def parse_permission_request_hook_output(
    result: HookRunResult,
) -> ParsedPermissionRequestHookOutput:
    stdout = result.stdout.strip()
    if not result.ok or not stdout:
        return ParsedPermissionRequestHookOutput()
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as error:
        if stdout.startswith(("{", "[")):
            raise PermissionRequestHookOutputError(
                f"PermissionRequest hook returned invalid JSON: {error.msg}."
            ) from error
        return ParsedPermissionRequestHookOutput()
    if not isinstance(payload, dict):
        raise PermissionRequestHookOutputError(
            "PermissionRequest hook JSON output must be an object."
        )
    specific_value = payload.get("hookSpecificOutput")
    if specific_value is None:
        return ParsedPermissionRequestHookOutput()
    if not isinstance(specific_value, dict):
        raise PermissionRequestHookOutputError("hookSpecificOutput must be an object.")
    event_name = specific_value.get("hookEventName")
    if event_name != "PermissionRequest":
        raise PermissionRequestHookOutputError(
            "hookSpecificOutput.hookEventName must be 'PermissionRequest'."
        )
    decision = specific_value.get("decision")
    if decision is None:
        return ParsedPermissionRequestHookOutput()
    if not isinstance(decision, dict):
        raise PermissionRequestHookOutputError(
            "PermissionRequest decision must be an object."
        )
    behavior = decision.get("behavior")
    if behavior not in {"allow", "deny"}:
        raise PermissionRequestHookOutputError(
            "PermissionRequest decision.behavior must be allow or deny."
        )
    unsupported = [
        field
        for field in ("updatedInput", "updatedPermissions", "interrupt")
        if field in decision
    ]
    if unsupported:
        raise PermissionRequestHookOutputError(
            "PermissionRequest decision fields are not supported yet: "
            + ", ".join(unsupported)
            + "."
        )
    message = decision.get("message")
    if message is not None and not isinstance(message, str):
        raise PermissionRequestHookOutputError(
            "PermissionRequest decision.message must be a string."
        )
    if behavior == "allow" and message is not None:
        raise PermissionRequestHookOutputError(
            "PermissionRequest decision.message is only supported for deny."
        )
    if behavior == "deny" and (
        not isinstance(message, str) or not message.strip()
    ):
        raise PermissionRequestHookOutputError(
            "PermissionRequest deny decision requires a non-empty message."
        )
    return ParsedPermissionRequestHookOutput(
        behavior=behavior,
        message=message.strip() if isinstance(message, str) and message.strip() else None,
    )


def merge_permission_request_behavior(
    current: PermissionRequestBehavior | None,
    candidate: PermissionRequestBehavior | None,
) -> PermissionRequestBehavior | None:
    if candidate == "deny" or current == "deny":
        return "deny"
    if candidate == "allow" or current == "allow":
        return "allow"
    return None


__all__ = [
    "ParsedPermissionRequestHookOutput",
    "PermissionRequestBehavior",
    "PermissionRequestHookOutcome",
    "PermissionRequestHookOutputError",
    "merge_permission_request_behavior",
    "parse_permission_request_hook_output",
]
