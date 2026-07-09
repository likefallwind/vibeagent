import tempfile
import unittest
from pathlib import Path

from vibeagent.actions import execute_action
from vibeagent.checkpoint_action_executor import execute_checkpoint_action
from vibeagent.types import (
    CheckCheckpointDeleteAction,
    CheckCheckpointPruneAction,
    CheckCheckpointRestoreAction,
    CheckpointCreateAction,
    CheckpointDeleteAction,
    CheckpointDiffAction,
    CheckpointListAction,
    CheckpointPruneAction,
    CheckpointRestoreAction,
    CheckpointShowAction,
    CheckpointStatusAction,
    ReadFileAction,
)
from vibeagent.workspace_core import RunWorkspace


class CheckpointActionExecutorTests(unittest.TestCase):
    def make_workspace(self, root: Path) -> RunWorkspace:
        session_dir = root / ".vibeagent" / "sessions" / "run-1"
        session_dir.mkdir(parents=True)
        return RunWorkspace(root=root, run_id="run-1", session_dir=session_dir)

    def test_checkpoint_executor_matches_top_level_for_checkpoint_actions(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-checkpoint-actions-") as tmp:
            workspace = self.make_workspace(Path(tmp))
            actions = [
                CheckpointCreateAction(type="checkpoint_create", label="before edit"),
                CheckpointListAction(type="checkpoint_list", max_entries=5),
                CheckpointShowAction(type="checkpoint_show", checkpoint_id="missing"),
                CheckpointDiffAction(type="checkpoint_diff", checkpoint_id="missing", max_chars=1000),
                CheckpointStatusAction(type="checkpoint_status", checkpoint_id="missing"),
                CheckCheckpointRestoreAction(type="check_checkpoint_restore", checkpoint_id="missing"),
                CheckpointRestoreAction(type="checkpoint_restore", checkpoint_id="missing"),
                CheckCheckpointDeleteAction(type="check_checkpoint_delete", checkpoint_id="missing"),
                CheckpointDeleteAction(type="checkpoint_delete", checkpoint_id="missing"),
                CheckCheckpointPruneAction(type="check_checkpoint_prune", keep_last=1),
                CheckpointPruneAction(type="checkpoint_prune", keep_last=1),
            ]

            for action in actions:
                with self.subTest(action=action.type):
                    self.assertEqual(execute_checkpoint_action(workspace, action), execute_action(workspace, action))

    def test_checkpoint_executor_returns_none_for_non_checkpoint_action(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-checkpoint-actions-") as tmp:
            workspace = self.make_workspace(Path(tmp))
            action = ReadFileAction(type="read_file", path="app.py")

            self.assertIsNone(execute_checkpoint_action(workspace, action))


if __name__ == "__main__":
    unittest.main()
