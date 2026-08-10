from __future__ import annotations

from argparse import Namespace
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from vibeagent.agent_runtime_utils import append_session_event
from vibeagent.cli_startup_context import resolve_interactive_startup_context


def _args(**overrides) -> Namespace:
    values = {
        "agent": None,
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
    }
    values.update(overrides)
    return Namespace(**values)


class CliStartupContextTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
