from __future__ import annotations

import json
import os
import signal
import subprocess
from pathlib import Path
from typing import Any

from .types import (
    AgentAction,
    CommandResult,
    FinishAction,
    FinishObservation,
    ModelActionResponse,
    Observation,
    RunCommandAction,
    RunCommandObservation,
    WriteFileAction,
    WriteFileObservation,
)
from .workspace import RunWorkspace, write_run_file


class ActionParseError(ValueError):
    def __init__(self, message: str, raw: str):
        super().__init__(message)
        self.raw = raw


def parse_model_action(raw: str) -> ModelActionResponse:
    # Parse the model's current turn as one typed action payload.
    try:
        parsed = parse_first_json_value(raw)
    except json.JSONDecodeError as error:
        raise ActionParseError(f"Model output was not valid JSON: {error}", raw) from error

    if not isinstance(parsed, dict):
        raise ActionParseError("Model output must be a JSON object.", raw)

    thought = parsed.get("thought")
    if not isinstance(thought, str):
        raise ActionParseError("Model output must include a string thought.", raw)

    action = parse_action(parsed.get("action"), raw)
    return ModelActionResponse(thought=thought, action=action)


def parse_first_json_value(raw: str) -> Any:
    # Be tolerant of model outputs that include multiple JSON objects or leading whitespace.
    decoder = json.JSONDecoder()
    return decoder.raw_decode(raw.lstrip())[0]


def execute_action(workspace: RunWorkspace, action: AgentAction, command_timeout_ms: int = 30_000) -> Observation:
    # Dispatch one action at a time; all side effects stay within the given run workspace.
    if isinstance(action, WriteFileAction):
        write_run_file(workspace, action.path, action.content)
        return WriteFileObservation(kind="write_file", path=action.path, ok=True, message=f"Wrote {action.path}")

    if isinstance(action, RunCommandAction):
        return RunCommandObservation(
            kind="run_command",
            result=run_command(workspace.root, action.command, command_timeout_ms),
        )

    return FinishObservation(kind="finish", message=action.message)


def run_command(cwd: str | Path, command: str, timeout_ms: int = 30_000) -> CommandResult:
    # Run shell command in controlled cwd, capture stdout/stderr, and enforce execution timeout.
    timed_out = False
    process = subprocess.Popen(
        command,
        cwd=Path(cwd),
        shell=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=os.name != "nt",
    )

    try:
        stdout, stderr = process.communicate(timeout=timeout_ms / 1000)
    except subprocess.TimeoutExpired:
        timed_out = True
        _terminate_process(process)
        stdout, stderr = process.communicate()

    return CommandResult(
        command=command,
        exit_code=process.returncode,
        stdout=stdout or "",
        stderr=stderr or "",
        timed_out=timed_out,
        signal=_signal_name(process.returncode) if process.returncode and process.returncode < 0 else None,
    )


def parse_action(value: Any, raw: str) -> AgentAction:
    # Validate action shape against the small, finite action schema.
    if not isinstance(value, dict):
        raise ActionParseError("Model output must include an action object.", raw)

    action_type = value.get("type")
    if action_type == "write_file":
        path = value.get("path")
        content = value.get("content")
        if not isinstance(path, str):
            raise ActionParseError("write_file action requires a string path.", raw)
        if not isinstance(content, str):
            raise ActionParseError("write_file action requires string content.", raw)
        return WriteFileAction(type="write_file", path=path, content=content)

    if action_type == "run_command":
        command = value.get("command")
        if not isinstance(command, str) or not command.strip():
            raise ActionParseError("run_command action requires a non-empty command.", raw)
        return RunCommandAction(type="run_command", command=command)

    if action_type == "finish":
        message = value.get("message")
        if not isinstance(message, str):
            raise ActionParseError("finish action requires a string message.", raw)
        return FinishAction(type="finish", message=message)

    raise ActionParseError("Unsupported action type.", raw)


def _terminate_process(process: subprocess.Popen[str]) -> None:
    try:
        if os.name == "nt":
            process.terminate()
        else:
            os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return

    try:
        process.wait(timeout=0.5)
    except subprocess.TimeoutExpired:
        try:
            if os.name == "nt":
                process.kill()
            else:
                os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            return


def _signal_name(returncode: int) -> str | None:
    try:
        return signal.Signals(-returncode).name
    except ValueError:
        return None
