from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import json
import tempfile
import unittest
from unittest.mock import patch

from vibeagent.cli import main
from vibeagent.cli_args import parse_args


class AutoModeCliTests(unittest.TestCase):
    def test_official_style_commands_normalize_to_local_flags(self) -> None:
        defaults = parse_args(["auto-mode", "defaults", "--label", "workspace"])
        config = parse_args(["auto-mode", "config"])
        self.assertTrue(defaults.auto_mode_defaults)
        self.assertEqual(defaults.auto_mode_label, "workspace")
        self.assertTrue(config.auto_mode_config)

    def test_defaults_is_provider_free_and_supports_json(self) -> None:
        output = StringIO()
        with patch("vibeagent.cli_local_flag_runner.build_provider_env", side_effect=AssertionError):
            with redirect_stdout(output):
                exit_code = main(["auto-mode", "defaults", "--json"])
        payload = json.loads(output.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertIn("autoModeDefaults", payload)
        self.assertTrue(payload["autoModeDefaults"]["hard_deny"])

    def test_config_ignores_project_auto_mode_and_accepts_cli_settings(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-auto-cli-") as base:
            output = StringIO()
            settings = json.dumps(
                {"autoMode": {"allow": ["cli-only: permitted"], "classifyAllShell": True}}
            )
            with redirect_stdout(output):
                exit_code = main(
                    [
                        "auto-mode", "config",
                        "--cwd", base,
                        "--settings", settings,
                        "--json",
                    ]
                )
        payload = json.loads(output.getvalue())["autoModeConfig"]
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["allow"], ["cli-only: permitted"])
        self.assertTrue(payload["classifyAllShell"])
        self.assertEqual(payload["sources"], ["CLI --settings"])


if __name__ == "__main__":
    unittest.main()
