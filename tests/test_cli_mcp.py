from __future__ import annotations

import io
import os
from contextlib import redirect_stdout
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from vibeagent.cli_interactive import run_interactive_loop


class CliMcpTests(unittest.TestCase):
    def test_mcp_lifecycle_commands_do_not_initialize_model_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-mcp-") as base:
            root = Path(base)
            home = root / "home"
            project = root / "project"
            home.mkdir()
            project.mkdir()
            create_client = Mock(return_value=object())
            inputs = iter(
                [
                    "/mcp add-json --scope project demo "
                    "'{\"type\":\"stdio\",\"command\":\"python3\",\"args\":[]}'",
                    "/mcp list",
                    "/mcp get demo",
                    "/mcp remove --scope project demo",
                    "/exit",
                ]
            )
            stdout = io.StringIO()
            old_cwd = Path.cwd()
            try:
                os.chdir(project)
                with (
                    patch.dict(os.environ, {"VIBEAGENT_USER_HOME": str(home)}),
                    patch(
                        "vibeagent.cli_interactive.prompt_project_permission_trust",
                        return_value=False,
                    ),
                    patch("vibeagent.cli_interactive_project_runtime.create_peer_runtime", return_value=None),
                    patch(
                        "vibeagent.cli_interactive.input_with_idle_callback",
                        side_effect=lambda _prompt, _callback, *, input_func: next(inputs),
                    ),
                    redirect_stdout(stdout),
                ):
                    exit_code = run_interactive_loop(
                        command_namespace={},
                        create_chat_client_func=create_client,
                    )
            finally:
                os.chdir(old_cwd)

        self.assertEqual(exit_code, 0)
        create_client.assert_not_called()
        output = stdout.getvalue()
        self.assertIn("Added MCP server demo at project scope.", output)
        self.assertIn("demo [project, stdio]", output)
        self.assertIn("MCP server demo:", output)
        self.assertIn("Removed MCP server demo from project scope.", output)


if __name__ == "__main__":
    unittest.main()
