import unittest

from vibeagent.command_code_intel_parsing import parse_code_intel_local_command
from vibeagent.command_parsing import LocalCommand, parse_local_command


class CommandCodeIntelParsingTests(unittest.TestCase):
    def test_code_intel_parser_recognizes_python_and_code_commands(self) -> None:
        cases = {
            "/python-check src": LocalCommand(type="python_check", argument="src"),
            "/python-check": LocalCommand(type="python_check"),
            "/python-deps src": LocalCommand(type="python_deps", argument="src"),
            "/python-deps": LocalCommand(type="python_deps"),
            "/python-defs Runner.run src": LocalCommand(type="python_defs", argument="Runner.run src"),
            "/python-defs": LocalCommand(type="python_defs"),
            "/python-refs run_agent src": LocalCommand(type="python_refs", argument="run_agent src"),
            "/python-refs": LocalCommand(type="python_refs"),
            "/python-ref-contexts run_agent src": LocalCommand(
                type="python_ref_contexts",
                argument="run_agent src",
            ),
            "/python-ref-contexts": LocalCommand(type="python_ref_contexts"),
            "/python-calls helper src": LocalCommand(type="python_calls", argument="helper src"),
            "/python-calls": LocalCommand(type="python_calls"),
            "/python-call-graph src": LocalCommand(type="python_call_graph", argument="src"),
            "/python-call-graph": LocalCommand(type="python_call_graph"),
            "/python-rename-preview run_agent execute_agent src": LocalCommand(
                type="python_rename_preview",
                argument="run_agent execute_agent src",
            ),
            "/python-rename-preview": LocalCommand(type="python_rename_preview"),
            "/python-rename run_agent execute_agent src": LocalCommand(
                type="python_rename",
                argument="run_agent execute_agent src",
            ),
            "/python-rename": LocalCommand(type="python_rename"),
            "/check-replace-python-def Runner.run '    def run(self):\\n        return 2\\n' src/app.py": LocalCommand(
                type="check_replace_python_definition",
                argument="Runner.run '    def run(self):\\n        return 2\\n' src/app.py",
            ),
            "/check-replace-python-def": LocalCommand(type="check_replace_python_definition"),
            "/replace-python-def Runner.run '    def run(self):\\n        return 2\\n' src/app.py": LocalCommand(
                type="replace_python_definition",
                argument="Runner.run '    def run(self):\\n        return 2\\n' src/app.py",
            ),
            "/replace-python-def": LocalCommand(type="replace_python_definition"),
            "/code-deps src": LocalCommand(type="code_deps", argument="src"),
            "/code-deps": LocalCommand(type="code_deps"),
            "/code-refs runAgent web": LocalCommand(type="code_refs", argument="runAgent web"),
            "/code-refs": LocalCommand(type="code_refs"),
            "/code-ref-contexts runAgent web": LocalCommand(
                type="code_ref_contexts",
                argument="runAgent web",
            ),
            "/code-ref-contexts": LocalCommand(type="code_ref_contexts"),
            "/code-defs Runner.run src": LocalCommand(type="code_defs", argument="Runner.run src"),
            "/code-defs": LocalCommand(type="code_defs"),
            "/code-rename-preview runAgent executeAgent web": LocalCommand(
                type="code_rename_preview",
                argument="runAgent executeAgent web",
            ),
            "/code-rename-preview": LocalCommand(type="code_rename_preview"),
            "/code-rename runAgent executeAgent web": LocalCommand(
                type="code_rename",
                argument="runAgent executeAgent web",
            ),
            "/code-rename": LocalCommand(type="code_rename"),
        }

        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(parse_code_intel_local_command(raw), expected)
                self.assertEqual(parse_local_command(raw), expected)

    def test_code_intel_parser_ignores_other_commands(self) -> None:
        self.assertIsNone(parse_code_intel_local_command("/session run-1"))
        self.assertIsNone(parse_code_intel_local_command("python-check src"))


if __name__ == "__main__":
    unittest.main()
