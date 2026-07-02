from __future__ import annotations

from pathlib import Path
import sys

from .actions import execute_action as _default_execute_action
from .edit_command_parsing import (
    parse_executable_argument,
    parse_regex_replace_argument,
)
from .edit_patch_report_helpers import get_patch_command_report, get_patches_command_report
from .types import (
    CheckPatchAction,
    CheckPatchesAction,
    CheckRegexReplaceAction,
    CheckSetExecutableAction,
    PatchFileAction,
    PatchFilesAction,
    RegexReplaceAction,
    SetExecutableAction,
)
from .workspace_core import RunWorkspace


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


def _format_command_text(
    title: str,
    report_name: str,
    report_default: object,
    formatter_name: str,
    formatter_default: object,
    project_root: str | Path,
    argument: str | None,
    **kwargs: object,
) -> str:
    get_report = _commands_attr(report_name, report_default)
    formatter = _commands_attr(formatter_name, formatter_default)
    return formatter(title, get_report(project_root, argument, **kwargs))


def get_check_set_executable_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
    executable: bool | str | None = None,
) -> str:
    return format_executable_report_text(
        "Check executable:",
        get_check_set_executable_report(project_root, argument, path=path, executable=executable),
    )


def get_check_set_executable_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
    executable: bool | str | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        parsed_path, parsed_executable = parse_executable_argument(
            argument,
            path=path,
            executable=executable,
            usage="/check-executable <path> [true|false]",
        )
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "kind": "check_set_executable",
            "ok": False,
            "path": path or "",
            "executable": executable if isinstance(executable, bool) else False,
            "modeBefore": "",
            "modeAfter": "",
            "message": f"Usage: /check-executable <path> [true|false]\nError: {error}",
        }
    workspace = RunWorkspace(root=root, run_id="local-check-executable", session_dir=root / ".vibeagent" / "sessions" / "local-check-executable")
    observation = _execute_action(workspace, CheckSetExecutableAction(type="check_set_executable", path=parsed_path, executable=parsed_executable))
    return serialize_executable_report(root, observation)


def get_set_executable_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
    executable: bool | str | None = None,
) -> str:
    return format_executable_report_text(
        "Set executable:",
        get_set_executable_report(project_root, argument, path=path, executable=executable),
    )


def get_set_executable_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
    executable: bool | str | None = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        parsed_path, parsed_executable = parse_executable_argument(
            argument,
            path=path,
            executable=executable,
            usage="/set-executable <path> [true|false]",
        )
    except ValueError as error:
        return {
            "projectRoot": str(root),
            "kind": "set_executable",
            "ok": False,
            "path": path or "",
            "executable": executable if isinstance(executable, bool) else False,
            "modeBefore": "",
            "modeAfter": "",
            "message": f"Usage: /set-executable <path> [true|false]\nError: {error}",
        }
    workspace = RunWorkspace(root=root, run_id="local-set-executable", session_dir=root / ".vibeagent" / "sessions" / "local-set-executable")
    observation = _execute_action(workspace, SetExecutableAction(type="set_executable", path=parsed_path, executable=parsed_executable))
    return serialize_executable_report(root, observation)


def get_check_patch_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
    patch: str | None = None,
) -> str:
    return _format_command_text(
        "Check patch:",
        "get_check_patch_report",
        get_check_patch_report,
        "format_patch_report_text",
        format_patch_report_text,
        project_root,
        argument,
        path=path,
        patch=patch,
    )


def get_check_patch_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
    patch: str | None = None,
) -> dict[str, object]:
    return get_patch_command_report(
        project_root,
        argument,
        path=path,
        patch=patch,
        kind="check_patch",
        usage="/check-patch <path> <patch|->",
        run_id="local-check-patch",
        action_factory=lambda kind, parsed_path, parsed_patch: CheckPatchAction(
            type=kind,
            path=parsed_path,
            patch=parsed_patch,
        ),
        execute_action=_execute_action,
        serialize_report=serialize_patch_report,
    )


def get_patch_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
    patch: str | None = None,
) -> str:
    return _format_command_text(
        "Patch:",
        "get_patch_report",
        get_patch_report,
        "format_patch_report_text",
        format_patch_report_text,
        project_root,
        argument,
        path=path,
        patch=patch,
    )


def get_patch_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
    patch: str | None = None,
) -> dict[str, object]:
    return get_patch_command_report(
        project_root,
        argument,
        path=path,
        patch=patch,
        kind="patch_file",
        usage="/patch <path> <patch|->",
        run_id="local-patch",
        action_factory=lambda kind, parsed_path, parsed_patch: PatchFileAction(
            type=kind,
            path=parsed_path,
            patch=parsed_patch,
        ),
        execute_action=_execute_action,
        serialize_report=serialize_patch_report,
    )


def get_check_patches_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    patch: str | None = None,
) -> str:
    return _format_command_text(
        "Check patches:",
        "get_check_patches_report",
        get_check_patches_report,
        "format_patches_report_text",
        format_patches_report_text,
        project_root,
        argument,
        patch=patch,
    )


def get_check_patches_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    patch: str | None = None,
) -> dict[str, object]:
    return get_patches_command_report(
        project_root,
        argument,
        patch=patch,
        kind="check_patches",
        usage="/check-patches <patch|->",
        run_id="local-check-patches",
        action_factory=lambda kind, parsed_patch: CheckPatchesAction(type=kind, patch=parsed_patch),
        execute_action=_execute_action,
        serialize_report=serialize_patches_report,
    )


def get_patches_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    patch: str | None = None,
) -> str:
    return _format_command_text(
        "Patches:",
        "get_patches_report",
        get_patches_report,
        "format_patches_report_text",
        format_patches_report_text,
        project_root,
        argument,
        patch=patch,
    )


def get_patches_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    patch: str | None = None,
) -> dict[str, object]:
    return get_patches_command_report(
        project_root,
        argument,
        patch=patch,
        kind="patch_files",
        usage="/patches <patch|->",
        run_id="local-patches",
        action_factory=lambda kind, parsed_patch: PatchFilesAction(type=kind, patch=parsed_patch),
        execute_action=_execute_action,
        serialize_report=serialize_patches_report,
    )


def format_executable_observation(title: str, root: Path, observation: object) -> str:
    return format_executable_report_text(title, serialize_executable_report(root, observation))


def serialize_executable_report(root: Path, observation: object) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "kind": str(getattr(observation, "kind", "") or ""),
        "ok": bool(getattr(observation, "ok", False)),
        "path": str(getattr(observation, "path", "") or ""),
        "executable": bool(getattr(observation, "executable", False)),
        "modeBefore": str(getattr(observation, "mode_before", "") or ""),
        "modeAfter": str(getattr(observation, "mode_after", "") or ""),
        "message": str(getattr(observation, "message", "") or ""),
    }


def format_executable_report_text(title: str, report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    return "\n".join(
        [
            title,
            f"  projectRoot: {report.get('projectRoot') or '.'}",
            f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
            f"  path: {report.get('path') or ''}",
            f"  executable: {'yes' if bool(report.get('executable')) else 'no'}",
            f"  modeBefore: {report.get('modeBefore') or ''}",
            f"  modeAfter: {report.get('modeAfter') or ''}",
            f"  message: {message}",
        ]
    )


def format_patch_observation(title: str, root: Path, observation: object) -> str:
    return format_patch_report_text(title, serialize_patch_report(root, observation))


def serialize_patch_report(root: Path, observation: object) -> dict[str, object]:
    diff = str(getattr(observation, "diff", "") or "")
    return {
        "projectRoot": str(root),
        "kind": str(getattr(observation, "kind", "") or ""),
        "ok": bool(getattr(observation, "ok", False)),
        "path": str(getattr(observation, "path", "") or ""),
        "message": str(getattr(observation, "message", "") or ""),
        "diff": {"text": diff, "lines": diff.splitlines(), "lineCount": len(diff.splitlines())},
    }


def format_patch_report_text(title: str, report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    lines = [
        title,
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  path: {report.get('path') or ''}",
        f"  message: {message}",
    ]
    diff_report = report.get("diff") if isinstance(report.get("diff"), dict) else {}
    diff = str(diff_report.get("text") or "")
    if diff:
        lines.append("  diff:")
        for diff_line in diff.splitlines():
            lines.append(f"    {diff_line}")
    return "\n".join(lines)


def format_patches_observation(title: str, root: Path, observation: object) -> str:
    return format_patches_report_text(title, serialize_patches_report(root, observation))


def serialize_patches_report(root: Path, observation: object) -> dict[str, object]:
    files = [str(file_path) for file_path in list(getattr(observation, "files", []))]
    diff = str(getattr(observation, "diff", "") or "")
    return {
        "projectRoot": str(root),
        "kind": str(getattr(observation, "kind", "") or ""),
        "ok": bool(getattr(observation, "ok", False)),
        "files": {"total": len(files), "items": files},
        "message": str(getattr(observation, "message", "") or ""),
        "diff": {"text": diff, "lines": diff.splitlines(), "lineCount": len(diff.splitlines())},
    }


def format_patches_report_text(title: str, report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    files_report = report.get("files") if isinstance(report.get("files"), dict) else {}
    files = [str(path) for path in files_report.get("items", [])] if isinstance(files_report.get("items"), list) else []
    lines = [
        title,
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  files: {int(files_report.get('total', len(files)) or 0)}",
        f"  message: {message}",
    ]
    if files:
        lines.append("  paths:")
        for file_path in files:
            lines.append(f"    - {file_path}")
    diff_report = report.get("diff") if isinstance(report.get("diff"), dict) else {}
    diff = str(diff_report.get("text") or "")
    if diff:
        lines.append("  diff:")
        for diff_line in diff.splitlines():
            lines.append(f"    {diff_line}")
    return "\n".join(lines)


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
        return {
            "projectRoot": str(root),
            "kind": "check_regex_replace",
            "ok": False,
            "path": path or "",
            "pattern": pattern or "",
            "replacement": replacement or "",
            "count": count,
            "caseSensitive": bool(case_sensitive),
            "multiline": bool(multiline),
            "maxReplacements": max_replacements,
            "replacements": 0,
            "message": f"Usage: /check-regex-replace [--ignore-case] [--multiline] [--count N] [--max-replacements N] <path> <pattern> <replacement>\nError: {error}",
            "diff": {"text": "", "lines": [], "lineCount": 0},
        }
    workspace = RunWorkspace(root=root, run_id="local-check-regex-replace", session_dir=root / ".vibeagent" / "sessions" / "local-check-regex-replace")
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
        return {
            "projectRoot": str(root),
            "kind": "regex_replace",
            "ok": False,
            "path": path or "",
            "pattern": pattern or "",
            "replacement": replacement or "",
            "count": count,
            "caseSensitive": bool(case_sensitive),
            "multiline": bool(multiline),
            "maxReplacements": max_replacements,
            "replacements": 0,
            "message": f"Usage: /regex-replace [--ignore-case] [--multiline] [--count N] [--max-replacements N] <path> <pattern> <replacement>\nError: {error}",
            "diff": {"text": "", "lines": [], "lineCount": 0},
        }
    workspace = RunWorkspace(root=root, run_id="local-regex-replace", session_dir=root / ".vibeagent" / "sessions" / "local-regex-replace")
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
