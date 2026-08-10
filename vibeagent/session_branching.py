from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from .agent_runtime_utils import append_session_event
from .goal_state import GoalStateError, read_session_goal, write_goal
from .scheduled_task_store import inherit_schedule_store
from .session_additional_directories import (
    merge_additional_directories,
    record_session_additional_directories,
    restore_session_additional_directories,
)
from .session_id import is_valid_session_id
from .session_store import list_sessions, read_session_events
from .session_tasks import inherit_task_store
from .workspace_core import RunWorkspace, create_run_workspace


MAX_BRANCH_NAME_CHARS = 80
MAX_BRANCH_DEPTH = 20
SESSION_BRANCH_EVENT = "session_branched"
RESERVED_BRANCH_NAMES = frozenset({"latest", "off", "clear", "none"})


@dataclass(frozen=True)
class SessionBranchInfo:
    run_id: str
    source_run_id: str
    name: str | None = None


@dataclass(frozen=True)
class CreatedSessionBranch:
    workspace: RunWorkspace
    source_run_id: str
    name: str | None
    tasks_inherited: bool
    schedules_inherited: int
    goal_inherited: bool
    warnings: tuple[str, ...] = ()

    @property
    def text(self) -> str:
        label = f" ({self.name})" if self.name else ""
        lines = [
            f"Created session branch{label}: {self.workspace.run_id}",
            f"  sourceSession: {self.source_run_id}",
        ]
        if self.warnings:
            lines.append("  warnings: " + "; ".join(self.warnings))
        return "\n".join(lines)


def create_session_branch(
    project_root: Path,
    source_run_id: str,
    *,
    name: str | None = None,
    additional_directories: tuple[Path, ...] = (),
    workspace: RunWorkspace | None = None,
) -> CreatedSessionBranch:
    root = project_root.resolve()
    _require_source_session(root, source_run_id)
    restored_directories = restore_session_additional_directories(root, source_run_id)
    merged_directories = merge_additional_directories(
        root,
        additional_directories,
        restored_directories.directories,
    )
    normalized_name = normalize_branch_name(name)
    if normalized_name is not None:
        existing = find_named_session(root, normalized_name)
        if existing is not None:
            raise ValueError(f"Session branch name is already in use: {normalized_name} ({existing})")

    target = workspace or create_run_workspace(root, additional_roots=merged_directories)
    if target.root != root:
        raise ValueError("Session branch workspace must use the same project root as its source.")
    if target.run_id == source_run_id:
        raise ValueError("Session branch must use a new session id.")
    target = replace(
        target,
        additional_roots=merge_additional_directories(
            root,
            target.additional_roots,
            merged_directories,
        ),
    )
    try:
        target_entries = tuple(target.session_dir.iterdir())
    except OSError as error:
        raise ValueError(f"Cannot inspect session branch target {target.run_id}: {error}") from error
    if target_entries:
        raise ValueError(f"Session branch target is not empty: {target.run_id}")

    append_session_event(
        target.session_dir,
        SESSION_BRANCH_EVENT,
        {
            "source_run_id": source_run_id,
            "name": normalized_name,
        },
    )
    tasks_inherited, task_error = inherit_task_store(target, source_run_id)
    schedules_inherited, schedule_error = inherit_schedule_store(target, source_run_id)
    goal_inherited = False
    goal_error: str | None = None
    try:
        goal = read_session_goal(root, source_run_id)
        if goal is not None:
            write_goal(target, goal)
            goal_inherited = True
    except (OSError, GoalStateError, ValueError) as error:
        goal_error = str(error)
    record_session_additional_directories(root, target.run_id, target.additional_roots)

    warnings = (
        tuple(f"working directories: {warning}" for warning in restored_directories.warnings)
        + tuple(
            f"{label}: {error}"
            for label, error in (
                ("tasks", task_error),
                ("scheduled tasks", schedule_error),
                ("goal", goal_error),
            )
            if error
        )
    )
    append_session_event(
        target.session_dir,
        "session_branch_state_restored",
        {
            "source_run_id": source_run_id,
            "tasks_inherited": tasks_inherited,
            "schedules_inherited": schedules_inherited,
            "goal_inherited": goal_inherited,
            "warnings": list(warnings),
        },
    )
    return CreatedSessionBranch(
        workspace=target,
        source_run_id=source_run_id,
        name=normalized_name,
        tasks_inherited=tasks_inherited,
        schedules_inherited=schedules_inherited,
        goal_inherited=goal_inherited,
        warnings=warnings,
    )


def read_session_branch_info(project_root: Path, run_id: str) -> SessionBranchInfo | None:
    for event in read_session_events(project_root, run_id):
        if event.malformed or event.type != SESSION_BRANCH_EVENT:
            continue
        source = event.payload.get("source_run_id")
        name = event.payload.get("name")
        if not is_valid_session_id(source) or (name is not None and not isinstance(name, str)):
            raise ValueError(f"Session {run_id} has malformed branch metadata.")
        try:
            normalized_name = normalize_branch_name(name)
        except ValueError as error:
            raise ValueError(f"Session {run_id} has malformed branch metadata.") from error
        if name is not None and normalized_name != name:
            raise ValueError(f"Session {run_id} has malformed branch metadata.")
        return SessionBranchInfo(run_id, source, normalized_name)
    return None


def unstarted_branch_lineage(project_root: Path, run_id: str) -> tuple[tuple[str, ...], str]:
    lineage: list[str] = []
    current = run_id
    seen: set[str] = set()
    for _ in range(MAX_BRANCH_DEPTH):
        if current in seen:
            raise ValueError(f"Session branch lineage contains a cycle at {current}.")
        seen.add(current)
        events = read_session_events(project_root, current)
        if any(not event.malformed and event.type == "task" for event in events):
            return tuple(lineage), current
        info = read_session_branch_info(project_root, current)
        if info is None:
            return tuple(lineage), current
        lineage.append(current)
        current = info.source_run_id
    raise ValueError(f"Session branch lineage exceeds {MAX_BRANCH_DEPTH} levels.")


def resolve_session_reference(project_root: Path, value: str) -> str:
    root = project_root.resolve()
    direct = root / ".vibeagent" / "sessions" / value
    if is_valid_session_id(value) and direct.is_dir() and not direct.is_symlink():
        return value
    matches: list[str] = []
    for info in list_sessions(root, limit=10_000):
        try:
            branch = read_session_branch_info(root, info.run_id)
        except ValueError:
            continue
        if branch is not None and branch.name == value:
            matches.append(info.run_id)
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ValueError(f"Session branch name is ambiguous: {value}")
    return value


def find_named_session(project_root: Path, name: str) -> str | None:
    resolved = resolve_session_reference(project_root, name)
    return resolved if resolved != name or (project_root / ".vibeagent" / "sessions" / name).is_dir() else None


def normalize_branch_name(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) > MAX_BRANCH_NAME_CHARS:
        raise ValueError(f"Session branch name must not exceed {MAX_BRANCH_NAME_CHARS} characters.")
    if normalized.lower() in RESERVED_BRANCH_NAMES:
        raise ValueError(f"Session branch name is reserved: {normalized}")
    if any(ord(character) < 32 or ord(character) == 127 for character in normalized):
        raise ValueError("Session branch name must not contain control characters.")
    return normalized


def _require_source_session(project_root: Path, run_id: str) -> None:
    if not is_valid_session_id(run_id):
        raise ValueError(f"Invalid source session id for branch: {run_id}")
    events = read_session_events(project_root, run_id)
    if not any(not event.malformed for event in events):
        raise ValueError(f"Session not found or empty: {run_id}")


__all__ = [
    "CreatedSessionBranch",
    "MAX_BRANCH_DEPTH",
    "MAX_BRANCH_NAME_CHARS",
    "RESERVED_BRANCH_NAMES",
    "SessionBranchInfo",
    "create_session_branch",
    "find_named_session",
    "normalize_branch_name",
    "read_session_branch_info",
    "resolve_session_reference",
    "unstarted_branch_lineage",
]
