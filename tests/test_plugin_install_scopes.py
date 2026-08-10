from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tests.test_plugins import write_demo_marketplace
from vibeagent.marketplace_store import add_marketplace, remove_marketplace
from vibeagent.plugin_commands import handle_plugin_command
from vibeagent.plugin_state import read_plugin_state
from vibeagent.plugin_store import list_installed_plugins
from vibeagent.workspace_core import create_run_workspace
from vibeagent.workspace_skills import read_project_skills


class PluginInstallScopeTests(unittest.TestCase):
    def test_project_and_local_scopes_follow_settings_precedence(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-scopes-") as base:
            root = Path(base)
            write_demo_marketplace(root)
            add_marketplace(root, "catalog")

            project_install = handle_plugin_command(
                root,
                "install demo-plugin@team-tools --scope project",
            )
            local_install = handle_plugin_command(
                root,
                "install --scope local demo-plugin@team-tools",
            )

            self.assertTrue(project_install.changed)
            self.assertIn("Scope: project", project_install.text)
            self.assertTrue(local_install.changed)
            installed = list_installed_plugins(root)[0]
            self.assertEqual(installed.scopes, ("local", "project"))
            project = self._settings(root, "settings.json")
            local = self._settings(root, "settings.local.json")
            self.assertTrue(project["enabledPlugins"]["demo-plugin@team-tools"])
            self.assertTrue(local["enabledPlugins"]["demo-plugin@team-tools"])

            disabled = handle_plugin_command(
                root,
                "disable demo-plugin --scope local",
            )
            workspace = create_run_workspace(root, "scope-disabled")
            self.assertIn("local scope", disabled.text)
            self.assertFalse(list_installed_plugins(root)[0].enabled)
            self.assertEqual(read_project_skills(workspace)["skills"], [])

            reinstalled = handle_plugin_command(
                root,
                "install demo-plugin@team-tools --scope local",
            )
            self.assertIn("(disabled)", reinstalled.text)
            self.assertFalse(list_installed_plugins(root)[0].enabled)

            enabled = handle_plugin_command(root, "enable -s local demo-plugin")
            workspace = create_run_workspace(root, "scope-enabled")
            self.assertIn("local scope", enabled.text)
            self.assertTrue(list_installed_plugins(root)[0].enabled)
            self.assertIn(
                "demo-plugin:review",
                [item["name"] for item in read_project_skills(workspace)["skills"]],
            )

    def test_uninstall_one_scope_keeps_cache_until_last_scope(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-scopes-") as base:
            root = Path(base)
            write_demo_marketplace(root)
            add_marketplace(root, "catalog")
            handle_plugin_command(root, "install demo-plugin@team-tools --scope project")
            handle_plugin_command(root, "install demo-plugin@team-tools --scope local")
            cache = root / ".vibeagent/plugins/cache/demo-plugin"

            local_removed = handle_plugin_command(
                root,
                "uninstall demo-plugin --scope local",
            )

            self.assertIn("from local scope", local_removed.text)
            self.assertTrue(cache.is_dir())
            self.assertEqual(list_installed_plugins(root)[0].scopes, ("project",))
            local = self._settings(root, "settings.local.json")
            self.assertNotIn("enabledPlugins", local)
            self.assertTrue(
                self._settings(root, "settings.json")["enabledPlugins"][
                    "demo-plugin@team-tools"
                ]
            )

            project_removed = handle_plugin_command(
                root,
                "uninstall demo-plugin --scope project",
            )

            self.assertIn("from project scope", project_removed.text)
            self.assertFalse(cache.exists())
            self.assertEqual(list_installed_plugins(root), [])
            self.assertNotIn("enabledPlugins", self._settings(root, "settings.json"))

    def test_scoped_install_rolls_settings_and_cache_back_on_state_failure(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-scopes-") as base:
            root = Path(base)
            write_demo_marketplace(root)
            add_marketplace(root, "catalog")

            with patch("vibeagent.plugin_store._write_state", side_effect=OSError("disk full")):
                result = handle_plugin_command(
                    root,
                    "install demo-plugin@team-tools --scope project",
                )

            self.assertIn("disk full", result.text)
            self.assertFalse(root.joinpath(".vibeagent/plugins/cache/demo-plugin").exists())
            self.assertNotIn("enabledPlugins", self._settings(root, "settings.json"))
            self.assertEqual(read_plugin_state(root)["plugins"], {})

    def test_scoped_uninstall_rolls_settings_and_cache_back_on_state_failure(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-scopes-") as base:
            root = Path(base)
            write_demo_marketplace(root)
            add_marketplace(root, "catalog")
            handle_plugin_command(root, "install demo-plugin@team-tools --scope project")
            cache = root / ".vibeagent/plugins/cache/demo-plugin"

            with patch("vibeagent.plugin_store._write_state", side_effect=OSError("disk full")):
                result = handle_plugin_command(
                    root,
                    "uninstall demo-plugin --scope project",
                )

            self.assertIn("disk full", result.text)
            self.assertTrue(cache.is_dir())
            self.assertTrue(
                self._settings(root, "settings.json")["enabledPlugins"][
                    "demo-plugin@team-tools"
                ]
            )
            self.assertEqual(list_installed_plugins(root)[0].scopes, ("project",))

    def test_marketplace_removal_clears_scoped_settings_atomically(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-scopes-") as base:
            root = Path(base)
            write_demo_marketplace(root)
            add_marketplace(root, "catalog")
            handle_plugin_command(root, "install demo-plugin@team-tools --scope project")
            handle_plugin_command(root, "install demo-plugin@team-tools --scope local")

            remove_marketplace(root, "team-tools")

            self.assertEqual(list_installed_plugins(root), [])
            self.assertNotIn("enabledPlugins", self._settings(root, "settings.json"))
            self.assertNotIn("enabledPlugins", self._settings(root, "settings.local.json"))

    def test_marketplace_removal_restores_scoped_settings_on_state_failure(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-scopes-") as base:
            root = Path(base)
            write_demo_marketplace(root)
            add_marketplace(root, "catalog")
            handle_plugin_command(root, "install demo-plugin@team-tools --scope project")
            plugin_cache = root / ".vibeagent/plugins/cache/demo-plugin"
            marketplace_cache = root / ".vibeagent/plugins/marketplaces/team-tools"

            with patch(
                "vibeagent.marketplace_state_ops._write_state",
                side_effect=OSError("disk full"),
            ):
                with self.assertRaisesRegex(OSError, "disk full"):
                    remove_marketplace(root, "team-tools")

            self.assertTrue(plugin_cache.is_dir())
            self.assertTrue(marketplace_cache.is_dir())
            self.assertTrue(
                self._settings(root, "settings.json")["enabledPlugins"][
                    "demo-plugin@team-tools"
                ]
            )

    def test_scope_commands_reject_missing_or_unknown_scope(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-scopes-") as base:
            root = Path(base)
            write_demo_marketplace(root)
            add_marketplace(root, "catalog")
            invalid = handle_plugin_command(
                root,
                "install demo-plugin@team-tools --scope user",
            )
            self.assertIn("scope must be local or project", invalid.text)

            handle_plugin_command(root, "install demo-plugin@team-tools --scope project")
            missing = handle_plugin_command(root, "disable demo-plugin --scope local")
            self.assertIn("not installed at local scope", missing.text)
            ambiguous = handle_plugin_command(root, "disable demo-plugin")
            self.assertIn("specify --scope local or project", ambiguous.text)

    def test_invalid_scope_state_is_reported_without_crashing_list(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-scopes-") as base:
            root = Path(base)
            write_demo_marketplace(root)
            add_marketplace(root, "catalog")
            handle_plugin_command(root, "install demo-plugin@team-tools --scope project")
            state_path = root / ".vibeagent/plugins/installed.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["plugins"]["demo-plugin"]["scopes"] = {"user": True}
            state_path.write_text(json.dumps(state), encoding="utf-8")

            plugins = list_installed_plugins(root)

            self.assertEqual(len(plugins), 1)
            self.assertIn("scopes must map", plugins[0].error or "")
            self.assertEqual(plugins[0].scopes, ())

    @staticmethod
    def _settings(root: Path, name: str) -> dict[str, object]:
        path = root / ".claude" / name
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
