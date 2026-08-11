from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .agent_view_render import ordered_agent_views, render_agent_view
from .agent_view_terminal import AgentViewTerminal, StandardAgentViewTerminal
from .background_agent_inbox import pending_background_agent_message_count
from .background_agent_runtime import (
    launch_background_agent,
    list_background_agents,
    read_background_agent_logs,
    remove_background_agent,
    respawn_background_agent,
    send_background_agent_message,
    stop_background_agent,
)
from .background_agent_types import BackgroundAgentView


@dataclass(frozen=True)
class AgentViewOutcome:
    attach_id: str | None = None


class AgentViewBackend(Protocol):
    def list(self) -> tuple[BackgroundAgentView, ...]: ...

    def pending(self, agent_id: str) -> int: ...

    def logs(self, agent_id: str) -> tuple[str, str]: ...

    def dispatch(self, task: str) -> BackgroundAgentView: ...

    def reply(self, agent_id: str, message: str) -> str: ...

    def stop(self, agent_id: str) -> str: ...

    def respawn(self, agent_id: str) -> str: ...

    def remove(self, agent_id: str) -> str: ...


class ProjectAgentViewBackend:
    def __init__(self, project_root: Path, invocation_root: Path) -> None:
        self.project_root = project_root.resolve()
        self.invocation_root = invocation_root.resolve()

    def list(self) -> tuple[BackgroundAgentView, ...]:
        return list_background_agents(self.project_root)

    def pending(self, agent_id: str) -> int:
        return pending_background_agent_message_count(self.project_root, agent_id)

    def logs(self, agent_id: str) -> tuple[str, str]:
        view, stdout, stderr = read_background_agent_logs(
            self.project_root,
            agent_id,
            max_chars=6_000,
        )
        if view is None:
            raise ValueError(f"Background agent not found: {agent_id}")
        return stdout, stderr

    def dispatch(self, task: str) -> BackgroundAgentView:
        return launch_background_agent(
            self.project_root,
            self.invocation_root,
            ["--background", "--", task],
            task_summary=task,
            session_name=None,
        )

    def reply(self, agent_id: str, message: str) -> str:
        view, disposition = send_background_agent_message(
            self.project_root,
            agent_id,
            message,
        )
        if view is None:
            raise ValueError(f"Background agent not found: {agent_id}")
        return f"Message {disposition} for {agent_id}."

    def stop(self, agent_id: str) -> str:
        view = stop_background_agent(self.project_root, agent_id)
        if view is None:
            raise ValueError(f"Background agent not found: {agent_id}")
        return f"Agent {agent_id} status: {view.status}."

    def respawn(self, agent_id: str) -> str:
        view, disposition = respawn_background_agent(self.project_root, agent_id)
        if view is None:
            raise ValueError(f"Background agent not found: {agent_id}")
        return f"Agent {agent_id} {disposition}."

    def remove(self, agent_id: str) -> str:
        removed, message = remove_background_agent(self.project_root, agent_id)
        if not removed:
            raise ValueError(message)
        return message


def run_agent_view(
    project_root: Path,
    *,
    backend: AgentViewBackend | None = None,
    terminal: AgentViewTerminal | None = None,
    refresh_interval: float = 0.5,
) -> AgentViewOutcome:
    root = project_root.resolve()
    active_backend = backend or ProjectAgentViewBackend(root, Path.cwd())
    active_terminal = terminal or StandardAgentViewTerminal()
    selected_id: str | None = None
    peek = False
    show_help = False
    message = ""
    previous_frame: list[str] | None = None

    with active_terminal:
        while True:
            try:
                views = ordered_agent_views(active_backend.list())
                selected_id = _resolve_selection(views, selected_id)
                pending = {
                    view.record.id: active_backend.pending(view.record.id)
                    for view in views
                }
                stdout = ""
                stderr = ""
                if peek and selected_id is not None:
                    stdout, stderr = active_backend.logs(selected_id)
            except (OSError, ValueError) as error:
                views = ()
                pending = {}
                stdout = ""
                stderr = ""
                message = f"Refresh failed: {error}"

            width, height = active_terminal.size()
            frame = render_agent_view(
                root,
                views,
                selected_id=selected_id,
                pending_counts=pending,
                peek_stdout=stdout,
                peek_stderr=stderr,
                message=message,
                show_help=show_help,
                width=width,
                height=height,
            )
            if frame != previous_frame:
                active_terminal.draw(frame)
                previous_frame = frame
            key = active_terminal.read_key(refresh_interval)
            if key is None or key == "c":
                continue
            if key in {"q", "escape"}:
                return AgentViewOutcome()
            if key == "?":
                show_help = not show_help
                continue
            if show_help:
                continue
            if key in {"up", "k", "down", "j", "home", "end"}:
                selected_id = _move_selection(views, selected_id, key)
                message = ""
                continue
            if key in {"space", "p", "l"}:
                peek = not peek
                continue
            if key in {"enter", "right", "a"}:
                if selected_id is not None:
                    return AgentViewOutcome(attach_id=selected_id)
                message = "No background agent is selected."
                continue
            try:
                if key in {"n", "d"}:
                    task = _prompt_nonempty(active_terminal, "Dispatch task: ")
                    if task is not None:
                        launched = active_backend.dispatch(task)
                        selected_id = launched.record.id
                        message = f"Dispatched background agent {selected_id}."
                elif key == "m":
                    if selected_id is None:
                        message = "No background agent is selected."
                    else:
                        reply = _prompt_nonempty(active_terminal, "Reply: ")
                        if reply is not None:
                            message = active_backend.reply(selected_id, reply)
                elif key == "s":
                    message = _selected_action(active_backend.stop, selected_id)
                elif key == "R":
                    message = _selected_action(active_backend.respawn, selected_id)
                elif key == "x":
                    if selected_id is None:
                        message = "No background agent is selected."
                    else:
                        confirmation = active_terminal.prompt(
                            f"Remove {selected_id} and its logs? [y/N] "
                        )
                        if confirmation is not None and confirmation.strip().lower() == "y":
                            message = active_backend.remove(selected_id)
                            selected_id = None
                        else:
                            message = "Removal cancelled."
            except (OSError, ValueError) as error:
                message = str(error)


def _resolve_selection(
    views: tuple[BackgroundAgentView, ...],
    selected_id: str | None,
) -> str | None:
    ids = [view.record.id for view in views]
    if selected_id in ids:
        return selected_id
    return ids[0] if ids else None


def _move_selection(
    views: tuple[BackgroundAgentView, ...],
    selected_id: str | None,
    key: str,
) -> str | None:
    ids = [view.record.id for view in views]
    if not ids:
        return None
    if key == "home":
        return ids[0]
    if key == "end":
        return ids[-1]
    try:
        index = ids.index(selected_id) if selected_id is not None else 0
    except ValueError:
        index = 0
    delta = -1 if key in {"up", "k"} else 1
    return ids[(index + delta) % len(ids)]


def _prompt_nonempty(terminal: AgentViewTerminal, label: str) -> str | None:
    value = terminal.prompt(label)
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _selected_action(action, selected_id: str | None) -> str:
    if selected_id is None:
        return "No background agent is selected."
    return action(selected_id)


__all__ = [
    "AgentViewBackend",
    "AgentViewOutcome",
    "ProjectAgentViewBackend",
    "run_agent_view",
]
