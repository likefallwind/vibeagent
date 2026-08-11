from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.agent_result import AgentResult
from vibeagent.agent_runtime_utils import append_session_event
from vibeagent.cli import main
from vibeagent.cli_ephemeral_session import ephemeral_session_scope
from vibeagent.session_conversation import checkpoint_session_conversation
from vibeagent.types import AssistantResponse, ChatMessage
from vibeagent.workspace_core import create_local_workspace


class RecordingRunAgent:
    def __init__(self) -> None:
        self.session_dirs: list[Path] = []
        self.prior_messages: list[ChatMessage] = []

    def __call__(self, task: str, **kwargs: object) -> AgentResult:
        workspace = kwargs["workspace"]
        session_dir = workspace.session_dir  # type: ignore[union-attr]
        self.session_dirs.append(session_dir)
        self.prior_messages = list(kwargs.get("prior_messages", []))  # type: ignore[arg-type]
        append_session_event(
            session_dir,
            "model",
            {
                "iteration": 1,
                "content": [{"type": "text", "text": "Ephemeral task complete."}],
                "usage": {"input_tokens": 12, "output_tokens": 4, "total_tokens": 16},
            },
        )
        append_session_event(
            session_dir,
            "result",
            {"success": True, "completion_ready": True, "message": "Ephemeral task complete."},
        )
        return AgentResult(
            success=True,
            message="Ephemeral task complete.",
            run_dir=workspace.root,  # type: ignore[union-attr]
            run_id=workspace.run_id,  # type: ignore[union-attr]
            iterations=1,
            observations=[],
            steps=[],
            conversation=[ChatMessage(role="assistant", content="Ephemeral task complete.")],
        )


class StructuredClient:
    def complete(self, *args: object, **kwargs: object) -> AssistantResponse:
        return AssistantResponse(content=[{"type": "text", "text": '{"summary":"done"}'}], raw={})


class TextClient:
    def complete(self, *args: object, **kwargs: object) -> AssistantResponse:
        return AssistantResponse(content=[{"type": "text", "text": "Repository inspected."}], raw={})


class CliNoSessionPersistenceTests(unittest.TestCase):
    def test_ephemeral_scope_uses_private_record_root_and_removes_it(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-no-session-") as base:
            project_root = Path(base).resolve()
            with ephemeral_session_scope(project_root) as scope:
                record_root = scope.record_root
                session_dir = scope.workspace.session_dir
                self.assertEqual(scope.workspace.root, project_root)
                self.assertNotIn(project_root, session_dir.parents)
                self.assertTrue(session_dir.is_dir())

            self.assertFalse(record_root.exists())
            self.assertFalse(project_root.joinpath(".vibeagent").exists())

    def test_json_run_reports_usage_then_removes_ephemeral_session(self) -> None:
        runner = RecordingRunAgent()
        with tempfile.TemporaryDirectory(prefix="vibeagent-no-session-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", side_effect=runner),
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "-p",
                        "--no-session-persistence",
                        "--output-format",
                        "json",
                        "--cwd",
                        base,
                        "inspect",
                    ]
                )
            payload = json.loads(stdout.getvalue())

            self.assertEqual(exit_code, 0)
            self.assertFalse(payload["sessionPersistence"])
            self.assertFalse(payload["session_persistence"])
            self.assertTrue(payload["usage"]["exists"])
            self.assertEqual(payload["usage"]["usage"]["tokens"]["total"], 16)
            self.assertFalse(runner.session_dirs[0].exists())
            self.assertFalse(Path(base, ".vibeagent").exists())

    def test_real_agent_loop_completes_without_project_session_storage(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-no-session-real-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client", return_value=TextClient()),
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "-p",
                        "--no-session-persistence",
                        "--output-format",
                        "json",
                        "--cwd",
                        base,
                        "inspect",
                    ]
                )
            payload = json.loads(stdout.getvalue())

            self.assertEqual(exit_code, 0)
            self.assertTrue(payload["success"])
            self.assertEqual(payload["message"], "Repository inspected.")
            self.assertFalse(payload["sessionPersistence"])
            self.assertFalse(Path(base, ".vibeagent").exists())

    def test_stream_json_delivers_ephemeral_events_before_cleanup(self) -> None:
        runner = RecordingRunAgent()
        with tempfile.TemporaryDirectory(prefix="vibeagent-no-session-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", side_effect=runner),
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "-p",
                        "--no-session-persistence",
                        "--output-format",
                        "stream-json",
                        "--cwd",
                        base,
                        "inspect",
                    ]
                )
            rows = [json.loads(line) for line in stdout.getvalue().splitlines()]

            self.assertEqual(exit_code, 0)
            self.assertIn("model", [row.get("event", {}).get("type") for row in rows])
            self.assertEqual(rows[-1]["type"], "result")
            self.assertFalse(rows[-1]["sessionPersistence"])
            self.assertFalse(runner.session_dirs[0].exists())

    def test_structured_output_finishes_before_ephemeral_cleanup(self) -> None:
        runner = RecordingRunAgent()
        schema = json.dumps(
            {
                "type": "object",
                "properties": {"summary": {"type": "string"}},
                "required": ["summary"],
                "additionalProperties": False,
            }
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-no-session-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client", return_value=StructuredClient()),
                patch("vibeagent.cli.run_agent", side_effect=runner),
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "-p",
                        "--no-session-persistence",
                        "--output-format",
                        "json",
                        "--json-schema",
                        schema,
                        "--cwd",
                        base,
                        "inspect",
                    ]
                )
            payload = json.loads(stdout.getvalue())

            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["structured_output"], {"summary": "done"})
            self.assertFalse(runner.session_dirs[0].exists())
            self.assertFalse(Path(base, ".vibeagent").exists())

    def test_failure_cleans_ephemeral_session_before_error_output(self) -> None:
        session_dirs: list[Path] = []

        def fail_agent(task: str, **kwargs: object) -> AgentResult:
            workspace = kwargs["workspace"]
            session_dirs.append(workspace.session_dir)  # type: ignore[union-attr]
            raise RuntimeError("provider failed")

        with tempfile.TemporaryDirectory(prefix="vibeagent-no-session-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", side_effect=fail_agent),
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "-p",
                        "--no-session-persistence",
                        "--output-format",
                        "json",
                        "--cwd",
                        base,
                        "inspect",
                    ]
                )

            self.assertEqual(exit_code, 1)
            self.assertIn("provider failed", json.loads(stdout.getvalue())["error"])
            self.assertFalse(session_dirs[0].exists())
            self.assertFalse(Path(base, ".vibeagent").exists())

    def test_goal_is_rejected_before_the_agent_runs(self) -> None:
        runner = RecordingRunAgent()
        with tempfile.TemporaryDirectory(prefix="vibeagent-no-session-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", side_effect=runner),
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "-p",
                        "--no-session-persistence",
                        "--output-format",
                        "json",
                        "--cwd",
                        base,
                        "/goal",
                        "finish",
                    ]
                )

            self.assertEqual(exit_code, 1)
            self.assertIn("cannot be used", json.loads(stdout.getvalue())["error"])
            self.assertEqual(runner.session_dirs, [])
            self.assertFalse(Path(base, ".vibeagent").exists())

    def test_resume_reads_source_without_modifying_it(self) -> None:
        runner = RecordingRunAgent()
        with tempfile.TemporaryDirectory(prefix="vibeagent-no-session-resume-") as base:
            root = Path(base)
            source_dir = root / ".vibeagent" / "sessions" / "source-run"
            append_session_event(source_dir, "task", {"task": "source task"})
            append_session_event(
                source_dir,
                "result",
                {"success": True, "completion_ready": True, "message": "source complete"},
            )
            checkpoint_session_conversation(
                create_local_workspace(root, "source-run"),
                [
                    ChatMessage(role="user", content="source task"),
                    ChatMessage(role="assistant", content="source answer"),
                ],
                "source task",
            )
            before = _directory_bytes(source_dir)
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", side_effect=runner),
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "-p",
                        "--no-session-persistence",
                        "--resume",
                        "source-run",
                        "--output-format",
                        "json",
                        "--cwd",
                        base,
                        "continue",
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual(_directory_bytes(source_dir), before)
            self.assertEqual([message.content for message in runner.prior_messages], ["source task", "source answer"])
            self.assertNotEqual(runner.session_dirs[0], source_dir)
            self.assertFalse(runner.session_dirs[0].exists())


def _directory_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


if __name__ == "__main__":
    unittest.main()
