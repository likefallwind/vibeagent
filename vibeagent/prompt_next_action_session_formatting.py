from __future__ import annotations

from .session_completion_detail_fields import completion_blocker_detail_values
from .types import Observation


def format_next_action_items(items: list[str], max_items: int = 3) -> str:
    shown = items[:max_items]
    suffix = "" if len(items) <= max_items else f"; +{len(items) - max_items} more"
    return "; ".join(shown) + suffix


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


def audit_section_items(audit: object, section_names: tuple[str, ...]) -> list[str]:
    if not isinstance(audit, str):
        return []

    names = set(section_names)
    items: list[str] = []
    in_section = False
    for line in audit.splitlines():
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
    return audit_section_items(
        getattr(latest, "audit", ""),
        ("completionBlockers", "latestCompletionBlockers"),
    )


def has_completion_blocker_signal(blockers: list[str], latest: Observation) -> bool:
    if getattr(latest, "completion_ready", None) is False:
        return True
    if completion_blocker_labels(latest):
        return True
    if any("completion blocker" in blocker.lower() or "completion is not ready" in blocker.lower() for blocker in blockers):
        return True
    audit_lower = str(getattr(latest, "audit", "") or "").lower()
    return "completionready: no" in audit_lower or "completionblockers:" in audit_lower
