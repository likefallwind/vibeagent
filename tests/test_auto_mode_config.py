from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from vibeagent.auto_mode_config import (
    DEFAULT_AUTO_MODE_ALLOW,
    get_auto_mode_config_report,
    resolve_auto_mode_config,
)
from vibeagent.workspace_core import create_local_workspace


class AutoModeConfigTests(unittest.TestCase):
    def test_only_user_and_cli_settings_can_configure_auto_mode(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-auto-home-") as home_base:
            with tempfile.TemporaryDirectory(prefix="vibeagent-auto-project-") as project_base:
                home = Path(home_base)
                project = Path(project_base)
                (home / ".claude").mkdir()
                (project / ".claude").mkdir()
                (home / ".claude/settings.json").write_text(
                    json.dumps({"autoMode": {"allow": ["$defaults", "user: trusted"]}}),
                    encoding="utf-8",
                )
                (project / ".claude/settings.json").write_text(
                    json.dumps({"autoMode": {"allow": "project injection"}}),
                    encoding="utf-8",
                )
                workspace = create_local_workspace(
                    project,
                    "test-auto-mode",
                    settings_override_json=json.dumps(
                        {"autoMode": {"allow": ["cli: explicit"], "classifyAllShell": True}}
                    ),
                )
                with patch("vibeagent.workspace_settings_sources.user_home", return_value=home):
                    config = resolve_auto_mode_config(workspace)

        self.assertEqual(config.allow[: len(DEFAULT_AUTO_MODE_ALLOW)], DEFAULT_AUTO_MODE_ALLOW)
        self.assertIn("user: trusted", config.allow)
        self.assertIn("cli: explicit", config.allow)
        self.assertEqual(config.sources, ("~/.claude/settings.json", "CLI --settings"))
        self.assertTrue(config.classify_all_shell)

    def test_section_without_defaults_replaces_builtins(self) -> None:
        report = get_auto_mode_config_report(
            ".",
            setting_sources=(),
            settings_override_json=json.dumps(
                {"autoMode": {"soft_deny": ["custom: review this"]}}
            ),
        )
        self.assertEqual(report["soft_deny"], ["custom: review this"])

    def test_malformed_trusted_config_fails_closed(self) -> None:
        workspace = create_local_workspace(
            ".",
            "test-auto-mode-invalid",
            setting_sources=(),
            settings_override_json=json.dumps(
                {"autoMode": {"allow": "everything"}}
            ),
        )
        with self.assertRaisesRegex(ValueError, "autoMode.allow must be an array"):
            resolve_auto_mode_config(workspace)

    def test_oversized_rule_list_is_rejected(self) -> None:
        workspace = create_local_workspace(
            ".",
            "test-auto-mode-oversized",
            setting_sources=(),
            settings_override_json=json.dumps(
                {"autoMode": {"allow": [f"rule-{index}" for index in range(101)]}}
            ),
        )
        with self.assertRaisesRegex(ValueError, "exceeds 100 rules"):
            resolve_auto_mode_config(workspace)


if __name__ == "__main__":
    unittest.main()
