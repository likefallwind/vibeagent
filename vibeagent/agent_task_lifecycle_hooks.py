from __future__ import annotations

from collections.abc import Callable

from .action_task_types import TaskCreateAction, TaskUpdateAction
from .agent_hook_prompt import HookModelRuntime
from .agent_lifecycle_hooks import LifecycleHookResult, run_lifecycle_hooks
from .session_tasks import get_session_task, list_session_tasks
from .team_state import TeamStateError, read_team_state
from .types import AgentLogger, ApprovalHandler, ApprovalPolicy, Observation
from .workspace_core import RunWorkspace
from .workspace_hooks import ProjectHooks
from .workspace_permissions import ProjectPermissions


ExecuteActionSafely = Callable[[RunWorkspace, object, int, str], Observation]


def run_task_lifecycle_hooks(
    workspace: RunWorkspace,
    action: object,
    *,
    teammate_name: str | None,
    iteration: int,
    command_timeout_ms: int,
    logger: AgentLogger | None,
    approval_handler: ApprovalHandler | None,
    approval_policy: ApprovalPolicy,
    execute_action_safely_func: ExecuteActionSafely,
    hooks: ProjectHooks,
    permissions: ProjectPermissions,
    hook_model_runtime: HookModelRuntime | None,
) -> LifecycleHookResult:
    expected_event = (
        "TaskCreated"
        if isinstance(action, TaskCreateAction)
        else "TaskCompleted"
        if isinstance(action, TaskUpdateAction) and action.status == "completed"
        else None
    )
    if expected_event is None or not any(hook.event == expected_event for hook in hooks.hooks):
        return LifecycleHookResult()
    if isinstance(action, TaskCreateAction):
        store = list_session_tasks(workspace)
        event = expected_event
        event_fields: dict[str, object] = {
            "task_id": str(store.next_id),
            "task_subject": action.subject,
            "task_description": action.description,
        }
    elif isinstance(action, TaskUpdateAction) and action.status == "completed":
        task, _store = get_session_task(workspace, action.task_id)
        if task is None or task.status == "completed":
            return LifecycleHookResult()
        event = expected_event
        event_fields = {
            "task_id": task.id,
            "task_subject": task.subject,
            "task_description": task.description,
        }
    else:
        return LifecycleHookResult()

    if teammate_name is not None:
        event_fields["teammate_name"] = teammate_name
    team_name = _team_name(workspace)
    if team_name is not None:
        event_fields["team_name"] = team_name
    return run_lifecycle_hooks(
        workspace,
        hooks,
        event,
        "",
        event_fields,
        iteration=iteration,
        command_timeout_ms=command_timeout_ms,
        logger=logger,
        approval_handler=approval_handler,
        approval_policy=approval_policy,
        execute_action_safely_func=execute_action_safely_func,
        permissions=permissions,
        hook_model_runtime=hook_model_runtime,
    )


def _team_name(workspace: RunWorkspace) -> str | None:
    try:
        state = read_team_state(workspace)
    except (OSError, TeamStateError):
        return None
    return state.name if state is not None else None


__all__ = ["run_task_lifecycle_hooks"]
