from __future__ import annotations

from .types import Observation


PROJECT_NEXT_ACTION_KINDS = {
    "suggest_checks",
    "check_suggested_checks",
    "project_commands",
    "related_tests",
    "focused_test_commands",
    "check_focused_test_commands",
}


def _command_labels(values: object) -> list[str]:
    labels: list[str] = []
    if not isinstance(values, list):
        return labels
    for value in values:
        command = str(getattr(value, "command", "") or "").strip()
        cwd = str(getattr(value, "cwd", ".") or ".").strip() or "."
        if command:
            labels.append(f"{command} (cwd={cwd})")
    return labels


def _available_command_labels(values: object) -> list[str]:
    labels: list[str] = []
    if not isinstance(values, list):
        return labels
    for value in values:
        if not getattr(value, "available", True):
            continue
        command = str(getattr(value, "command", "") or "").strip()
        cwd = str(getattr(value, "cwd", ".") or ".").strip() or "."
        if command:
            labels.append(f"{command} (cwd={cwd})")
    return labels


def _blocked_check_labels(values: object) -> list[str]:
    labels: list[str] = []
    if not isinstance(values, list):
        return labels
    for value in values:
        if getattr(value, "ok", False):
            continue
        command = str(getattr(value, "command", "") or "").strip()
        reason = str(getattr(value, "block_reason", "") or getattr(value, "missing_tool", "") or getattr(value, "message", "") or "").strip()
        if command and reason:
            labels.append(f"{command}: {reason}")
        elif command:
            labels.append(command)
        elif reason:
            labels.append(reason)
    return labels


def _format_next_action_items(items: list[str], max_items: int = 3) -> str:
    shown = items[:max_items]
    suffix = "" if len(items) <= max_items else f"; +{len(items) - max_items} more"
    return "; ".join(shown) + suffix


def _suggest_checks_next_action_instruction(base: str, latest: Observation) -> str:
    if not getattr(latest, "ok", False):
        return (
            f"{base} Suggested checks could not be collected. Use project_commands or focused_test_commands to find runnable checks, "
            "or continue with a known verification command."
        )

    available = _available_command_labels(getattr(latest, "checks", []))
    if available:
        return (
            f"{base} Suggested checks are available. Run run_suggested_checks or run_command for: "
            f"{_format_next_action_items(available)}. Fix failures before finishing."
        )

    total = int(getattr(latest, "total", 0) or 0)
    if total > 0:
        return (
            f"{base} Suggested checks were found but are not directly available. "
            "Inspect missing tools, use project_commands for alternatives, or run an equivalent check manually."
        )

    return (
        f"{base} No suggested checks were found. Use project_commands, related_tests, or focused_test_commands to find a verification path."
    )


def _check_suggested_checks_next_action_instruction(base: str, latest: Observation) -> str:
    if not getattr(latest, "ok", False):
        blockers = _blocked_check_labels(getattr(latest, "checks", []))
        if blockers:
            return (
                f"{base} Suggested check dry-run found blocked command(s): {_format_next_action_items(blockers)}. "
                "Fix the command context or choose another verification path before running checks."
            )
        return f"{base} Suggested check dry-run failed. Inspect the message, then choose another verification path."

    runnable = _command_labels(getattr(latest, "suggested_checks", []))
    if runnable:
        return (
            f"{base} Suggested check dry-run passed. Run run_suggested_checks or run_command for: "
            f"{_format_next_action_items(runnable)}."
        )
    return f"{base} Suggested check dry-run passed but no commands were listed. Continue with the next required check or answer directly."


def _project_commands_next_action_instruction(base: str, latest: Observation) -> str:
    if not getattr(latest, "ok", False):
        return (
            f"{base} Project commands could not be collected. Inspect project_manifests or run a known check command if available."
        )

    available = _available_command_labels(getattr(latest, "commands", []))
    if available:
        return (
            f"{base} Project commands were found. Choose the relevant command and use command_check or run_command: "
            f"{_format_next_action_items(available)}."
        )

    total = int(getattr(latest, "total", 0) or 0)
    if total > 0:
        return (
            f"{base} Project command hints exist but are not directly runnable. Inspect missing tools or project_manifests, "
            "then choose an equivalent verification command."
        )
    return f"{base} No project commands were found. Use related_tests, focused_test_commands, or a known repository check."


def _related_tests_next_action_instruction(base: str, latest: Observation) -> str:
    if not getattr(latest, "ok", False):
        return (
            f"{base} Related tests could not be identified. Use project_commands or suggest_checks to choose verification."
        )

    total = int(getattr(latest, "total", 0) or 0)
    if total > 0:
        return (
            f"{base} Related tests were found. Use focused_test_commands to build runnable focused checks, "
            "or run the listed tests manually before broader verification."
        )
    return f"{base} No related tests were found. Use suggest_checks or project_commands for broader verification."


def _focused_test_commands_next_action_instruction(base: str, latest: Observation) -> str:
    if not getattr(latest, "ok", False):
        return (
            f"{base} Focused test commands could not be collected. Use related_tests, suggest_checks, or project_commands for verification."
        )

    available = _available_command_labels(getattr(latest, "commands", []))
    if available:
        return (
            f"{base} Focused test commands are available. Run run_focused_test_commands or run_command for: "
            f"{_format_next_action_items(available)}. Then run broader checks if the change needs them."
        )

    total = int(getattr(latest, "total", 0) or 0)
    if total > 0:
        return (
            f"{base} Focused test commands were found but are not directly available. "
            "Inspect missing tools, use related_tests for paths, or choose another verification command."
        )
    return f"{base} No focused test commands were found. Use suggest_checks or project_commands for verification."


def _check_focused_test_commands_next_action_instruction(base: str, latest: Observation) -> str:
    if not getattr(latest, "ok", False):
        blockers = _blocked_check_labels(getattr(latest, "checks", []))
        if blockers:
            return (
                f"{base} Focused test dry-run found blocked command(s): {_format_next_action_items(blockers)}. "
                "Fix the command context or choose another focused check before running tests."
            )
        return f"{base} Focused test dry-run failed. Inspect the message, then choose another verification path."

    runnable = _command_labels(getattr(latest, "focused_commands", []))
    if runnable:
        return (
            f"{base} Focused test dry-run passed. Run run_focused_test_commands or run_command for: "
            f"{_format_next_action_items(runnable)}."
        )
    return f"{base} Focused test dry-run passed but no commands were listed. Continue with the next required check or answer directly."


def project_next_action_instruction(base: str, latest: Observation) -> str:
    if latest.kind == "suggest_checks":
        return _suggest_checks_next_action_instruction(base, latest)
    if latest.kind == "check_suggested_checks":
        return _check_suggested_checks_next_action_instruction(base, latest)
    if latest.kind == "project_commands":
        return _project_commands_next_action_instruction(base, latest)
    if latest.kind == "related_tests":
        return _related_tests_next_action_instruction(base, latest)
    if latest.kind == "focused_test_commands":
        return _focused_test_commands_next_action_instruction(base, latest)
    if latest.kind == "check_focused_test_commands":
        return _check_focused_test_commands_next_action_instruction(base, latest)

    raise ValueError(f"Unsupported project next-action kind: {latest.kind}")
