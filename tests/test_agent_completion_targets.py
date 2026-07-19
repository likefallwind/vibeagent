from __future__ import annotations

import unittest

from vibeagent import agent_completion_details, agent_completion_targets
from vibeagent.types import ApprovalDeniedObservation, WriteFileObservation


class AgentCompletionTargetsTests(unittest.TestCase):
    def test_completion_details_reexports_target_helpers(self) -> None:
        self.assertIs(agent_completion_details.denied_approval_resolved, agent_completion_targets.denied_approval_resolved)
        self.assertIs(
            agent_completion_details.denied_approval_target_matches_observation,
            agent_completion_targets.denied_approval_target_matches_observation,
        )
        self.assertIs(agent_completion_details.observation_target_tokens, agent_completion_targets.observation_target_tokens)
        self.assertIs(
            agent_completion_details.normalized_approval_target_tokens,
            agent_completion_targets.normalized_approval_target_tokens,
        )

    def test_denied_project_change_is_resolved_by_later_matching_write(self) -> None:
        denied = ApprovalDeniedObservation(
            kind="approval_denied",
            action_type="write_file",
            target="src/app.py",
            message="Denied by policy.",
        )
        later = [
            WriteFileObservation(kind="write_file", path="src/app.py", ok=True, message="Wrote src/app.py"),
        ]

        self.assertTrue(agent_completion_targets.denied_approval_resolved(denied, later))
        self.assertIn("src/app.py", agent_completion_targets.observation_target_tokens(later[0]))


if __name__ == "__main__":
    unittest.main()
