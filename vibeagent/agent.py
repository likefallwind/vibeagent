from __future__ import annotations

import json
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any

from .actions import AGENT_TOOL_DEFINITIONS, ActionParseError, execute_action, parse_tool_action
from .prompts import build_messages
from .types import (
    AgentLogger,
    ApprovalDecision,
    ApprovalDeniedObservation,
    ApprovalHandler,
    ApprovalRequest,
    ChatClient,
    ChatMessage,
    ContentBlock,
    EditFileAction,
    FinishAction,
    ListFilesAction,
    ListFilesObservation,
    Observation,
    ReadFileAction,
    RunCommandObservation,
    RunCommandAction,
    SearchAction,
    TaskStep,
    ToolErrorObservation,
    WriteFileAction,
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
    steps: list[TaskStep]


def run_agent(
    task: str,
    client: ChatClient,
    base_dir: str | Path | None = None,
    max_iterations: int = 20,
    command_timeout_ms: int = 30_000,
    logger: AgentLogger | None = None,
    workspace: RunWorkspace | None = None,
    approval_handler: ApprovalHandler | None = None,
) -> AgentResult:
    # Start with an isolated run workspace for one task execution.
    current_workspace = workspace or create_run_workspace(base_dir)
    observations: list[Observation] = []
    steps: list[TaskStep] = []
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
                    steps=steps,
                )
            return AgentResult(
                success=False,
                message="Model response did not include text or a tool call.",
                run_dir=current_workspace.root,
                run_id=current_workspace.run_id,
                iterations=iteration,
                observations=observations,
                steps=steps,
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
                step = start_task_step(current_workspace, steps, iteration, action, logger)
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
                    approval_request = build_approval_request(action)
                    if approval_request:
                        append_session_event(
                            current_workspace.session_dir,
                            "approval_requested",
                            {"iteration": iteration, "step": step, "request": approval_request},
                        )
                        if logger:
                            logger("approval required", summarize_approval_request(approval_request))
                        decision = request_approval(approval_handler, approval_request)
                        append_session_event(
                            current_workspace.session_dir,
                            "approval_decision",
                            {"iteration": iteration, "step": step, "decision": decision},
                        )
                        if logger:
                            status = "approval approved" if decision.approved else "approval denied"
                            logger(status, summarize_approval_decision(approval_request, decision))
                        if not decision.approved:
                            observation = ApprovalDeniedObservation(
                                kind="approval_denied",
                                action_type=approval_request.action_type,
                                target=approval_request.target,
                                message=decision.message or "Action was denied by approval policy.",
                            )
                        else:
                            observation = execute_action(current_workspace, action, command_timeout_ms)
                    else:
                        observation = execute_action(current_workspace, action, command_timeout_ms)
                complete_task_step(current_workspace, step, observation, iteration, logger)
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
                    steps=steps,
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
        steps=steps,
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


def start_task_step(
    workspace: RunWorkspace,
    steps: list[TaskStep],
    iteration: int,
    action: object,
    logger: AgentLogger | None,
) -> TaskStep:
    step = TaskStep(
        id=len(steps) + 1,
        label=build_step_label(action),
        action_type=str(getattr(action, "type", "unknown")),
        target=build_action_target(action),
        status="running",
    )
    steps.append(step)
    append_session_event(workspace.session_dir, "step_started", {"iteration": iteration, "step": step})
    if logger:
        logger("step started", step.label)
    return step


def complete_task_step(
    workspace: RunWorkspace,
    step: TaskStep,
    observation: Observation,
    iteration: int,
    logger: AgentLogger | None,
) -> None:
    if observation.kind == "approval_denied":
        step.status = "denied"
    elif observation_failed(observation):
        step.status = "failed"
    else:
        step.status = "completed"
    step.message = observation_summary(observation)
    append_session_event(workspace.session_dir, "step_completed", {"iteration": iteration, "step": step})
    if logger:
        logger("step completed", f"{step.label} -> {step.status}")


def build_step_label(action: object) -> str:
    if isinstance(action, WriteFileAction):
        return f"Write {action.path}"
    if isinstance(action, EditFileAction):
        return f"Edit {action.path}"
    if isinstance(action, RunCommandAction):
        return f"Run {summarize(action.command, 80)}"
    if isinstance(action, ReadFileAction):
        return f"Read {action.path}"
    if isinstance(action, SearchAction):
        return f"Search {summarize(action.query, 80)}"
    if isinstance(action, ListFilesAction):
        return f"List files {action.path or '.'}"
    if getattr(action, "type", None) == "list_files":
        return f"List files {getattr(action, 'path', None) or '.'}"
    if isinstance(action, FinishAction):
        return "Finish task"
    return str(getattr(action, "type", "Unknown action"))


def build_action_target(action: object) -> str:
    if isinstance(action, (WriteFileAction, EditFileAction, ReadFileAction)):
        return action.path
    if isinstance(action, RunCommandAction):
        return action.command
    if isinstance(action, SearchAction):
        return action.query
    if getattr(action, "type", None) == "list_files":
        return str(getattr(action, "path", None) or ".")
    if isinstance(action, FinishAction):
        return "finish"
    return ""


def build_approval_request(action: object) -> ApprovalRequest | None:
    if isinstance(action, WriteFileAction):
        return ApprovalRequest(
            action_type="write_file",
            target=action.path,
            risk="This will create or replace a file in the active project.",
        )
    if isinstance(action, EditFileAction):
        return ApprovalRequest(
            action_type="edit_file",
            target=action.path,
            risk="This will modify an existing file in the active project.",
        )
    if isinstance(action, RunCommandAction):
        return ApprovalRequest(
            action_type="run_command",
            target=action.command,
            risk="This will run a shell command from the active project directory.",
        )
    return None


def request_approval(handler: ApprovalHandler | None, request: ApprovalRequest) -> ApprovalDecision:
    if handler is None:
        return ApprovalDecision(approved=False, message="No approval handler configured.")
    return handler(request)


def summarize_approval_request(request: ApprovalRequest) -> str:
    return f"{request.action_type} {summarize(request.target, 120)}"


def summarize_approval_decision(request: ApprovalRequest, decision: ApprovalDecision) -> str:
    message = decision.message or ("approved" if decision.approved else "denied")
    return f"{request.action_type} {summarize(request.target, 80)}: {summarize(message, 120)}"


def observation_failed(observation: Observation) -> bool:
    if observation.kind in {"tool_error", "approval_denied"}:
        return True
    if observation.kind == "write_file":
        return not observation.ok
    if observation.kind == "edit_file":
        return not observation.ok
    if observation.kind == "run_command":
        return observation.result.exit_code != 0 or observation.result.timed_out
    if observation.kind == "read_file":
        return not observation.message.startswith("Read ")
    if observation.kind == "search":
        return not observation.message.startswith("Found ")
    if observation.kind == "list_files":
        return not observation.message.startswith(("Found ", "Already listed "))
    return False


def observation_summary(observation: Observation) -> str:
    if observation.kind == "run_command":
        return summarize_command(observation.result)
    return str(getattr(observation, "message", observation.kind))


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
