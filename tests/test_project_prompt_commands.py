import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

from vibeagent.agent_result import AgentResult
from vibeagent.cli import main
from vibeagent.workspace_prompt_commands import (
    expand_project_prompt_command,
    format_project_prompt_commands,
    read_project_prompt_commands,
)


def _write_command(
    root: Path,
    base: str,
    relative_name: str,
    body: str,
    *,
    description: str = "Project command",
    argument_hint: str = "",
) -> Path:
    path = root / base / f"{relative_name}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    hint_line = f"argument-hint: {argument_hint}\n" if argument_hint else ""
    path.write_text(
        f"---\ndescription: {description}\n{hint_line}---\n\n{body}\n",
        encoding="utf-8",
    )
    return path


class ProjectPromptCommandTests(unittest.TestCase):
    def test_discovers_nested_metadata_without_template_body(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            _write_command(
                root,
                ".claude/commands",
                "review/security",
                "PRIVATE_COMMAND_BODY $ARGUMENTS",
                description="Review security boundaries",
                argument_hint="[path]",
            )

            report = read_project_prompt_commands(root)
            formatted = format_project_prompt_commands(root)

        self.assertEqual(report["total"], 1)
        self.assertEqual(report["invalid"], 0)
        self.assertEqual(report["commands"][0]["name"], "review:security")
        self.assertEqual(report["commands"][0]["argument_hint"], "[path]")
        self.assertNotIn("body", report["commands"][0])
        self.assertIn("/review:security [path]", formatted)
        self.assertNotIn("PRIVATE_COMMAND_BODY", formatted)

    def test_expands_all_arguments_positionals_and_escaped_dollars(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            _write_command(
                root,
                ".agents/commands",
                "fix",
                "Fix $1 in ${2}. Raw: $ARGUMENTS. Price: $$5. Unsupported: $10.",
            )

            expanded = expand_project_prompt_command(root, '/fix "login bug" src/app.py')

        self.assertEqual(
            expanded["prompt"],
            'Fix login bug in src/app.py. Raw: "login bug" src/app.py. Price: $5. Unsupported: $10.',
        )

    def test_appends_arguments_when_template_has_no_placeholder(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            _write_command(root, ".claude/commands", "explain", "Explain the selected code.")

            expanded = expand_project_prompt_command(root, "/explain src/app.py")

        self.assertEqual(expanded["prompt"], "Explain the selected code.\n\nArguments:\nsrc/app.py")

    def test_duplicate_symlink_and_empty_templates_are_unavailable(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            _write_command(root, ".claude/commands", "duplicate", "First")
            _write_command(root, ".agents/commands", "duplicate", "Second")
            _write_command(root, ".claude/commands", "empty", "")
            external = root / "outside.md"
            external.write_text("External", encoding="utf-8")
            linked = root / ".claude/commands/linked.md"
            linked.symlink_to(external)

            report = read_project_prompt_commands(root)

        messages = {str(command["name"]): str(command["message"]) for command in report["commands"]}
        self.assertIn("Duplicate project command", messages["duplicate"])
        self.assertIn("must not be empty", messages["empty"])
        self.assertIn("symbolic link", messages["linked"])
        self.assertEqual(report["invalid"], 4)

    def test_unknown_command_and_bad_quoted_arguments_return_errors(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            _write_command(root, ".claude/commands", "fix", "Fix $1")

            with self.assertRaisesRegex(ValueError, "Unknown command"):
                expand_project_prompt_command(root, "/missing")
            with self.assertRaisesRegex(ValueError, "arguments are invalid"):
                expand_project_prompt_command(root, '/fix "unterminated')

        self.assertIsNone(expand_project_prompt_command(Path("."), "/not/a/command"))


class ProjectPromptCommandCliTests(unittest.TestCase):
    def test_interactive_custom_command_expands_to_code_task_from_chat_mode(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            _write_command(root, ".claude/commands", "fix", "Fix $1 in $2")
            result = AgentResult(
                success=True,
                message="done",
                run_dir=root,
                run_id="run-1",
                iterations=1,
                observations=[],
                steps=[],
            )
            run_agent = Mock(return_value=result)
            stdout = io.StringIO()

            with (
                patch("builtins.input", side_effect=["/chat", '/fix "login bug" app.py', "/exit"]),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", run_agent),
                patch("vibeagent.cli.get_resume_context", return_value=(None, None, "")),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base])

        self.assertEqual(exit_code, 0)
        self.assertEqual(run_agent.call_args.args[0], "Fix login bug in app.py")
        self.assertEqual(
            run_agent.call_args.kwargs["task_metadata"],
            {
                "source": "project_command",
                "name": "fix",
                "path": ".claude/commands/fix.md",
                "arguments": '"login bug" app.py',
            },
        )
        self.assertIn("Chat mode", stdout.getvalue())

    def test_builtin_precedence_catalog_and_unknown_command_do_not_call_agent(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-commands-") as base:
            root = Path(base)
            _write_command(root, ".claude/commands", "help", "This must not replace built-in help.")
            _write_command(root, ".claude/commands", "release", "Prepare a release.")
            run_agent = Mock()
            stdout = io.StringIO()

            with (
                patch("builtins.input", side_effect=["/help", "/custom-commands", "/missing", "/exit"]),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base])

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Commands:", output)
        self.assertIn("/release", output)
        self.assertIn("/help [invalid", output)
        self.assertIn("conflicts with a built-in command", output)
        self.assertIn("Unknown command: /missing", output)
        run_agent.assert_not_called()


if __name__ == "__main__":
    unittest.main()
