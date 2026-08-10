from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock, patch

from vibeagent import MACHINE_OUTPUT_SCHEMA_VERSION, __version__
from vibeagent.agent_result import AgentResult
from vibeagent.agent_runtime_utils import append_session_event
from vibeagent.cli import main
from vibeagent.cli_args import parse_args
from vibeagent.runtime_types import AssistantResponse, ChatMessage
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
    def test_json_schema_cli_returns_validated_structured_output(self) -> None:
        client = SequenceClient(
            [[{"type": "text", "text": '{"summary":"inspected","files":2}'}]]
        )
        schema = json.dumps(
            {
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "files": {"type": "integer"},
                },
                "required": ["summary", "files"],
                "additionalProperties": False,
            }
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-structured-cli-") as base:
            root = Path(base)
            (root / ".vibeagent" / "sessions" / "stream-run").mkdir(parents=True)
            result = replace(
                _result(root),
                conversation=[
                    ChatMessage(role="user", content="Inspect the repository."),
                    ChatMessage(role="assistant", content="Inspected two files."),
                ],
            )
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client", return_value=client),
                patch("vibeagent.cli.run_agent", return_value=result),
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "-p",
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
        self.assertEqual(payload["subtype"], "success")
        self.assertEqual(payload["structured_output"], {"summary": "inspected", "files": 2})
        self.assertEqual(payload["structuredOutput"], payload["structured_output"])
        self.assertEqual(payload["structured_output_attempts"], 1)

    def test_json_schema_cli_fails_after_bounded_validation_retries(self) -> None:
        client = SequenceClient(
            [[{"type": "text", "text": '{"files":"two"}'}]] * 3
        )
        schema = json.dumps(
            {
                "type": "object",
                "properties": {"files": {"type": "integer"}},
                "required": ["files"],
                "additionalProperties": False,
            }
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-structured-cli-") as base:
            root = Path(base)
            (root / ".vibeagent" / "sessions" / "stream-run").mkdir(parents=True)
            result = replace(
                _result(root),
                conversation=[
                    ChatMessage(role="user", content="Inspect the repository."),
                    ChatMessage(role="assistant", content="Inspected two files."),
                ],
            )
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client", return_value=client),
                patch("vibeagent.cli.run_agent", return_value=result),
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    ["-p", "--output-format", "json", "--json-schema", schema, "--cwd", base, "inspect"]
                )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertEqual(client.calls, 3)
        self.assertEqual(payload["subtype"], "error_max_structured_output_retries")
        self.assertEqual(payload["stopReason"], "error_max_structured_output_retries")
        self.assertEqual(payload["structured_output_attempts"], 3)
        self.assertNotIn("structured_output", payload)

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
        self.assertEqual(records[0]["schemaVersion"], MACHINE_OUTPUT_SCHEMA_VERSION)
        self.assertEqual(records[0]["version"], __version__)
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
            session_dir = Path(base) / ".vibeagent" / "sessions" / "stream-run"
            session_dir.mkdir(parents=True)
            (session_dir / "events.jsonl").write_text(
                json.dumps(
                    {
                        "type": "model",
                        "iteration": 1,
                        "usage": {"input_tokens": 10, "output_tokens": 4, "total_tokens": 14},
                        "content": [{"type": "text", "text": "done"}],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", return_value=_result(Path(base))),
                patch("vibeagent.cli_runner.monotonic", side_effect=[10.0, 10.123]),
                patch.dict(
                    os.environ,
                    {
                        "VIBEAGENT_INPUT_USD_PER_MILLION": "1",
                        "VIBEAGENT_OUTPUT_USD_PER_MILLION": "2",
                    },
                    clear=True,
                ),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--output-format", "json", "--cwd", base, "inspect"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["kind"], "code")
        self.assertEqual(payload["schemaVersion"], MACHINE_OUTPUT_SCHEMA_VERSION)
        self.assertEqual(payload["version"], __version__)
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["stopReason"], "completed")
        self.assertEqual(payload["stop_reason"], "completed")
        self.assertEqual(payload["exitCode"], 0)
        self.assertEqual(payload["exit_code"], 0)
        self.assertEqual(payload["result"], payload["message"])
        self.assertEqual(payload["numTurns"], 1)
        self.assertEqual(payload["num_turns"], 1)
        self.assertEqual(payload["sessionId"], payload["runId"])
        self.assertEqual(payload["session_id"], payload["runId"])
        self.assertEqual(payload["durationMs"], 123)
        self.assertEqual(payload["duration_ms"], 123)
        self.assertEqual(payload["usage"]["usage"]["sessions"], 1)
        self.assertEqual(payload["usage"]["usage"]["tokens"]["input"], 10)
        self.assertEqual(payload["usage"]["usage"]["tokens"]["output"], 4)
        self.assertEqual(payload["usage"]["usage"]["tokens"]["total"], 14)
        self.assertTrue(payload["cost"]["estimate"]["available"])
        self.assertEqual(payload["cost"]["estimate"]["estimatedCostUsd"], "0.000018")
        self.assertNotIn("type", payload)
        self.assertNotIn("sequence", payload)

    def test_json_output_reports_pending_user_input_requests(self) -> None:
        client = SequenceClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "ask-1",
                        "name": "ask_user",
                        "input": {
                            "question": "Which database?",
                            "options": ["SQLite", "PostgreSQL"],
                            "allow_free_text": False,
                        },
                    }
                ],
                [{"type": "text", "text": "Which database should I use?"}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-stream-") as base:
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client", return_value=client),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--json", "--cwd", base, "--max-iterations", "2", "configure", "storage"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["pendingUserInput"])
        self.assertTrue(payload["pending_user_input"])
        self.assertEqual(payload["userInputRequests"][0]["question"], "Which database?")
        self.assertEqual(payload["userInputRequests"][0]["options"], ["SQLite", "PostgreSQL"])
        self.assertIsNone(payload["userInputRequests"][0]["answer"])
        self.assertTrue(payload["userInputRequests"][0]["cancelled"])
        self.assertEqual(payload["user_input_requests"], payload["userInputRequests"])


class CliStreamJsonTests(unittest.TestCase):
    def test_stream_json_emits_structured_output_events_and_result(self) -> None:
        client = SequenceClient(
            [[{"type": "text", "text": '{"summary":"inspected"}'}]]
        )
        schema = json.dumps(
            {
                "type": "object",
                "properties": {"summary": {"type": "string"}},
                "required": ["summary"],
                "additionalProperties": False,
            }
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-structured-stream-") as base:
            def run_agent(task: str, **kwargs: object) -> AgentResult:
                workspace = kwargs["workspace"]
                return replace(
                    _result(Path(base), workspace.run_id),
                    conversation=[
                        ChatMessage(role="user", content="Inspect the repository."),
                        ChatMessage(role="assistant", content="Inspection complete."),
                    ],
                )

            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client", return_value=client),
                patch("vibeagent.cli.run_agent", side_effect=run_agent),
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "-p",
                        "--output-format",
                        "stream-json",
                        "--json-schema",
                        schema,
                        "--cwd",
                        base,
                        "inspect",
                    ]
                )

        records = [json.loads(line) for line in stdout.getvalue().splitlines()]
        event_types = [record["event"]["type"] for record in records if record["type"] == "event"]
        final = records[-1]
        self.assertEqual(exit_code, 0)
        self.assertEqual(event_types, ["structured_output_model", "structured_output_result"])
        self.assertEqual(final["type"], "result")
        self.assertEqual(final["structured_output"], {"summary": "inspected"})
        self.assertEqual(final["structured_output_attempts"], 1)

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
        self.assertTrue(all(record["schemaVersion"] == MACHINE_OUTPUT_SCHEMA_VERSION for record in event_records))
        self.assertTrue(all(record["version"] == __version__ for record in event_records))
        self.assertEqual(event_types[-1], "result")
        self.assertEqual(final["type"], "result")
        self.assertEqual(final["kind"], "code")
        self.assertEqual(final["schemaVersion"], MACHINE_OUTPUT_SCHEMA_VERSION)
        self.assertEqual(final["version"], __version__)
        self.assertEqual(final["status"], "completed")
        self.assertEqual(final["stopReason"], "completed")
        self.assertEqual(final["stop_reason"], "completed")
        self.assertEqual(final["numTurns"], 1)
        self.assertEqual(final["num_turns"], 1)
        self.assertEqual(final["sessionId"], final["runId"])
        self.assertEqual(final["session_id"], final["runId"])
        self.assertEqual(final["message"], "Inspected the project.")
        self.assertEqual(final["result"], "Inspected the project.")
        self.assertIsInstance(final["durationMs"], int)
        self.assertGreaterEqual(final["durationMs"], 0)
        self.assertIsInstance(final["duration_ms"], int)
        self.assertGreaterEqual(final["duration_ms"], 0)
        self.assertTrue(final["usage"]["exists"])
        self.assertEqual(final["usage"]["usage"]["sessions"], 1)
        self.assertEqual(final["usage"]["usage"]["tokens"]["input"], 0)
        self.assertTrue(all(record["runId"] == final["runId"] for record in event_records))
        self.assertTrue(all(record["sessionId"] == final["sessionId"] for record in event_records))
        self.assertTrue(all(record["session_id"] == final["session_id"] for record in event_records))

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

    def test_stream_json_accept_edits_permission_source_is_streamed(self) -> None:
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
                        "--permission-mode",
                        "acceptEdits",
                        "--cwd",
                        base,
                        "inspect",
                    ]
                )

        records = [json.loads(line) for line in stdout.getvalue().splitlines()]
        loaded = next(record["event"] for record in records if record["type"] == "event" and record["event"]["type"] == "permissions_loaded")
        self.assertEqual(exit_code, 0)
        self.assertEqual(loaded["count"], 4)
        self.assertIn("<cli --permission-mode acceptEdits>", loaded["sources"])
        self.assertIn("<cli --permission-mode acceptEdits>", loaded["trusted_allow_sources"])

    def test_stream_json_strict_mcp_config_marks_stream_workspace(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-stream-") as base:
            root = Path(base)
            (root / "extra.mcp.json").write_text('{"mcpServers": {}}', encoding="utf-8")
            run_agent = Mock(return_value=_result(root))

            with (
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(
                    [
                        "--output-format",
                        "stream-json",
                        "--mcp-config",
                        "extra.mcp.json",
                        "--strict-mcp-config",
                        "--cwd",
                        base,
                        "inspect",
                    ]
                )

        self.assertEqual(exit_code, 0)
        workspace = run_agent.call_args.kwargs["workspace"]
        self.assertTrue(workspace.strict_mcp_config)
        self.assertEqual(workspace.mcp_config_paths, (root / "extra.mcp.json",))

    def test_stream_json_input_roles_feed_system_prompt_and_prior_context(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-stream-") as base:
            stdout = io.StringIO()
            stdin = io.StringIO(
                json.dumps(
                    {
                        "messages": [
                            {"role": "system", "content": "Prefer focused tests."},
                            {"role": "assistant", "content": "I previously found tests/test_app.py."},
                            {"role": "user", "content": "fix the failing test"},
                        ]
                    }
                )
                + "\n"
            )
            root = Path(base)
            run_agent = Mock(return_value=_result(root))
            with (
                patch("sys.stdin", stdin),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", run_agent),
                patch("vibeagent.cli.get_compact_context", return_value=(None, None, "No sessions found.")),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--output-format", "json", "--input-format", "stream-json", "--cwd", base, "-"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["kind"], "code")
        self.assertEqual(run_agent.call_args.args[0], "fix the failing test")
        self.assertEqual(run_agent.call_args.kwargs["system_prompt"], "Prefer focused tests.")
        self.assertIn("Structured input assistant messages:", run_agent.call_args.kwargs["prior_context"])
        self.assertIn("tests/test_app.py", run_agent.call_args.kwargs["prior_context"])

    def test_stream_json_emits_structured_empty_input_error(self) -> None:
        stdout = io.StringIO()

        with (
            patch("sys.stdin", io.StringIO("\n")),
            patch("vibeagent.cli_runner.monotonic", side_effect=[40.0, 40.125]),
            redirect_stdout(stdout),
        ):
            exit_code = main(["--output-format", "stream-json", "-"])

        records = [json.loads(line) for line in stdout.getvalue().splitlines()]
        self.assertEqual(exit_code, 1)
        self.assertEqual(records, [{
            "durationMs": 125,
            "duration_ms": 125,
            "error": "No task provided.",
            "exitCode": 1,
            "exit_code": 1,
            "kind": "error",
            "sequence": 1,
            "schemaVersion": MACHINE_OUTPUT_SCHEMA_VERSION,
            "status": "failed",
            "stopReason": "failed",
            "stop_reason": "failed",
            "success": False,
            "type": "result",
            "version": __version__,
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
        self.assertEqual(records[0]["schemaVersion"], MACHINE_OUTPUT_SCHEMA_VERSION)
        self.assertEqual(records[0]["version"], __version__)
        self.assertEqual(records[0]["message"], "hello")
        self.assertEqual(records[0]["result"], "hello")
        self.assertEqual(records[0]["numTurns"], 1)
        self.assertEqual(records[0]["num_turns"], 1)
        self.assertIsInstance(records[0]["durationMs"], int)
        self.assertGreaterEqual(records[0]["durationMs"], 0)
        self.assertIsInstance(records[0]["duration_ms"], int)
        self.assertGreaterEqual(records[0]["duration_ms"], 0)


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
