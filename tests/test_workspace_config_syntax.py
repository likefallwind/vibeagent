import tempfile
import unittest
from pathlib import Path

from vibeagent import workspace_code_intel, workspace_config_syntax
from vibeagent.workspace import create_run_workspace, write_run_file


class WorkspaceConfigSyntaxTests(unittest.TestCase):
    def test_workspace_code_intel_reexports_config_syntax_helpers(self) -> None:
        self.assertIs(workspace_code_intel.check_config_syntax, workspace_config_syntax.check_config_syntax)
        self.assertIs(workspace_code_intel.config_format_for_path, workspace_config_syntax.config_format_for_path)
        self.assertIs(workspace_code_intel.check_config_file_paths, workspace_config_syntax.check_config_file_paths)

    def test_check_config_syntax_reports_json_and_toml_results(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-config-syntax-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "package.json", '{"scripts": {"test": "python -m unittest"}}\n')
            write_run_file(workspace, "bad.json", '{"scripts": }\n')
            write_run_file(workspace, "pyproject.toml", "[project]\nname = 'demo'\n")
            write_run_file(workspace, "bad.toml", "[project\nname = 'demo'\n")
            write_run_file(workspace, "app.py", "print('ignored')\n")

            results, total = workspace_config_syntax.check_config_syntax(workspace, max_files=10)
            scoped_results, scoped_total = workspace_config_syntax.check_config_syntax(workspace, "package.json")

        self.assertEqual(total, 4)
        self.assertEqual([item["path"] for item in results], ["bad.json", "bad.toml", "package.json", "pyproject.toml"])
        self.assertEqual([item["format"] for item in results], ["json", "toml", "json", "toml"])
        self.assertFalse(results[0]["ok"])
        self.assertEqual(results[0]["line"], 1)
        self.assertIn("JSON syntax error", results[0]["message"])
        self.assertFalse(results[1]["ok"])
        self.assertIn("TOML syntax error", results[1]["message"])
        self.assertTrue(results[2]["ok"])
        self.assertTrue(results[3]["ok"])
        self.assertEqual(scoped_total, 1)
        self.assertEqual(scoped_results[0]["path"], "package.json")

    def test_config_format_for_path_matches_supported_config_files(self) -> None:
        self.assertEqual(workspace_config_syntax.config_format_for_path("package.json"), "json")
        self.assertEqual(workspace_config_syntax.config_format_for_path(Path("pyproject.toml")), "toml")
        self.assertIsNone(workspace_config_syntax.config_format_for_path("app.py"))

    def test_check_config_file_paths_deduplicates_and_skips_unsupported_paths(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-config-syntax-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "package.json", "{}\n")
            write_run_file(workspace, "note.txt", "{}\n")

            results, total = workspace_config_syntax.check_config_file_paths(
                workspace,
                ["package.json", "package.json", "note.txt", "missing.json", "../outside.json"],
                max_files=10,
            )

        self.assertEqual(total, 1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["path"], "package.json")


if __name__ == "__main__":
    unittest.main()
