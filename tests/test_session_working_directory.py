from __future__ import annotations

import os
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from vibeagent.actions import execute_action, parse_tool_action
from vibeagent.session_working_directory import (
    MAINTAIN_PROJECT_CWD_ENV,
    SESSION_CWD_FILE,
    inherit_session_cwd,
    read_session_cwd,
    wrap_powershell_command_for_cwd_capture,
)
from vibeagent.types import RunCommandObservation, StartCommandObservation, WaitProcessAction
from vibeagent.workspace import create_run_workspace


class SessionWorkingDirectoryTests(unittest.TestCase):
    def test_bash_cd_changes_following_command_directory(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cwd-") as base:
            root = Path(base)
            (root / "src").mkdir()
            workspace = create_run_workspace(root, "run-1")

            changed = self._run(workspace, "cd src")
            following = self._run(workspace, "pwd")

        self.assertEqual(changed.result.exit_code, 0)
        self.assertEqual(changed.result.previous_cwd, str(root.resolve()))
        self.assertEqual(changed.result.final_cwd, str((root / "src").resolve()))
        self.assertEqual(following.result.stdout.strip(), str((root / "src").resolve()))
        self.assertEqual(following.result.cwd, "src")

    def test_cwd_capture_preserves_command_exit_code(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cwd-") as base:
            root = Path(base)
            (root / "src").mkdir()
            workspace = create_run_workspace(root, "run-1")

            observation = self._run(workspace, "cd src && false")

        self.assertEqual(observation.result.exit_code, 1)
        self.assertEqual(observation.result.final_cwd, str((root / "src").resolve()))

    def test_cwd_outside_workspace_resets_to_project_root(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cwd-") as base:
            root = Path(base)
            workspace = create_run_workspace(root, "run-1")

            changed = self._run(workspace, "cd /tmp")
            following = self._run(workspace, "pwd")

        self.assertTrue(changed.result.cwd_reset)
        self.assertIn("Shell cwd was reset", changed.result.stderr)
        self.assertEqual(following.result.stdout.strip(), str(root.resolve()))

    def test_opt_out_keeps_every_command_at_project_root(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cwd-") as base:
            root = Path(base)
            (root / "src").mkdir()
            workspace = create_run_workspace(root, "run-1")
            with patch.dict(os.environ, {MAINTAIN_PROJECT_CWD_ENV: "1"}):
                changed = self._run(workspace, "cd src")
                following = self._run(workspace, "pwd")

        self.assertIsNone(changed.result.final_cwd)
        self.assertEqual(following.result.stdout.strip(), str(root.resolve()))

    def test_additional_root_can_become_session_cwd(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cwd-") as base:
            parent = Path(base)
            root = parent / "project"
            shared = parent / "shared"
            root.mkdir()
            shared.mkdir()
            workspace = create_run_workspace(root, "run-1", additional_roots=(shared,))

            changed = self._run(workspace, f"cd {shared}")
            following = self._run(workspace, "pwd")

        self.assertEqual(changed.result.final_cwd, str(shared.resolve()))
        self.assertEqual(following.result.stdout.strip(), str(shared.resolve()))

    def test_background_bash_starts_in_persistent_cwd(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cwd-") as base:
            root = Path(base)
            (root / "src").mkdir()
            workspace = create_run_workspace(root, "run-1")
            self._run(workspace, "cd src")
            action = parse_tool_action(
                "Bash",
                {"command": "pwd", "run_in_background": True},
            )

            started = execute_action(workspace, action, 5_000)
            assert isinstance(started, StartCommandObservation)
            waited = execute_action(
                workspace,
                WaitProcessAction(
                    type="wait_process",
                    process_id=started.process_id,
                    timeout_ms=5_000,
                ),
                5_000,
            )

        self.assertEqual(started.cwd, "src")
        self.assertEqual(waited.stdout.strip(), str((root / "src").resolve()))

    def test_subagent_workspace_does_not_share_persistent_cwd(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cwd-") as base:
            root = Path(base)
            (root / "src").mkdir()
            workspace = replace(
                create_run_workspace(root, "run-1"),
                maintain_shell_cwd=False,
            )

            changed = self._run(workspace, "cd src")
            following = self._run(workspace, "pwd")

        self.assertIsNone(changed.result.final_cwd)
        self.assertEqual(following.result.stdout.strip(), str(root.resolve()))

    def test_invalid_state_falls_back_to_project_root(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cwd-") as base:
            root = Path(base)
            workspace = create_run_workspace(root, "run-1")
            (workspace.session_dir / SESSION_CWD_FILE).write_text("not-json", encoding="utf-8")

            cwd = read_session_cwd(workspace)

        self.assertEqual(cwd, root.resolve())

    def test_symlinked_state_is_not_followed_or_overwritten(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cwd-") as base:
            root = Path(base)
            (root / "src").mkdir()
            external = root / "external.txt"
            external.write_text("keep", encoding="utf-8")
            workspace = create_run_workspace(root, "run-1")
            state = workspace.session_dir / SESSION_CWD_FILE
            state.symlink_to(external)

            changed = self._run(workspace, "cd src")
            external_content = external.read_text(encoding="utf-8")

        self.assertEqual(external_content, "keep")
        self.assertIn("persistence warning", changed.result.stderr)

    def test_session_cwd_can_be_inherited_by_a_new_run(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cwd-") as base:
            root = Path(base)
            (root / "src").mkdir()
            source = create_run_workspace(root, "source-run")
            target = create_run_workspace(root, "target-run")
            self._run(source, "cd src")

            inherited, error = inherit_session_cwd(target, source.run_id)
            inherited_cwd = read_session_cwd(target)

        self.assertTrue(inherited)
        self.assertIsNone(error)
        self.assertEqual(inherited_cwd, (root / "src").resolve())

    def test_powershell_capture_wrapper_uses_final_provider_path(self) -> None:
        capture = Path("/tmp/cwd-state")

        wrapped = wrap_powershell_command_for_cwd_capture("Set-Location src", capture)

        self.assertIn("try { & {", wrapped)
        self.assertIn("Set-Location src", wrapped)
        self.assertIn("(Get-Location).ProviderPath", wrapped)
        self.assertIn(str(capture), wrapped)

    @staticmethod
    def _run(workspace, command: str) -> RunCommandObservation:
        action = parse_tool_action("Bash", {"command": command})
        observation = execute_action(workspace, action, 5_000)
        assert isinstance(observation, RunCommandObservation)
        return observation


if __name__ == "__main__":
    unittest.main()
