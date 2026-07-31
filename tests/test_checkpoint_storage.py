from __future__ import annotations

import unittest

from vibeagent import checkpoint_storage, checkpoint_untracked_storage


class CheckpointStorageTests(unittest.TestCase):
    def test_checkpoint_storage_reexports_untracked_helpers(self) -> None:
        self.assertIs(
            checkpoint_storage.save_checkpoint_untracked_files,
            checkpoint_untracked_storage.save_checkpoint_untracked_files,
        )
        self.assertIs(
            checkpoint_storage.read_checkpoint_untracked_manifest,
            checkpoint_untracked_storage.read_checkpoint_untracked_manifest,
        )
        self.assertIs(
            checkpoint_storage.restore_checkpoint_untracked_files,
            checkpoint_untracked_storage.restore_checkpoint_untracked_files,
        )
        self.assertIs(checkpoint_storage.is_runtime_checkpoint_path, checkpoint_untracked_storage.is_runtime_checkpoint_path)


if __name__ == "__main__":
    unittest.main()
