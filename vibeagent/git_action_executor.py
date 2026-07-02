from __future__ import annotations

from .git_index_action_executor import execute_git_index_action
from .git_info_action_executor import execute_git_info_action
from .git_read_action_executor import execute_git_read_action
from .git_remote_action_executor import execute_git_remote_action
from .git_stash_action_executor import execute_git_stash_action
from .types import Observation
from .workspace import RunWorkspace


def execute_git_action(workspace: RunWorkspace, action: object) -> Observation | None:
    info_observation = execute_git_info_action(workspace, action)
    if info_observation is not None:
        return info_observation

    remote_observation = execute_git_remote_action(workspace, action)
    if remote_observation is not None:
        return remote_observation

    read_observation = execute_git_read_action(workspace, action)
    if read_observation is not None:
        return read_observation

    index_observation = execute_git_index_action(workspace, action)
    if index_observation is not None:
        return index_observation

    stash_observation = execute_git_stash_action(workspace, action)
    if stash_observation is not None:
        return stash_observation

    return None
