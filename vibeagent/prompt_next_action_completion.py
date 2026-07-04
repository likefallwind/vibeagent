from __future__ import annotations

from .types import Observation


COMPLETION_NEXT_ACTION_KINDS = {
    "final_review",
    "finish",
    "update_plan",
}


def _format_next_action_items(items: list[str], max_items: int = 3) -> str:
    shown = items[:max_items]
    suffix = "" if len(items) <= max_items else f"; +{len(items) - max_items} more"
    return "; ".join(shown) + suffix


def _observation_commands(values: object) -> list[str]:
    commands: list[str] = []
    if not isinstance(values, list):
        return commands
    for value in values:
        command = str(getattr(value, "command", "") or "").strip()
        if command:
            commands.append(command)
    return commands


def _running_process_labels(values: object) -> list[str]:
    labels: list[str] = []
    if not isinstance(values, list):
        return labels
    for value in values:
        if not getattr(value, "running", False):
            continue
        process_id = str(getattr(value, "process_id", "") or "").strip()
        command = str(getattr(value, "command", "") or "").strip()
        if process_id and command:
            labels.append(f"{process_id}: {command}")
        elif process_id:
            labels.append(process_id)
        elif command:
            labels.append(command)
    return labels


def _final_review_next_action_instruction(base: str, latest: Observation) -> str:
    if getattr(latest, "ready", None) is not False:
        return f"{base} Use the final review report to decide whether to run verification, continue, or answer directly."

    running_processes = _running_process_labels(getattr(latest, "running_processes", []))
    if running_processes:
        return (
            f"{base} Final review is not ready because background processes are still running. "
            f"Inspect with list_processes or read_process if needed, then stop_process or stop_all_processes for: "
            f"{_format_next_action_items(running_processes)}. Rerun final_review before finishing."
        )

    focused_commands = _observation_commands(getattr(latest, "focused_test_commands", []))
    suggested_commands = _observation_commands(getattr(latest, "suggested_checks", []))
    if focused_commands and suggested_commands:
        return (
            f"{base} Final review is not ready and lists focused and suggested verification checks. "
            f"Run run_focused_test_commands or run_command first for: {_format_next_action_items(focused_commands)}. "
            f"Then run run_suggested_checks or run_command for broader checks: {_format_next_action_items(suggested_commands)}. "
            "Fix failures before finishing."
        )

    if suggested_commands:
        return (
            f"{base} Final review is not ready and lists suggested verification checks. "
            f"Run run_suggested_checks or run_command for: {_format_next_action_items(suggested_commands)}. "
            "Fix failures before finishing."
        )

    if focused_commands:
        return (
            f"{base} Final review is not ready and lists focused verification checks. "
            f"Run run_focused_test_commands or run_command for: {_format_next_action_items(focused_commands)}. "
            "Fix failures before finishing."
        )

    issues = [str(issue).strip() for issue in getattr(latest, "blocking_issues", []) if str(issue).strip()]
    if issues:
        return (
            f"{base} Final review is not ready. "
            f"Fix final review blocking issue(s) before finishing: {_format_next_action_items(issues)}."
        )

    return f"{base} Final review is not ready. Inspect its warnings and changed files, fix blockers, then rerun final_review before finishing."


def _finish_next_action_instruction(base: str, latest: Observation) -> str:
    message = str(getattr(latest, "message", "") or "").strip()
    suffix = f" Last finish message: {message}" if message else ""
    return (
        f"{base} Finish was attempted.{suffix} "
        "If completion feedback reports blockers, do not finish again unchanged; resolve the blockers with the required tools, "
        "rerun final_review or verification when relevant, then finish only after completion is ready."
    )


def completion_next_action_instruction(base: str, latest: Observation) -> str:
    if latest.kind == "final_review":
        return _final_review_next_action_instruction(base, latest)
    if latest.kind == "finish":
        return _finish_next_action_instruction(base, latest)
    if latest.kind == "update_plan":
        return f"{base} Continue with the current in-progress plan item, or update the plan again if the work changed."

    raise ValueError(f"Unsupported completion next-action kind: {latest.kind}")
