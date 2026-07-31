import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import call, patch

from vibeagent.cli import main


class CliInteractiveProjectOptionsTests(unittest.TestCase):
    def test_main_parses_interactive_checks_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/checks --max-checks 2",
                    "/checks --max-checks=3",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_checks_text", return_value="Checks:\n  suggestedChecks: 1/2") as get_checks_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Checks:", output)
        get_checks_text.assert_has_calls(
            [
                call(max_checks=2),
                call(max_checks=3),
            ]
        )
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_checks_option_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/checks --max-checks 0",
                    "/checks --unknown 1",
                    "/checks --max-checks 1 --max-checks 2",
                    "/checks package.json",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_checks_text") as get_checks_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /checks [--max-checks N]", output)
        self.assertIn("--max-checks must be a positive integer.", output)
        self.assertIn("Unknown option: --unknown", output)
        self.assertIn("provide --max-checks at most once.", output)
        get_checks_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_commands_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/commands --max-commands 2 --max-files 3",
                    "/commands --max-commands=4 --max-files=5",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_commands_text", return_value="Project commands:\n  commands: 1/2") as get_commands_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Project commands:", output)
        get_commands_text.assert_has_calls(
            [
                call(max_commands=2, max_files=3),
                call(max_commands=4, max_files=5),
            ]
        )
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_commands_option_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/commands --max-commands 0",
                    "/commands --max-files 0",
                    "/commands --unknown 1",
                    "/commands package.json",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_commands_text") as get_commands_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /commands [--max-commands N] [--max-files N]", output)
        self.assertIn("--max-commands must be a positive integer.", output)
        self.assertIn("--max-files must be a positive integer.", output)
        self.assertIn("Unknown option: --unknown", output)
        get_commands_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_agents_and_skills_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/agents --max-agents 2",
                    "/skills --max-skills=3",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_agents_text", return_value="Available project agent profiles:\n- reviewer") as get_agents_text,
            patch("vibeagent.cli.get_skills_text", return_value="Available project skills:\n- testing") as get_skills_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Available project agent profiles:", output)
        self.assertIn("Available project skills:", output)
        get_agents_text.assert_called_once_with(max_agents=2)
        get_skills_text.assert_called_once_with(max_skills=3)
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_agents_and_skills_option_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/agents --max-agents 0",
                    "/skills --unknown 1",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_agents_text") as get_agents_text,
            patch("vibeagent.cli.get_skills_text") as get_skills_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /agents [--max-agents N]", output)
        self.assertIn("--max-agents must be a positive integer.", output)
        self.assertIn("Usage: /skills [--max-skills N]", output)
        self.assertIn("Unknown option: --unknown", output)
        get_agents_text.assert_not_called()
        get_skills_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_manifests_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/manifests --max-files 2 --max-items 10",
                    "/manifests --max-files=3 --max-items=20",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_manifests_text", return_value="Manifests:\n  files: 1/2") as get_manifests_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Manifests:", output)
        get_manifests_text.assert_has_calls(
            [
                call(max_files=2, max_items=10),
                call(max_files=3, max_items=20),
            ]
        )
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_manifests_option_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/manifests --max-files 0",
                    "/manifests --max-items 0",
                    "/manifests --unknown 1",
                    "/manifests package.json",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_manifests_text") as get_manifests_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /manifests [--max-files N] [--max-items N]", output)
        self.assertIn("--max-files must be a positive integer.", output)
        self.assertIn("--max-items must be a positive integer.", output)
        self.assertIn("Unknown option: --unknown", output)
        get_manifests_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_todos_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/todos src --max-items 3 --max-files 20",
                    "/todos --max-items=4 --max-files=30 -- src",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_todos_text", return_value="Project TODOs:\n  todos: 1/3") as get_todos_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Project TODOs:", output)
        get_todos_text.assert_has_calls(
            [
                call(path="src", max_items=3, max_files=20),
                call(path="src", max_items=4, max_files=30),
            ]
        )
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_instructions_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/instructions --max-files 2 --max-bytes 1000",
                    "/instructions --max-files=3 --max-bytes=1200",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_instructions_text", return_value="Project instructions:\n  files: 1/2") as get_instructions_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Project instructions:", output)
        get_instructions_text.assert_has_calls(
            [
                call(max_files=2, max_bytes=1000),
                call(max_files=3, max_bytes=1200),
            ]
        )
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_instructions_option_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/instructions --max-files 0",
                    "/instructions --max-bytes 0",
                    "/instructions --unknown 1",
                    "/instructions AGENTS.md",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_instructions_text") as get_instructions_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /instructions [--max-files N] [--max-bytes N]", output)
        self.assertIn("--max-files must be a positive integer.", output)
        self.assertIn("--max-bytes must be a positive integer.", output)
        self.assertIn("Unknown option: --unknown", output)
        get_instructions_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_todos_option_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/todos --max-items 0 -- src",
                    "/todos --max-files 0 -- src",
                    "/todos --unknown 1 -- src",
                    "/todos src docs --max-items 2",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_todos_text") as get_todos_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /todos [--max-items N] [--max-files N] -- [path]", output)
        self.assertIn("error: --max-items must be a positive integer.", output)
        self.assertIn("error: --max-files must be a positive integer.", output)
        self.assertIn("error: Unknown option: --unknown", output)
        get_todos_text.assert_not_called()
        create_chat_client.assert_not_called()


if __name__ == "__main__":
    unittest.main()
