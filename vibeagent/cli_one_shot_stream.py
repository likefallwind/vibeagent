from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager, nullcontext
from dataclasses import dataclass
from pathlib import Path

from .cli_stream_output import JsonEventStream
from .cli_subagent_forwarding import SubagentStreamForwarder
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
    additional_roots: tuple[Path, ...] = (),
    safe_mode: bool = False,
    force_workspace: bool = False,
    workspace: RunWorkspace | None = None,
    forward_subagent_text: bool = False,
    create_workspace_func: Callable[..., RunWorkspace] = create_run_workspace,
    observe_events_func: Callable[..., AbstractContextManager[None]] = observe_session_events,
) -> OneShotStreamScope:
    if stream is None and not force_workspace and workspace is None:
        return OneShotStreamScope(workspace=None, event_scope=nullcontext())

    workspace_kwargs: dict[str, object] = {
        "mcp_config_paths": mcp_config_paths,
        "strict_mcp_config": strict_mcp_config,
    }
    if safe_mode:
        workspace_kwargs["safe_mode"] = True
    if additional_roots:
        workspace_kwargs["additional_roots"] = additional_roots
    workspace = workspace or create_workspace_func(project_root, **workspace_kwargs)
    event_scope = (
        observe_events_func(
            workspace.session_dir,
            (
                SubagentStreamForwarder(stream, enabled=True)
                if forward_subagent_text
                else stream.session_event
            ),
        )
        if stream is not None
        else nullcontext()
    )
    return OneShotStreamScope(workspace=workspace, event_scope=event_scope)
