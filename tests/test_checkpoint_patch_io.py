from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vibeagent.checkpoint_patch_io import (
    capture_git_stdout_file,
    checkpoint_patch_files_equal,
    read_checkpoint_patch_excerpt,
)


class CheckpointPatchIoTests(unittest.TestCase):
    def test_large_output_is_streamed_to_disk_exactly(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-checkpoint-patch-") as base:
            root = Path(base)
            destination = root / "saved.patch"
            chunk_chars = 1024 * 1024
            chunks = 64
            script = (
                "import os\n"
                f"chunk = b'x' * {chunk_chars}\n"
                f"for _ in range({chunks}): os.write(1, chunk)\n"
                "os.write(1, b'END\\n')\n"
            )

            result = capture_git_stdout_file(root, [sys.executable, "-c", script], destination)

            self.assertTrue(result.ok, result.stderr)
            self.assertEqual(result.chars, chunk_chars * chunks + 4)
            self.assertEqual(destination.stat().st_size, chunk_chars * chunks + 4)
            with destination.open("rb") as handle:
                handle.seek(-4, 2)
                self.assertEqual(handle.read(), b"END\n")

    def test_output_over_disk_limit_fails_without_partial_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-checkpoint-limit-") as base:
            root = Path(base)
            destination = root / "saved.patch"
            script = "import os\nfor _ in range(32): os.write(1, b'x' * 1048576)\n"

            with patch("vibeagent.checkpoint_patch_io.MAX_CHECKPOINT_PATCH_BYTES", 4 * 1024 * 1024):
                result = capture_git_stdout_file(root, [sys.executable, "-c", script], destination)

            self.assertFalse(result.ok)
            self.assertIn("exceeded", result.stderr)
            self.assertFalse(destination.exists())
            self.assertEqual(list(root.glob(".saved.patch.*")), [])
            self.assertEqual(list(root.glob(".git-stderr.*")), [])

    def test_excerpt_and_file_comparison_do_not_require_full_patch_text(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-checkpoint-compare-") as base:
            root = Path(base)
            first = root / "first.patch"
            second = root / "second.patch"
            different = root / "different.patch"
            content = ("header\n" + "z" * (3 * 1024 * 1024) + "\ntail\n").encode()
            first.write_bytes(content)
            second.write_bytes(content)
            different.write_bytes(content[:-2] + b"XX")

            shown, total, truncated = read_checkpoint_patch_excerpt(first, 100)

            self.assertEqual(shown, content.decode()[:100])
            self.assertEqual(total, len(content.decode()))
            self.assertTrue(truncated)
            self.assertTrue(checkpoint_patch_files_equal(first, second))
            self.assertFalse(checkpoint_patch_files_equal(first, different))

    def test_missing_or_unsafe_saved_patch_compares_as_empty_for_status_only(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-checkpoint-empty-") as base:
            root = Path(base)
            empty = root / "empty.patch"
            nonempty = root / "nonempty.patch"
            empty.write_bytes(b"")
            nonempty.write_bytes(b"diff")

            self.assertTrue(checkpoint_patch_files_equal(empty, None))
            self.assertTrue(checkpoint_patch_files_equal(None, empty))
            self.assertFalse(checkpoint_patch_files_equal(nonempty, None))
            self.assertFalse(checkpoint_patch_files_equal(None, nonempty))


if __name__ == "__main__":
    unittest.main()
