from __future__ import annotations

from .output_conversion import output_context_results_from_dicts, output_diagnostics_from_dicts
from .types import (
    AgentAction,
    CodeOutlineAction,
    CodeOutlineObservation,
    CodeOutlineResult,
    FileInfoAction,
    FileInfoObservation,
    FileInfoResult,
    ImageInfoAction,
    ImageInfoObservation,
    ImageInfoResult,
    ListFilesAction,
    ListFilesObservation,
    ListTreeAction,
    ListTreeObservation,
    Observation,
    OutputContextsAction,
    OutputContextsObservation,
    OutputDiagnosticsAction,
    OutputDiagnosticsObservation,
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
    RepoMapAction,
    RepoMapObservation,
    RepoMapPythonFile,
    TailFileAction,
    TailFileObservation,
)
from .workspace import (
    build_repo_map,
    list_project_files,
    list_project_tree,
    read_code_outline,
    read_output_contexts_result,
    read_output_diagnostics_result,
    read_project_file_context_result,
    read_project_file_info,
    read_project_file_result,
    read_project_file_tail_result,
    read_project_image_info,
    read_python_symbol_outline,
)


def execute_read_action(workspace, action: AgentAction) -> Observation | None:
    if isinstance(action, ListFilesAction):
        try:
            files, total = list_project_files(workspace, action.path)
            truncated = len(files) < total
            message = f"Found {total} file(s)."
            if truncated:
                message += f" Showing first {len(files)}."
        except ValueError as error:
            files = []
            total = 0
            truncated = False
            message = str(error)
        return ListFilesObservation(
            kind="list_files",
            path=action.path or ".",
            files=files,
            total=total,
            truncated=truncated,
            message=message,
        )

    if isinstance(action, ListTreeAction):
        try:
            entries, total = list_project_tree(
                workspace,
                action.path,
                max_depth=action.max_depth,
                max_entries=action.max_entries,
            )
            truncated = len(entries) < total
            entry_word = "entry" if total == 1 else "entries"
            message = f"Found {total} {entry_word}."
            if truncated:
                message += f" Showing first {len(entries)}."
            ok = True
        except ValueError as error:
            entries = []
            total = 0
            truncated = False
            message = str(error)
            ok = False
        return ListTreeObservation(
            kind="list_tree",
            path=action.path or ".",
            entries=entries,
            total=total,
            truncated=truncated,
            max_depth=action.max_depth,
            ok=ok,
            message=message,
        )

    if isinstance(action, RepoMapAction):
        try:
            repo_map = build_repo_map(
                workspace,
                action.path,
                max_depth=action.max_depth,
                max_files=action.max_files,
                max_symbols=action.max_symbols,
            )
            python_files = [
                RepoMapPythonFile(
                    path=str(item["path"]),
                    ok=bool(item["ok"]),
                    imports=list(item["imports"]),
                    symbols=[PythonSymbol(**symbol) for symbol in item["symbols"]],
                    message=str(item["message"]),
                )
                for item in repo_map["python_files"]
            ]
            code_files = [
                CodeOutlineResult(
                    path=str(item["path"]),
                    ok=bool(item["ok"]),
                    language=str(item["language"]) if item.get("language") is not None else None,
                    imports=list(item["imports"]),
                    symbols=[PythonSymbol(**symbol) for symbol in item["symbols"]],
                    message=str(item["message"]),
                )
                for item in repo_map["code_files"]
            ]
            return RepoMapObservation(
                kind="repo_map",
                path=str(repo_map["path"]),
                tree=list(repo_map["tree"]),
                files=list(repo_map["files"]),
                python_files=python_files,
                code_files=code_files,
                total_tree_entries=int(repo_map["total_tree_entries"]),
                total_files=int(repo_map["total_files"]),
                truncated=bool(repo_map["truncated"]),
                ok=True,
                message=str(repo_map["message"]),
            )
        except ValueError as error:
            return RepoMapObservation(
                kind="repo_map",
                path=action.path or ".",
                tree=[],
                files=[],
                python_files=[],
                code_files=[],
                total_tree_entries=0,
                total_files=0,
                truncated=False,
                ok=False,
                message=str(error),
            )

    if isinstance(action, ReadFileAction):
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

    if isinstance(action, ReadFileContextAction):
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

    if isinstance(action, ReadFileContextsAction):
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

    if isinstance(action, OutputContextsAction):
        result = read_output_contexts_result(
            workspace,
            action.text,
            context_lines=action.context_lines,
            max_contexts=action.max_contexts,
            max_bytes_per_context=action.max_bytes_per_context,
        )
        contexts = output_context_results_from_dicts(result["contexts"])
        return OutputContextsObservation(
            kind="output_contexts",
            contexts=contexts,
            total_refs=int(result["total_refs"]),
            truncated=bool(result["truncated"]),
            message=str(result["message"]),
        )

    if isinstance(action, OutputDiagnosticsAction):
        result = read_output_diagnostics_result(
            workspace,
            action.text,
            context_lines=action.context_lines,
            max_diagnostics=action.max_diagnostics,
            max_contexts=action.max_contexts,
            max_bytes_per_context=action.max_bytes_per_context,
        )
        return OutputDiagnosticsObservation(
            kind="output_diagnostics",
            diagnostics=output_diagnostics_from_dicts(result["diagnostics"]),
            contexts=output_context_results_from_dicts(result["contexts"]),
            total_diagnostics=int(result["total_diagnostics"]),
            total_refs=int(result["total_refs"]),
            diagnostics_truncated=bool(result["diagnostics_truncated"]),
            contexts_truncated=bool(result["contexts_truncated"]),
            message=str(result["message"]),
        )

    if isinstance(action, TailFileAction):
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

    if isinstance(action, ReadFilesAction):
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

    if isinstance(action, ReadFileRangesAction):
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

    if isinstance(action, FileInfoAction):
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

    if isinstance(action, ImageInfoAction):
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

    if isinstance(action, PythonSymbolsAction):
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

    if isinstance(action, CodeOutlineAction):
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

    return None
