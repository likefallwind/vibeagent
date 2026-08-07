from __future__ import annotations

import unittest

from vibeagent import agent_completion_details, agent_completion_target_normalization, agent_completion_targets
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
        self.assertIs(
            agent_completion_targets.normalized_approval_target_tokens,
            agent_completion_target_normalization.normalized_approval_target_tokens,
        )
        self.assertIs(
            agent_completion_targets.should_preserve_approval_target,
            agent_completion_target_normalization.should_preserve_approval_target,
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

    def test_approval_target_normalization_preserves_structured_targets(self) -> None:
        self.assertEqual(
            agent_completion_target_normalization.normalized_approval_target_tokens("src/app.py:10-12"),
            {"src/app.py:10-12"},
        )
        self.assertEqual(
            agent_completion_target_normalization.normalized_approval_target_tokens("old_name -> new_name in src/app.py"),
            {"old_name -> new_name in src/app.py"},
        )
        self.assertEqual(
            agent_completion_target_normalization.normalized_approval_target_tokens("src/a.py, src/b.py"),
            {"src/a.py, src/b.py"},
        )


if __name__ == "__main__":
    unittest.main()
