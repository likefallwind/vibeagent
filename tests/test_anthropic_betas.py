import unittest

from vibeagent.anthropic_betas import (
    MAX_ANTHROPIC_BETAS,
    anthropic_beta_header,
    normalize_anthropic_betas,
)


class AnthropicBetaTests(unittest.TestCase):
    def test_normalizes_repeated_comma_separated_names_in_order(self) -> None:
        values = normalize_anthropic_betas(
            ["interleaved-thinking,files-api-2025-04-14", "interleaved-thinking"]
        )

        self.assertEqual(
            values,
            ("interleaved-thinking", "files-api-2025-04-14"),
        )
        self.assertEqual(
            anthropic_beta_header(values),
            "interleaved-thinking,files-api-2025-04-14",
        )

    def test_rejects_header_injection_empty_names_and_excess_values(self) -> None:
        for value in ("", "bad beta", "bad\nheader", "x" * 129):
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_anthropic_betas([value])
        with self.assertRaisesRegex(ValueError, "at most"):
            normalize_anthropic_betas([f"beta-{index}" for index in range(MAX_ANTHROPIC_BETAS + 1)])


if __name__ == "__main__":
    unittest.main()
