from __future__ import annotations

import json
import os
import stat
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .workspace_metadata_files import read_regular_file_bytes


TRUST_FILE_ENV = "VIBEAGENT_TRUST_FILE"
MAX_TRUST_FILE_BYTES = 256_000
MAX_TRUSTED_PROJECTS = 1_000


@dataclass(frozen=True)
class ProjectTrustStore:
    projects: dict[str, str]
    path: Path
    error: str | None = None


def get_project_trust_report(root: str | Path, trust_file: str | Path | None = None) -> dict[str, object]:
    project = _canonical_project(root)
    store = read_project_trust_store(trust_file)
    trusted_at = store.projects.get(project)
    return {
        "ok": store.error is None,
        "project": project,
        "trusted": trusted_at is not None and store.error is None,
        "trustedAt": trusted_at,
        "storePath": store.path.as_posix(),
        "storeError": store.error,
        "trustedProjects": len(store.projects),
        "message": (
            f"Project permission allow rules are trusted for {project}."
            if trusted_at is not None and store.error is None
            else f"Project permission allow rules are not trusted for {project}."
        ),
    }


def format_project_trust_report_text(report: dict[str, object]) -> str:
    lines = [
        "Project permission trust:",
        f"  project: {report.get('project')}",
        f"  trusted: {'yes' if report.get('trusted') else 'no'}",
        f"  store: {report.get('storePath')}",
    ]
    trusted_at = report.get("trustedAt")
    if isinstance(trusted_at, str):
        lines.append(f"  trustedAt: {trusted_at}")
    error = report.get("storeError")
    if isinstance(error, str) and error:
        lines.append(f"  error: {error}")
    return "\n".join(lines)


def is_project_permissions_trusted(root: str | Path, trust_file: str | Path | None = None) -> bool:
    report = get_project_trust_report(root, trust_file)
    return bool(report["trusted"])


def trust_project_permissions(root: str | Path, trust_file: str | Path | None = None) -> dict[str, object]:
    project = _canonical_project(root)
    store = read_project_trust_store(trust_file)
    if store.error is not None:
        return _mutation_error_report(project, store, "trust", store.error)
    projects = dict(store.projects)
    already_trusted = project in projects
    projects[project] = projects.get(project) or datetime.now(UTC).isoformat(timespec="seconds")
    error = _write_project_trust_store(store.path, projects)
    if error is not None:
        return _mutation_error_report(project, store, "trust", error)
    return {
        **get_project_trust_report(project, store.path),
        "changed": not already_trusted,
        "action": "trust",
        "message": (
            "Project permission trust was already recorded."
            if already_trusted
            else "Project permission trust recorded."
        ),
    }


def untrust_project_permissions(root: str | Path, trust_file: str | Path | None = None) -> dict[str, object]:
    project = _canonical_project(root)
    store = read_project_trust_store(trust_file)
    if store.error is not None:
        return _mutation_error_report(project, store, "untrust", store.error)
    projects = dict(store.projects)
    existed = projects.pop(project, None) is not None
    if existed:
        error = _write_project_trust_store(store.path, projects)
        if error is not None:
            return _mutation_error_report(project, store, "untrust", error)
    report = get_project_trust_report(project, store.path)
    return {
        **report,
        "changed": existed,
        "action": "untrust",
        "message": "Project permission trust removed." if existed else "Project permission trust was not recorded.",
    }


def read_project_trust_store(trust_file: str | Path | None = None) -> ProjectTrustStore:
    path = _trust_store_path(trust_file)
    try:
        _validate_store_path(path, require_parent=False)
        if not path.exists():
            return ProjectTrustStore(projects={}, path=path)
        raw = read_regular_file_bytes(path, max_bytes=MAX_TRUST_FILE_BYTES, label=path.as_posix())
        payload = json.loads(raw.decode("utf-8"))
        projects = _parse_projects(payload)
        return ProjectTrustStore(projects=projects, path=path)
    except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError) as error:
        return ProjectTrustStore(projects={}, path=path, error=str(error))


def _trust_store_path(trust_file: str | Path | None) -> Path:
    if trust_file is not None:
        return Path(trust_file).expanduser().absolute()
    override = os.environ.get(TRUST_FILE_ENV)
    if override:
        return Path(override).expanduser().absolute()
    return (Path.home() / ".vibeagent/trusted-projects.json").absolute()


def _canonical_project(root: str | Path) -> str:
    return Path(root).expanduser().resolve().as_posix()


def _parse_projects(payload: object) -> dict[str, str]:
    if not isinstance(payload, dict) or payload.get("version") != 1:
        raise ValueError("Project trust store must be a version 1 JSON object.")
    raw_projects = payload.get("projects")
    if not isinstance(raw_projects, dict) or len(raw_projects) > MAX_TRUSTED_PROJECTS:
        raise ValueError(f"Project trust store projects must be an object with at most {MAX_TRUSTED_PROJECTS} entries.")
    projects: dict[str, str] = {}
    for project, metadata in raw_projects.items():
        if not isinstance(project, str) or not Path(project).is_absolute() or not isinstance(metadata, dict):
            raise ValueError("Project trust store contains an invalid project entry.")
        trusted_at = metadata.get("trustedAt")
        if not isinstance(trusted_at, str) or not trusted_at:
            raise ValueError("Project trust store contains an invalid trustedAt value.")
        projects[Path(project).resolve(strict=False).as_posix()] = trusted_at
    return projects


def _write_project_trust_store(path: Path, projects: dict[str, str]) -> str | None:
    try:
        if len(projects) > MAX_TRUSTED_PROJECTS:
            raise ValueError(f"Project trust store exceeds {MAX_TRUSTED_PROJECTS} entries.")
        _validate_store_path(path, require_parent=False)
        parent = path.parent
        if not parent.exists():
            parent.mkdir(mode=0o700, parents=True)
        _validate_store_path(path, require_parent=True)
        payload = {
            "version": 1,
            "projects": {
                project: {"trustedAt": trusted_at}
                for project, trusted_at in sorted(projects.items())
            },
        }
        encoded = (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
        if len(encoded) > MAX_TRUST_FILE_BYTES:
            raise ValueError(f"Project trust store exceeds {MAX_TRUST_FILE_BYTES} bytes.")
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=parent)
        temporary_path = Path(temporary_name)
        try:
            os.fchmod(descriptor, stat.S_IRUSR | stat.S_IWUSR)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_path, path)
        finally:
            if temporary_path.exists():
                temporary_path.unlink()
        return None
    except (OSError, ValueError) as error:
        return str(error)


def _validate_store_path(path: Path, *, require_parent: bool) -> None:
    parent = path.parent
    if parent.is_symlink():
        raise ValueError(f"Project trust store parent must not be a symbolic link: {parent}")
    if require_parent and (not parent.is_dir() or parent.is_symlink()):
        raise ValueError(f"Project trust store parent is not a regular directory: {parent}")
    if path.is_symlink():
        raise ValueError(f"Project trust store must not be a symbolic link: {path}")
    if path.exists() and not path.is_file():
        raise ValueError(f"Project trust store is not a regular file: {path}")


def _mutation_error_report(
    project: str,
    store: ProjectTrustStore,
    action: str,
    error: str,
) -> dict[str, object]:
    return {
        "ok": False,
        "project": project,
        "trusted": False,
        "trustedAt": None,
        "storePath": store.path.as_posix(),
        "storeError": error,
        "trustedProjects": len(store.projects),
        "changed": False,
        "action": action,
        "message": f"Project permission trust update failed: {error}",
    }
