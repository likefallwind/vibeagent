import unittest

from vibeagent.provider_tool_calls import parse_function_tool_call, parse_responses_function_call


class ProviderToolCallTests(unittest.TestCase):
    def test_parse_function_tool_call_decodes_json_arguments(self) -> None:
        self.assertEqual(
            parse_function_tool_call(
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "read_file", "arguments": '{"path":"app.py"}'},
                }
            ),
            {"type": "tool_call", "id": "call_1", "name": "read_file", "input": {"path": "app.py"}},
        )

    def test_parse_function_tool_call_preserves_malformed_arguments(self) -> None:
        self.assertEqual(
            parse_function_tool_call(
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "read_file", "arguments": "not json"},
                }
            ),
            {"type": "tool_call", "id": "call_1", "name": "read_file", "input": "not json"},
        )

    def test_parse_function_tool_call_rejects_invalid_shape(self) -> None:
        self.assertIsNone(parse_function_tool_call({"id": "call_1"}))
        self.assertIsNone(parse_function_tool_call({"function": {"name": "read_file"}}))

    def test_parse_responses_function_call_decodes_arguments(self) -> None:
        self.assertEqual(
            parse_responses_function_call(
                {
                    "type": "function_call",
                    "call_id": "call_1",
                    "name": "read_file",
                    "arguments": '{"path":"app.py"}',
                }
            ),
            {"type": "tool_call", "id": "call_1", "name": "read_file", "input": {"path": "app.py"}},
        )

    def test_parse_responses_function_call_rejects_invalid_shape(self) -> None:
        self.assertIsNone(parse_responses_function_call({"type": "message"}))
        self.assertIsNone(parse_responses_function_call({"type": "function_call", "name": "read_file"}))


if __name__ == "__main__":
    unittest.main()
