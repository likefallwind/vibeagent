from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from tests.test_plugin_user_config import write_user_config_plugin
from tests.test_plugins import write_demo_plugin
from vibeagent.mcp_config import read_mcp_server_configs
from vibeagent.plugin_commands import format_plugin_details, reload_plugins_text
from vibeagent.plugin_manifest import read_plugin_manifest
from vibeagent.plugin_store import install_local_plugin, set_plugin_enabled
from vibeagent.plugin_user_config import set_plugin_user_config_value
from vibeagent.workspace_core import create_run_workspace
from vibeagent.workspace_hooks import read_project_hooks


def write_inline_plugin(root: Path, *, default_enabled: bool = True) -> Path:
    plugin = write_demo_plugin(root, default_enabled=default_enabled)
    manifest_path = plugin / ".claude-plugin" / "plugin.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["hooks"] = {
        "PostToolUse": [
            {
                "matcher": "Write|Edit",
                "hooks": [
                    {
                        "type": "command",
                        "command": "${CLAUDE_PLUGIN_ROOT}/bin/check",
                    }
                ],
            }
        ]
    }
    payload["mcpServers"] = {
        "inline": {
            "command": "${CLAUDE_PLUGIN_ROOT}/bin/server",
            "args": ["${CLAUDE_PROJECT_DIR}"],
            "cwd": "${CLAUDE_PLUGIN_ROOT}",
        }
    }
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    return plugin


class PluginInlineComponentTests(unittest.TestCase):
    def test_inline_hooks_and_mcp_replace_default_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-inline-") as base:
            root = Path(base)
            plugin = write_inline_plugin(root)
            manifest = read_plugin_manifest(plugin)

            self.assertEqual(manifest.hook_files, ())
            self.assertEqual(manifest.mcp_files, ())
            self.assertIsNotNone(manifest.inline_hooks)
            self.assertIsNotNone(manifest.inline_mcp_servers)
            self.assertEqual(manifest.component_count, 5)
            self.assertIn("hooks: 1", format_plugin_details(manifest))
            self.assertIn("MCP configs: 1", format_plugin_details(manifest))

            install_local_plugin(root, "extensions/demo-plugin")
            workspace = create_run_workspace(root, "run-1")
            hooks = read_project_hooks(workspace)
            servers = read_mcp_server_configs(workspace)

            self.assertIsNone(hooks.error)
            self.assertEqual(len(hooks.hooks), 1)
            self.assertEqual(hooks.hooks[0].matcher, "Write|Edit")
            self.assertTrue(hooks.hooks[0].source.endswith("plugin.json#hooks"))
            self.assertIn(".vibeagent/plugins/cache/demo-plugin/bin/check", hooks.hooks[0].command)
            self.assertEqual([server.name for server in servers], ["demo-plugin.inline"])
            self.assertIn(".vibeagent/plugins/cache/demo-plugin/bin/server", servers[0].command)
            self.assertEqual(servers[0].args, [root.as_posix()])
            self.assertIn("hooks=1", reload_plugins_text(root))
            self.assertIn("MCP servers=1", reload_plugins_text(root))

    def test_disabled_and_strict_modes_ignore_inline_components(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-inline-") as base:
            root = Path(base)
            write_inline_plugin(root, default_enabled=False)
            install_local_plugin(root, "extensions/demo-plugin")

            disabled = create_run_workspace(root, "run-disabled")
            self.assertEqual(read_project_hooks(disabled).hooks, ())
            self.assertEqual(read_mcp_server_configs(disabled), [])

            set_plugin_enabled(root, "demo-plugin", True)
            strict = create_run_workspace(root, "run-strict", strict_mcp_config=True)
            self.assertEqual(read_mcp_server_configs(strict), [])
            self.assertEqual(len(read_project_hooks(strict).hooks), 1)

    def test_invalid_inline_components_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-inline-") as base:
            root = Path(base)
            plugin = write_inline_plugin(root)
            manifest_path = plugin / ".claude-plugin" / "plugin.json"
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            payload["hooks"] = {"PostToolUse": "invalid"}
            payload["mcpServers"] = {"broken": {"args": []}}
            manifest_path.write_text(json.dumps(payload), encoding="utf-8")
            install_local_plugin(root, "extensions/demo-plugin")
            workspace = create_run_workspace(root, "run-1")

            hooks = read_project_hooks(workspace)
            self.assertEqual(hooks.hooks, ())
            self.assertIn("must be a list", hooks.error or "")
            with self.assertRaisesRegex(ValueError, "requires a non-empty command"):
                read_mcp_server_configs(workspace)

    def test_inline_components_keep_sensitive_user_config_in_environment(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-inline-") as base:
            root = Path(base)
            plugin = write_user_config_plugin(root, default_enabled=False)
            manifest_path = plugin / ".claude-plugin" / "plugin.json"
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            payload["hooks"] = {
                "PostToolUse": [
                    {
                        "matcher": "Read",
                        "hooks": [
                            {
                                "type": "command",
                                "command": "check ${user_config.token}",
                            }
                        ],
                    }
                ]
            }
            payload["mcpServers"] = {
                "configured": {
                    "command": "echo",
                    "args": ["${user_config.endpoint}", "${user_config.token}"],
                }
            }
            manifest_path.write_text(json.dumps(payload), encoding="utf-8")
            install_local_plugin(root, "extensions/demo-plugin")
            set_plugin_user_config_value(root, "demo-plugin", "endpoint", "service.example")
            set_plugin_user_config_value(root, "demo-plugin", "token", "secret-token")
            set_plugin_enabled(root, "demo-plugin", True)
            workspace = create_run_workspace(root, "run-1")

            hook = read_project_hooks(workspace).hooks[0]
            server = read_mcp_server_configs(workspace)[0]

            self.assertIn("${CLAUDE_PLUGIN_OPTION_token}", hook.command)
            self.assertNotIn("secret-token", hook.command)
            self.assertEqual(hook.environment["CLAUDE_PLUGIN_OPTION_token"], "secret-token")
            self.assertEqual(server.argv[-2:], ["service.example", "secret-token"])
            self.assertNotIn("secret-token", server.args)

    def test_non_object_inline_values_still_require_paths(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-inline-") as base:
            plugin = write_demo_plugin(Path(base))
            manifest_path = plugin / ".claude-plugin" / "plugin.json"
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            payload["hooks"] = [object()]
            with self.assertRaises(TypeError):
                json.dumps(payload)
            payload["hooks"] = [42]
            manifest_path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "path string"):
                read_plugin_manifest(plugin)


if __name__ == "__main__":
    unittest.main()
