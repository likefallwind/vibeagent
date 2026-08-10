from __future__ import annotations

import json
import shlex

from .dynamic_workflow_runtime import DynamicWorkflowManager
from .dynamic_workflow_types import WorkflowRunSummary


WORKFLOWS_USAGE = (
    "Usage: /workflows [run <script.js>|show <workflow-id>|resume <workflow-id>|stop <workflow-id>]"
)


def handle_workflows_command(manager: DynamicWorkflowManager, argument: str | None) -> str:
    try:
        parts = shlex.split(argument or "")
    except ValueError as error:
        return f"{WORKFLOWS_USAGE}\nError: {error}"
    try:
        if not parts or parts == ["list"]:
            return format_workflow_list(manager.list())
        if len(parts) != 2 or parts[0] not in {"run", "show", "resume", "stop"}:
            return WORKFLOWS_USAGE
        operation, value = parts
        if operation == "run":
            summary = manager.start(value)
            return f"Workflow started: {summary.id} ({summary.script})"
        if operation == "resume":
            summary = manager.resume(value)
            return f"Workflow resumed: {summary.id}"
        if operation == "stop":
            summary = manager.stop(value)
            return f"Workflow {summary.id}: {summary.status}"
        return format_workflow_detail(manager.get(value))
    except (OSError, UnicodeError, ValueError) as error:
        return f"Workflow error: {error}"


def format_workflow_list(summaries: list[WorkflowRunSummary]) -> str:
    if not summaries:
        return "No workflows found."
    lines = ["Workflows:"]
    for summary in summaries:
        lines.append(
            f"  {summary.id}  {summary.status:<11} calls={summary.total_calls} cached={summary.cached_calls}  {summary.script}"
        )
    return "\n".join(lines)


def format_workflow_detail(summary: WorkflowRunSummary) -> str:
    lines = [
        f"Workflow {summary.id}",
        f"  status: {summary.status}",
        f"  script: {summary.script}",
        f"  session: {summary.session_id}",
        f"  calls: {summary.total_calls}",
        f"  cached calls: {summary.cached_calls}",
        f"  started: {summary.started_at}",
        f"  updated: {summary.updated_at}",
    ]
    if summary.error:
        lines.append(f"  error: {summary.error}")
    if summary.result is not None:
        rendered = json.dumps(summary.result, ensure_ascii=False, sort_keys=True)
        lines.append(f"  result: {rendered[:4000]}{'...' if len(rendered) > 4000 else ''}")
    return "\n".join(lines)


__all__ = ["WORKFLOWS_USAGE", "format_workflow_detail", "format_workflow_list", "handle_workflows_command"]
