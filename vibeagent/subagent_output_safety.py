from __future__ import annotations

from dataclasses import dataclass
import re


_MARKER_PREFIX = "[harness: subagent output matched instruction-shaped pattern(s):"
_SYSTEM_TAG_PATTERN = re.compile(
    r"(?i)(?<!\\)<(?=/?(?:system-reminder|system[_-]message|system|instructions?)(?:\s|>))"
)
_ROLE_PREFIX_PATTERN = re.compile(r"(?im)^(?P<indent>[ \t]*)(?P<role>Human|Assistant|System|User):")
_HARNESS_PREFIX_PATTERN = re.compile(r"(?im)^(?P<indent>[ \t]*)\[harness:")
_PERMISSION_PATTERN = re.compile(
    r"(?i)(?:\bbypassPermissions\b|\bpermissionMode\b|--dangerously-skip-permissions\b)"
)
_OVERRIDE_PATTERN = re.compile(
    r"(?i)\b(?:ignore|disregard|override)\s+(?:all\s+)?(?:previous|prior|system|developer)\s+instructions?\b"
)


@dataclass(frozen=True)
class SubagentOutputScan:
    text: str
    matches: tuple[str, ...] = ()


def scan_subagent_output(value: str) -> SubagentOutputScan:
    if not value:
        return SubagentOutputScan(text=value)

    matches: set[str] = set()
    sanitized = value
    if _SYSTEM_TAG_PATTERN.search(sanitized):
        matches.add("system-tag")
        sanitized = _SYSTEM_TAG_PATTERN.sub(r"\\<", sanitized)
    if _ROLE_PREFIX_PATTERN.search(sanitized):
        matches.add("role-prefix")
        sanitized = _ROLE_PREFIX_PATTERN.sub(
            lambda match: f"{match.group('indent')}\\{match.group('role')}:",
            sanitized,
        )
    if _HARNESS_PREFIX_PATTERN.search(sanitized):
        matches.add("harness-marker")
        sanitized = _HARNESS_PREFIX_PATTERN.sub(
            lambda match: f"{match.group('indent')}\\[harness:",
            sanitized,
        )
    if _PERMISSION_PATTERN.search(value):
        matches.add("permission-setting")
    if _OVERRIDE_PATTERN.search(value):
        matches.add("instruction-override")

    ordered = tuple(sorted(matches))
    if not ordered:
        return SubagentOutputScan(text=value)
    marker = f"{_MARKER_PREFIX} {', '.join(ordered)}]"
    return SubagentOutputScan(text=f"{marker}\n{sanitized}", matches=ordered)


__all__ = ["SubagentOutputScan", "scan_subagent_output"]
