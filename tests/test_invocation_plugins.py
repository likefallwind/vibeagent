from __future__ import annotations

import io
import json
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from tests.test_invocation_plugin_archives import write_plugin_zip
from tests.lsp_test_support import write_lsp_plugin
from tests.test_plugin_monitors import write_monitor_plugin
from tests.test_plugins import write_demo_plugin
from tests.user_home_test_case import IsolatedUserHomeTestCase
from vibeagent.agent_result import AgentResult
from vibeagent.agent_run_setup import prepare_agent_run
from vibeagent.cli import main
from vibeagent.cli_args import parse_args
from vibeagent.cli_startup_context import resolve_interactive_startup_context
from vibeagent.cli_validation import validate_cli_args
from vibeagent.invocation_plugins import resolve_invocation_plugin_dirs
from vibeagent.interactive_background import create_interactive_background_request
from vibeagent.lsp_config import read_lsp_server_configs
from vibeagent.mcp_config import read_mcp_server_configs
from vibeagent.plugin_environment import enabled_plugin_bin_paths
from vibeagent.plugin_manifest import read_plugin_manifest
from vibeagent.plugin_monitor_config import read_plugin_monitor_configs
from vibeagent.plugin_store import enabled_plugin_manifests, install_local_plugin
from vibeagent.workspace_agents import read_project_agents
from vibeagent.workspace_core import create_run_workspace
from vibeagent.workspace_hooks import read_project_hooks
from vibeagent.workspace_prompt_commands import (
    expand_project_prompt_command,
    read_project_prompt_commands,
)
from vibeagent.workspace_skills import read_project_skills


class InvocationPluginTests(IsolatedUserHomeTestCase):
    def test_resolves_relative_directories_deduplicates_and_rejects_symlinks(
        self,
    ) -> None:
        with TemporaryDirectory(prefix="vibeagent-invocation-plugin-") as temporary:
            root = Path(temporary)
            plugin = write_demo_plugin(root)

            resolved = resolve_invocation_plugin_dirs(
                ["extensions/demo-plugin", "extensions/demo-plugin"],
                invocation_root=root,
            )
            self.assertEqual(resolved, (plugin.resolve(),))

            linked = root / "linked-plugin"
            linked.symlink_to(plugin, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "non-symlink"):
                resolve_invocation_plugin_dirs(["linked-plugin"], invocation_root=root)

    def test_rejects_duplicate_explicit_plugin_names(self) -> None:
        with TemporaryDirectory(prefix="vibeagent-invocation-plugin-") as temporary:
            root = Path(temporary)
            first = write_demo_plugin(root)
            second = root / "second"
            second.mkdir()
            (second / ".claude-plugin").mkdir()
            (second / ".claude-plugin/plugin.json").write_text(
                json.dumps({"name": "demo-plugin"}),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                ValueError, "duplicate plugin name demo-plugin"
            ):
                resolve_invocation_plugin_dirs(
                    [str(first), str(second)], invocation_root=root
                )

    def test_uninstalled_directories_load_all_plugin_component_families(self) -> None:
        with TemporaryDirectory(prefix="vibeagent-invocation-plugin-") as temporary:
            root = Path(temporary)
            demo = write_demo_plugin(root)
            (demo / "bin/check").chmod(0o755)
            lsp = write_lsp_plugin(root)
            monitor = write_monitor_plugin(root)
            workspace = create_run_workspace(
                root,
                "run-1",
                invocation_plugin_dirs=(demo, lsp, monitor),
            )

            manifests = enabled_plugin_manifests(root, workspace=workspace)
            skills = read_project_skills(workspace)
            agents = read_project_agents(workspace)
            hooks = read_project_hooks(workspace)
            mcp = read_mcp_server_configs(workspace)
            lsp_configs = read_lsp_server_configs(workspace)
            monitors = read_plugin_monitor_configs(workspace)
            bin_paths = enabled_plugin_bin_paths(workspace)
            command = expand_project_prompt_command(
                root,
                "/demo-plugin:fix parser",
                workspace=workspace,
            )
            command_catalog = read_project_prompt_commands(root, workspace=workspace)

        self.assertEqual(
            {manifest.name for manifest in manifests},
            {"demo-plugin", "python-lsp", "watcher"},
        )
        self.assertIn("demo-plugin:review", {item["name"] for item in skills["skills"]})
        self.assertIn(
            "demo-plugin:reviewer", {item["name"] for item in agents["agents"]}
        )
        self.assertEqual(len(hooks.hooks), 1)
        self.assertEqual([server.name for server in mcp], ["demo-plugin.echo"])
        self.assertEqual([config.name for config in lsp_configs], ["python-lsp.python"])
        self.assertEqual([config.name for config in monitors], ["events"])
        self.assertIn(demo / "bin", bin_paths)
        self.assertIn("Inspect parser", str(command["prompt"]))  # type: ignore[index]
        self.assertIn(demo.as_posix(), str(command["prompt"]))  # type: ignore[index]
        self.assertIn(
            "demo-plugin:fix", {item["name"] for item in command_catalog["commands"]}
        )

    def test_explicit_directory_overrides_installed_plugin_with_same_name(self) -> None:
        with TemporaryDirectory(prefix="vibeagent-invocation-plugin-") as temporary:
            root = Path(temporary)
            plugin = write_demo_plugin(root)
            install_local_plugin(root, "extensions/demo-plugin")
            (plugin / "commands/fix.md").write_text(
                "---\ndescription: Invocation override\n---\nINVOCATION_PLUGIN $ARGUMENTS\n",
                encoding="utf-8",
            )
            workspace = create_run_workspace(
                root, "run-1", invocation_plugin_dirs=(plugin,)
            )

            manifests = enabled_plugin_manifests(root, workspace=workspace)
            expanded = expand_project_prompt_command(
                root,
                "/demo-plugin:fix target",
                workspace=workspace,
            )

        selected = [
            manifest for manifest in manifests if manifest.name == "demo-plugin"
        ]
        self.assertEqual([manifest.root for manifest in selected], [plugin.resolve()])
        self.assertEqual(expanded["prompt"], "INVOCATION_PLUGIN target")  # type: ignore[index]

    def test_cli_propagates_plugin_dirs_and_settings_to_persistent_one_shot(
        self,
    ) -> None:
        with TemporaryDirectory(prefix="vibeagent-invocation-plugin-") as temporary:
            root = Path(temporary)
            plugin = write_demo_plugin(root)
            result = AgentResult(True, "done", root, "run-1", 1, [], [])
            run_agent = Mock(return_value=result)
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        root.as_posix(),
                        "--plugin-dir",
                        plugin.as_posix(),
                        "--settings",
                        '{"env":{"INVOCATION_CHAIN":"yes"}}',
                        "inspect",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            run_agent.call_args.kwargs["invocation_plugin_dirs"], (plugin.resolve(),)
        )
        self.assertEqual(
            run_agent.call_args.kwargs["settings_override_json"],
            '{"env":{"INVOCATION_CHAIN":"yes"}}',
        )

    def test_cli_materializes_zip_before_persistent_one_shot(self) -> None:
        with TemporaryDirectory(prefix="vibeagent-invocation-plugin-") as temporary:
            root = Path(temporary)
            plugin = write_demo_plugin(root)
            archive = write_plugin_zip(plugin, root / "demo-plugin.zip", wrapped=True)
            result = AgentResult(True, "done", root, "run-zip", 1, [], [])
            run_agent = Mock(return_value=result)
            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        root.as_posix(),
                        "--plugin-dir",
                        archive.as_posix(),
                        "inspect",
                    ]
                )

        resolved = run_agent.call_args.kwargs["invocation_plugin_dirs"]
        self.assertEqual(exit_code, 0)
        self.assertEqual(len(resolved), 1)
        self.assertIn("invocation-plugin-cache", resolved[0].as_posix())
        self.assertEqual(read_plugin_manifest(resolved[0]).name, "demo-plugin")

    def test_safe_mode_rejects_plugin_dir(self) -> None:
        args = parse_args(["--safe-mode", "--plugin-dir", ".", "inspect"])
        self.assertEqual(
            validate_cli_args(args),
            "--safe-mode cannot be combined with --plugin-dir.",
        )

    def test_chat_and_local_commands_reject_plugin_dir(self) -> None:
        for argv in (
            ["--plugin-dir", ".", "--chat", "hello"],
            ["--plugin-dir", ".", "--version"],
        ):
            with self.subTest(argv=argv):
                self.assertEqual(
                    validate_cli_args(parse_args(argv)),
                    "--plugin-dir requires an interactive or one-shot coding session.",
                )

    def test_resume_fork_preserves_invocation_plugin_dirs(self) -> None:
        with TemporaryDirectory(prefix="vibeagent-invocation-plugin-") as temporary:
            root = Path(temporary)
            plugin = write_demo_plugin(root)
            source = create_run_workspace(root, "run-1")
            source.session_dir.mkdir(parents=True, exist_ok=True)
            (source.session_dir / "events.jsonl").write_text(
                json.dumps({"type": "task", "task": "source"}) + "\n",
                encoding="utf-8",
            )
            args = parse_args(
                [
                    "--plugin-dir",
                    plugin.as_posix(),
                    "--resume",
                    "run-1",
                    "--fork-session",
                ]
            )

            context = resolve_interactive_startup_context(
                args,
                root,
                get_resume_context_func=Mock(
                    return_value=("run-1", "source context", "Resume loaded.")
                ),
                get_compact_context_func=Mock(),
            )

        self.assertIsNone(context.error)
        self.assertEqual(context.invocation_plugin_dirs, (plugin.resolve(),))
        self.assertEqual(
            context.pending_workspace.invocation_plugin_dirs,  # type: ignore[union-attr]
            (plugin.resolve(),),
        )

    def test_interactive_background_forwards_plugin_dirs(self) -> None:
        with TemporaryDirectory(prefix="vibeagent-invocation-plugin-") as temporary:
            root = Path(temporary)
            plugin = write_demo_plugin(root)
            request = create_interactive_background_request(
                root,
                "run-1",
                None,
                approval_policy="ask",
                model=None,
                agent=None,
                dynamic_agent_profiles=(),
                effort=None,
                autocompact_tokens=None,
                system_prompt=None,
                append_system_prompt=None,
                additional_directories=(),
                invocation_plugin_dirs=(plugin.resolve(),),
            )

        index = request.argv.index("--plugin-dir")
        self.assertEqual(request.argv[index + 1], plugin.resolve().as_posix())

    def test_agent_event_records_count_without_plugin_paths(self) -> None:
        with TemporaryDirectory(prefix="vibeagent-invocation-plugin-") as temporary:
            root = Path(temporary)
            plugin = write_demo_plugin(root)
            setup = prepare_agent_run(
                "inspect",
                base_dir=root,
                workspace=None,
                prior_context=None,
                approval_policy="ask",
                task_metadata=None,
                trust_project_permissions=False,
                permission_overrides=None,
                mcp_config_paths=(),
                strict_mcp_config=False,
                system_prompt=None,
                append_system_prompt=None,
                invocation_plugin_dirs=(plugin.resolve(),),
            )
            events_text = (setup.workspace.session_dir / "events.jsonl").read_text(
                encoding="utf-8"
            )
            events = [json.loads(line) for line in events_text.splitlines()]

        loaded = next(
            event for event in events if event["type"] == "invocation_plugins_loaded"
        )
        self.assertEqual(loaded["count"], 1)
        self.assertNotIn(plugin.as_posix(), events_text)


if __name__ == "__main__":
    unittest.main()
