from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import signal
import subprocess
from threading import Thread
from typing import Any

from .command_safety import get_blocked_command_reason
from .command_sandbox import prepare_command_launch
from .plugin_store import enabled_plugin_manifests
from .plugin_user_config import (
    expand_plugin_user_config_variables,
    plugin_option_environment_name,
    resolve_plugin_user_config,
)
from .workspace_core import RunWorkspace


MAX_STATUS_OUTPUT_BYTES = 64_000
STATUS_COMMAND_TIMEOUT_SECONDS = 1.0


@dataclass(frozen=True)
class ResolvedSubagentStatusLine:
    plugin: str
    command: str
    environment: dict[str, str]
    sensitive_values: tuple[str, ...] = ()


def resolve_subagent_status_line(project_root: Path) -> ResolvedSubagentStatusLine | None:
    selected = [
        manifest
        for manifest in enabled_plugin_manifests(project_root)
        if manifest.subagent_status_line is not None
    ]
    if not selected:
        return None
    if len(selected) > 1:
        names = ", ".join(manifest.name for manifest in selected)
        raise ValueError(f"Multiple enabled plugins define subagentStatusLine: {names}.")
    manifest = selected[0]
    user_config = resolve_plugin_user_config(project_root, manifest)
    plugin_data = project_root / ".vibeagent" / "plugin-data" / manifest.name
    raw_command = manifest.subagent_status_line.command
    command = (
        raw_command.replace("${CLAUDE_PLUGIN_ROOT}", manifest.root.as_posix())
        .replace("${CLAUDE_PLUGIN_DATA}", plugin_data.as_posix())
        .replace("${CLAUDE_PROJECT_DIR}", project_root.as_posix())
    )
    command = expand_plugin_user_config_variables(
        command,
        user_config,
        sensitive="environment",
    )
    return ResolvedSubagentStatusLine(
        plugin=manifest.name,
        command=command,
        environment={
            "CLAUDE_PLUGIN_ROOT": manifest.root.as_posix(),
            "CLAUDE_PLUGIN_DATA": plugin_data.as_posix(),
            "CLAUDE_PROJECT_DIR": project_root.as_posix(),
            **user_config.environment,
        },
        sensitive_values=tuple(
            user_config.environment[plugin_option_environment_name(key)]
            for key in sorted(user_config.sensitive_keys)
            if plugin_option_environment_name(key) in user_config.environment
        ),
    )


def run_subagent_status_line(
    workspace: RunWorkspace,
    config: ResolvedSubagentStatusLine,
    payload: dict[str, object],
) -> dict[str, str]:
    blocked = get_blocked_command_reason(config.command)
    if blocked is not None:
        raise ValueError(f"Command blocked: {blocked}")
    launch = prepare_command_launch(workspace, config.command, workspace.root)
    if launch.error is not None:
        raise ValueError(launch.error)
    environment = dict(launch.environment or os.environ)
    environment.update(config.environment)
    stdin = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    return_code, raw, stderr = _run_bounded_process(
        launch.argv,
        cwd=workspace.root,
        environment=environment,
        stdin=stdin,
    )
    if return_code != 0:
        detail = _redact_values(
            stderr[:2_000].decode("utf-8", errors="replace").strip(),
            config.sensitive_values,
        )
        suffix = f": {detail}" if detail else ""
        raise ValueError(f"subagentStatusLine command exited with {return_code}{suffix}")
    if len(raw) > MAX_STATUS_OUTPUT_BYTES:
        raise ValueError("subagentStatusLine output exceeded 64000 bytes.")
    return _parse_status_rows(raw)


def _run_bounded_process(
    argv: tuple[str, ...],
    *,
    cwd: Path,
    environment: dict[str, str],
    stdin: bytes,
) -> tuple[int, bytes, bytes]:
    process = subprocess.Popen(
        argv,
        cwd=cwd,
        env=environment,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    stdout = bytearray()
    stderr = bytearray()

    def drain(stream, target: bytearray) -> None:
        try:
            while chunk := stream.read(8_192):
                remaining = MAX_STATUS_OUTPUT_BYTES + 1 - len(target)
                if remaining > 0:
                    target.extend(chunk[:remaining])
        finally:
            stream.close()

    readers = (
        Thread(target=drain, args=(process.stdout, stdout), daemon=True),
        Thread(target=drain, args=(process.stderr, stderr), daemon=True),
    )
    for reader in readers:
        reader.start()
    try:
        if process.stdin is not None:
            try:
                process.stdin.write(stdin)
                process.stdin.close()
            except BrokenPipeError:
                pass
        process.wait(timeout=STATUS_COMMAND_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired as error:
        _kill_process_group(process)
        process.wait()
        raise ValueError("subagentStatusLine command timed out.") from error
    finally:
        _kill_process_group(process)
        for reader in readers:
            reader.join(timeout=0.5)
    return process.returncode, bytes(stdout), bytes(stderr)


def _kill_process_group(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        return
    except PermissionError:
        if process.poll() is None:
            process.kill()


def _parse_status_rows(raw: bytes) -> dict[str, str]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("subagentStatusLine output must be valid UTF-8.") from error
    rows: dict[str, str] = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            value: Any = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"subagentStatusLine output is not JSONL: {error}") from error
        if not isinstance(value, dict) or not isinstance(value.get("id"), str):
            raise ValueError("subagentStatusLine rows must contain string id and content fields.")
        content = value.get("content")
        if not isinstance(content, str):
            raise ValueError("subagentStatusLine rows must contain string id and content fields.")
        rows[value["id"]] = content
    return rows


def _redact_values(text: str, values: tuple[str, ...]) -> str:
    for value in values:
        if value:
            text = text.replace(value, "[REDACTED]")
    return text


__all__ = [
    "ResolvedSubagentStatusLine",
    "resolve_subagent_status_line",
    "run_subagent_status_line",
]
