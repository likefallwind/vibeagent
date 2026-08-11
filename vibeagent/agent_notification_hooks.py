from __future__ import annotations

from collections.abc import Callable

from .agent_lifecycle_hooks import LifecycleHookResult
from .types import ApprovalHandler, ApprovalRequest


NotifyApproval = Callable[[ApprovalRequest], LifecycleHookResult]
NotificationErrorHandler = Callable[[Exception], None]


def wrap_approval_handler_with_notification(
    handler: ApprovalHandler | None,
    notify: NotifyApproval,
    system_messages: list[str],
    *,
    on_error: NotificationErrorHandler | None = None,
) -> ApprovalHandler | None:
    if handler is None:
        return None

    def wrapped(request: ApprovalRequest):
        needs_prompt = getattr(handler, "needs_prompt", None)
        if callable(needs_prompt) and not needs_prompt(request):
            return handler(request)
        try:
            result = notify(request)
        except Exception as error:
            if on_error is not None:
                try:
                    on_error(error)
                except Exception:
                    pass
        else:
            system_messages.extend(result.system_messages)
        return handler(request)

    return wrapped


def permission_notification_message(request: ApprovalRequest) -> str:
    return f"VibeAgent needs your permission to use {request.action_type}."


__all__ = [
    "permission_notification_message",
    "wrap_approval_handler_with_notification",
]
