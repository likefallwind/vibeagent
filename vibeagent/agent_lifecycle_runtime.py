from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .agent_lifecycle_hooks import LifecycleHookResult, run_instruction_loaded_hooks, run_lifecycle_hooks
from .agent_runtime_utils import append_session_event
from .agent_hook_prompt import HookModelRuntime
from .types import (
    AgentLogger,
    ApprovalHandler,
    ApprovalPolicy,
    ChatMessage,
    Observation,
)
from .model_failure import model_failure_fields
from .prompt_expansion import PromptExpansion
from .redaction import redact_sensitive_text
from .workspace_core import RunWorkspace
from .workspace_hooks import HookEvent, ProjectHooks
from .workspace_permissions import ProjectPermissions
from .workspace_project_instructions import read_project_instruction_sources


@dataclass
class AgentLifecycleRuntime:
    hooks: ProjectHooks
    permissions: ProjectPermissions
    command_timeout_ms: int
    logger: AgentLogger | None
    approval_handler: ApprovalHandler | None
    approval_policy: ApprovalPolicy
    execute_action_safely: Callable[[RunWorkspace, object, int, str], Observation]
    hook_model_runtime: HookModelRuntime | None = None
    stop_continuations: int = 0

    def start(
        self,
        workspace: RunWorkspace,
        messages: list[ChatMessage],
        task: str,
        *,
        resumed: bool,
        prompt_expansion: PromptExpansion | None = None,
    ) -> str | None:
        source = "resume" if resumed else "startup"
        session_start = self._run(
            workspace, "SessionStart", source, {"source": source}, iteration=0
        )
        _append_lifecycle_context(
            messages, "SessionStart hook context", session_start.contexts
        )
        self._run_startup_instruction_hooks(workspace)
        if prompt_expansion is not None:
            expansion = self._run(
                workspace,
                "UserPromptExpansion",
                prompt_expansion.command_name,
                prompt_expansion.hook_fields(),
                iteration=0,
            )
            if expansion.blocking_message is not None:
                return expansion.blocking_message
            _append_lifecycle_context(
                messages,
                "UserPromptExpansion hook context",
                expansion.contexts,
            )
        prompt_submit = self._run(
            workspace, "UserPromptSubmit", "", {"prompt": task}, iteration=0
        )
        if prompt_submit.blocking_message is not None:
            return prompt_submit.blocking_message
        _append_lifecycle_context(
            messages, "UserPromptSubmit hook context", prompt_submit.contexts
        )
        return None

    def stop_feedback_if_needed(
        self, workspace: RunWorkspace, message: str, iteration: int
    ) -> str | None:
        if self.stop_continuations >= 8:
            return None
        result = self._run(
            workspace,
            "Stop",
            "",
            {
                "stop_hook_active": self.stop_continuations > 0,
                "last_assistant_message": message,
                "background_tasks": [],
                "session_crons": [],
            },
            iteration=iteration,
        )
        if result.blocking_message is None:
            return None
        self.stop_continuations += 1
        return "Stop hook feedback:\n" + result.blocking_message

    def notify(
        self,
        workspace: RunWorkspace,
        notification_type: str,
        message: str,
        *,
        title: str | None = None,
        iteration: int = 0,
    ) -> LifecycleHookResult:
        fields: dict[str, object] = {
            "message": message,
            "notification_type": notification_type,
        }
        if title:
            fields["title"] = title
        return self._run(
            workspace,
            "Notification",
            notification_type,
            fields,
            iteration=iteration,
        )

    def file_changed(
        self,
        workspace: RunWorkspace,
        path: str,
        event: str,
        *,
        iteration: int = 0,
    ) -> LifecycleHookResult:
        return self._run(
            workspace,
            "FileChanged",
            path.rsplit("/", 1)[-1].rsplit("\\", 1)[-1],
            {"file_path": path, "event": event},
            iteration=iteration,
        )

    def config_change(
        self,
        workspace: RunWorkspace,
        source: str,
        *,
        file_path: str | None = None,
        iteration: int = 0,
    ) -> LifecycleHookResult:
        fields: dict[str, object] = {"source": source}
        if file_path is not None:
            fields["file_path"] = file_path
        return self._run(
            workspace,
            "ConfigChange",
            source,
            fields,
            iteration=iteration,
        )

    def message_display(
        self,
        workspace: RunWorkspace,
        delta: str,
        *,
        turn_id: str,
        message_id: str,
        iteration: int = 0,
    ) -> LifecycleHookResult:
        return self._run(
            workspace,
            "MessageDisplay",
            "",
            {
                "turn_id": turn_id,
                "message_id": message_id,
                "index": 0,
                "final": True,
                "delta": delta,
            },
            iteration=iteration,
        )

    def stop_failure(
        self,
        workspace: RunWorkspace,
        message: str,
        iteration: int,
    ) -> None:
        error, details = model_failure_fields(message)
        try:
            self._run(
                workspace,
                "StopFailure",
                error,
                {
                    "error": error,
                    "error_details": details,
                    "last_assistant_message": str(message),
                },
                iteration=iteration,
            )
        except Exception as hook_error:
            append_session_event(
                workspace.session_dir,
                "stop_failure_hook_error",
                {
                    "iteration": iteration,
                    "error": error,
                    "message": redact_sensitive_text(str(hook_error))[:2_000],
                },
            )

    def compact(
        self,
        workspace: RunWorkspace,
        phase: str,
        trigger: str,
        summary: str | None,
        *,
        iteration: int,
    ) -> None:
        event: HookEvent = "PreCompact" if phase == "pre" else "PostCompact"
        fields: dict[str, object] = {"trigger": trigger}
        if event == "PreCompact":
            fields["custom_instructions"] = ""
        else:
            fields["compact_summary"] = summary or ""
        self._run(
            workspace,
            event,
            trigger,
            fields,
            iteration=iteration,
        )

    def end(
        self,
        workspace: RunWorkspace,
        reason: str,
        *,
        iteration: int = 0,
    ) -> LifecycleHookResult:
        return self._run(
            workspace,
            "SessionEnd",
            reason,
            {"reason": reason},
            iteration=iteration,
        )

    def instruction_hook_runner(
        self,
        workspace: RunWorkspace,
        context: dict[str, object],
        iteration: int,
    ) -> tuple[object, ...]:
        return run_instruction_loaded_hooks(
            workspace,
            self.hooks,
            context,
            iteration=iteration,
            command_timeout_ms=self.command_timeout_ms,
            logger=self.logger,
            approval_handler=self.approval_handler,
            approval_policy=self.approval_policy,
            execute_action_safely_func=self.execute_action_safely,
            permissions=self.permissions,
            hook_model_runtime=self.hook_model_runtime,
        )

    def _run(
        self,
        workspace: RunWorkspace,
        event: HookEvent,
        matcher: str,
        fields: dict[str, object],
        *,
        iteration: int,
    ) -> LifecycleHookResult:
        return run_lifecycle_hooks(
            workspace,
            self.hooks,
            event,
            matcher,
            fields,
            iteration=iteration,
            command_timeout_ms=self.command_timeout_ms,
            logger=self.logger,
            approval_handler=self.approval_handler,
            approval_policy=self.approval_policy,
            execute_action_safely_func=self.execute_action_safely,
            permissions=self.permissions,
            hook_model_runtime=self.hook_model_runtime,
        )

    def _run_startup_instruction_hooks(self, workspace: RunWorkspace) -> None:
        report = read_project_instruction_sources(workspace)
        startup_sources = [
            source
            for source in report["files"]
            if isinstance(source, dict) and source.get("included") is True
        ]
        self.instruction_hook_runner(
            workspace, {"paths": [], "files": startup_sources}, 0
        )


def _append_lifecycle_context(
    messages: list[ChatMessage], label: str, contexts: tuple[str, ...]
) -> None:
    if not contexts:
        return
    addition = f"{label}:\n" + "\n\n".join(contexts)
    for index in range(len(messages) - 1, -1, -1):
        message = messages[index]
        if message.role == "user" and isinstance(message.content, str):
            messages[index] = ChatMessage(
                role="user", content=f"{message.content}\n\n{addition}"
            )
            return
    messages.append(ChatMessage(role="user", content=addition))


__all__ = ["AgentLifecycleRuntime"]
