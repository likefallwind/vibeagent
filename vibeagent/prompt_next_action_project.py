from __future__ import annotations

from .prompt_next_action_project_formatting import (
    available_command_labels,
    available_skill_names,
    blocked_check_labels,
    command_labels,
    format_next_action_items,
    instruction_paths,
    manifest_paths,
    todo_labels,
    tool_names,
    unavailable_tool_names,
)
from .prompt_next_action_project_tests import (
    _check_focused_test_commands_next_action_instruction,
    _focused_test_commands_next_action_instruction,
    _related_tests_next_action_instruction,
)
from .types import Observation


PROJECT_NEXT_ACTION_KINDS = {
    "Agent",
    "Task",
    "WebFetch",
    "WebSearch",
    "delegate_task",
    "suggest_checks",
    "check_suggested_checks",
    "project_commands",
    "tool_search",
    "related_tests",
    "focused_test_commands",
    "check_focused_test_commands",
    "project_manifests",
    "project_instructions",
    "project_skills",
    "project_agents",
    "skill",
    "project_todos",
    "project_overview",
    "environment_info",
    "mcp_servers",
    "mcp_tools",
    "mcp_call",
}


def _tool_search_next_action_instruction(base: str, latest: Observation) -> str:
    if not getattr(latest, "ok", False):
        return f"{base} Tool search failed. Use the known tool catalog or choose the next concrete action manually."

    names = tool_names(getattr(latest, "matches", []))
    if names:
        return (
            f"{base} Tool search found matching tool(s): {format_next_action_items(names)}. "
            "Use the most specific matching tool if it advances the current task; otherwise continue with the known workflow."
        )

    suggestions = [str(item).strip() for item in getattr(latest, "suggestions", []) if str(item).strip()]
    if suggestions:
        return (
            f"{base} Tool search found no direct matches. Consider suggested tool names: {format_next_action_items(suggestions)}."
        )
    return f"{base} Tool search found no matches. Choose from the currently known tools or continue manually."


def _suggest_checks_next_action_instruction(base: str, latest: Observation) -> str:
    if not getattr(latest, "ok", False):
        return (
            f"{base} Suggested checks could not be collected. Use project_commands or focused_test_commands to find runnable checks, "
            "or continue with a known verification command."
        )

    available = available_command_labels(getattr(latest, "checks", []))
    if available:
        return (
            f"{base} Suggested checks are available. Run run_suggested_checks or run_command for: "
            f"{format_next_action_items(available)}. Fix failures before finishing."
        )

    total = int(getattr(latest, "total", 0) or 0)
    if total > 0:
        return (
            f"{base} Suggested checks were found but are not directly available. "
            "Inspect missing tools, use project_commands for alternatives, or run an equivalent check manually."
        )

    return (
        f"{base} No suggested checks were found. Use project_commands, related_tests, or focused_test_commands to find a verification path."
    )


def _check_suggested_checks_next_action_instruction(base: str, latest: Observation) -> str:
    if not getattr(latest, "ok", False):
        blockers = blocked_check_labels(getattr(latest, "checks", []))
        if blockers:
            return (
                f"{base} Suggested check dry-run found blocked command(s): {format_next_action_items(blockers)}. "
                "Fix the command context or choose another verification path before running checks."
            )
        return f"{base} Suggested check dry-run failed. Inspect the message, then choose another verification path."

    runnable = command_labels(getattr(latest, "suggested_checks", []))
    if runnable:
        return (
            f"{base} Suggested check dry-run passed. Run run_suggested_checks or run_command for: "
            f"{format_next_action_items(runnable)}."
        )
    return f"{base} Suggested check dry-run passed but no commands were listed. Continue with the next required check or answer directly."


def _project_commands_next_action_instruction(base: str, latest: Observation) -> str:
    if not getattr(latest, "ok", False):
        return (
            f"{base} Project commands could not be collected. Inspect project_manifests or run a known check command if available."
        )

    available = available_command_labels(getattr(latest, "commands", []))
    if available:
        return (
            f"{base} Project commands were found. Choose the relevant command and use command_check or run_command: "
            f"{format_next_action_items(available)}."
        )

    total = int(getattr(latest, "total", 0) or 0)
    if total > 0:
        return (
            f"{base} Project command hints exist but are not directly runnable. Inspect missing tools or project_manifests, "
            "then choose an equivalent verification command."
        )
    return f"{base} No project commands were found. Use related_tests, focused_test_commands, or a known repository check."


def _project_manifests_next_action_instruction(base: str, latest: Observation) -> str:
    if not getattr(latest, "ok", False):
        return f"{base} Project manifests could not be read. Continue with project_commands or known repository conventions."

    paths = manifest_paths(getattr(latest, "manifests", []))
    if paths:
        return (
            f"{base} Project manifests were found: {format_next_action_items(paths)}. "
            "Use project_commands or suggest_checks to turn manifest metadata into runnable verification steps."
        )
    return f"{base} No project manifests were found. Use project_instructions, project_commands, or direct file inspection to understand the repo."


def _project_instructions_next_action_instruction(base: str, latest: Observation) -> str:
    if not getattr(latest, "ok", False):
        return f"{base} Project instructions could not be read. Continue carefully with local code conventions and targeted inspection."

    paths = instruction_paths(getattr(latest, "files", []))
    if paths:
        return (
            f"{base} Project instructions were read from: {format_next_action_items(paths)}. "
            "Follow those instructions for subsequent edits, then continue with the next concrete task step."
        )

    if str(getattr(latest, "text", "") or "").strip():
        return f"{base} Project instructions text is available. Follow it for subsequent edits, then continue with the task."
    return f"{base} No project instructions were found. Continue using local code patterns and targeted inspection."


def _project_todos_next_action_instruction(base: str, latest: Observation) -> str:
    if not getattr(latest, "ok", False):
        return f"{base} Project TODO search failed. Narrow the path or continue with direct code inspection."

    todos = todo_labels(getattr(latest, "todos", []))
    if todos:
        return (
            f"{base} Project TODOs were found: {format_next_action_items(todos)}. "
            "Inspect the relevant files before editing, or ignore them if they are unrelated to the current task."
        )
    return f"{base} No project TODOs were found. Continue with the current implementation or verification path."


def _project_overview_next_action_instruction(base: str, latest: Observation) -> str:
    if not getattr(latest, "ok", False):
        return f"{base} Project overview could not be read. Use targeted inspection such as list_files, project_commands, or git_status."

    commands = available_command_labels(getattr(latest, "commands", []))
    checks = available_command_labels(getattr(latest, "suggested_checks", []))
    instructions = instruction_paths(getattr(latest, "instruction_sources", []))
    todos = todo_labels(getattr(latest, "todos", []))
    skills = available_skill_names(getattr(latest, "skills", []))
    instruction_detail = (
        f" Project instructions are present in {format_next_action_items(instructions)}; use project_instructions before editing if their content is needed."
        if instructions
        else ""
    )
    todo_detail = (
        f" Project TODO markers are present: {format_next_action_items(todos)}; inspect them if they are relevant to the task."
        if todos
        else ""
    )
    skill_detail = (
        f" Project skills are available: {format_next_action_items(skills)}; use project_skills and skill if one applies before editing."
        if skills
        else ""
    )
    if commands or checks:
        return (
            f"{base} Project overview found runnable project context. "
            f"Use project_commands or suggest_checks for: {format_next_action_items(commands + checks)}."
            f"{instruction_detail}"
            f"{todo_detail}"
            f"{skill_detail}"
        )

    if str(getattr(latest, "git_status", "") or "").strip():
        return (
            f"{base} Project overview shows existing git changes. Inspect git_diff or review_changes before editing, "
            f"then continue with the requested task.{instruction_detail}"
            f"{todo_detail}"
            f"{skill_detail}"
        )
    return f"{base} Project overview is available. Use the tree, manifests, files, instruction sources, TODO markers, and skills to choose the next targeted inspection or edit.{instruction_detail}{todo_detail}{skill_detail}"


def _environment_info_next_action_instruction(base: str, latest: Observation) -> str:
    if not getattr(latest, "ok", False):
        return f"{base} Environment info could not be read. Continue with commands that are already known to work."

    unavailable = unavailable_tool_names(getattr(latest, "tools", []))
    if unavailable:
        return (
            f"{base} Environment info reports unavailable tool(s): {format_next_action_items(unavailable)}. "
            "Choose commands that use available tools or inspect project_commands for alternatives."
        )
    return f"{base} Environment info is available. Use it to choose compatible commands, then continue with implementation or verification."


def project_next_action_instruction(base: str, latest: Observation) -> str:
    if latest.kind == "mcp_servers":
        if not getattr(latest, "ok", False):
            return f"{base} MCP configuration could not be read. Fix .mcp.json or continue without MCP."
        if getattr(latest, "servers", []):
            return f"{base} Choose a configured MCP server and use mcp_tools after approval before calling one of its advertised tools."
        return f"{base} No MCP servers are configured. Continue with built-in tools."
    if latest.kind == "mcp_tools":
        if not getattr(latest, "ok", False):
            return f"{base} MCP tool discovery failed. Inspect the server command, timeout, and protocol error before retrying."
        return f"{base} Use mcp_call with an exact advertised tool name and arguments when it is relevant, or continue with built-in tools."
    if latest.kind == "mcp_call":
        if not getattr(latest, "ok", False):
            return f"{base} The MCP tool call failed or reported an error. Use its bounded output to correct arguments or choose another tool."
        return f"{base} Use the MCP result as external evidence and continue the task or answer directly if complete."
    if latest.kind == "delegate_task":
        if not getattr(latest, "ok", False):
            return (
                f"{base} The delegated task failed. Continue the necessary work in the main agent context "
                "or retry once with a narrower task; do not repeat the same delegation unchanged."
            )
        if getattr(latest, "mode", "explore") == "code":
            return (
                f"{base} Inspect the delegated changes, run any remaining verification, and continue the parent task. "
                "Do not assume the coding subagent's summary alone proves completion."
            )
        return (
            f"{base} Use the delegated findings as evidence, verify critical details with focused reads when needed, "
            "then continue implementation or answer if the task is complete."
        )
    if latest.kind == "suggest_checks":
        return _suggest_checks_next_action_instruction(base, latest)
    if latest.kind == "check_suggested_checks":
        return _check_suggested_checks_next_action_instruction(base, latest)
    if latest.kind == "project_commands":
        return _project_commands_next_action_instruction(base, latest)
    if latest.kind == "project_skills":
        if not getattr(latest, "ok", False):
            return f"{base} Project skill discovery failed. Continue without a skill or inspect the reported metadata error."
        return f"{base} Select a relevant available project skill by exact name and load it with skill, or continue directly if none applies."
    if latest.kind == "project_agents":
        if not getattr(latest, "ok", False):
            return f"{base} Project agent profile discovery failed. Continue with a generic delegation or inspect the reported metadata error."
        return f"{base} Select an available project agent profile by exact name in delegate_task.agent, or use a generic delegation if none matches."
    if latest.kind == "skill":
        if not getattr(latest, "ok", False):
            return f"{base} The requested project skill could not be loaded. Use project_skills to choose an available exact name or continue without it."
        return f"{base} Follow the loaded project skill instructions for the current task, while preserving higher-priority project and user requirements."
    if latest.kind == "tool_search":
        return _tool_search_next_action_instruction(base, latest)
    if latest.kind == "related_tests":
        return _related_tests_next_action_instruction(base, latest)
    if latest.kind == "focused_test_commands":
        return _focused_test_commands_next_action_instruction(base, latest)
    if latest.kind == "check_focused_test_commands":
        return _check_focused_test_commands_next_action_instruction(base, latest)
    if latest.kind == "project_manifests":
        return _project_manifests_next_action_instruction(base, latest)
    if latest.kind == "project_instructions":
        return _project_instructions_next_action_instruction(base, latest)
    if latest.kind == "project_todos":
        return _project_todos_next_action_instruction(base, latest)
    if latest.kind == "project_overview":
        return _project_overview_next_action_instruction(base, latest)
    if latest.kind == "environment_info":
        return _environment_info_next_action_instruction(base, latest)

    raise ValueError(f"Unsupported project next-action kind: {latest.kind}")
