from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from vibeagent.mcp_config import read_mcp_server_configs
from vibeagent.actions import parse_tool_action
from vibeagent.plugin_commands import handle_plugin_command, reload_plugins_text
from vibeagent.plugin_manifest import read_plugin_manifest
from vibeagent.plugin_store import (
    install_local_plugin,
    list_installed_plugins,
    set_plugin_enabled,
    uninstall_plugin,
)
from vibeagent.workspace_agents import read_project_agent, read_project_agents
from vibeagent.workspace_core import create_run_workspace
from vibeagent.workspace_hooks import read_project_hooks
from vibeagent.workspace_prompt_commands import expand_project_prompt_command, read_project_prompt_commands
from vibeagent.workspace_skills import read_project_skill, read_project_skills


def write_demo_plugin(root: Path, *, default_enabled: bool = True) -> Path:
    plugin = root / "extensions" / "demo-plugin"
    (plugin / ".claude-plugin").mkdir(parents=True)
    (plugin / "skills" / "review").mkdir(parents=True)
    (plugin / "commands").mkdir()
    (plugin / "agents").mkdir()
    (plugin / "hooks").mkdir()
    (plugin / "bin").mkdir()
    (plugin / ".claude-plugin" / "plugin.json").write_text(
        json.dumps(
            {
                "name": "demo-plugin",
                "description": "Demo extension",
                "version": "1.2.3",
                "defaultEnabled": default_enabled,
            }
        ),
        encoding="utf-8",
    )
    (plugin / "skills" / "review" / "SKILL.md").write_text(
        "---\nname: review\ndescription: Review focused code changes\n---\n\n"
        "Check the requested code carefully with ${CLAUDE_PLUGIN_ROOT} in ${CLAUDE_PROJECT_DIR}.\n",
        encoding="utf-8",
    )
    (plugin / "commands" / "fix.md").write_text(
        "---\ndescription: Fix one target\nargument-hint: <target>\n---\n"
        "Inspect $ARGUMENTS using ${CLAUDE_PLUGIN_ROOT}/scripts and ${CLAUDE_PROJECT_DIR}.\n",
        encoding="utf-8",
    )
    (plugin / "agents" / "reviewer.md").write_text(
        "---\nname: reviewer\ndescription: Review one change\nmode: explore\nskills: review\n---\n"
        "Inspect the requested change using ${CLAUDE_PLUGIN_ROOT}.\n",
        encoding="utf-8",
    )
    (plugin / "hooks" / "hooks.json").write_text(
        json.dumps(
            {
                "hooks": {
                    "PostToolUse": [
                        {
                            "matcher": "Read",
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": "${CLAUDE_PLUGIN_ROOT}/bin/check",
                                }
                            ],
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    (plugin / ".mcp.json").write_text(
        json.dumps(
            {
                "mcpServers": {
                    "echo": {
                        "command": "${CLAUDE_PLUGIN_ROOT}/bin/server",
                        "args": ["${CLAUDE_PROJECT_DIR}"],
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    (plugin / "bin" / "check").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    (plugin / "bin" / "server").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    return plugin


class PluginManifestTests(unittest.TestCase):
    def test_default_component_layout_is_inventoried(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-") as base:
            plugin = write_demo_plugin(Path(base))
            manifest = read_plugin_manifest(plugin)

            self.assertEqual(manifest.name, "demo-plugin")
            self.assertEqual(manifest.version, "1.2.3")
            self.assertEqual(manifest.component_count, 5)
            self.assertEqual([path.name for path in manifest.skill_files], ["SKILL.md"])

    def test_manifest_rejects_escaping_component_path(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-") as base:
            root = Path(base)
            plugin = write_demo_plugin(root)
            manifest_path = plugin / ".claude-plugin" / "plugin.json"
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            payload["skills"] = ["./../outside"]
            manifest_path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "escapes the plugin root"):
                read_plugin_manifest(plugin)

    def test_manifestless_root_skill_uses_directory_name(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-") as base:
            plugin = Path(base) / "bare-plugin"
            plugin.mkdir()
            (plugin / "SKILL.md").write_text(
                "---\ndescription: A minimal root skill\n---\n\nInspect the requested files.\n",
                encoding="utf-8",
            )

            manifest = read_plugin_manifest(plugin)

            self.assertEqual(manifest.name, "bare-plugin")
            self.assertIsNone(manifest.manifest_path)
            self.assertEqual(manifest.skill_files, (plugin / "SKILL.md",))

    def test_explicit_skills_path_extends_default_skills_directory(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-") as base:
            plugin = write_demo_plugin(Path(base))
            custom = plugin / "extra" / "audit"
            custom.mkdir(parents=True)
            (custom / "SKILL.md").write_text(
                "---\nname: audit\ndescription: Audit one change\n---\n",
                encoding="utf-8",
            )
            manifest_path = plugin / ".claude-plugin" / "plugin.json"
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            payload["skills"] = "./extra"
            manifest_path.write_text(json.dumps(payload), encoding="utf-8")

            manifest = read_plugin_manifest(plugin)

            self.assertEqual(
                [path.parent.name for path in manifest.skill_files],
                ["audit", "review"],
            )


class PluginRuntimeTests(unittest.TestCase):
    def test_default_disabled_plugin_installs_without_exposing_components(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-") as base:
            root = Path(base)
            write_demo_plugin(root, default_enabled=False)

            installed = install_local_plugin(root, "extensions/demo-plugin")
            workspace = create_run_workspace(root, run_id="run-1")

            self.assertFalse(installed.enabled)
            self.assertEqual(read_project_skills(workspace)["skills"], [])

    def test_installed_plugin_loads_all_supported_components_with_namespaces(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-") as base:
            root = Path(base)
            write_demo_plugin(root)
            installed = install_local_plugin(root, "extensions/demo-plugin")
            workspace = create_run_workspace(root, run_id="run-1")

            self.assertTrue(installed.enabled)
            self.assertEqual(installed.component_count, 5)
            skill_names = [item["name"] for item in read_project_skills(workspace)["skills"]]
            self.assertIn("demo-plugin:review", skill_names)
            skill = read_project_skill(workspace, "demo-plugin:review")
            self.assertIn("Check the requested code", skill["content"])
            self.assertIn(".vibeagent/plugins/cache/demo-plugin", skill["content"])

            agent_names = [item["name"] for item in read_project_agents(workspace)["agents"]]
            self.assertIn("demo-plugin:reviewer", agent_names)
            agent = read_project_agent(workspace, "demo-plugin:reviewer")
            self.assertEqual(agent["skills"], ["demo-plugin:review"])
            self.assertIn(".vibeagent/plugins/cache/demo-plugin", agent["prompt"])
            action = parse_tool_action(
                "delegate_task",
                {"task": "Review this change", "agent": "demo-plugin:reviewer"},
            )
            self.assertEqual(action.agent, "demo-plugin:reviewer")

            command_names = [item["name"] for item in read_project_prompt_commands(root)["commands"]]
            self.assertIn("demo-plugin:fix", command_names)
            expanded = expand_project_prompt_command(root, "/demo-plugin:fix parser")
            self.assertIsNotNone(expanded)
            self.assertIn("Inspect parser", expanded["prompt"])  # type: ignore[index]
            self.assertIn(".vibeagent/plugins/cache/demo-plugin/scripts", expanded["prompt"])  # type: ignore[index]

            hooks = read_project_hooks(workspace)
            self.assertIsNone(hooks.error)
            self.assertEqual(len(hooks.hooks), 1)
            self.assertIn(".vibeagent/plugins/cache/demo-plugin/bin/check", hooks.hooks[0].command)

            servers = read_mcp_server_configs(workspace)
            self.assertEqual([server.name for server in servers], ["demo-plugin.echo"])
            self.assertIn(".vibeagent/plugins/cache/demo-plugin/bin/server", servers[0].command)
            self.assertEqual(servers[0].args, [root.as_posix()])

    def test_disable_and_uninstall_remove_plugin_components(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-") as base:
            root = Path(base)
            write_demo_plugin(root)
            install_local_plugin(root, "extensions/demo-plugin")
            workspace = create_run_workspace(root, run_id="run-1")

            set_plugin_enabled(root, "demo-plugin", False)
            reinstalled = install_local_plugin(root, "extensions/demo-plugin")
            self.assertFalse(reinstalled.enabled)
            self.assertEqual(read_project_skills(workspace)["skills"], [])
            self.assertEqual(read_project_agents(workspace)["agents"], [])
            self.assertEqual(read_project_prompt_commands(root)["commands"], [])
            self.assertEqual(read_project_hooks(workspace).hooks, ())
            self.assertEqual(read_mcp_server_configs(workspace), [])

            removed = uninstall_plugin(root, "demo-plugin")
            self.assertEqual(removed.name, "demo-plugin")
            self.assertEqual(list_installed_plugins(root), [])
            self.assertFalse((root / ".vibeagent/plugins/cache/demo-plugin").exists())

    def test_uninstall_rolls_cache_back_when_state_write_fails(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-") as base:
            root = Path(base)
            write_demo_plugin(root)
            install_local_plugin(root, "extensions/demo-plugin")
            cache = root / ".vibeagent/plugins/cache/demo-plugin"

            with patch("vibeagent.plugin_store._write_state", side_effect=OSError("disk full")):
                with self.assertRaisesRegex(OSError, "disk full"):
                    uninstall_plugin(root, "demo-plugin")

            self.assertTrue(cache.is_dir())
            self.assertEqual([plugin.name for plugin in list_installed_plugins(root)], ["demo-plugin"])

    def test_plugin_mcp_cwd_cannot_target_git_metadata(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-") as base:
            root = Path(base)
            plugin = write_demo_plugin(root)
            (root / ".git").mkdir()
            (plugin / ".mcp.json").write_text(
                json.dumps(
                    {
                        "mcpServers": {
                            "unsafe": {
                                "command": "echo",
                                "cwd": "${CLAUDE_PROJECT_DIR}/.git",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            install_local_plugin(root, "extensions/demo-plugin")
            workspace = create_run_workspace(root, run_id="run-1")

            with self.assertRaisesRegex(ValueError, "escapes the plugin or project root"):
                read_mcp_server_configs(workspace)

    def test_install_rejects_symlinks_and_command_lifecycle_reports_changes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-") as base:
            root = Path(base)
            plugin = write_demo_plugin(root)
            (plugin / "linked.txt").symlink_to(root / "outside.txt")

            with self.assertRaisesRegex(ValueError, "symbolic link"):
                install_local_plugin(root, "extensions/demo-plugin")
            (plugin / "linked.txt").unlink()

            validated = handle_plugin_command(root, "validate extensions/demo-plugin")
            self.assertFalse(validated.changed)
            self.assertIn("validation passed", validated.text)
            installed = handle_plugin_command(root, "install extensions/demo-plugin")
            self.assertTrue(installed.changed)
            self.assertIn("Installed plugin demo-plugin 1.2.3", installed.text)
            self.assertIn("demo-plugin", handle_plugin_command(root, "list").text)
            self.assertIn("skills=1", reload_plugins_text(root))


if __name__ == "__main__":
    unittest.main()
