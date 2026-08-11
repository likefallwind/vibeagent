from __future__ import annotations

import json
from pathlib import Path
import sys

from .background_agent_config import (
    background_agent_config_path,
    read_background_agent_config,
)
from .background_agent_attachment import read_background_agent_attachment
from .background_agent_inbox import next_background_agent_message
from .background_agent_lock import background_agent_transition_lock
from .background_agent_store import write_private_text_atomic


def run_worker(payload_path: Path, *, cli_main_func=None) -> int:
    payload = _consume_payload(payload_path)
    if payload.get("schemaVersion") == 1:
        return _run_legacy_worker(payload, cli_main_func=cli_main_func)
    if payload.get("schemaVersion") != 2:
        raise ValueError("Invalid background agent launch payload.")
    agent_id = payload.get("agentId")
    project_root = payload.get("projectRoot")
    config_path = payload.get("configPath")
    initial_argv = payload.get("initialArgv")
    exit_code_path = payload.get("exitCodePath")
    if (
        not isinstance(agent_id, str)
        or not isinstance(project_root, str)
        or not Path(project_root).is_absolute()
        or not isinstance(config_path, str)
        or (initial_argv is not None and (
            not isinstance(initial_argv, list)
            or any(not isinstance(item, str) for item in initial_argv)
        ))
        or not isinstance(exit_code_path, str)
    ):
        raise ValueError("Invalid background agent launch payload.")
    root = Path(project_root)
    config = read_background_agent_config(root, agent_id)
    if Path(config_path) != config_path_for(config):
        raise ValueError("Invalid background agent config path.")
    cli_main = cli_main_func or _cli_main()
    exit_code = 0
    argv = (
        _with_internal_options(
            list(initial_argv),
            ["--_background-agent-worker-token", config.worker_token],
        )
        if initial_argv is not None
        else None
    )
    active_message_path: Path | None = None
    while True:
        if argv is not None:
            try:
                exit_code = cli_main(argv)
            except Exception as error:
                print(
                    f"Background agent turn failed: {type(error).__name__}: {error}",
                    file=sys.stderr,
                )
                exit_code = 1
            finally:
                if active_message_path is not None:
                    active_message_path.unlink(missing_ok=True)
                    active_message_path = None
        config = read_background_agent_config(root, agent_id)
        with background_agent_transition_lock(root, agent_id):
            if read_background_agent_attachment(root, agent_id) is not None:
                write_private_text_atomic(Path(exit_code_path), f"{exit_code}\n")
                return exit_code
            queued = next_background_agent_message(config)
            if queued is None:
                write_private_text_atomic(Path(exit_code_path), f"{exit_code}\n")
                return exit_code
            active_message_path, _message = queued
            write_private_text_atomic(Path(exit_code_path), "")
        argv = _with_internal_options(
            list(config.base_argv),
            [
                "--_background-agent-followup",
                active_message_path.as_posix(),
                "--_background-agent-worker-token",
                config.worker_token,
            ],
        )


def config_path_for(config) -> Path:
    return background_agent_config_path(config.project_root, config.agent_id)


def _run_legacy_worker(payload: dict[str, object], *, cli_main_func=None) -> int:
    argv = payload.get("argv")
    exit_code_path = payload.get("exitCodePath")
    if (
        not isinstance(argv, list)
        or any(not isinstance(item, str) for item in argv)
        or not isinstance(exit_code_path, str)
    ):
        raise ValueError("Invalid background agent launch payload.")
    cli_main = cli_main_func or _cli_main()

    exit_code = 1
    try:
        exit_code = cli_main(argv)
    finally:
        write_private_text_atomic(Path(exit_code_path), f"{exit_code}\n")
    return exit_code


def _cli_main():
    from .cli import main

    return main


def _with_internal_options(argv: list[str], options: list[str]) -> list[str]:
    try:
        marker = argv.index("--")
    except ValueError:
        marker = len(argv)
    return [*argv[:marker], *options, *argv[marker:]]


def _consume_payload(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    finally:
        path.unlink(missing_ok=True)
    if not isinstance(payload, dict):
        raise ValueError("Invalid background agent launch payload.")
    return payload


def main(argv: list[str] | None = None) -> int:
    values = list(sys.argv[1:] if argv is None else argv)
    if len(values) != 1:
        print("Usage: python -m vibeagent.background_agent_worker <payload>", file=sys.stderr)
        return 2
    try:
        return run_worker(Path(values[0]))
    except Exception as error:
        print(f"Background agent worker failed: {type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
