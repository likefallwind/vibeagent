from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import re
from uuid import uuid4


@dataclass(frozen=True)
class RunWorkspace:
    root: Path
    run_id: str
    session_dir: Path
    project_config_trusted: bool = False
    mcp_config_paths: tuple[Path, ...] = ()
    strict_mcp_config: bool = False


@dataclass(frozen=True)
class GitCommandResult:
    ok: bool
    stdout: str
    stderr: str
    exit_code: int | None


PROJECT_INSTRUCTION_FILE_NAMES = {"AGENTS.md", "CLAUDE.md"}
PROJECT_INSTRUCTION_CONTENT_LIMIT = 50_000
PROJECT_TODO_MARKERS = ("TODO", "FIXME", "HACK", "XXX", "BUG")
PROJECT_TODO_PATTERN = re.compile(
    r"^\s*(?:(?:#|//|/\*+|\*|<!--|;|--|-)\s*)?\b(TODO|FIXME|HACK|XXX|BUG)\b\s*:?\s*(.*)",
    re.IGNORECASE,
)
GIT_UNMERGED_STATUS_CODES = {"DD", "AU", "UD", "UA", "DU", "AA", "UU"}
GIT_CONFLICT_MARKERS = ("<<<<<<<", "=======", ">>>>>>>")
TEST_FILE_SUFFIXES = (".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs")
JS_TEST_SUFFIXES = (".test", ".spec")


def create_run_workspace(
    base_dir: str | Path | None = None,
    run_id: str | None = None,
    mcp_config_paths: tuple[Path, ...] = (),
    strict_mcp_config: bool = False,
) -> RunWorkspace:
    # Project mode: work in the caller's directory and store task logs under .vibeagent/sessions/.
    base = Path(base_dir) if base_dir is not None else Path.cwd()
    project_root = base.resolve()
    current_run_id = run_id or make_run_id()
    if not current_run_id or Path(current_run_id).name != current_run_id:
        raise ValueError(f"Invalid session id: {current_run_id}")
    runtime_dir = project_root / ".vibeagent"
    sessions_root = runtime_dir / "sessions"
    session_dir = sessions_root / current_run_id
    for label, path in (
        ("Runtime path", runtime_dir),
        ("Session root path", sessions_root),
        ("Session path", session_dir),
    ):
        if path.is_symlink():
            raise ValueError(f"{label} is not a regular directory: {path.relative_to(project_root).as_posix()}")
        if path.exists() and not path.is_dir():
            raise ValueError(f"{label} is not a directory: {path.relative_to(project_root).as_posix()}")
    session_dir.mkdir(parents=True, exist_ok=True)
    for label, path in (
        ("Runtime path", runtime_dir),
        ("Session root path", sessions_root),
        ("Session path", session_dir),
    ):
        if path.is_symlink() or not path.is_dir():
            raise ValueError(f"{label} is not a regular directory: {path.relative_to(project_root).as_posix()}")
    from .project_trust import is_project_permissions_trusted

    return RunWorkspace(
        root=project_root,
        run_id=current_run_id,
        session_dir=session_dir,
        project_config_trusted=is_project_permissions_trusted(project_root),
        mcp_config_paths=tuple(_absolute_path(project_root, path) for path in mcp_config_paths),
        strict_mcp_config=strict_mcp_config,
    )


def create_local_workspace(
    root: str | Path,
    run_id: str,
    mcp_config_paths: tuple[Path, ...] = (),
    strict_mcp_config: bool = False,
) -> RunWorkspace:
    from .project_trust import is_project_permissions_trusted

    project_root = Path(root).resolve()
    return RunWorkspace(
        root=project_root,
        run_id=run_id,
        session_dir=project_root / ".vibeagent" / "sessions" / run_id,
        project_config_trusted=is_project_permissions_trusted(project_root),
        mcp_config_paths=tuple(_absolute_path(project_root, path) for path in mcp_config_paths),
        strict_mcp_config=strict_mcp_config,
    )


def make_run_id() -> str:
    # Timestamp+uuid-based ID keeps IDs unique without shared state.
    timestamp = datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    safe_timestamp = timestamp.replace(":", "-").replace(".", "-")
    return f"{safe_timestamp}-{uuid4().hex[:8]}"


def _absolute_path(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path
