import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.action_parsing import ActionParseError, parse_tool_action
from vibeagent.actions import execute_action
from vibeagent.agent import run_agent
from vibeagent.cli_output import prompt_user_input
from vibeagent.session_timeline_reports import format_session_event_timeline_item
from vibeagent.session_types import SessionEvent
from vibeagent.types import AssistantResponse, ChatMessage, ContentBlock, UserInputRequest
from vibeagent.workspace_core import create_run_workspace


class UserInputClient:
    def __init__(self, responses: list[list[ContentBlock]]) -> None:
        self.responses = responses
        self.messages: list[list[ChatMessage]] = []

    def complete(self, messages, tools=None, max_tokens=4096, temperature=0.2, timeout_ms=120_000):
        self.messages.append(list(messages))
        content = self.responses[len(self.messages) - 1]
        return AssistantResponse(content=content, raw={"content": content})


class UserInputTests(unittest.TestCase):
    def test_parse_ask_user_supports_options_and_free_text_policy(self) -> None:
        action = parse_tool_action(
            "ask_user",
            {
                "question": "Which API should be the default?",
                "options": ["REST", "GraphQL"],
                "allow_free_text": False,
            },
        )

        self.assertEqual(action.question, "Which API should be the default?")
        self.assertEqual(action.options, ["REST", "GraphQL"])
        self.assertFalse(action.allow_free_text)

    def test_parse_ask_user_rejects_ambiguous_option_shapes(self) -> None:
        invalid_inputs = [
            {},
            {"question": "Choose", "options": [1]},
            {"question": "Choose", "options": ["same", "same"]},
            {"question": "Choose", "options": [], "allow_free_text": False},
        ]

        for tool_input in invalid_inputs:
            with self.subTest(tool_input=tool_input), self.assertRaises(ActionParseError):
                parse_tool_action("ask_user", tool_input)

    def test_direct_action_execution_reports_missing_user_input_handler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-user-input-") as base:
            workspace = create_run_workspace(Path(base))
            action = parse_tool_action("ask_user", {"question": "Which database?"})

            observation = execute_action(workspace, action)

        self.assertEqual(observation.kind, "ask_user")
        self.assertTrue(observation.cancelled)
        self.assertIsNone(observation.answer)

    def test_prompt_user_input_maps_number_to_option(self) -> None:
        request = UserInputRequest(
            question="Choose a database",
            options=["SQLite", "PostgreSQL"],
            allow_free_text=False,
        )
        stdout = io.StringIO()

        with patch("builtins.input", return_value="2"), redirect_stdout(stdout):
            answer = prompt_user_input(request)

        self.assertEqual(answer, "PostgreSQL")
        self.assertIn("Question: Choose a database", stdout.getvalue())
        self.assertIn("1. SQLite", stdout.getvalue())

    def test_prompt_user_input_reprompts_for_invalid_closed_choice(self) -> None:
        request = UserInputRequest("Choose", ["A", "B"], allow_free_text=False)
        stdout = io.StringIO()

        with patch("builtins.input", side_effect=["other", "1"]), redirect_stdout(stdout):
            answer = prompt_user_input(request)

        self.assertEqual(answer, "A")

    def test_agent_returns_user_answer_to_model_and_logs_session_events(self) -> None:
        client = UserInputClient(
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
                [{"type": "text", "text": "Using PostgreSQL."}],
            ]
        )
        requests: list[UserInputRequest] = []

        with tempfile.TemporaryDirectory(prefix="vibeagent-user-input-") as base:
            result = run_agent(
                "Configure storage",
                base_dir=Path(base),
                client=client,
                max_iterations=2,
                user_input_handler=lambda request: requests.append(request) or "PostgreSQL",
            )
            events = [
                json.loads(line)
                for line in (Path(base) / ".vibeagent" / "sessions" / result.run_id / "events.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]

        self.assertTrue(result.success)
        self.assertEqual(result.message, "Using PostgreSQL.")
        self.assertEqual(requests[0].question, "Which database?")
        self.assertEqual(result.observations[0].answer, "PostgreSQL")
        tool_result = json.loads(client.messages[1][-1].content[0]["content"])
        self.assertEqual(tool_result["answer"], "PostgreSQL")
        self.assertEqual(
            [event["type"] for event in events if event["type"].startswith("user_input_")],
            ["user_input_requested", "user_input_answered"],
        )

    def test_session_timeline_formats_user_input_events(self) -> None:
        requested = SessionEvent(
            line_number=1,
            type="user_input_requested",
            payload={"request": {"question": "Which database?", "options": ["A", "B"]}},
        )
        answered = SessionEvent(
            line_number=2,
            type="user_input_answered",
            payload={"result": {"answer": "B", "cancelled": False}},
        )

        self.assertIn("Which database?", format_session_event_timeline_item(requested))
        self.assertIn("options=2", format_session_event_timeline_item(requested))
        self.assertIn("answer=B", format_session_event_timeline_item(answered))

    def test_agent_reports_unavailable_input_without_guessing(self) -> None:
        client = UserInputClient(
            [
                [
                    {
                        "type": "tool_call",
                        "id": "ask-1",
                        "name": "ask_user",
                        "input": {"question": "Which database?"},
                    }
                ],
                [{"type": "text", "text": "Which database should I use?"}],
            ]
        )

        with tempfile.TemporaryDirectory(prefix="vibeagent-user-input-") as base:
            result = run_agent("Configure storage", base_dir=Path(base), client=client, max_iterations=2)

        self.assertTrue(result.success)
        self.assertTrue(result.observations[0].cancelled)
        self.assertIn("without guessing", result.observations[0].message)


if __name__ == "__main__":
    unittest.main()
