from __future__ import annotations

import json
import os
import stat
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from vibeagent.actions import execute_action, parse_tool_action
from vibeagent.agent import run_agent
from vibeagent.session_environment import (
    MAX_SESSION_ENV_BYTES,
    SESSION_ENV_FILE,
    ensure_session_environment_file,
    inherit_session_environment,
)
from vibeagent.session_working_directory import MAINTAIN_PROJECT_CWD_ENV
from vibeagent.types import (
    ApprovalDecision,
    AssistantResponse,
    ChatMessage,
    ContentBlock,
    RunCommandObservation,
    StartCommandObservation,
    WaitProcessAction,
)
from vibeagent.workspace import create_run_workspace


class SessionEnvironmentTests(unittest.TestCase):
    def test_foreground_bash_loads_session_environment(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-env-") as base:
            workspace = create_run_workspace(Path(base), "run-1")
            env_file = ensure_session_environment_file(workspace)
            env_file.write_text("export VIBE_ENV_TEST=ready\n", encoding="utf-8")

            result = self._run(workspace, "printf '%s' \"$VIBE_ENV_TEST\"")

        self.assertEqual(result.result.exit_code, 0)
        self.assertEqual(result.result.stdout, "ready")

    def test_plain_export_does_not_persist_without_environment_file_write(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-env-") as base:
            workspace = create_run_workspace(Path(base), "run-1")

            self._run(workspace, "export TRANSIENT_VALUE=temporary")
            result = self._run(workspace, "printf '%s' \"${TRANSIENT_VALUE-unset}\"")

        self.assertEqual(result.result.stdout, "unset")

    def test_background_bash_loads_session_environment(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-env-") as base:
            workspace = create_run_workspace(Path(base), "run-1")
            ensure_session_environment_file(workspace).write_text(
                "export BACKGROUND_VALUE=background-ready\n",
                encoding="utf-8",
            )
            action = parse_tool_action(
                "Bash",
                {
                    "command": "printf '%s' \"$BACKGROUND_VALUE\"",
                    "run_in_background": True,
                },
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

        self.assertEqual(waited.stdout, "background-ready")

    def test_environment_load_survives_cwd_persistence_opt_out(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-env-") as base:
            workspace = create_run_workspace(Path(base), "run-1")
            ensure_session_environment_file(workspace).write_text(
                "export OPT_OUT_VALUE=still-loaded\n",
                encoding="utf-8",
            )
            with patch.dict(os.environ, {MAINTAIN_PROJECT_CWD_ENV: "1"}):
                result = self._run(workspace, "printf '%s' \"$OPT_OUT_VALUE\"")

        self.assertEqual(result.result.stdout, "still-loaded")

    def test_subagent_workspace_loads_environment_without_sharing_cwd(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-env-") as base:
            workspace = replace(
                create_run_workspace(Path(base), "run-1"),
                maintain_shell_cwd=False,
            )
            ensure_session_environment_file(workspace).write_text(
                "export SUBAGENT_VALUE=available\n",
                encoding="utf-8",
            )

            result = self._run(workspace, "printf '%s' \"$SUBAGENT_VALUE\"")

        self.assertEqual(result.result.stdout, "available")
        self.assertIsNone(result.result.final_cwd)

    def test_invalid_environment_aborts_before_target_command(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-env-") as base:
            root = Path(base)
            workspace = create_run_workspace(root, "run-1")
            ensure_session_environment_file(workspace).write_text(
                "this-command-does-not-exist\n",
                encoding="utf-8",
            )

            result = self._run(workspace, "printf ran > marker.txt")
            marker_exists = (root / "marker.txt").exists()

        self.assertNotEqual(result.result.exit_code, 0)
        self.assertFalse(marker_exists)

    def test_hard_blocked_environment_never_reaches_target_command(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-env-") as base:
            root = Path(base)
            workspace = create_run_workspace(root, "run-1")
            ensure_session_environment_file(workspace).write_text(
                "sudo reboot\n",
                encoding="utf-8",
            )

            result = self._run(workspace, "printf ran > marker.txt")
            marker_exists = (root / "marker.txt").exists()

        self.assertIsNone(result.result.exit_code)
        self.assertIn("Session environment blocked", result.result.stderr)
        self.assertFalse(marker_exists)

    def test_symlinked_or_oversized_environment_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-env-") as base:
            root = Path(base)
            symlink_workspace = create_run_workspace(root, "symlink-run")
            external = root / "external.sh"
            external.write_text("export BAD=1\n", encoding="utf-8")
            (symlink_workspace.session_dir / SESSION_ENV_FILE).symlink_to(external)

            symlink_result = self._run(symlink_workspace, "printf should-not-run")

            large_workspace = create_run_workspace(root, "large-run")
            large_path = large_workspace.session_dir / SESSION_ENV_FILE
            large_path.write_bytes(b"x" * (MAX_SESSION_ENV_BYTES + 1))
            large_result = self._run(large_workspace, "printf should-not-run")

        self.assertIsNone(symlink_result.result.exit_code)
        self.assertIn("not a regular file", symlink_result.result.stderr)
        self.assertIsNone(large_result.result.exit_code)
        self.assertIn("exceeds", large_result.result.stderr)

    def test_environment_file_is_private_and_inheritable(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-env-") as base:
            root = Path(base)
            source = create_run_workspace(root, "source-run")
            target = create_run_workspace(root, "target-run")
            source_path = ensure_session_environment_file(source)
            source_path.write_text("export INHERITED_VALUE=yes\n", encoding="utf-8")
            source_path.chmod(0o644)

            inherited, error = inherit_session_environment(target, source.run_id)
            target_path = ensure_session_environment_file(target)
            target_content = target_path.read_text(encoding="utf-8")
            target_mode = stat.S_IMODE(target_path.stat().st_mode)

        self.assertTrue(inherited)
        self.assertIsNone(error)
        self.assertEqual(target_content, "export INHERITED_VALUE=yes\n")
        if os.name != "nt":
            self.assertEqual(target_mode, 0o600)

    @staticmethod
    def _run(workspace, command: str) -> RunCommandObservation:
        action = parse_tool_action("Bash", {"command": command})
        observation = execute_action(workspace, action, 5_000)
        assert isinstance(observation, RunCommandObservation)
        return observation


class HookEnvironmentClient:
    def __init__(self, responses: list[list[ContentBlock]]) -> None:
        self.responses = responses
        self.messages: list[list[ChatMessage]] = []

    def complete(self, messages, tools=None, max_tokens=4096, temperature=0.2, timeout_ms=120_000):
        self.messages.append(list(messages))
        content = self.responses[len(self.messages) - 1]
        return AssistantResponse(content=content, raw={"content": content})


class SessionEnvironmentHookTests(unittest.TestCase):
    def test_session_start_and_cwd_changed_hooks_update_later_bash_environment(self) -> None:
        client = HookEnvironmentClient(
            [
                [{"type": "tool_call", "id": "bash-1", "name": "Bash", "input": {"command": "cd src"}}],
                [
                    {
                        "type": "tool_call",
                        "id": "bash-2",
                        "name": "Bash",
                        "input": {"command": "printf '%s' \"$HOOK_ENV_VALUE\""},
                    }
                ],
                [{"type": "text", "text": "Environment loaded."}],
            ]
        )
        with tempfile.TemporaryDirectory(prefix="vibeagent-env-") as base:
            root = Path(base)
            (root / "src").mkdir()
            settings = root / ".vibeagent" / "hooks.json"
            settings.parent.mkdir(parents=True, exist_ok=True)
            settings.write_text(
                json.dumps(
                    {
                        "SessionStart": [self._environment_hook("startup")],
                        "CwdChanged": [self._environment_hook("cwd")],
                    }
                ),
                encoding="utf-8",
            )

            result = run_agent(
                "Load the directory environment",
                base_dir=root,
                client=client,
                max_iterations=3,
                approval_handler=lambda _request: ApprovalDecision(
                    approved=True,
                    message="approved",
                ),
            )

        command_results = [item.result for item in result.observations if item.kind == "run_command"]
        self.assertEqual(command_results[-1].stdout, "cwd")

    @staticmethod
    def _environment_hook(value: str) -> dict[str, object]:
        command = f"printf 'export HOOK_ENV_VALUE={value}\\n' > \"$CLAUDE_ENV_FILE\""
        return {
            "matcher": ".*",
            "hooks": [{"type": "command", "command": command, "timeout_ms": 5_000}],
        }


if __name__ == "__main__":
    unittest.main()
