from __future__ import annotations

import unittest

from vibeagent import types as t
from vibeagent.agent_action_descriptions import (
    build_action_target as compat_build_action_target,
    build_step_label as compat_build_step_label,
    log_action as compat_log_action,
)
from vibeagent.agent_action_labels import build_step_label
from vibeagent.agent_action_logging import log_action
from vibeagent.agent_action_targets import build_action_target


class AgentActionDescriptionTests(unittest.TestCase):
    def test_compat_module_reexports_split_helpers(self) -> None:
        self.assertIs(compat_build_step_label, build_step_label)
        self.assertIs(compat_build_action_target, build_action_target)
        self.assertIs(compat_log_action, log_action)

    def test_step_label_and_target_describe_same_action(self) -> None:
        action = t.RunCommandAction(type="run_command", command="python3 -m unittest", cwd="tests")

        self.assertEqual(build_step_label(action), "Run python3 -m unittest in tests")
        self.assertEqual(build_action_target(action), "python3 -m unittest (cwd: tests)")

    def test_action_targets_reuse_approval_command_target_format(self) -> None:
        action = t.CheckRunCommandsAction(
            type="check_run_commands",
            commands=[
                t.RunCommandItem(command="python -m unittest", cwd="."),
                t.RunCommandItem(command="npm test", cwd="web"),
            ],
        )

        self.assertEqual(
            build_action_target(action),
            "python -m unittest (cwd: .), npm test (cwd: web)",
        )

    def test_action_targets_reuse_verification_runner_target_format(self) -> None:
        self.assertEqual(
            build_action_target(t.CheckSuggestedChecksAction(type="check_suggested_checks", max_commands=2)),
            "up to 2 suggested check command(s)",
        )
        self.assertEqual(
            build_action_target(t.CheckFocusedTestCommandsAction(type="check_focused_test_commands", max_commands=3)),
            "up to 3 focused test command(s)",
        )
        self.assertEqual(
            build_action_target(
                t.RunSessionVerificationAction(
                    type="run_session_verification",
                    run_id="run-1",
                    include_failed=True,
                    include_pending=False,
                )
            ),
            "failed verification command(s) from run-1",
        )

    def test_log_action_uses_action_target(self) -> None:
        events: list[tuple[str, str | None]] = []
        action = t.ReadFileAction(type="read_file", path="vibeagent/agent.py")

        log_action(lambda message, target: events.append((message, target)), action)

        self.assertEqual(events, [("reading file", "vibeagent/agent.py")])


if __name__ == "__main__":
    unittest.main()
