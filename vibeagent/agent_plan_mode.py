from __future__ import annotations

from dataclasses import dataclass

from .agent_runtime_utils import append_session_event
from .types import (
    ApprovalDecision,
    ApprovalHandler,
    ApprovalPolicy,
    Observation,
)
from .workspace_core import RunWorkspace


@dataclass
class PlanModeRuntime:
    current_policy: ApprovalPolicy
    restore_policy: ApprovalPolicy | None = None
    locked: bool = False

    @classmethod
    def create(
        cls, approval_policy: ApprovalPolicy, *, locked: bool = False
    ) -> PlanModeRuntime:
        return cls(
            current_policy=approval_policy,
            restore_policy="ask" if approval_policy == "plan" else None,
            locked=locked,
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
        elif (
            observation.kind == "exit_plan_mode"
            and previous == "plan"
            and not self.locked
        ):
            self.current_policy = observation.next_policy or self.restore_policy or "ask"
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

    def apply_permission_policy(
        self,
        workspace: RunWorkspace,
        policy: ApprovalPolicy,
        *,
        iteration: int,
    ) -> bool:
        previous = self.current_policy
        if policy == previous:
            return False
        if policy == "plan":
            self.restore_policy = previous
        elif previous == "plan":
            self.restore_policy = None
        self.current_policy = policy
        append_session_event(
            workspace.session_dir,
            "permission_mode_changed",
            {
                "iteration": iteration,
                "previous": previous,
                "current": policy,
                "source": "PermissionRequest",
            },
        )
        return True


def approval_handler_after_plan(
    handler: ApprovalHandler | None,
    policy: ApprovalPolicy,
) -> ApprovalHandler | None:
    if policy != "allow":
        return handler
    return lambda request: ApprovalDecision(
        approved=True,
        message=f"Approved by policy for {request.action_type}.",
    )
