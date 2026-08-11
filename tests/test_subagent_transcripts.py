from dataclasses import replace
import tempfile
import unittest
from pathlib import Path

from vibeagent.action_parsing import ActionParseError, parse_tool_action
from vibeagent.agent_delegate import execute_delegate_task_action
from vibeagent.subagent_transcripts import (
    SubagentTranscriptError,
    create_subagent_transcript,
    read_subagent_transcript,
    resume_subagent_transcript,
)
from vibeagent.types import AssistantResponse, ChatMessage
from vibeagent.workspace import create_run_workspace


class TranscriptClient:
    def __init__(self, text: str) -> None:
        self.text = text
        self.messages = []

    def complete(self, messages, tools=None, max_tokens=4096, temperature=0.2, timeout_ms=120_000):
        self.messages.append(list(messages))
        content = [{"type": "text", "text": self.text}]
        return AssistantResponse(content=content, raw={"content": content})


class SubagentTranscriptTests(unittest.TestCase):
    def test_send_message_parser_accepts_claude_shape_and_rejects_unsafe_values(self) -> None:
        action = parse_tool_action("SendMessage", {"to": "delegate-1-1", "message": "  Continue  "})

        self.assertEqual(action.type, "send_message")
        self.assertEqual(action.to, "delegate-1-1")
        self.assertEqual(action.message, "Continue")
        for payload in ({"to": "../escape", "message": "x"}, {"to": "delegate-1", "message": ""}):
            with self.subTest(payload=payload), self.assertRaises(ActionParseError):
                parse_tool_action("SendMessage", payload)

        output = parse_tool_action("TaskOutput", {"task_id": "delegate-1-1"})
        stop = parse_tool_action("TaskStop", {"task_id": "delegate-1-1"})
        self.assertEqual(output.task_id, "delegate-1-1")
        self.assertEqual(stop.task_id, "delegate-1-1")

    def test_completed_subagent_resumes_with_same_id_and_full_history(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-subagent-transcript-") as base:
            workspace = create_run_workspace(Path(base), run_id="resume")
            action = parse_tool_action("delegate_task", {"task": "Inspect auth", "max_iterations": 2})
            first_client = TranscriptClient("Initial finding from auth.py")
            first = execute_delegate_task_action(
                workspace,
                action,
                first_client,
                parent_iteration=1,
                subagent_id="delegate-1-1",
                max_output_tokens=1024,
                model_retries=0,
                model_retry_delay_ms=0,
                model_timeout_ms=10_000,
                command_timeout_ms=10_000,
                logger=None,
            )

            transcript = read_subagent_transcript(workspace, "delegate-1-1")
            resumed_workspace = replace(
                workspace,
                append_subagent_system_prompt="Cite exact middleware paths.",
            )
            second_client = TranscriptClient("Follow-up finding from middleware.py")
            second = execute_delegate_task_action(
                resumed_workspace,
                transcript.action,
                second_client,
                parent_iteration=2,
                subagent_id="delegate-1-1",
                max_output_tokens=1024,
                model_retries=0,
                model_retry_delay_ms=0,
                model_timeout_ms=10_000,
                command_timeout_ms=10_000,
                logger=None,
                resume_transcript=transcript,
                followup_message="Check middleware too",
            )

            resumed = read_subagent_transcript(workspace, "delegate-1-1")

        self.assertEqual(first.task_id, "delegate-1-1")
        self.assertEqual(second.task_id, "delegate-1-1")
        self.assertEqual(resumed.status, "completed")
        self.assertEqual(resumed.runs, 2)
        resumed_text = str(second_client.messages[0])
        self.assertIn("Initial finding from auth.py", resumed_text)
        self.assertIn("Check middleware too", resumed_text)
        self.assertIn("Cite exact middleware paths.", resumed_text)
        self.assertEqual(resumed_text.count("Cite exact middleware paths."), 1)
        self.assertIn("Cite exact middleware paths.", str(resumed.messages[0].content))

    def test_transcript_redacts_secrets_and_rejects_running_resume(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-subagent-transcript-") as base:
            workspace = create_run_workspace(Path(base), run_id="redaction")
            action = parse_tool_action("delegate_task", {"task": "Inspect"})
            messages = [
                ChatMessage(role="system", content="system"),
                ChatMessage(role="user", content="API_KEY=super-secret-value"),
            ]
            create_subagent_transcript(workspace, "delegate-1-1", action, messages)
            transcript = read_subagent_transcript(workspace, "delegate-1-1")

            self.assertIn("[REDACTED]", str(transcript.messages))
            self.assertNotIn("super-secret-value", str(transcript.messages))
            with self.assertRaises(SubagentTranscriptError):
                resume_subagent_transcript(workspace, transcript, transcript.messages)

    def test_transcript_accepts_profile_resolved_max_turns(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-subagent-transcript-") as base:
            workspace = create_run_workspace(Path(base), run_id="profile-max-turns")
            action = parse_tool_action("delegate_task", {"task": "Inspect"})
            resolved = replace(action, max_iterations=50)
            create_subagent_transcript(
                workspace,
                "delegate-1-1",
                resolved,
                [ChatMessage(role="system", content="system")],
            )

            transcript = read_subagent_transcript(workspace, "delegate-1-1")

        self.assertEqual(transcript.action.max_iterations, 50)

    def test_transcript_persists_subagent_hierarchy(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-subagent-transcript-") as base:
            workspace = create_run_workspace(Path(base), run_id="hierarchy")
            action = parse_tool_action("delegate_task", {"task": "Nested check"})
            create_subagent_transcript(
                workspace,
                "agent-child",
                action,
                [ChatMessage(role="system", content="system")],
                depth=2,
                parent_id="agent-parent",
            )
            transcript = read_subagent_transcript(workspace, "agent-child")

        self.assertEqual(transcript.depth, 2)
        self.assertEqual(transcript.parent_id, "agent-parent")


if __name__ == "__main__":
    unittest.main()
