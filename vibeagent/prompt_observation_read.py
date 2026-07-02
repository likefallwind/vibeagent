from __future__ import annotations

from .prompt_observation_utils import truncate


def format_read_observation(index: int, observation: object) -> str | None:
    if observation.kind == "list_files":
        return "\n".join(
            [
                f"{index}. list_files {observation.path}: {observation.message}",
                *observation.files[:120],
            ]
        )
    if observation.kind == "list_tree":
        return "\n".join(
            [
                (
                    f"{index}. list_tree {observation.path}: {observation.message} "
                    f"maxDepth={observation.max_depth} truncated={str(observation.truncated).lower()}"
                ),
                *observation.entries[:160],
            ]
        )
    if observation.kind == "repo_map":
        return _format_repo_map(index, observation)
    if observation.kind == "read_file":
        return "\n".join(
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
    if observation.kind == "read_file_context":
        return "\n".join(
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
    if observation.kind == "read_file_contexts":
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
        return "\n".join(parts)
    if observation.kind == "tail_file":
        return "\n".join(
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
    if observation.kind == "read_files":
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
        return "\n".join(parts)
    if observation.kind == "read_file_ranges":
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
        return "\n".join(parts)
    if observation.kind == "file_info":
        return _format_file_info(index, observation)
    if observation.kind == "image_info":
        return _format_image_info(index, observation)
    if observation.kind == "search":
        return "\n".join(
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
    if observation.kind == "search_contexts":
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
        return "\n".join(parts)
    if observation.kind == "glob":
        return "\n".join(
            [
                f"{index}. glob {observation.pattern}: {observation.message}",
                *observation.matches[:120],
            ]
        )
    return None


def _format_repo_map(index: int, observation: object) -> str:
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
    return "\n".join(parts)


def _format_file_info(index: int, observation: object) -> str:
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
    return "\n".join(parts)


def _format_image_info(index: int, observation: object) -> str:
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
    return "\n".join(parts)


__all__ = ["format_read_observation"]
