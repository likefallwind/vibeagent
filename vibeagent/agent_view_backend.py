from __future__ import annotations

from pathlib import Path
from typing import Literal, Protocol

from .background_agent_approval import (
    BackgroundApproval,
    decide_background_approval,
    read_background_approval,
)
from .background_agent_changes import (
    BackgroundAgentChanges,
    read_background_agent_change_content,
    read_background_agent_changes,
)
from .background_agent_inbox import pending_background_agent_message_count
from .background_agent_input import (
    BackgroundUserInput,
    answer_background_user_input,
    read_background_user_input,
)
from .background_agent_integration import (
    BackgroundAgentIntegration,
    integrate_background_agent_changes,
)
from .background_agent_runtime import (
    launch_background_agent,
    list_background_agents,
    read_background_agent_logs,
    remove_background_agent,
    respawn_background_agent,
    send_background_agent_message,
    stop_background_agent,
)
from .background_agent_types import BackgroundAgentView
from .workspace_git_utils import run_readonly_git


class AgentViewBackend(Protocol):
    def list(self) -> tuple[BackgroundAgentView, ...]: ...

    def pending(self, agent_id: str) -> int: ...

    def logs(self, agent_id: str) -> tuple[str, str]: ...

    def changes(self, agent_id: str) -> BackgroundAgentChanges: ...

    def change_content(self, agent_id: str, path: str, side: str) -> str: ...

    def integrate(self, agent_id: str, snapshot_id: str) -> BackgroundAgentIntegration: ...

    def approval(self, agent_id: str) -> BackgroundApproval | None: ...

    def user_input(self, agent_id: str) -> BackgroundUserInput | None: ...

    def answer_user_input(
        self,
        agent_id: str,
        answer: str,
        request_id: str | None = None,
    ) -> str: ...

    def decide_approval(
        self,
        agent_id: str,
        approved: bool,
        scope: Literal["once", "session"],
        request_id: str | None = None,
    ) -> str: ...

    def dispatch(self, task: str) -> BackgroundAgentView: ...

    def reply(self, agent_id: str, message: str) -> str: ...

    def stop(self, agent_id: str) -> str: ...

    def respawn(self, agent_id: str) -> str: ...

    def remove(self, agent_id: str) -> str: ...


class ProjectAgentViewBackend:
    def __init__(self, project_root: Path, invocation_root: Path) -> None:
        self.project_root = project_root.resolve()
        self.invocation_root = invocation_root.resolve()

    def list(self) -> tuple[BackgroundAgentView, ...]:
        return list_background_agents(self.project_root)

    def pending(self, agent_id: str) -> int:
        return pending_background_agent_message_count(self.project_root, agent_id)

    def logs(self, agent_id: str) -> tuple[str, str]:
        view, stdout, stderr = read_background_agent_logs(
            self.project_root,
            agent_id,
            max_chars=6_000,
        )
        if view is None:
            raise ValueError(f"Background agent not found: {agent_id}")
        return stdout, stderr

    def changes(self, agent_id: str) -> BackgroundAgentChanges:
        return read_background_agent_changes(self.project_root, agent_id)

    def change_content(self, agent_id: str, path: str, side: str) -> str:
        return read_background_agent_change_content(
            self.project_root,
            agent_id,
            path,
            side=side,
        )

    def integrate(self, agent_id: str, snapshot_id: str) -> BackgroundAgentIntegration:
        return integrate_background_agent_changes(
            self.project_root,
            agent_id,
            expected_snapshot_id=snapshot_id,
        )

    def approval(self, agent_id: str) -> BackgroundApproval | None:
        return read_background_approval(self.project_root, agent_id)

    def user_input(self, agent_id: str) -> BackgroundUserInput | None:
        return read_background_user_input(self.project_root, agent_id)

    def answer_user_input(
        self,
        agent_id: str,
        answer: str,
        request_id: str | None = None,
    ) -> str:
        interaction = answer_background_user_input(
            self.project_root,
            agent_id,
            answer,
            request_id=request_id,
        )
        return f"Answered {interaction.request.header or 'question'} for {agent_id}."

    def decide_approval(
        self,
        agent_id: str,
        approved: bool,
        scope: Literal["once", "session"],
        request_id: str | None = None,
    ) -> str:
        approval = decide_background_approval(
            self.project_root,
            agent_id,
            approved=approved,
            scope=scope,
            request_id=request_id,
        )
        verb = "Approved" if approved else "Denied"
        return f"{verb} {approval.action_type} for {agent_id}."

    def dispatch(self, task: str) -> BackgroundAgentView:
        argv = ["--background"]
        if _supports_isolated_dispatch(self.project_root):
            argv.append("--worktree")
        argv.extend(["--", task])
        return launch_background_agent(
            self.project_root,
            self.invocation_root,
            argv,
            task_summary=task,
            session_name=None,
        )

    def reply(self, agent_id: str, message: str) -> str:
        view, disposition = send_background_agent_message(
            self.project_root,
            agent_id,
            message,
        )
        if view is None:
            raise ValueError(f"Background agent not found: {agent_id}")
        return f"Message {disposition} for {agent_id}."

    def stop(self, agent_id: str) -> str:
        view = stop_background_agent(self.project_root, agent_id)
        if view is None:
            raise ValueError(f"Background agent not found: {agent_id}")
        return f"Agent {agent_id} status: {view.status}."

    def respawn(self, agent_id: str) -> str:
        view, disposition = respawn_background_agent(self.project_root, agent_id)
        if view is None:
            raise ValueError(f"Background agent not found: {agent_id}")
        return f"Agent {agent_id} {disposition}."

    def remove(self, agent_id: str) -> str:
        removed, message = remove_background_agent(self.project_root, agent_id)
        if not removed:
            raise ValueError(message)
        return message


def _supports_isolated_dispatch(project_root: Path) -> bool:
    result = run_readonly_git(project_root, ["rev-parse", "--is-inside-work-tree"])
    return result.ok and result.stdout.strip() == "true"


__all__ = ["AgentViewBackend", "ProjectAgentViewBackend"]
