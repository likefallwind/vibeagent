from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from vibeagent.cli_args import parse_args
from vibeagent.cli_validation import validate_cli_args
from vibeagent.cli_startup_context import resolve_interactive_startup_context
from vibeagent.workspace_core import create_run_workspace
from vibeagent.workspace_teammate_mode import resolve_teammate_mode


class TeammateModeTests(unittest.TestCase):
    def test_cli_accepts_in_process_and_auto_but_rejects_unimplemented_split_panes(self) -> None:
        in_process = parse_args(["--teammate-mode", "in-process", "inspect"])
        automatic = parse_args(["--teammate-mode", "auto"])
        tmux = parse_args(["--teammate-mode", "tmux", "inspect"])
        iterm2 = parse_args(["--teammate-mode", "iterm2", "inspect"])
        local = parse_args(["--teammate-mode", "auto", "--status"])

        self.assertIsNone(validate_cli_args(in_process))
        self.assertIsNone(validate_cli_args(automatic))
        self.assertIn("not available yet", validate_cli_args(tmux) or "")
        self.assertIn("not available yet", validate_cli_args(iterm2) or "")
        self.assertIn("coding session", validate_cli_args(local) or "")

        with tempfile.TemporaryDirectory(prefix="vibeagent-teammate-mode-") as base:
            args = parse_args(["--cwd", base, "--teammate-mode", "auto"])
            context = resolve_interactive_startup_context(args, Path(base))
        self.assertEqual(context.teammate_mode, "auto")

    def test_settings_and_auto_resolve_to_in_process(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-teammate-mode-") as base:
            root = Path(base)
            project_settings = root / ".claude" / "settings.json"
            project_settings.parent.mkdir()
            project_settings.write_text('{"teammateMode":"auto"}', encoding="utf-8")
            workspace = create_run_workspace(root, "mode-test")

            self.assertEqual(resolve_teammate_mode(workspace), "in-process")
            self.assertEqual(resolve_teammate_mode(workspace, explicit="in-process"), "in-process")

    def test_invalid_or_split_pane_setting_fails_before_use(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-teammate-mode-") as base:
            root = Path(base)
            settings = root / ".claude" / "settings.json"
            settings.parent.mkdir()
            settings.write_text('{"teammateMode":"tmux"}', encoding="utf-8")
            workspace = create_run_workspace(root, "mode-test")
            with self.assertRaisesRegex(ValueError, "not available yet"):
                resolve_teammate_mode(workspace)

            settings.write_text('{"teammateMode":"invalid"}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "must be"):
                resolve_teammate_mode(workspace)


if __name__ == "__main__":
    unittest.main()
