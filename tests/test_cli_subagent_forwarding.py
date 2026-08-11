from __future__ import annotations

import io
import json
from pathlib import Path
import unittest

from vibeagent.cli_stream_output import JsonEventStream
from vibeagent.cli_subagent_forwarding import SubagentStreamForwarder


class SubagentStreamForwarderTests(unittest.TestCase):
    def test_forwards_linked_text_thinking_and_tool_results_after_source_events(self) -> None:
        output = io.StringIO()
        stream = JsonEventStream(output)
        forward = SubagentStreamForwarder(stream, enabled=True)
        session_dir = Path("/project/.vibeagent/sessions/run-1")

        forward(session_dir, {
            "type": "subagent_started",
            "subagent_id": "agent-1",
            "parent_tool_use_id": "delegate-tool-1",
        })
        forward(session_dir, {
            "type": "subagent_model",
            "subagent_id": "agent-1",
            "content": [
                {"type": "text", "text": "Found src/app.py:12."},
                {"type": "thinking", "thinking": "Check the caller.", "signature": "private-signature"},
                {"type": "tool_call", "id": "read-1", "name": "Read", "input": {"path": "src/app.py"}},
            ],
        })
        forward(session_dir, {
            "type": "subagent_tool_result",
            "subagent_id": "agent-1",
            "id": "read-1",
            "failed": False,
            "result": {"kind": "read_file", "path": "src/app.py"},
        })

        records = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual([record["sequence"] for record in records], [1, 2, 3, 4, 5])
        self.assertEqual([record["type"] for record in records], ["event", "event", "assistant", "event", "user"])
        assistant = records[2]
        self.assertEqual(assistant["parent_tool_use_id"], "delegate-tool-1")
        self.assertEqual(assistant["subagentId"], "agent-1")
        self.assertEqual(
            [block["type"] for block in assistant["message"]["content"]],
            ["text", "thinking"],
        )
        self.assertNotIn("tool_call", json.dumps(assistant))
        self.assertNotIn("private-signature", json.dumps(assistant))
        user = records[4]
        self.assertEqual(user["parent_tool_use_id"], "delegate-tool-1")
        tool_result = user["message"]["content"][0]
        self.assertEqual(tool_result["type"], "tool_result")
        self.assertEqual(tool_result["tool_use_id"], "read-1")
        self.assertEqual(json.loads(tool_result["content"])["path"], "src/app.py")

    def test_disabled_forwarder_and_non_text_model_blocks_emit_only_source_events(self) -> None:
        for enabled, event in (
            (False, {"type": "subagent_model", "subagent_id": "agent-1", "content": [{"type": "text", "text": "hidden"}]}),
            (True, {"type": "subagent_model", "subagent_id": "agent-1", "content": [{"type": "tool_call", "id": "x"}]}),
        ):
            with self.subTest(enabled=enabled):
                output = io.StringIO()
                forward = SubagentStreamForwarder(JsonEventStream(output), enabled=enabled)
                forward(Path("/sessions/run-1"), event)
                records = [json.loads(line) for line in output.getvalue().splitlines()]
                self.assertEqual(len(records), 1)
                self.assertEqual(records[0]["type"], "event")

    def test_falls_back_to_subagent_id_and_marks_failed_tool_results(self) -> None:
        output = io.StringIO()
        forward = SubagentStreamForwarder(JsonEventStream(output), enabled=True)
        forward(Path("/sessions/run-1"), {
            "type": "subagent_tool_result",
            "subagent_id": "orphan-agent",
            "id": "tool-1",
            "failed": True,
            "result": {"kind": "tool_error", "message": "failed"},
        })

        record = json.loads(output.getvalue().splitlines()[1])
        self.assertEqual(record["parent_tool_use_id"], "orphan-agent")
        self.assertTrue(record["message"]["content"][0]["is_error"])


if __name__ == "__main__":
    unittest.main()
