from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .agent_peer_notifications import peer_messages_as_task
from .agent_runtime_utils import append_session_event
from .async_hook_runtime import (
    async_hook_notifications_prompt,
    collect_async_hook_notifications,
)
from .cli_idle_notification import IdleNotificationTimer
from .cli_interactive_project_runtime import InteractiveProjectRuntime
from .cli_output import format_error
from .monitor_runtime import collect_monitor_notifications, monitor_notifications_prompt
from .plugin_auto_update import format_plugin_auto_update_notification
from .scheduled_task_store import collect_due_scheduled_tasks
from .types import ApprovalPolicy
from .workspace_core import RunWorkspace, create_local_workspace


CodeTaskRunner = Callable[
    [str, dict[str, object] | None],
    tuple[object, str | None],
]


@dataclass(frozen=True)
class InteractiveIdleContext:
    project_root: Path
    project_runtime: InteractiveProjectRuntime
    file_changed_runtime: Any | None
    config_change_runtime: Any | None
    idle_notification: IdleNotificationTimer
    current_resume_run_id: Callable[[], str | None]
    current_pending_workspace: Callable[[], RunWorkspace | None]
    additional_directories: tuple[Path, ...]
    safe_mode: bool
    bare_mode: bool
    disable_slash_commands: bool
    setting_sources: tuple[str, ...]
    settings_override_json: str | None
    invocation_plugin_dirs: tuple[Path, ...]
    current_approval_handler: Callable[[], Any]
    current_approval_policy: Callable[[], ApprovalPolicy]
    command_timeout_ms: Callable[[], int]
    scheduled_tasks_enabled: Callable[[], bool]
    run_notification_hooks: Callable[..., Any]
    run_code_task: CodeTaskRunner
    maybe_generate_automatic_recap: Callable[[], None]


def run_interactive_idle_tasks(context: InteractiveIdleContext) -> None:
    try:
        _poll_change_runtime(context.file_changed_runtime)
        _poll_change_runtime(context.config_change_runtime)
        resume_run_id = context.current_resume_run_id()
        if (
            not context.safe_mode
            and context.idle_notification.due()
            and resume_run_id is not None
        ):
            notification = context.run_notification_hooks(
                context.project_root,
                resume_run_id,
                context.current_pending_workspace(),
                context.additional_directories,
                "idle_prompt",
                "VibeAgent is waiting for your input.",
                title="VibeAgent is waiting",
                command_timeout_ms=context.command_timeout_ms(),
                approval_handler=context.current_approval_handler(),
                approval_policy=context.current_approval_policy(),
            )
            _print_system_messages(notification)
        notifications = (
            ()
            if context.safe_mode
            else context.project_runtime.collect_plugin_notifications()
        )
        for notification in notifications:
            print(f"\n{format_plugin_auto_update_notification(notification)}")
        if context.project_runtime.peer is not None:
            peer_task = peer_messages_as_task(context.project_runtime.peer)
            if peer_task is not None:
                task, metadata = peer_task
                print("\nPeer session message received.")
                context.run_code_task(task, metadata)

        resume_run_id = context.current_resume_run_id()
        if resume_run_id is None:
            context.maybe_generate_automatic_recap()
            return
        workspace = _idle_workspace(context, resume_run_id)
        async_notifications = (
            []
            if context.safe_mode
            else collect_async_hook_notifications(workspace, rewake_only=True)
        )
        if async_notifications:
            print("\nAsynchronous hook requested attention.")
            context.run_code_task(
                async_hook_notifications_prompt(async_notifications),
                {
                    "source": "async_hook_rewake",
                    "asyncHookProcessIds": [item.process_id for item in async_notifications],
                },
            )
        monitor_notifications = (
            [] if context.safe_mode else collect_monitor_notifications(workspace)
        )
        if monitor_notifications:
            print("\nMonitor event received.")
            context.run_code_task(
                monitor_notifications_prompt(monitor_notifications),
                {
                    "source": "monitor",
                    "monitorTaskIds": sorted(
                        {item.task_id for item in monitor_notifications}
                    ),
                },
            )
        if not context.scheduled_tasks_enabled():
            context.maybe_generate_automatic_recap()
            return

        current_run_id = context.current_resume_run_id()
        if current_run_id is None:
            context.maybe_generate_automatic_recap()
            return
        workspace = _idle_workspace(context, current_run_id)
        due = collect_due_scheduled_tasks(workspace)
        if due:
            append_session_event(
                workspace.session_dir,
                "scheduled_tasks_delivered",
                {
                    "iteration": 0,
                    "count": len(due),
                    "task_ids": [scheduled.id for scheduled in due],
                    "idle": True,
                },
            )
        for scheduled in due:
            print(f"\nScheduled task {scheduled.id}: {scheduled.prompt}")
            context.run_code_task(
                scheduled.prompt,
                {
                    "source": "scheduled_task",
                    "scheduledTaskId": scheduled.id,
                    "scheduledFor": scheduled.scheduled_for,
                },
            )
        context.maybe_generate_automatic_recap()
    except KeyboardInterrupt:
        raise
    except Exception as error:
        print(f"\nIdle task error: {format_error(error)}")


def _idle_workspace(
    context: InteractiveIdleContext,
    run_id: str,
) -> RunWorkspace:
    return create_local_workspace(
        context.project_root,
        run_id,
        additional_roots=context.additional_directories,
        safe_mode=context.safe_mode,
        bare_mode=context.bare_mode,
        disable_slash_commands=context.disable_slash_commands,
        setting_sources=context.setting_sources,
        settings_override_json=context.settings_override_json,
        invocation_plugin_dirs=context.invocation_plugin_dirs,
    )


def _poll_change_runtime(runtime: Any | None) -> None:
    if runtime is None:
        return
    _print_system_messages(runtime.poll(iteration=0))


def _print_system_messages(result: Any) -> None:
    for message in result.system_messages:
        print(f"\n{message}")


__all__ = ["InteractiveIdleContext", "run_interactive_idle_tasks"]
