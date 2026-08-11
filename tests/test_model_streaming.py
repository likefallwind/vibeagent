from __future__ import annotations

import json
import unittest

from vibeagent.anthropic_streaming import accumulate_anthropic_stream
from vibeagent.openai_streaming import accumulate_openai_chat_stream
from vibeagent.sse import SseProtocolError, iter_sse_json


def _sse(*events: dict[str, object] | str) -> list[bytes]:
    lines: list[bytes] = []
    for event in events:
        payload = event if isinstance(event, str) else json.dumps(event)
        lines.extend([f"data: {payload}\n".encode(), b"\n"])
    return lines


class SseParserTests(unittest.TestCase):
    def test_parses_comments_multiline_data_and_done(self) -> None:
        lines = [b": ping\n", b"data: {\"value\":\n", b"data: 1}\n", b"\n", b"data: [DONE]\n", b"\n"]

        self.assertEqual(list(iter_sse_json(lines)), [{"value": 1}])

    def test_rejects_invalid_json_and_oversized_events(self) -> None:
        with self.assertRaises(SseProtocolError):
            list(iter_sse_json([b"data: nope\n", b"\n"]))
        with self.assertRaisesRegex(SseProtocolError, "2-byte limit"):
            list(iter_sse_json([b"data: abc\n", b"\n"], max_event_bytes=2))

    def test_rejects_invalid_utf8(self) -> None:
        with self.assertRaisesRegex(SseProtocolError, "valid UTF-8"):
            list(iter_sse_json([b"data: \xff\n", b"\n"]))


class AnthropicStreamTests(unittest.TestCase):
    def test_accumulates_text_tool_input_and_usage(self) -> None:
        events: list[dict[str, object]] = []
        data = accumulate_anthropic_stream(
            _sse(
                {"type": "message_start", "message": {"id": "m1", "usage": {"input_tokens": 8}}},
                {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
                {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Hi"}},
                {"type": "content_block_stop", "index": 0},
                {"type": "content_block_start", "index": 1, "content_block": {"type": "tool_use", "id": "t1", "name": "read_file", "input": {}}},
                {"type": "content_block_delta", "index": 1, "delta": {"type": "input_json_delta", "partial_json": '{"path":'}},
                {"type": "content_block_delta", "index": 1, "delta": {"type": "input_json_delta", "partial_json": '"app.py"}'}},
                {"type": "content_block_stop", "index": 1},
                {"type": "message_delta", "delta": {"stop_reason": "tool_use"}, "usage": {"output_tokens": 5}},
                {"type": "message_stop"},
            ),
            on_event=events.append,
            response_error=RuntimeError,
        )

        self.assertEqual(data["content"][0]["text"], "Hi")
        self.assertEqual(data["content"][1]["input"], {"path": "app.py"})
        self.assertEqual(data["usage"], {"input_tokens": 8, "output_tokens": 5})
        self.assertEqual(events[-1]["type"], "message_stop")

    def test_rejects_truncated_stream(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "message_stop"):
            accumulate_anthropic_stream(
                _sse({"type": "message_start", "message": {}}),
                on_event=lambda _event: None,
                response_error=RuntimeError,
            )


class OpenAIStreamTests(unittest.TestCase):
    def test_accumulates_text_tool_calls_and_emits_canonical_events(self) -> None:
        events: list[dict[str, object]] = []
        data = accumulate_openai_chat_stream(
            _sse(
                {"id": "c1", "model": "test", "choices": [{"delta": {"content": "Hi"}, "finish_reason": None}]},
                {"id": "c1", "model": "test", "choices": [{"delta": {"tool_calls": [{"index": 0, "id": "t1", "function": {"name": "read_file", "arguments": '{"path":'}}]}, "finish_reason": None}]},
                {"id": "c1", "model": "test", "choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": '"app.py"}'}}]}, "finish_reason": "tool_calls"}]},
                {"id": "c1", "model": "test", "choices": [], "usage": {"prompt_tokens": 9, "completion_tokens": 4, "total_tokens": 13}},
                "[DONE]",
            ),
            on_event=events.append,
            response_error=RuntimeError,
        )

        message = data["choices"][0]["message"]
        self.assertEqual(message["content"], "Hi")
        self.assertEqual(message["tool_calls"][0]["function"]["arguments"], '{"path":"app.py"}')
        self.assertEqual(data["usage"]["total_tokens"], 13)
        self.assertEqual(events[0]["type"], "message_start")
        self.assertEqual(events[-1]["type"], "message_stop")

    def test_rejects_stream_without_finish_reason(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "finish reason"):
            accumulate_openai_chat_stream(
                _sse({"id": "c1", "choices": [{"delta": {"content": "partial"}}]}),
                on_event=lambda _event: None,
                response_error=RuntimeError,
            )


if __name__ == "__main__":
    unittest.main()
