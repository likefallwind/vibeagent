from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import shlex
import tempfile
import unittest
from unittest.mock import patch

from vibeagent.cli import main
from vibeagent.cli_args import parse_args
from vibeagent.process_registry import read_persistent_process_record, terminate_persistent_process
from vibeagent.process_runtime import BACKGROUND_PROCESSES
from vibeagent.types import StartCommandObservation


class CliBackgroundExecTests(unittest.TestCase):
    def test_parser_accepts_background_exec_without_a_task(self) -> None:
        args = parse_args(["--bg", "--exec", "pytest -x"])

        self.assertTrue(args.background)
        self.assertEqual(args.exec_command, "pytest -x")
        self.assertEqual(args.task, [])

    def test_exec_requires_background_and_rejects_a_prompt(self) -> None:
        stderr = io.StringIO()
        with redirect_stdout(stderr):
            missing_background = main(["--exec", "pytest -x"])
        self.assertEqual(missing_background, 2)
        self.assertIn("--exec requires --background", stderr.getvalue())

        stderr = io.StringIO()
        with redirect_stdout(stderr):
            prompt = main(["--bg", "--exec", "pytest -x", "fix", "tests"])
        self.assertEqual(prompt, 2)
        self.assertIn("cannot be combined with a coding task", stderr.getvalue())

    def test_exec_rejects_ignored_model_session_and_local_options(self) -> None:
        cases = (
            (["--bg", "--exec", "pytest -x", "--model", "opus"], "model-effort"),
            (["--bg", "--exec", "pytest -x", "--continue"], "session"),
            (["--bg", "--exec", "pytest -x", "--processes"], "local inspection"),
        )
        for argv, message in cases:
            with self.subTest(argv=argv):
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    exit_code = main(argv)
                self.assertEqual(exit_code, 2)
                self.assertIn(message, stdout.getvalue())

    def test_exec_launches_managed_process_without_a_model_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-bg-exec-") as base:
            root = Path(base).resolve()
            observation = StartCommandObservation(
                kind="start_command",
                process_id="abc123def456",
                pid=4321,
                command="pytest -x",
                cwd=".",
                ok=True,
                message="Started process abc123def456.",
                stdout_path=(root / ".vibeagent/sessions/cli-background-exec/processes/abc.stdout.log").as_posix(),
                stderr_path=(root / ".vibeagent/sessions/cli-background-exec/processes/abc.stderr.log").as_posix(),
                sandboxed=True,
            )
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch(
                    "vibeagent.cli_background_exec.start_background_command",
                    return_value=observation,
                ) as start,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--bg", "--exec", "pytest -x", "--cwd", base, "--json"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["backgroundJob"]["processId"], "abc123def456")
        self.assertEqual(payload["backgroundJob"]["command"], "pytest -x")
        self.assertTrue(payload["backgroundJob"]["sandboxed"])
        self.assertTrue(payload["backgroundJob"]["ptyBacked"])
        start.assert_called_once()
        self.assertEqual(start.call_args.args[0].root, root)
        self.assertEqual(start.call_args.args[1], "pytest -x")
        self.assertTrue(start.call_args.kwargs["pty_backed"])
        create_chat_client.assert_not_called()

    @unittest.skipUnless(os.name == "posix", "PTY-backed jobs require POSIX")
    def test_exec_accepts_stdin_from_a_later_cli_runtime(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-bg-exec-") as base:
            code = (
                "import sys; "
                "print(f'tty={sys.stdin.isatty()}', flush=True); "
                "print('got=' + input(), flush=True)"
            )
            command = f"python3 -c {shlex.quote(code)}"
            launch_stdout = io.StringIO()
            background = None
            record = None
            process_id = None
            try:
                with redirect_stdout(launch_stdout):
                    launch_exit = main(["--bg", "--exec", command, "--cwd", base, "--json"])
                launch_payload = json.loads(launch_stdout.getvalue())
                process_id = launch_payload["backgroundJob"]["processId"]
                background = BACKGROUND_PROCESSES.pop(process_id)
                background.stdout_handle.close()
                background.stderr_handle.close()

                write_stdout = io.StringIO()
                with redirect_stdout(write_stdout):
                    write_exit = main(
                        [
                            "--cwd",
                            base,
                            "--write-process",
                            process_id,
                            "--write-stdin",
                            "hello\\n",
                            "--json",
                        ]
                    )
                background.process.wait(timeout=5)

                wait_stdout = io.StringIO()
                with redirect_stdout(wait_stdout):
                    wait_exit = main(
                        [
                            "--cwd",
                            base,
                            "--wait-process",
                            process_id,
                            "--wait-timeout-ms",
                            "5000",
                            "--json",
                        ]
                    )
                wait_payload = json.loads(wait_stdout.getvalue())

                self.assertEqual(launch_exit, 0)
                self.assertTrue(launch_payload["backgroundJob"]["ptyBacked"])
                self.assertEqual(write_exit, 0)
                self.assertTrue(json.loads(write_stdout.getvalue())["success"])
                self.assertEqual(wait_exit, 0, wait_payload)
                self.assertEqual(wait_payload["waitProcess"]["exitCode"], 0)
                self.assertIn("tty=True", wait_payload["waitProcess"]["stdout"])
                self.assertIn("got=hello", wait_payload["waitProcess"]["stdout"])
            finally:
                if process_id is not None:
                    record = read_persistent_process_record(Path(base), process_id)
                if record is not None:
                    terminate_persistent_process(record)
                if background is not None:
                    if background.process.poll() is None:
                        background.process.terminate()
                    background.process.wait(timeout=5)

    def test_blocked_exec_returns_a_failure(self) -> None:
        observation = StartCommandObservation(
            kind="start_command",
            process_id="",
            pid=None,
            command="sudo reboot",
            cwd=".",
            ok=False,
            message="Command blocked: high-risk command",
            stdout_path="",
            stderr_path="",
        )
        stdout = io.StringIO()
        with (
            patch(
                "vibeagent.cli_background_exec.start_background_command",
                return_value=observation,
            ),
            redirect_stdout(stdout),
        ):
            exit_code = main(["--bg", "--exec", "sudo reboot", "--json"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertFalse(payload["success"])
        self.assertIn("Command blocked", payload["error"])


if __name__ == "__main__":
    unittest.main()
