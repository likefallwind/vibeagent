from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from vibeagent.background_delegate_types import BackgroundDelegateSnapshot
from vibeagent.cli_subagent_panel import SubagentPanel
from vibeagent.plugin_store import install_local_plugin
from vibeagent.plugin_subagent_status_line import (
    ResolvedSubagentStatusLine,
    resolve_subagent_status_line,
    run_subagent_status_line,
)
from vibeagent.types import DelegateTaskAction
from vibeagent.workspace_core import create_run_workspace


class TtyBuffer:
    def __init__(self) -> None:
        self.value = ""

    def isatty(self) -> bool:
        return True

    def write(self, value: str) -> int:
        self.value += value
        return len(value)

    def flush(self) -> None:
        return None


def write_status_plugin(root: Path) -> None:
    plugin = root / "extensions" / "status-tools"
    (plugin / ".claude-plugin").mkdir(parents=True)
    (plugin / ".claude-plugin" / "plugin.json").write_text(
        json.dumps({"name": "status-tools", "version": "1.0.0"}),
        encoding="utf-8",
    )
    (plugin / "settings.json").write_text(
        json.dumps(
            {
                "subagentStatusLine": {
                    "type": "command",
                    "command": "python3 \"${CLAUDE_PLUGIN_ROOT}/status.py\"",
                }
            }
        ),
        encoding="utf-8",
    )
    (plugin / "status.py").write_text(
        "import json, os, pathlib, sys\n"
        "payload = json.load(sys.stdin)\n"
        "pathlib.Path(os.environ['CLAUDE_PROJECT_DIR'], 'status-input.json').write_text(json.dumps(payload))\n"
        "print(json.dumps({'id': payload['tasks'][0]['id'], 'content': 'custom row'}))\n",
        encoding="utf-8",
    )
    install_local_plugin(root, "extensions/status-tools")


class SubagentStatusLineTests(unittest.TestCase):
    def test_plugin_command_receives_payload_and_returns_jsonl_rows(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-status-line-") as base:
            root = Path(base)
            write_status_plugin(root)
            workspace = create_run_workspace(root, run_id="status-run")
            config = resolve_subagent_status_line(root)

            self.assertIsNotNone(config)
            rows = run_subagent_status_line(
                workspace,
                config,
                {"columns": 80, "tasks": [{"id": "task-1"}]},
            )
            payload = json.loads((root / "status-input.json").read_text(encoding="utf-8"))

        self.assertEqual(rows, {"task-1": "custom row"})
        self.assertEqual(payload["columns"], 80)

    def test_plugin_command_timeout_and_errors_are_bounded_and_redacted(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-status-line-") as base:
            workspace = create_run_workspace(Path(base), run_id="status-run")
            secret = "status-secret-value"
            failing = ResolvedSubagentStatusLine(
                "status-tools",
                f"printf '{secret}' >&2; exit 1",
                {},
                (secret,),
            )
            with self.assertRaisesRegex(ValueError, r"\[REDACTED\]") as error:
                run_subagent_status_line(workspace, failing, {"tasks": []})
            self.assertNotIn(secret, str(error.exception))

            timeout = ResolvedSubagentStatusLine("status-tools", "sleep 5", {})
            with self.assertRaisesRegex(ValueError, "timed out"):
                run_subagent_status_line(workspace, timeout, {"tasks": []})

    def test_panel_renders_default_and_custom_rows_on_tty(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-status-panel-") as base:
            root = Path(base)
            workspace = create_run_workspace(root, run_id="panel-run")
            stream = TtyBuffer()
            panel = SubagentPanel(root, stream=stream)
            panel.workspace = workspace
            snapshot = BackgroundDelegateSnapshot(
                task_id="task-1",
                action=DelegateTaskAction(type="delegate_task", task="Inspect auth", teammate_name="reviewer"),
                status="running",
                started_at=1.0,
            )
            with patch(
                "vibeagent.cli_subagent_panel.list_background_delegate_snapshots",
                return_value=[snapshot],
            ):
                panel.refresh()
                self.assertIn("reviewer running Inspect auth 0 tok", stream.value)

                panel._observe_event(
                    workspace.session_dir,
                    {
                        "type": "subagent_model",
                        "subagent_id": "task-1",
                        "usage": {"input_tokens": 4, "output_tokens": 3},
                    },
                )

                panel.config = ResolvedSubagentStatusLine("status-tools", "printf row", {})
                panel.custom_authorized = True
                with patch(
                    "vibeagent.cli_subagent_panel.run_subagent_status_line",
                    return_value={"task-1": "custom reviewer row"},
                ) as command:
                    panel.refresh(force=True)

            panel.close()

        self.assertIn("Agents (1)", stream.value)
        self.assertIn("custom reviewer row", stream.value)
        command.assert_called_once()
        command_payload = command.call_args.args[2]
        self.assertEqual(command_payload["tasks"][0]["tokenCount"], 7)
        self.assertEqual(command_payload["tasks"][0]["tokenSamples"][0]["tokens"], 7)

    def test_non_tty_panel_does_not_resolve_or_render_plugins(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-status-panel-") as base:
            stream = TtyBuffer()
            stream.isatty = lambda: False
            with patch("vibeagent.cli_subagent_panel.resolve_subagent_status_line") as resolve:
                panel = SubagentPanel(Path(base), stream=stream)
                panel.refresh()

        self.assertEqual(stream.value, "")
        resolve.assert_not_called()

    def test_brief_panel_displays_sanitized_agent_message_without_tty(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-brief-panel-") as base:
            root = Path(base)
            workspace = create_run_workspace(root, run_id="brief-run")
            stream = TtyBuffer()
            stream.isatty = lambda: False
            panel = SubagentPanel(root, stream=stream, brief=True)
            panel.bind(workspace)
            panel._observe_event(
                workspace.session_dir,
                {"type": "agent_user_message", "message": "Testing\x1b[2J now"},
            )
            panel.close()

        self.assertIn("Agent update: Testing now", stream.value)
        self.assertNotIn("\x1b", stream.value)

    def test_panel_pause_blocks_refresh_until_resume(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-status-panel-") as base:
            root = Path(base)
            workspace = create_run_workspace(root, run_id="panel-run")
            stream = TtyBuffer()
            panel = SubagentPanel(root, stream=stream)
            panel.workspace = workspace
            snapshot = BackgroundDelegateSnapshot(
                task_id="task-1",
                action=DelegateTaskAction(type="delegate_task", task="Inspect auth"),
                status="running",
                started_at=1.0,
            )
            with patch(
                "vibeagent.cli_subagent_panel.list_background_delegate_snapshots",
                return_value=[snapshot],
            ):
                panel.refresh()
                panel.pause()
                paused_output = stream.value
                panel.refresh(force=True)
                self.assertEqual(stream.value, paused_output)
                panel.resume()

            panel.close()

        self.assertGreater(len(stream.value), len(paused_output))

    def test_screen_reader_panel_appends_changed_status_without_ansi_redraw(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-status-panel-") as base:
            root = Path(base)
            workspace = create_run_workspace(root, run_id="panel-run")
            stream = TtyBuffer()
            panel = SubagentPanel(root, stream=stream, screen_reader=True)
            panel.workspace = workspace
            snapshot = BackgroundDelegateSnapshot(
                task_id="task-1",
                action=DelegateTaskAction(type="delegate_task", task="Inspect auth"),
                status="running",
                started_at=1.0,
            )
            with patch(
                "vibeagent.cli_subagent_panel.list_background_delegate_snapshots",
                return_value=[snapshot],
            ):
                panel.refresh()
                first = stream.value
                panel.refresh(force=True)
                self.assertEqual(stream.value, first)

                with patch(
                    "vibeagent.cli_subagent_panel.list_background_delegate_snapshots",
                    return_value=[replace(snapshot, status="completed")],
                ):
                    panel.refresh()

            panel.close()

        self.assertEqual(stream.value.count("Agent status update"), 2)
        self.assertIn("running", stream.value)
        self.assertIn("completed", stream.value)
        self.assertNotIn("\x1b", stream.value)


if __name__ == "__main__":
    unittest.main()
