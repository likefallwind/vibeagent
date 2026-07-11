from __future__ import annotations

import argparse

from .workspace_permissions import ProjectPermissions, permission_rules_from_values


ALLOWED_TOOLS_SOURCE = "<cli --allowed-tools>"
DISALLOWED_TOOLS_SOURCE = "<cli --disallowed-tools>"


def add_permission_override_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--allowed-tools",
        "--allowedTools",
        action="append",
        default=[],
        metavar="RULE",
        help="Allow one Claude-style tool permission rule for this one-shot run, for example Read or Bash(git diff:*).",
    )
    parser.add_argument(
        "--disallowed-tools",
        "--disallowedTools",
        action="append",
        default=[],
        metavar="RULE",
        help="Deny one Claude-style tool permission rule for this one-shot run, for example Edit or Bash(git push:*).",
    )


def build_permission_overrides(args: argparse.Namespace) -> ProjectPermissions:
    allowed = _split_rule_values(getattr(args, "allowed_tools", []))
    disallowed = _split_rule_values(getattr(args, "disallowed_tools", []))
    rules = permission_rules_from_values("allow", allowed, ALLOWED_TOOLS_SOURCE) + permission_rules_from_values(
        "deny",
        disallowed,
        DISALLOWED_TOOLS_SOURCE,
    )
    sources = []
    if allowed:
        sources.append(ALLOWED_TOOLS_SOURCE)
    if disallowed:
        sources.append(DISALLOWED_TOOLS_SOURCE)
    return ProjectPermissions(
        rules=rules,
        sources=tuple(sources),
        trusted_allow_sources=(ALLOWED_TOOLS_SOURCE,) if allowed else (),
    )


def permission_override_validation_error(args: argparse.Namespace) -> str | None:
    try:
        build_permission_overrides(args)
    except ValueError as error:
        return str(error)
    return None


def has_permission_overrides(args: argparse.Namespace) -> bool:
    return bool(getattr(args, "allowed_tools", []) or getattr(args, "disallowed_tools", []))


def _split_rule_values(values: list[str] | tuple[str, ...]) -> list[str]:
    rules: list[str] = []
    for value in values:
        rules.extend(part.strip() for part in value.split(",") if part.strip())
    return rules


__all__ = [
    "ALLOWED_TOOLS_SOURCE",
    "DISALLOWED_TOOLS_SOURCE",
    "add_permission_override_arguments",
    "build_permission_overrides",
    "has_permission_overrides",
    "permission_override_validation_error",
]
