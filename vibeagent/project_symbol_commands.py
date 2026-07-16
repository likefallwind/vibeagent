from __future__ import annotations

from pathlib import Path

from .command_parsing import parse_local_path_args
from .local_command_workspace import local_command_workspace
from .project_command_utils import (
    commands_attr as _commands_attr,
    execute_action as _execute_action,
)
from .types import CodeOutlineAction


def serialize_symbol(symbol: object) -> dict[str, object]:
    return {
        "name": str(getattr(symbol, "name", "")),
        "kind": str(getattr(symbol, "kind", "")),
        "line": int(getattr(symbol, "line", 0)),
        "endLine": getattr(symbol, "end_line", None),
        "parent": getattr(symbol, "parent", None),
    }


def serialize_symbol_file(file: object) -> dict[str, object]:
    symbols = list(getattr(file, "symbols", []))
    imports = list(getattr(file, "imports", []))
    return {
        "path": str(getattr(file, "path", "")),
        "ok": bool(getattr(file, "ok", False)),
        "language": getattr(file, "language", None),
        "imports": imports,
        "symbols": [serialize_symbol(symbol) for symbol in symbols],
        "counts": {"imports": len(imports), "symbols": len(symbols)},
        "message": str(getattr(file, "message", "")),
    }


def format_serialized_symbol_file(file: dict[str, object]) -> list[str]:
    path = str(file.get("path") or "")
    language = str(file.get("language") or "code")
    imports = file.get("imports") if isinstance(file.get("imports"), list) else []
    symbols = file.get("symbols") if isinstance(file.get("symbols"), list) else []
    lines = [f"    - {path} ({language})"]
    if imports:
        import_values = [str(item) for item in imports if isinstance(item, str)]
        shown_imports = ", ".join(import_values[:8])
        suffix = f" (+{len(import_values) - 8} more)" if len(import_values) > 8 else ""
        lines.append(f"      imports: {shown_imports}{suffix}")
    if symbols:
        for symbol in symbols[:12]:
            if not isinstance(symbol, dict):
                continue
            kind = symbol.get("kind") or "symbol"
            name = symbol.get("name") or ""
            line = symbol.get("line") or 0
            parent = f" parent={symbol.get('parent')}" if symbol.get("parent") else ""
            lines.append(f"      - {kind} {name}:{line}{parent}")
        if len(symbols) > 12:
            lines.append(f"      - [{len(symbols) - 12} additional symbol(s) omitted]")
    else:
        lines.append("      symbols: none")
    return lines


def _symbols_failure_report(
    root: Path,
    message: str,
    *,
    paths: list[str] | None = None,
    max_symbols: int = 200,
) -> dict[str, object]:
    return {
        "projectRoot": str(root),
        "ok": False,
        "paths": paths or [],
        "maxSymbols": max_symbols,
        "files": {"ok": 0, "total": 0, "items": []},
        "counts": {"symbols": 0, "imports": 0},
        "message": message,
    }


def get_symbols_report(
    project_root: str | Path = ".",
    argument: str | list[str] | None = None,
    max_symbols: int = 200,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        paths = parse_symbols_paths(argument)
    except ValueError as error:
        return _symbols_failure_report(root, f"Usage: /symbols <path...>\nError: {error}", max_symbols=max_symbols)
    if not paths:
        return _symbols_failure_report(root, "Usage: /symbols <path...>", max_symbols=max_symbols)

    workspace = local_command_workspace(root, "local-symbols")
    observation = _execute_action(
        workspace,
        CodeOutlineAction(
            type="code_outline",
            paths=paths,
            max_symbols=max_symbols,
        ),
    )
    if observation.kind != "code_outline":
        return _symbols_failure_report(
            root,
            f"Unexpected observation: {observation.kind}",
            paths=paths,
            max_symbols=max_symbols,
        )

    items = [serialize_symbol_file(file) for file in observation.files]
    ok_count = sum(1 for item in items if bool(item["ok"]))
    symbol_count = sum(int(item["counts"]["symbols"]) for item in items if bool(item["ok"]))
    import_count = sum(int(item["counts"]["imports"]) for item in items if bool(item["ok"]))
    return {
        "projectRoot": str(root),
        "ok": ok_count == len(items),
        "paths": paths,
        "maxSymbols": max_symbols,
        "files": {"ok": ok_count, "total": len(items), "items": items},
        "counts": {"symbols": symbol_count, "imports": import_count},
        "message": observation.message,
    }


def format_symbols_report_text(report: dict[str, object]) -> str:
    message = str(report.get("message") or "")
    if message.startswith("Usage:"):
        return message
    files = report.get("files") if isinstance(report.get("files"), dict) else {}
    items = files.get("items") if isinstance(files, dict) and isinstance(files.get("items"), list) else []
    counts = report.get("counts") if isinstance(report.get("counts"), dict) else {}
    lines = [
        "Symbols:",
        f"  projectRoot: {report.get('projectRoot') or '.'}",
        f"  files: {files.get('ok', 0)}/{files.get('total', 0)}",
        f"  symbols: {counts.get('symbols', 0)}",
        f"  imports: {counts.get('imports', 0)}",
    ]
    if items:
        lines.append("  outlines:")
        for file in items:
            if not isinstance(file, dict):
                continue
            if bool(file.get("ok")):
                lines.extend(format_serialized_symbol_file(file))
            else:
                lines.append(f"    - {file.get('path')} (error): {file.get('message')}")
    else:
        lines.append("  outlines: none")
    lines.append(f"  message: {message}")
    return "\n".join(lines)


def get_symbols_text(
    project_root: str | Path = ".",
    argument: str | list[str] | None = None,
    max_symbols: int = 200,
) -> str:
    get_report = _commands_attr("get_symbols_report", get_symbols_report)
    formatter = _commands_attr("format_symbols_report_text", format_symbols_report_text)
    return formatter(get_report(project_root, argument, max_symbols=max_symbols))


def parse_symbols_paths(argument: str | list[str] | None) -> list[str]:
    return parse_local_path_args(argument, max_paths=20)
