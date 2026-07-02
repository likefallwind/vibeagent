import ast
import unittest

from vibeagent.command_safety_python import python_call_shell_command, python_os_exec_spawn_function_name
from vibeagent.command_safety_python_aliases import collect_python_import_aliases


class PythonImportAliasTests(unittest.TestCase):
    def test_collects_module_import_aliases(self) -> None:
        tree = ast.parse("import os as operating_system\nimport subprocess as sp\nimport webbrowser as wb")
        aliases = collect_python_import_aliases(tree, python_os_exec_spawn_function_name)

        self.assertIn("operating_system", aliases.os_aliases)
        self.assertIn("sp", aliases.subprocess_aliases)
        self.assertIn("wb", aliases.webbrowser_aliases)

    def test_collects_execution_import_aliases(self) -> None:
        tree = ast.parse(
            "from os import execvp as run_file\n"
            "from asyncio import create_subprocess_exec as start_exec\n"
            "from subprocess import run as shell_run\n"
            "from builtins import exec as run_python\n"
        )
        aliases = collect_python_import_aliases(tree, python_os_exec_spawn_function_name)

        self.assertIn("run_file", aliases.os_exec_spawn_aliases)
        self.assertEqual(aliases.os_exec_spawn_alias_functions["run_file"], "execvp")
        self.assertIn("start_exec", aliases.asyncio_subprocess_aliases)
        self.assertEqual(aliases.asyncio_subprocess_alias_functions["start_exec"], "create_subprocess_exec")
        self.assertIn("shell_run", aliases.subprocess_launcher_aliases)
        self.assertIn("run_python", aliases.eval_exec_aliases)

    def test_collects_file_mutation_import_aliases(self) -> None:
        tree = ast.parse(
            "from io import open as io_open\n"
            "from os import open as os_open\n"
            "from pathlib import Path as P\n"
            "from shutil import rmtree as remove_tree\n"
        )
        aliases = collect_python_import_aliases(tree, python_os_exec_spawn_function_name)

        self.assertIn("io_open", aliases.io_open_aliases)
        self.assertIn("os_open", aliases.os_open_aliases)
        self.assertIn("P", aliases.pathlib_path_aliases)
        self.assertIn("remove_tree", aliases.shutil_rmtree_aliases)


class PythonShellCommandCompatibilityTests(unittest.TestCase):
    def test_call_shell_command_keeps_old_positional_signature(self) -> None:
        call = ast.parse("execvp('xdg-open', ['xdg-open', '.'])", mode="eval").body
        assert isinstance(call, ast.Call)

        command = python_call_shell_command(
            call,
            {"os"},
            {"subprocess"},
            {"asyncio"},
            {"pty"},
            set(),
            set(),
            {"execvp"},
            set(),
            set(),
            {"builtins", "__builtins__"},
            {"importlib"},
            set(),
        )

        self.assertEqual(command, "xdg-open xdg-open .")


if __name__ == "__main__":
    unittest.main()
