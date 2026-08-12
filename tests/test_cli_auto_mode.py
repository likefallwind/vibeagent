from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from vibeagent.cli import main
from vibeagent.cli_args import parse_args
from vibeagent.types import AssistantResponse


class CliCritiqueClient:
    def complete(self, _messages, **_kwargs):
        return AssistantResponse(
            content=[
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "summary": "One custom rule needs clarification.",
                            "findings": [
                                {
                                    "severity": "medium",
                                    "section": "soft_deny",
                                    "rule": "database: avoid risky migrations",
                                    "issue": "Risky is ambiguous.",
                                    "recommendation": "Name the blocked targets and operations.",
                                }
                            ],
                        }
                    ),
                }
            ],
            raw={},
        )


class AutoModeCliTests(unittest.TestCase):
    def test_official_style_commands_normalize_to_local_flags(self) -> None:
        defaults = parse_args(["auto-mode", "defaults", "--label", "workspace"])
        config = parse_args(["auto-mode", "config"])
        critique = parse_args(["auto-mode", "critique"])
        reset = parse_args(["auto-mode", "reset", "--yes"])
        self.assertTrue(defaults.auto_mode_defaults)
        self.assertEqual(defaults.auto_mode_label, "workspace")
        self.assertTrue(config.auto_mode_config)
        self.assertTrue(critique.auto_mode_critique)
        self.assertTrue(reset.auto_mode_reset)
        self.assertTrue(reset.auto_mode_yes)

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

    def test_reset_json_requires_yes(self) -> None:
        output = StringIO()
        with redirect_stdout(output):
            exit_code = main(["auto-mode", "reset", "--json"])
        self.assertEqual(exit_code, 2)
        self.assertIn("requires --yes", output.getvalue())

    def test_unknown_subcommand_fails_before_provider_loading(self) -> None:
        output = StringIO()
        with patch(
            "vibeagent.cli_local_flag_runner.build_provider_env",
            side_effect=AssertionError("provider must not be loaded"),
        ):
            with redirect_stdout(output):
                exit_code = main(["auto-mode", "unknown"])
        self.assertEqual(exit_code, 2)
        self.assertIn("Unknown auto-mode subcommand", output.getvalue())

    def test_critique_runs_model_and_returns_structured_findings(self) -> None:
        output = StringIO()
        settings = json.dumps(
            {"autoMode": {"soft_deny": ["database: avoid risky migrations"]}}
        )
        with patch(
            "vibeagent.auto_mode_management.create_chat_client",
            return_value=CliCritiqueClient(),
        ):
            with redirect_stdout(output):
                exit_code = main(
                    ["auto-mode", "critique", "--settings", settings, "--json"]
                )
        report = json.loads(output.getvalue())["autoModeCritique"]
        self.assertEqual(exit_code, 0)
        self.assertTrue(report["modelRequested"])
        self.assertEqual(report["findings"][0]["section"], "soft_deny")

    def test_reset_yes_is_provider_free_and_preserves_other_user_settings(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-auto-home-") as base:
            home = Path(base)
            settings = home / ".claude/settings.json"
            settings.parent.mkdir()
            settings.write_text(
                json.dumps({"model": "keep", "autoMode": {"hard_deny": ["custom"]}}),
                encoding="utf-8",
            )
            output = StringIO()
            with patch("vibeagent.auto_mode_management.user_home", return_value=home):
                with patch(
                    "vibeagent.cli_local_flag_runner.build_provider_env",
                    side_effect=AssertionError("provider must not be loaded"),
                ):
                    with redirect_stdout(output):
                        exit_code = main(["auto-mode", "reset", "--yes", "--json"])
            payload = json.loads(settings.read_text(encoding="utf-8"))
        report = json.loads(output.getvalue())["autoModeReset"]
        self.assertEqual(exit_code, 0)
        self.assertTrue(report["changed"])
        self.assertEqual(payload, {"model": "keep"})


if __name__ == "__main__":
    unittest.main()
