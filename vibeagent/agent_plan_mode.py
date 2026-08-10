from __future__ import annotations

from dataclasses import dataclass

from .agent_runtime_utils import append_session_event
from .types import ApprovalPolicy, Observation
from .workspace_core import RunWorkspace


@dataclass
class PlanModeRuntime:
    current_policy: ApprovalPolicy
    restore_policy: ApprovalPolicy | None = None

    @classmethod
    def create(cls, approval_policy: ApprovalPolicy) -> PlanModeRuntime:
        return cls(
            current_policy=approval_policy,
            restore_policy="ask" if approval_policy == "plan" else None,
        )

    def apply(
        self,
        workspace: RunWorkspace,
        observation: Observation,
        *,
        iteration: int,
    ) -> bool:
        previous = self.current_policy
        if observation.kind == "enter_plan_mode" and previous != "plan":
            self.restore_policy = previous
            self.current_policy = "plan"
        elif observation.kind == "exit_plan_mode" and previous == "plan":
            self.current_policy = self.restore_policy or "ask"
            self.restore_policy = None
        else:
            return False

        append_session_event(
            workspace.session_dir,
            "permission_mode_changed",
            {
                "iteration": iteration,
                "previous": previous,
                "current": self.current_policy,
                "source": observation.kind,
            },
        )
        return True
