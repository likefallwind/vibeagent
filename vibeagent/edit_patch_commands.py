from __future__ import annotations

from pathlib import Path
import sys

from .actions import execute_action as _default_execute_action
from .edit_executable_commands import (
    format_executable_observation,
    format_executable_report_text,
    get_check_set_executable_report,
    get_check_set_executable_text,
    get_set_executable_report,
    get_set_executable_text,
    serialize_executable_report,
)
from .edit_patch_report_helpers import get_patch_command_report, get_patches_command_report
from .edit_regex_commands import (
    format_regex_replace_observation,
    format_regex_replace_report_text,
    get_check_regex_replace_report,
    get_check_regex_replace_text,
    get_regex_replace_report,
    get_regex_replace_text,
    serialize_regex_replace_report,
)
from .types import (
    CheckPatchAction,
    CheckPatchesAction,
    PatchFileAction,
    PatchFilesAction,
)


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
