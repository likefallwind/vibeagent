from __future__ import annotations

import platform
import shutil
import subprocess
import sys

from .bounded_subprocess import run_bounded_subprocess
from .workspace_core import RunWorkspace
from .workspace_git_utils import run_readonly_git


MAX_RUNTIME_TOOL_OUTPUT_CHARS = 4_000


def read_environment_info(workspace: RunWorkspace) -> dict[str, object]:
    tools = [read_runtime_tool_info(name, args) for name, args in runtime_tool_commands()]
    git_probe = run_readonly_git(workspace.root, ["rev-parse", "--is-inside-work-tree"])
    return {
        "project_root": workspace.root.as_posix(),
        "python_version": platform.python_version(),
        "python_executable": sys.executable,
        "platform": f"{platform.system()} {platform.release()} {platform.machine()}".strip(),
        "is_git_repo": git_probe.ok and git_probe.stdout.strip() == "true",
        "tools": tools,
        "message": f"Inspected runtime environment; {sum(1 for tool in tools if tool['available'])}/{len(tools)} tool(s) available.",
    }


def runtime_tool_commands() -> list[tuple[str, list[str]]]:
    return [
        ("python", [sys.executable, "--version"]),
        ("python3", ["python3", "--version"]),
        ("git", ["git", "--version"]),
        ("node", ["node", "--version"]),
        ("npm", ["npm", "--version"]),
        ("pnpm", ["pnpm", "--version"]),
        ("yarn", ["yarn", "--version"]),
        ("uv", ["uv", "--version"]),
        ("pytest", ["pytest", "--version"]),
        ("agent-browser", ["agent-browser", "--version"]),
    ]


def read_runtime_tool_info(name: str, command: list[str]) -> dict[str, object]:
    executable = command[0]
    path = sys.executable if executable == sys.executable else shutil.which(executable)
    if not path:
        return {"name": name, "available": False, "path": None, "version": None, "message": "Not found on PATH."}
    try:
        result = run_bounded_subprocess(
            [path, *command[1:]],
            timeout_ms=2_000,
            max_output_chars=MAX_RUNTIME_TOOL_OUTPUT_CHARS,
            errors="replace",
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"name": name, "available": True, "path": path, "version": None, "message": str(error)}
    version = (result.stdout or result.stderr).strip().splitlines()
    version_text = version[0] if version else ""
    return {
        "name": name,
        "available": result.returncode == 0,
        "path": path,
        "version": version_text or None,
        "message": version_text or f"Exited with {result.returncode}.",
    }
