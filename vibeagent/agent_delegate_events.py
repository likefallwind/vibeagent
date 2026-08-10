from __future__ import annotations

from .agent_runtime_utils import append_session_event, to_jsonable
from .types import ContentBlock
from .workspace_core import RunWorkspace


def record_delegate_model_response(
    workspace: RunWorkspace,
    *,
    subagent_id: str,
    parent_iteration: int,
    iteration: int,
    content: list[ContentBlock],
    usage: object | None,
) -> None:
    payload: dict[str, object] = {
        "subagent_id": subagent_id,
        "parent_iteration": parent_iteration,
        "iteration": iteration,
        "content": content,
    }
    if usage is not None:
        payload["usage"] = to_jsonable(usage)
    append_session_event(workspace.session_dir, "subagent_model", payload)


def record_delegate_tool_call(
    workspace: RunWorkspace,
    *,
    subagent_id: str,
    parent_iteration: int,
    iteration: int,
    tool_id: str,
    tool_name: str,
    tool_input: object,
) -> None:
    append_session_event(
        workspace.session_dir,
        "subagent_tool_call",
        {
            "subagent_id": subagent_id,
            "parent_iteration": parent_iteration,
            "iteration": iteration,
            "id": tool_id,
            "name": tool_name,
            "input": tool_input,
        },
    )


__all__ = ["record_delegate_model_response", "record_delegate_tool_call"]
