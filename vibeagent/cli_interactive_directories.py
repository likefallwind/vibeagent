from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
import os
from pathlib import Path

from .cli_additional_directory_state import update_additional_directory_state
from .cli_interactive_cd import resolve_interactive_directory_change
from .cli_interactive_project_runtime import InteractiveProjectRuntime
from .cli_output import format_error
from .directory_added_hooks import schedule_directory_added_hooks
from .goal_state import GoalState, write_goal
from .session_additional_directories import record_session_additional_directories
from .types import ApprovalHandler, ApprovalPolicy
from .workspace_core import (
    RunWorkspace,
    create_local_workspace,
    create_run_workspace,
    normalize_additional_roots,
)
from .workspace_hooks import read_project_hooks
from .workspace_permissions import read_project_permissions


@dataclass(frozen=True)
class InteractiveAddDirectoryRequest:
    project_root: Path
    argument: str | None
    additional_directories: tuple[Path, ...]
    pending_workspace: RunWorkspace | None
    resume_run_id: str | None
    project_runtime: InteractiveProjectRuntime
    approval_policy: ApprovalPolicy
    approval_handler: ApprovalHandler | None
    safe_mode: bool
    bare_mode: bool
    setting_sources: tuple[str, ...]
    settings_override_json: str | None
    invocation_plugin_dirs: tuple[Path, ...]


@dataclass(frozen=True)
class InteractiveAddDirectoryResult:
    additional_directories: tuple[Path, ...]
    pending_workspace: RunWorkspace | None
    messages: tuple[str, ...]


def apply_interactive_add_directory(
    request: InteractiveAddDirectoryRequest,
) -> InteractiveAddDirectoryResult:
    update = update_additional_directory_state(
        request.additional_directories,
        request.argument,
        project_root=request.project_root,
    )
    if not update.changed:
        return InteractiveAddDirectoryResult(
            request.additional_directories,
            request.pending_workspace,
            (update.text,),
        )

    pending_workspace = request.pending_workspace
    if pending_workspace is not None:
        pending_workspace = replace(
            pending_workspace,
            additional_roots=update.directories,
        )
    elif request.resume_run_id is not None:
        pending_workspace = _create_workspace(
            request,
            request.resume_run_id,
            update.directories,
        )

    request.project_runtime.close_workflow()
    messages: list[str] = []
    try:
        record_session_additional_directories(
            request.project_root,
            request.resume_run_id,
            update.directories,
        )
    except (OSError, ValueError) as error:
        messages.append(f"Additional directory persistence warning: {format_error(error)}")

    added = tuple(
        directory
        for directory in update.directories
        if directory not in request.additional_directories
    )
    if added and not request.safe_mode:
        try:
            if pending_workspace is None:
                pending_workspace = _create_workspace(request, None, update.directories)
            hooks = read_project_hooks(pending_workspace)
            permissions = read_project_permissions(pending_workspace)
            if pending_workspace.project_config_trusted and permissions.enabled:
                permissions = replace(permissions, allow_rules_trusted=True)
            for directory in added:
                schedule_directory_added_hooks(
                    pending_workspace,
                    directory,
                    "slash_command",
                    hooks=hooks,
                    permissions=permissions,
                    approval_policy=request.approval_policy,
                    approval_handler=request.approval_handler,
                )
        except (OSError, RuntimeError, ValueError) as error:
            messages.append(f"DirectoryAdded hook warning: {format_error(error)}")
    messages.append(update.text)
    return InteractiveAddDirectoryResult(
        update.directories,
        pending_workspace,
        tuple(messages),
    )


@dataclass(frozen=True)
class InteractiveDirectorySwitchRequest:
    project_root: Path
    argument: str | None
    additional_directories: tuple[Path, ...]
    pending_workspace: RunWorkspace | None
    pending_branch_source_run_id: str | None
    resume_run_id: str | None
    project_permissions_trusted: bool
    project_runtime: InteractiveProjectRuntime
    goal_state: GoalState | None
    approval_policy: ApprovalPolicy
    safe_mode: bool
    bare_mode: bool
    setting_sources: tuple[str, ...]
    settings_override_json: str | None
    invocation_plugin_dirs: tuple[Path, ...]


@dataclass(frozen=True)
class InteractiveDirectorySwitchResult:
    changed: bool
    project_runtime: InteractiveProjectRuntime
    project_permissions_trusted: bool
    additional_directories: tuple[Path, ...]
    pending_workspace: RunWorkspace | None
    pending_branch_source_run_id: str | None
    resume_run_id: str | None
    messages: tuple[str, ...]


def switch_interactive_directory(
    request: InteractiveDirectorySwitchRequest,
    *,
    run_session_end_hook: Callable[[], object],
    prompt_project_permission_trust: Callable[[Path], bool],
) -> InteractiveDirectorySwitchResult:
    change = resolve_interactive_directory_change(
        request.project_root,
        request.argument,
    )
    if not change.changed or change.target is None:
        return _unchanged_switch(request, request.project_runtime, change.text)

    target = change.target
    try:
        target_directories = normalize_additional_roots(
            target,
            request.additional_directories,
        )
        target_permissions_trusted = prompt_project_permission_trust(target)
        target_workspace = create_run_workspace(
            target,
            additional_roots=target_directories,
            safe_mode=request.safe_mode,
            bare_mode=request.bare_mode,
            setting_sources=request.setting_sources,
            settings_override_json=request.settings_override_json,
            invocation_plugin_dirs=request.invocation_plugin_dirs,
        )
    except (OSError, ValueError) as error:
        return _unchanged_switch(
            request,
            request.project_runtime,
            f"Cannot change project directory: {format_error(error)}",
        )

    run_session_end_hook()
    request.project_runtime.close(request.additional_directories, close_lsp=True)
    try:
        os.chdir(target)
    except OSError as error:
        replacement_runtime = _create_project_runtime(request, request.project_root)
        return _unchanged_switch(
            request,
            replacement_runtime,
            f"Cannot change project directory: {format_error(error)}",
        )

    replacement_runtime = _create_project_runtime(
        request,
        target,
        initial_session_id=target_workspace.run_id,
    )
    messages: list[str] = []
    try:
        record_session_additional_directories(
            target,
            target_workspace.run_id,
            target_directories,
        )
        if request.goal_state is not None:
            write_goal(target_workspace, request.goal_state)
    except (OSError, ValueError) as error:
        messages.append(f"Session persistence warning: {format_error(error)}")
    messages.extend(
        (
            change.text,
            f"Conversation preserved in new session: {target_workspace.run_id}",
        )
    )
    return InteractiveDirectorySwitchResult(
        changed=True,
        project_runtime=replacement_runtime,
        project_permissions_trusted=target_permissions_trusted,
        additional_directories=target_directories,
        pending_workspace=target_workspace,
        pending_branch_source_run_id=request.resume_run_id,
        resume_run_id=target_workspace.run_id,
        messages=tuple(messages),
    )


def _create_workspace(
    request: InteractiveAddDirectoryRequest,
    run_id: str | None,
    directories: tuple[Path, ...],
) -> RunWorkspace:
    kwargs = {
        "additional_roots": directories,
        "safe_mode": request.safe_mode,
        "bare_mode": request.bare_mode,
        "setting_sources": request.setting_sources,
        "settings_override_json": request.settings_override_json,
        "invocation_plugin_dirs": request.invocation_plugin_dirs,
    }
    if run_id is None:
        return create_run_workspace(request.project_root, **kwargs)
    return create_local_workspace(request.project_root, run_id, **kwargs)


def _create_project_runtime(
    request: InteractiveDirectorySwitchRequest,
    project_root: Path,
    *,
    initial_session_id: str | None = None,
) -> InteractiveProjectRuntime:
    return InteractiveProjectRuntime(
        project_root,
        request.approval_policy,
        initial_session_id=initial_session_id,
        safe_mode=request.safe_mode,
        bare_mode=request.bare_mode,
        setting_sources=request.setting_sources,
        settings_override_json=request.settings_override_json,
        invocation_plugin_dirs=request.invocation_plugin_dirs,
    )


def _unchanged_switch(
    request: InteractiveDirectorySwitchRequest,
    project_runtime: InteractiveProjectRuntime,
    message: str,
) -> InteractiveDirectorySwitchResult:
    return InteractiveDirectorySwitchResult(
        changed=False,
        project_runtime=project_runtime,
        project_permissions_trusted=request.project_permissions_trusted,
        additional_directories=request.additional_directories,
        pending_workspace=request.pending_workspace,
        pending_branch_source_run_id=request.pending_branch_source_run_id,
        resume_run_id=request.resume_run_id,
        messages=(message,),
    )


__all__ = [
    "InteractiveAddDirectoryRequest",
    "InteractiveAddDirectoryResult",
    "InteractiveDirectorySwitchRequest",
    "InteractiveDirectorySwitchResult",
    "apply_interactive_add_directory",
    "switch_interactive_directory",
]
