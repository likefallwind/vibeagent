from __future__ import annotations

import re

from .session_completion_detail_fields import completion_blocker_detail_values
from .types import Observation


_MARKDOWN_CHECKBOX_PATTERN = re.compile(r"^(?:[-*+]|\d+[.)])\s+\[([ x])\]")
_UNICODE_CHECKBOX_PATTERN = re.compile(r"^(?:(?:[-*+]|\d+[.)])\s+)?([☐☑☒✅])(?:\s|$)")


def format_next_action_items(items: list[str], max_items: int = 3) -> str:
    shown = items[:max_items]
    suffix = "" if len(items) <= max_items else f"; +{len(items) - max_items} more"
    return "; ".join(shown) + suffix


def text_reports_ready(text: object) -> bool:
    lowered = str(text or "").lower()
    return "ready: yes" in lowered or "status: ready" in lowered


def _session_plan_lines(plan: object) -> list[str]:
    return [line.strip().lower() for line in str(plan or "").splitlines() if line.strip()]


def _session_plan_checkbox_states(plan: object) -> list[str]:
    states: list[str] = []
    for line in _session_plan_lines(plan):
        markdown_match = _MARKDOWN_CHECKBOX_PATTERN.match(line)
        if markdown_match:
            states.append(markdown_match.group(1))
            continue
        unicode_match = _UNICODE_CHECKBOX_PATTERN.match(line)
        if unicode_match:
            states.append(" " if unicode_match.group(1) == "☐" else "x")
    return states


def session_plan_has_unfinished_work(plan: object) -> bool:
    if " " in _session_plan_checkbox_states(plan):
        return True
    plan_lower = str(plan or "").lower()
    unfinished_markers = (
        "in_progress",
        "in progress",
        "pending",
        "todo",
        "to do",
        "to-do",
        "not started",
        "not complete",
        "not completed",
        "incomplete",
        "not done",
        "undone",
        "blocked",
    )
    return any(marker in plan_lower for marker in unfinished_markers)


def session_plan_appears_complete(plan: object) -> bool:
    if session_plan_has_unfinished_work(plan):
        return False
    if "x" in _session_plan_checkbox_states(plan):
        return True
    plan_lower = str(plan or "").lower()
    complete_markers = ("completed", "complete", "done")
    return any(marker in plan_lower for marker in complete_markers)


def session_audit_process_labels(values: object) -> list[str]:
    labels: list[str] = []
    if not isinstance(values, list):
        return labels
    for value in values:
        process_id = str(getattr(value, "process_id", "") or "").strip()
        command = str(getattr(value, "command", "") or "").strip()
        cwd = str(getattr(value, "cwd", "") or "").strip()
        if process_id and command:
            label = f"{process_id}: {command}"
        elif process_id:
            label = process_id
        elif command:
            label = command
        else:
            continue
        if cwd and cwd != ".":
            label = f"{label} (cwd={cwd})"
        labels.append(label)
    return labels


def verification_command_labels(values: object) -> list[str]:
    labels: list[str] = []
    if not isinstance(values, list):
        return labels
    for value in values:
        if not isinstance(value, dict):
            continue
        command = str(value.get("command") or "").strip()
        cwd = str(value.get("cwd") or ".").strip() or "."
        reason = str(value.get("failureReason") or "").strip()
        if not command:
            continue
        label = f"{command} (cwd={cwd})"
        if reason:
            label = f"{label}: {reason}"
        labels.append(label)
    return labels


def plan_item_labels(values: object) -> list[str]:
    labels: list[str] = []
    if not isinstance(values, list):
        return labels
    for value in values:
        if not isinstance(value, dict):
            continue
        step = str(value.get("step") or "").strip()
        if not step:
            continue
        status = str(value.get("status") or "").strip()
        labels.append(f"{status}: {step}" if status else step)
    return labels


def file_reference_labels(values: object) -> list[str]:
    labels: list[str] = []
    if not isinstance(values, list):
        return labels
    for value in values:
        if not isinstance(value, dict):
            continue
        path = str(value.get("path") or "").strip()
        if not path:
            continue
        uses = [
            str(use).strip()
            for use in value.get("uses", [])
            if isinstance(use, str) and use.strip()
        ]
        labels.append(f"{path} (uses: {', '.join(uses)})" if uses else path)
    return labels


def text_section_items(text: object, section_names: tuple[str, ...]) -> list[str]:
    if not isinstance(text, str):
        return []

    names = set(section_names)
    items: list[str] = []
    in_section = False
    for line in text.splitlines():
        stripped = line.strip()
        heading = stripped[:-1] if stripped.endswith(":") else stripped
        if heading in names:
            in_section = True
            continue
        if not in_section:
            continue
        if not stripped:
            continue
        if stripped.startswith("- "):
            item = stripped[2:].strip()
            if item and item.lower() != "none":
                items.append(item)
            continue
        in_section = False
    return items


def audit_section_items(audit: object, section_names: tuple[str, ...]) -> list[str]:
    return text_section_items(audit, section_names)


def completion_blocker_labels(latest: Observation) -> list[str]:
    labels = [
        str(blocker).strip()
        for blocker in getattr(latest, "completion_blockers", [])
        if str(blocker).strip()
    ]
    labels.extend(
        str(blocker).strip()
        for blocker in getattr(latest, "latest_completion_blockers", [])
        if str(blocker).strip()
    )
    labels.extend(completion_blocker_detail_values(latest))
    if labels:
        return labels
    for attr in ("audit", "handoff", "summary"):
        labels = text_section_items(
            getattr(latest, attr, ""),
            ("completionBlockers", "latestCompletionBlockers"),
        )
        if labels:
            return labels
    return []


def completion_next_action_labels(latest: Observation) -> list[str]:
    labels = [
        str(action).strip()
        for action in getattr(latest, "latest_completion_next_actions", [])
        if str(action).strip()
    ]
    if labels:
        return labels
    for attr in ("audit", "handoff", "summary"):
        labels = text_section_items(
            getattr(latest, attr, ""),
            ("latestCompletionNextActions",),
        )
        if labels:
            return labels
    return []


def has_completion_blocker_signal(blockers: list[str], latest: Observation) -> bool:
    if getattr(latest, "completion_ready", None) is False:
        return True
    if completion_blocker_labels(latest):
        return True
    if any("completion blocker" in blocker.lower() or "completion is not ready" in blocker.lower() for blocker in blockers):
        return True
    audit_lower = str(getattr(latest, "audit", "") or "").lower()
    return "completionready: no" in audit_lower or "completionblockers:" in audit_lower
