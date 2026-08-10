from __future__ import annotations

import json
import os
from pathlib import Path
import shlex
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

from vibeagent.command_parsing import parse_local_command
from vibeagent.mcp_commands import handle_mcp_command
from vibeagent.mcp_config import read_mcp_server_configs
from vibeagent.mcp_scope_store import read_mcp_scope_servers
from vibeagent.workspace_core import create_run_workspace


class McpCommandTests(unittest.TestCase):
    def test_local_add_list_get_replace_and_remove_preserve_user_config(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-mcp-command-") as base:
            root = Path(base)
            home = root / "home"
            project = root / "project"
            home.mkdir()
            project.mkdir()
            user_config = home / ".claude.json"
            user_config.write_text(
                json.dumps({"theme": "dark", "projects": {}}),
                encoding="utf-8",
            )
            user_config.chmod(0o600)

            with patch.dict(os.environ, {"VIBEAGENT_USER_HOME": str(home)}):
                added = handle_mcp_command(
                    project,
                    f"add --env TOKEN=${{MCP_TOKEN:-fallback}} local-tools -- "
                    f"{shlex.quote(sys.executable)} -m example_server",
                )
                listing = handle_mcp_command(project, "list")
                details = handle_mcp_command(project, "get local-tools")
                duplicate = handle_mcp_command(
                    project,
                    f"add local-tools -- {shlex.quote(sys.executable)} -m other_server",
                )
                replaced = handle_mcp_command(
                    project,
                    f"add --replace local-tools -- {shlex.quote(sys.executable)} -m other_server",
                )
                local_servers = read_mcp_scope_servers(project, "local")
                removed = handle_mcp_command(project, "remove local-tools")

            persisted = json.loads(user_config.read_text(encoding="utf-8"))
            user_config_mode = stat.S_IMODE(user_config.stat().st_mode)

        self.assertTrue(added.changed)
        self.assertIn("local-tools [local, stdio]", listing.text)
        self.assertIn("args: 2", details.text)
        self.assertIn("env: TOKEN", details.text)
        self.assertNotIn("fallback", details.text)
        self.assertIn("already exists", duplicate.text)
        self.assertTrue(replaced.changed)
        self.assertEqual(local_servers["local-tools"]["args"], ["-m", "other_server"])
        self.assertTrue(removed.changed)
        self.assertEqual(persisted["theme"], "dark")
        self.assertNotIn(project.resolve().as_posix(), persisted.get("projects", {}))
        self.assertEqual(user_config_mode, 0o600)

    def test_project_http_add_hides_header_value_and_uses_project_file(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-mcp-command-http-") as base:
            root = Path(base)
            home = root / "home"
            project = root / "project"
            home.mkdir()
            project.mkdir()
            secret = "private-command-token"

            with patch.dict(
                os.environ,
                {
                    "VIBEAGENT_USER_HOME": str(home),
                    "MCP_COMMAND_TOKEN": secret,
                },
            ):
                added = handle_mcp_command(
                    project,
                    "add --transport http --scope project "
                    "--header 'Authorization:Bearer ${MCP_COMMAND_TOKEN}' docs -- "
                    "https://docs.example.com/mcp?token=hidden",
                )
                listing = handle_mcp_command(project, "list")
                details = handle_mcp_command(project, "get docs")

            payload = json.loads(project.joinpath(".mcp.json").read_text(encoding="utf-8"))
            project_config_mode = stat.S_IMODE(project.joinpath(".mcp.json").stat().st_mode)

        self.assertTrue(added.changed)
        self.assertEqual(project_config_mode, 0o644)
        self.assertEqual(
            payload["mcpServers"]["docs"]["headers"]["Authorization"],
            "Bearer ${MCP_COMMAND_TOKEN}",
        )
        self.assertIn("docs [project, http]", listing.text)
        self.assertIn("headers: Authorization", details.text)
        self.assertNotIn(secret, listing.text + details.text)
        self.assertNotIn("token=hidden", details.text)

    def test_user_add_json_is_available_in_another_project(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-mcp-command-user-") as base:
            root = Path(base)
            home = root / "home"
            first = root / "first"
            second = root / "second"
            home.mkdir()
            first.mkdir()
            second.mkdir()
            server = json.dumps(
                {"type": "stdio", "command": sys.executable, "args": ["-m", "shared_server"]},
                separators=(",", ":"),
            )

            with patch.dict(os.environ, {"VIBEAGENT_USER_HOME": str(home)}):
                added = handle_mcp_command(
                    first,
                    f"add-json --scope user shared {shlex.quote(server)}",
                )
                second_configs = read_mcp_server_configs(
                    create_run_workspace(second, "user-command-second")
                )
                removed = handle_mcp_command(second, "remove --scope user shared")

        self.assertTrue(added.changed)
        self.assertEqual([config.name for config in second_configs], ["shared"])
        self.assertEqual(second_configs[0].config_path, "~/.claude.json#mcpServers")
        self.assertTrue(removed.changed)

    def test_invalid_add_and_symlink_leave_configuration_unchanged(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-mcp-command-invalid-") as base:
            root = Path(base)
            home = root / "home"
            project = root / "project"
            home.mkdir()
            project.mkdir()
            target = root / "user-config.json"
            original = json.dumps({"marker": "unchanged"})
            target.write_text(original, encoding="utf-8")
            (home / ".claude.json").symlink_to(target)

            with patch.dict(os.environ, {"VIBEAGENT_USER_HOME": str(home)}):
                invalid = handle_mcp_command(
                    project,
                    "add-json --scope project bad '{\"type\":\"http\",\"url\":\"ftp://bad\"}'",
                )
                linked = handle_mcp_command(
                    project,
                    f"add-json --scope user safe '{{\"command\":{json.dumps(sys.executable)}}}'",
                )
            target_content = target.read_text(encoding="utf-8")

        self.assertIn("must use http or https", invalid.text)
        self.assertFalse(project.joinpath(".mcp.json").exists())
        self.assertIn("non-symlink", linked.text)
        self.assertEqual(target_content, original)

    def test_parser_recognizes_mcp_commands(self) -> None:
        command = parse_local_command("/mcp get docs")

        self.assertIsNotNone(command)
        self.assertEqual(command.type, "mcp")
        self.assertEqual(command.argument, "get docs")

if __name__ == "__main__":
    unittest.main()
