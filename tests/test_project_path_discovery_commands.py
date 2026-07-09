from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from vibeagent import project_discovery_commands, project_path_discovery_commands


class ProjectPathDiscoveryCommandsTests(unittest.TestCase):
    def test_project_discovery_commands_keeps_path_discovery_exports(self) -> None:
        self.assertIs(project_discovery_commands.get_find_files_text, project_path_discovery_commands.get_find_files_text)
        self.assertIs(project_discovery_commands.get_find_files_report, project_path_discovery_commands.get_find_files_report)
        self.assertIs(project_discovery_commands.format_find_files_report_text, project_path_discovery_commands.format_find_files_report_text)
        self.assertIs(project_discovery_commands.get_glob_text, project_path_discovery_commands.get_glob_text)
        self.assertIs(project_discovery_commands.get_glob_report, project_path_discovery_commands.get_glob_report)
        self.assertIs(project_discovery_commands.format_glob_report_text, project_path_discovery_commands.format_glob_report_text)
        self.assertIs(project_discovery_commands.get_tree_text, project_path_discovery_commands.get_tree_text)
        self.assertIs(project_discovery_commands.get_tree_report, project_path_discovery_commands.get_tree_report)
        self.assertIs(project_discovery_commands.format_tree_report_text, project_path_discovery_commands.format_tree_report_text)

    def test_find_files_report_handles_matches_directories_and_usage(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "src").mkdir()
            (root / "tests").mkdir()
            (root / "src" / "app.py").write_text("print('hi')\n", encoding="utf-8")
            (root / "tests" / "test_app.py").write_text("def test_app(): pass\n", encoding="utf-8")
            (root / "docs_app").mkdir()

            report = project_path_discovery_commands.get_find_files_report(root, "app")
            directory_text = project_path_discovery_commands.get_find_files_text(root, "docs", include_dirs=True)
            usage = project_path_discovery_commands.get_find_files_report(root)

        self.assertTrue(report["ok"])
        self.assertEqual(report["matches"]["shown"], 2)
        self.assertIn("src/app.py", report["matches"]["files"])
        self.assertIn("tests/test_app.py", report["matches"]["files"])
        self.assertIn("docs_app/", directory_text)
        self.assertFalse(usage["ok"])
        self.assertIn("Usage: /find-files", usage["message"])

    def test_glob_and_tree_reports_handle_matches_and_usage(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "src" / "pkg").mkdir(parents=True)
            (root / "src" / "app.py").write_text("print('hi')\n", encoding="utf-8")
            (root / "src" / "pkg" / "__init__.py").write_text("", encoding="utf-8")
            (root / "README.md").write_text("# Demo\n", encoding="utf-8")

            glob_report = project_path_discovery_commands.get_glob_report(root, "**/*.py")
            glob_usage = project_path_discovery_commands.get_glob_report(root)
            tree_report = project_path_discovery_commands.get_tree_report(root, "src", max_depth=3, max_entries=20)
            tree_text = project_path_discovery_commands.get_tree_text(root, "src", max_depth=3, max_entries=20)

        self.assertTrue(glob_report["ok"])
        self.assertEqual(glob_report["matches"]["shown"], 2)
        self.assertIn("src/app.py", glob_report["matches"]["files"])
        self.assertIn("src/pkg/__init__.py", glob_report["matches"]["files"])
        self.assertFalse(glob_usage["ok"])
        self.assertIn("Usage: /glob", glob_usage["message"])
        self.assertTrue(tree_report["ok"])
        self.assertEqual(tree_report["path"], "src")
        self.assertIn("src/pkg/", tree_report["entries"]["items"])
        self.assertIn("Tree:", tree_text)


if __name__ == "__main__":
    unittest.main()
