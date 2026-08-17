from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from vibeagent.workspace import create_run_workspace, read_git_diff_hunks
from vibeagent.workspace_git_diff_parser import StreamingGitDiffHunkParser


class GitDiffStreamingTests(unittest.TestCase):
    def test_parser_counts_discarded_hunks_across_chunk_boundaries(self) -> None:
        parser = StreamingGitDiffHunkParser(max_hunks=1, max_lines_per_hunk=2)
        diff = "".join(
            f"diff --git a/file{index}.py b/file{index}.py\n"
            "@@ -1 +1 @@\n"
            "-old\n"
            "+new\n"
            for index in range(3)
        )
        for offset in range(0, len(diff), 7):
            parser.append(diff[offset : offset + 7])

        result = parser.finish()

        self.assertEqual(result["total_hunks"], 3)
        self.assertEqual(len(result["hunks"]), 1)
        self.assertEqual(result["hunks"][0]["file"], "file0.py")
        self.assertEqual(result["hunks"][0]["added"], 1)
        self.assertEqual(result["hunks"][0]["deleted"], 1)
        self.assertTrue(result["truncated"])

    def test_parser_bounds_single_lines_and_aggregate_retained_text(self) -> None:
        parser = StreamingGitDiffHunkParser(
            max_hunks=2,
            max_lines_per_hunk=3,
            max_line_chars=20,
            max_retained_chars=25,
        )
        parser.append(
            "diff --git a/a.py b/a.py\n"
            "@@ -1 +1 @@\n"
            f"+{'a' * 100}\n"
            "diff --git a/b.py b/b.py\n"
            "@@ -1 +1 @@\n"
            f"+{'b' * 100}\n"
        )

        result = parser.finish()
        hunks = result["hunks"]

        self.assertEqual(result["total_hunks"], 2)
        self.assertEqual(sum(len(line) for hunk in hunks for line in hunk["lines"]), 25)
        self.assertEqual(len(hunks[0]["lines"][0]), 20)
        self.assertEqual(len(hunks[1]["lines"][0]), 5)
        self.assertTrue(hunks[0]["lines_truncated"])
        self.assertTrue(hunks[1]["lines_truncated"])
        self.assertTrue(result["truncated"])

    def test_parser_reports_truncated_structural_lines(self) -> None:
        parser = StreamingGitDiffHunkParser(
            max_hunks=1,
            max_lines_per_hunk=1,
            max_parse_line_chars=24,
        )
        parser.append(
            "diff --git a/very-long-file-name.py b/very-long-file-name.py\n"
            "@@ -1 +1 @@\n"
            "+new\n"
        )

        result = parser.finish()

        self.assertEqual(result["total_hunks"], 1)
        self.assertTrue(result["truncated"])

    def test_workspace_reader_streams_many_hunks_and_one_oversized_line(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-git-hunks-") as base:
            root = Path(base)
            fake_git = self._write_fake_git(
                root,
                "import sys\n"
                "if sys.argv[1] == 'diff':\n"
                "    print('diff --git a/large.py b/large.py')\n"
                "    print('@@ -1 +1 @@')\n"
                "    print('+' + ('x' * 2_000_000))\n"
                "    for index in range(10_000):\n"
                "        print(f'diff --git a/file{index}.py b/file{index}.py')\n"
                "        print('@@ -1 +1 @@')\n"
                "        print('-old')\n"
                "        print('+new')\n",
            )
            workspace = create_run_workspace(root, "test-run")
            environment = {"PATH": f"{fake_git.parent}{os.pathsep}{os.environ.get('PATH', '')}"}

            with patch.dict(os.environ, environment):
                summary = read_git_diff_hunks(workspace, max_hunks=3, max_lines_per_hunk=2)

        self.assertTrue(summary["ok"])
        self.assertEqual(summary["total_hunks"], 10_001)
        self.assertEqual(len(summary["hunks"]), 3)
        self.assertEqual(len(summary["hunks"][0]["lines"][0]), 4_000)
        self.assertTrue(summary["hunks"][0]["lines_truncated"])
        self.assertTrue(summary["truncated"])

    def test_workspace_reader_preserves_git_errors_and_discards_timed_out_partial_data(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-git-hunk-errors-") as base:
            root = Path(base)
            fake_git = self._write_fake_git(
                root,
                "import sys\n"
                "print('diff --git a/app.py b/app.py')\n"
                "print('@@ -1 +1 @@')\n"
                "print('+partial')\n"
                "print('git failed', file=sys.stderr)\n"
                "raise SystemExit(2)\n",
            )
            workspace = create_run_workspace(root, "test-run")
            environment = {"PATH": f"{fake_git.parent}{os.pathsep}{os.environ.get('PATH', '')}"}
            with patch.dict(os.environ, environment):
                failed = read_git_diff_hunks(workspace)

            fake_git.write_text(
                "#!/usr/bin/env python3\n"
                "import time\n"
                "print('diff --git a/app.py b/app.py', flush=True)\n"
                "print('@@ -1 +1 @@', flush=True)\n"
                "print('+partial', flush=True)\n"
                "time.sleep(30)\n",
                encoding="utf-8",
            )
            with (
                patch.dict(os.environ, environment),
                patch("vibeagent.workspace_git_utils.READONLY_GIT_TIMEOUT_MS", 50),
            ):
                timed_out = read_git_diff_hunks(workspace)

        self.assertFalse(failed["ok"])
        self.assertEqual(failed["total_hunks"], 1)
        self.assertEqual(failed["message"], "git failed\n")
        self.assertFalse(timed_out["ok"])
        self.assertEqual(timed_out["hunks"], [])
        self.assertEqual(timed_out["total_hunks"], 0)
        self.assertEqual(timed_out["message"], "git command timed out.")

    @staticmethod
    def _write_fake_git(root: Path, source: str) -> Path:
        bin_dir = root / "bin"
        bin_dir.mkdir()
        fake_git = bin_dir / "git"
        fake_git.write_text(f"#!/usr/bin/env python3\n{source}", encoding="utf-8")
        fake_git.chmod(0o755)
        return fake_git


if __name__ == "__main__":
    unittest.main()
