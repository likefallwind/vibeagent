import unittest

from vibeagent.terminal_text import (
    normalized_shell_permission_subject,
    terminal_safe_text,
)


class TerminalTextTests(unittest.TestCase):
    def test_plain_unicode_text_is_unchanged(self) -> None:
        self.assertEqual(terminal_safe_text("pytest 测试"), "pytest 测试")

    def test_control_and_format_characters_are_explicit(self) -> None:
        value = "git\tpush\\literal\x1b[2K\u200b"

        self.assertEqual(
            terminal_safe_text(value),
            r"[escaped] git\tpush\\literal\x1b[2K\u200b",
        )

    def test_shell_permission_normalization_collapses_ascii_whitespace(self) -> None:
        self.assertEqual(
            normalized_shell_permission_subject(" \tgit\t push\norigin  main\r"),
            "git push origin main",
        )


if __name__ == "__main__":
    unittest.main()
