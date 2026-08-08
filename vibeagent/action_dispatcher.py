from __future__ import annotations

from .action_parsing import summarize_plan_update
from .background_delegate_runtime import execute_background_task_action
from .checkpoint_action_executor import execute_checkpoint_action
from .code_intel_action_executor import execute_code_intel_action
from .file_action_executor import execute_file_action
from .final_review_action_executor import execute_final_review_action
from .git_action_executor import execute_git_action
from .json_action_executor import execute_json_action
from .mcp_action_executor import execute_mcp_action
from .project_context_action_executor import execute_project_context_action
from .read_action_executor import execute_read_action
from .runtime_action_executor import execute_runtime_action
from .search_action_executor import execute_search_action
from .session_action_executor import execute_session_action
from .types import (
    AgentAction,
    AskUserAction,
    DelegateTaskAction,
    DelegateTaskObservation,
    FinishObservation,
    Observation,
    UpdatePlanAction,
    UpdatePlanObservation,
    UserInputObservation,
)
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

    if isinstance(action, AskUserAction):
        return UserInputObservation(
            kind="ask_user",
            question=action.question,
            options=list(action.options),
            answer=None,
            cancelled=True,
            message="User input is unavailable without an agent user-input handler.",
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

    return FinishObservation(kind="finish", message=action.message)


__all__ = ["execute_action"]
