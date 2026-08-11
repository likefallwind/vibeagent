from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
import stat
import subprocess
from uuid import uuid4

from .background_agent_changes import read_background_agent_changes
from .background_agent_lock import background_agent_transition_lock
from .background_agent_store import get_background_agent
from .workspace_git_utils import combine_git_output, run_readonly_git
from .workspace_resolve import resolve_mutation_path


MAX_INTEGRATION_FILE_BYTES = 25 * 1024 * 1024
MAX_INTEGRATION_TOTAL_BYTES = 100 * 1024 * 1024
TERMINAL_AGENT_STATUSES = {"completed", "failed", "stopped", "lost"}


@dataclass(frozen=True)
class BackgroundAgentIntegration:
    agent_id: str
    snapshot_id: str
    applied_files: tuple[str, ...]
    skipped_files: tuple[str, ...]


@dataclass(frozen=True)
class _FileState:
    data: bytes
    executable: bool
    restore_mode: int = field(compare=False)


@dataclass(frozen=True)
class _Operation:
    path: str
    target: Path
    before: _FileState | None
    after: _FileState | None


def integrate_background_agent_changes(
    project_root: Path,
    agent_id: str,
    *,
    expected_snapshot_id: str,
) -> BackgroundAgentIntegration:
    if (
        len(expected_snapshot_id) != 64
        or any(character not in "0123456789abcdef" for character in expected_snapshot_id)
    ):
        raise ValueError("Background agent integration snapshot ID is invalid.")
    root = project_root.resolve()
    with background_agent_transition_lock(root, agent_id):
        view = get_background_agent(root, agent_id)
        if view is None:
            raise ValueError(f"Background agent not found: {agent_id}")
        if view.status not in TERMINAL_AGENT_STATUSES:
            raise ValueError(f"Background agent must stop before applying changes: {agent_id}")
        changes = read_background_agent_changes(root, agent_id)
        if not changes.isolated:
            raise ValueError(f"Background agent is not using an isolated worktree: {agent_id}")
        if changes.snapshot_id != expected_snapshot_id:
            raise ValueError(f"Background agent change snapshot is stale: {agent_id}")
        if not changes.files:
            raise ValueError(f"Background agent has no reviewable changes: {agent_id}")
        if changes.omitted_files:
            raise ValueError(
                "Background agent has too many changes to apply as one reviewed snapshot."
            )

        project_top = _git_path(root, ["rev-parse", "--show-toplevel"], "project worktree")
        relative_root = root.relative_to(project_top)
        operations: list[_Operation] = []
        skipped: list[str] = []
        conflicts: list[str] = []
        total_bytes = 0
        for changed in changes.files:
            path = changed.path
            repository_path = (relative_root / Path(path)).as_posix()
            base = _read_base_state(changes.session_root, changes.base_commit, repository_path, path)
            agent = _read_worktree_state(changes.session_root, path)
            if _state_fingerprint(changes.session_root, agent, path) != changed.fingerprint:
                raise ValueError(f"Background agent change snapshot is stale: {agent_id}")
            target = resolve_mutation_path(root, path)
            current = _read_worktree_state(root, path)
            total_bytes += sum(len(item.data) for item in (base, agent, current) if item is not None)
            if total_bytes > MAX_INTEGRATION_TOTAL_BYTES:
                raise ValueError("Background agent integration exceeds the 100 MiB total limit.")
            if current == agent:
                skipped.append(path)
            elif current != base:
                conflicts.append(path)
            else:
                operations.append(_Operation(path, target, current, agent))
        if conflicts:
            labels = ", ".join(conflicts[:10])
            suffix = f" (+{len(conflicts) - 10} more)" if len(conflicts) > 10 else ""
            raise ValueError(f"Background agent changes conflict with the main worktree: {labels}{suffix}")

        created_directories: list[Path] = []
        applied_operations: list[_Operation] = []
        try:
            for operation in sorted(
                (item for item in operations if item.after is None),
                key=lambda item: len(Path(item.path).parts),
                reverse=True,
            ):
                _apply_operation(root, operation, created_directories)
                applied_operations.append(operation)
            for operation in sorted(
                (item for item in operations if item.after is not None),
                key=lambda item: len(Path(item.path).parts),
            ):
                _apply_operation(root, operation, created_directories)
                applied_operations.append(operation)
            for operation in operations:
                if _read_worktree_state(root, operation.path) != operation.after:
                    raise ValueError(f"Applied background agent file failed verification: {operation.path}")
        except (OSError, ValueError) as error:
            rollback_errors = _rollback_operations(root, applied_operations, created_directories)
            detail = f" Rollback errors: {'; '.join(rollback_errors)}" if rollback_errors else ""
            raise ValueError(f"Could not apply background agent changes: {error}.{detail}") from error

        return BackgroundAgentIntegration(
            agent_id=agent_id,
            snapshot_id=changes.snapshot_id,
            applied_files=tuple(item.path for item in operations),
            skipped_files=tuple(skipped),
        )


def _apply_operation(root: Path, operation: _Operation, created_directories: list[Path]) -> None:
    if _read_worktree_state(root, operation.path) != operation.before:
        raise ValueError(f"Main worktree changed while applying: {operation.path}")
    if operation.after is None:
        if operation.target.is_symlink() or not operation.target.is_file():
            raise ValueError(f"Main worktree file is not safe to delete: {operation.path}")
        operation.target.unlink()
        return
    _ensure_parent_directories(root, operation.target.parent, created_directories)
    _write_file_atomic(operation.target, operation.after)


def _rollback_operations(
    root: Path,
    operations: list[_Operation],
    created_directories: list[Path],
) -> list[str]:
    errors: list[str] = []
    removed: list[_Operation] = []
    for operation in sorted(operations, key=lambda item: len(Path(item.path).parts), reverse=True):
        try:
            target = resolve_mutation_path(root, operation.path)
            if _read_worktree_state(root, operation.path) != operation.after:
                raise ValueError("target changed after integration")
            if target.is_symlink():
                raise ValueError("target became a symlink")
            if target.is_file():
                target.unlink()
            elif target.exists() and not target.is_dir():
                raise ValueError("target became an unsupported file type")
            removed.append(operation)
        except (OSError, ValueError) as error:
            errors.append(f"{operation.path}: {error}")
    for directory in sorted(set(created_directories), key=lambda item: len(item.parts), reverse=True):
        try:
            directory.rmdir()
        except OSError:
            pass
    for operation in sorted(
        (item for item in removed if item.before is not None),
        key=lambda item: len(Path(item.path).parts),
    ):
        try:
            _ensure_parent_directories(root, operation.target.parent, [])
            assert operation.before is not None
            _write_file_atomic(operation.target, operation.before, preserve_mode=True)
        except (OSError, ValueError) as error:
            errors.append(f"{operation.path}: {error}")
    return errors


def _ensure_parent_directories(root: Path, parent: Path, created: list[Path]) -> None:
    relative = parent.relative_to(root)
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"Integration path uses a symbolic link: {current.relative_to(root)}")
        if current.exists():
            if not current.is_dir():
                raise ValueError(f"Integration parent is not a directory: {current.relative_to(root)}")
            continue
        current.mkdir()
        created.append(current)


def _write_file_atomic(path: Path, state: _FileState, *, preserve_mode: bool = False) -> None:
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    descriptor: int | None = None
    try:
        mode = state.restore_mode if preserve_mode else (0o755 if state.executable else 0o644)
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = None
            handle.write(state.data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)


def _read_worktree_state(root: Path, path: str) -> _FileState | None:
    target = resolve_mutation_path(root, path)
    try:
        metadata = target.lstat()
    except FileNotFoundError:
        return None
    except NotADirectoryError:
        return None
    except OSError as error:
        raise ValueError(f"Could not inspect integration path: {path}") from error
    if not stat.S_ISREG(metadata.st_mode):
        raise ValueError(f"Integration supports regular files only: {path}")
    data = _read_bounded_file(target, path, metadata.st_size)
    return _FileState(
        data=data,
        executable=bool(metadata.st_mode & stat.S_IXUSR),
        restore_mode=stat.S_IMODE(metadata.st_mode),
    )


def _read_base_state(root: Path, commit: str, repository_path: str, display_path: str) -> _FileState | None:
    literal_pathspec = f":(literal){repository_path}"
    tree = run_readonly_git(root, ["ls-tree", "-z", commit, "--", literal_pathspec])
    if not tree.ok:
        raise ValueError(combine_git_output(tree) or f"Could not inspect base file: {display_path}")
    if not tree.stdout:
        return None
    entry, separator, listed_path = tree.stdout.rstrip("\0").partition("\t")
    parts = entry.split()
    if not separator or listed_path != repository_path or len(parts) != 3:
        raise ValueError(f"Git returned invalid base metadata for: {display_path}")
    mode, kind, object_id = parts
    if kind != "blob" or mode not in {"100644", "100755"}:
        raise ValueError(f"Integration supports regular Git files only: {display_path}")
    data = _read_git_object(root, object_id, display_path)
    return _FileState(data=data, executable=mode == "100755", restore_mode=int(mode[-3:], 8))


def _read_git_object(root: Path, object_id: str, display_path: str) -> bytes:
    size = run_readonly_git(root, ["cat-file", "-s", object_id])
    try:
        length = int(size.stdout.strip()) if size.ok else -1
    except ValueError:
        length = -1
    if length < 0:
        raise ValueError(combine_git_output(size) or f"Could not read base file: {display_path}")
    if length > MAX_INTEGRATION_FILE_BYTES:
        raise ValueError(f"Background agent file exceeds 25 MiB: {display_path}")
    try:
        result = subprocess.run(
            ["git", "cat-file", "blob", object_id],
            cwd=root,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as error:
        raise ValueError(f"Could not read base file: {display_path}") from error
    if result.returncode != 0 or len(result.stdout) != length:
        raise ValueError(f"Could not read base file: {display_path}")
    return result.stdout


def _state_fingerprint(root: Path, state: _FileState | None, display_path: str) -> str:
    if state is None:
        return "missing"
    try:
        result = subprocess.run(
            ["git", "hash-object", "--stdin"],
            cwd=root,
            input=state.data,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as error:
        raise ValueError(f"Could not fingerprint integration file: {display_path}") from error
    value = result.stdout.decode("ascii", errors="replace").strip()
    if (
        result.returncode != 0
        or len(value) not in {40, 64}
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"Could not fingerprint integration file: {display_path}")
    executable = "x" if state.executable else "-"
    return f"file:{executable}:{value}"


def _read_bounded_file(path: Path, display_path: str, size: int) -> bytes:
    if size > MAX_INTEGRATION_FILE_BYTES:
        raise ValueError(f"Background agent file exceeds 25 MiB: {display_path}")
    flags = os.O_RDONLY | (os.O_NOFOLLOW if hasattr(os, "O_NOFOLLOW") else 0)
    try:
        descriptor = os.open(path, flags)
        with os.fdopen(descriptor, "rb") as handle:
            metadata = os.fstat(handle.fileno())
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > MAX_INTEGRATION_FILE_BYTES:
                raise ValueError(f"Integration file is not a bounded regular file: {display_path}")
            data = handle.read(MAX_INTEGRATION_FILE_BYTES + 1)
    except ValueError:
        raise
    except OSError as error:
        raise ValueError(f"Could not read integration file: {display_path}") from error
    if len(data) > MAX_INTEGRATION_FILE_BYTES:
        raise ValueError(f"Background agent file exceeds 25 MiB: {display_path}")
    return data


def _git_path(root: Path, args: list[str], label: str) -> Path:
    result = run_readonly_git(root, args)
    value = result.stdout.strip()
    path = Path(value)
    if not result.ok or not value or not path.is_absolute() or path.is_symlink() or not path.is_dir():
        raise ValueError(combine_git_output(result) or f"Could not resolve {label}.")
    return path.resolve()


__all__ = ["BackgroundAgentIntegration", "integrate_background_agent_changes"]
