from __future__ import annotations

from pathlib import Path
import unittest
from unittest.mock import Mock

from vibeagent.cli_context import (
    OneShotPriorContext,
    build_context_limit_kwargs,
    is_resume_clear_arg,
    normalize_resume_arg,
    resolve_one_shot_prior_context,
)


class CliContextTests(unittest.TestCase):
    def test_build_context_limit_kwargs_omits_unset_limits(self) -> None:
        self.assertEqual(
            build_context_limit_kwargs(max_failures=3, max_files=None, max_output_chars=0),
            {"max_failures": 3, "max_output_chars": 0},
        )

    def test_normalize_resume_arg_maps_empty_string_to_none(self) -> None:
        self.assertIsNone(normalize_resume_arg(""))
        self.assertEqual(normalize_resume_arg("run-1"), "run-1")

    def test_is_resume_clear_arg_accepts_clear_tokens(self) -> None:
        self.assertTrue(is_resume_clear_arg("off"))
        self.assertTrue(is_resume_clear_arg(" CLEAR "))
        self.assertTrue(is_resume_clear_arg("none"))
        self.assertFalse(is_resume_clear_arg(None))
        self.assertFalse(is_resume_clear_arg("run-1"))

    def test_resolve_one_shot_prior_context_uses_explicit_resume_context(self) -> None:
        root = Path("/project")
        get_resume_context = Mock(return_value=("run-1", "resume context", "Resume context loaded."))
        get_compact_context = Mock()

        prior_context = resolve_one_shot_prior_context(
            resume_arg="run-1",
            compact_arg=None,
            project_root=root,
            resume_kwargs={"max_files": 4},
            compact_kwargs={"max_files": 8},
            get_resume_context_func=get_resume_context,
            get_compact_context_func=get_compact_context,
        )

        self.assertEqual(prior_context, OneShotPriorContext(context="resume context", source="resume", run_id="run-1"))
        self.assertTrue(prior_context.loaded)
        get_resume_context.assert_called_once_with("run-1", root, max_files=4)
        get_compact_context.assert_not_called()

    def test_resolve_one_shot_prior_context_allows_resume_off_without_error(self) -> None:
        root = Path("/project")
        get_resume_context = Mock(return_value=(None, None, "Resume context cleared."))

        prior_context = resolve_one_shot_prior_context(
            resume_arg="off",
            compact_arg=None,
            project_root=root,
            resume_kwargs={},
            compact_kwargs={},
            get_resume_context_func=get_resume_context,
            get_compact_context_func=Mock(),
        )

        self.assertEqual(prior_context, OneShotPriorContext(source="resume_clear"))
        self.assertFalse(prior_context.loaded)
        get_resume_context.assert_called_once_with("off", root)

    def test_resolve_one_shot_prior_context_reports_explicit_resume_failure(self) -> None:
        root = Path("/project")

        prior_context = resolve_one_shot_prior_context(
            resume_arg="missing",
            compact_arg=None,
            project_root=root,
            resume_kwargs={},
            compact_kwargs={},
            get_resume_context_func=Mock(return_value=(None, None, "Session not found: missing")),
            get_compact_context_func=Mock(),
        )

        self.assertEqual(prior_context, OneShotPriorContext(error="Session not found: missing", source="resume"))

    def test_resolve_one_shot_prior_context_uses_explicit_compact_context(self) -> None:
        root = Path("/project")
        get_resume_context = Mock()
        get_compact_context = Mock(return_value=("run-1", "compact context", "Compacted context loaded."))

        prior_context = resolve_one_shot_prior_context(
            resume_arg=None,
            compact_arg="run-1",
            project_root=root,
            resume_kwargs={},
            compact_kwargs={"max_checks": 2},
            get_resume_context_func=get_resume_context,
            get_compact_context_func=get_compact_context,
        )

        self.assertEqual(prior_context, OneShotPriorContext(context="compact context", source="compact", run_id="run-1"))
        self.assertEqual(prior_context.to_json(), {"loaded": True, "source": "compact", "runId": "run-1"})
        get_resume_context.assert_not_called()
        get_compact_context.assert_called_once_with("run-1", root, max_checks=2)

    def test_resolve_one_shot_prior_context_auto_loads_latest_compact_context(self) -> None:
        root = Path("/project")
        get_compact_context = Mock(return_value=("latest-run", "latest compact context", "Compacted context loaded."))

        prior_context = resolve_one_shot_prior_context(
            resume_arg=None,
            compact_arg=None,
            project_root=root,
            resume_kwargs={"max_files": 4},
            compact_kwargs={"max_files": 8},
            get_resume_context_func=Mock(),
            get_compact_context_func=get_compact_context,
        )

        self.assertEqual(
            prior_context,
            OneShotPriorContext(context="latest compact context", source="auto_compact", run_id="latest-run"),
        )
        get_compact_context.assert_called_once_with(None, root)

    def test_resolve_one_shot_prior_context_ignores_missing_auto_context(self) -> None:
        root = Path("/project")

        prior_context = resolve_one_shot_prior_context(
            resume_arg=None,
            compact_arg=None,
            project_root=root,
            resume_kwargs={},
            compact_kwargs={},
            get_resume_context_func=Mock(),
            get_compact_context_func=Mock(return_value=(None, None, "No sessions found.")),
        )

        self.assertEqual(prior_context, OneShotPriorContext(source="auto_compact"))


if __name__ == "__main__":
    unittest.main()
