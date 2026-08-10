from __future__ import annotations

from .types import ApprovalPolicy
from .tool_catalog_core import APPROVAL_REQUIRED_TOOL_NAMES
from .workspace_permissions import (
    ProjectPermissions,
    merge_project_permissions,
    permission_rules_from_values,
)


PROFILE_ACCEPT_EDITS_SOURCE = "<agent permissionMode acceptEdits>"
PROFILE_ACCEPT_EDITS_RULES = ("Write", "Edit", "MultiEdit", "NotebookEdit")
PROFILE_BYPASS_SOURCE = "<agent permissionMode bypassPermissions>"


def apply_agent_permission_mode(
    parent_policy: ApprovalPolicy,
    permissions: ProjectPermissions,
    permission_mode: str | None,
) -> tuple[ApprovalPolicy, ProjectPermissions]:
    if permission_mode is None or parent_policy in {"allow", "plan"}:
        return parent_policy, permissions
    if _parent_has_strong_mode(permissions):
        return parent_policy, permissions
    if permission_mode == "default":
        return "ask", permissions
    if permission_mode == "acceptEdits":
        rules = permission_rules_from_values(
            "allow",
            PROFILE_ACCEPT_EDITS_RULES,
            PROFILE_ACCEPT_EDITS_SOURCE,
        )
        overrides = ProjectPermissions(
            rules=rules,
            sources=(PROFILE_ACCEPT_EDITS_SOURCE,),
            trusted_allow_sources=(PROFILE_ACCEPT_EDITS_SOURCE,),
        )
        return "ask", merge_project_permissions(permissions, overrides)
    if permission_mode == "bypassPermissions":
        rules = permission_rules_from_values(
            "allow",
            tuple(sorted(APPROVAL_REQUIRED_TOOL_NAMES)),
            PROFILE_BYPASS_SOURCE,
        )
        overrides = ProjectPermissions(
            rules=rules,
            sources=(PROFILE_BYPASS_SOURCE,),
            trusted_allow_sources=(PROFILE_BYPASS_SOURCE,),
        )
        return "ask", merge_project_permissions(permissions, overrides)
    if permission_mode == "plan":
        return "plan", permissions
    if permission_mode in {"auto", "dontAsk"}:
        return "dontAsk", permissions
    raise ValueError(f"Unsupported agent permission mode: {permission_mode}.")


def permission_mode_forces_plan(
    parent_policy: ApprovalPolicy,
    permissions: ProjectPermissions,
    permission_mode: str | None,
) -> bool:
    return (
        permission_mode == "plan"
        and parent_policy not in {"allow", "plan"}
        and not _parent_has_strong_mode(permissions)
    )


def _parent_has_strong_mode(permissions: ProjectPermissions) -> bool:
    return any(
        source.endswith("permission-mode acceptEdits>")
        or source == PROFILE_ACCEPT_EDITS_SOURCE
        or source == PROFILE_BYPASS_SOURCE
        for source in permissions.trusted_allow_sources
    )


__all__ = [
    "PROFILE_ACCEPT_EDITS_RULES",
    "PROFILE_ACCEPT_EDITS_SOURCE",
    "PROFILE_BYPASS_SOURCE",
    "apply_agent_permission_mode",
    "permission_mode_forces_plan",
]
