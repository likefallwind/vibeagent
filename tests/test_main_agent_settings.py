from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from vibeagent.agent import run_agent
from vibeagent.main_agent_profile import load_main_agent_profile
from vibeagent.main_agent_settings import resolve_main_agent_selection
from vibeagent.plugin_commands import format_plugin_details, reload_plugins_text
from vibeagent.plugin_manifest import read_plugin_manifest
from vibeagent.plugin_store import install_local_plugin, set_plugin_enabled
from vibeagent.types import AssistantResponse, ContentBlock
from vibeagent.workspace_core import create_run_workspace


def _write_agent(path: Path, name: str, prompt: str, *, mode: str = "explore") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\nname: {name}\ndescription: {name} profile\nmode: {mode}\n---\n\n{prompt}\n",
        encoding="utf-8",
    )


def _write_plugin(
    root: Path,
    name: str,
    *,
    default_agent: str | None = "reviewer",
    inline: bool = False,
    root_settings: bool = True,
    subagent_status_line: bool = False,
) -> Path:
    plugin = root / "extensions" / name
    manifest_dir = plugin / ".claude-plugin"
    manifest_dir.mkdir(parents=True)
    _write_agent(plugin / "agents/reviewer.md", "reviewer", f"{name.upper()}_REVIEW_PROMPT")
    manifest: dict[str, object] = {"name": name, "version": "1.0.0"}
    settings: dict[str, object] = {}
    if default_agent is not None:
        settings["agent"] = default_agent
    if subagent_status_line:
        settings["subagentStatusLine"] = {
            "type": "command",
            "command": "printf status",
        }
    if inline:
        manifest["settings"] = dict(settings)
    (manifest_dir / "plugin.json").write_text(json.dumps(manifest), encoding="utf-8")
    if root_settings:
        settings["unknownFutureKey"] = True
        (plugin / "settings.json").write_text(json.dumps(settings), encoding="utf-8")
    return plugin


class ScriptedClient:
    def __init__(self, responses: list[list[ContentBlock]]) -> None:
        self.responses = responses
        self.calls = 0
        self.messages: list[list[object]] = []

    def complete(self, messages, tools=None, **kwargs):
        self.messages.append(list(messages))
        response = self.responses[self.calls]
        self.calls += 1
        return AssistantResponse(content=response, raw={"content": response})


class PluginDefaultSettingsTests(unittest.TestCase):
    def test_root_settings_override_inline_and_inventory_default_agent(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-settings-") as base:
            root = Path(base)
            plugin = _write_plugin(root, "review-tools", inline=True)
            manifest_path = plugin / ".claude-plugin/plugin.json"
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            payload["settings"] = {"agent": "missing-inline-agent"}
            manifest_path.write_text(json.dumps(payload), encoding="utf-8")

            manifest = read_plugin_manifest(plugin)
            details = format_plugin_details(manifest)

        self.assertEqual(manifest.default_agent, "reviewer")
        self.assertEqual(manifest.default_settings_source, "settings.json")
        self.assertEqual(manifest.component_count, 2)
        self.assertEqual(manifest.warnings, ())
        self.assertIn("default agent: reviewer", details)
        self.assertIn("default settings source: settings.json", details)

    def test_inline_settings_include_subagent_status_line_command(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-settings-") as base:
            root = Path(base)
            plugin = _write_plugin(
                root,
                "inline-tools",
                inline=True,
                root_settings=False,
                subagent_status_line=True,
            )

            manifest = read_plugin_manifest(plugin)

        self.assertEqual(manifest.default_agent, "reviewer")
        self.assertEqual(
            manifest.default_settings_source,
            ".claude-plugin/plugin.json:settings",
        )
        self.assertTrue(manifest.has_subagent_status_line)
        self.assertEqual(manifest.subagent_status_line.command, "printf status")
        self.assertEqual(manifest.component_count, 2)
        self.assertEqual(manifest.warnings, ())
        self.assertIn("subagent status line: command", format_plugin_details(manifest))

    def test_invalid_missing_malformed_and_symlink_settings_fail_validation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-settings-") as base:
            root = Path(base)
            missing = _write_plugin(root, "missing-tools", default_agent="missing")
            with self.assertRaisesRegex(ValueError, "not declared"):
                read_plugin_manifest(missing)

            malformed = _write_plugin(root, "malformed-tools")
            malformed.joinpath("settings.json").write_text("{bad", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Could not parse"):
                read_plugin_manifest(malformed)

            invalid_status = _write_plugin(root, "invalid-status", subagent_status_line=True)
            invalid_status.joinpath("settings.json").write_text(
                json.dumps({"agent": "reviewer", "subagentStatusLine": {"type": "text"}}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "type must be 'command'"):
                read_plugin_manifest(invalid_status)

            linked = _write_plugin(root, "linked-tools", root_settings=False)
            outside = root / "outside-settings.json"
            outside.write_text('{"agent":"reviewer"}', encoding="utf-8")
            linked.joinpath("settings.json").symlink_to(outside)
            with self.assertRaisesRegex(ValueError, "non-symlink"):
                read_plugin_manifest(linked)


class MainAgentSettingsTests(unittest.TestCase):
    def test_project_settings_precedence_and_explicit_override(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-settings-") as base:
            root = Path(base)
            _write_agent(root / ".claude/agents/project.md", "project", "PROJECT_PROMPT")
            _write_agent(root / ".claude/agents/local.md", "local", "LOCAL_PROMPT")
            settings_dir = root / ".claude"
            settings_dir.joinpath("settings.json").write_text(
                json.dumps({"agent": "project"}), encoding="utf-8"
            )
            settings_dir.joinpath("settings.local.json").write_text(
                json.dumps({"agent": "local"}), encoding="utf-8"
            )
            _write_plugin(root, "review-tools")
            install_local_plugin(root, "extensions/review-tools")
            workspace = create_run_workspace(root)

            implicit = resolve_main_agent_selection(workspace, None)
            explicit = resolve_main_agent_selection(workspace, "project")

        self.assertEqual((implicit.name, implicit.source), ("local", ".claude/settings.local.json"))
        self.assertEqual((explicit.name, explicit.source), ("project", "explicit"))

    def test_project_setting_can_use_unique_bare_plugin_agent(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-settings-") as base:
            root = Path(base)
            _write_plugin(root, "review-tools", default_agent=None)
            install_local_plugin(root, "extensions/review-tools")
            settings = root / ".claude/settings.json"
            settings.parent.mkdir(parents=True)
            settings.write_text(json.dumps({"agent": "reviewer"}), encoding="utf-8")
            workspace = create_run_workspace(root)

            selection = resolve_main_agent_selection(workspace, None)
            profile = load_main_agent_profile(
                workspace,
                selection.name,
                source=selection.source,
            )

        self.assertEqual(selection.source, ".claude/settings.json")
        self.assertEqual(profile.name, "review-tools:reviewer")

    def test_invalid_and_symlink_project_agent_settings_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-settings-") as base:
            root = Path(base)
            settings = root / ".claude/settings.json"
            settings.parent.mkdir(parents=True)
            settings.write_text(json.dumps({"agent": 3}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "valid agent name"):
                resolve_main_agent_selection(create_run_workspace(root), None)

        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-settings-") as base:
            root = Path(base)
            settings_dir = root / ".claude"
            settings_dir.mkdir()
            outside = root / "outside.json"
            outside.write_text(json.dumps({"agent": "reviewer"}), encoding="utf-8")
            settings_dir.joinpath("settings.local.json").symlink_to(outside)
            with self.assertRaisesRegex(ValueError, "non-symlink"):
                resolve_main_agent_selection(create_run_workspace(root), None)

    def test_enabled_plugin_default_runs_as_namespaced_main_profile(self) -> None:
        client = ScriptedClient([[{"type": "text", "text": "Reviewed."}]])
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-settings-") as base:
            root = Path(base)
            _write_plugin(root, "review-tools")
            install_local_plugin(root, "extensions/review-tools")
            reload_text = reload_plugins_text(root)

            result = run_agent(
                "Review this project",
                client,
                base_dir=root,
                max_iterations=1,
                model_retries=0,
            )
            events = [
                json.loads(line)
                for line in root.joinpath(
                    ".vibeagent", "sessions", result.run_id, "events.jsonl"
                ).read_text(encoding="utf-8").splitlines()
            ]

        self.assertTrue(result.success)
        self.assertIn("default agents=1", reload_text)
        self.assertIn("REVIEW-TOOLS_REVIEW_PROMPT", str(client.messages[0][0].content))
        loaded = next(event for event in events if event["type"] == "main_agent_profile_loaded")
        self.assertEqual(loaded["name"], "review-tools:reviewer")
        self.assertEqual(loaded["source"], "plugin:review-tools:settings.json")

    def test_disabled_plugin_default_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-settings-") as base:
            root = Path(base)
            _write_plugin(root, "review-tools")
            install_local_plugin(root, "extensions/review-tools")
            set_plugin_enabled(root, "review-tools", False)

            selection = resolve_main_agent_selection(create_run_workspace(root), None)

        self.assertIsNone(selection.name)

    def test_unique_bare_plugin_agent_resolves_and_ambiguous_name_fails(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-settings-") as base:
            root = Path(base)
            _write_plugin(root, "first-tools", default_agent=None)
            install_local_plugin(root, "extensions/first-tools")
            workspace = create_run_workspace(root)

            profile = load_main_agent_profile(workspace, "reviewer", source="explicit")

            _write_plugin(root, "second-tools", default_agent=None)
            install_local_plugin(root, "extensions/second-tools")
            ambiguous_workspace = create_run_workspace(root)
            with self.assertRaisesRegex(ValueError, "ambiguous"):
                load_main_agent_profile(ambiguous_workspace, "reviewer")

        self.assertEqual(profile.name, "first-tools:reviewer")

    def test_multiple_plugin_defaults_fail_before_model_request(self) -> None:
        client = ScriptedClient([])
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-settings-") as base:
            root = Path(base)
            _write_plugin(root, "first-tools")
            _write_plugin(root, "second-tools")
            install_local_plugin(root, "extensions/first-tools")
            install_local_plugin(root, "extensions/second-tools")

            with self.assertRaisesRegex(ValueError, "Multiple enabled plugins"):
                run_agent("Inspect", client, base_dir=root)

        self.assertEqual(client.calls, 0)


if __name__ == "__main__":
    unittest.main()
