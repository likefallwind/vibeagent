from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from vibeagent.cli_interactive_cd import resolve_interactive_directory_change


class InteractiveDirectoryChangeTests(unittest.TestCase):
    def test_requires_exactly_one_path(self) -> None:
        root = Path.cwd()

        self.assertEqual(resolve_interactive_directory_change(root, None).text, "Usage: /cd <path>")
        self.assertEqual(resolve_interactive_directory_change(root, "one two").text, "Usage: /cd <path>")

    def test_resolves_quoted_relative_path(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cd-") as base:
            root = Path(base) / "project"
            target = Path(base) / "other project"
            root.mkdir()
            target.mkdir()

            result = resolve_interactive_directory_change(root, '"../other project"')

        self.assertTrue(result.changed)
        self.assertEqual(result.target, target.resolve())

    def test_rejects_missing_path_and_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cd-") as base:
            root = Path(base)
            file_path = root / "file.txt"
            file_path.write_text("content", encoding="utf-8")

            missing = resolve_interactive_directory_change(root, "missing")
            file_result = resolve_interactive_directory_change(root, "file.txt")

        self.assertFalse(missing.changed)
        self.assertIn("Cannot change directory", missing.text)
        self.assertFalse(file_result.changed)
        self.assertIn("not a directory", file_result.text)

    def test_same_directory_is_a_no_op(self) -> None:
        root = Path.cwd().resolve()

        result = resolve_interactive_directory_change(root, ".")

        self.assertFalse(result.changed)
        self.assertEqual(result.target, root)
        self.assertIn("Already using", result.text)

    def test_reports_malformed_quotes(self) -> None:
        result = resolve_interactive_directory_change(Path.cwd(), '"unfinished')

        self.assertFalse(result.changed)
        self.assertIn("Invalid /cd path", result.text)


if __name__ == "__main__":
    unittest.main()
