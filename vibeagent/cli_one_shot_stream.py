from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager, nullcontext
from dataclasses import dataclass
from pathlib import Path

from .cli_stream_output import JsonEventStream
from .session_event_observers import observe_session_events
from .workspace_core import RunWorkspace, create_run_workspace


@dataclass(frozen=True)
class OneShotStreamScope:
    workspace: RunWorkspace | None
    event_scope: AbstractContextManager[None]


def build_one_shot_stream_scope(
    stream: JsonEventStream | None,
    *,
    project_root: Path,
    mcp_config_paths: tuple[Path, ...],
    strict_mcp_config: bool,
    create_workspace_func: Callable[..., RunWorkspace] = create_run_workspace,
    observe_events_func: Callable[..., AbstractContextManager[None]] = observe_session_events,
) -> OneShotStreamScope:
    if stream is None:
        return OneShotStreamScope(workspace=None, event_scope=nullcontext())

    workspace = create_workspace_func(
        project_root,
        mcp_config_paths=mcp_config_paths,
        strict_mcp_config=strict_mcp_config,
    )
    event_scope = observe_events_func(workspace.session_dir, stream.session_event)
    return OneShotStreamScope(workspace=workspace, event_scope=event_scope)
