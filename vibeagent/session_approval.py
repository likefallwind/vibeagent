from __future__ import annotations

from dataclasses import dataclass, field, replace

from .types import ApprovalDecision, ApprovalHandler, ApprovalRequest


NON_CACHEABLE_APPROVAL_ACTION_TYPES = frozenset({"mcp_call", "mcp_tools"})


@dataclass
class SessionApprovalHandler:
    prompt: ApprovalHandler
    _approved: dict[tuple[str, str], ApprovalDecision] = field(default_factory=dict)

    def __call__(self, request: ApprovalRequest) -> ApprovalDecision:
        key = approval_cache_key(request)
        if key is not None and key in self._approved:
            original = self._approved[key]
            return ApprovalDecision(
                approved=True,
                message=f"Approved by remembered session decision for {request.action_type}.",
                scope="session",
                remembered=True,
            )

        decision = self.prompt(request)
        if decision.approved and decision.scope == "session":
            if key is None:
                return replace(
                    decision,
                    scope="once",
                    message=(decision.message or "Approved by user.") + " This action always requires separate approval.",
                )
            self._approved[key] = decision
        return decision

    @property
    def remembered_count(self) -> int:
        return len(self._approved)

    def clear(self) -> None:
        self._approved.clear()


def approval_cache_key(request: ApprovalRequest) -> tuple[str, str] | None:
    if request.action_type in NON_CACHEABLE_APPROVAL_ACTION_TYPES:
        return None
    return request.action_type, request.target
