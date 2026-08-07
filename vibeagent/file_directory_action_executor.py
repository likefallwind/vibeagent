from __future__ import annotations

from .file_directory_copy_action_executor import execute_directory_copy_action
from .file_directory_create_action_executor import execute_directory_create_action
from .file_directory_delete_action_executor import execute_directory_delete_action
from .file_directory_move_action_executor import execute_directory_move_action
from .file_executable_action_executor import execute_executable_file_action
from .types import Observation
from .workspace import RunWorkspace


def execute_directory_file_action(workspace: RunWorkspace, action: object) -> Observation | None:
    executable_observation = execute_executable_file_action(workspace, action)
    if executable_observation is not None:
        return executable_observation

    move_observation = execute_directory_move_action(workspace, action)
    if move_observation is not None:
        return move_observation

    copy_observation = execute_directory_copy_action(workspace, action)
    if copy_observation is not None:
        return copy_observation

    create_observation = execute_directory_create_action(workspace, action)
    if create_observation is not None:
        return create_observation

    delete_observation = execute_directory_delete_action(workspace, action)
    if delete_observation is not None:
        return delete_observation

    return None
