from __future__ import annotations

from typing import Any

from .action_tool_alias_utils import rename_fields, truthy_alias_bool


GREP_TYPE_FILE_GLOBS = {
    "c": "*.c",
    "cc": "*.cc",
    "cpp": "*.cpp",
    "cs": "*.cs",
    "css": "*.css",
    "go": "*.go",
    "h": "*.h",
    "hpp": "*.hpp",
    "html": "*.html",
    "java": "*.java",
    "js": "*.js",
    "json": "*.json",
    "jsx": "*.jsx",
    "kt": "*.kt",
    "md": "*.md",
    "php": "*.php",
    "py": "*.py",
    "python": "*.py",
    "rb": "*.rb",
    "rs": "*.rs",
    "rust": "*.rs",
    "sh": "*.sh",
    "swift": "*.swift",
    "toml": "*.toml",
    "ts": "*.ts",
    "tsx": "*.tsx",
    "xml": "*.xml",
    "yaml": "*.yaml",
    "yml": "*.yml",
}


def normalize_search_input(value: dict[str, Any]) -> dict[str, Any]:
    normalized = rename_fields(value, {"pattern": "query", "head_limit": "max_matches", "glob": "file_glob"})
    _normalize_search_type_alias(normalized)
    if truthy_alias_bool(normalized.pop("-i", False)) and "case_sensitive" not in normalized:
        normalized["case_sensitive"] = False
    _normalize_search_context_aliases(normalized)
    if normalized.get("output_mode") == "content" and "context_lines" not in normalized:
        normalized["context_lines"] = 2
    return normalized


def _normalize_search_type_alias(value: dict[str, Any]) -> None:
    grep_type = value.pop("type", None)
    if "file_glob" in value or not isinstance(grep_type, str):
        return
    normalized_type = grep_type.strip().lower().lstrip(".")
    if not normalized_type:
        return
    file_glob = GREP_TYPE_FILE_GLOBS.get(normalized_type)
    if file_glob is not None:
        value["file_glob"] = file_glob
    elif normalized_type.isalnum() and len(normalized_type) <= 8:
        value["file_glob"] = f"*.{normalized_type}"


def _normalize_search_context_aliases(value: dict[str, Any]) -> None:
    context = value.pop("-C", None)
    after = value.pop("-A", None)
    before = value.pop("-B", None)
    if "context_lines" in value:
        return
    if context is not None:
        value["context_lines"] = context
        return
    directional = [item for item in (after, before) if item is not None]
    if directional:
        value["context_lines"] = _max_directional_context(directional)


def _max_directional_context(values: list[Any]) -> Any:
    numeric_values = []
    for value in values:
        if type(value) is int:
            numeric_values.append(value)
            continue
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.isdigit():
                numeric_values.append(int(stripped))
                continue
        return value
    return max(numeric_values)
