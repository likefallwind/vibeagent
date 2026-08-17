from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from vibeagent.autocompact_settings import (
    AUTOCOMPACT_ENV,
    AutocompactSetting,
    resolve_autocompact_setting,
    run_autocompact_command,
)
from vibeagent.workspace_core import create_local_workspace


class AutocompactSettingsTests(unittest.TestCase):
    def test_resolves_settings_cli_and_environment_precedence(self) -> None:
        with TemporaryDirectory(prefix="vibeagent-autocompact-settings-") as base:
            root = Path(base) / "project"
            home = Path(base) / "home"
            (root / ".claude").mkdir(parents=True)
            (home / ".claude").mkdir(parents=True)
            (home / ".claude/settings.json").write_text(
                '{"autoCompactWindow": 200000}', encoding="utf-8"
            )
            (root / ".claude/settings.json").write_text(
                '{"autoCompactWindow": "300k"}', encoding="utf-8"
            )
            workspace = create_local_workspace(root, "settings")
            with patch("vibeagent.workspace_settings_sources.user_home", return_value=home):
                configured = resolve_autocompact_setting(workspace, environment={})
                cli = resolve_autocompact_setting(
                    workspace,
                    cli_value=400_000,
                    cli_provided=True,
                    environment={},
                )
                automatic = resolve_autocompact_setting(
                    workspace,
                    cli_value=0,
                    cli_provided=True,
                    environment={},
                )
                environment = resolve_autocompact_setting(
                    workspace,
                    cli_value=400_000,
                    cli_provided=True,
                    environment={AUTOCOMPACT_ENV: "500000"},
                )

        self.assertEqual(configured.tokens, 300_000)
        self.assertEqual(configured.source, ".claude/settings.json")
        self.assertEqual(cli.tokens, 400_000)
        self.assertEqual(cli.source, "CLI --autocompact")
        self.assertIsNone(automatic.tokens)
        self.assertEqual(automatic.source, "CLI --autocompact")
        self.assertEqual(environment.tokens, 500_000)
        self.assertTrue(environment.locked)

    def test_environment_requires_a_plain_in_range_token_count(self) -> None:
        with TemporaryDirectory(prefix="vibeagent-autocompact-env-") as base:
            workspace = create_local_workspace(Path(base), "settings", setting_sources=())
            for value in ("500k", "auto", "99999", "1000001"):
                with self.subTest(value=value), self.assertRaisesRegex(
                    ValueError, AUTOCOMPACT_ENV
                ):
                    resolve_autocompact_setting(
                        workspace,
                        environment={AUTOCOMPACT_ENV: value},
                    )

    def test_command_persists_user_value_but_reports_higher_override(self) -> None:
        with TemporaryDirectory(prefix="vibeagent-autocompact-command-") as base:
            root = Path(base) / "project"
            home = Path(base) / "home"
            root.mkdir(parents=True)
            workspace = create_local_workspace(
                root,
                "settings",
                setting_sources=(),
                settings_override_json='{"autoCompactWindow":400000}',
            )
            with patch("vibeagent.autocompact_settings.user_home", return_value=home):
                result = run_autocompact_command(
                    workspace,
                    "300k",
                    current=AutocompactSetting(),
                    environment={},
                )
            saved = json.loads((home / ".claude/settings.json").read_text(encoding="utf-8"))

        self.assertEqual(saved["autoCompactWindow"], 300_000)
        self.assertEqual(result.setting.tokens, 400_000)
        self.assertEqual(result.setting.source, "CLI --settings")
        self.assertIn("higher-priority settings scope", result.text)

    def test_command_auto_removes_saved_value_without_discarding_other_settings(self) -> None:
        with TemporaryDirectory(prefix="vibeagent-autocompact-auto-") as base:
            root = Path(base) / "project"
            home = Path(base) / "home"
            root.mkdir(parents=True)
            settings = home / ".claude/settings.json"
            settings.parent.mkdir(parents=True)
            settings.write_text(
                '{"autoCompactWindow":200000,"model":"opus"}', encoding="utf-8"
            )
            workspace = create_local_workspace(root, "settings", setting_sources=())
            with patch("vibeagent.autocompact_settings.user_home", return_value=home):
                result = run_autocompact_command(
                    workspace,
                    "auto",
                    current=AutocompactSetting(tokens=200_000),
                    environment={},
                )
            saved = json.loads(settings.read_text(encoding="utf-8"))

        self.assertEqual(saved, {"model": "opus"})
        self.assertIsNone(result.setting.tokens)
        self.assertIn("saved: auto", result.text)

    def test_command_saves_while_environment_keeps_session_locked(self) -> None:
        with TemporaryDirectory(prefix="vibeagent-autocompact-locked-") as base:
            root = Path(base) / "project"
            home = Path(base) / "home"
            root.mkdir(parents=True)
            workspace = create_local_workspace(root, "settings", setting_sources=())
            with patch("vibeagent.autocompact_settings.user_home", return_value=home):
                result = run_autocompact_command(
                    workspace,
                    "300k",
                    current=AutocompactSetting(
                        tokens=500_000,
                        source=AUTOCOMPACT_ENV,
                        locked=True,
                    ),
                    environment={AUTOCOMPACT_ENV: "500000"},
                )

        self.assertEqual(result.setting.tokens, 500_000)
        self.assertTrue(result.setting.locked)
        self.assertIn("controls this session", result.text)


if __name__ == "__main__":
    unittest.main()
