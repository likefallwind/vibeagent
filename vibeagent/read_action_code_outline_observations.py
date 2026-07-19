from __future__ import annotations

from .types import (
    CodeOutlineAction,
    CodeOutlineObservation,
    CodeOutlineResult,
    PythonSymbol,
    PythonSymbolsAction,
    PythonSymbolsObservation,
    PythonSymbolsResult,
)
from .workspace import read_code_outline, read_python_symbol_outline
from .workspace_core import RunWorkspace


def python_symbols_observation(workspace: RunWorkspace, action: PythonSymbolsAction) -> PythonSymbolsObservation:
    files: list[PythonSymbolsResult] = []
    for path in action.paths:
        try:
            outline = read_python_symbol_outline(workspace, path)
            symbols = [PythonSymbol(**item) for item in outline["symbols"]]
            files.append(
                PythonSymbolsResult(
                    path=str(outline["path"]),
                    ok=True,
                    symbols=symbols,
                    imports=list(outline["imports"]),
                    message=str(outline["message"]),
                )
            )
        except ValueError as error:
            files.append(PythonSymbolsResult(path=path, ok=False, symbols=[], imports=[], message=str(error)))
    ok_count = sum(1 for item in files if item.ok)
    return PythonSymbolsObservation(
        kind="python_symbols",
        files=files,
        message=f"Read symbols for {ok_count}/{len(files)} Python file(s).",
    )


def code_outline_observation(workspace: RunWorkspace, action: CodeOutlineAction) -> CodeOutlineObservation:
    files: list[CodeOutlineResult] = []
    for path in action.paths:
        try:
            outline = read_code_outline(workspace, path, max_symbols=action.max_symbols)
            symbols = [PythonSymbol(**item) for item in outline["symbols"]]
            files.append(
                CodeOutlineResult(
                    path=str(outline["path"]),
                    ok=True,
                    language=str(outline["language"]),
                    symbols=symbols,
                    imports=list(outline["imports"]),
                    message=str(outline["message"]),
                )
            )
        except ValueError as error:
            files.append(CodeOutlineResult(path=path, ok=False, language=None, symbols=[], imports=[], message=str(error)))
    ok_count = sum(1 for item in files if item.ok)
    return CodeOutlineObservation(
        kind="code_outline",
        files=files,
        message=f"Read outlines for {ok_count}/{len(files)} source file(s).",
    )
