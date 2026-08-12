from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import re
from typing import TYPE_CHECKING
from uuid import uuid4

from .session_id import is_valid_session_id

if TYPE_CHECKING:
    from .dynamic_agent_profiles import DynamicAgentProfile
    from .mcp_config import McpServerConfig


@dataclass(frozen=True)
class RunWorkspace:
    root: Path
    run_id: str
    session_dir: Path
    project_config_trusted: bool = False
    mcp_config_paths: tuple[Path, ...] = ()
    strict_mcp_config: bool = False
    root_history: tuple[Path, ...] = ()
    memory_scope: str | None = None
    memory_namespace: str | None = None
    additional_roots: tuple[Path, ...] = ()
    dynamic_agent_profiles: tuple[DynamicAgentProfile, ...] = ()
    profile_mcp_server_configs: tuple[McpServerConfig, ...] = ()
    maintain_shell_cwd: bool = True
    autocompact_tokens: int | None = None
    append_subagent_system_prompt: str | None = None
    safe_mode: bool = False
    bare_mode: bool = False
    setting_sources: tuple[str, ...] = ("user", "project", "local")
    settings_override_json: str | None = None
    invocation_plugin_dirs: tuple[Path, ...] = ()
    permission_prompt_tool: str | None = None


@dataclass(frozen=True)
class GitCommandResult:
    ok: bool
    stdout: str
    stderr: str
    exit_code: int | None


PROJECT_INSTRUCTION_FILE_NAMES = {"AGENTS.md", "CLAUDE.md", "CLAUDE.local.md"}
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
    additional_roots: tuple[Path, ...] = (),
    safe_mode: bool = False,
    bare_mode: bool = False,
    setting_sources: tuple[str, ...] = ("user", "project", "local"),
    settings_override_json: str | None = None,
    invocation_plugin_dirs: tuple[Path, ...] = (),
    permission_prompt_tool: str | None = None,
) -> RunWorkspace:
    # Project mode: work in the caller's directory and store task logs under .vibeagent/sessions/.
    base = Path(base_dir) if base_dir is not None else Path.cwd()
    project_root = base.resolve()
    current_run_id = run_id or make_run_id()
    if not is_valid_session_id(current_run_id):
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
    validate_session_events_path(session_dir)
    from .project_trust import is_project_permissions_trusted

    return RunWorkspace(
        root=project_root,
        run_id=current_run_id,
        session_dir=session_dir,
        project_config_trusted=is_project_permissions_trusted(project_root),
        mcp_config_paths=tuple(_absolute_path(project_root, path) for path in mcp_config_paths),
        strict_mcp_config=strict_mcp_config,
        additional_roots=normalize_additional_roots(project_root, additional_roots),
        safe_mode=safe_mode,
        bare_mode=bare_mode,
        setting_sources=setting_sources,
        settings_override_json=settings_override_json,
        invocation_plugin_dirs=invocation_plugin_dirs,
        permission_prompt_tool=permission_prompt_tool,
    )


def create_local_workspace(
    root: str | Path,
    run_id: str,
    mcp_config_paths: tuple[Path, ...] = (),
    strict_mcp_config: bool = False,
    additional_roots: tuple[Path, ...] = (),
    safe_mode: bool = False,
    bare_mode: bool = False,
    setting_sources: tuple[str, ...] = ("user", "project", "local"),
    settings_override_json: str | None = None,
    invocation_plugin_dirs: tuple[Path, ...] = (),
    permission_prompt_tool: str | None = None,
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
        additional_roots=normalize_additional_roots(project_root, additional_roots),
        safe_mode=safe_mode,
        bare_mode=bare_mode,
        setting_sources=setting_sources,
        settings_override_json=settings_override_json,
        invocation_plugin_dirs=invocation_plugin_dirs,
        permission_prompt_tool=permission_prompt_tool,
    )


def normalize_additional_roots(project_root: Path, roots: tuple[Path, ...]) -> tuple[Path, ...]:
    normalized: list[Path] = []
    seen = {project_root}
    for root in roots:
        resolved = root.resolve(strict=True)
        if not resolved.is_dir():
            raise ValueError(f"Additional workspace path is not a directory: {root}")
        if resolved in seen or project_root in resolved.parents:
            continue
        seen.add(resolved)
        normalized.append(resolved)
    return tuple(normalized)


def make_run_id() -> str:
    # Timestamp+uuid-based ID keeps IDs unique without shared state.
    timestamp = datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    safe_timestamp = timestamp.replace(":", "-").replace(".", "-")
    return f"{safe_timestamp}-{uuid4().hex[:8]}"


def validate_session_events_path(session_dir: Path) -> Path:
    events_path = session_dir / "events.jsonl"
    if events_path.is_symlink() or (events_path.exists() and not events_path.is_file()):
        raise ValueError(f"Session events path is not a regular file: {events_path}")
    return events_path


def _absolute_path(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path
