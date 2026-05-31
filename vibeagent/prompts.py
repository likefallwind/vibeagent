from __future__ import annotations

from .types import ChatMessage, Observation
from .workspace import RunWorkspace, read_workspace_snapshot


# System prompt defines the exact JSON action protocol the model should follow.
SYSTEM_PROMPT = """You are VibeAgent, a minimal ReAct coding agent.

You solve the user's programming task by producing exactly one JSON object per turn.
Do not use Markdown, comments outside JSON, or code fences.

Allowed actions:
1. write_file: create or replace a file under the current run directory.
2. run_command: run a command from the current run directory.
3. finish: stop when the task is complete.

All file paths must be relative. Never use absolute paths or "..".
Keep tasks small and concrete. Prefer Python scripts unless the user asks for another language.

Required JSON shape:
{
  "thought": "short reasoning summary",
  "action": {
    "type": "write_file | run_command | finish",
    "path": "relative/path.py",
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
            f"Run directory:\n{workspace.root}",
            f"Current files:\n{snapshot}",
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
