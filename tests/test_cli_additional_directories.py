import tempfile
import unittest
from pathlib import Path

from vibeagent.cli_additional_directories import MAX_ADDITIONAL_DIRECTORIES, resolve_additional_directories


class CliAdditionalDirectoriesTests(unittest.TestCase):
    def test_resolves_relative_and_absolute_directories_from_invocation_root(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-add-dir-") as base:
            root = Path(base)
            first = root / "first"
            second = root / "second"
            first.mkdir()
            second.mkdir()

            resolved = resolve_additional_directories(
                ["first", str(second), "first"],
                invocation_root=root,
            )

        self.assertEqual(resolved, (first.resolve(), second.resolve()))

    def test_rejects_missing_files_empty_paths_and_excess_directories(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-add-dir-") as base:
            root = Path(base)
            file_path = root / "file.txt"
            file_path.write_text("x", encoding="utf-8")
            cases = [
                (["missing"], "Cannot resolve"),
                ([str(file_path)], "must reference a directory"),
                ([" "], "cannot be empty"),
                ([str(root)] * (MAX_ADDITIONAL_DIRECTORIES + 1), "at most"),
            ]

            for values, message in cases:
                with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                    resolve_additional_directories(values, invocation_root=root)


if __name__ == "__main__":
    unittest.main()
