from __future__ import annotations

from .runner_report_helpers import serialize_not_run_commands


def indent_block(value: str, spaces: int = 2) -> str:
    indent = " " * spaces
    return "\n".join(f"{indent}{line}" if line else "" for line in value.splitlines())


def serialize_suggested_check(check: object, index: int | None = None) -> dict[str, object]:
    item: dict[str, object] = {
        "command": str(getattr(check, "command", "") or ""),
        "cwd": str(getattr(check, "cwd", ".") or "."),
        "source": str(getattr(check, "source", "") or ""),
        "reason": str(getattr(check, "reason", "") or ""),
        "available": bool(getattr(check, "available", False)),
        "missingTool": getattr(check, "missing_tool", None),
    }
    if index is not None:
        item["index"] = index
    return item


def serialize_not_run_suggested_checks(
    checks: list[object],
    ran_count: int,
    stopped_early: bool,
) -> dict[str, object]:
    return serialize_not_run_commands(
        checks,
        ran_count=ran_count,
        stopped_early=stopped_early,
        item_key="commands",
        serialize_item=serialize_suggested_check,
    )


def serialize_focused_test_command(command: object, index: int | None = None) -> dict[str, object]:
    item: dict[str, object] = {
        "command": str(getattr(command, "command", "") or ""),
        "cwd": str(getattr(command, "cwd", ".") or "."),
        "test": str(getattr(command, "test_path", "") or ""),
        "source": str(getattr(command, "source", "") or ""),
        "reason": str(getattr(command, "reason", "") or ""),
        "available": bool(getattr(command, "available", False)),
        "missingTool": getattr(command, "missing_tool", None),
    }
    if index is not None:
        item["index"] = index
    return item


def serialize_not_run_focused_test_commands(
    commands: list[object],
    ran_count: int,
    stopped_early: bool,
) -> dict[str, object]:
    return serialize_not_run_commands(
        commands,
        ran_count=ran_count,
        stopped_early=stopped_early,
        item_key="items",
        serialize_item=serialize_focused_test_command,
    )


def format_structured_command_checks(checks: list[dict[str, object]], spaces: int = 2) -> list[str]:
    if not checks:
        return [f"{' ' * spaces}checks: none"]
    prefix = " " * spaces
    child = " " * (spaces + 2)
    lines = [f"{prefix}checks:"]
    for position, check in enumerate(checks, start=1):
        index = check.get("index", position)
        lines.extend(
            [
                f"{child}- index: {index}",
                f"{child}  command: {check.get('command') or ''}",
                f"{child}  cwd: {check.get('cwd') or '.'}",
                f"{child}  ok: {'yes' if bool(check.get('ok')) else 'no'}",
                f"{child}  cwdOk: {'yes' if bool(check.get('cwdOk')) else 'no'}",
                f"{child}  blocked: {'yes' if bool(check.get('blocked')) else 'no'}",
                f"{child}  executableAvailable: {'yes' if bool(check.get('executableAvailable')) else 'no'}",
            ]
        )
        if check.get("blockReason"):
            lines.append(f"{child}  blockReason: {check.get('blockReason')}")
        if check.get("missingTool"):
            lines.append(f"{child}  missingTool: {check.get('missingTool')}")
        lines.append(f"{child}  message: {check.get('message') or ''}")
    return lines
