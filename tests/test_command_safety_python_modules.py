import unittest

from vibeagent import command_safety_python
from vibeagent import command_safety_python_gui
from vibeagent import command_safety_python_introspection


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


if __name__ == "__main__":
    unittest.main()
