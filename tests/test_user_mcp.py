from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from vibeagent.actions import execute_action
from vibeagent.mcp_config import read_mcp_server_configs
from vibeagent.types import McpCallAction, McpToolsAction
from vibeagent.workspace_core import create_run_workspace


MCP_PROJECT_DIR_SERVER = r'''
import json
import os
import sys

for raw in sys.stdin:
    message = json.loads(raw)
    method = message.get("method")
    if method == "initialize":
        result = {
            "protocolVersion": "2025-11-25",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "user-server", "version": "1.0"},
        }
    elif method == "tools/list":
        result = {
            "tools": [
                {
                    "name": "project_dir",
                    "description": "Return runtime environment",
                    "inputSchema": {"type": "object"},
                }
            ]
        }
    elif method == "tools/call":
        result = {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "project": os.environ.get("CLAUDE_PROJECT_DIR"),
                            "fallback": os.environ.get("MCP_FALLBACK"),
                        },
                        sort_keys=True,
                    ),
                }
            ],
            "isError": False,
        }
    else:
        continue
    print(json.dumps({"jsonrpc": "2.0", "id": message["id"], "result": result}), flush=True)
'''


def _server(command: str) -> dict[str, object]:
    return {"command": command, "args": []}


def _write_user_config(
    home: Path,
    *,
    user_servers: dict[str, object],
    project: Path | None = None,
    local_servers: dict[str, object] | None = None,
) -> None:
    projects: dict[str, object] = {}
    if project is not None:
        projects[project.resolve().as_posix()] = {
            "mcpServers": local_servers or {}
        }
    (home / ".claude.json").write_text(
        json.dumps({"mcpServers": user_servers, "projects": projects}),
        encoding="utf-8",
    )


class UserMcpScopeTests(unittest.TestCase):
    def test_scope_precedence_is_local_project_user(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-user-mcp-") as base:
            root = Path(base)
            home = root / "home"
            project = root / "project"
            other = root / "other"
            home.mkdir()
            project.mkdir()
            other.mkdir()
            _write_user_config(
                home,
                user_servers={
                    "selected": _server("user-command"),
                    "user-only": _server("user-only-command"),
                },
                project=project,
                local_servers={
                    "selected": _server("local-command"),
                    "local-only": _server("local-only-command"),
                },
            )
            (project / ".mcp.json").write_text(
                json.dumps(
                    {
                        "mcpServers": {
                            "selected": _server("project-command"),
                            "project-only": _server("project-only-command"),
                        }
                    }
                ),
                encoding="utf-8",
            )

            with patch.dict(os.environ, {"VIBEAGENT_USER_HOME": str(home)}):
                project_configs = {
                    item.name: item for item in read_mcp_server_configs(
                        create_run_workspace(project, "scoped-project")
                    )
                }
                other_configs = {
                    item.name: item for item in read_mcp_server_configs(
                        create_run_workspace(other, "scoped-other")
                    )
                }

        self.assertEqual(project_configs["selected"].command, "local-command")
        self.assertIn("project-only", project_configs)
        self.assertIn("user-only", project_configs)
        self.assertIn("local-only", project_configs)
        self.assertEqual(other_configs["selected"].command, "user-command")
        self.assertNotIn("project-only", other_configs)
        self.assertNotIn("local-only", other_configs)

    def test_user_stdio_server_runs_across_projects_with_project_directory(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-user-mcp-runtime-") as base:
            root = Path(base)
            home = root / "home"
            first = root / "first"
            second = root / "second"
            home.mkdir()
            first.mkdir()
            second.mkdir()
            server_path = home / "mcp_server.py"
            server_path.write_text(MCP_PROJECT_DIR_SERVER, encoding="utf-8")
            _write_user_config(
                home,
                user_servers={
                    "personal": {
                        "command": sys.executable,
                        "args": [server_path.as_posix()],
                        "env": {"MCP_FALLBACK": "${UNSET_MCP_VALUE:-fallback-value}"},
                    }
                },
            )

            outputs: list[str] = []
            with patch.dict(os.environ, {"VIBEAGENT_USER_HOME": str(home)}):
                for index, project in enumerate((first, second), start=1):
                    result = execute_action(
                        create_run_workspace(project, f"user-mcp-{index}"),
                        McpCallAction(
                            type="mcp_call",
                            server="personal",
                            name="project_dir",
                            arguments={},
                            timeout_ms=2_000,
                        ),
                    )
                    self.assertTrue(result.ok, result.error)
                    outputs.append(result.output)

        self.assertIn(first.as_posix(), outputs[0])
        self.assertIn(second.as_posix(), outputs[1])
        self.assertTrue(all("fallback-value" in output for output in outputs))

    def test_strict_mode_ignores_user_and_local_scopes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-user-mcp-strict-") as base:
            root = Path(base)
            home = root / "home"
            project = root / "project"
            home.mkdir()
            project.mkdir()
            _write_user_config(
                home,
                user_servers={"user": _server("user-command")},
                project=project,
                local_servers={"local": _server("local-command")},
            )

            with patch.dict(os.environ, {"VIBEAGENT_USER_HOME": str(home)}):
                configs = read_mcp_server_configs(
                    create_run_workspace(
                        project,
                        "strict-user-mcp",
                        strict_mcp_config=True,
                    )
                )

        self.assertEqual(configs, [])

    def test_missing_required_environment_variable_fails_without_value_leak(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-user-mcp-env-") as base:
            root = Path(base)
            home = root / "home"
            project = root / "project"
            home.mkdir()
            project.mkdir()
            _write_user_config(
                home,
                user_servers={
                    "broken": {
                        "command": "${MISSING_REQUIRED_MCP_VALUE}",
                        "args": [],
                    }
                },
            )

            with patch.dict(os.environ, {"VIBEAGENT_USER_HOME": str(home)}):
                with self.assertRaisesRegex(
                    ValueError,
                    "MCP environment variable MISSING_REQUIRED_MCP_VALUE is not set",
                ):
                    read_mcp_server_configs(
                        create_run_workspace(project, "missing-user-mcp-env")
                    )

    def test_expanded_stdio_command_still_passes_hard_block_checks(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-user-mcp-block-") as base:
            root = Path(base)
            home = root / "home"
            project = root / "project"
            home.mkdir()
            project.mkdir()
            _write_user_config(
                home,
                user_servers={
                    "blocked": {
                        "command": "${MCP_BLOCKED_COMMAND}",
                        "args": ["--version"],
                    }
                },
            )

            with patch.dict(
                os.environ,
                {
                    "VIBEAGENT_USER_HOME": str(home),
                    "MCP_BLOCKED_COMMAND": "sudo",
                },
            ):
                result = execute_action(
                    create_run_workspace(project, "blocked-user-mcp"),
                    McpToolsAction(type="mcp_tools", server="blocked"),
                )

        self.assertFalse(result.ok)
        self.assertIn("MCP server command is blocked", result.error or "")

    def test_user_config_symbolic_link_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-user-mcp-link-") as base:
            root = Path(base)
            home = root / "home"
            project = root / "project"
            home.mkdir()
            project.mkdir()
            target = root / "claude-target.json"
            target.write_text(json.dumps({"mcpServers": {}}), encoding="utf-8")
            (home / ".claude.json").symlink_to(target)

            with patch.dict(os.environ, {"VIBEAGENT_USER_HOME": str(home)}):
                with self.assertRaisesRegex(ValueError, "symbolic link"):
                    read_mcp_server_configs(
                        create_run_workspace(project, "linked-user-mcp")
                    )


if __name__ == "__main__":
    unittest.main()
