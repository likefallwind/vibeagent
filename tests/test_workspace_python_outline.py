import unittest

from vibeagent import workspace_python_intel
from vibeagent import workspace_python_outline


class WorkspacePythonOutlineTests(unittest.TestCase):
    def test_workspace_python_intel_reexports_outline_helpers(self) -> None:
        self.assertIs(
            workspace_python_intel.read_python_symbol_outline,
            workspace_python_outline.read_python_symbol_outline,
        )
        self.assertIs(workspace_python_intel.collect_python_imports, workspace_python_outline.collect_python_imports)
        self.assertIs(workspace_python_intel.format_import_alias, workspace_python_outline.format_import_alias)
        self.assertIs(workspace_python_intel.import_line_number, workspace_python_outline.import_line_number)
        self.assertIs(workspace_python_intel.collect_python_symbols, workspace_python_outline.collect_python_symbols)


if __name__ == "__main__":
    unittest.main()
