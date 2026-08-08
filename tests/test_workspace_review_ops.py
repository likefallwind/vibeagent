import unittest
from pathlib import Path

from vibeagent import (
    workspace,
    workspace_git_changes,
    workspace_review_checks,
    workspace_review_ops,
    workspace_review_tests,
    workspace_untracked_previews,
)


class WorkspaceReviewOpsTests(unittest.TestCase):
    def test_workspace_reexports_review_helpers(self) -> None:
        names = [
            "read_git_changes",
            "review_project_changes",
            "read_untracked_file_previews",
            "suggest_project_checks",
            "find_related_tests",
            "suggest_focused_test_commands",
            "add_focused_test_commands_for_file",
            "focused_npm_test_command",
            "nearest_package_json",
            "preferred_test_script_name",
            "project_has_pytest_evidence",
            "normalize_related_test_targets",
            "is_project_test_file",
            "related_test_candidates_for_target",
            "expected_test_names",
            "expected_test_paths",
            "is_check_script_name",
            "find_python_test_dirs",
            "find_python_package_dirs",
        ]
        for name in names:
            with self.subTest(name=name):
                self.assertIs(getattr(workspace, name), getattr(workspace_review_ops, name))

    def test_related_test_helpers_match_python_and_javascript_layouts(self) -> None:
        test_files = [
            "tests/test_service.py",
            "pkg/service_test.py",
            "web/src/__tests__/app.test.ts",
            "web/src/other.spec.ts",
        ]

        python_candidates = workspace_review_ops.related_test_candidates_for_target("pkg/service.py", test_files)
        js_candidates = workspace_review_ops.related_test_candidates_for_target("web/src/app.ts", test_files)

        self.assertIn(("pkg/service_test.py", "Test path mirrors the source path.", 95), python_candidates)
        self.assertIn(("tests/test_service.py", "Test path mirrors the source path.", 95), python_candidates)
        self.assertIn(("web/src/__tests__/app.test.ts", "Test path mirrors the source path.", 95), js_candidates)
        self.assertTrue(workspace_review_ops.is_project_test_file("web/src/app.test.ts"))
        self.assertEqual(workspace_review_ops.source_module_stem(Path("pkg/__init__.py")), "pkg")

    def test_workspace_review_ops_reexports_related_test_helpers(self) -> None:
        names = [
            "find_related_tests",
            "suggest_focused_test_commands",
            "add_focused_test_commands_for_file",
            "add_focused_test_command",
            "focused_npm_test_command",
            "nearest_package_json",
            "preferred_test_script_name",
            "project_has_pytest_evidence",
            "normalize_related_test_targets",
            "is_project_test_file",
            "related_test_candidates_for_target",
            "source_module_stem",
            "normalized_test_stem",
            "expected_test_names",
            "expected_test_paths",
            "related_test_candidate_sort_key",
            "is_check_script_name",
            "add_check_suggestion",
            "check_suggestion_sort_key",
            "find_python_test_dirs",
            "find_python_package_dirs",
        ]
        for name in names:
            with self.subTest(name=name):
                self.assertIs(getattr(workspace_review_ops, name), getattr(workspace_review_tests, name))

    def test_workspace_review_ops_reexports_project_check_suggestions(self) -> None:
        self.assertIs(workspace_review_ops.suggest_project_checks, workspace_review_checks.suggest_project_checks)

    def test_workspace_review_ops_reexports_git_changes_helper(self) -> None:
        self.assertIs(workspace_review_ops.read_git_changes, workspace_git_changes.read_git_changes)

    def test_workspace_review_ops_reexports_untracked_preview_helper(self) -> None:
        self.assertIs(workspace_review_ops.read_untracked_file_previews, workspace_untracked_previews.read_untracked_file_previews)


if __name__ == "__main__":
    unittest.main()
