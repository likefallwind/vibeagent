import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vibeagent import checkpoint_actions
from vibeagent import checkpoint_create_actions
from vibeagent.agent_runtime_utils import append_session_event
from vibeagent.checkpoint_patch_io import CheckpointPatchSetResult
from vibeagent.workspace_core import create_run_workspace


class CheckpointCreateActionsTests(unittest.TestCase):
    def test_checkpoint_actions_reexports_create_helper(self) -> None:
        self.assertIs(
            checkpoint_actions.create_checkpoint_observation,
            checkpoint_create_actions.create_checkpoint_observation,
        )

    def test_checkpoint_records_session_event_boundary(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-checkpoint-session-") as base:
            root = Path(base)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=root, check=True)
            (root / "tracked.txt").write_text("initial\n", encoding="utf-8")
            subprocess.run(["git", "add", "tracked.txt"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "initial"], cwd=root, check=True)
            workspace = create_run_workspace(root)
            append_session_event(workspace.session_dir, "task", {"task": "change tracked file"})

            observation = checkpoint_create_actions.create_checkpoint_observation(workspace, "before edit")

            self.assertTrue(observation.ok)
            self.assertIsNotNone(observation.checkpoint)
            checkpoint_id = observation.checkpoint.checkpoint_id  # type: ignore[union-attr]
            metadata = json.loads(
                (root / ".vibeagent" / "checkpoints" / checkpoint_id / "metadata.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(metadata["session_run_id"], workspace.run_id)
            self.assertEqual(metadata["session_event_line"], 1)

    def test_checkpoint_capture_failure_removes_incomplete_directory(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-checkpoint-failure-") as base:
            root = Path(base)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=root, check=True)
            (root / "tracked.txt").write_text("initial\n", encoding="utf-8")
            subprocess.run(["git", "add", "tracked.txt"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "initial"], cwd=root, check=True)
            (root / "tracked.txt").write_text("changed\n", encoding="utf-8")
            workspace = create_run_workspace(root)

            with patch(
                "vibeagent.checkpoint_create_actions.capture_checkpoint_patches",
                return_value=CheckpointPatchSetResult(False, 0, 0, "patch too large"),
            ):
                observation = checkpoint_create_actions.create_checkpoint_observation(workspace)

            self.assertFalse(observation.ok)
            self.assertEqual(observation.message, "patch too large")
            checkpoint_root = root / ".vibeagent" / "checkpoints"
            self.assertEqual(list(checkpoint_root.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
