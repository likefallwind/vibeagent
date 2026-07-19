from __future__ import annotations

import unittest
from pathlib import Path

from vibeagent import workspace_review_tests
from vibeagent.workspace_related_test_candidates import (
    expected_test_names,
    expected_test_paths,
    is_project_test_file,
    normalized_test_stem,
    related_test_candidate_sort_key,
    related_test_candidates_for_target,
    source_module_stem,
)


class WorkspaceRelatedTestCandidateTests(unittest.TestCase):
    def test_review_tests_reexports_related_candidate_helpers(self) -> None:
        self.assertIs(workspace_review_tests.is_project_test_file, is_project_test_file)
        self.assertIs(
            workspace_review_tests.related_test_candidates_for_target,
            related_test_candidates_for_target,
        )
        self.assertIs(workspace_review_tests.source_module_stem, source_module_stem)
        self.assertIs(workspace_review_tests.normalized_test_stem, normalized_test_stem)
        self.assertIs(workspace_review_tests.expected_test_names, expected_test_names)
        self.assertIs(workspace_review_tests.expected_test_paths, expected_test_paths)
        self.assertIs(
            workspace_review_tests.related_test_candidate_sort_key,
            related_test_candidate_sort_key,
        )

    def test_related_candidates_match_python_and_javascript_layouts(self) -> None:
        test_files = [
            "tests/test_service.py",
            "pkg/service_test.py",
            "web/src/__tests__/app.test.ts",
            "web/src/other.spec.ts",
        ]

        self.assertIn(
            ("pkg/service_test.py", "Test path mirrors the source path.", 95),
            related_test_candidates_for_target("pkg/service.py", test_files),
        )
        self.assertIn(
            ("web/src/__tests__/app.test.ts", "Test path mirrors the source path.", 95),
            related_test_candidates_for_target("web/src/app.ts", test_files),
        )
        self.assertTrue(is_project_test_file("web/src/app.test.ts"))
        self.assertEqual(source_module_stem(Path("pkg/__init__.py")), "pkg")

    def test_expected_names_and_stem_normalization_keep_existing_rules(self) -> None:
        self.assertEqual(
            expected_test_names(Path("pkg/service.py"), "service"),
            {"test_service.py", "service_test.py"},
        )
        self.assertIn(
            "tests/service_test.py",
            expected_test_paths(Path("pkg/service.py"), "service"),
        )
        self.assertEqual(normalized_test_stem(Path("app.test.ts")), "app")
        self.assertEqual(normalized_test_stem(Path("test_service.py")), "service")

    def test_related_candidate_sort_key_orders_source_score_then_test(self) -> None:
        self.assertEqual(
            related_test_candidate_sort_key(
                {
                    "source_path": "src/app.py",
                    "score": 95,
                    "test_path": "tests/test_app.py",
                }
            ),
            ("src/app.py", -95, "tests/test_app.py"),
        )


if __name__ == "__main__":
    unittest.main()
