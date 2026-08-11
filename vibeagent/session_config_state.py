from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import shutil
from tempfile import NamedTemporaryFile

from .nested_skill_discovery import discover_nested_skill_locations
from .user_paths import user_home
from .workspace_core import RunWorkspace
from .workspace_metadata_files import has_symlink_component, read_regular_file_bytes


MAX_CONFIG_BYTES = 512_000
MAX_SKILL_FILES = 1_000
MAX_SKILL_FILE_BYTES = 256_000
MAX_SKILL_TOTAL_BYTES = 8_000_000
STATE_VERSION = 1


@dataclass(frozen=True)
class ConfigTarget:
    key: str
    source: str
    path: Path
    boundary: Path
    snapshot: Path
    directory: bool = False
    nested_skills: bool = False


def config_targets(workspace: RunWorkspace) -> tuple[ConfigTarget, ...]:
    home = user_home()
    root = workspace.session_dir / "config-state"
    return (
        ConfigTarget("user_settings", "user_settings", home / ".claude/settings.json", home, root / "user-settings.json"),
        ConfigTarget("project_settings", "project_settings", workspace.root / ".claude/settings.json", workspace.root, root / "project-settings.json"),
        ConfigTarget("local_settings", "local_settings", workspace.root / ".claude/settings.local.json", workspace.root, root / "local-settings.json"),
        ConfigTarget("user_skills", "skills", home / ".claude/skills", home, root / "user-skills", True),
        ConfigTarget("project_skills", "skills", workspace.root / ".claude/skills", workspace.root, root / "project-skills", True),
        ConfigTarget(
            "nested_project_skills",
            "skills",
            workspace.root,
            workspace.root,
            root / "nested-project-skills",
            directory=True,
            nested_skills=True,
        ),
    )


def config_state_path(workspace: RunWorkspace) -> Path:
    return workspace.session_dir / "config-state" / "state.json"


def has_config_state(workspace: RunWorkspace) -> bool:
    path = config_state_path(workspace)
    return path.is_file() and not path.is_symlink()


def effective_settings_path(workspace: RunWorkspace, physical: Path) -> Path:
    if not has_config_state(workspace):
        return physical
    for target in config_targets(workspace):
        if not target.directory and target.path == physical:
            return target.snapshot
    return physical


def effective_skill_root(workspace: RunWorkspace, *, user: bool) -> Path:
    if not has_config_state(workspace):
        return user_home() / ".claude/skills" if user else workspace.root / ".claude/skills"
    key = "user_skills" if user else "project_skills"
    return next(target.snapshot for target in config_targets(workspace) if target.key == key)


def effective_nested_skill_root(workspace: RunWorkspace) -> Path:
    if not has_config_state(workspace):
        return workspace.root
    return next(
        target.snapshot
        for target in config_targets(workspace)
        if target.key == "nested_project_skills"
    )


def initialize_config_state(workspace: RunWorkspace) -> dict[str, dict[str, object]]:
    existing = read_config_state(workspace)
    if existing is not None:
        dirty = False
        for target in config_targets(workspace):
            if target.key in existing:
                continue
            digest = capture_config_target(target)
            existing[target.key] = {"accepted": digest, "observed": digest}
            dirty = True
        if dirty:
            write_config_state(workspace, existing)
        return existing
    state: dict[str, dict[str, object]] = {}
    for target in config_targets(workspace):
        digest = capture_config_target(target)
        state[target.key] = {"accepted": digest, "observed": digest}
    write_config_state(workspace, state)
    return state


def read_config_state(workspace: RunWorkspace) -> dict[str, dict[str, object]] | None:
    path = config_state_path(workspace)
    if not path.exists() and not path.is_symlink():
        return None
    if path.is_symlink() or not path.is_file():
        raise ValueError("Session config state must be a regular non-symlink file.")
    raw = read_regular_file_bytes(path, max_bytes=128_000, label="session config state")
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict) or payload.get("version") != STATE_VERSION:
        raise ValueError("Session config state has an unsupported format.")
    targets = payload.get("targets")
    if not isinstance(targets, dict):
        raise ValueError("Session config state targets must be an object.")
    return {
        key: dict(value)
        for key, value in targets.items()
        if isinstance(key, str) and isinstance(value, dict)
    }


def write_config_state(workspace: RunWorkspace, state: dict[str, dict[str, object]]) -> None:
    path = config_state_path(workspace)
    if path.parent.is_symlink() or path.is_symlink():
        raise ValueError("Session config state path must not contain symbolic links.")
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps({"version": STATE_VERSION, "targets": state}, sort_keys=True, indent=2) + "\n").encode("utf-8")
    _atomic_write(path, encoded)


def fingerprint_config_target(target: ConfigTarget) -> str:
    if target.directory:
        return _skill_digest(_skill_files(target))
    if not target.path.exists() and not target.path.is_symlink():
        return "missing"
    content = _read_config_file(target)
    return "file:" + hashlib.sha256(content).hexdigest()


def capture_config_target(target: ConfigTarget) -> str:
    if target.directory:
        files = _skill_files(target)
        _replace_skill_snapshot(target.snapshot, files)
        return _skill_digest(files)
    if not target.path.exists() and not target.path.is_symlink():
        target.snapshot.unlink(missing_ok=True)
        return "missing"
    content = _read_config_file(target)
    target.snapshot.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write(target.snapshot, content)
    return "file:" + hashlib.sha256(content).hexdigest()


def _read_config_file(target: ConfigTarget) -> bytes:
    if has_symlink_component(target.boundary, target.path) or not target.path.is_file():
        raise ValueError(f"{target.path} must be a regular non-symlink file.")
    return read_regular_file_bytes(target.path, max_bytes=MAX_CONFIG_BYTES, label=target.source)


def _skill_files(target: ConfigTarget) -> list[tuple[Path, bytes]]:
    root = target.path
    if not root.exists() and not root.is_symlink():
        return []
    if has_symlink_component(target.boundary, root) or not root.is_dir():
        raise ValueError(f"{root} must be a regular non-symlink directory.")
    if target.nested_skills:
        locations, truncated = discover_nested_skill_locations(root, max_skills=MAX_SKILL_FILES + 1)
        if truncated or len(locations) > MAX_SKILL_FILES:
            raise ValueError(f"Skill configuration exceeds {MAX_SKILL_FILES} files.")
        paths = [location.path for location in locations]
    else:
        paths = [child / "SKILL.md" for child in sorted(root.iterdir(), key=lambda item: item.name)]

    files: list[tuple[Path, bytes]] = []
    total = 0
    for path in paths:
        if len(files) >= MAX_SKILL_FILES:
            raise ValueError(f"Skill configuration exceeds {MAX_SKILL_FILES} files.")
        if path.parent.is_symlink() or not path.parent.is_dir() or path.is_symlink() or not path.is_file():
            continue
        content = read_regular_file_bytes(path, max_bytes=MAX_SKILL_FILE_BYTES, label="SKILL.md")
        total += len(content)
        if total > MAX_SKILL_TOTAL_BYTES:
            raise ValueError(f"Skill configuration exceeds {MAX_SKILL_TOTAL_BYTES} bytes.")
        files.append((path.relative_to(root), content))
    return files


def _skill_digest(files: list[tuple[Path, bytes]]) -> str:
    digest = hashlib.sha256()
    for relative, content in files:
        digest.update(relative.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(content)
        digest.update(b"\0")
    return "dir:" + digest.hexdigest()


def _replace_skill_snapshot(root: Path, files: list[tuple[Path, bytes]]) -> None:
    if root.is_symlink():
        raise ValueError("Skill snapshot must not be a symbolic link.")
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    for relative, content in files:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write(path, content)


def _atomic_write(path: Path, content: bytes) -> None:
    if path.parent.is_symlink() or path.is_symlink():
        raise ValueError(f"Refusing to write session config state through a symbolic link: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("wb", dir=path.parent, delete=False) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    try:
        os.chmod(temporary, 0o600)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


__all__ = [
    "ConfigTarget",
    "capture_config_target",
    "config_targets",
    "effective_settings_path",
    "effective_nested_skill_root",
    "effective_skill_root",
    "fingerprint_config_target",
    "has_config_state",
    "initialize_config_state",
    "read_config_state",
    "write_config_state",
]
