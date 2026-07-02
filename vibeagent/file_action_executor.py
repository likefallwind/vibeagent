from __future__ import annotations

from .file_directory_action_executor import execute_directory_file_action
from .file_path_action_executor import execute_path_file_action
from .file_text_action_executor import execute_text_file_action
from .types import Observation
from .workspace import RunWorkspace


def execute_file_action(workspace: RunWorkspace, action: object) -> Observation | None:
    text_observation = execute_text_file_action(workspace, action)
    if text_observation is not None:
        return text_observation

    path_observation = execute_path_file_action(workspace, action)
    if path_observation is not None:
        return path_observation

    directory_observation = execute_directory_file_action(workspace, action)
    if directory_observation is not None:
        return directory_observation

    return None
