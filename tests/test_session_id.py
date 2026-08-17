import unittest

from vibeagent.session_id import normalize_requested_session_id


class SessionIdTests(unittest.TestCase):
    def test_requested_session_id_normalizes_canonical_uuid_case(self) -> None:
        self.assertEqual(
            normalize_requested_session_id("123E4567-E89B-12D3-A456-426614174000"),
            "123e4567-e89b-12d3-a456-426614174000",
        )

    def test_requested_session_id_rejects_noncanonical_values(self) -> None:
        for value in (
            "latest",
            "123e4567e89b12d3a456426614174000",
            "{123e4567-e89b-12d3-a456-426614174000}",
            " 123e4567-e89b-12d3-a456-426614174000",
            None,
        ):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "valid UUID"):
                normalize_requested_session_id(value)


if __name__ == "__main__":
    unittest.main()
