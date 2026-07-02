from __future__ import annotations

from dataclasses import dataclass
import unittest

from vibeagent.output_serialization import serialize_output_context_result, serialize_output_diagnostic


@dataclass
class ContextItem:
    path: str = "src/app.py"
    line: int = 3
    column: int | None = 5
    raw: str = "src/app.py:3:5"
    ok: bool = True
    content: str = "line"
    message: str = "ok"
    context_lines: int = 2
    start_line: int = 1
    end_line: int = 5
    line_count: int = 5
    total_lines: int = 10
    target_line_exists: bool = True
    truncated: bool = False
    max_bytes: int = 1000


@dataclass
class DiagnosticItem:
    severity: str = "error"
    output_line: int = 4
    text: str = "failed"
    path: str = "src/app.py"
    line: int = 3
    column: int | None = None
    raw: str = "raw"


class OutputSerializationTests(unittest.TestCase):
    def test_serialize_output_context_result_keeps_existing_keys(self) -> None:
        self.assertEqual(
            serialize_output_context_result(ContextItem()),
            {
                "path": "src/app.py",
                "line": 3,
                "column": 5,
                "raw": "src/app.py:3:5",
                "ok": True,
                "content": "line",
                "message": "ok",
                "contextLines": 2,
                "startLine": 1,
                "endLine": 5,
                "lineCount": 5,
                "totalLines": 10,
                "targetLineExists": True,
                "truncated": False,
                "maxBytes": 1000,
            },
        )

    def test_serialize_output_diagnostic_keeps_existing_keys(self) -> None:
        self.assertEqual(
            serialize_output_diagnostic(DiagnosticItem()),
            {
                "severity": "error",
                "outputLine": 4,
                "text": "failed",
                "path": "src/app.py",
                "line": 3,
                "column": None,
                "raw": "raw",
            },
        )


if __name__ == "__main__":
    unittest.main()
