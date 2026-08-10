from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from vibeagent.agent_runtime_utils import append_session_event
from vibeagent.session_branching import create_session_branch
from vibeagent.session_names import (
    name_session,
    read_session_name,
    resolve_session_reference,
    transfer_session_name,
)
from vibeagent.workspace_core import create_run_workspace


class SessionNameTests(unittest.TestCase):
    def test_names_regular_sessions_and_resolves_latest_rename(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-name-") as base:
            root = Path(base)
            workspace = create_run_workspace(root, "run-1")
            append_session_event(workspace.session_dir, "task", {"task": "implement auth"})

            self.assertEqual(name_session(root, workspace.run_id, "auth work"), "auth work")
            self.assertEqual(name_session(root, workspace.run_id, "auth-refactor"), "auth-refactor")
            self.assertEqual(read_session_name(root, workspace.run_id), "auth-refactor")
            self.assertEqual(resolve_session_reference(root, "auth-refactor"), workspace.run_id)
            self.assertEqual(resolve_session_reference(root, "auth work"), "auth work")

    def test_auto_name_is_task_based_unique_and_rejects_invalid_names(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-name-") as base:
            root = Path(base)
            first = create_run_workspace(root, "run-1")
            second = create_run_workspace(root, "run-2")
            append_session_event(first.session_dir, "task", {"task": "Fix login tests"})
            append_session_event(second.session_dir, "task", {"task": "Fix login tests"})

            self.assertEqual(name_session(root, first.run_id), "Fix-login-tests")
            self.assertEqual(name_session(root, second.run_id), "Fix-login-tests-2")
            with self.assertRaisesRegex(ValueError, "already in use"):
                name_session(root, second.run_id, "Fix-login-tests")
            with self.assertRaisesRegex(ValueError, "reserved"):
                name_session(root, second.run_id, "latest")
            with self.assertRaisesRegex(ValueError, "control characters"):
                name_session(root, second.run_id, "bad\nname")
            with self.assertRaisesRegex(ValueError, "sensitive credentials"):
                name_session(root, second.run_id, "sk-123456789abcdef")

    def test_name_transfers_to_latest_session_without_ambiguity(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-name-") as base:
            root = Path(base)
            source = create_run_workspace(root, "run-1")
            target = create_run_workspace(root, "run-2")
            append_session_event(source.session_dir, "task", {"task": "first"})
            append_session_event(target.session_dir, "task", {"task": "second"})
            name_session(root, source.run_id, "active-work")

            self.assertEqual(transfer_session_name(root, source.run_id, target.run_id), "active-work")
            self.assertIsNone(read_session_name(root, source.run_id))
            self.assertEqual(read_session_name(root, target.run_id), "active-work")
            self.assertEqual(resolve_session_reference(root, "active-work"), target.run_id)

    def test_legacy_branch_name_remains_a_general_session_name(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-name-") as base:
            root = Path(base)
            source = create_run_workspace(root, "source")
            append_session_event(source.session_dir, "task", {"task": "source"})
            branch = create_session_branch(root, source.run_id, name="experiment")

            self.assertEqual(read_session_name(root, branch.workspace.run_id), "experiment")
            name_session(root, branch.workspace.run_id, "experiment-v2")
            self.assertEqual(resolve_session_reference(root, "experiment-v2"), branch.workspace.run_id)


if __name__ == "__main__":
    unittest.main()
