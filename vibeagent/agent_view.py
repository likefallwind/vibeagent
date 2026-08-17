from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .agent_view_backend import AgentViewBackend, ProjectAgentViewBackend
from .agent_view_render import ordered_agent_views, render_agent_view
from .agent_view_terminal import (
    AgentViewTerminal,
    ScreenReaderAgentViewTerminal,
    StandardAgentViewTerminal,
)
from .background_agent_types import BackgroundAgentView


@dataclass(frozen=True)
class AgentViewOutcome:
    attach_id: str | None = None


def run_agent_view(
    project_root: Path,
    *,
    backend: AgentViewBackend | None = None,
    terminal: AgentViewTerminal | None = None,
    refresh_interval: float = 0.5,
    screen_reader: bool = False,
) -> AgentViewOutcome:
    root = project_root.resolve()
    active_backend = backend or ProjectAgentViewBackend(root, Path.cwd())
    active_terminal = terminal or (
        ScreenReaderAgentViewTerminal() if screen_reader else StandardAgentViewTerminal()
    )
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
                selected = next((view for view in views if view.record.id == selected_id), None)
                approval = (
                    active_backend.approval(selected_id)
                    if selected is not None and selected.status == "needs-input"
                    else None
                )
                user_input = (
                    active_backend.user_input(selected_id)
                    if selected is not None and selected.status == "needs-input" and approval is None
                    else None
                )
                if peek and selected_id is not None:
                    stdout, stderr = active_backend.logs(selected_id)
            except (OSError, ValueError) as error:
                views = ()
                pending = {}
                stdout = ""
                stderr = ""
                approval = None
                user_input = None
                message = f"Refresh failed: {error}"

            width, height = active_terminal.size()
            frame = render_agent_view(
                root,
                views,
                selected_id=selected_id,
                pending_counts=pending,
                peek_stdout=stdout,
                peek_stderr=stderr,
                approval=approval,
                user_input=user_input,
                message=message,
                show_help=show_help,
                width=width,
                height=height,
                screen_reader=screen_reader,
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
            if key in {"enter", "right"}:
                if selected_id is not None:
                    selected = next((view for view in views if view.record.id == selected_id), None)
                    if selected is not None and selected.status in {
                        "needs-input",
                        "approval-error",
                        "input-error",
                    }:
                        message = "Resolve the pending input before attaching."
                    else:
                        return AgentViewOutcome(attach_id=selected_id)
                else:
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
                elif key in {"y", "A", "N"}:
                    if selected_id is None:
                        message = "No background agent is selected."
                    else:
                        message = active_backend.decide_approval(
                            selected_id,
                            key in {"y", "A"},
                            "session" if key == "A" else "once",
                            approval.request_id if approval is not None else None,
                        )
                elif key == "r":
                    if selected_id is None:
                        message = "No background agent is selected."
                    elif user_input is None:
                        message = "Selected agent is not waiting for a question response."
                    else:
                        answer = _prompt_nonempty(active_terminal, "Answer: ")
                        if answer is not None:
                            message = active_backend.answer_user_input(
                                selected_id,
                                answer,
                                user_input.request_id,
                            )
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
