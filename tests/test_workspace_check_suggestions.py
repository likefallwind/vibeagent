from __future__ import annotations

import unittest
from pathlib import Path

from vibeagent import workspace_review_tests
from vibeagent.workspace_check_suggestions import (
    add_check_suggestion,
    check_suggestion_sort_key,
    find_python_package_dirs,
    find_python_test_dirs,
    is_check_script_name,
)


class WorkspaceCheckSuggestionTests(unittest.TestCase):
    def test_review_tests_reexports_check_suggestion_helpers(self) -> None:
        self.assertIs(workspace_review_tests.is_check_script_name, is_check_script_name)
        self.assertIs(workspace_review_tests.add_check_suggestion, add_check_suggestion)
        self.assertIs(workspace_review_tests.check_suggestion_sort_key, check_suggestion_sort_key)
        self.assertIs(workspace_review_tests.find_python_test_dirs, find_python_test_dirs)
        self.assertIs(workspace_review_tests.find_python_package_dirs, find_python_package_dirs)

    def test_check_script_name_matches_common_project_checks(self) -> None:
        for name in ["test", "test:unit", "build", "lint", "type-check"]:
            with self.subTest(name=name):
                self.assertTrue(is_check_script_name(name))
        self.assertFalse(is_check_script_name("start"))

    def test_add_check_suggestion_deduplicates_command_and_marks_missing_tool(self) -> None:
        suggestions: list[dict[str, object]] = []

        add_check_suggestion(suggestions, "definitely-missing-vibeagent-tool --version", ".", "x", "reason")
        add_check_suggestion(suggestions, "definitely-missing-vibeagent-tool --version", ".", "y", "other")

        self.assertEqual(len(suggestions), 1)
        self.assertFalse(suggestions[0]["available"])
        self.assertEqual(suggestions[0]["missing_tool"], "definitely-missing-vibeagent-tool")

    def test_check_sort_key_prioritizes_tests_before_builds_and_lints(self) -> None:
        ordered = sorted(
            [
                {"command": "npm run lint", "cwd": "."},
                {"command": "python -m compileall -q vibeagent", "cwd": "."},
                {"command": "npm test", "cwd": "."},
            ],
            key=check_suggestion_sort_key,
        )
        self.assertEqual([item["command"] for item in ordered], [
            "npm test",
            "python -m compileall -q vibeagent",
            "npm run lint",
        ])

    def test_python_dir_helpers_find_test_and_package_dirs(self) -> None:
        files = [
            "pkg/__init__.py",
            "pkg/mod.py",
            "tests/test_pkg.py",
            "tests/unit/test_mod.py",
            ".venv/lib/__init__.py",
        ]

        self.assertEqual(find_python_test_dirs(Path("."), files), ["tests", "tests/unit"])
        self.assertEqual(find_python_package_dirs(files), ["pkg"])


if __name__ == "__main__":
    unittest.main()
