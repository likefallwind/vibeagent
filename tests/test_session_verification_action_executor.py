import tempfile
import unittest
from pathlib import Path

from vibeagent.session_action_executor import execute_session_action
from vibeagent.session_verification_action_executor import execute_session_verification_action
from vibeagent.types import RunSessionVerificationAction, SessionSummaryAction, SessionVerificationAction
from vibeagent.workspace_core import RunWorkspace


class SessionVerificationActionExecutorTests(unittest.TestCase):
    def make_workspace(self, root: Path) -> RunWorkspace:
        session_dir = root / ".vibeagent" / "sessions" / "current"
        session_dir.mkdir(parents=True)
        return RunWorkspace(root=root, run_id="current", session_dir=session_dir)

    def test_session_verification_executor_matches_session_executor_for_verification_actions(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-verification-actions-") as tmp:
            workspace = self.make_workspace(Path(tmp))
            actions = [
                SessionVerificationAction(type="session_verification", run_id="missing"),
                RunSessionVerificationAction(type="run_session_verification", run_id="missing"),
            ]

            for action in actions:
                with self.subTest(action=action.type):
                    observation = execute_session_verification_action(workspace, action)

                    self.assertEqual(observation, execute_session_action(workspace, action))
                    self.assertIsNotNone(observation)
                    self.assertEqual(observation.kind, action.type)
                    self.assertEqual(observation.run_id, "missing")

    def test_session_verification_executor_reads_check_status(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-verification-actions-") as tmp:
            workspace = self.make_workspace(Path(tmp))
            (workspace.session_dir / "events.jsonl").write_text(
                '{"type":"result","success":true,"status":"completed","iterations":1,"message":"Done.",'
                '"verification_checks":["python3 -m unittest","python3 -m compileall -q vibeagent"],'
                '"pending_verification_checks":["npm test"],'
                '"failed_verification_checks":["npm run build (exit=1)"]}\n',
                encoding="utf-8",
            )

            observation = execute_session_verification_action(
                workspace,
                SessionVerificationAction(type="session_verification", max_checks=1),
            )

        self.assertEqual(observation.kind, "session_verification")
        self.assertTrue(observation.ok)
        self.assertEqual(observation.run_id, "current")
        self.assertEqual(observation.verified_count, 2)
        self.assertEqual(observation.pending_count, 1)
        self.assertEqual(observation.failed_count, 1)
        self.assertTrue(observation.verification_truncated)
        self.assertEqual(observation.verified_commands[0]["command"], "python3 -m unittest")
        self.assertEqual(observation.pending_commands[0]["command"], "npm test")
        self.assertEqual(observation.failed_commands[0]["command"], "npm run build")

    def test_session_verification_executor_returns_none_for_non_verification_action(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-session-verification-actions-") as tmp:
            workspace = self.make_workspace(Path(tmp))
            action = SessionSummaryAction(type="session_summary", run_id="missing")

            self.assertIsNone(execute_session_verification_action(workspace, action))


if __name__ == "__main__":
    unittest.main()
