import base64
import copy
import json
import tempfile
import unittest
from pathlib import Path

from vibeagent.actions import execute_action, parse_tool_action
from vibeagent.agent import run_agent
from vibeagent.minimax import message_to_minimax
from vibeagent.openai_compat import flatten_messages
from vibeagent.types import AssistantResponse, ChatMessage, ContentBlock, ViewImageAction
from vibeagent.workspace import create_run_workspace


PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


class _VisionClient:
    def __init__(self) -> None:
        self.messages: list[list[ChatMessage]] = []

    def complete(self, messages, tools=None, max_tokens=4096, temperature=0.2, timeout_ms=120_000):
        self.messages.append(copy.deepcopy(messages))
        call = len(self.messages)
        if call == 1:
            content = [{"type": "tool_call", "id": "image-1", "name": "view_image", "input": {"path": "pixel.png"}}]
        elif call == 2:
            content = [{"type": "tool_call", "id": "info-1", "name": "file_info", "input": {"paths": ["pixel.png"]}}]
        else:
            content = [{"type": "text", "text": "Image inspected."}]
        return AssistantResponse(content=content, raw={"content": content})


def _image_tool_message() -> ChatMessage:
    return ChatMessage(
        role="user",
        content=[
            {
                "type": "tool_result",
                "tool_call_id": "image-1",
                "content": [
                    {"type": "text", "text": '{"kind":"view_image","ok":true}'},
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": "image/png", "data": "YWJj"},
                    },
                ],
            }
        ],
    )


class MultimodalProviderTests(unittest.TestCase):
    def test_minimax_preserves_anthropic_image_tool_result(self) -> None:
        converted = message_to_minimax(_image_tool_message())

        self.assertEqual(converted["content"][0]["type"], "tool_result")
        nested = converted["content"][0]["content"]
        self.assertEqual(nested[1]["type"], "image")
        self.assertEqual(nested[1]["source"]["media_type"], "image/png")

    def test_openai_moves_tool_image_to_data_url_user_message(self) -> None:
        converted = flatten_messages([_image_tool_message()])

        self.assertEqual(converted[0]["role"], "tool")
        self.assertIn("view_image", converted[0]["content"])
        self.assertEqual(converted[1]["role"], "user")
        image = converted[1]["content"][1]
        self.assertEqual(image["type"], "image_url")
        self.assertEqual(image["image_url"]["url"], "data:image/png;base64,YWJj")


class ViewImageTests(unittest.TestCase):
    def test_view_image_observation_contains_metadata_not_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-image-") as base:
            root = Path(base)
            (root / "pixel.png").write_bytes(PNG_1X1)
            workspace = create_run_workspace(root, "run-1")

            observation = execute_action(workspace, ViewImageAction(type="view_image", path="pixel.png"))
            too_small = execute_action(
                workspace,
                ViewImageAction(type="view_image", path="pixel.png", max_bytes=10),
            )

        self.assertTrue(observation.ok)
        self.assertEqual((observation.width, observation.height), (1, 1))
        self.assertEqual(observation.mime_type, "image/png")
        self.assertFalse(hasattr(observation, "data"))
        self.assertFalse(too_small.ok)
        self.assertIn("exceeds max_bytes", too_small.message)

    def test_view_image_action_parses_bounded_input(self) -> None:
        action = parse_tool_action("view_image", {"path": "mockup.webp", "max_bytes": 1234})

        self.assertEqual(action.path, "mockup.webp")
        self.assertEqual(action.max_bytes, 1234)

    def test_agent_sends_image_once_then_removes_base64_from_history_and_session(self) -> None:
        client = _VisionClient()
        with tempfile.TemporaryDirectory(prefix="vibeagent-image-") as base:
            root = Path(base)
            (root / "pixel.png").write_bytes(PNG_1X1)

            result = run_agent("Inspect pixel.png", base_dir=root, client=client, max_iterations=3)
            events = (root / ".vibeagent" / "sessions" / result.run_id / "events.jsonl").read_text(encoding="utf-8")

        second_messages = json.dumps(
            [{"role": message.role, "content": message.content} for message in client.messages[1]],
            ensure_ascii=False,
        )
        third_messages = json.dumps(
            [{"role": message.role, "content": message.content} for message in client.messages[2]],
            ensure_ascii=False,
        )
        encoded = base64.b64encode(PNG_1X1).decode("ascii")
        self.assertTrue(result.success)
        self.assertIn(encoded, second_messages)
        self.assertNotIn(encoded, third_messages)
        self.assertIn("image payload consumed by model", third_messages)
        self.assertNotIn(encoded, events)
        self.assertNotIn('"data":', events)


if __name__ == "__main__":
    unittest.main()
