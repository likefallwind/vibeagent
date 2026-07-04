import unittest
from dataclasses import dataclass

from vibeagent.agent_approval_targets import (
    command_batch_target,
    command_target,
    focused_test_commands_target,
    session_verification_target,
    suggested_checks_target,
)
from vibeagent.verification_command_utils import verification_command_label


@dataclass
class CommandLike:
    command: str
    cwd: str = "."


class AgentApprovalTargetsTests(unittest.TestCase):
    def test_command_target_defaults_empty_cwd_to_project_root(self) -> None:
        self.assertEqual(command_target("npm test", ""), "npm test (cwd: .)")

    def test_command_batch_target_skips_blank_commands(self) -> None:
        self.assertEqual(
            command_batch_target(
                [
                    CommandLike("python -m unittest", "."),
                    CommandLike("", "web"),
                    CommandLike("npm test", "web"),
                ]
            ),
            "python -m unittest (cwd: .), npm test (cwd: web)",
        )

    def test_verification_command_label_omits_root_cwd_only(self) -> None:
        self.assertEqual(verification_command_label("npm test", "."), "npm test")
        self.assertEqual(verification_command_label("npm test", ""), "npm test")
        self.assertEqual(verification_command_label("npm test", "web"), "npm test (cwd: web)")

    def test_verification_runner_targets_match_approval_copy(self) -> None:
        self.assertEqual(suggested_checks_target(2), "up to 2 suggested check command(s)")
        self.assertEqual(focused_test_commands_target(3), "up to 3 focused test command(s)")
        self.assertEqual(
            session_verification_target("run-1", include_failed=True, include_pending=True),
            "failed/pending verification command(s) from run-1",
        )
        self.assertEqual(
            session_verification_target(None, include_failed=False, include_pending=True),
            "pending verification command(s) from current session",
        )


if __name__ == "__main__":
    unittest.main()
