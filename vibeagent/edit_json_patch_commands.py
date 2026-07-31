from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path
import sys

from .actions import execute_action as _default_execute_action
from .edit_command_parsing import parse_json_patch_argument
from .edit_usage_report_helpers import line_edit_usage_report
from .local_command_workspace import local_command_workspace
from .types import CheckJsonPatchAction, JsonPatchAction, JsonPatchOperation


def _plain_data(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    if isinstance(value, list):
        return [_plain_data(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _plain_data(item) for key, item in value.items()}
    return value


def _execute_action(*args: object, **kwargs: object) -> object:
    commands_module = sys.modules.get("vibeagent.commands")
    command_execute_action = getattr(commands_module, "execute_action", None) if commands_module is not None else None
    if command_execute_action is not None:
        return command_execute_action(*args, **kwargs)
    return _default_execute_action(*args, **kwargs)


def get_check_json_patch_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
    operations: object = None,
) -> str:
    return format_json_patch_report_text(
        "Check JSON patch:",
        get_check_json_patch_report(project_root, argument, path=path, operations=operations),
    )


def get_check_json_patch_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
    operations: object = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        parsed_path, parsed_operations = parse_json_patch_argument(
            argument,
            path=path,
            operations=operations,
            usage="/check-json-patch <path> <json-ops-array>",
        )
    except ValueError as error:
        return line_edit_usage_report(
            root,
            "check_json_patch",
            "/check-json-patch <path> <json-ops-array>",
            error,
            path=path,
            fields={"operations": {"total": 0, "items": []}},
        )
    workspace = local_command_workspace(root, "local-check-json-patch")
    observation = _execute_action(workspace, CheckJsonPatchAction(type="check_json_patch", path=parsed_path, operations=parsed_operations))
    return serialize_json_patch_report(root, observation, operations=parsed_operations)


def get_json_patch_text(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
    operations: object = None,
) -> str:
    return format_json_patch_report_text(
        "JSON patch:",
        get_json_patch_report(project_root, argument, path=path, operations=operations),
    )


def get_json_patch_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    *,
    path: str | None = None,
    operations: object = None,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        parsed_path, parsed_operations = parse_json_patch_argument(
            argument,
            path=path,
            operations=operations,
            usage="/json-patch <path> <json-ops-array>",
        )
    except ValueError as error:
        return line_edit_usage_report(
            root,
            "json_patch",
            "/json-patch <path> <json-ops-array>",
            error,
            path=path,
            fields={"operations": {"total": 0, "items": []}},
        )
    workspace = local_command_workspace(root, "local-json-patch")
    observation = _execute_action(workspace, JsonPatchAction(type="json_patch", path=parsed_path, operations=parsed_operations))
    return serialize_json_patch_report(root, observation, operations=parsed_operations)


def format_json_patch_observation(title: str, root: Path, observation: object) -> str:
    return format_json_patch_report_text(title, serialize_json_patch_report(root, observation))


def serialize_json_patch_report(root: Path, observation: object, *, operations: list[JsonPatchOperation] | None = None) -> dict[str, object]:
    operation_items = _plain_data(operations or [])
    diff = str(getattr(observation, "diff", "") or "")
    operation_count = int(getattr(observation, "operation_count", len(operation_items)) or 0)
    return {
        "projectRoot": str(root),
        "kind": str(getattr(observation, "kind", "") or ""),
        "ok": bool(getattr(observation, "ok", False)),
        "path": str(getattr(observation, "path", "") or ""),
        "operations": {"total": operation_count, "items": operation_items},
        "message": str(getattr(observation, "message", "") or ""),
        "diff": {"text": diff, "lines": diff.splitlines(), "lineCount": len(diff.splitlines())},
    }


def format_json_patch_report_text(title: str, report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    operations_report = report.get("operations") if isinstance(report.get("operations"), dict) else {}
    lines = [
        title,
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  path: {report.get('path') or ''}",
        f"  operations: {int(operations_report.get('total', 0) or 0)}",
        f"  message: {message}",
    ]
    diff_report = report.get("diff") if isinstance(report.get("diff"), dict) else {}
    diff = str(diff_report.get("text") or "")
    if diff:
        lines.append("  diff:")
        for diff_line in diff.splitlines():
            lines.append(f"    {diff_line}")
    return "\n".join(lines)
