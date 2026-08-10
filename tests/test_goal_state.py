import json
import tempfile
import unittest
from pathlib import Path

from vibeagent.goal_state import (
    GoalStateError,
    clear_goal,
    format_goal_status,
    new_goal,
    read_goal,
    record_goal_evaluation,
    reset_restored_goal,
    write_goal,
)
from vibeagent.workspace_core import create_run_workspace


class GoalStateTests(unittest.TestCase):
    def test_round_trip_evaluation_and_restore_reset(self) -> None:
        with tempfile.TemporaryDirectory() as base:
            workspace = create_run_workspace(base, run_id="goal-session")
            state = new_goal("tests pass", now=10)
            state = record_goal_evaluation(state, achieved=False, reason="one test fails", total_tokens=17)
            write_goal(workspace, state)

            loaded = read_goal(workspace)
            self.assertEqual(loaded, state)
            restored = reset_restored_goal(loaded, now=20)  # type: ignore[arg-type]
            self.assertEqual(restored.evaluated_turns, 0)  # type: ignore[union-attr]
            self.assertEqual(restored.total_tokens, 0)  # type: ignore[union-attr]
            self.assertEqual(restored.started_at, 20)  # type: ignore[union-attr]
            self.assertIsNone(restored.last_reason)  # type: ignore[union-attr]

    def test_achieved_and_cleared_goals_do_not_restore_active(self) -> None:
        state = new_goal("done", now=1)
        achieved = record_goal_evaluation(state, achieved=True, reason="verified")
        self.assertIsNone(reset_restored_goal(achieved, now=2))
        self.assertIsNone(reset_restored_goal(clear_goal(state), now=2))

    def test_condition_limit_and_status(self) -> None:
        with self.assertRaisesRegex(GoalStateError, "must not exceed"):
            new_goal("x" * 4_001)
        state = new_goal("release passes", now=5)
        text = format_goal_status(state, now=12)
        self.assertIn("Goal (active): release passes", text)
        self.assertIn("elapsed: 7s", text)

    def test_rejects_malformed_and_symlink_state(self) -> None:
        with tempfile.TemporaryDirectory() as base:
            workspace = create_run_workspace(base, run_id="goal-session")
            path = workspace.session_dir / "goal.json"
            path.write_text(json.dumps({"version": 1}), encoding="utf-8")
            with self.assertRaises(GoalStateError):
                read_goal(workspace)
            path.unlink()
            target = Path(base) / "outside.json"
            target.write_text("{}", encoding="utf-8")
            path.symlink_to(target)
            with self.assertRaisesRegex(GoalStateError, "symlink"):
                read_goal(workspace)


if __name__ == "__main__":
    unittest.main()
