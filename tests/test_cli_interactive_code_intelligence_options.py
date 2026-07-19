import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from vibeagent.cli import main


class CliInteractiveCodeIntelligenceOptionsTests(unittest.TestCase):
    def test_main_parses_interactive_python_symbol_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/python-defs --path src --max-matches 3 --max-lines 40 -- Runner.run",
                    "/python-refs run_agent --path src --max-matches 4",
                    "/python-ref-contexts --path src --max-matches 5 --context-lines 1 --max-bytes 1000 -- run_agent",
                    "/python-calls helper src --max-matches 6",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_python_defs_text", return_value="Python definitions:\n  definitions: 1/1") as get_python_defs_text,
            patch("vibeagent.cli.get_python_refs_text", return_value="Python references:\n  references: 1/1") as get_python_refs_text,
            patch("vibeagent.cli.get_python_ref_contexts_text", return_value="Python reference contexts:\n  contexts: 1/1") as get_python_ref_contexts_text,
            patch("vibeagent.cli.get_python_calls_text", return_value="Python calls:\n  calls: 1/1") as get_python_calls_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Python definitions:", output)
        self.assertIn("Python references:", output)
        self.assertIn("Python reference contexts:", output)
        self.assertIn("Python calls:", output)
        get_python_defs_text.assert_called_once_with(symbol="Runner.run", path="src", max_matches=3, max_lines=40)
        get_python_refs_text.assert_called_once_with(symbol="run_agent", path="src", max_matches=4)
        get_python_ref_contexts_text.assert_called_once_with(
            symbol="run_agent",
            path="src",
            max_matches=5,
            context_lines=1,
            max_bytes_per_context=1000,
        )
        get_python_calls_text.assert_called_once_with(symbol="helper", path="src", max_matches=6)
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_python_deps_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/python-deps --max-files 2 --max-imports=7 -- src",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch(
                "vibeagent.cli.get_python_deps_text",
                return_value="Python dependencies:\n  files: 1/1",
            ) as get_python_deps_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Python dependencies:", output)
        get_python_deps_text.assert_called_once_with(argument="src", max_files=2, max_imports=7)
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_python_call_graph_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/python-call-graph --max-files 2 --max-edges=7 -- src",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_python_call_graph_text", return_value="Python call graph:\n  edges: 3/3") as get_python_call_graph_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Python call graph:", output)
        get_python_call_graph_text.assert_called_once_with(argument="src", max_files=2, max_edges=7)
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_python_symbol_option_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/python-defs --max-matches 0 -- Runner.run",
                    "/python-defs --max-lines 0 -- Runner.run",
                    "/python-defs --path src Runner.run src",
                    "/python-refs --max-matches 0 -- run_agent",
                    "/python-ref-contexts --context-lines -1 -- run_agent",
                    "/python-ref-contexts --max-bytes 0 -- run_agent",
                    "/python-ref-contexts --unknown 1 -- run_agent",
                    "/python-calls --max-matches 0 -- helper",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_python_defs_text") as get_python_defs_text,
            patch("vibeagent.cli.get_python_refs_text") as get_python_refs_text,
            patch("vibeagent.cli.get_python_ref_contexts_text") as get_python_ref_contexts_text,
            patch("vibeagent.cli.get_python_calls_text") as get_python_calls_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /python-defs [--path PATH] [--max-matches N] [--max-lines N] -- <symbol> [path]", output)
        self.assertIn("Usage: /python-refs [--path PATH] [--max-matches N] -- <symbol> [path]", output)
        self.assertIn(
            "Usage: /python-ref-contexts [--path PATH] [--max-matches N] [--context-lines N] [--max-bytes N] -- <symbol> [path]",
            output,
        )
        self.assertIn("Usage: /python-calls [--path PATH] [--max-matches N] -- <symbol> [path]", output)
        self.assertIn("error: --max-matches must be a positive integer.", output)
        self.assertIn("error: --max-lines must be a positive integer.", output)
        self.assertIn("error: path can only be provided once.", output)
        self.assertIn("error: --context-lines must be a non-negative integer.", output)
        self.assertIn("error: --max-bytes must be a positive integer.", output)
        self.assertIn("error: Unknown option: --unknown", output)
        get_python_defs_text.assert_not_called()
        get_python_refs_text.assert_not_called()
        get_python_ref_contexts_text.assert_not_called()
        get_python_calls_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_python_deps_option_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/python-deps --max-files 0 -- src",
                    "/python-deps --max-imports 0 -- src",
                    "/python-deps --unknown 1 -- src",
                    "/python-deps src tests --max-files 2",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_python_deps_text") as get_python_deps_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /python-deps [--max-files N] [--max-imports N] -- [path]", output)
        self.assertIn("error: --max-files must be a positive integer.", output)
        self.assertIn("error: --max-imports must be a positive integer.", output)
        self.assertIn("error: Unknown option: --unknown", output)
        get_python_deps_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_python_call_graph_option_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/python-call-graph --max-files 0 -- src",
                    "/python-call-graph --max-edges 0 -- src",
                    "/python-call-graph --unknown 1 -- src",
                    "/python-call-graph src tests --max-files 2",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_python_call_graph_text") as get_python_call_graph_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /python-call-graph [--max-files N] [--max-edges N] -- [path]", output)
        self.assertIn("error: --max-files must be a positive integer.", output)
        self.assertIn("error: --max-edges must be a positive integer.", output)
        self.assertIn("error: Unknown option: --unknown", output)
        get_python_call_graph_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_code_symbol_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/code-refs runAgent --path web --max-matches 4",
                    "/code-ref-contexts --path web --max-matches 5 --context-lines 1 --max-bytes 1000 -- runAgent",
                    "/code-defs --path web --max-matches 6 --max-lines 40 -- runAgent",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_code_refs_text", return_value="Code references:\n  references: 1/1") as get_code_refs_text,
            patch("vibeagent.cli.get_code_ref_contexts_text", return_value="Code reference contexts:\n  contexts: 1/1") as get_code_ref_contexts_text,
            patch("vibeagent.cli.get_code_defs_text", return_value="Code definitions:\n  definitions: 1/1") as get_code_defs_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Code references:", output)
        self.assertIn("Code reference contexts:", output)
        self.assertIn("Code definitions:", output)
        get_code_refs_text.assert_called_once_with(symbol="runAgent", path="web", max_matches=4)
        get_code_ref_contexts_text.assert_called_once_with(
            symbol="runAgent",
            path="web",
            max_matches=5,
            context_lines=1,
            max_bytes_per_context=1000,
        )
        get_code_defs_text.assert_called_once_with(symbol="runAgent", path="web", max_matches=6, max_lines=40)
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_code_symbol_option_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/code-refs --max-matches 0 -- runAgent",
                    "/code-ref-contexts --context-lines -1 -- runAgent",
                    "/code-ref-contexts --max-bytes 0 -- runAgent",
                    "/code-ref-contexts --unknown 1 -- runAgent",
                    "/code-defs --max-lines 0 -- runAgent",
                    "/code-defs --path web runAgent web",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_code_refs_text") as get_code_refs_text,
            patch("vibeagent.cli.get_code_ref_contexts_text") as get_code_ref_contexts_text,
            patch("vibeagent.cli.get_code_defs_text") as get_code_defs_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /code-refs [--path PATH] [--max-matches N] -- <symbol> [path]", output)
        self.assertIn(
            "Usage: /code-ref-contexts [--path PATH] [--max-matches N] [--context-lines N] [--max-bytes N] -- <symbol> [path]",
            output,
        )
        self.assertIn("Usage: /code-defs [--path PATH] [--max-matches N] [--max-lines N] -- <symbol> [path]", output)
        self.assertIn("error: --max-matches must be a positive integer.", output)
        self.assertIn("error: --context-lines must be a non-negative integer.", output)
        self.assertIn("error: --max-bytes must be a positive integer.", output)
        self.assertIn("error: Unknown option: --unknown", output)
        self.assertIn("error: --max-lines must be a positive integer.", output)
        self.assertIn("error: path can only be provided once.", output)
        get_code_refs_text.assert_not_called()
        get_code_ref_contexts_text.assert_not_called()
        get_code_defs_text.assert_not_called()
        create_chat_client.assert_not_called()


if __name__ == "__main__":
    unittest.main()
