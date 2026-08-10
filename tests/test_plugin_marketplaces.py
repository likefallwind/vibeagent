from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tests.user_home_test_case import IsolatedUserHomeTestCase
from tests.test_plugins import write_demo_marketplace, write_demo_plugin
from vibeagent.marketplace_manifest import read_marketplace_manifest
from vibeagent.marketplace_store import (
    add_local_marketplace,
    install_marketplace_plugin,
    list_installed_marketplaces,
    read_installed_marketplace_manifest,
    remove_marketplace,
    update_local_marketplace,
)
from vibeagent.plugin_commands import handle_plugin_command
from vibeagent.plugin_store import install_local_plugin, list_installed_plugins
from vibeagent.workspace_core import create_run_workspace
from vibeagent.workspace_skills import read_project_skills


class MarketplaceManifestTests(IsolatedUserHomeTestCase):
    def test_local_marketplace_inventories_verified_relative_plugins(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-marketplace-") as base:
            marketplace = write_demo_marketplace(Path(base))

            manifest = read_marketplace_manifest(marketplace)

            self.assertEqual(manifest.name, "team-tools")
            self.assertEqual(manifest.owner, "VibeAgent Team")
            self.assertEqual([plugin.name for plugin in manifest.plugins], ["demo-plugin"])
            self.assertEqual(manifest.plugins[0].version, "1.2.3")

    def test_marketplace_rejects_escape_duplicate_and_identity_mismatch(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-marketplace-") as base:
            marketplace = write_demo_marketplace(Path(base))
            manifest_path = marketplace / ".claude-plugin" / "marketplace.json"
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))

            payload["plugins"][0]["source"] = "./../outside"
            manifest_path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "must not contain"):
                read_marketplace_manifest(marketplace)

            payload["plugins"][0]["source"] = "./extensions/demo-plugin"
            payload["plugins"].append(dict(payload["plugins"][0]))
            manifest_path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "names must be unique"):
                read_marketplace_manifest(marketplace)

            payload["plugins"].pop()
            payload["plugins"][0]["name"] = "wrong-name"
            manifest_path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "does not match plugin manifest"):
                read_marketplace_manifest(marketplace)


class MarketplaceRuntimeTests(IsolatedUserHomeTestCase):
    def test_marketplace_add_install_update_and_remove_are_runtime_complete(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-marketplace-") as base:
            root = Path(base)
            marketplace = write_demo_marketplace(root)
            (marketplace / ".git").mkdir()
            (marketplace / ".git" / "config").write_text("private metadata", encoding="utf-8")

            added = add_local_marketplace(root, "catalog")
            self.assertEqual(added.name, "team-tools")
            self.assertEqual(added.plugin_count, 1)
            self.assertEqual(
                [item.name for item in list_installed_marketplaces(root)],
                ["team-tools"],
            )
            self.assertFalse((root / ".vibeagent/plugins/marketplaces/team-tools/.git").exists())

            plugin = install_marketplace_plugin(root, "demo-plugin@team-tools")
            workspace = create_run_workspace(root, run_id="run-marketplace")
            self.assertEqual(plugin.marketplace, "team-tools")
            self.assertIn(
                "demo-plugin:review",
                [item["name"] for item in read_project_skills(workspace)["skills"]],
            )

            manifest_path = marketplace / ".claude-plugin" / "marketplace.json"
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            payload["description"] = "Updated team extensions"
            manifest_path.write_text(json.dumps(payload), encoding="utf-8")
            updated = update_local_marketplace(root, "team-tools")
            self.assertEqual(updated.description, "Updated team extensions")
            self.assertEqual(
                read_installed_marketplace_manifest(root, "team-tools").description,
                "Updated team extensions",
            )

            removed = remove_marketplace(root, "team-tools")
            self.assertEqual(removed.name, "team-tools")
            self.assertEqual(list_installed_marketplaces(root), [])
            self.assertEqual(list_installed_plugins(root), [])
            self.assertEqual(read_project_skills(workspace)["skills"], [])

    def test_marketplace_update_restores_previous_cache_on_state_failure(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-marketplace-") as base:
            root = Path(base)
            marketplace = write_demo_marketplace(root)
            add_local_marketplace(root, "catalog")
            manifest_path = marketplace / ".claude-plugin" / "marketplace.json"
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            payload["description"] = "Should not persist"
            manifest_path.write_text(json.dumps(payload), encoding="utf-8")

            with patch("vibeagent.marketplace_state_ops._write_state", side_effect=OSError("disk full")):
                with self.assertRaisesRegex(OSError, "disk full"):
                    update_local_marketplace(root, "team-tools")

            self.assertEqual(
                read_installed_marketplace_manifest(root, "team-tools").description,
                "Team coding extensions",
            )

    def test_marketplace_remove_rolls_back_catalog_and_plugins_on_state_failure(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-marketplace-") as base:
            root = Path(base)
            write_demo_marketplace(root)
            add_local_marketplace(root, "catalog")
            install_marketplace_plugin(root, "demo-plugin@team-tools")
            marketplace_cache = root / ".vibeagent/plugins/marketplaces/team-tools"
            plugin_cache = root / ".vibeagent/plugins/cache/demo-plugin"

            with patch("vibeagent.marketplace_state_ops._write_state", side_effect=OSError("disk full")):
                with self.assertRaisesRegex(OSError, "disk full"):
                    remove_marketplace(root, "team-tools")

            self.assertTrue(marketplace_cache.is_dir())
            self.assertTrue(plugin_cache.is_dir())
            self.assertEqual(
                [item.name for item in list_installed_marketplaces(root)],
                ["team-tools"],
            )
            self.assertEqual([item.name for item in list_installed_plugins(root)], ["demo-plugin"])

    def test_marketplace_commands_validate_and_manage_catalog(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-marketplace-") as base:
            root = Path(base)
            write_demo_marketplace(root)

            validated = handle_plugin_command(root, "validate catalog")
            self.assertIn("Marketplace validation passed", validated.text)
            added = handle_plugin_command(root, "marketplace add catalog")
            self.assertTrue(added.changed)
            self.assertIn("Added marketplace team-tools", added.text)
            installed = handle_plugin_command(root, "install demo-plugin@team-tools")
            self.assertTrue(installed.changed)
            self.assertIn("from team-tools", installed.text)
            self.assertIn("@team-tools", handle_plugin_command(root, "list").text)
            self.assertIn(
                "demo-plugin 1.2.3",
                handle_plugin_command(root, "marketplace details team-tools").text,
            )
            removed = handle_plugin_command(root, "marketplace remove team-tools")
            self.assertTrue(removed.changed)
            self.assertIn("and its installed plugins", removed.text)

    def test_version_one_plugin_state_without_marketplaces_remains_readable(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-marketplace-") as base:
            root = Path(base)
            write_demo_plugin(root)
            install_local_plugin(root, "extensions/demo-plugin")
            state_path = root / ".vibeagent/plugins/installed.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            del state["marketplaces"]
            state_path.write_text(json.dumps(state), encoding="utf-8")

            self.assertEqual([item.name for item in list_installed_plugins(root)], ["demo-plugin"])
            self.assertEqual(list_installed_marketplaces(root), [])


if __name__ == "__main__":
    unittest.main()
