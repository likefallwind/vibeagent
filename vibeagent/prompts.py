from __future__ import annotations

from .types import ChatMessage, Observation
from .workspace import RunWorkspace, read_workspace_snapshot


# System prompt defines the exact JSON action protocol the model should follow.
SYSTEM_PROMPT = """You are VibeAgent, a project-aware ReAct coding agent.

You solve the user's programming task by producing exactly one JSON object per turn.
Do not use Markdown, comments outside JSON, or code fences.

Allowed actions:
1. list_files: list project files, optionally under a relative path.
2. read_file: read a project file.
3. search: search project text for an exact query string.
4. edit_file: replace one exact text block in an existing project file.
5. write_file: create or replace a file under the project directory.
6. run_command: run a command from the project directory.
7. finish: stop when the task is complete.

All file paths must be relative. Never use absolute paths or "..".
The current project directory is the real workspace. Inspect files before editing existing code.
Prefer edit_file over write_file for existing files. Keep tasks small and concrete.
Return only the JSON object. Never wrap it in Markdown fences such as ```json.
Do not repeat the same list_files action after it already reported an empty directory.
If the directory is empty and the user asks you to create a frontend or website, start writing the needed files.
If the user asks for a file count, use list_files for the relevant path, then finish with the reported total.
If the user asks you to check the result, run an appropriate local command after writing files, then finish only if it succeeds.
Keep each write_file content reasonably small so the JSON response is never truncated.
For frontend or website tasks, do not put all HTML, CSS, and JavaScript into one huge file. Create separate files such as index.html, styles.css, and script.js across separate turns.
For frontend or website tasks, write a complete but compact first version instead of an exhaustive long page. Prefer concise sections and reusable CSS classes.

Required JSON shape:
{
  "thought": "short reasoning summary",
  "action": {
    "type": "list_files | read_file | search | edit_file | write_file | run_command | finish",
    "path": "relative/path.py",
    "query": "search text",
    "old": "exact text to replace",
    "new": "replacement text",
    "content": "...",
    "command": "python relative/path.py",
    "message": "done"
  }
}"""


def build_messages(task: str, workspace: RunWorkspace, observations: list[Observation]) -> list[ChatMessage]:
    # Assemble context for the model: goal, workspace state, and iterative history.
    snapshot = read_workspace_snapshot(workspace)
    content = "\n\n".join(
        [
            f"User task:\n{task}",
            f"Project directory:\n{workspace.root}",
            f"Session directory:\n{workspace.session_dir}",
            f"Project files:\n{snapshot}",
            f"Previous observations:\n{format_observations(observations)}",
            "Choose the next single action. If a command succeeded and proves the task is done, use finish.",
        ]
    )
    return [
        ChatMessage(role="system", content=SYSTEM_PROMPT),
        ChatMessage(role="user", content=content),
    ]


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
