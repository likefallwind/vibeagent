import unittest

from vibeagent import command_safety_python
from vibeagent import command_safety_python_eval
from vibeagent import command_safety_python_filesystem
from vibeagent import command_safety_python_gui
from vibeagent import command_safety_python_introspection
from vibeagent import command_safety_python_shell


class CommandSafetyPythonModuleTests(unittest.TestCase):
    def test_command_safety_python_reexports_gui_helpers(self) -> None:
        self.assertIs(command_safety_python.python_call_is_os_startfile, command_safety_python_gui.python_call_is_os_startfile)
        self.assertIs(command_safety_python.python_call_is_webbrowser_get, command_safety_python_gui.python_call_is_webbrowser_get)
        self.assertIs(command_safety_python.python_call_is_webbrowser_open, command_safety_python_gui.python_call_is_webbrowser_open)

    def test_command_safety_python_reexports_introspection_helpers(self) -> None:
        self.assertIs(command_safety_python.python_dynamic_import_name, command_safety_python_introspection.python_dynamic_import_name)
        self.assertIs(command_safety_python.python_first_string_argument, command_safety_python_introspection.python_first_string_argument)
        self.assertIs(command_safety_python.python_getattr_attribute, command_safety_python_introspection.python_getattr_attribute)
        self.assertIs(command_safety_python.python_static_getattr_target, command_safety_python_introspection.python_static_getattr_target)

    def test_command_safety_python_reexports_filesystem_helpers(self) -> None:
        self.assertIs(command_safety_python.python_call_deletes_broad_path, command_safety_python_filesystem.python_call_deletes_broad_path)
        self.assertIs(command_safety_python.python_call_is_text_open, command_safety_python_filesystem.python_call_is_text_open)
        self.assertIs(command_safety_python.python_call_string_argument, command_safety_python_filesystem.python_call_string_argument)
        self.assertIs(command_safety_python.python_call_writes_raw_device, command_safety_python_filesystem.python_call_writes_raw_device)
        self.assertIs(
            command_safety_python.python_open_call_writes_raw_device,
            command_safety_python_filesystem.python_open_call_writes_raw_device,
        )
        self.assertIs(
            command_safety_python.python_os_open_call_writes_raw_device,
            command_safety_python_filesystem.python_os_open_call_writes_raw_device,
        )
        self.assertIs(command_safety_python.python_os_open_flags_write, command_safety_python_filesystem.python_os_open_flags_write)
        self.assertIs(command_safety_python.python_pathlib_call_path, command_safety_python_filesystem.python_pathlib_call_path)
        self.assertIs(
            command_safety_python.python_pathlib_call_writes_raw_device,
            command_safety_python_filesystem.python_pathlib_call_writes_raw_device,
        )

    def test_command_safety_python_reexports_eval_helpers(self) -> None:
        self.assertIs(command_safety_python.python_call_is_compile, command_safety_python_eval.python_call_is_compile)
        self.assertIs(command_safety_python.python_call_is_eval_or_exec, command_safety_python_eval.python_call_is_eval_or_exec)
        self.assertIs(
            command_safety_python.python_expr_is_compile_reference,
            command_safety_python_eval.python_expr_is_compile_reference,
        )
        self.assertIs(
            command_safety_python.python_expr_is_eval_or_exec_reference,
            command_safety_python_eval.python_expr_is_eval_or_exec_reference,
        )
        self.assertIs(command_safety_python.python_literal_compile_script, command_safety_python_eval.python_literal_compile_script)
        self.assertIs(command_safety_python.python_literal_eval_exec_script, command_safety_python_eval.python_literal_eval_exec_script)
        self.assertIs(command_safety_python.python_literal_source_text, command_safety_python_eval.python_literal_source_text)

    def test_command_safety_python_reexports_shell_helpers(self) -> None:
        self.assertIs(command_safety_python.python_asyncio_subprocess_command, command_safety_python_shell.python_asyncio_subprocess_command)
        self.assertIs(command_safety_python.python_call_shell_command, command_safety_python_shell.python_call_shell_command)
        self.assertIs(command_safety_python.python_os_exec_spawn_command, command_safety_python_shell.python_os_exec_spawn_command)
        self.assertIs(
            command_safety_python.python_os_exec_spawn_function_name,
            command_safety_python_shell.python_os_exec_spawn_function_name,
        )


if __name__ == "__main__":
    unittest.main()
