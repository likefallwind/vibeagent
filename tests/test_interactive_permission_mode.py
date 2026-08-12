from __future__ import annotations

import unittest

from vibeagent.interactive_permission_mode import (
    initial_interactive_permission_state,
    update_interactive_permission_state,
)
from vibeagent.workspace_permissions import ProjectPermissions, permission_rules_from_values


class InteractivePermissionModeTests(unittest.TestCase):
    def test_default_cycle_adds_and_removes_accept_edits_rules(self) -> None:
        baseline = ProjectPermissions(
            rules=permission_rules_from_values("deny", ("Bash(git push:*)",), "baseline"),
            sources=("baseline",),
        )
        state = initial_interactive_permission_state(
            permission_mode=None,
            approval_policy="ask",
            permission_overrides=baseline,
            allow_bypass=False,
        )

        accept_edits, _ = update_interactive_permission_state(state, "next")
        plan, _ = update_interactive_permission_state(accept_edits, "next")
        automatic, _ = update_interactive_permission_state(plan, "next")

        self.assertEqual(accept_edits.mode, "acceptEdits")
        self.assertEqual(accept_edits.approval_policy, "ask")
        self.assertEqual(
            [rule.raw for rule in accept_edits.permission_overrides.rules],
            ["Bash(git push:*)", "Write", "Edit", "MultiEdit", "NotebookEdit"],
        )
        self.assertEqual(plan.mode, "plan")
        self.assertEqual([rule.raw for rule in plan.permission_overrides.rules], ["Bash(git push:*)"])
        self.assertEqual(automatic.mode, "auto")

    def test_bypass_requires_startup_unlock_and_joins_cycle_after_plan(self) -> None:
        locked = initial_interactive_permission_state(
            permission_mode="plan",
            approval_policy="plan",
            permission_overrides=ProjectPermissions(),
            allow_bypass=False,
        )
        unchanged, warning = update_interactive_permission_state(locked, "allow")
        unlocked = initial_interactive_permission_state(
            permission_mode="plan",
            approval_policy="plan",
            permission_overrides=ProjectPermissions(),
            allow_bypass=True,
        )
        bypass, _ = update_interactive_permission_state(unlocked, "cycle")

        self.assertEqual(unchanged, locked)
        self.assertIn("--allow-dangerously-skip-permissions", warning)
        self.assertEqual(bypass.mode, "bypassPermissions")
        self.assertEqual(bypass.approval_policy, "allow")

    def test_initial_accept_edits_replaces_cli_rule_source(self) -> None:
        cli_rules = permission_rules_from_values(
            "allow",
            ("Write", "Edit", "MultiEdit", "NotebookEdit"),
            "<cli --permission-mode acceptEdits>",
        )
        state = initial_interactive_permission_state(
            permission_mode="acceptEdits",
            approval_policy="ask",
            permission_overrides=ProjectPermissions(
                rules=cli_rules,
                sources=("<cli --permission-mode acceptEdits>",),
                trusted_allow_sources=("<cli --permission-mode acceptEdits>",),
            ),
            allow_bypass=False,
        )

        self.assertEqual(state.mode, "acceptEdits")
        self.assertEqual(len(state.permission_overrides.rules), 4)
        self.assertTrue(
            all("interactive permission-mode" in rule.source for rule in state.permission_overrides.rules)
        )


if __name__ == "__main__":
    unittest.main()
