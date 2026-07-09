import tempfile
import unittest
from pathlib import Path

from vibeagent.session_action_executor import execute_session_action
from vibeagent.session_report_action_executor import execute_session_report_action
from vibeagent.types import (
    SessionCommandsAction,
    SessionFailuresAction,
    SessionFilesAction,
    SessionOutputContextsAction,
    SessionPlanAction,
    SessionSearchAction,
    SessionSummaryAction,
    SessionTranscriptAction,
)
from vibeagent.workspace_core import RunWorkspace


class SessionReportActionExecutorTests(unittest.TestCase):
    def make_workspace(self, root: Path) -> RunWorkspace:
        session_dir = root / ".vibeagent" / "sessions" / "current"
        session_dir.mkdir(parents=True)
        return RunWorkspace(root=root, run_id="current", session_dir=session_dir)

    def test_session_report_executor_matches_session_executor_for_report_actions(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-report-actions-") as tmp:
            workspace = self.make_workspace(Path(tmp))
            actions = [
                SessionSummaryAction(type="session_summary", run_id="missing"),
                SessionPlanAction(type="session_plan", run_id="missing"),
                SessionTranscriptAction(type="session_transcript", run_id="missing"),
                SessionSearchAction(type="session_search", query="needle", run_id="missing"),
                SessionCommandsAction(type="session_commands", run_id="missing"),
                SessionFilesAction(type="session_files", run_id="missing"),
                SessionFailuresAction(type="session_failures", run_id="missing"),
            ]

            for action in actions:
                with self.subTest(action=action.type):
                    observation = execute_session_report_action(workspace, action)

                    self.assertEqual(observation, execute_session_action(workspace, action))
                    self.assertIsNotNone(observation)
                    self.assertEqual(observation.kind, action.type)
                    self.assertEqual(observation.run_id, "missing")

    def test_session_report_executor_returns_none_for_non_report_action(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-report-actions-") as tmp:
            workspace = self.make_workspace(Path(tmp))
            action = SessionOutputContextsAction(type="session_output_contexts", run_id="missing")

            self.assertIsNone(execute_session_report_action(workspace, action))


if __name__ == "__main__":
    unittest.main()
