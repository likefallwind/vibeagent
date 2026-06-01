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
    EditFileAction,
    EditFileObservation,
    FinishAction,
    FinishObservation,
    ListFilesAction,
    ListFilesObservation,
    ModelActionResponse,
    Observation,
    ReadFileAction,
    ReadFileObservation,
    RunCommandAction,
    RunCommandObservation,
    SearchAction,
    SearchObservation,
    WriteFileAction,
    WriteFileObservation,
)
from .workspace import RunWorkspace, edit_project_file, list_project_files, read_project_file, search_project, write_run_file


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
    raw = strip_markdown_json_fence(raw)
    decoder = json.JSONDecoder()
    return decoder.raw_decode(raw.lstrip())[0]


def strip_markdown_json_fence(raw: str) -> str:
    stripped = raw.strip()
    if not stripped.startswith("```"):
        return raw

    lines = stripped.splitlines()
    if len(lines) < 2 or not lines[0].startswith("```"):
        return raw
    if lines[-1].strip() != "```":
        return raw
    return "\n".join(lines[1:-1])


def execute_action(workspace: RunWorkspace, action: AgentAction, command_timeout_ms: int = 30_000) -> Observation:
    # Dispatch one action at a time; all side effects stay within the given project workspace.
    if isinstance(action, ListFilesAction):
        try:
            files, total = list_project_files(workspace, action.path)
            truncated = len(files) < total
            message = f"Found {total} file(s)."
            if truncated:
                message += f" Showing first {len(files)}."
        except ValueError as error:
            files = []
            total = 0
            truncated = False
            message = str(error)
        return ListFilesObservation(
            kind="list_files",
            path=action.path or ".",
            files=files,
            total=total,
            truncated=truncated,
            message=message,
        )

    if isinstance(action, ReadFileAction):
        try:
            content = read_project_file(workspace, action.path)
            message = f"Read {action.path}."
        except ValueError as error:
            content = ""
            message = str(error)
        return ReadFileObservation(
            kind="read_file",
            path=action.path,
            content=content,
            message=message,
        )

    if isinstance(action, SearchAction):
        try:
            matches = search_project(workspace, action.query)
            message = f"Found {len(matches)} match(es)."
        except ValueError as error:
            matches = []
            message = str(error)
        return SearchObservation(
            kind="search",
            query=action.query,
            matches=matches,
            message=message,
        )

    if isinstance(action, EditFileAction):
        try:
            _, diff = edit_project_file(workspace, action.path, action.old, action.new)
            ok = True
            message = f"Edited {action.path}."
        except ValueError as error:
            diff = ""
            ok = False
            message = str(error)
        return EditFileObservation(
            kind="edit_file",
            path=action.path,
            ok=ok,
            message=message,
            diff=diff,
        )

    if isinstance(action, WriteFileAction):
        try:
            write_run_file(workspace, action.path, action.content)
            return WriteFileObservation(kind="write_file", path=action.path, ok=True, message=f"Wrote {action.path}")
        except ValueError as error:
            return WriteFileObservation(kind="write_file", path=action.path, ok=False, message=str(error))

    if isinstance(action, RunCommandAction):
        blocked = get_blocked_command_reason(action.command)
        if blocked:
            return RunCommandObservation(
                kind="run_command",
                result=CommandResult(
                    command=action.command,
                    exit_code=None,
                    stdout="",
                    stderr=f"Command blocked: {blocked}",
                    timed_out=False,
                    signal=None,
                ),
            )
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
    if action_type == "list_files":
        path = value.get("path")
        if path is not None and not isinstance(path, str):
            raise ActionParseError("list_files action path must be a string when provided.", raw)
        return ListFilesAction(type="list_files", path=path)

    if action_type == "read_file":
        path = value.get("path")
        if not isinstance(path, str):
            raise ActionParseError("read_file action requires a string path.", raw)
        return ReadFileAction(type="read_file", path=path)

    if action_type == "search":
        query = value.get("query")
        if not isinstance(query, str) or not query.strip():
            raise ActionParseError("search action requires a non-empty query.", raw)
        return SearchAction(type="search", query=query)

    if action_type == "edit_file":
        path = value.get("path")
        old = value.get("old")
        new = value.get("new")
        if not isinstance(path, str):
            raise ActionParseError("edit_file action requires a string path.", raw)
        if not isinstance(old, str):
            raise ActionParseError("edit_file action requires string old.", raw)
        if not isinstance(new, str):
            raise ActionParseError("edit_file action requires string new.", raw)
        return EditFileAction(type="edit_file", path=path, old=old, new=new)

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


def get_blocked_command_reason(command: str) -> str | None:
    compact = " ".join(command.strip().split())
    lowered = compact.lower()
    blocked_prefixes = (
        "sudo ",
        "su ",
        "rm -rf /",
        "rm -fr /",
        "rm -rf .",
        "rm -fr .",
        "rm -rf *",
        "rm -fr *",
        "git clean -fd",
        "mkfs",
        "shutdown",
        "reboot",
    )
    if lowered.startswith(blocked_prefixes):
        return "high-risk command requires an explicit user-controlled approval flow"
    if " curl " in f" {lowered} " and " | sh" in lowered:
        return "network script piping is not allowed in project mode"
    if " wget " in f" {lowered} " and " | sh" in lowered:
        return "network script piping is not allowed in project mode"
    return None


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
