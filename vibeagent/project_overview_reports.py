from __future__ import annotations

from .project_command_utils import clip as _clip
from .project_command_utils import field_value as _field_value
from .project_command_utils import indent_block as _indent_block
from .workflow_commands import format_review_check


def format_project_command_report_item(item: object) -> str:
    available = bool(_field_value(item, "available", False))
    missing_tool = str(_field_value(item, "missing_tool", "") or "")
    command = str(_field_value(item, "command", "") or "")
    cwd = str(_field_value(item, "cwd", ".") or ".")
    source = str(_field_value(item, "file", "") or "")
    availability = "available" if available else f"missing {missing_tool}"
    return f"    - [{availability}] {command} (cwd: {cwd}, source: {source})"


def format_overview_report_text(report: dict[str, object]) -> str:
    git = report.get("git") if isinstance(report.get("git"), dict) else {}
    files = report.get("files") if isinstance(report.get("files"), dict) else {}
    tree = report.get("tree") if isinstance(report.get("tree"), dict) else {}
    commands = report.get("commands") if isinstance(report.get("commands"), dict) else {}
    manifests = report.get("manifests") if isinstance(report.get("manifests"), dict) else {}
    instructions = report.get("instructions") if isinstance(report.get("instructions"), dict) else {}
    suggested_checks = report.get("suggestedChecks") if isinstance(report.get("suggestedChecks"), dict) else {}
    tools = report.get("tools") if isinstance(report.get("tools"), dict) else {}

    lines = [
        "Overview:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  gitRepo: {'yes' if bool(git.get('isRepo')) else 'no'}",
    ]
    if bool(git.get("isRepo")):
        branch = str(git.get("branch") or "(detached)")
        upstream = str(git.get("upstream") or "none")
        lines.append(f"  git: {branch} {git.get('head') or ''} upstream={upstream} ahead={git.get('ahead', 0)} behind={git.get('behind', 0)}")
    lines.extend(
        [
            f"  files: {files.get('shown', 0)}/{files.get('total', 0)}",
            f"  treeEntries: {tree.get('shown', 0)}/{tree.get('total', 0)}",
            f"  repoTruncated: {'yes' if bool(tree.get('truncated')) else 'no'}",
            f"  commands: {commands.get('shown', 0)}/{commands.get('total', 0)}",
            f"  manifests: {manifests.get('shown', 0)}/{manifests.get('total', 0)}",
            f"  instructions: {instructions.get('shown', 0)}/{instructions.get('total', 0)}",
            f"  suggestedChecks: {suggested_checks.get('shown', 0)}/{suggested_checks.get('total', 0)}",
            f"  tools: {tools.get('available', 0)}/{tools.get('total', 0)} available",
        ]
    )
    command_items = commands.get("items") if isinstance(commands.get("items"), list) else []
    if command_items:
        lines.append("  commandList:")
        lines.extend(format_project_command_report_item(item) for item in command_items[:10])
    suggested_items = suggested_checks.get("items") if isinstance(suggested_checks.get("items"), list) else []
    if suggested_items:
        lines.append("  checks:")
        lines.extend(format_review_check(item) for item in suggested_items[:10] if isinstance(item, dict))
    manifest_items = manifests.get("items") if isinstance(manifests.get("items"), list) else []
    if manifest_items:
        lines.append("  manifestList:")
        for manifest in manifest_items[:10]:
            if isinstance(manifest, dict):
                lines.append(f"    - {manifest.get('path')} ({manifest.get('kind')}, items={manifest.get('item_count')}, ok={'yes' if bool(manifest.get('ok')) else 'no'})")
    instruction_sources = instructions.get("sources") if isinstance(instructions.get("sources"), list) else []
    if instruction_sources:
        lines.append("  instructionSources:")
        for source in instruction_sources[:10]:
            if isinstance(source, dict):
                lines.append(
                    "    - "
                    f"{source.get('path')} "
                    f"(scope={source.get('scope')}, included={'yes' if bool(source.get('included')) else 'no'}, "
                    f"empty={'yes' if bool(source.get('empty')) else 'no'})"
                )
    tool_items = tools.get("items") if isinstance(tools.get("items"), list) else []
    if tool_items:
        lines.append("  toolAvailability:")
        for tool in tool_items[:20]:
            if isinstance(tool, dict):
                lines.append(f"    - {tool.get('name')}: {'yes' if bool(tool.get('available')) else 'no'}")
    git_status = str(git.get("status") or "")
    if git_status.strip():
        lines.append("  gitStatus:")
        lines.append(_indent_block(_clip(git_status.strip(), 2_000), spaces=4))
    lines.append(f"  message: {report.get('message') or ''}")
    return "\n".join(lines)
