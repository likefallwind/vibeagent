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

    def test_log_action_uses_action_target(self) -> None:
        events: list[tuple[str, str | None]] = []
        action = t.ReadFileAction(type="read_file", path="vibeagent/agent.py")

        log_action(lambda message, target: events.append((message, target)), action)

        self.assertEqual(events, [("reading file", "vibeagent/agent.py")])


if __name__ == "__main__":
    unittest.main()
