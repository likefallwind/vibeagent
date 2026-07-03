from __future__ import annotations


def clip(value: str, max_length: int) -> str:
    if len(value) <= max_length:
        return value
    if max_length <= 3:
        return value[:max_length]
    return value[: max_length - 3] + "..."


def indent_block(value: str, spaces: int = 2) -> str:
    prefix = " " * spaces
    return "\n".join(f"{prefix}{line}" if line else prefix.rstrip() for line in value.splitlines())


def clip_with_flag(value: str, max_chars: int) -> tuple[str, bool]:
    if len(value) <= max_chars:
        return value, False
    if max_chars <= 0:
        return "", True
    if max_chars <= 20:
        return value[:max_chars], True
    suffix = "\n... [truncated]"
    return value[: max_chars - len(suffix)] + suffix, True


def format_git_status_report_text(report: dict[str, object]) -> str:
    status = report.get("status") if isinstance(report.get("status"), dict) else {}
    status_text = str(status.get("text") or "") if isinstance(status, dict) else ""
    lines = [
        "Git status:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  message: {report.get('message') or ''}",
    ]
    if status_text.strip():
        lines.append("  status:")
        lines.append(indent_block(status_text.strip(), spaces=4))
    else:
        lines.append("  status: none")
    return "\n".join(lines)


def format_git_conflicts_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    unmerged = report.get("unmerged") if isinstance(report.get("unmerged"), dict) else {}
    markers = report.get("markers") if isinstance(report.get("markers"), dict) else {}
    unmerged_items = [item for item in unmerged.get("items", []) if isinstance(item, dict)] if isinstance(unmerged.get("items"), list) else []
    marker_items = [item for item in markers.get("items", []) if isinstance(item, dict)] if isinstance(markers.get("items"), list) else []
    lines = [
        "Git conflicts:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  path: {report.get('path') or ''}",
        f"  unmerged: {len(unmerged_items)}/{int(unmerged.get('total', 0) or 0)}",
        f"  markers: {len(marker_items)}/{int(markers.get('total', 0) or 0)}",
        f"  scannedFiles: {int(report.get('scannedFiles', 0) or 0)}/{int(report.get('totalFiles', 0) or 0)}",
        f"  truncated: {'yes' if bool(report.get('truncated')) else 'no'}",
        f"  message: {message}",
    ]
    if not bool(report.get("ok")):
        return "\n".join(lines)

    if unmerged_items:
        lines.append("  unmergedFiles:")
        for item in unmerged_items:
            lines.append(f"    - {item.get('status') or ''} {item.get('path') or ''}")
    else:
        lines.append("  unmergedFiles: none")

    if marker_items:
        lines.append("  markerLines:")
        for item in marker_items:
            lines.append(f"    - {item.get('path') or ''}:{item.get('line') or ''} [{item.get('marker') or ''}] {item.get('text') or ''}")
    else:
        lines.append("  markerLines: none")
    return "\n".join(lines)


def format_git_info_report_text(report: dict[str, object]) -> str:
    remotes = report.get("remotes") if isinstance(report.get("remotes"), list) else []
    status = report.get("status") if isinstance(report.get("status"), dict) else {}
    status_text = str(status.get("text") or "") if isinstance(status, dict) else ""
    lines = [
        "Git info:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  isGitRepo: {'yes' if bool(report.get('isGitRepo')) else 'no'}",
        f"  branch: {report.get('branch') or '.'}",
        f"  head: {report.get('head') or '.'}",
        f"  upstream: {report.get('upstream') or '.'}",
        f"  ahead: {report.get('ahead', 0)}",
        f"  behind: {report.get('behind', 0)}",
    ]
    if remotes:
        lines.append("  remotes:")
        for remote in remotes:
            if isinstance(remote, dict):
                lines.append(f"    - {remote.get('name')} ({remote.get('kind')}): {remote.get('url')}")
    else:
        lines.append("  remotes: none")
    if status_text.strip():
        lines.append("  status:")
        lines.append(indent_block(status_text.strip(), spaces=4))
    else:
        lines.append("  status: none")
    lines.append(f"  message: {report.get('message') or ''}")
    return "\n".join(lines)


def format_branches_report_text(report: dict[str, object]) -> str:
    branches = report.get("branches") if isinstance(report.get("branches"), dict) else {}
    items = branches.get("items") if isinstance(branches, dict) and isinstance(branches.get("items"), list) else []
    status = report.get("gitStatus") if isinstance(report.get("gitStatus"), dict) else {}
    status_text = str(status.get("text") or "") if isinstance(status, dict) else ""
    lines = [
        "Branches:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  current: {report.get('current') or 'detached-or-none'}",
        f"  branches: {branches.get('shown', 0)}/{branches.get('total', 0)}",
        f"  truncated: {'yes' if bool(branches.get('truncated')) else 'no'}",
    ]
    if items:
        lines.append("  items:")
        for branch in items:
            if isinstance(branch, dict):
                marker = "*" if branch.get("current") else "-"
                lines.append(f"    {marker} {branch.get('name')}")
    else:
        lines.append("  items: none")
    if status_text.strip():
        lines.append("  gitStatus:")
        lines.append(indent_block(clip(status_text.strip(), 2_000), spaces=4))
    lines.append(f"  message: {report.get('message') or ''}")
    return "\n".join(lines)


def format_log_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    commits = report.get("commits") if isinstance(report.get("commits"), dict) else {}
    log_text = str(report.get("log") or "")
    lines = [
        "Log:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  path: {report.get('path') or '.'}",
        f"  maxCount: {report.get('maxCount', 0)}",
        f"  commits: {commits.get('shown', 0)}",
        f"  message: {message}",
    ]
    if log_text.strip():
        lines.append("  items:")
        lines.append(indent_block(log_text.strip(), spaces=4))
    else:
        lines.append("  items: none")
    return "\n".join(lines)


def format_show_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    output = report.get("output") if isinstance(report.get("output"), dict) else {}
    output_text = str(output.get("text") or "") if isinstance(output, dict) else ""
    lines = [
        "Show:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  rev: {report.get('rev') or 'HEAD'}",
        f"  path: {report.get('path') or '.'}",
        f"  maxOutputChars: {output.get('maxOutputChars', 0) if isinstance(output, dict) else 0}",
        f"  truncated: {'yes' if bool(output.get('truncated')) else 'no'}",
        f"  message: {message}",
    ]
    if output_text.strip():
        lines.append("  output:")
        lines.append(indent_block(output_text.strip(), spaces=4))
    else:
        lines.append("  output: none")
    return "\n".join(lines)


def format_blame_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    output = report.get("output") if isinstance(report.get("output"), dict) else {}
    output_text = str(output.get("text") or "") if isinstance(output, dict) else ""
    lines = [
        "Blame:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  path: {report.get('path') or ''}",
        f"  range: {report.get('range') or '.'}",
        f"  maxOutputChars: {output.get('maxOutputChars', 0) if isinstance(output, dict) else 0}",
        f"  truncated: {'yes' if bool(output.get('truncated')) else 'no'}",
        f"  message: {message}",
    ]
    if output_text.strip():
        lines.append("  output:")
        lines.append(indent_block(output_text.strip(), spaces=4))
    else:
        lines.append("  output: none")
    return "\n".join(lines)
