from __future__ import annotations

from .types import Observation


READ_NEXT_ACTION_KINDS = {
    "read_file",
    "read_file_context",
    "read_file_contexts",
    "tail_file",
    "read_files",
    "read_file_ranges",
    "file_info",
    "image_info",
    "view_image",
    "repo_map",
    "python_symbols",
    "code_outline",
    "python_dependencies",
    "code_dependencies",
    "code_references",
    "code_reference_contexts",
    "code_definitions",
    "code_rename_preview",
    "python_definitions",
    "python_calls",
    "python_call_graph",
    "python_references",
    "python_reference_contexts",
    "python_rename_preview",
    "list_files",
    "list_tree",
    "search",
    "search_contexts",
    "find_files",
    "glob",
}


def _format_next_action_items(items: list[str], max_items: int = 3) -> str:
    shown = items[:max_items]
    suffix = "" if len(items) <= max_items else f"; +{len(items) - max_items} more"
    return "; ".join(shown) + suffix


def _path_label(latest: Observation) -> str:
    path = str(getattr(latest, "path", "") or "").strip()
    return path or "the selected source"


def _paths_from_values(values: object, attr: str = "path") -> list[str]:
    if not isinstance(values, list):
        return []
    paths: list[str] = []
    for value in values:
        path = str(getattr(value, attr, "") or "").strip()
        if path:
            paths.append(path)
    return paths


def _string_items(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(value).strip() for value in values if str(value).strip()]


def _reference_labels(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    labels: list[str] = []
    for value in values:
        path = str(getattr(value, "path", "") or "").strip()
        line = getattr(value, "line", None)
        symbol = str(getattr(value, "symbol", "") or "").strip()
        label = path
        if path and isinstance(line, int):
            label = f"{path}:{line}"
        if label and symbol:
            label = f"{label} {symbol}"
        if label:
            labels.append(label)
    return labels


def _read_next_action_instruction(base: str, latest: Observation) -> str:
    if latest.kind == "read_file":
        target = _path_label(latest)
        if getattr(latest, "truncated", False):
            return (
                f"{base} Source file {target} was read but truncated. Use read_file with start_line/line_count, "
                "read_file_context, or search_contexts for the missing section before editing."
            )
        return (
            f"{base} Source file {target} was read. Use the content to choose the next edit, inspect neighboring "
            "or referenced code if needed, or run the relevant verification if the requested change is complete."
        )

    if latest.kind in {"read_file_context", "tail_file"}:
        target = _path_label(latest)
        if not getattr(latest, "ok", True):
            return f"{base} Targeted file context for {target} could not be read. Check the path or line and choose another inspection."
        return (
            f"{base} Targeted file context for {target} was read. Use it to make the edit or decide the next focused inspection; "
            "run verification once the relevant change is complete."
        )

    if latest.kind == "read_file_contexts":
        paths = _paths_from_values(getattr(latest, "contexts", []))
        if paths:
            return (
                f"{base} Multiple file contexts were read for {_format_next_action_items(paths)}. "
                "Use them to make the coordinated edit or choose the next focused inspection before verifying."
            )
        return f"{base} No file contexts were read. Check the requested locations or use search_contexts to find the relevant code."

    if latest.kind == "read_files":
        paths = _paths_from_values(getattr(latest, "files", []))
        if paths:
            return (
                f"{base} Files were read: {_format_next_action_items(paths)}. Use the compared content to edit, "
                "inspect missing references, or run relevant verification if the task is complete."
            )
        return f"{base} No files were read. Check the paths, use list_files, or search for the target code."

    if latest.kind == "read_file_ranges":
        paths = _paths_from_values(getattr(latest, "ranges", []))
        if paths:
            return (
                f"{base} Focused file ranges were read for {_format_next_action_items(paths)}. "
                "Use them to edit the relevant code or run the targeted verification."
            )
        return f"{base} No file ranges were read. Check the line ranges or use read_file_context for a known location."

    return ""


def _search_next_action_instruction(base: str, latest: Observation) -> str:
    if latest.kind == "search":
        total = int(getattr(latest, "total", 0) or 0)
        if total > 0:
            matches = _string_items(getattr(latest, "matches", []))
            target = _format_next_action_items(matches) if matches else f"{total} match(es)"
            return (
                f"{base} Search found {total} match(es): {target}. Use search_contexts, read_file_context, "
                "or read_file to inspect the relevant match before editing."
            )
        return f"{base} Search found no matches. Adjust the query, broaden the path, or use list_tree/repo_map to locate the code."

    if latest.kind == "search_contexts":
        total = int(getattr(latest, "total", 0) or 0)
        if total > 0:
            labels = _reference_labels(getattr(latest, "contexts", []))
            target = _format_next_action_items(labels) if labels else f"{total} context(s)"
            return (
                f"{base} Search contexts located {total} match context(s): {target}. "
                "Use the context to edit the relevant code, or inspect adjacent definitions before verifying."
            )
        return f"{base} Search contexts found no matches. Adjust the query or inspect the likely file directly."

    if latest.kind in {"find_files", "glob"}:
        total = int(getattr(latest, "total", 0) or 0)
        if total > 0:
            matches = _string_items(getattr(latest, "matches", []))
            return (
                f"{base} File discovery found {total} match(es): {_format_next_action_items(matches)}. "
                "Use read_file, read_files, or read_file_context on the most relevant path."
            )
        return f"{base} File discovery found no matches. Adjust the pattern or use list_tree/repo_map for broader orientation."

    return ""


def _structure_next_action_instruction(base: str, latest: Observation) -> str:
    if latest.kind in {"list_files", "list_tree"}:
        total = int(getattr(latest, "total", 0) or 0)
        if total > 0:
            return (
                f"{base} Directory listing found {total} item(s). Use read_file/read_files for likely source files, "
                "or search/search_contexts if you know the symbol or text to change."
            )
        return f"{base} Directory listing is empty. Check the path or use repo_map from the project root."

    if latest.kind == "repo_map":
        total = int(getattr(latest, "total_files", 0) or 0)
        return (
            f"{base} Repo map summarized {total} file(s). Use code_definitions, code_references, search_contexts, "
            "or read_file for the most relevant module before editing."
        )

    if latest.kind in {"file_info", "image_info"}:
        paths = _paths_from_values(getattr(latest, "files", []))
        if paths:
            return (
                f"{base} File metadata was read for {_format_next_action_items(paths)}. "
                "Use it to choose the right read/edit tool, or continue with verification if no edit is needed."
            )
        return f"{base} File metadata did not identify a usable target. Check the path or inspect the directory."

    if latest.kind == "view_image":
        if getattr(latest, "ok", False):
            return f"{base} Use the visual content and image metadata to continue the requested implementation or review."
        return f"{base} The image could not be shown. Fix the path, format, or size limit, or continue from available source evidence."

    return ""


def _code_intel_next_action_instruction(base: str, latest: Observation) -> str:
    if latest.kind in {"python_symbols", "code_outline"}:
        total = int(getattr(latest, "total", 0) or 0)
        if total > 0:
            return (
                f"{base} Code structure was found. Use code_definitions, python_definitions, read_file_context, "
                "or references for the target symbol before editing."
            )
        return f"{base} Code structure found no symbols. Use search_contexts or read_file to inspect manually."

    if latest.kind in {"code_references", "python_references", "python_calls", "python_call_graph"}:
        total = int(getattr(latest, "total", 0) or 0)
        if total > 0:
            labels = _reference_labels(
                getattr(latest, "references", None)
                or getattr(latest, "calls", None)
                or getattr(latest, "edges", None)
                or []
            )
            target = _format_next_action_items(labels) if labels else f"{total} reference(s)"
            return (
                f"{base} Code references were found: {target}. Use code_reference_contexts, python_reference_contexts, "
                "or read_file_context to inspect the impacted sites before editing."
            )
        return f"{base} No code references were found. Confirm the symbol name or inspect definitions directly."

    if latest.kind in {"code_reference_contexts", "python_reference_contexts"}:
        total = int(getattr(latest, "total", 0) or 0)
        if total > 0:
            labels = _reference_labels(getattr(latest, "contexts", []))
            return (
                f"{base} Reference contexts were read: {_format_next_action_items(labels)}. "
                "Use them to make a safe coordinated edit, then run related or focused tests."
            )
        return f"{base} Reference contexts found no usable sites. Use code_references or direct file reads to recover."

    if latest.kind in {"code_definitions", "python_definitions"}:
        total = int(getattr(latest, "total", 0) or 0)
        if total > 0:
            definitions = getattr(latest, "definitions", [])
            labels = _reference_labels(definitions)
            return (
                f"{base} Definitions were found: {_format_next_action_items(labels)}. "
                "Edit the target definition or inspect references before making a cross-file change."
            )
        return f"{base} No definitions were found. Use search_contexts, repo_map, or code_references to locate the symbol."

    if latest.kind in {"python_dependencies", "code_dependencies"}:
        total = int(getattr(latest, "total", 0) or 0)
        return (
            f"{base} Dependency information was read for {total} file(s). Use it to inspect impacted modules, "
            "then edit and run relevant verification."
        )

    if latest.kind in {"code_rename_preview", "python_rename_preview"}:
        total = int(getattr(latest, "total_replacements", 0) or 0)
        if getattr(latest, "ok", False):
            return (
                f"{base} Rename preview found {total} replacement(s). Review the diff; apply the rename only if all "
                "replacement sites are correct, then run focused verification."
            )
        return f"{base} Rename preview failed. Inspect errors, references, or definitions before trying another rename."

    return ""


def read_next_action_instruction(base: str, latest: Observation) -> str:
    instruction = _read_next_action_instruction(base, latest)
    if instruction:
        return instruction
    instruction = _search_next_action_instruction(base, latest)
    if instruction:
        return instruction
    instruction = _structure_next_action_instruction(base, latest)
    if instruction:
        return instruction
    instruction = _code_intel_next_action_instruction(base, latest)
    if instruction:
        return instruction

    raise ValueError(f"Unsupported read next-action kind: {latest.kind}")
