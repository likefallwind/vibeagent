from __future__ import annotations

from .project_check_command_runner import run_project_check_command
from .runtime_checks import build_command_check_observation
from .types import (
    CheckSuggestedChecksAction,
    CheckSuggestedChecksObservation,
    CommandResult,
    RunSuggestedChecksAction,
    RunSuggestedChecksObservation,
    SuggestedCheck,
    SuggestChecksAction,
    SuggestChecksObservation,
)
from .workspace import suggest_project_checks


def suggest_checks_observation(workspace, action: SuggestChecksAction) -> SuggestChecksObservation:
    try:
        suggestions = suggest_project_checks(workspace, max_commands=action.max_commands)
        checks = [SuggestedCheck(**item) for item in suggestions["checks"]]
        return SuggestChecksObservation(
            kind="suggest_checks",
            ok=bool(suggestions["ok"]),
            checks=checks,
            total=int(suggestions["total"]),
            truncated=bool(suggestions["truncated"]),
            changed_files=list(suggestions["changed_files"]),
            message=str(suggestions["message"]),
        )
    except ValueError as error:
        return SuggestChecksObservation(
            kind="suggest_checks",
            ok=False,
            checks=[],
            total=0,
            truncated=False,
            changed_files=[],
            message=str(error),
        )


def check_suggested_checks_observation(
    workspace,
    action: CheckSuggestedChecksAction,
) -> CheckSuggestedChecksObservation:
    try:
        suggestions = suggest_project_checks(workspace, max_commands=action.max_commands)
        suggested_checks = [SuggestedCheck(**item) for item in suggestions["checks"]]
        checks = [build_command_check_observation(workspace, item.command, item.cwd) for item in suggested_checks]
        failed_count = sum(1 for check in checks if not check.ok)
        truncated = bool(suggestions["truncated"])
        ok = failed_count == 0 and not truncated
        status = "incomplete" if truncated else ("all available" if ok else "one or more failed")
        return CheckSuggestedChecksObservation(
            kind="check_suggested_checks",
            ok=ok,
            checks=checks,
            suggested_checks=suggested_checks,
            total=int(suggestions["total"]),
            truncated=truncated,
            max_commands=action.max_commands,
            message=f"Preflighted {len(checks)}/{int(suggestions['total'])} suggested check command(s); {failed_count} failed; {status}.",
        )
    except ValueError as error:
        return CheckSuggestedChecksObservation(
            kind="check_suggested_checks",
            ok=False,
            checks=[],
            suggested_checks=[],
            total=0,
            truncated=False,
            max_commands=action.max_commands,
            message=str(error),
        )


def run_suggested_checks_observation(
    workspace,
    action: RunSuggestedChecksAction,
    command_timeout_ms: int,
) -> RunSuggestedChecksObservation:
    try:
        suggestions = suggest_project_checks(workspace, max_commands=action.max_commands)
        suggested_checks = [SuggestedCheck(**item) for item in suggestions["checks"]]
        runnable_checks = [item for item in suggested_checks if item.available]
        skipped_unavailable = len(suggested_checks) - len(runnable_checks)
        results: list[CommandResult] = []
        stopped_early = False
        for item in runnable_checks:
            result = run_project_check_command(workspace, item.command, item.cwd, action, command_timeout_ms)
            results.append(result)
            failed = result.exit_code != 0 or result.timed_out or result.exit_code is None
            if failed and action.stop_on_failure:
                stopped_early = len(results) < len(runnable_checks)
                break
        truncated = bool(suggestions["truncated"])
        ok = (
            not truncated
            and skipped_unavailable == 0
            and len(results) == len(runnable_checks)
            and all(result.exit_code == 0 and not result.timed_out for result in results)
        )
        status = "incomplete" if truncated else ("all passed" if ok else "one or more failed or were unavailable")
        return RunSuggestedChecksObservation(
            kind="run_suggested_checks",
            ok=ok,
            results=results,
            suggested_checks=suggested_checks,
            total=int(suggestions["total"]),
            truncated=truncated,
            max_commands=action.max_commands,
            stopped_early=stopped_early,
            skipped_unavailable=skipped_unavailable,
            message=(
                f"Ran {len(results)}/{len(runnable_checks)} available suggested check command(s); "
                f"{status}."
            ),
        )
    except ValueError as error:
        return RunSuggestedChecksObservation(
            kind="run_suggested_checks",
            ok=False,
            results=[],
            suggested_checks=[],
            total=0,
            truncated=False,
            max_commands=action.max_commands,
            stopped_early=False,
            skipped_unavailable=0,
            message=str(error),
        )
