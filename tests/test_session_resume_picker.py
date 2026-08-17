from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout
import io
from unittest.mock import patch

from vibeagent.agent_runtime_utils import append_session_event
from vibeagent.cli_args import parse_args
from vibeagent.cli import main
from vibeagent.session_names import name_session
from vibeagent.session_resume_picker import (
    MAX_RESUME_PICKER_EVENT_BYTES,
    list_resume_session_candidates,
    prepare_session_resume,
    prompt_resume_session,
    resolve_exact_resume_reference,
    rewrite_resume_picker_arguments,
)
from vibeagent.workspace_core import create_run_workspace


class SessionResumePickerTests(unittest.TestCase):
    def test_lists_newest_sessions_and_searches_names_tasks_and_status(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-resume-picker-") as base:
            root = Path(base)
            older = create_run_workspace(root, "older-run")
            newer = create_run_workspace(root, "newer-run")
            append_session_event(older.session_dir, "task", {"task": "Update documentation"})
            append_session_event(newer.session_dir, "task", {"task": "Fix authentication flow"})
            name_session(root, "newer-run", "修复登录")
            os.utime(older.session_dir / "events.jsonl", (1, 1))
            os.utime(newer.session_dir / "events.jsonl", (2, 2))

            candidates = list_resume_session_candidates(root)
            named = list_resume_session_candidates(root, "修复")
            tasked = list_resume_session_candidates(root, "authentication")
            status = list_resume_session_candidates(root, "incomplete")

        self.assertEqual([item.run_id for item in candidates], ["newer-run", "older-run"])
        self.assertEqual([item.run_id for item in named], ["newer-run"])
        self.assertEqual([item.run_id for item in tasked], ["newer-run"])
        self.assertEqual([item.run_id for item in status], ["newer-run", "older-run"])

    def test_candidate_search_is_bounded_and_validated(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-resume-picker-") as base:
            root = Path(base)
            for number in range(3):
                workspace = create_run_workspace(root, f"run-{number}")
                append_session_event(workspace.session_dir, "task", {"task": f"Task {number}"})
                os.utime(workspace.session_dir / "events.jsonl", (number + 1, number + 1))

            self.assertEqual(len(list_resume_session_candidates(root, result_limit=2)), 2)
            with self.assertRaisesRegex(ValueError, "positive"):
                list_resume_session_candidates(root, scan_limit=0)
            with self.assertRaisesRegex(ValueError, "control"):
                list_resume_session_candidates(root, "bad\nquery")

    def test_picker_skips_oversized_event_row_without_losing_later_metadata(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-resume-picker-") as base:
            root = Path(base)
            workspace = create_run_workspace(root, "run-one")
            append_session_event(workspace.session_dir, "task", {"task": "Initial task"})
            with (workspace.session_dir / "events.jsonl").open("ab") as stream:
                stream.write(b"{" + b"x" * MAX_RESUME_PICKER_EVENT_BYTES + b"\n")
            append_session_event(
                workspace.session_dir,
                "session_named",
                {"name": "after-large-row"},
            )

            candidates = list_resume_session_candidates(root, "after-large-row")

        self.assertEqual([item.run_id for item in candidates], ["run-one"])
        self.assertEqual(candidates[0].session_name, "after-large-row")

    def test_resolves_only_exact_local_or_machine_session_references(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-resume-picker-") as base:
            root = Path(base)
            workspace = create_run_workspace(root, "run-one")
            append_session_event(workspace.session_dir, "task", {"task": "Fix auth"})
            name_session(root, "run-one", "auth-fix")

            self.assertEqual(resolve_exact_resume_reference(root, "run-one"), "run-one")
            self.assertEqual(resolve_exact_resume_reference(root, "auth-fix"), "run-one")
            self.assertEqual(resolve_exact_resume_reference(root, "latest"), "latest")
            self.assertEqual(resolve_exact_resume_reference(root, "off"), "off")
            generated = "2026-08-17T12-34-56-789Z-1234abcd"
            self.assertEqual(resolve_exact_resume_reference(root, generated), generated)
            self.assertIsNone(resolve_exact_resume_reference(root, "auth"))

    def test_prepare_resume_uses_picker_but_continue_and_exact_values_do_not(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-resume-picker-") as base:
            root = Path(base)
            workspace = create_run_workspace(root, "run-one")
            append_session_event(workspace.session_dir, "task", {"task": "Fix auth"})
            name_session(root, "run-one", "auth-fix")

            picker = parse_args(["--cwd", base, "--resume"])
            prepare_session_resume(
                picker,
                input_func=lambda _prompt: "1",
                print_func=lambda _line: None,
                terminal_available=True,
            )
            exact = parse_args(["--cwd", base, "--resume", "auth-fix"])
            prepare_session_resume(exact, terminal_available=False)
            continued = parse_args(["--cwd", base, "--continue"])
            with patch(
                "vibeagent.session_resume_picker.list_resume_session_candidates"
            ) as candidates:
                prepare_session_resume(continued, terminal_available=True)

        self.assertEqual(picker.resume, "run-one")
        self.assertTrue(picker.resume_from_picker)
        self.assertEqual(exact.resume, "run-one")
        self.assertEqual(continued.resume, "")
        candidates.assert_not_called()

    def test_prepare_resume_requires_interactive_text_for_picker(self) -> None:
        for argv in (["--resume"], ["--resume", "auth", "--json"]):
            with self.subTest(argv=argv):
                args = parse_args(argv)
                with self.assertRaisesRegex(ValueError, "interactive text terminal"):
                    prepare_session_resume(args, terminal_available=False)

    def test_main_reports_resume_conflicts_before_opening_picker(self) -> None:
        stdout = io.StringIO()
        with (
            patch(
                "vibeagent.session_resume_picker.list_resume_session_candidates"
            ) as candidates,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--resume", "auth", "--compact", "run-two"])

        self.assertEqual(exit_code, 2)
        self.assertIn("--resume and --compact cannot be used together", stdout.getvalue())
        candidates.assert_not_called()

    def test_prompt_retries_cancels_and_renders_terminal_safe_text(self) -> None:
        from vibeagent.session_resume_picker import ResumeSessionCandidate

        candidate = ResumeSessionCandidate(
            run_id="run-one",
            session_name=None,
            task="unsafe\x1b[31m task",
            status="incomplete",
            last_event_time=None,
        )
        answers = iter(["bad", "2", "1"])
        output: list[str] = []

        selected = prompt_resume_session(
            (candidate,),
            input_func=lambda _prompt: next(answers),
            print_func=output.append,
        )

        self.assertEqual(selected, "run-one")
        self.assertEqual(sum("Enter a number" in line for line in output), 2)
        self.assertIn("[escaped]", "\n".join(output))
        with self.assertRaisesRegex(ValueError, "cancelled"):
            prompt_resume_session(
                (candidate,),
                input_func=lambda _prompt: "",
                print_func=lambda _line: None,
            )

    def test_rewrites_picker_selector_for_child_processes(self) -> None:
        self.assertEqual(
            rewrite_resume_picker_arguments(
                ["--cwd", "/tmp/project", "--resume", "auth", "--", "continue"],
                "run-one",
            ),
            ["--resume", "run-one", "--cwd", "/tmp/project", "--", "continue"],
        )
        self.assertEqual(
            rewrite_resume_picker_arguments(["--resume=auth", "continue"], "run-one"),
            ["--resume", "run-one", "continue"],
        )


if __name__ == "__main__":
    unittest.main()
