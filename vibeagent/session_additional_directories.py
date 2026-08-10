from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .agent_runtime_utils import append_session_event
from .cli_additional_directories import MAX_ADDITIONAL_DIRECTORIES
from .session_store import read_session_events
from .workspace_core import create_local_workspace, normalize_additional_roots


SESSION_DIRECTORY_EVENT = "additional_directories_updated"


@dataclass(frozen=True)
class RestoredAdditionalDirectories:
    directories: tuple[Path, ...] = ()
    warnings: tuple[str, ...] = ()

    @property
    def message(self) -> str | None:
        if not self.warnings:
            return None
        return "Additional directory restore warning: " + "; ".join(self.warnings)


def restore_session_additional_directories(
    project_root: Path,
    run_id: str | None,
) -> RestoredAdditionalDirectories:
    if run_id is None:
        return RestoredAdditionalDirectories()
    try:
        events = read_session_events(project_root, run_id)
    except ValueError as error:
        return RestoredAdditionalDirectories(warnings=(str(error),))

    stored: object | None = None
    found = False
    for event in reversed(events):
        if event.malformed or event.type not in {"task", SESSION_DIRECTORY_EVENT}:
            continue
        if "additional_directories" not in event.payload:
            continue
        stored = event.payload["additional_directories"]
        found = True
        break
    if not found:
        return RestoredAdditionalDirectories()
    if not isinstance(stored, list) or any(not isinstance(value, str) for value in stored):
        return RestoredAdditionalDirectories(warnings=("stored directory list is malformed",))
    if len(stored) > MAX_ADDITIONAL_DIRECTORIES:
        return RestoredAdditionalDirectories(
            warnings=(f"stored directory list exceeds the {MAX_ADDITIONAL_DIRECTORIES}-directory limit",)
        )

    restored: tuple[Path, ...] = ()
    warnings: list[str] = []
    for value in stored:
        candidate = Path(value).expanduser()
        if not candidate.is_absolute():
            warnings.append(f"ignored non-absolute stored path: {value}")
            continue
        try:
            restored = normalize_additional_roots(project_root.resolve(), (*restored, candidate))
        except (OSError, ValueError) as error:
            warnings.append(f"ignored unavailable stored path {value}: {error}")
    return RestoredAdditionalDirectories(restored, tuple(warnings))


def merge_additional_directories(
    project_root: Path,
    current: tuple[Path, ...],
    restored: tuple[Path, ...],
) -> tuple[Path, ...]:
    try:
        merged = normalize_additional_roots(project_root.resolve(), (*current, *restored))
    except OSError as error:
        raise ValueError(f"Cannot restore additional working directories: {error}") from error
    if len(merged) > MAX_ADDITIONAL_DIRECTORIES:
        raise ValueError(
            f"Combined working directories exceed the {MAX_ADDITIONAL_DIRECTORIES}-directory session limit."
        )
    return merged


def record_session_additional_directories(
    project_root: Path,
    run_id: str | None,
    directories: tuple[Path, ...],
) -> None:
    if run_id is None:
        return
    workspace = create_local_workspace(project_root, run_id, additional_roots=directories)
    append_session_event(
        workspace.session_dir,
        SESSION_DIRECTORY_EVENT,
        {"additional_directories": [str(path) for path in workspace.additional_roots]},
    )


__all__ = [
    "RestoredAdditionalDirectories",
    "merge_additional_directories",
    "record_session_additional_directories",
    "restore_session_additional_directories",
]
