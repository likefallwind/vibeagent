from __future__ import annotations

from types import SimpleNamespace
import unittest

from vibeagent.agent_preview_paths import (
    normalize_preview_path,
    paths_overlap_or_nested,
    preview_cwd_value,
    preview_optional_path_attr,
    preview_path_attr,
    preview_path_tuple,
    preview_path_value,
)


class AgentPreviewPathTests(unittest.TestCase):
    def test_normalize_preview_path_collapses_safe_segments(self) -> None:
        self.assertEqual(normalize_preview_path("./src/../app.py"), "app.py")
        self.assertEqual(normalize_preview_path("src\\pkg\\..\\app.py"), "src/app.py")
        self.assertEqual(normalize_preview_path("src//./app.py"), "src/app.py")

    def test_normalize_preview_path_preserves_leading_parent_segments(self) -> None:
        self.assertEqual(normalize_preview_path("../outside.py"), "../outside.py")
        self.assertEqual(normalize_preview_path("../../outside.py"), "../../outside.py")
        self.assertEqual(normalize_preview_path("../pkg/../outside.py"), "../outside.py")

    def test_preview_path_values_handle_root_and_non_string_defaults(self) -> None:
        self.assertEqual(preview_path_value("."), ".")
        self.assertEqual(preview_path_value("./"), ".")
        self.assertEqual(preview_path_value(None, "fallback"), "fallback")
        self.assertEqual(preview_path_attr(SimpleNamespace(path="./src/../app.py")), "app.py")
        self.assertIsNone(preview_optional_path_attr(SimpleNamespace(path=None)))
        self.assertEqual(preview_path_tuple(["./app.py", "pkg/../web"]), ("app.py", "web"))
        self.assertEqual(preview_cwd_value(None), ".")
        self.assertEqual(preview_cwd_value("./web/../api"), "api")

    def test_paths_overlap_or_nested_uses_normalized_boundaries(self) -> None:
        self.assertTrue(paths_overlap_or_nested(frozenset({"pkg/../app.py"}), frozenset({"./app.py"})))
        self.assertTrue(paths_overlap_or_nested(frozenset({"pkg/app.py"}), frozenset({"./pkg"})))
        self.assertTrue(paths_overlap_or_nested(frozenset({"./pkg"}), frozenset({"pkg/app.py"})))
        self.assertFalse(paths_overlap_or_nested(frozenset({"pkg-old/app.py"}), frozenset({"pkg"})))
        self.assertFalse(paths_overlap_or_nested(frozenset({"pkg"}), frozenset({"pkg-old/app.py"})))


if __name__ == "__main__":
    unittest.main()
