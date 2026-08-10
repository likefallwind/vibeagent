from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import time
import unittest

from vibeagent.agent import run_agent
from vibeagent.agent_plugin_monitors import inject_plugin_monitor_notifications
from vibeagent.plugin_commands import format_plugin_details, reload_plugins_text
from vibeagent.plugin_manifest import read_plugin_manifest
from vibeagent.plugin_monitor_config import read_plugin_monitor_configs
from vibeagent.plugin_monitor_runtime import PluginMonitorRuntime
from vibeagent.plugin_store import install_local_plugin, set_plugin_enabled
from vibeagent.types import ApprovalDecision, AssistantResponse, ChatMessage, ContentBlock
from vibeagent.workspace_core import create_run_workspace


class ScriptedClient:
    def __init__(self, responses: list[list[ContentBlock]]) -> None:
        self.responses = responses
        self.messages: list[list[ChatMessage]] = []

    def complete(self, messages, tools=None, max_tokens=4096, temperature=0.2, timeout_ms=120_000):
        self.messages.append(list(messages))
        content = self.responses[len(self.messages) - 1]
        return AssistantResponse(content=content, raw={"content": content})


def write_monitor_plugin(
    root: Path,
    *,
    entries: list[dict[str, object]] | None = None,
    inline: bool = False,
) -> Path:
    plugin = root / "extensions" / "watcher"
    manifest_dir = plugin / ".claude-plugin"
    monitor_dir = plugin / "monitors"
    skill_dir = plugin / "skills" / "debug"
    script_dir = plugin / "scripts"
    for directory in (manifest_dir, monitor_dir, skill_dir, script_dir):
        directory.mkdir(parents=True, exist_ok=True)
    selected = entries or [
        {
            "name": "events",
            "command": (
                'python3 -u "${CLAUDE_PLUGIN_ROOT}/scripts/monitor.py" '
                '"${CLAUDE_PLUGIN_DATA}" "${CLAUDE_PROJECT_DIR}" always'
            ),
            "description": "Project event stream",
        }
    ]
    manifest: dict[str, object] = {"name": "watcher", "version": "1.0.0"}
    if inline:
        manifest["experimental"] = {"monitors": selected}
    else:
        manifest["experimental"] = {"monitors": "./monitors/monitors.json"}
        (monitor_dir / "monitors.json").write_text(json.dumps(selected), encoding="utf-8")
    (manifest_dir / "plugin.json").write_text(json.dumps(manifest), encoding="utf-8")
    (skill_dir / "SKILL.md").write_text(
        "---\nname: debug\ndescription: Inspect runtime events.\n---\nInspect events.\n",
        encoding="utf-8",
    )
    (script_dir / "monitor.py").write_text(
        "from pathlib import Path\n"
        "import os, sys, time\n"
        "data, project, mode = sys.argv[1:]\n"
        "Path(data).mkdir(parents=True, exist_ok=True)\n"
        "Path(data, mode + '.pid').write_text(str(os.getpid()), encoding='utf-8')\n"
        "print(f'{mode}|project={project}|data={data}', flush=True)\n"
        "while True:\n"
        "    time.sleep(0.05)\n",
        encoding="utf-8",
    )
    return plugin


def wait_for_notifications(runtime: PluginMonitorRuntime, timeout: float = 2.0):
    deadline = time.monotonic() + timeout
    selected = []
    while time.monotonic() < deadline:
        selected.extend(runtime.collect())
        if any(item.status == "output" for item in selected):
            return selected
        time.sleep(0.02)
    return selected


def process_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


class PluginMonitorTests(unittest.TestCase):
    def test_manifest_file_and_inline_monitors_are_inventoried_and_parsed(self) -> None:
        for inline in (False, True):
            with self.subTest(inline=inline), tempfile.TemporaryDirectory(
                prefix="vibeagent-plugin-monitor-"
            ) as base:
                root = Path(base)
                plugin = write_monitor_plugin(root, inline=inline)
                manifest = read_plugin_manifest(plugin)
                self.assertEqual(manifest.component_count, 2)
                self.assertEqual(len(manifest.monitor_files), 0 if inline else 1)
                self.assertEqual(manifest.inline_monitors is not None, inline)
                install_local_plugin(root, "extensions/watcher")
                configs = read_plugin_monitor_configs(create_run_workspace(root, "run-1"))
                self.assertEqual([(item.plugin, item.name, item.when) for item in configs], [("watcher", "events", "always")])
                self.assertIn("monitors: 1", format_plugin_details(read_plugin_manifest(plugin)))

    def test_real_monitor_emits_expanded_output_and_is_cleaned_up(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-monitor-") as base:
            root = Path(base)
            write_monitor_plugin(root)
            install_local_plugin(root, "extensions/watcher")
            workspace = create_run_workspace(root, "run-1")
            runtime = PluginMonitorRuntime(workspace)
            self.assertEqual(runtime.start_always(lambda _config, _iteration: True), 1)
            notifications = wait_for_notifications(runtime)
            output = next(item for item in notifications if item.status == "output")
            pid_path = root / ".vibeagent" / "plugin-data" / "watcher" / "always.pid"
            pid = int(pid_path.read_text(encoding="utf-8"))
            self.assertIn(f"project={root.resolve()}", output.message)
            self.assertIn(".vibeagent/plugin-data/watcher", output.message)
            self.assertTrue(process_exists(pid))
            runtime.close()
            self.assertFalse(process_exists(pid))

    def test_skill_trigger_starts_once_and_notification_reaches_model(self) -> None:
        entries = [
            {
                "name": "debug-events",
                "command": (
                    'python3 -u "${CLAUDE_PLUGIN_ROOT}/scripts/monitor.py" '
                    '"${CLAUDE_PLUGIN_DATA}" "${CLAUDE_PROJECT_DIR}" skill'
                ),
                "description": "Debug skill event stream",
                "when": "on-skill-invoke:debug",
            }
        ]
        client = ScriptedClient(
            [
                [
                    {"type": "tool_call", "id": "skill-1", "name": "Skill", "input": {"skill": "watcher:debug"}},
                    {"type": "tool_call", "id": "skill-2", "name": "Skill", "input": {"skill": "watcher:debug"}},
                    {"type": "tool_call", "id": "wait-1", "name": "Bash", "input": {"command": "sleep 0.15"}},
                ],
                [{"type": "text", "text": "monitor received"}],
            ]
        )
        requests = []

        def approve(request):
            requests.append(request)
            return ApprovalDecision(approved=True, message="approved")

        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-monitor-") as base:
            root = Path(base)
            write_monitor_plugin(root, entries=entries)
            install_local_plugin(root, "extensions/watcher")
            result = run_agent(
                "Invoke the debug skill",
                base_dir=root,
                client=client,
                max_iterations=2,
                approval_handler=approve,
            )
            pid = int(
                (root / ".vibeagent" / "plugin-data" / "watcher" / "skill.pid").read_text(
                    encoding="utf-8"
                )
            )
            delivered = "\n".join(
                str(message.content) for message in client.messages[1] if message.role == "user"
            )
            events = (root / ".vibeagent" / "sessions" / result.run_id / "events.jsonl").read_text(
                encoding="utf-8"
            )
        self.assertTrue(result.success)
        self.assertIn("Untrusted background notification", delivered)
        self.assertIn("skill|project=", delivered)
        self.assertEqual([request.action_type for request in requests].count("plugin_monitor"), 1)
        self.assertIn("plugin_monitor_notifications_delivered", events)
        self.assertFalse(process_exists(pid))

    def test_crash_stderr_and_unsafe_data_path_are_reported(self) -> None:
        crashed = [
            {
                "name": "crash",
                "command": "printf 'failure detail' >&2; exit 7",
                "description": "Crashing monitor",
            }
        ]
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-monitor-") as base:
            root = Path(base)
            write_monitor_plugin(root, entries=crashed)
            install_local_plugin(root, "extensions/watcher")
            runtime = PluginMonitorRuntime(create_run_workspace(root, "run-1"))
            self.assertEqual(runtime.start_always(lambda _config, _iteration: True), 1)
            deadline = time.monotonic() + 2
            notifications = []
            while time.monotonic() < deadline and not any(
                item.status == "error" for item in notifications
            ):
                notifications.extend(runtime.collect())
                time.sleep(0.02)
            failure = next(item for item in notifications if item.status == "error")
            self.assertIn("code 7", failure.message)
            self.assertIn("failure detail", failure.message)
            runtime.close()

        secret_output = [
            {
                "name": "secret",
                "command": "printf 'API_KEY=secret-token-12345\\n'; sleep 1",
                "description": "Sensitive output monitor",
            }
        ]
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-monitor-") as base:
            root = Path(base)
            write_monitor_plugin(root, entries=secret_output)
            install_local_plugin(root, "extensions/watcher")
            runtime = PluginMonitorRuntime(create_run_workspace(root, "run-1"))
            self.assertEqual(runtime.start_always(lambda _config, _iteration: True), 1)
            output = next(
                item for item in wait_for_notifications(runtime) if item.status == "output"
            )
            self.assertNotIn("secret-token-12345", output.message)
            self.assertIn("[REDACTED]", output.message)
            runtime.close()

        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-monitor-") as base:
            root = Path(base)
            write_monitor_plugin(root)
            install_local_plugin(root, "extensions/watcher")
            runtime = PluginMonitorRuntime(create_run_workspace(root, "run-1"))
            data_root = root / ".vibeagent" / "plugin-data"
            data_root.mkdir(parents=True, exist_ok=True)
            (data_root / "watcher").symlink_to(root / "outside", target_is_directory=True)
            self.assertEqual(runtime.start_always(lambda _config, _iteration: True), 0)
            self.assertIn("symbolic link", runtime.collect()[0].message)
            runtime.close()

    def test_plan_mode_denies_monitor_without_calling_approval_handler(self) -> None:
        client = ScriptedClient([[{"type": "text", "text": "planned"}]])
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-monitor-") as base:
            root = Path(base)
            write_monitor_plugin(root)
            install_local_plugin(root, "extensions/watcher")
            result = run_agent(
                "Plan only",
                base_dir=root,
                client=client,
                max_iterations=1,
                approval_policy="plan",
                approval_handler=lambda _request: self.fail("approval handler must not run in plan mode"),
            )
            user_text = "\n".join(
                str(message.content) for message in client.messages[0] if message.role == "user"
            )
        self.assertTrue(result.success)
        self.assertIn('"status": "denied"', user_text)
        self.assertIn("startup was denied", user_text)

    def test_malformed_blocked_and_disabled_monitors_fail_safely(self) -> None:
        malformed = [{"name": "bad", "command": "echo bad", "description": "Bad", "when": "later"}]
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-monitor-") as base:
            root = Path(base)
            write_monitor_plugin(root, entries=malformed)
            install_local_plugin(root, "extensions/watcher")
            workspace = create_run_workspace(root, "run-1")
            runtime = PluginMonitorRuntime(workspace)
            self.assertIn("when must be", runtime.load_error or "")
            runtime.start_always(lambda _config, _iteration: True)
            messages: list[ChatMessage] = []
            self.assertEqual(
                inject_plugin_monitor_notifications(runtime, workspace, messages, iteration=1, logger=None),
                1,
            )
            self.assertIn("configuration", str(messages[0].content))
            runtime.close()

        blocked = [{"name": "bad", "command": "sudo true", "description": "Bad command"}]
        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-monitor-") as base:
            root = Path(base)
            write_monitor_plugin(root, entries=blocked)
            install_local_plugin(root, "extensions/watcher")
            runtime = PluginMonitorRuntime(create_run_workspace(root, "run-1"))
            self.assertEqual(runtime.start_always(lambda _config, _iteration: True), 0)
            self.assertIn("Command blocked", runtime.collect()[0].message)
            runtime.close()

        with tempfile.TemporaryDirectory(prefix="vibeagent-plugin-monitor-") as base:
            root = Path(base)
            write_monitor_plugin(root)
            install_local_plugin(root, "extensions/watcher")
            set_plugin_enabled(root, "watcher", False)
            runtime = PluginMonitorRuntime(create_run_workspace(root, "run-1"))
            self.assertEqual(runtime.configs, ())
            self.assertEqual(runtime.start_always(lambda _config, _iteration: True), 0)
            self.assertIn("monitors=0", reload_plugins_text(root))
            runtime.close()


if __name__ == "__main__":
    unittest.main()
