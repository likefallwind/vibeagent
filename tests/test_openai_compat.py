import unittest

from vibeagent.openai_compat import build_request_body, extract_content, extract_usage, get_openai_compatible_defaults
from vibeagent.types import ChatMessage


class OpenAICompatibleTests(unittest.TestCase):
    def test_defaults_target_deepseek_unless_overridden(self) -> None:
        self.assertEqual(get_openai_compatible_defaults({})["base_url"], "https://api.deepseek.com")
        self.assertEqual(get_openai_compatible_defaults({})["model"], "deepseek-chat")

    def test_build_request_body_maps_generic_tools_to_openai_shape(self) -> None:
        body = build_request_body(
            "deepseek-chat",
            [
                ChatMessage(role="system", content="You are concise."),
                ChatMessage(role="user", content="Hi"),
                ChatMessage(
                    role="assistant",
                    content=[{"type": "tool_call", "id": "call_1", "name": "finish", "input": {"message": "done"}}],
                ),
                ChatMessage(
                    role="user",
                    content=[{"type": "tool_result", "tool_call_id": "call_1", "content": '{"kind":"finish"}'}],
                ),
            ],
            tools=[{"name": "finish", "description": "Finish", "input_schema": {"type": "object"}}],
        )

        self.assertEqual(body["messages"][0], {"role": "system", "content": "You are concise."})
        self.assertEqual(body["messages"][1], {"role": "user", "content": "Hi"})
        self.assertEqual(body["messages"][2]["role"], "assistant")
        self.assertEqual(body["messages"][2]["tool_calls"][0]["function"]["name"], "finish")
        self.assertEqual(body["messages"][3], {"role": "tool", "tool_call_id": "call_1", "content": '{"kind":"finish"}'})
        self.assertEqual(body["tools"][0]["type"], "function")
        self.assertEqual(body["tool_choice"], "auto")

    def test_extract_content_maps_openai_tool_calls_to_generic_tool_calls(self) -> None:
        self.assertEqual(
            extract_content(
                {
                    "choices": [
                        {
                            "message": {
                                "content": "thinking",
                                "tool_calls": [
                                    {
                                        "id": "call_1",
                                        "type": "function",
                                        "function": {"name": "read_file", "arguments": '{"path":"app.py"}'},
                                    }
                                ],
                            }
                        }
                    ]
                }
            ),
            [
                {"type": "text", "text": "thinking"},
                {"type": "tool_call", "id": "call_1", "name": "read_file", "input": {"path": "app.py"}},
            ],
        )

    def test_extract_content_preserves_malformed_arguments_for_validation(self) -> None:
        self.assertEqual(
            extract_content(
                {
                    "choices": [
                        {
                            "message": {
                                "tool_calls": [
                                    {
                                        "id": "call_1",
                                        "type": "function",
                                        "function": {"name": "read_file", "arguments": "not json"},
                                    }
                                ]
                            }
                        }
                    ]
                }
            ),
            [{"type": "tool_call", "id": "call_1", "name": "read_file", "input": "not json"}],
        )

    def test_extract_usage_reads_openai_token_usage(self) -> None:
        usage = extract_usage(
            {
                "usage": {
                    "prompt_tokens": 13,
                    "completion_tokens": 8,
                    "total_tokens": 21,
                }
            }
        )

        self.assertIsNotNone(usage)
        self.assertEqual(usage.input_tokens, 13)
        self.assertEqual(usage.output_tokens, 8)
        self.assertEqual(usage.total_tokens, 21)


if __name__ == "__main__":
    unittest.main()
