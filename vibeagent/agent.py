from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .actions import ActionParseError, execute_action, parse_model_action
from .prompts import build_messages
from .types import AgentLogger, ChatClient, Observation, RunCommandObservation
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
    max_iterations: int = 5,
    command_timeout_ms: int = 30_000,
    logger: AgentLogger | None = None,
    workspace: RunWorkspace | None = None,
) -> AgentResult:
    current_workspace = workspace or create_run_workspace(base_dir)
    observations: list[Observation] = []

    for iteration in range(1, max_iterations + 1):
        if logger:
            logger("thinking", f"iteration {iteration}/{max_iterations}")

        messages = build_messages(task, current_workspace, observations)
        raw = client.complete(messages)

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
        if action.type == "write_file" and logger:
            logger("writing file", action.path)
        elif action.type == "run_command" and logger:
            logger("running command", action.command)

        observation = execute_action(current_workspace, action, command_timeout_ms)
        observations.append(observation)

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


def summarize_command(result: object) -> str:
    exit_code = getattr(result, "exit_code")
    timed_out = getattr(result, "timed_out")
    output = getattr(result, "stderr") or getattr(result, "stdout") or "(no output)"
    return f"exit={exit_code} timedOut={timed_out} {summarize(output, 300)}"
