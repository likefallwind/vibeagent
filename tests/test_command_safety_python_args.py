import ast
import unittest

from vibeagent.command_safety_python_args import (
    python_command_argument,
    python_executable_command_from_args,
    python_executable_command_from_call,
)


def parse_call(source: str) -> ast.Call:
    expression = ast.parse(source, mode="eval").body
    assert isinstance(expression, ast.Call)
    return expression


class PythonCommandArgumentTests(unittest.TestCase):
    def test_command_argument_reads_positional_string(self) -> None:
        self.assertEqual(python_command_argument(parse_call("run('xdg-open .')")), "xdg-open .")

    def test_command_argument_reads_keyword_string(self) -> None:
        self.assertEqual(python_command_argument(parse_call("run(command='xdg-open .')")), "xdg-open .")

    def test_command_argument_joins_static_sequence(self) -> None:
        self.assertEqual(python_command_argument(parse_call("run(['xdg-open', '.'])")), "xdg-open .")


class PythonExecutableCommandArgumentTests(unittest.TestCase):
    def test_executable_command_reads_positional_path_and_argv(self) -> None:
        call = parse_call("execvp('xdg-open', ['xdg-open', '.'])")
        self.assertEqual(python_executable_command_from_args(call.args, path_index=0, argv_index=1), "xdg-open xdg-open .")

    def test_executable_command_reads_keyword_path_and_argv(self) -> None:
        call = parse_call("execvp(file='xdg-open', args=['xdg-open', '.'])")
        self.assertEqual(python_executable_command_from_call(call, path_index=0, argv_index=1), "xdg-open xdg-open .")

    def test_executable_command_reads_custom_program_keyword(self) -> None:
        call = parse_call("create_subprocess_exec(program='xdg-open')")
        self.assertEqual(
            python_executable_command_from_call(call, path_index=0, argv_index=None, path_keyword_names=("program",)),
            "xdg-open",
        )


if __name__ == "__main__":
    unittest.main()
