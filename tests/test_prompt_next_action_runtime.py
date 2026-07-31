import unittest
from types import SimpleNamespace

from vibeagent.prompt_next_action_runtime import runtime_next_action_instruction


class PromptNextActionRuntimeTests(unittest.TestCase):
    def test_running_process_guides_checked_stdin_files(self) -> None:
        instruction = runtime_next_action_instruction(
            "Next.",
            [SimpleNamespace(kind="read_process", ok=True, running=True)],
        )

        self.assertIsNotNone(instruction)
        self.assertIn("check_write_process then write_process", instruction or "")
        self.assertIn("prefer stdin_file", instruction or "")

    def test_check_write_process_guides_stdin_files(self) -> None:
        instruction = runtime_next_action_instruction(
            "Next.",
            [SimpleNamespace(kind="check_write_process", ok=True)],
        )

        self.assertIsNotNone(instruction)
        self.assertIn("The process can receive stdin", instruction or "")
        self.assertIn("use stdin_file instead of inline content", instruction or "")


if __name__ == "__main__":
    unittest.main()
