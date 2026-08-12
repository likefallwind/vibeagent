from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager, nullcontext
from dataclasses import dataclass
from pathlib import Path

from .cli_stream_protocol import StreamSessionObserver
from .cli_stream_output import JsonEventStream
from .cli_subagent_forwarding import SubagentStreamForwarder
from .debug_runtime import combine_event_observers
from .session_event_observers import observe_session_events
from .session_event_observers import SessionEventObserver
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
    bare_mode: bool = False,
    setting_sources: tuple[str, ...] = ("user", "project", "local"),
    settings_override_json: str | None = None,
    invocation_plugin_dirs: tuple[Path, ...] = (),
    force_workspace: bool = False,
    workspace: RunWorkspace | None = None,
    include_hook_events: bool = False,
    forward_subagent_text: bool = False,
    event_observer: SessionEventObserver | None = None,
    provider_env: dict[str, str | None] | None = None,
    create_workspace_func: Callable[..., RunWorkspace] = create_run_workspace,
    observe_events_func: Callable[..., AbstractContextManager[None]] = observe_session_events,
) -> OneShotStreamScope:
    if stream is None and event_observer is None and not force_workspace and workspace is None:
        return OneShotStreamScope(workspace=None, event_scope=nullcontext())

    workspace_kwargs: dict[str, object] = {
        "mcp_config_paths": mcp_config_paths,
        "strict_mcp_config": strict_mcp_config,
    }
    if safe_mode:
        workspace_kwargs["safe_mode"] = True
    if bare_mode:
        workspace_kwargs["bare_mode"] = True
    if setting_sources != ("user", "project", "local"):
        workspace_kwargs["setting_sources"] = setting_sources
    if settings_override_json is not None:
        workspace_kwargs["settings_override_json"] = settings_override_json
    if invocation_plugin_dirs:
        workspace_kwargs["invocation_plugin_dirs"] = invocation_plugin_dirs
    if additional_roots:
        workspace_kwargs["additional_roots"] = additional_roots
    workspace = workspace or create_workspace_func(project_root, **workspace_kwargs)
    stream_observer = None
    if stream is not None:
        base_observer: SessionEventObserver = (
            StreamSessionObserver(
                stream,
                workspace,
                provider_env,
                include_hook_events=include_hook_events,
            )
            if provider_env is not None
            else stream.session_event
        )
        stream_observer = (
            SubagentStreamForwarder(stream, enabled=True, fallback=base_observer)
            if forward_subagent_text
            else base_observer
        )
    observer = combine_event_observers(stream_observer, event_observer)
    event_scope = (
        observe_events_func(
            workspace.session_dir,
            observer,
        )
        if observer is not None
        else nullcontext()
    )
    return OneShotStreamScope(workspace=workspace, event_scope=event_scope)
