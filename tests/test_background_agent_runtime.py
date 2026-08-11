from __future__ import annotations

import io
import json
import os
from pathlib import Path
import stat
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from unittest.mock import Mock, patch

from vibeagent import background_agent_runtime as runtime
from vibeagent import background_agent_process as process_runtime
from vibeagent import background_agent_store as store
from vibeagent.background_agent_worker import run_worker
from vibeagent.background_agent_inbox import pending_background_agent_message_count


class BackgroundAgentRuntimeTests(unittest.TestCase):
    def test_detached_worker_survives_launcher_and_records_cli_failure(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-background-agent-") as base:
            root = Path(base).resolve()
            with patch.dict(
                os.environ,
                {
                    "MINIMAX_API_KEY": "",
                    "MINIMAX_API": "",
                    "minimax_api": "",
                },
            ):
                view = runtime.launch_background_agent(
                    root,
                    root,
                    ["--background", "--provider", "minimax", "inspect"],
                    task_summary="inspect",
                    session_name=None,
                )
                self._wait_for_exit(root, view)
                first_failed, first_stdout, _ = runtime.read_background_agent_logs(
                    root,
                    view.record.id,
                )
                respawned, disposition = runtime.send_background_agent_message(
                    root,
                    view.record.id,
                    "continue after the provider configuration is repaired",
                )
                assert respawned is not None
                self._wait_for_exit(root, respawned)

            failed, stdout, stderr = runtime.read_background_agent_logs(root, view.record.id)
            pending_messages = pending_background_agent_message_count(root, view.record.id)
            removed, _ = runtime.remove_background_agent(root, view.record.id)

        assert first_failed is not None
        assert failed is not None
        self.assertEqual(first_failed.status, "failed")
        self.assertIn("Missing MiniMax API key", first_stdout)
        self.assertEqual(disposition, "respawned")
        self.assertEqual(respawned.record.id, view.record.id)
        self.assertEqual(failed.status, "failed")
        self.assertEqual(failed.exit_code, 1)
        self.assertIn("Missing MiniMax API key", stdout)
        self.assertEqual(stderr, "")
        self.assertEqual(pending_messages, 0)
        self.assertTrue(removed)

    def _wait_for_exit(self, root: Path, view) -> None:
        deadline = time.monotonic() + 5.0
        while (
            store.read_background_agent_exit_code(view.record.exit_code_path) is None
            and time.monotonic() < deadline
        ):
            time.sleep(0.02)
        if store.read_background_agent_exit_code(view.record.exit_code_path) is None:
            runtime.stop_background_agent(root, view.record.id)
            self.fail("Detached worker did not record an exit status")

    def test_launch_persists_private_record_and_consumable_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-background-agent-") as base:
            root = Path(base).resolve()
            process = Mock(pid=os.getpid())
            with (
                patch.object(process_runtime.subprocess, "Popen", return_value=process) as popen,
                patch.object(runtime, "read_process_start_ticks", return_value=77),
                patch.object(store, "persistent_process_running", return_value=True),
            ):
                view = runtime.launch_background_agent(
                    root,
                    root,
                    ["--bg", "--cwd", str(root), "fix", "tests"],
                    task_summary="fix tests",
                    session_name=None,
                )

                records = runtime.list_background_agents(root)

            self.assertEqual(view.status, "running")
            self.assertEqual(records, (view,))
            self.assertEqual(view.record.start_ticks, 77)
            self.assertEqual(view.record.session_name, f"background-{view.record.id}")
            command = popen.call_args.args[0]
            self.assertEqual(
                command[0:3],
                [process_runtime.sys.executable, "-m", "vibeagent.background_agent_worker"],
            )
            payload_path = Path(command[3])
            payload = json.loads(payload_path.read_text(encoding="utf-8"))
            self.assertNotIn("--bg", payload["initialArgv"])
            self.assertIn("--print", payload["initialArgv"])
            self.assertIn("--name", payload["initialArgv"])
            for path in (
                payload_path,
                view.record.stdout_path,
                view.record.stderr_path,
                view.record.exit_code_path,
                runtime.background_agent_record_path(root, view.record.id),
            ):
                assert path is not None
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_completed_logs_and_removal_preserve_session_contract(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-background-agent-") as base:
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
                    session_name="inspection",
                )
                view.record.stdout_path.write_text("done\n", encoding="utf-8")
                view.record.stderr_path.write_text("warning\n", encoding="utf-8")
                view.record.exit_code_path.write_text("0\n", encoding="utf-8")

                completed, stdout, stderr = runtime.read_background_agent_logs(
                    root,
                    view.record.id,
                )
                removed, message = runtime.remove_background_agent(root, view.record.id)

            assert completed is not None
            self.assertEqual(completed.status, "completed")
            self.assertEqual(completed.exit_code, 0)
            self.assertEqual(stdout, "done\n")
            self.assertEqual(stderr, "warning\n")
            self.assertTrue(removed)
            self.assertIn("Session transcript was preserved", message)
            self.assertIsNone(runtime.get_background_agent(root, view.record.id))

    def test_stop_terminates_running_process_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-background-agent-") as base:
            root = Path(base).resolve()
            process = Mock(pid=12345)
            running = [True, True, False]
            with (
                patch.object(process_runtime.subprocess, "Popen", return_value=process),
                patch.object(runtime, "read_process_start_ticks", return_value=77),
                patch.object(store, "persistent_process_running", side_effect=lambda _record: running.pop(0)),
                patch.object(runtime, "terminate_persistent_process") as terminate,
            ):
                view = runtime.launch_background_agent(
                    root,
                    root,
                    ["--background", "inspect"],
                    task_summary="inspect",
                    session_name=None,
                )
                stopped = runtime.stop_background_agent(root, view.record.id)

            assert stopped is not None
            terminate.assert_called_once()
            self.assertEqual(stopped.status, "stopped")
            self.assertTrue(stopped.record.stopped_path.is_file())

    def test_rejects_unsafe_ids_and_runtime_symlink(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-background-agent-") as base:
            root = Path(base).resolve()
            self.assertIsNone(runtime.background_agent_record_path(root, "../agent"))
            outside = root / "outside"
            outside.mkdir()
            runtime_path = root / ".vibeagent"
            runtime_path.symlink_to(outside, target_is_directory=True)

            with self.assertRaisesRegex(ValueError, "Runtime path"):
                runtime.launch_background_agent(
                    root,
                    root,
                    ["--background", "inspect"],
                    task_summary="inspect",
                    session_name=None,
                )

    def test_worker_consumes_payload_and_records_exit_code(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-background-worker-") as base:
            root = Path(base)
            payload_path = root / "payload.json"
            exit_path = root / "exitcode"
            payload_path.write_text(
                json.dumps(
                    {
                        "schemaVersion": 1,
                        "argv": ["--version"],
                        "exitCodePath": str(exit_path),
                    }
                ),
                encoding="utf-8",
            )
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = run_worker(payload_path)

            payload_exists = payload_path.exists()
            recorded_exit = exit_path.read_text(encoding="utf-8")

        self.assertEqual(exit_code, 0)
        self.assertFalse(payload_exists)
        self.assertEqual(recorded_exit, "0\n")
        self.assertIn("vibeagent", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
