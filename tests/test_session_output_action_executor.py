import tempfile
import unittest
from pathlib import Path

from vibeagent.session_action_executor import execute_session_action
from vibeagent.session_output_action_executor import execute_session_output_action
from vibeagent.types import SessionOutputContextsAction, SessionOutputDiagnosticsAction, SessionSummaryAction
from vibeagent.workspace_core import RunWorkspace


class SessionOutputActionExecutorTests(unittest.TestCase):
    def make_workspace(self, root: Path) -> RunWorkspace:
        session_dir = root / ".vibeagent" / "sessions" / "current"
        session_dir.mkdir(parents=True)
        return RunWorkspace(root=root, run_id="current", session_dir=session_dir)

    def test_session_output_executor_matches_session_executor_for_output_actions(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-output-actions-") as tmp:
            workspace = self.make_workspace(Path(tmp))
            actions = [
                SessionOutputContextsAction(type="session_output_contexts", run_id="missing"),
                SessionOutputDiagnosticsAction(type="session_output_diagnostics", run_id="missing"),
            ]

            for action in actions:
                with self.subTest(action=action.type):
                    self.assertEqual(
                        execute_session_output_action(workspace, action),
                        execute_session_action(workspace, action),
                    )

    def test_session_output_executor_returns_none_for_non_output_action(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-output-actions-") as tmp:
            workspace = self.make_workspace(Path(tmp))
            action = SessionSummaryAction(type="session_summary", run_id="missing")

            self.assertIsNone(execute_session_output_action(workspace, action))


if __name__ == "__main__":
    unittest.main()
