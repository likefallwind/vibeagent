from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from vibeagent.agent_runtime_utils import append_session_event
from vibeagent.cli_interactive_session_management import (
    interactive_session_prompt,
    run_interactive_session_management,
)
from vibeagent.command_types import LocalCommand
from vibeagent.session_names import read_session_name


class CliInteractiveSessionManagementTests(unittest.TestCase):
    def test_rename_creates_pending_session_and_export_stays_local(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-session-management-") as base:
            root = Path(base)
            renamed = run_interactive_session_management(
                LocalCommand(type="rename", argument="auth-refactor"),
                project_root=root,
                run_id=None,
                pending_workspace=None,
            )
            self.assertIsNotNone(renamed)
            self.assertIsNotNone(renamed.pending_workspace)  # type: ignore[union-attr]
            workspace = renamed.pending_workspace  # type: ignore[union-attr]
            append_session_event(workspace.session_dir, "task", {"task": "implement auth"})

            exported = run_interactive_session_management(
                LocalCommand(type="export", argument="session.txt"),
                project_root=root,
                run_id=renamed.run_id,  # type: ignore[union-attr]
                pending_workspace=workspace,
            )

            self.assertEqual(read_session_name(root, workspace.run_id), "auth-refactor")
            self.assertEqual(
                interactive_session_prompt(root, renamed.run_id, workspace),  # type: ignore[union-attr]
                "\nvibeagent[auth-refactor]> ",
            )
            self.assertIn("Session renamed: auth-refactor", renamed.text)  # type: ignore[union-attr]
            self.assertIn("Exported safe session transcript", exported.text)  # type: ignore[union-attr]
            self.assertIn("implement auth", (root / "session.txt").read_text(encoding="utf-8"))

    def test_export_without_session_and_invalid_filename_are_errors(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-session-management-") as base:
            root = Path(base)
            missing = run_interactive_session_management(
                LocalCommand(type="export"),
                project_root=root,
                run_id=None,
                pending_workspace=None,
            )
            invalid = run_interactive_session_management(
                LocalCommand(type="export", argument="one two"),
                project_root=root,
                run_id="run-1",
                pending_workspace=None,
            )

            self.assertIn("no active coding session", missing.text)  # type: ignore[union-attr]
            self.assertEqual(invalid.text, "Usage: /export [filename]")  # type: ignore[union-attr]


if __name__ == "__main__":
    unittest.main()
