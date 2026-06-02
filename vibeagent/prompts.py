from __future__ import annotations

from .types import ChatMessage, Observation
from .workspace import RunWorkspace, read_workspace_snapshot


# System prompt defines the tool-use contract for project mode.
SYSTEM_PROMPT = """You are VibeAgent, a project-aware ReAct coding agent.

Use the provided tools only when you need to inspect the project, edit files, search, or run commands.
If the user asks a question that can be answered without workspace access, answer directly in text.
When a coding task is complete, either answer directly with a concise summary or call the finish tool.

All file paths must be relative. Never use absolute paths or "..".
The current project directory is the real workspace. Inspect files before editing existing code.
Prefer edit_file over write_file for existing files. Keep tasks small and concrete.
Do not repeat the same list_files action after it already reported an empty directory.
If the directory is empty and the user asks you to create a frontend or website, start writing the needed files.
If the user asks for a file count, use list_files for the relevant path, then answer with the reported total.
If the user asks you to check the result, run an appropriate local command after writing files, then report completion only if it succeeds.
After a relevant check command succeeds, answer with a concise summary on the next turn. Do not keep reading files or running extra checks unless the latest observation shows a concrete error.
Keep each write_file content reasonably small so the JSON response is never truncated.
For frontend or website tasks, do not put all HTML, CSS, and JavaScript into one huge file. Create separate files such as index.html, styles.css, and script.js across separate turns.
For frontend or website tasks, write a complete but compact first version instead of an exhaustive long page. Prefer concise sections and reusable CSS classes.
For frontend or website tasks, one successful basic validation is enough: file existence, referenced asset existence, simple HTML parse, or local HTTP 200 checks. After that, answer with a summary.
"""


def build_messages(task: str, workspace: RunWorkspace, observations: list[Observation] | None = None) -> list[ChatMessage]:
    # Assemble initial context for the model: goal and current workspace state.
    snapshot = read_workspace_snapshot(workspace)
    content = "\n\n".join(
        [
            f"User task:\n{task}",
            f"Project directory:\n{workspace.root}",
            f"Session directory:\n{workspace.session_dir}",
            f"Project files:\n{snapshot}",
            get_next_action_instruction(task, observations or []),
        ]
    )
    return [
        ChatMessage(role="system", content=SYSTEM_PROMPT),
        ChatMessage(role="user", content=content),
    ]


def get_next_action_instruction(task: str, observations: list[Observation]) -> str:
    base = "Choose the next response: call a tool if needed, or answer directly if the task is complete."
    if not observations:
        return base

    latest = observations[-1]
    if latest.kind == "run_command":
        result = latest.result
        if result.exit_code == 0 and not result.timed_out:
            return (
                f"{base} The latest command succeeded. If it checked the requested work, your next action must be "
                "a concise final answer. Do not run another check unless the output contains a concrete error."
            )
        return f"{base} The latest command failed or timed out, so fix the concrete error before finishing."

    if latest.kind in {"read_file", "list_files"}:
        return (
            f"{base} Do not repeat inspection unless you need specific missing information. "
            "If you already created the requested files, run one appropriate check or answer directly if the task is complete."
        )

    if latest.kind in {"write_file", "edit_file"}:
        return f"{base} Continue with the next required file, run one appropriate check, or answer directly if the task is complete."

    return f"{base} If the task is complete, answer directly or use finish."


def format_observations(observations: list[Observation]) -> str:
    # Serialize prior observations in compact human-readable lines for next-turn reasoning.
    if not observations:
        return "No observations yet."

    lines: list[str] = []
    for index, observation in enumerate(observations, start=1):
        if observation.kind == "write_file":
            lines.append(f"{index}. write_file {observation.path}: {observation.message}")
        elif observation.kind == "list_files":
            lines.append(
                "\n".join(
                    [
                        f"{index}. list_files {observation.path}: {observation.message}",
                        *observation.files[:120],
                    ]
                )
            )
        elif observation.kind == "read_file":
            lines.append(
                "\n".join(
                    [
                        f"{index}. read_file {observation.path}: {observation.message}",
                        f"content:\n{truncate(observation.content)}",
                    ]
                )
            )
        elif observation.kind == "search":
            lines.append(
                "\n".join(
                    [
                        f"{index}. search {observation.query}: {observation.message}",
                        *observation.matches[:80],
                    ]
                )
            )
        elif observation.kind == "edit_file":
            lines.append(
                "\n".join(
                    [
                        f"{index}. edit_file {observation.path}: {observation.message}",
                        f"diff:\n{truncate(observation.diff)}",
                    ]
                )
            )
        elif observation.kind == "finish":
            lines.append(f"{index}. finish: {observation.message}")
        elif observation.kind == "tool_error":
            lines.append(f"{index}. tool_error {observation.tool}: {observation.message}")
        else:
            result = observation.result
            lines.append(
                "\n".join(
                    [
                        f"{index}. run_command: {result.command}",
                        f"exitCode: {result.exit_code}",
                        f"timedOut: {str(result.timed_out).lower()}",
                        f"signal: {result.signal or 'none'}",
                        f"stdout:\n{truncate(result.stdout)}",
                        f"stderr:\n{truncate(result.stderr)}",
                    ]
                )
            )

    return "\n\n".join(lines)


def truncate(value: str, max_length: int = 4_000) -> str:
    # Truncate long stdout/stderr fields so prompt context stays within practical size.
    if not value:
        return ""
    if len(value) <= max_length:
        return value
    return f"{value[:max_length]}\n[truncated]"
