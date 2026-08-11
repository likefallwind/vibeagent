from __future__ import annotations

from dataclasses import dataclass, replace
import json
from pathlib import Path
from secrets import token_hex

from .background_agent_store import (
    background_agent_runtime_root,
    ensure_background_agent_runtime_root,
    ensure_private_directory,
    write_private_json,
    write_private_json_atomic,
)
from .background_agent_types import BACKGROUND_AGENT_ID_PATTERN


BACKGROUND_AGENT_CONFIG_VERSION = 1
MAX_BACKGROUND_AGENT_CONFIG_BYTES = 256 * 1024


@dataclass(frozen=True)
class BackgroundAgentConfig:
    agent_id: str
    project_root: Path
    session_root: Path
    resume_reference: str
    base_argv: tuple[str, ...]
    worker_token: str


def create_background_agent_config(
    project_root: Path,
    agent_id: str,
    *,
    session_root: Path,
    resume_reference: str,
    base_argv: list[str],
) -> BackgroundAgentConfig:
    root = project_root.resolve()
    _require_agent_id(agent_id)
    ensure_background_agent_runtime_root(root)
    ensure_private_directory(background_agent_config_root(root))
    config = BackgroundAgentConfig(
        agent_id=agent_id,
        project_root=root,
        session_root=_normalize_session_root(session_root),
        resume_reference=_normalize_resume_reference(resume_reference),
        base_argv=_normalize_base_argv(base_argv),
        worker_token=token_hex(16),
    )
    write_private_json(
        background_agent_config_path(root, agent_id),
        _config_payload(config),
        exclusive=True,
    )
    return config


def read_background_agent_config(project_root: Path, agent_id: str) -> BackgroundAgentConfig:
    root = project_root.resolve()
    _require_agent_id(agent_id)
    path = background_agent_config_path(root, agent_id)
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Background agent does not support follow-up messages: {agent_id}")
    try:
        if path.stat().st_size > MAX_BACKGROUND_AGENT_CONFIG_BYTES:
            raise ValueError(f"Background agent config is too large: {agent_id}")
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Invalid background agent config: {agent_id}") from error
    return _parse_config(payload, root, agent_id)


def update_background_agent_session_root(
    config: BackgroundAgentConfig,
    session_root: Path,
) -> BackgroundAgentConfig:
    updated = replace(config, session_root=_normalize_session_root(session_root))
    write_private_json_atomic(
        background_agent_config_path(config.project_root, config.agent_id),
        _config_payload(updated),
    )
    return updated


def background_agent_config_root(project_root: Path) -> Path:
    return background_agent_runtime_root(project_root) / "config"


def background_agent_config_path(project_root: Path, agent_id: str) -> Path:
    _require_agent_id(agent_id)
    return background_agent_config_root(project_root) / f"{agent_id}.json"


def _config_payload(config: BackgroundAgentConfig) -> dict[str, object]:
    payload = {
        "schemaVersion": BACKGROUND_AGENT_CONFIG_VERSION,
        "agentId": config.agent_id,
        "projectRoot": config.project_root.as_posix(),
        "sessionRoot": config.session_root.as_posix(),
        "resumeReference": config.resume_reference,
        "baseArgv": list(config.base_argv),
        "workerToken": config.worker_token,
    }
    encoded = json.dumps(payload, ensure_ascii=False)
    if len(encoded.encode("utf-8")) > MAX_BACKGROUND_AGENT_CONFIG_BYTES:
        raise ValueError("Background agent launch configuration is too large.")
    return payload


def _parse_config(payload: object, root: Path, agent_id: str) -> BackgroundAgentConfig:
    if (
        not isinstance(payload, dict)
        or payload.get("schemaVersion") != BACKGROUND_AGENT_CONFIG_VERSION
        or payload.get("agentId") != agent_id
        or payload.get("projectRoot") != root.as_posix()
    ):
        raise ValueError(f"Invalid background agent config: {agent_id}")
    session_root = payload.get("sessionRoot")
    resume_reference = payload.get("resumeReference")
    base_argv = payload.get("baseArgv")
    worker_token = payload.get("workerToken")
    if (
        not isinstance(session_root, str)
        or not Path(session_root).is_absolute()
        or Path(session_root).is_symlink()
        or not Path(session_root).is_dir()
        or not isinstance(resume_reference, str)
        or not isinstance(base_argv, list)
        or any(not isinstance(item, str) for item in base_argv)
        or not isinstance(worker_token, str)
        or len(worker_token) != 32
        or any(character not in "0123456789abcdef" for character in worker_token)
    ):
        raise ValueError(f"Invalid background agent config: {agent_id}")
    return BackgroundAgentConfig(
        agent_id=agent_id,
        project_root=root,
        session_root=_normalize_session_root(Path(session_root)),
        resume_reference=_normalize_resume_reference(resume_reference),
        base_argv=_normalize_base_argv(base_argv),
        worker_token=worker_token,
    )


def _normalize_resume_reference(value: str) -> str:
    normalized = value.strip()
    if not normalized or len(normalized) > 200:
        raise ValueError("Background agent resume reference is invalid.")
    return normalized


def _normalize_session_root(value: Path) -> Path:
    if value.is_symlink() or not value.is_dir():
        raise ValueError(f"Background agent session root is not a regular directory: {value}")
    root = value.resolve()
    if not root.is_dir():
        raise ValueError(f"Background agent session root is not a regular directory: {root}")
    return root


def _normalize_base_argv(argv: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    if not argv or len(argv) > 512 or any("\0" in item for item in argv):
        raise ValueError("Background agent launch arguments are invalid.")
    return tuple(argv)


def _require_agent_id(agent_id: str) -> None:
    if BACKGROUND_AGENT_ID_PATTERN.fullmatch(agent_id) is None:
        raise ValueError(f"Invalid background agent id: {agent_id}")


__all__ = [
    "BackgroundAgentConfig",
    "background_agent_config_path",
    "create_background_agent_config",
    "read_background_agent_config",
    "update_background_agent_session_root",
]
