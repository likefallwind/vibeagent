from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import Mock, patch

from vibeagent import background_agent_process as process_runtime
from vibeagent import background_agent_runtime as runtime
from vibeagent import background_agent_store as store
from vibeagent.background_agent_config import (
    background_agent_config_path,
    create_background_agent_config,
    read_background_agent_config,
)
from vibeagent.background_agent_inbox import (
    enqueue_background_agent_message,
    pending_background_agent_message_count,
    read_background_agent_message,
)
from vibeagent.background_agent_worker import run_worker
from vibeagent.cli_args import parse_args
from vibeagent.cli_background_agent_followup import (
    BACKGROUND_AGENT_CONFIG_ENV,
    BACKGROUND_AGENT_ID_ENV,
    prepare_background_agent_followup,
    record_background_agent_session_root,
)


class BackgroundAgentFollowupTests(unittest.TestCase):
    def test_worker_drains_followup_in_same_process_before_recording_exit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-background-followup-") as base:
            root = Path(base).resolve()
            agent_id = "0123456789ab"
            config = create_background_agent_config(
                root,
                agent_id,
                session_root=root,
                resume_reference="background-0123456789ab",
                base_argv=["--print", "--name", "background-0123456789ab", "--", "initial"],
            )
            exit_path = root / ".vibeagent" / "background-agents" / "logs" / f"{agent_id}.exitcode"
            exit_path.parent.mkdir(parents=True)
            exit_path.write_text("", encoding="utf-8")
            payload_path = root / "payload.json"
            payload_path.write_text(
                json.dumps(
                    {
                        "schemaVersion": 2,
                        "agentId": agent_id,
                        "projectRoot": root.as_posix(),
                        "configPath": background_agent_config_path(root, agent_id).as_posix(),
                        "exitCodePath": exit_path.as_posix(),
                        "initialArgv": ["--print", "--", "initial"],
                    }
                ),
                encoding="utf-8",
            )
            calls: list[list[str]] = []
            followups: list[str] = []

            def fake_main(argv: list[str]) -> int:
                calls.append(argv)
                if len(calls) == 1:
                    enqueue_background_agent_message(config, "continue with focused tests")
                    enqueue_background_agent_message(config, "then review the diff")
                else:
                    marker = argv.index("--_background-agent-followup")
                    followups.append(
                        read_background_agent_message(config, Path(argv[marker + 1]))
                    )
                return 0

            exit_code = run_worker(payload_path, cli_main_func=fake_main)

            self.assertEqual(exit_code, 0)
            self.assertEqual(len(calls), 3)
            self.assertEqual(calls[0][0], "--print")
            self.assertIn("--_background-agent-worker-token", calls[0])
            self.assertLess(
                calls[0].index("--_background-agent-worker-token"),
                calls[0].index("--"),
            )
            self.assertIn("--_background-agent-followup", calls[1])
            self.assertLess(
                calls[1].index("--_background-agent-followup"),
                calls[1].index("--"),
            )
            self.assertEqual(
                followups,
                ["continue with focused tests", "then review the diff"],
            )
            self.assertEqual(pending_background_agent_message_count(root, agent_id), 0)
            self.assertEqual(exit_path.read_text(encoding="utf-8"), "0\n")

    def test_followup_overrides_old_task_resume_and_worktree(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-background-followup-") as base:
            root = Path(base).resolve()
            worktree = root / "worktree"
            worktree.mkdir()
            agent_id = "0123456789ab"
            config = create_background_agent_config(
                root,
                agent_id,
                session_root=root,
                resume_reference="run-123",
                base_argv=["--print", "--worktree", "feature", "old task"],
            )
            message_path = enqueue_background_agent_message(config, "new follow-up")
            args = parse_args(
                [
                    "--print",
                    "--worktree",
                    "feature",
                    "--_background-agent-followup",
                    message_path.as_posix(),
                    "--_background-agent-worker-token",
                    config.worker_token,
                    "--",
                    "old task",
                ]
            )
            environment = {
                BACKGROUND_AGENT_ID_ENV: agent_id,
                BACKGROUND_AGENT_CONFIG_ENV: background_agent_config_path(root, agent_id).as_posix(),
            }
            with patch.dict(os.environ, environment, clear=False):
                record_background_agent_session_root(args, worktree)
                prepare_background_agent_followup(args)

            self.assertEqual(args.task, ["new follow-up"])
            self.assertEqual(args.resume, "run-123")
            self.assertTrue(args.resume_from_background_followup)
            self.assertEqual(args.cwd, worktree.as_posix())
            self.assertIsNone(args.worktree)
            self.assertIsNone(args.name)
            self.assertFalse(args.fork_session)
            self.assertEqual(read_background_agent_config(root, agent_id).session_root, worktree)

            args._background_agent_worker_token = "0" * 32
            with (
                patch.dict(os.environ, environment, clear=False),
                self.assertRaisesRegex(ValueError, "worker token"),
            ):
                prepare_background_agent_followup(args)

    def test_private_config_and_message_files_reject_oversized_message(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-background-followup-") as base:
            root = Path(base).resolve()
            agent_id = "0123456789ab"
            config = create_background_agent_config(
                root,
                agent_id,
                session_root=root,
                resume_reference="run-123",
                base_argv=["--print", "initial"],
            )
            message_path = enqueue_background_agent_message(config, "continue")

            self.assertEqual(stat.S_IMODE(background_agent_config_path(root, agent_id).stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(message_path.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(message_path.parent.stat().st_mode), 0o700)
            with self.assertRaisesRegex(ValueError, "must not exceed"):
                enqueue_background_agent_message(config, "x" * 4_001)

    def test_send_queues_running_agent_and_respawns_completed_agent(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-background-followup-") as base:
            root = Path(base).resolve()
            first = Mock(pid=12345)
            second = Mock(pid=23456)
            with (
                patch.object(process_runtime.subprocess, "Popen", side_effect=[first, second]) as popen,
                patch.object(runtime, "read_process_start_ticks", side_effect=[77, 88]),
                patch.object(store, "persistent_process_running", return_value=True),
            ):
                view = runtime.launch_background_agent(
                    root,
                    root,
                    ["--background", "inspect"],
                    task_summary="inspect",
                    session_name=None,
                )
                queued, queued_status = runtime.send_background_agent_message(
                    root,
                    view.record.id,
                    "check the focused tests",
                )
                self.assertEqual(queued_status, "queued")
                self.assertEqual(popen.call_count, 1)
                self.assertEqual(
                    pending_background_agent_message_count(root, view.record.id),
                    1,
                )

                view.record.exit_code_path.write_text("0\n", encoding="utf-8")
                respawned, respawn_status = runtime.send_background_agent_message(
                    root,
                    view.record.id,
                    "review the result",
                )

            assert queued is not None
            assert respawned is not None
            self.assertEqual(respawn_status, "respawned")
            self.assertEqual(respawned.record.id, view.record.id)
            self.assertEqual(respawned.record.pid, 23456)
            self.assertEqual(popen.call_count, 2)
            self.assertEqual(
                pending_background_agent_message_count(root, view.record.id),
                2,
            )

    def test_respawn_failure_preserves_completed_status_and_queued_message(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-background-followup-") as base:
            root = Path(base).resolve()
            process = Mock(pid=12345)
            with (
                patch.object(process_runtime.subprocess, "Popen", return_value=process),
                patch.object(runtime, "read_process_start_ticks", return_value=77),
                patch.object(store, "persistent_process_running", return_value=True),
            ):
                view = runtime.launch_background_agent(
                    root,
                    root,
                    ["--background", "inspect"],
                    task_summary="inspect",
                    session_name=None,
                )
            view.record.exit_code_path.write_text("0\n", encoding="utf-8")

            with (
                patch.object(process_runtime.subprocess, "Popen", side_effect=OSError("spawn failed")),
                self.assertRaisesRegex(OSError, "spawn failed"),
            ):
                runtime.send_background_agent_message(
                    root,
                    view.record.id,
                    "continue",
                )

            preserved = runtime.get_background_agent(root, view.record.id)
            assert preserved is not None
            self.assertEqual(preserved.status, "completed")
            self.assertEqual(preserved.exit_code, 0)
            self.assertEqual(
                pending_background_agent_message_count(root, view.record.id),
                1,
            )

    def test_respawn_restarts_running_agent_before_continuation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-background-followup-") as base:
            root = Path(base).resolve()
            first = Mock(pid=12345)
            second = Mock(pid=23456)
            with (
                patch.object(process_runtime.subprocess, "Popen", side_effect=[first, second]),
                patch.object(runtime, "read_process_start_ticks", side_effect=[77, 88]),
                patch.object(store, "persistent_process_running", return_value=True),
                patch.object(runtime, "terminate_persistent_process") as terminate,
            ):
                view = runtime.launch_background_agent(
                    root,
                    root,
                    ["--background", "inspect"],
                    task_summary="inspect",
                    session_name=None,
                )
                restarted, disposition = runtime.respawn_background_agent(
                    root,
                    view.record.id,
                )

            assert restarted is not None
            terminate.assert_called_once()
            self.assertEqual(disposition, "respawned")
            self.assertEqual(restarted.record.id, view.record.id)
            self.assertEqual(restarted.record.pid, 23456)
            self.assertEqual(
                pending_background_agent_message_count(root, view.record.id),
                1,
            )


if __name__ == "__main__":
    unittest.main()
