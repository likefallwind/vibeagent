from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import stat
import subprocess

from .background_agent_config import read_background_agent_config
from .workspace_git_utils import combine_git_output, run_readonly_git, should_ignore_git_path


MAX_BACKGROUND_CHANGE_FILES = 200
MAX_BACKGROUND_CHANGE_PATH_CHARS = 1_000
MAX_BACKGROUND_CHANGE_GIT_OUTPUT_CHARS = 512_000
MAX_BACKGROUND_CHANGE_CONTENT_BYTES = 1_048_576
PRIVATE_BACKGROUND_CHANGE_ROOTS = {".claude"}


@dataclass(frozen=True)
class BackgroundAgentChangedFile:
    path: str
    committed: bool
    staged: bool
    unstaged: bool
    untracked: bool
    deleted: bool
    fingerprint: str


@dataclass(frozen=True)
class BackgroundAgentChanges:
    agent_id: str
    session_root: Path
    isolated: bool
    branch: str | None
    base_commit: str
    head_commit: str
    snapshot_id: str
    files: tuple[BackgroundAgentChangedFile, ...]
    omitted_files: int


@dataclass(frozen=True)
class _ChangeContext:
    project_root: Path
    session_root: Path
    project_top: Path
    session_top: Path
    relative_root: Path
    isolated: bool
    branch: str | None
    base_commit: str
    head_commit: str


def read_background_agent_changes(
    project_root: Path,
    agent_id: str,
    *,
    max_files: int = MAX_BACKGROUND_CHANGE_FILES,
) -> BackgroundAgentChanges:
    context = _change_context(project_root, agent_id)
    committed = _changed_paths(
        context.session_root,
        ["diff", "--relative", "--no-renames", "--name-only", "-z", context.base_commit, context.head_commit],
    )
    staged = _changed_paths(
        context.session_root,
        ["diff", "--relative", "--no-renames", "--cached", "--name-only", "-z"],
    )
    unstaged = _changed_paths(
        context.session_root,
        ["diff", "--relative", "--no-renames", "--name-only", "-z"],
    )
    untracked = _changed_paths(
        context.session_root,
        ["ls-files", "--others", "--exclude-standard", "-z"],
    )
    all_paths = sorted(committed | staged | unstaged | untracked)
    visible = [
        path
        for path in all_paths
        if _valid_change_path(path)
        and Path(path).parts[0] not in PRIVATE_BACKGROUND_CHANGE_ROOTS
        and not should_ignore_git_path(context.session_root, path)
    ]
    bounded = max(1, min(max_files, MAX_BACKGROUND_CHANGE_FILES))
    selected = visible[:bounded]
    files = tuple(
        BackgroundAgentChangedFile(
            path=path,
            committed=path in committed,
            staged=path in staged,
            unstaged=path in unstaged,
            untracked=path in untracked,
            deleted=not _regular_current_file(context.session_root, path),
            fingerprint=_current_fingerprint(context.session_root, path),
        )
        for path in selected
    )
    snapshot_id = _change_snapshot(context, files)
    return BackgroundAgentChanges(
        agent_id=agent_id,
        session_root=context.session_root,
        isolated=context.isolated,
        branch=context.branch,
        base_commit=context.base_commit,
        head_commit=context.head_commit,
        snapshot_id=snapshot_id,
        files=files,
        omitted_files=max(0, len(visible) - len(files)),
    )


def read_background_agent_change_content(
    project_root: Path,
    agent_id: str,
    path: str,
    *,
    side: str,
) -> str:
    changes = read_background_agent_changes(project_root, agent_id)
    if side not in {"base", "current"}:
        raise ValueError("Background agent change side must be base or current.")
    if path not in {item.path for item in changes.files}:
        raise ValueError(f"Background agent changed file is unavailable: {path}")
    if side == "current":
        candidate = changes.session_root / Path(path)
        if not candidate.exists():
            return ""
        if candidate.is_symlink() or not candidate.is_file():
            raise ValueError(f"Background agent changed file is not a regular file: {path}")
        payload = _read_regular_file(candidate, path)
        return _decode_content(payload, path)

    context = _change_context(project_root, agent_id)
    repository_path = (context.relative_root / Path(path)).as_posix()
    payload = _read_git_blob(context.session_root, f"{context.base_commit}:{repository_path}")
    return "" if payload is None else _decode_content(payload, path)


def _change_context(project_root: Path, agent_id: str) -> _ChangeContext:
    root = project_root.resolve()
    config = read_background_agent_config(root, agent_id)
    session_root = config.session_root.resolve()
    project_top = _git_path(root, ["rev-parse", "--show-toplevel"], "project worktree")
    session_top = _git_path(session_root, ["rev-parse", "--show-toplevel"], "agent worktree")
    project_common = _git_path(
        root,
        ["rev-parse", "--path-format=absolute", "--git-common-dir"],
        "project git directory",
    )
    session_common = _git_path(
        session_root,
        ["rev-parse", "--path-format=absolute", "--git-common-dir"],
        "agent git directory",
    )
    if project_common != session_common:
        raise ValueError(f"Background agent session is not a linked project worktree: {agent_id}")
    try:
        relative_root = root.relative_to(project_top)
    except ValueError as error:
        raise ValueError(f"Project root is outside its Git worktree: {root}") from error
    expected_session_root = (session_top / relative_root).resolve()
    if session_root != expected_session_root:
        raise ValueError(f"Background agent session root does not match the project scope: {agent_id}")
    project_head = _git_text(root, ["rev-parse", "HEAD"], "project HEAD")
    head_commit = _git_text(session_root, ["rev-parse", "HEAD"], "agent HEAD")
    base_commit = _git_text(
        session_root,
        ["merge-base", project_head, head_commit],
        "agent merge base",
    )
    branch = _git_text(
        session_root,
        ["branch", "--show-current"],
        "agent branch",
        allow_empty=True,
    ) or None
    return _ChangeContext(
        project_root=root,
        session_root=session_root,
        project_top=project_top,
        session_top=session_top,
        relative_root=relative_root,
        isolated=session_top != project_top,
        branch=branch,
        base_commit=base_commit,
        head_commit=head_commit,
    )


def _changed_paths(root: Path, args: list[str]) -> set[str]:
    result = run_readonly_git(
        root,
        args,
        max_output_chars=MAX_BACKGROUND_CHANGE_GIT_OUTPUT_CHARS + 1,
    )
    if not result.ok:
        raise ValueError(combine_git_output(result) or "Could not inspect background agent changes.")
    if result.stdout_truncated or len(result.stdout) > MAX_BACKGROUND_CHANGE_GIT_OUTPUT_CHARS:
        raise ValueError("Background agent change list is too large.")
    return {part for part in result.stdout.split("\0") if part}


def _git_path(root: Path, args: list[str], label: str) -> Path:
    value = _git_text(root, args, label)
    path = Path(value)
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        raise ValueError(f"Invalid {label}: {value}")
    return path.resolve()


def _git_text(root: Path, args: list[str], label: str, *, allow_empty: bool = False) -> str:
    result = run_readonly_git(root, args, max_output_chars=4_001)
    value = result.stdout.strip()
    if (
        not result.ok
        or result.stdout_truncated
        or (not value and not allow_empty)
        or len(value) > 4_000
    ):
        message = combine_git_output(result)
        raise ValueError(message or f"Could not resolve {label}.")
    return value


def _valid_change_path(value: str) -> bool:
    path = Path(value)
    return (
        bool(value)
        and len(value) <= MAX_BACKGROUND_CHANGE_PATH_CHARS
        and not path.is_absolute()
        and ".." not in path.parts
        and not any(ord(character) < 32 or ord(character) == 127 for character in value)
    )


def _regular_current_file(root: Path, path: str) -> bool:
    candidate = root / Path(path)
    return candidate.is_file() and not candidate.is_symlink()


def _change_snapshot(
    context: _ChangeContext,
    files: tuple[BackgroundAgentChangedFile, ...],
) -> str:
    digest = hashlib.sha256()
    digest.update(f"v1\0{context.base_commit}\0{context.head_commit}\0".encode("ascii"))
    for item in files:
        flags = "".join(
            "1" if value else "0"
            for value in (
                item.committed,
                item.staged,
                item.unstaged,
                item.untracked,
                item.deleted,
            )
        )
        digest.update(item.path.encode("utf-8"))
        digest.update(f"\0{flags}\0{item.fingerprint}\0".encode("utf-8"))
    return digest.hexdigest()


def _current_fingerprint(root: Path, path: str) -> str:
    candidate = root / Path(path)
    try:
        metadata = candidate.lstat()
    except FileNotFoundError:
        return "missing"
    except OSError as error:
        raise ValueError(f"Could not inspect background agent changed file: {path}") from error
    if stat.S_ISLNK(metadata.st_mode):
        try:
            target = os.readlink(candidate)
        except OSError as error:
            raise ValueError(f"Could not inspect background agent changed symlink: {path}") from error
        return f"symlink:{hashlib.sha256(os.fsencode(target)).hexdigest()}"
    if not stat.S_ISREG(metadata.st_mode):
        return f"mode:{stat.S_IFMT(metadata.st_mode):o}"
    result = run_readonly_git(
        root,
        ["hash-object", "--no-filters", "--", path],
        max_output_chars=65,
    )
    value = result.stdout.strip()
    if (
        not result.ok
        or result.stdout_truncated
        or len(value) not in {40, 64}
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(combine_git_output(result) or f"Could not fingerprint changed file: {path}")
    executable = "x" if metadata.st_mode & stat.S_IXUSR else "-"
    return f"file:{executable}:{value}"


def _read_git_blob(root: Path, object_spec: str) -> bytes | None:
    size_result = run_readonly_git(root, ["cat-file", "-s", object_spec])
    if not size_result.ok:
        return None
    try:
        size = int(size_result.stdout.strip())
    except ValueError as error:
        raise ValueError("Git returned an invalid background agent blob size.") from error
    if size < 0 or size > MAX_BACKGROUND_CHANGE_CONTENT_BYTES:
        raise ValueError("Background agent base content exceeds 1 MiB.")
    try:
        result = subprocess.run(
            ["git", "show", object_spec],
            cwd=root,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
            check=False,
        )
    except FileNotFoundError as error:
        raise ValueError("git executable was not found.") from error
    except subprocess.TimeoutExpired as error:
        raise ValueError("Reading background agent base content timed out.") from error
    if result.returncode != 0:
        return None
    return result.stdout


def _read_regular_file(path: Path, display_path: str) -> bytes:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor: int | None = None
    try:
        descriptor = os.open(path, flags)
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError(f"Background agent changed file is not a regular file: {display_path}")
        if metadata.st_size > MAX_BACKGROUND_CHANGE_CONTENT_BYTES:
            raise ValueError(f"Background agent changed file exceeds 1 MiB: {display_path}")
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = None
            return handle.read(MAX_BACKGROUND_CHANGE_CONTENT_BYTES + 1)
    except ValueError:
        raise
    except OSError as error:
        raise ValueError(f"Could not read background agent changed file: {display_path}") from error
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _decode_content(payload: bytes, path: str) -> str:
    if len(payload) > MAX_BACKGROUND_CHANGE_CONTENT_BYTES:
        raise ValueError(f"Background agent changed file exceeds 1 MiB: {path}")
    if b"\0" in payload:
        raise ValueError(f"Background agent changed file is binary: {path}")
    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(f"Background agent changed file is not UTF-8 text: {path}") from error


__all__ = [
    "BackgroundAgentChangedFile",
    "BackgroundAgentChanges",
    "read_background_agent_change_content",
    "read_background_agent_changes",
]
