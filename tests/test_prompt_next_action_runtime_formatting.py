import unittest

from vibeagent.prompt_next_action_runtime_formatting import (
    command_result_output_issue_labels,
    inline_output_issue_instruction,
    inline_output_issue_labels,
)
from vibeagent.types import CommandResult, OutputContextResult, OutputDiagnostic


class PromptNextActionRuntimeFormattingTests(unittest.TestCase):
    def test_inline_output_issue_labels_prefers_sourced_diagnostics(self) -> None:
        result = CommandResult(
            command="python -m unittest",
            exit_code=1,
            stdout="",
            stderr="",
            timed_out=False,
            signal=None,
            output_diagnostics=[
                OutputDiagnostic(severity="failure", output_line=1, text="text only"),
                OutputDiagnostic(
                    severity="failure",
                    output_line=2,
                    text="assertion failed",
                    path="tests/test_agent.py",
                    line=42,
                    column=None,
                ),
            ],
            output_contexts=[
                OutputContextResult(
                    path="tests/test_agent.py",
                    line=99,
                    column=1,
                    raw="tests/test_agent.py:99:1",
                    ok=True,
                    content="99: other()\n",
                    message="Read tests/test_agent.py:99.",
                )
            ],
        )

        labels = inline_output_issue_labels(result)

        self.assertEqual(labels, ["tests/test_agent.py:42 failure: assertion failed"])

    def test_inline_output_issue_labels_falls_back_to_contexts(self) -> None:
        result = CommandResult(
            command="python -m unittest",
            exit_code=1,
            stdout="",
            stderr="",
            timed_out=False,
            signal=None,
            output_diagnostics=[
                OutputDiagnostic(severity="failure", output_line=1, text="text only"),
            ],
            output_contexts=[
                OutputContextResult(
                    path="tests/test_agent.py",
                    line=42,
                    column=8,
                    raw="tests/test_agent.py:42:8",
                    ok=True,
                    content="42: self.assertTrue(False)\n",
                    message="Read tests/test_agent.py:42.",
                )
            ],
        )

        labels = inline_output_issue_labels(result)

        self.assertEqual(labels, ["tests/test_agent.py:42:8"])

    def test_command_result_output_issue_labels_filters_to_failed_results(self) -> None:
        failed = CommandResult(
            command="python -m unittest",
            exit_code=1,
            stdout="",
            stderr="",
            timed_out=False,
            signal=None,
            output_diagnostics=[
                OutputDiagnostic(
                    severity="failure",
                    output_line=1,
                    text="assertion failed",
                    path="tests/test_agent.py",
                    line=42,
                    column=None,
                )
            ],
        )
        passed = CommandResult(
            command="python -m ruff check",
            exit_code=0,
            stdout="",
            stderr="",
            timed_out=False,
            signal=None,
            output_diagnostics=[
                OutputDiagnostic(
                    severity="warning",
                    output_line=1,
                    text="deprecated helper",
                    path="vibeagent/agent.py",
                    line=9,
                    column=None,
                )
            ],
        )

        labels = command_result_output_issue_labels([failed, passed], failed_only=True)

        self.assertEqual(labels, ["tests/test_agent.py:42 failure: assertion failed"])

    def test_command_result_output_issue_labels_includes_successes_and_dedupes(self) -> None:
        first = CommandResult(
            command="python -m unittest",
            exit_code=0,
            stdout="",
            stderr="",
            timed_out=False,
            signal=None,
            output_contexts=[
                OutputContextResult(
                    path="tests/test_agent.py",
                    line=42,
                    column=None,
                    raw="tests/test_agent.py:42",
                    ok=True,
                    content="42: self.assertTrue(False)\n",
                    message="Read tests/test_agent.py:42.",
                )
            ],
        )
        second = CommandResult(
            command="python -m ruff check",
            exit_code=0,
            stdout="",
            stderr="",
            timed_out=False,
            signal=None,
            output_contexts=[
                OutputContextResult(
                    path="tests/test_agent.py",
                    line=42,
                    column=None,
                    raw="tests/test_agent.py:42",
                    ok=True,
                    content="42: self.assertTrue(False)\n",
                    message="Read tests/test_agent.py:42.",
                )
            ],
        )

        labels = command_result_output_issue_labels([first, second], failed_only=False)

        self.assertEqual(labels, ["tests/test_agent.py:42"])

    def test_inline_output_issue_instruction_formats_limited_issue_list(self) -> None:
        instruction = inline_output_issue_instruction(
            "Base.",
            "Intro.",
            ["one", "two", "three", "four"],
            "fix and rerun.",
        )

        self.assertIn("Base. Intro.", instruction)
        self.assertIn("Inline output analysis identified referenced source location", instruction)
        self.assertIn("one; two; three; +1 more", instruction)
        self.assertIn("Inspect or edit the referenced source, fix and rerun.", instruction)


if __name__ == "__main__":
    unittest.main()
