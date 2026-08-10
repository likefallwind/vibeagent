from __future__ import annotations

from .agent_runtime_utils import append_session_event
from .agent_tool_results import record_subagent_tool_result_event
from .subagent_output_safety import scan_subagent_output
from .types import AgentLogger, DelegateTaskAction, DelegateTaskObservation
from .workspace_core import RunWorkspace


def clip_delegate_summary(value: str, max_chars: int = 12_000) -> str:
    value = value.strip()
    if len(value) <= max_chars:
        return value
    return f"{value[:max_chars]}\n[delegate summary truncated]"


def delegate_completion_message(action: DelegateTaskAction) -> str:
    if action.mode == "code":
        return "Subagent completed the coding task."
    return "Subagent completed the investigation."


def finish_delegate_task(
    workspace: RunWorkspace,
    action: DelegateTaskAction,
    subagent_id: str,
    *,
    ok: bool,
    summary: str,
    iterations: int,
    tool_calls: list[str],
    message: str,
    logger: AgentLogger | None,
    tool_event: dict[str, object] | None = None,
    cancelled: bool = False,
) -> DelegateTaskObservation:
    output_scan = scan_subagent_output(summary)
    observation = DelegateTaskObservation(
        kind="delegate_task",
        ok=ok,
        task=action.task,
        summary=output_scan.text,
        iterations=iterations,
        tool_calls=list(tool_calls),
        message=message,
        mode=action.mode,
        agent=action.agent,
        task_id=subagent_id,
        background=action.run_in_background,
        running=False,
        cancelled=cancelled,
        isolation=action.isolation,
        color=action.color,
    )
    if output_scan.matches:
        append_session_event(
            workspace.session_dir,
            "subagent_output_scanned",
            {
                "subagent_id": subagent_id,
                "matches": list(output_scan.matches),
                "input_chars": len(summary),
                "output_chars": len(output_scan.text),
            },
        )
    if tool_event is not None:
        record_subagent_tool_result_event(
            workspace,
            subagent_id=subagent_id,
            parent_iteration=int(tool_event["parent_iteration"]),
            iteration=int(tool_event["iteration"]),
            tool_id=str(tool_event["id"]),
            tool_name=str(tool_event["name"]),
            observation=observation,
            failed=not ok,
        )
    append_session_event(
        workspace.session_dir,
        "subagent_completed",
        {"subagent_id": subagent_id, "result": observation},
    )
    if logger:
        logger("subagent completed" if ok else "subagent failed", message)
    return observation
