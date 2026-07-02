from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path
import sys

from .actions import execute_action as _default_execute_action


def plain_data(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    if isinstance(value, list):
        return [plain_data(item) for item in value]
    if isinstance(value, dict):
        return {str(key): plain_data(item) for key, item in value.items()}
    return value


def execute_action_for_commands(*args: object, **kwargs: object) -> object:
    commands_module = sys.modules.get("vibeagent.commands")
    command_execute_action = getattr(commands_module, "execute_action", None) if commands_module is not None else None
    if command_execute_action is not None:
        return command_execute_action(*args, **kwargs)
    return _default_execute_action(*args, **kwargs)


def commands_attr(name: str, default: object) -> object:
    commands_module = sys.modules.get("vibeagent.commands")
    if commands_module is None:
        return default
    return getattr(commands_module, name, default)


def symbol_report_base(
    project_root: str | Path,
    usage: str,
    parser,
    argument: str | None,
    symbol: str | None,
    path: str | None,
) -> tuple[Path, str | None, str | None, dict[str, object] | None]:
    root = Path(project_root).resolve()
    try:
        parsed_symbol, parsed_path = parser(argument, symbol=symbol, path=path, usage=usage)
    except ValueError as error:
        return root, None, None, {
            "projectRoot": str(root),
            "ok": False,
            "symbol": symbol or "",
            "path": path or ".",
            "items": {"shown": 0, "total": 0, "truncated": False, "results": []},
            "errors": [str(error)],
            "message": f"Usage: {usage}\nError: {error}",
        }
    return root, parsed_symbol, parsed_path, None


def rename_usage_report(root: Path, usage: str, symbol: str | None, new_name: str | None, path: str | None, max_files: int, max_replacements: int, error: str) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "symbol": symbol or "",
        "newName": new_name or "",
        "path": path or ".",
        "files": {"shown": 0, "total": 0, "truncated": False, "items": []},
        "totalFiles": 0,
        "totalReplacements": 0,
        "truncated": False,
        "errors": [error],
        "diff": "",
        "maxFiles": max_files,
        "maxReplacements": max_replacements,
        "message": f"Usage: {usage}\nError: {error}",
    }


def rename_unexpected_report(root: Path, symbol: str, new_name: str, path: str | None, max_files: int, max_replacements: int, message: str) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "symbol": symbol,
        "newName": new_name,
        "path": path or ".",
        "files": {"shown": 0, "total": 0, "truncated": False, "items": []},
        "totalFiles": 0,
        "totalReplacements": 0,
        "truncated": False,
        "errors": [],
        "diff": "",
        "maxFiles": max_files,
        "maxReplacements": max_replacements,
        "message": message,
    }


def rename_observation_report(root: Path, observation: object, *, max_files: int, max_replacements: int) -> dict[str, object]:
    files = list(getattr(observation, "files"))
    total_files = int(getattr(observation, "total_files"))
    return {
        "projectRoot": str(root),
        "ok": bool(getattr(observation, "ok")),
        "symbol": getattr(observation, "symbol"),
        "newName": getattr(observation, "new_name"),
        "path": getattr(observation, "path") or ".",
        "files": {
            "shown": len(files),
            "total": total_files,
            "truncated": bool(getattr(observation, "truncated", False)),
            "items": [plain_data(item) for item in files],
        },
        "totalFiles": total_files,
        "totalReplacements": int(getattr(observation, "total_replacements")),
        "truncated": bool(getattr(observation, "truncated", False)),
        "errors": list(getattr(observation, "errors")),
        "diff": str(getattr(observation, "diff", "")),
        "maxFiles": max_files,
        "maxReplacements": max_replacements,
        "message": str(getattr(observation, "message")),
    }


def format_rename_report_text(title: str, report: dict[str, object], *, include_language: bool) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    files = report.get("files") if isinstance(report.get("files"), dict) else {}
    items = files.get("items") if isinstance(files.get("items"), list) else []
    diff = str(report.get("diff") or "")
    lines = [
        title,
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  ok: {'yes' if bool(report.get('ok')) else 'no'}",
        f"  rename: {report.get('symbol') or ''} -> {report.get('newName') or ''}",
        f"  path: {report.get('path') or '.'}",
        f"  files: {files.get('shown', 0)}/{files.get('total', 0)}",
        f"  replacements: {report.get('totalReplacements', 0)}",
        f"  truncated: {'yes' if bool(report.get('truncated')) else 'no'}",
        f"  message: {message}",
    ]
    _append_errors(lines, report.get("errors"))
    if items:
        lines.append("  files:")
        for item in items:
            if not isinstance(item, dict):
                continue
            replacements = item.get("replacements") if isinstance(item.get("replacements"), list) else []
            if include_language:
                lines.append(
                    f"    - {item.get('path')} ({item.get('language')}): "
                    f"replacements={len(replacements)} truncated={'yes' if bool(item.get('truncated')) else 'no'}"
                )
            else:
                lines.append(f"    - {item.get('path')}: replacements={len(replacements)} truncated={'yes' if bool(item.get('truncated')) else 'no'}")
            for replacement in replacements:
                if not isinstance(replacement, dict):
                    continue
                detail = str(replacement.get("language") if include_language else replacement.get("kind") or "").strip()
                prefix = f"{detail}: " if detail else ""
                lines.append(f"      - {replacement.get('line')}:{replacement.get('column')}-{replacement.get('end_column')} {prefix}{replacement.get('old')} -> {replacement.get('new')} :: {replacement.get('context')}")
            item_diff = str(item.get("diff") or "")
            if item_diff:
                lines.append("      diff:")
                lines.extend(f"        {diff_line}" for diff_line in item_diff.splitlines())
    else:
        lines.append("  files: none")
    if diff:
        lines.append("  diff:")
        lines.extend(f"    {diff_line}" for diff_line in diff.splitlines())
    return "\n".join(lines)


def _append_errors(lines: list[str], errors: object) -> None:
    if isinstance(errors, list) and errors:
        lines.append("  errors:")
        for error in errors:
            lines.append(f"    - {error}")
