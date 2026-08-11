from __future__ import annotations

import argparse
import os
from pathlib import Path

from .background_agent_config import (
    BackgroundAgentConfig,
    background_agent_config_path,
    read_background_agent_config,
    update_background_agent_session_root,
)
from .background_agent_inbox import read_background_agent_message
from .background_agent_types import BACKGROUND_AGENT_ID_PATTERN


BACKGROUND_AGENT_ID_ENV = "VIBEAGENT_BACKGROUND_AGENT_ID"
BACKGROUND_AGENT_CONFIG_ENV = "VIBEAGENT_BACKGROUND_AGENT_CONFIG"


def prepare_background_agent_followup(args: argparse.Namespace) -> None:
    message_path_value = getattr(args, "_background_agent_followup", None)
    if message_path_value is None:
        return
    config = _config_from_environment(args)
    message_path = Path(message_path_value).absolute()
    message = read_background_agent_message(config, message_path)
    args.task = [message]
    args.background = False
    args.print_mode = True
    args.resume = config.resume_reference
    args.resume_from_continue = False
    args.continue_latest = False
    args.session_id = None
    args.compact = None
    args.no_auto_compact = False
    args.fork_session = False
    args.name = None
    args.worktree = None
    args.cwd = config.session_root.as_posix()


def record_background_agent_session_root(
    args: argparse.Namespace,
    session_root: Path,
) -> None:
    if getattr(args, "_background_agent_worker_token", None) is None:
        return
    config = _config_from_environment(args)
    if config.session_root != session_root.resolve():
        update_background_agent_session_root(config, session_root)


def background_agent_worker_config(args: argparse.Namespace) -> BackgroundAgentConfig | None:
    if getattr(args, "_background_agent_worker_token", None) is None:
        return None
    return _config_from_environment(args)


def _config_from_environment(args: argparse.Namespace) -> BackgroundAgentConfig:
    agent_id = os.environ.get(BACKGROUND_AGENT_ID_ENV, "")
    config_value = os.environ.get(BACKGROUND_AGENT_CONFIG_ENV, "")
    if BACKGROUND_AGENT_ID_PATTERN.fullmatch(agent_id) is None or not config_value:
        raise ValueError("Background agent follow-up is unavailable outside its worker.")
    path = Path(config_value).absolute()
    try:
        project_root = path.parents[3]
    except IndexError as error:
        raise ValueError("Background agent config path is invalid.") from error
    expected = background_agent_config_path(project_root, agent_id)
    if path != expected or path.is_symlink():
        raise ValueError("Background agent config path is invalid.")
    config = read_background_agent_config(project_root, agent_id)
    if getattr(args, "_background_agent_worker_token", None) != config.worker_token:
        raise ValueError("Background agent worker token is invalid.")
    return config


__all__ = [
    "BACKGROUND_AGENT_CONFIG_ENV",
    "BACKGROUND_AGENT_ID_ENV",
    "background_agent_worker_config",
    "prepare_background_agent_followup",
    "record_background_agent_session_root",
]
