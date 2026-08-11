from __future__ import annotations

import io
import os
from contextlib import redirect_stdout
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from vibeagent.cli_interactive import run_interactive_loop


class CliDynamicWorkflowTests(unittest.TestCase):
    def test_listing_workflows_does_not_initialize_model_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-workflow-") as base:
            root = Path(base)
            create_client = Mock(return_value=object())
            inputs = iter(["/workflows", "/exit"])
            stdout = io.StringIO()
            old_cwd = Path.cwd()
            try:
                os.chdir(root)
                with (
                    patch("vibeagent.cli_interactive.prompt_project_permission_trust", return_value=False),
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
            self.assertIn("No workflows found.", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
