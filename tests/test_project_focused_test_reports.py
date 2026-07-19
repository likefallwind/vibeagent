from __future__ import annotations

import unittest
from types import SimpleNamespace

from vibeagent.project_focused_test_reports import (
    empty_check_focused_test_commands_report,
    empty_focused_test_commands_report,
    empty_related_tests_report,
    empty_run_focused_test_commands_report,
    serialize_related_test_candidates,
    usage_error,
    usage_message,
)


class ProjectFocusedTestReportsTests(unittest.TestCase):
    def test_usage_helpers_match_existing_text_shapes(self) -> None:
        self.assertEqual(usage_message("Usage", "bad"), "Usage\n  message: bad")
        self.assertEqual(usage_error("Usage", "bad"), "Usage\nError: bad")

    def test_empty_reports_preserve_expected_payload_shapes(self) -> None:
        self.assertEqual(
            empty_related_tests_report("/repo", "bad"),
            {
                "projectRoot": "/repo",
                "ok": False,
                "targetPaths": [],
                "testFiles": 0,
                "candidates": {"shown": 0, "total": 0, "items": []},
                "truncated": False,
                "message": "bad",
            },
        )
        self.assertEqual(
            empty_focused_test_commands_report("/repo", "bad")["commands"],
            {"shown": 0, "total": 0, "items": []},
        )
        self.assertEqual(
            empty_check_focused_test_commands_report("/repo", "bad", max_commands=3)["focusedCommands"],
            {"shown": 0, "total": 0, "max": 3, "items": []},
        )
        self.assertEqual(
            empty_run_focused_test_commands_report(
                "/repo",
                "bad",
                max_commands=4,
                stop_on_failure=False,
            )["selectedCommandsNotRun"],
            {"count": 0, "items": []},
        )

    def test_serialize_related_test_candidates_keeps_public_fields(self) -> None:
        self.assertEqual(
            serialize_related_test_candidates(
                [
                    SimpleNamespace(
                        source_path="src/app.py",
                        test_path="tests/test_app.py",
                        score=90,
                        reason="name match",
                    )
                ]
            ),
            [
                {
                    "source": "src/app.py",
                    "test": "tests/test_app.py",
                    "score": 90,
                    "reason": "name match",
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
