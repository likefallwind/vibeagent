from __future__ import annotations

import io
import unittest
from pathlib import Path

from vibeagent.cli_model_stream import TerminalModelStreamRenderer, terminal_model_stream_scope


class TerminalModelStreamRendererTests(unittest.TestCase):
    def test_scope_only_creates_renderer_for_streaming_clients_and_finishes_it(self) -> None:
        class StreamingClient:
            def complete_stream(self):
                return None

        with terminal_model_stream_scope(object()) as unavailable:
            self.assertIsNone(unavailable)

        lifecycle = []
        with terminal_model_stream_scope(
            StreamingClient(),
            output=io.StringIO(),
            on_display_start=lambda: lifecycle.append("pause"),
            on_display_end=lambda: lifecycle.append("resume"),
        ) as renderer:
            self.assertIsNotNone(renderer)
            renderer.chat_event(
                1,
                {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "partial"}},
            )

        self.assertEqual(lifecycle, ["pause", "resume"])

    def test_renders_only_text_deltas_and_matches_completed_message(self) -> None:
        output = io.StringIO()
        renderer = TerminalModelStreamRenderer(output)

        renderer.agent_event(Path("run-1"), 1, 1, {"type": "message_start"})
        renderer.agent_event(
            Path("run-1"),
            1,
            1,
            {"type": "content_block_delta", "delta": {"type": "thinking_delta", "thinking": "hidden"}},
        )
        renderer.agent_event(
            Path("run-1"),
            1,
            1,
            {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "hello"}},
        )
        renderer.agent_event(
            Path("run-1"),
            1,
            1,
            {"type": "content_block_delta", "delta": {"type": "input_json_delta", "partial_json": "secret"}},
        )
        renderer.agent_event(Path("run-1"), 1, 1, {"type": "message_stop"})

        self.assertEqual(output.getvalue(), "\nhello\n")
        self.assertTrue(renderer.matches_final_message("hello"))
        self.assertFalse(renderer.matches_final_message("different"))

    def test_separates_partial_failed_attempt_from_retry(self) -> None:
        output = io.StringIO()
        renderer = TerminalModelStreamRenderer(output)

        renderer.chat_event(
            1,
            {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "partial"}},
        )
        renderer.chat_event(2, {"type": "message_start"})
        renderer.chat_event(
            2,
            {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "complete"}},
        )
        renderer.chat_event(2, {"type": "message_stop"})

        self.assertEqual(output.getvalue(), "\npartial\n\nModel response retry 2:\n\ncomplete\n")
        self.assertTrue(renderer.matches_final_message("complete"))

    def test_finish_closes_interrupted_text_line(self) -> None:
        output = io.StringIO()
        renderer = TerminalModelStreamRenderer(output)
        renderer.chat_event(
            1,
            {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "partial"}},
        )

        renderer.finish()
        renderer.finish()

        self.assertEqual(output.getvalue(), "\npartial\n")

    def test_separates_same_attempt_provider_fallback_restart(self) -> None:
        output = io.StringIO()
        renderer = TerminalModelStreamRenderer(output)
        renderer.chat_event(1, {"type": "message_start"})
        renderer.chat_event(
            1,
            {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "primary partial"}},
        )
        renderer.chat_event(1, {"type": "message_start"})
        renderer.chat_event(
            1,
            {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "fallback complete"}},
        )
        renderer.chat_event(1, {"type": "message_stop"})

        self.assertEqual(
            output.getvalue(),
            "\nprimary partial\n\nModel response restarted:\n\nfallback complete\n",
        )
        self.assertTrue(renderer.matches_final_message("fallback complete"))

    def test_coordinates_surrounding_terminal_display_once(self) -> None:
        output = io.StringIO()
        lifecycle = []
        renderer = TerminalModelStreamRenderer(
            output,
            on_display_start=lambda: lifecycle.append("pause"),
            on_display_end=lambda: lifecycle.append("resume"),
        )

        renderer.chat_event(1, {"type": "message_start"})
        for text in ("one", " two"):
            renderer.chat_event(
                1,
                {"type": "content_block_delta", "delta": {"type": "text_delta", "text": text}},
            )
        renderer.chat_event(1, {"type": "message_stop"})
        renderer.finish()

        self.assertEqual(lifecycle, ["pause", "resume"])
        self.assertEqual(output.getvalue(), "\none two\n")


if __name__ == "__main__":
    unittest.main()
