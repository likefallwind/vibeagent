from __future__ import annotations

import json
from pathlib import Path
import stat
import tempfile
import unittest

from vibeagent.plugin_scope_settings import (
    effective_plugin_enabled,
    restore_plugin_settings,
    validate_plugin_scope,
    write_plugin_enabled_setting,
)


class PluginScopeSettingsTests(unittest.TestCase):
    def test_scope_writes_preserve_unknown_settings_and_file_modes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-scope-") as base:
            root = Path(base)
            settings_dir = root / ".claude"
            settings_dir.mkdir()
            project_path = settings_dir / "settings.json"
            project_path.write_text(
                json.dumps({"permissions": {"allow": ["Read"]}}),
                encoding="utf-8",
            )
            project_path.chmod(0o640)

            project_snapshot = write_plugin_enabled_setting(
                root,
                "project",
                "review@team-tools",
                True,
            )
            local_snapshot = write_plugin_enabled_setting(
                root,
                "local",
                "review@team-tools",
                False,
            )

            project = json.loads(project_path.read_text(encoding="utf-8"))
            local_path = settings_dir / "settings.local.json"
            local = json.loads(local_path.read_text(encoding="utf-8"))
            self.assertEqual(project["permissions"], {"allow": ["Read"]})
            self.assertTrue(project["enabledPlugins"]["review@team-tools"])
            self.assertFalse(local["enabledPlugins"]["review@team-tools"])
            self.assertEqual(stat.S_IMODE(project_path.stat().st_mode), 0o640)
            self.assertEqual(stat.S_IMODE(local_path.stat().st_mode), 0o600)
            self.assertFalse(
                effective_plugin_enabled(root, "review@team-tools", fallback=True)
            )

            restore_plugin_settings(local_snapshot)
            restore_plugin_settings(project_snapshot)
            self.assertFalse(local_path.exists())
            self.assertEqual(
                json.loads(project_path.read_text(encoding="utf-8")),
                {"permissions": {"allow": ["Read"]}},
            )

    def test_remove_one_setting_keeps_other_plugins_and_precedence(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-scope-") as base:
            root = Path(base)
            write_plugin_enabled_setting(root, "project", "review@team", True)
            write_plugin_enabled_setting(root, "project", "format@team", True)
            write_plugin_enabled_setting(root, "local", "review@team", False)

            write_plugin_enabled_setting(root, "local", "review@team", None)
            write_plugin_enabled_setting(root, "project", "review@team", None)

            project = json.loads(
                root.joinpath(".claude/settings.json").read_text(encoding="utf-8")
            )
            self.assertEqual(project["enabledPlugins"], {"format@team": True})
            self.assertTrue(effective_plugin_enabled(root, "review@team", fallback=True))

    def test_invalid_settings_and_symlinks_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-scope-") as base:
            root = Path(base)
            settings_dir = root / ".claude"
            settings_dir.mkdir()
            settings = settings_dir / "settings.json"
            settings.write_text('{"enabledPlugins":{"review@team":"yes"}}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "map names to booleans"):
                effective_plugin_enabled(root, "review@team", fallback=False)

            settings.unlink()
            outside = root / "outside.json"
            outside.write_text("{}", encoding="utf-8")
            settings.symlink_to(outside)
            with self.assertRaisesRegex(ValueError, "non-symlink"):
                write_plugin_enabled_setting(root, "project", "review@team", True)

        self.assertEqual(validate_plugin_scope("user"), "user")
        with self.assertRaisesRegex(ValueError, "local, project, or user"):
            validate_plugin_scope("machine")


if __name__ == "__main__":
    unittest.main()
