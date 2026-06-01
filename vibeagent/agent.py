from __future__ import annotations

import json
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any

from .actions import ActionParseError, execute_action, parse_model_action
from .prompts import build_messages
from .types import AgentLogger, ChatClient, ListFilesObservation, Observation, RunCommandObservation
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

    for iteration in range(1, max_iterations + 1):
        # ReAct step: reason -> model action -> tool execution -> observation.
        if logger:
            logger("thinking", f"iteration {iteration}/{max_iterations}")

        messages = build_messages(task, current_workspace, observations)
        raw = client.complete(messages)
        append_session_event(current_workspace.session_dir, "model", {"iteration": iteration, "raw": raw})

        try:
            parsed = parse_model_action(raw)
        except ActionParseError as error:
            return AgentResult(
                success=False,
                message=f"Model output was not valid action JSON: {summarize(error.raw)}",
                run_dir=current_workspace.root,
                run_id=current_workspace.run_id,
                iterations=iteration,
                observations=observations,
            )

        action = parsed.action
        append_session_event(
            current_workspace.session_dir,
            "action",
            {"iteration": iteration, "thought": parsed.thought, "action": to_jsonable(action)},
        )
        if action.type == "list_files" and logger:
            logger("listing files", action.path or ".")
        elif action.type == "read_file" and logger:
            logger("reading file", action.path)
        elif action.type == "search" and logger:
            logger("searching", action.query)
        elif action.type == "edit_file" and logger:
            logger("editing file", action.path)
        elif action.type == "write_file" and logger:
            logger("writing file", action.path)
        elif action.type == "run_command" and logger:
            logger("running command", action.command)

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
                    "Do not call list_files for this path again. Choose write_file, read_file, run_command, or finish."
                ),
            )
        else:
            observation = execute_action(current_workspace, action, command_timeout_ms)
        observations.append(observation)
        append_session_event(
            current_workspace.session_dir,
            "observation",
            {"iteration": iteration, "observation": to_jsonable(observation)},
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
