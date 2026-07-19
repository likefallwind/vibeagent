from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from vibeagent.cli_project_command_expansion import (
    expand_code_task_project_command,
    expand_one_shot_project_command,
    project_command_task_metadata,
)


def _write_command(root: Path, relative_name: str, body: str) -> Path:
    path = root / ".claude" / "commands" / f"{relative_name}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\ndescription: Project command\n---\n\n{body}\n", encoding="utf-8")
    return path


class CliProjectCommandExpansionTests(unittest.TestCase):
    def test_one_shot_expands_custom_command_with_metadata(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-command-expand-") as base:
            root = Path(base)
            _write_command(root, "fix", "Fix $1 in $2")

            task, metadata = expand_one_shot_project_command(root, '/fix "login bug" app.py')

        self.assertEqual(task, "Fix login bug in app.py")
        self.assertEqual(
            metadata,
            {
                "source": "project_command",
                "name": "fix",
                "path": ".claude/commands/fix.md",
                "arguments": '"login bug" app.py',
            },
        )

    def test_non_project_command_tasks_pass_through(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-command-expand-") as base:
            root = Path(base)

            task, metadata = expand_one_shot_project_command(root, "fix the test")

        self.assertEqual(task, "fix the test")
        self.assertIsNone(metadata)

    def test_builtin_slash_commands_take_precedence_over_custom_commands(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-command-expand-") as base:
            root = Path(base)
            _write_command(root, "help", "This must not replace built-in help.")

            task, metadata = expand_one_shot_project_command(root, "/help")
            expanded = expand_code_task_project_command(root, "/help")

        self.assertEqual(task, "/help")
        self.assertIsNone(metadata)
        self.assertIsNone(expanded)

    def test_code_task_expansion_returns_raw_command_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-command-expand-") as base:
            root = Path(base)
            _write_command(root, "release", "Prepare release for $ARGUMENTS")

            command = expand_code_task_project_command(root, "/release v1")

        self.assertIsNotNone(command)
        assert command is not None
        self.assertEqual(command["name"], "release")
        self.assertEqual(command["prompt"], "Prepare release for v1")
        self.assertEqual(project_command_task_metadata(command)["arguments"], "v1")


if __name__ == "__main__":
    unittest.main()
