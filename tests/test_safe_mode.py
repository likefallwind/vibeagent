from __future__ import annotations

import io
import json
import os
from contextlib import redirect_stdout
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from vibeagent import cli as cli_module
from vibeagent.agent_run_setup import prepare_agent_run
from vibeagent.cli_interactive_project_runtime import InteractiveProjectRuntime
from vibeagent.cli_one_shot_setup import resolve_one_shot_project_setup
from vibeagent.cli_project_interactive_commands import run_interactive_project_command
from vibeagent.cli_subagent_panel import SubagentPanel
from vibeagent.command_parsing import LocalCommand
from vibeagent.interactive_background import create_interactive_background_request
from vibeagent.lsp_config import read_lsp_server_configs
from vibeagent.main_agent_settings import resolve_main_agent_selection
from vibeagent.mcp_config import read_mcp_server_configs
from vibeagent.plugin_store import enabled_plugin_manifests
from vibeagent.safe_mode import resolve_safe_mode
from vibeagent.types import AssistantResponse
from vibeagent.workspace_agents import read_project_agents
from vibeagent.workspace_hooks import read_project_hooks
from vibeagent.workspace_memory import read_auto_memory
from vibeagent.workspace_project_instructions import read_project_instruction_sources
from vibeagent.workspace_skills import read_project_skills
from vibeagent.workspace_core import create_run_workspace
from vibeagent.workspace_core import RunWorkspace


class CaptureTextClient:
    def __init__(self) -> None:
        self.messages = []

    def complete(self, messages, tools, **_kwargs):
        self.messages = list(messages)
        return AssistantResponse(
            content=[{"type": "text", "text": "Safe mode inspection complete."}],
            raw={},
        )


class TtyBuffer(io.StringIO):
    def isatty(self) -> bool:
        return True


class SafeModeTests(unittest.TestCase):
    def test_resolves_explicit_and_claude_environment_flags(self) -> None:
        self.assertTrue(resolve_safe_mode(True, {}))
        self.assertTrue(resolve_safe_mode(False, {"CLAUDE_CODE_SAFE_MODE": "YES"}))
        self.assertFalse(resolve_safe_mode(False, {"CLAUDE_CODE_SAFE_MODE": "0"}))

        with patch.dict(os.environ, {"CLAUDE_CODE_SAFE_MODE": "1"}, clear=True):
            args = cli_module.parse_args(["inspect"])

        self.assertTrue(args.safe_mode)
        self.assertTrue(cli_module.build_one_shot_kwargs_from_args(args)["safe_mode"])

    def test_cli_rejects_customization_flags_that_contradict_safe_mode(self) -> None:
        invalid = (
            (["--safe-mode", "--agent", "reviewer", "inspect"], "--agent or --agents"),
            (["--safe-mode", "--agents", '{"reviewer":{"prompt":"x"}}', "inspect"], "--agent or --agents"),
            (["--safe-mode", "--mcp-config", "server.json", "inspect"], "--mcp-config"),
            (["--safe-mode", "--strict-mcp-config", "inspect"], "--mcp-config"),
            (["--safe-mode", "-p", "--maintenance", "inspect"], "Setup hooks"),
        )
        for argv, message in invalid:
            with self.subTest(argv=argv):
                self.assertIn(message, cli_module.validate_cli_args(cli_module.parse_args(argv)) or "")

    def test_safe_workspace_disables_all_supported_customization_loaders(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-safe-mode-") as base:
            root = Path(base)
            self._write_customizations(root)
            workspace = create_run_workspace(
                root,
                "safe-run",
                mcp_config_paths=(root / ".mcp.json",),
                safe_mode=True,
            )

            instructions = read_project_instruction_sources(workspace)
            skills = read_project_skills(workspace)
            agents = read_project_agents(workspace)
            hooks = read_project_hooks(workspace)
            memory = read_auto_memory(workspace)
            mcp = read_mcp_server_configs(workspace)
            lsp = read_lsp_server_configs(workspace)
            selection = resolve_main_agent_selection(workspace, None)
            with patch(
                "vibeagent.plugin_store.list_installed_plugins",
                side_effect=AssertionError("safe mode must not inspect installed plugins"),
            ):
                plugins = enabled_plugin_manifests(root, workspace=workspace)

        self.assertEqual(instructions["files"], [])
        self.assertIn("disabled by safe mode", instructions["message"])
        self.assertEqual(skills["skills"], [])
        self.assertEqual(agents["agents"], [])
        self.assertFalse(hooks.enabled)
        self.assertFalse(memory.enabled)
        self.assertEqual(mcp, [])
        self.assertEqual(lsp, [])
        self.assertIsNone(selection.name)
        self.assertEqual(plugins, [])

    def test_agent_setup_keeps_permissions_and_explicit_prompt_but_omits_custom_content(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-safe-run-") as base:
            root = Path(base)
            self._write_customizations(root)
            permissions = root / ".vibeagent" / "permissions.json"
            permissions.parent.mkdir(parents=True, exist_ok=True)
            permissions.write_text(json.dumps({"deny": ["Bash(git push *)"]}), encoding="utf-8")
            setup = prepare_agent_run(
                "Inspect safely.",
                base_dir=root,
                workspace=None,
                prior_context=None,
                approval_policy="ask",
                task_metadata=None,
                trust_project_permissions=False,
                permission_overrides=None,
                mcp_config_paths=(root / ".mcp.json",),
                strict_mcp_config=False,
                safe_mode=True,
                system_prompt=None,
                append_system_prompt="EXPLICIT_INVOCATION_PROMPT",
            )
            prompt = "\n".join(str(message.content) for message in setup.messages)
            events = [
                json.loads(line)
                for line in (setup.workspace.session_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
            ]

        self.assertTrue(setup.workspace.safe_mode)
        self.assertTrue(setup.project_permissions.enabled)
        self.assertIn("Bash(git push *)", prompt)
        self.assertIn("EXPLICIT_INVOCATION_PROMPT", prompt)
        for marker in (
            "CUSTOM_INSTRUCTION_MARKER",
            "CUSTOM_SKILL_MARKER",
            "CUSTOM_AGENT_MARKER",
            "CUSTOM_MEMORY_MARKER",
        ):
            self.assertNotIn(marker, prompt)
        safe_event = next(event for event in events if event["type"] == "safe_mode")
        self.assertTrue(safe_event["enabled"])
        self.assertIn("plugins", safe_event["disabled"])
        memory_event = next(event for event in events if event["type"] == "auto_memory_loaded")
        self.assertFalse(memory_event["enabled"])
        self.assertNotIn("hooks_loaded", {event["type"] for event in events})

    def test_agent_setup_clears_custom_runtime_state_from_resumed_workspace(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-safe-resume-") as base:
            root = Path(base)
            session_dir = root / ".vibeagent" / "sessions" / "resumed-run"
            session_dir.mkdir(parents=True)
            workspace = RunWorkspace(
                root=root,
                run_id="resumed-run",
                session_dir=session_dir,
                mcp_config_paths=(root / ".mcp.json",),
                strict_mcp_config=True,
                dynamic_agent_profiles=(Mock(),),
                profile_mcp_server_configs=(Mock(),),
            )
            setup = prepare_agent_run(
                "Inspect safely.",
                base_dir=None,
                workspace=workspace,
                prior_context=None,
                approval_policy="ask",
                task_metadata=None,
                trust_project_permissions=False,
                permission_overrides=None,
                mcp_config_paths=(),
                strict_mcp_config=False,
                safe_mode=True,
                system_prompt=None,
                append_system_prompt=None,
                dynamic_agent_profiles=(Mock(),),
            )

        self.assertTrue(setup.workspace.safe_mode)
        self.assertEqual(setup.workspace.mcp_config_paths, ())
        self.assertFalse(setup.workspace.strict_mcp_config)
        self.assertEqual(setup.workspace.dynamic_agent_profiles, ())
        self.assertEqual(setup.workspace.profile_mcp_server_configs, ())

    def test_one_shot_safe_mode_keeps_builtins_but_rejects_custom_slash_commands(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-safe-command-") as base:
            root = Path(base)
            command = root / ".claude" / "commands" / "custom.md"
            command.parent.mkdir(parents=True)
            command.write_text("CUSTOM_COMMAND_BODY", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "disabled by safe mode"):
                resolve_one_shot_project_setup(
                    "/custom",
                    request_mode="code",
                    project_root=root,
                    mcp_config_paths=None,
                    safe_mode=True,
                )
            builtin = resolve_one_shot_project_setup(
                "/code-review",
                request_mode="code",
                project_root=root,
                mcp_config_paths=None,
                safe_mode=True,
            )

        self.assertEqual(builtin.task_metadata["source"], "builtin_command")
        self.assertEqual(builtin.mcp_config_paths, ())

    def test_interactive_catalogs_report_safe_mode_without_loading_commands(self) -> None:
        for command_type, expected in (
            ("custom_commands", "Custom commands"),
            ("agents", "Custom agents"),
            ("skills", "Custom skills"),
            ("instructions", "Project instructions"),
            ("hooks", "Custom hooks"),
        ):
            with self.subTest(command_type=command_type):
                text = run_interactive_project_command(
                    LocalCommand(type=command_type),
                    {},
                    "ask",
                    safe_mode=True,
                )
                self.assertIn(expected, text or "")
                self.assertIn("disabled by safe mode", text or "")

    def test_safe_mode_survives_background_handoff_and_disables_project_services(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-safe-background-") as base:
            root = Path(base)
            request = create_interactive_background_request(
                root,
                "run-1",
                "continue",
                approval_policy="ask",
                model=None,
                agent=None,
                dynamic_agent_profiles=(),
                effort=None,
                autocompact_tokens=None,
                system_prompt=None,
                append_system_prompt=None,
                additional_directories=(),
                safe_mode=True,
            )
            updates = Mock()
            with (
                patch(
                    "vibeagent.cli_interactive_project_runtime.create_peer_runtime",
                    return_value=None,
                ),
                patch(
                    "vibeagent.cli_interactive_project_runtime.PluginAutoUpdateRuntime",
                    return_value=updates,
                ),
            ):
                runtime = InteractiveProjectRuntime(root, "ask", safe_mode=True)
                restarted = runtime.start_plugin_updates()
                runtime.close(())

        self.assertIn("--safe-mode", request.argv)
        updates.start.assert_not_called()
        self.assertFalse(restarted)
        updates.close.assert_called_once_with()

    def test_safe_mode_does_not_resolve_plugin_status_line(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-safe-panel-") as base:
            with patch(
                "vibeagent.cli_subagent_panel.resolve_subagent_status_line",
                side_effect=AssertionError("status line must stay disabled"),
            ) as resolve:
                panel = SubagentPanel(Path(base), stream=TtyBuffer(), safe_mode=True)

        resolve.assert_not_called()
        self.assertIsNone(panel.config)

    def test_interactive_safe_mode_does_not_schedule_directory_hooks(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-safe-add-dir-") as base:
            project = Path(base) / "project"
            shared = Path(base) / "shared"
            project.mkdir()
            shared.mkdir()
            with (
                patch("builtins.input", side_effect=["/add-dir ../shared", "/exit"]),
                patch("vibeagent.cli_interactive.schedule_directory_added_hooks") as schedule,
                redirect_stdout(io.StringIO()),
            ):
                exit_code = cli_module.main(["--safe-mode", "--cwd", str(project)])

        self.assertEqual(exit_code, 0)
        schedule.assert_not_called()

    def test_real_cli_safe_mode_uses_clean_prompt_and_records_boundary(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-safe-cli-") as base:
            root = Path(base)
            self._write_customizations(root)
            client = CaptureTextClient()
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client", return_value=client),
                redirect_stdout(stdout),
            ):
                exit_code = cli_module.main(
                    [
                        "-p",
                        "--output-format",
                        "json",
                        "--safe-mode",
                        "--append-system-prompt",
                        "EXPLICIT_CLI_PROMPT",
                        "--cwd",
                        str(root),
                        "Inspect safely.",
                    ]
                )
            payload = json.loads(stdout.getvalue())
            events = [
                json.loads(line)
                for line in (root / ".vibeagent" / "sessions" / payload["runId"] / "events.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            prompt = "\n".join(str(message.content) for message in client.messages)

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertIn("EXPLICIT_CLI_PROMPT", prompt)
        self.assertNotIn("CUSTOM_INSTRUCTION_MARKER", prompt)
        self.assertNotIn("CUSTOM_MEMORY_MARKER", prompt)
        self.assertIn("safe_mode", {event["type"] for event in events})

    @staticmethod
    def _write_customizations(root: Path) -> None:
        (root / "CLAUDE.md").write_text("CUSTOM_INSTRUCTION_MARKER\n", encoding="utf-8")
        skill = root / ".claude" / "skills" / "custom" / "SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text(
            "---\nname: custom\ndescription: custom skill\n---\nCUSTOM_SKILL_MARKER\n",
            encoding="utf-8",
        )
        agent = root / ".claude" / "agents" / "reviewer.md"
        agent.parent.mkdir(parents=True)
        agent.write_text(
            "---\nname: reviewer\ndescription: custom agent\n---\nCUSTOM_AGENT_MARKER\n",
            encoding="utf-8",
        )
        settings = root / ".claude" / "settings.json"
        settings.write_text(json.dumps({"agent": "reviewer"}), encoding="utf-8")
        hooks = root / ".vibeagent" / "hooks.json"
        hooks.parent.mkdir(parents=True, exist_ok=True)
        hooks.write_text("{ malformed hooks", encoding="utf-8")
        memory = root / ".vibeagent" / "memory" / "MEMORY.md"
        memory.parent.mkdir(parents=True)
        memory.write_text("CUSTOM_MEMORY_MARKER\n", encoding="utf-8")
        (root / ".mcp.json").write_text("{ malformed mcp", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
