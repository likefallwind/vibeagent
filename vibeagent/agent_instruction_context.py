from __future__ import annotations

from .workspace_core import RunWorkspace
from .workspace_project_instructions import read_path_instruction_context
from .workspace_instruction_state import DEFAULT_INSTRUCTION_CONSUMER


LAZY_INSTRUCTION_OBSERVATION_KINDS = {
    "code_outline",
    "notebook_read",
    "python_symbols",
    "read_file",
    "read_file_context",
    "read_file_contexts",
    "read_file_ranges",
    "read_files",
    "tail_file",
}


def instruction_context_for_observation(
    workspace: RunWorkspace,
    observation: object,
    consumer_id: str = DEFAULT_INSTRUCTION_CONSUMER,
) -> dict[str, object] | None:
    if getattr(observation, "kind", None) not in LAZY_INSTRUCTION_OBSERVATION_KINDS:
        return None
    paths = _successful_observation_paths(observation)
    if not paths:
        return None
    try:
        context = read_path_instruction_context(workspace, paths, consumer_id=consumer_id)
    except (OSError, ValueError) as error:
        return {
            "ok": False,
            "paths": paths,
            "files": [],
            "text": "",
            "message": f"Could not load path-scoped instructions: {error}",
        }
    return context if context["files"] else None


def _successful_observation_paths(observation: object) -> list[str]:
    kind = str(getattr(observation, "kind", ""))
    if kind in {"read_file", "read_file_context", "tail_file", "notebook_read"}:
        if getattr(observation, "ok", True) is False:
            return []
        if kind == "read_file" and getattr(observation, "total_bytes", None) is None:
            return []
        return _one_path(getattr(observation, "path", None))
    items = []
    for attribute in ("contexts", "files", "ranges"):
        values = getattr(observation, attribute, None)
        if isinstance(values, list):
            items.extend(values)
    paths: list[str] = []
    for item in items:
        if getattr(item, "ok", True) is False:
            continue
        path = getattr(item, "path", None)
        if isinstance(path, str) and path and path not in paths:
            paths.append(path)
    return paths


def _one_path(value: object) -> list[str]:
    return [value] if isinstance(value, str) and value else []
