from __future__ import annotations

import unittest

from vibeagent.python_action_reports import python_call_graph_message, python_found_message


class PythonActionReportsTests(unittest.TestCase):
    def test_python_found_message_preserves_count_truncation_and_error_text(self) -> None:
        self.assertEqual(
            python_found_message(5, 2, "reference", errors=[{"path": "bad.py"}]),
            "Found 5 Python reference(s). Showing first 2. Skipped 1 file(s).",
        )
        self.assertEqual(
            python_found_message(2, 2, "definition", errors=[]),
            "Found 2 Python definition(s).",
        )

    def test_python_call_graph_message_preserves_file_limit_text(self) -> None:
        self.assertEqual(
            python_call_graph_message(9, 3, 7, 5, errors=["bad.py", "worse.py"]),
            "Found 9 Python call graph edge(s) across 7 file(s). Showing first 3. "
            "Inspected first 5 file(s). Skipped 2 file(s).",
        )
        self.assertEqual(
            python_call_graph_message(1, 1, 1, 5),
            "Found 1 Python call graph edge(s) across 1 file(s).",
        )


if __name__ == "__main__":
    unittest.main()
