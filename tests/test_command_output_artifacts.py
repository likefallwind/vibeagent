from __future__ import annotations

from dataclasses import asdict
import os
from pathlib import Path
import tempfile
import unittest

from vibeagent.action_process_types import RunCommandAction
from vibeagent.command_output_artifacts import (
    OUTPUT_DIRECTORY_NAME,
    resolve_command_output_artifact,
)
from vibeagent.local_runtime_report_formatting import format_run_report_text
from vibeagent.local_runtime_reports import serialize_command_result
from vibeagent.process_runtime import execute_run_command_item
from vibeagent.prompts import format_observations
from vibeagent.types import RunCommandObservation
from vibeagent.session_command_reports import (
    format_session_command_entry,
    serialize_session_command_with_output,
)
from vibeagent.workspace_core import RunWorkspace, create_run_workspace
from vibeagent.workspace_file_read import read_project_file_result


class CommandOutputArtifactTests(unittest.TestCase):
    def test_truncated_foreground_output_is_private_and_readable_by_exact_reference(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-command-output-") as base:
            root = Path(base)
            workspace = create_run_workspace(root, "artifact-run")
            stdout = "stdout-line\n" * 200
            stderr = "stderr-line\n" * 200
            command = (
                "python3 -c \"import sys; "
                f"sys.stdout.write({stdout!r}); sys.stderr.write({stderr!r})\""
            )

            result = execute_run_command_item(
                workspace,
                RunCommandAction(type="run_command", command=command, max_output_chars=1_000),
                30_000,
            )

            self.assertEqual(result.exit_code, 0)
            self.assertTrue(result.stdout_truncated)
            self.assertTrue(result.stderr_truncated)
            self.assertEqual(result.stdout_total_bytes, len(stdout.encode("utf-8")))
            self.assertEqual(result.stderr_total_bytes, len(stderr.encode("utf-8")))
            self.assertIsNone(result.output_artifact_error)
            for reference, expected in (
                (result.stdout_path, stdout),
                (result.stderr_path, stderr),
            ):
                self.assertIsNotNone(reference)
                assert reference is not None
                artifact = resolve_command_output_artifact(workspace, reference)
                self.assertIsNotNone(artifact)
                assert artifact is not None
                self.assertEqual(artifact.stat().st_mode & 0o777, 0o600)
                read = read_project_file_result(workspace, reference, max_bytes=20_000)
                self.assertEqual(read["content"], expected)
                self.assertFalse(read["truncated"])

    def test_short_output_does_not_create_artifact_directory(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-command-output-short-") as base:
            workspace = create_run_workspace(Path(base), "short-run")

            result = execute_run_command_item(
                workspace,
                RunCommandAction(type="run_command", command="printf short", max_output_chars=200),
                30_000,
            )

            self.assertEqual(result.stdout, "short")
            self.assertIsNone(result.stdout_path)
            self.assertIsNone(result.stderr_path)
            self.assertFalse((workspace.session_dir / OUTPUT_DIRECTORY_NAME).exists())

    def test_model_observation_exposes_recoverable_output_reference(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-command-output-prompt-") as base:
            workspace = create_run_workspace(Path(base), "prompt-run")
            result = execute_run_command_item(
                workspace,
                RunCommandAction(
                    type="run_command",
                    command="python3 -c \"print('q' * 2000)\"",
                    max_output_chars=1_000,
                ),
                30_000,
            )

            prompt = format_observations(
                [RunCommandObservation(kind="run_command", result=result)]
            )

        self.assertIn(f"stdoutPath: {result.stdout_path}", prompt)
        self.assertIn(f"stdoutTotalBytes: {result.stdout_total_bytes}", prompt)
        self.assertIn("stdoutTruncated: true", prompt)

        report = {
            "projectRoot": workspace.root.as_posix(),
            "message": "Command completed.",
            **serialize_command_result(result),
        }
        rendered = format_run_report_text(report)
        self.assertIn(f"stdoutPath: {result.stdout_path}", rendered)
        self.assertIn(f"stdoutTotalBytes: {result.stdout_total_bytes}", rendered)

        entry = {
            "line_number": 7,
            "kind": "run_command",
            "index": 1,
            "result": asdict(result),
        }
        session_text = "\n".join(format_session_command_entry(entry, 2_000))
        session_payload = serialize_session_command_with_output(entry, 2_000)
        self.assertIn(f"stdoutPath: {result.stdout_path}", session_text)
        self.assertEqual(session_payload["stdoutPath"], result.stdout_path)
        self.assertEqual(session_payload["stdoutTotalBytes"], result.stdout_total_bytes)

    def test_artifact_write_failure_does_not_replace_command_result(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-command-output-error-") as base:
            workspace = create_run_workspace(Path(base), "error-run")
            (workspace.session_dir / OUTPUT_DIRECTORY_NAME).write_text("not a directory", encoding="utf-8")

            result = execute_run_command_item(
                workspace,
                RunCommandAction(
                    type="run_command",
                    command="python3 -c \"print('x' * 2000)\"",
                    max_output_chars=1_000,
                ),
                30_000,
            )

            self.assertEqual(result.exit_code, 0)
            self.assertTrue(result.stdout_truncated)
            self.assertIsNone(result.stdout_path)
            self.assertIn("not a regular directory", result.output_artifact_error or "")

    def test_artifact_reader_rejects_other_protected_files_and_symlinks(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-command-output-safety-") as base:
            root = Path(base)
            workspace = create_run_workspace(root, "safety-run")
            outside = root / "outside.log"
            outside.write_text("outside secret", encoding="utf-8")
            directory = workspace.session_dir / OUTPUT_DIRECTORY_NAME
            directory.mkdir(mode=0o700)
            link = directory / ("a" * 32 + ".stdout.log")
            link.symlink_to(outside)

            with self.assertRaisesRegex(ValueError, "Invalid command output artifact"):
                resolve_command_output_artifact(workspace, link.as_posix())
            with self.assertRaisesRegex(ValueError, "protected"):
                read_project_file_result(workspace, ".vibeagent/sessions/safety-run/events.jsonl")
            with self.assertRaisesRegex(ValueError, "Invalid command output artifact"):
                read_project_file_result(workspace, link.relative_to(root).as_posix())

    def test_artifact_writer_rejects_symlinked_session_directory(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-command-output-session-link-") as base:
            root = Path(base) / "project"
            outside = Path(base) / "outside"
            root.mkdir()
            outside.mkdir()
            session_link = root / "session-link"
            session_link.symlink_to(outside, target_is_directory=True)
            workspace = RunWorkspace(root=root, run_id="linked-run", session_dir=session_link)

            result = execute_run_command_item(
                workspace,
                RunCommandAction(
                    type="run_command",
                    command="python3 -c \"print('x' * 2000)\"",
                    max_output_chars=1_000,
                ),
                30_000,
            )

            self.assertEqual(result.exit_code, 0)
            self.assertIn("session path is not a regular directory", result.output_artifact_error or "")
            self.assertFalse((outside / OUTPUT_DIRECTORY_NAME).exists())

    def test_ephemeral_session_artifact_uses_absolute_readable_reference(self) -> None:
        with (
            tempfile.TemporaryDirectory(prefix="vibeagent-command-root-") as root_base,
            tempfile.TemporaryDirectory(prefix="vibeagent-command-session-") as session_base,
        ):
            root = Path(root_base)
            session_dir = Path(session_base) / "session"
            session_dir.mkdir()
            workspace = RunWorkspace(root=root, run_id="ephemeral-run", session_dir=session_dir)

            result = execute_run_command_item(
                workspace,
                RunCommandAction(
                    type="run_command",
                    command="python3 -c \"print('z' * 2000)\"",
                    max_output_chars=1_000,
                ),
                30_000,
            )

            self.assertTrue(Path(result.stdout_path or "").is_absolute())
            read = read_project_file_result(workspace, result.stdout_path or "", max_bytes=3_000)
            self.assertEqual(read["content"], "z" * 2000 + os.linesep)


if __name__ == "__main__":
    unittest.main()
