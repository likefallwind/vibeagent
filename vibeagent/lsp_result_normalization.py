from __future__ import annotations

from pathlib import Path
from urllib.parse import unquote, urlparse


def normalize_lsp_query_result(
    project_root: Path,
    operation: str,
    value: object,
    max_results: int,
) -> tuple[list[dict[str, object]], int, bool]:
    if value is None:
        return [], 0, False
    if operation in {"goToDefinition", "goToImplementation", "findReferences"}:
        source = value if isinstance(value, list) else [value]
        results = [selected for item in source if (selected := _location(project_root, item)) is not None]
    elif operation == "hover":
        results = [_hover(value)] if isinstance(value, dict) else []
    elif operation == "documentSymbol":
        results = _document_symbols(value)
    else:
        source = value if isinstance(value, list) else [value]
        results = [selected for item in source if (selected := _workspace_symbol(project_root, item)) is not None]
    total = len(results)
    return results[:max_results], total, total > max_results


def normalize_lsp_diagnostics(
    project_root: Path,
    path: Path,
    diagnostics: list[object],
    max_results: int,
) -> tuple[list[dict[str, object]], int, bool]:
    relative = path.resolve().relative_to(project_root.resolve()).as_posix()
    results: list[dict[str, object]] = []
    for item in diagnostics:
        if not isinstance(item, dict):
            continue
        selected: dict[str, object] = {"path": relative}
        if (range_value := _range(item.get("range"))) is not None:
            selected["range"] = range_value
        for key in ("severity", "code", "source"):
            value = item.get(key)
            if isinstance(value, (str, int)) and not isinstance(value, bool):
                selected[key] = value
        message = item.get("message")
        selected["message"] = message[:4_000] if isinstance(message, str) else ""
        results.append(selected)
    total = len(results)
    return results[:max_results], total, total > max_results


def _location(project_root: Path, value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    uri = value.get("uri", value.get("targetUri"))
    range_value = value.get("range", value.get("targetSelectionRange", value.get("targetRange")))
    relative = _relative_uri(project_root, uri)
    selected_range = _range(range_value)
    if relative is None or selected_range is None:
        return None
    return {"path": relative, "range": selected_range}


def _hover(value: dict[object, object]) -> dict[str, object]:
    selected: dict[str, object] = {"contents": _bounded_json(value.get("contents"), 0)}
    if (range_value := _range(value.get("range"))) is not None:
        selected["range"] = range_value
    return selected


def _document_symbols(value: object) -> list[dict[str, object]]:
    source = value if isinstance(value, list) else []
    results: list[dict[str, object]] = []

    def visit(items: list[object], container: str | None = None) -> None:
        for item in items:
            if len(results) >= 1_000 or not isinstance(item, dict):
                continue
            name = item.get("name")
            selected_range = _range(item.get("selectionRange", item.get("range")))
            if not isinstance(name, str) or selected_range is None:
                continue
            selected: dict[str, object] = {"name": name[:500], "range": selected_range}
            if isinstance(item.get("kind"), int):
                selected["symbolKind"] = item["kind"]
            selected_container = item.get("containerName", container)
            if isinstance(selected_container, str):
                selected["containerName"] = selected_container[:500]
            results.append(selected)
            children = item.get("children")
            if isinstance(children, list):
                visit(children, name)

    visit(source)
    return results


def _workspace_symbol(project_root: Path, value: object) -> dict[str, object] | None:
    if not isinstance(value, dict) or not isinstance(value.get("name"), str):
        return None
    location = _location(project_root, value.get("location"))
    if location is None:
        return None
    selected: dict[str, object] = {"name": value["name"][:500], **location}
    if isinstance(value.get("kind"), int):
        selected["symbolKind"] = value["kind"]
    if isinstance(value.get("containerName"), str):
        selected["containerName"] = value["containerName"][:500]
    return selected


def _range(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    start = _position(value.get("start"))
    end = _position(value.get("end"))
    if start is None or end is None:
        return None
    return {"start": start, "end": end}


def _position(value: object) -> dict[str, int] | None:
    if not isinstance(value, dict):
        return None
    line = value.get("line")
    character = value.get("character")
    if not isinstance(line, int) or not isinstance(character, int) or line < 0 or character < 0:
        return None
    return {"line": line + 1, "character": character}


def _relative_uri(project_root: Path, value: object) -> str | None:
    if not isinstance(value, str):
        return None
    parsed = urlparse(value)
    if parsed.scheme != "file" or parsed.netloc not in {"", "localhost"}:
        return None
    path = Path(unquote(parsed.path)).resolve()
    try:
        return path.relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return None


def _bounded_json(value: object, depth: int) -> object:
    if depth >= 5:
        return "..."
    if isinstance(value, str):
        return value[:20_000]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    if isinstance(value, list):
        return [_bounded_json(item, depth + 1) for item in value[:100]]
    if isinstance(value, dict):
        return {
            str(key)[:200]: _bounded_json(item, depth + 1)
            for key, item in list(value.items())[:100]
        }
    return str(value)[:1_000]


__all__ = ["normalize_lsp_diagnostics", "normalize_lsp_query_result"]
