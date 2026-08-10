from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from vibeagent.actions import execute_action, parse_tool_action
from vibeagent.agent_runtime_utils import append_session_event
from vibeagent.goal_state import new_goal, read_goal, write_goal
from vibeagent.session_additional_directories import restore_session_additional_directories
from vibeagent.session_branching import (
    create_session_branch,
    read_session_branch_info,
    resolve_session_reference,
    unstarted_branch_lineage,
)
from vibeagent.session_handoff_commands import build_session_resume_context
from vibeagent.session_readiness_commands import get_resume_context
from vibeagent.session import build_sessions_report, format_sessions
from vibeagent.session_store import read_session_events
from vibeagent.session_tasks import read_task_store
from vibeagent.scheduled_task_store import list_scheduled_tasks
from vibeagent.workspace_core import create_run_workspace


class SessionBranchingTests(unittest.TestCase):
    def test_branch_copies_session_state_without_mutating_source(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-branch-") as base:
            root = Path(base) / "project"
            shared = Path(base) / "shared"
            root.mkdir()
            shared.mkdir()
            source = create_run_workspace(root, "source-run")
            append_session_event(
                source.session_dir,
                "task",
                {"task": "implement auth", "additional_directories": [str(shared.resolve())]},
            )
            execute_action(
                source,
                parse_tool_action(
                    "TaskCreate",
                    {"subject": "Implement auth", "description": "Add login flow"},
                ),
            )
            execute_action(
                source,
                parse_tool_action(
                    "CronCreate",
                    {"cron": "0 * * * *", "prompt": "check branch", "recurring": True},
                ),
            )
            goal = new_goal("authentication works", now=10)
            write_goal(source, goal)
            source_events = source.session_dir.joinpath("events.jsonl").read_bytes()

            branch = create_session_branch(
                root,
                source.run_id,
                name="try-oauth",
            )

            info = read_session_branch_info(root, branch.workspace.run_id)
            restored_dirs = restore_session_additional_directories(root, branch.workspace.run_id)
            self.assertEqual(source.session_dir.joinpath("events.jsonl").read_bytes(), source_events)
            self.assertEqual(info.source_run_id, source.run_id)  # type: ignore[union-attr]
            self.assertEqual(info.name, "try-oauth")  # type: ignore[union-attr]
            self.assertEqual(read_task_store(branch.workspace).tasks[0].subject, "Implement auth")
            self.assertEqual(list_scheduled_tasks(branch.workspace).tasks[0].prompt, "check branch")
            self.assertEqual(read_goal(branch.workspace), goal)
            self.assertEqual(restored_dirs.directories, (shared.resolve(),))
            self.assertEqual(resolve_session_reference(root, "try-oauth"), branch.workspace.run_id)
            selected, context, _ = get_resume_context("try-oauth", root)
            self.assertEqual(selected, branch.workspace.run_id)
            self.assertIn("implement auth", context or "")
            sessions_text = format_sessions(root)
            sessions_report = build_sessions_report(root)
            self.assertIn("branch=source-run name=try-oauth", sessions_text)
            branch_item = next(
                item
                for item in sessions_report["sessions"]["items"]
                if item["session"] == branch.workspace.run_id
            )
            self.assertEqual(branch_item["branch"], {"sourceSession": "source-run", "name": "try-oauth"})

    def test_unstarted_branch_resume_uses_parent_context_then_own_context_after_task(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-branch-") as base:
            root = Path(base)
            source = create_run_workspace(root, "source-run")
            append_session_event(source.session_dir, "task", {"task": "parent task"})
            branch = create_session_branch(root, source.run_id)

            inherited = build_session_resume_context(root, branch.workspace.run_id)
            lineage = unstarted_branch_lineage(root, branch.workspace.run_id)
            append_session_event(branch.workspace.session_dir, "task", {"task": "branch task"})
            own = build_session_resume_context(root, branch.workspace.run_id)

        self.assertEqual(lineage, ((branch.workspace.run_id,), source.run_id))
        self.assertIn(f"branchLineage: {branch.workspace.run_id} -> {source.run_id}", inherited)
        self.assertIn("parent task", inherited)
        self.assertNotIn("branchLineage:", own)
        self.assertIn("branch task", own)

    def test_rejects_duplicate_names_invalid_sources_and_lineage_cycles(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-branch-") as base:
            root = Path(base)
            source = create_run_workspace(root, "source-run")
            append_session_event(source.session_dir, "task", {"task": "parent"})
            create_session_branch(root, source.run_id, name="experiment")

            with self.assertRaisesRegex(ValueError, "already in use"):
                create_session_branch(root, source.run_id, name="experiment")
            with self.assertRaisesRegex(ValueError, "Invalid source session id"):
                create_session_branch(root, "../outside")
            with self.assertRaisesRegex(ValueError, "control characters"):
                create_session_branch(root, source.run_id, name="bad\nname")
            with self.assertRaisesRegex(ValueError, "reserved"):
                create_session_branch(root, source.run_id, name="latest")

            first = create_run_workspace(root, "cycle-a")
            second = create_run_workspace(root, "cycle-b")
            append_session_event(first.session_dir, "session_branched", {"source_run_id": "cycle-b", "name": None})
            append_session_event(second.session_dir, "session_branched", {"source_run_id": "cycle-a", "name": None})
            with self.assertRaisesRegex(ValueError, "cycle"):
                unstarted_branch_lineage(root, first.run_id)

    def test_malformed_branch_metadata_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-branch-") as base:
            root = Path(base)
            workspace = create_run_workspace(root, "bad-branch")
            append_session_event(
                workspace.session_dir,
                "session_branched",
                {"source_run_id": "../outside", "name": None},
            )

            with self.assertRaisesRegex(ValueError, "malformed branch metadata"):
                read_session_branch_info(root, workspace.run_id)
            self.assertIn("bad-branch", format_sessions(root))
            self.assertTrue(build_sessions_report(root)["ok"])

            source = create_run_workspace(root, "source-run")
            append_session_event(source.session_dir, "task", {"task": "source"})
            valid = create_session_branch(root, source.run_id, name="valid-name")
            self.assertEqual(resolve_session_reference(root, "valid-name"), valid.workspace.run_id)

    def test_rejects_nonempty_explicit_target_workspace(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-branch-") as base:
            root = Path(base)
            source = create_run_workspace(root, "source-run")
            append_session_event(source.session_dir, "task", {"task": "source"})
            target = create_run_workspace(root, "target-run")
            (target.session_dir / "unexpected.txt").write_text("occupied\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "target is not empty"):
                create_session_branch(root, source.run_id, workspace=target)


if __name__ == "__main__":
    unittest.main()
