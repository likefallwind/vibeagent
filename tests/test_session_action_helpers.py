import unittest

from vibeagent.session_action_helpers import select_session_run_id, session_file_references


class SessionActionHelpersTests(unittest.TestCase):
    def test_select_session_run_id_uses_normalized_action_run_id_or_workspace(self) -> None:
        self.assertEqual(select_session_run_id(" run-1 ", "current-run"), "run-1")
        self.assertEqual(select_session_run_id(None, "current-run"), "current-run")

    def test_session_file_references_normalizes_visible_file_uses(self) -> None:
        references, total, shown, truncated = session_file_references(
            [
                {"path": " app.py ", "uses": [" read ", "", 3, "write"]},
                {"path": "", "uses": ["ignored"]},
                {"path": "tests/test_app.py", "uses": ["test"]},
            ],
            2,
        )

        self.assertEqual(references, [{"path": "app.py", "uses": ["read", "write"]}])
        self.assertEqual(total, 3)
        self.assertEqual(shown, 2)
        self.assertTrue(truncated)


if __name__ == "__main__":
    unittest.main()
