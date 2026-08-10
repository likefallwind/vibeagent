import os
import tempfile
import unittest
from pathlib import Path

from vibeagent.cli_system_prompt_files import (
    MAX_SYSTEM_PROMPT_FILE_BYTES,
    read_system_prompt_file,
    resolve_system_prompt_inputs,
)


class CliSystemPromptFileTests(unittest.TestCase):
    def test_resolve_reads_relative_replacement_and_combines_append_sources(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-prompt-") as base:
            root = Path(base)
            (root / "system.txt").write_text("  Replacement prompt.\n", encoding="utf-8")
            (root / "append.txt").write_text("Append from file.\n", encoding="utf-8")

            system_prompt, append_system_prompt = resolve_system_prompt_inputs(
                system_prompt=None,
                system_prompt_file="system.txt",
                append_system_prompt="Append inline.",
                append_system_prompt_file="append.txt",
                invocation_root=root,
            )

        self.assertEqual(system_prompt, "Replacement prompt.")
        self.assertEqual(append_system_prompt, "Append inline.\n\nAppend from file.")

    def test_read_accepts_an_absolute_regular_file(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-prompt-") as base:
            path = Path(base) / "prompt.txt"
            path.write_text("Use focused checks.", encoding="utf-8")

            content = read_system_prompt_file(
                str(path),
                invocation_root=Path("/unused"),
                option="--system-prompt-file",
            )

        self.assertEqual(content, "Use focused checks.")

    def test_read_rejects_missing_directory_empty_invalid_utf8_and_oversized_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-prompt-") as base:
            root = Path(base)
            (root / "empty.txt").write_text(" \n", encoding="utf-8")
            (root / "invalid.txt").write_bytes(b"\xff")
            (root / "large.txt").write_bytes(b"x" * (MAX_SYSTEM_PROMPT_FILE_BYTES + 1))
            cases = [
                ("missing.txt", "Cannot read"),
                (".", "regular file"),
                ("empty.txt", "cannot be empty"),
                ("invalid.txt", "valid UTF-8"),
                ("large.txt", "exceeds"),
            ]

            for path_value, message in cases:
                with self.subTest(path_value=path_value), self.assertRaisesRegex(ValueError, message):
                    read_system_prompt_file(
                        path_value,
                        invocation_root=root,
                        option="--system-prompt-file",
                    )

    @unittest.skipUnless(hasattr(os, "symlink"), "symbolic links are unavailable")
    def test_read_rejects_final_and_parent_symbolic_links(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-prompt-") as base:
            root = Path(base)
            real_dir = root / "real"
            real_dir.mkdir()
            (real_dir / "prompt.txt").write_text("Prompt.", encoding="utf-8")
            (root / "prompt-link.txt").symlink_to(real_dir / "prompt.txt")
            (root / "dir-link").symlink_to(real_dir, target_is_directory=True)

            for path_value in ("prompt-link.txt", "dir-link/prompt.txt"):
                with self.subTest(path_value=path_value), self.assertRaisesRegex(ValueError, "symbolic links"):
                    read_system_prompt_file(
                        path_value,
                        invocation_root=root,
                        option="--system-prompt-file",
                    )


if __name__ == "__main__":
    unittest.main()
