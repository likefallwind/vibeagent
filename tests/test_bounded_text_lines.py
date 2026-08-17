from __future__ import annotations

from io import StringIO
import unittest

from vibeagent.bounded_text_lines import TextLineTooLongError, iter_bounded_text_lines


class BoundedTextLinesTests(unittest.TestCase):
    def test_reads_complete_lines_across_fixed_character_chunks(self) -> None:
        stream = StringIO("alpha\nbeta")

        lines = list(iter_bounded_text_lines(stream, max_line_bytes=10, chunk_chars=2))

        self.assertEqual(lines, ["alpha\n", "beta"])

    def test_enforces_utf8_bytes_before_joining_an_oversized_line(self) -> None:
        stream = RecordingStringIO("éééé\n")

        with self.assertRaises(TextLineTooLongError) as raised:
            list(iter_bounded_text_lines(stream, max_line_bytes=6, chunk_chars=2))

        self.assertEqual(raised.exception.max_bytes, 6)
        self.assertEqual(raised.exception.observed_bytes, 8)
        self.assertEqual(stream.read_sizes, [2, 2])

    def test_rejects_invalid_limits(self) -> None:
        with self.assertRaisesRegex(ValueError, "byte limit"):
            list(iter_bounded_text_lines(StringIO(""), max_line_bytes=0))
        with self.assertRaisesRegex(ValueError, "chunk size"):
            list(iter_bounded_text_lines(StringIO(""), max_line_bytes=1, chunk_chars=0))


class RecordingStringIO(StringIO):
    def __init__(self, value: str) -> None:
        super().__init__(value)
        self.read_sizes: list[int] = []

    def readline(self, size: int = -1, /) -> str:
        self.read_sizes.append(size)
        return super().readline(size)


if __name__ == "__main__":
    unittest.main()
