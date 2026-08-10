from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

from tests.test_agent_hooks import HookClient
from tests.test_plugins import write_demo_marketplace, write_demo_plugin
from vibeagent.agent import run_agent
from vibeagent.lsp_config import read_lsp_server_configs
from vibeagent.mcp_config import read_mcp_server_configs
from vibeagent.plugin_commands import handle_plugin_command
from vibeagent.plugin_manifest import read_plugin_manifest
from vibeagent.plugin_monitor_config import read_plugin_monitor_configs
from vibeagent.plugin_store import install_local_plugin, set_plugin_enabled
from vibeagent.plugin_user_config import (
    resolve_plugin_user_config,
    set_plugin_user_config_value,
    unset_plugin_user_config_value,
)
from vibeagent.workspace_agents import read_project_agent
from vibeagent.workspace_core import create_run_workspace
from vibeagent.workspace_hooks import read_project_hooks
from vibeagent.workspace_prompt_commands import expand_project_prompt_command
from vibeagent.workspace_skills import read_project_skill
from vibeagent.types import ApprovalDecision


def write_user_config_plugin(root: Path, *, default_enabled: bool = True) -> Path:
    plugin = write_demo_plugin(root, default_enabled=default_enabled)
    manifest_path = plugin / ".claude-plugin" / "plugin.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["userConfig"] = {
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
            "sensitive": True,
            "required": True,
        },
        "retries": {
            "type": "number",
            "title": "Retries",
            "description": "Retry count",
            "default": 2,
            "min": 1,
            "max": 5,
        },
        "labels": {
            "type": "string",
            "title": "Labels",
            "description": "Request labels",
            "multiple": True,
            "default": ["review"],
        },
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    (plugin / "skills" / "review" / "SKILL.md").write_text(
        "---\nname: review\ndescription: Review code\n---\n\n"
        "Use ${user_config.endpoint} from ${CLAUDE_PLUGIN_DATA}.\n",
        encoding="utf-8",
    )
    secret_skill = plugin / "skills" / "secret"
    secret_skill.mkdir()
    (secret_skill / "SKILL.md").write_text(
        "---\nname: secret\ndescription: Invalid secret exposure\n---\n\n"
        "Never show ${user_config.token}.\n",
        encoding="utf-8",
    )
    (plugin / "commands" / "fix.md").write_text(
        "---\ndescription: Fix one target\n---\n"
        "Use ${user_config.endpoint} for $ARGUMENTS.\n",
        encoding="utf-8",
    )
    (plugin / "agents" / "reviewer.md").write_text(
        "---\nname: reviewer\ndescription: Review one change\nmode: explore\n---\n"
        "Review through ${user_config.endpoint}.\n",
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
                                    "command": (
                                        "test \"${user_config.token}\" = \"$CLAUDE_PLUGIN_OPTION_token\" "
                                        "&& test \"${user_config.endpoint}\" = "
                                        "\"$CLAUDE_PLUGIN_OPTION_endpoint\" "
                                        "&& printf 'ok' > plugin-hook.log"
                                    ),
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
                    "configured": {
                        "command": sys.executable,
                        "args": ["-c", "pass", "${user_config.endpoint}", "${user_config.token}"],
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    (plugin / ".lsp.json").write_text(
        json.dumps(
            {
                "configured": {
                    "command": sys.executable,
                    "args": ["-c", "pass", "${user_config.token}"],
                    "env": {"PLUGIN_ENDPOINT": "${user_config.endpoint}"},
                    "extensionToLanguage": {".py": "python"},
                }
            }
        ),
        encoding="utf-8",
    )
    monitors = plugin / "monitors"
    monitors.mkdir()
    (monitors / "monitors.json").write_text(
        json.dumps(
            [
                {
                    "name": "configured",
                    "command": "printf '%s' \"${user_config.endpoint}:${user_config.token}\"",
                    "description": "Configured monitor",
                }
            ]
        ),
        encoding="utf-8",
    )
    return plugin


class PluginUserConfigTests(unittest.TestCase):
    def test_manifest_validates_schema_defaults_and_constraints(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-user-config-") as base:
            plugin = write_user_config_plugin(Path(base))
            manifest = read_plugin_manifest(plugin)

            options = {option.key: option for option in manifest.user_config}
            self.assertEqual(set(options), {"endpoint", "token", "retries", "labels"})
            self.assertTrue(options["token"].sensitive)
            self.assertEqual(options["retries"].minimum, 1)
            self.assertEqual(options["labels"].default, ["review"])

            path = plugin / ".claude-plugin" / "plugin.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["userConfig"]["retries"]["default"] = 10
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "at most 5"):
                read_plugin_manifest(plugin)

    def test_set_stores_shared_and_sensitive_values_separately(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-user-config-") as base:
            root = Path(base)
            write_user_config_plugin(root)
            install_local_plugin(root, "extensions/demo-plugin")
            set_plugin_user_config_value(root, "demo-plugin", "endpoint", "https://api.example")
            config = set_plugin_user_config_value(root, "demo-plugin", "token", "secret-token")

            settings = (root / ".claude/settings.local.json").read_text(encoding="utf-8")
            credentials_path = root / ".vibeagent/plugins/user-config-credentials.json"
            credentials = credentials_path.read_text(encoding="utf-8")
            credential_mode = stat.S_IMODE(credentials_path.stat().st_mode)
            status = handle_plugin_command(root, "config demo-plugin").text

        self.assertIn("https://api.example", settings)
        self.assertNotIn("secret-token", settings)
        self.assertIn("secret-token", credentials)
        self.assertEqual(credential_mode, 0o600)
        self.assertEqual(config.values["retries"], 2)
        self.assertEqual(config.values["labels"], ["review"])
        self.assertIn("token: configured", status)
        self.assertIn("<redacted>", status)
        self.assertNotIn("secret-token", status)

    def test_local_and_environment_values_override_project_configuration(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-user-config-") as base:
            root = Path(base)
            write_user_config_plugin(root)
            install_local_plugin(root, "extensions/demo-plugin")
            (root / ".claude").mkdir()
            (root / ".claude/settings.json").write_text(
                json.dumps(
                    {
                        "pluginConfigs": {
                            "demo-plugin": {"options": {"endpoint": "project"}}
                        }
                    }
                ),
                encoding="utf-8",
            )
            set_plugin_user_config_value(root, "demo-plugin", "endpoint", "local")
            set_plugin_user_config_value(root, "demo-plugin", "token", "secret")
            manifest = read_plugin_manifest(root / ".vibeagent/plugins/cache/demo-plugin")

            local = resolve_plugin_user_config(root, manifest)
            with patch.dict(os.environ, {"CLAUDE_PLUGIN_OPTION_endpoint": "environment"}):
                environment = resolve_plugin_user_config(root, manifest)

        self.assertEqual(local.values["endpoint"], "local")
        self.assertEqual(environment.values["endpoint"], "environment")
        self.assertEqual(environment.sources["endpoint"], "environment:CLAUDE_PLUGIN_OPTION_endpoint")

    def test_required_values_gate_enable_and_unset_restores_missing_state(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-user-config-") as base:
            root = Path(base)
            write_user_config_plugin(root, default_enabled=False)
            install_local_plugin(root, "extensions/demo-plugin")

            denied = handle_plugin_command(root, "enable demo-plugin")
            handle_plugin_command(root, "config set demo-plugin endpoint local")
            handle_plugin_command(root, "config set demo-plugin token secret")
            enabled = handle_plugin_command(root, "enable demo-plugin")
            unset_plugin_user_config_value(root, "demo-plugin", "endpoint")
            status = handle_plugin_command(root, "config demo-plugin").text

        self.assertIn("missing required user configuration", denied.text)
        self.assertIn("Enabled plugin demo-plugin", enabled.text)
        self.assertIn("endpoint: missing required", status)

    def test_values_expand_across_plugin_components_without_exposing_secret_content(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-user-config-") as base:
            root = Path(base)
            write_user_config_plugin(root)
            install_local_plugin(root, "extensions/demo-plugin")
            set_plugin_user_config_value(root, "demo-plugin", "endpoint", "service.example")
            set_plugin_user_config_value(root, "demo-plugin", "token", "secret-token")
            set_plugin_enabled(root, "demo-plugin", True)
            workspace = create_run_workspace(root, "run-1")

            skill = read_project_skill(workspace, "demo-plugin:review")
            command = expand_project_prompt_command(root, "/demo-plugin:fix parser")
            agent = read_project_agent(workspace, "demo-plugin:reviewer")
            hooks = read_project_hooks(workspace)
            mcp = read_mcp_server_configs(workspace)[0]
            lsp = read_lsp_server_configs(workspace)[0]
            monitor = read_plugin_monitor_configs(workspace)[0]

            with self.assertRaisesRegex(ValueError, "model-visible content"):
                read_project_skill(workspace, "demo-plugin:secret")

        self.assertIn("service.example", skill["content"])
        self.assertIn("service.example", command["prompt"])  # type: ignore[index]
        self.assertIn("service.example", agent["prompt"])
        self.assertIsNone(hooks.error)
        self.assertIn("service.example", hooks.hooks[0].command)
        self.assertIn("${CLAUDE_PLUGIN_OPTION_token}", hooks.hooks[0].command)
        self.assertEqual(hooks.hooks[0].environment["CLAUDE_PLUGIN_OPTION_token"], "secret-token")
        self.assertEqual(mcp.argv[-2:], ["service.example", "secret-token"])
        self.assertEqual(lsp.argv[-1], "secret-token")
        self.assertEqual(lsp.plugin_environment["CLAUDE_PLUGIN_OPTION_token"], "secret-token")
        self.assertIn("${CLAUDE_PLUGIN_OPTION_token}", monitor.command)
        self.assertEqual(monitor.environment["CLAUDE_PLUGIN_OPTION_token"], "secret-token")

    def test_sensitive_values_in_shared_settings_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-user-config-") as base:
            root = Path(base)
            write_user_config_plugin(root)
            install_local_plugin(root, "extensions/demo-plugin")
            (root / ".claude").mkdir()
            (root / ".claude/settings.json").write_text(
                json.dumps(
                    {
                        "pluginConfigs": {
                            "demo-plugin": {"options": {"token": "plaintext"}}
                        }
                    }
                ),
                encoding="utf-8",
            )
            manifest = read_plugin_manifest(root / ".vibeagent/plugins/cache/demo-plugin")

            with self.assertRaisesRegex(ValueError, "must not be stored"):
                resolve_plugin_user_config(root, manifest)
            with self.assertRaisesRegex(ValueError, "must not be stored"):
                set_plugin_user_config_value(root, "demo-plugin", "token", "replacement")
            self.assertFalse(
                root.joinpath(".vibeagent/plugins/user-config-credentials.json").exists()
            )

    def test_marketplace_plugin_uses_qualified_plugin_config_id(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-user-config-") as base:
            root = Path(base)
            marketplace = write_demo_marketplace(root)
            manifest_path = marketplace / "extensions/demo-plugin/.claude-plugin/plugin.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["userConfig"] = {
                "endpoint": {
                    "type": "string",
                    "title": "Endpoint",
                    "description": "Service endpoint",
                }
            }
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            handle_plugin_command(root, "marketplace add catalog")
            handle_plugin_command(root, "install demo-plugin@team-tools")
            set_plugin_user_config_value(root, "demo-plugin", "endpoint", "qualified")
            settings = json.loads(
                (root / ".claude/settings.local.json").read_text(encoding="utf-8")
            )

        self.assertEqual(
            settings["pluginConfigs"]["demo-plugin@team-tools"]["options"]["endpoint"],
            "qualified",
        )

    def test_hook_receives_sensitive_environment_without_recording_value_in_command(self) -> None:
        client = HookClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "read-1",
                        "name": "read_file",
                        "input": {"path": "app.py"},
                    }
                ],
                [{"type": "text", "text": "Read complete."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-user-config-") as base:
            root = Path(base)
            write_user_config_plugin(root)
            install_local_plugin(root, "extensions/demo-plugin")
            set_plugin_user_config_value(root, "demo-plugin", "endpoint", "service.example")
            set_plugin_user_config_value(root, "demo-plugin", "token", "secret-token")
            set_plugin_enabled(root, "demo-plugin", True)
            (root / "app.py").write_text("value = 1\n", encoding="utf-8")

            result = run_agent(
                "Read app.py",
                base_dir=root,
                client=client,
                max_iterations=2,
                approval_handler=lambda _request: ApprovalDecision(
                    approved=True,
                    message="approved",
                ),
            )
            events = (root / ".vibeagent/sessions" / result.run_id / "events.jsonl").read_text(
                encoding="utf-8"
            )
            hook_log = root.joinpath("plugin-hook.log").read_text(encoding="utf-8")
            temporary_environment_files = list(
                (root / ".vibeagent/sessions" / result.run_id).glob(".hook-launch-*")
            )

        self.assertTrue(result.success)
        self.assertEqual(hook_log, "ok")
        self.assertNotIn("secret-token", events)
        self.assertEqual(temporary_environment_files, [])


if __name__ == "__main__":
    unittest.main()
