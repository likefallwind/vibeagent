import subprocess
import tempfile
import unittest
from pathlib import Path

from vibeagent import checkpoint_actions
from vibeagent import checkpoint_restore_actions
from vibeagent import checkpoint_storage
from vibeagent.checkpoint_create_actions import create_checkpoint_observation
from vibeagent.workspace_core import create_run_workspace


class CheckpointRestoreActionsTests(unittest.TestCase):
    def test_checkpoint_actions_reexports_restore_helpers(self) -> None:
        self.assertIs(
            checkpoint_actions.check_checkpoint_restore_observation,
            checkpoint_restore_actions.check_checkpoint_restore_observation,
        )
        self.assertIs(
            checkpoint_actions.checkpoint_restore_observation,
            checkpoint_restore_actions.checkpoint_restore_observation,
        )
        self.assertIs(
            checkpoint_actions.empty_check_checkpoint_restore,
            checkpoint_restore_actions.empty_check_checkpoint_restore,
        )

    def test_checkpoint_actions_reexports_untracked_restore_helpers(self) -> None:
        self.assertIs(
            checkpoint_actions.checkpoint_untracked_files_match,
            checkpoint_storage.checkpoint_untracked_files_match,
        )
        self.assertIs(
            checkpoint_actions.read_checkpoint_git_head,
            checkpoint_storage.read_checkpoint_git_head,
        )
        self.assertIs(
            checkpoint_actions.restore_checkpoint_untracked_files,
            checkpoint_storage.restore_checkpoint_untracked_files,
        )
        self.assertIs(
            checkpoint_actions.save_checkpoint_untracked_files,
            checkpoint_storage.save_checkpoint_untracked_files,
        )

    def test_checkpoint_restores_staged_binary_patch_without_loading_it_as_text(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-checkpoint-binary-") as base:
            root = Path(base)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=root, check=True)
            binary = root / "asset.bin"
            binary.write_bytes(b"\x00base" * 1024)
            subprocess.run(["git", "add", "asset.bin"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "initial"], cwd=root, check=True)
            expected = b"\x00checkpoint" * 2048
            binary.write_bytes(expected)
            subprocess.run(["git", "add", "asset.bin"], cwd=root, check=True)
            workspace = create_run_workspace(root)
            created = create_checkpoint_observation(workspace, "binary")
            self.assertTrue(created.ok, created.message)
            checkpoint_id = created.checkpoint.checkpoint_id  # type: ignore[union-attr]
            binary.write_bytes(b"\x00broken" * 512)

            restored = checkpoint_restore_actions.checkpoint_restore_observation(workspace, checkpoint_id)

            self.assertTrue(restored.ok, restored.message)
            self.assertTrue(restored.matches)
            self.assertEqual(binary.read_bytes(), expected)
            cached = subprocess.run(
                ["git", "diff", "--cached", "--binary"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
            )
            self.assertTrue(cached.stdout)


if __name__ == "__main__":
    unittest.main()
