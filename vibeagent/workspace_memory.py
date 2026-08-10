from __future__ import annotations

from dataclasses import dataclass, replace
import difflib
import os
from pathlib import Path
import re
from threading import RLock
from uuid import uuid4

from .config import read_project_config
from .redaction import redact_sensitive_text
from .workspace_core import RunWorkspace
from .workspace_git_utils import run_readonly_git


MEMORY_ENTRYPOINT = "MEMORY.md"
MEMORY_STARTUP_MAX_BYTES = 25_000
MEMORY_STARTUP_MAX_LINES = 200
MEMORY_FILE_MAX_BYTES = 256_000
MEMORY_WRITE_MAX_BYTES = 64_000
MEMORY_FILE_LIMIT = 100
_MEMORY_FILE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}\.md$")
_MEMORY_NAMESPACE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
AGENT_MEMORY_SCOPES = frozenset({"project", "local"})
_DISABLE_VALUES = {"1", "true", "yes", "on"}
_MEMORY_LOCK = RLock()


class MemoryStoreError(ValueError):
    pass


@dataclass(frozen=True)
class AutoMemorySnapshot:
    enabled: bool
    root: Path
    content: str = ""
    truncated: bool = False
    error: str | None = None


@dataclass(frozen=True)
class MemoryFile:
    path: str
    bytes: int


@dataclass(frozen=True)
class MemoryWriteResult:
    path: str
    bytes: int
    redacted: bool


@dataclass(frozen=True)
class MemoryWritePreview:
    path: str
    current_bytes: int
    proposed_bytes: int
    redacted: bool
    diff: str


def project_memory_root(workspace: RunWorkspace) -> Path:
    project_root = _shared_project_root(workspace.root)
    if workspace.memory_namespace is not None:
        namespace = _validate_memory_namespace(workspace.memory_namespace)
        if workspace.memory_scope == "project":
            return project_root / ".claude" / "agent-memory" / namespace
        if workspace.memory_scope == "local":
            return project_root / ".claude" / "agent-memory-local" / namespace
        raise MemoryStoreError(f"Unsupported agent memory scope: {workspace.memory_scope}.")
    return project_root / ".vibeagent" / "memory"


def with_agent_memory(workspace: RunWorkspace, name: str, scope: str) -> RunWorkspace:
    if scope not in AGENT_MEMORY_SCOPES:
        raise MemoryStoreError(f"Agent memory scope must be one of: {', '.join(sorted(AGENT_MEMORY_SCOPES))}.")
    return replace(
        workspace,
        memory_scope=scope,
        memory_namespace=_validate_memory_namespace(name),
    )


def auto_memory_enabled(workspace: RunWorkspace, env: dict[str, str] | None = None) -> bool:
    source = os.environ if env is None else env
    if str(source.get("VIBEAGENT_DISABLE_AUTO_MEMORY", "")).strip().lower() in _DISABLE_VALUES:
        return False
    try:
        configured = read_project_config(workspace.root).get("auto_memory_enabled")
    except (OSError, ValueError):
        return True
    return configured is not False


def read_auto_memory(workspace: RunWorkspace, env: dict[str, str] | None = None) -> AutoMemorySnapshot:
    root = project_memory_root(workspace)
    if not auto_memory_enabled(workspace, env):
        return AutoMemorySnapshot(enabled=False, root=root)
    try:
        content, truncated = _read_memory_text(workspace, MEMORY_ENTRYPOINT, startup=True)
    except (OSError, MemoryStoreError) as error:
        return AutoMemorySnapshot(enabled=True, root=root, error=str(error))
    return AutoMemorySnapshot(enabled=True, root=root, content=content, truncated=truncated)


def list_memory_files(workspace: RunWorkspace) -> list[MemoryFile]:
    root = project_memory_root(workspace)
    _validate_memory_root(workspace, root, create=False)
    if not root.exists():
        return []
    files: list[MemoryFile] = []
    for path in sorted(root.iterdir(), key=lambda item: item.name.lower()):
        if path.is_symlink():
            raise MemoryStoreError(f"Memory path must not be a symlink: {path.name}")
        if not path.is_file() or not _MEMORY_FILE_PATTERN.fullmatch(path.name):
            continue
        files.append(MemoryFile(path=path.name, bytes=path.stat().st_size))
        if len(files) >= MEMORY_FILE_LIMIT:
            break
    return files


def read_memory_file(workspace: RunWorkspace, path: str = MEMORY_ENTRYPOINT) -> tuple[str, bool]:
    return _read_memory_text(workspace, path, startup=False)


def write_memory_file(
    workspace: RunWorkspace,
    path: str,
    content: str,
    *,
    mode: str = "replace",
) -> MemoryWriteResult:
    name = _validate_memory_name(path)
    if mode not in {"replace", "append"}:
        raise MemoryStoreError("Memory write mode must be replace or append.")
    encoded = content.encode("utf-8")
    if len(encoded) > MEMORY_WRITE_MAX_BYTES:
        raise MemoryStoreError(f"Memory write content exceeds {MEMORY_WRITE_MAX_BYTES} bytes.")
    redacted_content = redact_sensitive_text(content)
    redacted = redacted_content != content
    root = project_memory_root(workspace)
    with _MEMORY_LOCK:
        _validate_memory_root(workspace, root, create=True)
        target = root / name
        _validate_memory_target(target)
        existing = ""
        if mode == "append" and target.exists():
            existing, _ = _read_memory_text(workspace, name, startup=False)
        updated = existing + redacted_content
        updated_bytes = len(updated.encode("utf-8"))
        if updated_bytes > MEMORY_FILE_MAX_BYTES:
            raise MemoryStoreError(f"Memory file exceeds {MEMORY_FILE_MAX_BYTES} bytes.")
        temporary = root / f".{name}.{uuid4().hex}.tmp"
        try:
            temporary.write_text(updated, encoding="utf-8")
            temporary.replace(target)
        finally:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
    return MemoryWriteResult(path=name, bytes=updated_bytes, redacted=redacted)


def preview_memory_write(
    workspace: RunWorkspace,
    path: str,
    content: str,
    *,
    mode: str = "replace",
) -> MemoryWritePreview:
    name = _validate_memory_name(path)
    if mode not in {"replace", "append"}:
        raise MemoryStoreError("Memory write mode must be replace or append.")
    if len(content.encode("utf-8")) > MEMORY_WRITE_MAX_BYTES:
        raise MemoryStoreError(f"Memory write content exceeds {MEMORY_WRITE_MAX_BYTES} bytes.")
    root = project_memory_root(workspace)
    current, _ = _read_memory_text(workspace, name, startup=False)
    redacted_content = redact_sensitive_text(content)
    proposed = current + redacted_content if mode == "append" else redacted_content
    proposed_bytes = len(proposed.encode("utf-8"))
    if proposed_bytes > MEMORY_FILE_MAX_BYTES:
        raise MemoryStoreError(f"Memory file exceeds {MEMORY_FILE_MAX_BYTES} bytes.")
    diff = "".join(
        difflib.unified_diff(
            current.splitlines(keepends=True),
            proposed.splitlines(keepends=True),
            fromfile=f"a/{name}",
            tofile=f"b/{name}",
        )
    )
    return MemoryWritePreview(
        path=name,
        current_bytes=len(current.encode("utf-8")),
        proposed_bytes=proposed_bytes,
        redacted=redacted_content != content,
        diff=diff,
    )


def _read_memory_text(workspace: RunWorkspace, path: str, *, startup: bool) -> tuple[str, bool]:
    name = _validate_memory_name(path)
    root = project_memory_root(workspace)
    _validate_memory_root(workspace, root, create=False)
    target = root / name
    _validate_memory_target(target)
    if not target.exists():
        return "", False
    size = target.stat().st_size
    if size > MEMORY_FILE_MAX_BYTES:
        raise MemoryStoreError(f"Memory file exceeds {MEMORY_FILE_MAX_BYTES} bytes: {name}")
    content = target.read_text(encoding="utf-8")
    if not startup:
        return content, False
    lines = content.splitlines(keepends=True)
    line_limited = "".join(lines[:MEMORY_STARTUP_MAX_LINES])
    encoded = line_limited.encode("utf-8")
    byte_limited = encoded[:MEMORY_STARTUP_MAX_BYTES]
    while byte_limited:
        try:
            bounded = byte_limited.decode("utf-8")
            break
        except UnicodeDecodeError:
            byte_limited = byte_limited[:-1]
    else:
        bounded = ""
    truncated = len(lines) > MEMORY_STARTUP_MAX_LINES or len(encoded) > MEMORY_STARTUP_MAX_BYTES
    return bounded, truncated


def _shared_project_root(root: Path) -> Path:
    result = run_readonly_git(root, ["rev-parse", "--path-format=absolute", "--git-common-dir"])
    if not result.ok:
        return root.resolve()
    common_dir = Path(result.stdout.strip()).resolve()
    if common_dir.name != ".git" or not common_dir.parent.is_dir():
        return root.resolve()
    return common_dir.parent


def _validate_memory_name(path: str) -> str:
    if not isinstance(path, str) or not _MEMORY_FILE_PATTERN.fullmatch(path):
        raise MemoryStoreError("Memory path must be one Markdown filename such as MEMORY.md or debugging.md.")
    return path


def _validate_memory_namespace(name: str) -> str:
    if not isinstance(name, str) or not _MEMORY_NAMESPACE_PATTERN.fullmatch(name):
        raise MemoryStoreError("Agent memory namespace is invalid.")
    return name


def _validate_memory_root(workspace: RunWorkspace, root: Path, *, create: bool) -> None:
    boundary = _shared_project_root(workspace.root)
    try:
        relative = root.relative_to(boundary)
    except ValueError as error:
        raise MemoryStoreError("Memory root must stay inside the current project.") from error
    current = boundary
    paths: list[Path] = []
    for part in relative.parts:
        current = current / part
        paths.append(current)
    for path in paths:
        if path.is_symlink():
            raise MemoryStoreError(f"Memory path component must not be a symlink: {path}")
        if path.exists() and not path.is_dir():
            raise MemoryStoreError(f"Memory path component must be a directory: {path}")
    if create:
        root.mkdir(parents=True, exist_ok=True)
        for path in paths:
            if path.is_symlink() or not path.is_dir():
                raise MemoryStoreError(f"Memory path component must be a regular directory: {path}")


def _validate_memory_target(path: Path) -> None:
    if path.is_symlink():
        raise MemoryStoreError(f"Memory file must not be a symlink: {path.name}")
    if path.exists() and not path.is_file():
        raise MemoryStoreError(f"Memory path must be a regular file: {path.name}")


__all__ = [
    "AutoMemorySnapshot",
    "MemoryFile",
    "MemoryStoreError",
    "MemoryWriteResult",
    "MemoryWritePreview",
    "AGENT_MEMORY_SCOPES",
    "auto_memory_enabled",
    "list_memory_files",
    "project_memory_root",
    "preview_memory_write",
    "read_auto_memory",
    "read_memory_file",
    "write_memory_file",
    "with_agent_memory",
]
