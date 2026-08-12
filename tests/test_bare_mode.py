from __future__ import annotations

import io
import json
from contextlib import redirect_stdout
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from tests.test_plugins import write_demo_plugin
from tests.user_home_test_case import IsolatedUserHomeTestCase
from vibeagent import cli as cli_module
from vibeagent.agent_result import AgentResult
from vibeagent.agent_run_setup import prepare_agent_run
from vibeagent.cli_startup_context import resolve_interactive_startup_context
from vibeagent.cli_config import build_provider_env
from vibeagent.dynamic_agent_profiles import parse_dynamic_agent_profiles
from vibeagent.interactive_background import create_interactive_background_request
from vibeagent.mcp_config import read_mcp_server_configs
from vibeagent.plugin_store import enabled_plugin_manifests
from vibeagent.workspace_agents import read_project_agents
from vibeagent.workspace_core import create_run_workspace
from vibeagent.workspace_hooks import read_project_hooks
from vibeagent.workspace_memory import read_auto_memory
from vibeagent.workspace_project_instructions import read_project_instruction_sources
from vibeagent.workspace_prompt_commands import read_project_prompt_commands
from vibeagent.workspace_skills import read_project_skills


class BareModeTests(IsolatedUserHomeTestCase):
    def test_cli_propagates_bare_mode_and_rejects_safe_mode_combination(self) -> None:
        args = cli_module.parse_args(["--bare", "inspect"])

        self.assertTrue(args.bare)
        kwargs = cli_module.build_one_shot_kwargs_from_args(args)
        self.assertTrue(kwargs["bare_mode"])
        self.assertEqual(kwargs["setting_sources"], ())
        self.assertEqual(
            cli_module.validate_cli_args(
                cli_module.parse_args(
                    ["--bare", "--setting-sources", "project", "inspect"]
                )
            ),
            "--bare does not load settings files; pass explicit settings with --settings.",
        )
        self.assertEqual(
            cli_module.validate_cli_args(
                cli_module.parse_args(["--bare", "--safe-mode", "inspect"])
            ),
            "--safe-mode and --bare cannot be combined.",
        )

    def test_bare_workspace_skips_automatic_customization_sources(self) -> None:
        with TemporaryDirectory(prefix="vibeagent-bare-") as temporary:
            root = Path(temporary)
            self._write_automatic_customizations(root)
            workspace = create_run_workspace(root, "bare-run", bare_mode=True)

            instructions = read_project_instruction_sources(workspace)
            skills = read_project_skills(workspace)
            agents = read_project_agents(workspace)
            hooks = read_project_hooks(workspace)
            memory = read_auto_memory(workspace)
            mcp = read_mcp_server_configs(workspace)
            commands = read_project_prompt_commands(root, workspace=workspace)
            with patch(
                "vibeagent.plugin_store.list_installed_plugins",
                side_effect=AssertionError("bare mode must not inspect installed plugins"),
            ):
                plugins = enabled_plugin_manifests(root, workspace=workspace)

        self.assertEqual(instructions["files"], [])
        self.assertIn("bare mode", instructions["message"])
        self.assertEqual(skills["skills"], [])
        self.assertEqual(agents["agents"], [])
        self.assertFalse(hooks.enabled)
        self.assertFalse(memory.enabled)
        self.assertEqual(mcp, [])
        self.assertEqual(commands["commands"], [])
        self.assertEqual(plugins, [])

    def test_bare_provider_environment_uses_only_explicit_settings(self) -> None:
        with TemporaryDirectory(prefix="vibeagent-bare-env-") as temporary:
            root = Path(temporary)
            settings = root / ".claude/settings.json"
            settings.parent.mkdir(parents=True)
            settings.write_text(
                json.dumps({"env": {"BARE_AUTO_SETTING": "blocked"}}),
                encoding="utf-8",
            )
            args = cli_module.parse_args(
                [
                    "--bare",
                    "--settings",
                    '{"env":{"BARE_EXPLICIT_SETTING":"kept"}}',
                    "inspect",
                ]
            )

            env = build_provider_env(args, root)

        self.assertNotIn("BARE_AUTO_SETTING", env)
        self.assertEqual(env["BARE_EXPLICIT_SETTING"], "kept")

    def test_bare_workspace_retains_explicit_agents_mcp_settings_and_plugins(self) -> None:
        with TemporaryDirectory(prefix="vibeagent-bare-explicit-") as temporary:
            root = Path(temporary)
            self._write_automatic_customizations(root)
            plugin = write_demo_plugin(root)
            explicit_mcp = root / "explicit-mcp.json"
            explicit_mcp.write_text(
                json.dumps(
                    {
                        "mcpServers": {
                            "explicit.echo": {
                                "command": "python3",
                                "args": ["-c", "print('unused')"],
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            profiles = parse_dynamic_agent_profiles(
                json.dumps(
                    {
                        "cli-reviewer": {
                            "description": "Explicit reviewer",
                            "prompt": "Review only explicit evidence.",
                        }
                    }
                )
            )
            workspace = replace(
                create_run_workspace(
                    root,
                    "bare-explicit-run",
                    bare_mode=True,
                    mcp_config_paths=(explicit_mcp,),
                    invocation_plugin_dirs=(plugin,),
                    settings_override_json=json.dumps(
                        {
                            "hooks": {
                                "Stop": [
                                    {
                                        "hooks": [
                                            {"type": "command", "command": "echo explicit"}
                                        ]
                                    }
                                ]
                            }
                        }
                    ),
                ),
                dynamic_agent_profiles=profiles,
            )

            manifests = enabled_plugin_manifests(root, workspace=workspace)
            skills = read_project_skills(workspace)
            agents = read_project_agents(workspace)
            hooks = read_project_hooks(workspace)
            mcp = read_mcp_server_configs(workspace)
            commands = read_project_prompt_commands(root, workspace=workspace)
            explicit_setup = prepare_agent_run(
                "Inspect.",
                base_dir=root,
                workspace=None,
                prior_context=None,
                approval_policy="ask",
                task_metadata=None,
                trust_project_permissions=False,
                permission_overrides=None,
                mcp_config_paths=(),
                strict_mcp_config=False,
                bare_mode=True,
                setting_sources=(),
                settings_override_json=None,
                invocation_plugin_dirs=(plugin,),
                system_prompt=None,
                append_system_prompt=None,
                agent="cli-reviewer",
                dynamic_agent_profiles=profiles,
            )

        self.assertEqual([manifest.name for manifest in manifests], ["demo-plugin"])
        self.assertEqual(
            {item["name"] for item in skills["skills"]},
            {"demo-plugin:review"},
        )
        self.assertEqual(
            {item["name"] for item in agents["agents"]},
            {"cli-reviewer", "demo-plugin:reviewer"},
        )
        self.assertEqual(len(hooks.hooks), 2)
        self.assertNotIn(".vibeagent/hooks.json", hooks.sources)
        self.assertIn("CLI --settings", hooks.sources)
        self.assertEqual(
            {server.name for server in mcp},
            {"demo-plugin.echo", "explicit.echo"},
        )
        self.assertEqual(
            {item["name"] for item in commands["commands"]},
            {"demo-plugin:fix"},
        )
        self.assertEqual(explicit_setup.main_profile.name, "cli-reviewer")

    def test_agent_run_records_bare_boundary_and_keeps_explicit_prompt(self) -> None:
        with TemporaryDirectory(prefix="vibeagent-bare-run-") as temporary:
            root = Path(temporary)
            self._write_automatic_customizations(root)
            (root / ".vibeagent/permissions.json").write_text(
                json.dumps({"deny": ["Bash(git push *)"]}),
                encoding="utf-8",
            )
            setup = prepare_agent_run(
                "Inspect deterministically.",
                base_dir=root,
                workspace=None,
                prior_context=None,
                approval_policy="ask",
                task_metadata=None,
                trust_project_permissions=False,
                permission_overrides=None,
                mcp_config_paths=(),
                strict_mcp_config=False,
                bare_mode=True,
                system_prompt=None,
                append_system_prompt="EXPLICIT_PROMPT",
            )
            prompt = "\n".join(str(message.content) for message in setup.messages)
            events = [
                json.loads(line)
                for line in (setup.workspace.session_dir / "events.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]

        self.assertTrue(setup.workspace.bare_mode)
        self.assertTrue(setup.project_permissions.enabled)
        self.assertIn("Bash(git push *)", prompt)
        self.assertIn("EXPLICIT_PROMPT", prompt)
        self.assertNotIn("AUTO_INSTRUCTION", prompt)
        self.assertNotIn("AUTO_MEMORY", prompt)
        bare_event = next(event for event in events if event["type"] == "bare_mode")
        self.assertIn("plugins", bare_event["auto_discovery_disabled"])

    def test_cli_resume_and_interactive_background_preserve_bare_mode(self) -> None:
        with TemporaryDirectory(prefix="vibeagent-bare-resume-") as temporary:
            root = Path(temporary)
            source = create_run_workspace(root, "source-run")
            (source.session_dir / "events.jsonl").write_text(
                json.dumps({"type": "task", "task": "source"}) + "\n",
                encoding="utf-8",
            )
            context = resolve_interactive_startup_context(
                cli_module.parse_args(["--bare", "--resume", "source-run"]),
                root,
                get_resume_context_func=Mock(
                    return_value=("source-run", "source context", "loaded")
                ),
                get_compact_context_func=Mock(),
            )
            request = create_interactive_background_request(
                root,
                "source-run",
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
                bare_mode=True,
            )

        self.assertTrue(context.bare_mode)
        self.assertEqual(context.setting_sources, ())
        self.assertTrue(context.pending_workspace.bare_mode)  # type: ignore[union-attr]
        self.assertIn("--bare", request.argv)

    def test_real_cli_passes_bare_mode_to_agent_without_changing_stdout(self) -> None:
        with TemporaryDirectory(prefix="vibeagent-bare-cli-") as temporary:
            root = Path(temporary)
            run_agent = Mock(
                return_value=AgentResult(True, "done", root, "bare-cli-run", 1, [], [])
            )
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(stdout),
            ):
                exit_code = cli_module.main(
                    ["-p", "--bare", "--cwd", root.as_posix(), "inspect"]
                )

        self.assertEqual(exit_code, 0)
        self.assertTrue(run_agent.call_args.kwargs["bare_mode"])
        self.assertEqual(stdout.getvalue(), "done\n")

    def test_real_cli_bare_mode_expands_only_explicit_plugin_commands(self) -> None:
        with TemporaryDirectory(prefix="vibeagent-bare-plugin-cli-") as temporary:
            root = Path(temporary)
            plugin = write_demo_plugin(root)
            run_agent = Mock(
                return_value=AgentResult(True, "done", root, "bare-plugin-run", 1, [], [])
            )
            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = cli_module.main(
                    [
                        "-p",
                        "--bare",
                        "--cwd",
                        root.as_posix(),
                        "--plugin-dir",
                        plugin.as_posix(),
                        "/demo-plugin:fix parser",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Inspect parser", run_agent.call_args.args[0])
        self.assertEqual(run_agent.call_args.kwargs["invocation_plugin_dirs"], (plugin.resolve(),))

    def _write_automatic_customizations(self, root: Path) -> None:
        (root / "CLAUDE.md").write_text("AUTO_INSTRUCTION\n", encoding="utf-8")
        skill = root / ".claude/skills/auto"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            "---\nname: auto\ndescription: Automatic skill\n---\nAUTO_SKILL\n",
            encoding="utf-8",
        )
        command = root / ".claude/commands/auto.md"
        command.parent.mkdir(parents=True, exist_ok=True)
        command.write_text(
            "---\ndescription: Automatic command\n---\nAUTO_COMMAND\n",
            encoding="utf-8",
        )
        agent = root / ".claude/agents/auto.md"
        agent.parent.mkdir(parents=True, exist_ok=True)
        agent.write_text(
            "---\nname: auto\ndescription: Automatic agent\n---\nAUTO_AGENT\n",
            encoding="utf-8",
        )
        hooks = root / ".vibeagent/hooks.json"
        hooks.parent.mkdir(parents=True, exist_ok=True)
        hooks.write_text(
            json.dumps(
                {
                    "hooks": {
                        "Stop": [
                            {"hooks": [{"type": "command", "command": "echo automatic"}]}
                        ]
                    }
                }
            ),
            encoding="utf-8",
        )
        (root / ".mcp.json").write_text(
            json.dumps(
                {
                    "mcpServers": {
                        "automatic.echo": {
                            "command": "python3",
                            "args": ["-c", "print('unused')"],
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        memory = root / ".vibeagent/memory"
        memory.mkdir(parents=True)
        (memory / "MEMORY.md").write_text("AUTO_MEMORY\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
