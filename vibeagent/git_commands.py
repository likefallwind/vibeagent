from __future__ import annotations

from pathlib import Path

from .actions import execute_action
from .types import CheckGitFetchAction, CheckGitPullAction, CheckGitPushAction, GitFetchAction, GitPullAction, GitPushAction
from .workspace_core import RunWorkspace


from .git_stash_commands import (
    format_git_stash_apply_report_text,
    format_git_stash_apply_text,
    format_git_stash_drop_report_text,
    format_git_stash_drop_text,
    format_git_stash_report_text,
    format_git_stash_text,
    format_stashes_report_text,
    get_check_stash_apply_report,
    get_check_stash_apply_text,
    get_check_stash_drop_report,
    get_check_stash_drop_text,
    get_check_stash_report,
    get_check_stash_text,
    get_stash_apply_report,
    get_stash_apply_text,
    get_stash_drop_report,
    get_stash_drop_text,
    get_stash_report,
    get_stash_text,
    get_stashes_report,
    get_stashes_text,
    parse_stash_argument,
    parse_stashes_request,
)
from .git_read_commands import (
    _git_output_payload,
    _git_status_payload,
    format_blame_report_text,
    format_branches_report_text,
    format_git_conflicts_report_text,
    format_git_info_report_text,
    format_git_status_report_text,
    format_log_report_text,
    get_blame_report,
    get_blame_text,
    get_branches_report,
    get_branches_text,
    get_git_conflicts_report,
    get_git_conflicts_text,
    get_git_info_report,
    get_git_info_text,
    get_git_status_report,
    get_git_status_text,
    get_log_report,
    get_log_text,
    get_show_report,
    get_show_text,
    format_show_report_text,
    parse_log_request,
    parse_show_request,
)
from .git_index_commands import (
    get_check_stage_report,
    get_check_stage_text,
    get_check_unstage_report,
    get_check_unstage_text,
    get_stage_report,
    get_stage_text,
    get_unstage_report,
    get_unstage_text,
)
from .git_commit_commands import (
    get_check_commit_report,
    get_check_commit_text,
    get_commit_report,
    get_commit_text,
)
from .git_restore_commands import (
    get_check_restore_report,
    get_check_restore_text,
    get_restore_report,
    get_restore_text,
)
from .git_switch_commands import (
    get_check_switch_report,
    get_check_switch_text,
    get_switch_report,
    get_switch_text,
    parse_switch_argument,
)
from .git_local_report_helpers import (
    format_check_switch_text,
    format_git_commit_report_text,
    format_git_commit_text,
    format_git_index_report_text,
    format_git_index_text,
    format_git_restore_report_text,
    format_git_restore_text,
    format_git_switch_report_text,
    format_switch_text,
)
from .git_sync_commands import (
    format_git_fetch_preview_text,
    format_git_fetch_report_text,
    format_git_fetch_text,
    format_git_pull_push_preview_text,
    format_git_pull_report_text,
    format_git_pull_text,
    format_git_push_report_text,
    format_git_push_text,
    format_git_sync_preview_report_text,
    get_check_fetch_report,
    get_check_fetch_text,
    get_check_pull_report,
    get_check_pull_text,
    get_check_push_report,
    get_check_push_text,
    get_fetch_report,
    get_fetch_text,
    get_pull_report,
    get_pull_text,
    get_push_report,
    get_push_text,
    parse_optional_remote_argument,
)
