from __future__ import annotations

from pathlib import Path
import sys

from .actions import execute_action as _default_execute_action
from .edit_command_parsing import parse_regex_replace_argument
from .edit_usage_report_helpers import line_edit_usage_report
from .local_command_workspace import local_command_workspace
from .types import CheckRegexReplaceAction, RegexReplaceAction


def _execute_action(*args: object, **kwargs: object) -> object:
    commands_module = sys.modules.get("vibeagent.commands")
    command_execute_action = getattr(commands_module, "execute_action", None) if commands_module is not None else None
    if command_execute_action is not None:
        return command_execute_action(*args, **kwargs)
    return _default_execute_action(*args, **kwargs)


def _commands_attr(name: str, default: object) -> object:
    commands_module = sys.modules.get("vibeagent.commands")
    if commands_module is None:
        return default
    return getattr(commands_module, name, default)


def get_check_regex_replace_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
    pattern: str | None = None,
    replacement: str | None = None,
    count: int = 0,
    case_sensitive: bool = True,
    multiline: bool = False,
    max_replacements: int = 100,
) -> str:
    return format_regex_replace_report_text(
        "Check regex replace:",
        get_check_regex_replace_report(
            project_root,
            argument,
            path=path,
            pattern=pattern,
            replacement=replacement,
            count=count,
            case_sensitive=case_sensitive,
            multiline=multiline,
            max_replacements=max_replacements,
        ),
    )


def get_check_regex_replace_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
    pattern: str | None = None,
    replacement: str | None = None,
    count: int = 0,
    case_sensitive: bool = True,
    multiline: bool = False,
    max_replacements: int = 100,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        parsed = parse_regex_replace_argument(
            argument,
            path=path,
            pattern=pattern,
            replacement=replacement,
            count=count,
            case_sensitive=case_sensitive,
            multiline=multiline,
            max_replacements=max_replacements,
            usage="/check-regex-replace [opts] <path> <pattern> <replacement>",
        )
    except ValueError as error:
        return line_edit_usage_report(
            root,
            "check_regex_replace",
            "/check-regex-replace [--ignore-case] [--multiline] [--count N] [--max-replacements N] <path> <pattern> <replacement>",
            error,
            path=path,
            fields={
                "pattern": pattern or "",
                "replacement": replacement or "",
                "count": count,
                "caseSensitive": bool(case_sensitive),
                "multiline": bool(multiline),
                "maxReplacements": max_replacements,
                "replacements": 0,
            },
        )
    workspace = local_command_workspace(root, "local-check-regex-replace")
    observation = _execute_action(workspace, CheckRegexReplaceAction(type="check_regex_replace", **parsed))
    return serialize_regex_replace_report(root, observation, parsed)


def get_regex_replace_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
    pattern: str | None = None,
    replacement: str | None = None,
    count: int = 0,
    case_sensitive: bool = True,
    multiline: bool = False,
    max_replacements: int = 100,
) -> str:
    get_report = _commands_attr("get_regex_replace_report", get_regex_replace_report)
    formatter = _commands_attr("format_regex_replace_report_text", format_regex_replace_report_text)
    return formatter(
        "Regex replace:",
        get_report(
            project_root,
            argument,
            path=path,
            pattern=pattern,
            replacement=replacement,
            count=count,
            case_sensitive=case_sensitive,
            multiline=multiline,
            max_replacements=max_replacements,
        ),
    )


def get_regex_replace_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
    pattern: str | None = None,
    replacement: str | None = None,
    count: int = 0,
    case_sensitive: bool = True,
    multiline: bool = False,
    max_replacements: int = 100,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        parsed = parse_regex_replace_argument(
            argument,
            path=path,
            pattern=pattern,
            replacement=replacement,
            count=count,
            case_sensitive=case_sensitive,
            multiline=multiline,
            max_replacements=max_replacements,
            usage="/regex-replace [opts] <path> <pattern> <replacement>",
        )
    except ValueError as error:
        return line_edit_usage_report(
            root,
            "regex_replace",
            "/regex-replace [--ignore-case] [--multiline] [--count N] [--max-replacements N] <path> <pattern> <replacement>",
            error,
            path=path,
            fields={
                "pattern": pattern or "",
                "replacement": replacement or "",
                "count": count,
                "caseSensitive": bool(case_sensitive),
                "multiline": bool(multiline),
                "maxReplacements": max_replacements,
                "replacements": 0,
            },
        )
    workspace = local_command_workspace(root, "local-regex-replace")
    observation = _execute_action(workspace, RegexReplaceAction(type="regex_replace", **parsed))
    return serialize_regex_replace_report(root, observation, parsed)


def format_regex_replace_observation(title: str, root: Path, observation: object) -> str:
    return format_regex_replace_report_text(title, serialize_regex_replace_report(root, observation))


def serialize_regex_replace_report(root: Path, observation: object, parsed: dict[str, object] | None = None) -> dict[str, object]:
    parsed = parsed or {}
    diff = str(getattr(observation, "diff", "") or "")
    return {
        "projectRoot": str(root),
        "kind": str(getattr(observation, "kind", "") or ""),
        "ok": bool(getattr(observation, "ok", False)),
        "path": str(getattr(observation, "path", "") or ""),
        "pattern": str(getattr(observation, "pattern", "") or ""),
        "replacement": str(parsed.get("replacement", "") or ""),
        "count": int(getattr(observation, "count", 0) or 0),
        "caseSensitive": bool(parsed.get("case_sensitive", True)),
        "multiline": bool(parsed.get("multiline", False)),
        "maxReplacements": int(parsed.get("max_replacements", 0) or 0),
        "replacements": int(getattr(observation, "replacements", 0) or 0),
        "message": str(getattr(observation, "message", "") or ""),
        "diff": {"text": diff, "lines": diff.splitlines(), "lineCount": len(diff.splitlines())},
    }


def format_regex_replace_report_text(title: str, report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    lines = [
        title,
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  path: {report.get('path') or ''}",
        f"  pattern: {report.get('pattern') or ''}",
        f"  count: {report.get('count') or 0}",
        f"  replacements: {report.get('replacements') or 0}",
        f"  message: {message}",
    ]
    diff_report = report.get("diff") if isinstance(report.get("diff"), dict) else {}
    diff = str(diff_report.get("text") or "")
    if diff:
        lines.append("  diff:")
        for diff_line in diff.splitlines():
            lines.append(f"    {diff_line}")
    return "\n".join(lines)
