from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from vibeagent.workspace_git_utils import (
    MAX_GIT_MUTATION_OUTPUT_CHARS,
    run_git_mutation,
)


class GitMutationOutputBoundsTests(unittest.TestCase):
    def test_large_failed_mutation_retains_bounded_output_and_totals(self) -> None:
        stdout_chars = 128 * 1024 * 1024
        stderr_chars = 128 * 1024 * 1024
        with tempfile.TemporaryDirectory(prefix="vibeagent-git-mutation-") as base:
            root = Path(base)
            self._write_fake_git(
                root,
                "import os, sys\n"
                "chunk = bytes([120]) * 65536\n"
                "for _ in range(2048):\n"
                "    os.write(1, chunk)\n"
                "for _ in range(2048):\n"
                "    os.write(2, chunk)\n"
                "os.write(2, b'failure-tail\\n')\n"
                "sys.exit(7)\n",
            )
            with patch.dict(os.environ, {"PATH": self._path_with_fake_git(root)}):
                result = run_git_mutation(root, ["commit"])

        self.assertFalse(result.ok)
        self.assertEqual(result.exit_code, 7)
        self.assertEqual(len(result.stdout), MAX_GIT_MUTATION_OUTPUT_CHARS)
        self.assertTrue(result.stdout_truncated)
        self.assertEqual(result.stdout_total_chars, stdout_chars)
        self.assertEqual(len(result.stderr), MAX_GIT_MUTATION_OUTPUT_CHARS)
        self.assertIn("failure-tail", result.stderr)
        self.assertTrue(result.stderr_truncated)
        self.assertEqual(result.stderr_total_chars, stderr_chars + len("failure-tail\n"))

    def test_timeout_preserves_existing_failure_contract(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-git-mutation-") as base:
            root = Path(base)
            self._write_fake_git(root, "import time\ntime.sleep(30)\n")
            started = time.monotonic()
            with (
                patch.dict(os.environ, {"PATH": self._path_with_fake_git(root)}),
                patch("vibeagent.workspace_git_utils.GIT_MUTATION_TIMEOUT_MS", 50),
            ):
                result = run_git_mutation(root, ["fetch"])
            duration = time.monotonic() - started

        self.assertFalse(result.ok)
        self.assertIsNone(result.exit_code)
        self.assertEqual(result.stderr, "git command timed out.")
        self.assertLess(duration, 3)

    @staticmethod
    def _write_fake_git(root: Path, body: str) -> None:
        executable = root / "git"
        executable.write_text(f"#!{sys.executable}\n{body}", encoding="utf-8")
        executable.chmod(0o755)

    @staticmethod
    def _path_with_fake_git(root: Path) -> str:
        return f"{root}{os.pathsep}{os.environ.get('PATH', '')}"


if __name__ == "__main__":
    unittest.main()
