from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Literal

from .agent_hook_results import HookRunResult


PermissionRequestBehavior = Literal["allow", "deny"]
MAX_PERMISSION_UPDATE_ENTRIES = 50
MAX_PERMISSION_UPDATE_RULES = 200
MAX_PERMISSION_UPDATE_DIRECTORIES = 20
MAX_PERMISSION_UPDATE_STRING_CHARS = 1_000
PERMISSION_UPDATE_DESTINATIONS = frozenset(
    {"session", "localSettings", "projectSettings", "userSettings"}
)
PERMISSION_UPDATE_MODES = frozenset(
    {
        "default",
        "manual",
        "auto",
        "acceptEdits",
        "dontAsk",
        "bypassPermissions",
        "plan",
    }
)


@dataclass(frozen=True)
class ParsedPermissionRequestHookOutput:
    behavior: PermissionRequestBehavior | None = None
    message: str | None = None
    updated_input: dict[str, object] | None = None
    updated_permissions: tuple[dict[str, object], ...] = ()
    interrupt: bool = False


@dataclass(frozen=True)
class PermissionRequestHookOutcome:
    behavior: PermissionRequestBehavior | None = None
    message: str | None = None
    results: tuple[HookRunResult, ...] = ()
    updated_input: dict[str, object] | None = None
    updated_permissions: tuple[dict[str, object], ...] = ()
    interrupt: bool = False


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
    updated_input = decision.get("updatedInput")
    updated_permissions = decision.get("updatedPermissions")
    interrupt = decision.get("interrupt", False)
    if behavior == "deny":
        if updated_input is not None or updated_permissions is not None:
            raise PermissionRequestHookOutputError(
                "PermissionRequest deny decision cannot update input or permissions."
            )
        if not isinstance(interrupt, bool):
            raise PermissionRequestHookOutputError(
                "PermissionRequest decision.interrupt must be a boolean."
            )
    else:
        if "interrupt" in decision:
            raise PermissionRequestHookOutputError(
                "PermissionRequest decision.interrupt is only supported for deny."
            )
        if updated_input is not None and not isinstance(updated_input, dict):
            raise PermissionRequestHookOutputError(
                "PermissionRequest decision.updatedInput must be an object."
            )
    normalized_permissions = (
        _parse_permission_updates(updated_permissions)
        if updated_permissions is not None
        else ()
    )
    return ParsedPermissionRequestHookOutput(
        behavior=behavior,
        message=message.strip() if isinstance(message, str) and message.strip() else None,
        updated_input=dict(updated_input) if isinstance(updated_input, dict) else None,
        updated_permissions=normalized_permissions,
        interrupt=interrupt,
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


def _parse_permission_updates(value: object) -> tuple[dict[str, object], ...]:
    if not isinstance(value, list):
        raise PermissionRequestHookOutputError(
            "PermissionRequest decision.updatedPermissions must be an array."
        )
    if len(value) > MAX_PERMISSION_UPDATE_ENTRIES:
        raise PermissionRequestHookOutputError(
            f"PermissionRequest updatedPermissions exceeds {MAX_PERMISSION_UPDATE_ENTRIES} entries."
        )
    return tuple(_parse_permission_update_entry(entry) for entry in value)


def _parse_permission_update_entry(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise PermissionRequestHookOutputError(
            "PermissionRequest permission update entries must be objects."
        )
    entry_type = value.get("type")
    destination = value.get("destination")
    if entry_type not in {
        "addRules",
        "replaceRules",
        "removeRules",
        "setMode",
        "addDirectories",
        "removeDirectories",
    }:
        raise PermissionRequestHookOutputError(
            "PermissionRequest permission update type is invalid."
        )
    if destination not in PERMISSION_UPDATE_DESTINATIONS:
        raise PermissionRequestHookOutputError(
            "PermissionRequest permission update destination is invalid."
        )
    if entry_type in {"addRules", "replaceRules", "removeRules"}:
        return _parse_rule_update(value, entry_type, destination)
    if entry_type == "setMode":
        mode = value.get("mode")
        if mode not in PERMISSION_UPDATE_MODES:
            raise PermissionRequestHookOutputError(
                "PermissionRequest setMode mode is invalid."
            )
        return {"type": entry_type, "mode": mode, "destination": destination}
    directories = value.get("directories")
    if not isinstance(directories, list) or len(directories) > MAX_PERMISSION_UPDATE_DIRECTORIES:
        raise PermissionRequestHookOutputError(
            f"PermissionRequest {entry_type} directories must be an array of at most "
            f"{MAX_PERMISSION_UPDATE_DIRECTORIES} paths."
        )
    normalized_directories = [
        _bounded_string(path, f"PermissionRequest {entry_type} directory")
        for path in directories
    ]
    return {
        "type": entry_type,
        "directories": normalized_directories,
        "destination": destination,
    }


def _parse_rule_update(
    value: dict[str, object],
    entry_type: str,
    destination: object,
) -> dict[str, object]:
    behavior = value.get("behavior")
    if behavior not in {"allow", "deny", "ask"}:
        raise PermissionRequestHookOutputError(
            f"PermissionRequest {entry_type} behavior is invalid."
        )
    rules = value.get("rules")
    if not isinstance(rules, list) or len(rules) > MAX_PERMISSION_UPDATE_RULES:
        raise PermissionRequestHookOutputError(
            f"PermissionRequest {entry_type} rules must be an array of at most "
            f"{MAX_PERMISSION_UPDATE_RULES} entries."
        )
    normalized_rules: list[dict[str, object]] = []
    for rule in rules:
        if not isinstance(rule, dict):
            raise PermissionRequestHookOutputError(
                f"PermissionRequest {entry_type} rules must be objects."
            )
        tool_name = _bounded_string(
            rule.get("toolName"), f"PermissionRequest {entry_type} toolName"
        )
        normalized: dict[str, object] = {"toolName": tool_name}
        if "ruleContent" in rule:
            normalized["ruleContent"] = _bounded_string(
                rule.get("ruleContent"),
                f"PermissionRequest {entry_type} ruleContent",
                allow_empty=True,
            )
        normalized_rules.append(normalized)
    return {
        "type": entry_type,
        "rules": normalized_rules,
        "behavior": behavior,
        "destination": destination,
    }


def _bounded_string(value: object, label: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise PermissionRequestHookOutputError(f"{label} must be a string.")
    normalized = value.strip()
    if (not normalized and not allow_empty) or len(normalized) > MAX_PERMISSION_UPDATE_STRING_CHARS:
        raise PermissionRequestHookOutputError(
            f"{label} must contain {'0' if allow_empty else '1'}-"
            f"{MAX_PERMISSION_UPDATE_STRING_CHARS} characters."
        )
    return normalized


__all__ = [
    "ParsedPermissionRequestHookOutput",
    "PermissionRequestBehavior",
    "PermissionRequestHookOutcome",
    "PermissionRequestHookOutputError",
    "merge_permission_request_behavior",
    "parse_permission_request_hook_output",
]
