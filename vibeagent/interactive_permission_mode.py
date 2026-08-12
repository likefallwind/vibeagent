from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, cast

from .cli_permission_overrides import ACCEPT_EDITS_RULES
from .types import ApprovalPolicy
from .workspace_permissions import ProjectPermissions, permission_rules_from_values


InteractivePermissionMode = Literal[
    "default",
    "acceptEdits",
    "plan",
    "bypassPermissions",
    "auto",
    "dontAsk",
    "deny",
]
INTERACTIVE_ACCEPT_EDITS_SOURCE = "<interactive permission-mode acceptEdits>"


@dataclass(frozen=True)
class InteractivePermissionState:
    mode: InteractivePermissionMode
    approval_policy: ApprovalPolicy
    permission_overrides: ProjectPermissions
    bypass_available: bool


def initial_interactive_permission_state(
    *,
    permission_mode: str | None,
    approval_policy: ApprovalPolicy,
    permission_overrides: ProjectPermissions,
    allow_bypass: bool,
) -> InteractivePermissionState:
    mode = _initial_mode(permission_mode, approval_policy)
    return InteractivePermissionState(
        mode,
        _approval_policy(mode),
        _set_accept_edits(permission_overrides, mode == "acceptEdits"),
        allow_bypass or mode == "bypassPermissions",
    )


def update_interactive_permission_state(
    state: InteractivePermissionState,
    argument: str | None,
) -> tuple[InteractivePermissionState, str]:
    if not argument:
        return state, _status_text(state)
    requested = argument.strip()
    normalized = requested.lower()
    aliases = {
        "ask": "default",
        "default": "default",
        "acceptedits": "acceptEdits",
        "allow": "bypassPermissions",
        "bypasspermissions": "bypassPermissions",
        "auto": "auto",
        "dontask": "dontAsk",
        "deny": "deny",
        "plan": "plan",
    }
    if normalized in {"next", "cycle"}:
        mode = _next_mode(state)
    elif normalized in aliases:
        mode = cast(InteractivePermissionMode, aliases[normalized])
    else:
        return state, (
            "Usage: /approval [next|default|acceptEdits|plan|auto|dontAsk|deny|"
            "bypassPermissions]"
        )
    if mode == "bypassPermissions" and not state.bypass_available:
        return state, (
            "bypassPermissions is unavailable. Restart with "
            "--allow-dangerously-skip-permissions to enable it for this session."
        )
    updated = InteractivePermissionState(
        mode,
        _approval_policy(mode),
        _set_accept_edits(state.permission_overrides, mode == "acceptEdits"),
        state.bypass_available,
    )
    return updated, _status_text(updated)


def _initial_mode(
    permission_mode: str | None,
    approval_policy: ApprovalPolicy,
) -> InteractivePermissionMode:
    if permission_mode in {
        "default",
        "acceptEdits",
        "plan",
        "auto",
        "dontAsk",
        "bypassPermissions",
    }:
        return cast(InteractivePermissionMode, permission_mode)
    return {
        "ask": "default",
        "allow": "bypassPermissions",
        "auto": "auto",
        "deny": "deny",
        "dontAsk": "dontAsk",
        "plan": "plan",
    }[approval_policy]


def _approval_policy(mode: InteractivePermissionMode) -> ApprovalPolicy:
    return {
        "default": "ask",
        "acceptEdits": "ask",
        "plan": "plan",
        "bypassPermissions": "allow",
        "auto": "auto",
        "dontAsk": "dontAsk",
        "deny": "deny",
    }[mode]


def _next_mode(state: InteractivePermissionState) -> InteractivePermissionMode:
    cycle: tuple[InteractivePermissionMode, ...] = (
        "default",
        "acceptEdits",
        "plan",
        *(("bypassPermissions",) if state.bypass_available else ()),
        "auto",
    )
    if state.mode not in cycle:
        return cycle[0]
    return cycle[(cycle.index(state.mode) + 1) % len(cycle)]


def _set_accept_edits(
    permissions: ProjectPermissions,
    enabled: bool,
) -> ProjectPermissions:
    if permissions.managed_rules_only:
        return permissions
    removed_sources = {
        INTERACTIVE_ACCEPT_EDITS_SOURCE,
        "<cli --permission-mode acceptEdits>",
    }
    rules = tuple(rule for rule in permissions.rules if rule.source not in removed_sources)
    sources = tuple(source for source in permissions.sources if source not in removed_sources)
    trusted = tuple(
        source for source in permissions.trusted_allow_sources if source not in removed_sources
    )
    if enabled:
        rules += permission_rules_from_values(
            "allow",
            ACCEPT_EDITS_RULES,
            INTERACTIVE_ACCEPT_EDITS_SOURCE,
        )
        sources += (INTERACTIVE_ACCEPT_EDITS_SOURCE,)
        trusted += (INTERACTIVE_ACCEPT_EDITS_SOURCE,)
    return ProjectPermissions(
        rules=rules,
        sources=sources,
        error=permissions.error,
        allow_rules_trusted=permissions.allow_rules_trusted,
        trusted_allow_sources=trusted,
        default_mode=permissions.default_mode,
        default_mode_source=permissions.default_mode_source,
        additional_directories=permissions.additional_directories,
        managed_rules_only=permissions.managed_rules_only,
        bypass_permissions_disabled=permissions.bypass_permissions_disabled,
        auto_mode_disabled=permissions.auto_mode_disabled,
    )


def _status_text(state: InteractivePermissionState) -> str:
    if state.mode == "acceptEdits":
        return "Permission mode: acceptEdits (edits allowed; other actions ask)"
    return f"Permission mode: {state.mode}"


__all__ = [
    "InteractivePermissionMode",
    "InteractivePermissionState",
    "initial_interactive_permission_state",
    "update_interactive_permission_state",
]
