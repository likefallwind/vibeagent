from __future__ import annotations

import json
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any

from .actions import AGENT_TOOL_DEFINITIONS, ActionParseError, execute_action, parse_tool_action
from .prompts import build_messages
from .types import (
    AgentLogger,
    ChatClient,
    ChatMessage,
    ContentBlock,
    ListFilesObservation,
    Observation,
    RunCommandObservation,
    ToolErrorObservation,
)
from .workspace import RunWorkspace, create_run_workspace


@dataclass(frozen=True)
class AgentResult:
    success: bool
    message: str
    run_dir: Path
    run_id: str
    iterations: int
    observations: list[Observation]


def run_agent(
    task: str,
    client: ChatClient,
    base_dir: str | Path | None = None,
    max_iterations: int = 20,
    command_timeout_ms: int = 30_000,
    logger: AgentLogger | None = None,
    workspace: RunWorkspace | None = None,
) -> AgentResult:
    # Start with an isolated run workspace for one task execution.
    current_workspace = workspace or create_run_workspace(base_dir)
    observations: list[Observation] = []
    messages = build_messages(task, current_workspace)

    for iteration in range(1, max_iterations + 1):
        # Tool loop: provider-neutral tool_call blocks -> local execution -> tool_result blocks.
        if logger:
            logger("thinking", f"iteration {iteration}/{max_iterations}")

        response = client.complete(messages, tools=AGENT_TOOL_DEFINITIONS)
        assistant_content = normalize_assistant_content(response.content if hasattr(response, "content") else response)
        append_session_event(current_workspace.session_dir, "model", {"iteration": iteration, "content": assistant_content})
        messages.append(ChatMessage(role="assistant", content=assistant_content))

        tool_calls = [block for block in assistant_content if block.get("type") == "tool_call"]
        if not tool_calls:
            text = content_blocks_to_text(assistant_content).strip()
            if text:
                if logger:
                    logger("finished", text)
                return AgentResult(
                    success=True,
                    message=text,
                    run_dir=current_workspace.root,
                    run_id=current_workspace.run_id,
                    iterations=iteration,
                    observations=observations,
                )
            return AgentResult(
                success=False,
                message="Model response did not include text or a tool call.",
                run_dir=current_workspace.root,
                run_id=current_workspace.run_id,
                iterations=iteration,
                observations=observations,
            )

        tool_results: list[ContentBlock] = []
        for block in tool_calls:
            tool_id = str(block.get("id") or "")
            tool_name = str(block.get("name") or "")
            tool_input = block.get("input") or {}
            append_session_event(
                current_workspace.session_dir,
                "tool_call",
                {"iteration": iteration, "id": tool_id, "name": tool_name, "input": tool_input},
            )

            try:
                action = parse_tool_action(tool_name, tool_input)
                log_action(logger, action)
                repeated_list = find_repeated_list_observation(action, observations)
                if repeated_list:
                    observation = ListFilesObservation(
                        kind="list_files",
                        path=repeated_list.path,
                        files=repeated_list.files,
                        total=repeated_list.total,
                        truncated=repeated_list.truncated,
                        message=(
                            f"Already listed {repeated_list.path}: {repeated_list.message} "
                            "Do not call list_files for this path again. Choose a useful tool call or answer directly."
                        ),
                    )
                else:
                    observation = execute_action(current_workspace, action, command_timeout_ms)
            except ActionParseError as error:
                observation = tool_error_observation(tool_name, error)

            observations.append(observation)
            result_payload = to_jsonable(observation)
            append_session_event(
                current_workspace.session_dir,
                "tool_result",
                {"iteration": iteration, "id": tool_id, "name": tool_name, "result": result_payload},
            )
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_call_id": tool_id,
                    "content": json.dumps(result_payload, ensure_ascii=False),
                }
            )

            if observation.kind == "finish":
                if logger:
                    logger("finished", observation.message)
                return AgentResult(
                    success=True,
                    message=observation.message,
                    run_dir=current_workspace.root,
                    run_id=current_workspace.run_id,
                    iterations=iteration,
                    observations=observations,
                )

            if isinstance(observation, RunCommandObservation) and logger:
                ok = observation.result.exit_code == 0 and not observation.result.timed_out
                logger("observed success" if ok else "observed failure", summarize_command(observation.result))

        messages.append(ChatMessage(role="user", content=tool_results))

    # Return failure only after exhausting max iterations without an explicit finish action.
    return AgentResult(
        success=False,
        message=f"Reached iteration limit ({max_iterations}) before finish.",
        run_dir=current_workspace.root,
        run_id=current_workspace.run_id,
        iterations=max_iterations,
        observations=observations,
    )


def summarize(value: str, max_length: int = 500) -> str:
    compact = " ".join(value.split())
    if len(compact) <= max_length:
        return compact
    return f"{compact[:max_length]}..."


def find_repeated_list_observation(action: object, observations: list[Observation]) -> ListFilesObservation | None:
    if getattr(action, "type", None) != "list_files":
        return None

    path = getattr(action, "path", None) or "."
    for observation in reversed(observations):
        if observation.kind == "list_files" and observation.path == path:
            return observation
    return None


def log_action(logger: AgentLogger | None, action: object) -> None:
    if not logger:
        return
    action_type = getattr(action, "type", None)
    if action_type == "list_files":
        logger("listing files", getattr(action, "path", None) or ".")
    elif action_type == "read_file":
        logger("reading file", getattr(action, "path"))
    elif action_type == "search":
        logger("searching", getattr(action, "query"))
    elif action_type == "edit_file":
        logger("editing file", getattr(action, "path"))
    elif action_type == "write_file":
        logger("writing file", getattr(action, "path"))
    elif action_type == "run_command":
        logger("running command", getattr(action, "command"))


def normalize_assistant_content(value: Any) -> list[ContentBlock]:
    if isinstance(value, str):
        return [{"type": "text", "text": value}]
    if isinstance(value, list):
        return [dict(block) for block in value if isinstance(block, dict)]
    return []


def content_blocks_to_text(content: list[ContentBlock]) -> str:
    return "".join(block["text"] for block in content if block.get("type") == "text" and isinstance(block.get("text"), str))


def tool_error_observation(tool_name: str, error: ActionParseError) -> Observation:
    return ToolErrorObservation(kind="tool_error", tool=tool_name or "unknown", message=f"Invalid tool input: {error}")


def summarize_command(result: object) -> str:
    exit_code = getattr(result, "exit_code")
    timed_out = getattr(result, "timed_out")
    output = getattr(result, "stderr") or getattr(result, "stdout") or "(no output)"
    return f"exit={exit_code} timedOut={timed_out} {summarize(output, 300)}"


def append_session_event(session_dir: Path, event_type: str, payload: dict[str, Any]) -> None:
    session_dir.mkdir(parents=True, exist_ok=True)
    event = {"type": event_type, **payload}
    with (session_dir / "events.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(to_jsonable(event), ensure_ascii=False) + "\n")


def to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return to_jsonable(asdict(value))
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    return value
