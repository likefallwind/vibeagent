from __future__ import annotations

from dataclasses import replace
import os
from threading import RLock

from .action_task_types import TaskCreateAction, TaskGetAction, TaskListAction, TaskUpdateAction
from .background_delegate_runtime import send_background_delegate_message
from .subagent_transcripts import SubagentTranscriptError, read_subagent_transcript
from .task_action_executor import execute_task_action
from .team_state import TeamStateError, delete_team_state, ensure_implicit_team_state
from .types import DelegateTaskObservation, Observation, SendMessageAction, ToolErrorObservation
from .workspace_core import RunWorkspace


TEAM_COORDINATION_TOOL_NAMES = frozenset(
    {"SendMessage", "TaskCreate", "TaskGet", "TaskList", "TaskUpdate"}
)
_ENABLED_VALUES = frozenset({"1", "true", "yes", "on"})
_LEAD_INBOX_LOCK = RLock()
_LEAD_INBOXES: dict[str, list[dict[str, str]]] = {}


def agent_teams_enabled() -> bool:
    value = os.environ.get(
        "VIBEAGENT_EXPERIMENTAL_AGENT_TEAMS",
        os.environ.get("CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS", ""),
    )
    return value.strip().lower() in _ENABLED_VALUES


def teammate_spawn_error(
    workspace: RunWorkspace,
    teammate_name: str | None,
    *,
    depth: int,
    allow_existing: bool = False,
) -> str | None:
    if teammate_name is None:
        return None
    if not agent_teams_enabled():
        return (
            "Agent teams are experimental and disabled. Set "
            "VIBEAGENT_EXPERIMENTAL_AGENT_TEAMS=1 to enable named teammates."
        )
    if depth != 1:
        return "Only the lead agent can spawn teammates."
    if allow_existing:
        return _ensure_team_state(workspace)
    try:
        read_subagent_transcript(workspace, teammate_name)
    except SubagentTranscriptError as error:
        if "was not found" in str(error):
            return _ensure_team_state(workspace)
        return str(error)
    return f"Teammate name is already used in this session: {teammate_name}"


def execute_teammate_coordination_action(
    workspace: RunWorkspace,
    action: object,
    teammate_name: str,
) -> Observation | None:
    if isinstance(action, SendMessageAction):
        if action.to == teammate_name:
            return _error("SendMessage", "A teammate cannot send a message to itself.")
        if action.to == "lead":
            _enqueue_lead_message(workspace, teammate_name, action.message)
            return _message_delivered(teammate_name, "lead")
        delivered = send_background_delegate_message(
            workspace,
            action.to,
            action.message,
            sender=teammate_name,
            teammates_only=True,
        )
        if delivered is None:
            return _error("SendMessage", f"Running teammate not found: {action.to}")
        from .agent_runtime_utils import append_session_event

        append_session_event(
            workspace.session_dir,
            "teammate_message_sent",
            {"from": teammate_name, "to": action.to},
        )
        return delivered
    if not isinstance(action, (TaskCreateAction, TaskGetAction, TaskListAction, TaskUpdateAction)):
        return None
    if isinstance(action, TaskUpdateAction):
        current = execute_task_action(
            workspace,
            TaskGetAction(type="task_get", task_id=action.task_id),
        )
        task = getattr(current, "task", None)
        if task is None:
            return execute_task_action(workspace, action)  # type: ignore[return-value]
        owner = getattr(task, "owner", None)
        if owner not in {None, teammate_name}:
            return _error(
                "TaskUpdate",
                f"Task {action.task_id} is owned by teammate {owner}; {teammate_name} cannot update it.",
            )
        if action.owner_set and action.owner not in {None, teammate_name}:
            return _error("TaskUpdate", "Teammates may only assign tasks to themselves.")
        if action.status in {"in_progress", "completed"} and owner is None and not action.owner_set:
            action = replace(action, owner=teammate_name, owner_set=True)
    return execute_task_action(workspace, action)  # type: ignore[return-value]


def collect_lead_team_messages(workspace: RunWorkspace) -> list[dict[str, str]]:
    key = _workspace_key(workspace)
    with _LEAD_INBOX_LOCK:
        return _LEAD_INBOXES.pop(key, [])


def clear_team_messages(workspace: RunWorkspace) -> None:
    with _LEAD_INBOX_LOCK:
        _LEAD_INBOXES.pop(_workspace_key(workspace), None)


def clear_team_runtime(workspace: RunWorkspace) -> None:
    clear_team_messages(workspace)
    try:
        delete_team_state(workspace)
    except (OSError, TeamStateError):
        pass


def _ensure_team_state(workspace: RunWorkspace) -> str | None:
    try:
        state, created = ensure_implicit_team_state(workspace)
    except (OSError, TeamStateError) as error:
        return f"Agent team state is unavailable: {error}"
    if created:
        from .agent_runtime_utils import append_session_event

        append_session_event(
            workspace.session_dir,
            "team_created",
            {"team_name": state.name, "explicit": False},
        )
    return None


def _enqueue_lead_message(workspace: RunWorkspace, sender: str, message: str) -> None:
    with _LEAD_INBOX_LOCK:
        _LEAD_INBOXES.setdefault(_workspace_key(workspace), []).append(
            {"from": sender, "message": message}
        )
    from .agent_runtime_utils import append_session_event

    append_session_event(
        workspace.session_dir,
        "teammate_message_sent",
        {"from": sender, "to": "lead"},
    )


def _message_delivered(sender: str, recipient: str) -> DelegateTaskObservation:
    return DelegateTaskObservation(
        kind="delegate_task",
        ok=True,
        task="Team message",
        summary="",
        iterations=0,
        tool_calls=[],
        message=f"Message delivered from teammate {sender} to {recipient}.",
        task_id=recipient,
        teammate_name=sender,
    )


def _workspace_key(workspace: RunWorkspace) -> str:
    return str(workspace.session_dir.resolve())


def _error(tool: str, message: str) -> ToolErrorObservation:
    return ToolErrorObservation(kind="tool_error", tool=tool, message=message)


__all__ = [
    "TEAM_COORDINATION_TOOL_NAMES",
    "agent_teams_enabled",
    "clear_team_runtime",
    "clear_team_messages",
    "collect_lead_team_messages",
    "execute_teammate_coordination_action",
    "teammate_spawn_error",
]
