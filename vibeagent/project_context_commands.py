from __future__ import annotations

from pathlib import Path
import shlex

from .actions import execute_action
from .check_commands import serialize_focused_test_command
from .local_runtime_commands import (
    command_results_clean,
    serialize_command_check,
    serialize_command_result,
    sum_command_result_duration_ms,
    validate_run_output_context_options,
)
from .project_context_formatting import (
    format_check_focused_test_commands_report_text,
    format_commands_report_text,
    format_focused_test_commands_report_text,
    format_instructions_report_text,
    format_manifest_summary,
    format_manifests_report_text,
    format_project_command,
    format_related_tests_report_text,
    format_run_focused_test_commands_report_text,
    format_todos_report_text,
)
from .types import (
    CheckFocusedTestCommandsAction,
    FocusedTestCommandsAction,
    RelatedTestsAction,
    RunFocusedTestCommandsAction,
)
from .workspace_core import RunWorkspace
from .workspace import (
    read_project_commands,
    read_project_instruction_sources,
    read_project_manifests,
    read_project_todos,
)


def get_commands_text(project_root: str | Path = ".", max_commands: int = 100, max_files: int = 30) -> str:
    return format_commands_report_text(get_commands_report(project_root, max_commands=max_commands, max_files=max_files))


def get_commands_report(project_root: str | Path = ".", max_commands: int = 100, max_files: int = 30) -> dict[str, object]:
    root = Path(project_root).resolve()
    workspace = RunWorkspace(root=root, run_id="local-commands", session_dir=root / ".vibeagent" / "sessions" / "local-commands")
    try:
        metadata = read_project_commands(workspace, max_commands=max_commands, max_files=max_files)
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "ok": False,
            "commands": {"shown": 0, "total": 0, "items": []},
            "metadataFiles": {"scanned": 0, "total": 0},
            "truncated": False,
            "message": str(error),
        }
    commands = [item for item in metadata["commands"] if isinstance(item, dict)]
    return {
        "projectRoot": str(root),
        "ok": bool(metadata["ok"]),
        "commands": {
            "shown": len(commands),
            "total": int(metadata["total"]),
            "items": commands,
        },
        "metadataFiles": {
            "scanned": int(metadata["scanned_files"]),
            "total": int(metadata["total_files"]),
        },
        "truncated": bool(metadata["truncated"]),
        "message": str(metadata["message"]),
    }


def get_related_tests_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    max_paths: int = 100,
    max_candidates: int = 200,
) -> str:
    return format_related_tests_report_text(
        get_related_tests_report(project_root, argument, max_paths=max_paths, max_candidates=max_candidates)
    )


def get_related_tests_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    max_paths: int = 100,
    max_candidates: int = 200,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        paths = parse_related_tests_argument(argument)
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "ok": False,
            "targetPaths": [],
            "testFiles": 0,
            "candidates": {"shown": 0, "total": 0, "items": []},
            "truncated": False,
            "message": f"Usage: /related-tests [path...]\n  message: {error}",
        }

    workspace = RunWorkspace(root=root, run_id="local-related-tests", session_dir=root / ".vibeagent" / "sessions" / "local-related-tests")
    observation = execute_action(
        workspace,
        RelatedTestsAction(
            type="related_tests",
            paths=paths,
            max_paths=max_paths,
            max_candidates=max_candidates,
        ),
    )
    if observation.kind != "related_tests":
        return {
            "projectRoot": str(root),
            "ok": False,
            "targetPaths": [],
            "testFiles": 0,
            "candidates": {"shown": 0, "total": 0, "items": []},
            "truncated": False,
            "message": f"Unexpected observation: {observation.kind}",
        }

    candidates = [
        {
            "source": candidate.source_path,
            "test": candidate.test_path,
            "score": candidate.score,
            "reason": candidate.reason,
        }
        for candidate in observation.candidates
    ]
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "targetPaths": list(observation.target_paths),
        "testFiles": observation.test_files_total,
        "candidates": {
            "shown": len(candidates),
            "total": observation.total,
            "items": candidates,
        },
        "truncated": observation.truncated,
        "message": observation.message,
    }


def get_focused_test_commands_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    max_paths: int = 100,
    max_candidates: int = 200,
    max_commands: int = 50,
) -> str:
    return format_focused_test_commands_report_text(
        get_focused_test_commands_report(
            project_root,
            argument,
            max_paths=max_paths,
            max_candidates=max_candidates,
            max_commands=max_commands,
        )
    )


def get_focused_test_commands_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    max_paths: int = 100,
    max_candidates: int = 200,
    max_commands: int = 50,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        paths = parse_related_tests_argument(argument)
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "ok": False,
            "targetPaths": [],
            "relatedTests": {"total": 0},
            "commands": {"shown": 0, "total": 0, "items": []},
            "truncated": False,
            "message": f"Usage: /focused-tests [path...]\n  message: {error}",
        }

    workspace = RunWorkspace(root=root, run_id="local-focused-tests", session_dir=root / ".vibeagent" / "sessions" / "local-focused-tests")
    observation = execute_action(
        workspace,
        FocusedTestCommandsAction(
            type="focused_test_commands",
            paths=paths,
            max_paths=max_paths,
            max_candidates=max_candidates,
            max_commands=max_commands,
        ),
    )
    if observation.kind != "focused_test_commands":
        return {
            "projectRoot": str(root),
            "ok": False,
            "targetPaths": [],
            "relatedTests": {"total": 0},
            "commands": {"shown": 0, "total": 0, "items": []},
            "truncated": False,
            "message": f"Unexpected observation: {observation.kind}",
        }

    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "targetPaths": list(observation.target_paths),
        "relatedTests": {"total": observation.related_tests_total},
        "commands": {
            "shown": len(observation.commands),
            "total": observation.total,
            "items": [serialize_focused_test_command(command, index=index) for index, command in enumerate(observation.commands, start=1)],
        },
        "truncated": observation.truncated,
        "message": observation.message,
    }


def get_check_focused_test_commands_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    max_paths: int = 100,
    max_candidates: int = 200,
    max_commands: int = 10,
) -> str:
    return format_check_focused_test_commands_report_text(
        get_check_focused_test_commands_report(
            project_root,
            argument,
            max_paths=max_paths,
            max_candidates=max_candidates,
            max_commands=max_commands,
        )
    )


def get_check_focused_test_commands_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    max_paths: int = 100,
    max_candidates: int = 200,
    max_commands: int = 10,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        paths = parse_related_tests_argument(argument)
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "ok": False,
            "targetPaths": [],
            "relatedTests": {"total": 0},
            "focusedCommands": {"shown": 0, "total": 0, "max": max_commands, "items": []},
            "truncated": False,
            "checks": [],
            "message": f"Usage: /check-focused-tests [path...]\n  message: {error}",
        }

    workspace = RunWorkspace(root=root, run_id="local-check-focused-tests", session_dir=root / ".vibeagent" / "sessions" / "local-check-focused-tests")
    observation = execute_action(
        workspace,
        CheckFocusedTestCommandsAction(
            type="check_focused_test_commands",
            paths=paths,
            max_paths=max_paths,
            max_candidates=max_candidates,
            max_commands=max_commands,
        ),
    )
    if observation.kind != "check_focused_test_commands":
        return {
            "projectRoot": str(root),
            "ok": False,
            "targetPaths": [],
            "relatedTests": {"total": 0},
            "focusedCommands": {"shown": 0, "total": 0, "max": max_commands, "items": []},
            "truncated": False,
            "checks": [],
            "message": f"Unexpected observation: {observation.kind}",
        }

    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "targetPaths": list(observation.target_paths),
        "relatedTests": {"total": observation.related_tests_total},
        "focusedCommands": {
            "shown": len(observation.focused_commands),
            "total": observation.total,
            "max": observation.max_commands,
            "items": [serialize_focused_test_command(command, index=index) for index, command in enumerate(observation.focused_commands, start=1)],
        },
        "truncated": observation.truncated,
        "checks": [serialize_command_check(check, index=index) for index, check in enumerate(observation.checks, start=1)],
        "message": observation.message,
    }


def get_run_focused_test_commands_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    max_paths: int = 100,
    max_candidates: int = 200,
    max_commands: int = 10,
    timeout_ms: int = 30_000,
    max_output_chars: int = 12_000,
    stop_on_failure: bool = True,
    extract_output_contexts: bool = False,
    extract_output_diagnostics: bool = False,
    context_lines: int = 5,
    max_diagnostics: int = 50,
    max_contexts: int = 20,
    max_bytes_per_context: int = 20_000,
) -> str:
    return format_run_focused_test_commands_report_text(
        get_run_focused_test_commands_report(
            project_root,
            argument,
            max_paths=max_paths,
            max_candidates=max_candidates,
            max_commands=max_commands,
            timeout_ms=timeout_ms,
            max_output_chars=max_output_chars,
            stop_on_failure=stop_on_failure,
            extract_output_contexts=extract_output_contexts,
            extract_output_diagnostics=extract_output_diagnostics,
            context_lines=context_lines,
            max_diagnostics=max_diagnostics,
            max_contexts=max_contexts,
            max_bytes_per_context=max_bytes_per_context,
        )
    )


def get_run_focused_test_commands_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    max_paths: int = 100,
    max_candidates: int = 200,
    max_commands: int = 10,
    timeout_ms: int = 30_000,
    max_output_chars: int = 12_000,
    stop_on_failure: bool = True,
    extract_output_contexts: bool = False,
    extract_output_diagnostics: bool = False,
    context_lines: int = 5,
    max_diagnostics: int = 50,
    max_contexts: int = 20,
    max_bytes_per_context: int = 20_000,
) -> dict[str, object]:
    root = Path(project_root).resolve()

    def failure(message: str) -> dict[str, object]:
        return {
            "projectRoot": str(root),
            "ok": False,
            "clean": False,
            "targetPaths": [],
            "relatedTests": {"total": 0},
            "focusedCommands": {"shown": 0, "total": 0, "max": max_commands, "items": []},
            "ran": 0,
            "skippedUnavailable": 0,
            "truncated": False,
            "stopOnFailure": stop_on_failure,
            "stoppedEarly": False,
            "results": [],
            "message": message,
        }

    try:
        paths = parse_related_tests_argument(argument)
    except ValueError as error:
        return failure(f"Usage: /run-focused-tests [path...]\n  message: {error}")
    if timeout_ms < 100:
        return failure("Usage: /run-focused-tests [path...]\nError: timeout_ms must be at least 100.")
    if timeout_ms > 600_000:
        return failure("Usage: /run-focused-tests [path...]\nError: timeout_ms must be at most 600000.")
    if max_output_chars < 1_000:
        return failure("Usage: /run-focused-tests [path...]\nError: max_output_chars must be at least 1000.")
    if max_output_chars > 50_000:
        return failure("Usage: /run-focused-tests [path...]\nError: max_output_chars must be at most 50000.")
    output_context_error = validate_run_output_context_options(
        context_lines=context_lines,
        max_diagnostics=max_diagnostics,
        max_contexts=max_contexts,
        max_bytes_per_context=max_bytes_per_context,
        usage="Usage: /run-focused-tests [path...]",
    )
    if output_context_error:
        return failure(output_context_error)

    workspace = RunWorkspace(root=root, run_id="local-run-focused-tests", session_dir=root / ".vibeagent" / "sessions" / "local-run-focused-tests")
    observation = execute_action(
        workspace,
        RunFocusedTestCommandsAction(
            type="run_focused_test_commands",
            paths=paths,
            max_paths=max_paths,
            max_candidates=max_candidates,
            max_commands=max_commands,
            timeout_ms=timeout_ms,
            max_output_chars=max_output_chars,
            stop_on_failure=stop_on_failure,
            extract_output_contexts=extract_output_contexts,
            extract_output_diagnostics=extract_output_diagnostics,
            context_lines=context_lines,
            max_diagnostics=max_diagnostics,
            max_contexts=max_contexts,
            max_bytes_per_context=max_bytes_per_context,
        ),
        command_timeout_ms=timeout_ms,
    )
    if observation.kind != "run_focused_test_commands":
        return failure(f"Unexpected observation: {observation.kind}")

    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "clean": observation.ok and command_results_clean(list(observation.results)),
        "targetPaths": list(observation.target_paths),
        "relatedTests": {"total": observation.related_tests_total},
        "focusedCommands": {
            "shown": len(observation.focused_commands),
            "total": observation.total,
            "max": observation.max_commands,
            "items": [serialize_focused_test_command(command, index=index) for index, command in enumerate(observation.focused_commands, start=1)],
        },
        "ran": len(observation.results),
        "skippedUnavailable": observation.skipped_unavailable,
        "truncated": observation.truncated,
        "stopOnFailure": stop_on_failure,
        "stoppedEarly": observation.stopped_early,
        "durationMs": sum_command_result_duration_ms(list(observation.results)),
        "results": [serialize_command_result(result, index=index) for index, result in enumerate(observation.results, start=1)],
        "message": observation.message,
    }


def parse_related_tests_argument(argument: str | None) -> list[str] | None:
    if not argument or not argument.strip():
        return None
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        raise ValueError(str(error)) from error
    if any(part.startswith("-") for part in parts):
        raise ValueError("options are not supported.")
    return parts or None


def get_manifests_text(project_root: str | Path = ".", max_files: int = 30, max_items: int = 500) -> str:
    return format_manifests_report_text(get_manifests_report(project_root, max_files=max_files, max_items=max_items))


def get_manifests_report(project_root: str | Path = ".", max_files: int = 30, max_items: int = 500) -> dict[str, object]:
    root = Path(project_root).resolve()
    workspace = RunWorkspace(root=root, run_id="local-manifests", session_dir=root / ".vibeagent" / "sessions" / "local-manifests")
    try:
        metadata = read_project_manifests(workspace, max_files=max_files, max_items=max_items)
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "ok": False,
            "files": {"shown": 0, "total": 0, "scanned": 0},
            "items": {"total": 0},
            "truncated": False,
            "manifests": [],
            "message": str(error),
        }
    manifests = [item for item in metadata["manifests"] if isinstance(item, dict)]
    return {
        "projectRoot": str(root),
        "ok": bool(metadata["ok"]),
        "files": {
            "shown": len(manifests),
            "total": int(metadata["total_files"]),
            "scanned": int(metadata["scanned_files"]),
        },
        "items": {"total": int(metadata["total_items"])},
        "truncated": bool(metadata["truncated"]),
        "manifests": manifests,
        "message": str(metadata["message"]),
    }


def get_instructions_text(project_root: str | Path = ".", max_files: int = 20, max_bytes: int = 12_000) -> str:
    return format_instructions_report_text(get_instructions_report(project_root, max_files=max_files, max_bytes=max_bytes))


def get_instructions_report(project_root: str | Path = ".", max_files: int = 20, max_bytes: int = 12_000) -> dict[str, object]:
    root = Path(project_root).resolve()
    workspace = RunWorkspace(root=root, run_id="local-instructions", session_dir=root / ".vibeagent" / "sessions" / "local-instructions")
    try:
        metadata = read_project_instruction_sources(workspace, max_files=max_files, max_bytes=max_bytes)
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "ok": False,
            "files": {"shown": 0, "total": 0, "scanned": 0, "omitted": 0, "sources": []},
            "truncated": False,
            "text": "",
            "message": str(error),
        }
    sources = [item for item in metadata["files"] if isinstance(item, dict)]
    return {
        "projectRoot": str(root),
        "ok": bool(metadata["ok"]),
        "files": {
            "shown": len(sources),
            "total": int(metadata["total_files"]),
            "scanned": int(metadata["scanned_files"]),
            "omitted": int(metadata["omitted_files"]),
            "sources": sources,
        },
        "truncated": bool(metadata["truncated"]),
        "text": str(metadata["text"]),
        "message": str(metadata["message"]),
    }


def get_todos_text(
    project_root: str | Path = ".",
    path: str | None = None,
    max_items: int = 100,
    max_files: int = 1000,
) -> str:
    return format_todos_report_text(get_todos_report(project_root, path=path, max_items=max_items, max_files=max_files))


def get_todos_report(
    project_root: str | Path = ".",
    path: str | None = None,
    max_items: int = 100,
    max_files: int = 1000,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    workspace = RunWorkspace(root=root, run_id="local-todos", session_dir=root / ".vibeagent" / "sessions" / "local-todos")
    try:
        metadata = read_project_todos(workspace, relative_path=path, max_items=max_items, max_files=max_files)
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "path": path or ".",
            "ok": False,
            "todos": {"shown": 0, "total": 0, "items": []},
            "files": {"scanned": 0, "total": 0},
            "truncated": False,
            "markers": [],
            "message": str(error),
        }
    todos = [item for item in metadata["todos"] if isinstance(item, dict)]
    return {
        "projectRoot": str(root),
        "path": str(metadata["path"]),
        "ok": bool(metadata["ok"]),
        "todos": {
            "shown": len(todos),
            "total": int(metadata["total"]),
            "items": todos,
        },
        "files": {
            "scanned": int(metadata["scanned_files"]),
            "total": int(metadata["total_files"]),
        },
        "truncated": bool(metadata["truncated"]),
        "markers": list(metadata["markers"]),
        "message": str(metadata["message"]),
    }
