from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from vibeagent import project_commands, project_discovery_commands, project_search_commands


class ProjectSearchCommandsTests(unittest.TestCase):
    def test_project_modules_keep_search_command_exports(self) -> None:
        self.assertIs(project_discovery_commands.get_search_text, project_search_commands.get_search_text)
        self.assertIs(project_discovery_commands.get_search_report, project_search_commands.get_search_report)
        self.assertIs(project_discovery_commands.format_search_report_text, project_search_commands.format_search_report_text)
        self.assertIs(project_discovery_commands.get_search_contexts_text, project_search_commands.get_search_contexts_text)
        self.assertIs(project_discovery_commands.get_search_contexts_report, project_search_commands.get_search_contexts_report)
        self.assertIs(
            project_discovery_commands.format_search_contexts_report_text,
            project_search_commands.format_search_contexts_report_text,
        )
        self.assertIs(project_commands.get_search_text, project_search_commands.get_search_text)
        self.assertIs(project_commands.get_search_contexts_text, project_search_commands.get_search_contexts_text)

    def test_search_report_scopes_matches_and_formats_usage(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("needle = 'visible'\nprint(needle)\n", encoding="utf-8")
            (root / "other.txt").write_text("needle outside scope\n", encoding="utf-8")

            report = project_search_commands.get_search_report(root, "needle", path="src", max_matches=5)
            text = project_search_commands.get_search_text(root, "needle", path="src")
            usage = project_search_commands.get_search_report(root)

        self.assertTrue(report["ok"])
        self.assertEqual(report["query"], "needle")
        self.assertEqual(report["path"], "src")
        self.assertEqual(report["matches"]["shown"], 2)
        self.assertIn("src/app.py:1:", report["matches"]["items"][0])
        self.assertIn("Search:", text)
        self.assertNotIn("other.txt", text)
        self.assertFalse(usage["ok"])
        self.assertEqual(project_search_commands.format_search_report_text(usage), "Usage: /search <query>")

    def test_search_contexts_report_serializes_contexts_and_usage(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("before\nneedle = 'visible'\nafter\n", encoding="utf-8")
            (root / "other.txt").write_text("needle outside scope\n", encoding="utf-8")

            report = project_search_commands.get_search_contexts_report(
                root,
                "needle",
                path="src",
                context_lines=1,
                max_bytes_per_context=1000,
            )
            text = project_search_commands.get_search_contexts_text(
                root,
                "needle",
                path="src",
                context_lines=1,
                max_bytes_per_context=1000,
            )
            usage = project_search_commands.get_search_contexts_report(root)

        self.assertTrue(report["ok"])
        self.assertEqual(report["contexts"]["shown"], 1)
        self.assertEqual(report["contexts"]["items"][0]["path"], "src/app.py")
        self.assertEqual(report["contexts"]["items"][0]["start_line"], 1)
        self.assertIn("Search contexts:", text)
        self.assertIn("needle = 'visible'", text)
        self.assertNotIn("other.txt", text)
        self.assertFalse(usage["ok"])
        self.assertEqual(project_search_commands.format_search_contexts_report_text(usage), "Usage: /search-contexts <query>")


if __name__ == "__main__":
    unittest.main()
