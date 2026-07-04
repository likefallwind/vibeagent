from __future__ import annotations

from typing import Iterable


def command_target(command: str, cwd: str | None) -> str:
    return f"{command} (cwd: {cwd or '.'})"


def command_batch_target(commands: Iterable[object]) -> str:
    targets = []
    for item in commands:
        command = str(getattr(item, "command", "") or "").strip()
        if not command:
            continue
        targets.append(command_target(command, str(getattr(item, "cwd", ".") or ".")))
    return ", ".join(targets)


def suggested_checks_target(max_commands: int) -> str:
    return f"up to {max_commands} suggested check command(s)"


def focused_test_commands_target(max_commands: int) -> str:
    return f"up to {max_commands} focused test command(s)"


def session_verification_target(run_id: str | None, include_failed: bool, include_pending: bool) -> str:
    groups = session_verification_groups(include_failed, include_pending)
    return f"{'/'.join(groups)} verification command(s) from {run_id or 'current session'}"


def session_verification_groups(include_failed: bool, include_pending: bool) -> list[str]:
    groups = []
    if include_failed:
        groups.append("failed")
    if include_pending:
        groups.append("pending")
    return groups
