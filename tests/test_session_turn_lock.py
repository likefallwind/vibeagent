from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vibeagent.agent import run_agent
from vibeagent import session_turn_lock as lock_module
from vibeagent.session_turn_lock import SessionTurnBusyError, session_turn_lock
from vibeagent.workspace_core import create_run_workspace


class NoCallClient:
    def complete(self, *args, **kwargs):
        raise AssertionError("model must not be called while the session is busy")


class SessionTurnLockTests(unittest.TestCase):
    def test_lock_rejects_overlapping_turn_and_releases_after_exit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-turn-lock-") as base:
            workspace = create_run_workspace(base, run_id="run-1")
            with session_turn_lock(workspace):
                with self.assertRaisesRegex(SessionTurnBusyError, "active agent turn"):
                    with session_turn_lock(workspace):
                        pass

            with session_turn_lock(workspace):
                pass

            lock_path = workspace.session_dir / "turn.lock"
            self.assertEqual(os.stat(lock_path).st_mode & 0o777, 0o600)

    def test_run_agent_refuses_busy_existing_session_before_model_call(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-turn-lock-") as base:
            workspace = create_run_workspace(base, run_id="run-1")
            with session_turn_lock(workspace):
                with self.assertRaisesRegex(SessionTurnBusyError, "--fork-session"):
                    run_agent(
                        "continue",
                        workspace=workspace,
                        client=NoCallClient(),
                        max_iterations=1,
                    )

    def test_lock_rejects_symbolic_link_storage(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-turn-lock-") as base:
            root = Path(base)
            workspace = create_run_workspace(root, run_id="run-1")
            target = root / "outside.lock"
            target.write_text("outside", encoding="utf-8")
            (workspace.session_dir / "turn.lock").symlink_to(target)

            with self.assertRaisesRegex(SessionTurnBusyError, "not a regular file"):
                with session_turn_lock(workspace):
                    pass

    def test_lock_releases_when_agent_turn_raises(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-turn-lock-") as base:
            workspace = create_run_workspace(base, run_id="run-1")

            with self.assertRaisesRegex(RuntimeError, "turn failed"):
                with session_turn_lock(workspace):
                    raise RuntimeError("turn failed")

            with session_turn_lock(workspace):
                pass

    def test_windows_lock_backend_preserves_the_active_owner(self) -> None:
        class FakeMsvcrt:
            LK_NBLCK = 1
            LK_UNLCK = 2
            locked = False

            @classmethod
            def locking(cls, descriptor, mode, count):
                self.assertEqual(count, 1)
                if mode == cls.LK_NBLCK:
                    if cls.locked:
                        raise OSError("locked")
                    cls.locked = True
                else:
                    self.assertTrue(cls.locked)
                    cls.locked = False

        with tempfile.TemporaryDirectory(prefix="vibeagent-turn-lock-") as base:
            workspace = create_run_workspace(base, run_id="run-1")
            with patch.object(lock_module, "_fcntl", None), patch.object(lock_module, "_msvcrt", FakeMsvcrt):
                with session_turn_lock(workspace):
                    with self.assertRaisesRegex(SessionTurnBusyError, "active agent turn"):
                        with session_turn_lock(workspace):
                            pass
                    self.assertTrue(FakeMsvcrt.locked)

                self.assertFalse(FakeMsvcrt.locked)


if __name__ == "__main__":
    unittest.main()
