from __future__ import annotations

from .types import (
    CodeOutlineAction,
    CodeOutlineObservation,
    CodeOutlineResult,
    FileInfoAction,
    FileInfoObservation,
    FileInfoResult,
    ImageInfoAction,
    ImageInfoObservation,
    ImageInfoResult,
    Observation,
    PythonSymbol,
    PythonSymbolsAction,
    PythonSymbolsObservation,
    PythonSymbolsResult,
    ReadFileAction,
    ReadFileContextAction,
    ReadFileContextObservation,
    ReadFileContextResult,
    ReadFileContextsAction,
    ReadFileContextsObservation,
    ReadFileObservation,
    ReadFileRangeResult,
    ReadFileRangesAction,
    ReadFileRangesObservation,
    ReadFileResult,
    ReadFilesAction,
    ReadFilesObservation,
    TailFileAction,
    TailFileObservation,
)
from .workspace import (
    read_code_outline,
    read_project_file_context_result,
    read_project_file_info,
    read_project_file_result,
    read_project_file_tail_result,
    read_project_image_info,
    read_python_symbol_outline,
)
from .workspace_core import RunWorkspace


def execute_read_file_action(workspace: RunWorkspace, action: object) -> Observation | None:
    if isinstance(action, ReadFileAction):
        return read_file_observation(workspace, action)
    if isinstance(action, ReadFileContextAction):
        return read_file_context_observation(workspace, action)
    if isinstance(action, ReadFileContextsAction):
        return read_file_contexts_observation(workspace, action)
    if isinstance(action, TailFileAction):
        return tail_file_observation(workspace, action)
    if isinstance(action, ReadFilesAction):
        return read_files_observation(workspace, action)
    if isinstance(action, ReadFileRangesAction):
        return read_file_ranges_observation(workspace, action)
    if isinstance(action, FileInfoAction):
        return file_info_observation(workspace, action)
    if isinstance(action, ImageInfoAction):
        return image_info_observation(workspace, action)
    if isinstance(action, PythonSymbolsAction):
        return python_symbols_observation(workspace, action)
    if isinstance(action, CodeOutlineAction):
        return code_outline_observation(workspace, action)
    return None


def read_file_observation(workspace: RunWorkspace, action: ReadFileAction) -> ReadFileObservation:
    try:
        result = read_project_file_result(
            workspace,
            action.path,
            max_bytes=action.max_bytes,
            start_line=action.start_line,
            line_count=action.line_count,
            show_line_numbers=action.show_line_numbers,
        )
        content = str(result["content"])
        truncated = bool(result["truncated"])
        total_bytes = int(result["total_bytes"])
        max_bytes = int(result["max_bytes"])
        if action.start_line is None:
            message = f"Read {action.path}."
        else:
            message = f"Read {action.path} from line {action.start_line}."
    except ValueError as error:
        content = ""
        message = str(error)
        truncated = False
        total_bytes = None
        max_bytes = action.max_bytes
    return ReadFileObservation(
        kind="read_file",
        path=action.path,
        content=content,
        message=message,
        start_line=action.start_line,
        line_count=action.line_count,
        show_line_numbers=action.show_line_numbers,
        truncated=truncated,
        total_bytes=total_bytes,
        max_bytes=max_bytes,
    )


def read_file_context_observation(workspace: RunWorkspace, action: ReadFileContextAction) -> ReadFileContextObservation:
    try:
        result = read_project_file_context_result(
            workspace,
            action.path,
            line=action.line,
            context_lines=action.context_lines,
            max_bytes=action.max_bytes,
        )
        return ReadFileContextObservation(
            kind="read_file_context",
            path=action.path,
            ok=True,
            content=str(result["content"]),
            message=f"Read {action.path} around line {action.line}.",
            line=int(result["line"]),
            context_lines=int(result["context_lines"]),
            start_line=int(result["start_line"]),
            end_line=int(result["end_line"]),
            line_count=int(result["line_count"]),
            total_lines=int(result["total_lines"]),
            target_line_exists=bool(result["target_line_exists"]),
            truncated=bool(result["truncated"]),
            max_bytes=int(result["max_bytes"]),
        )
    except ValueError as error:
        return ReadFileContextObservation(
            kind="read_file_context",
            path=action.path,
            ok=False,
            content="",
            message=str(error),
            line=action.line,
            context_lines=action.context_lines,
            max_bytes=action.max_bytes,
        )


def read_file_contexts_observation(workspace: RunWorkspace, action: ReadFileContextsAction) -> ReadFileContextsObservation:
    contexts: list[ReadFileContextResult] = []
    for item in action.contexts:
        try:
            result = read_project_file_context_result(
                workspace,
                item.path,
                line=item.line,
                context_lines=item.context_lines,
                max_bytes=action.max_bytes_per_context,
            )
            contexts.append(
                ReadFileContextResult(
                    path=item.path,
                    line=int(result["line"]),
                    context_lines=int(result["context_lines"]),
                    ok=True,
                    content=str(result["content"]),
                    message=f"Read {item.path} around line {item.line}.",
                    start_line=int(result["start_line"]),
                    end_line=int(result["end_line"]),
                    line_count=int(result["line_count"]),
                    total_lines=int(result["total_lines"]),
                    target_line_exists=bool(result["target_line_exists"]),
                    truncated=bool(result["truncated"]),
                    max_bytes=int(result["max_bytes"]),
                )
            )
        except ValueError as error:
            contexts.append(
                ReadFileContextResult(
                    path=item.path,
                    line=item.line,
                    context_lines=item.context_lines,
                    ok=False,
                    content="",
                    message=str(error),
                    max_bytes=action.max_bytes_per_context,
                )
            )
    ok_count = sum(1 for item in contexts if item.ok)
    return ReadFileContextsObservation(
        kind="read_file_contexts",
        contexts=contexts,
        message=f"Read {ok_count}/{len(contexts)} file context(s).",
    )


def tail_file_observation(workspace: RunWorkspace, action: TailFileAction) -> TailFileObservation:
    try:
        result = read_project_file_tail_result(
            workspace,
            action.path,
            line_count=action.line_count,
            max_bytes=action.max_bytes,
        )
        return TailFileObservation(
            kind="tail_file",
            path=action.path,
            ok=True,
            content=str(result["content"]),
            message=f"Read last {result['line_count']} line(s) from {action.path}.",
            start_line=int(result["start_line"]),
            line_count=int(result["line_count"]),
            requested_line_count=int(result["requested_line_count"]),
            total_lines=int(result["total_lines"]),
            truncated=bool(result["truncated"]),
            max_bytes=int(result["max_bytes"]),
        )
    except ValueError as error:
        return TailFileObservation(
            kind="tail_file",
            path=action.path,
            ok=False,
            content="",
            message=str(error),
            requested_line_count=action.line_count,
            max_bytes=action.max_bytes,
        )


def read_files_observation(workspace: RunWorkspace, action: ReadFilesAction) -> ReadFilesObservation:
    files: list[ReadFileResult] = []
    for path in action.paths:
        try:
            result = read_project_file_result(
                workspace,
                path,
                max_bytes=action.max_bytes_per_file,
                show_line_numbers=action.show_line_numbers,
            )
            files.append(
                ReadFileResult(
                    path=path,
                    ok=True,
                    content=str(result["content"]),
                    message=f"Read {path}.",
                    truncated=bool(result["truncated"]),
                    total_bytes=int(result["total_bytes"]),
                    max_bytes=int(result["max_bytes"]),
                    show_line_numbers=action.show_line_numbers,
                )
            )
        except ValueError as error:
            files.append(
                ReadFileResult(
                    path=path,
                    ok=False,
                    content="",
                    message=str(error),
                    truncated=False,
                    total_bytes=None,
                    max_bytes=action.max_bytes_per_file,
                    show_line_numbers=action.show_line_numbers,
                )
            )
    ok_count = sum(1 for item in files if item.ok)
    return ReadFilesObservation(
        kind="read_files",
        files=files,
        message=f"Read {ok_count}/{len(files)} file(s).",
    )


def read_file_ranges_observation(workspace: RunWorkspace, action: ReadFileRangesAction) -> ReadFileRangesObservation:
    ranges: list[ReadFileRangeResult] = []
    for item in action.ranges:
        try:
            result = read_project_file_result(
                workspace,
                item.path,
                max_bytes=action.max_bytes_per_range,
                start_line=item.start_line,
                line_count=item.line_count,
            )
            content = str(result["content"])
            ranges.append(
                ReadFileRangeResult(
                    path=item.path,
                    start_line=item.start_line,
                    line_count=item.line_count,
                    ok=True,
                    content=content,
                    message=f"Read {item.path}:{item.start_line}+{item.line_count}.",
                    truncated=bool(result["truncated"]),
                    total_bytes=int(result["total_bytes"]),
                    max_bytes=int(result["max_bytes"]),
                )
            )
        except ValueError as error:
            ranges.append(
                ReadFileRangeResult(
                    path=item.path,
                    start_line=item.start_line,
                    line_count=item.line_count,
                    ok=False,
                    content="",
                    message=str(error),
                    truncated=False,
                    total_bytes=None,
                    max_bytes=action.max_bytes_per_range,
                )
            )
    ok_count = sum(1 for item in ranges if item.ok)
    return ReadFileRangesObservation(
        kind="read_file_ranges",
        ranges=ranges,
        message=f"Read {ok_count}/{len(ranges)} file range(s).",
    )


def file_info_observation(workspace: RunWorkspace, action: FileInfoAction) -> FileInfoObservation:
    files: list[FileInfoResult] = []
    for path in action.paths:
        try:
            info = read_project_file_info(workspace, path)
            files.append(FileInfoResult(**info))
        except ValueError as error:
            files.append(
                FileInfoResult(
                    path=path,
                    ok=False,
                    exists=False,
                    is_file=False,
                    is_dir=False,
                    size_bytes=None,
                    line_count=None,
                    is_binary=None,
                    message=str(error),
                )
            )
    ok_count = sum(1 for item in files if item.ok)
    return FileInfoObservation(
        kind="file_info",
        files=files,
        message=f"Inspected {ok_count}/{len(files)} path(s).",
    )


def image_info_observation(workspace: RunWorkspace, action: ImageInfoAction) -> ImageInfoObservation:
    images: list[ImageInfoResult] = []
    for path in action.paths:
        try:
            info = read_project_image_info(workspace, path)
            images.append(ImageInfoResult(**info))
        except ValueError as error:
            images.append(
                ImageInfoResult(
                    path=path,
                    ok=False,
                    exists=False,
                    is_file=False,
                    size_bytes=None,
                    format=None,
                    mime_type=None,
                    width=None,
                    height=None,
                    message=str(error),
                )
            )
    ok_count = sum(1 for item in images if item.ok)
    return ImageInfoObservation(
        kind="image_info",
        images=images,
        message=f"Inspected {ok_count}/{len(images)} image(s).",
    )


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
