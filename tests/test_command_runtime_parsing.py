import unittest

from vibeagent.command_parsing import LocalCommand, parse_local_command
from vibeagent.command_runtime_parsing import parse_runtime_local_command


class CommandRuntimeParsingTests(unittest.TestCase):
    def test_runtime_parser_recognizes_runtime_commands(self) -> None:
        cases = {
            "/tools": LocalCommand(type="tools"),
            "/tool read_file": LocalCommand(type="tool", argument="read_file"),
            "/tool": LocalCommand(type="tool"),
            "/tool-search git": LocalCommand(type="tool_search", argument="git"),
            "/tool-search": LocalCommand(type="tool_search"),
            "/permissions": LocalCommand(type="permissions"),
            "/checks src": LocalCommand(type="checks", argument="src"),
            "/checks": LocalCommand(type="checks"),
            "/check-suggested-checks": LocalCommand(type="check_suggested_checks"),
            "/run-suggested-checks": LocalCommand(type="run_suggested_checks"),
            "/commands": LocalCommand(type="commands"),
            "/commands test": LocalCommand(type="commands", argument="test"),
            "/related-tests src/app.py": LocalCommand(type="related_tests", argument="src/app.py"),
            "/related-tests": LocalCommand(type="related_tests"),
            "/focused-tests src/app.py tests/test_app.py": LocalCommand(
                type="focused_test_commands",
                argument="src/app.py tests/test_app.py",
            ),
            "/check-focused-tests": LocalCommand(type="check_focused_test_commands"),
            "/run-focused-tests tests/test_app.py": LocalCommand(
                type="run_focused_test_commands",
                argument="tests/test_app.py",
            ),
            "/manifests --max-files 2": LocalCommand(type="manifests", argument="--max-files 2"),
            "/instructions --max-bytes 1000": LocalCommand(type="instructions", argument="--max-bytes 1000"),
            "/todos src": LocalCommand(type="todos", argument="src"),
            "/command python -m unittest": LocalCommand(type="command", argument="python -m unittest"),
            "/run python3 --version": LocalCommand(type="run", argument="python3 --version"),
            "/run-commands python3 --version ;; npm test": LocalCommand(
                type="run_sequence",
                argument="python3 --version ;; npm test",
            ),
            "/run-seq python3 --version ;; npm test": LocalCommand(
                type="run_sequence",
                argument="python3 --version ;; npm test",
            ),
            "/check-run-commands python3 --version ;; npm test": LocalCommand(
                type="check_run_sequence",
                argument="python3 --version ;; npm test",
            ),
            "/check-run-seq python3 --version ;; npm test": LocalCommand(
                type="check_run_sequence",
                argument="python3 --version ;; npm test",
            ),
            "/check-start npm run dev": LocalCommand(type="check_start", argument="npm run dev"),
            "/start npm run dev": LocalCommand(type="start", argument="npm run dev"),
            "/port 5173 127.0.0.1 1500": LocalCommand(type="port", argument="5173 127.0.0.1 1500"),
            "/http http://127.0.0.1:5173 ready": LocalCommand(
                type="http",
                argument="http://127.0.0.1:5173 ready",
            ),
            "/http-fetch http://127.0.0.1:5173/app": LocalCommand(
                type="http_fetch",
                argument="http://127.0.0.1:5173/app",
            ),
        }

        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(parse_runtime_local_command(raw), expected)
                self.assertEqual(parse_local_command(raw), expected)

    def test_runtime_parser_ignores_other_commands(self) -> None:
        self.assertIsNone(parse_runtime_local_command("/session run-1"))
        self.assertIsNone(parse_runtime_local_command("run python3 --version"))


if __name__ == "__main__":
    unittest.main()
