from __future__ import annotations

from .prompt_next_action_project_formatting import (
    available_command_labels,
    blocked_check_labels,
    command_labels,
    format_next_action_items,
)
from .types import Observation


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

    available = available_command_labels(getattr(latest, "commands", []))
    if available:
        return (
            f"{base} Focused test commands are available. Run run_focused_test_commands or run_command for: "
            f"{format_next_action_items(available)}. Then run broader checks if the change needs them."
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
        blockers = blocked_check_labels(getattr(latest, "checks", []))
        if blockers:
            return (
                f"{base} Focused test dry-run found blocked command(s): {format_next_action_items(blockers)}. "
                "Fix the command context or choose another focused check before running tests."
            )
        return f"{base} Focused test dry-run failed. Inspect the message, then choose another verification path."

    runnable = command_labels(getattr(latest, "focused_commands", []))
    if runnable:
        return (
            f"{base} Focused test dry-run passed. Run run_focused_test_commands or run_command for: "
            f"{format_next_action_items(runnable)}."
        )
    return f"{base} Focused test dry-run passed but no commands were listed. Continue with the next required check or answer directly."
