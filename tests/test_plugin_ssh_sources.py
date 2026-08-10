from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tests.test_plugin_remote_sources import write_remote_marketplace
from tests.test_plugins import write_demo_plugin
from vibeagent.marketplace_store import add_marketplace, install_marketplace_plugin
from vibeagent.plugin_installation import copy_plugin_tree
from vibeagent.plugin_store import update_installed_plugin


class SshPluginUpdateTests(unittest.TestCase):
    def test_ssh_plugin_source_updates_through_atomic_marketplace_flow(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-ssh-update-") as base:
            root = Path(base)
            catalog = write_remote_marketplace(
                root,
                {
                    "source": "url",
                    "url": "git@gitlab.example.com:team/demo-plugin.git",
                    "ref": "release",
                },
            )
            add_marketplace(root, "remote-catalog")
            remote_plugin = write_demo_plugin(root / "remote-plugin-source")

            def clone(_url: str, destination: Path, **kwargs: object) -> None:
                self.assertEqual(kwargs["ref"], "release")
                copy_plugin_tree(remote_plugin, destination)

            with patch(
                "vibeagent.marketplace_plugin_fetch.clone_remote_git",
                side_effect=clone,
            ):
                installed = install_marketplace_plugin(root, "demo-plugin@remote-tools")

            plugin_manifest_path = remote_plugin / ".claude-plugin/plugin.json"
            plugin_manifest = json.loads(plugin_manifest_path.read_text(encoding="utf-8"))
            plugin_manifest["version"] = "1.2.4"
            plugin_manifest_path.write_text(json.dumps(plugin_manifest), encoding="utf-8")
            skill_path = remote_plugin / "skills/review/SKILL.md"
            skill_path.write_text(
                "---\nname: review\ndescription: Updated SSH review\n---\n\nUpdated SSH content.\n",
                encoding="utf-8",
            )
            catalog_path = catalog / ".claude-plugin/marketplace.json"
            catalog_payload = json.loads(catalog_path.read_text(encoding="utf-8"))
            catalog_payload["plugins"][0]["version"] = "1.2.4"
            catalog_path.write_text(json.dumps(catalog_payload), encoding="utf-8")

            with patch(
                "vibeagent.marketplace_plugin_fetch.clone_remote_git",
                side_effect=clone,
            ):
                updated = update_installed_plugin(root, "demo-plugin")

            self.assertEqual(installed.version, "1.2.3")
            self.assertTrue(updated.updated)
            self.assertEqual(updated.plugin.version, "1.2.4")
            cached_skill = root / ".vibeagent/plugins/cache/demo-plugin/skills/review/SKILL.md"
            self.assertIn("Updated SSH content", cached_skill.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
