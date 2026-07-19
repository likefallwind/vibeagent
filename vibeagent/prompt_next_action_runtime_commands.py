from __future__ import annotations

from .prompt_next_action_runtime_formatting import (
    check_failure_labels,
    command_result_output_issue_labels,
    failed_command_labels,
    format_next_action_items,
    inline_output_issue_instruction,
)
from .prompt_next_action_runtime_output import (
    not_run_batch_command_labels,
    not_run_detail,
    not_run_session_verification_labels,
)
from .types import Observation


def run_command_next_action_instruction(base: str, latest: Observation) -> str:
    result = latest.result
    if result.exit_code == 0 and not result.timed_out:
        output_issues = command_result_output_issue_labels([result], failed_only=False)
        if output_issues:
            return inline_output_issue_instruction(
                base,
                "The latest command succeeded, but its inline output analysis found source-linked issue(s).",
                output_issues,
                "decide whether they are relevant, edit or fix if needed, and rerun or continue only after confirming they are non-blocking.",
            )
        return (
            f"{base} The latest command succeeded. If it checked the requested work, your next action must be "
            "a concise final answer. Do not run another check unless the output contains a concrete error."
        )
    output_issues = command_result_output_issue_labels([result], failed_only=True)
    if output_issues:
        return inline_output_issue_instruction(
            base,
            "The latest command failed or timed out.",
            output_issues,
            "fix the issue, and rerun the failed command before finishing.",
        )
    return (
        f"{base} The latest command failed or timed out. Inspect its stdout/stderr for concrete errors; "
        "if the output names file:line locations or is noisy, use output_diagnostics, output_contexts, "
        "or python_traceback to locate the relevant source before editing. Fix the issue and rerun the "
        "failed command before finishing."
    )


def check_run_commands_next_action_instruction(base: str, latest: Observation) -> str:
    checks = getattr(latest, "checks", [])
    blocked = [check for check in checks if getattr(check, "blocked", False)]
    missing = [check for check in checks if not getattr(check, "executable_available", True)]
    if not getattr(latest, "ok", False):
        if blocked:
            commands = [str(getattr(check, "command", "") or "").strip() for check in blocked]
            return (
                f"{base} Command preflight found blocked command(s): {format_next_action_items([item for item in commands if item])}. "
                "Choose a safer command or inspect the block reason before requesting execution."
            )
        if missing:
            tools = [str(getattr(check, "missing_tool", "") or "").strip() for check in missing]
            return (
                f"{base} Command preflight found unavailable executable(s): {format_next_action_items([item for item in tools if item])}. "
                "Use an available project command or inspect environment_info before requesting execution."
            )
        return f"{base} Command preflight failed. Fix the command, cwd, or executable choice before running it."
    return f"{base} Command preflight succeeded. Use run_commands only if executing the checked commands is still required."


def python_or_config_check_next_action_instruction(base: str, latest: Observation) -> str:
    if getattr(latest, "ok", False):
        return (
            f"{base} The latest {latest.kind} passed. Continue with the next required check, "
            "or answer directly if the requested work is complete."
        )
    failures = check_failure_labels(getattr(latest, "files", []))
    if failures:
        return (
            f"{base} The latest {latest.kind} failed. Fix the reported issue(s) before finishing: "
            f"{format_next_action_items(failures)}."
        )
    return f"{base} The latest {latest.kind} failed. Inspect its message, fix the issue, and rerun the check before finishing."


def batch_command_result_next_action_instruction(base: str, latest: Observation) -> str:
    results = getattr(latest, "results", [])
    failed_commands = failed_command_labels(results)
    if failed_commands:
        stopped = " The batch stopped early after the first failure; remaining selected checks may still be unverified." if getattr(latest, "stopped_early", False) else ""
        not_run_text = not_run_detail(
            not_run_batch_command_labels(latest, len(results or []))
        )
        output_issues = command_result_output_issue_labels(results, failed_only=True)
        if output_issues:
            return inline_output_issue_instruction(
                base,
                f"The latest {latest.kind} had failed command(s).{stopped}",
                output_issues,
                (
                    "fix the issue(s), and rerun the failed command(s) or the full batch before finishing: "
                    f"{format_next_action_items(failed_commands)}.{not_run_text}"
                ),
            )
        return (
            f"{base} The latest {latest.kind} had failed command(s). Inspect stdout/stderr; "
            "use output_diagnostics, output_contexts, or python_traceback for noisy output with file references. "
            f"{stopped} Fix the issue(s) and rerun the failed command(s) or the full batch before finishing: "
            f"{format_next_action_items(failed_commands)}.{not_run_text}"
        )
    output_issues = command_result_output_issue_labels(results, failed_only=False)
    if output_issues:
        return inline_output_issue_instruction(
            base,
            f"The latest {latest.kind} completed without failed commands, but inline output analysis found source-linked issue(s).",
            output_issues,
            "decide whether they are relevant, edit or fix if needed, and rerun the relevant command(s) or continue only after confirming they are non-blocking.",
        )
    return (
        f"{base} The latest {latest.kind} completed without failed commands. "
        "Continue with the next required check, or answer directly if the requested work is complete."
    )


def run_session_verification_next_action_instruction(base: str, latest: Observation) -> str:
    selected_count = int(getattr(latest, "selected_count", 0) or 0)
    results = getattr(latest, "results", [])
    failed_commands = failed_command_labels(results)
    if failed_commands:
        stopped = " The run stopped early after the first failure." if getattr(latest, "stopped_early", False) else ""
        not_run_text = not_run_detail(not_run_session_verification_labels(latest))
        output_issues = command_result_output_issue_labels(results, failed_only=True)
        if output_issues:
            return inline_output_issue_instruction(
                base,
                f"run_session_verification reran recorded verification check(s) and found failed command(s).{stopped}",
                output_issues,
                (
                    "fix the issue(s), then rerun run_session_verification or session_verification before finishing: "
                    f"{format_next_action_items(failed_commands)}.{not_run_text}"
                ),
            )
        return (
            f"{base} run_session_verification reran recorded verification check(s) and found failed command(s)."
            f"{stopped} Inspect stdout/stderr, use session_output_diagnostics or session_output_contexts for noisy output, "
            f"fix the issue(s), then rerun run_session_verification or session_verification before finishing: "
            f"{format_next_action_items(failed_commands)}.{not_run_text}"
        )
    if selected_count > 0 and not getattr(latest, "ok", False):
        output_issues = command_result_output_issue_labels(results, failed_only=False)
        if output_issues:
            not_run_text = not_run_detail(not_run_session_verification_labels(latest))
            return inline_output_issue_instruction(
                base,
                "run_session_verification reran recorded verification check(s) and found source-linked output issue(s) without a failed exit code.",
                output_issues,
                (
                    "inspect or edit the referenced source, then rerun run_session_verification or session_verification "
                    f"before finishing.{not_run_text}"
                ),
            )
    if selected_count > 0 and getattr(latest, "ok", False):
        output_issues = command_result_output_issue_labels(results, failed_only=False)
        if output_issues:
            return inline_output_issue_instruction(
                base,
                f"run_session_verification reran {selected_count} recorded verification check(s), and they passed, but inline output analysis found source-linked issue(s).",
                output_issues,
                "decide whether they are relevant, edit or fix if needed, and rerun run_session_verification or session_audit before finishing only after confirming they are non-blocking.",
            )
        return (
            f"{base} run_session_verification reran {selected_count} recorded verification check(s), and they passed. "
            "Run session_audit or final_review to confirm readiness, or answer directly if the task is complete."
        )
    if selected_count == 0:
        return (
            f"{base} run_session_verification did not select any pending or failed check. "
            "Use session_verification to inspect recorded verification state, or session_audit if readiness is unclear."
        )
    return (
        f"{base} run_session_verification could not confirm the recorded checks passed. "
        "Inspect its message and output, then use session_verification or session_audit before finishing."
    )
