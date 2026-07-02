from __future__ import annotations

from .code_action_executor import execute_code_action
from .python_action_executor import execute_python_action
from .types import AgentAction, Observation


def execute_code_intel_action(workspace, action: AgentAction) -> Observation | None:
    python_observation = execute_python_action(workspace, action)
    if python_observation is not None:
        return python_observation

    code_observation = execute_code_action(workspace, action)
    if code_observation is not None:
        return code_observation

    return None
