from __future__ import annotations

import argparse
from pathlib import Path

from .cli_config import resolve_project_root
from .cli_local_result import emit_local_result
from .cli_output import print_error_result
from .local_command_workspace import local_command_workspace
from .process_runtime import start_background_command


def launch_background_exec_from_cli(args: argparse.Namespace) -> int:
    root = resolve_project_root(args.cwd) or Path.cwd().resolve()
    command = args.exec_command.strip()
    workspace = local_command_workspace(root, "cli-background-exec")
    observation = start_background_command(
        workspace,
        command,
    )
    if not observation.ok:
        return print_error_result(
            observation.message,
            args.json,
            exit_code=1,
            output_format=args.output_format,
        )

    process_id = observation.process_id
    text = "\n".join(
        [
            f"Background job started: {process_id}",
            f"  pid: {observation.pid}",
            f"  cwd: {observation.cwd}",
            f"  output: vibeagent --process-output {process_id}",
            f"  wait: vibeagent --wait-process {process_id}",
            f"  input: vibeagent --write-process {process_id} --write-stdin TEXT",
            f"  stop: vibeagent --stop-process {process_id}",
        ]
    )
    return emit_local_result(
        args,
        text,
        {
            "backgroundJob": {
                "processId": process_id,
                "pid": observation.pid,
                "command": observation.command,
                "cwd": observation.cwd,
                "running": True,
                "status": "running",
                "stdoutPath": observation.stdout_path,
                "stderrPath": observation.stderr_path,
                "sandboxed": observation.sandboxed,
                "sandboxWarning": observation.sandbox_warning,
                "message": observation.message,
            }
        },
    )


__all__ = ["launch_background_exec_from_cli"]
