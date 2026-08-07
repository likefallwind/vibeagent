from __future__ import annotations

from .project_test_formatting import (
    format_check_focused_test_commands_report_text,
    format_focused_test_commands_report_text,
    format_related_tests_report_text,
    format_run_focused_test_commands_report_text,
)
from .types import ProjectCommand


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
