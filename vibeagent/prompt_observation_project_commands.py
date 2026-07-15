from __future__ import annotations


COMMAND_OBSERVATION_KINDS = {
    "suggest_checks",
    "check_suggested_checks",
    "project_commands",
    "focused_test_commands",
    "check_focused_test_commands",
}


def format_project_command_observation(index: int, observation: object) -> str | None:
    if observation.kind == "suggest_checks":
        return format_suggest_checks(index, observation)
    if observation.kind == "check_suggested_checks":
        return format_check_suggested_checks(index, observation)
    if observation.kind == "project_commands":
        return format_project_commands(index, observation)
    if observation.kind == "focused_test_commands":
        return format_focused_test_commands(index, observation)
    if observation.kind == "check_focused_test_commands":
        return format_check_focused_test_commands(index, observation)
    return None


def format_command_metadata(
    label: str,
    command: object,
    extra_fields: list[tuple[str, object]],
    pre_availability_fields: list[tuple[str, object]] | None = None,
) -> str:
    parts = [
        f"{label}:",
        f"cwd={getattr(command, 'cwd')}",
        f"command={getattr(command, 'command')}",
    ]
    if pre_availability_fields:
        parts.extend(f"{name}={value}" for name, value in pre_availability_fields)
    parts.extend(
        [
            f"available={str(getattr(command, 'available')).lower()}",
            f"missingTool={getattr(command, 'missing_tool') or '.'}",
        ]
    )
    parts.extend(f"{name}={value}" for name, value in extra_fields)
    return " ".join(parts)


def format_suggest_checks(index: int, observation: object) -> str:
    parts = [
        (
            f"{index}. suggest_checks: {observation.message} "
            f"shown={len(observation.checks)}/{observation.total} "
            f"truncated={str(observation.truncated).lower()}"
        )
    ]
    for check in observation.checks:
        parts.append(format_command_metadata("check", check, [("source", check.source), ("reason", check.reason)]))
    if observation.changed_files:
        parts.append("changed_files:\n" + "\n".join(observation.changed_files[:120]))
    return "\n".join(parts)


def format_check_suggested_checks(index: int, observation: object) -> str:
    parts = [
        (
            f"{index}. check_suggested_checks: {observation.message} "
            f"shown={len(observation.checks)}/{observation.total} "
            f"truncated={str(observation.truncated).lower()}"
        ),
        f"ok: {str(observation.ok).lower()}",
    ]
    for check in observation.checks:
        parts.extend(
            [
                f"command: {check.command}",
                f"cwd: {check.cwd}",
                f"ok: {str(check.ok).lower()} cwdOk={str(check.cwd_ok).lower()} blocked={str(check.blocked).lower()} executableAvailable={str(check.executable_available).lower()}",
                f"blockReason: {check.block_reason or 'none'} missingTool={check.missing_tool or 'none'} message={check.message}",
            ]
        )
    return "\n".join(parts)


def format_project_commands(index: int, observation: object) -> str:
    parts = [
        (
            f"{index}. project_commands: {observation.message} "
            f"shown={len(observation.commands)}/{observation.total} "
            f"files={observation.scanned_files}/{observation.total_files} "
            f"truncated={str(observation.truncated).lower()}"
        )
    ]
    for command in observation.commands:
        parts.append(
            format_command_metadata(
                "command",
                command,
                [("source", command.source), ("file", command.file), ("detail", command.detail)],
            )
        )
    return "\n".join(parts)


def format_focused_test_commands(index: int, observation: object) -> str:
    parts = [
        (
            f"{index}. focused_test_commands: {observation.message} "
            f"ok={str(observation.ok).lower()} "
            f"targets={len(observation.target_paths)} "
            f"shown={len(observation.commands)}/{observation.total} "
            f"relatedTests={observation.related_tests_total} "
            f"truncated={str(observation.truncated).lower()}"
        )
    ]
    if observation.target_paths:
        parts.append("target_paths:\n" + "\n".join(observation.target_paths[:120]))
    for command in observation.commands:
        parts.append(
            format_command_metadata(
                "command",
                command,
                [("source", command.source), ("reason", command.reason)],
                pre_availability_fields=[("test", command.test_path)],
            )
        )
    return "\n".join(parts)


def format_check_focused_test_commands(index: int, observation: object) -> str:
    parts = [
        (
            f"{index}. check_focused_test_commands: {observation.message} "
            f"ok={str(observation.ok).lower()} "
            f"targets={len(observation.target_paths)} "
            f"shown={len(observation.focused_commands)}/{observation.total} "
            f"relatedTests={observation.related_tests_total} "
            f"truncated={str(observation.truncated).lower()}"
        )
    ]
    if observation.target_paths:
        parts.append("target_paths:\n" + "\n".join(observation.target_paths[:120]))
    for command, check in zip(observation.focused_commands, observation.checks, strict=False):
        parts.extend(
            [
                f"command: {command.command}",
                f"cwd: {command.cwd}",
                f"test: {command.test_path}",
                f"available: {str(command.available).lower()} missingTool={command.missing_tool or 'none'} source={command.source} reason={command.reason}",
                f"ok: {str(check.ok).lower()} cwdOk={str(check.cwd_ok).lower()} blocked={str(check.blocked).lower()} executableAvailable={str(check.executable_available).lower()}",
                f"blockReason: {check.block_reason or 'none'} missingTool={check.missing_tool or 'none'} message={check.message}",
            ]
        )
    return "\n".join(parts)
