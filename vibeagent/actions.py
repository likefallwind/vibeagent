from __future__ import annotations

from .action_parsing import ActionParseError, parse_tool_action, summarize_plan_update
from .command_safety import get_blocked_command_reason
from .checkpoint_actions import (
    check_checkpoint_delete_observation,
    check_checkpoint_prune_observation,
    check_checkpoint_restore_observation,
    checkpoint_delete_observation,
    checkpoint_diff_observation,
    checkpoint_prune_observation,
    checkpoint_restore_observation,
    checkpoint_show_observation,
    checkpoint_status_observation,
    checkpoint_untracked_files_match,
    create_checkpoint_observation,
    list_checkpoints_observation,
    read_checkpoint_git_head,
    restore_checkpoint_untracked_files,
    save_checkpoint_untracked_files,
)
from .code_intel_action_executor import execute_code_intel_action
from .final_review_action_executor import execute_final_review_action
from .file_action_executor import execute_file_action
from .git_action_executor import execute_git_action
from .json_action_executor import execute_json_action
from .project_context_action_executor import execute_project_context_action
from .read_action_executor import execute_read_action
from .runtime_action_executor import execute_runtime_action
from .session_action_executor import execute_session_action
from .process_runtime import (
    BACKGROUND_PROCESSES,
    attach_output_analysis_to_process_observation,
    run_command,
)
from .runtime_checks import build_command_check_observation
from .tool_definitions import AGENT_TOOL_DEFINITIONS
from .types import (
    AgentAction,
    CheckCheckpointDeleteAction,
    CheckCheckpointPruneAction,
    CheckCheckpointRestoreAction,
    CheckpointCreateAction,
    CheckpointDeleteAction,
    CheckpointDiffAction,
    CheckpointListAction,
    CheckpointPruneAction,
    CheckpointRestoreAction,
    CheckpointShowAction,
    CheckpointStatusAction,
    FindFilesAction,
    FindFilesObservation,
    FinishObservation,
    GlobAction,
    GlobObservation,
    Observation,
    SearchAction,
    SearchContextResult,
    SearchContextsAction,
    SearchContextsObservation,
    SearchObservation,
    UpdatePlanAction,
    UpdatePlanObservation,
)
from .workspace import (
    RunWorkspace,
    find_project_files_result,
    glob_project_files,
    search_project_contexts_result,
    search_project_result,
)


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

    if isinstance(action, SearchAction):
        try:
            result = search_project_result(
                workspace,
                action.query,
                max_matches=action.max_matches,
                relative_path=action.path,
                regex=action.regex,
                case_sensitive=action.case_sensitive,
                context_lines=action.context_lines,
            )
            matches = list(result["matches"])
            total = int(result["total"])
            truncated = bool(result["truncated"])
            message = f"Found {total} match(es)."
            if truncated:
                message += f" Showing {len(matches)}."
            ok = True
        except ValueError as error:
            matches = []
            total = 0
            truncated = False
            message = str(error)
            ok = False
        return SearchObservation(
            kind="search",
            ok=ok,
            query=action.query,
            matches=matches,
            total=total,
            truncated=truncated,
            message=message,
            path=action.path,
            regex=action.regex,
            case_sensitive=action.case_sensitive,
            context_lines=action.context_lines,
        )

    if isinstance(action, SearchContextsAction):
        try:
            result = search_project_contexts_result(
                workspace,
                action.query,
                max_matches=action.max_matches,
                relative_path=action.path,
                regex=action.regex,
                case_sensitive=action.case_sensitive,
                context_lines=action.context_lines,
                max_bytes_per_context=action.max_bytes_per_context,
            )
            contexts = [SearchContextResult(**item) for item in result["contexts"]]
            total = int(result["total"])
            truncated = bool(result["truncated"])
            message = f"Found {total} match context(s)."
            if truncated:
                message += f" Showing {len(contexts)}."
            ok = True
        except ValueError as error:
            contexts = []
            total = 0
            truncated = False
            message = str(error)
            ok = False
        return SearchContextsObservation(
            kind="search_contexts",
            ok=ok,
            query=action.query,
            contexts=contexts,
            total=total,
            truncated=truncated,
            message=message,
            path=action.path,
            regex=action.regex,
            case_sensitive=action.case_sensitive,
            context_lines=action.context_lines,
            max_bytes_per_context=action.max_bytes_per_context,
        )

    if isinstance(action, FindFilesAction):
        try:
            result = find_project_files_result(
                workspace,
                action.query,
                max_matches=action.max_matches,
                relative_path=action.path,
                regex=action.regex,
                case_sensitive=action.case_sensitive,
                include_dirs=action.include_dirs,
            )
            matches = list(result["matches"])
            total = int(result["total"])
            truncated = bool(result["truncated"])
            message = f"Found {total} path match(es)."
            if truncated:
                message += f" Showing {len(matches)}."
            ok = True
        except ValueError as error:
            matches = []
            total = 0
            truncated = False
            message = str(error)
            ok = False
        return FindFilesObservation(
            kind="find_files",
            ok=ok,
            query=action.query,
            matches=matches,
            total=total,
            truncated=truncated,
            message=message,
            path=action.path,
            regex=action.regex,
            case_sensitive=action.case_sensitive,
            include_dirs=action.include_dirs,
        )

    if isinstance(action, GlobAction):
        try:
            matches, total = glob_project_files(
                workspace,
                action.pattern,
                max_matches=action.max_matches,
                include_dirs=action.include_dirs,
            )
            truncated = len(matches) < total
            noun = "file(s) or directories" if action.include_dirs else "file(s)"
            message = f"Found {total} {noun}."
            if truncated:
                message += f" Showing first {len(matches)}."
            ok = True
        except ValueError as error:
            matches = []
            total = 0
            truncated = False
            message = str(error)
            ok = False
        return GlobObservation(
            kind="glob",
            pattern=action.pattern,
            matches=matches,
            total=total,
            truncated=truncated,
            ok=ok,
            message=message,
        )

    git_observation = execute_git_action(workspace, action)
    if git_observation is not None:
        return git_observation

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

    if isinstance(action, CheckpointCreateAction):
        return create_checkpoint_observation(workspace, action.label)

    if isinstance(action, CheckpointListAction):
        return list_checkpoints_observation(workspace.root, action.max_entries)

    if isinstance(action, CheckpointShowAction):
        return checkpoint_show_observation(workspace.root, action.checkpoint_id)

    if isinstance(action, CheckpointDiffAction):
        return checkpoint_diff_observation(workspace.root, action.checkpoint_id, action.max_chars)

    if isinstance(action, CheckpointStatusAction):
        return checkpoint_status_observation(workspace, action.checkpoint_id)

    if isinstance(action, CheckCheckpointRestoreAction):
        return check_checkpoint_restore_observation(workspace, action.checkpoint_id)

    if isinstance(action, CheckpointRestoreAction):
        return checkpoint_restore_observation(workspace, action.checkpoint_id)

    if isinstance(action, CheckCheckpointDeleteAction):
        return check_checkpoint_delete_observation(workspace.root, action.checkpoint_id)

    if isinstance(action, CheckpointDeleteAction):
        return checkpoint_delete_observation(workspace.root, action.checkpoint_id)

    if isinstance(action, CheckCheckpointPruneAction):
        return check_checkpoint_prune_observation(workspace.root, action.keep_last)

    if isinstance(action, CheckpointPruneAction):
        return checkpoint_prune_observation(workspace.root, action.keep_last)

    file_observation = execute_file_action(workspace, action)
    if file_observation is not None:
        return file_observation

    if isinstance(action, UpdatePlanAction):
        return UpdatePlanObservation(
            kind="update_plan",
            plan=action.plan,
            message=summarize_plan_update(action),
        )

    return FinishObservation(kind="finish", message=action.message)
