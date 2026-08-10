from __future__ import annotations

import hashlib

from .action_memory_types import CheckMemoryWriteAction, MemoryListAction, MemoryReadAction, MemoryWriteAction
from .observation_memory_types import (
    MemoryFileInfo,
    CheckMemoryWriteObservation,
    MemoryListObservation,
    MemoryReadObservation,
    MemoryWriteObservation,
)
from .workspace_core import RunWorkspace
from .workspace_memory import (
    MemoryStoreError,
    list_memory_files,
    preview_memory_write,
    read_memory_file,
    write_memory_file,
)


def execute_memory_action(workspace: RunWorkspace, action: object) -> object | None:
    try:
        if isinstance(action, CheckMemoryWriteAction):
            preview = preview_memory_write(workspace, action.path, action.content, mode=action.mode)
            return CheckMemoryWriteObservation(
                kind="check_memory_write",
                ok=True,
                path=preview.path,
                mode=action.mode,
                content_sha256=hashlib.sha256(action.content.encode("utf-8")).hexdigest(),
                current_bytes=preview.current_bytes,
                proposed_bytes=preview.proposed_bytes,
                redacted=preview.redacted,
                diff=preview.diff,
                message=f"Previewed memory write for {preview.path}.",
            )
        if isinstance(action, MemoryListAction):
            files = list_memory_files(workspace)
            return MemoryListObservation(
                kind="memory_list",
                ok=True,
                files=[MemoryFileInfo(path=item.path, bytes=item.bytes) for item in files],
                message=f"Found {len(files)} memory file(s).",
            )
        if isinstance(action, MemoryReadAction):
            content, truncated = read_memory_file(workspace, action.path)
            return MemoryReadObservation(
                kind="memory_read",
                ok=True,
                path=action.path,
                content=content,
                truncated=truncated,
                message=(
                    f"Read memory file {action.path}."
                    if content
                    else f"Memory file is empty or missing: {action.path}"
                ),
            )
        if isinstance(action, MemoryWriteAction):
            result = write_memory_file(workspace, action.path, action.content, mode=action.mode)
            return MemoryWriteObservation(
                kind="memory_write",
                ok=True,
                path=result.path,
                bytes=result.bytes,
                redacted=result.redacted,
                message=(
                    f"Wrote memory file {result.path}; sensitive values were redacted."
                    if result.redacted
                    else f"Wrote memory file {result.path}."
                ),
            )
    except (OSError, UnicodeError, MemoryStoreError) as error:
        return _memory_failure(action, str(error))
    return None


def _memory_failure(action: object, message: str) -> object:
    if isinstance(action, CheckMemoryWriteAction):
        return CheckMemoryWriteObservation(
            kind="check_memory_write",
            ok=False,
            path=action.path,
            mode=action.mode,
            content_sha256=hashlib.sha256(action.content.encode("utf-8")).hexdigest(),
            current_bytes=0,
            proposed_bytes=0,
            redacted=False,
            diff="",
            message=message,
        )
    if isinstance(action, MemoryListAction):
        return MemoryListObservation(kind="memory_list", ok=False, message=message)
    if isinstance(action, MemoryReadAction):
        return MemoryReadObservation(
            kind="memory_read", ok=False, path=action.path, content="", truncated=False, message=message
        )
    assert isinstance(action, MemoryWriteAction)
    return MemoryWriteObservation(
        kind="memory_write", ok=False, path=action.path, bytes=0, redacted=False, message=message
    )
