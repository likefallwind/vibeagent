from __future__ import annotations

from .project_check_command_runner import run_project_check_command
from .project_suggested_check_actions import (
    check_suggested_checks_observation,
    run_suggested_checks_observation,
    suggest_checks_observation,
)
from .runtime_checks import build_command_check_observation
from .types import (
    AgentAction,
    CheckFocusedTestCommandsAction,
    CheckFocusedTestCommandsObservation,
    CheckSuggestedChecksAction,
    CommandResult,
    FocusedTestCommand,
    FocusedTestCommandsAction,
    FocusedTestCommandsObservation,
    Observation,
    RelatedTestCandidate,
    RelatedTestsAction,
    RelatedTestsObservation,
    RunFocusedTestCommandsAction,
    RunFocusedTestCommandsObservation,
    RunSuggestedChecksAction,
    SuggestChecksAction,
)
from .workspace import (
    find_related_tests,
    suggest_focused_test_commands,
)


def execute_project_context_check_action(
    workspace,
    action: AgentAction,
    command_timeout_ms: int = 30_000,
) -> Observation | None:
    if isinstance(action, SuggestChecksAction):
        return suggest_checks_observation(workspace, action)

    if isinstance(action, CheckSuggestedChecksAction):
        return check_suggested_checks_observation(workspace, action)

    if isinstance(action, RunSuggestedChecksAction):
        return run_suggested_checks_observation(workspace, action, command_timeout_ms)

    if isinstance(action, RelatedTestsAction):
        return related_tests_observation(workspace, action)

    if isinstance(action, FocusedTestCommandsAction):
        return focused_test_commands_observation(workspace, action)

    if isinstance(action, CheckFocusedTestCommandsAction):
        return check_focused_test_commands_observation(workspace, action)

    if isinstance(action, RunFocusedTestCommandsAction):
        return run_focused_test_commands_observation(workspace, action, command_timeout_ms)

    return None


def related_tests_observation(workspace, action: RelatedTestsAction) -> RelatedTestsObservation:
    try:
        metadata = find_related_tests(
            workspace,
            paths=action.paths,
            max_paths=action.max_paths,
            max_candidates=action.max_candidates,
        )
        candidates = [RelatedTestCandidate(**item) for item in metadata["candidates"]]
        return RelatedTestsObservation(
            kind="related_tests",
            ok=bool(metadata["ok"]),
            target_paths=list(metadata["target_paths"]),
            candidates=candidates,
            total=int(metadata["total"]),
            truncated=bool(metadata["truncated"]),
            test_files_total=int(metadata["test_files_total"]),
            message=str(metadata["message"]),
        )
    except ValueError as error:
        return RelatedTestsObservation(
            kind="related_tests",
            ok=False,
            target_paths=[],
            candidates=[],
            total=0,
            truncated=False,
            test_files_total=0,
            message=str(error),
        )

def focused_test_commands_observation(
    workspace,
    action: FocusedTestCommandsAction,
) -> FocusedTestCommandsObservation:
    try:
        metadata = suggest_focused_test_commands(
            workspace,
            paths=action.paths,
            max_paths=action.max_paths,
            max_candidates=action.max_candidates,
            max_commands=action.max_commands,
        )
        commands = [FocusedTestCommand(**item) for item in metadata["commands"]]
        return FocusedTestCommandsObservation(
            kind="focused_test_commands",
            ok=bool(metadata["ok"]),
            target_paths=list(metadata["target_paths"]),
            commands=commands,
            total=int(metadata["total"]),
            truncated=bool(metadata["truncated"]),
            related_tests_total=int(metadata["related_tests_total"]),
            message=str(metadata["message"]),
        )
    except ValueError as error:
        return FocusedTestCommandsObservation(
            kind="focused_test_commands",
            ok=False,
            target_paths=[],
            commands=[],
            total=0,
            truncated=False,
            related_tests_total=0,
            message=str(error),
        )


def check_focused_test_commands_observation(
    workspace,
    action: CheckFocusedTestCommandsAction,
) -> CheckFocusedTestCommandsObservation:
    try:
        if action.max_commands > 50:
            raise ValueError("max_commands must be at most 50")
        metadata = suggest_focused_test_commands(
            workspace,
            paths=action.paths,
            max_paths=action.max_paths,
            max_candidates=action.max_candidates,
            max_commands=action.max_commands,
        )
        focused_commands = [FocusedTestCommand(**item) for item in metadata["commands"]]
        checks = [build_command_check_observation(workspace, item.command, item.cwd) for item in focused_commands]
        failed_count = sum(1 for check in checks if not check.ok)
        return CheckFocusedTestCommandsObservation(
            kind="check_focused_test_commands",
            ok=failed_count == 0,
            checks=checks,
            focused_commands=focused_commands,
            target_paths=list(metadata["target_paths"]),
            total=int(metadata["total"]),
            truncated=bool(metadata["truncated"]),
            max_commands=action.max_commands,
            related_tests_total=int(metadata["related_tests_total"]),
            message=f"Preflighted {len(checks)}/{int(metadata['total'])} focused test command(s); {failed_count} failed.",
            max_paths=action.max_paths,
            max_candidates=action.max_candidates,
            requested_paths=list(action.paths or []),
        )
    except ValueError as error:
        return CheckFocusedTestCommandsObservation(
            kind="check_focused_test_commands",
            ok=False,
            checks=[],
            focused_commands=[],
            target_paths=[],
            total=0,
            truncated=False,
            max_commands=action.max_commands,
            related_tests_total=0,
            message=str(error),
            max_paths=action.max_paths,
            max_candidates=action.max_candidates,
            requested_paths=list(action.paths or []),
        )


def run_focused_test_commands_observation(
    workspace,
    action: RunFocusedTestCommandsAction,
    command_timeout_ms: int,
) -> RunFocusedTestCommandsObservation:
    try:
        if action.max_commands > 50:
            raise ValueError("max_commands must be at most 50")
        metadata = suggest_focused_test_commands(
            workspace,
            paths=action.paths,
            max_paths=action.max_paths,
            max_candidates=action.max_candidates,
            max_commands=action.max_commands,
        )
        focused_commands = [FocusedTestCommand(**item) for item in metadata["commands"]]
        runnable_commands = [item for item in focused_commands if item.available]
        skipped_unavailable = len(focused_commands) - len(runnable_commands)
        results: list[CommandResult] = []
        stopped_early = False
        for item in runnable_commands:
            result = run_project_check_command(workspace, item.command, item.cwd, action, command_timeout_ms)
            results.append(result)
            failed = result.exit_code != 0 or result.timed_out or result.exit_code is None
            if failed and action.stop_on_failure:
                stopped_early = len(results) < len(runnable_commands)
                break
        ok = (
            skipped_unavailable == 0
            and len(results) == len(runnable_commands)
            and all(result.exit_code == 0 and not result.timed_out for result in results)
        )
        return RunFocusedTestCommandsObservation(
            kind="run_focused_test_commands",
            ok=ok,
            results=results,
            focused_commands=focused_commands,
            target_paths=list(metadata["target_paths"]),
            total=int(metadata["total"]),
            truncated=bool(metadata["truncated"]),
            max_commands=action.max_commands,
            related_tests_total=int(metadata["related_tests_total"]),
            stopped_early=stopped_early,
            skipped_unavailable=skipped_unavailable,
            message=(
                f"Ran {len(results)}/{len(runnable_commands)} available focused test command(s); "
                f"{'all passed' if ok else 'one or more failed or were unavailable'}."
            ),
            max_paths=action.max_paths,
            max_candidates=action.max_candidates,
            requested_paths=list(action.paths or []),
        )
    except ValueError as error:
        return RunFocusedTestCommandsObservation(
            kind="run_focused_test_commands",
            ok=False,
            results=[],
            focused_commands=[],
            target_paths=[],
            total=0,
            truncated=False,
            max_commands=action.max_commands,
            related_tests_total=0,
            stopped_early=False,
            skipped_unavailable=0,
            message=str(error),
            max_paths=action.max_paths,
            max_candidates=action.max_candidates,
            requested_paths=list(action.paths or []),
        )
