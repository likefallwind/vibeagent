from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import vibeagent.background_agent_changes as changes_runtime
from vibeagent.background_agent_changes import (
    MAX_BACKGROUND_CHANGE_GIT_OUTPUT_CHARS,
    read_background_agent_change_content,
    read_background_agent_changes,
)
from vibeagent.background_agent_config import create_background_agent_config
from vibeagent.workspace_core import GitCommandResult


AGENT_ID = "0123456789ab"


class BackgroundAgentChangesTests(unittest.TestCase):
    def test_change_list_rejects_stream_truncation_before_parsing_paths(self) -> None:
        result = GitCommandResult(
            ok=True,
            stdout="head\0tail",
            stderr="",
            exit_code=0,
            stdout_truncated=True,
            stdout_total_chars=2_000_000,
        )
        with patch(
            "vibeagent.background_agent_changes.run_readonly_git",
            return_value=result,
        ) as run:
            with self.assertRaisesRegex(ValueError, "change list is too large"):
                changes_runtime._changed_paths(Path("/project"), ["status"])

        run.assert_called_once_with(
            Path("/project"),
            ["status"],
            max_output_chars=MAX_BACKGROUND_CHANGE_GIT_OUTPUT_CHARS + 1,
        )

    def test_reads_committed_staged_unstaged_and_untracked_worktree_changes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-changes-") as base:
            root = Path(base) / "project"
            worktree = Path(base) / "worktree"
            root.mkdir()
            self._init_repo(root)
            self._git(root, "worktree", "add", "-q", "-b", "agent-review", str(worktree))
            create_background_agent_config(
                root,
                AGENT_ID,
                session_root=worktree,
                resume_reference="background-review",
                base_argv=["--print", "review"],
            )

            (worktree / "committed.txt").write_text("agent commit\n", encoding="utf-8")
            self._git(worktree, "add", "committed.txt")
            self._git(worktree, "commit", "-qm", "agent commit")
            (worktree / "staged.txt").write_text("staged change\n", encoding="utf-8")
            self._git(worktree, "add", "staged.txt")
            (worktree / "unstaged.txt").write_text("unstaged change\n", encoding="utf-8")
            (worktree / "new.txt").write_text("new file\n", encoding="utf-8")
            (worktree / ".env").write_text("SECRET=value\n", encoding="utf-8")
            (worktree / ".claude").mkdir()
            (worktree / ".claude/settings.json").write_text("{}\n", encoding="utf-8")

            changes = read_background_agent_changes(root, AGENT_ID)
            files = {item.path: item for item in changes.files}

            self.assertTrue(changes.isolated)
            self.assertEqual(changes.branch, "agent-review")
            self.assertTrue(files["committed.txt"].committed)
            self.assertTrue(files["staged.txt"].staged)
            self.assertTrue(files["unstaged.txt"].unstaged)
            self.assertTrue(files["new.txt"].untracked)
            self.assertNotIn(".env", files)
            self.assertNotIn(".claude/settings.json", files)
            self.assertEqual(
                read_background_agent_change_content(root, AGENT_ID, "committed.txt", side="base"),
                "initial\n",
            )
            self.assertEqual(
                read_background_agent_change_content(root, AGENT_ID, "committed.txt", side="current"),
                "agent commit\n",
            )
            self.assertEqual(
                read_background_agent_change_content(root, AGENT_ID, "new.txt", side="base"),
                "",
            )

            snapshot_id = changes.snapshot_id
            (worktree / "new.txt").write_text("newer file\n", encoding="utf-8")
            self.assertNotEqual(
                read_background_agent_changes(root, AGENT_ID).snapshot_id,
                snapshot_id,
            )

    def test_rejects_unlinked_session_and_unlisted_or_binary_content(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-changes-") as base:
            root = Path(base) / "project"
            other = Path(base) / "other"
            root.mkdir()
            other.mkdir()
            self._init_repo(root)
            self._init_repo(other)
            create_background_agent_config(
                root,
                AGENT_ID,
                session_root=other,
                resume_reference="background-invalid",
                base_argv=["--print", "review"],
            )

            with self.assertRaisesRegex(ValueError, "not a linked project worktree"):
                read_background_agent_changes(root, AGENT_ID)

        with tempfile.TemporaryDirectory(prefix="vibeagent-agent-changes-") as base:
            root = Path(base) / "project"
            worktree = Path(base) / "worktree"
            root.mkdir()
            self._init_repo(root)
            self._git(root, "worktree", "add", "-q", "-b", "agent-binary", str(worktree))
            create_background_agent_config(
                root,
                AGENT_ID,
                session_root=worktree,
                resume_reference="background-binary",
                base_argv=["--print", "review"],
            )
            (worktree / "binary.dat").write_bytes(b"value\0data")

            with self.assertRaisesRegex(ValueError, "unavailable"):
                read_background_agent_change_content(root, AGENT_ID, "missing.txt", side="current")
            with self.assertRaisesRegex(ValueError, "binary"):
                read_background_agent_change_content(root, AGENT_ID, "binary.dat", side="current")

    def _init_repo(self, root: Path) -> None:
        self._git(root, "init", "-q")
        self._git(root, "config", "user.email", "test@example.com")
        self._git(root, "config", "user.name", "Test User")
        (root / ".gitignore").write_text(".env\n.vibeagent/\n", encoding="utf-8")
        for name in ("committed.txt", "staged.txt", "unstaged.txt"):
            (root / name).write_text("initial\n", encoding="utf-8")
        self._git(root, "add", ".")
        self._git(root, "commit", "-qm", "initial")

    def _git(self, root: Path, *args: str) -> None:
        subprocess.run(
            ["git", *args],
            cwd=root,
            text=True,
            capture_output=True,
            check=True,
        )


if __name__ == "__main__":
    unittest.main()
