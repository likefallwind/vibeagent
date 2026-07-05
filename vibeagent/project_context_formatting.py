from __future__ import annotations

from .check_commands import format_structured_command_checks
from .process_report_helpers import format_structured_command_output_analysis_lines
from .types import ProjectCommand


def _indent_block(value: str, spaces: int = 2) -> str:
    indent = " " * spaces
    return "\n".join(f"{indent}{line}" if line else "" for line in value.splitlines())


def format_project_command(item: ProjectCommand) -> str:
    availability = "available" if item.available else f"missing {item.missing_tool}"
    return f"    - [{availability}] {item.command} (cwd: {item.cwd}, source: {item.file})"


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


def format_run_focused_test_commands_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    target_paths = [str(item) for item in report.get("targetPaths", [])] if isinstance(report.get("targetPaths"), list) else []
    focused = report.get("focusedCommands") if isinstance(report.get("focusedCommands"), dict) else {}
    focused_items = (
        [item for item in focused.get("items", []) if isinstance(item, dict)]
        if isinstance(focused.get("items"), list)
        else []
    )
    results = [item for item in report.get("results", []) if isinstance(item, dict)] if isinstance(report.get("results"), list) else []
    lines = [
        "Run focused test commands:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  clean: {'yes' if bool(report.get('clean')) else 'no'}",
        f"  targetPaths: {len(target_paths)}",
        f"  focusedCommands: {int(focused.get('shown', 0) or 0)}/{int(focused.get('total', 0) or 0)}",
        f"  ran: {int(report.get('ran', len(results)) or 0)}",
        f"  skippedUnavailable: {int(report.get('skippedUnavailable', 0) or 0)}",
        f"  truncated: {'yes' if bool(report.get('truncated')) else 'no'}",
        f"  stopOnFailure: {'yes' if bool(report.get('stopOnFailure')) else 'no'}",
        f"  stoppedEarly: {'yes' if bool(report.get('stoppedEarly')) else 'no'}",
        f"  durationMs: {report.get('durationMs', 0)}",
        f"  message: {message}",
    ]
    if target_paths:
        lines.append("  targets:")
        lines.extend(f"    - {path}" for path in target_paths)
    else:
        lines.append("  targets: none")
    if focused_items:
        lines.append("  focusedCommands:")
        for command in focused_items:
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
        lines.append("  focusedCommands: none")
    selected_not_run = report.get("selectedCommandsNotRun") if isinstance(report.get("selectedCommandsNotRun"), dict) else {}
    if isinstance(selected_not_run.get("items"), list):
        not_run = [item for item in selected_not_run.get("items", []) if isinstance(item, dict)]
    else:
        not_run = focused_items[len(results) :] if bool(report.get("stoppedEarly")) else []
    if not_run:
        lines.append(f"  selectedCommandsNotRun: {len(not_run)}")
        for command in not_run:
            lines.append(f"    - command: {command.get('command') or ''}")
            lines.append(f"      cwd: {command.get('cwd') or '.'}")
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
                    f"      clean: {'yes' if bool(result.get('clean')) else 'no'}",
                    f"      exitCode: {result.get('exitCode') if result.get('exitCode') is not None else '.'}",
                    f"      timedOut: {'yes' if bool(result.get('timedOut')) else 'no'}",
                    f"      signal: {result.get('signal') or '.'}",
                    f"      timeoutMs: {result.get('timeoutMs', 0)}",
                    f"      durationMs: {result.get('durationMs', 0)}",
                    f"      maxOutputChars: {result.get('maxOutputChars', 0)}",
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
