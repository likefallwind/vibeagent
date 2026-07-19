from __future__ import annotations

from .types import Observation
from .file_exact_action_executor import execute_exact_file_action
from .file_line_action_executor import execute_line_file_action
from .file_patch_action_executor import execute_patch_file_action
from .file_write_action_executor import execute_write_file_action
from .workspace import RunWorkspace


def execute_text_file_action(workspace: RunWorkspace, action: object) -> Observation | None:
    write_observation = execute_write_file_action(workspace, action)
    if write_observation is not None:
        return write_observation

    patch_observation = execute_patch_file_action(workspace, action)
    if patch_observation is not None:
        return patch_observation

    line_observation = execute_line_file_action(workspace, action)
    if line_observation is not None:
        return line_observation

    exact_observation = execute_exact_file_action(workspace, action)
    if exact_observation is not None:
        return exact_observation

    return None
