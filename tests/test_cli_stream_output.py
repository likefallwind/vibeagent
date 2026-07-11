from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

from vibeagent.agent_result import AgentResult
from vibeagent.agent_runtime_utils import append_session_event
from vibeagent.cli import main
from vibeagent.cli_args import parse_args
from vibeagent.runtime_types import AssistantResponse
from vibeagent.session_event_observers import observe_session_events


class TextClient:
    def complete(self, messages, tools=None, max_tokens=4096, temperature=0.2, timeout_ms=120_000):
        return AssistantResponse(content=[{"type": "text", "text": "Inspected the project."}], raw={})


class SequenceClient:
    def __init__(self, responses: list[list[dict[str, object]]]) -> None:
        self.responses = responses
        self.calls = 0

    def complete(self, messages, tools=None, max_tokens=4096, temperature=0.2, timeout_ms=120_000):
        content = self.responses[self.calls]
        self.calls += 1
        return AssistantResponse(content=content, raw={})


def _result(root: Path, run_id: str = "stream-run") -> AgentResult:
    return AgentResult(
        success=True,
        message="done",
        run_dir=root,
        run_id=run_id,
        iterations=1,
        observations=[],
        steps=[],
    )


class CliOutputFormatTests(unittest.TestCase):
    def test_json_alias_and_output_format_normalize_to_machine_output(self) -> None:
        alias = parse_args(["--json", "inspect"])
        explicit_json = parse_args(["--output-format", "json", "inspect"])
        stream = parse_args(["--output-format", "stream-json", "inspect"])

        self.assertEqual((alias.output_format, alias.json), ("json", True))
        self.assertEqual((explicit_json.output_format, explicit_json.json), ("json", True))
        self.assertEqual((stream.output_format, stream.json), ("stream-json", True))

    def test_stream_json_requires_a_one_shot_task(self) -> None:
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            exit_code = main(["--output-format", "stream-json"])

        records = [json.loads(line) for line in stdout.getvalue().splitlines()]
        self.assertEqual(exit_code, 2)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["type"], "result")
        self.assertEqual(records[0]["sequence"], 1)
        self.assertIn("requires a one-shot task", records[0]["error"])

    def test_stream_json_rejects_local_flags_even_with_positional_arguments(self) -> None:
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            exit_code = main(["--output-format", "stream-json", "--diff", "", "app.py"])

        records = [json.loads(line) for line in stdout.getvalue().splitlines()]
        self.assertEqual(exit_code, 2)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["type"], "result")
        self.assertIn("requires a one-shot task", records[0]["error"])

    def test_output_format_json_matches_single_json_result(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-stream-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", return_value=_result(Path(base))),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--output-format", "json", "--cwd", base, "inspect"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["kind"], "code")
        self.assertEqual(payload["status"], "completed")
        self.assertNotIn("type", payload)
        self.assertNotIn("sequence", payload)


class CliStreamJsonTests(unittest.TestCase):
    def test_real_agent_streams_session_events_then_final_result(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-stream-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client", return_value=TextClient()),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--output-format", "stream-json", "--cwd", base, "inspect", "project"])

        records = [json.loads(line) for line in stdout.getvalue().splitlines()]
        event_records = [record for record in records if record["type"] == "event"]
        event_types = [record["event"]["type"] for record in event_records]
        final = records[-1]

        self.assertEqual(exit_code, 0)
        self.assertEqual([record["sequence"] for record in records], list(range(1, len(records) + 1)))
        self.assertEqual(event_types[0], "task")
        self.assertIn("tool_catalog_initialized", event_types)
        self.assertLess(event_types.index("model"), event_types.index("result"))
        self.assertEqual(event_types[-1], "result")
        self.assertEqual(final["type"], "result")
        self.assertEqual(final["kind"], "code")
        self.assertEqual(final["status"], "completed")
        self.assertEqual(final["message"], "Inspected the project.")
        self.assertTrue(all(record["runId"] == final["runId"] for record in event_records))

    def test_stream_json_disables_interactive_handlers_by_default(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-stream-") as base:
            root = Path(base)
            run_agent = Mock(return_value=_result(root))
            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--output-format", "stream-json", "--cwd", base, "change", "file"])

        self.assertEqual(exit_code, 0)
        self.assertIsNone(run_agent.call_args.kwargs["approval_handler"])
        self.assertIsNone(run_agent.call_args.kwargs["user_input_handler"])
        self.assertEqual(run_agent.call_args.kwargs["workspace"].root, root.resolve())

    def test_stream_json_default_ask_denies_write_without_polluting_stdout(self) -> None:
        client = SequenceClient(
            [
                [{"type": "tool_call", "id": "write-1", "name": "write_file", "input": {"path": "blocked.txt", "content": "no\n"}}],
                [{"type": "text", "text": "The write was denied."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-stream-") as base:
            root = Path(base)
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client", return_value=client),
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    ["--output-format", "stream-json", "--max-iterations", "2", "--cwd", base, "write", "blocked.txt"]
                )
            file_exists = root.joinpath("blocked.txt").exists()

        records = [json.loads(line) for line in stdout.getvalue().splitlines()]
        event_types = [record["event"]["type"] for record in records if record["type"] == "event"]
        self.assertEqual(exit_code, 1)
        self.assertFalse(file_exists)
        self.assertIn("approval_requested", event_types)
        self.assertIn("approval_decision", event_types)
        self.assertEqual(records[-1]["type"], "result")
        self.assertEqual(records[-1]["status"], "blocked")

    def test_stream_json_allowed_tools_source_is_streamed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-stream-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client", return_value=TextClient()),
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--output-format",
                        "stream-json",
                        "--allowed-tools",
                        "Read",
                        "--cwd",
                        base,
                        "inspect",
                    ]
                )

        records = [json.loads(line) for line in stdout.getvalue().splitlines()]
        loaded = next(record["event"] for record in records if record["type"] == "event" and record["event"]["type"] == "permissions_loaded")
        self.assertEqual(exit_code, 0)
        self.assertIn("<cli --allowed-tools>", loaded["sources"])
        self.assertIn("<cli --allowed-tools>", loaded["trusted_allow_sources"])

    def test_stream_json_emits_structured_empty_input_error(self) -> None:
        stdout = io.StringIO()

        with patch("sys.stdin", io.StringIO("\n")), redirect_stdout(stdout):
            exit_code = main(["--output-format", "stream-json", "-"])

        records = [json.loads(line) for line in stdout.getvalue().splitlines()]
        self.assertEqual(exit_code, 1)
        self.assertEqual(records, [{
            "error": "No task provided.",
            "kind": "error",
            "sequence": 1,
            "status": "failed",
            "success": False,
            "type": "result",
        }])

    def test_stream_json_chat_emits_one_final_result(self) -> None:
        stdout = io.StringIO()
        with (
            patch("vibeagent.cli.create_chat_client", return_value=object()),
            patch("vibeagent.cli.run_chat", return_value="hello"),
            redirect_stdout(stdout),
        ):
            exit_code = main(["--output-format", "stream-json", "--chat", "hello"])

        records = [json.loads(line) for line in stdout.getvalue().splitlines()]
        self.assertEqual(exit_code, 0)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["type"], "result")
        self.assertEqual(records[0]["kind"], "chat")
        self.assertEqual(records[0]["message"], "hello")


class SessionEventObserverTests(unittest.TestCase):
    def test_observer_receives_sanitized_written_event_only_inside_scope(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-stream-") as base:
            session_dir = Path(base) / "sessions" / "run-1"
            observed: list[tuple[Path, dict[str, object]]] = []
            with observe_session_events(session_dir, lambda path, event: observed.append((path, event))):
                append_session_event(session_dir, "task", {"task": "inspect", "api_key": "secret"})
            append_session_event(session_dir, "result", {"success": True})

        self.assertEqual(len(observed), 1)
        self.assertEqual(observed[0][0], session_dir)
        self.assertEqual(observed[0][1]["type"], "task")
        self.assertNotEqual(observed[0][1].get("api_key"), "secret")


if __name__ == "__main__":
    unittest.main()
