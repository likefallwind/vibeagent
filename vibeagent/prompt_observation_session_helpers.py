from __future__ import annotations

from .session_completion_detail_fields import completion_detail_prompt_lines


def format_verification_command_lines(label: str, commands: list[dict[str, object]], total: int) -> list[str]:
    if not commands:
        return [f"{label}: none"]
    lines = [f"{label}: {len(commands)}/{total}"]
    for command in commands:
        cwd = str(command.get("cwd") or ".")
        suffix = "" if cwd == "." else f" (cwd: {cwd})"
        reason = command.get("failureReason")
        reason_suffix = f" ({reason})" if isinstance(reason, str) and reason else ""
        lines.append(f"- {command.get('command') or ''}{suffix}{reason_suffix}")
    return lines


def format_selected_session_verification_command_lines(
    commands: list[dict[str, object]],
    total: int,
    ran_count: int,
    stopped_early: bool,
) -> list[str]:
    if not commands:
        return ["selectedCommands: none"]
    lines = [f"selectedCommands: {len(commands)}/{total}"]
    for index, command in enumerate(commands):
        cwd = str(command.get("cwd") or ".")
        cwd_suffix = "" if cwd == "." else f" (cwd: {cwd})"
        run_status = "ran" if index < ran_count else "notRun"
        reason = command.get("failureReason")
        reason_suffix = f" ({reason})" if isinstance(reason, str) and reason else ""
        status = str(command.get("status") or "").strip()
        status_suffix = f" source={status}" if status else ""
        lines.append(f"- {command.get('command') or ''}{cwd_suffix} [{run_status}{status_suffix}]{reason_suffix}")
    if stopped_early and len(commands) > ran_count:
        lines.append(f"selectedCommandsNotRun: {len(commands) - ran_count}")
    return lines


def format_file_reference_lines(
    references: object,
    file_count: int,
    shown_file_count: int,
    files_truncated: bool,
) -> list[str]:
    file_references = [
        item
        for item in references
        if isinstance(item, dict) and str(item.get("path") or "").strip()
    ] if isinstance(references, list) else []
    file_lines: list[str] = []
    if file_count or file_references:
        file_lines.append(f"files: {shown_file_count}/{file_count} truncated={str(files_truncated).lower()}")
        for item in file_references[:20]:
            path = str(item.get("path") or "").strip()
            uses = [
                str(use).strip()
                for use in item.get("uses", [])
                if isinstance(use, str) and str(use).strip()
            ]
            suffix = f" uses={','.join(uses)}" if uses else ""
            file_lines.append(f"file: {path}{suffix}")
    return file_lines


def format_subagent_failure_lines(observation: object) -> list[str]:
    failures = [
        str(failure).strip()
        for failure in getattr(observation, "latest_subagent_failures", [])
        if str(failure).strip()
    ]
    return [f"latestSubagentFailure: {failure}" for failure in failures[:20]]


def format_completion_recovery_lines(observation: object, *, include_ready: bool = True) -> list[str]:
    lines: list[str] = []
    completion_ready = getattr(observation, "completion_ready", None)
    if include_ready and completion_ready is not None:
        lines.append(f"completionReady: {str(completion_ready).lower()}")
    lines.extend(
        f"completionBlocker: {blocker}"
        for blocker in getattr(observation, "completion_blockers", [])[:20]
    )
    lines.extend(
        f"latestCompletionBlocker: {blocker}"
        for blocker in getattr(observation, "latest_completion_blockers", [])[:20]
    )
    lines.extend(completion_detail_prompt_lines(observation))
    return lines


__all__ = [
    "format_completion_recovery_lines",
    "format_file_reference_lines",
    "format_selected_session_verification_command_lines",
    "format_subagent_failure_lines",
    "format_verification_command_lines",
]
