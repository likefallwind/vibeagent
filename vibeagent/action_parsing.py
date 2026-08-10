from __future__ import annotations

import json
from typing import Any

from .action_parsing_helpers import ActionParseError, summarize_plan_update
from .action_tool_aliases import normalize_tool_action
from .action_parsing_checkpoint import parse_checkpoint_action
from .action_parsing_cron import parse_cron_action
from .action_parsing_delegation import parse_delegation_action
from .action_parsing_code_intel import parse_code_intel_action
from .action_parsing_file_edit import parse_file_edit_action
from .action_parsing_git import parse_git_action
from .action_parsing_json import parse_json_action
from .action_parsing_mcp import parse_mcp_action
from .action_parsing_memory import parse_memory_action
from .action_parsing_process import parse_process_action
from .action_parsing_project import parse_project_action
from .action_parsing_read import parse_read_action
from .action_parsing_runtime import parse_runtime_action
from .action_parsing_search import parse_search_action
from .action_parsing_session import parse_session_action
from .action_parsing_tasks import parse_task_action
from .action_parsing_workflow import parse_workflow_action
from .types import AgentAction


def parse_action(value: Any, raw: str) -> AgentAction:
    # Validate action shape against the small, finite action schema.
    if not isinstance(value, dict):
        raise ActionParseError("Model output must include an action object.", raw)

    action_type = value.get("type")
    for parser in (
        parse_read_action,
        parse_json_action,
        parse_code_intel_action,
        parse_search_action,
        parse_git_action,
        parse_mcp_action,
        parse_memory_action,
        parse_project_action,
        parse_runtime_action,
        parse_session_action,
        parse_cron_action,
        parse_task_action,
        parse_checkpoint_action,
        parse_delegation_action,
        parse_file_edit_action,
        parse_process_action,
        parse_workflow_action,
    ):
        action = parser(action_type, value, raw)
        if action is not None:
            return action

    raise ActionParseError("Unsupported action type.", raw)


def parse_tool_action(name: str, tool_input: Any) -> AgentAction:
    if not isinstance(tool_input, dict):
        raise ActionParseError(f"{name} tool input must be an object.", json.dumps(tool_input))
    action_type, normalized_input = normalize_tool_action(name, tool_input)
    return parse_action(
        {"type": action_type, **normalized_input},
        json.dumps({"name": name, "input": tool_input}),
    )


__all__ = [
    "ActionParseError",
    "parse_action",
    "parse_tool_action",
    "summarize_plan_update",
]
