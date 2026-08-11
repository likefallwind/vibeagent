from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
import time
from typing import Callable, Iterator

from .background_agent_attachment import (
    activate_background_agent_attachment,
    claim_background_agent_attachment,
    release_background_agent_attachment,
)
from .background_agent_config import BackgroundAgentConfig, read_background_agent_config
from .background_agent_lock import background_agent_transition_lock
from .background_agent_store import as_process_record, get_background_agent
from .process_registry import persistent_process_running


@dataclass(frozen=True)
class BackgroundAgentAttachContext:
    config: BackgroundAgentConfig
    invocation_root: Path


@contextmanager
def attach_background_agent(
    project_root: Path,
    agent_id: str,
    *,
    poll_interval: float = 0.05,
    on_wait: Callable[[], None] | None = None,
) -> Iterator[BackgroundAgentAttachContext]:
    root = project_root.resolve()
    with background_agent_transition_lock(root, agent_id):
        view = get_background_agent(root, agent_id)
        if view is None:
            raise ValueError(f"Background agent not found: {agent_id}")
        if view.status in {"needs-input", "approval-error"}:
            raise ValueError(
                f"Resolve the background agent approval before attaching: {agent_id}"
            )
        config = read_background_agent_config(root, agent_id)
        invocation_root = view.record.invocation_root
        if invocation_root.is_symlink() or not invocation_root.is_dir():
            raise ValueError(
                f"Background agent invocation directory is unavailable: {invocation_root}"
            )
        worker_running = persistent_process_running(as_process_record(view.record))
        claim_background_agent_attachment(
            root,
            agent_id,
            waiting_for_worker=worker_running,
        )

    try:
        if worker_running and on_wait is not None:
            on_wait()
        while worker_running:
            if not persistent_process_running(as_process_record(view.record)):
                worker_running = False
                break
            time.sleep(poll_interval)
        with background_agent_transition_lock(root, agent_id):
            activate_background_agent_attachment(root, agent_id)
        yield BackgroundAgentAttachContext(config, invocation_root)
    finally:
        with background_agent_transition_lock(root, agent_id):
            release_background_agent_attachment(root, agent_id)


__all__ = ["BackgroundAgentAttachContext", "attach_background_agent"]
