from __future__ import annotations

import re
from pathlib import Path

from .code_action_executor import execute_code_action
from .python_action_executor import execute_python_action
from .read_action_code_outline_observations import code_outline_observation
from .lsp_runtime import execute_plugin_lsp_query
from .types import (
    CodeDefinitionsAction,
    CodeOutlineAction,
    CodeReferencesAction,
    LspQueryAction,
    Observation,
    PythonDefinitionsAction,
    PythonReferencesAction,
    ToolErrorObservation,
)
from .workspace_core import RunWorkspace
from .workspace_file_helpers import read_utf8_text_file
from .workspace_resolve import resolve_inside_run


LSP_MAX_SOURCE_BYTES = 2_000_000
SYMBOL_PATTERN = re.compile(r"[\w$]+", re.UNICODE)


def execute_lsp_action(workspace: RunWorkspace, action: LspQueryAction) -> Observation:
    try:
        plugin_observation = execute_plugin_lsp_query(workspace, action)
    except (OSError, UnicodeError, ValueError, TimeoutError) as error:
        return ToolErrorObservation(kind="tool_error", tool="LSP", message=str(error))
    if plugin_observation is not None:
        return plugin_observation

    if action.operation == "documentSymbol":
        return code_outline_observation(
            workspace,
            CodeOutlineAction(type="code_outline", paths=[action.path or ""], max_symbols=action.max_results),
        )

    try:
        symbol = action.symbol or _symbol_at_position(workspace, action.path or "", action.line, action.character)
    except ValueError as error:
        return ToolErrorObservation(kind="tool_error", tool="LSP", message=str(error))

    python_source = bool(action.path and Path(action.path).suffix.lower() == ".py")
    if action.operation == "findReferences":
        delegated = (
            PythonReferencesAction(type="python_references", symbol=symbol, path=action.path, max_matches=action.max_results)
            if python_source
            else CodeReferencesAction(type="code_references", symbol=symbol, path=action.path, max_matches=action.max_results)
        )
    else:
        max_matches = 1 if action.operation == "hover" else action.max_results
        delegated = (
            PythonDefinitionsAction(type="python_definitions", symbol=symbol, path=action.path, max_matches=max_matches, max_lines=120)
            if python_source
            else CodeDefinitionsAction(type="code_definitions", symbol=symbol, path=action.path, max_matches=max_matches, max_lines=120)
        )

    observation = execute_python_action(workspace, delegated) if python_source else execute_code_action(workspace, delegated)
    if observation is None:
        raise AssertionError(f"Unhandled delegated LSP action: {delegated!r}")
    if action.operation == "workspaceSymbol" and not python_source and action.path is None and getattr(observation, "total", 0) == 0:
        python_action = PythonDefinitionsAction(
            type="python_definitions", symbol=symbol, path=None, max_matches=action.max_results, max_lines=120
        )
        python_observation = execute_python_action(workspace, python_action)
        if python_observation is not None and getattr(python_observation, "total", 0) > 0:
            return python_observation
    return observation


def _symbol_at_position(
    workspace: RunWorkspace,
    path: str,
    line: int | None,
    character: int | None,
) -> str:
    if line is None or character is None:
        raise ValueError("LSP position requires line and character.")
    target = resolve_inside_run(workspace, path)
    if not target.is_file():
        raise ValueError(f"File does not exist: {path}")
    if target.stat().st_size > LSP_MAX_SOURCE_BYTES:
        raise ValueError(f"LSP source file exceeds {LSP_MAX_SOURCE_BYTES} bytes: {path}")
    lines = read_utf8_text_file(target, path).splitlines()
    line_index = 0 if line == 0 else line - 1
    if line_index < 0 or line_index >= len(lines):
        raise ValueError(f"LSP line is outside {path}: {line}")
    source_line = lines[line_index]
    candidates = [_python_index_from_utf16(source_line, character)]
    if character > 0:
        candidates.append(_python_index_from_utf16(source_line, character - 1))
    matches = list(SYMBOL_PATTERN.finditer(source_line))
    for index in candidates:
        for match in matches:
            if match.start() <= index < match.end() or (index == match.end() and index > match.start()):
                return match.group(0)
    for index in candidates:
        nearest = min(matches, key=lambda match: min(abs(match.start() - index), abs(match.end() - index)), default=None)
        if nearest is not None and min(abs(nearest.start() - index), abs(nearest.end() - index)) <= 1:
            return nearest.group(0)
    raise ValueError(f"LSP position does not identify a symbol in {path}:{line}:{character}.")


def _python_index_from_utf16(value: str, utf16_offset: int) -> int:
    units = 0
    for index, character in enumerate(value):
        if units >= utf16_offset:
            return index
        units += 2 if ord(character) > 0xFFFF else 1
    return len(value)
