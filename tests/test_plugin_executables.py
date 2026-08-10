from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest

from vibeagent.actions import execute_action
from vibeagent.command_sandbox import prepare_command_launch
from vibeagent.plugin_environment import enabled_plugin_bin_paths
from vibeagent.plugin_commands import reload_plugins_text
from vibeagent.plugin_manifest import read_plugin_manifest
from vibeagent.plugin_store import install_local_plugin, set_plugin_enabled
from vibeagent.runtime_checks import build_command_check_observation
from vibeagent.types import (
    RunCommandAction,
    StartCommandAction,
    StopProcessAction,
    WaitProcessAction,
)
from vibeagent.workspace_core import create_run_workspace
from vibeagent.workspace_sandbox import read_workspace_sandbox


TOOL_NAME = "vibeagent-plugin-test-tool"


def plugin_sandbox_available() -> bool:
    with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-bin-probe-") as base:
        root = Path(base)
        config = root / ".vibeagent" / "sandbox.json"
        config.parent.mkdir()
        config.write_text(
            json.dumps({"enabled": True, "failIfUnavailable": True}),
            encoding="utf-8",
        )
        return read_workspace_sandbox(create_run_workspace(root, "probe-run")).available


def write_executable_plugin(
    root: Path,
    name: str,
    output: str,
    *,
    tool_name: str = TOOL_NAME,
) -> Path:
    plugin = root / "extensions" / name
    (plugin / ".claude-plugin").mkdir(parents=True)
    (plugin / "bin").mkdir()
    (plugin / ".claude-plugin" / "plugin.json").write_text(
        json.dumps({"name": name, "description": f"{name} executable plugin"}),
        encoding="utf-8",
    )
    executable = plugin / "bin" / tool_name
    executable.write_text(
        f"#!/bin/sh\nprintf '%s:%s\\n' {output!r} \"$1\"\n",
        encoding="utf-8",
    )
    executable.chmod(0o755)
    (plugin / "bin" / "README.txt").write_text("not executable\n", encoding="utf-8")
    return plugin


class PluginExecutableTests(unittest.TestCase):
    def test_manifest_inventories_only_executable_bin_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-bin-") as base:
            plugin = write_executable_plugin(Path(base), "demo-bin", "demo")
            manifest = read_plugin_manifest(plugin)

        self.assertEqual(manifest.component_count, 1)
        self.assertEqual([path.name for path in manifest.bin_files], [TOOL_NAME])

    def test_enabled_plugin_executes_and_preflight_tracks_disable(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-bin-") as base:
            root = Path(base)
            write_executable_plugin(root, "demo-bin", "foreground")
            installed = install_local_plugin(root, "extensions/demo-bin")
            workspace = create_run_workspace(root, "run-1")

            check = build_command_check_observation(workspace, f"{TOOL_NAME} value", None)
            observation = execute_action(
                workspace,
                RunCommandAction(type="run_command", command=f"{TOOL_NAME} value"),
            )
            self.assertEqual(installed.component_count, 1)
            self.assertIn("executables=1", reload_plugins_text(root))
            self.assertTrue(check.ok)
            self.assertEqual(observation.result.exit_code, 0)
            self.assertEqual(observation.result.stdout, "foreground:value\n")

            set_plugin_enabled(root, "demo-bin", False)
            disabled_check = build_command_check_observation(workspace, TOOL_NAME, None)
            self.assertFalse(disabled_check.ok)
            self.assertEqual(disabled_check.missing_tool, TOOL_NAME)
            self.assertEqual(enabled_plugin_bin_paths(workspace), ())

    def test_background_commands_inherit_plugin_path(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-bin-") as base:
            root = Path(base)
            write_executable_plugin(root, "demo-bin", "background")
            install_local_plugin(root, "extensions/demo-bin")
            workspace = create_run_workspace(root, "run-1")
            start = execute_action(
                workspace,
                StartCommandAction(type="start_command", command=f"{TOOL_NAME} async"),
            )
            try:
                wait = execute_action(
                    workspace,
                    WaitProcessAction(
                        type="wait_process",
                        process_id=start.process_id,
                        timeout_ms=5_000,
                    ),
                )
                self.assertTrue(start.ok)
                self.assertEqual(wait.exit_code, 0)
                self.assertEqual(wait.stdout, "background:async\n")
            finally:
                if start.process_id:
                    execute_action(
                        workspace,
                        StopProcessAction(type="stop_process", process_id=start.process_id),
                    )

    def test_plugin_name_order_resolves_executable_collisions(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-bin-") as base:
            root = Path(base)
            write_executable_plugin(root, "zeta-bin", "zeta")
            write_executable_plugin(root, "alpha-bin", "alpha")
            install_local_plugin(root, "extensions/zeta-bin")
            install_local_plugin(root, "extensions/alpha-bin")
            workspace = create_run_workspace(root, "run-1")

            paths = enabled_plugin_bin_paths(workspace)
            observation = execute_action(
                workspace,
                RunCommandAction(type="run_command", command=f"{TOOL_NAME} selected"),
            )

        self.assertEqual([path.parent.name for path in paths], ["alpha-bin", "zeta-bin"])
        self.assertEqual(observation.result.stdout, "alpha:selected\n")

    def test_sandbox_launch_receives_scoped_environment_without_global_mutation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-bin-") as base:
            root = Path(base)
            write_executable_plugin(root, "demo-bin", "sandbox")
            install_local_plugin(root, "extensions/demo-bin")
            workspace = create_run_workspace(root, "run-1")

            original_path = os.environ.get("PATH")
            launch = prepare_command_launch(workspace, TOOL_NAME, root)
            plugin_bin = root / ".vibeagent" / "plugins" / "cache" / "demo-bin" / "bin"

        self.assertIsNotNone(launch.environment)
        self.assertEqual(
            str(launch.environment["PATH"]).split(os.pathsep, 1)[0],
            plugin_bin.as_posix(),
        )
        self.assertEqual(os.environ.get("PATH"), original_path)

    @unittest.skipUnless(plugin_sandbox_available(), "bubblewrap sandbox is unavailable")
    def test_plugin_executable_runs_inside_bubblewrap(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-bin-") as base:
            root = Path(base)
            write_executable_plugin(root, "demo-bin", "sandboxed")
            install_local_plugin(root, "extensions/demo-bin")
            config = root / ".vibeagent" / "sandbox.json"
            config.write_text(
                json.dumps({"enabled": True, "failIfUnavailable": True}),
                encoding="utf-8",
            )
            workspace = create_run_workspace(root, "run-1")

            observation = execute_action(
                workspace,
                RunCommandAction(type="run_command", command=f"{TOOL_NAME} isolated"),
            )

        self.assertTrue(observation.result.sandboxed)
        self.assertEqual(observation.result.exit_code, 0)
        self.assertEqual(observation.result.stdout, "sandboxed:isolated\n")


if __name__ == "__main__":
    unittest.main()
