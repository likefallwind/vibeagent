from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from vibeagent.workspace_core import create_local_workspace
from vibeagent.workspace_shell_response import resolve_respond_to_bash_commands


class WorkspaceShellResponseTests(unittest.TestCase):
    def test_defaults_enabled_and_local_settings_override_project(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-shell-settings-") as base:
            root = Path(base)
            default_workspace = create_local_workspace(
                root,
                "default-settings",
                setting_sources=(),
            )

            self.assertTrue(resolve_respond_to_bash_commands(default_workspace))

            project = root / ".claude" / "settings.json"
            project.parent.mkdir()
            project.write_text(
                '{"respondToBashCommands":true}\n',
                encoding="utf-8",
            )
            local = root / ".claude" / "settings.local.json"
            local.write_text(
                '{"respondToBashCommands":false}\n',
                encoding="utf-8",
            )

            self.assertFalse(
                resolve_respond_to_bash_commands(
                    create_local_workspace(root, "layered-settings")
                )
            )

    def test_rejects_non_boolean_setting(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-shell-settings-") as base:
            root = Path(base)
            settings = root / ".claude" / "settings.json"
            settings.parent.mkdir()
            settings.write_text(
                '{"respondToBashCommands":"yes"}\n',
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "must be true or false"):
                resolve_respond_to_bash_commands(
                    create_local_workspace(root, "settings")
                )


if __name__ == "__main__":
    unittest.main()
