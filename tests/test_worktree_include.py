from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vibeagent.worktree_include import copy_worktree_includes


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout.strip()


def _repository(root: Path) -> None:
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "VibeAgent Test")
    _git(root, "config", "user.email", "vibeagent@example.test")
    root.joinpath("tracked.txt").write_text("tracked\n", encoding="utf-8")
    root.joinpath("ordinary.txt").write_text("ordinary\n", encoding="utf-8")
    root.joinpath(".gitignore").write_text(
        ".env\nignored/\n*.log\n.vibeagent/\n",
        encoding="utf-8",
    )
    root.joinpath(".worktreeinclude").write_text(
        ".env\nignored/*.txt\n!ignored/skip.txt\ntracked.txt\nordinary.txt\n",
        encoding="utf-8",
    )
    _git(root, "add", ".gitignore", ".worktreeinclude", "tracked.txt", "ordinary.txt")
    _git(root, "commit", "-qm", "initial")


def _target_worktree(root: Path) -> Path:
    target = root / ".vibeagent" / "worktrees" / "copy-test"
    target.parent.mkdir(parents=True, exist_ok=True)
    _git(root, "worktree", "add", "--quiet", "-b", "copy-test", str(target), "HEAD")
    return target


class WorktreeIncludeTests(unittest.TestCase):
    def test_copies_only_gitignored_untracked_files_matching_include_rules(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-worktree-include-") as base:
            root = Path(base)
            _repository(root)
            root.joinpath(".env").write_text("TOKEN=local\n", encoding="utf-8")
            root.joinpath("ignored").mkdir()
            root.joinpath("ignored", "keep.txt").write_text("keep\n", encoding="utf-8")
            root.joinpath("ignored", "skip.txt").write_text("skip\n", encoding="utf-8")
            root.joinpath("debug.log").write_text("log\n", encoding="utf-8")
            target = _target_worktree(root)

            report = copy_worktree_includes(root, target)

            self.assertEqual(target.joinpath(".env").read_text(encoding="utf-8"), "TOKEN=local\n")
            self.assertEqual(target.joinpath("ignored", "keep.txt").read_text(encoding="utf-8"), "keep\n")
            self.assertFalse(target.joinpath("ignored", "skip.txt").exists())
            self.assertFalse(target.joinpath("debug.log").exists())
            self.assertEqual(report.copied_paths, (".env", "ignored/keep.txt"))
            self.assertEqual(report.copied_bytes, len("TOKEN=local\n") + len("keep\n"))

    def test_rejects_symlink_source_without_copying_any_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-worktree-include-") as base:
            root = Path(base)
            _repository(root)
            root.joinpath("real.env").write_text("secret\n", encoding="utf-8")
            root.joinpath(".env").symlink_to("real.env")
            target = _target_worktree(root)

            with self.assertRaisesRegex(ValueError, "symbolic link"):
                copy_worktree_includes(root, target)

            self.assertFalse(target.joinpath(".env").exists())

    def test_file_count_limit_is_checked_before_copying(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-worktree-include-") as base:
            root = Path(base)
            _repository(root)
            root.joinpath(".env").write_text("one\n", encoding="utf-8")
            root.joinpath("ignored").mkdir()
            root.joinpath("ignored", "keep.txt").write_text("two\n", encoding="utf-8")
            target = _target_worktree(root)

            with patch("vibeagent.worktree_include.MAX_WORKTREE_INCLUDE_FILES", 1):
                with self.assertRaisesRegex(ValueError, "limit is 1"):
                    copy_worktree_includes(root, target)

            self.assertFalse(target.joinpath(".env").exists())
            self.assertFalse(target.joinpath("ignored", "keep.txt").exists())

    def test_broad_pattern_never_copies_agent_runtime_or_worktree_storage(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-worktree-include-") as base:
            root = Path(base)
            _repository(root)
            root.joinpath(".worktreeinclude").write_text("*\n", encoding="utf-8")
            _git(root, "add", ".worktreeinclude")
            _git(root, "commit", "-qm", "use broad include")
            root.joinpath(".env").write_text("safe\n", encoding="utf-8")
            runtime_file = root / ".vibeagent" / "sessions" / "private.json"
            runtime_file.parent.mkdir(parents=True)
            runtime_file.write_text("private\n", encoding="utf-8")
            target = _target_worktree(root)

            report = copy_worktree_includes(root, target)

            self.assertEqual(target.joinpath(".env").read_text(encoding="utf-8"), "safe\n")
            self.assertFalse(target.joinpath(".vibeagent", "sessions", "private.json").exists())
            self.assertFalse(any(path.startswith(".vibeagent/") for path in report.copied_paths))

    def test_rejects_invalid_include_encoding(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-worktree-include-") as base:
            root = Path(base)
            _repository(root)
            target = _target_worktree(root)
            root.joinpath(".worktreeinclude").write_bytes(b".env\n\xff")

            with self.assertRaisesRegex(ValueError, "valid UTF-8"):
                copy_worktree_includes(root, target)

    def test_rejects_target_from_an_unrelated_repository(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-worktree-include-") as source_base, tempfile.TemporaryDirectory(
            prefix="vibeagent-worktree-include-other-"
        ) as target_base:
            source = Path(source_base)
            target = Path(target_base)
            _repository(source)
            _repository(target)

            with self.assertRaisesRegex(ValueError, "same git repository"):
                copy_worktree_includes(source, target)


if __name__ == "__main__":
    unittest.main()
