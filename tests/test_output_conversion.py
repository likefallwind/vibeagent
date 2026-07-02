from __future__ import annotations

import unittest

from vibeagent import output_conversion, process_runtime


class OutputConversionTests(unittest.TestCase):
    def test_process_runtime_keeps_compatibility_exports(self) -> None:
        self.assertIs(
            process_runtime.output_context_results_from_dicts,
            output_conversion.output_context_results_from_dicts,
        )
        self.assertIs(
            process_runtime.output_diagnostics_from_dicts,
            output_conversion.output_diagnostics_from_dicts,
        )

    def test_output_context_results_from_dicts_converts_known_shape(self) -> None:
        results = output_conversion.output_context_results_from_dicts(
            [
                "skip",
                {
                    "path": "src/app.py",
                    "line": 3,
                    "column": None,
                    "raw": "src/app.py:3",
                    "ok": True,
                    "content": "line",
                    "message": "ok",
                    "context_lines": 2,
                    "start_line": 1,
                    "end_line": 5,
                    "line_count": 5,
                    "total_lines": 10,
                    "target_line_exists": True,
                    "truncated": False,
                    "max_bytes": 1000,
                },
            ]
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].path, "src/app.py")
        self.assertEqual(results[0].line, 3)
        self.assertIsNone(results[0].column)
        self.assertEqual(results[0].context_lines, 2)
        self.assertEqual(results[0].total_lines, 10)

    def test_output_diagnostics_from_dicts_normalizes_unknown_severity(self) -> None:
        diagnostics = output_conversion.output_diagnostics_from_dicts(
            [
                {
                    "severity": "unknown",
                    "output_line": 4,
                    "text": "failed",
                    "path": "src/app.py",
                    "line": 3,
                    "column": None,
                    "raw": "raw",
                }
            ]
        )

        self.assertEqual(len(diagnostics), 1)
        self.assertEqual(diagnostics[0].severity, "info")
        self.assertEqual(diagnostics[0].output_line, 4)
        self.assertEqual(diagnostics[0].path, "src/app.py")

    def test_non_list_inputs_return_empty_lists(self) -> None:
        self.assertEqual(output_conversion.output_context_results_from_dicts({}), [])
        self.assertEqual(output_conversion.output_diagnostics_from_dicts({}), [])


if __name__ == "__main__":
    unittest.main()
