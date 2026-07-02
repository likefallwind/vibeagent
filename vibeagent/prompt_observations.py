from __future__ import annotations

from .types import Observation


def format_observations(observations: list[Observation]) -> str:
    # Serialize prior observations in compact human-readable lines for next-turn reasoning.
    if not observations:
        return "No observations yet."

    lines: list[str] = []
    for index, observation in enumerate(observations, start=1):
        if observation.kind == "check_write_file":
            lines.append(
                "\n".join(
                    [
                        f"{index}. check_write_file {observation.path}: {observation.message}",
                        f"diff:\n{truncate(observation.diff)}",
                    ]
                )
            )
        elif observation.kind == "write_file":
            lines.append(f"{index}. write_file {observation.path}: {observation.message}")
        elif observation.kind == "check_write_files":
            parts = [f"{index}. check_write_files: {observation.message} ok={str(observation.ok).lower()}"]
            for file in observation.files:
                parts.append(
                    "\n".join(
                        [
                            f"file: {file.path} ok={str(file.ok).lower()} message={file.message}",
                            f"diff:\n{truncate(file.diff)}",
                        ]
                    )
                )
            lines.append("\n".join(parts))
        elif observation.kind == "write_files":
            parts = [f"{index}. write_files: {observation.message} ok={str(observation.ok).lower()}"]
            for file in observation.files:
                parts.append(f"file: {file.path} ok={str(file.ok).lower()} message={file.message}")
            lines.append("\n".join(parts))
        elif observation.kind == "list_files":
            lines.append(
                "\n".join(
                    [
                        f"{index}. list_files {observation.path}: {observation.message}",
                        *observation.files[:120],
                    ]
                )
            )
        elif observation.kind == "list_tree":
            lines.append(
                "\n".join(
                    [
                        (
                            f"{index}. list_tree {observation.path}: {observation.message} "
                            f"maxDepth={observation.max_depth} truncated={str(observation.truncated).lower()}"
                        ),
                        *observation.entries[:160],
                    ]
                )
            )
        elif observation.kind == "repo_map":
            parts = [
                (
                    f"{index}. repo_map {observation.path}: {observation.message} "
                    f"files={len(observation.files)}/{observation.total_files} "
                    f"treeEntries={len(observation.tree)}/{observation.total_tree_entries} "
                    f"truncated={str(observation.truncated).lower()}"
                )
            ]
            if observation.tree:
                parts.append("tree:\n" + "\n".join(observation.tree[:120]))
            if observation.files:
                parts.append("files:\n" + "\n".join(observation.files[:120]))
            for file in observation.python_files[:40]:
                parts.append(f"python: {file.path} ok={str(file.ok).lower()} message={file.message}")
                if file.imports:
                    parts.append("imports:\n" + "\n".join(file.imports[:20]))
                if file.symbols:
                    parts.append(
                        "symbols:\n"
                        + "\n".join(
                            (
                                f"- {symbol.kind} {symbol.name} "
                                f"line={symbol.line} parent={symbol.parent or '.'}"
                            )
                            for symbol in file.symbols[:60]
                        )
                    )
            for file in [item for item in observation.code_files if item.language != "python"][:40]:
                parts.append(
                    (
                        f"source: {file.path} language={file.language or '.'} "
                        f"ok={str(file.ok).lower()} message={file.message}"
                    )
                )
                if file.imports:
                    parts.append("imports:\n" + "\n".join(file.imports[:20]))
                if file.symbols:
                    parts.append(
                        "symbols:\n"
                        + "\n".join(
                            (
                                f"- {symbol.kind} {symbol.name} "
                                f"line={symbol.line} parent={symbol.parent or '.'}"
                            )
                            for symbol in file.symbols[:60]
                        )
                    )
            lines.append("\n".join(parts))
        elif observation.kind == "read_file":
            lines.append(
                "\n".join(
                    [
                        (
                            f"{index}. read_file {observation.path}: {observation.message} "
                            f"truncated={str(observation.truncated).lower()} "
                            f"bytes={observation.total_bytes if observation.total_bytes is not None else 'unknown'} "
                            f"maxBytes={observation.max_bytes}"
                        ),
                        f"content:\n{truncate(observation.content)}",
                    ]
                )
            )
        elif observation.kind == "read_file_context":
            lines.append(
                "\n".join(
                    [
                        (
                            f"{index}. read_file_context {observation.path}:{observation.line}: {observation.message} "
                            f"ok={str(observation.ok).lower()} "
                            f"range={observation.start_line}:{observation.end_line} "
                            f"contextLines={observation.context_lines} "
                            f"targetExists={str(observation.target_line_exists).lower()} "
                            f"lines={observation.line_count}/{observation.total_lines if observation.total_lines is not None else 'unknown'} "
                            f"truncated={str(observation.truncated).lower()} "
                            f"maxBytes={observation.max_bytes}"
                        ),
                        f"content:\n{truncate(observation.content)}",
                    ]
                )
            )
        elif observation.kind == "read_file_contexts":
            parts = [f"{index}. read_file_contexts: {observation.message}"]
            for item in observation.contexts:
                parts.append(
                    (
                        f"context: {item.path}:{item.line} "
                        f"ok={str(item.ok).lower()} range={item.start_line}:{item.end_line} "
                        f"contextLines={item.context_lines} targetExists={str(item.target_line_exists).lower()} "
                        f"lines={item.line_count}/{item.total_lines if item.total_lines is not None else 'unknown'} "
                        f"truncated={str(item.truncated).lower()} maxBytes={item.max_bytes} "
                        f"message={item.message}"
                    )
                )
                if item.ok:
                    parts.append(f"content:\n{truncate(item.content)}")
            lines.append("\n".join(parts))
        elif observation.kind == "output_contexts":
            parts = [
                (
                    f"{index}. output_contexts: {observation.message} "
                    f"totalRefs={observation.total_refs} truncated={str(observation.truncated).lower()}"
                )
            ]
            for item in observation.contexts:
                column = f":{item.column}" if item.column is not None else ""
                parts.append(
                    (
                        f"context: {item.path}:{item.line}{column} raw={item.raw!r} "
                        f"ok={str(item.ok).lower()} range={item.start_line}:{item.end_line} "
                        f"contextLines={item.context_lines} targetExists={str(item.target_line_exists).lower()} "
                        f"lines={item.line_count}/{item.total_lines if item.total_lines is not None else 'unknown'} "
                        f"truncated={str(item.truncated).lower()} maxBytes={item.max_bytes} "
                        f"message={item.message}"
                    )
                )
                if item.ok:
                    parts.append(f"content:\n{truncate(item.content)}")
            lines.append("\n".join(parts))
        elif observation.kind == "output_diagnostics":
            parts = [
                (
                    f"{index}. output_diagnostics: {observation.message} "
                    f"diagnostics={len(observation.diagnostics)}/{observation.total_diagnostics} "
                    f"refs={observation.total_refs} "
                    f"diagnosticsTruncated={str(observation.diagnostics_truncated).lower()} "
                    f"contextsTruncated={str(observation.contexts_truncated).lower()}"
                )
            ]
            for diagnostic in observation.diagnostics:
                location = (
                    f" {diagnostic.path}:{diagnostic.line}{':' + str(diagnostic.column) if diagnostic.column is not None else ''}"
                    if diagnostic.path and diagnostic.line is not None
                    else ""
                )
                parts.append(
                    f"diagnostic: {diagnostic.severity} outputLine={diagnostic.output_line}{location} text={diagnostic.text!r}"
                )
            for item in observation.contexts:
                column = f":{item.column}" if item.column is not None else ""
                parts.append(
                    (
                        f"context: {item.path}:{item.line}{column} raw={item.raw!r} "
                        f"ok={str(item.ok).lower()} range={item.start_line}:{item.end_line} "
                        f"contextLines={item.context_lines} targetExists={str(item.target_line_exists).lower()} "
                        f"lines={item.line_count}/{item.total_lines if item.total_lines is not None else 'unknown'} "
                        f"truncated={str(item.truncated).lower()} maxBytes={item.max_bytes} "
                        f"message={item.message}"
                    )
                )
                if item.ok:
                    parts.append(f"content:\n{truncate(item.content)}")
            lines.append("\n".join(parts))
        elif observation.kind == "tail_file":
            lines.append(
                "\n".join(
                    [
                        (
                            f"{index}. tail_file {observation.path}: {observation.message} "
                            f"ok={str(observation.ok).lower()} "
                            f"lines={observation.line_count}/{observation.total_lines if observation.total_lines is not None else 'unknown'} "
                            f"startLine={observation.start_line} "
                            f"requestedLines={observation.requested_line_count} "
                            f"truncated={str(observation.truncated).lower()} "
                            f"maxBytes={observation.max_bytes}"
                        ),
                        f"content:\n{truncate(observation.content)}",
                    ]
                )
            )
        elif observation.kind == "read_files":
            parts = [f"{index}. read_files: {observation.message}"]
            for file in observation.files:
                byte_count = file.total_bytes if file.total_bytes is not None else "unknown"
                parts.append(
                    (
                        f"file: {file.path} ok={str(file.ok).lower()} "
                        f"truncated={str(file.truncated).lower()} bytes={byte_count} "
                        f"maxBytes={file.max_bytes} message={file.message}"
                    )
                )
                if file.ok:
                    parts.append(f"content:\n{truncate(file.content)}")
            lines.append("\n".join(parts))
        elif observation.kind == "read_file_ranges":
            parts = [f"{index}. read_file_ranges: {observation.message}"]
            for item in observation.ranges:
                parts.append(
                    (
                        f"range: {item.path}:{item.start_line}+{item.line_count} "
                        f"ok={str(item.ok).lower()} message={item.message}"
                    )
                )
                if item.ok:
                    parts.append(f"content:\n{truncate(item.content)}")
            lines.append("\n".join(parts))
        elif observation.kind == "file_info":
            parts = [f"{index}. file_info: {observation.message}"]
            for file in observation.files:
                size = "unknown" if file.size_bytes is None else str(file.size_bytes)
                line_count = "unknown" if file.line_count is None else str(file.line_count)
                binary = "unknown" if file.is_binary is None else str(file.is_binary).lower()
                parts.append(
                    (
                        f"file: {file.path} ok={str(file.ok).lower()} exists={str(file.exists).lower()} "
                        f"isFile={str(file.is_file).lower()} isDir={str(file.is_dir).lower()} "
                        f"sizeBytes={size} lineCount={line_count} binary={binary} message={file.message}"
                    )
                )
            lines.append("\n".join(parts))
        elif observation.kind == "image_info":
            parts = [f"{index}. image_info: {observation.message}"]
            for image in observation.images:
                size = "unknown" if image.size_bytes is None else str(image.size_bytes)
                width = "unknown" if image.width is None else str(image.width)
                height = "unknown" if image.height is None else str(image.height)
                image_format = "unknown" if image.format is None else image.format
                mime_type = "unknown" if image.mime_type is None else image.mime_type
                parts.append(
                    (
                        f"image: {image.path} ok={str(image.ok).lower()} exists={str(image.exists).lower()} "
                        f"isFile={str(image.is_file).lower()} sizeBytes={size} format={image_format} "
                        f"mimeType={mime_type} width={width} height={height} message={image.message}"
                    )
                )
            lines.append("\n".join(parts))
        elif observation.kind == "python_symbols":
            parts = [f"{index}. python_symbols: {observation.message}"]
            for file in observation.files:
                parts.append(f"file: {file.path} ok={str(file.ok).lower()} message={file.message}")
                if file.imports:
                    parts.append("imports:\n" + "\n".join(file.imports[:40]))
                if file.symbols:
                    parts.append(
                        "symbols:\n"
                        + "\n".join(
                            (
                                f"- {symbol.kind} {symbol.name} "
                                f"line={symbol.line} endLine={symbol.end_line or 'unknown'} "
                                f"parent={symbol.parent or '.'}"
                            )
                            for symbol in file.symbols[:120]
                        )
                    )
            lines.append("\n".join(parts))
        elif observation.kind == "code_outline":
            parts = [f"{index}. code_outline: {observation.message}"]
            for file in observation.files:
                parts.append(
                    (
                        f"file: {file.path} language={file.language or '.'} "
                        f"ok={str(file.ok).lower()} message={file.message}"
                    )
                )
                if file.imports:
                    parts.append("imports:\n" + "\n".join(file.imports[:40]))
                if file.symbols:
                    parts.append(
                        "symbols:\n"
                        + "\n".join(
                            (
                                f"- {symbol.kind} {symbol.name} "
                                f"line={symbol.line} parent={symbol.parent or '.'}"
                            )
                            for symbol in file.symbols[:120]
                        )
                    )
            lines.append("\n".join(parts))
        elif observation.kind == "python_check":
            parts = [
                (
                    f"{index}. python_check {observation.path or '.'}: {observation.message} "
                    f"checked={len(observation.files)}/{observation.total} "
                    f"truncated={str(observation.truncated).lower()}"
                )
            ]
            for file in observation.files[:120]:
                location = ""
                if file.line is not None:
                    location = f" line={file.line} column={file.column or 'unknown'}"
                parts.append(f"file: {file.path} ok={str(file.ok).lower()}{location} message={file.message}")
            lines.append("\n".join(parts))
        elif observation.kind == "config_check":
            parts = [
                (
                    f"{index}. config_check {observation.path or '.'}: {observation.message} "
                    f"checked={len(observation.files)}/{observation.total} "
                    f"truncated={str(observation.truncated).lower()}"
                )
            ]
            for file in observation.files[:120]:
                location = ""
                if file.line is not None:
                    location = f" line={file.line} column={file.column or 'unknown'}"
                parts.append(
                    (
                        f"file: {file.path} format={file.format} ok={str(file.ok).lower()}"
                        f"{location} message={file.message}"
                    )
                )
            lines.append("\n".join(parts))
        elif observation.kind == "python_dependencies":
            parts = [
                (
                    f"{index}. python_dependencies {observation.path or '.'}: {observation.message} "
                    f"files={len(observation.files)}/{observation.total} "
                    f"truncated={str(observation.truncated).lower()}"
                )
            ]
            for file in observation.files[:80]:
                parts.append(
                    (
                        f"file: {file.path} module={file.module or '.'} ok={str(file.ok).lower()} "
                        f"local={','.join(file.local_modules[:20]) or '-'} "
                        f"external={','.join(file.external_modules[:20]) or '-'} "
                        f"message={file.message}"
                    )
                )
                for import_ref in file.imports[:80]:
                    parts.append(
                        (
                            f"import: line={import_ref.line} kind={import_ref.kind} "
                            f"module={import_ref.module or '.'} name={import_ref.name or '-'} "
                            f"target={import_ref.target or '.'} local={str(import_ref.local).lower()}"
                        )
                    )
            lines.append("\n".join(parts))
        elif observation.kind == "code_dependencies":
            parts = [
                (
                    f"{index}. code_dependencies {observation.path or '.'}: {observation.message} "
                    f"files={len(observation.files)}/{observation.total} "
                    f"truncated={str(observation.truncated).lower()}"
                )
            ]
            for file in observation.files[:80]:
                parts.append(
                    (
                        f"file: {file.path} language={file.language} ok={str(file.ok).lower()} "
                        f"dependencies={','.join(file.dependencies[:40]) or '-'} "
                        f"message={file.message}"
                    )
                )
                for import_ref in file.imports[:80]:
                    parts.append(
                        (
                            f"import: line={import_ref.line} kind={import_ref.kind} "
                            f"source={import_ref.source or '.'} raw={import_ref.raw}"
                        )
                    )
            lines.append("\n".join(parts))
        elif observation.kind == "code_references":
            parts = [
                (
                    f"{index}. code_references {observation.symbol}: {observation.message} "
                    f"shown={len(observation.references)}/{observation.total} "
                    f"path={observation.path or '.'} "
                    f"truncated={str(observation.truncated).lower()}"
                )
            ]
            for reference in observation.references[:160]:
                parts.append(
                    (
                        f"reference: {reference.path}:{reference.line}:{reference.column} "
                        f"language={reference.language} context={reference.context}"
                    )
                )
            lines.append("\n".join(parts))
        elif observation.kind == "code_reference_contexts":
            parts = [
                (
                    f"{index}. code_reference_contexts {observation.symbol}: {observation.message} "
                    f"shown={len(observation.contexts)}/{observation.total} "
                    f"path={observation.path or '.'} "
                    f"context_lines={observation.context_lines} "
                    f"truncated={str(observation.truncated).lower()}"
                )
            ]
            for context in observation.contexts[:80]:
                parts.append(
                    (
                        f"reference: {context.path}:{context.line}:{context.column} "
                        f"language={context.language or 'unknown'} kind={context.kind} "
                        f"range={context.start_line}-{context.end_line} "
                        f"truncated={str(context.truncated).lower()} "
                        f"match={context.matched_line}"
                    )
                )
                parts.append("content:\n" + truncate(context.content))
            lines.append("\n".join(parts))
        elif observation.kind == "code_definitions":
            parts = [
                (
                    f"{index}. code_definitions {observation.symbol}: {observation.message} "
                    f"path={observation.path or '.'} truncated={str(observation.truncated).lower()}"
                )
            ]
            for definition in observation.definitions[:80]:
                parts.append(
                    (
                        f"definition: {definition.path}:{definition.line}-{definition.end_line} "
                        f"language={definition.language} {definition.kind} {definition.name} "
                        f"truncated={str(definition.truncated).lower()}"
                    )
                )
                parts.append("content:\n" + truncate(definition.content))
            if observation.errors:
                parts.append("errors:\n" + "\n".join(observation.errors[:20]))
            lines.append("\n".join(parts))
        elif observation.kind == "code_rename_preview":
            parts = [
                (
                    f"{index}. code_rename_preview {observation.symbol}->{observation.new_name}: "
                    f"{observation.message} path={observation.path or '.'} "
                    f"files={len(observation.files)}/{observation.total_files} "
                    f"replacements={observation.total_replacements} "
                    f"truncated={str(observation.truncated).lower()}"
                )
            ]
            for file in observation.files[:40]:
                parts.append(
                    (
                        f"file: {file.path} language={file.language} replacements={len(file.replacements)} "
                        f"truncated={str(file.truncated).lower()}"
                    )
                )
                for replacement in file.replacements[:80]:
                    parts.append(
                        (
                            f"replace: {replacement.line}:{replacement.column}-{replacement.end_column} "
                            f"{replacement.old}->{replacement.new} context={replacement.context}"
                        )
                    )
                parts.append("diff:\n" + truncate(file.diff))
            if observation.errors:
                parts.append("errors:\n" + "\n".join(observation.errors[:20]))
            lines.append("\n".join(parts))
        elif observation.kind == "code_rename":
            parts = [
                (
                    f"{index}. code_rename {observation.symbol}->{observation.new_name}: "
                    f"{observation.message} path={observation.path or '.'} "
                    f"files={len(observation.files)}/{observation.total_files} "
                    f"replacements={observation.total_replacements}"
                )
            ]
            if observation.diff:
                parts.append("diff:\n" + truncate(observation.diff))
            if observation.errors:
                parts.append("errors:\n" + "\n".join(observation.errors[:20]))
            lines.append("\n".join(parts))
        elif observation.kind == "python_definitions":
            parts = [
                (
                    f"{index}. python_definitions {observation.symbol}: {observation.message} "
                    f"path={observation.path or '.'} truncated={str(observation.truncated).lower()}"
                )
            ]
            for definition in observation.definitions[:80]:
                parts.append(
                    (
                        f"definition: {definition.path}:{definition.line}-{definition.end_line} "
                        f"{definition.kind} {definition.qualified_name} "
                        f"truncated={str(definition.truncated).lower()}"
                    )
                )
                parts.append("content:\n" + truncate(definition.content))
            if observation.errors:
                parts.append("errors:\n" + "\n".join(observation.errors[:20]))
            lines.append("\n".join(parts))
        elif observation.kind == "python_calls":
            parts = [
                (
                    f"{index}. python_calls {observation.symbol}: {observation.message} "
                    f"path={observation.path or '.'} truncated={str(observation.truncated).lower()}"
                )
            ]
            for call in observation.calls[:120]:
                parts.append(
                    (
                        f"{call.path}:{call.line}:{call.column}: "
                        f"caller={call.caller or '.'} callee={call.callee} {call.context}"
                    )
                )
            if observation.errors:
                parts.append("errors:\n" + "\n".join(observation.errors[:20]))
            lines.append("\n".join(parts))
        elif observation.kind == "python_call_graph":
            parts = [
                (
                    f"{index}. python_call_graph {observation.path or '.'}: {observation.message} "
                    f"truncated={str(observation.truncated).lower()}"
                )
            ]
            for edge in observation.edges[:160]:
                parts.append(
                    (
                        f"{edge.path}:{edge.line}:{edge.column}: "
                        f"caller={edge.caller or '.'} callee={edge.callee} {edge.context}"
                    )
                )
            if observation.errors:
                parts.append("errors:\n" + "\n".join(observation.errors[:20]))
            lines.append("\n".join(parts))
        elif observation.kind == "python_references":
            parts = [
                (
                    f"{index}. python_references {observation.symbol}: {observation.message} "
                    f"path={observation.path or '.'} truncated={str(observation.truncated).lower()}"
                )
            ]
            for reference in observation.references[:160]:
                parts.append(
                    (
                        f"{reference.path}:{reference.line}:{reference.column}: "
                        f"{reference.kind} {reference.context}"
                    )
                )
            if observation.errors:
                parts.append("errors:\n" + "\n".join(observation.errors[:20]))
            lines.append("\n".join(parts))
        elif observation.kind == "python_reference_contexts":
            parts = [
                (
                    f"{index}. python_reference_contexts {observation.symbol}: {observation.message} "
                    f"shown={len(observation.contexts)}/{observation.total} "
                    f"path={observation.path or '.'} "
                    f"context_lines={observation.context_lines} "
                    f"truncated={str(observation.truncated).lower()}"
                )
            ]
            for context in observation.contexts[:80]:
                parts.append(
                    (
                        f"reference: {context.path}:{context.line}:{context.column} "
                        f"kind={context.kind} range={context.start_line}-{context.end_line} "
                        f"truncated={str(context.truncated).lower()} "
                        f"match={context.matched_line}"
                    )
                )
                parts.append("content:\n" + truncate(context.content))
            if observation.errors:
                parts.append("errors:\n" + "\n".join(observation.errors[:20]))
            lines.append("\n".join(parts))
        elif observation.kind == "python_rename_preview":
            parts = [
                (
                    f"{index}. python_rename_preview {observation.symbol}->{observation.new_name}: "
                    f"{observation.message} path={observation.path or '.'} "
                    f"files={len(observation.files)}/{observation.total_files} "
                    f"replacements={observation.total_replacements} "
                    f"truncated={str(observation.truncated).lower()}"
                )
            ]
            for file in observation.files[:40]:
                parts.append(
                    (
                        f"file: {file.path} replacements={len(file.replacements)} "
                        f"truncated={str(file.truncated).lower()}"
                    )
                )
                for replacement in file.replacements[:80]:
                    parts.append(
                        (
                            f"replace: {replacement.path}:{replacement.line}:{replacement.column}-"
                            f"{replacement.end_column} kind={replacement.kind} "
                            f"{replacement.old}->{replacement.new} {replacement.context}"
                        )
                    )
                parts.append(f"diff:\n{truncate(file.diff)}")
            if observation.errors:
                parts.append("errors:\n" + "\n".join(observation.errors[:20]))
            lines.append("\n".join(parts))
        elif observation.kind == "python_rename":
            parts = [
                (
                    f"{index}. python_rename {observation.symbol}->{observation.new_name}: "
                    f"{observation.message} path={observation.path or '.'} "
                    f"files={len(observation.files)}/{observation.total_files} "
                    f"replacements={observation.total_replacements}"
                )
            ]
            for file in observation.files[:40]:
                parts.append(f"file: {file.path} replacements={len(file.replacements)}")
            if observation.diff:
                parts.append(f"diff:\n{truncate(observation.diff)}")
            if observation.errors:
                parts.append("errors:\n" + "\n".join(observation.errors[:20]))
            lines.append("\n".join(parts))
        elif observation.kind == "search":
            lines.append(
                "\n".join(
                    [
                        (
                            f"{index}. search {observation.query}: {observation.message} "
                            f"ok={str(observation.ok).lower()} "
                            f"shown={len(observation.matches)}/{observation.total} "
                            f"truncated={str(observation.truncated).lower()} "
                            f"path={observation.path or '.'} regex={str(observation.regex).lower()} "
                            f"caseSensitive={str(observation.case_sensitive).lower()} "
                            f"contextLines={observation.context_lines}"
                        ),
                        *observation.matches[:80],
                    ]
                )
            )
        elif observation.kind == "search_contexts":
            parts = [
                (
                    f"{index}. search_contexts {observation.query}: {observation.message} "
                    f"ok={str(observation.ok).lower()} "
                    f"shown={len(observation.contexts)}/{observation.total} "
                    f"truncated={str(observation.truncated).lower()} "
                    f"path={observation.path or '.'} regex={str(observation.regex).lower()} "
                    f"caseSensitive={str(observation.case_sensitive).lower()} "
                    f"contextLines={observation.context_lines}"
                )
            ]
            for context in observation.contexts[:50]:
                parts.extend(
                    [
                        f"context: {context.path}:{context.line} range={context.start_line}-{context.end_line} truncated={str(context.truncated).lower()}",
                        context.content,
                    ]
                )
            lines.append("\n".join(parts))
        elif observation.kind == "glob":
            lines.append(
                "\n".join(
                    [
                        f"{index}. glob {observation.pattern}: {observation.message}",
                        *observation.matches[:120],
                    ]
                )
            )
        elif observation.kind == "git_status":
            lines.append(
                "\n".join(
                    [
                        f"{index}. git_status: {observation.message}",
                        f"status:\n{truncate(observation.status)}",
                    ]
                )
            )
        elif observation.kind == "git_conflicts":
            unmerged = "\n".join(f"{item.status} {item.path}" for item in observation.unmerged[:80]) or "none"
            markers = "\n".join(
                f"{item.path}:{item.line} [{item.marker}] {item.text}"
                for item in observation.markers[:120]
            ) or "none"
            lines.append(
                "\n".join(
                    [
                        f"{index}. git_conflicts {observation.path}: {observation.message}",
                        f"ok: {observation.ok}",
                        f"unmerged: {len(observation.unmerged)}/{observation.unmerged_total}",
                        f"markers: {len(observation.markers)}/{observation.markers_total}",
                        f"scannedFiles: {observation.scanned_files}/{observation.total_files}",
                        f"truncated: {observation.truncated}",
                        f"unmergedFiles:\n{truncate(unmerged)}",
                        f"markerLines:\n{truncate(markers)}",
                    ]
                )
            )
        elif observation.kind == "git_info":
            parts = [
                (
                    f"{index}. git_info: {observation.message} "
                    f"branch={observation.branch or 'detached'} head={observation.head or 'unknown'} "
                    f"upstream={observation.upstream or 'none'} ahead={observation.ahead} behind={observation.behind}"
                )
            ]
            for remote in observation.remotes[:20]:
                parts.append(f"remote: {remote.name} {remote.kind} {remote.url}")
            if observation.status.strip():
                parts.append(f"status:\n{truncate(observation.status)}")
            lines.append("\n".join(parts))
        elif observation.kind == "git_changes":
            parts = [f"{index}. git_changes: {observation.message}"]
            for file in observation.files[:120]:
                parts.append(
                    (
                        f"file: {file.path} status={file.status or '..'} "
                        f"staged={str(file.staged).lower()} unstaged={str(file.unstaged).lower()} "
                        f"untracked={str(file.untracked).lower()} "
                        f"stagedLines=+{file.staged_insertions}/-{file.staged_deletions} "
                        f"unstagedLines=+{file.unstaged_insertions}/-{file.unstaged_deletions} "
                        f"binary={str(file.binary).lower()}"
                    )
                )
            if observation.status.strip():
                parts.append(f"status:\n{truncate(observation.status)}")
            lines.append("\n".join(parts))
        elif observation.kind == "git_branches":
            parts = [
                (
                    f"{index}. git_branches: {observation.message} "
                    f"current={observation.current or 'detached'} shown={len(observation.branches)}/{observation.total} "
                    f"truncated={str(observation.truncated).lower()}"
                )
            ]
            for branch in observation.branches[:120]:
                marker = "*" if branch.current else "-"
                parts.append(f"{marker} {branch.name}")
            if observation.status.strip():
                parts.append(f"status:\n{truncate(observation.status)}")
            lines.append("\n".join(parts))
        elif observation.kind == "check_git_fetch":
            lines.append(
                "\n".join(
                    [
                        f"{index}. check_git_fetch {observation.remote or 'default remote'}: {observation.message}",
                        f"ok: {str(observation.ok).lower()}",
                        f"remoteUrl: {observation.remote_url or 'none'}",
                        f"branch: {observation.branch or 'detached'}",
                        f"upstream: {observation.upstream or 'none'}",
                        f"aheadBehind: {observation.ahead}/{observation.behind}",
                    ]
                )
            )
        elif observation.kind == "git_fetch":
            lines.append(
                "\n".join(
                    [
                        f"{index}. git_fetch {observation.remote or 'default remote'}: {observation.message}",
                        f"ok: {str(observation.ok).lower()}",
                        f"remoteUrl: {observation.remote_url or 'none'}",
                        f"branch: {observation.branch or 'detached'}",
                        f"upstream: {observation.upstream or 'none'}",
                        (
                            "aheadBehind: "
                            f"{observation.ahead_before}/{observation.behind_before}"
                            f" -> {observation.ahead_after}/{observation.behind_after}"
                        ),
                    ]
                )
            )
        elif observation.kind == "check_git_pull":
            lines.append(
                "\n".join(
                    [
                        f"{index}. check_git_pull {observation.upstream or 'no upstream'}: {observation.message}",
                        f"ok: {str(observation.ok).lower()}",
                        f"remoteBranch: {observation.remote or 'none'}/{observation.branch or 'none'}",
                        f"current: {observation.current or 'detached'}",
                        f"aheadBehind: {observation.ahead}/{observation.behind}",
                        f"worktreeClean: {str(observation.worktree_clean).lower()}",
                        f"status:\n{truncate(observation.status)}",
                    ]
                )
            )
        elif observation.kind == "git_pull":
            lines.append(
                "\n".join(
                    [
                        f"{index}. git_pull {observation.upstream or 'no upstream'}: {observation.message}",
                        f"ok: {str(observation.ok).lower()}",
                        f"remoteBranch: {observation.remote or 'none'}/{observation.branch or 'none'}",
                        f"current: {observation.current_before or 'detached'} -> {observation.current_after or 'detached'}",
                        (
                            "aheadBehind: "
                            f"{observation.ahead_before}/{observation.behind_before}"
                            f" -> {observation.ahead_after}/{observation.behind_after}"
                        ),
                        f"status:\n{truncate(observation.status)}",
                    ]
                )
            )
        elif observation.kind == "check_git_push":
            lines.append(
                "\n".join(
                    [
                        f"{index}. check_git_push {observation.upstream or 'no upstream'}: {observation.message}",
                        f"ok: {str(observation.ok).lower()}",
                        f"remoteBranch: {observation.remote or 'none'}/{observation.branch or 'none'}",
                        f"current: {observation.current or 'detached'}",
                        f"aheadBehind: {observation.ahead}/{observation.behind}",
                        f"worktreeClean: {str(observation.worktree_clean).lower()}",
                        f"status:\n{truncate(observation.status)}",
                    ]
                )
            )
        elif observation.kind == "git_push":
            lines.append(
                "\n".join(
                    [
                        f"{index}. git_push {observation.upstream or 'no upstream'}: {observation.message}",
                        f"ok: {str(observation.ok).lower()}",
                        f"remoteBranch: {observation.remote or 'none'}/{observation.branch or 'none'}",
                        f"current: {observation.current or 'detached'}",
                        f"aheadBehindBefore: {observation.ahead_before}/{observation.behind_before}",
                        f"status:\n{truncate(observation.status)}",
                    ]
                )
            )
        elif observation.kind in {"check_git_restore", "git_restore"}:
            lines.append(
                "\n".join(
                    [
                        f"{index}. {observation.kind}: {observation.message}",
                        f"ok: {str(observation.ok).lower()}",
                        f"paths: {', '.join(observation.paths)}",
                        f"diff:\n{truncate(observation.diff)}",
                        f"status:\n{truncate(observation.status)}",
                    ]
                )
            )
        elif observation.kind == "git_stashes":
            parts = [
                (
                    f"{index}. git_stashes: {observation.message} "
                    f"shown={len(observation.entries)}/{observation.total} "
                    f"truncated={str(observation.truncated).lower()}"
                )
            ]
            for entry in observation.entries[:50]:
                parts.append(f"stash: {entry.name} {entry.summary}")
            lines.append("\n".join(parts))
        elif observation.kind in {"check_git_stash", "git_stash"}:
            stash_ref = f"\nstashRef: {observation.stash_ref}" if observation.kind == "git_stash" else ""
            lines.append(
                "\n".join(
                    [
                        f"{index}. {observation.kind}: {observation.message}",
                        f"ok: {str(observation.ok).lower()}",
                        f"messageText: {observation.message_text}",
                        f"includeUntracked: {str(observation.include_untracked).lower()}{stash_ref}",
                        f"diff:\n{truncate(observation.diff)}",
                        f"status:\n{truncate(observation.status)}",
                    ]
                )
            )
        elif observation.kind in {"check_git_stash_apply", "git_stash_apply"}:
            worktree = (
                f"\nworktreeClean: {str(observation.worktree_clean).lower()}"
                if observation.kind == "check_git_stash_apply"
                else ""
            )
            lines.append(
                "\n".join(
                    [
                        f"{index}. {observation.kind} {observation.stash_ref}: {observation.message}",
                        f"ok: {str(observation.ok).lower()}{worktree}",
                        f"patch:\n{truncate(observation.patch)}",
                        f"status:\n{truncate(observation.status)}",
                    ]
                )
            )
        elif observation.kind in {"check_git_stash_drop", "git_stash_drop"}:
            remaining = (
                f"\nremainingTotal: {observation.remaining_total}"
                if observation.kind == "git_stash_drop"
                else ""
            )
            lines.append(
                "\n".join(
                    [
                        f"{index}. {observation.kind} {observation.stash_ref}: {observation.message}",
                        f"ok: {str(observation.ok).lower()}{remaining}",
                        f"summary: {observation.summary}",
                        f"patch:\n{truncate(observation.patch)}",
                    ]
                )
            )
        elif observation.kind == "check_git_switch":
            lines.append(
                "\n".join(
                    [
                        f"{index}. check_git_switch {observation.branch}: {observation.message}",
                        f"ok: {str(observation.ok).lower()}",
                        f"create: {str(observation.create).lower()}",
                        f"currentBefore: {observation.current_before or 'detached'}",
                        f"branchExists: {str(observation.branch_exists).lower()}",
                        f"worktreeClean: {str(observation.worktree_clean).lower()}",
                        f"status:\n{truncate(observation.status)}",
                    ]
                )
            )
        elif observation.kind == "git_switch":
            lines.append(
                "\n".join(
                    [
                        f"{index}. git_switch {observation.branch}: {observation.message}",
                        f"ok: {str(observation.ok).lower()}",
                        f"create: {str(observation.create).lower()}",
                        f"currentBefore: {observation.current_before or 'detached'}",
                        f"currentAfter: {observation.current_after or 'detached'}",
                        f"status:\n{truncate(observation.status)}",
                    ]
                )
            )
        elif observation.kind in {"check_git_stage", "git_stage", "check_git_unstage", "git_unstage"}:
            parts = [
                (
                    f"{index}. {observation.kind}: {observation.message} "
                    f"ok={str(observation.ok).lower()} paths={', '.join(observation.paths)}"
                )
            ]
            if observation.status.strip():
                parts.append(f"status:\n{truncate(observation.status)}")
            lines.append("\n".join(parts))
        elif observation.kind in {"check_git_commit", "git_commit"}:
            parts = [
                (
                    f"{index}. {observation.kind}: {observation.message} ok={str(observation.ok).lower()} "
                    f"head={observation.head_before or 'none'}->{observation.head_after or 'none'}"
                )
            ]
            if observation.status.strip():
                parts.append(f"status:\n{truncate(observation.status)}")
            lines.append("\n".join(parts))
        elif observation.kind == "review_changes":
            parts = [
                (
                    f"{index}. review_changes: {observation.message} "
                    f"ok={str(observation.ok).lower()} "
                    f"diffCheck={str(observation.diff_check_ok).lower()} "
                    f"stagedDiffCheck={str(observation.staged_diff_check_ok).lower()} "
                    f"pythonOk={str(observation.python_ok).lower()} "
                    f"configOk={str(observation.config_ok).lower()} "
                    f"changed={len(observation.files)}/{observation.total_files} "
                    f"python={len(observation.python)}/{observation.python_total} "
                    f"pythonTruncated={str(observation.python_truncated).lower()} "
                    f"config={len(observation.config)}/{observation.config_total} "
                    f"configTruncated={str(observation.config_truncated).lower()} "
                    f"suggestedChecks={len(observation.suggested_checks)}/{observation.suggested_checks_total} "
                    f"suggestedChecksTruncated={str(observation.suggested_checks_truncated).lower()} "
                    f"diffHunks={len(observation.diff_hunks)}/{observation.diff_hunks_total} "
                    f"diffHunksTruncated={str(observation.diff_hunks_truncated).lower()} "
                    f"stagedDiffHunks={len(observation.staged_diff_hunks)}/{observation.staged_diff_hunks_total} "
                    f"stagedDiffHunksTruncated={str(observation.staged_diff_hunks_truncated).lower()} "
                    f"untrackedPreviews={len(observation.untracked_previews)}/{observation.untracked_previews_total} "
                    f"untrackedPreviewsTruncated={str(observation.untracked_previews_truncated).lower()}"
                )
            ]
            for file in observation.files[:120]:
                parts.append(
                    (
                        f"file: {file.path} status={file.status or '..'} "
                        f"staged={str(file.staged).lower()} unstaged={str(file.unstaged).lower()} "
                        f"untracked={str(file.untracked).lower()}"
                    )
                )
            for file in observation.python[:120]:
                location = ""
                if file.line is not None:
                    location = f" line={file.line} column={file.column or 'unknown'}"
                parts.append(f"python: {file.path} ok={str(file.ok).lower()}{location} message={file.message}")
            for file in observation.config[:120]:
                location = ""
                if file.line is not None:
                    location = f" line={file.line} column={file.column or 'unknown'}"
                parts.append(
                    (
                        f"config: {file.path} format={file.format} ok={str(file.ok).lower()}"
                        f"{location} message={file.message}"
                    )
                )
            for check in observation.suggested_checks[:40]:
                parts.append(
                    (
                        f"check: cwd={check.cwd} command={check.command} "
                        f"available={str(check.available).lower()} missingTool={check.missing_tool or '.'} "
                        f"source={check.source} reason={check.reason}"
                    )
                )
            for hunk in observation.diff_hunks[:40]:
                parts.append(
                    (
                        f"diff_hunk: {hunk.file} old={hunk.old_start},{hunk.old_count} "
                        f"new={hunk.new_start},{hunk.new_count} added={hunk.added} "
                        f"deleted={hunk.deleted} linesTruncated={str(hunk.lines_truncated).lower()}"
                    )
                )
            for hunk in observation.staged_diff_hunks[:40]:
                parts.append(
                    (
                        f"staged_diff_hunk: {hunk.file} old={hunk.old_start},{hunk.old_count} "
                        f"new={hunk.new_start},{hunk.new_count} added={hunk.added} "
                        f"deleted={hunk.deleted} linesTruncated={str(hunk.lines_truncated).lower()}"
                    )
                )
            for preview in observation.untracked_previews[:40]:
                parts.append(
                    (
                        f"untracked_preview: {preview.path} size={preview.size_bytes} "
                        f"binary={str(preview.is_binary).lower()} "
                        f"truncated={str(preview.truncated).lower()} message={preview.message}"
                    )
                )
                if preview.content:
                    parts.append(f"untracked_content {preview.path}:\n{truncate(preview.content, 4000)}")
            if observation.diff_check.strip():
                parts.append(f"diff_check:\n{truncate(observation.diff_check)}")
            if observation.staged_diff_check.strip():
                parts.append(f"staged_diff_check:\n{truncate(observation.staged_diff_check)}")
            if observation.status.strip():
                parts.append(f"status:\n{truncate(observation.status)}")
            lines.append("\n".join(parts))
        elif observation.kind == "final_review":
            parts = [
                (
                    f"{index}. final_review: {observation.message} "
                    f"ok={str(observation.ok).lower()} "
                    f"ready={str(observation.ready).lower()} "
                    f"blocking={len(observation.blocking_issues)} "
                    f"warnings={len(observation.warnings)} "
                    f"runningProcesses={len(observation.running_processes)} "
                    f"changed={len(observation.files)}/{observation.total_files} "
                    f"suggestedChecks={len(observation.suggested_checks)}/{observation.suggested_checks_total} "
                    f"suggestedChecksTruncated={str(observation.suggested_checks_truncated).lower()}"
                )
            ]
            for issue in observation.blocking_issues[:20]:
                parts.append(f"blocking_issue: {issue}")
            for warning in observation.warnings[:20]:
                parts.append(f"warning: {warning}")
            for check in observation.python[:20]:
                if not check.ok:
                    parts.append(
                        (
                            f"python_failure: {check.path} line={check.line or '.'} "
                            f"column={check.column or '.'} message={check.message}"
                        )
                    )
            for check in observation.config[:20]:
                if not check.ok:
                    parts.append(
                        (
                            f"config_failure: {check.path} line={check.line or '.'} "
                            f"column={check.column or '.'} message={check.message}"
                        )
                    )
            for process in observation.running_processes[:20]:
                parts.append(
                    (
                        f"running_process: {process.process_id} pid={process.pid} cwd={process.cwd} "
                        f"command={process.command}"
                    )
                )
            for file in observation.files[:120]:
                parts.append(
                    (
                        f"file: {file.path} status={file.status or '..'} "
                        f"staged={str(file.staged).lower()} unstaged={str(file.unstaged).lower()} "
                        f"untracked={str(file.untracked).lower()}"
                    )
                )
            for check in observation.suggested_checks[:40]:
                parts.append(
                    (
                        f"check: cwd={check.cwd} command={check.command} "
                        f"available={str(check.available).lower()} missingTool={check.missing_tool or '.'} "
                        f"source={check.source} reason={check.reason}"
                    )
                )
            if observation.diff_check.strip():
                parts.append(f"diff_check:\n{truncate(observation.diff_check)}")
            if observation.staged_diff_check.strip():
                parts.append(f"staged_diff_check:\n{truncate(observation.staged_diff_check)}")
            if observation.status.strip():
                parts.append(f"status:\n{truncate(observation.status)}")
            lines.append("\n".join(parts))
        elif observation.kind == "suggest_checks":
            parts = [
                (
                    f"{index}. suggest_checks: {observation.message} "
                    f"shown={len(observation.checks)}/{observation.total} "
                    f"truncated={str(observation.truncated).lower()}"
                )
            ]
            for check in observation.checks:
                parts.append(
                    (
                        f"check: cwd={check.cwd} command={check.command} "
                        f"available={str(check.available).lower()} missingTool={check.missing_tool or '.'} "
                        f"source={check.source} reason={check.reason}"
                    )
                )
            if observation.changed_files:
                parts.append("changed_files:\n" + "\n".join(observation.changed_files[:120]))
            lines.append("\n".join(parts))
        elif observation.kind == "check_suggested_checks":
            parts = [
                (
                    f"{index}. check_suggested_checks: {observation.message} "
                    f"shown={len(observation.checks)}/{observation.total} "
                    f"truncated={str(observation.truncated).lower()}"
                ),
                f"ok: {str(observation.ok).lower()}",
            ]
            for check in observation.checks:
                parts.extend(
                    [
                        f"command: {check.command}",
                        f"cwd: {check.cwd}",
                        f"ok: {str(check.ok).lower()} cwdOk={str(check.cwd_ok).lower()} blocked={str(check.blocked).lower()} executableAvailable={str(check.executable_available).lower()}",
                        f"blockReason: {check.block_reason or 'none'} missingTool={check.missing_tool or 'none'} message={check.message}",
                    ]
                )
            lines.append("\n".join(parts))
        elif observation.kind == "project_commands":
            parts = [
                (
                    f"{index}. project_commands: {observation.message} "
                    f"shown={len(observation.commands)}/{observation.total} "
                    f"files={observation.scanned_files}/{observation.total_files} "
                    f"truncated={str(observation.truncated).lower()}"
                )
            ]
            for command in observation.commands:
                parts.append(
                    (
                        f"command: cwd={command.cwd} command={command.command} "
                        f"available={str(command.available).lower()} missingTool={command.missing_tool or '.'} "
                        f"source={command.source} file={command.file} detail={command.detail}"
                    )
                )
            lines.append("\n".join(parts))
        elif observation.kind == "related_tests":
            parts = [
                (
                    f"{index}. related_tests: {observation.message} "
                    f"ok={str(observation.ok).lower()} "
                    f"targets={len(observation.target_paths)} "
                    f"shown={len(observation.candidates)}/{observation.total} "
                    f"testFiles={observation.test_files_total} "
                    f"truncated={str(observation.truncated).lower()}"
                )
            ]
            if observation.target_paths:
                parts.append("target_paths:\n" + "\n".join(observation.target_paths[:120]))
            for candidate in observation.candidates:
                parts.append(
                    (
                        f"candidate: source={candidate.source_path} test={candidate.test_path} "
                        f"score={candidate.score} reason={candidate.reason}"
                    )
                )
            lines.append("\n".join(parts))
        elif observation.kind == "focused_test_commands":
            parts = [
                (
                    f"{index}. focused_test_commands: {observation.message} "
                    f"ok={str(observation.ok).lower()} "
                    f"targets={len(observation.target_paths)} "
                    f"shown={len(observation.commands)}/{observation.total} "
                    f"relatedTests={observation.related_tests_total} "
                    f"truncated={str(observation.truncated).lower()}"
                )
            ]
            if observation.target_paths:
                parts.append("target_paths:\n" + "\n".join(observation.target_paths[:120]))
            for command in observation.commands:
                parts.append(
                    (
                        f"command: cwd={command.cwd} command={command.command} "
                        f"test={command.test_path} available={str(command.available).lower()} "
                        f"missingTool={command.missing_tool or '.'} source={command.source} reason={command.reason}"
                    )
                )
            lines.append("\n".join(parts))
        elif observation.kind == "check_focused_test_commands":
            parts = [
                (
                    f"{index}. check_focused_test_commands: {observation.message} "
                    f"ok={str(observation.ok).lower()} "
                    f"targets={len(observation.target_paths)} "
                    f"shown={len(observation.focused_commands)}/{observation.total} "
                    f"relatedTests={observation.related_tests_total} "
                    f"truncated={str(observation.truncated).lower()}"
                )
            ]
            if observation.target_paths:
                parts.append("target_paths:\n" + "\n".join(observation.target_paths[:120]))
            for command, check in zip(observation.focused_commands, observation.checks, strict=False):
                parts.extend(
                    [
                        f"command: {command.command}",
                        f"cwd: {command.cwd}",
                        f"test: {command.test_path}",
                        f"available: {str(command.available).lower()} missingTool={command.missing_tool or 'none'} source={command.source} reason={command.reason}",
                        f"ok: {str(check.ok).lower()} cwdOk={str(check.cwd_ok).lower()} blocked={str(check.blocked).lower()} executableAvailable={str(check.executable_available).lower()}",
                        f"blockReason: {check.block_reason or 'none'} missingTool={check.missing_tool or 'none'} message={check.message}",
                    ]
                )
            lines.append("\n".join(parts))
        elif observation.kind == "project_manifests":
            parts = [
                (
                    f"{index}. project_manifests: {observation.message} "
                    f"files={observation.scanned_files}/{observation.total_files} "
                    f"items={observation.total_items} "
                    f"truncated={str(observation.truncated).lower()}"
                )
            ]
            for manifest in observation.manifests[:40]:
                parts.append(
                    (
                        f"manifest: {manifest.path} kind={manifest.kind} ok={str(manifest.ok).lower()} "
                        f"name={manifest.name or '.'} version={manifest.version or '.'} "
                        f"items={len(manifest.items)}/{manifest.item_count} "
                        f"truncated={str(manifest.truncated).lower()} message={manifest.message}"
                    )
                )
                for item in manifest.items[:120]:
                    parts.append(f"item: group={item.group} name={item.name} value={item.value or '.'}")
            lines.append("\n".join(parts))
        elif observation.kind == "project_instructions":
            parts = [
                (
                    f"{index}. project_instructions: {observation.message} "
                    f"files={observation.scanned_files}/{observation.total_files} "
                    f"omitted={observation.omitted_files} "
                    f"truncated={str(observation.truncated).lower()}"
                ),
                f"ok: {str(observation.ok).lower()}",
            ]
            for source in observation.files:
                parts.append(
                    (
                        f"source: {source.path} scope={source.scope} "
                        f"bytes={source.bytes} chars={source.chars} "
                        f"empty={str(source.empty).lower()} included={str(source.included).lower()} "
                        f"message={source.message}"
                    )
                )
            if observation.text:
                parts.append(f"instructions:\n{truncate(observation.text)}")
            lines.append("\n".join(parts))
        elif observation.kind == "project_todos":
            parts = [
                (
                    f"{index}. project_todos: {observation.message} "
                    f"path={observation.path} "
                    f"shown={len(observation.todos)}/{observation.total} "
                    f"files={observation.scanned_files}/{observation.total_files} "
                    f"truncated={str(observation.truncated).lower()}"
                ),
                f"markers: {', '.join(observation.markers) if observation.markers else '.'}",
            ]
            for todo in observation.todos:
                parts.append(f"todo: {todo.path}:{todo.line} [{todo.marker}] {todo.text}")
            lines.append("\n".join(parts))
        elif observation.kind == "project_overview":
            parts = [
                (
                    f"{index}. project_overview: {observation.message} "
                    f"root={observation.project_root} "
                    f"git={str(observation.is_git_repo).lower()} "
                    f"branch={observation.git_branch or '.'} head={observation.git_head or '.'} "
                    f"upstream={observation.git_upstream or '.'} "
                    f"ahead={observation.git_ahead} behind={observation.git_behind}"
                ),
                (
                    f"repo: files={len(observation.files)}/{observation.total_files} "
                    f"tree={len(observation.tree)}/{observation.total_tree_entries} "
                    f"truncated={str(observation.repo_truncated).lower()}"
                ),
            ]
            if observation.git_status.strip():
                parts.append(f"git_status:\n{truncate(observation.git_status, 2000)}")
            if observation.tree:
                parts.append("tree:\n" + "\n".join(observation.tree[:80]))
            if observation.commands:
                parts.append(
                    (
                        f"commands shown={len(observation.commands)}/{observation.commands_total} "
                        f"truncated={str(observation.commands_truncated).lower()}"
                    )
                )
                for command in observation.commands[:40]:
                    parts.append(
                        (
                            f"command: cwd={command.cwd} command={command.command} "
                            f"available={str(command.available).lower()} missingTool={command.missing_tool or '.'} "
                            f"source={command.source} file={command.file}"
                        )
                    )
            if observation.manifests:
                parts.append(
                    (
                        f"manifests shown={len(observation.manifests)}/{observation.manifest_files_total} "
                        f"truncated={str(observation.manifests_truncated).lower()}"
                    )
                )
                for manifest in observation.manifests[:20]:
                    parts.append(
                        (
                            f"manifest: {manifest.path} kind={manifest.kind} ok={str(manifest.ok).lower()} "
                            f"name={manifest.name or '.'} items={manifest.item_count}"
                        )
                    )
            if observation.suggested_checks:
                parts.append(
                    (
                        f"suggested_checks shown={len(observation.suggested_checks)}/{observation.suggested_checks_total} "
                        f"truncated={str(observation.suggested_checks_truncated).lower()}"
                    )
                )
                for check in observation.suggested_checks[:20]:
                    parts.append(
                        (
                            f"check: cwd={check.cwd} command={check.command} "
                            f"available={str(check.available).lower()} missingTool={check.missing_tool or '.'} "
                            f"reason={check.reason}"
                        )
                    )
            if observation.tools:
                parts.append(
                    "tools: "
                    + ", ".join(
                        f"{tool.name}={'yes' if tool.available else 'no'}"
                        for tool in observation.tools[:20]
                    )
                )
            lines.append("\n".join(parts))
        elif observation.kind in {"command_check", "check_start_command"}:
            lines.append(
                "\n".join(
                    [
                        f"{index}. {observation.kind}: {observation.message}",
                        f"ok: {str(observation.ok).lower()}",
                        f"command: {observation.command}",
                        f"cwd: {observation.cwd}",
                        f"cwdOk: {str(observation.cwd_ok).lower()}",
                        f"blocked: {str(observation.blocked).lower()}",
                        f"blockReason: {observation.block_reason or 'none'}",
                        f"executableAvailable: {str(observation.executable_available).lower()}",
                        f"missingTool: {observation.missing_tool or 'none'}",
                    ]
                )
            )
        elif observation.kind == "check_run_commands":
            parts = [
                f"{index}. check_run_commands: {observation.message}",
                f"ok: {str(observation.ok).lower()}",
            ]
            for check in observation.checks:
                parts.extend(
                    [
                        f"command: {check.command}",
                        f"cwd: {check.cwd}",
                        f"ok: {str(check.ok).lower()} cwdOk={str(check.cwd_ok).lower()} blocked={str(check.blocked).lower()} executableAvailable={str(check.executable_available).lower()}",
                        f"blockReason: {check.block_reason or 'none'} missingTool={check.missing_tool or 'none'} message={check.message}",
                    ]
                )
            lines.append("\n".join(parts))
        elif observation.kind == "port_check":
            lines.append(
                "\n".join(
                    [
                        f"{index}. port_check {observation.host}:{observation.port}: {observation.message}",
                        f"ok: {str(observation.ok).lower()}",
                        f"reachable: {str(observation.reachable).lower()}",
                        f"timeoutMs: {observation.timeout_ms}",
                        f"error: {observation.error or 'none'}",
                    ]
                )
            )
        elif observation.kind == "http_check":
            parts = [
                f"{index}. http_check {observation.url}: {observation.message}",
                f"ok: {str(observation.ok).lower()}",
                f"reachable: {str(observation.reachable).lower()}",
                f"status: {observation.status if observation.status is not None else 'none'}",
                f"reason: {observation.reason or 'none'}",
                f"finalUrl: {observation.final_url or 'none'}",
                f"timeoutMs: {observation.timeout_ms}",
                f"matched: {str(observation.matched).lower()}",
                f"matchedPattern: {observation.matched_pattern or 'none'}",
                f"bodyTruncated: {str(observation.body_truncated).lower()}",
                f"maxBodyChars: {observation.max_body_chars}",
                f"error: {observation.error or 'none'}",
            ]
            if observation.body:
                parts.append(f"body:\n{observation.body}")
            lines.append("\n".join(parts))
        elif observation.kind == "http_fetch":
            parts = [
                f"{index}. http_fetch {observation.url}: {observation.message}",
                f"ok: {str(observation.ok).lower()}",
                f"reachable: {str(observation.reachable).lower()}",
                f"status: {observation.status if observation.status is not None else 'none'}",
                f"reason: {observation.reason or 'none'}",
                f"contentType: {observation.content_type or 'none'}",
                f"finalUrl: {observation.final_url or 'none'}",
                f"timeoutMs: {observation.timeout_ms}",
                f"bodyTruncated: {str(observation.body_truncated).lower()}",
                f"maxBodyChars: {observation.max_body_chars}",
                f"error: {observation.error or 'none'}",
            ]
            if observation.body:
                parts.append(f"body:\n{observation.body}")
            lines.append("\n".join(parts))
        elif observation.kind == "environment_info":
            parts = [
                (
                    f"{index}. environment_info: {observation.message} "
                    f"ok={str(observation.ok).lower()} "
                    f"projectRoot={observation.project_root} "
                    f"python={observation.python_version} "
                    f"platform={observation.platform} "
                    f"gitRepo={str(observation.is_git_repo).lower()}"
                ),
                f"pythonExecutable: {observation.python_executable or 'unknown'}",
            ]
            for tool in observation.tools:
                parts.append(
                    (
                        f"tool: {tool.name} available={str(tool.available).lower()} "
                        f"path={tool.path or '.'} version={tool.version or '.'} message={tool.message}"
                    )
                )
            lines.append("\n".join(parts))
        elif observation.kind == "git_diff":
            lines.append(
                "\n".join(
                    [
                        f"{index}. git_diff {observation.path or '.'}: {observation.message}",
                        f"staged: {str(observation.staged).lower()}",
                        f"maxOutputChars: {observation.max_output_chars}",
                        f"truncated: {str(observation.truncated).lower()}",
                        f"diff:\n{truncate(observation.diff)}",
                    ]
                )
            )
        elif observation.kind == "git_diff_hunks":
            parts = [
                (
                    f"{index}. git_diff_hunks {observation.path or '.'}: {observation.message} "
                    f"shown={len(observation.hunks)}/{observation.total_hunks} "
                    f"staged={str(observation.staged).lower()} "
                    f"truncated={str(observation.truncated).lower()}"
                )
            ]
            for hunk in observation.hunks[:120]:
                parts.append(
                    (
                        f"hunk: {hunk.file} old={hunk.old_start},{hunk.old_count} "
                        f"new={hunk.new_start},{hunk.new_count} "
                        f"added={hunk.added} deleted={hunk.deleted} context={hunk.context} "
                        f"linesTruncated={str(hunk.lines_truncated).lower()}"
                    )
                )
                if hunk.lines:
                    parts.append("lines:\n" + truncate("\n".join(hunk.lines)))
            lines.append("\n".join(parts))
        elif observation.kind == "git_diff_contexts":
            parts = [
                (
                    f"{index}. git_diff_contexts {observation.path or '.'}: {observation.message} "
                    f"shown={len(observation.contexts)}/{observation.total_hunks} "
                    f"staged={str(observation.staged).lower()} "
                    f"contextLines={observation.context_lines} "
                    f"truncated={str(observation.truncated).lower()}"
                )
            ]
            for item in observation.contexts[:80]:
                hunk = item.hunk
                context = item.context
                parts.append(
                    (
                        f"hunkContext: {hunk.file} old={hunk.old_start},{hunk.old_count} "
                        f"new={hunk.new_start},{hunk.new_count} added={hunk.added} deleted={hunk.deleted} "
                        f"contextOk={str(context.ok).lower()} targetExists={str(context.target_line_exists).lower()} "
                        f"sourceRange={context.start_line}-{context.end_line}"
                    )
                )
                if context.ok and context.content:
                    parts.append("source:\n" + truncate(context.content))
                elif not context.ok:
                    parts.append(f"sourceError: {context.message}")
            lines.append("\n".join(parts))
        elif observation.kind == "git_log":
            lines.append(
                "\n".join(
                    [
                        f"{index}. git_log {observation.path or '.'}: {observation.message}",
                        f"maxCount: {observation.max_count}",
                        f"log:\n{truncate(observation.log)}",
                    ]
                )
            )
        elif observation.kind == "git_show":
            target = f"{observation.rev} -- {observation.path}" if observation.path else observation.rev
            lines.append(
                "\n".join(
                    [
                        f"{index}. git_show {target}: {observation.message}",
                        f"maxOutputChars: {observation.max_output_chars}",
                        f"truncated: {str(observation.truncated).lower()}",
                        f"output:\n{truncate(observation.output)}",
                    ]
                )
            )
        elif observation.kind == "git_blame":
            line_range = ""
            if observation.start_line is not None:
                line_range = f":{observation.start_line}+{observation.line_count or 120}"
            lines.append(
                "\n".join(
                    [
                        f"{index}. git_blame {observation.path}{line_range}: {observation.message}",
                        f"maxOutputChars: {observation.max_output_chars}",
                        f"truncated: {str(observation.truncated).lower()}",
                        f"blame:\n{truncate(observation.blame)}",
                    ]
                )
            )
        elif observation.kind == "session_summary":
            lines.append(
                "\n".join(
                    [
                        f"{index}. session_summary {observation.run_id}: {observation.message}",
                        f"ok: {str(observation.ok).lower()}",
                        f"summary:\n{truncate(observation.summary)}",
                        f"recent:\n{truncate(chr(10).join(observation.recent_sessions))}",
                    ]
                )
            )
        elif observation.kind == "session_plan":
            lines.append(
                "\n".join(
                    [
                        f"{index}. session_plan {observation.run_id}: {observation.message}",
                        f"ok: {str(observation.ok).lower()}",
                        f"plan:\n{truncate(observation.plan)}",
                    ]
                )
            )
        elif observation.kind == "session_transcript":
            lines.append(
                "\n".join(
                    [
                        f"{index}. session_transcript {observation.run_id}: {observation.message}",
                        f"ok: {str(observation.ok).lower()}",
                        f"transcript:\n{truncate(observation.transcript)}",
                    ]
                )
            )
        elif observation.kind == "session_search":
            lines.append(
                "\n".join(
                    [
                        f"{index}. session_search {observation.run_id}: {observation.message}",
                        f"ok: {str(observation.ok).lower()}",
                        f"query: {observation.query}",
                        f"matches: {observation.shown_matches}/{observation.total_matches}",
                        f"timeline:\n{truncate(observation.matches)}",
                    ]
                )
            )
        elif observation.kind == "session_commands":
            lines.append(
                "\n".join(
                    [
                        f"{index}. session_commands {observation.run_id}: {observation.message}",
                        f"ok: {str(observation.ok).lower()}",
                        f"commands: {observation.shown_commands}/{observation.command_count}",
                        f"results:\n{truncate(observation.commands)}",
                    ]
                )
            )
        elif observation.kind == "session_output_contexts":
            parts = [
                (
                    f"{index}. session_output_contexts {observation.run_id}: {observation.message} "
                    f"ok={str(observation.ok).lower()} "
                    f"commands={observation.shown_commands}/{observation.command_count} "
                    f"totalRefs={observation.total_refs} truncated={str(observation.truncated).lower()}"
                )
            ]
            for item in observation.contexts:
                column = f":{item.column}" if item.column is not None else ""
                parts.append(
                    (
                        f"context: {item.path}:{item.line}{column} raw={item.raw!r} "
                        f"ok={str(item.ok).lower()} range={item.start_line}:{item.end_line} "
                        f"contextLines={item.context_lines} targetExists={str(item.target_line_exists).lower()} "
                        f"lines={item.line_count}/{item.total_lines if item.total_lines is not None else 'unknown'} "
                        f"truncated={str(item.truncated).lower()} maxBytes={item.max_bytes} "
                        f"message={item.message}"
                    )
                )
                if item.ok:
                    parts.append(f"content:\n{truncate(item.content)}")
            lines.append("\n".join(parts))
        elif observation.kind == "session_output_diagnostics":
            parts = [
                (
                    f"{index}. session_output_diagnostics {observation.run_id}: {observation.message} "
                    f"ok={str(observation.ok).lower()} "
                    f"commands={observation.shown_commands}/{observation.command_count} "
                    f"diagnostics={len(observation.diagnostics)}/{observation.total_diagnostics} "
                    f"totalRefs={observation.total_refs} "
                    f"diagnosticsTruncated={str(observation.diagnostics_truncated).lower()} "
                    f"contextsTruncated={str(observation.contexts_truncated).lower()}"
                )
            ]
            for diagnostic in observation.diagnostics:
                location = ""
                if diagnostic.path:
                    location = f" location={diagnostic.path}:{diagnostic.line if diagnostic.line is not None else '?'}"
                    if diagnostic.column is not None:
                        location += f":{diagnostic.column}"
                parts.append(
                    (
                        f"diagnostic: severity={diagnostic.severity} outputLine={diagnostic.output_line}"
                        f"{location} raw={diagnostic.raw!r} text={diagnostic.text}"
                    )
                )
            for item in observation.contexts:
                column = f":{item.column}" if item.column is not None else ""
                parts.append(
                    (
                        f"context: {item.path}:{item.line}{column} raw={item.raw!r} "
                        f"ok={str(item.ok).lower()} range={item.start_line}:{item.end_line} "
                        f"contextLines={item.context_lines} targetExists={str(item.target_line_exists).lower()} "
                        f"lines={item.line_count}/{item.total_lines if item.total_lines is not None else 'unknown'} "
                        f"truncated={str(item.truncated).lower()} maxBytes={item.max_bytes} "
                        f"message={item.message}"
                    )
                )
                if item.ok:
                    parts.append(f"content:\n{truncate(item.content)}")
            lines.append("\n".join(parts))
        elif observation.kind == "session_files":
            lines.append(
                "\n".join(
                    [
                        f"{index}. session_files {observation.run_id}: {observation.message}",
                        f"ok: {str(observation.ok).lower()}",
                        f"files: {observation.shown_files}/{observation.file_count}",
                        f"entries:\n{truncate(observation.files)}",
                    ]
                )
            )
        elif observation.kind == "session_failures":
            lines.append(
                "\n".join(
                    [
                        f"{index}. session_failures {observation.run_id}: {observation.message}",
                        f"ok: {str(observation.ok).lower()}",
                        f"failures: {observation.shown_failures}/{observation.failure_count}",
                        f"entries:\n{truncate(observation.failures)}",
                    ]
                )
            )
        elif observation.kind == "session_verification":
            lines.append(
                "\n".join(
                    [
                        f"{index}. session_verification {observation.run_id}: {observation.message}",
                        f"ok: {str(observation.ok).lower()}",
                        f"verification:\n{truncate(observation.verification)}",
                    ]
                )
            )
        elif observation.kind == "session_audit":
            process_lines = [
                (
                    f"active_process: {process.process_id} pid={process.pid} "
                    f"cwd={process.cwd} command={process.command}"
                )
                for process in observation.active_background_processes[:20]
            ]
            lines.append(
                "\n".join(
                    [
                        f"{index}. session_audit {observation.run_id}: {observation.message}",
                        f"ok: {str(observation.ok).lower()}",
                        f"ready: {str(observation.ready).lower()}",
                        f"blockers: {len(observation.blockers)}",
                        f"backgroundProcesses: started={observation.background_processes_started} active={len(observation.active_background_processes)}",
                        *[f"blocker: {blocker}" for blocker in observation.blockers[:20]],
                        *process_lines,
                        f"audit:\n{truncate(observation.audit)}",
                    ]
                )
            )
        elif observation.kind == "session_handoff":
            lines.append(
                "\n".join(
                    [
                        f"{index}. session_handoff {observation.run_id}: {observation.message}",
                        f"ok: {str(observation.ok).lower()}",
                        f"handoff:\n{truncate(observation.handoff)}",
                    ]
                )
            )
        elif observation.kind == "checkpoint_show":
            checkpoint = observation.checkpoint
            parts = [
                f"{index}. checkpoint_show: {observation.message}",
                f"ok: {str(observation.ok).lower()}",
            ]
            if checkpoint is not None:
                parts.extend(
                    [
                        f"id: {checkpoint.checkpoint_id}",
                        f"label: {checkpoint.label or 'none'}",
                        f"createdAt: {checkpoint.created_at}",
                        f"projectRoot: {observation.project_root or 'none'}",
                        f"head: {checkpoint.head}",
                        f"changedFiles: {checkpoint.changed_files}",
                        f"stagedFiles: {checkpoint.staged_files}",
                        f"unstagedFiles: {checkpoint.unstaged_files}",
                        f"untrackedFiles: {checkpoint.untracked_files}",
                        f"untrackedSavedFiles: {observation.untracked_saved_files}",
                        f"untrackedSkippedFiles: {observation.untracked_skipped_files}",
                        f"savedUntrackedPathsTruncated: {str(observation.saved_untracked_paths_truncated).lower()}",
                        f"savedUntrackedPaths: {', '.join(observation.saved_untracked_paths) or 'none'}",
                        f"stagedPatchChars: {observation.staged_patch_chars}",
                        f"unstagedPatchChars: {observation.unstaged_patch_chars}",
                    ]
                )
            if observation.git_status:
                parts.append(f"gitStatus:\n{truncate(observation.git_status)}")
            lines.append("\n".join(parts))
        elif observation.kind == "checkpoint_diff":
            lines.append(
                "\n".join(
                    [
                        f"{index}. checkpoint_diff {observation.checkpoint_id}: {observation.message}",
                        f"ok: {str(observation.ok).lower()}",
                        f"label: {observation.label or 'none'}",
                        f"createdAt: {observation.created_at or 'none'}",
                        f"maxChars: {observation.max_chars}",
                        f"stagedPatchChars: {observation.staged_patch_chars}",
                        f"stagedPatchTruncated: {str(observation.staged_patch_truncated).lower()}",
                        f"stagedPatch:\n{truncate(observation.staged_patch) if observation.staged_patch else 'no staged changes'}",
                        f"unstagedPatchChars: {observation.unstaged_patch_chars}",
                        f"unstagedPatchTruncated: {str(observation.unstaged_patch_truncated).lower()}",
                        f"unstagedPatch:\n{truncate(observation.unstaged_patch) if observation.unstaged_patch else 'no unstaged changes'}",
                    ]
                )
            )
        elif observation.kind == "checkpoint_status":
            lines.append(
                "\n".join(
                    [
                        f"{index}. checkpoint_status {observation.checkpoint_id}: {observation.message}",
                        f"ok: {str(observation.ok).lower()}",
                        f"matches: {str(observation.matches).lower()}",
                        f"statusMatches: {str(observation.status_matches).lower()}",
                        f"stagedPatchMatches: {str(observation.staged_patch_matches).lower()}",
                        f"unstagedPatchMatches: {str(observation.unstaged_patch_matches).lower()}",
                        f"untrackedFileMatches: {str(observation.untracked_file_matches).lower()}",
                        (
                            "saved/current changedFiles: "
                            f"{observation.saved_changed_files}/{observation.current_changed_files}, "
                            f"staged: {observation.saved_staged_files}/{observation.current_staged_files}, "
                            f"unstaged: {observation.saved_unstaged_files}/{observation.current_unstaged_files}, "
                            f"untracked: {observation.saved_untracked_files}/{observation.current_untracked_files}"
                        ),
                    ]
                )
            )
        elif observation.kind == "check_checkpoint_restore":
            lines.append(
                "\n".join(
                    [
                        f"{index}. check_checkpoint_restore {observation.checkpoint_id}: {observation.message}",
                        f"ok: {str(observation.ok).lower()}",
                        f"canRestore: {str(observation.can_restore).lower()}",
                        f"savedHead: {observation.saved_head or 'none'}",
                        f"currentHead: {observation.current_head or 'none'}",
                        f"savedUntrackedFiles: {observation.saved_untracked_files}",
                        f"currentUntrackedFiles: {observation.current_untracked_files}",
                        f"stagedPatchChars: {observation.staged_patch_chars}",
                        f"unstagedPatchChars: {observation.unstaged_patch_chars}",
                    ]
                )
            )
        elif observation.kind == "checkpoint_restore":
            lines.append(
                "\n".join(
                    [
                        f"{index}. checkpoint_restore {observation.checkpoint_id}: {observation.message}",
                        f"ok: {str(observation.ok).lower()}",
                        f"restored: {str(observation.restored).lower()}",
                        f"matches: {str(observation.matches).lower()}",
                        f"savedHead: {observation.saved_head or 'none'}",
                        f"currentHead: {observation.current_head or 'none'}",
                        f"savedUntrackedFiles: {observation.saved_untracked_files}",
                        f"currentUntrackedFiles: {observation.current_untracked_files}",
                        f"stagedPatchChars: {observation.staged_patch_chars}",
                        f"unstagedPatchChars: {observation.unstaged_patch_chars}",
                    ]
                )
            )
        elif observation.kind == "check_checkpoint_delete":
            lines.append(
                "\n".join(
                    [
                        f"{index}. check_checkpoint_delete {observation.checkpoint_id}: {observation.message}",
                        f"ok: {str(observation.ok).lower()}",
                        f"canDelete: {str(observation.can_delete).lower()}",
                        f"createdAt: {observation.created_at or 'none'}",
                    ]
                )
            )
        elif observation.kind == "checkpoint_delete":
            lines.append(
                "\n".join(
                    [
                        f"{index}. checkpoint_delete {observation.checkpoint_id}: {observation.message}",
                        f"ok: {str(observation.ok).lower()}",
                        f"deleted: {str(observation.deleted).lower()}",
                    ]
                )
            )
        elif observation.kind == "check_checkpoint_prune":
            checkpoint_ids = ", ".join(item.checkpoint_id for item in observation.checkpoints) or "none"
            lines.append(
                "\n".join(
                    [
                        f"{index}. check_checkpoint_prune keep_last={observation.keep_last}: {observation.message}",
                        f"ok: {str(observation.ok).lower()}",
                        f"total/kept/deleteCount: {observation.total}/{observation.kept}/{observation.delete_count}",
                        f"deleteCheckpoints: {checkpoint_ids}",
                    ]
                )
            )
        elif observation.kind == "checkpoint_prune":
            checkpoint_ids = ", ".join(item.checkpoint_id for item in observation.checkpoints) or "none"
            lines.append(
                "\n".join(
                    [
                        f"{index}. checkpoint_prune keep_last={observation.keep_last}: {observation.message}",
                        f"ok: {str(observation.ok).lower()}",
                        f"total/kept/deleted: {observation.total}/{observation.kept}/{observation.deleted}",
                        f"deletedCheckpoints: {checkpoint_ids}",
                    ]
                )
            )
        elif observation.kind == "edit_file":
            lines.append(
                "\n".join(
                    [
                        f"{index}. edit_file {observation.path}: {observation.message}",
                        f"diff:\n{truncate(observation.diff)}",
                    ]
                )
            )
        elif observation.kind == "check_edit_file":
            lines.append(
                "\n".join(
                    [
                        f"{index}. check_edit_file {observation.path}: {observation.message}",
                        f"diff:\n{truncate(observation.diff)}",
                    ]
                )
            )
        elif observation.kind == "multi_edit_file":
            lines.append(
                "\n".join(
                    [
                        f"{index}. multi_edit_file {observation.path}: {observation.message}",
                        f"diff:\n{truncate(observation.diff)}",
                    ]
                )
            )
        elif observation.kind == "check_multi_edit_file":
            lines.append(
                "\n".join(
                    [
                        f"{index}. check_multi_edit_file {observation.path}: {observation.message}",
                        f"diff:\n{truncate(observation.diff)}",
                    ]
                )
            )
        elif observation.kind == "check_replace_lines":
            lines.append(
                "\n".join(
                    [
                        (
                            f"{index}. check_replace_lines {observation.path}:"
                            f"{observation.start_line}-{observation.end_line}: {observation.message}"
                        ),
                        f"diff:\n{truncate(observation.diff)}",
                    ]
                )
            )
        elif observation.kind == "check_replace_python_definition":
            target = observation.definition_path or observation.path or "."
            lines.append(
                "\n".join(
                    [
                        (
                            f"{index}. check_replace_python_definition {observation.symbol} in {target}: "
                            f"{observation.message}"
                        ),
                        f"qualifiedName: {observation.qualified_name or '.'}",
                        f"lines: {observation.start_line or '?'}-{observation.end_line or '?'}",
                        f"diff:\n{truncate(observation.diff)}",
                    ]
                )
            )
        elif observation.kind == "replace_python_definition":
            target = observation.definition_path or observation.path or "."
            lines.append(
                "\n".join(
                    [
                        (
                            f"{index}. replace_python_definition {observation.symbol} in {target}: "
                            f"{observation.message}"
                        ),
                        f"qualifiedName: {observation.qualified_name or '.'}",
                        f"lines: {observation.start_line or '?'}-{observation.end_line or '?'}",
                        f"diff:\n{truncate(observation.diff)}",
                    ]
                )
            )
        elif observation.kind == "replace_lines":
            lines.append(
                "\n".join(
                    [
                        (
                            f"{index}. replace_lines {observation.path}:{observation.start_line}-{observation.end_line}: "
                            f"{observation.message}"
                        ),
                        f"diff:\n{truncate(observation.diff)}",
                    ]
                )
            )
        elif observation.kind == "check_insert_lines":
            lines.append(
                "\n".join(
                    [
                        f"{index}. check_insert_lines {observation.path}:{observation.line}: {observation.message}",
                        f"diff:\n{truncate(observation.diff)}",
                    ]
                )
            )
        elif observation.kind == "insert_lines":
            lines.append(
                "\n".join(
                    [
                        f"{index}. insert_lines {observation.path}:{observation.line}: {observation.message}",
                        f"diff:\n{truncate(observation.diff)}",
                    ]
                )
            )
        elif observation.kind == "check_append_file":
            lines.append(
                "\n".join(
                    [
                        f"{index}. check_append_file {observation.path}: {observation.message}",
                        f"diff:\n{truncate(observation.diff)}",
                    ]
                )
            )
        elif observation.kind == "append_file":
            lines.append(
                "\n".join(
                    [
                        f"{index}. append_file {observation.path}: {observation.message}",
                        f"diff:\n{truncate(observation.diff)}",
                    ]
                )
            )
        elif observation.kind == "regex_replace":
            lines.append(
                "\n".join(
                    [
                        (
                            f"{index}. regex_replace {observation.path}: {observation.message} "
                            f"replacements={observation.replacements} count={observation.count}"
                        ),
                        f"diff:\n{truncate(observation.diff)}",
                    ]
                )
            )
        elif observation.kind == "check_regex_replace":
            lines.append(
                "\n".join(
                    [
                        (
                            f"{index}. check_regex_replace {observation.path}: {observation.message} "
                            f"replacements={observation.replacements} count={observation.count}"
                        ),
                        f"diff:\n{truncate(observation.diff)}",
                    ]
                )
            )
        elif observation.kind in {"check_json_set", "json_set", "check_json_remove", "json_remove"}:
            lines.append(
                "\n".join(
                    [
                        f"{index}. {observation.kind} {observation.path} {observation.pointer}: {observation.message}",
                        f"diff:\n{truncate(observation.diff)}",
                    ]
                )
            )
        elif observation.kind in {"check_json_patch", "json_patch"}:
            lines.append(
                "\n".join(
                    [
                        f"{index}. {observation.kind} {observation.path}: {observation.message} operations={observation.operation_count}",
                        f"diff:\n{truncate(observation.diff)}",
                    ]
                )
            )
        elif observation.kind == "check_patch":
            lines.append(
                "\n".join(
                    [
                        f"{index}. check_patch {observation.path}: {observation.message}",
                        f"diff:\n{truncate(observation.diff)}",
                    ]
                )
            )
        elif observation.kind == "check_patches":
            lines.append(
                "\n".join(
                    [
                        f"{index}. check_patches {', '.join(observation.files) or 'no files'}: {observation.message}",
                        f"diff:\n{truncate(observation.diff)}",
                    ]
                )
            )
        elif observation.kind == "patch_file":
            lines.append(
                "\n".join(
                    [
                        f"{index}. patch_file {observation.path}: {observation.message}",
                        f"diff:\n{truncate(observation.diff)}",
                    ]
                )
            )
        elif observation.kind == "patch_files":
            lines.append(
                "\n".join(
                    [
                        f"{index}. patch_files {', '.join(observation.files) or 'no files'}: {observation.message}",
                        f"diff:\n{truncate(observation.diff)}",
                    ]
                )
            )
        elif observation.kind == "delete_file":
            lines.append(
                "\n".join(
                    [
                        f"{index}. delete_file {observation.path}: {observation.message}",
                        f"diff:\n{truncate(observation.diff)}",
                    ]
                )
            )
        elif observation.kind == "check_delete_file":
            lines.append(
                "\n".join(
                    [
                        f"{index}. check_delete_file {observation.path}: {observation.message}",
                        f"diff:\n{truncate(observation.diff)}",
                    ]
                )
            )
        elif observation.kind in {"check_delete_files", "delete_files"}:
            lines.append(
                "\n".join(
                    [
                        f"{index}. {observation.kind} {', '.join(observation.paths)}: {observation.message}",
                        f"diff:\n{truncate(observation.diff)}",
                    ]
                )
            )
        elif observation.kind == "move_file":
            lines.append(
                f"{index}. move_file {observation.source} -> {observation.destination}: {observation.message}"
            )
        elif observation.kind == "check_move_file":
            lines.append(
                f"{index}. check_move_file {observation.source} -> {observation.destination}: {observation.message}"
            )
        elif observation.kind in {"check_move_files", "move_files"}:
            transfers = ", ".join(
                f"{transfer.source} -> {transfer.destination}" for transfer in observation.transfers
            )
            lines.append(f"{index}. {observation.kind} {transfers}: {observation.message}")
        elif observation.kind == "copy_file":
            lines.append(
                f"{index}. copy_file {observation.source} -> {observation.destination}: {observation.message}"
            )
        elif observation.kind == "check_copy_file":
            lines.append(
                f"{index}. check_copy_file {observation.source} -> {observation.destination}: {observation.message}"
            )
        elif observation.kind in {"check_copy_files", "copy_files"}:
            transfers = ", ".join(
                f"{transfer.source} -> {transfer.destination}" for transfer in observation.transfers
            )
            lines.append(f"{index}. {observation.kind} {transfers}: {observation.message}")
        elif observation.kind == "check_move_dir":
            lines.append(
                f"{index}. check_move_dir {observation.source} -> {observation.destination}: {observation.message}"
            )
        elif observation.kind == "move_dir":
            lines.append(
                f"{index}. move_dir {observation.source} -> {observation.destination}: {observation.message}"
            )
        elif observation.kind in {"check_move_dirs", "move_dirs"}:
            transfers = ", ".join(
                f"{transfer.source} -> {transfer.destination}" for transfer in observation.transfers
            )
            lines.append(f"{index}. {observation.kind} {transfers}: {observation.message}")
        elif observation.kind == "check_copy_dir":
            lines.append(
                f"{index}. check_copy_dir {observation.source} -> {observation.destination}: {observation.message}"
            )
        elif observation.kind == "copy_dir":
            lines.append(
                f"{index}. copy_dir {observation.source} -> {observation.destination}: {observation.message}"
            )
        elif observation.kind in {"check_copy_dirs", "copy_dirs"}:
            transfers = ", ".join(
                f"{transfer.source} -> {transfer.destination}" for transfer in observation.transfers
            )
            lines.append(f"{index}. {observation.kind} {transfers}: {observation.message}")
        elif observation.kind == "check_create_dir":
            lines.append(f"{index}. check_create_dir {observation.path}: {observation.message}")
        elif observation.kind == "create_dir":
            lines.append(f"{index}. create_dir {observation.path}: {observation.message}")
        elif observation.kind == "check_create_dirs":
            lines.append(f"{index}. check_create_dirs {', '.join(observation.paths)}: {observation.message}")
        elif observation.kind == "create_dirs":
            lines.append(f"{index}. create_dirs {', '.join(observation.paths)}: {observation.message}")
        elif observation.kind == "check_delete_empty_dir":
            lines.append(f"{index}. check_delete_empty_dir {observation.path}: {observation.message}")
        elif observation.kind == "delete_empty_dir":
            lines.append(f"{index}. delete_empty_dir {observation.path}: {observation.message}")
        elif observation.kind == "check_delete_empty_dirs":
            lines.append(f"{index}. check_delete_empty_dirs {', '.join(observation.paths)}: {observation.message}")
        elif observation.kind == "delete_empty_dirs":
            lines.append(f"{index}. delete_empty_dirs {', '.join(observation.paths)}: {observation.message}")
        elif observation.kind == "check_set_executable":
            lines.append(
                (
                    f"{index}. check_set_executable {observation.path}: {observation.message} "
                    f"ok={str(observation.ok).lower()} executable={str(observation.executable).lower()} "
                    f"mode={observation.mode_before or '?'}->{observation.mode_after or '?'}"
                )
            )
        elif observation.kind == "set_executable":
            lines.append(
                (
                    f"{index}. set_executable {observation.path}: {observation.message} "
                    f"ok={str(observation.ok).lower()} executable={str(observation.executable).lower()} "
                    f"mode={observation.mode_before or '?'}->{observation.mode_after or '?'}"
                )
            )
        elif observation.kind == "start_command":
            lines.append(
                "\n".join(
                    [
                        f"{index}. start_command: {observation.message}",
                        f"processId: {observation.process_id or 'none'}",
                        f"pid: {observation.pid or 'none'}",
                        f"command: {observation.command}",
                        f"cwd: {observation.cwd}",
                        f"stdoutPath: {observation.stdout_path or 'none'}",
                        f"stderrPath: {observation.stderr_path or 'none'}",
                    ]
                )
            )
        elif observation.kind == "read_process":
            parts = [
                f"{index}. read_process {observation.process_id}: {observation.message}",
                f"pid: {observation.pid or 'none'}",
                f"running: {str(observation.running).lower()}",
                f"exitCode: {observation.exit_code}",
                f"signal: {observation.signal or 'none'}",
                f"maxOutputChars: {observation.max_output_chars}",
                f"stdout:\n{truncate(observation.stdout)}",
                f"stderr:\n{truncate(observation.stderr)}",
                format_command_output_diagnostics(observation),
                format_command_output_contexts(observation),
            ]
            lines.append("\n".join(parts))
        elif observation.kind == "process_output_contexts":
            parts = [
                f"{index}. process_output_contexts {observation.process_id}: {observation.message}",
                f"pid: {observation.pid or 'none'}",
                f"ok: {str(observation.ok).lower()}",
                f"running: {str(observation.running).lower()}",
                f"contexts: {len(observation.contexts)}/{observation.total_refs}",
                f"truncated: {str(observation.truncated).lower()}",
                f"stdoutChars: {observation.stdout_chars}",
                f"stderrChars: {observation.stderr_chars}",
                f"maxOutputChars: {observation.max_output_chars}",
            ]
            for item in observation.contexts:
                column = f":{item.column}" if item.column is not None else ""
                parts.append(
                    (
                        f"context: {item.path}:{item.line}{column} raw={item.raw!r} "
                        f"ok={str(item.ok).lower()} range={item.start_line}:{item.end_line} "
                        f"contextLines={item.context_lines} message={item.message}"
                    )
                )
                if item.ok:
                    parts.append(f"content:\n{truncate(item.content)}")
            lines.append("\n".join(parts))
        elif observation.kind == "process_output_diagnostics":
            parts = [
                f"{index}. process_output_diagnostics {observation.process_id}: {observation.message}",
                f"pid: {observation.pid or 'none'}",
                f"ok: {str(observation.ok).lower()}",
                f"running: {str(observation.running).lower()}",
                f"diagnostics: {len(observation.diagnostics)}/{observation.total_diagnostics}",
                f"contexts: {len(observation.contexts)}/{observation.total_refs}",
                f"diagnosticsTruncated: {str(observation.diagnostics_truncated).lower()}",
                f"contextsTruncated: {str(observation.contexts_truncated).lower()}",
                f"stdoutChars: {observation.stdout_chars}",
                f"stderrChars: {observation.stderr_chars}",
                f"maxOutputChars: {observation.max_output_chars}",
            ]
            for diagnostic in observation.diagnostics:
                location = ""
                if diagnostic.path:
                    location = f" location={diagnostic.path}:{diagnostic.line if diagnostic.line is not None else '?'}"
                    if diagnostic.column is not None:
                        location += f":{diagnostic.column}"
                parts.append(
                    (
                        f"diagnostic: severity={diagnostic.severity} outputLine={diagnostic.output_line}"
                        f"{location} raw={diagnostic.raw!r} text={diagnostic.text}"
                    )
                )
            for item in observation.contexts:
                column = f":{item.column}" if item.column is not None else ""
                parts.append(
                    (
                        f"context: {item.path}:{item.line}{column} raw={item.raw!r} "
                        f"ok={str(item.ok).lower()} range={item.start_line}:{item.end_line} "
                        f"contextLines={item.context_lines} message={item.message}"
                    )
                )
                if item.ok:
                    parts.append(f"content:\n{truncate(item.content)}")
            lines.append("\n".join(parts))
        elif observation.kind == "wait_process":
            parts = [
                f"{index}. wait_process {observation.process_id}: {observation.message}",
                f"pid: {observation.pid or 'none'}",
                f"running: {str(observation.running).lower()}",
                f"timedOut: {str(observation.timed_out).lower()}",
                f"matched: {str(observation.matched).lower()}",
                f"matchedStream: {observation.matched_stream or 'none'}",
                f"matchedPattern: {observation.matched_pattern or 'none'}",
                f"timeoutMs: {observation.timeout_ms}",
                f"exitCode: {observation.exit_code}",
                f"signal: {observation.signal or 'none'}",
                f"maxOutputChars: {observation.max_output_chars}",
                f"stdout:\n{truncate(observation.stdout)}",
                f"stderr:\n{truncate(observation.stderr)}",
                format_command_output_diagnostics(observation),
                format_command_output_contexts(observation),
            ]
            lines.append("\n".join(parts))
        elif observation.kind == "check_write_process":
            lines.append(
                "\n".join(
                    [
                        f"{index}. check_write_process {observation.process_id}: {observation.message}",
                        f"pid: {observation.pid or 'none'}",
                        f"ok: {str(observation.ok).lower()}",
                        f"running: {str(observation.running).lower()}",
                        f"cwd: {observation.cwd or 'none'}",
                        f"contentChars: {observation.content_chars}",
                        f"command: {observation.command or 'none'}",
                    ]
                )
            )
        elif observation.kind == "write_process":
            lines.append(
                "\n".join(
                    [
                        f"{index}. write_process {observation.process_id}: {observation.message}",
                        f"pid: {observation.pid or 'none'}",
                        f"ok: {str(observation.ok).lower()}",
                        f"running: {str(observation.running).lower()}",
                        f"cwd: {observation.cwd or 'none'}",
                        f"contentChars: {observation.content_chars}",
                        f"command: {observation.command or 'none'}",
                    ]
                )
            )
        elif observation.kind == "list_processes":
            process_lines = [
                (
                    f"- {process.process_id} pid={process.pid} cwd={process.cwd} running={str(process.running).lower()} "
                    f"exitCode={process.exit_code} signal={process.signal or 'none'} command={process.command}"
                )
                for process in observation.processes
            ]
            lines.append(
                "\n".join(
                    [
                        f"{index}. list_processes: {observation.message}",
                        *process_lines,
                    ]
                )
            )
        elif observation.kind == "check_stop_all_processes":
            process_lines = [
                (
                    f"- {process.process_id} pid={process.pid} cwd={process.cwd} running={str(process.running).lower()} "
                    f"exitCode={process.exit_code} signal={process.signal or 'none'} command={process.command}"
                )
                for process in observation.processes
            ]
            lines.append(
                "\n".join(
                    [
                        f"{index}. check_stop_all_processes: {observation.message}",
                        f"ok: {str(observation.ok).lower()}",
                        f"runningCount: {observation.running_count}",
                        *process_lines,
                    ]
                )
            )
        elif observation.kind == "check_stop_process":
            lines.append(
                "\n".join(
                    [
                        f"{index}. check_stop_process {observation.process_id}: {observation.message}",
                        f"ok: {str(observation.ok).lower()}",
                        f"pid: {observation.pid or 'none'}",
                        f"running: {str(observation.running).lower()}",
                        f"exitCode: {observation.exit_code}",
                        f"signal: {observation.signal or 'none'}",
                        f"cwd: {observation.cwd or 'none'}",
                        f"command: {observation.command or 'none'}",
                    ]
                )
            )
        elif observation.kind == "stop_all_processes":
            stopped_lines = [
                (
                    f"- {process.process_id} pid={process.pid} cwd={process.cwd} ok={str(process.ok).lower()} "
                    f"exitCode={process.exit_code} signal={process.signal or 'none'} command={process.command}"
                )
                for process in observation.stopped
            ]
            lines.append(
                "\n".join(
                    [
                        f"{index}. stop_all_processes: {observation.message}",
                        f"ok: {str(observation.ok).lower()}",
                        *stopped_lines,
                    ]
                )
            )
        elif observation.kind == "stop_process":
            lines.append(
                "\n".join(
                    [
                        f"{index}. stop_process {observation.process_id}: {observation.message}",
                        f"pid: {observation.pid or 'none'}",
                        f"exitCode: {observation.exit_code}",
                        f"signal: {observation.signal or 'none'}",
                    ]
                )
            )
        elif observation.kind == "finish":
            lines.append(f"{index}. finish: {observation.message}")
        elif observation.kind == "tool_error":
            lines.append(f"{index}. tool_error {observation.tool}: {observation.message}")
        elif observation.kind == "update_plan":
            lines.append(
                "\n".join(
                    [
                        f"{index}. update_plan: {observation.message}",
                        *[f"- {item.status}: {item.step}" for item in observation.plan],
                    ]
                )
            )
        elif observation.kind == "run_commands":
            parts = [
                f"{index}. run_commands: {observation.message}",
                f"ok: {str(observation.ok).lower()}",
                f"stoppedEarly: {str(observation.stopped_early).lower()}",
            ]
            for result in observation.results:
                parts.extend(
                    [
                        f"command: {result.command}",
                        f"cwd: {result.cwd}",
                        f"exitCode: {result.exit_code}",
                        f"timedOut: {str(result.timed_out).lower()}",
                        f"timeoutMs: {result.timeout_ms}",
                        f"maxOutputChars: {result.max_output_chars}",
                        f"stdoutTruncated: {str(result.stdout_truncated).lower()} stderrTruncated={str(result.stderr_truncated).lower()} signal={result.signal or 'none'}",
                        f"stdout:\n{truncate(result.stdout)}",
                        f"stderr:\n{truncate(result.stderr)}",
                        format_command_output_diagnostics(result),
                        format_command_output_contexts(result),
                    ]
                )
            lines.append("\n".join(parts))
        elif observation.kind == "run_suggested_checks":
            parts = [
                f"{index}. run_suggested_checks: {observation.message}",
                f"ok: {str(observation.ok).lower()}",
                f"suggested: {len(observation.suggested_checks)}/{observation.total}",
                f"truncated: {str(observation.truncated).lower()}",
                f"skippedUnavailable: {observation.skipped_unavailable}",
                f"stoppedEarly: {str(observation.stopped_early).lower()}",
            ]
            for result in observation.results:
                parts.extend(
                    [
                        f"command: {result.command}",
                        f"cwd: {result.cwd}",
                        f"exitCode: {result.exit_code}",
                        f"timedOut: {str(result.timed_out).lower()}",
                        f"timeoutMs: {result.timeout_ms}",
                        f"maxOutputChars: {result.max_output_chars}",
                        f"stdoutTruncated: {str(result.stdout_truncated).lower()} stderrTruncated={str(result.stderr_truncated).lower()} signal={result.signal or 'none'}",
                        f"stdout:\n{truncate(result.stdout)}",
                        f"stderr:\n{truncate(result.stderr)}",
                        format_command_output_diagnostics(result),
                        format_command_output_contexts(result),
                    ]
                )
            lines.append("\n".join(parts))
        elif observation.kind == "run_focused_test_commands":
            parts = [
                f"{index}. run_focused_test_commands: {observation.message}",
                f"ok: {str(observation.ok).lower()}",
                f"focused: {len(observation.focused_commands)}/{observation.total}",
                f"truncated: {str(observation.truncated).lower()}",
                f"skippedUnavailable: {observation.skipped_unavailable}",
                f"stoppedEarly: {str(observation.stopped_early).lower()}",
            ]
            if observation.target_paths:
                parts.append("target_paths:\n" + "\n".join(observation.target_paths[:120]))
            for result in observation.results:
                parts.extend(
                    [
                        f"command: {result.command}",
                        f"cwd: {result.cwd}",
                        f"exitCode: {result.exit_code}",
                        f"timedOut: {str(result.timed_out).lower()}",
                        f"timeoutMs: {result.timeout_ms}",
                        f"maxOutputChars: {result.max_output_chars}",
                        f"stdoutTruncated: {str(result.stdout_truncated).lower()} stderrTruncated={str(result.stderr_truncated).lower()} signal={result.signal or 'none'}",
                        f"stdout:\n{truncate(result.stdout)}",
                        f"stderr:\n{truncate(result.stderr)}",
                        format_command_output_diagnostics(result),
                        format_command_output_contexts(result),
                    ]
                )
            lines.append("\n".join(parts))
        else:
            result = observation.result
            lines.append(
                "\n".join(
                    [
                        f"{index}. run_command: {result.command}",
                        f"cwd: {result.cwd}",
                        f"exitCode: {result.exit_code}",
                        f"timedOut: {str(result.timed_out).lower()}",
                        f"timeoutMs: {result.timeout_ms}",
                        f"maxOutputChars: {result.max_output_chars}",
                        f"stdoutTruncated: {str(result.stdout_truncated).lower()}",
                        f"stderrTruncated: {str(result.stderr_truncated).lower()}",
                        f"signal: {result.signal or 'none'}",
                        f"stdout:\n{truncate(result.stdout)}",
                        f"stderr:\n{truncate(result.stderr)}",
                        format_command_output_diagnostics(result),
                        format_command_output_contexts(result),
                    ]
                )
            )

    return "\n\n".join(lines)


def format_command_output_diagnostics(result: object) -> str:
    diagnostics = getattr(result, "output_diagnostics", [])
    total = getattr(result, "output_diagnostic_total", 0)
    truncated = getattr(result, "output_diagnostics_truncated", False)
    if not diagnostics and not total:
        return "outputDiagnostics: none"
    lines = [
        (
            f"outputDiagnostics: {len(diagnostics)}/{total} "
            f"truncated={str(bool(truncated)).lower()}"
        )
    ]
    for item in diagnostics:
        location = ""
        if item.path:
            location = f" location={item.path}:{item.line if item.line is not None else '?'}"
            if item.column is not None:
                location += f":{item.column}"
        lines.append(
            (
                f"diagnostic: severity={item.severity} outputLine={item.output_line}"
                f"{location} raw={item.raw!r} text={item.text}"
            )
        )
    return "\n".join(lines)


def format_command_output_contexts(result: object) -> str:
    contexts = getattr(result, "output_contexts", [])
    total_refs = getattr(result, "output_context_total_refs", 0)
    truncated = getattr(result, "output_contexts_truncated", False)
    if not contexts and not total_refs:
        return "outputContexts: none"
    lines = [
        (
            f"outputContexts: {len(contexts)}/{total_refs} "
            f"truncated={str(bool(truncated)).lower()}"
        )
    ]
    for item in contexts:
        column = f":{item.column}" if item.column is not None else ""
        lines.append(
            (
                f"context: {item.path}:{item.line}{column} raw={item.raw!r} "
                f"ok={str(item.ok).lower()} range={item.start_line}:{item.end_line} "
                f"contextLines={item.context_lines} targetExists={str(item.target_line_exists).lower()} "
                f"lines={item.line_count}/{item.total_lines if item.total_lines is not None else 'unknown'} "
                f"truncated={str(item.truncated).lower()} maxBytes={item.max_bytes} "
                f"message={item.message}"
            )
        )
        if item.ok:
            lines.append(f"content:\n{truncate(item.content)}")
    return "\n".join(lines)


def truncate(value: str, max_length: int = 4_000) -> str:
    # Truncate long stdout/stderr fields so prompt context stays within practical size.
    if not value:
        return ""
    if len(value) <= max_length:
        return value
    return f"{value[:max_length]}\n[truncated]"
