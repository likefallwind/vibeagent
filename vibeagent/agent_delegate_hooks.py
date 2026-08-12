from __future__ import annotations

from dataclasses import dataclass

from .agent_execution_support import execute_action_safely
from .agent_hook_results import HookRunResult
from .agent_hook_prompt import HookModelRuntime
from .agent_lifecycle_hooks import LifecycleHookResult, run_lifecycle_hooks
from .types import (
    AgentLogger,
    ApprovalHandler,
    ApprovalPolicy,
    ChatMessage,
    DelegateTaskAction,
)
from .workspace_core import RunWorkspace
from .workspace_hooks import HookEvent, ProjectHooks
from .workspace_permissions import ProjectPermissions
from .team_state import TeamStateError, implicit_team_name, read_team_state


MAX_SUBAGENT_STOP_CONTINUATIONS = 8
MAX_TEAMMATE_IDLE_CONTINUATIONS = 8


@dataclass
class DelegateLifecycleHooks:
    workspace: RunWorkspace
    action: DelegateTaskAction
    subagent_id: str
    hooks: ProjectHooks
    command_timeout_ms: int
    logger: AgentLogger | None
    approval_handler: ApprovalHandler | None
    approval_policy: ApprovalPolicy
    permissions: ProjectPermissions
    hook_model_runtime: HookModelRuntime | None = None
    stop_continuations: int = 0
    idle_continuations: int = 0

    @property
    def agent_type(self) -> str:
        if self.action.agent:
            return self.action.agent
        return "Explore" if self.action.mode == "explore" else "general-purpose"

    def start(self, messages: list[ChatMessage]) -> tuple[HookRunResult, ...]:
        result = self._run(
            "SubagentStart",
            {
                "agent_id": self.subagent_id,
                "agent_type": self.agent_type,
            },
            iteration=0,
        )
        _append_context(messages, result.contexts)
        return result.results

    def stop_feedback(self, last_message: str, iteration: int) -> str | None:
        if self.stop_continuations >= MAX_SUBAGENT_STOP_CONTINUATIONS:
            return None
        transcript_path = str(self.workspace.session_dir / "events.jsonl")
        result = self._run(
            "SubagentStop",
            {
                "stop_hook_active": self.stop_continuations > 0,
                "agent_id": self.subagent_id,
                "agent_type": self.agent_type,
                "agent_transcript_path": transcript_path,
                "last_assistant_message": last_message,
            },
            iteration=iteration,
        )
        if result.blocking_message is None:
            return None
        self.stop_continuations += 1
        return "SubagentStop hook feedback:\n" + result.blocking_message

    def teammate_idle_feedback(self, iteration: int) -> tuple[str | None, str | None]:
        teammate_name = self.action.teammate_name
        if teammate_name is None or self.idle_continuations >= MAX_TEAMMATE_IDLE_CONTINUATIONS:
            return None, None
        try:
            team = read_team_state(self.workspace)
        except (OSError, TeamStateError):
            team = None
        result = self._run(
            "TeammateIdle",
            {
                "teammate_name": teammate_name,
                "team_name": team.name if team is not None else implicit_team_name(self.workspace),
            },
            iteration=iteration,
        )
        if result.blocking_message is None:
            return None, None
        if result.halt_turn_message is not None:
            return None, result.halt_turn_message
        self.idle_continuations += 1
        return "TeammateIdle hook feedback:\n" + result.blocking_message, None

    def _run(
        self,
        event: HookEvent,
        fields: dict[str, object],
        *,
        iteration: int,
    ) -> LifecycleHookResult:
        return run_lifecycle_hooks(
            self.workspace,
            self.hooks,
            event,
            self.agent_type,
            fields,
            iteration=iteration,
            command_timeout_ms=self.command_timeout_ms,
            logger=self.logger,
            approval_handler=self.approval_handler,
            approval_policy=self.approval_policy,
            execute_action_safely_func=execute_action_safely,
            permissions=self.permissions,
            hook_model_runtime=self.hook_model_runtime,
        )


def _append_context(messages: list[ChatMessage], contexts: tuple[str, ...]) -> None:
    if not contexts:
        return
    addition = "SubagentStart hook context:\n" + "\n\n".join(contexts)
    for index in range(len(messages) - 1, -1, -1):
        message = messages[index]
        if message.role == "user" and isinstance(message.content, str):
            messages[index] = ChatMessage(
                role="user",
                content=f"{message.content}\n\n{addition}",
            )
            return
    messages.append(ChatMessage(role="user", content=addition))


__all__ = [
    "DelegateLifecycleHooks",
    "MAX_SUBAGENT_STOP_CONTINUATIONS",
    "MAX_TEAMMATE_IDLE_CONTINUATIONS",
]
