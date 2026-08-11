from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import vibeagent.background_agent_integration as integration_module
from vibeagent.background_agent_changes import read_background_agent_changes
from vibeagent.background_agent_config import create_background_agent_config
from vibeagent.background_agent_integration import integrate_background_agent_changes
from vibeagent.background_agent_store import (
    background_agent_runtime_root,
    get_background_agent,
    write_background_agent_record,
)
from vibeagent.background_agent_types import BackgroundAgentRecord, BackgroundAgentView


AGENT_ID = "0123456789ab"


class BackgroundAgentIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="vibeagent-agent-integrate-")
        base = Path(self.temp.name)
        self.root = base / "project"
        self.worktree = base / "worktree"
        self.root.mkdir()
        self._init_repo()
        self._git(self.root, "worktree", "add", "-q", "-b", "agent-integrate", str(self.worktree))
        create_background_agent_config(
            self.root,
            AGENT_ID,
            session_root=self.worktree,
            resume_reference="background-integrate",
            base_argv=["--print", "integrate"],
        )
        self._write_completed_record()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_applies_mixed_snapshot_without_touching_unrelated_main_changes(self) -> None:
        (self.worktree / "committed.txt").write_text("agent commit\n", encoding="utf-8")
        self._git(self.worktree, "add", "committed.txt")
        self._git(self.worktree, "commit", "-qm", "agent commit")
        (self.worktree / "staged.txt").write_text("agent staged\n", encoding="utf-8")
        self._git(self.worktree, "add", "staged.txt")
        (self.worktree / "unstaged.txt").write_text("agent unstaged\n", encoding="utf-8")
        (self.worktree / "binary.dat").write_bytes(b"agent\0binary")
        (self.worktree / "deleted.txt").unlink()
        os.chmod(self.worktree / "script.sh", 0o755)
        (self.root / "unrelated.txt").write_text("user change\n", encoding="utf-8")

        changes = read_background_agent_changes(self.root, AGENT_ID)
        result = integrate_background_agent_changes(
            self.root,
            AGENT_ID,
            expected_snapshot_id=changes.snapshot_id,
        )

        self.assertEqual((self.root / "committed.txt").read_text(), "agent commit\n")
        self.assertEqual((self.root / "staged.txt").read_text(), "agent staged\n")
        self.assertEqual((self.root / "unstaged.txt").read_text(), "agent unstaged\n")
        self.assertEqual((self.root / "binary.dat").read_bytes(), b"agent\0binary")
        self.assertFalse((self.root / "deleted.txt").exists())
        self.assertTrue((self.root / "script.sh").stat().st_mode & 0o100)
        self.assertEqual((self.root / "unrelated.txt").read_text(), "user change\n")
        self.assertEqual(set(result.applied_files), {item.path for item in changes.files})
        self.assertEqual(result.skipped_files, ())

        repeated = integrate_background_agent_changes(
            self.root,
            AGENT_ID,
            expected_snapshot_id=changes.snapshot_id,
        )
        self.assertEqual(repeated.applied_files, ())
        self.assertEqual(set(repeated.skipped_files), {item.path for item in changes.files})

    def test_rejects_conflict_before_applying_any_file(self) -> None:
        (self.worktree / "committed.txt").write_text("agent version\n", encoding="utf-8")
        (self.worktree / "staged.txt").write_text("agent staged\n", encoding="utf-8")
        (self.root / "committed.txt").write_text("user version\n", encoding="utf-8")
        changes = read_background_agent_changes(self.root, AGENT_ID)

        with self.assertRaisesRegex(ValueError, "conflict.*committed.txt"):
            integrate_background_agent_changes(
                self.root,
                AGENT_ID,
                expected_snapshot_id=changes.snapshot_id,
            )

        self.assertEqual((self.root / "committed.txt").read_text(), "user version\n")
        self.assertEqual((self.root / "staged.txt").read_text(), "initial\n")

    def test_rejects_stale_snapshot_and_running_agent(self) -> None:
        target = self.worktree / "unstaged.txt"
        target.write_text("first\n", encoding="utf-8")
        snapshot_id = read_background_agent_changes(self.root, AGENT_ID).snapshot_id
        target.write_text("second\n", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "snapshot is stale"):
            integrate_background_agent_changes(
                self.root,
                AGENT_ID,
                expected_snapshot_id=snapshot_id,
            )
        self.assertEqual((self.root / "unstaged.txt").read_text(), "initial\n")

        current = read_background_agent_changes(self.root, AGENT_ID)
        view = get_background_agent(self.root, AGENT_ID)
        assert view is not None
        running = BackgroundAgentView(record=view.record, status="running", exit_code=None)
        with patch("vibeagent.background_agent_integration.get_background_agent", return_value=running):
            with self.assertRaisesRegex(ValueError, "must stop"):
                integrate_background_agent_changes(
                    self.root,
                    AGENT_ID,
                    expected_snapshot_id=current.snapshot_id,
                )

    def test_rolls_back_files_when_a_later_write_fails(self) -> None:
        (self.worktree / "committed.txt").write_text("agent first\n", encoding="utf-8")
        (self.worktree / "staged.txt").write_text("agent second\n", encoding="utf-8")
        changes = read_background_agent_changes(self.root, AGENT_ID)
        original_write = integration_module._write_file_atomic
        calls = 0

        def fail_second_write(path, state, *, preserve_mode=False):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("injected write failure")
            return original_write(path, state, preserve_mode=preserve_mode)

        with patch.object(integration_module, "_write_file_atomic", side_effect=fail_second_write):
            with self.assertRaisesRegex(ValueError, "Could not apply.*injected write failure"):
                integrate_background_agent_changes(
                    self.root,
                    AGENT_ID,
                    expected_snapshot_id=changes.snapshot_id,
                )

        self.assertEqual((self.root / "committed.txt").read_text(), "initial\n")
        self.assertEqual((self.root / "staged.txt").read_text(), "initial\n")

    def test_rejects_worktree_edit_during_snapshot_application(self) -> None:
        target = self.worktree / "unstaged.txt"
        target.write_text("reviewed\n", encoding="utf-8")
        snapshot_id = read_background_agent_changes(self.root, AGENT_ID).snapshot_id
        original_read_base = integration_module._read_base_state
        mutated = False

        def mutate_before_agent_read(*args, **kwargs):
            nonlocal mutated
            if not mutated:
                mutated = True
                target.write_text("changed during apply\n", encoding="utf-8")
            return original_read_base(*args, **kwargs)

        with patch.object(
            integration_module,
            "_read_base_state",
            side_effect=mutate_before_agent_read,
        ):
            with self.assertRaisesRegex(ValueError, "snapshot is stale"):
                integrate_background_agent_changes(
                    self.root,
                    AGENT_ID,
                    expected_snapshot_id=snapshot_id,
                )

        self.assertEqual((self.root / "unstaged.txt").read_text(), "initial\n")

    def _init_repo(self) -> None:
        self._git(self.root, "init", "-q")
        self._git(self.root, "config", "user.email", "test@example.com")
        self._git(self.root, "config", "user.name", "Test User")
        (self.root / ".gitignore").write_text(".vibeagent/\n", encoding="utf-8")
        for name in ("committed.txt", "staged.txt", "unstaged.txt", "deleted.txt"):
            (self.root / name).write_text("initial\n", encoding="utf-8")
        (self.root / "script.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        (self.root / "unrelated.txt").write_text("initial\n", encoding="utf-8")
        self._git(self.root, "add", ".")
        self._git(self.root, "commit", "-qm", "initial")

    def _write_completed_record(self) -> None:
        runtime = background_agent_runtime_root(self.root)
        logs = runtime / "logs"
        logs.mkdir(mode=0o700)
        stdout = logs / f"{AGENT_ID}.stdout.log"
        stderr = logs / f"{AGENT_ID}.stderr.log"
        exit_code = logs / f"{AGENT_ID}.exit"
        stopped = logs / f"{AGENT_ID}.stopped"
        stdout.write_text("done\n", encoding="utf-8")
        stderr.write_text("", encoding="utf-8")
        exit_code.write_text("0\n", encoding="utf-8")
        write_background_agent_record(
            BackgroundAgentRecord(
                id=AGENT_ID,
                project_root=self.root,
                invocation_root=self.root,
                pid=2_000_000_000,
                start_ticks=None,
                started_at="2026-08-11T00:00:00+00:00",
                task_summary="integration test",
                session_name="integration-test",
                stdout_path=stdout,
                stderr_path=stderr,
                exit_code_path=exit_code,
                stopped_path=stopped,
            )
        )

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
