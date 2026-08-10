from __future__ import annotations

from .action_parsing import summarize_plan_update
from .background_delegate_runtime import execute_background_task_action
from .checkpoint_action_executor import execute_checkpoint_action
from .cron_action_executor import execute_cron_action
from .code_intel_action_executor import execute_code_intel_action
from .file_action_executor import execute_file_action
from .final_review_action_executor import execute_final_review_action
from .git_action_executor import execute_git_action
from .json_action_executor import execute_json_action
from .mcp_action_executor import execute_mcp_action
from .memory_action_executor import execute_memory_action
from .project_context_action_executor import execute_project_context_action
from .read_action_executor import execute_read_action
from .runtime_action_executor import execute_runtime_action
from .search_action_executor import execute_search_action
from .session_action_executor import execute_session_action
from .subagent_listing import execute_list_agents_action
from .task_action_executor import execute_task_action
from .team_action_executor import execute_team_action
from .types import (
    AgentAction,
    AskUserAction,
    DelegateTaskAction,
    DelegateTaskObservation,
    EnterPlanModeAction,
    ExitPlanModeAction,
    FinishObservation,
    Observation,
    PlanModeObservation,
    SendMessageAction,
    ToolErrorObservation,
    UpdatePlanAction,
    UpdatePlanObservation,
    UserInputObservation,
)
from .user_input_runtime import serialize_user_input_request, user_input_requests
from .workspace import RunWorkspace


def execute_action(workspace: RunWorkspace, action: AgentAction, command_timeout_ms: int = 30_000) -> Observation:
    # Dispatch one action at a time; all side effects stay within the given project workspace.
    read_observation = execute_read_action(workspace, action)
    if read_observation is not None:
        return read_observation

    json_observation = execute_json_action(workspace, action)
    if json_observation is not None:
        return json_observation

    code_intel_observation = execute_code_intel_action(workspace, action)
    if code_intel_observation is not None:
        return code_intel_observation

    search_observation = execute_search_action(workspace, action)
    if search_observation is not None:
        return search_observation

    git_observation = execute_git_action(workspace, action)
    if git_observation is not None:
        return git_observation

    mcp_observation = execute_mcp_action(workspace, action)
    if mcp_observation is not None:
        return mcp_observation

    memory_observation = execute_memory_action(workspace, action)
    if memory_observation is not None:
        return memory_observation

    final_review_observation = execute_final_review_action(workspace, action)
    if final_review_observation is not None:
        return final_review_observation

    project_context_observation = execute_project_context_action(workspace, action, command_timeout_ms)
    if project_context_observation is not None:
        return project_context_observation

    runtime_observation = execute_runtime_action(workspace, action, command_timeout_ms)
    if runtime_observation is not None:
        return runtime_observation

    session_observation = execute_session_action(workspace, action, command_timeout_ms)
    if session_observation is not None:
        return session_observation

    task_observation = execute_task_action(workspace, action)
    if task_observation is not None:
        return task_observation

    team_observation = execute_team_action(workspace, action)
    if team_observation is not None:
        return team_observation

    cron_observation = execute_cron_action(workspace, action)
    if cron_observation is not None:
        return cron_observation

    list_agents_observation = execute_list_agents_action(workspace, action)
    if list_agents_observation is not None:
        return list_agents_observation

    background_task_observation = execute_background_task_action(workspace, action)
    if background_task_observation is not None:
        return background_task_observation

    checkpoint_observation = execute_checkpoint_action(workspace, action)
    if checkpoint_observation is not None:
        return checkpoint_observation

    file_observation = execute_file_action(workspace, action)
    if file_observation is not None:
        return file_observation

    if isinstance(action, UpdatePlanAction):
        return UpdatePlanObservation(
            kind="update_plan",
            plan=action.plan,
            message=summarize_plan_update(action),
        )

    if isinstance(action, EnterPlanModeAction):
        return PlanModeObservation(
            kind="enter_plan_mode",
            message=(
                "Plan mode is now active. Inspect and plan with read-only tools, "
                "then call ExitPlanMode."
            ),
        )

    if isinstance(action, ExitPlanModeAction):
        return PlanModeObservation(
            kind="exit_plan_mode",
            plan=action.plan,
            message=(
                "Plan approved. Plan mode exited; code execution may continue "
                "under the restored permission mode."
            ),
        )

    if isinstance(action, AskUserAction):
        requests = user_input_requests(action)
        return UserInputObservation(
            kind="ask_user",
            question=requests[0].question,
            options=list(requests[0].options),
            answer=None,
            cancelled=True,
            message="User input is unavailable without an agent user-input handler.",
            questions=(
                [serialize_user_input_request(request) for request in requests]
                if action.questions
                else []
            ),
        )

    if isinstance(action, DelegateTaskAction):
        return DelegateTaskObservation(
            kind="delegate_task",
            ok=False,
            task=action.task,
            summary="",
            iterations=0,
            tool_calls=[],
            message="Task delegation is unavailable without an agent model client.",
            mode=action.mode,
            agent=action.agent,
        )

    if isinstance(action, SendMessageAction):
        from .peer_protocol import send_peer_message
        from .peer_types import PeerMessagingError
        from .types import PeerMessageObservation

        try:
            delivery = send_peer_message(action.to, action.message)
        except PeerMessagingError as error:
            return ToolErrorObservation(kind="tool_error", tool="SendMessage", message=str(error))
        if delivery is not None:
            return PeerMessageObservation(
                kind="peer_message",
                ok=delivery.status == "delivered",
                to=action.to,
                peer_id=delivery.target_id,
                status=delivery.status,
                message=delivery.message,
            )
        return ToolErrorObservation(
            kind="tool_error",
            tool="SendMessage",
            message="Subagent resume is unavailable without an agent model client, and no peer session matched.",
        )

    return FinishObservation(kind="finish", message=action.message)


__all__ = ["execute_action"]
