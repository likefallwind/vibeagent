from __future__ import annotations

from argparse import Namespace
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from vibeagent.agent_runtime_utils import append_session_event
from vibeagent.cli_startup_context import resolve_interactive_startup_context
from vibeagent.session_names import read_session_name
from vibeagent.session_conversation import checkpoint_session_conversation
from vibeagent.types import ChatMessage
from vibeagent.workspace_core import create_local_workspace


def _args(**overrides) -> Namespace:
    values = {
        "agent": None,
        "agents": None,
        "add_dir": [],
        "system_prompt": None,
        "system_prompt_file": None,
        "append_system_prompt": None,
        "append_system_prompt_file": None,
        "resume": None,
        "session_id": None,
        "compact": None,
        "resume_max_failures": None,
        "resume_max_files": None,
        "resume_max_commands": None,
        "resume_max_checks": None,
        "resume_max_output_chars": None,
        "resume_max_text": None,
        "compact_max_failures": None,
        "compact_max_files": None,
        "compact_max_commands": None,
        "compact_max_checks": None,
        "compact_max_output_chars": None,
        "compact_max_text": None,
        "fork_session": False,
        "name": None,
        "autocompact": None,
    }
    values.update(overrides)
    return Namespace(**values)


class CliStartupContextTests(unittest.TestCase):
    def test_autocompact_is_forwarded_for_interactive_startup(self) -> None:
        context = resolve_interactive_startup_context(
            _args(autocompact=200_000),
            Path.cwd(),
            get_resume_context_func=Mock(),
            get_compact_context_func=Mock(),
        )

        self.assertEqual(context.autocompact_tokens, 200_000)

    def test_dynamic_agents_are_validated_for_interactive_startup(self) -> None:
        context = resolve_interactive_startup_context(
            _args(
                agents=(
                    '{"reviewer":{"description":"Reviews code",'
                    '"prompt":"Inspect evidence only","tools":["Read"]}}'
                )
            ),
            Path.cwd(),
            get_resume_context_func=Mock(),
            get_compact_context_func=Mock(),
        )

        self.assertEqual(len(context.dynamic_agent_profiles), 1)
        self.assertEqual(context.dynamic_agent_profiles[0].name, "reviewer")

    def test_name_creates_a_pending_interactive_session(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-startup-name-") as base:
            root = Path(base)

            context = resolve_interactive_startup_context(
                _args(name="auth-refactor"),
                root,
                get_resume_context_func=Mock(),
                get_compact_context_func=Mock(),
            )

            self.assertIsNone(context.error)
            self.assertIsNotNone(context.pending_workspace)
            self.assertEqual(read_session_name(root, context.run_id), "auth-refactor")  # type: ignore[arg-type]
            self.assertIn("Session named: auth-refactor", context.message or "")

    def test_name_with_resume_renames_the_continued_session(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-startup-name-") as base:
            root = Path(base)
            append_session_event(root / ".vibeagent" / "sessions" / "source", "task", {"task": "source"})

            context = resolve_interactive_startup_context(
                _args(name="continued-work", resume="source"),
                root,
                get_resume_context_func=Mock(return_value=("source", "context", "Loaded source.")),
                get_compact_context_func=Mock(),
            )

            self.assertEqual(context.run_id, "source")
            self.assertIsNotNone(context.pending_workspace)
            self.assertEqual(context.pending_workspace.run_id, "source")  # type: ignore[union-attr]
            self.assertEqual(read_session_name(root, "source"), "continued-work")

    def test_resume_restores_session_additional_directories(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-startup-dirs-") as base:
            root = Path(base) / "project"
            shared = Path(base) / "shared"
            root.mkdir()
            shared.mkdir()
            append_session_event(
                root / ".vibeagent" / "sessions" / "run-1",
                "task",
                {"additional_directories": [str(shared.resolve())]},
            )
            resume = Mock(return_value=("run-1", "context", "Resume loaded."))

            context = resolve_interactive_startup_context(
                _args(resume="run-1"),
                root,
                get_resume_context_func=resume,
                get_compact_context_func=Mock(),
            )

        self.assertEqual(context.additional_directories, (shared.resolve(),))
        self.assertIsNone(context.error)
        self.assertEqual(context.pending_workspace.run_id, "run-1")  # type: ignore[union-attr]

    def test_resume_restores_persisted_conversation_but_compact_does_not(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-startup-conversation-") as base:
            root = Path(base)
            workspace = create_local_workspace(root, "run-1")
            workspace.session_dir.mkdir(parents=True)
            checkpoint_session_conversation(
                workspace,
                [
                    ChatMessage(role="user", content="User task:\nfirst"),
                    ChatMessage(role="assistant", content="remember this"),
                ],
                "first",
            )

            resumed = resolve_interactive_startup_context(
                _args(resume="run-1"),
                root,
                get_resume_context_func=Mock(return_value=("run-1", "context", "Resume loaded.")),
                get_compact_context_func=Mock(),
            )
            compacted = resolve_interactive_startup_context(
                _args(compact="run-1"),
                root,
                get_resume_context_func=Mock(),
                get_compact_context_func=Mock(return_value=("run-1", "context", "Compact loaded.")),
            )

        self.assertEqual(resumed.conversation[-1].content, "remember this")
        self.assertEqual(compacted.conversation, ())

    def test_compact_merges_cli_and_session_additional_directories(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-startup-dirs-") as base:
            root = Path(base) / "project"
            shared = Path(base) / "shared"
            explicit = Path(base) / "explicit"
            root.mkdir()
            shared.mkdir()
            explicit.mkdir()
            append_session_event(
                root / ".vibeagent" / "sessions" / "run-1",
                "task",
                {"additional_directories": [str(shared.resolve())]},
            )
            compact = Mock(return_value=("run-1", "context", "Compact loaded."))

            context = resolve_interactive_startup_context(
                _args(compact="run-1", add_dir=[str(explicit)]),
                root,
                get_resume_context_func=Mock(),
                get_compact_context_func=compact,
            )

        self.assertEqual(context.additional_directories, (explicit.resolve(), shared.resolve()))
        self.assertIsNone(context.error)

    def test_resume_fork_creates_pending_branch_workspace(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-startup-branch-") as base:
            root = Path(base)
            source_dir = root / ".vibeagent" / "sessions" / "run-1"
            append_session_event(source_dir, "task", {"task": "source task"})
            original = source_dir.joinpath("events.jsonl").read_bytes()

            context = resolve_interactive_startup_context(
                _args(resume="run-1", fork_session=True),
                root,
                get_resume_context_func=Mock(return_value=("run-1", "source context", "Resume loaded.")),
                get_compact_context_func=Mock(),
            )

            self.assertIsNone(context.error)
            self.assertIsNotNone(context.pending_workspace)
            self.assertNotEqual(context.run_id, "run-1")
            self.assertEqual(context.branch_source_run_id, "run-1")
            self.assertEqual(source_dir.joinpath("events.jsonl").read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
