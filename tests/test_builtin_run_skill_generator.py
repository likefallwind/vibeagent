from __future__ import annotations

from contextlib import redirect_stdout
import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from vibeagent.agent import AgentResult
from vibeagent.builtin_run_skill_generator import (
    build_run_skill_generator_workflow,
    parse_run_skill_generator_hint,
)
from vibeagent.cli import main
from vibeagent.cli_project_command_expansion import expand_one_shot_project_command
from vibeagent.config_change_hooks import ConfigChangeHookRuntime
from vibeagent.workspace import create_run_workspace, read_project_skill, read_project_skills


class BuiltinRunSkillGeneratorTests(unittest.TestCase):
    def test_builds_interactive_validated_recipe_workflow(self) -> None:
        workflow = build_run_skill_generator_workflow("web app", interactive=True)

        self.assertIn('Application or package hint: "web app"', workflow.task)
        self.assertIn("call ask_user", workflow.task)
        self.assertIn(".claude/skills/<name>/SKILL.md", workflow.task)
        self.assertIn("at the repository root", workflow.task)
        self.assertIn("encode a monorepo package", workflow.task)
        self.assertIn("do not reuse a pre-existing app process", workflow.task)
        self.assertIn("Every build, launch, readiness, drive, and cleanup command", workflow.task)
        self.assertIn("check_stop_process before stop_process", workflow.task)
        self.assertIn("project_skills and then skill", workflow.task)
        self.assertIn("Do not include credentials", workflow.task)
        self.assertIn("PASS", workflow.task)
        self.assertEqual(workflow.metadata["name"], "run-skill-generator")
        self.assertEqual(workflow.metadata["app_hint"], "web app")
        self.assertTrue(workflow.metadata["interactive"])

    def test_print_workflow_fails_closed_on_ambiguous_app(self) -> None:
        workflow = build_run_skill_generator_workflow(None, interactive=False)

        self.assertIn("stop with the concrete candidates", workflow.task)
        self.assertIn("do not guess or write files in print mode", workflow.task)
        self.assertFalse(workflow.metadata["interactive"])

    def test_hint_parser_is_bounded_and_fail_closed(self) -> None:
        self.assertEqual(parse_run_skill_generator_hint("-- --generated app"), "--generated app")
        for argument, message in (
            ("--force", "Unknown"),
            ("'unterminated", "invalid"),
            ("x" * 1001, "1000"),
            ("bad\x00hint", "NUL"),
        ):
            with self.subTest(argument=argument), self.assertRaisesRegex(ValueError, message):
                parse_run_skill_generator_hint(argument)

    def test_one_shot_expands_with_noninteractive_contract(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-run-skill-") as base:
            task, metadata = expand_one_shot_project_command(Path(base), "/run-skill-generator api")

        self.assertIn('Application or package hint: "api"', task)
        self.assertIn("do not guess or write files in print mode", task)
        self.assertEqual(metadata["name"], "run-skill-generator")
        self.assertFalse(metadata["interactive"])

    def test_generated_project_skill_is_discoverable_after_config_reload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-run-skill-") as base:
            root = Path(base)
            workspace = create_run_workspace(root, "run-skill-reload")
            lifecycle = Mock()
            lifecycle.config_change.return_value = SimpleNamespace(
                system_messages=(),
                blocking_message=None,
            )
            runtime = ConfigChangeHookRuntime(workspace, lifecycle)
            skill_path = root / ".claude/skills/run-api/SKILL.md"
            skill_path.parent.mkdir(parents=True)
            skill_path.write_text(
                "---\n"
                "name: run-api\n"
                "description: Build, launch, and exercise the API.\n"
                "---\n\n"
                "Run the validated API recipe.\n",
                encoding="utf-8",
            )

            self.assertEqual(read_project_skills(workspace)["skills"], [])
            changed = runtime.poll(iteration=1)
            catalog = read_project_skills(workspace)
            loaded = read_project_skill(workspace, "run-api")

        self.assertEqual(len(changed.events), 1)
        self.assertFalse(changed.events[0].blocked)
        self.assertEqual([item["name"] for item in catalog["skills"]], ["run-api"])
        self.assertIn("Run the validated API recipe.", loaded["content"])
        lifecycle.config_change.assert_called_once()

    def test_interactive_command_runs_with_workflow_metadata(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-run-skill-") as base:
            root = Path(base)
            result = AgentResult(True, "recipe written", root, "run-skill", 1, [], [])
            run_agent = Mock(return_value=result)
            with (
                patch("builtins.input", side_effect=["/run-skill-generator api", "/exit"]),
                patch("vibeagent.cli.create_chat_client", return_value=object()),
                patch("vibeagent.cli.run_agent", run_agent),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["--cwd", str(root)])

        self.assertEqual(exit_code, 0)
        self.assertIn('Application or package hint: "api"', run_agent.call_args.args[0])
        metadata = run_agent.call_args.kwargs["task_metadata"]
        self.assertEqual(metadata["name"], "run-skill-generator")
        self.assertTrue(metadata["interactive"])

    def test_invalid_print_command_fails_before_provider_creation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-run-skill-") as base:
            create_client = Mock()
            stdout = io.StringIO()
            with (
                patch("vibeagent.cli.create_chat_client", create_client),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--print", "/run-skill-generator --force"])

        self.assertNotEqual(exit_code, 0)
        create_client.assert_not_called()
        self.assertIn("Unknown /run-skill-generator option", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
