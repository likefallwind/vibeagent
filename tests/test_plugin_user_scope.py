from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

from tests.test_plugin_updates import bump_plugin
from tests.test_plugins import write_demo_marketplace, write_demo_plugin
from vibeagent.plugin_commands import handle_plugin_command
from vibeagent.plugin_scope_settings import write_plugin_enabled_setting
from vibeagent.plugin_store import (
    list_installed_plugins,
    read_installed_plugin,
    read_installed_plugin_manifest,
)
from vibeagent.plugin_user_config import resolve_plugin_user_config
from vibeagent.mcp_config import read_mcp_server_configs
from vibeagent.workspace_agents import read_project_agent
from vibeagent.workspace_core import create_run_workspace
from vibeagent.workspace_hooks import read_project_hooks
from vibeagent.workspace_prompt_commands import expand_project_prompt_command
from vibeagent.workspace_skills import read_project_skills


class PluginUserScopeTests(unittest.TestCase):
    def test_user_marketplace_plugin_is_discovered_and_updated_across_projects(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-user-scope-") as base:
            root = Path(base)
            home = root / "home"
            project_a = root / "project-a"
            project_b = root / "project-b"
            home.mkdir()
            project_a.mkdir()
            project_b.mkdir()
            marketplace = write_demo_marketplace(project_a)

            with patch.dict(os.environ, {"VIBEAGENT_USER_HOME": str(home)}):
                added = handle_plugin_command(
                    project_a,
                    "marketplace add catalog --scope user",
                )
                installed = handle_plugin_command(
                    project_a,
                    "install demo-plugin@team-tools --scope user",
                )

                self.assertTrue(added.changed)
                self.assertIn("user scope", added.text)
                self.assertTrue(installed.changed)
                self.assertTrue(
                    home.joinpath(".vibeagent/plugins/cache/demo-plugin").is_dir()
                )
                self.assertFalse(
                    project_a.joinpath(".vibeagent/plugins/cache/demo-plugin").exists()
                )
                self.assertEqual(list_installed_plugins(project_b)[0].scopes, ("user",))
                workspace = create_run_workspace(project_b, "user-scope")
                skills = read_project_skills(workspace)
                self.assertIn(
                    "demo-plugin:review",
                    [item["name"] for item in skills["skills"]],
                )
                command = expand_project_prompt_command(
                    project_b,
                    "/demo-plugin:fix parser",
                )
                agent = read_project_agent(workspace, "demo-plugin:reviewer")
                hooks = read_project_hooks(workspace)
                mcp = read_mcp_server_configs(workspace)
                self.assertIsNotNone(command)
                self.assertIn("parser", str(command["prompt"]))  # type: ignore[index]
                self.assertIn("demo-plugin", agent["name"])
                self.assertIsNone(hooks.error)
                self.assertEqual(len(hooks.hooks), 1)
                self.assertEqual([item.name for item in mcp], ["demo-plugin.echo"])

                source = marketplace / "extensions/demo-plugin"
                bump_plugin(source, "1.2.4", "global-update")
                updated = handle_plugin_command(
                    project_b,
                    "update demo-plugin --scope user",
                )

                self.assertTrue(updated.changed)
                self.assertEqual(
                    read_installed_plugin(project_b, "demo-plugin", scope="user").version,
                    "1.2.4",
                )
                cached = home / ".vibeagent/plugins/cache/demo-plugin/skills/review/SKILL.md"
                self.assertIn("global-update", cached.read_text(encoding="utf-8"))

                removed = handle_plugin_command(
                    project_b,
                    "marketplace remove team-tools --scope user",
                )
                self.assertTrue(removed.changed)
                self.assertEqual(list_installed_plugins(project_a), [])
                self.assertFalse(cached.parent.parent.parent.exists())
                settings = json.loads(
                    home.joinpath(".claude/settings.json").read_text(encoding="utf-8")
                )
                self.assertNotIn("enabledPlugins", settings)

    def test_project_plugin_overrides_user_cache_and_settings_precedence_is_local_first(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-user-scope-") as base:
            root = Path(base)
            home = root / "home"
            project = root / "project"
            home.mkdir()
            project.mkdir()
            write_demo_plugin(project)

            with patch.dict(os.environ, {"VIBEAGENT_USER_HOME": str(home)}):
                handle_plugin_command(
                    project,
                    "install extensions/demo-plugin --scope user",
                )
                write_plugin_enabled_setting(
                    project,
                    "project",
                    "demo-plugin",
                    False,
                )
                self.assertFalse(list_installed_plugins(project)[0].enabled)
                write_plugin_enabled_setting(project, "local", "demo-plugin", True)
                self.assertTrue(list_installed_plugins(project)[0].enabled)

                project_source = write_demo_plugin(project / "project-copy")
                manifest_path = project_source / ".claude-plugin/plugin.json"
                payload = json.loads(manifest_path.read_text(encoding="utf-8"))
                payload["version"] = "9.0.0"
                manifest_path.write_text(json.dumps(payload), encoding="utf-8")
                handle_plugin_command(
                    project,
                    "install project-copy/extensions/demo-plugin --scope project",
                )

                selected = list_installed_plugins(project)
                self.assertEqual(len(selected), 1)
                self.assertEqual(selected[0].version, "9.0.0")
                self.assertEqual(selected[0].scopes, ("project",))
                self.assertIn(
                    str(project / ".vibeagent/plugins/cache/demo-plugin"),
                    str(read_installed_plugin_manifest(project, "demo-plugin").root),
                )

    def test_user_configuration_and_credentials_follow_global_plugin(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-user-scope-") as base:
            root = Path(base)
            home = root / "home"
            project_a = root / "project-a"
            project_b = root / "project-b"
            home.mkdir()
            project_a.mkdir()
            project_b.mkdir()
            marketplace = write_demo_marketplace(project_a)
            manifest_path = marketplace / "extensions/demo-plugin/.claude-plugin/plugin.json"
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            payload["userConfig"] = {
                "endpoint": {
                    "type": "string",
                    "title": "Endpoint",
                    "description": "Service endpoint",
                    "required": True,
                },
                "token": {
                    "type": "string",
                    "title": "Token",
                    "description": "Service token",
                    "required": True,
                    "sensitive": True,
                },
            }
            manifest_path.write_text(json.dumps(payload), encoding="utf-8")

            with patch.dict(os.environ, {"VIBEAGENT_USER_HOME": str(home)}):
                handle_plugin_command(project_a, "marketplace add catalog --scope user")
                handle_plugin_command(
                    project_a,
                    "install demo-plugin@team-tools --scope user",
                )
                handle_plugin_command(
                    project_a,
                    "config set demo-plugin endpoint https://api.example --scope user",
                )
                handle_plugin_command(
                    project_a,
                    "config set demo-plugin token secret-token --scope user",
                )
                enabled = handle_plugin_command(
                    project_a,
                    "enable demo-plugin --scope user",
                )
                manifest = read_installed_plugin_manifest(
                    project_b,
                    "demo-plugin",
                    scope="user",
                )
                config = resolve_plugin_user_config(project_b, manifest)

                self.assertTrue(enabled.changed)
                self.assertEqual(config.values["endpoint"], "https://api.example")
                self.assertEqual(config.values["token"], "secret-token")
                settings = home.joinpath(".claude/settings.json").read_text(encoding="utf-8")
                settings_path = home / ".claude/settings.json"
                credentials_path = home / ".vibeagent/plugins/user-config-credentials.json"
                credentials = credentials_path.read_text(encoding="utf-8")
                self.assertNotIn("secret-token", settings)
                self.assertIn("secret-token", credentials)
                self.assertEqual(stat.S_IMODE(settings_path.stat().st_mode), 0o600)
                self.assertEqual(stat.S_IMODE(credentials_path.stat().st_mode), 0o600)


if __name__ == "__main__":
    unittest.main()
