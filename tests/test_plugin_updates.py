from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from tests.test_plugins import write_demo_marketplace, write_demo_plugin
from vibeagent.marketplace_store import (
    add_local_marketplace,
    install_marketplace_plugin,
    list_installed_marketplaces,
    set_marketplace_auto_update,
)
from vibeagent.plugin_auto_update import (
    PluginAutoUpdateRuntime,
    format_plugin_auto_update_notification,
    plugin_auto_updates_enabled,
)
from vibeagent.plugin_commands import handle_plugin_command
from vibeagent.plugin_installation import copy_plugin_tree
from vibeagent.plugin_store import (
    install_local_plugin,
    list_installed_plugins,
    read_installed_plugin,
    set_plugin_enabled,
    uninstall_plugin,
    update_installed_plugin,
)
from vibeagent.plugin_types import InstalledMarketplace


def bump_plugin(plugin: Path, version: str, marker: str) -> None:
    manifest_path = plugin / ".claude-plugin" / "plugin.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["version"] = version
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    (plugin / "skills" / "review" / "SKILL.md").write_text(
        f"---\nname: review\ndescription: Review code\n---\n\n{marker}\n",
        encoding="utf-8",
    )


class PluginUpdateTests(unittest.TestCase):
    def test_local_update_skips_same_version_and_preserves_disabled_state(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-update-") as base:
            root = Path(base)
            source = write_demo_plugin(root)
            installed = install_local_plugin(root, "extensions/demo-plugin")
            set_plugin_enabled(root, installed.name, False)
            bump_plugin(source, "1.2.3", "same-version-content")

            unchanged = update_installed_plugin(root, "demo-plugin")
            cached_skill = root / ".vibeagent/plugins/cache/demo-plugin/skills/review/SKILL.md"
            self.assertFalse(unchanged.updated)
            self.assertNotIn("same-version-content", cached_skill.read_text(encoding="utf-8"))
            current_command = handle_plugin_command(root, "update demo-plugin")
            self.assertFalse(current_command.changed)
            self.assertIn("already current", current_command.text)

            bump_plugin(source, "1.2.4", "new-version-content")
            update_command = handle_plugin_command(root, "update demo-plugin")
            updated = read_installed_plugin(root, "demo-plugin")

            self.assertTrue(update_command.changed)
            self.assertIn("1.2.3 -> 1.2.4", update_command.text)
            self.assertEqual(updated.version, "1.2.4")
            self.assertFalse(updated.enabled)
            self.assertIn("new-version-content", cached_skill.read_text(encoding="utf-8"))

    def test_marketplace_entry_version_drives_update_when_manifest_has_none(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-update-") as base:
            root = Path(base)
            marketplace = write_demo_marketplace(root)
            source = marketplace / "extensions" / "demo-plugin"
            manifest_path = source / ".claude-plugin" / "plugin.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest.pop("version")
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            catalog_path = marketplace / ".claude-plugin" / "marketplace.json"
            catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
            catalog["plugins"][0]["version"] = "1.2.3"
            catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
            add_local_marketplace(root, "catalog")
            installed = install_marketplace_plugin(root, "demo-plugin@team-tools")
            self.assertEqual(installed.version, "1.2.3")

            (source / "skills/review/SKILL.md").write_text(
                "---\nname: review\ndescription: Review code\n---\n\nmarketplace-v2\n",
                encoding="utf-8",
            )
            catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
            catalog["plugins"][0]["version"] = "1.2.4"
            catalog_path.write_text(json.dumps(catalog), encoding="utf-8")

            updated = update_installed_plugin(root, "demo-plugin")
            cached_skill = root / ".vibeagent/plugins/cache/demo-plugin/skills/review/SKILL.md"

            self.assertTrue(updated.updated)
            self.assertEqual(updated.plugin.version, "1.2.4")
            self.assertIn("marketplace-v2", cached_skill.read_text(encoding="utf-8"))

    def test_update_rolls_back_cache_when_state_write_fails(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-update-") as base:
            root = Path(base)
            source = write_demo_plugin(root)
            install_local_plugin(root, "extensions/demo-plugin")
            bump_plugin(source, "1.2.4", "must-roll-back")

            with patch("vibeagent.plugin_store._write_state", side_effect=OSError("disk full")):
                with self.assertRaisesRegex(OSError, "disk full"):
                    update_installed_plugin(root, "demo-plugin")

            cached = root / ".vibeagent/plugins/cache/demo-plugin/skills/review/SKILL.md"
            self.assertNotIn("must-roll-back", cached.read_text(encoding="utf-8"))
            self.assertEqual(read_installed_plugin(root, "demo-plugin").version, "1.2.3")

    def test_update_does_not_reinstall_plugin_removed_during_copy(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-update-") as base:
            root = Path(base)
            source = write_demo_plugin(root)
            install_local_plugin(root, "extensions/demo-plugin")
            bump_plugin(source, "1.2.4", "new-content")
            removed = False

            def copy_then_remove(copy_source: Path, destination: Path) -> None:
                nonlocal removed
                copy_plugin_tree(copy_source, destination)
                if not removed:
                    removed = True
                    uninstall_plugin(root, "demo-plugin")

            with patch("vibeagent.plugin_store.copy_plugin_tree", side_effect=copy_then_remove):
                with self.assertRaisesRegex(ValueError, "removed while"):
                    update_installed_plugin(root, "demo-plugin")

            self.assertEqual(list_installed_plugins(root), [])
            self.assertFalse((root / ".vibeagent/plugins/cache/demo-plugin").exists())


class PluginAutoUpdateTests(unittest.TestCase):
    def test_opt_in_runtime_refreshes_marketplace_and_installed_plugin(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-auto-update-") as base:
            root = Path(base)
            marketplace = write_demo_marketplace(root)
            add_local_marketplace(root, "catalog")
            install_marketplace_plugin(root, "demo-plugin@team-tools")
            configured = set_marketplace_auto_update(root, "team-tools", True)
            self.assertTrue(configured.auto_update)

            source = marketplace / "extensions" / "demo-plugin"
            bump_plugin(source, "1.2.4", "automatic-update")
            runtime = PluginAutoUpdateRuntime(root, delay_seconds=0)
            with patch.dict(os.environ, {}, clear=False):
                self.assertTrue(runtime.start())
                deadline = time.monotonic() + 2
                notifications = []
                while time.monotonic() < deadline and not notifications:
                    time.sleep(0.01)
                    notifications = runtime.collect_notifications()
            runtime.close()

            self.assertEqual(len(notifications), 1)
            self.assertEqual(notifications[0].updated_plugins, ("demo-plugin",))
            self.assertIn("/reload-plugins", format_plugin_auto_update_notification(notifications[0]))
            self.assertEqual(read_installed_plugin(root, "demo-plugin").version, "1.2.4")
            self.assertTrue(list_installed_marketplaces(root)[0].auto_update)

    def test_commands_toggle_auto_update_and_refresh_all_marketplaces(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-auto-update-") as base:
            root = Path(base)
            write_demo_marketplace(root)
            add_local_marketplace(root, "catalog")

            enabled = handle_plugin_command(root, "marketplace auto-update team-tools on")
            listing = handle_plugin_command(root, "marketplace list")
            refreshed = handle_plugin_command(root, "marketplace update")

            self.assertTrue(enabled.changed)
            self.assertIn("enabled", enabled.text)
            self.assertIn("auto-update=on", listing.text)
            self.assertTrue(refreshed.changed)
            self.assertIn("Updated 1 marketplace", refreshed.text)

    def test_batch_marketplace_refresh_continues_after_one_failure(self) -> None:
        def marketplace(name: str) -> InstalledMarketplace:
            return InstalledMarketplace(
                name=name,
                description="",
                owner="team",
                source=f"catalogs/{name}",
                cache_path=f".vibeagent/plugins/marketplaces/{name}",
                added_at="now",
                plugin_count=1,
            )

        with (
            patch(
                "vibeagent.marketplace_commands.list_installed_marketplaces",
                return_value=[marketplace("broken"), marketplace("working")],
            ),
            patch(
                "vibeagent.marketplace_commands.update_marketplace",
                side_effect=[ValueError("fetch failed"), marketplace("working")],
            ) as update,
        ):
            result = handle_plugin_command(Path.cwd(), "marketplace update")

        self.assertTrue(result.changed)
        self.assertIn("Updated 1 marketplace(s): working", result.text)
        self.assertIn("broken: fetch failed", result.text)
        self.assertEqual(update.call_count, 2)

    def test_global_disable_can_be_overridden_for_plugin_updates(self) -> None:
        with patch.dict(os.environ, {"DISABLE_AUTOUPDATER": "1"}, clear=True):
            self.assertFalse(plugin_auto_updates_enabled())
        with patch.dict(
            os.environ,
            {"DISABLE_AUTOUPDATER": "1", "FORCE_AUTOUPDATE_PLUGINS": "true"},
            clear=True,
        ):
            self.assertTrue(plugin_auto_updates_enabled())

    def test_invalid_auto_update_state_does_not_block_cli_startup(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-auto-update-") as base:
            runtime = PluginAutoUpdateRuntime(Path(base), delay_seconds=0)
            with patch(
                "vibeagent.plugin_auto_update.list_installed_marketplaces",
                side_effect=ValueError("bad state"),
            ):
                self.assertFalse(runtime.start())

        notifications = runtime.collect_notifications()
        self.assertEqual(len(notifications), 1)
        self.assertIn("bad state", notifications[0].errors[0])


if __name__ == "__main__":
    unittest.main()
