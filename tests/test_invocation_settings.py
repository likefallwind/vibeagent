from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from vibeagent.cli_args import parse_args
from vibeagent.cli_config import build_provider_env
from vibeagent.cli_one_shot_input import build_one_shot_kwargs_from_args
from vibeagent.interactive_background import create_interactive_background_request
from vibeagent.invocation_settings import parse_invocation_settings, parse_setting_sources
from vibeagent.main_agent_settings import resolve_main_agent_selection
from vibeagent.plugin_scope_settings import effective_plugin_enabled
from vibeagent.plugin_user_config_store import read_plugin_configured_values
from vibeagent.workspace_core import create_local_workspace
from vibeagent.workspace_environment import read_workspace_environment


class InvocationSettingsTests(unittest.TestCase):
    def test_parses_inline_and_relative_file_settings_to_canonical_json(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "settings.json").write_text('{"env": {"B": "2", "A": "1"}}', encoding="utf-8")

            inline = parse_invocation_settings('{ "env": {"A": "1"} }', root)
            from_file = parse_invocation_settings("settings.json", root)

        self.assertEqual(inline, '{"env":{"A":"1"}}')
        self.assertEqual(from_file, '{"env":{"A":"1","B":"2"}}')

    def test_rejects_invalid_setting_sources_and_non_object_settings(self) -> None:
        self.assertEqual(parse_setting_sources("local,user,user"), ("user", "local"))
        self.assertEqual(parse_setting_sources(""), ())
        with self.assertRaisesRegex(ValueError, "invalid: machine"):
            parse_setting_sources("user,machine")
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "settings.json").write_text("[]", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "JSON object"):
                parse_invocation_settings("settings.json", root)

    def test_override_wins_and_setting_sources_filter_physical_files(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "project"
            home = Path(temporary) / "home"
            (root / ".claude").mkdir(parents=True)
            (home / ".claude").mkdir(parents=True)
            (home / ".claude/settings.json").write_text(
                json.dumps({"env": {"SOURCE": "user"}}), encoding="utf-8"
            )
            (root / ".claude/settings.json").write_text(
                json.dumps({"env": {"SOURCE": "project"}}), encoding="utf-8"
            )
            (root / ".claude/settings.local.json").write_text(
                json.dumps({"env": {"SOURCE": "local"}}), encoding="utf-8"
            )
            workspace = replace(
                create_local_workspace(
                    root,
                    "settings-test",
                    setting_sources=("user", "local"),
                    settings_override_json='{"env":{"SOURCE":"override"}}',
                ),
                project_config_trusted=True,
            )
            with patch("vibeagent.workspace_settings_sources.user_home", return_value=home):
                loaded = read_workspace_environment(workspace)

        self.assertIsNone(loaded.error)
        self.assertEqual(loaded.variables, {"SOURCE": "override"})
        self.assertEqual(loaded.sources, ("~/.claude/settings.json", ".claude/settings.local.json", "CLI --settings"))

    def test_override_applies_to_agent_and_plugin_settings(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = create_local_workspace(
                root,
                "settings-test",
                setting_sources=(),
                settings_override_json=json.dumps(
                    {
                        "agent": "reviewer",
                        "enabledPlugins": {"demo": True},
                        "pluginConfigs": {"demo": {"options": {"region": "cn"}}},
                    }
                ),
            )

            selection = resolve_main_agent_selection(workspace, None)
            enabled = effective_plugin_enabled(root, "demo", fallback=False, workspace=workspace)
            configured, sources, settings_sources = read_plugin_configured_values(
                root, ("demo",), workspace=workspace
            )

        self.assertEqual(selection.name, "reviewer")
        self.assertEqual(selection.source, "CLI --settings")
        self.assertTrue(enabled)
        self.assertEqual(configured, {"region": "cn"})
        self.assertEqual(sources, {"region": "CLI --settings"})
        self.assertEqual(settings_sources, sources)

    def test_cli_parses_settings_before_one_shot_and_provider_environment(self) -> None:
        args = parse_args(
            [
                "--settings",
                '{"env":{"INVOCATION_SETTINGS_TEST":"settings-value"}}',
                "--setting-sources",
                "local",
                "task",
            ]
        )
        kwargs = build_one_shot_kwargs_from_args(args)
        provider_env = build_provider_env(args, Path.cwd())

        self.assertEqual(kwargs["setting_sources"], ("local",))
        self.assertEqual(
            kwargs["settings_override_json"],
            '{"env":{"INVOCATION_SETTINGS_TEST":"settings-value"}}',
        )
        self.assertEqual(provider_env["INVOCATION_SETTINGS_TEST"], "settings-value")

    def test_interactive_background_forwards_invocation_settings(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            request = create_interactive_background_request(
                root,
                "run-1",
                None,
                approval_policy="ask",
                model=None,
                agent=None,
                dynamic_agent_profiles=(),
                effort=None,
                autocompact_tokens=None,
                system_prompt=None,
                append_system_prompt=None,
                additional_directories=(),
                setting_sources=("project",),
                settings_override_json='{"env":{"A":"1"}}',
            )
            settings_path = root / ".vibeagent/sessions/run-1/invocation-settings.json"
            self.assertEqual(settings_path.read_text(encoding="utf-8"), '{"env":{"A":"1"}}\n')
            self.assertEqual(settings_path.stat().st_mode & 0o777, 0o600)

        self.assertIn("--setting-sources", request.argv)
        self.assertIn("project", request.argv)
        self.assertIn("--settings", request.argv)
        self.assertIn(settings_path.as_posix(), request.argv)


if __name__ == "__main__":
    unittest.main()
