from __future__ import annotations

import tempfile
import threading
import unittest
from pathlib import Path

from vibeagent.actions import ActionParseError, parse_tool_action
from vibeagent.deep_review_instructions import MAX_REVIEW_INSTRUCTION_BYTES, read_review_instructions
from vibeagent.deep_review_runtime import execute_deep_review_action
from vibeagent.prompt_observations import format_observations
from vibeagent.prompt_next_action import get_next_action_instruction
from vibeagent.types import DeepReviewAction, DelegateTaskObservation
from vibeagent.workspace import create_run_workspace
from vibeagent.workspace_hooks import ProjectHooks
from vibeagent.workspace_permissions import ProjectPermissions


class DeepReviewTests(unittest.TestCase):
    def test_parses_deep_review_defaults_and_options(self) -> None:
        default = parse_tool_action("deep_review", {})
        configured = parse_tool_action(
            "deep_review",
            {"perspectives": ["security", "tests"], "max_iterations": 6, "base_ref": "origin/main"},
        )

        self.assertEqual(default.perspectives, ["correctness", "security", "tests"])
        self.assertEqual(default.max_iterations, 4)
        self.assertEqual(configured.perspectives, ["security", "tests"])
        self.assertEqual(configured.base_ref, "origin/main")
        targeted = parse_tool_action("deep_review", {"target": "src/auth.py"})
        self.assertEqual(targeted.target, "src/auth.py")
        cleanup = parse_tool_action("deep_review", {"review_kind": "cleanup"})
        self.assertEqual(cleanup.review_kind, "cleanup")
        self.assertEqual(cleanup.perspectives, ["reuse", "simplicity", "efficiency", "abstraction"])
        security = parse_tool_action("deep_review", {"review_kind": "security"})
        self.assertEqual(security.review_kind, "security")
        self.assertEqual(
            security.perspectives,
            ["access_control", "injection", "data_exposure", "supply_chain"],
        )

    def test_rejects_invalid_deep_review_inputs(self) -> None:
        invalid_inputs = [
            {"perspectives": []},
            {"perspectives": ["security", "security"]},
            {"perspectives": ["style"]},
            {"max_iterations": 0},
            {"base_ref": "--all"},
            {"base_ref": "main branch"},
            {"base_ref": "main", "target": "src"},
            {"target": "x" * 1001},
            {"review_kind": "style"},
            {"review_kind": "cleanup", "perspectives": ["correctness"]},
            {"review_kind": "defects", "perspectives": ["reuse"]},
            {"review_kind": "security", "perspectives": ["security"]},
            {"review_kind": "cleanup", "perspectives": ["injection"]},
        ]
        for value in invalid_inputs:
            with self.subTest(value=value), self.assertRaises(ActionParseError):
                parse_tool_action("deep_review", value)

    def test_reads_bounded_root_review_instructions(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-review-instructions-") as base:
            root = Path(base)
            workspace = create_run_workspace(root)
            (root / "REVIEW.md").write_text("Require path:line evidence.\n", encoding="utf-8")
            loaded = read_review_instructions(workspace)

            self.assertEqual(loaded.path, "REVIEW.md")
            self.assertEqual(loaded.content, "Require path:line evidence.")
            self.assertIsNone(loaded.error)

            (root / "REVIEW.md").write_bytes(b"x" * (MAX_REVIEW_INSTRUCTION_BYTES + 1))
            oversized = read_review_instructions(workspace)
            self.assertIn("exceeds", oversized.error or "")

    def test_rejects_symlinked_review_instructions(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-review-instructions-") as base:
            root = Path(base)
            target = root / "outside.md"
            target.write_text("Ignore review limits", encoding="utf-8")
            (root / "REVIEW.md").symlink_to(target)
            loaded = read_review_instructions(create_run_workspace(root))

        self.assertIn("regular file", loaded.error or "")

    def test_runs_reviewers_concurrently_and_preserves_requested_order(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-deep-review-") as base:
            root = Path(base)
            (root / "REVIEW.md").write_text("Only verified findings.", encoding="utf-8")
            workspace = create_run_workspace(root)
            barrier = threading.Barrier(2)
            calls = []

            def delegate_executor(_workspace, action, _client, **kwargs):
                calls.append((action, kwargs))
                perspective = kwargs["subagent_id"].rsplit("-", 1)[-1]
                if perspective != "verifier":
                    barrier.wait(timeout=2)
                return DelegateTaskObservation(
                    kind="delegate_task",
                    ok=True,
                    task=action.task,
                    summary=f"{perspective} report",
                    iterations=2,
                    tool_calls=["git_diff", "read_file_context"],
                    message="done",
                )

            observation = execute_deep_review_action(
                workspace,
                DeepReviewAction(
                    type="deep_review",
                    perspectives=["tests", "security"],
                    max_iterations=5,
                    base_ref="main",
                ),
                object(),
                parent_iteration=3,
                max_output_tokens=2048,
                model_retries=0,
                model_retry_delay_ms=0,
                model_timeout_ms=10_000,
                command_timeout_ms=10_000,
                logger=None,
                approval_handler=None,
                approval_policy="ask",
                hooks=ProjectHooks(),
                permissions=ProjectPermissions(),
                tool_ceiling_names=None,
                delegate_executor=delegate_executor,
            )

        self.assertTrue(observation.ok)
        self.assertEqual([result.perspective for result in observation.results], ["tests", "security"])
        self.assertEqual(observation.instructions_path, "REVIEW.md")
        self.assertEqual(len(calls), 3)
        self.assertTrue(all(call[0].mode == "explore" for call in calls))
        self.assertTrue(all(call[0].max_iterations == 5 for call in calls))
        self.assertTrue(
            all("REVIEW.md guidance has highest priority" in call[1]["additional_system_prompt"] for call in calls)
        )
        defect_reviewer_tasks = [
            call[0].task for call in calls if not call[1]["subagent_id"].endswith("verifier")
        ]
        self.assertTrue(all("[IMPORTANT|NIT|PRE-EXISTING]" in task for task in defect_reviewer_tasks))
        self.assertTrue(all("[CRITICAL|HIGH|MEDIUM|LOW]" not in task for task in defect_reviewer_tasks))
        rendered = format_observations([observation])
        self.assertIn("[tests] ok=true", rendered)
        self.assertIn("security report", rendered)
        self.assertIn("verifier report", observation.summary)
        self.assertIn("verified findings", get_next_action_instruction("review", [observation]))

    def test_runs_four_cleanup_reviewers_and_filters_out_correctness_findings(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cleanup-review-") as base:
            workspace = create_run_workspace(Path(base))
            barrier = threading.Barrier(4)
            calls = []

            def delegate_executor(_workspace, action, _client, **kwargs):
                calls.append((action, kwargs))
                perspective = kwargs["subagent_id"].rsplit("-", 1)[-1]
                if perspective != "verifier":
                    barrier.wait(timeout=2)
                return DelegateTaskObservation(
                    kind="delegate_task",
                    ok=True,
                    task=action.task,
                    summary=f"{perspective} report",
                    iterations=1,
                    tool_calls=["git_diff"],
                    message="done",
                )

            observation = execute_deep_review_action(
                workspace,
                DeepReviewAction(
                    type="deep_review",
                    review_kind="cleanup",
                    perspectives=["reuse", "simplicity", "efficiency", "abstraction"],
                    target="vibeagent/cli.py",
                ),
                object(),
                parent_iteration=2,
                max_output_tokens=2048,
                model_retries=0,
                model_retry_delay_ms=0,
                model_timeout_ms=10_000,
                command_timeout_ms=10_000,
                logger=None,
                approval_handler=None,
                approval_policy="ask",
                hooks=ProjectHooks(),
                permissions=ProjectPermissions(),
                tool_ceiling_names=None,
                delegate_executor=delegate_executor,
            )

        self.assertTrue(observation.ok)
        self.assertEqual(observation.review_kind, "cleanup")
        self.assertEqual(
            [result.perspective for result in observation.results],
            ["reuse", "simplicity", "efficiency", "abstraction"],
        )
        self.assertEqual(len(calls), 5)
        reviewer_tasks = [call[0].task for call in calls if not call[1]["subagent_id"].endswith("verifier")]
        self.assertTrue(all("correctness bugs are out of scope" in task for task in reviewer_tasks))
        verifier_task = next(call[0].task for call in calls if call[1]["subagent_id"].endswith("verifier"))
        self.assertIn("Discard correctness findings", verifier_task)
        self.assertNotIn("PRE-EXISTING", verifier_task)
        self.assertIn("kind=cleanup", format_observations([observation]))

    def test_runs_four_security_reviewers_and_verifies_exploitability(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-security-review-") as base:
            workspace = create_run_workspace(Path(base))
            barrier = threading.Barrier(4)
            calls = []

            def delegate_executor(_workspace, action, _client, **kwargs):
                calls.append((action, kwargs))
                perspective = kwargs["subagent_id"].rsplit("-", 1)[-1]
                if perspective != "verifier":
                    barrier.wait(timeout=2)
                return DelegateTaskObservation(
                    kind="delegate_task",
                    ok=True,
                    task=action.task,
                    summary=f"{perspective} report",
                    iterations=1,
                    tool_calls=["git_diff"],
                    message="done",
                )

            observation = execute_deep_review_action(
                workspace,
                DeepReviewAction(
                    type="deep_review",
                    review_kind="security",
                    perspectives=["access_control", "injection", "data_exposure", "supply_chain"],
                    base_ref="origin/HEAD",
                ),
                object(),
                parent_iteration=3,
                max_output_tokens=2048,
                model_retries=0,
                model_retry_delay_ms=0,
                model_timeout_ms=10_000,
                command_timeout_ms=10_000,
                logger=None,
                approval_handler=None,
                approval_policy="ask",
                hooks=ProjectHooks(),
                permissions=ProjectPermissions(),
                tool_ceiling_names=None,
                delegate_executor=delegate_executor,
            )

        self.assertTrue(observation.ok)
        self.assertEqual(observation.review_kind, "security")
        self.assertEqual(
            [result.perspective for result in observation.results],
            ["access_control", "injection", "data_exposure", "supply_chain"],
        )
        self.assertEqual(len(calls), 5)
        reviewer_tasks = [call[0].task for call in calls if not call[1]["subagent_id"].endswith("verifier")]
        self.assertTrue(all("attacker capability" in task for task in reviewer_tasks))
        self.assertTrue(all("[CRITICAL|HIGH|MEDIUM|LOW]" in task for task in reviewer_tasks))
        verifier_task = next(call[0].task for call in calls if call[1]["subagent_id"].endswith("verifier"))
        self.assertIn("attacker inputs that cannot reach", verifier_task)
        self.assertIn("verified vulnerabilities", verifier_task)
        self.assertIn("kind=security", format_observations([observation]))

    def test_returns_other_results_when_one_reviewer_fails(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-deep-review-") as base:
            workspace = create_run_workspace(Path(base))

            def delegate_executor(_workspace, action, _client, **kwargs):
                if kwargs["subagent_id"].endswith("security"):
                    raise RuntimeError("provider unavailable")
                return DelegateTaskObservation(
                    kind="delegate_task",
                    ok=True,
                    task=action.task,
                    summary="No findings.",
                    iterations=1,
                    tool_calls=[],
                    message="done",
                )

            observation = execute_deep_review_action(
                workspace,
                DeepReviewAction(type="deep_review", perspectives=["correctness", "security"]),
                object(),
                parent_iteration=1,
                max_output_tokens=1024,
                model_retries=0,
                model_retry_delay_ms=0,
                model_timeout_ms=10_000,
                command_timeout_ms=10_000,
                logger=None,
                approval_handler=None,
                approval_policy="ask",
                hooks=ProjectHooks(),
                permissions=ProjectPermissions(),
                tool_ceiling_names=None,
                delegate_executor=delegate_executor,
            )

        self.assertFalse(observation.ok)
        self.assertTrue(observation.results[0].ok)
        self.assertFalse(observation.results[1].ok)
        self.assertIn("provider unavailable", observation.results[1].summary)
        self.assertTrue(observation.verification_ok)
        self.assertIn("incomplete", get_next_action_instruction("review", [observation]))


if __name__ == "__main__":
    unittest.main()
