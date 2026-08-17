from __future__ import annotations

import argparse
import io
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from vibeagent.background_agent_runtime import BackgroundAgentRecord, BackgroundAgentView
from vibeagent.cli import main
from vibeagent.cli_args import parse_args
from vibeagent.cli_exit_codes import local_result_exit_code
from vibeagent.cli_background_agent_launch import launch_background_agent_from_cli
from vibeagent.cli_background_agent_local_flags import (
    run_background_agent_local_flag,
    run_interactive_background_agent_command,
)
from vibeagent.command_types import LocalCommand


def _view(root: Path, *, status: str = "running") -> BackgroundAgentView:
    logs = root / ".vibeagent" / "background-agents" / "logs"
    return BackgroundAgentView(
        record=BackgroundAgentRecord(
            id="0123456789ab",
            project_root=root,
            invocation_root=root,
            pid=1234,
            start_ticks=77,
            started_at="2026-08-11T00:00:00+00:00",
            task_summary="fix tests",
            session_name="background-0123456789ab",
            stdout_path=logs / "0123456789ab.stdout.log",
            stderr_path=logs / "0123456789ab.stderr.log",
            exit_code_path=logs / "0123456789ab.exitcode",
            stopped_path=logs / "0123456789ab.stopped",
        ),
        status=status,
        exit_code=None if status == "running" else 0,
    )


class CliBackgroundAgentTests(unittest.TestCase):
    def test_main_routes_background_task_before_one_shot_execution(self) -> None:
        with patch("vibeagent.cli.launch_background_agent_from_cli", return_value=0) as launch:
            argv = ["--bg", "fix", "tests", "--file", "file_alpha:fixtures/input.bin"]
            exit_code = main(argv)

        self.assertEqual(exit_code, 0)
        launch.assert_called_once()
        self.assertEqual(launch.call_args.args[0], argv)

    def test_internal_followup_arguments_fail_outside_registered_worker(self) -> None:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            followup_exit = main(
                [
                    "--_background-agent-followup",
                    "/tmp/not-a-worker-message.json",
                    "task",
                ]
            )
            token_exit = main(
                [
                    "--_background-agent-worker-token",
                    "0" * 32,
                    "task",
                ]
            )

        self.assertEqual(followup_exit, 2)
        self.assertEqual(token_exit, 2)
        self.assertIn("outside its worker", stdout.getvalue())

    def test_launch_formats_management_commands_and_json_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-background-") as base:
            root = Path(base).resolve()
            view = _view(root)
            args = argparse.Namespace(cwd=str(root), task=["fix", "tests"], name=None, json=False)
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli_background_agent_launch.launch_background_agent", return_value=view) as launch,
                redirect_stdout(stdout),
            ):
                exit_code = launch_background_agent_from_cli(["--bg", "fix", "tests"], args)

        self.assertEqual(exit_code, 0)
        launch.assert_called_once()
        self.assertIn("Background agent started: 0123456789ab", stdout.getvalue())
        self.assertIn("--background-agent-log 0123456789ab", stdout.getvalue())
        self.assertIn("approvals", stdout.getvalue())

    def test_background_launch_preserves_brief_mode_for_worker_and_followups(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-background-") as base:
            root = Path(base).resolve()
            view = _view(root)
            argv = ["--bg", "--brief", "--cwd", root.as_posix(), "fix", "tests"]
            args = parse_args(argv)
            with (
                patch(
                    "vibeagent.cli_background_agent_launch.launch_background_agent",
                    return_value=view,
                ) as launch,
                redirect_stdout(io.StringIO()),
            ):
                exit_code = launch_background_agent_from_cli(argv, args)

        self.assertEqual(exit_code, 0)
        self.assertIn("--brief", launch.call_args.args[2])

    def test_background_resume_pins_followups_to_resolved_run_id(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-background-") as base:
            root = Path(base).resolve()
            view = _view(root)
            argv = ["--bg", "--cwd", root.as_posix(), "--resume", "latest", "continue"]
            args = parse_args(argv)
            with (
                patch(
                    "vibeagent.cli_background_agent_launch.get_resume_context",
                    return_value=("resolved-run-id", "context", "resumed"),
                ),
                patch(
                    "vibeagent.cli_background_agent_launch.launch_background_agent",
                    return_value=view,
                ) as launch,
                redirect_stdout(io.StringIO()),
            ):
                exit_code = launch_background_agent_from_cli(argv, args)

        self.assertEqual(exit_code, 0)
        self.assertEqual(launch.call_args.kwargs["resume_reference"], "resolved-run-id")

    def test_background_session_id_is_forwarded_as_a_new_worker_session(self) -> None:
        session_id = "123e4567-e89b-12d3-a456-426614174000"
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-background-") as base:
            root = Path(base).resolve()
            view = _view(root)
            argv = ["--bg", "--cwd", root.as_posix(), "--session-id", session_id, "inspect"]
            args = parse_args(argv)
            with (
                patch("vibeagent.cli_background_agent_launch.get_resume_context") as get_resume,
                patch(
                    "vibeagent.cli_background_agent_launch.launch_background_agent",
                    return_value=view,
                ) as launch,
                redirect_stdout(io.StringIO()),
            ):
                exit_code = launch_background_agent_from_cli(argv, args)

        self.assertEqual(exit_code, 0)
        self.assertIn(session_id, launch.call_args.args[2])
        self.assertIsNone(launch.call_args.kwargs["resume_reference"])
        get_resume.assert_not_called()

    def test_background_materializes_plugin_urls_before_persisting_launch_argv(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-background-") as base:
            root = Path(base).resolve()
            cached = root / "cached-plugin"
            cached.mkdir()
            view = _view(root)
            argv = [
                "--bg",
                "--cwd",
                root.as_posix(),
                "--plugin-url",
                "https://plugins.example.com/demo.zip?token=secret",
                "--",
                "fix",
            ]
            args = parse_args(argv)
            with (
                patch(
                    "vibeagent.cli_background_agent_launch.resolve_invocation_plugin_dirs",
                    return_value=(cached,),
                ) as resolve,
                patch(
                    "vibeagent.cli_background_agent_launch.launch_background_agent",
                    return_value=view,
                ) as launch,
                redirect_stdout(io.StringIO()),
            ):
                exit_code = launch_background_agent_from_cli(argv, args)

        persisted = launch.call_args.args[2]
        self.assertEqual(exit_code, 0)
        resolve.assert_called_once_with(
            [],
            invocation_root=Path.cwd(),
            plugin_urls=["https://plugins.example.com/demo.zip?token=secret"],
        )
        self.assertNotIn("--plugin-url", persisted)
        self.assertNotIn("https://plugins.example.com/demo.zip?token=secret", persisted)
        separator = persisted.index("--")
        self.assertEqual(persisted[separator - 2 : separator], ["--plugin-dir", cached.as_posix()])

    def test_background_persists_debug_options_for_worker(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-background-") as base:
            root = Path(base).resolve()
            view = _view(root)
            debug_path = root / "debug.jsonl"
            argv = [
                "--bg",
                "--cwd",
                root.as_posix(),
                "--debug=api,!mcp",
                "--debug-file",
                debug_path.as_posix(),
                "--",
                "inspect",
            ]
            args = parse_args(argv)
            with (
                patch(
                    "vibeagent.cli_background_agent_launch.launch_background_agent",
                    return_value=view,
                ) as launch,
                redirect_stdout(io.StringIO()),
            ):
                exit_code = launch_background_agent_from_cli(argv, args)

        self.assertEqual(exit_code, 0)
        self.assertEqual(launch.call_args.args[2], argv)

    def test_local_list_log_stop_and_remove_reports(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-background-") as base:
            root = Path(base).resolve()
            view = _view(root)
            base_args = {
                "background_agents": False,
                "background_agent_log": None,
                "background_agent_log_max_chars": 20_000,
                "stop_background_agent": None,
                "remove_background_agent": None,
                "send_background_agent": None,
                "respawn_background_agent": None,
            }
            with patch(
                "vibeagent.cli_background_agent_local_flags.list_background_agents",
                return_value=(view,),
            ):
                text, payload = run_background_agent_local_flag(
                    argparse.Namespace(**{**base_args, "background_agents": True}),
                    root,
                    {},
                )
            self.assertIn("count: 1", text)
            self.assertEqual(payload["backgroundAgents"][0]["status"], "running")

            with patch(
                "vibeagent.cli_background_agent_local_flags.read_background_agent_logs",
                return_value=(view, "out\n", "err\n"),
            ):
                text, _ = run_background_agent_local_flag(
                    argparse.Namespace(**{**base_args, "background_agent_log": view.record.id}),
                    root,
                    {},
                )
            self.assertIn("out", text)
            self.assertIn("err", text)

            with patch(
                "vibeagent.cli_background_agent_local_flags.stop_background_agent",
                return_value=view,
            ):
                text, _ = run_background_agent_local_flag(
                    argparse.Namespace(**{**base_args, "stop_background_agent": view.record.id}),
                    root,
                    {},
                )
            self.assertIn("status: running", text)

            with patch(
                "vibeagent.cli_background_agent_local_flags.remove_background_agent",
                return_value=(True, "removed"),
            ):
                text, payload = run_background_agent_local_flag(
                    argparse.Namespace(**{**base_args, "remove_background_agent": view.record.id}),
                    root,
                    {},
                )
            self.assertIn("ok: yes", text)
            self.assertTrue(payload["backgroundAgentRemoval"]["ok"])

    def test_local_and_interactive_followup_commands_report_delivery(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-background-") as base:
            root = Path(base).resolve()
            view = _view(root)
            base_args = {
                "background_agents": False,
                "background_agent_log": None,
                "background_agent_log_max_chars": 20_000,
                "stop_background_agent": None,
                "remove_background_agent": None,
                "send_background_agent": [view.record.id, "continue"],
                "respawn_background_agent": None,
            }
            with (
                patch(
                    "vibeagent.cli_background_agent_local_flags.send_background_agent_message",
                    return_value=(view, "queued"),
                ),
                patch(
                    "vibeagent.cli_background_agent_local_flags.pending_background_agent_message_count",
                    return_value=1,
                ),
            ):
                text, payload = run_background_agent_local_flag(
                    argparse.Namespace(**base_args),
                    root,
                    {},
                )
            self.assertIn("delivery: queued", text)
            self.assertEqual(payload["backgroundAgentDelivery"]["status"], "queued")

            with (
                patch(
                    "vibeagent.cli_background_agent_local_flags.respawn_background_agent",
                    return_value=(view, "respawned"),
                ),
                patch(
                    "vibeagent.cli_background_agent_local_flags.pending_background_agent_message_count",
                    return_value=0,
                ),
            ):
                text = run_interactive_background_agent_command(
                    LocalCommand(
                        type="respawn_background_agent",
                        argument=view.record.id,
                    )
                )
            self.assertIn("delivery: respawned", text or "")

    def test_interactive_commands_validate_arguments_and_delegate(self) -> None:
        self.assertEqual(
            run_interactive_background_agent_command(
                LocalCommand(type="background_agent_log")
            ),
            "Usage: /background-agent-log <id> [max-chars]",
        )
        self.assertEqual(
            run_interactive_background_agent_command(
                LocalCommand(type="background_agent_log", argument="abc 999")
            ),
            "Background agent log max-chars must be between 1000 and 100000.",
        )
        with patch(
            "vibeagent.cli_background_agent_local_flags.list_background_agents",
            return_value=(),
        ):
            self.assertIn(
                "count: 0",
                run_interactive_background_agent_command(
                    LocalCommand(type="background_agents")
                ) or "",
            )

    def test_failed_agent_log_has_failed_local_exit_code(self) -> None:
        args = parse_args(["--background-agent-log", "0123456789ab"])

        exit_code = local_result_exit_code(
            args,
            "Background agent 0123456789ab:\n  status: failed\n  exitCode: 1",
        )

        self.assertEqual(exit_code, 1)


if __name__ == "__main__":
    unittest.main()
