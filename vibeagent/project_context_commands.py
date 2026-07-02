from __future__ import annotations

from pathlib import Path
import shlex

from .actions import execute_action
from .check_commands import format_structured_command_checks, serialize_focused_test_command
from .local_runtime_commands import (
    serialize_command_check,
    serialize_command_result,
    validate_run_output_context_options,
)
from .process_commands import format_structured_command_output_analysis_lines
from .types import (
    CheckFocusedTestCommandsAction,
    FocusedTestCommandsAction,
    ProjectCommand,
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


def _indent_block(value: str, spaces: int = 2) -> str:
    indent = " " * spaces
    return "\n".join(f"{indent}{line}" if line else "" for line in value.splitlines())


def format_project_command(item: ProjectCommand) -> str:
    availability = "available" if item.available else f"missing {item.missing_tool}"
    return f"    - [{availability}] {item.command} (cwd: {item.cwd}, source: {item.file})"


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


def format_commands_report_text(report: dict[str, object]) -> str:
    commands = report.get("commands") if isinstance(report.get("commands"), dict) else {}
    items = [item for item in commands.get("items", []) if isinstance(item, dict)] if isinstance(commands.get("items"), list) else []
    files = report.get("metadataFiles") if isinstance(report.get("metadataFiles"), dict) else {}
    lines = [
        "Project commands:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  commands: {int(commands.get('shown', len(items)) or 0)}/{int(commands.get('total', len(items)) or 0)}",
        f"  metadataFiles: {int(files.get('scanned', 0) or 0)}/{int(files.get('total', 0) or 0)}",
        f"  truncated: {'yes' if bool(report.get('truncated')) else 'no'}",
    ]
    if items:
        lines.append("  commands:")
        lines.extend(format_project_command(ProjectCommand(**item)) for item in items)
    else:
        lines.append("  commands: none")
    lines.append(f"  message: {report.get('message') or ''}")
    return "\n".join(lines)


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


def format_related_tests_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    target_paths = [str(item) for item in report.get("targetPaths", [])] if isinstance(report.get("targetPaths"), list) else []
    candidates = report.get("candidates") if isinstance(report.get("candidates"), dict) else {}
    items = [item for item in candidates.get("items", []) if isinstance(item, dict)] if isinstance(candidates.get("items"), list) else []
    lines = [
        "Related tests:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  targetPaths: {len(target_paths)}",
        f"  testFiles: {int(report.get('testFiles', 0) or 0)}",
        f"  candidates: {int(candidates.get('shown', len(items)) or 0)}/{int(candidates.get('total', len(items)) or 0)}",
        f"  truncated: {'yes' if bool(report.get('truncated')) else 'no'}",
        f"  message: {message}",
    ]
    if target_paths:
        lines.append("  targets:")
        lines.extend(f"    - {path}" for path in target_paths)
    else:
        lines.append("  targets: none")

    if items:
        lines.append("  candidates:")
        for candidate in items:
            lines.extend(
                [
                    f"    - source: {candidate.get('source') or ''}",
                    f"      test: {candidate.get('test') or ''}",
                    f"      score: {candidate.get('score')}",
                    f"      reason: {candidate.get('reason') or ''}",
                ]
            )
    else:
        lines.append("  candidates: none")
    return "\n".join(lines)


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


def format_focused_test_commands_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    target_paths = [str(item) for item in report.get("targetPaths", [])] if isinstance(report.get("targetPaths"), list) else []
    related_tests = report.get("relatedTests") if isinstance(report.get("relatedTests"), dict) else {}
    commands = report.get("commands") if isinstance(report.get("commands"), dict) else {}
    items = [item for item in commands.get("items", []) if isinstance(item, dict)] if isinstance(commands.get("items"), list) else []
    lines = [
        "Focused test commands:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  targetPaths: {len(target_paths)}",
        f"  relatedTests: {int(related_tests.get('total', 0) or 0)}",
        f"  commands: {int(commands.get('shown', len(items)) or 0)}/{int(commands.get('total', len(items)) or 0)}",
        f"  truncated: {'yes' if bool(report.get('truncated')) else 'no'}",
        f"  message: {message}",
    ]
    if target_paths:
        lines.append("  targets:")
        lines.extend(f"    - {path}" for path in target_paths)
    else:
        lines.append("  targets: none")

    if items:
        lines.append("  commands:")
        for command in items:
            lines.extend(
                [
                    f"    - command: {command.get('command') or ''}",
                    f"      cwd: {command.get('cwd') or '.'}",
                    f"      test: {command.get('test') or ''}",
                    f"      source: {command.get('source') or ''}",
                    f"      available: {'yes' if bool(command.get('available')) else 'no'}",
                    f"      missingTool: {command.get('missingTool') or 'none'}",
                    f"      reason: {command.get('reason') or ''}",
                ]
            )
    else:
        lines.append("  commands: none")
    return "\n".join(lines)


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


def format_check_focused_test_commands_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    target_paths = [str(item) for item in report.get("targetPaths", [])] if isinstance(report.get("targetPaths"), list) else []
    related_tests = report.get("relatedTests") if isinstance(report.get("relatedTests"), dict) else {}
    focused = report.get("focusedCommands") if isinstance(report.get("focusedCommands"), dict) else {}
    checks = [item for item in report.get("checks", []) if isinstance(item, dict)] if isinstance(report.get("checks"), list) else []
    lines = [
        "Check focused test commands:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  targetPaths: {len(target_paths)}",
        f"  relatedTests: {int(related_tests.get('total', 0) or 0)}",
        f"  focusedCommands: {int(focused.get('shown', len(checks)) or 0)}/{int(focused.get('total', len(checks)) or 0)}",
        f"  truncated: {'yes' if bool(report.get('truncated')) else 'no'}",
        f"  message: {message}",
    ]
    lines.extend(format_structured_command_checks(checks, spaces=2))
    return "\n".join(lines)


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
        "results": [serialize_command_result(result, index=index) for index, result in enumerate(observation.results, start=1)],
        "message": observation.message,
    }


def format_run_focused_test_commands_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    target_paths = [str(item) for item in report.get("targetPaths", [])] if isinstance(report.get("targetPaths"), list) else []
    focused = report.get("focusedCommands") if isinstance(report.get("focusedCommands"), dict) else {}
    results = [item for item in report.get("results", []) if isinstance(item, dict)] if isinstance(report.get("results"), list) else []
    lines = [
        "Run focused test commands:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  targetPaths: {len(target_paths)}",
        f"  focusedCommands: {int(focused.get('shown', 0) or 0)}/{int(focused.get('total', 0) or 0)}",
        f"  ran: {int(report.get('ran', len(results)) or 0)}",
        f"  skippedUnavailable: {int(report.get('skippedUnavailable', 0) or 0)}",
        f"  truncated: {'yes' if bool(report.get('truncated')) else 'no'}",
        f"  stopOnFailure: {'yes' if bool(report.get('stopOnFailure')) else 'no'}",
        f"  stoppedEarly: {'yes' if bool(report.get('stoppedEarly')) else 'no'}",
        f"  message: {message}",
    ]
    if results:
        lines.append("  results:")
        for position, result in enumerate(results, start=1):
            index = result.get("index", position)
            analysis = result.get("analysis") if isinstance(result.get("analysis"), dict) else {}
            lines.extend(
                [
                    f"    - index: {index}",
                    f"      command: {result.get('command') or ''}",
                    f"      cwd: {result.get('cwd') or '.'}",
                    f"      ok: {'yes' if bool(result.get('ok')) else 'no'}",
                    f"      exitCode: {result.get('exitCode') if result.get('exitCode') is not None else '.'}",
                    f"      timedOut: {'yes' if bool(result.get('timedOut')) else 'no'}",
                    f"      stdoutTruncated: {'yes' if bool(result.get('stdoutTruncated')) else 'no'}",
                    f"      stderrTruncated: {'yes' if bool(result.get('stderrTruncated')) else 'no'}",
                ]
            )
            lines.extend(format_structured_command_output_analysis_lines(analysis, spaces=6))
            stdout = str(result.get("stdout") or "")
            stderr = str(result.get("stderr") or "")
            if stdout:
                lines.append("      stdout:")
                lines.append(_indent_block(stdout.rstrip(), spaces=8))
            else:
                lines.append("      stdout: none")
            if stderr:
                lines.append("      stderr:")
                lines.append(_indent_block(stderr.rstrip(), spaces=8))
            else:
                lines.append("      stderr: none")
    else:
        lines.append("  results: none")
    return "\n".join(lines)


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


def format_manifests_report_text(report: dict[str, object]) -> str:
    files = report.get("files") if isinstance(report.get("files"), dict) else {}
    items = report.get("items") if isinstance(report.get("items"), dict) else {}
    manifests = [item for item in report.get("manifests", []) if isinstance(item, dict)] if isinstance(report.get("manifests"), list) else []
    lines = [
        "Manifests:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  files: {int(files.get('shown', len(manifests)) or 0)}/{int(files.get('total', len(manifests)) or 0)}",
        f"  scannedFiles: {int(files.get('scanned', 0) or 0)}/{int(files.get('total', len(manifests)) or 0)}",
        f"  items: {int(items.get('total', 0) or 0)}",
        f"  truncated: {'yes' if bool(report.get('truncated')) else 'no'}",
    ]
    if manifests:
        lines.append("  manifests:")
        for manifest in manifests:
            lines.extend(format_manifest_summary(manifest))
    else:
        lines.append("  manifests: none")
    lines.append(f"  message: {report.get('message') or ''}")
    return "\n".join(lines)


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


def format_instructions_report_text(report: dict[str, object]) -> str:
    files = report.get("files") if isinstance(report.get("files"), dict) else {}
    sources = [item for item in files.get("sources", []) if isinstance(item, dict)] if isinstance(files.get("sources"), list) else []
    lines = [
        "Project instructions:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  files: {int(files.get('shown', len(sources)) or 0)}/{int(files.get('total', len(sources)) or 0)}",
        f"  scannedFiles: {int(files.get('scanned', 0) or 0)}/{int(files.get('total', len(sources)) or 0)}",
        f"  omittedFiles: {int(files.get('omitted', 0) or 0)}",
        f"  truncated: {'yes' if bool(report.get('truncated')) else 'no'}",
    ]
    if sources:
        lines.append("  sources:")
        for source in sources:
            lines.append(
                "    - "
                f"{source.get('path')} "
                f"(scope={source.get('scope')}, bytes={source.get('bytes')}, chars={source.get('chars')}, "
                f"empty={'yes' if source.get('empty') else 'no'}, included={'yes' if source.get('included') else 'no'})"
            )
            lines.append(f"      message: {source.get('message')}")
    else:
        lines.append("  sources: none")
    text = str(report.get("text") or "")
    if text:
        lines.append("  text:")
        lines.extend(f"    {line}" for line in text.splitlines())
    else:
        lines.append("  text: none")
    lines.append(f"  message: {report.get('message') or ''}")
    return "\n".join(lines)


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


def format_todos_report_text(report: dict[str, object]) -> str:
    todos = report.get("todos") if isinstance(report.get("todos"), dict) else {}
    items = [item for item in todos.get("items", []) if isinstance(item, dict)] if isinstance(todos.get("items"), list) else []
    files = report.get("files") if isinstance(report.get("files"), dict) else {}
    markers = report.get("markers") if isinstance(report.get("markers"), list) else []
    lines = [
        "Project TODOs:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  path: {report.get('path') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  todos: {int(todos.get('shown', len(items)) or 0)}/{int(todos.get('total', len(items)) or 0)}",
        f"  scannedFiles: {int(files.get('scanned', 0) or 0)}/{int(files.get('total', 0) or 0)}",
        f"  truncated: {'yes' if bool(report.get('truncated')) else 'no'}",
        f"  markers: {', '.join(str(item) for item in markers)}",
    ]
    if items:
        lines.append("  todos:")
        for item in items:
            lines.append(
                "    - "
                f"{item.get('path')}:{item.get('line')} "
                f"[{item.get('marker')}] {item.get('text')}"
            )
    else:
        lines.append("  todos: none")
    lines.append(f"  message: {report.get('message') or ''}")
    return "\n".join(lines)


def format_manifest_summary(manifest: dict[str, object], max_items: int = 20) -> list[str]:
    path = str(manifest.get("path") or "")
    kind = str(manifest.get("kind") or "")
    name = str(manifest.get("name") or "")
    version = str(manifest.get("version") or "")
    item_count = int(manifest.get("item_count") or 0)
    ok = bool(manifest.get("ok"))
    truncated = bool(manifest.get("truncated"))
    items = [item for item in manifest.get("items", []) if isinstance(item, dict)] if isinstance(manifest.get("items"), list) else []
    title = f"    - {path} ({kind}, ok={'yes' if ok else 'no'}, items={item_count}, truncated={'yes' if truncated else 'no'})"
    if name or version:
        title += f" name={name or '.'} version={version or '.'}"
    lines = [title]
    if not ok:
        lines.append(f"      message: {manifest.get('message')}")
    for item in items[:max_items]:
        group = str(item.get("group") or "")
        name = str(item.get("name") or "")
        value = str(item.get("value") or "")
        suffix = f" = {value}" if value else ""
        lines.append(f"      - {group}: {name}{suffix}")
    if len(items) > max_items:
        lines.append(f"      - [{len(items) - max_items} additional item(s) omitted]")
    return lines
